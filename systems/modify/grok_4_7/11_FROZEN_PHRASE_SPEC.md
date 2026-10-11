# Frozen phrase spec

**Status:** frozen 2026-10-08 after an independent cross-check of [Opus 5.5 review](697fc449-fd95-4054-a834-e0fc55853788).

This spec removes known defects. It does not claim minted items beat the chemistry ingest or JEEBench. That claim needs a blinded comparison that has not been run.

## Evidence that survived the cross-check

- Sanitized maps hold 28,095 mix-ups. 9,857 have border text. The other border objects carry only a reason. No row stores `mx_id`.
- 5,657 hinges. No hinge repeats a route. No mix-up has an empty `wrong`. 1,983 hinges have at least three mix-ups on one admitted boundary. Science G6–8: 337 of 391. Maths: 806 of 1,659 hinges have fewer than three mix-ups.
- `bind_cited_mx` reassigned a bad citation to `unused[0]`. `attach_wrong_option_feedback` labelled wrong options by walking the mix-up list. T-MOD's probe picked one lead mix-up. `select_mx` highlighted one or two lines inside T-MINT. Those are choosers.
- The `_{index}` id fallback exists, but the sanitized path already sets `{unit_id}/MX_{route}` before that fallback. The fallback is deleted so the two paths cannot diverge.
- Human review (`reviews.jsonl`, 23 rows) shows phrasing and logic failures. Two of them are structural: missing combination claims, and an assertion–reason frame on the wrong item. "Distractor also true" and "same logic" are not decidable in code.

## Invariants

1. `mx_id` is `{unit_id}/MX_{route}` everywhere. A hinge whose routes are not unique fails the build.
2. One packet builder feeds T-MINT. Full center-hinge mix-ups. No six-cap. No border-only filter. Neighbour mix-ups are labelled support and are not citable. T-MOD does not consume that packet as the source of the wrong options. T-MOD reads the sitting item and tests the eight routes on that situation.
3. The situation sentence is `situation_boundary` of the center mix-ups (most admitted links, then highest p1, then text).
4. After the item exists, if the mix-ups linked to that situation are at least as many as the wrong slots, those linked ids are the legal set and `situation_verified` is true. Otherwise the legal set is every center mix-up and `situation_verified` is false.
5. T-MINT writes no wrong options, so an empty distractor list is the handoff to T-MOD, not a refusal. A T-MINT stem that copies the law, the decision, or a border is refused.
6. T-MINT: the writer receives the format contract, the legal set, the full center catalog, support mix-ups marked do-not-cite, and the situation sentence as teacher-side, and uses them to choose a situation. `select_mx` is not printed. The probe step does not run. T-MOD's writer receives the sitting stem and key, or the free-response situation, and the eight route tests. It does not receive the map catalog.
7. T-MOD does not cite stored ids. Its wrong option is the bare result of a route test on the sitting situation. When two routes reach the same result, the same-output gate keeps that result once and drops the wording that explains the route. There is no remap and no positional feedback.
8. Before any code writes the worked solution: `result` equals the keyed option text when both are present; roman-set options have their labels in the stem; a stem that evaluates an assertion and a reason uses the five relation sentences in the format menu; candidate text does not contain an `mx_id` or the banned meta phrases. T-MINT chooses the format. T-MOD follows it. T-MINT's expected answer must match an independent solve of the stem (the proposed key is not shown to that solve). T-MOD does not build until that key check passes. After T-MOD a standard single-key MCQ has four options A–D: the key plus the three strongest distractors. A result reached by two routes is kept. Letters are consecutive from A. The keyed option does not explain itself with a because-clause when the other options are bare results.
9. If the hinge lists entities, "the material" and "the substance" are refused. The word "it" is not a violation.
10. Gate order: invariant 8, citation check, MIQG. JEV typed questions are not called and do not decide until a labelled set exists for each question.
11. A trail that passes MIQG still has `release.human_hold`. It does not enter the pass bank.
12. The trail stores the legal set, `situation_verified`, and the citations.

## Not in this harness

Fixed option counts. A model that writes the key before the phrasing call. Remap. Positional feedback. A JEV threshold. Full construct scoring on every mint. JEPA-Anything. Neighbour mix-ups in the legal set. Code that rewrites candidate prose to pass a gate, except the T-MOD same-output gate, which keeps one bare result and drops the second wording of that result. Assertion–reason where both members are true (the binding policy is still open).
