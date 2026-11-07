import json
import subprocess
import sys
from controller.store import Store


def test_audit_query_reads_our_own_store(tmp_path):
    path = tmp_path / "state.sqlite3"
    with Store(path) as store:
        store.audit(29985000, "wf", "change_effective", {"reason": "population evidence", "approval_id": "apr1", "version": 2})
    result = subprocess.run([sys.executable, "-m", "controller", "why", "--db", str(path), "--workflow", "wf"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout)
    assert response["decision"]["reason"] == "population evidence"
    assert response["decision"]["approval_id"] == "apr1"


def test_why_links_a_remote_change_to_intent_before_receipt_reconciliation(tmp_path):
    import copy
    from controller.governance import Governance
    from test_governance import WF, WorldAPI
    api = WorldAPI()
    target = copy.deepcopy(api.current["config"])
    target["schedule"] = {"hour_weights": {"default": {"9": 1}}}
    path = tmp_path / "state.sqlite3"
    with Store(path) as store:
        gov = Governance(store, api)
        pid = gov.propose(WF, api.current, target, 29985000, "population evidence", "schedule", {})
        store.audit(29985015, "wf", "config_changed", {"version": 2, "proposal_id": pid, "actor": "controller_auto"})
    result = subprocess.run([sys.executable, "-m", "controller", "why", "--db", str(path), "--workflow", "wf"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    decision = json.loads(result.stdout)["decision"]
    assert decision["reason"] == "population evidence"
    assert decision["version"] == 2
    assert decision["after"]["schedule"] == target["schedule"]
