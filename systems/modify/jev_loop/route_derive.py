"""T-MOD derives wrong answers from the sitting question.

The stem and the key, or the free-response situation, already exist. Stored map
sentences are not the option source. Each of the eight routes is tested on this
situation. A combination is used only when the decision needs two composing
steps. When two routes reach one result, the item keeps that result once, as
the result itself.
"""
from __future__ import annotations

import re

ROUTES = (
    "term_substitution",
    "condition_omission",
    "relationship_reversal",
    "scope_error",
    "surface_feature_capture",
    "mechanism_conflation",
    "operation_confusion",
    "everyday_replacement",
)

FREE_TYPES = {
    "open",
    "open_response",
    "structured",
    "structured_parts",
    "practical",
    "paper_3",
    "paper_5",
    "lab",
    "worked_response",
    "project_extended",
}

_REASON = re.compile(
    r"\b(?:because|since|therefore|thus|hence|which means|for each|as a result|given that|this means|so)\b",
    re.IGNORECASE,
)
_ROUTE_WORD = re.compile("|".join(ROUTES), re.IGNORECASE)

ROUTE_TESTS = """
Routes. Attempt each one. Keep an attempt only when its test is met.
- term_substitution: a named term is swapped with a sibling term, and the swap makes the claim false.
- condition_omission: a condition the decision requires is dropped, and what remains is a stateable false claim.
- relationship_reversal: the decision has an asymmetric directed relation or a monotonic map, and the option swaps its poles or its direction. A bare denial of the correct claim is not reversal.
- scope_error: a domain or boundary is stretched or narrowed.
- surface_feature_capture: a salient surface (a word, a symbol, a repeated number) replaces the real criterion.
- mechanism_conflation: a neighbouring mechanism the student could actually run is used in place of the decision. Name that neighbour. If you cannot name one, do not use this route.
- operation_confusion: the decision is a procedure with non-interchangeable steps or operands, and the option swaps those steps or operands. A meaning or a classification is not a procedure.
- everyday_replacement: an ordinary-life picture replaces the taught mechanism. A familiar noun this grade already uses does not by itself close the route. The route stays closed when the belief is a second taught mechanism or the technical name of a process.

A combination is two of these tests, each met on its own part, whose results compose to one option. Use one only when the decision needs two composing steps. Applying one route twice to two different comparisons counts. A nearby value, or three or more independent edits of the correct result, is not one combination.
""".strip()

SAME_OUTPUT = (
    "Each wrong result has an output: the bare result, in the same kind as the correct result, "
    "including a unit when the correct result has a unit. The candidate-facing text is that output. "
    "It does not name a route, and it does not explain how the result was reached. "
    "If two routes arrive at the same output, keep that output once. "
    "Do not also write a sentence that shows the reasoning and ends at the same result. "
    "Record every route that produced it on the teacher side."
)


def _item(source: dict) -> dict:
    if not isinstance(source, dict):
        return {}
    inner = source.get("item")
    if isinstance(inner, dict) and (inner.get("stem") or inner.get("options") or inner.get("parts")):
        return inner
    return source


def _norm(text: str) -> str:
    raw = str(text or "").strip().lower()
    raw = raw.replace("−", "-").replace("–", "-").replace("—", "-").replace("×", "x")
    raw = raw.replace("°", " deg ")
    raw = re.sub(r"\s+", " ", raw).strip(" .;")
    return raw


def _has_reason(text: str) -> bool:
    return bool(_REASON.search(str(text or "")))


def _terminal(text: str) -> str:
    raw = str(text or "")
    matches = list(_REASON.finditer(raw))
    if not matches:
        return raw.strip()
    return raw[matches[-1].end():].strip(" .;,")


def _bare_claim(text: str) -> str:
    """The result without a because-clause that explains it."""
    raw = str(text or "").strip()
    match = re.match(
        r"^(.*?)(?:[,;:]|\s)+(?=(?:because|since)\b)",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match and match.group(1).strip():
        return match.group(1).strip(" .;")
    if _has_reason(raw):
        terminal = _terminal(raw)
        if terminal and terminal != raw:
            return terminal
    return raw


def _bounded_contains(hay: str, needle: str) -> bool:
    if not needle or not hay or len(needle) < 2:
        return False
    if needle == hay:
        return True
    return re.search(r"(?<![\w.])" + re.escape(needle) + r"(?![\w.])", hay) is not None


def _option_map(item: dict) -> dict[str, str]:
    opts = item.get("options")
    out: dict[str, str] = {}
    if isinstance(opts, dict):
        for key, value in opts.items():
            letter = str(key).strip().upper()[:1]
            text = value.get("text") if isinstance(value, dict) else value
            if letter:
                out[letter] = str(text or "").strip()
        return out
    if isinstance(opts, list):
        for index, raw in enumerate(opts):
            if isinstance(raw, dict):
                letter = str(raw.get("id") or raw.get("letter") or chr(65 + index)).strip().upper()[:1]
                out[letter] = str(raw.get("text") or "").strip()
            elif isinstance(raw, str):
                out[chr(65 + index)] = raw.strip()
    return out


def _key_letters(item: dict) -> list[str]:
    letters: list[str] = []
    answer = item.get("answer") if isinstance(item.get("answer"), dict) else {}
    one = str(answer.get("letter") or "").strip().upper()[:1]
    if one:
        letters.append(one)
    many = answer.get("letters")
    if isinstance(many, list):
        for token in many:
            letter = str(token).strip().upper()[:1]
            if letter and letter not in letters:
                letters.append(letter)
    assess = item.get("assessment") if isinstance(item.get("assessment"), dict) else {}
    mcq = str(assess.get("mcq_key") or item.get("correct") or "").strip().upper()
    if len(mcq) == 1 and mcq not in letters:
        letters.append(mcq)
    elif len(mcq) > 1 and all(ch in "ABCDEF" for ch in mcq):
        for ch in mcq:
            if ch not in letters:
                letters.append(ch)
    return letters


def is_free_response(item: dict) -> bool:
    kind = str(item.get("item_type") or "").strip().lower()
    if kind in FREE_TYPES or kind == "three_statement":
        return True
    answer = item.get("answer") if isinstance(item.get("answer"), dict) else {}
    if answer.get("kind") in {"rubric", "part_answers", "statement_pattern"}:
        return True
    if item.get("parts") and not item.get("options"):
        return True
    return False


def canonical_free_type(item: dict) -> str:
    kind = str(item.get("item_type") or "")
    if kind == "three_statement":
        return "three_statement"
    if item.get("parts") or kind in {"structured", "structured_parts", "worked_response", "project_extended"}:
        return "structured_parts"
    return "open_response"


def situation_of(source: dict) -> dict:
    """The question the routes are tested against. No map sentences."""
    item = _item(source)
    stem = str(item.get("stem") or "").strip()
    if not stem:
        return {"error": "no question situation"}
    from packet import packed_item_type

    free = is_free_response(item)
    letters = _key_letters(item)
    options = _option_map(item)
    key_text = options.get(letters[0], "") if letters else ""
    if not free and not letters:
        return {"error": "no keyed claim"}
    if not free and letters and not key_text:
        return {"error": "no keyed claim"}
    return {
        "error": "",
        "mode": "situation" if free else "choice",
        "item": item,
        "item_type": canonical_free_type(item) if free else packed_item_type(item),
        "stem": stem,
        "key_letters": letters,
        "key_text": key_text,
        "options": options,
        "parts": item.get("parts") if isinstance(item.get("parts"), list) else [],
        "statements": item.get("statements") if isinstance(item.get("statements"), list) else [],
        "answer": item.get("answer") if isinstance(item.get("answer"), dict) else {},
        "tikz": item.get("tikz") or "",
        "tables": item.get("tables") if isinstance(item.get("tables"), list) else [],
    }


def _routes_of(slot: dict) -> list[str]:
    found: list[str] = []
    raw_routes = slot.get("routes")
    names = []
    if isinstance(slot.get("route"), str):
        names.append(slot["route"])
    if isinstance(raw_routes, str):
        names.append(raw_routes)
    elif isinstance(raw_routes, list):
        names.extend(str(name) for name in raw_routes)
    for name in names:
        for part in re.split(r"\s*(?:\+|and|,)\s*", name):
            part = part.strip()
            if part and part not in found:
                found.append(part)
    return found


def _same_output(left: dict, right: dict) -> bool:
    left_out = _norm(left.get("output"))
    right_out = _norm(right.get("output"))
    if left_out and right_out:
        return left_out == right_out
    left_text = _norm(left.get("text"))
    right_text = _norm(right.get("text"))
    if left_text and left_text == right_text:
        return True
    if _reasoned_reaches(left, right_text):
        return True
    if _reasoned_reaches(right, left_text):
        return True
    return False


def _reasoned_reaches(reasoned: dict, bare_text: str) -> bool:
    """True when a reasoned option's result is the other option's bare text."""
    if not bare_text or not _has_reason(reasoned.get("text")) or _has_reason(bare_text):
        return False
    full = _norm(reasoned.get("text"))
    if not _bounded_contains(full, bare_text):
        return False
    terminal = _norm(_terminal(reasoned.get("text")))
    if terminal and terminal != bare_text and not _bounded_contains(terminal, bare_text):
        return False
    return True


def _clean_output(slot: dict) -> str:
    raw = str(slot.get("output") or "").strip()
    if raw and not _has_reason(raw):
        return raw
    return ""


def _group_text(group: list[dict]) -> str:
    bare = [slot for slot in group if str(slot.get("text") or "").strip() and not _has_reason(slot.get("text"))]
    outputs = []
    for slot in group:
        clean = _clean_output(slot)
        if clean and clean not in outputs:
            outputs.append(clean)
    shared = outputs[0] if outputs else ""
    if bare:
        if shared:
            for slot in bare:
                if _norm(slot.get("text")) == _norm(shared):
                    return str(slot.get("text")).strip()
        bare.sort(key=lambda slot: (len(str(slot.get("text"))), str(slot.get("id") or "")))
        return str(bare[0].get("text")).strip()
    if shared:
        return shared
    group.sort(key=lambda slot: (len(str(slot.get("text"))), str(slot.get("id") or "")))
    return str(group[0].get("text") or "").strip()


def collapse_slots(slots: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep one bare result when two slots name the same output.

    Keys are not slots here. A single slot whose text explains its own bare
    output is reduced to that output. Distinct outputs stay.
    """
    parent = list(range(len(slots)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a

    for i in range(len(slots)):
        for j in range(i + 1, len(slots)):
            if _same_output(slots[i], slots[j]):
                union(i, j)
    groups: dict[int, list[dict]] = {}
    for index, slot in enumerate(slots):
        groups.setdefault(find(index), []).append(slot)
    kept: list[dict] = []
    dropped: list[dict] = []
    for group in groups.values():
        text = _group_text(group)
        chosen = group[0]
        for slot in group:
            if str(slot.get("text") or "").strip() == text:
                chosen = slot
                break
        else:
            bare = [slot for slot in group if not _has_reason(slot.get("text"))]
            if bare:
                chosen = sorted(bare, key=lambda slot: len(str(slot.get("text"))))[0]
        routes: list[str] = []
        for slot in group:
            for name in _routes_of(slot):
                if name not in routes:
                    routes.append(name)
        kept.append({
            "id": str(chosen.get("id") or "").strip(),
            "text": text,
            "output": text,
            "routes": routes,
            "why": " ".join(str(slot.get("why") or "").strip() for slot in group if str(slot.get("why") or "").strip()),
            "variable": chosen.get("variable") or "",
        })
        for slot in group:
            if slot is chosen:
                continue
            dropped.append({
                "id": str(slot.get("id") or "").strip(),
                "text": str(slot.get("text") or "").strip(),
                "output": text,
                "routes": _routes_of(slot),
            })
    return kept, dropped


def _raw_item(raw: dict) -> dict:
    if not isinstance(raw, dict):
        return {}
    if raw.get("stem") or raw.get("options") or raw.get("parts"):
        return raw
    inner = raw.get("item")
    if isinstance(inner, dict):
        merged = dict(inner)
        for key in ("status", "refusal_reason", "answer", "teacher", "item_type"):
            if key not in merged and key in raw:
                merged[key] = raw[key]
        return merged
    items = raw.get("items")
    if isinstance(items, list) and items and isinstance(items[0], dict):
        return items[0]
    return raw


def _slots_from_options(options) -> list[dict]:
    slots = []
    if isinstance(options, dict):
        rows = [{"id": key, **value} if isinstance(value, dict) else {"id": key, "text": value} for key, value in options.items()]
    elif isinstance(options, list):
        rows = options
    else:
        return slots
    for index, raw in enumerate(rows):
        if isinstance(raw, str):
            slots.append({"id": chr(65 + index), "text": raw, "output": raw, "route": "", "routes": [], "why": ""})
            continue
        if not isinstance(raw, dict):
            continue
        letter = str(raw.get("id") or raw.get("letter") or chr(65 + index)).strip().upper()[:1]
        text = str(raw.get("text") or "").strip()
        output = str(raw.get("output") or "").strip()
        slots.append({
            "id": letter,
            "text": text,
            "output": output,
            "route": raw.get("route") or "",
            "routes": raw.get("routes") or [],
            "why": raw.get("why") or "",
            "role": raw.get("role") or "",
        })
    return slots


def _publish_choice(options: list[dict], key_letters: list[str], route_map: dict) -> tuple[list[dict], dict, dict]:
    """Published options are A, B, C... with no gap. The key letter moves with the key."""
    ordered = [dict(row) for row in options if str(row.get("text") or "").strip()]
    ordered.sort(key=lambda row: str(row.get("id") or ""))
    mapping = {}
    published = []
    for index, row in enumerate(ordered):
        new_id = chr(65 + index)
        old_id = str(row.get("id") or new_id)
        mapping[old_id] = new_id
        published.append({"id": new_id, "text": row["text"]})
    new_keys = [mapping.get(letter, letter) for letter in key_letters if mapping.get(letter)]
    if not new_keys and published:
        new_keys = [published[0]["id"]]
    remapped = {}
    for old_id, payload in route_map.items():
        new_id = mapping.get(old_id)
        if new_id:
            remapped[new_id] = payload
    if len(new_keys) > 1:
        answer = {"kind": "letter_set", "letters": new_keys}
    else:
        answer = {"kind": "single_letter", "letter": new_keys[0] if new_keys else "A"}
    return published, answer, remapped


FOUR_OPTION_TYPES = {"single_mcq", "options_are_figure", "option_table"}


def _is_assertion_reason(item: dict) -> bool:
    stem = str((item or {}).get("stem") or "").lower()
    return "assertion" in stem and "reason" in stem


def needs_four_options(item: dict) -> bool:
    if not isinstance(item, dict):
        return False
    if str(item.get("item_type") or "") not in FOUR_OPTION_TYPES:
        return False
    if _is_assertion_reason(item):
        return False
    answer = item.get("answer") if isinstance(item.get("answer"), dict) else {}
    if answer.get("kind") == "letter_set":
        return False
    return True


def _rank_rows(rows: list[dict], ranker, route_map: dict) -> list[dict]:
    scores = {}
    if ranker:
        try:
            scores = ranker(rows) or {}
        except Exception:
            scores = {}

    def sort_key(row: dict):
        token = str(row.get("id") or "")
        jev = float(scores.get(token) or 0)
        routes = len(((route_map.get(token) or {}).get("routes")) or [])
        return (-jev, -routes, token)

    return sorted(rows, key=sort_key)


def keep_best_distractors(item: dict, ranker=None, want: int = 3) -> tuple[dict | None, dict]:
    """Keep the key plus the three strongest distractors on a standard MCQ."""
    if not needs_four_options(item):
        return item, {"skipped": True}
    answer = item.get("answer") if isinstance(item.get("answer"), dict) else {}
    key_letter = str(answer.get("letter") or "A").strip().upper()[:1]
    options = [row for row in (item.get("options") or []) if isinstance(row, dict)]
    key_rows = [row for row in options if str(row.get("id") or "").upper()[:1] == key_letter]
    wrong = [row for row in options if str(row.get("id") or "").upper()[:1] != key_letter]
    teacher = dict(item.get("teacher") or {}) if isinstance(item.get("teacher"), dict) else {}
    route_map = teacher.get("route_map") if isinstance(teacher.get("route_map"), dict) else {}

    def nroutes(row: dict) -> int:
        return len(((route_map.get(str(row.get("id") or "")) or {}).get("routes")) or [])

    dual = [row for row in wrong if nroutes(row) >= 2]
    rest = [row for row in wrong if nroutes(row) < 2]
    if len(wrong) < want:
        return None, {"error": "single_mcq needs three distractors", "have": len(wrong)}
    if len(dual) >= want:
        ranked = _rank_rows(dual, ranker, route_map)
        picked, unused = ranked[:want], ranked[want:] + rest
    else:
        ranked_rest = _rank_rows(rest, ranker, route_map)
        need = want - len(dual)
        picked = list(dual) + ranked_rest[:need]
        unused = ranked_rest[need:]
    teacher["unused_distractors"] = [
        {
            "id": str(row.get("id") or ""),
            "text": str(row.get("text") or ""),
            "routes": ((route_map.get(str(row.get("id") or "")) or {}).get("routes")) or [],
        }
        for row in unused
    ]
    keep_map = {}
    for row in picked:
        payload = route_map.get(str(row.get("id") or ""))
        if payload:
            keep_map[str(row.get("id") or "")] = payload
    published, answer, remapped = _publish_choice(key_rows + picked, [key_letter], keep_map)
    item["options"] = published
    item["answer"] = answer
    teacher["route_map"] = remapped
    item["teacher"] = teacher
    return item, {"kept": len(picked), "unused": len(unused), "dual_kept": sum(1 for row in picked if nroutes(row) >= 2)}


def _teacher(body: dict, variation: str, route_map: dict, report: dict) -> dict:
    incoming = body.get("teacher") if isinstance(body.get("teacher"), dict) else {}
    teacher = {
        "variation_applied": variation,
        "proposed_key_status": "UNVERIFIED",
        "route_map": route_map,
        "same_output_dropped": report.get("dropped") or [],
    }
    for key in ("stem_decision", "keyed_claim", "situation_features"):
        if incoming.get(key):
            teacher[key] = incoming[key]
        elif body.get(key):
            teacher[key] = body[key]
    return teacher


def _finish_choice(body: dict, sit: dict, variation: str) -> tuple[dict, dict]:
    key_letters = set(sit["key_letters"])
    key_text = sit["key_text"]
    slots = []
    for slot in _slots_from_options(body.get("options")):
        if slot["id"] in key_letters or str(slot.get("role") or "").lower() == "key":
            continue
        if not slot["text"] and not slot["output"]:
            continue
        slots.append(slot)
    kept, dropped = collapse_slots(slots)
    key_text = _bare_claim(key_text) or key_text
    key_norm = _norm(key_text)
    distractors = []
    seen = set(key_letters)
    route_map = {}
    for slot in kept:
        if not slot["id"] or slot["id"] in seen:
            dropped.append({"id": slot["id"], "text": slot["text"], "output": slot["output"], "routes": slot["routes"]})
            continue
        if _norm(slot["text"]) == key_norm or _norm(_bare_claim(slot["text"])) == key_norm:
            dropped.append({"id": slot["id"], "text": slot["text"], "output": slot["output"], "routes": slot["routes"]})
            continue
        seen.add(slot["id"])
        distractors.append({"id": slot["id"], "text": slot["text"]})
        route_map[slot["id"]] = {"routes": slot["routes"], "output": slot["text"]}
    options = [{"id": letter, "text": key_text} for letter in sit["key_letters"]]
    options.extend(distractors)
    options, answer, route_map = _publish_choice(options, sit["key_letters"], route_map)
    report = {"dropped": dropped, "mode": "choice"}
    if len(options) < 2:
        return None, {"error": "choice item has no wrong options", "dropped": dropped, "mode": "choice"}
    item = {
        "schema": "modify_result.v1",
        "status": "OK",
        "item_type": sit["item_type"],
        "stem": sit["stem"],
        "options": options,
        "statements": sit["statements"],
        "parts": sit["parts"],
        "tables": sit["tables"],
        "tikz": sit["tikz"],
        "answer": answer,
        "teacher": _teacher(body, variation, route_map, report),
    }
    return item, report


def _strip_dropped(text: str, dropped: list[dict]) -> str:
    banned = {_norm(row.get("text")) for row in dropped if row.get("text")}
    if not banned or not text:
        return text
    parts = re.split(r"(?<=[.?;])\s+", text.strip())
    kept = [part for part in parts if _norm(part) not in banned]
    if not kept:
        return ""
    return " ".join(kept).strip()


def _finish_situation(body: dict, sit: dict, variation: str) -> tuple[dict, dict]:
    records = body.get("route_records")
    if not isinstance(records, list):
        teacher = body.get("teacher") if isinstance(body.get("teacher"), dict) else {}
        records = teacher.get("route_records") if isinstance(teacher.get("route_records"), list) else []
    slots = []
    for index, raw in enumerate(records):
        if not isinstance(raw, dict):
            continue
        slots.append({
            "id": str(raw.get("id") or raw.get("variable") or chr(65 + index)),
            "text": str(raw.get("text") or raw.get("output") or "").strip(),
            "output": str(raw.get("output") or "").strip(),
            "route": raw.get("route") or "",
            "routes": raw.get("routes") or [],
            "why": raw.get("why") or "",
            "variable": raw.get("variable") or "",
        })
    kept, dropped = collapse_slots(slots)
    route_records = []
    for slot in kept:
        if _ROUTE_WORD.search(slot["text"]):
            slot["text"] = _ROUTE_WORD.sub("", slot["text"]).strip(" .;")
        route_records.append({
            "output": slot["text"],
            "routes": slot["routes"],
            "variable": slot.get("variable") or "",
        })
    stem = _strip_dropped(str(body.get("stem") or sit["stem"]).strip(), dropped) or sit["stem"]
    parts = body.get("parts") if isinstance(body.get("parts"), list) and body.get("parts") else sit["parts"]
    source_parts = {
        str(part.get("id")): part
        for part in sit["parts"]
        if isinstance(part, dict)
    }
    clean_parts = []
    for index, part in enumerate(parts):
        if isinstance(part, str):
            prompt = _strip_dropped(part, dropped)
            clean_parts.append({"id": str(index + 1), "prompt": prompt})
            continue
        if not isinstance(part, dict):
            continue
        prompt = _strip_dropped(str(part.get("prompt") or part.get("text") or ""), dropped)
        if not prompt:
            source = source_parts.get(str(part.get("id") or ""))
            prompt = str((source or {}).get("prompt") or (source or {}).get("text") or "")
        row = dict(part)
        if part.get("prompt") is not None or "text" not in part:
            row["prompt"] = prompt
        else:
            row["text"] = prompt
        row.setdefault("id", str(index + 1))
        clean_parts.append(row)
    answer = body.get("answer") if isinstance(body.get("answer"), dict) else {}
    if sit["item_type"] == "structured_parts":
        if answer.get("kind") != "part_answers":
            answer = sit["answer"] if sit["answer"].get("kind") == "part_answers" else {
                "kind": "part_answers",
                "part_answers": [
                    {"part_id": row.get("id"), "answer": str(row.get("answer") or "")}
                    for row in clean_parts
                ],
            }
    elif sit["item_type"] == "three_statement":
        if answer.get("kind") != "statement_pattern":
            answer = sit["answer"] if sit["answer"].get("kind") == "statement_pattern" else {
                "kind": "statement_pattern",
                "pattern": str((sit["answer"] or {}).get("pattern") or body.get("keyed_claim") or ""),
            }
    elif answer.get("kind") != "rubric" or not str(answer.get("rubric") or "").strip():
        if sit["answer"].get("kind") == "rubric" and sit["answer"].get("rubric"):
            answer = sit["answer"]
        else:
            answer = {"kind": "rubric", "rubric": str(body.get("keyed_claim") or sit["key_text"] or sit["stem"])}
    report = {"dropped": dropped, "mode": "situation"}
    teacher = _teacher(body, variation, {row["output"]: {"routes": row["routes"]} for row in route_records}, report)
    teacher["route_records"] = route_records
    statements = body.get("statements") if isinstance(body.get("statements"), list) and body.get("statements") else sit["statements"]
    item = {
        "schema": "modify_result.v1",
        "status": "OK",
        "item_type": sit["item_type"],
        "stem": stem,
        "options": [] if sit["item_type"] != "option_table" else (body.get("options") or []),
        "statements": statements or [],
        "parts": clean_parts,
        "tables": body.get("tables") if isinstance(body.get("tables"), list) else sit["tables"],
        "tikz": sit["tikz"] or "",
        "answer": answer,
        "teacher": teacher,
    }
    return item, report


def finish_item(raw: dict, source: dict, variation: str) -> tuple[dict | None, dict]:
    """Apply the route gate to a writer draft. Stem and key stay on a choice item."""
    sit = situation_of(source)
    if sit.get("error"):
        return None, {"error": sit["error"]}
    body = _raw_item(raw if isinstance(raw, dict) else {})
    status = str(body.get("status") or "OK").upper()
    if status == "REFUSED":
        return None, {"error": str(body.get("refusal_reason") or "writer refused")}
    if sit["mode"] == "choice":
        return _finish_choice(body, sit, variation)
    return _finish_situation(body, sit, variation)


def _situation_block(sit: dict) -> str:
    lines = ["Stem:", sit["stem"], ""]
    if sit["mode"] == "choice":
        lines.append("Keyed option (fixed): " + ", ".join(sit["key_letters"]) + " — " + sit["key_text"])
        return "\n".join(lines)
    if sit["parts"]:
        lines.append("Existing parts:")
        for index, part in enumerate(sit["parts"]):
            if isinstance(part, dict):
                lines.append(
                    str(part.get("id") or index + 1)
                    + ". "
                    + str(part.get("prompt") or part.get("text") or "")
                )
            else:
                lines.append(str(part))
    if sit["answer"]:
        lines.append("Expected answer (teacher-side): " + str(sit["answer"]))
    return "\n".join(lines)


def prompt_for(sit: dict, req: dict, variation: str) -> str:
    """Writer instructions. The map packet is not included."""
    head = (
        "Return modify_result.v1 JSON only. status OK or REFUSED. No markdown.\n"
        f"Grade {req.get('grade')} {req.get('subject')}. Item type {sit.get('item_type')}.\n"
        "The question situation is already built. Test the routes on that situation. "
        "Do not paste a stored mix-up sentence, and do not cite a stored mix-up id.\n\n"
        + _situation_block(sit)
        + "\n\n"
        + ROUTE_TESTS
        + "\n\n"
        + SAME_OUTPUT
        + "\n"
    )
    intent = str(req.get("intent") or "").strip()
    if intent:
        head += (
            "\nTeacher note (do not print, and do not let it replace a route test): "
            + intent[:1000]
            + "\n"
        )
    if sit.get("mode") == "choice":
        tail = (
            "\nThe stem stays. The keyed option is the bare result, with no because-clause. "
            "If the handed key explains itself, keep only the result. Write only the wrong options.\n"
            "Before writing, state the decision this stem asks, the keyed claim in this stem's quantities, "
            "and the situation features a wrong step could use.\n"
            "Write every surviving route as an option of the same kind as the key. "
            "A standard single-key MCQ keeps the keyed result plus the three strongest distractors. "
            "A result reached by two routes is kept. The harness selects those three; write all survivors. "
            "Published letters are consecutive from A. "
            "Do not fill a slot with 'cannot be determined', 'none of these', or the mere opposite of the key.\n"
            "Flat JSON: status, stem, item_type, options as a list of {id, text, output, route, routes, why}, "
            "answer, teacher. why is teacher-side. text is the bare output.\n"
            f"teacher.variation_applied is {variation}. teacher.proposed_key_status is UNVERIFIED.\n"
        )
    else:
        tail = (
            "\nThis is a free-response question. Derive the route mixups from the situation above, "
            "then write the complete question.\n"
            "The variables are the quantities, conditions, and steps already in the situation. "
            "The situation and the expected answer stay. Carry a variable only so that a surviving route "
            "is an error a student would make. Do not replace the situation or the expected answer.\n"
            "The student-facing stem and parts state the question. They do not name a route and they do not explain a wrong method.\n"
            "If two routes reach the same output, the question carries that output once.\n"
            "Flat JSON: status, stem, item_type, parts, answer, teacher. "
            "teacher.route_records is a list of {route, routes, output, variable, why}. "
            "output is the bare wrong result.\n"
            f"item_type is {sit.get('item_type')}. "
            f"teacher.variation_applied is {variation}. teacher.proposed_key_status is UNVERIFIED.\n"
        )
    return head + tail
