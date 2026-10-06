"""Append-only explicit-key/functional evidence on the protected cohort.

Not a key detector or harmonic selector.  The complete old denominator and
candidate groups survive all extra resource guards.  A single completion is
shared by every competing path and key overlay in each comparison.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from . import factor_musical_trial as meaning
from . import harmony_frozen_context_lineage_trial as parent
from . import factor_musical_view as common
from . import factor_musical_rules as nct
from . import factor_functional_overlay as functional
from . import factor_functional_resolution as resolution
from . import factor_functional_comparison as comparison
from .harmony_factorized_voice_paths import query, materialize_witness
from .musical_pattern_observation import digest

ROOT = parent.ROOT
VERSION = "factor-functional-trial-0.1.0"
MAJOR_TONICS = (("C", -1), ("G", -1), ("D", -1), ("A", -1), ("E", -1),
                ("B", -1), ("F", 0), ("C", 0), ("G", 0), ("D", 0),
                ("A", 0), ("E", 0), ("B", 0), ("F", 1), ("C", 1))
MINOR_TONICS = (("A", -1), ("E", -1), ("B", -1), ("F", 0), ("C", 0),
                ("G", 0), ("D", 0), ("A", 0), ("E", 0), ("B", 0),
                ("F", 1), ("C", 1), ("G", 1), ("D", 1), ("A", 1))


def _provenance():
    return {"kind": "caller_hypothesis", "engine_version": VERSION,
            "source_document_sha256": None, "source_path": None,
            "pitch_basis": "written_IR_not_concert_certified", "status": "hypothesis_not_gold"}


def key_candidates(view):
    """Signature-compatible hypotheses plus unknown, never an inferred key.

    Every measure intersecting the observed context matters; a changing,
    absent, nonstandard or contradictory declaration yields only unknown.
    An unknown track always retains signature-external/local-key alternatives.
    """
    common.validate_view(view)
    start, end = common.span_bounds(view["context_span"])
    declarations = []
    for measure in view["measure_snapshots"]:
        a = common.f(measure["global_start_quarter"])
        b = a + common.f(measure["actual_duration_quarter"])
        if max(start, a) < min(end, b):
            signature = measure["key_signature"]
            declarations.append({"measure_id": measure["measure_id"],
                "measure_span": {"start": common.q(a), "end": common.q(b)},
                "signature": deepcopy(signature)})
    values = [None if r["signature"] is None else r["signature"].get("fifths") for r in declarations]
    cursor, covered = start, True
    for row in sorted(declarations, key=lambda r: common.f(r["measure_span"]["start"])):
        a, b = common.span_bounds(row["measure_span"])
        if max(a, start) != cursor:
            covered = False
        cursor = min(b, end)
    covered &= cursor == end
    usable = (covered and bool(values) and all(type(v) is int and -7 <= v <= 7 for v in values)
              and len(set(values)) == 1)
    specs = []
    if usable:
        fifths = values[0]
        major, minor = MAJOR_TONICS[fifths + 7], MINOR_TONICS[fifths + 7]
        specs = [(major, "major", "major"), (minor, "minor", "natural_minor"),
                 (minor, "minor", "harmonic_minor"), (minor, "minor", "melodic_minor_ascending")]
    specs.append((None, "unknown", "unknown"))
    tracks = [functional.make_key_track(view, [{"segment_id": "key_context_" + str(i),
               "span": deepcopy(view["context_span"]),
               "tonic": None if tonic is None else {"step": tonic[0], "alter": common.q(tonic[1])},
               "mode": mode, "scale_form": form}], _provenance())
              for i, (tonic, mode, form) in enumerate(specs)]
    return {"version": VERSION, "declarations": declarations, "tracks": tracks,
            "status": "signature_compatible_hypotheses_and_unknown" if usable else "unknown_only",
            "key_inferred": False, "mode_hint_used_as_key": False, "source_labels_used": False,
            "unambiguous_measure_coverage": bool(covered),
            "scope": "full-context compatible major and three minor reference forms plus unknown",
            "exhaustive_local_key_universe": False, "unknown_covers_signature_external_alternatives": True}


def load_inputs(baseline, lineage, musical_meaning):
    data = meaning.load_inputs(baseline, lineage)
    prior_inputs = deepcopy(data["hashes"])
    directory = Path(musical_meaning).resolve(strict=True)
    report = meaning._completed(directory, meaning.VERSION, data["hashes"], data["inventories"])
    plan = parent._load(directory / "run-plan.json", data["hashes"])
    if (plan.get("version") != meaning.VERSION or plan.get("inputs") != prior_inputs
            or Path(plan["baseline"]).resolve() != data["baseline"]
            or Path(plan["lineage"]).resolve() != data["lineage"]
            or plan.get("expected_contexts") != [list(k) for k in data["contexts"]]
            or plan.get("expected_lanes") != len(data["units"])
            or plan.get("all_denominators_retained") is not True
            or any(plan.get(k) is not False for k in ("source_annotation_labels_used",
                "old_selectors_engines_reexecuted", "production_modified"))):
        raise ValueError("meaning_plan_input_binding_or_policy_mismatch")
    parent._guard(plan["inputs"], data["hashes"])
    parent._guard(plan["code"], data["hashes"])
    contexts = parent._unique(parent._load(directory / "context-index.json", data["hashes"]),
                              parent._key, "duplicate_meaning_context")
    units = parent._unique(parent._load(directory / "unit-index.json", data["hashes"]),
        lambda r: (parent._key(r), tuple(r["lane"])), "duplicate_meaning_lane")
    if set(contexts) != set(data["contexts"]) or set(units) != set(data["units"]):
        raise ValueError("meaning_denominator_mismatch")
    summary = report["summary"]
    if (summary["contexts"] != len(contexts) or summary["raw_lanes"] != len(units)
            or summary["calculation_failures"] != 0
            or summary["old_geometry_status_counts"] != data["report"]["summary"]["status_counts"]
            or summary["source_gate_counts"] != data["lineage_report"]["summary"]["gate_status_counts"]
            or summary["status_counts"] != dict(Counter(r["status"] for r in units.values()))
            or any(summary.get(k) != 0 for k in ("human_validated", "training_eligible", "gold_eligible", "generation_ready"))
            or report.get("selected") is not None
            or any(report.get(k) is not False for k in ("musical_accuracy_measured", "production_modified",
                         "source_labels_used_for_inference", "core_modified", "external_transmission"))):
        raise ValueError("meaning_report_status_or_policy_mismatch")
    data.update(meaning=directory, meaning_plan=plan, meaning_contexts=contexts, meaning_report=report)
    return data


def _context(data, key, observation, ir, audit_packet):
    view = common.prepare(ir, observation, audit_packet["audit"])
    index = data["meaning_contexts"][key]
    path = Path(index["artifact"]).resolve(strict=True)
    if path != data["meaning"] / "contexts" / (observation["record_id"] + ".json.gz"):
        raise ValueError("foreign_meaning_context_artifact")
    saved = parent._load(path, data["hashes"], compressed=True)
    stored = parent._load(data["current"][key]["artifact"], data["hashes"], compressed=True)["bundle"]
    previous = data["contexts"][key]
    if (stored["input_ir_content_sha256"] != view["binding"]["ir_content_sha256"]
            or stored["sample"]["span"] != view["context_span"]
            or stored["stage_statuses"] != previous["original_stage_statuses"]
            or data["current"][key]["previous_status"] != previous["original_final_status"]):
        raise ValueError("stored_candidate_context_status_or_binding_mismatch")
    groups = meaning.path_groups(view, stored["stages"]["lattice"], path_budget=data["meaning_plan"]["path_budget"])
    policy = deepcopy(data["packages"][key[0]]["source"]["pitch_policy"])
    if policy.get("harmonic_replay_allowed") is not True:
        for group in groups:
            group["status"] = "withheld_pitch_policy"
    expected = {"view": view, "groups": groups, "old_stage_statuses": previous["original_stage_statuses"],
                "original_final_status": previous["original_final_status"], "pitch_policy": policy,
                "stored_lattice_artifact": data["current"][key]["artifact"],
                "stored_lattice_content_sha256": digest(stored["stages"]["lattice"]),
                "unspelled_candidates": stored["unspelled_candidates"], "lattice_status": stored["stages"]["lattice"]["status"]}
    if (set(index) != {"context_key", "artifact", "sha256", "view_ref", "planned_groups"}
            or index["context_key"] != list(key) or index["sha256"] != data["hashes"][str(path)]
            or index["view_ref"] != common.ref(view) or index["planned_groups"] != len(groups)
            or saved != expected):
        raise ValueError("meaning_context_fresh_candidate_replay_mismatch")
    return expected


def _paths(group):
    paths = list(group["paths"]) + [row["split_path"] for row in group["controls"]]
    if len({p["record_id"] for p in paths}) != len(paths):
        raise ValueError("duplicate_competing_path_identity")
    return paths


def _entry(graph, clause=None):
    clause = {} if clause is None else clause
    result = query(graph, required_links=clause.get("required_links", []),
                   forbidden_links=clause.get("forbidden_links", []))
    if result["status"] != "exact_count":
        return None, result
    return {"graph": graph, "query": result, "witness": materialize_witness(graph, result)}, result


def _requests(compilations, nct_records, budget):
    """All singleton critical voices, LT/seventh pairs and their NCT pairs.

    This is a declared first/second-order request scope, NOT every possible
    multi-rule subset.  A doubled leading tone is not automatically required
    in every voice.  The whole count is checked before materialization.
    """
    records = {common.ref(p)["record_id"]: rows for p, rows in nct_records}
    inventories, count = [], 0
    for overlay, compiled in compilations:
        rows = [r for r in compiled["rules"] if r["status"] == "conditional_resolution_shape"]
        grouped = defaultdict(list)
        for row in rows:
            grouped[row["function_ref"]].append(row)
        pairs = sum(sum(r["critical_role"] == "leading_tone" for r in items)
                    * sum(r["critical_role"] == "seventh" for r in items) for items in grouped.values())
        nct_rows = records[overlay["functions"]["path_ref"]["record_id"]]
        resolution_count = len(rows) + pairs
        planned = resolution_count * (1 + len(nct_rows))
        count += planned
        inventories.append((overlay, compiled, rows, grouped, nct_rows))
    if count > budget:
        return {"planned_requests": count, "scope": "single_critical_voice_and_LT_seventh_pair_each_with_one_optional_NCT",
                "status": "withheld_joint_request_budget_no_partial_sampling", "requests": [],
                "all_multi_rule_subsets_exhaustive": False}
    requests = []
    for overlay, compiled, rows, grouped, nct_rows in inventories:
        subsets = [[r["resolution_id"]] for r in rows]
        for values in grouped.values():
            subsets.extend([a["resolution_id"], b["resolution_id"]] for a in values for b in values
                           if a["critical_role"] == "leading_tone" and b["critical_role"] == "seventh")
        for subset in subsets:
            for nct_request in [[], *[[row] for row in nct_rows]]:
                requests.append({"path_ref": overlay["functions"]["path_ref"],
                    "key_track_ref": common.ref(overlay["key_track"]),
                    "requested_resolution_refs": [{"compiled_ref": common.ref(compiled), "resolution_id": rid}
                                                  for rid in subset],
                    "requested_nct_refs": nct_request})
    if len(requests) != count:
        raise ValueError("joint_request_inventory_cardinality_mismatch")
    return {"planned_requests": count, "scope": "single_critical_voice_and_LT_seventh_pair_each_with_one_optional_NCT",
            "status": "requests_prepared", "requests": requests, "all_multi_rule_subsets_exhaustive": False}


def _assessed_bundles(solution):
    if solution["status"] != "joint_possible" or solution["all_requested_branches_assessed"] is not True:
        return []
    return [branch["completion_bundle"] for branch in solution["branches"]
            if branch["status"] == "joint_possible" and branch["completion_bundle"] is not None]


def evaluate_group(view, group, key_scope, graphs, *, pair_budget=4096,
                   overlay_pair_budget=65536, functional_budget=16384, request_budget=256):
    result = {"group_id": group["group_id"], "original_status": group["status"], "status": group["status"],
              "planned_paths": group["planned_paths"], "overlays": [], "resolutions": [],
              "request_inventory": None, "solutions": [], "comparisons": [], "selected": None}
    if group["status"] != "paths_prepared":
        return result
    paths = _paths(group)
    pairs = len(paths) * (len(paths) - 1) // 2
    result["planned_comparison_pairs"] = pairs
    if pairs > pair_budget:
        result["status"] = "withheld_comparison_pair_budget"
        return result
    tracks = key_scope["tracks"]
    interpretation_count = len(paths) * len(tracks)
    result["planned_interpretation_pairs"] = interpretation_count * (interpretation_count - 1) // 2
    if result["planned_interpretation_pairs"] > overlay_pair_budget:
        result["status"] = "withheld_whole_interpretation_pair_budget"
        return result
    count = sum(len(p["segments"]) * 10 for p in paths) * len(tracks)
    result["planned_function_rows"] = count
    if count > functional_budget:
        result["status"] = "withheld_whole_function_inventory_budget"
        return result
    overlays = [{"key_track": key, "functions": functional.compile_functions(view, path, key)}
                for path in paths for key in tracks]
    result["overlays"] = overlays
    compilations = []
    by_path = {p["record_id"]: p for p in paths}
    for overlay in overlays:
        path = by_path[overlay["functions"]["path_ref"]["record_id"]]
        compiled = resolution.compile_resolutions(view, path, overlay["key_track"], overlay["functions"], graphs)
        compilations.append((overlay, compiled))
    result["resolutions"] = [r for _, r in compilations]
    if not graphs:
        result["status"] = "withheld_no_ready_geometry"
        return result
    entries = []
    for graph in graphs:
        entry, answer = _entry(graph)
        if entry is None:
            result["status"] = "withheld_baseline_completion"
            result["completion_failure"] = answer
            return result
        entries.append(entry)
    baseline = resolution.make_bundle(view, paths, entries)
    result["comparisons"].append(comparison.compare_functional(view, paths, overlays, baseline))
    nct_records = []
    for path in paths:
        requests = []
        for graph in graphs:
            compiled = nct.compile_rules(view, path, graph)
            requests.extend({"graph_ref": common.ref(graph), "compiled": compiled, "rule_id": row["rule_id"]}
                            for row in compiled["rules"] if row["status"] == "conditional_shape")
        nct_records.append((path, requests))
    inventory = _requests(compilations, nct_records, request_budget)
    result["request_inventory"] = inventory
    by_overlay = {(r["functions"]["path_ref"]["record_id"], r["key_track"]["record_id"]): r for r in overlays}
    seen_bundles = {baseline["record_id"]}
    for request in inventory["requests"]:
        path = by_path[request["path_ref"]["record_id"]]
        overlay = by_overlay[(path["record_id"], request["key_track_ref"]["record_id"])]
        solution = resolution.solve_joint(view, path, overlay["key_track"], overlay["functions"], graphs,
                   request["requested_resolution_refs"], request["requested_nct_refs"], comparison_paths=paths)
        result["solutions"].append({"request": request, "solution": solution})
        # A possible solution is not a selected interpretation. Each bundle is
        # reused for ALL competing paths, not just the path that requested it.
        for bundle in _assessed_bundles(solution):
            if bundle["record_id"] not in seen_bundles:
                seen_bundles.add(bundle["record_id"])
                result["comparisons"].append(comparison.compare_functional(view, paths, overlays, bundle))
    result["status"] = "conditional_functional_comparison_complete"
    return result


def evaluate_groups(view, groups, scope, graphs, **budgets):
    results, errors = [], []
    for group in groups:
        try:
            results.append(evaluate_group(view, group, scope, graphs, **budgets))
        except Exception as exc:
            error = f"{type(exc).__name__}:{exc}"
            errors.append(group["group_id"] + ":" + error)
            results.append({"group_id": group["group_id"], "original_status": group["status"],
                "planned_paths": group["planned_paths"], "status": "calculation_failure", "error": error,
                "overlays": [], "resolutions": [], "request_inventory": None,
                "solutions": [], "comparisons": [], "selected": None})
    return results, errors


def run(baseline, lineage, musical_meaning, output, *, pair_budget=4096,
        overlay_pair_budget=65536, functional_budget=16384, request_budget=256):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("output_must_be_new_direct_workspace_child")
    for budget in (pair_budget, overlay_pair_budget, functional_budget, request_budget):
        if type(budget) is not int or budget < 1:
            raise ValueError("positive_functional_trial_budget_required")
    data = load_inputs(baseline, lineage, musical_meaning)
    inputs = deepcopy(data["hashes"])
    code = {str(p.resolve()): parent.file_digest(p) for p in parent._code_paths()}
    plan = {"version": VERSION, "baseline": str(data["baseline"]), "lineage": str(data["lineage"]),
            "musical_meaning": str(data["meaning"]), "inputs": inputs, "code": code,
            "pair_budget": pair_budget, "overlay_pair_budget": overlay_pair_budget,
            "functional_budget": functional_budget, "request_budget": request_budget,
            "expected_contexts": [list(k) for k in data["contexts"]], "expected_lanes": len(data["units"]),
            "all_denominators_retained": True, "old_selectors_engines_reexecuted": False,
            "geometry_recomputed": False, "source_annotation_labels_used": False,
            "key_scope": "signature compatible major/minor forms plus unknown; changing/missing/ambiguous=>unknown",
            "production_modified": False}
    output.mkdir()
    artifacts, indices, unit_indices = {}, [], []
    meaning._save(output, "run-plan.json", plan, artifacts)
    statuses, function_statuses, function_kinds, resolution_statuses, joint_statuses = (Counter() for _ in range(5))
    key_statuses, compiler_statuses, bundle_resolution_statuses, request_statuses = (Counter() for _ in range(4))
    compared_contexts = positive_contexts = failures = comparison_count = function_rows = resolution_rows = 0
    conditionally_satisfied_contexts = planned_requests = 0
    for pair in data["packages"]:
        historical_ir, ir, revision = parent._working_case(data, pair)
        ir_before = digest(ir)
        for key, obs_index in data["contexts"].items():
            if key[0] != pair:
                continue
            observation = parent._observation(data, key, historical_ir, ir, revision, literal=False)
            if Path(obs_index["path"]).resolve() != data["baseline"] / "observations" / (observation["record_id"] + ".json"):
                raise ValueError("foreign_baseline_observation_artifact")
            audit = meaning._audit_packet(data, key, observation)
            context = _context(data, key, observation, ir, audit)
            view, groups = context["view"], context["groups"]
            scope = key_candidates(view)
            key_statuses[scope["status"]] += 1
            graphs, lane_inventory = [], []
            for lane in observation["raw_lanes"]:
                lane_key = (lane["part_id"], lane["voice_id"])
                unit = meaning._baseline_unit(data, key, observation, lane_key, audit)
                graph = unit["unit"]["graph"]
                if graph is not None and graph["status"] == "ready":
                    graphs.append(graph)
                snapshot = {"context_key": list(key), "lane": list(lane_key),
                            "old_geometry_status": unit["unit"]["status"],
                            "old_geometry_reasons": deepcopy(unit["unit"]["reasons"]),
                            "graph_ref": None if graph is None else common.ref(graph),
                            "parent_gate": deepcopy(data["gates"][(key, lane_key)])}
                lane_inventory.append(snapshot)
                unit_indices.append(deepcopy(snapshot))
            before = digest([context, graphs, lane_inventory])
            result = {"version": VERSION, "context_key": list(key), "context": context, "key_scope": scope,
                      "lane_inventory": lane_inventory, "groups": [], "error": None,
                      "selected": None, "training_eligible": False, "gold_eligible": False, "generation_ready": False}
            result["groups"], group_errors = evaluate_groups(view, groups, scope, graphs,
                pair_budget=pair_budget, overlay_pair_budget=overlay_pair_budget,
                functional_budget=functional_budget, request_budget=request_budget)
            result["status"] = "calculation_failure" if group_errors else "calculation_complete_not_selected"
            result["error"] = "; ".join(group_errors) if group_errors else None
            failures += len(group_errors)
            if before != digest([context, graphs, lane_inventory]) or digest(ir) != ir_before:
                raise ValueError("functional_inputs_mutated")
            path = meaning._save(output, "contexts/" + observation["record_id"] + ".json.gz", result, artifacts, compressed=True)
            indices.append({"context_key": list(key), "artifact": str(path), "sha256": artifacts[str(path)],
                            "status": result["status"], "error": result["error"]})
            compared = positive = satisfied = False
            for group in result["groups"]:
                statuses[group["status"]] += 1
                comparison_count += len(group["comparisons"])
                compared |= bool(group["comparisons"])
                for overlay in group["overlays"]:
                    rows = overlay["functions"]["rows"]
                    function_rows += len(rows)
                    function_statuses.update(row["status"] for row in rows)
                    function_kinds.update(row["function_kind"] for row in rows)
                for compiled in group["resolutions"]:
                    compiler_statuses[compiled["status"]] += 1
                    resolution_rows += len(compiled["rules"])
                    resolution_statuses.update(row["status"] for row in compiled["rules"])
                    positive |= any(row["status"] == "conditional_resolution_shape" for row in compiled["rules"])
                joint_statuses.update(r["solution"]["status"] for r in group["solutions"])
                request_inventory = group["request_inventory"]
                if request_inventory is not None:
                    request_statuses[request_inventory["status"]] += 1
                    planned_requests += request_inventory["planned_requests"]
                for compared_record in group["comparisons"]:
                    for evaluated in compared_record["resolution_evaluations"]:
                        bundle_resolution_statuses.update(r["status"] for r in evaluated["assessments"])
                        satisfied |= any(r["status"] == "conditional_resolution_under_bundle" for r in evaluated["assessments"])
            compared_contexts += int(compared)
            positive_contexts += int(positive)
            conditionally_satisfied_contexts += int(satisfied)
            print(f"[{len(indices)}/{len(data['contexts'])}] contexts; {len(unit_indices)} raw lanes; failures={failures}", flush=True)
    if ({parent._key(r) for r in indices} != set(data["contexts"])
            or {(parent._key(r), tuple(r["lane"])) for r in unit_indices} != set(data["units"])):
        raise ValueError("functional_denominator_loss")
    meaning._save(output, "context-index.json", indices, artifacts)
    meaning._save(output, "unit-index.json", unit_indices, artifacts)
    changed = [p for p, sha in {**inputs, **code}.items() if not Path(p).is_file() or parent.file_digest(p) != sha]
    if {str(p.resolve()) for p in parent._code_paths()} != set(code):
        changed.append("current_code_inventory_changed")
    for directory, inventory in data["inventories"].items():
        if {str(p.resolve()) for p in Path(directory).rglob("*") if p.is_file()} != inventory:
            changed.append("parent_inventory_changed:" + directory)
    changed_outputs = [p for p, sha in artifacts.items() if not Path(p).is_file() or parent.file_digest(p) != sha]
    if {str(p.resolve()) for p in output.rglob("*") if p.is_file()} != set(artifacts):
        changed_outputs.append("new_artifact_inventory_changed")
    report = {"version": VERSION, "complete": not changed and not changed_outputs and not failures,
              "inputs_and_code_unchanged": not changed, "artifacts_unchanged": not changed_outputs,
              "computation_integrity_passed": failures == 0, "artifact_hashes": artifacts,
              "changed_inputs_or_code": changed, "changed_artifacts": changed_outputs,
              "elapsed_seconds": perf_counter() - started, "summary": {
                "work_families": data["report"]["summary"]["work_families"], "packages": len(data["packages"]),
                "contexts": len(indices), "raw_lanes": len(unit_indices), "compared_contexts": compared_contexts,
                "conditional_resolution_shape_contexts": positive_contexts, "group_status_counts": dict(statuses),
                "conditionally_satisfied_resolution_contexts": conditionally_satisfied_contexts,
                "bundle_resolution_status_counts": dict(bundle_resolution_statuses),
                "key_scope_status_counts": dict(key_statuses), "resolution_compiler_status_counts": dict(compiler_statuses),
                "planned_joint_requests": planned_requests, "request_inventory_status_counts": dict(request_statuses),
                "comparison_count": comparison_count, "function_rows": function_rows,
                "function_status_counts": dict(function_statuses), "function_kind_counts": dict(function_kinds),
                "resolution_rows": resolution_rows, "resolution_status_counts": dict(resolution_statuses),
                "joint_status_counts": dict(joint_statuses), "calculation_failures": failures,
                "old_geometry_status_counts": data["report"]["summary"]["status_counts"],
                "source_gate_counts": data["lineage_report"]["summary"]["gate_status_counts"],
                "human_validated": 0, "training_eligible": 0, "gold_eligible": 0, "generation_ready": 0},
              "selected": None, "musical_accuracy_measured": False, "production_modified": False,
              "source_labels_used_for_inference": False, "core_modified": False, "external_transmission": False,
              "limits": ["Key/function/voice hypotheses are not selected musical analyses.",
                 "Known key candidates are signature-compatible reference forms, not all possible local keys.",
                 "Literal boundary support and later distributed membership are different evidence axes.",
                 "Conditional resolutions and arrivals do not certify consonance, perceived accent or cadence.",
                 "All raw lanes remain; withheld geometry is not fabricated or disproved.",
                 "Joint requests are declared singleton/LT-seventh/one-NCT scope, not exhaustive multi-rule subsets."]}
    parent.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "lineage", "musical-meaning", "output"):
        parser.add_argument("--" + name, required=True)
    for name, default in (("pair-budget", 4096), ("overlay-pair-budget", 65536),
                         ("functional-budget", 16384), ("request-budget", 256)):
        parser.add_argument("--" + name, type=int, default=default)
    report = run(**vars(parser.parse_args()))
    print(report["summary"])
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
