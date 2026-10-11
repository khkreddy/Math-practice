"""T-MOD: sitting item → route tests on that situation → same-output gate → G1–G8+G3b → ISO examiner → G17 → classify-with-TikZ → G18.

Does not replace T-MINT. The map packet is not the source of the wrong options.
Fail closed. Keys from env. Do not auto-rewrite after a near-miss noul.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
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
from packet import assemble_modify_packet  # noqa: E402
import gates  # noqa: E402
import iso_examiner  # noqa: E402
import v5_lock  # noqa: E402
import miqg_cal  # noqa: E402
import run as mint  # noqa: E402

# Packet-first map loader (current modify law).
if str(MODIFY) not in sys.path:
    sys.path.insert(0, str(MODIFY))
if str(TTWIN_ROOT) not in sys.path:
    sys.path.insert(0, str(TTWIN_ROOT))
import packet_modify  # noqa: E402
import route_derive  # noqa: E402


def append_jsonl(path: Path, rec: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def band_of(grade) -> str:
    try:
        g = int(grade)
    except (TypeError, ValueError):
        return "senior_11_12"
    return mint.band_of(g)


def requirement_from_mod(src: dict, target: str | None, instruction: str, extras: dict | None = None) -> dict:
    extras = extras or {}
    grade = src.get("grade") or extras.get("grade") or 11
    return {
        "schema": "modify_requirement.v1",
        "requirement_id": extras.get("requirement_id") or src.get("id") or "t-mod",
        "target_construct": target,
        "subject": src.get("subject") or extras.get("subject") or "science",
        "grade": int(grade) if str(grade).isdigit() else 11,
        "grade_band": src.get("grade_band") or extras.get("grade_band") or band_of(grade),
        "chapter": src.get("chapter") or extras.get("chapter"),
        "hinge_id": extras.get("hinge_id") or ((src.get("jev_taxonomy") or {}).get("hinge_id")) or "UNBOUND",
        "hinge_title": extras.get("hinge_title") or "",
        "intent": instruction,
        "accept_neighbour": bool(extras.get("accept_neighbour")),
        "variation_class": extras.get("variation_class") or "V5",
    }


def g17(item: dict, req: dict, packet: dict, extra_findings: list | None = None) -> dict:
    result = mint.to_result(item)
    meta = {
        "id": req.get("requirement_id") or "t-mod",
        "subject": req.get("subject"),
        "grade": req.get("grade"),
        "chapter": req.get("chapter"),
        "hinge_id": req.get("hinge_id"),
        "hinge": req.get("hinge_title"),
        "uid": req.get("requirement_id"),
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
        "findings": [
            {
                "code": f.get("code"),
                "severity": f.get("severity"),
                "quote": f.get("quoted_text"),
                "loc": f.get("location"),
            }
            for f in (row.get("findings") or [])
        ],
    }


def log_call(out: Path, phase: str, state: dict, questions: dict, resp: dict | None, err: str | None) -> None:
    rec = {
        "utc": utc_now(),
        "phase": phase,
        "model": MODEL,
        "url": JEV_URL,
        "state_keys": list(state.keys()) if isinstance(state, dict) else None,
        "question_keys": list(questions.keys()),
        "target_in_state": bool(isinstance(state, dict) and state.get("target_construct")),
        "tikz_in_state": bool(isinstance(state, dict) and state.get("tikz")),
        "author_key_in_state": bool(isinstance(state, dict) and (state.get("key") or state.get("key_rationale"))),
        "error": err,
        "usage": (resp or {}).get("usage") if isinstance(resp, dict) else None,
        "answers": (resp or {}).get("answers") if isinstance(resp, dict) else None,
        "stem_excerpt": str((state or {}).get("stem") or "")[:180],
    }
    append_jsonl(out / "jev_calls.jsonl", rec)


def plan_if_needed(req: dict, d: dict, out: Path, key: str | None, skip_plan: bool) -> dict:
    if skip_plan or not req.get("target_construct") or not key:
        return {"skipped": True, "proceed": "proceed_mcq" if skip_plan else None}
    st = mint.plan_state(req, d)
    st["variation_class"] = req.get("variation_class") or "V5"
    st["task"] = (
        "This is a V5 figure rewrite of an existing sitting item. "
        "Guide whether the TARGET cell is honest for the rewritten item. Do not write the stem."
    )
    try:
        resp = jev_call(key, st, design_questions(req.get("grade_band")))
        log_call(out, "T-PLAN", st, design_questions(req.get("grade_band")), resp, None)
        return parse_plan(resp.get("answers") or {})
    except Exception as e:
        log_call(out, "T-PLAN", st, design_questions(req.get("grade_band")), None, str(e))
        raise


def _draft_probe(request: str, law: str, border: str, sentence: str) -> dict:
    prompt = packet_modify.PROBE_DRAFT.format(
        request=(request or "")[:800],
        law=(law or "")[:500],
        border=(border or "")[:500],
        sentence=(sentence or "")[:900],
    )
    if (os.environ.get("LLM_API_URL") or "").strip() and (os.environ.get("LLM_MODEL") or "").strip():
        harness = Path(__file__).resolve().parents[2] / "curriculum_harness" / "src"
        if str(harness) not in sys.path:
            sys.path.insert(0, str(harness))
        from llm import llm
        text, _usage = llm(prompt, system="Return JSON only.")
        return packet_modify.parse_probe(text)
    if (os.environ.get("TTWIN_WRITER_KEY") or "").strip():
        made = mint.call_writer(prompt)
        if isinstance(made, dict) and (made.get("text") or made.get("no_probe")):
            return packet_modify.parse_probe(json.dumps(made))
    return {"no_probe": "drafter_unconfigured"}


def rank_distractors_with_jev(jev_key: str | None, sit: dict, rows: list) -> dict:
    """Score each leftover distractor. 1 = a student mix-up, 0 = implausible."""
    if not jev_key or not rows:
        return {}
    questions = {}
    for row in rows:
        token = str((row or {}).get("id") or "")
        if not token:
            continue
        questions["opt_" + token] = {
            "type": "score",
            "instructions": (
                "Stem: " + str((sit or {}).get("stem") or "")[:500] + "\n"
                "Correct result: " + str((sit or {}).get("key_text") or "")[:240] + "\n"
                "This option: " + str((row or {}).get("text") or "")[:300] + "\n"
                "Score 1 if a student who mixes up this decision would pick this option. "
                "Score 0 if it is implausible, off-topic, or also correct."
            ),
            "criteria": ["0 not a plausible error", "1 plausible student error"],
        }
    if not questions:
        return {}
    data = jev_call(jev_key, {"role": "tmod_distractor_rank"}, questions)
    answers = data.get("answers") if isinstance(data.get("answers"), dict) else {}
    scores = {}
    for row in rows:
        token = str((row or {}).get("id") or "")
        rec = answers.get("opt_" + token) if isinstance(answers.get("opt_" + token), dict) else {}
        probs = rec.get("probabilities") if isinstance(rec.get("probabilities"), dict) else {}
        try:
            scores[token] = float(probs.get("1") or 0)
        except (TypeError, ValueError):
            scores[token] = 0.0
    return scores


def _score_probe(key: str, request: str, law: str, border: str, probe: str, sentence: str) -> float:
    questions = {
        "p0": {
            "type": "score",
            "instructions": packet_modify.PROBE_Q.format(
                request=(request or "")[:800],
                law=(law or "")[:500],
                border=(border or "")[:500],
                probe=(probe or "")[:900],
                sentence=(sentence or "")[:900],
            ),
            "criteria": ["0 criterion not met", "1 criterion met"],
        }
    }
    data = jev_call(key, {"role": "mx_probe"}, questions)
    probs = ((data.get("answers") or {}).get("p0") or {}).get("probabilities") or {}
    if "1" not in probs:
        raise RuntimeError("JEV returned no label-1 for the probe")
    return float(probs["1"])


def _probe_for_request(writer_packet: dict, request: str, jev_key: str | None, out: Path) -> dict:
    """Design the probe for this request and score it. The map does not store it."""
    key = jev_key
    if not key:
        try:
            key = load_jev_key()
        except RuntimeError:
            return {"reason": "probe_unscored"}
    try:
        probe = packet_modify.admit_probe(
            writer_packet,
            request,
            _draft_probe,
            lambda request, law, border, probe, sentence: _score_probe(
                key, request, law, border, probe, sentence
            ),
        )
    except Exception as exc:
        probe = {"note": str(exc)[:200], "reason": "probe_score_failed"}
    append_jsonl(out / "probe.jsonl", {"utc": utc_now(), "probe": probe})
    return probe


def _center_records(writer_packet: dict | None) -> list[dict]:
    rows = []
    if not isinstance(writer_packet, dict):
        return rows
    for raw in writer_packet.get("misconceptions_mx") or []:
        if not isinstance(raw, dict) or not raw.get("mx_id"):
            continue
        rows.append({
            "mx_id": raw.get("mx_id"),
            "route": raw.get("route"),
            "unit_id": raw.get("unit_id") or "",
            "wrong": raw.get("wrong_output_students_produce") or raw.get("canonical_wrong_output") or "",
            "confused": raw.get("confused_element") or "",
            "observable": raw.get("observable_prediction") or "",
            "boundary_links": raw.get("boundary_links") or [],
            "border": raw.get("border") if isinstance(raw.get("border"), dict) else {},
        })
    return rows


def _freeze_phrase(item: dict, writer_packet: dict | None, trail: dict) -> str | None:
    """Map-citation bind kept for inspection. The route path does not call it."""
    from phrase_contract import structural_errors, wrong_slots
    from systems.modify.packet_modify import bind_cited_mx, legal_set_for

    records = _center_records(writer_packet)
    units = (writer_packet or {}).get("units") if isinstance(writer_packet, dict) else []
    center = units[0] if isinstance(units, list) and units and isinstance(units[0], dict) else {}
    unit = {
        "entities": center.get("entities") or [],
        "law": center.get("law_do_not_copy") or center.get("law") or "",
        "decision": center.get("decision_do_not_print") or center.get("decision") or "",
        "mx_records": records,
    }
    slots = wrong_slots(item)
    legal = legal_set_for(records, slots if slots else None)
    trail["legal_set"] = {
        "situation": legal["situation"],
        "situation_verified": legal["situation_verified"],
        "linked_ids": legal["linked_ids"],
        "legal_ids": legal["legal_ids"],
    }
    errors = structural_errors(item, unit, records)
    if slots and len(legal["legal_ids"]) < slots:
        errors.append(
            "legal set has %s mix-ups and the item has %s wrong slots" % (len(legal["legal_ids"]), slots)
        )
    if errors:
        return "phrase: " + "; ".join(errors)[:240]
    allowed = set(legal["legal_ids"])
    err = bind_cited_mx(item, [rec for rec in records if rec.get("mx_id") in allowed])
    return ("mx_bind: " + err[:240]) if err else None


def modify_one(
    source: dict,
    instruction: str,
    *,
    draft: dict | None = None,
    variation_class: str = "V5",
    figure_mode: str = "rewrite",
    declared_delta: str | None = None,
    lbs_followup_of: str | None = None,
    target_construct: str | None = None,
    dictionary: dict | None = None,
    jev_key: str | None = None,
    out: Path | None = None,
    skip_plan: bool = False,
    skip_examine: bool = False,
    skip_classify: bool = False,
    accept_neighbour: bool = False,
    extras: dict | None = None,
) -> dict:
    extras = extras or {}
    out = Path(out) if out else Path("/tmp/t-mod-out")
    out.mkdir(parents=True, exist_ok=True)
    req = requirement_from_mod(source, target_construct, instruction, {
        **extras,
        "accept_neighbour": accept_neighbour,
        "variation_class": variation_class,
        "lbs_followup_of": lbs_followup_of,
    })
    # The map is recorded and not consumed. Options come from the sitting situation.
    try:
        map_pack = packet_modify.packet_for_row(
            source,
            meta={
                "band": req.get("grade_band"),
                "subject": req.get("subject"),
                "grade": req.get("grade"),
            },
        )
    except Exception as exc:
        map_pack = {"ok": False, "empty_reason": str(exc)[:200]}
    situation = route_derive.situation_of(source)
    target_item_type = (draft or {}).get("item_type") or "preserve"
    if situation.get("mode") == "situation" and target_item_type == "preserve":
        target_item_type = situation.get("item_type") or "open_response"
    packet = assemble_modify_packet(
        source.get("item") or source,
        instruction,
        variation_class=variation_class,
        figure_mode=figure_mode,
        target_item_type=target_item_type,
        declared_delta=declared_delta,
        lbs_followup_of=lbs_followup_of,
        hinge=extras.get("hinge"),
        packed_tags=extras.get("packed_tags"),
        item_ref="session:" + str(source.get("id") or extras.get("requirement_id") or "item"),
    )
    trail = {
        "utc": utc_now(),
        "slot": "T-MOD",
        "requirement": req,
        "packet": packet,
        "map_packet": {
            "ok": map_pack.get("ok"),
            "empty_reason": map_pack.get("empty_reason"),
            "extra_hinge_required": map_pack.get("extra_hinge_required"),
            "extra_hinge_ids": map_pack.get("extra_hinge_ids") or [],
            "map_unit_ids": map_pack.get("map_unit_ids") or [],
            "writer_packet": map_pack.get("writer_packet"),
        },
        "steps": ["map loaded, not consumed"],
        "map_consumed": False,
        "serve_eligible": False,
    }
    (out / "packet.json").write_text(json.dumps(packet, indent=2, default=str), encoding="utf-8")
    (out / "map_packet.json").write_text(
        json.dumps(trail["map_packet"], indent=2, default=str), encoding="utf-8"
    )

    if situation.get("error"):
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = str(situation["error"])
        trail["steps"].append("no question situation")
        (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
        return trail

    import key_gate

    pack_units = ((map_pack.get("writer_packet") or {}).get("units") or [])
    pack_unit = pack_units[0] if pack_units and isinstance(pack_units[0], dict) else {}
    key_unit = {
        "decision": pack_unit.get("decision_do_not_print") or pack_unit.get("decision") or "",
        "law": pack_unit.get("law_do_not_copy") or pack_unit.get("law") or "",
    }
    key_report = key_gate.check(situation.get("item") or source.get("item") or source, key_unit, mint.call_writer, req)
    trail["key_gate"] = key_report
    if key_report.get("status") != "PASS":
        trail["status"] = "REFUSED"
        trail["refusal_reason"] = "key: " + str(key_report.get("reason") or "keyed claim is not the result this stem requires")
        trail["steps"].append("T-MOD key refused")
        (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
        return trail
    trail["steps"].append("T-MOD key PASS")

    d = dictionary
    plan = {"skipped": True}
    if target_construct and not skip_plan:
        if d is None:
            raise RuntimeError("construct dictionary required when target_construct is set")
        plan = plan_if_needed(req, d, out, jev_key, skip_plan=False)
        trail["plan"] = plan
        trail["steps"].append("T-PLAN ok")
        if plan.get("proceed") == "abandon_cell":
            trail["abandon_cell"] = True
            trail["status"] = "REFUSED"
            trail["refusal_reason"] = (
                "T-PLAN abandon_cell for "
                + str(target_construct)
                + "; likely_collapse="
                + str(plan.get("likely_collapse"))
            )
            trail["steps"].append("abandon_cell hard-stop")
            trail["retry_same_prompt"] = False
    elif skip_plan:
        trail["steps"].append("T-PLAN skipped (--gates-only or --skip-plan)")

    if draft is not None:
        item, report = route_derive.finish_item(deepcopy(draft), source, variation_class)
        trail["same_output"] = report
        trail["steps"].append("writer skipped (--draft)")
        if item is None:
            trail["status"] = "REFUSED"
            trail["refusal_reason"] = str(report.get("error") or "route gate refused the draft")
            (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
            return trail
    elif trail.get("abandon_cell"):
        item = None
        trail["steps"].append("writer skipped (abandon_cell)")
    else:
        prompt = route_derive.prompt_for(situation, req, variation_class)
        (out / "writer_prompt.txt").write_text(prompt, encoding="utf-8")
        try:
            item, report = route_derive.finish_item(mint.call_writer(prompt), source, variation_class)
            trail["same_output"] = report
            if item is None:
                trail["status"] = "REFUSED"
                trail["refusal_reason"] = str(report.get("error") or "route gate refused the draft")
                (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
                return trail
            trail["steps"].append("writer ok (route derive)")
        except RuntimeError as e:
            trail["status"] = "REFUSED"
            trail["refusal_reason"] = str(e)
            (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
            return trail

    if item is not None and route_derive.needs_four_options(item):
        key = jev_key
        if not key:
            try:
                key = load_jev_key()
            except RuntimeError:
                key = None

        def _rank(rows):
            return rank_distractors_with_jev(key, situation, rows)

        item, pick = route_derive.keep_best_distractors(item, ranker=_rank if key else None)
        trail["distractor_pick"] = pick
        if item is None:
            trail["status"] = "REFUSED"
            trail["refusal_reason"] = str(pick.get("error") or "single_mcq needs three distractors")
            trail["steps"].append("four-option MCQ refused")
            (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
            return trail
        trail["steps"].append(
            "four-option MCQ kept %s unused %s" % (pick.get("kept"), pick.get("unused"))
        )

    if item is not None:
        from phrase_contract import option_shape_errors

        shape_errors = option_shape_errors(item)
        if shape_errors:
            trail["status"] = "REFUSED"
            trail["refusal_reason"] = "phrase: " + "; ".join(shape_errors)[:240]
            trail["item"] = item
            trail["steps"].append("option shape refused")
            (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
            return trail
        gate = gates.apply_outcome(item, packet, source.get("item") or source)
        trail["g1_g8"] = {"ok": gate.get("ok"), "gate": gate.get("gate"), "detail": gate.get("detail")}
        trail["v5_lock"] = gate.get("v5")
        trail["steps"].append("G1-G8+G3b " + ("ok" if gate.get("ok") else str(gate.get("gate"))))
        extra = list(((gate.get("v5") or {}).get("extra_findings")) or [])
        exam = None
        if not skip_examine and jev_key and v5_lock.tikz_of(item).strip():
            try:
                exam = iso_examiner.run(jev_call, jev_key, item, req)
                log_call(out, "T-ISO-EXAMINER", iso_examiner.examiner_state(item, req), iso_examiner.examiner_questions(iso_examiner.letters_of(item)), {"answers": exam.get("answers"), "usage": exam.get("usage")}, None)
                extra.extend(exam.get("extra_findings") or [])
                trail["iso_examiner"] = {k: exam.get(k) for k in ("independent_key", "figure_load_bearing", "stem_figure_agree", "load_bearing_fail", "author_key_in_state")}
                trail["steps"].append("T-ISO-EXAMINER " + str(exam.get("independent_key")))
                if exam.get("load_bearing_fail"):
                    trail["g3e"] = {"ok": False, "gate": "G3e", "detail": exam["load_bearing_fail"]}
            except Exception as e:
                trail["examine_error"] = str(e)
                trail["steps"].append("T-ISO-EXAMINER error")
                if "402" in str(e):
                    trail["status"] = "REFUSED"
                    trail["refusal_reason"] = str(e)
                    (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
                    return trail
        elif skip_examine:
            trail["steps"].append("T-ISO-EXAMINER skipped")

        miqg = g17(item, req, packet, extra_findings=extra)
        trail["miqg"] = miqg
        trail["steps"].append("G17 " + str(miqg.get("quality_tier")))

        tag = None
        if not skip_classify and jev_key and d is not None:
            st = mint.classify_state(item, req)
            q = taxonomy_questions(d)
            try:
                cres = jev_call(jev_key, st, q)
                log_call(out, "T-JEV-CLASSIFY", st, q, cres, None)
                tag = pack_tag(
                    {
                        "id": req["requirement_id"],
                        "subject": req["subject"],
                        "grade": req["grade"],
                        "chapter": req.get("chapter"),
                        "hinge_id": req.get("hinge_id"),
                        "item_type": item.get("item_type"),
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
        elif skip_classify:
            trail["steps"].append("T-JEV-CLASSIFY skipped")

        zone = None
        if req.get("target_construct"):
            bound, reason = mint.unit_bind.bind_requirement(req)
            if reason == "BOUND" and bound is not None:
                zone = set(bound.get("zone") or [])
                trail["unit_bind"] = {"reason": reason, "unit_id": bound.get("unit_id")}
        g18r = mint.g18(req, plan if not plan.get("skipped") else {}, miqg, tag, zone=zone) if req.get("target_construct") else {
            "gate": "G18",
            "status": "NOT_CLAIMED",
            "reason": "no target_construct",
            "construct_hit": False,
        }
        trail["g18"] = g18r
        trail["jev_taxonomy"] = tag
        trail["item"] = item

        figure_ok = bool(gate.get("ok")) and not (trail.get("g3e") or {}).get("gate")
        construct_ok = g18r.get("status") in {"PASS", "PASS_NEIGHBOUR", "PASS_ZONE", "NOT_CLAIMED"}
        abandoned = bool(trail.get("abandon_cell"))
        g17_ok = (
            miqg.get("quality_tier") == "TOP"
            and miqg.get("release_gate") == "PASS"
            and "KEY_WRONG" not in (miqg.get("dq_codes") or [])
        )
        if abandoned:
            trail["status"] = "REFUSED"
        elif not figure_ok:
            trail["status"] = "REFUSED"
            trail["refusal_reason"] = trail.get("refusal_reason") or (
                str(gate.get("gate")) + ": " + str(gate.get("detail") or "")
            )
        elif trail.get("g3e"):
            trail["status"] = "REFUSED"
            trail["refusal_reason"] = trail["g3e"]["detail"]
        elif not g17_ok:
            trail["status"] = g18r.get("status") if g18r.get("status") not in {"PASS", "PASS_NEIGHBOUR"} else (miqg.get("release_gate") or "HOLD")
            if miqg.get("release_gate") == "BLOCK":
                trail["status"] = "BLOCK"
            trail["refusal_reason"] = trail.get("refusal_reason") or (
                "MIQG: tier=" + str(miqg.get("quality_tier"))
                + " release_gate=" + str(miqg.get("release_gate"))
                + " decisive=" + str(miqg.get("decisive_reason"))
            )
        elif not construct_ok:
            trail["status"] = g18r.get("status") or "CONSTRUCT_HOLD"
        else:
            trail["status"] = "OK"
        trail["serve_eligible"] = bool(
            trail["status"] == "OK" and figure_ok and construct_ok and g17_ok and not abandoned
        )
        trail["candidate_write"] = (
            "CANDIDATE" if trail["serve_eligible"] else (
                "CANDIDATE_REPAIR" if miqg.get("release_gate") == "REPAIR" else "HOLD"
            )
        )
        if trail["candidate_write"] != "CANDIDATE":
            trail["serve_eligible"] = False
    else:
        trail["candidate_write"] = "HOLD"

    from phrase_contract import release_record

    trail["release"] = release_record(trail.get("legal_set") if isinstance(trail.get("legal_set"), dict) else {})
    trail["serve_eligible"] = False
    (out / "run.json").write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
    if trail.get("item"):
        (out / "result.json").write_text(json.dumps(trail["item"], indent=2, default=str), encoding="utf-8")
    return trail


def main() -> int:
    ap = argparse.ArgumentParser(description="T-MOD V5 lock: packet, G3b/bind, ISO examiner, classify-with-TikZ")
    ap.add_argument("--source", required=True, help="source item JSON (bank or session record)")
    ap.add_argument("--instruction", default="", help="teacher instruction ≤1000")
    ap.add_argument("--declared-delta", default="", help="what the TikZ rewrite claims to change")
    ap.add_argument("--lbs-followup-of", default="", help="prior item id if this is an LBS follow-up")
    ap.add_argument("--variation", default="V5")
    ap.add_argument("--figure-mode", default="rewrite")
    ap.add_argument("--target-construct", default="", help="optional construct claim; triggers T-PLAN + G18")
    ap.add_argument("--draft", help="skip writer; gate this modify_result.v1")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dictionary")
    ap.add_argument("--accept-neighbour", action="store_true")
    ap.add_argument("--skip-plan", action="store_true")
    ap.add_argument("--skip-examine", action="store_true")
    ap.add_argument("--skip-classify", action="store_true")
    ap.add_argument("--gates-only", action="store_true", help="deterministic G1–G8+G3b+G17 only; no JEV")
    args = ap.parse_args()
    source = json.loads(Path(args.source).read_text(encoding="utf-8"))
    draft = json.loads(Path(args.draft).read_text(encoding="utf-8")) if args.draft else None
    d = None
    if args.dictionary or args.target_construct:
        dpath = mint.find_dictionary(args.dictionary)
        d = json.loads(dpath.read_text(encoding="utf-8"))
    gates_only = bool(args.gates_only)
    key = None
    if not gates_only:
        try:
            key = load_jev_key()
        except RuntimeError:
            if not (args.skip_plan and args.skip_examine and args.skip_classify):
                raise
    trail = modify_one(
        source,
        args.instruction or args.declared_delta,
        draft=draft,
        variation_class=args.variation,
        figure_mode=args.figure_mode,
        declared_delta=args.declared_delta or None,
        lbs_followup_of=args.lbs_followup_of or None,
        target_construct=args.target_construct or None,
        dictionary=d,
        jev_key=key,
        out=Path(args.out),
        skip_plan=gates_only or args.skip_plan,
        skip_examine=gates_only or args.skip_examine,
        skip_classify=gates_only or args.skip_classify,
        accept_neighbour=args.accept_neighbour,
    )
    print(json.dumps(
        {k: trail.get(k) for k in ("status", "g1_g8", "v5_lock", "iso_examiner", "miqg", "g18", "refusal_reason", "abandon_cell", "candidate_write")},
        indent=2,
        default=str,
    ))
    return 0 if trail.get("status") in {"OK", "CONSTRUCT_HOLD", "HOLD", "REFUSED", "BLOCK", "REPAIR"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
