#!/usr/bin/env python3
"""Coverage picker and TOP bank gate on representative hinge and cell counts."""
from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import bank_gate  # noqa: E402
import middle_schedule as ms  # noqa: E402


def _unit(uid, zone, grade=7, subject="science"):
    return {
        "unit_id": uid,
        "node": "N",
        "subject": subject,
        "grade": grade,
        "decision": "Decide.",
        "zone": list(zone),
    }


class CoveragePickerTests(unittest.TestCase):
    def test_top_overlay_eligible_medium_and_low_are_not(self):
        top = {
            "miqg": {"tier": "TOP"},
            "jev_taxonomy": {"schema": bank_gate.OVERLAY_SCHEMA},
        }
        medium = {
            "miqg": {"tier": "MEDIUM"},
            "jev_taxonomy": {"schema": bank_gate.OVERLAY_SCHEMA},
        }
        low = {
            "miqg": {"quality_tier": "LOW"},
            "jev_taxonomy": {"schema": bank_gate.OVERLAY_SCHEMA},
        }
        self.assertTrue(bank_gate.bank_append_eligible(top))
        self.assertFalse(bank_gate.bank_append_eligible(medium))
        self.assertFalse(bank_gate.bank_append_eligible(low))

    def test_next_pick_is_empty_hinge_and_higher_in_zone_cell(self):
        dense = _unit("u-dense", ["An.Pr.3", "U.Co.2"])
        empty = _unit("u-empty", ["U.Co.2", "An.Pr.3", "Ev.Co.2"])
        by_hinge = Counter({"u-dense": 4, "u-empty": 0})
        by_cell = Counter({("u-empty", "U.Co.2"): 0, ("u-dense", "An.Pr.3"): 2})
        picks = ms.next_picks([dense, empty], by_hinge, by_cell, {}, n=1)
        self.assertEqual(picks, [("u-empty", "An.Pr.3")])

    def test_repeated_failure_skips_that_coordinate(self):
        unit = _unit("u-empty", ["An.Pr.3", "U.Co.2"])
        skips = {ms.skip_key("u-empty", "An.Pr.3"): ms.FAIL_LIMIT}
        picks = ms.next_picks([unit], Counter(), Counter(), skips, n=1)
        self.assertEqual(picks, [("u-empty", "U.Co.2")])

    def test_wave_includes_both_subjects(self):
        science = _unit("science/grade_06/ch_01/H001", ["An.Pr.3"], subject="science")
        maths = _unit("math/grade_06/ch_10/H011", ["An.Co.4"], subject="maths")
        picks = ms.next_picks([science, maths], Counter(), Counter(), {}, n=2)
        self.assertEqual(
            picks,
            [("science/grade_06/ch_01/H001", "An.Pr.3"), ("math/grade_06/ch_10/H011", "An.Co.4")],
        )

    def test_repeated_dok4_abandons_move_the_picker_down(self):
        units = [
            _unit("u1", ["An.Pr.4", "An.Pr.3"]),
            _unit("u2", ["Ev.Co.4", "U.Co.2"]),
        ]
        skips = {
            ms.skip_key("a", "An.Co.4"): 1,
            ms.skip_key("b", "An.Fa.4"): 1,
            ms.skip_key("c", "Ev.Pr.4"): 1,
            ms.skip_key("d", "Cr.Co.4"): 1,
        }
        picks = ms.next_picks(units, Counter(), Counter(), skips, n=1)
        self.assertEqual(picks, [("u1", "An.Pr.3")])
        also = dict(skips)
        also.update({
            ms.skip_key("e", "An.Co.3"): 1,
            ms.skip_key("f", "An.Pr.3"): 1,
            ms.skip_key("g", "Ev.Co.3"): 1,
            ms.skip_key("h", "Ap.Co.3"): 1,
        })
        still = ms.next_picks([_unit("u3", ["An.Co.3", "U.Co.2"])], Counter(), Counter(), also, n=1)
        self.assertEqual(still, [("u3", "An.Co.3")])

    def test_one_failure_is_not_the_immediate_next_pick(self):
        unit = _unit("u-empty", ["An.Pr.3", "Ev.Co.2"])
        skips = {ms.skip_key("u-empty", "An.Pr.3"): 1}
        picks = ms.next_picks([unit], Counter(), Counter(), skips, n=1)
        self.assertEqual(picks, [("u-empty", "Ev.Co.2")])

    def test_sanitized_zone_field_is_read(self):
        units = ms.units_from_maps(
            {"hinges": [{
                "unit_id": "sci/H1",
                "grade": 7,
                "decision": "Decide the state.",
                "zone": {"admitted": ["An.Co.2"], "noul": {"An.Co.2": 0.7}},
            }]},
            {"hinges": []},
        )
        self.assertEqual(units[0]["unit_id"], "sci/H1")
        self.assertEqual(units[0]["zone"], ["An.Co.2"])


if __name__ == "__main__":
    unittest.main()
