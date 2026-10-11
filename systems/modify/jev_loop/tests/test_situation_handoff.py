#!/usr/bin/env python3
"""T-MINT stops at the situation. T-MOD receives that situation."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import run as tmint  # noqa: E402
import situation  # noqa: E402


class SituationStageTests(unittest.TestCase):
    def test_wrong_options_are_removed_and_the_expected_answer_stays(self):
        item = {
            "item_type": "single_mcq",
            "stem": "A spring already holding 2 N is loaded with another 2 N. What is the extension now?",
            "expected_answer": "8 cm",
            "answer_mechanism": "Extension is proportional to load, so the added load adds the same extension.",
            "options": [
                {"id": "A", "text": "4 cm"},
                {"id": "B", "text": "8 cm"},
                {"id": "C", "text": "16 cm"},
            ],
            "answer": {"kind": "single_letter", "letter": "B"},
        }
        error = situation.stage_item(item, {})
        self.assertEqual(error, "")
        self.assertEqual(item["options"], [{"id": "B", "text": "8 cm"}])
        self.assertTrue(item["teacher"]["answer_mechanism"].startswith("Extension"))
        self.assertNotIn("mx_option_map", item)

    def test_an_occupied_scene_is_refused_and_a_user_scene_is_kept(self):
        stem = "A leaf has one thick middle vein and a net of smaller veins on both sides."
        item = {"item_type": "single_mcq", "stem": stem, "expected_answer": "reticulate"}
        occupied = (
            "A leaf has one thick middle vein and a net of smaller veins on both sides of the midrib."
        )
        self.assertTrue(situation.repeats_occupied(stem, [occupied]))
        self.assertIn("already used", situation.stage_item(item, {"occupied_situations": [occupied]}))
        fresh = {
            "item_type": "single_mcq",
            "stem": "The same leaf is viewed from the underside after the midrib is marked.",
            "expected_answer": "reticulate",
        }
        self.assertEqual(situation.stage_item(fresh, {"occupied_situations": [occupied]}), "")
        supplied = {
            "item_type": "single_mcq",
            "stem": "In this titration the weak acid is added until the indicator changes.",
            "expected_answer": "the end point",
        }
        self.assertEqual(
            situation.stage_item(supplied, {"user_situation": "titration of a weak acid until the indicator changes"}),
            "",
        )
        drifted = {
            "item_type": "single_mcq",
            "stem": "A metal rod is heated at one end and the far end stays cool.",
            "expected_answer": "conduction",
        }
        self.assertIn(
            "user input",
            situation.stage_item(drifted, {"user_situation": "titration of a weak acid until the indicator changes"}),
        )

    def test_the_writer_prompt_asks_for_a_situation_and_not_for_distractors(self):
        prompt = tmint.writer_prompt(
            {
                "grade": 8,
                "subject": "physics",
                "hinge_id": "H-SPRING",
                "target_construct": "An.Pr.3",
                "user_situation": "a spring that already holds a load",
                "occupied_situations": ["A different spring is stretched on a bench by a single mass."],
                "companion_hinges": [{"hinge_id": "H-FORCE", "decision": "Force and extension stay proportional."}],
            },
            {"proceed": "proceed_mcq"},
            "single_mcq",
            {"construct_id": "An.Pr.3", "coordinate_display": "x", "definition": "d", "evidence_mode": "either"},
            {"unit_id": "H-SPRING", "decision": "Extension tracks the load.", "law": "Hooke", "boundaries": [], "mx_records": []},
        )
        self.assertIn("does not write wrong options", prompt)
        self.assertIn("answer_mechanism", prompt)
        self.assertIn("a spring that already holds a load", prompt)
        self.assertIn("Do not invent a different scene", prompt)
        self.assertIn("H-FORCE", prompt)
        self.assertNotIn("Return mx_option_map", prompt)
        self.assertNotIn("distractors as", prompt)

    def test_t_mint_is_told_to_choose_the_format(self):
        prompt = tmint.writer_prompt(
            {
                "grade": 7,
                "subject": "science",
                "hinge_id": "science/grade_07/ch_07/H006",
                "target_construct": "An.Co.2",
            },
            {"proceed": "proceed_mcq"},
            "single_mcq",
            {"construct_id": "An.Co.2", "coordinate_display": "x", "definition": "d", "evidence_mode": "either"},
            {"unit_id": "science/grade_07/ch_07/H006", "decision": "Radiation warms a nearby object.", "law": "Radiation", "boundaries": [], "mx_records": []},
        )
        self.assertIn("chooses the item_type", prompt)
        self.assertIn("four options", prompt)
        self.assertIn("bare result", prompt)
        self.assertNotIn("locked to single_mcq", prompt)

    def test_the_handoff_keeps_the_stem_and_the_expected_answer(self):
        item = {
            "item_type": "single_mcq",
            "stem": "Two equal loads hang on one spring.",
            "options": [{"id": "C", "text": "twice the extension"}],
            "answer": {"kind": "single_letter", "letter": "C"},
            "teacher": {"expected_answer": "twice the extension"},
        }
        source = situation.source_for_tmod(
            {"requirement_id": "req-1", "subject": "physics", "grade": 8, "hinge_id": "H-SPRING"},
            item,
        )
        self.assertEqual(source["item"]["stem"], item["stem"])
        self.assertEqual(source["item"]["options"][0]["text"], "twice the extension")
        self.assertEqual(source["jev_taxonomy"]["hinge_id"], "H-SPRING")


if __name__ == "__main__":
    unittest.main()
