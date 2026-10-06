"""Append-only indexed universes and explicit technical queries, not winners.

All historical source gates, old budget holds and unexecuted denominators stay
visible. A symbolic Cartesian universe is not an exhaustively evaluated one.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from . import factor_expanded_trial as previous
from . import factor_expanded_hypotheses as frozen
from . import factor_expanded_scope as expanded_scope
from . import factor_musical_trial as storage
from . import harmony_frozen_context_lineage_trial as parent
from .musical_pattern_observation import digest

ROOT = parent.ROOT
VERSION = "factor-indexed-trial-0.1.0"
POLICY_FALSE = ("harmony_confirmed", "cadence_confirmed", "musical_accuracy_measured",
    "training_eligible", "gold_eligible", "generation_ready", "source_labels_used_for_inference",
    "core_or_production_modified", "old_paths_or_bundles_extended")


def _limit(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("explicit_nonnegative_integer_trial_limit_required:" + name)


def _registered(data, row, stage, prefix):
    info = row.get(stage)
    if not isinstance(info, dict):
        raise ValueError("complete_registered_expanded_stage_required:" + stage)
    path = Path(info["artifact"]).resolve(strict=True)
    if (path.parent != data["directory"] / stage
            or data["hashes"].get(str(path)) != info["sha256"]):
        raise ValueError("foreign_or_unregistered_expanded_stage:" + stage)
    record = parent._load(path, data["hashes"], compressed=True)
    frozen._check(record, prefix)
    if (frozen._ref(record) != info["record_ref"] or record["status"] != info["status"]
            or path.name != record["record_id"] + ".json.gz"):
        raise ValueError("expanded_stage_identity_or_status_mismatch:" + stage)
    return record


def load_inputs(directory):
    """Verify registered storage and the entire original prerequisite chain."""
    directory = Path(directory).resolve(strict=True)
    report_path = directory / "report.json"
    report = parent.read(report_path)
    if (report.get("version") != previous.VERSION
            or any(report.get(k) is not True for k in ("scope_calculation_complete",
                "computation_integrity_passed", "selected_denominators_complete",
                "inputs_and_code_unchanged", "artifacts_unchanged"))
            or report.get("cohort_complete") is not False or report.get("selected") is not None
            or any(report.get(k) != [] for k in ("failures", "changed_inputs_or_code", "changed_artifacts"))
            or any(report.get(k) is not False for k in POLICY_FALSE)):
        raise ValueError("completed_unselected_expanded_parent_required")
    hashes = {}
    parent._guard({str(report_path): parent.file_digest(report_path)}, hashes)
    if any(not Path(p).is_relative_to(directory) for p in report["artifact_hashes"]):
        raise ValueError("expanded_parent_artifact_outside_registered_directory")
    parent._guard(report["artifact_hashes"], hashes)
    inventory = parent._inventory(directory, hashes)
    plan = parent._load(directory / "run-plan.json", hashes)
    if (plan.get("version") != previous.VERSION or plan.get("cohort_complete") is not False
            or any(plan.get(k) is not False for k in ("old_selector_or_analysis_reexecuted",
                "old_paths_or_bundles_extended", "source_labels_used_for_inference", "production_modified"))):
        raise ValueError("expanded_parent_plan_policy_mismatch")
    parent._guard(plan["inputs"], hashes)
    parent._guard(plan["code"], hashes)
    prerequisites = previous.load_inputs(plan["prerequisites"])
    if (plan["parent_report_sha256"] != parent.file_digest(prerequisites["directory"] / "report.json")
            or any(plan[k] != prerequisites["plan"][k] for k in
                   ("declared_contexts", "declared_units", "selected_contexts", "selection"))):
        raise ValueError("expanded_parent_declared_lineage_mismatch")
    rows = parent._load(directory / "context-index.json", hashes)
    expected_artifacts = {str(directory / name) for name in ("run-plan.json", "context-index.json")}
    expected_artifacts.update(str(Path(row[stage]["artifact"]).resolve(strict=True))
        for row in rows for stage in ("expanded_scope", "hypotheses", "assessment"))
    if set(report["artifact_hashes"]) != expected_artifacts:
        raise ValueError("expanded_parent_exact_artifact_inventory_mismatch")
    if ([r["context_key"] for r in rows] != plan["selected_contexts"]
            or len({tuple(r["context_key"]) for r in rows}) != len(rows)
            or len(rows) != report["summary"]["contexts"]):
        raise ValueError("expanded_parent_context_denominator_mismatch")
    totals = Counter()
    for row, original in zip(rows, prerequisites["rows"]):
        original_lanes = [{"lane": deepcopy(lane["lane"]), "old_status": lane["old_geometry_status"],
            "old_graph_ref": None if lane["graph_snapshot"] is None else frozen._ref(lane["graph_snapshot"])}
            for lane in original["lane_inventory"]]
        if (row["status"] != "scope_calculation_complete_not_selected" or row["error"] is not None
                or row["old_context_row_sha256"] != digest(original)
                or row["old_view_ref"] != original["view_ref"] or row["old_groups"] != original["groups"]
                or row["old_lane_refs"] != original_lanes
                or row["parent_extension_ref"] != original["context_observation"]["record_ref"]):
            raise ValueError("expanded_parent_original_context_or_groups_mismatch")
        scope = _registered({"directory": directory, "hashes": hashes}, row, "expanded_scope", "fmes_")
        h = _registered({"directory": directory, "hashes": hashes}, row, "hypotheses", frozen.PREFIX)
        assessment = _registered({"directory": directory, "hashes": hashes}, row, "assessment", frozen.EVALUATION_PREFIX)
        if (scope["contract"] != expanded_scope._contract() or h["contract"] != frozen._contract()
                or assessment["contract"] != frozen._contract()
                or scope["binding"] != h["binding"] or scope["binding"] != assessment["binding"]
                or h["scope_ref"] != frozen._ref(scope) or assessment["scope_ref"] != frozen._ref(scope)
                or assessment["hypotheses_ref"] != frozen._ref(h)
                or row["analysis_span"] != scope["analysis_span"] or row["lane_inventory"] != scope["lane_inventory"]
                or row["hypothesis_counts"] != h["summary"] or row["assessment_counts"] != assessment["summary"]
                or h["flags"] != frozen._flags() or assessment["flags"] != frozen._flags()):
            raise ValueError("expanded_parent_scope_contract_or_lineage_mismatch")
        expected_plans = [{k: deepcopy(group[k]) for k in ("group_id", "status", "total_path_key_pairs",
            "total_function_shapes", "planned_same_bundle_assessments")} for group in assessment["groups"]]
        if (row["assessment_group_plans"] != expected_plans
                or [g["group_id"] for g in h["path_groups"]] != [g["group_id"] for g in assessment["groups"]]):
            raise ValueError("expanded_parent_comparison_group_denominator_mismatch")
        totals.update(contexts=1, expanded_raw_lanes=len(scope["raw_lanes"]), expanded_sounds=len(scope["sound_facts"]),
            old_raw_lanes=len(original["lane_inventory"]), old_groups=len(original["groups"]),
            planned_catalog_spans=len(h["catalog_inventory"]),
            materialized_catalogs=sum(c["supplier_catalog"] is not None for c in h["catalog_inventory"]),
            new_groups=len(h["path_groups"]),
            planned_paths=sum(g["planned_paths"] for g in h["path_groups"] if g["planned_paths"] is not None),
            unknown_path_group_counts=sum(g["planned_paths"] is None for g in h["path_groups"]),
            materialized_paths=sum(len(g["paths"]) for g in h["path_groups"]))
    summary = report["summary"]
    if (any(summary.get(k, 0) != value for k, value in totals.items())
            or summary["declared_contexts"] != len(plan["declared_contexts"])
            or summary["declared_original_raw_lanes"] != len(plan["declared_units"])
            or summary["unexecuted_original_contexts"] != len(plan["declared_contexts"]) - len(rows)
            or summary["unexecuted_original_raw_lanes"] != len(plan["declared_units"]) - totals["old_raw_lanes"]
            or Counter(summary["old_group_status_counts"]) != Counter(g["old_status"] for r in rows for g in r["old_groups"])):
        raise ValueError("expanded_parent_saved_or_unexecuted_denominator_mismatch")
    return {"directory": directory, "report": report, "plan": plan, "rows": rows,
            "hashes": hashes, "inventory": inventory, "prerequisites": prerequisites}


def load_case(data, row):
    original = next(r for r in data["prerequisites"]["rows"] if r["context_key"] == row["context_key"])
    packet, ir, extension = previous.load_case(data["prerequisites"], original)
    scope = _registered(data, row, "expanded_scope", "fmes_")
    h = _registered(data, row, "hypotheses", frozen.PREFIX)
    assessment = _registered(data, row, "assessment", frozen.EVALUATION_PREFIX)
    expanded_scope.validate_scope(scope, ir=ir, view=packet["context"]["view"],
        observation=packet["observation"], audit=packet["audit_packet"]["audit"], extension=extension,
        **{k: data["plan"]["settings"][k] for k in ("max_events", "max_factors", "max_edges")})
    if (row["parent_extension_ref"] != frozen._ref(extension)
            or row["old_context_span"] != packet["context"]["view"]["context_span"]):
        raise ValueError("expanded_parent_original_span_or_extension_mismatch")
    return packet, ir, extension, scope, h, assessment


def sample_requests(hypotheses, index=None):
    """First/last tuple controls; order is storage order, never a music rank."""
    catalogs = {c["catalog_id"]: c for c in hypotheses["catalog_inventory"]}
    keys = hypotheses["keys"]
    requests = []
    ready = None if index is None else {g["group_id"] for g in index["path_groups"]
                                        if g["status"] == "ready_factorized_group"}
    for position, group in enumerate(hypotheses["path_groups"]):
        if ready is not None and group["group_id"] not in ready:
            continue
        entries = [catalogs[c] for c in group["catalog_refs"]]
        if not keys or any(c["supplier_catalog"] is None or not c["variants"] for c in entries):
            continue
        endpoints = [tuple(c["variants"][endpoint]["record_id"] for c in entries) for endpoint in (0, -1)]
        for variant_ids in dict.fromkeys(endpoints):
            requests.append({"group_id": group["group_id"], "variant_ids": list(variant_ids),
                             "key_id": keys[position % len(keys)]["record_id"]})
    return requests


def run(expanded, output, *, max_variants=65536, max_motion_pairs=65536):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("trial_output_must_be_new_direct_workspace_child")
    settings = dict(max_variants=max_variants, max_motion_pairs=max_motion_pairs)
    for name, value in settings.items():
        _limit(value, name)
    from . import factor_indexed_hypotheses as indexed
    data = load_inputs(expanded)
    inputs = {**data["hashes"], **data["prerequisites"]["hashes"], **data["prerequisites"]["family"]["hashes"]}
    code = {str(p.resolve()): parent.file_digest(p) for p in parent._code_paths()}
    plan = {"version": VERSION, "expanded": str(data["directory"]),
        "parent_report_sha256": parent.file_digest(data["directory"] / "report.json"),
        "inputs": deepcopy(inputs), "code": code, "settings": settings,
        **{k: deepcopy(data["plan"][k]) for k in ("declared_contexts", "declared_units", "selected_contexts", "selection")},
        "sampling": "first_last_tuple_per_nonempty_group_one_key_cyclic_storage_order_not_music_rank",
        "cohort_complete": False, "old_selector_or_analysis_reexecuted": False,
        "all_logical_paths_evaluated": False, "source_labels_used_for_inference": False,
        "old_paths_or_bundles_extended": False, "production_modified": False}
    output.mkdir()
    artifacts, indices, failures, totals = {}, [], [], Counter()
    storage._save(output, "run-plan.json", plan, artifacts)
    for row in data["rows"]:
        started_case = perf_counter()
        entry = {"context_key": deepcopy(row["context_key"]), "old_row_sha256": digest(row),
            "old_groups": deepcopy(row["old_groups"]), "old_lane_refs": deepcopy(row["old_lane_refs"]),
            "old_hypothesis_counts": deepcopy(row["hypothesis_counts"]),
            "old_assessment_counts": deepcopy(row["assessment_counts"]),
            "expanded_scope": deepcopy(row["expanded_scope"]), "hypotheses": deepcopy(row["hypotheses"]),
            "indexed_universe": None, "query_samples": None, "status": "not_calculated", "error": None}
        print(f"[{len(indices)+1}/{len(data['rows'])}] index {row['context_key'][0]}", flush=True)
        owned_parents = None
        before = None
        try:
            packet, ir, extension, scope, h, assessment = load_case(data, row)
            owned_parents = [packet, ir, extension, scope, h, assessment]
            before = digest(owned_parents)
            index = indexed.build_index(ir, scope, h, max_variants=max_variants)
            path = storage._save(output, "indices/" + index["record_id"] + ".json.gz", index, artifacts, compressed=True)
            entry["indexed_universe"] = {"artifact": str(path), "sha256": artifacts[str(path)],
                "record_ref": frozen._ref(index), "status": index["status"]}
            entry["index_counts"] = deepcopy(index["summary"])
            # Known universe denominators survive a later query failure.
            totals["indexed_groups"] += len(index["path_groups"])
            totals["ready_factorized_groups"] += sum(g["status"] == "ready_factorized_group" for g in index["path_groups"])
            totals["logical_paths"] += sum(g["logical_path_count"] for g in index["path_groups"] if g["logical_path_count"] is not None)
            totals["logical_path_key_tuples"] += sum(g["logical_tuple_count"] for g in index["path_groups"] if g["logical_tuple_count"] is not None)
            totals["logical_function_rows"] += sum(g["logical_function_count"] for g in index["path_groups"] if g["logical_function_count"] is not None)
            totals["unknown_logical_groups"] += sum(g["logical_path_count"] is None for g in index["path_groups"])
            totals["origin_variants"] += len(index["variant_inventory"])
            totals["shared_profile_descriptors"] += len(index["profile_inventory"])
            requests = sample_requests(h, index)
            session = indexed.prepare_index(ir, scope, h, index) if requests else None
            queries = []
            # One request is fully calculated or explicitly held; never a partial
            # critical-edge Cartesian prefix. The request list is not a winner set.
            for request in requests:
                queries.append(indexed.query_prepared(session, **request, max_motion_pairs=max_motion_pairs))
            # Compare every declared technical control under ONE actual bundle,
            # not a separately favorable voice completion per competitor.
            control = (next(bundle for bundle in queries[0]["bundle_inventory"]
                            if bundle["all_no_link_control"]) if queries else None)
            comparisons = [indexed.assess_prepared(session, control, **request,
                            max_motion_pairs=max_motion_pairs) for request in requests]
            samples = {"version": VERSION, "context_key": deepcopy(row["context_key"]),
                "index_ref": frozen._ref(index), "sampling": plan["sampling"],
                "requests": requests, "queries": queries,
                "shared_control_bundle_ref": None if control is None else frozen._ref(control),
                "same_bundle_comparisons": comparisons, "all_logical_paths_evaluated": False,
                "selected": None, "musical_accuracy_measured": False}
            path = storage._save(output, "queries/" + index["record_id"] + ".json.gz", samples, artifacts, compressed=True)
            entry["query_samples"] = {"artifact": str(path), "sha256": artifacts[str(path)], "queries": len(queries)}
            entry["status"] = "index_and_technical_queries_saved_not_selected"
            totals["queried_path_key_tuples"] += len(queries)
            totals["queried_function_rows"] += sum(len(query.get("functions", [])) for query in queries)
            totals["same_bundle_technical_comparisons"] += sum(value["computed_counts"]["compatibility_tuples"]
                                                               for value in comparisons)
            if digest(owned_parents) != before:
                raise ValueError("indexed_trial_parent_or_IR_mutated")
        except Exception as exc:
            entry["status"] = "calculation_failure"
            entry["error"] = f"{type(exc).__name__}:{exc}"
            failures.append({"context_key": deepcopy(row["context_key"]), "error": entry["error"]})
        if owned_parents is not None and digest(owned_parents) != before:
            entry["status"] = "calculation_failure"
            entry["error"] = "ValueError:indexed_trial_parent_or_IR_mutated"
            if not any(f["context_key"] == entry["context_key"] and f["error"] == entry["error"] for f in failures):
                failures.append({"context_key": deepcopy(row["context_key"]), "error": entry["error"]})
        totals.update(contexts=1, old_raw_lanes=len(row["old_lane_refs"]), old_groups=len(row["old_groups"]))
        entry["elapsed_seconds"] = perf_counter() - started_case
        indices.append(entry)
        print(f"[{len(indices)}/{len(data['rows'])}] {entry['status']} {entry['elapsed_seconds']:.3f}s", flush=True)
    storage._save(output, "context-index.json", indices, artifacts)
    changed = [p for p, sha in {**inputs, **code}.items() if not Path(p).is_file() or parent.file_digest(p) != sha]
    if {str(p.resolve()) for p in parent._code_paths()} != set(code):
        changed.append("current_code_inventory_changed")
    for name, source in (("expanded", data), ("prerequisite", data["prerequisites"]),
                         ("family", data["prerequisites"]["family"])):
        if {str(p.resolve()) for p in source["directory"].rglob("*") if p.is_file()} != source["inventory"]:
            changed.append(name + "_parent_inventory_changed")
    changed_artifacts = [p for p, sha in artifacts.items() if not Path(p).is_file() or parent.file_digest(p) != sha]
    if {str(p.resolve()) for p in output.rglob("*") if p.is_file()} != set(artifacts):
        changed_artifacts.append("generated_artifact_inventory_changed")
    denominator = ([r["context_key"] for r in indices] == plan["selected_contexts"]
        and totals["old_raw_lanes"] == data["report"]["summary"]["old_raw_lanes"]
        and totals["old_groups"] == data["report"]["summary"]["old_groups"])
    integrity = not changed and not changed_artifacts and not failures
    report = {"version": VERSION, "scope_calculation_complete": bool(integrity and denominator),
        "computation_integrity_passed": bool(integrity), "selected_denominators_complete": bool(denominator),
        "inputs_and_code_unchanged": not changed, "artifacts_unchanged": not changed_artifacts,
        "changed_inputs_or_code": changed, "changed_artifacts": changed_artifacts, "failures": failures,
        "artifact_hashes": deepcopy(artifacts), "summary": {**dict(totals),
            "old_planned_paths": data["report"]["summary"]["planned_paths"],
            "old_unknown_path_group_counts": data["report"]["summary"]["unknown_path_group_counts"],
            "declared_contexts": len(plan["declared_contexts"]), "declared_original_raw_lanes": len(plan["declared_units"]),
            "unexecuted_original_contexts": len(plan["declared_contexts"]) - totals["contexts"],
            "unexecuted_original_raw_lanes": len(plan["declared_units"]) - totals["old_raw_lanes"],
            "context_status_counts": dict(Counter(r["status"] for r in indices))},
        "cohort_complete": False, "all_logical_paths_evaluated": False, "selected": None,
        **{k: False for k in POLICY_FALSE}, "elapsed_seconds": perf_counter() - started,
        "limits": ["Every supplied Cartesian tuple is represented; only declared technical queries are evaluated.",
            "First/last storage-order tuples are controls, not preferred musical hypotheses.",
            "Historical budget holds and the full unexecuted cohort remain unchanged.",
            "Intrinsic frozen catalog validation is not full fresh supplier/evaluator replay.",
            "No confidence, cadence, NCT, confirmed harmony, training, generation or production promotion."]}
    parent.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("expanded", "output"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--max-variants", type=int, default=65536)
    parser.add_argument("--max-motion-pairs", type=int, default=65536)
    report = run(**vars(parser.parse_args()))
    print(report["summary"], flush=True)
    return 0 if report["scope_calculation_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
