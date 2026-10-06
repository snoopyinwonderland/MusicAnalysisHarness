"""Exact, label-blind continuity factors, without a global path enumeration.

Each interior release/attack is a complete bipartite partial injective map.
Leaving every endpoint unconnected is always possible.  Counts describe the
geometry hypothesis universe, not confidence, observed voices, NCT or harmony.
"""
from collections import defaultdict
from copy import deepcopy
import json
from math import comb, factorial

from .harmony_path_contrast import token
from .harmony_voice_paths import partition
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "factorized-voice-paths-0.1.0"
COUNT_SEMANTICS = "exact_number_of_partial_injective_geometry_assignments_not_confidence"


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("invalid_nonnegative_integer:" + name)
    return value


def _decimal(value):
    """Arbitrary precision decimal, without altering Python's global limits."""
    if value == 0:
        return "0"
    chunks = []
    while value:
        value, tail = divmod(value, 10 ** 9)
        chunks.append(tail)
    return str(chunks[-1]) + "".join(f"{piece:09d}" for piece in reversed(chunks[:-1]))


def _matching_count(m, n):
    # No choices or global assignments are materialized by this formula.
    return sum(comb(m, k) * comb(n, k) * factorial(k)
               for k in range(min(m, n) + 1))


def _seal(body, prefix):
    body = deepcopy(body)
    sha = digest(body)
    return {**body, "record_id": prefix + sha[:24], "record_sha256": sha}


def _check_seal(record, prefix):
    body = {key: value for key, value in record.items()
            if key not in ("record_id", "record_sha256")}
    sha = digest(body)
    if record.get("record_sha256") != sha or record.get("record_id") != prefix + sha[:24]:
        raise ValueError("invalid_record_seal")
    return body


def _lane(lane):
    if not isinstance(lane, (list, tuple)) or len(lane) != 2 or any(
            not isinstance(item, str) or not item for item in lane):
        raise ValueError("explicit_raw_part_voice_lane_required")
    return list(lane)


def _index(rows, key):
    index = {}
    for row in rows:
        ref = row.get(key)
        if not isinstance(ref, str) or not ref or ref in index:
            raise ValueError("missing_or_duplicate_id:" + key)
        index[ref] = row
    return index


def _bounds(sound):
    a, b = f(sound["span"]["start"]), f(sound["span"]["end"])
    if a < 0 or b < a:
        raise ValueError("invalid_sound_geometry")
    return a, b


def _in_context(sound, bounds):
    a, b = _bounds(sound)
    return bounds[0] <= a < bounds[1] if a == b else a < bounds[1] and b > bounds[0]


def _contract():
    return {"count_semantics": COUNT_SEMANTICS, "counts_are_confidence": False,
            "selected_assignment": None, "preferred_assignment": None,
            "used_for_ranking": False, "voice_identity_confirmed": False,
            "harmonic_labels_used": False, "source_annotations_used": False,
            "production_enabled": False, "global_product_enumerated": False,
            "all_no_link_alternatives_retained": True,
            "limits": ["Only positive sounding events in one explicit raw part/voice are endpoints.",
                       "Exact release=attack strictly inside the original context; no gap bridging.",
                       "No pitch-based pruning, branch, merge, reassignment of held notes or cross-lane link.",
                       "Continuity hypotheses do not establish contrapuntal voice identity or musical roles.",
                       "Fresh IR validation is required to establish original input binding; a seal is not authority."]}


def _body(binding, span, lane, context, notes_rows, source_rows, ties, caps):
    """Rebuild geometry from stored literal snapshots, never stored counts."""
    bounds = span_bounds(span)
    lane = _lane(lane)
    notes = _index(notes_rows, "note_id")
    sources = _index(source_rows, "source_ref_id")
    tie_index = _index(ties, "tie_chain_id")
    file_index = _index(binding["source_files"], "source_file_id")
    sounds = _index(context, "sounding_event_id")
    if any(not _in_context(s, bounds) for s in context):
        raise ValueError("context_snapshot_contains_noncontext_sound")
    for key in ("max_events", "max_factors", "max_edges"):
        _integer(caps[key], key)
    events, points, unknown = [], [], []
    sampled_points, other_points, grace_refs = [], [], []
    missing_notes, missing_sources, missing_ties = set(), set(), set()
    attack_mismatches, tie_mismatches = [], []
    reasons = []
    for sound in context:
        sid = sound["sounding_event_id"]
        a, b = _bounds(sound)
        ids = sound.get("source_note_ids", [])
        if not isinstance(ids, list) or any(not isinstance(n, str) or not n for n in ids):
            raise ValueError("malformed_source_note_ids")
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate_source_note_id")
        ns = [notes.get(n) for n in ids]
        missing_notes.update(n for n in ids if n not in notes)
        keys = {(n.get("part_id"), n.get("voice_id")) for n in ns if n is not None}
        located = bool(ns) and all(n is not None for n in ns) and len(keys) == 1
        if located:
            key = next(iter(keys))
            located = all(isinstance(value, str) and value for value in key)
        if not located:
            unknown.append(sid)
        selected = located and list(key) == lane
        if a == b:
            points.append(sid)
            if selected:
                sampled_points.append(sid)
            elif located:
                other_points.append(sid)
        elif selected:
            events.append(sound)
        if selected:
            if any(n.get("grace", {}).get("is_grace", False) for n in ns):
                grace_refs.append(sid)
            for n in ns:
                source = n.get("source_ref_id")
                if source not in sources or sources[source].get("source_file_id") not in file_index:
                    missing_sources.add(n["note_id"])
            attack = sound.get("attack_note_id")
            if not isinstance(attack, str) or attack not in ids or attack not in notes:
                attack_mismatches.append(sid)
            tid = sound.get("tie_chain_id")
            if tid is not None:
                if not isinstance(tid, str) or not tid:
                    raise ValueError("malformed_tie_chain_reference")
                if tid not in tie_index:
                    missing_ties.add(tid)
                else:
                    chain = tie_index[tid]
                    if chain.get("source_note_ids") != ids or chain.get("span") != sound["span"]:
                        tie_mismatches.append(sid)
    events.sort(key=lambda s: (f(s["span"]["start"]), s["sounding_event_id"]))
    if unknown:
        reasons.append("unlocated_context_sounds_no_silent_exclusion")
    if not events:
        reasons.append("empty_lane")
    if sampled_points:
        reasons.append("sampled_lane_point_timing_not_supported")
    if grace_refs:
        reasons.append("sampled_lane_grace_timing_not_supported")
    if missing_sources:
        reasons.append("sampled_source_traceability_missing")
    if missing_ties:
        reasons.append("sampled_tie_chain_reference_missing")
    if attack_mismatches:
        reasons.append("sampled_attack_source_lineage_invalid")
    if tie_mismatches:
        reasons.append("sampled_tie_source_lineage_invalid")
    if len(events) > caps["max_events"]:
        reasons.append("max_events_exceeded_no_pruning")
    starts, ends = defaultdict(list), defaultdict(list)
    for sound in events:
        starts[f(sound["span"]["start"])].append(sound["sounding_event_id"])
        ends[f(sound["span"]["end"])].append(sound["sounding_event_id"])
    factors = []
    for t in sorted(set(starts).intersection(ends)):
        if not bounds[0] < t < bounds[1]:
            continue
        left, right = sorted(ends[t]), sorted(starts[t])
        held = sorted(s["sounding_event_id"] for s in events
                      if f(s["span"]["start"]) < t < f(s["span"]["end"]))
        fid = "vfactor_" + token([lane, q(t), left, right])
        factors.append({"factor_id": fid, "time": q(t), "source_refs": left,
                        "target_refs": right, "held_refs": held,
                        "edge_representation": "complete_bipartite_endpoint_product",
                        "legal_edge_count": len(left) * len(right),
                        "possible_assignments": None, "counts_are_confidence": False})
    if len(factors) > caps["max_factors"]:
        reasons.append("max_factors_exceeded_no_pruning")
    edge_count = sum(row["legal_edge_count"] for row in factors)
    if edge_count > caps["max_edges"]:
        reasons.append("max_edges_exceeded_no_pruning")
    possible = None
    if not reasons:
        count = 1
        for row in factors:
            n = _matching_count(len(row["source_refs"]), len(row["target_refs"]))
            row["possible_assignments"] = _decimal(n)
            count *= n
        possible = _decimal(count)
    note_time = sum((min(bounds[1], f(s["span"]["end"]))
                     - max(bounds[0], f(s["span"]["start"])) for s in events), f(q(0)))
    return {"version": VERSION, "status": "abstention" if reasons else "ready",
            "binding": deepcopy(binding), "span": deepcopy(span), "lane": lane,
            "resource_limits": deepcopy(caps), "reasons": sorted(set(reasons)),
            "events": deepcopy(events), "context_sounding_events": deepcopy(context),
            "source_note_events": deepcopy(notes_rows), "source_references": deepcopy(source_rows),
            "tie_chains": deepcopy(ties), "unlocated_sound_refs": sorted(unknown),
            "unlocated_sounding_events": deepcopy([sounds[s] for s in sorted(unknown)]),
            "point_sound_refs": sorted(points),
            "point_sounding_events": deepcopy([sounds[s] for s in sorted(points)]),
            "sampled_lane_point_sound_refs": sorted(sampled_points),
            "other_lane_point_sound_refs": sorted(other_points),
            "point_policy": "preserve_all_context_points; sampled_or_unlocated_points_abstain; known_other_lane_points_metadata_only",
            "missing_source_note_refs": sorted(missing_notes),
            "missing_source_reference_note_refs": sorted(missing_sources),
            "missing_tie_chain_refs": sorted(missing_ties),
            "attack_lineage_mismatch_sound_refs": sorted(attack_mismatches),
            "tie_lineage_mismatch_sound_refs": sorted(tie_mismatches),
            "sampled_lane_grace_sound_refs": sorted(grace_refs), "factors": factors,
            "legal_edge_count": edge_count, "possible_assignments": possible,
            "count_representation": "nonnegative_decimal_string_or_null_if_unavailable",
            "total_observed_note_time": q(note_time), **_contract()}


def factorize(ir, span, lane, *, max_events=4096, max_factors=4096, max_edges=65536):
    """Preserve an exact bound literal graph; never enumerate global paths."""
    bounds = span_bounds(span)
    lane = _lane(lane)
    notes = _index(ir["note_events"], "note_id")
    _index(ir["sounding_events"], "sounding_event_id")
    sources = _index(ir["source_references"], "source_ref_id")
    _index(ir["source_files"], "source_file_id")
    ties = _index(ir["tie_chains"], "tie_chain_id")
    if not ir.get("ir_document_id") or not ir["score"].get("score_id") or not ir["source_files"]:
        raise ValueError("IR_document_score_source_binding_required")
    context = sorted((s for s in ir["sounding_events"] if _in_context(s, bounds)),
                     key=lambda s: (f(s["span"]["start"]), s["sounding_event_id"]))
    note_ids = {n for s in context for n in s.get("source_note_ids", [])}
    chosen_ties = [ties[tid] for tid in sorted({s.get("tie_chain_id") for s in context
                  if s.get("tie_chain_id") is not None}) if tid in ties]
    note_ids.update(n for row in chosen_ties for n in row.get("source_note_ids", []))
    rows = [notes[n] for n in sorted(note_ids) if n in notes]
    refs = {n.get("source_ref_id") for n in rows}
    source_rows = [sources[ref] for ref in sorted(refs - {None}) if ref in sources]
    binding = {"ir_document_id": ir["ir_document_id"], "score_id": ir["score"]["score_id"],
               "source_file_id": ir["score"].get("source_file_id"),
               "source_files": deepcopy(ir["source_files"]), "ir_content_sha256": digest(ir)}
    body = _body(binding, span, lane, context, rows, source_rows, chosen_ties,
                 {"max_events": max_events, "max_factors": max_factors, "max_edges": max_edges})
    return _seal(body, "vfgraph_")


def _graph(record):
    body = _check_seal(record, "vfgraph_")
    rebuilt = _body(body["binding"], body["span"], body["lane"],
                    body["context_sounding_events"], body["source_note_events"],
                    body["source_references"], body["tie_chains"], body["resource_limits"])
    if body != rebuilt:
        raise ValueError("stored_graph_geometry_or_contract_mismatch")
    return body


def validate_graph(record, *, ir, span, lane):
    """Fresh literal extraction, complete content binding and exact replay."""
    _graph(record)
    fresh = factorize(ir, span, lane, **record["resource_limits"])
    if record != fresh:
        raise ValueError("stale_or_foreign_factor_graph")
    return True


class _BudgetExceeded(Exception):
    pass


def _spend(work, kind):
    if work["state_visits"] + work["transition_attempts"] >= work["budget"]:
        raise _BudgetExceeded()
    work[kind] += 1


def _constrained_count(left, right, forbidden, work):
    """Count all partial matchings by bitmask over the smaller residual side."""
    if not forbidden:
        return _matching_count(len(left), len(right)), "closed_form_complete_bipartite"
    # Reverse direction only for DP indexing; stored edges remain source->target.
    reverse = len(left) < len(right)
    rows, cols = (right, left) if reverse else (left, right)
    allowed = []
    for row in rows:
        allowed.append([index for index, col in enumerate(cols)
                        if ((col, row) if reverse else (row, col)) not in forbidden])
    dp = {0: 1}
    for indices in allowed:
        following = defaultdict(int)
        for mask, multiplicity in sorted(dp.items()):
            _spend(work, "state_visits")
            _spend(work, "transition_attempts")
            following[mask] += multiplicity  # row left unmatched
            for index in indices:
                bit = 1 << index
                if mask & bit:
                    continue
                _spend(work, "transition_attempts")
                following[mask | bit] += multiplicity
        dp = following
    return sum(dp.values()), "exact_small_side_bitmask_partial_matching_DP"


def _constraints(rows, name, events, owner, graph):
    if not isinstance(rows, (list, tuple)):
        return [], [name + ":malformed_constraint_collection"]
    normalized, reasons = set(), []
    for index, pair in enumerate(rows):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2 or any(
                not isinstance(item, str) or not item for item in pair):
            reasons.append(name + f":malformed_edge:{index}")
            continue
        pair = tuple(pair)
        if not set(pair).issubset(events):
            reasons.append(name + f":dangling_or_nonsampled_event:{index}")
        elif pair[0] not in owner or pair[1] not in graph["factors"][owner[pair[0]]]["target_refs"]:
            reasons.append(name + f":not_an_admissible_interior_endpoint_edge:{index}")
        else:
            normalized.add(pair)
    return sorted(normalized, key=lambda p: (f(graph["factors"][owner[p[0]]]["time"]), *p)), reasons


def query(record, *, required_links=(), forbidden_links=(), work_budget=100000):
    """Exact direct-edge count, not a transitive same-track test or verdict."""
    graph = _graph(record)
    _integer(work_budget, "work_budget")
    events = {s["sounding_event_id"] for s in graph["events"]}
    owner = {sid: index for index, row in enumerate(graph["factors"]) for sid in row["source_refs"]}
    required, bad_required = _constraints(required_links, "required", events, owner, graph)
    forbidden, bad_forbidden = _constraints(forbidden_links, "forbidden", events, owner, graph)
    work = {"budget": work_budget, "state_visits": 0, "transition_attempts": 0,
            "semantics": "each_DP_state_visit_and_each_allowed_transition_attempt_consumes_one_unit"}
    request = {"required_links": [list(p) for p in required],
               "forbidden_links": [list(p) for p in forbidden], "work_budget": work_budget,
               "original_required_links": json.loads(json.dumps(required_links)),
               "original_forbidden_links": json.loads(json.dumps(forbidden_links)),
               "duplicate_constraint_policy": "canonical_set_no_double_removal"}
    body = {"version": VERSION, "graph_ref": {"record_id": record["record_id"], "record_sha256": record["record_sha256"]},
            "binding": deepcopy(graph["binding"]), "span": deepcopy(graph["span"]), "lane": list(graph["lane"]),
            "request": request, "status": "exact_count", "reasons": [],
            "constraint_semantics": "direct_endpoint_edges_not_transitive_same_track",
            "possible_assignments": None, "count_representation": graph["count_representation"],
            "factor_results": [], "work": work, "witness": None, **_contract()}
    if bad_required or bad_forbidden:
        body.update(status="invalid_constraints", reasons=sorted(set(bad_required + bad_forbidden)))
    elif graph["status"] != "ready":
        body.update(status="abstention", reasons=["graph_not_ready_no_count_query", *graph["reasons"]])
    else:
        source_degree, target_degree = defaultdict(int), defaultdict(int)
        for src, dst in required:
            source_degree[src] += 1
            target_degree[dst] += 1
        conflicts = []
        if set(required).intersection(forbidden):
            conflicts.append("required_and_forbidden_same_edge")
        if any(value > 1 for value in source_degree.values()):
            conflicts.append("required_branch_not_allowed")
        if any(value > 1 for value in target_degree.values()):
            conflicts.append("required_merge_not_allowed")
        if conflicts:
            body.update(status="unsatisfiable_constraints", reasons=conflicts, possible_assignments="0")
        else:
            count = 1
            try:
                for index, factor in enumerate(graph["factors"]):
                    req = [p for p in required if owner[p[0]] == index]
                    fs = [p for p in forbidden if owner[p[0]] == index]
                    fixed_sources, fixed_targets = {p[0] for p in req}, {p[1] for p in req}
                    left = [sid for sid in factor["source_refs"] if sid not in fixed_sources]
                    right = [sid for sid in factor["target_refs"] if sid not in fixed_targets]
                    effective = {p for p in fs if p[0] in left and p[1] in right}
                    n, method = _constrained_count(left, right, effective, work)
                    count *= n
                    body["factor_results"].append({"factor_ref": factor["factor_id"],
                        "required_links": [list(p) for p in req], "forbidden_links": [list(p) for p in fs],
                        "effective_forbidden_links": [list(p) for p in sorted(effective)],
                        "residual_source_refs": left, "residual_target_refs": right,
                        "possible_assignments": _decimal(n), "count_method": method})
                body["possible_assignments"] = _decimal(count)
                body["witness"] = {"links": [list(p) for p in required],
                    "kind": "query_local_required_only_sparse_completion_not_preferred",
                    "selected": False, "all_unrequired_edges_left_unconnected": True,
                    "may_be_combined_with_other_query_witnesses": False}
            except _BudgetExceeded:
                body.update(status="abstention", reasons=["DP_work_budget_exceeded_no_partial_count"],
                            possible_assignments=None, witness=None)
    return _seal(body, "vfquery_")


def validate_query(record, result, *, required_links=(), forbidden_links=(), work_budget=100000):
    """Check graph invariants, query binding, seal, request and fresh DP replay."""
    _check_seal(result, "vfquery_")
    fresh = query(record, required_links=required_links, forbidden_links=forbidden_links, work_budget=work_budget)
    if fresh != result:
        raise ValueError("stale_foreign_or_modified_factor_query")
    return True


def materialize_witness(record, result):
    """One exact query-local completion, not a global inventory addition."""
    _check_seal(result, "vfquery_")
    request = result["request"]
    validate_query(record, result, required_links=request["original_required_links"],
                   forbidden_links=request["original_forbidden_links"], work_budget=request["work_budget"])
    if result["status"] != "exact_count" or not result["witness"]:
        raise ValueError("no_exact_query_witness_available")
    links = deepcopy(result["witness"]["links"])
    tracks = partition(record["events"], links)
    completion = "vfcompletion_" + digest([record["record_sha256"], result["record_sha256"], links])[:24]
    assignment = {"assignment_id": completion, "completion_id": completion,
                  "legacy_geometry_id": "vpaths_" + token([record["lane"], record["span"], links]),
                  "reference_semantics": "query_bound_completion; legacy_geometry_id_is_not_an_inventory_ref",
                  "links": links, "tracks": tracks, "local_choice_indices": None,
                  "local_choice_representation": "not_materialized_factor_constraint_completion",
                  "all_events_used_once": True, "note_time_preserved": True, "selected": False}
    return _seal({"version": VERSION, "status": "query_local_completion_not_preferred",
        "graph_ref": {key: record[key] for key in ("record_id", "record_sha256")},
        "query_ref": {key: result[key] for key in ("record_id", "record_sha256")},
        "binding": deepcopy(record["binding"]), "span": deepcopy(record["span"]), "lane": list(record["lane"]),
        "assignment": assignment, "total_observed_note_time": deepcopy(record["total_observed_note_time"]),
        "existing_assignment_inventory_inserted": False,
        "legacy_assignment_inventory_membership": "not_checked_not_claimed",
        "may_be_combined_with_other_query_witnesses": False, **_contract()}, "vfwitness_")
