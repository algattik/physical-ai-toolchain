# Editorial critique — PR Regression Safety deck

## Verdict: too long for the decision

**HIGH — Ship a 36-slide core, 24–26 minutes at 1x, with a 14–18 slide appendix.** The current 68 slides / ~39 minutes is a research readout, not a decision deck. It over-serves maintainers who want implementation detail and under-serves the funding decision-maker who needs: problem, proof, options, cost, ask, risk. The author’s “don’t worry if it gets long” is the trap: the longer version dilutes the funding ask and makes every phase look equally important.

**Target package:**

| Version | Target | Use |
| --- | ---: | --- |
| Executive core | 36 slides / 24–26 min | Live presentation to CI/CD maintainers + funder |
| Appendix / backup | 14–18 slides | Evidence, primers, prototype detail, Renovate adoption proof |
| One-slide version | 1 slide / 1 min | Opening TL;DR and reusable funding ask |

**The deck does not currently have a crisp one-slide / one-minute version. HIGH.** It opens with agenda and method, not conclusion. Add one slide after the title: **“Decision: ship no-Azure safeguards now; fund gated GPU e2e next.”** Include three bullets: regressions are real and CPU CI misses them; Phases 0–2 cost standard runners only; the ask is a dedicated gated GPU subscription plus approval to implement the no-Azure work immediately.

## Section balance

| Section | Current | Target core | Rank | Editorial judgement |
| --- | ---: | ---: | --- | --- |
| Intro | 3 | 2 | HIGH | Agenda + method delay the point. Lead with conclusion and ask. |
| Primer | 8 | 2 | HIGH | Too long. The audience knows CI/CD; teach only terms needed for the recommendation. |
| Current state / evidence | 11 | 6 | HIGH | Strong but padded. Keep churn, blind CI, incident proof; cut topology detail. |
| Phase 0 | 7 | 4 | MED | Good near-term value; duplicate “what others do” and security recommendation. |
| Phase 1 | 12 | 7 | HIGH | Now bloated after Tier-1 additions. Keep the real-image insight; move refactor/prototype mechanics to backup. |
| Phase 2 | 8 | 4 | HIGH | Too many variants of “agent decides, human/agent acts.” |
| Phase 3 | 6 | 4 | MED | Appropriate for funding, but YAML design repeats recommendation. |
| Renovate spike | 5 | 1 | HIGH | Lowest-priority item receives too much airtime. One slide in core, evidence in appendix. |
| Roadmap / close | 7 | 6 | MED | Needs an explicit ask + cost slide; merge roadmap and sequencing. |

## Concrete cut / merge list

Starting point: **68 slides**. Add one executive TL;DR / ask slide after Slide 01: **+1 = 69**. Apply the cuts and merges below: **36-slide core**. Backup slides are not counted in the live core.

| Rank | Original slide(s) | Action | Core count effect | Rationale |
| --- | --- | --- | ---: | --- |
| HIGH | 02 — What this covers | Cut entirely | -1 | Agenda slide adds no decision value. The roadmap later covers structure. |
| MED | 03 — The mandate & method | Move to appendix | -1 | Useful for evidence credibility, but not before the decision frame. Mention method in notes. |
| HIGH | 04–12 — Primer block | Merge to 2 core slides; move detailed glossary to appendix | -6 | Eight slides teaches vocabulary at classroom pace. Keep only “dependency vocabulary” and “CI/safety vocabulary.” |
| HIGH | 13 — What’s in the repo today | Cut entirely | -1 | Section divider; narration can bridge. |
| MED | 14 + 15 | Merge | -1 | “Dependency intake today” and “21 contexts” make one point: monorepo blast radius varies. |
| MED | 16 — These are full environments, not toy configs | Move to appendix | -1 | Good proof, too detailed for core. Use one phrase on merged 14/15. |
| MED | 17 + 18 | Merge | -1 | CI today and agentic review today are both “current gate is shallow.” |
| HIGH | 21 + 22 | Merge | -1 | The two incident-catalogue slides make the same proof. Keep five incidents max. |
| LOW | 24 — Dependency intake & reviewer cost | Cut entirely | -1 | Section divider. |
| MED | 26 + 27 | Merge | -1 | “Dependency hygiene” and “grouping/cooldown” duplicate. One external-practice slide is enough. |
| HIGH | 28 + 29 | Merge | -1 | Security ungrouped is a rule inside the grouping recommendation, not its own slide. |
| LOW | 31 — GPU-free smoke gate | Cut entirely | -1 | Section divider. |
| HIGH | 34 + 35 | Merge | -1 | “What each tier catches” and “How deep can smoke go” overlap. One tier-boundary slide. |
| HIGH | 36 + 37 + 40 | Merge | -2 | The real point is: Tier 1 runs inside the real image and catches #809-class failures. Keep proof; cut mechanics. |
| MED | 38 — Tier 1 — one image per job, path-gated | Keep core, tighten | 0 | Important feasibility constraint. Reduce narration by half. |
| MED | 39 — A 2-line refactor widens the Isaac smoke | Move to appendix | -1 | Useful implementation note, not decision-critical. |
| HIGH | 41 + 42 | Merge | -1 | Smoke-cpu job and fail-safe required check are one recommendation. |
| LOW | 43 — Safe automation | Cut entirely | -1 | Section divider. |
| MED | 45 + 46 | Merge | -1 | Both are external agentic precedent; NeMo can be one proof point. |
| HIGH | 47 + 48 + 49 | Merge | -2 | Three versions of the same recommendation: triage layer, decider/doer, wire to CI. Use one flow slide. |
| LOW | 51 — Gated GPU e2e — the capstone | Cut entirely | -1 | Section divider. |
| MED | 55 + 56 | Merge | -1 | Design and YAML repeat. Keep design; move YAML to appendix if needed. |
| HIGH | 57 — Renovate evaluation | Cut entirely | -1 | Section divider for lowest-priority work. |
| HIGH | 58 + 59 + 61 | Merge to one core slide | -2 | One Renovate-spike slide is enough: why, how, decision criterion. |
| HIGH | 60 — Reality check — Renovate in Microsoft OSS | Move to appendix | -1 | Evidence is useful only if challenged. It overweights a spike. |
| LOW | 62 — Roadmap & sequencing | Cut entirely | -1 | Section divider. |
| MED | 63 + 64 | Merge | -1 | Roadmap and sequencing are the same close. |
| MED | 65 — Alternatives considered & rejected | Move to appendix | -1 | Keep for Q&A, not live unless the audience is adversarial. |
| HIGH | 66 + 67 + new ask content | Merge into “Open decisions + ask + cost” | -1 | The close needs a decision slide, not a task list. |

**Resulting live count:** 69 - 33 = **36 slides**.

## Redundancy findings

**HIGH — “What others do” is repeated too often.** Slides 26/27, 33, 45/46, 53/54, and 59/60 create the feeling that every recommendation needs precedent. Keep one precedent per decision: dependency hygiene, CPU/GPU tiering, safe agentic loop, safe GPU execution, Renovate spike.

**HIGH — Phase recommendations repeat inside each phase.** Phase 2 is the worst: Slides 47, 48, and 49 are the same mechanism at different zoom levels. Phase 3 repeats design and YAML in Slides 55/56. Phase 0 repeats grouping/security in Slides 28/29.

**HIGH — The two incident-catalogue slides should become one.** The audience needs pattern recognition, not a legal record. Put three runtime failures and two CI-integrity failures on one slide; backup carries the full catalogue.

**MED — “What each tier catches” vs “How deep can smoke go” should merge.** Both answer the same audience question: what cheap smoke can and cannot catch. One two-column slide can do it.

**MED — Tier 1 now has too many proof/mechanics slides.** Slides 36–40 are five slides on a sub-design. Keep the conclusion and feasibility constraint in core; move refactor details and raw prototype result to appendix.

## What is missing despite the cuts

**HIGH — Add a one-slide executive TL;DR / ask immediately after title.** Proposed content:

> **Decision needed:** authorize Phases 0–2 now; fund Phase 3 GPU gate.
>
> - **Problem:** ~24 dependency PRs/week; eight reconstructed regressions or CI-integrity gaps; CPU CI caught zero.
> - **No-Azure fixes:** risk-aware Dependabot grouping, green-CI agentic review, CPU/real-image smoke, safe low-risk auto-merge.
> - **Funding ask:** dedicated gated GPU e2e capacity using OIDC + GitHub Environment approval; idle cost near zero, but requires subscription/resource approval.

**HIGH — Add or rewrite one “Ask + cost” slide near the close.** The deck says Phase 3 needs funding but never forces the decision. Give the funder a binary ask: approve no-Azure implementation now; approve funded GPU subscription next; choose Renovate spike timing.

**MED — Add one “what we will not do” line on the ask slide.** No credentials for fork PRs; no GPU on every PR; no immediate Renovate migration. This reassures both maintainers and funder.

## Proposed lean running order — 36-slide core

1. Title
2. Executive TL;DR + ask **[new]**
3. Problem in one sentence: blind dependency intake + no e2e gate
4. Dependency churn stat
5. Regressions invisible to CPU CI stat
6. Incident catalogue — merged runtime + CI integrity
7. Current repo topology — merged dependency intake + 21 contexts
8. Current gate — merged CI + agentic review today
9. Open-source quality + security thesis
10. Dependency vocabulary — Dependabot, Renovate, uv, GHSA
11. CI/safety vocabulary — gh-aw, tiers, untrusted PR code
12. Phase 0 problem — blind intake + reviewer cost
13. External dependency hygiene — merged grouping/cooldown examples
14. Phase 0 recommendation — grouping + security fast lane
15. Reviewer waits for green CI
16. Phase 1 problem — green CI is blind
17. External precedent — fast CPU tests every PR, GPU only after approval
18. Tier boundary — what CPU smoke catches vs only GPU e2e catches
19. Tier 1 real-image smoke catches #809-class failures — merged 36/37/40
20. Tier 1 feasibility — one image per path-gated job
21. Phase 1 recommendation — smoke-cpu + fail-safe required check
22. Phase 2 problem — no safe automation
23. External precedent — gh-aw capabilities + NeMo gated loop
24. Phase 2 recommendation — one triage flow: decider → issue → coding agent → PR → CI
25. Auto-merge low-risk on green CI
26. Phase 3 problem — no GPU e2e gate
27. Safe execution model — pull_request vs pull_request_target
28. External precedent — NeMo gates GPU run
29. Phase 3 recommendation — gated GPU e2e design
30. Renovate spike — one slide: residual problem, GitHub Action path, decision criterion
31. Phased roadmap + sequencing — merged 63/64
32. Ask + cost + decisions — merged 66/67 with explicit funding request
33. Alternatives rejected — compressed, optional if time; otherwise appendix
34. Implementation first moves — grouping, reviewer-cost, smoke tier
35. Close: why this reduces regressions now and reserves GPU for what only GPU catches
36. Questions

## Appendix / backup candidates

- Slide 03 — mandate & method
- Slide 12 — glossary
- Slide 16 — full AzureML environment detail
- Slide 21/22 full incident catalogue if merged core slide is challenged
- Slide 27 detailed grouping/cooldown examples
- Slide 39 two-line Isaac refactor
- Slide 40 raw prototype result / harness details if not merged into Slide 19
- Slide 46 full NeMo babysitter loop
- Slide 56 YAML for gated GPU job
- Slide 60 Renovate Microsoft OSS adoption reality check
- Slide 65 alternatives considered & rejected if removed from live flow

## Single highest-value cut

**HIGH — Collapse the 8-slide primer into 2 slides.** It saves six slides, removes the classroom opening, and gets the audience to the decision before attention decays.
