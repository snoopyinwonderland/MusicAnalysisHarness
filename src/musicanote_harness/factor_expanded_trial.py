"""Append-only fresh-scope hypotheses over saved context prerequisites.

Historical score/annotation/source gates and every old context/group/lane stay
in scope. New graphs and hypotheses have their own explicit envelope. Neither
an expanded observation nor a geometric witness is musical gold or a winner.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from . import factor_context_prerequisite_trial as previous
from . import factor_musical_trial as storage
from . import factor_musical_view as common
from . import harmony_frozen_context_lineage_trial as parent
from .musical_pattern_observation import digest

ROOT = parent.ROOT
VERSION = "factor-expanded-trial-0.1.0"


def _limit(value, name, *, positive=False):
    if type(value) is not int or value < (1 if positive else 0):
        raise ValueError("explicit_integer_trial_limit_required:" + name)


def load_inputs(directory):
    """Saved report/hash trust is storage integrity, never a source gold label."""
    directory = Path(directory).resolve(strict=True)
    report_path = directory / "report.json"
    report = parent.read(report_path)
    if (report.get("version") != previous.VERSION
            or any(report.get(k) is not True for k in (
                "scope_calculation_complete", "computation_integrity_passed",
                "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged"))
            or report.get("cohort_complete") is not False or report.get("selected") is not None
            or report.get("failures") != [] or report.get("changed_inputs_or_code") != []
            or report.get("changed_artifacts") != []
            or any(report.get(k) is not False for k in (
                "harmony_confirmed", "cadence_confirmed", "musical_accuracy_measured",
                "training_eligible", "gold_eligible", "generation_ready",
                "source_labels_used_for_inference", "core_or_production_modified",
                "old_paths_or_bundles_extended"))):
        raise ValueError("completed_unselected_context_prerequisites_required")
    hashes = {}
    parent._guard({str(report_path): parent.file_digest(report_path)}, hashes)
    if any(not Path(p).is_relative_to(directory) for p in report["artifact_hashes"]):
        raise ValueError("parent_artifact_outside_prerequisite_directory")
    parent._guard(report["artifact_hashes"], hashes)
    inventory = parent._inventory(directory, hashes)
    plan = parent._load(directory / "run-plan.json", hashes)
    if (plan.get("version") != previous.VERSION or plan.get("cohort_complete") is not False
            or any(plan.get(k) is not False for k in (
                "old_selector_or_comparison_reexecuted", "old_paths_or_bundles_extended",
                "source_labels_used_for_inference", "production_modified"))):
        raise ValueError("parent_prerequisite_plan_policy_mismatch")
    parent._guard(plan["inputs"], hashes)
    parent._guard(plan["code"], hashes)
    family = previous.load_batch(plan["parent_directory"])
    if (plan["parent_report_sha256"] != parent.file_digest(family["directory"] / "batch-report.json")
            or any(plan[name] != family["plan"][name] for name in ("declared_contexts", "declared_units"))
            or plan["selected_contexts"] != family["plan"]["selection"]["selected_contexts"]):
        raise ValueError("parent_family_or_declared_denominator_mismatch")
    rows = parent._load(directory / "context-index.json", hashes)
    if ([r["context_key"] for r in rows] != plan["selected_contexts"]
            or len({tuple(r["context_key"]) for r in rows}) != len(rows)
            or report["summary"]["contexts"] != len(rows)
            or report["summary"]["raw_lanes"] != sum(len(r["lane_inventory"]) for r in rows)
            or report["summary"]["groups"] != sum(len(r["groups"]) for r in rows)
            or report["summary"]["declared_contexts"] != len(plan["declared_contexts"])
            or report["summary"]["declared_raw_lanes"] != len(plan["declared_units"])):
        raise ValueError("parent_prerequisite_index_denominator_mismatch")
    if (Counter(report["summary"]["old_calculation_counts"]) != Counter(family["report"]["summary"]["counts"])
            or Counter(report["summary"]["old_group_status_counts"]) != Counter(
                g["old_status"] for r in rows for g in r["groups"])
            or report["summary"]["unexecuted_contexts"] != len(plan["declared_contexts"]) - len(rows)
            or report["summary"]["unexecuted_raw_lanes"] != len(plan["declared_units"]) - sum(
                len(r["lane_inventory"]) for r in rows)):
        raise ValueError("parent_prerequisite_saved_counts_or_unexecuted_denominator_mismatch")
    return {"directory": directory, "report": report, "plan": plan, "rows": rows,
            "hashes": hashes, "inventory": inventory, "family": family}


def load_case(data, row):
    key = tuple(row["context_key"])
    family_row = next(r for r in data["family"]["indices"] if tuple(r["context_key"]) == key)
    packet, ir = previous._case(data["family"], family_row)
    if (row["parent_artifact"] != family_row["artifact"]
            or row["parent_artifact_sha256"] != family_row["sha256"]
            or row["working_ir"] != packet["score_snapshots"]["working-ir"]
            or row["view_ref"] != common.ref(packet["context"]["view"])
            or row["lane_inventory"] != packet["lane_inventory"]
            or [(g["group_id"], g["old_status"], g["original_status"], g["planned_paths"],
                 g["old_overlay_count"], g["old_comparison_count"])
                for g in row["groups"]] != [(g["group_id"], g["status"], g["original_status"],
                    g["planned_paths"], len(g["overlays"]), len(g["comparisons"]))
                    for g in packet["groups"]]):
        raise ValueError("parent_context_group_lane_or_score_binding_mismatch")
    for stored, old in zip(row["groups"], packet["groups"]):
        if stored["errors"] or len(stored["records"]) != len(old["comparisons"]):
            raise ValueError("parent_prerequisite_records_or_errors_mismatch")
        for record, compared in zip(stored["records"], old["comparisons"]):
            artifact = Path(record["artifact"]).resolve(strict=True)
            if (artifact.parent != data["directory"] / "cadence"
                    or data["hashes"].get(str(artifact)) != record["sha256"]
                    or record["comparison_ref"] != common.ref(compared)
                    or record["completion_bundle_ref"] != compared["completion_bundle_ref"]
                    or record["planned_records"] != len(old["overlays"])):
                raise ValueError("registered_closed_parent_prerequisite_record_required")
            saved = parent._load(artifact, data["hashes"], compressed=True)
            from .factor_cadence_prerequisites import BATCH_PREFIX, FLAGS
            common.check(saved, BATCH_PREFIX)
            if (common.ref(saved) != record["record_ref"] or saved["status"] != record["status"]
                    or saved["planned_records"] != record["planned_records"]
                    or len(saved["records"]) != record["saved_records"] or saved["flags"] != FLAGS
                    or saved["view_ref"] != common.ref(packet["context"]["view"])
                    or saved["completion_bundle_ref"] != compared["completion_bundle_ref"]
                    or saved["path_refs"] != compared["path_refs"]
                    or saved["overlay_refs"] != compared["overlay_refs"]):
                raise ValueError("parent_prerequisite_content_identity_mismatch")
    info = row["context_observation"]
    path = Path(info["artifact"]).resolve(strict=True)
    if (path.parent != data["directory"] / "contexts" or data["hashes"].get(str(path)) != info["sha256"]
            or info["error"] is not None):
        raise ValueError("registered_parent_context_observation_required")
    extension = parent._load(path, data["hashes"], compressed=True)
    if (common.ref(extension) != info["record_ref"] or extension["status"] != info["status"]
            or path.name != extension["record_id"] + ".json.gz"):
        raise ValueError("parent_extension_identity_or_status_mismatch")
    return packet, ir, extension


def run(prerequisites, output, *, max_events=4096, max_factors=4096, max_edges=65536,
        max_catalogs=128, path_budget=128, pair_budget=4096,
        overlay_pair_budget=65536, max_motion_pairs=65536):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("trial_output_must_be_new_direct_workspace_child")
    settings = dict(max_events=max_events, max_factors=max_factors, max_edges=max_edges,
        max_catalogs=max_catalogs, path_budget=path_budget, pair_budget=pair_budget,
        overlay_pair_budget=overlay_pair_budget, max_motion_pairs=max_motion_pairs)
    for name, value in settings.items():
        _limit(value, name, positive=name == "path_budget")
    # Imports remain lazy: guards precede every new calculation and filesystem write.
    from . import factor_expanded_scope as expanded
    from . import factor_expanded_hypotheses as hypotheses
    data = load_inputs(prerequisites)
    inputs = {**data["hashes"], **data["family"]["hashes"]}
    code = {str(p.resolve()): parent.file_digest(p) for p in parent._code_paths()}
    plan = {"version": VERSION, "prerequisites": str(data["directory"]),
        "parent_report_sha256": parent.file_digest(data["directory"] / "report.json"),
        "inputs": deepcopy(inputs), "code": code, "settings": settings,
        "declared_contexts": deepcopy(data["plan"]["declared_contexts"]),
        "declared_units": deepcopy(data["plan"]["declared_units"]),
        "selected_contexts": deepcopy(data["plan"]["selected_contexts"]),
        "selection": deepcopy(data["plan"]["selection"]), "cohort_complete": False,
        "scope": "fresh_explicit_envelope_for_every_previously_selected_context",
        "old_selector_or_analysis_reexecuted": False, "old_paths_or_bundles_extended": False,
        "source_labels_used_for_inference": False, "production_modified": False}
    output.mkdir()
    artifacts, indices, failures = {}, [], []
    totals = Counter()
    storage._save(output, "run-plan.json", plan, artifacts)
    for row in data["rows"]:
        case_started = perf_counter()
        packet, ir, extension = load_case(data, row)
        before = digest([packet, ir, extension])
        index = {"context_key": deepcopy(row["context_key"]), "old_view_ref": deepcopy(row["view_ref"]),
            "parent_extension_ref": common.ref(extension), "old_context_row_sha256": digest(row),
            "old_context_span": deepcopy(packet["context"]["view"]["context_span"]),
            "old_groups": deepcopy(row["groups"]), "old_lane_refs": [
                {"lane": deepcopy(r["lane"]), "old_status": r["old_geometry_status"],
                 "old_graph_ref": None if r["graph_snapshot"] is None else common.ref(r["graph_snapshot"])}
                for r in row["lane_inventory"]],
            "expanded_scope": None, "hypotheses": None, "assessment": None,
            "status": "withheld_parent_context_observation", "error": None}
        print(f"[{len(indices)+1}/{len(data['rows'])}] fresh scope {row['context_key'][0]}", flush=True)
        if extension["status"] == "ready_literal_context_not_analysis":
            try:
                def save_stage(name, value):
                    path = storage._save(output, name + "/" + value["record_id"] + ".json.gz",
                                         value, artifacts, compressed=True)
                    index[name] = {"artifact": str(path), "sha256": artifacts[str(path)],
                                   "record_ref": common.ref(value), "status": value["status"]}
                scope = expanded.prepare_scope(ir, packet["context"]["view"], packet["observation"],
                    packet["audit_packet"]["audit"], extension,
                    max_events=max_events, max_factors=max_factors, max_edges=max_edges)
                save_stage("expanded_scope", scope)
                index["analysis_span"] = deepcopy(scope["analysis_span"])
                index["lane_inventory"] = deepcopy(scope["lane_inventory"])
                totals["expanded_raw_lanes"] += len(scope["raw_lanes"])
                totals["expanded_sounds"] += len(scope["sound_facts"])
                proposed = hypotheses.build_hypotheses(ir, scope, max_catalogs=max_catalogs, path_budget=path_budget)
                save_stage("hypotheses", proposed)
                totals["planned_catalog_spans"] += len(proposed["catalog_inventory"])
                totals["materialized_catalogs"] += sum(
                    entry["supplier_catalog"] is not None for entry in proposed["catalog_inventory"])
                totals["new_groups"] += len(proposed["path_groups"])
                totals["planned_paths"] += sum(g["planned_paths"] for g in proposed["path_groups"]
                                               if g["planned_paths"] is not None)
                totals["unknown_path_group_counts"] += sum(g["planned_paths"] is None for g in proposed["path_groups"])
                totals["materialized_paths"] += sum(len(g["paths"]) for g in proposed["path_groups"])
                assessed = hypotheses.evaluate_hypotheses(ir, scope, proposed,
                    pair_budget=pair_budget, overlay_pair_budget=overlay_pair_budget, max_motion_pairs=max_motion_pairs)
                save_stage("assessment", assessed)
                index["hypothesis_counts"] = deepcopy(proposed["summary"])
                index["assessment_counts"] = deepcopy(assessed["summary"])
                index["assessment_group_plans"] = [
                    {name: deepcopy(group[name]) for name in (
                        "group_id", "status", "total_path_key_pairs", "total_function_shapes",
                        "planned_same_bundle_assessments")}
                    for group in assessed["groups"]]
                index["status"] = "scope_calculation_complete_not_selected"
            except Exception as exc:
                index["status"] = "calculation_failure"
                index["error"] = f"{type(exc).__name__}:{exc}"
                failures.append({"context_key": deepcopy(row["context_key"]), "error": index["error"]})
        if digest([packet, ir, extension]) != before:
            raise ValueError("expanded_trial_parent_or_IR_mutated")
        totals["contexts"] += 1
        totals["old_raw_lanes"] += len(row["lane_inventory"])
        totals["old_groups"] += len(row["groups"])
        index["elapsed_seconds"] = perf_counter() - case_started
        indices.append(index)
        print(f"[{len(indices)}/{len(data['rows'])}] {index['status']}, {index['elapsed_seconds']:.3f}s", flush=True)
    storage._save(output, "context-index.json", indices, artifacts)
    changed = [p for p, sha in {**inputs, **code}.items()
               if not Path(p).is_file() or parent.file_digest(p) != sha]
    if {str(p.resolve()) for p in parent._code_paths()} != set(code):
        changed.append("current_code_inventory_changed")
    for prefix, directory, inventory in (("prerequisite", data["directory"], data["inventory"]),
            ("family", data["family"]["directory"], data["family"]["inventory"])):
        if {str(p.resolve()) for p in directory.rglob("*") if p.is_file()} != inventory:
            changed.append(prefix + "_parent_inventory_changed")
    changed_artifacts = [p for p, sha in artifacts.items()
                         if not Path(p).is_file() or parent.file_digest(p) != sha]
    if {str(p.resolve()) for p in output.rglob("*") if p.is_file()} != set(artifacts):
        changed_artifacts.append("generated_artifact_inventory_changed")
    denominator = ([r["context_key"] for r in indices] == plan["selected_contexts"]
                   and totals["old_raw_lanes"] == data["report"]["summary"]["raw_lanes"]
                   and totals["old_groups"] == data["report"]["summary"]["groups"])
    integrity = not changed and not changed_artifacts and not failures
    report = {"version": VERSION, "scope_calculation_complete": bool(integrity and denominator),
        "cohort_complete": False, "computation_integrity_passed": bool(integrity),
        "selected_denominators_complete": bool(denominator), "inputs_and_code_unchanged": not changed,
        "artifacts_unchanged": not changed_artifacts, "changed_inputs_or_code": changed,
        "changed_artifacts": changed_artifacts, "failures": failures, "artifact_hashes": deepcopy(artifacts),
        "summary": {**dict(totals), "declared_contexts": len(plan["declared_contexts"]),
            "declared_original_raw_lanes": len(plan["declared_units"]),
            "unexecuted_original_contexts": len(plan["declared_contexts"]) - totals["contexts"],
            "unexecuted_original_raw_lanes": len(plan["declared_units"]) - totals["old_raw_lanes"],
            "context_status_counts": dict(Counter(r["status"] for r in indices)),
            "old_group_status_counts": dict(Counter(g["old_status"] for r in indices for g in r["old_groups"]))},
        "elapsed_seconds": perf_counter() - started, "selected": None,
        "harmony_confirmed": False, "cadence_confirmed": False, "musical_accuracy_measured": False,
        "training_eligible": False, "gold_eligible": False, "generation_ready": False,
        "source_labels_used_for_inference": False, "core_or_production_modified": False,
        "old_paths_or_bundles_extended": False,
        "limits": ["Fresh envelope hypotheses are not extensions of old paths or completions.",
                   "Historical source/annotation/split/use policies are unchanged.",
                   "Stored shape/geometry alternatives do not establish a winner or a cadence.",
                   "Whole-group budgets preserve planned denominators, not byte/RSS bounds.",
                   "Completion covers the declared executed subset, not the full cohort."]}
    parent.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prerequisites", "output"):
        parser.add_argument("--" + name, required=True)
    for name, default in (("max-events", 4096), ("max-factors", 4096), ("max-edges", 65536),
            ("max-catalogs", 128), ("path-budget", 128), ("pair-budget", 4096),
            ("overlay-pair-budget", 65536), ("max-motion-pairs", 65536)):
        parser.add_argument("--" + name, type=int, default=default)
    report = run(**vars(parser.parse_args()))
    print(report["summary"])
    return 0 if report["scope_calculation_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
