"""
End-to-end lifecycle test for the OSMO RL (Isaac/SKRL) train -> eval path.

Submits a real OSMO training workflow that registers its checkpoint under a unique
AzureML model name, validates MLflow tracking and task success, resolves the concrete
registered model version (never ``latest``), then evaluates the ``models:/<name>/<version>``
checkpoint via ``submit-osmo-eval.sh``.

Set ``E2E_OSMO_RL_EVAL_CHECKPOINT_URI`` to skip training and evaluate a pre-existing
checkpoint — a fast inner loop while fixing the eval path.

```shell
uv run pytest -vv -s -m e2e tests/e2e/test_e2e_osmo_rl_lifecycle.py
```
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e._aml import AzureMLWorkspace, resolve_registered_model
from tests.e2e._common import e2e_name, log_e2e
from tests.e2e._mlflow import assert_osmo_workflow_has_mlflow_tracking
from tests.e2e._osmo import (
    assert_workflow_task_succeeded,
    cancel_osmo_workflow,
    resolve_osmo_isaac_eval_checkpoint_override,
    start_task_pod_log_stream,
    submit_osmo_isaaclab_eval,
    submit_osmo_training,
    wait_until_osmo_completed,
    wait_until_osmo_started,
)

_TASK = "Isaac-Velocity-Rough-Anymal-C-v0"
_ISAAC_TRAINING_TASK_NAME = "isaac-training"
_ISAAC_INFERENCE_TASK_NAME = "isaac-inference"


@pytest.mark.e2e
@pytest.mark.usefixtures("ensure_gpu_nodes_available")
@pytest.mark.usefixtures("ensure_osmo_cli_available")
def test_osmo_rl_lifecycle_e2e(
    request: pytest.FixtureRequest,
    aml_workspace: AzureMLWorkspace,
    repo_root: Path,
) -> None:
    log_e2e("Starting OSMO RL (Isaac Lab) lifecycle e2e test")
    checkpoint_uri = resolve_osmo_isaac_eval_checkpoint_override()
    if checkpoint_uri is None:
        register_model_name = e2e_name("rl-e2e-osmo-model")
        workflow = submit_osmo_training(
            repo_root,
            task=_TASK,
            max_iterations=10,
            num_envs=64,
            register_model_name=register_model_name,
        )
        request.addfinalizer(lambda: cancel_osmo_workflow(workflow, repo_root))
        log_stream = start_task_pod_log_stream(workflow, repo_root, _ISAAC_TRAINING_TASK_NAME)
        request.addfinalizer(log_stream.stop)

        log_e2e(f"Waiting for OSMO training workflow {workflow.workflow_id} to start")
        wait_until_osmo_started(workflow, repo_root)
        log_e2e(f"Waiting for OSMO training workflow {workflow.workflow_id} to complete")
        wait_until_osmo_completed(workflow, repo_root, timeout_minutes=30)
        log_stream.stop()
        log_e2e("Validating OSMO training MLflow tracking")
        assert_osmo_workflow_has_mlflow_tracking(workflow, aml_workspace)
        log_e2e("Validating OSMO training workflow task success")
        assert_workflow_task_succeeded(workflow, repo_root, _ISAAC_TRAINING_TASK_NAME)
        model = resolve_registered_model(aml_workspace, repo_root, model_name=register_model_name)
        checkpoint_uri = f"models:/{model.name}/{model.version}"
    else:
        log_e2e(f"Using pre-configured eval checkpoint {checkpoint_uri} (training skipped)")

    eval_workflow = submit_osmo_isaaclab_eval(
        repo_root,
        aml_workspace,
        checkpoint_uri=checkpoint_uri,
        task=_TASK,
        num_envs=4,
        max_steps=50,
    )
    request.addfinalizer(lambda: cancel_osmo_workflow(eval_workflow, repo_root))
    eval_log_stream = start_task_pod_log_stream(eval_workflow, repo_root, _ISAAC_INFERENCE_TASK_NAME)
    request.addfinalizer(eval_log_stream.stop)

    log_e2e(f"Waiting for OSMO eval workflow {eval_workflow.workflow_id} to start")
    wait_until_osmo_started(eval_workflow, repo_root)
    log_e2e(f"Waiting for OSMO eval workflow {eval_workflow.workflow_id} to complete")
    wait_until_osmo_completed(eval_workflow, repo_root, timeout_minutes=30)
    eval_log_stream.stop()
    log_e2e("Validating OSMO eval workflow task success")
    assert_workflow_task_succeeded(eval_workflow, repo_root, _ISAAC_INFERENCE_TASK_NAME)
    log_e2e("OSMO RL lifecycle e2e test finished successfully")
