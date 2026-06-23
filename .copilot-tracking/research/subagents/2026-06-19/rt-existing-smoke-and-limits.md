<!-- markdownlint-disable-file -->
# rt-existing-smoke: existing smoke/import tests + CI runner limits

Captured by parent (research subagent read-only).

## Verdict
One real smoke exists (Azure connectivity), NOT wired to CI. All test CI is CPU-only ubuntu-latest; the 14GB disk is the cap for container-build / cu12-torch smoke.

## Key findings
* training/rl/scripts/smoke_test_azure.py — CPU-only Azure/MLflow connectivity check (creds, workspace read, blob upload). Its TEST (training/tests/test_smoke_test_azure.py) mocks all Azure/MLflow via sys.modules and runs in CI, but the script's main() is never executed in CI (needs real Azure creds) → effectively manual.
* Test convention: training/tests/conftest.py:15-28 `load_training_module()` loads source by importlib WITHOUT importing the heavy package tree; heavy deps (isaaclab, azure, mlflow, lerobot) mocked via `sys.modules` injection (e.g. test_cli_args.py:238-240, evaluation/tests/conftest.py:10-17). So current "tests" are mocked unit tests, not runtime smoke.
* pytest-training.yml: ubuntu-latest, python 3.12, `uv sync --group dev`, then explicit `uv pip install torch==2.11.0` (:41), runs training/tests, 80% cov gate. test_export_policy.py uses real torch via importorskip.
* All pytest workflows run on ubuntu-latest (pytest-training/inference, evaluation, data-pipeline, dm-tools, dataviewer-backend, fuzz, go). No `self-hosted`, no larger runners (only dependabot uses ubuntu-slim).
* Runner limits (confirmed): ubuntu-latest = 4 vCPU, 16GB RAM, ~14GB free SSD, 6h job cap, NO GPU. The 14GB disk is the binding constraint for container-build and cu12-torch-wheel smoke.

## Gap to "runtime smoke"
Missing: any real training/eval step (isaaclab=GPU-only; lerobot CPU step needs cpu-torch+dataset), container-build validation (disk), explicit `@pytest.mark.smoke` job. Smoke is currently blended into mocked unit suites.

## Recommended baseline (fits 14GB)
Explicit smoke-cpu job: import smoke + a tiny torch CPU inference (~100MB torchvision model, <30s) + LeRobotDataset metadata validation (no video pull). Reserve container-build / cu12 for a path-gated heavier job with free-disk-space.
