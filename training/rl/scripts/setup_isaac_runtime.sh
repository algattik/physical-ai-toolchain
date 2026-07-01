# shellcheck shell=bash
# Shared Isaac Lab runtime setup for in-container GPU jobs (training and evaluation).
#
# Source (do not execute) after setting:
#   ISAAC_PROJECT_DIR       directory holding pyproject.toml + uv.lock to install (e.g. training/rl)
#   ISAAC_PYTHONPATH_ROOT   path prepended to PYTHONPATH so first-party packages import
#
# Honors the PYTHON env var (space-separated launcher, e.g. Isaac Lab's isaaclab.sh -p).
# On return: uv is on PATH, PYTHONPATH is exported, the locked project dependencies are
# installed, and `python_cmd` (array) is set for the caller to exec its entrypoint module.

: "${ISAAC_PROJECT_DIR:?ISAAC_PROJECT_DIR must be set before sourcing setup_isaac_runtime.sh}"
: "${ISAAC_PYTHONPATH_ROOT:?ISAAC_PYTHONPATH_ROOT must be set before sourcing setup_isaac_runtime.sh}"

declare -a python_cmd
if [[ -n "${PYTHON:-}" ]]; then
  IFS=' ' read -r -a python_cmd <<< "${PYTHON}"
else
  python_cmd=(python)
fi

python_exec="/isaac-sim/kit/python/bin/python3"
if [[ ! -x "${python_exec}" ]]; then
  python_exec="${python_cmd[0]}"
fi

configure_uv() {
  local resolved_env
  if ! command -v uv &>/dev/null; then
    return 0
  fi
  if [[ -n "${python_exec}" ]]; then
    resolved_env="$("${python_cmd[@]}" -c 'import sys; print(sys.prefix)' 2>/dev/null || true)"
    export UV_PYTHON="${python_exec}"
    if [[ -n "${resolved_env}" && -d "${resolved_env}" ]]; then
      export UV_PROJECT_ENVIRONMENT="${resolved_env}"
      echo "uv configured with Python: ${python_exec}, environment: ${resolved_env}"
    else
      echo "uv configured with Python: ${python_exec}"
    fi
  else
    echo "Python executable not set; uv will use system discovery"
  fi
}

if ! command -v uv &>/dev/null; then
  echo "Installing uv package manager..."
  UV_VERSION="0.11.21"
  UV_SHA256="8c88519b0ef0af9801fcdee419bbb12116bd9e6b18e162ae093c932d8b264050"
  curl -LsSf "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz" -o /tmp/uv.tar.gz
  echo "${UV_SHA256}  /tmp/uv.tar.gz" | sha256sum -c --quiet -
  tar -xzf /tmp/uv.tar.gz -C /tmp
  mkdir -p "${HOME}/.local/bin"
  install -m 0755 /tmp/uv-x86_64-unknown-linux-gnu/uv "${HOME}/.local/bin/uv"
  install -m 0755 /tmp/uv-x86_64-unknown-linux-gnu/uvx "${HOME}/.local/bin/uvx"
  rm -rf /tmp/uv.tar.gz /tmp/uv-x86_64-unknown-linux-gnu
  export PATH="${HOME}/.local/bin:${PATH}"
fi

configure_uv

prebundle_path="/isaac-sim/exts/omni.pip.compute/pip_prebundle"
if [[ -d "${prebundle_path}" ]]; then
  export PYTHONPATH="${prebundle_path}:${ISAAC_PYTHONPATH_ROOT}:${PYTHONPATH:-}"
else
  export PYTHONPATH="${ISAAC_PYTHONPATH_ROOT}:${PYTHONPATH:-}"
fi

if command -v uv &>/dev/null; then
  echo "uv detected, exporting locked manifest dependencies from ${ISAAC_PROJECT_DIR}..."
  # The Isaac Lab container ships a torch + CUDA runtime stack matched to its GPU
  # driver and to the omni.*/pip_prebundle trees the simulator imports. torch is only
  # a transitive dependency of skrl/rsl-rl, so the lock resolves the latest torch
  # (CUDA 13); installing it uninstalls the container's torch and split-loads the
  # package across the prebundle and site-packages, crashing (ImportError:
  # cannot import name 'CacheArtifactType' from 'torch.compiler._cache') as soon as
  # skrl builds an optimizer. Install every other locked package and keep the
  # container's torch/CUDA stack. pynvml/nvidia-ml-py are pure-Python NVML bindings
  # and are intentionally retained.
  isaac_provided_re='^(torch|torchvision|triton|cuda-bindings|cuda-pathfinder|cuda-toolkit|nvidia-(cu|nccl|nvjitlink|nvshmem|nvtx)[a-z0-9.-]*)=='
  reqs_file="$(mktemp)"
  uv export --frozen --no-hashes --no-emit-project --project "${ISAAC_PROJECT_DIR}" \
    | grep -Ev "${isaac_provided_re}" >"${reqs_file}"
  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    uv pip install --no-cache-dir --no-deps --requirement "${reqs_file}"
  else
    uv pip install --no-cache-dir --no-deps --system --requirement "${reqs_file}"
  fi
  rm -f "${reqs_file}"
else
  echo "Error: uv is required to install workflow manifest dependencies" >&2
  exit 1
fi
