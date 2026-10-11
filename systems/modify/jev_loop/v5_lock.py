"""Deterministic V5 figure lock: G3b stem-object bind, label-to-stroke, declared delta.

Author comments and tikz_delta prose are not evidence. Geometry is.
G3 (presence of a figure-word vs TikZ) stays in gates.py. This module is G3b/G3c/G3d.
"""
from __future__ import annotations

import math
import re
from typing import Any

PT = re.compile(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)")
NODE_RE = re.compile(
    r"\\node(?:\[(?P<opts>[^\]]*)\])?\s*"
    r"(?:\([^)]+\)\s*)?"
    r"(?:at\s*\((?P<x>[^,\)]+)\s*,\s*(?P<y>[^\)]+)\))?\s*"
    r"\{(?P<txt>[^}]*)\}",
    re.I,
)
CIRCLE_NODE_RE = re.compile(
    r"circle\s*\([^)]*\)\s*node(?:\[[^\]]*\])?\s*\{([^}]*)\}",
    re.I,
)
BEZIER_RE = re.compile(
    r"\\draw\s*(?:\[(?P<opts>[^\]]*)\])?\s*"
    r"\((?P<x0>[^,]+),(?P<y0>[^)]+)\)\s*"
    r"\.\.\s*controls\s*\((?P<x1>[^,]+),(?P<y1>[^)]+)\)\s*"
    r"and\s*\((?P<x2>[^,]+),(?P<y2>[^)]+)\)\s*"
    r"\.\.\s*\((?P<x3>[^,]+),(?P<y3>[^)]+)\)",
    re.I,
)
LINE_RE = re.compile(
    r"\\draw\s*(?:\[(?P<opts>[^\]]*)\])?\s*"
    r"\((?P<x0>[^,]+),(?P<y0>[^)]+)\)\s*--\s*\((?P<x1>[^,]+),(?P<y1>[^)]+)\)",
    re.I,
)
DEVICE_RE = re.compile(
    r"\b(voltmeter|ammeter|meter|wave|curve|line|marble|magnet|rod|end|graph|flask)\s+"
    r"([A-Z](?:\d+)?|\d+)\b",
    re.I,
)
LABELLED_RE = re.compile(
    r"\b(?:re-)?(?:labell?ed|marked|named|called)\s+(?:as\s+)?([A-Za-z][A-Za-z0-9]*)\b",
    re.I,
)
RUNS_RE = re.compile(r"\bruns?\s+([A-Z])(?:\s+and\s+([A-Z]))?\b")
PATHWAY_RE = re.compile(
    r"\b(?:the\s+)?([A-Za-z][A-Za-z0-9-]{2,})\s+pathway\b",
    re.I,
)
REMOVAL_RE = re.compile(
    r"(taken out|removed|deleted|no longer (?:shown|present|drawn)|has been taken)",
    re.I,
)
STYLE_LETTER_RE = re.compile(
    r"\b(solid|dashed|dotted|continuous)\s+(?:curve|line|path|series)?\s*([A-Z])\b",
    re.I,
)
LETTER_STYLE_RE = re.compile(
    r"\b([A-Z])\s+(?:is|now|as)?\s*(?:the\s+)?(solid|dashed|dotted|continuous)\b",
    re.I,
)
FASTER_RE = re.compile(
    r"\b(falls faster|faster at first|steeper|greater initial (?:rate|slope)|steep start)\b",
    re.I,
)
LOWER_RE = re.compile(
    r"\b(finishes at a lower|lower (?:final )?mass|lower finish|ends? (?:at a )?lower|finishes lower)\b",
    re.I,
)
STOP = {
    "the", "a", "an", "as", "this", "that", "these", "those", "diagram", "figure", "graph",
    "chart", "table", "map", "picture", "circuit", "apparatus", "experiment", "class",
    "student", "item", "question", "option", "stem", "tikz", "time", "mass", "force",
    "reaction", "flask", "against", "shown", "above", "below", "original", "cycle",
    "arrow", "sign", "change", "from", "after", "before", "with", "onto",
}

POLE_LABELS = {"N", "S", "E", "W", "North", "South"}


def _f(s: str) -> float | None:
    try:
        return float(str(s).strip())
    except (TypeError, ValueError):
        return None


def tikz_of(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, dict):
        t = obj.get("tikz")
        if isinstance(t, list):
            return "\n".join(str(x) for x in t)
        return str(t or "")
    if isinstance(obj, list):
        return "\n".join(str(x) for x in obj)
    return str(obj)


def norm_label(s: str) -> str:
    t = re.sub(r"\\[A-Za-z]+", " ", s or "")
    t = re.sub(r"[{}$]", " ", t)
    t = t.replace("\\\\", " ")
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def node_texts(tikz: str) -> list[str]:
    out = []
    for m in NODE_RE.finditer(tikz or ""):
        raw = (m.group("txt") or "").strip()
        if raw:
            out.append(raw)
    for m in CIRCLE_NODE_RE.finditer(tikz or ""):
        raw = (m.group(1) or "").strip()
        if raw:
            out.append(raw)
    return out


def letter_nodes(tikz: str) -> list[dict]:
    rows = []
    for m in NODE_RE.finditer(tikz or ""):
        txt = re.sub(r"\s+", " ", (m.group("txt") or "").strip())
        if not txt:
            continue
        x, y = _f(m.group("x")), _f(m.group("y"))
        if x is None or y is None:
            continue
        letter = txt if re.fullmatch(r"[A-Z](?:\d+)?", txt) else None
        if letter and letter in POLE_LABELS:
            letter = None
        rows.append({"text": txt, "letter": letter, "x": x, "y": y})
    return rows


def _style(opts: str) -> str:
    o = (opts or "").lower()
    if "dashed" in o:
        return "dashed"
    if "dotted" in o:
        return "dotted"
    return "solid"


def _cubic(p0, p1, p2, p3, t: float):
    u = 1.0 - t
    x = (u ** 3) * p0[0] + 3 * (u ** 2) * t * p1[0] + 3 * u * (t ** 2) * p2[0] + (t ** 3) * p3[0]
    y = (u ** 3) * p0[1] + 3 * (u ** 2) * t * p1[1] + 3 * u * (t ** 2) * p2[1] + (t ** 3) * p3[1]
    return x, y


def strokes(tikz: str) -> list[dict]:
    rows = []
    for i, m in enumerate(BEZIER_RE.finditer(tikz or "")):
        pts = []
        for k in ("x0", "y0", "x1", "y1", "x2", "y2", "x3", "y3"):
            v = _f(m.group(k))
            if v is None:
                pts = []
                break
            pts.append(v)
        if len(pts) != 8:
            continue
        p0, p1, p2, p3 = (pts[0], pts[1]), (pts[2], pts[3]), (pts[4], pts[5]), (pts[6], pts[7])
        samples = [_cubic(p0, p1, p2, p3, t / 40.0) for t in range(41)]
        dy = 3.0 * (p1[1] - p0[1])
        dx = 3.0 * (p1[0] - p0[0])
        slope0 = dy / dx if abs(dx) > 1e-9 else None
        rows.append({
            "id": f"bezier{i}",
            "style": _style(m.group("opts") or ""),
            "samples": samples,
            "start": p0,
            "end": p3,
            "initial_slope": slope0,
            "kind": "bezier",
        })
    for i, m in enumerate(LINE_RE.finditer(tikz or "")):
        x0, y0, x1, y1 = _f(m.group("x0")), _f(m.group("y0")), _f(m.group("x1")), _f(m.group("y1"))
        if None in (x0, y0, x1, y1):
            continue
        opts = m.group("opts") or ""
        if "->" in opts or "-latex" in opts.lower():
            continue
        rows.append({
            "id": f"line{i}",
            "style": _style(opts),
            "samples": [(x0, y0), (x1, y1)],
            "start": (x0, y0),
            "end": (x1, y1),
            "initial_slope": (y1 - y0) / (x1 - x0) if abs(x1 - x0) > 1e-9 else None,
            "kind": "line",
        })
    return rows


def _nearest_stroke(pt: tuple[float, float], paths: list[dict]) -> dict | None:
    best = None
    best_d = None
    for path in paths:
        for sx, sy in path["samples"]:
            d = math.hypot(pt[0] - sx, pt[1] - sy)
            if best_d is None or d < best_d:
                best_d = d
                best = path
    if best is None:
        return None
    return {**best, "dist": best_d}


def bind_labels(tikz: str) -> dict[str, dict]:
    paths = [p for p in strokes(tikz) if p["kind"] == "bezier" or (
        abs(p["end"][0] - p["start"][0]) > 0.4 and abs(p["end"][1] - p["start"][1]) > 0.05
    )]
    if not paths:
        paths = strokes(tikz)
    out = {}
    for node in letter_nodes(tikz):
        letter = node.get("letter")
        if not letter:
            continue
        hit = _nearest_stroke((node["x"], node["y"]), paths)
        if not hit:
            continue
        out[letter] = {
            "letter": letter,
            "x": node["x"],
            "y": node["y"],
            "style": hit["style"],
            "stroke_id": hit["id"],
            "dist": hit["dist"],
            "initial_slope": hit.get("initial_slope"),
            "end_y": hit["end"][1],
            "end_x": hit["end"][0],
        }
    return out


def inventory(tikz: str) -> set[str]:
    labels = {norm_label(t) for t in node_texts(tikz) if t.strip()}
    labels.discard("")
    blob = norm_label(tikz)
    return labels | ({blob} if blob else set())


def _in_tikz(obj: str, labels: set[str], blob: str) -> bool:
    n = norm_label(obj)
    if not n:
        return False
    if n in labels:
        return True
    compact = n.replace(" ", "")
    for lab in labels:
        if not lab:
            continue
        if lab.replace(" ", "") == compact:
            return True
        parts = lab.split()
        if n in parts:
            return True
        if len(n) >= 4 and len(lab) >= 4 and (n in lab or lab in n):
            return True
    return False


def stem_objects(stem: str) -> list[dict]:
    text = stem or ""
    found: list[dict] = []
    seen = set()

    def add(name: str, kind: str, span: tuple[int, int]):
        key = norm_label(name)
        if not key or key in STOP or key in seen:
            return
        seen.add(key)
        found.append({"name": name.strip(), "norm": key, "kind": kind, "span": span})

    for m in DEVICE_RE.finditer(text):
        add(m.group(0), "device", m.span())
    for m in LABELLED_RE.finditer(text):
        add(m.group(1), "labelled", m.span())
    for m in RUNS_RE.finditer(text):
        add(m.group(1), "run", (m.start(1), m.end(1)))
        if m.group(2):
            add(m.group(2), "run", (m.start(2), m.end(2)))
    for m in PATHWAY_RE.finditer(text):
        add(m.group(1), "pathway", m.span(1))
    for m in re.finditer(r"\b([A-Z])\b", text):
        if m.group(1) in "ABCD":
            continue
        add(m.group(1), "letter", m.span())
    return found


def _removed_here(stem: str, obj: dict) -> bool:
    s, e = obj["span"]
    window = (stem or "")[max(0, s - 90): min(len(stem or ""), e + 90)]
    return bool(REMOVAL_RE.search(window))


def spec_figure(packet: dict | None) -> dict:
    return (((packet or {}).get("spec") or {}).get("figure")) or {}


def declared_delta_of(packet: dict | None, result: dict | None = None) -> str:
    fig = spec_figure(packet)
    return str(fig.get("declared_delta") or "").strip()


def lbs_followup_of(packet: dict | None) -> str:
    return str(spec_figure(packet).get("lbs_followup_of") or "").strip()


def g3b_stem_objects(stem: str, tikz: str, packet: dict | None = None) -> list[dict]:
    labels = {norm_label(t) for t in node_texts(tikz) if t.strip()}
    blob = norm_label(tikz)
    follow = lbs_followup_of(packet)
    misses = []
    for obj in stem_objects(stem):
        present = _in_tikz(obj["name"], labels, blob)
        if not present:
            dm = DEVICE_RE.search(obj["name"])
            if dm and _in_tikz(dm.group(2), labels, blob):
                present = True
        if present:
            continue
        if _removed_here(stem, obj) and follow:
            continue
        misses.append({
            "gate": "G3b",
            "code": "STEM_OBJECT_ABSENT",
            "object": obj["name"],
            "removed_clause": _removed_here(stem, obj),
            "lbs_followup_of": follow or None,
            "detail": (
                "stem names %r which is not a TikZ node; removal is legal only when "
                "spec.figure.lbs_followup_of is set" % obj["name"]
            ),
        })
    return misses


def style_letter_claims(text: str) -> list[tuple[str, str]]:
    out = []
    for m in STYLE_LETTER_RE.finditer(text or ""):
        style = m.group(1).lower()
        if style == "continuous":
            style = "solid"
        out.append((m.group(2), style))
    for m in LETTER_STYLE_RE.finditer(text or ""):
        style = m.group(2).lower()
        if style == "continuous":
            style = "solid"
        out.append((m.group(1), style))
    return out


def g3c_label_stroke(stem: str, tikz: str, notes: str = "") -> list[dict]:
    bound = bind_labels(tikz)
    hits = []
    if not bound:
        return hits
    blob = " ".join([stem or "", notes or ""])
    for letter, style in style_letter_claims(blob):
        row = bound.get(letter)
        if not row:
            hits.append({
                "gate": "G3c",
                "code": "LABEL_STROKE_UNBOUND",
                "object": letter,
                "detail": "claim binds %s to %s but label has no nearest stroke" % (letter, style),
            })
            continue
        if row["style"] != style:
            hits.append({
                "gate": "G3c",
                "code": "LABEL_STROKE_MISMATCH",
                "object": letter,
                "claimed_style": style,
                "bound_style": row["style"],
                "detail": "claim %s=%s; nearest stroke is %s (id %s, dist %.3f)" % (
                    letter, style, row["style"], row["stroke_id"], row["dist"],
                ),
            })

    for letter, row in bound.items():
        pat = re.compile(r"\b" + re.escape(letter) + r"\b")
        for sent in re.split(r"(?<=[.?!])\s+", stem or ""):
            if not pat.search(sent):
                continue
            if FASTER_RE.search(sent) and LOWER_RE.search(sent):
                others = [b for k, b in bound.items() if k != letter]
                if not others:
                    continue
                steeper = min(
                    [row] + others,
                    key=lambda b: (b["initial_slope"] if b["initial_slope"] is not None else 0),
                )
                lower = min([row] + others, key=lambda b: b["end_y"])
                if steeper["letter"] != letter or lower["letter"] != letter:
                    hits.append({
                        "gate": "G3c",
                        "code": "SERIES_CLAIM_CONFLICT",
                        "object": letter,
                        "detail": (
                            "stem pins both steeper-start and lower-finish on %s; "
                            "bind gives %s style=%s slope=%s end_y=%.3f; "
                            "steeper=%s lower=%s"
                            % (
                                letter,
                                letter,
                                row["style"],
                                "%.2f" % row["initial_slope"] if row["initial_slope"] is not None else "na",
                                row["end_y"],
                                steeper["letter"],
                                lower["letter"],
                            )
                        ),
                        "bind": bound,
                    })
    return hits


def numeric_tokens(s: str) -> set[str]:
    t = (s or "").replace("−", "-").replace("–", "-")
    return set(re.findall(r"-?\d+(?:\.\d+)?", t))


def norm_tikz(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def g3d_declared_delta(src_tikz: str, dst_tikz: str, delta: str, variation: str, mode: str) -> list[dict]:
    hits = []
    src_n, dst_n = norm_tikz(src_tikz), norm_tikz(dst_tikz)
    if mode == "rewrite" and variation == "V5":
        if not dst_n:
            hits.append({
                "gate": "G3d",
                "code": "TIKZ_DELTA_UNMATCHED",
                "detail": "V5 rewrite produced no TikZ",
            })
            return hits
        if src_n and src_n == dst_n:
            hits.append({
                "gate": "G3d",
                "code": "TIKZ_DELTA_UNMATCHED",
                "detail": "V5 rewrite left the TikZ identical to source",
            })
            return hits
    if not src_n or src_n == dst_n:
        return hits
    delta_l = (delta or "").lower()
    if any(w in delta_l for w in ("unchanged", "same figure", "figure unchanged", "tikz unchanged")):
        hits.append({
            "gate": "G3d",
            "code": "TIKZ_DELTA_UNMATCHED",
            "detail": "declared_delta says the figure is unchanged but the TikZ differs from source",
        })
        return hits
    changed = numeric_tokens(src_tikz) ^ numeric_tokens(dst_tikz)
    delta_n = numeric_tokens(delta)
    if changed and delta_n and not (changed & delta_n):
        sample = ", ".join(sorted(changed)[:6])
        hits.append({
            "gate": "G3d",
            "code": "TIKZ_DELTA_UNMATCHED",
            "detail": "TikZ numbers changed (%s) but declared_delta mentions none of them" % sample,
        })
    return hits


def extra_findings(lock_hits: list[dict]) -> list[dict]:
    """Map bind/delta misses onto existing G17 codes. Does not invent new counting codes."""
    out = []
    for h in lock_hits:
        code = h.get("code")
        if code in {"LABEL_STROKE_MISMATCH", "SERIES_CLAIM_CONFLICT", "STEM_OBJECT_ABSENT"}:
            g17 = "FIGURE_STEM_CONFLICT"
            sev = "DQ"
        elif code == "TIKZ_DELTA_UNMATCHED":
            g17 = "FIGURE_STEM_CONFLICT"
            sev = "DQ"
        else:
            continue
        out.append({
            "code": g17,
            "severity": sev,
            "gate_id": h.get("gate") or "V8",
            "quoted_text": (h.get("detail") or "")[:180],
            "location": "tikz",
            "status": "CONFIRMED",
            "merged_into": None,
            "v5_code": code,
        })
    return out


def evaluate(result: dict, packet: dict | None = None, declared_delta: str | None = None) -> dict:
    tikz = tikz_of(result)
    stem = (result or {}).get("stem") or ""
    src = tikz_of((packet or {}).get("source") or {})
    spec = (packet or {}).get("spec") or {}
    variation = spec.get("variation_class") or ((result.get("teacher") or {}).get("variation_applied")) or ""
    mode = spec_figure(packet).get("mode") or "preserve"
    notes = declared_delta if declared_delta is not None else declared_delta_of(packet, result)
    g3c_notes = " ".join([
        notes,
        spec.get("instruction") or "",
        ((result.get("teacher") or {}).get("figure_note")) or "",
    ])
    hits = []
    if tikz.strip() or mode in {"rewrite", "add"}:
        hits.extend(g3b_stem_objects(stem, tikz, packet))
        hits.extend(g3c_label_stroke(stem, tikz, g3c_notes))
        delta_for_d = notes or spec.get("instruction") or ""
        hits.extend(g3d_declared_delta(src, tikz, delta_for_d, variation, mode))
    ok = not hits
    return {
        "ok": ok,
        "gate": None if ok else hits[0]["gate"],
        "hits": hits,
        "bind": bind_labels(tikz) if tikz.strip() else {},
        "extra_findings": extra_findings(hits),
    }
