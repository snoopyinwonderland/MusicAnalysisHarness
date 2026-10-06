"""Conditional role explanations for authentic native multi-slot comparisons.

This sidecar preserves raw membership.  Actual links from ONE registered
completion support local contours, adjacent-cut carries and explicit ordinary
roles.  Interval union is not a final NCT, harmony, key or cadence verdict.
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

from . import factor_interval_lattice as native
from . import factor_indexed_hypotheses as owned
from . import factor_expanded_hypotheses as kernels
from . import factor_temporal_explanations as temporal
from . import factor_boundary_explanations as boundary
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "factor-native-role-explanations-0.1.0"
PREFIX = "fmnrole_"
CATEGORIES = temporal.CATEGORIES
_SESSIONS = WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)


def _contract():
    return {"version": VERSION, "native_contract": native._contract(),
        "sources": [{"module": name, "sha256": sha256(Path(path).read_bytes()).hexdigest()}
                    for name, path in [(__name__, __file__),
                        (temporal.__name__, temporal.__file__),
                        (boundary.__name__, boundary.__file__)]]}


def _flags():
    return {**native._flags(), "raw_membership_modified": False,
        "independent_completions_unioned": False, "multicut_carries_supported": False,
        "consonance_or_accent_confirmed": False}


class _PreparedExplanations:
    __slots__ = ("__weakref__",)


@dataclass(frozen=True)
class _State:
    native_session: object
    native_state: object
    data: object
    contract_digest: str
    authentication: str


def _auth(handle, state):
    return hmac.new(_SECRET, owned._encoded([id(handle), id(state), id(state.data),
        id(state.native_session), id(state.native_state), state.contract_digest]), "sha256").hexdigest()


def _issued(handle):
    if type(handle) is not _PreparedExplanations or handle not in _SESSIONS:
        raise ValueError("issued_native_explanation_session_required")
    state = _SESSIONS[handle]
    if type(state) is not _State or type(state.data) is not MappingProxyType:
        raise ValueError("native_explanation_immutable_owned_state_required")
    if native._issued(state.native_session) is not state.native_state:
        raise ValueError("native_explanation_parent_state_identity_changed")
    if state.contract_digest != digest(_contract()) or not hmac.compare_digest(state.authentication, _auth(handle, state)):
        raise ValueError("stale_or_modified_native_explanation_session")
    return state


def prepare_explanations(native_session, comparison):
    """Recompute the exact native request; saved seals alone grant no authority."""
    native_state = native._issued(native_session)
    contract_digest = digest(_contract())
    before = digest(comparison)
    kernels._check(comparison, native.COMPARISON_PREFIX)
    fresh = native.compare_prepared(native_session, comparison["selectors"],
        comparison["bundle_ref"]["record_id"], **comparison["resource_limits"])
    if not owned._same(fresh, comparison) or before != digest(comparison):
        raise ValueError("stale_foreign_or_modified_native_comparison")
    scope = owned._thaw(native_state.data["scope"])
    origin_ids = {r["record_id"] for path in fresh["paths"] for r in path["origin_refs"]}
    origins = {key: owned._thaw(native_state.lookups["origins"][key]) for key in sorted(origin_ids)}
    bundle = native._registered_bundle(native_session, fresh["bundle_ref"]["record_id"])
    data = owned._freeze(deepcopy({"scope": scope, "origins": origins,
                                  "bundle": bundle, "comparison": fresh}))
    if (native._issued(native_session) is not native_state
            or contract_digest != digest(_contract()) or before != digest(comparison)):
        raise ValueError("native_explanation_inputs_changed_during_preparation")
    handle = _PreparedExplanations()
    state = _State(native_session, native_state, data, contract_digest, "")
    object.__setattr__(state, "authentication", _auth(handle, state))
    _SESSIONS[handle] = state
    return handle


def _span(a, b):
    return {"start": q(a), "end": q(b)}


def _clips(sounds, extent):
    return [{"sound_ref": s["sound_ref"], "span": clip} for s in sounds
            if (clip := kernels._overlap(s["span"], extent)) is not None]


def _inside(sound, extent):
    a, b = span_bounds(sound["span"])
    lo, hi = span_bounds(extent)
    return lo <= a < b <= hi


def _step(a, b):
    motion = kernels._move(a, b)
    return bool(motion is not None and abs(motion["diatonic_steps"]) == 1
        and f(motion["semitones"]) in (-2, -1, 1, 2)
        and motion["diatonic_steps"] * f(motion["semitones"]) > 0)


def _chain(start, sounds, links):
    """Follow the unique actual continuation only to its FIRST pitch change."""
    route, required, visited = [start], [], {start["sound_ref"]}
    while route[-1]["sound_ref"] in links:
        nxt = sounds[links[route[-1]["sound_ref"]]]
        if nxt["sound_ref"] in visited:
            raise ValueError("registered_completion_cycle")
        required.append([route[-1]["sound_ref"], nxt["sound_ref"]])
        route.append(nxt)
        visited.add(nxt["sound_ref"])
        if not boundary._same(start, nxt):
            return route, required, nxt
    return route, required, None


def _clause(role, slots, origins, sounds, links, predicates, unknown, clips, **extra):
    blockers = [reason for sound in sounds for reason in kernels._source_blockers(sound)]
    blockers.extend(sound["sound_ref"] + ":" + reason for sound in sounds
                    for reason in temporal._guard_codes(sound))
    blockers.extend("hypothesis:" + reason for origin in origins for reason in origin["blockers"])
    unknown = sorted(set([*unknown, *blockers]))
    failures = sorted(k for k, value in predicates.items() if value is not True)
    satisfied = None if unknown else not failures
    body = {"version": VERSION, "role": role, "slot_indices": slots,
        "origin_refs": [kernels._ref(o) for o in origins],
        "sound_refs": [s["sound_ref"] for s in sounds],
        "source_note_refs": [n for s in sounds for n in s["source_note_refs"]],
        "full_sound_spans": [deepcopy(s["span"]) for s in sounds],
        "actual_required_links": deepcopy(links), "prerequisites": predicates,
        "qualified": not unknown, "satisfied": satisfied,
        "status": "unassessed" if satisfied is None else "supported" if satisfied else "failed",
        "blockers": unknown, "failed_prerequisites": failures,
        "proposed_clips": deepcopy(clips), "clips": deepcopy(clips) if satisfied else [],
        "interpretation": "conditional_role_geometry_not_final_NCT", **extra}
    body["geometry_id"] = "fmnrolegeom_" + digest({
        "role": role, "sound_refs": body["sound_refs"], "full_sound_spans": body["full_sound_spans"],
        "slot_spans": [o["span"] for o in origins], "actual_required_links": body["actual_required_links"],
        "boundary_time": extra.get("boundary_time")})[:24]
    return body


def _local(path, origins, sounds, links):
    rows = []
    for xref, yref in sorted(links.items()):
        if yref not in links:
            continue
        triple = [sounds[sid] for sid in (xref, yref, links[yref])]
        a, b, c = triple
        moves = [kernels._move(a, b), kernels._move(b, c)]
        neighbor = boundary._same(a, c)
        contour = _step(a, b) and _step(b, c) and (neighbor or
            moves[0]["diatonic_steps"] == moves[1]["diatonic_steps"])
        for pos, origin in enumerate(origins):
            if kernels._overlap(b["span"], origin["span"]) is None:
                continue
            unknown = [] if all(_inside(s, origin["span"]) for s in triple) else ["local_full_triple_not_inside_one_slot"]
            predicates = {"ordinary_contour": contour,
                "member_nonmember_member": [kernels._state(s, origin) for s in triple] ==
                    ["member", "nonmember_not_confirmed_nct", "member"]}
            rows.append(_clause("local_neighbor" if neighbor else "local_passing", [pos], [origin], triple,
                [[xref, yref], [yref, links[yref]]], predicates, unknown, _clips([b], origin["span"]), motions=moves))
    return rows


def _boundary(origins, sounds, links):
    rows = []
    for pos, (left, right) in enumerate(zip(origins, origins[1:])):
        cut = f(right["span"]["start"])
        envelope = _span(f(left["span"]["start"]), f(right["span"]["end"]))
        for source in sounds.values():
            a, b = span_bounds(source["span"])
            if not a < cut <= b:
                continue
            held = a < cut < b
            nxt = sounds.get(links.get(source["sound_ref"]))
            reattack = (b == cut and nxt is not None and f(nxt["span"]["start"]) == cut
                        and boundary._same(source, nxt))
            carry = held or reattack
            # Held anticipation has an intrinsic crossing and no fake self-edge.
            anticip = [source] if held or not reattack else [source, nxt]
            alinks = [] if not reattack else [[source["sound_ref"], nxt["sound_ref"]]]
            unknown = [] if all(_inside(s, envelope) for s in anticip) else ["boundary_full_span_outside_adjacent_pair_multicut_unassessed"]
            attack_inside = f(left["span"]["start"]) <= a < cut
            rows.append(_clause("boundary_anticipation", [pos, pos + 1], [left, right], anticip, alinks,
                {"actual_boundary_carry": carry, "preparation_attack_inside_left": attack_inside,
                 "left_nonmember": kernels._state(source, left) == "nonmember_not_confirmed_nct",
                 "right_member": kernels._state(anticip[-1], right) == "member"}, unknown,
                _clips([source], left["span"]), boundary_time=q(cut), carry_kind="held" if held else "reattack" if reattack else "not_observed"))
            route, required, endpoint = _chain(source, sounds, links)
            carries = route[:-1] if endpoint is not None else route
            crossing = [s for s in carries if kernels._overlap(s["span"], right["span"]) is not None]
            unknown = [] if all(_inside(s, envelope) for s in route) else ["boundary_full_span_outside_adjacent_pair_multicut_unassessed"]
            predicates = {"actual_boundary_carry": carry, "preparation_attack_inside_left": attack_inside,
                "left_member": kernels._state(source, left) == "member",
                "right_nonmember_carry": bool(crossing) and all(kernels._state(s, right) == "nonmember_not_confirmed_nct" for s in crossing),
                "first_changed_downward_member_inside_right": endpoint is not None
                    and cut <= f(endpoint["span"]["start"]) < f(right["span"]["end"])
                    and boundary._ordinary_down(source, endpoint) and kernels._state(endpoint, right) == "member"}
            rows.append(_clause("boundary_suspension", [pos, pos + 1], [left, right], route, required,
                predicates, unknown, _clips(carries, right["span"]), boundary_time=q(cut),
                carry_kind="held" if held else "reattack" if reattack else "not_observed",
                endpoint_sound_ref=None if endpoint is None else endpoint["sound_ref"]))
    return rows


def _ordinary(path, origins, sounds):
    rows, templates = [], []
    for pos, context in enumerate(path["transition_contexts"]):
        shape, strategy = context["function_shape"], context["ordinary_strategy"]
        if shape is None:
            templates.append({"cut_index": pos, "satisfied": None, "reason": "no_explicit_transition_assumption"})
            continue
        left, right = origins[pos:pos + 2]
        cut, end = span_bounds(right["span"])
        envelope = _span(f(left["span"]["start"]), end)
        unavailable = ["hypothesis:" + reason for origin in (left, right) for reason in origin["blockers"]]
        if any(origin["root"] is None or origin["members"] is None for origin in (left, right)):
            unavailable.append("ordinary_source_or_target_spelling_unavailable")
        cuts_rows, truths = [], []
        for role in strategy["role_assessments"]:
            role_rows = []
            for occurrence in role["occurrences"]:
                route = [sounds[sid] for sid in occurrence["route_sound_refs"]]
                endpoint = sounds.get(occurrence["endpoint_sound_ref"])
                unknown = [] if all(_inside(s, envelope) for s in route) else ["ordinary_full_route_outside_adjacent_pair_multicut_unassessed"]
                predicates = {"explicit_source_target_shape": shape["status"] == "conditional_function_shape",
                    "source_member": kernels._state(route[0], left) == "member",
                    "native_first_change_ordinary_motion": occurrence["satisfied_under_this_bundle"],
                    "endpoint_attack_inside_right": endpoint is not None and cut <= f(endpoint["span"]["start"]) < end}
                row = _clause("delayed_ordinary_" + role["role"], [pos, pos + 1], [left, right], route,
                    occurrence["actual_required_links"], predicates, unknown,
                    _clips(route[:-1] if endpoint is not None else route, right["span"]),
                    boundary_time=q(cut), endpoint_sound_ref=occurrence["endpoint_sound_ref"],
                    native_function_context_ref=kernels._ref(context),
                    key_projection=deepcopy(shape["key_projection"]), timing=occurrence["timing"])
                role_rows.append(row); cuts_rows.append(row)
            if role["critical_pitch"] is None:
                unavailable.append("ordinary_critical_pitch_identity_unavailable:" + role["role"])
            truth = (None if unavailable else True if any(r["satisfied"] is True for r in role_rows)
                     else None if any(r["satisfied"] is None for r in role_rows) else False)
            truths.append(truth)
        whole = None if unavailable else False if False in truths else None if None in truths else bool(truths)
        for row in cuts_rows:
            row["whole_ordinary_template_satisfied"] = whole
            row["all_doublings_individually_required"] = False
            if whole is not True:
                row["clips"] = []
        rows.extend(cuts_rows)
        templates.append({"cut_index": pos, "satisfied": whole, "role_truths": truths,
                          "prerequisite_blockers": sorted(set(unavailable)),
                          "native_function_context_ref": kernels._ref(context),
                          "strategy": "role_occurrence_OR_then_roles_AND_same_bundle"})
    return rows, templates


def _account(path, origins, sounds, rows, assessed):
    proposals = defaultdict(list)
    for row in rows:
        for clip in row["clips"]:
            proposals[clip["sound_ref"]].append(clip["span"])
    unions = {sid: temporal._union(spans) for sid, spans in proposals.items()}
    totals = {category: Fraction() for category in CATEGORIES}
    credited = defaultdict(list)
    guarded_nonmember = Fraction()
    for profile, origin in zip(path["profiles"], origins):
        for row in profile["rows"]:
            sid = row["sound_ref"]
            a, b = span_bounds(row["observed_span"])
            duration = b - a
            if origin["blockers"] or temporal._guard_codes(sounds[sid]):
                totals["source_or_hypothesis_unsupported"] += duration
            elif row["state"] == "member":
                totals["source_guarded_member"] += duration
            elif row["state"] == "spelling_unresolved":
                totals["membership_unknown"] += duration
            elif not assessed:
                totals["unassessed_nonmember"] += duration
            else:
                guarded_nonmember += duration
                clips = [_span(max(a, x), min(b, y)) for x, y in
                         (span_bounds(s) for s in unions.get(sid, ())) if max(a, x) < min(b, y)]
                clipped = temporal._union(clips)
                credit = temporal._duration(clipped)
                if credit > duration:
                    raise ValueError("native_role_credit_exceeds_guarded_nonmember")
                credited[sid].extend(clipped)
                totals["conditional_explained_nonmember"] += credit
                totals["unexplained_nonmember_under_this_completion"] += duration - credit
    final_union = {sid: temporal._union(spans) for sid, spans in credited.items() if spans}
    total = f(path["whole_path_account"]["raw_total_note_time_quarters"])
    explained = totals["conditional_explained_nonmember"]
    if sum(totals.values(), Fraction()) != total or sum((temporal._duration(s) for s in final_union.values()), Fraction()) != explained:
        raise ValueError("native_role_union_raw_note_time_loss")
    return {"raw_total_note_time_quarters": q(total),
        "raw_state_note_time_quarters": deepcopy(path["whole_path_account"]["raw_state_note_time_quarters"]),
        "note_time_quarters": {k: q(v) for k, v in totals.items()},
        "conditional_explanation_note_time_quarters": q(explained) if assessed else None,
        "guarded_nonmember_note_time_quarters": q(guarded_nonmember) if assessed else None,
        "explained_intervals_by_sound": [{"sound_ref": sid, "spans": spans} for sid, spans in sorted(final_union.items())],
        "raw_time_conserved": True, "union_counted_once": True,
        "status": "conditional_account_not_NCT_verdict" if assessed else "unassessed_completion_raw_time_preserved"}


def _plan(scope, paths, selectors=None):
    n = len(scope["sound_facts"])
    # The exact request remains available even when native work was held.
    sizes = [len(s["origin_ids"]) for s in selectors] if selectors is not None else [len(p["partition"]) for p in paths]
    slots = sum(sizes)
    cuts = sum(max(0, size - 1) for size in sizes)
    local = slots * n
    boundary_count = cuts * 2 * n
    ordinary = cuts * 2 * n
    clauses = local + boundary_count + ordinary
    routes = (boundary_count + ordinary) * (n + 1)
    intersections = slots * n
    # Upper bound for sorting/merging and every row's clipped union scan.
    union_endpoints = 2 * clauses * (n + 1)
    union_visits = (intersections + 1) * union_endpoints
    references = sum(len(s["source_note_refs"]) for s in scope["sound_facts"])
    max_refs = max((len(s["source_note_refs"]) for s in scope["sound_facts"]), default=0)
    closure = n + references if sizes else 0
    # Every clause emits its own source-note closure; long tie chains must not
    # be charged once then copied freely across many hypotheses/routes.
    reference_visits = local * 3 * max_refs + (boundary_count + ordinary) * references
    work = closure + reference_visits + local * 4 + routes * 3 + intersections + union_visits
    return {"source_closure_items": closure, "planned_slot_occurrences": slots,
        "planned_internal_cuts": cuts, "clause_upper_bound": clauses,
        "actual_chain_visit_upper_bound": routes, "profile_intersection_upper_bound": intersections,
        "union_endpoint_upper_bound": union_endpoints, "union_visit_upper_bound": union_visits,
        "source_reference_visit_upper_bound": reference_visits,
        "planned_query_work": work,
        "semantics": "conservative_whole_request_logical_bounds_not_CPU_RSS_or_accuracy"}


def explain_prepared(handle, *, query_work_budget=1000000):
    native._integer(query_work_budget, "query_work_budget")
    state = _issued(handle)
    data = owned._thaw(state.data)
    scope, comparison, bundle = (data[k] for k in ("scope", "comparison", "bundle"))
    plan = _plan(scope, comparison["paths"], comparison["selectors"])
    reasons = []
    if comparison["status"] == "whole_comparison_hold":
        reasons.append("native_comparison_unavailable")
    if plan["planned_query_work"] > query_work_budget:
        reasons.append("whole_explanation_work_exceeds_budget_no_prefix")
    paths = []
    if not reasons:
        sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
        links = dict(bundle["materialized_witness_links"])
        assessed = scope["context_sound_inventory_complete"] and bundle["status"] == "complete_all_lane_witness"
        for path in comparison["paths"]:
            origins = [data["origins"][r["record_id"]] for r in path["origin_refs"]]
            rows = []; templates = []
            if assessed:
                rows.extend(_local(path, origins, sounds, links))
                rows.extend(_boundary(origins, sounds, links))
                ordinary, templates = _ordinary(path, origins, sounds)
                rows.extend(ordinary)
            clauses = [kernels._seal({**row, "native_path_ref": kernels._ref(path),
                "key_ref": deepcopy(path["key_ref"]), "bundle_ref": deepcopy(path["bundle_ref"]),
                "flags": _flags()}, "fmnroleclause_") for row in rows]
            paths.append(kernels._seal({"native_path_ref": kernels._ref(path),
                "logical_tuple_ref": kernels._ref(path["logical_tuple"]),
                "raw_account_pointer": {"parent_path_ref": kernels._ref(path),
                    "field": "whole_path_account", "sha256": digest(path["whole_path_account"])},
                "origin_refs": deepcopy(path["origin_refs"]), "partition": deepcopy(path["partition"]),
                "transition_assumptions": deepcopy(path["logical_tuple"]["transition_assumptions"]),
                "key_ref": deepcopy(path["key_ref"]), "bundle_ref": deepcopy(path["bundle_ref"]),
                "clauses": clauses, "ordinary_templates": templates,
                "account": _account(path, origins, sounds, clauses, assessed),
                "status": "assessed_same_completion" if assessed else "unassessed_completion",
                "selected": None, "rank": None, "confidence": None, "flags": _flags()}, "fmnrolepath_"))
    counts = Counter(row["status"] for p in paths for row in p["clauses"])
    clauses = [row for p in paths for row in p["clauses"]]
    result = kernels._seal({"version": VERSION, "contract": _contract(),
        "native_comparison_ref": kernels._ref(comparison), "scope_ref": deepcopy(comparison["scope_ref"]),
        "native_request": {key: deepcopy(comparison[key]) for key in
            ("selectors", "resource_limits", "status", "reasons", "summary", "query_plan")},
        "logical_universe": deepcopy(comparison["logical_universe"]),
        "lattice_ref": deepcopy(comparison["lattice_ref"]), "bundle_ref": deepcopy(comparison["bundle_ref"]),
        "analysis_span": deepcopy(comparison["analysis_span"]), "paths": paths,
        "query_plan": plan, "resource_limits": {"query_work_budget": query_work_budget},
        "summary": {"planned_paths": comparison["summary"]["planned_selectors"],
            "native_computed_paths": len(comparison["paths"]), "computed_paths": len(paths),
            "planned_clause_upper_bound": plan["clause_upper_bound"],
            "unique_geometry_count": len({row["geometry_id"] for row in clauses}),
            "role_clause_occurrences": dict(sorted(Counter(row["role"] for row in clauses).items())),
            "evaluated_clauses": sum(counts.values()), "qualified_clauses": sum(r["qualified"] for p in paths for r in p["clauses"]),
            "satisfied_clauses": counts["supported"], "failed_clauses": counts["failed"],
            "unassessed_clauses": counts["unassessed"],
            "credit_sound_occurrences": sum(len(p["account"]["explained_intervals_by_sound"]) for p in paths),
            "withheld_paths": comparison["summary"]["planned_selectors"] - len(paths)},
        "status": "whole_explanation_hold" if reasons else "computed_native_role_explanations_not_selected",
        "reasons": reasons, "selected": None, "rank": None, "confidence": None, "flags": _flags(),
        "limitations": ["Conditional geometry is not final NCT, consonance, accent or musical correctness.",
            "Multiple-cut carries, exceptions and unsubmitted paths remain unassessed.",
            "Ordinary role OR/AND does not require every doubling; key/function/cadence are not promoted.",
            "Native raw profiles and earlier experimental outputs are unchanged."]}, PREFIX)
    _issued(handle)
    return result


def validate_explanation_prepared(handle, record):
    kernels._check(record, PREFIX)
    fresh = explain_prepared(handle, **record["resource_limits"])
    if not owned._same(fresh, record):
        raise ValueError("stale_foreign_or_modified_native_explanation")
    return True
