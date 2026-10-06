"""Append-only native all-interval probe over registered phase-21 contexts.

The saved metadata is a hash-protected selection/creation boundary, NOT an
issued phase-21 authority. Only the genuine registered full IR is supplied to
the new native engine, which freshly checks the expanded source/geometry scope.
No previous.load_inputs call or absent original-parent replay is claimed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import re
from pathlib import Path
from time import perf_counter

from . import factor_interval_lattice as engine
from . import factor_progression_context_trial as previous
from . import factor_progression_context as old_engine
from . import factor_expanded_scope as expanded
from . import factor_expanded_hypotheses as frozen
from . import factor_indexed_hypotheses as indexed
from . import factor_temporal_explanation_trial as cohort
from . import factor_musical_trial as storage
from . import harmony_frozen_context_lineage_trial as parent
from .musical_pattern_observation import digest, f, q, span_bounds

ROOT = parent.ROOT
VERSION = "factor-interval-lattice-trial-0.1.0"
SETTINGS = {**engine.DEFAULTS, "max_hypotheses": 64, "max_slots": 64,
            "query_work_budget": 200000, "geometry_work_budget": 100000,
            "max_greedy_links": 20}
PANEL_POLICY = "observed_nearest_half_thirds_first_native_origin_id_all_explicit_keys_None_vs_V7_M"
AUTHORITY = "registered_metadata_and_full_IR_scope_replay_not_original_parent_file_authority"
POLICY_FALSE = (*previous.POLICY_FALSE, "cohort_complete", "all_logical_paths_evaluated",
                "conditional_NCT_evaluated", "boundary_NCT_evaluated",
                "delayed_resolution_confirmed", "sample_is_accuracy_evaluation",
                "original_parent_file_authority_replayed", "phase21_owned_session_reused",
                "source_projection_synthesized_as_IR", "UI_or_production_connected",
                "general_transition_assumption_universe_evaluated")
PARENT_REPORT_KEYS = {"version", "scope_calculation_complete", "computation_integrity_passed",
    "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged",
    "changed_inputs_or_code", "changed_artifacts", "failures", "artifact_hashes", "parent_summary",
    "summary", "cohort_complete", "all_logical_paths_evaluated", "selected", *previous.POLICY_FALSE,
    "conditional_progression_context_stage_enabled", "conditional_NCT_evaluated", "boundary_NCT_evaluated",
    "delayed_resolution_confirmed", "sample_is_accuracy_evaluation", "elapsed_seconds", "limits"}
PARENT_PLAN_KEYS = {"version", "progression", "parent_report_sha256", "inputs", "code", "settings",
    "declared_contexts", "declared_units", "selected_contexts", "selection", "cohort_complete",
    "old_selector_or_analysis_reexecuted", "all_logical_paths_evaluated", "source_labels_used_for_inference",
    "old_paths_or_bundles_extended", "production_modified", "conditional_progression_context_stage_enabled",
    "coverage", "parent_panel_policy", "sample_is_accuracy_evaluation"}
PARENT_ROW_KEYS = {"context_key", "old_row_sha256", *previous.INHERITED_ROW_FIELDS,
                   "progression_context", "context_counts", "status", "error", "elapsed_seconds"}
PARENT_SUMMARY_KEYS = {*previous.DENOMINATORS, "context_integer_subtotals", "context_unknown_metric_contexts",
    "context_saved_contexts", "context_failed_contexts", "declared_contexts", "declared_original_raw_lanes",
    "unexecuted_original_contexts", "unexecuted_original_raw_lanes", "context_status_counts"}


def _limit(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("explicit_nonnegative_integer_lattice_trial_limit_required:" + name)


def _hash_map(value, name):
    if type(value) is not dict or any(type(p) is not str or type(h) is not str
            or not Path(p).is_absolute()
            or re.fullmatch(r"[0-9a-f]{64}", h) is None for p, h in value.items()):
        raise ValueError("registered_absolute_path_SHA256_map_required:" + name)


def _context_key(value):
    if (type(value) is not list or len(value) != 3 or type(value[0]) is not str
            or type(value[1]) is not int or value[1] < 0 or type(value[2]) is not str):
        raise ValueError("closed_original_context_key_required")
    return tuple(value)


def _code_paths():
    # Protect this creation inventory, including the two new test contracts.
    # Historical inventories are protected as recorded, not retrospectively
    # required to contain these additive native child files.
    extra = [ROOT / "tests/test_factor_interval_lattice.py",
             ROOT / "tests/test_factor_interval_lattice_trial.py"]
    return sorted({*parent._code_paths(), *(p for p in extra if p.is_file())})


def _registered(data, info, prefix, *, own_subdirectory=None):
    indexed._closed(info, {"artifact", "sha256", "record_ref", "status"}, "registered_lattice_trial_input")
    _hash_map({info["artifact"]: info["sha256"]}, "registered_stage")
    path = Path(info["artifact"]).resolve(strict=True)
    if (str(path) != info["artifact"] or data["hashes"].get(str(path)) != info["sha256"]
            or (own_subdirectory is not None and path.parent != data["directory"] / own_subdirectory)):
        raise ValueError("foreign_or_unregistered_lattice_trial_stage")
    value = parent._load(path, data["hashes"], compressed=True)
    frozen._check(value, prefix)
    if (not indexed._same(frozen._ref(value), info["record_ref"])
            or value["status"] != info["status"] or path.name != value["record_id"] + ".json.gz"):
        raise ValueError("registered_stage_identity_status_or_filename_mismatch")
    return value


def load_inputs(directory):
    """Read registered metadata/hashes only; deliberately no old producer call."""
    directory = Path(directory).resolve(strict=True)
    report_path = directory / "report.json"
    report = parent.read(report_path)
    indexed._closed(report, PARENT_REPORT_KEYS, "saved_phase21_metadata_report")
    if (report["version"] != previous.VERSION
            or any(report[k] is not True for k in ("scope_calculation_complete", "computation_integrity_passed",
                "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged",
                "conditional_progression_context_stage_enabled"))
            or report["selected"] is not None
            or any(report[k] is not False for k in (*previous.POLICY_FALSE, "cohort_complete",
                "all_logical_paths_evaluated", "conditional_NCT_evaluated", "boundary_NCT_evaluated",
                "delayed_resolution_confirmed", "sample_is_accuracy_evaluation"))
            or any(report[k] != [] for k in ("failures", "changed_inputs_or_code", "changed_artifacts"))):
        raise ValueError("completed_unselected_phase21_metadata_required")
    indexed._closed(report["summary"], PARENT_SUMMARY_KEYS, "saved_phase21_metadata_summary")
    for name in PARENT_SUMMARY_KEYS - {"context_integer_subtotals", "context_unknown_metric_contexts", "context_status_counts"}:
        _limit(report["summary"][name], name)
    for name in ("context_integer_subtotals", "context_unknown_metric_contexts", "context_status_counts"):
        if type(report["summary"][name]) is not dict:
            raise ValueError("closed_phase21_count_map_required")
        for count in report["summary"][name].values():
            _limit(count, name)
    hashes = {str(report_path): parent.file_digest(report_path)}
    _hash_map(report["artifact_hashes"], "phase21_artifacts")
    if any(not Path(p).resolve().is_relative_to(directory) or Path(p).resolve() == report_path
           for p in report["artifact_hashes"]):
        raise ValueError("phase21_artifact_outside_registered_directory")
    parent._guard(report["artifact_hashes"], hashes)
    inventory = parent._inventory(directory, hashes)
    plan = parent._load(directory / "run-plan.json", hashes)
    indexed._closed(plan, PARENT_PLAN_KEYS, "saved_phase21_metadata_plan")
    if (plan["version"] != previous.VERSION or plan["coverage"] != previous.COVERAGE
            or plan["parent_panel_policy"] != previous.previous.PANEL_POLICY
            or plan["conditional_progression_context_stage_enabled"] is not True
            or any(plan[k] is not False for k in ("cohort_complete", "old_selector_or_analysis_reexecuted",
                "all_logical_paths_evaluated", "source_labels_used_for_inference", "old_paths_or_bundles_extended",
                "production_modified", "sample_is_accuracy_evaluation"))):
        raise ValueError("phase21_metadata_plan_policy_mismatch")
    indexed._closed(plan["settings"], set(previous.SETTINGS), "saved_phase21_settings")
    for name, value in plan["settings"].items():
        _limit(value, name)
    for name in ("inputs", "code"):
        _hash_map(plan[name], name)
        parent._guard(plan[name], hashes)
    producer_paths = {str(Path(m.__file__).resolve()) for m in (previous, old_engine)}
    if not producer_paths <= set(plan["code"]):
        raise ValueError("phase21_historical_creation_producer_not_registered")
    predecessor = Path(plan["progression"]).resolve(strict=True)
    predecessor_report = parent._load(predecessor / "report.json", hashes)
    predecessor_plan = parent._load(predecessor / "run-plan.json", hashes)
    expected_inputs = {**predecessor_plan["inputs"], **predecessor_plan["code"],
                       **predecessor_report["artifact_hashes"],
                       str(predecessor / "report.json"): hashes[str(predecessor / "report.json")]}
    expected_code = {**predecessor_plan["code"], **{p: plan["code"][p] for p in producer_paths}}
    if (plan["inputs"] != expected_inputs or plan["code"] != expected_code
            or plan["parent_report_sha256"] != hashes[str(predecessor / "report.json")]
            or report["parent_summary"] != predecessor_report["summary"]):
        raise ValueError("phase21_registered_creation_hash_closure_or_summary_mismatch")
    for name in ("declared_contexts", "selected_contexts"):
        if type(plan[name]) is not list or len({_context_key(v) for v in plan[name]}) != len(plan[name]):
            raise ValueError("unique_declared_context_inventory_required")
    if (not {_context_key(v) for v in plan["selected_contexts"]}
            <= {_context_key(v) for v in plan["declared_contexts"]}
            or type(plan["declared_units"]) is not list or type(plan["selection"]) is not dict):
        raise ValueError("phase21_selected_contexts_outside_declared_cohort")
    units = set()
    for unit in plan["declared_units"]:
        indexed._closed(unit, {"context_key", "lane"}, "declared_original_raw_lane_unit")
        key = _context_key(unit["context_key"])
        lane = unit["lane"]
        if (key not in {_context_key(v) for v in plan["declared_contexts"]}
                or type(lane) is not list or len(lane) != 2 or any(type(v) is not str for v in lane)
                or (key, tuple(lane)) in units):
            raise ValueError("unique_declared_original_raw_lane_unit_required")
        units.add((key, tuple(lane)))
    rows = parent._load(directory / "context-index.json", hashes)
    if (type(rows) is not list or any(type(r) is not dict for r in rows)
            or [r.get("context_key") for r in rows] != plan["selected_contexts"]):
        raise ValueError("phase21_exact_selected_context_row_inventory_required")
    data = {"directory": directory, "report": report, "plan": plan, "rows": rows,
            "hashes": hashes, "inventory": inventory}
    totals, integer_counts, unknown_counts = Counter(), Counter(), Counter()
    own_artifacts = {str(directory / n) for n in ("run-plan.json", "context-index.json")}
    for row in rows:
        indexed._closed(row, PARENT_ROW_KEYS, "saved_phase21_context_metadata_row")
        key = _context_key(row["context_key"])
        if row["status"] != "progression_context_saved_not_selected" or row["error"] is not None:
            raise ValueError("completed_phase21_context_metadata_row_required")
        if type(row["old_lane_refs"]) is not list:
            raise ValueError("selected_original_raw_lane_denominator_mismatch")
        lanes = []
        for lane_ref in row["old_lane_refs"]:
            indexed._closed(lane_ref, {"lane", "old_status", "old_graph_ref"}, "saved_original_raw_lane_reference")
            lane = lane_ref["lane"]
            if type(lane) is not list or len(lane) != 2 or any(type(v) is not str for v in lane):
                raise ValueError("original_two_string_raw_lane_reference_required")
            lanes.append(tuple(lane))
        if set(lanes) != {lane for k, lane in units if k == key} or len(lanes) != len(set(lanes)):
            raise ValueError("selected_original_raw_lane_denominator_mismatch")
        for name in ("groups", "logical_paths", "logical_path_key_tuples", "logical_function_shapes",
                     "unknown_product_groups", "indexed_variants", "shared_profile_descriptors"):
            _limit(row["index_counts"][name], name)
        value = _registered(data, row["progression_context"], old_engine.PREFIX,
                            own_subdirectory="progression-contexts")
        own_artifacts.add(str(Path(row["progression_context"]["artifact"]).resolve()))
        if (value["version"] != old_engine.VERSION or value["selected"] is not None
                or value["flags"] != old_engine._flags()
                or not indexed._same(value["resource_limits"], plan["settings"])
                or not indexed._same(value["summary"], row["context_counts"])):
            raise ValueError("phase21_registered_context_metadata_counts_mismatch")
        scope_info = row["expanded_scope"]
        if type(scope_info) is not dict or scope_info.get("artifact") not in plan["inputs"]:
            raise ValueError("expanded_scope_not_registered_in_phase21_inputs")
        scope = _registered(data, scope_info, expanded.PREFIX)
        if (frozen._ref(scope) != value["scope_ref"]
                or scope["analysis_span"] != value["analysis_span"]):
            raise ValueError("phase21_context_scope_metadata_pointer_mismatch")
        cohort._add_denominators(totals, row)
        for name, count in value["summary"].items():
            if type(count) is int:
                integer_counts[name] += count
            elif count is None:
                unknown_counts[name] += 1
    expected = {**dict(totals), "context_integer_subtotals": dict(integer_counts),
        "context_unknown_metric_contexts": dict(unknown_counts), "context_saved_contexts": len(rows),
        "context_failed_contexts": 0, **cohort._cohort_counts(plan, totals),
        "context_status_counts": dict(Counter(r["status"] for r in rows))}
    if (report["summary"] != expected or set(report["artifact_hashes"]) != own_artifacts):
        raise ValueError("phase21_metadata_denominators_or_exact_artifact_inventory_mismatch")
    return data


def load_case(data, row):
    """Find the genuine full registered IR by exact binding, never by title."""
    scope = _registered(data, row["expanded_scope"], expanded.PREFIX)
    binding = scope["binding"]
    source_stems = {Path(s["original_name"]).stem for s in binding["source_files"]}
    candidates = [Path(p) for p in data["plan"]["inputs"]
                  if Path(p).suffix == ".json" and Path(p).name.endswith("_ir.json")]
    candidates.sort(key=lambda p: (p.parent.name not in source_stems, str(p)))
    for path in candidates:
        ir = parent._load(path, data["hashes"])
        if (type(ir) is not dict or ir.get("ir_document_id") != binding["ir_document_id"]
                or type(ir.get("score")) is not dict or ir["score"].get("score_id") != binding["score_id"]
                or ir["score"].get("source_file_id") != binding["source_file_id"]):
            continue
        if expanded._binding(ir) == binding:
            return ir, scope, {"artifact": str(path), "sha256": data["hashes"][str(path)],
                "ir_document_id": ir["ir_document_id"], "ir_content_sha256": binding["ir_content_sha256"],
                "binding_match": True, "registered_full_IR_not_projection": True}
    raise ValueError("exact_registered_full_IR_binding_not_found_no_synthesis")


def technical_panel(lattice):
    """Label-blind technical probes, not harmonic candidate recommendations."""
    points = [f(v) for v in lattice["coordinate_times"]]
    if len(points) < 2 or points != sorted(set(points)):
        raise ValueError("strict_positive_native_observed_coordinate_inventory_required")
    interiors = list(range(1, len(points) - 1))
    a, b = points[0], points[-1]

    def nearest(ratio):
        return min(interiors, key=lambda i: (abs(points[i] - (a + (b - a) * ratio)), points[i])) if interiors else None

    half, thirds = nearest(Fraction(1, 2)), [nearest(Fraction(1, 3)), nearest(Fraction(2, 3))]
    specs = [("whole_hold", [0, len(points) - 1], 1),
             ("nearest_half_two_slots", None if half is None else [0, half, len(points) - 1], 2),
             ("nearest_thirds_three_slots", None if None in thirds or thirds[0] >= thirds[1]
              else [0, *thirds, len(points) - 1], 2)]
    entries = {tuple(e["point_indices"]): e for e in lattice["catalog_inventory"]}
    keys = sorted(lattice["keys"], key=lambda k: k["record_id"])
    if len({k["record_id"] for k in keys}) != len(keys):
        raise ValueError("duplicate_native_panel_explicit_key")
    selectors, rows = [], []
    for name, indices, mode_count in specs:
        reasons, origins = [], []
        if indices is None:
            reasons.append("observed_quantile_cuts_not_distinct_positive_partition")
        elif lattice["status"] != "ready_native_interval_lattice":
            reasons.append("whole_native_lattice_held_no_prefix_panel")
        else:
            for pair in zip(indices, indices[1:]):
                entry = entries.get(pair)
                available = [] if entry is None else sorted(entry["origins"], key=lambda o: o["record_id"])
                if not available:
                    reasons.append("requested_positive_interval_native_origin_unavailable")
                else:
                    origins.append(available[0]["record_id"])
        planned = len(keys) * mode_count
        selections = []
        if not reasons:
            for key in keys:
                modes = [None] if mode_count == 1 else [None, {"family": "V7", "quality": "M"}]
                for assumption in modes:
                    selections.append({"origin_ids": deepcopy(origins), "key_id": key["record_id"],
                        "transition_assumptions": [deepcopy(assumption) for _ in range(len(origins) - 1)]})
            selectors.extend(selections)
        rows.append({"partition_kind": name, "point_indices": indices,
            "partition": None if indices is None else [frozen._span(points[i], points[j]) for i, j in zip(indices, indices[1:])],
            "native_origin_ids": origins if not reasons else None, "planned_selectors": planned,
            "available_selectors": len(selections), "status": "available_technical_probe" if not reasons else "whole_requested_partition_withheld",
            "reasons": sorted(set(reasons))})
    return {"selection_policy": PANEL_POLICY, "rows": rows, "selectors": selectors,
        "planned_selectors": sum(r["planned_selectors"] for r in rows),
        "available_selectors": len(selectors), "explicit_key_count": len(keys),
        "origin_choice": "first_native_record_id_not_highest_membership_or_source_label",
        "nearest_tie_break": "earlier_exact_observed_coordinate", "source_annotation_labels_used": False,
        "accuracy_or_general_transition_sample": False, "winning_hypothesis_selected": False}


def greedy_links(scope, maximum):
    """One bounded admissible endpoint matching, not a voice-leading winner."""
    _limit(maximum, "max_greedy_links")
    if maximum > 20:
        raise ValueError("at_most_twenty_greedy_probe_links")
    candidates = []
    for graph in scope["graphs"]:
        for factor in graph["factors"]:
            for a in sorted(factor["source_refs"]):
                for b in sorted(factor["target_refs"]):
                    candidates.append((tuple(graph["lane"]), f(factor["time"]), a, b))
    result, outgoing, incoming = [], set(), set()
    for _, _, a, b in sorted(candidates):
        if len(result) == maximum:
            break
        if a not in outgoing and b not in incoming:
            result.append([a, b])
            outgoing.add(a)
            incoming.add(b)
    return result


def _counts(lattice, panel, bundles, comparisons, requested_bundles):
    universe = lattice["universe"]
    paths = [p for c in comparisons for p in c["paths"]]
    return {"observed_cut_coordinates": len(lattice["coordinate_times"]) - 2,
        "planned_interval_catalogs": lattice["planned_catalogs"], "stored_interval_catalogs": len(lattice["catalog_inventory"]),
        "native_origin_variants": lattice["origin_count"], "materialized_origins": lattice["materialized_origins"],
        **{k: deepcopy(universe[k]) for k in ("partition_skeletons", "known_path_subtotal", "unknown_nonzero_skeletons",
            "logical_paths", "logical_path_keys", "slot_occurrences", "internal_transition_occurrences",
            "internal_function_shape_rows", "terminal_inclusive_function_shape_rows", "key_hypotheses")},
        "requested_bundles": requested_bundles, "registered_bundles": len(bundles),
        "complete_all_lane_bundles": sum(b["status"] == "complete_all_lane_witness" for b in bundles),
        "withheld_all_lane_bundles": sum(b["status"] != "complete_all_lane_witness" for b in bundles),
        "planned_panel_selector_occurrences": panel["planned_selectors"] * requested_bundles,
        "available_panel_selectors_per_bundle": panel["available_selectors"],
        "submitted_panel_selector_occurrences": sum(c["summary"]["planned_selectors"] for c in comparisons),
        "computed_selector_occurrences": len(paths),
        "computed_distinct_origin_path_keys": len({digest([p["origin_refs"], p["key_ref"]]) for p in paths}),
        "computed_internal_transitions": sum(c["summary"]["computed_internal_transitions"] for c in comparisons),
        "computed_boundary_occurrences": sum(len(p["boundaries"]) for p in paths),
        "whole_comparison_holds": sum(c["status"] == "whole_comparison_hold" for c in comparisons),
        "raw_time_conserved_paths": sum(p["whole_path_account"]["raw_time_conserved"] is True for p in paths)}


def _saved(output, folder, value, artifacts):
    path = storage._save(output, folder + "/" + value["record_id"] + ".json.gz", value, artifacts, compressed=True)
    return {"artifact": str(path), "sha256": artifacts[str(path)],
            "record_ref": frozen._ref(value), "status": value["status"]}


def run(context_parent, output, *, include_greedy_bundle=True, **limits):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("trial_output_must_be_new_direct_workspace_child")
    if set(limits) - set(SETTINGS) or type(include_greedy_bundle) is not bool:
        raise ValueError("closed_native_lattice_trial_settings_required")
    settings = {**SETTINGS, **limits}
    for name, value in settings.items():
        _limit(value, name)
    if settings["max_hypotheses"] > 64 or settings["max_greedy_links"] > 20:
        raise ValueError("bounded_64_selector_20_greedy_link_probe_required")
    data = load_inputs(context_parent)
    inputs = deepcopy(data["hashes"])
    code = {str(p.resolve()): parent.file_digest(p) for p in _code_paths()}
    plan = {"version": VERSION, "context_parent": str(data["directory"]),
        "parent_report_sha256": inputs[str(data["directory"] / "report.json")],
        "inputs": inputs, "code": code, "settings": settings, "include_greedy_bundle": include_greedy_bundle,
        **{k: deepcopy(data["plan"][k]) for k in ("declared_contexts", "declared_units", "selected_contexts", "selection")},
        "panel_policy": PANEL_POLICY, "source_authority": AUTHORITY,
        "source_scope_geometry_freshly_checked_by_native_engine": True,
        "fresh_native_interval_suppliers_enabled": True, "original_parent_artifacts_registered_not_replayed": True,
        "old_selector_or_analysis_reexecuted": False, "old_paths_or_bundles_extended": False,
        "source_labels_used_for_inference": False, "production_modified": False,
        "cohort_complete": False, "sample_is_accuracy_evaluation": False,
        "all_logical_paths_evaluated": False, "general_transition_assumption_universe_evaluated": False}
    output.mkdir()
    artifacts, rows, failures, totals, metric_totals, unknown_metrics = {}, [], [], Counter(), Counter(), Counter()
    storage._save(output, "run-plan.json", plan, artifacts)
    for row in data["rows"]:
        case_started = perf_counter()
        entry = {"context_key": deepcopy(row["context_key"]), "registered_parent_row_sha256": digest(row),
            "registered_parent_metadata": deepcopy(row), "full_IR": None, "native_lattice": None,
            "technical_panel": None, "bundle_comparisons": [], "native_counts": None,
            "status": "not_calculated", "error": None}
        cohort._add_denominators(totals, row)
        case, before = None, None
        print(f"[{len(rows)+1}/{len(data['rows'])}] fresh native interval lattice {row['context_key'][0]}", flush=True)
        try:
            ir, scope, ir_info = load_case(data, row)
            case = (ir, scope)
            before = digest(case)
            session = engine.prepare_lattice(ir, scope, **{k: settings[k] for k in engine.DEFAULTS})
            lattice = engine.lattice_prepared(session)
            frozen._check(lattice, engine.PREFIX)
            if lattice["version"] != engine.VERSION or lattice["resource_limits"] != {k: settings[k] for k in engine.DEFAULTS}:
                raise ValueError("native_lattice_output_contract_mismatch")
            entry["full_IR"], entry["native_lattice"] = ir_info, _saved(output, "lattices", lattice, artifacts)
            panel = technical_panel(lattice)
            entry["technical_panel"] = deepcopy(panel)
            requests = [("all_no_link_control", [])]
            if include_greedy_bundle:
                links = greedy_links(scope, settings["max_greedy_links"])
                if links:
                    requests.append(("bounded_greedy_endpoint_matching_technical_probe", links))
                else:
                    entry["bundle_comparisons"].append({"kind": "bounded_greedy_endpoint_matching_technical_probe",
                        "bundle": None, "comparison": None, "status": "no_admissible_probe_links_no_duplicate_control",
                        "reasons": ["no_bounded_greedy_links_available"]})
            bundles, comparisons = [], []
            for kind, links in requests:
                bundle = engine.compile_bundle_prepared(session, links, geometry_work_budget=settings["geometry_work_budget"])
                frozen._check(bundle, engine.BUNDLE_PREFIX)
                comparison = engine.compare_prepared(session, panel["selectors"], bundle["record_id"],
                    **{k: settings[k] for k in ("max_hypotheses", "max_slots", "query_work_budget")})
                frozen._check(comparison, engine.COMPARISON_PREFIX)
                if (bundle["lattice_ref"] != frozen._ref(lattice) or comparison["bundle_ref"] != frozen._ref(bundle)
                        or comparison["selectors"] != panel["selectors"]):
                    raise ValueError("native_bundle_comparison_identity_mismatch")
                bundles.append(bundle)
                comparisons.append(comparison)
                entry["bundle_comparisons"].append({"kind": kind, "bundle": _saved(output, "bundles", bundle, artifacts),
                    "comparison": _saved(output, "comparisons", comparison, artifacts),
                    "status": comparison["status"], "reasons": deepcopy(comparison["reasons"])})
            if before != digest(case):
                raise ValueError("registered_full_IR_or_scope_mutated_during_native_trial")
            entry["native_counts"] = _counts(lattice, panel, bundles, comparisons, 1 + int(include_greedy_bundle))
            entry["status"] = "native_lattice_probe_saved_not_selected"
        except Exception as exc:
            entry["status"], entry["error"] = "calculation_failure", f"{type(exc).__name__}:{exc}"
            failures.append({"context_key": deepcopy(row["context_key"]), "error": entry["error"]})
        if case is not None and before != digest(case):
            entry["status"], entry["error"] = "calculation_failure", "ValueError:registered_full_IR_or_scope_mutated_during_native_trial"
            failure = {"context_key": deepcopy(entry["context_key"]), "error": entry["error"]}
            if failure not in failures:
                failures.append(failure)
        if entry["status"] == "native_lattice_probe_saved_not_selected":
            for name, count in entry["native_counts"].items():
                if type(count) is int:
                    metric_totals[name] += count
                elif count is None:
                    unknown_metrics[name] += 1
        entry["elapsed_seconds"] = perf_counter() - case_started
        rows.append(entry)
        print(f"[{len(rows)}/{len(data['rows'])}] {entry['status']} {entry['elapsed_seconds']:.3f}s", flush=True)
    storage._save(output, "context-index.json", rows, artifacts)
    changed = [p for p, h in {**inputs, **code}.items() if not Path(p).is_file() or parent.file_digest(p) != h]
    if {str(p.resolve()) for p in _code_paths()} != set(code):
        changed.append("creation_code_inventory_changed")
    if {str(p.resolve()) for p in data["directory"].rglob("*") if p.is_file()} != data["inventory"]:
        changed.append("registered_phase21_parent_inventory_changed")
    changed_artifacts = [p for p, h in artifacts.items() if not Path(p).is_file() or parent.file_digest(p) != h]
    if {str(p.resolve()) for p in output.rglob("*") if p.is_file()} != set(artifacts):
        changed_artifacts.append("generated_artifact_inventory_changed")
    denominator = ([r["context_key"] for r in rows] == plan["selected_contexts"]
                   and all(totals[k] == data["report"]["summary"][k] for k in previous.DENOMINATORS))
    integrity = not failures and not changed and not changed_artifacts
    report = {"version": VERSION, "scope_calculation_complete": bool(integrity and denominator),
        "computation_integrity_passed": bool(integrity), "selected_denominators_complete": bool(denominator),
        "inputs_and_code_unchanged": not changed, "artifacts_unchanged": not changed_artifacts,
        "changed_inputs_or_code": changed, "changed_artifacts": changed_artifacts, "failures": failures,
        "artifact_hashes": deepcopy(artifacts), "parent_summary": deepcopy(data["report"]["summary"]),
        "summary": {"registered_parent_denominators": dict(totals), "native_integer_subtotals": dict(metric_totals),
            "native_unknown_metric_contexts": dict(unknown_metrics), "selected_contexts": len(rows),
            "selected_original_raw_lanes": totals["old_raw_lanes"],
            "native_saved_contexts": sum(r["status"] == "native_lattice_probe_saved_not_selected" for r in rows),
            "native_failed_contexts": sum(r["status"] == "calculation_failure" for r in rows),
            **cohort._cohort_counts(plan, totals), "context_status_counts": dict(Counter(r["status"] for r in rows))},
        "source_authority": AUTHORITY, "selected": None, **{k: False for k in POLICY_FALSE},
        "fresh_native_interval_suppliers_enabled": True,
        "fresh_native_completions_created": metric_totals["registered_bundles"] > 0,
        "source_scope_geometry_freshly_checked_by_native_engine": bool(integrity and denominator),
        "elapsed_seconds": perf_counter() - started,
        "limits": ["Registered metadata hashes are not an issued original-parent/session authority; no cold parent replay occurred.",
            "Native scope checks use the exact protected full IR, not a projection assembled into a fake score.",
            "All contiguous observed-grid intervals and exact DP counts are new; no legacy path/key/origin/completion is extended.",
            "Five selected contexts and their raw lanes are technical probes, separate from the declared 322-context/1013-lane cohort.",
            "Quantile cuts and first native IDs are label-blind implementation probes, not selected musical boundaries or harmonies.",
            "None versus one explicit V7/M vector is not a general transition-assumption coverage claim.",
            "Each comparison uses one fresh registered complete all-raw-lane witness; pairwise witnesses are never combined.",
            "Unknown/whole-held suppliers, panel requests, query budgets and universe denominators are not replaced by favorable prefixes.",
            "Provider ornaments are not joint NCT proof; local/boundary NCT credits and all-doubling obligations remain unintegrated.",
            "No harmony/key/cadence winner, accuracy, training, Gold, generation, UI or production promotion follows."]}
    parent.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-parent", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--no-greedy-bundle", action="store_false", dest="include_greedy_bundle")
    for name, value in SETTINGS.items():
        parser.add_argument("--" + name.replace("_", "-"), type=int, default=value)
    report = run(**vars(parser.parse_args()))
    print(report["summary"], flush=True)
    return 0 if report["scope_calculation_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
