#!/usr/bin/env python3
"""Repair all DeepSeek science-gap admitted items using reviewer notes and chemistry gold.

Runs unattended. Stop by writing mint_learning/science_gap_repair_STOP.
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TTWIN_ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(TTWIN_ROOT))

import run as tmint  # noqa: E402
from combination_key import collapse_multiselect  # noqa: E402
from unit_bind import MAP_DIR, MAP_FILES, mx_records_of  # noqa: E402

WRITER_KEY_FILE = os.environ.get("TTWIN_WRITER_KEY_FILE") or r"C:\Users\Shanthi\Desktop\Deepseek API key.txt"
PASS_BANK = TTWIN_ROOT / "data" / "questions" / "JEV-pass" / "middle_6_8" / "science.jsonl"
CHEM_PASS = TTWIN_ROOT / "data" / "questions" / "JEV-pass" / "senior_11_12" / "chemistry.jsonl"
CHEM_HELD = TTWIN_ROOT / "data" / "questions" / "senior_11_12" / "chemistry_addqs_held.jsonl"
REVIEW_LOG = TTWIN_ROOT / "systems" / "review_app" / "reviews.jsonl"
PROGRESS = HERE / "mint_learning" / "science_gap_repair_progress.jsonl"
ORIGINALS = HERE / "mint_learning" / "science_gap_repair_originals.jsonl"
LOG = HERE / "mint_learning" / "science_gap_repair.log"
STOP = HERE / "mint_learning" / "science_gap_repair_STOP"
PID = HERE / "mint_learning" / "science_gap_repair.pid"
FAIL_LIMIT = 2

KEEP_EXAMPLE_ID = "science_grade_07_science-grade_07-ch_07-H010__sg-science-20261007T151037Z-0"

STANDING = """Repair standing rules from human review, after comparing DeepSeek science items with the chemistry ingest gold set (499 admitted + 560 held):
1. Gold items use a short concrete stem and mutually exclusive options that all answer the same asked quantity. Every option and every statement must follow from the stem scene.
2. No claim, statement, or option may contradict a fact given in the stem. If a stem reports an observation, later claims must not deny that observation.
3. Wrong options must be clearly false in this scene. They must not also be a valid key. Two options must not encode the same logic.
4. Option and statement text must be complete, unambiguous sentences. Name the actual substances, objects, and observations. Do not write vague words such as 'the material'.
5. A statement that has no relation to the stem is a bad design and must be rewritten or dropped.
6. Keep the same hinge, keep distinct map mx_id citations on every wrong option or false statement, and keep a complete worked_solution whose result equals the keyed option text. Steps must contain the word therefore and must not quote the keyed option.
7. Keep the original item_type. Do not reframe a scene as assertion-and-reason unless the original item already is that type.
8. Combination / multi-select items must keep the numbered claims in the QUESTION. If options are sets such as 'I and II' or 'I, II, and III', the stem must contain: 'Which set of these claims is supported: I ...; II ...; III ...?' Never leave roman-set options without those claim sentences.
9. Keep statements[] for three_statement / true-false bundles. Do not delete claims when rewriting language.
"""


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = utc() + " " + msg
    with LOG.open("a", encoding="utf-8") as handle:
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


def opt_text(val) -> str:
    if isinstance(val, dict):
        return str(val.get("text") or val.get("value") or "").strip()
    return str(val or "").strip()


def gold_slim(row: dict) -> dict | None:
    item = row.get("item") if isinstance(row.get("item"), dict) else {}
    stem = str(item.get("stem") or "").strip()
    if len(stem) < 40:
        return None
    opts = item.get("options")
    packed = []
    if isinstance(opts, dict):
        for letter, val in opts.items():
            packed.append({"id": str(letter), "text": opt_text(val)})
    elif isinstance(opts, list):
        for i, val in enumerate(opts):
            if isinstance(val, dict):
                packed.append({"id": str(val.get("id") or chr(65 + i)), "text": opt_text(val)})
            else:
                packed.append({"id": chr(65 + i), "text": str(val)})
    if len(packed) < 3:
        return None
    assess = item.get("assessment") if isinstance(item.get("assessment"), dict) else {}
    key = str(assess.get("mcq_key") or (item.get("answer") or {}).get("letter") or "")
    return {
        "stem": stem[:420],
        "options": packed[:6],
        "key": key,
        "item_type": item.get("item_type") or row.get("item_type"),
    }


def load_gold() -> list[dict]:
    out = []
    for path in (CHEM_PASS, CHEM_HELD):
        for row in read_jsonl(path):
            if path == CHEM_PASS:
                src = str((row.get("design") or {}).get("source") or "")
                qid = str(row.get("id") or "")
                if src != "addqs" and not qid.startswith("addqs:"):
                    continue
            slim = gold_slim(row)
            if slim:
                out.append(slim)
    return out


def load_reviews() -> dict[str, dict]:
    latest: dict[str, dict] = {}
    if not REVIEW_LOG.is_file():
        return latest
    for rec in read_jsonl(REVIEW_LOG):
        qid = str(rec.get("id") or "")
        if qid:
            latest[qid] = rec
    return latest


def load_progress() -> dict[str, str]:
    done = {}
    if not PROGRESS.is_file():
        return done
    for rec in read_jsonl(PROGRESS):
        qid = str(rec.get("id") or "")
        if qid:
            done[qid] = str(rec.get("status") or "")
    return done


def note_progress(rec: dict) -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    with PROGRESS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")


def science_targets() -> list[dict]:
    rows = []
    for row in read_jsonl(PASS_BANK):
        qid = str(row.get("id") or "")
        src = str((row.get("design") or {}).get("source") or "")
        if "sg-science-" in qid or src == "t-mint-science-gap":
            rows.append(row)
    return rows


def map_units() -> dict[str, dict]:
    path = MAP_DIR / MAP_FILES["science"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for row in doc.get("hinges") or doc.get("units") or []:
        if isinstance(row, dict) and row.get("unit_id"):
            copied = dict(row)
            copied["mx_records"] = mx_records_of(row)
            out[str(row["unit_id"])] = copied
    return out


def hinge_of(row: dict) -> str:
    jt = row.get("jev_taxonomy") if isinstance(row.get("jev_taxonomy"), dict) else {}
    design = row.get("design") if isinstance(row.get("design"), dict) else {}
    return str(jt.get("hinge_id") or design.get("hinge_id") or "")


def option_blob(item: dict) -> str:
    opts = item.get("options")
    parts = []
    if isinstance(opts, dict):
        vals = opts.values()
    elif isinstance(opts, list):
        vals = opts
    else:
        vals = []
    for val in vals:
        parts.append(opt_text(val))
    return " ".join(parts)


def looks_combination(item: dict) -> bool:
    if item.get("combination_key"):
        return True
    blob = option_blob(item)
    return bool(re.search(r"\bI\b.*\bII\b", blob)) and (
        "only" in blob.lower() or " and " in blob.lower() or "," in blob
    )


def has_numbered_claims(item: dict) -> bool:
    stem = str(item.get("stem") or "")
    if re.search(r"\bI[\s:.\)]", stem) and "II" in stem:
        return True
    if item.get("statements"):
        return True
    ck = item.get("combination_key") if isinstance(item.get("combination_key"), dict) else {}
    return bool(ck.get("claims"))


def standing_notes(reviews: dict) -> str:
    bits = []
    seen = set()
    for rec in reviews.values():
        note = str(rec.get("note") or "").strip()
        if not note or note in seen:
            continue
        seen.add(note)
        bits.append("- [" + str(rec.get("verdict") or "") + "] " + note)
    return "\n".join(bits[:20])


def needs_rework(row: dict, rec: dict) -> bool:
    qid = str(row.get("id") or "")
    if qid == KEEP_EXAMPLE_ID:
        return False
    item = row.get("item") if isinstance(row.get("item"), dict) else {}
    verdict = str((rec or {}).get("verdict") or "")
    note = str((rec or {}).get("note") or "").strip()
    collection = str((rec or {}).get("collection") or "")
    if collection == "science_repair" and verdict in ("fix", "drop") and note:
        return True
    if looks_combination(item) and not has_numbered_claims(item):
        return True
    return False


def slim_item(item: dict) -> dict:
    keep = (
        "stem",
        "item_type",
        "options",
        "statements",
        "answer",
        "mx_option_map",
        "statement_mx_map",
        "worked_solution",
        "combination_key",
        "rows",
        "tikz",
        "tables",
    )
    return {k: item.get(k) for k in keep if item.get(k) not in (None, [], {})}


def repair_prompt(
    row: dict,
    gold: list[dict],
    note: str,
    unit: dict,
    *,
    notes: str = "",
    keep_example: dict | None = None,
    original: dict | None = None,
) -> str:
    item = row.get("item") if isinstance(row.get("item"), dict) else {}
    samples = random.sample(gold, k=min(3, len(gold))) if gold else []
    mx = []
    for rec in (unit.get("mx_records") or [])[:12]:
        if not isinstance(rec, dict):
            continue
        packed = {
            "mx_id": rec.get("mx_id"),
            "route": rec.get("route"),
            "wrong": rec.get("wrong"),
            "confused": rec.get("confused"),
            "observable": rec.get("observable"),
        }
        border = rec.get("border") if isinstance(rec.get("border"), dict) else {}
        if border.get("text"):
            packed["border"] = border.get("text")
        mx.append(packed)
    extra = ""
    if notes:
        extra += "\n\nRecent reviewer notes (apply even if written on another item):\n" + notes
    if keep_example:
        extra += (
            "\n\nReviewer-approved science repair example (match this language and logic; do not copy facts):\n"
            + json.dumps(slim_item(keep_example), ensure_ascii=False)[:4000]
        )
    if original:
        extra += (
            "\n\nPre-repair original (restore numbered claim sentences from here if the current item dropped them):\n"
            + json.dumps(slim_item(original.get("item") if isinstance(original.get("item"), dict) else original), ensure_ascii=False)[:5000]
        )
    return (
        STANDING
        + "\nGold chemistry ingest items (structure and framing only; different subject; do not copy wording):\n"
        + json.dumps(samples, ensure_ascii=False)[:6000]
        + extra
        + "\n\nHinge: "
        + hinge_of(row)
        + "\nDecision: "
        + str(unit.get("decision") or unit.get("decision_hinge") or "")[:300]
        + "\nMix-up catalog (cite distinct mx_id on every wrong option / false statement):\n"
        + json.dumps(mx, ensure_ascii=False)[:4000]
        + ("\n\nReviewer note on THIS item:\n" + note if note else "")
        + "\n\nReturn the full repaired item as JSON. Keep item_type unless a combination multi-select should be single_mcq with combination options. "
        "answer.kind is required. worked_solution.result must equal the keyed option text. "
        "Do not write 'a student asks' or 'which statement is correct'. Stem at most two sentences unless numbered claims must be listed.\n"
        "Current item:\n"
        + json.dumps(slim_item(item), ensure_ascii=False)[:9000]
    )


def save_original(row: dict) -> None:
    qid = str(row.get("id") or "")
    if not qid:
        return
    ORIGINALS.parent.mkdir(parents=True, exist_ok=True)
    if ORIGINALS.is_file():
        with ORIGINALS.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip() and json.loads(line).get("id") == qid:
                    return
    with ORIGINALS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def replace_bank_row(new_row: dict) -> bool:
    qid = new_row.get("id")
    if not qid or not PASS_BANK.is_file():
        return False
    tmp = PASS_BANK.with_suffix(".jsonl.repair_tmp")
    found = False
    with PASS_BANK.open(encoding="utf-8") as inf, tmp.open("w", encoding="utf-8") as out:
        for line in inf:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("id") == qid:
                out.write(json.dumps(new_row, ensure_ascii=False) + "\n")
                found = True
            else:
                out.write(line if line.endswith("\n") else line + "\n")
    if found:
        last = None
        for attempt in range(10):
            try:
                tmp.replace(PASS_BANK)
                return True
            except OSError as exc:
                last = exc
                time.sleep(0.4 * (attempt + 1))
        if tmp.is_file():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise last
    if tmp.is_file():
        tmp.unlink()
    return False


def repair_one(
    row: dict,
    gold: list[dict],
    reviews: dict,
    units: dict,
    *,
    notes: str = "",
    keep_example: dict | None = None,
    original: dict | None = None,
) -> str:
    item = dict(row.get("item") or {})
    hid = hinge_of(row)
    unit = units.get(hid) or {"mx_records": []}
    note = str((reviews.get(str(row.get("id"))) or {}).get("note") or "").strip()
    prompt = repair_prompt(
        row,
        gold,
        note,
        unit,
        notes=notes,
        keep_example=keep_example,
        original=original,
    )
    try:
        repaired = tmint.unwrap_writer_item(tmint.call_writer(prompt))
    except Exception as exc:
        return f"writer: {type(exc).__name__}: {exc}"[:240]
    if not isinstance(repaired, dict) or not repaired.get("stem"):
        return "writer returned no stem"
    repaired["item_type"] = repaired.get("item_type") or item.get("item_type")
    err = tmint._bind_item_mx(repaired, unit)
    if err:
        return "mx_bind: " + err[:200]
    tmint._ensure_answer_kind(repaired)
    collapse_multiselect(repaired)
    if looks_combination(repaired) and not has_numbered_claims(repaired):
        return "missing_claims_in_stem"
    req = {
        "requirement_id": str(row.get("id")),
        "subject": row.get("subject") or "science",
        "grade": row.get("grade"),
        "hinge_id": hid,
        "hinge_title": str(unit.get("decision") or unit.get("decision_hinge") or hid),
    }
    miqg = tmint.g17(repaired, req)
    if miqg.get("quality_tier") != "TOP" or miqg.get("release_gate") != "PASS":
        return "NOT_TOP " + str(miqg.get("quality_tier")) + " " + str(miqg.get("decisive_reason") or "")[:80]
    design = dict(row.get("design") or {})
    design["repair"] = "deepseek_review_gold"
    design["repaired_at"] = utc()
    if note:
        design["reviewer_note"] = note
    save_original(row)
    new_row = dict(row)
    new_row["item"] = repaired
    new_row["item_type"] = repaired.get("item_type") or row.get("item_type")
    new_row["miqg"] = {
        "protocol": miqg.get("protocol"),
        "tier": "TOP",
        "quality_tier": "TOP",
        "release_gate": miqg.get("release_gate"),
        "decisive_reason": miqg.get("decisive_reason"),
        "rationale": miqg.get("rationale"),
        "dq_codes": miqg.get("dq_codes"),
        "major_codes": miqg.get("major_codes"),
        "flags": miqg.get("flags"),
        "k_major": miqg.get("k_major"),
        "ran_locally": True,
    }
    new_row["design"] = design
    if not replace_bank_row(new_row):
        return "replace failed"
    return "REPLACED"


def main() -> int:
    configure_env()
    PID.parent.mkdir(parents=True, exist_ok=True)
    PID.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    gold = load_gold()
    reviews = load_reviews()
    units = map_units()
    targets = science_targets()
    done = load_progress()
    originals = {str(r.get("id")): r for r in read_jsonl(ORIGINALS) if r.get("id")}
    keep_row = next((r for r in targets if str(r.get("id")) == KEEP_EXAMPLE_ID), None)
    keep_example = (keep_row or {}).get("item") if keep_row else None
    notes = standing_notes(reviews)
    rework = []
    fresh = []
    for row in targets:
        qid = str(row.get("id") or "")
        rec = reviews.get(qid) or {}
        if rec.get("collection") == "science_repair" and rec.get("verdict") == "keep":
            continue
        if needs_rework(row, rec):
            rework.append(row)
        elif done.get(qid) != "REPLACED":
            fresh.append(row)
    pending = rework + fresh
    log(
        f"REPAIR start n={len(targets)} pending={len(pending)} rework={len(rework)} "
        f"gold={len(gold)} notes={len(reviews)}"
    )
    fails: dict[str, int] = {}
    for row in pending:
        if STOP.is_file():
            log("STOP file present; repair exiting")
            return 0
        qid = str(row.get("id"))
        outcome = repair_one(
            row,
            gold,
            reviews,
            units,
            notes=notes,
            keep_example=keep_example,
            original=originals.get(qid),
        )
        ok = outcome == "REPLACED"
        if not ok:
            fails[qid] = fails.get(qid, 0) + 1
            if fails[qid] < FAIL_LIMIT:
                pending.append(row)
        status = "REPLACED" if ok else ("SKIP" if fails.get(qid, 0) >= FAIL_LIMIT else "RETRY")
        note_progress({"utc": utc(), "id": qid, "status": status, "outcome": outcome[:200]})
        log(f"{status} {qid} {outcome[:160]}")
        time.sleep(1.0)
    log("REPAIR complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
