<!-- markdownlint-disable-file -->
# Subagent D: Gated GPU E2E + GPU-free Smoke + CI Security for Untrusted PR Code

Captured by parent (research agent is read-only). Findings + citations.

## 1. Manual approval gate on an expensive CI job

GitHub Actions **Environments with required reviewers** (deployment protection rules) are the human gate. A job declares `environment: <name>`; the run pauses until a designated reviewer clicks **Approve**, which also releases that environment's secrets. Combine with `workflow_dispatch` and/or `pull_request` + environment approval.

Sketch:

```yaml
jobs:
  smoke:           # cheap, always runs
    runs-on: ubuntu-latest
    steps: [ ... ]
  e2e-gpu:         # expensive, gated
    needs: smoke
    environment: e2e-approval   # required-reviewers gate; releases Azure OIDC perms
    runs-on: ubuntu-latest
    steps:
      - uses: azure/login@v2     # OIDC, no stored secret
      - run: az ml job create -f e2e/job.yml --stream  # runs on scale-from-zero GPU pool
```

Cite: GitHub Docs "Managing environments for deployment" / "required reviewers" / "Reviewing deployments".

## 2. Security: `pull_request` vs `pull_request_target`

* `pull_request` (forks): read-only `GITHUB_TOKEN`, **no repo secrets** by default — safe default for running untrusted code.
* `pull_request_target`: write token + secrets, but runs workflow defs from the **base** branch. The "pwn request" vuln appears when it explicitly checks out PR head (`ref: github.event.pull_request.head.sha`) and then builds/tests — attacker-controlled code (incl. dependency build scripts) executes **with secrets**.
* GitHub-recommended safe patterns: (a) **label-gated** `pull_request_target` where a maintainer adds an approval label before the privileged run; (b) **two-workflow** split — untrusted code runs in unprivileged `pull_request`, uploads artifacts; a privileged `workflow_run` consumes artifacts with secrets. Environment approval gates further ensure secrets release only after human review.
* First-time-contributor fork PRs already require manual "Approve and run workflows".

Do/Don't for an e2e job needing cloud creds: never `pull_request_target` + PR-head checkout + secrets without a human gate; prefer **submit-and-poll** so PR code runs inside the AML/OSMO job sandbox, not on the runner.

Cite: GitHub Security Lab "Preventing pwn requests"; GitHub Docs "Securely using pull_request_target"; "Approving workflow runs from public forks".

## 3. Reuse scale-from-zero AML/OSMO as the e2e engine

Two shapes:
* (a) **Submit-and-poll (RECOMMENDED, safer)**: runner authenticates to Azure via **OIDC workload-identity federation** (no long-lived secret), runs `az ml job create` / `osmo` workflow against a GPU pool that autoscales from 0, polls, surfaces pass/fail as the check. PR code executes inside the AML/OSMO sandbox; the runner only orchestrates.
* (b) **Self-hosted GPU runner on AKS** (e.g. Actions Runner Controller, ephemeral pods): cheaper per-run but exposes the runner to PR code — mitigate with ephemeral pods + K8s RBAC + network policy; higher risk.

Cite: Azure "Configure OIDC / workload identity federation for GitHub Actions"; `az ml job create` reference.

## 4. Cost/safety controls for the GPU tier

Run only on manual approval/label; scale-to-zero → idle cost ≈ $0; concurrency-cancel superseded runs; per-job timeout caps; restrict to non-fork or post-approval; budget enforced via the gated environment.

## 5. GPU-free smoke tier (the "do it now, no subscription" layer)

Cheap checks on standard runners and the breakage class each catches:

| Smoke check | Catches |
|---|---|
| `uv lock --check` / `uv sync` resolve | dependency resolution conflicts (the lock-desync class) |
| Python import smoke (`python -c "import lerobot, torch, ..."`), entrypoint `--help`, `--config-preview` | ABI / import-time breaks, removed modules |
| CPU-only minimal train/eval step on a tiny synthetic dataset | API breaks in training/eval call paths |
| Container image BUILD smoke after a bump | image no longer builds (system/python dep break) |
| terraform `validate`/`plan`, go output-contract, fuzz-regression, frontend `npm run validate` | infra/contract/UI regressions |
| **GPU-only runtime break (CUDA/Isaac Vulkan/MIG)** | **only the gated GPU e2e tier catches this** |

Recommended layering: cheap smoke auto-runs on every PR → heavy GPU e2e only on manual approval/label.

## Blocking clarifying questions raised by D

1. Until a GPU subscription is funded, what is the no-GPU tier's target: (a) public-contributor PRs never run GPU e2e, (b) maintainer manual run in a dev subscription, or (c) hybrid fallback?
2. Risk tolerance for a self-hosted GPU runner executing PR code (vs mandating AML/OSMO sandbox-only execution)?
3. Should the gate be stricter for fork PRs (always human label) vs collaborator PRs (approval gate only)?
