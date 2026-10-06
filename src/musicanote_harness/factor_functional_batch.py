"""Bounded, family/collection-diverse functional research on frozen inputs.

The complete cohort is declared, not claimed executed. Selection reads only
protected family/collection identities and freshly reconstructed path-group
availability. Neither annotation labels nor favourable musical outcomes pick
cases. All groups and raw lanes survive each selected context calculation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from . import factor_functional_trial as functional
from . import factor_functional_resolution as resolution
from . import factor_musical_trial as meaning
from . import factor_musical_view as common
from . import harmony_frozen_context_lineage_trial as parent
from .musical_pattern_observation import digest

ROOT = parent.ROOT
VERSION = "factor-functional-family-batch-0.1.0"
CATALOG_KEYS = {"view", "groups", "old_stage_statuses", "original_final_status", "pitch_policy",
                "stored_lattice_artifact", "stored_lattice_content_sha256", "unspelled_candidates", "lattice_status"}


def _identity(data, pair):
    entry = data["packages"][pair]["source"]["manifest_entry"]
    fields = ("work_family_id", "corpus_id", "collection_id")
    if any(not isinstance(entry.get(k), str) or not entry[k] for k in fields):
        raise ValueError("explicit_frozen_family_and_collection_identity_required")
    return entry["work_family_id"], (entry["corpus_id"], entry["collection_id"])


def catalog(data):
    """Reconstruct all protected group inventories; literal IR replay is later.

    This is a registered-parent availability catalog, NOT original-score or
    musical validation of unexecuted contexts. Selected cases additionally
    use the full IR/observation/audit replay in functional._context.
    """
    rows = []
    for key, index in data["meaning_contexts"].items():
        path = Path(index["artifact"]).resolve(strict=True)
        expected_observation_ref = {k: data["contexts"][key][k] for k in ("record_id", "record_sha256")}
        if (set(index) != {"context_key", "artifact", "sha256", "view_ref", "planned_groups"}
                or path != data["meaning"] / "contexts" / (expected_observation_ref["record_id"] + ".json.gz")):
            raise ValueError("foreign_batch_context_artifact")
        saved = parent._load(path, data["hashes"], compressed=True)
        if set(saved) != CATALOG_KEYS:
            raise ValueError("closed_batch_parent_context_required")
        view = saved["view"]
        common.validate_view(view)
        old = data["contexts"][key]
        current = data["current"][key]
        stored = parent._load(current["artifact"], data["hashes"], compressed=True)["bundle"]
        policy = deepcopy(data["packages"][key[0]]["source"]["pitch_policy"])
        groups = meaning.path_groups(view, stored["stages"]["lattice"],
                                     path_budget=data["meaning_plan"]["path_budget"])
        if policy.get("harmonic_replay_allowed") is not True:
            for group in groups:
                group["status"] = "withheld_pitch_policy"
        if (index["context_key"] != list(key) or index["sha256"] != data["hashes"][str(path)]
                or index["view_ref"] != common.ref(view) or index["planned_groups"] != len(groups)
                or view["observation_ref"] != expected_observation_ref
                or view["audit_ref"] != data["audits"][key]["audit_ref"]
                or saved["groups"] != groups or saved["old_stage_statuses"] != old["original_stage_statuses"]
                or saved["original_final_status"] != old["original_final_status"]
                or current["previous_status"] != old["original_final_status"]
                or saved["pitch_policy"] != policy
                or saved["stored_lattice_artifact"] != current["artifact"]
                or saved["stored_lattice_content_sha256"] != digest(stored["stages"]["lattice"])
                or saved["unspelled_candidates"] != stored["unspelled_candidates"]
                or saved["lattice_status"] != stored["stages"]["lattice"]["status"]
                or stored["input_ir_content_sha256"] != view["binding"]["ir_content_sha256"]
                or stored["sample"]["span"] != view["context_span"]
                or view["target_span"] != stored["sample"]["span"]
                or stored["stage_statuses"] != old["original_stage_statuses"]):
            raise ValueError("batch_catalog_fresh_group_or_parent_binding_mismatch")
        family, collection = _identity(data, key[0])
        group_rows = [{"group_id": g["group_id"], "status": g["status"],
                       "planned_paths": g["planned_paths"],
                       "stored_path_count": len(g["paths"]), "stored_control_count": len(g["controls"])}
                      for g in groups]
        rows.append({"context_key": list(key), "work_family_id": family, "collection": list(collection),
                     "view_ref": common.ref(view), "context_span": deepcopy(view["context_span"]),
                     "artifact": str(path), "artifact_sha256": data["hashes"][str(path)],
                     "groups": group_rows,
                     "eligible_change_group_ids": [g["group_id"] for g in groups
                         if g["group_id"].startswith("change:") and g["status"] == "paths_prepared"],
                     "literal_source_replay_performed_in_catalog": False})
    if [tuple(r["context_key"]) for r in rows] != list(data["contexts"]):
        raise ValueError("batch_catalog_frozen_order_or_denominator_mismatch")
    return rows


def select_families(data, rows, family_limit=5):
    """First change-ready context per family; round-robin frozen collections."""
    if type(family_limit) is not int or family_limit < 1:
        raise ValueError("positive_integer_family_limit_required")
    if [tuple(r["context_key"]) for r in rows] != list(data["contexts"]):
        raise ValueError("selection_requires_full_frozen_context_order")
    family_collections, family_pairs = {}, defaultdict(list)
    for pair in data["packages"]:
        family, collection = _identity(data, pair)
        if family in family_collections and family_collections[family] != collection:
            raise ValueError("frozen_family_cross_collection_ambiguity")
        family_collections[family] = collection
        family_pairs[family].append(pair)
    candidates, prior = {}, defaultdict(list)
    for row in rows:
        key = tuple(row["context_key"])
        family, collection = _identity(data, key[0])
        if row["work_family_id"] != family or tuple(row["collection"]) != collection:
            raise ValueError("selection_family_identity_mismatch")
        expected_change = [g["group_id"] for g in row["groups"]
                           if g["group_id"].startswith("change:") and g["status"] == "paths_prepared"]
        if row["eligible_change_group_ids"] != expected_change:
            raise ValueError("selection_change_availability_mismatch")
        if family in candidates:
            continue
        if row["eligible_change_group_ids"]:
            candidates[family] = deepcopy(row)
        else:
            prior[family].append({"context_key": deepcopy(row["context_key"]),
                                  "groups": deepcopy(row["groups"]),
                                  "reason": "no_paths_prepared_change_group"})
    collections = {}
    for family in family_collections:
        if family in candidates:
            collections.setdefault(family_collections[family], deque()).append(family)
    order = []
    while any(collections.values()):
        for queue in collections.values():
            if queue:
                order.append(queue.popleft())
    chosen = order[:family_limit]
    decisions = []
    for family, collection in family_collections.items():
        status = ("scheduled" if family in chosen else "deferred_family_limit" if family in candidates
                  else "no_paths_prepared_change_context")
        decisions.append({"work_family_id": family, "collection": list(collection),
                          "package_ids": family_pairs[family], "status": status,
                          "first_eligible_context": candidates.get(family),
                          "preceding_noneligible_contexts": prior[family]})
    return {"family_limit": family_limit, "family_decisions": decisions,
            "eligible_family_order": order, "selected_family_order": chosen,
            "selected_contexts": [candidates[f]["context_key"] for f in chosen],
            "selection_policy": "first_frozen_change_ready_context_per_family_collection_round_robin",
            "source_annotation_labels_used": False, "outcomes_used_for_selection": False,
            "key_or_geometry_or_source_gate_used_for_selection": False,
            "unexecuted_catalog_is_literal_or_musical_validation": False}


def _bundles(view, original_groups, results, graphs):
    if len(original_groups) != len(results):
        raise ValueError("batch_group_result_denominator_loss")
    records = {}
    for original, result in zip(original_groups, results):
        if (result["group_id"] != original["group_id"]
                or result["original_status"] != original["status"]
                or result["planned_paths"] != original["planned_paths"]):
            raise ValueError("batch_group_identity_loss")
        if not result["comparisons"]:
            continue
        entries = []
        for graph in graphs:
            entry, answer = functional._entry(graph)
            if entry is None:
                raise ValueError("batch_baseline_bundle_unavailable:" + answer["status"])
            entries.append(entry)
        baseline = resolution.make_bundle(view, functional._paths(original), entries)
        records[baseline["record_id"]] = baseline
        for item in result["solutions"]:
            for bundle in functional._assessed_bundles(item["solution"]):
                records[bundle["record_id"]] = bundle
        for compared in result["comparisons"]:
            reference = compared["completion_bundle_ref"]
            if reference["record_id"] not in records or common.ref(records[reference["record_id"]]) != reference:
                raise ValueError("batch_comparison_bundle_reference_not_closed")
    return list(records.values())


def run(baseline, lineage, musical_meaning, output, *, family_limit=5,
        pair_budget=4096, overlay_pair_budget=65536, functional_budget=16384, request_budget=256):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("batch_output_must_be_new_direct_workspace_child")
    budgets = dict(pair_budget=pair_budget, overlay_pair_budget=overlay_pair_budget,
                   functional_budget=functional_budget, request_budget=request_budget)
    if any(type(v) is not int or v < 1 for v in [family_limit, *budgets.values()]):
        raise ValueError("positive_integer_batch_limits_required")
    data = functional.load_inputs(baseline, lineage, musical_meaning)
    inputs = deepcopy(data["hashes"])
    code = {str(p.resolve()): parent.file_digest(p) for p in parent._code_paths()}
    rows = catalog(data)
    selection = select_families(data, rows, family_limit)
    keys = [tuple(k) for k in selection["selected_contexts"]]
    plan = {"version": VERSION, "baseline": str(data["baseline"]), "lineage": str(data["lineage"]),
            "musical_meaning": str(data["meaning"]), "inputs": inputs, "code": code,
            "declared_contexts": [list(k) for k in data["contexts"]],
            "declared_units": [{"context_key": list(k), "lane": list(l)} for k, l in data["units"]],
            "catalog": rows, "selection": selection, "budgets": budgets,
            "cohort_complete": False, "source_labels_used_for_inference": False,
            "geometry_recomputed": False, "old_selectors_engines_reexecuted": False,
            "production_modified": False}
    output.mkdir()
    artifacts, indices, units, failures = {}, [], [], []
    meaning._save(output, "batch-plan.json", plan, artifacts)
    saved_scores, totals, statuses = {}, Counter(), defaultdict(Counter)
    for key in keys:
        case_started = perf_counter()
        pair = key[0]
        historical, ir, revision = parent._working_case(data, pair)
        ir_before = digest(ir)
        observation = parent._observation(data, key, historical, ir, revision, literal=False)
        audit = meaning._audit_packet(data, key, observation)
        context = functional._context(data, key, observation, ir, audit)
        expected_row = next(r for r in rows if tuple(r["context_key"]) == key)
        if common.ref(context["view"]) != expected_row["view_ref"]:
            raise ValueError("batch_selected_view_changed_from_catalog")
        scope = functional.key_candidates(context["view"])
        graphs, lane_inventory = [], []
        for lane in observation["raw_lanes"]:
            lane_key = (lane["part_id"], lane["voice_id"])
            unit = meaning._baseline_unit(data, key, observation, lane_key, audit)
            graph = unit["unit"]["graph"]
            if graph is not None and graph["status"] == "ready":
                graphs.append(graph)
            row = {"context_key": list(key), "lane": list(lane_key),
                   "old_geometry_status": unit["unit"]["status"],
                   "old_geometry_reasons": deepcopy(unit["unit"]["reasons"]),
                   "graph_snapshot": deepcopy(graph),
                   "parent_gate": deepcopy(data["gates"][(key, lane_key)])}
            lane_inventory.append(row)
            units.append({k: deepcopy(v) for k, v in row.items() if k != "graph_snapshot"})
        before = digest([context, scope, graphs, lane_inventory])
        print(f"[{len(indices) + 1}/{len(keys)}] starting {pair}; groups={len(context['groups'])}; lanes={len(lane_inventory)}", flush=True)
        results, errors = functional.evaluate_groups(context["view"], context["groups"], scope, graphs, **budgets)
        failures.extend({"context_key": list(key), "error": error} for error in errors)
        bundles = _bundles(context["view"], context["groups"], results, graphs)
        if digest([context, scope, graphs, lane_inventory]) != before or digest(ir) != ir_before:
            raise ValueError("batch_context_inputs_mutated")
        if pair not in saved_scores:
            token = digest(pair)[:16]
            saved_scores[pair] = {}
            for name, value in (("working-ir", ir), ("historical-ir", historical), ("revision", revision)):
                path = meaning._save(output, "scores/" + token + "/" + name + ".json.gz", value, artifacts, compressed=True)
                saved_scores[pair][name] = {"artifact": str(path), "sha256": artifacts[str(path)]}
        payload = {"version": VERSION, "context_key": list(key), "context": context,
                   "key_scope": scope, "observation": observation, "audit_packet": audit,
                   "score_snapshots": saved_scores[pair], "lane_inventory": lane_inventory,
                   "ready_graphs": graphs, "completion_bundles": bundles, "groups": results,
                   "errors": errors, "selected": None, "training_eligible": False,
                   "gold_eligible": False, "generation_ready": False,
                   "elapsed_seconds": perf_counter() - case_started}
        path = meaning._save(output, "contexts/" + observation["record_id"] + ".json.gz", payload, artifacts, compressed=True)
        indices.append({"context_key": list(key), "artifact": str(path), "sha256": artifacts[str(path)],
                        "status": "calculation_failure" if errors else "scope_calculation_complete_not_selected",
                        "errors": errors})
        totals["groups"] += len(results)
        for group in results:
            statuses["group"].update([group["status"]])
            for overlay in group["overlays"]:
                for row in overlay["functions"]["rows"]:
                    totals["function_rows"] += 1
                    statuses["function"].update([row["status"]])
            for compiled in group["resolutions"]:
                for row in compiled["rules"]:
                    totals["resolution_rows"] += 1
                    statuses["resolution"].update([row["status"]])
            inventory = group["request_inventory"]
            if inventory is not None:
                totals["planned_joint_requests"] += inventory["planned_requests"]
                statuses["request"].update([inventory["status"]])
            for solution in group["solutions"]:
                totals["joint_solutions"] += 1
                statuses["joint"].update([solution["solution"]["status"]])
                totals["joint_branches"] += len(solution["solution"]["branches"])
            for compared in group["comparisons"]:
                totals["comparisons"] += 1
                totals["vectors"] += len(compared["evidence_vectors"])
                totals["pairwise_differences"] += len(compared["pairwise_differences"])
                for evaluation in compared["resolution_evaluations"]:
                    statuses["bundle_resolution"].update(r["status"] for r in evaluation["assessments"])
        print(f"[{len(indices)}/{len(keys)}] saved; seconds={payload['elapsed_seconds']:.3f}; errors={len(errors)}", flush=True)
    attempted = {tuple(r["context_key"]) for r in indices}
    actual_units = {(tuple(r["context_key"]), tuple(r["lane"])) for r in units}
    expected_units = {u for u in data["units"] if u[0] in set(keys)}
    if attempted != set(keys) or actual_units != expected_units or len(units) != len(actual_units):
        raise ValueError("batch_selected_context_or_lane_denominator_loss")
    meaning._save(output, "context-index.json", indices, artifacts)
    meaning._save(output, "unit-index.json", units, artifacts)
    changed = [p for p, sha in {**inputs, **code}.items() if not Path(p).is_file() or parent.file_digest(p) != sha]
    if {str(p.resolve()) for p in parent._code_paths()} != set(code):
        changed.append("current_code_inventory_changed")
    for directory, inventory in data["inventories"].items():
        if {str(p.resolve()) for p in Path(directory).rglob("*") if p.is_file()} != inventory:
            changed.append("parent_inventory_changed:" + directory)
    changed_artifacts = [p for p, sha in artifacts.items() if not Path(p).is_file() or parent.file_digest(p) != sha]
    if {str(p.resolve()) for p in output.rglob("*") if p.is_file()} != set(artifacts):
        changed_artifacts.append("batch_artifact_inventory_changed")
    report = {"version": VERSION, "batch_complete": not failures and not changed and not changed_artifacts,
              "cohort_complete": False, "inputs_and_code_unchanged": not changed,
              "artifacts_unchanged": not changed_artifacts, "computation_integrity_passed": not failures,
              "declared_denominators_complete": True, "selected_denominators_complete": True,
              "artifact_hashes": artifacts, "changed_inputs_or_code": changed,
              "changed_artifacts": changed_artifacts, "failures": failures,
              "elapsed_seconds": perf_counter() - started,
              "summary": {"declared_work_families": len(selection["family_decisions"]),
                          "declared_packages": len(data["packages"]), "declared_contexts": len(data["contexts"]),
                          "declared_raw_lanes": len(data["units"]), "attempted_contexts": len(indices),
                          "error_contexts": sum(bool(r["errors"]) for r in indices),
                          "attempted_raw_lanes": len(units), "executed_families": len(keys),
                          "executed_packages": len(saved_scores),
                          "unexecuted_contexts": len(data["contexts"]) - len(indices),
                          "unexecuted_raw_lanes": len(data["units"]) - len(units),
                          "family_status_counts": dict(Counter(r["status"] for r in selection["family_decisions"])),
                          "counts": dict(totals), "status_counts": {k: dict(v) for k, v in statuses.items()},
                          "calculation_failures": len(failures), "human_validated": 0,
                          "training_eligible": 0, "gold_eligible": 0, "generation_ready": 0},
              "selected": None, "musical_accuracy_measured": False, "production_modified": False,
              "source_labels_used_for_inference": False, "core_modified": False,
              "external_transmission": False,
              "limits": ["Batch completion applies only to the predeclared family-limited scope, not the full cohort.",
                         "Prepared-change availability selection is not random or an independent accuracy holdout.",
                         "Catalog reconstruction is not literal IR/source validation of unexecuted contexts.",
                         "All original groups, candidates, raw lanes and blockers survive selected-case evaluation.",
                         "Conditional shapes and shared completions do not select key, harmony, NCT or cadence."]}
    parent.write_new(output / "batch-report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "lineage", "musical-meaning", "output"):
        parser.add_argument("--" + name, required=True)
    for name, default in (("family-limit", 5), ("pair-budget", 4096), ("overlay-pair-budget", 65536),
                          ("functional-budget", 16384), ("request-budget", 256)):
        parser.add_argument("--" + name, type=int, default=default)
    report = run(**vars(parser.parse_args()))
    print(report["summary"])
    return 0 if report["batch_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
