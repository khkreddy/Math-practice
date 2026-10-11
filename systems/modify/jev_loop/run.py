#!/usr/bin/env python3
"""T-MINT: requirement in → JEV plan → situation and expected answer → T-MOD distractors → G17 → classify → G18.

T-MINT does not write wrong options. It studies the hinge packet and chooses a
situation, then states the expected answer or the mechanism that reaches it.
T-MOD completes the distractors. See harness.generate.
API keys stay in the environment. Fail closed. Do not auto-rewrite after a near-miss noul.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import zlib
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODIFY = HERE.parent
TTWIN_ROOT = MODIFY.parent.parent

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(MODIFY / "miqg"))

from catalog import (  # noqa: E402
    construct_brief,
    design_questions,
    lock_item_type,
    pack_tag,
    parse_plan,
    taxonomy_questions,
    utc_now,
)
from jev_client import load_jev_key, jev_call, MODEL, JEV_URL  # noqa: E402
import miqg_cal  # noqa: E402
import gates  # noqa: E402
import iso_examiner  # noqa: E402
import packet as modify_packet  # noqa: E402
import v5_lock  # noqa: E402
import human_review  # noqa: E402
import unit_bind  # noqa: E402
import situation as sit_stage  # noqa: E402

SHIP_G18 = {"PASS", "PASS_NEIGHBOUR", "PASS_ZONE"}
LEARNED = (
    "SPC actions:\n"
    "- Build one decision: give a contrast, readings, or a result the student must interpret, then ask which claim that evidence supports.\n"
    "- Do not state the relation, the formula, or the steps and then ask for them. A task that puts given numbers directly into a stated or named relation is DoK 1.\n"
    "- When a name, label, or formula would turn the task into a direct substitution, withhold it and give the measurements it stood for, so the student must work out what was withheld before using it.\n"
    "- Write a stem readable in one pass that says what each label, symbol, or record is, and make each option one full claim with no word doing two jobs.\n"
    "- Use figure or diagram words only when the item includes tikz or a table, and do not reuse an 8-word span, the same three quantities, or the same scene from an item already on this hinge.\n"
    "- A single-key item uses answer.letter. Part answers are full sentences.\n"
    "- For one_or_more, answer.letters must list at least two correct options. A single correct option is a single_mcq.\n"
    "- The Reason must apply a principle to the scene. Do not let the Reason repeat the Assertion in different words.\n"
)

FORMAT_MENU = """item_type MUST be one of: single_mcq, one_or_more, three_statement, structured_parts, open_response, option_table, options_are_figure. Choose by the evidence the cell needs, and set item_type to the menu type that makes this cell observable. If the JEV plan says proceed_mcq, treat it as a suggestion, not a lock. Never pick a format for variety.
Format menu (format → item_type → answer kind):
- Single-key choice → single_mcq → single_letter. Use when one claim among close alternatives is enough evidence. The number of options follows the real plausible alternatives and is not fixed at four.
- Assertion-reason → single_mcq → single_letter. Use when the cell is a causal link. Use exactly the five standard relation options and nothing else: (A) Both Assertion and Reason are true, and the Reason correctly explains the Assertion. (B) Both Assertion and Reason are true, but the Reason does not correctly explain the Assertion. (C) The Assertion is true, but the Reason is false. (D) The Assertion is false, but the Reason is true. (E) Both Assertion and Reason are false.
- Multi-select → single_mcq → single_letter. List the claims in the stem as I, II, III. Each option is one combination of those labels, such as "I and II" or "I, III, and V". Exactly one option is the full set of supported claims. Every other option adds at least one unsupported claim, and that option cites the mix-up of the unsupported claim it adds.
- Multiple true-false → three_statement → statement_pattern. Use when each statement is itself diagnostic.
- Answer-plus-reason → option_table → single_letter. Each row pairs an answer with a reason. Use when a correct pick without a reason would be misleading and the wrong reasons are known. If the student must produce the reason instead of picking it, use structured_parts.
- Reasoning chain → structured_parts → part_answers. Use tiers only to show a reasoning chain, such as a multi-step computation whose intermediate value is the evidence.
- Numeric entry → open_response → rubric. Use when the work is a computation or when options would cue the answer. The rubric gives the accepted value, unit, and tolerance.
- Short explanation or error repair → open_response → rubric. Use when the next action is to see the fault. The rubric states what a correct answer must identify or fix.
- Figure options → options_are_figure → single_letter. Use when the alternatives can only be told apart as figures. Use figure or diagram words only when tikz or a table is attached.
One scaffold only: never put an option list and a tier breakdown on the same item.
This is a starting menu, not a closed set. A new format may be used only when no listed format makes the cell observable, and it must still map to one of the seven item_type values and one of the listed answer kinds above.
"""

ALLOWED_ITEM_TYPES = {
    "single_mcq",
    "one_or_more",
    "three_statement",
    "structured_parts",
    "open_response",
    "option_table",
    "options_are_figure",
}

# Writer craft points at grok_4_7/04_GROK_SLOT (compose for a reader from map/packet
# facts). Modify uses packet-first (09_PACKET_MODIFY) — never slice the old stem
# into givens/registration rows. Release gate: MIQG only (TOP / release_gate PASS).
CRAFT = """Grok slot rules (systems/modify/grok_4_7/04_GROK_SLOT) — wording only:
- Compose one concrete situation plus exactly one question, or a single imperative with the command word. Not two asks.
- No syllabus / specification / learning-objective sentence. No tutor voice (let's, think about, can you, hint, recall that).
- Do not state or paraphrase the keyed answer in the stem.
- Do not print registration templates or 'X is recorded as Y' / 'identity of the aim' costumes.
- No named-child or city dressing (Ravi, Priya, Meera, Pune, Delhi, ...).
- No catch-all options. No 'this is wrong because' / 'by reversing' / 'confuses' recipes.
- Options are complete answer-statements of the same answer-type as the key, not boolean flags and not descriptions of a mistake.
- Do not name the misconception type in the stem.
- Do not refer to a figure or table unless you attach tikz/tables (figure asset required before spatial phrasing).
- Learner fields must not contain mx_type names, CANDIDATE, or vendor names.
- Public UI says AI; do not name a vendor in the item.
"""


def find_dictionary(cli: str | None) -> Path:
    if cli:
        p = Path(cli)
        if p.is_file():
            return p
        raise SystemExit("construct dictionary not found: " + cli)
    for p in (
        TTWIN_ROOT / "data" / "intelligence" / "construct_dictionary.json",
        Path("/home/harik/TTwin-final/data/intelligence/construct_dictionary.json"),
        Path("/mnt/d/Hari HP/awm_build/data/intelligence/construct_dictionary.json"),
    ):
        if p.is_file():
            return p
    raise SystemExit("construct_dictionary.json not found; pass --dictionary")


def band_of(grade: int) -> str:
    if 6 <= grade <= 8:
        return "middle_6_8"
    if 9 <= grade <= 10:
        return "secondary_9_10"
    if 11 <= grade <= 13:
        return "senior_11_12"
    return "middle_6_8"


def append_jsonl(path: Path, rec: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def classify_state(item: dict, req: dict) -> dict:
    opts = []
    for o in item.get("options") or []:
        if isinstance(o, dict):
            opts.append({"id": o.get("id"), "text": o.get("text")})
    parts = []
    for p in item.get("parts") or []:
        parts.append(
            {
                "id": p.get("id"),
                "prompt": p.get("text") or p.get("prompt") or "",
                "marks": p.get("marks"),
            }
        )
    tikz = item.get("tikz")
    if isinstance(tikz, list):
        tikz = "\n".join(str(x) for x in tikz)
    st = {
        "role": "unbiased_construct_classifier",
        "do_not_use_author_target": True,
        "item_type": item.get("item_type"),
        "stem": item.get("stem"),
        "options": opts,
        "parts": parts,
        "key": item.get("answer"),
        "subject": req.get("subject"),
        "grade": req.get("grade"),
        "hinge_id": req.get("hinge_id"),
        "hinge_title": req.get("hinge_title"),
        "has_tikz": bool(str(tikz or "").strip()),
    }
    if str(tikz or "").strip():
        st["tikz"] = str(tikz)
    return st


def plan_state(req: dict, d: dict, unit: dict | None = None) -> dict:
    task = (
        "Guide design of one sitting item on this unit. Do not write the stem. "
        "If the TARGET cell is not an honest demand of this decision, choose abandon_cell. "
        "Do not retarget the cell."
    )
    if (req.get("grade_band") or "") == "secondary_9_10":
        task += (
            " When a single sitting item can carry this target, name the format that makes the cell observable. "
            "Do not abandon when the honest cell is the target itself. "
            "One decision. Do not require a four-option question."
        )
    state = {
        "role": "item_design_planner",
        "task": task,
        "grade_band": req.get("grade_band") or band_of(int(req["grade"])),
        "subject": req["subject"],
        "grade": req["grade"],
        "hinge_id": req["hinge_id"],
        "hinge_title": req.get("hinge_title"),
        "target_construct": construct_brief(d, req["target_construct"]),
        "quality_bar": (
            "MIQG-v1.0-rc9-CAL-KNGOOD TOP: no named-child padding, no catch-all, "
            "no distractor recipes, no missing figure referent, stem has scene-plus-purpose. "
            "Do not print the method. Do not explain the phenomenon and then ask for that explanation."
        ),
        "author_intent": _intent_for_prompt(req.get("intent") or "", (unit or {}).get("decision") or ""),
    }
    if unit:
        lines = select_mx(unit, req)
        state["unit"] = {
            "unit_id": unit.get("unit_id"),
            "decision": unit.get("decision"),
            "law": unit.get("law"),
            "boundaries": unit.get("boundaries") or [],
            "zone": sorted(unit.get("zone") or []),
            "mx": lines,
        }
        if _repeats(req.get("hinge_title"), unit.get("decision")):
            state["hinge_title"] = ""
    return state


def to_result(item: dict) -> dict:
    parts = []
    for p in item.get("parts") or []:
        q = deepcopy(p)
        if "text" not in q and q.get("prompt"):
            q["text"] = q.pop("prompt")
        parts.append(q)
    return {
        "schema": "modify_result.v1",
        "status": item.get("status") or "OK",
        "item_type": item["item_type"],
        "stem": item.get("stem") or "",
        "options": item.get("options") or [],
        "statements": item.get("statements") or [],
        "parts": parts,
        "tikz": item.get("tikz"),
        "tables": item.get("tables") or [],
        "answer": item.get("answer") or {},
        "teacher": {
            "proposed_key_status": "UNVERIFIED",
            "variation_applied": item.get("variation_applied") or "V3",
            "fidelity_selfcheck": "T-MINT; hinge bound; learner fields only in stem/options/parts.",
            "key_rationale": (item.get("key_rationale") or item.get("teacher", {}).get("key_rationale") or "")[:500],
        },
        "mx_option_map": item.get("mx_option_map") or {},
    }


def g17(item: dict, req: dict, extra_findings: list | None = None, packet: dict | None = None) -> dict:
    result = to_result(item)
    meta = {
        "id": req.get("requirement_id") or "t-mint",
        "subject": req.get("subject"),
        "grade": req.get("grade"),
        "chapter": req.get("chapter"),
        "hinge_id": req.get("hinge_id"),
        "hinge": req.get("hinge_title"),
        "uid": req.get("requirement_id"),
    }
    packet = packet or {
        "intelligence": {
            "hinge": {
                "title": req.get("hinge_title"),
                "decision_hinge": req.get("hinge_title"),
                "primary": req.get("hinge_id"),
            }
        }
    }
    row = miqg_cal.evaluate_result(
        result, packet=packet, meta=meta, corpus="CANDIDATE", extra_findings=extra_findings or [],
    )
    return {
        "quality_tier": row.get("quality_tier"),
        "release_gate": row.get("release_gate"),
        "decisive_reason": row.get("decisive_reason"),
        "k_major": row.get("k_major"),
        "dq_codes": row.get("dq_codes"),
        "major_codes": row.get("major_codes"),
        "flags": row.get("flags"),
        "rationale": row.get("rationale"),
        "protocol": row.get("protocol"),
    }


def g18(req: dict, plan: dict, miqg: dict, tag: dict | None, zone: set | None = None) -> dict:
    """Construct lock. G17 TOP is necessary, not sufficient.

    When zone is set, an admitted cell inside that zone is kept even if it is
    not the aim. A cell outside the zone is not stored as a neighbour.
    A miss does not ask for the same writer prompt again.
    """
    target = req["target_construct"]
    neighbour = plan.get("likely_collapse")
    accept = bool(req.get("accept_neighbour"))
    if (miqg.get("quality_tier") or "") != "TOP":
        return {
            "gate": "G18",
            "status": "BLOCK" if miqg.get("release_gate") == "BLOCK" else (miqg.get("release_gate") or "HOLD"),
            "reason": "G17_NOT_TOP",
            "construct_hit": False,
            "retry_same_prompt": False,
        }
    if not tag or not tag.get("admitted"):
        return {
            "gate": "G18",
            "status": "CONSTRUCT_HOLD",
            "reason": "JEV_NOT_ADMITTED",
            "construct_hit": False,
            "retry_same_prompt": False,
            "unresolved_coord": (tag or {}).get("unresolved_coord"),
        }
    cid = tag.get("construct_id")
    if zone is not None and cid not in zone:
        return {
            "gate": "G18",
            "status": "CONSTRUCT_HOLD",
            "reason": "CELL_OUTSIDE_ZONE",
            "construct_hit": False,
            "admitted_as": cid,
            "retry_same_prompt": False,
        }
    if cid == target:
        return {
            "gate": "G18",
            "status": "PASS",
            "reason": "TARGET_ADMITTED",
            "construct_hit": True,
            "retry_same_prompt": False,
        }
    if zone is not None and cid in zone:
        return {
            "gate": "G18",
            "status": "PASS_ZONE",
            "reason": "ZONE_ADMITTED",
            "construct_hit": True,
            "aim_missed": True,
            "admitted_as": cid,
            "retry_same_prompt": False,
        }
    if accept and neighbour and cid == neighbour:
        return {
            "gate": "G18",
            "status": "PASS_NEIGHBOUR",
            "reason": "NEIGHBOUR_ADMITTED",
            "construct_hit": True,
            "admitted_as": cid,
            "retry_same_prompt": False,
        }
    return {
        "gate": "G18",
        "status": "CONSTRUCT_HOLD",
        "reason": "CELL_MISMATCH",
        "construct_hit": False,
        "admitted_as": cid,
        "retry_same_prompt": False,
    }


def _norm_text(value) -> str:
    return " ".join(str(value or "").split()).strip().rstrip(".").lower()


def _repeats(left, right) -> bool:
    a, b = _norm_text(left), _norm_text(right)
    return bool(a and b and (a == b or a in b or b in a))


def _intent_for_prompt(intent, decision: str) -> str:
    text = str(intent or "").strip()
    marker = "Unit statement:"
    at = text.find(marker)
    if at < 0:
        return text
    rest = text[at + len(marker):].strip()
    scope = ""
    cut = rest.find(" Out of scope:")
    statement = rest if cut < 0 else rest[:cut].strip()
    if cut >= 0:
        scope = rest[cut:].strip()
    if not _repeats(statement, decision):
        return text
    head = text[:at].strip()
    return (head + (" " + scope if scope else "")).strip()


def select_mx(unit: dict | None, req: dict) -> list[str]:
    """One mix-up line, or two when the aim is Analyze/Evaluate at DoK 3+.

    The window moves with the requirement id, so a later request on the same
    hinge does not keep receiving only the first row.
    """
    if not unit:
        return []
    lines = unit.get("mx_lines")
    if not isinstance(lines, list) or not lines:
        one = str(unit.get("mx") or "").strip()
        lines = [one] if one else []
    lines = [str(line).strip() for line in lines if str(line).strip()]
    if not lines:
        return []
    cell = str(req.get("target_construct") or "")
    parts = cell.split(".")
    dok = int(parts[-1]) if parts and parts[-1].isdigit() else 0
    want = 2 if dok >= 3 and parts[0] in {"An", "Ev"} and len(lines) > 1 else 1
    key = "\t".join([
        str(req.get("requirement_id") or ""),
        cell,
        str(req.get("hinge_id") or unit.get("unit_id") or ""),
    ])
    start = zlib.adler32(key.encode()) % len(lines)
    return [lines[(start + i) % len(lines)] for i in range(want)]


def writer_prompt(req: dict, plan: dict, item_type: str, brief: dict, unit: dict | None = None) -> str:
    form = plan.get("recommended_form")
    decision = (unit or {}).get("decision") or ""
    title = req.get("hinge_title") or ""
    repeated = bool(unit) and _repeats(title, decision)
    if unit and repeated:
        head = f"Grade {req.get('grade')} {req.get('subject')}. Unit {unit.get('unit_id')}.\n"
    else:
        head = (
            f"Grade {req.get('grade')} {req.get('subject')}. "
            f"Hinge {req.get('hinge_id')} — {title}.\n"
        )
    unit_block = ""
    if unit:
        bounds = "; ".join(unit.get("boundaries") or [])
        mx_block = ""
        records = unit.get("mx_records") if isinstance(unit.get("mx_records"), list) else []
        if records:
            from systems.modify.packet_modify import legal_set_for, writer_mx_block

            blocks = [
                writer_mx_block(rec, "center")
                for rec in records
                if isinstance(rec, dict) and rec.get("mx_id")
            ]
            if blocks:
                legal_ids = [str(mx_id) for mx_id in (unit.get("legal_mx_ids") or [])]
                linked_ids = [str(mx_id) for mx_id in (unit.get("linked_mx_ids") or [])]
                catalog = {
                    "misconceptions_mx": blocks,
                    "support_mx": [],
                    "legal_set": legal_set_for(blocks),
                }
                mx_block += (
                    "Mix-up catalog (teacher-side). Cite these mx_id values. "
                    "Do not print an mx_id or these sentences in the stem, options, or statements. "
                    "A border is the line that mix-up's wrong option must cross. "
                    "Do not print the border.\n"
                    + json.dumps(catalog, ensure_ascii=False)
                    + "\n"
                )
                if linked_ids:
                    mx_block += (
                        "Linked set for the situation boundary (teacher-side): "
                        + ", ".join(linked_ids)
                        + "\n"
                    )
                if legal_ids:
                    mx_block += (
                        "Legal set (cite a wrong option or false statement only from this set): "
                        + ", ".join(legal_ids)
                        + "\n"
                    )
        extra_bits = []
        if unit.get("because"):
            extra_bits.append(f"Because (teacher-side): {unit.get('because')}\n")
        if unit.get("operation"):
            extra_bits.append(f"Operation (teacher-side): {unit.get('operation')}\n")
        if unit.get("student_default"):
            extra_bits.append(f"Student default (teacher-side): {unit.get('student_default')}\n")
        if unit.get("false_success"):
            extra_bits.append(
                "False success (teacher-side): "
                + json.dumps(unit.get("false_success"), ensure_ascii=False)[:800]
                + "\n"
            )
        if unit.get("entities"):
            extra_bits.append("Entities (teacher-side): " + ", ".join(str(e) for e in unit.get("entities")) + "\n")
        if unit.get("mastery_claim"):
            extra_bits.append(f"Mastery claim (teacher-side, do not print): {unit.get('mastery_claim')}\n")
        situation = str(unit.get("situation_boundary") or "").strip()
        if situation:
            extra_bits.append(
                "Situation boundary (teacher-side). Stage the item in this situation. "
                "Do not print this sentence: "
                + situation
                + "\n"
            )
        id_line = "" if repeated else f"Unit {unit.get('unit_id')}.\n"
        unit_block = (
            id_line
            + f"Hinge decision (do not print this sentence): {decision}\n"
            f"Law (do not copy this into the stem or the options): {unit.get('law') or ''}\n"
            f"Boundaries: {bounds}\n"
            + "".join(extra_bits)
            + mx_block
            + f"Anti-narration: {unit.get('anti_narration') or 'none'}\n"
        )
    intent = _intent_for_prompt(req.get("intent") or "", decision)
    return (
        "Return modify_result.v1 JSON only. status OK or REFUSED. No markdown.\n"
        "Flat object: stem, item_type, options/statements/parts, answer, teacher at the top level. Do not nest them under an 'item' key.\n"
        + FORMAT_MENU
        + f"JEV suggested {form or 'none'}. Use that form only when it is the evidence this cell needs.\n"
        + head
        + unit_block
        + f"Aim for construct {brief.get('construct_id')} ({brief.get('coordinate_display')}).\n"
        f"Definition: {brief.get('definition') or ''}\n"
        "The task must match that definition and no neighbour. "
        "If the cell is a comparison, put two cases in the stem and ask what distinguishes them. "
        "Do not ask for an explanation of one case. "
        "If the cell is an explanation, ask why this result follows. "
        "Do not ask the candidate to judge which of several explanations is best.\n"
        f"Evidence mode: {brief.get('evidence_mode')}. Warning: {brief.get('warning') or 'none'}.\n"
        f"Intent (teacher-side, do not print): {intent}\n"
        + (
            "Secondary demand: one decision only. "
            "Stem may be one situation sentence plus exactly one question (04_GROK_SLOT). "
            "Do not add a second question. Do not use syllabus or tutor voice. "
            "The keyed claim must not paraphrase a sentence already in the stem.\n"
            if (req.get("grade_band") or "") == "secondary_9_10"
            else ""
        )
        + f"JEV plan: viable_as_mcq={plan.get('viable_as_mcq')} proceed={plan.get('proceed')} "
        f"likely_collapse={plan.get('likely_collapse')}.\n"
        + (
            "Do not cue the method by name. "
            if str(req.get("target_construct") or "").startswith("Ap.Pr")
            else ""
        )
        + "Error-analysis options must be competing predictions, not recipes.\n"
        + LEARNED
        + "teacher.variation_applied must be V3. proposed_key_status UNVERIFIED.\n"
        + CRAFT
        + sit_stage.prompt_block(req)
        + human_review.appendix(req)
    )


def unwrap_writer_item(item: dict) -> dict:
    """Flatten nested writer JSON {item: {stem, ...}, answer, teacher} into modify_result.v1."""
    if not isinstance(item, dict):
        return item
    inner = item.get("item")
    nested = (
        isinstance(inner, dict)
        and not item.get("stem")
        and (inner.get("stem") or inner.get("parts") or inner.get("options"))
    )
    if not nested:
        from catalog import normalize_result_shape

        return normalize_result_shape(item)
    out = dict(inner)
    for k in (
        "status",
        "answer",
        "teacher",
        "item_type",
        "schema",
        "tikz",
        "tables",
        "statements",
        "options",
        "parts",
        "mx_option_map",
    ):
        if out.get(k) in (None, [], {}) and item.get(k) not in (None, [], {}):
            out[k] = item[k]
    out.setdefault("schema", "modify_result.v1")
    if item.get("status") and not out.get("status"):
        out["status"] = item["status"]
    if item.get("proposed_key_status"):
        teach = out.get("teacher") if isinstance(out.get("teacher"), dict) else {}
        teach = dict(teach)
        teach.setdefault("proposed_key_status", item["proposed_key_status"])
        out["teacher"] = teach
    from catalog import normalize_result_shape

    return normalize_result_shape(out)


def extract_json(text: str) -> dict:
    t = (text or "").strip()
    fence = None
    if "```" in t:
        start = t.find("```")
        rest = t[start + 3 :]
        if rest.startswith("json"):
            rest = rest[4:]
        end = rest.find("```")
        if end >= 0:
            fence = rest[:end]
    raw = fence if fence is not None else t
    a, b = raw.find("{"), raw.rfind("}")
    if a < 0 or b <= a:
        raise RuntimeError("writer did not return JSON")
    return json.loads(raw[a : b + 1])


def call_writer(prompt: str) -> dict:
    key = (os.environ.get("TTWIN_WRITER_KEY") or "").strip()
    if not key:
        raise RuntimeError("WRITER_UNCONFIGURED")
    url = (os.environ.get("TTWIN_WRITER_URL") or "https://api.x.ai/v1/chat/completions").rstrip("/")
    model = os.environ.get("TTWIN_WRITER_MODEL") or "grok-4.7"
    # kimi-k3 and grok-4.7 spend a large reasoning budget; 4096 often yields empty JSON.
    if "kimi" in model or "grok" in model:
        default_tokens, default_timeout = "32000", "300" if "kimi" in model else "600"
    else:
        default_tokens, default_timeout = "4096", "90"
    max_tokens = int(os.environ.get("TTWIN_WRITER_MAX_TOKENS") or default_tokens)
    timeout = int(os.environ.get("TTWIN_WRITER_TIMEOUT") or default_timeout)
    payload = {
        "model": model,
        "temperature": 1,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": "You design TeacherTwin sitting items. JSON only."},
            {"role": "user", "content": prompt},
        ],
    }
    effort = (os.environ.get("TTWIN_WRITER_REASONING_EFFORT") or "").strip()
    if "kimi" in model:
        payload["reasoning_effort"] = effort or "low"
    elif "grok" in model:
        payload["reasoning_effort"] = effort or "xhigh"
    elif "deepseek" in model:
        payload["thinking"] = {"type": "disabled"}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    last = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            choice = ((data.get("choices") or [{}])[0]) or {}
            msg = choice.get("message") or {}
            content = msg.get("content") or ""
            if not str(content).strip():
                alt = msg.get("reasoning_content") or ""
                if str(alt).strip() and "{" in alt:
                    try:
                        return unwrap_writer_item(extract_json(alt))
                    except (json.JSONDecodeError, RuntimeError):
                        pass
                usage = data.get("usage") or {}
                last = "Empty writer response finish=%s keys=%s content_len=%s reasoning_len=%s usage=%s" % (
                    choice.get("finish_reason"),
                    ",".join(str(k) for k in msg.keys()),
                    len(str(content)),
                    len(str(alt)),
                    {k: usage.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens") if k in usage},
                )
                if attempt == 0:
                    continue
                raise RuntimeError(last)
            try:
                return extract_json(content)
            except json.JSONDecodeError as e:
                last = "writer JSON: " + str(e)
                if attempt == 0:
                    continue
                raise RuntimeError(last) from e
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if attempt == 0:
                continue
            raise RuntimeError(last) from e
        except RuntimeError:
            raise
        except Exception as e:
            last = str(e)
            if attempt == 0 and "timed out" in last.lower():
                continue
            raise RuntimeError(last) from e
    raise RuntimeError(last or "writer failed")


def log_call(out: Path, phase: str, state: dict, questions: dict, resp: dict | None, err: str | None) -> None:
    rec = {
        "utc": utc_now(),
        "phase": phase,
        "model": MODEL,
        "url": JEV_URL,
        "state_keys": list(state.keys()) if isinstance(state, dict) else None,
        "question_keys": list(questions.keys()),
        "target_in_state": bool(isinstance(state, dict) and state.get("target_construct")),
        "error": err,
        "usage": (resp or {}).get("usage") if isinstance(resp, dict) else None,
        "answers": (resp or {}).get("answers") if isinstance(resp, dict) else None,
        "stem_excerpt": str((state or {}).get("stem") or "")[:180],
    }
    append_jsonl(out / "jev_calls.jsonl", rec)


def _mx_repair_prompt(item: dict, unit: dict | None, err: str) -> str:
    records = (unit or {}).get("mx_records") if isinstance(unit, dict) else []
    catalog = "\n".join(
        f"- {rec.get('mx_id')}: {rec.get('wrong')}"
        for rec in (records or [])
        if isinstance(rec, dict) and rec.get("mx_id")
    )
    slim = {
        "item_type": item.get("item_type"),
        "stem": item.get("stem"),
        "options": [
            {"id": opt.get("id"), "text": opt.get("text")}
            for opt in (item.get("options") or [])
            if isinstance(opt, dict)
        ],
        "statements": [
            {"id": st.get("id"), "text": st.get("text")}
            for st in (item.get("statements") or [])
            if isinstance(st, dict)
        ],
        "answer": item.get("answer"),
    }
    unit_id = (unit or {}).get("unit_id") or ""
    return (
        "Return JSON only. Do not change the stem, the option text, the statement text, or the keyed answer.\n"
        "Fill mx_option_map so every option that is not the key cites a distinct mx_id from the catalog.\n"
        "For a multiple true-false item, set answer.pattern to a list of T and F, and statement_mx_map "
        "so every F statement cites a distinct mx_id.\n"
        "Fill worked_solution: status complete; result exactly the keyed option text; key_letter the key; "
        "given_facts as facts from the stem; hinges_used as "
        '[{"unit_id": "' + str(unit_id) + '", "role": "primary"}]; '
        "steps as at least two sentences, each containing the word therefore, and neither quoting the keyed option; "
        "why_key as one sentence; distractors as {letter, mx_id, why_wrong} for each wrong option.\n"
        f"Bind error to fix: {err}\n"
        f"Catalog:\n{catalog}\n"
        "Item:\n" + json.dumps(slim, ensure_ascii=False)[:8000]
    )


def _clean_letters(raw) -> list[str]:
    found = []
    values = raw if isinstance(raw, list) else [raw]
    for value in values:
        for token in str(value or "").upper().replace(",", " ").split():
            letter = token.strip()[:1]
            if letter.isalpha() and letter not in found:
                found.append(letter)
    return found


def _ensure_answer_kind(item: dict) -> None:
    """Writers often omit answer.kind, or mark only one option in a multi-select."""
    if not isinstance(item, dict):
        return
    ans = item.get("answer")
    if not isinstance(ans, dict):
        key = item.get("key")
        if isinstance(key, str) and key.strip()[:1].isalpha():
            item["answer"] = {"kind": "single_letter", "letter": key.strip().upper()[:1]}
        return
    if item.get("item_type") == "one_or_more":
        letters = _clean_letters(ans.get("letters") or ans.get("letter"))
        if len(letters) >= 2:
            ans["kind"] = "letter_set"
            ans["letters"] = letters
            ans.pop("letter", None)
            return
        if len(letters) == 1:
            item["item_type"] = "single_mcq"
            item["answer"] = {"kind": "single_letter", "letter": letters[0]}
            return
    if isinstance(ans.get("letter"), str) and ans["letter"].strip():
        ans["letter"] = ans["letter"].strip().upper()[:1]
    letters = _clean_letters(ans.get("letters"))
    if letters:
        ans["letters"] = letters
    if ans.get("kind"):
        return
    if ans.get("letter"):
        ans["kind"] = "single_letter"
    elif ans.get("letters"):
        ans["kind"] = "letter_set"
    elif ans.get("pattern"):
        ans["kind"] = "statement_pattern"


def _meta_repair_prompt(item: dict, phrase: str) -> str:
    slim = {
        "stem": item.get("stem"),
        "options": [
            {"id": opt.get("id"), "text": opt.get("text")}
            for opt in (item.get("options") or [])
            if isinstance(opt, dict)
        ],
        "statements": [
            {"id": st.get("id"), "text": st.get("text")}
            for st in (item.get("statements") or [])
            if isinstance(st, dict)
        ],
        "answer": item.get("answer"),
    }
    return (
        "Return the same item as JSON. Keep the same decision, the same key, and the same option count. "
        "The stem must be at most two sentences and at most 38 words. "
        "If the banned phrase is 'padded teaching narration', delete the extra scene-setting and leave the data plus one question. "
        "Do not write 'a student asks', 'a student wants', 'a student must', 'a class is', "
        "'already known', 'which statement is correct', 'which statements are correct', "
        "'which claim is correct', or 'the learner'. "
        "Describe the objects and the event directly.\n"
        f"Banned phrase found: {phrase}\n"
        "Item:\n" + json.dumps(slim, ensure_ascii=False)[:8000]
    )


def _sharpen_prompt(item: dict, noul: float, cell: str) -> str:
    slim = {
        "item_type": item.get("item_type"),
        "stem": item.get("stem"),
        "options": [
            {"id": opt.get("id"), "text": opt.get("text")}
            for opt in (item.get("options") or [])
            if isinstance(opt, dict)
        ],
        "statements": [
            {"id": st.get("id"), "text": st.get("text")}
            for st in (item.get("statements") or [])
            if isinstance(st, dict)
        ],
        "answer": item.get("answer"),
        "mx_option_map": item.get("mx_option_map"),
        "statement_mx_map": item.get("statement_mx_map"),
    }
    return (
        "Return the full item as JSON. The decision was not sharp enough to admit "
        f"(fit {noul:.2f} on {cell}). Keep the same item_type, the same key, and the same mix-up map. "
        "Rewrite the scene so two concrete results support only the keyed claim. "
        "Do not ask which claim does NOT fit. Do not let a reason repeat the claim. "
        "Do not write 'a student asks'. Keep worked_solution, with result equal to the keyed option text, "
        "and steps that each contain the word therefore and do not quote the keyed option.\n"
        "Item:\n" + json.dumps(slim, ensure_ascii=False)[:8000]
    )


def _bind_item_mx(item: dict, unit: dict | None) -> str | None:
    """Bind cited packet mx ids onto wrong options before any gate or bank write."""
    if str(TTWIN_ROOT) not in sys.path:
        sys.path.insert(0, str(TTWIN_ROOT))
    from systems.modify.packet_modify import bind_cited_mx

    records = []
    if isinstance(unit, dict) and isinstance(unit.get("mx_records"), list):
        records = unit["mx_records"]
    err = bind_cited_mx(item, records)
    if err:
        return err
    try:
        from worked_solution import worked_solution_is_complete
    except ImportError:
        from systems.modify.miqg.worked_solution import worked_solution_is_complete
    if item.get("item_type") in {"open_response", "structured_parts"}:
        return None
    ws = item.get("worked_solution")
    if isinstance(ws, dict):
        for field in ("result", "key_letter", "why_key"):
            value = ws.get(field)
            if isinstance(value, list):
                parts = [str(part).strip() for part in value if str(part).strip()]
                ws[field] = parts[0] if len(parts) == 1 else " ".join(parts)
    if not worked_solution_is_complete(item.get("worked_solution"), item):
        return "complete worked_solution required at generation"
    return None


def _miqg_top_only() -> bool:
    """This run admits on MIQG TOP. The taxonomy cell and noul are not gates."""
    return os.environ.get("TTWIN_ADMIT_MIQG_TOP") == "1"


def _hinge_tag(req: dict, item: dict, miqg: dict) -> dict:
    top = miqg.get("quality_tier") == "TOP" and miqg.get("release_gate") == "PASS"
    return {
        "schema": "ttwin.jev_taxonomy.v1",
        "item_id": req.get("requirement_id"),
        "subject": req.get("subject"),
        "grade": str(req.get("grade") or ""),
        "hinge_id": req.get("hinge_id"),
        "item_type": item.get("item_type"),
        "miqg_tier": miqg.get("quality_tier"),
        "miqg_protocol": miqg.get("protocol"),
        "admitted": top,
        "admission_basis": "miqg_top",
        "noul": None,
        "construct_id": None,
    }


def _relay_to_tmod(req: dict, item: dict, out: Path) -> tuple[dict | None, dict]:
    """Hand the situation to T-MOD. T-MOD writes the distractors and leaves the stem and key."""
    import tmod

    source = sit_stage.source_for_tmod(req, item)
    trail = tmod.modify_one(
        source,
        "The situation and the expected answer are fixed. Write the wrong options from the routes.",
        variation_class="V3",
        figure_mode="preserve",
        out=Path(out) / "tmod",
        skip_plan=True,
        skip_examine=True,
        skip_classify=True,
        extras={"hinge_id": req.get("hinge_id")},
    )
    finished = trail.get("item") if isinstance(trail.get("item"), dict) else None
    if trail.get("status") != "OK" or not finished or not finished.get("stem"):
        return None, trail
    return finished, trail


def mint(req: dict, d: dict, out: Path, draft: dict | None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    key = load_jev_key()
    req = deepcopy(req)
    req.setdefault("grade_band", band_of(int(req["grade"])))
    req.setdefault("requirement_id", "t-mint-" + utc_now().replace(":", "").replace("-", ""))
    brief = construct_brief(d, req["target_construct"])
    trail = {"utc": utc_now(), "requirement": req, "steps": [], "retry_same_prompt": False}

    unit, bind_reason = unit_bind.bind_requirement(req)
    trail["unit_bind"] = {
        "reason": bind_reason,
        "unit_id": None if unit is None else unit.get("unit_id"),
        "zone_size": 0 if unit is None else len(unit.get("zone") or []),
    }
    if bind_reason != "BOUND":
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = bind_reason + " for " + str(req.get("target_construct"))
        trail["steps"].append("stopped before T-PLAN: " + bind_reason)
        (out / "run.json").write_text(json.dumps(trail, indent=2), encoding="utf-8")
        return trail
    req["unit_id"] = unit["unit_id"]
    trail["steps"].append("bound " + unit["unit_id"])
    if unit.get("duplicate_routes"):
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = "duplicate mix-up route: " + ", ".join(unit["duplicate_routes"])
        trail["steps"].append("stopped before writer: duplicate route")
        (out / "run.json").write_text(json.dumps(trail, indent=2), encoding="utf-8")
        return trail
    from systems.modify.packet_modify import legal_set_for

    preview = legal_set_for(unit.get("mx_records") or [])
    unit["legal_mx_ids"] = preview["legal_ids"]
    unit["linked_mx_ids"] = preview["linked_ids"]

    resp = None
    plan_st = plan_state(req, d, unit)
    plan_questions = design_questions(req.get("grade_band"))
    if _miqg_top_only():
        plan = {
            "viable_as_mcq": None,
            "recommended_form": None,
            "likely_collapse": None,
            "proceed": "proceed_mcq",
        }
        trail["plan"] = plan
        trail["steps"].append("JEV scoring skipped; MIQG TOP is the only gate")
    else:
        try:
            resp = jev_call(key, plan_st, plan_questions)
            log_call(out, "T-PLAN", plan_st, plan_questions, resp, None)
            plan = parse_plan(resp.get("answers") or {})
            trail["plan"] = plan
            trail["steps"].append("T-PLAN ok")
        except Exception as e:
            log_call(out, "T-PLAN", plan_st, plan_questions, None, str(e))
            trail["error"] = str(e)
            (out / "run.json").write_text(json.dumps(trail, indent=2), encoding="utf-8")
            raise

    if plan.get("proceed") == "abandon_cell":
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = (
            "T-PLAN abandon_cell for "
            + req["target_construct"]
            + "; likely_collapse="
            + str(plan.get("likely_collapse"))
        )
        trail["steps"].append("stopped before writer: abandon_cell")
        (out / "run.json").write_text(json.dumps(trail, indent=2), encoding="utf-8")
        return trail

    item_type = lock_item_type(plan)
    trail["locked_item_type"] = item_type
    if "occupied_situations" not in req and not str(req.get("user_situation") or "").strip():
        req["occupied_situations"] = sit_stage.collect_occupied(
            [req.get("hinge_id"), req.get("unit_id"), *(req.get("companion_hinge_ids") or [])]
        )
        trail["occupied_situations"] = len(req["occupied_situations"])
    if req.get("companion_hinge_ids") and "companion_hinges" not in req:
        req["companion_hinges"] = sit_stage.companion_briefs(req)
    prompt = writer_prompt(req, plan, item_type, brief, unit)
    (out / "writer_prompt.txt").write_text(prompt, encoding="utf-8")

    if draft is not None:
        item = unwrap_writer_item(deepcopy(draft))
        trail["steps"].append("writer skipped (--draft)")
    else:
        try:
            item = unwrap_writer_item(call_writer(prompt))
            trail["steps"].append("writer ok")
        except Exception as e:
            if str(e) == "WRITER_UNCONFIGURED":
                trail["status"] = "REFUSED"
                trail["refusal_reason"] = (
                    "WRITER_UNCONFIGURED: set TTWIN_WRITER_KEY or pass --draft. "
                    "T-PLAN completed; writer_prompt.txt is in the out dir."
                )
                (out / "run.json").write_text(json.dumps(trail, indent=2), encoding="utf-8")
                return trail
            trail["status"] = "REFUSED"
            trail["refusal_reason"] = "writer: " + type(e).__name__ + ": " + str(e)[:240]
            (out / "run.json").write_text(json.dumps(trail, indent=2), encoding="utf-8")
            return trail

    if item.get("status") == "REFUSED":
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = item.get("refusal_reason")
        (out / "run.json").write_text(json.dumps(trail, indent=2), encoding="utf-8")
        return trail

    chosen = item.get("item_type") or item_type
    if chosen not in ALLOWED_ITEM_TYPES:
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = "G2 form lock: writer item_type %s is not a stored format" % chosen
        (out / "run.json").write_text(json.dumps(trail, indent=2), encoding="utf-8")
        return trail
    item["item_type"] = chosen

    item.setdefault("teacher", {})
    item["teacher"].setdefault("proposed_key_status", "UNVERIFIED")
    item["teacher"].setdefault("variation_applied", "V3")
    item["teacher"].setdefault("fidelity_selfcheck", "T-MINT")

    if draft is None and unit_bind.procedure_leaked(item.get("stem") or "", unit.get("law") or ""):
        trail["steps"].append("repair procedure_leaked")
        repair_prompt = prompt + (
            "\nREPAIR: the stem copies the method. Rewrite so the method is not stated. "
            "Keep one scene and one decision. Do not explain the phenomenon in the stem.\n"
            "Previous stem:\n" + str(item.get("stem") or "")[:800] + "\n"
        )
        try:
            repaired = unwrap_writer_item(call_writer(repair_prompt))
            if repaired.get("status") != "REFUSED":
                repaired["item_type"] = item.get("item_type") or item_type
                item = repaired
                trail["steps"].append("repair writer ok")
        except Exception as e:
            trail["repair_error"] = str(e)[:200]

    staged = sit_stage.stage_item(item, req)
    if staged:
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = staged
        trail["steps"].append("situation refused")
        (out / "writer_item.json").write_text(json.dumps(item, indent=2, default=str)[:200000], encoding="utf-8")
        (out / "run.json").write_text(json.dumps(trail, indent=2), encoding="utf-8")
        return trail
    from phrase_contract import enforce_locked_type, structural_errors

    locked = enforce_locked_type(item, req)
    if locked:
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = locked
        trail["steps"].append("situation refused")
        (out / "writer_item.json").write_text(json.dumps(item, indent=2, default=str)[:200000], encoding="utf-8")
        (out / "run.json").write_text(json.dumps(trail, indent=2), encoding="utf-8")
        return trail
    trail["steps"].append("situation ready")

    records = list(unit.get("mx_records") or [])
    phrase_errors = structural_errors(item, unit, records)
    if phrase_errors:
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = "phrase: " + "; ".join(phrase_errors)[:240]
        trail["steps"].append("phrase refused")
        (out / "writer_item.json").write_text(json.dumps(item, indent=2, default=str)[:200000], encoding="utf-8")
        (out / "run.json").write_text(json.dumps(trail, indent=2), encoding="utf-8")
        return trail
    import key_gate

    key_report = key_gate.check(item, unit, call_writer, req)
    trail["key_gate"] = key_report
    teacher = dict(item.get("teacher") or {}) if isinstance(item.get("teacher"), dict) else {}
    teacher["key_gate"] = {k: key_report.get(k) for k in ("status", "reason", "independent_result")}
    item["teacher"] = teacher
    if key_report.get("status") != "PASS":
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = "key: " + str(key_report.get("reason") or "keyed claim is not the result this stem requires")
        trail["item"] = item
        trail["steps"].append("T-MINT key refused")
        (out / "writer_item.json").write_text(json.dumps(item, indent=2, default=str)[:200000], encoding="utf-8")
        (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
        return trail
    trail["steps"].append("T-MINT key PASS")
    if req.get("situation_only"):
        trail["status"] = "SITUATION"
        trail["item"] = item
        trail["steps"].append("stopped before T-MOD")
        (out / "writer_item.json").write_text(json.dumps(item, indent=2, default=str)[:200000], encoding="utf-8")
        (out / "run.json").write_text(json.dumps(trail, indent=2), encoding="utf-8")
        (out / "result.json").write_text(json.dumps(item, indent=2, default=str), encoding="utf-8")
        return trail

    relayed, tmod_trail = _relay_to_tmod(req, item, out)
    trail["tmod"] = {
        "status": tmod_trail.get("status"),
        "refusal_reason": tmod_trail.get("refusal_reason"),
        "steps": tmod_trail.get("steps"),
        "same_output": tmod_trail.get("same_output"),
    }
    if relayed is None:
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = tmod_trail.get("refusal_reason") or "T-MOD did not return an item"
        trail["item"] = tmod_trail.get("item")
        trail["steps"].append("T-MOD refused")
        (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
        return trail
    item = relayed
    trail["steps"].append("T-MOD distractors")
    trail["steps"].append("mx_bind skipped: T-MOD owns the distractors")
    from phrase_contract import option_shape_errors

    shape_errors = option_shape_errors(item)
    if shape_errors:
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = "phrase: " + "; ".join(shape_errors)[:240]
        trail["item"] = item
        trail["steps"].append("option shape refused")
        (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
        return trail
    _ensure_answer_kind(item)
    if draft is None:
        facing = miqg_cal.student_facing_texts(item)
        hit = miqg_cal.meta_language_match(*facing) if facing else None
        if hit:
            trail["steps"].append("meta repair: " + hit.group(0)[:80])
            try:
                patched = unwrap_writer_item(call_writer(_meta_repair_prompt(item, hit.group(0))))
                if patched.get("stem"):
                    item["stem"] = patched["stem"]
                if isinstance(patched.get("options"), list) and patched["options"]:
                    by_old = {
                        str(opt.get("id") or "").upper(): opt
                        for opt in (item.get("options") or [])
                        if isinstance(opt, dict)
                    }
                    rewritten = []
                    for opt in patched["options"]:
                        if not isinstance(opt, dict):
                            continue
                        letter = str(opt.get("id") or "").upper()
                        kept = dict(by_old.get(letter) or {})
                        kept["id"] = letter or kept.get("id")
                        kept["text"] = opt.get("text") or kept.get("text")
                        rewritten.append(kept)
                    if rewritten:
                        item["options"] = rewritten
                if isinstance(patched.get("statements"), list) and patched["statements"]:
                    item["statements"] = patched["statements"]
                _ensure_answer_kind(item)
                trail["steps"].append("meta repair writer ok")
            except Exception as e:
                trail["repair_error"] = str(e)[:200]

    from combination_key import collapse_multiselect

    if collapse_multiselect(item):
        trail["steps"].append("combination key " + str((item.get("answer") or {}).get("letter")))

    fig_mode = "add" if v5_lock.tikz_of(item).strip() else "preserve"
    compiled = modify_packet.assemble_modify_packet(
        {"item_type": item["item_type"], "stem": req.get("intent") or "", "options": item.get("options") or [], "tikz": None},
        req.get("intent") or "",
        variation_class="V3",
        figure_mode=fig_mode,
        target_item_type=item["item_type"],
        hinge={"primary": req.get("hinge_id"), "title": req.get("hinge_title") or req.get("hinge_id") or "hinge"} if req.get("hinge_id") else None,
        packed_tags={
            "pack": req.get("grade_band") or band_of(int(req["grade"])),
            "subject": str(req.get("subject") or "science")[:40],
            "level": "",
            "topic": "",
            "paper_hint": "",
        },
        item_ref="session:" + str(req.get("requirement_id") or "t-mint"),
    )
    gate = gates.apply_outcome(item, compiled)
    trail["g1_g8"] = {"ok": gate.get("ok"), "gate": gate.get("gate"), "detail": gate.get("detail")}
    trail["v5_lock"] = gate.get("v5")
    extra = list(((gate.get("v5") or {}).get("extra_findings")) or [])
    trail["steps"].append("G1-G8+G3b " + ("ok" if gate.get("ok") else str(gate.get("gate"))))

    if v5_lock.tikz_of(item).strip() and not _miqg_top_only():
        try:
            exam = iso_examiner.run(jev_call, key, item, req)
            log_call(
                out,
                "T-ISO-EXAMINER",
                iso_examiner.examiner_state(item, req),
                iso_examiner.examiner_questions(iso_examiner.letters_of(item)),
                {"answers": exam.get("answers"), "usage": exam.get("usage")},
                None,
            )
            extra.extend(exam.get("extra_findings") or [])
            trail["iso_examiner"] = {
                k: exam.get(k)
                for k in ("independent_key", "figure_load_bearing", "stem_figure_agree", "load_bearing_fail", "author_key_in_state")
            }
            trail["steps"].append("T-ISO-EXAMINER " + str(exam.get("independent_key")))
        except Exception as e:
            log_call(out, "T-ISO-EXAMINER", iso_examiner.examiner_state(item, req), iso_examiner.examiner_questions(iso_examiner.letters_of(item)), None, str(e))
            trail["examine_error"] = str(e)
            if "402" in str(e):
                trail["status"] = "REFUSED"
                trail["refusal_reason"] = str(e)
                (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
                return trail

    miqg = g17(item, req, extra_findings=extra, packet=compiled)
    trail["miqg"] = miqg
    trail["steps"].append("G17 " + str(miqg.get("quality_tier")))

    q = taxonomy_questions(d)
    st = classify_state(item, req)
    tag = None
    if _miqg_top_only():
        tag = _hinge_tag(req, item, miqg)
        trail["steps"].append("hinge " + str(req.get("hinge_id")) + " mapped without a JEV score")
    else:
        try:
            cres = jev_call(key, st, q)
            log_call(out, "T-JEV-CLASSIFY", st, q, cres, None)
            tag = pack_tag(
                {
                    "id": req["requirement_id"],
                    "subject": req["subject"],
                    "grade": req["grade"],
                    "chapter": req.get("chapter"),
                    "hinge_id": req["hinge_id"],
                    "item_type": item["item_type"],
                    "quality_tier": miqg.get("quality_tier"),
                },
                d,
                cres.get("answers") or {},
                cres.get("usage"),
            )
            trail["steps"].append("T-JEV-CLASSIFY tikz_in_state=" + str(bool(st.get("tikz"))))
        except Exception as e:
            log_call(out, "T-JEV-CLASSIFY", st, q, None, str(e))
            trail["classify_error"] = str(e)
            if "402" in str(e):
                trail["status"] = "REFUSED"
                trail["refusal_reason"] = str(e)

    if _miqg_top_only():
        top = miqg.get("quality_tier") == "TOP" and miqg.get("release_gate") == "PASS"
        g18r = {
            "gate": "G18",
            "status": "PASS" if top else "HOLD",
            "reason": "MIQG_TOP" if top else "G17_NOT_TOP",
            "construct_hit": False,
            "retry_same_prompt": False,
        }
    else:
        g18r = g18(req, plan, miqg, tag, zone=set(unit.get("zone") or []))
    noul = tag.get("noul") if isinstance(tag, dict) else None
    if (
        not _miqg_top_only()
        and draft is None
        and miqg.get("quality_tier") == "TOP"
        and isinstance(noul, (int, float))
        and 0.40 <= float(noul) < 0.50
        and not (tag or {}).get("admitted")
    ):
        trail["steps"].append("sharpen noul=%.2f" % float(noul))
        try:
            patched = unwrap_writer_item(call_writer(_sharpen_prompt(item, float(noul), str((tag or {}).get("unresolved_coord") or ""))))
            if patched.get("stem") and patched.get("status") != "REFUSED":
                patched["item_type"] = item.get("item_type")
                for field in ("mx_option_map", "statement_mx_map", "worked_solution"):
                    if patched.get(field) in (None, {}, []) and item.get(field) not in (None, {}, []):
                        patched[field] = item[field]
                if not _bind_item_mx(patched, unit):
                    _ensure_answer_kind(patched)
                    item = patched
                    miqg = g17(item, req, extra_findings=extra, packet=compiled)
                    trail["miqg"] = miqg
                    trail["steps"].append("sharpen G17 " + str(miqg.get("quality_tier")))
                    st = classify_state(item, req)
                    cres = jev_call(key, st, q)
                    log_call(out, "T-JEV-CLASSIFY-SHARPEN", st, q, cres, None)
                    tag = pack_tag(
                        {
                            "id": req["requirement_id"],
                            "subject": req["subject"],
                            "grade": req["grade"],
                            "chapter": req.get("chapter"),
                            "hinge_id": req["hinge_id"],
                            "item_type": item["item_type"],
                            "quality_tier": miqg.get("quality_tier"),
                        },
                        d,
                        cres.get("answers") or {},
                        cres.get("usage"),
                    )
                    g18r = g18(req, plan, miqg, tag, zone=set(unit.get("zone") or []))
                    trail["steps"].append("sharpen noul=%s" % (tag or {}).get("noul"))
        except Exception as e:
            trail["steps"].append("sharpen failed: " + str(e)[:160])
    trail["g18"] = g18r
    trail["retry_same_prompt"] = bool(g18r.get("retry_same_prompt"))
    trail["jev_taxonomy"] = tag
    trail["item"] = item
    figure_ok = bool(gate.get("ok"))
    construct_ok = g18r.get("status") in SHIP_G18
    miqg_ok = miqg.get("quality_tier") == "TOP" and miqg.get("release_gate") == "PASS"
    if not figure_ok:
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = str(gate.get("gate")) + ": " + str(gate.get("detail") or "")
    elif not miqg_ok:
        trail["status"] = trail.get("status") or "HOLD"
        trail["refusal_reason"] = trail.get("refusal_reason") or (
            "MIQG: tier=" + str(miqg.get("quality_tier"))
            + " release_gate=" + str(miqg.get("release_gate"))
            + " decisive=" + str(miqg.get("decisive_reason"))
        )
    else:
        trail["status"] = "OK" if construct_ok else g18r.get("status")
    from phrase_contract import release_record

    trail["release"] = release_record(trail.get("legal_set") if isinstance(trail.get("legal_set"), dict) else {})
    trail["serve_eligible"] = False
    trail["candidate_write"] = "CANDIDATE" if (figure_ok and construct_ok and miqg_ok) else (
        "CANDIDATE_REPAIR" if miqg.get("release_gate") == "REPAIR" else "HOLD"
    )
    (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
    (out / "result.json").write_text(json.dumps(item, indent=2, default=str), encoding="utf-8")
    return trail


def main() -> int:
    ap = argparse.ArgumentParser(description="Modify harness: T-MINT situation, then T-MOD distractors")
    ap.add_argument("--requirement", required=True, help="modify_requirement.v1 JSON")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--dictionary", help="construct_dictionary.json")
    ap.add_argument("--draft", help="skip the T-MINT writer; this JSON is the situation")
    ap.add_argument("--situation-only", action="store_true", help="stop after T-MINT, before T-MOD")
    args = ap.parse_args()
    req = json.loads(Path(args.requirement).read_text(encoding="utf-8"))
    if req.get("schema") and req["schema"] != "modify_requirement.v1":
        raise SystemExit("requirement schema must be modify_requirement.v1")
    if args.situation_only:
        req["situation_only"] = True
    d = json.loads(find_dictionary(args.dictionary).read_text(encoding="utf-8"))
    draft = json.loads(Path(args.draft).read_text(encoding="utf-8")) if args.draft else None
    out = Path(args.out)
    try:
        import harness
        trail = harness.generate(req, d, out, draft)
    except Exception as e:
        import traceback
        trail = {
            "status": "REFUSED",
            "refusal_reason": "crash: " + type(e).__name__ + ": " + str(e)[:400],
            "error": traceback.format_exc()[-2000:],
        }
        out.mkdir(parents=True, exist_ok=True)
        (out / "run.json").write_text(json.dumps(trail, indent=2), encoding="utf-8")
    print(json.dumps({k: trail.get(k) for k in ("status", "g18", "miqg", "refusal_reason", "locked_item_type", "plan")}, indent=2, default=str))
    return 0 if trail.get("status") in {"OK", "PASS", "PASS_NEIGHBOUR", "PASS_ZONE", "CONSTRUCT_HOLD", "HOLD", "REFUSED", "SITUATION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
