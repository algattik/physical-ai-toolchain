<!-- markdownlint-disable-file -->
# rt-il-container: IL/LeRobot container build feasibility on a standard runner

Captured by parent (research subagent read-only).

## Verdict: build-only smoke of the EVAL image is VIABLE WITH CAVEATS (disk-tight).

## Key findings
* evaluation/sil/docker/Dockerfile.lerobot-eval base = mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04 (digest-pinned) — PUBLIC, CPU-pullable, NO auth (Dockerfile.lerobot-eval:1). ~2-3GB base.
* System apt deps are arch-independent (ffmpeg git build-essential unzip python3-dev) — no CUDA system libs (:3-5).
* Python deps via `uv export --frozen --no-hashes --no-emit-project | uv pip install --system --no-deps -r -` (:28-29). uv itself hash-pinned (--require-hashes, :9-27).
* BUT the lock pulls cu12 wheels: torch 2.10.0 ~916MB + 7 nvidia-*-cu12 wheels ~3.5GB. Final image ~6-8GB on a ~14GB runner → TIGHT; needs a free-disk-space action + docker buildx; worst case (dirty docker cache) can OOM disk.
* IMPORTANT scope: IL TRAINING is NOT built from this image. OSMO IL uses image pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime (training/il/workflows/osmo/lerobot-train.yaml:160); AzureML uses a managed env (azureml:lerobot-training-env). Dockerfile.lerobot-eval is INFERENCE/eval-only and CPU-runnable. Isaac Lab image (nvcr.io/nvidia/isaac-lab:2.3.2) is separate and **anonymously pullable** (verified 2026-06-22: manifest HTTP 200, no NGC key; 8.4 GB compressed / ~18-22 GB unpacked) — not built by us either.
* Line 32 pre-downloads torchvision ResNet18 weights (CPU op, no GPU).

## What build-only smoke catches / misses
Catches: base-image registry drift (Dependabot digest bumps), dependency/wheel resolution failures, hash failures, apt availability, Dockerfile syntax. Misses: GPU runtime (CUDA kernels), inference correctness, performance.

## Recommended
A `docker build` job on `evaluation/sil/docker/**` path-trigger: jlumbroso/free-disk-space first → buildx build → `docker run --rm <img> python -c "import torch, lerobot; print('ok')"` as a cheap post-build import check. Warn-only initially.

## Open questions
1. Accept ~1-5% disk-churn flakiness?  2. Multi-stage to shrink, or accept 6-8GB?  3. Trigger only on docker-dir changes (avoid noise)?
