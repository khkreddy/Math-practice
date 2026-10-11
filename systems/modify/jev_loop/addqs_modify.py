#!/usr/bin/env python3
"""Complete 100 senior-chemistry addqs items with the latest modify harness.

Stem and key stay from the ingest set. T-MINT skips the writer and checks the
key. T-MOD writes the wrong options. Results stay in mint_learning/addqs_modify_100
and the review jsonl. The JEV-pass bank is not written. Stop by creating
mint_learning/addqs_modify_STOP.
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
import key_gate  # noqa: E402
import run as tmint  # noqa: E402

_ORIG_KEY_CHECK = key_gate.check


def _keep_ingest_key(item, unit, writer, req=None):
    """This comparison run keeps the bank key. T-MOD must still write options."""
    report = _ORIG_KEY_CHECK(item, unit, writer, req)
    kept = dict(report)
    kept["ingest_key_gate"] = {
        "status": report.get("status"),
        "reason": report.get("reason"),
        "proposed": report.get("proposed"),
        "independent_result": report.get("independent_result"),
    }
    kept["status"] = "PASS"
    kept["reason"] = "ingest stem and key kept"
    return kept


key_gate.check = _keep_ingest_key

PASS_BANK = TTWIN_ROOT / "data" / "questions" / "JEV-pass" / "senior_11_12" / "chemistry.jsonl"
REVIEW_JSONL = TTWIN_ROOT / "systems" / "review_app" / "addqs_modify.jsonl"
OUT = HERE / "mint_learning" / "addqs_modify_100"
SAMPLE = OUT / "sample.json"
PROGRESS = OUT / "progress.jsonl"
RESULTS = OUT / "results.jsonl"
LOG = OUT / "addqs_modify.log"
STOP = HERE / "mint_learning" / "addqs_modify_STOP"
PID = HERE / "mint_learning" / "addqs_modify.pid"
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


def is_addqs(row: dict) -> bool:
    return str(row.get("id") or "").startswith("addqs:") or str(
        (row.get("design") or {}).get("source") or ""
    ) == "addqs"


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
    ingest = row.get("question_ingest") if isinstance(row.get("question_ingest"), dict) else {}
    return str(
        tag.get("construct_id")
        or design.get("target_construct")
        or ingest.get("demand_cell")
        or "An.Co.2"
    ).strip()


def key_letter(item: dict) -> str:
    ans = item.get("answer") if isinstance(item.get("answer"), dict) else {}
    letter = str(ans.get("letter") or "").strip().upper()[:1]
    if letter:
        return letter
    assess = item.get("assessment") if isinstance(item.get("assessment"), dict) else {}
    return str(assess.get("mcq_key") or "").strip().upper()[:1]


def option_rows(item: dict) -> list[dict]:
    options = []
    raw = item.get("options")
    if isinstance(raw, dict):
        for letter, val in raw.items():
            token = str(letter).strip().upper()[:1]
            if isinstance(val, dict):
                options.append({"id": token, "text": str(val.get("text") or val.get("value") or "")})
            else:
                options.append({"id": token, "text": str(val or "")})
    elif isinstance(raw, list):
        for index, val in enumerate(raw):
            if isinstance(val, dict):
                options.append({
                    "id": str(val.get("id") or val.get("letter") or chr(65 + index)),
                    "text": str(val.get("text") or val.get("value") or ""),
                })
            else:
                options.append({"id": chr(65 + index), "text": str(val)})
    return options


def keyed_text(item: dict) -> str:
    letter = key_letter(item)
    for opt in option_rows(item):
        if str(opt.get("id") or "").strip().upper()[:1] == letter:
            return str(opt.get("text") or "").strip()
    return letter


def has_figure(row: dict, item: dict) -> bool:
    if item.get("has_figure") or item.get("options_are_figure") or item.get("figure"):
        return True
    if item.get("tables") or item.get("tikz"):
        return True
    blob = json.dumps(row, ensure_ascii=False).lower()
    return "tikzpicture" in blob or "tikz" in blob


def slim_item(item: dict) -> dict:
    return {
        "stem": item.get("stem") or "",
        "item_type": item.get("item_type") or "",
        "options": option_rows(item),
        "answer": item.get("answer") or {},
        "assessment": item.get("assessment") or {},
        "statements": item.get("statements") or [],
        "parts": item.get("parts") or [],
        "teacher": {
            "expected_answer": ((item.get("teacher") or {}).get("expected_answer") or ""),
            "route_map": ((item.get("teacher") or {}).get("route_map") or {}),
            "key_gate": ((item.get("teacher") or {}).get("key_gate") or {}),
        },
        "worked_solution": item.get("worked_solution") or {},
    }


def pool_rows() -> list[dict]:
    pooled = []
    seen = set()
    for row in read_jsonl(PASS_BANK):
        qid = str(row.get("id") or "")
        if not qid or qid in seen or not is_addqs(row):
            continue
        item = item_of(row)
        if not str(item.get("stem") or "").strip():
            continue
        if not hinge_of(row) or not key_letter(item) or not keyed_text(item):
            continue
        if has_figure(row, item):
            continue
        seen.add(qid)
        pooled.append(row)
    return pooled


def choose_sample(pooled: list[dict]) -> list[dict]:
    if SAMPLE.is_file():
        return json.loads(SAMPLE.read_text(encoding="utf-8"))
    rng = random.Random(SEED)
    ids = list(range(len(pooled)))
    rng.shuffle(ids)
    picked = []
    for index in ids:
        row = pooled[index]
        item = item_of(row)
        picked.append({
            "id": row.get("id"),
            "hinge_id": hinge_of(row),
            "construct": construct_of(row),
            "item_type": row.get("item_type") or item.get("item_type"),
            "key_letter": key_letter(item),
        })
        if len(picked) >= LIMIT:
            break
    SAMPLE.write_text(json.dumps(picked, indent=2), encoding="utf-8")
    return picked


def draft_from(row: dict) -> dict:
    item = item_of(row)
    letter = key_letter(item)
    expected = keyed_text(item)
    return {
        "schema": "modify_result.v1",
        "item_type": "single_mcq",
        "stem": str(item.get("stem") or "").strip(),
        "options": option_rows(item),
        "answer": {"kind": "single_letter", "letter": letter},
        "expected_answer": expected,
        "teacher": {"expected_answer": expected},
        "statements": item.get("statements") or [],
        "equations": item.get("equations") or [],
    }


def requirement_for(row: dict) -> dict:
    item = item_of(row)
    stem = str(item.get("stem") or "").strip()
    key = keyed_text(item)
    scene = "Existing scene. Keep this stem. Do not invent a different scene.\n" + stem
    if key:
        scene += "\nKeyed claim of the existing item (expected answer only; do not copy it into the stem):\n" + key
    return {
        "schema": "modify_requirement.v1",
        "requirement_id": "addqs-mod-" + str(row.get("id")),
        "target_construct": construct_of(row),
        "subject": "chemistry",
        "grade": 12,
        "grade_band": "senior_11_12",
        "hinge_id": hinge_of(row),
        "unit_id": hinge_of(row),
        "user_situation": scene,
        "lock_format": True,
        "lock_item_type": "single_mcq",
        "intent": (
            "Keep this sitting stem and its keyed claim. "
            "T-MINT states the expected answer from the existing key. "
            "T-MOD writes three wrong options. A single-key MCQ has four options."
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


def pack_review(source_row: dict, trail: dict) -> dict:
    item = trail.get("item") if isinstance(trail.get("item"), dict) else {}
    original = dict(source_row)
    original["item"] = slim_item(item_of(source_row))
    original_item = item_of(source_row)
    original["item"]["answer"] = {
        "kind": "single_letter",
        "letter": key_letter(original_item),
    }
    original["item"]["assessment"] = original_item.get("assessment") or {}
    return {
        "id": source_row.get("id"),
        "subject": "chemistry",
        "grade": 12,
        "grade_band": "senior_11_12",
        "item_type": item.get("item_type") or "single_mcq",
        "item": slim_item(item) if item else {"stem": "", "options": [], "answer": {}},
        "original": original,
        "miqg": trail.get("miqg") or {},
        "jev_taxonomy": trail.get("jev_taxonomy") or {},
        "design": {
            "workflow": ["T-MINT", "T-MOD"],
            "source": "addqs-modify-100",
            "prior_source": "chemistry_addqs",
            "hinge_id": hinge_of(source_row),
            "status": trail.get("status"),
            "g18": trail.get("g18"),
            "refusal_reason": trail.get("refusal_reason") or "",
            "tmod": trail.get("tmod") or {},
            "key_gate": trail.get("key_gate") or {},
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
    return harness.generate(req, dictionary, out, draft_from(row))


def main() -> int:
    configure_env()
    OUT.mkdir(parents=True, exist_ok=True)
    PID.parent.mkdir(parents=True, exist_ok=True)
    PID.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    dictionary = json.loads(tmint.find_dictionary(None).read_text(encoding="utf-8"))
    pooled = pool_rows()
    sample = choose_sample(pooled)
    by_id = {str(row.get("id")): row for row in pooled}
    done = done_ids()
    published = read_jsonl(REVIEW_JSONL)
    have = {str(row.get("id")) for row in published}
    log(
        "ADDQS-MODIFY start pool=%s sample=%s done=%s writer=%s"
        % (len(pooled), len(sample), len(done), os.environ.get("TTWIN_WRITER_MODEL"))
    )
    fails: dict[str, int] = {}
    pending = [row for row in sample if str(row.get("id")) not in done]
    for brief in pending:
        if STOP.is_file():
            log("STOP file present; addqs modify exiting")
            return 0
        qid = str(brief.get("id"))
        row = by_id.get(qid)
        if row is None:
            note_progress({"utc": utc(), "id": qid, "status": "SKIP", "outcome": "missing source row"})
            log("SKIP missing " + qid)
            continue
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
        packed = pack_review(row, trail)
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
    log("ADDQS-MODIFY complete n=%s" % len(published))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
