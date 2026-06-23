# Visual slide critique

Reviewed rendered JPGs as images, including slides 001, 002, 004, 005, 006, 007, 011, 012, 013, 014, 017, 018, 024, 031, 032, 036, 037, 038, 039, 040, 043, 045, 046, 050, 056, 057, 062, 063, 064, 065, 066, 067, and 068. Confidence: high.

## High

| Slides | Problem | Concrete fix |
| --- | --- | --- |
| 037, 046 | Code is visually dense and small. Slide 037's shell pipeline has long wrapped command lines, backslash continuations, inline comments, and a stray quote at the left edge; it reads like pasted terminal text rather than presentation code. Slide 046 has too many YAML levels and comments for one screen. Confidence: high. | Split each into two slides: one with the trigger/intent, one with the critical code. Increase monospace to 21-22 pt, cap lines at ~58 characters, remove inline comments longer than 20 characters, and move explanatory comments into a callout above the card. |
| 005, 006, 007, 011 | Primer two-pane slides crowd the left prose column while the right code card has a large empty lower half. The visual weight is wrong: paragraphs feel compressed, while the code area wastes space. Confidence: high. | Convert the prose to 3-4 bullets or widen the left column by ~8%. Alternatively lower the code card height by 25% and use the freed space for a larger key-term strip. Keep body text around 23-24 pt and raise line spacing slightly. |
| 014, 017, 018, 038, 039, 040, 050, 056 | Code-card slides use a card nearly the full slide height even when code occupies only the upper third. The grey box dominates the page and creates a hollow lower half. Confidence: high. | Make code cards content-fit vertically with a minimum height, not a fixed tall rectangle. For short snippets, reduce card height to ~55-65% of current and add a one-line implication or visual callout below. |
| 063 | Roadmap rows are legible but crowded; the first row's description and right-side cost compete, and Phase 1 wraps tightly inside a shallow row. The right cost labels feel bolted on rather than aligned to a column. Confidence: high. | Increase row height by 10-15%, align all cost labels to a fixed right column with more padding, reduce description text to 17-18 pt, and shorten Phase 1 copy or wrap it deliberately into two balanced lines. |

## Medium

| Slides | Problem | Concrete fix |
| --- | --- | --- |
| 001, 004, 013, 024, 031, 057, 062, 068 | Divider and cover photography feels generic corporate stock rather than technical CI/CD. The smiling people images are polished and on-brand, but they dilute the engineering subject. Confidence: high. | Use the photo layouts more sparingly. For technical sections, prefer abstract gradient dividers, repository/workflow screenshots, or subtle code/graph texture. Keep one human-photo cover and one close slide. |
| 004, 013, 024, 031, 057, 062, 068 | White-on-color divider text is readable, but the subtitle lines are thinner and lower contrast against saturated backgrounds, especially red/orange slides 024 and 062. Confidence: high. | Increase divider subtitle weight or size by ~2 pt, add a 10-15% dark overlay behind the left text region, or switch subtitles to 90-95% white opacity only if the background is darkened. |
| 036 | Two-column layout is strong, but the right header wraps awkwardly after “real image,” leaving “minutes” alone on the second line. Confidence: high. | Reduce the right header by 2 pt, widen the right column by ~4%, or change to “Tier 1 — real image smoke, minutes”. |
| 012 | Glossary is impressively compact and mostly legible, but row spacing is tight and long definitions in the right column wrap into dense two-line blocks. Confidence: high. | Split into two glossary slides or reduce to the 10-12 terms needed in the talk. Increase row leading by ~10% and keep definition text at no less than 17 pt. |
| 002, 032, 045, 064, 065, 066, 067 | Bullet slides are very readable but top-heavy, leaving a large blank lower half. This is acceptable for pacing, but repeated use starts to look under-designed. Confidence: high. | For short bullet slides, add a bottom summary band, small evidence/source line, or a simple icon/diagram. Do not enlarge bullets; the current body size is already presentation-safe. |
| 011, 014, 017, 018, 037, 038, 039, 040, 050, 056 | Code legibility is mostly good at full slide size, but comments wrap or align awkwardly on several slides. The inline comments create visual noise and make YAML/shell harder to scan. Confidence: high. | Remove most inline comments from code and place interpretation in the subtitle or a right-side annotation. Keep code to syntax plus one highlighted line. |

## Low

| Slides | Problem | Concrete fix |
| --- | --- | --- |
| 001 | Cover is clean and legible. The subtitle line break after “end-” is slightly awkward but not damaging. Confidence: high. | Shorten to “Intelligent dependency updates and gated e2e testing” or reduce subtitle width so the break falls after “updates”. |
| 013 and 057 | Teal divider slides reuse the same laptop-at-table photo. The repetition is noticeable because the image is distinctive. Confidence: high. | Use a different divider treatment for the Spike section or crop tighter so the repeated photo is less obvious. |
| 018 | Big-stat-style slide is visually not a true big-stat slide; it is a sparse code slide with a small caption and a large empty grey card. Confidence: high. | If intended as a statistic, make the number or phrase the hero element. If intended as code evidence, crop the grey card to the snippet height. |
| 045 | The title is long but still fits. Its visual weight crowds the accent bar and makes the slide feel less airy than nearby bullet slides. Confidence: high. | Shorten to “What others do — gh-aw and NeMo” or reduce title size by 3-4 pt only on long-title slides. |
| 050, 056 | Green accent bars on recommendation code slides read consistently, but the same green is also used for some Tier 1 technical slides, blurring category semantics. Confidence: moderate. | Reserve green for recommendations and use blue for neutral technical implementation, or add a small section label to reinforce meaning. |

## Slide-type judgments

| Type | Judgment | Fix |
| --- | --- | --- |
| Cover | Strong brand fit, clean hierarchy, good contrast. The stock photo is generic but acceptable for the opening. Confidence: high. | Keep, with the subtitle wording fix above. |
| Section dividers | Good template execution and strong legibility. The photo choices are the weakest conceptual fit for a technical CI/CD talk. Confidence: high. | Reduce photo repetition and use more technical/abstract visual language. |
| Bullet slides | Highly readable, but repeated blank lower halves make the deck feel unfinished rather than intentionally minimal. Confidence: high. | Add lightweight visual anchors on repeated short-bullet slides. |
| Primer two-pane | Useful structure, but prose is too paragraph-heavy beside sparse code. Confidence: high. | Convert prose to bullets and shorten/flex the code card. |
| Glossary | Legible for a dense reference slide, but near the lower bound for room readability. Confidence: high. | Split or cut terms; increase row spacing. |
| Code comparison/code cards | No obvious off-slide clipping in the sampled slides. The main issue is overlarge grey cards and overly dense snippets, not overflow. Confidence: high. | Fit card height to content, split dense snippets, and move comments out of code. |
| Two-column | Slide 036 works, but the right header wrap is inelegant. Confidence: high. | Shorten or resize that header. |
| Roadmap/phases | Slide 063 is useful and clear, but row density and cost-label alignment need refinement. Confidence: high. | Taller rows, fixed cost column, shorter descriptions. |
| Close | Slide 068 is clean and readable; slide 067 has the same blank-lower-half issue as other short bullet slides. Confidence: high. | Keep close; add a visual anchor or reduce slide 067's unused space. |

## Biggest visual problem

The single biggest visual problem is the fixed, oversized grey code-card treatment: it makes many slides look simultaneously too dense at the top and empty at the bottom, while long snippets such as slides 037 and 046 become harder to read than they need to be. Confidence: high.
