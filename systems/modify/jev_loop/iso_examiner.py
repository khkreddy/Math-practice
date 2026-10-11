"""ISO Family 2 examiner for Modify: independent solve of stem+TikZ, blind of rationale.

Must not consume only author artifacts. Packed key and key_rationale stay out of state.
Disagreement with the packed letter becomes KEY_WRONG (already a G17 counting DQ).
"""
from __future__ import annotations

from copy import deepcopy

import v5_lock
from catalog import as_float, as_text, parse_code


def letters_of(item: dict) -> list[str]:
    out = []
    for o in item.get("options") or []:
        if isinstance(o, dict) and o.get("id"):
            out.append(str(o["id"]))
    return out


def examiner_questions(letters: list[str]) -> dict:
    criteria = {L: "Option %s is the unique answer warranted by stem and figure." % L for L in letters}
    criteria["unsolved"] = (
        "No unique letter is warranted: the figure and stem disagree, "
        "or more than one option is equally supported."
    )
    return {
        "independent_key": {
            "type": "choice",
            "instructions": (
                "Solve the sitting item from stem, options, and TikZ only. "
                "Do not use any author key, rationale, or tikz_delta. "
                "If the drawing does not uniquely support one option, choose unsolved."
            ),
            "criteria": criteria,
        },
        "figure_load_bearing": {
            "type": "noul",
            "instructions": (
                "Must the learner read the TikZ to choose the key? "
                "Yes only if changing the figure would change the key."
            ),
        },
        "stem_figure_agree": {
            "type": "noul",
            "instructions": (
                "Do the stem's claims about the figure match the TikZ? "
                "Yes only if every named object and quantitative claim is true of the drawing."
            ),
        },
    }


def examiner_state(item: dict, req: dict | None = None) -> dict:
    opts = []
    for o in item.get("options") or []:
        if isinstance(o, dict):
            opts.append({"id": o.get("id"), "text": o.get("text")})
    tikz = v5_lock.tikz_of(item)
    st = {
        "role": "iso_family2_examiner",
        "blind_of_author_rationale": True,
        "do_not_use_author_key": True,
        "item_type": item.get("item_type"),
        "stem": item.get("stem"),
        "options": opts,
        "tikz": tikz,
        "subject": (req or {}).get("subject"),
        "grade": (req or {}).get("grade") or (req or {}).get("grade_band"),
    }
    return st


def packed_letter(item: dict) -> str | None:
    ans = item.get("answer") or {}
    if isinstance(ans, str) and len(ans) == 1:
        return ans
    if ans.get("kind") == "single_letter":
        return ans.get("letter")
    if ans.get("letter"):
        return ans.get("letter")
    return None


def parse_exam(answers: dict, letters: list[str]) -> dict:
    key = parse_code(as_text(answers.get("independent_key")), letters + ["unsolved"])
    load = as_float(answers.get("figure_load_bearing"))
    agree = as_float(answers.get("stem_figure_agree"))
    return {
        "independent_key": key,
        "figure_load_bearing": load,
        "stem_figure_agree": agree,
    }


def extra_findings(exam: dict, item: dict, variation: str = "") -> list[dict]:
    packed = packed_letter(item)
    got = exam.get("independent_key")
    findings = []
    if got and got != "unsolved" and packed and got != packed:
        findings.append({
            "code": "KEY_WRONG",
            "severity": "DQ",
            "gate_id": "V1",
            "quoted_text": "examiner=%s packed=%s" % (got, packed),
            "location": "answer",
            "status": "CONFIRMED",
            "merged_into": None,
        })
    if got == "unsolved" and as_float(exam.get("stem_figure_agree")) < 0.50:
        findings.append({
            "code": "FIGURE_STEM_CONFLICT",
            "severity": "DQ",
            "gate_id": "V8",
            "quoted_text": "examiner unsolved; stem_figure_agree=%.2f" % as_float(exam.get("stem_figure_agree")),
            "location": "tikz",
            "status": "CONFIRMED",
            "merged_into": None,
        })
    return findings


def v5_load_bearing_fail(exam: dict, variation: str, has_tikz: bool) -> str | None:
    if not has_tikz or variation != "V5":
        return None
    if as_float(exam.get("figure_load_bearing")) < 0.50:
        return "V5 figure is not load-bearing (examiner noul %.2f)" % as_float(exam.get("figure_load_bearing"))
    return None


def run(jev_call, key: str, item: dict, req: dict | None = None) -> dict:
    letters = letters_of(item)
    st = examiner_state(item, req)
    q = examiner_questions(letters)
    resp = jev_call(key, st, q)
    parsed = parse_exam(resp.get("answers") or {}, letters)
    rec = deepcopy(parsed)
    rec["usage"] = resp.get("usage")
    rec["answers"] = resp.get("answers")
    rec["state_keys"] = list(st.keys())
    rec["author_key_in_state"] = False
    rec["extra_findings"] = extra_findings(parsed, item, ((req or {}).get("variation_class")) or "")
    rec["load_bearing_fail"] = v5_load_bearing_fail(
        parsed,
        ((req or {}).get("variation_class")) or ((item.get("teacher") or {}).get("variation_applied")) or "",
        bool(v5_lock.tikz_of(item).strip()),
    )
    return rec
