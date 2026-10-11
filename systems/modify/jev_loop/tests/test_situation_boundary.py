"""The writer packet uses one scored boundary as the situation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import packet_modify as packet


def test_situation_is_the_boundary_most_mixups_produce():
    mx = [
        {"mx_id": "a", "boundary_links": [
            {"boundary": "Ten percent of the energy is not ten percent of the speed.", "p1": 0.90},
            {"boundary": "Final speed comes from the square root.", "p1": 0.92},
        ]},
        {"mx_id": "b", "boundary_links": [
            {"boundary": "Ten percent of the energy is not ten percent of the speed.", "p1": 0.85},
        ]},
        {"mx_id": "c", "canonical_wrong_output": "The lorry is bigger."},
    ]
    boundary = packet.situation_boundary(mx)
    assert boundary == "Ten percent of the energy is not ten percent of the speed."
    chosen = packet.mixups_for_situation(mx, boundary)
    assert [row["mx_id"] for row in chosen] == ["a", "b"]
    assert chosen[0]["boundary_links"] == [{
        "boundary": "Ten percent of the energy is not ten percent of the speed.",
        "p1": 0.90,
    }]


def test_admitted_border_outranks_a_linked_limit():
    mx = [
        {"mx_id": "low", "border": {"text": "Square of speed.", "p1": 0.72, "source": "drafted"}},
        {"mx_id": "high", "border": {"text": "Squared quantity is the speed.", "p1": 0.81, "source": "boundary"}},
        {"mx_id": "none", "border": {"reason": "template"}},
    ]
    chosen = packet.mixups_with_border(mx)
    assert [row["mx_id"] for row in chosen] == ["high", "low"]


def test_probe_parser_reads_the_first_object():
    got = packet.parse_probe('{"text":"A cart doubles its speed."}\nA second note.')
    assert got == {"text": "A cart doubles its speed."}


def test_probe_draft_prompt_keeps_its_json_example():
    text = packet.PROBE_DRAFT.format(
        request="a question on doubling speed",
        law="Kinetic energy changes with the square of speed.",
        border="Kinetic energy changes with the square of speed.",
        sentence="Kinetic energy is proportional to speed.",
    )
    assert '{"text":"..."}' in text
    assert "a question on doubling speed" in text


def test_probe_admits_at_070_and_stops_below_040():
    packet_doc = {
        "units": [{"role": "center", "law_do_not_copy": "K = one-half m v squared"}],
        "misconceptions_mx": [{
            "mx_id": "ke",
            "wrong_output_students_produce": "Kinetic energy is proportional to speed.",
            "border": {"text": "Kinetic energy changes with the square of speed.", "p1": 0.72, "source": "drafted"},
        }],
    }

    def draft(_request, _law, _border, _sentence):
        return {"text": "A 2 kg cart doubles its speed."}

    seen = {"n": 0}

    def score_high(*_args):
        return 0.83

    admitted = packet.admit_probe(packet_doc, "a question on doubling speed", draft, score_high)
    assert admitted["text"] == "A 2 kg cart doubles its speed."
    assert admitted["p1"] == 0.83

    def score_low(*_args):
        seen["n"] += 1
        return 0.22

    empty = packet.admit_probe(packet_doc, "a question on doubling speed", draft, score_low)
    assert empty["reason"] == "probe_not_admitted"
    assert seen["n"] == 1


def test_writer_packet_keeps_every_mixup_and_the_full_law():
    law = "Acid rain is rain whose pH is below 5.6. " + ("threshold " * 80)
    enthalpy = "ΔH < 0, so the reaction is spontaneous."
    mixups = []
    for i in range(7):
        mixups.append({
            "route": f"r{i}",
            "wrong": f"Wrong belief {i}.",
            "observable": f"The learner does {i}.",
            "confused": f"route {i}",
            "border": {"text": f"Border {i}.", "p1": 0.70 + i / 100, "source": "drafted"},
        })
    mixups.append({
        "route": "term_substitution",
        "wrong": enthalpy,
        "observable": "The learner keys from the sign of enthalpy.",
        "confused": "enthalpy sign",
    })
    hinge = {
        "unit_id": "science/grade_11/chem_ch_105/H019",
        "decision": "Use Gibbs energy to predict spontaneity.",
        "law": law,
        "boundaries": [f"Boundary {i} " + ("x" * 200) for i in range(5)],
        "mixups": mixups,
        "mastery": {"not_yet": [enthalpy, "Does not yet separate enthalpy from entropy."]},
        "within_chapter_prerequisites_prose": [
            {"hinge_id": f"science/grade_11/chem_ch_105/H00{i}", "required_capability": "Cap " + ("y" * 400)}
            for i in range(5)
        ],
        "jev_taxonomy_zone": {"admitted": ["Ap.Co.2"], "noul": {"Ap.Co.2": 0.80}},
    }
    original = packet.raw_by_id
    packet.raw_by_id = lambda _subject: {hinge["unit_id"]: hinge}
    try:
        built = packet.packet_for_row(
            {
                "subject": "chemistry",
                "grade": 11,
                "band": "senior_11_12",
                "item_type": "single_mcq",
                "jev_taxonomy": {"hinge_id": hinge["unit_id"], "construct_id": "Ap.Co.2"},
            },
            {"band": "senior_11_12"},
        )
    finally:
        packet.raw_by_id = original
    assert built["ok"]
    writer = built["writer_packet"]
    mx = writer["misconceptions_mx"]
    assert len(mx) == 8
    assert mx[-1]["wrong_output_students_produce"] == enthalpy.rstrip(".")
    assert "border" not in mx[-1]
    assert mx[0]["border"]["text"] == "Border 0."
    center = writer["units"][0]
    assert len(center["law_do_not_copy"]) > 400
    assert "threshold " * 40 in center["law_do_not_copy"]
    assert len(center["boundaries"]) == 5
    assert len(center["boundaries"][0]) > 180
    assert enthalpy in center["not_yet"]
    assert len(writer["prerequisite_gaps"]) == 5
    assert len(writer["prerequisite_gaps"][0]["required_capability"]) > 300
