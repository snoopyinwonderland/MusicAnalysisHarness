"""Append-only literal grounding of lossless function-shape relations.

Historical catalogues, shape complements and technical queries are protected.
Grounded membership/direct-motion prerequisites are not selected harmony/NCT.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from . import factor_function_relation_trial as previous
from . import factor_function_relations as shapes
from . import factor_indexed_hypotheses as indexed
from . import factor_expanded_hypotheses as frozen
from . import factor_musical_trial as storage
from . import harmony_frozen_context_lineage_trial as parent
from .musical_pattern_observation import digest

ROOT = parent.ROOT
VERSION = "factor-grounded-relation-trial-0.1.0"
POLICY_FALSE = previous.POLICY_FALSE
PARENT_METRICS = (
    "semantic_types", "planned_source_kernels", "materialized_source_kernels",
    "shared_target_relations", "shared_key_projections", "factored_function_rows",
    "unassessed_function_rows", "conditional_function_shape_rows", "withheld_function_shape_rows",
    "terminal_target_rows", "literal_profiles_computed", "actual_endpoint_pairs_computed",
    "motion_groups_computed", "same_bundle_assessments_computed")
DENOMINATORS = ("contexts", "old_raw_lanes", "old_groups", "indexed_groups", "logical_paths",
    "logical_path_key_tuples", "logical_function_rows", "unknown_logical_groups",
    "origin_variants", "shared_profile_descriptors")


def _limit(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("explicit_nonnegative_integer_trial_limit_required:" + name)


def _registered(data, row, stage):
    info = row.get(stage)
    if type(info) is not dict:
        raise ValueError("complete_registered_relation_stage_required:" + stage)
    path = Path(info["artifact"]).resolve(strict=True)
    folder = "relations" if stage == "relations" else "function-samples"
    if path.parent != data["directory"] / folder or data["hashes"].get(str(path)) != info["sha256"]:
        raise ValueError("foreign_or_unregistered_relation_stage:" + stage)
    value = parent._load(path, data["hashes"], compressed=True)
    if stage == "relations":
        frozen._check(value, shapes.PREFIX)
        if (not indexed._same(frozen._ref(value), info["record_ref"])
                or value["status"] != info["status"] or path.name != value["record_id"] + ".json.gz"):
            raise ValueError("relation_stage_identity_or_status_mismatch")
    return value


def _check_samples(samples, row, scope, hypotheses, index, relations, session):
    """Exact public function replay; historical profile/motion is NOT rerun."""
    indexed._closed(samples, {"version", "context_key", "index_ref", "relations_ref", "sampling",
        "requests", "queries", "selected", "musical_accuracy_measured", "profiles_evaluated",
        "motion_evaluated", "all_logical_paths_evaluated"}, "saved_relation_function_samples")
    requests = previous.sample_requests(hypotheses, index)
    expected = {"version": previous.VERSION, "context_key": row["context_key"],
        "index_ref": frozen._ref(index), "relations_ref": frozen._ref(relations),
        "sampling": previous.SAMPLING, "requests": requests, "selected": None,
        "musical_accuracy_measured": False, "profiles_evaluated": False,
        "motion_evaluated": False, "all_logical_paths_evaluated": False}
    if (any(not indexed._same(samples[name], value) for name, value in expected.items())
            or type(samples["queries"]) is not list or len(samples["queries"]) != len(requests)
            or type(row["function_samples"]["requests"]) is not int
            or type(row["function_samples"]["queries"]) is not int
            or row["function_samples"]["requests"] != len(requests)
            or row["function_samples"]["queries"] != len(requests)
            or Path(row["function_samples"]["artifact"]).name != relations["record_id"] + ".json.gz"):
        raise ValueError("saved_relation_samples_policy_identity_or_denominator_mismatch")
    for request, actual in zip(requests, samples["queries"]):
        expected_query = shapes.query_function_prepared(session, **request)
        if not indexed._same(actual, expected_query):
            raise ValueError("saved_relation_function_query_fresh_replay_mismatch")


def load_inputs(directory):
    """Validate every registered shape parent BEFORE creating new output."""
    directory = Path(directory).resolve(strict=True)
    report_path = directory / "report.json"
    report = parent.read(report_path)
    indexed._closed(report, {"version", "scope_calculation_complete", "computation_integrity_passed",
        "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged",
        "changed_inputs_or_code", "changed_artifacts", "failures", "artifact_hashes", "summary",
        "cohort_complete", "all_logical_paths_evaluated", "selected", *POLICY_FALSE,
        "profiles_evaluated", "motion_evaluated", "same_bundle_evaluated", "elapsed_seconds", "limits"},
        "saved_function_relation_report")
    if (report.get("version") != previous.VERSION
            or any(report.get(k) is not True for k in ("scope_calculation_complete", "computation_integrity_passed",
                "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged"))
            or report.get("selected") is not None
            or any(report.get(k) is not False for k in (*POLICY_FALSE, "cohort_complete",
                "all_logical_paths_evaluated", "profiles_evaluated", "motion_evaluated", "same_bundle_evaluated"))
            or any(report.get(k) != [] for k in ("failures", "changed_inputs_or_code", "changed_artifacts"))):
        raise ValueError("completed_unselected_function_relation_parent_required")
    hashes = {}
    parent._guard({str(report_path): parent.file_digest(report_path)}, hashes)
    if type(report["artifact_hashes"]) is not dict or any(
            not Path(p).resolve().is_relative_to(directory) for p in report["artifact_hashes"]):
        raise ValueError("relation_parent_artifact_outside_registered_directory")
    parent._guard(report["artifact_hashes"], hashes)
    inventory = parent._inventory(directory, hashes)
    plan = parent._load(directory / "run-plan.json", hashes)
    indexed._closed(plan, {"version", "indexed", "parent_report_sha256", "inputs", "code", "settings",
        "declared_contexts", "declared_units", "selected_contexts", "selection", "sampling", "cohort_complete",
        "old_selector_or_analysis_reexecuted", "all_logical_paths_evaluated", "source_labels_used_for_inference",
        "old_paths_or_bundles_extended", "production_modified", "profiles_evaluated", "motion_evaluated",
        "same_bundle_evaluated"}, "saved_function_relation_plan")
    if (plan.get("version") != previous.VERSION or plan.get("sampling") != previous.SAMPLING
            or any(plan.get(k) is not False for k in ("cohort_complete", "old_selector_or_analysis_reexecuted",
                "all_logical_paths_evaluated", "source_labels_used_for_inference", "old_paths_or_bundles_extended",
                "production_modified", "profiles_evaluated", "motion_evaluated", "same_bundle_evaluated"))):
        raise ValueError("relation_parent_plan_policy_mismatch")
    indexed._closed(plan["settings"], {"max_kernels"}, "saved_relation_settings")
    _limit(plan["settings"]["max_kernels"], "max_kernels")
    parent._guard(plan["inputs"], hashes)
    parent._guard(plan["code"], hashes)
    old = previous.load_inputs(plan["indexed"])
    ancestors = [old, old["expanded"], old["expanded"]["prerequisites"],
                 old["expanded"]["prerequisites"]["family"]]
    expected_inputs = {p: value for ancestor in ancestors for p, value in ancestor["hashes"].items()}
    if not indexed._same(plan["inputs"], expected_inputs):
        raise ValueError("relation_parent_exact_protected_input_closure_mismatch")
    if (plan["parent_report_sha256"] != parent.file_digest(old["directory"] / "report.json")
            or any(not indexed._same(plan[k], old["plan"][k]) for k in
                   ("declared_contexts", "declared_units", "selected_contexts", "selection"))):
        raise ValueError("relation_parent_declared_lineage_mismatch")
    rows = parent._load(directory / "context-index.json", hashes)
    if (type(rows) is not list or not indexed._same([r["context_key"] for r in rows], plan["selected_contexts"])
            or len({tuple(r["context_key"]) for r in rows}) != len(rows)
            or len(rows) != report["summary"]["contexts"]):
        raise ValueError("relation_parent_context_denominator_mismatch")
    artifacts = {str(directory / name) for name in ("run-plan.json", "context-index.json")}
    artifacts.update(str(Path(row[stage]["artifact"]).resolve(strict=True)) for row in rows
                     for stage in ("relations", "function_samples"))
    if set(report["artifact_hashes"]) != artifacts:
        raise ValueError("relation_parent_exact_artifact_inventory_mismatch")
    data = {"directory": directory, "report": report, "plan": plan, "rows": rows,
        "hashes": hashes, "inventory": inventory, "indexed": old, "cases": {}}
    totals = Counter()
    state_totals = dict.fromkeys(shapes.SHAPE_STATES, 0)
    kind_totals = dict.fromkeys(shapes.FUNCTION_KINDS, 0)
    for position, (row, original) in enumerate(zip(rows, old["rows"]), 1):
        print(f"[parent {position}/{len(rows)}] protected relation/source replay {row['context_key'][0]}", flush=True)
        if (row["status"] != "relations_and_function_queries_saved_not_selected" or row["error"] is not None
                or row["old_row_sha256"] != digest(original)
                or any(not indexed._same(row[k], original[k]) for k in ("old_groups", "old_lane_refs",
                    "old_hypothesis_counts", "old_assessment_counts", "expanded_scope", "hypotheses",
                    "indexed_universe", "index_counts"))):
            raise ValueError("relation_parent_original_context_or_origins_mismatch")
        case = previous.load_case(old, original)
        packet, ir, extension, scope, hypotheses, assessment, index = case
        relations = _registered(data, row, "relations")
        if not indexed._same(relations["resource_limits"], plan["settings"]):
            raise ValueError("relation_parent_saved_limit_mismatch")
        session = shapes.prepare_relations(ir, scope, hypotheses, index, relations)
        if not indexed._same(row["relation_counts"], relations["summary"]):
            raise ValueError("relation_parent_saved_counts_mismatch")
        samples = _registered(data, row, "function_samples")
        _check_samples(samples, row, scope, hypotheses, index, relations, session)
        data["cases"][tuple(row["context_key"])] = (*case, relations)
        count = row["index_counts"]
        totals.update(contexts=1, old_raw_lanes=len(row["old_lane_refs"]), old_groups=len(row["old_groups"]),
            indexed_groups=count["groups"], logical_paths=count["logical_paths"],
            logical_path_key_tuples=count["logical_path_key_tuples"], logical_function_rows=count["logical_function_shapes"],
            unknown_logical_groups=count["unknown_product_groups"], origin_variants=count["indexed_variants"],
            shared_profile_descriptors=count["shared_profile_descriptors"])
        for name in PARENT_METRICS:
            totals[name] += relations["summary"][name]
        for name, count in relations["summary"]["shape_state_counts"].items():
            state_totals[name] += count
        for name, count in relations["summary"]["function_kind_counts"].items():
            kind_totals[name] += count
        totals["queried_function_rows"] += sum(q["function"] is not None for q in samples["queries"])
        totals["technical_function_requests"] += len(samples["requests"])
    expected = {**dict(totals), "shape_state_counts": state_totals, "function_kind_counts": kind_totals,
        "old_planned_paths": old["report"]["summary"]["old_planned_paths"],
        "old_unknown_path_group_counts": old["report"]["summary"]["old_unknown_path_group_counts"],
        "declared_contexts": len(plan["declared_contexts"]), "declared_original_raw_lanes": len(plan["declared_units"]),
        "unexecuted_original_contexts": len(plan["declared_contexts"]) - len(rows),
        "unexecuted_original_raw_lanes": len(plan["declared_units"]) - totals["old_raw_lanes"],
        "context_status_counts": dict(Counter(r["status"] for r in rows))}
    if not indexed._same(report["summary"], expected):
        raise ValueError("relation_parent_summary_or_unexecuted_denominator_mismatch")
    return data


def load_case(data, row):
    return data["cases"][tuple(row["context_key"])]


def run(relations, output, *, max_profiles=65536, max_motion_kernels=65536,
        max_motion_pairs=65536, max_joint_options=65536):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("trial_output_must_be_new_direct_workspace_child")
    settings = {"max_profiles": max_profiles, "max_motion_kernels": max_motion_kernels,
        "max_motion_pairs": max_motion_pairs, "max_joint_options": max_joint_options}
    for name, value in settings.items():
        _limit(value, name)
    from . import factor_grounded_relations as engine
    data = load_inputs(relations)
    ancestors = [("relations", data), ("indexed", data["indexed"]),
        ("expanded", data["indexed"]["expanded"]),
        ("prerequisite", data["indexed"]["expanded"]["prerequisites"]),
        ("family", data["indexed"]["expanded"]["prerequisites"]["family"])]
    inputs = {p: value for _, ancestor in ancestors for p, value in ancestor["hashes"].items()}
    code = {str(p.resolve()): parent.file_digest(p) for p in parent._code_paths()}
    plan = {"version": VERSION, "relations": str(data["directory"]),
        "parent_report_sha256": parent.file_digest(data["directory"] / "report.json"),
        "inputs": deepcopy(inputs), "code": code, "settings": settings,
        **{k: deepcopy(data["plan"][k]) for k in ("declared_contexts", "declared_units", "selected_contexts", "selection")},
        "cohort_complete": False, "old_selector_or_analysis_reexecuted": False,
        "all_logical_paths_evaluated": False, "source_labels_used_for_inference": False,
        "old_paths_or_bundles_extended": False, "production_modified": False,
        "conditional_NCT_evaluated": False, "delayed_resolution_evaluated": False,
        "coverage": "all_exact_profile_descriptors_and_shape_eligible_direct_motion_kernels_not_music_ranking"}
    output.mkdir()
    artifacts, rows, failures, totals, grounding_totals = {}, [], [], Counter(), Counter()
    unknown_metrics = Counter()
    storage._save(output, "run-plan.json", plan, artifacts)
    for row in data["rows"]:
        case_started = perf_counter()
        entry = {"context_key": deepcopy(row["context_key"]), "old_row_sha256": digest(row),
            **{k: deepcopy(row[k]) for k in ("old_groups", "old_lane_refs", "old_hypothesis_counts",
                "old_assessment_counts", "expanded_scope", "hypotheses", "indexed_universe", "index_counts",
                "relations", "relation_counts", "function_samples")},
            "grounding": None, "status": "not_calculated", "error": None}
        count = row["index_counts"]
        totals.update(contexts=1, old_raw_lanes=len(row["old_lane_refs"]), old_groups=len(row["old_groups"]),
            indexed_groups=count["groups"], logical_paths=count["logical_paths"],
            logical_path_key_tuples=count["logical_path_key_tuples"], logical_function_rows=count["logical_function_shapes"],
            unknown_logical_groups=count["unknown_product_groups"], origin_variants=count["indexed_variants"],
            shared_profile_descriptors=count["shared_profile_descriptors"])
        print(f"[{len(rows)+1}/{len(data['rows'])}] literal/direct-motion grounding {row['context_key'][0]}", flush=True)
        owned, before = None, None
        try:
            owned = load_case(data, row)
            before = digest(owned)
            packet, ir, extension, scope, h, assessment, index, relation = owned
            grounding = engine.build_grounding(ir, scope, h, index, relation, **settings)
            path = storage._save(output, "groundings/" + grounding["record_id"] + ".json.gz", grounding, artifacts, compressed=True)
            entry["grounding"] = {"artifact": str(path), "sha256": artifacts[str(path)],
                "record_ref": frozen._ref(grounding), "status": grounding["status"]}
            entry["grounding_counts"] = deepcopy(grounding["summary"])
            for name, value in grounding["summary"].items():
                if type(value) is int:
                    grounding_totals[name] += value
                elif value is None:
                    unknown_metrics[name] += 1
            entry["status"] = "literal_and_direct_motion_grounding_saved_not_selected"
        except Exception as exc:
            entry["status"] = "calculation_failure"
            entry["error"] = f"{type(exc).__name__}:{exc}"
            failures.append({"context_key": deepcopy(row["context_key"]), "error": entry["error"]})
        if owned is not None and before != digest(owned):
            entry["status"], entry["error"] = "calculation_failure", "ValueError:grounded_trial_parent_or_IR_mutated"
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
        "summary": {**dict(totals), "grounding_integer_subtotals": dict(grounding_totals),
            "grounding_unknown_metric_contexts": dict(unknown_metrics),
            "grounding_saved_contexts": sum(row["grounding"] is not None for row in rows),
            "grounding_failed_contexts": sum(row["status"] == "calculation_failure" for row in rows),
            "declared_contexts": len(plan["declared_contexts"]), "declared_original_raw_lanes": len(plan["declared_units"]),
            "unexecuted_original_contexts": len(plan["declared_contexts"]) - totals["contexts"],
            "unexecuted_original_raw_lanes": len(plan["declared_units"]) - totals["old_raw_lanes"],
            "context_status_counts": dict(Counter(r["status"] for r in rows))},
        "cohort_complete": False, "all_logical_paths_evaluated": False, "selected": None,
        **{k: False for k in POLICY_FALSE}, "conditional_NCT_evaluated": False, "delayed_resolution_evaluated": False,
        "elapsed_seconds": perf_counter() - started,
        "limits": ["Literal membership and direct motion are conditional prerequisites, not confirmed harmony or NCT.",
            "Every shape false/unknown/terminal complement, original origin and known/unknown denominator remains in its parent.",
            "All critical links must coexist in one actual all-lane completion; independent witnesses are never votes.",
            "Integer metric subtotals do not convert unknown, held or failed contexts into zero or full coverage.",
            "Delayed resolution, conditional NCT, local-key selection, cadence, accuracy, training, gold, generation and production are unassessed."]}
    parent.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("relations", "output"):
        parser.add_argument("--" + name, required=True)
    for name in ("max_profiles", "max_motion_kernels", "max_motion_pairs", "max_joint_options"):
        parser.add_argument("--" + name.replace("_", "-"), type=int, default=65536)
    report = run(**vars(parser.parse_args()))
    print(report["summary"], flush=True)
    return 0 if report["scope_calculation_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
