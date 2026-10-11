"""Coverage picker for middle-school science and maths mints.

Pure of bank counts and each unit zone. Does not call JEV or the writer.
A coordinate whose failure count reaches the limit is left out of later picks.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
TTWIN_ROOT = HERE.parents[2]
SCIENCE_MAP = TTWIN_ROOT / "data" / "maps" / "jev" / "sanitized" / "SCIENCE_MAP_G68_AGENT.json"
MATHS_MAP = TTWIN_ROOT / "data" / "maps" / "jev" / "sanitized" / "MATHEMATICS_MAP_AGENT.json"
SCIENCE_BANK = TTWIN_ROOT / "data" / "questions" / "middle_6_8" / "science.jsonl"
MATHS_BANK = TTWIN_ROOT / "data" / "questions" / "middle_6_8" / "maths.jsonl"
SKIP_PATH = HERE / "mint_learning" / "middle_skips.json"

CONSTRUCT_RE = re.compile(r"^(R|U|Ap|An|Ev|Cr)\.(Fa|Co|Pr|Me)\.[1-4]$")
PROCESS_RANK = {"An": 0, "Ev": 1, "Ap": 2, "Cr": 3, "U": 4, "R": 5}
FAIL_LIMIT = 3
SOURCE = "t-mint-middle-uniform"


def skip_key(unit_id: str, cell: str) -> str:
    return f"{unit_id}\t{cell}"


def _dok(cell: str) -> int:
    tail = str(cell).rsplit(".", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def _process(cell: str) -> str:
    return str(cell).split(".", 1)[0]


def zone_cells(row: dict) -> list[str]:
    zone = row.get("jev_taxonomy_zone")
    if not isinstance(zone, dict):
        zone = row.get("zone") if isinstance(row.get("zone"), dict) else {}
    admitted = zone.get("admitted") if isinstance(zone, dict) else None
    if not isinstance(admitted, list):
        return []
    out = []
    seen = set()
    for cell in admitted:
        if isinstance(cell, str) and cell not in seen and CONSTRUCT_RE.match(cell):
            seen.add(cell)
            out.append(cell)
    return out


def _middle_grade(row: dict) -> int | None:
    grade = row.get("grade")
    try:
        g = int(grade)
    except (TypeError, ValueError):
        return None
    if 6 <= g <= 8:
        return g
    return None


def units_from_maps(science_doc: dict, maths_doc: dict) -> list[dict]:
    """Grade 6–8 units that have a non-empty taxonomy zone."""
    out = []
    for subject, doc in (("science", science_doc), ("maths", maths_doc)):
        rows = doc.get("hinges") or doc.get("statements") or doc.get("units") or []
        for row in rows:
            if not isinstance(row, dict) or not row.get("unit_id"):
                continue
            grade = _middle_grade(row)
            if grade is None:
                continue
            cells = zone_cells(row)
            if not cells:
                continue
            decision = row.get("decision_hinge") or row.get("decision") or ""
            out.append({
                "unit_id": row["unit_id"],
                "node": row.get("node") or "",
                "subject": subject,
                "grade": grade,
                "decision": " ".join(str(decision).split()),
                "zone": cells,
            })
    return out


def occupancy(rows: list[dict]) -> tuple[Counter, Counter]:
    """Hinge and (hinge, cell) counts for rows already in the two banks."""
    by_hinge: Counter = Counter()
    by_cell: Counter = Counter()
    for row in rows:
        if not isinstance(row, dict):
            continue
        tag = row.get("jev_taxonomy")
        if not isinstance(tag, dict):
            continue
        hinge = tag.get("hinge_id")
        if not isinstance(hinge, str) or not hinge:
            continue
        by_hinge[hinge] += 1
        cell = tag.get("construct_id") or tag.get("unresolved_coord")
        if isinstance(cell, str) and CONSTRUCT_RE.match(cell):
            by_cell[(hinge, cell)] += 1
    return by_hinge, by_cell


def suppressed_doks(skips: dict, threshold: int = 4) -> set[int]:
    """A DoK level is set aside after that many distinct abandoned cells."""
    counts: dict[int, int] = {}
    for key, val in skips.items():
        if int(val or 0) < 1 or "\t" not in str(key):
            continue
        cell = str(key).split("\t", 1)[1]
        if not CONSTRUCT_RE.match(cell):
            continue
        dok = _dok(cell)
        counts[dok] = counts.get(dok, 0) + 1
    highs = [dok for dok, n in counts.items() if n >= threshold]
    if not highs:
        return set()
    return {max(highs)}


def next_picks(
    units: list[dict],
    by_hinge: Counter,
    by_cell: Counter,
    skips: dict,
    n: int = 1,
    fail_limit: int = FAIL_LIMIT,
) -> list[tuple[str, str]]:
    """Under-covered hinges first, then a higher in-zone cell.

    A cell at or above fail_limit is omitted. Among the rest, a cell that has
    already failed sorts after a cell that has not, so it is not the next pick.
    """
    blocked = suppressed_doks(skips)
    ranked = []
    for unit in units:
        uid = unit["unit_id"]
        hinge_n = int(by_hinge.get(uid, 0))
        for cell in unit.get("zone") or []:
            sk = int(skips.get(skip_key(uid, cell), 0) or 0)
            if sk >= fail_limit or _dok(cell) in blocked:
                continue
            ranked.append((
                hinge_n,
                int(by_cell.get((uid, cell), 0)),
                sk,
                -_dok(cell),
                PROCESS_RANK.get(_process(cell), 9),
                uid,
                cell,
                unit.get("subject") or "",
            ))
    ranked.sort()
    by_subject: dict[str, list] = {}
    for row in ranked:
        by_subject.setdefault(row[7], []).append(row)
    order = [s for s in ("science", "maths") if s in by_subject]
    order += [s for s in by_subject if s not in order]
    picks = []
    seen = set()
    cursors = {s: 0 for s in order}
    while len(picks) < n and order:
        progressed = False
        for subject in order:
            rows = by_subject[subject]
            i = cursors[subject]
            while i < len(rows) and rows[i][5] in seen:
                i += 1
            cursors[subject] = i
            if i >= len(rows):
                continue
            uid, cell = rows[i][5], rows[i][6]
            seen.add(uid)
            cursors[subject] = i + 1
            picks.append((uid, cell))
            progressed = True
            if len(picks) >= n:
                break
        if not progressed:
            break
    return picks


def requirement_for(unit: dict, cell: str, requirement_id: str) -> dict:
    decision = unit.get("decision") or unit["unit_id"]
    return {
        "schema": "modify_requirement.v1",
        "requirement_id": requirement_id,
        "target_construct": cell,
        "subject": unit["subject"],
        "grade": int(unit["grade"]),
        "grade_band": "middle_6_8",
        "hinge_id": unit["unit_id"],
        "unit_id": unit["unit_id"],
        "hinge_title": decision,
        "intent": (
            "Middle-school sitting item on this unit only. "
            "Aim at the named cell. Do not print the method or restate the law. "
            "One decision. A wrong option is a plausible observation."
        ),
        "accept_neighbour": False,
        "figure_mode": "none",
    }


def load_skips(path: Path | None = None) -> dict:
    path = Path(path) if path else SKIP_PATH
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): int(v) for k, v in raw.items() if isinstance(v, int) or str(v).isdigit()}


def save_skips(skips: dict, path: Path | None = None) -> None:
    path = Path(path) if path else SKIP_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(skips, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def note_failure(skips: dict, unit_id: str, cell: str) -> int:
    key = skip_key(unit_id, cell)
    skips[key] = int(skips.get(key, 0) or 0) + 1
    return skips[key]
