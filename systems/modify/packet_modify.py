"""Packet-first modification: load the map intelligence packet for a seed row.

Law: systems/modify/grok_4_7/09_PACKET_MODIFY.md (current modify harness).
Evidence: systems/modify_archive/grok_4_7/trial_500/ (mean 3.92; form-filling trials archived).

The minted question is a SEED (form + what was asked). The writer must receive the
same map packet a fresh mint would get — unit statements, Mx records, prerequisite
gaps, JEV cell, hinges on the row — not a rearrangement of the old stem into
givens / registration triples.

This module loads that packet. It does not mint questions, call a writer, or
re-run a batch trial.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
JEV_LOOP = HERE / "jev_loop"
if str(JEV_LOOP) not in sys.path:
    sys.path.insert(0, str(JEV_LOOP))

from unit_bind import MAP_DIR, MAP_FILES, slim_unit  # noqa: E402
ON_ITEM_ABOUT_RE = re.compile(r"\s*[—\-–]\s*on the item about\b.*$", re.I)
WS_RE = re.compile(r"\s+")

_RAW_CACHE: dict[str, dict[str, dict]] = {}


def clean_mx_text(text: str) -> str:
    """Whitespace and the trailing item-about tag. The sentence itself is kept."""
    t = ON_ITEM_ABOUT_RE.sub("", str(text or "")).strip()
    return WS_RE.sub(" ", t).strip(" —-.")


def _opt_text(v: Any) -> str:
    if isinstance(v, dict):
        return str(v.get("text") or v.get("value") or "").strip()
    return str(v or "").strip()


def get_item(row: dict) -> dict:
    item = row.get("item")
    return item if isinstance(item, dict) else row


def get_stem(row: dict) -> str:
    item = get_item(row)
    return str(item.get("stem") or row.get("stem") or "").strip()


def get_options(row: dict) -> dict[str, str]:
    item = get_item(row)
    opts = item.get("options") or row.get("options") or {}
    out: dict[str, str] = {}
    if isinstance(opts, dict):
        for k, v in opts.items():
            out[str(k).upper()] = _opt_text(v)
    elif isinstance(opts, list):
        for i, v in enumerate(opts):
            out[chr(65 + i)] = _opt_text(v)
    return out


def raw_by_id(subject: str) -> dict[str, dict]:
    """Index map statements by unit_id for one subject file (cached)."""
    subj = (subject or "science").lower()
    fname = MAP_FILES.get(subj) or MAP_FILES.get("science")
    if fname in _RAW_CACHE:
        return _RAW_CACHE[fname]
    path = MAP_DIR / fname
    by_id: dict[str, dict] = {}
    if path.is_file():
        import json

        doc = json.loads(path.read_text(encoding="utf-8"))
        for row in doc.get("hinges") or doc.get("statements") or doc.get("units") or []:
            if isinstance(row, dict) and row.get("unit_id"):
                by_id[str(row["unit_id"])] = row
    _RAW_CACHE[fname] = by_id
    return by_id


def seed_unit_ids(row: dict) -> list[str]:
    out: list[str] = []
    hinges = (row.get("design") or {}).get("hinges") or []
    if isinstance(hinges, dict):
        hinges = list(hinges.values())
    if isinstance(hinges, list):
        for h in hinges:
            if isinstance(h, dict):
                hid = h.get("unit_id") or h.get("id") or h.get("hinge_id") or h.get("term")
                if hid:
                    out.append(str(hid))
    units = (row.get("question_ingest") or {}).get("units") or []
    if isinstance(units, list):
        for u in units:
            if isinstance(u, dict) and u.get("unit_id"):
                uid = str(u["unit_id"])
                if uid not in out:
                    out.append(uid)
    jt = row.get("jev_taxonomy") if isinstance(row.get("jev_taxonomy"), dict) else {}
    hid = jt.get("hinge_id")
    if hid and str(hid) not in out:
        out.insert(0, str(hid))
    rid = str(row.get("id") or "")
    m = re.match(
        r"^(?:maths?|science|chemistry|physics|biology)_grade_(\d+)_.*?((?:ch_|phy_ch_|chem_ch_|bio_ch_)\d+).*?(H\d{3})",
        rid,
        re.I,
    )
    if m and not out:
        grade = m.group(1)
        ch = m.group(2).replace("-", "_")
        h = m.group(3).upper()
        subj = str(row.get("subject") or "science").lower()
        prefix = {
            "maths": "math",
            "math": "math",
            "mathematics": "math",
            "science": "science",
            "chemistry": "science",
            "physics": "science",
            "biology": "science",
        }.get(subj, "science")
        out.append(f"{prefix}/grade_{grade}/{ch}/{h}")
    return out


def seed_cell(row: dict) -> str:
    jt = row.get("jev_taxonomy") if isinstance(row.get("jev_taxonomy"), dict) else {}
    cid = jt.get("construct_id") or jt.get("target_construct") or ""
    if cid:
        return str(cid)
    design = row.get("design") if isinstance(row.get("design"), dict) else {}
    return str(design.get("target_construct") or design.get("construct_id") or "")


def seed_subject(row: dict, meta: dict | None = None) -> str:
    meta = meta or {}
    s = str(row.get("subject") or meta.get("subj") or "science").lower()
    if s in {"math", "mathematics"}:
        return "maths"
    if s in {"chem"}:
        return "chemistry"
    if s in {"phy", "phys"}:
        return "physics"
    if s in {"bio"}:
        return "biology"
    return s


def mx_records(raw: dict) -> list[dict]:
    mx = raw.get("mx")
    if isinstance(mx, dict):
        mx = mx.get("items") or mx.get("mx") or []
    if not isinstance(mx, list) or not mx:
        mx = []
        uid = str(raw.get("unit_id") or "")
        for item in raw.get("mixups") or []:
            if not isinstance(item, dict):
                continue
            route = str(item.get("route") or "").strip()
            rec = {
                "mx_id": item.get("mx_id") or (f"{uid}/MX_{route}" if uid and route else ""),
                "route": route,
                "p1": item.get("p1"),
                "canonical_wrong_output": item.get("wrong") or item.get("canonical_wrong_output") or "",
                "observable_prediction": item.get("observable") or item.get("observable_prediction") or "",
                "confused_element": item.get("confused") or item.get("confused_element") or "",
                "corruption_path": item.get("corruption_path") or "",
                "reversed_relation": item.get("reversed_relation") or "",
            }
            links = item.get("links") or item.get("boundary_links") or []
            if links:
                rec["boundary_links"] = links
            if isinstance(item.get("border"), dict):
                rec["border"] = item["border"]
            mx.append(rec)
    if not isinstance(mx, list):
        return []
    out = []
    for row in mx:
        if not isinstance(row, dict):
            continue
        mid = str(row.get("mx_id") or "").strip()
        cwo = clean_mx_text(row.get("canonical_wrong_output") or "")
        obs = clean_mx_text(row.get("observable_prediction") or "")
        conf = clean_mx_text(row.get("confused_element") or "")
        if not (cwo or obs or conf):
            continue
        stable_id = mid or (
            f"{raw.get('unit_id')}/MX_{row.get('route')}"
            if raw.get("unit_id") and row.get("route")
            else ""
        )
        if not stable_id:
            continue
        rec = {
            "mx_id": stable_id,
            "route": str(row.get("route") or row.get("confusion_type") or "").strip(),
            "p1": row.get("p1"),
            "canonical_wrong_output": cwo,
            "observable_prediction": obs,
            "confused_element": conf,
            "corruption_path": clean_mx_text(row.get("corruption_path") or ""),
            "reversed_relation": clean_mx_text(row.get("reversed_relation") or ""),
        }
        links = row.get("boundary_links") or row.get("links") or []
        if isinstance(links, list) and links:
            rec["boundary_links"] = links
        if isinstance(row.get("border"), dict):
            rec["border"] = row["border"]
        out.append(rec)
    return out


def prereq_gaps(raw: dict) -> list[dict]:
    out: list[dict] = []
    for row in raw.get("within_chapter_prerequisites_prose") or []:
        if not isinstance(row, dict):
            continue
        cap = str(row.get("required_capability") or "").strip()
        hid = str(row.get("hinge_id") or "").strip()
        if cap or hid:
                out.append(
                {
                    "hinge_id": hid,
                    "relationship": str(row.get("relationship") or ""),
                    "required_capability": cap,
                }
            )
    for row in raw.get("prereq_prose") or []:
        if not isinstance(row, dict):
            continue
        cap = str(row.get("required_capability") or "").strip()
        hid = str(row.get("hinge_id") or "").strip()
        if cap or hid:
                out.append(
                {
                    "hinge_id": hid,
                    "relationship": str(row.get("relationship") or ""),
                    "required_capability": cap,
                }
            )
    for p in raw.get("prereq_ids") or []:
        if isinstance(p, str) and p.strip():
            out.append(
                {
                    "hinge_id": p.strip(),
                    "relationship": "prerequisite",
                    "required_capability": "",
                }
            )
    for p in raw.get("prerequisites") or []:
        if isinstance(p, str) and p.strip():
            out.append(
                {
                    "hinge_id": p.strip(),
                    "relationship": "prerequisite",
                    "required_capability": "",
                }
            )
        elif isinstance(p, dict) and (p.get("hinge_id") or p.get("unit_id")):
            out.append(
                {
                    "hinge_id": str(p.get("hinge_id") or p.get("unit_id")),
                    "relationship": str(p.get("relationship") or "prerequisite"),
                    "required_capability": str(p.get("required_capability") or ""),
                }
            )
    return out


_BAND_RANK = {
    "CORE": 1,
    "SUPPLEMENT": 2,
    "SECONDARY": 2,
    "AS": 3,
    "SENIOR_SECONDARY": 3,
    "A_LEVEL": 4,
}


def _zone_doc(raw: dict) -> dict | None:
    zone = raw.get("jev_taxonomy_zone")
    if isinstance(zone, dict) and ("admitted" in zone or "noul" in zone):
        return zone
    zone = raw.get("zone")
    if isinstance(zone, dict) and ("admitted" in zone or "noul" in zone):
        return zone
    return None


def _text_list(value) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("exclusion") or item.get("apparent_success") or "").strip()
            if text:
                out.append(text)
    return out


def _writer_context(raw: dict, law: str) -> dict:
    mechanism = raw.get("mechanism") if isinstance(raw.get("mechanism"), dict) else {}
    mastery = raw.get("mastery") if isinstance(raw.get("mastery"), dict) else {}
    lok = raw.get("lok_model") if isinstance(raw.get("lok_model"), dict) else {}
    pedagogy = raw.get("pedagogy") if isinstance(raw.get("pedagogy"), dict) else {}
    because = str(raw.get("because") or mechanism.get("causal_direction") or "").strip()
    if because == law:
        because = ""
    reasoning = str(mastery.get("reasoning") or mastery.get("reasoning_chain") or "").strip()
    not_yet = _text_list(mastery.get("not_yet") if "not_yet" in mastery else mastery.get("non_mastery_signals"))
    default = str(raw.get("student_default") or lok.get("folk_default") or pedagogy.get("lok_folk") or "").strip()
    signals = _text_list(raw.get("student_signals") if raw.get("student_signals") else lok.get("lok_signals"))
    false_success = raw.get("false_success") if isinstance(raw.get("false_success"), list) else []
    if not false_success:
        pockets = raw.get("gaming_pocket_map")
        if not isinstance(pockets, list):
            pockets = pedagogy.get("gaming_pockets")
        false_success = []
        if isinstance(pockets, list):
            for pocket in pockets:
                if isinstance(pocket, dict) and str(pocket.get("apparent_success") or "").strip():
                    false_success.append(
                        {
                            "type": str(pocket.get("type") or "").strip(),
                            "apparent_success": str(pocket.get("apparent_success") or "").strip(),
                        }
                    )
    scope = _text_list(raw.get("out_of_scope") if raw.get("out_of_scope") else raw.get("scope_exclusions"))
    check = raw.get("check") if isinstance(raw.get("check"), dict) else {}
    if not check:
        assessment = raw.get("assessment") if isinstance(raw.get("assessment"), dict) else {}
        ask = str(assessment.get("diagnostic_item") or "").strip()
        accept = str(assessment.get("expected_correct_response") or "").strip()
        if ask and accept:
            check = {"ask": ask, "accept": accept}
    operation = str(raw.get("operation") or raw.get("cognitive_operation") or "").strip()
    out = {}
    if operation:
        out["operation"] = operation
    if because:
        out["because"] = because
    if reasoning:
        out["reasoning"] = reasoning
    if not_yet:
        out["not_yet"] = not_yet
    if default:
        out["student_default"] = default
    if signals:
        out["student_signals"] = signals
    if false_success:
        out["false_success"] = false_success
    if scope:
        out["out_of_scope"] = scope
    if check:
        out["check"] = check
    return out


def _stored_line(value: object) -> str:
    return str(value or "").strip()


def _stored_law(raw: dict) -> str:
    mechanism = raw.get("mechanism") if isinstance(raw.get("mechanism"), dict) else {}
    return _stored_line(raw.get("law") or mechanism.get("law"))


def _stored_decision(raw: dict) -> str:
    return _stored_line(raw.get("decision") or raw.get("decision_hinge") or raw.get("statement"))


def _stored_boundaries(raw: dict) -> list[str]:
    mechanism = raw.get("mechanism") if isinstance(raw.get("mechanism"), dict) else {}
    raw_rows = raw.get("boundaries") or mechanism.get("boundary_conditions") or []
    if isinstance(raw_rows, str):
        raw_rows = [raw_rows]
    if not isinstance(raw_rows, list):
        return []
    out = []
    for item in raw_rows:
        text = item.get("text") if isinstance(item, dict) else item
        line = _stored_line(text)
        if line:
            out.append(line)
    return out


def _stored_anti(raw: dict) -> str:
    value = raw.get("anti_narration") or raw.get("anti_narration_constraint") or ""
    if isinstance(value, dict):
        value = value.get("forbidden_shortcut") or value.get("text") or value.get("constraint") or ""
    return _stored_line(value)


def unit_facts(raw: dict) -> dict:
    slim = slim_unit(raw)
    zone_doc = _zone_doc(raw)
    law = _stored_law(raw) or slim.get("law") or ""
    facts = {
        "unit_id": slim.get("unit_id"),
        "decision": _stored_decision(raw) or slim.get("decision") or "",
        "law": law,
        "boundaries": _stored_boundaries(raw) or slim.get("boundaries") or [],
        "zone": sorted(slim.get("zone") or []),
        "zone_known": zone_doc is not None,
        "anti_narration": _stored_anti(raw) or slim.get("anti_narration") or "",
        "grade": raw.get("grade"),
        "grade_band": raw.get("grade_band") or "",
        "board": raw.get("board") or "",
        "chapter": raw.get("chapter"),
        "node": raw.get("node") or "",
        "mx": mx_records(raw),
        "prerequisite_gaps": prereq_gaps(raw),
        "noul": zone_doc.get("noul") if isinstance(zone_doc, dict) and isinstance(zone_doc.get("noul"), dict) else None,
    }
    facts.update(_writer_context(raw, law))
    if isinstance(raw.get("entities"), list) and raw.get("entities"):
        facts["entities"] = raw["entities"]
    mastery = raw.get("mastery") if isinstance(raw.get("mastery"), dict) else {}
    if mastery.get("claim"):
        facts["mastery_claim"] = str(mastery.get("claim") or "").strip()
    if raw.get("chapter_title"):
        facts["chapter_title"] = raw.get("chapter_title")
    return facts


def _demand_parts(cell: str) -> tuple[str, int]:
    parts = (cell or "").split(".")
    family = parts[0] if parts else ""
    dok = int(parts[-1]) if parts and parts[-1].isdigit() else 0
    return family, dok


def _deep_demand(cell: str) -> bool:
    family, dok = _demand_parts(cell)
    return dok >= 3 and family in {"An", "Ev", "Cr"}


def cell_needs_support(cell: str, center: dict) -> bool:
    """True when the given hinge alone cannot carry the requested JEV cell."""
    if not cell or not center.get("zone_known"):
        return False
    zone = set(center.get("zone") or [])
    if cell not in zone:
        return True
    family, dok = _demand_parts(cell)
    noul = center.get("noul") if isinstance(center.get("noul"), dict) else {}
    rating = noul.get(cell)
    try:
        if rating is not None and float(rating) < 0.50:
            return True
    except (TypeError, ValueError):
        pass
    return dok >= 3 and family in {"An", "Ev", "Cr"}


def _eligible_neighbour(center: dict, other: dict) -> bool:
    board = str(center.get("board") or "")
    if not board or board != str(other.get("board") or ""):
        return False
    center_rank = _BAND_RANK.get(str(center.get("grade_band") or ""), 0)
    other_rank = _BAND_RANK.get(str(other.get("grade_band") or ""), 0)
    if center_rank and other_rank and other_rank < center_rank:
        return False
    return True


def _hosts_cell(raw: dict, cell: str) -> bool:
    if not cell:
        return False
    zone = _zone_doc(raw) or {}
    admitted = zone.get("admitted") if isinstance(zone.get("admitted"), list) else []
    if cell not in admitted:
        return False
    noul = zone.get("noul") if isinstance(zone.get("noul"), dict) else {}
    rating = noul.get(cell)
    if rating is None:
        return True
    try:
        return float(rating) >= 0.50
    except (TypeError, ValueError):
        return False


def neighbour_unit_ids(center_raw: dict, by_id: dict[str, dict], cell: str = "", limit: int = 2) -> list[str]:
    """Neighbour hinges: prerequisites, then same chapter, then same node and band."""
    center_id = str(center_raw.get("unit_id") or "")

    def hnum(uid: str) -> int:
        m = re.search(r"H(\d+)$", uid)
        return int(m.group(1)) if m else 10**9

    center_h = hnum(center_id)
    ranked: list[tuple[int, str]] = []

    def add(uid: str, source: int) -> None:
        if uid and uid != center_id and uid in by_id and uid not in {item[1] for item in ranked}:
            if _eligible_neighbour(center_raw, by_id[uid]):
                ranked.append((source, uid))

    for gap in prereq_gaps(center_raw):
        add(str(gap.get("hinge_id") or ""), 0)
    if not _deep_demand(cell):
        chapter = center_raw.get("chapter")
        grade = center_raw.get("grade")
        node = center_raw.get("node")
        band = str(center_raw.get("grade_band") or "")
        if chapter is not None:
            for uid, row in by_id.items():
                if row.get("chapter") == chapter and row.get("grade") == grade:
                    add(uid, 1)
        if node and band:
            for uid, row in by_id.items():
                if row.get("node") == node and str(row.get("grade_band") or "") == band:
                    add(uid, 2)
    ranked.sort(
        key=lambda item: (
            0 if _hosts_cell(by_id[item[1]], cell) else 1,
            item[0],
            abs(hnum(item[1]) - center_h),
            item[1],
        )
    )
    return [uid for _source, uid in ranked[:limit]]


def _seed_ask_hint(row: dict) -> str:
    """Form-only hint from seed — shape of what was asked; never prose to splice."""
    stem = get_stem(row)
    parts = re.split(r"(?<=[.?!])\s+", stem.strip())
    ask = parts[-1] if parts else ""
    ask = WS_RE.sub(" ", ask).strip()
    if len(ask) > 160:
        ask = ask[:157] + "..."
    ask = re.sub(r"(?i)\bis recorded as\b.*", "", ask).strip()
    ask = re.sub(
        r"(?i)\bwhat is the identity of\b.*",
        "what value follows from the facts?",
        ask,
    )
    return ask[:160]


def load_packet(row: dict, meta: dict | None = None) -> dict | None:
    """Load the map intelligence packet for a seed row.

    Returns None when no map units load or the units carry neither Mx nor facts.
    On success the packet includes every center mix-up, every prerequisite gap,
    the JEV cell, form, and whether neighbour hinges were added
    (`extra_hinge_added` / `extra_hinge_ids`). A border does not remove a mix-up.
    """
    meta = meta or {}
    subject = seed_subject(row, meta)
    uids = seed_unit_ids(row)
    cell = seed_cell(row)
    by_id = raw_by_id(subject)
    if uids and uids[0] not in by_id:
        for alt in ("science", "chemistry", "physics", "biology", "maths"):
            if alt == subject:
                continue
            alt_map = raw_by_id(alt)
            if uids[0] in alt_map:
                by_id = alt_map
                subject = alt
                break

    loaded_raw: list[dict] = []
    for uid in uids:
        if uid in by_id:
            loaded_raw.append(by_id[uid])
    if not loaded_raw and uids:
        for uid in uids:
            for cand in by_id:
                if cand.endswith(uid) or uid.endswith(cand) or uid in cand or cand in uid:
                    loaded_raw.append(by_id[cand])
                    break
            if loaded_raw:
                break

    if not loaded_raw:
        return None

    center = unit_facts(loaded_raw[0])
    units = [center]
    extra_added = False
    extra_ids: list[str] = []
    if cell_needs_support(cell, center):
        for nid in neighbour_unit_ids(loaded_raw[0], by_id, cell=cell, limit=2):
            if nid in by_id:
                neighbour = unit_facts(by_id[nid])
                units.append(neighbour)
                extra_ids.append(nid)
                extra_added = True

    center_mx = list(center.get("mx") or [])
    situation = situation_boundary(center_mx)
    if situation:
        center["situation_boundary"] = situation
    all_mx = []
    for unit in units:
        all_mx.extend(unit.get("mx") or [])
    has_facts = any((u.get("decision") or u.get("law")) for u in units)
    if not all_mx and not has_facts:
        return None

    cell_brief = {
        "construct_id": cell or None,
        "zone_known": bool(center.get("zone_known")),
        "in_center_zone": bool(center.get("zone_known") and cell and cell in set(center.get("zone") or [])),
        "center_zone": center.get("zone") or [],
        "noul": None,
    }
    if isinstance(center.get("noul"), dict) and cell:
        cell_brief["noul"] = center["noul"].get(cell)

    form = {
        "item_type": str(row.get("item_type") or get_item(row).get("item_type") or "single_mcq"),
        "n_options": max(4, len(get_options(row)) or 4),
        "band": meta.get("band") or row.get("band"),
        "subject": subject,
        "grade": row.get("grade") or center.get("grade"),
        "seed_ask_hint": _seed_ask_hint(row),
    }

    return {
        "subject": subject,
        "center_unit_id": center.get("unit_id"),
        "map_unit_ids": [u.get("unit_id") for u in units if u.get("unit_id")],
        "extra_hinge_added": extra_added,
        "extra_hinge_ids": extra_ids,
        "units": units,
        "mx_ids": [m["mx_id"] for m in all_mx],
        "mx": all_mx,
        "prerequisite_gaps": list(center.get("prerequisite_gaps") or []),
        "jev_cell": cell_brief,
        "form": form,
    }


def _kept_links(mx: dict) -> list[dict]:
    rows = mx.get("boundary_links") or mx.get("links") or []
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        boundary = str(row.get("boundary") or "").strip()
        try:
            score = float(row.get("p1"))
        except (TypeError, ValueError):
            continue
        if boundary and score >= 0.70:
            out.append({"boundary": boundary, "p1": score})
    return out


def mixups_with_border(mx_list: list[dict]) -> list[dict]:
    """Mix-ups that already have an admitted border. Highest border score first."""
    chosen = []
    for mx in mx_list:
        border = mx.get("border")
        if not isinstance(border, dict):
            continue
        text = str(border.get("text") or "").strip()
        try:
            score = float(border.get("p1"))
        except (TypeError, ValueError):
            continue
        if text and score >= 0.70:
            rec = dict(mx)
            rec["border"] = {"p1": score, "source": border.get("source"), "text": text}
            chosen.append(rec)
    chosen.sort(key=lambda mx: -float(mx["border"]["p1"]))
    return chosen


def situation_boundary(mx_list: list[dict]) -> str:
    """Boundary that the most mix-ups produce. The highest link score breaks a tie."""
    counts: dict[str, int] = {}
    best: dict[str, float] = {}
    for mx in mx_list:
        for link in _kept_links(mx):
            boundary = link["boundary"]
            counts[boundary] = counts.get(boundary, 0) + 1
            if boundary not in best or link["p1"] > best[boundary]:
                best[boundary] = link["p1"]
    if not counts:
        return ""
    return max(counts, key=lambda boundary: (counts[boundary], best[boundary], boundary))


def legal_set_for(records: list[dict], wrong_slots: int | None = None) -> dict:
    """Center-hinge legal mix-ups. Support rows are not accepted here.

    situation_verified is true only when the linked set can fill the wrong slots.
    Before the item exists, wrong_slots is None and the legal set stays the full center list.
    """
    rows = [rec for rec in records if isinstance(rec, dict) and rec.get("mx_id")]
    situation = situation_boundary(rows)
    linked: list[str] = []
    seen: set[str] = set()
    for rec in rows:
        mx_id = str(rec.get("mx_id"))
        if not situation or mx_id in seen:
            continue
        if any(link["boundary"] == situation for link in _kept_links(rec)):
            seen.add(mx_id)
            linked.append(mx_id)
    center_ids = [str(rec.get("mx_id")) for rec in rows]
    verified = bool(wrong_slots and wrong_slots > 0 and len(linked) >= wrong_slots)
    legal_ids = linked if verified else center_ids
    return {
        "situation": situation,
        "situation_verified": verified,
        "linked_ids": linked,
        "legal_ids": legal_ids,
        "center_ids": center_ids,
    }


def mixups_for_situation(mx_list: list[dict], boundary: str) -> list[dict]:
    """Mix-ups whose belief produces this boundary. Other boundaries stay off the packet."""
    chosen = []
    for mx in mx_list:
        links = [link for link in _kept_links(mx) if link["boundary"] == boundary]
        if not links:
            continue
        rec = dict(mx)
        rec["boundary_links"] = links
        chosen.append(rec)
    chosen.sort(key=lambda mx: -float(mx["boundary_links"][0]["p1"]))
    return chosen


def packet_empty_reason(packet: dict | None) -> str | None:
    if packet is None:
        return "empty_packet:no_map_units"
    if not packet.get("map_unit_ids"):
        return "empty_packet:no_map_unit_ids"
    if not packet.get("mx") and not any(
        (u.get("decision") or u.get("law")) for u in packet.get("units") or []
    ):
        return "empty_packet:no_mx_no_facts"
    return None


def writer_mx_block(m: dict, role: str) -> dict:
    """One mix-up object. T-MINT and T-MOD both send this shape."""
    block = {
        "role": role,
        "mx_id": m.get("mx_id"),
        "wrong_output_students_produce": (
            m.get("canonical_wrong_output")
            or m.get("wrong")
            or m.get("wrong_output_students_produce")
        ),
        "observable_prediction": m.get("observable_prediction") or m.get("observable"),
        "confused_element": m.get("confused_element") or m.get("confused"),
    }
    if m.get("route"):
        block["route"] = m.get("route")
    if m.get("p1") is not None:
        block["p1"] = m.get("p1")
    links = m.get("boundary_links") or m.get("links") or []
    if isinstance(links, list) and links:
        block["boundary_links"] = links
    if isinstance(m.get("border"), dict) and m.get("border"):
        block["border"] = m["border"]
    return block


def facts_for_writer(packet: dict) -> dict:
    """Teacher-side facts the writer must see — never old stem sentences."""
    unit_blocks = []
    for i, u in enumerate(packet["units"]):
        role = "center" if i == 0 else "support"
        block = {
            "role": role,
            "unit_id": u.get("unit_id"),
            "decision_do_not_print": u.get("decision"),
            "law_do_not_copy": u.get("law"),
            "boundaries": u.get("boundaries") or [],
            "anti_narration": u.get("anti_narration") or "",
        }
        if u.get("situation_boundary"):
            block["situation_boundary"] = u["situation_boundary"]
        for key in (
            "operation",
            "because",
            "reasoning",
            "student_default",
            "student_signals",
            "false_success",
            "out_of_scope",
            "check",
            "board",
            "chapter",
            "chapter_title",
            "entities",
            "mastery_claim",
        ):
            if u.get(key):
                block[key] = u[key]
        not_yet = [line for line in (u.get("not_yet") or []) if str(line or "").strip()]
        if not_yet:
            block["not_yet"] = not_yet
        unit_blocks.append(block)
    mx_blocks = []
    support_blocks = []
    for index, unit in enumerate(packet.get("units") or []):
        role = "center" if index == 0 else "support"
        for m in unit.get("mx") or []:
            if not isinstance(m, dict) or not m.get("mx_id"):
                continue
            packed = writer_mx_block(m, role)
            if role == "center":
                mx_blocks.append(packed)
            else:
                support_blocks.append(packed)
    if not mx_blocks:
        for m in packet.get("mx") or []:
            if isinstance(m, dict) and m.get("mx_id"):
                mx_blocks.append(writer_mx_block(m, "center"))
    legal = legal_set_for(mx_blocks)
    gaps = []
    for g in packet.get("prerequisite_gaps") or []:
        gaps.append(
            {
                "missing_hinge": g.get("hinge_id"),
                "required_capability": g.get("required_capability"),
            }
        )
    return {
        "subject": packet["form"]["subject"],
        "grade": packet["form"]["grade"],
        "band": packet["form"]["band"],
        "item_type": packet["form"]["item_type"],
        "n_options": packet["form"]["n_options"],
        "seed_form_hint_ask_shape_only": packet["form"].get("seed_ask_hint"),
        "jev_cell": packet.get("jev_cell"),
        "units": unit_blocks,
        "misconceptions_mx": mx_blocks,
        "support_mx": support_blocks,
        "legal_set": legal,
        "prerequisite_gaps": gaps,
    }


PROBE_DRAFT = """Design one probe for this item request. A probe is one concrete situation in which the hinge is applied. A mastered student and a student who holds the false sentence give different answers, and that difference is the crossing of the border. Use only the request, the law, and the border. Do not write the exam question. Do not restate the border with no situation.

Return JSON only: {{"text":"..."}} or {{"no_probe":"no_situation"|"out_of_request"}}.

Request: {request}
Law: {law}
Border: {border}
False sentence: {sentence}
"""

PROBE_Q = """Question type: score. Classes: 0, 1.

Request: {request}
Hinge law: {law}
Border: {border}
Probe: {probe}
Candidate Mx sentence: {sentence}

The probe is a concrete situation built for this request, in which the hinge is applied.
Label 1 only if all three are true:
- The probe is a situation this request is asking about.
- A student who has mastered the law resolves the probe one way, and a student who holds the Mx sentence as true resolves it the other way. The two answers differ.
- The difference is produced by crossing the border.

Label 0 if the probe ignores the request, if both students would resolve it the same way, if the probe only restates the border or the law, if the probe is itself the Mx sentence, or if resolving it needs a fact the request and the law do not supply.

Return the probability of label 1 and the probability of label 0."""


def parse_probe(text: str) -> dict:
    raw = (text or "").strip()
    start = raw.find("{")
    if start < 0:
        raise ValueError("probe draft returned no JSON")
    try:
        obj, _end = json.JSONDecoder().raw_decode(raw[start:])
    except json.JSONDecodeError:
        end = raw.rfind("}")
        if end <= start:
            raise ValueError("probe draft returned no JSON")
        obj = json.loads(raw[start:end + 1])
    if not isinstance(obj, dict):
        raise ValueError("probe draft JSON was not an object")
    if obj.get("no_probe"):
        return {"no_probe": str(obj["no_probe"])}
    sentence = str(obj.get("text") or "").strip()
    if not sentence:
        raise ValueError("probe draft text was empty")
    return {"text": sentence}


def _lead_border(writer_packet: dict) -> dict | None:
    units = writer_packet.get("units") or []
    center = next((unit for unit in units if unit.get("role") == "center"), None)
    if center is None and units:
        center = units[0]
    law = str((center or {}).get("law_do_not_copy") or "")
    best = None
    for mx in writer_packet.get("misconceptions_mx") or []:
        border = mx.get("border") if isinstance(mx, dict) else None
        if not isinstance(border, dict):
            continue
        text = str(border.get("text") or "").strip()
        try:
            score = float(border.get("p1"))
        except (TypeError, ValueError):
            continue
        if not text or score < 0.70:
            continue
        if best is None or score > best["p1"]:
            best = {
                "border": text,
                "law": law,
                "mx_id": mx.get("mx_id"),
                "p1": score,
                "wrong": str(mx.get("wrong_output_students_produce") or ""),
            }
    return best


def admit_probe(writer_packet: dict, request: str, draft_fn, score_fn) -> dict:
    """Design a probe for this request and keep it when the score is at least 0.70.

    draft_fn(request, law, border, sentence) -> {"text"} or {"no_probe"}.
    score_fn(request, law, border, probe, sentence) -> label-1 probability.
    Below 0.40 stops. The band between allows at most three drafts.
    """
    lead = _lead_border(writer_packet)
    if lead is None:
        return {"reason": "no_border"}
    best_p = 0.0
    for attempt in range(1, 4):
        made = draft_fn(request, lead["law"], lead["border"], lead["wrong"])
        if not isinstance(made, dict) or made.get("no_probe"):
            return {
                "best_p1": round(best_p, 4),
                "mx_id": lead["mx_id"],
                "note": str((made or {}).get("no_probe") or "declined"),
                "reason": "drafter_declined",
            }
        p1 = float(score_fn(request, lead["law"], lead["border"], made["text"], lead["wrong"]))
        best_p = max(best_p, p1)
        if p1 >= 0.70:
            return {
                "border": lead["border"],
                "mx_id": lead["mx_id"],
                "p1": round(p1, 4),
                "text": made["text"],
            }
        if p1 < 0.40:
            break
        if attempt >= 3:
            break
    return {"best_p1": round(best_p, 4), "mx_id": lead["mx_id"], "reason": "probe_not_admitted"}


def packet_for_row(row: dict, meta: dict | None = None) -> dict:
    """Public entry: load packet + writer facts + whether an extra hinge is required.

    Returns
    -------
    {
      "ok": bool,
      "empty_reason": str | None,
      "packet": dict | None,          # raw map packet (or None)
      "writer_packet": dict | None,   # facts_for_writer shape (or None)
      "extra_hinge_required": bool,
      "extra_hinge_ids": list[str],
      "map_unit_ids": list[str],
    }
    """
    packet = load_packet(row, meta)
    empty = packet_empty_reason(packet)
    if empty:
        return {
            "ok": False,
            "empty_reason": empty,
            "packet": None,
            "writer_packet": None,
            "extra_hinge_required": False,
            "extra_hinge_ids": [],
            "map_unit_ids": [],
        }
    assert packet is not None
    return {
        "ok": True,
        "empty_reason": None,
        "packet": packet,
        "writer_packet": facts_for_writer(packet),
        "extra_hinge_required": bool(packet.get("extra_hinge_added")),
        "extra_hinge_ids": list(packet.get("extra_hinge_ids") or []),
        "map_unit_ids": list(packet.get("map_unit_ids") or []),
    }


def _key_letter(item: dict) -> str:
    ans = item.get("answer")
    if isinstance(ans, dict):
        for k in ("letter", "correct", "value", "key"):
            v = ans.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip().upper()[:1]
    if isinstance(ans, str) and ans.strip():
        return ans.strip().upper()[:1]
    return ""


def attach_wrong_option_feedback(item: dict, writer_packet: dict | None) -> dict:
    """Write feedback only on a wrong option that cites one packet mx_id.

    Uncited wrong options stay without feedback. Nothing is assigned by position.
    """
    if not isinstance(item, dict) or not writer_packet:
        return item
    try:
        from systems.question_ingest.option_feedback import (
            OPTION_FEEDBACK_FIELD,
            has_valid_feedback,
            make_feedback,
        )
    except ImportError:
        OPTION_FEEDBACK_FIELD = "feedback"

        def has_valid_feedback(option):  # type: ignore
            if not isinstance(option, dict):
                return False
            fb = option.get(OPTION_FEEDBACK_FIELD)
            return (
                isinstance(fb, dict)
                and bool(str(fb.get("learning_state") or "").strip())
                and bool(str(fb.get("evidence") or "").strip())
                and str(fb.get("source") or "") in {"misconception", "prerequisite_gap"}
            )

        def make_feedback(*, learning_state, evidence, source):  # type: ignore
            return {
                "learning_state": learning_state,
                "evidence": evidence,
                "source": source,
            }

    mxs = [m for m in (writer_packet.get("misconceptions_mx") or []) if isinstance(m, dict)]
    gaps = [g for g in (writer_packet.get("prerequisite_gaps") or []) if isinstance(g, dict)]
    if not mxs and not gaps:
        return item

    key = _key_letter(item)
    opts = item.get("options")
    if not isinstance(opts, list):
        return item

    by_mx = {str(m.get("mx_id")): m for m in mxs if m.get("mx_id")}
    cited = item.get("mx_option_map") if isinstance(item.get("mx_option_map"), dict) else {}
    out_opts = []
    for i, raw in enumerate(opts):
        if not isinstance(raw, dict):
            out_opts.append(raw)
            continue
        opt = dict(raw)
        letter = str(opt.get("id") or chr(65 + i)).upper()[:1]
        if key and letter == key:
            out_opts.append(opt)
            continue
        if has_valid_feedback(opt):
            out_opts.append(opt)
            continue
        mx_id = str(cited.get(letter) or opt.get("mx_id") or "").strip()
        m = by_mx.get(mx_id)
        if m is None:
            out_opts.append(opt)
            continue
        claim = (
            str(m.get("wrong_output_students_produce") or "").strip()
            or str(m.get("confused_element") or "").strip()
            or str(m.get("observable_prediction") or "").strip()
        )
        evidence = (
            str(m.get("observable_prediction") or "").strip()
            or str(m.get("confused_element") or "").strip()
            or claim
        )
        if claim and evidence:
            opt[OPTION_FEEDBACK_FIELD] = make_feedback(
                learning_state=claim if claim.endswith((".", "!", "?")) else claim + ".",
                evidence=evidence if evidence.endswith((".", "!", "?")) else evidence + ".",
                source="misconception",
            )
        out_opts.append(opt)

    item = dict(item)
    item["options"] = out_opts
    return item


def _absorb_mx_citations(item: dict, by_id: dict, keyed: set[str] | None = None) -> None:
    """Copy generation-time citations into mx_option_map before the strict bind."""
    keyed = keyed or set()
    cited = dict(item.get("mx_option_map") or {}) if isinstance(item.get("mx_option_map"), dict) else {}
    options = item.get("options") if isinstance(item.get("options"), list) else []
    for index, raw in enumerate(options):
        if not isinstance(raw, dict):
            continue
        letter = str(raw.get("id") or chr(65 + index)).strip().upper()[:1]
        found = raw.get("mx_id") or raw.get("source_id") or raw.get("mx")
        if isinstance(found, str) and found in by_id and letter not in cited and letter not in keyed:
            cited[letter] = found
    if cited:
        item["mx_option_map"] = cited
    statement_map = dict(item.get("statement_mx_map") or {}) if isinstance(item.get("statement_mx_map"), dict) else {}
    statements = item.get("statements") if isinstance(item.get("statements"), list) else []
    for index, raw in enumerate(statements):
        if not isinstance(raw, dict):
            continue
        sid = str(raw.get("id") or index + 1)
        found = raw.get("mx_id") or raw.get("source_id")
        if isinstance(found, str) and found in by_id and sid not in statement_map:
            statement_map[sid] = found
    if statement_map:
        item["statement_mx_map"] = statement_map


def bind_cited_mx(item: dict, mx_records: list[dict] | None) -> str | None:
    """Stamp each wrong option from the mx_id the writer cited at generation.

    learning_state and evidence are verbatim map sentences for that mx_id.
    Returns an error when a wrong option has no distinct packet mx_id.
    Choice items with no wrong options return an error. Open responses are left unchanged.
    """
    if not isinstance(item, dict):
        return "item is not an object"
    kind = str(item.get("item_type") or "")
    if kind in {"open_response", "structured_parts"}:
        return None
    records = [m for m in (mx_records or []) if isinstance(m, dict) and m.get("mx_id")]
    by_id = {str(m["mx_id"]): m for m in records}
    if not by_id:
        return "hinge has no mix-up records to bind"

    try:
        from systems.question_ingest.option_feedback import OPTION_FEEDBACK_FIELD, make_feedback
    except ImportError:
        OPTION_FEEDBACK_FIELD = "feedback"

        def make_feedback(*, learning_state, evidence, source):  # type: ignore
            return {"learning_state": learning_state, "evidence": evidence, "source": source}

    answer = item.get("answer") if isinstance(item.get("answer"), dict) else {}
    if isinstance(answer.get("pattern"), str):
        answer = dict(answer)
        answer["pattern"] = [ch for ch in answer["pattern"].upper() if ch in {"T", "F"}]
        item["answer"] = answer
    elif isinstance(answer.get("pattern"), dict):
        roman_index = {label: index for index, label in enumerate(
            ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"], 0
        )}
        ranked = []
        for key, flag in answer["pattern"].items():
            token = str(key).strip().upper()
            if token in roman_index:
                rank = roman_index[token]
            elif token.isdigit():
                rank = int(token)
            else:
                continue
            mark = str(flag).strip().upper()[:1]
            if mark in {"T", "F"}:
                ranked.append((rank, mark))
        if ranked:
            answer = dict(answer)
            answer["pattern"] = [mark for _, mark in sorted(ranked)]
            item["answer"] = answer
    keyed = set()
    letter = str(answer.get("letter") or "").strip().upper()
    if len(letter) == 1 and letter.isalpha():
        keyed.add(letter)
    for raw in answer.get("letters") or []:
        token = str(raw).strip().upper()
        if len(token) == 1 and token.isalpha():
            keyed.add(token)
    _absorb_mx_citations(item, by_id, keyed)

    cited_map = item.get("mx_option_map") if isinstance(item.get("mx_option_map"), dict) else {}
    used: set[str] = set()

    def stamp(target: dict, cited: str) -> str | None:
        mx_id = str(cited or "").strip()
        if mx_id not in by_id:
            return f"cited mx_id {mx_id!r} is not on this hinge"
        if mx_id in used:
            return f"mx_id {mx_id} is already bound to another wrong option"
        used.add(mx_id)
        rec = by_id[mx_id]
        claim = str(
            rec.get("wrong")
            or rec.get("canonical_wrong_output")
            or rec.get("wrong_output_students_produce")
            or rec.get("confused")
            or rec.get("confused_element")
            or rec.get("observable")
            or rec.get("observable_prediction")
            or ""
        ).strip()
        evidence = str(
            rec.get("observable")
            or rec.get("observable_prediction")
            or rec.get("confused")
            or rec.get("confused_element")
            or claim
        ).strip()
        if not claim or not evidence:
            return f"mx_id {mx_id} has no map sentence"
        target["mx_refs"] = [{
            "source": "map",
            "unit_id": rec.get("unit_id") or "",
            "ref": mx_id,
            "confusion_type": rec.get("route") or "",
            "label": claim,
        }]
        target[OPTION_FEEDBACK_FIELD] = make_feedback(
            learning_state=claim if claim.endswith((".", "!", "?")) else claim + ".",
            evidence=evidence if evidence.endswith((".", "!", "?")) else evidence + ".",
            source="misconception",
        )
        return None

    rows = item.get("rows")
    options = item.get("options")
    if item.get("item_type") == "option_table" and not options and isinstance(rows, list):
        built = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            letter = str(row.get("letter") or row.get("id") or chr(65 + index)).strip().upper()[:1]
            claim = str(row.get("claim") or row.get("text") or "").strip()
            reason = str(row.get("reason") or "").strip()
            text = f"{claim}; {reason}" if claim and reason else (claim or reason)
            built.append({"id": letter, "text": text})
        if built:
            item["options"] = built
            options = built
    wrong_n = 0
    if isinstance(options, list):
        for index, raw in enumerate(options):
            if not isinstance(raw, dict):
                continue
            opt_letter = str(raw.get("id") or chr(65 + index)).strip().upper()[:1]
            if opt_letter in keyed:
                raw.pop("mx_refs", None)
                raw.pop(OPTION_FEEDBACK_FIELD, None)
                continue
            wrong_n += 1
            cited = cited_map.get(opt_letter) or cited_map.get(opt_letter.lower()) or raw.get("mx_id")
            err = stamp(raw, str(cited or ""))
            if err:
                return f"option {opt_letter}: {err}"
            cited_map[opt_letter] = raw["mx_refs"][0]["ref"]

    pattern = answer.get("pattern") if isinstance(answer.get("pattern"), list) else []
    statements = item.get("statements") if isinstance(item.get("statements"), list) else []
    statement_map = item.get("statement_mx_map") if isinstance(item.get("statement_mx_map"), dict) else {}
    if pattern and statements:
        normalized: list[dict] = []
        for index, raw in enumerate(statements):
            if isinstance(raw, str):
                raw = {"id": str(index + 1), "text": raw}
            if isinstance(raw, dict):
                normalized.append(raw)
        if normalized:
            item["statements"] = normalized
            statements = normalized
        for index, raw in enumerate(statements):
            if not isinstance(raw, dict):
                continue
            flag = str(pattern[index]).strip().upper() if index < len(pattern) else ""
            sid = str(raw.get("id") or index + 1)
            if flag != "F":
                raw.pop("mx_refs", None)
                raw.pop(OPTION_FEEDBACK_FIELD, None)
                continue
            wrong_n += 1
            roman = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
            cited = (
                statement_map.get(sid)
                or statement_map.get(str(index + 1))
                or (statement_map.get(roman[index + 1]) if index + 1 < len(roman) else None)
                or raw.get("mx_id")
            )
            err = stamp(raw, str(cited or ""))
            if err:
                return f"statement {sid}: {err}"
            statement_map[sid] = raw["mx_refs"][0]["ref"]

    if wrong_n == 0:
        return "no wrong option or false statement to bind"
    item["mx_option_map"] = {
        **{str(k): str(v) for k, v in cited_map.items()},
    }
    if statement_map:
        item["statement_mx_map"] = {str(k): str(v) for k, v in statement_map.items()}
    ws = item.get("worked_solution")
    if item.get("item_type") == "option_table" and isinstance(ws, dict) and isinstance(options, list):
        key = next(iter(keyed), "")
        keyed_text = ""
        for opt in options:
            if isinstance(opt, dict) and str(opt.get("id") or "").upper()[:1] == key:
                keyed_text = str(opt.get("text") or "").strip()
                break
        if key and keyed_text:
            ws["key_letter"] = key
            ws["result"] = keyed_text
    return None
