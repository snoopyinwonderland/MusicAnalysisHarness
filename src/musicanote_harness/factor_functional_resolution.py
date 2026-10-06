"""Actual written motion under explicit functional and voice hypotheses.

Every joint branch has one query/completion per declared raw lane.  Neither
observed motion nor a geometric completion certifies a chord, key or cadence.
No source annotations or legacy assignment producers are consulted here.
"""
from collections import defaultdict, OrderedDict
from copy import deepcopy
from fractions import Fraction
from itertools import product
import math
import json
from hashlib import sha256
from pathlib import Path
from dataclasses import dataclass
from weakref import WeakKeyDictionary
import hmac
import secrets

from . import factor_musical_view as common
from . import factor_musical_rules as nct
from . import harmony_factorized_voice_paths as factors
from .musical_pattern_observation import digest

VERSION = "factor-functional-resolution-0.1.0"
LETTERS = "CDEFGAB"
NATURAL = dict(zip(LETTERS, (0, 2, 4, 5, 7, 9, 11)))
_COMPILATION_CACHE = OrderedDict()
_COMPILATION_CACHE_LIMIT = 512
_COMPILATION_CACHE_BYTE_LIMIT = 64 * 1024 * 1024
_COMPILATION_CACHE_BYTES = 0
_PREPARED_BUNDLES = WeakKeyDictionary()
_PREPARED_SECRET = secrets.token_bytes(32)


class _PreparedBundle:
    """Opaque handle; possession alone does not establish internal registration."""
    __slots__ = ("__weakref__",)


@dataclass(frozen=True)
class _PreparedBundleState:
    payload: bytes
    payload_sha256: str
    contract: tuple
    authentication: bytes


def _encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode()


def _seal_owned(body, prefix):
    """Seal private freshly-owned output without cloning it a second time.

    Call sites copy every caller-derived snapshot when constructing the body;
    their intermediate producer results are not exposed to the caller. This
    is not a public seal accepting untrusted bodies or asserted checksums.
    The canonical bytes and identifiers are exactly common.seal's contract.
    """
    checksum = digest(body)
    return {**body, "record_id": prefix + checksum[:24], "record_sha256": checksum}


def _prepared_authentication(handle, checksum, contract):
    # Private state-integrity check, not a security boundary against code
    # executing inside this Python module or access to the module secret.
    stamp = [*contract[:3], sha256(contract[3]).hexdigest(), contract[4]]
    return hmac.digest(_PREPARED_SECRET, _encoded([id(handle), checksum, stamp]), "sha256")


def _prepared_state(handle):
    if type(handle) is not _PreparedBundle or handle not in _PREPARED_BUNDLES:
        raise ValueError("internally_issued_prepared_bundle_required")
    state = _PREPARED_BUNDLES[handle]
    contract = _cache_contract()
    if (type(state) is not _PreparedBundleState or state.contract != contract or
            not hmac.compare_digest(state.authentication,
                                    _prepared_authentication(handle, state.payload_sha256, contract))):
        raise ValueError("prepared_bundle_contract_or_internal_state_changed")
    if type(state.payload) is not bytes or sha256(state.payload).hexdigest() != state.payload_sha256:
        raise ValueError("prepared_bundle_internal_content_changed")
    return state


def _flags():
    return {"selected": None, "preferred": None, "counts_are_confidence": False,
            "source_annotations_used": False, "production_modified": False,
            "harmony_confirmed": False, "key_confirmed": False,
            "function_confirmed": False, "resolution_confirmed": False,
            "cadence_confirmed": False, "musical_accuracy_measured": False,
            "training_eligible": False, "gold_eligible": False,
            "generation_ready": False, "legacy_assignment_inventory_inserted": False}


def _budget(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("invalid_nonnegative_budget:" + name)


def _paths(view, paths):
    rows = [paths] if isinstance(paths, dict) else list(paths)
    if not rows:
        raise ValueError("explicit_complete_harmony_path_registry_required")
    ids = set()
    for path in rows:
        common.validate_path(view, path)
        if path["record_id"] in ids:
            raise ValueError("duplicate_complete_harmony_path")
        ids.add(path["record_id"])
    return sorted(rows, key=lambda r: r["record_id"])


def _graphs(view, path, graphs):
    if not isinstance(graphs, (list, tuple)):
        raise ValueError("explicit_graph_inventory_required")
    indexed, lanes, endpoints = {}, set(), set()
    for graph in graphs:
        body, _ = nct._guards(view, path, graph)
        lane = tuple(body["lane"])
        ids = {s["sounding_event_id"] for s in body["events"]}
        if graph["record_id"] in indexed or lane in lanes:
            raise ValueError("duplicate_graph_or_raw_lane")
        if ids & endpoints:
            raise ValueError("graph_endpoints_not_disjoint")
        indexed[graph["record_id"]] = graph
        lanes.add(lane)
        endpoints.update(ids)
    return indexed


def make_bundle(view, paths, entries):
    """Seal exact per-lane completions and an explicit comparison-path registry."""
    before = digest([view, paths, entries])
    common.validate_view(view)
    registry = _paths(view, paths)
    if not isinstance(entries, (list, tuple)):
        raise ValueError("explicit_completion_entry_list_required")
    graphs = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"graph", "query", "witness"}:
            raise ValueError("exact_graph_query_witness_entry_required")
        graphs.append(entry["graph"])
    _graphs(view, registry[0], graphs)
    rows = []
    for entry in entries:
        graph, query, witness = (entry[k] for k in ("graph", "query", "witness"))
        request = query["request"]
        factors.validate_query(graph, query, required_links=request["original_required_links"],
                               forbidden_links=request["original_forbidden_links"],
                               work_budget=request["work_budget"])
        if query["status"] != "exact_count" or witness != factors.materialize_witness(graph, query):
            raise ValueError("one_exact_graph_bound_completion_required")
        rows.append({**deepcopy(entry), "graph_ref": common.ref(graph),
                     "query_ref": common.ref(query), "witness_ref": common.ref(witness),
                     "lane": deepcopy(graph["lane"]),
                     "completion_id": witness["assignment"]["completion_id"]})
    rows.sort(key=lambda r: (r["lane"], r["graph_ref"]["record_id"]))
    covered = sorted(r["lane"] for r in rows)
    all_lanes = sorted([r["part_id"], r["voice_id"]] for r in view["raw_lanes"])
    missing = [lane for lane in all_lanes if lane not in covered]
    body = {"version": VERSION, "view_ref": common.ref(view),
            "binding": deepcopy(view["binding"]), "context_span": deepcopy(view["context_span"]),
            "path_refs": [common.ref(p) for p in registry], "path_registry": deepcopy(registry),
            "entries": rows, "covered_lanes": covered, "missing_lanes": missing,
            "status": "exact_completion_bundle_with_unknown_missing_lanes" if missing else "exact_completion_bundle",
            "missing_lane_semantics": "unassessed_not_false_not_an_inferred_voice",
            "witnesses_may_be_unioned": False, "possible_assignments_product": None,
            "limits": ["One completion for each declared raw lane, not a selected voice.",
                       "Different lane completions are explicit disjoint hypotheses, not a witness union.",
                       "Geometry is path-independent; every comparison path is explicitly registered."], **_flags()}
    if digest([view, paths, entries]) != before:
        raise ValueError("completion_bundle_inputs_mutated")
    return common.seal(body, "fmcmb_")


def validate_bundle(view, paths, graphs, record):
    common.check(record, "fmcmb_")
    registry = _paths(view, paths)
    inventory = _graphs(view, registry[0], graphs)
    if set(inventory) != {e["graph_ref"]["record_id"] for e in record["entries"]}:
        raise ValueError("completion_bundle_graph_inventory_mismatch")
    entries = [{k: e[k] for k in ("graph", "query", "witness")} for e in record["entries"]]
    for entry in entries:
        if entry["graph"] != inventory[entry["graph"]["record_id"]]:
            raise ValueError("completion_bundle_foreign_graph")
    if record != make_bundle(view, registry, entries):
        raise ValueError("stale_foreign_or_modified_completion_bundle")
    return True


def prepare_bundle(view, paths, graphs, bundle):
    """Freshly verify and snapshot one fixed complete comparison experiment.

    The lifecycle-bound registry owns immutable ACTUAL canonical input bytes;
    no caller hash, skip flag or caller-constructed handle authorizes reuse.
    Every public evaluator/validator still rebuilds its verification. Only the
    private assessment helper can reuse this exact verified bundle context.
    Extra declared graphs without completions retain the public evaluator's
    unknown-missing-lane semantics, and never acquire an inferred witness.
    """
    supplied = {"view": view, "paths": paths, "graphs": graphs, "bundle": bundle}
    payload = _encoded(supplied)
    fixed = json.loads(payload)
    stamp = _cache_contract()
    registry = _paths(fixed["view"], fixed["paths"])
    fixed["paths"] = registry
    validate_bundle(fixed["view"], registry,
                    [e["graph"] for e in fixed["bundle"]["entries"]], fixed["bundle"])
    inventory = _graphs(fixed["view"], registry[0], fixed["graphs"])
    if any(e["graph"] != inventory.get(e["graph_ref"]["record_id"])
           for e in fixed["bundle"]["entries"]):
        raise ValueError("resolution_bundle_graph_not_in_explicit_inventory")
    if _encoded(supplied) != payload:
        raise ValueError("prepared_bundle_caller_inputs_mutated")
    if stamp != _cache_contract():
        raise ValueError("prepared_bundle_contract_changed_during_validation")
    frozen = _encoded(fixed)
    checksum = sha256(frozen).hexdigest()
    handle = _PreparedBundle()
    _PREPARED_BUNDLES[handle] = _PreparedBundleState(
        frozen, checksum, stamp, _prepared_authentication(handle, checksum, stamp))
    _prepared_state(handle)
    return handle


def _functional(view, path, key_track, functions):
    from . import factor_functional_overlay as overlay
    overlay.validate_key_track(view, key_track)
    overlay.validate_functions(view, path, key_track, functions,
                               max_candidates=functions["max_candidates"])


def _motion(left, right):
    p, r = left["pitch"], right["pitch"]
    d = 7 * (r["octave"] - p["octave"]) + LETTERS.index(r["step"]) - LETTERS.index(p["step"])
    s = 12 * (r["octave"] - p["octave"]) + NATURAL[r["step"]] - NATURAL[p["step"]] + common.f(r["alter"]) - common.f(p["alter"])
    return {"diatonic_steps": d, "semitones": common.q(s),
            "integer_spelling_supported": common.f(p["alter"]).denominator == common.f(r["alter"]).denominator == 1}


def _source_blockers(sound):
    codes = list(sound["source_diagnostics"])
    if sound["source_clock_passed"] is not True:
        codes.append("source_clock_not_passed:" + sound["sound_id"])
    if sound["source_pitch_consistency_passed"] is not True:
        codes.append("source_written_pitch_not_passed:" + sound["sound_id"])
    if common.f(sound["pitch"]["alter"]).denominator != 1:
        codes.append("microtonal_resolution_not_supported")
    return codes


def _outgoing(graph):
    result = defaultdict(list)
    for factor in graph["factors"]:
        for source in factor["source_refs"]:
            result[source].extend(factor["target_refs"])
    return {s: sorted(set(t)) for s, t in result.items()}


def _chain_stats(source, sounds, outgoing, target_end):
    """Count every same-pitch continuation leaf before materializing any chain."""
    critical = common.pitch_key(source["pitch"], True)
    table = {}
    for sid in sorted(sounds, key=lambda x: (common.f(sounds[x]["span"]["start"]), x), reverse=True):
        sound = sounds[sid]
        if common.pitch_key(sound["pitch"], True) != critical:
            continue
        if common.f(sound["span"]["end"]) >= target_end or not outgoing.get(sid):
            table[sid] = (1, 0)
            continue
        count, depth = 0, 0
        for target in outgoing[sid]:
            child = sounds[target]
            if common.f(child["span"]["start"]) >= target_end or common.pitch_key(child["pitch"], True) != critical:
                n, d = 1, 0
            else:
                n, d = table[target]
            count += n
            depth = max(depth, 1 + d)
        table[sid] = count, depth
    return table[source["sound_id"]]


def _chains(source, sounds, outgoing, target_end):
    critical = common.pitch_key(source["pitch"], True)
    stack = [[source["sound_id"]]]
    while stack:
        ids = stack.pop()
        last = sounds[ids[-1]]
        if common.f(last["span"]["end"]) >= target_end or not outgoing.get(ids[-1]):
            yield ids
            continue
        for target in reversed(outgoing[ids[-1]]):
            child = sounds[target]
            chain = ids + [target]
            if common.f(child["span"]["start"]) >= target_end or common.pitch_key(child["pitch"], True) != critical:
                yield chain
            else:
                stack.append(chain)


def _initial_blockers(function, source, graph):
    blockers = list(function["blockers"])
    if function["status"] != "conditional_function_shape":
        blockers.append("functional_shape_prerequisites_withheld")
    if function["target_basis"] != "next_path_segment" or function["target_span"] is None:
        blockers.append("actual_following_harmony_span_missing")
    if source is None:
        blockers.append("critical_source_not_observed_in_source_span")
    else:
        blockers.extend(_source_blockers(source))
        cut = common.f(function["source_span"]["end"])
        a, b = common.span_bounds(source["span"])
        if not a < cut <= b:
            blockers.append("critical_source_not_active_at_harmonic_change_left_limit")
        ka, kb = common.span_bounds(function["key_span"])
        if not ka < cut <= kb:
            blockers.append("key_projection_not_covering_harmonic_change_left_limit")
    if graph is None:
        blockers.append("missing_raw_lane_graph")
    elif graph["status"] != "ready":
        blockers.extend(["factor_graph_not_ready", *graph["reasons"]])
    return sorted(set(blockers))


def _observation(view, path, function, role, chain, initial, source):
    ids = [s["sound_id"] for s in chain]
    links = [ids[i:i + 2] for i in range(len(ids) - 1)]
    moves = [_motion(a, b) for a, b in zip(chain, chain[1:])]
    target = chain[-1] if len(chain) > 1 else None
    same = target is None or common.pitch_key(target["pitch"], True) == common.pitch_key(source["pitch"], True)
    blockers = list(initial)
    for sound in chain:
        blockers.extend(_source_blockers(sound))
    cut = common.f(function["source_span"]["end"])
    target_span = function["target_span"]
    target_time = None if target is None else target["span"]["start"]
    onset_in_target = target_span is not None and target_time is not None and common.f(target_span["start"]) <= common.f(target_time) < common.f(target_span["end"])
    actual_member = None
    if target is not None and target_span is not None:
        segment = common.segment_at(path, common.f(target_time))
        actual_member = ("unknown" if segment is None or segment["status"] != "usable" or segment["blockers"] else
                         "member" if common.pitch_key(target["pitch"]) in {common.pitch_key(m) for m in segment["members"]} else "nonmember")
    if same:
        blockers.append("no_changed_pitch_successor_observed_within_target_span")
        expected = None
    else:
        motion = moves[-1]
        semi, degree = common.f(motion["semitones"]), motion["diatonic_steps"]
        if role == "leading_tone":
            expected = motion["integer_spelling_supported"] and semi == 1 and degree == 1 and common.pitch_key(target["pitch"]) == common.pitch_key(function["target_root"])
        else:
            expected = motion["integer_spelling_supported"] and semi in (-1, -2) and degree == -1 and common.pitch_key(target["pitch"]) in {common.pitch_key(p) for p in function["target_members"]}
        if not expected:
            blockers.append("literal_motion_not_expected_ordinary_resolution")
        if not onset_in_target:
            blockers.append("actual_destination_attack_outside_following_harmony_span")
        if actual_member != "member":
            blockers.append("actual_destination_membership_unknown" if actual_member == "unknown" else "actual_destination_not_member")
    body = {"sound_refs": ids, "note_refs": [n for s in chain for n in s["source_note_ids"]],
            "harmonic_change_time": common.q(cut),
            "source_terminal_time": None if source is None else deepcopy(source["span"]["end"]),
            "source_terminal_sound_ref": None if source is None else source["sound_id"],
            "resolution_predecessor_sound_ref": None if target is None or same else chain[-2]["sound_id"],
            "resolution_predecessor_terminal_time": None if target is None or same else deepcopy(chain[-2]["span"]["end"]),
            "target_onset": deepcopy(target_time),
            "required_links": links, "motions": moves, "source_and_destination_snapshots": deepcopy(chain),
            "same_pitch_carry_edges": [link for link, move in zip(links, moves) if move["diatonic_steps"] == 0 and common.f(move["semitones"]) == 0],
            "actual_motion_matches_expected": expected, "destination_onset_in_target_span": onset_in_target,
            "actual_destination_membership": actual_member, "blockers": sorted(set(blockers)),
            "status": "conditional_resolution_motion" if not blockers else "withheld_literal_observation",
            "literal_motion_is_not_function_or_chord_certification": True}
    return {"observation_id": "fmrobs_" + digest([common.ref(view), function["function_id"], role, body])[:24], **body}


def _compile_fresh(view, path, key_track, functions, graphs, *, max_candidates=1024, max_chain_edges=8):
    """Pre-count the entire row plus chain-observation inventory; never sample it."""
    before = digest([view, path, key_track, functions, graphs])
    _budget(max_candidates, "max_candidates")
    _budget(max_chain_edges, "max_chain_edges")
    common.validate_view(view)
    common.validate_path(view, path)
    _functional(view, path, key_track, functions)
    inventory = _graphs(view, path, graphs)
    by_lane = {tuple(g["lane"]): g for g in inventory.values()}
    sounds = {s["sound_id"]: s for s in view["sounds"]}
    specs, observation_count, max_depth = [], 0, 0
    for function in functions["rows"]:
        for role, field in (("leading_tone", "leading_tone"), ("seventh", "seventh")):
            critical = function[field]
            if critical is None:
                continue
            sources = [s for s in view["sounds"] if common.pitch_key(s["pitch"]) == common.pitch_key(critical)
                       and common.clipped(s["span"], function["source_span"]) is not None]
            for source in sorted(sources, key=lambda s: s["sound_id"]) or [None]:
                graph = None if source is None else by_lane.get(tuple(source["lane"]))
                initial = _initial_blockers(function, source, graph)
                outgoing = {} if graph is None else _outgoing(graph)
                lane_sounds = {} if graph is None else {sid: sounds[sid] for sid in (e["sounding_event_id"] for e in graph["events"])}
                eligible_geometry = source is not None and graph is not None and graph["status"] == "ready" and function["target_span"] is not None and "critical_source_not_active_at_harmonic_change_left_limit" not in initial
                if eligible_geometry:
                    n, depth = _chain_stats(source, lane_sounds, outgoing, common.f(function["target_span"]["end"]))
                else:
                    n, depth = 1, 0
                observation_count += n
                max_depth = max(max_depth, depth)
                specs.append((function, role, critical, source, graph, initial, outgoing, lane_sounds, eligible_geometry))
    cost = len(specs) + observation_count
    rules, reasons = [], []
    if functions["status"] != "ready":
        status = "functional_inventory_abstention"
        reasons = ["functional_inventory_not_complete", *functions.get("reasons", [])]
    elif max_depth > max_chain_edges:
        status = "chain_budget_abstention"
        reasons = ["whole_chain_inventory_exceeds_edge_budget_no_partial_candidates"]
    elif cost > max_candidates:
        status = "candidate_budget_abstention"
        reasons = ["whole_row_and_observation_inventory_exceeds_budget_no_pruning"]
    else:
        status = "ready"
        for function, role, critical, source, graph, initial, outgoing, lane_sounds, geometry in specs:
            chains = list(_chains(source, lane_sounds, outgoing, common.f(function["target_span"]["end"]))) if geometry else ([[]] if source is None else [[source["sound_id"]]])
            observations = [_observation(view, path, function, role, [sounds[sid] for sid in chain], initial, source) for chain in chains]
            alternatives = [{"graph_ref": common.ref(graph), "required_links": deepcopy(o["required_links"]),
                             "forbidden_links": [], "observation_ref": o["observation_id"]}
                            for o in observations if o["status"] == "conditional_resolution_motion"]
            codes = list(initial)
            if not alternatives:
                codes.append("no_supported_ordinary_resolution_alternative_observed")
            body = {"function_ref": function["function_id"], "source_segment_ref": function["source_segment_ref"],
                    "target_segment_ref": function["target_segment_ref"], "source_span": deepcopy(function["source_span"]),
                    "target_span": deepcopy(function["target_span"]), "critical_role": role, "critical_pitch": deepcopy(critical),
                    "target_pitch_assumption": deepcopy(function["target_root"] if role == "leading_tone" else function["target_members"]),
                    "source_sound_ref": None if source is None else source["sound_id"],
                    "lane": None if source is None else deepcopy(source["lane"]),
                    "graph_ref": None if graph is None else common.ref(graph),
                    "observations": observations, "alternatives": alternatives,
                    "prerequisites": {"function_snapshot": deepcopy(function),
                        "source_clock_and_pitch_snapshots": [] if source is None else [deepcopy(source)],
                        "ordinary_written_register_motion_required": True,
                        "all_same_pitch_carry_edges_required": True,
                        "target_members_are_explicit_path_assumptions_not_observed_boundary_chord": True,
                        "key": "unassessed", "function": "unassessed", "cadence": "unassessed"},
                    "blockers": sorted(set(codes)), "status": "conditional_resolution_shape" if alternatives and not codes else "withheld",
                    "observed_failure_is_not_global_resolution_failure": True, "verdict": None}
            rules.append({"resolution_id": "fmresolution_" + digest([common.ref(view), common.ref(path), common.ref(functions), body])[:24], **body})
    body = {"version": VERSION, "view_ref": common.ref(view), "path_ref": common.ref(path),
            "key_track_ref": common.ref(key_track), "functions_ref": common.ref(functions),
            "binding": deepcopy(view["binding"]), "context_span": deepcopy(view["context_span"]),
            "graph_refs": sorted([common.ref(g) for g in graphs], key=lambda r: r["record_id"]),
            "max_candidates": max_candidates, "max_chain_edges": max_chain_edges,
            "total_candidates": str(cost), "total_resolution_rows": len(specs),
            "total_chain_observations": str(observation_count), "maximum_chain_edges": max_depth,
            "candidate_budget_semantics": "rows_plus_all_literal_chain_observation_slots",
            "rules": rules, "status": status, "reasons": reasons,
            "point_observations": deepcopy(view["points"]),
            "limits": ["Actual identity/time/register motion is separate from an assumed target chord.",
                       "Accumulated members never become a boundary identity or chord certificate.",
                       "Only same-pitch delayed carries are traversed; other embellishment routes remain unsupported.",
                       "No observation or failed branch establishes universal absence or resolution failure."], **_flags()}
    if digest([view, path, key_track, functions, graphs]) != before:
        raise ValueError("resolution_compiler_inputs_mutated")
    return _seal_owned(body, "fmres_")


def _cache_contract():
    from . import factor_functional_overlay as overlay
    from . import applied_chords, seventh_context, tonal_foundations
    from . import musical_pattern_observation, sounding_lineage_audit
    from . import harmony_voice_paths, harmony_path_contrast, formal_ir, harmony_joint
    schema = common._schema_bytes()
    sources = tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest())
                    for m in (common, nct, factors, overlay, applied_chords,
                              seventh_context, tonal_foundations, musical_pattern_observation,
                              sounding_lineage_audit, harmony_voice_paths, harmony_path_contrast,
                              formal_ir, harmony_joint))
    return (VERSION, sha256(Path(__file__).read_bytes()).hexdigest(),
            sha256(schema).hexdigest(), schema, sources)


def compile_resolutions(view, path, key_track, functions, graphs, *, max_candidates=1024, max_chain_edges=8):
    """Bounded immutable pure memo, keyed by ACTUAL contents, never caller SHA.

    Only already-validated ready results are memoized. Public fresh validators
    still execute the compiler. No persistent cache, skip flag or caller-built
    prepared object is trusted. Returned mutations cannot mutate stored bytes.
    """
    global _COMPILATION_CACHE_BYTES
    _budget(max_candidates, "max_candidates")
    _budget(max_chain_edges, "max_chain_edges")
    serialized = json.dumps([view, path, key_track, functions, graphs, max_candidates, max_chain_edges],
                            sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    key = (serialized, _cache_contract())
    if key in _COMPILATION_CACHE:
        _COMPILATION_CACHE.move_to_end(key)
        payload, expected_sha, _ = _COMPILATION_CACHE[key]
        if sha256(payload).hexdigest() != expected_sha:
            raise ValueError("private_compilation_memo_payload_changed")
        return json.loads(payload)
    result = _compile_fresh(view, path, key_track, functions, graphs,
                            max_candidates=max_candidates, max_chain_edges=max_chain_edges)
    if result["status"] == "ready":
        payload = json.dumps(result, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode()
        # Bound retained serialized bytes, not an asserted process-RSS limit.
        size = len(serialized) + len(payload) + len(key[1][3])
        if size <= _COMPILATION_CACHE_BYTE_LIMIT:
            _COMPILATION_CACHE[key] = payload, sha256(payload).hexdigest(), size
            _COMPILATION_CACHE_BYTES += size
            while (len(_COMPILATION_CACHE) > _COMPILATION_CACHE_LIMIT or
                   _COMPILATION_CACHE_BYTES > _COMPILATION_CACHE_BYTE_LIMIT):
                _, old = _COMPILATION_CACHE.popitem(last=False)
                _COMPILATION_CACHE_BYTES -= old[2]
    return result


def validate_resolutions(view, path, key_track, functions, graphs, record):
    common.check(record, "fmres_")
    if record != _compile_fresh(view, path, key_track, functions, graphs,
                               max_candidates=record["max_candidates"], max_chain_edges=record["max_chain_edges"]):
        raise ValueError("stale_foreign_or_modified_resolution_inventory")
    return True


def _evaluate_resolutions(view, path, key_track, functions, graphs, bundle, *, max_candidates=1024, max_chain_edges=8,
                          _compiler=compile_resolutions):
    compiled = _compiler(view, path, key_track, functions, graphs,
                         max_candidates=max_candidates, max_chain_edges=max_chain_edges)
    validate_bundle(view, bundle["path_registry"], [e["graph"] for e in bundle["entries"]], bundle)
    if common.ref(path) not in bundle["path_refs"]:
        raise ValueError("resolution_path_not_in_completion_registry")
    supplied = {g["record_id"]: g for g in graphs}
    if any(e["graph"] != supplied.get(e["graph_ref"]["record_id"]) for e in bundle["entries"]):
        raise ValueError("resolution_bundle_graph_not_in_explicit_inventory")
    return _assessment(view, path, key_track, functions, bundle, compiled,
                       max_candidates=max_candidates, max_chain_edges=max_chain_edges)


def _assessment(view, path, key_track, functions, bundle, compiled, *, max_candidates, max_chain_edges):
    """Builder for a privately-owned fresh compiler result after full guards.

    Public/prepared entry points own this compiler result, including a fresh
    deserialization on a memo hit. Retaining its rule snapshots here avoids a
    second clone while neither inputs nor immutable stored memo bytes alias
    the returned evaluation. All public fresh replay boundaries stay intact.
    """
    available = {e["graph_ref"]["record_id"]: e for e in bundle["entries"]}
    assessments = []
    for rule in compiled["rules"]:
        entry = None if rule["graph_ref"] is None else available.get(rule["graph_ref"]["record_id"])
        blockers = list(rule["blockers"])
        if entry is None:
            blockers.append("raw_lane_completion_missing_unknown")
        matches = []
        if entry is not None:
            links = {tuple(p) for p in entry["witness"]["assignment"]["links"]}
            matches = [i for i, alt in enumerate(rule["alternatives"])
                       if {tuple(p) for p in alt["required_links"]} <= links and not {tuple(p) for p in alt["forbidden_links"]} & links]
        status = ("withheld" if rule["status"] != "conditional_resolution_shape" or blockers else
                  "conditional_resolution_under_bundle" if matches else "not_satisfied_under_this_bundle_not_global_absence")
        assessments.append({"resolution_ref": rule["resolution_id"], "function_ref": rule["function_ref"],
            "critical_role": rule["critical_role"], "source_sound_ref": rule["source_sound_ref"],
            "lane": deepcopy(rule["lane"]), "graph_ref": deepcopy(rule["graph_ref"]),
            "status": status, "matching_alternative_indices": matches,
            "satisfied_observation_refs": [rule["alternatives"][i]["observation_ref"] for i in matches],
            "blockers": sorted(set(blockers)), "rule_snapshot": rule, "selected": None})
    body = {"version": VERSION, "view_ref": common.ref(view), "path_ref": common.ref(path),
            "key_track_ref": common.ref(key_track), "functions_ref": common.ref(functions),
            "compiled_ref": common.ref(compiled), "completion_bundle_ref": common.ref(bundle),
            "binding": deepcopy(view["binding"]), "context_span": deepcopy(view["context_span"]),
            "max_candidates": max_candidates, "max_chain_edges": max_chain_edges,
            "status": "conditional_assessment_complete" if compiled["status"] == "ready" else "unassessed",
            "reasons": deepcopy(compiled["reasons"]), "assessments": assessments,
            # Every exact literal payload occurs once inside its rule snapshot;
            # these closed pointers retain the central inventory without a
            # second copy of all note/source/duration snapshots.
            "literal_motion_observation_refs": [{"resolution_ref": r["resolution_id"],
                                                 "observation_ref": o["observation_id"]}
                                                for r in compiled["rules"] for o in r["observations"]], **_flags()}
    return _seal_owned(body, "fmreval_")


def _assess_prepared(handle, path, key_track, functions, *, max_candidates=1024, max_chain_edges=8):
    """Internal exact-content reuse; per-path functional compilation stays bound.

    The returned record is identical to public evaluate_resolutions for the
    fixed inputs. NCT/resolution choices and their per-lane conditions are not
    merged. Private bytes are deserialized into new objects on every call.
    """
    state = _prepared_state(handle)
    fixed = json.loads(state.payload)
    registered = next((p for p in fixed["paths"] if p["record_id"] == path.get("record_id")), None)
    if registered is None or _encoded(registered) != _encoded(path):
        raise ValueError("resolution_path_not_in_prepared_registry")
    key_track, functions = json.loads(_encoded([key_track, functions]))
    compiled = compile_resolutions(fixed["view"], registered, key_track, functions, fixed["graphs"],
                                   max_candidates=max_candidates, max_chain_edges=max_chain_edges)
    return _assessment(fixed["view"], registered, key_track, functions, fixed["bundle"], compiled,
                       max_candidates=max_candidates, max_chain_edges=max_chain_edges)


def evaluate_resolutions(view, path, key_track, functions, graphs, bundle, *, max_candidates=1024, max_chain_edges=8):
    return _evaluate_resolutions(view, path, key_track, functions, graphs, bundle,
                                 max_candidates=max_candidates, max_chain_edges=max_chain_edges,
                                 _compiler=compile_resolutions)


def validate_evaluation(view, path, key_track, functions, graphs, bundle, record):
    common.check(record, "fmreval_")
    if record != _evaluate_resolutions(view, path, key_track, functions, graphs, bundle,
                                      max_candidates=record["max_candidates"], max_chain_edges=record["max_chain_edges"],
                                      _compiler=_compile_fresh):
        raise ValueError("stale_foreign_or_modified_resolution_evaluation")
    return True


def _solve_joint(view, path, key_track, functions, graphs, resolution_requests=(), nct_requests=(), *,
                comparison_paths=None, branch_budget=256, work_budget=100000,
                max_candidates=1024, max_chain_edges=8, _compiler=compile_resolutions):
    """AND an explicit subset in ONE branch; preserve each role's alternatives."""
    before = digest([view, path, key_track, functions, graphs, resolution_requests, nct_requests, comparison_paths])
    _budget(branch_budget, "branch_budget")
    _budget(work_budget, "work_budget")
    registry = _paths(view, path if comparison_paths is None else comparison_paths)
    if common.ref(path) not in [common.ref(p) for p in registry]:
        raise ValueError("requested_path_missing_from_comparison_registry")
    inventory = _graphs(view, path, graphs)
    compiled = _compiler(view, path, key_track, functions, graphs,
                         max_candidates=max_candidates, max_chain_edges=max_chain_edges)
    rows = {r["resolution_id"]: r for r in compiled["rules"]}
    requested, ids = [], set()
    for request in resolution_requests:
        if not isinstance(request, dict) or set(request) != {"compiled_ref", "resolution_id"}:
            raise ValueError("canonical_resolution_reference_required")
        if request["compiled_ref"] != common.ref(compiled) or request["resolution_id"] not in rows:
            raise ValueError("foreign_stale_or_unknown_resolution_reference")
        row = rows[request["resolution_id"]]
        if row["resolution_id"] in ids:
            raise ValueError("duplicate_requested_resolution")
        ids.add(row["resolution_id"])
        requested.append({"kind": "resolution", "ref": row["resolution_id"], "status": row["status"],
                          "blockers": row["blockers"], "alternatives": row["alternatives"]})
    for request in nct_requests:
        if not isinstance(request, dict) or set(request) != {"graph_ref", "compiled", "rule_id"}:
            raise ValueError("canonical_compiled_nct_reference_required")
        graph = inventory.get(request["graph_ref"]["record_id"])
        if graph is None or common.ref(graph) != request["graph_ref"]:
            raise ValueError("foreign_nct_graph_reference")
        nct.validate_rules(view, path, graph, request["compiled"])
        row = next((r for r in request["compiled"]["rules"] if r["rule_id"] == request["rule_id"]), None)
        if row is None or row["rule_id"] in ids:
            raise ValueError("unknown_or_duplicate_canonical_nct_rule")
        ids.add(row["rule_id"])
        requested.append({"kind": "nct", "ref": row["rule_id"], "status": row["status"], "blockers": row["blockers"],
                          "alternatives": [{**deepcopy(a), "graph_ref": common.ref(graph)} for a in row["alternatives"]]})
    count = math.prod(len(r["alternatives"]) for r in requested)
    body = {"version": VERSION, "view_ref": common.ref(view), "path_ref": common.ref(path),
            "key_track_ref": common.ref(key_track), "functions_ref": common.ref(functions),
            "compiled_ref": common.ref(compiled), "graph_refs": sorted([common.ref(g) for g in graphs], key=lambda r: r["record_id"]),
            "path_refs": [common.ref(p) for p in registry], "resolution_requests": deepcopy(list(resolution_requests)),
            "nct_requests": deepcopy(list(nct_requests)), "requested_canonical_clauses": deepcopy(requested),
            "branch_budget": branch_budget, "work_budget_per_query": work_budget,
            "max_candidates": max_candidates, "max_chain_edges": max_chain_edges,
            "possible_branch_count": str(count), "branches": [], "status": "unassessed", "reasons": [],
            "all_requested_branches_assessed": False, "branch_counts_may_be_summed": False,
            "witnesses_may_be_unioned": False, "possible_assignments_union": None,
            "constraint_semantics": "AND_of_explicit_requests_OR_of_each_request_alternatives_one_query_per_lane", **_flags()}
    withheld = [r["ref"] for r in requested if r["status"] not in ("conditional_resolution_shape", "conditional_shape") or r["blockers"] or not r["alternatives"]]
    if withheld:
        body["reasons"] = ["requested_prerequisites_withheld_unknown_not_false"]
        body["withheld_requested_refs"] = withheld
    elif count > branch_budget:
        body["reasons"] = ["whole_OR_branch_budget_exceeded_no_partial_success"]
    else:
        unknown = False
        for choices in product(*(range(len(r["alternatives"])) for r in requested)):
            by_graph = {rid: {"required": set(), "forbidden": set()} for rid in inventory}
            selected = []
            for row, index in zip(requested, choices):
                alt = row["alternatives"][index]
                ref = alt["graph_ref"]
                if ref["record_id"] not in inventory or common.ref(inventory[ref["record_id"]]) != ref:
                    raise ValueError("foreign_rule_alternative_graph")
                by_graph[ref["record_id"]]["required"].update(tuple(p) for p in alt["required_links"])
                by_graph[ref["record_id"]]["forbidden"].update(tuple(p) for p in alt["forbidden_links"])
                selected.append({"requested_ref": row["ref"], "kind": row["kind"], "alternative_index": index})
            queries, entries = [], []
            for rid in sorted(inventory):
                graph, constraints = inventory[rid], by_graph[rid]
                query = factors.query(graph, required_links=[list(p) for p in sorted(constraints["required"])],
                                      forbidden_links=[list(p) for p in sorted(constraints["forbidden"])], work_budget=work_budget)
                witness = factors.materialize_witness(graph, query) if query["status"] == "exact_count" else None
                queries.append({"graph_ref": common.ref(graph), "query": query, "witness": witness})
                if witness is not None:
                    entries.append({"graph": graph, "query": query, "witness": witness})
            unavailable = any(q["query"]["status"] not in ("exact_count", "unsatisfiable_constraints") for q in queries)
            unsat = any(q["query"]["status"] == "unsatisfiable_constraints" for q in queries)
            status = "unassessed" if unavailable else "incompatible_joint_constraints" if unsat else "joint_possible"
            bundle = make_bundle(view, registry, entries) if status == "joint_possible" else None
            body["branches"].append({"chosen_alternatives": selected, "queries": queries,
                                     "completion_bundle": bundle, "status": status})
            unknown |= unavailable
        body["all_requested_branches_assessed"] = not unknown
        if unknown:
            body["reasons"] = ["one_or_more_lane_queries_unassessed_no_partial_success"]
        elif any(b["status"] == "joint_possible" for b in body["branches"]):
            body["status"] = "joint_possible"
        else:
            body["status"] = "incompatible_joint_constraints"
            body["reasons"] = ["all_explicit_requested_alternatives_jointly_unsatisfiable"]
    if digest([view, path, key_track, functions, graphs, resolution_requests, nct_requests, comparison_paths]) != before:
        raise ValueError("functional_joint_inputs_mutated")
    return common.seal(body, "fmfj_")


def solve_joint(view, path, key_track, functions, graphs, resolution_requests=(), nct_requests=(), *,
                comparison_paths=None, branch_budget=256, work_budget=100000,
                max_candidates=1024, max_chain_edges=8):
    return _solve_joint(view, path, key_track, functions, graphs, resolution_requests, nct_requests,
                        comparison_paths=comparison_paths, branch_budget=branch_budget, work_budget=work_budget,
                        max_candidates=max_candidates, max_chain_edges=max_chain_edges,
                        _compiler=compile_resolutions)


def validate_joint(view, path, key_track, functions, graphs, record, *, comparison_paths=None):
    common.check(record, "fmfj_")
    fresh = _solve_joint(view, path, key_track, functions, graphs, record["resolution_requests"], record["nct_requests"],
                        comparison_paths=comparison_paths, branch_budget=record["branch_budget"],
                        work_budget=record["work_budget_per_query"], max_candidates=record["max_candidates"],
                        max_chain_edges=record["max_chain_edges"], _compiler=_compile_fresh)
    if fresh != record:
        raise ValueError("stale_foreign_or_modified_functional_joint")
    return True
