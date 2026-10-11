import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import score_submission


SHEET = {
    "id": "demo",
    "sections": [
        {
            "id": "A",
            "questions": [
                {
                    "id": "q1",
                    "qno": 1,
                    "type": "mcq",
                    "marks": 1,
                    "options": [{"id": "c", "text": "6"}],
                },
                {
                    "id": "q13",
                    "qno": 13,
                    "type": "short",
                    "marks": 2,
                    "response": "text",
                },
                {
                    "id": "q16",
                    "qno": 16,
                    "type": "construction",
                    "marks": 2,
                    "response": "photo",
                },
                {
                    "id": "q12",
                    "qno": 12,
                    "type": "multi_part",
                    "marks": 2,
                    "parts": [
                        {"id": "a", "text": "45", "response": "short"},
                        {"id": "b", "text": "125", "response": "short"},
                    ],
                },
            ],
        }
    ],
}

KEY = {
    "sheet_id": "demo",
    "questions": {
        "q1": {"accept": ["c"], "match": "choice", "wrong": {"a": "div-by-5"}},
        "q13": {"accept": ["1, 2, 3, 4, 6, 8, 12, 24"], "match": "set"},
        "q16": {"kind": "photo", "rubric": "Point marked three fifths after 2."},
        "q12": {
            "parts": {
                "a": {"accept": ["acute"], "match": "token"},
                "b": {"accept": ["obtuse"], "match": "token"},
            }
        },
    },
}


class ScoreTests(unittest.TestCase):
    def test_auto_and_photo(self):
        submission = {
            "answers": {
                "q1": {"value": "a"},
                "q13": {"value": "24, 12, 8, 6, 4, 3, 2, 1"},
                "q16": {"photo": "abc", "content_type": "image/jpeg"},
                "q12": {"parts": {"a": {"value": "Acute angle"}, "b": {"value": ""}}},
            }
        }
        result = score_submission.score(SHEET, KEY, submission)
        by_id = {item["id"]: item for item in result["results"]}
        self.assertEqual(by_id["q1"]["status"], "incorrect")
        self.assertEqual(by_id["q1"]["misconception"], "div-by-5")
        self.assertEqual(by_id["q13"]["status"], "correct")
        self.assertEqual(by_id["q13"]["marks_awarded"], 2)
        self.assertEqual(by_id["q16"]["status"], "needs_review")
        self.assertIsNone(by_id["q16"]["marks_awarded"])
        self.assertIn("fifths", by_id["q16"]["rubric"])
        self.assertEqual(by_id["q12"]["status"], "partial")
        self.assertIn("q16", result["summary"]["needs_review"])

    def test_number_and_rs(self):
        self.assertTrue(score_submission.matches("Profit - 60 Rs", {"accept": ["60"], "match": "number"}))
        self.assertTrue(score_submission.matches("Ans - 45", {"accept": ["45"], "match": "number"}))
        self.assertFalse(score_submission.matches("46", {"accept": ["45"], "match": "number"}))


if __name__ == "__main__":
    unittest.main()
