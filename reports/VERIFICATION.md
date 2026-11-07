# Final verification record

Date: 8 November 2026. Main work was performed locally in the `feature/outcome-controller` branch. No remote publication, form submission, or client communication was performed.

- Full test suite: **31 tests passed**. Tests cover atomic chunk rollback after a real batch flush, replay/reopen, KPI sample/guardrail checks, policy limits, stricter client preferences, uncertain writes, supervisor races, paid-receipt recovery, alert detection, governed decay rollback, and historical `why` queries before local receipt reconciliation.
- `public_01`: completed through Bash `run.sh`; conclusion-rate lift +1.3% in the supplied grader; two neutral applied changes.
- `public_02`: completed through Bash `run.sh`; conclusion-rate lift +6.7%; two neutral and two beneficial applied changes. Prompt-incident MTTR: 390 simulated minutes. Six simulated credits used.
- `public_03`: completed through the Python entrypoint; 9,737,461 events processed, including history; 7,433,295 call rows equal materialized dial counts; server event high-water matches. Eight neutral and three beneficial changes, including three promotions. No change was classified as harmful in the final three public reports.
- Load controller wall time including history ingestion: 814.4 seconds for five simulated days, or 162.9 seconds/day. Complete-loop replay throughput: 11,956 events/sec. OS peak controller working set: 180.2 MiB. Simulator history generation: 278.6 seconds separately measured. Per-chunk parse/SQL rates exclude the final COMMIT/checkpoint and are explicitly labeled.
- Actual machine: Windows 10, four logical CPUs, 7.88 GiB physical RAM. Code and simulator files on the D: SATA HDD; final load database on the C: SATA SSD, with a 128 MiB SQLite page-cache budget and WAL/FULL durability. This is a shared desktop measurement, not verified execution on the evaluator's Linux machine.
- Earlier scale attempts encountered a simulator startup bound and a HDD random-IO slowdown. Those attempts are not represented as successful benchmarks. The protected simulator/scenarios were unchanged.
- Final-code hard-stop test: `reports/crash_recovery_final-recovery.json`. Exit 91 occurs immediately after remote apply and before local receipt commit; the same database resumes, completes, matches call/event counts, and has no duplicate remote applications.
- Statistical null calibration: zero false winners in 20,000 seeded independent fixed-look null pairs. This is not a clustered/sequential production guarantee.
- The submission's real audit query is saved in `reports/audit-example.json`. It uses only the controller database, not simulator logs.
- Original `sim/`, `scenarios/`, stakeholder memos, supplied simulator tests, and requirements were checked unchanged against the initial commit.

Runtime JSON labels for the small scenarios were refreshed using the same completed audit databases; their original measured timings were retained. The default database directory can be changed with `CONTROLLER_DB`, or `--state-root` in the evaluation harness. Raw database files and simulator runs are local scratch evidence, excluded from the source archive.

Known limits are in `SUBMISSION.md`: default-cohort scope, call-level approximate inference, limited counterfactual dry run, incomplete proactive approval forecasting, limited automated post-fix performance repair, and unverified target Linux execution. A passing public run is not a promise about hidden or production outcomes.
