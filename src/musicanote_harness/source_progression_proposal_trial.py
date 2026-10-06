"""Append-only saved-source proposal probe, never a native replay or winner.

Complete archived origin inventories are admitted once per exact source context.
The proposed selectors and a separate later fresh-replay manifest are saved;
no old producer, path, role predicate or native session is executed here.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from itertools import product
from pathlib import Path
from time import perf_counter

from . import native_progression_policy_trial as parent
from . import source_progression_proposals as engine
from .musical_pattern_observation import digest, f

old, sealed = parent.old, parent.sealed
ROOT = parent.ROOT
VERSION = "source-progression-proposal-trial-0.1.0"
AUTHORITY = parent.AUTHORITY
SETTINGS = {"work_budget": 3000000, "max_paths": 512, "max_selectors": 4096,
    "max_contexts": 2, "max_origins": 200000, "max_catalogs": 1024,
    "max_file_bytes": 67108864, "max_decoded_file_bytes": 268435456,
    "max_total_decoded_bytes": 1073741824, "max_output_record_bytes": 67108864}
POLICY_FALSE = (*parent.POLICY_FALSE, "policy_producer_replayed", "source_proposal_is_final_harmony",
    "native_replay_executed", "all_cartesian_paths_evaluated")
REPORT_KEYS = (parent.REPORT_KEYS - {"whole_contrast_holds"}) | {
    "whole_policy_holds", "submitted_policy_evaluation_complete", "known_computed_summary_subtotal",
    "unknown_summary_completion_occurrences", "parent_contrast_summary", *parent.POLICY_FALSE}
PLAN_KEYS = {"version", "parent", "inputs", "code", "settings", "denominators", "parent_report_sha256",
    "parent_inventories", "parent_source_size_manifest", "parent_selected_contexts", "parent_contrast_summary",
    "reader_counts", "source_authority", "all_saved_alternatives_retained", "fresh_native_preparations",
    "selected", *parent.POLICY_FALSE}
ROW_KEYS = parent.ROW_KEYS | {"parent_summary", "policy"}
RESULT_KEYS = {"version", "source_authority", "contract", "rules", "scope_ref", "lattice_ref",
    "prior_panel_ref", "binding", "analysis_span", "logical_universe", "resource_limits", "query_plan",
    "intervals", "partitions", "complete_proposal_paths", "shape_request_groups", "selector_aliases",
    "retained_control_selectors", "additional_selectors", "selectors", "summary", "status", "reasons",
    "flags", "selected", "rank", "confidence", "native_replay_status", "limitations", "record_id", "record_sha256"}
PLAN_COUNT_FIELDS = {"input_visit_work", "source_scan_and_sort_work"}
PLAN_NULLABLE_FIELDS = {"path_shape_vector_work", "planned_work"}
KNOWN_SUMMARY_FIELDS = {"requested_intervals", "retained_control_selectors"}
PROPOSAL_KEYS = {"origin_ref", "eligible", "reasons", "missing_guarded_member_spellings",
    "guarded_pooled_member_note_time", "guarded_root_note_time", "raw_note_time_by_support",
    "member_sound_evidence", "root", "members", "source_ornaments_used", "source_annotation_labels_used",
    "simultaneous_core_certified", "selected", "confidence"}
INTERVAL_KEYS = {"catalog_id", "point_indices", "span", "native_origins", "eligible_origins",
    "rejected_origins", "rejection_reason_occurrences", "distinct_eligible_spelling_signatures",
    "bucket_representatives", "proposals", "proposal_count", "omitted_eligible_origins"}
PARTITION_KEYS = {"partition_kind", "point_indices", "proposed_paths", "eligible_cartesian_origin_paths",
    "omitted_eligible_cartesian_origin_paths", "status"}
PATH_KEYS = {"partition_kind", "point_indices", "origin_ids", "origin_refs", "proposal_provenance"}
CUT_KEYS = {"source_origin_ref", "target_origin_ref", "same_spelling_signature", "checked_shapes",
    "request_options", "resolution_support", "secondary_support", "boundary_support", "same_completion_ref"}
SHAPE_KEYS = {"assumption", "source_shape_compatible", "target_shape_compatible", "shape_request_eligible",
    "function_kind_under_key", "key_projection", "blockers"}


def _strings(value, name):
    if type(value) is not list or any(type(s) is not str or not s for s in value):
        raise ValueError("typed_string_list_required:" + name)


def _rational(value, name):
    old._closed(value, {"numerator", "denominator"}, name)
    if (type(value["numerator"]) is not int or type(value["denominator"]) is not int
            or value["denominator"] <= 0):
        raise ValueError("exact_rational_required:" + name)
    return f(value)


def _pitch(value, name):
    old._closed(value, {"step", "alter"}, name)
    if value["step"] not in tuple("CDEFGAB"):
        raise ValueError("written_pitch_step_required:" + name)
    _rational(value["alter"], name + ".alter")


def _shape(value, assumption):
    """Typed saved declarations and conjunction, never rerun function inference."""
    old._closed(value, SHAPE_KEYS, "saved_shape_declaration")
    if value["assumption"] != assumption:
        raise ValueError("all_ordered_family_quality_declarations_required")
    for field in ("source_shape_compatible", "target_shape_compatible"):
        if value[field] is not None and type(value[field]) is not bool:
            raise ValueError("strict_tristate_shape_declaration_required")
    expected = value["source_shape_compatible"] is True and value["target_shape_compatible"] is True
    if type(value["shape_request_eligible"]) is not bool or value["shape_request_eligible"] is not expected:
        raise ValueError("shape_eligibility_requires_both_exact_true_declarations")
    if value["function_kind_under_key"] not in ("primary", "parallel", "applied", "unassessed"):
        raise ValueError("typed_declared_function_kind_required")
    _strings(value["blockers"], "shape.blockers")
    projection = value["key_projection"]
    old._closed(projection, {"target_coordinate", "chromatic_source_members", "unassessed_reasons",
        "chromatic_is_not_applied_function_proof", "scale_form_is_not_motion_direction_rule"}, "saved_key_projection")
    if (projection["chromatic_is_not_applied_function_proof"] is not True
            or projection["scale_form_is_not_motion_direction_rule"] is not True):
        raise ValueError("shape_projection_not_function_proof_required")
    _strings(projection["unassessed_reasons"], "projection.reasons")
    chromatic = projection["chromatic_source_members"]
    if chromatic is not None:
        if type(chromatic) is not list:
            raise ValueError("typed_chromatic_pitch_list_required")
        for pitch in chromatic:
            _pitch(pitch, "projection.chromatic_pitch")
    coordinate = projection["target_coordinate"]
    if coordinate is not None:
        old._closed(coordinate, {"degree", "alteration_from_scale", "diatonic_to_candidate", "candidate",
            "basis", "key_inferred"}, "saved_scale_coordinate")
        if (type(coordinate["degree"]) is not int or not 1 <= coordinate["degree"] <= 7
                or type(coordinate["alteration_from_scale"]) is not int
                or type(coordinate["diatonic_to_candidate"]) is not bool
                or coordinate["basis"] != "conditional_scale_coordinate" or coordinate["key_inferred"] is not False):
            raise ValueError("typed_conditional_scale_coordinate_required")
        candidate = coordinate["candidate"]
        old._closed(candidate, {"tonic_step", "tonic_alter", "mode"}, "saved_scale_candidate")
        if (candidate["tonic_step"] not in tuple("CDEFGAB") or type(candidate["tonic_alter"]) is not int
                or candidate["mode"] not in engine.kernels.tonal.SCALES):
            raise ValueError("typed_explicit_scale_candidate_required")


def _literal_signature(origin):
    """Literal octave-insensitive spelling only, not candidate/function inference."""
    pitches = [origin["root"], *(origin["members"] or ())]
    if origin["root"] is None or not origin["members"]:
        return None
    values = []
    for pitch in pitches:
        if type(pitch) is not dict or pitch.get("step") not in tuple("CDEFGAB"):
            return None
        try:
            alter = f(pitch["alter"])
        except (KeyError, TypeError, ValueError):
            return None
        if alter.denominator != 1:
            return None
        values.append((pitch["step"], alter))
    return values[0], tuple(sorted(set(values[1:])))


def _settings(limits):
    if set(limits) - set(SETTINGS):
        raise ValueError("closed_saved_source_proposal_trial_limits_required")
    result = {**SETTINGS, **limits}
    for key, value in result.items():
        old._limit(value, key)
    return result


def _new_code_paths():
    return {Path(__file__).resolve(), Path(engine.__file__).resolve(),
        ROOT / "tests/test_source_progression_proposals.py", ROOT / "tests/test_source_progression_proposal_trial.py"}


def _code_paths():
    return sorted({*parent._code_paths(), *(p for p in _new_code_paths() if p.is_file())})


def _record(info, registration, reader, protected, prefix):
    old._closed(info, parent.parent.INFO_KEYS, "registered_source_proposal_input")
    if registration.get(info["artifact"]) != info["sha256"]:
        raise ValueError("registered_source_proposal_creation_SHA_required")
    return parent.parent._record(info, prefix, reader, protected)


def _source_identity(row):
    return digest({key: row[key] for key in ("context_key", "full_IR", "scope", "native_lattice", "source_panel")})


def _summary_types(summary, held):
    old._closed(summary, parent.SUMMARY_FIELDS, "registered_policy_summary")
    for key in parent.KNOWN_COUNT_FIELDS:
        old._limit(summary[key], "registered_policy_summary." + key)
    for key in parent.NULLABLE_COUNT_FIELDS:
        if held:
            if summary[key] is not None:
                raise ValueError("withheld_registered_policy_counts_are_unknown")
        else:
            old._limit(summary[key], "registered_policy_summary." + key)
    reasons = summary["diagnostic_reason_counts"]
    if held:
        if reasons is not None:
            raise ValueError("withheld_registered_policy_diagnostics_are_unknown")
    elif type(reasons) is not dict or any(type(k) is not str or not k for k in reasons):
        raise ValueError("typed_registered_policy_diagnostic_map_required")
    else:
        for count in reasons.values():
            old._limit(count, "registered_policy_reason_count")


def _policy(record, row, scope, lattice, batches):
    """Validate archived linkage/counts; never recalculate policy predicates."""
    old._closed(record, parent.RESULT_KEYS, "registered_policy_body")
    old._closed(record["flags"], parent.parent.RESULT_FLAGS, "registered_policy_flags")
    held = record["status"] == "whole_saved_policy_hold"
    _summary_types(record["summary"], held)
    if (record["version"] != parent.policy.VERSION or record["source_authority"] != AUTHORITY
            or any(value is not False for value in record["flags"].values())
            or record["status"] not in ("computed_saved_progression_policy_not_selected", "whole_saved_policy_hold")
            or record["parent_contrast_ref"] != row["contrast"]["record_ref"]
            or record["scope_ref"] != sealed._ref(scope) or record["lattice_ref"] != sealed._ref(lattice)
            or record["binding"] != scope["binding"] or record["analysis_span"] != scope["analysis_span"]
            or record["logical_universe"] != lattice["universe"]
            or record["summary"] != row["summary"] or record["query_plan"] != row["query_plan"]
            or record["status"] != row["status"] or record["reasons"] != row["reasons"]
            or any(record[k] is not None for k in ("selected", "rank", "confidence"))):
        raise ValueError("exact_registered_saved_policy_identity_required")
    entries, alternatives = record["submitted_entry_refs"], record["alternatives"]
    if (type(entries) is not list or type(alternatives) is not list or len(entries) != 50
            or len(alternatives) != 50 or record["summary"]["submitted_entries"] != 50
            or record["summary"]["evaluated_entries"] != (0 if held else 50)
            or record["summary"]["withheld_entries"] != (50 if held else 0)):
        raise ValueError("all_fifty_original_policy_controls_required")
    refs, statuses, diagnostics, groups = set(), Counter(), Counter(), defaultdict(list)
    for i, (entry, alternative) in enumerate(zip(entries, alternatives)):
        old._closed(entry, {"native_path_ref", "role_path_ref", "comparison_ref", "explanation_ref"}, "original_policy_entry")
        old._closed(alternative, parent.ALTERNATIVE_KEYS, "original_policy_alternative")
        for value in entry.values():
            parent._ref(value)
        batch = batches[i // 3]
        if (entry["comparison_ref"] != batch["comparison"]["record_ref"]
                or entry["explanation_ref"] != batch["explanation"]["record_ref"]
                or alternative["entry_refs"] != entry
                or any(alternative[k] is not None for k in ("selected", "rank", "confidence"))):
            raise ValueError("ordered_policy_controls_and_batch_refs_required")
        marker = digest(entry["native_path_ref"])
        if marker in refs:
            raise ValueError("duplicate_original_policy_path_ref")
        refs.add(marker)
        if held:
            if (alternative["status"] != "held_whole_request" or alternative["premises"] is not None
                    or alternative["account_pointer"] is not None or alternative["diagnostics"]
                    or alternative["transition_assessments"] or alternative["claim_scope"] != "no_partial_policy_evaluation"):
                raise ValueError("held_policy_control_cannot_claim_assessed_evidence")
        else:
            if (alternative["status"] not in parent.policy.STATUSES
                    or alternative["premises"]["bundle_ref"] != row["bundle"]["record_ref"]):
                raise ValueError("original_policy_control_same_completion_required")
            for diagnostic in alternative["diagnostics"]:
                old._closed(diagnostic, {"rule_id", "reason", "effect", "target"}, "original_policy_diagnostic")
                if type(diagnostic["reason"]) is not str or not diagnostic["reason"]:
                    raise ValueError("typed_original_policy_diagnostic_reason")
                diagnostics[diagnostic["reason"]] += 1
            statuses[alternative["status"]] += 1
            groups[digest(alternative["premises"])].append(i)
    if held:
        if record["fixed_premise_groups"]:
            raise ValueError("whole_parent_policy_hold_no_partial_groups")
    else:
        expected = {"submitted_entries": 50, "evaluated_entries": 50, "withheld_entries": 0,
            "fixed_premise_groups": len(groups), "conditional_function_supported_alternatives": statuses[parent.policy.STATUSES[0]],
            "held_alternatives": statuses[parent.policy.STATUSES[1]],
            "declared_requirement_not_supported_alternatives": statuses[parent.policy.STATUSES[2]],
            "diagnostic_reason_counts": dict(sorted(diagnostics.items()))}
        if record["summary"] != expected or len(record["fixed_premise_groups"]) != len(groups):
            raise ValueError("exact_archived_policy_alternative_count_summary")
        for group, (signature, indices) in zip(record["fixed_premise_groups"], groups.items()):
            old._closed(group, parent.GROUP_KEYS, "original_policy_group")
            if (group["group_id"] != "nppgroup_" + signature[:24] or group["alternative_indices"] != indices
                    or group["premises"] != alternatives[indices[0]]["premises"] or group["selected"] is not None
                    or any(group[name] != [i for i in indices if alternatives[i]["status"] == status]
                        for name, status in (("conditional_support_indices", parent.policy.STATUSES[0]),
                            ("held_indices", parent.policy.STATUSES[1]),
                            ("declared_requirement_not_supported_indices", parent.policy.STATUSES[2])))):
                raise ValueError("exact_archived_policy_fixed_premise_group_inventory")


def _inventory(lattice, panel, scope, settings):
    """Admit every archived origin, not only the old six requested intervals."""
    entries = lattice["catalog_inventory"]
    if type(entries) is not list or len(entries) > settings["max_catalogs"]:
        raise ValueError("whole_saved_catalog_admission_budget_no_prefix")
    origins = [o for entry in entries for o in entry["origins"]]
    if len(origins) > settings["max_origins"]:
        raise ValueError("whole_saved_origin_admission_budget_no_prefix")
    if (panel["summary"]["native_interval_catalogs"] != len(entries)
            or panel["summary"]["native_origins"] != len(origins)
            or ("materialized_origins" in lattice and lattice["materialized_origins"] != len(origins))):
        raise ValueError("exact_all_entry_native_origin_inventory_required")
    indexed = {}
    a, b = f(scope["analysis_span"]["start"]), f(scope["analysis_span"]["end"])
    for origin in origins:
        sealed._check(origin, "fmilorigin_")
        oid = origin["record_id"]
        if oid in indexed or not a <= f(origin["span"]["start"]) < f(origin["span"]["end"]) <= b:
            raise ValueError("unique_positive_registered_origin_required")
        if "source_scope_ref" in origin and origin["source_scope_ref"] != sealed._ref(scope):
            raise ValueError("foreign_registered_origin_scope")
        indexed[oid] = origin
    keys = {key["record_id"]: key for key in lattice["keys"]}
    if len(keys) != len(lattice["keys"]):
        raise ValueError("unique_original_key_inventory_required")
    for selector in panel["selectors"]:
        old._closed(selector, {"origin_ids", "key_id", "transition_assumptions"}, "original_control_selector")
        if (not selector["origin_ids"] or any(oid not in indexed for oid in selector["origin_ids"])
                or selector["key_id"] not in keys
                or len(selector["transition_assumptions"]) != len(selector["origin_ids"]) - 1):
            raise ValueError("complete_original_control_selector_required")
    return {"native_catalogs": len(entries), "native_origins": len(origins), "registered_key_hypotheses": len(keys)}


def load_inputs(directory, **limits):
    """Read registered saved sources, with no predecessor load or replay."""
    settings = _settings(limits)
    directory = Path(directory).resolve(strict=True)
    reader = parent.parent.BoundedReader(settings)
    report_path = directory / "report.json"
    report, plan, rows = (reader.read(directory / name) for name in ("report.json", "run-plan.json", "context-index.json"))
    old._closed(report, REPORT_KEYS, "phase27_saved_report")
    old._closed(plan, PLAN_KEYS, "phase27_saved_plan")
    if (report["version"] != parent.VERSION or plan["version"] != parent.VERSION
            or report["status"] != "saved_progression_policy_probe_complete_not_selected"
            or any(report[k] is not True for k in ("computation_integrity_passed", "inputs_and_code_unchanged", "artifacts_unchanged"))
            or any(report[k] != [] for k in ("changed_inputs_or_code", "changed_artifacts", "failures"))
            or any(report[k] is not False or plan[k] is not False for k in parent.POLICY_FALSE)
            or report["selected"] is not None or plan["selected"] is not None
            or report["source_authority"] != AUTHORITY or plan["source_authority"] != AUTHORITY
            or report["fresh_native_preparations"] != 0 or plan["fresh_native_preparations"] != 0
            or plan["all_saved_alternatives_retained"] is not True
            or type(report["artifact_hashes"]) is not dict or len(report["artifact_hashes"]) != 6
            or report["denominators"] != plan["denominators"]):
        raise ValueError("exact_completed_phase27_saved_creation_required")
    for key in ("fresh_native_preparations", "saved_completion_groups", "computed_completion_groups", "whole_policy_holds"):
        old._limit(report[key], "phase27_report." + key)
    old._limit(plan["fresh_native_preparations"], "phase27_plan.fresh_native_preparations")
    protected = {}
    old._protect_map(protected, plan["inputs"])
    old._protect_map(protected, plan["code"])
    old._protect_map(protected, report["artifact_hashes"])
    old._protect(protected, str(report_path), old._file_sha(report_path))
    inventories = [(directory, old._inventory(directory, report["artifact_hashes"], report_path))]
    historical = {str(p.resolve()) for p in _code_paths()} - {str(p.resolve()) for p in _new_code_paths()}
    if set(plan["code"]) != historical:
        raise ValueError("exact_historical_phase27_creation_code_inventory_required")
    if old._guard(protected):
        raise ValueError("registered_source_proposal_creation_SHA_changed")
    p_dir = Path(plan["parent"]).resolve(strict=True)
    p_report, p_plan, p_rows = (reader.read(p_dir / name) for name in ("report.json", "run-plan.json", "context-index.json"))
    old._closed(p_report, parent.REPORT_KEYS, "phase26_protected_report")
    old._closed(p_plan, parent.PLAN_KEYS, "phase26_protected_plan")
    if protected.get(str(p_dir / "report.json")) != plan["parent_report_sha256"]:
        raise ValueError("phase26_registered_report_SHA_required")
    inventories.append((p_dir, old._inventory(p_dir, p_report["artifact_hashes"], p_dir / "report.json")))
    earlier = Path(p_plan["parent"]).resolve(strict=True)
    e_report, e_plan, e_rows = (reader.read(earlier / name) for name in ("report.json", "run-plan.json", "context-index.json"))
    old._closed(e_report, parent.parent.REPORT_KEYS, "phase25_protected_report")
    old._closed(e_plan, parent.parent.PLAN_KEYS, "phase25_protected_plan")
    inventories.append((earlier, old._inventory(earlier, e_report["artifact_hashes"], earlier / "report.json")))
    if ([len(i) for _, i in inventories] != [7, 7, 148]
            or plan["parent_inventories"] != [{"directory": str(p), "files": len(i)} for p, i in inventories[1:]]):
        raise ValueError("exact_registered_7_7_148_parent_inventories_required")
    for parent_plan, parent_report in ((p_plan, p_report), (e_plan, e_report)):
        for mapping in (parent_plan["inputs"], parent_plan["code"], parent_report["artifact_hashes"]):
            for path, sha in mapping.items():
                if protected.get(path) != sha:
                    raise ValueError("complete_original_creation_SHA_closure_required")
    denoms = report["denominators"]
    old._closed(denoms, parent.parent.DENOMINATOR_KEYS, "source_proposal_original_cohort")
    for value in denoms.values():
        old._limit(value, "original_cohort")
    if (denoms["selected_contexts"] != 2 or denoms["registered_context_pool"] != 5
            or denoms["unexecuted_declared_contexts"] != denoms["declared_contexts"] - 2
            or denoms["unexecuted_declared_original_raw_lanes"] != denoms["declared_original_raw_lanes"] - denoms["selected_original_raw_lanes"]
            or any(x["denominators"] != denoms for x in (p_report, p_plan, e_report, e_plan))
            or plan["parent_source_size_manifest"] != p_plan["parent_source_size_manifest"]
            or plan["parent_source_size_manifest"] != e_plan["source_size_manifest"]
            or plan["parent_selected_contexts"] != e_plan["selected_contexts"]):
        raise ValueError("original_source_selection_and_cohort_must_remain_exact")
    if (type(rows) is not list or type(p_rows) is not list or type(e_rows) is not list
            or len(rows) != 4 or len(p_rows) != 4 or len(e_rows) != 2):
        raise ValueError("all_four_registered_policy_controls_required")
    if len({_source_identity(row) for row in rows}) > settings["max_contexts"]:
        raise ValueError("whole_saved_source_context_admission_no_prefix")
    contexts, by_key, summaries = {}, {}, []
    for row, p_row in zip(rows, p_rows):
        old._closed(row, ROW_KEYS, "phase27_saved_context_index")
        if (row["error"] is not None or row["submitted_entries"] != 50
                or row["parent_summary"] != p_row["summary"]
                or any(row[k] != p_row[k] for k in ("context_key", "kind", "full_IR", "scope", "native_lattice",
                    "source_panel", "original_source_files", "bundle", "saved_batch_refs", "contrast"))):
            raise ValueError("all_exact_original_policy_control_rows_required")
        key, identity = digest(row["context_key"]), _source_identity(row)
        if key in by_key and by_key[key] != identity:
            raise ValueError("same_context_has_conflicting_registered_source_identity")
        by_key[key] = identity
        if identity not in contexts:
            info = row["full_IR"]
            old._closed(info, parent.parent.IR_INFO_KEYS, "registered_full_IR")
            if (protected.get(info["artifact"]) != info["sha256"] or info["binding_match"] is not True
                    or info["registered_full_IR_not_projection"] is not True):
                raise ValueError("registered_full_IR_creation_identity_required")
            ir = reader.read(info["artifact"])
            if ir["ir_document_id"] != info["ir_document_id"] or digest(ir) != info["ir_content_sha256"]:
                raise ValueError("registered_full_IR_content_binding_required")
            scope = _record(row["scope"], protected, reader, protected, old.expanded.PREFIX)
            lattice = _record(row["native_lattice"], protected, reader, protected, parent.parent.parent.native.PREFIX)
            panel = _record(row["source_panel"], protected, reader, protected, parent.parent.parent.panel_engine.PREFIX)
            if (scope["binding"] != old.expanded._binding(ir)
                    or lattice["scope_ref"] != sealed._ref(scope) or lattice["binding"] != scope["binding"]
                    or lattice["analysis_span"] != scope["analysis_span"]
                    or panel["scope_ref"] != sealed._ref(scope) or panel["lattice_ref"] != sealed._ref(lattice)
                    or row["original_source_files"] != ir["source_files"]):
                raise ValueError("exact_original_IR_scope_lattice_panel_binding_required")
            native_counts = _inventory(lattice, panel, scope, settings)
            contexts[identity] = {"context_key": deepcopy(row["context_key"]), "source_identity_sha256": identity,
                "full_IR": deepcopy(info), "scope_info": deepcopy(row["scope"]), "lattice_info": deepcopy(row["native_lattice"]),
                "panel_info": deepcopy(row["source_panel"]), "original_source_files": deepcopy(ir["source_files"]),
                "scope": scope, "lattice": lattice, "panel": panel, "native_counts": native_counts,
                "parent_policy_rows": [], "completion_controls": []}
        case = contexts[identity]
        e_row = next(r for r in e_rows if r["context_key"] == row["context_key"])
        completion = next(c for c in e_row["completion_batches"] if c["kind"] == row["kind"])
        if (case["panel"]["selectors"] != e_row["selected_selectors"]
                or row["bundle"] != completion["bundle"]
                or row["saved_batch_refs"] != [{k: b[k] for k in ("comparison", "explanation")} for b in completion["batches"]]
                or len(row["saved_batch_refs"]) != 17):
            raise ValueError("original_all_key_control_panel_and_completion_batches_required")
        for batch in row["saved_batch_refs"]:
            for info in batch.values():
                old._closed(info, parent.parent.INFO_KEYS, "original_batch_info")
                if protected.get(info["artifact"]) != info["sha256"]:
                    raise ValueError("original_batch_creation_SHA_required")
        policy_record = _record(row["policy"], report["artifact_hashes"], reader, protected, parent.policy.PREFIX)
        _policy(policy_record, row, case["scope"], case["lattice"], row["saved_batch_refs"])
        summaries.append(policy_record["summary"])
        case["parent_policy_rows"].append(deepcopy(row))
        case["completion_controls"].append({"kind": row["kind"], "bundle": deepcopy(row["bundle"]),
            "required_links": deepcopy(completion["required_links"]), "policy": deepcopy(row["policy"]),
            "policy_status": row["status"], "native_and_role_replay_executed": False})
    if len(contexts) != 2 or len(contexts) > settings["max_contexts"]:
        raise ValueError("whole_saved_source_context_admission_no_prefix")
    if any(len(case["parent_policy_rows"]) != 2 for case in contexts.values()):
        raise ValueError("both_original_completion_controls_required")
    combined, known, unknown = parent._aggregate(summaries)
    if (report["summary"] != combined or report["known_computed_summary_subtotal"] != known
            or report["unknown_summary_completion_occurrences"] != unknown
            or report["saved_completion_groups"] != 4
            or report["computed_completion_groups"] != sum(row["status"] == "computed_saved_progression_policy_not_selected" for row in rows)
            or report["whole_policy_holds"] != sum(row["status"] == "whole_saved_policy_hold" for row in rows)
            or sum(len(c["scope"]["raw_lanes"]) for c in contexts.values()) != denoms["selected_original_raw_lanes"]):
        raise ValueError("exact_original_policy_summary_and_source_denominators_required")
    return {"parent": directory, "report": report, "plan": plan, "cases": list(contexts.values()),
        "hashes": protected, "inventories": inventories, "settings": settings,
        "reader_counts": {"files_read": reader.read_files, "decoded_bytes": reader.decoded_bytes}}


def _selector(selector, scope, lattice, origins=None, keys=None):
    old._closed(selector, {"origin_ids", "key_id", "transition_assumptions"}, "source_proposal_selector")
    if origins is None:
        origins = {o["record_id"]: o for entry in lattice["catalog_inventory"] for o in entry["origins"]}
    if keys is None:
        keys = {key["record_id"] for key in lattice["keys"]}
    ids, assumptions = selector["origin_ids"], selector["transition_assumptions"]
    if (type(ids) is not list or not ids or any(type(i) is not str or i not in origins for i in ids)
            or selector["key_id"] not in keys or type(assumptions) is not list or len(assumptions) != len(ids) - 1):
        raise ValueError("complete_registered_source_proposal_selector_required")
    spans = [origins[i]["span"] for i in ids]
    if (spans[0]["start"] != scope["analysis_span"]["start"] or spans[-1]["end"] != scope["analysis_span"]["end"]
            or any(left["end"] != right["start"] for left, right in zip(spans, spans[1:]))):
        raise ValueError("whole_contiguous_source_proposal_selector_required")
    for assumption in assumptions:
        if assumption is not None:
            old._closed(assumption, {"family", "quality"}, "source_proposal_function_request")
            if assumption["family"] not in engine.kernels.FAMILIES or assumption["quality"] not in ("M", "m"):
                raise ValueError("declared_ordinary_function_request_required")


def _validate_result(record, case, settings):
    """Intrinsic saved joins/counts, not a proposal-producer recalculation."""
    sealed._check(record, engine.PREFIX)
    old._closed(record, RESULT_KEYS, "saved_source_proposal_result")
    old._closed(record["summary"], engine.SUMMARY_KEYS, "saved_source_proposal_summary")
    old._closed(record["query_plan"], PLAN_COUNT_FIELDS | PLAN_NULLABLE_FIELDS | {"semantics"}, "saved_source_proposal_plan")
    old._closed(record["resource_limits"], {"work_budget", "max_paths", "max_selectors"}, "saved_source_proposal_limits")
    old._closed(record["flags"], set(engine.FLAGS), "saved_source_proposal_flags")
    held = record["status"] == "whole_source_proposal_hold"
    scope, lattice, panel = (case[key] for key in ("scope", "lattice", "panel"))
    for name, value in record["resource_limits"].items():
        old._limit(value, "source_proposal_resource_limit." + name)
    if (record["version"] != engine.VERSION or record["source_authority"] != engine.AUTHORITY
            or record["contract"] != engine._contract() or record["rules"] != engine.RULES
            or record["scope_ref"] != sealed._ref(scope) or record["lattice_ref"] != sealed._ref(lattice)
            or record["prior_panel_ref"] != sealed._ref(panel) or record["binding"] != scope["binding"]
            or record["analysis_span"] != scope["analysis_span"] or record["logical_universe"] != lattice["universe"]
            or record["resource_limits"] != {key: settings[key] for key in ("work_budget", "max_paths", "max_selectors")}
            or record["status"] not in ("computed_source_progression_proposals_not_evaluated", "whole_source_proposal_hold")
            or record["native_replay_status"] != "not_executed_requires_fresh_native_session"
            or any(v is not False for v in record["flags"].values())
            or any(record[k] is not None for k in ("selected", "rank", "confidence"))):
        raise ValueError("exact_saved_source_proposal_identity_without_native_authority_required")
    for key in PLAN_COUNT_FIELDS:
        old._limit(record["query_plan"][key], "source_proposal_plan." + key)
    for key in PLAN_NULLABLE_FIELDS:
        if record["query_plan"][key] is not None:
            old._limit(record["query_plan"][key], "source_proposal_plan." + key)
        elif not held:
            raise ValueError("computed_source_proposal_plan_cannot_be_unknown")
    if record["query_plan"]["semantics"] != "whole_request_logical_visit_allowance_not_CPU_RSS_accuracy":
        raise ValueError("source_proposal_work_unit_semantics_required")
    if (all(record["query_plan"][key] is not None for key in PLAN_COUNT_FIELDS | PLAN_NULLABLE_FIELDS)
            and record["query_plan"]["planned_work"] != sum(record["query_plan"][key]
                for key in PLAN_COUNT_FIELDS | {"path_shape_vector_work"})):
        raise ValueError("exact_additive_source_proposal_work_plan_required")
    if (type(record["reasons"]) is not list or any(type(v) is not str or not v for v in record["reasons"])
            or bool(record["reasons"]) != held):
        raise ValueError("whole_source_proposal_hold_reasons_required")
    for key, value in record["summary"].items():
        if held and key not in KNOWN_SUMMARY_FIELDS:
            if value is not None:
                raise ValueError("whole_source_proposal_unknown_counts_must_remain_null")
        else:
            old._limit(value, "source_proposal_summary." + key)
    controls, additional, selectors = (record[k] for k in ("retained_control_selectors", "additional_selectors", "selectors"))
    if (controls != panel["selectors"] or record["summary"]["retained_control_selectors"] != len(controls)
            or record["summary"]["requested_intervals"] != panel["summary"]["requested_intervals"]
            or type(additional) is not list or selectors != controls + additional
            or len({digest(s) for s in selectors}) != len(selectors)):
        raise ValueError("exact_ordered_controls_and_unique_additive_selectors_required")
    origins = {o["record_id"]: o for entry in lattice["catalog_inventory"] for o in entry["origins"]}
    keys = {key["record_id"]: key for key in lattice["keys"]}
    for selector in selectors:
        _selector(selector, scope, lattice, origins, keys)
    if held:
        if additional or any(record[k] for k in ("intervals", "partitions", "complete_proposal_paths", "shape_request_groups", "selector_aliases")):
            raise ValueError("whole_source_proposal_hold_no_new_prefix")
        return
    summary = record["summary"]
    if (len(record["complete_proposal_paths"]) > settings["max_paths"] or len(selectors) > settings["max_selectors"]
            or record["query_plan"]["planned_work"] > settings["work_budget"]
            or summary["additional_selectors"] != len(additional) or summary["total_selectors"] != len(selectors)
            or summary["complete_proposal_paths"] != len(record["complete_proposal_paths"])
            or summary["assessed_origin_occurrences"] != summary["eligible_origin_occurrences"] + summary["rejected_origin_occurrences"]
            or summary["eligible_origin_occurrences"] != summary["proposal_origin_occurrences"] + summary["omitted_eligible_origin_occurrences"]
            or summary["eligible_cartesian_origin_paths"] != summary["complete_proposal_paths"] + summary["omitted_eligible_cartesian_origin_paths"]):
        raise ValueError("complete_bounded_source_proposal_count_joins_required")
    intervals = record["intervals"]
    interval_totals = Counter()
    points = ([f(value) for value in lattice["coordinate_times"]] if "coordinate_times" in lattice else
        sorted({f(origin["span"][field]) for origin in origins.values() for field in ("start", "end")}))
    catalogs = {digest(entry["span"] if "span" in entry else entry["origins"][0]["span"]): entry
        for entry in lattice["catalog_inventory"] if "span" in entry or entry["origins"]}
    sounds = {sound["sound_ref"]: sound for sound in scope["sound_facts"]}
    interval_by_pair = {}
    for interval in intervals:
        old._closed(interval, INTERVAL_KEYS, "saved_requested_interval")
        indices = interval["point_indices"]
        if (type(indices) is not list or len(indices) != 2 or any(type(i) is not int for i in indices)
                or not 0 <= indices[0] < indices[1] < len(points)
                or (f(interval["span"]["start"]), f(interval["span"]["end"])) != (points[indices[0]], points[indices[1]])
                or tuple(indices) in interval_by_pair):
            raise ValueError("exact_unique_requested_interval_coordinates_required")
        entry = catalogs.get(digest(interval["span"]))
        if (entry is None or ("point_indices" in entry and entry["point_indices"] != indices)
                or ("catalog_id" in entry and entry["catalog_id"] != interval["catalog_id"])):
            raise ValueError("exact_registered_requested_interval_catalog_required")
        interval_by_pair[tuple(indices)] = interval
        for field in ("native_origins", "eligible_origins", "rejected_origins", "proposal_count", "omitted_eligible_origins"):
            old._limit(interval[field], "source_proposal_interval." + field)
            interval_totals[field] += interval[field]
        if (interval["native_origins"] != interval["eligible_origins"] + interval["rejected_origins"]
                or interval["eligible_origins"] != interval["proposal_count"] + interval["omitted_eligible_origins"]
                or interval["proposal_count"] != len(interval["proposals"])
                or interval["native_origins"] != len(entry["origins"])
                or type(interval["catalog_id"]) is not str or not interval["catalog_id"]):
            raise ValueError("exact_requested_interval_origin_denominators_required")
        old._limit(interval["distinct_eligible_spelling_signatures"], "distinct_eligible_spelling_signatures")
        reasons = interval["rejection_reason_occurrences"]
        if type(reasons) is not dict or any(type(key) is not str or not key for key in reasons):
            raise ValueError("typed_origin_rejection_reason_counts_required")
        for value in reasons.values():
            old._limit(value, "origin_rejection_reason_count")
        proposed_ids = set()
        for proposal in interval["proposals"]:
            old._closed(proposal, PROPOSAL_KEYS, "saved_origin_proposal")
            origin_ref = proposal["origin_ref"]
            parent._ref(origin_ref)
            oid = origin_ref["record_id"]
            if (oid not in origins or oid in proposed_ids or origin_ref != sealed._ref(origins[oid])
                    or origins[oid]["span"] != interval["span"]
                    or proposal["root"] != origins[oid]["root"] or proposal["members"] != origins[oid]["members"]):
                raise ValueError("registered_interval_proposal_origin_provenance_required")
            proposed_ids.add(oid)
            if (proposal["eligible"] is not True or proposal["reasons"] != []
                    or any(proposal[key] is not False for key in ("source_ornaments_used", "source_annotation_labels_used", "simultaneous_core_certified"))
                    or proposal["selected"] is not None or proposal["confidence"] is not None):
                raise ValueError("unpromoted_eligible_source_proposal_declaration_required")
            if proposal["missing_guarded_member_spellings"] is not None:
                old._limit(proposal["missing_guarded_member_spellings"], "missing_guarded_member_spellings")
            for key in ("guarded_pooled_member_note_time", "guarded_root_note_time"):
                if _rational(proposal[key], key) < 0:
                    raise ValueError("nonnegative_proposal_note_time_required")
            old._closed(proposal["raw_note_time_by_support"], {"member", "nonmember", "unknown", "unsupported"}, "raw_source_support")
            for key, value in proposal["raw_note_time_by_support"].items():
                if _rational(value, key) < 0:
                    raise ValueError("nonnegative_raw_support_time_required")
            if type(proposal["member_sound_evidence"]) is not list:
                raise ValueError("typed_proposal_source_sound_evidence_required")
            for evidence in proposal["member_sound_evidence"]:
                old._closed(evidence, {"sound_ref", "source_note_refs", "full_sound_span", "observed_span"}, "proposal_member_sound")
                _strings(evidence["source_note_refs"], "member_sound.source_notes")
                if type(evidence["sound_ref"]) is not str or not evidence["sound_ref"]:
                    raise ValueError("typed_proposal_source_sound_reference_required")
                for field in ("full_sound_span", "observed_span"):
                    old._closed(evidence[field], {"start", "end"}, "member_sound_span")
                    if _rational(evidence[field]["start"], field) >= _rational(evidence[field]["end"], field):
                        raise ValueError("positive_proposal_member_sound_span_required")
                sound = sounds.get(evidence["sound_ref"])
                if (sound is None or evidence["source_note_refs"] != sound["source_note_refs"]
                        or evidence["full_sound_span"] != sound["span"]):
                    raise ValueError("exact_proposal_sound_and_original_note_provenance_required")
                a = max(f(sound["span"]["start"]), f(interval["span"]["start"]))
                b = min(f(sound["span"]["end"]), f(interval["span"]["end"]))
                if a >= b or evidence["observed_span"] != sealed._span(a, b):
                    raise ValueError("exact_literal_source_sound_interval_overlap_required")
        for bucket in interval["bucket_representatives"]:
            old._closed(bucket, {"bucket", "eligible_origins", "representative_ref", "distinct_ordered_signatures",
                "omitted_bucket_representative_origins"}, "source_bucket_representative")
            old._closed(bucket["bucket"], {"kind", "quality", "spelled_root", "classification_is_harmony_confirmation"}, "saved_bucket")
            declared = bucket["bucket"]
            if (declared["classification_is_harmony_confirmation"] is not False
                    or declared["kind"] not in ("triad", "seventh", "nonordinary_or_unassessed")):
                raise ValueError("unconfirmed_typed_source_bucket_required")
            if declared["kind"] == "nonordinary_or_unassessed":
                if declared["quality"] is not None or declared["spelled_root"] is not None:
                    raise ValueError("unassessed_bucket_cannot_claim_ordinary_quality_root")
            else:
                if type(declared["quality"]) is not str or not declared["quality"]:
                    raise ValueError("typed_ordinary_bucket_quality_required")
                _pitch(declared["spelled_root"], "bucket.root")
            for field in ("eligible_origins", "distinct_ordered_signatures", "omitted_bucket_representative_origins"):
                old._limit(bucket[field], "bucket." + field)
            parent._ref(bucket["representative_ref"])
            if (bucket["representative_ref"]["record_id"] not in proposed_ids
                    or bucket["representative_ref"] != sealed._ref(origins[bucket["representative_ref"]["record_id"]])
                    or bucket["eligible_origins"] != 1 + bucket["omitted_bucket_representative_origins"]):
                raise ValueError("exact_retained_bucket_representative_provenance_required")
    if (len(intervals) != summary["requested_intervals"] or interval_totals["native_origins"] != summary["assessed_origin_occurrences"]
            or interval_totals["eligible_origins"] != summary["eligible_origin_occurrences"]
            or interval_totals["proposal_count"] != summary["proposal_origin_occurrences"]
            or list(interval_by_pair) != sorted(interval_by_pair)
            or [interval["point_indices"] for interval in intervals]
                != [interval["point_indices"] for interval in panel["intervals"]]):
        raise ValueError("all_requested_interval_source_scan_counts_required")
    paths = record["complete_proposal_paths"]
    if (len({digest(path["origin_ids"]) for path in paths}) != len(paths)
            or not {digest(selector["origin_ids"]) for selector in controls}
                <= {digest(path["origin_ids"]) for path in paths}):
        raise ValueError("unique_complete_source_proposal_paths_required")
    for path in paths:
        old._closed(path, PATH_KEYS, "saved_complete_proposal_path")
        if path["origin_refs"] != [sealed._ref(origins[oid]) for oid in path["origin_ids"]]:
            raise ValueError("exact_source_path_origin_provenance_required")
        indices = path["point_indices"]
        if (type(indices) is not list or len(indices) != len(path["origin_ids"]) + 1
                or any(type(i) is not int for i in indices) or indices[0] != 0 or indices[-1] != len(points) - 1
                or any(left >= right for left, right in zip(indices, indices[1:]))
                or any(origins[oid]["span"] != interval_by_pair[tuple(pair)]["span"]
                    or oid not in {p["origin_ref"]["record_id"] for p in interval_by_pair[tuple(pair)]["proposals"]}
                    for oid, pair in zip(path["origin_ids"], zip(indices, indices[1:])))):
            raise ValueError("full_contiguous_path_uses_retained_interval_proposals_required")
        if type(path["proposal_provenance"]) is not list or not path["proposal_provenance"]:
            raise ValueError("source_proposal_path_provenance_required")
        for provenance in path["proposal_provenance"]:
            kind = provenance.get("kind")
            old._closed(provenance, {"kind", "proposal_lane"} | ({"slot"} if kind == "single_slot_substitution" else set()), "source_path_provenance")
            if kind not in ("retained_seed", "single_slot_substitution") or type(provenance["proposal_lane"]) is not int or provenance["proposal_lane"] not in (0, 1):
                raise ValueError("typed_original_seed_or_substitution_provenance_required")
            if kind == "single_slot_substitution" and (type(provenance["slot"]) is not int or not 0 <= provenance["slot"] < len(path["origin_ids"])):
                raise ValueError("typed_source_substitution_slot_required")
    partitions = record["partitions"]
    names = ["whole_hold", "nearest_half_two_slots", "nearest_thirds_three_slots"]
    if type(partitions) is not list or [p["partition_kind"] for p in partitions] != names:
        raise ValueError("all_three_ordered_structural_partition_denominators_required")
    if ([(p["partition_kind"], p["point_indices"]) for p in partitions]
            != [(p["partition_kind"], p["point_indices"]) for p in panel["partitions"]]):
        raise ValueError("exact_original_structural_partition_coordinates_required")
    cartesian_sum = 0
    for partition in partitions:
        old._closed(partition, PARTITION_KEYS, "saved_source_partition")
        for field in ("proposed_paths", "eligible_cartesian_origin_paths", "omitted_eligible_cartesian_origin_paths"):
            old._limit(partition[field], "partition." + field)
        matching = [path for path in paths if path["partition_kind"] == partition["partition_kind"]]
        indices = partition["point_indices"]
        if indices is None:
            if partition["status"] != "unavailable_structural_partition" or matching or any(partition[k] for k in ("proposed_paths", "eligible_cartesian_origin_paths", "omitted_eligible_cartesian_origin_paths")):
                raise ValueError("unavailable_structural_partition_is_known_zero")
        else:
            if (type(indices) is not list or len(indices) != names.index(partition["partition_kind"]) + 2
                    or any(type(i) is not int for i in indices) or indices[0] != 0 or indices[-1] != len(points) - 1
                    or any(a >= b for a, b in zip(indices, indices[1:]))
                    or any(path["point_indices"] != indices for path in matching)):
                raise ValueError("exact_full_partition_path_coordinates_required")
            cartesian = 1
            for pair in zip(indices, indices[1:]):
                cartesian *= interval_by_pair[tuple(pair)]["eligible_origins"]
            if (partition["eligible_cartesian_origin_paths"] != cartesian
                    or partition["proposed_paths"] != len(matching)
                    or partition["omitted_eligible_cartesian_origin_paths"] != cartesian - len(matching)
                    or partition["status"] != ("computed_bounded_mixed_path_sample" if matching else "known_no_complete_evaluable_path")):
                raise ValueError("exact_partition_cartesian_and_omitted_path_denominators_required")
        cartesian_sum += partition["eligible_cartesian_origin_paths"]
    if cartesian_sum != summary["eligible_cartesian_origin_paths"]:
        raise ValueError("all_partition_cartesian_paths_required")
    expected_paths = []
    for partition in partitions:
        indices = partition["point_indices"]
        if indices is None:
            continue
        slot_pairs = list(zip(indices, indices[1:]))
        pools = [interval_by_pair[tuple(pair)]["proposals"] for pair in slot_pairs]
        proposed = {}
        if all(pools):
            for seed in (p for p in panel["complete_proposal_paths"] if p["partition_kind"] == partition["partition_kind"]):
                ids = tuple(seed["origin_ids"])
                proposed.setdefault(ids, []).append({"kind": "retained_seed", "proposal_lane": seed["proposal_lane"]})
                for slot, pool in enumerate(pools):
                    for proposal in pool:
                        changed = list(ids)
                        changed[slot] = proposal["origin_ref"]["record_id"]
                        proposed.setdefault(tuple(changed), []).append({"kind": "single_slot_substitution",
                            "proposal_lane": seed["proposal_lane"], "slot": slot})
            for ids, provenance in proposed.items():
                expected_paths.append({"partition_kind": partition["partition_kind"], "point_indices": indices,
                    "origin_ids": list(ids), "origin_refs": [sealed._ref(origins[oid]) for oid in ids],
                    "proposal_provenance": provenance})
    if paths != expected_paths:
        raise ValueError("exact_seed_and_single_slot_substitution_provenance_required")
    observed = {digest(s): {"kind": "retained_control", "index": i} for i, s in enumerate(controls)}
    generated = []
    aliases = []
    shape_options = 0
    requests = record["shape_request_groups"]
    if len(requests) != len(paths) * len(keys):
        raise ValueError("all_paths_and_registered_keys_request_inventory_required")
    reserved_vectors = 0
    for request in requests:
        old._limit(request["complete_vector_count"], "source_request_vector_count")
        reserved_vectors += request["complete_vector_count"]
    if reserved_vectors + len(controls) > settings["max_selectors"]:
        raise ValueError("whole_vector_admission_before_join_budget_required")
    ordered_keys = sorted(keys)
    for position, request in enumerate(requests):
        old._closed(request, {"path_index", "key_ref", "cuts", "complete_vector_count"}, "saved_source_request")
        index = request["path_index"]
        old._limit(index, "source_request_path_index")
        if (index != position // len(keys) or index >= len(paths)
                or request["key_ref"] != sealed._ref(keys[ordered_keys[position % len(keys)]])):
            raise ValueError("registered_source_request_path_key_required")
        path = paths[index]
        if len(request["cuts"]) != len(path["origin_ids"]) - 1:
            raise ValueError("complete_source_request_cut_inventory_required")
        for i, cut in enumerate(request["cuts"]):
            old._closed(cut, CUT_KEYS, "saved_source_request_cut")
            if (cut["source_origin_ref"] != path["origin_refs"][i] or cut["target_origin_ref"] != path["origin_refs"][i + 1]
                    or any(cut[k] is not None for k in ("resolution_support", "secondary_support", "boundary_support", "same_completion_ref"))
                    or type(cut["same_spelling_signature"]) is not bool
                    or cut["same_spelling_signature"] is not (_literal_signature(origins[path["origin_ids"][i]])
                        == _literal_signature(origins[path["origin_ids"][i + 1]]))
                    or type(cut["request_options"]) is not list or not cut["request_options"] or cut["request_options"][0] is not None):
                raise ValueError("shape_request_must_not_claim_resolution_or_completion_support")
            assumptions = [{"family": family, "quality": quality} for family in engine.kernels.FAMILIES for quality in ("M", "m")]
            if type(cut["checked_shapes"]) is not list or len(cut["checked_shapes"]) != len(assumptions):
                raise ValueError("all_ordered_family_quality_declarations_required")
            for value, assumption in zip(cut["checked_shapes"], assumptions):
                _shape(value, assumption)
            compatible = [value["assumption"] for value in cut["checked_shapes"] if value["shape_request_eligible"] is True]
            if cut["request_options"] != [None, *compatible]:
                raise ValueError("exact_declared_shape_request_options_required")
            shape_options += len(cut["request_options"]) - 1
        count = 1
        for cut in request["cuts"]:
            count *= len(cut["request_options"])
        if request["complete_vector_count"] != count:
            raise ValueError("exact_source_request_cartesian_vector_count")
        for vector in product(*(c["request_options"] for c in request["cuts"])):
            selector = {"origin_ids": path["origin_ids"], "key_id": request["key_ref"]["record_id"],
                "transition_assumptions": list(vector)}
            marker = digest(selector)
            if marker in observed:
                aliases.append({"request_index": position, "selector_fingerprint": marker,
                    "existing_selector": deepcopy(observed[marker])})
            else:
                observed[marker] = {"kind": "additional", "index": len(generated)}
                generated.append(selector)
    if (generated != additional or record["selector_aliases"] != aliases
            or summary["shape_request_occurrences"] != shape_options):
        raise ValueError("all_declared_shape_vectors_unique_additive_not_ranked_prefix")


def _case_metadata(case):
    return {"context_key": deepcopy(case["context_key"]), "source_identity_sha256": case["source_identity_sha256"],
        "full_IR": deepcopy(case["full_IR"]), "scope": deepcopy(case["scope_info"]),
        "native_lattice": deepcopy(case["lattice_info"]), "prior_panel": deepcopy(case["panel_info"]),
        "original_source_files": deepcopy(case["original_source_files"]), "native_inventory": deepcopy(case["native_counts"]),
        "parent_policy_rows": deepcopy(case["parent_policy_rows"]), "completion_controls": deepcopy(case["completion_controls"])}


def _aggregate(records):
    known, unknown = Counter(), Counter()
    for record in records:
        for key, value in record["summary"].items():
            if value is None:
                unknown[key] += 1
            else:
                known[key] += value
    return {key: None if unknown[key] else known[key] for key in engine.SUMMARY_KEYS}, dict(known), dict(unknown)


def run(directory, output, **limits):
    started, output = perf_counter(), Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("append_only_new_direct_workspace_output_required")
    settings = _settings(limits)
    data = load_inputs(directory, **settings)
    code = {str(path.resolve()): old._file_sha(path) for path in _code_paths()}
    protected = deepcopy(data["hashes"])
    old._protect_map(protected, code)
    output.mkdir()
    artifacts, rows, results, failures, replay_jobs = {}, [], [], [], []
    plan = {"version": VERSION, "parent": str(data["parent"]), "inputs": deepcopy(data["hashes"]), "code": code,
        "settings": settings, "denominators": deepcopy(data["report"]["denominators"]),
        "parent_report_sha256": old._file_sha(data["parent"] / "report.json"),
        "parent_inventories": [{"directory": str(p), "files": len(i)} for p, i in data["inventories"]],
        "parent_source_size_manifest": deepcopy(data["plan"]["parent_source_size_manifest"]),
        "parent_selected_contexts": deepcopy(data["plan"]["parent_selected_contexts"]),
        "parent_policy_summary": deepcopy(data["report"]["summary"]), "reader_counts": deepcopy(data["reader_counts"]),
        "distinct_registered_sources": len(data["cases"]), "registered_policy_completion_rows": 4,
        "source_authority": engine.AUTHORITY, "parent_source_authority": AUTHORITY,
        "fresh_native_preparations": 0, "selected": None, **{key: False for key in POLICY_FALSE}}
    old._save_json(output, "run-plan.json", plan, artifacts)
    baselines = [digest([c["scope"], c["lattice"], c["panel"]]) for c in data["cases"]]
    for case, baseline in zip(data["cases"], baselines):
        key = case["context_key"]
        try:
            if digest([case["scope"], case["lattice"], case["panel"]]) != baseline:
                raise ValueError("saved_source_changed_after_admission")
            result = engine.propose(case["scope"], case["lattice"], case["panel"],
                **{k: settings[k] for k in ("work_budget", "max_paths", "max_selectors")})
            if digest([case["scope"], case["lattice"], case["panel"]]) != baseline:
                raise ValueError("source_proposal_modified_registered_saved_inputs")
            _validate_result(result, case, settings)
            encoded = json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
            if len(encoded) > settings["max_output_record_bytes"]:
                raise ValueError("whole_source_proposal_output_byte_budget_no_prefix")
            info = old._save_record(output, "proposals", result, engine.PREFIX, artifacts)
            results.append(result)
            rows.append({**_case_metadata(case),
                "proposal": info, "summary": deepcopy(result["summary"]), "query_plan": deepcopy(result["query_plan"]),
                "status": result["status"], "reasons": deepcopy(result["reasons"]), "error": None})
            for completion in case["completion_controls"]:
                held = result["status"] == "whole_source_proposal_hold"
                replay_jobs.append({"context_key": deepcopy(key), "source_identity_sha256": case["source_identity_sha256"],
                    "full_IR": deepcopy(case["full_IR"]), "scope": deepcopy(case["scope_info"]),
                    "archived_lattice": deepcopy(case["lattice_info"]), "source_proposal": deepcopy(info),
                    "archived_completion_control": deepcopy(completion),
                    "selector_field_pointer": None if held else {"record_ref": sealed._ref(result), "field": "selectors"},
                    "planned_selector_occurrences": None if held else len(result["selectors"]),
                    "retained_control_selector_occurrences": len(result["retained_control_selectors"]),
                    "execution_status": "blocked_whole_source_proposal_hold" if held else "not_executed_requires_fresh_native_session",
                    "archived_origins_are_fresh_native_authority": False,
                    "native_path_ids_reused": False, "native_evaluation_performed": False})
        except Exception as exc:
            error = f"{type(exc).__name__}:{exc}"
            failures.append({"context_key": deepcopy(key), "error": error})
            rows.append({**_case_metadata(case), "proposal": None, "summary": None,
                "status": "saved_source_proposal_failure", "error": error})
            for completion in case["completion_controls"]:
                replay_jobs.append({"context_key": deepcopy(key), "source_identity_sha256": case["source_identity_sha256"],
                    "full_IR": deepcopy(case["full_IR"]), "scope": deepcopy(case["scope_info"]),
                    "archived_lattice": deepcopy(case["lattice_info"]), "source_proposal": None,
                    "archived_completion_control": deepcopy(completion), "selector_field_pointer": None,
                    "planned_selector_occurrences": None, "retained_control_selector_occurrences": len(case["panel"]["selectors"]),
                    "execution_status": "blocked_source_proposal_failure", "archived_origins_are_fresh_native_authority": False,
                    "native_path_ids_reused": False, "native_evaluation_performed": False})
    old._save_json(output, "context-index.json", rows, artifacts)
    replay = {"version": VERSION, "source_authority": engine.AUTHORITY, "jobs": replay_jobs,
        "planned_completion_requests": len(replay_jobs),
        "planned_selector_occurrences": None if failures or any(j["planned_selector_occurrences"] is None for j in replay_jobs)
            else sum(j["planned_selector_occurrences"] for j in replay_jobs),
        "retained_control_selector_occurrences": sum(j["retained_control_selector_occurrences"] for j in replay_jobs),
        "native_evaluations_performed": 0, "fresh_native_sessions_prepared": 0,
        "same_completion_resolution_evaluated": False, "winning_harmony_selected": False,
        "limitations": ["This is a future fresh-replay request manifest, not an evaluated native comparison.",
            "Archived origin IDs must be rebound only by exact fresh supplier/source provenance, never nearest-pitch matching.",
            "A withheld proposal creates blocked jobs, not a favorable partial selector prefix."]}
    old._save_json(output, "native-replay-plan.json", replay, artifacts)
    changed, changed_artifacts = old._guard(protected), old._guard(artifacts)
    if {str(p.resolve()) for p in _code_paths()} != set(code):
        changed.append("creation_code_inventory_changed")
    for directory, inventory in data["inventories"]:
        if {str(p.resolve()) for p in directory.rglob("*") if p.is_file()} != inventory:
            changed.append("registered_parent_inventory_changed:" + str(directory))
    if {str(p.resolve()) for p in output.rglob("*") if p.is_file()} != set(artifacts):
        changed_artifacts.append("new_artifact_inventory_changed")
    integrity = not failures and not changed and not changed_artifacts
    summary, known, unknown = _aggregate(results)
    computed = sum(r["status"] == "computed_source_progression_proposals_not_evaluated" for r in rows)
    held = sum(r["status"] == "whole_source_proposal_hold" for r in rows)
    report = {"version": VERSION, "status": "saved_source_proposal_probe_complete_not_evaluated" if integrity else "saved_source_proposal_probe_failed",
        "computation_integrity_passed": integrity, "inputs_and_code_unchanged": not changed, "artifacts_unchanged": not changed_artifacts,
        "changed_inputs_or_code": changed, "changed_artifacts": changed_artifacts, "failures": failures, "artifact_hashes": artifacts,
        "denominators": deepcopy(data["report"]["denominators"]), "distinct_registered_sources": len(data["cases"]),
        "registered_policy_completion_rows": 4, "saved_source_proposals": len(results), "computed_source_proposals": computed,
        "whole_source_proposal_holds": held, "submitted_source_proposal_computation_complete": bool(integrity and rows and computed == len(rows)),
        "admitted_native_inventory": {key: sum(c["native_counts"][key] for c in data["cases"])
            for key in ("native_catalogs", "native_origins", "registered_key_hypotheses")},
        "summary": summary if integrity else None, "known_summary_subtotal": known if integrity else None,
        "unknown_summary_context_occurrences": unknown if integrity else None,
        "parent_policy_summary": deepcopy(data["report"]["summary"]), "native_replay_planned_completion_requests": len(replay_jobs),
        "native_replay_planned_selector_occurrences": replay["planned_selector_occurrences"] if integrity else None,
        "native_replay_evaluations_performed": 0, "source_authority": engine.AUTHORITY, "parent_source_authority": AUTHORITY,
        "fresh_native_preparations": 0, "selected": None, "elapsed_seconds": perf_counter() - started,
        **{key: False for key in POLICY_FALSE}, "limits": [
            "All saved origins are admitted; only explicitly requested source intervals are assessed by the proposal engine.",
            "Retained controls, additive selectors, sampled mixed paths and omitted Cartesian paths have distinct denominators.",
            "Archived proposals and shape requests are not winning harmony or same-completion resolution judgments.",
            "Later native/role evaluation requires a fresh session and exact provenance binding; no replay is performed here."]}
    old.storage.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-budget", type=int, default=SETTINGS["work_budget"])
    parser.add_argument("--max-paths", type=int, default=SETTINGS["max_paths"])
    parser.add_argument("--max-selectors", type=int, default=SETTINGS["max_selectors"])
    args = parser.parse_args()
    run(args.parent, args.output, work_budget=args.work_budget, max_paths=args.max_paths, max_selectors=args.max_selectors)


if __name__ == "__main__":
    main()
