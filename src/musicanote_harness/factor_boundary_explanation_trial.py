"""Append-only conditional suspension/anticipation role experiment.

Only touching slots from the authentic indexed group are compared. These are
conditional role explanations, not selected NCT, harmony, key or cadence labels.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from . import factor_temporal_explanation_trial as previous
from . import factor_temporal_explanations as temporal
from . import factor_indexed_hypotheses as indexed
from . import factor_expanded_hypotheses as frozen
from . import factor_musical_trial as storage
from . import harmony_frozen_context_lineage_trial as parent
from .musical_pattern_observation import digest

ROOT = parent.ROOT
VERSION = "factor-boundary-explanation-trial-0.1.0"
POLICY_FALSE = previous.POLICY_FALSE
DENOMINATORS = previous.DENOMINATORS
SETTINGS = {"max_geometry_candidates": 4096, "max_chain_edges": 16,
    "max_membership_relations": 65536, "max_new_bundles": 4096, "query_work_budget": 100000}
INHERITED_ROW_FIELDS = (*previous.INHERITED_ROW_FIELDS, "grounding", "grounding_counts")
TEMPORAL_COVERAGE = "all_exact_single_segment_descriptors_with_separate_authentic_local_chain_bundles_not_music_ranking"


def _limit(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("explicit_nonnegative_integer_trial_limit_required:" + name)


def _ancestors(data):
    return [("temporal", data), *previous._ancestors(data["grounding"])]


def _registered(data, row):
    info = row.get("temporal_explanations")
    indexed._closed(info, {"artifact", "sha256", "record_ref", "status"}, "registered_temporal_stage")
    path = Path(info["artifact"]).resolve(strict=True)
    if path.parent != data["directory"] / "temporal-explanations" or data["hashes"].get(str(path)) != info["sha256"]:
        raise ValueError("foreign_or_unregistered_temporal_stage")
    value = parent._load(path, data["hashes"], compressed=True)
    frozen._check(value, temporal.PREFIX)
    if (not indexed._same(frozen._ref(value), info["record_ref"])
            or value["status"] != info["status"] or path.name != value["record_id"] + ".json.gz"):
        raise ValueError("temporal_stage_identity_or_status_mismatch")
    return value


def load_inputs(directory):
    """Authenticate the complete temporal parent before creating an output."""
    directory = Path(directory).resolve(strict=True)
    report_path = directory / "report.json"
    report = parent.read(report_path)
    indexed._closed(report, {"version", "scope_calculation_complete", "computation_integrity_passed",
        "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged",
        "changed_inputs_or_code", "changed_artifacts", "failures", "artifact_hashes", "parent_summary",
        "summary", "cohort_complete", "all_logical_paths_evaluated", "selected", *POLICY_FALSE,
        "conditional_local_contour_stage_enabled", "boundary_NCT_evaluated", "delayed_resolution_evaluated",
        "elapsed_seconds", "limits"}, "saved_temporal_explanation_report")
    if (report.get("version") != previous.VERSION
            or any(report.get(k) is not True for k in ("scope_calculation_complete", "computation_integrity_passed",
                "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged",
                "conditional_local_contour_stage_enabled"))
            or report.get("selected") is not None
            or any(report.get(k) is not False for k in (*POLICY_FALSE, "cohort_complete",
                "all_logical_paths_evaluated", "boundary_NCT_evaluated", "delayed_resolution_evaluated"))
            or any(report.get(k) != [] for k in ("failures", "changed_inputs_or_code", "changed_artifacts"))):
        raise ValueError("completed_unselected_temporal_parent_required")
    indexed._closed(report["summary"], {*DENOMINATORS, "temporal_integer_subtotals",
        "temporal_unknown_metric_contexts", "temporal_saved_contexts", "temporal_failed_contexts",
        "declared_contexts", "declared_original_raw_lanes", "unexecuted_original_contexts",
        "unexecuted_original_raw_lanes", "context_status_counts"}, "saved_temporal_summary")
    hashes = {}
    parent._guard({str(report_path): parent.file_digest(report_path)}, hashes)
    if type(report["artifact_hashes"]) is not dict or any(
            not Path(p).resolve().is_relative_to(directory) for p in report["artifact_hashes"]):
        raise ValueError("temporal_parent_artifact_outside_registered_directory")
    parent._guard(report["artifact_hashes"], hashes)
    inventory = parent._inventory(directory, hashes)
    plan = parent._load(directory / "run-plan.json", hashes)
    indexed._closed(plan, {"version", "grounding", "parent_report_sha256", "inputs", "code", "settings",
        "declared_contexts", "declared_units", "selected_contexts", "selection", "cohort_complete",
        "old_selector_or_analysis_reexecuted", "all_logical_paths_evaluated", "source_labels_used_for_inference",
        "old_paths_or_bundles_extended", "production_modified", "conditional_local_contour_stage_enabled",
        "boundary_NCT_evaluated", "delayed_resolution_evaluated", "coverage"}, "saved_temporal_plan")
    if (plan.get("version") != previous.VERSION or plan.get("coverage") != TEMPORAL_COVERAGE
            or plan.get("conditional_local_contour_stage_enabled") is not True
            or any(plan.get(k) is not False for k in ("cohort_complete", "old_selector_or_analysis_reexecuted",
                "all_logical_paths_evaluated", "source_labels_used_for_inference", "old_paths_or_bundles_extended",
                "production_modified", "boundary_NCT_evaluated", "delayed_resolution_evaluated"))):
        raise ValueError("temporal_parent_plan_policy_mismatch")
    indexed._closed(plan["settings"], set(previous.SETTINGS), "saved_temporal_settings")
    for name, value in plan["settings"].items():
        _limit(value, name)
    if type(plan["inputs"]) is not dict or type(plan["code"]) is not dict:
        raise ValueError("temporal_parent_declared_hash_maps_required")
    parent._guard(plan["inputs"], hashes)
    parent._guard(plan["code"], hashes)
    old = previous.load_inputs(plan["grounding"])
    expected_inputs = {p: value for _, ancestor in previous._ancestors(old) for p, value in ancestor["hashes"].items()}
    if not indexed._same(plan["inputs"], expected_inputs):
        raise ValueError("temporal_parent_exact_protected_input_closure_mismatch")
    if (plan["parent_report_sha256"] != parent.file_digest(old["directory"] / "report.json")
            or not indexed._same(report["parent_summary"], old["report"]["summary"])
            or any(not indexed._same(plan[k], old["plan"][k]) for k in
                ("declared_contexts", "declared_units", "selected_contexts", "selection"))):
        raise ValueError("temporal_parent_declared_lineage_or_summary_mismatch")
    rows = parent._load(directory / "context-index.json", hashes)
    if (type(rows) is not list or not indexed._same([r["context_key"] for r in rows], plan["selected_contexts"])
            or len({tuple(r["context_key"]) for r in rows}) != len(rows)
            or len(rows) != report["summary"]["contexts"]):
        raise ValueError("temporal_parent_context_denominator_mismatch")
    artifacts = {str(directory / name) for name in ("run-plan.json", "context-index.json")}
    artifacts.update(str(Path(row["temporal_explanations"]["artifact"]).resolve(strict=True)) for row in rows)
    if set(report["artifact_hashes"]) != artifacts:
        raise ValueError("temporal_parent_exact_artifact_inventory_mismatch")
    data = {"directory": directory, "report": report, "plan": plan, "rows": rows, "hashes": hashes,
        "inventory": inventory, "grounding": old, "cases": {}, "boundary_sessions": {}}
    totals, subtotals, unknown = Counter(), Counter(), Counter()
    from . import factor_boundary_explanations as engine
    for position, (row, original) in enumerate(zip(rows, old["rows"]), 1):
        indexed._closed(row, {"context_key", "old_row_sha256", *INHERITED_ROW_FIELDS, "temporal_explanations",
            "temporal_counts", "status", "error", "elapsed_seconds"}, "saved_temporal_context_row")
        print(f"[parent {position}/{len(rows)}] protected temporal source replay {row['context_key'][0]}", flush=True)
        if (row["status"] != "temporal_and_local_contour_explanations_saved_not_selected" or row["error"] is not None
                or row["old_row_sha256"] != digest(original)
                or any(not indexed._same(row[k], original[k]) for k in INHERITED_ROW_FIELDS)):
            raise ValueError("temporal_parent_original_context_or_origins_mismatch")
        case = previous.load_case(old, original)
        value = _registered(data, row)
        if (not indexed._same(value["resource_limits"], plan["settings"])
                or not indexed._same(row["temporal_counts"], value["summary"])):
            raise ValueError("temporal_parent_saved_limit_or_counts_mismatch")
        session = engine.prepare_inputs_prepared(old["grounded_sessions"][tuple(row["context_key"])], value)
        data["cases"][tuple(row["context_key"])] = (*case, value)
        data["boundary_sessions"][tuple(row["context_key"])] = session
        previous._add_denominators(totals, row)
        for name, count in value["summary"].items():
            if type(count) is int:
                subtotals[name] += count
            elif count is None:
                unknown[name] += 1
    expected = {**dict(totals), "temporal_integer_subtotals": dict(subtotals),
        "temporal_unknown_metric_contexts": dict(unknown), "temporal_saved_contexts": len(rows),
        "temporal_failed_contexts": 0, **previous._cohort_counts(plan, totals),
        "context_status_counts": dict(Counter(r["status"] for r in rows))}
    if not indexed._same(report["summary"], expected):
        raise ValueError("temporal_parent_summary_or_unexecuted_denominator_mismatch")
    return data


def load_case(data, row):
    return data["cases"][tuple(row["context_key"])]


def run(temporal, output, **limits):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("trial_output_must_be_new_direct_workspace_child")
    if set(limits) - set(SETTINGS):
        raise ValueError("unknown_boundary_trial_limits")
    settings = {**SETTINGS, **limits}
    for name, value in settings.items():
        _limit(value, name)
    from . import factor_boundary_explanations as engine
    data = load_inputs(temporal)
    ancestors = _ancestors(data)
    inputs = {p: value for _, ancestor in ancestors for p, value in ancestor["hashes"].items()}
    code = {str(p.resolve()): parent.file_digest(p) for p in parent._code_paths()}
    plan = {"version": VERSION, "temporal": str(data["directory"]),
        "parent_report_sha256": parent.file_digest(data["directory"] / "report.json"),
        "inputs": deepcopy(inputs), "code": code, "settings": settings,
        **{k: deepcopy(data["plan"][k]) for k in ("declared_contexts", "declared_units", "selected_contexts", "selection")},
        "cohort_complete": False, "old_selector_or_analysis_reexecuted": False, "all_logical_paths_evaluated": False,
        "source_labels_used_for_inference": False, "old_paths_or_bundles_extended": False, "production_modified": False,
        "conditional_boundary_role_stage_enabled": True, "conditional_NCT_evaluated": False,
        "boundary_NCT_evaluated": False, "delayed_resolution_evaluated": False,
        "coverage": "original_touching_slot_pairs_with_factored_roles_and_new_complete_chain_bundles_not_music_ranking"}
    output.mkdir()
    artifacts, rows, failures, totals, metric_totals, unknown_metrics = {}, [], [], Counter(), Counter(), Counter()
    storage._save(output, "run-plan.json", plan, artifacts)
    for row in data["rows"]:
        case_started = perf_counter()
        entry = {"context_key": deepcopy(row["context_key"]), "old_row_sha256": digest(row),
            **{k: deepcopy(row[k]) for k in (*INHERITED_ROW_FIELDS, "temporal_explanations", "temporal_counts")},
            "boundary_explanations": None, "boundary_counts": None, "status": "not_calculated", "error": None}
        previous._add_denominators(totals, row)
        print(f"[{len(rows)+1}/{len(data['rows'])}] conditional boundary roles {row['context_key'][0]}", flush=True)
        owned, before = None, None
        try:
            owned = load_case(data, row)
            before = digest(owned)
            value = engine.build_explanations_prepared(data["boundary_sessions"][tuple(row["context_key"])], **settings)
            if before != digest(owned):
                raise ValueError("boundary_trial_parent_or_IR_mutated")
            path = storage._save(output, "boundary-explanations/" + value["record_id"] + ".json.gz", value, artifacts, compressed=True)
            entry["boundary_explanations"] = {"artifact": str(path), "sha256": artifacts[str(path)],
                "record_ref": frozen._ref(value), "status": value["status"]}
            entry["boundary_counts"] = deepcopy(value["summary"])
            for name, count in value["summary"].items():
                if type(count) is int:
                    metric_totals[name] += count
                elif count is None:
                    unknown_metrics[name] += 1
            entry["status"] = "boundary_role_explanations_saved_not_selected"
        except Exception as exc:
            entry["status"] = "calculation_failure"
            entry["error"] = f"{type(exc).__name__}:{exc}"
            failures.append({"context_key": deepcopy(row["context_key"]), "error": entry["error"]})
        if owned is not None and before != digest(owned):
            entry["status"], entry["error"] = "calculation_failure", "ValueError:boundary_trial_parent_or_IR_mutated"
            failure = {"context_key": deepcopy(entry["context_key"]), "error": entry["error"]}
            if failure not in failures:
                failures.append(failure)
        entry["elapsed_seconds"] = perf_counter() - case_started
        rows.append(entry)
        print(f"[{len(rows)}/{len(data['rows'])}] {entry['status']} {entry['elapsed_seconds']:.3f}s", flush=True)
    storage._save(output, "context-index.json", rows, artifacts)
    changed = [p for p, value in {**inputs, **code}.items() if not Path(p).is_file() or parent.file_digest(p) != value]
    if {str(p.resolve()) for p in parent._code_paths()} != set(code):
        changed.append("current_code_inventory_changed")
    for name, ancestor in ancestors:
        if {str(p.resolve()) for p in ancestor["directory"].rglob("*") if p.is_file()} != ancestor["inventory"]:
            changed.append(name + "_parent_inventory_changed")
    changed_artifacts = [p for p, value in artifacts.items() if not Path(p).is_file() or parent.file_digest(p) != value]
    if {str(p.resolve()) for p in output.rglob("*") if p.is_file()} != set(artifacts):
        changed_artifacts.append("generated_artifact_inventory_changed")
    denominator = indexed._same([r["context_key"] for r in rows], plan["selected_contexts"]) and all(
        totals[name] == data["report"]["summary"][name] for name in DENOMINATORS)
    integrity = not failures and not changed and not changed_artifacts
    report = {"version": VERSION, "scope_calculation_complete": bool(integrity and denominator),
        "computation_integrity_passed": bool(integrity), "selected_denominators_complete": bool(denominator),
        "inputs_and_code_unchanged": not changed, "artifacts_unchanged": not changed_artifacts,
        "changed_inputs_or_code": changed, "changed_artifacts": changed_artifacts, "failures": failures,
        "artifact_hashes": deepcopy(artifacts), "parent_summary": deepcopy(data["report"]["summary"]),
        "summary": {**dict(totals), "boundary_integer_subtotals": dict(metric_totals),
            "boundary_unknown_metric_contexts": dict(unknown_metrics),
            "boundary_saved_contexts": sum(r["boundary_explanations"] is not None for r in rows),
            "boundary_failed_contexts": sum(r["status"] == "calculation_failure" for r in rows),
            **previous._cohort_counts(plan, totals), "context_status_counts": dict(Counter(r["status"] for r in rows))},
        "cohort_complete": False, "all_logical_paths_evaluated": False, "selected": None,
        **{k: False for k in POLICY_FALSE}, "conditional_boundary_role_stage_enabled": True,
        "conditional_NCT_evaluated": False, "boundary_NCT_evaluated": False, "delayed_resolution_evaluated": False,
        "elapsed_seconds": perf_counter() - started,
        "limits": ["Conditional boundary roles are shape evidence, not confirmed suspension, anticipation or harmony.",
            "Only original touching group slots share a pair envelope; no outside-note harmony is extrapolated.",
            "All required links coexist in one new authentic all-raw-lane completion; parent bundles remain unchanged.",
            "Credit is clipped to the affected nonmember portion: suspension right, anticipation left; raw note time remains unchanged.",
            "Strict carry differs from same-pitch rearticulation; consonance, accent, key and whole functional delayed obligations remain unassessed.",
            "Integer subtotals distinguish zero from unknown; failed and unexecuted denominator rows are retained."]}
    parent.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("temporal", "output"):
        parser.add_argument("--" + name, required=True)
    for name, value in SETTINGS.items():
        parser.add_argument("--" + name.replace("_", "-"), type=int, default=value)
    report = run(**vars(parser.parse_args()))
    print(report["summary"], flush=True)
    return 0 if report["scope_calculation_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
