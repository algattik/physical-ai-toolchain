"""
End-to-end test for the Azure ML IL (LeRobot/ACT) evaluation submission path.

Exercises ``submit-azureml-lerobot-eval.sh`` — the AzureML counterpart of the OSMO
LeRobot eval. The synthetic dataset is staged to blob and consumed via ``--from-blob``.
The AzureML eval script has no ``--builtin-policy`` option (unlike the OSMO one), so a
real policy source must be configured; the test skips otherwise:

- ``E2E_AML_LEROBOT_EVAL_POLICY_REPO_ID`` — a HuggingFace policy repo id, or
- ``E2E_AML_LEROBOT_EVAL_MODEL`` — an AzureML model ``name:version``.

```shell
uv run pytest -vv -s -m e2e tests/e2e/test_e2e_aml_il_eval.py
```
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e._aml import (
    AzureMLWorkspace,
    cancel_aml_job,
    resolve_aml_lerobot_eval_policy_source,
    submit_aml_lerobot_eval,
    wait_until_aml_completed,
    wait_until_aml_started,
)
from tests.e2e._common import log_e2e
from tests.e2e._lerobot_dataset import stage_synthetic_lerobot_dataset
from tests.e2e._mlflow import assert_aml_lerobot_eval_has_mlflow_tracking


@pytest.mark.e2e
@pytest.mark.usefixtures("aml_compute_target")
def test_aml_il_eval_e2e(
    request: pytest.FixtureRequest,
    aml_workspace: AzureMLWorkspace,
    repo_root: Path,
    storage_account: str,
) -> None:
    log_e2e("Starting AzureML IL (LeRobot) eval e2e test")
    # Resolve the policy source first so an unconfigured skip does not waste dataset staging.
    policy_source = resolve_aml_lerobot_eval_policy_source()
    dataset = stage_synthetic_lerobot_dataset(request, repo_root, storage_account)
    job = submit_aml_lerobot_eval(
        repo_root,
        aml_workspace,
        policy_source=policy_source,
        policy_type="act",
        eval_episodes=1,
        eval_batch_size=1,
        blob_storage_account=dataset.storage_account,
        blob_container=dataset.container,
        blob_prefix=dataset.prefix,
    )
    request.addfinalizer(lambda: cancel_aml_job(job, repo_root))

    log_e2e(f"Waiting for AzureML LeRobot eval job {job.name} to start")
    wait_until_aml_started(job, repo_root, timeout_minutes=15, poll_interval_seconds=30)
    log_e2e(f"Waiting for AzureML LeRobot eval job {job.name} to complete")
    wait_until_aml_completed(job, repo_root, timeout_minutes=30, poll_interval_seconds=30)
    log_e2e("Validating AzureML LeRobot eval MLflow tracking")
    assert_aml_lerobot_eval_has_mlflow_tracking(job, aml_workspace)
    log_e2e("AzureML LeRobot eval e2e test finished successfully")
