#!/usr/bin/env python3
"""Continuous middle-school science and maths mint.

Each wave asks the shipped mint entry for several under-covered units at once.
Only MIQG TOP rows with a ttwin.jev_taxonomy.v1 overlay are appended.
The process starts another wave when the current one finishes.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TTWIN_ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import bank_gate  # noqa: E402
import middle_schedule as ms  # noqa: E402
import unit_bind  # noqa: E402

WAVE_SIZE = 3
STAGGER_S = 25
MINT_TIMEOUT_S = 900
SRC = ms.SOURCE


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_path() -> Path:
    raw = os.environ.get("MIDDLE_MINT_LOG") or str(HERE / "mint_learning" / "middle_campaign.log")
    path = Path(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def log(msg: str) -> None:
    line = utc() + " " + msg
    with log_path().open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    if msg.startswith("FAILED") or msg.startswith("CAMPAIGN") or "APPENDED" in msg:
        print(line, flush=True)


def load_maps() -> list[dict]:
    science = json.loads(ms.SCIENCE_MAP.read_text(encoding="utf-8"))
    maths = json.loads(ms.MATHS_MAP.read_text(encoding="utf-8"))
    return ms.units_from_maps(science, maths)


def bank_rows() -> list[dict]:
    rows = []
    for path in (ms.SCIENCE_BANK, ms.MATHS_BANK):
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def ids_of(rows: list[dict]) -> set[str]:
    return {str(r.get("id")) for r in rows if isinstance(r, dict) and r.get("id")}


def write_census(rows: list[dict], units: list[dict], skips: dict, dest: Path) -> None:
    by_hinge, by_cell = ms.occupancy(rows)
    unit_ids = {u["unit_id"] for u in units}
    lines = [
        f"utc {utc()}",
        f"middle_rows {len(rows)}",
        f"units_with_zone {len(units)}",
        f"skipped_coordinates {sum(1 for v in skips.values() if int(v) >= ms.FAIL_LIMIT)}",
    ]
    hinge_counts = Counter()
    for uid in unit_ids:
        hinge_counts[by_hinge.get(uid, 0)] += 1
    lines.append("hinges_by_item_count " + " ".join(f"{k}:{hinge_counts[k]}" for k in sorted(hinge_counts)))
    cell_totals = Counter()
    for (_hinge, cell), n in by_cell.items():
        if _hinge in unit_ids:
            cell_totals[cell] += n
    lines.append("cells " + " ".join(f"{c}:{cell_totals[c]}" for c, _n in cell_totals.most_common(24)))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def hard_stop(trail: dict) -> str | None:
    blob = " ".join(
        str(trail.get(k) or "")
        for k in ("status", "refusal_reason", "error", "classify_error", "repair_error")
    )
    if "402" in blob or "Payment Required" in blob:
        return "402"
    if "WRITER_UNCONFIGURED" in blob:
        return "WRITER_UNCONFIGURED"
    return None


def consume(trail: dict, unit_id: str, cell: str, skips: dict) -> str:
    stop = hard_stop(trail)
    if stop:
        return stop
    reason = str(trail.get("refusal_reason") or "")
    if trail.get("status") == "REFUSED" or reason.startswith("AIM_NOT_IN_ZONE") or "abandon_cell" in reason:
        n = ms.note_failure(skips, unit_id, cell)
        return f"REFUSED {reason[:180]} fails={n}"
    item = trail.get("item") if isinstance(trail.get("item"), dict) else {}
    law = ""
    bound = trail.get("unit_bind") if isinstance(trail.get("unit_bind"), dict) else {}
    # law check uses the stem only when the trail recorded a unit
    if unit_bind.procedure_leaked(str(item.get("stem") or ""), str(bound.get("law") or law)):
        n = ms.note_failure(skips, unit_id, cell)
        return f"LAW_COPIED fails={n}"
    row = bank_gate.bank_row_from_trail(trail, source=SRC)
    if row is None:
        n = ms.note_failure(skips, unit_id, cell)
        tier = (trail.get("miqg") or {}).get("quality_tier") if isinstance(trail.get("miqg"), dict) else None
        return f"NOT_BANKED tier={tier} status={trail.get('status')} fails={n}"
    bank = ms.SCIENCE_BANK if row.get("subject") == "science" else ms.MATHS_BANK
    if not bank_gate.append_eligible_row(bank, row):
        n = ms.note_failure(skips, unit_id, cell)
        return f"APPEND_REJECTED {row.get('id')} fails={n}"
    return f"APPENDED {row.get('id')} g18={(trail.get('g18') or {}).get('status')}"


def one_wave(units: list[dict], wave_i: int) -> str | None:
    rows = bank_rows()
    by_hinge, by_cell = ms.occupancy(rows)
    skips = ms.load_skips()
    picks = ms.next_picks(units, by_hinge, by_cell, skips, n=WAVE_SIZE)
    if not picks:
        log("WAVE no picks; every remaining coordinate is skipped")
        ms.save_skips(skips)
        time.sleep(60)
        return None
    by_id = {u["unit_id"]: u for u in units}
    before = ids_of(rows)
    jobs = []
    stamp = utc().replace(":", "").replace("-", "")
    for offset, (uid, cell) in enumerate(picks):
        unit = by_id[uid]
        req = ms.requirement_for(unit, cell, f"ms-{unit['subject']}-{stamp}-{offset}")
        out = HERE / "mint_learning" / "runs" / req["requirement_id"]
        log(f"START {req['requirement_id']} {uid} {cell}")
        jobs.append((req, out, uid, cell))
    return _run_jobs(jobs, before, skips, units)


def _run_jobs(jobs, before, skips, units) -> str | None:
    procs = []
    for offset, (req, out, uid, cell) in enumerate(jobs):
        if offset:
            time.sleep(STAGGER_S)
        out.mkdir(parents=True, exist_ok=True)
        (out / "requirement.json").write_text(json.dumps(req, indent=2) + "\n", encoding="utf-8")
        cmd = [sys.executable, str(HERE / "run.py"), "--requirement", str(out / "requirement.json"), "--out", str(out)]
        procs.append((subprocess.Popen(cmd, cwd=str(HERE), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE), req, out, uid, cell))
    results = []
    stop = None
    for proc, req, out, uid, cell in procs:
        try:
            _stdout, stderr = proc.communicate(timeout=MINT_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            trail = {"status": "TIMEOUT", "refusal_reason": "mint timeout"}
        else:
            trail_path = out / "run.json"
            if trail_path.is_file():
                try:
                    trail = json.loads(trail_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    trail = {"status": "NO_TRAIL", "refusal_reason": (stderr or "")[-300:]}
            else:
                trail = {"status": "NO_TRAIL", "refusal_reason": (stderr or "")[-300:]}
        outcome = consume(trail, uid, cell, skips)
        log(f"RESULT {req['requirement_id']} {outcome}")
        results.append(outcome)
        if outcome in {"402", "WRITER_UNCONFIGURED"}:
            stop = outcome
    ms.save_skips(skips)
    after = ids_of(bank_rows())
    new_ids = sorted(after - before)
    if new_ids:
        bank_gate.sync_manifest(TTWIN_ROOT)
    census = Path(os.environ.get("MIDDLE_CENSUS") or str(log_path().parent / "bank-census.txt"))
    write_census(bank_rows(), units, skips, census)
    log("WAVE " + " | ".join(results) + " new=" + ",".join(new_ids[:8]))
    return stop


def main() -> int:
    units = load_maps()
    log(f"CAMPAIGN units={len(units)} wave_size={WAVE_SIZE}")
    write_census(bank_rows(), units, ms.load_skips(), Path(os.environ.get("MIDDLE_CENSUS") or str(log_path().parent / "bank-census.txt")))
    while True:
        stop = one_wave(units, 0)
        if stop:
            log(f"FAILED {stop}")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
