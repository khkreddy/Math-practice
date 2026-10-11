#!/usr/bin/env python3
"""Frozen phrase checks: legal set, citation refusal, and raw-output guards."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from systems.modify.packet_modify import facts_for_writer, legal_set_for  # noqa: E402
import phrase_contract  # noqa: E402
import run as tmint  # noqa: E402
import unit_bind  # noqa: E402


def _mx(mx_id: str, boundary: str, p1: float) -> dict:
    return {
        "mx_id": mx_id,
        "route": mx_id.rsplit("/", 1)[-1],
        "wrong": "A false sentence for " + mx_id,
        "boundary_links": [{"boundary": boundary, "p1": p1}],
    }


class LegalSetTests(unittest.TestCase):
    def test_verified_set_is_the_linked_mixups_when_it_fills_the_slots(self):
        records = [
            _mx("u/MX_a", "same situation", 0.91),
            _mx("u/MX_b", "same situation", 0.80),
            _mx("u/MX_c", "same situation", 0.75),
            _mx("u/MX_d", "other situation", 0.99),
        ]
        legal = legal_set_for(records, 3)
        self.assertTrue(legal["situation_verified"])
        self.assertEqual(legal["legal_ids"], ["u/MX_a", "u/MX_b", "u/MX_c"])
        self.assertNotIn("u/MX_d", legal["legal_ids"])

    def test_unverified_set_is_every_center_mixup_and_a_short_set_is_too_small(self):
        records = [
            _mx("u/MX_a", "same situation", 0.91),
            _mx("u/MX_b", "other situation", 0.80),
        ]
        legal = legal_set_for(records, 3)
        self.assertFalse(legal["situation_verified"])
        self.assertEqual(legal["legal_ids"], ["u/MX_a", "u/MX_b"])
        self.assertLess(len(legal["legal_ids"]), 3)

    def test_support_mixups_are_outside_the_legal_set(self):
        writer = facts_for_writer({
            "form": {
                "subject": "science",
                "grade": 6,
                "band": "middle_6_8",
                "item_type": "single_mcq",
                "n_options": 4,
            },
            "units": [
                {"unit_id": "c", "mx": [{
                    "mx_id": "c/MX_a",
                    "canonical_wrong_output": "Wrong center.",
                    "boundary_links": [{"boundary": "one situation", "p1": 0.9}],
                }]},
                {"unit_id": "n", "mx": [{
                    "mx_id": "n/MX_b",
                    "canonical_wrong_output": "Wrong neighbour.",
                }]},
            ],
            "prerequisite_gaps": [],
        })
        self.assertEqual([row["mx_id"] for row in writer["misconceptions_mx"]], ["c/MX_a"])
        self.assertEqual(writer["support_mx"][0]["mx_id"], "n/MX_b")
        self.assertEqual(writer["support_mx"][0]["role"], "support")
        self.assertNotIn("n/MX_b", writer["legal_set"]["legal_ids"])


class PhraseGuardTests(unittest.TestCase):
    def _item(self, **over):
        item = {
            "item_type": "single_mcq",
            "stem": "A leaf shows a net of veins. Which pattern is this?",
            "options": [
                {"id": "A", "text": "Reticulate venation."},
                {"id": "B", "text": "Parallel venation."},
            ],
            "answer": {"letter": "A"},
            "worked_solution": {"result": "Reticulate venation."},
        }
        item.update(over)
        return item

    def test_result_must_match_the_keyed_option_before_any_rewrite(self):
        item = self._item()
        item["worked_solution"] = {"result": "Parallel venation."}
        errors = phrase_contract.structural_errors(item, {"entities": ["leaf"]})
        self.assertIn("worked_solution.result does not equal the keyed option text", errors)

    def test_the_word_it_is_not_a_violation(self):
        item = self._item(stem="It shows a net of veins. Which pattern is this?")
        errors = phrase_contract.structural_errors(item, {"entities": ["leaf"]})
        self.assertFalse(any("material" in err or "substance" in err for err in errors))

    def test_the_material_is_refused_when_the_hinge_names_entities(self):
        item = self._item(stem="The material shows a net of veins. Which pattern is this?")
        errors = phrase_contract.structural_errors(item, {"entities": ["leaf"]})
        self.assertTrue(any("material" in err for err in errors))

    def test_roman_labels_in_options_must_appear_in_the_stem(self):
        item = self._item(
            stem="Which set is supported?",
            options=[
                {"id": "A", "text": "I and II"},
                {"id": "B", "text": "I only"},
            ],
        )
        errors = phrase_contract.structural_errors(item, {})
        self.assertTrue(any("roman labels" in err for err in errors))

    def test_assertion_reason_requires_the_five_relations(self):
        options = [
            "Both Assertion and Reason are true, and the Reason correctly explains the Assertion.",
            "Both Assertion and Reason are true, but the Reason does not correctly explain the Assertion.",
            "The Assertion is true, but the Reason is false.",
            "The Assertion is false, but the Reason is true.",
            "Both Assertion and Reason are false.",
        ]
        item = self._item(
            stem="Assertion (A): Ice melts at 0 °C. Reason (R): Particles leave the solid. Which relation holds?",
            options=[{"id": chr(65 + i), "text": text} for i, text in enumerate(options)],
            answer={"letter": "A"},
            worked_solution={"result": options[0]},
        )
        errors = phrase_contract.structural_errors(item, {})
        self.assertFalse(any("assertion-reason" in err for err in errors))
        item["options"] = item["options"][:4]
        errors = phrase_contract.structural_errors(item, {})
        self.assertTrue(any("assertion-reason" in err for err in errors))

    def test_a_choice_item_must_have_consecutive_options_and_a_bare_key(self):
        gapped = self._item(options=[
            {"id": "A", "text": "Reticulate venation."},
            {"id": "B", "text": "Parallel venation."},
            {"id": "C", "text": "No venation."},
            {"id": "E", "text": "Waxy coating."},
        ])
        errors = phrase_contract.option_shape_errors(gapped)
        self.assertTrue(any("consecutive" in err for err in errors))
        empty = self._item(item_type="single_mcq", options=[{"id": "A", "text": "Reticulate venation."}])
        errors = phrase_contract.option_shape_errors(empty)
        self.assertTrue(any("four options" in err for err in errors))
        explained = self._item(options=[
            {"id": "A", "text": "Nitrogen, because it is present in the largest amount in air."},
            {"id": "B", "text": "Oxygen"},
            {"id": "C", "text": "Argon"},
            {"id": "D", "text": "Carbon dioxide"},
        ])
        errors = phrase_contract.option_shape_errors(explained)
        self.assertTrue(any("explains the answer" in err for err in errors))
        free = {"item_type": "open_response", "stem": "What happens to the spoon?", "options": []}
        self.assertEqual(phrase_contract.enforce_locked_type(free, {"lock_item_type": "single_mcq"}), "")
        self.assertEqual(
            phrase_contract.enforce_locked_type(
                free, {"lock_format": True, "lock_item_type": "single_mcq"}
            ),
            "choice item was rewritten as free response",
        )


class RouteIdTests(unittest.TestCase):
    def test_duplicate_route_is_recorded_and_the_id_has_no_index(self):
        unit = unit_bind.slim_unit({
            "unit_id": "science/grade_06/ch_01/H001",
            "mixups": [
                {"route": "scope_error", "wrong": "Any change is chemical."},
                {"route": "scope_error", "wrong": "Any mixing is chemical."},
            ],
        })
        self.assertEqual(unit["duplicate_routes"], ["scope_error"])
        self.assertTrue(all(rec["mx_id"].endswith("/MX_scope_error") for rec in unit["mx_records"]))
        self.assertFalse(any(rec["mx_id"].endswith("_1") or rec["mx_id"].endswith("_2") for rec in unit["mx_records"]))
        prompt = tmint.writer_prompt(
            {"grade": 6, "subject": "science", "hinge_id": unit["unit_id"], "target_construct": "U.Co.1"},
            {"proceed": "proceed_mcq"},
            "single_mcq",
            {"construct_id": "U.Co.1", "coordinate_display": "x", "definition": "d", "evidence_mode": "either"},
            unit,
        )
        self.assertIn("wrong_output_students_produce", prompt)
        self.assertIn("science/grade_06/ch_01/H001/MX_scope_error", prompt)
        self.assertNotIn("Mix-up line (teacher-side)", prompt)


if __name__ == "__main__":
    unittest.main()
