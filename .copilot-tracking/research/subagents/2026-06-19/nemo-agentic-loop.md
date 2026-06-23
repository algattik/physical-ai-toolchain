<!-- markdownlint-disable-file -->
---

## Research Findings: NVIDIA-NeMo/NeMo — GPU CI Gating & Agentic Babysitter Loop

> **Note on deliverable:** The `.copilot-tracking/` directory does not exist in this repo and the subagent operating constraints prohibit writing output files. All findings are returned inline below. The main agent should create `.copilot-tracking/research/subagents/2026-06-19/nemo-agentic-loop.md` from this content.

---

### 1. Summary

NVIDIA-NeMo/NeMo (the live repo, redirected from NVIDIA/NeMo) contains three tiers of CI safety: (a) cheap checks (linting, formatting, copyright) run automatically on every push; (b) expensive GPU tests are gated behind a **"Run CICD" label** (human-applied) plus an `environment: test` deployment gate that a programmatic queue-manager bot approves one-at-a-time to enforce concurrency limits; (c) an agentic "babysitter" loop (`claude-babysit-pr.yml`) that uses Claude via `anthropics/claude-code-action@v1` to investigate CI failures, post a repair plan, wait for a **human approval comment** (`@claude go ahead`), then execute the fix and re-trigger CI. The entire agentic loop is restricted to `speech_team` GitHub team members and has hard fork-guards throughout.

---

### 2. Repositories Discovered

| Repo | Purpose |
|---|---|
| `NVIDIA-NeMo/NeMo` | Main NeMo framework repo (redirects from `NVIDIA/NeMo`) — 28 KB workflow directory |
| `NVIDIA-NeMo/FW-CI-templates` | Shared reusable workflow templates (`_cicd_preflight.yml`, `_claude_review.yml`, etc.) |

---

### 3. Key Source Files

| File | Size | Purpose |
|---|---|---|
| `NVIDIA-NeMo/NeMo:.github/workflows/claude-babysit-pr.yml` | 28 KB | **The agentic babysitter** — full investigate/propose/approve/execute loop |
| `NVIDIA-NeMo/NeMo:.github/workflows/cicd-main.yml` | 14 KB | Main GPU CI workflow — environment gate, GPU runner, label gating |
| `NVIDIA-NeMo/NeMo:.github/workflows/cicd-approve-test-queue.yml` | 10 KB | Queue manager bot — auto-approves `environment: test` deployments up to `MAX_CONCURRENCY` |
| `NVIDIA-NeMo/NeMo:.github/workflows/cicd-main-speech.yml` | 25 KB | GPU speech tests — shows self-hosted `nemo-ci-aws-gpu-x2` runner and `--gpus all` Docker |
| `NVIDIA-NeMo/NeMo:.github/workflows/claude-fix.yml` | 3.9 KB | On-demand `/claude fix` bot for issues |
| `NVIDIA-NeMo/NeMo:.github/workflows/claude-review.yml` | 1.8 KB | On-demand `/claude review` bot for PRs |
| `NVIDIA-NeMo/FW-CI-templates:.github/workflows/_cicd_preflight.yml` | 9 KB | Preflight: NVIDIA SSO check, runner selection (NVIDIA vs public runners) |

---

### 4. Implementation Details with Code Evidence

#### 4a. GPU CI Gating — `cicd-main.yml`

**Trigger pattern:** GPU tests fire on `push` to branches matching `"pull-request/[0-9]+"`. These branches are created by a "copy-pr-bot" that mirrors fork PRs into the base repo, completely avoiding the `pull_request_target` "pwn request" risk.

```yaml
# NVIDIA-NeMo/NeMo:.github/workflows/cicd-main.yml (lines ~18-24)
on:
  push:
    branches:
      - main
      - r**
      - "pull-request/[0-9]+"   # ← copy-pr-bot branches for fork PRs
  workflow_dispatch:
```

**`environment: test` queue gate** (key GPU gating mechanism):

```yaml
# NVIDIA-NeMo/NeMo:.github/workflows/cicd-main.yml (~line 90-100)
cicd-wait-in-queue:
  needs: [configure, code-linting]
  runs-on: ubuntu-latest
  environment: test          # ← PAUSES until approved by queue bot
  if: |
    needs.configure.outputs.test_to_run != '[]'
    && needs.configure.outputs.components_to_run != '[]'
    && needs.configure.outputs.is_ci_workload == 'false'
  steps:
    - name: Running CI tests
      run: echo "Running CI tests"
```

All expensive GPU jobs (`cicd-test-container-build`, `cicd-main-speech`, `L0_Setup_Test_Data_And_Models`) depend on `cicd-wait-in-queue`, so they cannot start until that environment gate clears.

**GPU runner label** (from `cicd-main-speech.yml`):
```yaml
# NVIDIA-NeMo/NeMo:.github/workflows/cicd-main-speech.yml (~line 21)
runner:
  default: nemo-ci-aws-gpu-x2
  description: "Runner to use for GPU jobs"
```

Docker flags confirm GPU access:
```yaml
# NVIDIA-NeMo/NeMo:.github/workflows/cicd-main.yml (~line 150)
docker run \
  --rm \
  --device=/dev/nvidia0 \
  --gpus all \
  --shm-size=8g \
```

#### 4b. Queue Manager Bot — `cicd-approve-test-queue.yml`

Runs every 5 minutes via `schedule: cron: '*/5 * * * *'`. It calls the GitHub API to find `CICD NeMo` workflow runs in `waiting` status (paused at `environment: test`), sorts oldest-first, and approves them one by one until `MAX_CONCURRENCY` (repo variable) is reached.

```yaml
# NVIDIA-NeMo/NeMo:.github/workflows/cicd-approve-test-queue.yml (~line 23)
jobs:
  approve-queue:
    runs-on: ubuntu-latest
    environment: main        # ← bot itself is also gated (holds the PAT)
    steps:
      ...
      - name: Approve waiting deployments
        env:
          GITHUB_TOKEN: ${{ secrets.PAT }}
          MAX_CONCURRENCY: ${{ vars.MAX_CONCURRENCY || 1 }}
        run: |
          python - <<EOF
          # ... fetches waiting CICD NeMo runs, approves oldest if total < MAX_CONCURRENCY
          status_data = {
              "environment_ids": environment_ids,
              "state": "approved",
              "comment": "Automatically approved by queue manager"
          }
          EOF
```

> **Key nuance:** This is **programmatic (automatic) approval** for GPU concurrency management, NOT human-gated security review. Human control enters via the "Run CICD" label requirement.

#### 4c. "Run CICD" Label Gate and NVIDIA SSO Check

From `_cicd_preflight.yml`:
```yaml
# NVIDIA-NeMo/FW-CI-templates:.github/workflows/_cicd_preflight.yml (~line 95)
- name: Select runner and test data path
  env:
    IS_MEMBER: ${{ steps.check-sso.outputs.is_member }}
  run: |
    if [[ "$IS_MEMBER" == "true" || "$IS_CI_WORKLOAD" == "true" ]]; then
      echo "runner_prefix=${{ inputs.default_runner_prefix }}"  # NVIDIA GPU runners
    else
      echo "runner_prefix=${{ inputs.non_nvidia_runner_prefix }}"  # Public runners (no GPU data access)
```

NVIDIA SSO members get the fast, private GPU runners. External contributors get public runners with restricted test data paths.

---

#### 4d. The Agentic Babysitter — `claude-babysit-pr.yml` (FULLY VERIFIED)

**File header documents the complete lifecycle:**
```yaml
# NVIDIA-NeMo/NeMo:.github/workflows/claude-babysit-pr.yml (lines 1-47)
# PR Babysitter — half-autonomous CI fix loop, speech_team-only.
#
# Lifecycle (all participants must be speech_team members):
#   1. "Has Babysitter" added  -> activate posts a takeover comment and adds
#                                 "Run CICD" to start the pipeline.
#   2. CI runs (CICD NeMo workflow).
#   3. If all checks pass      -> babysitter stays silent, done.
#      If a CI workflow fails  -> workflow_run completion event triggers
#                                 investigate-and-propose.
#   4. investigate-and-propose: Claude investigates root cause, posts a *plan
#      comment* on the PR (tagged with <!-- babysit-plan -->), and adds
#      "Agent Plan Awaiting Approval". It does NOT push code.
#   5. The PR author approves by replying with a comment that mentions `@claude`
#      affirmatively (e.g., `@claude go ahead`).
#   6. "Agent Plan Approved" added -> execute-fix verifies sender is speech_team,
#      verifies a bot-authored plan comment exists, then reads the plan, pushes
#      the fix, re-adds "Run CICD", and goes back to #2.
```

**Triggers:**
```yaml
on:
  pull_request:
    types: [labeled, unlabeled]
  workflow_run:
    workflows:
      - "CICD NeMo"
      - "PyLint and flake8 linting"
      # ... 6 more CI workflow names
    types: [completed]
  issue_comment:
    types: [created]
```

> Note: Uses `workflow_run` (not `check_run`) specifically because GitHub's recursion guard blocks `check_run` events from GHA-produced check suites. The comments in the file explicitly explain this.

**Fork guard (repeated on every job):**
```yaml
# Example from check-label-for-ci job
const isFork = pr.head.repo.full_name !== `${context.repo.owner}/${context.repo.repo}`;
const shouldPropose = hasBabysitter && !hasPending && !hasApproved && !isStale && !isFork;
```

**Claude's "investigate and propose" step (read-only):**
```yaml
# claude-babysit-pr.yml investigate-and-propose job
- uses: anthropics/claude-code-action@v1
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    prompt: |
      You are in HALF-AUTONOMOUS mode. You MUST NOT edit files, commit,
      or push code in this job. Investigation and planning only.
      ...
      Post a SINGLE PR comment with this structure:
        **CI Fix Plan** — awaiting approval from @<author>
        <analysis and proposed change>
        <!-- babysit-plan -->
    claude_args: "--max-turns 10 --model claude-sonnet-4-6"
```

**Human approval classification:**
```yaml
# claude-babysit-pr.yml evaluate-comment-approval job
- uses: anthropics/claude-code-action@v1
  with:
    prompt: |
      Classify the reply as exactly one of:
        - APPROVE: the author clearly agrees to proceed with the plan.
        - REJECT: the author clearly disagrees or wants changes.
        - NEITHER: the reply is a question, side remark, or ambiguous.
      Take action:
        - APPROVE: run `gh pr edit $PR_NUMBER --remove-label "Agent Plan Awaiting Approval"
                   --add-label "Agent Plan Approved"` and do nothing else.
        - REJECT: post a short PR comment acknowledging the rejection.
        - NEITHER: post a short PR comment asking for an explicit approve/reject.
      Do not push any code. Do not edit files in the repository.
    claude_args: "--max-turns 8 --model claude-sonnet-4-6"
```

**Execute-fix (the only code-push job):**
```yaml
# claude-babysit-pr.yml execute-fix job
# Preflight 1: sender must be speech_team
# Preflight 2: a bot-authored <!-- babysit-plan --> comment must exist
- uses: anthropics/claude-code-action@v1
  with:
    prompt: |
      The PR author has approved your previously posted fix plan. Execute it now.
      1. Read the PR comment thread and find the most recent comment containing <!-- babysit-plan -->
      2. Implement exactly what the plan described. Do not expand scope.
      3. Commit with DCO sign-off and push to the same branch.
    claude_args: "--max-turns 10 --model claude-sonnet-4-6"

- name: Re-trigger CI or stop loop
  run: |
    NEW_SHA=$(gh pr view "$PR_NUMBER" --json headRefOid -q '.headRefOid')
    if [ "$NEW_SHA" != "$ORIGINAL_SHA" ]; then
      gh pr edit "$PR_NUMBER" --add-label "Run CICD"  # ← restarts the loop
    else
      gh pr edit "$PR_NUMBER" --remove-label "Has Babysitter"
    fi
```

---

#### 4e. GitHub Docs — Environments & Required Reviewers (Verified)

From `https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments`:
> "**Secrets stored in an environment are only available to workflow jobs that reference the environment. If the environment requires approval, a job cannot access environment secrets until one of the required reviewers approves it.**"
> "You can list up to six users or teams as reviewers. The reviewers must have at least read access to the repository. Only one of the required reviewers needs to approve the job for it to proceed."

From `https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments`:
> "specify people or teams that must approve workflow jobs that use this environment" and "Optionally, to prevent users from approving workflows runs that they triggered, select **Prevent self-review**."

#### 4f. `pull_request_target` / "Pwn Request" Risk (Verified from GitHub Security Lab)

From `https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/`:
> "Workflows triggered via `pull_request_target` have write permission to the target repository. They also have access to target repository secrets."
> "The main differences: `pull_request_target` runs in the context of the target repository... [and has] write permission to the target repository."

NeMo's mitigation: They avoid `pull_request_target` entirely. Fork PRs are mirrored to `pull-request/NNN` branches by a bot, so the `push` trigger fires — safe, with no fork code executing in a privileged context.

---

### 5. What NeMo Does NOT Have

| Pattern | Status |
|---|---|
| `/blossom-ci` comment trigger | ❌ Not found (no evidence in any workflow file) |
| `environment:` with human required-reviewers for GPU | ❌ Their `environment: test` uses a **programmatic bot** approver, not human |
| `pull_request_target` trigger | ❌ Deliberately avoided (copy-pr-bot instead) |
| An agentic loop that uses GitHub Environments to gate secrets | ❌ The babysitter uses label + comment approval, not environment-based secrets gating |

---

### 6. Gaps and Uncertainties

1. **"Run CICD" label mechanism** — exactly who can add this label is controlled by repository branch protection / label permissions settings which are not visible in workflow YAML; inferred from context that team maintainers add it.
2. **`environment: main`** on the queue bot — we can see it has a `PAT` secret, but the required-reviewers config for the `main` environment is a repo setting not visible in YAML.
3. **Copy-pr-bot** — referenced by branch naming pattern `pull-request/[0-9]+` but the bot itself is not a visible GitHub Actions workflow in the public repo; likely a separate service or a GitHub App.
4. **`MAX_CONCURRENCY` value** — set as a repo variable, not visible in YAML; the code defaults to `1` if unset.
5. **`claude-answer.yml`** — not fetched (only 2 KB); likely a general Q&A bot similar to `claude-review.yml`.

---

## SLIDE-READY MATERIAL

---

### Plain-English Explanation (6–8 sentences)

Large ML repos like NVIDIA's NeMo framework face two practical problems when running CI on pull requests: **GPU time costs serious money** (a single training run can cost hundreds of dollars), and **fork contributors may submit untrusted code** that could exfiltrate secrets or abuse compute. NeMo's solution has three layers. First, cheap checks — linting, formatting, copyright scans — run immediately and automatically on every push. Second, GPU tests sit in a queue gated by a label ("Run CICD") that a human must apply, and then a programmatic bot approves them one at a time (controlled by a `MAX_CONCURRENCY` variable) using a GitHub "Deployment Environment" — a feature that pauses a workflow job until the environment's approval conditions are met. Third, when CI fails, an **agentic Claude-powered "babysitter"** wakes up, reads the failure logs, and posts a written repair plan on the PR — but it *explicitly cannot push code at this stage*. The human (PR author) must reply with something like `@claude go ahead`, which a second Claude instance classifies as Approve / Reject / Ambiguous; only a confirmed "Approve" flips a label that unlocks the code-push job. The whole agentic loop refuses to run on fork PRs (a hard code check), and all actions are restricted to team members — this is why ML repos can afford to give an AI agent write access: humans remain the final gate before any code touches the branch.

---

### Concrete YAML Snippet — Gated GPU Job with Environment

> **Source basis:** This snippet is a simplified, slide-legible extract drawn directly from `NVIDIA-NeMo/NeMo:.github/workflows/cicd-main.yml` (the `cicd-wait-in-queue` + downstream GPU job pattern) and the `cicd-approve-test-queue.yml` bot. The `environment: gpu-ci` name is renamed for clarity; NeMo calls theirs `test`.

```yaml
# ── Slide: How NeMo gates GPU CI with a Deployment Environment ──────────────

# 1️⃣  Cheap checks run instantly, no gate
lint:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: ruff check . && pytest tests/unit/

# 2️⃣  A "wait in queue" job holds the GPU work
#     environment: gpu-ci pauses here until approved
wait-for-gpu-slot:
  needs: [lint]
  runs-on: ubuntu-latest
  environment: gpu-ci       # ← job pauses; env secrets withheld until approved
  steps:
    - run: echo "Approved — GPU slot acquired"

# 3️⃣  Expensive GPU jobs only start after the gate clears
gpu-e2e-tests:
  needs: [wait-for-gpu-slot]
  runs-on: [self-hosted, gpu, aws]   # ← private self-hosted GPU runner
  steps:
    - uses: actions/checkout@v4
    - run: |
        docker run --rm --gpus all $IMAGE \
          pytest tests/e2e/ --timeout=1800
```

> **How the gate works:** In the GitHub repo Settings → Environments → `gpu-ci`, configure **Required Reviewers** (up to 6 people/teams). When the `wait-for-gpu-slot` job reaches that environment, GitHub emails the reviewers and pauses the job. Only after one clicks Approve does the job proceed — and only then does it gain access to environment-scoped secrets (GPU cluster credentials, model registry tokens, etc.). NeMo uses a *bot* as the reviewer (running on a 5-minute cron) to approve automatically but one-at-a-time, enforcing concurrency without requiring a human click per run.

---

### What NVIDIA-NeMo Actually Does — Evidence List

#### ✅ Verified Facts (with permalinks)

| Claim | Evidence |
|---|---|
| GPU tests gated by `environment: test` deployment environment | [`cicd-main.yml` L90-100](https://github.com/NVIDIA-NeMo/NeMo/blob/main/.github/workflows/cicd-main.yml) — `cicd-wait-in-queue` job with `environment: test` |
| Programmatic queue bot approves GPU runs (not human) | [`cicd-approve-test-queue.yml`](https://github.com/NVIDIA-NeMo/NeMo/blob/main/.github/workflows/cicd-approve-test-queue.yml) — Python script calls GitHub Deployments API `state: approved`, every 5 min cron |
| Self-hosted GPU runners (`nemo-ci-aws-gpu-x2`) | [`cicd-main-speech.yml` L21](https://github.com/NVIDIA-NeMo/NeMo/blob/main/.github/workflows/cicd-main-speech.yml) — `runner: nemo-ci-aws-gpu-x2` |
| GPU jobs run Docker with `--gpus all --device=/dev/nvidia0` | [`cicd-main.yml` ~L150](https://github.com/NVIDIA-NeMo/NeMo/blob/main/.github/workflows/cicd-main.yml) |
| "Run CICD" label required to enter queue | [`_cicd_preflight.yml`](https://github.com/NVIDIA-NeMo/FW-CI-templates/blob/main/.github/workflows/_cicd_preflight.yml) + `configure` job label fetch |
| Fork PRs handled via copy-pr-bot `pull-request/NNN` branches (avoids `pull_request_target`) | [`cicd-main.yml` triggers](https://github.com/NVIDIA-NeMo/NeMo/blob/main/.github/workflows/cicd-main.yml) — `push: branches: "pull-request/[0-9]+"` |
| Agentic babysitter uses `anthropics/claude-code-action@v1` | [`claude-babysit-pr.yml`](https://github.com/NVIDIA-NeMo/NeMo/blob/main/.github/workflows/claude-babysit-pr.yml) |
| `investigate-and-propose` explicitly forbidden from pushing code | [`claude-babysit-pr.yml`](https://github.com/NVIDIA-NeMo/NeMo/blob/main/.github/workflows/claude-babysit-pr.yml) — `"You MUST NOT edit files, commit, or push code in this job."` |
| Human approval via `@claude` affirmative comment is required | [`claude-babysit-pr.yml`](https://github.com/NVIDIA-NeMo/NeMo/blob/main/.github/workflows/claude-babysit-pr.yml) — `evaluate-comment-approval` job |
| Code-push only fires when `<!-- babysit-plan -->` bot comment confirmed to exist | [`claude-babysit-pr.yml`](https://github.com/NVIDIA-NeMo/NeMo/blob/main/.github/workflows/claude-babysit-pr.yml) — `execute-fix` preflight step |
| Entire agentic loop is `speech_team`-only via GitHub team membership API | [`claude-babysit-pr.yml`](https://github.com/NVIDIA-NeMo/NeMo/blob/main/.github/workflows/claude-babysit-pr.yml) — `teams.getMembershipForUserInOrg` on every job |
| Hard fork-guard on every agentic job | [`claude-babysit-pr.yml`](https://github.com/NVIDIA-NeMo/NeMo/blob/main/.github/workflows/claude-babysit-pr.yml) — `pr.head.repo.full_name !== context.repo.owner/context.repo.repo` |
| Additional on-demand `/claude fix` and `/claude review` bots | [`claude-fix.yml`](https://github.com/NVIDIA-NeMo/NeMo/blob/main/.github/workflows/claude-fix.yml), [`claude-review.yml`](https://github.com/NVIDIA-NeMo/NeMo/blob/main/.github/workflows/claude-review.yml) |
| GitHub Environments: secrets withheld until reviewer approves | [GitHub Docs](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments) — "If the environment requires approval, a job cannot access environment secrets until one of the required reviewers approves it." |
| `pull_request_target` gives secrets to fork code = "pwn request" risk | [GitHub Security Lab](https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/) — "Workflows triggered via `pull_request_target` have write permission to the target repository. They also have access to target repository secrets." |

#### ❌ Claims NOT Verified in NeMo

| Claim | Finding |
|---|---|
| `/blossom-ci` comment trigger | No evidence in any workflow file |
| Human-gated `environment:` required reviewers for GPU tests | NeMo uses **automatic bot approval** for `environment: test`, not human required reviewers |
| `pull_request_target` trigger usage | Absent — NeMo deliberately avoids it via copy-pr-bot |

#### ⚠️ Reasonable Inferences (not directly verified from workflow YAML)

| Inference | Basis |
|---|---|
| The `environment: main` on the queue bot has the PAT secret and may have required reviewers configured as a secondary gate | `cicd-approve-test-queue.yml` uses `environment: main` with `secrets.PAT` — settings not visible in YAML |
| External contributors without NVIDIA SSO membership get routed to non-GPU runners | `_cicd_preflight.yml` `select_runner` step checks `IS_MEMBER` — exact runner labels for non-NVIDIA path are repo variables |

---

### One-Paragraph Context for Slides

> NVIDIA's NeMo repo is one of the best documented public examples of a **two-axis CI safety system**: GPU cost is controlled by a concurrency queue (bot-approved `environment:` gate), and agent autonomy is controlled by a human-in-the-loop approval step (comment → label flip). The key insight for our work is that GitHub Environments are the *mechanical enforcement point* — a job literally cannot start, and cannot access any secrets, until the environment's protection rules pass. Pairing that with a Claude-powered agent that can only *propose* (never push) until a human says "go ahead" gives you an auditable, cancellable, cost-bounded agentic CI assistant. The NeMo team also hardened it against the main GitHub Actions security risks: no fork code ever runs in a privileged context (copy-pr-bot pattern), and team-membership checks are enforced on every job that mutates state.