#!/usr/bin/env python3
"""Secondary chemistry first pass: real map, real banks, no JEV calls."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import catalog  # noqa: E402
import chem_schedule  # noqa: E402
import run as tmint  # noqa: E402

MAP_PATH = ROOT / "data" / "maps" / "jev" / "CHEMISTRY_MAP_COMBINED_JEV.json"
BANKS = (
    ROOT / "data" / "questions" / "secondary_9_10" / "chemistry.jsonl",
    ROOT / "data" / "questions" / "senior_11_12" / "chemistry.jsonl",
)
PHYSICS_BANK = ROOT / "data" / "questions" / "secondary_9_10" / "physics.jsonl"

SYLLABI = {
    "NCERT_SECONDARY",
    "CISCE_ICSE",
    "CAMBRIDGE_IGCSE_CORE",
    "CAMBRIDGE_IGCSE_SUPPLEMENT",
}
GRADE_BANDS = {"SECONDARY", "CORE", "SUPPLEMENT"}
HIGH_PROCESS = {"An", "Ev", "Ap"}
LOW_PROCESS = {"R", "U"}


def _dok(cell: str) -> int:
    tail = str(cell).rsplit(".", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def _rows(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def _zone(row: dict) -> list[str]:
    admitted = ((row.get("jev_taxonomy_zone") or {}).get("admitted")) or []
    out = []
    for cell in admitted:
        if isinstance(cell, str) and cell and cell not in out:
            out.append(cell)
    return out


class FirstPassScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schedule = chem_schedule.first_pass(MAP_PATH, BANKS)
        doc = json.loads(MAP_PATH.read_text(encoding="utf-8"))
        cls.by_id = {}
        for row in doc.get("statements") or []:
            if (
                row.get("syllabus") in SYLLABI
                and row.get("grade_band") in GRADE_BANDS
                and row.get("unit_id")
            ):
                cls.by_id[row["unit_id"]] = row
        cls.reqs = cls.schedule["requirements"]
        cls.req_ids = [req["unit_id"] for req in cls.reqs]

    def test_constants_match_the_secondary_slice(self):
        self.assertEqual(set(chem_schedule.SECONDARY_SYLLABI), SYLLABI)
        self.assertEqual(set(chem_schedule.SECONDARY_GRADE_BANDS), GRADE_BANDS)

    def test_first_pass_covers_each_nonempty_secondary_unit_once(self):
        nonempty = {uid for uid, row in self.by_id.items() if _zone(row)}
        empty = sorted(uid for uid, row in self.by_id.items() if not _zone(row))
        self.assertEqual(len(self.reqs), len(nonempty))
        self.assertEqual(set(self.req_ids), nonempty)
        self.assertEqual(len(self.req_ids), len(set(self.req_ids)))
        skipped = [row["unit_id"] for row in self.schedule["skipped"]]
        self.assertEqual(sorted(skipped), empty)
        self.assertTrue(all(row["reason"] == "EMPTY_ZONE" for row in self.schedule["skipped"]))
        senior = [
            uid for uid in self.req_ids
            if "/grade_11/" in uid or "/grade_12/" in uid or "/grade_13/" in uid or uid.startswith("AS:") or uid.startswith("AL:")
        ]
        self.assertEqual(senior, [])
        print("OBS first pass contains each non-empty-zone secondary unit once")
        print("OBS empty-zone units are skipped: " + ",".join(empty))
        print("OBS senior-secondary AS and A-level units are not in the schedule")

    def test_zero_coverage_precedes_a_large_admitted_count(self):
        counts = self.schedule["unit_admit_counts"]
        order = [counts[uid] for uid in self.req_ids]
        self.assertEqual(order, sorted(order))
        large_uid = max(self.req_ids, key=lambda uid: (counts[uid], uid))
        large_count = counts[large_uid]
        large_at = self.req_ids.index(large_uid)
        self.assertGreaterEqual(large_count, 100)
        zero_ids = [uid for uid in self.req_ids if counts[uid] == 0]
        self.assertTrue(zero_ids)
        self.assertTrue(all(self.req_ids.index(uid) < large_at for uid in zero_ids))
        icse_zero = [
            uid for uid, row in self.by_id.items()
            if row.get("syllabus") == "CISCE_ICSE" and counts.get(uid, 0) == 0 and uid in self.req_ids
        ]
        self.assertTrue(icse_zero)
        self.assertTrue(all(self.req_ids.index(uid) < large_at for uid in icse_zero))
        print(
            "OBS zero-count units including every currently uncovered CISCE_ICSE unit "
            "precede a unit that already has a large admitted count "
            f"({large_uid} count={large_count}, icse_uncovered={len(icse_zero)}, zeros={len(zero_ids)})"
        )

    def test_every_requested_coordinate_is_inside_the_zone(self):
        cell_counts = Counter()
        for key, count in self.schedule["cell_admit_counts"].items():
            uid, cell = key.split("\t", 1)
            cell_counts[(uid, cell)] = count
        for req in self.reqs:
            uid = req["unit_id"]
            zone = _zone(self.by_id[uid])
            target = req["target_construct"]
            self.assertIn(target, zone)
            self.assertEqual(req["hinge_id"], uid)
            self.assertEqual(req["subject"], "chemistry")
            self.assertEqual(req["grade_band"], "secondary_9_10")
            self.assertIn(req["grade"], (9, 10))
            self.assertIsInstance(req["grade"], int)
            self.assertFalse(req["accept_neighbour"])
            self.assertLessEqual(len(req["intent"]), 1000)
            self.assertNotIn("JEE style", req["intent"])
            self.assertIn("non-routine", req["intent"])
            occ = cell_counts[(uid, target)]
            self.assertTrue(all(cell_counts[(uid, cell)] >= occ for cell in zone))
            peers = [cell for cell in zone if cell_counts[(uid, cell)] == occ]
            self.assertTrue(all(_dok(cell) <= _dok(target) for cell in peers))
            top = [cell for cell in peers if _dok(cell) == _dok(target)]
            if target.split(".", 1)[0] in LOW_PROCESS:
                self.assertFalse(any(cell.split(".", 1)[0] in HIGH_PROCESS for cell in top))
            if self.schedule["unit_admit_counts"][uid] == 0:
                self.assertEqual(_dok(target), max(_dok(cell) for cell in zone))
        print("OBS every requested coordinate is in that unit zone")
        print("OBS on a zero-admit unit the requested cell is a maximum-DoK cell in the zone")

    def test_foreign_hinge_is_rejected_as_a_seed(self):
        target = self.req_ids[0]
        foreign = {
            "subject": "chemistry",
            "jev_taxonomy": {"hinge_id": "science/grade_11/chem_ch_101/H016"},
        }
        self.assertFalse(chem_schedule.seed_allowed(foreign, target))
        self.assertFalse(
            chem_schedule.seed_allowed(
                {"subject": "physics", "jev_taxonomy": {"hinge_id": target}},
                target,
            )
        )
        physics = next(_rows(PHYSICS_BANK))
        self.assertNotEqual(str(physics.get("subject") or "").lower(), "chemistry")
        self.assertFalse(chem_schedule.seed_allowed(physics, target))
        matched = None
        mismatched = None
        for path in BANKS:
            for row in _rows(path):
                hinge = (row.get("jev_taxonomy") or {}).get("hinge_id")
                if matched is None and hinge in self.schedule["zones"]:
                    matched = row
                if mismatched is None and hinge and hinge not in self.schedule["zones"]:
                    mismatched = row
                if matched and mismatched:
                    break
            if matched and mismatched:
                break
        self.assertIsNotNone(matched)
        self.assertIsNotNone(mismatched)
        same = (matched.get("jev_taxonomy") or {})["hinge_id"]
        self.assertTrue(chem_schedule.seed_allowed(matched, same))
        self.assertFalse(chem_schedule.seed_allowed(matched, target if target != same else self.req_ids[1]))
        self.assertFalse(chem_schedule.seed_allowed(mismatched, target))
        borrowed = chem_schedule.same_unit_seed(BANKS, "not-a-unit")
        self.assertIsNone(borrowed)
        print("OBS a foreign hinge_id is rejected as a seed")
        print("OBS a same-unit chemistry-bank hinge is accepted as a seed")


def _trail(
    *,
    g18="PASS",
    tier="TOP",
    noul=0.62,
    construct="An.Co.3",
    stem="Two samples of the same salt give different gas tests. Which claim follows from the colours?",
    kind="single_letter",
    admitted=True,
    status="OK",
    refusal=None,
    schema="ttwin.jev_taxonomy.v1",
):
    trail = {
        "status": status,
        "requirement": {
            "schema": "modify_requirement.v1",
            "requirement_id": "chem-sec-test-AnCo3",
            "target_construct": "An.Co.3",
            "subject": "chemistry",
            "grade": 10,
            "grade_band": "secondary_9_10",
            "hinge_id": "ICSE:52.10.1.ii",
            "unit_id": "ICSE:52.10.1.ii",
        },
        "unit_bind": {"reason": "BOUND", "unit_id": "ICSE:52.10.1.ii"},
        "plan": {"recommended_form": "claim_evidence_mcq"},
        "g18": {"status": g18},
        "miqg": {"quality_tier": tier, "protocol": "MIQG-v1.0-rc9-CAL-KNGOOD", "decisive_reason": "KNOWN_GOOD_ENVELOPE"},
        "jev_taxonomy": {
            "schema": schema,
            "admitted": admitted,
            "construct_id": construct,
            "noul": noul,
            "hinge_id": "ICSE:52.10.1.ii",
        },
        "item": {
            "schema": "modify_result.v1",
            "status": "OK",
            "item_type": "single_mcq",
            "stem": stem,
            "options": [{"id": "A", "text": "Claim A."}, {"id": "B", "text": "Claim B."}],
            "answer": {"kind": kind, "letter": "B"},
            "teacher": {"proposed_key_status": "UNVERIFIED", "variation_applied": "V3"},
        },
    }
    if refusal:
        trail["refusal_reason"] = refusal
    return trail


class ShipGateTests(unittest.TestCase):
    ZONE = ["An.Co.3", "U.Co.2", "R.Co.1"]

    def test_pass_zone_row_uses_chemistry_provenance_and_integer_grade(self):
        trail = _trail(g18="PASS_ZONE", construct="U.Co.2")
        row = chem_schedule.row_from_shipped_trail(trail, zone=self.ZONE, occupied=set())
        self.assertIsNotNone(row)
        self.assertEqual(row["grade"], 10)
        self.assertIsInstance(row["grade"], int)
        self.assertEqual(row["grade_band"], "secondary_9_10")
        self.assertEqual(row["subject"], "chemistry")
        self.assertEqual(row["design"]["source"], chem_schedule.CHEM_SOURCE)
        self.assertNotEqual(row["design"]["source"], "t-mint-middle-6-8-fill")
        self.assertEqual(row["design"]["hinge_id"], "ICSE:52.10.1.ii")
        self.assertEqual(row["jev_taxonomy"]["hinge_id"], "ICSE:52.10.1.ii")
        bare = __import__("bank_gate").bank_row_from_trail(trail)
        self.assertEqual(bare["design"]["source"], "t-mint-middle-6-8-fill")

    def test_top_releases_below_noul_and_outside_the_zone(self):
        for trail in (
            _trail(g18="CONSTRUCT_HOLD"),
            _trail(g18="HOLD"),
            _trail(g18="PASS_NEIGHBOUR"),
            _trail(noul=0.49),
            _trail(admitted=False),
            _trail(construct="R.Fa.1"),
            _trail(),
        ):
            self.assertIsNotNone(
                chem_schedule.row_from_shipped_trail(
                    trail,
                    zone=self.ZONE,
                    occupied={("ICSE:52.10.1.ii", "An.Co.3")},
                )
            )
        self.assertIsNone(chem_schedule.row_from_shipped_trail(_trail(tier="MEDIUM"), zone=self.ZONE, occupied=set()))
        self.assertIsNone(chem_schedule.row_from_shipped_trail(_trail(tier="LOW"), zone=self.ZONE, occupied=set()))
        self.assertEqual(
            chem_schedule.ship_block_reason(_trail(stem=""), zone=self.ZONE, occupied=set()),
            "BLANK_STEM",
        )
        self.assertEqual(
            chem_schedule.ship_block_reason(_trail(kind="rubric"), zone=self.ZONE, occupied=set()),
            "ANSWER_KIND",
        )
        stem = _trail()["item"]["stem"]
        self.assertEqual(
            chem_schedule.ship_block_reason(_trail(), zone=self.ZONE, occupied=set(), seed_stem=stem),
            "SEED_STEM",
        )
        law = "copper displaces silver from a silver nitrate solution when the coil is dipped"
        copied = "Copper displaces silver from a silver nitrate solution when the coil is dipped. Which mass remains?"
        self.assertEqual(
            chem_schedule.ship_block_reason(_trail(stem=copied), zone=self.ZONE, occupied=set(), law=law),
            "LAW_COPIED",
        )
        statement = "explain periodicity on the basis of atomic number nuclear charge and shells studying the elements"
        copied_statement = (
            "Explain periodicity on the basis of atomic number nuclear charge and shells studying the elements. "
            "Which claim follows?"
        )
        self.assertEqual(
            chem_schedule.ship_block_reason(
                _trail(stem=copied_statement),
                zone=self.ZONE,
                occupied=set(),
                statement=statement,
            ),
            "STATEMENT_COPIED",
        )
        refused = _trail(status="REFUSED", g18="CONSTRUCT_HOLD", refusal="T-PLAN abandon_cell for An.Co.3")
        self.assertIn("abandon_cell", chem_schedule.ship_block_reason(refused, zone=self.ZONE, occupied=set()))


class PlannerBriefTests(unittest.TestCase):
    def test_secondary_plan_keeps_an_honest_target(self):
        dictionary = {
            "constructs": {},
            "validity_map": {"LIVE": [], "FRAGILE": [], "IMPOSSIBLE": [], "DEGENERATE": {}},
            "profiles": {},
        }
        unit = {
            "unit_id": "ICSE:52.10.2.c",
            "decision": "Explain coordinate bonding by the lone pair effect.",
            "law": "",
            "boundaries": [],
            "zone": {"An.Co.3"},
            "mx": "",
        }
        secondary = tmint.plan_state(
            {
                "grade_band": "secondary_9_10",
                "subject": "chemistry",
                "grade": 10,
                "hinge_id": unit["unit_id"],
                "target_construct": "An.Co.3",
                "intent": "non-routine",
            },
            dictionary,
            unit,
        )
        middle = tmint.plan_state(
            {
                "grade_band": "middle_6_8",
                "subject": "science",
                "grade": 7,
                "hinge_id": "S4/H-MOTION",
                "target_construct": "An.Pr.3",
                "intent": "non-routine",
            },
            dictionary,
            unit,
        )
        self.assertIn("Do not abandon when the honest cell is the target itself", secondary["task"])
        self.assertNotIn("Do not abandon when the honest cell is the target itself", middle["task"])
        secondary_prompt = tmint.writer_prompt(
            {
                "grade_band": "secondary_9_10",
                "grade": 10,
                "subject": "chemistry",
                "hinge_id": "ICSE:52.10.3.i",
                "intent": "non-routine",
            },
            {"recommended_form": "claim_evidence_mcq", "proceed": "proceed_mcq"},
            "single_mcq",
            {"construct_id": "An.Co.3", "coordinate_display": "x", "definition": "d", "evidence_mode": "either"},
            unit,
        )
        self.assertIn("one decision only", secondary_prompt)
        middle_prompt = tmint.writer_prompt(
            {
                "grade_band": "middle_6_8",
                "grade": 7,
                "subject": "science",
                "hinge_id": "S4/H-MOTION",
                "intent": "non-routine",
            },
            {"recommended_form": "worked_response", "proceed": "proceed_structured"},
            "structured_parts",
            {"construct_id": "An.Pr.3", "coordinate_display": "x", "definition": "d", "evidence_mode": "either"},
            unit,
        )
        self.assertNotIn("one decision only", middle_prompt)

    def test_grok_writer_request_carries_reasoning_effort(self):
        import io
        import os
        import urllib.request

        captured = {}

        class _Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_open(req, timeout=None):
            captured["url"] = req.full_url
            captured["timeout"] = timeout
            captured["body"] = json.loads(req.data.decode("utf-8"))
            raw = json.dumps({
                "choices": [{
                    "message": {"content": '{"status":"OK","item_type":"single_mcq","stem":"A salt does not conduct until it melts. Which claim fits?","options":[{"id":"A","text":"Ions are locked in the solid."}],"answer":{"kind":"single_letter","letter":"A"}}'},
                    "finish_reason": "stop",
                }]
            }).encode("utf-8")
            return _Resp(raw)

        keys = (
            "TTWIN_WRITER_KEY",
            "TTWIN_WRITER_MODEL",
            "TTWIN_WRITER_URL",
            "TTWIN_WRITER_REASONING_EFFORT",
            "TTWIN_WRITER_MAX_TOKENS",
            "TTWIN_WRITER_TIMEOUT",
        )
        saved = {key: os.environ.get(key) for key in keys}
        os.environ["TTWIN_WRITER_KEY"] = "test-key"
        # Unset-env law: x.ai URL, grok-4.7, reasoning_effort xhigh (Grok slot).
        for key in (
            "TTWIN_WRITER_MODEL",
            "TTWIN_WRITER_URL",
            "TTWIN_WRITER_REASONING_EFFORT",
            "TTWIN_WRITER_MAX_TOKENS",
            "TTWIN_WRITER_TIMEOUT",
        ):
            os.environ.pop(key, None)
        original = urllib.request.urlopen
        urllib.request.urlopen = fake_open
        try:
            item = tmint.call_writer("Write one item.")
        finally:
            urllib.request.urlopen = original
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual(captured["url"], "https://api.x.ai/v1/chat/completions")
        self.assertEqual(captured["body"]["model"], "grok-4.7")
        self.assertEqual(captured["body"]["reasoning_effort"], "xhigh")
        self.assertGreaterEqual(captured["timeout"], 600)
        self.assertEqual(item.get("item_type"), "single_mcq")
        self.assertTrue(str(item.get("stem") or "").strip())

    def test_secondary_phrase_is_not_the_middle_school_default(self):
        secondary = catalog.design_questions("secondary_9_10")
        middle = catalog.design_questions(None)
        text = secondary["viable_as_mcq"]["instructions"]
        self.assertIn("secondary sitting item", text)
        self.assertNotIn("middle-school", text)
        self.assertNotIn("4-option MCQ", text)
        self.assertIn("middle-school sitting item", middle["viable_as_mcq"]["instructions"])

    def test_mint_sends_the_secondary_brief_to_t_plan(self):
        schedule = FirstPassScheduleTests.schedule if hasattr(FirstPassScheduleTests, "schedule") else chem_schedule.first_pass(MAP_PATH, BANKS)
        req = schedule["requirements"][0]
        seen = {}

        def fake_key():
            return "sk_test"

        def fake_jev(key, state, questions):
            seen["state"] = state
            seen["questions"] = questions
            return {
                "answers": {
                    "viable_as_mcq": 0.2,
                    "recommended_form": "claim_evidence_mcq",
                    "likely_collapse": "U.Co.2",
                    "proceed": "abandon_cell",
                }
            }

        original_key = tmint.load_jev_key
        original_jev = tmint.jev_call
        tmint.load_jev_key = fake_key
        tmint.jev_call = fake_jev
        dictionary = {
            "constructs": {},
            "validity_map": {"LIVE": [], "FRAGILE": [], "IMPOSSIBLE": [], "DEGENERATE": {}},
            "profiles": {},
        }
        try:
            with tempfile.TemporaryDirectory() as tmp:
                trail = tmint.mint(req, dictionary, Path(tmp), None)
        finally:
            tmint.load_jev_key = original_key
            tmint.jev_call = original_jev
        self.assertEqual(trail["unit_bind"]["reason"], "BOUND")
        self.assertEqual(trail["unit_bind"]["unit_id"], req["unit_id"])
        self.assertIn("abandon_cell", trail.get("refusal_reason") or "")
        self.assertEqual(seen["state"]["grade_band"], "secondary_9_10")
        brief = seen["questions"]["viable_as_mcq"]["instructions"]
        self.assertIn("secondary sitting item", brief)
        self.assertNotIn("middle-school", brief)
        print("OBS planner brief for secondary_9_10 is a secondary sitting item")


if __name__ == "__main__":
    unittest.main()
