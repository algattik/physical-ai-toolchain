# GitHub Agentic Workflows for Dependabot PR Regression Safety

GitHub Agentic Workflows (gh-aw) turns a markdown file with YAML frontmatter into a compiled GitHub Actions workflow. The compiled workflow calls an AI engine such as Copilot, but keeps the main agent job read-only; writes to GitHub happen only through declared `safe-outputs` such as comments, issues, pull requests, or labels. That split is the safety model: the agent can inspect code, PRs, CI and release notes, then it must ask a constrained output processor to perform any write.

## Today: advisory reviewer invoked by a maintainer

```yaml
---
name: AW Dependabot PR Review
engine: copilot # use Copilot as the AI engine
on:
  slash_command: { name: aw-dependabot-review, events: [pull_request_comment] } # run only when a maintainer comments /aw-dependabot-review
permissions: { contents: read, pull-requests: read, actions: read, checks: read } # read-only token for repo, PR and CI context
tools:
  github: { toolsets: [context, repos, pull_requests] } # read GitHub context and PR data
  web-fetch: # fetch advisory and release-note pages
  bash: ["cat **/*.toml", "cat **/go.mod", "jq . **/*.json"] # read manifests; do not run validation
safe-outputs:
  add-comment: { max: 2, target: "${{ env.PR_NUMBER }}" } # only approved write channel shown here
  noop: { max: 1 } # safe no-op when the PR is out of scope
---
```

The repository workflow uses `engine: copilot`, a `slash_command` trigger, read-only `permissions`, constrained `tools`, and `safe-outputs` for comments and reviews (`.github/workflows/aw-dependabot-pr-review.md:4`, `.github/workflows/aw-dependabot-pr-review.md:6-16`, `.github/workflows/aw-dependabot-pr-review.md:143-168`). Its prompt says it is advisory-only, Dependabot-scoped, and anchored on PR Validation rather than rerunning validation inside the sandbox (`.github/workflows/aw-dependabot-pr-review.md:173-195`, `.github/workflows/aw-dependabot-pr-review.md:210-239`).

## Proposed: automatic CI follow-up after PR Validation

```yaml
---
name: Dependabot CI Follow-up
engine: copilot # markdown workflow compiled by gh-aw into .lock.yml
on:
  workflow_run: { workflows: ["PR Validation"], types: [completed] } # wait until the normal PR CI finishes
  skip-if-check-failing: { include: ["PR Validation"], allow-pending: true } # skip agent work when this CI signal is red
bots: [dependabot[bot]] # allow the Dependabot-triggered run through the bot gate
permissions: { contents: read, pull-requests: read, actions: read, checks: read } # no write permissions in the agent job
tools:
  github: { toolsets: [context, repos, pull_requests, actions] } # find the PR and read run/check data
  web-fetch: # read release notes and advisory pages
safe-outputs:
  add-comment: { max: 1, target: "*", hide-older-comments: true } # one updating PR comment
  create-issue: { max: 1, title-prefix: "[dependabot-risk] ", labels: [dependencies], assignees: [copilot] } # high-risk follow-up for Copilot
---
Classify the Dependabot bump after PR Validation. Comment for low risk; create one Copilot-assigned issue for high risk.
```

Use this as a follow-up pattern, not a merge gate. For low-risk bumps with green PR Validation, the agent posts a single refreshed comment. For high-risk bumps, it opens one issue and assigns `copilot`, which gives the coding agent a concrete repair task instead of asking a human to reverse-engineer the failure.

## Generalist explanation

A gh-aw workflow is source-controlled automation written in markdown, then compiled to a `.lock.yml` GitHub Actions workflow before it runs. The frontmatter declares when it starts, which AI engine it uses, which read tools it may call, and which constrained write actions are allowed. In this repository, the current Dependabot reviewer is manual: a maintainer comments `/aw-dependabot-review`, the agent reads the Dependabot PR and CI state, then posts advisory review output. That fits teams that want human control before spending agent time. The proposed version moves the trigger to `workflow_run`, so the agent waits for the existing `PR Validation` workflow, avoids noisy work with `skip-if-check-failing`, and then turns a dependency bump into a readable risk classification. `hide-older-comments` keeps the PR from accumulating stale bot comments, while `create-issue` with `assignees: [copilot]` turns risky updates into follow-up work. The pattern scales Dependabot triage without giving an AI job broad write permissions.

## Glossary

| Term | Meaning |
| --- | --- |
| `engine` | The AI runner for the workflow, for example `copilot`, `claude`, `codex`, or `gemini`. |
| `safe-outputs` | Declarative write channels handled outside the read-only agent job, such as `add-comment`, `create-issue`, `create-pull-request`, and `add-labels`. |
| Lock file | The generated `.lock.yml` GitHub Actions workflow produced by `gh aw compile`; frontmatter edits require recompilation. |
| `slash_command` | A command trigger that runs when an allowed user comments a slash command such as `/aw-dependabot-review`. |
| `workflow_run` | A standard GitHub Actions trigger that starts this workflow after another workflow, such as `PR Validation`, completes. |

## Sources and verification notes

| Claim | Source |
| --- | --- |
| The repo uses one gh-aw Dependabot PR reviewer with Copilot, slash command activation, read-only permissions, tools, and safe outputs. | `.github/workflows/aw-dependabot-pr-review.md:4-16`, `.github/workflows/aw-dependabot-pr-review.md:143-168` |
| The reviewer is advisory-only, Dependabot-scoped, and anchored on PR Validation/checks. | `.github/workflows/aw-dependabot-pr-review.md:173-239` |
| The repo's gh-aw agent describes markdown workflows, `.lock.yml` compilation, safe outputs, sandboxing, and the Dependabot recompile pattern. | `.github/agents/agentic-workflows.agent.md:9`, `.github/agents/agentic-workflows.agent.md:21`, `.github/agents/agentic-workflows.agent.md:31-34`, `.github/agents/agentic-workflows.agent.md:176-191` |
| Dependabot ignores `github/gh-aw-actions/*` because gh-aw compile manages those action versions. | `.github/dependabot.yml:219-232` |
| Upstream describes markdown workflows, read-only default permissions, and writes through sanitized safe outputs. | https://raw.githubusercontent.com/github/gh-aw/main/README.md |
| Upstream v0.68.3 confirms `engine`, standard `on:` triggers plus `slash_command`, read-only permissions, `tools`, `skip-if-check-failing`, `safe-outputs`, `add-comment.hide-older-comments`, `create-issue.assignees`, `create-pull-request`, and `add-labels`. | https://raw.githubusercontent.com/github/gh-aw/v0.68.3/.github/aw/github-agentic-workflows.md |
| Latest trigger docs confirm standard events, `schedule`, `slash_command`, and `label_command` patterns. | https://raw.githubusercontent.com/github/gh-aw/main/.github/aw/triggers.md |
| Latest memory docs confirm `cache-memory`, `repo-memory`, and `comment-memory` as persistence options. | https://raw.githubusercontent.com/github/gh-aw/main/.github/aw/memory.md |

I did not find a separate top-level trigger named `command` in the fetched docs. The confirmed command-style fields are `slash_command` and `label_command`; `workflow_run` and `schedule` are standard GitHub Actions events accepted under `on:`.
