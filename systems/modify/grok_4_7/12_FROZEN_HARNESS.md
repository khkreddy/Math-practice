# Frozen modify harness

**Status:** the workflow is T-MINT, then T-MOD.

T-MINT writes the situation and the expected answer from the hinge packet, from a situation the user supplied, or from a situation that is not already on the hinge. The expected answer must be the result this stem requires; an independent solve that never sees the proposed key must match it, or T-MINT refuses. T-MOD does not write distractors until the same key check passes. The phrase checks in `11_FROZEN_PHRASE_SPEC.md` still apply to T-MINT's stem. T-MOD does not cite stored mix-up ids.

## What stays frozen

- One mix-up id, `{unit_id}/MX_{route}`. Neighbour mix-ups are not citable.
- The legal set is checked after the item exists. A missing, foreign, or repeated citation fails.
- The release gate is MIQG. Only tier TOP and release_gate PASS is an admission.
- Most items are rejected. A rejected item stays available for a person to check.
- JEV does not admit or fail an item.
- A passing trail still carries `release.human_hold` and does not enter the pass bank by itself.

## What was added for the failure rate

Rejecting most items is the bar. The failure rate is handled by one repair pass, not by a looser gate.

1. Every run records the gate decision and a plain-language explanation: the tier, the release gate, the decisive reason, each major code with its quoted text, the harness refusal, and the reviewer note.
2. An item that is not TOP and PASS is sent through T-MOD once more. T-MOD keeps the sitting stem and key, tests the eight routes on that situation, and writes the wrong options from the routes that pass. It does not paste stored mix-up sentences. If two routes reach the same result, the repair keeps that result once, without the sentence that explains the route. The instruction still carries the gate record and the standing repair rules: complete sentences that name the actor, no fact the stem does not state, four options when a fifth would be weak, exactly one key, no shared logic with the key, no border text.
3. The second decision is recorded the same way. If it is still not TOP, the item stays rejected. There is no third automatic pass.
