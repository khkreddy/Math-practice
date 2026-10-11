"""T-MINT situation stage.

T-MINT chooses the situation and the expected answer. It does not write the
wrong options. Occupied stems on the hinge, and a situation the user supplied,
decide which scene is still available.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TTWIN_ROOT = HERE.parents[2]
QUESTION_ROOT = TTWIN_ROOT / "data" / "questions"

_STOP = {
    "the", "a", "an", "of", "and", "or", "to", "in", "on", "for", "with", "from",
    "that", "this", "is", "are", "was", "were", "be", "by", "at", "as", "it",
}


def _words(text: str) -> list[str]:
    return [part for part in "".join(ch.lower() if ch.isalnum() else " " for ch in str(text or "")).split() if part]


def _spans(words: list[str], width: int = 8) -> set[str]:
    if len(words) < width:
        return set()
    return {" ".join(words[i:i + width]) for i in range(0, len(words) - width + 1)}


def repeats_occupied(stem: str, occupied: list[str] | None) -> str:
    """Return the occupied stem that shares an 8-word span, or the same scene."""
    words = _words(stem)
    if not words:
        return ""
    norm = " ".join(words)
    spans = _spans(words)
    for old in occupied or []:
        old_words = _words(old)
        if not old_words:
            continue
        old_norm = " ".join(old_words)
        if old_norm == norm or (len(old_words) >= 8 and (old_norm in norm or norm in old_norm)):
            return str(old).strip()[:180]
        if spans and _spans(old_words) & spans:
            return str(old).strip()[:180]
    return ""


def follows_user_situation(stem: str, user_situation: str) -> bool:
    """A supplied situation is followed when the stem keeps its scene."""
    given = str(user_situation or "").strip()
    if not given:
        return True
    if repeats_occupied(stem, [given]):
        return True
    wanted = [word for word in _words(given) if len(word) > 3 and word not in _STOP]
    if not wanted:
        return True
    have = set(_words(stem))
    hit = sum(1 for word in wanted if word in have)
    return hit >= max(1, (len(wanted) + 1) // 2)


def collect_occupied(hinge_ids, root: Path | None = None, limit: int = 40) -> list[str]:
    """Stems already built for these hinges. Used so the next situation is a different one."""
    want = {str(hinge).strip() for hinge in hinge_ids if str(hinge).strip()}
    if not want:
        return []
    base = root or QUESTION_ROOT
    if not base.is_dir():
        return []
    found: list[str] = []
    for path in base.rglob("*.jsonl"):
        if "mint_learning" in path.parts:
            continue
        try:
            handle = path.open(encoding="utf-8")
        except OSError:
            continue
        with handle:
            for line in handle:
                if len(found) >= limit:
                    return found
                if not line.strip() or not any(hinge in line for hinge in want):
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                hinge = str((row.get("jev_taxonomy") or {}).get("hinge_id") or row.get("hinge_id") or "")
                if hinge not in want:
                    continue
                item = row.get("item") if isinstance(row.get("item"), dict) else row
                stem = str((item or {}).get("stem") or "").strip()
                if stem and stem not in found:
                    found.append(stem)
    return found


def companion_briefs(req: dict) -> list[dict]:
    """Decision sentences for hinges the situation may combine with the center."""
    ids = [str(hinge).strip() for hinge in (req.get("companion_hinge_ids") or []) if str(hinge).strip()]
    if not ids:
        return []
    try:
        import unit_bind
    except ImportError:
        return []
    tables = unit_bind.load_tables(req)
    if not tables:
        return []
    by_id = tables[0]
    briefs = []
    for hinge_id in ids:
        unit = by_id.get(hinge_id)
        if not isinstance(unit, dict):
            continue
        briefs.append({
            "hinge_id": hinge_id,
            "decision": str(unit.get("decision") or "").strip(),
        })
    return briefs


def prompt_block(req: dict) -> str:
    """Teacher-side situation instructions. The map catalog stays above this block."""
    lines = [
        "T-MINT writes the question situation and the expected answer. "
        "It does not write wrong options. T-MOD writes those after this situation is fixed.",
        "Study the hinge decision, the boundaries, and the mix-up catalog above as evidence of "
        "what this hinge can assess. Choose a situation that makes that decision observable. "
        "The catalog is teacher-side. Do not paste a mix-up sentence, a border, or a mix-up id into the stem.",
        "Ignore any instruction above that asks for wrong options, a mix-up citation, or a worked solution. "
        "Those are not this step.",
    ]
    if req.get("lock_format") and str(req.get("lock_item_type") or "").strip():
        lines.append(
            "Item type is locked to "
            + str(req.get("lock_item_type")).strip()
            + ". Do not change it."
        )
    else:
        lines.append(
            "T-MINT chooses the item_type from the format menu. Choose the format that makes "
            "this hinge's decision observable. T-MOD will complete that format: four options "
            "for a standard single-key MCQ, statements for three_statement, parts for "
            "structured_parts, a rubric for open_response. Do not pick a format for variety."
        )
    user = str(req.get("user_situation") or "").strip()
    if user:
        lines.append(
            "USER SITUATION. Build the question and the expected answer from this scene. "
            "Do not invent a different scene.\n" + user[:1200]
        )
    occupied = [str(stem).strip() for stem in (req.get("occupied_situations") or []) if str(stem).strip()]
    if occupied and not user:
        lines.append(
            "Situations already built for this hinge. Choose a different situation. "
            "Do not reuse an 8-word span, the same quantities, or the same scene."
        )
        for stem in occupied[:8]:
            lines.append("- " + stem[:180])
    companions = req.get("companion_hinges") if isinstance(req.get("companion_hinges"), list) else []
    if companions:
        lines.append(
            "Companion hinges. A situation may use the center hinge together with one of these "
            "when the decision needs both. Record every hinge id you use in teacher.hinge_ids. "
            "Do not paste these sentences."
        )
        for row in companions[:6]:
            if isinstance(row, dict):
                lines.append(str(row.get("hinge_id") or "") + ": " + str(row.get("decision") or "")[:240])
            else:
                lines.append(str(row)[:240])
    lines.append(
        "expected_answer is the bare result THIS stem requires, in this situation's quantities. "
        "Do not copy a general hinge sentence when a given condition blocks it. "
        "Do not attach a because-clause or an explanation to that result. "
        "When the assessment is the method rather than one value, write the steps in answer_mechanism. "
        "Do not print the mechanism in the stem.\n"
        "The stem is at most two sentences and at most 38 words. "
        "Do not write these phrases anywhere a candidate can read: 'a student asks', 'a student wants', "
        "'a student must', 'a class is', 'already known', 'which statement is correct', "
        "'which statements are correct', 'which claim is correct', 'the learner'. "
        "Describe the objects and the event.\n"
        "Return stem, item_type, expected_answer, answer_mechanism, and teacher with situation_decision "
        "and hinge_ids. For a choice item, options contains only the keyed option and answer.letter is that option. "
        "Do not add any other option. For open_response or structured_parts, put the expected answer in the "
        "rubric or the part answers and leave options empty."
    )
    return "\n".join(lines) + "\n"


def _option_text(item: dict, letter: str) -> str:
    options = item.get("options")
    if isinstance(options, dict):
        raw = options.get(letter)
        if isinstance(raw, dict):
            return str(raw.get("text") or "").strip()
        return str(raw or "").strip()
    if isinstance(options, list):
        for index, raw in enumerate(options):
            if isinstance(raw, dict):
                token = str(raw.get("id") or raw.get("letter") or chr(65 + index)).strip().upper()[:1]
                if token == letter:
                    return str(raw.get("text") or "").strip()
            elif isinstance(raw, str) and chr(65 + index) == letter:
                return raw.strip()
    return ""


def install_expected_answer(item: dict) -> str:
    """Keep the stem and one expected answer. Drop any wrong options."""
    if not isinstance(item, dict):
        return "situation is not an object"
    stem = str(item.get("stem") or "").strip()
    if not stem:
        return "no question situation"
    item["stem"] = stem
    teacher = dict(item.get("teacher") or {}) if isinstance(item.get("teacher"), dict) else {}
    expected = str(item.get("expected_answer") or teacher.get("expected_answer") or "").strip()
    mechanism = str(item.get("answer_mechanism") or teacher.get("answer_mechanism") or "").strip()
    kind = str(item.get("item_type") or "")
    item.pop("worked_solution", None)
    item.pop("mx_option_map", None)
    item.pop("statement_mx_map", None)
    if kind in {"open_response", "structured_parts", "three_statement"}:
        if not expected and not mechanism:
            return "no expected answer"
        teacher["expected_answer"] = expected
        if mechanism:
            teacher["answer_mechanism"] = mechanism
        item["teacher"] = teacher
        if kind == "three_statement":
            item["options"] = []
            pattern = expected.replace(" ", "").upper()
            if pattern and set(pattern) <= set("TF"):
                item["answer"] = {"kind": "statement_pattern", "pattern": pattern}
            elif not isinstance(item.get("answer"), dict) or item["answer"].get("kind") != "statement_pattern":
                item["answer"] = {"kind": "statement_pattern", "pattern": expected}
            return ""
        item["options"] = []
        if kind == "open_response":
            item["answer"] = {"kind": "rubric", "rubric": expected or mechanism}
        return ""
    answer = item.get("answer") if isinstance(item.get("answer"), dict) else {}
    letter = str(answer.get("letter") or "").strip().upper()[:1] or "A"
    if not expected:
        expected = _option_text(item, letter)
    if not expected:
        return "no expected answer"
    teacher["expected_answer"] = expected
    if mechanism:
        teacher["answer_mechanism"] = mechanism
    item["teacher"] = teacher
    item["options"] = [{"id": letter, "text": expected}]
    item["answer"] = {"kind": "single_letter", "letter": letter}
    item.pop("expected_answer", None)
    item.pop("answer_mechanism", None)
    return ""


def stage_item(item: dict, req: dict) -> str:
    """Install the expected answer and refuse a repeated scene. Empty means ready."""
    error = install_expected_answer(item)
    if error:
        return error
    user = str(req.get("user_situation") or "").strip()
    if user and not follows_user_situation(item.get("stem") or "", user):
        return "situation did not follow the user input"
    if not user:
        occupied = repeats_occupied(item.get("stem") or "", req.get("occupied_situations") or [])
        if occupied:
            return "situation already used: " + occupied[:180]
    return ""


def source_for_tmod(req: dict, item: dict) -> dict:
    """The sitting item T-MOD receives. Stem and expected answer are already fixed."""
    return {
        "id": req.get("requirement_id") or req.get("hinge_id") or "t-mint",
        "subject": req.get("subject"),
        "grade": req.get("grade"),
        "grade_band": req.get("grade_band"),
        "item_type": item.get("item_type"),
        "jev_taxonomy": {
            "hinge_id": req.get("hinge_id") or req.get("unit_id"),
            "hinge_ids": list((item.get("teacher") or {}).get("hinge_ids") or []),
        },
        "item": item,
    }
