"""Durable proposal outbox and approval reconciliation."""
import json
import os
import uuid
from .client import APIError, UncertainWrite
from .evidence import auto_check, changed_dimensions
from .store import encode


ACTIVE = ("prepared", "pending", "approved", "uncertain")


class Governance:
    def __init__(self, store, api, crash_after_apply=False):
        self.store, self.api, self.crash_after_apply = store, api, crash_after_apply
        store.db.executescript("""CREATE TABLE IF NOT EXISTS proposals(
            pid TEXT PRIMARY KEY,wid TEXT,state TEXT,mode TEXT,body TEXT,data TEXT,
            approval_id TEXT,created INTEGER,updated INTEGER,applied_version INTEGER,
            handled INTEGER DEFAULT 0);""")

    def operation(self, pid):
        row = dict(self.store.db.execute("SELECT * FROM proposals WHERE pid=?", (pid,)).fetchone())
        row["body"], row["data"] = json.loads(row["body"]), json.loads(row["data"])
        return row

    def active(self, wid):
        return self.store.db.execute("SELECT pid FROM proposals WHERE wid=? AND state IN (?,?,?,?)",
                                     (wid, *ACTIVE)).fetchone()

    def propose(self, workflow, current, target, now, reason, kind, data, evidence=None):
        wid = workflow["workflow_id"]
        dimensions = changed_dimensions(current["config"], target)
        if not dimensions or self.active(wid):
            return None
        policy = workflow["governance"]
        check = auto_check(policy["auto_apply"], current["config"], target)
        mode = "auto" if check["allowed"] and set(dimensions) <= {"schedule", "caller_id"} else "approval"
        if mode == "approval":
            used = self.store.db.execute("SELECT COUNT(*) FROM proposals WHERE wid=? AND mode='approval' AND created>?",
                                         (wid, now - 1440)).fetchone()[0]
            cap = policy["max_requests_per_24h"]
            if workflow.get("tenant_id") == "kestrel_finance":
                cap = min(cap, 2)  # Supervisor's stricter attention budget.
            hour = ((now + 330) % 1440) // 60
            start, end = policy["approver_hours"]
            if used >= cap or (kind != "incident" and not start <= hour < end - 1):
                return None
        active_since = now - 1440 * len(workflow.get("cadence", [1, 1, 1]))
        affected = self.store.db.execute("SELECT COUNT(*) FROM leads WHERE wid=? AND concluded=0 AND created>=?",
                                          (wid, active_since)).fetchone()[0]
        scope = "observed, unconcluded leads in recent campaign days; estimate, not dial eligibility"
        if workflow.get("mid_flight") == "next_campaign_only" and set(dimensions) & {"voice", "welcome_message", "caller_id", "cohorts"}:
            affected = 0
            scope = "new campaigns only; unknown future uploads, zero currently affected leads"
        pid = str(uuid.uuid4())
        local = dict(data, kind=kind, reason=reason, before_config=current["config"], policy_check=check)
        score = max(0.0, min(1.0, data.get("expected_primary_delta", 0) or 0))
        body = {"proposal_id": pid, "workflow_id": wid, "base_version": current["version"],
                "proposed_config": target, "change_summary": reason, "diff": {key: "changed" for key in dimensions},
                "affected_leads": affected, "dry_run": {"scope": scope, "affected_leads": affected,
                    "observed_evidence": data, "policy_check": check,
                    "limitation": "Observed comparisons only; untried options have no counterfactual estimate"},
                "impact_score": score, "rationale": reason + ". Impact score is estimated absolute primary-KPI gain, not a probability.",
                "expires_in_hours": policy.get("proposal_ttl_hours", 24)}
        if evidence:
            body["evidence"] = evidence
        with self.store.transaction():
            self.store.db.execute("INSERT INTO proposals(pid,wid,state,mode,body,data,created,updated) VALUES(?,?,'prepared',?,?,?,?,?)",
                                  (pid, wid, mode, encode(body), encode(local), now, now))
            self.store.audit(now, wid, "proposal_prepared", {"proposal_id": pid, "mode": mode, "body": body})
        return pid

    def _state(self, operation, state, now, detail=None, approval_id=None, version=None):
        with self.store.transaction():
            self.store.db.execute("UPDATE proposals SET state=?,updated=?,approval_id=COALESCE(?,approval_id),"
                                  "applied_version=COALESCE(?,applied_version) WHERE pid=?",
                                  (state, now, approval_id, version, operation["pid"]))
            self.store.audit(now, operation["wid"], "proposal_" + state,
                             {"proposal_id": operation["pid"], "approval_id": approval_id or operation["approval_id"],
                              "detail": detail, "version": version})

    def abandon(self, wid, now, reason):
        rows = self.store.db.execute("SELECT pid FROM proposals WHERE wid=? AND state IN (?,?,?,?)", (wid, *ACTIVE)).fetchall()
        for row in rows:
            self._state(self.operation(row[0]), "superseded", now, reason)

    def tick(self, workflows, now):
        rows = self.store.db.execute("SELECT pid FROM proposals WHERE state IN (?,?,?,?) ORDER BY created", ACTIVE).fetchall()
        for row in rows:
            op = self.operation(row[0])
            wid, body = op["wid"], op["body"]
            history = self.api.get(f"/workflows/{wid}/config/history")
            applied = next((h for h in history if h.get("proposal_id") == op["pid"]), None)
            if applied:
                self._state(op, "applied", now, applied, version=applied["version"])
                continue
            current = self.api.get(f"/workflows/{wid}/config")
            if current["version"] != body["base_version"]:
                self._state(op, "stale", now, {"current_version": current["version"]})
                continue
            try:
                if op["mode"] == "auto":
                    check = auto_check(workflows[wid]["governance"]["auto_apply"], current["config"], body["proposed_config"])
                    if not check["allowed"]:
                        self._state(op, "superseded", now, check)
                        continue
                    receipt = self.api.write("PUT", f"/workflows/{wid}/config", body)
                    if self.crash_after_apply:
                        os._exit(91)  # Explicit evaluation failpoint; restart without the CLI test flag.
                    self._state(op, "applied", now, receipt, version=receipt["version"])
                    continue
                aid = op["approval_id"]
                if not aid:
                    existing = self.api.get("/approvals", workflow_id=wid)
                    approval = next((a for a in existing if a["proposal_id"] == op["pid"]), None)
                    if approval is None:
                        approval = self.api.write("POST", "/approvals", body)
                    aid = approval["approval_id"]
                    self._state(op, approval["status"], now, approval, approval_id=aid)
                approval = self.api.get(f"/approvals/{aid}")
                if approval["status"] == "approved":
                    receipt = self.api.write("POST", f"/workflows/{wid}/apply", {"approval_id": aid})
                    if self.crash_after_apply:
                        os._exit(91)
                    self._state(op, "applied", now, receipt, approval_id=aid, version=receipt["version"])
                elif approval["status"] != op["state"]:
                    self._state(op, approval["status"], now, approval, approval_id=aid)
            except UncertainWrite as error:
                self._state(op, "uncertain", now, str(error), approval_id=op["approval_id"])
            except APIError as error:
                state = "stale" if error.status == 409 else "lapsed" if error.status == 410 else "rejected"
                self._state(op, state, now, error.body)
