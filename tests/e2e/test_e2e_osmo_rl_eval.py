"""
End-to-end test for the OSMO RL (Isaac Lab) evaluation/inference submission path.

Exercises ``submit-osmo-eval.sh``, which packages the eval code, exports the policy via
``export_policy.py``, and submits the Isaac Lab inference workflow. Evaluation requires a
trained checkpoint, so set ``E2E_OSMO_RL_EVAL_CHECKPOINT_URI`` to an MLflow
(``runs:/<id>/path`` or ``models:/<name>/<version>``), Azure Blob, or HTTP(S) checkpoint
URI produced by a prior training run; the test skips otherwise.

```shell
uv run pytest -vv -s -m e2e tests/e2e/test_e2e_osmo_rl_eval.py
```
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e._aml import AzureMLWorkspace
from tests.e2e._common import log_e2e
from tests.e2e._osmo import (
    assert_workflow_task_succeeded,
    cancel_osmo_workflow,
    resolve_osmo_isaac_eval_checkpoint,
    start_task_pod_log_stream,
    submit_osmo_isaaclab_eval,
    wait_until_osmo_completed,
    wait_until_osmo_started,
)

_ISAAC_INFERENCE_TASK_NAME = "isaac-inference"


@pytest.mark.e2e
@pytest.mark.usefixtures("ensure_gpu_nodes_available")
@pytest.mark.usefixtures("ensure_osmo_cli_available")
def test_osmo_rl_eval_e2e(
    request: pytest.FixtureRequest,
    aml_workspace: AzureMLWorkspace,
    repo_root: Path,
) -> None:
    log_e2e("Starting OSMO RL (Isaac Lab) eval e2e test")
    checkpoint_uri = resolve_osmo_isaac_eval_checkpoint()
    workflow = submit_osmo_isaaclab_eval(
        repo_root,
        aml_workspace,
        checkpoint_uri=checkpoint_uri,
        task="Isaac-Ant-v0",
        num_envs=4,
        max_steps=50,
    )
    request.addfinalizer(lambda: cancel_osmo_workflow(workflow, repo_root))

    log_stream = start_task_pod_log_stream(workflow, repo_root, _ISAAC_INFERENCE_TASK_NAME)
    request.addfinalizer(log_stream.stop)

    log_e2e(f"Waiting for OSMO eval workflow {workflow.workflow_id} to start")
    wait_until_osmo_started(workflow, repo_root)
    log_e2e(f"Waiting for OSMO eval workflow {workflow.workflow_id} to complete")
    wait_until_osmo_completed(workflow, repo_root, timeout_minutes=30)
    log_stream.stop()
    log_e2e("Validating OSMO eval workflow task success")
    assert_workflow_task_succeeded(workflow, repo_root, _ISAAC_INFERENCE_TASK_NAME)
    log_e2e("OSMO RL eval e2e test finished successfully")
