"""Bank-append eligibility for TTwin-final question JSONL.

Only MIQG TOP rows that carry a ttwin.jev_taxonomy.v1 overlay may enter the bank.
MEDIUM, LOW, and overlay-missing rows are rejected. G18 HOLD does not by itself
block packing: a coordinate counts as populated only when unbiased classify admits
that construct_id.

META_LANGUAGE in any student-facing field is a hard refuse at append time, via the
shared MIQG checker — even if a caller forged a TOP stamp.

A complete item.worked_solution is also required at append time: framing is only
allowed after the solution exists, and worked_solution.result must be the keyed
option. STEM_STACKED_TUTORIAL_CONCLUSION stacks are refused.

Served MCQs must carry option.feedback on every wrong option
(systems.question_ingest.option_feedback.OPTION_FEEDBACK_FIELD).

Release gate is MIQG only (TOP + overlay). Legacy harness_gate is archived.
MIQG TOP rules themselves are unchanged — this module only refuses serve/append.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from catalog import normalize_result_shape

OVERLAY_SCHEMA = "ttwin.jev_taxonomy.v1"
TOP = "TOP"
BANK_MIQG_PROTOCOL = "MIQG-v1.0-rc9-CAL-KNGOOD"

_MIQG_DIR = Path(__file__).resolve().parents[1] / "miqg"
if str(_MIQG_DIR) not in sys.path:
    sys.path.insert(0, str(_MIQG_DIR))
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _item_refuses_meta_language(row_or_item: Any) -> bool:
    """Shared MIQG META_LANGUAGE gate — do not duplicate regex here."""
    try:
        from systems.modify.miqg.miqg_cal import item_refuses_meta_language
    except ImportError:
        from miqg_cal import item_refuses_meta_language  # type: ignore
    if not isinstance(row_or_item, dict):
        return False
    return bool(item_refuses_meta_language(row_or_item))


def _worked_solution_refuse(row_or_item: Any) -> str | None:
    try:
        from systems.modify.miqg.worked_solution import admit_refuse_reason
    except ImportError:
        from worked_solution import admit_refuse_reason  # type: ignore
    if not isinstance(row_or_item, dict):
        return "not a dict"
    return admit_refuse_reason(row_or_item)


def _item_refuses_worked_solution(row_or_item: Any) -> bool:
    """Refuse when complete worked_solution is missing or key does not follow."""
    return _worked_solution_refuse(row_or_item) is not None


def _letters_from_value(value: Any) -> set[str]:
    if value is None or isinstance(value, bool):
        return set()
    if isinstance(value, list):
        found: set[str] = set()
        for item in value:
            found.update(_letters_from_value(item))
        return found
    text = str(value).strip().upper()
    if not text or text in {"NONE", "NULL"}:
        return set()
    parts = [part for part in text.replace(",", " ").split() if part.isalpha() and len(part) == 1]
    if parts:
        return set(parts)
    if text.isalpha() and len(text) == 1:
        return {text}
    return set()


def _correct_letters(row: dict) -> set[str]:
    item = row.get("item") if isinstance(row.get("item"), dict) else row
    if not isinstance(item, dict):
        return set()
    found: set[str] = set()
    assessment = item.get("assessment") or {}
    if isinstance(assessment, dict):
        found.update(_letters_from_value(assessment.get("mcq_key")))
    answer = item.get("answer")
    if isinstance(answer, dict):
        found.update(_letters_from_value(answer.get("letter")))
        found.update(_letters_from_value(answer.get("letters")))
    elif isinstance(answer, str):
        found.update(_letters_from_value(answer))
    options = item.get("options")
    if isinstance(options, list):
        for option in options:
            if isinstance(option, dict) and option.get("key") is True:
                found.update(_letters_from_value(option.get("letter") or option.get("id")))
    return found


def _iter_mcq_options(row: dict) -> list[tuple[str, Any]]:
    item = row.get("item") if isinstance(row.get("item"), dict) else row
    if not isinstance(item, dict):
        return []
    options = item.get("options")
    out: list[tuple[str, Any]] = []
    if isinstance(options, dict):
        for letter, raw in options.items():
            out.append((str(letter).upper(), raw))
    elif isinstance(options, list):
        for option in options:
            if not isinstance(option, dict):
                continue
            letter = option.get("letter") or option.get("id")
            if isinstance(letter, str) and letter.strip():
                out.append((letter.strip().upper(), option))
    return out


def _item_refuses_missing_option_feedback(row_or_item: Any) -> bool:
    """Refuse a served MCQ whose wrong options lack option.feedback."""
    try:
        from systems.question_ingest.option_feedback import has_valid_feedback
    except ImportError:
        return True
    if not isinstance(row_or_item, dict):
        return True
    pairs = _iter_mcq_options(row_or_item)
    if not pairs:
        return False  # not an MCQ surface — other gates apply
    keyed = _correct_letters(row_or_item)
    if not keyed:
        # No letter key: cannot classify wrong options; refuse serve of MCQ-shaped rows.
        return True
    for letter, raw in pairs:
        if letter in keyed:
            continue
        if not has_valid_feedback(raw if isinstance(raw, dict) else None):
            return True
    return False


def miqg_tier(row_or_miqg: Any) -> str | None:
    if not isinstance(row_or_miqg, dict):
        return None
    miqg = row_or_miqg["miqg"] if "miqg" in row_or_miqg else row_or_miqg
    if not isinstance(miqg, dict):
        return None
    t = miqg.get("tier") or miqg.get("quality_tier")
    if t is None:
        return None
    return str(t)


def has_overlay(row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    jt = row.get("jev_taxonomy")
    return isinstance(jt, dict) and jt.get("schema") == OVERLAY_SCHEMA


def _multiformat_key_mismatch_only(row: Any) -> bool:
    """True when a multi-select or true/false item is solved, but has no single keyed letter."""
    if not isinstance(row, dict):
        return False
    item = row.get("item") if isinstance(row.get("item"), dict) else row
    if not isinstance(item, dict) or item.get("item_type") not in ("one_or_more", "three_statement"):
        return False
    return (
        _worked_solution_refuse(row)
        == "worked_solution.result must be the keyed option (asked quantity)"
    )


def bank_append_eligible(row: Any, *, allow_multiformat_result: bool = False) -> bool:
    """True iff TOP, overlay-tagged, free of META_LANGUAGE, solved, and wrong options carry feedback."""
    if not isinstance(row, dict):
        return False
    design = row.get("design") if isinstance(row.get("design"), dict) else {}
    release = row.get("release") if isinstance(row.get("release"), dict) else {}
    if design.get("human_hold") or release.get("human_hold"):
        return False
    if _item_refuses_meta_language(row):
        return False
    if _item_refuses_worked_solution(row) and not (
        allow_multiformat_result and _multiformat_key_mismatch_only(row)
    ):
        return False
    if _item_refuses_missing_option_feedback(row):
        return False
    return miqg_tier(row) == TOP and has_overlay(row)


def mint_item_id(req: dict, utc: str | None = None) -> str:
    subject = str(req.get("subject") or "item").strip().lower() or "item"
    try:
        grade = f"{int(req.get('grade')):02d}"
    except (TypeError, ValueError):
        grade = "00"
    hinge = str(req.get("hinge_id") or "H").replace("/", "-")
    rid = str(req.get("requirement_id") or "tmint")
    slug = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in rid)[:48]
    return f"{subject}_grade_{grade}_{hinge}__{slug}"


def bank_row_from_trail(
    trail: dict,
    item_id: str | None = None,
    source: str | None = None,
    *,
    allow_multiformat_result: bool = False,
) -> dict | None:
    """Project a T-MINT run trail into a bank row, or None if ineligible."""
    if not isinstance(trail, dict):
        return None
    release = trail.get("release") if isinstance(trail.get("release"), dict) else {}
    if release.get("human_hold"):
        return None
    item = trail.get("item")
    tag = trail.get("jev_taxonomy")
    if not isinstance(item, dict) or not isinstance(tag, dict):
        return None
    if _item_refuses_meta_language(item):
        return None
    solution_row = {"item": item, "worked_solution": item.get("worked_solution")}
    if _item_refuses_worked_solution(solution_row):
        if not (
            allow_multiformat_result
            and item.get("item_type") in ("one_or_more", "three_statement")
            and _worked_solution_refuse(solution_row)
            == "worked_solution.result must be the keyed option (asked quantity)"
        ):
            return None
    if _item_refuses_missing_option_feedback({"item": item}):
        return None
    miqg_src = trail.get("miqg") if isinstance(trail.get("miqg"), dict) else {}
    req = trail.get("requirement") if isinstance(trail.get("requirement"), dict) else {}
    plan = trail.get("plan") if isinstance(trail.get("plan"), dict) else {}
    g18 = trail.get("g18") if isinstance(trail.get("g18"), dict) else {}
    iid = item_id or mint_item_id(req)
    overlay = dict(tag)
    overlay["item_id"] = iid
    overlay["schema"] = overlay.get("schema") or OVERLAY_SCHEMA
    overlay["miqg_tier"] = miqg_src.get("quality_tier") or miqg_src.get("tier") or overlay.get("miqg_tier")
    protocol = miqg_src.get("protocol") or overlay.get("miqg_protocol") or BANK_MIQG_PROTOCOL
    row = {
        "id": iid,
        "subject": req.get("subject") or overlay.get("subject"),
        "grade_band": req.get("grade_band") or "middle_6_8",
        "grade": str(req.get("grade") if req.get("grade") is not None else overlay.get("grade") or ""),
        "item_type": item.get("item_type") or overlay.get("item_type"),
        "miqg": {
            "protocol": protocol,
            "tier": miqg_src.get("quality_tier") or miqg_src.get("tier"),
            "decisive_reason": miqg_src.get("decisive_reason"),
        },
        "jev_taxonomy": overlay,
        "design": {
            "schema": "modify_requirement.v1",
            "target_construct": req.get("target_construct"),
            "hinge_id": req.get("hinge_id"),
            "workflow": "jev_loop.v1",
            "recommended_form": plan.get("recommended_form"),
            "g18": g18.get("status"),
            "source": source or "t-mint-middle-6-8-fill",
        },
        "item": normalize_result_shape(item),
    }
    if not bank_append_eligible(row, allow_multiformat_result=allow_multiformat_result):
        return None
    return row


def append_eligible_row(path: Path, row: dict, *, allow_multiformat_result: bool = False) -> bool:
    """Append one eligible row. Returns False if rejected or id already present."""
    if _item_refuses_meta_language(row):
        return False
    if _item_refuses_worked_solution(row) and not (
        allow_multiformat_result and _multiformat_key_mismatch_only(row)
    ):
        return False
    if _item_refuses_missing_option_feedback(row):
        return False
    if not bank_append_eligible(row, allow_multiformat_result=allow_multiformat_result):
        return False
    path = Path(path)
    if path.is_file():
        want = row.get("id")
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if existing.get("id") == want:
                    return False
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return True


def sync_manifest(root: Path) -> dict:
    """Rewrite data/questions/MANIFEST.json from JSONL line counts and overlay flags."""
    root = Path(root)
    qdir = root / "data" / "questions"
    files = []
    by_band_subject = {}
    n = 0
    admitted = 0
    held = 0
    sources = [("held", path) for path in sorted(qdir.glob("*/*.jsonl"))]
    passed_dir = qdir / "JEV-pass"
    if passed_dir.is_dir():
        sources.extend(("JEV-pass", path) for path in sorted(passed_dir.glob("*/*.jsonl")))
    for part, jsonl in sources:
        if jsonl.stem.endswith("_held"):
            continue
        recs = []
        with jsonl.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    recs.append(json.loads(line))
        rel = jsonl.relative_to(root).as_posix()
        band = jsonl.parent.name
        subject = jsonl.stem
        files.append(
            {
                "path": rel,
                "part": part,
                "grade_band": band,
                "subject": subject,
                "n": len(recs),
                "bytes": jsonl.stat().st_size,
            }
        )
        key = f"{band}/{subject}" if part == "held" else f"JEV-pass/{band}/{subject}"
        by_band_subject[key] = len(recs)
        n += len(recs)
        for r in recs:
            jt = r.get("jev_taxonomy") or {}
            if jt.get("admitted"):
                admitted += 1
            else:
                held += 1
    man = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rule": "MIQG-v1.0-rc9-CAL-KNGOOD tier TOP and present in ttwin.jev_taxonomy.v1 overlay",
        "n": n,
        "admitted": admitted,
        "held": held,
        "grade_bands": [
            "middle_6_8",
            "secondary_9_10",
            "senior_11_12",
            "olympiad_iit",
        ],
        "files": files,
        "by_band_subject": by_band_subject,
        "excluded": [
            "MEDIUM and LOW",
            "untagged structured_parts and open_response (pre-T-MINT overlay pack)",
            "origin folders (candidate vs harvest)",
        ],
    }
    (qdir / "MANIFEST.json").write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    return man
