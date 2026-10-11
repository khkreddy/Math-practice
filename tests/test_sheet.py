import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET = json.loads((ROOT / "content/sheets/2026-10-11-p1.json").read_text())


def questions(sheet):
    return [q for section in sheet["sections"] for q in section["questions"]]


class SheetTests(unittest.TestCase):
    def test_identity_and_marks(self):
        self.assertEqual(SHEET["id"], "2026-10-11-p1")
        self.assertEqual(SHEET["title"], "Practice Sheet 1")
        self.assertEqual(SHEET["total_marks"], 50)
        qs = questions(SHEET)
        self.assertEqual(len(qs), 24)
        self.assertEqual(sum(q["marks"] for q in qs), 50)
        self.assertEqual([q["qno"] for q in qs], list(range(1, 25)))

    def test_wording_is_the_printed_paper(self):
        qs = {q["qno"]: q for q in questions(SHEET)}
        self.assertEqual(qs[1]["text"], "Which of the following is a factor of 44?")
        self.assertEqual([o["text"] for o in qs[1]["options"]], ["5", "7", "9", "11"])
        self.assertEqual(qs[2]["text"], "Which fraction is equivalent to $\\frac{3}{5}$?")
        self.assertEqual(qs[11]["text"], "Solve using DMAS: $56 \\div 8 \\times 6 + 3$")
        self.assertEqual(qs[16]["text"], "Represent $2\\frac{3}{5}$ on a number line.")
        self.assertIn("$19\\frac{3}{6}$", qs[22]["text"])
        self.assertTrue(qs[22]["text"].startswith("Saumya wants to stitch a dress"))
        self.assertEqual(qs[24]["parts"][0]["text"], "Draw one net of a cube.")
        self.assertEqual(qs[24]["parts"][1]["parts"][0]["text"], "Name one right angle from the figure.")
        self.assertEqual(qs[24]["parts"][1]["parts"][1]["text"], "Name one obtuse angle.")

    def test_photo_responses(self):
        qs = {q["qno"]: q for q in questions(SHEET)}
        self.assertEqual(qs[16]["type"], "construction")
        self.assertEqual(qs[16]["response"], "photo")
        self.assertEqual([p["response"] for p in qs[20]["parts"]], ["photo", "photo", "photo"])
        self.assertEqual(qs[24]["parts"][0]["response"], "photo")
        self.assertEqual(qs[24]["parts"][1]["figure"]["src"], "figures/q24.svg")
        self.assertNotIn("response", qs[24]["parts"][1])

    def test_no_answer_key_or_private_fields(self):
        raw = json.dumps(SHEET)
        for forbidden in ("answer_key", "accept", "rubric", "page3", "hinge"):
            self.assertNotIn(forbidden, raw)

    def test_sections(self):
        self.assertEqual([s["id"] for s in SHEET["sections"]], ["A", "B", "C", "D"])
        self.assertEqual(SHEET["sections"][0]["instruction"], "Choose the correct option in the following.")
        self.assertEqual(len(SHEET["instructions"]), 6)


if __name__ == "__main__":
    unittest.main()
