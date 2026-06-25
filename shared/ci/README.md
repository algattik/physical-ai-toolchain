---
title: CI Smoke Scripts
description: GPU-free import smoke scripts for training and evaluation domains, runnable locally and in CI.
author: Microsoft Robotics-AI Team
ms.date: 2026-06-25
---

GPU-free import smoke checks that catch syntax, import, dependency-resolution, and interpreter/ABI regressions before they reach a GPU job. The same scripts run in CI (`.github/workflows/smoke-cpu.yml`) and locally.

## 📋 Prerequisites

| Tool   | Required for        | Install                                            |
|--------|---------------------|----------------------------------------------------|
| uv     | All modes           | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker | Runtime-image smoke | <https://docs.docker.com/get-docker/>              |
| bash   | All modes           | Preinstalled on macOS and Linux                    |

Run every command from the repository root.

## 🚀 Usage

Two depths. The CPU import smoke resolves CPU torch wheels on the host; the runtime-image smoke pulls the domain's production container and imports inside it on the real interpreter.

```bash
# CPU import smoke — fast, no Docker
shared/ci/smoke-import.sh rl --mode cpu
shared/ci/smoke-import.sh il --mode cpu
shared/ci/smoke-import.sh evaluation --mode cpu

# Runtime-image smoke — pulls the domain's container, runs inside it
shared/ci/smoke-image.sh rl
shared/ci/smoke-image.sh il
```

`smoke-image.sh` resolves the domain image, mounts the repository at `/workspace`, and runs `smoke-import.sh <domain> --mode image` inside the container. CI calls the same wrapper after a free-disk-space step.

> [!NOTE]
> The runtime images are multi-gigabyte. The first `smoke-image.sh` run pulls the image; expect several minutes and ensure free disk.

## 📦 Scripts

| Script            | Purpose                                                                    |
|-------------------|----------------------------------------------------------------------------|
| `smoke-import.sh` | Install a domain's locked dependencies and import it (`--mode cpu\|image`) |
| `smoke-image.sh`  | Resolve a domain's image and run `smoke-import.sh --mode image` in Docker  |

## 🧪 Domains

| Domain       | Python | Runtime image                           | CPU smoke | Runtime-image smoke |
|--------------|--------|-----------------------------------------|-----------|---------------------|
| `rl`         | 3.11   | Isaac Lab (`DEFAULT_ISAAC_LAB_IMAGE`)   | yes       | yes                 |
| `il`         | 3.12   | PyTorch (`lerobot-train.yaml` default)  | yes       | yes                 |
| `evaluation` | 3.12   | none (shares the Isaac Lab SiL runtime) | yes       | no                  |

Image references come from their source of truth: `scripts/lib/common.sh` for `rl`/`evaluation`, and `training/il/workflows/osmo/lerobot-train.yaml` for `il`.

## 🔍 What each depth catches

CPU import smoke installs CPU torch wheels, so it validates a different dependency graph than the production CUDA one. It catches import, resolution, and interpreter-syntax errors — not the production CUDA resolution.

The runtime-image smoke installs the committed lock exactly as production does and imports the domain on the real interpreter. It catches the interpreter and ABI-at-import class. It does not prove CUDA, Vulkan, MIG, or a real training loop.

## 🔧 CI integration

`.github/workflows/smoke-cpu.yml` runs the CPU import smoke for every domain on each pull request (unconditional baseline) and the runtime-image smoke path-gated to the changed training domain. The job feeds the single required `pr-validation-summary` check.
