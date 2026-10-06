"""Partition-invariant harmonic-run scoring, with source-bound observations.

This research decoder never receives annotation/key/function answers. Adjacent
identical spelled signatures share one run score, even if the inventory only
contains smaller edges. No source event or candidate is removed. NCT evidence
is a conditional, bounded bonus, not an exemption or a confirmed note label.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from bisect import bisect_right
from dataclasses import dataclass, field
from fractions import Fraction as F
import hashlib
import json
from math import lcm

from .harmony_candidate_recall import fraction, rational
from .harmony_progression_search import _hash
from .harmony_reading_voice_context import prepare_voice_geometry, spelled_height
from .harmony_scored_decoder import (
    DEFAULT_WEIGHTS, feature_cost, observations, prepare, transition,
)

VERSION = "harmony-evidence-scoring-0.1.0"
FEATURE_VERSION = "source-bound-harmonic-run-features-0.1.0"
BASE_WEIGHTS = {k: v for k, v in DEFAULT_WEIGHTS.items() if k != "segment_count"}
BASE_WEIGHTS["harmonic_run_count"] = DEFAULT_WEIGHTS["segment_count"]
EVIDENCE_WEIGHTS = {
    "key_signature_foreign_member": F(1, 10),
    "metric_nonmember_exposure": F(1, 4),
    "lowest_nonmember_exposure": F(1, 4),
    "conditional_step_ornament_exposure": F(-1, 2),
}
LIMITS = [
    "Key signature is observation, not an inferred global/local key.",
    "Lowest sounding pitch is not structural bass or confirmed inversion.",
    "Unique explicit IR voice is not verified contrapuntal voice identity.",
    "Passing/neighbor geometry is conditional on THIS complete harmonic run.",
    "Raw nonmember exposure is retained; no optimistic NCT membership exemption.",
    "No applied-chord/seventh resolution, modulation, cadence or Roman inference here.",
    "Original candidate inventory, spelling, raw segment cap and abstentions remain.",
]


@dataclass
class Evidence:
    events: tuple
    measures: tuple
    rows: dict
    neighbors: dict
    voice_statuses: dict
    source_ir_content_sha256: str
    _measure_times: tuple = field(default=(), repr=False)
    _metric_cache: dict = field(default_factory=dict, repr=False)
    _feature_cache: dict = field(default_factory=dict, repr=False)


def pitch_token(p):
    a = fraction(p.get("alter", rational(F())))
    return (p["step"], int(a)) if a.denominator == 1 and p.get("step") in tuple("CDEFGAB") else None


def source_evidence(ir, bundle):
    """Bind the full pinned IR, but consume only Core events/measures/identity.

    Extensions, source annotations, titles and mode_hint never enter scoring.
    Invalid tied clocks withhold voice-pattern evidence, not the whole score.
    """
    sha = _hash(ir)
    if (sha != bundle["input_ir_content_sha256"]
            or ir["ir_document_id"] != bundle["parent_ir_document_id"]
            or ir["score"]["score_id"] != bundle["score_id"]):
        raise ValueError("full_ir_context_binding_mismatch")
    events = observations(bundle["stages"].get("lattice", {}).get("events", []))
    raw_events = {s["sounding_event_id"]: s for s in bundle["stages"].get("lattice", {}).get("events", [])}
    sounds = {s["sounding_event_id"]: s for s in ir["sounding_events"]}
    if len(sounds) != len(ir["sounding_events"]):
        raise ValueError("duplicate_source_sound")
    for e in events:
        s = sounds.get(e.event_id)
        if s is None:
            raise ValueError("missing_source_sound")
        x, y = fraction(s["span"]["start"]), fraction(s["span"]["end"])
        stored = raw_events[e.event_id]
        if (e.source_note_ids != tuple(s["source_note_ids"]) or e.pitch != pitch_token(s["pitch"])
                or (e.start, e.end) != (x, y)
                or any(stored.get(k) != s.get(k) for k in ("pitch", "attack_note_id", "tie_chain_id", "sounding_duration"))):
            raise ValueError("clipped_event_source_binding_mismatch")
    geometry = prepare_voice_geometry(ir)
    notes = {n["note_id"]: n for n in ir["note_events"]}
    rows = {r["id"]: dict(r, pitch_data=sounds[r["id"]]["pitch"]) for r in geometry["rows"]}
    valid, statuses = {}, Counter()
    for eid, s in sounds.items():
        chain = [notes.get(nid) for nid in s["source_note_ids"]]
        x, y = fraction(s["span"]["start"]), fraction(s["span"]["end"])
        reason = None
        if not chain or any(n is None for n in chain):
            reason = "missing_source_notes"
        elif eid not in rows or eid in geometry["reason"]:
            reason = "missing_or_cross_voice_identity"
        else:
            ordered = sorted(chain, key=lambda n: (fraction(n["global_onset_quarter"]), n["note_id"]))
            cursor = x
            for n in ordered:
                onset = fraction(n["global_onset_quarter"])
                dur = fraction(n["notated_duration_quarter"])
                if (onset != cursor or dur <= 0 or spelled_height(n.get("concert_pitch", {})) is None
                        or n.get("concert_pitch") != s["pitch"]):
                    reason = "source_clock_or_pitch_inconsistent"; break
                cursor += dur
            if cursor != y or s.get("attack_note_id") != ordered[0]["note_id"]:
                reason = "source_clock_or_attack_inconsistent"
        valid[eid] = reason is None
        statuses[reason or "consistent_explicit_ir_lane"] += 1
    neighbors = {}
    # Reuse the existing voice geometry, with the stricter full tied-clock gate.
    for original_seq in geometry["voices"].values():
        seq = [rows[r["id"]] for r in original_seq]
        overlapping, current = set(), []
        for r in seq:
            current = [t for t in current if t["end"] > r["start"]]
            if current:
                overlapping.add(r["id"]); overlapping.update(t["id"] for t in current)
            current.append(r)
        for index, r in enumerate(seq):
            if not valid.get(r["id"]) or index == 0 or index+1 == len(seq):
                continue
            p, n = seq[index-1], seq[index+1]
            triplet = (p, r, n)
            if (not all(valid.get(z["id"]) for z in triplet)
                    or p["end"] != r["start"] or r["end"] != n["start"]
                    or any(z["id"] in overlapping for z in triplet)):
                continue
            neighbors[r["id"]] = p, n
    measures = defaultdict(list)
    for m in ir["measures"]:
        measures[fraction(m["global_start_quarter"])].append(m)
    grid = []
    for t, group in sorted(measures.items()):
        meters = {(m.get("time_signature", {}).get("beats"), m.get("time_signature", {}).get("beat_type")) for m in group}
        keys = {m.get("key_signature", {}).get("fifths") for m in group}
        meter = next(iter(meters)) if len(meters) == 1 else (None, None)
        fifths = next(iter(keys)) if len(keys) == 1 else None
        grid.append((t, meter, fifths))
    return Evidence(events, tuple(grid), rows, neighbors, dict(statuses), sha, tuple(g[0] for g in grid))


def meter_at(evidence, time):
    index = bisect_right(evidence._measure_times, time)-1
    return evidence.measures[index] if index >= 0 else None


def metric(evidence, time):
    if time in evidence._metric_cache:
        return evidence._metric_cache[time]
    g = meter_at(evidence, time)
    if g is None:
        return None, None
    start, (beats, denominator), _ = g
    if type(beats) is not int or type(denominator) is not int or beats <= 0 or denominator <= 0:
        return None, None
    unit = F(4, denominator)*(3 if denominator == 8 and beats in (6, 9, 12) else 1)
    offset = time-start
    result = (F(2) if offset == 0 else F(1) if offset % unit == 0 else F(1, 2)), unit
    evidence._metric_cache[time] = result
    return result


def key_alters(fifths):
    if type(fifths) is not int or not -7 <= fifths <= 7:
        return None
    result = dict.fromkeys("CDEFGAB", 0)
    for letter in ("FCGDAEB" if fifths >= 0 else "BEADGCF")[:abs(fifths)]:
        result[letter] = 1 if fifths >= 0 else -1
    return result


def run_features(problem, evidence, start, end, signature):
    """Union evidence for one harmonic run; independent of internal edge cuts."""
    cache_key = problem.points, problem.total_note_time, start, end, signature
    if cache_key in evidence._feature_cache:
        return evidence._feature_cache[cache_key]
    total = problem.total_note_time; width = problem.points[-1]-problem.points[0]
    root, members = signature; members = set(members)
    active = [(e, min(e.end, end)-max(e.start, start)) for e in evidence.events if e.start < end and start < e.end]
    known = {e.pitch for e, dur in active if e.pitch is not None and dur > 0}
    raw = sum((dur for e, dur in active if e.pitch is not None and e.pitch not in members), F())
    unresolved = sum((dur for e, dur in active if e.pitch is None), F())
    presence = bool(known) and not unresolved
    features = {
        "nonmember_exposure": raw/total, "unresolved_spelling_exposure": unresolved/total,
        "missing_member_fraction": (F(len(members-known), len(members))*(end-start)/width if presence and members else None),
        "missing_root": (end-start)/width*int(root not in known) if presence and root is not None else None,
        "extra_member_complexity": (end-start)/width*max(0, len(members)-3),
        "unknown_root": (end-start)/width*int(root is None), "harmonic_run_count": F(1),
    }
    # The run key prior is integrated over signature changes; mode_hint ignored.
    left, right = bisect_right(evidence._measure_times, start), bisect_right(evidence._measure_times, end)
    times = sorted({start, end} | {t for t in evidence._measure_times[left:right] if t < end})
    key_loss = F(); key_available = bool(members)
    for x, y in zip(times, times[1:]):
        g = meter_at(evidence, x); alters = key_alters(g[2]) if g else None
        if alters is None:
            key_available = False; continue
        key_loss += (y-x)/width*F(sum(alters[s] != a for s, a in members), len(members))
    features["key_signature_foreign_member"] = key_loss if key_available else None
    metric_loss = F(); metric_available = True; patterns = []; pattern_assessed = 0
    for e, dur in active:
        original = evidence.rows.get(e.event_id)
        time = original["start"] if original else e.start
        strength, unit = metric(evidence, time)
        if strength is None:
            metric_available = False
        if e.pitch is None or e.pitch in members:
            continue
        if strength is not None:
            metric_loss += dur*strength/total
        neighbors = evidence.neighbors.get(e.event_id)
        if not neighbors or strength is None or strength > 1:
            continue
        pattern_assessed += 1
        p, n = neighbors; r = evidence.rows[e.event_id]
        # Entire preparation/ornament/resolution belongs to this same run.
        if (p["start"] < start or n["end"] > end or r["end"]-r["start"] > unit/2
                or pitch_token(p["pitch_data"]) not in members or pitch_token(n["pitch_data"]) not in members):
            continue
        h = [spelled_height(z["pitch_data"]) for z in (p, r, n)]
        if any(v is None for v in h):
            continue
        approach, departure = r["pitch"]-p["pitch"], n["pitch"]-r["pitch"]
        steps = h[1]-h[0], h[2]-h[1]
        if not (abs(steps[0]) == abs(steps[1]) == 1 and 0 < abs(approach) <= 2 and 0 < abs(departure) <= 2):
            continue
        kind = "neighbor_like" if p["pitch_data"] == n["pitch_data"] else "passing_like" if approach*departure > 0 else None
        if kind:
            patterns.append({"kind": kind, "source_event_ids": [p["id"], r["id"], n["id"]],
                             "ornament_event_id": r["id"], "exposure": rational(dur/total),
                             "confirmed_nct": False, "membership_exempted": False,
                             "identity": "unique_contiguous_clock_consistent_explicit_ir_voice"})
    features["metric_nonmember_exposure"] = metric_loss if metric_available else None
    features["conditional_step_ornament_exposure"] = (sum((fraction(p["exposure"]) for p in patterns), F())
                                                      if pattern_assessed else None)
    # Recompute lowest SOUNDING pitches per cell; not one bass pick per attack.
    cuts = sorted({start, end} | {t for e, _ in active for t in (e.start, e.end) if start < t < end})
    bass_loss = F(); bass_available = True
    for x, y in zip(cuts, cuts[1:]):
        sounding = [e for e, _ in active if e.start <= x < e.end]
        if not sounding:
            continue
        rows = [evidence.rows.get(e.event_id) for e in sounding]
        if any(r is None for r in rows):
            bass_available = False; continue
        lowest = min(r["pitch"] for r in rows)
        tokens = [pitch_token(r["pitch_data"]) for r in rows if r["pitch"] == lowest]
        if any(t is None for t in tokens):
            bass_available = False; continue
        bass_loss += (y-x)/width*F(sum(t not in members for t in tokens), len(tokens))
    features["lowest_nonmember_exposure"] = bass_loss if bass_available else None
    result = features, patterns
    evidence._feature_cache[cache_key] = result
    return result


def decode(problem, evidence, *, musical_evidence=True, transition_budget=2_000_000):
    """Exact DAG state = endpoint/raw count/run-start/spelled signature.

    Extending the same signature replaces its current UNION cost, instead of
    adding another edge score. Raw edge count still consumes the original cap.
    """
    if type(transition_budget) is not int or transition_budget <= 0:
        raise ValueError("invalid_transition_budget")
    if problem.status != "ready":
        return {"status": problem.status, "selected": None, "transitions": 0,
                "exact_optimum_under_declared_score": False}
    weights = BASE_WEIGHTS | (EVIDENCE_WEIGHTS if musical_evidence else {})
    # Exact integer score units, NOT quantization. All primitive costs remain
    # Fraction; a conservative common denominator covers time, note exposure,
    # member/lowest multiplicities and every declared weight/metric factor.
    # Assert divisibility for each cost before using fast integer DAG addition.
    time_scale = lcm(*(x.denominator for x in (
        *problem.points, *(t for e in evidence.events for t in (e.start, e.end)), *evidence._measure_times)))
    max_members = max((len(e.signature[1]) for e in problem.edges), default=0)
    multiplicity_scale = lcm(*range(1, max(6, 2*max_members, len(evidence.events))+1))
    scale = (2*time_scale*problem.total_note_time.numerator*(problem.points[-1]-problem.points[0]).numerator
             *lcm(*(v.denominator for v in weights.values()))*multiplicity_scale)
    def integer_cost(value):
        exact = value*scale
        if exact.denominator != 1:
            raise ValueError("score_scale_not_exact")
        return exact.numerator
    cache = {}
    def run(a, b, sig):
        key = a, b, sig
        if key not in cache:
            values, patterns = run_features(problem, evidence, problem.points[a], problem.points[b], sig)
            cache[key] = integer_cost(feature_cost(values, weights)), values, patterns
        return cache[key]
    outgoing = defaultdict(list); by_id = {}
    for e in problem.edges:
        outgoing[e.start_index].append(e); by_id[e.group_id] = e
    states = [dict() for _ in problem.points]
    states[0][(0, None, None)] = (0, ())
    transitions = 0; transition_cache = {}; blocker_costs = {
        e.group_id: integer_cost(DEFAULT_WEIGHTS["blocker_exposure"]*e.features.get("blocker_exposure", F())) for e in problem.edges}
    for index, current in enumerate(states):
        for (count, run_start, previous), (cost, ids) in current.items():
            if count >= problem.max_segments:
                continue
            for e in outgoing[index]:
                transitions += 1
                if transitions > transition_budget:
                    return {"status": "transition_budget_abstention", "selected": None,
                            "transitions": transitions-1, "exact_optimum_under_declared_score": False}
                same = previous == e.signature
                a = run_start if same else index
                increment = run(a, e.end_index, e.signature)[0]
                if same:
                    increment -= run(a, index, previous)[0]
                else:
                    transition_key = previous, e.signature, e.attack_spellings
                    if transition_key not in transition_cache:
                        transition_cache[transition_key] = integer_cost(feature_cost(transition(previous, e), weights))
                    increment += transition_cache[transition_key]
                # Candidate-specific blockers remain additive and are NEVER
                # washed away by the union of adjacent unblocked hypotheses.
                increment += blocker_costs[e.group_id]
                key = count+1, a, e.signature
                candidate = cost+increment, ids+(e.group_id,)
                existing = states[e.end_index].get(key)
                if existing is None or candidate < existing:
                    states[e.end_index][key] = candidate
    if not states[-1]:
        return {"status": "no_complete_path_under_segment_cap", "selected": None,
                "transitions": transitions, "exact_optimum_under_declared_score": True}
    cost, ids = min(states[-1].values())
    segments, runs = [], []
    for gid in ids:
        e = by_id[gid]
        segments.append({"semantic_group_ref": gid, "span": {"start": rational(e.start), "end": rational(e.end)},
                         "root_spelling": e.signature[0], "members": e.signature[1],
                         "source_event_ids": e.source_event_ids, "candidate_blockers": e.blockers})
        if runs and runs[-1][2] == e.signature:
            runs[-1] = runs[-1][0], e.end_index, e.signature
        else:
            runs.append((e.start_index, e.end_index, e.signature))
    details = []
    for a, b, sig in runs:
        c, values, patterns = run(a, b, sig)
        details.append({"span": {"start": rational(problem.points[a]), "end": rational(problem.points[b])},
                        "root_spelling": sig[0], "members": sig[1], "run_cost": rational(F(c, scale)),
                        "features": {k: None if v is None else rational(v) for k, v in values.items()},
                        "availability": {k: v is not None for k, v in values.items()},
                        "conditional_patterns": patterns})
    return {"status": "selected_untrained_hypothesis", "transitions": transitions,
            "exact_optimum_under_declared_score": True,
            "selected": {"proposal_id": "evidence_"+hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:24],
                         "score_cost": rational(F(cost, scale)), "segments": segments, "harmonic_runs": details,
                         "feature_version": FEATURE_VERSION, "musical_evidence_enabled": musical_evidence,
                         "confidence": None, "source_labels_used_for_selection": False,
                         "human_validated": False, "music_constraints_fully_validated": False}}


def prepare_with_evidence(ir, bundle, search):
    return prepare(bundle, search), source_evidence(ir, bundle)


def score_path(problem, evidence, ids, *, musical_evidence=True):
    """Audit a complete existing path; no gold compatibility or fitting."""
    by_id = {e.group_id: e for e in problem.edges}
    edges = [by_id[gid] for gid in ids]
    if (not edges or len(edges) > problem.max_segments or edges[0].start_index != 0
            or edges[-1].end_index != len(problem.points)-1
            or any(l.end_index != r.start_index for l, r in zip(edges, edges[1:]))):
        raise ValueError("not_complete_existing_path")
    weights = BASE_WEIGHTS | (EVIDENCE_WEIGHTS if musical_evidence else {})
    runs, transitions = [], F()
    previous = None
    for e in edges:
        if runs and previous == e.signature:
            runs[-1] = (runs[-1][0], e.end, e.signature)
        else:
            runs.append((e.start, e.end, e.signature))
            transitions += feature_cost(transition(previous, e), weights)
        previous = e.signature
    return (transitions + sum((feature_cost(run_features(problem, evidence, a, b, sig)[0], weights)
                               for a, b, sig in runs), F())
            + sum((DEFAULT_WEIGHTS["blocker_exposure"]*e.features.get("blocker_exposure", F()) for e in edges), F()))
