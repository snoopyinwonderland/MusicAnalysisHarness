"""Label-blind segmental scoring and exact DAG decoding of stored candidates.

This is an UNTRAINED research baseline, not calibrated confidence or a full
Roman/NCT/voice validator. References are confined to the separate trial.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json

from .harmony_candidate_recall import fraction, rational, spelling
from .harmony_lattice_recall import signature, validate_binding

VERSION = "harmony-scored-decoder-0.1.0"
FEATURE_VERSION = "stored-spelled-music-features-0.1.0"
SEGMENT_FEATURES = (
    "nonmember_exposure", "unresolved_spelling_exposure", "blocker_exposure",
    "missing_member_fraction", "missing_root", "extra_member_complexity",
    "unknown_root", "segment_count",
)
TRANSITION_FEATURES = ("unanchored_change", "root_motion_distance", "member_turnover")
UNAVAILABLE_FEATURES = (
    "consistent_voice_nct_explanation", "seventh_resolution", "local_key",
    "applied_chord_resolution", "metric_boundary", "structural_bass",
)
# Fixed BEFORE the first corpus evaluation. These are heuristic costs, NOT
# fitted DCML weights, universal musical laws, or a preference for one piece.
DEFAULT_WEIGHTS = {
    "nonmember_exposure": Fraction(1),
    "unresolved_spelling_exposure": Fraction(1, 2),
    "blocker_exposure": Fraction(1, 4),
    "missing_member_fraction": Fraction(3, 10),
    "missing_root": Fraction(1, 10),
    "extra_member_complexity": Fraction(1, 10),
    "unknown_root": Fraction(1, 5),
    "segment_count": Fraction(3, 200),
    "unanchored_change": Fraction(1, 25),
    "root_motion_distance": Fraction(3, 200),
    "member_turnover": Fraction(1, 50),
}


@dataclass(frozen=True)
class Observation:
    event_id: str
    start: Fraction
    end: Fraction
    pitch: tuple | None
    source_note_ids: tuple


@dataclass(frozen=True)
class Edge:
    group_id: str
    start_index: int
    end_index: int
    start: Fraction
    end: Fraction
    signature: tuple
    features: dict
    attack_spellings: frozenset
    source_event_ids: tuple
    blockers: tuple
    adapter: dict


@dataclass(frozen=True)
class Problem:
    points: tuple
    edges: tuple
    max_segments: int
    total_note_time: Fraction
    status: str
    zero_duration_event_ids: tuple = ()


def weights_contract(weights=None):
    values = dict(DEFAULT_WEIGHTS if weights is None else weights)
    if set(values) != set(DEFAULT_WEIGHTS):
        raise ValueError("unknown_or_missing_weight")
    if any(type(v) not in (int, Fraction) for v in values.values()):
        raise ValueError("weights_must_be_exact_rationals")
    return {k: Fraction(v) for k, v in values.items()}


def observations(events):
    result, seen = [], set()
    for event in events:
        eid = event["sounding_event_id"]
        a, b = fraction(event["span"]["start"]), fraction(event["span"]["end"])
        if eid in seen or b < a:
            raise ValueError("duplicate_or_negative_sounding_event")
        seen.add(eid)
        if fraction(event["sounding_duration"]) != b-a or not event["source_note_ids"]:
            raise ValueError("sounding_event_source_or_duration_mismatch")
        pitch = event.get("pitch") or {}
        alter = fraction(pitch["alter"]) if "alter" in pitch else None
        token = None if alter is None or alter.denominator != 1 else spelling((pitch["step"], int(alter)))
        result.append(Observation(eid, a, b, token, tuple(event["source_note_ids"])))
    return tuple(result)


def prepare(bundle, search):
    """Only score input + previously label-blind inventory; no gold argument."""
    points = validate_binding(bundle, search, bundle["sample"]["span"])
    if points is None:
        return Problem((), (), 0, Fraction(), search["lattice_status"])
    budget = search["budgets"]["max_segments"]
    if type(budget) is not int or budget <= 0:
        raise ValueError("invalid_segment_budget")
    groups = search["semantic_groups"]
    if len({g["group_id"] for g in groups}) != len(groups):
        raise ValueError("duplicate_semantic_group")
    observed = observations(bundle["stages"]["lattice"]["events"])
    zero_refs = tuple(o.event_id for o in observed if o.start == o.end)
    context_duration = points[-1]-points[0]
    total = sum((max(Fraction(), min(o.end, points[-1])-max(o.start, points[0]))
                 for o in observed), Fraction())
    if total <= 0:
        return Problem(tuple(points), (), budget, total, "no_positive_sounding_exposure", zero_refs)
    # Observation summaries depend on geometry, not candidate origin/provider.
    geometry = {}
    edges = []
    for g in sorted(groups, key=lambda item: item["group_id"]):
        a, b = points[g["from"]], points[g["to"]]
        if (a, b) not in geometry:
            active = [(o, min(o.end, b)-max(o.start, a)) for o in observed if o.start < b and a < o.end]
            exposure = sum((dur for _, dur in active), Fraction())
            # Zero-duration notation is preserved in event_states/source refs,
            # but is not evidence of positive sounding exposure or an attack
            # with known performed timing. Do not stretch it into a duration.
            known = frozenset(o.pitch for o, dur in active if o.pitch is not None and dur > 0)
            attacks = frozenset(o.pitch for o, dur in active if o.start == a and o.pitch is not None and dur > 0)
            geometry[a, b] = active, exposure, known, attacks
        active, exposure, known, attacks = geometry[a, b]
        obj = g["objective_increment"]
        if fraction(obj["total_note_time"]) != exposure or set(g["event_states"]) != {o.event_id for o, _ in active}:
            raise ValueError("candidate_observation_binding_mismatch")
        sig = signature((g["root_spelling"], g["members"]))
        root, members = sig
        for o, _ in active:
            expected = "spelling_unresolved" if o.pitch is None else "member" if o.pitch in members else "nonmember_not_confirmed_nct"
            if g["event_states"][o.event_id] != expected:
                raise ValueError("candidate_membership_observation_mismatch")
        raw = sum((dur for o, dur in active if o.pitch is not None and o.pitch not in members), Fraction())
        unresolved = sum((dur for o, dur in active if o.pitch is None), Fraction())
        blocked = exposure if g["candidate_blockers"] else Fraction()
        if any(fraction(obj[name]) != val for name, val in (
            ("raw_nonmember_note_time", raw), ("spelling_unresolved_note_time", unresolved), ("blocked_note_time", blocked),
        )):
            raise ValueError("candidate_objective_observation_mismatch")
        time_weight = (b-a)/context_duration
        # Unknown observations stay unavailable, not a false claim of absence.
        presence_available = bool(known) and unresolved == 0
        features = {
            "nonmember_exposure": raw/total,
            "unresolved_spelling_exposure": unresolved/total,
            "blocker_exposure": blocked/total,
            "missing_member_fraction": (time_weight*Fraction(len(set(members)-known), len(members))
                                        if presence_available and members else None),
            "missing_root": time_weight*int(root not in known) if presence_available and root is not None else None,
            "extra_member_complexity": time_weight*max(0, len(members)-3),
            "unknown_root": time_weight*int(root is None),
            "segment_count": Fraction(1),
            **{k: None for k in UNAVAILABLE_FEATURES},
        }
        edges.append(Edge(g["group_id"], g["from"], g["to"], a, b, sig, features, attacks,
                          tuple(sorted(o.event_id for o, _ in active)), tuple(g["candidate_blockers"]),
                          dict(g["adapter_reading_key"])))
    return Problem(tuple(points), tuple(edges), budget, total, "ready", zero_refs)


def pitch_class(token):
    return ({"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[token[0]]+token[1]) % 12


def transition(previous, edge):
    """Observational transition cost; NOT function, voice leading or cadence."""
    if previous is None:
        return {name: Fraction() for name in TRANSITION_FEATURES}
    old_root, old_members = previous; root, members = edge.signature
    changed = previous != edge.signature
    introduced = set(members)-set(old_members)
    # Sustained tie continuations are not new attacks. Lack of an attack is a
    # soft cost: anticipation/pedal/arpeggiation may still justify a change.
    anchored = bool(introduced & edge.attack_spellings)
    distance = None
    if root is not None and old_root is not None:
        delta = abs(pitch_class(root)-pitch_class(old_root))
        distance = Fraction(min(delta, 12-delta), 6)
    union = set(old_members) | set(members)
    return {"unanchored_change": Fraction(int(changed and not anchored)),
            "root_motion_distance": distance,
            "member_turnover": Fraction(len(set(old_members)^set(members)), len(union)) if union else None}


def feature_cost(features, weights):
    return sum((weights[name]*value for name, value in features.items()
                if name in weights and value is not None), Fraction())


def decode(problem, weights=None, *, include_transitions=True, transition_budget=2_000_000):
    """Exact under the declared first-order score/cap, unless budget abstains.

    A state retains endpoint, segment count AND previous spelled signature.
    No prefix/output beam or 24-path pruning. Resource exhaustion emits no
    approximate winner, and does not drop an old abstention.
    """
    weights = weights_contract(weights)
    if type(transition_budget) is not int or transition_budget <= 0:
        raise ValueError("invalid_transition_budget")
    if problem.status != "ready":
        return {"status": problem.status, "selected": None, "transitions": 0,
                "exact_optimum_under_declared_score": False}
    outgoing = [[] for _ in problem.points]
    by_id = {}
    emissions = {}
    for edge in problem.edges:
        outgoing[edge.start_index].append(edge)
        by_id[edge.group_id] = edge
        emissions[edge.group_id] = feature_cost(edge.features, weights)
    states = [dict() for _ in problem.points]
    states[0][(0, None)] = (Fraction(), ())
    transitions = 0; transition_cache = {}
    for index, current in enumerate(states):
        for (count, previous), (cost, ids) in sorted(current.items(), key=lambda item: repr(item[0])):
            if count >= problem.max_segments:
                continue
            for edge in outgoing[index]:
                transitions += 1
                if transitions > transition_budget:
                    return {"status": "transition_budget_abstention", "selected": None,
                            "transitions": transitions-1, "exact_optimum_under_declared_score": False}
                tkey = previous, edge.signature, edge.attack_spellings
                if tkey not in transition_cache:
                    transition_cache[tkey] = feature_cost(transition(previous, edge), weights) if include_transitions else Fraction()
                candidate = cost+emissions[edge.group_id]+transition_cache[tkey], ids+(edge.group_id,)
                key = count+1, edge.signature
                existing = states[edge.end_index].get(key)
                if existing is None or candidate < existing:
                    states[edge.end_index][key] = candidate
    if not states[-1]:
        return {"status": "no_complete_path_under_segment_cap", "selected": None,
                "transitions": transitions, "exact_optimum_under_declared_score": True}
    cost, ids = min(states[-1].values())
    selected = [by_id[i] for i in ids]
    details, previous = [], None
    for edge in selected:
        tf = transition(previous, edge)
        details.append({"semantic_group_ref": edge.group_id, "span": {"start": rational(edge.start), "end": rational(edge.end)},
                        "root_spelling": edge.signature[0], "members": edge.signature[1],
                        "source_event_ids": edge.source_event_ids, "candidate_blockers": edge.blockers,
                        "adapter_reading_key": edge.adapter,
                        "features": {k: None if v is None else rational(v) for k, v in edge.features.items()},
                        "availability": {k: v is not None for k, v in edge.features.items()},
                        "transition_features": {k: None if v is None else rational(v) for k, v in tf.items()},
                        "segment_cost": rational(emissions[edge.group_id]),
                        "transition_cost": rational(feature_cost(tf, weights) if include_transitions else Fraction())})
        previous = edge.signature
    payload = json.dumps(ids, separators=(",", ":")).encode()
    return {"status": "selected_untrained_hypothesis", "transitions": transitions,
            "exact_optimum_under_declared_score": True,
            "selected": {"proposal_id": "scored_"+hashlib.sha256(payload).hexdigest()[:24],
                         "score_cost": rational(cost), "segments": details, "confidence": None,
                         "source_labels_used_for_selection": False, "human_validated": False,
                         "music_constraints_fully_validated": False,
                         "transition_features_enabled": include_transitions}}


def evaluation_path(result):
    chosen = result["selected"]
    if chosen is None:
        return None
    return {"proposal_id": chosen["proposal_id"], "segments": [
        {"start": fraction(s["span"]["start"]), "end": fraction(s["span"]["end"]),
         "signature": signature((s["root_spelling"], s["members"])), "group_id": s["semantic_group_ref"]}
        for s in chosen["segments"]]}
