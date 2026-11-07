"""Reproducible local evaluation. Only the supplied CLI reads simulator run files."""
import argparse
import json
import os
import platform
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]


def get(url, path):
    with urlopen(url + path, timeout=10) as response:
        return json.load(response)


def command(args, **kwargs):
    result = subprocess.run(args, cwd=ROOT, text=True, encoding="utf-8", capture_output=True, **kwargs)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args}\n{result.stdout[-5000:]}\n{result.stderr[-5000:]}")
    return result.stdout


def wait(process, timeout=2400):
    deadline = time.monotonic() + timeout
    while process.poll() is None:
        if time.monotonic() > deadline:
            raise TimeoutError("Evaluation child exceeded its bounded timeout")
        time.sleep(.1)
    return process.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--root", default="runs")
    parser.add_argument("--baseline")
    parser.add_argument("--crash", choices=["after-apply"])
    parser.add_argument("--bash", action="store_true")
    parser.add_argument("--no-grade", action="store_true")
    parser.add_argument("--startup-timeout", type=int, default=300,
                        help="Bound for simulator history generation, reported separately from controller time")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", args.name):
        parser.error("Use a simple report name containing letters, digits, underscores, or hyphens")
    run_id = args.name + "-" + uuid.uuid4().hex[:10]
    work = (Path(args.root) / run_id).resolve()
    work.mkdir(parents=True, exist_ok=False)
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    db_path = ROOT / "state" / (run_id + ".sqlite3")
    world_path = work / "world"
    baseline_path = Path(args.baseline).resolve() if args.baseline else work / "baseline"
    python = [sys.executable, "-X", "utf8"]
    if not args.no_grade and not args.baseline:
        print(json.dumps({"phase": "baseline", "scenario": args.scenario}), flush=True)
        print(command(python + ["-m", "sim", "baseline", "--scenario", args.scenario, "--run-dir", str(baseline_path)]).strip(), flush=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    server_log = open(work / "server.log", "w", encoding="utf-8")
    controller_log = open(work / "controller.log", "w", encoding="utf-8")
    server = controller = None
    started = time.perf_counter()
    crash_evidence = None
    try:
        server = subprocess.Popen(python + ["-m", "sim", "serve", "--scenario", args.scenario,
                                  "--run-dir", str(world_path), "--port", str(port)], cwd=ROOT,
                                  stdout=server_log, stderr=subprocess.STDOUT, **flags)
        print(json.dumps({"phase": "server_start", "url": url}), flush=True)
        deadline = time.monotonic() + args.startup_timeout
        next_telemetry = time.monotonic() + 30
        while True:
            if server.poll() is not None:
                raise RuntimeError("Simulator exited during startup; inspect " + str(work / "server.log"))
            try:
                if get(url, "/health")["ok"]:
                    break
            except OSError:
                pass
            if time.monotonic() > deadline:
                raise TimeoutError(f"Simulator did not become healthy within {args.startup_timeout} seconds")
            if time.monotonic() >= next_telemetry:
                print(json.dumps({"phase": "simulator_history_generation", "elapsed_seconds": round(time.perf_counter() - started, 1),
                                  "server_pid": server.pid, "controller_started": False}), flush=True)
                next_telemetry = time.monotonic() + 30
            time.sleep(.2)
        startup_seconds = time.perf_counter() - started
        launch = python + ["-m", "controller", "run", "--url", url, "--db", str(db_path)]
        environment = os.environ.copy()
        if args.bash:
            bash = r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else shutil.which("bash")
            if not bash:
                raise RuntimeError("Bash is unavailable")
            environment["PYTHON"], environment["CONTROLLER_DB"] = Path(sys.executable).as_posix(), db_path.as_posix()
            launch = [bash, "./run.sh", url]
        if args.crash:
            if args.bash:
                raise RuntimeError("The explicit after-apply failpoint uses the Python test entrypoint")
            launch.append("--test-crash-after-apply")
        print(json.dumps({"phase": "controller", "database": str(db_path)}), flush=True)
        controller_started = time.perf_counter()
        controller = subprocess.Popen(launch, cwd=ROOT, env=environment, stdout=controller_log, stderr=subprocess.STDOUT, **flags)
        code = wait(controller)
        if args.crash:
            if code != 91:
                raise RuntimeError(f"Expected hard exit 91 at the apply failpoint, got {code}")
            with sqlite3.connect(db_path) as connection:
                local = connection.execute("SELECT pid,wid,state FROM proposals WHERE state IN ('prepared','approved','uncertain','pending')").fetchall()
            remote = []
            for pid, wid, state in local:
                remote.extend(h for h in get(url, f"/workflows/{wid}/config/history") if h.get("proposal_id") == pid)
            crash_evidence = {"method": "os._exit(91) immediately after successful HTTP apply, before local receipt commit",
                              "exit_code": code, "sim_state_before_restart": get(url, "/sim/state"),
                              "local_outbox_before_restart": local, "remote_changes_before_local_receipt": remote}
            if not remote:
                raise AssertionError("Failpoint did not exercise a committed remote change")
            print(json.dumps({"phase": "restart", "remote_applied_local_unrecorded": len(remote)}), flush=True)
            controller = subprocess.Popen(launch[:-1], cwd=ROOT, env=environment, stdout=controller_log, stderr=subprocess.STDOUT, **flags)
            code = wait(controller)
        if code:
            raise RuntimeError(f"Controller exited {code}; inspect {work / 'controller.log'}")
        controller_seconds = time.perf_counter() - controller_started
        state = get(url, "/sim/state")
        if not state["finished"]:
            raise AssertionError("Controller stopped before the world finished")
        snapshot = json.loads(command(python + ["-m", "controller", "view", "--db", str(db_path)]))
        with sqlite3.connect(db_path) as connection:
            calls = connection.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
            totals = connection.execute("SELECT COALESCE(SUM(dials),0) FROM metrics").fetchone()[0]
            duplicate_remote = []
            for workflow in get(url, "/workflows"):
                pids = [h["proposal_id"] for h in get(url, f"/workflows/{workflow['workflow_id']}/config/history") if h.get("proposal_id")]
                duplicate_remote.extend(pid for pid in set(pids) if pids.count(pid) > 1)
            high_water = json.loads(connection.execute("SELECT value FROM kv WHERE key='last_event_id'").fetchone()[0])
        if calls != totals or high_water != state["last_event_id"] or duplicate_remote:
            raise AssertionError("Observation/checkpoint/application integrity check failed")
        snapshot["evaluation"] = {"platform": platform.platform(), "python": platform.python_version(),
            "logical_cpus": os.cpu_count(), "target_linux_hardware_verified": False,
            "server_start_seconds": startup_seconds, "controller_wall_seconds_including_restart": controller_seconds,
            "wall_seconds_per_simulated_day_including_history_ingest": controller_seconds / (state["end_minute"] / 1440),
            "entrypoint": "run.sh via Bash" if args.bash else "Python module",
            "call_rows": calls, "metric_dials": totals, "last_event_id_matches_server": True,
            "duplicate_remote_applications": duplicate_remote}
        (reports / (args.name + "-runtime.json")).write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        if crash_evidence:
            crash_evidence.update(finished=True, call_rows=calls, metric_dials=totals,
                                  last_event_id_matches_server=True, duplicate_remote_applications=duplicate_remote,
                                  database=str(db_path))
            (reports / (args.name + "-recovery.json")).write_text(json.dumps(crash_evidence, indent=2), encoding="utf-8")
        if not args.no_grade:
            grade = python + ["-m", "sim", "grade", "--run", str(world_path), "--baseline", str(baseline_path)]
            command(grade + ["--out", str(reports / (args.name + ".md"))])
            command(grade + ["--json", "--out", str(reports / (args.name + ".json"))])
        print(json.dumps({"phase": "complete", "name": args.name, "evaluation": snapshot["evaluation"]}), flush=True)
    finally:
        for process in (controller, server):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        server_log.close()
        controller_log.close()
        shutil.copyfile(work / "controller.log", reports / (args.name + "-controller.log"))


if __name__ == "__main__":
    main()
