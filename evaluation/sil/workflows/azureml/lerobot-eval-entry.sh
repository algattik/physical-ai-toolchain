#!/usr/bin/env bash
# AzureML entry script for LeRobot inference/evaluation
# All configuration via environment variables set by submit-azureml-lerobot-eval.sh
set -euo pipefail

echo "=== LeRobot AzureML Inference ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || (cd "$SCRIPT_DIR/../../../.." && pwd))"

ensure_runtime_dependencies() {
  if python3 - <<'PY'
import importlib.util

modules = (
    "av",
    "azure.ai.ml",
    "azure.identity",
    "azure.storage.blob",
    "azureml.mlflow",
    "lerobot",
    "matplotlib",
    "mlflow",
    "pyarrow",
)
missing = []
for module in modules:
    try:
        spec = importlib.util.find_spec(module)
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        missing.append(module)
if missing:
    print("[ENTRY] Missing runtime modules: " + ", ".join(missing))
    raise SystemExit(1)
PY
  then
    return
  fi

  apt-get update -qq && apt-get install -y -qq ffmpeg git build-essential >/dev/null 2>&1
  pip install --quiet --break-system-packages uv==0.10.9

  local eval_project="${REPO_ROOT}/evaluation/sil/docker"
  local eval_venv="${LEROBOT_EVAL_VENV:-/opt/lerobot-eval-venv}"
  if [[ ! -f "${eval_project}/uv.lock" ]]; then
    echo "ERROR: LeRobot eval lockfile not found at ${eval_project}/uv.lock" >&2
    exit 1
  fi

  uv python install 3.12
  uv venv --python 3.12 "${eval_venv}"
  # shellcheck disable=SC1091
  source "${eval_venv}/bin/activate"
  uv export --frozen --no-hashes --no-emit-project --project "${eval_project}" \
    | uv pip install --no-cache-dir --no-deps -r -
}

ensure_runtime_dependencies

if [[ -n "${AZURE_ML_OUTPUT_eval_results:-}" ]]; then
  export OUTPUT_DIR="${AZURE_ML_OUTPUT_eval_results}"
fi

# HuggingFace auth
if [[ -n "${HF_TOKEN:-}" ]]; then
  python3 -c "import os; from huggingface_hub import login; login(token=os.environ['HF_TOKEN'], add_to_git_credential=False)"
fi

# Download model from AzureML registry if specified
if [[ -n "${AML_MODEL_NAME:-}" && "${AML_MODEL_NAME}" != "none" && -n "${AML_MODEL_VERSION:-}" && "${AML_MODEL_VERSION}" != "none" ]]; then
  echo "Downloading model from AzureML registry: ${AML_MODEL_NAME}:${AML_MODEL_VERSION}..."

  python3 "${REPO_ROOT}/evaluation/sil/scripts/download_aml_model.py"

  if [[ -f /tmp/aml_model_path.env ]]; then
    # shellcheck disable=SC2046
    export $(cat /tmp/aml_model_path.env | xargs)
    export POLICY_REPO_ID="${AML_MODEL_PATH}"
    echo "Using AzureML model at: ${POLICY_REPO_ID}"
  else
    echo "Error: Model download did not produce path file"
    exit 1
  fi
fi

# Download dataset from Azure Blob Storage if configured
if [[ -n "${BLOB_STORAGE_ACCOUNT:-}" && "${BLOB_STORAGE_ACCOUNT}" != "none" && -n "${BLOB_PREFIX:-}" && "${BLOB_PREFIX}" != "none" ]]; then
  echo "Downloading dataset from Azure Blob: ${BLOB_STORAGE_ACCOUNT}/${BLOB_STORAGE_CONTAINER}/${BLOB_PREFIX}..."

  python3 "${REPO_ROOT}/evaluation/sil/scripts/download_blob_dataset.py"

  if [[ -f /tmp/dataset_path.env ]]; then
    # shellcheck disable=SC2046
    export $(cat /tmp/dataset_path.env | xargs)
    echo "Dataset ready at: ${DATASET_DIR}"
  fi
fi

# Bootstrap MLflow tracking
if [[ "${MLFLOW_ENABLE:-false}" == "true" ]]; then
  echo "Configuring Azure ML MLflow tracking..."

  python3 "${REPO_ROOT}/evaluation/metrics/bootstrap_mlflow.py"

  if [[ -f /tmp/mlflow_config.env ]]; then
    # shellcheck disable=SC2046
    export $(cat /tmp/mlflow_config.env | xargs)
  fi
fi

# Run evaluation
echo "Starting LeRobot evaluation..."
mkdir -p "${OUTPUT_DIR}"

python3 "${REPO_ROOT}/evaluation/sil/scripts/run_evaluation.py"

echo "=== Evaluation Complete ==="

# Register model to Azure ML if requested
if [[ -n "${REGISTER_MODEL:-}" && "${REGISTER_MODEL}" != "none" ]]; then
  echo "=== Registering Model to Azure ML ==="
  python3 "${REPO_ROOT}/workflows/azureml/scripts/register_model.py"
  echo "=== Model Registration Complete ==="
fi
