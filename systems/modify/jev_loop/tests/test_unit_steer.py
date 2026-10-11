#!/usr/bin/env python3
"""Unit binding stops an illegal aim, and G18 keeps a zone cell."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import run as tmint  # noqa: E402
import unit_bind  # noqa: E402


def _unit(uid, node, cells, grade=7):
    return {
        "unit_id": uid,
        "node": node,
        "grade": grade,
        "decision": "Decide when one oscillation is complete.",
        "law": "One oscillation is completed when the bob returns to the mean position after both extremes.",
        "boundaries": ["Count from the mean position."],
        "zone": set(cells),
        "mx": "The learner counts a swing to one side as a full oscillation.",
        "anti_narration": "Do not print the count rule.",
    }


class UnitBindTests(unittest.TestCase):
    def test_coarse_hinge_picks_unit_that_allows_the_aim(self):
        a = _unit("science/grade_07/ch_08/H003", "S4/H-MOTION", ["U.Co.2"])
        b = _unit("science/grade_07/ch_08/H004", "S4/H-MOTION", ["An.Pr.3", "U.Co.2"], grade=7)
        tables = ({}, {"S4/H-MOTION": [a, b]})
        unit, reason = unit_bind.bind_requirement(
            {"subject": "science", "grade": 7, "hinge_id": "S4/H-MOTION", "target_construct": "An.Pr.3"},
            tables=tables,
        )
        self.assertEqual(reason, "BOUND")
        self.assertEqual(unit["unit_id"], b["unit_id"])

    def test_aim_outside_every_unit_stops(self):
        a = _unit("science/grade_07/ch_08/H003", "S4/H-MOTION", ["U.Co.2"])
        tables = ({}, {"S4/H-MOTION": [a]})
        unit, reason = unit_bind.bind_requirement(
            {"subject": "science", "grade": 7, "hinge_id": "S4/H-MOTION", "target_construct": "Cr.Me.4"},
            tables=tables,
        )
        self.assertIsNone(unit)
        self.assertEqual(reason, "AIM_NOT_IN_ZONE")

    def test_empty_decision_hinge_uses_the_unit_statement(self):
        slim = unit_bind.slim_unit({
            "unit_id": "ICSE:52.10.2.b",
            "decision_hinge": "",
            "statement": "Draw electron dot structures of covalent molecules and distinguish polar from non-polar.",
            "jev_taxonomy_zone": {"admitted": ["An.Co.3"]},
        })
        self.assertIn("electron dot structures", slim["decision"])
        kept = unit_bind.slim_unit({
            "unit_id": "science/grade_09/ch_08/H001",
            "decision_hinge": "Decide when an indivisible-particle model is an early idea.",
            "statement": "A different sentence that must not replace the hinge.",
            "jev_taxonomy_zone": {"admitted": ["An.Co.3"]},
        })
        self.assertTrue(kept["decision"].startswith("Decide when an indivisible-particle model"))

    def test_procedure_copy_is_detected(self):
        law = "One oscillation is completed when the bob returns to the mean position after both extremes."
        stem = "One oscillation is completed when the bob returns to the mean position after both extremes. Which claim is correct?"
        self.assertTrue(unit_bind.procedure_leaked(stem, law))
        self.assertFalse(unit_bind.procedure_leaked("A bob is released from one side. Which count is one oscillation?", law))


class G18ZoneTests(unittest.TestCase):
    def _tag(self, cid, admitted=True):
        return {"admitted": admitted, "construct_id": cid, "unresolved_coord": cid}

    def test_admitted_zone_cell_is_kept_when_aim_misses(self):
        req = {"target_construct": "An.Pr.3"}
        out = tmint.g18(req, {}, {"quality_tier": "TOP"}, self._tag("U.Co.2"), zone={"An.Pr.3", "U.Co.2"})
        self.assertEqual(out["status"], "PASS_ZONE")
        self.assertTrue(out["aim_missed"])
        self.assertEqual(out["admitted_as"], "U.Co.2")

    def test_cell_outside_zone_is_not_stored(self):
        req = {"target_construct": "An.Pr.3", "accept_neighbour": True}
        out = tmint.g18(
            req,
            {"likely_collapse": "U.Co.2"},
            {"quality_tier": "TOP"},
            self._tag("R.Fa.1"),
            zone={"An.Pr.3", "U.Co.2"},
        )
        self.assertEqual(out["status"], "CONSTRUCT_HOLD")
        self.assertEqual(out["reason"], "CELL_OUTSIDE_ZONE")
        self.assertFalse(out["retry_same_prompt"])

    def test_unadmitted_does_not_ask_for_the_same_prompt(self):
        req = {"target_construct": "An.Pr.3"}
        out = tmint.g18(req, {}, {"quality_tier": "TOP"}, {"admitted": False, "unresolved_coord": "An.Co.2"}, zone={"An.Pr.3"})
        self.assertEqual(out["reason"], "JEV_NOT_ADMITTED")
        self.assertFalse(out["retry_same_prompt"])

    def test_writer_prompt_carries_the_unit_constraint(self):
        unit = _unit("science/grade_07/ch_08/H004", "S4/H-MOTION", ["An.Pr.3"])
        prompt = tmint.writer_prompt(
            {"target_construct": "An.Pr.3", "grade": 7, "subject": "science", "hinge_id": "S4/H-MOTION"},
            {"recommended_form": "worked_response", "proceed": "proceed_structured"},
            "structured_parts",
            {"construct_id": "An.Pr.3", "coordinate_display": "x", "definition": "d", "evidence_mode": "either"},
            unit,
        )
        self.assertIn("do not copy this into the stem", prompt)
        self.assertNotIn("Mix-up line (teacher-side)", prompt)
        self.assertIn("Do not state the relation, the formula, or the steps", prompt)
        self.assertIn(unit["unit_id"], prompt)

    def test_hinge_sentence_is_not_printed_twice(self):
        unit = _unit("science/grade_07/ch_08/H004", "S4/H-MOTION", ["An.Pr.3"])
        prompt = tmint.writer_prompt(
            {
                "target_construct": "An.Pr.3",
                "grade": 7,
                "subject": "science",
                "hinge_id": unit["unit_id"],
                "hinge_title": unit["decision"],
                "intent": "Unit statement: " + unit["decision"] + " Out of scope: no clocks.",
            },
            {"recommended_form": "worked_response", "proceed": "proceed_structured"},
            "structured_parts",
            {"construct_id": "An.Pr.3", "coordinate_display": "x", "definition": "d", "evidence_mode": "either"},
            unit,
        )
        self.assertEqual(prompt.count(unit["decision"]), 1)
        self.assertIn("Out of scope: no clocks.", prompt)

    def test_higher_cell_rotates_two_mixup_lines(self):
        unit = _unit("science/grade_07/ch_08/H004", "S4/H-MOTION", ["An.Co.3"])
        unit["mx_lines"] = ["counts one side only", "starts at an extreme", "ignores the return"]
        seen = set()
        for i in range(12):
            picked = tuple(tmint.select_mx(unit, {
                "requirement_id": f"ms-{i}",
                "target_construct": "An.Co.3",
                "hinge_id": unit["unit_id"],
            }))
            self.assertEqual(len(picked), 2)
            seen.add(picked)
        self.assertGreater(len(seen), 1)
        low = tmint.select_mx(unit, {
            "requirement_id": "ms-0",
            "target_construct": "U.Co.2",
            "hinge_id": unit["unit_id"],
        })
        self.assertEqual(len(low), 1)

    def test_mixup_line_drops_the_hinge_tail(self):
        line = unit_bind._mx_text({
            "canonical_wrong_output": (
                "The learner names the acid and stops"
                " — on the item about Decide whether a pattern claim has both a regularity."
            ),
        })
        self.assertEqual(line, "The learner names the acid and stops")

    def test_format_menu_is_not_locked_to_four_option_mcq(self):
        unit = _unit("science/grade_07/ch_08/H004", "S4/H-MOTION", ["An.Co.3"])
        prompt = tmint.writer_prompt(
            {
                "target_construct": "An.Co.3",
                "grade": 7,
                "subject": "science",
                "hinge_id": unit["unit_id"],
                "grade_band": "middle_6_8",
            },
            {"recommended_form": "error_analysis_mcq", "proceed": "proceed_mcq"},
            "single_mcq",
            {"construct_id": "An.Co.3", "coordinate_display": "x", "definition": "d", "evidence_mode": "either"},
            unit,
        )
        self.assertIn("one_or_more", prompt)
        self.assertIn("three_statement", prompt)
        self.assertIn("not a lock", prompt)
        self.assertNotIn("MUST be single_mcq", prompt)
        self.assertNotIn("if the cell is Ap.Pr.3", prompt)


if __name__ == "__main__":
    unittest.main()
