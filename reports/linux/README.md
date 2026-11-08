# Hosted Ubuntu evidence

Measured on 8 November 2026 by [workflow run 42464947413](https://github.com/devgupta-9/agentic-universe-round2/actions/runs/42464947413) at source commit `45316650ff6e2724a02f099d20dc280a2d240999`. This identifies the benchmarked code, independently of later documentation or merge commits. The [PR workflow](https://github.com/devgupta-9/agentic-universe-round2/actions/runs/42465958611) passed its normal test/scenario/recovery checks too; the optional load job was skipped on that event.

All 40 tests passed separately on Python 3.10 and 3.12. Bash/Python syntax, executable entrypoint, and fatal lint checks passed. Scenario jobs used Python 3.10.22 on Ubuntu 24.04, with 2 logical CPUs and 8,317,927,424 physical RAM bytes (7.75 GiB) measured from the runner.

| Run | Events | Controller wall seconds | Complete-loop events/sec | Peak controller MiB | Aggregate conclusion-rate lift |
|---|---:|---:|---:|---:|---:|
| public_01 | 297,066 | 7.2 | 41,191 | 76.3 | -0.6% |
| public_02 | 324,332 | 8.5 | 38,096 | 79.7 | +4.4% |
| public_03 | 9,737,457 | 275.2 | 35,378 | 186.0 | +0.9% |
| after-apply recovery | 297,066 | 8.1 | 36,588 | 62.2 | Not graded |

Complete-loop throughput = all ingested events / controller wall seconds, including history ingestion, API/simulation work, decisions, commits, and any restart. It excludes baseline generation and simulator startup/history generation. Load simulator startup took another 75.9 seconds. Peak RSS is for the controller, excluding simulator and OS memory.

All regular scenarios used native `./run.sh`. The recovery run used the Python failpoint entrypoint: hard exit 91 after a successful remote apply, before local receipt commit, followed by a restart using the same SQLite database. Counts/checkpoints matched and remote applications were not duplicated. The full load had 7,433,295 call rows, equal to materialized dial counts.

## Saved files

- [verification.json](verification.json): host/source/timing/integrity measurements and test counts extracted from the downloaded artifacts; original artifact ZIP hashes are included for provenance.
- [linux-public_01.md](linux-public_01.md), [linux-public_02.md](linux-public_02.md), [linux-public_03.md](linux-public_03.md): unchanged supplied grader output. Their original JSON reports are included alongside them.
- `integration-environment.txt`, `load-environment.txt`: actual dependency versions captured by the corresponding jobs.

CI checks completion and integrity, without imposing a positive outcome-lift threshold. The negative development-scenario lift and individual workflow declines remain visible. No applied change was classified as harmful in these Linux reports, but that is distinct from aggregate outcomes. These shared hosted-runner measurements do not certify the evaluator's exact 4-vCPU / 8-GB machine, hidden scenarios, or production behavior. Windows results in the parent directory are separate historical measurements, not a controlled performance comparison.

GitHub workflow artifacts contain the fuller runtime JSON, recovery snapshot, controller/server logs, and JUnit results and are retained for seven days. The committed files here preserve the selected evidence beyond that window. Initial Python 3.10 downloads failed with HTTP 504; failed-job retries passed without a code change.
