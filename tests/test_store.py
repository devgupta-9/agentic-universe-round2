import pytest

from controller.store import Store


def call(event_id, connected, engaged=False):
    return {"event_id": event_id, "type": "call", "ts": "2027-01-04T09:15:00+05:30",
            "workflow_id": "wf", "lead_id": f"lead{event_id}", "person_id": "p1",
            "config_version": 1, "cohort_id": "default",
            "variant": {"voice": "V1", "welcome_message": "W1", "caller_id": "D1", "prompt_version": "P1"},
            "connected": connected, "engaged": engaged,
            "qa": {"hallucination_flag": False} if connected else None}


def test_all_dials_and_replay_survive_restart(tmp_path):
    path = tmp_path / "state.sqlite3"
    with Store(path) as store:
        assert store.ingest(0, "events", [call(1, False), call(2, True), call(3, True, True)]) == 3
        assert store.counts("wf", 0, 99999999)[0]["dials"] == 3
        assert store.ingest(0, "events", [call(1, False), call(2, True), call(3, True, True)]) == 0
    with Store(path) as store:
        count = store.counts("wf", 0, 99999999)[0]
        assert (count["dials"], count["connected"], count["engaged"]) == (3, 2, 1)
        assert store.get("last_event_id") == 3
        assert store.get("last_chunk") == 0


def test_broken_stream_rolls_back_data_and_checkpoint(tmp_path):
    def broken():
        for eid in range(1, 5002):
            yield call(eid, True)
        raise ValueError("truncated NDJSON")
    with Store(tmp_path / "state.sqlite3") as store:
        with pytest.raises(ValueError, match="truncated"):
            store.ingest(0, "events", broken())
        assert store.get("last_chunk", -1) == -1
        assert store.counts("wf", 0, 99999999)[0]["dials"] == 0
        assert store.ingest(0, "events", [call(1, True)]) == 1


def test_history_and_actual_variants_are_queryable(tmp_path):
    with Store(tmp_path / "state.sqlite3") as store:
        first, second = call(1, True, True), call(2, False)
        second["variant"]["voice"] = "V2"
        store.ingest(0, "history", [first, second])
        rows = store.counts("wf", 0, 99999999, group="voice")
        assert {r["arm"]: r["dials"] for r in rows} == {"V1": 1, "V2": 1}
        assert store.counts("wf", 0, 99999999, voice="V2")[0]["connected"] == 0
