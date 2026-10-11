#!/usr/bin/env python3
"""Mint middle-school science items for hinges with no JEV-pass question.

Uses the sanitized science map and the modify harness. Each wrong option is
bound to a map mx_id before the row is written. Admitted rows go to the
JEV-pass science bank. Held rows stay local.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TTWIN_ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(TTWIN_ROOT))

import bank_gate  # noqa: E402
import middle_schedule as ms  # noqa: E402

WAVE_SIZE = 2
STAGGER_S = 20
MINT_TIMEOUT_S = 900
SRC = "t-mint-science-gap"
PASS_BANK = TTWIN_ROOT / "data" / "questions" / "JEV-pass" / "middle_6_8" / "science.jsonl"
HELD_BANK = ms.SCIENCE_BANK
SKIP_PATH = HERE / "mint_learning" / "science_gap_skips.json"
WRITER_KEY_FILE = os.environ.get("TTWIN_WRITER_KEY_FILE") or r"C:\Users\Shanthi\Desktop\Deepseek API key.txt"
JEV_KEY_FILE = os.environ.get("TTWIN_JEV_KEY_FILE") or r"C:\Users\Shanthi\Desktop\JEV AI API Key.txt"

STRATEGIES = [
    "assertion-reason: item_type single_mcq. Write one Assertion sentence and one Reason sentence in the stem. The five options are only the standard relations: both true and the Reason explains the Assertion; both true but the Reason does not explain it; Assertion true and Reason false; Assertion false and Reason true; both false. answer.kind is single_letter.",
    "multi-select as a single key: item_type single_mcq. Put the claims in the stem as I, II, III. Options are combinations such as 'I and II' or 'I, III, and V'. Exactly one option is the full set of supported claims. Every other option adds at least one unsupported claim, and mx_option_map cites the mix-up of that claim. answer.kind is single_letter. Do not ask which statements are correct.",
    "multiple true-false: item_type three_statement. Three or four statements about the scene. answer.kind is statement_pattern with T and F. Do not ask which statements are correct. Each false statement cites its own mx_id in statement_mx_map.",
    "answer-plus-reason: item_type option_table. Each option is a claim followed by because and a reason. Wrong reasons come from the mix-up catalog.",
    "NOT-stem: single_mcq whose one question asks which claim does NOT fit the scene.",
    "two-tier: single_mcq. Each option states the result and the reason in one sentence, separated by a semicolon.",
    "figure: attach TikZ when a graph, ray, circuit, apparatus, or labelled diagram is what makes the options different. Otherwise use a concrete scene and single_mcq.",
]
FIGURE_WORDS = ("graph", "diagram", "circuit", "ray", "apparatus", "chart", "plot", "balance", "thermometer", "food web")


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_path() -> Path:
    path = HERE / "mint_learning" / "science_gap_campaign.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def log(msg: str) -> None:
    line = utc() + " " + msg
    with log_path().open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


def _key_line(path: str, prefix: str) -> str:
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(prefix):
            return line
    raise RuntimeError("key file has no usable key line")


def configure_env() -> None:
    os.environ["TTWIN_ADMIT_MIQG_TOP"] = "1"
    os.environ["TTWIN_JEV_KEY_FILE"] = JEV_KEY_FILE
    os.environ["TTWIN_WRITER_KEY"] = _key_line(WRITER_KEY_FILE, "sk-")
    os.environ["TTWIN_WRITER_URL"] = "https://api.deepseek.com/chat/completions"
    os.environ["TTWIN_WRITER_MODEL"] = "deepseek-flash"
    os.environ["TTWIN_WRITER_MAX_TOKENS"] = "16000"
    os.environ["TTWIN_WRITER_TIMEOUT"] = "180"


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def seeds_for(unit: dict, bank: list[dict]) -> str:
    grade = str(unit.get("grade"))
    picked = []
    for row in bank:
        if str(row.get("grade")) != grade:
            continue
        hinge = ((row.get("jev_taxonomy") or {}).get("hinge_id"))
        if hinge == unit.get("unit_id"):
            continue
        item = row.get("item") or {}
        stem = " ".join(str(item.get("stem") or "").split())
        if len(stem) < 40:
            continue
        tier = str((row.get("miqg") or {}).get("tier") or "")
        picked.append((0 if tier == "TOP" else 1, stem[:360]))
        if len(picked) >= 12:
            break
    picked.sort()
    lines = [text for _rank, text in picked[:2]]
    if not lines:
        return ""
    return "Quality seeds, shape only. Do not copy their wording or their hinge:\n" + "\n".join(
        f"- {text}" for text in lines
    )


def strategy_for(index: int, unit: dict) -> str:
    decision = (unit.get("decision") or "").lower()
    if any(word in decision for word in FIGURE_WORDS):
        base = STRATEGIES[-1]
    else:
        base = STRATEGIES[index % (len(STRATEGIES) - 1)]
    return base


SITTING_FIRST = ("An.Co.3", "An.Co.2", "Ap.Co.2", "Ap.Pr.2", "Ev.Co.3", "U.Co.2", "Ap.Pr.3", "An.Pr.2")


def _sitting_zone(zone: list[str]) -> list[str]:
    preferred = [cell for cell in SITTING_FIRST if cell in zone]
    rest = [cell for cell in zone if cell not in preferred and not str(cell).startswith("Cr.") and not str(cell).endswith(".4")]
    return preferred or rest or list(zone)


def science_units() -> list[dict]:
    science = json.loads(ms.SCIENCE_MAP.read_text(encoding="utf-8"))
    units = []
    for unit in ms.units_from_maps(science, {"hinges": []}):
        if unit.get("subject") != "science":
            continue
        copied = dict(unit)
        copied["zone"] = _sitting_zone(list(unit.get("zone") or []))
        units.append(copied)
    return units


def one_wave(units: list[dict], bank: list[dict], wave_i: int) -> str | None:
    by_hinge, by_cell = ms.occupancy(read_jsonl(PASS_BANK))
    skips = ms.load_skips(SKIP_PATH)
    picks = ms.next_picks(units, by_hinge, by_cell, skips, n=WAVE_SIZE)
    if not picks:
        log("WAVE no picks")
        ms.save_skips(skips, SKIP_PATH)
        time.sleep(60)
        return None
    by_id = {unit["unit_id"]: unit for unit in units}
    jobs = []
    stamp = utc().replace(":", "").replace("-", "")
    for offset, (uid, cell) in enumerate(picks):
        unit = by_id[uid]
        req = ms.requirement_for(unit, cell, f"sg-science-{stamp}-{offset}")
        seed = seeds_for(unit, bank)
        strategy = strategy_for(wave_i + offset, unit)
        req["intent"] = (
            "Middle-school science sitting item on this unit only. "
            "Aim at the named cell. Do not print the method or restate the law. "
            "Do not write 'a student asks', 'a student wants', 'a student must', "
            "'which statement is correct', or 'the learner'. "
            f"Format for this attempt: {strategy} "
            "Every wrong option cites a distinct mx_id from the catalog. "
            "answer.kind is required. "
            + seed
        )
        req["figure_mode"] = "add" if "TikZ" in strategy else "none"
        out = HERE / "mint_learning" / "runs" / req["requirement_id"]
        log(f"START {req['requirement_id']} {uid} {cell} {strategy.split(':', 1)[0]}")
        jobs.append((req, out, uid, cell))
    return _run_jobs(jobs, skips, units)


def _run_jobs(jobs, skips, units) -> str | None:
    procs = []
    env = os.environ.copy()
    for offset, (req, out, uid, cell) in enumerate(jobs):
        if offset:
            time.sleep(STAGGER_S)
        out.mkdir(parents=True, exist_ok=True)
        (out / "requirement.json").write_text(json.dumps(req, indent=2) + "\n", encoding="utf-8")
        cmd = [sys.executable, str(HERE / "run.py"), "--requirement", str(out / "requirement.json"), "--out", str(out)]
        procs.append((
            subprocess.Popen(cmd, cwd=str(HERE), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE),
            req, out, uid, cell,
        ))
    stop = None
    new_pass = []
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
        outcome, passed = _consume(trail, uid, cell, skips)
        log(f"RESULT {req['requirement_id']} {outcome}")
        if passed:
            new_pass.append(passed)
        if outcome in {"402", "WRITER_UNCONFIGURED"}:
            stop = outcome
    ms.save_skips(skips, SKIP_PATH)
    if new_pass:
        bank_gate.sync_manifest(TTWIN_ROOT)
        log("APPENDED " + ",".join(new_pass))
    return stop


def _stamp_miqg_pass(row: dict, hinge_id: str) -> dict:
    """MIQG TOP admits the row onto the hinge it was written for."""
    jt = dict(row.get("jev_taxonomy") or {})
    jt["schema"] = "ttwin.jev_taxonomy.v1"
    jt["hinge_id"] = hinge_id or jt.get("hinge_id")
    jt["admitted"] = True
    jt["admission_basis"] = "miqg_top"
    row["jev_taxonomy"] = jt
    design = dict(row.get("design") or {})
    design["admission"] = "miqg_top"
    design["hinge_id"] = jt.get("hinge_id")
    row["design"] = design
    return row


def _drop_held(ids: set[str]) -> None:
    if not ids or not HELD_BANK.is_file():
        return
    kept = []
    with HELD_BANK.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("id") in ids:
                continue
            kept.append(line if line.endswith("\n") else line + "\n")
    HELD_BANK.write_text("".join(kept), encoding="utf-8")


def promote_top_trails() -> list[str]:
    """Move every MIQG TOP item from this run into the JEV-pass bank."""
    promoted = []
    already = {row.get("id") for row in read_jsonl(PASS_BANK)}
    runs = HERE / "mint_learning" / "runs"
    if not runs.is_dir():
        return promoted
    PASS_BANK.parent.mkdir(parents=True, exist_ok=True)
    for path in sorted(runs.glob("sg-science-*/run.json")):
        try:
            trail = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        miqg = trail.get("miqg") if isinstance(trail.get("miqg"), dict) else {}
        if miqg.get("quality_tier") != "TOP" or miqg.get("release_gate") != "PASS":
            continue
        req = trail.get("requirement") if isinstance(trail.get("requirement"), dict) else {}
        row = bank_gate.bank_row_from_trail(trail, source=SRC, allow_multiformat_result=True)
        if row is None or row.get("id") in already:
            continue
        _stamp_miqg_pass(row, str(req.get("hinge_id") or ""))
        if bank_gate.append_eligible_row(PASS_BANK, row, allow_multiformat_result=True):
            already.add(row.get("id"))
            promoted.append(str(row.get("id")))
    if promoted:
        _drop_held(set(promoted))
        bank_gate.sync_manifest(TTWIN_ROOT)
    return promoted


def _consume(trail: dict, unit_id: str, cell: str, skips: dict) -> tuple[str, str | None]:
    blob = " ".join(str(trail.get(k) or "") for k in ("status", "refusal_reason", "error"))
    if "402" in blob or "Payment Required" in blob:
        return "402", None
    if "WRITER_UNCONFIGURED" in blob:
        return "WRITER_UNCONFIGURED", None
    row = bank_gate.bank_row_from_trail(trail, source=SRC, allow_multiformat_result=True)
    if row is not None:
        _stamp_miqg_pass(row, unit_id)
        PASS_BANK.parent.mkdir(parents=True, exist_ok=True)
        if bank_gate.append_eligible_row(PASS_BANK, row, allow_multiformat_result=True):
            return f"APPENDED {row.get('id')}", str(row.get("id"))
        return f"APPEND_REJECTED {row.get('id')}", None
    reason = str(trail.get("refusal_reason") or "")
    if trail.get("status") == "REFUSED" or "abandon_cell" in reason:
        n = ms.note_failure(skips, unit_id, cell)
        return f"REFUSED {reason[:180]} fails={n}", None
    n = ms.note_failure(skips, unit_id, cell)
    tier = (trail.get("miqg") or {}).get("quality_tier") if isinstance(trail.get("miqg"), dict) else None
    return f"NOT_BANKED tier={tier} status={trail.get('status')} fails={n}", None


def main() -> int:
    configure_env()
    units = science_units()
    empty = 0
    by_hinge, _by_cell = ms.occupancy(read_jsonl(PASS_BANK))
    for unit in units:
        if by_hinge.get(unit["unit_id"], 0) == 0:
            empty += 1
    promoted = promote_top_trails()
    log(
        f"CAMPAIGN science_units={len(units)} jev_pass_empty={empty} "
        f"writer=deepseek-flash gate=miqg_top promoted={len(promoted)}"
    )
    bank = read_jsonl(PASS_BANK) + read_jsonl(HELD_BANK)
    wave = 0
    while True:
        stop = one_wave(units, bank, wave)
        wave += 1
        if stop:
            log(f"FAILED {stop}")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
