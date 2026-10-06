"""Append-only cross-batch contrast of validated, saved progression evidence.

This is a saved-metadata adapter, never a live native issuer or a replay of
earlier producers. Every entry from both complete saved controls is retained.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import gzip
from itertools import combinations
import json
from pathlib import Path
from time import perf_counter

from . import factor_source_evidence_trial as parent
from . import native_progression_contrast as engine
from .musical_pattern_observation import digest

old, sealed = parent.old, parent.sealed
ROOT = parent.ROOT
VERSION = "native-progression-contrast-trial-0.1.0"
AUTHORITY = "validated_saved_evidence_not_live_native_session"
SETTINGS = {"max_pairs": 2000, "work_budget": 2000000, "max_entries_per_completion": 64,
    "max_file_bytes": 67108864, "max_decoded_file_bytes": 268435456,
    "max_total_decoded_bytes": 1073741824, "max_output_record_bytes": 67108864}
POLICY_FALSE = (*parent.POLICY_FALSE, "live_native_authority_claimed", "native_or_role_producer_replayed",
    "candidate_selected", "ranking_computed", "partial_read_prefix_used")
REPORT_KEYS = {"version", "status", "computation_integrity_passed", "inputs_and_code_unchanged",
    "artifacts_unchanged", "changed_inputs_or_code", "changed_artifacts", "failures", "artifact_hashes",
    "denominators", "fresh_native_preparations", "summary", "source_authority", "selected",
    "submitted_role_calculation_complete", "elapsed_seconds", "limits", *parent.POLICY_FALSE}
PLAN_KEYS = {"version", "native_parent", "supplier_parent", "role_parent", "inputs", "code", "settings",
    "max_contexts", "selection_policy", "source_size_manifest", "selected_contexts", "denominators",
    "source_authority", "selector_batch_size", "all_batches_for_both_completions_planned", "selected", *parent.POLICY_FALSE}
ROW_KEYS = {"context_key", "full_IR", "scope", "native_lattice", "panel", "panel_summary", "panel_query_plan",
    "selected_selectors", "batch_count_per_completion", "completion_batches", "counts",
    "planned_batch_upper_bound_per_completion", "unsubmitted_selector_upper_bound_per_completion",
    "actual_completion_requests", "status", "error"}
COMPLETION_KEYS = {"kind", "bundle", "required_links", "planned_batches", "saved_batches", "batches"}
BATCH_KEYS = {"batch_index", "selector_start", "selector_end_exclusive", "selectors", "comparison", "explanation",
    "native_summary", "role_summary", "native_query_plan", "role_query_plan", "status", "reasons"}
INFO_KEYS = {"artifact", "sha256", "record_ref", "status"}
IR_INFO_KEYS = {"artifact", "sha256", "ir_document_id", "ir_content_sha256", "binding_match", "registered_full_IR_not_projection"}
DENOMINATOR_KEYS = {"declared_contexts", "declared_original_raw_lanes", "registered_context_pool", "selected_contexts",
    "selected_original_raw_lanes", "unexecuted_declared_contexts", "unexecuted_declared_original_raw_lanes"}
SUMMARY_FIELDS = {"submitted_entries", "planned_same_key_same_bundle_pairs", "computed_pairs", "withheld_pairs",
    "candidate_only_pairs", "transition_only_pairs", "candidate_and_transition_pairs", "partition_pairs",
    "alias_control_pairs", "raw_time_conserved_entries", "pair_kind_counts"}
RESULT_FLAGS = {"final_harmony_confirmed", "final_NCT_confirmed", "key_confirmed", "cadence_confirmed",
    "ranking_computed", "training_eligible", "generation_ready", "production_modified", "live_native_authority_claimed",
    "independent_completions_unioned", "all_logical_paths_evaluated"}


class BoundedReader:
    def __init__(self, settings):
        self.settings, self.decoded_bytes, self.read_files = settings, 0, 0

    def read(self, path):
        path = Path(path)
        if path.stat().st_size > self.settings["max_file_bytes"]:
            raise ValueError("whole_saved_read_hold:file_bytes")
        cap = min(self.settings["max_decoded_file_bytes"], self.settings["max_total_decoded_bytes"] - self.decoded_bytes)
        stream = gzip.open(path, "rb") if path.suffix == ".gz" else path.open("rb")
        with stream:
            raw = stream.read(cap + 1)
        if len(raw) > cap:
            raise ValueError("whole_saved_read_hold:decoded_bytes_no_partial_JSON")
        self.decoded_bytes += len(raw)
        self.read_files += 1
        return json.loads(raw.decode("utf-8"), parse_constant=old._reject_constant, object_pairs_hook=old._unique_object)


def _settings(limits):
    if set(limits) - set(SETTINGS):
        raise ValueError("closed_saved_contrast_trial_limits_required")
    result = {**SETTINGS, **limits}
    for key, value in result.items():
        old._limit(value, key)
    return result


def _code_paths():
    extra = [Path(__file__).resolve(), Path(engine.__file__).resolve(),
        ROOT / "tests/test_native_progression_contrast.py", ROOT / "tests/test_native_progression_contrast_trial.py"]
    return sorted({*parent._code_paths(), *(p for p in extra if p.is_file())})


def _record(info, prefix, reader, protected):
    old._closed(info, INFO_KEYS, "registered_saved_record_info")
    old._protect(protected, info["artifact"], info["sha256"])
    if old._file_sha(info["artifact"]) != info["sha256"]:
        raise ValueError("registered_saved_record_file_hash_changed")
    record = reader.read(info["artifact"])
    sealed._check(record, prefix)
    if sealed._ref(record) != info["record_ref"] or record["status"] != info["status"]:
        raise ValueError("registered_saved_record_ref_or_status_mismatch")
    return record


def _edge_signature(links):
    if type(links) is not list or any(type(edge) is not list or len(edge) != 2
            or any(type(sid) is not str for sid in edge) for edge in links):
        raise ValueError("closed_saved_required_link_list_required")
    values = [tuple(edge) for edge in links]
    if len(set(values)) != len(values):
        raise ValueError("duplicate_saved_required_link")
    return sorted(values)


def _entry(native_path, role_path, selector, comparison, explanation, lattice, scope, bundle, origins, keys):
    sealed._check(native_path, "fmilpath_")
    sealed._check(native_path["logical_tuple"], "fmiltuple_")
    sealed._check(role_path, "fmnrolepath_")
    origin_refs = [sealed._ref(origins[origin_id]) for origin_id in selector["origin_ids"]]
    key_ref, bundle_ref = sealed._ref(keys[selector["key_id"]]), sealed._ref(bundle)
    if (native_path["scope_ref"] != sealed._ref(scope) or native_path["lattice_ref"] != sealed._ref(lattice)
            or native_path["origin_refs"] != origin_refs or native_path["key_ref"] != key_ref
            or native_path["bundle_ref"] != bundle_ref
            or native_path["partition"] != [origins[origin_id]["span"] for origin_id in selector["origin_ids"]]
            or native_path["logical_tuple"]["transition_assumptions"] != selector["transition_assumptions"]
            or any(native_path["logical_tuple"][key] != native_path[key]
                for key in ("scope_ref", "lattice_ref", "origin_refs", "partition", "key_ref", "bundle_ref"))
            or role_path["native_path_ref"] != sealed._ref(native_path)
            or role_path["logical_tuple_ref"] != sealed._ref(native_path["logical_tuple"])
            or any(role_path[key] != native_path[key] for key in ("origin_refs", "partition", "key_ref", "bundle_ref"))
            or role_path["transition_assumptions"] != selector["transition_assumptions"]
            or role_path["raw_account_pointer"] != {"parent_path_ref": sealed._ref(native_path),
                "field": "whole_path_account", "sha256": digest(native_path["whole_path_account"])}):
        raise ValueError("exact_saved_selector_same_completion_path_role_relationship_required")
    return {"native_path": native_path, "role_path": role_path,
        "comparison_ref": sealed._ref(comparison), "explanation_ref": sealed._ref(explanation)}


def _context(row, plan, report, reader, protected, settings):
    old._closed(row, ROW_KEYS, "saved_source_evidence_context")
    if (row["status"] != "source_evidence_probe_saved_not_selected" or row["error"] is not None
            or row["batch_count_per_completion"] != 17 or row["actual_completion_requests"] != 2
            or row["unsubmitted_selector_upper_bound_per_completion"] != 0
            or type(row["selected_selectors"]) is not list or len(row["selected_selectors"]) != 50
            or len(row["completion_batches"]) != 2):
        raise ValueError("exact_saved_fifty_entry_two_completion_panel_required")
    old._closed(row["full_IR"], IR_INFO_KEYS, "registered_full_IR_info")
    info = row["full_IR"]
    if (info["binding_match"] is not True or info["registered_full_IR_not_projection"] is not True
            or plan["inputs"].get(info["artifact"]) != info["sha256"]):
        raise ValueError("registered_full_IR_snapshot_required")
    old._protect(protected, info["artifact"], info["sha256"])
    ir = reader.read(info["artifact"])
    if ir["ir_document_id"] != info["ir_document_id"] or digest(ir) != info["ir_content_sha256"]:
        raise ValueError("registered_full_IR_content_binding_mismatch")
    if plan["inputs"].get(row["scope"]["artifact"]) != row["scope"]["sha256"]:
        raise ValueError("registered_scope_not_in_creation_inputs")
    scope = _record(row["scope"], old.expanded.PREFIX, reader, protected)
    if scope["binding"] != old.expanded._binding(ir):
        raise ValueError("exact_saved_scope_full_IR_binding_required")
    for name in ("native_lattice", "panel"):
        if report["artifact_hashes"].get(row[name]["artifact"]) != row[name]["sha256"]:
            raise ValueError("saved_context_artifact_not_registered")
    lattice = _record(row["native_lattice"], parent.native.PREFIX, reader, protected)
    panel = _record(row["panel"], parent.panel_engine.PREFIX, reader, protected)
    parent._validate_panel_record(panel, lattice, scope, plan["settings"])
    if (lattice["scope_ref"] != sealed._ref(scope) or lattice["analysis_span"] != scope["analysis_span"]
            or panel["selectors"] != row["selected_selectors"] or panel["summary"] != row["panel_summary"]
            or panel["query_plan"] != row["panel_query_plan"]):
        raise ValueError("exact_saved_lattice_panel_scope_required")
    if 50 > settings["max_entries_per_completion"]:
        raise ValueError("whole_saved_read_hold:entries_no_prefix")
    origins = {o["record_id"]: o for entry in lattice["catalog_inventory"] for o in entry["origins"]}
    keys = {key["record_id"]: key for key in lattice["keys"]}
    jobs, used = [], set()
    for completion in row["completion_batches"]:
        old._closed(completion, COMPLETION_KEYS, "saved_completion_batches")
        if (completion["planned_batches"] != 17 or completion["saved_batches"] != 17
                or len(completion["batches"]) != 17 or completion["kind"] in used):
            raise ValueError("exact_cross_batch_saved_inventory_required")
        used.add(completion["kind"])
        edge_count = len(_edge_signature(completion["required_links"]))
        if ((completion["kind"] == "all_no_link_control" and edge_count != 0)
                or (completion["kind"] == "bounded_same_raw_lane_greedy_technical_probe"
                    and not 0 < edge_count <= plan["settings"]["max_greedy_links"])):
            raise ValueError("saved_control_kind_and_required_edges_mismatch")
        binfo = completion["bundle"]
        if report["artifact_hashes"].get(binfo["artifact"]) != binfo["sha256"]:
            raise ValueError("saved_bundle_not_registered")
        bundle = _record(binfo, parent.native.BUNDLE_PREFIX, reader, protected)
        if (bundle["scope_ref"] != sealed._ref(scope) or bundle["lattice_ref"] != sealed._ref(lattice)
                or _edge_signature(bundle["required_links"]) != _edge_signature(completion["required_links"])):
            raise ValueError("same_saved_all_lane_completion_required")
        entries, refs, ordered = [], [], []
        for position, batch in enumerate(completion["batches"]):
            old._closed(batch, BATCH_KEYS, "saved_ordered_batch")
            start, end = position * 3, min(position * 3 + 3, 50)
            selectors = panel["selectors"][start:end]
            if (batch["batch_index"] != position or batch["selector_start"] != start
                    or batch["selector_end_exclusive"] != end or batch["selectors"] != selectors):
                raise ValueError("exact_saved_selector_order_without_prefix_required")
            for name in ("comparison", "explanation"):
                if report["artifact_hashes"].get(batch[name]["artifact"]) != batch[name]["sha256"]:
                    raise ValueError("saved_batch_artifact_not_registered")
            comparison = _record(batch["comparison"], parent.native.COMPARISON_PREFIX, reader, protected)
            explanation = _record(batch["explanation"], parent.roles.PREFIX, reader, protected)
            old._validate_role_summary(explanation, comparison)
            if (comparison["selectors"] != selectors or comparison["scope_ref"] != sealed._ref(scope)
                    or comparison["lattice_ref"] != sealed._ref(lattice) or comparison["bundle_ref"] != sealed._ref(bundle)
                    or comparison["summary"] != batch["native_summary"] or comparison["query_plan"] != batch["native_query_plan"]
                    or explanation["summary"] != batch["role_summary"] or explanation["query_plan"] != batch["role_query_plan"]
                    or explanation["status"] != batch["status"] or explanation["reasons"] != batch["reasons"]
                    or explanation["native_comparison_ref"] != sealed._ref(comparison)
                    or any(explanation[key] != comparison[key] for key in ("scope_ref", "lattice_ref", "bundle_ref"))
                    or explanation["native_request"] != {key: comparison[key] for key in (
                        "selectors", "resource_limits", "status", "reasons", "summary", "query_plan")}
                    or len(comparison["paths"]) != len(selectors) or len(explanation["paths"]) != len(selectors)):
                raise ValueError("exact_saved_batch_summary_parent_relationship_required")
            roles_by_native = {path["native_path_ref"]["record_id"]: path for path in explanation["paths"]}
            if len(roles_by_native) != len(selectors):
                raise ValueError("duplicate_saved_role_native_path_ref")
            for selector, native_path in zip(selectors, comparison["paths"]):
                entries.append(_entry(native_path, roles_by_native[native_path["record_id"]], selector,
                    comparison, explanation, lattice, scope, bundle, origins, keys))
            ordered.extend(selectors)
            refs.append({"comparison": deepcopy(batch["comparison"]), "explanation": deepcopy(batch["explanation"])})
        if ordered != panel["selectors"] or len(entries) != 50 or {e["native_path"]["key_ref"]["record_id"] for e in entries} != set(keys):
            raise ValueError("all_saved_entries_and_all_registered_keys_required")
        jobs.append({"kind": completion["kind"], "bundle": bundle, "bundle_info": binfo,
            "entries": entries, "saved_batch_refs": refs})
    if used != {"all_no_link_control", "bounded_same_raw_lane_greedy_technical_probe"}:
        raise ValueError("exact_saved_both_completion_controls_required")
    if len({job["bundle"]["record_id"] for job in jobs}) != 2:
        raise ValueError("distinct_saved_completion_controls_required")
    return {"context_key": deepcopy(row["context_key"]), "full_IR": deepcopy(info), "scope_info": deepcopy(row["scope"]),
        "lattice_info": deepcopy(row["native_lattice"]), "panel_info": deepcopy(row["panel"]),
        "original_source_files": deepcopy(ir["source_files"]), "scope": scope, "lattice": lattice, "jobs": jobs}


def load_inputs(directory, **limits):
    settings = _settings(limits)
    directory = Path(directory).resolve(strict=True)
    reader, protected = BoundedReader(settings), {}
    report_path = directory / "report.json"
    report = reader.read(report_path)
    old._closed(report, REPORT_KEYS, "saved_phase25_report")
    if (report["version"] != parent.VERSION or report["status"] != "source_evidence_probe_complete_not_selected"
            or any(report[key] is not True for key in ("computation_integrity_passed", "inputs_and_code_unchanged",
                "artifacts_unchanged", "submitted_role_calculation_complete"))
            or any(report[key] != [] for key in ("changed_inputs_or_code", "changed_artifacts", "failures"))
            or any(report[key] is not False for key in parent.POLICY_FALSE) or report["selected"] is not None
            or type(report["artifact_hashes"]) is not dict or len(report["artifact_hashes"]) != 147):
        raise ValueError("exact_completed_saved_phase25_parent_required")
    old._protect(protected, str(report_path), old._file_sha(report_path))
    old._protect_map(protected, report["artifact_hashes"])
    inventory = old._inventory(directory, report["artifact_hashes"], report_path)
    plan = reader.read(directory / "run-plan.json")
    old._closed(plan, PLAN_KEYS, "saved_phase25_creation_plan")
    if (plan["version"] != parent.VERSION or plan["source_authority"] != parent.AUTHORITY
            or plan["selection_policy"] != parent.SELECTION_POLICY or plan["selector_batch_size"] != 3
            or plan["all_batches_for_both_completions_planned"] is not True
            or plan["selected"] is not None or any(plan[key] is not False for key in parent.POLICY_FALSE)
            or plan["denominators"] != report["denominators"]):
        raise ValueError("exact_saved_parent_creation_policy_required")
    old._closed(report["denominators"], DENOMINATOR_KEYS, "saved_cohort_denominators")
    denoms = report["denominators"]
    for key in DENOMINATOR_KEYS:
        old._limit(denoms[key], "saved_denominator." + key)
    old._limit(report["fresh_native_preparations"], "saved_fresh_preparations")
    if (denoms["selected_contexts"] != 2 or denoms["registered_context_pool"] != 5
            or denoms["unexecuted_declared_contexts"] != denoms["declared_contexts"] - 2
            or denoms["unexecuted_declared_original_raw_lanes"] != denoms["declared_original_raw_lanes"] - denoms["selected_original_raw_lanes"]
            or report["fresh_native_preparations"] != 2):
        raise ValueError("exact_saved_cohort_complement_required")
    old._protect_map(protected, plan["inputs"])
    old._protect_map(protected, plan["code"])
    changed = old._guard(protected)
    if changed:
        raise ValueError("saved_parent_creation_SHA256_changed:" + repr(changed))
    rows = reader.read(directory / "context-index.json")
    if type(rows) is not list or len(rows) != 2 or [row["context_key"] for row in rows] != plan["selected_contexts"]:
        raise ValueError("exact_saved_two_context_order_required")
    contexts = [_context(row, plan, report, reader, protected, settings) for row in rows]
    if sum(len(case["scope"]["raw_lanes"]) for case in contexts) != denoms["selected_original_raw_lanes"]:
        raise ValueError("exact_saved_selected_raw_lane_denominator_required")
    return {"parent": directory, "report": report, "plan": plan, "contexts": contexts,
        "hashes": protected, "inventory": inventory, "reader_counts": {"files_read": reader.read_files,
            "decoded_bytes": reader.decoded_bytes}, "settings": settings}


def _validate_result(record, case, job, settings):
    """Closed saved counts/refs only; no live issuer or producer invocation."""
    sealed._check(record, engine.PREFIX)
    old._closed(record["summary"], SUMMARY_FIELDS, "saved_contrast_summary")
    old._closed(record["flags"], RESULT_FLAGS, "saved_contrast_policy_flags")
    summary = record["summary"]
    for key in SUMMARY_FIELDS - {"pair_kind_counts"}:
        old._limit(summary[key], "saved_contrast_summary." + key)
    kinds = summary["pair_kind_counts"]
    if type(kinds) is not dict or set(kinds) - set(engine.KINDS):
        raise ValueError("closed_saved_pair_kind_counts_required")
    for key, value in kinds.items():
        old._limit(value, "saved_pair_kind." + key)
    entries, groups = job["entries"], {}
    for entry in entries:
        path = entry["native_path"]
        groups.setdefault((digest(path["key_ref"]), digest(path["bundle_ref"])), []).append(path["record_id"])
    expected = {tuple(pair) for group in groups.values() for pair in combinations(group, 2)}
    refs = [{"native_path_ref": sealed._ref(entry["native_path"]), "role_path_ref": sealed._ref(entry["role_path"]),
        "comparison_ref": entry["comparison_ref"], "explanation_ref": entry["explanation_ref"]} for entry in entries]
    held = record["status"] == "whole_saved_contrast_hold"
    if (record["status"] not in ("whole_saved_contrast_hold", "computed_saved_progression_contrasts_not_selected")
            or record["version"] != engine.VERSION or record["source_authority"] != AUTHORITY
            or record["scope_ref"] != sealed._ref(case["scope"]) or record["lattice_ref"] != sealed._ref(case["lattice"])
            or record["analysis_span"] != case["scope"]["analysis_span"] or record["binding"] != case["scope"]["binding"]
            or record["logical_universe"] != case["lattice"]["universe"] or record["submitted_entry_refs"] != refs
            or record["resource_limits"] != {key: settings[key] for key in ("max_pairs", "work_budget")}
            or any(value is not False for value in record["flags"].values())
            or any(record[key] is not None for key in ("selected", "rank", "confidence"))
            or summary["submitted_entries"] != len(entries) or record["query_plan"]["entry_count"] != len(entries)
            or summary["planned_same_key_same_bundle_pairs"] != len(expected) or record["query_plan"]["planned_pairs"] != len(expected)
            or summary["computed_pairs"] != len(record["pairs"])
            or summary["withheld_pairs"] != len(expected) - len(record["pairs"])
            or summary["raw_time_conserved_entries"] != len(record["facets"])
            or summary["alias_control_pairs"] != sum(pair["alias_control"] is True for pair in record["pairs"])
            or kinds != dict(sorted(Counter(pair["comparison_kind"] for pair in record["pairs"]).items()))
            or any(summary[kind + "_pairs"] != kinds.get(kind, 0) for kind in engine.KINDS)
            or (held and (record["pairs"] or record["facets"]))
            or (not held and len(record["facets"]) != len(entries))):
        raise ValueError("exact_saved_contrast_summary_ref_or_whole_hold_required")
    old._limit(record["query_plan"]["planned_work"], "saved_contrast_planned_work")
    if not held:
        if {tuple((pair["left_path_ref"]["record_id"], pair["right_path_ref"]["record_id"])) for pair in record["pairs"]} != expected:
            raise ValueError("complete_same_key_same_completion_pair_set_required")
        if [facet["native_path_ref"] for facet in record["facets"]] != [ref["native_path_ref"] for ref in refs]:
            raise ValueError("exact_saved_all_entry_facet_order_required")
        indexed = {entry["native_path"]["record_id"]: entry for entry in entries}
        for pair in record["pairs"]:
            left, right = (indexed[pair[name]["record_id"]] for name in ("left_path_ref", "right_path_ref"))
            if (pair["left_path_ref"] != sealed._ref(left["native_path"])
                    or pair["right_path_ref"] != sealed._ref(right["native_path"])
                    or pair["left_role_path_ref"] != sealed._ref(left["role_path"])
                    or pair["right_role_path_ref"] != sealed._ref(right["role_path"])
                    or pair["key_ref"] != left["native_path"]["key_ref"] or pair["key_ref"] != right["native_path"]["key_ref"]
                    or pair["bundle_ref"] != left["native_path"]["bundle_ref"] or pair["bundle_ref"] != right["native_path"]["bundle_ref"]
                    or type(pair["alias_control"]) is not bool or pair["raw_time_conserved"] is not True
                    or any(pair[key] is not None for key in ("selected", "rank", "confidence"))):
                raise ValueError("exact_saved_pair_content_refs_and_same_premises_required")
        for facet, ref in zip(record["facets"], refs):
            if any(facet[key] != value for key, value in ref.items()):
                raise ValueError("exact_saved_facet_entry_parent_refs_required")


def run(directory, output, **limits):
    started, output = perf_counter(), Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("append_only_new_direct_workspace_output_required")
    settings = _settings(limits)  # Every cap is checked before any saved file read.
    data = load_inputs(directory, **settings)
    code = {str(path.resolve()): old._file_sha(path) for path in _code_paths()}
    protected = deepcopy(data["hashes"])
    old._protect_map(protected, code)
    output.mkdir()
    artifacts, rows, failures, summaries = {}, [], [], []
    plan = {"version": VERSION, "parent": str(data["parent"]), "inputs": deepcopy(data["hashes"]), "code": code,
        "settings": settings, "denominators": deepcopy(data["report"]["denominators"]),
        "parent_report_sha256": old._file_sha(data["parent"] / "report.json"), "parent_inventory_files": len(data["inventory"]),
        "parent_source_size_manifest": deepcopy(data["plan"]["source_size_manifest"]),
        "parent_selected_contexts": deepcopy(data["plan"]["selected_contexts"]),
        "reader_counts": data["reader_counts"], "source_authority": AUTHORITY,
        "all_cross_batch_entries_per_saved_completion": True, "fresh_native_preparations": 0,
        "selected": None, **{key: False for key in POLICY_FALSE}}
    old._save_json(output, "run-plan.json", plan, artifacts)
    for case in data["contexts"]:
        for job in case["jobs"]:
            try:
                record = engine.compare(case["scope"], case["lattice"], job["entries"],
                    bundles={job["bundle"]["record_id"]: job["bundle"]}, max_pairs=settings["max_pairs"], work_budget=settings["work_budget"])
                _validate_result(record, case, job, settings)
                encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
                if len(encoded) > settings["max_output_record_bytes"]:
                    raise ValueError("whole_saved_output_record_byte_budget_no_partial_save")
                info = old._save_record(output, "contrasts", record, engine.PREFIX, artifacts)
                summaries.append(deepcopy(record["summary"]))
                rows.append({"context_key": deepcopy(case["context_key"]), "kind": job["kind"],
                    "full_IR": case["full_IR"], "scope": case["scope_info"], "native_lattice": case["lattice_info"],
                    "source_panel": case["panel_info"], "original_source_files": case["original_source_files"],
                    "bundle": deepcopy(job["bundle_info"]), "saved_batch_refs": job["saved_batch_refs"],
                    "submitted_entries": len(job["entries"]), "contrast": info, "summary": deepcopy(record["summary"]),
                    "query_plan": deepcopy(record["query_plan"]), "status": record["status"], "reasons": deepcopy(record["reasons"]), "error": None})
            except Exception as exc:
                error = f"{type(exc).__name__}:{exc}"
                failures.append({"context_key": deepcopy(case["context_key"]), "kind": job["kind"], "error": error})
                rows.append({"context_key": deepcopy(case["context_key"]), "kind": job["kind"], "contrast": None,
                    "summary": None, "status": "saved_contrast_calculation_failure", "error": error})
    old._save_json(output, "context-index.json", rows, artifacts)
    changed = old._guard(protected)
    if {str(path.resolve()) for path in _code_paths()} != set(code):
        changed.append("creation_code_inventory_changed")
    if {str(path.resolve()) for path in data["parent"].rglob("*") if path.is_file()} != data["inventory"]:
        changed.append("saved_parent_inventory_changed")
    changed_artifacts = old._guard(artifacts)
    if {str(path.resolve()) for path in output.rglob("*") if path.is_file()} != set(artifacts):
        changed_artifacts.append("new_artifact_inventory_changed")
    integrity = not failures and not changed and not changed_artifacts
    numeric, kinds = Counter(), Counter()
    for summary in summaries:
        for key, value in summary.items():
            if key == "pair_kind_counts":
                kinds.update(value)
            else:
                old._limit(value, "saved_contrast_summary." + key)
                numeric[key] += value
    report = {"version": VERSION, "status": "saved_progression_contrast_probe_complete_not_selected" if integrity else
        "saved_progression_contrast_probe_failed", "computation_integrity_passed": integrity,
        "inputs_and_code_unchanged": not changed, "artifacts_unchanged": not changed_artifacts,
        "changed_inputs_or_code": changed, "changed_artifacts": changed_artifacts, "failures": failures,
        "artifact_hashes": artifacts, "denominators": deepcopy(data["report"]["denominators"]),
        "saved_completion_groups": len(rows), "computed_completion_groups": sum(row["status"] == "computed_saved_progression_contrasts_not_selected" for row in rows),
        "whole_contrast_holds": sum(row["status"] == "whole_saved_contrast_hold" for row in rows),
        "summary": {**dict(numeric), "pair_kind_counts": dict(kinds)} if integrity else None,
        "source_authority": AUTHORITY, "fresh_native_preparations": 0, "selected": None,
        "elapsed_seconds": perf_counter() - started, **{key: False for key in POLICY_FALSE},
        "limits": ["Registered saved metadata/body integrity is not live native authority or producer replay.",
            "All fifty entries per same-context completion are compared across old storage batches, preserving every key.",
            "Pair/work limits hold the whole request; file/read caps fail closed before a new output is created.",
            "Counts concern conditional evidence, not accuracy, confidence, selected harmony/NCT, training or generation."]}
    old.storage.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-pairs", type=int, default=SETTINGS["max_pairs"])
    parser.add_argument("--work-budget", type=int, default=SETTINGS["work_budget"])
    args = parser.parse_args()
    run(args.parent, args.output, max_pairs=args.max_pairs, work_budget=args.work_budget)


if __name__ == "__main__":
    main()
