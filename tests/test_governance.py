import copy
from controller.client import UncertainWrite
from controller.governance import Governance
from controller.store import Store
from test_evidence import config


class WorldAPI:
    def __init__(self):
        self.current = {"version": 1, "config": config({"V1": 1})}
        self.history = []
        self.writes = 0
        self.lose_response = False

    def get(self, path, **params):
        if path.endswith("/history"):
            return self.history
        if path.endswith("/config"):
            return self.current
        return []

    def write(self, method, path, body):
        self.writes += 1
        self.current = {"version": 2, "config": body["proposed_config"]}
        self.history.append({"version": 2, "proposal_id": body["proposal_id"], "approval_id": None})
        if self.lose_response:
            raise UncertainWrite("remote applied but reply was lost")
        return {"version": 2}


WF = {"workflow_id": "wf", "tenant_id": "tenant", "governance": {
    "auto_apply": {"enabled": True, "allowed_dims": ["schedule"], "max_shift": .2},
    "approver_hours": [0, 24], "max_requests_per_24h": 3}}


def test_remote_success_with_lost_response_reconciles_after_restart(tmp_path):
    api = WorldAPI()
    api.lose_response = True
    target = copy.deepcopy(api.current["config"])
    target["schedule"] = {"hour_weights": {"default": {"9": 1}}}
    path = tmp_path / "state.sqlite3"
    with Store(path) as store:
        gov = Governance(store, api)
        pid = gov.propose(WF, api.current, target, 1000, "timing", "schedule", {})
        gov.tick({"wf": WF}, 1000)
        assert gov.operation(pid)["state"] == "uncertain"
    with Store(path) as store:
        gov = Governance(store, api)
        gov.tick({"wf": WF}, 1015)
        assert gov.operation(pid)["state"] == "applied"
        assert api.writes == 1


def test_supervisor_version_change_prevents_apply(tmp_path):
    api = WorldAPI()
    target = copy.deepcopy(api.current["config"])
    target["schedule"] = {"hour_weights": {"default": {"9": 1}}}
    with Store(tmp_path / "state.sqlite3") as store:
        gov = Governance(store, api)
        pid = gov.propose(WF, api.current, target, 1000, "timing", "schedule", {})
        api.current["version"] = 2
        gov.tick({"wf": WF}, 1000)
        assert gov.operation(pid)["state"] == "stale"
        assert api.writes == 0


def test_kestrel_preferences_are_stricter_than_platform_policy(tmp_path):
    from controller.store import minute
    wf = copy.deepcopy(WF)
    wf["tenant_id"] = "kestrel_finance"
    api = WorldAPI()
    target = copy.deepcopy(api.current["config"])
    target["schedule"] = {"hour_weights": {"default": {"9": 1}}}
    with Store(tmp_path / "state.sqlite3") as store:
        gov = Governance(store, api)
        assert gov.propose(wf, api.current, target, minute("2027-01-04T10:00:00+05:30"), "timing", "schedule", {}) is None
        pid = gov.propose(wf, api.current, target, minute("2027-01-04T11:00:00+05:30"), "timing", "schedule", {})
        assert gov.operation(pid)["mode"] == "approval"


def test_success_is_reconciled_before_a_later_supervisor_version(tmp_path):
    api = WorldAPI()
    api.lose_response = True
    target = copy.deepcopy(api.current["config"])
    target["schedule"] = {"hour_weights": {"default": {"9": 1}}}
    with Store(tmp_path / "state.sqlite3") as store:
        gov = Governance(store, api)
        pid = gov.propose(WF, api.current, target, 1000, "timing", "schedule", {})
        gov.tick({"wf": WF}, 1000)
        api.current["version"] = 3
        gov.reconcile_applied(1015)
        assert gov.operation(pid)["state"] == "applied"
        assert gov.operation(pid)["applied_version"] == 2
        assert api.writes == 1
