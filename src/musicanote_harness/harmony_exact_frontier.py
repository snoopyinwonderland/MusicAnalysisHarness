"""Exact computational reductions, not a new musical scoring rule.

Keep the J3c graph, spelled hypotheses, full clocks and global normalization.
Equivalent raw edges share work; Pareto-dominated states cannot win under the
same raw-edge cap. An indexed integral computes the existing run features.
No beam, score threshold, top-N chord filter, gold or tile-wise winner is used.
"""
from collections import defaultdict
from dataclasses import replace
from fractions import Fraction as F
from math import lcm

from . import harmony_bounded_recovery as bounded
from .harmony_candidate_recall import rational
from .harmony_evidence_scoring import (
    BASE_WEIGHTS, EVIDENCE_WEIGHTS, key_alters, meter_at, metric, pitch_token,
)
from .harmony_functional_scoring import (
    PAIR_WEIGHTS, ROLE_COST, decode as original_decode, dominant_pairs,
    pair_features, role_cost, shapes, six_four_surface, supply,
)
from .harmony_progression_search import _hash
from .harmony_reading_voice_context import spelled_height
from .harmony_scored_decoder import DEFAULT_WEIGHTS, feature_cost, transition

VERSION = "harmony-exact-frontier-0.1.0"
CONFIG = dict(bounded.CONFIG)


def prefix(values):
    result = [F()]
    for value in values:
        result.append(result[-1]+value)
    return tuple(result)


class RunIndex:
    """Exact cell integrals; original attack/neighbor clocks stay unchanged.

    A fine grid is required rather than silently approximating an observation
    between grid points. Missing fields preserve the original None semantics.
    The original unindexed implementation independently checks the winner.
    """
    def __init__(self, problem, source):
        self.problem, self.source = problem, source
        self.points = problem.points
        self.positions = {t: i for i, t in enumerate(self.points)}
        a, b = self.points[0], self.points[-1]
        if any(t not in self.positions for e in source.events for t in (e.start, e.end) if a < t < b):
            raise ValueError("index_missing_observation_boundary")
        if any(t not in self.positions for t in source._measure_times if a < t < b):
            raise ValueError("index_missing_measure_boundary")
        self.cells = []
        strengths = {}
        for e in source.events:
            row = source.rows.get(e.event_id)
            strengths[e.event_id] = metric(source, row["start"] if row else e.start)
        for x, y in zip(self.points, self.points[1:]):
            active = [e for e in source.events if e.start <= x < e.end]
            counts = defaultdict(int); weighted = defaultdict(F)
            for e in active:
                counts[e.pitch] += 1
                strength, _ = strengths[e.event_id]
                if strength is not None:
                    weighted[e.pitch] += strength
            rows = [source.rows.get(e.event_id) for e in active]
            lowest = []
            bass_available = all(r is not None for r in rows)
            if rows and bass_available:
                low = min(r["pitch"] for r in rows)
                lowest = [pitch_token(r["pitch_data"]) for r in rows if r["pitch"] == low]
                bass_available = all(t is not None for t in lowest)
            g = meter_at(source, x)
            self.cells.append((y-x, dict(counts), dict(weighted),
                any(strengths[e.event_id][0] is None for e in active), lowest,
                bass_available, key_alters(g[2]) if g else None))
        self.unresolved = prefix(d*counts.get(None, 0) for d, counts, *_ in self.cells)
        self.metric_unavailable = prefix(int(c[3]) for c in self.cells)
        self.bass_unavailable = prefix(int(not c[5]) for c in self.cells)
        self.key_unavailable = prefix(int(c[6] is None) for c in self.cells)
        tokens = {e.pitch for e in source.events if e.pitch is not None}
        self.presence = {token: prefix(d*counts.get(token, 0) for d, counts, *_ in self.cells) for token in tokens}
        self.by_signature = {}
        self.patterns = []
        for e in source.events:
            neighbors = source.neighbors.get(e.event_id)
            strength, unit = strengths[e.event_id]
            if not neighbors or e.pitch is None or strength is None or strength > 1:
                continue
            p, n = neighbors; r = source.rows[e.event_id]
            kind = None
            if r["end"]-r["start"] <= unit/2:
                h = [spelled_height(z["pitch_data"]) for z in (p, r, n)]
                if all(v is not None for v in h):
                    approach, departure = r["pitch"]-p["pitch"], n["pitch"]-r["pitch"]
                    if (abs(h[1]-h[0]) == abs(h[2]-h[1]) == 1
                            and 0 < abs(approach) <= 2 and 0 < abs(departure) <= 2):
                        kind = ("neighbor_like" if p["pitch_data"] == n["pitch_data"]
                                else "passing_like" if approach*departure > 0 else None)
            self.patterns.append((e, p, n, pitch_token(p["pitch_data"]), pitch_token(n["pitch_data"]), kind))

    def signature_integrals(self, sig):
        if sig not in self.by_signature:
            members = set(sig[1]); raw = []; weighted = []; bass = []; key = []
            for d, counts, strengths, _, lowest, available, alters in self.cells:
                raw.append(d*sum(v for t, v in counts.items() if t is not None and t not in members))
                weighted.append(d*sum((v for t, v in strengths.items() if t is not None and t not in members), F()))
                bass.append(d*F(sum(t not in members for t in lowest), len(lowest)) if available and lowest else F())
                key.append(d*F(sum(alters[s] != a for s, a in members), len(members)) if alters is not None and members else F())
            self.by_signature[sig] = tuple(prefix(v) for v in (raw, weighted, bass, key))
        return self.by_signature[sig]

    def features(self, start, end, sig):
        i, j = self.positions[start], self.positions[end]
        if i >= j:
            raise ValueError("invalid_index_run")
        def delta(p): return p[j]-p[i]
        root, tokens = sig; members = set(tokens)
        raw, weighted, bass, key = self.signature_integrals(sig)
        total = self.problem.total_note_time; width = self.points[-1]-self.points[0]
        known = {t for t, p in self.presence.items() if delta(p) > 0}
        unresolved = delta(self.unresolved); present = bool(known) and not unresolved
        values = {
            "nonmember_exposure": delta(raw)/total,
            "unresolved_spelling_exposure": unresolved/total,
            "missing_member_fraction": F(len(members-known), len(members))*(end-start)/width if present and members else None,
            "missing_root": (end-start)/width*int(root not in known) if present and root is not None else None,
            "extra_member_complexity": (end-start)/width*max(0, len(members)-3),
            "unknown_root": (end-start)/width*int(root is None), "harmonic_run_count": F(1),
            "key_signature_foreign_member": delta(key)/width if members and not delta(self.key_unavailable) else None,
            "metric_nonmember_exposure": delta(weighted)/total if not delta(self.metric_unavailable) else None,
            "lowest_nonmember_exposure": delta(bass)/width if not delta(self.bass_unavailable) else None,
        }
        patterns = []; assessed = 0
        for e, p, n, pt, nt, kind in self.patterns:
            if e.pitch in members or not (e.start < end and start < e.end):
                continue
            assessed += 1
            if kind and p["start"] >= start and n["end"] <= end and pt in members and nt in members:
                duration = min(e.end, end)-max(e.start, start)
                patterns.append({"kind": kind, "source_event_ids": [p["id"], e.event_id, n["id"]],
                    "ornament_event_id": e.event_id, "exposure": rational(duration/total),
                    "confirmed_nct": False, "membership_exempted": False,
                    "identity": "unique_contiguous_clock_consistent_explicit_ir_voice"})
        values["conditional_step_ornament_exposure"] = (
            sum((F(p["exposure"]["numerator"], p["exposure"]["denominator"]) for p in patterns), F()) if assessed else None)
        return values, patterns


def canonical_edges(problem):
    """Coalesce score-identical raw arcs; keep all origins in a receipt.

    This equivalence is only under the declared score, NOT musical equivalence
    of augmented-sixth/tertian functions. Different spellings are never merged.
    The lowest ID is the original decoder's lexicographic tie winner.
    """
    groups = defaultdict(list); by_id = {}
    for e in problem.edges:
        if e.group_id in by_id:
            raise ValueError("duplicate_frontier_edge_id")
        by_id[e.group_id] = e
        if (not 0 <= e.start_index < e.end_index < len(problem.points)
                or (e.start, e.end) != (problem.points[e.start_index], problem.points[e.end_index])):
            raise ValueError("invalid_frontier_edge_geometry")
        if not e.signature[1]:
            raise ValueError("unscorable_empty_signature")
        key = (e.start_index, e.end_index, e.signature, e.attack_spellings,
               e.blockers, e.source_event_ids, e.features.get("blocker_exposure", F()))
        groups[key].append(e)
    edges = []; receipts = []
    for group in groups.values():
        group.sort(key=lambda e: e.group_id); edges.append(group[0])
        if len(group) > 1:
            receipts.append({"representative_group_id": group[0].group_id,
                "equivalent_group_ids": [e.group_id for e in group],
                "equivalence": "declared_score_and_future_state_only", "musical_function_equivalence": False})
    return tuple(sorted(edges, key=lambda e: (e.start_index, e.end_index, e.group_id))), receipts


def pareto(current):
    """Same endpoint/run-start/signature: count<= and cost/ID<= dominates.

    Positive DAG paths ending at the same point cannot be prefixes of each
    other. Their lexicographic ordering therefore survives a common suffix.
    All subsequent run replacements, transition/pair costs and cap tests are
    identical. No feature sign assumption is needed for this proof.
    """
    groups = defaultdict(list)
    for (count, start, sig), value in current.items():
        groups[start, sig].append((count, value))
    kept = {}; removed = 0
    for (start, sig), items in groups.items():
        best = None
        for count, value in sorted(items):
            if best is not None and best <= value:
                removed += 1
            else:
                kept[count, start, sig] = value
                best = value if best is None else min(best, value)
    return kept, removed


def decode(problem, ev, *, functional_evidence=True, transition_budget=2_000_000):
    if type(transition_budget) is not int or transition_budget <= 0:
        raise ValueError("invalid_transition_budget")
    stats = {"pareto_states_removed": 0, "unreachable_states_removed": 0,
             "cap_infeasible_arcs_skipped": 0, "states_expanded": 0,
             "peak_endpoint_states": 0, "run_cost_evaluations": 0,
             "pair_cost_evaluations": 0, "beam_pruning": False, "score_weights_changed": False}
    def result(status, selected, transitions, exact):
        return {"status": status, "selected": selected, "transitions": transitions,
                "exact_optimum_under_declared_score": exact, "search_diagnostics": stats}
    if problem.status != "ready":
        return result(problem.status, None, 0, False)
    if (len(problem.points) < 2 or any(a >= b for a, b in zip(problem.points, problem.points[1:]))
            or problem.total_note_time <= 0 or type(problem.max_segments) is not int or problem.max_segments <= 0):
        raise ValueError("invalid_frontier_problem")
    edges, receipts = canonical_edges(problem)
    stats.update(original_edges=len(problem.edges), representative_edges=len(edges), equivalence_receipts=receipts)
    source = ev.source; indexer = RunIndex(problem, source)
    weights = BASE_WEIGHTS | EVIDENCE_WEIGHTS
    times = (*problem.points, *(t for e in source.events for t in (e.start, e.end)), *source._measure_times)
    time_scale = lcm(*(x.denominator for x in times))
    mult = lcm(*range(1, max(6, 2*max((len(e.signature[1]) for e in edges), default=0), len(source.events))+1))
    scale = (2*time_scale*problem.total_note_time.numerator*(problem.points[-1]-problem.points[0]).numerator
             *lcm(*(v.denominator for v in (*weights.values(), *PAIR_WEIGHTS.values(), ROLE_COST)))*mult)
    def units(v):
        value = v*scale
        if value.denominator != 1: raise ValueError("score_scale_not_exact")
        return value.numerator
    runs = {}; pairs = {}; transitions = {}; outgoing = defaultdict(list); by_id = {}
    def run(a, b, sig):
        key = a, b, sig
        if key not in runs:
            values, _ = indexer.features(problem.points[a], problem.points[b], sig)
            runs[key] = units(feature_cost(values, weights)+role_cost(sig))
            stats["run_cost_evaluations"] += 1
        return runs[key]
    def pair(a, b, e, previous):
        if not (six_four_surface(previous) and previous[0] == e.signature[0]
                and any(q in ("M", "Mm7") for q in shapes(e.signature))) and not dominant_pairs(previous, e.signature):
            return 0
        # pair_features itself is invariant to the next raw edge end.
        key = a, b, previous, e.signature
        if key not in pairs:
            pairs[key] = units(feature_cost(pair_features(ev, problem.points[a], problem.points[b], e.end, previous, e.signature)[0], PAIR_WEIGHTS))
            stats["pair_cost_evaluations"] += 1
        return pairs[key]
    for e in edges:
        outgoing[e.start_index].append(e); by_id[e.group_id] = e
    remaining = [problem.max_segments+1]*len(problem.points); remaining[-1] = 0
    for i in range(len(problem.points)-2, -1, -1):
        remaining[i] = min((1+remaining[e.end_index] for e in outgoing[i]), default=problem.max_segments+1)
    blockers = {e.group_id: units(DEFAULT_WEIGHTS["blocker_exposure"]*e.features.get("blocker_exposure", F())) for e in edges}
    states = [dict() for _ in problem.points]; states[0][0, None, None] = (0, ())
    count_transitions = 0
    for index in range(len(states)-1):
        current = states[index]
        stats["peak_endpoint_states"] = max(stats["peak_endpoint_states"], len(current))
        feasible = {key: value for key, value in current.items() if key[0]+remaining[index] <= problem.max_segments}
        stats["unreachable_states_removed"] += len(current)-len(feasible)
        current, removed = pareto(feasible); stats["pareto_states_removed"] += removed
        states[index] = {}  # Completed endpoints are not working memory.
        stats["states_expanded"] += len(current)
        for (count, a, previous), (cost, ids) in current.items():
            for e in outgoing[index]:
                if count+1+remaining[e.end_index] > problem.max_segments:
                    stats["cap_infeasible_arcs_skipped"] += 1; continue
                if count_transitions >= transition_budget:
                    return result("transition_budget_abstention", None, count_transitions, False)
                count_transitions += 1
                same = previous == e.signature; left = a if same else index
                increment = run(left, e.end_index, e.signature)+blockers[e.group_id]
                if same:
                    increment -= run(a, index, previous)
                else:
                    tkey = previous, e.signature, e.attack_spellings
                    if tkey not in transitions:
                        transitions[tkey] = units(feature_cost(transition(previous, e), weights))
                    increment += transitions[tkey]
                    if previous is not None and functional_evidence:
                        increment += pair(a, index, e, previous)
                key = count+1, left, e.signature; candidate = cost+increment, ids+(e.group_id,)
                old = states[e.end_index].get(key)
                if old is None or candidate < old: states[e.end_index][key] = candidate
    if not states[-1]:
        return result("no_complete_path_under_segment_cap", None, count_transitions, True)
    cost, ids = min(states[-1].values())
    # Independent original-feature evaluation of the winning COMPLETE path.
    reconstructed = original_decode(replace(problem, edges=tuple(by_id[gid] for gid in ids)), ev,
        functional_evidence=functional_evidence, transition_budget=max(1, len(ids)))
    selected = reconstructed["selected"]
    if (selected is None or selected["score_cost"] != rational(F(cost, scale))
            or tuple(s["semantic_group_ref"] for s in selected["segments"]) != ids):
        raise ValueError("indexed_winner_score_or_path_mismatch")
    stats["winner_checked_with_original_features"] = True
    return result(reconstructed["status"], selected, count_transitions, True)


def infer(ir, sample):
    before = _hash(ir); view, grace = bounded.grace_projection(ir)
    permissible = {"nonpositive_duration"} if grace["grace_sounding_events"] else set()
    remaining = sorted(set(sample.get("abstention_reasons", []))-permissible)
    plan = bounded.tile_plan(view, sample["span"])
    if remaining: plan.update(status="sample_scope_abstention", blockers=remaining)
    ev, functional, links = bounded.bound_evidence(view, sample["span"], grace)
    problem, origins = bounded.build_problem(view, plan, ev)
    expanded, receipts = supply(problem, functional)
    chosen = decode(expanded, functional, transition_budget=CONFIG["decoder_transition_budget"])
    if _hash(ir) != before or _hash(view) != grace["consumer_view_sha256"]:
        raise ValueError("frontier_mutated_inputs")
    return {"version": VERSION, "status": chosen["status"], "selected_prediction": chosen["selected"],
        "transitions": chosen["transitions"], "exact_optimum_under_declared_graph": chosen["exact_optimum_under_declared_score"],
        "search_diagnostics": chosen["search_diagnostics"], "grace_projection": grace,
        "tile_plan": plan, "link_withholding": links, "lattice_edge_count": len(expanded.edges),
        "functional_candidate_receipts": receipts, "candidate_origin_groups": origins,
        "source_labels_used_at_inference": False, "production_modified": False, "formal_core_modified": False}, expanded
