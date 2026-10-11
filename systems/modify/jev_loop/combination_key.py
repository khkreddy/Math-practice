"""Turn a multi-select into one single-key combination item.

The supported claims stay in the stem as I, II, III. Each option is a different
set of those labels. The keyed option is the full supported set. Every other
set adds at least one unsupported claim, and that option keeps the mix-up
already bound to that claim.
"""
from __future__ import annotations

import copy
import re
from typing import Any

_ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
_ROMAN_ORDER = {label: index for index, label in enumerate(_ROMAN) if label}


def _roman(index: int) -> str:
    if 1 <= index < len(_ROMAN):
        return _ROMAN[index]
    return str(index)


def format_set(labels: list[str] | tuple[str, ...]) -> str:
    ordered = list(labels)
    if len(ordered) == 1:
        return f"{ordered[0]} only"
    if len(ordered) == 2:
        return f"{ordered[0]} and {ordered[1]}"
    return ", ".join(ordered[:-1]) + ", and " + ordered[-1]


def _pack(labels: list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(labels), key=lambda label: _ROMAN_ORDER.get(label, 99)))


def _letter_of(option: dict, index: int) -> str:
    token = str(option.get("id") or chr(65 + index)).strip().upper()
    return token[:1]


def _scene(stem: str) -> str:
    text = re.sub(r"\s+", " ", (stem or "").strip())
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if parts and parts[-1].lower().startswith("which"):
        parts = parts[:-1]
    scene = " ".join(parts).strip() or text
    scene = scene.rstrip(".!?")
    scene = scene.replace("?", "")
    scene = re.sub(r"[.!]+\s*", "; ", scene)
    scene = re.sub(r"\s+", " ", scene).strip(" ;")
    return scene


def _claim_clause(text: str) -> str:
    clause = re.sub(r"\s+", " ", (text or "").strip())
    clause = clause.rstrip(".!?").replace("?", "")
    clause = clause.replace(".", ",")
    return clause


def collapse_multiselect(item: dict) -> bool:
    """Rewrite one_or_more in place. Returns False when it cannot be a combination key."""
    if not isinstance(item, dict) or item.get("item_type") != "one_or_more":
        return False
    answer = item.get("answer") if isinstance(item.get("answer"), dict) else {}
    keyed = {str(letter).strip().upper()[:1] for letter in (answer.get("letters") or []) if str(letter).strip()}
    options = [opt for opt in (item.get("options") or []) if isinstance(opt, dict)]
    if len(keyed) < 2 or len(options) < 3:
        return False

    ordered: list[str] = []
    by_letter: dict[str, dict] = {}
    for index, opt in enumerate(options):
        letter = _letter_of(opt, index)
        ordered.append(letter)
        by_letter[letter] = opt
    romans = {letter: _roman(index + 1) for index, letter in enumerate(ordered)}
    correct = [romans[letter] for letter in ordered if letter in keyed]
    wrongs: list[dict[str, Any]] = []
    for letter in ordered:
        if letter in keyed:
            continue
        opt = by_letter[letter]
        refs = opt.get("mx_refs") if isinstance(opt.get("mx_refs"), list) else []
        feedback = opt.get("feedback") if isinstance(opt.get("feedback"), dict) else None
        ref = refs[0] if refs and isinstance(refs[0], dict) else None
        if not ref or not ref.get("ref") or not feedback:
            continue
        wrongs.append({"roman": romans[letter], "refs": refs, "feedback": feedback, "mx_id": ref.get("ref")})
    if len(correct) < 2 or not wrongs:
        return False

    key_pack = _pack(correct)
    seen = {key_pack}
    distractors: list[tuple[tuple[str, ...], dict]] = []

    def add(labels: list[str], primary: dict) -> None:
        combo = _pack(labels)
        if not combo or combo in seen or combo == key_pack:
            return
        if not any(wrong["roman"] in combo for wrong in wrongs):
            return
        seen.add(combo)
        distractors.append((combo, primary))

    for wrong in wrongs:
        add(list(key_pack) + [wrong["roman"]], wrong)
    for wrong in wrongs:
        for drop in key_pack:
            add([label for label in key_pack if label != drop] + [wrong["roman"]], wrong)
    add([wrong["roman"] for wrong in wrongs], wrongs[0])
    distractors = distractors[:4]
    if len(distractors) < 2:
        return False

    built: list[dict] = []
    width = 1 + len(distractors)
    key_index = sum(ord(ch) for label in key_pack for ch in label) % width
    cursor = 0
    for index in range(1 + len(distractors)):
        letter = chr(65 + index)
        if index == key_index:
            built.append({"id": letter, "text": format_set(key_pack), "key": True})
            continue
        combo, primary = distractors[cursor]
        cursor += 1
        included = {wrong["roman"] for wrong in wrongs if wrong["roman"] in combo}
        refs: list[dict] = []
        seen_refs: set[str] = set()
        for wrong in wrongs:
            if wrong["roman"] not in included:
                continue
            for ref in wrong["refs"]:
                mx_id = str(ref.get("ref") or "")
                if mx_id and mx_id not in seen_refs:
                    seen_refs.add(mx_id)
                    refs.append(copy.deepcopy(ref))
        built.append({
            "id": letter,
            "text": format_set(combo),
            "key": False,
            "mx_refs": refs,
            "feedback": copy.deepcopy(primary["feedback"]),
            "mx_id": primary["mx_id"],
        })

    claim_bits = [
        f"{romans[letter]} {_claim_clause(str(by_letter[letter].get('text') or ''))}"
        for letter in ordered
    ]
    scene = _scene(str(item.get("stem") or ""))
    item["stem"] = scene + ". Which set of these claims is supported: " + "; ".join(claim_bits) + "?"
    item["item_type"] = "single_mcq"
    item["options"] = [
        {"id": opt["id"], "text": opt["text"]}
        if opt["key"]
        else {"id": opt["id"], "text": opt["text"], "mx_refs": opt["mx_refs"], "feedback": opt["feedback"]}
        for opt in built
    ]
    key_letter = built[key_index]["id"]
    key_text = built[key_index]["text"]
    item["answer"] = {"kind": "single_letter", "letter": key_letter}
    item["mx_option_map"] = {opt["id"]: opt["mx_id"] for opt in built if not opt["key"]}
    item["combination_key"] = {
        "claims": [
            {"id": romans[letter], "text": by_letter[letter].get("text"), "supported": letter in keyed}
            for letter in ordered
        ],
        "supported": list(key_pack),
    }

    ws = item.get("worked_solution")
    if isinstance(ws, dict):
        ws["key_letter"] = key_letter
        ws["result"] = key_text
        ws["why_key"] = "This set contains every supported claim and no unsupported claim."
        steps = [str(step) for step in (ws.get("steps") or []) if key_text.lower() not in str(step).lower()]
        closing = (
            "A set is supported only when it keeps every claim that follows from the evidence "
            "and leaves out every other claim, therefore any set that adds or drops a claim is not supported."
        )
        if not any("therefore" in step.lower() for step in steps):
            steps.append(closing)
        elif all(key_text.lower() in step.lower() for step in steps[-1:]):
            steps.append(closing)
        ws["steps"] = steps[:6] if len(steps) > 6 else steps
        if len(ws["steps"]) < 2:
            ws["steps"] = [
                "Each claim either follows from the given evidence or it does not, therefore the supported claims form one set.",
                closing,
            ]
        ws["distractors"] = [
            {
                "letter": opt["id"],
                "mx_id": opt["mx_id"],
                "why_wrong": "This set adds or drops a claim, so it is not the supported set.",
            }
            for opt in built
            if not opt["key"]
        ]
    return True
