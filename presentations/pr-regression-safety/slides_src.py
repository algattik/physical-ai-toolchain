"""Generate the full research presentation content/ tree + narration files.
Dark GitHub-style theme. Slide kinds: title, section, bullets, stat, twocol."""
from __future__ import annotations

from pathlib import Path

import yaml

FONT = "Arial"
BG = "#0D1117"
TEXT = "#E6EDF3"
MUTED = "#8B949E"
BODY = "#D0D8E0"
BLUE = "#2F81F7"
GREEN = "#3FB950"
RED = "#F85149"
AMBER = "#D29922"
PURPLE = "#A371F7"

W, H = 13.333, 7.5
ML = 0.9
CW = W - 2 * ML


def tb(left, top, width, height, text, size, color, bold=False, align="left"):
    return {"type": "textbox", "left": left, "top": top, "width": width, "height": height,
            "text": text, "font": FONT, "font_size": size, "font_color": color,
            "font_bold": bold, "alignment": align}


def rect(left, top, width, height, fill):
    return {"type": "shape", "shape": "rectangle", "left": left, "top": top,
            "width": width, "height": height, "fill": fill}


def footer(idx, total):
    return [rect(ML, 6.86, CW, 0.02, "#262E36"),
            tb(ML, 6.95, 9.0, 0.4, "Physical AI Toolchain  ·  PR Regression Safety", 11, MUTED),
            tb(W - ML - 1.6, 6.95, 1.6, 0.4, f"{idx} / {total}", 11, MUTED, align="right")]


def topbar(accent):
    return [rect(0, 0, W, 0.16, accent)]


def heading(title, accent):
    return [rect(ML, 0.66, 0.12, 0.82, accent),
            tb(ML + 0.32, 0.6, CW - 0.32, 1.0, title, 30, TEXT, bold=True),
            rect(ML, 1.62, CW, 0.018, "#262E36")]


def render_title(s, idx, total):
    el = topbar(BLUE) + [rect(0, 0, 0.16, H, BLUE)]
    el.append(tb(ML, 2.4, CW, 1.7, s["title"], 54, TEXT, bold=True))
    el.append(rect(ML, 4.08, 4.3, 0.06, BLUE))
    el.append(tb(ML, 4.35, CW, 0.8, s["subtitle"], 26, MUTED))
    el.append(tb(ML, 6.4, CW, 0.5, s["sub2"], 17, MUTED))
    return el


def render_section(s, idx, total):
    accent = s.get("accent", BLUE)
    el = topbar(accent) + [rect(0, 0, 0.16, H, accent)]
    el.append(tb(ML, 2.6, CW, 0.7, s["part"], 26, accent, bold=True))
    el.append(tb(ML, 3.25, CW, 1.5, s["title"], 46, TEXT, bold=True))
    el.append(rect(ML, 4.95, 5.2, 0.05, accent))
    if s.get("sub"):
        el.append(tb(ML, 5.15, CW, 0.8, s["sub"], 20, MUTED))
    return el


def render_bullets(s, idx, total):
    accent = s["accent"]
    el = topbar(accent) + heading(s["title"], accent)
    el.append(tb(ML, 1.95, CW, 4.7, s["body"], s.get("body_size", 21), BODY))
    el += footer(idx, total)
    return el


def render_stat(s, idx, total):
    accent = s["accent"]
    el = topbar(accent) + heading(s["title"], accent)
    el.append(tb(ML - 0.05, 1.9, CW, 1.6, s["stat"], 80, accent, bold=True))
    el.append(tb(ML, 3.6, CW, 0.9, s["statcap"], 22, TEXT))
    el.append(tb(ML, 4.6, CW, 2.1, s["body"], s.get("body_size", 20), BODY))
    el += footer(idx, total)
    return el


def render_twocol(s, idx, total):
    accent = s["accent"]
    el = topbar(accent) + heading(s["title"], accent)
    gap = 0.6
    colw = (CW - gap) / 2
    lx = ML
    rx = ML + colw + gap
    la = s.get("left_accent", accent)
    ra = s.get("right_accent", accent)
    el.append(tb(lx, 1.95, colw, 0.5, s["left_head"], 23, la, bold=True))
    el.append(tb(lx, 2.55, colw, 4.1, s["left_body"], s.get("body_size", 19), BODY))
    el.append(rect(ML + colw + gap / 2 - 0.008, 2.0, 0.016, 4.4, "#262E36"))
    el.append(tb(rx, 1.95, colw, 0.5, s["right_head"], 23, ra, bold=True))
    el.append(tb(rx, 2.55, colw, 4.1, s["right_body"], s.get("body_size", 19), BODY))
    el += footer(idx, total)
    return el


def render_phases(s, idx, total):
    accent = s.get("accent", BLUE)
    el = topbar(accent) + heading(s["title"], accent)
    phases = s["phases"]
    n = len(phases)
    top, rowh = 1.95, 0.86
    gap = max((4.74 - n * rowh) / (n - 1), 0.08) if n > 1 else 0.0
    for i, p in enumerate(phases):
        y = top + i * (rowh + gap)
        pa = p.get("accent", accent)
        cx, cw = ML + 2.34, CW - 2.34 - 1.65
        el.append(rect(ML, y, CW, rowh, "#161B22"))
        el.append(rect(ML, y, 0.10, rowh, pa))
        el.append(tb(ML + 0.30, y + 0.12, 1.78, 0.4, p["tag"], 17, pa, bold=True))
        el.append(tb(ML + 0.30, y + 0.50, 1.9, 0.3, p["when"], 11, MUTED))
        el.append(rect(ML + 2.12, y + 0.16, 0.014, rowh - 0.32, "#2A323B"))
        el.append(tb(cx, y + 0.12, cw, 0.4, p["head"], 16.5, TEXT, bold=True))
        el.append(tb(cx, y + 0.50, cw, 0.3, p["items"], 12, BODY))
        el.append(tb(W - ML - 1.6, y + 0.25, 1.52, 0.4, p["cost"], 15, pa, bold=True, align="right"))
    el += footer(idx, total)
    return el


RENDER = {"title": render_title, "section": render_section, "bullets": render_bullets,
          "stat": render_stat, "twocol": render_twocol, "phases": render_phases}


SLIDES = [
    {"kind": "title", "title": "PR Regression Safety",
     "subtitle": "Intelligent dependency updates & gated end-to-end testing",
     "sub2": "Full research findings  ·  microsoft/physical-ai-toolchain  ·  June 2026",
     "notes": "Welcome. This is the full research findings on reducing pull request regressions in the physical A-I toolchain. We will cover the evidence, the dependency-update problem and its remedies, agentic workflows, testing and security, what comparable open-source projects do, and a sequenced recommendation. The throughline is open-source quality and security."},

    {"kind": "bullets", "accent": BLUE, "title": "What this covers",
     "body": "- The problem, in evidence — churn numbers and a catalogue of real regressions\n- Intelligent dependency updates — grouping, Renovate, and an agentic triage layer\n- Agentic workflows — what gh-aw can really do, and how to orchestrate it\n- Testing and security — a layered gate, and running untrusted PR code safely\n- What other open-source projects do — proven patterns to copy\n- A sequenced recommendation — what ships now, what waits on funding",
     "notes": "Here is the shape of the talk. First, the evidence — how noisy dependency updates are, and a catalogue of regressions reconstructed from the project's own history. Then the dependency-update remedies. Then agentic workflows and orchestration. Then testing and security. Then a benchmark of comparable projects. And finally, a recommendation ordered by cost and funding."},

    {"kind": "bullets", "accent": BLUE, "title": "The mandate & method",
     "body": "- Question posed by the maintainers: \"solve dependabot at the root, and gate safe merges\"\n- Six parallel research threads, each writing a cited evidence file:\n-   repo & CI state · dependency intelligence · gh-aw capabilities\n-   gated GPU e2e & security · issue / PR history · open-source benchmark\n- Grounded in the repo's own git history, configs, and primary upstream sources",
     "notes": "The mandate came directly from the maintainers: solve the dependency problem at its root, and find a way to gate genuinely safe merges. The method was six parallel research threads, each producing a cited evidence file — covering the current state of the repository, dependency intelligence, agentic-workflow capabilities, gated G-P-U testing and its security, the project's own issue and pull request history, and a benchmark of other open-source projects. Everything is grounded in primary evidence."},

    {"kind": "section", "accent": RED, "part": "Part 1", "title": "The problem, in evidence",
     "sub": "Why regressions are constant — and why green CI doesn't see them",
     "notes": "Part one. The problem, in evidence. The claim that regressions are constant is not rhetorical — the history proves it, and it reveals why a green pipeline keeps missing them."},

    {"kind": "bullets", "accent": RED, "title": "Two problems, one root",
     "body": "- Dependency intake is blind — single-package PRs with no notion of risk\n- There is no end-to-end gate — \"safe to merge\" cannot actually be asserted\n- Both feed the same outcome: regressions land on the main branch\n- A dedicated GPU subscription is the funding blocker for true end-to-end testing",
     "notes": "There are two problems, but one root. Dependency intake is blind — updates arrive as single-package pull requests with no sense of risk. And there is no end-to-end gate, so 'safe to merge' cannot actually be asserted. Both feed the same outcome: regressions reach the main branch. The honest blocker for true end-to-end testing is funding for G-P-U compute."},

    {"kind": "stat", "accent": RED, "title": "Dependency churn",
     "stat": "~24 / week",
     "statcap": "Dependabot pull requests, and accelerating — ~350 opened all-time (~216 merged); multiple days saw six-plus merged.",
     "body": "- ~24 / week all-time average, rising to ~28 / week over the last six weeks\n- Every PR triggers the full pipeline; the AI reviewer spends tokens on each rebase\n- No risk awareness: a harmless patch and a CUDA-breaking major look identical",
     "notes": "Start with volume. Around three hundred and fifty dependency pull requests opened to date, about two hundred and sixteen merged — roughly twenty-four a week on average, rising to twenty-eight over the last six weeks, with several days seeing six or more merged. Every one runs the full pipeline, and the A-I reviewer spends tokens on each rebase. Crucially, none of them carries any notion of risk: a harmless patch and a CUDA-breaking major version look exactly the same."},

    {"kind": "stat", "accent": AMBER, "title": "The regressions that hurt are invisible to CI",
     "stat": "8  vs  0",
     "statcap": "Eight regressions & test-integrity gaps reconstructed from history — zero caught by green CPU CI.",
     "body": "- Most are runtime, GPU, or interpreter specific — exactly what CPU CI cannot exercise\n- Two were caused by CI itself: path-filter bugs silently switched tests off for weeks\n- A green check, in this project, has repeatedly meant \"nothing was actually tested\"",
     "notes": "Now the central insight. Eight distinct regressions and test-integrity gaps were reconstructed from the project's history, and not one was caught by the green, CPU-only pipeline. Most are runtime, G-P-U, or interpreter specific — precisely what CPU continuous-integration cannot exercise. Worse, two were caused by the pipeline itself: path-filter bugs that silently switched tests off for weeks. A green check has repeatedly meant nothing was actually tested."},

    {"kind": "bullets", "accent": AMBER, "title": "Incident catalogue — runtime & dependency drift",
     "body_size": 20,
     "body": "- #809 — RL locks resolved for Python 3.12 vs a 3.11.9 runtime → four cascading ABI failures; a dep PR also dropped azureml-mlflow\n- #790 — LeRobot needs Python ≥ 3.12 vs an OSMO 3.11.9 runtime\n- #958 / 36ba1ba — a torch 2.10→2.11 security bump pulled CUDA 13 bindings → libcudart break\n-   and it is a LIVE desync today: the lock pins 2.10, but CI force-installs 2.11",
     "notes": "Here is the first half of the catalogue. Issue eight-oh-nine: reinforcement-learning locks were resolved against Python three-point-twelve while the Isaac runtime is three-eleven-point-nine — four cascading A-B-I failures, and in the same fix a dependency pull request dropped azure-m-l-flow. Issue seven-ninety: LeRobot requires Python three-twelve against an OSMO three-eleven runtime. And pull request nine-fifty-eight: a torch security bump pulled in CUDA-thirteen bindings and broke the CUDA runtime library. That one is a live desync today — the lock pins two-point-ten, but the pipeline force-installs two-point-eleven."},

    {"kind": "bullets", "accent": AMBER, "title": "Incident catalogue — CI integrity & churn",
     "body_size": 20,
     "body": "- #691 — a malformed path-filter regex silently disabled the fuzz tests for weeks\n- #547 — a folder restructure silently disabled data-pipeline and training tests\n- The AI dependabot reviewer itself shipped with six consecutive bugs\n- starlette bumped 0.52→1.0→1.3 within ~11 days — three churning security PRs",
     "notes": "The second half. Issue six-ninety-one: a malformed path-filter expression silently disabled the fuzz tests for weeks. Issue five-forty-seven: a folder restructure did the same to the data-pipeline and training tests. The automated reviewer itself shipped with six consecutive bugs. And the churn shows up plainly — starlette was bumped from zero-point-five-two to one-point-three in about eleven days, three churning security pull requests. The pattern is integrity gaps and noise, on top of the runtime breaks."},

    {"kind": "bullets", "accent": BLUE, "title": "So: this is open-source quality + security",
     "body": "- Supply-chain hygiene — batch low-risk, fast-track security, isolate high-risk\n- CI integrity — fail-safe required checks; no silently skipped tests\n- Safe execution — OIDC and environment gates; never run untrusted PR code with secrets\n- Adopt it incrementally — each fix stands alone; no all-or-nothing rollout",
     "notes": "Framed correctly, this is open-source quality and security, on three axes. Supply-chain hygiene — batching the low-risk, fast-tracking security, isolating the high-risk. Continuous-integration integrity — fail-safe required checks, and never a silently skipped test. And safe execution — OIDC and environment gates, so untrusted contributor code never runs with secrets. And you can adopt all of this incrementally — each fix stands alone, with no all-or-nothing rollout."},

    {"kind": "section", "accent": GREEN, "part": "Part 2", "title": "Intelligent dependency updates",
     "sub": "From blind single-package PRs to risk-aware intake",
     "notes": "Part two. Intelligent dependency updates — moving from blind, single-package pull requests to risk-aware intake."},

    {"kind": "bullets", "accent": BLUE, "title": "Dependabot today",
     "body": "- ~17–20 ecosystem blocks: npm, ~10 uv/Python subprojects, Terraform, Go, Docker\n- Grouping IS used — but as wildcard catch-all groups, not split by risk\n- ~7 ignore-pins added reactively after breakages (torch, numpy, marshmallow, …)\n- Nine committed uv.lock files, guarded by a read-only `uv lock --check` gate",
     "notes": "Where the project stands today. Dependabot watches roughly seventeen to twenty ecosystem blocks — npm, about ten Python subprojects via u-v, Terraform, Go, and Docker. Grouping is already used, but as wildcard catch-all groups, not split by risk. Around seven ignore-pins were added reactively after things broke. And nine committed lockfiles are guarded by a read-only lock-consistency check."},

    {"kind": "bullets", "accent": GREEN, "title": "Native grouping: the immediate win",
     "body": "- Split update-types: batch patch + minor into one PR; isolate majors for review\n- Group dev-dependencies and GitHub-Actions digests separately\n- Add `cooldown` — a stability window before a bump opens (a documented Dependabot option)\n- Keep security updates ungrouped and fast-tracked; keep the existing ignore-pins\n- Cost: zero code. It is a dependabot.yml change.",
     "notes": "The immediate win needs no code at all. Split the update types — batch patch and minor into a single pull request per ecosystem, and isolate major versions for human review. Group developer dependencies and GitHub-Actions digests separately. Add a cooldown — a stability window before a bump opens; HuggingFace uses seven days. Keep security updates ungrouped and fast-tracked. This is purely a configuration change."},

    {"kind": "bullets", "accent": AMBER, "title": "What native grouping doesn't solve",
     "body": "- Cross-ecosystem grouping — Dependabot groups are per-ecosystem; you still get 4+ PRs\n- Risk classification beyond semver — \"this major is safe, that one breaks CUDA\"\n- Severity routing — a CVSS-9 should page; a CVSS-4 can auto-merge\n- Auto-merge — Dependabot cannot merge its own PRs; that needs an Actions layer",
     "notes": "But native grouping has limits — and these define the gap an intelligent layer fills. It cannot group across ecosystems, so you still get four or more pull requests per cycle. It cannot classify risk beyond semantic versioning — it does not know that this major is safe and that one breaks CUDA. It cannot route by severity. And it cannot merge its own pull requests; that requires an Actions or agentic layer."},

    {"kind": "twocol", "accent": BLUE, "title": "Renovate vs Dependabot",
     "left_head": "Renovate — one config, all ecosystems", "left_accent": GREEN,
     "left_body": "- Cross-ecosystem grouping: npm + uv + terraform + go in ONE PR\n- One renovate.json vs ~20 separate dependabot blocks\n- Native automerge + a Dependency Dashboard\n- minimumReleaseAge stability windows\n- pep621 / uv too — but Dependabot now supports uv as well",
     "right_head": "…cost is organizational, not engineering", "right_accent": AMBER,
     "right_body": "- Migration is mechanical — AI-assisted; Renovate auto-onboards\n- Mend App needs org approval — BUT renovatebot/github-action avoids it\n- Microsoft OSS reality: Dependabot-dominant; Renovate ~19 repos (niche)\n- So: a scoped spike on merit, not an all-or-nothing switch",
     "notes": "How does Renovate compare? Its real edge is cross-ecosystem grouping: a single Renovate config can batch npm, u-v, terraform, and go updates into one pull request, instead of the twenty-odd separate Dependabot blocks. The often-cited pep621 and u-v advantage is now thinner: Dependabot has supported u-v since twenty-twenty-five, and this repo already uses it and regenerates the lock natively, so the case rests on grouping, not u-v. And the cost is not engineering: migration is mechanical and Renovate auto-onboards. We checked adoption directly — across Microsoft open source Dependabot dominates and Renovate is a niche minority of about nineteen repositories, so the third-party Mend app carries real approval friction; but running Renovate as a plain GitHub Action sidesteps that entirely. So this is a scoped spike decided on merit, not an all-or-nothing switch."},

    {"kind": "bullets", "accent": BLUE, "title": "An agentic triage layer",
     "body": "- Read open Dependabot PRs; classify high-impact vs low-impact\n-   high: majors, lockfile-wide changes, security severity, production deps\n-   low: patch, dev, docs, CI-action digests\n- Auto-merge low-impact on green CI; combine several into one batch\n- Escalate high-impact: hand a remediation issue to the Copilot coding agent",
     "notes": "On top of grouping sits the agentic layer the maintainers asked about. It reads the open dependency pull requests and classifies them. High-impact means majors, lockfile-wide changes, security severity, or production dependencies. Low-impact means patches, developer tools, documentation, and CI-action digests. The low-impact ones are auto-merged on green CI, or combined into a single batch. The high-impact ones are escalated — handed as a remediation issue to the Copilot coding agent."},

    {"kind": "bullets", "accent": RED, "title": "Security updates are never batched",
     "body": "- Security and version updates are separate Dependabot streams — keep it that way\n- Fast-track by severity; a high-CVSS advisory should not wait in a weekly batch\n- Batch and delay only routine version bumps\n- The uv.lock convention self-heals: Dependabot regenerates locks natively",
     "notes": "One firm rule: security updates are never batched. Dependabot keeps security and version updates as separate streams, and that separation must be preserved. Fast-track by severity — a high-score advisory should never sit in a weekly batch. Only routine version bumps get batched and delayed. And the lockfile convention helps here: Dependabot regenerates the locks natively, so version bumps largely self-heal."},

    {"kind": "section", "accent": PURPLE, "part": "Part 3", "title": "Agentic workflows & orchestration",
     "sub": "What gh-aw can really do — and who does the work",
     "notes": "Part three. Agentic workflows and orchestration — what GitHub's agentic workflows can really do, and how to divide the labour."},

    {"kind": "bullets", "accent": GREEN, "title": "gh-aw can do more than it's used for today",
     "body": "- Create pull requests directly — from a git patch, agent stays read-only\n- Wait for CI — trigger on workflow_run; skip-if-check-failing\n- Keep ONE updating comment — hide-older-comments / comment-memory\n- Produce a required check — create-check-run, name matched to branch protection\n- Hand work to Copilot — assign-to-agent on a structured issue",
     "notes": "Today the repository runs exactly one agentic workflow — an advisory Dependabot pull-request reviewer. Its capability surface is far broader than that single use. They can create pull requests directly from a git patch, while the agent itself stays read-only. They can wait for C-I, triggering only when it completes, and skipping when checks are failing. They can keep a single updating comment rather than spamming on every rebase. They can produce a required status check. And they can hand work to the Copilot coding agent."},

    {"kind": "bullets", "accent": BLUE, "title": "Fixing the AW reviewer's cost",
     "body": "- Today: a maintainer-only slash command — but it can run before CI concludes\n- Trigger on workflow_run when the PR pipeline completes successfully\n- skip-if-check-failing → never spend tokens on a PR that will deterministically fail\n- hide-older-comments → one tidy comment across rebases\n- Keep the slash command as an explicit manual override",
     "notes": "This directly answers the cost concern. Today the reviewer is a maintainer-only slash command, but it can be invoked before C-I concludes — wasting tokens when the pipeline will deterministically fail. The fix: trigger it when the pipeline completes successfully, skip it when checks are failing, and collapse its comments into one across rebases. Keep the slash command as an explicit manual override for when a maintainer wants it sooner."},

    {"kind": "bullets", "accent": BLUE, "title": "Orchestration: a decider and a doer",
     "body": "- gh-aw is the cheap, gated DECIDER — it triages and dispatches\n- The Copilot coding agent is the DOER — it opens a fix PR from a tagged issue\n- Pattern: triage → structured issue → assign-to-agent → PR → CI\n- Precedent: NVIDIA NeMo's gated \"babysitter\" runs exactly this human-approved loop",
     "notes": "The orchestration pattern keeps a clean division of labour. The agentic workflow is the cheap, gated decider — it triages and dispatches. The Copilot coding agent is the doer — it opens a fix pull request from a tagged issue. The flow is: triage, create a structured issue, assign the agent, get a pull request, run C-I. This is not speculative — NVIDIA's NeMo runs exactly this human-approved loop in production."},

    {"kind": "section", "accent": GREEN, "part": "Part 4", "title": "Testing & security",
     "sub": "A layered gate, and running untrusted PR code safely",
     "notes": "Part four. Testing and security — a layered gate that catches real regressions, and how to run untrusted contributor code without risk."},

    {"kind": "bullets", "accent": BLUE, "title": "A layered test gate",
     "body": "- Tier 1 — GPU-free smoke, on every PR, on standard runners (ship now, no Azure)\n- Tier 2 — gated GPU end-to-end, only on approval (needs funded compute)\n- Cheap checks run always; expensive checks run only when a human releases them\n- This mirrors the maintainers' own ask: automatic checks plus a manual gate",
     "notes": "The recommendation is a two-tier gate. Tier one is a G-P-U free smoke suite that runs on every pull request on standard runners — it ships now and needs no Azure. Tier two is a gated G-P-U end-to-end run that fires only on approval and needs funded compute. Cheap checks run always; expensive checks run only when a human releases them. This is exactly the maintainers' own ask: automatic checks, plus a manual gate."},

    {"kind": "twocol", "accent": BLUE, "title": "What each tier catches",
     "left_head": "GPU-free smoke catches", "left_accent": GREEN,
     "left_body": "- Resolution conflicts — uv lock --check\n- Import / ABI breaks — import smoke, --help\n- API breaks — tiny CPU train/eval step\n- Won't-build — container build smoke\n- Infra/UI — terraform validate, contract, fuzz",
     "right_head": "Only GPU e2e catches", "right_accent": RED,
     "right_body": "- CUDA / driver runtime breaks\n- Isaac Sim Vulkan / MIG issues\n- GPU-only ABI mismatches (the torch case)\n- Real training-loop convergence on device\n- → only a funded GPU tier catches these",
     "notes": "Why two tiers? Because they catch different things. The G-P-U free smoke tier catches resolution conflicts, import and A-B-I breaks, A-P-I breaks, won't-build failures, and infrastructure or U-I regressions — cheaply, on every pull request. But only the G-P-U end-to-end tier catches CUDA and driver runtime breaks, Isaac Sim rendering issues, G-P-U only A-B-I mismatches like the torch incident, and real on-device training. That is precisely why a funded G-P-U tier earns its place — the one we will reach in Phase three."},

    {"kind": "twocol", "accent": BLUE, "title": "How deep can the GPU-free smoke go?",
     "left_head": "Reachable on a standard runner", "left_accent": GREEN,
     "left_body": "- Import + --help — every domain (CPU torch)\n- IL: one real CPU train step — tiny dataset\n- Submit flow: validate config (~70% offline)\n- Build the eval image — the only image we own (others are stock/managed)",
     "right_head": "Needs the GPU tier", "right_accent": RED,
     "right_body": "- RL / Isaac: GPU-coupled end-to-end (Vulkan / CUDA)\n- No CPU training mode exists\n- CUDA / driver / MIG runtime breaks",
     "notes": "How deep can the cheap tier actually go? On a standard runner you can import every entry point and run help across all domains, run one real C-P-U training step for imitation learning on a tiny dataset, render and schema-validate the OSMO and AzureML submission YAML — about seventy percent of that flow offline — and build the evaluation container image, around seven to nine gigabytes, after a free-disk-space step. What it cannot reach: reinforcement learning is G-P-U coupled end to end through Isaac Sim and Vulkan, there is no C-P-U training mode, and only real hardware catches CUDA, driver, and MIG runtime breaks. More disk via larger runners buys speed, not capability."},

    {"kind": "bullets", "accent": GREEN, "title": "Gated GPU e2e design",
     "body": "- Trigger on PR-review approval, non-forks only — the HuggingFace LeRobot pattern\n- Authenticate to Azure with OIDC — no stored secret\n- Submit-and-poll to the scale-from-zero OSMO / AML GPU pool (idle cost ≈ $0)\n- PR code runs INSIDE the job sandbox, never on the runner\n- Wrap in a GitHub Environment with required reviewers; concurrency-cancel; timeout caps",
     "notes": "Here is the design for the G-P-U tier. It triggers on pull request-review approval, and only for non-forks — the same pattern HuggingFace LeRobot already uses. It authenticates to Azure with OIDC, so there is no stored secret. It submits a job to the scale-from-zero pool and polls — idle cost is essentially zero. The contributor's code runs inside the job sandbox, never on the runner. And it is wrapped in a GitHub Environment with required reviewers, with concurrency cancellation and timeout caps."},

    {"kind": "twocol", "accent": BLUE, "title": "Running untrusted PR code safely",
     "left_head": "pull_request — safe default", "left_accent": GREEN,
     "left_body": "- Fork PRs get a read-only token\n- No repository secrets exposed\n- Run untrusted build/test here\n- Pass results forward as artifacts",
     "right_head": "pull_request_target — danger", "right_accent": RED,
     "right_body": "- Base context, has secrets\n- Checkout PR head + build = \"pwn request\"\n- Use only label-gated, human-reviewed\n- Or release secrets via Environment approval",
     "notes": "The security model deserves its own slide. The pull request event is the safe default: fork pull requests get a read-only token and no secrets, so untrusted build and test can run there, passing results forward as artifacts. The pull request-target event is the dangerous one: it runs in the base context with secrets, and if you check out and build the contributor's head, that is the classic 'pwn request' — secret exfiltration. Use it only label-gated and human-reviewed, or release secrets only through an environment approval."},

    {"kind": "bullets", "accent": BLUE, "title": "A required check on **/uv.lock",
     "body": "- Goal: a manually-gated required check when a PR touches a lockfile\n- create-check-run, with the name matched to branch-protection rules\n- Fail-safe pattern: a default-pass job, plus a gated heavy path on lock changes\n- Cautionary tale: #691 / #547 show naive path filters silently skip — and block merge",
     "notes": "Finally, the maintainers asked whether a required check could be gated manually on lockfile changes. It can. You create a check run whose name matches the branch-protection rule. The fail-safe pattern is a default-passing job plus a gated heavy path that engages only when a lockfile changes. And there is a cautionary tale here: incidents six-ninety-one and five-forty-seven show that naive path filters either silently skip — testing nothing — or leave a required check pending and block merge. The gate must be fail-safe by design."},

    {"kind": "section", "accent": PURPLE, "part": "Part 5", "title": "What others do",
     "sub": "Proven patterns from inside and outside Microsoft",
     "notes": "Part five. What others do — the proven patterns, inside and outside Microsoft, that we can simply adopt."},

    {"kind": "bullets", "accent": GREEN, "title": "The exemplar is our own upstream",
     "body": "- HuggingFace LeRobot — fast CPU tests every PR; GPU tests only on approval, never forks\n- NVIDIA NeMo — GitHub Environments gate the GPU queue; gated agentic review & fix loop\n- Isaac Lab — the very simulator used here runs GPU CI with fork-safety checks\n- PyTorch — Actions Runner Controller GPU fleet; a deliberately minimal Dependabot",
     "notes": "The strongest finding: we do not need to invent any of this. LeRobot — the training library this repository depends on — already runs fast CPU tests on every pull request and G-P-U tests only after approval, never on forks. NVIDIA NeMo gates its G-P-U queue with GitHub Environments and runs a gated agentic review and fix loop. Isaac Lab, the very simulator used here, runs G-P-U C-I with fork-safety. And PyTorch runs a large self-hosted G-P-U fleet with a deliberately minimal Dependabot."},

    {"kind": "bullets", "accent": BLUE, "title": "Dependency best practice across OSS",
     "body": "- vercel/ai — gold-standard multi-group dependabot.yml (npm-only; left Renovate for simplicity)\n- huggingface/transformers — uses the 7-day `cooldown` (on its github-actions deps)\n- cheeriojs/cheerio — auto-merge via dependabot/fetch-metadata + `gh pr merge --auto`\n- Renovate shops — config:recommended + automergeMinor + a Dependency Dashboard",
     "notes": "And on the dependency side, the norms are clear from real configurations. Vercel's A-I SDK — a single-ecosystem, npm-only project — has a gold-standard multi-group Dependabot file, and migrated from Renovate to it for simplicity, a different context from this repo's multi-ecosystem Python. HuggingFace transformers uses the new seven-day cooldown window. Cheerio auto-merges using the standard fetch-metadata and auto-merge pattern. And Renovate shops lean on the recommended preset with minor-version auto-merge and a dependency dashboard. These are all directly copyable."},

    {"kind": "section", "accent": GREEN, "part": "Part 6", "title": "The recommendation",
     "sub": "A layered program, sequenced by cost and funding",
     "notes": "Part six. The recommendation — a single layered programme, sequenced by cost and funding."},

    {"kind": "phases", "accent": GREEN, "title": "The phased roadmap",
     "phases": [
         {"tag": "Phase 0", "when": "now · hours", "accent": GREEN, "cost": "$0",
          "head": "Configuration only",
          "items": "Dependabot risk-grouping + cooldown · reviewer waits for green CI, one comment"},
         {"tag": "Phase 1", "when": "now · days", "accent": BLUE, "cost": "$0",
          "head": "GPU-free smoke gate",
          "items": "lock --check · import + --help · YAML validate · eval-image build (only image we own) · fail-safe lock check"},
         {"tag": "Phase 2", "when": "now · days", "accent": BLUE, "cost": "$0",
          "head": "Safe automation",
          "items": "Auto-merge low-risk on green CI · agentic triage → Copilot coding agent"},
         {"tag": "Phase 3", "when": "when funded", "accent": AMBER, "cost": "GPU $",
          "head": "Gated GPU e2e — the capstone",
          "items": "OIDC submit-and-poll to scale-from-zero OSMO / AML · Environment + required reviewers"},
         {"tag": "Spike", "when": "parallel", "accent": PURPLE, "cost": "$0",
          "head": "Renovate evaluation",
          "items": "Cross-ecosystem grouping · pep621 / uv · native automerge — decide vs Dependabot"},
     ],
     "notes": "Here is the whole programme as one phased roadmap. Phase zero, now and within hours, is configuration only — risk-aware Dependabot grouping with a cooldown, and a reviewer that waits for green C-I and keeps a single comment. Phase one, now and within days, is the G-P-U free smoke gate — lock-consistency, import and help checks, rendered-YAML validation, the evaluation-image build, and a fail-safe required check on lockfiles. Phase two, also now, is safe automation — auto-merge for low-risk updates and an agentic triage layer that escalates to the Copilot coding agent. Phase three, when funded, is the gated G-P-U end-to-end capstone via OIDC submit-and-poll. And running in parallel, a spike to evaluate Renovate. The key line: everything except phase three needs no Azure and ships now."},

    {"kind": "bullets", "accent": GREEN, "title": "Sequencing: ship now vs funded",
     "body": "- Phases 0–2 and the Renovate spike need NO Azure — they run on standard runners\n- Each phase is independently shippable and reduces regressions or noise immediately\n- Only Phase 3, the GPU capstone, needs funded compute — its design is settled\n- Map: Phase 1 smoke + Phase 0 grouping would have caught the #809, #790, #958 class early",
     "notes": "The sequencing is the practical heart of this. Phases zero through two, plus the Renovate spike, need no Azure at all — they run on standard runners, each is independently shippable, and each reduces regressions or noise immediately. Only phase three, the G-P-U capstone, needs funded compute, and its design is already settled. And to close the loop: the phase-one smoke tier and phase-zero grouping together would have caught the interpreter and CUDA incidents — eight-oh-nine, seven-ninety, and nine-fifty-eight — early."},

    {"kind": "bullets", "accent": AMBER, "title": "Alternatives considered & rejected",
     "body": "- A fully custom bot replacing Dependabot — reinvents native grouping; high upkeep\n- Migrating to Renovate immediately via the Mend App — niche in MSFT OSS; approval friction\n- pull_request_target + PR-head checkout for fork creds — the classic pwn request\n- GPU on every PR / self-hosted runner running PR code — too costly and risky unfunded",
     "notes": "For honesty, the alternatives that were considered and rejected. A fully custom bot replacing Dependabot reinvents grouping that is now native, with high upkeep. Migrating to Renovate immediately through the Mend app is rejected as a first move — it is a niche tool in Microsoft open source with real approval friction; the scoped github-action spike is the measured path instead. Giving fork pull requests credentials via pull request-target is the classic pwn request. And running G-P-U on every pull request, or a self-hosted runner that executes contributor code, is too costly and risky without dedicated funding."},

    {"kind": "bullets", "accent": BLUE, "title": "Open decisions",
     "body": "- Required-status-check census — confirm what actually blocks merge today\n- Dependabot grouping now, or a Renovate spike first?\n- No-GPU-tier scope for public forks until funding lands\n- Submit-and-poll vs self-hosted runner risk tolerance\n- Out of band: fix the live torch 2.10 / 2.11 desync",
     "notes": "A handful of decisions gate planning. First, a census of which checks actually block merge today. Second, whether to tune Dependabot now or run the Renovate spike first. Third, the scope of the no-G-P-U tier for public forks until funding lands. Fourth, the risk tolerance between submit-and-poll and a self-hosted runner. And quite separately, the live torch desync should be fixed out of band."},

    {"kind": "bullets", "accent": BLUE, "title": "Next steps",
     "body": "- File the backlog issue — no prior one exists, so it's non-duplicative\n- Pick the first thread: grouping + reviewer-cost + smoke tier are the quick wins\n- Full research, with citations, lives in: .copilot-tracking/research/2026-06-19/\n- Six subagent evidence files back every claim in this deck",
     "notes": "The next steps. File the backlog issue — there is no prior one, so it is non-duplicative. Pick the first thread to implement; the grouping change, the reviewer-cost fix, and the smoke tier are the quick wins. And the full research, with citations, lives in the tracking folder — six subagent evidence files back every claim in this deck."},

    {"kind": "section", "accent": BLUE, "part": "Thank you", "title": "Questions & discussion",
     "sub": "PR Regression Safety  ·  research findings  ·  June 2026",
     "notes": "That concludes the full findings. In short: the regressions are real and runtime-specific, most of the remedy needs no Azure and can ship now, and the expensive G-P-U gate is designed and waiting only on funding. Thank you — happy to take questions."},
]


def main():
    root = Path("content")
    (root / "global").mkdir(parents=True, exist_ok=True)
    Path("narration").mkdir(exist_ok=True)
    # clear stale slide dirs
    for d in root.glob("slide-*"):
        for p in d.glob("*"):
            p.unlink()
        d.rmdir()

    total = len(SLIDES)
    style = {
        "dimensions": {"width_inches": W, "height_inches": H, "format": "16:9"},
        "metadata": {"title": "PR Regression Safety — Full Research Findings",
                     "author": "Task Researcher (Copilot)",
                     "subject": "Dependency-update intelligence and gated e2e testing",
                     "keywords": "dependabot, CI, e2e, gh-aw, security, OSS",
                     "category": "Research"},
        "defaults": {"speaker_notes_required": True},
    }
    (root / "global" / "style.yaml").write_text(
        yaml.safe_dump(style, sort_keys=False, allow_unicode=True))

    for i, s in enumerate(SLIDES, 1):
        elements = RENDER[s["kind"]](s, i, total)
        doc = {"slide": i, "title": s["title"], "layout": "blank",
               "background": {"fill": BG}, "elements": elements,
               "speaker_notes": s["notes"]}
        d = root / f"slide-{i:02d}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "content.yaml").write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100))
        Path("narration", f"slide-{i:02d}.txt").write_text(s["notes"])
    print(f"wrote {total} slides")


if __name__ == "__main__":
    main()
