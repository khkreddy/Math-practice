# 09_PACKET_MODIFY

**Current modify law.** Modification uses the map packet and the minted item as a seed. Do not rearrange the old stem into registration triples and print those fields back out.

Evidence: `systems/modify_archive/grok_4_7/trial_500/` (mean 3.92, median 4, 71/100 at or above Cambridge median). Form-filling runs archived under `trial_200`–`trial_400` scored 1.0–1.75 and are **not** the law. The 2026-10-07 blind audit of thirty writer packs (Opus 5.5, plus a second 100-point reading of the first sixteen) is the evidence for what the packet must contain.

## What the packet's intelligence is

A pack improved the item when the writer could fix three things from it: one defensible key, wrong answers that are real student difficulties, and a situation that separates those. Both readings lost that use when the builder removed records. The six-slot cap did it first. The later rule did it again: if any mix-up had an admitted border, the brief kept only the bordered mix-ups, ordered by the border score. The sentences the audits used were still on the hinge. Gibbs energy lost `ΔH < 0, so the reaction is spontaneous.` Net force lost the forward-force belief. Differentiability lost the continuity sentence. A border is information about the line a mistake crosses. It is not a ticket into the brief.

Intelligence is the center hinge, in full, in stored order:

1. **Key record.** Decision, law, because, reasoning, operation, every boundary, the check, the student default, the student signals, false success, every not-yet line, out of scope, and the anti-narration line. These strings are copied whole. The builder does not shorten them and does not drop a boundary past the fourth.
2. **Every mix-up on that hinge.** Wrong output, observable prediction, confused element, and, when the map stored them, the border and the boundary links. A mix-up with no border stays. A template sentence stays. An empty field stays empty. The writer chooses which difficulties the item uses.
3. **Every prerequisite gap** on that hinge, with the capability sentence copied whole.
4. **The JEV cell brief** for the requested construct: construct id, zone membership, noul.

The seed contributes form only: item type, option count, and the ask-shape hint. That hint is not hinge intelligence.

`situation_boundary` is still named, as the boundary the most center-hinge mix-ups produce. Naming it does not remove the other mix-ups.

A support hinge is added only when the center cannot carry the requested cell. The neighbour rule is unchanged: prerequisites first, then same chapter and grade, at most two. Once a support hinge is in the packet, its key record and every one of its mix-ups are included on the same terms. They are not cut to two mix-ups.

## What modification is

1. The existing minted question is a **SEED** only: form (MCQ / band / option count) and a shape hint for what was being asked.
2. The writer receives the full hinge intelligence defined above. The builder does not select a subset of mix-ups, does not rank them by border score, and does not stop at six.
3. If the given hinge cannot carry the cell, add **neighbour hinges** centered on that hinge (prerequisites / same-chapter neighbours), then include their units and Mx in the packet.
4. Compose a better question **from that packet**. Do not rebuild by slicing the old stem into `givens[]` / registration fields and rendering those fields into the stem.

Loader: `systems/modify/packet_modify.py` (`packet_for_row` / `load_packet` / `facts_for_writer`).

## What the writer sees

- `units[]` with `role` center|support, `unit_id`, `decision_do_not_print`, `law_do_not_copy`, every boundary, `situation_boundary` when the center mix-ups produce one, `anti_narration`, and the rest of the key record when the hinge stores it
- `misconceptions_mx[]` lists every mix-up from the center and from any support hinge in the packet: `mx_id`, wrong-output, observable, confused element, `border` when the map stored one, `boundary_links` when the map stored them
- `probe` is designed at modify time from the request and the lead border, then scored. It is not stored on the map. `probe.text` is present only when that score is at least 0.70. The writer may stage the item there. A border constrains the wrong option that cites that mix-up. It does not remove any other mix-up from the packet.
- `prerequisite_gaps[]` lists every gap on the center hinge
- `jev_cell`, `seed_form_hint_ask_shape_only` (ask shape only — not prose to splice)
- subject, grade, band, item_type, n_options

## What Grok must do

Compose candidate-facing prose for a reader from the packet. Grok must **not** author the evidence the gate checks (no self-typed map triples, no inventing Mx ids). See `04_GROK_SLOT.md`.

Release gate is **MIQG only** (`systems/modify/miqg/miqg_cal.py`): TOP / `release_gate` PASS required to serve. Bank admit/serve (`systems/modify/jev_loop/bank_gate.py` `bank_append_eligible`) additionally refuses any MCQ whose wrong options lack `option.feedback` (`learning_state`, `evidence`, `source`).

After option values are fixed, the writer fills each wrong option's `feedback` from the packet Mx (`misconceptions_mx`) or prerequisite gap for that option: `learning_state` (subject-language claim about the idea used or the missing prior) + `evidence` (concrete fact from this stem). Source is `"misconception"` or `"prerequisite_gap"` — keep a missing prerequisite distinct from a rule used backwards. Field name: `OPTION_FEEDBACK_FIELD` in `systems/question_ingest/option_feedback.py`.

## What is demoted (not law)

- Rendering `givens[].statement` / registration strings into the stem.
- Refusing an item solely because a hand-built attribute-table / value-set file is missing.
- Form-filling: slicing the old stem into referent|attribute|value rows and asking Grok to phrase those rows.

The packet must come from the map (packet_modify.py). Do not invent map claims from the old stem.

## T-MINT then T-MOD

The modify harness runs the two steps in order (`systems/modify/jev_loop/harness.py`).

T-MINT studies the hinge packet and writes the situation and the expected answer. That expected answer must be the result this stem requires. An independent solve of the stem, blind of the proposed key, must match it. A general hinge rule that a given condition blocks is not the answer. T-MOD does not write distractors until the same key check passes. If the hinge already has situations, T-MINT chooses a different one. A user-supplied situation is used as given. A situation may combine the center hinge with one named companion hinge when the decision needs both.

T-MINT chooses the format from the menu. T-MOD completes that format. On a standard single-key MCQ, T-MOD writes every surviving route, then keeps the keyed result plus the three strongest distractors. A result reached by two routes is kept. JEV ranks the rest. Letters are A–D. The keyed option is the bare result, not an explanation of why it is correct. Assertion–reason stays the five relation options. Three-statement, option-table, structured, and open items keep their own shapes.

T-MINT still uses the packet above as teacher-side evidence for which situation to build. T-MOD does not consume that packet as the source of the options.

When two routes produce the same result, the item keeps that result once. The candidate sees the result, not a sentence that explains how it was reached. Both routes are recorded on the teacher side.

A free-response item, including a practical or a planning question, uses the same tests. The variables are the quantities, conditions, and steps already in the situation. T-MOD carries those variables so a surviving route is an error a student would make, then writes the complete question. The route tests are the same at every grade and subject. They are not fitted to one paper's items.
