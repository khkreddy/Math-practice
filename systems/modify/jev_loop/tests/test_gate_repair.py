#!/usr/bin/env python3
"""Gate explanations stay plain, and only a non-TOP item is repaired."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "miqg"))

import gate_repair  # noqa: E402


class GateRepairTests(unittest.TestCase):
    def test_top_is_admitted_and_the_explanation_says_so(self):
        trail = {
            "status": "OK",
            "miqg": {"quality_tier": "TOP", "release_gate": "PASS", "decisive_reason": "KNOWN_GOOD_ENVELOPE"},
        }
        record = gate_repair.explain_gate(trail)
        self.assertTrue(record["admitted"])
        self.assertIn("Admitted", record["explanation"])
        self.assertIn("TOP", record["explanation"])

    def test_medium_is_rejected_with_the_quoted_failure(self):
        trail = {
            "status": "NOT_CLAIMED",
            "refusal_reason": "MIQG: tier=MEDIUM release_gate=HOLD decisive=MAJOR_PRESENT",
            "miqg": {
                "quality_tier": "MEDIUM",
                "release_gate": "HOLD",
                "decisive_reason": "MAJOR_PRESENT",
                "major_codes": "STEM_CONTEXT_THIN",
                "findings": [{"code": "STEM_CONTEXT_THIN", "quote": "Four jars are on a bench", "loc": "stem"}],
            },
        }
        record = gate_repair.explain_gate(trail, "option B can also be true")
        self.assertFalse(record["admitted"])
        self.assertIn("Rejected", record["explanation"])
        self.assertIn("scene-plus-purpose", record["explanation"])
        self.assertIn("Four jars are on a bench", record["explanation"])
        self.assertIn("option B can also be true", record["explanation"])

    def test_a_top_score_does_not_override_a_harness_rejection(self):
        trail = {
            "status": "REFUSED",
            "refusal_reason": "mx_bind: option D is not on this hinge",
            "miqg": {"quality_tier": "TOP", "release_gate": "PASS", "decisive_reason": "KNOWN_GOOD_ENVELOPE"},
        }
        record = gate_repair.explain_gate(trail)
        self.assertFalse(record["admitted"])
        self.assertIn("does not admit", record["explanation"])
        self.assertNotIn("Release gate PASS, tier TOP, because", record["explanation"])
        trail = {"status": "REFUSED", "refusal_reason": "mx_bind: option E is not on this hinge", "miqg": {}}
        text = gate_repair.repair_instruction(
            trail,
            "option D uses conductivity, which the stem does not state",
            ["science/grade_07/ch_04/H001/MX_scope_error"],
            {"stem": "A soft solid is drawn into wire.", "options": [{"id": "A", "text": "It is a metal."}]},
        )
        self.assertIn("ONE REPAIR PASS", text)
        self.assertNotIn("MX_scope_error", text)
        self.assertIn("same result", text)
        self.assertIn("Do not add a fifth", text)
        self.assertIn("conductivity", text)
        self.assertIn("A soft solid is drawn into wire.", text)


if __name__ == "__main__":
    unittest.main()
