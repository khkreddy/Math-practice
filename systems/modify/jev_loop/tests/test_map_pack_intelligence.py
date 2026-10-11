"""Sanitized mixups keep confused/observable/borders in T-MINT and T-MOD packs."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
MODIFY = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(MODIFY))

import packet_modify as packet  # noqa: E402
import run as tmint  # noqa: E402
import unit_bind  # noqa: E402

HINGE = {
    "unit_id": "science/grade_06/ch_02/H004",
    "decision": "Identify whether a leaf has reticulate venation or parallel venation from the pattern of its veins.",
    "law": "The thin lines seen on leaves are veins, and the pattern of veins is called venation.",
    "because": "leaf_vein_pattern -> venation_type",
    "operation": "identify",
    "entities": ["leaf", "veins"],
    "student_default": "Venation means the overall shape of a leaf.",
    "false_success": [{"apparent_success": "states reticulate without vein evidence", "type": "label_only"}],
    "mastery": {"claim": "The learner uses the vein pattern."},
    "chapter_title": "Diversity in the Living World",
    "boundaries": [
        "Use the pattern of veins on the leaf, not flower colour or plant height.",
        "A thick middle vein with a net-like pattern on both sides supports reticulate venation.",
    ],
    "mixups": [
        {
            "route": "relationship_reversal",
            "wrong": "Net-like pattern: parallel venation.",
            "confused": "Assignments from vein patterns to venation types",
            "observable": "Assigns the opposite venation label",
            "border": {
                "p1": 0.7,
                "source": "boundary",
                "text": "A thick middle vein with a net-like pattern on both sides supports reticulate venation.",
            },
            "links": [
                {"boundary": "Use the pattern of veins on the leaf, not flower colour or plant height.", "p1": 0.82},
                {"boundary": "A thick middle vein with a net-like pattern on both sides supports reticulate venation.", "p1": 0.92},
            ],
        },
        {
            "route": "everyday_replacement",
            "wrong": "Parallel veins are roads drawn next to each other.",
            "border": {"reason": "template"},
        },
    ],
    "jev_taxonomy_zone": {"admitted": ["An.Co.2"]},
}


class MintPackTests(unittest.TestCase):
    def test_slim_unit_keeps_confused_observable_and_border(self):
        slim = unit_bind.slim_unit(HINGE)
        rec = slim["mx_records"][0]
        self.assertEqual(rec["mx_id"], "science/grade_06/ch_02/H004/MX_relationship_reversal")
        self.assertIn("Assignments from vein patterns", rec["confused"])
        self.assertIn("opposite venation", rec["observable"])
        self.assertEqual(rec["border"]["source"], "boundary")
        self.assertEqual(
            slim["situation_boundary"],
            "A thick middle vein with a net-like pattern on both sides supports reticulate venation.",
        )

    def test_writer_prompt_prints_situation_boundary_and_confused(self):
        slim = unit_bind.slim_unit(HINGE)
        prompt = tmint.writer_prompt(
            {
                "target_construct": "An.Co.2",
                "grade": 6,
                "subject": "science",
                "hinge_id": HINGE["unit_id"],
                "grade_band": "middle_6_8",
            },
            {"recommended_form": "claim_evidence_mcq", "proceed": "proceed_mcq"},
            "single_mcq",
            {"construct_id": "An.Co.2", "coordinate_display": "x", "definition": "d", "evidence_mode": "either"},
            slim,
        )
        self.assertIn("Situation boundary (teacher-side)", prompt)
        self.assertIn("confused_element", prompt)
        self.assertIn("Assignments from vein patterns to venation types", prompt)
        self.assertIn("A thick middle vein with a net-like pattern", prompt)
        self.assertIn("Student default (teacher-side)", prompt)
        self.assertIn("Entities (teacher-side): leaf, veins", prompt)


class ModPackTests(unittest.TestCase):
    def test_writer_packet_keeps_entities_mastery_route_and_template_border(self):
        original = packet.raw_by_id
        packet.raw_by_id = lambda _subject: {HINGE["unit_id"]: HINGE}
        try:
            built = packet.packet_for_row(
                {
                    "subject": "science",
                    "grade": 6,
                    "item_type": "single_mcq",
                    "jev_taxonomy": {"hinge_id": HINGE["unit_id"], "construct_id": "An.Co.2"},
                },
                {"band": "middle_6_8", "subject": "science", "grade": 6},
            )
        finally:
            packet.raw_by_id = original
        self.assertTrue(built["ok"])
        writer = built["writer_packet"]
        center = writer["units"][0]
        self.assertEqual(center["entities"], ["leaf", "veins"])
        self.assertIn("vein pattern", center["mastery_claim"])
        self.assertEqual(center["chapter_title"], "Diversity in the Living World")
        mx = writer["misconceptions_mx"]
        self.assertEqual(mx[0]["route"], "relationship_reversal")
        self.assertEqual(mx[0]["confused_element"], "Assignments from vein patterns to venation types")
        self.assertEqual(mx[1]["border"]["reason"], "template")


if __name__ == "__main__":
    unittest.main()
