"""Append-only lossless shape/key relations, not harmony or motion decisions.

The protected indexed parent supplies every origin. Bulk weighted function
coverage and explicit function-query controls have separate denominators.
Saved historical profile/motion results are preserved, not freshly evaluated.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from . import factor_indexed_trial as previous
from . import factor_indexed_hypotheses as indexed_engine
from . import factor_expanded_hypotheses as frozen
from . import factor_musical_trial as storage
from . import harmony_frozen_context_lineage_trial as parent
from .musical_pattern_observation import digest

ROOT = parent.ROOT
VERSION = "factor-function-relation-trial-0.1.0"
POLICY_FALSE = previous.POLICY_FALSE
SAMPLING = "first_last_tuple_one_cyclic_key_all_slots_and_ten_function_shapes_not_music_rank"


def _registered(data, row, stage):
    info = row.get(stage)
    if not isinstance(info, dict):
        raise ValueError("complete_registered_indexed_stage_required:" + stage)
    path = Path(info["artifact"]).resolve(strict=True)
    folder = "indices" if stage == "indexed_universe" else "queries"
    if (path.parent != data["directory"] / folder
            or data["hashes"].get(str(path)) != info["sha256"]):
        raise ValueError("foreign_or_unregistered_indexed_stage:" + stage)
    value = parent._load(path, data["hashes"], compressed=True)
    if stage == "indexed_universe":
        frozen._check(value, indexed_engine.PREFIX)
        if (not indexed_engine._same(frozen._ref(value), info["record_ref"])
                or value["status"] != info["status"] or path.name != value["record_id"] + ".json.gz"):
            raise ValueError("indexed_stage_identity_or_status_mismatch")
    return value


def _check_samples(samples, row, scope, hypotheses, index, plan):
    """Saved provenance + exact function bodies; no fresh motion/profile replay."""
    requests = previous.sample_requests(hypotheses, index)
    fields = {"version", "context_key", "index_ref", "sampling", "requests", "queries",
        "shared_control_bundle_ref", "same_bundle_comparisons", "all_logical_paths_evaluated",
        "selected", "musical_accuracy_measured"}
    indexed_engine._closed(samples, fields, "saved_indexed_query_envelope")
    if (samples["version"] != previous.VERSION
            or not indexed_engine._same(samples["context_key"], row["context_key"])
            or not indexed_engine._same(samples["index_ref"], frozen._ref(index))
            or samples["sampling"] != plan["sampling"]
            or not indexed_engine._same(samples["requests"], requests)
            or samples["all_logical_paths_evaluated"] is not False
            or samples["musical_accuracy_measured"] is not False or samples["selected"] is not None
            or type(samples["queries"]) is not list or type(samples["same_bundle_comparisons"]) is not list
            or len(samples["queries"]) != len(requests)
            or len(samples["same_bundle_comparisons"]) != len(requests)
            or type(row["query_samples"]["queries"]) is not int
            or row["query_samples"]["queries"] != len(requests)):
        raise ValueError("saved_indexed_query_policy_identity_or_denominator_mismatch")
    groups = {g["group_id"]: g for g in index["path_groups"]}
    variants = {v["variant_id"]: v["variant"] for v in index["variant_inventory"]}
    keys = {k["record_id"]: k for k in index["keys"]}
    bundles = {}
    for request, query, assessment in zip(requests, samples["queries"], samples["same_bundle_comparisons"]):
        frozen._check(query, indexed_engine.QUERY_PREFIX)
        frozen._check(assessment, indexed_engine.ASSESSMENT_PREFIX)
        indexed_engine._closed(query, {"version", "contract", "index_ref", "scope_ref", "hypotheses_ref",
            "tuple_ref", "logical_tuple", "group_ref", "variant_ids", "key_ref", "analysis_span", "logical_universe",
            "resource_limits", "profiles", "functions", "bundle_inventory", "same_bundle_assessments", "computed_counts",
            "status", "reasons", "selected", "rank", "confidence", "flags", "record_id", "record_sha256"}, "saved_query")
        indexed_engine._closed(assessment, {"version", "contract", "scope_ref", "index_ref", "query_ref", "tuple_ref",
            "group_ref", "variant_ids", "key_ref", "bundle_ref", "symbolic_universe_ref", "logical_universe",
            "resource_limits", "rows", "joint_motion_shape_refs", "computed_counts", "unqueried_logical_tuple_count",
            "unknown_product_groups", "unqueried_tuple_compatibility", "link_basis", "same_complete_bundle_for_all_function_assumptions",
            "bundle_status", "all_no_link_control", "status", "reasons", "selected", "rank", "confidence", "flags",
            "record_id", "record_sha256"}, "saved_assessment")
        group, key = groups[request["group_id"]], keys[request["key_id"]]
        logical = indexed_engine._tuple_identity(index, group, request["variant_ids"], key)
        expected_refs = {"version": indexed_engine.VERSION, "contract": indexed_engine._contract(),
            "index_ref": frozen._ref(index), "scope_ref": frozen._ref(scope),
            "hypotheses_ref": frozen._ref(hypotheses), "variant_ids": request["variant_ids"],
            "key_ref": frozen._ref(key), "tuple_ref": frozen._ref(logical),
            "group_ref": {"group_id": group["group_id"], "indexed_group_id": group["indexed_group_id"]},
            "logical_universe": index["universe"], "resource_limits": {"max_motion_pairs": plan["settings"]["max_motion_pairs"]},
            "selected": None, "rank": None, "confidence": None, "flags": indexed_engine._flags()}
        if (any(not indexed_engine._same(query.get(name), value) for name, value in expected_refs.items())
                or not indexed_engine._same(query["logical_tuple"], logical)
                or query["status"] != "computed_logical_tuple_not_selected" or query["reasons"] != []
                or not indexed_engine._same(query["analysis_span"], index["analysis_span"])):
            raise ValueError("saved_indexed_query_reference_or_policy_mismatch")
        segments = [variants[ref] for ref in request["variant_ids"]]
        expected_functions = []
        for position, source in enumerate(segments):
            target = segments[position + 1] if position + 1 < len(segments) else None
            for family in frozen.FAMILIES:
                for quality in ("M", "m"):
                    function = frozen._function(scope, source, target, key["segments"][0], family, quality)
                    function["function_id"] = "fmifunction_" + digest([frozen._ref(logical), position, function])[:24]
                    expected_functions.append(function)
        if (type(query["functions"]) is not list or len(query["functions"]) != len(expected_functions)
                or any(not indexed_engine._same({k: v for k, v in actual.items() if k != "motion"}, expected)
                       for actual, expected in zip(query["functions"], expected_functions))
                or len(query["profiles"]) != len(segments)):
            raise ValueError("saved_indexed_query_function_body_or_count_mismatch")
        for position, profile in enumerate(query["profiles"]):
            if profile["segment_ref"] != segments[position]["segment_id"]:
                raise ValueError("saved_indexed_profile_origin_mismatch")
        for bundle in query["bundle_inventory"]:
            frozen._check(bundle, indexed_engine.BUNDLE_PREFIX)
            if not indexed_engine._same(bundle.get("index_ref"), frozen._ref(index)):
                raise ValueError("saved_indexed_bundle_foreign_index")
            prior = bundles.get(bundle["record_id"])
            if prior is None:
                expected = indexed_engine._new_bundle(scope, index, index["keys"], bundle["required_links"])
                if not indexed_engine._same(bundle, expected):
                    raise ValueError("saved_indexed_bundle_geometry_or_policy_mismatch")
                bundles[bundle["record_id"]] = bundle
            elif not indexed_engine._same(prior, bundle):
                raise ValueError("saved_indexed_bundle_identity_conflict")
        if (not query["bundle_inventory"] or any(not indexed_engine._same(assessment.get(name), value)
                for name, value in expected_refs.items() if name != "hypotheses_ref")
                or not indexed_engine._same(assessment["query_ref"], frozen._ref(query))
                or not indexed_engine._same(assessment["bundle_ref"], samples["shared_control_bundle_ref"])
                or not indexed_engine._same(assessment["symbolic_universe_ref"], frozen._ref(index["universe"]))
                or len(assessment["rows"]) != len(expected_functions)
                or [r["function_id"] for r in assessment["rows"]] != [r["function_id"] for r in expected_functions]):
            raise ValueError("saved_indexed_assessment_reference_or_policy_mismatch")
        control = bundles.get(assessment["bundle_ref"]["record_id"])
        if control is None or not indexed_engine._same(frozen._ref(control), assessment["bundle_ref"]) or control["all_no_link_control"] is not True:
            raise ValueError("saved_indexed_shared_actual_control_missing")
        expected_incidence = []
        for bundle in query["bundle_inventory"]:
            links = {tuple(pair) for item in bundle["entries"] if item["witness"] is not None
                     for pair in item["witness"]["assignment"]["links"]}
            supported = [function["function_id"] for function in query["functions"] if any(
                bundle["status"] == "complete_all_lane_witness" and option["status"] == "conditional_joint_motion_shape"
                and {tuple(pair) for pair in option["required_links"]} <= links
                for option in function["motion"]["joint_options"])]
            expected_incidence.append({"bundle_ref": frozen._ref(bundle), "tuple_ref": frozen._ref(logical),
                "joint_motion_shape_refs": supported, "symbolic_universe_ref": frozen._ref(index["universe"]),
                "same_complete_bundle_for_all_function_assumptions": bundle["status"] == "complete_all_lane_witness",
                "link_basis": "actual_materialized_completion_links_in_all_declared_lanes",
                "unqueried_tuple_compatibility": "unassessed_not_false_not_materialized",
                "sparse_universe_predicate": "query_any_exact_indexed_tuple_under_this_same_complete_bundle", "selected": None})
        if not indexed_engine._same(query["same_bundle_assessments"], expected_incidence):
            raise ValueError("saved_indexed_query_actual_bundle_incidence_mismatch")
        links = {tuple(pair) for item in control["entries"] if item["witness"] is not None
                 for pair in item["witness"]["assignment"]["links"]}
        complete = control["status"] == "complete_all_lane_witness"
        expected_rows = []
        for function in query["functions"]:
            motion = function["motion"]
            roles = list(motion["edge_options"])
            matched = {role: [deepcopy(edge["required_link"]) for edge in edges
                             if edge["qualified"] and tuple(edge["required_link"]) in links]
                       for role, edges in motion["edge_options"].items()}
            blockers = deepcopy(motion["blockers"])
            if not complete:
                blockers.extend(control["reasons"])
                blockers.append("existing_complete_all_lane_bundle_withheld")
            if motion["status"] == "whole_group_budget_abstention":
                status = "whole_group_budget_abstention"
            elif complete and not blockers and roles and all(matched[role] for role in roles):
                status = "conditional_joint_motion_shape_under_existing_bundle"
            else:
                status = "withheld_under_existing_bundle"
                blockers.extend(role + "_required_link_absent_from_existing_actual_witness" for role in roles if not matched[role])
            expected_rows.append({"function_id": function["function_id"], "family": function["family"],
                "target_quality": function["target_quality"], "source_segment_ref": function["source_segment_ref"],
                "status": status, "critical_roles": roles, "matched_actual_links_by_role": matched,
                "all_critical_roles_in_same_complete_bundle": status == "conditional_joint_motion_shape_under_existing_bundle",
                "blockers": sorted(set(blockers)), "function_confirmed": None,
                "cadence_NCT_and_actual_harmony_identity": "unassessed"})
        expected_assessment = {"rows": expected_rows, "joint_motion_shape_refs": [r["function_id"] for r in expected_rows
            if r["status"] == "conditional_joint_motion_shape_under_existing_bundle"],
            "unqueried_logical_tuple_count": max(0, index["universe"]["logical_tuples"] - 1),
            "unknown_product_groups": index["universe"]["unknown_product_groups"],
            "unqueried_tuple_compatibility": "unassessed_not_false_not_materialized",
            "link_basis": "actual_materialized_completion_links_in_all_declared_lanes",
            "same_complete_bundle_for_all_function_assumptions": complete, "bundle_status": control["status"],
            "all_no_link_control": control["all_no_link_control"], "status": "computed_compatibility_under_existing_bundle",
            "reasons": []}
        if any(not indexed_engine._same(assessment.get(name), value) for name, value in expected_assessment.items()):
            raise ValueError("saved_indexed_assessment_actual_control_incidence_mismatch")
        query_counts = {"queried_tuples": 1, "profile_uses": len(segments),
            "function_shapes": len(expected_functions), "bundles": len(query["bundle_inventory"]),
            "conditional_joint_motion_shapes": sum(f["motion"]["status"] == "conditional_joint_motion_shape"
                                                  for f in query["functions"])}
        assessment_counts = {"compatibility_tuples": 1, "function_shapes": len(expected_functions),
            "conditional_joint_motion_shapes": sum(r["status"] == "conditional_joint_motion_shape_under_existing_bundle"
                                                  for r in assessment["rows"])}
        if (not indexed_engine._same(query["computed_counts"], query_counts)
                or not indexed_engine._same(assessment["computed_counts"], assessment_counts)
                or any(r["function_confirmed"] is not None for r in assessment["rows"])
                or any(r["cadence_NCT_and_actual_harmony_identity"] != "unassessed" for r in assessment["rows"])):
            raise ValueError("saved_indexed_query_or_assessment_accounting_mismatch")
    if not requests and samples["shared_control_bundle_ref"] is not None:
        raise ValueError("empty_indexed_queries_cannot_invent_control_bundle")


def load_inputs(directory):
    """Guard registered indexed storage and the complete historical chain."""
    directory = Path(directory).resolve(strict=True)
    report_path = directory / "report.json"
    report = parent.read(report_path)
    if (report.get("version") != previous.VERSION
            or any(report.get(k) is not True for k in ("scope_calculation_complete", "computation_integrity_passed",
                "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged"))
            or report.get("cohort_complete") is not False or report.get("all_logical_paths_evaluated") is not False
            or report.get("selected") is not None
            or any(report.get(k) != [] for k in ("failures", "changed_inputs_or_code", "changed_artifacts"))
            or any(report.get(k) is not False for k in POLICY_FALSE)):
        raise ValueError("completed_unselected_indexed_parent_required")
    hashes = {}
    parent._guard({str(report_path): parent.file_digest(report_path)}, hashes)
    if any(not Path(p).is_relative_to(directory) for p in report["artifact_hashes"]):
        raise ValueError("indexed_parent_artifact_outside_registered_directory")
    parent._guard(report["artifact_hashes"], hashes)
    inventory = parent._inventory(directory, hashes)
    plan = parent._load(directory / "run-plan.json", hashes)
    if (plan.get("version") != previous.VERSION
            or plan.get("sampling") != "first_last_tuple_per_nonempty_group_one_key_cyclic_storage_order_not_music_rank"
            or any(plan.get(k) is not False for k in ("cohort_complete", "old_selector_or_analysis_reexecuted",
                "all_logical_paths_evaluated", "source_labels_used_for_inference", "old_paths_or_bundles_extended", "production_modified"))):
        raise ValueError("indexed_parent_plan_policy_mismatch")
    indexed_engine._closed(plan["settings"], {"max_variants", "max_motion_pairs"}, "saved_indexed_settings")
    for name, value in plan["settings"].items():
        previous._limit(value, name)
    parent._guard(plan["inputs"], hashes)
    parent._guard(plan["code"], hashes)
    expanded = previous.load_inputs(plan["expanded"])
    if (plan["parent_report_sha256"] != parent.file_digest(expanded["directory"] / "report.json")
            or any(not indexed_engine._same(plan[k], expanded["plan"][k]) for k in
                   ("declared_contexts", "declared_units", "selected_contexts", "selection"))):
        raise ValueError("indexed_parent_declared_lineage_mismatch")
    rows = parent._load(directory / "context-index.json", hashes)
    if (not indexed_engine._same([r["context_key"] for r in rows], plan["selected_contexts"])
            or len({tuple(r["context_key"]) for r in rows}) != len(rows)
            or len(rows) != report["summary"]["contexts"]):
        raise ValueError("indexed_parent_context_denominator_mismatch")
    expected_artifacts = {str(directory / name) for name in ("run-plan.json", "context-index.json")}
    expected_artifacts.update(str(Path(row[stage]["artifact"]).resolve(strict=True)) for row in rows
                              for stage in ("indexed_universe", "query_samples"))
    if set(report["artifact_hashes"]) != expected_artifacts:
        raise ValueError("indexed_parent_exact_artifact_inventory_mismatch")
    data = {"directory": directory, "report": report, "plan": plan, "rows": rows,
            "hashes": hashes, "inventory": inventory, "expanded": expanded}
    totals = Counter()
    for row, original in zip(rows, expanded["rows"]):
        if (row["status"] != "index_and_technical_queries_saved_not_selected" or row["error"] is not None
                or row["old_row_sha256"] != digest(original)
                or any(not indexed_engine._same(row[k], original[k]) for k in
                       ("old_groups", "old_lane_refs", "expanded_scope", "hypotheses"))
                or not indexed_engine._same(row["old_hypothesis_counts"], original["hypothesis_counts"])
                or not indexed_engine._same(row["old_assessment_counts"], original["assessment_counts"])):
            raise ValueError("indexed_parent_original_context_or_groups_mismatch")
        scope = previous._registered(expanded, original, "expanded_scope", "fmes_")
        hypotheses = previous._registered(expanded, original, "hypotheses", frozen.PREFIX)
        index = _registered(data, row, "indexed_universe")
        expected_index = frozen._seal(indexed_engine._body(scope, hypotheses,
            {c["catalog_id"]: c for c in hypotheses["catalog_inventory"]}, plan["settings"]["max_variants"]), indexed_engine.PREFIX)
        if not indexed_engine._same(index, expected_index) or not indexed_engine._same(row["index_counts"], index["summary"]):
            raise ValueError("indexed_parent_current_contract_or_complete_origin_mismatch")
        samples = _registered(data, row, "query_samples")
        if Path(row["query_samples"]["artifact"]).name != index["record_id"] + ".json.gz":
            raise ValueError("indexed_parent_query_filename_mismatch")
        _check_samples(samples, row, scope, hypotheses, index, plan)
        totals.update(contexts=1, old_raw_lanes=len(row["old_lane_refs"]), old_groups=len(row["old_groups"]),
            indexed_groups=len(index["path_groups"]), ready_factorized_groups=sum(g["status"] == "ready_factorized_group" for g in index["path_groups"]),
            logical_paths=index["summary"]["logical_paths"], logical_path_key_tuples=index["summary"]["logical_path_key_tuples"],
            logical_function_rows=index["summary"]["logical_function_shapes"], unknown_logical_groups=index["summary"]["unknown_product_groups"],
            origin_variants=len(index["variant_inventory"]), shared_profile_descriptors=len(index["profile_inventory"]),
            queried_path_key_tuples=len(samples["queries"]), queried_function_rows=sum(len(q["functions"]) for q in samples["queries"]),
            same_bundle_technical_comparisons=len(samples["same_bundle_comparisons"]))
    expected_summary = {**dict(totals), "old_planned_paths": expanded["report"]["summary"]["planned_paths"],
        "old_unknown_path_group_counts": expanded["report"]["summary"]["unknown_path_group_counts"],
        "declared_contexts": len(plan["declared_contexts"]), "declared_original_raw_lanes": len(plan["declared_units"]),
        "unexecuted_original_contexts": len(plan["declared_contexts"]) - len(rows),
        "unexecuted_original_raw_lanes": len(plan["declared_units"]) - totals["old_raw_lanes"],
        "context_status_counts": dict(Counter(r["status"] for r in rows))}
    if not indexed_engine._same(report["summary"], expected_summary):
        raise ValueError("indexed_parent_saved_or_unexecuted_denominator_mismatch")
    return data


def load_case(data, row):
    original = next(r for r in data["expanded"]["rows"] if r["context_key"] == row["context_key"])
    return (*previous.load_case(data["expanded"], original), _registered(data, row, "indexed_universe"))


def sample_requests(hypotheses, index):
    groups = {g["group_id"]: g for g in index["path_groups"]}
    return [{**request, "slot_index": position, "family": family, "quality": quality}
        for request in previous.sample_requests(hypotheses, index)
        for position in range(len(groups[request["group_id"]]["slots"]))
        for family in frozen.FAMILIES for quality in ("M", "m")]


def run(indexed, output, *, max_kernels=65536):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("trial_output_must_be_new_direct_workspace_child")
    previous._limit(max_kernels, "max_kernels")
    from . import factor_function_relations as engine
    data = load_inputs(indexed)
    ancestors = [("indexed", data), ("expanded", data["expanded"]),
        ("prerequisite", data["expanded"]["prerequisites"]), ("family", data["expanded"]["prerequisites"]["family"])]
    inputs = {p: value for _, ancestor in ancestors for p, value in ancestor["hashes"].items()}
    code = {str(p.resolve()): parent.file_digest(p) for p in parent._code_paths()}
    plan = {"version": VERSION, "indexed": str(data["directory"]),
        "parent_report_sha256": parent.file_digest(data["directory"] / "report.json"), "inputs": deepcopy(inputs),
        "code": code, "settings": {"max_kernels": max_kernels},
        **{k: deepcopy(data["plan"][k]) for k in ("declared_contexts", "declared_units", "selected_contexts", "selection")},
        "sampling": SAMPLING, "cohort_complete": False, "old_selector_or_analysis_reexecuted": False,
        "all_logical_paths_evaluated": False, "source_labels_used_for_inference": False,
        "old_paths_or_bundles_extended": False, "production_modified": False,
        "profiles_evaluated": False, "motion_evaluated": False, "same_bundle_evaluated": False}
    output.mkdir()
    artifacts, rows, failures, totals = {}, [], [], Counter()
    shape_totals, kind_totals = dict.fromkeys(engine.SHAPE_STATES, 0), dict.fromkeys(engine.FUNCTION_KINDS, 0)
    storage._save(output, "run-plan.json", plan, artifacts)
    for row in data["rows"]:
        started_case = perf_counter()
        entry = {"context_key": deepcopy(row["context_key"]), "old_row_sha256": digest(row),
            **{k: deepcopy(row[k]) for k in ("old_groups", "old_lane_refs", "old_hypothesis_counts", "old_assessment_counts",
                "expanded_scope", "hypotheses", "indexed_universe", "index_counts")},
            "relations": None, "function_samples": None, "status": "not_calculated", "error": None}
        # Parent-known denominators survive ANY later relation/query failure.
        count = row["index_counts"]
        totals.update(contexts=1, old_raw_lanes=len(row["old_lane_refs"]), old_groups=len(row["old_groups"]),
            indexed_groups=count["groups"], logical_paths=count["logical_paths"],
            logical_path_key_tuples=count["logical_path_key_tuples"], logical_function_rows=count["logical_function_shapes"],
            unknown_logical_groups=count["unknown_product_groups"], origin_variants=count["indexed_variants"],
            shared_profile_descriptors=count["shared_profile_descriptors"])
        print(f"[{len(rows)+1}/{len(data['rows'])}] function relations {row['context_key'][0]}", flush=True)
        owned, before = None, None
        try:
            packet, ir, extension, scope, h, assessment, index = load_case(data, row)
            owned = [packet, ir, extension, scope, h, assessment, index]
            before = digest(owned)
            relations = engine.build_relations(ir, scope, h, index, max_kernels=max_kernels)
            path = storage._save(output, "relations/" + relations["record_id"] + ".json.gz", relations, artifacts, compressed=True)
            entry["relations"] = {"artifact": str(path), "sha256": artifacts[str(path)],
                "record_ref": frozen._ref(relations), "status": relations["status"]}
            entry["relation_counts"] = deepcopy(relations["summary"])
            for name in ("semantic_types", "planned_source_kernels", "materialized_source_kernels",
                    "shared_target_relations", "shared_key_projections", "factored_function_rows",
                    "unassessed_function_rows", "conditional_function_shape_rows", "withheld_function_shape_rows",
                    "terminal_target_rows", "literal_profiles_computed", "actual_endpoint_pairs_computed",
                    "motion_groups_computed", "same_bundle_assessments_computed"):
                totals[name] += relations["summary"][name]
            for name, count in relations["summary"]["shape_state_counts"].items():
                shape_totals[name] += count
            for name, count in relations["summary"]["function_kind_counts"].items():
                kind_totals[name] += count
            requests = sample_requests(h, index)
            session = engine.prepare_relations(ir, scope, h, index, relations) if requests else None
            queries = [engine.query_function_prepared(session, **request) for request in requests]
            samples = {"version": VERSION, "context_key": deepcopy(row["context_key"]), "index_ref": frozen._ref(index),
                "relations_ref": frozen._ref(relations), "sampling": SAMPLING, "requests": requests, "queries": queries,
                "selected": None, "musical_accuracy_measured": False, "profiles_evaluated": False,
                "motion_evaluated": False, "all_logical_paths_evaluated": False}
            path = storage._save(output, "function-samples/" + relations["record_id"] + ".json.gz", samples, artifacts, compressed=True)
            entry["function_samples"] = {"artifact": str(path), "sha256": artifacts[str(path)],
                "requests": len(requests), "queries": len(queries)}
            totals["queried_function_rows"] += sum(q.get("function") is not None for q in queries)
            totals["technical_function_requests"] += len(requests)
            entry["status"] = "relations_and_function_queries_saved_not_selected"
        except Exception as exc:
            entry["status"] = "calculation_failure"
            entry["error"] = f"{type(exc).__name__}:{exc}"
            failures.append({"context_key": deepcopy(row["context_key"]), "error": entry["error"]})
        if owned is not None and before != digest(owned):
            entry["status"], entry["error"] = "calculation_failure", "ValueError:function_relation_trial_parent_or_IR_mutated"
            if not any(f == {"context_key": entry["context_key"], "error": entry["error"]} for f in failures):
                failures.append({"context_key": deepcopy(entry["context_key"]), "error": entry["error"]})
        entry["elapsed_seconds"] = perf_counter() - started_case
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
    denominator = (indexed_engine._same([r["context_key"] for r in rows], plan["selected_contexts"])
        and totals["old_raw_lanes"] == data["report"]["summary"]["old_raw_lanes"]
        and totals["old_groups"] == data["report"]["summary"]["old_groups"])
    integrity = not failures and not changed and not changed_artifacts
    report = {"version": VERSION, "scope_calculation_complete": bool(integrity and denominator),
        "computation_integrity_passed": bool(integrity), "selected_denominators_complete": bool(denominator),
        "inputs_and_code_unchanged": not changed, "artifacts_unchanged": not changed_artifacts,
        "changed_inputs_or_code": changed, "changed_artifacts": changed_artifacts, "failures": failures,
        "artifact_hashes": deepcopy(artifacts), "summary": {**dict(totals),
            "shape_state_counts": shape_totals, "function_kind_counts": kind_totals,
            "old_planned_paths": data["report"]["summary"]["old_planned_paths"],
            "old_unknown_path_group_counts": data["report"]["summary"]["old_unknown_path_group_counts"],
            "declared_contexts": len(plan["declared_contexts"]), "declared_original_raw_lanes": len(plan["declared_units"]),
            "unexecuted_original_contexts": len(plan["declared_contexts"]) - totals["contexts"],
            "unexecuted_original_raw_lanes": len(plan["declared_units"]) - totals["old_raw_lanes"],
            "context_status_counts": dict(Counter(r["status"] for r in rows))},
        "cohort_complete": False, "all_logical_paths_evaluated": False, "selected": None,
        **{k: False for k in POLICY_FALSE}, "profiles_evaluated": False, "motion_evaluated": False,
        "same_bundle_evaluated": False, "elapsed_seconds": perf_counter() - started,
        "limits": ["Bulk function-shape/key counts are not exhaustive profile, motion or actual bundle evaluation.",
            "False and unknown shape relations, every original variant and terminal multiplicity are preserved.",
            "Technical first/last query controls are not preferred musical interpretations.",
            "Registered historical profile/motion outputs are protected, not freshly replayed in this stage.",
            "No confirmed harmony, key, cadence, NCT, accuracy, training, gold, generation or production promotion."]}
    parent.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("indexed", "output"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--max-kernels", type=int, default=65536)
    report = run(**vars(parser.parse_args()))
    print(report["summary"], flush=True)
    return 0 if report["scope_calculation_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
