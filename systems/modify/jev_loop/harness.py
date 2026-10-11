"""Modify harness: T-MINT situation, then T-MOD distractors.

T-MINT studies the hinge packet and writes the situation and the expected
answer. T-MOD receives that sitting item and writes the wrong options, or the
wrong paths of a free-response question. Neither step pastes a stored mix-up
sentence into the candidate text.
"""
from __future__ import annotations

from pathlib import Path


def generate(req: dict, dictionary: dict, out: Path, draft: dict | None = None) -> dict:
    """Run T-MINT, then T-MOD, on one requirement.

    A user_situation on the requirement is the scene. Otherwise T-MINT must
    choose a situation that is not already built for the hinge. Companion
    hinge ids are hinges the situation may combine with the center.
    """
    import run as tmint

    trail = tmint.mint(req, dictionary, Path(out), draft)
    trail["workflow"] = ["T-MINT", "T-MOD"]
    return trail
