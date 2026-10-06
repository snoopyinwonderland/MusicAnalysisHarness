"""Factorized geometry over every context in a frozen integration cohort.

Window selection is label-independent; historical cohort admission is not.
No synthetic SOURCE/alignment records, new chord candidates or NCT verdicts
are created. All source revisions and old abstentions remain separate.
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

from .harmony_breadth_trial import freeze_score
from .harmony_factorized_voice_trial import _unit, DEFAULT_CONFIG
from .musical_pattern_observation import digest
from .musical_role_evidence_trial import ROOT, read, write_new, file_digest
from .source_locator_revision_trial import _load, validate_policy
from .source_physical_measure_revision import revise, validate_revision
from .frozen_context_observation import observe, validate_observation

VERSION = "frozen-context-voice-trial-0.1.0"


def _code_paths():
    return [*sorted((ROOT / "src/musicanote_harness").glob("*.py")),
            *sorted((ROOT / "docs/harmony/schemas").glob("*.json")),
            ROOT / "MUSICANOTE_Canonical_Music_IR/schemas/canonical_music_ir.schema.json"]


def _guard(paths, hashes):
    for name, expected in paths.items():
        path = Path(name).resolve(strict=True)
        observed = file_digest(path)
        if observed != expected:
            raise ValueError("input_hash_mismatch:" + str(path))
        if str(path) in hashes and hashes[str(path)] != observed:
            raise ValueError("input_changed_while_loading:" + str(path))
        hashes[str(path)] = observed


def _unique(rows, key, error):
    result = {}
    for row in rows:
        identity = key(row)
        if identity in result:
            raise ValueError(error)
        result[identity] = row
    return result


def _key(row):
    return row["pair_id"], row["plan_index"], row["sample_id"]


def _directory_inventory(directory, hashes, *, exact=None):
    directory = Path(directory).resolve(strict=True)
    actual = {str(p.resolve()) for p in directory.rglob("*") if p.is_file()}
    declared = ({name for name in hashes if Path(name).is_relative_to(directory)}
                if exact is None else set(exact))
    if actual != declared:
        raise ValueError("parent_artifact_inventory_mismatch:" + str(directory)
                         + ":unregistered=" + repr(sorted(actual - declared))
                         + ":missing=" + repr(sorted(declared - actual)))
    return actual


def _flags(value, true_fields, false_fields, error):
    if (any(value.get(field) is not True for field in true_fields)
            or any(value.get(field) is not False for field in false_fields)):
        raise ValueError(error)


def _inputs(integration):
    """Load/hash exact parents, never inspect harmony annotation labels."""
    hashes = {}
    report = _load(integration / "report.json", hashes)
    if report.get("version") != "harmony-context-integration-trial-0.1.0":
        raise ValueError("unsupported_integration_version")
    _flags(report, ("complete", "inputs_and_code_unchanged", "artifacts_unchanged"),
           ("source_labels_used", "accuracy_measured", "production_modified", "annotation_retargeted",
            "gold_promoted", "training_promoted", "external_transmission", "engine_recomputed",
            "operating_core_modified", "gate_changed"), "unsafe_integration_report")
    contract = _load(integration / "run-contract.json", hashes, report["contract_sha256"])
    if contract.get("version") != report["version"]:
        raise ValueError("integration_contract_version_mismatch")
    _guard(report["artifact_hashes"], hashes)
    if any(not Path(name).is_relative_to(integration) for name in report["artifact_hashes"]):
        raise ValueError("foreign_integration_artifact")
    _directory_inventory(integration, hashes)
    _guard(contract["input_hashes"], hashes)
    _guard(contract["code_hashes"], hashes)
    breadth = Path(contract["breadth_trial"]).resolve(strict=True)
    replay = Path(contract["source_replay_trial"]).resolve(strict=True)
    breadth_report = _load(breadth / "report.json", hashes)
    breadth_contract = _load(breadth / "run-contract.json", hashes)
    replay_report = _load(replay / "report.json", hashes)
    replay_contract = _load(replay / "run-contract.json", hashes, replay_report["contract_sha256"])
    if (breadth_report.get("version") != "harmony-breadth-trial-0.1.1"
            or breadth_contract.get("version") != breadth_report["version"]
            or replay_report.get("version") != "source-sequence-replay-trial-0.1.0"
            or replay_contract.get("version") != replay_report["version"]):
        raise ValueError("unsupported_upstream_version")
    _flags(breadth_report, ("complete", "inputs_unchanged"),
           ("source_labels_used", "accuracy_measured"), "unsafe_breadth_report")
    _flags(replay_report, ("complete", "inputs_and_code_unchanged", "artifacts_unchanged"),
           ("source_labels_used", "accuracy_measured", "production_modified",
            "annotation_retargeted", "engine_recomputed", "gate_changed"), "unsafe_replay_report")
    _guard(breadth_contract["input_hashes"], hashes)
    _guard(replay_contract["input_hashes"], hashes)
    # Old breadth engines were subsequently versioned; their frozen outputs
    # are consumed, not executed. Do not require historical producer code to
    # equal today's code or accidentally rerun it to recreate old stages.
    _guard(replay_report["artifact_hashes"], hashes)
    plan = _load(breadth / "frozen-plan.json", hashes, breadth_contract["frozen_plan_sha256"])
    if plan.get("version") != breadth_report["version"]:
        raise ValueError("frozen_plan_version_mismatch")
    packages = _unique(plan["packages"], lambda r: r["pair_id"], "duplicate_frozen_package")
    revisions = _unique(report["measure_revisions"], lambda r: r["pair_id"], "duplicate_revision")
    replay_rows = _unique(replay_report["records"], lambda r: r["pair_id"], "duplicate_replay_package")
    if (not packages or set(packages) != set(revisions) or set(packages) != set(replay_rows)
            or len(packages) != report["summary"]["packages"]
            or len(packages) != breadth_report["frozen_packages"]
            or len(packages) != replay_report["summary"]["packages"]):
        raise ValueError("frozen_package_coverage_mismatch")
    if len({p["source"]["manifest_entry"]["work_family_id"] for p in packages.values()}) != report["summary"]["work_families"]:
        raise ValueError("work_family_denominator_mismatch")
    expected = {}
    for pair, package in packages.items():
        if package["source"]["pair_id"] != pair:
            raise ValueError("package_source_identity_mismatch")
        validate_policy(package["source"]["manifest_entry"])
        for row in package["plan"]["selected_samples"]:
            key = pair, row["plan_index"], row["sample"]["sample_id"]
            if key in expected:
                raise ValueError("duplicate_frozen_context")
            expected[key] = row
    current = _unique(report["records"], _key, "duplicate_integration_context")
    original = _unique(breadth_report["records"], _key, "duplicate_breadth_context")
    if (set(current) != set(expected) or set(original) != set(expected)
            or len(expected) != report["summary"]["samples"]
            or len(expected) != breadth_report["executed_windows"]):
        raise ValueError("frozen_context_coverage_mismatch")
    if dict(Counter(r["previous_status"] for r in current.values())) != report["summary"]["previous_statuses_retained"]:
        raise ValueError("integration_original_status_denominator_mismatch")
    if dict(Counter(r["status"] for r in original.values())) != breadth_report["status_counts"]:
        raise ValueError("breadth_original_status_denominator_mismatch")
    for key, row in current.items():
        if row["previous_status"] != original[key]["status"]:
            raise ValueError("original_status_changed")
        _guard({original[key]["artifact"]: original[key]["sha256"]}, hashes)
        if hashes.get(str(Path(row["artifact"]).resolve())) != row["sha256"]:
            raise ValueError("unregistered_context_packet")
    # These producer diagnostics were not harmonic input artifacts in the old
    # integration contract. Freeze their bytes/inventory without using their
    # contents for admission, sampling, or geometry.
    for diagnostic in ("inventory.json", "progress.json"):
        path = breadth / diagnostic
        if path.is_file():
            _guard({str(path): file_digest(path)}, hashes)
    for package in packages.values():
        source_path = Path(package["source"]["frozen_ir_path"]).parent / "provenance.json"
        if source_path.is_file():
            if _load(source_path, hashes) != package["source"]:
                raise ValueError("breadth_source_provenance_mismatch")
    inventories = {str(integration): _directory_inventory(integration, hashes),
                   str(breadth): _directory_inventory(breadth, hashes),
                   str(replay): _directory_inventory(replay, hashes)}
    return {"hashes": hashes, "inventories": inventories, "report": report,
            "contract": contract, "breadth_contract": breadth_contract,
            "packages": packages, "revisions": revisions, "replay_rows": replay_rows,
            "contexts": current, "original": original, "expected": expected}


def _case(package, revision_row, replay_row, hashes, samples_per_lane):
    info = package["source"]
    entry = info["manifest_entry"]
    validate_policy(entry)
    if (info["pitch_policy"].get("harmonic_replay_allowed") is not True
            or info["source_files"].get(entry["score_source_path"]) != entry["score_sha256"]
            or entry["annotation_sha256"] not in info["source_files"].values()):
        raise ValueError("source_policy_or_identity_mismatch")
    _guard(info["source_files"], hashes)
    _guard({info["original_ir_path"]: info["ir_sha256"]}, hashes)
    parent = _load(info["frozen_ir_path"], hashes, info["ir_sha256"])
    _load(info["preparation_path"], hashes, info["preparation_sha256"])
    if (parent["ir_document_id"] != entry["ir_document_id"]
            or parent["score"]["score_id"] != entry["score_id"]):
        raise ValueError("historical_parent_identity_mismatch")
    # Reproduce only the label-blind selector, not harmonic/NCT engines.
    if freeze_score(parent, per_lane=samples_per_lane) != package["plan"]:
        raise ValueError("frozen_selector_reconstruction_mismatch")
    replay = _load(replay_row["artifact"], hashes, replay_row["sha256"], compressed=True)
    if (replay["pair_id"] != package["pair_id"] or replay["manifest_entry"] != entry
            or replay["pitch_policy"] != info["pitch_policy"]):
        raise ValueError("replay_policy_identity_mismatch")
    snapshot = replay["parent_snapshot"]
    _guard({snapshot["parent_ir"]: info["ir_sha256"], snapshot["source_xml"]: entry["score_sha256"]}, hashes)
    sidecar = _load(revision_row["sidecar"], hashes)
    if sidecar["verification_payload"] != replay:
        raise ValueError("revision_replay_origin_mismatch")
    if revision_row["candidate_created"] is True:
        working = _load(revision_row["candidate_ir"], hashes)
        validate_revision(parent, working, sidecar)
    elif revision_row["candidate_created"] is False and revision_row["candidate_ir"] is None:
        candidate, rebuilt = revise(parent, replay)
        if candidate is not None or rebuilt != sidecar or sidecar["status"] != "not_required":
            raise ValueError("unverified_not_required_revision")
        working = parent
    else:
        raise ValueError("invalid_explicit_revision_selection")
    if (revision_row["parent_ir_document_id"] != parent["ir_document_id"]
            or revision_row["working_ir_document_id"] != working["ir_document_id"]
            or revision_row["status"] != sidecar["status"]):
        raise ValueError("working_revision_index_mismatch")
    return parent, working, sidecar


def _origin_args(package, revision, sidecar, parent, current, packet, old_packet, plan_row):
    return {"integration_index_row": current, "integration_packet": packet,
            "original_stored_packet": old_packet, "frozen_plan_row": plan_row,
            "package": package, "revision_row": revision,
            "revision_sidecar": sidecar, "parent_ir": parent}


def _ref(record):
    return {"record_id": record["record_id"], "record_sha256": record["record_sha256"]}


def _gzip_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    with path.open("xb") as stream:
        stream.write(gzip.compress(raw, mtime=0))


def run(integration, output, **options):
    started = perf_counter()
    integration, output = Path(integration).resolve(strict=True), Path(output).resolve()
    if (output.exists() or output == ROOT / "output" or not output.is_relative_to(ROOT / "output")
            or output.parent != ROOT / "output"
            or output.is_relative_to(integration)):
        raise ValueError("output_must_be_new_workspace_output_directory")
    if set(options) - set(DEFAULT_CONFIG) or any(type(v) is not int or v < 1 for v in options.values()):
        raise ValueError("invalid_factor_trial_budget")
    config = {**DEFAULT_CONFIG, **options}
    data = _inputs(integration)
    inputs = data["hashes"]
    # Reject a stale selector/source/revision before creating any output. Keep
    # only metadata between packages rather than all full-score IRs in RAM.
    for pair, package in data["packages"].items():
        _case(package, data["revisions"][pair], data["replay_rows"][pair],
              inputs, data["breadth_contract"]["samples_per_lane"])
    code = {str(p.resolve()): file_digest(p) for p in _code_paths()}
    plan = {"version": VERSION, "integration": str(integration), "inputs": deepcopy(inputs),
            "code": code, "config": config,
            "expected_context_keys": [list(key) for key in data["contexts"]],
            "selection": "every frozen context, no passing-only subset or resampling",
            "lane_inventory": "all context-observed note/rest lanes with tie/chord/grace-anchor closure; not silent full-score lanes",
            "target_policy": "full_frozen_context",
            "historical_cohort_dependency": "score+annotation exact identity and historical alignment admission",
            "window_selector": "IR attack groups and explicit-lane quantiles, label-independent",
            "source_annotation_labels_consumed": False, "synthetic_SOURCE_records_created": False,
            "legacy_geometry_recomputed_or_enumerated": False, "harmonic_engine_recomputed": False,
            "probe_selection": "three arithmetic/partition controls per ready graph, not musical evidence",
            "environment": {"python": sys.version, "packages": {name: importlib.metadata.version(name)
                            for name in ("music21", "jsonschema", "referencing")}}}
    output.mkdir(parents=True)
    (output / "observations").mkdir()
    # New computations append only; parent inventories/hash maps are frozen.
    write_new(output / "run-plan.json", plan)
    artifacts = {str((output / "run-plan.json").resolve()): file_digest(output / "run-plan.json")}
    observations, units, statuses, reasons = [], [], Counter(), Counter()
    old_statuses, old_stages, probes, counts = Counter(), {}, Counter(), Counter()
    maximum_count = "0"
    expected_units = set()
    context_number = 0
    for pair, package in data["packages"].items():
        parent, ir, sidecar = _case(package, data["revisions"][pair], data["replay_rows"][pair],
                                    inputs, data["breadth_contract"]["samples_per_lane"])
        ir_before = digest(ir)
        for key, current in data["contexts"].items():
            if key[0] != pair:
                continue
            context_number += 1
            old_row = data["original"][key]
            packet = _load(current["artifact"], inputs, current["sha256"], compressed=True)
            original = _load(old_row["artifact"], inputs, old_row["sha256"], compressed=True)
            if (packet["provenance"]["reused_stage_artifact"] != old_row["artifact"]
                    or packet["provenance"]["reused_stage_sha256"] != old_row["sha256"]
                    or original["sample"] != data["expected"][key]["sample"]
                    or old_row["lane"] != original["sample"]["lane"]
                    or old_row["span"] != original["sample"]["span"]
                    or current["previous_status"] != original["summary"]["status"]):
                raise ValueError("parent_context_packet_or_index_mismatch")
            origin = _origin_args(package, data["revisions"][pair], sidecar, parent,
                                  current, packet, original, data["expected"][key])
            observation = observe(ir, **origin)
            validate_observation(observation, ir=ir)
            if observation["scope"]["ir_content_sha256"] != ir_before:
                raise ValueError("observation_working_IR_changed")
            obs_path = output / "observations" / (observation["record_id"] + ".json")
            write_new(obs_path, observation)
            artifacts[str(obs_path.resolve())] = file_digest(obs_path)
            raw_lanes = [[row["part_id"], row["voice_id"]] for row in observation["raw_lanes"]]
            if len({tuple(lane) for lane in raw_lanes}) != len(raw_lanes):
                raise ValueError("duplicate_observed_raw_lane")
            declared = {(key, tuple(lane)) for lane in raw_lanes}
            if expected_units.intersection(declared):
                raise ValueError("duplicate_context_lane_identity")
            expected_units.update(declared)  # Declared before eligibility/query.
            before = digest([observation, packet, original])
            for lane in raw_lanes:
                try:
                    unit = _unit(ir, observation, lane, config)
                except Exception as exc:
                    unit = {"status": "integrity_or_computation_abstention", "reasons": [f"{type(exc).__name__}:{exc}"],
                            "graph": None, "constraint_probes": [], "legacy_geometry_comparison": None}
                result = {"version": VERSION, "context_key": list(key), "observation_ref": _ref(observation),
                          "lane": lane, "original_stage_statuses": deepcopy(packet["bundle"]["stage_statuses"]),
                          "original_final_status": current["previous_status"], "unit": unit,
                          "parent_context_artifact": deepcopy(current),
                          "selected": None, "harmonic_or_role_claim": False, "training_eligible": False,
                          "generation_ready": False}
                path = output / "units" / observation["record_id"] / (digest(lane)[:16] + ".json.gz")
                _gzip_new(path, result)
                artifacts[str(path.resolve())] = file_digest(path)
                units.append({"context_key": list(key), "observation_ref": _ref(observation), "lane": lane,
                              "status": unit["status"], "reasons": unit["reasons"],
                              "artifact": str(path), "sha256": file_digest(path)})
                statuses[unit["status"]] += 1
                reasons.update(unit["reasons"])
                graph = unit["graph"]
                if graph is not None:
                    counts["positive_sound_instances"] += len(graph["events"])
                    counts["point_sound_instances"] += len(graph["point_sound_refs"])
                    counts["factor_instances"] += len(graph["factors"])
                    if graph["status"] == "ready":
                        candidate_count = graph["possible_assignments"]
                        if (len(candidate_count), candidate_count) > (len(maximum_count), maximum_count):
                            maximum_count = candidate_count
                        counts["ready_units_from_original_held_contexts"] += current["previous_status"] != "ready"
                for probe in unit["constraint_probes"]:
                    probes[probe["answer"]["status"]] += 1
                    counts["witness_instances"] += probe["witness"] is not None
            if digest([observation, packet, original]) != before:
                raise ValueError("context_inputs_mutated")
            observations.append({"context_key": list(key), **_ref(observation), "path": str(obs_path),
                                 "sha256": file_digest(obs_path), "raw_lane_count": len(raw_lanes),
                                 "original_final_status": current["previous_status"],
                                 "original_stage_statuses": deepcopy(packet["bundle"]["stage_statuses"])})
            old_statuses[current["previous_status"]] += 1
            for stage, status in packet["bundle"]["stage_statuses"].items():
                old_stages.setdefault(stage, Counter())[status] += 1
            print(f"[{context_number}/{len(data['contexts'])}] frozen context; raw-lane units={len(units)}", flush=True)
        if digest(ir) != ir_before:
            raise ValueError("working_IR_mutated_during_package")
    actual_units = {(tuple(r["context_key"]), tuple(r["lane"])) for r in units}
    if (len(units) != len(expected_units) or actual_units != expected_units
            or {tuple(r["context_key"]) for r in observations} != set(data["contexts"])):
        raise ValueError("context_or_raw_lane_denominator_loss")
    if (dict(old_statuses) != data["report"]["summary"]["previous_statuses_retained"]
            or {k: dict(v) for k, v in old_stages.items()} != data["report"]["summary"]["stage_statuses_retained"]):
        raise ValueError("original_stage_status_inventory_changed")
    write_new(output / "observation-index.json", observations)
    write_new(output / "unit-index.json", units)
    for index_path in (output / "observation-index.json", output / "unit-index.json"):
        artifacts[str(index_path.resolve())] = file_digest(index_path)
    changed = [name for name, sha in {**inputs, **code}.items()
               if not Path(name).is_file() or file_digest(name) != sha]
    if set(map(lambda p: str(p.resolve()), _code_paths())) != set(code):
        changed.append("source_or_schema_inventory_changed")
    for directory, inventory in data["inventories"].items():
        if {str(p.resolve()) for p in Path(directory).rglob("*") if p.is_file()} != inventory:
            changed.append("parent_artifact_inventory_changed:" + directory)
    # Detect any newly loaded input missing from the pre-computation plan.
    if plan["inputs"] != inputs:
        changed.append("input_inventory_changed_while_computing")
    changed_artifacts = [name for name, sha in artifacts.items()
                         if not Path(name).is_file() or file_digest(name) != sha]
    actual_artifacts = {str(p.resolve()) for p in output.rglob("*") if p.is_file()}
    if actual_artifacts != set(artifacts):
        changed_artifacts.append("output_artifact_inventory_changed")
    integrity = statuses["integrity_or_computation_abstention"] == 0
    report = {"version": VERSION, "complete": not changed and not changed_artifacts and integrity,
              "inputs_and_code_unchanged": not changed, "computation_integrity_passed": integrity,
              "artifacts_unchanged": not changed_artifacts,
              "summary": {"packages": len(data["packages"]),
                          "work_families": data["report"]["summary"]["work_families"],
                          "contexts": len(observations), "raw_lane_units": len(units),
                          "status_counts": dict(statuses), "reason_counts": dict(reasons),
                          "original_final_statuses_preserved": dict(old_statuses),
                          "original_stage_statuses_preserved": {k: dict(v) for k, v in old_stages.items()},
                          "probe_status_counts": dict(probes), **dict(counts),
                          "largest_geometry_assignment_count": maximum_count,
                          "human_validated": 0, "training_eligible": 0, "gold_eligible": 0,
                          "generation_ready": 0, "independent_piece_count": None},
              "artifact_hashes": artifacts, "changed_artifacts": changed_artifacts,
              "changed_inputs_or_code": changed, "elapsed_seconds": perf_counter() - started,
              "musical_accuracy_measured": False, "source_labels_used_for_inference": False,
              "synthetic_SOURCE_records_created": False, "legacy_inventory_recomputed_or_enumerated": False,
              "old_harmony_or_nct_inventory_modified": False, "core_or_production_modified": False,
              "score_viewer_modified": False, "external_transmission": False,
              "limits": ["The cohort inherits annotation/alignment admission; window selection alone is label-independent.",
                         "Context-observed lanes retain all parts and linked notation, not silent full-score voices.",
                         "Geometry readiness and exact control counts are not harmonic, NCT, role or musical accuracy.",
                         "No SOURCE statement/alignment has been fabricated, and the old SOURCE gate is unchanged.",
                         "Historical source locators/extensions stay parent-bound; no annotation retarget or concert-pitch certification.",
                         "This cohort does not admit the separately held orchestral sources."]}
    write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("integration", "output"):
        parser.add_argument("--" + name, required=True)
    for name, default in DEFAULT_CONFIG.items():
        parser.add_argument("--" + name.replace("_", "-"), type=int, default=default)
    report = run(**vars(parser.parse_args()))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
