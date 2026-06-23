# PR Regression Safety — Narration Script

51 slides. Generated from `gen_content.py`.

## Slide 01 — PR Regression Safety

This repository has a dependency-regression problem its green pipeline cannot see. The remedy is not one large platform bet; it is four cheap controls that ship now and one funded gate that waits on a budget number. The next slide is the whole case in one statistic.

## Slide 02 — Green CI has missed every costly regression

Eight distinct runtime regressions and test-integrity gaps were reconstructed from this project's history, and the green pipeline caught none of them. Most break on a real interpreter or a real GPU, which a CPU runner never touches. Two were caused by the pipeline itself, where a path filter quietly switched tests off for weeks. The decision this talk asks for follows directly from that zero.

## Slide 03 — The eight, in one place

These five carry the rest of the talk, so they are worth a name. Eight-oh-nine and seven-ninety are interpreter mismatches: a lock resolved for one Python version against a runtime built on another. Nine-fifty-eight is a torch security bump that dragged in an incompatible CUDA runtime, and it still ships today because the lock pins one version while the pipeline force-installs another. Six-ninety-one and five-forty-seven are the pipeline disabling its own tests. And starlette shows the churn. Hold these five; every later recommendation maps back to them.

## Slide 04 — What this asks for

The ask is four controls plus one capstone. Phases zero, one, and two are configuration and ordinary Actions runners — no Azure, no budget. Phase three is the only line that needs funded GPU compute, and it is the only one that can prove the GPU half of safe-to-merge. Each phase stands alone and reduces regressions on its own, so this is adopted incrementally, not as a single bet. Every claim that follows is grounded in the repo's own history and a prototype we ran.

## Slide 05 — The stack under test — why this repo is hard

This audience knows CI but not necessarily this runtime, so five terms first. Isaac Lab is a GPU simulator that needs Vulkan and ships its own Python three-eleven. CUDA and torch wheels are compiled contracts that must match the driver, which is why a version bump can break on device and nowhere else. MIG slices one GPU into isolated instances. AzureML and OSMO take a submitted job and run it on a pool that scales from zero. And uv produces an exact pinned lock per subproject. Every recommendation later turns on one of these five.

## Slide 06 — Dependency intake today

Dependencies arrive through twenty-one Dependabot blocks, and every group is a single wildcard catch-all, so nothing is split by risk: a harmless patch and a CUDA-breaking major look identical. The ignore-pins, like marshmallow here, were all added reactively, after something already broke. This is the intake that feeds the regressions.

## Slide 07 — 21 contexts = several independent runtimes

Those twenty-one blocks are not one application with one lockfile; they are several independent runtimes sharing a repository. Reinforcement learning on Isaac Lab pinned to Python three-eleven. Imitation learning on LeRobot. Evaluation and its container. A full web application. Four Terraform roots. The same version bump can be harmless in the React app and fatal in the Isaac training image — which is exactly why blind, uniform intake is dangerous here.

## Slide 08 — CI and automation today

Two facts complete the current picture. First, every test job runs on a standard CPU runner with no GPU, and it force-installs a torch version that disagrees with the committed lock — a live desync that ships today. Second, the only agentic workflow is an advisory Dependabot reviewer: a maintainer types a slash command, it reads, it comments, it never writes. So today's automation is one read-only adviser on top of a pipeline that never touches a GPU.

## Slide 09 — The failure map

This is the map the whole plan hangs on. Read each row to the first column that catches it. The interpreter breaks, eight-oh-nine and seven-ninety, are caught by the Phase-one smoke gate, on a CPU. The integrity failures, six-ninety-one and five-forty-seven, are caught by a fail-safe required check, also Phase one. Churn is absorbed by Phase-zero grouping and Phase-two auto-merge. And nine-fifty-eight splits in two: the cheap phases catch the dependency-resolution half early, but the actual device-ABI break can only be proven on a GPU, in Phase three. That split is the honest reason the capstone earns funding.

## Slide 10 — Dependency intake

Phase zero changes how dependencies arrive. It is pure configuration and ships in an afternoon.

## Slide 11 — Intake has no risk signal

Today every block batches by ecosystem, not by risk, so a patch and a major land in the same pull request and the same review. The seven ignore-pins were all reactive — added after a break, never before. And there is no cooldown, so a freshly published version can open a pull request the same day. The fix is to give intake the risk signal it lacks.

## Slide 12 — What others do — group by risk, add a cooldown

The pattern to copy is settled. Vercel's AI SDK splits production from development dependencies and batches minor and patch together. HuggingFace transformers adds a seven-day cooldown, a stability window before a bump opens. Both are real configuration files, not advice — we can lift them directly.

## Slide 13 — Recommendation — split by risk, keep security fast

Side by side: on the left, one wildcard group per ecosystem, patches and majors treated alike. On the right, update types are split so patches and minors batch into one auto-mergeable pull request while majors are isolated for review, a seven-day cooldown is added, and — the firm rule — security updates stay ungrouped and fast-tracked, never held in a weekly batch. This is configuration only; it removes the noise that hides the dangerous bump.

## Slide 14 — Renovate — a scoped spike, not a switch

One alternative deserves a place, not a section. Renovate's single real edge here is cross-ecosystem grouping: one config across npm, Python, Terraform, and Go, where Dependabot needs a block each. What is not the edge is uv — Dependabot has supported it since twenty-twenty-five and this repo relies on it. The friction is organizational: the hosted app needs approval, but a self-hosted Action sidesteps that. So the recommendation is a time-boxed spike that switches only if it measurably cuts pull-request volume without weakening the security lane. The adoption evidence is in the appendix.

## Slide 15 — GPU-free smoke gate

Phase one is the cheap gate that catches the expensive interpreter class, with no GPU and no Azure.

## Slide 16 — A green check tests nothing real

The pipeline's blind spot is structural. It runs on a generic Ubuntu image with a generic Python, while the breaks that hurt happen on Isaac's own three-eleven runtime, which CI never loads. And when a path filter misfired, the pipeline reported green while testing nothing. The conclusion writes the design: to catch these, the smoke gate has to run inside the actual runtime image.

## Slide 17 — Two depths: Tier 0 and Tier 1

CPU smoke has two depths, and naming them prevents a costly confusion. Tier zero runs in a plain virtual environment in seconds — lock-check, import, schema-validate — cheap enough for every pull request. But it deliberately installs CPU wheels, so it is checking a different dependency graph than production's CUDA one; it catches import and resolution errors, not production resolution. Tier one is the one that mirrors production: it pulls the real image and reinstalls the pull request's lock exactly as the training job does, on the real interpreter. That tier deterministically catches the interpreter class, eight-oh-nine and probably seven-ninety. Its limit is disk, not capability.

## Slide 18 — Tier 1 — import inside the real image

Concretely, for the hardest environment: pull the real Isaac image and reinstall the pull request's lock with no-deps, exactly as the training job does, on the real three-eleven interpreter. That install step is the circuit breaker for the interpreter and marker class — eight-oh-nine was a lock resolved for three-twelve, and it fails right here, before anything imports, on a CPU agent. The import-check mode is the follow-on net: it runs the real launcher far enough to load the Isaac, SKRL, and gym graph, then stops before AppLauncher, the only GPU step — catching a package that installs but will not load on the runtime. Neither step needs a GPU.

## Slide 19 — We ran it — it catches #809 on CPU

This is not a claim on a slide; we ran it. Inside the actual Isaac image, the runtime interpreter is Python three-eleven-point-one-three. Install a dependency that requires three-twelve — the exact shape of eight-oh-nine — and the runtime rejects it at install time, on the CPU. The same mismatch fails a lock-check against the repo's real training lock. The interpreter class breaks before any GPU compute, so a CPU agent is enough to catch it. The harness is saved with this session.

## Slide 20 — Recommendation — Phase 1a + 1b

The recommendation is two named jobs. Phase one-a is Tier zero on every pull request: lock-check, a CPU-torch install so the heavy CUDA build does not block it, import smoke, a config-preview of the submit scripts, and the evaluation-image build. Phase one-b is Tier one, the real-image import, path-gated to the area that changed. Both sit behind one fail-safe required check. But state the limit plainly: this catches install, import, and interpreter drift. It cannot prove CUDA, Vulkan, MIG, or a real training loop — and that limit is exactly what Phase three exists to close.

## Slide 21 — Safe automation

Phase two removes human toil from the safe path without weakening any gate. It auto-merges only the bumps that are provably trivial, and leaves everything riskier to scoped manual review.

## Slide 22 — Every low-risk bump waits on a human

The toil is concentrated in the safe path. Dependabot cannot merge its own pull requests, so every trivial patch waits for a maintainer's click, and high-risk and low-risk updates get the same manual handling — roughly twenty-four pull requests a week, most of them trivial. That is toil, not safety, and it is fixable without touching the safety bar.

## Slide 23 — Recommendation — auto-merge, scoped tight

Auto-merge the trivially safe, and only that — no agent, no inference. Dependabot's fetch-metadata action reads the update type without running the pull request's code; for a development patch it enables auto-merge, which waits for the required checks. The natural objection — won't this cause incidents — is answered by scope: patch-only at first, development and docs and actions only, never a runtime or GPU package, never a security pull request, required checks green, and an instant-revert playbook. Everything riskier stays in scoped manual review.

## Slide 24 — Gated GPU end-to-end — the capstone

Phase three is the capstone: the only tier that can assert safe-to-merge on a GPU. Its blocker is a budget number, not a design.

## Slide 25 — The GPU half is never proven

The cheap phases close the dependency and interpreter classes, but one class remains open. Only real hardware catches CUDA and driver breaks, Isaac's Vulkan rendering, and MIG. Recall the failure map: nine-fifty-eight's resolution half is caught early, but its device-ABI half passes every CPU tier and only fails on the GPU. Proving that half is what Phase three buys, and the only thing standing in the way is a funded, capped GPU subscription.

## Slide 26 — What others do — NeMo gates the GPU run

NeMo gates the expensive half cleanly. Every GPU job depends on a wait-in-queue job bound to a GitHub Environment, so nothing on a GPU starts until a reviewer or a queue bot approves it. And to run fork code safely, NeMo avoids the dangerous base-context trigger entirely — a bot mirrors fork pull requests onto internal branches, so untrusted code never executes with secrets in scope. Approval gate plus sandboxed execution: that is the shape we copy.

## Slide 27 — Recommendation — the gated GPU job

The safety hinge is that contributor code never runs on the runner that holds the cloud token. Job A runs on the plain pull-request event — read-only, no secrets — and only renders a constrained job spec. Job B runs after an approving review, checks out the trusted base workflow rather than the pull request, validates the spec against an allowlist, mints an OIDC token through an Environment gate, and submits. The contributor's code runs inside the GPU pool, never on the privileged runner. That is the difference between a gate and a leak.

## Slide 28 — What funding buys

A capstone needs a number, so here is an honest, capped estimate — and I label the dollar figures low-confidence. Each gated run is short, and the GPU node scales from zero between runs. But the honest catch is that the Kubernetes cluster it submits to cannot scale all the way down: the control plane and a system node pool have to stay up around the clock, a standing cost on the order of a couple hundred dollars a month for a dedicated cluster — or near-zero marginal if we fold it onto a cluster we already run. Runs happen only on approval, not per pull request, so think five to fifteen a week. With a one-hour timeout, single concurrency, and a monthly cap, the GPU compute itself is on the order of a hundred and fifty dollars a month; add the standing cluster and the all-in expected spend is a few hundred. What that buys is the only proof of GPU-runtime safety there is. What it costs to skip is that GPU-only regressions keep merging blind.

## Slide 29 — Roadmap and the ask

Bring it together: the sequence, and the specific decisions requested.

## Slide 30 — Roadmap — ship now vs funded

Everything but Phase three runs on ordinary runners and ships now; Phase three waits on the GPU budget. The order is deliberate: intake first to cut noise, then the smoke gate to catch the interpreter class, then automation to remove toil, and the funded capstone last. The Renovate spike runs in parallel and is reversible. Funding does not gate progress — only the final proof.

## Slide 31 — Decision requested today

So, concretely, seven decisions. Approve the configuration grouping. Approve the Tier-zero required check on every pull request. Approve a capped Tier-one real-image spike. Approve a patch-only auto-merge pilot scoped to development, docs, and actions. Approve a time-boxed Renovate spike through the Action. Defer Phase three until there is a GPU budget number — its design is settled and waiting. And separately from all of it, fix the live torch desync now; that one is not a decision, it is a bug.

## Slide 32 — Questions

That is the case: the regressions are real and runtime-specific, four controls ship now for almost nothing, and the GPU capstone is designed and waiting on a budget number. The appendix has the primers, the prototype detail, the economics, and the rejected alternatives. I will stop there.

## Slide 33 — Primers & glossary

Appendix A is the tool primers and the glossary: the concepts the talk leans on, here for anyone who wants the definition behind a term.

## Slide 34 — Primer — Dependabot

Dependabot has two independent update streams. Version updates keep packages current and are configured in dependabot.yml. Security updates are always on and automatic, triggered by advisories against your dependency graph, needing no configuration, and are never batched behind the version stream. Groups batch, ignore records deliberate pins, the limit caps noise, and a cooldown adds a stability window. It regenerates lockfiles natively.

## Slide 35 — Primer — uv and lockfiles

The manifest lists direct dependencies and the required Python version; the lock is the resolver's exact output, with hashes and markers. The danger is a pull request that edits the manifest but forgets the lock, so CI installs a different graph. A lock-check gate prevents that drift.

## Slide 36 — Primer — security advisories (GHSA)

A GitHub Security Advisory records a vulnerable package, its patched version, and a severity, usually tied to a CVE. When such a package is in your graph, Dependabot opens a security pull request to the minimum patched version. Because these close known exposure, they are fast-tracked by severity, never batched. That separate fast lane recurs throughout the recommendations.

## Slide 37 — Primer — CI gating tiers

Good CI is tiered: cheap checks on every pull request, expensive checks only when their area changed. This repo computes path booleans in one job and aggregates into a single required check. The trap, which bit this repo twice, is a naive paths filter that leaves a required check skipped, so a pull request looks green having tested nothing. The aggregator must be fail-safe.

## Slide 38 — Primer — running untrusted PR code

A fork pull request is untrusted code. On the plain event it gets a read-only token and no secrets, so building it is safe. On the base-context event it has secrets, and running the contributor's head there is the classic pwn request. So gate genuine cloud access behind an Environment, and remember that the OIDC token is only as safe as the federated policy that pins which repo and environment may mint it.

## Slide 39 — Glossary

A glossary to leave up for reference — the terms used through the talk, each in a line. Not read aloud.

## Slide 40 — Phase mechanics

Appendix B is the mechanics behind the phase recommendations, in running order: first the Phase 0 dependency-intake detail, then the Phase 1 smoke-gate detail.

## Slide 41 — Renovate — adoption across Microsoft OSS

Because adoption determines approval friction, we measured it. Dependabot is the de-facto standard across Microsoft open source. Renovate appears in roughly nineteen org repositories, mostly one Visual Studio team sharing a preset; one in Azure, about nine in dotnet, zero in the GitHub org, and the open-source program page names only GitHub-native features. So the hosted app is a minority, team-scoped path — but the self-hosted Action sidesteps the approval entirely.

## Slide 42 — Renovate — the scoped spike config

If the spike runs, this is its shape: one config across ecosystems, a stability window, auto-merge for minor and patch, and the torch pin preserved. Run through the Action, not the app, so there is no approval barrier. Auto-detection handles our ecosystems; only the custom pins and groups need translating, a few hours of work. Then decide on the merits — does it cut pull-request volume without losing the security lane.

## Slide 43 — These are production contracts, not toy configs

Two surfaces can break, not one. This is the AzureML job contract for an Isaac training container — the runtime wrapper, the mandatory EULA, the checkpoint behavior. A dependency bump can break the container's runtime packaging, caught by import smoke, or the submission contract that renders this YAML, caught by config-preview, or on-device execution, caught only by the GPU tier. Different tests catch each; that is why the gate is layered.

## Slide 44 — Tier 1 — one image per job, disk-gated

Tier one's honest constraint is disk. Isaac unpacks to around twenty gigabytes, the PyTorch image another fifteen, the eval image seven to nine — they cannot co-reside even after a free-disk step. So it is one image per matrix job, pruned between legs, path-gated to the environment whose dependencies actually moved. The secondary cost, pull time, a nightly cache warm-up absorbs.

## Slide 45 — A small refactor widens the Isaac smoke

One small repository change deepens the Isaac smoke. Today the RSL launcher builds the Isaac AppLauncher at module top level, so the file cannot be imported or show help without a GPU. Moving that call into a main function, as the SKRL script already does, makes the module importable on a CPU agent. It is small, but it is not zero: it needs acceptance criteria — imports on CPU, help exits before the launcher, argument order preserved, GPU behavior unchanged, and a test to hold all of that.

## Slide 46 — Smoke operating cost and the fail-safe gate

A new gate has running costs, so own them explicitly. The smoke tier's runtime is minutes; its known flakes are image-pull timeouts and free-disk fragility, triaged by a re-run and a cache; an owner watches schema drift as images change. And the fail-safe pattern is the heart of it: the required summary always runs, never reports skipped, and a wrongly-skipped heavy leg fails the check rather than passing silently — which is exactly what bit this repo in six-ninety-one and five-forty-seven.

## Slide 47 — The case — economics, objections, alternatives

Appendix C is the argument around the recommendation: the economics that justify the cheap phases, the objections a skeptic will raise, the alternatives we rejected, and the mandate behind the work.

## Slide 48 — Economics — the toil being priced out

The case for the cheap phases is also economic. Two dependency pull requests a day, most trivial, each costing reviewer minutes. Batching and patch auto-merge take most of that queue away. Set against the status quo — eight runtime incidents over the window, each taking hours to diagnose — the configuration phases pay for themselves immediately, before any GPU spend.

## Slide 49 — Anticipated objections

The objections a skeptical maintainer will raise, answered. Auto-merge is safe because it is scoped to patches in non-runtime areas with an instant revert. Pinning Python is necessary but not sufficient — it does not exercise a real image install or device execution. Replacing Dependabot now is premature when grouping is native and Renovate is a minority tool here. GPU on every pull request is too costly and unsafe for forks. And the prototype, run under emulation, is enough to prove the interpreter class, though a native runner would harden the final confidence.

## Slide 50 — Alternatives considered and rejected

For honesty, the paths rejected and why. A custom bot reinvents grouping that is now native. Migrating straight to the Renovate app carries approval friction for a minority tool. Giving forks credentials through the base-context trigger is the pwn request. Running GPU on every pull request, or letting a runner execute contributor code, is too costly and risky unfunded. And pinning Python everywhere helps but does not exercise a real image install or device execution. Each shares one flaw: it buys control by adding risk or upkeep.

## Slide 51 — Mandate and method

Finally, provenance. The maintainers asked to solve the dependency problem at its root and to gate safe merges. The method was six parallel research threads, each writing a cited evidence file, grounded in the repository's own history, configurations, and pull requests, plus the prototype we executed this session inside the real Isaac image. The full research, with citations, lives in the tracking folder.
