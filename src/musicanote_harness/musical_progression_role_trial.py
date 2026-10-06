"""Frozen G1 windows -> competing path / assignment / literal role links.

Every raw lane is attempted independently. Source harmony is neither a provider
nor an answer; Pedal statements select the old fixed windows, not their roles.
Budgets hold whole units and never substitute the first favorable assignment.
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

from .harmony_breadth_trial import source_transposition
from .harmony_context_bundle import bundle
from .harmony_progression_context import build as build_lattice
from .harmony_progression_search import search
from .harmony_voice_paths import observe as observe_voice
from .musical_pattern_observation import digest, f, validate_observation
from .musical_role_evidence import analyze as literal_roles, ref
from .musical_role_evidence_trial import ROOT, _case, _inputs, file_digest, read, write_new
from .musical_progression_role_link import prepare_context, link_prepared, validate_link_prepared
from .musical_semantic_alignment import validate_alignment

VERSION = "musical-progression-role-trial-0.1.1"
DEFAULT_CONFIG = {"max_edges": 256, "max_segments": 4, "per_state_limit": 2,
                  "max_complete_paths": 8, "transition_budget": 200000,
                  "max_assignments": 64, "max_role_links": 128}


def _write_gzip(path, value):
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    with Path(path).open("xb") as stream:
        stream.write(gzip.compress(data, mtime=0))


def _code_paths():
    return [*sorted((ROOT / "src/musicanote_harness").glob("*.py")),
            *sorted((ROOT / "docs/harmony/schemas").glob("*.json")),
            ROOT / "MUSICANOTE_Canonical_Music_IR/schemas/canonical_music_ir.schema.json"]


def _unit(ir, observation, lane, pitch_policy, config):
    """One raw lane's NCT assignments, all-part harmony, all-lane literal roles."""
    context = observation["scope"]["context_span"]
    result = {"lane": deepcopy(lane), "status": "blocked", "reasons": [],
              "voice_inventory": None, "bundle": None, "search": None, "links": [],
              "planned_role_links": None, "role_link_inventory_complete": False,
              "selected": None, "musical_accuracy_measured": False}
    if pitch_policy.get("harmonic_replay_allowed") is not True:
        return {**result, "status": "source_pitch_abstention",
                "reasons": ["source_transposition_not_supported"]}
    a, b = f(context["start"]), f(context["end"])
    events = [s for s in ir["sounding_events"] if f(s["span"]["start"]) < b and f(s["span"]["end"]) > a]
    if any(f(s["span"]["start"]) == f(s["span"]["end"]) and a <= f(s["span"]["start"]) < b
           for s in ir["sounding_events"]):
        return {**result, "status": "grace_context_abstention",
                "reasons": ["legacy_progression_geometry_does_not_support_grace_points"]}
    voices = observe_voice(ir, context, lane)
    result["voice_inventory"] = voices
    if not voices["enumeration_complete"]:
        return {**result, "status": "voice_inventory_abstention", "reasons": voices["abstention_reasons"]}
    if len(voices["assignments"]) > config["max_assignments"]:
        return {**result, "status": "assignment_budget_abstention",
                "reasons": ["entire_assignment_inventory_held_before_candidate_computation"]}
    lattice = build_lattice(ir, {"status": "ready", "span": deepcopy(context),
                                "events": deepcopy(events), "assignments": deepcopy(voices["assignments"])},
                           max_edges=config["max_edges"])
    sample = {"sample_id": "rolecontext_" + digest([ref(observation), lane])[:24],
              "span": deepcopy(context), "lane": deepcopy(lane),
              "target_span": deepcopy(observation["scope"]["target_span"])}
    stored = {"sample": sample, "summary": {"source_labels_used": False},
              "stages": {"lattice": lattice,
                         "relations": {"status": "not_requested_in_role_link_trial", "plan": {"pairs": []}, "results": []},
                         "hold_change": {"status": "not_requested_in_role_link_trial", "chain_comparisons": []}}}
    result["bundle"] = context_bundle = bundle(ir, stored)
    proposals = search(context_bundle, **{k: config[k] for k in
                       ("max_segments", "per_state_limit", "max_complete_paths", "transition_budget")})
    result["search"] = proposals
    if lattice["status"] != "ready":
        return {**result, "status": "lattice_abstention", "reasons": [lattice["status"]]}
    rows, assignments = proposals["proposals"], voices["assignments"]
    work = len(rows) * len(assignments)
    result["planned_role_links"] = work
    if not rows:
        return {**result, "status": "no_complete_proposal", "reasons": [proposals["status"]]}
    if len(assignments) > config["max_assignments"] or work > config["max_role_links"]:
        return {**result, "status": "role_link_budget_abstention",
                "reasons": ["entire_proposal_assignment_inventory_held_no_subset"]}
    prepared = prepare_context(ir, observation, context_bundle, pitch_policy=pitch_policy,
                               search_result=proposals)
    for number, proposal in enumerate(rows, 1):
        for assignment in assignments:
            aid = assignment["assignment_id"]
            value = link_prepared(prepared, proposal, aid)
            validate_link_prepared(value, prepared, proposal, aid)
            result["links"].append(value)
        print(f"  role/progression proposals={number}/{len(rows)} links={len(result['links'])}/{work}", flush=True)
    if len(result["links"]) != work:
        raise ValueError("role_link_inventory_loss")
    return {**result, "status": "conditional_links_not_verdict", "role_link_inventory_complete": True}


def run(alignment, output, **options):
    start = perf_counter()
    alignment, output = Path(alignment).resolve(strict=True), Path(output).resolve()
    if (output.exists() or not output.is_relative_to(ROOT / "output") or output == ROOT / "output"
            or output.is_relative_to(alignment)):
        raise ValueError("output_must_be_new_workspace_output_directory")
    if set(options) - set(DEFAULT_CONFIG):
        raise ValueError("unknown_role_trial_option")
    config = {**DEFAULT_CONFIG, **options}
    if any(type(v) is not int or v < 1 for v in config.values()):
        raise ValueError("invalid_role_trial_budget")
    inputs, index = _inputs(alignment)
    attempts = read(alignment / "alignment-attempts.json")
    code_paths = _code_paths()
    code = {str(p): file_digest(p) for p in code_paths}
    plan = {"version": VERSION, "alignment": str(alignment), "inputs": inputs, "code": code,
            "config": config, "pattern_refs": [{k: row[k] for k in ("record_id", "record_sha256", "path")} for row in index],
            "selection": "every frozen observation x every raw lane; no new score or passing-only selection",
            "harmony_source": "label_blind_existing_candidate_catalog_not_source_RomanText",
            "replay_strategy": "private immutable context/proposal reuse; assignment-specific accounting freshly replayed",
            "assignment_scope": "one raw lane at a time, never a union of its or other lanes' assignments",
            "environment": {"python": sys.version, "packages": {n: importlib.metadata.version(n)
                            for n in ("music21", "jsonschema", "referencing")}},
            "source_labels_used_for_inference": False, "external_transmission": False}
    output.mkdir(parents=True)
    write_new(output / "run-plan.json", plan)
    cache, rows, counts, statuses = {}, [], Counter(), Counter()
    unique_tracks, unique_roles = set(), set()
    expected_units = 0
    for number, row in enumerate(index, 1):
        path = Path(row["path"]); directory = path.parent
        if directory not in cache:
            ir, meter, sources = _case(directory, inputs)
            scores = [p for p in directory.iterdir() if p.name in ("score.musicxml", "score.mxl")]
            # G1 snapshots currently XML; do not parse compressed bytes as XML.
            if scores[0].suffix.lower() != ".musicxml":
                policy = {"harmonic_replay_allowed": False, "reason": "compressed_transpose_probe_not_implemented"}
            else:
                policy = source_transposition(scores[0])
                if any("chromatic" not in row for row in policy["source_transpose_elements"]):
                    policy.update(harmonic_replay_allowed=False,
                                  reason="incomplete_source_transpose_declaration")
            policy.update(source_path=str(scores[0]), source_sha256=file_digest(scores[0]),
                          ir_content_sha256=digest(ir), pitch_basis="written_IR_not_concert_certified")
            cache[directory] = (ir, policy, meter, sources)
        ir, policy, meter, sources = cache[directory]
        observation = read(path)
        source = [s for s in sources if ref(s) == observation["scope"]["source_statement_ref"]]
        matched = [a["alignment"] for a in attempts if a["status"] == "exact_coordinate"
                   and ref(a["alignment"]) == observation["scope"]["alignment_ref"]]
        if len(source) != 1 or len(matched) != 1:
            raise ValueError("missing_or_duplicate_observation_source_or_alignment")
        validate_alignment(matched[0], source=source[0], ir=ir, meter_index=meter)
        if matched[0]["binding"] != {k: observation["scope"][k] for k in
                                    ("score_id", "ir_document_id", "ir_content_sha256", "source_files", "target_span")}:
            raise ValueError("observation_alignment_binding_mismatch")
        validate_observation(observation, ir=ir)
        literal = literal_roles(ir, observation, ())
        name = digest(ref(observation))[:24]
        folder = output / "observations" / name; folder.mkdir(parents=True)
        write_new(folder / "literal-role-evidence.json", literal)
        lanes = [[r["part_id"], r["voice_id"]] for r in observation["raw_lanes"]]
        if len({tuple(l) for l in lanes}) != len(lanes):
            raise ValueError("duplicate_raw_lane")
        expected_units += len(lanes)
        for lane in lanes:
            before = digest([ir, observation])
            try:
                unit = _unit(ir, observation, lane, policy, config)
            except Exception as exc:
                unit = {"lane": lane, "status": "integrity_or_computation_abstention",
                        "reasons": [f"{type(exc).__name__}:{exc}"], "links": [],
                        "role_link_inventory_complete": False, "selected": None}
            if digest([ir, observation]) != before:
                raise ValueError("role_trial_mutated_ir_or_observation")
            target = folder / (digest(lane)[:16] + ".json.gz")
            packet = {"version": VERSION, "observation_ref": ref(observation), "scope": deepcopy(observation["scope"]),
                      "literal_evidence_ref": ref(literal),
                      "literal_evidence_path": str(folder / "literal-role-evidence.json"),
                      "pitch_policy": deepcopy(policy), "unit": unit,
                      "selected": None, "source_labels_used_for_inference": False,
                      "training_eligible": False, "generation_ready": False}
            _write_gzip(target, packet)
            rows.append({"observation_ref": ref(observation), "lane": lane,
                         "status": unit["status"], "reasons": unit["reasons"], "links": len(unit["links"]),
                         "planned_role_links": unit.get("planned_role_links"),
                         "artifact": str(target), "sha256": file_digest(target)})
            statuses[unit["status"]] += 1; counts["role_link_instances"] += len(unit["links"])
            for value in unit["links"]:
                # Nested records keep the complete accounting; counts are not accuracy.
                counts["proposal_assignment_instances"] += 1
                unique_tracks.add(value["harmony_assumption_track"]["record_id"])
                unique_roles.add(value["role_evidence"]["record_id"])
                counts["active_nct_pattern_link_instances"] += len(value["active_pattern_links"])
        print(f"[{number}/{len(index)}] role/progression lane units={len(rows)} links={counts['role_link_instances']}", flush=True)
    if len(rows) != expected_units or len({(r["observation_ref"]["record_id"], tuple(r["lane"])) for r in rows}) != expected_units:
        raise ValueError("role_trial_denominator_loss")
    write_new(output / "unit-index.json", rows)
    changed = [p for p, sha in {**inputs, **code}.items() if file_digest(p) != sha]
    if set(str(p) for p in _code_paths()) != set(code):
        changed.append("source_or_schema_inventory_changed")
    if {str(p.resolve()) for p in alignment.rglob("*") if p.is_file()} != set(inputs):
        changed.append("upstream_artifact_inventory_changed")
    artifacts = {str(p): file_digest(p) for p in output.rglob("*") if p.is_file()}
    computation_integrity_passed = not statuses["integrity_or_computation_abstention"]
    report = {"version": VERSION, "complete": not changed and computation_integrity_passed,
              "inputs_and_code_unchanged": not changed,
              "computation_integrity_passed": computation_integrity_passed,
              "summary": {"score_files": len(cache), "observations": len(index), "raw_lane_units": expected_units,
                          "status_counts": dict(statuses), **dict(counts), "human_validated": 0,
                          "unique_harmony_assumption_tracks": len(unique_tracks),
                          "unique_conditional_role_evidence_records": len(unique_roles),
                          "training_eligible": 0, "gold_eligible": 0, "generation_ready": 0,
                          "independent_piece_count": None},
              "artifact_hashes": artifacts, "changed_inputs_or_code": changed,
              "elapsed_seconds": perf_counter() - start, "core_or_production_modified": False,
              "prepared_context_reuse_used": True,
              "source_or_previous_outputs_modified": False, "score_viewer_modified": False,
              "source_labels_used_for_inference": False, "external_transmission": False,
              "musical_accuracy_measured": False,
              "limits": ["Pedal-selected windows are biased and overlapping; role links are not independent correct harmonies.",
                         "Raw lane identity and sampled NCT assignments are separate, neither is a semantic voice verdict.",
                         "The source text fixes old window coordinates but never supplies the inferred chord or role.",
                         "Grace, source-transposition, enumeration, interval and link budgets remain explicit abstentions.",
                         "No comparison winner, new role classifier, arpeggio confirmation, generation or operating viewer migration.",
                         "This trial does not backfill the older 322 harmony contexts or certify concert pitch."]}
    write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment", required=True); parser.add_argument("--output", required=True)
    for name, default in DEFAULT_CONFIG.items():
        parser.add_argument("--" + name.replace("_", "-"), type=int, default=default)
    args = vars(parser.parse_args())
    report = run(args.pop("alignment"), args.pop("output"), **args)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
