<!-- markdownlint-disable-file -->
# Subagent B raw capture: Intelligent Dependency Updates
(Captured by parent: research agent is read-only; this is the agent chat output verbatim.)


Now I have sufficient research to compile everything. Let me produce the full research in-response (since writing to files is prohibited), followed by the executive summary.

---

# Full Research: Intelligent Dependency Updates for `microsoft/physical-ai-toolchain`

<!-- markdownlint-disable-file -->

## Current Repo State (Verified)

The repo's `.github/dependabot.yml` (359 lines, `.github/dependabot.yml:1-359`) tracks **20 separate update blocks** across 7 ecosystems: npm (root `/`, `/data-management/viewer/frontend`, `/docs/docusaurus`), uv/Python (7 directories), terraform (4 directories), github-actions, docker (3 dirs), gomod (1 dir). All are `schedule: weekly, day: monday`. Groups are already configured for most blocks but with a critical gap: **most groups use `patterns: ["*"]` with no `update-types` differentiation**, so major version bumps land in the same grouped PR as patches. Only the `dataviewer-frontend-patch-minor` group at `.github/dependabot.yml:280-291` correctly uses `update-types: [minor, patch]`. The four terraform blocks have **no groups at all** (`.github/dependabot.yml:173-221`).

The AI reviewer is `aw-dependabot-pr-review.lock.yml` — a `gh-aw`-compiled agentic workflow triggered **only on explicit `/aw-dependabot-review` comment** (`.github/workflows/aw-dependabot-pr-review.lock.yml:77`), not automatically on every PR open. PR CI (`pr-validation.yml`) uses path-based filtering (`.github/workflows/pr-validation.yml:22-61`) — so expensive pytest/Go/Terraform jobs are skipped when their paths aren't touched. A `uv-lock-consistency.yml` workflow exists and can run in `changed-files-only: true` mode.

---

## 1. Native Dependabot Grouping — Full Capability

**Source:** [GitHub Docs — Optimizing PR creation for version updates](https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/optimizing-pr-creation-version-updates) · [Dependabot options reference — `groups`](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)

### The `groups:` key — complete parameter set

| Parameter | Purpose |
|---|---|
| `IDENTIFIER` | Branch name and PR title slug (letters, pipes, underscores, hyphens) |
| `applies-to` | `version-updates` (default) or `security-updates` — cannot mix |
| `dependency-type` | `development` or `production` (supported: bundler, composer, npm, pip, uv, maven, mix) |
| `patterns` | Wildcard name matches to include |
| `exclude-patterns` | Wildcard name matches to exclude from group (takes precedence) |
| `update-types` | `minor`, `patch`, `major` — unmatched semver levels get individual PRs |
| `group-by` | `dependency-name` — cross-directory grouping (same ecosystem only, version updates only) |

**Key insight verified:** Any dependency NOT matching a group rule falls back to an individual PR. So the pattern `update-types: [minor, patch]` in a group leaves all majors as individual PRs — which is exactly the desired behavior.

**The `cooldown` key** (new capability, verified in reference docs):

```yaml
cooldown:
  semver-major-days: 30   # Hold major updates for 30 days
  semver-minor-days: 7    # Hold minor updates 7 days
  semver-patch-days: 0    # Patches immediate
```

`cooldown` applies to **version updates only** — security updates are always immediate. Supported by `uv` (confirmed in the cooldown support table). The `include`/`exclude` lists (max 150 each) allow selective application. This is a significant new tool.

### Concrete improved `dependabot.yml` snippet

Addressing this repo's specific gaps — splitting patch/minor from major for all current wildcard groups:

```yaml
version: 2
updates:
  # Root npm — split low-risk from majors
  - package-ecosystem: npm
    directory: /
    schedule: { interval: weekly, day: monday }
    groups:
      root-npm-patch-minor:
        applies-to: version-updates
        patterns: ["*"]
        update-types: [minor, patch]
        dependency-type: development
      # majors fall through as individual PRs
    open-pull-requests-limit: 3
    labels: [dependencies, npm]
    commit-message: { prefix: chore, include: scope }

  # uv Python (root workspace) — split low-risk from majors, delay majors
  - package-ecosystem: uv
    directory: /
    schedule: { interval: weekly, day: monday }
    cooldown:
      semver-major-days: 30  # Majors wait 30 days for ecosystem stability
      semver-minor-days: 7
    groups:
      python-patch-minor:
        applies-to: version-updates
        patterns: ["*"]
        update-types: [minor, patch]
      # majors fall through individually, but cooldown delays them 30 days
    open-pull-requests-limit: 5
    labels: [dependencies, python]
    commit-message: { prefix: chore, include: scope }

  # Terraform (currently has NO groups) — add batching
  - package-ecosystem: terraform
    directory: /infrastructure/terraform
    schedule: { interval: weekly, day: monday }
    groups:
      terraform-providers-patch-minor:
        applies-to: version-updates
        patterns: ["*"]
        update-types: [minor, patch]
    open-pull-requests-limit: 3
    labels: [dependencies, terraform]
    commit-message: { prefix: chore, include: scope }

  # github-actions — digest bumps + patch/minor together, majors separate
  - package-ecosystem: github-actions
    directory: /
    schedule: { interval: weekly, day: monday }
    groups:
      github-actions-patch-minor:
        applies-to: version-updates
        patterns: ["*"]
        exclude-patterns: ["github/gh-aw-actions/*"]
        update-types: [minor, patch]
    ignore:
      - dependency-name: "github/gh-aw-actions/*"
    labels: [dependencies, github-actions]
    commit-message: { prefix: chore, include: scope }
```

**Cross-directory grouping** (same ecosystem only): The 7 uv workspace directories could potentially use `directories:` + `group-by: dependency-name` — but only if they are under a single update block (same ecosystem, version updates only). The limitation is that all directories must use the same ecosystem. This would merge e.g. all `torch` updates across `/training/rl`, `/evaluation`, `/evaluation/sil/docker` into one PR per package.

### `open-pull-requests-limit`

Already set in this repo. The default is 5. When the limit is reached, Dependabot pauses creating new PRs until existing ones are closed. Reducing the limit on low-value groups forces batching.

---

## 2. What Native Grouping Does NOT Solve

Native Dependabot grouping, even with `cooldown` and `update-types` splitting, leaves these gaps:

| Gap | Why Native Grouping Falls Short |
|---|---|
| **Cross-ecosystem grouping** | Dependabot `groups:` is per `package-ecosystem` block. Cannot bundle npm + Python + terraform CI-tooling patches into one PR. Each ecosystem's group creates its own PR. |
| **Risk classification beyond SemVer** | SemVer level (patch/minor/major) is a proxy for risk, not reality. A `torch` major from 2.x→3.x is higher risk than a `cspell` major. Native grouping can't read changelogs or vulnerability databases. |
| **Deciding which majors to hold indefinitely** | The `ignore` key handles this (repo already uses it for `torch`, `marshmallow`, `numpy`, `packaging`, `av`). But new "hold-this-forever" decisions require config edits. No signal-based classification. |
| **Security severity weighting** | Dependabot security updates are binary (vulnerable/not-vulnerable). No native CVSS-based routing: CVSS 9+ should page an oncall, CVSS 4 can auto-merge. |
| **Auto-approve / auto-merge low-risk PRs** | Native Dependabot cannot merge its own PRs. An Actions workflow is required. |
| **Lockfile-scope impact detection** | A single Python dependency bump can cause a cascade of transitive updates in `uv.lock`. Dependabot cannot signal "this changes 47 packages in the lock" vs "this changes 1". An agent could diff the lockfile. |
| **AI reviewer routing** | The existing `aw-dependabot-pr-review` agent is comment-triggered. No automated signal to decide "this PR warrants AI review" vs "auto-approve". |

---

## 3. Renovate Comparison

**Sources:** [Renovate Automerge docs](https://docs.renovatebot.com/key-concepts/automerge/) · [Renovate Configuration Options](https://docs.renovatebot.com/configuration-options/) · [Renovate Dependency Dashboard](https://docs.renovatebot.com/key-concepts/dashboard/) · [Renovate GitHub platform](https://docs.renovatebot.com/modules/platform/github/)

### Renovate's grouping model

Renovate uses `packageRules` (ordered, merged) with `groupName` to combine PRs:

```json
{
  "packageRules": [
    {
      "description": "Automerge all patch + minor dev deps after CI",
      "matchUpdateTypes": ["minor", "patch"],
      "matchDepTypes": ["devDependencies"],
      "automerge": true,
      "groupName": "dev-patch-minor"
    },
    {
      "description": "Hold major updates for dashboard approval",
      "matchUpdateTypes": ["major"],
      "dependencyDashboardApproval": true
    },
    {
      "description": "Batch Python non-major updates",
      "matchManagers": ["uv"],
      "matchUpdateTypes": ["minor", "patch"],
      "groupName": "python-non-major",
      "minimumReleaseAge": "7 days"
    }
  ],
  "dependencyDashboard": true
}
```

**Key Renovate capabilities native Dependabot lacks:**

| Feature | Renovate | Dependabot |
|---|---|---|
| `automerge: true` per rule | ✅ Built-in, waits for CI green | ❌ Requires separate Actions workflow |
| Cross-ecosystem grouping | ✅ `groupName` across all managers | ❌ Per-ecosystem only |
| `minimumReleaseAge` (stability days) | ✅ e.g. `"7 days"` before PR raised | ✅ Equivalent `cooldown` key (new) |
| `dependencyDashboard` | ✅ Single GitHub issue, approve/defer | ❌ No equivalent |
| `dependencyDashboardApproval` | ✅ Major updates wait for human click | ❌ Manual `ignore` rules only |
| Platform automerge (merge queue) | ✅ `platformAutomerge: true` | ❌ Needs Actions |
| `matchManagers` cross-manager rules | ✅ Apply to all Python managers | ❌ Not applicable |

### Should this repo migrate to Renovate?

**Arguments FOR:**
- Renovate solves cross-ecosystem grouping (1 PR for npm+Python dev tools update)
- Built-in automerge removes the need for a custom Actions workflow
- `dependencyDashboard` gives a single overview issue instead of 20+ PRs
- `minimumReleaseAge` is equivalent to Dependabot's new `cooldown` but more mature
- The `config:recommended` preset + `packageRules` replaces all 20 dependabot.yml blocks

**Arguments AGAINST:**
- **Migration cost is HIGH**: All 20 ecosystem blocks need Renovate equivalents, the `gh-aw-actions` exclusion logic needs porting, `ignore` rules for `torch/marshmallow/numpy/packaging/av` need porting
- **`uv.lock` handling**: The repo has custom `uv lock --check` CI gates and a uv.lock regeneration step in `main.yml`. Renovate supports `uv` but the exact interaction with workspace layouts and multi-directory pyproject.toml needs testing
- **Microsoft org policy**: The `aw-dependabot-pr-review.lock.yml` workflow is compiled by `gh-aw` tooling tied to GitHub's internal toolchain. Whether that toolchain works with Renovate PRs is unknown
- **Security updates**: Dependabot security updates come from the GitHub Advisory Database and are deeply integrated with the GitHub Security tab. Renovate uses `osvVulnerabilityAlerts` + OSV, not GHSA — the behavior differs
- **No zero-code path**: Renovate requires new config file + GitHub App installation or self-hosting; Dependabot is already running

**Verdict**: Renovate would be **lower-effort long-term** but **higher-effort to migrate**. For this repo, Phase 0+1 (Dependabot grouping + Actions auto-merge) is lower risk. Renovate makes sense only if Phase 2 custom agent proves too complex to maintain.

---

## 4. Agent-Based Triage/Batching Design

**Sources:** [GitHub Docs — Automating Dependabot with GitHub Actions](https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/automate-dependabot-with-actions) · [github/combine-prs README](https://github.com/github/combine-prs) · [mAAdhaTTah/combine-dependabot-prs README](https://github.com/mAAdhaTTah/combine-dependabot-prs)

### (a) Reading open Dependabot PRs via GitHub API

The `dependabot/fetch-metadata` action (currently used in `dependabot-security-prefix.yml` at `.github/workflows/dependabot-security-prefix.yml:24`) exposes:
- `steps.metadata.outputs.dependency-names` — list of updated packages
- `steps.metadata.outputs.dependency-type` — `direct:production` or `direct:development`
- `steps.metadata.outputs.update-type` — `version-update:semver-patch/minor/major`
- `steps.metadata.outputs.ghsa-id` — non-empty if security advisory
- `steps.metadata.outputs.cvss` — CVSS score string

### (b) Impact Classification

**High-impact criteria (require human or AI review):**
- `update-type == version-update:semver-major`
- `dependency-type == direct:production` AND `update-type == version-update:semver-minor` (conservative)
- `ghsa-id != ''` AND CVSS ≥ 7.0 (critical/high security)
- Changed `uv.lock` diff has > N packages affected (detect via `git diff --stat HEAD~1 '*uv.lock' | awk '{print $1}'`)
- Terraform provider major bumps (potential API breaking changes)

**Low-impact criteria (auto-approvable):**
- `update-type == version-update:semver-patch`
- `dependency-type == direct:development` with any non-major update
- GitHub Actions digest/patch bumps
- Docker base image patch bumps
- `ghsa-id != ''` AND CVSS < 7.0 (low/moderate security — still merge fast but no AI needed)

### (c) Auto-approve / auto-merge pattern (GitHub Actions)

```yaml
name: Dependabot Auto-Merge
on: pull_request

permissions:
  contents: write
  pull-requests: write

jobs:
  dependabot-triage:
    runs-on: ubuntu-latest
    if: github.actor == 'dependabot[bot]'
    steps:
      - uses: dependabot/fetch-metadata@v3
        id: meta
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Auto-approve low-risk PR
        if: |
          steps.meta.outputs.update-type == 'version-update:semver-patch' ||
          (steps.meta.outputs.dependency-type == 'direct:development' &&
           steps.meta.outputs.update-type != 'version-update:semver-major') &&
          steps.meta.outputs.ghsa-id == ''
        run: gh pr review --approve "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Enable auto-merge for low-risk PR
        if: |
          steps.meta.outputs.update-type == 'version-update:semver-patch' ||
          (steps.meta.outputs.dependency-type == 'direct:development' &&
           steps.meta.outputs.update-type != 'version-update:semver-major') &&
          steps.meta.outputs.ghsa-id == ''
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Label high-impact PR for AI review
        if: |
          steps.meta.outputs.update-type == 'version-update:semver-major' ||
          (steps.meta.outputs.ghsa-id != '' && steps.meta.outputs.cvss >= '7.0')
        run: |
          gh pr edit "$PR_URL" --add-label "ai-review-needed"
          gh pr comment "$PR_URL" --body "/aw-dependabot-review"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Note: `gh pr merge --auto` requires "Allow auto-merge" to be enabled in repo settings AND branch protection "Require status checks to pass" to be set.

### (d) Combine PRs for low-impact batching

The `github/combine-prs` action ([github/combine-prs README](https://github.com/github/combine-prs)) supports:
- `ci_required: "true"` — only combines PRs where CI has passed
- `select_label` — only combine PRs with a specific label (e.g. `auto-combine`)
- `ignore_label: "nocombine"` — skip security PRs labeled `nocombine`
- `branch_prefix: "dependabot"` — targets all dependabot branches

**Architecture for this repo:**

```yaml
# .github/workflows/combine-dependabot-prs.yml
name: Combine Dependabot PRs
on:
  schedule:
    - cron: '0 8 * * 2'  # Tuesday 08:00 (day after Monday Dependabot run)
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write
  checks: read

jobs:
  combine:
    runs-on: ubuntu-latest
    steps:
      - uses: github/combine-prs@v5
        with:
          select_label: auto-combine     # Only PRs labeled by triage workflow
          ci_required: "true"            # Only green PRs
          ignore_label: "security"       # Never combine security PRs
          pr_title: "chore(deps): combined low-risk dependency updates"
          labels: "dependencies,combined-pr"
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

The triage workflow (triggered on `pull_request: opened`) labels low-impact PRs `auto-combine`. The combine workflow runs Tuesday morning after Dependabot fires Monday night, collects all green + `auto-combine` labeled PRs, cherry-picks their commits into a single branch, and opens one combined PR. One CI run instead of N.

**`mAAdhaTTah/combine-dependabot-prs`** ([README](https://github.com/mAAdhaTTah/combine-dependabot-prs)) is an alternative CLI + Action with `mustBeGreen: true`, `includeLabel`, and `ignoreLabel` parameters — simpler but less actively maintained.

### Recommended architecture for this repo

```
Monday (Dependabot fires) →
  Each PR triggers pr-validation.yml (path-filtered CI) →
  AND triggers dependabot-triage.yml:
    Low-risk (patch / dev non-major / no GHSA) → approve + label "auto-combine"
    Security (any GHSA) → label "security" + fast-track
    Major production → label "ai-review-needed" + post /aw-dependabot-review comment

Tuesday 08:00 (scheduled) →
  combine-prs workflow → cherry-pick all "auto-combine" + CI-green PRs →
  One combined PR → one more CI run → human merge
```

**Impact on AI tokens:** Only PRs labeled `ai-review-needed` get `/aw-dependabot-review` posted. With ~20 Dependabot PRs/week, perhaps 3-5 are major/security → 3-5 AI reviews per week instead of 20. Token burn reduced ~75%.

**Impact on CI runs:** Combined PRs reduce from N individual CI runs + 1 combined to N individual (already path-filtered) + 1 combined. Since the path-filtered CI mostly skips expensive jobs for dep-only changes, the marginal cost per individual Dependabot PR is LOW already. The real win is human attention and PR queue size.

---

## 5. Security Updates — Fast-Track, Never Batch

**Source:** [GitHub Docs — About Dependabot security updates](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-security-updates)

**Key facts verified:**
1. Dependabot security updates are **separate from version updates** — they fire immediately on new GHSA advisories, not on the weekly schedule
2. `cooldown` does NOT apply to security updates (confirmed: "cooldown applies to version updates only")
3. `applies-to: security-updates` in `groups` can group security updates, but NOT with version updates
4. The `open-pull-requests-limit` for security updates defaults to 10 (separate from version updates limit)
5. The existing `dependabot-security-prefix.yml` already re-titles security PRs from `chore(deps)` to `security(deps)` by detecting `ghsa-id != '' || cvss != ''`

**Recommended security update handling:**

- **DO NOT** add `applies-to: security-updates` groups that would combine multiple security fixes — each GHSA should remain isolated for auditability
- **DO** use the existing security prefix workflow as a fast-track signal
- **DO** add auto-approve for CVSS < 7.0 security patches (low/moderate severity) where CI is green
- **DO NOT** delay, combine, or use `nocombine` label on any security PR
- **DO** trigger AI review (`/aw-dependabot-review`) for CVSS ≥ 7.0 critical/high security updates
- The `dependency-review.yml` workflow already gates PRs against known vulnerabilities via `actions/dependency-review-action`

For grouped security updates at scale (optional): Enable "grouped security updates" at the repo/org settings level — this lets Dependabot group all available security patches per ecosystem into one PR automatically. The `dependabot.yml` `groups` key with `applies-to: security-updates` provides more granular control.

---

## 6. Recommended Phased Plan

### Phase 0: Pure `dependabot.yml` grouping — zero code, immediate wins

**Changes to `.github/dependabot.yml`:**

1. **All Python (uv) groups**: Add `update-types: [minor, patch]` to existing group definitions → majors become individual PRs
2. **All npm groups (root, docusaurus)**: Same — add `update-types: [minor, patch]`
3. **All terraform blocks**: Add `groups` entries (currently none) with `update-types: [minor, patch]`
4. **GitHub Actions group**: Add `update-types: [minor, patch]` to existing group (digest bumps are `patch`)
5. **Add `cooldown`** to uv and npm blocks: `semver-major-days: 30, semver-minor-days: 7` — delays non-security version bumps, reducing churn
6. **Reduce `open-pull-requests-limit`** where groups are now batching: e.g. 3 instead of 5 for python/npm groups

**Expected PR reduction:** Currently ~20 ecosystem blocks × (N deps per block) = potentially 20+ PRs/week. With `update-types` grouping, each block produces AT MOST 2 PRs (one batch for patch/minor + individual ones for major). With `cooldown: semver-major-days: 30`, major PRs only appear once per 30 days. **Estimated: 70-80% reduction in PR volume.**

Note on uv.lock: The repo's `uv-lock-consistency.yml` workflow runs `uv lock --check` in CI. Dependabot regenerates `uv.lock` natively when updating uv dependencies (confirmed by the `uv` ecosystem support for both `cooldown` and `groups`). The `changed-files-only: true` mode means the check only runs when uv manifests or locks are touched — so Python dep PRs automatically heal their own locks.

### Phase 1: Auto-merge low-risk on green CI

**New file: `.github/workflows/dependabot-auto-merge.yml`**

- Trigger: `pull_request: [opened, synchronize]` from `dependabot[bot]`
- Uses `dependabot/fetch-metadata@v3` to extract `update-type`, `dependency-type`, `ghsa-id`
- Low-risk criteria: `update-type == semver-patch` OR (`dependency-type == direct:development` AND `update-type != semver-major`) AND `ghsa-id == ''`
- Actions: `gh pr review --approve` + `gh pr merge --auto --squash`
- High-risk criteria: `update-type == semver-major` OR `ghsa-id != ''`
- Actions for high-risk: add label `ai-review-needed`, post `/aw-dependabot-review` comment

**Prereqs:**
- Enable "Allow auto-merge" in repo Settings → General
- Ensure branch protection "Require status checks: pr-validation-summary" is set (already the case based on the `pr-validation-summary` aggregator job)
- Use `GITHUB_TOKEN` — sufficient for auto-merge, but if branch protection requires a non-bot approval, a PAT or GitHub App token may be needed

**Expected impact:** ~80% of Dependabot PRs auto-merge within hours of CI green, with zero human attention. AI reviews only triggered for high-impact PRs.

### Phase 2: Agentic triage/combine + escalation

**New file: `.github/workflows/combine-dependabot-prs.yml`**

- Schedule: Tuesday 08:00 (after Monday Dependabot run)
- Uses `github/combine-prs@v5` with `select_label: auto-combine` + `ci_required: true`
- Phase 1 triage workflow labels low-risk PRs `auto-combine`
- Combines all green + labeled PRs into ONE combined PR, triggering ONE CI run
- Remaining individual PRs (major / security / failed CI) stay separate for human review

**Escalation flow:**
1. `ai-review-needed` label → `/aw-dependabot-review` comment triggers existing `aw-dependabot-pr-review` workflow
2. The compiled agentic workflow already has the `dependabot/fetch-metadata` output and can make an informed review
3. AI reviewer can post a structured comment: "SAFE: patch to production dep, auto-merge" or "NEEDS REVIEW: major version, breaking changes detected in CHANGELOG"

**Expected impact:** At ~20 Dependabot PRs/week, Phase 2 reduces to:
- 3-5 individual security PRs (fast-tracked, some auto-merged if low CVSS)
- 2-4 major version PRs (AI reviewed)
- 1-2 combined PRs (all low-risk batched, 1 CI run each)
- Total human review: ~5-6 PRs/week vs current 20+
- AI token usage: ~4 reviews/week vs potential 20 reviews/week

---

## Sources Summary

| Source | URL | Key Content |
|---|---|---|
| GitHub Docs: Optimizing PR creation | https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/optimizing-pr-creation-version-updates | `groups`, `cooldown`, scheduling, examples with `update-types` |
| GitHub Docs: Dependabot options reference | https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference | Full `groups` params, `cooldown` params, `dependency-type` support table |
| GitHub Docs: Security updates | https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-security-updates | Security vs version update distinction, grouped security updates |
| GitHub Docs: Automating with Actions | https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/automate-dependabot-with-actions | `fetch-metadata` action, auto-approve, auto-merge patterns |
| Renovate: Automerge | https://docs.renovatebot.com/key-concepts/automerge/ | `automerge`, `automergeType`, scheduling, merge queue |
| Renovate: Config options | https://docs.renovatebot.com/configuration-options/ | `packageRules`, `groupName`, `minimumReleaseAge`, `dependencyDashboard` |
| Renovate: Dashboard | https://docs.renovatebot.com/key-concepts/dashboard/ | `dependencyDashboard`, approval workflow, major gating |
| github/combine-prs | https://github.com/github/combine-prs | `select_label`, `ci_required`, `ignore_label`, usage pattern |
| mAAdhaTTah/combine-dependabot-prs | https://github.com/mAAdhaTTah/combine-dependabot-prs | CLI + Actions alternative |
| Repo: dependabot.yml | .github/dependabot.yml:1-359 | 20 blocks, existing groups (all use `"*"` no `update-types`), 4 terraform blocks with no groups |
| Repo: pr-validation.yml | .github/workflows/pr-validation.yml:22-61 | Path-filtered CI, 30+ jobs, `changes` detector |
| Repo: dependabot-security-prefix.yml | .github/workflows/dependabot-security-prefix.yml:24 | `fetch-metadata@v3` usage, GHSA/CVSS detection |
| Repo: aw-dependabot-pr-review.lock.yml | .github/workflows/aw-dependabot-pr-review.lock.yml:77 | AI reviewer is comment-triggered, NOT auto-fired |
| Repo: uv-lock-consistency.yml | .github/workflows/uv-lock-consistency.yml | `changed-files-only` mode, `uv lock --check` gate |

---

# Researcher Subagent Executive Summary

**Subagent file path:** `.copilot-tracking/research/subagents/2026-06-19/dependency-update-intelligence.md` (NOTE: per system constraints, findings are returned in this response text rather than written to disk)

**Status:** Research complete — all 6 areas fully investigated with live doc fetches and repo file reads.

## ≤7 Key Finding Bullets

1. **Phase 0 is almost free**: The repo's existing `dependabot.yml` already has `groups:` on most blocks but critically lacks `update-types: [minor, patch]` — adding it to the 19 remaining groups and 4 terraform blocks (which have zero groups today) would collapse ~20+ PRs/week into ≤2 per ecosystem.

2. **`cooldown` is a new native lever**: Dependabot now supports `semver-major-days: 30` / `semver-minor-days: 7` for version updates (not security), allowing major Python/npm bumps to sit 30 days before a PR is even opened — exactly what the "hold AI-heavy torch upgrades" use case needs.

3. **Security PRs are already isolated architecturally**: Dependabot security updates fire immediately (bypass `schedule`), cannot use `cooldown`, and the existing `dependabot-security-prefix.yml` already detects GHSA/CVSS. Security PRs should NEVER be batched — add `ignore_label: "security"` to any combine workflow.

4. **The AI reviewer is NOT auto-firing today**: `aw-dependabot-pr-review.lock.yml` triggers on `/aw-dependabot-review` comment only — token waste comes from humans or automation posting that comment on every PR, not from the workflow itself triggering on all PRs. Phase 1's triage workflow should be the gatekeeper for when to post that comment.

5. **`github/combine-prs` is the right prior art**: GitHub uses it internally, supports `select_label` + `ci_required: true` + `ignore_label`, and is maintained. Running it Tuesday after Monday's Dependabot batch reduces N individual "auto-combine"-labeled green PRs to 1 combined PR per week.

6. **Renovate solves cross-ecosystem grouping** (Dependabot can't) but migration cost is HIGH — 20 blocks, `gh-aw-actions` exclusion logic, uv workspace handling, and unknown compatibility with the `gh-aw` compiler toolchain make it Phase 3+ at earliest.

7. **PR CI is already path-filtered**: The `pr-validation.yml` `changes` detector skips pytest/Terraform/Go jobs unless their paths change — so each individual Dependabot PR already runs a lightweight CI set. The remaining CI cost is from always-run jobs (spell-check, markdown-lint, dependency-pinning, CodeQL, etc. — ~15 jobs). Batching reduces the number of times those run.

## ≤5 Next Research Items

1. **Count actual weekly PR volume**: Query the GitHub API for open Dependabot PRs over the last 4 weeks to quantify the real "hell" — how many PRs/week, which ecosystems, which semver level — to prioritize which Phase 0 changes give the most reduction.

2. **Test `cooldown` on uv**: The `uv` manager is listed as supporting `semver-*-days` cooldown in the reference table — verify this works with the multi-directory workspace layout (root `uv.lock` + 7 sub-directory `pyproject.toml` files).

3. **GitHub App token requirement for auto-merge**: Check if the repo's branch protection "Require a pull request before merging" with required reviewers would block `GITHUB_TOKEN`-based auto-merge — if so, a GitHub App token is required and the existing `RELEASE_APP_ID` + `RELEASE_APP_PRIVATE_KEY` pattern could be reused.

4. **Map the `always-run` CI jobs**: Identify which of the ~15 always-run jobs in `pr-validation.yml` can be made `changed-files-only`, as this is orthogonal to batching but reduces per-PR cost regardless of grouping strategy.

5. **Evaluate `group-by: dependency-name` across uv dirs**: Whether collapsing the 7 uv workspace directories into one update block with `directories:` + `group-by: dependency-name` is feasible — this would generate per-package PRs across all Python workspaces instead of per-workspace PRs.

## ≤3 Blocking Clarifying Questions

1. **Is auto-merge gated by required human reviewers?** If branch protection requires N human approvals before merge, `gh pr merge --auto` will queue but not merge until a human approves — meaning Phase 1 auto-merge only works if the bot's own approval satisfies the branch protection rule (requires "Allow specified actors to bypass required pull requests" or 0 required human reviewers for bot PRs).

2. **Who/what is currently triggering `/aw-dependabot-review` on Dependabot PRs?** If humans are posting this manually for every PR, Phase 1 (the triage workflow gating the comment to high-risk PRs only) gives immediate token savings. If it's automated by another workflow, that workflow needs to be modified.

3. **Are there licensing or policy constraints on using `github/combine-prs` in this Microsoft org repo?** The action is MIT-licensed and used by GitHub internally, but some org policies restrict third-party Actions to approved lists. If `github/combine-prs` isn't on the approved list, a custom combine script using `gh` CLI would be needed instead.

## Full Detail pointer

All detailed findings, concrete `dependabot.yml` snippets, workflow YAML patterns, comparison tables, and cited source URLs are included verbatim in this response text above (beginning at "# Full Research: Intelligent Dependency Updates").