#!/usr/bin/env python3
"""T-MOD route gate: one bare result when two routes agree. Not fitted to one paper."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import route_derive  # noqa: E402


def _choice_source():
    return {
        "subject": "physics",
        "grade": 8,
        "item": {
            "item_type": "single_mcq",
            "stem": "A spring extends 4 cm under a load of 2 N. The same spring is used again with the load still 2 N. What extension is measured?",
            "options": {
                "A": "8 cm",
                "B": "4 cm",
                "C": "2 cm",
                "D": "16 cm",
            },
            "assessment": {"mcq_key": "B"},
        },
    }


class SameOutputTests(unittest.TestCase):
    def test_two_routes_keep_the_bare_result_and_both_routes(self):
        source = _choice_source()
        draft = {
            "status": "OK",
            "stem": "rewritten stem that must not survive",
            "options": [
                {"id": "B", "text": "6 cm", "role": "key"},
                {
                    "id": "A",
                    "text": "8 cm",
                    "output": "8 cm",
                    "route": "condition_omission",
                    "why": "the load is doubled and the extension is treated as doubled",
                },
                {
                    "id": "D",
                    "text": "4 cm for each extra 2 N, so 8 cm total",
                    "output": "8 cm",
                    "route": "operation_confusion",
                    "why": "the two extensions are added",
                },
                {
                    "id": "C",
                    "text": "2 cm",
                    "output": "2 cm",
                    "route": "relationship_reversal",
                },
            ],
        }
        item, report = route_derive.finish_item(draft, source, "V5")
        texts = {row["id"]: row["text"] for row in item["options"]}
        self.assertEqual(item["stem"], source["item"]["stem"])
        self.assertEqual(texts["B"], "4 cm")
        self.assertEqual(item["answer"]["letter"], "B")
        self.assertNotIn("D", texts)
        self.assertEqual(texts["A"], "8 cm")
        self.assertEqual(texts["C"], "2 cm")
        self.assertEqual(
            item["teacher"]["route_map"]["A"]["routes"],
            ["condition_omission", "operation_confusion"],
        )
        self.assertTrue(any(row["id"] == "D" for row in report["dropped"]))
        self.assertNotIn("for each", " ".join(texts.values()))

    def test_a_step_inside_the_reasoning_is_not_the_result(self):
        kept, dropped = route_derive.collapse_slots([
            {"id": "A", "text": "4 cm", "output": "", "route": "scope_error"},
            {
                "id": "E",
                "text": "the extension for each load is 4 cm, so 8 cm total",
                "output": "",
                "route": "operation_confusion",
            },
        ])
        self.assertEqual(len(kept), 2)
        self.assertEqual(dropped, [])

    def test_nearby_values_stay_distinct(self):
        kept, _dropped = route_derive.collapse_slots([
            {"id": "A", "text": "12 N", "output": "12 N", "route": "operation_confusion"},
            {"id": "C", "text": "120 N", "output": "120 N", "route": "scope_error"},
            {"id": "D", "text": "3 − 2√3", "output": "3 − 2√3", "routes": ["operation_confusion", "relationship_reversal"]},
            {"id": "E", "text": "6 − 4√3", "output": "6 − 4√3", "route": "relationship_reversal"},
        ])
        self.assertEqual({row["text"] for row in kept}, {"12 N", "120 N", "3 − 2√3", "6 − 4√3"})

    def test_equal_outputs_collapse_even_when_the_wording_differs(self):
        kept, dropped = route_derive.collapse_slots([
            {"id": "A", "text": "shifts left", "output": "shifts left", "route": "relationship_reversal"},
            {
                "id": "C",
                "text": "Q is above K, so the system shifts left",
                "output": "shifts left",
                "route": "condition_omission",
            },
        ])
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["text"], "shifts left")
        self.assertEqual(kept[0]["routes"], ["relationship_reversal", "condition_omission"])
        self.assertEqual(len(dropped), 1)

    def test_a_reasoned_option_alone_is_reduced_to_its_output(self):
        kept, dropped = route_derive.collapse_slots([
            {
                "id": "A",
                "text": "the mass doubles, so the rise is 12 degrees",
                "output": "12 degrees",
                "route": "condition_omission",
            },
        ])
        self.assertEqual(kept[0]["text"], "12 degrees")
        self.assertEqual(dropped, [])


class SituationTests(unittest.TestCase):
    def test_a_practical_item_is_rebuilt_from_the_situation(self):
        source = {
            "subject": "biology",
            "grade": 11,
            "item": {
                "item_type": "practical",
                "stem": "A student measures the time for a leaf disc to rise in different concentrations.",
                "parts": [
                    {"id": "a", "prompt": "State the independent variable."},
                    {"id": "b", "prompt": "Calculate the rate."},
                ],
                "answer": {"kind": "part_answers", "part_answers": [{"part_id": "a", "answer": "concentration"}]},
            },
        }
        sit = route_derive.situation_of(source)
        self.assertEqual(sit["mode"], "situation")
        self.assertEqual(sit["item_type"], "structured_parts")
        draft = {
            "status": "OK",
            "stem": "A student measures the time for a leaf disc to rise in different concentrations. The time for each disc is 20 s, so the rate is 40 s.",
            "parts": [
                {"id": "a", "prompt": "State the independent variable."},
                {"id": "b", "prompt": "The time for each disc is 20 s, so the rate is 40 s."},
            ],
            "answer": {
                "kind": "part_answers",
                "part_answers": [
                    {"part_id": "a", "answer": "concentration"},
                    {"part_id": "b", "answer": "1/time"},
                ],
            },
            "teacher": {
                "route_records": [
                    {"route": "operation_confusion", "output": "40 s", "variable": "rate", "text": "40 s"},
                    {
                        "route": "condition_omission",
                        "output": "40 s",
                        "variable": "rate",
                        "text": "The time for each disc is 20 s, so the rate is 40 s.",
                    },
                ],
            },
        }
        item, report = route_derive.finish_item(draft, source, "V5")
        self.assertEqual(item["item_type"], "structured_parts")
        self.assertNotIn("so the rate is 40 s", item["stem"])
        self.assertEqual(len(item["teacher"]["route_records"]), 1)
        self.assertEqual(item["teacher"]["route_records"][0]["output"], "40 s")
        self.assertEqual(
            item["teacher"]["route_records"][0]["routes"],
            ["operation_confusion", "condition_omission"],
        )
        self.assertEqual(len(report["dropped"]), 1)
        prompt = route_derive.prompt_for(sit, {"grade": 11, "subject": "biology", "intent": ""}, "V5")
        self.assertIn("complete question", prompt)
        self.assertIn("variables", prompt)
        self.assertNotIn("mx_id", prompt)
        self.assertNotIn("legal_set", prompt)

    def test_the_choice_prompt_does_not_carry_a_map_or_a_worked_example(self):
        sit = route_derive.situation_of(_choice_source())
        prompt = route_derive.prompt_for(
            sit,
            {"grade": 8, "subject": "physics", "intent": "fix the thin stem"},
            "V5",
        )
        for name in route_derive.ROUTES:
            self.assertIn(name, prompt)
        self.assertIn("same output", prompt)
        self.assertIn("4 cm", prompt)
        self.assertNotIn("legal_set", prompt)
        self.assertNotIn("misconceptions_mx", prompt)
        self.assertNotIn("addqs:", prompt)
        self.assertNotIn("mx_id", prompt)
        self.assertIn("fix the thin stem", prompt)

    def test_a_gapped_letter_is_closed_and_a_key_because_is_stripped(self):
        source = {
            "item": {
                "item_type": "single_mcq",
                "stem": "Dry air is about 78 percent nitrogen. Which gas is the solvent?",
                "options": {"A": "Nitrogen, because it is present in the largest amount in air."},
                "answer": {"kind": "single_letter", "letter": "A"},
            }
        }
        draft = {
            "status": "OK",
            "options": [
                {"id": "A", "text": "Nitrogen, because it is present in the largest amount in air.", "role": "key"},
                {"id": "B", "text": "Oxygen", "route": "mechanism_conflation"},
                {"id": "C", "text": "Reading the chapter and watching the sky answer the same question about how shadows move.", "route": "relationship_reversal"},
                {"id": "D", "text": "Nitrogen", "route": "relationship_reversal"},
            ],
        }
        # Drop C as unrelated in a second item; first item only B and D plus key.
        draft["options"] = [
            {"id": "A", "text": "Nitrogen, because it is present in the largest amount in air.", "role": "key"},
            {"id": "B", "text": "Oxygen", "route": "mechanism_conflation"},
            {"id": "D", "text": "Nitrogen", "route": "relationship_reversal"},
        ]
        item, _report = route_derive.finish_item(draft, source, "V3")
        letters = [row["id"] for row in item["options"]]
        texts = {row["id"]: row["text"] for row in item["options"]}
        self.assertEqual(letters, ["A", "B"])
        self.assertEqual(texts["A"], "Nitrogen")
        self.assertEqual(texts["B"], "Oxygen")
        self.assertEqual(item["answer"]["letter"], "A")
        self.assertNotIn("because", " ".join(texts.values()).lower())

    def test_missing_c_is_relettered(self):
        source = {
            "item": {
                "item_type": "single_mcq",
                "stem": "Which claim does not fit this scene?",
                "options": {"A": "Claim A."},
                "answer": {"kind": "single_letter", "letter": "A"},
            }
        }
        draft = {
            "status": "OK",
            "options": [
                {"id": "A", "text": "Claim A.", "role": "key"},
                {"id": "B", "text": "Claim B.", "route": "scope_error"},
                {"id": "D", "text": "Claim D.", "route": "mechanism_conflation"},
            ],
        }
        item, _report = route_derive.finish_item(draft, source, "V3")
        self.assertEqual([row["id"] for row in item["options"]], ["A", "B", "C"])
        self.assertEqual(item["options"][2]["text"], "Claim D.")

    def test_a_standard_mcq_keeps_two_route_hits_and_three_distractors(self):
        item = {
            "item_type": "single_mcq",
            "stem": "Which gas is the solvent?",
            "options": [
                {"id": "A", "text": "Nitrogen"},
                {"id": "B", "text": "Oxygen"},
                {"id": "C", "text": "Argon"},
                {"id": "D", "text": "Water vapour"},
                {"id": "E", "text": "Carbon dioxide"},
                {"id": "F", "text": "Hydrogen"},
            ],
            "answer": {"kind": "single_letter", "letter": "A"},
            "teacher": {
                "route_map": {
                    "B": {"routes": ["mechanism_conflation", "scope_error"]},
                    "C": {"routes": ["term_substitution"]},
                    "D": {"routes": ["everyday_replacement"]},
                    "E": {"routes": ["surface_feature_capture"]},
                    "F": {"routes": ["condition_omission"]},
                }
            },
        }
        scores = {"C": 0.1, "D": 0.9, "E": 0.2, "F": 0.8}
        finished, report = route_derive.keep_best_distractors(
            item, ranker=lambda rows: scores
        )
        texts = {row["id"]: row["text"] for row in finished["options"]}
        self.assertEqual(len(finished["options"]), 4)
        self.assertEqual(texts["A"], "Nitrogen")
        self.assertIn("Oxygen", texts.values())
        self.assertIn("Water vapour", texts.values())
        self.assertIn("Hydrogen", texts.values())
        self.assertNotIn("Argon", texts.values())
        self.assertEqual(report["dual_kept"], 1)
        self.assertEqual(report["kept"], 3)


if __name__ == "__main__":
    unittest.main()
