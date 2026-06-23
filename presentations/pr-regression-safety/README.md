<!-- markdownlint-disable-file -->
# PR Regression Safety

A short, narrated talk arguing that **a green CI check is not the same as "safe to merge"** in `microsoft/physical-ai-toolchain` — and proposing a phased gate that closes the gap.

The repository's test pipeline runs CPU-only, but the regressions that actually hurt are runtime-, GPU-, and interpreter-specific: CUDA/torch ABI breaks, Isaac Lab's Python-3.11 runtime, lockfile drift. Eight such failures were reconstructed from the project's own history — **green CI caught none of them**. The talk lays out four fixes that ship now for ~$0 and one funded GPU capstone, each mapped to the incidents it would have stopped.

## ▶️ Watch (≈26 min)

[![Play — PR Regression Safety, a ~26 minute narrated talk](poster.jpg)](presentation.mp4)

**[▶ Play the narrated video](presentation.mp4)** (~60 MB) — opens a player on GitHub. Prefer the slides? See the silent [`deck/presentation.pdf`](deck/presentation.pdf).

> [!NOTE]
> GitHub does not embed an inline player for repo-committed video, so the image above links to the file's page, where GitHub shows a player. Click it, or use the links below it.

## 🗺️ The argument in one line

> Green CPU CI is blind to the costly regression classes → add risk-aware dependency intake, a GPU-free smoke gate that runs inside the real runtime image, safe automation, and — when funded — a gated GPU end-to-end run.

| Phase | Ships | Cost | Catches |
| --- | --- | --- | --- |
| **0 — Risk-aware intake** | now, hours | ~$0 | dependency churn / noise |
| **1 — GPU-free smoke gate** | now, days | ~$0 | interpreter & import breaks (#809, #790) |
| **2 — Safe automation** | now, days | ~$0 | reviewer toil; routes risk to an agent |
| **3 — Gated GPU e2e** | when funded | GPU $ | CUDA / Vulkan / MIG / training-loop (#958 device half) |
| Spike — Renovate | parallel | ~$0 | cross-ecosystem PR sprawl |

53 slides (34 core + 19 appendix). The structure, claims, and narration reflect a 7-lens critique pass.

## 📂 What's inside

- [`presentation.mp4`](presentation.mp4) — the narrated video (~26 min, ~60 MB).
- [`deck/presentation.pdf`](deck/presentation.pdf) — the slides as a lightweight PDF.
- [`narration-script.md`](narration-script.md) — the full spoken script, one section per slide.
- [`deck.yaml`](deck.yaml) — every slide's source in one readable file (for clean review diffs).
- [`BUILD.md`](BUILD.md) — how to regenerate the slides, PDF, and video from source.
- [`PRESENTATION_SPEC.md`](PRESENTATION_SPEC.md) — the durable requirements and the applied-critique record.

The underlying research and the 7-lens critique are linked from [BUILD.md](BUILD.md#-research-and-critique).
