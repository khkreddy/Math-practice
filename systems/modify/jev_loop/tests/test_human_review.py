#!/usr/bin/env python3
"""Human-review appendix is env-gated and drives the shipped writer_prompt."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import human_review  # noqa: E402
import run as tmint_run  # noqa: E402


class HumanReviewAppendixTests(unittest.TestCase):
    def test_missing_dir_is_empty(self):
        os.environ.pop("TTWIN_FILL_FEEDBACK_DIR", None)
        self.assertEqual(human_review.appendix({"target_construct": "An.Pr.3"}), "")

    def test_block_and_gold_injected_into_writer_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "writer_prompt_block.txt").write_text(
                "HUMAN REVIEW CONSTRAINTS (fill campaign):\n- part_answers must be full sentences.\n",
                encoding="utf-8",
            )
            (root / "gold_examples.json").write_text(
                json.dumps(
                    [
                        {
                            "construct": "An.Pr.3",
                            "stem_excerpt": "A taught procedure for ranking carts by speed is broken when a student ranks by start time.",
                            "notes": "Keep the method-trace demand.",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            os.environ["TTWIN_FILL_FEEDBACK_DIR"] = str(root)
            req = {
                "target_construct": "An.Pr.3",
                "grade": 8,
                "subject": "science",
                "hinge_id": "S4/H-MOTION",
                "hinge_title": "Describing motion",
                "intent": "test",
            }
            brief = {"construct_id": "An.Pr.3", "coordinate_display": "Analyze × Procedural × DoK-3", "definition": "d", "evidence_mode": "either"}
            plan = {"recommended_form": "worked_response", "viable_as_mcq": False, "proceed": "proceed_structured", "likely_collapse": None}
            prompt = tmint_run.writer_prompt(req, plan, "structured_parts", brief)
            self.assertIn("HUMAN REVIEW CONSTRAINTS", prompt)
            self.assertIn("part_answers must be full sentences", prompt)
            self.assertIn("GOLD example for An.Pr.3", prompt)
            self.assertIn("method-trace", prompt)
            os.environ.pop("TTWIN_FILL_FEEDBACK_DIR", None)


if __name__ == "__main__":
    unittest.main()
