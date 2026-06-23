<!-- markdownlint-disable-file -->
# Fact-Check: Renovate in Microsoft OSS — re-verification 2026-06-22

Verdict: 5/7 PASS, 1 PARTIAL FAIL, 1 UNCERTAIN. Headline narrative (Dependabot-dominant; Renovate niche ~19 microsoft repos) is accurate.

| # | Claim | Verdict | Note / Correction |
|---|---|---|---|
| 1 | `microsoft/vs-renovate-presets` exists; ≥3 VS-team repos reference it | PASS | repo confirmed; CsWin32, vs-threading, vs-streamjsonrpc, vs-validation, vs-mef verified (extends `github>microsoft/vs-renovate-presets:microbuild`) |
| 2 | Named Renovate configs real (ebpf-for-windows, component-detection, rnx-kit, CsWin32, vs-threading) | PASS | all real; ebpf-for-windows = root + config:recommended ✓; rnx-kit/CsWin32/vs-threading at `.github/renovate.json` |
| 3 | Flagships use Dependabot not Renovate | PASS | vscode/TypeScript/aspnetcore/github-docs ✓ Dependabot. Nuance: dotnet/runtime also has a narrow `eng/renovate.json` (Docker-digest pinning only) |
| 4 | ~19 microsoft repos; Dependabot >> Renovate | PASS | Sourcegraph exhaustive: 21 paths − 2 vendor/fixture = **19 real** ✓ exact |
| 5 | Azure:1, dotnet:1, github:0 | **PARTIAL FAIL** | Azure:1 ✓ (AgentBaker); github:0 ✓; **dotnet is ~9, NOT 1** (runtime, arcade, dotnet, dotnet-operator-sdk, dotnet-buildtools-prereqs-docker, nbgv, Nerdbank.GitVersioning, docker-tools, Nerdbank.Streams) |
| 6 | OSPO promotes Dependabot, no Renovate | UNCERTAIN | OSPO page implies Dependabot via "built-in dependency update PR capabilities" but does NOT name it; Renovate absent. Soften to "GitHub-native dep features only (no Renovate mention)" |
| 7 | `renovatebot/github-action` = self-hosted, no Mend App | PASS | README: "run Renovate self-hosted"; PAT-based; no App approval |

## Actions for the deck
- **FIX** `RENOVATE_ADOPTION` (gen_content.py): `dotnet: 1` → `dotnet: ~9`.
- Soften OSPO line: "OSPO: GitHub-native dependency features only (no Renovate mention)".
- (Optional) note dotnet/runtime uses both Dependabot (primary) + narrow Renovate.
