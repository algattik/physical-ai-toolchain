# PR Regression Safety deck narrative critique

This critique covers narrative and structure only. It assumes the facts are already verified and focuses on what the deck makes the audience feel, remember, and decide.

## HIGH

### 1. Slides 01-03 — The opening starts with logistics, not stakes

The first three slides explain the talk before they create tension. Slide 01 promises a research report; Slide 02 lists the structure; Slide 03 defends the method. That is a cold open. The funding decision-maker does not yet know what is at risk, what decision is needed, or why this cannot wait. The deck's strongest hook is already available on Slide 20: eight relevant failures, zero caught by green CI. It arrives too late.

Fix: open with the failure pattern, not the agenda. Use this order: Slide 01 cover with subtitle sharpened to “Green CI has missed every costly runtime regression”; Slide 02 “8 vs 0 — why safe-to-merge is false today”; Slide 03 “Decision requested: ship $0 fixes now; fund the gated GPU capstone.” Move the detailed agenda to a small footer or cut it. Fold “mandate & method” into one sentence on the evidence slide or into an appendix.

### 2. Slides 04-12 — The primer stalls the argument before it starts

Eight primer slides before the current state is too much pre-teaching. The audience came for a decision on PR regression safety, but the deck spends roughly ten percent of its slide count defining tools before proving the problem. The primer also teaches several concepts that become clearer when introduced at the moment of use: Dependabot in Phase 0, gh-aw in Phase 2, pull_request_target in Phase 3. The glossary on Slide 12 confirms the problem: this is reference material, not narrative.

Fix: cut the front-loaded primer to one “Terms used today” slide with five definitions maximum: Dependabot version/security streams, uv.lock, gh-aw safe outputs, required check, Environment/OIDC. Move the rest to appendix or introduce terms just-in-time inside the relevant phase. If the deck must keep a primer, place it after Slide 23, once the audience believes the problem and has a reason to learn the mechanisms.

### 3. Slides 13-23 and 25/32/44/52/58 — The AA baseline duplicates the phase problem slides

The AA “current state” section does useful work, but it overreaches. Slides 14-22 already diagnose blind intake, CPU-only CI, agentic underuse, churn, incidents, and security framing. Then each phase repeats the same diagnosis: Slide 25 repeats Slide 14 and Slide 19; Slide 32 repeats Slides 17 and 20; Slide 44 repeats Slide 18 plus Slide 30; Slide 52 repeats Slide 17, Slide 20, and Slide 34; Slide 58 repeats Slide 14 and Slide 26. The result is not a clean AA baseline followed by new arguments; it is a baseline that keeps reappearing under new labels.

Fix: make the AA section a compact three-claim baseline: dependency intake is blind, CI is CPU-only and path-gating has failed, automation is advisory only. Keep one incident catalogue slide, not two. Then make each phase problem slide explicitly incremental: “Given the baseline, this phase fixes X.” If a phase problem cannot add a new problem, cut it and let the phase divider carry the transition.

### 4. Slides 24-56 — The A/B/C scaffold is visible, but it becomes mechanical and inconsistent

The intended pattern is A Problem today, B What others do, C Recommendation. The labels help orientation, but the execution drifts. Phase 0 has two recommendations plus a security rule and reviewer-cost fix; Phase 1 puts “What each tier catches” and “How deep can smoke go?” under the “others/recommendation” region even though they are internal design rationale; Phase 2’s “What others do” starts with gh-aw capability, not an external precedent; Phase 3 repeats the safety primer and NeMo precedent. The scaffold becomes a filing system rather than a story engine.

Fix: enforce a stricter unit per phase: one problem slide, one external pattern slide, one recommendation slide, one optional code slide only if the code changes the decision. Put all detailed YAML and prototype proof after the recommendation as appendix-style backup. Retitle internal rationale slides plainly: “Why this phase is enough” or “Boundary of the phase,” not “What others do.”

### 5. Slides 31-42 — Phase 1 absorbs the emotional climax that should belong to Phase 3

Phase 1 is structurally dominant. It has the richest technical proof, the prototype, the two-tier distinction, the disk constraint, the two-line refactor, and the fail-safe check. By the time Phase 3 arrives, the audience has been taught that CPU smoke catches the costly class, including #809, #790, and #958. That weakens the funding ask: if the $0 tier catches the named incidents, the GPU tier feels like a nice-to-have instead of the capstone.

Fix: trim Phase 1 to “what $0 catches” and hold back “only GPU catches” as the bridge into Phase 3. Do not say Phase 1 plus grouping would have caught #958 unless the Phase 3 funding story is reframed around a different, clearly uncaught class. Make Phase 1 end with a limitation, not a victory: “This catches install/import/runtime-image drift. It still cannot prove CUDA, Vulkan, MIG, or real training behavior.”

### 6. Slides 51-56 — Phase 3 does not land as the capstone

The deck calls Phase 3 the capstone, but structurally it is short, late, and less vivid than Phase 1. It lacks a funding-decision slide. Slide 52 states the blocker is funding, then Slides 53-56 explain safety mechanics and YAML. That is technically responsible but narratively flat. The decision-maker needs to hear what funding buys, what risk remains unfunded, and what approval would unlock.

Fix: add a Phase 3 decision slide before the YAML: “Funding buys the only proof of safe-to-merge on GPU.” Show three columns: unfunded risk, funded gate, decision needed. Move detailed untrusted-code mechanics to one condensed slide or appendix. End Phase 3 with a strong “Definition of done” slide: “A dependency PR is not safe until CPU smoke passes and the gated GPU run passes when the changed area requires it.”

### 7. Slides 57-61 — The Renovate spike is in the wrong place

Renovate after the Phase 3 capstone is a deflationary detour. The deck moves from the expensive strategic climax to a tooling comparison about cross-ecosystem grouping. That may be important, but it is not emotionally or structurally bigger than gated GPU e2e. It makes the capstone feel like just another phase rather than the end of the argument.

Fix: move Renovate into Phase 0 as an “alternative path/spike” after Slide 30, or move it to the close as one line in the roadmap. If kept as a section, put it before Phase 3 so the deck climbs from dependency hygiene to automation to funded e2e, rather than stepping down after the climax.

### 8. Slides 62-68 — The ending is a long tail, not a decision close

The close has roadmap, sequencing, alternatives, open decisions, next steps, and Q&A. That is six slides after the plan is already known. Slide 66 “Open decisions” weakens the close because it reopens uncertainty after the deck has spent an hour arguing that the design is settled. Slide 67’s “file the backlog issue” is operationally small compared with the buy-in goal. The final impression is administrative, not decisive.

Fix: replace Slides 65-67 with one “Decision requested” slide. It should ask for three commitments: approve Phase 0-2 implementation now, approve a Renovate spike as parallel evaluation or defer it, and fund/authorize Phase 3 GPU e2e. Keep alternatives as appendix. Put live torch desync in an “immediate fix” callout, not as an open decision.

## MED

### 9. Slides 03 and 67 — Evidence process is over-explained in the spoken arc

“The mandate & method” and “six evidence files back every claim” try to establish credibility, but they consume front-stage narrative time. The audience does not need research methodology before seeing the problem. Repeating the evidence-file point near the end also sounds defensive.

Fix: reduce methodology to one caption: “Evidence: repo history, configs, PRs, OSS benchmarks.” Link the evidence folder in the final slide or appendix. Do not narrate the six research threads unless challenged.

### 10. Slides 17, 20, 21, 32, 34, 36, 40, 52, 64, 66 — The repeated “green CI is blind” motif turns into a drumbeat

The phrase and its supporting examples recur so often that they stop escalating. The 8-vs-0 statistic is powerful once, useful twice, and stale by the fifth invocation. Torch desync also recurs as current state, incident, CPU-smoke proof, GPU-only example, sequencing proof, and open-decision item. That blurs whether it is evidence, diagnosis, or action item.

Fix: create one canonical “failure map” slide with rows for #809, #790, #958, #691, #547 and columns for “missed by today,” “caught by Phase 0/1,” and “requires Phase 3.” Then refer back to the map by phase. Use torch desync once as the live example and once as the immediate fix; stop reintroducing it.

### 11. Slides 33, 45, 46, 53, 54 — External precedents are scattered and repetitive

LeRobot and NeMo carry much of the “others already do this” burden, but they appear in several roles: fast CPU tests, GPU approval gates, agentic babysitter, fork safety. That is credible but structurally noisy. The audience may remember “NeMo does things” rather than the specific pattern to copy.

Fix: use one “Pattern bank” slide before the phases: LeRobot = CPU every PR + GPU after approval; NeMo = environment-gated GPU queue + human-approved agentic loop; Isaac Lab = GPU CI with fork safety; Vercel/HuggingFace/Cheerio = dependency hygiene. Then each phase cites one pattern instead of re-explaining the repository.

### 12. Slides 24-30 and 43-50 — Reviewer-cost material is split across phases

Phase 0 includes reviewer waits for green CI, while Phase 2 handles safe automation and agentic triage. These are the same storyline: reduce human and token toil without lowering safety. Splitting them makes Phase 0 less clean and Phase 2 partially repetitive.

Fix: keep Phase 0 purely dependency intake: grouping, cooldown, security fast lane. Move “reviewer waits for green CI” to Phase 2 as the first safe-automation step. Then Phase 2 becomes: wait for green CI, single comment, auto-merge low-risk, escalate high-risk.

### 13. Slide 23 — The thesis slide is abstract when it should become the plan

“So: this is open-source quality + security” correctly frames the axes, but it does not yet translate them into the phased plan. It names supply-chain hygiene, CI integrity, and safe execution, but the audience still has to infer that these map to Phases 0-3.

Fix: turn Slide 23 into the first roadmap preview: “Three controls, four phases.” Map supply-chain hygiene to Phase 0, CI integrity to Phase 1, safe automation to Phase 2, and GPU proof to Phase 3. This gives the audience a mental model before the per-phase scaffold begins.

### 14. Slides 35-40 — The smoke-gate detail is too early for a mixed audience

Slides 35-40 dive into CPU train steps, runtime images, matrix disk limits, AppLauncher placement, and prototype output before the audience has accepted the recommendation. Maintainers may appreciate it; the funding decision-maker will hear implementation before decision.

Fix: keep one “CPU smoke depth” slide in the main story. Move Tier 1 code, disk matrix, AppLauncher refactor, and prototype output into backup. In the main arc, say: “We tested the risky class; it fails at install/import on CPU. Details available.”

## LOW

### 15. Slide 01 — The title undersells the conflict

“PR Regression Safety” is accurate but inert. It sounds like a hygiene project, not a decision about whether green CI can be trusted in a robotics ML monorepo.

Fix: keep the title but add a sharper subtitle: “Why green CI is not safe-to-merge — and the phased gate that fixes it.”

### 16. Slide 12 — The glossary is a dead slide in a narrated deck

A glossary that will not be read aloud is useful as reference, but it is dead air in a narrative sequence. It also signals that the preceding primer may have overloaded the audience.

Fix: move it to appendix or make it a handout. If kept, do not spend a slide on it in the spoken path.

### 17. Slides 26-27 and 59-61 — Renovate receives more narrative weight than its recommendation warrants

The recommendation is only a scoped spike, but Renovate gets primer time, Phase 0 comparison time, and a three-slide late section. That overweights a secondary decision relative to the main safety plan.

Fix: make Renovate a single decision box in Phase 0: “Dependabot first; Renovate spike only for cross-ecosystem grouping.” Move Microsoft OSS adoption details to backup.

### 18. Slide 65 — Alternatives considered arrives after the audience should already be closing

Alternatives are useful for objections, but placing them after the roadmap interrupts commitment. It tells the audience to re-evaluate discarded paths just as they should be choosing.

Fix: move alternatives to appendix or distribute them where the objection arises: custom bot in Phase 0, pull_request_target in Phase 3, GPU every PR in Phase 3.

## Single most important structural change

Move from “teach all concepts, then repeat A/B/C five times” to “prove the failure in the first three slides, then run a decision ladder.” The ladder should be: current failure map → $0 controls now → safe automation → funded GPU proof → decision requested. Cut or appendix the front-loaded primer, late Renovate detour, and long administrative close.
