"""Compile modify_packet.v1 with zero model calls. Lookup only; UNBOUND is honest."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from copy import deepcopy

import v5_lock


def packed_item_type(item: dict) -> str:
    if item.get("options_are_figure"):
        return "options_are_figure"
    t = item.get("item_type")
    key = ((item.get("assessment") or {}).get("mcq_key")) or item.get("correct")
    multi = (item.get("assessment") or {}).get("one_or_more") or (
        isinstance(key, str) and len(key) > 1 and all(c in "ABCDEF" for c in key)
    )
    if t == "three_statement":
        return "three_statement"
    if t in {"structured", "structured_parts"}:
        return "structured_parts"
    if t == "open_response":
        return "open_response"
    if t in {"mcq_table", "option_table"}:
        return "option_table"
    if t == "one_or_more" or multi:
        return "one_or_more"
    return "single_mcq"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clip(s, n: int) -> str:
    t = "" if s is None else str(s)
    return t[:n]


def _options(item: dict) -> list[dict]:
    opts = item.get("options")
    out = []
    if isinstance(opts, dict):
        for k in ("A", "B", "C", "D", "E", "F"):
            if opts.get(k) is None:
                continue
            v = opts[k]
            if isinstance(v, dict):
                out.append({"id": k, "text": clip(v.get("text") or "", 1000)})
            else:
                out.append({"id": k, "text": clip(v, 1000)})
        return out
    for o in opts or []:
        if isinstance(o, dict):
            oid = str(o.get("id") or "").strip()
            if not oid:
                continue
            rec = {"id": oid, "text": clip(o.get("text") or "", 1000)}
            if o.get("tikz"):
                rec["tikz"] = clip(o.get("tikz"), 6000)
            out.append(rec)
    return out


def _key(item: dict):
    ans = item.get("answer") or item.get("key")
    if isinstance(ans, str) and re_letter(ans):
        return {"kind": "single_letter", "letter": ans}
    if not isinstance(ans, dict):
        letter = item.get("correct") or item.get("answer_letter")
        if isinstance(letter, str) and re_letter(letter):
            return {"kind": "single_letter", "letter": letter}
        return None
    kind = ans.get("kind")
    if kind == "single_letter" and ans.get("letter"):
        return {"kind": "single_letter", "letter": ans["letter"]}
    if kind == "letter_set" and ans.get("letters"):
        return {"kind": "letter_set", "letters": list(ans["letters"])}
    if kind == "statement_pattern" and ans.get("pattern"):
        return {"kind": "statement_pattern", "pattern": list(ans["pattern"])}
    if ans.get("letter"):
        return {"kind": "single_letter", "letter": ans["letter"]}
    return None


def re_letter(s: str) -> bool:
    return isinstance(s, str) and len(s) == 1 and "A" <= s <= "F"


def assemble_modify_packet(
    item: dict,
    instruction: str,
    *,
    variation_class: str = "V5",
    figure_mode: str = "rewrite",
    target_item_type: str = "preserve",
    declared_delta: str | None = None,
    lbs_followup_of: str | None = None,
    hinge: dict | None = None,
    packed_tags: dict | None = None,
    join_status: str | None = None,
    item_ref: str | None = None,
) -> dict:
    """Minimal compiler for the Python T-MOD path. Does not fetch maps.

    Cambridge grafts with no hinge row stay UNBOUND. That is a stamp, not a rescue.
    """
    itype = packed_item_type(item)
    options = _options(item)
    tikz = clip(v5_lock.tikz_of(item), 6000)
    bound = bool(hinge and (hinge.get("primary") or hinge.get("title")))
    status = join_status or ("BOUND" if bound else "UNBOUND")
    ref = item_ref or "session:" + str(item.get("id") or item.get("uid") or item.get("source_id") or "item")
    tags = packed_tags or {
        "pack": "senior_11_12",
        "subject": str(item.get("subject") or "science")[:40],
        "level": "",
        "topic": "",
        "paper_hint": "",
    }
    fig = {"mode": figure_mode, "tikz_required": figure_mode in {"rewrite", "add"}}
    if declared_delta:
        fig["declared_delta"] = clip(declared_delta, 300)
    if lbs_followup_of:
        fig["lbs_followup_of"] = clip(lbs_followup_of, 80)
    packet = {
        "schema": "modify_packet.v1",
        "packet_id": ref[:60],
        "slot": "T-MOD",
        "created_at": utc_now(),
        "source": {
            "item_ref": clip(ref, 80),
            "item_type": itype,
            "stem": clip(item.get("stem") or item.get("stem_lead") or "", 4000),
            "options": options,
            "statements": (item.get("statements") or [])[:5],
            "parts": (item.get("parts") or [])[:8],
            "equations": [clip(e, 1000) for e in (item.get("equations") or [])][:6],
            "tables": [clip(t if isinstance(t, str) else json.dumps(t), 1000) for t in (item.get("tables") or [])][:6],
            "tikz": tikz,
            "key": _key(item),
        },
        "intelligence": {
            "join_status": status,
            "hinge": deepcopy(hinge) if bound else None,
            "packed_tags": tags,
            "mx": [],
            "enrichment": None,
            "lbs_recipe": None,
            "modify_seeds": [],
        },
        "spec": {
            "instruction": clip(instruction or "", 1000),
            "variation_class": variation_class,
            "fidelity_mode": "FAITHFUL_TRANSFER",
            "target_item_type": target_item_type,
            "format": {"n_options": max(2, min(6, len(options) or 4))},
            "figure": fig,
        },
        "caps": {"hard_total_chars": 16000, "tightened_from": "40_PACKETS"},
        "assembly": {
            "builder": "assembleModifyPacket",
            "trimmed": [],
            "slim_map_ref": "python-tmod",
        },
    }
    order = ["enrichment", "lbs_recipe", "mx_notes", "node_labels", "enrichment_drop"]
    while len(json.dumps(packet, default=str)) > 16000 and order:
        step = order.pop(0)
        packet["assembly"]["trimmed"].append(step)
        if step == "enrichment":
            enr = packet["intelligence"].get("enrichment")
            packet["intelligence"]["enrichment"] = clip(enr, 400) if enr else None
        elif step == "lbs_recipe":
            packet["intelligence"]["lbs_recipe"] = None
        elif step == "mx_notes":
            packet["intelligence"]["mx"] = [
                {"mx_type": m.get("mx_type"), "name": m.get("name")}
                for m in (packet["intelligence"].get("mx") or [])
            ]
        elif step == "node_labels" and packet["intelligence"].get("hinge"):
            packet["intelligence"]["hinge"]["node_labels"] = []
        elif step == "enrichment_drop":
            packet["intelligence"]["enrichment"] = None
    return packet
