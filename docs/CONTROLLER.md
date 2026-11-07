# Outcome Ledger: running and understanding the controller

The provided simulator is unchanged. The implementation is in `controller/`. It uses HTTP, httpx, and a single-writer SQLite database. There is no real LLM account or additional stateful service to configure.

## Run

Install the supplied requirements in a Python 3.10+ environment. Start a fresh simulator in one terminal:

```sh
python -m sim serve --scenario scenarios/public_01_dev.yaml --run-dir runs/my-world
```

Then, with that Python environment active:

```sh
./run.sh http://127.0.0.1:8700
```

`run.sh` resolves its own directory and runs until the scenario finishes. `PYTHON` may select an interpreter, and `CONTROLLER_DB` may select a database. Otherwise a persistent database is selected under `state/` by the server URL and scenario name. Restart against the same running simulator and same database. Restarting the simulator creates a different world; use a fresh database. The default detects clear clock/event regressions and preserves the old file under a new name before starting fresh. The API does not expose an immutable run ID, so identical-looking world resets cannot always be distinguished.

Windows PowerShell equivalent:

```powershell
.\.venv\Scripts\python.exe -m controller run --url http://127.0.0.1:8700 --db state/my-controller.sqlite3
```

## What each file does

| File | Responsibility |
|---|---|
| `store.py` | Stream observations into bounded batches; commit observations and checkpoint together; maintain raw call facts and time-bucketed counts. |
| `client.py` | Retry reads finitely; never blindly retry an uncertain write. |
| `evidence.py` | Rates, confidence bounds, deterministic comparisons, cohort matching, and auto-apply policy checks. |
| `governance.py` | Persist intent, submit/reconcile approval, check version/policy, apply, and reconcile lost replies. |
| `incidents.py` | Reserve credits, validate a historically safe fallback, or ask the simulated LLM for hypotheses. |
| `learning.py` | Conservative voice experiments, default-cohort caller-ID quarantine, prompt verification, and supervisor ownership. |
| `engine.py` | Ingest, reconcile, decide, and advance; track controller health. |
| `__main__.py` | Run, inspect the consolidated view, or explain a configuration change. |

## Query your own records

```sh
python -m controller view --db state/my-controller.sqlite3
python -m controller view --db state/my-controller.sqlite3 --workflow ks_cancel
python -m controller why --db state/my-controller.sqlite3 --workflow ks_cancel --at 2027-01-07T20:00:00+05:30
```

The view combines current configuration, shared cohort definitions, experiment state, incidents, proposals, and recent decisions. The `why` command returns the recorded reason, proposal and approval IDs, before/after settings when the controller made the change, and descriptive six-hour follow-up counts. Supervisor intent or a human's legal identity is unavailable from the API; we do not invent it.

## Verify and reproduce reports

```sh
python -m pytest -q tests
python scripts/evaluate.py --scenario scenarios/public_01_dev.yaml --name public_01 --bash
python scripts/evaluate.py --scenario scenarios/public_02_incidents.yaml --name public_02 --bash
python scripts/evaluate.py --scenario scenarios/public_03_load.yaml --name public_03 --startup-timeout 900
python scripts/evaluate.py --scenario scenarios/public_01_dev.yaml --name crash_recovery --crash after-apply --no-grade
python scripts/check_statistics.py
```

The harness creates unique run directories; it never deletes an existing run. It launches and stops only its own subprocesses. Only the provided baseline/grade CLI reads simulator run files. The controller uses only HTTP and its own SQLite file. Resource measurements describe this host and separate simulator startup from controller wall time; a Windows/Bash run does not establish Linux behavior.

## Practical failure handling

- **Database locked:** another controller may own that database; do not start a second writer. The operating-system writer lock is released after a crash.
- **HTTP outage or uncertain advance:** keep the simulator running. The checkpoint, pending intent, and proposal IDs remain durable. Restart the controller; it checks the server clock and history before continuing. The API's clock-advance endpoint has no idempotency key, so an advance still in flight is handled by stopping rather than guessing.
- **Stale proposal:** no overwrite. The old intent becomes terminal and later decisions use current configuration and fresh evidence.
- **Lost paid receipt:** the cost remains reserved. Saved receipts are reused; missing validation receipts are never presented as evidence.
- **Credit or prompt-verification alert:** inspect the incident in the consolidated view. Safety validation does not establish engagement quality. The current implementation alerts on a large post-fix primary regression; automatic search after that alert is limited.

## What changed during development

The first uncommitted integrated experiment allocated 50% of traffic to alternatives and restarted optimization after a supervisor edit. The incident grader classified two exploratory changes as harmful. We retained those reports under `reports/initial/`, reduced unknown exposure to at most 20%, used exactly representable weights to avoid normalization drift, and stopped voice exploration after a material supervisor voice edit. We did not weaken the winner or guardrail tests to force a promotion.

## Storage measurements

SQLite uses a 128 MiB page-cache budget and keeps WAL/FULL durability. The scale investigation found severe random-IO stalls on the D: SATA HDD with the small default cache. The successful scale measurement records its temporary database on the C: SATA SSD, while code and simulator files remain on D:. Use the evaluation harness --state-root option to choose a durable volume explicitly; this is a benchmark storage choice, not an external database service.

Per-chunk ingestion rates measure streaming, parsing, and SQL work before COMMIT; they exclude the final fsync/checkpoint. The view also reports complete-loop replay throughput using total events divided by full controller wall time. The scale report uses the outer harness timing for that conservative end-to-end rate.
