# 03_DRAFTING

**Modify (current law):** content comes from the map packet (`09_PACKET_MODIFY.md` / `packet_modify.py`), not from slicing the old stem into registration triples. Rules R1–R9 below still govern **mint** registration. Nothing here produces candidate-facing prose; Grok does that in `04_GROK_SLOT`.

## R0 — Modify: packet before phrase (law)

On modify:
1. Load `packet_for_row(seed_row)`.
2. If the center hinge cannot carry the cell, the packet already includes neighbour hinges (`extra_hinge_required`).
3. Feed `writer_packet` to Grok. Do **not** register `givens[]` by harvesting sentences from the old stem. Do **not** render registration fields into the stem.
4. Hand-built attribute-table / value-set files are **not** required to admit a modify write. The packet must come from the map via `packet_modify.py`.
5. Release gate after phrasing is **MIQG only** (TOP / `release_gate` PASS).

## R1 — Mint: solution before ask

Write `solution.steps` first, from `hinge_given` outward. Each step names its `uses_hinge`. If a step needs a hinge not in `hinges_used`, trigger Step 1b; if no map-adjacent hinge with positive `weight_connection` exists, end with `future_defect`.

Bound facts the candidate is told may be recorded as structured `givens[]` on mint when they come from the map / figure asset — never as free sentences harvested from a prior stem for the purpose of printing them back out.

## R2 — Mint: single ask is the last step's output

`single_ask.target` is the output of the final step in `entail_trace`. It is one noun phrase (`the size of angle AOB`, `the name of the relationship between OA and OB`, `the number of lines of symmetry of the figure`). Two noun phrases joined by "and" is two asks; register two items.

`ask_type` is set from the target's type:

| target type | ask_type | default command_word |
|---|---|---|
| number with unit | `compute` | Calculate |
| number without unit | `state_value` | State |
| named relation/category | `select_relation` | Identify |
| justification | `give_reason` | Explain (one reason, one mark) |
| drawn object | `construct` | Draw |
| sequence | `order` | Complete |

`give_reason` items are mcq only when four determinate reasons exist; otherwise `short_response` with a `mark_scheme`.

## R3 — Key entailed, unique, typed

`key.value` must equal the last step's output. `equivalents[]` lists every acceptable surface (e.g. `90`, `90°`, `ninety degrees`; `perpendicular`, `at right angles`). Uniqueness: no distractor value may appear in `equivalents[]`.

## R4 — Distractors answer the same ask

Each option `value` has the same type as `key.value`. For `select_relation` this means every option is a relation of the same kind (`perpendicular`, `parallel`, `equal in length`, `collinear`), never a label or a location. `answers_ask` is set true only when the value is a well-formed member of the target type; any false value ends registration with `future_defect`.

Provenance:
- `misconception` options: `source_id` from the misconception bank bound to a hinge in `hinges_used`; `rationale` states the faulty step. On modify, Mx ids come from the packet's `misconceptions_mx`.
- `prerequisite_gap` option: exactly one; `source_id` from `solution.steps[*].prerequisite_ids` or the packet's `prerequisite_gaps`; it is the answer a candidate gives when the prerequisite is missing, and it is the `ls_seed.entry_step` for learn-by-solve.

Distractors are wrong **answer values**, not fault labels or descriptions of the learner.

After each wrong option **value** is fixed, fill `option.feedback` (`OPTION_FEEDBACK_FIELD` in `systems/question_ingest/option_feedback.py`) from the map Mx or prerequisite gap bound to that option, in the two-part shape `{learning_state, evidence, source}` (`source` is `"misconception"` or `"prerequisite_gap"`). `learning_state` is the subject-language claim; `evidence` is the concrete stem fact that shows it. Keep a missing prerequisite distinct from a rule used backwards.

## R5 — Figure decision is binary and asset-backed

`figure.required = true` when any `solution.step` refers to a spatial referent (a labelled point, a fold line, a region, a graph reading). If required, `asset_id` must resolve now; if it cannot, either (a) redraft the solution so no step is spatial, or (b) end with `future_defect`. `labels[]` is copied from the asset manifest, not typed by hand. On modify, prefer no figure unless the packet solution requires one.

## R6 — Register / phrase: must contain no

- syllabus reference (`syllabus`, `specification`, `learning objective`, `as defined in`, `under the definition`)
- course-position language (`you have learned`, `recall`, `remember`, `earlier`, `this topic`)
- tutor address (`let's`, `think about`, `try to`, `hint`, `can you`)
- item-about-itself language (`this question`, `the correct answer`, `option`, `distractor`)
- registration voice (`is recorded as`, `identity of the aim`, form-filling costumes)

Checked at REGISTER (mint) and again at MIQG (release gate) on phrasing.

## R7 — Weights

`weight_connection[h]` is assigned by the existing connection weigher in `systems/question_ingest/weight.py` (`weight_connection`): contributions sum to 1.0 ± 0.01, with use / idle text and role (`primary` / `support` / `thin`). Do **not** replace this with a step-count fraction (`|{steps : uses_hinge = h}| / |steps|`). Overlay / `cell.noul_rating` remains an admit threshold only and is never the stored weight under `hinges_used`. After support hinges are added, `hinge_given` must hold the largest contribution.

## R8 — Modify mode

The seed's form (item_type, n_options, ask shape) is preserved unless the cell forces a change. Content is rewritten from the map packet. Do not treat option-rationale-only tweaks that leave a form-filled stem as a successful modify.

## R9 — Freeze

On mint, `future_hash` is computed; any later change to `future` invalidates the run. On modify, the packet snapshot (unit ids + mx ids + extra hinge ids) is what the write was against; inventing new map claims after GROK is a new run.

---
