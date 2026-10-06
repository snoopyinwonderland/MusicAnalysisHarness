"""Lossless geometry factors for the frozen G1 raw-lane denominator.

This does not replace old NCT inventories or authorize new harmony verdicts.
The three deterministic constraint probes are integrity checks, not musical
queries or votes. Every old abstention remains in the output unchanged.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import importlib.metadata
import json
from pathlib import Path
import sys
from time import perf_counter

from .harmony_factorized_voice_paths import (
    factorize, query, validate_graph, validate_query, materialize_witness)
from .harmony_voice_paths import partition
from .harmony_path_contrast import token
from .musical_pattern_observation import digest, f, q, validate_observation
from .musical_role_evidence import ref
from .musical_role_evidence_trial import ROOT, _inputs, _case, read, write_new, file_digest
from .musical_semantic_alignment import validate_alignment

VERSION = "factorized-voice-trial-0.1.1"
DEFAULT_CONFIG = {"max_events": 4096, "max_factors": 4096,
                  "max_edges": 65536, "work_budget": 100000}


def _code_paths():
    return [*sorted((ROOT / "src/musicanote_harness").glob("*.py")),
            *sorted((ROOT / "docs/harmony/schemas").glob("*.json")),
            ROOT / "MUSICANOTE_Canonical_Music_IR/schemas/canonical_music_ir.schema.json"]


def _protected_baseline(baseline, alignment_hashes):
    report_path = baseline / "report.json"
    report = read(report_path)
    if (report.get("version") != "musical-progression-role-trial-0.1.1"
            or report.get("complete") is not True
            or report.get("inputs_and_code_unchanged") is not True
            or report.get("computation_integrity_passed") is not True):
        raise ValueError("completed_supported_role_baseline_required")
    hashes = report["artifact_hashes"]
    actual = {str(p.resolve()) for p in baseline.rglob("*") if p.is_file() and p != report_path}
    if set(hashes) != actual:
        raise ValueError("baseline_artifact_inventory_mismatch")
    for name, expected in hashes.items():
        path = Path(name).resolve(strict=True)
        if not path.is_relative_to(baseline) or file_digest(path) != expected:
            raise ValueError("baseline_artifact_changed")
    plan = read(baseline / "run-plan.json")
    if plan.get("inputs") != alignment_hashes:
        raise ValueError("baseline_alignment_inventory_mismatch")
    if plan.get("version") != report["version"]:
        raise ValueError("baseline_plan_version_mismatch")
    # The new module may add files, but never changes old frozen source/schema.
    for name, expected in plan["code"].items():
        if file_digest(name) != expected:
            raise ValueError("baseline_producer_source_changed")
    rows = read(baseline / "unit-index.json")
    keys = [(r["observation_ref"]["record_id"], tuple(r["lane"])) for r in rows]
    if len(keys) != len(set(keys)) or len(rows) != report["summary"]["raw_lane_units"]:
        raise ValueError("baseline_duplicate_or_missing_raw_lane")
    for row in rows:
        path = Path(row["artifact"]).resolve(strict=True)
        if (not path.is_relative_to(baseline) or str(path) not in hashes
                or row["sha256"] != hashes[str(path)]):
            raise ValueError("unregistered_baseline_unit")
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            packet = json.load(stream)
        unit = packet["unit"]
        if (packet["observation_ref"] != row["observation_ref"] or unit["lane"] != row["lane"]
                or unit["status"] != row["status"] or unit["reasons"] != row["reasons"]
                or len(unit.get("links", [])) != row["links"]):
            raise ValueError("baseline_packet_index_mismatch")
    protected = {**hashes, str(report_path): file_digest(report_path), **plan["code"]}
    return protected, {key: deepcopy(row) for key, row in zip(keys, rows)}


def _probe(graph, required_links, forbidden_links, kind, work_budget):
    answer = query(graph, required_links=required_links,
                   forbidden_links=forbidden_links, work_budget=work_budget)
    validate_query(graph, answer, required_links=required_links,
                   forbidden_links=forbidden_links, work_budget=work_budget)
    witness = None
    if answer["status"] == "exact_count":
        witness = materialize_witness(graph, answer)
        assignment = witness["assignment"]
        links = assignment["links"]
        if assignment["tracks"] != partition(graph["events"], links):
            raise ValueError("query_witness_partition_mismatch")
        if assignment["legacy_geometry_id"] != "vpaths_" + token([graph["lane"], graph["span"], links]):
            raise ValueError("query_witness_legacy_identity_mismatch")
        completion_id = "vfcompletion_" + digest([graph["record_sha256"], answer["record_sha256"], links])[:24]
        if assignment["assignment_id"] != completion_id or assignment["completion_id"] != completion_id:
            raise ValueError("query_witness_bound_identity_mismatch")
        if any(pair not in links for pair in required_links) or any(pair in links for pair in forbidden_links):
            raise ValueError("query_witness_constraint_mismatch")
    return {"probe_kind": kind, "musical_claim": False,
            "required_links": deepcopy(required_links), "forbidden_links": deepcopy(forbidden_links),
            "answer": answer, "witness": witness}


def _literal_positive_lane(ir, context, lane):
    """Independent literal projection, never choices or legacy assignments."""
    start, end = f(context["start"]), f(context["end"])
    notes = {row["note_id"]: row for row in ir["note_events"]}
    events = []
    for sound in ir["sounding_events"]:
        a, b = f(sound["span"]["start"]), f(sound["span"]["end"])
        if b <= a or a >= end or b <= start:
            continue
        source_notes = [notes.get(nid) for nid in sound["source_note_ids"]]
        if not source_notes or any(note is None for note in source_notes):
            continue
        identities = {(note.get("part_id"), note.get("voice_id")) for note in source_notes}
        if identities == {tuple(lane)}:
            events.append(sound)
    events.sort(key=lambda sound: (f(sound["span"]["start"]), sound["sounding_event_id"]))
    note_time = sum((min(end, f(sound["span"]["end"]))
                     - max(start, f(sound["span"]["start"])) for sound in events), f(q(0)))
    return events, q(note_time)


def _unit(ir, observation, lane, config, baseline_voice_inventory=None):
    context = observation["scope"]["context_span"]
    graph = factorize(ir, context, lane,
                      **{key: config[key] for key in ("max_events", "max_factors", "max_edges")})
    validate_graph(graph, ir=ir, span=context, lane=lane)
    literal_events, literal_note_time = _literal_positive_lane(ir, context, lane)
    if graph["events"] != literal_events or graph["total_observed_note_time"] != literal_note_time:
        raise ValueError("factor_graph_lost_literal_positive_geometry")
    legacy = baseline_voice_inventory
    if legacy is not None:
        legacy_positive = [sound for sound in legacy["events"]
                           if f(sound["span"]["end"]) > f(sound["span"]["start"])]
        if (legacy["span"] != context or legacy["lane"] != list(lane)
                or graph["events"] != legacy_positive
                or graph["total_observed_note_time"] != legacy["total_observed_note_time"]):
            raise ValueError("factor_graph_lost_frozen_legacy_positive_geometry")
        if graph["status"] == "ready" and legacy["enumeration_complete"]:
            if graph["possible_assignments"] != str(legacy["possible_assignments"]):
                raise ValueError("factor_count_differs_from_complete_legacy_inventory")
    probes = []
    if graph["status"] == "ready":
        edges = [[a, b] for factor in graph["factors"]
                 for a in factor["source_refs"] for b in factor["target_refs"]]
        required = [[factor["source_refs"][0], factor["target_refs"][0]]
                    for factor in graph["factors"]]
        specs = [((), (), "unconstrained_count_and_sparse_completion"),
                 (required, (), "joint_required_edges_not_independent_witness_union"),
                 ((), edges, "all_edges_forbidden_no_link_control")]
        for required_links, forbidden_links, kind in specs:
            probes.append(_probe(graph, list(required_links), list(forbidden_links), kind, config["work_budget"]))
        if (probes[0]["answer"]["status"] == "exact_count"
                and probes[0]["answer"].get("possible_assignments") != graph["possible_assignments"]):
            raise ValueError("unconstrained_count_mismatch")
        if probes[-1]["answer"]["status"] == "exact_count":
            if (probes[-1]["answer"].get("possible_assignments") != "1"
                    or probes[-1]["witness"]["assignment"]["links"]):
                raise ValueError("no_link_control_mismatch")
    return {"graph": graph, "legacy_geometry_comparison": {
                "events_and_note_time_identical": True,
                "literal_IR_projection_checked": True,
                "prior_inventory_available": legacy is not None,
                "prior_geometry_checked": legacy is not None,
                "prior_inventory_not_computed": legacy is None,
                "legacy_recomputed_or_enumerated": False,
                "legacy_enumeration_complete": None if legacy is None else legacy["enumeration_complete"],
                "legacy_possible_assignments": None if legacy is None else legacy["possible_assignments"],
                "legacy_abstention_reasons": None if legacy is None else deepcopy(legacy["abstention_reasons"]),
                "old_inventory_replaced": False},
            "constraint_probes": probes, "status": graph["status"], "reasons": graph["reasons"]}


def run(alignment, baseline, output, **options):
    start = perf_counter()
    alignment, baseline, output = Path(alignment).resolve(strict=True), Path(baseline).resolve(strict=True), Path(output).resolve()
    if (output.exists() or not output.is_relative_to(ROOT / "output") or output == ROOT / "output"
            or output.is_relative_to(alignment) or output.is_relative_to(baseline)):
        raise ValueError("output_must_be_new_workspace_output_directory")
    if set(options) - set(DEFAULT_CONFIG) or any(type(v) is not int or v < 1 for v in options.values()):
        raise ValueError("invalid_factor_trial_budget")
    config = {**DEFAULT_CONFIG, **options}
    alignment_hashes, index = _inputs(alignment)
    baseline_hashes, previous = _protected_baseline(baseline, alignment_hashes)
    inputs = {**alignment_hashes, **baseline_hashes}
    code = {str(p): file_digest(p) for p in _code_paths()}
    expected = []
    for row in index:
        observation = read(row["path"])
        expected.extend((row["record_id"], (lane["part_id"], lane["voice_id"]))
                        for lane in observation["raw_lanes"])
    if len(expected) != len(set(expected)) or set(expected) != set(previous):
        raise ValueError("baseline_and_current_lane_denominator_mismatch")
    for row in index:
        observation = read(row["path"])
        for raw_lane in observation["raw_lanes"]:
            key = (row["record_id"], (raw_lane["part_id"], raw_lane["voice_id"]))
            if previous[key]["observation_ref"] != ref(observation):
                raise ValueError("baseline_observation_content_reference_mismatch")
    plan = {"version": VERSION, "alignment": str(alignment), "baseline": str(baseline),
            "inputs": inputs, "code": code, "config": config,
            "pattern_refs": [{key: row[key] for key in ("record_id", "record_sha256", "path")} for row in index],
            "selection": "same frozen observation x every raw lane, no harmonic eligibility filter",
            "representation": "exact touching partial matchings, independent boundary factors",
            "legacy_comparison": "read_frozen_inventory_only; unavailable_stays_unavailable; independent_literal_IR_projection_for_all_units",
            "probe_selection": "three geometry-integrity controls per ready graph, not musical evidence",
            "environment": {"python": sys.version, "packages": {name: importlib.metadata.version(name)
                            for name in ("music21", "jsonschema", "referencing")}},
            "concert_pitch_certified": False, "source_labels_used_for_inference": False,
            "old_harmony_or_nct_inventory_modified": False, "external_transmission": False}
    output.mkdir(parents=True)
    write_new(output / "run-plan.json", plan)
    attempts = read(alignment / "alignment-attempts.json")
    cache, rows, statuses, probe_statuses = {}, [], Counter(), Counter()
    old_statuses, recovered_statuses = Counter(), Counter()
    counts = Counter()
    maximum_count = "0"
    for number, row in enumerate(index, 1):
        directory = Path(row["path"]).parent
        if directory not in cache:
            cache[directory] = _case(directory, alignment_hashes)
        ir, meter, sources = cache[directory]
        observation = read(row["path"])
        matched_source = [s for s in sources if ref(s) == observation["scope"]["source_statement_ref"]]
        matched_alignment = [a["alignment"] for a in attempts if a["status"] == "exact_coordinate"
                             and ref(a["alignment"]) == observation["scope"]["alignment_ref"]]
        if len(matched_source) != 1 or len(matched_alignment) != 1:
            raise ValueError("missing_or_duplicate_parent_alignment")
        validate_alignment(matched_alignment[0], source=matched_source[0], ir=ir, meter_index=meter)
        if matched_alignment[0]["binding"] != {key: observation["scope"][key] for key in
                ("score_id", "ir_document_id", "ir_content_sha256", "source_files", "target_span")}:
            raise ValueError("parent_alignment_observation_binding_mismatch")
        validate_observation(observation, ir=ir)
        for raw_lane in observation["raw_lanes"]:
            lane = [raw_lane["part_id"], raw_lane["voice_id"]]
            key = (row["record_id"], tuple(lane))
            before = digest([ir, observation])
            try:
                with gzip.open(previous[key]["artifact"], "rt", encoding="utf-8") as stream:
                    baseline_voice_inventory = json.load(stream)["unit"].get("voice_inventory")
                unit = _unit(ir, observation, lane, config, baseline_voice_inventory)
            except Exception as exc:
                unit = {"status": "integrity_or_computation_abstention", "reasons": [f"{type(exc).__name__}:{exc}"],
                        "graph": None, "constraint_probes": [], "legacy_geometry_comparison": None}
            if digest([ir, observation]) != before:
                raise ValueError("factor_trial_mutated_input")
            packet = {"version": VERSION, "observation_ref": ref(observation),
                      "scope": deepcopy(observation["scope"]), "lane": lane,
                      "baseline_unit": deepcopy(previous[key]), "unit": unit,
                      "selected": None, "harmonic_or_role_claim": False,
                      "training_eligible": False, "generation_ready": False}
            folder = output / "observations" / digest(ref(observation))[:24]
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / (digest(lane)[:16] + ".json.gz")
            raw = json.dumps(packet, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
            with path.open("xb") as stream:
                stream.write(gzip.compress(raw, mtime=0))
            rows.append({"observation_ref": ref(observation), "lane": lane, "status": unit["status"],
                         "reasons": unit["reasons"], "baseline_status": previous[key]["status"],
                         "artifact": str(path), "sha256": file_digest(path)})
            statuses[unit["status"]] += 1
            old_statuses[previous[key]["status"]] += 1
            graph = unit["graph"]
            if graph is not None:
                counts["positive_sound_instances"] += len(graph["events"])
                counts["point_sound_instances"] += len(graph["point_sound_refs"])
                counts["factor_instances"] += len(graph["factors"])
                if graph["status"] == "ready":
                    candidate_count = graph["possible_assignments"]
                    if (len(candidate_count), candidate_count) > (len(maximum_count), maximum_count):
                        maximum_count = candidate_count
                    legacy_complete = unit["legacy_geometry_comparison"]["legacy_enumeration_complete"]
                    if legacy_complete is False:
                        counts["ready_graphs_with_legacy_enumeration_abstention"] += 1
                    if legacy_complete is None:
                        counts["ready_graphs_without_prior_voice_inventory"] += 1
                    recovered_statuses[previous[key]["status"]] += 1
            for probe in unit["constraint_probes"]:
                probe_statuses[probe["answer"]["status"]] += 1
                counts["probe_instances"] += 1
                counts["witness_instances"] += probe["witness"] is not None
        print(f"[{number}/{len(index)}] factorized geometry units={len(rows)}", flush=True)
    if len(rows) != len(expected) or {(r["observation_ref"]["record_id"], tuple(r["lane"])) for r in rows} != set(expected):
        raise ValueError("factor_trial_denominator_loss")
    write_new(output / "unit-index.json", rows)
    changed = [name for name, sha in {**inputs, **code}.items() if not Path(name).is_file() or file_digest(name) != sha]
    if set(map(str, _code_paths())) != set(code):
        changed.append("source_or_schema_inventory_changed")
    if {str(p.resolve()) for p in alignment.rglob("*") if p.is_file()} != set(alignment_hashes):
        changed.append("alignment_artifact_inventory_changed")
    baseline_files = {str(p.resolve()) for p in baseline.rglob("*") if p.is_file()}
    if baseline_files != {name for name in baseline_hashes if Path(name).is_relative_to(baseline)}:
        changed.append("baseline_artifact_inventory_changed")
    integrity = not statuses["integrity_or_computation_abstention"]
    report = {"version": VERSION, "complete": not changed and integrity,
              "inputs_and_code_unchanged": not changed, "computation_integrity_passed": integrity,
              "summary": {"score_files": len(cache), "observations": len(index), "raw_lane_units": len(expected),
                          "status_counts": dict(statuses), "original_status_counts_preserved": dict(old_statuses),
                          "ready_graphs_by_original_status": dict(recovered_statuses),
                          "probe_status_counts": dict(probe_statuses), **dict(counts),
                          "largest_geometry_assignment_count": maximum_count,
                          "count_representation": "nonnegative_decimal_string_not_probability",
                          "counts_are_confidence": False, "human_validated": 0, "training_eligible": 0,
                          "gold_eligible": 0, "generation_ready": 0, "independent_piece_count": None},
              "artifact_hashes": {str(p): file_digest(p) for p in output.rglob("*") if p.is_file()},
              "changed_inputs_or_code": changed, "elapsed_seconds": perf_counter() - start,
              "musical_accuracy_measured": False, "source_labels_used_for_inference": False,
              "legacy_inventory_recomputed_or_enumerated": False,
              "old_harmony_or_nct_inventory_modified": False, "core_or_production_modified": False,
              "score_viewer_modified": False, "external_transmission": False,
              "limits": ["Geometry factors are not semantic voice identities or confirmed NCT.",
                         "Global products are represented, not enumerated, selected or assigned probabilities.",
                         "Probes are arithmetic/partition controls; their witnesses cannot be promoted or merged as music evidence.",
                         "Original grace, candidate meter/silence, harmony and NCT abstentions remain unchanged.",
                         "Pedal-selected sampling bias, old 322 context provenance and pitch certification remain separate work."]}
    write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("alignment", "baseline", "output"):
        parser.add_argument("--" + name, required=True)
    for name, default in DEFAULT_CONFIG.items():
        parser.add_argument("--" + name.replace("_", "-"), type=int, default=default)
    args = vars(parser.parse_args())
    report = run(**args)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
