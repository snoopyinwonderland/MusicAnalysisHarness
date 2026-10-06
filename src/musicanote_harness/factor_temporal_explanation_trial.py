"""Append-only temporal presentation and conditional local contour trial.

Authentic expanded descriptors and new complete local-chain bundles are separate
from the frozen direct-motion experiment. No harmony or NCT label is selected.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from . import factor_grounded_relation_trial as previous
from . import factor_grounded_relations as grounded
from . import factor_indexed_hypotheses as indexed
from . import factor_expanded_hypotheses as frozen
from . import factor_musical_trial as storage
from . import harmony_frozen_context_lineage_trial as parent
from .musical_pattern_observation import digest

ROOT = parent.ROOT
VERSION = "factor-temporal-explanation-trial-0.1.0"
POLICY_FALSE = previous.POLICY_FALSE
DENOMINATORS = previous.DENOMINATORS
SETTINGS = {"max_geometry_candidates": 4096, "max_membership_relations": 65536,
    "max_new_bundles": 4096, "max_account_templates": 262144, "query_work_budget": 100000}
INHERITED_ROW_FIELDS = ("old_groups", "old_lane_refs", "old_hypothesis_counts",
    "old_assessment_counts", "expanded_scope", "hypotheses", "indexed_universe", "index_counts",
    "relations", "relation_counts", "function_samples")
GROUNDING_SETTINGS = ("max_profiles", "max_motion_kernels", "max_motion_pairs", "max_joint_options")
GROUNDING_COVERAGE = "all_exact_profile_descriptors_and_shape_eligible_direct_motion_kernels_not_music_ranking"


def _limit(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("explicit_nonnegative_integer_trial_limit_required:" + name)


def _ancestors(data):
    relations = data["relations"]
    index = relations["indexed"]
    expanded = index["expanded"]
    prerequisites = expanded["prerequisites"]
    return [("grounding", data), ("relations", relations), ("indexed", index),
        ("expanded", expanded), ("prerequisite", prerequisites), ("family", prerequisites["family"])]


def _registered(data, row):
    info = row.get("grounding")
    indexed._closed(info, {"artifact", "sha256", "record_ref", "status"}, "registered_grounding_stage")
    path = Path(info["artifact"]).resolve(strict=True)
    if path.parent != data["directory"] / "groundings" or data["hashes"].get(str(path)) != info["sha256"]:
        raise ValueError("foreign_or_unregistered_grounding_stage")
    value = parent._load(path, data["hashes"], compressed=True)
    frozen._check(value, grounded.PREFIX)
    if (not indexed._same(frozen._ref(value), info["record_ref"])
            or value["status"] != info["status"] or path.name != value["record_id"] + ".json.gz"):
        raise ValueError("grounding_stage_identity_or_status_mismatch")
    return value


def load_inputs(directory):
    """Check the closed grounded parent and fresh source replay before output."""
    directory = Path(directory).resolve(strict=True)
    report_path = directory / "report.json"
    report = parent.read(report_path)
    indexed._closed(report, {"version", "scope_calculation_complete", "computation_integrity_passed",
        "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged",
        "changed_inputs_or_code", "changed_artifacts", "failures", "artifact_hashes", "parent_summary",
        "summary", "cohort_complete", "all_logical_paths_evaluated", "selected", *POLICY_FALSE,
        "conditional_NCT_evaluated", "delayed_resolution_evaluated", "elapsed_seconds", "limits"},
        "saved_grounded_relation_report")
    if (report.get("version") != previous.VERSION
            or any(report.get(k) is not True for k in ("scope_calculation_complete", "computation_integrity_passed",
                "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged"))
            or report.get("selected") is not None
            or any(report.get(k) is not False for k in (*POLICY_FALSE, "cohort_complete",
                "all_logical_paths_evaluated", "conditional_NCT_evaluated", "delayed_resolution_evaluated"))
            or any(report.get(k) != [] for k in ("failures", "changed_inputs_or_code", "changed_artifacts"))):
        raise ValueError("completed_unselected_grounded_parent_required")
    indexed._closed(report["summary"], {*DENOMINATORS, "grounding_integer_subtotals",
        "grounding_unknown_metric_contexts", "grounding_saved_contexts", "grounding_failed_contexts",
        "declared_contexts", "declared_original_raw_lanes", "unexecuted_original_contexts",
        "unexecuted_original_raw_lanes", "context_status_counts"}, "saved_grounding_summary")
    hashes = {}
    parent._guard({str(report_path): parent.file_digest(report_path)}, hashes)
    if type(report["artifact_hashes"]) is not dict or any(
            not Path(p).resolve().is_relative_to(directory) for p in report["artifact_hashes"]):
        raise ValueError("grounded_parent_artifact_outside_registered_directory")
    parent._guard(report["artifact_hashes"], hashes)
    inventory = parent._inventory(directory, hashes)
    plan = parent._load(directory / "run-plan.json", hashes)
    indexed._closed(plan, {"version", "relations", "parent_report_sha256", "inputs", "code", "settings",
        "declared_contexts", "declared_units", "selected_contexts", "selection", "cohort_complete",
        "old_selector_or_analysis_reexecuted", "all_logical_paths_evaluated", "source_labels_used_for_inference",
        "old_paths_or_bundles_extended", "production_modified", "conditional_NCT_evaluated",
        "delayed_resolution_evaluated", "coverage"}, "saved_grounded_relation_plan")
    if (plan.get("version") != previous.VERSION or plan.get("coverage") != GROUNDING_COVERAGE
            or any(plan.get(k) is not False for k in ("cohort_complete", "old_selector_or_analysis_reexecuted",
                "all_logical_paths_evaluated", "source_labels_used_for_inference", "old_paths_or_bundles_extended",
                "production_modified", "conditional_NCT_evaluated", "delayed_resolution_evaluated"))):
        raise ValueError("grounded_parent_plan_policy_mismatch")
    indexed._closed(plan["settings"], set(GROUNDING_SETTINGS), "saved_grounding_settings")
    for name, value in plan["settings"].items():
        _limit(value, name)
    if type(plan["inputs"]) is not dict or type(plan["code"]) is not dict:
        raise ValueError("grounded_parent_declared_hash_maps_required")
    parent._guard(plan["inputs"], hashes)
    parent._guard(plan["code"], hashes)
    old = previous.load_inputs(plan["relations"])
    ancestors = [old, old["indexed"], old["indexed"]["expanded"],
        old["indexed"]["expanded"]["prerequisites"], old["indexed"]["expanded"]["prerequisites"]["family"]]
    expected_inputs = {p: value for ancestor in ancestors for p, value in ancestor["hashes"].items()}
    if not indexed._same(plan["inputs"], expected_inputs):
        raise ValueError("grounded_parent_exact_protected_input_closure_mismatch")
    if (plan["parent_report_sha256"] != parent.file_digest(old["directory"] / "report.json")
            or not indexed._same(report["parent_summary"], old["report"]["summary"])
            or any(not indexed._same(plan[k], old["plan"][k]) for k in
                ("declared_contexts", "declared_units", "selected_contexts", "selection"))):
        raise ValueError("grounded_parent_declared_lineage_or_summary_mismatch")
    rows = parent._load(directory / "context-index.json", hashes)
    if (type(rows) is not list or not indexed._same([r["context_key"] for r in rows], plan["selected_contexts"])
            or len({tuple(r["context_key"]) for r in rows}) != len(rows)
            or len(rows) != report["summary"]["contexts"]):
        raise ValueError("grounded_parent_context_denominator_mismatch")
    artifacts = {str(directory / name) for name in ("run-plan.json", "context-index.json")}
    artifacts.update(str(Path(row["grounding"]["artifact"]).resolve(strict=True)) for row in rows)
    if set(report["artifact_hashes"]) != artifacts:
        raise ValueError("grounded_parent_exact_artifact_inventory_mismatch")
    data = {"directory": directory, "report": report, "plan": plan, "rows": rows, "hashes": hashes,
        "inventory": inventory, "relations": old, "cases": {}, "grounded_sessions": {}}
    totals, subtotals, unknown = Counter(), Counter(), Counter()
    for position, (row, original) in enumerate(zip(rows, old["rows"]), 1):
        indexed._closed(row, {"context_key", "old_row_sha256", *INHERITED_ROW_FIELDS, "grounding",
            "grounding_counts", "status", "error", "elapsed_seconds"}, "saved_grounding_context_row")
        print(f"[parent {position}/{len(rows)}] protected literal/chain source replay {row['context_key'][0]}", flush=True)
        if (row["status"] != "literal_and_direct_motion_grounding_saved_not_selected" or row["error"] is not None
                or row["old_row_sha256"] != digest(original)
                or any(not indexed._same(row[k], original[k]) for k in INHERITED_ROW_FIELDS)):
            raise ValueError("grounded_parent_original_context_or_origins_mismatch")
        case = previous.load_case(old, original)
        packet, ir, extension, scope, hypotheses, assessment, index, relations = case
        grounding = _registered(data, row)
        if (not indexed._same(grounding["resource_limits"], plan["settings"])
                or not indexed._same(row["grounding_counts"], grounding["summary"])):
            raise ValueError("grounded_parent_saved_limit_or_counts_mismatch")
        from . import factor_temporal_explanations as engine
        session = engine.prepare_inputs(ir, scope, hypotheses, index, relations, grounding)
        data["cases"][tuple(row["context_key"])] = (*case, grounding)
        data["grounded_sessions"][tuple(row["context_key"])] = session
        _add_denominators(totals, row)
        for name, value in grounding["summary"].items():
            if type(value) is int:
                subtotals[name] += value
            elif value is None:
                unknown[name] += 1
    expected = {**dict(totals), "grounding_integer_subtotals": dict(subtotals),
        "grounding_unknown_metric_contexts": dict(unknown), "grounding_saved_contexts": len(rows),
        "grounding_failed_contexts": 0, **_cohort_counts(plan, totals),
        "context_status_counts": dict(Counter(r["status"] for r in rows))}
    if not indexed._same(report["summary"], expected):
        raise ValueError("grounded_parent_summary_or_unexecuted_denominator_mismatch")
    return data


def load_case(data, row):
    return data["cases"][tuple(row["context_key"])]


def _add_denominators(totals, row):
    count = row["index_counts"]
    totals.update(contexts=1, old_raw_lanes=len(row["old_lane_refs"]), old_groups=len(row["old_groups"]),
        indexed_groups=count["groups"], logical_paths=count["logical_paths"],
        logical_path_key_tuples=count["logical_path_key_tuples"], logical_function_rows=count["logical_function_shapes"],
        unknown_logical_groups=count["unknown_product_groups"], origin_variants=count["indexed_variants"],
        shared_profile_descriptors=count["shared_profile_descriptors"])


def _cohort_counts(plan, totals):
    return {"declared_contexts": len(plan["declared_contexts"]), "declared_original_raw_lanes": len(plan["declared_units"]),
        "unexecuted_original_contexts": len(plan["declared_contexts"]) - totals["contexts"],
        "unexecuted_original_raw_lanes": len(plan["declared_units"]) - totals["old_raw_lanes"]}


def run(grounding, output, **limits):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("trial_output_must_be_new_direct_workspace_child")
    if set(limits) - set(SETTINGS):
        raise ValueError("unknown_temporal_trial_limits")
    settings = {**SETTINGS, **limits}
    for name, value in settings.items():
        _limit(value, name)
    from . import factor_temporal_explanations as engine
    data = load_inputs(grounding)
    ancestors = _ancestors(data)
    inputs = {p: value for _, ancestor in ancestors for p, value in ancestor["hashes"].items()}
    code = {str(p.resolve()): parent.file_digest(p) for p in parent._code_paths()}
    plan = {"version": VERSION, "grounding": str(data["directory"]),
        "parent_report_sha256": parent.file_digest(data["directory"] / "report.json"),
        "inputs": deepcopy(inputs), "code": code, "settings": settings,
        **{k: deepcopy(data["plan"][k]) for k in ("declared_contexts", "declared_units", "selected_contexts", "selection")},
        "cohort_complete": False, "old_selector_or_analysis_reexecuted": False, "all_logical_paths_evaluated": False,
        "source_labels_used_for_inference": False, "old_paths_or_bundles_extended": False, "production_modified": False,
        "conditional_local_contour_stage_enabled": True, "boundary_NCT_evaluated": False, "delayed_resolution_evaluated": False,
        "coverage": "all_exact_single_segment_descriptors_with_separate_authentic_local_chain_bundles_not_music_ranking"}
    output.mkdir()
    artifacts, rows, failures, totals, metric_totals, unknown_metrics = {}, [], [], Counter(), Counter(), Counter()
    storage._save(output, "run-plan.json", plan, artifacts)
    for row in data["rows"]:
        case_started = perf_counter()
        entry = {"context_key": deepcopy(row["context_key"]), "old_row_sha256": digest(row),
            **{k: deepcopy(row[k]) for k in (*INHERITED_ROW_FIELDS, "grounding", "grounding_counts")},
            "temporal_explanations": None, "temporal_counts": None, "status": "not_calculated", "error": None}
        _add_denominators(totals, row)
        print(f"[{len(rows)+1}/{len(data['rows'])}] temporal/local-chain explanations {row['context_key'][0]}", flush=True)
        owned, before = None, None
        try:
            owned = load_case(data, row)
            before = digest(owned)
            session = data["grounded_sessions"][tuple(row["context_key"])]
            value = engine.build_explanations_prepared(session, **settings)
            if before != digest(owned):
                raise ValueError("temporal_trial_parent_or_IR_mutated")
            path = storage._save(output, "temporal-explanations/" + value["record_id"] + ".json.gz", value, artifacts, compressed=True)
            entry["temporal_explanations"] = {"artifact": str(path), "sha256": artifacts[str(path)],
                "record_ref": frozen._ref(value), "status": value["status"]}
            entry["temporal_counts"] = deepcopy(value["summary"])
            for name, count in value["summary"].items():
                if type(count) is int:
                    metric_totals[name] += count
                elif count is None:
                    unknown_metrics[name] += 1
            entry["status"] = "temporal_and_local_contour_explanations_saved_not_selected"
        except Exception as exc:
            entry["status"] = "calculation_failure"
            entry["error"] = f"{type(exc).__name__}:{exc}"
            failures.append({"context_key": deepcopy(row["context_key"]), "error": entry["error"]})
        if owned is not None and before != digest(owned):
            entry["status"], entry["error"] = "calculation_failure", "ValueError:temporal_trial_parent_or_IR_mutated"
            failure = {"context_key": deepcopy(entry["context_key"]), "error": entry["error"]}
            if failure not in failures:
                failures.append(failure)
        entry["elapsed_seconds"] = perf_counter() - case_started
        rows.append(entry)
        print(f"[{len(rows)}/{len(data['rows'])}] {entry['status']} {entry['elapsed_seconds']:.3f}s", flush=True)
    storage._save(output, "context-index.json", rows, artifacts)
    changed = [p for p, sha in {**inputs, **code}.items() if not Path(p).is_file() or parent.file_digest(p) != sha]
    if {str(p.resolve()) for p in parent._code_paths()} != set(code):
        changed.append("current_code_inventory_changed")
    for name, ancestor in ancestors:
        if {str(p.resolve()) for p in ancestor["directory"].rglob("*") if p.is_file()} != ancestor["inventory"]:
            changed.append(name + "_parent_inventory_changed")
    changed_artifacts = [p for p, sha in artifacts.items() if not Path(p).is_file() or parent.file_digest(p) != sha]
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
        "summary": {**dict(totals), "temporal_integer_subtotals": dict(metric_totals),
            "temporal_unknown_metric_contexts": dict(unknown_metrics),
            "temporal_saved_contexts": sum(r["temporal_explanations"] is not None for r in rows),
            "temporal_failed_contexts": sum(r["status"] == "calculation_failure" for r in rows),
            **_cohort_counts(plan, totals), "context_status_counts": dict(Counter(r["status"] for r in rows))},
        "cohort_complete": False, "all_logical_paths_evaluated": False, "selected": None,
        **{k: False for k in POLICY_FALSE}, "conditional_local_contour_stage_enabled": True,
        "boundary_NCT_evaluated": False, "delayed_resolution_evaluated": False,
        "elapsed_seconds": perf_counter() - started,
        "limits": ["Member presentation and local contour accounting do not certify NCT, arpeggio, persistence or harmony.",
            "New whole-chain bundles are separately typed; historical bundles and candidate origins remain unchanged.",
            "Both critical links must coexist in one authentic all-lane completion, not independent witnesses.",
            "Raw member/nonmember/unknown evidence is never removed; only middle nonmember interval unions receive conditional credit.",
            "Metric/accent/consonance, boundary NCT, delayed chains, key, cadence, musical accuracy and production remain unassessed.",
            "Saved contexts include held records; integer subtotals retain unknown metrics and failed/unexecuted denominators."]}
    parent.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("grounding", "output"):
        parser.add_argument("--" + name, required=True)
    for name, value in SETTINGS.items():
        parser.add_argument("--" + name.replace("_", "-"), type=int, default=value)
    report = run(**vars(parser.parse_args()))
    print(report["summary"], flush=True)
    return 0 if report["scope_calculation_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
