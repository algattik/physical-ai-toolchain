#!/usr/bin/env bash
set -Eeuo pipefail

# shellcheck disable=SC2154  # exit_code is assigned in the trap body itself.
trap 'exit_code=$?; echo "ERROR: command failed (line ${LINENO}): ${BASH_COMMAND} (exit ${exit_code})" >&2' ERR

retry_cmd() {
  local max_attempts="$1"
  shift
  local attempt=1
  while true; do
    if "$@"; then
      return 0
    fi
    if [ "${attempt}" -ge "${max_attempts}" ]; then
      echo "ERROR: command failed after ${attempt} attempts: $*" >&2
      return 1
    fi
    attempt=$((attempt + 1))
    echo "WARN: retry ${attempt}/${max_attempts}: $*" >&2
  done
}

if [ -d "${DATASET_PATH}" ] && [ -n "$(ls -A "${DATASET_PATH}" 2>/dev/null)" ]; then
  echo "--- using existing local dataset at ${DATASET_PATH} ---"
  ls -lh "${DATASET_PATH}/" | head
elif [ -n "${BLOB_URL:-}" ]; then
  echo "--- downloading dataset from Azure Blob ---"
  mkdir -p "${DATASET_PATH}"
  export DEBIAN_FRONTEND=noninteractive
  retry_cmd 3 apt-get update -qq
  retry_cmd 3 apt-get install -y --no-install-recommends curl >/dev/null
  pip install --quiet azure-storage-blob azure-identity
  python3 /tmp/download_blob.py
  echo "--- dataset download complete ---"
  ls -lh "${DATASET_PATH}/" | head
else
  echo "ERROR: no local dataset at ${DATASET_PATH} and BLOB_URL is not set" >&2
  exit 1
fi

if [ -n "${RUN_ID_OVERRIDE:-}" ]; then
  RUN_ID="${RUN_ID_OVERRIDE}"
  echo "RUN_ID_OVERRIDE set: reusing existing output dir ${RUN_ID}"
else
  RUN_ID="${WF_ID:-run-$(date -u +%Y%m%d-%H%M%S)}"
fi
OUTPUT_DIR="${OUTPUT_ROOT}/${RUN_ID}"
mkdir -p "${OUTPUT_DIR}"

if [ "${RESUME:-false}" = "true" ]; then
  RESUME_FLAG="--resume"
  LATEST_CKPT="$(ls -1d ${OUTPUT_DIR}/checkpoint-* 2>/dev/null | sort -t- -k2 -n | tail -1 || true)"
  if [ -z "${LATEST_CKPT}" ]; then
    echo "ERROR: RESUME=true but no checkpoint-* found in ${OUTPUT_DIR}" >&2
    exit 1
  fi
  echo "Resuming from checkpoint: ${LATEST_CKPT}"
else
  RESUME_FLAG="--no-resume"
fi

echo "========================================================"
echo " LeRobot / GR00T fine-tune"
echo "   node:        $(hostname)"
echo "   date (utc):  $(date -u)"
echo "   dataset:     ${DATASET_PATH}"
echo "   output:      ${OUTPUT_DIR}"
echo "   base model:  ${BASE_MODEL}"
echo "   data config: ${DATA_CONFIG}"
echo "   batch_size:  ${BATCH_SIZE}"
echo "   max_steps:   ${MAX_STEPS}"
echo "========================================================"

nvidia-smi
df -h /dev/shm /outputs || true
echo "--- dataset ---"; ls -1 "${DATASET_PATH}" | head
echo "--- dataset/meta ---"; ls -1 "${DATASET_PATH}/meta" | head

export DEBIAN_FRONTEND=noninteractive
retry_cmd 3 apt-get update -qq
retry_cmd 3 apt-get install -y --no-install-recommends \
  git git-lfs build-essential cmake ffmpeg \
  libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev \
  libvulkan-dev ca-certificates wget curl >/dev/null

cd /workspace || cd /tmp
if [ ! -d Isaac-GR00T ]; then
  echo "--- cloning Isaac-GR00T ---"
  retry_cmd 3 git clone https://github.com/NVIDIA/Isaac-GR00T.git
fi
cd Isaac-GR00T
git lfs install --system || true

echo "--- checking out ref: ${ISAAC_GROOT_REF} ---"
if ! git checkout "${ISAAC_GROOT_REF}"; then
  echo "WARN: initial checkout failed; fetching ref then retrying" >&2
  git fetch origin "${ISAAC_GROOT_REF}" --depth 1 || true
  git checkout "${ISAAC_GROOT_REF}"
fi

# GR00T N1.7+ pins python==3.10.*; the default pytorch image ships
# python 3.11. Create a conda env when the active interpreter is
# not 3.10 so the editable install can resolve.
if [ -f "gr00t/experiment/launch_finetune.py" ]; then
  CURRENT_PY="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [ "${CURRENT_PY}" != "3.10" ] && command -v conda >/dev/null 2>&1; then
    echo "[setup] GR00T N1.7 requires Python 3.10 (active: ${CURRENT_PY}); creating conda env"
    conda create -y -n gr00t-py310 python=3.10
    # shellcheck disable=SC1091
    source /opt/conda/etc/profile.d/conda.sh
    conda activate gr00t-py310
    pip install --upgrade pip setuptools wheel
    pip install azure-identity azure-storage-blob
  fi
fi

pip install --upgrade pip setuptools wheel
pip install "uv==0.11.13"

# --- Python dependencies from the committed uv.lock ---
# training/vla/uv.lock is the single dependency surface Dependabot tracks. It
# resolves GR00T N1.7's full transitive tree for linux x86_64 / python 3.10:
# torch and torchvision come from the CUDA 12.8 index, and the +cu128 wheels
# carry both Hopper (sm_90) and Blackwell (sm_100/sm_120) kernels, so one lock
# serves every supported GPU with no per-architecture install branch. flash-attn
# is a prebuilt cp310 wheel. Installing the exported lock with --no-deps means
# pip never re-resolves, so the torch-backtracking download thrash cannot recur.
# The +cu128 local version is published only on the PyTorch index, so
# --index-strategy unsafe-best-match lets uv reach it past PyPI; this is safe
# because every requirement is exactly pinned and --no-deps is set.
PROJECT_DIR=/tmp/vla-project
mkdir -p "${PROJECT_DIR}"
base64 -d /tmp/pyproject.toml.b64 > "${PROJECT_DIR}/pyproject.toml"
base64 -d /tmp/uv.lock.b64 > "${PROJECT_DIR}/uv.lock"
uv export --frozen --no-hashes --no-emit-project --project "${PROJECT_DIR}" \
  | uv pip install --python "$(command -v python)" --no-cache-dir --no-deps \
      --index-strategy unsafe-best-match \
      --extra-index-url https://download.pytorch.org/whl/cu128 \
      -r -

# Install GR00T's own source as an editable package without re-resolving its
# dependencies; the lock above already pins the entire tree.
pip install -e . --no-deps

python -c "import torch, torchvision, flash_attn; print('torch=', torch.__version__, 'tv=', torchvision.__version__, 'cuda=', torch.version.cuda, 'flash_attn=', flash_attn.__version__)"

if [ -n "${DATA_CONFIG_B64:-}" ]; then
  DATA_CFG_PY="$(pwd)/gr00t/experiment/data_config.py"
  echo "${DATA_CONFIG_B64}" | base64 -d >> "${DATA_CFG_PY}"
  echo "  patched ${DATA_CFG_PY} with custom data config (${DATA_CONFIG})"
fi

if [ -n "${MODALITY_CONFIG_B64:-}" ]; then
  echo "${MODALITY_CONFIG_B64}" | base64 -d > /tmp/modality_config.py
  echo "  wrote modality config to /tmp/modality_config.py"
fi

python -c "import torch; p=torch.cuda.get_device_properties(0); print(f'[preflight] GPU: {p.name}  total={p.total_memory/1024**3:.2f} GiB  sm={p.major}.{p.minor}')"

echo "--- starting training ---"
if [ -f "scripts/gr00t_finetune.py" ]; then
  echo "  N1.5/N1.6 branch: using scripts/gr00t_finetune.py"
  python scripts/gr00t_finetune.py \
    --dataset-path "${DATASET_PATH}" \
    --output-dir "${OUTPUT_DIR}" \
    --data-config "${DATA_CONFIG}" \
    --batch-size "${BATCH_SIZE}" \
    --max-steps "${MAX_STEPS}" \
    --num-gpus 1 \
    --save-steps "${SAVE_STEPS}" \
    --base-model-path "${BASE_MODEL}" \
    --no-tune-llm \
    --tune-visual \
    --tune-projector \
    --tune-diffusion-model \
    ${RESUME_FLAG} \
    --dataloader-num-workers "${DATALOADER_WORKERS}" \
    --report-to tensorboard \
    --embodiment-tag "${EMBODIMENT_TAG}"
elif [ -f "gr00t/experiment/launch_finetune.py" ]; then
  echo "  N1.7+ branch: using gr00t/experiment/launch_finetune.py"
  FINETUNE_ARGS=(
    --base_model_path "${BASE_MODEL}"
    --dataset_path "${DATASET_PATH}"
    --embodiment_tag "${EMBODIMENT_TAG}"
    --output_dir "${OUTPUT_DIR}"
    --max_steps "${MAX_STEPS}"
    --save_steps "${SAVE_STEPS}"
    --global_batch_size "${BATCH_SIZE}"
    --dataloader_num_workers "${DATALOADER_WORKERS}"
    --num_gpus 1
    --tune_diffusion_model
    --tune_projector
    --save_total_limit 5
    --warmup_ratio 0.05
    --weight_decay 1e-5
    --learning_rate 1e-4
  )
  if [ -f "/tmp/modality_config.py" ]; then
    FINETUNE_ARGS+=(--modality_config_path /tmp/modality_config.py)
  fi
  export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
  python gr00t/experiment/launch_finetune.py "${FINETUNE_ARGS[@]}"
else
  echo "ERROR: no finetune script found in Isaac-GR00T" >&2; exit 1
fi

echo "--- training done ---"
du -sh "${OUTPUT_DIR}"
ls -lh "${OUTPUT_DIR}" | head

if [ "${AZURE_UPLOAD:-false}" = "true" ]; then
  if [ -z "${AZUREML_WORKSPACE_NAME:-}" ] || [ -z "${AZURE_SUBSCRIPTION_ID:-}" ]; then
    echo "AZURE_UPLOAD=true but AZUREML_WORKSPACE_NAME or AZURE_SUBSCRIPTION_ID not set. Skipping." >&2
  else
    echo "--- mirroring run to Azure ML ---"
    pip install --quiet \
      'mlflow>=2.10,<3' \
      'azureml-mlflow>=1.55' \
      'azure-identity>=1.17' \
      'azure-ai-ml>=1.20'
    RUN_ID="${RUN_ID}" OUTPUT_DIR="${OUTPUT_DIR}" \
      python /tmp/mlflow_log.py || \
      echo "WARN: Azure ML mirror failed; local run at ${OUTPUT_DIR} is unaffected." >&2
  fi
fi

if [ -n "${ACR_REGISTRY:-}" ]; then
  echo "--- pushing model to ACR: ${ACR_REGISTRY} ---"
  ORAS_VERSION="1.2.0"
  curl -sLO "https://github.com/oras-project/oras/releases/download/v${ORAS_VERSION}/oras_${ORAS_VERSION}_linux_amd64.tar.gz"
  tar xzf "oras_${ORAS_VERSION}_linux_amd64.tar.gz" -C /usr/local/bin/ oras
  chmod +x /usr/local/bin/oras
  rm -f "oras_${ORAS_VERSION}_linux_amd64.tar.gz"

  pip install --quiet azure-identity
  ACR_HOST="${ACR_REGISTRY}.azurecr.io"
  az login --identity --allow-no-subscriptions 2>/dev/null && \
    az acr login --name "${ACR_REGISTRY}" 2>/dev/null || {
    echo "  az acr login unavailable; authenticating oras via workload identity token"
    ACR_REFRESH=$(python3 -c "import requests; from azure.identity import DefaultAzureCredential; aad=DefaultAzureCredential().get_token('https://management.azure.com/.default').token; r=requests.post('https://${ACR_HOST}/oauth2/exchange', data={'grant_type':'access_token','service':'${ACR_HOST}','access_token':aad}); r.raise_for_status(); print(r.json()['refresh_token'])")
    printf '%s' "${ACR_REFRESH}" | oras login "${ACR_HOST}" --username 00000000-0000-0000-0000-000000000000 --password-stdin
    unset ACR_REFRESH
  }

  FINAL_CKPT="$(ls -1d ${OUTPUT_DIR}/checkpoint-* 2>/dev/null | sort -t- -k2 -n | tail -1 || true)"
  if [ -z "${FINAL_CKPT}" ]; then
    echo "WARN: no checkpoint-* dirs found; skipping ACR push" >&2
  else
    STEP="$(basename "${FINAL_CKPT}" | sed 's/checkpoint-//')"
    MODEL_REPO="${ACR_MODEL_REPO:-models/groot}"
    TAG="${RUN_ID}-step${STEP}"
    REF="${ACR_HOST}/${MODEL_REPO}:${TAG}"

    echo "  checkpoint: ${FINAL_CKPT}"
    echo "  pushing to: ${REF}"
    cd "${FINAL_CKPT}"
    oras push "${REF}" \
      --annotation "org.opencontainers.image.title=${MODEL_REPO}" \
      --annotation "training.run_id=${RUN_ID}" \
      --annotation "training.step=${STEP}" \
      --annotation "training.base_model=${BASE_MODEL}" \
      ./:application/vnd.nvidia.groot.checkpoint.v1 || \
      echo "WARN: ACR push failed; local checkpoint at ${FINAL_CKPT} is unaffected." >&2
    cd -
    echo "  ACR push complete: ${REF}"
  fi
fi

echo "TRAIN_RESULT=PASS"
