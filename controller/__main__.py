"""Run the controller, inspect its consolidated view, or explain a change."""
import argparse
import hashlib
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from .client import API
from .engine import Engine
from .evidence import rate
from .store import Store, minute


@contextmanager
def writer_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + ".lock", "a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def summary(store, wid=None):
    ingestion = [dict(r) for r in store.db.execute("SELECT kind,SUM(n) AS events,SUM(seconds) AS seconds FROM chunks GROUP BY kind")]
    for row in ingestion:
        row["events_per_second"] = row["events"] / row["seconds"] if row["seconds"] else None
        row["timing_scope"] = "Streaming, parsing and SQL writes before COMMIT; final commit/checkpoint latency is excluded"
    params, where = ((wid,), " WHERE wid=?") if wid else ((), "")
    operations = [dict(r) for r in store.db.execute("SELECT pid,wid,state,mode,approval_id,created,applied_version FROM proposals" + where + " ORDER BY created", params)]
    workflows = {}
    for row in store.db.execute("SELECT key,value FROM kv WHERE key LIKE 'workflow:%'"):
        key = row["key"].split(":", 1)[1]
        if wid and key != wid:
            continue
        workflow = json.loads(row["value"])
        workflow["experiment"] = store.get("experiment:" + key)
        workflow["incident"] = store.get("incident:" + key)
        workflows[key] = workflow
    performance = store.get("performance")
    replay_rate = sum(row["events"] for row in ingestion) / performance["wall_seconds"] if performance and performance["wall_seconds"] else None
    return {"database": str(store.path), "last_state": store.get("last_state"), "performance": performance,
            "end_to_end_replay_events_per_second": replay_rate,
            "ingestion": ingestion, "workflows": workflows, "proposals": operations,
            "recent_decisions": [{**dict(r), "data": json.loads(r["data"])} for r in store.db.execute(
                "SELECT * FROM audit" + where + " ORDER BY id DESC LIMIT 30", params)]}


def explain(store, wid, at=None):
    until = minute(at) if at else 999999999
    row = store.db.execute("SELECT * FROM audit WHERE wid=? AND minute<=? AND kind IN ('change_effective','config_changed') "
                           "ORDER BY minute DESC,CASE WHEN kind='change_effective' THEN 1 ELSE 0 END DESC,id DESC LIMIT 1",
                           (wid, until)).fetchone()
    if not row:
        return {"workflow": wid, "decision": None, "message": "No recorded configuration change at or before that time"}
    decision = json.loads(row["data"])
    if row["kind"] == "config_changed" and decision.get("proposal_id"):
        intent = store.db.execute("SELECT data,body,approval_id FROM proposals WHERE pid=?", (decision["proposal_id"],)).fetchone()
        if intent:
            metadata, body = json.loads(intent["data"]), json.loads(intent["body"])
            decision.update(reason=metadata["reason"], kind=metadata["kind"], before=metadata["before_config"],
                            after=body["proposed_config"], evidence=metadata, approval_id=intent["approval_id"])
    count = store.counts(wid, row["minute"], row["minute"] + 360)[0]
    return {"workflow": wid, "minute": row["minute"], "time_utc": datetime.fromtimestamp(row["minute"] * 60, timezone.utc).isoformat(),
            "decision": decision, "observed_next_six_hours": {
                **count, "pickup_rate": rate(count, "pickup_rate"), "engagement_rate": rate(count, "engagement_rate"),
                "limitation": "Descriptive follow-up; not a causal estimate"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--url", required=True)
    run.add_argument("--db", default=os.environ.get("CONTROLLER_DB"))
    run.add_argument("--report")
    run.add_argument("--test-crash-after-apply", action="store_true", help=argparse.SUPPRESS)
    for command in ("view", "why"):
        read = commands.add_parser(command)
        read.add_argument("--db", required=True)
        read.add_argument("--workflow", required=command == "why")
        if command == "why":
            read.add_argument("--at", help="ISO timestamp with an explicit timezone")
    args = parser.parse_args()
    if args.command != "run":
        if not Path(args.db).is_file():
            parser.error("The specified controller database does not exist")
        with Store(args.db) as store:
            result = explain(store, args.workflow, args.at) if args.command == "why" else summary(store, args.workflow)
        print(json.dumps(result, indent=2))
        return
    api = API(args.url)
    try:
        state = api.get("/sim/state")
        identity = hashlib.sha256((args.url + "|" + state["scenario"]).encode()).hexdigest()[:12]
        path = Path(args.db) if args.db else Path("state") / (identity + ".sqlite3")
        with writer_lock(path):
            if not args.db and path.exists():
                with Store(path) as old:
                    previous = old.get("last_state")
                    reset = previous and (previous["sim_minute"] > state["sim_minute"] or old.get("last_event_id", 0) > state["last_event_id"])
                if reset:
                    destination = path.with_name(path.stem + f".previous-{time.time_ns()}.sqlite3")
                    path.rename(destination)
            with Store(path) as store:
                Engine(store, api, args.test_crash_after_apply).run()
                result = summary(store)
                if args.report:
                    destination = Path(args.report)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    finally:
        api.close()


if __name__ == "__main__":
    main()
