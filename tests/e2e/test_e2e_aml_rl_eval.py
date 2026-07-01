"""
End-to-end test for the Azure ML RL (Isaac Lab) evaluation submission path.

Exercises ``submit-azureml-isaaclab-evaluation.sh``, the AzureML counterpart of the OSMO
Isaac Lab eval. Evaluation requires a registered model, so set ``E2E_AML_ISAAC_EVAL_MODEL``
to an AzureML model ``name:version`` produced by a prior training run; the test skips
otherwise.

```shell
uv run pytest -vv -s -m e2e tests/e2e/test_e2e_aml_rl_eval.py
```
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e._aml import (
    AzureMLWorkspace,
    cancel_aml_job,
    submit_aml_isaaclab_eval,
    wait_until_aml_completed,
    wait_until_aml_started,
)
from tests.e2e._common import log_e2e


@pytest.mark.e2e
@pytest.mark.usefixtures("aml_compute_target")
def test_aml_rl_eval_e2e(
    request: pytest.FixtureRequest,
    aml_workspace: AzureMLWorkspace,
    repo_root: Path,
) -> None:
    log_e2e("Starting AzureML RL (Isaac Lab) eval e2e test")
    job = submit_aml_isaaclab_eval(
        repo_root,
        aml_workspace,
        eval_episodes=2,
        num_envs=4,
    )
    request.addfinalizer(lambda: cancel_aml_job(job, repo_root))

    log_e2e(f"Waiting for AzureML Isaac Lab eval job {job.name} to start")
    wait_until_aml_started(job, repo_root, timeout_minutes=15, poll_interval_seconds=30)
    log_e2e(f"Waiting for AzureML Isaac Lab eval job {job.name} to complete")
    wait_until_aml_completed(job, repo_root, timeout_minutes=30, poll_interval_seconds=30)
    log_e2e("AzureML RL eval e2e test finished successfully")
