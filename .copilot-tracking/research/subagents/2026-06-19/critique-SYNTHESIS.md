# PR Regression Safety deck — consolidated critique

Synthesis of 7 parallel critique lenses: **visual, structure, argument, audience, narration, editorial, techdepth**. Findings are de-duplicated and ranked by impact. The bracketed tags show which lenses independently raised each point — more tags means stronger signal. This is a critique only; nothing here is applied yet.

## Headline

The deck's *diagnosis* is strong and well-evidenced; its *decision ask* is not yet fundable, it is ~40% too long, and it contains one genuine technical contradiction that an expert will challenge on sight. Fix the accuracy defects first (they are wrong, not merely suboptimal), then re-cut from a 68-slide research readout into a ~36-slide decision deck with an appendix.

---

## TIER 1 — Accuracy / credibility defects (fix before showing)

**A1. The `#958` (torch/CUDA) claim contradicts itself and overreaches.** [techdepth, argument, structure]
Slide 34 says only GPU e2e catches GPU-only ABI mismatches "like the torch case," but slides 36/64 say Tier 1 / Phase 1 catches `#958`. Both lenses rank this the single most-challengeable claim (confidence: high). A torch/CUDA/libcudart break can import fine on CPU and fail only when CUDA initializes.
Fix: split `#958` into (a) dependency-resolution / import-time failure (CPU-catchable) and (b) device-execution ABI failure (GPU-only). Remove `#958` from the deterministic Tier-1 catch list. Reword slide 64 from "would have caught #958" to "would have exposed the dependency-selection risk before merge; only Phase 3 proves runtime execution."

**A2. Tier 0 silently swaps the production CUDA torch graph for CPU wheels.** [techdepth]
It changes the very dependency graph it claims to validate. Retitle "Tier 0 CPU-compatibility smoke" and caveat: it catches Python/package import failures, not production CUDA resolution. Add a Tier-1 smoke that exports the real lock and imports inside the CUDA image without initializing CUDA.

**A3. The GPU submit-and-poll YAML may execute untrusted PR shell on a privileged runner.** [techdepth]
`submit-osmo-training.sh` runs after `azure/login@v2`. If it is PR-head code, contributor shell runs with an Azure OIDC token — violating the deck's own safety model. If it is base-branch code, the job doesn't test the PR's submission changes. Show a two-job pattern: Job A (pull_request, no token) builds a constrained artifact; Job B (after Environment approval, trusted base code) validates and submits, never executing PR shell.

**A4. The RSL-RL "2-line refactor" is understated.** [techdepth, argument, structure]
Real acceptance criteria: import on CPU, `--help` exits before AppLauncher, identical GPU launch path, argv preservation, unchanged Azure/MLflow side effects. Say "small refactor," not "2-line."

**A5. OIDC / `pull_request_target` / auto-merge safety is asserted, not constrained.** [techdepth, argument]
`id-token: write` is not harmless on fork PRs; it is safe only with a tight federated-credential policy (sub/aud/repo/branch/event) or an Environment gate before token mint. Auto-merge needs an explicit conservative scope: patch-only first; dev/docs/actions only; no GPU/runtime packages; no lockfile-wide churn; no security-PR batching; no PR-head checkout under `pull_request_target`; required checks green; merge queue; instant-revert playbook.

---

## TIER 2 — Strategic structure (research readout → decision deck)

**B1. Too long. Cut 68 → ~36 core + 14–18 appendix.** [editorial, structure, narration, audience]

**B2. Cold open.** Slides 01–03 give agenda + method before stakes. Open with the 8-vs-0 failure pattern and the decision ask in the first three slides; move method to one caption. [structure, narration, editorial]

**B3. The 8-slide primer stalls the argument.** Collapse to one "Terms used today" slide (≤5 terms); move the glossary and the rest to appendix or introduce just-in-time inside the phase that uses each tool. [editorial, structure, narration]

**B4. (Tension with B3) The deck lacks a robotics-stack primer.** [audience]
CI/CD generalists are taught dependency/agentic vocabulary but not Isaac Lab / CUDA / Vulkan / MIG / AzureML / OSMO / submit-and-poll — the very concepts that justify Phase 1/3. Resolution: trade *down* the tool-vocabulary primer, but add a tight stack primer (or just-in-time stack callouts) so the runtime story lands.

**B5. No crisp, fundable ask.** Add an executive TL;DR immediately after the title and a "Decision requested today" close listing specific approvals, owners, costs, success metrics, and explicit deferrals. [argument, editorial, structure]

**B6. Phase 3 cost is unquantified; "idle cost ≈ \$0" is not a budget.** Give per-run cost, monthly cap, expected run frequency, timeout, queue policy, retained artifacts, and three scenarios (low/expected/spike). [argument, techdepth]

**B7. Phase 1 steals Phase 3's climax.** Proving "$0 smoke catches #809/#790/#958" makes the GPU funding ask look optional. End Phase 1 on its *limitation* ("catches install/import/runtime-image drift; cannot prove CUDA, Vulkan, MIG, or training behavior"), not a victory. (Depends on A1.) [structure, argument]

**B8. The Tier-0 vs Tier-1 ask is blurred.** Rename to Phase 1a (Tier 0, every PR) and Phase 1b (Tier 1, real-image, path-gated); give each a runtime, disk requirement, maintainer burden, and branch-protection status. [argument, techdepth]

**B9. Renovate is overweighted and placed after the climax.** A tooling comparison should not follow the funded-GPU capstone. Move it into Phase 0 as a scoped spike (or one roadmap line) and condense 3–4 slides to 1. [structure, audience, editorial, narration]

**B10. The close is a 6-slide administrative tail.** Replace roadmap + sequencing + alternatives + open-decisions + next-steps with one "Decision requested" slide; alternatives → appendix; treat the live torch desync as an "immediate fix" callout, not an open decision. [structure, editorial, narration]

---

## TIER 3 — Redundancy (merge)

- **C1. AA baseline duplicates the per-phase problem slides** (25/32/44/52/58 re-state 14–22). Make each phase problem explicitly incremental ("given the baseline, this phase fixes X"). [structure, editorial]
- **C2. Two incident-catalogue slides → one** (keep ~5 incidents; full catalogue to backup). [editorial, structure]
- **C3. "What others do" recurs** (26/27, 33, 45/46, 53/54, 59/60). Replace with one "Pattern bank" slide; each phase then cites one precedent plus "what transfers / what doesn't." [structure, argument, editorial, narration]
- **C4. Same recommendation repeated within a phase**: Phase 2 (47/48/49 = one flow), Phase 0 (28/29), Phase 3 design+YAML (55/56), tier slides (34/35). Merge each pair/triple. [editorial, structure, narration]
- **C5. Smoke run 35–40 is the attention sag** — five restatements of "no GPU / disk-not-capability." Cut a third; keep conclusion + feasibility constraint, move mechanics to backup. [narration, structure, editorial]

---

## TIER 4 — Missing content (mostly appendix/backup)

- **D1. Incident→control matrix ("failure map").** Rows = #809/#790/#958/#691/#547; columns = missed-today / Phase 0 / Phase 1 Tier 0 / Tier 1 / Phase 2 / Phase 3, marked catches / reduces / not-addressed. This is the most-requested addition: it converts the "8 vs 0" slogan into causality and becomes the callback spine for the whole deck. [argument, structure, narration]
- **D2. Counterargument slides.** "Won't auto-merge cause incidents?" and "Why not just pin Python everywhere?" (answer: necessary but insufficient — pins don't exercise real image installs, transitive ABI selection, or CUDA/MIG execution). [argument, techdepth]
- **D3. Economics / ROI.** Price current dependency-PR waste (PRs/week × CI wait/rebases × reviewer minutes × token cost) and a "do nothing" status-quo baseline. [argument]
- **D4. Smoke-tier operating cost.** Owner, runtime, known flakes, image-pull/free-disk fragility, false-positive triage path, and the explicit fail-safe path-gate design (stable required summary always runs; skipped legs reported; lockfile changes override path gates). [argument, techdepth]

---

## TIER 5 — Narration craft [narration]

- **E1.** One rule per slide: *new claim → evidence not already on screen → implication.* Stop reading bullets aloud (worst overlap: 67, 20, 44, 10, 11, 8, 7, 52, 23, 5).
- **E2.** Purge stock phrases: "Here is" (×10), "The problem/The problem today" (×6), "And concretely," "Today" (crutch), "The key."
- **E3.** Break the two dense exposition clusters (35–40, 58–63); give thin divider slides one causal bridge each; end without conference politeness ("Thank you — happy to take questions").

---

## TIER 6 — Visual / layout [visual]

- **F1.** Fixed oversized grey code cards make slides top-heavy with a hollow lower half (worst: 037, 046). Size the card to the snippet.
- **F2.** Dense/small code on 037/046; over-tall cards for short snippets (014, 017, 018, 038–040, 050, 056).
- **F3.** Roadmap 063: taller rows + aligned cost column.
- **F4.** Generic divider stock photos read non-technical; white-on-saturated subtitle contrast (024, 062); slide 036 header wraps "minutes" alone; glossary 012 cramped.

---

## Suggested execution order (if the user chooses to act)

1. **Accuracy pass** (A1–A5) — small, high-credibility edits; A1 also unlocks B7.
2. **Re-cut to core + appendix** (B1–B3, B5, B8–B10; C1–C5) — the biggest single lift; halves the deck.
3. **Add the failure-map spine + decision slide** (D1, B5/B6).
4. **Add counterargument + economics + operating-cost backup** (D2–D4).
5. **Narration rewrite on the surviving slides** (E1–E3).
6. **Visual code-card resizing + roadmap polish** (F1–F4).

Step 2 invalidates the audio cache below every insertion/deletion point, so batch all structural edits before re-synthesizing. apply 
