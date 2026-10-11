# 01_WORKFLOW

One loop. `hinges_used` has length 1 or more; every step iterates over it identically.

**Modify path (current law):** load the map intelligence packet for the seed row first (`systems/modify/packet_modify.py` / `09_PACKET_MODIFY.md`). Do not slice the old stem into givens. Mint path still uses REGISTER below.

## Step 0 — Intake

Input: `{mode: mint|modify, hinge_given, cell, existing_item_id?}`.

If `mode = modify`:
- Load the existing item as a **seed** only (form + ask-shape hint).
- Call `packet_for_row(row)` → map units, Mx, prerequisite gaps, JEV cell, and whether neighbour hinges are required.
- Empty packet → abandon (`empty_packet`); do not invent triples from the old stem.
- A modify that changes the keyed answer type or figure requirement beyond the seed form may be re-classed as `mint` with `supersedes = existing_item_id`.

If `mode = mint`: proceed with `hinge_given` / `cell` as today.

## Step 1 — JEV_BIND (mint; also used when modify adds support hinges)

```
zone      = hinge_unit(hinge_given).admitted_zone_at_bind
in_zone   = cell ∈ zone
overlay   = overlay(cell, hinge_given)
admitted  = overlay.noul_fit ≥ 0.5
            AND overlay.construct_state ∈ {LIVE, FRAGILE, REDIRECTED}
```

| in_zone | admitted | accept_neighbour | Result |
|---|---|---|---|
| T | T | – | `ADMITTED`, `hinges_used = [hinge_given]` |
| T | F | – | weak cell → Step 1b (support hinges), then retry Step 1; abandon only if no honest support |
| F | – | T | go to Step 1a |
| F | – | F | `abandon_cell`, reason `out_of_zone` |

A **weak cell** is one that is in zone but overlay noul under 0.5, or one where the single given hinge cannot carry the requested cell. Weak cells do not abandon immediately. On modify, `packet_modify.cell_needs_support` decides whether neighbour hinges are added into the packet (same idea as Step 1b).

### Step 1a — Neighbour (G18 PASS_NEIGHBOUR)

```
n = T_PLAN(hinge_given).likely_collapse.construct_cell
if n is null: abandon_cell, reason no_collapse_cell
cell ← n ; rerun Step 1 with cell = n ; if ADMITTED → status ADMITTED_NEIGHBOUR
```

No other source of a neighbour is permitted. `hinges_used` still begins with `hinge_given`.

### Step 1b — Support hinges

Support hinges are added in two cases:

1. **Weak cell** (in zone, overlay noul under 0.5, or the given hinge alone cannot carry the cell): candidates from `map.adjacent(hinge_given)` that can honestly support the cell. Retry Step 1 with the enlarged `hinges_used`. Abandon only when no honest support hinge exists (`abandon_cell`, reason `no_support_hinge`). On modify, neighbours are centered on the given hinge and recorded as `extra_hinge_ids` on the packet.
2. **Entailment gap** (mint registration in Step 3 cannot produce `entail_trace` with `hinges_used` alone): same neighbour pool, filtered to those with positive connection toward the registered solution. Each added hinge is recorded with `added_reason = entail_gap:<step_id>` (weak-cell supports use `added_reason = weak_cell_support`).

`hinge_given` always keeps the largest single `weight_connection` contribution after weighing.

## Step 2 — Format decision

```
if key is a spatial construction, an ordering, a derivation, or a value with a required unit:
    format ∈ {construct, order, short_response, numeric}
else:
    format = mcq
```
Recorded as `format` with `format_reason`. On modify, prefer the seed's item_type / n_options from the packet `form` block unless the cell forces a change.

## Step 3 — Packet (modify) or REGISTER (mint)

### Modify — packet is the content

No stem-slicing registration. The writer input is `facts_for_writer(packet)`:
unit decisions/laws/every boundary, every Mx pathway on those hinges, every prerequisite gap, JEV cell, seed ask-shape hint.
Teacher-side map text must not be copied verbatim into the stem.

### Mint — REGISTER (per 03_DRAFTING)

For each `h` in `hinges_used`:
- `solution.steps[*]` that depend on `h` carry `uses_hinge = h.id`.
- `weight_connection[h]` is assigned by the existing connection weigher in `systems/question_ingest/weight.py` (contribution sums to 1; use / idle / role). Not a step-count fraction. Overlay noul is an admit threshold only and is never the stored weight.

Then fix `single_ask`, `key`, `entail_trace`, `options` (mcq) or `mark_scheme` (other formats), `figure`.

REGISTER closes when the mint future record is complete. A `future_hash` is computed over `future`.

## Step 4 — GROK (04_GROK_SLOT)

One call. Input is the **packet** (modify) or the future rendered to the fixed prompt (mint). Output is `phrasing`. Grok composes prose for a reader; it does not author the map evidence MIQG checks.

## Step 5 — Craft checks (rewrite-only fatals)

A1 ask count · A2 key leakage · A3 figure availability · A4 option cardinality/identity.

Fail → Step 8 with `repair_mode = REWRITE`.

## Step 6 — Craft checks (top-blocking)

B1 lexicon · B2 option-answers-ask · B3 entailment preserved (map/packet facts, not registration-string reprint) · B4 command word · B5 figure references.

## Step 7 — Unbiased classify + MIQG release

JEV classify (existing mint/tmod path) receives stem and options only — no target cell. Mismatch on construct/ask-type blocks top.

**MIQG** (`systems/modify/miqg/miqg_cal.py`) is the only release gate. Serve / bank append require `quality_tier == TOP` and `release_gate == PASS`. Meta language and stacked tutorial conclusions are hard holds. `KNOWN_GOOD_ENVELOPE` cannot restore TOP after a MIQG hold.

## Step 8 — REPAIR

- `REWRITE`: return to Step 4 with `attempt += 1` and the failed check ids appended to the Grok prompt's `reject_reasons`. Max 3 attempts.
- Any repair output re-enters Step 5 in full, then MIQG again. There is no partial re-grade.
- A repair may not invent map triples from the old stem. If the packet itself is empty/defective, the run ends with `future_defect` / `empty_packet` and no item stored.

## Step 9 — STORE

Write `R`. Servable only when MIQG is TOP / PASS (and craft + classify checks above did not hold).

---
