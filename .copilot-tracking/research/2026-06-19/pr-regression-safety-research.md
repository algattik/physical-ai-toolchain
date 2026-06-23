<!-- markdownlint-disable-file -->
# Task Research: PR Regression Safety — Intelligent Dependency Updates and Gated E2E Testing

Research into reducing the constant PR regressions in `microsoft/physical-ai-toolchain` (especially from Dependabot), framed by a chat between Alexandre Gattiker and Katrien De Graeve. Two intertwined problems: (1) Dependabot fires blind single-PR updates with no impact awareness, flooding CI and reviewers; (2) there is no automated end-to-end (GPU) regression gate on PRs, so "safe merge" cannot be asserted. Funding for an Azure GPU subscription is the blocker for full e2e; this research therefore also covers what can be done **without** a dedicated GPU subscription.

## Task Implementation Requests

* Research an agent-based dependency-update manager that replaces/augments Dependabot's blind single-PR firing: filter/triage high-impact updates and group low-impact ones into larger batched PRs. (Explicitly requested by Katrien: "the current dependabot is really not intelligent enough.")
* Determine whether a manual-gated, required CI check on high-risk PRs (e.g. `**/uv.lock` changes) is possible, and whether GitHub Agentic Workflows (gh-aw) + GitHub Coding Agent can implement the orchestration (create issues/PRs, trigger on labels/paths).
* Research gated e2e/smoke testing on PRs reusing the delivered scale-from-zero AzureML/OSMO setup, with a manual approval gate and explicit handling of the security risk of running PR code in CI.
* Improve the existing `aw-dependabot-pr-review` so it does not run before CI completes or on every rebase (token cost), ideally updating a single comment.

## Scope and Success Criteria

* Scope:
  * IN: GitHub-side CI/CD orchestration for this repo; Dependabot/Renovate grouping & triage; gh-aw capabilities and limits; GitHub Coding Agent orchestration; manual approval gates (Environments); GPU-free smoke-test ideas; security of running PR/fork code in CI; cost/token controls.
  * OUT: Provisioning the Azure GPU subscription / securing budget (org decision — "Bill"); authoring IsaacSim-specific test content; full implementation (this is research → handoff to planning).
* Assumptions:
  * The repo already has the scale-from-zero AML + OSMO setup delivered by Alex (referenced in memories and docs/training/osmo-training.md).
  * Free GitHub Actions/Copilot token budget is expected to tighten; designs must be token- and compute-frugal and avoid redundant runs.
  * Breaking changes are acceptable repo-wide; no backward-compat layers required.
* Success Criteria:
  * A recommended, layered approach is selected with rationale and evidence, separating "do now, no Azure needed" from "do when GPU funding lands".
  * Concrete `dependabot.yml` grouping config and a triage/batching design are provided.
  * gh-aw vs Coding Agent capabilities (PR creation, triggers, gates, safe-outputs) are documented with citations.
  * Manual-gate and fork-code-security patterns are documented with citations.
  * Clear next steps suitable for `/task-plan` handoff.

## Outline

1. Current repo state: Dependabot config, AW workflows, CI gates, e2e/contract tests, scale-from-zero backend. (Subagent A)
2. Intelligent dependency updates: native Dependabot grouping, Renovate, agent-based triage/batching. (Subagent B)
3. gh-aw + Coding Agent capabilities: triggers, PR/issue creation, manual gates, safe-outputs, orchestration. (Subagent C)
4. Gated GPU e2e + GPU-free smoke tests + CI security for untrusted PR code. (Subagent D)
5. Synthesis: layered recommendation + alternatives. (Phase 2)

Subagent capture files (full evidence, plain-text paths):

* .copilot-tracking/research/subagents/2026-06-19/repo-ci-current-state.md (Subagent A)
* .copilot-tracking/research/subagents/2026-06-19/dependency-update-intelligence.md (Subagent B)
* .copilot-tracking/research/subagents/2026-06-19/ghaw-and-coding-agent-capabilities.md (Subagent C)
* .copilot-tracking/research/subagents/2026-06-19/gated-gpu-e2e-smoke-security.md (Subagent D)
* .copilot-tracking/research/subagents/2026-06-19/issues-and-dependabot-pr-history.md (Subagent E)
* .copilot-tracking/research/subagents/2026-06-19/oss-best-practice-benchmark.md (Subagent F)

## Potential Next Research / Open Questions

* Required-status-check census: `gh api repos/microsoft/physical-ai-toolchain/branches/main --jq '.protection.required_status_checks'` — determines what currently blocks merge and where a new gated check must register. (Subagent A open Q1.)
* Renovate-vs-Dependabot decision spike: the repo uses committed `uv.lock` (Dependabot supports natively) AND `pyproject.toml` PEP621 (Dependabot pip does NOT read; Renovate `pep621`/`uv` manager does). Quantify migration effort vs payoff. (B vs F tension.)
* No-GPU-tier scope decision: until a GPU subscription is funded, do public-contributor PRs simply never run GPU e2e, do maintainers run it manually in a dev subscription, or hybrid? (Subagent D Q1.)
* Self-hosted GPU runner risk tolerance vs submit-and-poll-only (PR code never touches the runner). (Subagent D Q2.)
* Live desync to fix out-of-band: `training/il/lerobot/uv.lock` pins torch 2.10.0 but `.github/workflows/pytest-training.yml:41` forces `uv pip install torch==2.11.0` — lock and CI disagree today (Incident 3). Not part of this design but should be filed.

## Research Executed

### File Analysis

* .github/dependabot.yml — ~17–20 `package-ecosystem` blocks (npm ×2 incl. docusaurus, uv/pip ×~10 subprojects, terraform ×4, gomod ×1, docker ×3); all `schedule: weekly`. Grouping already used but as **wildcard catch-all groups per ecosystem**, NOT split by update-type (patch/minor vs major) or dependency-type. ~7 `ignore` pins (torch ≥2.11.0, numpy, marshmallow, packaging, av) added reactively after breakages. (Subagent A.)
* .github/workflows/aw-dependabot-pr-review.md + .lock.yml + .github/aw/ — trigger is slash command `/aw-dependabot-review`, **maintainer-only (RBAC)**, fires on a PR comment (NOT on push/rebase). Posts 1 review + ≤5 inline + ≤2 comments; Copilot engine v0.79.8; imports the `dependabot-pr-reviewer` agent. No mechanism makes it wait for CI to conclude → it can be invoked before CI fails (token waste — Katrien's concern). (Subagent A, C.)
* .github/workflows/uv-lock-consistency.yml — `npm run lint:uvlock` → read-only `uv lock --check`; fails PR on lock/manifest drift. 9 committed `uv.lock` files. (Subagent A.)
* .github/workflows/pytest-training.yml:41 — `uv pip install torch==2.11.0` overrides the lock (torch 2.10.0); live desync from Incident 3. (Subagent E.)
* infrastructure/setup/03-deploy-osmo-control-plane.sh, 04-deploy-osmo-backend.sh; training/rl/scripts/submit-osmo-training.sh; training/il/scripts/submit-osmo-lerobot-training.sh; evaluation/sil/scripts/submit-osmo-lerobot-eval.sh — OSMO on AKS, GPU node pool autoscales min_count=0→N on pending pods, scales back after cooldown; checkpoints to Azure Blob. Submit-and-poll e2e engine with ~0 idle cost. (Subagent A.)
* training/rl/scripts/smoke_test_azure.py — existing CPU-only Azure/MLflow connectivity smoke; wrapped in a unit test but NOT wired into PR CI. Submission scripts lack a `--config-preview` dry-run. (Subagent A.)

### Code Search Results

* Dependabot PR authorship history (`gh pr list --author app/dependabot`) — ~210 all-time; churn ~13/week all-time, ~14/week last 8 weeks, ~17/week last 6 weeks (accelerating); 6 merged in one day (2026-06-16). (Subagent E.)
* Issue search (CI/e2e/regression/smoke/dependabot) — only open issues are #9, #10 (OpenSSF docs). NO existing issue requests e2e testing, smoke tests, dependency batching, or regression prevention → a new issue is non-duplicative. Two closed issues (#809, #790) document dependency-drift production regressions. (Subagent E.)
* `git log --grep` (revert/desync/pin) — surfaced Incidents 1–8 below. (Subagent E.)

### External Research

* GitHub Docs — Dependabot `groups:` (patterns, `dependency-type`, `update-types`, `applies-to`), `cooldown` (new 2025, == Renovate `minimumReleaseAge`), `open-pull-requests-limit`, security vs version updates. Source: https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference
* GitHub Docs — Automating Dependabot with Actions; `dependabot/fetch-metadata` + `gh pr merge --auto` auto-merge pattern. Source: https://docs.github.com/en/code-security/dependabot/working-with-dependabot/automating-dependabot-with-github-actions
* Renovate docs — `config:recommended`, `:automergeMinor`/`:automergeDigest`, `group:*` presets, `dependencyDashboard`, `pep621`/`uv` managers, `platformAutomerge`. Source: https://docs.renovatebot.com
* gh-aw (github/gh-aw) — `safe-outputs` (`create-issue`, `create-pull-request`, `add-comment` with `hide-older-comments`, `comment-memory`, `create-check-run`, `assign-to-agent`), triggers (`slash_command`, `workflow_run`, `label_command`, path filters), gates (`roles:`, `manual-approval:`, `staged:`, `skip-if-check-failing:`), cost controls (timeout, `max-turns`, concurrency cancel, model var). gh-aw CAN create PRs from a git patch. Source: https://github.com/github/gh-aw (safe-outputs-*.md, pkg/workflow/create_pull_request.go).
* GitHub Copilot coding agent — assignable to issues / `assign-to-agent`; produces a PR autonomously in its own Actions env. Source: https://docs.github.com/en/copilot/using-github-copilot/using-copilot-coding-agent-to-work-on-tasks
* GitHub Actions security — `pull_request` (forks: read-only token, no secrets) vs `pull_request_target` (base context + secrets; "pwn request" if PR head is checked out and built); Environments with required reviewers as the human gate; fork-run approval. Sources: https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/ , https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments
* Azure — OIDC workload-identity federation for GitHub Actions (no stored secret); `az ml job create`. Sources: https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation , https://learn.microsoft.com/en-us/cli/azure/ml/job
* OSS exemplars (primary config evidence, Subagent F): huggingface/lerobot .github/workflows (GPU tests gated on PR-review approval, non-fork only) — the closest analogue; huggingface/transformers dependabot.yml (`cooldown: default-days: 7`) + self-scheduled.yml (nightly GPU); NVIDIA-NeMo cicd-approve-test-queue.yml (Environment as GPU concurrency gate) + claude-review.yml / claude-babysit-pr.yml (gated agentic review + half-autonomous fix loop); isaac-sim/IsaacLab build.yml (self-hosted GPU on PR + fork-safety XML check); pytorch/pytorch arc.yaml (ARC GPU fleet) + minimal dependabot.yml; vercel/ai, kubernetes-sigs/kind, grafana/augurs, vllm-project/vllm, ray-project/ray dependabot `groups:`; cheeriojs/cheerio dependabot-automerge.yml.

### Project Conventions

* Standards referenced: .github/copilot-instructions.md (uv.lock = source of truth, derive flat reqs at build; conventional commits; breaking changes OK; no unsolicited tests/docs). Memories: torch/lerobot ABI is the highest-risk ecosystem; uv.lock regenerated by Dependabot natively; scale-from-zero AML/OSMO mechanics; "confirm before external changes".
* Instructions followed: Task Researcher protocol (delegate research to subagents; write only under .copilot-tracking/research/).

## Key Discoveries

### The central insight: green CPU CI is blind to the regressions that actually hurt

The empirical record (Subagent E) shows the costly regressions are **runtime/GPU/interpreter-specific** and therefore invisible to today's CPU-only PR validation:

* Incident 1 (#809): RL `requirements.txt`/lock resolved against Python 3.12 while the Isaac Lab 2.3.2 container runs Python 3.11.9 → 4 cascading ABI/plugin failures (numpy 2.x vs Isaac's <2.0, etc.); 9 days to fix.
* Incident 2 (#790): `lerobot` requires Python ≥3.12 but the OSMO runtime is 3.11.9; a dep PR (#541) also dropped `azureml-mlflow`.
* Incident 3 (#958 / commit 36ba1ba): security bump torch 2.10→2.11 pulled uncapped `cuda-bindings` 13.x needing `libcudart.so.13` while cu12 wheels ship CUDA 12 → GPU import break. Reverted in lock; **CI still force-installs 2.11.0 → live desync**.
* Incidents 4–5 (#691, #547): malformed path-filter regex / folder restructure **silently disabled** fuzz + training tests for weeks — a green check that tested nothing.
* Incident 6: the AW dependabot reviewer (#498) itself shipped 6 consecutive bugs.
* Incidents 7–8 (#884→#983 starlette twice in 11 days; #346 release-please lock desync): churn and lock-staleness.

Implication: a meaningful "safe-merge" signal requires (a) exercising the **real container/runtime** (GPU e2e tier), and (b) cheaper checks that at least catch resolution/import/interpreter breaks **before** GPU spend, and (c) making path-gated required checks fail-safe rather than silently skip.

### Dependabot is already grouped — the gap is risk-awareness, not grouping per se

Native `groups:` is present but wildcard. The unmet needs an "intelligent" layer must fill: split patch/minor (batch) from major (isolate); fast-track security, batch routine; cross-ecosystem consolidation; auto-merge low-risk on green CI; escalate high-risk (torch/isaaclab/numpy, lockfile-wide, CVSS-high) to deep review. Native Dependabot cannot auto-merge or group across ecosystems; both need an Actions/Renovate/agent layer. (Subagents B, F.)

### gh-aw can do far more than the maintainers assumed

Resolves the chat's open questions directly (Subagent C):

* "Can GH AW create PRs?" — **Yes**, `create-pull-request:` safe-output (git patch → branch → PR; agent stays read-only, safe-outputs job holds `contents: write`; PRs don't trigger CI by default).
* "Runs before CI / on every rebase / many comments?" — already `slash_command`-gated; can additionally trigger on `workflow_run` (CI completed) and `skip-if-check-failing:` to avoid pre-CI runs; `add-comment: {hide-older-comments: true}` or `comment-memory:` keeps a single updating comment.
* "Required check triggered manually on `**/uv.lock`?" — `create-check-run:` (name must match branch-protection required check) + path/label gating; mind the "skipped pull_request leaves required check Pending → blocks merge" trap (use a default-pass job + gated heavy job, or environment approval).
* "AW → issue → coding agent?" — `assign-to-agent:` assigns Copilot coding agent to a structured issue, which opens its own PR.

### The closest OSS exemplar is our own upstream

huggingface/lerobot already runs **fast CPU tests on every PR and GPU tests only after a maintainer approves the PR review, never on forks** — exactly the gate this repo needs. NVIDIA NeMo gates GPU via a GitHub Environment queue and runs gated agentic review/fix loops; Isaac Lab runs GPU per-PR with fork-safety. GitHub Copilot coding agent / gh-aw has little public OSS adoption yet — this repo is unusually early; Claude Code is the dominant production agentic-CI tool elsewhere. (Subagent F.)

## Technical Scenarios

### Scenario 1 — Intelligent dependency-update management (the explicitly-requested research)

Reduce Dependabot noise and catch high-risk bumps, minimizing CI runs and AI tokens.

**Requirements:** batch low-risk, isolate/escalate high-risk, fast-track security, no regression in the uv.lock governance, near-zero added compute.

**Preferred Approach — phased, Dependabot-native first:**

* Phase 0 (config-only, zero code, immediate): rewrite `.github/dependabot.yml` groups to split `update-types: [patch, minor]` (one grouped PR/ecosystem) from majors (separate, human-reviewed); group dev-dependencies and github-actions digests; add `cooldown: { default-days: 7 }` (stability window, mirrors HF transformers); keep security updates ungrouped/fast-tracked; keep existing ignore pins. Prevents the #884→#983 double-churn and most single-PR spam.
* Phase 1 (low-risk auto-merge): an Actions workflow using `dependabot/fetch-metadata` + `gh pr merge --auto --squash`, restricted to `semver-patch`/`semver-minor` and github-actions digests, merging only after required checks pass; never auto-merges torch/isaaclab/numpy/lerobot or majors. Pattern from cheeriojs/cheerio.
* Phase 2 (agentic escalation, optional): a `gh-aw` workflow (triggered weekly or on `workflow_run` after CI) that reads open Dependabot PRs, classifies high vs low impact, and either (a) `assign-to-agent:` a remediation issue to the Copilot coding agent for high-risk bumps that need code/lock fixes, or (b) `create-pull-request:` a combined low-risk batch. Mirrors NeMo's gated agentic model.

```text
.github/dependabot.yml            # Phase 0: split patch/minor vs major + cooldown + dev/actions groups
.github/workflows/dependabot-automerge.yml   # Phase 1: fetch-metadata + gh pr merge --auto (low-risk only)
.github/workflows/aw-dependency-triage.md    # Phase 2 (optional): gh-aw triage -> assign-to-agent / create-pull-request
```

**Considered Alternatives:** (1) Migrate to Renovate — strategically superior for multi-ecosystem + uv/pep621 (cross-ecosystem grouping, native automerge, dependency dashboard, `minimumReleaseAge`), but high migration cost (port ~20 blocks, ignore rules, the gh-aw/uv-lock interplay) and changes the GHSA-integrated security flow; recommend as a deliberate spike, not the default first move. (2) `github/combine-prs` to collapse cross-ecosystem PRs — useful but a workaround that Renovate obviates; skip in favor of Phase 0/2. (3) Pure custom agent replacing Dependabot — highest effort/maintenance; rejected (reinvents grouping that is now native).

### Scenario 2 — Make the AW reviewer cost-frugal

**Preferred Approach:** add `workflow_run` (on the PR-validation workflow `completed`) and/or `skip-if-check-failing:` so the reviewer only runs when CI is green; switch its comment to `add-comment: { hide-older-comments: true }` or `comment-memory:` so rebases update one comment. Keep the maintainer-only `slash_command` as an explicit override. Directly answers Katrien's "it runs before CI finishes → wasted tokens" and Alex's single-comment point. (Subagent C.)

### Scenario 3 — Gated e2e regression testing (when GPU funding lands) + GPU-free smoke tier (now)

**Preferred Approach — two tiers:**

* Tier 1 (now, no Azure): a `smoke` job on every PR on standard runners — `uv lock --check` / `uv sync --locked` resolve; import smoke (`python -c "import lerobot, torch, ..."` and entrypoint `--help`); extend `--config-preview`/`--save-as` to emit the *rendered* OSMO/AML YAML for schema validation (today it prints parsed CLI values, not the YAML); container BUILD smoke for the **eval** image only (`Dockerfile.lerobot-eval`; the training images are stock/managed — `pytorch/pytorch` base and an AML managed env — with no Dockerfiles of ours to build) — disk-tight, needs a free-disk-space step; reuse existing go contract + fuzz + frontend validate. Catches resolution/import/interpreter breaks (Incidents 1–3 partially, 2 fully) for ~$0.
* Tier 2 (when funded): a gated `e2e-gpu` job following the **LeRobot pattern** — trigger on `pull_request_review` approved + `head.repo.fork == false`, OR a maintainer label; the job authenticates to Azure via **OIDC** (no stored secret) and **submits a job to the scale-from-zero OSMO/AML GPU pool, then polls** (PR code runs inside the AML/OSMO sandbox, not on the runner); wrap in a GitHub **Environment with required reviewers** for a hard human gate; concurrency-cancel superseded runs; timeout caps. Idle cost ≈ $0 (scale-to-zero).

```yaml
# Tier 2 sketch
on:
  pull_request_review:
    types: [submitted]
jobs:
  e2e-gpu:
    if: >-
      github.event.review.state == 'approved' &&
      github.event.pull_request.head.repo.fork == false
    environment: e2e-approval        # required-reviewers gate releases OIDC perms
    steps:
      - uses: azure/login@v2          # OIDC federated credential, no secret
      - run: ./training/rl/scripts/submit-osmo-training.sh   # submit-and-poll, GPU pool 0->N
```

**Considered Alternatives:** (1) Self-hosted GPU runner on AKS (ARC) executing PR code directly — cheaper per run but exposes the runner to untrusted code; rejected for fork PRs in favor of submit-and-poll; acceptable only post-approval for collaborators. (2) `pull_request_target` + PR-head checkout to give fork PRs secrets — classic "pwn request"; rejected. (3) Nightly-only GPU on main (HF transformers self-scheduled) — good complement but doesn't gate the PR; keep as an additive safety net, not the primary gate. (4) GPU on every PR (Isaac Lab) — too costly without dedicated funding; rejected.

### Depth calibration — how deep can the GPU-free smoke go, per domain

Answers the follow-up: *build the full container? run the actual training script on the agent?* Sources: `subagents/2026-06-19/rt-il-container-build.md`, `rt-il-cputrain-path.md`, `rt-rl-isaac-gpu-boundary.md`, `rt-submit-dryrun-surface.md`, `rt-existing-smoke-and-limits.md`.

Runner ceiling (confirmed): `ubuntu-latest` = 4 vCPU / 16 GB RAM / ~14 GB free disk / **no GPU** / 6 h cap. The 14 GB disk is the binding constraint for any container or cu12-torch work.

| Depth | IL / LeRobot | RL / Isaac | Submission flow |
|---|---|---|---|
| Import smoke | ✅ (needs CPU-torch) | ⚠️ SKRL module importable; RSL-RL `train.py` calls `AppLauncher()` at import → needs a `main()` refactor to import/`--help` without GPU | n/a |
| `--help` / arg-parse | ✅ | ✅ `launch*.py` are isaaclab-free | ✅ |
| Build the container | ⚠️ only the **eval** image (`Dockerfile.lerobot-eval`, public CPU base) builds — disk-tight (~7–9 GB final, pulls cu12 torch ~4.4 GB) → free-disk-space action recommended. Training images are **not ours to build**: OSMO = stock `pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime`, AML = managed env (built server-side) | ⚠️ Isaac image (`nvcr.io/nvidia/isaac-lab:2.3.2`) is **anonymously pullable** (verified live: HTTP 200, no NGC key; 8.4 GB compressed / ~18–22 GB unpacked) but there is **nothing to build** (no Dockerfile) and **no GPU** to run it — pulling buys only "digest didn't rot" | n/a |
| Run the training script | ⚠️ 1 real CPU step works with `--policy.device=cpu --steps=1 --batch_size=1` BUT needs (a) a CPU-torch install (lock pins cu12, not `+cpu`) and (b) a real `LeRobotDataset` (e.g. `lerobot/pusht`) — **no synthetic fallback** | ❌ GPU-coupled end-to-end (Isaac Sim + Vulkan); no CPU env/training mode exists | submit-and-poll runs only online |
| Submit dry-run | — | — | ~70% offline-validatable: arg-parse, base64 payload pack, Jinja render, YAML syntax + JSON-schema (AML `commandJob.schema.json`), shellcheck. Strictly online: `az/osmo login`, `az ml job create`, asset/dataset resolution |

**Bottom line.** *Build the full container?* — only the eval image, and only with a free-disk-space step; the training images are stock/managed (built elsewhere, nothing for us to build). *Run the actual training script?* — IL yes but shallowly (import + `--help` cheap; one real CPU step possible behind two blockers: the cu12-pinned lock and the missing synthetic dataset); RL no — Isaac is GPU-only end-to-end, so the real RL e2e must be the gated GPU tier. Two cheap enabling tricks unlock most of the reachable depth: a CPU-torch install path (`--index-url …/whl/cpu`) for the smoke env, and emitting rendered YAML from the submit scripts for offline schema validation. Optional RL refactor: move `rsl_rl/train.py`'s `AppLauncher()` into a `main()` (mirroring SKRL) so the module imports and `--help` work without a GPU.

### Container build feasibility — verified numbers

Answers the follow-up *"are the containers too big to reasonably build in CI?"* — verified live 2026-06-22, replacing earlier estimates.

Runner disk budget (`ubuntu-latest`, confirmed):

| Metric | Value |
|---|---|
| Total VM disk | ~72 GB |
| Free on `/` at job start | ~14–22 GB |
| Reclaimable via `jlumbroso/free-disk-space` | ~20–31 GB → ~35–45 GB free |

Per-image verdict:

* **Eval image** (`evaluation/sil/docker/Dockerfile.lerobot-eval`) — the only image in the repo with our own Dockerfile. Final ~7–9 GB uncompressed (public `mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04` base ~2–3 GB + cu12 torch & 7 nvidia-cu12 wheels ~4.4 GB). Cold-build disk peak ~14–18 GB → **tight on a bare runner, comfortable after a free-disk-space step**. Binding cost is **time** (~8–15 min cold, fully layer-cacheable), not size. A CPU-torch variant (this is a CPU-runnable eval image) would shrink it to ~2–3 GB and build in minutes — but that changes the production artifact, so it is a separate decision.
* **OSMO IL training image** = stock `pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime` (~15–18 GB unpacked). No Dockerfile → nothing to build; it is a pull-and-run artifact.
* **AML training env** = managed AzureML environment, built server-side. Nothing to build in CI.
* **Isaac (RL) image** = `nvcr.io/nvidia/isaac-lab:2.3.2`. **Anonymously pullable** — verified live: anonymous bearer token → manifest HTTP 200, no NGC key; 29 layers, **8.4 GB compressed**, ~18–22 GB unpacked. Earlier "NGC-auth, not pullable" claim was **wrong**. The repo's NGC-credential requirement (`prerequisites.md:70`) is for the **GPU Operator** catalog and **pre-release `nvcr.io/nvidia/osmo/*` platform images** (the `osmo-backend-operator.yaml:30` comment: *"backend-test-runner … NVCR requires authentication"*), NOT the isaac-lab training image. Proof in deploy logic: `create_nvcr_pull_secret` fires only for `is_prerelease_tag`/`--use-acr` (`scripts/lib/common.sh:303`, `infrastructure/setup/03-deploy-osmo-control-plane.sh:276`); `isaac-lab:2.3.2` is neither, yet pods pull it — so no secret is needed. The real CI blocker for Isaac is **GPU + disk**, not auth: ~18–22 GB unpacked is heavy but feasible post-cleanup, but without a GPU (Vulkan/CUDA) you cannot run Isaac Sim, so pulling it only verifies the digest still resolves — low value, belongs in the gated GPU tier.

**Bottom line on size:** "too big" is a non-issue. The only image with a Dockerfile to build (eval) fits comfortably after a free-disk-space step; the genuinely large images (PyTorch training, Isaac) are pull-and-run artifacts we never build in CI.

**More disk is available but doesn't change the conclusion.** Options: (1) `jlumbroso/free-disk-space` → ~35–45 GB, free, already sufficient for the eval image; (2) GitHub-hosted **larger runners** — 4-core/150 GB, 8-core/300 GB, 16-core/600 GB SSD (disk is fixed per SKU, not separately configurable — you buy disk by buying cores), paid per-minute; (3) **self-hosted** runners (e.g. ARC on the project AKS) with arbitrary PV-backed disk, but they expose the runner to PR code (same security tradeoff as the self-hosted-GPU option). For this repo none of this is needed: the eval image is the only thing we build and free-disk-space covers it; the large training/Isaac images are never built, and disk is not what blocks *running* them — **no GPU** is. A 600 GB runner still has no GPU, so it would pull a ~22 GB Isaac image only to be unable to run Isaac Sim. Larger runners would buy build **speed/parallelism**, not capability.

### Scenario 4 — Required, manually-gated check on high-risk PRs (e.g. `**/uv.lock`)

**Preferred Approach:** register a branch-protection required check (e.g. `uv-lock-review`) produced by a gated workflow. Because a path-skipped `pull_request` job leaves the required check Pending and blocks merge, use the fail-safe pattern: a cheap always-running job reports the check as success by default, and only when the PR touches `**/uv.lock` does it require the gated heavy path (manual approval via Environment, or a maintainer `slash_command` that flips the `create-check-run:` to in-progress/success). This realizes Alex's "required CI check that must be triggered manually on `**/uv.lock`". (Subagent C §6.) Note: the #691/#547 silent-skip incidents are the cautionary tale for naive `paths:` gating.

### Scenario 5 — Orchestration: who does the work

**Preferred Approach:** keep cheap, gated gh-aw as the **decider/dispatcher** and the Copilot coding agent as the **doer**. gh-aw (slash-command or `workflow_run`, maintainer-gated, `staged`/`manual-approval` for safety) triages and either creates a structured remediation issue and `assign-to-agent:` (Copilot opens a fix PR), or `create-pull-request:` directly for trivial batches. This matches the chat's "GH AW create an issue, tag it, have Coding agent do the work" and NeMo's gated babysitter precedent. (Subagents C, F.)

## Selected Layered Program (sequenced by cost and funding)

Order chosen so the highest-value, lowest-cost, no-Azure-needed items ship first; GPU e2e waits on funding but its design is settled.

1. Phase 0 Dependabot grouping + cooldown (config-only) — kills most noise; prevents double-churn. [no Azure, hours]
2. AW reviewer: gate on CI-green + single updating comment — stops token waste. [no Azure, hours]
3. GPU-free smoke tier (uv lock --check, import smoke, `--config-preview`, build smoke) wired into PR validation; make path-gated checks fail-safe — catches Incidents 1–3 class early; closes the silent-skip gap. [no Azure, days]
4. Low-risk auto-merge on green CI — reclaims reviewer time. [no Azure, days]
5. Optional gh-aw → issue → Copilot coding-agent triage/escalation — intelligent layer atop 1–4. [no Azure, days–week]
6. Gated GPU e2e via OIDC submit-and-poll to scale-from-zero OSMO/AML, LeRobot approval gate + Environment — the only tier that catches GPU-runtime regressions. [needs GPU subscription/funding]
7. Strategic spike: evaluate Renovate migration for true cross-ecosystem + pep621/uv intelligence. [no Azure, spike]

Each of 1–5 is independently shippable and reduces regression/noise now; 6 is the funded capstone; 7 is a fork in the road for the dependency layer.

## Presentation artifact

A narrated deck conveys this research, restructured as **AA Current state → per-phase (A Problem today · B What others do · C Recommendation) → Roadmap & close**, with real config/YAML on both current state and proposed changes. Built on the corporate `Global-Skilling-PowerPoint-Template.pptx` (Microsoft brand: blue/teal/orange covers and dividers, white content slides, Segoe). Generator + assets live under the session workspace (`presentation/gen_content.py`, `slides_src.py`, `build_video.sh`); the deck is 48 slides with a ~1.8× narrated MP4. Not committed to the repo.

## Current state — config & code reference

Grounded snippets documenting what ships today (cited to real files).

**Dependency intake** — 21 ecosystem blocks, every group a wildcard, pins added reactively (`.github/dependabot.yml`):

```yaml
- package-ecosystem: uv
  directory: /training/rl
  groups:
    training-dependencies:
      patterns: ["*"]          # catch-all: no risk split
  ignore:
  - dependency-name: marshmallow
    versions: [">=4.0.0"]      # reactive pin, post-breakage
# … ×21: npm, 10× uv, terraform, go, docker, actions
```

**CI & testing** — CPU-only runners; torch force-installed, desynced from the committed lock (`.github/workflows/pytest-training.yml:19,41`; lock pins torch 2.10.0 in `training/il/lerobot/uv.lock` — live desync, PR #958 / commit 36ba1ba):

```yaml
jobs:
  test:
    runs-on: ubuntu-latest          # 4 vCPU · 16 GB · ~14 GB disk · NO GPU
    steps:
      - run: uv sync --group dev
      - run: uv pip install torch==2.11.0   # force-installed; lock pins 2.10.0
```

**Agentic review** — one advisory, hand-triggered, read-only workflow (`.github/workflows/aw-dependabot-pr-review.md`):

```yaml
on:
  slash_command:
    name: aw-dependabot-review   # maintainer-triggered; can run before CI
permissions:
  contents: read
  pull-requests: read            # advisory only — never writes
```

## Proposed changes — config & YAML reference (by phase)

Illustrative target configs for each phase (the deck shows current-vs-proposed side by side).

**Phase 0 — group by risk + cooldown** (`.github/dependabot.yml`, config-only):

```yaml
groups:
  prod-minor-patch: { dependency-type: production,  update-types: [minor, patch] }
  dev-deps:         { dependency-type: development, update-types: [minor, patch] }
# majors NOT grouped → isolated for review
cooldown: { default-days: 7 }     # HF-style stability window
# security updates stay ungrouped + fast-tracked
```

**Phase 0 — reviewer waits for green CI** (AW reviewer frontmatter): trigger `on: workflow_run: { workflows: ["PR Validation"], types: [completed] }`, `skip-if-check-failing: true`, `add-comment: { hide-older-comments: true }`. Keep the `slash_command` as a manual override.

**Phase 1 — smoke-cpu job** (`.github/workflows/smoke-cpu.yml`, every PR, ~$0):

```yaml
steps:
  - run: uv lock --check                                   # resolution drift
  - run: uv pip install torch --index-url https://download.pytorch.org/whl/cpu
  - run: python -c "import lerobot, torch"                 # ABI / import smoke
  - run: ./training/rl/scripts/submit-osmo-training.sh --config-preview
  - uses: jlumbroso/free-disk-space@<sha>
  - run: docker build -f evaluation/sil/docker/Dockerfile.lerobot-eval .
```

The CPU-torch index is the enabling trick (the committed lock pins the cu12 build); `--config-preview` already exists on the submit scripts but must be extended to emit rendered YAML for schema validation.

**Phase 2 — auto-merge low-risk** (cheerio pattern):

```yaml
- uses: dependabot/fetch-metadata@<sha>
  id: meta
- if: steps.meta.outputs.update-type == 'version-update:semver-patch'
  run: gh pr merge --auto --squash "$PR_URL"   # waits for green CI
```

**Phase 3 — gated GPU e2e** (the only tier that catches GPU-runtime regressions; needs funding):

```yaml
on: { pull_request_review: { types: [submitted] } }
jobs:
  e2e-gpu:
    if: github.event.review.state == 'approved' && github.event.pull_request.head.repo.fork == false
    environment: e2e-approval       # required-reviewers gate
    steps:
      - uses: azure/login@v2         # OIDC — no stored secret
      - run: ./training/rl/scripts/submit-osmo-training.sh   # scale-from-zero pool 0→N→0
```

**Spike — Renovate** (`renovate.json`, justified only by the uv/pep621 edge):

```json
{
  "extends": ["config:best-practices"],
  "minimumReleaseAge": "3 days",
  "pep621": { "enabled": true },
  "packageRules": [{ "matchUpdateTypes": ["minor", "patch"], "automerge": true }]
}
```

## Deep-dive addenda (2026-06-22) — generalist primer + verified precedents

Five subagent investigations expand this research for a CI/CD-generalist audience. Full captures in `subagents/2026-06-19/`.

### Generalist primer (`tutorial-primer.md`)
Teaching units (each cited to repo + GitHub docs): Dependabot mechanics (version vs **security** streams, `groups`/`ignore`/`cooldown`/PR-limit, native lockfile regen); uv & lockfiles (PEP 621 `[project]` manifest vs resolved `uv.lock`; `uv lock --check` gate); GHSA/CVSS (security PRs must not be batched/delayed); CI gating tiers (one `changes` job + `if:` + a single aggregate required check; naive `paths:` silently skips — the #691/#547 failure mode); running untrusted PR code (`pull_request` fork = no secrets vs `pull_request_target` = secrets → "pwn request"; Environments + required reviewers + OIDC). Plus an 18-term glossary.

### The 21 Dependabot contexts (`ctx-21-dependabot-contexts.md`)
The 21 `package-ecosystem` blocks are not one app — they are independent runtime stacks: Training-RL (Isaac Lab SKRL/RSL-RL, Py 3.11, numpy 1.26; `azureml:isaaclab-training-env`), Training-IL (LeRobot ACT/Diffusion; full AzureML command-job + pipeline), Evaluation/SIL (ONNX/Torch + the eval container image), data-pipeline, Dataviewer (FastAPI backend + React 19 frontend + 2 Docker images), 4 Terraform roots + Go contract tests, and docs/root tooling. High **volume** (each ecosystem its own cadence) and high **blast radius** (a "safe" Python bump can break a CUDA/Torch/Isaac ABI the other contexts never exercise). The pins (`torch`, `numpy`, `marshmallow`, `packaging`, `av`) encode real runtime constraints. Cited AzureML job-contract excerpt (`training/rl/workflows/azureml/train.yaml:53-63`).

### gh-aw (`ghaw-deepdive.md`)
gh-aw = markdown workflow compiled to `.lock.yml`; `engine` + trigger + read-only `tools`; the agent writes ONLY through declared `safe-outputs` (add-comment/create-issue/create-pull-request) — that is the safety model. Repo's today: `aw-dependabot-pr-review.md` (slash_command, read-only, add-comment). Proposed: `workflow_run` after PR Validation + `skip-if-check-failing` + `hide-older-comments` + `create-issue`→assign Copilot. (Verified field `slash_command`/`label_command`; no separate top-level `command` trigger.)

### NeMo gated agentic loop (`nemo-agentic-loop.md`) — REAL precedent
`NVIDIA-NeMo/NeMo:.github/workflows/claude-babysit-pr.yml` is a verified human-gated "investigate → plan-comment → human `@claude go ahead` → execute-fix (team-verified) → re-run CI" loop; the agent is read-only in the propose phase ("do NOT edit or push"). GPU CI is gated via `cicd-wait-in-queue` bound to `environment: test` (queue-bot/human approval); fork PRs are mirrored to `pull-request/NNN` branches (avoids `pull_request_target` "pwn request"); GPU runs on self-hosted `nemo-ci-aws-gpu-x2`. This concretely substantiates both the Phase-2 agentic-triage and Phase-3 gated-GPU recommendations.

### Renovate in Microsoft OSS (`renovate-msft-oss-adoption.md`) — decision evidence
Verdict: **Dependabot-dominant by ~10–20×**; Renovate is a niche minority (~19 `microsoft`-org repos ≈ 1.5–3%, mostly the VS-team `microsoft/vs-renovate-presets` cluster; Azure 1, dotnet 1, `github` org 0). OSPO promotes Dependabot, never mentions Renovate. The Mend GitHub App needs org approval (real friction; VS/M365 teams obtained it) — **but `renovatebot/github-action` runs Renovate with no App approval**, dropping the barrier to ~0. Migration auto-detects all our ecosystems; custom pins/groups/the `gh-aw-actions` exclusion need manual `packageRules` (~2–3 h AI-assisted + ½–1 day validation — moderate, not trivial). **Reframing applied to deck:** Renovate's real edge is cross-ecosystem grouping (NOT pep621/uv — Dependabot supports uv and this repo uses it); keep as a scoped, github-action spike decided on merit.

### Presentation (updated)
Deck rebuilt on `Global-Skilling-PowerPoint-Template.pptx` (Microsoft brand), now **62 slides**: added an up-front **Primer** section (Dependabot/uv/GHSA/gh-aw/CI-gating/untrusted-PR + glossary), the **21-contexts** detail (+ AzureML env example), a **gh-aw today-vs-proposed** codecompare, **NeMo babysitter** + **NeMo GPU-gate** code slides, and the **Renovate reality-check** evidence slide. Durable requirements tracked in `presentation/PRESENTATION_SPEC.md` (session workspace). Narration: bare-caps acronyms (GPU/CPU/CI/SDK), spelled `O-I-D-C`, no `pull-request` hyphen; 1.8× MP4.

## Fact-check pass (2026-06-22)

Five parallel verification subagents checked every deck claim against the live repo, registries, gh-aw/NeMo sources, and GitHub/Renovate docs. Captures: `subagents/2026-06-19/verify-{A-repo,B-gpu,C-ghaw-nemo,D-oss,E-renovate-msft}.md`. Outcome: most claims PASS; corrections applied to the deck:

- **Dependency churn (was overstated low):** live `gh` count is ~350 Dependabot PRs opened (~216 merged), ~24/week all-time / ~28/week recent — not "~17/week, ~210". Stat slide updated.
- **21 contexts:** 9 uv (not "ten"); 3 npm, 4 Terraform, 3 Docker, 1 Go, 1 Actions. Several Terraform/Docker/Go blocks are ungrouped (not "every group a wildcard").
- **Incidents:** `azureml-mlflow` drop belongs to #809 (not #790); removed the #346/release-please-drift claim (#346 is a Dependabot PR). "8 vs 0" reframed as "regressions & test-integrity gaps" (2 of 8 are CI path-filter gaps, not runtime).
- **cheerio auto-merge:** merges semver-minor OR -patch on `pull_request_target` (snippet was patch-only); snippet + framing corrected.
- **HF transformers cooldown:** the 7-day `cooldown` is on its github-actions deps only; wording softened to cite the Dependabot feature, not a Python-dep example.
- **gh-aw:** all fields verified real; fixed an indentation error in the reviewer codecompare (`skip-if-check-failing` nests under `on:`, `add-comment` under `safe-outputs:`). `assign-to-agent:` noted as the purpose-built handoff vs `assignees:[copilot]`.
- **Renovate-in-MSFT:** `dotnet` org has ~9 Renovate repos (not 1); OSPO wording softened (page implies GitHub-native features, doesn't name Dependabot). ~19 microsoft-org count and the Dependabot-dominant direction confirmed exactly.
- **GPU/runtime:** Isaac 8.408 GB anonymous pull re-confirmed live; runner specs, eval-image base, RL/SKRL import boundary, CPU-step blockers all PASS. `--config-preview` prints parsed config today (does not render YAML) — smoke-slide wording corrected.
- **Capstone ordering:** removed forward-references to "the capstone" before Phase 3 introduces the term.

Deck rebuilt (62 slides) and video re-rendered (~18m51s @ 1.8×) post-corrections.

## Tier-1 real-image CPU smoke — prototyped (2026-06-22)

Followed the discussion to its conclusion: a CPU agent CAN catch the costly regression class (#809/#790/#958) by importing **inside the real runtime image** on the real interpreter — because those failures occur at dependency-resolution/install/import time, before any GPU compute.

**Executed proof (this session):**
- Against the repo's real `training/rl` manifest/lock on the host: `uv lock --check --python 3.12` → `error: ... incompatible with the project's requires-python ==3.11.*` (exit 2). A CPU `uv` command deterministically catches the #809 interpreter mismatch. (The RL project now hard-pins `requires-python = "==3.11.*"`, a direct lesson from #809.)
- **Inside the actual `nvcr.io/nvidia/isaac-lab:2.3.2` image** (anon-pulled, run linux/amd64 under emulation on an arm64 host, CPU only): runtime interpreter confirmed **Python 3.11.13**; installing a dependency with `requires-python = ">=3.12"` (the #809 shape) → `ERROR: Package requires a different Python: 3.11.13 not in '>=3.12'`. Image ships pip 24.3.1; uv is installed by the workflow.

**Authored + statically validated:** `isaac-import-smoke.sh` (shellcheck clean) and `smoke-environments.yml` (path-gated matrix, free-disk-space, fail-safe aggregate check; actionlint unavailable locally). Artifacts in the session workspace `files/prototype/` and capture `subagents/2026-06-19/proto-isaac-cpu-smoke.md`.

**Design folded into deck Phase 1:** "Two depths of CPU smoke" (Tier 0 venv vs Tier 1 real-image), the Tier-1 recipe, a per-image/disk path-gated matrix, the `rsl_rl/train.py` 2-line `AppLauncher`→`main()` unlock (widens CPU import surface), and a "We prototyped it — it catches #809" result slide with the executed evidence.

**Limits (unchanged):** Tier 1 catches install/import/packaging breaks; CUDA-kernel correctness, Isaac Sim/Vulkan/MIG, and training convergence still require the gated GPU tier.

Deck now 68 slides; video ~22m26s @ 1.8×.
