# Modify harness (packet-first)

Copy of the TTwin-final modify harness (`systems/modify`) as of 2026-10-11. Run logs under `jev_loop/mint_learning/` were not copied. Maps are not in this repo: `unit_bind.py` reads `data/maps/jev/sanitized` at the repository root. Keys stay in the environment. Never commit keys.

**This folder is the only current modify harness.** Packet-first modification is the law (`grok_4_7/09_PACKET_MODIFY.md`).

- The minted item is a **seed** (form + ask shape).
- The writer receives the **map packet** (units, Mx, prerequisite gaps, JEV cell).
- Extra neighbour hinges are added by the harness when the given hinge cannot carry the cell.
- **Grok** composes the question from that packet.
- **MIQG** (`miqg/miqg_cal.py`) is the only release gate: **TOP** / `release_gate` **PASS** required to serve or append to the bank.

**Archi-mint.** When the modify harness revisits an older minted item, `archi_mint.commit_revisit` (hooked from `upgrade_top/run_batch.write_row_back`) copies the pre-revisit minted row into `data/archi-mint/<same relative bank path>.jsonl`. Served-corpus loaders only read under `data/questions` (explicit lists, `glob("*/*.jsonl")`, or `rglob` within that root), so `data/archi-mint/` is outside the live tree and is not served. On TOP+PASS the main bank keeps only the new TOP row; on a non-TOP revisit the older minted row is archived and removed from the main bank (failed drafts are not left behind). Cambridge and other harvested rows (no `__tmod_` / `exp_mh` / `ms_sci_th` / `ms_math_th` id markers, no `*_grade_NN_*` T-MINT id, and no `design` block) are never archived or removed. Unrevisited minted items stay in the main bank until a revisit happens.

Evidence (rectified mean 3.92 vs Cambridge 3.23): `systems/modify_archive/grok_4_7/trial_500/`. Older form-filling trials and multi-hinge wave trees live under `systems/modify_archive/`.

| Path | Role |
|---|---|
| `packet_modify.py` | Load map packet + writer facts; report if extra hinge required |
| `archi_mint.py` | Archive pre-revisit minted rows under `data/archi-mint/`; TOP-only keep in live bank |
| `grok_4_7/` | Current law: workflow, drafting, Grok slot, packet modify |
| `jev_loop/` | Live mint (`run.py`) and modify (`tmod.py`) runtime; `bank_gate.py` (TOP-only append) |
| `miqg/` | Release gate (`miqg_cal.py`, `worked_solution.py`, `codes.json`) |
| `schema/` | Packet / requirement / result JSON schemas |

Keys stay in the environment (`TTWIN_JEV_KEY` / `TTWIN_WRITER_KEY`). Never commit keys.

```bash
python3 systems/modify/jev_loop/run.py \
  --requirement systems/modify/jev_loop/examples/requirement.example.json \
  --out /tmp/t-mint-out

python3 systems/modify/jev_loop/tmod.py \
  --source source.json --draft result.json --gates-only --out /tmp/t-mod-gates
```
