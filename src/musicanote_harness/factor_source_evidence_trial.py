"""Append-only, source-size-selected native conditional-role evidence probe.

Registered full IRs/scopes are freshly prepared once per selected context.
Old saved sessions/labels never supply native authority or winning hypotheses.
Every ordered source-evidence selector batch runs under each actual all-lane
completion, with visible whole holds and separately stored bounded examples.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from . import factor_native_role_trial as old
from . import factor_source_evidence_panel as panel_engine
from .musical_pattern_observation import digest, f, q

native, roles, sealed, storage = old.native, old.roles, old.sealed, old.storage
ROOT = old.ROOT
VERSION = "factor-source-evidence-trial-0.1.0"
SELECTION_POLICY = "registered_observed_coordinate_count_sound_count_context_key_ascending"
AUTHORITY = "fresh_native_full_IR_scope_and_same_completion_source_evidence_not_saved_parent_session_authority"
SETTINGS = {**native.DEFAULTS, "max_selectors": 64, "selection_work_budget": 3000000,
    "max_hypotheses": 3, "max_slots": 3, "native_query_work_budget": 2000000,
    "role_query_work_budget": 100000000, "geometry_work_budget": 100000, "max_greedy_links": 20}
POLICY_FALSE = (*old.POLICY_FALSE, "old_lattice_or_role_outputs_cold_replayed",
    "outcome_based_context_selection", "positive_only_case_coverage", "musical_voice_identity_confirmed")
ROLE_REPORT_KEYS = {"version", "status", "computation_integrity_passed", "inputs_and_code_unchanged",
    "artifacts_unchanged", "changed_inputs_or_code", "changed_artifacts", "failures", "artifact_hashes",
    "denominators", "fresh_native_preparations", "source_authority", "selected", "role_calculation_complete",
    "counts", "elapsed_seconds", "limits", *old.POLICY_FALSE}
ROLE_PLAN_KEYS = {"version", "native_parent", "supplier_parent", "inputs", "code", "settings",
    "context_position", "selected_context_key", "registered_parent_row_sha256", "full_IR", "scope",
    "denominators", "panel_policy", "source_authority", "fresh_native_preparation_planned",
    "include_greedy_bundle", *old.POLICY_FALSE}
PANEL_INTEGER_FIELDS = {"native_interval_catalogs", "native_origins", "requested_intervals",
    "complete_proposal_paths", "submitted_selectors"}
PANEL_BOUND_FIELDS = {"planned_selector_upper_bound", "unsubmitted_selector_bound"}
PANEL_NULLABLE_FIELDS = {"evaluated_origin_occurrences", "eligible_origin_occurrences", "rejected_origin_occurrences"}


def _code_paths():
    extra = [ROOT / "tests/test_factor_native_role_explanations.py",
             ROOT / "tests/test_factor_native_role_trial.py",
             ROOT / "tests/test_factor_source_evidence_panel.py",
             ROOT / "tests/test_factor_source_evidence_trial.py"]
    return sorted({*storage._code_paths(), *(path for path in extra if path.is_file())})


def _register_role_parent(directory, native_parent, supplier_parent, hashes, inventories):
    """Protect exactly ten phase-24 files; metadata is not native authority."""
    directory = Path(directory).resolve(strict=True)
    if directory in (native_parent, supplier_parent):
        raise ValueError("distinct_registered_phase24_parent_required")
    path = directory / "report.json"
    report = old._read(path)
    old._closed(report, ROLE_REPORT_KEYS, "phase24_role_metadata_report")
    old._limit(report["fresh_native_preparations"], "phase24_fresh_native_preparations")
    if (report["version"] != old.VERSION or report["status"] != "native_role_probe_complete_not_selected"
            or any(report[key] is not True for key in ("computation_integrity_passed",
                "inputs_and_code_unchanged", "artifacts_unchanged", "role_calculation_complete"))
            or any(report[key] != [] for key in ("changed_inputs_or_code", "changed_artifacts", "failures"))
            or any(report[key] is not False for key in old.POLICY_FALSE) or report["selected"] is not None
            or report["fresh_native_preparations"] != 1 or type(report["artifact_hashes"]) is not dict
            or len(report["artifact_hashes"]) != 9):
        raise ValueError("completed_unselected_exact_phase24_creation_required")
    old._protect(hashes, str(path), old._file_sha(path))
    old._protect_map(hashes, report["artifact_hashes"])
    inventories[str(directory)] = old._inventory(directory, report["artifact_hashes"], path)
    plan = old._read(directory / "run-plan.json")
    old._closed(plan, ROLE_PLAN_KEYS, "phase24_role_creation_plan")
    if (plan["version"] != old.VERSION or Path(plan["native_parent"]).resolve(strict=True) != native_parent
            or Path(plan["supplier_parent"]).resolve(strict=True) != supplier_parent
            or plan["source_authority"] != old.AUTHORITY or plan["panel_policy"] != old.PANEL_POLICY
            or any(plan[key] is not False for key in old.POLICY_FALSE)):
        raise ValueError("phase24_registered_parents_or_policy_mismatch")
    old._protect_map(hashes, plan["inputs"])
    old._protect_map(hashes, plan["code"])
    changed = old._guard(hashes)
    if changed:
        raise ValueError("registered_phase24_creation_hash_changed:" + repr(changed))
    return directory, report, plan


def load_inputs(native_parent, supplier_parent, role_parent, *, max_contexts=2):
    """Read all five saved source-size records, no native cold/session replay."""
    old._limit(max_contexts, "max_contexts")
    if max_contexts > 2:
        raise ValueError("at_most_two_registered_source_size_contexts_required")
    native_parent, supplier_parent = (Path(path).resolve(strict=True) for path in (native_parent, supplier_parent))
    raw_rows = old._read(native_parent / "context-index.json")
    if type(raw_rows) is not list or len(raw_rows) != 5:
        raise ValueError("exact_five_registered_context_pool_required")
    contexts, hashes, inventories, manifest = [], {}, {}, []
    for position in range(len(raw_rows)):
        data = old.load_inputs(native_parent, supplier_parent, context_position=position)
        old._protect_map(hashes, data["hashes"])
        for directory, inventory in data["inventories"].items():
            if directory in inventories and inventories[directory] != inventory:
                raise ValueError("registered_parent_inventory_changed_between_source_reads")
            inventories[directory] = inventory
        scope, row = data["scope"], data["row"]
        points = native._points(scope)
        old._limit(row["native_counts"]["materialized_origins"], "registered_native_origin_count")
        if len(points) != row["native_counts"]["observed_cut_coordinates"] + 2:
            raise ValueError("registered_observed_source_coordinate_count_mismatch")
        entry = {"context_position": position, "context_key": deepcopy(row["context_key"]),
            "observed_coordinate_count": len(points), "source_sound_count": len(scope["sound_facts"]),
            "registered_raw_lane_count": len(scope["raw_lanes"]),
            "registered_interval_catalogs": row["native_counts"]["stored_interval_catalogs"],
            "registered_native_origin_variants": row["native_counts"]["materialized_origins"],
            "previous_context_elapsed_seconds_not_runtime_prediction": row["elapsed_seconds"],
            "full_IR": deepcopy(data["ir_info"]), "scope": deepcopy(data["scope_info"]),
            "registered_parent_row_sha256": digest(row), "selected_for_new_execution": False}
        manifest.append(entry)
        contexts.append(data)
    order = sorted(range(len(contexts)), key=lambda pos: (
        manifest[pos]["observed_coordinate_count"], manifest[pos]["source_sound_count"],
        tuple(manifest[pos]["context_key"])))
    selected_positions = order[:max_contexts]
    for position in selected_positions:
        manifest[position]["selected_for_new_execution"] = True
    directory, report, plan = _register_role_parent(role_parent, native_parent, supplier_parent, hashes, inventories)
    return {"native_parent": native_parent, "supplier_parent": supplier_parent, "role_parent": directory,
        "role_report": report, "role_plan": plan, "contexts": contexts, "manifest": manifest,
        "selected_positions": selected_positions, "hashes": hashes, "inventories": inventories}


def _batches(selectors):
    if type(selectors) is not list:
        raise ValueError("ordered_source_panel_selector_list_required")
    return [deepcopy(selectors[start:start + 3]) for start in range(0, len(selectors), 3)]


def _validate_panel_record(panel, lattice, scope, settings):
    sealed._check(panel, panel_engine.PREFIX)
    old._closed(panel["summary"], PANEL_INTEGER_FIELDS | PANEL_NULLABLE_FIELDS | PANEL_BOUND_FIELDS, "source_panel_summary")
    summary = panel["summary"]
    for name in PANEL_INTEGER_FIELDS:
        old._limit(summary[name], "source_panel." + name)
    held = panel["status"] == "whole_source_panel_hold"
    if panel["status"] not in ("whole_source_panel_hold", "computed_source_evidence_panel_not_selected"):
        raise ValueError("closed_source_panel_status_required")
    for name in PANEL_BOUND_FIELDS:
        if summary[name] is None:
            if not held:
                raise ValueError("unknown_panel_bounds_require_whole_hold")
        else:
            old._limit(summary[name], "source_panel." + name)
    for name in PANEL_NULLABLE_FIELDS:
        if held:
            if summary[name] is not None:
                raise ValueError("whole_panel_hold_requires_null_evaluation_counts")
        else:
            old._limit(summary[name], "source_panel." + name)
    if (panel["version"] != panel_engine.VERSION or panel["policy"] != panel_engine.POLICY
            or panel["scope_ref"] != sealed._ref(scope) or panel["lattice_ref"] != sealed._ref(lattice)
            or panel["logical_universe"] != lattice["universe"]
            or panel["native_request"] != {key: lattice[key] for key in ("status", "reasons", "resource_limits")}
            or panel["resource_limits"] != {key: settings[key] for key in ("max_selectors", "selection_work_budget")}
            or any(value is not False for value in panel["flags"].values())
            or any(panel[key] is not None for key in ("selected", "rank", "confidence"))
            or type(panel["selectors"]) is not list or len({digest(selector) for selector in panel["selectors"]}) != len(panel["selectors"])
            or summary["submitted_selectors"] != len(panel["selectors"])
            or summary["planned_selector_upper_bound"] != panel["query_plan"]["selector_upper_bound"]
            or summary["unsubmitted_selector_bound"] != (None if summary["planned_selector_upper_bound"] is None else
                summary["planned_selector_upper_bound"] - len(panel["selectors"]))
            or (held and panel["selectors"])
            or (not held and summary["evaluated_origin_occurrences"] !=
                summary["eligible_origin_occurrences"] + summary["rejected_origin_occurrences"])):
        raise ValueError("exact_source_panel_reference_summary_or_whole_hold_required")


def _sample_occurrences(explanation, comparison, scope, context_key, ir_info, ir, origins):
    """All saved candidate occurrences; samples are bounded later, not winners."""
    sounds = {sound["sound_ref"]: sound for sound in scope["sound_facts"]}
    notes = {note["note_id"]: note for note in ir.get("note_events", [])}
    measures = {measure["measure_id"]: measure for measure in ir.get("measures", [])}
    source_refs = {ref["source_ref_id"]: ref for ref in ir.get("source_references", [])}
    result = []
    for path in explanation["paths"]:
        for clause in path["clauses"]:
            if clause["status"] not in ("supported", "failed"):
                continue
            snapshots = []
            for sound_ref in clause["sound_refs"]:
                sound = sounds[sound_ref]
                snapshots.append({key: deepcopy(sound[key]) for key in (
                    "sound_ref", "source_note_refs", "pitch", "span", "lane", "attack_note_ref", "tie_chain_ref")})
                snapshots[-1]["full_sounding_duration_quarters"] = q(f(sound["span"]["end"]) - f(sound["span"]["start"]))
            note_snapshots = []
            for note_id in clause["source_note_refs"]:
                note = notes.get(note_id)
                if note is None:
                    raise ValueError("case_source_note_not_in_registered_full_IR:" + note_id)
                measure = measures.get(note["measure_id"])
                display = None
                if measure is not None:
                    meter = measure.get("time_signature")
                    beat_type = None if meter is None else meter.get("beat_type")
                    display = {"measure_id": note["measure_id"],
                        "printed_measure_number": measure["printed_measure_number"],
                        "sequential_measure_index": measure["sequential_measure_index"],
                        "notated_denominator_beat_1_based": None if type(beat_type) is not int or beat_type <= 0 else
                            q(1 + f(note["onset_in_measure"]) * beat_type / 4),
                        "meter": deepcopy(meter), "compound_grouping_not_inferred": True}
                note_snapshots.append({"note_id": note_id,
                    "written_pitch": deepcopy(note["written_pitch"]),
                    "global_onset_quarter": deepcopy(note["global_onset_quarter"]),
                    "onset_in_measure": deepcopy(note["onset_in_measure"]),
                    "notated_duration_quarter": deepcopy(note["notated_duration_quarter"]),
                    "source_ref_id": note["source_ref_id"],
                    "source_reference": deepcopy(source_refs.get(note["source_ref_id"])), "display": display})
            result.append({"role": clause["role"], "status": clause["status"], "geometry_id": clause["geometry_id"],
                "context_key": deepcopy(context_key), "full_IR": deepcopy(ir_info),
                "original_source_files": deepcopy(ir["source_files"]), "scope_ref": sealed._ref(scope),
                "sound_snapshots": snapshots, "notated_note_snapshots": note_snapshots,
                "source_note_refs": deepcopy(clause["source_note_refs"]),
                "full_sound_spans": deepcopy(clause["full_sound_spans"]),
                "actual_required_links": deepcopy(clause["actual_required_links"]),
                "boundary_time": deepcopy(clause.get("boundary_time")),
                "candidate_occurrence": {"origin_refs": deepcopy(clause["origin_refs"]),
                    "prerequisites": deepcopy(clause["prerequisites"]),
                    "failed_prerequisites": deepcopy(clause["failed_prerequisites"]),
                    "blockers": deepcopy(clause["blockers"]), "conditional_credit_clips": deepcopy(clause["clips"]),
                    "candidate_spellings": [{"origin_ref": deepcopy(ref),
                        **{name: deepcopy(origins[ref["record_id"]][name]) for name in ("root", "members", "span", "blockers")}}
                        for ref in clause["origin_refs"]],
                    "key_ref": deepcopy(path["key_ref"]), "bundle_ref": deepcopy(path["bundle_ref"]),
                    "native_comparison_ref": sealed._ref(comparison), "explanation_ref": sealed._ref(explanation),
                    "role_path_ref": sealed._ref(path), "role_clause_ref": sealed._ref(clause),
                    "partition": deepcopy(path["partition"]),
                    "whole_ordinary_template_satisfied": clause.get("whole_ordinary_template_satisfied")}})
    return result


def _case_samples(occurrences):
    by_geometry = {}
    for row in occurrences:
        source_identity = digest([row["context_key"], row["full_IR"], row["scope_ref"]])
        key = (row["role"], row["geometry_id"], row["status"], source_identity)
        if key not in by_geometry:
            by_geometry[key] = {key: deepcopy(value) for key, value in row.items() if key != "candidate_occurrence"}
            by_geometry[key]["candidate_occurrences"] = []
        by_geometry[key]["candidate_occurrences"].append(deepcopy(row["candidate_occurrence"]))
    kept, slots = [], Counter()
    for key, row in sorted(by_geometry.items()):
        role, _, status, _ = key
        if slots[(role, status)] >= 3:
            continue
        kept.append(row)
        slots[(role, status)] += 1
    return {"version": VERSION, "selection_policy": "first_geometry_and_exact_source_identity_per_role_status_max_three_not_accuracy_or_winners",
        "eligible_candidate_occurrences": len(occurrences), "distinct_eligible_role_geometry_status": len(by_geometry),
        "saved_samples": len(kept), "withheld_distinct_eligible_role_geometry_status": len(by_geometry) - len(kept),
        "saved_sample_counts_by_role_status": {role + ":" + status: count for (role, status), count in sorted(slots.items())},
        "cases": kept, "musical_accuracy_evaluated": False, "NCT_confirmed": False, "training_eligible": False,
        "all_source_notes_reconstructable_from_registered_full_IR": True}


def _summary(rows, sample_record):
    successful = [row for row in rows if row["status"] == "source_evidence_probe_saved_not_selected"]
    totals, unknown_totals, roles_by_status, role_subtotals, role_occurrences = Counter(), Counter(), Counter(), Counter(), Counter()
    fields = ("planned_structural_selector_occurrences", "submitted_selector_occurrences", "computed_selector_occurrences",
        "distinct_origin_path_keys", "distinct_completion_origin_path_keys", "complete_all_lane_bundles",
        "withheld_all_lane_bundles", "whole_comparison_holds", "whole_explanation_holds", "computed_role_paths",
        "evaluated_clause_occurrences", "raw_time_conserved_role_paths")
    fields = (*fields, "computed_distinct_origin_key_function_path_tuples",
        "computed_distinct_same_completion_logical_tuples", "computed_distinct_key_hypotheses",
        "unique_role_geometries", "unique_role_geometry_statuses", "assessed_role_account_occurrences",
        "unknown_role_account_occurrences", "uncomputed_role_account_occurrences")
    for row in successful:
        counts = row["counts"]
        for key in fields:
            if counts[key] is None:
                unknown_totals[key] += 1
            else:
                old._limit(counts[key], key)
                totals[key] += counts[key]
        roles_by_status.update(counts["role_status_occurrences"])
        role_subtotals.update(counts["role_summary_occurrence_subtotals"])
        role_occurrences.update(counts["role_clause_occurrences"])
    return {"saved_contexts": len(successful), "failed_contexts": len(rows) - len(successful),
        "context_occurrence_subtotals": {key: None if unknown_totals[key] else totals[key] for key in fields},
        "unknown_occurrence_denominator_contexts": dict(unknown_totals),
        "role_status_occurrences": dict(roles_by_status), "role_integer_occurrence_subtotals": dict(role_subtotals),
        "role_clause_occurrences": dict(role_occurrences), "whole_panel_holds": sum(
            row["panel"] is not None and row["panel"]["status"] != "computed_source_evidence_panel_not_selected" for row in rows),
        "planned_batch_upper_bound_occurrences": None if any(row.get("planned_batch_upper_bound_per_completion") is None
            for row in rows) else sum(row["planned_batch_upper_bound_per_completion"] * row["actual_completion_requests"] for row in rows),
        "submitted_batch_occurrences": sum(sum(entry.get("saved_batches", 0) for entry in row["completion_batches"]) for row in rows),
        "unsubmitted_selector_upper_bound_occurrences": None if any(row.get("unsubmitted_selector_upper_bound_per_completion") is None
            for row in rows) else sum(row["unsubmitted_selector_upper_bound_per_completion"] * row["actual_completion_requests"] for row in rows),
        "conditional_explained_note_time_selector_occurrence_sum": None if (
            totals["unknown_role_account_occurrences"] + totals["uncomputed_role_account_occurrences"]) else q(sum((
            f(row["counts"]["known_conditional_explained_note_time_selector_occurrence_subtotal"]) for row in successful), start=f(q(0)))),
        "known_conditional_explained_note_time_selector_occurrence_subtotal": q(sum((
            f(row["counts"]["known_conditional_explained_note_time_selector_occurrence_subtotal"]) for row in successful), start=f(q(0)))),
        "case_sample_counts": {key: deepcopy(sample_record[key]) for key in (
            "eligible_candidate_occurrences", "distinct_eligible_role_geometry_status", "saved_samples",
            "withheld_distinct_eligible_role_geometry_status", "saved_sample_counts_by_role_status")}}


def run(native_parent, supplier_parent, role_parent, output, *, max_contexts=2, **limits):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("append_only_new_direct_workspace_output_required")
    old._limit(max_contexts, "max_contexts")
    if max_contexts > 2 or set(limits) - set(SETTINGS):
        raise ValueError("closed_bounded_source_evidence_trial_settings_required")
    settings = {**SETTINGS, **limits}
    for key, value in settings.items():
        old._limit(value, key)
    if (settings["max_selectors"] > 64 or settings["max_hypotheses"] > 3
            or settings["max_slots"] > 3 or settings["max_greedy_links"] > 20):
        raise ValueError("bounded_source_evidence_selectors_and_batches_required")
    data = load_inputs(native_parent, supplier_parent, role_parent, max_contexts=max_contexts)
    inputs = deepcopy(data["hashes"])
    code = {str(path.resolve()): old._file_sha(path) for path in _code_paths()}
    protected = deepcopy(inputs)
    old._protect_map(protected, code)
    selected = [data["contexts"][position] for position in data["selected_positions"]]
    plan0 = data["contexts"][0]["plan"]
    selected_keys = {tuple(case["row"]["context_key"]) for case in selected}
    selected_units = [unit for unit in plan0["declared_units"] if tuple(unit["context_key"]) in selected_keys]
    denominators = {"declared_contexts": len(plan0["declared_contexts"]),
        "declared_original_raw_lanes": len(plan0["declared_units"]), "registered_context_pool": len(data["contexts"]),
        "selected_contexts": len(selected), "selected_original_raw_lanes": len(selected_units),
        "unexecuted_declared_contexts": len(plan0["declared_contexts"]) - len(selected),
        "unexecuted_declared_original_raw_lanes": len(plan0["declared_units"]) - len(selected_units)}
    before = {tuple(case["row"]["context_key"]): digest([case["ir"], case["scope"]]) for case in data["contexts"]}
    plan = {"version": VERSION, "native_parent": str(data["native_parent"]), "supplier_parent": str(data["supplier_parent"]),
        "role_parent": str(data["role_parent"]), "inputs": inputs, "code": code, "settings": settings,
        "max_contexts": max_contexts, "selection_policy": SELECTION_POLICY,
        "source_size_manifest": data["manifest"], "selected_contexts": [deepcopy(case["row"]["context_key"]) for case in selected],
        "denominators": denominators, "source_authority": AUTHORITY, "selector_batch_size": 3,
        "all_batches_for_both_completions_planned": True, "selected": None, **{key: False for key in POLICY_FALSE}}
    output.mkdir()
    artifacts, rows, failures, occurrences, preparations = {}, [], [], [], 0
    old._save_json(output, "run-plan.json", plan, artifacts)
    for case in selected:
        key, ir, scope = case["row"]["context_key"], case["ir"], case["scope"]
        lattice_info, panel_info, entries, comparisons, explanations, bundles = None, None, [], [], [], []
        case_occurrences = []
        print("SOURCE EVIDENCE CONTEXT START", key[0], flush=True)
        try:
            preparations += 1
            session = native.prepare_lattice(ir, scope, **{key: settings[key] for key in native.DEFAULTS})
            lattice = native.lattice_prepared(session)  # One detached lattice copy/save per context.
            origins = {origin["record_id"]: origin for entry in lattice["catalog_inventory"] for origin in entry["origins"]}
            lattice_info = old._save_record(output, "lattices", lattice, native.PREFIX, artifacts)
            panel_handle = panel_engine.prepare_panel(session)
            panel = panel_engine.panel_prepared(panel_handle, max_selectors=settings["max_selectors"],
                                               selection_work_budget=settings["selection_work_budget"])
            _validate_panel_record(panel, lattice, scope, settings)
            panel_info = old._save_record(output, "panels", panel, panel_engine.PREFIX, artifacts)
            batches = _batches(panel["selectors"])
            requests = [("all_no_link_control", [])]
            links = old.native_trial.greedy_links(scope, settings["max_greedy_links"])
            if links:
                requests.append(("bounded_same_raw_lane_greedy_technical_probe", links))
            else:
                entries.append({"kind": "bounded_same_raw_lane_greedy_technical_probe",
                    "status": "no_admissible_links_no_duplicate_control", "reasons": ["no_greedy_probe_links"]})
            for kind, links in requests:
                bundle = native.compile_bundle_prepared(session, links, geometry_work_budget=settings["geometry_work_budget"])
                bundles.append(bundle)
                bundle_info = old._save_record(output, "bundles", bundle, native.BUNDLE_PREFIX, artifacts)
                batch_entries = []
                for batch_index, selectors in enumerate(batches):
                    comparison = native.compare_prepared(session, selectors, bundle["record_id"],
                        max_hypotheses=settings["max_hypotheses"], max_slots=settings["max_slots"],
                        query_work_budget=settings["native_query_work_budget"])
                    handle = roles.prepare_explanations(session, comparison)
                    explanation = roles.explain_prepared(handle, query_work_budget=settings["role_query_work_budget"])
                    old._validate_role_summary(explanation, comparison)
                    if (comparison["bundle_ref"] != sealed._ref(bundle) or comparison["lattice_ref"] != sealed._ref(lattice)
                            or comparison["selectors"] != selectors or explanation["native_comparison_ref"] != sealed._ref(comparison)
                            or explanation["bundle_ref"] != sealed._ref(bundle) or explanation["scope_ref"] != sealed._ref(scope)
                            or explanation["lattice_ref"] != sealed._ref(lattice)
                            or explanation["native_request"] != {key: comparison[key] for key in (
                                "selectors", "resource_limits", "status", "reasons", "summary", "query_plan")}):
                        raise ValueError("same_completion_ordered_batch_native_role_reference_mismatch")
                    comparisons.append(comparison); explanations.append(explanation)
                    case_occurrences.extend(_sample_occurrences(explanation, comparison, scope, key, case["ir_info"], ir, origins))
                    batch_entries.append({"batch_index": batch_index, "selector_start": batch_index * 3,
                        "selector_end_exclusive": batch_index * 3 + len(selectors), "selectors": deepcopy(selectors),
                        "comparison": old._save_record(output, "comparisons", comparison, native.COMPARISON_PREFIX, artifacts),
                        "explanation": old._save_record(output, "explanations", explanation, roles.PREFIX, artifacts),
                        "native_summary": deepcopy(comparison["summary"]), "role_summary": deepcopy(explanation["summary"]),
                        "native_query_plan": deepcopy(comparison["query_plan"]), "role_query_plan": deepcopy(explanation["query_plan"]),
                        "status": explanation["status"], "reasons": deepcopy(explanation["reasons"])})
                entries.append({"kind": kind, "bundle": bundle_info, "required_links": deepcopy(links),
                    "planned_batches": len(batches), "saved_batches": len(batch_entries), "batches": batch_entries})
            if digest([ir, scope]) != before[tuple(key)]:
                raise ValueError("registered_source_changed_during_source_evidence_trial")
            counts = old._counts(lattice, {"planned_selectors": len(panel["selectors"])},
                                 bundles, comparisons, explanations)
            upper = panel["summary"]["planned_selector_upper_bound"]
            counts["planned_structural_selector_occurrences"] = None if upper is None else upper * len(bundles)
            native_paths = [path for comparison in comparisons for path in comparison["paths"]]
            role_paths = [path for explanation in explanations for path in explanation["paths"]]
            clauses = [clause for path in role_paths for clause in path["clauses"]]
            unknown_accounts = sum(path["account"]["conditional_explanation_note_time_quarters"] is None for path in role_paths)
            uncomputed_accounts = sum(explanation["summary"]["withheld_paths"] for explanation in explanations)
            known_credit = q(sum((f(path["account"]["conditional_explanation_note_time_quarters"])
                for path in role_paths if path["account"]["conditional_explanation_note_time_quarters"] is not None), start=f(q(0))))
            counts.update({"assessed_role_account_occurrences": len(role_paths) - unknown_accounts,
                "unknown_role_account_occurrences": unknown_accounts,
                "uncomputed_role_account_occurrences": uncomputed_accounts,
                "conditional_explained_note_time_selector_occurrence_sum": None if unknown_accounts + uncomputed_accounts else deepcopy(known_credit),
                "known_conditional_explained_note_time_selector_occurrence_subtotal": known_credit})
            counts.update({"computed_distinct_origin_key_function_path_tuples": len({digest([
                    path["origin_refs"], path["key_ref"], path["logical_tuple"]["transition_assumptions"]]) for path in native_paths}),
                "computed_distinct_same_completion_logical_tuples": len({digest([
                    path["origin_refs"], path["key_ref"], path["logical_tuple"]["transition_assumptions"], path["bundle_ref"]]) for path in native_paths}),
                "computed_distinct_key_hypotheses": len({digest(path["key_ref"]) for path in native_paths}),
                "unique_role_geometries": len({clause["geometry_id"] for clause in clauses}),
                "unique_role_geometry_statuses": len({(clause["geometry_id"], clause["status"]) for clause in clauses})})
            occurrences.extend(case_occurrences)
            rows.append({"context_key": deepcopy(key), "full_IR": case["ir_info"], "scope": case["scope_info"],
                "native_lattice": lattice_info, "panel": panel_info, "panel_summary": deepcopy(panel.get("summary")),
                "panel_query_plan": deepcopy(panel["query_plan"]), "selected_selectors": deepcopy(panel["selectors"]),
                "batch_count_per_completion": len(batches), "completion_batches": entries, "counts": counts,
                "planned_batch_upper_bound_per_completion": None if upper is None else (upper + 2) // 3,
                "unsubmitted_selector_upper_bound_per_completion": panel["summary"]["unsubmitted_selector_bound"],
                "actual_completion_requests": len(requests),
                "status": "source_evidence_probe_saved_not_selected", "error": None})
        except Exception as exc:
            error = f"{type(exc).__name__}:{exc}"
            failures.append({"context_key": deepcopy(key), "error": error})
            rows.append({"context_key": deepcopy(key), "full_IR": case["ir_info"], "scope": case["scope_info"],
                "native_lattice": lattice_info, "panel": panel_info, "completion_batches": entries,
                "counts": None, "status": "calculation_failure", "error": error})
        print("SOURCE EVIDENCE CONTEXT DONE", key[0], rows[-1]["status"], flush=True)
    old._save_json(output, "context-index.json", rows, artifacts)
    samples = _case_samples(occurrences)
    old._save_json(output, "case-samples.json", samples, artifacts)
    changed = old._guard(protected)
    if {str(path.resolve()) for path in _code_paths()} != set(code):
        changed.append("creation_code_inventory_changed")
    for directory, inventory in data["inventories"].items():
        if {str(path.resolve()) for path in Path(directory).rglob("*") if path.is_file()} != inventory:
            changed.append("registered_parent_artifact_inventory_changed:" + directory)
    for case in data["contexts"]:
        if before[tuple(case["row"]["context_key"])] != digest([case["ir"], case["scope"]]):
            changed.append("registered_full_IR_scope_changed:" + repr(case["row"]["context_key"]))
    changed_artifacts = old._guard(artifacts)
    if {str(path.resolve()) for path in output.rglob("*") if path.is_file()} != set(artifacts):
        changed_artifacts.append("new_artifact_inventory_changed")
    integrity = not failures and not changed and not changed_artifacts
    report = {"version": VERSION, "status": "source_evidence_probe_complete_not_selected" if integrity else
        "source_evidence_probe_failed", "computation_integrity_passed": integrity,
        "inputs_and_code_unchanged": not changed, "artifacts_unchanged": not changed_artifacts,
        "changed_inputs_or_code": changed, "changed_artifacts": changed_artifacts, "failures": failures,
        "artifact_hashes": artifacts, "denominators": denominators, "fresh_native_preparations": preparations,
        "summary": _summary(rows, samples) if integrity else None, "source_authority": AUTHORITY, "selected": None,
        "submitted_role_calculation_complete": bool(integrity and rows
            and any(entry.get("saved_batches", 0) for row in rows for entry in row["completion_batches"])
            and all(
            row["panel"]["status"] == "computed_source_evidence_panel_not_selected"
            and row["counts"]["unknown_role_account_occurrences"] == 0
            and row["counts"]["uncomputed_role_account_occurrences"] == 0
            and all(batch["status"] == "computed_native_role_explanations_not_selected"
                    for entry in row["completion_batches"] for batch in entry.get("batches", [])) for row in rows)),
        "elapsed_seconds": perf_counter() - started, **{key: False for key in POLICY_FALSE},
        "limits": ["Two source-size-selected registered contexts at most, not the full five-context pool or 322-context cohort.",
            "Source guards/contours/carries and candidate premises are conditional evidence, not gold or final NCT/harmony labels.",
            "Every ordered selector batch is submitted to both actual completion controls; whole resource holds are not dropped.",
            "Case samples are bounded first geometry/source identity per role/status; distinct sample geometries never merge different IR/scope/context sources.",
            "All accounts preserve raw note time within one path/completion; aggregate note time counts selector occurrences.",
            "Unknown or uncomputed submitted completion accounts leave the credit aggregate null, with separate known subtotals and occurrence counts.",
            "Old native/role outputs were protected metadata, not cold replayed authority; no production/UI change occurred."]}
    storage.write_new(output / "report.json", report)
    print("SOURCE EVIDENCE PROBE DONE", report["status"], f"{report['elapsed_seconds']:.3f}s", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("native-parent", "supplier-parent", "role-parent", "output"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--max-contexts", type=int, default=2)
    args = parser.parse_args()
    run(args.native_parent, args.supplier_parent, args.role_parent, args.output, max_contexts=args.max_contexts)


if __name__ == "__main__":
    main()
