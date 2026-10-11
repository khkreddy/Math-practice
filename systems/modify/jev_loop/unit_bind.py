"""Bind a mint requirement to one map unit before any writer call.

The live maps are read only. This module does not score new edges.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP_DIR = HERE.parents[2] / "data" / "maps" / "jev" / "sanitized"

MAP_FILES = {
    "science": "SCIENCE_MAP_G68_AGENT.json",
    "maths": "MATHEMATICS_MAP_AGENT.json",
    "math": "MATHEMATICS_MAP_AGENT.json",
    "mathematics": "MATHEMATICS_MAP_AGENT.json",
    "chemistry": "CHEMISTRY_MAP_AGENT.json",
    "chem": "CHEMISTRY_MAP_AGENT.json",
    "physics": "PHYSICS_MAP_AGENT.json",
    "phy": "PHYSICS_MAP_AGENT.json",
    "biology": "BIOLOGY_MAP_AGENT.json",
    "bio": "BIOLOGY_MAP_AGENT.json",
}


def _clip(text, n: int) -> str:
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    return s[:n]


def _plain(text) -> str:
    """Writer-facing text. Whitespace is collapsed. The sentence is not cut."""
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def map_file_for(req: dict) -> str:
    blob = f"{req.get('unit_id') or ''} {req.get('hinge_id') or ''}"
    if "phy_ch" in blob:
        return MAP_FILES["physics"]
    if "chem_ch" in blob:
        return MAP_FILES["chemistry"]
    subject = str(req.get("subject") or "science").lower()
    return MAP_FILES.get(subject, MAP_FILES["science"])


def _law_of(mechanism) -> str:
    if isinstance(mechanism, dict):
        return _clip(mechanism.get("law") or "", 800)
    return _clip(mechanism, 800)


def _boundaries(row: dict) -> list[str]:
    mechanism = row.get("mechanism")
    raw = mechanism.get("boundary_conditions") if isinstance(mechanism, dict) else None
    if not raw:
        raw = row.get("boundaries") or []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        text = item.get("text") if isinstance(item, dict) else item
        line = _clip(text, 400)
        if line:
            out.append(line)
    return out


_ITEM_ABOUT = " on the item about"


def _mx_text(row) -> str:
    if isinstance(row, dict):
        raw = (
            row.get("canonical_wrong_output")
            or row.get("wrong")
            or row.get("confused_element")
            or row.get("confusion_type")
            or ""
        )
    else:
        raw = row
    text = re.sub(r"\s+", " ", str(raw or "")).strip()
    cut = text.lower().find(_ITEM_ABOUT)
    if cut >= 20:
        text = text[:cut].rstrip(" —-")
    return _clip(text, 320)


def _mx_lines(mx) -> list[str]:
    if isinstance(mx, dict):
        mx = mx.get("items") or mx.get("mx") or []
    if not isinstance(mx, list):
        return []
    out = []
    seen = set()
    for row in mx:
        line = _mx_text(row)
        if line and line not in seen:
            seen.add(line)
            out.append(line)
    return out


def _one_mx(mx) -> str:
    lines = _mx_lines(mx)
    return lines[0] if lines else ""


def _anti(row: dict) -> str:
    raw = (
        row.get("anti_narration_constraint")
        or row.get("anti_narration")
        or row.get("do_not_reveal")
        or ""
    )
    if isinstance(raw, dict):
        raw = raw.get("forbidden_shortcut") or raw.get("text") or raw.get("constraint") or ""
    return _plain(raw)


def _zone(row: dict) -> set[str]:
    zone = row.get("jev_taxonomy_zone")
    if not isinstance(zone, dict):
        zone = row.get("zone") if isinstance(row.get("zone"), dict) else {}
    admitted = zone.get("admitted") if isinstance(zone, dict) else None
    if not isinstance(admitted, list):
        return set()
    return {c for c in admitted if isinstance(c, str) and c}


def _mx_rows(row: dict) -> list:
    mx = row.get("mx")
    if isinstance(mx, dict):
        mx = mx.get("items") or mx.get("mx") or []
    if isinstance(mx, list) and mx:
        return mx
    mixups = row.get("mixups")
    if not isinstance(mixups, list):
        return []
    uid = str(row.get("unit_id") or "")
    out = []
    for item in mixups:
        if not isinstance(item, dict):
            continue
        route = str(item.get("route") or item.get("confusion_type") or "").strip()
        wrong = item.get("wrong") or item.get("canonical_wrong_output") or ""
        rec = {
            "mx_id": item.get("mx_id") or (f"{uid}/MX_{route}" if uid and route else ""),
            "route": route,
            "confusion_type": route,
            "wrong": wrong,
            "canonical_wrong_output": wrong,
            "confused": item.get("confused") or item.get("confused_element") or "",
            "confused_element": item.get("confused") or item.get("confused_element") or "",
            "observable": item.get("observable") or item.get("observable_prediction") or "",
            "observable_prediction": item.get("observable") or item.get("observable_prediction") or "",
            "p1": item.get("p1"),
        }
        links = item.get("links") or item.get("boundary_links") or []
        if links:
            rec["boundary_links"] = links
            rec["links"] = links
        if isinstance(item.get("border"), dict):
            rec["border"] = item["border"]
        out.append(rec)
    return out


def mx_records_of(row: dict) -> list[dict]:
    """Stable mx ids for generation-time binding onto wrong options."""
    uid = str(row.get("unit_id") or "")
    out = []
    for index, item in enumerate(_mx_rows(row), start=1):
        if not isinstance(item, dict):
            continue
        route = str(item.get("route") or item.get("confusion_type") or "mx").strip() or "mx"
        wrong = _plain(
            item.get("wrong") or item.get("canonical_wrong_output") or item.get("wrong_output_students_produce") or ""
        )
        confused = _plain(item.get("confused") or item.get("confused_element") or "")
        observable = _plain(item.get("observable") or item.get("observable_prediction") or "")
        if not wrong and not confused and not observable:
            continue
        mx_id = str(item.get("mx_id") or "").strip() or (f"{uid}/MX_{route}" if uid and route else "")
        rec = {
            "mx_id": mx_id,
            "route": route,
            "wrong": wrong,
            "confused": confused,
            "observable": observable,
            "unit_id": uid,
            "p1": item.get("p1"),
        }
        links = item.get("boundary_links") or item.get("links") or []
        if isinstance(links, list) and links:
            rec["boundary_links"] = links
        if isinstance(item.get("border"), dict):
            rec["border"] = item["border"]
        out.append(rec)
    return out


def situation_boundary_of(records: list[dict]) -> str:
    """Boundary most mix-ups produce, using admitted links (p1 >= 0.70)."""
    counts: dict[str, int] = {}
    best: dict[str, float] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        for link in rec.get("boundary_links") or rec.get("links") or []:
            if not isinstance(link, dict):
                continue
            boundary = str(link.get("boundary") or link.get("text") or "").strip()
            try:
                score = float(link.get("p1"))
            except (TypeError, ValueError):
                continue
            if not boundary or score < 0.70:
                continue
            counts[boundary] = counts.get(boundary, 0) + 1
            if boundary not in best or score > best[boundary]:
                best[boundary] = score
    if not counts:
        return ""
    return max(counts, key=lambda boundary: (counts[boundary], best[boundary], boundary))


def slim_unit(row: dict) -> dict:
    mechanism = row.get("mechanism")
    decision = _plain(row.get("decision_hinge") or row.get("decision") or "")
    if not decision:
        decision = _plain(row.get("statement") or "")
    law = _law_of(mechanism) or _clip(row.get("law") or "", 800)
    mx_rows = _mx_rows(row)
    records = mx_records_of(row)
    routes = [str(rec.get("route") or "") for rec in records if rec.get("route")]
    duplicate_routes = sorted({route for route in routes if routes.count(route) > 1})
    mastery = row.get("mastery") if isinstance(row.get("mastery"), dict) else {}
    return {
        "unit_id": row.get("unit_id"),
        "node": row.get("node") or "",
        "grade": row.get("grade"),
        "board": row.get("board") or "",
        "chapter": row.get("chapter") or "",
        "chapter_title": row.get("chapter_title") or "",
        "decision": decision,
        "law": law,
        "because": _plain(row.get("because") or ""),
        "operation": _clip(row.get("operation") or row.get("cognitive_operation") or "", 80),
        "student_default": _clip(row.get("student_default") or "", 320),
        "false_success": row.get("false_success") if isinstance(row.get("false_success"), list) else [],
        "entities": row.get("entities") if isinstance(row.get("entities"), list) else [],
        "mastery_claim": _clip(mastery.get("claim") or "", 400),
        "boundaries": _boundaries(row),
        "situation_boundary": situation_boundary_of(records),
        "zone": _zone(row),
        "mx": _one_mx(mx_rows),
        "mx_lines": _mx_lines(mx_rows),
        "mx_records": records,
        "duplicate_routes": duplicate_routes,
        "anti_narration": _anti(row),
    }


@lru_cache(maxsize=8)
def _tables(filename: str):
    path = MAP_DIR / filename
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("hinges") or doc.get("statements") or doc.get("units") or []
    by_id = {}
    by_node: dict[str, list] = {}
    for row in rows:
        if not isinstance(row, dict) or not row.get("unit_id"):
            continue
        rec = slim_unit(row)
        by_id[rec["unit_id"]] = rec
        if rec["node"]:
            by_node.setdefault(rec["node"], []).append(rec)
    return by_id, by_node


def load_tables(req: dict):
    return _tables(map_file_for(req))


def choose_unit(units: list[dict], target: str, grade) -> dict | None:
    hosts = [u for u in units if target in (u.get("zone") or set())]
    graded = [u for u in hosts if grade is not None and u.get("grade") == grade]
    return (graded or hosts or [None])[0]


def bind_requirement(req: dict, tables=None):
    """Return (unit or None, reason).

    reason is BOUND, AIM_NOT_IN_ZONE, HINGE_UNBOUND, or MAP_UNAVAILABLE.
    """
    if tables is None:
        tables = load_tables(req)
    if not tables:
        return None, "MAP_UNAVAILABLE"
    by_id, by_node = tables
    target = req.get("target_construct") or ""
    uid = str(req.get("unit_id") or "").strip()
    hid = str(req.get("hinge_id") or "").strip()
    unit = None
    if uid and uid in by_id:
        unit = by_id[uid]
    elif hid and hid in by_id:
        unit = by_id[hid]
    elif hid and hid in by_node:
        unit = choose_unit(by_node[hid], target, req.get("grade"))
        if unit is None:
            return None, "AIM_NOT_IN_ZONE"
    else:
        return None, "HINGE_UNBOUND"
    if target not in unit["zone"]:
        return unit, "AIM_NOT_IN_ZONE"
    return unit, "BOUND"


def procedure_leaked(stem: str, law: str) -> bool:
    """True when an 8-word span of the unit law is copied into the stem."""
    sw = _words(stem)
    lw = _words(law)
    if len(lw) < 8 or len(sw) < 8:
        return False
    blob = " ".join(sw)
    for i in range(0, len(lw) - 7):
        if " ".join(lw[i:i + 8]) in blob:
            return True
    return False
