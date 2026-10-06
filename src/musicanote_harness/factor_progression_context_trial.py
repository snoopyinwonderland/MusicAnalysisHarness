"""Append-only tonal/cadential prerequisites of the exact phase-20 panel.

This stage reuses one authentic parent authority per context. Saved technical
probes are not a representative accuracy sample, a selected harmony/key, or a
new partition/completion catalogue.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from . import factor_progression_evidence_trial as previous
from . import factor_progression_evidence as progression
from . import factor_expanded_hypotheses as frozen
from . import factor_indexed_hypotheses as indexed
from . import factor_musical_trial as storage
from . import factor_temporal_explanation_trial as cohort
from . import harmony_frozen_context_lineage_trial as parent
from .musical_pattern_observation import digest

ROOT = parent.ROOT
VERSION = "factor-progression-context-trial-0.1.0"
POLICY_FALSE = previous.POLICY_FALSE
DENOMINATORS = previous.DENOMINATORS
SETTINGS = {"max_hypotheses": 64, "max_boundary_observations": 2048,
            "max_transition_pairs": 4096, "query_work_budget": 200000}
INHERITED_ROW_FIELDS = (*previous.INHERITED_ROW_FIELDS, "delayed_obligations", "delayed_counts",
                        "progression_comparison", "progression_counts", "technical_panel")
COVERAGE = "conditional_key_function_cadence_prerequisites_of_exact_complete_original_partition_panel_not_music_ranking"


def _limit(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("explicit_nonnegative_integer_trial_limit_required:" + name)


def _ancestors(data):
    return [("progression", data), *previous._ancestors(data["delayed"])]


def _registered(data, row, prefix):
    info = row["progression_comparison"]
    indexed._closed(info, {"artifact", "sha256", "record_ref", "status"}, "registered_progression_stage")
    path = Path(info["artifact"]).resolve(strict=True)
    if (path.parent != data["directory"] / "progression-comparisons"
            or data["hashes"].get(str(path)) != info["sha256"]):
        raise ValueError("foreign_or_unregistered_progression_stage")
    value = parent._load(path, data["hashes"], compressed=True)
    frozen._check(value, prefix)
    if (not indexed._same(frozen._ref(value), info["record_ref"])
            or value["status"] != info["status"] or path.name != value["record_id"] + ".json.gz"):
        raise ValueError("progression_stage_identity_or_status_mismatch")
    return value


def load_inputs(directory):
    """Admit exact saved metadata, then replay once through owned authority."""
    directory = Path(directory).resolve(strict=True)
    report_path = directory / "report.json"
    report = parent.read(report_path)
    indexed._closed(report, {"version", "scope_calculation_complete", "computation_integrity_passed",
        "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged",
        "changed_inputs_or_code", "changed_artifacts", "failures", "artifact_hashes", "parent_summary",
        "summary", "cohort_complete", "all_logical_paths_evaluated", "selected", *POLICY_FALSE,
        "conditional_progression_comparison_stage_enabled", "conditional_NCT_evaluated", "boundary_NCT_evaluated",
        "delayed_resolution_confirmed", "sample_is_accuracy_evaluation", "elapsed_seconds", "limits"},
        "saved_progression_report")
    if (report["version"] != previous.VERSION
            or any(report[k] is not True for k in ("scope_calculation_complete", "computation_integrity_passed",
                "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged",
                "conditional_progression_comparison_stage_enabled"))
            or report["selected"] is not None
            or any(report[k] is not False for k in (*POLICY_FALSE, "cohort_complete",
                "all_logical_paths_evaluated", "conditional_NCT_evaluated", "boundary_NCT_evaluated",
                "delayed_resolution_confirmed", "sample_is_accuracy_evaluation"))
            or any(report[k] != [] for k in ("failures", "changed_inputs_or_code", "changed_artifacts"))):
        raise ValueError("completed_unselected_progression_parent_required")
    indexed._closed(report["summary"], {*DENOMINATORS, "progression_integer_subtotals",
        "progression_unknown_metric_contexts", "progression_saved_contexts", "progression_failed_contexts",
        "declared_contexts", "declared_original_raw_lanes", "unexecuted_original_contexts",
        "unexecuted_original_raw_lanes", "context_status_counts"}, "saved_progression_summary")
    hashes = {}
    parent._guard({str(report_path): parent.file_digest(report_path)}, hashes)
    if type(report["artifact_hashes"]) is not dict or any(
            not Path(p).resolve().is_relative_to(directory) for p in report["artifact_hashes"]):
        raise ValueError("progression_parent_artifact_outside_registered_directory")
    parent._guard(report["artifact_hashes"], hashes)
    inventory = parent._inventory(directory, hashes)
    plan = parent._load(directory / "run-plan.json", hashes)
    indexed._closed(plan, {"version", "delayed", "parent_report_sha256", "inputs", "code", "settings",
        "declared_contexts", "declared_units", "selected_contexts", "selection", "cohort_complete",
        "old_selector_or_analysis_reexecuted", "all_logical_paths_evaluated", "source_labels_used_for_inference",
        "old_paths_or_bundles_extended", "production_modified", "conditional_progression_comparison_stage_enabled",
        "coverage", "panel_policy", "sample_is_accuracy_evaluation"}, "saved_progression_plan")
    if (plan["version"] != previous.VERSION or plan["coverage"] != previous.COVERAGE
            or plan["panel_policy"] != previous.PANEL_POLICY
            or plan["conditional_progression_comparison_stage_enabled"] is not True
            or any(plan[k] is not False for k in ("cohort_complete", "old_selector_or_analysis_reexecuted",
                "all_logical_paths_evaluated", "source_labels_used_for_inference", "old_paths_or_bundles_extended",
                "production_modified", "sample_is_accuracy_evaluation"))):
        raise ValueError("progression_parent_plan_policy_mismatch")
    indexed._closed(plan["settings"], set(previous.SETTINGS), "saved_progression_settings")
    for name, value in plan["settings"].items():
        _limit(value, name)
    if type(plan["inputs"]) is not dict or type(plan["code"]) is not dict:
        raise ValueError("progression_parent_declared_hash_maps_required")
    parent._guard(plan["inputs"], hashes)
    parent._guard(plan["code"], hashes)
    # Exactly one authentic transitive parent replay. Its comparison sessions
    # are reused; neither a checksum nor caller metadata grants an authority.
    old = previous.load_inputs(plan["delayed"])
    expected_code = deepcopy(old["plan"]["code"])
    current_paths = {str(p.resolve()) for p in parent._code_paths()}
    for module in (previous, progression):
        path = str(Path(module.__file__).resolve())
        if path in current_paths:
            expected_code[path] = parent.file_digest(path)
    if not indexed._same(plan["code"], expected_code):
        raise ValueError("progression_parent_exact_creation_producer_inventory_mismatch")
    expected_inputs = {p: value for _, ancestor in previous._ancestors(old) for p, value in ancestor["hashes"].items()}
    if not indexed._same(plan["inputs"], expected_inputs):
        raise ValueError("progression_parent_exact_protected_input_closure_mismatch")
    if (plan["parent_report_sha256"] != parent.file_digest(old["directory"] / "report.json")
            or not indexed._same(report["parent_summary"], old["report"]["summary"])
            or any(not indexed._same(plan[k], old["plan"][k]) for k in
                ("declared_contexts", "declared_units", "selected_contexts", "selection"))):
        raise ValueError("progression_parent_declared_lineage_or_summary_mismatch")
    rows = parent._load(directory / "context-index.json", hashes)
    if (type(rows) is not list or not indexed._same([r["context_key"] for r in rows], plan["selected_contexts"])
            or len({tuple(r["context_key"]) for r in rows}) != len(rows)
            or len(rows) != report["summary"]["contexts"]):
        raise ValueError("progression_parent_context_denominator_mismatch")
    artifacts = {str(directory / name) for name in ("run-plan.json", "context-index.json")}
    artifacts.update(str(Path(row["progression_comparison"]["artifact"]).resolve(strict=True)) for row in rows)
    if set(report["artifact_hashes"]) != artifacts:
        raise ValueError("progression_parent_exact_artifact_inventory_mismatch")
    data = {"directory": directory, "report": report, "plan": plan, "rows": rows, "hashes": hashes,
        "inventory": inventory, "delayed": old, "cases": {}, "context_sessions": {}}
    totals, subtotals, unknown = Counter(), Counter(), Counter()
    from . import factor_progression_context as engine
    for position, (row, original) in enumerate(zip(rows, old["rows"]), 1):
        indexed._closed(row, {"context_key", "old_row_sha256", *INHERITED_ROW_FIELDS,
            "status", "error", "elapsed_seconds"}, "saved_progression_context_row")
        print(f"[parent {position}/{len(rows)}] protected complete progression replay {row['context_key'][0]}", flush=True)
        inherited = (*previous.INHERITED_ROW_FIELDS, "delayed_obligations", "delayed_counts")
        if (row["status"] != "progression_contrast_saved_not_selected" or row["error"] is not None
                or row["old_row_sha256"] != digest(original)
                or any(not indexed._same(row[k], original[k]) for k in inherited)):
            raise ValueError("progression_parent_original_context_or_origins_mismatch")
        case = previous.load_case(old, original)
        case_before = digest(case)
        panel = previous.technical_panel(case[-1])
        if not indexed._same(row["technical_panel"], panel):
            raise ValueError("progression_parent_exact_technical_panel_mismatch")
        is_probe_hold = len(panel["selectors"]) < 2
        value = _registered(data, row, "fmpeprobehold_" if is_probe_hold else progression.PREFIX)
        if (not indexed._same(value["resource_limits"], plan["settings"])
                or not indexed._same(value["summary"], row["progression_counts"])):
            raise ValueError("progression_parent_saved_limit_or_counts_mismatch")
        if is_probe_hold:
            if not indexed._same(value, previous._no_panel(case[-1], panel, plan["settings"])):
                raise ValueError("progression_parent_saved_probe_hold_mismatch")
            owned = None
        else:
            # Child preparation performs exact compare_prepared replay under
            # this authentic authority, once per context and not per selector.
            owned = engine.prepare_context_prepared(old["comparison_sessions"][tuple(row["context_key"])], value)
        if case_before != digest(case):
            raise ValueError("progression_context_parent_or_IR_mutated_during_preparation")
        data["context_sessions"][tuple(row["context_key"])] = owned
        data["cases"][tuple(row["context_key"])] = (*case, value)
        cohort._add_denominators(totals, row)
        for name, count in value["summary"].items():
            if type(count) is int:
                subtotals[name] += count
            elif count is None:
                unknown[name] += 1
    expected = {**dict(totals), "progression_integer_subtotals": dict(subtotals),
        "progression_unknown_metric_contexts": dict(unknown), "progression_saved_contexts": len(rows),
        "progression_failed_contexts": 0, **cohort._cohort_counts(plan, totals),
        "context_status_counts": dict(Counter(r["status"] for r in rows))}
    if not indexed._same(report["summary"], expected):
        raise ValueError("progression_parent_summary_or_unexecuted_denominator_mismatch")
    return data


def load_case(data, row):
    return data["cases"][tuple(row["context_key"])]


def _no_panel(record, panel, settings):
    """Runner-only hold; never impersonate a native prepared core record."""
    return frozen._seal({"version": VERSION, "progression_ref": frozen._ref(record),
        "analysis_span": deepcopy(record["analysis_span"]), "logical_universe": deepcopy(record["logical_universe"]),
        "selectors": deepcopy(panel["selectors"]), "contexts": [], "resource_limits": deepcopy(settings),
        "summary": {"planned_hypotheses": len(panel["selectors"]), "computed_hypotheses": 0,
            "computed_boundary_observations": 0, "computed_transition_pairs": 0,
            "planned_boundary_observations": None, "planned_transition_pairs": None,
            **{k: deepcopy(record["summary"][k]) for k in
                ("logical_paths", "logical_path_key_tuples", "logical_function_rows", "unknown_product_groups")}},
        "status": "withheld_parent_runner_probe_has_no_native_comparison_authority",
        "reasons": ["fewer_than_two_registered_complete_hypotheses"],
        "selected": None, "rank": None, "confidence": None, "production_modified": False}, "fmpctxprobehold_")


def run(progression_parent, output, **limits):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("trial_output_must_be_new_direct_workspace_child")
    if set(limits) - set(SETTINGS):
        raise ValueError("unknown_progression_context_trial_limits")
    settings = {**SETTINGS, **limits}
    for name, value in settings.items():
        _limit(value, name)
    from . import factor_progression_context as engine
    data = load_inputs(progression_parent)
    ancestors = _ancestors(data)
    inputs = {p: value for _, ancestor in ancestors for p, value in ancestor["hashes"].items()}
    code = {str(p.resolve()): parent.file_digest(p) for p in parent._code_paths()}
    plan = {"version": VERSION, "progression": str(data["directory"]),
        "parent_report_sha256": parent.file_digest(data["directory"] / "report.json"),
        "inputs": deepcopy(inputs), "code": code, "settings": settings,
        **{k: deepcopy(data["plan"][k]) for k in ("declared_contexts", "declared_units", "selected_contexts", "selection")},
        "cohort_complete": False, "old_selector_or_analysis_reexecuted": False, "all_logical_paths_evaluated": False,
        "source_labels_used_for_inference": False, "old_paths_or_bundles_extended": False, "production_modified": False,
        "conditional_progression_context_stage_enabled": True, "coverage": COVERAGE,
        "parent_panel_policy": previous.PANEL_POLICY, "sample_is_accuracy_evaluation": False}
    output.mkdir()
    artifacts, rows, failures, totals, metric_totals, unknown_metrics = {}, [], [], Counter(), Counter(), Counter()
    storage._save(output, "run-plan.json", plan, artifacts)
    for row in data["rows"]:
        case_started = perf_counter()
        entry = {"context_key": deepcopy(row["context_key"]), "old_row_sha256": digest(row),
            **{k: deepcopy(row[k]) for k in INHERITED_ROW_FIELDS},
            "progression_context": None, "context_counts": None, "status": "not_calculated", "error": None}
        cohort._add_denominators(totals, row)
        print(f"[{len(rows)+1}/{len(data['rows'])}] conditional progression context {row['context_key'][0]}", flush=True)
        case, before = None, None
        try:
            case = load_case(data, row)
            before = digest(case)
            session = data["context_sessions"][tuple(row["context_key"])]
            value = _no_panel(case[-1], row["technical_panel"], settings) if session is None else engine.build_context_prepared(
                session, **settings)
            if session is not None:
                frozen._check(value, engine.PREFIX)
                if value["version"] != engine.VERSION or not indexed._same(value["resource_limits"], settings):
                    raise ValueError("progression_context_native_output_contract_mismatch")
            if before != digest(case):
                raise ValueError("progression_context_trial_parent_or_IR_mutated")
            path = storage._save(output, "progression-contexts/" + value["record_id"] + ".json.gz", value, artifacts, compressed=True)
            entry["progression_context"] = {"artifact": str(path), "sha256": artifacts[str(path)],
                "record_ref": frozen._ref(value), "status": value["status"]}
            entry["context_counts"] = deepcopy(value["summary"])
            for name, count in value["summary"].items():
                if type(count) is int:
                    metric_totals[name] += count
                elif count is None:
                    unknown_metrics[name] += 1
            entry["status"] = "progression_context_saved_not_selected"
        except Exception as exc:
            entry["status"], entry["error"] = "calculation_failure", f"{type(exc).__name__}:{exc}"
            failures.append({"context_key": deepcopy(row["context_key"]), "error": entry["error"]})
        if case is not None and before != digest(case):
            entry["status"], entry["error"] = "calculation_failure", "ValueError:progression_context_trial_parent_or_IR_mutated"
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
        "summary": {**dict(totals), "context_integer_subtotals": dict(metric_totals),
            "context_unknown_metric_contexts": dict(unknown_metrics),
            "context_saved_contexts": sum(r["progression_context"] is not None for r in rows),
            "context_failed_contexts": sum(r["status"] == "calculation_failure" for r in rows),
            **cohort._cohort_counts(plan, totals), "context_status_counts": dict(Counter(r["status"] for r in rows))},
        "cohort_complete": False, "all_logical_paths_evaluated": False, "selected": None,
        **{k: False for k in POLICY_FALSE}, "conditional_progression_context_stage_enabled": True,
        "conditional_NCT_evaluated": False, "boundary_NCT_evaluated": False, "delayed_resolution_confirmed": False,
        "sample_is_accuracy_evaluation": False, "elapsed_seconds": perf_counter() - started,
        "limits": ["The exact saved technical panel is a reproducible implementation probe, not representative music accuracy.",
            "Original partitions, key hypotheses, source facts and one registered all-lane completion remain unchanged.",
            "Applied shape, chromatic coordinates and observed extremes are conditional prerequisites, not Secondary or cadence verdicts.",
            "Arrival, full release and observation-horizon exhaustion are separate coordinates.",
            "Unknown/held axes and every original denominator remain visible; whole budgets produce no favorable prefix.",
            "No selected key, winner, confidence, confirmed harmony/NCT/cadence, training, Gold or production changes."]}
    parent.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("progression-parent", "output"):
        parser.add_argument("--" + name, required=True)
    for name, value in SETTINGS.items():
        parser.add_argument("--" + name.replace("_", "-"), type=int, default=value)
    report = run(**vars(parser.parse_args()))
    print(report["summary"], flush=True)
    return 0 if report["scope_calculation_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
