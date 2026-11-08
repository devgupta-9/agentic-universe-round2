# CI and Linux verification

The [workflow](../.github/workflows/ci.yml) runs on pull requests to `main`, pushes to `main` or `ci/**`, and manual dispatch. It verifies the checked-out commit on GitHub-hosted Ubuntu 24.04. It never merges or deploys code.

## Checks

- **Tests:** Python 3.10 and 3.12 install `requirements-ci.txt`, check that `run.sh` is executable, validate Bash and Python syntax, check fatal Ruff errors, and run the complete pytest suite. Test results and dependency versions are uploaded for each interpreter.
- **Linux scenarios and recovery:** Python 3.10 runs `public_01` and `public_02` through the executable `./run.sh`. A separate run hard-stops immediately after a remote change is applied, then restarts against the same SQLite database. The supplied simulator grades both public scenarios.
- **Linux load benchmark:** the full `public_03` scenario, including its baseline and history, runs on pushes to `ci/linux-verification`. After merging, select **Actions → CI and Linux verification → Run workflow**, choose the desired branch, and enable `full_load` to repeat it. Routine main/PR runs omit this longer benchmark.

`scripts/verify_ci_reports.py` fails if a scenario is unfinished, the report came from another commit or OS, the wrong entrypoint ran, call counts disagree with materialized dial counts, the event checkpoint differs from the server, or remote changes were applied more than once. Recovery also requires evidence of a remote application before the interrupted process saved its local receipt.

Every third-party action is pinned to a commit. Workflow permissions are read-only and checkout does not retain Git credentials. No API keys or external LLM account are required.

## Review the evidence

Open the workflow run for the branch commit and inspect each job. The integration and load job summaries show source revision, total events, complete-loop throughput, controller peak memory, and measured CPU count. Download `linux-integration` and `linux-load` for runtime JSON, supplied grader output, controller/server logs, dependency versions, recovery evidence, and `ci-verification.json`. Artifacts are retained for seven days; save them before expiry if needed.

Generated evidence stays under ignored `ci-artifacts/`. The previously committed Windows results in `reports/` remain reproducible historical measurements. A failed scenario uploads the available logs even when verification cannot finish.

An Ubuntu runner confirms Linux execution. Its CPU/RAM configuration is measured in each runtime report; it does not certify performance on the evaluator's exact 4-vCPU / 8-GB machine. Grade reports describe the measured outcomes; CI completion does not impose an outcome-lift threshold or promise hidden-scenario performance.

## Repeat locally on Linux

With Python 3.10+ installed, run from the repository root:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-ci.txt
test -x run.sh
bash -n run.sh
python -m compileall -q controller scripts
python -m ruff check --select E9,F63,F7,F82 controller scripts tests
python -m pytest -q tests

python scripts/evaluate.py --scenario scenarios/public_01_dev.yaml \
  --name linux-public_01 --bash --root ci-artifacts/runs \
  --state-root ci-artifacts/state --report-root ci-artifacts/reports
python scripts/evaluate.py --scenario scenarios/public_02_incidents.yaml \
  --name linux-public_02 --bash --root ci-artifacts/runs \
  --state-root ci-artifacts/state --report-root ci-artifacts/reports
python scripts/evaluate.py --scenario scenarios/public_01_dev.yaml \
  --name linux-recovery --crash after-apply --no-grade \
  --root ci-artifacts/runs --state-root ci-artifacts/state \
  --report-root ci-artifacts/reports
python scripts/verify_ci_reports.py --report-root ci-artifacts/reports \
  --expected-commit "$(git rev-parse HEAD)" \
  --run linux-public_01 --run linux-public_02 --recovery linux-recovery
```

Use a clean committed checkout so the recorded source revision identifies the code being tested. For the full benchmark, use `scenarios/public_03_load.yaml`, `--name linux-public_03 --bash --startup-timeout 900`, and the same isolated directories, then verify with `--run linux-public_03`.
