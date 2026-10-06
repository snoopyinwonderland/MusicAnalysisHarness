"""Append-only source-clock diagnostics over a protected frozen geometry run.

The stored geometry, probes and old semantic abstentions are not recomputed.
Diagnostic completion is distinct from consistency: an inherited IR conflict
is a successful diagnostic result, never a musical or XML certification.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .frozen_context_observation import validate_observation, _revision
from .musical_pattern_observation import digest, f, span_bounds
from .sounding_lineage_audit import audit_sounding_lineage, validate_audit

ROOT = Path(__file__).resolve().parents[2]
VERSION = "frozen-context-lineage-trial-0.1.0"
BASELINE_VERSION = "frozen-context-voice-trial-0.1.0"


def read(path, *, compressed=False):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if compressed else raw)


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def _code_paths():
    return [*sorted((ROOT / "src/musicanote_harness").glob("*.py")),
            *sorted((ROOT / "docs/harmony/schemas").glob("*.json")),
            ROOT / "MUSICANOTE_Canonical_Music_IR/schemas/canonical_music_ir.schema.json"]


def _guard(declared, hashes):
    for name, expected in declared.items():
        path = Path(name).resolve(strict=True)
        if str(path) != name or file_digest(path) != expected:
            raise ValueError("input_hash_mismatch:" + name)
        if name in hashes and hashes[name] != expected:
            raise ValueError("conflicting_input_hash:" + name)
        hashes[name] = expected


def _load(path, hashes, *, compressed=False):
    path = Path(path).resolve(strict=True)
    if str(path) not in hashes or file_digest(path) != hashes[str(path)]:
        raise ValueError("unregistered_or_changed_input:" + str(path))
    return read(path, compressed=compressed)


def _inventory(directory, hashes):
    directory = Path(directory).resolve(strict=True)
    actual = {str(p.resolve()) for p in directory.rglob("*") if p.is_file()}
    declared = {name for name in hashes if Path(name).is_relative_to(directory)}
    if actual != declared:
        raise ValueError("parent_artifact_inventory_mismatch:" + str(directory))
    return actual


def _unique(rows, key, error):
    result = {}
    for row in rows:
        identity = key(row)
        if identity in result:
            raise ValueError(error)
        result[identity] = row
    return result


def _key(row):
    return tuple(row["context_key"])


def _ref(record):
    return {"record_id": record["record_id"], "record_sha256": record["record_sha256"]}


def _inputs(baseline):
    """Verify stored parents, without executing their producer or selector."""
    report_path = baseline / "report.json"
    report = read(report_path)
    if (report.get("version") != BASELINE_VERSION
            or any(report.get(flag) is not True for flag in
                   ("complete", "inputs_and_code_unchanged", "computation_integrity_passed", "artifacts_unchanged"))
            or any(report.get(flag) is not False for flag in
                   ("musical_accuracy_measured", "source_labels_used_for_inference", "synthetic_SOURCE_records_created",
                    "legacy_inventory_recomputed_or_enumerated", "old_harmony_or_nct_inventory_modified",
                    "core_or_production_modified", "external_transmission"))
            or report.get("changed_artifacts") != [] or report.get("changed_inputs_or_code") != []):
        raise ValueError("completed_supported_frozen_baseline_required")
    artifacts = report["artifact_hashes"]
    actual = {str(p.resolve()) for p in baseline.rglob("*") if p.is_file() and p != report_path}
    if set(artifacts) != actual or any(not Path(name).is_relative_to(baseline) for name in artifacts):
        raise ValueError("baseline_artifact_inventory_mismatch")
    hashes = {str(report_path): file_digest(report_path)}
    _guard(artifacts, hashes)
    plan = _load(baseline / "run-plan.json", hashes)
    if (plan.get("version") != BASELINE_VERSION
            or plan.get("source_annotation_labels_consumed") is not False
            or plan.get("synthetic_SOURCE_records_created") is not False
            or plan.get("legacy_geometry_recomputed_or_enumerated") is not False
            or plan.get("harmonic_engine_recomputed") is not False):
        raise ValueError("unsafe_or_unsupported_baseline_plan")
    _guard(plan["inputs"], hashes)
    # New auditor files are additive. Only registered historical code hashes
    # are protected here; they need not equal the new current code inventory.
    _guard(plan["code"], hashes)
    integration = Path(plan["integration"]).resolve(strict=True)
    integrated = _load(integration / "report.json", hashes)
    contract = _load(integration / "run-contract.json", hashes)
    if (integrated.get("version") != "harmony-context-integration-trial-0.1.0"
            or integrated.get("complete") is not True
            or integrated.get("contract_sha256") != hashes[str(integration / "run-contract.json")]
            or contract.get("version") != integrated["version"]):
        raise ValueError("invalid_frozen_integration_parent")
    breadth = Path(contract["breadth_trial"]).resolve(strict=True)
    replay = Path(contract["source_replay_trial"]).resolve(strict=True)
    frozen_plan = _load(breadth / "frozen-plan.json", hashes)
    breadth_contract = _load(breadth / "run-contract.json", hashes)
    if (frozen_plan.get("version") != "harmony-breadth-trial-0.1.1"
            or breadth_contract["frozen_plan_sha256"] != hashes[str(breadth / "frozen-plan.json")]):
        raise ValueError("invalid_frozen_breadth_parent")
    packages = _unique(frozen_plan["packages"], lambda r: r["pair_id"], "duplicate_frozen_package")
    revisions = _unique(integrated["measure_revisions"], lambda r: r["pair_id"], "duplicate_revision")
    current = _unique(integrated["records"], lambda r: (r["pair_id"], r["plan_index"], r["sample_id"]),
                      "duplicate_integration_context")
    expected = {}
    for pair, package in packages.items():
        if package["source"]["pair_id"] != pair:
            raise ValueError("package_source_identity_mismatch")
        for row in package["plan"]["selected_samples"]:
            key = (pair, row["plan_index"], row["sample"]["sample_id"])
            if key in expected:
                raise ValueError("duplicate_frozen_context")
            expected[key] = row
    contexts = _unique(_load(baseline / "observation-index.json", hashes), _key, "duplicate_baseline_context")
    units = _unique(_load(baseline / "unit-index.json", hashes),
                    lambda r: (_key(r), tuple(r["lane"])), "duplicate_baseline_raw_lane")
    summary = report["summary"]
    if (not packages or set(packages) != set(revisions) or set(expected) != set(current)
            or set(contexts) != set(expected) or len(contexts) != summary["contexts"]
            or len(packages) != summary["packages"]
            or len(packages) != integrated["summary"]["packages"]
            or len(contexts) != integrated["summary"]["samples"]
            or len({p["source"]["manifest_entry"]["work_family_id"] for p in packages.values()}) != summary["work_families"]
            or len(units) != summary["raw_lane_units"]
            or plan["expected_context_keys"] != [list(key) for key in current]):
        raise ValueError("baseline_context_or_lane_denominator_mismatch")
    if (dict(Counter(r["status"] for r in units.values())) != summary["status_counts"]
            or any(summary.get(flag) != 0 for flag in
                   ("human_validated", "training_eligible", "gold_eligible", "generation_ready"))):
        raise ValueError("baseline_status_inventory_or_promotion_mismatch")
    old_stages = {}
    for row in contexts.values():
        for stage, status in row["original_stage_statuses"].items():
            old_stages.setdefault(stage, Counter())[status] += 1
    if (dict(Counter(r["original_final_status"] for r in contexts.values())) != summary["original_final_statuses_preserved"]
            or {k: dict(v) for k, v in old_stages.items()} != summary["original_stage_statuses_preserved"]
            or summary["original_final_statuses_preserved"] != integrated["summary"]["previous_statuses_retained"]
            or summary["original_stage_statuses_preserved"] != integrated["summary"]["stage_statuses_retained"]):
        raise ValueError("baseline_original_stage_inventory_mismatch")
    inventories = {str(path): _inventory(path, hashes) for path in (baseline, integration, breadth, replay)}
    return {"baseline": baseline, "hashes": hashes, "inventories": inventories, "report": report,
            "plan": plan, "packages": packages, "revisions": revisions,
            "current": current, "expected": expected, "contexts": contexts, "units": units,
            "unit_snapshots": {}}


def _working_case(data, pair):
    info, row = data["packages"][pair]["source"], data["revisions"][pair]
    parent = _load(info["frozen_ir_path"], data["hashes"])
    if data["hashes"][str(Path(info["frozen_ir_path"]).resolve())] != info["ir_sha256"]:
        raise ValueError("historical_parent_file_hash_mismatch")
    sidecar = _load(row["sidecar"], data["hashes"])
    if row["candidate_created"] is True and isinstance(row["candidate_ir"], str):
        ir = _load(row["candidate_ir"], data["hashes"])
    elif row["candidate_created"] is False and row["candidate_ir"] is None:
        ir = parent
    else:
        raise ValueError("invalid_explicit_revision_selection")
    if (row["parent_ir_document_id"] != parent["ir_document_id"]
            or row["working_ir_document_id"] != ir["ir_document_id"]
            or parent["source_files"] != ir["source_files"]):
        raise ValueError("working_revision_identity_mismatch")
    _revision(ir, parent, info, row, sidecar)
    return parent, ir, sidecar


def _observation(data, key, parent, ir, sidecar, *, literal=True):
    row = data["contexts"][key]
    if not Path(row["path"]).resolve().is_relative_to(data["baseline"] / "observations"):
        raise ValueError("foreign_baseline_observation_artifact")
    observation = _load(row["path"], data["hashes"])
    if (row["sha256"] != data["hashes"][str(Path(row["path"]).resolve())]
            or _ref(observation) != {k: row[k] for k in ("record_id", "record_sha256")}):
        raise ValueError("baseline_observation_index_binding_mismatch")
    current = data["current"][key]
    # The completed baseline already checked the eight explicit original
    # parents. Protect those frozen bytes, without decompressing large old
    # harmony-stage packets or replaying their producer. Fresh-check literal
    # IR projection once before output; subsequent reads retain byte+seal trust.
    validate_observation(observation, ir=ir if literal else None)
    package, revision = data["packages"][key[0]], data["revisions"][key[0]]
    origin, scope = observation["origin"], observation["scope"]
    expected_scope = {"score_id": ir["score"]["score_id"], "ir_document_id": ir["ir_document_id"],
                      "ir_content_sha256": digest(ir), "source_files": ir["source_files"],
                      "target_span": data["expected"][key]["sample"]["span"],
                      "context_span": data["expected"][key]["sample"]["span"]}
    content_parents = {"integration_index_row": current, "frozen_plan_row": data["expected"][key],
                       "package": package, "revision_row": revision,
                       "revision_sidecar": sidecar, "parent_ir": parent}
    refs = origin["artifact_references"]
    if (scope != expected_scope or (origin["pair_id"], origin["plan_index"], origin["sample"]["sample_id"]) != key
            or origin["sample"] != data["expected"][key]["sample"]
            or origin["lane_index"] != data["expected"][key]["lane_index"]
            or origin["historical_ir_document_id"] != parent["ir_document_id"]
            or origin["historical_ir_content_sha256"] != digest(parent)
            or origin["working_ir_selection"] != ("measure_core_candidate" if revision["candidate_created"] else "historical_parent")
            or any(origin["parent_content_sha256"][name] != digest(value) for name, value in content_parents.items())
            or refs["integration_artifact"] != current["artifact"]
            or refs["integration_file_sha256"] != current["sha256"]
            or refs["integration_file_sha256"] != data["hashes"][str(Path(current["artifact"]).resolve())]
            or refs["original_stored_file_sha256"] != data["hashes"].get(str(Path(refs["original_stored_artifact"]).resolve()))
            or refs["revision_sidecar"] != revision["sidecar"]
            or refs["historical_ir_file_sha256"] != package["source"]["ir_sha256"]):
        raise ValueError("frozen_observation_scope_or_origin_binding_mismatch")
    if (row["original_final_status"] != current["previous_status"]
            or origin["parent_statuses"] != {"original": current["previous_status"], "integration": current["status"],
                                            "measure_revision": revision["status"]}):
        raise ValueError("baseline_original_status_binding_mismatch")
    lanes = [(lane["part_id"], lane["voice_id"]) for lane in observation["raw_lanes"]]
    if (len(lanes) != len(set(lanes)) or len(lanes) != row["raw_lane_count"]
            or {(key, lane) for lane in lanes} != {identity for identity in data["units"] if identity[0] == key}):
        raise ValueError("baseline_context_or_lane_denominator_mismatch")
    for lane in lanes if literal else []:
        unit_row = data["units"][(key, lane)]
        if not Path(unit_row["artifact"]).resolve().is_relative_to(data["baseline"] / "units"):
            raise ValueError("foreign_baseline_unit_artifact")
        unit = _load(unit_row["artifact"], data["hashes"], compressed=True)
        if (unit_row["sha256"] != data["hashes"][str(Path(unit_row["artifact"]).resolve())]
                or unit["version"] != BASELINE_VERSION or unit["context_key"] != list(key)
                or unit["lane"] != list(lane) or unit["observation_ref"] != _ref(observation)
                or unit_row["observation_ref"] != _ref(observation)
                or unit_row["status"] != unit["unit"]["status"]
                or unit_row["reasons"] != unit["unit"]["reasons"]
                or unit["original_final_status"] != row["original_final_status"]
                or unit["original_stage_statuses"] != row["original_stage_statuses"]
                or unit["parent_context_artifact"] != current
                or unit.get("selected") is not None
                or any(unit.get(flag) is not False for flag in
                       ("harmonic_or_role_claim", "training_eligible", "generation_ready"))):
            raise ValueError("baseline_unit_index_or_packet_binding_mismatch")
        positive, points = _owned_sound_refs(observation, lane)
        geometry = unit["unit"]
        graph = geometry["graph"]
        if graph is not None and ({s["sounding_event_id"] for s in graph["events"]} != set(positive)
                                  or set(graph["sampled_lane_point_sound_refs"]) != set(points)):
            raise ValueError("baseline_graph_selected_lane_sound_ownership_mismatch")
        data["unit_snapshots"][(key, lane)] = {
            "baseline_unit_content_sha256": digest(unit), "geometry_result_content_sha256": digest(geometry),
            "geometry_status": geometry["status"], "geometry_reasons": deepcopy(geometry["reasons"]),
            "probe_status_inventory": dict(Counter(p["answer"]["status"] for p in geometry["constraint_probes"])),
            "original_final_status": unit["original_final_status"],
            "original_stage_statuses": deepcopy(unit["original_stage_statuses"])}
    return observation


def _owned_sound_refs(observation, lane):
    """Literal source-note ownership and half-open timing, not a voice choice."""
    start, end = span_bounds(observation["scope"]["context_span"])
    notes = {slot["core_event"]["note_id"]: slot["core_event"] for slot in observation["slots"]
             if slot["event_kind"] == "note"}
    positive, points = [], []
    for sound in observation["core_projection"]["sounding_events"]:
        if not sound["source_note_ids"] or any(nid not in notes for nid in sound["source_note_ids"]):
            raise ValueError("missing_projected_source_note_ownership")
        owners = {(notes[nid]["part_id"], notes[nid]["voice_id"]) for nid in sound["source_note_ids"]}
        if owners != {tuple(lane)}:
            continue
        left, right = f(sound["span"]["start"]), f(sound["span"]["end"])
        if left < right and left < end and right > start:
            positive.append(sound["sounding_event_id"])
        elif left == right and start <= left < end:
            points.append(sound["sounding_event_id"])
    return positive, points


def _gate(data, key, observation, lane, audit, audit_path, audit_sha):
    row = data["units"][(key, tuple(lane))]
    snapshot = data["unit_snapshots"][(key, tuple(lane))]
    positive, points = _owned_sound_refs(observation, lane)
    failed_rows = {} if audit is None else {
        item["sounding_event_ref"]: item for item in audit["sounding_audits"]
        if item["source_clock_consistency_passed"] is not True}
    failed = set(failed_rows)
    affected = [sid for sid in [*positive, *points] if sid in failed]
    if audit is None:
        status = "withheld_diagnostic_failure"
    elif affected and all(failed_rows[sid].get("timing_status") == "grace_point_performed_timing_unknown"
                          and set(failed_rows[sid].get("diagnostics", [])) <= {"grace_performed_timing_not_assessed"}
                          for sid in affected):
        status = "withheld_point_timing_not_assessed"
    elif affected:
        status = "withheld_source_clock_conflict"
    elif not positive:
        status = "not_applicable_no_positive_sounds"
    else:
        status = "source_clock_consistent_not_semantic_approval"
    return {"context_key": list(key), "observation_ref": _ref(observation), "lane": list(lane),
            "baseline_unit_artifact": row["artifact"], "baseline_unit_file_sha256": row["sha256"],
            **deepcopy(snapshot),
            "audit_ref": None if audit is None else _ref(audit), "audit_artifact": str(audit_path),
            "audit_file_sha256": audit_sha, "context_full_lineage_source_clock_passed":
                False if audit is None else audit["source_clock_consistency_passed"],
            "selected_lane_positive_sound_refs": positive, "selected_lane_point_sound_refs": points,
            "affected_selected_lane_sound_refs": affected, "gate_status": status,
            "geometry_result_preserved": True, "geometry_recomputed": False,
            "selected": None, "semantic_eligible": False, "training_eligible": False,
            "gold_eligible": False, "generation_ready": False}


def run(baseline, output):
    started = perf_counter()
    baseline, output = Path(baseline).resolve(strict=True), Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output" or output.is_relative_to(baseline):
        raise ValueError("output_must_be_new_workspace_output_directory")
    data = _inputs(baseline)
    # Validate every exact binding before allocating output; never resample.
    for pair in data["packages"]:
        parent, ir, sidecar = _working_case(data, pair)
        for key in data["contexts"]:
            if key[0] == pair:
                _observation(data, key, parent, ir, sidecar)
    inputs = deepcopy(data["hashes"])
    code = {str(p.resolve()): file_digest(p) for p in _code_paths()}
    plan = {"version": VERSION, "baseline": str(baseline), "inputs": inputs, "code": code,
            "expected_context_keys": [list(key) for key in data["contexts"]],
            "expected_raw_lane_units": len(data["units"]),
            "selection": "all frozen observations and every frozen raw lane; no passing-only subset",
            "audit_selection": "every core_projection sounding event, including linked context-only sounds",
            "context_gate": "full chain consistency, even when conflict lies outside active context",
            "unit_gate": "only affected selected-lane active sound references; no semantic approval",
            "producer_code_policy": "registered old hashes protected; additive current auditor inventory frozen separately",
            "old_engines_or_selector_recomputed": False, "source_xml_inspected": False,
            "source_labels_used_for_inference": False, "geometry_recomputed": False}
    output.mkdir(parents=True)
    (output / "audits").mkdir()
    write_new(output / "run-plan.json", plan)
    artifacts = {str((output / "run-plan.json").resolve()): file_digest(output / "run-plan.json")}
    records, gates, context_statuses, gate_statuses, diagnostics = [], [], Counter(), Counter(), Counter()
    failures = 0
    for pair in data["packages"]:
        parent, ir, sidecar = _working_case(data, pair)
        ir_before = digest(ir)
        for key, row in data["contexts"].items():
            if key[0] != pair:
                continue
            observation = _observation(data, key, parent, ir, sidecar, literal=False)
            before = digest(observation)
            sound_ids = [s["sounding_event_id"] for s in observation["core_projection"]["sounding_events"]]
            sound_ids_before = list(sound_ids)
            path = output / "audits" / (observation["record_id"] + ".json")
            audit, error = None, None
            try:
                audit = audit_sounding_lineage(ir, sound_ids=sound_ids, context_span=observation["scope"]["context_span"])
                validate_audit(audit, ir=ir, sound_ids=sound_ids, context_span=observation["scope"]["context_span"])
            except Exception as exc:
                audit = None
                error = f"{type(exc).__name__}:{exc}"
                failures += 1
            if digest(observation) != before or digest(ir) != ir_before or sound_ids != sound_ids_before:
                raise ValueError("diagnostic_inputs_mutated")
            packet = {"version": VERSION, "context_key": list(key), "observation_ref": _ref(observation),
                      "baseline_observation_artifact": row["path"], "baseline_observation_file_sha256": row["sha256"],
                      "status": "integrity_or_computation_abstention" if audit is None else "diagnostic_complete",
                      "error": error, "audit": audit, "selected": None,
                      "semantic_eligible": False, "training_eligible": False, "generation_ready": False}
            write_new(path, packet)
            artifact_sha = file_digest(path)
            artifacts[str(path.resolve())] = artifact_sha
            passed = audit is not None and audit["source_clock_consistency_passed"] is True
            context_status = ("diagnostic_failure" if audit is None else
                              "source_clock_consistent" if passed else "source_clock_not_consistent_or_not_assessed")
            context_statuses[context_status] += 1
            if audit is not None:
                diagnostics.update(audit["summary"]["diagnostic_counts"])
            records.append({"context_key": list(key), "observation_ref": _ref(observation),
                            "audit_ref": None if audit is None else _ref(audit),
                            "source_clock_consistency_passed": passed, "status": context_status,
                            "error": error, "artifact": str(path), "sha256": artifact_sha})
            for raw_lane in observation["raw_lanes"]:
                lane = [raw_lane["part_id"], raw_lane["voice_id"]]
                gate = _gate(data, key, observation, lane, audit, path, artifact_sha)
                gates.append(gate)
                gate_statuses[gate["gate_status"]] += 1
            print(f"[{len(records)}/{len(data['contexts'])}] lineage context; raw-lane gates={len(gates)}", flush=True)
    if ({(_key(row), tuple(row["lane"])) for row in gates} != set(data["units"])
            or len(gates) != len(data["units"]) or len(records) != len(data["contexts"])):
        raise ValueError("lineage_context_or_lane_denominator_loss")
    for name, value in (("audit-index.json", records), ("gate-index.json", gates)):
        path = output / name
        write_new(path, value)
        artifacts[str(path.resolve())] = file_digest(path)
    changed = [name for name, sha in {**inputs, **code}.items()
               if not Path(name).is_file() or file_digest(name) != sha]
    if {str(p.resolve()) for p in _code_paths()} != set(code):
        changed.append("source_or_schema_inventory_changed")
    for directory, inventory in data["inventories"].items():
        if {str(p.resolve()) for p in Path(directory).rglob("*") if p.is_file()} != inventory:
            changed.append("parent_artifact_inventory_changed:" + directory)
    if inputs != data["hashes"]:
        changed.append("input_inventory_changed_while_computing")
    changed_artifacts = [name for name, sha in artifacts.items()
                         if not Path(name).is_file() or file_digest(name) != sha]
    if {str(p.resolve()) for p in output.rglob("*") if p.is_file()} != set(artifacts):
        changed_artifacts.append("output_artifact_inventory_changed")
    report = {"version": VERSION, "complete": not changed and not changed_artifacts and failures == 0,
              "inputs_and_code_unchanged": not changed, "artifacts_unchanged": not changed_artifacts,
              "computation_integrity_passed": failures == 0,
              "source_clock_consistency_passed": all(r["source_clock_consistency_passed"] for r in records),
              "summary": {"packages": len(data["packages"]), "contexts": len(records), "raw_lane_units": len(gates),
                          "context_status_counts": dict(context_statuses), "gate_status_counts": dict(gate_statuses),
                          "diagnostic_counts": dict(diagnostics), "diagnostic_failures": failures,
                          "original_geometry_status_counts_preserved": deepcopy(data["report"]["summary"]["status_counts"]),
                          "human_validated": 0, "training_eligible": 0, "gold_eligible": 0, "generation_ready": 0},
              "artifact_hashes": artifacts, "changed_inputs_or_code": changed, "changed_artifacts": changed_artifacts,
              "elapsed_seconds": perf_counter() - started,
              "source_labels_used_for_inference": False, "source_xml_inspected": False,
              "source_xml_certified": False, "voice_identity_certified": False, "performed_timing_certified": False,
              "concert_pitch_certified": False, "geometry_recomputed": False,
              "old_engines_or_selector_recomputed": False, "old_harmony_or_nct_inventory_modified": False,
              "semantic_eligible": False, "generation_ready": False, "external_transmission": False,
              "limits": ["Complete means diagnostic execution and preservation, not universal source-clock consistency.",
                         "Full-chain failure can lie outside the active context; unit gates use only active selected-lane refs.",
                         "Stored notated IR is compared with derived sound clocks, not XML or importer causes.",
                         "A consistent clock is not harmonic/NCT/role/training/gold approval."]}
    write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--output", required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
