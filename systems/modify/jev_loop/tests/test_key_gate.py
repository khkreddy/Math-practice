#!/usr/bin/env python3
"""Independent key gate: proposed key must be the result this stem requires."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import key_gate  # noqa: E402
import situation  # noqa: E402


class KeyGateTests(unittest.TestCase):
    def test_polarity_conflict_is_a_fail(self):
        self.assertFalse(
            key_gate.results_match("The density of the gas decreases.", "The density stays the same.")
        )
        self.assertFalse(key_gate.results_match("pressure increases", "pressure decreases"))
        self.assertTrue(key_gate.results_match("density stays the same", "The density remains unchanged."))
        self.assertTrue(key_gate.results_match("8 cm because load doubled", "8 cm"))

    def test_h011_wrong_generic_heating_rule_is_refused(self):
        item = {
            "stem": (
                "A sealed metal cylinder of fixed volume contains a gas. "
                "The gas is heated so that the pressure inside the cylinder rises. "
                "What happens to the density of the gas?"
            ),
            "teacher": {"expected_answer": "The density of the gas decreases."},
        }

        def writer(_prompt: str) -> dict:
            self.assertNotIn("decreases", _prompt)
            self.assertIn("sealed metal cylinder", _prompt)
            return {"status": "ok", "independent_result": "The density stays the same."}

        report = key_gate.check(item, {"decision": "Predict density from T and P.", "law": "PV=nRT"}, writer, {"grade": 8, "subject": "science"})
        self.assertEqual(report["status"], "REFUSED")
        self.assertIn("not the result this stem requires", report["reason"])

    def test_matching_independent_result_passes(self):
        item = {
            "stem": "A sealed metal cylinder of fixed volume is heated. What happens to the density of the gas?",
            "teacher": {"expected_answer": "The density stays the same."},
        }
        report = key_gate.check(item, {}, lambda _p: {"independent_result": "density remains unchanged"}, None)
        self.assertEqual(report["status"], "PASS")

    def test_missing_independent_result_fails_closed(self):
        item = {"stem": "What is the density?", "teacher": {"expected_answer": "unchanged"}}
        report = key_gate.check(item, {}, lambda _p: {"status": "ok"}, None)
        self.assertEqual(report["status"], "REFUSED")
        self.assertIn("missing", report["reason"])

    def test_writer_error_fails_closed(self):
        item = {"stem": "What is the density?", "teacher": {"expected_answer": "unchanged"}}

        def writer(_prompt: str) -> dict:
            raise RuntimeError("writer down")

        report = key_gate.check(item, {}, writer, None)
        self.assertEqual(report["status"], "REFUSED")
        self.assertIn("writer", report["reason"])

    def test_proposed_key_prefers_the_keyed_option(self):
        item = {
            "stem": "What happens to the density?",
            "options": [
                {"id": "A", "text": "The density of the gas decreases."},
                {"id": "C", "text": "The density stays the same."},
            ],
            "answer": {"letter": "A"},
            "teacher": {"expected_answer": "The density stays the same."},
        }
        self.assertEqual(key_gate.proposed_key(item), "The density of the gas decreases.")

    def test_tmint_prompt_requires_this_stem(self):
        prompt = situation.prompt_block({"grade": 8, "subject": "science"})
        self.assertIn("THIS stem requires", prompt)
        self.assertIn("given condition blocks", prompt)


if __name__ == "__main__":
    unittest.main()
