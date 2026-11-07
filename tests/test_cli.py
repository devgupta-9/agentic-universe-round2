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
