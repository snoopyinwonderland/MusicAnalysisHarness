"""Research ablation: defining members and held-member step context.

No invented sounding notes, annotation lookup, chord ban or NCT exemption.
Old sealed scorers remain callable with their original globals and costs.
"""
from bisect import bisect_left
from fractions import Fraction as F
from functools import lru_cache

from . import harmony_root_context_scoring as prior
from .harmony_evidence_scoring import BASE_WEIGHTS, EVIDENCE_WEIGHTS
from .harmony_functional_scoring import shapes
from .seventh_context import chord, QUALITIES
from .harmony_candidate_recall import fraction as f, rational as q

VERSION = "harmony-component-support-scoring-0.1.0"
FEATURE_VERSION = "source-bound-component-support-features-0.1.0"
ARMS = ("control", "defining_member", "held_step", "combined")
# Fixed before the corpus run: reuse established scales; no sweep or fit.
DEFINING_WEIGHT = BASE_WEIGHTS["missing_root"]
HELD_STEP_WEIGHT = EVIDENCE_WEIGHTS["conditional_step_ornament_exposure"]


@lru_cache(maxsize=4096)
def defining_members(sig):
    """Spelled tertian templates only; functional 6-4/unknown shapes abstain.

The third, altered fifth and seventh distinguish these hypotheses. Root and
perfect fifth keep their original omission costs, not a new hard constraint.
"""
    qualities = shapes(sig)
    if len(qualities) != 1:
        return None
    quality = qualities[0]
    members = tuple(map(tuple, chord(sig[0], quality)["members"]))
    selected = [members[1]]
    if QUALITIES[quality][1] != 7:
        selected.append(members[2])
    if len(members) == 4:
        selected.append(members[3])
    return tuple(selected)


class ComponentContext(prior.RootReturnContext):
    """Reuse immutable full-source observations, memoize identical gate calls.

Memoization is not weakened validation. Each context belongs to one pinned
source/argument set; source mutation is forbidden and runner SHA-guarded.
"""
    def __init__(self, ev, grace_notes=(), context_barriers=(), history_gate=None):
        self.lowest_cache = {}
        self.gate_cache = {}
        def gate(a, b):
            if (a, b) not in self.gate_cache:
                self.gate_cache[a, b] = history_gate(a, b)
            return self.gate_cache[a, b]
        super().__init__(ev, grace_notes, context_barriers, gate if history_gate else None)
        self.step_candidates = []
        self.bridge_cache = {}
        consumed_ids = {e.event_id for e in self.source.events}
        # Full-source neighbor geometry: do not infer links by nearest pitch.
        for ident, (p0, n0) in self.source.neighbors.items():
            # A middle event outside the scoped observations cannot intersect
            # any candidate run. Keep full p/n/held clocks, restrict work only.
            if ident not in consumed_ids:
                continue
            if any(i not in self.by_id for i in (p0["id"], ident, n0["id"])):
                continue
            p, r, n = (self.by_id[i] for i in (p0["id"], ident, n0["id"]))
            if (not all(x["clock_valid"] and x["token"] is not None for x in (p, r, n))
                    or not p["identity"] or not p["identity"] == r["identity"] == n["identity"]
                    or (p["id"], r["id"]) not in self.links or (r["id"], n["id"]) not in self.links):
                continue
            pattern = self.step_group((p["start"], p["end"], (p,)),
                (r["start"], r["end"], (r,)), (n["start"], n["end"], (n,)), {p["token"], n["token"]})
            if not pattern:
                continue
            if any(lane == r["identity"] and p["start"] <= t <= n["end"] for lane, t in self.graces):
                continue
            if any(p["start"] < t <= n["end"] for t in self.barriers):
                continue
            # Sustained support is actual positive sounding time, not a union
            # of successive arpeggio attacks or a previous silent root.
            held = tuple(x for x in self.rows if x["id"] not in (p["id"], r["id"], n["id"])
                and x["clock_valid"] and x["token"] is not None
                and x["start"] <= r["start"] and r["end"] <= x["end"])
            if len({x["token"] for x in held}) < 2:
                continue
            self.step_candidates.append((p, r, n, held, pattern))
        self.step_candidates.sort(key=lambda item: (item[1]["start"], item[1]["id"]))
        self.step_starts = tuple(item[1]["start"] for item in self.step_candidates)

    def lowest(self, row, time, *, before=False):
        key = row["id"], time, before
        if key not in self.lowest_cache:
            self.lowest_cache[key] = super().lowest(row, time, before=before)
        return self.lowest_cache[key]

    def held_steps(self, start, end, sig):
        key = start, end, sig
        if key in self.bridge_cache:
            return self.bridge_cache[key]
        members = set(sig[1]); receipts = []
        stop = bisect_left(self.step_starts, end)
        for p, r, n, held, pattern in self.step_candidates[:stop]:
            if (r["end"] <= start or r["token"] in members
                    or p["token"] not in members or n["token"] not in members):
                continue
            # The old same-run pattern already earned its original credit.
            if p["start"] >= start and n["end"] <= end:
                continue
            support = [x for x in held if x["token"] in members]
            if len({x["token"] for x in support}) < 2:
                continue
            # Same exact source gate, deferred until this context can affect
            # the queried run/signature. Never skip the gate for used credit.
            if self.history_gate is not None and not self.history_gate(p["start"], n["end"]):
                continue
            receipts.append(pattern | {"kind": "held_member_cross_run_"+pattern["kind"],
                "ornament_event_id": r["id"],
                "supporting_held_event_ids": sorted(x["id"] for x in support),
                "supporting_distinct_spellings": sorted({x["token"] for x in support}),
                "credited_span": {"start": q(max(start, r["start"])), "end": q(min(end, r["end"]))},
                "context_span": {"start": q(p["start"]), "end": q(n["end"])},
                "source_note_ids": {x["id"]: list(x["source_note_ids"]) for x in (p,r,n,*support)},
                "voice_identity_confirmed": False, "harmony_held_confirmed": False,
                "prior_events_added_to_run": False, "raw_nonmember_cost_removed": False,
                "same_run_credit_double_counted": False, "source_labels_used": False})
        self.bridge_cache[key] = receipts
        return receipts


def features(problem, source, context, start, end, sig, *, index=None):
    """Direct source scan for independent audit; optional exact prefix index."""
    if index is None:
        active = [e for e in source.events if e.start < end and start < e.end]
        known = {e.pitch for e in active if e.pitch is not None}
        available = bool(known) and all(e.pitch is not None for e in active)
    else:
        i,j = index.positions[start], index.positions[end]
        known = {t for t,p in index.presence.items() if p[j] > p[i]}
        available = bool(known) and index.unresolved[j] == index.unresolved[i]
    defining = defining_members(sig)
    absent = set(defining)-known if defining is not None else set()
    value = F(len(absent), len(defining))*(end-start)/(problem.points[-1]-problem.points[0]) if available and defining else None
    details = [{"kind": "unobserved_defining_members", "span": {"start":q(start),"end":q(end)},
        "defining_members": defining, "unobserved_members": sorted(absent),
        "observed_member_event_ids": sorted(e.event_id for e in source.events if e.pitch in sig[1] and e.start < end and start < e.end),
        "omission_prohibited": False, "unobserved_notes_invented": False,
        "normalized_value": None if value is None else q(value)}] if index is None else []
    steps = context.held_steps(start,end,sig) if available else []
    credit = sum((f(r["credited_span"]["end"])-f(r["credited_span"]["start"]) for r in steps),F())/problem.total_note_time if available else None
    return {"unobserved_defining_member_exposure":value, "held_member_step_support_exposure":credit}, details+steps


def decoder(problem,ev,context,arm):
    if arm not in ARMS:
        raise ValueError("unknown_component_support_arm")
    _,Parent,base_run = prior.decoder(problem,ev,context)
    base_weights = BASE_WEIGHTS | {"root_deferred_presence":prior.temporal.ROOT_WEIGHT}
    extra_weights = dict(EVIDENCE_WEIGHTS)
    if arm in ("defining_member","combined"):
        base_weights["unobserved_defining_member_exposure"] = DEFINING_WEIGHT
    if arm in ("held_step","combined"):
        extra_weights["held_member_step_support_exposure"] = HELD_STEP_WEIGHT
    def run(p,source,a,b,sig):
        values,patterns = base_run(p,source,a,b,sig)
        if arm == "control": return values,patterns
        extra,_ = features(p,source,context,a,b,sig)
        return values | extra,patterns
    class ComponentIndex(Parent):
        def features(self,a,b,sig):
            values,patterns = super().features(a,b,sig)
            if arm == "control": return values,patterns
            extra,_ = features(self.problem,self.source,context,a,b,sig,index=self)
            return values | extra,patterns
    reconstruction = prior.temporal.bind(prior.temporal.functional.decode, {
        "BASE_WEIGHTS":base_weights, "EVIDENCE_WEIGHTS":extra_weights, "run_features":run,
        "pair_features":prior.temporal.resolution_features, "FEATURE_VERSION":FEATURE_VERSION})
    chosen = prior.temporal.bind(prior.temporal.frontier.decode, {
        "BASE_WEIGHTS":base_weights,"EVIDENCE_WEIGHTS":extra_weights,"RunIndex":ComponentIndex,
        "pair_features":prior.temporal.resolution_features,"original_decode":reconstruction})
    return chosen,ComponentIndex,run,base_weights,extra_weights


def decode(problem,ev,*,arm="combined",grace_notes=(),context_barriers=(),history_gate=None,
           functional_evidence=True,transition_budget=2_000_000):
    context = ComponentContext(ev,grace_notes,context_barriers,history_gate)
    chosen = decoder(problem,ev,context,arm)[0]
    result = chosen(problem,ev,functional_evidence=functional_evidence,transition_budget=transition_budget)
    if result["selected"] is not None:
        selected = result["selected"]
        selected["proposal_id"] = "component_"+arm+"_"+selected["proposal_id"]
        selected["component_support_observations"] = [d for r in selected["harmonic_runs"]
            for d in features(problem,ev.source,context,f(r["span"]["start"]),f(r["span"]["end"]),
                (tuple(r["root_spelling"]) if r["root_spelling"] is not None else None,tuple(map(tuple,r["members"]))))[1]]
    result["component_support_contract"] = {"version":VERSION,"arm":arm,
        "defining_weight":q(DEFINING_WEIGHT),"held_step_weight":q(HELD_STEP_WEIGHT),
        "training_performed":False,"source_labels_used":False,"omission_prohibited":False,
        "raw_nonmember_cost_removed":False,"new_scoring_contract":arm!="control"}
    result["search_diagnostics"]["score_weights_changed"] = True
    return result


def score_path(problem,ev,ids,*,arm="combined",grace_notes=(),context_barriers=(),history_gate=None,functional_evidence=True):
    context = ComponentContext(ev,grace_notes,context_barriers,history_gate)
    _,_,run,base_weights,extra_weights = decoder(problem,ev,context,arm)
    return prior.temporal.bind(prior.temporal.functional.score_path,{
        "BASE_WEIGHTS":base_weights,"EVIDENCE_WEIGHTS":extra_weights,"run_features":run,
        "pair_features":prior.temporal.resolution_features})(problem,ev,ids,functional_evidence=functional_evidence)
