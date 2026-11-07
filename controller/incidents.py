"""Bounded prompt repair: observed safe fallback, then LLM hypotheses."""
from .client import APIError, UncertainWrite


class BudgetBlocked(Exception):
    pass


class PaidUnknown(Exception):
    pass


class Incidents:
    def __init__(self, store, api, workflows):
        self.store, self.api, self.workflows = store, api, workflows

    def save(self, wid, job):
        self.store.set("incident:" + wid, job)
        return job

    def paid(self, wid, job, path, body, cost, now):
        state = self.api.get("/sim/state")
        initial = self.store.get("initial_credit_budget", state["credits_remaining"])
        quota = max(18, initial * .75 / max(1, len(self.workflows)))
        spent = self.store.get("credits_reserved:" + wid, 0)
        if state["credits_remaining"] < cost + 8 or spent + cost > quota:
            raise BudgetBlocked("Keep eight global credits and a per-workflow incident allowance")
        with self.store.transaction():
            self.store.set("credits_reserved:" + wid, spent + cost)
            job["pending_paid"] = {"path": path, "body": body, "cost": cost}
            self.save(wid, job)
            self.store.audit(now, wid, "credit_reserved", job["pending_paid"])
        try:
            response = self.api.write("POST", path, body)
        except (UncertainWrite, APIError) as error:
            self.store.audit(now, wid, "paid_response_unknown", {"request": job["pending_paid"], "error": str(error)})
            raise PaidUnknown(str(error)) from error
        job.pop("pending_paid", None)
        job.setdefault("paid_receipts", []).append({"path": path, "response": response})
        self.save(wid, job)
        return response

    def fix(self, workflow, job, now):
        wid = workflow["workflow_id"]
        if job["state"] in ("ready", "verifying", "verified", "budget_blocked"):
            return job
        if job.get("retry_after", 0) > now:
            return job
        # Paid endpoints have no recovery/idempotency API. Lost receipts are charged
        # conservatively and never treated as validation evidence.
        if job.get("pending_paid"):
            lost = job.pop("pending_paid")
            if lost["path"] == "/validation/runs":
                job.setdefault("attempted", []).append(lost["body"]["prompt_version"])
            self.store.audit(now, wid, "credit_receipt_lost", lost)
            self.save(wid, job)
        job.setdefault("attempted", [])
        job.setdefault("validations", [])
        candidates = job.setdefault("candidates", [])
        threshold = max(.975, workflow["governance"]["min_validation_pass_rate"])
        for receipt in job.get("paid_receipts", []):
            response = receipt["response"]
            if receipt["path"] == "/llm/suggest-fixes":
                job["suggested"] = True
                candidates.extend(p["prompt_version"] for p in response["suggestions"] if p["prompt_version"] not in candidates)
            elif receipt["path"] == "/validation/runs":
                prompt = response["prompt_version"]
                if prompt not in job["attempted"]:
                    job["attempted"].append(prompt)
                    job["validations"].append(response)
                if response["pass_rate"] >= threshold and prompt != job["current_prompt"]:
                    job.update(state="ready", selected_prompt=prompt,
                               evidence={"validation_run_id": response["validation_run_id"]})
                    return self.save(wid, job)
        fallback = job.get("known_safe_prompt")
        if fallback and fallback != job["current_prompt"] and fallback not in candidates:
            candidates.append(fallback)
        try:
            while True:
                untried = [p for p in candidates if p not in job["attempted"] and p != job["current_prompt"]]
                if untried:
                    prompt = untried[0]
                    validation = self.paid(wid, job, "/validation/runs",
                                           {"workflow_id": wid, "prompt_version": prompt, "n": 600}, 6, now)
                    job["attempted"].append(prompt)
                    job["validations"].append(validation)
                    if validation["pass_rate"] >= threshold:
                        job.update(state="ready", selected_prompt=prompt,
                                   evidence={"validation_run_id": validation["validation_run_id"]})
                        self.store.audit(now, wid, "prompt_validated", {"prompt": prompt, "validation": validation,
                            "limitation": "Safety evidence only; engagement must be measured after application"})
                        return self.save(wid, job)
                    self.save(wid, job)
                    continue
                if job.get("suggested"):
                    job["state"] = "no_validated_fix"
                    return self.save(wid, job)
                suggestion = self.paid(wid, job, "/llm/suggest-fixes",
                                       {"workflow_id": wid, "problem": "Population hallucination-rate incident; propose grounded fixes"}, 3, now)
                job["suggested"] = True
                candidates.extend(p["prompt_version"] for p in suggestion["suggestions"] if p["prompt_version"] not in candidates)
                self.save(wid, job)
        except BudgetBlocked as error:
            job.update(state="budget_blocked", reason=str(error))
            self.store.audit(now, wid, "alert_credit_budget", {"reason": str(error), "action": "Review incident and remaining shared credits"})
        except PaidUnknown as error:
            job.update(state="uncertain", retry_after=now + 360, reason=str(error))
        return self.save(wid, job)
