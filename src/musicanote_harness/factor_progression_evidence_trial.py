"""Append-only technical contrasts of complete original progression hypotheses.

The contrast panel is a reproducible implementation probe, not an accuracy
sample, winner search, or expansion of the frozen segmentation universe.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from . import factor_delayed_obligation_trial as previous
from . import factor_delayed_obligations as delayed_engine
from . import factor_expanded_hypotheses as frozen
from . import factor_indexed_hypotheses as indexed
from . import factor_musical_trial as storage
from . import harmony_frozen_context_lineage_trial as parent
from .musical_pattern_observation import digest

ROOT = parent.ROOT
VERSION = "factor-progression-evidence-trial-0.1.0"
POLICY_FALSE = previous.POLICY_FALSE
DENOMINATORS = previous.DENOMINATORS
SETTINGS = {"max_hypotheses": 64, "max_comparisons": 4096, "query_work_budget": 100000}
INHERITED_ROW_FIELDS = (*previous.INHERITED_ROW_FIELDS, "boundary_explanations", "boundary_counts")
COVERAGE = "explicit_technical_complete_original_partition_contrasts_under_one_registered_completion_not_music_ranking"
PANEL_POLICY = "first_lexical_supported_kernel_else_first_TT_else_first_original_pair_with_all_keys_and_function_shapes_not_accuracy_sample"


def _limit(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("explicit_nonnegative_integer_trial_limit_required:" + name)


def _ancestors(data):
    return [("delayed", data), *previous._ancestors(data["boundary"])]


def _registered(data, row):
    info = row.get("delayed_obligations")
    indexed._closed(info, {"artifact", "sha256", "record_ref", "status"}, "registered_delayed_stage")
    path = Path(info["artifact"]).resolve(strict=True)
    if (path.parent != data["directory"] / "delayed-obligations"
            or data["hashes"].get(str(path)) != info["sha256"]):
        raise ValueError("foreign_or_unregistered_delayed_stage")
    value = parent._load(path, data["hashes"], compressed=True)
    frozen._check(value, delayed_engine.PREFIX)
    if (not indexed._same(frozen._ref(value), info["record_ref"])
            or value["status"] != info["status"] or path.name != value["record_id"] + ".json.gz"):
        raise ValueError("delayed_stage_identity_or_status_mismatch")
    return value


def load_inputs(directory):
    """Replay the exact saved delayed parent and its complete source closure."""
    directory = Path(directory).resolve(strict=True)
    report_path = directory / "report.json"
    report = parent.read(report_path)
    indexed._closed(report, {"version", "scope_calculation_complete", "computation_integrity_passed",
        "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged",
        "changed_inputs_or_code", "changed_artifacts", "failures", "artifact_hashes", "parent_summary",
        "summary", "cohort_complete", "all_logical_paths_evaluated", "selected", *POLICY_FALSE,
        "conditional_delayed_obligation_stage_enabled", "conditional_NCT_evaluated", "boundary_NCT_evaluated",
        "delayed_resolution_confirmed", "elapsed_seconds", "limits"}, "saved_delayed_report")
    if (report.get("version") != previous.VERSION
            or any(report.get(k) is not True for k in ("scope_calculation_complete", "computation_integrity_passed",
                "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged",
                "conditional_delayed_obligation_stage_enabled"))
            or report.get("selected") is not None
            or any(report.get(k) is not False for k in (*POLICY_FALSE, "cohort_complete",
                "all_logical_paths_evaluated", "conditional_NCT_evaluated", "boundary_NCT_evaluated",
                "delayed_resolution_confirmed"))
            or any(report.get(k) != [] for k in ("failures", "changed_inputs_or_code", "changed_artifacts"))):
        raise ValueError("completed_unselected_delayed_parent_required")
    indexed._closed(report["summary"], {*DENOMINATORS, "delayed_integer_subtotals",
        "delayed_unknown_metric_contexts", "delayed_saved_contexts", "delayed_failed_contexts",
        "declared_contexts", "declared_original_raw_lanes", "unexecuted_original_contexts",
        "unexecuted_original_raw_lanes", "context_status_counts"}, "saved_delayed_summary")
    hashes = {}
    parent._guard({str(report_path): parent.file_digest(report_path)}, hashes)
    if type(report["artifact_hashes"]) is not dict or any(
            not Path(p).resolve().is_relative_to(directory) for p in report["artifact_hashes"]):
        raise ValueError("delayed_parent_artifact_outside_registered_directory")
    parent._guard(report["artifact_hashes"], hashes)
    inventory = parent._inventory(directory, hashes)
    plan = parent._load(directory / "run-plan.json", hashes)
    indexed._closed(plan, {"version", "boundary", "parent_report_sha256", "inputs", "code", "settings",
        "declared_contexts", "declared_units", "selected_contexts", "selection", "cohort_complete",
        "old_selector_or_analysis_reexecuted", "all_logical_paths_evaluated", "source_labels_used_for_inference",
        "old_paths_or_bundles_extended", "production_modified", "conditional_delayed_obligation_stage_enabled",
        "conditional_NCT_evaluated", "boundary_NCT_evaluated", "delayed_resolution_confirmed", "coverage"},
        "saved_delayed_plan")
    if (plan.get("version") != previous.VERSION or plan.get("coverage") != previous.COVERAGE
            or plan.get("conditional_delayed_obligation_stage_enabled") is not True
            or any(plan.get(k) is not False for k in ("cohort_complete", "old_selector_or_analysis_reexecuted",
                "all_logical_paths_evaluated", "source_labels_used_for_inference", "old_paths_or_bundles_extended",
                "production_modified", "conditional_NCT_evaluated", "boundary_NCT_evaluated",
                "delayed_resolution_confirmed"))):
        raise ValueError("delayed_parent_plan_policy_mismatch")
    indexed._closed(plan["settings"], set(previous.SETTINGS), "saved_delayed_settings")
    for name, value in plan["settings"].items():
        _limit(value, name)
    if type(plan["inputs"]) is not dict or type(plan["code"]) is not dict:
        raise ValueError("delayed_parent_declared_hash_maps_required")
    parent._guard(plan["inputs"], hashes)
    parent._guard(plan["code"], hashes)
    old = previous.load_inputs(plan["boundary"])
    # Historical producer inventory grows by exactly this parent's two stage
    # modules. New child modules are not retroactively required in old plans.
    expected_code = deepcopy(old["plan"]["code"])
    current_paths = {str(p.resolve()) for p in parent._code_paths()}
    for module in (previous, delayed_engine):
        path = str(Path(module.__file__).resolve())
        if path in current_paths:
            expected_code[path] = parent.file_digest(path)
    if not indexed._same(plan["code"], expected_code):
        raise ValueError("delayed_parent_exact_creation_producer_inventory_mismatch")
    expected_inputs = {p: value for _, ancestor in previous._ancestors(old) for p, value in ancestor["hashes"].items()}
    if not indexed._same(plan["inputs"], expected_inputs):
        raise ValueError("delayed_parent_exact_protected_input_closure_mismatch")
    if (plan["parent_report_sha256"] != parent.file_digest(old["directory"] / "report.json")
            or not indexed._same(report["parent_summary"], old["report"]["summary"])
            or any(not indexed._same(plan[k], old["plan"][k]) for k in
                ("declared_contexts", "declared_units", "selected_contexts", "selection"))):
        raise ValueError("delayed_parent_declared_lineage_or_summary_mismatch")
    rows = parent._load(directory / "context-index.json", hashes)
    if (type(rows) is not list or not indexed._same([r["context_key"] for r in rows], plan["selected_contexts"])
            or len({tuple(r["context_key"]) for r in rows}) != len(rows)
            or len(rows) != report["summary"]["contexts"]):
        raise ValueError("delayed_parent_context_denominator_mismatch")
    artifacts = {str(directory / name) for name in ("run-plan.json", "context-index.json")}
    artifacts.update(str(Path(row["delayed_obligations"]["artifact"]).resolve(strict=True)) for row in rows)
    if set(report["artifact_hashes"]) != artifacts:
        raise ValueError("delayed_parent_exact_artifact_inventory_mismatch")
    data = {"directory": directory, "report": report, "plan": plan, "rows": rows, "hashes": hashes,
        "inventory": inventory, "boundary": old, "cases": {}, "comparison_sessions": {}}
    totals, subtotals, unknown = Counter(), Counter(), Counter()
    from . import factor_progression_evidence as engine
    for position, (row, original) in enumerate(zip(rows, old["rows"]), 1):
        indexed._closed(row, {"context_key", "old_row_sha256", *INHERITED_ROW_FIELDS,
            "delayed_obligations", "delayed_counts", "status", "error", "elapsed_seconds"}, "saved_delayed_context_row")
        print(f"[parent {position}/{len(rows)}] protected delayed source replay {row['context_key'][0]}", flush=True)
        if (row["status"] != "delayed_obligation_templates_saved_not_selected" or row["error"] is not None
                or row["old_row_sha256"] != digest(original)
                or any(not indexed._same(row[k], original[k]) for k in INHERITED_ROW_FIELDS)):
            raise ValueError("delayed_parent_original_context_or_origins_mismatch")
        case = previous.load_case(old, original)
        value = _registered(data, row)
        if (not indexed._same(value["resource_limits"], plan["settings"])
                or not indexed._same(row["delayed_counts"], value["summary"])):
            raise ValueError("delayed_parent_saved_limit_or_counts_mismatch")
        owned = delayed_engine.prepare_obligations_prepared(old["delayed_sessions"][tuple(row["context_key"])], value)
        data["comparison_sessions"][tuple(row["context_key"])] = engine.prepare_comparison_prepared(owned)
        data["cases"][tuple(row["context_key"])] = (*case, value)
        previous.previous.previous._add_denominators(totals, row)
        for name, count in value["summary"].items():
            if type(count) is int:
                subtotals[name] += count
            elif count is None:
                unknown[name] += 1
    expected = {**dict(totals), "delayed_integer_subtotals": dict(subtotals),
        "delayed_unknown_metric_contexts": dict(unknown), "delayed_saved_contexts": len(rows),
        "delayed_failed_contexts": 0, **previous.previous.previous._cohort_counts(plan, totals),
        "context_status_counts": dict(Counter(r["status"] for r in rows))}
    if not indexed._same(report["summary"], expected):
        raise ValueError("delayed_parent_summary_or_unexecuted_denominator_mismatch")
    return data


def load_case(data, row):
    return data["cases"][tuple(row["context_key"])]


def technical_panel(record):
    """Declared probes of implementation axes; not top-k or musical ranking."""
    kernels = sorted(record["obligation_kernel_inventory"], key=lambda k: k["record_id"])
    plans = {p["record_id"]: p for p in record["joint_plan_inventory"]}
    supported = [(k, b) for k in kernels if k["status"] == "conditional" and k["joint_plan_ref"] is not None
        for b in sorted(plans[k["joint_plan_ref"]["record_id"]]["branches"],
                        key=lambda b: indexed._encoded(b)) if b["status"] == "possible"]
    seed = supported[0][0] if supported else kernels[0] if kernels else None
    bundles = record["inherited_bundle_inventory"] + record["bundle_inventory"]
    control = next((b["record_id"] for b in sorted(bundles, key=lambda b: b["record_id"]) if not b["required_links"]), None)
    bundle_id = supported[0][1]["bundle_ref"]["record_id"] if supported else control
    groups = {g["group_id"]: g for g in record["path_groups"]}
    ordered_groups = sorted(record["path_groups"], key=lambda g: g["group_id"])
    pair = groups[seed["group_id"]] if seed is not None else next((g for g in ordered_groups
        if len(g["slots"]) == 2 and all(s["variant_ids"] for s in g["slots"])), None)
    ids = None if pair is None else [seed["source_variant_ids"][0], seed["target_variant_ids"][0]] if seed else [s["variant_ids"][0] for s in pair["slots"]]
    selectors = []
    family, quality = (seed["family"], seed["quality"]) if seed else ("V7", "M")
    def add(group, variant_ids, key, family=None, quality=None):
        selectors.append({"group_id": group["group_id"], "variant_ids": list(variant_ids), "key_id": key["record_id"],
            "transition": None if len(variant_ids) == 1 else {"family": family, "quality": quality,
                "strategy": "ordinary_role_existential", "declared_occurrences": None, "requested_explanations": None}})
    if pair is not None:
        for key in record["keys"]:
            for actual_family in frozen.FAMILIES:
                for actual_quality in ("M", "m"):
                    add(pair, ids, key, actual_family, actual_quality)
    full = next((g for g in ordered_groups if len(g["slots"]) == 1 and g["slots"][0]["variant_ids"]), None)
    if full is not None:
        for key in record["keys"]:
            add(full, [full["slots"][0]["variant_ids"][0]], key)
    origins = {o["variant_id"]: o for o in record["origin_inventory"]}
    alternate = None
    if pair is not None:
        original_profile = origins.get(ids[1], {}).get("profile_ref")
        alternate = next((v for v in pair["slots"][1]["variant_ids"] if v != ids[1]
            and origins.get(v, {}).get("profile_ref") != original_profile), None)
        if alternate is not None:
            for key in record["keys"]:
                add(pair, [ids[0], alternate], key, family, quality)
    unique = []; seen = set()
    for row in selectors:
        signature = digest(row)
        if signature not in seen:
            seen.add(signature); unique.append(row)
    return {"selectors": unique, "bundle_id": bundle_id, "selection_policy": PANEL_POLICY,
        "seed_kernel_ref": None if seed is None else frozen._ref(seed),
        "seed_supported_in_saved_phase19": bool(supported), "alternate_target_variant_id": alternate,
        "comparison_scope": "same_scope_complete_original_partitions",
        "sampling_is_accuracy_evidence": False, "winning_hypothesis_selected": False}


def _no_panel(record, panel, settings):
    return frozen._seal({"version": VERSION, "obligations_ref": frozen._ref(record),
        "analysis_span": deepcopy(record["analysis_span"]), "logical_universe": deepcopy(record["logical_universe"]),
        "selectors": deepcopy(panel["selectors"]), "hypotheses": [], "contrasts": [],
        "resource_limits": deepcopy(settings), "summary": {"planned_hypotheses": len(panel["selectors"]),
            "computed_hypotheses": 0, "computed_comparisons": 0, "tested_logical_path_key_tuples": 0,
            **{k: deepcopy(record["summary"][k]) for k in ("logical_paths", "logical_path_key_tuples", "logical_function_rows", "unknown_product_groups")}},
        "status": "withheld_no_complete_technical_contrast_panel", "reasons": ["fewer_than_two_registered_complete_hypotheses"],
        "selected": None, "rank": None, "confidence": None, "production_modified": False}, "fmpeprobehold_")


def run(delayed, output, **limits):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("trial_output_must_be_new_direct_workspace_child")
    if set(limits) - set(SETTINGS):
        raise ValueError("unknown_progression_comparison_trial_limits")
    settings = {**SETTINGS, **limits}
    for name, value in settings.items():
        _limit(value, name)
    from . import factor_progression_evidence as engine
    data = load_inputs(delayed)
    ancestors = _ancestors(data)
    inputs = {p: value for _, ancestor in ancestors for p, value in ancestor["hashes"].items()}
    code = {str(p.resolve()): parent.file_digest(p) for p in parent._code_paths()}
    plan = {"version": VERSION, "delayed": str(data["directory"]),
        "parent_report_sha256": parent.file_digest(data["directory"] / "report.json"),
        "inputs": deepcopy(inputs), "code": code, "settings": settings,
        **{k: deepcopy(data["plan"][k]) for k in ("declared_contexts", "declared_units", "selected_contexts", "selection")},
        "cohort_complete": False, "old_selector_or_analysis_reexecuted": False, "all_logical_paths_evaluated": False,
        "source_labels_used_for_inference": False, "old_paths_or_bundles_extended": False, "production_modified": False,
        "conditional_progression_comparison_stage_enabled": True, "coverage": COVERAGE, "panel_policy": PANEL_POLICY,
        "sample_is_accuracy_evaluation": False}
    output.mkdir()
    artifacts, rows, failures, totals, metric_totals, unknown_metrics = {}, [], [], Counter(), Counter(), Counter()
    storage._save(output, "run-plan.json", plan, artifacts)
    for row in data["rows"]:
        case_started = perf_counter()
        entry = {"context_key": deepcopy(row["context_key"]), "old_row_sha256": digest(row),
            **{k: deepcopy(row[k]) for k in (*INHERITED_ROW_FIELDS, "delayed_obligations", "delayed_counts")},
            "progression_comparison": None, "progression_counts": None, "technical_panel": None,
            "status": "not_calculated", "error": None}
        previous.previous.previous._add_denominators(totals, row)
        print(f"[{len(rows)+1}/{len(data['rows'])}] complete progression contrast {row['context_key'][0]}", flush=True)
        owned, before = None, None
        try:
            owned = load_case(data, row)
            before = digest(owned)
            panel = technical_panel(owned[-1])
            entry["technical_panel"] = deepcopy(panel)
            value = _no_panel(owned[-1], panel, settings) if len(panel["selectors"]) < 2 else engine.compare_prepared(
                data["comparison_sessions"][tuple(row["context_key"])], panel["selectors"], panel["bundle_id"], **settings)
            if before != digest(owned):
                raise ValueError("progression_trial_parent_or_IR_mutated")
            path = storage._save(output, "progression-comparisons/" + value["record_id"] + ".json.gz", value, artifacts, compressed=True)
            entry["progression_comparison"] = {"artifact": str(path), "sha256": artifacts[str(path)],
                "record_ref": frozen._ref(value), "status": value["status"]}
            entry["progression_counts"] = deepcopy(value["summary"])
            for name, count in value["summary"].items():
                if type(count) is int:
                    metric_totals[name] += count
                elif count is None:
                    unknown_metrics[name] += 1
            entry["status"] = "progression_contrast_saved_not_selected"
        except Exception as exc:
            entry["status"], entry["error"] = "calculation_failure", f"{type(exc).__name__}:{exc}"
            failures.append({"context_key": deepcopy(row["context_key"]), "error": entry["error"]})
        if owned is not None and before != digest(owned):
            entry["status"], entry["error"] = "calculation_failure", "ValueError:progression_trial_parent_or_IR_mutated"
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
        "summary": {**dict(totals), "progression_integer_subtotals": dict(metric_totals),
            "progression_unknown_metric_contexts": dict(unknown_metrics),
            "progression_saved_contexts": sum(r["progression_comparison"] is not None for r in rows),
            "progression_failed_contexts": sum(r["status"] == "calculation_failure" for r in rows),
            **previous.previous.previous._cohort_counts(plan, totals),
            "context_status_counts": dict(Counter(r["status"] for r in rows))},
        "cohort_complete": False, "all_logical_paths_evaluated": False, "selected": None,
        **{k: False for k in POLICY_FALSE}, "conditional_progression_comparison_stage_enabled": True,
        "conditional_NCT_evaluated": False, "boundary_NCT_evaluated": False, "delayed_resolution_confirmed": False,
        "sample_is_accuracy_evaluation": False, "elapsed_seconds": perf_counter() - started,
        "limits": ["Technical selector panels are declared implementation probes, not representative music accuracy samples.",
            "Full hold and original one-cut complete partitions share one authentic all-raw-lane completion.",
            "Raw note time is conserved; competing function assumptions never pool explanation credits.",
            "Unselected hypotheses, keys, terminal function shapes and unknown/held axes remain visible.",
            "Whole-request budgets produce no favorable prefix; quota is not a CPU/RSS bound.",
            "No winner, confidence, final harmony/key/NCT/cadence, training, Gold or production changes."]}
    parent.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("delayed", "output"):
        parser.add_argument("--" + name, required=True)
    for name, value in SETTINGS.items():
        parser.add_argument("--" + name.replace("_", "-"), type=int, default=value)
    report = run(**vars(parser.parse_args()))
    print(report["summary"], flush=True)
    return 0 if report["scope_calculation_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
