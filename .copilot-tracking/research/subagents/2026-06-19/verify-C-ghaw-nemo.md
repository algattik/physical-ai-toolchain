<!-- markdownlint-disable-file -->
# Fact-Check: gh-aw & NeMo Claims — 2026-06-22

Verdict: **all 10 claims PASS** (primary source verified); no invented fields. Flags below.

Sources: gh-aw README (github/gh-aw@main), spec v0.68.3 `.github/aw/github-agentic-workflows.md`; NVIDIA-NeMo/NeMo `.github/workflows/{claude-babysit-pr,cicd-main,cicd-main-speech,cicd-approve-test-queue}.yml`.

| # | Claim | Verdict | Notes / Correction |
|---|---|---|---|
| 1 | `engine: copilot` valid | PASS | spec lists copilot (default)/claude/codex/gemini |
| 2a | `on: slash_command: {name}` trigger | PASS | documented; no separate top-level `command:` trigger (only slash_command/label_command) |
| 2b | `events: [pull_request_comment]` under slash_command | PASS | documented event identifier |
| 3 | `on: workflow_run: {workflows, types:[completed]}` | PASS | confirmed via `github.event.workflow_run.*` context vars + NeMo usage; not in the spec's short trigger-examples list |
| 4 | `skip-if-check-failing:` with `include:` | PASS — but **FIX slide** | real field, **nested under `on:`**. `GHAW_PROPOSED` is correct; the `CMP_REV_RIGHT` snippet mis-indents it at top level and shows `add-comment:` without its `safe-outputs:` parent → fix indentation. |
| 5a | `add-comment` (max/target/hide-older-comments) | PASS | all documented |
| 5b | `create-issue` (labels/assignees) | PASS | documented |
| 5c | `assignees: [copilot]` hands to coding agent | PASS (nuance) | documented (`use 'copilot' for bot`), but the **purpose-built** type is `assign-to-agent:` (needs `GH_AW_AGENT_TOKEN`). Framing "hand to the coding agent" is directionally fine. |
| 6 | read-only agent; acts only via safe-outputs | PASS | README/spec: read-only default, writes only via sanitized safe-outputs |
| 7 | `claude-babysit-pr.yml` human-gated loop, `anthropics/claude-code-action@v1` | PASS (simplified) | lifecycle confirmed (investigate→plan comment, no push; human `@claude go ahead`; classify; execute-fix verifies team membership + plan comment, pushes, re-runs). Deck snippet shows 2 of 5 triggers and 1 of 8 workflow_run workflows — acceptable simplification; notes accurate. |
| 8 | GPU gated via `environment: test` + queue-bot up to MAX_CONCURRENCY | PASS | `cicd-wait-in-queue` (environment: test); `cicd-approve-test-queue.yml` cron */5 approves waiting runs |
| 9 | fork PRs mirrored to `pull-request/NNN`; no pull_request_target | PASS | `on.push.branches: ["pull-request/[0-9]+"]`; comment names copy-pr-bot; no pull_request_target trigger |
| 10 | self-hosted `nemo-ci-aws-gpu-x2`, `--gpus all` | PASS | runner default confirmed; test-template uses `--runtime=nvidia --gpus all` |

## Actions for the deck
- **Fix** `CMP_REV_RIGHT` (slides_src.py, "Recommendation — reviewer waits for green CI"): indent `skip-if-check-failing:` under `on:`; show `add-comment:` under `safe-outputs:`. (GHAW_PROPOSED already correct.)
- Optional: mention `assign-to-agent:` as the purpose-built handoff (vs `assignees:[copilot]`).
- NeMo snippet simplification is fine; no change required.
