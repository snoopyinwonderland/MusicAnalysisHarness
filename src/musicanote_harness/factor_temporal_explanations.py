"""Descriptor-local conditional contours and literal temporal presentation.

Raw note-time never changes.  Every contour needs both direct links in ONE
actual all-raw-lane completion.  Pooling written members is not an arpeggio,
NCT, sustained harmony, delayed resolution, or musical verdict.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import hmac
from pathlib import Path
import secrets
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import factor_grounded_relations as grounded
from . import factor_indexed_hypotheses as indexed
from . import factor_expanded_hypotheses as frozen
from . import harmony_factorized_voice_paths as geometry
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "factor-temporal-explanations-0.1.0"
PREFIX = "fmte_"
GEOMETRY_PREFIX = "fmtegeom_"
RELATION_PREFIX = "fmterel_"
PRESENTATION_PREFIX = "fmtepresent_"
ACCOUNT_PREFIX = "fmteaccount_"
BUNDLE_PREFIX = "fmtebundle_"
QUERY_PREFIX = "fmtequery_"
CAPS = ("max_geometry_candidates", "max_membership_relations", "max_new_bundles",
        "max_account_templates", "query_work_budget")
CATEGORIES = ("source_guarded_member", "conditional_explained_nonmember",
    "unexplained_nonmember_under_this_completion", "unassessed_nonmember",
    "membership_unknown", "source_or_hypothesis_unsupported")
_INPUTS = WeakKeyDictionary()
_SESSIONS = WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)


def _flags():
    return {**grounded._flags(), "nct_confirmed": False, "arpeggio_confirmed": False,
        "chord_persistence_confirmed": False, "boundary_nct_evaluated": False,
        "delayed_resolution_evaluated": False, "pooled_members_certify_harmony": False,
        "explanation_modifies_raw_membership": False, "counts_are_confidence": False,
        "explanations_add_note_time": False, "independent_completions_unioned": False}


def _contract():
    return {"version": VERSION, "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "grounding_contract": grounded._contract(),
        "geometry_source_sha256": sha256(Path(geometry.__file__).read_bytes()).hexdigest()}


def _seal(body, prefix):
    return frozen._seal(body, prefix)


def _ref(record):
    return frozen._ref(record)


def _caps(values):
    for name in CAPS:
        indexed._integer(values[name], name)


class _PreparedInputs:
    __slots__ = ("__weakref__",)


class _PreparedExplanations:
    __slots__ = ("__weakref__",)


@dataclass(frozen=True)
class _State:
    data: object
    lookups: object
    contract_sha256: str
    authentication: bytes


def _auth(handle, state):
    return hmac.digest(_SECRET, indexed._encoded([id(handle), id(state), id(state.data),
        id(state.lookups), state.contract_sha256]), "sha256")


def _issued(handle, registry, cls):
    if type(handle) is not cls or handle not in registry:
        raise ValueError("internally_issued_temporal_session_required")
    state = registry[handle]
    if (type(state) is not _State or not isinstance(state.data, MappingProxyType)
            or not isinstance(state.lookups, MappingProxyType)
            or state.contract_sha256 != digest(_contract())
            or not hmac.compare_digest(state.authentication, _auth(handle, state))):
        raise ValueError("temporal_session_current_contract_or_owned_state_changed")
    return state


def _issue(cls, registry, data, lookups):
    handle = cls()
    state = _State(indexed._freeze(data), indexed._freeze(lookups), digest(_contract()), b"")
    object.__setattr__(state, "authentication", _auth(handle, state))
    registry[handle] = state
    return handle


def prepare_inputs(ir, scope, hypotheses, index, relations, grounding):
    """One authentic full parent replay, then an owned immutable supplier."""
    caller = [ir, scope, hypotheses, index, relations, grounding]
    before, contract = digest(caller), _contract()
    owned = deepcopy(caller)
    parent_session = grounded.prepare_grounding(*owned)
    grounded._session(parent_session)
    data = {"scope": owned[1], "index": owned[3], "relations": owned[4], "grounding": owned[5]}
    if before != digest(caller) or not indexed._same(contract, _contract()):
        raise ValueError("temporal_inputs_or_code_changed_during_owned_parent_validation")
    return _issue(_PreparedInputs, _INPUTS, data, {})


def _span(a, b):
    return {"start": q(a), "end": q(b)}


def _union(spans):
    ordered = sorted(span_bounds(s) for s in spans if f(s["start"]) < f(s["end"]))
    result = []
    for a, b in ordered:
        if result and a <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], b))
        else:
            result.append((a, b))
    return [_span(a, b) for a, b in result]


def _duration(spans):
    return sum((f(s["end"]) - f(s["start"]) for s in spans), Fraction())


def _guard_codes(sound):
    reasons = list(sound["source_diagnostics"])
    if sound["eligible_as_analysis_source"] is not True:
        reasons.append("source_not_eligible")
    for name in ("source_clock_passed", "source_pitch_consistency_passed", "source_attack_consistency_passed"):
        if sound.get(name) is not True:
            reasons.append(name + "_not_passed")
    if sound["point"] or sound["grace"]:
        reasons.append("point_or_grace_positive_time_role_not_supported")
    return sorted(set(reasons))


def _geometries(scope, cap):
    inventories, unknown, known_count = [], False, 0
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    for graph in sorted(scope["graphs"], key=lambda g: g["lane"]):
        unknown |= graph["status"] != "ready"
        outgoing = defaultdict(set)
        for factor in graph["factors"]:
            for src in factor["source_refs"]:
                outgoing[src].update(factor["target_refs"])
        incoming = Counter(y for targets in outgoing.values() for y in targets)
        known_count += sum(incoming[y] * len(targets) for y, targets in outgoing.items())
        inventories.append((graph, outgoing))
    count = None if unknown else known_count
    held = known_count > cap or unknown
    rows = []
    if not held:
        specs = ((graph, (x, y, z)) for graph, outgoing in inventories
            for x in sorted(outgoing) for y in sorted(outgoing[x]) for z in sorted(outgoing.get(y, ())))
        for graph, refs in specs:
            chain = [sounds[sid] for sid in refs]
            moves = [frozen._move(a, b) for a, b in zip(chain, chain[1:])]
            ordinary = [move is not None and abs(move["diatonic_steps"]) == 1
                and abs(f(move["semitones"])) in (1, 2)
                and move["diatonic_steps"] * f(move["semitones"]) > 0
                and frozen._integer_pitch(a["pitch"]) and frozen._integer_pitch(b["pitch"])
                for move, a, b in zip(moves, chain, chain[1:])]
            same = frozen._pitch_key(chain[0]["pitch"], True) == frozen._pitch_key(chain[2]["pitch"], True)
            direction = None if any(move is None for move in moves) else f(moves[0]["semitones"]) * f(moves[1]["semitones"])
            family = ("neighbor" if all(ordinary) and same else "passing" if all(ordinary) and direction > 0
                      else "passing_neighbor_unsupported")
            reasons = ["source:" + s["sound_ref"] + ":" + code for s in chain for code in _guard_codes(s)]
            reasons.extend(code for s in chain for code in frozen._source_blockers(s))
            if family == "passing_neighbor_unsupported": reasons.append("ordinary_passing_neighbor_contour_not_met")
            body = {"version": VERSION, "scope_ref": _ref(scope), "graph_ref": _ref(graph),
                "raw_lane": deepcopy(graph["lane"]), "family": family,
                "involved_sound_refs": list(refs), "source_note_refs": [nid for s in chain for nid in s["source_note_refs"]],
                "full_sound_spans": [deepcopy(s["span"]) for s in chain],
                "explained_sound_ref": refs[1], "explained_span": deepcopy(chain[1]["span"]),
                "required_links": [[refs[0], refs[1]], [refs[1], refs[2]]], "motions": moves,
                "status": "conditional_contour_geometry" if not reasons else "withheld_contour_geometry",
                "blockers": sorted(set(reasons)), "accent": "unassessed", "consonance": "unassessed",
                "metric_role": "unassessed", "flags": _flags()}
            rows.append(_seal(body, GEOMETRY_PREFIX))
    return rows, count, known_count, held, unknown


def _profile_tables(index, grounding):
    descriptors = {d["record_id"]: d for d in index["profile_inventory"]}
    profiles = {p["descriptor_ref"]["record_id"]: p for p in grounding["profile_inventory"]}
    rows = {r["record_id"]: r for r in grounding["row_inventory"]}
    cells = {c["record_id"]: c for c in grounding["cell_inventory"]}
    return descriptors, profiles, rows, cells


def _presentations(scope, descriptors, profiles, rows, cells):
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    notes = {slot["core_event"]["note_id"]: slot["core_event"] for slot in scope["literal_observation"]["slots"]
             if slot["event_kind"] == "note"}
    result = []
    for did, descriptor in descriptors.items():
        profile = profiles.get(did)
        semantic = descriptor["semantic_input"]
        body = {"version": VERSION, "scope_ref": _ref(scope), "descriptor_ref": _ref(descriptor),
            "grounded_profile_ref": None if profile is None else _ref(profile),
            "span": deepcopy(semantic["span"]), "root": deepcopy(semantic["root"]),
            "ordered_members": deepcopy(semantic["members"]), "blockers": deepcopy(semantic["blockers"]),
            "members": None, "simultaneous_raw_core_spans": None, "simultaneous_guarded_core_spans": None,
            "pooled_written_member_presence_complete": None, "pooled_guarded_member_presence_complete": None,
            "status": "upstream_literal_profile_unavailable", "flags": _flags(),
            "arpeggio_and_chord_persistence": "unassessed", "boundary_NCT_and_delayed_resolution": "unassessed"}
        if profile is not None:
            body["status"] = "literal_temporal_presentation_not_harmony"
            actual_rows = [rows[rid]["value"] for rid in profile["row_ids"]]
            actual_cells = [cells[cid]["value"] for cid in profile["cell_ids"]]
            if semantic["members"] is not None:
                member_rows = []
                for ordinal, member in enumerate(semantic["members"]):
                    matching = [r for r in actual_rows if frozen._pitch_key(r["pitch"]) == frozen._pitch_key(member)]
                    guarded = [r for r in matching if not _guard_codes(sounds[r["sound_ref"]])]
                    uses = []
                    for r in matching:
                        sound = sounds[r["sound_ref"]]
                        note = notes.get(sound["attack_note_ref"])
                        uses.append({"sound_ref": sound["sound_ref"], "source_note_refs": deepcopy(sound["source_note_refs"]),
                            "attack_note_ref": sound["attack_note_ref"], "raw_lane": deepcopy(sound["lane"]),
                            "full_span": deepcopy(sound["span"]), "observed_span": deepcopy(r["observed_span"]),
                            "actual_attack_time": None if note is None else deepcopy(note["global_onset_quarter"]),
                            "first_observed_time": deepcopy(r["observed_span"]["start"]),
                            "raw_membership": r["state"], "source_guard_blockers": _guard_codes(sound)})
                    raw_union = _union([r["observed_span"] for r in matching])
                    guarded_union = _union([r["observed_span"] for r in guarded])
                    member_rows.append({"member_index": ordinal, "member": deepcopy(member), "observations": uses,
                        "raw_presence_union": raw_union, "guarded_presence_union": guarded_union,
                        "raw_presence_duration": q(_duration(raw_union)), "guarded_presence_duration": q(_duration(guarded_union)),
                        "raw_additive_note_time": q(sum((f(r["observed_span"]["end"]) - f(r["observed_span"]["start"]) for r in matching), Fraction())),
                        "first_observed_time": None if not raw_union else raw_union[0]["start"],
                        "last_observed_time": None if not raw_union else raw_union[-1]["end"]})
                raw_core = _union([c["span"] for c in actual_cells if c["sound_refs"] and c["missing_spellings"] == []])
                guarded_core = _union([c["span"] for c in actual_cells if c["sound_refs"] and c["source_guard_missing_spellings"] == []])
                body.update(members=member_rows, simultaneous_raw_core_spans=raw_core,
                    simultaneous_guarded_core_spans=guarded_core,
                    pooled_written_member_presence_complete=bool(member_rows) and all(r["raw_presence_union"] for r in member_rows),
                    pooled_guarded_member_presence_complete=bool(member_rows) and all(r["guarded_presence_union"] for r in member_rows))
        result.append(_seal(body, PRESENTATION_PREFIX))
    return result


def _memberships(descriptors, geometries, scope, ready, cap):
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    groups = {}; conditional = defaultdict(set); pair_counts = Counter()
    if not ready:
        return [], conditional, None, pair_counts, True
    pitch_keys = {sid: frozen._pitch_key(sound["pitch"]) for sid, sound in sounds.items()}
    distinct_pitches = set(pitch_keys.values())
    state_tables, descriptor_inputs = {}, {}
    for did, descriptor in descriptors.items():
        semantic = descriptor["semantic_input"]
        signature = None if semantic["members"] is None else tuple(frozen._pitch_key(p) for p in semantic["members"])
        if signature not in state_tables:
            member_keys = None if signature is None else set(signature)
            state_tables[signature] = {key: "spelling_unresolved" if key is None or member_keys is None else
                "member" if key in member_keys else "nonmember_not_confirmed_nct" for key in distinct_pitches}
        descriptor_inputs[did] = (span_bounds(semantic["span"]), signature, tuple(semantic["blockers"]))
    # One finite signature relation for many exact, individually retained
    # descriptor IDs. No Cartesian path or per-descriptor clause object.
    for geom in geometries:
        extents = [span_bounds(s) for s in geom["full_sound_spans"]]
        chain_pitches = [pitch_keys[sid] for sid in geom["involved_sound_refs"]]
        for did, descriptor in descriptors.items():
            (a, b), signature, hypothesis_blockers = descriptor_inputs[did]
            covered = all(a <= x < y <= b for x, y in extents)
            states = tuple(state_tables[signature][key] for key in chain_pitches)
            key = (geom["record_id"], covered, states, hypothesis_blockers)
            if key not in groups:
                blockers = list(geom["blockers"])
                if not covered: blockers.append("all_three_full_sound_spans_not_inside_descriptor")
                blockers.extend("hypothesis:" + reason for reason in hypothesis_blockers)
                if "spelling_unresolved" in states:
                    blockers.append("contour_membership_unknown")
                elif states != ("member", "nonmember_not_confirmed_nct", "member"):
                    blockers.append("member_nonmember_member_prerequisites_not_met")
                body = {"version": VERSION, "geometry_ref": _ref(geom), "descriptor_ids": [],
                    "membership_states": list(states), "expected_states": ["member", "nonmember_not_confirmed_nct", "member"],
                    "all_three_full_spans_inside_descriptor": covered, "hypothesis_blockers": list(hypothesis_blockers),
                    "status": "conditional_contour_shape" if not blockers else "withheld_contour_prerequisites",
                    "blockers": sorted(set(blockers)), "flags": _flags(),
                    "accent_consonance_and_complete_NCT_classification": "unassessed"}
                groups[key] = body
            body = groups[key]
            body["descriptor_ids"].append(did)
            pair_counts[body["status"]] += 1
            if body["status"] == "conditional_contour_shape": conditional[did].add(geom["record_id"])
    count = len(groups)
    held = count > cap
    records = [] if held else [_seal(body, RELATION_PREFIX) for body in groups.values()]
    return records, conditional if not held else defaultdict(set), count, pair_counts, held


def _universe(scope, index, grounding):
    return _seal({"version": VERSION, "scope_ref": _ref(scope), "index_ref": _ref(index),
        "grounding_ref": _ref(grounding), "indexed_universe_ref": _ref(index["universe"]),
        "grounded_universe_ref": _ref(grounding["logical_universe"]),
        "logical_paths": grounding["summary"]["logical_paths"],
        "logical_path_key_tuples": grounding["summary"]["logical_path_key_tuples"],
        "logical_function_rows": grounding["summary"]["logical_function_rows"],
        "unknown_product_groups": grounding["summary"]["unknown_product_groups"],
        "representation": "all_original_origins_catalogue_products_keys_and_descriptor_local_axes_not_enumerated_paths",
        "flags": _flags()}, "fmteuniverse_")


def _new_bundle(scope, index, grounding, universe, required, work_budget):
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    by_lane = defaultdict(list); reasons = []
    for src, dst in required:
        if src not in sounds or dst not in sounds or sounds[src]["lane"] != sounds[dst]["lane"]:
            raise ValueError("local_contour_request_has_foreign_or_cross_lane_edge")
        by_lane[tuple(sounds[src]["lane"])].append([src, dst])
    entries = []
    for graph in sorted(scope["graphs"], key=lambda g: g["lane"]):
        result = geometry.query(graph, required_links=by_lane.get(tuple(graph["lane"]), []), work_budget=work_budget)
        witness = geometry.materialize_witness(graph, result) if result["status"] == "exact_count" and result["possible_assignments"] != "0" else None
        entries.append({"lane": deepcopy(graph["lane"]), "graph_ref": _ref(graph), "query": result,
            "witness": witness, "status": "complete" if witness is not None else "lane_withheld"})
        if witness is None:
            reasons.extend("lane_query:" + reason for reason in result["reasons"])
            if not result["reasons"]:
                reasons.append("lane_query:certified_zero_assignments" if result["possible_assignments"] == "0"
                    else "lane_query:completion_not_available")
    covered = sorted(e["lane"] for e in entries)
    expected = sorted([[r["part_id"], r["voice_id"]] for r in scope["raw_lanes"]])
    if covered != expected: reasons.append("complete_raw_lane_graph_inventory_missing")
    links = sorted({tuple(pair) for e in entries if e["witness"] is not None for pair in e["witness"]["assignment"]["links"]})
    if not reasons and links != list(required): raise ValueError("local_chain_witness_required_links_mismatch")
    condition = ("possible" if not reasons else "impossible" if any(e["query"]["status"] in
        ("exact_count", "unsatisfiable_constraints") and e["query"]["possible_assignments"] == "0" for e in entries) else "unknown")
    return _seal({"version": VERSION, "contract": _contract(), "binding": deepcopy(scope["binding"]),
        "scope_ref": _ref(scope), "analysis_span": deepcopy(scope["analysis_span"]), "index_ref": _ref(index),
        "grounding_ref": _ref(grounding), "symbolic_universe_ref": _ref(universe),
        "comparison_key_refs": [_ref(k) for k in grounding["keys"]],
        "comparison_representation": "full_original_symbolic_universe_not_empty_or_fabricated_paths",
        "required_links": [list(p) for p in required], "materialized_witness_links": [list(p) for p in links],
        "entries": entries, "covered_lanes": covered, "status": "complete_all_lane_witness" if not reasons else "all_lane_witness_withheld",
        "geometry_condition_status": condition, "reasons": sorted(set(reasons)),
        "query_work_budget": work_budget, "all_unrequired_edges_left_unconnected": True,
        "all_no_link_control": not required, "flags": _flags()}, BUNDLE_PREFIX)


def _links(bundle):
    return {tuple(pair) for entry in bundle["entries"] if entry["witness"] is not None
        for pair in entry["witness"]["assignment"]["links"]}


def _account(did, descriptor, profile, rows, sounds, geometries, supported, assessed):
    raw = deepcopy(profile["profile_core"]["note_time_quarters"])
    totals = {name: Fraction() for name in CATEGORIES}
    intervals = defaultdict(list)
    for gid in supported:
        geom = geometries[gid]
        intervals[geom["explained_sound_ref"]].append(geom["explained_span"])
    unions = {sid: _union(spans) for sid, spans in intervals.items()}
    for rid in profile["row_ids"]:
        row = rows[rid]["value"]; sid = row["sound_ref"]
        duration = f(row["observed_span"]["end"]) - f(row["observed_span"]["start"])
        if descriptor["semantic_input"]["blockers"] or _guard_codes(sounds[sid]):
            totals["source_or_hypothesis_unsupported"] += duration
        elif row["state"] == "member": totals["source_guarded_member"] += duration
        elif row["state"] == "spelling_unresolved": totals["membership_unknown"] += duration
        elif not assessed: totals["unassessed_nonmember"] += duration
        else:
            a, b = span_bounds(row["observed_span"])
            clipped = [_span(max(a, x), min(b, y)) for x, y in (span_bounds(s) for s in unions.get(sid, ())) if max(a, x) < min(b, y)]
            credit = _duration(_union(clipped))
            totals["conditional_explained_nonmember"] += credit
            totals["unexplained_nonmember_under_this_completion"] += duration - credit
    total = f(profile["profile_core"]["total_note_time_quarters"])
    if sum(totals.values(), Fraction()) != total: raise ValueError("temporal_accounting_note_time_loss")
    return _seal({"version": VERSION, "descriptor_ref": _ref(descriptor), "grounded_profile_ref": _ref(profile),
        "raw_note_time": raw, "total_note_time": q(total), "note_time": {k: q(v) for k, v in totals.items()},
        "conditional_explanation_note_time": q(totals["conditional_explained_nonmember"]) if assessed else None,
        "unexplained_nonmember_note_time": q(totals["unexplained_nonmember_under_this_completion"]) if assessed else None,
        "supported_geometry_refs": [_ref(geometries[gid]) for gid in sorted(supported)],
        "explained_intervals_by_sound": [{"sound_ref": sid, "spans": spans} for sid, spans in sorted(unions.items())],
        "status": "conditional_account_under_one_completion_not_NCT_verdict" if assessed else "unassessed_contour_axis_raw_time_preserved",
        "account_template_semantics": "descriptor_and_exact_supported_clause_set_attach_only_to_registered_same_bundle",
        "boundary_NCT_and_delayed_resolution": "unassessed", "flags": _flags()}, ACCOUNT_PREFIX)


def _weights(index, descriptors):
    cats = defaultdict(Counter)
    for row in index["variant_inventory"]: cats[row["catalog_id"]][row["profile_ref"]["record_id"]] += 1
    groups = []
    for old in index["path_groups"]:
        slots = []
        for position, slot in enumerate(old["slots"]):
            other = 1
            for j, s in enumerate(old["slots"]):
                if j != position: other *= len(s["variant_ids"])
            records = [{"descriptor_id": did, "origin_multiplicity": n,
                "weighted_descriptor_uses": n * other * len(index["keys"])} for did, n in cats[slot["catalog_id"]].items()]
            slots.append({"slot_index": position, "catalog_id": slot["catalog_id"], "span": deepcopy(slot["span"]),
                "descriptor_weights": records,
                "origin_snapshot_count": sum(cats[slot["catalog_id"]].values()),
                "declared_origin_count": len(slot["variant_ids"])})
        groups.append({**deepcopy(old), "temporal_descriptor_weights": slots,
            "boundary_NCT_and_delayed_resolution": "unassessed",
            "descriptor_local_explanations_are_partition_dependent": True})
    return groups


def _body(scope, index, relations, grounding, caps):
    descriptors, profiles, rows, cells = _profile_tables(index, grounding)
    presentations = _presentations(scope, descriptors, profiles, rows, cells)
    geometries, planned_geom, known_geom, geometry_hold, unknown_geom = _geometries(scope, caps["max_geometry_candidates"])
    profile_ready = grounding["summary"]["literal_profiles_complete"] is True
    relation_ready = profile_ready and not geometry_hold
    relation_rows, conditional, planned_rel, pair_counts, relation_hold = _memberships(descriptors, geometries, scope,
        relation_ready, caps["max_membership_relations"])
    universe = _universe(scope, index, grounding)
    geom_by_id = {g["record_id"]: g for g in geometries}
    request_map = {}
    if not relation_hold:
        eligible = set().union(*conditional.values()) if conditional else set()
        for geom in geometries:
            if geom["record_id"] in eligible:
                required = tuple(sorted(tuple(p) for p in geom["required_links"]))
                request_map.setdefault(required, []).append(_ref(geom))
    planned_new = None if relation_hold else len(request_map)
    bundle_hold = len(request_map) > caps["max_new_bundles"]
    requests = []; new_bundles = []
    for required, refs in request_map.items():
        bundle = None if bundle_hold else _new_bundle(scope, index, grounding, universe, required, caps["query_work_budget"])
        if bundle is not None: new_bundles.append(bundle)
        requests.append(_seal({"version": VERSION, "symbolic_universe_ref": _ref(universe),
            "geometry_refs": refs, "required_links": [list(p) for p in required],
            "bundle_ref": None if bundle is None else _ref(bundle),
            "status": "whole_new_completion_inventory_budget_hold" if bundle is None else bundle["geometry_condition_status"],
            "flags": _flags()}, "fmtebundlereq_"))
    inherited = deepcopy(grounding["bundle_inventory"])
    actual_bundles = inherited + new_bundles
    bundle_keys = []; template_keys = set(); pair_count = len(descriptors) * len(actual_bundles)
    for bundle in actual_bundles:
        links = _links(bundle)
        witnessed = {gid for gid, geom in geom_by_id.items() if all(tuple(p) in links for p in geom["required_links"])}
        assessed = not relation_hold and bundle["status"] == "complete_all_lane_witness"
        per_descriptor = {}
        for did in descriptors:
            if did not in profiles: continue
            supported = tuple(sorted(conditional.get(did, set()) & witnessed)) if assessed else ()
            key = (did, assessed, supported)
            template_keys.add(key); per_descriptor[did] = key
        bundle_keys.append((bundle, assessed, per_descriptor))
    account_hold = len(template_keys) > caps["max_account_templates"]
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    templates = {}; baselines = {}; associations = []
    if not account_hold:
        for did, assessed, supported in sorted(template_keys):
            account = _account(did, descriptors[did], profiles[did], rows, sounds, geom_by_id, supported, assessed)
            templates[(did, assessed, supported)] = account
            if not supported: baselines.setdefault(did, {})["complete" if assessed else "unassessed"] = _ref(account)
        for bundle, assessed, pairs in bundle_keys:
            overrides = [{"descriptor_id": did, "account_ref": _ref(templates[key])} for did, key in pairs.items() if key[2]]
            associations.append({"bundle_ref": _ref(bundle), "bundle_origin": "inherited_grounding_not_retargeted" if bundle in inherited else "new_local_chain_completion",
                "default_account_kind": "complete" if assessed else "unassessed", "overrides": overrides,
                "represented_descriptor_count": len(descriptors), "admitted_profile_count": len(pairs),
                "same_complete_all_lane_bundle": bundle["status"] == "complete_all_lane_witness",
                "link_basis": "actual_materialized_links_AND_of_both_contour_edges_not_union_of_witnesses"})
    groups = _weights(index, descriptors)
    weighted_accounts = []
    scope_note_time = sum((f(s["observed_span"]["end"]) - f(s["observed_span"]["start"])
        for s in scope["sound_facts"]), Fraction())
    if not account_hold:
        for bundle, assessed, pairs in bundle_keys:
            accounts = []
            for group in groups:
                totals = {k: Fraction() for k in CATEGORIES}; raw = {k: Fraction() for k in frozen.catalog.STATES}
                unknown_uses = 0; known_uses = 0
                for slot in group["temporal_descriptor_weights"]:
                    if slot["origin_snapshot_count"] != slot["declared_origin_count"]: unknown_uses += 1
                    for row in slot["descriptor_weights"]:
                        did, weight = row["descriptor_id"], row["weighted_descriptor_uses"]
                        if did not in pairs: unknown_uses += weight; continue
                        account = templates[pairs[did]]; known_uses += weight
                        for k in totals: totals[k] += f(account["note_time"][k]) * weight
                        for k in raw: raw[k] += f(account["raw_note_time"][k]) * weight
                unknown = group["logical_path_count"] is None or (
                    group["logical_path_count"] != 0 and bool(unknown_uses))
                if not unknown:
                    tuples = group["logical_path_count"] * len(index["keys"])
                    if known_uses != tuples * len(group["slots"]):
                        raise ValueError("weighted_temporal_descriptor_multiplicity_loss")
                    expected_time = scope_note_time * tuples
                    if (sum(totals.values(), Fraction()) != expected_time
                            or sum(raw.values(), Fraction()) != expected_time):
                        raise ValueError("weighted_temporal_partition_note_time_loss")
                accounts.append({"group_id": group["group_id"], "logical_path_count": group["logical_path_count"],
                    "logical_path_key_count": None if group["logical_path_count"] is None else group["logical_path_count"] * len(index["keys"]),
                    "logical_function_count": group["logical_function_count"], "known_weighted_descriptor_uses": known_uses,
                    "weighted_note_time": None if unknown else {k: q(v) for k, v in totals.items()},
                    "known_weighted_note_time_subtotal": {k: q(v) for k, v in totals.items()},
                    "weighted_raw_note_time": None if unknown else {k: q(v) for k, v in raw.items()},
                    "known_weighted_raw_note_time_subtotal": {k: q(v) for k, v in raw.items()},
                    "status": "unknown_source_product_raw_subtotal_retained" if unknown else "descriptor_local_axes_under_same_bundle_not_full_harmony",
                    "boundary_NCT_and_delayed_resolution": "unassessed"})
            weighted_accounts.append({"bundle_ref": _ref(bundle), "accounts": accounts,
                "different_bundle_totals_may_be_summed_as_confidence": False})
    descriptor_origins = defaultdict(list)
    for variant in index["variant_inventory"]:
        descriptor_origins[variant["profile_ref"]["record_id"]].append(variant["variant_id"])
    descriptor_rows = [{"descriptor_ref": _ref(d), "semantic_input": deepcopy(d["semantic_input"]),
        "grounded_profile_ref": None if did not in profiles else _ref(profiles[did]),
        "presentation_ref": _ref(presentations[i]),
        "origin_variant_ids": descriptor_origins[did],
        "status": "available_literal_descriptor" if did in profiles else "upstream_literal_profile_unavailable"}
        for i, (did, d) in enumerate(descriptors.items())]
    reasons = []
    if not profile_ready: reasons.append("upstream_literal_profile_inventory_not_complete")
    if geometry_hold: reasons.append("raw_geometry_inventory_unknown_or_whole_budget_hold")
    if relation_hold: reasons.append("membership_relation_inventory_unknown_or_whole_budget_hold")
    if bundle_hold: reasons.append("whole_new_completion_inventory_exceeds_budget_no_prefix")
    if account_hold: reasons.append("whole_account_template_inventory_exceeds_budget_no_prefix")
    if any(b["status"] != "complete_all_lane_witness" for b in actual_bundles): reasons.append("one_or_more_actual_bundle_completions_withheld")
    logical = grounding["summary"]
    known_variant_ids = {v for group in index["path_groups"] for slot in group["slots"] for v in slot["variant_ids"]}
    origin_ready = index["status"] != "whole_index_budget_hold" and logical["unknown_supplier_catalogs"] == 0
    summary = {"origin_variants": len(grounding["origin_inventory"]),
        "planned_origin_variants": len(grounding["origin_inventory"]) if origin_ready else None,
        "known_origin_variant_ids": len(known_variant_ids), "known_stored_profile_descriptors": len(descriptors),
        "planned_profiles": logical["planned_profiles"], "literal_profiles_available": len(profiles),
        "presentations_computed": sum(p["status"] == "literal_temporal_presentation_not_harmony" for p in presentations),
        "planned_geometry_candidates": planned_geom, "known_geometry_candidate_subtotal": known_geom,
        "materialized_geometry_candidates": len(geometries),
        "planned_membership_pairs": None if planned_geom is None or logical["planned_profiles"] is None else planned_geom * len(descriptors),
        "planned_membership_relations": planned_rel, "materialized_membership_relations": len(relation_rows),
        "conditional_contour_descriptor_pairs": None if relation_hold else pair_counts["conditional_contour_shape"],
        "withheld_contour_descriptor_pairs": None if relation_hold else pair_counts["withheld_contour_prerequisites"],
        "known_conditional_contour_descriptor_pair_subtotal": pair_counts["conditional_contour_shape"],
        "known_withheld_contour_descriptor_pair_subtotal": pair_counts["withheld_contour_prerequisites"],
        "known_membership_pair_count_subtotal": sum(pair_counts.values()),
        "planned_new_bundles": planned_new, "materialized_new_bundles": len(new_bundles),
        "inherited_bundles": len(inherited), "new_complete_bundles": sum(b["status"] == "complete_all_lane_witness" for b in new_bundles),
        "new_impossible_bundles": sum(b["geometry_condition_status"] == "impossible" for b in new_bundles),
        "new_unknown_bundles": sum(b["geometry_condition_status"] == "unknown" for b in new_bundles),
        "planned_account_templates": len(template_keys), "materialized_account_templates": len(templates),
        "planned_descriptor_bundle_pairs": None if planned_new is None or logical["planned_profiles"] is None else len(descriptors) * (len(inherited) + planned_new),
        "actual_descriptor_bundle_pairs": pair_count,
        "assessed_descriptor_bundle_pairs": 0 if account_hold else sum(len(pairs) for _, assessed, pairs in bundle_keys if assessed),
        "unassessed_actual_descriptor_bundle_pairs": pair_count if account_hold else sum(len(descriptors) - (len(pairs) if assessed else 0) for _, assessed, pairs in bundle_keys),
        "sparse_bundle_account_overrides": sum(len(a["overrides"]) for a in associations),
        "computed_weighted_group_accounts": sum(len(a["accounts"]) for a in weighted_accounts),
        "logical_paths": logical["logical_paths"], "logical_path_key_tuples": logical["logical_path_key_tuples"],
        "logical_function_rows": logical["logical_function_rows"], "unknown_product_groups": logical["unknown_product_groups"],
        "unknown_supplier_catalogs": logical["unknown_supplier_catalogs"],
        "boundary_NCT_rules_computed": 0, "delayed_chains_computed": 0,
        "complete_path_harmony_evaluations": 0, "queried_origins": 0,
        "literal_presentation_inventory_complete": profile_ready,
        "local_contour_relation_inventory_complete": not relation_hold}
    return {"version": VERSION, "contract": _contract(), "binding": deepcopy(scope["binding"]),
        "analysis_span": deepcopy(scope["analysis_span"]), "scope_ref": _ref(scope),
        "hypotheses_ref": deepcopy(index["hypotheses_ref"]), "index_ref": _ref(index), "relations_ref": _ref(relations),
        "grounding_ref": _ref(grounding), "logical_universe": universe,
        "origin_inventory": deepcopy(grounding["origin_inventory"]), "catalog_inventory": deepcopy(grounding["catalog_inventory"]),
        "keys": deepcopy(grounding["keys"]), "source_inventory": deepcopy(grounding["source_inventory"]),
        "descriptor_inventory": descriptor_rows, "geometry_inventory": geometries, "membership_relation_inventory": relation_rows,
        "presentation_inventory": presentations, "inherited_bundle_inventory": inherited,
        "bundle_requests": requests, "bundle_inventory": new_bundles,
        "account_template_inventory": list(templates.values()),
        "descriptor_baseline_accounts": [{"descriptor_id": did, **refs} for did, refs in baselines.items()],
        "bundle_account_overrides": associations, "bundle_weighted_accounts": weighted_accounts,
        "path_groups": groups, "parent_summary": deepcopy(relations["summary"]), "grounding_summary": deepcopy(grounding["summary"]),
        "resource_limits": deepcopy(caps), "summary": summary,
        "status": "temporal_explanations_with_holds" if reasons else "ready_descriptor_local_temporal_explanations",
        "reasons": sorted(set(reasons)), "selected": None, "rank": None, "confidence": None, "flags": _flags(),
        "boundary_NCT_and_delayed_resolution": "unassessed",
        "resource_limit_semantics": "whole_geometry_finite_membership_relation_new_completion_and_distinct_account_template_inventories_no_prefix_not_byte_RSS_or_lifetime_caps",
        "validation_semantics": "owned_serial_immutable_inputs_one_authentic_full_grounding_parent_replay_then_new_geometry_and_exact_account_replay_not_concurrent_atomic_ABA",
        "limits": ["Ordinary descriptor-local passing/neighbor contour credit is not complete NCT or harmony certification.",
            "All three full sounding spans must be inside one exact descriptor; cross-slot boundary roles remain unassessed.",
            "Both direct links must occur in the same actual complete all-raw-lane bundle.",
            "Pooling written members across time is literal presentation, not arpeggio or chord persistence.",
            "Raw membership, unknown/source-held time, every origin and full weighted universe survive.",
            "Accounts from different completions are alternatives and cannot be added as explanation or confidence.",
            "Accent, consonance, boundary NCT, suspension, delayed resolution, cadence and final key/harmony remain unassessed."]}


def build_explanations_prepared(input_session, *, max_geometry_candidates=4096, max_membership_relations=65536,
                                max_new_bundles=4096, max_account_templates=262144, query_work_budget=100000):
    caps = dict(zip(CAPS, (max_geometry_candidates, max_membership_relations, max_new_bundles, max_account_templates, query_work_budget)))
    _caps(caps)
    state = _issued(input_session, _INPUTS, _PreparedInputs)
    owned = indexed._thaw(state.data)
    result = _seal(_body(owned["scope"], owned["index"], owned["relations"], owned["grounding"], caps), PREFIX)
    _issued(input_session, _INPUTS, _PreparedInputs)
    return result


def build_explanations(ir, scope, hypotheses, index, relations, grounding, **caps):
    defaults = dict(zip(CAPS, (4096, 65536, 4096, 262144, 100000)))
    if set(caps) - set(CAPS): raise TypeError("unknown_temporal_limit")
    defaults.update(caps); _caps(defaults)
    return build_explanations_prepared(prepare_inputs(ir, scope, hypotheses, index, relations, grounding), **defaults)


def _header(record):
    indexed._closed(record, {"version", "contract", "binding", "analysis_span", "scope_ref", "hypotheses_ref", "index_ref",
        "relations_ref", "grounding_ref", "logical_universe", "origin_inventory", "catalog_inventory", "keys", "source_inventory",
        "descriptor_inventory", "geometry_inventory", "membership_relation_inventory", "presentation_inventory",
        "inherited_bundle_inventory", "bundle_requests", "bundle_inventory", "account_template_inventory",
        "descriptor_baseline_accounts", "bundle_account_overrides", "bundle_weighted_accounts", "path_groups",
        "parent_summary", "grounding_summary", "resource_limits", "summary", "status", "reasons", "selected", "rank", "confidence",
        "flags", "boundary_NCT_and_delayed_resolution", "resource_limit_semantics", "validation_semantics", "limits",
        "record_id", "record_sha256"}, "temporal_explanations")
    indexed._closed(record["resource_limits"], set(CAPS), "temporal_resource_limits"); _caps(record["resource_limits"])
    for key in ("origin_inventory", "catalog_inventory", "keys", "source_inventory", "descriptor_inventory", "geometry_inventory",
        "membership_relation_inventory", "presentation_inventory", "inherited_bundle_inventory", "bundle_requests", "bundle_inventory",
        "account_template_inventory", "descriptor_baseline_accounts", "bundle_account_overrides", "bundle_weighted_accounts",
        "path_groups", "reasons", "limits"):
        if type(record[key]) is not list: raise ValueError("temporal_inventory_list_required:" + key)


def validate_explanations(ir, scope, hypotheses, index, relations, grounding, record):
    _header(record); frozen._check(record, PREFIX)
    fresh = build_explanations(ir, scope, hypotheses, index, relations, grounding, **record["resource_limits"])
    if not indexed._same(fresh, record): raise ValueError("stale_foreign_modified_or_promoting_temporal_explanations")
    return True


def prepare_explanations(ir, scope, hypotheses, index, relations, grounding, record):
    _header(record); frozen._check(record, PREFIX)
    before, contract = digest([ir, scope, hypotheses, index, relations, grounding, record]), _contract()
    owned_record = deepcopy(record)
    supplier = prepare_inputs(ir, scope, hypotheses, index, relations, grounding)
    fresh = build_explanations_prepared(supplier, **owned_record["resource_limits"])
    if not indexed._same(fresh, owned_record): raise ValueError("stale_foreign_modified_or_promoting_temporal_explanations")
    owned = indexed._thaw(_issued(supplier, _INPUTS, _PreparedInputs).data)
    owned["explanations"] = owned_record
    lookup = {}
    for name, field, parent in (("descriptors", "descriptor_inventory", "explanations"),
        ("profiles", "profile_inventory", "grounding"), ("rows", "row_inventory", "grounding"),
        ("cells", "cell_inventory", "grounding"), ("variants", "variant_inventory", "index"),
        ("presentations", "presentation_inventory", "explanations"), ("accounts", "account_template_inventory", "explanations")):
        lookup[name] = {(r["descriptor_ref"]["record_id"] if name in ("descriptors", "profiles") else r["variant_id"] if name == "variants" else r["record_id"]): i
            for i, r in enumerate(owned[parent][field])}
    all_bundles = owned_record["inherited_bundle_inventory"] + owned_record["bundle_inventory"]
    owned["registered_bundles"] = all_bundles
    lookup["bundles"] = {b["record_id"]: i for i, b in enumerate(all_bundles)}
    lookup["associations"] = {a["bundle_ref"]["record_id"]: i for i, a in enumerate(owned_record["bundle_account_overrides"])}
    lookup["baselines"] = {a["descriptor_id"]: i for i, a in enumerate(owned_record["descriptor_baseline_accounts"])}
    lookup["known_variant_ids"] = {v: True for g in owned["index"]["path_groups"] for slot in g["slots"] for v in slot["variant_ids"]}
    descriptor_relations = defaultdict(list)
    for i, relation in enumerate(owned_record["membership_relation_inventory"]):
        for did in relation["descriptor_ids"]: descriptor_relations[did].append(i)
    lookup["descriptor_relations"] = dict(descriptor_relations)
    if before != digest([ir, scope, hypotheses, index, relations, grounding, record]) or not indexed._same(contract, _contract()):
        raise ValueError("temporal_inputs_or_code_changed_during_owned_session_preparation")
    return _issue(_PreparedExplanations, _SESSIONS, owned, lookup)


def _query(state, descriptor_id, bundle_id, variant_id=None):
    no_admitted_bundle = bundle_id is None and not state.lookups["bundles"]
    if not no_admitted_bundle and (type(bundle_id) is not str or bundle_id not in state.lookups["bundles"]):
        raise ValueError("actual_registered_same_universe_bundle_required")
    if descriptor_id is not None and (type(descriptor_id) is not str or descriptor_id not in state.lookups["descriptors"]):
        raise ValueError("foreign_or_unknown_temporal_descriptor")
    data = state.data; record = data["explanations"]
    bundle = None if no_admitted_bundle else data["registered_bundles"][state.lookups["bundles"][bundle_id]]
    account = presentation = profile = None; relation_rows = []
    descriptor = None if descriptor_id is None else record["descriptor_inventory"][state.lookups["descriptors"][descriptor_id]]
    if descriptor is not None:
        presentation = indexed._thaw(record["presentation_inventory"][state.lookups["presentations"][descriptor["presentation_ref"]["record_id"]]])
        if bundle_id in state.lookups["associations"]:
            association = record["bundle_account_overrides"][state.lookups["associations"][bundle_id]]
            aref = next((a["account_ref"] for a in association["overrides"] if a["descriptor_id"] == descriptor_id), None)
            if aref is None and descriptor_id in state.lookups["baselines"]:
                baseline = record["descriptor_baseline_accounts"][state.lookups["baselines"][descriptor_id]]
                aref = baseline.get(association["default_account_kind"])
            if aref is not None: account = indexed._thaw(record["account_template_inventory"][state.lookups["accounts"][aref["record_id"]]])
        for ridx in state.lookups["descriptor_relations"].get(descriptor_id, ()):
            relation = record["membership_relation_inventory"][ridx]
            relation_rows.append({"relation_ref": _ref(relation), "geometry_ref": indexed._thaw(relation["geometry_ref"]),
                    "status": "conditional_contour_under_this_same_completion" if account is not None and relation["geometry_ref"] in account["supported_geometry_refs"] else
                        "unassessed_contour_axis" if account is None or account["conditional_explanation_note_time"] is None else
                        "withheld_contour_prerequisites" if relation["status"] != "conditional_contour_shape" else "not_satisfied_under_this_completion_not_global_absence",
                "membership_states": indexed._thaw(relation["membership_states"]), "blockers": indexed._thaw(relation["blockers"])})
        if variant_id is not None and descriptor_id in state.lookups["profiles"]:
            original = data["index"]["variant_inventory"][state.lookups["variants"][variant_id]]["variant"]
            p = indexed._thaw(data["grounding"]["profile_inventory"][state.lookups["profiles"][descriptor_id]])
            rs = {rid: indexed._thaw(data["grounding"]["row_inventory"][state.lookups["rows"][rid]]) for rid in p["row_ids"]}
            cs = {cid: indexed._thaw(data["grounding"]["cell_inventory"][state.lookups["cells"][cid]]) for cid in p["cell_ids"]}
            profile = grounded._restore_profile(p, indexed._thaw(original), rs, cs)
    return _seal({"version": VERSION, "contract": _contract(), "explanations_ref": _ref(record),
        "scope_ref": indexed._thaw(record["scope_ref"]), "index_ref": indexed._thaw(record["index_ref"]),
        "grounding_ref": indexed._thaw(record["grounding_ref"]), "symbolic_universe_ref": _ref(record["logical_universe"]),
        "descriptor_id": descriptor_id, "origin_variant_id": variant_id, "bundle_ref": None if bundle is None else _ref(bundle),
        "bundle_origin": "no_admitted_actual_completion" if bundle is None else "inherited_grounding_not_retargeted" if bundle_id.startswith(grounded.BUNDLE_PREFIX) else "new_local_chain_completion",
        "same_complete_all_lane_bundle": bundle is not None and bundle["status"] == "complete_all_lane_witness", "profile": profile,
        "descriptor": None if descriptor is None else indexed._thaw(descriptor), "presentation": presentation,
        "account": account, "relation_assessments": relation_rows,
        "status": "computed_descriptor_local_axes_not_selected" if account is not None else "withheld_temporal_source_or_account_inventory",
        "selected": None, "rank": None, "confidence": None, "flags": _flags(),
        "boundary_NCT_and_delayed_resolution": "unassessed"}, QUERY_PREFIX)


def query_descriptor_prepared(session, descriptor_id, bundle_id):
    state = _issued(session, _SESSIONS, _PreparedExplanations)
    if type(descriptor_id) is not str or descriptor_id not in state.lookups["descriptors"]:
        raise ValueError("explicit_registered_temporal_descriptor_required")
    result = _query(state, descriptor_id, bundle_id)
    _issued(session, _SESSIONS, _PreparedExplanations)
    return result


def query_origin_prepared(session, variant_id, bundle_id):
    state = _issued(session, _SESSIONS, _PreparedExplanations)
    if type(variant_id) is not str or variant_id not in state.lookups["known_variant_ids"]:
        raise ValueError("foreign_or_unknown_temporal_origin")
    did = None if variant_id not in state.lookups["variants"] else state.data["index"]["variant_inventory"][state.lookups["variants"][variant_id]]["profile_ref"]["record_id"]
    result = _query(state, did, bundle_id, variant_id)
    _issued(session, _SESSIONS, _PreparedExplanations)
    return result


def query_descriptor(ir, scope, hypotheses, index, relations, grounding, record, descriptor_id, bundle_id):
    return query_descriptor_prepared(prepare_explanations(ir, scope, hypotheses, index, relations, grounding, record), descriptor_id, bundle_id)


def query_origin(ir, scope, hypotheses, index, relations, grounding, record, variant_id, bundle_id):
    return query_origin_prepared(prepare_explanations(ir, scope, hypotheses, index, relations, grounding, record), variant_id, bundle_id)


def validate_descriptor_query(ir, scope, hypotheses, index, relations, grounding, record, descriptor_id, bundle_id, result):
    frozen._check(result, QUERY_PREFIX)
    if not indexed._same(result, query_descriptor(ir, scope, hypotheses, index, relations, grounding, record, descriptor_id, bundle_id)):
        raise ValueError("stale_foreign_modified_temporal_descriptor_query")
    return True


def validate_origin_query(ir, scope, hypotheses, index, relations, grounding, record, variant_id, bundle_id, result):
    frozen._check(result, QUERY_PREFIX)
    if not indexed._same(result, query_origin(ir, scope, hypotheses, index, relations, grounding, record, variant_id, bundle_id)):
        raise ValueError("stale_foreign_modified_temporal_origin_query")
    return True
