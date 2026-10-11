#!/usr/bin/env python3
"""MIQG-CAL-KNGOOD v2 — Cambridge/MathNet envelope plus owner-loop detectors.

TikZ is a first-class field, equal to the stem. Master MIQG rc9 is not rewritten.
This assembler is the Modify harness release gate (G17).
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODES_PATH = os.path.join(HERE, "codes.json")
FEEDBACK_PATH = os.path.join(HERE, "human_feedback.jsonl")

PT = re.compile(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)")
SENT_SPLIT = re.compile(r"(?<=[.?!])\s+")
NAME_RE = re.compile(
    r"\b(?:Ravi|Priya|Meera|Arjun|Rohan|Meena|Sara|Ira|Esha|Dev|Ananya|Kabir|"
    r"Aisha|Rahul|Sneha|Vikram|Neha|Aarav|Diya|Ishaan|Ritu|Kavita|Ojas|Sahil|"
    r"Nidhi|Krish|Naina|Qadir|Gita|Zoya|Chirag|Pune|Jaipur|Coimbatore|"
    r"Chennai|Delhi|Mumbai|Kolkata|Bengaluru|Hyderabad|Lucknow|Nagpur)\b"
)
REF_RE = re.compile(
    r"\b(?:the graph|the figure|the diagram|the table|the map|this experiment|"
    r"the chart|the picture)\b",
    re.I,
)
RECIPE_RE = re.compile(
    r"\b(by reversing|without using|confuses|is what produces|because we |"
    r"this is (?:wrong|a mistake)|instead of)\b",
    re.I,
)
CATCH_ALL = (
    "all of the above",
    "none of the above",
    "none of these",
    "both a and b",
    "cannot be determined",
    "not enough information",
)
STOP = {
    "a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "with", "from",
    "that", "this", "it", "as", "by", "at", "if", "than", "then", "so", "we",
}
CATEGORY = {
    "blood", "oxygen", "organ", "tissue", "cell", "gas", "air", "water",
    "energy", "mass", "force", "speed", "heat", "light", "sound", "plant",
    "animal", "metal", "acid", "base", "salt", "number", "fraction", "angle",
}
SHAPE_RE = re.compile(
    r"\b(raised (?:metal )?cap|flat (?:metal )?(?:base|disc)|red paint|painted end)\b",
    re.I,
)
PURPOSE_RE = re.compile(
    r"\b(wants? to|must|in order to|to find out|to check|to test|to know if|"
    r"trying to)\b",
    re.I,
)
FRAME_RE = re.compile(
    r"^Ask whether\b.*\b(already )?(correct|true|settled)\b",
    re.I,
)
QUANT_RE = re.compile(
    r"\b(\d+(?:\.\d+)?\s*(?:V|A|ohm|volt|ampere|mA)|EMF|e\.m\.f\.)\b",
    re.I,
)
NUM_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])")
# META_LANGUAGE: voice about the candidate, the constructed item, authoring
# machinery, or teaching narration (not the science/maths phenomenon). Hardest
# release gate: scanned by meta_language_match over EVERY student-facing string;
# HOLD before envelope; final assert demotes TOP. KNOWN_GOOD_ENVELOPE cannot override.
# Ordinary subject wording stays legal (e.g. cathode/anode products; pictograph "key").
META_LANGUAGE_RE = re.compile(
    r"(?:"
    # Pedagogical actor framing (exam papers do not say "a student wants…")
    r"\ba student (?:must|wants|asks|says|adds|plans)\b|"
    r"\bstudents? (?:must|discuss|want|wants|already know)\b|"
    r"\bstudents already know\b|"
    r"\b(?:the )?(?:class|group|club) must\b|"
    r"\bthe class wants\b|"
    r"\ba class wants\b|"
    r"\ba class is\b|"
    r"\ba student recalls\b|"
    r"\ba student works a clear syllabus\b|"
    r"\brecall a factual\b|"
    r"\brestate a factual\b|"
    r"\blearners? must\b|"
    r"\bpupils? must\b|"
    r"\bthe learner\b|"
    r"\bthe candidate\b|"
    r"\ba learner\b|"
    r"\byou should\b|"
    r"\byou must\b|"
    r"\bmust decide\b|"
    r"\bmust invent\b|"
    # Worksheet / demo props narrating the pedagogical move
    r"\b(?:lab|poster|worksheet|chart|board|note|card) must\b|"
    r"\b(?:skywatch note|timing card|resources board|health worksheet|"
    r"seasons wall chart|clinic poster|class poster|canteen line|"
    r"measuring team) must\b|"
    r"\bmust explain\b|"
    r"\bmust classify\b|"
    r"\bmust predict\b|"
    r"\bpredict the following\b|"
    r"\bidentify which statement\b|"
    r"\bwhich of the following is correct\b|"
    # Bare task wrappers (not ordinary "Which products…?" / "Which compound…?")
    r"\bwhich statements? are correct\b|"
    r"\bwhich statement is correct\b|"
    r"\bwhich claim is correct\b|"
    r"\bwhich decision is correct\b|"
    r"\bwhich ordering and grouping is correct\b|"
    r"\bwhich factual recall is correct\b|"
    r"\bwhich claim do (?:these |the )?records support\b|"
    r"\bwhich claim about\b.{0,80}\bsupport\b|"
    r"\bwhich claim about\b.{0,80}\bis best\b|"
    r"\bwhich claim about\b.{0,80}\bis supported\b|"
    # Broad "claim … is correct" removed: it false-hit option/LBS lines like
    # "claim: the second result is correct". Wrappers use which-claim patterns above.
    r"\bthis question\b|"
    r"\bthis item\b|"
    r"\bthe stem\b|"
    r"\bthe options\b|"
    r"\bthe answer key\b|"
    r"\bthe keyed\b|"
    # Teaching asides that coach before the subject question
    r"\ba common idea\b|"
    r"\ba tempting claim\b|"
    r"\balready know(?:n|s)?\b|"
    r"\balready settled\b|"
    r"\balready treated\b|"
    r"\balready agreed\b|"
    r"\balready listed\b|"
    r"\balready prepared\b|"
    r"\beveryday talk\b|"
    r"\binformal talk\b|"
    r"\bprice talk\b|"
    r"\bgrown-ups?\b|"
    r"\bsaying that\b|"
    r"\bsaying\b|"
    r"\bdo not confuse\b|"
    r"\bdo not merge\b|"
    r"\bdo not keep only\b|"
    r"\bbefore isolating\b|"
    r"\bremove same unknown\b|"
    r"\bis not enough if\b|"
    r"\bchecking (?:\w+[-\s]+){0,4}sample\b|"
    r"\bthe taught\b|"
    r"\btaught (?:procedure|steps|order)\b|"
    r"\bas taught\b|"
    r"\bwork through the parts\b|"
    r"\bmisconception\b|"
    r"\btaxonomy\b|"
    r"\bprerequisite\b|"
    r"\bdistractor\b|"
    r"\bmiqg\b|"
    r"\bjev\b|"
    r"\bnoul\b|"
    r"\bunit[_\s-]?id\b|"
    r"\bhinge\b|"
    # Tutorial imperatives / ontology lectures (confirmed on minted stems)
    r"\bclassify\b.{0,80}\bcorrectly\b|"
    r"\bfor a (?:geometry )?checklist\b|"
    r"\b(?:are |as )?basic objects\b|"
    r"\bbasic objects\b|"
    r"\bclassify a straight path\b|"
    # Method giveaways: ban the coaching pattern, not every Cambridge "use"
    # (real papers: "use the key", "which processes use energy", "careless use of…")
    r"\buse only the final digit\b|"
    r"\busing only (?:its |the )?final digit\b|"
    r"\bgenerate an equivalent fraction\b|"
    r"\bwhile preserving the same quantity\b|"
    r"\bpreserving the same quantity\b|"
    # "How is X found/calculated" when asking for a quantity (not "How is urea removed")
    r"\bhow is\b.{0,100}\b(?:found|calculated)\b|"
    # Conclusion wrappers left after earlier "which statement" rewrites
    r"\bwhich .{0,40}conclusion is correct\b"
    r")",
    re.I,
)
# Padded lecture+question: every remaining TOP stem above this word count with
# 3+ sentences was method coaching before the ask (equation first-move lecture
# at 44w; discount successive cuts 53w; workers/days 52w). Clean exam stems in
# the same banks topped out near 38–39 words. Not a crude cap on ordinary
# two-sentence exam stems.
STEM_PADDED_LECTURE_WORDS = 42
# Field names that may hold student-facing hint / learn-by-solve prose.
_STUDENT_HINT_KEYS = (
    "hint",
    "hints",
    "learn_by_solve",
    "learn_by_solving",
    "learn-by-solve",
    "solution_hint",
    "student_hint",
    "lbs_text",
    "lbs",
)
PHRASE = {
    "KEY_WRONG": "packed key disagrees with independent solving (rectifiable)",
    "KEY_LETTER_ABSENT": "stored key is missing or not among the options (rectifiable)",
    "NO_UNIQUE_ANSWER": "duplicate option text",
    "MISSING_REFERENT": "stem names a figure the record does not contain",
    "PAYLOAD_MISSING": "option table has no table payload",
    "PART_ANSWER_MISSING": "a structured part has no answer line",
    "RECORD_INVALID": "record invalid",
    "WHITELIST_LEAK": "author/mx string leaked into learner text",
    "WHITELIST_PARAPHRASE_LEAK": "stem names the misconception being tested",
    "UNSCORABLE": "constructed part has no usable rubric (authoring)",
    "PADDING": "named-child or place dressing unused by the hinge",
    "DISTRACTOR_RECIPE": "an option describes a mistake instead of stating an answer",
    "FOREIGN_NOUN": "an option introduces a noun the stem never used",
    "CATCH_ALL_OPTION": "the key is a catch-all",
    "FIGURE_ANSWER_LEAK": "the TikZ draws the answer (givens must not be the insight)",
    "FIGURE_STEM_CONFLICT": "the TikZ contradicts the stem (arrow sense or labels)",
    "FIGURE_DISTRACTOR_KILL": "the figure makes a distractor rejectable without the hinge",
    "ANSWER_IN_STEM": "the stem states the discriminant that is the key",
    "STEM_CONTEXT_THIN": "stem has no scene-plus-purpose before the question (Zinsser)",
    "OPTION_FRAME_UNCLEAR": "an option is not a clear, relatable Class 6–8 statement",
    "SURFACE_FEATURE_RECALL": "item tests a surface feature the hinge does not demand",
    "DISTRACTOR_UNJUSTIFIABLE": "a distractor needs values or facts not given at this grade",
    "META_LANGUAGE": "student-facing text uses meta voice or teaching narration instead of a plain exam question",
    "STEM_STACKED_TUTORIAL_CONCLUSION": (
        "stem stacks a scene and a tutorial imperative with a vague "
        "'what conclusion follows' ask while the key states a rule the scene does not give"
    ),
    "STEM_DOUBLE_ASK": "stem asks more than one quantity (two '?' or bundled how/what asks)",
    "STEM_WORDCOUNT_PADDING": "stem adds filler clauses only to raise the word count before the ask",
    "STEM_KEY_LEAK": "stem embeds the keyed claim in the ask",
    "SYLLABUS_BOUND": "map hinge names this topic — on syllabus",
    "SYLLABUS_UNBOUND": "topic is not named on the bound hinge — confirm syllabus before TOP credit",
}


def load_json(path: str, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_codes() -> dict:
    return load_json(CODES_PATH, {})


def opt_text(o) -> str:
    if isinstance(o, dict):
        return (o.get("text") or "").strip()
    return str(o).strip()


def opt_id(o) -> str:
    if isinstance(o, dict):
        return str(o.get("id") or "").strip()
    return ""


def normalize_meta_scan_text(s: str) -> str:
    """Collapse case and whitespace before META_LANGUAGE scanning."""
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def keyed_correct_option_text(result: dict) -> str:
    """Joined text of the keyed/correct option(s) — not merely the letter."""
    options = student_options(result)
    keys = set(key_letters(result.get("answer") or {}))
    return " ".join(o["text"] for o in options if o["id"] in keys)


def _append_text_field(out: list[str], value) -> None:
    if value is None:
        return
    if isinstance(value, str):
        if value.strip():
            out.append(value)
        return
    if isinstance(value, list):
        for v in value:
            _append_text_field(out, v)
        return
    if isinstance(value, dict):
        for k in ("text", "hint", "body", "content", "prompt", "solve"):
            if k in value:
                _append_text_field(out, value.get(k))
        for k in _STUDENT_HINT_KEYS:
            if k in value:
                _append_text_field(out, value.get(k))


def student_facing_source(item_or_result: dict) -> dict:
    """Prefer nested bank `item` when the outer row has no stem of its own."""
    if not isinstance(item_or_result, dict):
        return {}
    nested = item_or_result.get("item")
    if (
        isinstance(nested, dict)
        and not (item_or_result.get("stem") or item_or_result.get("stem_lead"))
        and (nested.get("stem") or nested.get("stem_lead") or nested.get("options"))
    ):
        return nested
    return item_or_result


def student_facing_texts(item_or_result: dict) -> list[str]:
    """Every student-facing string: stem, all options, statements, hints/LBS.

    Shared collector for MIQG and every modify-harness admit/write path.
    Does not scan authoring metadata (design, mx maps, unit ids as fields).
    """
    src = student_facing_source(item_or_result)
    if not src:
        return []
    out: list[str] = []
    _append_text_field(out, src.get("stem"))
    _append_text_field(out, src.get("stem_lead"))
    for o in student_options(src):
        _append_text_field(out, o.get("text"))
    for s in src.get("statements") or []:
        _append_text_field(out, s)
    for part in src.get("parts") or []:
        if isinstance(part, dict):
            _append_text_field(out, part.get("text") or part.get("prompt") or part.get("stem"))
            for k in _STUDENT_HINT_KEYS:
                _append_text_field(out, part.get(k))
            for o in student_options({"options": part.get("options") or []}):
                _append_text_field(out, o.get("text"))
        else:
            _append_text_field(out, part)
    for k in _STUDENT_HINT_KEYS:
        _append_text_field(out, src.get(k))
    assessment = src.get("assessment")
    if isinstance(assessment, dict):
        for k in _STUDENT_HINT_KEYS:
            _append_text_field(out, assessment.get(k))
    # Bank rows nest item.assessment; also scan outer assessment when present.
    if src is not item_or_result and isinstance(item_or_result, dict):
        outer_assessment = item_or_result.get("assessment")
        if isinstance(outer_assessment, dict):
            for k in _STUDENT_HINT_KEYS:
                _append_text_field(out, outer_assessment.get(k))
    teacher = src.get("teacher")
    if isinstance(teacher, dict):
        for k in _STUDENT_HINT_KEYS:
            _append_text_field(out, teacher.get(k))
    elif isinstance(teacher, str):
        _append_text_field(out, teacher)
    return out


class _MetaHit:
    """Lightweight match stand-in so padded-lecture hits share the match API."""

    def __init__(self, quote: str):
        self._quote = quote

    def group(self, _n: int = 0) -> str:
        return self._quote


def stem_is_padded_lecture(stem: str) -> bool:
    """True when the stem is a long teaching lecture plus a trailing question.

    Threshold STEM_PADDED_LECTURE_WORDS (42): grounded in remaining TOP three-hinge
    stems — method-coaching stems ran 44–53 words over 3 sentences (equation
    first-move lecture, discount successive cuts, workers/days trade-off). Clean
    exam stems in the same banks topped out near 38–39 words. Does not reject
    ordinary two-sentence exam stems. Meta phrases still fail at any length via
    META_LANGUAGE_RE.
    """
    s = (stem or "").strip()
    if not s:
        return False
    if word_count(s) <= STEM_PADDED_LECTURE_WORDS:
        return False
    return len(sentences(s)) >= 3


def meta_language_match(*texts: str):
    """Hard-fail detector: meta voice or teaching narration in student-facing text.

    Talk about the candidate, the item, authoring machinery, or a teaching aside —
    not the subject. Scans case- and whitespace-normalized text. When the first
    argument is a stem (callers pass stem first), also fails padded lecture stems.
    Returns a match-like object with .group(0), or None.
    """
    parts = [t for t in texts if t]
    blob = "\n".join(normalize_meta_scan_text(t) for t in parts)
    if blob.strip():
        m = META_LANGUAGE_RE.search(blob)
        if m:
            return m
    # First text is the stem on every harness path (stem, *options / student_facing_texts).
    if parts and stem_is_padded_lecture(parts[0]):
        return _MetaHit("padded teaching narration")
    return None


def meta_language_in_result(item_or_result: dict):
    """Run the shared META_LANGUAGE checker on every student-facing field."""
    texts = student_facing_texts(item_or_result)
    m = meta_language_match(*texts)
    if m:
        return m
    # Belt: even if stem was not first in the collected list, re-check stem alone.
    src = student_facing_source(item_or_result)
    stem = (src.get("stem") or src.get("stem_lead") or "") if src else ""
    if stem and stem_is_padded_lecture(stem):
        return _MetaHit("padded teaching narration")
    return None


def item_refuses_meta_language(item_or_result: dict) -> bool:
    """True when the shared checker matches — callers must not admit/write."""
    return bool(meta_language_in_result(item_or_result))


def word_count(s: str) -> int:
    return len(re.findall(r"\b[\w']+\b", s or ""))


def sentences(s: str) -> list[str]:
    s = (s or "").strip()
    if not s:
        return []
    return [p.strip() for p in SENT_SPLIT.split(s) if p.strip()]


def finding(code: str, severity: str, gate: str, quote: str, loc: str, **extra) -> dict:
    row = {
        "code": code,
        "severity": severity,
        "gate_id": gate,
        "quoted_text": (quote or "")[:180],
        "location": loc,
        "status": "CONFIRMED",
        "merged_into": None,
    }
    row.update(extra)
    return row


def student_options(result: dict) -> list[dict]:
    opts = result.get("options") or []
    out = []
    if isinstance(opts, dict):
        for k, v in opts.items():
            if isinstance(v, dict):
                out.append({"id": str(k), "text": opt_text(v), "tikz": v.get("tikz")})
            else:
                out.append({"id": str(k), "text": str(v or "").strip(), "tikz": None})
        return out
    for o in opts:
        if isinstance(o, dict):
            out.append({"id": opt_id(o), "text": opt_text(o), "tikz": o.get("tikz")})
        else:
            out.append({"id": "", "text": str(o), "tikz": None})
    return out


def key_letters(answer: dict) -> list[str]:
    if not answer:
        return []
    kind = answer.get("kind")
    if kind == "single_letter" and answer.get("letter"):
        return [str(answer["letter"])]
    if kind == "letter_set":
        return [str(x) for x in (answer.get("letters") or [])]
    if kind == "part_answers":
        out = []
        for pa in answer.get("part_answers") or []:
            if not isinstance(pa, dict):
                continue
            a = pa.get("answer")
            if isinstance(a, str) and re.fullmatch(r"[A-F]", a):
                out.append(a)
        return out
    if isinstance(answer.get("letter"), str):
        return [answer["letter"]]
    mcq = answer.get("mcq_key")
    if isinstance(mcq, str) and mcq:
        return list(mcq)
    return []


def tikz_of(result: dict) -> str:
    t = result.get("tikz")
    if isinstance(t, list):
        return "\n".join(str(x) for x in t)
    return str(t or "")


def node_labels(tikz: str) -> list[str]:
    return re.findall(
        r"\\node(?:\[[^\]]*\])?\s*(?:at\s*\([^)]+\)\s*)?\{([^}]*)\}",
        tikz or "",
    )


def parse_pt(s: str):
    m = PT.search(s or "")
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def arrows(tikz: str) -> list[tuple]:
    out = []
    for m in re.finditer(
        r"\\draw\[([^\]]*)\]\s*\(([^)]+)\)\s*--\s*\(([^)]+)\)",
        tikz or "",
    ):
        opts, a, b = m.group(1), m.group(2), m.group(3)
        if "->" in opts or "-latex" in opts:
            pa, pb = parse_pt(a), parse_pt(b)
            if pa and pb:
                out.append((pa, pb, opts))
    return out


def rects(tikz: str) -> list[tuple]:
    out = []
    for m in re.finditer(
        r"\\draw(?:\[[^\]]*\])?\s*\(([^)]+)\)\s*rectangle\s*\(([^)]+)\)",
        tikz or "",
    ):
        pa, pb = parse_pt(m.group(1)), parse_pt(m.group(2))
        if not pa or not pb:
            continue
        xmin, xmax = min(pa[0], pb[0]), max(pa[0], pb[0])
        ymin, ymax = min(pa[1], pb[1]), max(pa[1], pb[1])
        out.append((xmin, xmax, ymin, ymax))
    return out


def arrow_into_rect(arr, rect, tol=0.25) -> bool:
    (x0, y0), (x1, y1), _ = arr
    xmin, xmax, ymin, ymax = rect

    def inside(x, y):
        return xmin - tol <= x <= xmax + tol and ymin - tol <= y <= ymax + tol

    return (not inside(x0, y0)) and inside(x1, y1)


def hinge_blob(packet: dict | None, meta: dict | None) -> str:
    bits = []
    if packet:
        h = ((packet.get("intelligence") or {}).get("hinge")) or {}
        bits.extend([h.get("title") or "", h.get("decision_hinge") or "", h.get("primary") or ""])
        tags = ((packet.get("intelligence") or {}).get("packed_tags")) or {}
        bits.append(str(tags.get("topic") or ""))
    if meta:
        bits.extend([
            meta.get("hinge") or "",
            meta.get("decision_hinge") or "",
            meta.get("chapter") or "",
            meta.get("unit_id") or "",
        ])
    return " ".join(str(b) for b in bits if b)


def is_catch_all(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(c in t for c in CATCH_ALL)


def parse_num(text: str):
    t = (text or "").strip().replace(",", "")
    t = re.sub(r"[^\d.\-eE/ ]", "", t).strip()
    if not t:
        return None
    if re.fullmatch(r"-?\d+/\d+", t):
        a, b = t.split("/")
        b = float(b)
        return None if b == 0 else float(a) / b
    try:
        return float(t)
    except ValueError:
        return None


def hinge_kind(stem: str, options: list) -> str:
    nums = NUM_RE.findall(stem or "")
    numeric_opts = sum(1 for o in options if parse_num(o["text"]) is not None)
    if len(nums) >= 2 and numeric_opts >= 2:
        return "DECISION"
    if re.search(r"\b(find|calculate|compute|evaluate|simplify|work out)\b", stem or "", re.I) and nums:
        return "DECISION"
    return "RECALL"


def bank_to_result(item: dict) -> dict:
    opts = item.get("options") or {}
    answer = {}
    a = item.get("assessment") or {}
    key = a.get("mcq_key") or item.get("mcq_key")
    if isinstance(key, str) and len(key) == 1:
        answer = {"kind": "single_letter", "letter": key}
    elif isinstance(key, str) and len(key) > 1:
        answer = {"kind": "letter_set", "letters": list(key)}
    return {
        "schema": "modify_result.v1",
        "status": "OK",
        "item_type": item.get("item_type") or "single_mcq",
        "stem": item.get("stem") or item.get("stem_lead") or "",
        "options": opts,
        "statements": item.get("statements") or [],
        "parts": item.get("parts") or [],
        "tikz": item.get("tikz"),
        "tables": item.get("tables") or [],
        "answer": answer,
        "mx_option_map": item.get("mx_option_map") or {},
    }


def scan(result: dict, packet: dict | None = None, meta: dict | None = None, codes: dict | None = None) -> list[dict]:
    codes = codes or load_codes()
    findings: list[dict] = []
    stem = result.get("stem") or ""
    options = student_options(result)
    parts = result.get("parts") or []
    tikz = tikz_of(result)
    tables = result.get("tables") or []
    item_type = result.get("item_type") or "single_mcq"
    answer = result.get("answer") or {}
    keys = key_letters(answer)
    letters = [o["id"] for o in options if o["id"]]
    has_visual = bool(tikz.strip()) or item_type == "options_are_figure"
    hinge = hinge_blob(packet, meta)
    mx_map = result.get("mx_option_map") or {}
    pairs = codes.get("answer_in_stem_pairs") or []

    if item_type in ("single_mcq", "option_table", "options_are_figure", "three_statement", "mcq", "mcq_diagram", "mcq_table"):
        if item_type == "three_statement" and answer.get("kind") == "statement_pattern":
            pass
        elif letters and (not keys or not all(k in letters for k in keys)):
            findings.append(finding("KEY_LETTER_ABSENT", "DQ", "V1", ",".join(keys) or "<absent>", "answer"))
    if item_type in ("structured_parts", "structured"):
        pa = {}
        for p in (answer.get("part_answers") or []):
            if not isinstance(p, dict):
                continue
            pid = p.get("part_id")
            if pid:
                pa[pid] = p
        for part in parts:
            if not isinstance(part, dict):
                continue
            pid = part.get("id")
            if pid not in pa or not str((pa.get(pid) or {}).get("answer") or "").strip():
                findings.append(finding("PART_ANSWER_MISSING", "DQ", "V1", "<absent>", f"part {pid}"))
        for part in parts:
            if not isinstance(part, dict):
                continue
            if part.get("options"):
                continue
            rub = (part.get("rubric") or "").strip()
            if not rub or rub.lower() in ("good explanation", "full marks for a good explanation"):
                findings.append(finding("UNSCORABLE", "DQ", "V7", rub or "<absent>", f"part {part.get('id')}"))

    # Level 1: dedicated META_LANGUAGE scan on EVERY student-facing string.
    facing = student_facing_texts(result)
    meta_m = meta_language_match(*facing)
    if meta_m:
        loc = "student_facing"
        if meta_language_match(stem or ""):
            loc = "stem"
        else:
            for o in options:
                if meta_language_match(o.get("text") or ""):
                    loc = f"option {o.get('id') or '?'}"
                    break
            else:
                for i, s in enumerate(result.get("statements") or []):
                    st = s.get("text") if isinstance(s, dict) else s
                    if meta_language_match(str(st or "")):
                        loc = f"statement {i}"
                        break
                else:
                    for k in _STUDENT_HINT_KEYS:
                        if meta_language_match(str(result.get(k) or "")):
                            loc = k
                            break
        findings.append(finding("META_LANGUAGE", "MAJOR", "M0", meta_m.group(0), loc))

    # Stacked scene + tutorial imperative + vague conclusion (does not ban bare conclusion asks).
    try:
        from systems.modify.miqg.worked_solution import (
            facing_stacked_tutorial_conclusion,
            stem_stacked_tutorial_conclusion,
        )
    except ImportError:
        from worked_solution import (  # type: ignore
            facing_stacked_tutorial_conclusion,
            stem_stacked_tutorial_conclusion,
        )
    stacked_hit = facing_stacked_tutorial_conclusion(*(facing or [stem]))
    if stacked_hit:
        loc = "stem" if stem_stacked_tutorial_conclusion(stem) else "student_facing"
        findings.append(
            finding(
                "STEM_STACKED_TUTORIAL_CONCLUSION",
                "MAJOR",
                "M0",
                stacked_hit,
                loc,
            )
        )

    try:
        from systems.modify.miqg.worked_solution import (
            stem_asks_two_quantities,
            stem_has_wordcount_padding,
            stem_leaks_keyed_claim,
        )
    except ImportError:
        from worked_solution import (  # type: ignore
            stem_asks_two_quantities,
            stem_has_wordcount_padding,
            stem_leaks_keyed_claim,
        )
    two = stem_asks_two_quantities(stem)
    if two:
        findings.append(finding("STEM_DOUBLE_ASK", "MAJOR", "M0", two, "stem"))
    pad = stem_has_wordcount_padding(stem)
    if pad:
        findings.append(finding("STEM_WORDCOUNT_PADDING", "MAJOR", "M0", pad, "stem"))
    leak = stem_leaks_keyed_claim(stem)
    if leak:
        findings.append(finding("STEM_KEY_LEAK", "MAJOR", "M0", leak, "stem"))

    leak_needles = ["CANDIDATE", "mx_option_map", "condition_omission", "relationship_reversal", "scope_error"]
    blob = stem.lower()
    for n in leak_needles:
        if n.lower() in blob:
            findings.append(finding("WHITELIST_LEAK", "DQ", "V2", n, "stem"))
            break

    if REF_RE.search(stem) and not tikz.strip() and not tables and item_type not in ("option_table", "mcq_table"):
        m = REF_RE.search(stem)
        findings.append(finding("MISSING_REFERENT", "DQ", "V6", m.group(0), "stem"))

    texts = [re.sub(r"\s+", " ", o["text"].lower()) for o in options]
    if options and len(texts) != len(set(texts)):
        findings.append(finding("NO_UNIQUE_ANSWER", "DQ", "V3", options[0]["text"][:80], f"option {options[0]['id']}"))

    for o in options:
        if is_catch_all(o["text"]):
            findings.append(finding("CATCH_ALL_OPTION", "MAJOR", "K2", o["text"][:80], f"option {o['id']}"))
        if RECIPE_RE.search(o["text"]):
            findings.append(finding("DISTRACTOR_RECIPE", "MAJOR", "K1", o["text"][:80], f"option {o['id']}"))

    sents = sentences(stem)
    names = NAME_RE.findall(stem)
    hk = hinge_kind(stem, options)
    if names and sents and hk == "RECALL":
        last = sents[-1]
        if not any(n in last for n in names):
            findings.append(finding("PADDING", "MAJOR", "K3", names[0], "stem"))
    if hk != "RECALL":
        for o in options:
            for m in re.finditer(r"\bthe ([a-z]{3,12})\b", o["text"].lower()):
                noun = m.group(1)
                if noun in CATEGORY or noun in STOP:
                    continue
                if noun not in stem.lower() and noun not in tikz.lower():
                    findings.append(finding("FOREIGN_NOUN", "MAJOR", "K3", m.group(0), f"option {o['id']}"))
                    break

    if tikz.strip():
        labs = node_labels(tikz)
        n_n = sum(1 for t in labs if t.strip() in ("N", "North", "north"))
        n_s = sum(1 for t in labs if t.strip() in ("S", "South", "south"))
        if re.search(r"\b(cut|pieces?|broken|breaks)\b", stem, re.I) and n_n >= 2 and n_s >= 2:
            findings.append(finding(
                "FIGURE_ANSWER_LEAK", "DQ", "V8",
                f"TikZ labels {n_n} N and {n_s} S on the fragments",
                "tikz",
            ))
        if re.search(r"\bcompass\b", stem, re.I) and re.search(r"geographic north", tikz, re.I):
            if re.search(r"red", tikz, re.I) and re.search(r"\b(north|direction|needle)\b", stem, re.I):
                findings.append(finding(
                    "FIGURE_ANSWER_LEAK", "DQ", "V8",
                    "compass needle already settled on labelled geographic north",
                    "tikz",
                ))
        if re.search(r"\bpull", stem, re.I) and re.search(r"pull", tikz, re.I):
            for arr in arrows(tikz):
                if any(arrow_into_rect(arr, rc) for rc in rects(tikz)):
                    findings.append(finding(
                        "FIGURE_STEM_CONFLICT", "DQ", "V8",
                        "pull drawn as an arrow into the object; pull arrows start at the object and point outward",
                        "tikz",
                    ))
                    break
        distractors = [o for o in options if o["id"] not in set(keys)]
        if re.search(r"geographic north", tikz, re.I) or re.search(r"\\node[^{]*\{[NESW]\}", tikz):
            for o in distractors:
                if re.search(r"east.?west|marks east|red paint", o["text"], re.I):
                    findings.append(finding(
                        "FIGURE_DISTRACTOR_KILL", "MAJOR", "V8",
                        o["text"][:80],
                        f"option {o['id']}",
                    ))
                    if (mx_map.get(o["id"]) or "") == "surface_feature_capture":
                        findings.append(finding(
                            "MX_INTENDED_SURFACE", "FLAG", "K7",
                            "mapped to surface_feature_capture; figure still kills it",
                            f"option {o['id']}",
                        ))

    for pair in pairs:
        if re.search(pair["stem"], stem, re.I):
            hits = [o for o in options if re.search(pair["key"], o["text"], re.I)]
            if len(hits) == 1 and hits[0]["id"] in set(keys):
                findings.append(finding(
                    "ANSWER_IN_STEM", "DQ", "C3",
                    hits[0]["text"][:80],
                    "stem",
                    mechanism=pair.get("id"),
                ))

    mathish = bool(re.search(r"\b(find|calculate|evaluate|simplify|solve|compute)\b", stem, re.I))
    if not (has_visual and REF_RE.search(stem)) and not mathish and not NUM_RE.search(stem):
        body = re.sub(r"(Which|What|How)\b.*$", "", stem, flags=re.S | re.I).strip()
        wc = word_count(body)
        if wc < 18 and not PURPOSE_RE.search(body):
            findings.append(finding("STEM_CONTEXT_THIN", "MAJOR", "K4", body[:120], "stem"))
        elif wc < 24 and re.search(r"\bguess\b", body, re.I) and not PURPOSE_RE.search(body):
            findings.append(finding("STEM_CONTEXT_THIN", "MAJOR", "K4", body[:120], "stem"))

    for o in options:
        if FRAME_RE.search(o["text"].strip()):
            findings.append(finding("OPTION_FRAME_UNCLEAR", "MAJOR", "K4", o["text"][:80], f"option {o['id']}"))

    if SHAPE_RE.search(stem):
        if not re.search(r"\b(positive terminal|negative terminal|north-south|poles?)\b", hinge, re.I):
            findings.append(finding("SURFACE_FEATURE_RECALL", "MAJOR", "C1", SHAPE_RE.search(stem).group(0), "stem"))
        elif re.search(r"\b(positive terminal|negative terminal)\b", hinge, re.I):
            findings.append(finding("SYLLABUS_BOUND", "FLAG", "C1", "hinge names cell terminals", "whole_item"))

    stem_has_q = bool(QUANT_RE.search(stem))
    for o in options:
        if o["id"] in set(keys):
            continue
        if QUANT_RE.search(o["text"]) and not stem_has_q:
            findings.append(finding("DISTRACTOR_UNJUSTIFIABLE", "MAJOR", "C4", o["text"][:80], f"option {o['id']}"))

    led_item = bool(re.search(r"\bLED\b", stem + " " + " ".join(o["text"] for o in options)))
    if led_item:
        if re.search(r"\bLED\b", hinge, re.I):
            findings.append(finding("SYLLABUS_BOUND", "FLAG", "C1", "hinge names LED", "whole_item"))
        else:
            findings.append(finding("SYLLABUS_UNBOUND", "FLAG", "C1", "LED not named on the bound hinge", "whole_item"))

    return findings


def assemble(
    findings: list[dict],
    corpus: str,
    codes: dict | None = None,
    row: dict | None = None,
    stem: str = "",
    keyed_option_text: str = "",
    student_facing: str | list[str] | None = None,
) -> dict:
    codes = codes or load_codes()
    counting_dq = set(codes.get("counting_dq") or [])
    cand_dq = set(codes.get("candidate_only_dq") or [])
    counting_maj = set(codes.get("counting_major") or [])
    cand_maj = set(codes.get("candidate_only_major") or [])
    flags_set = set(codes.get("flags") or [])
    rectifiable = set(codes.get("rectifiable") or [])
    if corpus == "CANDIDATE":
        counting_dq |= cand_dq
        counting_maj |= cand_maj

    kept_dq, kept_maj, flags, suppressed = [], [], [], []
    seen = set()
    for f in findings:
        if f.get("status") not in (None, "CONFIRMED"):
            continue
        code = f.get("code") or ""
        if not code or code in seen:
            continue
        seen.add(code)
        sev = f.get("severity")
        if code in flags_set or sev == "FLAG":
            flags.append(code)
        elif code in counting_dq:
            kept_dq.append(code)
        elif code in counting_maj:
            kept_maj.append(code)
        else:
            suppressed.append(code)

    # Level 2: shared matcher FIRST — META_LANGUAGE before any envelope rule.
    if isinstance(student_facing, list):
        facing_parts = [str(x) for x in student_facing if x]
    elif student_facing:
        facing_parts = [str(student_facing)]
    else:
        facing_parts = [stem or "", keyed_option_text or ""]
    ml_hit = meta_language_match(*facing_parts)
    has_meta_finding = any(
        (f.get("code") == "META_LANGUAGE" and f.get("status") in (None, "CONFIRMED"))
        for f in findings
    )
    has_meta = bool(ml_hit) or has_meta_finding

    try:
        from systems.modify.miqg.worked_solution import facing_stacked_tutorial_conclusion
    except ImportError:
        from worked_solution import facing_stacked_tutorial_conclusion  # type: ignore
    stacked_hit = facing_stacked_tutorial_conclusion(*facing_parts)
    has_stacked_finding = any(
        (
            f.get("code") == "STEM_STACKED_TUTORIAL_CONCLUSION"
            and f.get("status") in (None, "CONFIRMED")
        )
        for f in findings
    )
    has_stacked = bool(stacked_hit) or has_stacked_finding

    k_major = len(kept_maj)
    if has_meta:
        # Hardest gate: never TOP / PASS / KNOWN_GOOD_ENVELOPE when meta voice is present.
        status, tier, decisive = "ASSESSED", "MEDIUM", "META_LANGUAGE"
        if "META_LANGUAGE" not in kept_maj:
            kept_maj = ["META_LANGUAGE"] + [c for c in kept_maj if c != "META_LANGUAGE"]
            k_major = len(kept_maj)
        if "META_LANGUAGE" in suppressed:
            suppressed = [c for c in suppressed if c != "META_LANGUAGE"]
    elif has_stacked:
        # Scene + tutorial imperative + vague conclusion: never TOP while stacked.
        status, tier, decisive = "ASSESSED", "MEDIUM", "STEM_STACKED_TUTORIAL_CONCLUSION"
        if "STEM_STACKED_TUTORIAL_CONCLUSION" not in kept_maj:
            kept_maj = ["STEM_STACKED_TUTORIAL_CONCLUSION"] + [
                c for c in kept_maj if c != "STEM_STACKED_TUTORIAL_CONCLUSION"
            ]
            k_major = len(kept_maj)
        if "STEM_STACKED_TUTORIAL_CONCLUSION" in suppressed:
            suppressed = [c for c in suppressed if c != "STEM_STACKED_TUTORIAL_CONCLUSION"]
    elif kept_dq:
        status, tier, decisive = "ASSESSED", "LOW", "EXTRACTION_OR_AUTHORING_DQ"
    elif k_major >= 3:
        status, tier, decisive = "ASSESSED", "LOW", "POORLY_DESIGNED_3_MAJOR"
    elif k_major >= 1:
        status, tier, decisive = "ASSESSED", "MEDIUM", "MAJOR_PRESENT"
    else:
        status, tier, decisive = "ASSESSED", "TOP", "KNOWN_GOOD_ENVELOPE"

    repairable = [c for c in kept_dq + kept_maj if c in rectifiable]
    non_repair = [c for c in kept_dq if c not in rectifiable]
    if tier == "TOP":
        release = "PASS"
    elif tier == "MEDIUM":
        release = "HOLD"
    elif kept_dq and not non_repair:
        release = "REPAIR"
    elif kept_dq:
        release = "BLOCK"
    else:
        release = "REPAIR" if repairable else "BLOCK"

    # Level 3: final assertion — later rules (incl. KNOWN_GOOD_ENVELOPE) cannot restore TOP.
    if meta_language_match(*facing_parts):
        if tier == "TOP" or release == "PASS" or decisive == "KNOWN_GOOD_ENVELOPE":
            status, tier, decisive = "ASSESSED", "MEDIUM", "META_LANGUAGE"
            release = "HOLD"
        if "META_LANGUAGE" not in kept_maj:
            kept_maj = ["META_LANGUAGE"] + kept_maj
            k_major = len(kept_maj)
        if "META_LANGUAGE" in suppressed:
            suppressed = [c for c in suppressed if c != "META_LANGUAGE"]
    if facing_stacked_tutorial_conclusion(*facing_parts):
        if tier == "TOP" or release == "PASS" or decisive == "KNOWN_GOOD_ENVELOPE":
            status, tier, decisive = "ASSESSED", "MEDIUM", "STEM_STACKED_TUTORIAL_CONCLUSION"
            release = "HOLD"
        if "STEM_STACKED_TUTORIAL_CONCLUSION" not in kept_maj:
            kept_maj = ["STEM_STACKED_TUTORIAL_CONCLUSION"] + kept_maj
            k_major = len(kept_maj)
        if "STEM_STACKED_TUTORIAL_CONCLUSION" in suppressed:
            suppressed = [c for c in suppressed if c != "STEM_STACKED_TUTORIAL_CONCLUSION"]

    bits = []
    if decisive == "META_LANGUAGE":
        bits.append(
            "Rated MEDIUM: META_LANGUAGE — student-facing text uses meta voice "
            "or teaching narration instead of a plain exam question ("
            + ", ".join(kept_maj)
            + ")."
        )
    elif decisive == "STEM_STACKED_TUTORIAL_CONCLUSION":
        bits.append(
            "Rated MEDIUM: STEM_STACKED_TUTORIAL_CONCLUSION — stem stacks a "
            "tutorial imperative with a vague conclusion ask ("
            + ", ".join(kept_maj)
            + ")."
        )
    elif tier == "TOP":
        bits.append("Rated TOP (CAL-KNGOOD v2): within the Cambridge/MathNet envelope; TikZ and stem do not leak the answer.")
    elif tier == "MEDIUM":
        bits.append("Rated MEDIUM: craft outside the known-good envelope (" + ", ".join(kept_maj) + ").")
    else:
        bits.append("Rated LOW: " + "; ".join(PHRASE.get(c, c) for c in kept_dq or kept_maj) + ".")
    if flags:
        bits.append("Syllabus/flags: " + ", ".join(flags) + ".")
    if suppressed:
        bits.append("Master codes not counting under calibration: " + ",".join(suppressed) + ".")
    if release == "REPAIR":
        bits.append("Rectifiable: " + ", ".join(repairable) + ".")
    rationale = " ".join(bits)

    out = dict(row or {})
    out.update({
        "protocol": codes.get("protocol") or "MIQG-v1.0-rc9-CAL-KNGOOD-v2",
        "master_protocol": codes.get("master_protocol") or "MIQG-v1.0-rc9",
        "corpus": corpus,
        "evaluation_status": status,
        "quality_tier": tier,
        "decisive_reason": decisive,
        "rationale": rationale,
        "k_major": k_major,
        "dq_codes": ",".join(kept_dq),
        "major_codes": ",".join(kept_maj),
        "flags": ",".join(flags),
        "suppressed": ",".join(suppressed),
        "rectifiable_codes": ",".join(repairable),
        "release_gate": release,
        "findings": findings,
    })
    return out


def reasons_of(row: dict) -> list[str]:
    out = []
    if row.get("rationale"):
        out.append(row["rationale"])
    dq = [c for c in (row.get("dq_codes") or "").split(",") if c]
    maj = [c for c in (row.get("major_codes") or "").split(",") if c]
    if dq:
        out.append("Fatal codes that count: " + ", ".join(dq) + ".")
        for c in dq:
            if c in PHRASE:
                out.append(PHRASE[c] + ".")
    if maj:
        out.append("Craft outside the Cambridge/MathNet envelope: " + ", ".join(maj) + ".")
        for c in maj:
            if c in PHRASE:
                out.append(PHRASE[c] + ".")
    fl = [c for c in (row.get("flags") or "").split(",") if c]
    if fl:
        out.append("Flags: " + ", ".join(fl) + ".")
    if row.get("release_gate"):
        out.append("Modify release gate: " + row["release_gate"] + ".")
    hf = row.get("human_feedback") or []
    if hf:
        note = hf[-1].get("human_note") or ""
        if note:
            out.append("Owner review: " + note)
    out.append("Bar: published Cambridge and MathNet items are TOP unless the pack is broken or the figure/stem leaks the answer.")
    return out


def evaluate_result(
    result: dict,
    packet: dict | None = None,
    meta: dict | None = None,
    corpus: str = "CANDIDATE",
    extra_findings: list | None = None,
) -> dict:
    codes = load_codes()
    findings = scan(result, packet=packet, meta=meta, codes=codes)
    if extra_findings:
        findings.extend(extra_findings)
    stem = result.get("stem") or ""
    keyed = keyed_correct_option_text(result)
    facing = student_facing_texts(result)
    row = {
        "item_type": result.get("item_type"),
        "stem_excerpt": stem[:180].replace("\n", " "),
        "stored_key": ",".join(key_letters(result.get("answer") or {})),
        "has_visual": bool(tikz_of(result).strip()),
    }
    if meta:
        for k in ("id", "subject", "grade", "chapter", "hinge_id", "attempt", "filename", "uid"):
            if meta.get(k) is not None:
                row[k] = meta.get(k)
    out = assemble(
        findings,
        corpus,
        codes,
        row,
        stem=stem,
        keyed_option_text=keyed,
        student_facing=facing,
    )
    # Belt-and-suspenders: even if a caller mutates findings or an envelope path
    # races ahead, meta voice in ANY student-facing part cannot leave as TOP / PASS.
    if meta_language_match(*facing):
        if out.get("quality_tier") == "TOP" or out.get("release_gate") == "PASS":
            out["quality_tier"] = "MEDIUM"
            out["release_gate"] = "HOLD"
            out["decisive_reason"] = "META_LANGUAGE"
            maj = [c for c in (out.get("major_codes") or "").split(",") if c]
            if "META_LANGUAGE" not in maj:
                maj = ["META_LANGUAGE"] + maj
            out["major_codes"] = ",".join(maj)
            out["k_major"] = len(maj)
            out["rationale"] = (
                "Rated MEDIUM: META_LANGUAGE — student-facing text uses meta voice "
                "or teaching narration instead of a plain exam question ("
                + out["major_codes"]
                + ")."
            )
    try:
        from systems.modify.miqg.worked_solution import facing_stacked_tutorial_conclusion
    except ImportError:
        from worked_solution import facing_stacked_tutorial_conclusion  # type: ignore
    if facing_stacked_tutorial_conclusion(*facing):
        if out.get("quality_tier") == "TOP" or out.get("release_gate") == "PASS":
            out["quality_tier"] = "MEDIUM"
            out["release_gate"] = "HOLD"
            out["decisive_reason"] = "STEM_STACKED_TUTORIAL_CONCLUSION"
            maj = [c for c in (out.get("major_codes") or "").split(",") if c]
            if "STEM_STACKED_TUTORIAL_CONCLUSION" not in maj:
                maj = ["STEM_STACKED_TUTORIAL_CONCLUSION"] + maj
            out["major_codes"] = ",".join(maj)
            out["k_major"] = len(maj)
            out["rationale"] = (
                "Rated MEDIUM: STEM_STACKED_TUTORIAL_CONCLUSION — stem stacks a "
                "tutorial imperative with a vague conclusion ask ("
                + out["major_codes"]
                + ")."
            )
    return out


def load_feedback() -> dict:
    by = {}
    if not os.path.exists(FEEDBACK_PATH):
        return by
    with open(FEEDBACK_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            by.setdefault(rec.get("id"), []).append(rec)
    return by


def evaluate_stdin() -> dict:
    raw = sys.stdin.read()
    doc = json.loads(raw)
    result = doc.get("result") or doc
    packet = doc.get("packet")
    meta = doc.get("meta")
    corpus = doc.get("corpus") or "CANDIDATE"
    return evaluate_result(result, packet=packet, meta=meta, corpus=corpus)


if __name__ == "__main__":
    if "--stdin" in sys.argv:
        json.dump(evaluate_stdin(), sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print("usage: miqg_cal.py --stdin < {result, packet, corpus}", file=sys.stderr)
        sys.exit(2)
