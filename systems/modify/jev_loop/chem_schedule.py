"""First-pass schedule for secondary-school chemistry mints.

Reads the chemistry map and the two chemistry banks. Does not call JEV.
Release is MIQG TOP. noul below 0.50 does not block an append.
A requirement is emitted only for a secondary unit with a non-empty zone.
The requested cell is inside that zone. A seed is accepted only when an
existing chemistry-bank item is hinged on that same unit.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import bank_gate
import unit_bind

HERE = Path(__file__).resolve().parent
TTWIN_ROOT = HERE.parents[2]

DEFAULT_MAP = TTWIN_ROOT / "data" / "maps" / "jev" / "sanitized" / "CHEMISTRY_MAP_AGENT.json"
DEFAULT_BANKS = (
    TTWIN_ROOT / "data" / "questions" / "secondary_9_10" / "chemistry.jsonl",
    TTWIN_ROOT / "data" / "questions" / "senior_11_12" / "chemistry.jsonl",
)
CHEMISTRY_JSONL = TTWIN_ROOT / "data" / "questions" / "secondary_9_10" / "chemistry.jsonl"

SECONDARY_SYLLABI = frozenset({
    "NCERT_SECONDARY",
    "CISCE_ICSE",
    "CAMBRIDGE_IGCSE_CORE",
    "CAMBRIDGE_IGCSE_SUPPLEMENT",
})
SECONDARY_GRADE_BANDS = frozenset({"SECONDARY", "CORE", "SUPPLEMENT"})
PROCESS_RANK = {"An": 0, "Ev": 1, "Ap": 2, "Cr": 3, "U": 4, "R": 5}
ANSWER_KINDS = frozenset({"single_letter", "letter_set", "part_answers"})
CHEM_SOURCE = "t-mint-secondary-chemistry"
CONSTRUCT_RE = re.compile(r"^(R|U|Ap|An|Ev|Cr)\.(Fa|Co|Pr|Me)\.[1-4]$")

DEMAND = (
    "Secondary sitting item on this unit only. "
    "Write one short non-routine item with given data, two competing claims, or a numerical result. "
    "Stay inside the out-of-scope line when one is given. "
    "One decision only. Do not name the method, do not restate the law, and do not print a taxonomy code. "
    "Do not use class 11, class 12, or A-level facts outside this unit. "
    "Do not copy an eight-word span of the unit statement into the stem. "
)


def _load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def iter_bank_rows(paths) -> list[dict]:
    rows = []
    for path in paths:
        p = Path(path)
        if not p.is_file():
            continue
        with p.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    return rows


def zone_cells(row: dict) -> list[str]:
    zone = row.get("jev_taxonomy_zone") or {}
    admitted = zone.get("admitted") if isinstance(zone, dict) else None
    if not isinstance(admitted, list):
        return []
    out = []
    seen = set()
    for cell in admitted:
        if isinstance(cell, str) and cell and cell not in seen and CONSTRUCT_RE.match(cell):
            seen.add(cell)
            out.append(cell)
    return out


def is_secondary_unit(row: dict) -> bool:
    if not isinstance(row, dict) or not row.get("unit_id"):
        return False
    if row.get("grade_band") not in SECONDARY_GRADE_BANDS:
        return False
    if row.get("syllabus") in SECONDARY_SYLLABI:
        return True
    return row.get("board") in {"NCERT", "CISCE", "CAMBRIDGE"}


def grade_for(unit_id: str) -> int:
    text = str(unit_id or "")
    if "grade_09" in text:
        return 9
    if "grade_10" in text:
        return 10
    return 10


def _dok(cell: str) -> int:
    tail = str(cell).rsplit(".", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def _process(cell: str) -> str:
    return str(cell).split(".", 1)[0]


def pick_cell(zone: list[str], cell_counts: Counter, unit_id: str) -> str:
    """Least-occupied in-zone cell. Higher DoK, then Analyze/Evaluate/Apply, then id."""

    def key(cell: str):
        return (
            int(cell_counts[(unit_id, cell)]),
            -_dok(cell),
            PROCESS_RANK.get(_process(cell), 9),
            cell,
        )

    return min(zone, key=key)


def seed_allowed(row: dict, unit_id: str) -> bool:
    """True only for a chemistry-bank item hinged on this unit."""
    if not isinstance(row, dict) or not unit_id:
        return False
    subject = str(row.get("subject") or "").strip().lower()
    if subject not in {"chemistry", "chem"}:
        return False
    tag = row.get("jev_taxonomy")
    if not isinstance(tag, dict):
        return False
    return tag.get("hinge_id") == unit_id


def _statement(row: dict) -> str:
    text = row.get("statement") or row.get("decision") or row.get("decision_hinge") or ""
    return " ".join(str(text).split())


def _exclusion(row: dict) -> str:
    raw = (row.get("assessment") or {}).get("scope_exclusions") if isinstance(row.get("assessment"), dict) else None
    if not raw:
        raw = row.get("out_of_scope")
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return ""
    parts = []
    for item in raw:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            parts.append(str(item.get("exclusion") or item.get("text") or ""))
    return " ".join(" ".join(parts).split())


def build_intent(statement: str, exclusion: str) -> str:
    tail = "Unit statement: " + " ".join(str(statement or "").split())
    extra = " ".join(str(exclusion or "").split())
    if extra:
        tail += " Out of scope: " + extra
    room = 1000 - len(DEMAND)
    if room < 1:
        return DEMAND[:1000]
    if len(tail) > room:
        tail = tail[:room].rstrip()
    return DEMAND + tail


def _requirement_id(unit_id: str, construct: str) -> str:
    slug = "".join(ch if ch.isalnum() else "-" for ch in unit_id)
    slug = "-".join(part for part in slug.split("-") if part)
    cid = construct.replace(".", "")
    return f"chem-sec-{slug}-{cid}"[:80]


def _chapter(row: dict) -> str:
    node = str(row.get("node") or "").strip()
    if node:
        return node[:80]
    return str(row.get("syllabus") or "chemistry")[:80]


def admit_counts(rows: list[dict], unit_ids: set[str]) -> tuple[Counter, Counter]:
    """Admitted chemistry rows joined on jev_taxonomy.hinge_id."""
    by_unit: Counter = Counter()
    by_cell: Counter = Counter()
    for row in rows:
        if not isinstance(row, dict):
            continue
        tag = row.get("jev_taxonomy")
        if not isinstance(tag, dict) or not tag.get("admitted"):
            continue
        hinge = tag.get("hinge_id")
        if hinge not in unit_ids:
            continue
        by_unit[hinge] += 1
        construct = tag.get("construct_id")
        if isinstance(construct, str) and construct:
            by_cell[(hinge, construct)] += 1
    return by_unit, by_cell


def first_pass(map_path=None, bank_paths=None) -> dict:
    """One requirement per non-empty secondary zone, least-covered units first."""
    doc = _load_json(Path(map_path) if map_path else DEFAULT_MAP)
    statements = doc.get("hinges") or doc.get("statements") or doc.get("units") or []
    secondary = [row for row in statements if is_secondary_unit(row)]
    kept = []
    skipped = []
    zones = {}
    for row in secondary:
        cells = zone_cells(row)
        uid = row["unit_id"]
        if not cells:
            skipped.append({
                "unit_id": uid,
                "reason": "EMPTY_ZONE",
                "syllabus": row.get("syllabus"),
            })
            continue
        zones[uid] = cells
        kept.append(row)
    unit_ids = set(zones)
    bank_rows = iter_bank_rows(bank_paths or DEFAULT_BANKS)
    by_unit, by_cell = admit_counts(bank_rows, unit_ids)
    kept.sort(key=lambda row: (int(by_unit[row["unit_id"]]), row["unit_id"]))
    requirements = []
    for row in kept:
        uid = row["unit_id"]
        cell = pick_cell(zones[uid], by_cell, uid)
        grade = grade_for(uid)
        statement = _statement(row)
        title = statement if statement else uid
        requirements.append({
            "schema": "modify_requirement.v1",
            "requirement_id": _requirement_id(uid, cell),
            "target_construct": cell,
            "subject": "chemistry",
            "grade": grade,
            "grade_band": "secondary_9_10",
            "chapter": _chapter(row),
            "hinge_id": uid,
            "unit_id": uid,
            "hinge_title": title,
            "intent": build_intent(statement, _exclusion(row)),
            "accept_neighbour": False,
            "figure_mode": "none",
        })
    return {
        "requirements": requirements,
        "skipped": skipped,
        "zones": zones,
        "unit_admit_counts": {uid: int(by_unit[uid]) for uid in unit_ids},
        "cell_admit_counts": {
            f"{uid}\t{cell}": int(n) for (uid, cell), n in by_cell.items()
        },
        "statements": {row["unit_id"]: _statement(row) for row in kept},
        "laws": {
            row["unit_id"]: unit_bind.slim_unit(row).get("law") or ""
            for row in kept
        },
    }


def same_unit_seed(bank_paths, unit_id: str) -> dict | None:
    """First chemistry-bank item hinged on unit_id, or None. Never borrows another unit."""
    for row in iter_bank_rows(bank_paths or DEFAULT_BANKS):
        if seed_allowed(row, unit_id):
            return row
    return None


def ship_block_reason(
    trail: dict,
    *,
    zone,
    occupied,
    seed_stem: str = "",
    law: str = "",
    statement: str = "",
) -> str | None:
    """None when the trail may be appended. Otherwise a refusal reason.

    Release is MIQG TOP plus a usable stem and answer. noul below 0.50,
    a held construct, and a cell already occupied on the hinge do not
    block release. zone and occupied remain arguments for census callers.
    """
    del zone, occupied
    if not isinstance(trail, dict):
        return "NO_TRAIL"
    if trail.get("status") == "REFUSED" or trail.get("refusal_reason"):
        return str(trail.get("refusal_reason") or trail.get("status") or "REFUSED")
    bind = trail.get("unit_bind") if isinstance(trail.get("unit_bind"), dict) else {}
    uid = bind.get("unit_id")
    if bind.get("reason") != "BOUND" or not uid:
        return str(trail.get("refusal_reason") or bind.get("reason") or "NOT_BOUND")
    miqg = trail.get("miqg") if isinstance(trail.get("miqg"), dict) else {}
    tier = miqg.get("quality_tier") or miqg.get("tier")
    if tier != "TOP":
        return "MIQG_NOT_TOP"
    tag = trail.get("jev_taxonomy") if isinstance(trail.get("jev_taxonomy"), dict) else {}
    if tag.get("schema") != bank_gate.OVERLAY_SCHEMA:
        return "OVERLAY_SCHEMA"
    item = trail.get("item") if isinstance(trail.get("item"), dict) else {}
    stem = str(item.get("stem") or "").strip()
    if not stem:
        return "BLANK_STEM"
    if seed_stem and stem == str(seed_stem).strip():
        return "SEED_STEM"
    kind = (item.get("answer") or {}).get("kind") if isinstance(item.get("answer"), dict) else None
    if kind not in ANSWER_KINDS:
        return "ANSWER_KIND"
    if law and unit_bind.procedure_leaked(stem, law):
        return "LAW_COPIED"
    if statement and unit_bind.procedure_leaked(stem, statement):
        return "STATEMENT_COPIED"
    req = trail.get("requirement") if isinstance(trail.get("requirement"), dict) else {}
    if req.get("unit_id") and req.get("unit_id") != uid:
        return "UNIT_MISMATCH"
    if req.get("hinge_id") and req.get("hinge_id") != uid:
        return "HINGE_MISMATCH"
    return None


def row_from_shipped_trail(
    trail: dict,
    *,
    zone,
    occupied,
    seed_stem: str = "",
    law: str = "",
    statement: str = "",
) -> dict | None:
    if ship_block_reason(
        trail,
        zone=zone,
        occupied=occupied,
        seed_stem=seed_stem,
        law=law,
        statement=statement,
    ):
        return None
    row = bank_gate.bank_row_from_trail(trail, source=CHEM_SOURCE)
    if row is None:
        return None
    uid = trail["unit_bind"]["unit_id"]
    grade = int((trail.get("requirement") or {})["grade"])
    row["subject"] = "chemistry"
    row["grade_band"] = "secondary_9_10"
    row["grade"] = grade
    row["design"]["hinge_id"] = uid
    row["design"]["source"] = CHEM_SOURCE
    row["jev_taxonomy"]["hinge_id"] = uid
    row["jev_taxonomy"]["subject"] = row["jev_taxonomy"].get("subject") or "chemistry"
    return row


def append_chemistry_row(root: Path, row: dict) -> bool:
    """Append one gated row to secondary chemistry and refresh the manifest."""
    path = Path(root) / "data" / "questions" / "secondary_9_10" / "chemistry.jsonl"
    if not bank_gate.append_eligible_row(path, row):
        return False
    bank_gate.sync_manifest(Path(root))
    return True


def coverage_snapshot(schedule: dict) -> dict:
    """Admitted counts on the secondary unit set, plus empty-zone skips."""
    by_unit = dict(schedule.get("unit_admit_counts") or {})
    by_construct: Counter = Counter()
    for key, count in (schedule.get("cell_admit_counts") or {}).items():
        cell = str(key).split("\t", 1)[-1]
        by_construct[cell] += int(count)
    return {
        "by_unit": by_unit,
        "by_construct": dict(by_construct),
        "skipped_empty_zone": [row["unit_id"] for row in schedule.get("skipped") or []],
    }
