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
