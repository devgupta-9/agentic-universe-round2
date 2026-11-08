"""Fail CI on incomplete, stale, non-Linux, or inconsistent evidence."""
import argparse
import json
import re
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(root, name, suffix):
    require(bool(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name)), "Invalid report name")
    return json.loads((root / f"{name}-{suffix}.json").read_text(encoding="utf-8"))


def integrity(evidence, name):
    require(type(evidence["call_rows"]) is int and evidence["call_rows"] > 0, f"{name}: no call observations")
    require(evidence["call_rows"] == evidence["metric_dials"], f"{name}: materialized counts differ")
    require(evidence["last_event_id_matches_server"] is True, f"{name}: event checkpoint mismatch")
    require(evidence["duplicate_remote_applications"] == [], f"{name}: duplicate or missing application evidence")


def verify_reports(root, names, expected_commit, recovery_name=None):
    root = Path(root)
    require(bool(names) or bool(recovery_name), "Select at least one run to verify")
    verified = []
    for name in list(names) + ([recovery_name] if recovery_name else []):
        report = read(root, name, "runtime")
        evidence = report["evaluation"]
        require(report["last_state"]["finished"] is True, f"{name}: scenario did not finish")
        require(evidence["linux_runtime_verified"] is True and evidence["platform"].startswith("Linux-"), f"{name}: Linux was not exercised")
        require(evidence["source_commit"] == expected_commit, f"{name}: stale source commit")
        expected_entrypoint = "Python module" if name == recovery_name else "run.sh (native Linux)"
        require(evidence["entrypoint"] == expected_entrypoint, f"{name}: expected {expected_entrypoint}")
        require(evidence["logical_cpus"] > 0 and evidence["physical_memory_bytes"] > 0, f"{name}: missing host measurements")
        integrity(evidence, name)
        seconds = evidence["controller_wall_seconds_including_restart"]
        require(seconds > 0, f"{name}: invalid wall time")
        events = sum(chunk["events"] for chunk in report["ingestion"])
        require(events > 0, f"{name}: no events ingested")
        verified.append({"name": name, "source_commit": expected_commit, "events": events,
                         "complete_loop_events_per_second": events / seconds,
                         "peak_memory_mib": report["performance"]["peak_memory_mb"],
                         "logical_cpus": evidence["logical_cpus"], "physical_memory_bytes": evidence["physical_memory_bytes"],
                         "entrypoint": evidence["entrypoint"]})
    if recovery_name:
        recovery = read(root, recovery_name, "recovery")
        require(recovery["exit_code"] == 91 and recovery["finished"] is True, "Recovery did not hard-stop and finish")
        integrity(recovery, recovery_name)
        local_ids = {row[0] for row in recovery["local_outbox_before_restart"]}
        remote = recovery["remote_changes_before_local_receipt"]
        require(bool(remote) and all(change["proposal_id"] in local_ids for change in remote),
                "Recovery did not exercise a remote apply before local receipt")
    return {"verified": True, "expected_commit": expected_commit, "runs": verified,
            "recovery_verified": bool(recovery_name)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-root", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--run", action="append", default=[])
    parser.add_argument("--recovery")
    parser.add_argument("--summary")
    args = parser.parse_args()
    result = verify_reports(args.report_root, args.run, args.expected_commit, args.recovery)
    destination = Path(args.report_root) / "ci-verification.json"
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.summary:
        lines = ["### Verified Linux evidence", "", f"Source: `{args.expected_commit}`", "",
                 "| Run | Events | Complete-loop events/sec | Peak controller MiB | CPUs |", "|---|---:|---:|---:|---:|"]
        for run in result["runs"]:
            lines.append(f"| {run['name']} | {run['events']:,} | {run['complete_loop_events_per_second']:,.0f} | {run['peak_memory_mib']:.1f} | {run['logical_cpus']} |")
        lines += ["", "Resources are measured from the actual runner; this does not certify an exact 4-vCPU / 8-GB deployment."]
        with Path(args.summary).open("a", encoding="utf-8") as summary:
            summary.write("\n".join(lines) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
