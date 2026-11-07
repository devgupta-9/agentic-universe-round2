from controller.learning import Learning
from controller.governance import Governance
from controller.store import Store, minute
from test_evidence import config
from test_store import call


def workflow():
    return {"workflow_id": "wf", "tenant_id": "tenant", "options": {"voice": ["V1", "V2"]},
            "cadence": [2, 3, 3], "mid_flight": "allowed", "objective": {
                "primary": "engagement_rate", "guardrail": {"pickup_rate_max_drop": .02}},
            "governance": {"auto_apply": {"enabled": False, "allowed_dims": [], "max_shift": 0},
                "approver_hours": [10, 19], "max_requests_per_24h": 3, "proposal_ttl_hours": 24}}


def test_unapproved_unrun_arm_is_not_evidence(tmp_path):
    origin = minute("2027-01-04T00:00:00+05:30")
    with Store(tmp_path / "state.sqlite3") as store:
        events = [call(n, True, True) for n in range(1, 1001)]
        for event in events:
            event["ts"] = "2027-01-03T09:15:00+05:30"
        store.ingest(0, "history", events)
        wf, cur = workflow(), {"version": 1, "config": config({"V1": 1})}
        gov = Governance(store, object())
        learning = Learning(store, object(), gov, {"wf": wf}, origin, origin + 8 * 1440)
        learning.plan_voice(wf, cur, origin + 600)
        op = gov.operation(gov.active("wf")[0])
        assert op["data"]["kind"] == "voice_explore"
        assert store.get("experiment:wf") is None
        assert store.counts("wf", 0, origin, voice="V2")[0]["dials"] == 0
        learning.plan_voice(wf, cur, origin + 660)
        assert store.db.execute("SELECT COUNT(*) FROM proposals").fetchone()[0] == 1


def test_single_flagged_call_cannot_trigger_prompt_repair(tmp_path):
    origin = minute("2027-01-04T00:00:00+05:30")
    with Store(tmp_path / "state.sqlite3") as store:
        event = call(1, True)
        event["qa"]["hallucination_flag"] = True
        store.ingest(0, "events", [event])
        wf = workflow()
        learning = Learning(store, object(), Governance(store, object()), {"wf": wf}, origin, origin + 8 * 1440)
        assert not learning.prompt_alarm(wf, {"config": config({"V1": 1})}, origin + 600)["alarm"]


def test_decayed_promoted_voice_requires_a_governed_rollback(tmp_path):
    origin = minute("2027-01-04T00:00:00+05:30")
    def observations():
        for index in range(24000):
            arm, offset = ("V1", index) if index < 12000 else ("V2", index - 12000)
            connected = offset < 4800
            engaged = connected and offset < (3840 if arm == "V1" else 960)
            event = call(index + 1, connected, engaged)
            event["variant"]["voice"] = arm
            event["ts"] = "2027-01-06T09:15:00+05:30"
            yield event
    with Store(tmp_path / "state.sqlite3") as store:
        store.ingest(0, "events", observations())
        wf = workflow()
        gov = Governance(store, object())
        learning = Learning(store, object(), gov, {"wf": wf}, origin, origin + 8 * 1440)
        store.set("experiment:wf", {"phase": "promoted", "start": origin, "monitor_start": origin + 1440,
                                    "last_look": -1, "winner": "V2", "control": "V1"})
        learning.plan_voice(wf, {"version": 2, "config": config({"V2": .8, "V1": .2})}, origin + 3 * 1440 + 660)
        operation = gov.operation(gov.active("wf")[0])
        assert operation["data"]["kind"] == "voice_rollback"
        assert operation["body"]["proposed_config"]["allocations"]["default"]["voice"] == {"V1": 1}
        assert store.get("experiment:wf")["phase"] == "promoted"  # A proposal is not an applied rollback.


def test_material_supervisor_voice_edit_freezes_further_voice_exploration(tmp_path):
    class API:
        def get(self, path):
            return [{"version": 3, "actor": "supervisor", "changed_dims": ["voice"]}]
    origin = minute("2027-01-04T00:00:00+05:30")
    with Store(tmp_path / "state.sqlite3") as store:
        wf = workflow()
        learning = Learning(store, API(), Governance(store, API()), {"wf": wf}, origin, origin + 8 * 1440)
        store.set("known_version:wf", 2)
        store.set("workflow:wf", {"current": {"version": 2, "config": config({"V1": .875, "V2": .125})}})
        learning.initialize(wf, {"version": 3, "config": config({"V2": 1})}, origin + 3 * 1440)
        assert store.get("experiment_pause:wf") == origin + 8 * 1440


def test_safety_alert_can_trigger_on_a_clear_population_shift_before_winner_level_certainty(tmp_path):
    origin = minute("2027-01-04T00:00:00+05:30")
    with Store(tmp_path / "state.sqlite3") as store:
        observations = [call(i, True) for i in range(1, 241)]
        for event in observations[:15]:
            event["qa"]["hallucination_flag"] = True
        store.ingest(0, "events", observations)
        store.set("baseline:wf", {"counts": {"connected": 10000, "hallucinations": 100}})
        learning = Learning(store, object(), Governance(store, object()), {"wf": workflow()}, origin, origin + 8 * 1440)
        assert learning.prompt_alarm(workflow(), {"config": config({"V1": 1})}, origin + 600)["alarm"]
