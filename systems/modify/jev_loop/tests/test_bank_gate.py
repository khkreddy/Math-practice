#!/usr/bin/env python3
"""Bank-append eligibility: TOP + overlay in; MEDIUM/LOW/missing overlay out.

Drives the shipped predicate. Does not reimplement it and does not treat a full
item fixture as the expected bank.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import bank_gate  # noqa: E402


def _mcq_payload() -> dict:
    """Minimal served MCQ that already clears worked_solution + option.feedback gates."""
    return {
        "item_type": "single_mcq",
        "stem": (
            "A straight path through R and S has an arrowhead beyond R away from S "
            "and an arrowhead beyond S away from R. What name matches this path?"
        ),
        "options": {
            "A": "line",
            "B": {
                "text": "ray",
                "feedback": {
                    "learning_state": "A path with arrowheads beyond both marked points is classed as a ray.",
                    "evidence": "beyond R, an arrowhead points away from S; beyond S, an arrowhead points away from R.",
                    "source": "misconception",
                },
            },
            "C": {
                "text": "line segment",
                "feedback": {
                    "learning_state": "A path with arrowheads beyond both marked points is classed as a line segment.",
                    "evidence": "beyond R, an arrowhead points away from S; beyond S, an arrowhead points away from R.",
                    "source": "misconception",
                },
            },
            "D": {
                "text": "curve",
                "feedback": {
                    "learning_state": "A path with arrowheads beyond both marked points is classed as a curve.",
                    "evidence": "beyond R, an arrowhead points away from S; beyond S, an arrowhead points away from R.",
                    "source": "misconception",
                },
            },
        },
        "answer": {"kind": "single_letter", "letter": "A"},
        "worked_solution": {
            "schema": "ttwin.worked_solution.v1",
            "status": "complete",
            "blocker": None,
            "given_facts": [
                "A straight path is marked through points R and S",
                "beyond R, an arrowhead points away from S",
                "beyond S, an arrowhead points away from R",
            ],
            "hinges_used": [
                {
                    "unit_id": "math/grade_06/ch_02/H002",
                    "role": "primary",
                    "contribution": 1.0,
                }
            ],
            "steps": [
                "Given: A straight path is marked through points R and S.",
                "Given: beyond R, an arrowhead points away from S.",
                "Given: beyond S, an arrowhead points away from R.",
                "By definition, a line has no endpoints; a ray has one endpoint and continues past the other mark; a line segment has two endpoints and stops at both — so the name is fixed by how many ends the path has and whether it continues past them.",
                "This path has no endpoint at either marked point and continues both ways, so the matching name is a line (not a line segment, not a ray).",
            ],
            "result": "line",
            "key_letter": "A",
            "why_key": "Option A is the quantity obtained by the derivation from the givens.",
            "distractors": [
                {
                    "letter": "B",
                    "text": "ray",
                    "why_wrong": "Wrong: conflicts with the derived result.",
                    "mx_or_gap": [],
                },
                {
                    "letter": "C",
                    "text": "line segment",
                    "why_wrong": "Wrong: conflicts with the derived result.",
                    "mx_or_gap": [],
                },
                {
                    "letter": "D",
                    "text": "curve",
                    "why_wrong": "Wrong: conflicts with the derived result.",
                    "mx_or_gap": [],
                },
            ],
        },
    }


def _row(tier: str | None, schema: str | None, extra_miqg: dict | None = None) -> dict:
    miqg = dict(extra_miqg or {})
    if tier is not None:
        miqg["tier"] = tier
    row: dict = {"id": "probe", "miqg": miqg, "item": _mcq_payload()}
    if schema is not None:
        row["jev_taxonomy"] = {"schema": schema, "admitted": True, "construct_id": "U.Pr.2"}
    return row


class BankAppendEligibleTests(unittest.TestCase):
    def test_top_with_overlay_accepted(self):
        self.assertTrue(
            bank_gate.bank_append_eligible(_row("TOP", bank_gate.OVERLAY_SCHEMA))
        )

    def test_human_hold_blocks_an_otherwise_eligible_row(self):
        row = _row("TOP", bank_gate.OVERLAY_SCHEMA)
        row["release"] = {"human_hold": True}
        self.assertFalse(bank_gate.bank_append_eligible(row))

    def test_quality_tier_alias_accepted(self):
        row = _row("TOP", bank_gate.OVERLAY_SCHEMA)
        row["miqg"] = {"quality_tier": "TOP"}
        self.assertTrue(bank_gate.bank_append_eligible(row))

    def test_medium_rejected(self):
        self.assertFalse(
            bank_gate.bank_append_eligible(_row("MEDIUM", bank_gate.OVERLAY_SCHEMA))
        )

    def test_low_rejected(self):
        self.assertFalse(
            bank_gate.bank_append_eligible(_row("LOW", bank_gate.OVERLAY_SCHEMA))
        )

    def test_missing_overlay_rejected(self):
        self.assertFalse(bank_gate.bank_append_eligible(_row("TOP", None)))

    def test_wrong_overlay_schema_rejected(self):
        self.assertFalse(bank_gate.bank_append_eligible(_row("TOP", "other.schema")))

    def test_empty_or_non_dict_rejected(self):
        self.assertFalse(bank_gate.bank_append_eligible({}))
        self.assertFalse(bank_gate.bank_append_eligible(None))  # type: ignore[arg-type]
        self.assertFalse(bank_gate.bank_append_eligible("TOP"))  # type: ignore[arg-type]


class TrailPackTests(unittest.TestCase):
    def _trail(self, tier: str, overlay: bool = True) -> dict:
        tag = {"schema": bank_gate.OVERLAY_SCHEMA, "admitted": False, "construct_id": None} if overlay else None
        item = dict(_mcq_payload())
        item["schema"] = "modify_result.v1"
        return {
            "requirement": {
                "subject": "science",
                "grade": 7,
                "grade_band": "middle_6_8",
                "target_construct": "An.Pr.3",
                "hinge_id": "S5/H-CIRCUIT",
                "requirement_id": "probe-anpr3",
            },
            "plan": {"recommended_form": "error_analysis_mcq"},
            "miqg": {"quality_tier": tier, "protocol": "MIQG-v1.0-rc9-CAL-KNGOOD-v2", "decisive_reason": "KNOWN_GOOD_ENVELOPE"},
            "g18": {"status": "CONSTRUCT_HOLD"},
            "jev_taxonomy": tag,
            "item": item,
        }

    def test_top_trail_packs_and_stays_eligible(self):
        packed = bank_gate.bank_row_from_trail(self._trail("TOP"), "sci_probe")
        self.assertIsNotNone(packed)
        self.assertTrue(bank_gate.bank_append_eligible(packed))
        self.assertEqual(packed["id"], "sci_probe")
        self.assertEqual(packed["miqg"]["tier"], "TOP")
        self.assertEqual(packed["jev_taxonomy"]["schema"], bank_gate.OVERLAY_SCHEMA)

    def test_medium_trail_not_packed(self):
        self.assertIsNone(bank_gate.bank_row_from_trail(self._trail("MEDIUM"), "sci_probe"))

    def test_low_trail_not_packed(self):
        self.assertIsNone(bank_gate.bank_row_from_trail(self._trail("LOW"), "sci_probe"))

    def test_missing_overlay_trail_not_packed(self):
        self.assertIsNone(bank_gate.bank_row_from_trail(self._trail("TOP", overlay=False), "sci_probe"))

    def test_append_writes_only_eligible(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "science.jsonl"
            good = bank_gate.bank_row_from_trail(self._trail("TOP"), "keep_me")
            self.assertTrue(bank_gate.append_eligible_row(path, good))
            medium_row = {
                "id": "drop_me",
                "miqg": {"tier": "MEDIUM", "protocol": "x"},
                "jev_taxonomy": {"schema": bank_gate.OVERLAY_SCHEMA},
                "item": {"stem": "no"},
            }
            self.assertFalse(bank_gate.append_eligible_row(path, medium_row))
            lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
            self.assertEqual(len(lines), 1)
            stored = json.loads(lines[0])
            self.assertEqual(stored["id"], "keep_me")
            self.assertTrue(bank_gate.bank_append_eligible(stored))
            self.assertFalse(bank_gate.append_eligible_row(path, good))  # duplicate id


class KeyLettersFailClosedTests(unittest.TestCase):
    def test_string_part_answers_do_not_crash(self):
        sys.path.insert(0, str(HERE.parent / "miqg"))
        import miqg_cal  # noqa: E402

        letters = miqg_cal.key_letters(
            {"kind": "part_answers", "part_answers": ["7", "x=7"]}
        )
        self.assertEqual(letters, [])

    def test_scan_string_part_answers_do_not_crash(self):
        sys.path.insert(0, str(HERE.parent / "miqg"))
        import miqg_cal  # noqa: E402

        result = {
            "item_type": "structured_parts",
            "stem": "A dish holds salt and sand.",
            "options": [],
            "parts": [
                {"id": "a", "text": "First step?", "marks": 1, "rubric": "dissolve"},
                {"id": "b", "text": "Second?", "marks": 1, "rubric": "filter"},
            ],
            "answer": {"kind": "part_answers", "part_answers": ["dissolve", "filter"]},
            "tikz": "",
            "tables": [],
        }
        findings = miqg_cal.scan(result, packet={}, meta={}, codes={"answer_in_stem_pairs": []})
        self.assertIsInstance(findings, list)


class StructuredPartsGateTests(unittest.TestCase):
    def test_string_parts_fail_closed(self):
        import gates
        import packet

        src = {"item_type": "structured_parts", "stem": "Separate salt from sand.", "options": []}
        pkt = packet.assemble_modify_packet(
            src,
            "order of steps",
            variation_class="V3",
            figure_mode="preserve",
            target_item_type="structured_parts",
        )
        out = {
            "schema": "modify_result.v1",
            "status": "OK",
            "item_type": "structured_parts",
            "stem": "A dish holds salt and sand. A student wants to recover the salt.",
            "options": [],
            "parts": ["write the first step", "write the second step"],
            "answer": {"kind": "part_answers", "part_answers": []},
            "teacher": {"proposed_key_status": "UNVERIFIED", "variation_applied": "V3", "fidelity_selfcheck": "test", "key_rationale": "x"},
        }
        gate = gates.apply_outcome(out, pkt)
        self.assertFalse(gate["ok"])
        self.assertEqual(gate["gate"], "G2")

    def test_string_statements_do_not_crash_learner_blob(self):
        import gates
        import packet

        src = {"item_type": "structured_parts", "stem": "A cable.", "options": []}
        pkt = packet.assemble_modify_packet(
            src,
            "conductor vs insulator",
            variation_class="V3",
            figure_mode="preserve",
            target_item_type="structured_parts",
        )
        out = {
            "schema": "modify_result.v1",
            "status": "OK",
            "item_type": "structured_parts",
            "stem": "A lamp cable lies on wet grass.",
            "options": [],
            "parts": [
                {"id": "a", "text": "Core material?", "marks": 1, "rubric": "metal"},
                {"id": "b", "text": "Coating?", "marks": 1, "rubric": "rubber"},
            ],
            "statements": ["copper conducts", "rubber insulates"],
            "answer": {
                "kind": "part_answers",
                "part_answers": [
                    {"part_id": "a", "answer": "metal"},
                    {"part_id": "b", "answer": "rubber"},
                ],
            },
            "teacher": {
                "proposed_key_status": "UNVERIFIED",
                "variation_applied": "V3",
                "fidelity_selfcheck": "test",
                "key_rationale": "x",
            },
        }
        blob = gates.learner_blob(out)
        self.assertIn("copper conducts", blob)
        gate = gates.apply_outcome(out, pkt)
        self.assertIsInstance(gate.get("ok"), bool)

    def test_dict_stem_does_not_crash_g3(self):
        import gates
        import packet

        src = {"item_type": "structured_parts", "stem": "Salt in water.", "options": []}
        pkt = packet.assemble_modify_packet(
            src,
            "dissolving",
            variation_class="V3",
            figure_mode="preserve",
            target_item_type="structured_parts",
        )
        out = {
            "schema": "modify_result.v1",
            "status": "OK",
            "item_type": "structured_parts",
            "stem": {"text": "A student stirs salt into water."},
            "options": [],
            "parts": [
                {"id": "a", "text": "What remains?", "marks": 1, "rubric": "mixture"},
                {"id": "b", "text": "How to recover salt?", "marks": 1, "rubric": "evaporate"},
            ],
            "answer": {
                "kind": "part_answers",
                "part_answers": [
                    {"part_id": "a", "answer": "a mixture"},
                    {"part_id": "b", "answer": "evaporate the water"},
                ],
            },
            "teacher": {
                "proposed_key_status": "UNVERIFIED",
                "variation_applied": "V3",
                "fidelity_selfcheck": "test",
                "key_rationale": "x",
            },
        }
        self.assertFalse(gates.mentions_figure(out["stem"]))
        gate = gates.apply_outcome(out, pkt)
        self.assertIsInstance(gate.get("ok"), bool)


    def test_mcq_without_option_feedback_rejected(self):
        row = {
            "miqg": {"tier": "TOP"},
            "jev_taxonomy": {"schema": bank_gate.OVERLAY_SCHEMA},
            "item": {
                "item_type": "single_mcq",
                "stem": "A lamp is in a loop. What follows?",
                "options": {
                    "A": "the lamp lights",
                    "B": {"text": "the lamp stays dark"},
                    "C": {"text": "the wire melts"},
                    "D": {"text": "the switch vanishes"},
                },
                "answer": {"kind": "single_letter", "letter": "A"},
                "worked_solution": {
                    "status": "complete",
                    "steps": ["The loop is closed.", "Current reaches the lamp.", "The lamp lights."],
                    "result": "the lamp lights",
                },
            },
        }
        self.assertTrue(bank_gate._item_refuses_missing_option_feedback(row))

    def test_mcq_with_option_feedback_passes_feedback_gate(self):
        row = {
            "item": {
                "item_type": "single_mcq",
                "stem": "A lamp is in a closed loop. What follows?",
                "options": {
                    "A": "the lamp lights",
                    "B": {
                        "text": "the lamp stays dark",
                        "feedback": {
                            "learning_state": "A closed loop is treated as having no path for current.",
                            "evidence": "The stem states the lamp is in a closed loop.",
                            "source": "misconception",
                        },
                    },
                    "C": {
                        "text": "the wire melts",
                        "feedback": {
                            "learning_state": "Current in a simple lamp loop is taken to destroy the wire.",
                            "evidence": "The stem names only a lamp in a closed loop.",
                            "source": "misconception",
                        },
                    },
                    "D": {
                        "text": "the switch vanishes",
                        "feedback": {
                            "learning_state": "The idea of a closed conducting path is missing.",
                            "evidence": "The stem states the lamp is in a closed loop.",
                            "source": "prerequisite_gap",
                        },
                    },
                },
                "answer": {"kind": "single_letter", "letter": "A"},
            }
        }
        self.assertFalse(bank_gate._item_refuses_missing_option_feedback(row))


class MintIdTests(unittest.TestCase):
    def test_id_stable_for_same_requirement(self):
        req = {
            "subject": "science",
            "grade": 7,
            "hinge_id": "S5/H-CIRCUIT",
            "requirement_id": "sci-An.Pr.3-circuit-r2",
        }
        a = bank_gate.mint_item_id(req)
        b = bank_gate.mint_item_id(req)
        self.assertEqual(a, b)
        self.assertEqual(a, "science_grade_07_S5-H-CIRCUIT__sci-An-Pr-3-circuit-r2")


class LiveBankPredicateTests(unittest.TestCase):
    """Drive the shipped predicate on real middle_6_8 bank rows."""

    BANK = Path("/home/harik/TTwin-final/data/questions/middle_6_8")

    def _first_row(self, name: str) -> dict:
        with (self.BANK / name).open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    return json.loads(line)
        self.fail("empty bank " + name)

    def test_existing_science_row_accepted(self):
        row = self._first_row("science.jsonl")
        if bank_gate._item_refuses_missing_option_feedback(row):
            self.skipTest("first science row lacks option.feedback (pre-backfill)")
        self.assertTrue(bank_gate.bank_append_eligible(row), row.get("id"))

    def test_existing_maths_row_accepted(self):
        row = self._first_row("maths.jsonl")
        if bank_gate._item_refuses_missing_option_feedback(row):
            self.skipTest("first maths row lacks option.feedback (pre-backfill)")
        self.assertTrue(bank_gate.bank_append_eligible(row), row.get("id"))

    def test_medium_mutation_of_real_row_rejected(self):
        row = json.loads(json.dumps(self._first_row("science.jsonl")))
        row["miqg"] = dict(row.get("miqg") or {})
        row["miqg"]["tier"] = "MEDIUM"
        self.assertFalse(bank_gate.bank_append_eligible(row))

    def test_missing_overlay_mutation_of_real_row_rejected(self):
        row = json.loads(json.dumps(self._first_row("maths.jsonl")))
        row.pop("jev_taxonomy", None)
        self.assertFalse(bank_gate.bank_append_eligible(row))

    def test_appended_fill_row_accepted_if_present(self):
        hits = []
        with (self.BANK / "maths.jsonl").open(encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if (rec.get("design") or {}).get("source") == "t-mint-middle-6-8-fill":
                    hits.append(rec)
        if not hits:
            self.skipTest("no fill row packed yet")
        for rec in hits:
            self.assertEqual(rec["miqg"]["tier"], "TOP")
            self.assertTrue(bank_gate.bank_append_eligible(rec), rec.get("id"))


class UnwrapWriterItemTests(unittest.TestCase):
    def test_nested_stem_promoted(self):
        import run as mint_run

        nested = {
            "version": "modify_result.v1",
            "status": "OK",
            "item": {
                "item_type": "structured_parts",
                "stem": "Two methods are proposed.",
                "parts": [{"id": "a", "text": "Which method?", "marks": 2}],
            },
            "answer": {"kind": "part_answers", "part_answers": []},
            "teacher": {"key_rationale": "melting point is intensive"},
            "item_type": "structured_parts",
        }
        flat = mint_run.unwrap_writer_item(nested)
        self.assertEqual(flat.get("stem"), "Two methods are proposed.")
        self.assertEqual(flat.get("item_type"), "structured_parts")
        self.assertEqual(flat.get("status"), "OK")
        self.assertIn("part_answers", flat.get("answer") or {})

    def test_dict_options_get_ids(self):
        import catalog

        item = {
            "status": "OK",
            "item_type": "single_mcq",
            "stem": "A saucepan base.",
            "options": {"A": "melting point and rigidity", "B": "conductivity"},
            "answer": {"kind": "single_letter", "letter": "A"},
        }
        flat = catalog.normalize_result_shape(item)
        ids = [o["id"] for o in flat["options"]]
        self.assertEqual(ids, ["A", "B"])
        self.assertEqual(flat["options"][0]["text"], "melting point and rigidity")

    def test_dict_options_preserve_option_feedback(self):
        """Writer dict options with feedback must not be stripped to bare text."""
        import catalog

        item = {
            "status": "OK",
            "item_type": "single_mcq",
            "stem": "Which path is a ray?",
            "options": {
                "A": {
                    "text": "Arrowheads beyond both marked points.",
                    "feedback": {
                        "learning_state": "A path with arrowheads beyond both marked points is classed as a line.",
                        "evidence": "Arrowheads beyond both marked points.",
                        "source": "misconception",
                    },
                },
                "B": {"text": "One arrowhead beyond one marked point."},
                "C": {
                    "text": "No arrowheads.",
                    "feedback": {
                        "learning_state": "A required prior idea for ray vs segment is missing.",
                        "evidence": "No arrowheads.",
                        "source": "prerequisite_gap",
                    },
                },
            },
            "answer": {"kind": "single_letter", "letter": "B"},
        }
        flat = catalog.normalize_result_shape(item)
        by_id = {o["id"]: o for o in flat["options"]}
        self.assertEqual(
            by_id["A"]["feedback"]["learning_state"],
            "A path with arrowheads beyond both marked points is classed as a line.",
        )
        self.assertEqual(by_id["A"]["feedback"]["source"], "misconception")
        self.assertEqual(by_id["C"]["feedback"]["source"], "prerequisite_gap")
        self.assertNotIn("feedback", by_id["B"])

    def test_attach_wrong_option_feedback_uses_mx_verbatim(self):
        """Harness must write feedback from loaded Mx / gap, not invent free prose."""
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[3]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from systems.modify import packet_modify

        item = {
            "status": "OK",
            "item_type": "single_mcq",
            "stem": "Which claim follows?",
            "options": [
                {"id": "A", "text": "Keyed claim."},
                {"id": "B", "text": "Wrong mix-up claim."},
                {"id": "C", "text": "Wrong gap claim."},
            ],
            "answer": {"kind": "single_letter", "letter": "A"},
            "mx_option_map": {"C": "mx_1"},
        }
        wp = {
            "misconceptions_mx": [
                {
                    "mx_id": "mx_1",
                    "wrong_output_students_produce": "Students treat the vector as a scalar magnitude only",
                    "confused_element": "vector vs scalar",
                    "observable_prediction": "reports a positive length with no direction",
                }
            ],
            "prerequisite_gaps": [
                {
                    "missing_hinge": "math/grade_06/ch_01/H001",
                    "required_capability": "Read a directed segment as having one arrowhead",
                }
            ],
        }
        out = packet_modify.attach_wrong_option_feedback(item, wp)
        by_id = {o["id"]: o for o in out["options"]}
        self.assertNotIn("feedback", by_id["A"])
        self.assertNotIn("feedback", by_id["B"])
        self.assertEqual(by_id["C"]["feedback"]["source"], "misconception")
        self.assertIn(
            "Students treat the vector as a scalar magnitude only",
            by_id["C"]["feedback"]["learning_state"],
        )
        self.assertIn("reports a positive length with no direction", by_id["C"]["feedback"]["evidence"])

    def test_single_letter_correct_field_becomes_letter(self):
        import catalog
        import gates
        import packet

        item = {
            "status": "OK",
            "item_type": "single_mcq",
            "stem": "A solid salt does not conduct, and the melt does. Which model fits both observations?",
            "options": [
                {"id": "A", "text": "Free electrons appear only after melting."},
                {"id": "B", "text": "Ions are locked in the solid and mobile in the melt."},
                {"id": "C", "text": "Molecules break into atoms when heated."},
                {"id": "D", "text": "The lattice has no charged particles."},
            ],
            "answer": {"kind": "single_letter", "correct": "B"},
            "teacher": {"proposed_key_status": "UNVERIFIED", "variation_applied": "V3"},
        }
        flat = catalog.normalize_result_shape(item)
        self.assertEqual(flat["answer"]["kind"], "single_letter")
        self.assertEqual(flat["answer"]["letter"], "B")
        valued = dict(item)
        valued["answer"] = {"kind": "single_letter", "value": "B"}
        self.assertEqual(catalog.normalize_result_shape(valued)["answer"]["letter"], "B")
        src = {"item_type": "single_mcq", "stem": "intent", "options": []}
        pkt = packet.assemble_modify_packet(
            src,
            "intent",
            variation_class="V3",
            figure_mode="preserve",
            target_item_type="single_mcq",
        )
        gate = gates.apply_outcome(flat, pkt)
        self.assertTrue(gate.get("ok"), gate)

    def test_answer_parts_list_becomes_part_answers(self):
        import catalog

        item = {
            "status": "OK",
            "item_type": "structured_parts",
            "stem": "Two claims are made about the melt.",
            "parts": [
                {"id": "a", "text": "Which claim fails?", "marks": 2},
                {"id": "b", "text": "What forms at the cathode?", "marks": 2},
            ],
            "answer": {"kind": "part_answers", "parts": ["The first claim fails.", "Copper metal forms."]},
            "teacher": {"proposed_key_status": "UNVERIFIED", "variation_applied": "V3"},
        }
        flat = catalog.normalize_result_shape(item)
        answers = flat["answer"]["part_answers"]
        self.assertEqual([row["part_id"] for row in answers], ["a", "b"])
        self.assertEqual(answers[1]["answer"], "Copper metal forms.")

    def test_string_options_get_letter_ids(self):
        import catalog

        item = {
            "status": "OK",
            "item_type": "single_mcq",
            "stem": "Place value.",
            "options": ["tenths", "hundredths", "ones", "thousandths"],
            "answer": {"kind": "single_letter", "letter": "B"},
        }
        flat = catalog.normalize_result_shape(item)
        self.assertEqual([o["id"] for o in flat["options"]], ["A", "B", "C", "D"])
        self.assertEqual(flat["options"][1]["text"], "hundredths")

    def test_part_answers_gain_part_id(self):
        import catalog

        item = {
            "status": "OK",
            "item_type": "structured_parts",
            "stem": "Separate salt.",
            "parts": [{"text": "First step?", "marks": 1}, {"id": "b", "text": "Second?", "marks": 1}],
            "answer": {
                "kind": "part_answers",
                "part_answers": [
                    {"part": "a", "answer": "dissolve"},
                    {"part_id": "b", "answer": "filter"},
                ],
            },
        }
        flat = catalog.normalize_result_shape(item)
        self.assertEqual(flat["parts"][0]["id"], "a")
        self.assertEqual(flat["answer"]["part_answers"][0]["part_id"], "a")

    def test_string_part_answers_coerced_to_dicts(self):
        import catalog

        item = {
            "status": "OK",
            "item_type": "structured_parts",
            "stem": "Ice and steam.",
            "parts": [
                {"id": "a", "text": "Ice melting point?", "marks": 1},
                {"id": "b", "text": "Water boiling point?", "marks": 1},
            ],
            "answer": {"kind": "part_answers", "part_answers": ["0 °C", "100 °C"]},
        }
        flat = catalog.normalize_result_shape(item)
        self.assertEqual(
            [p["part_id"] for p in flat["answer"]["part_answers"]],
            ["a", "b"],
        )
        self.assertEqual(flat["answer"]["part_answers"][0]["answer"], "0 °C")
        self.assertEqual(flat["answer"]["part_answers"][1]["answer"], "100 °C")

    def test_part_answer_text_field_becomes_answer(self):
        import catalog

        item = {
            "status": "OK",
            "item_type": "structured_parts",
            "stem": "A saucepan.",
            "parts": [
                {"id": "a", "text": "Base material?", "marks": 1},
                {"id": "b", "text": "Handle material?", "marks": 1},
            ],
            "answer": {
                "kind": "part_answers",
                "part_answers": [
                    {"part_id": "a", "text": "metal"},
                    {"part_id": "b", "text": "wood"},
                ],
            },
        }
        flat = catalog.normalize_result_shape(item)
        self.assertEqual(flat["answer"]["part_answers"][0]["answer"], "metal")
        self.assertEqual(flat["answer"]["part_answers"][1]["answer"], "wood")

    def test_part_answer_answer_text_field_becomes_answer(self):
        import catalog

        item = {
            "status": "OK",
            "item_type": "structured_parts",
            "stem": "Copper wires.",
            "parts": [{"id": "a", "text": "Judge the claim.", "marks": 2}],
            "answer": {
                "kind": "part_answers",
                "part_answers": [{"part_id": "a", "answer_text": "Correct. Copper conducts."}],
            },
        }
        flat = catalog.normalize_result_shape(item)
        self.assertEqual(
            flat["answer"]["part_answers"][0]["answer"],
            "Correct. Copper conducts.",
        )

    def test_already_flat_unchanged(self):
        import run as mint_run

        flat = {
            "schema": "modify_result.v1",
            "status": "OK",
            "item_type": "single_mcq",
            "stem": "A lamp is in a loop.",
            "options": [],
            "answer": {"kind": "single_letter", "letter": "B"},
        }
        self.assertEqual(mint_run.unwrap_writer_item(flat)["stem"], "A lamp is in a loop.")


if __name__ == "__main__":
    unittest.main()
