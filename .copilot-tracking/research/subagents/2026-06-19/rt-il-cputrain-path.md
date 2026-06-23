<!-- markdownlint-disable-file -->
# rt-il-cputrain: IL/LeRobot CPU training-path feasibility

Captured by parent (research subagent read-only).

## Verdict (graded by depth)
* (a) Import smoke — VIABLE (after installing CPU torch). Catches the #809/#790 ABI/dropped-symbol/Python-version class.
* (b) `--help` / arg-parse — VIABLE. Catches CLI/hydra config + policy.device arg wiring.
* (c) 1 real CPU training step — CONDITIONAL. Two blockers: CPU torch, and a real dataset (no synthetic fallback).

## Key findings
* training/il/scripts/lerobot/train.py appends `--policy.device=cuda` by default ONLY if `--policy.device` not already in CLI (train.py:~531-532) — so a caller CAN pass `--policy.device=cpu` to override. Test-verified the cpu flag passes through to the `lerobot-train` subprocess.
* GPU detection: `torch.cuda.device_count()` returns 0 on CPU; the script then runs WITHOUT the accelerate multi-GPU wrapper and invokes `lerobot-train --policy.device=cpu` directly (graceful).
* LeRobot 0.5.1 (training/il/lerobot/pyproject.toml:39) natively supports `policy.device=cpu` for ACT and Diffusion (slower).
* CRITICAL BLOCKER: training/il/lerobot/uv.lock pins torch==2.10.0 with cu12 nvidia libs — NOT a +cpu build. A CPU runner installing the lock pulls cu12 torch (huge; CUDA ops fail/hang). Fix: install torch from CPU index (`--index-url https://download.pytorch.org/whl/cpu`) for the smoke env, or a cpu-override lock.
* A minimal real step works with `--steps=1 --batch_size=1` but REQUIRES a real LeRobotDataset (e.g. lerobot/pusht) — the wrapper has no synthetic dataset; adds dataset-download time.

## Recommended
Tier the IL smoke: import-smoke + `--help` (cheap, CPU-torch) on every PR; an optional 1-step CPU train on a tiny cached dataset as a deeper (slower) job. The cpu-torch install is the enabling trick.

## Open questions
1. Maintain a cpu-torch install path just for smoke (vs the cu12 runtime lock)?
2. Acceptable to download a tiny real dataset (lerobot/pusht) in CI, or cache it?
