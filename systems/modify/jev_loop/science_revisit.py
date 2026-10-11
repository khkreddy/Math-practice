#!/usr/bin/env python3
"""Revisit 100 middle-school science items with T-MINT then T-MOD.

DeepSeek writes. Results stay in mint_learning/science_revisit_100 and the
review jsonl. The JEV-pass bank is not written. Stop by creating
mint_learning/science_revisit_STOP.
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TTWIN_ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(TTWIN_ROOT))

import harness  # noqa: E402
import run as tmint  # noqa: E402

PASS_BANK = TTWIN_ROOT / "data" / "questions" / "JEV-pass" / "middle_6_8" / "science.jsonl"
HELD_BANK = TTWIN_ROOT / "data" / "questions" / "middle_6_8" / "science.jsonl"
REVIEW_JSONL = TTWIN_ROOT / "systems" / "review_app" / "science_revisit.jsonl"
OUT = HERE / "mint_learning" / "science_revisit_100"
SAMPLE = OUT / "sample.json"
PROGRESS = OUT / "progress.jsonl"
RESULTS = OUT / "results.jsonl"
LOG = OUT / "science_revisit.log"
STOP = HERE / "mint_learning" / "science_revisit_STOP"
PID = HERE / "mint_learning" / "science_revisit.pid"
WRITER_KEY_FILE = os.environ.get("TTWIN_WRITER_KEY_FILE") or r"C:\Users\Shanthi\Desktop\Deepseek API key.txt"
JEV_KEY_FILE = os.environ.get("TTWIN_JEV_KEY_FILE") or r"C:\Users\Shanthi\Desktop\JEV AI API Key.txt"
LIMIT = 100
SEED = 20261009
FAIL_LIMIT = 2


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
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
            if line.strip():
                rows.append(json.loads(line))
    return rows


def item_of(row: dict) -> dict:
    item = row.get("item")
    return item if isinstance(item, dict) else {}


def hinge_of(row: dict) -> str:
    tag = row.get("jev_taxonomy") if isinstance(row.get("jev_taxonomy"), dict) else {}
    design = row.get("design") if isinstance(row.get("design"), dict) else {}
    return str(
        tag.get("hinge_id")
        or design.get("hinge_id")
        or row.get("hinge_id")
        or tag.get("unit_id")
        or ""
    ).strip()


def construct_of(row: dict) -> str:
    tag = row.get("jev_taxonomy") if isinstance(row.get("jev_taxonomy"), dict) else {}
    design = row.get("design") if isinstance(row.get("design"), dict) else {}
    return str(
        tag.get("construct_id")
        or design.get("target_construct")
        or tag.get("unresolved_coord")
        or "U.Co.2"
    ).strip()


def grade_of(row: dict) -> int:
    raw = row.get("grade") or (row.get("jev_taxonomy") or {}).get("grade") or 6
    try:
        return int(str(raw).lstrip("0") or "0") or 6
    except ValueError:
        return 6


def keyed_text(item: dict) -> str:
    letter = str((item.get("answer") or {}).get("letter") or (item.get("assessment") or {}).get("mcq_key") or "").strip().upper()[:1]
    options = item.get("options")
    if isinstance(options, list):
        for index, raw in enumerate(options):
            if isinstance(raw, dict):
                token = str(raw.get("id") or chr(65 + index)).strip().upper()[:1]
                if token == letter:
                    return str(raw.get("text") or "").strip()
            elif letter == chr(65 + index):
                return str(raw).strip()
    return letter


def slim_item(item: dict) -> dict:
    options = []
    raw = item.get("options")
    if isinstance(raw, list):
        for index, val in enumerate(raw):
            if isinstance(val, dict):
                options.append({"id": str(val.get("id") or chr(65 + index)), "text": str(val.get("text") or "")})
            else:
                options.append({"id": chr(65 + index), "text": str(val)})
    return {
        "stem": item.get("stem") or "",
        "item_type": item.get("item_type") or "",
        "options": options,
        "answer": item.get("answer") or {},
        "statements": item.get("statements") or [],
        "parts": item.get("parts") or [],
        "teacher": {
            "expected_answer": ((item.get("teacher") or {}).get("expected_answer") or ""),
            "route_map": ((item.get("teacher") or {}).get("route_map") or {}),
        },
    }


def pool_rows() -> list[dict]:
    seen = set()
    pooled = []
    for source, path in (("passed", PASS_BANK), ("held", HELD_BANK)):
        for row in read_jsonl(path):
            qid = str(row.get("id") or "")
            if not qid or qid in seen:
                continue
            item = item_of(row)
            if not str(item.get("stem") or "").strip():
                continue
            if not hinge_of(row):
                continue
            seen.add(qid)
            pooled.append({"source": source, "row": row})
    return pooled


def choose_sample(pooled: list[dict]) -> list[dict]:
    if SAMPLE.is_file():
        return json.loads(SAMPLE.read_text(encoding="utf-8"))
    rng = random.Random(SEED)
    ids = list(range(len(pooled)))
    rng.shuffle(ids)
    picked = []
    for index in ids:
        rec = pooled[index]
        row = rec["row"]
        picked.append({
            "id": row.get("id"),
            "source": rec["source"],
            "hinge_id": hinge_of(row),
            "grade": grade_of(row),
            "construct": construct_of(row),
            "item_type": row.get("item_type") or item_of(row).get("item_type"),
            "admitted": bool((row.get("jev_taxonomy") or {}).get("admitted")),
        })
        if len(picked) >= LIMIT:
            break
    SAMPLE.write_text(json.dumps(picked, indent=2), encoding="utf-8")
    return picked


def requirement_for(row: dict) -> dict:
    item = item_of(row)
    stem = str(item.get("stem") or "").strip()
    key = keyed_text(item)
    scene = "Existing scene. Reshape this stem; do not invent a different scene.\n" + stem
    if key:
        scene += "\nKeyed claim of the existing item (expected answer only; do not copy it into the stem):\n" + key
    return {
        "schema": "modify_requirement.v1",
        "requirement_id": "revisit-" + str(row.get("id")),
        "target_construct": construct_of(row),
        "subject": row.get("subject") or "science",
        "grade": grade_of(row),
        "grade_band": "middle_6_8",
        "hinge_id": hinge_of(row),
        "unit_id": hinge_of(row),
        "user_situation": scene,
        "intent": (
            "Repair this sitting item on the named hinge. "
            "T-MINT chooses the format and states the expected answer. "
            "T-MOD completes that format. A single-key MCQ has four options."
        ),
        "accept_neighbour": False,
        "figure_mode": "none",
    }


def note_progress(rec: dict) -> None:
    with PROGRESS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")


def publish_review(rows: list[dict]) -> None:
    REVIEW_JSONL.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_JSONL.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def pack_review(source_row: dict, source_label: str, trail: dict) -> dict:
    item = trail.get("item") if isinstance(trail.get("item"), dict) else {}
    original = dict(source_row)
    original["item"] = slim_item(item_of(source_row))
    return {
        "id": source_row.get("id"),
        "subject": source_row.get("subject") or "science",
        "grade": grade_of(source_row),
        "grade_band": "middle_6_8",
        "item_type": item.get("item_type") or source_row.get("item_type"),
        "item": slim_item(item) if item else {"stem": "", "options": [], "answer": {}},
        "original": original,
        "miqg": trail.get("miqg") or {},
        "jev_taxonomy": trail.get("jev_taxonomy") or {},
        "design": {
            "workflow": ["T-MINT", "T-MOD"],
            "source": "science-revisit-100",
            "prior_source": source_label,
            "hinge_id": hinge_of(source_row),
            "status": trail.get("status"),
            "g18": trail.get("g18"),
            "refusal_reason": trail.get("refusal_reason") or "",
            "tmod": trail.get("tmod") or {},
            "steps": trail.get("steps") or [],
        },
    }


def done_ids() -> set[str]:
    seen = set()
    for rec in read_jsonl(PROGRESS):
        if rec.get("status") in {"OK", "PASS", "PASS_ZONE", "PASS_NEIGHBOUR", "HOLD", "CONSTRUCT_HOLD", "SKIP"}:
            if rec.get("id"):
                seen.add(str(rec["id"]))
    return seen


def run_one(row: dict, dictionary: dict) -> dict:
    req = requirement_for(row)
    out = OUT / "runs" / str(row.get("id")).replace(":", "_").replace("/", "_")
    return harness.generate(req, dictionary, out)


def main() -> int:
    configure_env()
    OUT.mkdir(parents=True, exist_ok=True)
    PID.parent.mkdir(parents=True, exist_ok=True)
    PID.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    dictionary = json.loads(tmint.find_dictionary(None).read_text(encoding="utf-8"))
    pooled = pool_rows()
    sample = choose_sample(pooled)
    by_id = {str(rec["row"].get("id")): rec for rec in pooled}
    done = done_ids()
    published = read_jsonl(REVIEW_JSONL)
    have = {str(row.get("id")) for row in published}
    log(
        "REVISIT start pool=%s sample=%s done=%s writer=%s"
        % (len(pooled), len(sample), len(done), os.environ.get("TTWIN_WRITER_MODEL"))
    )
    fails: dict[str, int] = {}
    pending = [row for row in sample if str(row.get("id")) not in done]
    for brief in pending:
        if STOP.is_file():
            log("STOP file present; revisit exiting")
            return 0
        qid = str(brief.get("id"))
        rec = by_id.get(qid)
        if rec is None:
            note_progress({"utc": utc(), "id": qid, "status": "SKIP", "outcome": "missing source row"})
            log("SKIP missing " + qid)
            continue
        row = rec["row"]
        try:
            trail = run_one(row, dictionary)
            outcome = str(trail.get("status") or "REFUSED")
            reason = str(trail.get("refusal_reason") or "")[:200]
        except Exception as exc:
            trail = {
                "status": "REFUSED",
                "refusal_reason": type(exc).__name__ + ": " + str(exc)[:240],
                "item": None,
                "steps": [traceback.format_exc()[-800:]],
            }
            outcome = "REFUSED"
            reason = trail["refusal_reason"]
        packed = pack_review(row, rec["source"], trail)
        if qid in have:
            published = [entry for entry in published if str(entry.get("id")) != qid]
            have.discard(qid)
        published.append(packed)
        have.add(qid)
        publish_review(published)
        with RESULTS.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"utc": utc(), "id": qid, "status": outcome, "reason": reason}, ensure_ascii=False) + "\n")
        if outcome == "REFUSED":
            fails[qid] = fails.get(qid, 0) + 1
            if fails[qid] < FAIL_LIMIT:
                pending.append(brief)
                status = "RETRY"
            else:
                status = "SKIP"
        else:
            status = outcome
        note_progress({"utc": utc(), "id": qid, "status": status, "outcome": (outcome + " " + reason)[:240]})
        log("%s %s %s %s" % (status, qid, outcome, reason[:120]))
        time.sleep(1.0)
    log("REVISIT complete n=%s" % len(published))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
