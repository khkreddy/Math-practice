#!/usr/bin/env python3
"""Deterministic V5 lock tests. No JEV. Run from jev_loop: python3 -m unittest tests.test_v5_lock"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import gates  # noqa: E402
import packet  # noqa: E402
import v5_lock  # noqa: E402

TIKZ_RATE = (
    r"\begin{tikzpicture}[x=1.2cm,y=1.2cm,font=\sffamily,>=stealth]"
    r"\draw[->,thick] (0,0) -- (4.45,0); \draw[->,thick] (0,0) -- (0,3.65);"
    r"\node[below] at (0,0) {0}; \node[below] at (2.15,-0.02) {time};"
    r"\node[align=center,left] at (-0.18,1.65) {mass of\\reaction flask};"
    r"\draw[thick] (0,3.20) .. controls (0.22,1.15) and (1.35,0.48) .. (4.05,0.32);"
    r"\draw[thick,dashed] (0,3.20) .. controls (0.65,1.45) and (1.55,0.50) .. (4.05,0.12);"
    r"\node at (1.18,1.48) {P}; \node at (0.47,0.72) {Q};"
    r"\end{tikzpicture}"
)
TIKZ_CAP = (
    r"\begin{tikzpicture}"
    r"\node[above=8pt] at (1.12,0.14) {resistor};"
    r"\node[above=9pt] at (3.595,0.31) {capacitor};"
    r"\draw (1.12,-1.0) circle (0.28) node {V};"
    r"\node[below=5pt] at (1.12,-1.28) {voltmeter 2};"
    r"\node[below=5pt] at (3.90,-1.28) {voltmeter 3};"
    r"\end{tikzpicture}"
)
TIKZ_WEB = (
    r"\begin{tikzpicture}"
    r"\node (grass) at (0,-2.0) {grass};"
    r"\node (locust) at (-1.8,-1.35) {locust};"
    r"\node (leopard) at (-0.45,1.65) {leopard};"
    r"\end{tikzpicture}"
)


def mcq(stem, letter, tikz, variation="V5"):
    return {
        "schema": "modify_result.v1",
        "status": "OK",
        "item_type": "single_mcq",
        "stem": stem,
        "options": [
            {"id": "A", "text": "Option A statement."},
            {"id": "B", "text": "Option B statement."},
            {"id": "C", "text": "Option C statement."},
            {"id": "D", "text": "Option D statement."},
        ],
        "statements": [],
        "parts": [],
        "tikz": tikz,
        "tables": [],
        "answer": {"kind": "single_letter", "letter": letter},
        "teacher": {
            "proposed_key_status": "UNVERIFIED",
            "variation_applied": variation,
            "fidelity_selfcheck": "test",
            "key_rationale": "not evidence",
        },
    }


class BindTests(unittest.TestCase):
    def test_marble_q_is_solid_steeper_p_is_dashed_lower(self):
        bound = v5_lock.bind_labels(TIKZ_RATE)
        self.assertEqual(bound["Q"]["style"], "solid")
        self.assertEqual(bound["P"]["style"], "dashed")
        self.assertLess(bound["Q"]["initial_slope"], bound["P"]["initial_slope"])
        self.assertLess(bound["P"]["end_y"], bound["Q"]["end_y"])

    def test_marble_stem_pins_both_features_on_q(self):
        stem = (
            "Marble chips react with hydrochloric acid in a flask. The diagram is mass of flask against time "
            "for runs P and Q. Q falls faster at first and finishes at a lower mass."
        )
        hits = v5_lock.g3c_label_stroke(stem, TIKZ_RATE, "Dashed curve Q now finishes lower.")
        codes = {h["code"] for h in hits}
        self.assertIn("SERIES_CLAIM_CONFLICT", codes)
        self.assertIn("LABEL_STROKE_MISMATCH", codes)

    def test_honest_marble_passes_bind(self):
        stem = (
            "The diagram shows mass against time for runs P and Q. "
            "Q falls faster at first. P finishes at a lower mass."
        )
        hits = v5_lock.g3c_label_stroke(stem, TIKZ_RATE, "Dashed curve is P; solid curve is Q.")
        self.assertEqual(hits, [])


class G3bTests(unittest.TestCase):
    def test_capacitor_voltmeter_1_absent_without_followup(self):
        stem = (
            "The circuit in the diagram was connected. "
            "Voltmeter 1 (across the switch) has been taken out."
        )
        hits = v5_lock.g3b_stem_objects(stem, TIKZ_CAP, packet={"spec": {"figure": {"mode": "rewrite"}}})
        self.assertTrue(any(h["object"].lower().startswith("voltmeter 1") for h in hits))

    def test_capacitor_followup_allows_named_removal(self):
        stem = (
            "The circuit in the diagram was connected. "
            "Voltmeter 1 (across the switch) has been taken out."
        )
        pkt = {"spec": {"figure": {"mode": "rewrite", "lbs_followup_of": "0625_m15_qp_12:q32"}}}
        hits = v5_lock.g3b_stem_objects(stem, TIKZ_CAP, packet=pkt)
        self.assertEqual(hits, [])

    def test_foodweb_impala_absent_without_followup(self):
        stem = "The diagram is a food web after the impala pathway has been removed."
        hits = v5_lock.g3b_stem_objects(stem, TIKZ_WEB, packet={"spec": {"figure": {"mode": "rewrite"}}})
        self.assertTrue(any("impala" in h["object"].lower() for h in hits))


class DeltaTests(unittest.TestCase):
    def test_v5_identical_tikz_fails(self):
        hits = v5_lock.g3d_declared_delta(TIKZ_RATE, TIKZ_RATE, "change the finish", "V5", "rewrite")
        self.assertTrue(hits)

    def test_enthalpy_sign_flip_mentioned(self):
        src = r"\node {R}; \draw[->] node {$\Delta H=-134$} ;"
        dst = r"\node {R}; \draw[->] node {$\Delta H=+134$} ;"
        hits = v5_lock.g3d_declared_delta(src, dst, "flipped from -134 to +134", "V5", "rewrite")
        self.assertEqual(hits, [])

    def test_enthalpy_change_unmentioned_fails(self):
        src = r"\node {R}; \draw[->] node {$\Delta H=-134$} ;"
        dst = r"\node {R}; \draw[->] node {$\Delta H=+134$} ;"
        hits = v5_lock.g3d_declared_delta(src, dst, "figure unchanged", "V5", "rewrite")
        self.assertTrue(hits)


class GateStackTests(unittest.TestCase):
    def test_broken_marble_fails_closed(self):
        src = {"item_type": "single_mcq", "stem": "The diagram.", "tikz": TIKZ_RATE, "options": {"A": "a", "B": "b", "C": "c", "D": "d"}, "answer": {"kind": "single_letter", "letter": "B"}}
        pkt = packet.assemble_modify_packet(
            src,
            "rewrite the finish",
            variation_class="V5",
            figure_mode="rewrite",
            declared_delta="Dashed curve Q now finishes lower.",
        )
        out = mcq(
            "The diagram is mass against time for runs P and Q. Q falls faster at first and finishes at a lower mass.",
            "B",
            TIKZ_RATE,
        )
        gate = gates.apply_outcome(out, pkt, src)
        self.assertFalse(gate["ok"])
        self.assertIn(gate["gate"], {"G3b", "G3c"})

    def test_prose_item_unaffected(self):
        src = {
            "item_type": "single_mcq",
            "stem": "A cart rolls on a track. A class wants to check which force account is warranted.",
            "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
            "answer": {"kind": "single_letter", "letter": "B"},
        }
        pkt = packet.assemble_modify_packet(src, "new numbers", variation_class="V3", figure_mode="preserve")
        out = mcq(
            "A cart rolls on a track. A class wants to check which force account is warranted.",
            "B",
            "",
            variation="V3",
        )
        gate = gates.validate(out, pkt, src)
        self.assertTrue(gate["ok"], gate)


if __name__ == "__main__":
    unittest.main()
