<!-- markdownlint-disable-file -->
# Fact-Check: External OSS practice claims — 2026-06-22

Verdict: **all 10 claims PASS**; three snippet/wording corrections. All sources fetched live 2026-06-22.

| # | Claim | Verdict | Notes / Correction |
|---|---|---|---|
| 1 | LeRobot: fast CPU tests every PR; GPU tests only on approval, never forks | PASS | `fast_tests.yml` on `pull_request` (CPU). `full_tests.yml` `gpu-tests` needs `build-and-push-docker` which is gated `review approved && head.repo.fork == false`. Nuance: the CPU `full-tests` job lacks the fork check; GPU tier is correctly fork-gated. |
| 2 | HF transformers: 7-day Dependabot cooldown | PASS (scope nuance) | `cooldown: {default-days: 7}` is real — but **only on the `github-actions` ecosystem**; transformers' dependabot.yml has NO Python entry. Don't imply a Python-dep cooldown; the basis for our rec is the documented feature itself. |
| 3 | cheerio: auto-merge via dependabot/fetch-metadata + `gh pr merge --auto` | PASS (FIX snippet) | Real. **Correction:** merges `semver-minor OR semver-patch` (our `C_AUTOMERGE` shows patch-only) and triggers on `pull_request_target`. |
| 4 | vercel/ai: gold-standard multi-group dependabot.yml, ~npm-only, migrated FROM Renovate | PASS | Header: "migrated from .github/renovate.json5". Ecosystems: npm + github-actions only (no Python/uv/terraform) — fair contrast. |
| 5 | Dependabot `cooldown` real (2025+); `uv` ecosystem supported; PEP 621 `[project]` deps | PASS | `cooldown` documented (version-updates only, not security); `uv` in supported package-manager table. Exact GA-date changelog pages 404'd — feature support itself confirmed. |
| 6 | GitHub Environments: required reviewers pause job + release secrets; ≤6 reviewers; prevent self-review | PASS | All three confirmed verbatim in GitHub docs. |
| 7 | `pull_request` fork = read-only, no secrets; `pull_request_target` = base context w/ secrets → pwn request | PASS | Confirmed verbatim (GitHub Security Lab). |
| 8 | OIDC: `id-token: write` → short-lived token, `azure/login` exchanges, no stored secret | PASS | Confirmed (GitHub OIDC-in-Azure docs). |
| 9 | Renovate: `config:best-practices`, `minimumReleaseAge`, `pep621` manager (pyproject+uv.lock), `renovatebot/github-action` (no Mend App) | PASS | All confirmed. `config:best-practices` even bundles `security:minimumReleaseAgeNpm` (3 days). github-action runs Renovate self-hosted via PAT. |
| 10 | vercel/ai (npm-only) left Renovate "for simplicity" — fair non-counterexample | PASS | Single-ecosystem npm; genuinely different from this multi-ecosystem Python repo. |

## Actions for the deck
- **Fix `C_AUTOMERGE`** (gen_content.py): cheerio merges `semver-minor || semver-patch` and uses `pull_request_target`. Either match cheerio (minor+patch) or relabel the snippet as *our* patch-only choice rather than "the cheerio pattern".
- **Soften HF cooldown wording**: the 7-day cooldown example is on github-actions; cite the Dependabot `cooldown` feature as the basis for applying it to our Python deps.
- LeRobot framing fine (GPU tier is fork-gated).

Evidence SHAs: lerobot fast_tests b6680db, full_tests c672689; transformers dependabot 15f7bdd; cheerio automerge dd077db; vercel/ai dependabot 68e1e7e. Docs: GitHub dependabot-options-reference, environments, oidc-in-azure, securitylab pwn-requests; docs.renovatebot.com presets/minimumReleaseAge/pep621; github.com/renovatebot/github-action.
