"""Python G1–G8 for T-MOD / T-MINT. Same rules as js/kimi.js validateModifyResult.

G3 is figure-word XOR TikZ (presence). G3b/G3c/G3d live in v5_lock.py and are
applied after G3 when the result or spec is a figure rewrite.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy

import v5_lock

FIG_WORD = re.compile(
    r"figure|diagram|shown above|shown below|as shown|the graph|the circuit|the apparatus",
    re.I,
)
VENDOR = re.compile(r"\b(kimi|moonshot|openai|anthropic|chatgpt|claude|astra)\b", re.I)
JOIN = re.compile(
    r"science/grade_\d+|IGCSE:|AS_A:|[SPCBMLQ]\d+/H-[A-Z0-9-]+|\b(?:chem|phy|bio|math):[A-Z]"
)
SMILES = re.compile(r"smiles\s*[:=]|\bSMILES\b", re.I)


def as_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("text") or value.get("stem") or "")
    return str(value or "")


def mentions_figure(text) -> bool:
    return bool(FIG_WORD.search(as_text(text)))


def option_ids(out: dict) -> list[str]:
    return [str(o.get("id")) for o in (out.get("options") or []) if isinstance(o, dict) and o.get("id")]


def is_blank_grid_table(t) -> bool:
    s = t if isinstance(t, str) else json.dumps(t or "")
    if not re.search(r"<table", s, re.I):
        return False
    cells = re.findall(r"<t[dh]\b[^>]*>[\s\S]*?</t[dh]>", s, re.I)
    if len(cells) < 8:
        return False
    empty = 0
    for c in cells:
        inner = re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").strip()
        if len(inner) <= 1:
            empty += 1
    return empty / len(cells) > 0.7


def banned_in_learner(text: str, packet: dict) -> str | None:
    blob = (text or "").lower()
    if re.search(r"\bcandidate\b", blob):
        return "CANDIDATE"
    if VENDOR.search(blob):
        return "vendor"
    mx = ((packet.get("intelligence") or {}).get("mx")) or []
    for row in mx:
        t = (row or {}).get("mx_type") or ""
        n = (row or {}).get("name") or ""
        if t and len(t) > 3 and t.lower() in blob:
            return "mx_type"
        if n and len(n) > 6 and n.lower() in blob:
            return "mx_name"
    if SMILES.search(text or ""):
        return "SMILES"
    return None


def learner_blob(out: dict) -> str:
    opts = []
    for o in out.get("options") or []:
        if isinstance(o, dict):
            opts.append(str(o.get("text") or "") + " " + str(o.get("tikz") or ""))
        else:
            opts.append(str(o))
    parts = []
    for p in (out.get("parts") or []):
        if isinstance(p, dict):
            parts.append(str(p.get("text") or ""))
        else:
            parts.append(str(p or ""))
    stmts = []
    for s in (out.get("statements") or []):
        if isinstance(s, dict):
            stmts.append(str(s.get("text") or ""))
        else:
            stmts.append(str(s or ""))
    return "\n".join([
        str(out.get("stem") or ""),
        "\n".join(opts),
        "\n".join(parts),
        "\n".join(stmts),
        "\n".join(str(t) for t in (out.get("tables") or [])),
        v5_lock.tikz_of(out),
    ])


def fail(gate: str, detail: str = "") -> dict:
    return {"ok": False, "gate": gate, "detail": detail, "v5": None}


def validate(out: dict | None, packet: dict | None, source_item: dict | None = None) -> dict:
    if not out:
        return fail("G1", "empty result")
    if out.get("status") == "REFUSED":
        return fail("REFUSED" if out.get("refusal_reason") else "G1", out.get("refusal_reason") or "")
    if out.get("status") != "OK":
        return fail("G1", "status not OK")
    if not out.get("item_type") or not out.get("stem") or not out.get("answer") or not out.get("teacher"):
        return fail("G1", "missing item_type/stem/answer/teacher")
    if out.get("schema") and out.get("schema") != "modify_result.v1":
        return fail("G1", "schema")
    teacher = out.get("teacher") or {}
    if teacher.get("proposed_key_status") and teacher.get("proposed_key_status") != "UNVERIFIED":
        return fail("G1", "proposed_key_status")

    packet = packet or {}
    spec = packet.get("spec") or {}
    want = spec.get("target_item_type") or "preserve"
    preserved = ((packet.get("source") or {}).get("item_type")) or (
        (source_item or {}).get("item_type")
    )
    itype = out.get("item_type")
    if want == "preserve":
        if preserved and itype != preserved:
            return fail("G2", "item_type drifted from source")
    elif itype != want:
        return fail("G2", "item_type != target")

    ids = option_ids(out)
    ans = out.get("answer") or {}
    if itype == "single_mcq":
        if ans.get("kind") != "single_letter" or not ans.get("letter") or ans.get("letter") not in ids:
            return fail("G2", "single_letter key")
        if ids.count(ans.get("letter")) != 1:
            return fail("G2", "duplicate key letter")
    if itype == "one_or_more":
        letters = list(ans.get("letters") or [])
        uniq = []
        for L in letters:
            if L not in uniq:
                uniq.append(L)
        if ans.get("kind") != "letter_set" or len(uniq) < 2:
            return fail("G2", "letter_set")
        if any(L not in ids for L in uniq):
            return fail("G2", "letter_set missing option")
    if itype == "three_statement":
        stmts = out.get("statements") or []
        if len(stmts) < 2:
            return fail("G2", "statements")
        if ans.get("kind") == "statement_pattern":
            if not ans.get("pattern") or len(ans.get("pattern")) != len(stmts):
                return fail("G2", "pattern length")
        elif ans.get("kind") == "single_letter":
            if not ans.get("letter") or ans.get("letter") not in ids:
                return fail("G2", "three_statement letter")
        else:
            return fail("G2", "three_statement kind")
    if itype == "structured_parts":
        parts = out.get("parts") or []
        pa = ans.get("part_answers") or []
        if not parts or ans.get("kind") != "part_answers":
            return fail("G2", "part_answers")
        for p in parts:
            if not isinstance(p, dict):
                return fail("G2", "part not object")
            pid = p.get("id")
            hit = [x for x in pa if isinstance(x, dict) and x.get("part_id") == pid and str(x.get("answer") or "").strip()]
            if not hit:
                return fail("G2", "part %s" % pid)
            mk = p.get("marks")
            if mk is not None and (mk < 0 or mk > 20 or int(mk) != mk):
                return fail("G2", "marks")
    if itype == "open_response":
        if ans.get("kind") != "rubric" or not ans.get("rubric"):
            return fail("G2", "rubric")
        if ans.get("letter") or ans.get("letters"):
            return fail("G2", "open_response letter")
    if itype in {"option_table", "options_are_figure"}:
        if not ids:
            return fail("G2", "options")
        if itype == "options_are_figure":
            with_fig = [o for o in (out.get("options") or []) if isinstance(o, dict) and o.get("tikz")]
            if not with_fig and not v5_lock.tikz_of(out).strip():
                return fail("G2", "options_are_figure empty")

    fig_mode = ((spec.get("figure") or {}).get("mode")) or "preserve"
    src_tikz = v5_lock.tikz_of(packet.get("source") or {})
    out_tikz = v5_lock.tikz_of(out)
    has_tikz = bool(out_tikz.strip())
    learner_fig = mentions_figure(out.get("stem") or "") or any(
        mentions_figure(p.get("text") if isinstance(p, dict) else p)
        for p in (out.get("parts") or [])
    )
    if has_tikz != learner_fig:
        return fail("G3", "figure-word XOR tikz")
    n_visual = (1 if has_tikz else 0) + sum(
        1 for o in (out.get("options") or []) if isinstance(o, dict) and o.get("tikz")
    )
    if n_visual > 1:
        return fail("G3", "more than one visual")
    if any(is_blank_grid_table(t) for t in (out.get("tables") or [])) and has_tikz:
        return fail("G3", "blank grid beside tikz")
    if not src_tikz.strip() and fig_mode != "add" and has_tikz:
        return fail("G3", "invented figure")
    if fig_mode == "remove" and has_tikz:
        return fail("G3", "mode remove still has tikz")

    ban = banned_in_learner(learner_blob(out), packet)
    if ban:
        return fail("G4", ban)
    dumped = json.dumps(out, default=str)
    if "exam.v1" in dumped:
        return fail("G5", "exam.v1")
    uid = out.get("uid")
    if uid and not re.match(r"^(session:|candidate:)", str(uid)):
        return fail("G5", "uid")

    if ans.get("kind") == "single_letter":
        if not ans.get("letter") or ans.get("letter") not in ids:
            return fail("G6", "letter")
    if ans.get("kind") == "letter_set":
        seen = set()
        for L in ans.get("letters") or []:
            if L in seen or L not in ids:
                return fail("G6", "letter_set")
            seen.add(L)
    if ans.get("kind") == "statement_pattern":
        if not ans.get("pattern") or len(ans.get("pattern")) != len(out.get("statements") or []):
            return fail("G6", "pattern")

    applied = teacher.get("variation_applied")
    want_var = spec.get("variation_class")
    if want_var and applied != want_var:
        return fail("G7", "variation_applied")

    join = (packet.get("intelligence") or {}).get("join_status")
    if JOIN.search(learner_blob(out)):
        return fail("G8", "join code in learner")
    if join == "UNBOUND":
        teach = json.dumps(teacher, default=str)
        if JOIN.search(teach):
            return fail("G8", "join code in teacher")
        title = ((packet.get("intelligence") or {}).get("hinge") or {}).get("title")
        if title and title.lower() in teach.lower():
            return fail("G8", "UNBOUND named hinge title")

    v5 = v5_lock.evaluate(out, packet)
    if not v5.get("ok"):
        return {
            "ok": False,
            "gate": v5.get("gate") or "G3b",
            "detail": ((v5.get("hits") or [{}])[0].get("detail") if v5.get("hits") else ""),
            "v5": v5,
        }
    return {"ok": True, "gate": None, "detail": "", "v5": v5}


def apply_outcome(out: dict | None, packet: dict | None, source_item: dict | None = None) -> dict:
    packet = packet or {}
    if (packet.get("spec") or {}).get("fidelity_mode") == "BLOCKED":
        return {"ok": False, "gate": "BLOCKED", "keepOriginal": True, "v5": None}
    gate = validate(out, packet, source_item)
    if not gate.get("ok"):
        rec = deepcopy(gate)
        rec["keepOriginal"] = True
        return rec
    return {"ok": True, "gate": None, "keepOriginal": False, "v5": gate.get("v5")}
