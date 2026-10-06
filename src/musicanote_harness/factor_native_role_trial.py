"""One-context, append-only native conditional-role technical probe.

Registered phase-22/23 files are protected metadata, not old session authority.
One genuine full IR/scope receives one fresh native preparation. Every role
sidecar uses one complete all-raw-lane bundle; no pairwise witness union occurs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import gzip
from hashlib import sha256
import json
from pathlib import Path
import re
from time import perf_counter

from . import factor_expanded_hypotheses as sealed
from . import factor_expanded_scope as expanded
from . import factor_interval_lattice as native
from . import factor_interval_lattice_trial as native_trial
from . import factor_native_role_explanations as roles
from . import harmony_frozen_context_lineage_trial as storage
from . import harmony_shared_candidate_supply_trial as supply_trial
from .musical_pattern_observation import digest, f, q

ROOT = storage.ROOT
VERSION = "factor-native-role-trial-0.1.0"
SETTINGS = {**native.DEFAULTS, "max_hypotheses": 3, "max_slots": 3,
            "native_query_work_budget": 2000000, "role_query_work_budget": 3000000,
            "geometry_work_budget": 100000, "max_greedy_links": 20}
PANEL_POLICY = "observed_half_thirds_first_native_origin_and_key_id_three_structural_probes"
AUTHORITY = "fresh_owned_native_full_IR_scope_not_saved_parent_session_authority"
POLICY_FALSE = ("music_accuracy_evaluated", "harmony_confirmed", "cadence_confirmed",
    "NCT_confirmed", "training_eligible", "gold_eligible", "generation_ready",
    "source_labels_used_for_inference", "core_or_production_modified", "UI_connected",
    "cohort_complete", "all_logical_paths_evaluated", "all_doublings_required",
    "original_parent_file_authority_replayed", "old_native_session_reused",
    "independent_completions_unioned", "source_projection_synthesized_as_IR")
ROLE_INTEGER_SUMMARY_FIELDS = {"planned_paths", "native_computed_paths", "computed_paths",
    "planned_clause_upper_bound", "unique_geometry_count", "evaluated_clauses",
    "qualified_clauses", "satisfied_clauses", "failed_clauses", "unassessed_clauses",
    "credit_sound_occurrences", "withheld_paths"}
ROLE_SUMMARY_FIELDS = {*ROLE_INTEGER_SUMMARY_FIELDS, "role_clause_occurrences"}
NATIVE_REPORT_KEYS = {"version", "scope_calculation_complete", "computation_integrity_passed",
    "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged",
    "changed_inputs_or_code", "changed_artifacts", "failures", "artifact_hashes", "parent_summary",
    "summary", "source_authority", "selected", *native_trial.POLICY_FALSE,
    "fresh_native_interval_suppliers_enabled", "fresh_native_completions_created",
    "source_scope_geometry_freshly_checked_by_native_engine", "elapsed_seconds", "limits"}
NATIVE_PLAN_KEYS = {"version", "context_parent", "parent_report_sha256", "inputs", "code", "settings",
    "include_greedy_bundle", "declared_contexts", "declared_units", "selected_contexts", "selection",
    "panel_policy", "source_authority", "source_scope_geometry_freshly_checked_by_native_engine",
    "fresh_native_interval_suppliers_enabled", "original_parent_artifacts_registered_not_replayed",
    "old_selector_or_analysis_reexecuted", "old_paths_or_bundles_extended", "source_labels_used_for_inference",
    "production_modified", "cohort_complete", "sample_is_accuracy_evaluation", "all_logical_paths_evaluated",
    "general_transition_assumption_universe_evaluated"}
NATIVE_ROW_KEYS = {"context_key", "registered_parent_row_sha256", "registered_parent_metadata", "full_IR",
    "native_lattice", "technical_panel", "bundle_comparisons", "native_counts", "status", "error", "elapsed_seconds"}
SUPPLIER_REPORT_KEYS = {"version", "status", "contexts", "request_occurrences", "distinct_context_span_queries",
    "candidate_occurrences", "baseline_seconds", "baseline_serialization_seconds", "prepare_plus_cold_seconds",
    "warm_seconds", "cold_window_calls", "warm_window_calls", "legacy_window_calls_structural_not_instrumented",
    "protected_paths", "changed_protected_paths", "artifact_sha256", "elapsed_seconds", "music_accuracy_evaluated",
    "native_lattice_reexecuted", "old_saved_catalogs_replayed", "production_or_UI_connected", "limits"}
SUPPLIER_PLAN_KEYS = {"version", "parent", "protected_sha256", "selection_policy", "source_labels_used_for_inference",
    "native_lattice_reexecuted", "original_parent_file_authority_replayed", "requests"}


def _limit(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("explicit_nonnegative_integer_role_trial_limit_required:" + name)


def _closed(value, keys, name):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError("closed_role_trial_record_required:" + name)


def _file_sha(path):
    result = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            result.update(block)
    return result.hexdigest()


def _reject_constant(value):
    raise ValueError("nonfinite_saved_JSON_number:" + value)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_saved_JSON_key:" + key)
        result[key] = value
    return result


def _read(path):
    path = Path(path)
    stream = gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz" else path.open(encoding="utf-8")
    with stream:
        return json.load(stream, parse_constant=_reject_constant, object_pairs_hook=_unique_object)


def _protect(hashes, path, expected):
    if (type(path) is not str or not Path(path).is_absolute()
            or str(Path(path).resolve(strict=True)) != path or type(expected) is not str
            or re.fullmatch(r"[0-9a-f]{64}", expected) is None):
        raise ValueError("registered_canonical_absolute_SHA256_required")
    if path in hashes and hashes[path] != expected:
        raise ValueError("conflicting_registered_SHA256:" + path)
    hashes[path] = expected


def _protect_map(hashes, values):
    if type(values) is not dict:
        raise ValueError("registered_SHA256_map_required")
    for path, expected in values.items():
        _protect(hashes, path, expected)


def _guard(hashes):
    return [path for path, expected in hashes.items()
            if not Path(path).is_file() or _file_sha(path) != expected]


def _inventory(directory, artifacts, report_path):
    if type(artifacts) is not dict or any(type(path) is not str
            or not Path(path).is_relative_to(directory) or Path(path) == report_path for path in artifacts):
        raise ValueError("registered_parent_artifact_directory_required")
    actual = {str(path.resolve()) for path in directory.rglob("*") if path.is_file()}
    if actual != {*artifacts, str(report_path)}:
        raise ValueError("exact_registered_parent_inventory_required")
    return actual


def _code_paths():
    tests = [ROOT / "tests/test_factor_native_role_explanations.py",
             ROOT / "tests/test_factor_native_role_trial.py"]
    return sorted({*storage._code_paths(), *(path for path in tests if path.is_file())})


def load_inputs(native_parent, supplier_parent, *, context_position=1):
    """Only metadata and ONE registered full IR/scope; no old cold replay."""
    _limit(context_position, "context_position")
    native_parent, supplier_parent = (Path(p).resolve(strict=True) for p in (native_parent, supplier_parent))
    if native_parent == supplier_parent:
        raise ValueError("distinct_phase22_and_phase23_parents_required")
    protected, inventories = {}, {}
    report_path = native_parent / "report.json"
    report = _read(report_path)
    _closed(report, NATIVE_REPORT_KEYS, "phase22_metadata_report")
    if (report.get("version") != native_trial.VERSION
            or any(report.get(key) is not True for key in ("scope_calculation_complete",
                "computation_integrity_passed", "selected_denominators_complete",
                "inputs_and_code_unchanged", "artifacts_unchanged"))
            or any(report.get(key) != [] for key in ("failures", "changed_inputs_or_code", "changed_artifacts"))
            or report.get("selected") is not None
            or any(report.get(key) is not False for key in native_trial.POLICY_FALSE)):
        raise ValueError("completed_unselected_registered_phase22_required")
    _protect(protected, str(report_path), _file_sha(report_path))
    _protect_map(protected, report["artifact_hashes"])
    inventories[str(native_parent)] = _inventory(native_parent, report["artifact_hashes"], report_path)
    plan = _read(native_parent / "run-plan.json")
    _closed(plan, NATIVE_PLAN_KEYS, "phase22_creation_plan")
    if (plan.get("version") != native_trial.VERSION
            or plan.get("source_labels_used_for_inference") is not False
            or plan.get("cohort_complete") is not False):
        raise ValueError("registered_phase22_creation_plan_required")
    for name in ("inputs", "code"):
        _protect_map(protected, plan[name])
    for name in ("declared_contexts", "selected_contexts"):
        if (type(plan[name]) is not list
                or len({native_trial._context_key(key) for key in plan[name]}) != len(plan[name])):
            raise ValueError("unique_declared_or_selected_context_inventory_required")
    contexts = {native_trial._context_key(key) for key in plan["declared_contexts"]}
    if (not {native_trial._context_key(key) for key in plan["selected_contexts"]} <= contexts
            or type(plan["declared_units"]) is not list):
        raise ValueError("selected_contexts_outside_declared_original_cohort")
    units = set()
    for unit in plan["declared_units"]:
        _closed(unit, {"context_key", "lane"}, "declared_original_raw_lane_unit")
        key, lane = native_trial._context_key(unit["context_key"]), unit["lane"]
        if (key not in contexts or type(lane) is not list or len(lane) != 2
                or any(type(value) is not str for value in lane) or (key, tuple(lane)) in units):
            raise ValueError("unique_declared_original_raw_lane_unit_required")
        units.add((key, tuple(lane)))
    rows = _read(native_parent / "context-index.json")
    if (type(rows) is not list or any(type(row) is not dict for row in rows)
            or [row.get("context_key") for row in rows] != plan.get("selected_contexts")
            or context_position >= len(rows)):
        raise ValueError("registered_context_position_or_exact_inventory_required")
    row = rows[context_position]
    _closed(row, NATIVE_ROW_KEYS, "registered_phase22_context_row")
    if (row.get("status") != "native_lattice_probe_saved_not_selected" or row.get("error") is not None
            or row.get("registered_parent_row_sha256") != digest(row.get("registered_parent_metadata"))
            or row["context_key"] != row["registered_parent_metadata"]["context_key"]):
        raise ValueError("completed_exact_registered_context_metadata_required")
    lane_refs = row["registered_parent_metadata"]["old_lane_refs"]
    if type(lane_refs) is not list:
        raise ValueError("registered_original_raw_lane_references_required")
    lanes = []
    for lane_ref in lane_refs:
        _closed(lane_ref, {"lane", "old_status", "old_graph_ref"}, "registered_original_raw_lane_reference")
        lane = lane_ref["lane"]
        if type(lane) is not list or len(lane) != 2 or any(type(value) is not str for value in lane):
            raise ValueError("original_two_string_raw_lane_reference_required")
        lanes.append(tuple(lane))
    selected_key = native_trial._context_key(row["context_key"])
    if len(lanes) != len(set(lanes)) or set(lanes) != {lane for key, lane in units if key == selected_key}:
        raise ValueError("selected_original_raw_lane_denominator_mismatch")

    supplier_report_path = supplier_parent / "report.json"
    supplier_report = _read(supplier_report_path)
    _closed(supplier_report, SUPPLIER_REPORT_KEYS, "phase23_metadata_report")
    if (supplier_report.get("version") != supply_trial.VERSION
            or supplier_report.get("status") != "exact_supplier_equivalence_complete"
            or supplier_report.get("changed_protected_paths") != []
            or any(supplier_report.get(key) is not False for key in ("music_accuracy_evaluated",
                "native_lattice_reexecuted", "old_saved_catalogs_replayed", "production_or_UI_connected"))):
        raise ValueError("completed_registered_phase23_equivalence_required")
    _protect(protected, str(supplier_report_path), _file_sha(supplier_report_path))
    _protect_map(protected, supplier_report["artifact_sha256"])
    inventories[str(supplier_parent)] = _inventory(supplier_parent, supplier_report["artifact_sha256"], supplier_report_path)
    supplier_plan = _read(supplier_parent / "run-plan.json")
    _closed(supplier_plan, SUPPLIER_PLAN_KEYS, "phase23_creation_plan")
    if (supplier_plan.get("version") != supply_trial.VERSION
            or Path(supplier_plan.get("parent", "")).resolve(strict=True) != native_parent
            or any(supplier_plan.get(key) is not False for key in ("source_labels_used_for_inference",
                "native_lattice_reexecuted", "original_parent_file_authority_replayed"))):
        raise ValueError("phase23_registered_parent_or_creation_policy_mismatch")
    _protect_map(protected, supplier_plan["protected_sha256"])
    changed = _guard(protected)
    if changed:
        raise ValueError("registered_input_source_or_prior_code_changed:" + repr(changed))

    ir_info = row["full_IR"]
    _closed(ir_info, {"artifact", "sha256", "ir_document_id", "ir_content_sha256",
                     "binding_match", "registered_full_IR_not_projection"}, "registered_full_IR")
    if (ir_info["binding_match"] is not True or ir_info["registered_full_IR_not_projection"] is not True
            or protected.get(ir_info["artifact"]) != ir_info["sha256"]):
        raise ValueError("registered_full_IR_not_projection_required")
    scope_info = row["registered_parent_metadata"]["expanded_scope"]
    _closed(scope_info, {"artifact", "sha256", "record_ref", "status"}, "registered_scope")
    if protected.get(scope_info["artifact"]) != scope_info["sha256"]:
        raise ValueError("expanded_scope_not_in_registered_creation_inputs")
    ir, scope = (_read(info["artifact"]) for info in (ir_info, scope_info))
    sealed._check(scope, expanded.PREFIX)
    if (scope_info["record_ref"] != sealed._ref(scope) or scope_info["status"] != scope["status"]
            or ir.get("ir_document_id") != ir_info["ir_document_id"]
            or digest(ir) != ir_info["ir_content_sha256"] or expanded._binding(ir) != scope["binding"]):
        raise ValueError("exact_registered_full_IR_and_scope_binding_required")
    return {"native_parent": native_parent, "supplier_parent": supplier_parent,
            "report": report, "plan": plan, "rows": rows, "row": row,
            "ir": ir, "scope": scope, "ir_info": deepcopy(ir_info),
            "scope_info": deepcopy(scope_info), "hashes": protected, "inventories": inventories}


def technical_panel(lattice):
    """Three fixed structural probes, never annotation/work-ID chord choices."""
    original = native_trial.technical_panel(lattice)
    keys = sorted(lattice["keys"], key=lambda key: key["record_id"])
    if not keys:
        raise ValueError("registered_native_key_inventory_required")
    rows, selectors = [], []
    for row in original["rows"]:
        entry = deepcopy(row)
        entry["planned_selectors"] = 1
        available = row["status"] == "available_technical_probe"
        entry["available_selectors"] = int(available)
        if available:
            ids = deepcopy(row["native_origin_ids"])
            selectors.append({"origin_ids": ids, "key_id": keys[0]["record_id"],
                              "transition_assumptions": [{"family": "V7", "quality": "M"}
                                                         for _ in range(len(ids) - 1)]})
        rows.append(entry)
    return {"selection_policy": PANEL_POLICY, "rows": rows, "selectors": selectors,
            "planned_selectors": 3, "available_selectors": len(selectors),
            "key_ref": sealed._ref(keys[0]), "known_and_unknown_key_inventory": len(keys),
            "origin_choice": "first_native_record_id_not_accuracy_or_membership_rank",
            "transition_profile": "explicit_V7_M_technical_assumption_not_selected_function",
            "source_annotation_labels_used": False, "winning_hypothesis_selected": False}


def _save_record(output, folder, value, prefix, artifacts):
    sealed._check(value, prefix)
    if re.fullmatch(r"[a-z0-9_]+", value["record_id"]) is None:
        raise ValueError("closed_generated_record_filename_required")
    directory = output / folder
    directory.mkdir(exist_ok=True)
    path = directory / (value["record_id"] + ".json.gz")
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    with path.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(encoded)
    artifacts[str(path)] = _file_sha(path)
    return {"artifact": str(path), "sha256": artifacts[str(path)],
            "record_ref": sealed._ref(value), "status": value["status"]}


def _save_json(output, name, value, artifacts):
    path = output / name
    storage.write_new(path, value)
    artifacts[str(path)] = _file_sha(path)


def _validate_role_summary(explanation, comparison):
    """Closed typed counters, including map-valued occurrence denominators."""
    summary = explanation["summary"]
    _closed(summary, ROLE_SUMMARY_FIELDS, "role_summary")
    for key in ROLE_INTEGER_SUMMARY_FIELDS:
        _limit(summary[key], "role_summary." + key)
    counts = summary["role_clause_occurrences"]
    if type(counts) is not dict or any(type(key) is not str or not key for key in counts):
        raise ValueError("typed_role_clause_occurrence_count_map_required")
    for count in counts.values():
        _limit(count, "role_clause_occurrences")
    clauses = [clause for path in explanation["paths"] for clause in path["clauses"]]
    statuses = Counter(clause["status"] for clause in clauses)
    if (summary["planned_paths"] != comparison["summary"]["planned_selectors"]
            or summary["native_computed_paths"] != len(comparison["paths"])
            or summary["computed_paths"] != len(explanation["paths"])
            or summary["withheld_paths"] != summary["planned_paths"] - summary["computed_paths"]
            or summary["planned_clause_upper_bound"] != explanation["query_plan"]["clause_upper_bound"]
            or summary["evaluated_clauses"] != len(clauses)
            or summary["unique_geometry_count"] != len({clause["geometry_id"] for clause in clauses})
            or counts != dict(Counter(clause["role"] for clause in clauses))
            or any(type(clause["qualified"]) is not bool for clause in clauses)
            or summary["qualified_clauses"] != sum(clause["qualified"] for clause in clauses)
            or summary["satisfied_clauses"] != statuses["supported"]
            or summary["failed_clauses"] != statuses["failed"]
            or summary["unassessed_clauses"] != statuses["unassessed"]
            or summary["satisfied_clauses"] + summary["failed_clauses"] + summary["unassessed_clauses"] != len(clauses)
            or summary["credit_sound_occurrences"] != sum(
                len(path["account"]["explained_intervals_by_sound"]) for path in explanation["paths"])):
        raise ValueError("exact_role_summary_occurrence_denominators_required")


def _counts(lattice, panel, bundles, comparisons, explanations):
    paths = [path for comparison in comparisons for path in comparison["paths"]]
    role_paths = [path for explanation in explanations for path in explanation["paths"]]
    clauses = [clause for path in role_paths for clause in path["clauses"]]
    return {"planned_structural_selector_occurrences": panel["planned_selectors"] * len(bundles),
            "submitted_selector_occurrences": sum(len(c["selectors"]) for c in comparisons),
            "computed_selector_occurrences": len(paths),
            "distinct_origin_path_keys": len({digest([p["origin_refs"], p["key_ref"]]) for p in paths}),
            "distinct_completion_origin_path_keys": len({digest([p["bundle_ref"], p["origin_refs"], p["key_ref"]]) for p in paths}),
            "complete_all_lane_bundles": sum(b["status"] == "complete_all_lane_witness" for b in bundles),
            "withheld_all_lane_bundles": sum(b["status"] != "complete_all_lane_witness" for b in bundles),
            "whole_comparison_holds": sum(c["status"] == "whole_comparison_hold" for c in comparisons),
            "whole_explanation_holds": sum(e["status"] == "whole_explanation_hold" for e in explanations),
            "computed_role_paths": len(role_paths), "evaluated_clause_occurrences": len(clauses),
            "role_status_occurrences": dict(Counter((c["role"] + ":" + c["status"]) for c in clauses)),
            "raw_time_conserved_role_paths": sum(p["account"]["raw_time_conserved"] is True for p in role_paths),
            "conditional_explained_note_time_selector_occurrence_sum": q(sum(
                (f(p["account"]["conditional_explanation_note_time_quarters"]) for p in role_paths
                 if p["account"]["conditional_explanation_note_time_quarters"] is not None), start=f(q(0)))),
            "logical_universe": deepcopy(lattice["universe"]),
            "role_summary_occurrence_subtotals": {key: sum(e["summary"][key] for e in explanations)
                                                   for key in sorted(ROLE_INTEGER_SUMMARY_FIELDS)},
            "role_clause_occurrences": dict(sum(
                (Counter(e["summary"]["role_clause_occurrences"]) for e in explanations), start=Counter()))}


def run(native_parent, supplier_parent, output, *, context_position=1,
        include_greedy_bundle=True, **limits):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("append_only_new_direct_workspace_output_required")
    _limit(context_position, "context_position")
    if type(include_greedy_bundle) is not bool or set(limits) - set(SETTINGS):
        raise ValueError("closed_bounded_role_trial_settings_required")
    settings = {**SETTINGS, **limits}
    for key, value in settings.items():
        _limit(value, key)
    if settings["max_hypotheses"] > 3 or settings["max_slots"] > 3 or settings["max_greedy_links"] > 20:
        raise ValueError("at_most_three_structural_probes_twenty_greedy_links_required")
    data = load_inputs(native_parent, supplier_parent, context_position=context_position)
    inputs = deepcopy(data["hashes"])
    code = {str(path.resolve()): _file_sha(path) for path in _code_paths()}
    protected = deepcopy(inputs)
    _protect_map(protected, code)
    ir, scope, row = (data[name] for name in ("ir", "scope", "row"))
    case_before = digest([ir, scope])
    selected_key = row["context_key"]
    declared_contexts = data["plan"]["declared_contexts"]
    declared_units = data["plan"]["declared_units"]
    selected_units = [unit for unit in declared_units if unit["context_key"] == selected_key]
    denominators = {"declared_contexts": len(declared_contexts), "declared_original_raw_lanes": len(declared_units),
                    "registered_phase22_contexts": len(data["rows"]), "selected_contexts": 1,
                    "selected_original_raw_lanes": len(selected_units),
                    "unexecuted_declared_contexts": len(declared_contexts) - 1,
                    "unexecuted_declared_original_raw_lanes": len(declared_units) - len(selected_units)}
    plan = {"version": VERSION, "native_parent": str(data["native_parent"]),
            "supplier_parent": str(data["supplier_parent"]), "inputs": inputs, "code": code,
            "settings": settings, "context_position": context_position, "selected_context_key": deepcopy(selected_key),
            "registered_parent_row_sha256": digest(row), "full_IR": data["ir_info"], "scope": data["scope_info"],
            "denominators": denominators, "panel_policy": PANEL_POLICY,
            "source_authority": AUTHORITY, "fresh_native_preparation_planned": True,
            "include_greedy_bundle": include_greedy_bundle, **{key: False for key in POLICY_FALSE}}
    output.mkdir()
    artifacts, bundles, comparisons, explanations, entries, failures = {}, [], [], [], [], []
    _save_json(output, "run-plan.json", plan, artifacts)
    lattice, panel, preparation_count = None, None, 0
    print("NATIVE ROLE PROBE START", selected_key[0], flush=True)
    try:
        preparation_count += 1
        session = native.prepare_lattice(ir, scope, **{key: settings[key] for key in native.DEFAULTS})
        lattice = native.lattice_prepared(session)
        lattice_info = _save_record(output, "lattices", lattice, native.PREFIX, artifacts)
        panel = technical_panel(lattice)
        requests = [("all_no_link_control", [])]
        if include_greedy_bundle:
            links = native_trial.greedy_links(scope, settings["max_greedy_links"])
            if links:
                requests.append(("bounded_same_raw_lane_greedy_technical_probe", links))
            else:
                entries.append({"kind": "bounded_same_raw_lane_greedy_technical_probe",
                                "status": "no_admissible_links_no_duplicate_control", "reasons": ["no_greedy_probe_links"]})
        for kind, links in requests:
            bundle = native.compile_bundle_prepared(session, links, geometry_work_budget=settings["geometry_work_budget"])
            comparison = native.compare_prepared(session, panel["selectors"], bundle["record_id"],
                max_hypotheses=settings["max_hypotheses"], max_slots=settings["max_slots"],
                query_work_budget=settings["native_query_work_budget"])
            handle = roles.prepare_explanations(session, comparison)
            explanation = roles.explain_prepared(handle, query_work_budget=settings["role_query_work_budget"])
            _validate_role_summary(explanation, comparison)
            if (comparison["bundle_ref"] != sealed._ref(bundle)
                    or comparison["lattice_ref"] != sealed._ref(lattice)
                    or explanation["native_comparison_ref"] != sealed._ref(comparison)
                    or explanation["bundle_ref"] != sealed._ref(bundle)
                    or explanation["scope_ref"] != sealed._ref(scope)
                    or explanation["lattice_ref"] != sealed._ref(lattice)
                    or explanation["native_request"] != {key: comparison[key] for key in (
                        "selectors", "resource_limits", "status", "reasons", "summary", "query_plan")}
                    or comparison["selectors"] != panel["selectors"]):
                raise ValueError("same_native_session_bundle_and_role_sidecar_reference_mismatch")
            bundles.append(bundle); comparisons.append(comparison); explanations.append(explanation)
            entries.append({"kind": kind,
                "bundle": _save_record(output, "bundles", bundle, native.BUNDLE_PREFIX, artifacts),
                "comparison": _save_record(output, "comparisons", comparison, native.COMPARISON_PREFIX, artifacts),
                "explanation": _save_record(output, "explanations", explanation, roles.PREFIX, artifacts),
                "required_links": deepcopy(links), "native_summary": deepcopy(comparison["summary"]),
                "role_summary": deepcopy(explanation["summary"]), "role_query_plan": deepcopy(explanation["query_plan"]),
                "status": explanation["status"], "reasons": deepcopy(explanation["reasons"])})
        if case_before != digest([ir, scope]):
            raise ValueError("registered_full_IR_or_scope_changed_during_native_role_probe")
        index = {"context_key": deepcopy(selected_key), "full_IR": data["ir_info"], "scope": data["scope_info"],
                 "native_lattice": lattice_info, "panel": panel, "bundle_explanations": entries,
                 "counts": _counts(lattice, panel, bundles, comparisons, explanations),
                 "status": "native_role_probe_saved_not_selected", "error": None}
    except Exception as exc:
        error = f"{type(exc).__name__}:{exc}"
        failures.append({"context_key": deepcopy(selected_key), "error": error})
        index = {"context_key": deepcopy(selected_key), "full_IR": data["ir_info"], "scope": data["scope_info"],
                 "panel": panel, "bundle_explanations": entries, "counts": None,
                 "status": "calculation_failure", "error": error}
    _save_json(output, "context-index.json", [index], artifacts)
    changed = _guard(protected)
    if {str(path.resolve()) for path in _code_paths()} != set(code):
        changed.append("creation_code_inventory_changed")
    for directory, inventory in data["inventories"].items():
        if {str(path.resolve()) for path in Path(directory).rglob("*") if path.is_file()} != inventory:
            changed.append("registered_parent_inventory_changed:" + directory)
    if case_before != digest([ir, scope]):
        changed.append("registered_full_IR_or_scope_content_changed")
    changed_artifacts = _guard(artifacts)
    if {str(path.resolve()) for path in output.rglob("*") if path.is_file()} != set(artifacts):
        changed_artifacts.append("generated_artifact_inventory_changed")
    integrity = not failures and not changed and not changed_artifacts
    report = {"version": VERSION, "status": "native_role_probe_complete_not_selected" if integrity else "native_role_probe_failed",
              "computation_integrity_passed": integrity, "inputs_and_code_unchanged": not changed,
              "artifacts_unchanged": not changed_artifacts, "changed_inputs_or_code": changed,
              "changed_artifacts": changed_artifacts, "failures": failures, "artifact_hashes": artifacts,
              "denominators": denominators, "fresh_native_preparations": preparation_count,
              "source_authority": AUTHORITY, "selected": None,
              "role_calculation_complete": bool(integrity and explanations and all(
                  e["status"] == "computed_native_role_explanations_not_selected" for e in explanations)),
              "counts": index["counts"] if integrity else None, "elapsed_seconds": perf_counter() - started,
              **{key: False for key in POLICY_FALSE},
              "limits": ["One caller-selected registered context, not all five contexts or the full declared cohort.",
                         "Old saved lattice and earlier parent output chains were not cold replayed; fresh native source/suppliers were executed.",
                         "Fixed first-ID candidates are technical probes; zero supported clauses is a coverage gap, not accuracy.",
                         "Every explanation is conditional on one complete registered all-lane witness and explicit candidate/key assumptions.",
                         "Whole budget holds remain visible; no favorable-prefix fallback or after-result budget increase occurs.",
                         "Raw note-time is preserved; conditional interval union is not a final NCT, harmony, cadence, gold or generation verdict."]}
    storage.write_new(output / "report.json", report)
    print("NATIVE ROLE PROBE DONE", report["status"], f"{report['elapsed_seconds']:.3f}s", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-parent", type=Path, required=True)
    parser.add_argument("--supplier-parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--context-position", type=int, default=1)
    args = parser.parse_args()
    run(args.native_parent, args.supplier_parent, args.output, context_position=args.context_position)


if __name__ == "__main__":
    main()
