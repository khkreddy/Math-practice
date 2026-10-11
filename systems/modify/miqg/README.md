# MIQG — only release gate for modify

G17 CAL-KNGOOD v2 grader used by T-MINT / T-MOD. `miqg_cal.py` is the sole release gate: **TOP** and `release_gate` **PASS** required to serve; bank append is TOP-only via `jev_loop/bank_gate.py`.

Keep: `miqg_cal.py`, `worked_solution.py`, `codes.json`. Repair scripts and trial reports live under `systems/modify_archive/miqg/`.
