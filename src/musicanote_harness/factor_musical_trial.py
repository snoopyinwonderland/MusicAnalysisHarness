"""Append-only factor-conditioned comparisons of frozen candidate harmonies.

Every frozen raw lane remains in the denominator. Candidate paths and source
clock diagnostics are hypotheses/guards, never a selected harmonic analysis.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import gzip
from itertools import combinations, product
from pathlib import Path
from time import perf_counter

from . import harmony_frozen_context_lineage_trial as parent
from .factor_musical_view import prepare, make_path, ref, f, q, span_bounds
from .factor_musical_rules import compile_rules
from .factor_musical_joint import solve_joint, compare_under_completion
from .harmony_factorized_voice_paths import query, materialize_witness
from .musical_pattern_observation import digest

ROOT = parent.ROOT
VERSION = "factor-musical-trial-0.1.0"


def _completed(directory, version, hashes, inventories):
    directory = Path(directory).resolve(strict=True)
    report_path = directory / "report.json"
    report = parent.read(report_path)
    if report.get("version") != version or any(report.get(k) is not True for k in
            ("complete", "inputs_and_code_unchanged", "artifacts_unchanged", "computation_integrity_passed")):
        raise ValueError("completed_supported_parent_required")
    if report.get("changed_inputs_or_code") != [] or report.get("changed_artifacts") != []:
        raise ValueError("changed_parent_not_allowed")
    parent._guard({str(report_path): parent.file_digest(report_path)}, hashes)
    parent._guard(report["artifact_hashes"], hashes)
    inventories[str(directory)] = parent._inventory(directory, hashes)
    return report


def load_inputs(baseline, lineage):
    """The completed protected baseline is the historical trust boundary."""
    data = parent._inputs(Path(baseline).resolve(strict=True))
    # Capture the completed baseline boundary before adding any child artifacts
    # or the lineage producer's additive code inventory.
    baseline_inputs = deepcopy(data["hashes"])
    lineage = Path(lineage).resolve(strict=True)
    lr = _completed(lineage, parent.VERSION, data["hashes"], data["inventories"])
    lp = parent._load(lineage / "run-plan.json", data["hashes"])
    if (lp.get("version") != parent.VERSION or Path(lp["baseline"]).resolve() != data["baseline"]
            or lp.get("inputs") != baseline_inputs
            or lp.get("expected_context_keys") != [list(key) for key in data["contexts"]]
            or lp.get("expected_raw_lane_units") != len(data["units"])
            or any(lp.get(flag) is not False for flag in
                   ("old_engines_or_selector_recomputed", "source_xml_inspected",
                    "source_labels_used_for_inference", "geometry_recomputed"))):
        raise ValueError("lineage_plan_baseline_inputs_or_policy_mismatch")
    parent._guard(lp["inputs"], data["hashes"])
    parent._guard(lp["code"], data["hashes"])
    audits = parent._unique(parent._load(lineage / "audit-index.json", data["hashes"]),
                            parent._key, "duplicate_lineage_context")
    gates = parent._unique(parent._load(lineage / "gate-index.json", data["hashes"]),
        lambda r: (parent._key(r), tuple(r["lane"])), "duplicate_lineage_lane")
    if set(audits) != set(data["contexts"]) or set(gates) != set(data["units"]):
        raise ValueError("lineage_denominator_mismatch")
    if (len(gates) != lr["summary"]["raw_lane_units"]
            or len(audits) != lr["summary"]["contexts"]
            or dict(Counter(r["status"] for r in audits.values())) != lr["summary"]["context_status_counts"]
            or dict(Counter(r["gate_status"] for r in gates.values())) != lr["summary"]["gate_status_counts"]):
        raise ValueError("lineage_status_inventory_mismatch")
    if (any(lr.get(flag) is not False for flag in
            ("source_labels_used_for_inference", "source_xml_inspected", "source_xml_certified",
             "voice_identity_certified", "performed_timing_certified", "concert_pitch_certified",
             "geometry_recomputed", "old_engines_or_selector_recomputed", "old_harmony_or_nct_inventory_modified",
             "semantic_eligible", "generation_ready", "external_transmission"))
            or any(lr["summary"].get(flag) != 0 for flag in
                   ("human_validated", "training_eligible", "gold_eligible", "generation_ready"))
            or lr["summary"].get("diagnostic_failures") != 0
            or lr["summary"].get("original_geometry_status_counts_preserved") != data["report"]["summary"]["status_counts"]):
        raise ValueError("lineage_report_policy_or_preserved_status_mismatch")
    data.update(lineage=lineage, lineage_report=lr, audits=audits, gates=gates)
    return data


def _audit_packet(data, key, observation):
    index = data["audits"][key]
    path = Path(index["artifact"]).resolve(strict=True)
    if path != data["lineage"] / "audits" / (observation["record_id"] + ".json"):
        raise ValueError("foreign_lineage_audit_artifact")
    packet = parent._load(path, data["hashes"])
    audit = packet.get("audit")
    expected_keys = {"version", "context_key", "observation_ref", "baseline_observation_artifact",
                     "baseline_observation_file_sha256", "status", "error", "audit", "selected",
                     "semantic_eligible", "training_eligible", "generation_ready"}
    index_keys = {"context_key", "observation_ref", "audit_ref", "source_clock_consistency_passed",
                  "status", "error", "artifact", "sha256"}
    row = data["contexts"][key]
    if (set(packet) != expected_keys or set(index) != index_keys or packet["version"] != parent.VERSION
            or packet["context_key"] != list(key) or packet["observation_ref"] != ref(observation)
            or packet["baseline_observation_artifact"] != row["path"]
            or packet["baseline_observation_file_sha256"] != row["sha256"]
            or packet["status"] != "diagnostic_complete" or packet["error"] is not None
            or packet["selected"] is not None
            or any(packet[flag] is not False for flag in ("semantic_eligible", "training_eligible", "generation_ready"))
            or not isinstance(audit, dict) or index["context_key"] != list(key)
            or index["observation_ref"] != ref(observation) or index["audit_ref"] != ref(audit)
            or index["sha256"] != data["hashes"][str(path)] or index["error"] is not None
            or index["source_clock_consistency_passed"] is not audit["source_clock_consistency_passed"]
            or index["status"] != ("source_clock_consistent" if audit["source_clock_consistency_passed"]
                                    else "source_clock_not_consistent_or_not_assessed")):
        raise ValueError("lineage_audit_index_or_packet_binding_mismatch")
    return packet


def _baseline_unit(data, key, observation, lane, audit_packet):
    lane = list(lane)
    index = data["units"][(key, tuple(lane))]
    path = Path(index["artifact"]).resolve(strict=True)
    expected_path = data["baseline"] / "units" / observation["record_id"] / (digest(lane)[:16] + ".json.gz")
    if path != expected_path:
        raise ValueError("foreign_baseline_unit_artifact")
    unit = parent._load(path, data["hashes"], compressed=True)
    context = data["contexts"][key]
    geometry = unit["unit"]
    unit_keys = {"version", "context_key", "observation_ref", "lane", "original_stage_statuses",
                 "original_final_status", "unit", "parent_context_artifact", "selected",
                 "harmonic_or_role_claim", "training_eligible", "generation_ready"}
    index_keys = {"context_key", "observation_ref", "lane", "status", "reasons", "artifact", "sha256"}
    if (set(unit) != unit_keys or set(index) != index_keys
            or unit["version"] != parent.BASELINE_VERSION or unit["context_key"] != list(key)
            or unit["lane"] != lane or unit["observation_ref"] != ref(observation)
            or index["context_key"] != list(key) or index["lane"] != lane
            or index["observation_ref"] != ref(observation) or index["sha256"] != data["hashes"][str(path)]
            or index["status"] != geometry["status"] or index["reasons"] != geometry["reasons"]
            or unit["original_final_status"] != context["original_final_status"]
            or unit["original_stage_statuses"] != context["original_stage_statuses"]
            or unit["parent_context_artifact"] != data["current"][key]
            or unit.get("selected") is not None
            or any(unit.get(flag) is not False for flag in ("harmonic_or_role_claim", "training_eligible", "generation_ready"))):
        raise ValueError("baseline_unit_index_or_packet_binding_mismatch")
    positive, points = parent._owned_sound_refs(observation, lane)
    graph = geometry["graph"]
    if graph is not None and ({s["sounding_event_id"] for s in graph["events"]} != set(positive)
                              or set(graph["sampled_lane_point_sound_refs"]) != set(points)):
        raise ValueError("baseline_graph_selected_lane_sound_ownership_mismatch")
    data["unit_snapshots"][(key, tuple(lane))] = {
        "baseline_unit_content_sha256": digest(unit), "geometry_result_content_sha256": digest(geometry),
        "geometry_status": geometry["status"], "geometry_reasons": deepcopy(geometry["reasons"]),
        "probe_status_inventory": dict(Counter(p["answer"]["status"] for p in geometry["constraint_probes"])),
        "original_final_status": unit["original_final_status"],
        "original_stage_statuses": deepcopy(unit["original_stage_statuses"])}
    audit_index = data["audits"][key]
    expected_gate = parent._gate(data, key, observation, lane, audit_packet["audit"],
                                 audit_index["artifact"], audit_index["sha256"])
    if data["gates"][(key, tuple(lane))] != expected_gate:
        raise ValueError("lineage_gate_exact_metadata_or_no_promotion_mismatch")
    return unit


def _provenance():
    return {"kind": "caller_hypothesis", "engine_version": VERSION,
            "source_document_sha256": None, "source_path": None,
            "pitch_basis": "written_IR_not_concert_certified", "status": "hypothesis_not_gold"}


def _segment(reading, index):
    blockers = list(reading.get("abstention_reasons", []))
    if not reading.get("members"):
        blockers.append("no_spelled_members")
    return {"segment_id": "segment_" + str(index) + "_" + digest(reading)[:24], "span": deepcopy(reading["span"]),
            "root": None if reading.get("root_spelling") is None else
                {"step": reading["root_spelling"][0], "alter": _alter(reading["root_spelling"][1])},
            "members": [{"step": p[0], "alter": _alter(p[1])} for p in reading["members"]],
            "status": "blocked" if blockers else "usable", "blockers": sorted(set(blockers))}


def _alter(value):
    if isinstance(value, dict):
        return q(f(value))
    if type(value) not in (int, float):
        raise ValueError("unsupported_stored_alter")
    return q(Fraction(str(value)))


def path_groups(view, lattice, *, path_budget=128):
    """All complete hold readings and all two-segment readings at every cut.

    Budgets withhold an ENTIRE named group, not the favorable paths within it.
    Stored origin rows, unspelled refs and old status remain available separately.
    A same-member split control is included for every complete hold reading.
    """
    if isinstance(path_budget, bool) or not isinstance(path_budget, int) or path_budget < 1:
        raise ValueError("positive_path_budget_required")
    start, end = span_bounds(view["context_span"])
    edges = lattice.get("edges", [])
    planned = lattice.get("plan", {})
    if not planned and lattice.get("status") != "ready":
        return [{"group_id": "stored_lattice_unavailable", "kind": "unavailable", "cut": None,
                 "planned_paths": None, "status": "withheld_stored_lattice_no_plan",
                 "old_lattice_status": lattice.get("status"), "old_lattice_payload": deepcopy(lattice),
                 "paths": [], "candidate_bindings": [], "controls": []}]
    if planned.get("context_span") != view["context_span"]:
        raise ValueError("lattice_context_binding_mismatch")
    def at(a, b):
        rows = [e for e in edges if span_bounds(e["span"]) == (a, b)]
        if len(rows) > 1:
            raise ValueError("duplicate_lattice_edge")
        return [] if not rows else rows[0]["readings"]
    holds = at(start, end)
    cuts = sorted({f(p) for p in planned.get("points", []) if start < f(p) < end})
    specs = [("hold", None, len(holds), holds)]
    for cut in cuts:
        left, right = at(start, cut), at(cut, end)
        specs.append(("change", cut, len(left) * len(right), (left, right)))
    groups = []
    for kind, cut, count, rows in specs:
        disposition = ("no_complete_spelled_paths" if count == 0 else
                       "withheld_path_budget" if count > path_budget else "paths_prepared")
        group = {"group_id": kind + ":" + ("full" if cut is None else str(cut)),
                 "kind": kind, "cut": None if cut is None else q(cut), "planned_paths": count,
                 "status": disposition, "paths": [], "candidate_bindings": [], "controls": []}
        if disposition == "paths_prepared":
            choices = [(r,) for r in rows] if kind == "hold" else product(*rows)
            for readings in choices:
                path = make_path(view, [_segment(r, i) for i, r in enumerate(readings)], _provenance())
                group["paths"].append(path)
                group["candidate_bindings"].append({"path_ref": ref(path),
                    "stored_readings": deepcopy(list(readings)), "reading_content_sha256": digest(list(readings))})
                if kind == "hold" and cuts:
                    first = _segment(readings[0], 0)
                    second = deepcopy(first)
                    first["span"]["end"], second["span"]["start"] = q(cuts[0]), q(cuts[0])
                    second["segment_id"] = first["segment_id"] + "_split_right"
                    control = make_path(view, [first, second], _provenance())
                    group["controls"].append({"original_ref": ref(path), "split_path": control})
        groups.append(group)
    return groups


def evaluate_group(view, group, graph, *, rule_budget=4096, witness_budget=32, joint_pair_budget=256, pair_budget=4096):
    """Use each query's ONE witness for ALL competing paths in that comparison."""
    result = {"group_id": group["group_id"], "status": group["status"],
              "planned_paths": group["planned_paths"], "compiled": [], "comparisons": [],
              "joint_probes": [], "probe_status": "not_assessed", "selected": None}
    if group["status"] != "paths_prepared" or graph["status"] != "ready":
        if graph["status"] != "ready":
            result["status"] = "withheld_geometry"
        return result
    paths = list(group["paths"]) + [r["split_path"] for r in group["controls"]]
    result["planned_comparison_pairs"] = len(paths) * (len(paths) - 1) // 2
    if result["planned_comparison_pairs"] > pair_budget:
        result["status"] = "withheld_comparison_pair_budget"
        return result
    compiled = [compile_rules(view, p, graph, max_candidates=rule_budget) for p in paths]
    result["compiled"] = compiled
    result["status"] = "conditional_comparison_complete"
    base = query(graph)
    witness = materialize_witness(graph, base)
    result["comparisons"].append(compare_under_completion(view, paths, graph, base, witness, compiled))
    # Group exact link clauses across paths, not semantic votes or preferred labels.
    clauses = {}
    conditional = []
    for record in compiled:
        rows = [r for r in record["rules"] if r["status"] == "conditional_shape"]
        conditional.append(rows)
        for rule in rows:
            for clause in rule["alternatives"]:
                clauses.setdefault(digest(clause), clause)
    result["planned_clause_witnesses"] = len(clauses)
    if len(clauses) > witness_budget:
        result["probe_status"] = "withheld_witness_budget_no_partial_sampling"
    else:
        result["probe_status"] = "clause_witnesses_evaluated"
        for clause in clauses.values():
            queried = query(graph, required_links=clause["required_links"], forbidden_links=clause["forbidden_links"])
            if queried["status"] == "exact_count":
                completion = materialize_witness(graph, queried)
                result["comparisons"].append(compare_under_completion(view, paths, graph, queried, completion, compiled))
            else:
                result["joint_probes"].append({"kind": "single_clause", "query": queried})
    pair_count = sum(len(rows) * (len(rows) - 1) // 2 for rows in conditional)
    result["planned_joint_pairs"] = pair_count
    if pair_count > joint_pair_budget:
        result["joint_pair_status"] = "withheld_joint_pair_budget_no_partial_sampling"
    else:
        result["joint_pair_status"] = "joint_pairs_evaluated"
        result["joint_probes"].extend({"kind": "same_path_rule_pair", "solution": solve_joint(graph, list(pair))}
                                      for rows in conditional for pair in combinations(rows, 2))
    # These are evidence observations, not selected interpretations or exhaustive joint subsets.
    result["joint_subsets_exhaustive"] = False
    result["controls"] = deepcopy(group["controls"])
    # Same-member segmentation must not change raw or conditional time.
    for comparison in result["comparisons"]:
        accounts = {a["path_ref"]["record_id"]: a for a in comparison["accounts"]}
        for control in group["controls"]:
            left = accounts[control["original_ref"]["record_id"]]
            right = accounts[control["split_path"]["record_id"]]
            if left["raw_note_time"] != right["raw_note_time"] or left["note_time"] != right["note_time"]:
                raise ValueError("same_member_partition_control_failed")
    result["same_member_partition_controls_passed"] = True
    return result


def _save(output, relative, value, artifacts, *, compressed=False):
    path = output / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if compressed:
        import json
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        with path.open("xb") as stream:
            stream.write(gzip.compress(raw, mtime=0))
    else:
        parent.write_new(path, value)
    artifacts[str(path.resolve())] = parent.file_digest(path)
    return path


def run(baseline, lineage, output, *, path_budget=128, witness_budget=32, joint_pair_budget=256):
    started = perf_counter()
    output = Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("output_must_be_new_direct_workspace_child")
    for value in (path_budget, witness_budget, joint_pair_budget):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("positive_trial_budget_required")
    data = load_inputs(baseline, lineage)
    inputs = deepcopy(data["hashes"])
    code = {str(p.resolve()): parent.file_digest(p) for p in parent._code_paths()}
    plan = {"version": VERSION, "baseline": str(data["baseline"]), "lineage": str(data["lineage"]),
            "inputs": inputs, "code": code, "path_budget": path_budget, "witness_budget": witness_budget,
            "joint_pair_budget": joint_pair_budget, "expected_contexts": [list(k) for k in data["contexts"]],
            "expected_lanes": len(data["units"]), "path_scope": "all complete hold and every single-cut two-segment stored readings",
            "all_denominators_retained": True, "source_annotation_labels_used": False,
            "old_selectors_engines_reexecuted": False, "production_modified": False}
    output.mkdir()
    artifacts = {}
    _save(output, "run-plan.json", plan, artifacts)
    indices, context_indices, statuses, groups_status, families, joint_status = [], [], Counter(), Counter(), Counter(), Counter()
    failures = 0
    for pair in data["packages"]:
        historical_ir, ir, revision = parent._working_case(data, pair)
        ir_before = digest(ir)
        for key, obs_index in data["contexts"].items():
            if key[0] != pair:
                continue
            # Existing lightweight origin/index replay, never literal=True's
            # full-Core projection or any obsolete harmony producer.
            obs = parent._observation(data, key, historical_ir, ir, revision, literal=False)
            if Path(obs_index["path"]).resolve() != data["baseline"] / "observations" / (obs["record_id"] + ".json"):
                raise ValueError("foreign_baseline_observation_artifact")
            audit_packet = _audit_packet(data, key, obs)
            # New bounded literal replay; no repeated full-score Core schema validation.
            view = prepare(ir, obs, audit_packet["audit"])
            stored = parent._load(data["current"][key]["artifact"], data["hashes"], compressed=True)
            bundle = stored["bundle"]
            if bundle["input_ir_content_sha256"] != view["binding"]["ir_content_sha256"] or bundle["sample"]["span"] != view["context_span"]:
                raise ValueError("stored_candidate_working_context_mismatch")
            if (obs_index["original_stage_statuses"] != bundle["stage_statuses"]
                    or obs_index["original_final_status"] != data["current"][key]["previous_status"]):
                raise ValueError("original_context_stage_or_final_status_mismatch")
            groups = path_groups(view, bundle["stages"]["lattice"], path_budget=path_budget)
            pitch_policy = deepcopy(data["packages"][pair]["source"]["pitch_policy"])
            if pitch_policy.get("harmonic_replay_allowed") is not True:
                for g in groups:
                    g["status"] = "withheld_pitch_policy"
            context_path = _save(output, "contexts/" + obs["record_id"] + ".json.gz", {
                "view": view, "groups": groups, "old_stage_statuses": obs_index["original_stage_statuses"],
                "original_final_status": obs_index["original_final_status"],
                "pitch_policy": pitch_policy, "stored_lattice_artifact": data["current"][key]["artifact"],
                "stored_lattice_content_sha256": digest(bundle["stages"]["lattice"]),
                "unspelled_candidates": bundle["unspelled_candidates"], "lattice_status": bundle["stages"]["lattice"]["status"]}, artifacts, compressed=True)
            context_indices.append({"context_key": list(key), "artifact": str(context_path), "sha256": artifacts[str(context_path)],
                                    "view_ref": ref(view), "planned_groups": len(groups)})
            for lane in obs["raw_lanes"]:
                lane_key = (lane["part_id"], lane["voice_id"])
                gate = data["gates"][(key, lane_key)]
                unit = _baseline_unit(data, key, obs, lane_key, audit_packet)
                before = digest([view, groups, unit])
                result = {"version": VERSION, "context_key": list(key), "lane": list(lane_key), "view_ref": ref(view),
                          "parent_gate": deepcopy(gate), "old_geometry_status": unit["unit"]["status"], "groups": [], "error": None,
                          "selected": None, "training_eligible": False, "gold_eligible": False, "generation_ready": False}
                try:
                    result["groups"] = [evaluate_group(view, g, unit["unit"]["graph"], witness_budget=witness_budget,
                            joint_pair_budget=joint_pair_budget) for g in groups]
                    result["status"] = ("conditional_calculation_complete" if unit["unit"]["status"] == "ready" else "withheld_geometry")
                except Exception as exc:
                    result["status"] = "calculation_failure"
                    result["error"] = f"{type(exc).__name__}:{exc}"
                    failures += 1
                if before != digest([view, groups, unit]) or ir_before != digest(ir):
                    raise ValueError("meaning_inputs_mutated")
                token = digest([list(key), list(lane_key)])[:24]
                path = _save(output, "units/" + token + ".json.gz", result, artifacts, compressed=True)
                indices.append({"context_key": list(key), "lane": list(lane_key), "artifact": str(path),
                                "sha256": artifacts[str(path)], "status": result["status"], "error": result["error"]})
                statuses[result["status"]] += 1
                for g in result["groups"]:
                    groups_status[g["status"]] += 1
                    for c in g["compiled"]:
                        families.update((r["family"], r["status"]) for r in c["rules"])
                    joint_status.update(p["solution"]["status"] for p in g["joint_probes"] if "solution" in p)
            print(f"[{len(context_indices)}/{len(data['contexts'])}] contexts; {len(indices)} raw lanes; failures={failures}", flush=True)
    if ({(parent._key(r), tuple(r["lane"])) for r in indices} != set(data["units"])
            or {parent._key(r) for r in context_indices} != set(data["contexts"])):
        raise ValueError("meaning_denominator_loss")
    _save(output, "context-index.json", context_indices, artifacts)
    _save(output, "unit-index.json", indices, artifacts)
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
                  "contexts": len(context_indices), "raw_lanes": len(indices), "status_counts": dict(statuses),
                  "group_status_counts": dict(groups_status), "rule_instance_counts": {str(k): v for k, v in families.items()},
                  "joint_status_counts": dict(joint_status), "calculation_failures": failures,
                  "old_geometry_status_counts": data["report"]["summary"]["status_counts"],
                  "source_gate_counts": data["lineage_report"]["summary"]["gate_status_counts"],
                  "human_validated": 0, "training_eligible": 0, "gold_eligible": 0, "generation_ready": 0},
              "musical_accuracy_measured": False, "selected": None, "production_modified": False,
              "source_labels_used_for_inference": False, "core_modified": False, "external_transmission": False,
              "limits": ["Witnesses are conditional geometry, never selected voices or harmonic truth.",
                  "All-part note-time and one sampled lane's geometry denominator are different.",
                  "Single-cut path groups are not exhaustive multicut harmonic search.",
                  "Conditional rules and sparse completions do not certify NCT, texture, key, cadence or generation."]}
    parent.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "lineage", "output"):
        parser.add_argument("--" + name, required=True)
    for name, default in (("path-budget", 128), ("witness-budget", 32), ("joint-pair-budget", 256)):
        parser.add_argument("--" + name, type=int, default=default)
    report = run(**vars(parser.parse_args()))
    print(report["summary"])
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
