# T-MINT / T-MOD — JEV loop

Packet-first modify loads systems/modify/packet_modify.py on T-MOD. **MIQG is the only release gate** (TOP / release_gate PASS). Bank append is TOP-only via ank_gate.py.

Additive. T-MOD still modifies an existing session item. T-MINT **mints** a sitting item from a construct × hinge requirement.

## T-MINT

`schema/modify_requirement.v1.json`

```bash
export TTWIN_JEV_KEY_FILE="/path/to/JEV AI API Key.txt"   # or TTWIN_JEV_KEY
# optional writer:
export TTWIN_WRITER_KEY="..."
export TTWIN_WRITER_URL="https://api.moonshot.ai/v1/chat/completions"
export TTWIN_WRITER_MODEL="kimi-k3"

python3 jev_loop/run.py \
  --requirement jev_loop/examples/requirement.example.json \
  --out /tmp/t-mint-out

From TTwin: `python3 harness/modify/jev_loop/run.py …`
From TTwin-final: `python3 systems/modify/jev_loop/run.py …`
```

`--draft result.json` skips the writer. T-PLAN still runs. `abandon_cell` refuses unless `accept_neighbour`. G1–G8+G3b then G17 then unbiased classify (**TikZ in state when present**). When the result has TikZ, T-ISO-EXAMINER runs first and may inject `KEY_WRONG`.

Never commit keys. Never put `target_construct` in the classify state. Never put the packed key or `key_rationale` in the examiner state.

## T-MOD (V5 lock)

```bash
python3 jev_loop/tmod.py \
  --source source.json \
  --instruction "V5 rewrite" \
  --declared-delta "what changed in the TikZ" \
  --variation V5 \
  --figure-mode rewrite \
  --target-construct Ev.Co.3 \
  --draft result.json \
  --out /tmp/t-mod-out

# Deterministic gates only (no JEV):
python3 jev_loop/tmod.py --source source.json --draft result.json --gates-only --out /tmp/t-mod-gates
```

`--lbs-followup-of <prior_id>` is required before a stem may name a removed object (voltmeter 1, impala pathway).

## Pipeline

1. **Bind one map unit** — `unit_bind.py`. The aim must sit in that unit's `jev_taxonomy_zone`. Otherwise stop. No T-PLAN and no writer.
2. **T-PLAN** — JEV sees that unit's decision, law, zone, and one misconception. `abandon_cell` stops before the writer. The cell is not retargeted here.
3. **Writer** or `--draft`. The prompt carries the law as text that must not be copied, one wrong-answer pattern, and the review constraints (do not print the method, do not explain the phenomenon and then ask for it, no equal-time comparisons, full-sentence part answers).
4. **One repair** — if the stem copies an 8-word span of the unit law, one rewrite. No further loop.
5. **G1–G8** then **G3b** (stem-object ∈ TikZ nodes) **G3c** (label-to-stroke) **G3d** (declared delta vs diff).
6. **T-ISO-EXAMINER** — independent solve of stem+TikZ, blind of rationale and packed key. Disagreement → `KEY_WRONG`.
7. **G17** — live `systems/modify/miqg/miqg_cal.py`. Extra findings from 5–6 are injected; `scan()` still does not invent keys.
8. **T-JEV-CLASSIFY** — unbiased taxonomy. The aimed cell is not in the state. TikZ is included when present.
9. **G18** — TOP and noul ≥ 0.50. The admitted cell is kept when it is in the bound unit's zone (`PASS` or `PASS_ZONE`). A cell outside the zone is not stored. A miss sets `retry_same_prompt` false.

Trial 2026-09-21: G17 TOP was cheap; G18 failed closed on An.Co.3 / Ap.Pr.3 / Ev.Pr.4 sitting items. Figure-HOT sidecar skipped this lock; marble P/Q, capacitor V1, food-web impala are the regression tests in `tests/test_v5_lock.py`.

Do **not** auto-rewrite because noul is 0.44–0.49. Do **not** request Ev.Pr.4 as a sitting item; T-PLAN will `abandon_cell`.

## Env

| var | role |
|---|---|
| `TTWIN_JEV_KEY` / `TTWIN_JEV_KEY_FILE` | System One |
| `TTWIN_JEV_URL` | default `https://jev-ai.pro/api/v1/systemone` |
| `TTWIN_WRITER_KEY` / `TTWIN_WRITER_URL` / `TTWIN_WRITER_MODEL` | stem writer |

