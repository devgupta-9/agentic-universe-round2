# Outcome controller implementation plan

**Goal:** Deliver a runnable, explainable controller with durable event ingestion, governed experiments, incident handling, public reports, and crash-recovery evidence.

**Architecture:** One synchronous Python process talks only to the simulator's HTTP API. SQLite holds normalized observations, time-bucketed counts, pending operations, experiments, credit reservations, and an append-only decision log. Statistical rules and policy checks are deterministic; the LLM is consulted only for detected prompt incidents.

**Tech stack:** Python 3.10+, existing httpx dependency, SQLite and the Python standard library. No new service or paid API.

## Decisions and alternatives

- Use Python + SQLite: the supplied tooling already uses Python and this deployment has one writer. In-memory dictionaries cannot satisfy restart safety. Postgres is a reasonable production migration but adds unnecessary local infrastructure.
- Read history through HTTP. Never import `sim`, inspect run files, or read scenario truth from controller code.
- Start with workflow/default-cohort voice experiments and retain a control after promotion. Defer welcome-message interactions and per-person timing rather than implement fifteen shallow capabilities.
- Use fixed, daily winner checks, minimum samples, multiple-comparison correction, and a separate guardrail check. Operational incidents may be detected hourly with conservative population thresholds.
- Persist intended external operations before sending them. Reconcile uncertain results rather than blindly retry mutation requests.
- Keep operational changes within actual API policy; customer-facing voice/prompt changes use human approvals. Supervisor edits invalidate old intents.
- Implement natively in this session, explaining each stage. The user's implementation go-ahead was “Lets do this!” after the Python/SQLite recommendation. No remote publication or submission is authorized.

## Files and ordered increments

- [ ] **1. Durable observations.** Add `controller/store.py`, `controller/__init__.py`, and `tests/test_store.py`. Interface: `Store.ingest(chunk_id, kind, events) -> int`, `Store.counts(wid, since, until, group=None, **filters) -> list[dict]`, `Store.get/set`, `Store.audit`. Prove unanswered calls count, replay does not double-count, parse failure rolls back both rows and checkpoint, and close/reopen preserves progress.
- [ ] **2. Evidence and policy.** Add `controller/evidence.py` and policy tests. Interface: count-to-rate helpers, corrected comparison, `changed_dimensions(old,new)`, and `auto_permitted(policy,old,new)`. Test small samples, guardrail harm, unsupported auto dimensions, and max-shift boundaries.
- [ ] **3. HTTP and recovery.** Add `controller/client.py`, `controller/governance.py`, and boundary tests. Streaming chunk reads, finite GET retries, durable mutation intents, proposal reconciliation, version conflicts, and an approval lifecycle. Test response loss after remote success and supervisor changes before apply.
- [ ] **4. Learning loop.** Add `controller/engine.py` with history bootstrap, voice exploration/promotion/control retention, decay monitoring, caller-ID detection, and bounded incident/validation jobs. All decisions carry actual counts and explicit uncertainty. Test that observations from unrun or unapproved arms never become evidence.
- [ ] **5. Runnable and queryable.** Add `controller/__main__.py`, minimal audit/supervisor commands, and update `run.sh`. One automatic entrypoint until the scenario finishes. Persist advance intents and ingest outstanding chunks on restart. Check real HTTP execution and the Bash entrypoint.
- [ ] **6. Evidence and documentation.** Add a subprocess-based evaluation/crash harness and `SUBMISSION.md`. Run dev, incidents, and load scenarios, retain grade reports and measured controller resource use, and demonstrate a kill/restart. Explain all stakeholder conflicts and deliberate cuts. Preserve honest local commit history.

## Verification and review focus

- Use tests before each behavior and inspect the expected failure before implementing it.
- Review event/checkpoint atomicity, pending approvals after a kill, successful remote writes with lost responses, supervisor version conflicts, and credit consumption after uncertain responses.
- Do not modify `sim/`, `scenarios/`, stakeholder memos, or the supplied tests.
- Distinguish Windows/Python verification, Bash entrypoint verification, and any Linux or target-hardware evidence actually available.
- Run the full tests after meaningful stages. Review and commit only the intended paths after each coherent increment. Keep unknown work intact.

This plan is a working record; measured outcomes and limitations belong in the final submission, not invented targets.
