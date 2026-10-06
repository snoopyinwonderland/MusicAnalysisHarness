"""Additive saved-source request proposals, never live native authority.

Ordinary quality AND spelled root buckets prevent pooled expanded candidates
from consuming the entire proposal panel. Single-slot substitutions of the
old zipped seeds are a bounded sample, not a Cartesian path enumeration.
Shape-compatible function requests still require fresh same-completion
ordinary/NCT/key/boundary evaluation before any musical support claim.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from itertools import product
from math import prod
from pathlib import Path

from . import factor_expanded_hypotheses as kernels
from . import factor_expanded_scope as expanded
from . import factor_interval_lattice as native
from . import factor_progression_context as context
from . import factor_source_evidence_panel as prior
from . import factor_temporal_explanations as temporal
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "source-progression-proposals-0.1.0"
PREFIX = "npsprop_"
AUTHORITY = "validated_saved_source_request_not_live_native_authority"
SUMMARY_KEYS = {"requested_intervals", "assessed_origin_occurrences", "eligible_origin_occurrences",
    "rejected_origin_occurrences", "proposal_origin_occurrences", "omitted_eligible_origin_occurrences",
    "complete_proposal_paths", "eligible_cartesian_origin_paths", "omitted_eligible_cartesian_origin_paths",
    "retained_control_selectors", "additional_selectors", "total_selectors", "shape_request_occurrences"}
FLAGS = {name: False for name in ("source_annotation_labels_used", "supplier_ornaments_used",
    "role_outcomes_used_for_proposal", "native_authority_issued", "fresh_native_evaluation_performed",
    "same_completion_resolution_evaluated", "winning_harmony_selected", "function_confirmed",
    "secondary_confirmed", "cadence_confirmed", "NCT_confirmed", "training_eligible", "gold_eligible",
    "generation_ready", "production_modified", "musical_accuracy_measured")}
RULES = {
    "S01": "Keep every prior control in its original order, including adverse and None requests.",
    "S02": "Assess every origin in every requested saved interval before proposing representatives.",
    "S03": "Keep ordered-spelled ordinary triad/seventh quality AND root buckets distinct.",
    "S04": "Missing guarded members are evidence gaps, never automatic omissions or chord rejection.",
    "S05": "Keep old seeds and every one-slot substitution; record unproposed Cartesian paths.",
    "S06": "Request ordinary families only for compatible source and target shapes; keep None alternatives.",
    "S07": "Keep every registered key, including unknown; shape is not function or secondary proof.",
    "S08": "Do not evaluate links, NCT outcomes, boundary truth, rank or confidence during proposal.",
    "S09": "Whole request holds never return a favorable partial proposal prefix.",
}


def _contract():
    modules = (kernels, expanded, native, context, prior, temporal)
    return {"version": VERSION, "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "kernel_contract": kernels._contract(), "context_kernel_contract": context._contract(),
        "sources": [{"module": m.__name__, "sha256": sha256(Path(m.__file__).read_bytes()).hexdigest()}
                    for m in modules]}


def _nodes(value):
    """Finite JSON visit allowance, not elapsed-time or memory measurement."""
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise ValueError("string_JSON_keys_required")
        return 1 + sum(1 + _nodes(v) for v in value.values())
    if type(value) is list:
        return 1 + sum(_nodes(v) for v in value)
    if value is None or type(value) in (str, int, bool):
        return 1
    raise ValueError("finite_exact_JSON_required")


def _limits(**values):
    for name, value in values.items():
        native._integer(value, name)
    return values


def _validate_sources(scope, lattice, panel):
    for record, prefix in ((scope, expanded.PREFIX), (lattice, native.PREFIX), (panel, prior.PREFIX)):
        kernels._check(record, prefix)
    if (lattice["scope_ref"] != kernels._ref(scope) or lattice["binding"] != scope["binding"]
            or lattice["analysis_span"] != scope["analysis_span"]
            or panel["scope_ref"] != kernels._ref(scope) or panel["lattice_ref"] != kernels._ref(lattice)
            or panel["analysis_span"] != scope["analysis_span"]
            or panel["logical_universe"] != lattice["universe"]):
        raise ValueError("exact_saved_scope_lattice_prior_binding_required")
    points = [f(v) for v in lattice["coordinate_times"]]
    if points != sorted(set(points)) or len(points) < 2 or (points[0], points[-1]) != span_bounds(scope["analysis_span"]):
        raise ValueError("exact_saved_positive_coordinate_clock_required")
    if len({s["sound_ref"] for s in scope["sound_facts"]}) != len(scope["sound_facts"]):
        raise ValueError("unique_saved_sound_inventory_required")
    keys = lattice["keys"]
    if not keys or len({k["record_id"] for k in keys}) != len(keys):
        raise ValueError("unique_complete_registered_keys_required")
    for key in keys:
        kernels._check(key, kernels.KEY_PREFIX)
        if (len(key["segments"]) != 1 or key["segments"][0]["span"] != scope["analysis_span"]):
            raise ValueError("one_full_scope_explicit_key_segment_required")
    if panel["keys"] != [kernels._ref(k) for k in sorted(keys, key=lambda k: k["record_id"])]:
        raise ValueError("prior_complete_key_inventory_required")
    inventory, origins = {}, {}
    for entry in lattice["catalog_inventory"]:
        pair = tuple(entry["point_indices"])
        if (len(pair) != 2 or any(type(i) is not int for i in pair)
                or not 0 <= pair[0] < pair[1] < len(points) or pair in inventory
                or span_bounds(entry["span"]) != (points[pair[0]], points[pair[1]])):
            raise ValueError("unique_exact_saved_catalog_clock_required")
        inventory[pair] = entry
        for origin in entry["origins"]:
            kernels._check(origin, native.ORIGIN_PREFIX)
            if (origin["record_id"] in origins or origin["source_scope_ref"] != kernels._ref(scope)
                    or origin["scope_ref"] != kernels._ref(scope) or origin["span"] != entry["span"]
                    or origin["catalog_id"] != entry["catalog_id"]):
                raise ValueError("exact_unique_saved_origin_catalog_binding_required")
            origins[origin["record_id"]] = origin
    return points, inventory, origins, sorted(keys, key=lambda k: k["record_id"])


def _evidence(scope, origin, guards):
    """Old pooled proposal ordering with cached literal source guards."""
    signature = prior._signature(origin)
    root, members = (None, ()) if signature is None else signature
    totals = {name: f(q(0)) for name in ("member", "nonmember", "unknown", "unsupported")}
    observed, sounds, root_time = set(), [], f(q(0))
    for sound in scope["sound_facts"]:
        if sound["point"]:
            continue
        clip = kernels._overlap(sound["span"], origin["span"])
        if clip is None:
            continue
        a, b = span_bounds(clip)
        pitch = kernels._pitch_key(sound["pitch"])
        if guards[sound["sound_ref"]]:
            totals["unsupported"] += b - a
        elif pitch is None or signature is None:
            totals["unknown"] += b - a
        elif pitch in members:
            totals["member"] += b - a
            observed.add(pitch)
            sounds.append({"sound_ref": sound["sound_ref"], "source_note_refs": deepcopy(sound["source_note_refs"]),
                "full_sound_span": deepcopy(sound["span"]), "observed_span": clip})
            if pitch == root:
                root_time += b - a
        else:
            totals["nonmember"] += b - a
    reasons = ["hypothesis:" + reason for reason in origin["blockers"]]
    if signature is None:
        reasons.append("integral_written_root_and_members_unavailable")
    if totals["member"] == 0:
        reasons.append("no_guarded_literal_member_note_time")
    missing = None if signature is None else len(set(members) - observed)
    body = {"origin_ref": kernels._ref(origin), "eligible": not reasons, "reasons": sorted(set(reasons)),
        "missing_guarded_member_spellings": missing, "guarded_pooled_member_note_time": q(totals["member"]),
        "guarded_root_note_time": q(root_time), "raw_note_time_by_support": {k: q(v) for k, v in totals.items()},
        "member_sound_evidence": sounds, "root": deepcopy(origin["root"]), "members": deepcopy(origin["members"]),
        "source_ornaments_used": False, "source_annotation_labels_used": False,
        "simultaneous_core_certified": False, "selected": None, "confidence": None}
    order = (missing if missing is not None else 1000000, -totals["member"], -root_time,
        () if signature is None else signature, origin["record_id"])
    return body, order, signature


def _bucket(origin):
    # Member order is part of the ordinary contract, not merely a pitch SET.
    if kernels._ordinary_tertian(origin):
        shape = context._ordinary_shape(origin)
        if shape["status"] == "conditional_complete_ordinary_shape":
            return ("triad" if len(origin["members"]) == 3 else "seventh", shape["quality"],
                kernels._pitch_key(origin["root"]))
    return ("nonordinary_or_unassessed", None, None)


def _bucket_json(bucket):
    kind, quality, root = bucket
    return {"kind": kind, "quality": quality, "spelled_root": kernels._pitch(root),
        "classification_is_harmony_confirmation": False}


def _controls(chosen, specs, keys):
    paths, selectors = [], []
    for name, indices in specs:
        if indices is None:
            continue
        pools = [chosen[pair] for pair in zip(indices, indices[1:])]
        if any(not pool for pool in pools):
            continue
        seen = set()
        for position in range(2):
            ids = [pool[min(position, len(pool) - 1)]["origin_ref"]["record_id"] for pool in pools]
            if tuple(ids) in seen:
                continue
            seen.add(tuple(ids))
            paths.append({"partition_kind": name, "proposal_lane": position, "origin_ids": ids})
            for key in keys:
                for assumption in ([None] if len(ids) == 1 else [None, {"family": "V7", "quality": "M"}]):
                    selectors.append({"origin_ids": deepcopy(ids), "key_id": key["record_id"],
                        "transition_assumptions": [deepcopy(assumption) for _ in range(len(ids) - 1)]})
    return paths, selectors


def propose(scope, lattice, prior_panel, *, work_budget=3000000, max_paths=512, max_selectors=4096):
    limits = _limits(work_budget=work_budget, max_paths=max_paths, max_selectors=max_selectors)
    source_digest, contract = digest([scope, lattice, prior_panel]), _contract()
    points, inventory, origins, keys = _validate_sources(scope, lattice, prior_panel)
    specs = prior._partitions(points)
    pairs = sorted({pair for _, indices in specs if indices is not None for pair in zip(indices, indices[1:])})
    controls = deepcopy(prior_panel["selectors"])
    # Validation and begin/end content seals traverse the complete admitted tree.
    tree = 3 * sum(_nodes(value) for value in (scope, lattice, prior_panel))
    closure = sum(_nodes(s) for s in scope["sound_facts"])
    scan = sum((closure + 1) * (2 + len(o["members"] or ())) for pair in pairs if pair in inventory
               for o in inventory[pair]["origins"])
    sorting = sum(len(inventory[pair]["origins"]) * max(1, len(inventory[pair]["origins"]).bit_length())
                  for pair in pairs if pair in inventory)
    work = tree + scan + sorting
    plan = {"input_visit_work": tree, "source_scan_and_sort_work": scan + sorting,
        "path_shape_vector_work": None, "planned_work": None,
        "semantics": "whole_request_logical_visit_allowance_not_CPU_RSS_accuracy"}
    reasons = []
    if (lattice["status"] != "ready_native_interval_lattice" or scope["context_sound_inventory_complete"] is not True
            or prior_panel["status"] != "computed_source_evidence_panel_not_selected"):
        reasons.append("whole_saved_source_inventory_or_prior_panel_unavailable")
    if any(pair not in inventory or inventory[pair]["status"] != "ready_native_interval" for pair in pairs):
        reasons.append("requested_complete_native_interval_inventory_unavailable")
    if work > work_budget:
        reasons.append("whole_source_scan_work_budget_no_prefix")
    intervals, chosen, pools, eligible_counts, paths, partitions, requests = [], {}, {}, {}, [], [], []
    assessed = eligible_total = proposal_total = 0
    if not reasons:
        guards = {s["sound_ref"]: bool(kernels._source_blockers(s) or temporal._guard_codes(s))
                  for s in scope["sound_facts"]}
        for pair in pairs:
            entry = inventory[pair]
            evaluated = [(*_evidence(scope, o, guards), o) for o in entry["origins"]]
            eligible = sorted((row for row in evaluated if row[0]["eligible"]), key=lambda row: row[1])
            primary = eligible[0] if eligible else None
            competitor = next((r for r in eligible if r[2] != primary[2]), None) if primary else None
            chosen[pair] = [r[0] for r in (primary, competitor) if r is not None]
            groups = {}
            for row in eligible:
                groups.setdefault(_bucket(row[3]), []).append(row)
            representatives = [*chosen[pair]]
            for bucket in sorted(groups, key=lambda b: digest(_bucket_json(b))):
                body = groups[bucket][0][0]
                if body not in representatives:
                    representatives.append(body)
            pools[pair] = representatives
            eligible_counts[pair] = len(eligible)
            assessed += len(evaluated)
            eligible_total += len(eligible)
            proposal_total += len(representatives)
            intervals.append({"catalog_id": entry["catalog_id"], "point_indices": list(pair), "span": deepcopy(entry["span"]),
                "native_origins": len(evaluated), "eligible_origins": len(eligible),
                "rejected_origins": len(evaluated) - len(eligible),
                "rejection_reason_occurrences": dict(Counter(reason for r in evaluated if not r[0]["eligible"] for reason in r[0]["reasons"])),
                "distinct_eligible_spelling_signatures": len({r[2] for r in eligible}),
                "bucket_representatives": [{"bucket": _bucket_json(b), "eligible_origins": len(rows),
                    "representative_ref": rows[0][0]["origin_ref"],
                    "distinct_ordered_signatures": len({digest([r[3]["root"], r[3]["members"]]) for r in rows}),
                    "omitted_bucket_representative_origins": len(rows) - 1} for b, rows in groups.items()],
                "proposals": representatives, "proposal_count": len(representatives),
                "omitted_eligible_origins": len(eligible) - len(representatives)})
        old_paths, expected_controls = _controls(chosen, specs, keys)
        if (controls != expected_controls or prior_panel["complete_proposal_paths"] != old_paths
                or [(r["point_indices"], r["proposals"]) for r in prior_panel["intervals"]]
                != [(list(pair), chosen[pair]) for pair in pairs]):
            raise ValueError("exact_prior_source_proposals_and_ordered_controls_required")
        path_reserve = sum((1 + sum(len(pools[pair]) for pair in zip(indices, indices[1:])))
            * len(seed["origin_ids"]) * 24
            for name, indices in specs if indices is not None
            for seed in old_paths if seed["partition_kind"] == name)
        plan["path_shape_vector_work"] = path_reserve
        if work + path_reserve > work_budget:
            reasons.append("whole_mixed_path_construction_work_budget_no_prefix")
        # All one-slot substitutions are enumerated; not arbitrary best-first truncation.
        for name, indices in ([] if reasons else specs):
            row = {"partition_kind": name, "point_indices": indices, "proposed_paths": 0,
                "eligible_cartesian_origin_paths": 0, "omitted_eligible_cartesian_origin_paths": 0,
                "status": "unavailable_structural_partition" if indices is None else "known_no_complete_evaluable_path"}
            if indices is not None:
                slot_pairs = list(zip(indices, indices[1:]))
                row["eligible_cartesian_origin_paths"] = prod(eligible_counts[pair] for pair in slot_pairs)
                if all(pools[pair] for pair in slot_pairs):
                    proposed = {}
                    for seed in (p for p in old_paths if p["partition_kind"] == name):
                        proposed.setdefault(tuple(seed["origin_ids"]), []).append({"kind": "retained_seed", "proposal_lane": seed["proposal_lane"]})
                        for slot, pair in enumerate(slot_pairs):
                            for body in pools[pair]:
                                ids = list(seed["origin_ids"])
                                ids[slot] = body["origin_ref"]["record_id"]
                                proposed.setdefault(tuple(ids), []).append({"kind": "single_slot_substitution", "proposal_lane": seed["proposal_lane"], "slot": slot})
                    for ids, provenance in proposed.items():
                        paths.append({"partition_kind": name, "point_indices": indices,
                            "origin_ids": list(ids), "origin_refs": [kernels._ref(origins[i]) for i in ids],
                            "proposal_provenance": provenance})
                    row.update(proposed_paths=len(proposed), status="computed_bounded_mixed_path_sample")
                row["omitted_eligible_cartesian_origin_paths"] = row["eligible_cartesian_origin_paths"] - row["proposed_paths"]
            partitions.append(row)
        # Conservative reservation precedes family/quality calls and vector materialization.
        shape_reserve = sum((len(p["origin_ids"]) - 1) * len(keys) * len(kernels.FAMILIES) * 2
            * (32 + sum(_nodes(origins[i]) for i in p["origin_ids"]) + max(_nodes(k) for k in keys)) for p in paths)
        plan["path_shape_vector_work"] += shape_reserve
        if len(paths) > max_paths:
            reasons.append("whole_mixed_path_budget_no_prefix")
        if work + plan["path_shape_vector_work"] > work_budget:
            reasons.append("whole_path_shape_work_budget_no_prefix")
        if not reasons:
            vector_count = 0
            for path in paths:
                selected = [origins[i] for i in path["origin_ids"]]
                for key in keys:
                    cuts = []
                    for left, right in zip(selected, selected[1:]):
                        checked, compatible = [], []
                        for family in kernels.FAMILIES:
                            for quality in ("M", "m"):
                                shape = kernels._function(scope, left, right, key["segments"][0], family, quality)
                                compatible_shape = shape["shape_compatible"] is True and shape["target_shape_compatible"] is True
                                checked.append({"assumption": {"family": family, "quality": quality},
                                    "source_shape_compatible": shape["shape_compatible"],
                                    "target_shape_compatible": shape["target_shape_compatible"],
                                    "shape_request_eligible": compatible_shape, "function_kind_under_key": shape["function_kind"],
                                    "key_projection": deepcopy(shape["key_projection"]), "blockers": shape["blockers"]})
                                if compatible_shape:
                                    compatible.append({"family": family, "quality": quality})
                        cuts.append({"source_origin_ref": kernels._ref(left), "target_origin_ref": kernels._ref(right),
                            "same_spelling_signature": prior._signature(left) == prior._signature(right),
                            "checked_shapes": checked, "request_options": [None, *compatible],
                            "resolution_support": None, "secondary_support": None,
                            "boundary_support": None, "same_completion_ref": None})
                    count = prod(len(c["request_options"]) for c in cuts)
                    vector_count += count
                    requests.append({"path_index": len(requests) // len(keys), "key_ref": kernels._ref(key),
                        "cuts": cuts, "complete_vector_count": count})
            # All vectors are known before building any selector list.
            vector_work = vector_count * (32 + max((len(p["origin_ids"]) for p in paths), default=0))
            plan["path_shape_vector_work"] += vector_work
            plan["planned_work"] = work + plan["path_shape_vector_work"]
            if vector_count + len(controls) > max_selectors:
                reasons.append("whole_selector_upper_bound_budget_no_prefix")
            if plan["planned_work"] > work_budget:
                reasons.append("whole_vector_materialization_work_budget_no_prefix")
    additional, aliases = [], []
    if not reasons:
        seen = {digest(selector): {"kind": "retained_control", "index": i} for i, selector in enumerate(controls)}
        for request_index, request in enumerate(requests):
            path = paths[request["path_index"]]
            for vector in product(*(c["request_options"] for c in request["cuts"])):
                selector = {"origin_ids": deepcopy(path["origin_ids"]), "key_id": request["key_ref"]["record_id"],
                    "transition_assumptions": deepcopy(list(vector))}
                fingerprint = digest(selector)
                if fingerprint in seen:
                    aliases.append({"request_index": request_index, "selector_fingerprint": fingerprint,
                        "existing_selector": deepcopy(seen[fingerprint])})
                else:
                    seen[fingerprint] = {"kind": "additional", "index": len(additional)}
                    additional.append(selector)
    if reasons:
        intervals, paths, partitions, requests, aliases = [], [], [], [], []
    cartesian = None if reasons else sum(r["eligible_cartesian_origin_paths"] or 0 for r in partitions)
    summary = {"requested_intervals": len(pairs), "assessed_origin_occurrences": None if reasons else assessed,
        "eligible_origin_occurrences": None if reasons else eligible_total,
        "rejected_origin_occurrences": None if reasons else assessed - eligible_total,
        "proposal_origin_occurrences": None if reasons else proposal_total,
        "omitted_eligible_origin_occurrences": None if reasons else eligible_total - proposal_total,
        "complete_proposal_paths": None if reasons else len(paths), "eligible_cartesian_origin_paths": cartesian,
        "omitted_eligible_cartesian_origin_paths": None if reasons else cartesian - len(paths),
        "retained_control_selectors": len(controls), "additional_selectors": None if reasons else len(additional),
        "total_selectors": None if reasons else len(controls) + len(additional),
        "shape_request_occurrences": None if reasons else sum(len(c["request_options"]) - 1 for r in requests for c in r["cuts"])}
    if source_digest != digest([scope, lattice, prior_panel]) or contract != _contract():
        raise ValueError("saved_proposal_sources_or_current_contract_changed_during_call")
    return kernels._seal({"version": VERSION, "source_authority": AUTHORITY, "contract": contract, "rules": RULES,
        "scope_ref": kernels._ref(scope), "lattice_ref": kernels._ref(lattice), "prior_panel_ref": kernels._ref(prior_panel),
        "binding": deepcopy(scope["binding"]), "analysis_span": deepcopy(scope["analysis_span"]),
        "logical_universe": deepcopy(lattice["universe"]), "resource_limits": limits, "query_plan": plan,
        "intervals": intervals, "partitions": partitions, "complete_proposal_paths": paths,
        "shape_request_groups": requests, "selector_aliases": aliases,
        "retained_control_selectors": controls, "additional_selectors": additional,
        "selectors": controls + additional, "summary": summary,
        "status": "whole_source_proposal_hold" if reasons else "computed_source_progression_proposals_not_evaluated",
        "reasons": sorted(set(reasons)), "flags": deepcopy(FLAGS), "selected": None, "rank": None, "confidence": None,
        "native_replay_status": "not_executed_requires_fresh_native_session",
        "limitations": ["Saved content seals are not authenticated live native/session authority.",
            "Ordinary buckets retain one representative per quality and spelled root, not every supplier reading.",
            "Old seeds plus single-slot substitutions omit multi-slot combinations; Cartesian counts remain separate.",
            "Pooled note-time and member coverage do not confirm arpeggios, omissions, NCTs or harmony.",
            "A dominant-shaped request may also describe a home triad; shape is not secondary-function proof.",
            "Shape-only requests have no same-completion motion, cadence or boundary support.",
            "Held records retain controls but do not schedule a partial new native evaluation."]}, PREFIX)
