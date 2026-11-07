"""Population decisions. No scenario files, simulator imports, or LLM winners."""
import copy
import json
import math
from statistics import NormalDist
from .evidence import compare, distribution, effective, interval, rate, exploration_weights
from .incidents import Incidents


class Learning:
    def __init__(self, store, api, governance, workflows, origin, end):
        self.store, self.api, self.gov = store, api, governance
        self.workflows, self.origin, self.end = workflows, origin, end
        days = max(1, math.ceil((end - origin) / 1440))
        self.looks = days * max(1, len(workflows))
        self.incident_z = NormalDist().inv_cdf(1 - .01 / (2 * self.looks * 24))
        self.incidents = Incidents(store, api, workflows)

    def initialize(self, workflow, current, now):
        wid = workflow["workflow_id"]
        if self.store.get("baseline:" + wid) is None:
            counts = self.store.counts(wid, 0, self.origin)[0]
            prompts = self.store.counts(wid, 0, self.origin, group="prompt_version")
            safe = [p for p in prompts if p["connected"] >= 200 and
                    interval(p["hallucinations"], p["connected"])[1] < .05]
            safe.sort(key=lambda p: (-(rate(p, "engagement_rate") or 0), p["arm"]))
            baseline = {"counts": counts, "known_safe_prompt": safe[0]["arm"] if safe else None}
            self.store.set("baseline:" + wid, baseline)
            self.store.audit(now, wid, "history_bootstrap", baseline)
        known = self.store.get("known_version:" + wid)
        if known is not None and current["version"] != known:
            history = self.api.get(f"/workflows/{wid}/config/history")
            edits = [h for h in history if h["version"] > known and h["actor"] == "supervisor"]
            if edits:
                self.gov.abandon(wid, now, "Supervisor changed configuration; old full-config intent is invalid")
                self.store.set("experiment:" + wid, None)
                previous = self.store.get("workflow:" + wid, {}).get("current", {}).get("config")
                voice_edit = False
                if previous:
                    before, after = effective(previous, "default", "voice"), effective(current["config"], "default", "voice")
                    voice_edit = sum(abs(before.get(v, 0) - after.get(v, 0)) for v in before.keys() | after.keys()) > 1e-6
                    voice_edit = voice_edit or previous.get("cohorts", []) != current["config"].get("cohorts", [])
                self.store.set("experiment_pause:" + wid, self.end if voice_edit else now + 1440)
                self.store.audit(now, wid, "supervisor_edit_observed", {"edits": edits, "action": "abort experiment and re-evaluate; safety detection remains active"})
        self.store.set("known_version:" + wid, current["version"])
        self.store.set("workflow:" + wid, {"workflow": workflow, "current": current,
            "cohorts": [{"id": "default", "where": {}}] + current["config"].get("cohorts", [])})

    def handle_applied(self, now):
        rows = self.store.db.execute("SELECT pid FROM proposals WHERE state='applied' AND handled=0").fetchall()
        for row in rows:
            op = self.gov.operation(row[0])
            wid, data = op["wid"], op["data"]
            with self.store.transaction():
                if data["kind"] == "voice_explore":
                    experiment = {"phase": "explore", "control": data["control"], "options": data["options"],
                                  "start": now, "version": op["applied_version"], "cohort": "default", "last_look": -1}
                    self.store.set("experiment:" + wid, experiment)
                elif data["kind"] in ("voice_promote", "voice_rollback"):
                    experiment = self.store.get("experiment:" + wid)
                    if experiment:
                        experiment.update(phase="promoted" if data["kind"] == "voice_promote" else "rolled_back",
                                          winner=data.get("winner"), monitor_start=now, last_look=-1)
                        self.store.set("experiment:" + wid, experiment)
                elif data["kind"] == "incident":
                    job = self.store.get("incident:" + wid)
                    job.update(state="verifying", applied=now, proposal_id=op["pid"])
                    self.store.set("incident:" + wid, job)
                    self.store.set("experiment:" + wid, None)
                    self.store.set("experiment_pause:" + wid, now + 1440)
                self.store.set("known_version:" + wid, op["applied_version"])
                snapshot = self.store.get("workflow:" + wid)
                if snapshot:
                    snapshot["current"] = {"version": op["applied_version"], "config": op["body"]["proposed_config"]}
                    self.store.set("workflow:" + wid, snapshot)
                self.store.db.execute("UPDATE proposals SET handled=1 WHERE pid=?", (op["pid"],))
                self.store.audit(now, wid, "change_effective", {"proposal_id": op["pid"], "version": op["applied_version"],
                    "kind": data["kind"], "reason": data["reason"], "before": data["before_config"], "after": op["body"]["proposed_config"],
                    "evidence": data, "approval_id": op["approval_id"]})

    def prompt_alarm(self, workflow, current, now):
        wid = workflow["workflow_id"]
        recent = self.store.counts(wid, max(self.origin, now - 180), now,
                                    prompt_version=current["config"]["prompt_version"])[0]
        historical = self.store.get("baseline:" + wid, {"counts": {"connected": 0, "hallucinations": 0}})["counts"]
        lo = interval(recent["hallucinations"], recent["connected"], self.incident_z)[0]
        hi = interval(historical["hallucinations"], historical["connected"], self.incident_z)[1]
        if not historical["connected"]:
            hi = .10  # Explicit absolute fallback when there is no usable historical reference.
        alarm = recent["connected"] >= 200 and recent["hallucinations"] / recent["connected"] > .06 and lo > hi + .01
        return {"alarm": alarm, "recent": recent, "historical": historical, "z": self.incident_z}

    def check_prompt(self, workflow, current, now):
        wid = workflow["workflow_id"]
        job = self.store.get("incident:" + wid)
        if job and job["state"] == "verifying":
            post = self.store.counts(wid, job["applied"], now, prompt_version=job["selected_prompt"])[0]
            if post["connected"] >= 200:
                flags = post["hallucinations"] / post["connected"]
                hist = self.store.get("baseline:" + wid)["counts"]
                primary = workflow["objective"]["primary"]
                delta = (rate(post, primary) or 0) - (rate(hist, primary) or 0)
                job.update(state="verified" if flags < .06 else "verification_failed", post=post, primary_delta=delta)
                self.store.set("incident:" + wid, job)
                self.store.audit(now, wid, "incident_" + job["state"], {"post": post, "primary_delta": delta,
                    "action": "Review performance regression" if delta < -.05 else "Continue monitoring"})
            else:
                return True
        alarm = self.prompt_alarm(workflow, current, now)
        if not alarm["alarm"]:
            return False
        prompt = current["config"]["prompt_version"]
        if not job or job["current_prompt"] != prompt or job["state"] in ("verified", "verification_failed"):
            job = {"state": "detected", "detected": now, "current_prompt": prompt,
                   "known_safe_prompt": self.store.get("baseline:" + wid)["known_safe_prompt"], "detection": alarm}
            self.gov.abandon(wid, now, "Population safety incident takes precedence over experiment")
            self.store.audit(now, wid, "hallucination_incident", job)
            self.store.set("incident:" + wid, job)
        job = self.incidents.fix(workflow, job, now)
        if job["state"] == "ready":
            target = copy.deepcopy(current["config"])
            target["prompt_version"] = job["selected_prompt"]
            self.gov.propose(workflow, current, target, now, "Restore a validated grounded prompt after population QA degradation",
                             "incident", {"detection": alarm, "validation": job["validations"], "expected_primary_delta": 0}, job["evidence"])
        return True

    def plan_caller(self, workflow, current, now):
        wid = workflow["workflow_id"]
        recent = self.store.counts(wid, max(self.origin, now - 180), now, group="caller_id")
        historical = {row["arm"]: row for row in self.store.counts(wid, 0, self.origin, group="caller_id")}
        weights = effective(current["config"], "default", "caller_id")
        for row in recent:
            caller, baseline = row["arm"], historical.get(row["arm"])
            if not baseline or baseline["dials"] < 400 or row["dials"] < 200 or weights.get(caller, 0) == 0:
                continue
            others = {key: sum(r[key] for r in recent if r["arm"] != caller) for key in ("dials", "connected")}
            lo = interval(baseline["connected"], baseline["dials"], self.incident_z)[0]
            hi = interval(row["connected"], row["dials"], self.incident_z)[1]
            other_lo = interval(others["connected"], others["dials"], self.incident_z)[0]
            if others["dials"] < 200 or hi + .03 >= lo or hi >= other_lo:
                continue
            remaining = {key: value for key, value in weights.items() if key != caller}
            if not remaining:
                continue
            active = self.gov.active(wid)
            if active and self.gov.operation(active[0])["data"]["kind"] in ("caller_rotate", "incident"):
                return True
            self.gov.abandon(wid, now, "Caller-ID degradation takes precedence over pending optimization")
            target = copy.deepcopy(current["config"])
            target["allocations"]["default"]["caller_id"] = distribution(remaining)
            gain = max(0, (rate(baseline, "pickup_rate") or 0) - (rate(row, "pickup_rate") or 0)) * weights[caller]
            self.gov.propose(workflow, current, target, now, f"Quarantine caller ID {caller}: degraded against history and concurrent alternatives",
                             "caller_rotate", {"caller": caller, "recent": row, "historical": baseline, "concurrent": others,
                                "expected_primary_delta": gain if workflow["objective"]["primary"] == "pickup_rate" else 0})
            return True
        return False

    def plan_voice(self, workflow, current, now):
        wid = workflow["workflow_id"]
        if workflow["objective"]["primary"] != "engagement_rate" or self.store.get("experiment_pause:" + wid, 0) > now:
            return
        voices = sorted(workflow["options"]["voice"])
        if len(voices) < 2 or self.gov.active(wid):
            return
        experiment = self.store.get("experiment:" + wid)
        if not experiment:
            if self.store.counts(wid, 0, now, cohort_id="default")[0]["connected"] < 200:
                return
            weights = effective(current["config"], "default", "voice")
            control = max(sorted(weights), key=weights.get)
            target = copy.deepcopy(current["config"])
            target["allocations"]["default"]["voice"] = exploration_weights(voices, control)
            for cohort in current["config"].get("cohorts", []):
                cid = cohort["id"]
                target["allocations"].setdefault(cid, {})["voice"] = effective(current["config"], cid, "voice")
            self.gov.propose(workflow, current, target, now, "Start a randomized voice comparison while retaining at least 80% incumbent traffic",
                             "voice_explore", {"control": control, "options": voices, "cohort": "default",
                                "expected_primary_delta": 0, "estimate": "Untried voices have no outcome estimate"})
            return
        day, hour = (now - self.origin) // 1440, ((now + 330) % 1440) // 60
        start = experiment.get("monitor_start", experiment["start"])
        if experiment["phase"] not in ("explore", "promoted") or hour != 11 or now - start < 1440 or experiment["last_look"] == day:
            return
        experiment["last_look"] = day
        self.store.set("experiment:" + wid, experiment)
        rows = {r["arm"]: r for r in self.store.counts(wid, max(start, now - 2880) if experiment["phase"] == "promoted" else start,
                                                     now, group="voice", cohort_id="default")}
        control = rows.get(experiment["control"])
        if not control:
            return
        guardrail = workflow["objective"]["guardrail"]["pickup_rate_max_drop"]
        comparisons = self.looks * (len(voices) - 1) * 2  # Reserve a second family for decay checks.
        results = {}
        if experiment["phase"] == "explore":
            for voice, observed in sorted(rows.items()):
                if voice != experiment["control"]:
                    results[voice] = compare(control, observed, "engagement_rate", guardrail, comparisons)
            winners = [voice for voice, evidence in results.items() if evidence["winner"]]
            if winners:
                winner = max(winners, key=lambda v: (results[v]["primary_delta"], v))
                target = copy.deepcopy(current["config"])
                target["allocations"]["default"]["voice"] = {winner: .8, experiment["control"]: .2}
                self.gov.propose(workflow, current, target, now, f"Promote voice {winner}: corrected evidence supports primary lift and pickup guardrail",
                    "voice_promote", {"winner": winner, "comparison": results[winner],
                                      "expected_primary_delta": results[winner]["primary_delta"]})
        else:
            winner = rows.get(experiment["winner"])
            if winner:
                result = compare(winner, control, "engagement_rate", guardrail, comparisons)
                results[experiment["control"]] = result
                if result["winner"]:
                    target = copy.deepcopy(current["config"])
                    target["allocations"]["default"]["voice"] = {experiment["control"]: 1}
                    self.gov.propose(workflow, current, target, now, "Roll back a decayed voice: retained incumbent now wins with guardrail respected",
                        "voice_rollback", {"winner": experiment["control"], "comparison": result, "expected_primary_delta": result["primary_delta"]})
        self.store.audit(now, wid, "experiment_look", {"phase": experiment["phase"], "cohort": "default", "comparisons": results})

    def decide(self, workflow, current, now):
        if not self.check_prompt(workflow, current, now) and not self.plan_caller(workflow, current, now):
            self.plan_voice(workflow, current, now)
