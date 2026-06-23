# PR Regression Safety Primer

Slide-ready tutorial content for CI/CD generalists. Use these units before the analysis section to establish shared vocabulary for dependency, security, and untrusted-code gates.

## 1. Dependabot mechanics

Dependabot has two streams. Version updates run on the schedule in `.github/dependabot.yml` and keep old-but-not-vulnerable dependencies current. Security updates are triggered by Dependabot alerts and security advisories, not by the weekly schedule. By default, Dependabot opens one PR per dependency update; `groups:` batches matching dependencies into one PR, `ignore:` suppresses known-bad ranges or deliberate pins, `open-pull-requests-limit` caps version-update noise, and `cooldown` delays new version updates for a stability window. Security updates are separate and should not be delayed by cooldown because the documented cooldown option applies only to version updates. Dependabot supports the repo's `uv` ecosystem and updates manifests and lockfiles as part of its native package-manager flow. Confidence: high.

```yaml
updates:
  - package-ecosystem: uv
    directory: /training/il/lerobot
    groups:
      lerobot-dependencies:
        patterns: ["*"]
    ignore:
      - dependency-name: torch
        versions: [">=2.11.0"]
    open-pull-requests-limit: 5
```

Key terms: version update, security update, group, ignore, cooldown, open PR limit, manifest, lockfile.

Sources: `.github/dependabot.yml:72-101`, `.github/dependabot.yml:223-240`; GitHub Dependabot pull requests: <https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-pull-requests>; Dependabot options reference: <https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference>; supported ecosystems: <https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories>.

## 2. uv and lockfiles

`pyproject.toml` is the human-authored project manifest; in Python packaging, PEP 621 puts project metadata and direct dependencies under `[project]`, including `requires-python` and `dependencies`. `uv.lock` is the resolver output: exact package versions, sources, hashes, wheels, platform markers, and dependency edges. A green resolve means the solver can still produce a coherent dependency graph for the target Python and platform; that matters because a PR can update a manifest but forget the lockfile, leaving CI or production to install a different graph. This repo prevents that drift with `uv lock --check`, wired into PR validation as the `uv Lock Consistency` gate. Confidence: high.

```toml
[project]
requires-python = ">=3.12"
dependencies = [
  "lerobot==0.5.1",
  "huggingface-hub==1.19.0",
]

# CI: uv --directory <project> lock --check
```

Key terms: `pyproject.toml`, PEP 621, direct dependency, transitive dependency, `uv.lock`, resolver, hash, lock drift, green resolve.

Sources: `training/il/lerobot/pyproject.toml:1-12`, `training/il/lerobot/pyproject.toml:64-75`, `training/il/lerobot/uv.lock:1-25`, `training/il/lerobot/uv.lock:27-43`, `scripts/linting/Invoke-UvLockConsistencyCheck.ps1:7-15`, `scripts/linting/Invoke-UvLockConsistencyCheck.ps1:85-104`, `.github/workflows/uv-lock-consistency.yml:37-52`, `.github/workflows/pr-validation.yml:317-325`.

## 3. GHSA and security advisories

GHSA means GitHub Security Advisory. A GHSA entry records a vulnerable package, affected versions, patched versions, severity, and often a CVE link. Dependabot alerts and security-update PRs are driven by these advisories: when a vulnerable dependency appears in the dependency graph and a patch is available, Dependabot tries to open a PR to the minimum patched version. Severity comes from CVSS levels such as low, medium/moderate, high, and critical; it tells the CI/CD owner how much exposure the old dependency carries. Security PRs should not wait for weekly batching or stability windows because they close known exposure, and this repo treats them specially by retitling Dependabot PRs with security metadata as `security(...)`. Confidence: high.

```text
GHSA-xxxx-xxxx-xxxx
package: urllib3
vulnerable: < 2.7.0
patched: >= 2.7.0
severity: high
PR: bump to minimum patched version
```

Key terms: GHSA, GitHub Advisory Database, CVE, CVSS, severity, Dependabot alert, patched version, vulnerable range.

Sources: `training/il/lerobot/pyproject.toml:45-48`, `training/rl/pyproject.toml:36-39`, `.github/workflows/dependency-review.yml:24-43`, `.github/workflows/dependabot-security-prefix.yml:22-40`; GitHub Advisory Database: <https://docs.github.com/en/code-security/concepts/vulnerability-reporting-and-management/github-advisory-database>; Dependabot security updates: <https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-security-updates>.

## 4. CI gating tiers

CI should have tiers. Cheap checks run on every PR because they are fast and catch broad mistakes: spelling, lint, formatting, dependency review, lock consistency, and static security scans. Expensive checks run only when their code area changed or when a human releases secrets or scarce infrastructure. This repo implements path-aware job gating inside the workflow: one `changes` job computes booleans, selected jobs run with `if:`, and a single `pr-validation-summary` aggregates all required results so branch protection can require one stable check name. The trap is a naive top-level `paths:` filter: the whole workflow may be skipped or left pending, and if branch protection is not wired exactly, a PR can appear green without the intended tests. Keep the required check stable and make skipped work explicit. Confidence: high.

```yaml
jobs:
  changes:
    outputs:
      training: ${{ steps.filter.outputs.training }}
  pytest-training:
    needs: changes
    if: needs.changes.outputs.training == 'true'
  pr-validation-summary:
    if: always()
```

Key terms: cheap check, expensive check, path gate, required check, branch protection, status check, skipped job, aggregator.

Sources: `.github/workflows/pr-validation.yml:16-61`, `.github/workflows/pr-validation.yml:143-189`, `.github/workflows/pr-validation.yml:191-239`, `.github/workflows/pr-validation.yml:317-325`, `.github/workflows/pr-validation.yml:420-478`, `.github/workflows/main.yml:89-178`; GitHub workflow syntax path-filter behavior: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax>; protected branches and required checks: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches>.

## 5. Running untrusted PR code safely

A fork PR is untrusted code. On `pull_request`, GitHub runs the workflow on the PR merge ref; for forked PRs, secrets are not passed and `GITHUB_TOKEN` is read-only. On `pull_request_target`, GitHub runs in the base repository context; it can access write permissions and secrets, so checking out and executing the PR head is the classic "pwn request" failure. Use `pull_request` for building untrusted code. Use `pull_request_target` only for safe metadata tasks such as labeling or commenting. When a job needs cloud access or deployment secrets, put it behind a GitHub Environment with required reviewers; a job referencing an environment must satisfy protection rules before it can run or access environment secrets. Prefer OIDC over stored cloud secrets: `id-token: write` lets the job request a short-lived identity token and `azure/login` exchanges it for a cloud token. Confidence: high.

```yaml
permissions:
  contents: read
  id-token: write
jobs:
  smoke:
    environment: gpu-smoke-approved
    runs-on: ubuntu-latest
    steps:
      - uses: azure/login@8c334a195cbb38e46038007b304988d888bf676a
```

Key terms: untrusted code, fork PR, `pull_request`, `pull_request_target`, `GITHUB_TOKEN`, secret, GitHub Environment, required reviewer, OIDC, federated credential.

Sources: `.github/workflows/pr-validation.yml:3-14`, `.github/workflows/pr-validation.yml:33-38`, `.github/workflows/dependabot-security-prefix.yml:3-19`, `.github/workflows/aw-dependabot-pr-review.lock.yml:60-83`; GitHub PR events: <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows>; GitHub Environments: <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>; GitHub OIDC concepts: <https://docs.github.com/en/actions/concepts/security/openid-connect>; Azure OIDC workflow example: <https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-azure>.

## 6. gh-aw and agentic workflows

gh-aw and agentic Dependabot review are covered in their own section; this primer only names them so readers know the workflow exists. Confidence: high.

```yaml
name: AW Dependabot PR Review
on:
  issue_comment:
    types: [created, edited]
```

Key terms: gh-aw, agentic workflow, advisory review, slash command.

Sources: `.github/workflows/aw-dependabot-pr-review.lock.yml:20-27`, `.github/workflows/aw-dependabot-pr-review.lock.yml:60-83`.

## Consolidated glossary

| Term | One-line definition |
| --- | --- |
| ABI | Application Binary Interface: the compiled-code contract between libraries and runtimes; an ABI mismatch can crash even when source code imports succeed. |
| Branch protection | GitHub rules that restrict merging or pushing to a branch until configured requirements, such as reviews or checks, pass. |
| CVSS | Common Vulnerability Scoring System: a standard severity scale used to classify vulnerabilities as low, medium/moderate, high, or critical. |
| Dependabot | GitHub's dependency bot that opens PRs for outdated or vulnerable dependencies. |
| e2e | End-to-end test: a test that exercises a complete user or system flow across multiple components. |
| GHSA | GitHub Security Advisory identifier and record for a known vulnerability or malicious package. |
| GitHub Environment | A named deployment target in GitHub Actions that can require reviewers, wait timers, branch restrictions, and environment-scoped secrets. |
| GPU runtime | The driver, CUDA/Vulkan libraries, container hooks, and device plugins that let CI jobs use GPU hardware. |
| Lockfile | A generated file that pins the exact resolved dependency graph, usually including versions, sources, hashes, and platform markers. |
| OIDC | OpenID Connect: a federated identity flow where CI exchanges a short-lived GitHub token for a cloud token instead of storing cloud credentials. |
| PEP 621 | The Python packaging standard that defines project metadata, including dependencies, in `[project]` inside `pyproject.toml`. |
| `pull_request` vs `pull_request_target` | `pull_request` runs PR code with fork-safe restrictions; `pull_request_target` runs in base-repo context and must not execute untrusted PR head code. |
| Renovate | A third-party dependency update bot with configuration and grouping features similar in purpose to Dependabot. |
| Required check | A status check that branch protection requires to pass, be skipped, or be neutral before merge. |
| Self-hosted runner | A GitHub Actions runner operated by the repository owner rather than GitHub, often used for private networks, GPUs, or custom hardware. |
| Semver patch/minor/major | Semantic versioning levels: patch fixes within `x.y.z`, minor adds compatible features, major may break compatibility. |
| Smoke test | A small, fast test that proves the system starts and the most critical path works. |
| uv | A fast Python package manager and resolver that reads `pyproject.toml` and writes `uv.lock`. |
