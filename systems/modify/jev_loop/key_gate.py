#!/usr/bin/env python3
"""Independent key gate for T-MINT and T-MOD.

The sitting stem is solved without seeing the proposed key. The proposed key
must equal that independent result. A general hinge rule that the stem's
conditions block is not the answer. Fail closed.
"""
from __future__ import annotations

import re

from route_derive import _bare_claim, _norm

DOWN = re.compile(
    r"\b(?:decrease|decreases|decreased|lower|less|smaller|drop|drops|falls|reduce|reduces)\b",
    re.I,
)
UP = re.compile(
    r"\b(?:increase|increases|increased|higher|more|greater|rise|rises|raise|raises)\b",
    re.I,
)
SAME = re.compile(
    r"\b(?:stay|stays|remain|remains|same|unchanged|constant|fixed|no change|does not change|do not change)\b",
    re.I,
)
POLAR_STOP = re.compile(
    r"\b(?:the|a|an|of|to|and|or|in|for|its|their|this|that|"
    r"decrease|decreases|decreased|lower|less|smaller|drop|drops|falls|reduce|reduces|"
    r"increase|increases|increased|higher|more|greater|rise|rises|raise|raises|"
    r"stay|stays|remain|remains|same|unchanged|constant|fixed|change|changes|"
    r"does|do|not|no)\b",
    re.I,
)


def proposed_key(item: dict) -> str:
    """Bare keyed claim from a T-MINT situation or a T-MOD sitting item."""
    if not isinstance(item, dict):
        return ""
    teacher = item.get("teacher") if isinstance(item.get("teacher"), dict) else {}
    text = str(teacher.get("expected_answer") or item.get("expected_answer") or "").strip()
    answer = item.get("answer") if isinstance(item.get("answer"), dict) else {}
    letter = str(answer.get("letter") or "").strip().upper()[:1]
    if letter:
        options = item.get("options")
        if isinstance(options, list):
            for index, raw in enumerate(options):
                if isinstance(raw, dict):
                    token = str(raw.get("id") or chr(65 + index)).strip().upper()[:1]
                    if token == letter:
                        text = str(raw.get("text") or text).strip() or text
                elif letter == chr(65 + index):
                    text = str(raw).strip() or text
        elif isinstance(options, dict) and options.get(letter):
            raw = options.get(letter)
            text = str(raw.get("text") if isinstance(raw, dict) else raw).strip() or text
    if not text:
        text = str(answer.get("rubric") or answer.get("pattern") or "").strip()
    return _bare_claim(text) or text


def _polarity(text: str) -> str:
    raw = str(text or "")
    marks = []
    if DOWN.search(raw):
        marks.append("down")
    if UP.search(raw):
        marks.append("up")
    if SAME.search(raw):
        marks.append("same")
    if len(marks) == 1:
        return marks[0]
    return ""


def _core(text: str) -> set[str]:
    tokens = POLAR_STOP.sub(" ", _norm(text)).split()
    return {tok for tok in tokens if len(tok) > 1}


def results_match(proposed: str, independent: str) -> bool:
    """True when the proposed key is the independent result of this stem."""
    left = _bare_claim(proposed) or str(proposed or "").strip()
    right = _bare_claim(independent) or str(independent or "").strip()
    if not left or not right:
        return False
    if _norm(left) == _norm(right):
        return True
    polar_l, polar_r = _polarity(left), _polarity(right)
    if polar_l and polar_r and polar_l != polar_r:
        return False
    a, b = _norm(left), _norm(right)
    if a and b and (a in b or b in a) and (not polar_l or not polar_r or polar_l == polar_r):
        return True
    core_l, core_r = _core(left), _core(right)
    if core_l and core_r and (core_l <= core_r or core_r <= core_l):
        if polar_l and polar_r:
            return polar_l == polar_r
        if polar_l or polar_r:
            return False
        return True
    return False


def prompt_for(item: dict, unit: dict | None, req: dict | None = None) -> str:
    """Solve the stem alone. Do not show the proposed key."""
    req = req or {}
    unit = unit if isinstance(unit, dict) else {}
    stem = str((item or {}).get("stem") or "").strip()
    decision = str(unit.get("decision") or unit.get("decision_do_not_print") or "").strip()
    law = str(unit.get("law") or unit.get("law_do_not_copy") or "").strip()
    return (
        "Return JSON only: status, independent_result.\n"
        "Grade "
        + str(req.get("grade") or "")
        + " "
        + str(req.get("subject") or "")
        + ".\n"
        "Solve this question situation. independent_result is the bare result this stem requires.\n"
        "Apply the hinge to the quantities and conditions already in the stem. "
        "A general rule does not apply when a given condition blocks it "
        "(for example volume cannot change, mass cannot leave, a value is already fixed).\n"
        "Do not write a because-clause. Do not invent a different scene.\n"
        "Stem:\n"
        + stem
        + "\n"
        + ("Hinge decision (teacher-side, do not print): " + decision[:400] + "\n" if decision else "")
        + ("Hinge law (teacher-side, do not copy into the result): " + law[:400] + "\n" if law else "")
    )


def check(item: dict, unit: dict | None, writer, req: dict | None = None) -> dict:
    """Run the independent solve. status PASS or REFUSED. Fail closed."""
    proposed = proposed_key(item)
    if not proposed:
        return {"status": "REFUSED", "reason": "no proposed key", "proposed": "", "independent_result": ""}
    if not str((item or {}).get("stem") or "").strip():
        return {"status": "REFUSED", "reason": "no question situation", "proposed": proposed, "independent_result": ""}
    try:
        raw = writer(prompt_for(item, unit, req))
    except Exception as exc:
        return {
            "status": "REFUSED",
            "reason": "key check writer: " + type(exc).__name__ + ": " + str(exc)[:160],
            "proposed": proposed,
            "independent_result": "",
        }
    body = raw if isinstance(raw, dict) else {}
    independent = str(body.get("independent_result") or body.get("result") or "").strip()
    independent = _bare_claim(independent) or independent
    if not independent:
        return {"status": "REFUSED", "reason": "independent result missing", "proposed": proposed, "independent_result": ""}
    if not results_match(proposed, independent):
        return {
            "status": "REFUSED",
            "reason": "keyed claim is not the result this stem requires",
            "proposed": proposed,
            "independent_result": independent[:240],
        }
    return {"status": "PASS", "reason": "", "proposed": proposed, "independent_result": independent[:240]}
