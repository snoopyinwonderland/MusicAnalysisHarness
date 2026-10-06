"""Label-blind functional alternatives and source-bound joint run scoring.

The literal surface root is retained. A major/minor 6-4 surface can ALSO have
the observed fifth as a dominant-origin analysis root. This is a hypothesis,
not a cadence/key decision. Dominant/leading-tone-to-target interpretations
are conditional on the next SELECTED spelled chord, not annotation lookup.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import json
from math import lcm

from .applied_chords import hypothesis
from .harmony_candidate_recall import fraction, rational
from .harmony_evidence_scoring import BASE_WEIGHTS, EVIDENCE_WEIGHTS, pitch_token, run_features
from .harmony_progression_search import _hash
from .harmony_reading_voice_context import spelled_height
from .harmony_scored_decoder import DEFAULT_WEIGHTS, feature_cost, transition
from .seventh_context import QUALITIES, chord

VERSION = "harmony-functional-scoring-0.1.0"
FEATURE_VERSION = "source-bound-functional-run-features-0.1.0"
# Fixed before corpus evaluation; no training, dev tuning or calibrated confidence.
ROLE_COST = F(1, 20)
PAIR_WEIGHTS = {"six_four_surface_and_held_bass": F(-1, 10),
                "six_four_direct_upper_paths": F(-1, 20),
                "dominant_family_leading_tone": F(-1, 10),
                "dominant_family_seventh_step": F(-1, 20)}


@lru_cache(maxsize=4096)
def shapes(sig):
    root, members = sig
    if root is None:
        return ()
    return tuple(q for q in QUALITIES if tuple(sorted(map(tuple, chord(root, q)["members"]))) == members)


@lru_cache(maxsize=4096)
def six_four_surface(sig):
    """Functional root at fifth; return literal surface shape, never overwrite it."""
    root, members = sig
    if root is None or len(members) != 3:
        return None
    for literal in members:
        for quality in ("M", "m"):
            c = chord(literal, quality, 2)
            if tuple(sorted(map(tuple, c["members"]))) == members and tuple(c["expected_bass"]) == root:
                return tuple(literal), quality
    return None


@lru_cache(maxsize=8192)
def dominant_pairs(left, right):
    """Reuse Unit26 spelling vocabulary; no supplied home/local-key answer."""
    result = []
    # A selected V7 can be the target of V7/V or vii/V. Its triad core,
    # not an artificially stripped/rewritten reference label, supplies target.
    target_qualities = {"M" if q in ("M", "MM7", "Mm7") else "m"
                        for q in shapes(right) if q in ("M", "MM7", "Mm7", "m", "mm7", "mM7")}
    for quality in sorted(target_qualities):
        for family in ("V", "V7", "vii", "vii7", "vii_half7"):
            h = hypothesis(right[0], quality, family)
            c = h["chord"]
            if (tuple(c["root"]), tuple(sorted(map(tuple, c["members"])))) == left:
                result.append((family, tuple(h["leading_tone"]),
                               tuple(c["members"][3]) if len(c["members"]) == 4 else None))
    return tuple(result)


@dataclass
class FunctionalEvidence:
    source: object
    # Full, validated source events; identity comes from the tied note chain.
    rows: tuple
    links: tuple
    _surface_cache: dict
    _pair_cache: dict
    voice_statuses: dict


def prepare_functional_evidence(ir, evidence):
    if _hash(ir) != evidence.source_ir_content_sha256:
        raise ValueError("functional_source_ir_binding_mismatch")
    notes = {n["note_id"]: n for n in ir["note_events"]}
    sounds = {s["sounding_event_id"]: s for s in ir["sounding_events"]}
    by_voice = defaultdict(list); rows = []; statuses = defaultdict(int)
    for row in evidence.rows.values():
        sound = sounds.get(row["id"])
        if sound is None:
            raise ValueError("missing_functional_source_sound")
        chain = [notes.get(nid) for nid in sound["source_note_ids"]]
        identities = {(n.get("part_id"), n.get("voice_id")) for n in chain if n}
        valid = bool(chain) and all(chain) and len(identities) == 1 and not any(n.get("grace", {}).get("is_grace") for n in chain if n)
        ident = next(iter(identities)) if valid else None
        valid = valid and bool(ident and all(ident))
        cursor = row["start"]
        for n in sorted((n for n in chain if n), key=lambda n: (fraction(n["global_onset_quarter"]), n["note_id"])):
            onset, dur = fraction(n["global_onset_quarter"]), fraction(n["notated_duration_quarter"])
            if onset != cursor or dur <= 0 or n.get("concert_pitch") != sound["pitch"]:
                valid = False
            cursor += dur
        valid = valid and cursor == row["end"] and spelled_height(row["pitch_data"]) is not None
        ordered = sorted((n for n in chain if n), key=lambda n: (fraction(n["global_onset_quarter"]), n["note_id"]))
        valid = valid and sound.get("attack_note_id") == ordered[0]["note_id"]
        r = dict(row, identity=ident if valid else None, token=pitch_token(row["pitch_data"]),
                 source_note_ids=tuple(sound["source_note_ids"]), clock_valid=bool(valid))
        rows.append(r)
        if valid:
            by_voice[ident].append(r)
        statuses["valid_tied_clock" if valid else "unavailable_voice_clock"] += 1
    links = []
    for ident, seq in by_voice.items():
        seq.sort(key=lambda r: (r["start"], r["id"]))
        blocked = set(); active = []
        for r in seq:
            active = [p for p in active if p["end"] > r["start"]]
            if active:
                blocked.add(r["id"]); blocked.update(p["id"] for p in active)
            active.append(r)
        for p, n in zip(seq, seq[1:]):
            if p["end"] == n["start"] and p["id"] not in blocked and n["id"] not in blocked:
                links.append((p, n))
        statuses["polyphonic_event_direct_links_withheld"] += len(blocked)
    return FunctionalEvidence(evidence, tuple(rows), tuple(links), {}, {}, dict(statuses))


def interval_surface(ev, start, end):
    key = start, end
    if key in ev._surface_cache:
        return ev._surface_cache[key]
    rows = [r for r in ev.rows if r["start"] < end and start < r["end"]]
    cuts = sorted({start, end} | {t for r in rows for t in (r["start"], r["end"]) if start < t < end})
    cells = []
    for x, y in zip(cuts, cuts[1:]):
        active = [r for r in rows if r["start"] <= x < r["end"]]
        if not active:
            continue
        lowest = min(r["pitch"] for r in active)
        cells.append((x, y, frozenset(r["token"] for r in active),
                      frozenset(r["token"] for r in active if r["pitch"] == lowest), tuple(active)))
    ev._surface_cache[key] = cells
    return cells


def supply(problem, ev):
    """Append alternatives only; unchanged points/old edges/blockers/raw cap.

    Require a complete observed surface triad union and positive exposure with
    its fifth lowest. A union is explicitly NOT asserted to be a vertical chord.
    No gold label, key/mode, title, instrument or work ID is inspected.
    """
    if problem.status != "ready":
        return problem, []
    additions = []; receipts = []; seen = {(e.start_index, e.end_index, e.signature, e.blockers) for e in problem.edges}
    for e in problem.edges:
        qualities = set(shapes(e.signature)) & {"M", "m"}
        if not qualities:
            continue
        cells = interval_surface(ev, e.start, e.end)
        if any(o.pitch is None or o.event_id not in ev.source.rows for o in ev.source.events if o.start < e.end and e.start < o.end):
            continue
        observed = set().union(*(c[2] for c in cells)) if cells else set()
        if not set(e.signature[1]) <= observed or None in observed:
            continue
        for quality in sorted(qualities):
            literal = chord(e.signature[0], quality, 2)
            root = tuple(literal["expected_bass"]); sig = root, e.signature[1]
            witnesses = [(x, y, rs) for x, y, _, lows, rs in cells if lows == {root}]
            if not witnesses or sig == e.signature:
                continue
            key = e.start_index, e.end_index, sig, e.blockers
            if key in seen:
                continue
            seen.add(key)
            gid = "func64_"+hashlib.sha256(json.dumps([VERSION, e.group_id, sig]).encode()).hexdigest()[:24]
            adapter = {"origin_group_id": e.group_id, "surface_root_spelling": e.signature[0],
                       "surface_quality": quality, "analysis_root_spelling": root,
                       "role_hypothesis": "dominant_origin_six_four", "role_confirmed": False}
            # Old missing_root is not consumed by run_features, but keep it
            # truthful for any later audit. Membership/time/blockers are identical.
            values = e.features | {"missing_root": F()}
            additions.append(replace(e, group_id=gid, signature=sig, features=values, adapter=adapter))
            receipts.append({"group_id": gid, "span": {"start": rational(e.start), "end": rational(e.end)},
                             **adapter, "members": sig[1], "candidate_blockers": e.blockers,
                             "observed_union_is_vertical_chord": False,
                             "lowest_fifth_source_event_ids": sorted({r["id"] for _, _, rs in witnesses for r in rs if r["token"] == root}),
                             "function_confirmed": False, "cadence": None})
    return replace(problem, edges=problem.edges+tuple(additions)), receipts


def pair_features(ev, left_start, boundary, right_end, left, right):
    if not left_start < boundary < right_end:
        raise ValueError("invalid_functional_pair_span")
    # Resolution evidence concerns the arrival at the selected boundary, not
    # how long the first raw edge happens to be. The destination's complete
    # original span may extend past that edge; it is not clipped or stretched.
    key = left_start, boundary, left, right
    if key in ev._pair_cache:
        return ev._pair_cache[key]
    values = dict.fromkeys(PAIR_WEIGHTS, F()); details = []
    surface = six_four_surface(left)
    six_four_pair = bool(surface and right[0] == left[0] and any(q in ("M", "Mm7") for q in shapes(right)))
    applied = dominant_pairs(left, right)
    if not six_four_pair and not applied:
        return values, details
    before = interval_surface(ev, left_start, boundary)
    # Last/first positive cell: retain attacked and sustained original sound IDs.
    xs = before[-1] if before and before[-1][1] == boundary else None
    arriving = [r for r in ev.rows if r["start"] <= boundary < r["end"]]
    low = min((r["pitch"] for r in arriving), default=None)
    ys = (boundary, right_end, frozenset(r["token"] for r in arriving),
          frozenset(r["token"] for r in arriving if r["pitch"] == low), tuple(arriving)) if arriving else None
    direct = [(p, n) for p, n in ev.links if p["end"] == boundary == n["start"]
              and p["start"] >= left_start]
    def motion(p, n, target, delta):
        return n["token"] == target and n["pitch"]-p["pitch"] in delta and abs(spelled_height(n["pitch_data"])-spelled_height(p["pitch_data"])) == 1
    def receipt(kind, pairs):
        details.append({"kind": kind, "source_event_pairs": [[p["id"], n["id"]] for p, n in pairs],
                        "basis": "unique_contiguous_clock_consistent_explicit_ir_voice",
                        "voice_identity_confirmed": False, "function_confirmed": False})
    if six_four_pair and xs and ys:
        root = left[0]; target = chord(root, "M"); third, fifth = map(tuple, target["members"][1:])
        bass_pairs = [(p, n) for p in xs[4] for n in ys[4]
                      if p["token"] == n["token"] == root and p["pitch"] == n["pitch"]
                      and p["clock_valid"] and n["clock_valid"]
                      and (p["id"] == n["id"] or (p["identity"] == n["identity"] and p["end"] == n["start"]))]
        if (xs[3] == ys[3] == {root} and set(left[1]) <= xs[2] and {root, third, fifth} <= ys[2] and bass_pairs):
            values["six_four_surface_and_held_bass"] = F(1)
            details.append({"kind": "six_four_surface_and_held_bass", "bass_event_pairs": [[p["id"], n["id"]] for p, n in bass_pairs],
                            "left_event_ids": sorted(r["id"] for r in xs[4]), "right_event_ids": sorted(r["id"] for r in ys[4]),
                            "upper_voice_resolution_confirmed": False, "function_confirmed": False, "cadence": None})
            four = [p for p in left[1] if ("CDEFGAB".index(p[0])-"CDEFGAB".index(root[0])) % 7 == 3][0]
            six = [p for p in left[1] if ("CDEFGAB".index(p[0])-"CDEFGAB".index(root[0])) % 7 == 5][0]
            p43 = [(p, n) for p, n in direct if p["token"] == four and motion(p, n, third, (-1, -2))]
            p65 = [(p, n) for p, n in direct if p["token"] == six and motion(p, n, fifth, (-1, -2))]
            if p43 and p65:
                values["six_four_direct_upper_paths"] = F(1); receipt("four_to_three_and_six_to_five", p43+p65)
    for family, leading, seventh in applied:
        pairs = [(p, n) for p, n in direct if p["token"] == leading and motion(p, n, right[0], (1,))]
        if pairs:
            values["dominant_family_leading_tone"] = F(1); receipt(family+"_leading_tone_to_selected_target", pairs)
        pairs = [(p, n) for p, n in direct if p["token"] == seventh and n["token"] in right[1]
                 and n["pitch"]-p["pitch"] in (-1, -2)
                 and spelled_height(n["pitch_data"])-spelled_height(p["pitch_data"]) == -1]
        if pairs:
            values["dominant_family_seventh_step"] = F(1); receipt(family+"_seventh_to_selected_member", pairs)
    result = values, details
    ev._pair_cache[key] = result
    return result


def role_cost(sig):
    return ROLE_COST if six_four_surface(sig) else F()


def score_path(problem, ev, ids, *, functional_evidence=True):
    by_id = {e.group_id: e for e in problem.edges}; edges = [by_id[i] for i in ids]
    if (not edges or len(edges) > problem.max_segments or edges[0].start_index != 0 or edges[-1].end_index != len(problem.points)-1
            or any(a.end_index != b.start_index for a, b in zip(edges, edges[1:]))):
        raise ValueError("not_complete_existing_path")
    weights = BASE_WEIGHTS | EVIDENCE_WEIGHTS; cost = F(); runs = []
    for e in edges:
        if runs and runs[-1][2] == e.signature:
            runs[-1] = runs[-1][0], e.end, e.signature
        else:
            if runs:
                a, b, previous = runs[-1]
                cost += feature_cost(transition(previous, e), weights)
                if functional_evidence:
                    cost += feature_cost(pair_features(ev, a, b, e.end, previous, e.signature)[0], PAIR_WEIGHTS)
            runs.append((e.start, e.end, e.signature))
    cost += sum((feature_cost(run_features(problem, ev.source, a, b, sig)[0], weights)+role_cost(sig) for a, b, sig in runs), F())
    return cost+sum((DEFAULT_WEIGHTS["blocker_exposure"]*e.features.get("blocker_exposure", F()) for e in edges), F())


def decode(problem, ev, *, functional_evidence=True, transition_budget=2_000_000):
    """Exact augmented DAG; no beam/label pruning or resource cap increase.

    New pair evidence is evaluated on the completed left run + next onset.
    The destination's original span is preserved across later raw-edge cuts.
    """
    if type(transition_budget) is not int or transition_budget <= 0:
        raise ValueError("invalid_transition_budget")
    if problem.status != "ready":
        return {"status": problem.status, "selected": None, "transitions": 0, "exact_optimum_under_declared_score": False}
    weights = BASE_WEIGHTS | EVIDENCE_WEIGHTS; source = ev.source
    times = (*problem.points, *(t for e in source.events for t in (e.start, e.end)), *source._measure_times)
    time_scale = lcm(*(x.denominator for x in times))
    max_members = max((len(e.signature[1]) for e in problem.edges), default=0)
    mult = lcm(*range(1, max(6, 2*max_members, len(source.events))+1))
    scale = 2*time_scale*problem.total_note_time.numerator*(problem.points[-1]-problem.points[0]).numerator*lcm(*(v.denominator for v in (*weights.values(), *PAIR_WEIGHTS.values(), ROLE_COST)))*mult
    def units(v):
        exact = v*scale
        if exact.denominator != 1:
            raise ValueError("score_scale_not_exact")
        return exact.numerator
    run_cache = {}; pair_cache = {}; transitions_cache = {}; by_id = {}; outgoing = defaultdict(list)
    def run(a, b, sig):
        key = a, b, sig
        if key not in run_cache:
            values, patterns = run_features(problem, source, problem.points[a], problem.points[b], sig)
            run_cache[key] = units(feature_cost(values, weights)+role_cost(sig)), values, patterns
        return run_cache[key]
    def pair(a, b, e, sig):
        if not (six_four_surface(sig) and sig[0] == e.signature[0] and any(q in ("M", "Mm7") for q in shapes(e.signature))) and not dominant_pairs(sig, e.signature):
            return 0, dict.fromkeys(PAIR_WEIGHTS, F()), []
        key = a, b, e.end_index, sig, e.signature
        if key not in pair_cache:
            values, details = pair_features(ev, problem.points[a], problem.points[b], e.end, sig, e.signature)
            pair_cache[key] = units(feature_cost(values, PAIR_WEIGHTS)), values, details
        return pair_cache[key]
    for e in problem.edges:
        outgoing[e.start_index].append(e); by_id[e.group_id] = e
    blockers = {e.group_id: units(DEFAULT_WEIGHTS["blocker_exposure"]*e.features.get("blocker_exposure", F())) for e in problem.edges}
    states = [dict() for _ in problem.points]; states[0][(0, None, None)] = (0, ())
    count_transitions = 0
    for index, current in enumerate(states):
        for (count, a, previous), (cost, ids) in current.items():
            if count >= problem.max_segments:
                continue
            for e in outgoing[index]:
                count_transitions += 1
                if count_transitions > transition_budget:
                    return {"status": "transition_budget_abstention", "selected": None, "transitions": count_transitions-1,
                            "exact_optimum_under_declared_score": False}
                same = previous == e.signature; left = a if same else index
                increment = run(left, e.end_index, e.signature)[0]+blockers[e.group_id]
                if same:
                    increment -= run(a, index, previous)[0]
                else:
                    tkey = previous, e.signature, e.attack_spellings
                    if tkey not in transitions_cache:
                        transitions_cache[tkey] = units(feature_cost(transition(previous, e), weights))
                    increment += transitions_cache[tkey]
                    if previous is not None and functional_evidence:
                        increment += pair(a, index, e, previous)[0]
                key = count+1, left, e.signature; candidate = cost+increment, ids+(e.group_id,)
                existing = states[e.end_index].get(key)
                if existing is None or candidate < existing:
                    states[e.end_index][key] = candidate
    if not states[-1]:
        return {"status": "no_complete_path_under_segment_cap", "selected": None, "transitions": count_transitions, "exact_optimum_under_declared_score": True}
    cost, ids = min(states[-1].values()); segments = []; runs = []; pairs = []
    for gid in ids:
        e = by_id[gid]
        segments.append({"semantic_group_ref": gid, "span": {"start": rational(e.start), "end": rational(e.end)},
                         "root_spelling": e.signature[0], "members": e.signature[1], "source_event_ids": e.source_event_ids,
                         "candidate_blockers": e.blockers, "interpretation": e.adapter if gid.startswith("func64_") else None})
        if runs and runs[-1][2] == e.signature:
            runs[-1] = runs[-1][0], e.end_index, e.signature
        else:
            if runs and functional_evidence:
                a, b, sig = runs[-1]; pc, values, details = pair(a, b, e, sig)
                if details:
                    pairs.append({"boundary": rational(e.start), "left_signature": sig, "right_signature": e.signature,
                                  "score_cost": rational(F(pc, scale)), "features": {k: rational(v) for k, v in values.items()},
                                  "observations": details, "secondary_vs_primary": "unresolved_without_local_key",
                                  "function_confirmed": False, "cadence": None})
            runs.append((e.start_index, e.end_index, e.signature))
    run_rows = []
    for a, b, sig in runs:
        c, values, patterns = run(a, b, sig)
        surface = six_four_surface(sig)
        run_rows.append({"span": {"start": rational(problem.points[a]), "end": rational(problem.points[b])}, "root_spelling": sig[0], "members": sig[1],
                         "run_cost": rational(F(c, scale)), "functional_role_complexity_cost": rational(role_cost(sig)),
                         "surface_root_spelling": surface[0] if surface else sig[0],
                         "role_hypothesis": "dominant_origin_six_four" if surface else None,
                         "features": {k: None if v is None else rational(v) for k, v in values.items()}, "conditional_patterns": patterns})
    return {"status": "selected_untrained_hypothesis", "transitions": count_transitions, "exact_optimum_under_declared_score": True,
            "selected": {"proposal_id": "functional_"+hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:24],
                         "score_cost": rational(F(cost, scale)), "segments": segments, "harmonic_runs": run_rows, "functional_pairs": pairs,
                         "feature_version": FEATURE_VERSION, "functional_evidence_enabled": functional_evidence,
                         "confidence": None, "source_labels_used_for_selection": False, "human_validated": False,
                         "music_constraints_fully_validated": False}}
