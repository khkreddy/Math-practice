"""Code checks from the frozen phrase spec. These refuse an item. They do not rewrite it."""
from __future__ import annotations

import re

ROMAN = ("VIII", "VII", "VI", "IV", "III", "II", "V", "I")
ROMAN_RE = re.compile(r"\b(VIII|VII|VI|IV|III|II|V|I)\b")
VAGUE_RE = re.compile(r"\bthe (?:material|substance)\b", re.IGNORECASE)
META_RE = re.compile(
    r"this is wrong because|by reversing|\bconfuses\b|teacher-side|\bmx_id\b|/MX_",
    re.IGNORECASE,
)
AR_RELATIONS = (
    ("both_true_explains", re.compile(
        r"both .{0,48}true,?\s+and .{0,80}(?:correct explanation|correctly explains)", re.I
    )),
    ("both_true_not", re.compile(
        r"both .{0,48}true,?\s+but .{0,80}(?:not the correct explanation|does not correctly explain)", re.I
    )),
    ("a_true_r_false", re.compile(
        r"(?:the )?assertion is true,? but (?:the )?reason is false|\ba is true,? but r is false", re.I
    )),
    ("a_false_r_true", re.compile(
        r"(?:the )?assertion is false,? but (?:the )?reason is true|\ba is false,? but r is true", re.I
    )),
    ("both_false", re.compile(r"both .{0,48}false", re.I)),
)

CHOICE_TYPES = {
    "single_mcq",
    "one_or_more",
    "three_statement",
    "option_table",
    "options_are_figure",
}
REASON_RE = re.compile(
    r"\b(?:because|since|therefore|thus|hence|which means|for each|as a result|given that|this means)\b",
    re.IGNORECASE,
)
JEV_QUESTIONS = (
    "unrelated statement",
    "distractor also true",
    "same logic as the key or another distractor",
    "claim contradicts the stem",
    "option is what a holder of the cited wrong sentence would choose",
)


def release_record(legal: dict | None) -> dict:
    legal = legal or {}
    return {
        "human_hold": True,
        "jev_judge": "not_run_until_labelled_set",
        "situation_verified": bool(legal.get("situation_verified")),
        "legal_ids": list(legal.get("legal_ids") or []),
        "jev_questions": list(JEV_QUESTIONS),
    }


def wrong_slots(item: dict) -> int:
    """How many wrong choices the written item must fill from the legal set."""
    if not isinstance(item, dict):
        return 0
    kind = str(item.get("item_type") or "")
    if kind in {"open_response", "structured_parts"}:
        return 0
    answer = item.get("answer") if isinstance(item.get("answer"), dict) else {}
    if kind == "three_statement":
        pattern = answer.get("pattern")
        if isinstance(pattern, str):
            marks = [ch for ch in pattern.upper() if ch in {"T", "F"}]
        elif isinstance(pattern, list):
            marks = [str(ch).strip().upper()[:1] for ch in pattern]
        else:
            marks = []
        return sum(1 for mark in marks if mark == "F")
    options = item.get("options")
    if not isinstance(options, list) or not options:
        rows = item.get("rows")
        options = rows if isinstance(rows, list) else []
    count = len(options)
    letters = answer.get("letters")
    if isinstance(letters, list) and letters:
        keyed = len([token for token in letters if str(token).strip()])
    elif str(answer.get("letter") or "").strip():
        keyed = 1
    else:
        keyed = 1 if count else 0
    return max(0, count - keyed)


def _student_blob(item: dict) -> str:
    parts: list[str] = [str(item.get("stem") or "")]
    for key in ("options", "statements", "rows", "parts"):
        rows = item.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, str):
                parts.append(row)
            elif isinstance(row, dict):
                for field in ("text", "claim", "reason", "prompt"):
                    if row.get(field):
                        parts.append(str(row.get(field)))
    return "\n".join(parts)


def _keyed_option_text(item: dict) -> str:
    answer = item.get("answer") if isinstance(item.get("answer"), dict) else {}
    letter = str(answer.get("letter") or "").strip().upper()[:1]
    if not letter:
        return ""
    options = item.get("options") if isinstance(item.get("options"), list) else []
    for index, raw in enumerate(options):
        if isinstance(raw, dict):
            token = str(raw.get("id") or chr(65 + index)).strip().upper()[:1]
            if token == letter:
                return str(raw.get("text") or "").strip()
        elif isinstance(raw, str) and chr(65 + index) == letter:
            return raw.strip()
    return ""


def _option_texts(item: dict) -> list[str]:
    options = item.get("options") if isinstance(item.get("options"), list) else []
    texts = []
    for raw in options:
        if isinstance(raw, dict):
            texts.append(str(raw.get("text") or ""))
        elif isinstance(raw, str):
            texts.append(raw)
    return texts


def _ar_errors(item: dict) -> list[str]:
    stem = str(item.get("stem") or "").lower()
    if "assertion" not in stem or "reason" not in stem:
        return []
    found: dict[str, int] = {}
    for text in _option_texts(item):
        hits = [name for name, pattern in AR_RELATIONS if pattern.search(text)]
        if len(hits) != 1:
            return ["assertion-reason options are not the five standard relations"]
        found[hits[0]] = found.get(hits[0], 0) + 1
    expected = {name for name, _pattern in AR_RELATIONS}
    if set(found) != expected or any(count != 1 for count in found.values()):
        return ["assertion-reason options are not the five standard relations"]
    return []


def structural_errors(item: dict, unit: dict | None = None, records: list | None = None) -> list[str]:
    """Invariant 8 and 9. Empty means the raw item passed the code checks."""
    if not isinstance(item, dict):
        return ["item is not an object"]
    errors: list[str] = []
    blob = _student_blob(item)
    low = blob.lower()
    if META_RE.search(blob):
        errors.append("candidate text contains an mx_id or a banned meta phrase")
    rows = records if isinstance(records, list) else []
    if unit and isinstance(unit.get("mx_records"), list):
        rows = rows or unit["mx_records"]
    for rec in rows:
        if not isinstance(rec, dict):
            continue
        mx_id = str(rec.get("mx_id") or "").strip()
        if mx_id and mx_id in blob:
            errors.append(f"candidate text contains {mx_id}")
        border = rec.get("border") if isinstance(rec.get("border"), dict) else {}
        border_text = str(border.get("text") or "").strip()
        if len(border_text) >= 24 and border_text.lower() in low:
            errors.append("candidate text copies a border")
    if isinstance(unit, dict):
        for label in ("law", "decision"):
            sentence = str(unit.get(label) or "").strip()
            if len(sentence) >= 24 and sentence.lower() in low:
                errors.append(f"candidate text copies the {label}")
        if unit.get("entities") and VAGUE_RE.search(blob):
            errors.append('candidate text says "the material" or "the substance"')
    worked = item.get("worked_solution") if isinstance(item.get("worked_solution"), dict) else {}
    result = str(worked.get("result") or "").strip()
    keyed = _keyed_option_text(item)
    if result and keyed and result != keyed:
        errors.append("worked_solution.result does not equal the keyed option text")
    stem = str(item.get("stem") or "")
    used: list[str] = []
    for text in _option_texts(item):
        if not re.search(r"\b(?:and|only)\b|,", text, re.I):
            continue
        for label in ROMAN_RE.findall(text):
            if label not in used:
                used.append(label)
    missing = [label for label in used if not re.search(rf"\b{label}\b", stem)]
    if missing:
        errors.append("roman labels in options are missing from the stem: " + ", ".join(missing))
    errors.extend(_ar_errors(item))
    return errors


def option_shape_errors(item: dict) -> list[str]:
    """After T-MOD: a choice item must show consecutive options and a bare key."""
    if not isinstance(item, dict):
        return ["item is not an object"]
    kind = str(item.get("item_type") or "")
    if kind not in CHOICE_TYPES:
        return []
    if kind == "three_statement":
        statements = item.get("statements") if isinstance(item.get("statements"), list) else []
        if len(statements) < 2:
            return ["choice item has no statements"]
        return []
    options = item.get("options") if isinstance(item.get("options"), list) else []
    if not options:
        rows = item.get("rows")
        options = rows if isinstance(rows, list) else []
    letters = []
    texts = []
    for index, raw in enumerate(options):
        if isinstance(raw, dict):
            letters.append(str(raw.get("id") or chr(65 + index)).strip().upper()[:1])
            texts.append(str(raw.get("text") or "").strip())
        else:
            letters.append(chr(65 + index))
            texts.append(str(raw).strip())
    errors: list[str] = []
    stem = str(item.get("stem") or "").lower()
    assertion_reason = "assertion" in stem and "reason" in stem
    four = kind in {"single_mcq", "options_are_figure"} and not assertion_reason
    if four:
        if len(texts) != 4:
            errors.append("single_mcq must have four options")
            return errors
    elif len(texts) < 2:
        errors.append("choice item has no wrong options")
        return errors
    expected = [chr(65 + i) for i in range(len(letters))]
    if letters != expected:
        errors.append("option letters are not consecutive from A")
    if assertion_reason:
        return errors
    keyed = _keyed_option_text(item)
    if keyed and REASON_RE.search(keyed):
        others = [text for text in texts if text != keyed]
        if others and not all(REASON_RE.search(text) for text in others):
            errors.append("keyed option explains the answer")
    return errors


def enforce_locked_type(item: dict, req: dict) -> str:
    """Refuse only when the caller explicitly locks the format."""
    if not isinstance(item, dict):
        return "item is not an object"
    if not (req or {}).get("lock_format"):
        return ""
    locked = str((req or {}).get("lock_item_type") or (req or {}).get("source_item_type") or "").strip()
    kind = str(item.get("item_type") or "")
    if locked in CHOICE_TYPES and kind in {"open_response", "structured_parts", "open"}:
        return "choice item was rewritten as free response"
    if locked in CHOICE_TYPES:
        item["item_type"] = locked
    return ""
