# Pack construction audit

**Date:** 2026-10-06. **Status:** diagnosis only. No item was generated.
**Maps:** original files in `data/maps/jev/`, sanitized files in `data/maps/jev/sanitized/`, schema `ttwin.map_agent.v1`, commit `0f9e5ffa` on `main`.
**Harness:** `systems/modify/packet_modify.py` (`packet_for_row` → `facts_for_writer`), writer law `04_GROK_SLOT.md`, loop `01_WORKFLOW.md`.
**Evidence:** ten blind pair-audits by Opus 5.5 (international-exam standard; one pair held to IIT-JEE). Sanitized won 8. Original won 2. This note traces those two wins and states what a later change has to satisfy.

## 1. What the pack is for

A modify run loads one hinge and sends `facts_for_writer` to the writer. The writer is supposed to produce one item that identifies a misconception, a learning difficulty, or a failure of mastery, using the map and nothing invented beside it.

The item is supposed to be correct by construction in Lamport’s sense: the specification (which hinge, which demand, which key, which wrong answers, which map record each wrong answer comes from) is fixed before prose, and every later step preserves it. The writer phrases. The writer does not choose the science.

The current modify prompt does the opposite. `04_GROK_SLOT.md` asks the model, in one call, to invent the situation, the key, the wrong values, and which mix-up each option uses. Craft checks and MIQG run afterwards. That is generate-and-test. A failed check returns to the writer up to three times (`01_WORKFLOW.md` Step 8).

## 2. How a pack is built today

1. The projection (`systems/curriculum_harness/src/map_agent.py`, `_mixups`) keeps one mix-up per route with label-1 probability ≥ 0.70. It copies `wrong`. It copies `observable` and `confused` only when the sentence is real. It drops a score note (`JEV label-1 … is at least 0.70`) and two filler observables: “A question on this hinge draws the wrong choice this belief predicts.” and “The student states this everyday picture instead of the hinge mechanism.”
2. Stored order is: any surviving `observable` or `confused` first, then descending `p1`, then route name. A generic confused label counts as a surviving companion. See the sort at `_mixups`.
3. `packet_modify.load_packet` sends the first six mix-ups in that stored order (`all_mx[:6]`). The original-map path uses source order instead, and it reads `canonical_wrong_output` only. It does not read `cwo`.
4. The writer packet also carries decision, law, up to four boundaries, because, reasoning, not-yet, student default, student signals, scope, check, and the JEV cell code with its noul. It does not choose three distractors. It does not compute the key.

## 3. Root cause of the two original-pack wins

Both losses are selection. The sanitized hinge still held the sentence the auditor wanted. The six-record cap, fed by the projection’s sort, is what kept it out of the brief or put a weaker record first.

### 3.1 Grade 10 pH — `science/grade_10/ch_02/H012`, cell `Ap.Co.2`

Decision: apply pH thresholds to living systems and everyday environmental effects. Eight admitted mix-ups exist on both maps. Nothing in this set was deleted by projection.

| p1 | route | On sanitized map | In original brief (source order, first 6) | In sanitized brief (ranked, first 6) |
|---:|---|---|---|---|
| 0.92 | condition_omission | full | yes | yes |
| 0.92 | relationship_reversal | full | yes | yes |
| 0.92 | surface_feature_capture | full | yes | yes |
| 0.88 | term_substitution | full | yes | yes |
| 0.83 | everyday_replacement | wrong sentence kept; observable dropped as filler; confused kept as “pre-lesson everyday picture of the cause” | no (7th in source order) | yes (5th) |
| 0.78 | operation_confusion | wrong sentence only | no | no |
| 0.77 | scope_error | full | yes | yes |
| 0.73 | mechanism_conflation | full | yes (6th) | no (7th) |

The record Opus used to prefer the original brief is still on the sanitized hinge, at position 7:

- Wrong: “Rain with pH 5.2 is not acid rain because it fell far from factories and vehicles.”
- Observable: “Denies acid rain for low-pH samples from unpolluted regions and affirms it for city rain regardless of the measured pH.”
- Confused: “Cause of acid rain (fossil-fuel emissions) used as its defining test.”

What entered instead, because `p1` 0.83 outranks 0.73 once any companion remains:

- Wrong: “Eating too many sweets rots your teeth because sugar eats holes in them.”
- Confused: “pre-lesson everyday picture of the cause.”

That confused line is a template. The filler filter does not treat it as noise, because the filter only removes the two observable boilerplate strings and the score-note pattern. After the real observable was removed, the template label was enough to mark the record “specified.” The cap then dropped the acid-rain mechanism record.

Opus’s judgement follows from that swap. The sugar sentence does not test a pH threshold. The acid-rain sentence does. The original brief contained the acid-rain sentence only because source order happened to place it sixth and the everyday record seventh.

### 3.2 Grade 11 sliding filament — `science/grade_11/bio_ch_117/H005`, cell `U.Co.2`

The same six routes were sent from both maps. Every one of those six has a real wrong sentence, a real observable, and a real confused element. Two further records (operation_confusion at 0.90, everyday_replacement at 0.88) have a wrong sentence and empty companions. They are absent from both briefs: past the sixth source row on the original path, and after every companioned row on the sanitized path.

Opus called the briefs the same text in a different order and preferred the original order by a narrow margin. Original source order opens with the I-band / H-zone name swap and the “I band is narrow, therefore contracting” error. Those can be wrong geometry options. Sanitized order opens with the highest `p1` among companioned rows: Z-lines dragged inward (0.90), then the name swap (0.87), then “uniformly dark means contracted” (0.84). Opus judged the Z-line cause hard to use as a geometry option, and the darkness error as one that needs a micrograph the writer would have to invent.

No sentence was lost. `p1` order was treated as item priority. The writer prompt never says that position 1 is the distractor to use. The auditor assumed a writer walks the list from the top. That assumption is reasonable, and the harness never replaces it with a selection law.

### 3.3 What this is, and what it is not

The projection copied the pedagogical sentences. The pH mechanism record and all six sarcomere records are on the sanitized map. The loss is in the transfer from the hinge into the six-slot writer brief: rank by “any companion, then `p1`,” then truncate.

A related transfer bug runs the other way and is not one of these two wins. On the grade-6 condensation hinge, the original brief had six empty wrong-output fields because `mx_records` reads `canonical_wrong_output` and not `cwo`. The projection reads both, so the sanitized brief had the student sentences. Opus preferred that sanitized brief. Archive rows that store the belief only in `cwo` will keep losing it on the original path.

## 4. What Opus still found lacking in the winning packs

These remarks recurred across the ten pairs, including packs Opus preferred. They are properties of the brief the writer receives, not of which file it was loaded from.

1. **The demand is a code.** `An.Co.2`, `Ap.Co.2`, `U.Co.2` are sent with a 14-to-24-code zone list and a noul. The code is not glossed into the single thing the candidate must do. On kinetic energy the code reads as analysis while `operation` says calculate. The later classify step rejects a construct mismatch. The pack never gave the writer the demand in words.
2. **Six errors, three wrong options, no chooser.** The brief does not say which three mix-ups become options, which one is the best distractor for this cell, or which near-duplicates must not both be used. List order becomes a silent chooser.
3. **A boundary with no mix-up.** The strongest constraint is often ungrounded. Example: “10 percent of the kinetic energy is not 10 percent of the speed” had no error record that produces that mistake. The writer must invent the distractor. That breaks the rule that wrong answers come from the map.
4. **`not_yet` repeats `because`.** Several not-yet lines are the causal sentence with a prefix. They add no new failure mode.
5. **Generic signals and internal names.** “Cannot identify the chapter quantity…” and tokens such as `kinetic_energy_square_law` are not candidate-facing facts. A writer can print them.
6. **`check` is already an item.** Where a diagnostic ask and its accepted answer are both in the pack, the writer is invited to copy that item. On the photoelectric hinge the supplied check is a one-step comparison of a frequency with the threshold, which Opus judged below IIT-JEE standard.
7. **The law is several decisions at once.** The pH law holds body pH, acid rain, tooth decay, and soil. Nothing in the pack cuts that to one threshold. One clear idea is left to the model.
8. **Empty companions on a real wrong sentence.** A wrong sentence with no observable still forces the writer to invent how the error shows up. The everyday template and the childish “it stops when it gets tired” line remain available at senior level when their wrong sentence survived.
9. **The prompt demands a prerequisite-gap option the pack does not have.** `04_GROK_SLOT.md` says exactly one option is the missing-prior error. These ten packs had `prerequisite_gaps: []`. The specification given to the writer cannot be satisfied from the packet.

## 5. Is the pack helping correct-by-construction?

Partly, and at the wrong layer.

What already matches the intention:

- Decision, law, and boundaries are teacher-side and marked do-not-print.
- A mix-up that survives carries the student’s wrong sentence, and, when the archive had a real one, the behaviour and the confused idea.
- The zone and noul tell the harness whether this hinge may carry the cell. Neighbour attachment no longer fires on a missing zone.
- The mint path already fixes answer values before phrasing (`04_GROK_SLOT.md`, mint prompt). Grok is forbidden to invent map ids.

What the modify path still hands to free generation:

- Which of several clauses in the decision is the one idea.
- What the keyed value is. Nothing in the pack computes it from the law and a situation.
- Which three mix-ups are the wrong answers, and that each wrong value is what that mix-up produces in the same situation.
- The option-to-mix-up binding. The model is asked to return `mx_ids_used` after it has written the options. The binding is a claim, not an input.
- Feedback. The harness can fill `learning_state` and `evidence` from the packet after the values exist, but the values themselves were not fixed first.

Lamport’s bar is: state the invariant, then admit only those steps that preserve it. Bird–Meertens, as replayed by Satnam Singh (https://satnam6502.github.io/bird-meertens/, Lean derivation of Kadane from the obvious segment-sum specification), adds three habits:

- The specification is the obviously correct, possibly wasteful program. Every later line is the same function, proved equal, and itself runnable.
- Each step cites one law. There is no silent improvement.
- The agent does not supply the guarantee. The checked equality does.

Applied here, the obviously correct item is small and strict. An efficient writer prompt is a later line, equal to that specification, not a fresh invention.

### 5.1 Specification the pack should already satisfy

One modify item, before any prose:

- One hinge id. One construct id that is in `zone.admitted` with noul ≥ 0.50. If the cell is weak, the support hinge is chosen by the neighbour law and recorded. A missing zone does not invent a neighbour.
- One situation: the facts held fixed, taken from one mix-up’s observable (or from a boundary the mix-up actually uses). The situation is data, not a paragraph.
- Key = the value the law assigns to that situation. The key is a value of the same type as the wrong answers.
- Exactly three wrong values. Each is the value one mix-up assigns to that same situation. The three mix-ups have distinct confused ideas. Each cited mix-up has a non-empty wrong sentence. A template confused label does not count as a confused idea.
- The four values are distinct. No value paraphrases the law or the decision.
- If `prerequisite_gaps` is empty, no option has role `prerequisite_gap`. The prompt must not require one.
- `mx_ids_used` is an input to the writer, not a field the writer reports back.

Prose is allowed only after this record exists. The stem may add a scene. It may not change a value, add an option, or drop a cited mix-up. That is the same split the mint prompt already uses.

### 5.2 Laws worth installing, in derivation order

Each law is equality-preserving: the item still tests the same hinge and the same three errors. A later agent should implement these as checked steps, not as advice in a prompt.

1. **Companion filter (already started).** Drop score notes and the two filler observables. Also drop generic confused labels, including “pre-lesson everyday picture of the cause.” Keep the wrong sentence.
2. **Rank is not “any companion.”** A record with a real observable outranks a record whose only companion is a label that remained after the observable was stripped. `p1` breaks ties. This is the pH repair: the acid-rain mechanism record (full observable, p1 0.73) outranks the sugar record (template confused label, p1 0.83).
3. **Select three, do not truncate six.** The writer brief contains the three chosen mix-ups and no others. Near-duplicates (same confused idea, or wrong sentences that entail each other) collapse to one before the cap. The sarcomere repair is a stated choice of the three geometry errors, not a hope that list order matches what a writer will pick.
4. **One idea from a multi-clause decision.** If the law names several thresholds or several phenomena, bind the item to the clause the chosen mix-ups actually contradict. The other clauses stay out of the brief.
5. **Situation and values before prose.** Build the four answer values from the law and the three mix-ups. Refuse to call the writer when a value cannot be derived. That is the fold-scan step: the running result is carried forward, and the model is not asked to rediscover it.
6. **Phrase only.** The modify prompt matches the mint prompt: answer values are fixed, option roles are fixed, the model returns wording. `option.feedback` is copied from the cited mix-up’s wrong sentence and observable, not written as new claims about the learner.
7. **Gate checks equality, not taste.** MIQG remains the release gate for voice, leakage, and the Cambridge envelope. It should not be the first place that notices an option with no mix-up id, a prerequisite role with an empty gap list, or a key that is not the law’s value.

### 5.3 What not to copy from the article

The Kadane derivation is about algorithmic cost. Item generation does not need Horner’s rule, scan lemmas, or a Lean port as a first step. The transferable part is the shape: a specification that is obviously the right item, a short list of laws, and a writer step that cannot change the specification. A Lean proof of the laws can come after the laws exist as ordinary checks a test can fail.

## 6. Invariants a later patch can test

- For `science/grade_10/ch_02/H012`, the writer brief includes the mechanism-conflation record whose wrong sentence begins “Rain with pH 5.2 is not acid rain” and does not include the sugar-eats-holes record, unless a selection law explicitly chooses a tooth-decay situation and then uses only tooth-decay mix-ups.
- For `science/grade_11/bio_ch_117/H005`, the three distractors are chosen by a named rule and are the same three whichever file the hinge was loaded from. Order inside the brief is the selection order, not source order and not raw `p1` order.
- A writer prompt for a pack with `prerequisite_gaps: []` does not require a prerequisite-gap option.
- The construct code is accompanied by one sentence that states the demand, taken from the cell family and the operation, and the zone list is not dumped into the brief.
- Calling the writer with an underived key is a harness error, not a MIQG hold.

## 7. Files

- Projection sort and filler filter: `systems/curriculum_harness/src/map_agent.py`, `_kept_sentence`, `_mixups`.
- Six-record cap and archive field read: `systems/modify/packet_modify.py`, `mx_records`, `load_packet`.
- Writer contract: `systems/modify/grok_4_7/04_GROK_SLOT.md`.
- Loop: `systems/modify/grok_4_7/01_WORKFLOW.md`.
- Schema: `systems/curriculum_harness/schema/map_agent.v1.json` and `data/maps/jev/booklet_design/MAP_SANITIZATION_SPEC.md`.
