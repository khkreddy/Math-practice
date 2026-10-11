"""Construct-dictionary briefs and JEV question maps for T-PLAN / classify."""
from __future__ import annotations

from datetime import datetime, timezone

PROCESS = [
    ("R", "Remember — retrieve, recognize, recall, identify"),
    ("U", "Understand — paraphrase, classify, exemplify, explain, compare"),
    ("Ap", "Apply — carry out or use a procedure in a given situation"),
    ("An", "Analyze — break into parts, differentiate, organize, diagnose"),
    ("Ev", "Evaluate — judge against criteria, check, critique, justify"),
    ("Cr", "Create — generate, plan, design, produce a new whole"),
]
KNOWLEDGE = [
    ("Fa", "Factual — terms, symbols, units, labels, isolated facts"),
    ("Co", "Conceptual — categories, principles, models, structures, relations"),
    ("Pr", "Procedural — algorithms, methods, techniques, method selection"),
    ("Me", "Metacognitive — strategy knowledge, self-monitoring, planning"),
]
DOK = [
    ("1", "DoK-1 Recall/Reproduction — single known route, no decision point"),
    ("2", "DoK-2 Skill/Concept — two+ steps in a familiar setting"),
    ("3", "DoK-3 Strategic Thinking — method not fully cued, justification, non-routine"),
    ("4", "DoK-4 Extended Thinking — multi-source, investigation, design-revision"),
]
NOUL_ADMIT = 0.50
MODEL = "jev-latest"

FORM_TO_TYPE = {
    "error_analysis_mcq": "single_mcq",
    "method_selection_mcq": "single_mcq",
    "claim_evidence_mcq": "single_mcq",
    "worked_response": "structured_parts",
    "project_extended": "structured_parts",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enum_pairs(d: dict, key: str, id_field: str, gloss_field: str) -> list[tuple[str, str]]:
    rows = d.get("enums", {}).get(key) or []
    return [(str(r[id_field]), str(r.get(gloss_field) or r[id_field])) for r in rows]


def construct_brief(d: dict, cid: str) -> dict:
    c = (d.get("constructs") or {}).get(cid) or {}
    vm = d.get("validity_map") or {}
    if cid in (vm.get("LIVE") or []):
        status = "LIVE"
    elif cid in (vm.get("FRAGILE") or []):
        status = "FRAGILE"
    elif cid in (vm.get("IMPOSSIBLE") or []):
        status = "IMPOSSIBLE"
    elif cid in (vm.get("DEGENERATE") or {}):
        status = "DEGENERATE"
    else:
        status = "UNKNOWN"
    return {
        "construct_id": cid,
        "status": status,
        "label": c.get("label"),
        "coordinate_display": c.get("coordinate_display"),
        "definition": c.get("definition"),
        "evidence_mode": c.get("evidence_mode"),
        "evidence_mode_note": c.get("evidence_mode_note"),
        "item_forms": c.get("item_forms"),
        "cue_risks": c.get("cue_risks"),
        "example": c.get("example"),
        "warning": c.get("warning"),
        "mastery_observable": c.get("mastery_observable"),
        "in_minimum_viable_v1": cid in ((d.get("profiles") or {}).get("minimum_viable_v1") or []),
    }


def sitting_phrase(grade_band: str | None = None) -> str:
    """Planner sitting label. Secondary requirements are not the middle-school default."""
    if not grade_band or grade_band == "middle_6_8":
        return "middle-school sitting item"
    if grade_band == "secondary_9_10":
        return "secondary sitting item"
    return "IGCSE or AS/A sitting item"


def design_questions(grade_band: str | None = None) -> dict:
    sitting = sitting_phrase(grade_band)
    return {
        "viable_as_mcq": {
            "type": "noul",
            "instructions": (
                "Can a single %s honestly occupy the TARGET construct cell, "
                "without collapsing to a weaker neighbour? Yes only if the demanded "
                "performance is that cell." % sitting
            ),
        },
        "recommended_form": {
            "type": "choice",
            "instructions": "Best honest item form for this TARGET cell at the stated grade.",
            "criteria": {
                "error_analysis_mcq": "Error-analysis MCQ; options are competing observable predictions or diagnoses",
                "method_selection_mcq": "MCQ of which procedure applies; the method is not named as a cue in the stem",
                "claim_evidence_mcq": "MCQ judging which claim is warranted by the given evidence",
                "worked_response": "Generated worked response / structured parts; MCQ cannot hold the cell",
                "project_extended": "Multi-source or multi-condition investigation; a single MCQ cannot hold DoK-4",
            },
        },
        "likely_collapse": {
            "type": "choice",
            "instructions": "If forced into a typical 4-option recall/explain MCQ, which cell would it actually occupy?",
            "criteria": {
                "U.Co.2": "Understand conceptual DoK-2",
                "An.Co.2": "Analyze conceptual DoK-2",
                "An.Co.3": "Analyze conceptual DoK-3",
                "Ap.Pr.2": "Apply procedural DoK-2",
                "Ap.Pr.3": "Apply procedural DoK-3",
                "An.Pr.3": "Analyze procedural DoK-3",
                "Ev.Pr.3": "Evaluate procedural DoK-3",
                "Ev.Pr.4": "Evaluate procedural DoK-4",
                "Ev.Co.3": "Evaluate conceptual DoK-3",
                "R.Co.1": "Remember conceptual DoK-1",
            },
        },
        "proceed": {
            "type": "choice",
            "instructions": "Instruction to the writer for this requirement.",
            "criteria": {
                "proceed_mcq": "A selected-response item can hold the TARGET cell. The writer still chooses the format that makes the cell observable.",
                "proceed_structured": "Write structured/worked-response parts aimed at the TARGET cell",
                "retarget_neighbour": "Keep a sitting item but retarget the LIVE neighbour named in likely_collapse",
                "abandon_cell": "Do not claim the TARGET cell for a single sitting item",
            },
        },
    }


def taxonomy_questions(d: dict) -> dict:
    facets = enum_pairs(d, "facet_type", "facet_id", "what_it_tests")
    jobs = enum_pairs(d, "epistemic_job", "job_id", "what_it_discriminates")
    mxs = enum_pairs(d, "misconception_type", "type_id", "what_the_student_does_wrong")
    mxs.append(("none_not_diagnostic", "Item is not designed to surface a named misconception"))
    return {
        "process": {
            "type": "choice",
            "instructions": "Primary cognitive process demanded by a correct response.",
            "criteria": {c: lab for c, lab in PROCESS},
        },
        "knowledge": {
            "type": "choice",
            "instructions": "Knowledge type the item mainly requires.",
            "criteria": {c: lab for c, lab in KNOWLEDGE},
        },
        "dok": {
            "type": "choice",
            "instructions": "Webb Depth of Knowledge of the demanded performance.",
            "criteria": {c: lab for c, lab in DOK},
        },
        "noul_fit": {
            "type": "noul",
            "instructions": (
                "Is the process × knowledge × DoK triple you chose a valid description "
                "of this item's cognitive demand? Yes only if a weaker or neighbouring cell "
                "would mis-describe the demanded performance."
            ),
        },
        "strength": {
            "type": "score",
            "instructions": "How strongly does that construct cell fit this item?",
            "criteria": [
                "0 none — no adequate cell",
                "1 weak — nearby cell, several others almost as good",
                "2 moderate — good fit, one plausible neighbour",
                "3 strong — this is the distinctive demand",
            ],
        },
        "facet": {
            "type": "choice",
            "instructions": "Dominant facet of the demand.",
            "criteria": {i: g for i, g in facets},
        },
        "epistemic_job": {
            "type": "choice",
            "instructions": "What diagnostic job this item is best used for.",
            "criteria": {i: g for i, g in jobs},
        },
        "designed_mx": {
            "type": "choice",
            "instructions": "Misconception type the item is designed to surface, if any.",
            "criteria": {i: g for i, g in mxs},
        },
    }


def as_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, dict):
        for k in ("value", "choice", "id", "label", "answer", "option"):
            if k in v and v[k] is not None:
                return as_text(v[k])
        return str(v)
    if isinstance(v, (list, tuple)):
        return as_text(v[0]) if v else ""
    return str(v).strip()


def as_float(v, default=0.0) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        for k in ("value", "noul", "score", "rating"):
            if k in v:
                return as_float(v[k], default)
    try:
        return float(str(v).strip())
    except Exception:
        return default


def parse_code(raw: str, allowed: list[str]) -> str | None:
    t = (raw or "").strip()
    if not t:
        return None
    head = t.split("—")[0].split("–")[0].split(":")[0].strip()
    if head in allowed:
        return head
    for a in sorted(allowed, key=len, reverse=True):
        if t == a or t.startswith(a + " ") or t.startswith(a + "—") or f"({a})" in t:
            return a
        if t.lower().startswith(a.lower()):
            return a
    return None


def resolve_construct(d: dict, proc: str | None, know: str | None, dok: str | None) -> dict:
    live = set(d["validity_map"]["LIVE"])
    fragile = set(d["validity_map"]["FRAGILE"])
    impossible = set(d["validity_map"]["IMPOSSIBLE"])
    degenerate = d["validity_map"].get("DEGENERATE") or {}
    cid = f"{proc}.{know}.{dok}" if proc and know and dok else None
    status = "UNRESOLVED"
    redirected_from = None
    if not cid:
        status = "UNRESOLVED"
    elif cid in live:
        status = "LIVE"
    elif cid in fragile:
        status = "FRAGILE"
    elif cid in degenerate:
        redirected_from = cid
        cid2 = degenerate[cid]
        if cid2 == "IMPOSSIBLE":
            status = "IMPOSSIBLE"
            cid = redirected_from
        else:
            cid = cid2
            status = "LIVE" if cid in live else ("FRAGILE" if cid in fragile else "DEGENERATE_REDIRECT")
    elif cid in impossible:
        status = "IMPOSSIBLE"
    else:
        status = "UNKNOWN_CELL"
    rec = (d.get("constructs") or {}).get(cid) or {}
    return {
        "construct_id": cid,
        "construct_status": status,
        "redirected_from": redirected_from,
        "label": rec.get("label"),
        "coordinate_display": rec.get("coordinate_display"),
        "definition": rec.get("definition"),
    }


def pack_tag(row: dict, d: dict, answers: dict, usage: dict | None) -> dict:
    proc = parse_code(as_text(answers.get("process")), [c for c, _ in PROCESS])
    know = parse_code(as_text(answers.get("knowledge")), [c for c, _ in KNOWLEDGE])
    dok = parse_code(as_text(answers.get("dok")), [c for c, _ in DOK])
    noul = as_float(answers.get("noul_fit"))
    strength = as_float(answers.get("strength"))
    weight = round(0.5 * noul + 0.5 * (strength / 3.0), 4) if (noul or strength) else None
    resolved = resolve_construct(d, proc, know, dok)
    admitted = bool(
        noul >= NOUL_ADMIT
        and resolved["construct_id"]
        and resolved["construct_status"] in {"LIVE", "FRAGILE", "DEGENERATE_REDIRECT"}
    )
    facets = [i for i, _ in enum_pairs(d, "facet_type", "facet_id", "what_it_tests")]
    jobs = [i for i, _ in enum_pairs(d, "epistemic_job", "job_id", "what_it_discriminates")]
    mxs = [i for i, _ in enum_pairs(d, "misconception_type", "type_id", "what_the_student_does_wrong")]
    mxs.append("none_not_diagnostic")
    return {
        "schema": "ttwin.jev_taxonomy.v1",
        "item_id": row.get("id"),
        "subject": row.get("subject"),
        "grade": str(row.get("grade") or ""),
        "chapter": row.get("chapter"),
        "hinge_id": row.get("hinge_id"),
        "item_type": row.get("item_type"),
        "miqg_tier": row.get("quality_tier") or row.get("miqg_tier"),
        "miqg_protocol": "MIQG-v1.0-rc9-CAL-KNGOOD",
        "admitted": admitted,
        "construct_id": resolved["construct_id"] if admitted else None,
        "construct_status": resolved["construct_status"],
        "redirected_from": resolved["redirected_from"],
        "construct_label": resolved["label"],
        "coordinate": {
            "cognitive_process": proc,
            "knowledge_type": know,
            "dok_level": int(dok) if dok else None,
        },
        "coordinate_display": resolved.get("coordinate_display"),
        "noul": noul,
        "strength_score": strength,
        "weight": weight,
        "facet": parse_code(as_text(answers.get("facet")), facets),
        "epistemic_job": parse_code(as_text(answers.get("epistemic_job")), jobs),
        "designed_confusion_type": parse_code(as_text(answers.get("designed_mx")), mxs),
        "raw_choice_text": {
            "process": as_text(answers.get("process")),
            "knowledge": as_text(answers.get("knowledge")),
            "dok": as_text(answers.get("dok")),
            "facet": as_text(answers.get("facet")),
            "epistemic_job": as_text(answers.get("epistemic_job")),
            "designed_mx": as_text(answers.get("designed_mx")),
        },
        "model": MODEL,
        "tagged_utc": utc_now(),
        "usage": usage or {},
        "unresolved_coord": (
            f"{proc}.{know}.{dok}" if proc and know and dok else None
        ),
    }


def parse_plan(answers: dict) -> dict:
    form_ok = set(FORM_TO_TYPE)
    proceed_ok = {"proceed_mcq", "proceed_structured", "retarget_neighbour", "abandon_cell"}
    collapse_ok = {
        "U.Co.2", "An.Co.2", "An.Co.3", "Ap.Pr.2", "Ap.Pr.3",
        "An.Pr.3", "Ev.Pr.3", "Ev.Pr.4", "Ev.Co.3", "R.Co.1",
    }

    def pick(raw: str, allowed: set[str]) -> str | None:
        t = (raw or "").strip()
        if t in allowed:
            return t
        for a in sorted(allowed, key=len, reverse=True):
            if t.startswith(a) or a in t:
                return a
        return t or None

    return {
        "viable_as_mcq": as_float(answers.get("viable_as_mcq")),
        "recommended_form": pick(as_text(answers.get("recommended_form")), form_ok),
        "likely_collapse": pick(as_text(answers.get("likely_collapse")), collapse_ok),
        "proceed": pick(as_text(answers.get("proceed")), proceed_ok),
    }


def lock_item_type(plan: dict) -> str:
    form = plan.get("recommended_form")
    proceed = plan.get("proceed")
    if proceed == "proceed_structured":
        return "structured_parts"
    if proceed == "proceed_mcq":
        return "single_mcq"
    return FORM_TO_TYPE.get(form or "", "single_mcq")


def normalize_result_shape(item: dict) -> dict:
    """Coerce writer option/part shapes into modify_result.v1 lists with ids.

    Writers often return options as an A–D object or a list of bare strings.
    Gates G2/G6 require options[].id and parts[].id matching the key.
    """
    if not isinstance(item, dict):
        return item
    out = dict(item)
    letters = "ABCDEFGH"
    opts = out.get("options")
    if isinstance(opts, dict):
        coerced = []
        for k, v in opts.items():
            if isinstance(v, str):
                coerced.append({"id": str(k), "text": v})
                continue
            if isinstance(v, dict):
                q = {"id": str(k), "text": str(v.get("text") or v.get("value") or "")}
                # Preserve serve-required wrong-option provenance fields.
                try:
                    from systems.question_ingest.option_feedback import OPTION_FEEDBACK_FIELD
                except ImportError:
                    OPTION_FEEDBACK_FIELD = "feedback"
                if OPTION_FEEDBACK_FIELD in v and isinstance(v.get(OPTION_FEEDBACK_FIELD), dict):
                    q[OPTION_FEEDBACK_FIELD] = v[OPTION_FEEDBACK_FIELD]
                if isinstance(v.get("mx_refs"), list):
                    q["mx_refs"] = v["mx_refs"]
                if "prerequisite_gap" in v:
                    q["prerequisite_gap"] = v["prerequisite_gap"]
                coerced.append(q)
                continue
            coerced.append({"id": str(k), "text": str(v)})
        out["options"] = coerced
    elif isinstance(opts, list):
        coerced = []
        for i, o in enumerate(opts):
            lid = letters[i] if i < len(letters) else str(i + 1)
            if isinstance(o, str):
                coerced.append({"id": lid, "text": o})
            elif isinstance(o, dict):
                q = dict(o)
                if not q.get("id"):
                    q["id"] = lid
                if q.get("text") in (None, "") and "id" in o and len(o) == 1:
                    k, v = next(iter(o.items()))
                    q = {"id": str(k), "text": str(v)}
                elif q.get("text") in (None, ""):
                    q["text"] = str(q.get("option") or q.get("label") or "")
                coerced.append(q)
            else:
                coerced.append({"id": lid, "text": str(o)})
        out["options"] = coerced
    parts = out.get("parts")
    if isinstance(parts, list):
        pletters = "abcdefgh"
        newp = []
        for i, p in enumerate(parts):
            if not isinstance(p, dict):
                continue
            q = dict(p)
            q["id"] = q.get("id") or pletters[i]
            if q.get("text") in (None, "") and q.get("prompt"):
                q["text"] = q["prompt"]
            newp.append(q)
        out["parts"] = newp
        ans = dict(out.get("answer") or {})
        pa = list(ans.get("part_answers") or [])
        fixed = []
        for i, x in enumerate(pa):
            pid = newp[i]["id"] if i < len(newp) else pletters[i]
            if not isinstance(x, dict):
                fixed.append({"part_id": pid, "answer": str(x)})
                continue
            y = dict(x)
            if not y.get("part_id"):
                y["part_id"] = y.get("part") or pid
            if not str(y.get("answer") or "").strip():
                alt = y.get("text") or y.get("answer_text") or y.get("response")
                if alt:
                    y["answer"] = alt
            fixed.append(y)
        ans["part_answers"] = fixed
        if ans.get("kind") or fixed:
            out["answer"] = ans
    ans = out.get("answer")
    if isinstance(ans, dict) and not (ans.get("part_answers")) and isinstance(ans.get("parts"), list):
        part_ids = [p.get("id") for p in (out.get("parts") or []) if isinstance(p, dict)]
        lifted = []
        for i, raw in enumerate(ans["parts"]):
            pid = part_ids[i] if i < len(part_ids) and part_ids[i] else "abcdefgh"[i] if i < 8 else str(i + 1)
            if isinstance(raw, str):
                lifted.append({"part_id": pid, "answer": raw})
            elif isinstance(raw, dict):
                text = raw.get("answer") or raw.get("text") or raw.get("answer_text") or ""
                lifted.append({"part_id": raw.get("part_id") or raw.get("part") or pid, "answer": text})
        if lifted:
            ans = dict(ans)
            ans["part_answers"] = lifted
            ans["kind"] = ans.get("kind") or "part_answers"
            out["answer"] = ans
    ans = out.get("answer")
    if isinstance(ans, str):
        token = ans.strip()
        if len(token) == 1 and token.upper() in "ABCDEFGH":
            out["answer"] = {"kind": "single_letter", "letter": token.upper()}
    elif isinstance(ans, dict):
        fixed = dict(ans)
        if not fixed.get("letter") and fixed.get("kind") in (None, "", "single_letter"):
            raw = (
                fixed.get("correct")
                or fixed.get("key")
                or fixed.get("choice")
                or fixed.get("answer_letter")
                or fixed.get("value")
            )
            if isinstance(raw, str):
                token = raw.strip()
                letter = ""
                if len(token) == 1 and token.upper() in "ABCDEFGH":
                    letter = token.upper()
                elif len(token) >= 2 and token[0].upper() in "ABCDEFGH" and token[1] in ".)":
                    letter = token[0].upper()
                if letter:
                    fixed["letter"] = letter
                    fixed["kind"] = "single_letter"
        out["answer"] = fixed
    teach = out.get("teacher") if isinstance(out.get("teacher"), dict) else {}
    teach = dict(teach)
    teach.setdefault("proposed_key_status", "UNVERIFIED")
    teach.setdefault("variation_applied", teach.get("variation_applied") or "V3")
    out["teacher"] = teach
    out.setdefault("schema", "modify_result.v1")
    out.setdefault("status", "OK")
    return out
