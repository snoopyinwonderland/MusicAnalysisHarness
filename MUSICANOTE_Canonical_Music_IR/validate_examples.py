"""Validate schemas, fixture layers, and basic Canonical IR references."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).parent


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rational(value: dict) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def validate_references(ir: dict, fixture_name: str) -> None:
    collections = {
        "source_file_id": ir["source_files"],
        "source_ref_id": ir["source_references"],
        "part_id": ir["parts"],
        "staff_id": ir["staves"],
        "voice_id": ir["voices"],
        "measure_id": ir["measures"],
        "note_id": ir["note_events"],
        "rest_id": ir["rest_events"],
        "tie_chain_id": ir["tie_chains"],
        "sounding_event_id": ir["sounding_events"],
        "attack_event_id": ir["attack_events"],
        "chord_onset_group_id": ir["chord_onset_groups"],
    }
    ids = {item[key] for key, items in collections.items() for item in items}
    ids.add(ir["score"]["score_id"])
    for event in ir["note_events"] + ir["rest_events"]:
        for key in ("score_id", "part_id", "display_staff_id", "voice_id", "measure_id", "source_ref_id"):
            assert event[key] in ids, f"{fixture_name}: unresolved {key}={event[key]}"
        measure = next(m for m in ir["measures"] if m["measure_id"] == event["measure_id"])
        expected = rational(measure["global_start_quarter"]) + rational(event["onset_in_measure"])
        assert expected == rational(event["global_onset_quarter"]), f"{fixture_name}: inconsistent onset"
    note_ids = {n["note_id"] for n in ir["note_events"]}
    sound_ids = {s["sounding_event_id"] for s in ir["sounding_events"]}
    for attack in ir["attack_events"]:
        assert attack["note_id"] in note_ids and attack["sounding_event_id"] in sound_ids
    for chain in ir["tie_chains"]:
        assert set(chain["source_note_ids"]) <= note_ids
        assert chain["attack_note_id"] == chain["source_note_ids"][0]
        assert rational(chain["span"]["end"]) - rational(chain["span"]["start"]) == rational(chain["total_duration"])


def main() -> None:
    schemas = {p.stem: load(p) for p in (ROOT / "schemas").glob("*.schema.json")}
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        print(f"schema OK: {name}")

    canonical = Draft202012Validator(schemas["canonical_music_ir.schema"])
    analysis = Draft202012Validator(schemas["analysis_record.schema"])
    evidence = Draft202012Validator(schemas["evidence_record.schema"])
    fixture_count = 0
    for path in sorted((ROOT / "examples").glob("*.json")):
        fixture = load(path)
        canonical.validate(fixture["canonical_ir"])
        for record in fixture["derived_evidence_examples"]:
            evidence.validate(record)
        for record in fixture["later_analysis_examples"]:
            analysis.validate(record)
        validate_references(fixture["canonical_ir"], path.name)
        fixture_count += 1
        print(f"fixture OK: {path.name}")
    assert fixture_count == 5, f"expected 5 fixtures, found {fixture_count}"


if __name__ == "__main__":
    main()
