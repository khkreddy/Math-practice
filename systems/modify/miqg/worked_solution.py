"""Complete worked-solution schema and admit-path guards.

Solve completely before framing. Persist the solution on the item in a field
that is never student-facing (MIQG scans stem/options/statements/hints/LBS only).

A complete solution derives the keyed result from explicit givens by hinge
inferences. Template steps that paste map statements or paste the key are refused.
"""
from __future__ import annotations

import re
from typing import Any

WORKED_SOLUTION_SCHEMA = "ttwin.worked_solution.v1"
WORKED_SOLUTION_FIELD = "worked_solution"

# Tutorial imperatives / ontology lectures that stack onto a scene before a vague ask.
_TUTORIAL_IMPERATIVE_RE = re.compile(
    r"(?:"
    r"\bname an angle from (?:its )?vertex and arms\b|"
    r"\bname an? (?:angle|ray|segment|line)\b|"
    r"\bclassify\b.{0,80}\bcorrectly\b|"
    r"\bfor a (?:geometry )?checklist\b|"
    r"\b(?:are |as )?basic objects\b|"
    r"\bbasic objects\b|"
    r"\bclassify a straight path\b|"
    r"\bgenerate an equivalent fraction\b|"
    r"\bwhile preserving the same quantity\b|"
    r"\buse only the final digit\b|"
    r"\busing only (?:its |the )?final digit\b|"
    r"\brecognize that\b|"
    r"\brelate the name\b"
    r")",
    re.I,
)
_VAGUE_CONCLUSION_RE = re.compile(
    r"\bwhat conclusion follows from these facts\b",
    re.I,
)
_CLASSROOM_SCENE_RE = re.compile(
    r"\b(?:classroom|on the (?:class |school )?floor|in (?:a |the )?class(?:room)?|"
    r"a group of students|students record|class activity)\b",
    re.I,
)
_MIDDLE_IMPERATIVE_RE = re.compile(
    r"^(?:Name|Classify|Generate|Use only|Decide whether|Decide how|Recognize|Relate)\b",
    re.I,
)

# Paste-the-key / map-paste template patterns (previous bad harness).
_TEMPLATE_RESULT_PASTE_RE = re.compile(
    r"\bfrom those steps the result is\b",
    re.I,
)
_TEMPLATE_SOFT_PASTE_RE = re.compile(
    r"(?:"
    r"\busing the given facts together with the rule that\b|"
    r"\bit follows that\b|"
    r"\bprimary:\s*from the givens, apply the operative rule\b"
    r")",
    re.I,
)
_TEMPLATE_APPLY_MAP_RE = re.compile(
    r"^apply\s+(?:math|science|igcse)[/\w.:-]+\s*\([^)]*\)\s*:\s*",
    re.I,
)
_TEMPLATE_APPLY_UNIT_RE = re.compile(
    r"^apply\s+\S+/H\d+\b",
    re.I,
)
_TEMPLATE_KEYED_IS_RESULT_RE = re.compile(
    r"^keyed option\s+[A-D]\s+is that result\.?$",
    re.I,
)
_TEMPLATE_GIVENS_USED_RE = re.compile(
    r"^givens used:\s*",
    re.I,
)
_KEY_LEAK_ASK_RE = re.compile(
    r"\bwhich of the following matches these facts\s*:",
    re.I,
)
_WORDCOUNT_PAD_RE = re.compile(
    r"(?:"
    r"\bwith labelled endpoints\b|"
    r"\bdrawn with clear vertex and arm marks\b|"
    r"\bthe figure is drawn on a flat plane with labelled points\b|"
    r"\bthe following facts are given for this decision\b"
    r")",
    re.I,
)
_DOUBLE_ASK_RE = re.compile(
    r"\band\s+how\b.+\?$|\band\s+what\b.+\?$|\?\s*.+\?",
    re.I,
)
_INFER_MARKERS_RE = re.compile(
    r"(?:"
    r"\btherefore\b|\bso\b|\bhence\b|\bthus\b|\bit follows\b|"
    r"\bwhich means\b|\bthis means\b|\bequals?\b|\b=\b|"
    r"\bconclude\b|\bconcludes?\b|\bgives\b|\byields?\b|"
    r"\bimplies?\b|\bmust be\b|\bis therefore\b|"
    r"\bfrom .{1,40}\b(?:we |one )?(?:get|obtain|find|deduce)\b|"
    r"\b\d+(?:\.\d+)?\s*[+\-×*/÷]\s*\d+"
    r")",
    re.I,
)


def opt_text(raw: Any) -> str:
    if isinstance(raw, dict):
        return str(raw.get("text") or "").strip()
    return str(raw or "").strip()


def mcq_key_of(item_or_row: dict) -> str:
    """Letter of the keyed option from bank item or draft shapes."""
    if not isinstance(item_or_row, dict):
        return ""
    item = item_or_row.get("item") if isinstance(item_or_row.get("item"), dict) else item_or_row
    for container in (item_or_row, item):
        if not isinstance(container, dict):
            continue
        assessment = container.get("assessment")
        if isinstance(assessment, dict) and assessment.get("mcq_key"):
            return str(assessment.get("mcq_key")).strip().upper()
        ans = container.get("answer")
        if isinstance(ans, dict) and ans.get("letter"):
            return str(ans.get("letter")).strip().upper()
        if isinstance(ans, str) and ans.strip():
            return ans.strip().upper()
        if container.get("key"):
            return str(container.get("key")).strip().upper()
    return ""


def keyed_option_text(item_or_row: dict) -> str:
    key = mcq_key_of(item_or_row)
    item = item_or_row.get("item") if isinstance(item_or_row.get("item"), dict) else item_or_row
    options = (item or {}).get("options") if isinstance(item, dict) else None
    if not key or options is None:
        return ""
    if isinstance(options, dict):
        return opt_text(options.get(key) or options.get(key.lower()))
    if isinstance(options, list):
        for o in options:
            if isinstance(o, dict) and str(o.get("id") or "").upper() == key:
                return opt_text(o)
    return ""


def sentences(stem: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", (stem or "").strip())
    return [p.strip() for p in parts if p and p.strip()]


def stem_stacked_tutorial_conclusion(stem: str) -> str | None:
    """Detect scene + tutorial imperative + vague conclusion stack.

    Returns a short quote when the class matches; None otherwise.
    Does NOT ban a bare two-sentence 'facts. What conclusion follows…?' exam ask.
    """
    text = (stem or "").strip()
    if not text or not _VAGUE_CONCLUSION_RE.search(text):
        return None
    if _TUTORIAL_IMPERATIVE_RE.search(text):
        m = _TUTORIAL_IMPERATIVE_RE.search(text)
        return (m.group(0) if m else "stacked tutorial + vague conclusion")
    units = sentences(text)
    if len(units) >= 3 and _VAGUE_CONCLUSION_RE.search(units[-1]):
        middle = " ".join(units[1:-1])
        if _MIDDLE_IMPERATIVE_RE.search(middle.strip()) or _TUTORIAL_IMPERATIVE_RE.search(middle):
            return middle[:120]
        if _CLASSROOM_SCENE_RE.search(units[0]) and re.search(
            r"\b(name|classify|generate|checklist|basic objects|recognize that)\b",
            middle,
            re.I,
        ):
            return units[0][:80]
    return None


def facing_stacked_tutorial_conclusion(*texts: str) -> str | None:
    """Run the stacked-ask detector on stem first, then other student-facing strings."""
    for t in texts:
        hit = stem_stacked_tutorial_conclusion(t or "")
        if hit:
            return hit
    return None


def stem_asks_two_quantities(stem: str) -> str | None:
    """Refuse stems with two question marks or a bundled 'how X, and how Y' ask."""
    text = (stem or "").strip()
    if not text:
        return None
    if text.count("?") >= 2:
        return "stem contains more than one question mark"
    if re.search(
        r"\bhow\b.+\band how\b|\bwhat\b.+\band what\b|\bhow\b.+\band what\b",
        text,
        re.I,
    ):
        return "stem bundles two asks with 'and how/what'"
    return None


def stem_has_wordcount_padding(stem: str) -> str | None:
    m = _WORDCOUNT_PAD_RE.search(stem or "")
    return m.group(0) if m else None


def stem_leaks_keyed_claim(stem: str) -> str | None:
    if _KEY_LEAK_ASK_RE.search(stem or ""):
        return "stem embeds the keyed claim in the ask"
    return None


def empty_worked_solution(*, status: str = "held", blocker: str = "") -> dict:
    return {
        "schema": WORKED_SOLUTION_SCHEMA,
        "status": status,
        "blocker": blocker or None,
        "given_facts": [],
        "hinges_used": [],
        "steps": [],
        "result": "",
        "key_letter": "",
        "why_key": "",
        "distractors": [],
        "old_stem_removed": [],
    }


def build_worked_solution(
    *,
    given_facts: list[str],
    hinges_used: list[dict],
    steps: list[str],
    result: str,
    key_letter: str,
    why_key: str,
    distractors: list[dict],
    old_stem_removed: list[str],
    status: str = "complete",
    blocker: str | None = None,
) -> dict:
    return {
        "schema": WORKED_SOLUTION_SCHEMA,
        "status": status,
        "blocker": blocker,
        "given_facts": list(given_facts),
        "hinges_used": list(hinges_used),
        "steps": list(steps),
        "result": (result or "").strip(),
        "key_letter": str(key_letter or "").strip().upper(),
        "why_key": (why_key or "").strip(),
        "distractors": list(distractors),
        "old_stem_removed": list(old_stem_removed),
    }


def get_worked_solution(item_or_row: dict) -> dict | None:
    if not isinstance(item_or_row, dict):
        return None
    for container in (
        item_or_row,
        item_or_row.get("item") if isinstance(item_or_row.get("item"), dict) else None,
        item_or_row.get("draft") if isinstance(item_or_row.get("draft"), dict) else None,
    ):
        if not isinstance(container, dict):
            continue
        ws = container.get(WORKED_SOLUTION_FIELD)
        if isinstance(ws, dict) and ws:
            return ws
    return None


def _norm_claim(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(".")
    return s


def solution_result_matches_key(ws: dict, item_or_row: dict) -> bool:
    """True when worked_solution.result is the keyed option text (asked quantity)."""
    if not isinstance(ws, dict):
        return False
    key = str(ws.get("key_letter") or mcq_key_of(item_or_row) or "").strip().upper()
    if not key or key != mcq_key_of(item_or_row):
        return False
    result = _norm_claim(str(ws.get("result") or ""))
    keyed = _norm_claim(keyed_option_text(item_or_row))
    if not result or not keyed:
        return False
    return result == keyed or result in keyed or keyed in result


def _hinge_statements_from_context(item_or_row: dict) -> list[str]:
    stmts: list[str] = []
    for container in (
        item_or_row,
        item_or_row.get("item") if isinstance(item_or_row.get("item"), dict) else None,
        item_or_row.get("design") if isinstance(item_or_row.get("design"), dict) else None,
    ):
        if not isinstance(container, dict):
            continue
        design = container if "hinges" in container and isinstance(container.get("hinges"), list) else None
        if design is None and isinstance(container.get("design"), dict):
            design = container["design"]
        if not isinstance(design, dict):
            continue
        for h in design.get("hinges") or []:
            if isinstance(h, dict) and h.get("statement"):
                stmts.append(str(h["statement"]))
        # also top-level design on row
    design = item_or_row.get("design") if isinstance(item_or_row, dict) else None
    if isinstance(design, dict):
        for h in design.get("hinges") or []:
            if isinstance(h, dict) and h.get("statement"):
                stmts.append(str(h["statement"]))
    qi = item_or_row.get("question_ingest") if isinstance(item_or_row, dict) else None
    if isinstance(qi, dict):
        for u in qi.get("units") or []:
            if isinstance(u, dict) and u.get("statement"):
                stmts.append(str(u["statement"]))
    # de-dupe
    seen = set()
    out = []
    for s in stmts:
        n = _norm_claim(s)
        if n and n not in seen:
            seen.add(n)
            out.append(s)
    return out


def steps_look_like_template(steps: list, *, keyed_text: str = "", hinge_statements: list[str] | None = None) -> str | None:
    """Return a refuse reason when steps are the apply-map-then-paste-key template."""
    if not steps:
        return "steps missing"
    texts = [str(s).strip() for s in steps if str(s).strip()]
    if len(texts) < 2:
        return "steps too short to be a derivation"

    keyed_n = _norm_claim(keyed_text)
    hinge_norms = {_norm_claim(h) for h in (hinge_statements or []) if h}

    soft_paste = 0
    hard_paste = 0
    apply_hits = 0
    intermediate_infer = 0
    for t in texts:
        low = t.lower().strip()
        if _TEMPLATE_RESULT_PASTE_RE.search(t) or _TEMPLATE_KEYED_IS_RESULT_RE.search(t):
            hard_paste += 1
            continue
        if _TEMPLATE_SOFT_PASTE_RE.search(t):
            soft_paste += 1
            continue
        if _TEMPLATE_GIVENS_USED_RE.search(t) or low.startswith("given:"):
            continue
        if _TEMPLATE_APPLY_MAP_RE.search(t) or _TEMPLATE_APPLY_UNIT_RE.search(t):
            apply_hits += 1
            continue
        if _norm_claim(t) in hinge_norms:
            apply_hits += 1
            continue
        if keyed_n and _norm_claim(t) == keyed_n:
            hard_paste += 1
            continue
        # Intermediate inference: has infer markers and is not merely restating the key.
        if _INFER_MARKERS_RE.search(t):
            # Allow a final "therefore <key>" only after other intermediate work.
            body_without_key = _norm_claim(t)
            if keyed_n and keyed_n in body_without_key:
                # Strip the key phrase; if almost nothing remains, it's a paste.
                remainder = body_without_key.replace(keyed_n, "").strip(" .;,-")
                remainder = re.sub(
                    r"\b(therefore|thus|hence|so|it follows that|conclude that)\b",
                    "",
                    remainder,
                ).strip(" .;,-")
                if len(remainder) < 20 and not re.search(r"\d+\s*[+\-×*/÷]\s*\d+", t):
                    # thin therefore-key line — counts as conclusion, not intermediate
                    continue
            intermediate_infer += 1

    if hard_paste or soft_paste:
        return "steps paste the keyed result instead of deriving it"
    if apply_hits and intermediate_infer == 0:
        return "steps only restate map hinge statements; no inference"
    if intermediate_infer == 0:
        return "steps lack at least one inferential sentence"
    return None


def worked_solution_is_complete(ws: dict | None, item_or_row: dict | None = None) -> bool:
    """True only for a derived complete solution (not a template paste)."""
    if not isinstance(ws, dict):
        return False
    if ws.get("status") != "complete":
        return False
    steps = ws.get("steps") or []
    if not steps:
        return False
    if not (ws.get("result") or "").strip():
        return False
    if not (ws.get("key_letter") or "").strip():
        return False
    if not (ws.get("given_facts") or []):
        return False
    if not (ws.get("why_key") or "").strip():
        return False
    if not (ws.get("hinges_used") or []):
        return False
    if not (ws.get("distractors") or []):
        return False

    keyed = ""
    hinge_stmts: list[str] = []
    if isinstance(item_or_row, dict):
        keyed = keyed_option_text(item_or_row) or str(ws.get("result") or "")
        hinge_stmts = _hinge_statements_from_context(item_or_row)
    else:
        keyed = str(ws.get("result") or "")
    if steps_look_like_template(steps, keyed_text=keyed, hinge_statements=hinge_stmts):
        return False
    return True


def admit_refuse_reason(draft_or_row: dict) -> str | None:
    """Refuse reason for write/admit, or None when a derived complete solution matches the key."""
    if not isinstance(draft_or_row, dict):
        return "not a dict"
    ws = get_worked_solution(draft_or_row)
    if ws is None and isinstance(draft_or_row.get("worked_solution"), dict):
        ws = draft_or_row["worked_solution"]
    if not worked_solution_is_complete(ws, draft_or_row):
        if isinstance(ws, dict) and ws.get("status") == "complete":
            reason = steps_look_like_template(
                ws.get("steps") or [],
                keyed_text=keyed_option_text(draft_or_row) or str(ws.get("result") or ""),
                hinge_statements=_hinge_statements_from_context(draft_or_row),
            )
            if reason:
                return f"worked_solution not derived: {reason}"
        return "complete worked_solution required before framing/admit"
    if not solution_result_matches_key(ws, draft_or_row):
        return "worked_solution.result must be the keyed option (asked quantity)"

    stem = ""
    item = draft_or_row.get("item") if isinstance(draft_or_row.get("item"), dict) else None
    if item:
        stem = str(item.get("stem") or "")
    stem = stem or str(draft_or_row.get("stem") or "")

    hit = stem_stacked_tutorial_conclusion(stem)
    if hit:
        return f"STEM_STACKED_TUTORIAL_CONCLUSION: {hit}"
    two = stem_asks_two_quantities(stem)
    if two:
        return f"STEM_DOUBLE_ASK: {two}"
    pad = stem_has_wordcount_padding(stem)
    if pad:
        return f"STEM_WORDCOUNT_PADDING: {pad}"
    leak = stem_leaks_keyed_claim(stem)
    if leak:
        return f"STEM_KEY_LEAK: {leak}"
    return None


def require_worked_solution_for_admit(draft_or_row: dict) -> None:
    """Raise ValueError when framing/admit should refuse."""
    reason = admit_refuse_reason(draft_or_row)
    if reason:
        raise ValueError(reason)
