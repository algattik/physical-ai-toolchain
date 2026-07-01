"""
End-to-end lifecycle test for the OSMO IL (LeRobot/ACT) train -> eval path.

Stages a synthetic dataset, submits a real OSMO training workflow that registers its
checkpoint under a unique AzureML model name, validates MLflow tracking and task success,
resolves the concrete registered model version (never ``latest``), then evaluates that
model against the same dataset via ``submit-osmo-lerobot-eval.sh``.

Set ``E2E_LEROBOT_EVAL_POLICY_REPO_ID`` (HuggingFace repo) or ``E2E_LEROBOT_EVAL_MODEL``
(AzureML ``name:version``) to skip training and evaluate a pre-existing policy — a fast
inner loop while fixing the eval path.

```shell
uv run pytest -vv -s -m e2e tests/e2e/test_e2e_osmo_il_lifecycle.py
```
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e._aml import AzureMLWorkspace, resolve_registered_model
from tests.e2e._common import e2e_name, log_e2e
from tests.e2e._lerobot_dataset import stage_synthetic_lerobot_dataset
from tests.e2e._mlflow import (
    assert_osmo_lerobot_eval_has_mlflow_tracking,
    assert_osmo_lerobot_training_has_mlflow_tracking,
)
from tests.e2e._osmo import (
    assert_workflow_task_succeeded,
    cancel_osmo_workflow,
    osmo_lerobot_policy_source_from_model,
    resolve_osmo_lerobot_eval_policy_override,
    start_task_pod_log_stream,
    submit_osmo_lerobot_eval,
    submit_osmo_lerobot_training,
    wait_until_osmo_completed,
    wait_until_osmo_started,
)

_LEROBOT_TRAIN_TASK_NAME = "lerobot-train"
_LEROBOT_EVAL_TASK_NAME = "lerobot-eval"


@pytest.mark.e2e
@pytest.mark.usefixtures("ensure_gpu_nodes_available")
@pytest.mark.usefixtures("ensure_osmo_cli_available")
def test_osmo_il_lifecycle_e2e(
    request: pytest.FixtureRequest,
    aml_workspace: AzureMLWorkspace,
    repo_root: Path,
    storage_account: str,
) -> None:
    log_e2e("Starting OSMO IL (LeRobot) lifecycle e2e test")
    policy_source = resolve_osmo_lerobot_eval_policy_override()
    dataset = stage_synthetic_lerobot_dataset(request, repo_root, storage_account)
    if policy_source is None:
        register_model_name = e2e_name("il-e2e-osmo-model")
        workflow = submit_osmo_lerobot_training(
            repo_root,
            aml_workspace,
            blob_url=dataset.blob_url,
            policy_type="act",
            training_steps=10,
            save_freq=5,
            batch_size=8,
            learning_rate="1e-4",
            log_freq=1,
            register_model_name=register_model_name,
        )
        request.addfinalizer(lambda: cancel_osmo_workflow(workflow, repo_root))
        log_stream = start_task_pod_log_stream(workflow, repo_root, _LEROBOT_TRAIN_TASK_NAME)
        request.addfinalizer(log_stream.stop)

        log_e2e(f"Waiting for OSMO LeRobot training workflow {workflow.workflow_id} to start")
        wait_until_osmo_started(workflow, repo_root)
        log_e2e(f"Waiting for OSMO LeRobot training workflow {workflow.workflow_id} to complete")
        wait_until_osmo_completed(workflow, repo_root, timeout_minutes=30)
        log_stream.stop()
        log_e2e("Validating OSMO LeRobot training MLflow tracking")
        assert_osmo_lerobot_training_has_mlflow_tracking(workflow, aml_workspace)
        log_e2e("Validating OSMO LeRobot training workflow task success")
        assert_workflow_task_succeeded(workflow, repo_root, _LEROBOT_TRAIN_TASK_NAME)
        model = resolve_registered_model(repo_root, aml_workspace, model_name=register_model_name)
        policy_source = osmo_lerobot_policy_source_from_model(model)
    else:
        log_e2e(f"Using pre-configured eval policy {policy_source.description} (training skipped)")

    eval_workflow = submit_osmo_lerobot_eval(
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
    request.addfinalizer(lambda: cancel_osmo_workflow(eval_workflow, repo_root))
    eval_log_stream = start_task_pod_log_stream(eval_workflow, repo_root, _LEROBOT_EVAL_TASK_NAME)
    request.addfinalizer(eval_log_stream.stop)

    log_e2e(f"Waiting for OSMO LeRobot eval workflow {eval_workflow.workflow_id} to start")
    wait_until_osmo_started(eval_workflow, repo_root)
    log_e2e(f"Waiting for OSMO LeRobot eval workflow {eval_workflow.workflow_id} to complete")
    wait_until_osmo_completed(eval_workflow, repo_root, timeout_minutes=30)
    eval_log_stream.stop()
    log_e2e("Validating OSMO LeRobot eval MLflow tracking")
    assert_osmo_lerobot_eval_has_mlflow_tracking(eval_workflow, aml_workspace)
    log_e2e("Validating OSMO LeRobot eval workflow task success")
    assert_workflow_task_succeeded(eval_workflow, repo_root, _LEROBOT_EVAL_TASK_NAME)
    log_e2e("OSMO LeRobot lifecycle e2e test finished successfully")
