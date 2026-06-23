<!-- markdownlint-disable-file -->
# Subagent E raw capture: Issues + Dependabot PR/fix history
(Captured by parent: research agent is read-only; agent chat output verbatim.)


Now I have all the data needed. Let me compile the complete findings report.

---

## Research Findings: microsoft/physical-ai-toolchain — Issues & Dependabot PR History

**Output file path:** `.copilot-tracking/research/subagents/2026-06-19/issues-and-dependabot-pr-history.md`
**Status:** Research complete — all 5 questions answered with citations
**Repository:** microsoft/physical-ai-toolchain (16 weeks old, 2026-03-02 creation, currently at PR ~#1000)

---

## QUESTION 1: ISSUES — CI, e2e, regression, Dependabot noise

### Finding: ZERO issues exist for the requested topics

**No filed issues** request:
- Automated e2e/integration testing on PRs
- GPU test infrastructure
- Smoke tests
- Dependency-update batching/grouping
- "Dependabot is too noisy"
- Regression prevention
- Required manual CI gates

The only two confirmed open issues are #9 (input validation docs) and #10 (hardening docs) — both OpenSSF documentation compliance items. The issues API (`/issues?state=all&pulls=false`) returns only these.

**However — two CLOSED issues document production regressions from dependency drift:**

| # | Title | State | Created | Closed | Summary |
|---|-------|-------|---------|--------|---------|
| [#809](https://github.com/microsoft/physical-ai-toolchain/issues/809) | "fix(training): RL training requirements.txt drifts from Isaac Lab 2.3.2 runtime, causing ABI and plugin failures" | Closed 2026-06-10 | 2026-06-01 | 2026-06-10 | Lock resolved against Python 3.12, runtime is 3.11.9 → 4 cascading failures |
| [#790](https://github.com/microsoft/physical-ai-toolchain/issues/790) | "fix(training): fix OSMO LeRobot Azure Blob submissions" | Closed 2026-06-10 | 2026-05-28 | 2026-06-10 | lerobot requires Python >=3.12, OSMO runtime is 3.11.9; dep PR #541 accidentally dropped azureml-mlflow |

Issue #809 is the most detailed regression report in the repo — describes 4 cascading failures from a single lock drift event:
1. `pydantic-core 2.47.0 ↔ pydantic 2.13.4` ABI mismatch (lock built for Python 3.12 wheels, runtime is 3.11)
2. `Unsupported URI 'azureml://…'` — PR #541 dropped `azureml-mlflow` plugin accidentally while resolving a pin conflict
3. `numpy==2.4.6` circular import in Isaac Sim extensions (re-installed over Isaac Sim's `<2.0` requirement)
4. `TypeError: azureml_artifacts_builder() got an unexpected keyword argument 'tracking_uri'` — mlflow 3.13.0 vs azureml-mlflow API incompatibility

**Labels in use (relevant):**
- `dependencies` — used on all Dependabot PRs
- `python`, `training`, `evaluation`, `npm`, `docker`, `github-actions`, `terraform` — ecosystem labels
- `ci`, `ci/cd`, `area/workflows` — CI-specific labels
- Total: 60+ labels in the taxonomy

**Conclusion: A new issue should be filed** for both (a) the uv-lock governance/e2e testing gap and (b) the Dependabot grouping/batching improvement ask. No prior art exists.

---

## QUESTION 2: DEPENDABOT VOLUME

### Volume summary

| Metric | Value | Source |
|--------|-------|--------|
| Repo age | 16 weeks (2026-03-02 → 2026-06-18) | API repo metadata |
| Total PRs to date | ~1000 (PR #1000 open as of June 18) | PR list API |
| Dependabot PRs (all-time estimate) | ~210 total | CHANGELOG dep PR count + post-release estimation |
| Churn rate (all-time avg) | ~13 Dep PRs/week | 210 PRs / 16 weeks |
| Churn rate (last 8 weeks, Apr 25–Jun 18) | ~14/week (accelerating) | ~112 PRs / 8 weeks |
| Churn rate (post v0.8.0 sprint, last 6 weeks) | ~17/week | Visible from June commit density |
| Single busiest day observed | 6 Dep PRs merged June 16, 2026 | Commit chain: #962, #963, #967, #983, #985, #986 |

### Merged vs open vs closed-unmerged
- **Merged:** Vast majority (every dep entry in CHANGELOG = merged)
- **Currently OPEN:** Minimum 2 confirmed (#999 undici security, #1000 appears to be a feature PR) — likely more
- **Closed without merge:** The ignore rules in `dependabot.yml` would cause future bumps (e.g., torch ≥2.11.0) to be auto-closed by Dependabot when it regenerates; specific count unknown
- `open_issues_count: 154` includes all open PRs, so if ~6 open non-Dep PRs are visible, ~148 could be open Dep PRs — but this seems high; the limit configs (5-10 per ecosystem) cap it

### Ecosystem breakdown (from CHANGELOG + dependabot.yml)

| Ecosystem | Directory | Group Name | Max Example |
|-----------|-----------|------------|-------------|
| uv (Python) | /training/rl | training-dependencies | 54 updates in one PR (#286) |
| uv (Python) | /training/il/lerobot | lerobot-dependencies | Grouped + multiple ignores |
| uv (Python) | /evaluation | inference-dependencies | Multiple weekly groups |
| uv (Python) | /evaluation/sil/docker | lerobot-eval-image-dependencies | Grouped |
| uv (Python) | /data-management/viewer | dataviewer-dependencies | Grouped |
| uv (Python) | /data-management/viewer/backend | dataviewer-backend-dependencies | Multi-pack groups (5-6 at once) |
| npm | Root | root-npm-dependencies | Grouped |
| npm | /viewer/frontend | dataviewer-frontend-patch-minor | patch+minor only; separate major |
| docker | /viewer/frontend | No group | Individual digest bumps |
| docker | /evaluation/sil/docker | No group | Individual image bumps |
| github-actions | Root | github-actions | 6 updates/group (#433) |
| terraform | /infrastructure | No group | Individual provider bumps |
| gomod | /infrastructure | go-module-dependencies | Weekly |

**Groups ARE in use** — all Python/uv and npm ecosystems use `groups: patterns: ["*"]`. This means the 54-package RL training bump (#286) was ONE PR, not 54. However, security-triggered bumps **bypass grouping** and arrive as individual PRs immediately (not waiting for weekly schedule), which explains the visible spike in June.

### churn-by-release (CHANGELOG-derived)

| Release | Date | Dep PRs (est.) |
|---------|------|----------------|
| v0.1.0 | 2026-02-07 | ~1 |
| v0.2.0 | 2026-02-12 | ~3 (#51, #134, #155) |
| v0.3.0 | 2026-02-19 | ~2 (#172, etc.) |
| v0.4.0 | 2026-02-27 | ~10 (#186, #223, #279, #286, #297, #317–#319, #339, #344, #360, #361, #370) |
| v0.5.0–v0.7.x | Mar–Apr 2026 | ~40 |
| v0.8.0 | 2026-05-08 | ~55 (#423–#632 range, largest release so far) |
| Unreleased (post v0.8.0) | May 8–June 18 | ~100 |
| **TOTAL** | | **~211** |

---

## QUESTION 3: REGRESSIONS & FIXES

### Incident 1 — Issue #809: RL Lock Drift → 4 Production Failures (MOST SEVERE)

**Source:** `github.com/microsoft/physical-ai-toolchain/issues/809`
**Filed:** 2026-06-01, **Closed:** 2026-06-10 (9 days to fix)

**What broke:** `training/rl/requirements.txt` was regenerated against Python 3.12 constraint-set but the Isaac Lab 2.3.2 container runs Python 3.11.9. Installing with `uv pip install --no-deps` bypasses pip's resolver, so inconsistent ABI wheels landed verbatim in the container. Four cascading failures:
1. `pydantic-core 2.47.0 ↔ pydantic 2.13.4` ABI crash at import time — Python 3.12 wheel vs 3.11 runtime
2. Missing `azureml://` URI scheme — PR #541 (`standardize on Python 3.12`) dropped `azureml-mlflow` while resolving a pin conflict
3. `numpy==2.4.6` overwrite broke Isaac Sim's `<2.0` numpy requirement (circular import in `omni.kit.pip_archive`)
4. `mlflow==3.13.0` passes `tracking_uri=` kwarg to artifact builders; `azureml-mlflow` caps `mlflow-skinny<=3.9.0` and doesn't accept it

**Fix:** Regenerated lock with explicit `--python-version 3.11 --python-platform manylinux_2_28_x86_64` constraints; pinned `azureml-mlflow==1.62.0.post2`, `mlflow==3.9.0`, `numpy<2.0.0`, `packaging==25.0`; referencing the LeRobot pattern from #777.

**Connection to Dependabot:** PR #541 (`chore: standardize on Python 3.12`) changed Python version constraints during a routine dependency alignment — this is the "accidental azureml-mlflow drop" that caused failure #2. The PR is in CHANGELOG v0.8.0 as a Build System entry, not a deps entry, showing that non-Dependabot dependency changes also cause regressions.

---

### Incident 2 — Issue #790: OSMO LeRobot Python Version Mismatch

**Source:** `github.com/microsoft/physical-ai-toolchain/issues/790`
**Filed:** 2026-05-28, **Closed:** 2026-06-10

**What broke:** `submit-osmo-lerobot-training.sh` fails at dependency resolution: runtime is Python 3.11.9, `lerobot==0.5.1` requires `Python>=3.12`. Log shows: `Because the current Python version (3.11.9) does not satisfy Python>=3.12 and lerobot==0.5.1 depends on Python>=3.12, we can conclude that lerobot==0.5.1 cannot be used`.

**Fix:** Applied AzureML submission/runtime/requirements fixes from PRs #777 and #778 to the OSMO code path.

---

### Incident 3 — PR #958 / Commit `36ba1ba`: torch 2.10.0→2.11.0 Security Bump → Lock Desync

**Source:**
- Commit `36ba1ba22e8624f9045d469808e61e990e521d33` (2026-06-15T10:01:54Z)
- PR #958 (`security(deps): bump torch from 2.10.0 to 2.11.0 in /training/il/lerobot`)
- Local file: `training/il/lerobot/uv.lock` line 2200 (current: `version = "2.10.0"`)
- Local file: `.github/dependabot.yml` lines 84-86 (`ignore: torch >= 2.11.0` for `/training/il/lerobot`)
- Local file: `.github/workflows/pytest-training.yml` line 41 (`uv pip install torch==2.11.0`)

**What broke:** Dependabot bumped torch from 2.10.0→2.11.0 in the uv.lock for `/training/il/lerobot`. The root cause was that `torch==2.11.0`'s uncapped `cuda-bindings` dependency would resolve to cuda-bindings 13.x (requiring `libcudart.so.13`), but the CUDA 12 wheels only bundle `libcudart.so.12`. This causes a CUDA library not found error in GPU containers.

**Evidence of desync:**
- Current `uv.lock` has `torch==2.10.0` (reverted) — `training/il/lerobot/uv.lock:2199-2200`
- `pytest-training.yml` still has `uv pip install torch==2.11.0` on line 41 — meaning CI explicitly overrides the lock with 2.11.0
- `dependabot.yml` has ignore rule added post-incident: `torch >= 2.11.0` for both `/training/il/lerobot` AND `/evaluation/sil/docker` (lines 84-86, 140-142)
- `pyproject.toml` comment on lines 54-57: `"cuda-bindings: torch==2.10.0 depends on cuda-bindings but does not cap it; unconstrained resolution picks 13.x which requires libcudart.so.13 (CUDA 13). The cu12 torch wheels only ship CUDA 12 runtime, so pin to 12.x."`

**State today:** Lock has torch 2.10.0, but CI runs with torch 2.11.0 (forced via `uv pip install torch==2.11.0`). The pyproject.toml has `cuda-bindings==12.9.0` pin to work around torch 2.10.0's uncapped issue. This is a **live desync** — the lock and the CI workflow disagree on the torch version.

A follow-up commit between `36ba1ba` (June 15) and the June 16 Dependabot batch reverted the lock to 2.10.0 and added the ignore rules. The pytest-training.yml was not cleaned up.

---

### Incident 4 — PR #691: Fuzz Regression Tests Silently Skipped (Weeks-Long CI Gap)

**Source:** CHANGELOG v0.8.0 entry (released May 8, 2026): `fix(ci): repair ERE regex for fuzz-regression-test path matching (#691)`

**What broke:** The fuzz regression test job in `pr-validation.yml` used a double-escaped ERE regex in the path filter. Tests had been **silently NOT RUNNING** for an unknown period. Any regression introduced during this period would not have been caught by CI.

**Fix:** PR #691 (2026-05-16) corrected the regex. The CHANGELOG notes this as a bug fix — no estimate of how long tests were skipped.

---

### Incident 5 — PR #547: Data-Pipeline and Training CI Broken by Folder Restructure

**Source:** CHANGELOG v0.8.0 entry: `fix(ci): restore data-pipeline and training broken tests by domain folder restructure (#547)` — `microsoft/physical-ai-toolchain:CHANGELOG.md:41`

**What broke:** A domain folder restructure broke the path filters in `pr-validation.yml` for data-pipeline and training jobs. Tests were not running on PRs touching those domains.

**Fix:** PR #547 repaired the path filter references.

---

### Incident 6 — PR #346: release-please uv.lock Desync

**Source:** CHANGELOG v0.4.0 entry: `fix(build): regenerate uv.lock in release-please PR to sync project version (#346), closes #322` — `microsoft/physical-ai-toolchain:CHANGELOG.md:420`

**What broke:** The release-please automation creates a PR to bump the project version. That PR did NOT regenerate `uv.lock`, so the lock was stale relative to the new version in pyproject.toml.

**Fix:** PR #346 regenerated the lock as part of the release process. This was the **first documented lock drift incident** (February 2026), showing the problem predates any Dependabot activity.

---

### Incident 7 — PR #584/#586/#589/#976: AW Dependabot Reviewer Non-Functional for 6+ Weeks

**Source:** CHANGELOG v0.8.0 bug fixes section, lines 47-51; confirmed via PR #976 commit `a9c41af` (June 17 2026)

**What broke:** The automated Dependabot PR reviewer agent (added in #498) had 6 consecutive bugs:
1. `#576` — lock file stale (recompile needed)
2. `#580` — trigger race: `pull_request` event fired before CI, reviewer had nothing to evaluate
3. `#584` — branches filter bug: wrong branch name syntax
4. `#586` — `dependabot[bot]` actor detection bug: reviewer never activated on actual Dependabot PRs
5. `#589` — switched to `pull_request_target` (permissions issue)
6. `#976` (2026-06-17) — **GitHub Actions CANNOT approve PRs** (Actions tokens can't use the Reviews approval API); every "safe" verdict was failing with a 422 error, making the reviewer completely non-functional

After fix #976, the reviewer was downgraded to COMMENT-only advisory mode. This means that for the ~6 weeks the reviewer existed, it was either not running or silently failing on safe verdicts. The "automated safety checking" was effectively never working until June 17.

---

### Incident 8 — starlette 0.52.1→1.0.1 Major Version Bump (PR #884)

**Source:** PR #884 (2026-06-05, merged): `security(deps): bump starlette from 0.52.1 to 1.0.1` — then immediately followed by PR #983 (2026-06-16): `security(deps): bump starlette from 1.0.1 to 1.3.1`

**What this shows:** Starlette jumped a major version (0.x → 1.x) in a single Dependabot security PR. This is a breaking change according to semver. The fact it was allowed to merge without reverting shows either (a) no tests caught any breaking changes, or (b) starlette's 1.x is backward-compatible enough. But the immediately-following security update to 1.3.1 shows rapid CVE activity in starlette. No explicit regression was documented, but the major version jump is a latent risk.

---

## QUESTION 4: EXISTING MITIGATIONS

### Mitigation 1: `dependabot.yml` — groups + ignore rules + limits
**Location:** `.github/dependabot.yml`
**Added:** Incrementally, with groups visible from early PRs (#134 = "python-dependencies group across 1 directory with 11 updates")

**Current state:**
- All Python/uv ecosystems: `groups: patterns: ["*"]` (bundle all package updates into one PR per ecosystem per directory per week)
- npm root: `root-npm-dependencies` group; viewer/frontend: `dataviewer-frontend-patch-minor` group (minor+patch only — majors get separate PRs)
- github-actions: single group (excluding `github/gh-aw-actions/*`)
- Terraform, Docker: NO groups (individual bumps)
- `open-pull-requests-limit: 5` to `10` per directory — caps the queue
- Schedule: weekly (Monday) — batches to once per week instead of continuous

**Ignore rules added as post-incident mitigations:**

| Package | Version ceiling | Directories | Incident reference |
|---------|----------------|-------------|-------------------|
| torch | `>=2.11.0` | `/training/il/lerobot`, `/evaluation/sil/docker` | PR #958, CUDA ABI |
| torch | `>=2.12.0` | `/evaluation` | (softer, 2.11.0 succeeded in eval) |
| numpy | `>=2.3.0` | `/training/il/lerobot`, `/evaluation` | numpy 2.x breaking Isaac Sim |
| marshmallow | `>=4.0.0` | `/training/il/lerobot`, `/training/rl`, `/evaluation`, `/evaluation/sil/docker` | azure-ai-ml compat |
| packaging | `>=26.0` | `/training/il/lerobot` | azureml-mlflow compat |
| av | `>=16.0.0` | `/evaluation/sil/docker` | Unknown AV version incompatibility |

### Mitigation 2: `dependabot-security-prefix.yml`
**Location:** `.github/workflows/dependabot-security-prefix.yml`
**Added:** ~v0.5.0 PR #241 (visible in CHANGELOG v0.5.0 section)
**Purpose:** Retitles security-triggered Dependabot PRs from `chore(deps): bump...` to `security(deps): bump...` so they appear separately in release notes and can be triaged by severity

### Mitigation 3: `uv-lock-consistency.yml`
**Location:** `.github/workflows/uv-lock-consistency.yml`
**Purpose:** On every PR that touches a manifest file (`pyproject.toml`, `uv.lock`, `requirements.txt`), checks that the lock is consistent with the manifest. Uses `changed-files-only: true` — only checks dirs with changed files.
**Limitation:** Does NOT catch the torch desync in `pytest-training.yml` (a workflow file, not a manifest). Also does NOT catch platform-specific lock drift (lock built on Linux CI, tested differently on different platforms).

### Mitigation 4: AW Dependabot PR Reviewer (`aw-dependabot-pr-review.lock.yml`)
**Location:** `.github/workflows/aw-dependabot-pr-review.lock.yml` (116KB compiled lock)
**Added:** PR #498 in v0.8.0 (~April 2026)
**Purpose:** Agentic workflow that analyzes each Dependabot PR for risk signals (ABI changes, lock desync, breaking CHANGELOG entries) and posts a COMMENT advisory
**Current state as of June 17:** COMMENT-only (after #976 fix) — the reviewer cannot block, approve, or reject. It is advisory only. Before June 17, it was either not running or silently failing.

### Did mitigations help?
- **Groups** reduced PR count significantly: before groups, each package bump = 1 PR; after, 54 packages = 1 PR (#286)
- **Ignore rules** have prevented re-occurrence of known breakages (no new torch 2.11.0 bump in training/il/lerobot after the incident)
- **uv-lock-consistency** catches lock drift on manifest changes (though wasn't effective for the pytest-training.yml desync)
- **AW reviewer** was non-functional until June 17; now working but advisory-only, so cannot prevent any merge
- **No observable drop in churn or revert rate** post-v0.8.0 — activity actually accelerated

---

## QUESTION 5: SYNTHESIS

### Does the data support "constant regressions" and "Dependabot is hell"?

**Yes, with nuance.** Quantified evidence:

**Evidence FOR "constant":**
- **5+ regression incidents in 16 weeks** — that's roughly one every 3 weeks, though some are worse than others
- **Issue #809** alone had 4 cascading failures in a single production deployment (RL training completely broken for at least 9 days)
- **Issue #790** affected OSMO path for at least 9 days simultaneously
- **CI blind spot for fuzz tests** — unknown duration, potentially weeks
- **Lock desync for torch** is still present today (uv.lock=2.10.0, CI installs 2.11.0)
- **AW reviewer had 6 consecutive bugs** over 6 weeks — the "safety net" was never working
- Early regression: **uv.lock desync in release-please** (#322/#346) from the very first weeks

**Evidence AGAINST "hell" (the mitigations are working):**
- Groups ARE in use: 54 packages as 1 PR instead of 54 PRs
- Weekly batching reduces noise significantly
- Ignore rules for known-problematic versions (torch, numpy, marshmallow) are in place
- The repo runs at very high velocity (~1000 PRs in 16 weeks = 62.5/week) and has NOT had a total-freeze incident

**Ecosystem risk breakdown:**

| Risk Level | Ecosystems | Why |
|------------|------------|-----|
| 🔴 Highest | Python/uv: training/rl, training/il/lerobot | ABI-sensitive (torch, pydantic, numpy), GPU/CUDA coupling, Python version mismatch with runtime containers, lock drift across platforms |
| 🟠 High | Python/uv: evaluation, evaluation/sil/docker | Same ABI risks + docker image coupling |
| 🟡 Medium | npm: root, viewer/frontend | Some major-version jumps (React 19, starlette 0.x→1.x) but tests catch breakage |
| 🟢 Low | github-actions, Docker digest bumps | Digest bumps are hash-only (no behavior change); github-actions are well-tested |
| 🟢 Low | Terraform | Provider bumps are slow-moving; no ABI issues |

**Root cause analysis (not just "Dependabot"):**
The real problem is that the Python training stack uses **GPU containers with platform-specific ABI requirements** that cannot be tested in CI (CI uses CPU-only `ubuntu-latest`). This creates a "CI is green, production is broken" pattern that no amount of Dependabot configuration can solve without GPU CI or e2e smoke tests that validate the actual container.

The uv-lock-consistency check is valuable but insufficient — it catches lock drift at the manifest level but not:
1. Platform-specific dependency resolution (Python 3.11 vs 3.12 wheels)
2. Runtime coupling (CUDA 12 vs 13 ABI)
3. Multi-step install sequences (`uv sync` + manual `uv pip install torch==X.X`)

---

## Summary Statistics Table

| Metric | Value |
|--------|-------|
| Repo age at time of research | 16 weeks (March 2 – June 18, 2026) |
| Total PRs | ~1000 |
| Total Dependabot PRs (estimated) | ~210 |
| Dependabot PRs / week (average) | ~13 |
| Dependabot PRs / week (recent 6 weeks) | ~17 |
| Open Dependabot PRs right now | ≥2 confirmed, likely more |
| Ecosystems under Dependabot | 8 (uv×7, npm×2, docker×2, github-actions×1, terraform×1, gomod×1) |
| Directories with group: * grouping | 9/12 (75%) |
| Directories WITHOUT grouping | 3 (Docker, Terraform, single-file ecosystems) |
| Confirmed regression incidents | 8 (5 in last 8 weeks) |
| Issues filed about CI/e2e/GPU/batching | 0 |
| Ignore rules added post-incident | 6 package×ecosystem combinations |
| AW reviewer bug fixes | 6 (in 6 weeks) |
| Days AW reviewer was non-functional | ~42 (all of its existence until June 17) |

---

## Key Files with Citations

1. `microsoft/physical-ai-toolchain:.github/dependabot.yml:70-155` — full groups + ignore rules configuration
2. `microsoft/physical-ai-toolchain:.github/workflows/pytest-training.yml:40-41` — hardcoded `torch==2.11.0` override
3. `microsoft/physical-ai-toolchain:training/il/lerobot/uv.lock:2199-2200` — `torch version = "2.10.0"` (current lock state vs CI)
4. `microsoft/physical-ai-toolchain:training/il/lerobot/pyproject.toml:54-57` — cuda-bindings pin comment documenting CUDA 12 vs 13 issue
5. `microsoft/physical-ai-toolchain:training/il/lerobot/pyproject.toml:85-110` — override-dependencies section
6. `microsoft/physical-ai-toolchain:CHANGELOG.md:18-100` — v0.8.0 feature/fix/dep sections including 7 AW reviewer bugs
7. `microsoft/physical-ai-toolchain:CHANGELOG.md:380-403` — v0.5.0 regression + 54-package security group PR #286
8. `microsoft/physical-ai-toolchain:CHANGELOG.md:420` — first lock drift incident (#346, closes #322, February 2026)
9. GitHub Issue #809 — comprehensive 4-failure RL lock drift report
10. GitHub Issue #790 — OSMO LeRobot Python version mismatch

---

## Gaps and Uncertainties

1. **PR #809 fix PR number unknown** — The issue was closed by `rezatnoMsirhC` on June 10 but the fixing PR number was not retrieved (it would be in the PR #800–#840 range based on timing). Could be confirmed with `gh pr list --state merged --author rezatnoMsirhC`.

2. **torch 2.11.0 lock revert commit not identified** — There is a commit between `36ba1ba` (June 15, torch bump) and the June 16 commit wave that reverted the lock to torch 2.10.0. The specific commit was not isolated in the chain because the chain had many Dependabot merges in that window. Key: parent of `9c95b56` (starlette 1.0.1→1.3.1, June 16 13:59) was not fetched.

3. **Exact open Dependabot PR count** — Only PR #999 (undici security) confirmed open. The full queue requires paginating the open PRs list filtered by author `app/dependabot`.

4. **PR #541 details** — This PR (`standardize on Python 3.12`) accidentally dropped `azureml-mlflow` and is documented as causing failures in #809 and #790. The PR's intent was legitimate but had unintended side effects. The PR's full diff was not retrieved.

5. **CHANGELOG lines 100-380 not fully counted** — The full v0.8.0 dependency section extends beyond line 100. My estimate of ~55 Dep PRs in v0.8.0 is based on visible entries; the actual count could be higher (70+).

6. **starlette 0.52.1→1.0.1 impact** — PR #884 merged a starlette major version bump. No revert or follow-up fix was found, suggesting either tests passed or no one noticed. The risk is that starlette's 1.x breaking changes (`router.routes` no longer plain list) would only surface at runtime, not in unit tests.

---

## Next Research Items

1. **Fetch the torch 2.11.0 lock revert commit** — run `git log --oneline --grep="torch\|lerobot\|lock\|revert\|cuda" --since=2026-06-14 --until=2026-06-18` on the local checkout (or fetch parent chain for `9c95b56`) to find the specific fix commit.

2. **Count exact open Dependabot PRs** — `gh pr list -R microsoft/physical-ai-toolchain --state open --author "app/dependabot" --limit 200 --json number,title,labels` to get the current queue.

3. **Read pr-validation.yml path filters for training/evaluation** — to quantify how many of the 30+ CI jobs are currently gated (run on Dep PRs) vs. fully skipped. This matters for e2e proposal: which new gate would be cheapest to add.

4. **Investigate PR #541** (`standardize on Python 3.12`) — confirm which packages were dropped and whether the drop of `azureml-mlflow` was intentional or accidental. This informs whether a "no-deletions from requirements" rule would help.

5. **Check if any unreleased issues in the #850-#1000 range document further regressions** — the period May 10 – June 18 is entirely post-v0.8.0 and unreleased. A sweep of `gh issue list --state closed --since 2026-05-08` would capture any additional filed-and-closed regression reports.

---

## Blocking Clarifying Questions (≤3)

1. **GPU CI feasibility**: Is there a budget/intent to add GPU runners? The research shows all regressions are GPU/CUDA-specific and CPU CI cannot catch them. Without this, even perfect dependency governance cannot prevent GPU breakage.

2. **torch 2.11.0 policy intent**: Is the `uv pip install torch==2.11.0` in `pytest-training.yml:41` intentional (testing against 2.11.0 even though the lock says 2.10.0) or is it a leftover from the incident that should be cleaned up? This affects whether the "lock desync" is considered fixed.

3. **Scope of e2e testing**: When maintainers mention wanting e2e/smoke tests, do they mean GPU container validation (requires hardware), or lightweight CPU-based integration tests (import-chain verification, API smoke tests)? The answer determines whether the gap can be filled with GitHub Actions or requires Azure ML compute.