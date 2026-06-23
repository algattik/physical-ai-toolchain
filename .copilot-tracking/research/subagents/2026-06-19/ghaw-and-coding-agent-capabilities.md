<!-- markdownlint-disable-file -->
# Subagent C raw capture: gh-aw + Copilot Coding Agent capabilities
(Captured by parent: research agent is read-only; agent chat output verbatim.)


I have all findings. Per my operating constraints, I cannot write to files — all findings are returned directly in this response.

---

## Researcher Subagent Report

**Subagent file path:** `.copilot-tracking/research/subagents/2026-06-19/ghaw-and-coding-agent-capabilities.md` *(file write blocked by operating constraints; full content follows inline)*

**Status:** Complete — all six research questions answered with primary-source citations.

---

## Full Detail

Below is the complete research document content (would be the file if writing were permitted):

---

<!-- markdownlint-disable-file -->

# gh-aw + GitHub Copilot Coding Agent Capabilities Research

**Date:** 2026-06-19  
**Researcher:** Subagent  
**Scope:** `microsoft/physical-ai-toolchain` — gated on-PR automation via gh-aw and Copilot Coding Agent

---

## 1. gh-aw Triggers

### Supported `on:` Triggers

Source: `github/gh-aw:.github/aw/triggers.md` (SHA `1452121194a8a8c816f60a7819987fbc1b7175de`), `github/gh-aw:.github/aw/syntax-core.md` (SHA `9e3c8919aec49eb77785a3ceaadb0b7a716d754a`)

**Standard GitHub events (pass-through):**

```yaml
on:
  issues:
    types: [opened, edited, closed]
  pull_request:
    types: [opened, edited, closed]
    paths: ["**/uv.lock"]            # ← path filter supported
  push:
    branches: [main]
  schedule:
    - cron: "0 9 * * 1"
  workflow_dispatch:
  workflow_run:
    workflows: ["PR Validation"]
    types: [completed]
  deployment_status:
```

**Fuzzy scheduling** (`daily on weekdays`, `weekly`, `hourly`, `every 2 hours`) is compiled to deterministic cron; `workflow_dispatch` is automatically added.

**Slash command trigger (the key on-demand gate):**

```yaml
on:
  slash_command:
    name: aw-dependabot-review   # → responds to /aw-dependabot-review
    events: [pull_request_comment]
```

Supported `events:` identifiers:
| Value | Fires on |
|---|---|
| `issues` | Issue bodies (opened, edited, reopened) |
| `issue_comment` | Comments on issues only |
| `pull_request_comment` | Comments on PRs only |
| `pull_request` | PR bodies |
| `pull_request_review_comment` | PR review inline comments |
| `*` | All comment-related events (default) |

**Label command trigger:**

```yaml
on:
  label_command:
    name: uv-lock-review
    events: [pull_request]
    remove_label: true   # removes label after activation (default)
```

### Path Filtering

`paths:` and `paths-ignore:` are fully supported on `pull_request`, `push`, and other triggers (pass-through to GitHub Actions). Example:

```yaml
on:
  pull_request:
    paths: ["**/uv.lock", "**/pyproject.toml"]
```

**Critical caveat on path filtering + required checks:** A `pull_request` workflow that is *skipped* due to `paths:` leaves any required check in "Pending" state, which **blocks merge**. See §6 for the workaround pattern.

### Can a workflow fire ONLY on slash command (not on every push/rebase)?

**Yes.** `slash_command:` is the only trigger, so the workflow runs exactly when `/command-name` is posted. No other event fires it. This is exactly what the existing `aw-dependabot-pr-review.md` workflow does:

```yaml
on:
  slash_command:
    name: aw-dependabot-review
    events: [pull_request_comment]
```
— `algattik/physical-ai-toolchain:.github/workflows/aw-dependabot-pr-review.md:7-9`

The compiled lock file confirms this becomes a standard `issue_comment` trigger with an `if:` guard that checks `startsWith(github.event.comment.body, '/aw-dependabot-review')`:
— `algattik/physical-ai-toolchain:.github/workflows/aw-dependabot-pr-review.lock.yml:77`

### Additional `on:` Guards

From `github/gh-aw:.github/aw/syntax-core.md`:

| Field | Purpose |
|---|---|
| `skip-roles:` | Skip for users with roles in list (`read`, `write`, `maintainer`, `admin`) |
| `skip-bots:` | Skip for specific bots (`dependabot`, `renovate`) |
| `labels:` | Only fire when triggering label matches |
| `skip-if-match:` | Skip when GH search query returns results (dedup guard) |
| `skip-if-no-match:` | Skip when GH search query returns nothing (precondition gate) |
| `skip-if-check-failing:` | Skip when CI checks are failing on triggering ref |
| `reaction:` | Add emoji to triggering item on activation |
| `status-comment:` | Post status comment when workflow starts/completes |
| `manual-approval:` | Require environment protection approval |
| `stop-after:` | Deadline for workflow execution (`+25h`, `+3d`, or absolute timestamp) |

---

## 2. Safe Outputs: What gh-aw Workflows Can DO

Source: `github/gh-aw:.github/aw/safe-outputs-content.md` (SHA `750876edc5be5a23d9e335fe0b2da9d9fc8fab23`), `github/gh-aw:.github/aw/safe-outputs-management.md` (SHA `73ecbf006e17d88c9f8b6c1d840698ea554f029f`), `github/gh-aw:.github/aw/safe-outputs-automation.md` (SHA `0b1b9a9e6c7f13da1601164b04d3520f8fffa189`), `github/gh-aw:.github/aw/safe-outputs-runtime.md` (SHA `731d87025942505573803e2923f1de94a5d82448`)

### Content Operations (`safe-outputs-content.md`)

| Safe Output | Description |
|---|---|
| `create-issue:` | Create GitHub issues with labels, assignees, dedup, sub-issues, auto-close |
| `close-issue:` | Close issues with filtering (required-labels, prefix) |
| `create-discussion:` | Create discussions in a category |
| `add-comment:` | Post comments on issues/PRs/discussions; `hide-older-comments: true` minimizes prior comments (single-comment update pattern) |
| `comment-memory:` | Persistent managed comment (configured under `tools:`, not `safe-outputs:`) |
| **`create-pull-request:`** | **Create PRs with git patches — SEE DETAIL BELOW** |
| `create-pull-request-review-comment:` | Inline PR review comment (used in existing workflow) |
| `submit-pull-request-review:` | Submit a PR review (APPROVE/COMMENT/REQUEST_CHANGES) |

### `create-pull-request` — Full Detail (ANSWERS THE PR QUESTION)

**gh-aw CAN create pull requests directly with code changes.** The `create-pull-request:` safe-output takes a git patch from the agent and pushes it to a new branch, then opens a PR.

```yaml
safe-outputs:
  create-pull-request:
    title-prefix: "[ai] "           # PR title prefix
    branch-prefix: "ghaw/"          # branch name prefix
    labels: [automation, ai-agent]  # labels on PR
    draft: true                     # default: true (creates draft PR)
    if-no-changes: "warn"           # warn/error/ignore when no changes
    base-branch: "main"             # static base branch
    allowed-base-branches:          # dynamic base branch overrides
      - "release/*"
      - "main"
    allowed-files:                  # ALWAYS RESTRICT THIS - limits agent scope
      - "uv.lock"
      - "pyproject.toml"
      - "training/rl/uv.lock"
    excluded-files:
      - "**/*.generated"
    protected-files: request_review  # request_review/blocked/fallback-to-issue/allowed
    signed-commits: true            # default true, GitHub-signed via GraphQL
    patch-format: "bundle"          # bundle (default) or am
    github-token-for-extra-empty-commit: ${{ secrets.MY_CI_PAT }}  # trigger CI
    auto-close-issue: true          # add "Fixes #N" when triggered from issue
    max-patch-size: 2048            # KB cap (default 4096)
    max-patch-files: 50             # file count cap (default 100)
    allowed-branches:               # source branch glob filter
      - "ghaw/*"
    fallback-as-issue: true         # create issue if PR creation fails
```

**Key constraints:**
- Requires `contents: write` permission (via safe-outputs job, not agent job)
- Agent job remains read-only; safe-outputs job handles the write
- `allowed-files` should always be set (restricts which files agent can touch)
- `draft: true` is the default (maintainer review required before merge)
- PRs do NOT trigger CI by default — use `github-token-for-extra-empty-commit` or `GH_AW_CI_TRIGGER_TOKEN` secret to push an extra empty commit that triggers CI
- Output variables: `created_pr_number`, `created_pr_url`
- `allow-workflows: false` by default — set `true` + `github-app:` to push to `.github/workflows/`
- `preserve-branch-name: true` skips random salt suffix on branch names

Sources:
- `github/gh-aw:.github/aw/safe-outputs-content.md` (web view content)
- `github/gh-aw:pkg/workflow/create_pull_request.go` (SHA `2dcd22d5fd2ec19d4a641a9636ce2ca36a90cf55`) — struct with `Draft`, `AllowedBranches`, `AllowedFiles`, `MaxPatchSize` etc.
- `github/gh-aw:docs/src/content/docs/reference/safe-outputs-pull-requests.md` — "PRs do not trigger CI by default"

### Management Operations (`safe-outputs-management.md`)

| Safe Output | Description |
|---|---|
| `update-issue:` | Update issue title/body/labels/assignees |
| `update-pull-request:` | Update PR title/body (replace/append/prepend) |
| `merge-pull-request:` | ⚠️ Experimental — merge with label gates |
| `close-pull-request:` | Close PRs with label/prefix filters |
| `mark-pull-request-as-ready-for-review:` | Undraft a PR |
| `add-labels:` | Add labels to issues/PRs |
| `remove-labels:` | Remove labels from issues/PRs |
| `add-reviewer:` | Add reviewers (including `copilot` for AI review) |
| `push-to-pull-request-branch:` | Push changes to existing PR branch |
| `assign-milestone:` | Assign milestone |
| `link-sub-issue:` | Create parent-child issue relationships |
| `create-project:` / `update-project:` | GitHub Projects v2 operations |

**`update-comment` question:** gh-aw does not have a dedicated `update-comment:` safe-output. The pattern for single-comment-per-run is `add-comment: { hide-older-comments: true }` which minimizes/hides previous comments from the same workflow before posting the new one. `comment-memory:` (under `tools:`) maintains a persistent managed comment that is updated in-place across runs.

### Automation Operations (`safe-outputs-automation.md`)

| Safe Output | Description |
|---|---|
| `dispatch-workflow:` | Trigger other AW workflows via `workflow_dispatch` |
| `call-workflow:` | Fan-out to reusable workflows at compile time |
| `create-code-scanning-alert:` | Generate SARIF findings |
| **`create-check-run:`** | **Create GitHub Check Runs in PR Checks UI** — key for required check pattern |
| **`create-agent-session:`** | **Create Copilot cloud agent sessions** (requires `COPILOT_GITHUB_TOKEN` PAT) |
| **`assign-to-agent:`** | **Assign Copilot coding agent to issues** — key for AW→issue→agent pattern |
| `assign-to-user:` | Assign users to issues/PRs |
| `upload-asset:` | Publish files to orphaned git branch (embeddable URLs) |
| `upload-artifact:` | Upload run-scoped GitHub Actions artifacts |

**`create-check-run:` detail:**

```yaml
safe-outputs:
  create-check-run:
    name: "uv-lock-review"    # name must match branch protection required check name
    max: 1
    output:
      title: "Pending analysis"
      summary: "Awaiting agent output"
```

Requires `checks: write` permission (auto-added). Agent calls with `conclusion: success/failure/neutral`, `title`, `summary`, optional `annotations`.

---

## 3. Human-in-the-Loop / Manual Gates

Source: `github/gh-aw:.github/aw/syntax-agentic.md` (SHA `3ba9e56f91cc698b6bb7f5b7306f00ee655594c9`), `github/gh-aw:.github/aw/syntax-core.md`, compiled lock file `algattik/physical-ai-toolchain:.github/workflows/aw-dependabot-pr-review.lock.yml:1621-1665`

### Role-Based Access Control (Verified in compiled output)

```yaml
on:
  slash_command:
    name: aw-uv-lock-review
    events: [pull_request_comment]
  roles: [admin, maintainer, write]   # default — only users with write+ can trigger
```

`on.roles:` *(in `syntax-agentic.md`):*
- **Default: `[admin, maintainer, write]`** — read-only users cannot trigger
- Available: `admin`, `maintainer`, `write`, `read`, `all`
- Compiled into `pre_activation` job with `GH_AW_REQUIRED_ROLES: "admin,maintainer,write"` and a `check_membership.cjs` step
- Also guarded by `author_association in ["OWNER","MEMBER","COLLABORATOR"]` in the `pre_activation.if:` expression

From the compiled lock file (line 1622, 1647):
```yaml
if: "...contains(fromJSON('[\"OWNER\",\"MEMBER\",\"COLLABORATOR\"]'), 
     github.event.comment.author_association)..."
# and:
GH_AW_REQUIRED_ROLES: "admin,maintainer,write"
```

### Skip Roles

```yaml
on:
  skip-roles: [read]   # skip for read-only users even if slash command matches
```

### Staged/Dry-Run Mode

```yaml
staged: true   # at workflow level — emits step summary instead of API calls
```

Or per safe-output:
```yaml
safe-outputs:
  create-pull-request:
    staged: true   # preview-only for this output
```

### Manual Approval via Environment

```yaml
environment: production   # triggers GitHub Environment protection rules
# OR:
on:
  manual-approval: true  # require environment approval before executing
```

### `if:` Guards

Standard `if:` expression on the workflow:
```yaml
if: ${{ github.event.issue.pull_request != null }}
```

### `skip-if-check-failing:` — Gate on CI

```yaml
on:
  pull_request:
  skip-if-check-failing:
    include:
      - "PR Validation"     # only run if this check is passing
    allow-pending: false    # pending = failing (default)
```

### Rate Limiting

```yaml
user-rate-limit:
  max-runs-per-window: 3
  window: 60          # minutes
  ignored-roles: [admin, maintain, write]
```

### Reaction-Based Integrity Promotion

```yaml
features:
  integrity-reactions: true   # 👍/❤️ to promote, 👎/😕 to demote content integrity
```

---

## 4. Cost Controls

Source: `github/gh-aw:.github/aw/syntax-agentic.md`, `github/gh-aw:.github/aw/syntax-core.md`, compiled lock file

### Timeout

```yaml
timeout-minutes: 15   # agent execution step timeout (default: 20 min)
                      # safe-outputs job default: 45 min
```

### Turn Cap

```yaml
max-turns: 30   # AWF turn cap (replaces deprecated max-runs)
```

### AI Credit Budget

```yaml
max-ai-credits: 5000    # per-run AIC budget (default: 1000)
                        # set negative to disable enforcement
max-daily-ai-credits: 20000   # per-user 24h guardrail
```

From the compiled lock file (line 85): `GH_AW_MAX_DAILY_AI_CREDITS: ${{ vars.GH_AW_DEFAULT_MAX_DAILY_AI_CREDITS || '5000' }}` — the existing workflow already uses this guardrail.

### Concurrency Cancellation

```yaml
concurrency:
  group: "gh-aw-${{ github.workflow }}-${{ github.event.pull_request.number }}"
  cancel-in-progress: true   # cancel superseded runs on new pushes
  queue: single               # keep only one pending (default)
```

Current repo uses: `"gh-aw-${{ github.workflow }}-${{ github.event.issue.number || github.event.pull_request.number || github.run_id }}"` (lock file line 70) — cancels concurrent runs for the same PR number.

### Model Selection

```yaml
engine: copilot
# model set via repository variable:
# GH_AW_MODEL_AGENT_COPILOT: claude-sonnet-4.6
```

From compiled lock line 126: `GH_AW_INFO_MODEL: ${{ vars.GH_AW_MODEL_AGENT_COPILOT || vars.GH_AW_DEFAULT_MODEL_COPILOT || 'claude-sonnet-4.6' }}` — override model without recompilation via repo var.

### Waiting for CI Before Running (CI Dependency)

**Pattern 1: `workflow_run` trigger** (runs after named workflow completes)

```yaml
on:
  workflow_run:
    workflows: ["PR Validation"]
    types: [completed]
```

gh-aw supports `workflow_run` (from `triggers.md`). With this trigger, the AW only fires after `PR Validation` finishes. Documented in `github/gh-aw:.github/aw/workflow-patterns.md` ("Use `workflow_run` when monitoring another GitHub Actions workflow in the same repository").

**Pattern 2: `skip-if-check-failing:`** (run on PR but skip if CI is red)

```yaml
on:
  slash_command:
    name: aw-uv-lock-review
  skip-if-check-failing:
    include: ["PR Validation"]
    allow-pending: false
```

The existing `aw-dependabot-pr-review` workflow uses a hybrid: the resolver step reads `PR_VALIDATION_CONCLUSION` manually via `actions.listWorkflowRunsForRepo` and incorporates it into the advisory (`aw-dependabot-pr-review.md:99-121`).

**Pattern 3: Inline resolver step** (repo's existing pattern — queries CI status in a `steps:` block before agent runs)

**Cannot use `needs:` across workflows** — gh-aw runs as a single job, so `needs:` only connects within the same workflow. Cross-workflow dependency requires `workflow_run` trigger or manual CI check in a resolver step.

---

## 5. Orchestration Pattern: AW → Issue → Coding Agent

### GitHub Copilot Cloud Agent (formerly "Coding Agent") Capabilities

Source: `docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent`, `docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-via-the-api`, `docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/create-automations`

**What it can do:**
- Research repo, create implementation plan, make code changes in its own ephemeral GitHub Actions environment
- Open exactly **one PR per task** (hard constraint)
- Work on one branch at a time in one specified repo (no cross-repo)
- Maximum execution time: **59 minutes** (hard limit)
- Add requester as reviewer when finished
- Uses AI credits + GitHub Actions minutes

**How to trigger it:**

1. **Issue assignment** (web UI or API): Assign `copilot` in the Assignees panel. Bot login: `copilot-swe-agent[bot]`.

2. **REST API** (`POST /agents/repos/{owner}/{repo}/tasks`):
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR-TOKEN" \
  https://api.github.com/agents/repos/OWNER/REPO/tasks \
  -d '{"prompt": "Update uv.lock to latest compatible versions", "base_ref": "main", "create_pull_request": true}'
```
Note: Only **user-to-server tokens** (PAT, OAuth, GitHub App user token) work — NOT server-to-server (installation tokens).

3. **GraphQL mutations**: `createIssue`, `updateIssue`, `addAssigneesToAssignable`, `replaceActorsForAssignable` — with `assigneeIds: [BOT_ID]` where BOT_ID is the `copilot-swe-agent` node ID from `suggestedActors`.

4. **REST issue update**:
```bash
gh api --method POST /repos/OWNER/REPO/issues \
  --input - <<< '{"title": "Update uv.lock", "body": "...", 
    "assignees": ["copilot-swe-agent[bot]"],
    "agent_assignment": {"target_repo": "OWNER/REPO", "base_branch": "main"}}'
```

### The `assign-to-agent:` Safe Output (RECOMMENDED PATTERN FOR gh-aw)

```yaml
safe-outputs:
  assign-to-agent:
    name: "copilot"                    # agent name
    model: "claude-sonnet-4-5"         # optional model override
    custom-agent: ""                   # optional custom agent ID
    custom-instructions: "..."         # additional instructions for Copilot
    allowed: [copilot]                 # restrict to Copilot only
    max: 1                             # one assignment per run
    target: "triggering"               # the triggering issue
    base-branch: "main"                # PR base branch
```

Requires PAT with elevated permissions as `GH_AW_AGENT_TOKEN` secret.

### `create-agent-session:` Safe Output (Direct Session Creation)

```yaml
safe-outputs:
  create-agent-session:
    base: main
    target-repo: "owner/repo"
```

Requires PAT as `COPILOT_GITHUB_TOKEN`.

### Recommended Orchestration Pattern for `uv.lock` Updates

```
1. AW triggered: slash_command /aw-uv-lock-review on PR touching uv.lock
   (gated: only admin/maintainer/write can trigger via roles: default)
2. AW resolver step: check PR context, validate lock file change scope
3. AW safe-output: create-issue with structured body
   - Title: "[uv-lock-update] Auto-update lock file"
   - Body: full dependency resolution context, PR number, affected packages
4. AW safe-output: assign-to-agent (assigns Copilot to the created issue)
   - custom-instructions: "Run uv lock --upgrade-package <pkg> for each flagged package"
5. Copilot Cloud Agent picks up issue, works in its Actions env, opens PR
6. Agent adds requester as reviewer on PR
```

OR simpler: gh-aw uses `create-pull-request:` directly (without Coding Agent) to push the updated `uv.lock` after running `uv lock` in a resolver `steps:` block.

### Copilot Automations vs. assign-to-agent

Copilot Automations (from `docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/create-automations`):
- **Not available in public repos** — private/internal only
- Triggers: schedule (hourly/daily/weekly), issue created, PR opened, PR synchronized
- Path filter available on PR triggers
- Stored separately from repo (not Git-versioned)
- **Not the right fit** for a slash-command-gated workflow in a public repo

**`assign-to-agent:` from gh-aw works in public repos** (assuming Copilot is enabled for the org/user), because gh-aw itself runs as a GitHub Actions workflow.

---

## 6. Required Check Gated on Path + Manual Trigger

### GitHub Required Status Check Mechanism

Source: `docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches`, `docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks`

**How required checks work:**
- Configure in branch protection rule or ruleset: "Require status checks before merging" → list check names
- Check must pass on the **latest commit SHA** of the PR head
- Allowed pass states: `success`, `skipped`, `neutral`
- Check runs created via `create-check-run:` (gh-aw) or GitHub's Checks API appear in PR UI

### The "Expected-but-Pending" Problem

> ⚠️ From GitHub docs: "If a workflow is skipped due to path filtering... checks associated with that workflow will remain in a 'Pending' state. A pull request that requires those checks to be successful will be **blocked from merging**."

If you add `create-check-run: uv-lock-review` as a required check but the gh-aw workflow only fires on slash command (not automatically on push), then every PR that touches `uv.lock` will have a pending required check until someone runs `/aw-uv-lock-review`. This IS the desired "human gate" behavior — PRs touching `uv.lock` cannot merge until a maintainer runs the command.

**This is a valid, intentional design:**
```
PR opened touching uv.lock
  → CI runs (PR Validation)
  → "uv-lock-review" check: PENDING (required, not yet run)
  → Maintainer reviews CI, decides to invoke: /aw-uv-lock-review
  → gh-aw runs, emits create-check-run with conclusion: success/failure
  → "uv-lock-review" check: SUCCESS or FAILURE
  → If success: PR can merge (if other required checks pass)
  → If failure: PR blocked; maintainer must fix and re-run
```

### Pattern A: Always-Present Default-Passing Check + Conditional Heavy Check

For PRs that DON'T touch `uv.lock`, you don't want the required check to be permanently pending. Solution:

**Wrapper GitHub Actions workflow (not gh-aw):**

```yaml
# .github/workflows/uv-lock-gate.yml
name: uv-lock-gate
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  check-paths:
    runs-on: ubuntu-latest
    outputs:
      lock-changed: ${{ steps.changed.outputs.lock }}
    steps:
      - uses: actions/checkout@v4
      - id: changed
        run: |
          if git diff --name-only origin/${{ github.base_ref }}...HEAD | grep -q 'uv\.lock'; then
            echo "lock=true" >> $GITHUB_OUTPUT
          else
            echo "lock=false" >> $GITHUB_OUTPUT
          fi

  uv-lock-review-gate:
    needs: check-paths
    runs-on: ubuntu-latest
    steps:
      - if: ${{ needs.check-paths.outputs.lock-changed == 'false' }}
        run: echo "No uv.lock changes - check passes automatically"
      - if: ${{ needs.check-paths.outputs.lock-changed == 'true' }}
        run: |
          echo "uv.lock changed - manual review required"
          echo "Invoke /aw-uv-lock-review on this PR to complete review"
          exit 1   # Or exit 0 and let the gh-aw check-run be required separately
```

**Better pattern: separate required check names:**
- `uv-lock-gate` (always runs, reports success when no `uv.lock` change)
- `uv-lock-review` (gh-aw `create-check-run`, only exists when slash command is run)

Configure branch protection to require BOTH, but use a conditional:
- When `uv.lock` is NOT changed: `uv-lock-gate` = success; `uv-lock-review` = not required (not listed as required, OR use ruleset with path condition)
- When `uv.lock` IS changed: `uv-lock-gate` = failure (forcing review); `uv-lock-review` = required and pending until `/aw-uv-lock-review` is run

### Pattern B: Environment Approval Gate

```yaml
safe-outputs:
  environment: "uv-lock-approval"   # environment with required reviewer
  create-pull-request:
    ...
```

The main workflow uses `environment: uv-lock-approval` which triggers GitHub's environment protection rules (requires a human to approve before the safe-outputs job runs).

### Pattern C: gh-aw `create-check-run` as the Required Gate

This is the most elegant pattern for `microsoft/physical-ai-toolchain`:

**Step 1: AW workflow with `create-check-run:`:**

```yaml
# .github/workflows/aw-uv-lock-review.md
---
name: AW uv.lock Review
on:
  slash_command:
    name: aw-uv-lock-review
    events: [pull_request_comment]
safe-outputs:
  create-check-run:
    name: "uv-lock-review"   # must match branch protection rule check name
    max: 1
  add-comment:
    max: 1
    target: ${{ env.PR_NUMBER }}
---
Review the uv.lock changes in the PR...
```

**Step 2: Branch protection / ruleset:** Add `uv-lock-review` as a required status check on `main`.

**Step 3: Behavior:** PRs touching `uv.lock` will have `uv-lock-review` pending until a maintainer runs `/aw-uv-lock-review`. Check created by AW with `conclusion: success` or `conclusion: failure` based on agent's analysis. This is the manual gate.

### Path-Scoped Required Check via Rulesets

GitHub rulesets (from `docs.github.com` branch protection docs) support:
- "Require status checks before merging" with specific check names
- **No native path-scoped required check** in standard branch protection

To scope the required check to only PRs touching `uv.lock`:
1. Use a traditional GH Actions workflow that runs on all PRs, but exits `0` (neutral/success) when no `uv.lock` change and exits to "needs review" state when changed
2. OR use a path-filtered `pull_request` + a "skip" job that reports `neutral` (not pending) for non-matching paths — note: skipped jobs within a workflow report `success`, but skipped workflows (due to path filter) report `pending`

**Key from GH docs:** "If a job within a workflow is skipped due to a conditional, it will report its status as 'Success'" — so a job-level `if:` (not workflow-level `paths:`) is the right approach for required checks.

---

## Summary of Key Answers

| Question | Answer |
|---|---|
| Can gh-aw fire only on slash command? | Yes — `slash_command:` trigger is exclusive |
| Can gh-aw filter by changed paths? | Yes — `paths:` on `pull_request` trigger |
| Can gh-aw CREATE a PR with code changes? | **Yes** — `create-pull-request:` safe-output, with `allowed-files`, `draft`, `base-branch`, CI trigger |
| Can gh-aw update a SINGLE comment? | Via `add-comment: { hide-older-comments: true }` or `comment-memory:` under `tools:` |
| Default role gate? | `admin`, `maintainer`, `write` — enforced in `pre_activation` job |
| Can gh-aw assign Copilot coding agent? | **Yes** — `assign-to-agent:` safe-output (requires `GH_AW_AGENT_TOKEN` PAT) |
| Can gh-aw create a Copilot session directly? | **Yes** — `create-agent-session:` safe-output (requires `COPILOT_GITHUB_TOKEN`) |
| Coding Agent trigger mechanism | Issue assignment to `copilot-swe-agent[bot]`, REST API `POST /agents/repos/{owner}/{repo}/tasks`, GraphQL, CLI |
| Coding Agent PR output | Exactly one PR per task; 59-min hard limit; single-repo only |
| Required check + path gate | `create-check-run:` in AW → register as required check; slash-command gate creates "pending until human runs" behavior |
| Path-scoped required check | Job-level `if:` (not workflow `paths:`) avoids "pending" problem; AW slash-command naturally creates the manual gate |
| Wait for CI before AW? | `workflow_run:` trigger, `skip-if-check-failing:`, or inline resolver step (repo's existing pattern) |

---

## Sources

| Source | URL / Citation |
|---|---|
| gh-aw triggers.md | `github/gh-aw:.github/aw/triggers.md` SHA `1452121194` |
| gh-aw syntax-core.md | `github/gh-aw:.github/aw/syntax-core.md` SHA `9e3c8919` |
| gh-aw syntax-agentic.md | `github/gh-aw:.github/aw/syntax-agentic.md` SHA `3ba9e56f` |
| gh-aw safe-outputs-content.md | `github/gh-aw:.github/aw/safe-outputs-content.md` SHA `750876ed` |
| gh-aw safe-outputs-management.md | `github/gh-aw:.github/aw/safe-outputs-management.md` SHA `73ecbf00` |
| gh-aw safe-outputs-automation.md | `github/gh-aw:.github/aw/safe-outputs-automation.md` SHA `0b1b9a9e` |
| gh-aw safe-outputs-runtime.md | `github/gh-aw:.github/aw/safe-outputs-runtime.md` SHA `731d8702` |
| gh-aw workflow-patterns.md | `github/gh-aw:.github/aw/workflow-patterns.md` SHA `a7aa26de` |
| gh-aw workflow-constraints.md | `github/gh-aw:.github/aw/workflow-constraints.md` SHA `452922f0` |
| Existing AW workflow | `algattik/physical-ai-toolchain:.github/workflows/aw-dependabot-pr-review.md:1-240` |
| Compiled lock file | `algattik/physical-ai-toolchain:.github/workflows/aw-dependabot-pr-review.lock.yml:1-1700` |
| Copilot cloud agent overview | `https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent` |
| Copilot cloud agent API | `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-via-the-api` |
| Copilot automations | `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/create-automations` |
| GitHub branch protection | `https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches` |
| Required check troubleshooting | `https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks` |

---

## Executive Summary

**Subagent file path:** `.copilot-tracking/research/subagents/2026-06-19/ghaw-and-coding-agent-capabilities.md` *(content above)*

**Status:** ✅ Complete

**Key findings (≤7 bullets, ≤240 chars each):**

1. **gh-aw CAN create PRs**: `create-pull-request:` safe-output pushes git patches to a new branch and opens a PR; defaults to draft; requires `allowed-files:` scope; CI not auto-triggered (use `github-token-for-extra-empty-commit`).

2. **Required check gate works as intended**: gh-aw `create-check-run:` registered as required branch-protection check + slash-command trigger = "pending until maintainer runs `/cmd`"; this naturally implements path-scoped manual gate.

3. **Path-filter gotcha**: Workflow `paths:` filter leaves required checks "Pending" forever. Fix: use job-level `if:` (reports `success`) NOT workflow-level `paths:`, or accept "pending = gate not yet invoked" as the intentional gate behavior.

4. **Default role gate is write+**: `on.roles:` defaults `[admin, maintainer, write]`; compiled to `check_membership.cjs` with `GH_AW_REQUIRED_ROLES: admin,maintainer,write`; verified in existing lock file line 1647.

5. **Coding Agent assign pattern confirmed**: `assign-to-agent:` safe-output assigns `copilot-swe-agent[bot]` to an issue; Copilot starts autonomously, opens exactly one PR, requests review. Requires `GH_AW_AGENT_TOKEN` PAT.

6. **`update-comment` is via `hide-older-comments`**: No dedicated `update-comment:` — use `add-comment: { hide-older-comments: true }` to minimize previous comments; or `comment-memory:` (under `tools:`) for persistent single managed comment.

7. **Copilot Automations NOT suitable for public repos**: Automations require private/internal repos; the gh-aw `assign-to-agent:` safe-output is the correct mechanism for public repo orchestration to Coding Agent.

---

**Next research items (≤5):**

1. Verify whether `create-check-run:` output is created on the PR head SHA or the workflow run SHA — this determines whether it satisfies branch protection requirements for the PR's commit.
2. Research the `GH_AW_AGENT_TOKEN` PAT minimum required permissions for `assign-to-agent:` (issue assignment scope needed).
3. Investigate `copilot-setup-steps.yml` in the repo (already present at `.github/workflows/copilot-setup-steps.yml`) — what's its current configuration and how does it affect Coding Agent environment setup.
4. Confirm whether `microsoft/physical-ai-toolchain` is public or private, as this affects Copilot Automations availability and required check behavior on fork PRs.
5. Research GitHub's native "path-conditional required check" via rulesets — newer ruleset features may support condition-based required checks without wrapper workflows.

---

**Blocking clarifying questions (≤3):**

1. **Is `microsoft/physical-ai-toolchain` public or private?** Copilot Automations (the alternative to `assign-to-agent:`) require private/internal; the current research assumes public.
2. **Should the required check BLOCK merge (hard gate) or WARN (advisory)?** Both patterns are implementable but the architecture differs significantly — hard gate needs `create-check-run:` as required check; advisory needs only `add-comment:` or `submit-pull-request-review:`.
3. **Does the team want the Coding Agent to auto-update `uv.lock` (write access, creates PR) or just review/annotate it (read-only, advisory)?** The answer determines whether `create-pull-request:` or `assign-to-agent:` or `submit-pull-request-review:` is the right safe-output.