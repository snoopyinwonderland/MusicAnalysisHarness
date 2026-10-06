"""Research-only contextual attenuation of delayed-root cost.

A recent LOWEST root returning through one explicit source lane may support
an omitted/arpeggiated root explanation. This never makes that root sound
retroactively and never exempts nonmembers. No work IDs or annotations enter.
The original temporal scorer remains sealed and independently callable.
"""
from bisect import bisect_left, bisect_right
from collections import defaultdict
from fractions import Fraction as F

from . import harmony_temporal_scoring as temporal
from .harmony_evidence_scoring import BASE_WEIGHTS, metric, run_features
from .harmony_reading_voice_context import spelled_height
from .harmony_candidate_recall import fraction as f, rational as q

VERSION = "harmony-root-context-scoring-0.1.0"
FEATURE_VERSION = "source-bound-root-return-features-0.1.0"
# Fixed before the corpus run. Not a probability, fit, or parameter sweep.
SUPPORTED_DELAY_FACTOR = F(1, 2)
ARMS = ("baseline", "meter_credit", "combined", "bass_return")


class RootReturnContext:
    """Full original geometry, including pre-scope history, without clipping.

One lane can contain a simultaneous notated group; unequal-duration overlaps
remain ambiguous. Grace notation is an explicit barrier, not erased timing.
"""
    def __init__(self, ev, grace_notes=(), context_barriers=(), history_gate=None):
        self.source = ev.source
        self.rows = tuple(ev.rows)
        self.by_id = {r["id"]: r for r in self.rows}
        self.links = {(p["id"], n["id"]) for p, n in ev.links}
        self.graces = tuple(((n.get("part_id"), n.get("voice_id")), f(n["global_onset_quarter"]))
                            for n in grace_notes)
        self.barriers = tuple(context_barriers)
        self.history_gate = history_gate
        lanes = defaultdict(lambda: defaultdict(list)); roots = defaultdict(list)
        for r in self.rows:
            if r["identity"] is not None:
                lanes[r["identity"]][r["start"], r["end"]].append(r)
            if r["token"] is not None: roots[r["token"]].append(r)
        self.groups = {lane: [(a, b, tuple(rs)) for (a, b), rs in sorted(groups.items())]
                       for lane, groups in lanes.items()}
        self.starts = {lane: tuple(a for a, _, _ in gs) for lane, gs in self.groups.items()}
        self.roots = {root: sorted(rs, key=lambda r: (r["end"], r["id"])) for root, rs in roots.items()}
        self.root_ends = {root: tuple(r["end"] for r in rs) for root, rs in self.roots.items()}
        self.cache = {}

    def lowest(self, row, time, *, before=False):
        active = [r for r in self.rows if (r["start"] < time <= r["end"] if before
                  else r["start"] <= time < r["end"])]
        if not active or any(not r["clock_valid"] or r["token"] is None for r in active): return False
        return row["pitch"] == min(r["pitch"] for r in active)

    def step_group(self, previous, middle, following, members):
        if any(len(g[2]) != 1 for g in (previous, middle, following)): return None
        p, r, n = (g[2][0] for g in (previous, middle, following))
        strength, unit = metric(self.source, r["start"])
        if (strength is None or strength > 1 or r["end"]-r["start"] > unit/2
                or p["token"] not in members or n["token"] not in members
                or (p["id"], r["id"]) not in self.links or (r["id"], n["id"]) not in self.links): return None
        heights = [spelled_height(x["pitch_data"]) for x in (p, r, n)]
        if any(h is None for h in heights): return None
        dp, dn = r["pitch"]-p["pitch"], n["pitch"]-r["pitch"]
        if not (abs(heights[1]-heights[0]) == abs(heights[2]-heights[1]) == 1
                and 0 < abs(dp) <= 2 and 0 < abs(dn) <= 2): return None
        kind = "neighbor_like" if p["pitch_data"] == n["pitch_data"] else "passing_like" if dp*dn > 0 else None
        return {"kind": kind, "source_event_ids": [p["id"], r["id"], n["id"]],
                "confirmed_nct": False, "membership_exempted": False} if kind else None

    def support(self, start, first, sig):
        key = start, first, sig
        if key in self.cache: return self.cache[key]
        result = self._support(start, first, sig)
        self.cache[key] = result
        return result

    def _support(self, start, first, sig):
        root, members = sig; members = set(members)
        _, unit = metric(self.source, start)
        if first <= start or unit is None or root is None: return []
        # Full-source prior anchors are CONTEXT ONLY; never add them to the
        # run observations, total-note-time, candidate edges or selected spans.
        rs = self.roots.get(root, ()); ends = self.root_ends.get(root, ())
        anchors = rs[bisect_left(ends, start-unit):bisect_right(ends, start)]
        arrivals = [self.by_id[e.event_id] for e in self.source.events if e.pitch == root
                    and max(start, e.start) == first and e.event_id in self.by_id]
        for anchor in reversed(anchors):
            lane = anchor["identity"]
            if not lane or not anchor["clock_valid"] or not self.lowest(anchor, anchor["end"], before=True): continue
            returning = [r for r in arrivals if r["identity"] == lane and r["clock_valid"]
                         and self.lowest(r, first)]
            if not returning: continue
            groups = self.groups[lane]; times = self.starts[lane]
            lo = bisect_left(times, anchor["start"]); hi = bisect_right(times, first)
            chain = groups[lo:hi]
            if (not chain or chain[0][0] != anchor["start"] or chain[0][1] != anchor["end"]
                    or chain[-1][0] != first or not any(r in chain[-1][2] for r in returning)
                    or any(a[1] != b[0] for a, b in zip(chain, chain[1:]))): continue
            # An earlier unequal-duration overlapping group invalidates the
            # proposed chain, even when its onset precedes the chosen anchor.
            if any(g[1] > anchor["start"] for g in groups[:lo]): continue
            if any(ident == lane and anchor["start"] <= t <= first for ident, t in self.graces): continue
            if any(anchor["start"] < t <= first for t in self.barriers): continue
            if self.history_gate is not None and not self.history_gate(anchor["start"], chain[-1][1]): continue
            if any(not r["clock_valid"] or r["token"] is None for _, _, g in chain for r in g): continue
            patterns = []; compatible = True
            for i, (_, _, rows) in enumerate(chain):
                if all(r["token"] in members for r in rows): continue
                pattern = self.step_group(chain[i-1], chain[i], chain[i+1], members) if 0 < i < len(chain)-1 else None
                if pattern is None: compatible = False; break
                patterns.append(pattern)
            if not compatible: continue
            # Two distinct other members must actually sound in the delayed
            # prefix. A root-return melody alone is not harmonic support.
            prefix = [r for r in self.rows if r["start"] < first and start < r["end"]]
            if any(not r["clock_valid"] or r["token"] is None for r in prefix): continue
            observed = {r["token"] for r in prefix if r["token"] in members and r["token"] != root}
            if len(observed) < 2: continue
            before = [r for r in self.rows if r["start"] < first <= r["end"]]
            after = [r for r in self.rows if r["start"] <= first < r["end"]]
            bt, at = {r["token"] for r in before}, {r["token"] for r in after}
            return [{"kind": "conditional_recent_lowest_root_return", "root_spelling": root,
                "prior_root_event_id": anchor["id"], "prior_root_span": {"start": q(anchor["start"]), "end": q(anchor["end"])},
                "lookback_notated_beat_unit": q(unit), "return_root_event_ids": sorted(r["id"] for r in returning),
                "history_clock_gate_accepted": True if self.history_gate is not None else None,
                "original_explicit_lane": lane, "voice_identity_confirmed": False,
                "source_event_ids": sorted({r["id"] for _, _, g in chain for r in g}),
                "prefix_member_event_ids": sorted(r["id"] for r in prefix if r["token"] in observed),
                "prefix_distinct_nonroot_members": sorted(observed), "conditional_step_patterns": patterns,
                "held_across_root_arrival_ids": sorted({r["id"] for r in before} & {r["id"] for r in after}),
                "lost_spelling_at_arrival": sorted(bt-at), "gained_spelling_at_arrival": sorted(at-bt),
                "delay_cost_factor": q(SUPPORTED_DELAY_FACTOR), "earlier_root_was_sounding_in_run": False,
                "harmony_held_confirmed": False, "nonmember_cost_removed": False,
                "source_labels_used": False, "performed_grace_time_invented": False}]
        return []


def context_delay(problem, source, context, start, end, sig):
    value, receipt = temporal.deferred_root(problem, source, start, end, sig)
    if value is None or not value: return value, receipt
    first = f(receipt[0]["first_positive_root_time"])
    support = context.support(start, first, sig)
    return value*(SUPPORTED_DELAY_FACTOR if support else 1), receipt+support


def decoder(problem, ev, context):
    weights = BASE_WEIGHTS | {"root_deferred_presence": temporal.ROOT_WEIGHT}
    def run(p, source, a, b, sig):
        values, patterns = run_features(p, source, a, b, sig)
        return values | {"root_deferred_presence": context_delay(p, source, context, a, b, sig)[0]}, patterns
    class ContextIndex(temporal.TemporalIndex):
        def features(self, a, b, sig):
            values, patterns = super().features(a, b, sig)
            value = values["root_deferred_presence"]
            if value:
                i, j = self.positions[a], self.positions[b]; exposure = self.presence[sig[0]]
                k = bisect_right(exposure, exposure[i], i+1, j+1)
                if context.support(a, self.points[k-1], sig): values = values | {"root_deferred_presence": value*SUPPORTED_DELAY_FACTOR}
            return values, patterns
    reconstruction = temporal.bind(temporal.functional.decode, {"BASE_WEIGHTS": weights, "run_features": run,
        "pair_features": temporal.resolution_features, "FEATURE_VERSION": FEATURE_VERSION})
    chosen = temporal.bind(temporal.frontier.decode, {"BASE_WEIGHTS": weights, "RunIndex": ContextIndex,
        "pair_features": temporal.resolution_features, "original_decode": reconstruction})
    return chosen, ContextIndex, run


def decode(problem, ev, *, arm="bass_return", grace_notes=(), context_barriers=(), history_gate=None,
           functional_evidence=True, transition_budget=2_000_000):
    if arm not in ARMS: raise ValueError("unknown_root_context_arm")
    context = RootReturnContext(ev, grace_notes, context_barriers, history_gate)
    if arm != "bass_return":
        result = temporal.decode(problem, ev, arm=arm, functional_evidence=functional_evidence, transition_budget=transition_budget)
    else:
        result = decoder(problem, ev, context)[0](problem, ev, functional_evidence=functional_evidence, transition_budget=transition_budget)
        if result["selected"] is not None:
            selected = result["selected"]; selected["proposal_id"] = "root_context_"+selected["proposal_id"]
            selected["root_context_observations"] = [d for r in selected["harmonic_runs"]
                for d in context_delay(problem, ev.source, context, f(r["span"]["start"]), f(r["span"]["end"]),
                    (tuple(r["root_spelling"]) if r["root_spelling"] is not None else None,
                     tuple(tuple(m) for m in r["members"])))[1]]
    result["root_context_contract"] = {"version": VERSION, "arm": arm,
        "supported_delay_factor": q(SUPPORTED_DELAY_FACTOR) if arm == "bass_return" else None,
        "new_scoring_contract": arm == "bass_return", "source_labels_used": False,
        "prior_events_added_to_run": False, "nonmember_cost_removed": False, "training_performed": False}
    result["search_diagnostics"]["score_weights_changed"] = arm != "baseline"
    return result


def score_path(problem, ev, ids, *, arm="bass_return", grace_notes=(), context_barriers=(), history_gate=None,
               functional_evidence=True):
    if arm not in ARMS: raise ValueError("unknown_root_context_arm")
    if arm != "bass_return": return temporal.score_path(problem, ev, ids, arm=arm, functional_evidence=functional_evidence)
    context = RootReturnContext(ev, grace_notes, context_barriers, history_gate); run = decoder(problem, ev, context)[2]
    return temporal.bind(temporal.functional.score_path, {
        "BASE_WEIGHTS": BASE_WEIGHTS | {"root_deferred_presence": temporal.ROOT_WEIGHT},
        "run_features": run, "pair_features": temporal.resolution_features})(
            problem, ev, ids, functional_evidence=functional_evidence)
