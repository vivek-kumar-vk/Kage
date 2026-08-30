# finance-telemetry — shared local-model build harness

The `.scratch/finance-telemetry/` **effort** (F1/telemetry skin) is superseded and its
logs/prompts/reports are archived under `.scratch/_archive/finance-telemetry/`.

These scripts stay here because they are **shared infrastructure**, not tied to that
effort:

| File | Role |
|---|---|
| `run_phase.py` | phase runner + helpers; imported by `.scratch/finance-os-build/run_build.py` (`sys.path` insert + `import run_phase as rp`) |
| `run_task.py` | single-task driver |
| `bump.py` | progress-file bumper |
| `lm_chores.py` | local-model housekeeping calls |

Do not move or delete without updating `.scratch/finance-os-build/run_build.py:26-27`.
