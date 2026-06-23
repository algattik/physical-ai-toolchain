# Prototype: Isaac RL CPU smoke for #809

CPU CI can catch the #809 regression class if it validates dependency resolution and installation with the Isaac Lab runtime interpreter. The real `training/rl` project now encodes that invariant with `requires-python = "==3.11.*"` and a linux x86_64 uv environment marker.

## Findings

| Check | Result |
| --- | --- |
| `cd training/rl && uv lock --check` | Passed with CPython 3.11.15 and the committed lock. |
| `uv lock --check --python 3.12` | Failed because Python 3.12 violates `project.requires-python ==3.11.*`. |
| `uv sync --frozen --python 3.12 --no-install-project --dry-run` | Failed for the same interpreter mismatch. |
| `uv export --frozen --python 3.12` | Did not fail; export alone is not a sufficient guard. |
| Minimal 3.12-only simulation | Passed under Python 3.12 and failed under Python 3.11 before GPU or simulation. |
| `shellcheck isaac-import-smoke.sh` | Passed. |
| `actionlint smoke-environments.yml` | Not run; `actionlint` was unavailable locally. |

## Artifacts

Artifacts live under `/Users/algattik/.copilot/session-state/cd8662d7-14d4-4481-afd2-f93c051bcc89/files/prototype/`:

- `isaac-import-smoke.sh`
- `smoke-environments.yml`
- `README.md`
- `evidence-*.txt`
- `sim-py312-only/`

## Container smoke recipe

The authored script runs `nvcr.io/nvidia/isaac-lab:2.3.2` on `linux/amd64`, sets `UV_PYTHON=/isaac-sim/kit/python/bin/python3`, mirrors `training/rl/scripts/train.sh`, installs the committed lock with `uv export --frozen --no-hashes --no-emit-project | uv pip install --no-deps --system`, then imports CPU-safe modules: `training.rl.cli_args`, launch wrappers, `skrl_mlflow_agent`, and `skrl_training`.

## RSL-RL import surface

`training/rl/scripts/rsl_rl/train.py` is not CPU-importable because it imports `AppLauncher` at line 21 and instantiates it at lines 90-91 during module import. Moving parser setup and `AppLauncher(args_cli)` into `main()` would make it importable like `skrl_training.py`, where the Isaac import is deferred until execution.

## Verdict

YES for interpreter and resolution regressions. GPU, Vulkan, Isaac task startup, and physics stepping still require a GPU-backed container job.
