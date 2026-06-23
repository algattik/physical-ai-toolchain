<!-- markdownlint-disable-file -->
# Presentation Spec — PR Regression Safety (DURABLE; re-read before every rebuild)

Authoritative, persistent record of @algattik's instructions for this narrated deck. **Update this file whenever a new instruction is given.** It exists so requirements never drop out of context. Source of truth alongside `gen_content.py` + `slides_src.py`.

## Build pipeline (commands)
- Generator: `gen_content.py` (imports refined slide bodies/notes from `slides_src.py`); writes `content/slide-NN/` + `narration/slide-NN.txt`.
- Skill venv: `~/.copilot/installed-plugins/hve-core/hve-core-all/skills/experimental/powerpoint/.venv/bin/python`
- Build deck: `build_deck.py --content-dir content --style content/global/style.yaml --template <TPL> --output deck/presentation.pptx`
- Template (TPL): `~/OneDrive - Microsoft/Tools/Templates/Global-Skilling-PowerPoint-Template-slim.pptx` (slim ~52 MB; quote the path — it has spaces). The full ~547 MB variant is source-only; slim shares masters/layouts/theme and renders identically at 1080p.
- Export: `export_slides.py` → PDF, then `render_pdf_images.py --dpi 120` → `slides/slide-NNN.jpg` (ignore "MuPDF error: No common ancestor" warnings).
- Video: `SPEED=1.8 ./build_video.sh` (TTS via macOS `say`, ffmpeg per-slide clips → concat `presentation.mp4`). Then `open presentation.mp4`.
- **Audio robustness:** macOS `say` can transiently hang. Pre-synthesize all `audio/slide-NN.aiff` with `timeout 70 say` + retry, and validate each with `ffprobe` duration > 0 (a killed `say` leaves a corrupt aiff that makes `build_video.sh` divide-by-zero). Clear `audio/`+`clips/` when the slide set changes.

## Structure (REQUIRED) — re-cut 2026-06-22 to a decision deck (32 core + ~17 appendix)

Decision-ladder, not a research readout. Open with stakes, end with the ask; tool-vocabulary primers live in the appendix.

1. **Frame (4):** Title (subtitle "Why green CI is not safe to merge…") · `8 vs 0` stat hook · the five named incidents (one slide) · "What this asks for" (decision in brief).
2. **Current state — compact (4):** stack primer (Isaac/CUDA/MIG/AzureML/uv) · dependency intake today · 21 contexts = runtimes · CI & automation today.
3. **The bridge (1):** **failure map** matrix (incidents × Phase 0/1/2/3) — the callback spine; encodes the #958 split.
4. **Per PHASE (problem → one precedent → recommendation), tightened:** Phase 0 intake (+Renovate spike as 1 slide) · Phase 1 GPU-free smoke (Tier 0/1a/1b; **ends on its limitation**) · Phase 2 safe automation · Phase 3 gated GPU e2e (+"What funding buys" cost slide).
5. **Close (3):** roadmap (ship-now vs funded) · **Decision requested today** (specific approvals) · Questions.
6. **Appendix (~17):** 5 tool primers + glossary · production-contracts · disk-matrix · small-refactor · smoke operating-cost + fail-safe · anticipated objections (incl. pin-Python) · economics/ROI · Renovate adoption + spike config · alternatives · mandate & method.

A color-banded **phased roadmap** slide is mandatory (Phase 0–3 + Spike, cost + timing per row).

## Template / styling (REQUIRED)
- Use **Global-Skilling-PowerPoint-Template-slim.pptx** (Microsoft brand, slim ~52 MB variant). NOT the dark theme, NOT the MSA template (both rejected).
- Cover = `COVER_BLUE`; section dividers cycle template colored layouts (`DIVIDER_BLUE/TEAL/ORANGE/RED/GRAD-1/BLUE-2`); content = `TITLE-1` (clean white). Native placeholder fill is unreliable → overlay white text manually on cover/divider; dark text on white content.
- Fonts: Segoe UI (headings/body), DejaVu Sans Mono (code). Accent blue `#0078D4`, green `#107C10`, red `#C4314B`, amber `#9D5D00`, purple `#5C2E91`.
- **Ample real code/YAML** for BOTH current state and proposed change, ideally side-by-side (`codecompare` render kind). Code blocks must render literally — use `paragraphs:` (NOT flat `text:`) so YAML `- ` lines don't become bullets.

## Audience (shapes ALL content)
- **CI/CD generalists, NOT versed in cutting-edge methods.** Explain agentic/gh-aw/NeMo/Renovate concepts plainly, with concrete, readable code examples. Don't assume familiarity. Dig deep on these topics rather than hand-wave.

## Narration / TTS (REQUIRED)
- Speed **1.8×** (was 2×). Default macOS system voice — **no `-v` flag** (user sets System Voice; `-v` silently falls back).
- Video may run **up to 30 min**.
- Write **"pull request"** not "pull-request" (hyphen → audible pause).
- **Acronyms: bare caps** — write `GPU`, `CPU`, `CI`, `OIDC` (NOT `G-P-U` letter-spelling). User confirmed bare caps is the best TTS; drop all letter-spelling treatment.
- Scan narration before build for `[A-Z](-[A-Z])+-[a-z]` (hyphen-join bug) and stray spelled forms.

## Content accuracy / corrections (HONOR THESE)
- **Renovate framing (UPDATED 2026-06-22 w/ evidence):** real edge is **cross-ecosystem grouping** (one config for npm+uv+terraform+go+docker vs ~20 Dependabot blocks), NOT pep621/uv — Dependabot supports uv since 2025, repo uses it (9 uv blocks) + regenerates uv.lock natively. **Microsoft-OSS adoption verdict: Dependabot-dominant by ~10–20×; Renovate is a niche minority (~19 microsoft-org repos, mainly the sanctioned `microsoft/vs-renovate-presets` VS-team cluster + `microsoft/m365-renovate-config`; Azure/dotnet 1 each; github org ZERO).** OSPO promotes Dependabot, never mentions Renovate. **Key nuance:** the Mend GitHub App needs org approval (real friction, but VS/M365 teams got it) — BUT `renovatebot/github-action` (self-hosted) avoids the App entirely → approval friction ~0. **Migration effort:** auto-detects all our ecosystems; custom rules (torch/numpy/marshmallow pins, groups, gh-aw-actions exclusion) need manual packageRules → ~2–3h AI-assisted draft + ½–1 day validation (moderate, NOT a heavy spike, but "trivial" overstates it). **Roadmap positioning:** keep as a deliberate evaluation, but it CAN be earlier if done via github-action (no App approval). Evidence: subagents/2026-06-19/renovate-msft-oss-adoption.md.
- **gh-aw:** say "does more than it's **used for today**" (NOT "than assumed"). Repo runs exactly ONE gh-aw workflow today: advisory `aw-dependabot-pr-review.md` (slash-command, read-only).
- **Isaac image:** do NOT state it's public / no NGC key (obvious) — removed.
- Fixed: "any particular programme" → "adopt incrementally — each fix stands alone".
- Renovate/vercel-ai contradiction resolved: vercel/ai is npm-only and left Renovate for simplicity — not evidence against Renovate here.
- **Live torch desync (PR #958):** lock pins torch 2.10.0, `pytest-training.yml:41` force-installs 2.11.0.
- **Phase 2 de-scoped to deterministic (2026-06-23, @algattik):** dropped the AI decider/doer for dependency bumps. Rationale: a bump's risk is deterministic metadata (update-type × package-class × security-flag) and breakage is caught by Phase 1 *running* the smoke/import/lock gate, not by an LLM; code changes in response to bumps are rare and usually one-line pins/locks. Phase 2 = deterministic patch-only auto-merge + scoped manual review for the rest. **Cut slides:** "NeMo's gated agentic loop" (babysitter), "wire the agent to CI" (gh-aw today/proposed codecompare), and the **gh-aw primer** (backs no recommendation now; glossary `safe-outputs` row also dropped). NeMo stays only in the Phase 3 GPU-gating slide. gh-aw survives as a one-line current-state gloss (the repo's existing read-only advisory reviewer).

## Latest detail asks (2026-06-22)
- **Tutorial / primer section (REQUIRED):** add an explicit teaching section for the CI/CD-generalist audience covering **Dependabot** (version vs security updates, groups, ignore, cooldown, lockfile handling) and any other worthwhile concept (CI gating tiers; `pull_request` vs `pull_request_target` + OIDC + Environments for running untrusted PR code; uv/lockfiles; GHSA security advisories). Concrete tiny examples + a glossary. **Length is not a concern** — user said don't worry if the prez gets long. Place the primer up front (after Intro, before AA Current state) so later analysis lands. **gh-aw primer dropped 2026-06-23** (see corrections) — gh-aw backs no recommendation after the Phase 2 de-scope; it survives only as a one-line current-state gloss.
- **Explain the 21 Dependabot "contexts"** concretely, grounded in the repo: they are 21 `package-ecosystem` blocks across the monorepo's real subprojects — 8 `uv` Python envs (root, data-pipeline, training/rl, training/il/lerobot, evaluation, evaluation/sil/docker, workflows/osmo, data-management/viewer, viewer/backend), 4 Terraform roots (main, dns, vpn, automation), 3 npm (root, dataviewer frontend, docusaurus), 3 docker, gomod (terraform/e2e), github-actions. Convey that these are full, real environments (e.g. LeRobot IL training with full **AzureML env definitions** under `training/il/workflows/azureml/`, RL/Isaac training, SIL eval, FastAPI+React dataviewer, Terraform infra) — not toy contexts.
- **Clearer code examples**, e.g. the "gh-aw & NeMo" slide — show real, readable config, explained for generalists. Dig deep.

## Research capture (REQUIRED)
- Everything → `.copilot-tracking/research/2026-06-19/pr-regression-safety-research.md` (+ subagent captures in `.../subagents/2026-06-19/`). Keep deck claims and research in sync.

## Artifacts (session workspace; NOT committed)
`presentation/`: `gen_content.py`, `slides_src.py`, `build_video.sh`, `content/`, `narration/`, `slides/`, `audio/`, `clips/`, `deck/presentation.pptx`, `presentation.mp4`, `template/`, this spec.

## Critique applied (2026-06-22) — 7-lens deep critique → `critique-SYNTHESIS.md`

Generator is now **self-contained**: `gen_content.py` no longer imports `slides_src.py` (all content inlined). New render kinds: `matrix` (failure map); code/primer cards are **auto-height** (sized to snippet, not a fixed tall box); `phases` has taller rows + an aligned cost column.

Applied across all tiers:
- **Accuracy:** #958 split into resolution (cheap, ~) vs device-ABI (Phase 3, ✓) — removes the slide-34-vs-36/64 contradiction; Tier-0 "swaps CUDA graph for CPU wheels" caveat; GPU job is now a **two-job** pattern (PR code never on the token runner); "small refactor" (not "2-line") with acceptance criteria; OIDC/`pull_request_target`/auto-merge scoped tight (patch-only, no runtime/GPU pkgs, no security batch, fork federated-policy note).
- **Structure:** cold open (8-vs-0 first); tool primers → appendix; **stack primer** added for the robotics runtime; exec ask up front + **Decision requested** close; **Phase 1 ends on its limitation**; Tier 0/1a/1b named; Renovate condensed to 1 core slide; admin tail removed.
- **Added:** failure-map matrix · "What funding buys" cost slide · anticipated-objections (incl. pin-Python) · economics/ROI · smoke operating-cost + fail-safe gate.
- **Narration:** rewritten one-claim-per-slide; purged "Here is / The problem / And concretely / Today / no-GPU-anywhere"; TTS rules preserved (bare caps, "pull request").

## Pending fixes (apply in next correction pass)
- Bullet-only slides (e.g. Decision, Phase problems) sit a little top-heavy — optional vertical-centering polish (visual critique LOW); code-card HIGH items are resolved.
- Divider stock photos are template-generic (visual MED) — would need template asset swap.
