#!/usr/bin/env python3
"""Wrong options keep the mx_id the writer cited, taken from the map sentence."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from systems.modify.packet_modify import bind_cited_mx  # noqa: E402


RECORDS = [
    {
        "mx_id": "sci/H1/MX_condition_omission_1",
        "route": "condition_omission",
        "unit_id": "sci/H1",
        "wrong": "Copying steps without a question counts as science.",
        "confused": "Experiments must serve a question.",
        "observable": "Accepts a question-free routine as science.",
    },
    {
        "mx_id": "sci/H1/MX_everyday_replacement_2",
        "route": "everyday_replacement",
        "unit_id": "sci/H1",
        "wrong": "Any careful looking is an experiment.",
        "confused": "Observation is not by itself an experiment.",
        "observable": "Calls watching a plant an experiment.",
    },
]


def _item():
    return {
        "item_type": "single_mcq",
        "stem": "A class copies the steps of a melting-ice activity and writes no question. Which claim fits?",
        "options": [
            {"id": "A", "text": "The activity is not yet science, because no question is being answered."},
            {"id": "B", "text": "The activity is science, because the steps were copied carefully."},
            {"id": "C", "text": "The activity is science, because the class looked carefully."},
        ],
        "answer": {"kind": "single_letter", "letter": "A"},
        "mx_option_map": {
            "B": "sci/H1/MX_condition_omission_1",
            "C": "sci/H1/MX_everyday_replacement_2",
        },
        "worked_solution": {"status": "complete"},
    }


class BindCitedMxTests(unittest.TestCase):
    def test_wrong_options_receive_distinct_map_mx(self):
        item = _item()
        self.assertIsNone(bind_cited_mx(item, RECORDS))
        by_id = {opt["id"]: opt for opt in item["options"]}
        self.assertNotIn("mx_refs", by_id["A"])
        self.assertNotIn("feedback", by_id["A"])
        self.assertEqual(by_id["B"]["mx_refs"][0]["ref"], "sci/H1/MX_condition_omission_1")
        self.assertEqual(by_id["B"]["feedback"]["source"], "misconception")
        self.assertIn("Copying steps without a question", by_id["B"]["feedback"]["learning_state"])
        self.assertIn("question-free routine", by_id["B"]["feedback"]["evidence"])
        self.assertEqual(by_id["C"]["mx_refs"][0]["confusion_type"], "everyday_replacement")

    def test_repeated_or_unknown_mx_is_refused(self):
        item = _item()
        item["mx_option_map"]["C"] = "sci/H1/MX_condition_omission_1"
        err = bind_cited_mx(item, RECORDS)
        self.assertTrue(err and "already bound" in err)
        item = _item()
        item["mx_option_map"]["B"] = "not-on-hinge"
        err = bind_cited_mx(item, RECORDS)
        self.assertTrue(err and "not on this hinge" in err)

    def test_repeated_mx_is_refused_when_the_catalog_is_exhausted(self):
        item = _item()
        item["options"].append({"id": "D", "text": "The activity is science, because ice melted."})
        item["mx_option_map"]["D"] = "sci/H1/MX_condition_omission_1"
        err = bind_cited_mx(item, RECORDS)
        self.assertTrue(err and ("already bound" in err or "not on this hinge" in err))

    def test_false_statement_is_bound(self):
        item = {
            "item_type": "three_statement",
            "stem": "Which statements hold?",
            "statements": [
                {"id": "1", "text": "A question is required."},
                {"id": "2", "text": "Copying steps is enough."},
            ],
            "answer": {"kind": "statement_pattern", "pattern": ["T", "F"]},
            "statement_mx_map": {"2": "sci/H1/MX_condition_omission_1"},
        }
        self.assertIsNone(bind_cited_mx(item, RECORDS))
        self.assertNotIn("mx_refs", item["statements"][0])
        self.assertEqual(item["statements"][1]["mx_refs"][0]["ref"], "sci/H1/MX_condition_omission_1")

    def test_string_statements_are_bound(self):
        item = {
            "item_type": "three_statement",
            "stem": "Which statements hold?",
            "statements": [
                "A question is required.",
                "Copying steps is enough.",
            ],
            "answer": {"kind": "statement_pattern", "pattern": ["T", "F"]},
            "statement_mx_map": {"2": "sci/H1/MX_condition_omission_1"},
        }
        self.assertIsNone(bind_cited_mx(item, RECORDS))
        self.assertEqual(item["statements"][1]["text"], "Copying steps is enough.")
        self.assertEqual(item["statements"][1]["mx_refs"][0]["ref"], "sci/H1/MX_condition_omission_1")
        self.assertNotIn("mx_refs", item["statements"][0])

    def test_option_table_rows_are_bound(self):
        item = {
            "item_type": "option_table",
            "stem": "A block stops sooner on cloth than on glass. What does that show?",
            "rows": [
                {"letter": "A", "claim": "Cloth opposes sliding more", "reason": "the bumps interlock"},
                {"letter": "B", "claim": "The block runs out of motion", "reason": "motion weakens itself"},
                {"letter": "C", "claim": "Cloth pushes the block less", "reason": "rough means less push"},
            ],
            "answer": {"kind": "single_letter", "letter": "A"},
            "mx_option_map": {
                "B": "sci/H1/MX_condition_omission_1",
                "C": "sci/H1/MX_everyday_replacement_2",
            },
        }
        self.assertIsNone(bind_cited_mx(item, RECORDS))
        by_id = {opt["id"]: opt for opt in item["options"]}
        self.assertNotIn("mx_refs", by_id["A"])
        self.assertEqual(by_id["B"]["mx_refs"][0]["ref"], "sci/H1/MX_condition_omission_1")
        self.assertEqual(by_id["C"]["feedback"]["source"], "misconception")

    def test_roman_pattern_dict_is_bound(self):
        item = {
            "item_type": "three_statement",
            "stem": "Which statements hold?",
            "statements": [
                "A question is required.",
                "Copying steps is enough.",
                "Watching a plant is an experiment.",
            ],
            "answer": {"kind": "statement_pattern", "pattern": {"I": "T", "II": "F", "III": "F"}},
            "statement_mx_map": {
                "II": "sci/H1/MX_condition_omission_1",
                "III": "sci/H1/MX_everyday_replacement_2",
            },
        }
        self.assertIsNone(bind_cited_mx(item, RECORDS))
        self.assertEqual(item["answer"]["pattern"], ["T", "F", "F"])
        self.assertNotIn("mx_refs", item["statements"][0])
        self.assertEqual(item["statements"][1]["mx_refs"][0]["ref"], "sci/H1/MX_condition_omission_1")
        self.assertEqual(item["statements"][2]["mx_refs"][0]["ref"], "sci/H1/MX_everyday_replacement_2")


if __name__ == "__main__":
    unittest.main()
