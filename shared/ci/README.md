---
title: CI Smoke Scripts
description: GPU-free import smoke scripts for training and evaluation domains, runnable locally and in CI.
author: Microsoft Robotics-AI Team
ms.date: 2026-06-25
---

GPU-free import smoke checks that catch syntax, import, dependency-resolution, and interpreter/ABI regressions before they reach a GPU job. The same scripts run in CI (`.github/workflows/smoke-cpu.yml`) and locally.

## 📋 Prerequisites

| Tool   | Required for                             | Install                                            |
|--------|------------------------------------------|----------------------------------------------------|
| Docker | `smoke-image.sh` (any local host)        | <https://docs.docker.com/get-docker/>              |
| uv     | `smoke-import.sh` direct on linux/x86_64 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| bash   | All modes                                | Preinstalled on macOS and Linux                    |

Run every command from the repository root.

## 🚀 Usage

The locks target linux/x86_64, so on macOS or any non-linux host run the smoke through Docker with `smoke-image.sh`. On a linux/x86_64 host (and in CI) the inner `smoke-import.sh` runs directly.

```bash
# Any host with Docker (macOS included)
shared/ci/smoke-image.sh rl --mode cpu           # CPU import smoke, lightweight container
shared/ci/smoke-image.sh il --mode cpu
shared/ci/smoke-image.sh evaluation --mode cpu
shared/ci/smoke-image.sh rl                       # runtime-image smoke (Isaac Lab)
shared/ci/smoke-image.sh il                       # runtime-image smoke (PyTorch)

# linux/x86_64 host or CI — run the inner probe directly, no Docker
shared/ci/smoke-import.sh rl --mode cpu
```

`smoke-image.sh` mounts the repository at `/workspace` and runs `smoke-import.sh <domain> --mode <mode>` inside a linux/amd64 container: a lightweight uv image for `--mode cpu`, the domain's production image for `--mode image`. CI runs the CPU smoke directly on its linux runners and calls `smoke-image.sh` for the runtime-image depth after a free-disk-space step.

> [!NOTE]
> The runtime images are multi-gigabyte. The first `--mode image` run pulls the image; expect several minutes and ensure free disk.

## 📦 Scripts

| Script            | Purpose                                                                          |
|-------------------|----------------------------------------------------------------------------------|
| `smoke-import.sh` | Inner probe: install a domain's locked deps and import it; runs on linux/x86_64  |
| `smoke-image.sh`  | Run `smoke-import.sh` in a linux/amd64 container (`--mode cpu\|image`), any host |

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
