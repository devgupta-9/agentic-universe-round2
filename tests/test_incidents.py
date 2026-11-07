from controller.incidents import Incidents
from controller.store import Store


class PaidAPI:
    def __init__(self):
        self.writes = []
    def get(self, path):
        return {"credits_remaining": 200}
    def write(self, method, path, body):
        self.writes.append((path, body))
        if "suggest" in path:
            return {"suggestions": [{"prompt_version": "P3"}]}
        return {"validation_run_id": "val1", "pass_rate": .99, "prompt_version": body["prompt_version"], "n": body["n"]}


def test_paid_request_is_reserved_before_sending_and_validated_fix_is_reused(tmp_path):
    api = PaidAPI()
    with Store(tmp_path / "state.sqlite3") as store:
        service = Incidents(store, api, {"wf": {}})
        workflow = {"workflow_id": "wf", "governance": {"min_validation_pass_rate": .97}}
        job = {"state": "detected", "current_prompt": "P2", "known_safe_prompt": "P1", "detected": 1000}
        store.set("incident:wf", job)
        result = service.fix(workflow, job, 1000)
        assert result["selected_prompt"] == "P1"
        assert result["evidence"]["validation_run_id"] == "val1"
        assert store.get("credits_reserved:wf") == 6
        service.fix(workflow, result, 1000)
        assert len(api.writes) == 1


def test_credit_exhaustion_is_prevented(tmp_path):
    api = PaidAPI()
    api.get = lambda path: {"credits_remaining": 5}
    with Store(tmp_path / "state.sqlite3") as store:
        service = Incidents(store, api, {"wf": {}})
        workflow = {"workflow_id": "wf", "governance": {"min_validation_pass_rate": .97}}
        job = {"state": "detected", "current_prompt": "P2", "known_safe_prompt": "P1", "detected": 1000}
        result = service.fix(workflow, job, 1000)
        assert result["state"] == "budget_blocked"
        assert not api.writes


def test_saved_paid_receipt_survives_a_crash_before_job_advancement(tmp_path):
    api = PaidAPI()
    with Store(tmp_path / "state.sqlite3") as store:
        service = Incidents(store, api, {"wf": {}})
        workflow = {"workflow_id": "wf", "governance": {"min_validation_pass_rate": .97}}
        job = {"state": "detected", "current_prompt": "P2", "known_safe_prompt": "P1", "detected": 1000,
               "paid_receipts": [{"path": "/validation/runs", "response": {
                   "validation_run_id": "saved", "prompt_version": "P1", "pass_rate": .99, "n": 600}}]}
        result = service.fix(workflow, job, 1015)
        assert result["evidence"]["validation_run_id"] == "saved"
        assert not api.writes
