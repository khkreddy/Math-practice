# 04_GROK_SLOT

Grok composes candidate-facing prose for a reader. It must not author the evidence the gate checks (map units, Mx, keys). On **modify**, the input is the map intelligence packet (`09_PACKET_MODIFY.md` / `facts_for_writer`). On **mint**, the input is the registered future rendered below. Either way: compose the stem; do not print registration rows or map law verbatim.

Grok receives no chat history. Reject reasons from prior attempts may be appended.

## Modify prompt (current law — packet-first)

Compose ONE Cambridge past-paper style MCQ from this intelligence packet.
The packet is teacher-side only. Do not quote decision/law sentences into the stem.
Rules:
- Concrete situation from the unit facts (numbers, named substances, labelled objects, a short scene).
- Exactly one ask. Key must be entailed by those stem facts alone.
- Options are alternative ANSWERS a candidate would give (values/claims), not fault labels.
- Use misconceptions in misconceptions_mx as wrong-answer pathways; phrase the wrong VALUE each produces. The packet lists every mix-up on the hinge. Choose the pathways the item needs. Do not treat a border, a score, or list position as a sign that another mix-up was withheld.
- When probe.text is present, you may stage the item in that situation. It was designed for this request and scored against one border. The key is the mastered resolution of the probe. A misconceptions_mx border is the limit that mix-up's wrong option must cross. Do not print the probe or the border. Do not add a wrong option from a mix-up that is not in the packet.
- When the center unit has situation_boundary, that sentence names the boundary most mix-ups produce. The other mix-ups remain available.
- Exactly ONE option must be a prerequisite-gap wrong answer (what you get if a listed gap is missing).
- Cambridge voice. No tutor talk, no syllabus talk, no 'which claim follows', no 'X is recorded as Y', no 'identity of the aim', no 'which statement is correct'.
- Figure only if essential; prefer no figure.
- Keep the same rough form: [item_type] with [n_options] options.
- seed_form_hint_ask_shape_only shows the SHAPE of what was asked; do not rebuild by splicing old prose.

PACKET:
[json.dumps(writer_packet)]

Return JSON only:
{"stem":"","options":{"A":"","B":"","C":"","D":""},"key":"A",
 "option_roles":{"A":"key","B":"misconception","C":"misconception","D":"prerequisite_gap"},
 "mx_ids_used":["..."],"facts_used":["short concrete fact 1","fact 2"]}

## Mint prompt (registered future)

Write the candidate-facing text for one Cambridge examination item. The content is fixed; you compose the wording.

Command word: [single_ask.command_word]
Ask: [single_ask.target]
Marks: [single_ask.marks]
Format: [format]
Figure present: [figure.required]  Labels available: [figure.labels joined by ", "]
Given facts the candidate may be told: [figure.facts / bound map facts — not old-stem slices]
Answer values (keep this order, do not add or remove):
  1. [options[0].value]
  2. [options[1].value]
  3. [options[2].value]
  4. [options[3].value]
Previous rejections: [reject_reasons or "none"]

Rules:
- You may write one situation sentence plus exactly one question (ending with `?`), or a single imperative beginning with the command word. Not two asks. Not a syllabus/tutor sentence. Not a stem that states the key.
- Do not state or paraphrase any answer value in the stem.
- Use only the labels listed. Do not refer to a figure if "Figure present" is false.
- No reference to a syllabus, course, lesson, or to the reader's prior learning. No second person except within the imperative.
- Option text must be a phrasing of the given value and nothing more. Options must be the same answer-type as the key.
- Do not print registration templates (`referent | attribute | value` rows) into the stem.

Return JSON only:
{"stem": "", "options": ["", "", "", ""], "figure_caption": "", "answer_line": ""}

For non-mcq formats the `Answer values` block is replaced by `Answer form: [mark_scheme summary]` and `options` is returned as `[]`.

## Fields Grok returns

| Field | Constraint enforced at gate |
|---|---|
| `stem` | situation optional + one ask (A1); no key equivalent (A2); no figure reference unless required (A3, B5); lexicon (B1); command word or trailing `?` (B4); no registration / syllabus voice |
| `options` | count matches form / future (A4); each option answers the ask (B2); wrong options map to Mx or one prerequisite gap |
| `option.feedback` (post-value, harness/writer) | On each wrong option after the value is fixed: `{learning_state, evidence, source}` from the packet Mx or prerequisite gap for that option (`OPTION_FEEDBACK_FIELD`). Not invented by Grok as free prose about the learner. |
| `figure_caption` | empty unless figure required; labels only from asset (B5) |
| `answer_line` / `key` | consistent with keyed option |

## What Grok never does

Choose or invent map unit ids; invent Mx ids not in the packet; choose or reorder answers beyond the returned options; add a "none of these"; supply a key that is not entailed; name hinges/weights as student-facing text; decide admission; write `gate.top`; edit the packet or `future`. Any returned field outside the allowed set is discarded. No Grok output is ever read back into the map packet.

---
