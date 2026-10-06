"""Append-only context and cadence prerequisites over a completed family batch.

The full declared cohort and every old group/lane/status remain visible. This
does not rerun the old selector/comparison, extend its harmony paths, or select
a key, role, cadence or training example. Registered parent checksums are the
storage trust boundary; new evidence separately replays literal score inputs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from . import factor_functional_batch as batch
from . import factor_musical_view as common
from . import factor_musical_trial as storage
from . import harmony_frozen_context_lineage_trial as parent
from .musical_pattern_observation import digest

ROOT = parent.ROOT
VERSION = "factor-context-prerequisite-trial-0.1.0"


def _limit(value, name, *, zero=False):
    if type(value) is not int or value < (0 if zero else 1):
        raise ValueError("explicit_integer_trial_limit_required:" + name)


def load_batch(directory):
    """Admit a completed saved batch, not an independent musical gold corpus."""
    directory = Path(directory).resolve(strict=True)
    report_path = directory / "batch-report.json"
    report = parent.read(report_path)
    required = ("batch_complete", "inputs_and_code_unchanged", "artifacts_unchanged",
                "computation_integrity_passed", "declared_denominators_complete",
                "selected_denominators_complete")
    if (report.get("version") != batch.VERSION or any(report.get(k) is not True for k in required)
            or report.get("cohort_complete") is not False or report.get("selected") is not None
            or report.get("changed_inputs_or_code") != [] or report.get("changed_artifacts") != []
            or report.get("failures") != []
            or any(report.get(k) is not False for k in ("musical_accuracy_measured", "production_modified",
                "source_labels_used_for_inference", "core_modified", "external_transmission"))):
        raise ValueError("completed_unselected_research_family_batch_required")
    hashes = {}
    parent._guard({str(report_path): parent.file_digest(report_path)}, hashes)
    artifacts = report["artifact_hashes"]
    if any(not Path(p).is_relative_to(directory) for p in artifacts):
        raise ValueError("batch_artifact_outside_parent_directory")
    parent._guard(artifacts, hashes)
    inventory = parent._inventory(directory, hashes)
    plan = parent._load(directory / "batch-plan.json", hashes)
    if (plan.get("version") != batch.VERSION or plan.get("cohort_complete") is not False
            or any(plan.get(k) is not False for k in ("source_labels_used_for_inference", "geometry_recomputed",
                "old_selectors_engines_reexecuted", "production_modified"))):
        raise ValueError("batch_plan_policy_mismatch")
    parent._guard(plan["inputs"], hashes)
    parent._guard(plan["code"], hashes)
    indices = parent._load(directory / "context-index.json", hashes)
    units = parent._load(directory / "unit-index.json", hashes)
    selected = plan["selection"]["selected_contexts"]
    if ([r["context_key"] for r in indices] != selected
            or len({tuple(k) for k in selected}) != len(selected)
            or [r["context_key"] for r in plan["catalog"]] != plan["declared_contexts"]
            or any(tuple(k) not in {tuple(x) for x in plan["declared_contexts"]} for k in selected)
            or report["summary"]["attempted_contexts"] != len(indices)
            or report["summary"]["attempted_raw_lanes"] != len(units)
            or report["summary"]["declared_contexts"] != len(plan["declared_contexts"])
            or report["summary"]["declared_raw_lanes"] != len(plan["declared_units"])):
        raise ValueError("batch_context_denominator_or_order_mismatch")
    expected = {(tuple(r["context_key"]), tuple(r["lane"])) for r in plan["declared_units"]
                if r["context_key"] in selected}
    actual = {(tuple(r["context_key"]), tuple(r["lane"])) for r in units}
    if actual != expected or len(actual) != len(units):
        raise ValueError("batch_selected_lane_denominator_mismatch")
    return {"directory": directory, "report": report, "plan": plan, "indices": indices,
            "units": units, "hashes": hashes, "inventory": inventory}


def _case(data, row):
    key = tuple(row["context_key"])
    path = Path(row["artifact"]).resolve(strict=True)
    if (path.parent != data["directory"] / "contexts"
            or data["hashes"].get(str(path)) != row["sha256"]
            or row["status"] != "scope_calculation_complete_not_selected" or row["errors"] != []):
        raise ValueError("registered_completed_parent_context_required")
    packet = parent._load(path, data["hashes"], compressed=True)
    if (packet["version"] != batch.VERSION or tuple(packet["context_key"]) != key
            or packet["errors"] != [] or packet["selected"] is not None
            or any(packet[k] is not False for k in ("training_eligible", "gold_eligible", "generation_ready"))
            or path.name != packet["observation"]["record_id"] + ".json.gz"):
        raise ValueError("parent_packet_identity_or_policy_mismatch")
    ir_ref = packet["score_snapshots"]["working-ir"]
    ir_path = Path(ir_ref["artifact"]).resolve(strict=True)
    if (not ir_path.is_relative_to(data["directory"] / "scores")
            or data["hashes"].get(str(ir_path)) != ir_ref["sha256"]):
        raise ValueError("registered_full_working_IR_required")
    ir = parent._load(ir_path, data["hashes"], compressed=True)
    view, observation = packet["context"]["view"], packet["observation"]
    audit = packet["audit_packet"]["audit"]
    common.validate_view(view, ir=ir, observation=observation, audit=audit)
    catalog = next(r for r in data["plan"]["catalog"] if tuple(r["context_key"]) == key)
    old_groups, results = packet["context"]["groups"], packet["groups"]
    if (catalog["view_ref"] != common.ref(view) or catalog["context_span"] != view["context_span"]
            or len(results) != len(old_groups) or len(results) != len(catalog["groups"])):
        raise ValueError("parent_context_or_group_denominator_mismatch")
    for old, result, declared in zip(old_groups, results, catalog["groups"]):
        if (old["group_id"] != result["group_id"] or old["status"] != result["original_status"]
                or old["planned_paths"] != result["planned_paths"]
                or {k: old[k] for k in ("group_id", "status", "planned_paths")} !=
                   {k: declared[k] for k in ("group_id", "status", "planned_paths")}
                or len(old["paths"]) != declared["stored_path_count"]
                or len(old["controls"]) != declared["stored_control_count"]):
            raise ValueError("parent_group_identity_or_count_mismatch")
        if ((result["status"] == "conditional_functional_comparison_complete") != bool(result["comparisons"])):
            raise ValueError("parent_comparison_status_or_denominator_mismatch")
        for compared in result["comparisons"]:
            # Actual canonical content, not a caller's retained claimed seal.
            # This is intrinsic integrity only, not old calculation replay.
            from .factor_functional_comparison import PREFIX, FLAGS
            common.check(compared, PREFIX)
            if compared["flags"] != FLAGS:
                raise ValueError("parent_comparison_promoted_policy")
    lanes = packet["lane_inventory"]
    expected = [r for r in data["units"] if tuple(r["context_key"]) == key]
    thin = [{k: v for k, v in lane.items() if k != "graph_snapshot"} for lane in lanes]
    if (thin != expected or [(r["part_id"], r["voice_id"]) for r in observation["raw_lanes"]]
            != [tuple(r["lane"]) for r in lanes]):
        raise ValueError("parent_lane_inventory_or_gate_mismatch")
    expected_graphs = [r["graph_snapshot"] for r in lanes
                       if r["graph_snapshot"] is not None and r["graph_snapshot"]["status"] == "ready"]
    if packet["ready_graphs"] != expected_graphs:
        raise ValueError("parent_ready_graph_inventory_mismatch")
    return packet, ir


def _cadence(packet, group):
    # Imported lazily so manifest/output guards can run before new producers.
    from . import factor_cadence_prerequisites as cadence
    from .factor_functional_trial import _paths
    by_bundle = {r["record_id"]: r for r in packet["completion_bundles"]}
    paths = _paths(group) if group["paths"] or group["controls"] else []
    return cadence, paths, by_bundle


def run(family_batch, output, *, pre_measures=1, post_measures=1,
        max_events=4096, max_relations=65536, max_records=4096, max_pairs=65536):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("trial_output_must_be_new_direct_workspace_child")
    for name, value in (("pre_measures", pre_measures), ("post_measures", post_measures),
                        ("max_events", max_events), ("max_relations", max_relations),
                        ("max_records", max_records), ("max_pairs", max_pairs)):
        _limit(value, name, zero=True)
    from . import factor_context_observation as context
    data = load_batch(family_batch)
    inputs = deepcopy(data["hashes"])
    code = {str(p.resolve()): parent.file_digest(p) for p in parent._code_paths()}
    settings = dict(pre_measures=pre_measures, post_measures=post_measures, max_events=max_events,
                    max_relations=max_relations, max_records=max_records, max_pairs=max_pairs)
    plan = {"version": VERSION, "parent_directory": str(data["directory"]),
            "parent_report_sha256": parent.file_digest(data["directory"] / "batch-report.json"),
            "inputs": inputs, "code": code, "settings": settings,
            "declared_contexts": deepcopy(data["plan"]["declared_contexts"]),
            "declared_units": deepcopy(data["plan"]["declared_units"]),
            "selected_contexts": deepcopy(data["plan"]["selection"]["selected_contexts"]),
            "selection": deepcopy(data["plan"]["selection"]), "cohort_complete": False,
            "scope": "all_previously_selected_contexts_and_every_saved_overlay_under_every_saved_comparison_bundle",
            "old_selector_or_comparison_reexecuted": False, "old_paths_or_bundles_extended": False,
            "source_labels_used_for_inference": False, "production_modified": False}
    output.mkdir()
    artifacts, indices, failures, totals, old_counts = {}, [], [], Counter(), Counter()
    storage._save(output, "run-plan.json", plan, artifacts)
    for row in data["indices"]:
        case_started = perf_counter()
        packet, ir = _case(data, row)
        view, observation, audit = packet["context"]["view"], packet["observation"], packet["audit_packet"]["audit"]
        before = digest([packet, ir])
        for group in packet["groups"]:
            old_counts["groups"] += 1
            old_counts["function_rows"] += sum(len(o["functions"]["rows"]) for o in group["overlays"])
            old_counts["resolution_rows"] += sum(len(r["rules"]) for r in group["resolutions"])
            old_counts["comparisons"] += len(group["comparisons"])
            old_counts["vectors"] += sum(len(c["evidence_vectors"]) for c in group["comparisons"])
            old_counts["pairwise_differences"] += sum(len(c["pairwise_differences"]) for c in group["comparisons"])
            if group["request_inventory"] is not None:
                old_counts["planned_joint_requests"] += group["request_inventory"]["planned_requests"]
            old_counts["joint_solutions"] += len(group["solutions"])
            old_counts["joint_branches"] += sum(len(s["solution"]["branches"]) for s in group["solutions"])
        print(f"[{len(indices)+1}/{len(data['indices'])}] context {row['context_key'][0]}", flush=True)
        context_result = {"artifact": None, "sha256": None, "record_ref": None,
                          "status": "calculation_failure", "error": None}
        try:
            extension = context.observe_context(ir, view, observation, audit,
                pre_measures=pre_measures, post_measures=post_measures,
                max_events=max_events, max_relations=max_relations)
            context_path = storage._save(output, "contexts/" + extension["record_id"] + ".json.gz",
                                         extension, artifacts, compressed=True)
            context_result.update(artifact=str(context_path), sha256=artifacts[str(context_path)],
                                  record_ref=common.ref(extension), status=extension["status"])
        except Exception as exc:
            context_result["error"] = f"{type(exc).__name__}:{exc}"
            failures.append({"context_key": row["context_key"], "stage": "context_observation",
                             "error": context_result["error"]})
        groups = []
        for old, result in zip(packet["context"]["groups"], packet["groups"]):
            g = {"group_id": old["group_id"], "old_status": result["status"],
                 "original_status": result["original_status"], "planned_paths": result["planned_paths"],
                 "old_overlay_count": len(result["overlays"]), "old_comparison_count": len(result["comparisons"]),
                 "records": [], "errors": []}
            if result["comparisons"] and context_result["error"] is not None:
                g["errors"].append({"error": "new_context_calculation_failed_not_inferred_as_music"})
            elif result["comparisons"]:
                cadence, paths, bundles = _cadence(packet, old)
                for compared in result["comparisons"]:
                    ref = compared["completion_bundle_ref"]
                    bundle = bundles[ref["record_id"]]
                    if (common.ref(bundle) != ref or compared["path_refs"] != bundle["path_refs"]
                            or compared["view_ref"] != common.ref(view)
                            or compared["overlay_refs"] != sorted(
                                [common.ref(r["functions"]) for r in result["overlays"]],
                                key=lambda r: r["record_id"])):
                        raise ValueError("saved_comparison_path_overlay_or_bundle_not_closed")
                    try:
                        record = cadence.observe_all_prerequisites(view, paths, result["overlays"], bundle,
                            packet["ready_graphs"], max_records=max_records, max_pairs=max_pairs)
                        path = storage._save(output, "cadence/" + record["record_id"] + ".json.gz",
                                             record, artifacts, compressed=True)
                        g["records"].append({"artifact": str(path), "sha256": artifacts[str(path)],
                            "record_ref": common.ref(record), "comparison_ref": common.ref(compared),
                            "completion_bundle_ref": ref, "planned_records": record["planned_records"],
                            "saved_records": len(record["records"]), "status": record["status"]})
                        totals["planned_prerequisite_records"] += record["planned_records"]
                        totals["saved_prerequisite_records"] += len(record["records"])
                        totals["prerequisite_batches"] += 1
                        totals["boundaries"] += sum(len(r["boundaries"]) for r in record["records"])
                    except Exception as exc:
                        error = f"{type(exc).__name__}:{exc}"
                        g["errors"].append({"comparison_ref": common.ref(compared), "error": error})
                        failures.append({"context_key": row["context_key"], "group_id": old["group_id"], "error": error})
            groups.append(g)
        if digest([packet, ir]) != before:
            raise ValueError("trial_parent_packet_or_IR_mutated")
        totals["contexts"] += 1
        totals["raw_lanes"] += len(packet["lane_inventory"])
        totals["groups"] += len(groups)
        indices.append({"context_key": row["context_key"], "parent_artifact": row["artifact"],
            "parent_artifact_sha256": row["sha256"], "working_ir": packet["score_snapshots"]["working-ir"],
            "view_ref": common.ref(view), "context_observation": context_result, "groups": groups,
            "lane_inventory": deepcopy(packet["lane_inventory"]),
            "elapsed_seconds": perf_counter() - case_started})
        print(f"[{len(indices)}/{len(data['indices'])}] saved, {indices[-1]['elapsed_seconds']:.3f}s", flush=True)
    storage._save(output, "context-index.json", indices, artifacts)
    changed = [p for p, sha in {**inputs, **code}.items()
               if not Path(p).is_file() or parent.file_digest(p) != sha]
    if {str(p.resolve()) for p in parent._code_paths()} != set(code):
        changed.append("current_code_inventory_changed")
    if {str(p.resolve()) for p in data["directory"].rglob("*") if p.is_file()} != data["inventory"]:
        changed.append("parent_batch_inventory_changed")
    changed_artifacts = [p for p, sha in artifacts.items()
                         if not Path(p).is_file() or parent.file_digest(p) != sha]
    if {str(p.resolve()) for p in output.rglob("*") if p.is_file()} != set(artifacts):
        changed_artifacts.append("generated_artifact_inventory_changed")
    # Older completed batches omit Counter keys whose value stayed zero.
    # Absence is normalized only for these arithmetic counts, never statuses,
    # candidate references, evidence or a positive inventory.
    if old_counts != Counter(data["report"]["summary"]["counts"]):
        failures.append({"error": "parent_saved_calculation_denominator_mismatch",
                         "actual": dict(old_counts), "expected": data["report"]["summary"]["counts"]})
    integrity = (not changed and not changed_artifacts and not failures)
    denominator = ([r["context_key"] for r in indices] == plan["selected_contexts"]
                   and totals["raw_lanes"] == len(data["units"]))
    report = {"version": VERSION, "scope_calculation_complete": bool(integrity and denominator),
        "cohort_complete": False, "computation_integrity_passed": integrity,
        "selected_denominators_complete": denominator, "inputs_and_code_unchanged": not changed,
        "artifacts_unchanged": not changed_artifacts, "changed_inputs_or_code": changed,
        "changed_artifacts": changed_artifacts, "failures": failures, "artifact_hashes": deepcopy(artifacts),
        "summary": {**dict(totals), "old_calculation_counts": dict(old_counts),
            "declared_contexts": len(plan["declared_contexts"]),
            "declared_raw_lanes": len(plan["declared_units"]),
            "unexecuted_contexts": len(plan["declared_contexts"]) - totals["contexts"],
            "unexecuted_raw_lanes": len(plan["declared_units"]) - totals["raw_lanes"],
            "old_group_status_counts": dict(Counter(g["old_status"] for r in indices for g in r["groups"])),
            "context_status_counts": dict(Counter(r["context_observation"]["status"] for r in indices)),
            "cadence_batch_status_counts": dict(Counter(a["status"] for r in indices for g in r["groups"] for a in g["records"]))},
        "elapsed_seconds": perf_counter() - started, "selected": None,
        "harmony_confirmed": False, "cadence_confirmed": False, "musical_accuracy_measured": False,
        "training_eligible": False, "gold_eligible": False, "generation_ready": False,
        "source_labels_used_for_inference": False, "core_or_production_modified": False,
        "old_paths_or_bundles_extended": False,
        "limits": ["Parent checksums establish storage integrity, not musicological truth.",
                   "New literal neighbors do not join an old voice completion or harmony hypothesis.",
                   "Same-lane temporal neighbors are not inferred logical voices.",
                   "Conditional extreme chord factors and terminal observations do not certify a cadence.",
                   "Completion covers only the declared executed family-limited scope."]}
    parent.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("family-batch", "output"):
        parser.add_argument("--" + name, required=True)
    for name, default in (("pre-measures", 1), ("post-measures", 1), ("max-events", 4096),
                          ("max-relations", 65536), ("max-records", 4096), ("max-pairs", 65536)):
        parser.add_argument("--" + name, type=int, default=default)
    report = run(**vars(parser.parse_args()))
    print(report["summary"])
    return 0 if report["scope_calculation_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
