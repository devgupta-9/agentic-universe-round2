import copy
import json
import pytest

from scripts.verify_ci_reports import verify_reports


COMMIT = "a" * 40


def runtime(entrypoint="run.sh (native Linux)"):
    return {"last_state": {"finished": True}, "performance": {"peak_memory_mb": 42},
            "ingestion": [{"events": 1000}], "evaluation": {
                "platform": "Linux-6.8.0-x86_64", "linux_runtime_verified": True,
                "source_commit": COMMIT, "logical_cpus": 2, "physical_memory_bytes": 7 * 1024 ** 3,
                "entrypoint": entrypoint, "call_rows": 800, "metric_dials": 800,
                "last_event_id_matches_server": True, "duplicate_remote_applications": [],
                "controller_wall_seconds_including_restart": 10}}


def write(root, name, payload, suffix="runtime"):
    (root / f"{name}-{suffix}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_accepts_completed_linux_run_with_matching_source(tmp_path):
    write(tmp_path, "dev", runtime())
    result = verify_reports(tmp_path, ["dev"], COMMIT)
    assert result["verified"] and result["runs"][0]["complete_loop_events_per_second"] == 100


@pytest.mark.parametrize("mutation", [
    lambda r: r["last_state"].update(finished=False),
    lambda r: r["evaluation"].update(platform="Windows-10", linux_runtime_verified=False),
    lambda r: r["evaluation"].update(source_commit="b" * 40),
    lambda r: r["evaluation"].update(metric_dials=799),
    lambda r: r["evaluation"].update(last_event_id_matches_server=False),
    lambda r: r["evaluation"].update(duplicate_remote_applications=["duplicate"]),
    lambda r: r["evaluation"].update(entrypoint="Python module"),
])
def test_rejects_incomplete_stale_or_wrong_platform_evidence(tmp_path, mutation):
    report = runtime()
    mutation(report)
    write(tmp_path, "dev", report)
    with pytest.raises(ValueError):
        verify_reports(tmp_path, ["dev"], COMMIT)


def test_recovery_must_show_an_actual_remote_apply_before_restart(tmp_path):
    write(tmp_path, "recovery", runtime("Python module"))
    recovery = {"exit_code": 91, "finished": True, "call_rows": 800, "metric_dials": 800,
                "last_event_id_matches_server": True, "duplicate_remote_applications": [],
                "local_outbox_before_restart": [["p1", "wf", "pending"]],
                "remote_changes_before_local_receipt": [{"proposal_id": "p1"}]}
    write(tmp_path, "recovery", recovery, "recovery")
    assert verify_reports(tmp_path, [], COMMIT, recovery_name="recovery")["recovery_verified"]
    bad = copy.deepcopy(recovery)
    bad["remote_changes_before_local_receipt"] = []
    write(tmp_path, "recovery", bad, "recovery")
    with pytest.raises(ValueError):
        verify_reports(tmp_path, [], COMMIT, recovery_name="recovery")
