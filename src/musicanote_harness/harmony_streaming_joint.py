"""Tile-streamed exact joint selection, not tile-wise chord winners.

Only topology storage changes. Run starts, raw counts, exact score, spelled
signatures and lexicographic paths survive tile seams. A cumulative 2M work
cap is never reset by a checkpoint. Missing future topology uses a SAFE lower
bound, not an invented chord or a beam. Source/repeat blockers are retained.
"""
from collections import OrderedDict, defaultdict
from copy import deepcopy
from dataclasses import replace, asdict, is_dataclass
from fractions import Fraction as F
from math import lcm

from . import harmony_bounded_recovery as bounded
from .harmony_batched_frontier import scoped_functional_evidence
from .harmony_exact_frontier import RunIndex, canonical_edges, pareto
from .harmony_evidence_scoring import BASE_WEIGHTS, EVIDENCE_WEIGHTS
from .harmony_functional_scoring import (PAIR_WEIGHTS, ROLE_COST, dominant_pairs, shapes,
    six_four_surface, pair_features, role_cost, decode as original_decode, supply)
from .harmony_candidate_recall import fraction as f, rational as q
from .harmony_scored_decoder import DEFAULT_WEIGHTS, feature_cost, transition, Problem, Edge
from .harmony_window_workspace import WindowWorkspace
from .harmony_progression_search import _hash

VERSION = "harmony-streaming-joint-0.1.0"
CONFIG = {"page_candidate_edges": 20000, "live_states": 100000,
          "memo_entries": 4096, "signature_integrals": 64,
          "maximum_members": 7, "decoder_operations": 2000000}
RESOURCE_BLOCKERS = {"global_cell_budget_no_truncation", "global_sound_budget_no_pruning"}


def packed(value):
    if isinstance(value, F): return q(value)
    if is_dataclass(value): return packed(asdict(value))
    if isinstance(value, dict): return {k: packed(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)): return [packed(v) for v in sorted(value, key=repr)]
    if isinstance(value, (tuple, list)): return [packed(v) for v in value]
    return value


def evidence_binding(ev):
    s = ev.source
    return _hash(packed({"source_sha": s.source_ir_content_sha256, "events": s.events,
        "measures": s.measures, "measure_times": s._measure_times, "rows": s.rows,
        "neighbors": s.neighbors, "voice_statuses": s.voice_statuses,
        "functional_rows": ev.rows, "functional_links": ev.links,
        "functional_voice_statuses": ev.voice_statuses}))


class Memo:
    def __init__(self, limit):
        self.limit = limit; self.values = OrderedDict(); self.computations = 0; self.evictions = 0

    def get(self, key, compute):
        if key in self.values:
            value = self.values.pop(key)
        else:
            value = compute(); self.computations += 1
        self.values[key] = value
        if len(self.values) > self.limit:
            self.values.popitem(last=False); self.evictions += 1
        return value


def streaming_plan(view, span):
    plan = bounded.tile_plan(view, span)
    # Only global storage guards can be superseded by page storage. The old
    # per-tile policy, fine clock grid and every musical/source barrier remain.
    if plan["status"] == "bounded_plan_abstention":
        old = set(plan["blockers"]); remaining = old-RESOURCE_BLOCKERS
        plan.update(status="ready" if not remaining else "bounded_plan_abstention",
                    blockers=sorted(remaining), superseded_global_storage_guards=sorted(old & RESOURCE_BLOCKERS))
    plan["streaming_resource_contract"] = dict(CONFIG)
    return plan


def header(view, plan, evidence):
    points = tuple(f(t) for t in plan["points"])
    total = sum((min(e.end, points[-1])-max(e.start, points[0]) for e in evidence.events), F())
    status = plan["status"] if total > 0 else "no_positive_sounding_exposure"
    return Problem(points, (), plan.get("global_raw_edge_budget", 0), total, status)


def build_page(workspace, plan, tile, evidence, functional):
    one = deepcopy(plan); one["tiles"] = [deepcopy(tile)]
    problem, origins = workspace.build(one, evidence)
    if problem.status != "ready": return problem, origins, []
    expanded, receipts = supply(problem, functional)
    if len(expanded.edges) > CONFIG["page_candidate_edges"]:
        expanded = replace(expanded, edges=(), status="stream_page_candidate_budget_abstention")
    return expanded, origins, receipts


def encode_edge(edge):
    return {"group_id": edge.group_id, "start_index": edge.start_index, "end_index": edge.end_index,
        "start": q(edge.start), "end": q(edge.end), "signature": edge.signature,
        "features": {k: None if v is None else q(v) for k, v in edge.features.items()},
        "attack_spellings": sorted(edge.attack_spellings), "source_event_ids": edge.source_event_ids,
        "blockers": edge.blockers, "adapter": edge.adapter}


def decode_edge(row):
    root, members = row["signature"]
    sig = None if root is None else tuple(root), tuple(tuple(m) for m in members)
    return Edge(row["group_id"], row["start_index"], row["end_index"], f(row["start"]), f(row["end"]), sig,
        {k: None if v is None else f(v) for k, v in row["features"].items()},
        frozenset(tuple(p) for p in row["attack_spellings"]), tuple(row["source_event_ids"]),
        tuple(row["blockers"]), deepcopy(row["adapter"]))


class JointStream:
    """One full-score objective with immutable source/topology binding.

    consume() commits a complete computational page. snapshot() can be stored
    and restored between pages; caches are disposable exact recomputations.
    A resource abort is terminal, with no provisional selected harmony.
    Caller must pin page artifacts and load only original winning edges.
    """
    def __init__(self, problem, ev, page_ranges, *, operation_budget=None, memo_entries=None,
                 functional_evidence=True, checkpoint=None):
        self.problem = problem; self.original_ev = ev
        self.ev = scoped_functional_evidence(problem, ev)
        self.ranges = tuple(tuple(r) for r in page_ranges)
        if (problem.status != "ready" or len(problem.points) < 2 or problem.total_note_time <= 0
                or type(problem.max_segments) is not int or problem.max_segments <= 0
                or any(a >= b for a, b in zip(problem.points, problem.points[1:]))):
            raise ValueError("invalid_stream_problem")
        if (not self.ranges or self.ranges[0][0] != 0 or self.ranges[-1][1] != len(problem.points)-1
                or any(type(i) is not int for r in self.ranges for i in r)
                or any(a >= b for a, b in self.ranges)
                or any(a[1] != b[0] for a, b in zip(self.ranges, self.ranges[1:]))):
            raise ValueError("invalid_stream_page_partition")
        self.budget = CONFIG["decoder_operations"] if operation_budget is None else operation_budget
        limit = CONFIG["memo_entries"] if memo_entries is None else memo_entries
        if type(self.budget) is not int or self.budget < 1 or type(limit) is not int or limit < 1:
            raise ValueError("invalid_stream_budget")
        self.enabled = functional_evidence; self.weights = BASE_WEIGHTS | EVIDENCE_WEIGHTS
        self.evidence_sha = evidence_binding(ev)
        source = self.ev.source
        times = (*problem.points, *(t for e in source.events for t in (e.start, e.end)), *source._measure_times)
        mult = lcm(*range(1, max(6, 2*CONFIG["maximum_members"], len(source.events))+1))
        self.scale = (2*lcm(*(t.denominator for t in times))*problem.total_note_time.numerator
            *(problem.points[-1]-problem.points[0]).numerator
            *lcm(*(v.denominator for v in (*self.weights.values(), *PAIR_WEIGHTS.values(), ROLE_COST)))*mult)
        self.binding = _hash({"version": VERSION, "source": source.source_ir_content_sha256,
            "points": [q(t) for t in problem.points], "total": q(problem.total_note_time),
            "raw_cap": problem.max_segments, "ranges": self.ranges, "config": CONFIG,
            "budget": self.budget, "functional_evidence": self.enabled, "evidence": self.evidence_sha,
            "weights": packed(self.weights | PAIR_WEIGHTS | {"role_cost": ROLE_COST})})
        self.indexer = RunIndex(problem, source)
        self.runs = Memo(limit); self.pairs = Memo(limit); self.transitions = Memo(limit)
        self.at = 0; self.operations = 0; self.status = "stream_pending"
        self.frontier = {(0, None, None): (0, ())}; self.seen = set()
        self.stats = {"pages_consumed": 0, "original_edges": 0, "representative_edges": 0,
            "equivalent_edge_groups": 0, "logical_transitions_represented": 0,
            "pareto_states_removed": 0, "states_expanded": 0, "peak_live_states": 1,
            "beam_pruning": False, "score_weights_changed": False,
            "cumulative_budget_never_reset": True, "future_reachability": "safe_page_count_lower_bound",
            "tile_winner_stitching": False}
        if checkpoint is not None:
            if checkpoint.get("binding_sha256") != self.binding or checkpoint.get("seal") != _hash({k:v for k,v in checkpoint.items() if k != "seal"}):
                raise ValueError("stream_checkpoint_binding_or_seal_changed")
            self.at = checkpoint["next_page"]; self.operations = checkpoint["operations"]
            if type(self.at) is not int or not 0 <= self.at <= len(self.ranges) or not 0 <= self.operations <= self.budget:
                raise ValueError("invalid_stream_checkpoint_cursor")
            self.frontier = {}
            for row in checkpoint["frontier"]:
                root, members = row["signature"] if row["signature"] is not None else (None, ())
                sig = (None if root is None else tuple(root), tuple(tuple(m) for m in members)) if row["signature"] is not None else None
                key = row["count"], row["run_start"], sig
                if key in self.frontier: raise ValueError("duplicate_stream_checkpoint_state")
                self.frontier[key] = row["cost_units"], tuple(row["ids"])
            self.seen = set(checkpoint["seen_edge_ids"]); self.stats = deepcopy(checkpoint["statistics"])

    def check_evidence(self):
        if evidence_binding(self.original_ev) != self.evidence_sha:
            self.status = "stream_binding_invalid"
            raise ValueError("stream_source_evidence_changed")

    def units(self, value):
        value *= self.scale
        if value.denominator != 1: raise ValueError("stream_score_scale_not_exact")
        return value.numerator

    def run_cost(self, a, b, sig):
        def compute():
            values, _ = self.indexer.features(self.problem.points[a], self.problem.points[b], sig)
            result = self.units(feature_cost(values, self.weights)+role_cost(sig))
            # Prefix integrals are exact; eviction changes only recomputation.
            if len(self.indexer.by_signature) > CONFIG["signature_integrals"]:
                del self.indexer.by_signature[next(iter(self.indexer.by_signature))]
            return result
        return self.runs.get((a, b, sig), compute)

    def pair_cost(self, a, b, edge, previous):
        if not self.enabled or not ((six_four_surface(previous) and previous[0] == edge.signature[0]
                and any(s in ("M", "Mm7") for s in shapes(edge.signature))) or dominant_pairs(previous, edge.signature)):
            return 0
        def compute():
            values, _ = pair_features(self.ev, self.problem.points[a], self.problem.points[b], edge.end, previous, edge.signature)
            value = self.units(feature_cost(values, PAIR_WEIGHTS))
            self.ev._pair_cache.clear(); self.ev._surface_cache.clear()
            return value
        return self.pairs.get((a, b, previous, edge.signature), compute)

    def consume(self, page):
        self.check_evidence()
        if self.status != "stream_pending" or self.at >= len(self.ranges): raise ValueError("stream_terminal_or_complete")
        if (page.points, page.total_note_time, page.max_segments) != (self.problem.points, self.problem.total_note_time, self.problem.max_segments):
            raise ValueError("stream_page_objective_changed")
        if page.status != "ready": self.status = page.status; return self.receipt()
        lo, hi = self.ranges[self.at]
        if any(not lo <= e.start_index < e.end_index <= hi for e in page.edges): raise ValueError("stream_page_crosses_partition")
        if any(len(e.signature[1]) > CONFIG["maximum_members"] for e in page.edges): raise ValueError("stream_member_contract_exceeded")
        if self.seen.intersection(e.group_id for e in page.edges): raise ValueError("duplicate_stream_edge_id")
        edges, aliases = canonical_edges(page)
        self.seen.update(e.group_id for e in page.edges)
        self.stats["original_edges"] += len(page.edges); self.stats["representative_edges"] += len(edges)
        self.stats["equivalent_edge_groups"] += len(aliases)
        outgoing = defaultdict(list)
        for e in edges: outgoing[e.start_index].append(e)
        states = {lo: self.frontier}; future = len(self.ranges)-self.at-1
        def remaining(index): return future+int(index < hi)
        blockers = {e.group_id: self.units(DEFAULT_WEIGHTS["blocker_exposure"]*e.features.get("blocker_exposure", F())) for e in edges}
        def put(end, key, value):
            target = states.setdefault(end, {}); old = target.get(key)
            if old is None or value < old: target[key] = value
        def tick():
            if self.operations >= self.budget: self.status = "stream_operation_budget_abstention"; return False
            self.operations += 1; return True
        for index in range(lo, hi):
            live = sum(len(s) for s in states.values())
            self.stats["peak_live_states"] = max(self.stats["peak_live_states"], live)
            if live > CONFIG["live_states"]: self.status = "stream_live_state_budget_abstention"; break
            current, removed = pareto({k:v for k,v in states.pop(index, {}).items()
                                      if k[0]+remaining(index) <= self.problem.max_segments})
            self.stats["pareto_states_removed"] += removed; self.stats["states_expanded"] += len(current)
            groups = defaultdict(list); by_previous = defaultdict(list)
            for e in outgoing[index]: groups[e.signature, e.attack_spellings].append(e)
            for key, value in current.items(): by_previous[key[2]].append((key, value))
            for (sig, attacks), group in groups.items():
                proto = group[0]; shortest = min(remaining(e.end_index) for e in group)
                best = {}; counts = defaultdict(int)
                for (count, a, previous), (cost, ids) in current.items():
                    if previous == sig or count+1+shortest > self.problem.max_segments: continue
                    if not tick(): return self.receipt()
                    counts[count] += 1
                    tcost = self.transitions.get((previous, sig, attacks), lambda: self.units(feature_cost(transition(previous, proto), self.weights)))
                    value = cost+tcost+(self.pair_cost(a, index, proto, previous) if previous is not None else 0), ids
                    if count not in best or value < best[count]: best[count] = value
                for e in group:
                    for count, (cost, ids) in best.items():
                        if count+1+remaining(e.end_index) > self.problem.max_segments: continue
                        if not tick(): return self.receipt()
                        self.stats["logical_transitions_represented"] += counts[count]
                        put(e.end_index, (count+1, index, sig), (cost+self.run_cost(index, e.end_index, sig)+blockers[e.group_id], ids+(e.group_id,)))
                    for (count, a, _), (cost, ids) in by_previous.get(sig, ()):
                        if count+1+remaining(e.end_index) > self.problem.max_segments: continue
                        if not tick(): return self.receipt()
                        self.stats["logical_transitions_represented"] += 1
                        put(e.end_index, (count+1, a, sig), (cost+self.run_cost(a, e.end_index, sig)-self.run_cost(a, index, sig)+blockers[e.group_id], ids+(e.group_id,)))
            if self.status != "stream_pending": break
        if self.status == "stream_pending":
            self.frontier = states.get(hi, {}); self.at += 1; self.stats["pages_consumed"] = self.at
        self.check_evidence()
        return self.receipt()

    def receipt(self):
        return {"status": self.status, "operations": self.operations, "next_page": self.at,
            "statistics": deepcopy(self.stats), "selected": None, "exact_optimum_under_declared_score": False,
            "cache_computations": {"runs": self.runs.computations, "pairs": self.pairs.computations,
                                   "transitions": self.transitions.computations},
            "cache_evictions": self.runs.evictions+self.pairs.evictions+self.transitions.evictions}

    def snapshot(self):
        self.check_evidence()
        if self.status != "stream_pending": raise ValueError("aborted_stream_not_checkpointable")
        value = {"version": VERSION, "binding_sha256": self.binding, "next_page": self.at,
            "operations": self.operations, "statistics": deepcopy(self.stats), "seen_edge_ids": sorted(self.seen),
            "frontier": [{"count": c, "run_start": a, "signature": sig, "cost_units": cost, "ids": ids}
                         for (c, a, sig), (cost, ids) in self.frontier.items()]}
        value["seal"] = _hash(value)
        return value

    def finish(self, load_edges):
        self.check_evidence()
        result = self.receipt()
        if self.status != "stream_pending": return result
        if self.at != len(self.ranges): raise ValueError("incomplete_stream_not_a_prediction")
        if not self.frontier:
            return result | {"status": "no_complete_path_under_segment_cap", "exact_optimum_under_declared_score": True}
        cost, ids = min(self.frontier.values()); edges = tuple(load_edges(ids))
        if tuple(e.group_id for e in edges) != ids: raise ValueError("stream_selected_edge_ledger_changed")
        chosen = original_decode(replace(self.problem, edges=edges), self.original_ev,
            functional_evidence=self.enabled, transition_budget=max(1, len(ids)))
        selected = chosen["selected"]
        if (selected is None or selected["score_cost"] != q(F(cost, self.scale))
                or tuple(s["semantic_group_ref"] for s in selected["segments"]) != ids):
            raise ValueError("stream_original_winner_score_or_path_mismatch")
        return result | {"status": chosen["status"], "selected": selected,
            "exact_optimum_under_declared_score": True, "winner_checked_with_original_features": True}


def decode(problem, ev, *, functional_evidence=True, transition_budget=2000000):
    """One-page compatibility proof, not the long-score page generator."""
    if type(transition_budget) is not int or transition_budget < 1: raise ValueError("invalid_transition_budget")
    if problem.status != "ready":
        return {"status": problem.status, "selected": None, "transitions": 0,
                "exact_optimum_under_declared_score": False, "search_diagnostics": {}}
    stream = JointStream(problem, ev, [(0, len(problem.points)-1)],
        functional_evidence=functional_evidence, operation_budget=transition_budget)
    stream.consume(problem); by_id = {e.group_id: e for e in problem.edges}
    result = stream.finish(lambda ids: [by_id[gid] for gid in ids])
    return result | {"transitions": result["operations"], "search_diagnostics": result["statistics"]}
