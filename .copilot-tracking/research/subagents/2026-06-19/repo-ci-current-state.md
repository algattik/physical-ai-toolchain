<!-- markdownlint-disable-file -->
# Subagent A: Repo CI / Dependabot / AW / E2E current state

Distilled capture by parent (research agent is read-only). File/line citations from the subagent run.

## 1. Dependabot (.github/dependabot.yml)
* ~17–20 ecosystem blocks (npm ×2 incl. docusaurus, uv/pip ×~10 subprojects, terraform ×4, gomod ×1, docker ×3). All `schedule: weekly`.
* Grouping IS already used, but as **wildcard catch-all groups** per ecosystem (one group bundling everything matched), NOT split by update-type (patch/minor vs major) or dependency-type (dev vs prod).
* ~7 `ignore` pins to hold back known-breaking majors: torch, numpy, marshmallow, packaging, av.
* Commit-message prefixes configured; security PRs retitled by dependabot-security-prefix.yml.

## 2. uv locks
* 9 committed `uv.lock` files (root + 8 subprojects). Lock = single source of truth; flat requirements.txt are NOT committed (derived at build).
* `.github/workflows/uv-lock-consistency.yml` runs `npm run lint:uvlock` → read-only `uv lock --check`; fails PR if lock drifts from manifest. Dependabot regenerates uv locks natively.

## 3. aw-dependabot-pr-review (.md + .lock.yml, .github/aw/)
* Trigger: **slash command `/aw-dependabot-review`**, **maintainer-only** (RBAC). Fires on a PR comment, NOT automatically — so it does NOT run on every rebase already.
* Output: 1 PR review + ≤5 inline review comments + ≤2 comments. Engine: Copilot (v0.79.8). Imports the `dependabot-pr-reviewer` agent (HVE-core).
* GAP (matches Katrien's concern): nothing makes it WAIT for CI to pass — a maintainer can invoke it before CI concludes, wasting tokens when CI will deterministically fail.

## 4. Other dependency/security workflows
* dependabot-security-prefix.yml: retitles security PRs (metadata only).
* dependency-review.yml: blocks PRs introducing moderate+ vulnerabilities (7 allowlisted advisories).
* dependency-pinning-scan.yml: enforces ~95% SHA-pinning of actions; SARIF upload.

## 5. CI orchestration
* pr-validation.yml ≈ 31 jobs (lint → tests → infra → security); main.yml ≈ 25+ (adds release-please).
* Required status checks are NOT explicit in committed code — must confirm via `gh api repos/microsoft/physical-ai-toolchain/branches/main`.

## 6. Existing e2e / integration tests (GPU need?)
* CPU-only (no GPU, no Azure): terraform output-contract (go-tests.yml, infrastructure/terraform/e2e/run-contract-tests.sh), terraform-tests (mock_provider, plan), fuzz-regression-tests.yml, data-pipeline/dm-tools/dataviewer pytest, frontend vitest, pester.
* Flagged GPU/Azure by A: training/eval/inference pytest (NOTE: these likely run CPU-mocked in CI per repo testing conventions — verify; A may have over-flagged).
* No existing automated test runs a real GPU or live cloud job in CI today.

## 7. Scale-from-zero backend (candidate e2e engine)
* OSMO control plane + backend on AKS (infrastructure/setup/03-*, 04-*). AKS GPU node pool autoscales **min_count=0 → N** on pending pod resource requests; scales back to 0 after cooldown. Checkpoints to Azure Blob.
* Job submission: training/rl/scripts/submit-osmo-training.sh, training/il/scripts/submit-osmo-lerobot-training.sh, evaluation/sil/scripts/submit-osmo-lerobot-eval.sh → generate OSMO workflow YAML → `osmo workflow create`.
* Also AzureML path (az ml job create) on the same Arc-connected AKS. Either is a submit-and-poll e2e engine with ~0 idle cost.

## 8. Smoke-test surface
* Exists: training/rl/scripts/smoke_test_azure.py — CPU-only Azure/MLflow connectivity check; wrapped in a unit test; NOT wired into CI.
* Submission scripts have NO `--config-preview` dry-run (deploy scripts do). Adding it would give a <1s CPU pre-flight that validates generated workflow YAML.
* Import smoke possible via `python -m ... --help` on training/eval entrypoints (loads torch/lerobot/etc.).

## A's clarifying questions
1. Which jobs are actually required status checks on main? (`gh api` to confirm.)
2. On-demand GPU e2e posture: slash-command (maintainer, cost-controlled) vs scheduled-on-main vs release-only?
3. Add `--config-preview` to submission scripts for cost-free CI dry-run?
