"""Research joint chord/conditional-NCT transition score; not an NCT classifier.

Preparation and arrival belong to the actually competing adjacent signatures.
Only arrival evidence is used, so the pair cost is independent of raw right
edge duration. Existing run costs, raw nonmembers and sealed code are retained.
"""
from collections import defaultdict
from dataclasses import replace
from fractions import Fraction as F
from math import lcm

from . import harmony_component_support_scoring as component
from .harmony_batched_frontier import scoped_functional_evidence
from .harmony_exact_frontier import canonical_edges, pareto
from .harmony_functional_scoring import PAIR_WEIGHTS, ROLE_COST, role_cost, dominant_pairs, six_four_surface, shapes
from .harmony_scored_decoder import DEFAULT_WEIGHTS, feature_cost, transition
from .harmony_candidate_recall import fraction as f, rational as q

VERSION = "harmony-joint-nct-scoring-0.1.0"
FEATURE_VERSION = "selected-transition-held-step-features-0.1.0"
ARMS = ("control", "selected_roles", "shared_support")
STEP_WEIGHT = component.HELD_STEP_WEIGHT
STEP_FEATURE = "selected_transition_step_exposure"


class JointContext(component.ComponentContext):
    def __init__(self, ev, **kwargs):
        super().__init__(ev, **kwargs)
        self.at_boundary = defaultdict(list)
        for item in self.step_candidates:
            self.at_boundary[item[1]["end"]].append(item)
        self.joint_cache = {}

    def assess(self, problem, start, boundary, left, right, arm):
        """A completed left run + actual right onset, not a borrowed future.

The middle must end exactly at this transition. The preparation must be
inside the left run. No credit for a triple crossing several unknown chords.
An event's membership here concerns its arrival only, not its full duration.
"""
        if arm not in ARMS:
            raise ValueError("unknown_joint_nct_arm")
        if arm == "control" or boundary not in self.at_boundary: return F(), []
        key = start, boundary, left, right, arm
        if key in self.joint_cache: return self.joint_cache[key]
        lm, rm = set(left[1]), set(right[1]); details = []; value = F()
        for p, r, n, held, pattern in self.at_boundary.get(boundary, ()):
            if p["start"] < start or r["token"] in lm:
                continue
            reasons = []
            if p["token"] not in lm: reasons.append("preparation_not_left_member")
            if n["token"] not in lm: reasons.append("not_step_between_left_members")
            if n["token"] not in rm: reasons.append("arrival_not_selected_right_member")
            support = [x for x in held if x["token"] in lm]
            if len({x["token"] for x in support}) < 2:
                reasons.append("fewer_than_two_actual_left_members_held")
            shared = [x for x in support if x["token"] in rm and x["end"] > boundary]
            if arm == "shared_support" and len({x["token"] for x in shared}) < 2:
                reasons.append("fewer_than_two_actual_shared_members_at_arrival")
            if not reasons and self.history_gate is not None and not self.history_gate(p["start"], n["end"]):
                reasons.append("source_clock_context_withheld")
            credited = not reasons
            if credited: value += (r["end"]-r["start"])/problem.total_note_time
            details.append(pattern | {
                "kind": "selected_transition_"+pattern["kind"],
                "status": "conditional_support" if credited else "withheld",
                "arm": arm, "boundary": q(boundary),
                "left_span": {"start": q(start), "end": q(boundary)},
                "left_signature": left, "right_signature": right,
                "middle_event_id": r["id"], "preparation_event_id": p["id"], "arrival_event_id": n["id"],
                "supporting_held_event_ids": sorted(x["id"] for x in support),
                "shared_held_event_ids": sorted(x["id"] for x in shared),
                "shared_held_spellings": sorted({x["token"] for x in shared}),
                "context_span": {"start": q(p["start"]), "end": q(n["end"])},
                "credited_span": {"start": q(r["start"]), "end": q(r["end"])} if credited else None,
                "normalized_exposure": q((r["end"]-r["start"])/problem.total_note_time) if credited else None,
                "source_note_ids": {x["id"]: list(x["source_note_ids"]) for x in (p,r,n,*support)},
                "withheld_reasons": reasons, "confirmed_nct": False,
                "harmony_held_confirmed": False, "voice_identity_confirmed": False,
                "arrival_only_membership": True, "future_run_end_assumed": False,
                "raw_nonmember_cost_removed": False, "same_run_credit_double_counted": False,
                "source_labels_used": False,
            })
        self.joint_cache[key] = value, details
        return value, details


def completed_runs(problem, ids):
    by_id = {e.group_id: e for e in problem.edges}; runs = []; end = problem.points[0]
    for ident in ids:
        e = by_id[ident]
        if e.start != end: raise ValueError("noncontiguous_joint_path")
        if runs and runs[-1][2] == e.signature: runs[-1] = runs[-1][0], e.end, e.signature
        else: runs.append((e.start, e.end, e.signature))
        end = e.end
    if end != problem.points[-1]: raise ValueError("incomplete_joint_path")
    return runs


def path_observations(problem, ev, ids, *, arm, context=None, **kwargs):
    context = context or JointContext(ev, **kwargs); runs = completed_runs(problem, ids)
    return [detail for (a,b,left), (_,_,right) in zip(runs,runs[1:])
            for detail in context.assess(problem,a,b,left,right,arm)[1]]


def score_path(problem, ev, ids, *, arm="shared_support", functional_evidence=True, **kwargs):
    if arm not in ARMS: raise ValueError("unknown_joint_nct_arm")
    base = component.score_path(problem,ev,ids,arm="control",functional_evidence=functional_evidence,**kwargs)
    if arm == "control" or not functional_evidence: return base
    context = JointContext(ev,**kwargs); runs = completed_runs(problem,ids)
    return base+STEP_WEIGHT*sum((context.assess(problem,a,b,l,r,arm)[0]
        for (a,b,l),(_,_,r) in zip(runs,runs[1:])),F())


def decode(problem, ev, *, arm="shared_support", functional_evidence=True,
           transition_budget=2_000_000, **kwargs):
    """Exact factored DP; pair dependency is part of search, not reranking.

The same future signature/attack set shares the same arrival-only pair cost.
Run start is retained; raw-edge subdivisions do not create extra NCT credit.
"""
    if arm not in ARMS: raise ValueError("unknown_joint_nct_arm")
    if type(transition_budget) is not int or transition_budget <= 0:
        raise ValueError("invalid_transition_budget")
    context = JointContext(ev,**kwargs)
    _,Index,_,weights,extras = component.decoder(problem,ev,context,"control")
    weights = weights | extras
    stats = {"operation_unit":"predecessor_comparison_or_factored_edge_emission_or_same_run_extension",
        "logical_transitions_represented":0,"pareto_states_removed":0,"cap_infeasible_operations_skipped":0,
        "states_expanded":0,"peak_endpoint_states":0,"run_cost_evaluations":0,"pair_cost_evaluations":0,
        "beam_pruning":False,"score_weights_changed":arm!="control",
        "numeric_budget_unchanged_operation_unit_changed":True}
    operations = 0
    def result(status,selected,exact):
        return {"status":status,"selected":selected,"transitions":operations,
            "exact_optimum_under_declared_score":exact,"search_diagnostics":stats,
            "joint_nct_contract":{"version":VERSION,"arm":arm,"step_weight":q(STEP_WEIGHT),
                "feature":STEP_FEATURE,"selected_adjacent_signatures_required":arm!="control",
                "shared_held_members_required":arm=="shared_support",
                "arrival_only":True,"complete_nct_classifier":False,"source_labels_used":False,
                "training_performed":False,"production_modified":False}}
    if problem.status != "ready": return result(problem.status,None,False)
    if (len(problem.points)<2 or any(a>=b for a,b in zip(problem.points,problem.points[1:]))
            or problem.total_note_time<=0 or type(problem.max_segments) is not int or problem.max_segments<=0):
        raise ValueError("invalid_frontier_problem")
    edges,aliases = canonical_edges(problem)
    stats.update(original_edges=len(problem.edges),representative_edges=len(edges),equivalence_receipts=aliases)
    original_ev = ev; ev = scoped_functional_evidence(problem,ev)
    indexer = Index(problem,ev.source)
    times = (*problem.points,*(t for e in ev.source.events for t in (e.start,e.end)),*ev.source._measure_times)
    mult = lcm(*range(1,max(6,2*max((len(e.signature[1]) for e in edges),default=0),len(ev.source.events))+1))
    scale = (2*lcm(*(t.denominator for t in times))*problem.total_note_time.numerator
        *(problem.points[-1]-problem.points[0]).numerator
        *lcm(*(v.denominator for v in (*weights.values(),*PAIR_WEIGHTS.values(),ROLE_COST,STEP_WEIGHT)))*mult)
    def units(value):
        value *= scale
        if value.denominator!=1: raise ValueError("score_scale_not_exact")
        return value.numerator
    runs={};pairs={};turns={};outgoing=defaultdict(list);by_id={}
    def run(a,b,sig):
        key=a,b,sig
        if key not in runs:
            values,_=indexer.features(problem.points[a],problem.points[b],sig)
            runs[key]=units(feature_cost(values,weights)+role_cost(sig));stats["run_cost_evaluations"]+=1
        return runs[key]
    def pair(a,b,e,left):
        key=a,b,left,e.signature
        if key not in pairs:
            eligible=(six_four_surface(left) and left[0]==e.signature[0]
                and any(k in ("M","Mm7") for k in shapes(e.signature))) or dominant_pairs(left,e.signature)
            old=component.prior.temporal.resolution_features(ev,problem.points[a],problem.points[b],e.end,left,e.signature)[0] if eligible else {}
            extra=context.assess(problem,problem.points[a],problem.points[b],left,e.signature,arm)[0]
            pairs[key]=units(feature_cost(old,PAIR_WEIGHTS)+STEP_WEIGHT*extra);stats["pair_cost_evaluations"]+=1
        return pairs[key]
    def turn(previous,e):
        key=previous,e.signature,e.attack_spellings
        if key not in turns: turns[key]=units(feature_cost(transition(previous,e),weights))
        return turns[key]
    for e in edges: outgoing[e.start_index].append(e);by_id[e.group_id]=e
    remaining=[problem.max_segments+1]*len(problem.points);remaining[-1]=0
    for i in range(len(problem.points)-2,-1,-1):
        remaining[i]=min((1+remaining[e.end_index] for e in outgoing[i]),default=problem.max_segments+1)
    blockers={e.group_id:units(DEFAULT_WEIGHTS["blocker_exposure"]*e.features.get("blocker_exposure",F())) for e in edges}
    states=[dict() for _ in problem.points];states[0][0,None,None]=(0,())
    def put(end,key,value):
        old=states[end].get(key)
        if old is None or value<old: states[end][key]=value
    for index in range(len(states)-1):
        stats["peak_endpoint_states"]=max(stats["peak_endpoint_states"],len(states[index]))
        feasible={k:v for k,v in states[index].items() if k[0]+remaining[index]<=problem.max_segments}
        current,n=pareto(feasible);stats["pareto_states_removed"]+=n
        stats["states_expanded"]+=len(current);states[index]={}
        groups=defaultdict(list);previous_groups=defaultdict(list)
        for e in outgoing[index]:groups[e.signature,e.attack_spellings].append(e)
        for key,value in current.items():previous_groups[key[2]].append((key,value))
        for (sig,_),group in groups.items():
            prototype=group[0];shortest=min(remaining[e.end_index] for e in group)
            best={};source_counts=defaultdict(int)
            for (count,a,previous),(cost,ids) in current.items():
                if previous==sig:continue
                if count+1+shortest>problem.max_segments:stats["cap_infeasible_operations_skipped"]+=1;continue
                if operations>=transition_budget:return result("transition_budget_abstention",None,False)
                operations+=1;source_counts[count]+=1
                increment=turn(previous,prototype)
                if previous is not None and functional_evidence:increment+=pair(a,index,prototype,previous)
                value=cost+increment,ids
                if count not in best or value<best[count]:best[count]=value
            for e in group:
                for count,(cost,ids) in best.items():
                    if count+1+remaining[e.end_index]>problem.max_segments:stats["cap_infeasible_operations_skipped"]+=1;continue
                    if operations>=transition_budget:return result("transition_budget_abstention",None,False)
                    operations+=1;stats["logical_transitions_represented"]+=source_counts[count]
                    put(e.end_index,(count+1,index,sig),(cost+run(index,e.end_index,sig)+blockers[e.group_id],ids+(e.group_id,)))
                for (count,a,_),(cost,ids) in previous_groups.get(sig,()):
                    if count+1+remaining[e.end_index]>problem.max_segments:stats["cap_infeasible_operations_skipped"]+=1;continue
                    if operations>=transition_budget:return result("transition_budget_abstention",None,False)
                    operations+=1;stats["logical_transitions_represented"]+=1
                    put(e.end_index,(count+1,a,sig),(cost+run(a,e.end_index,sig)-run(a,index,sig)+blockers[e.group_id],ids+(e.group_id,)))
    if not states[-1]:return result("no_complete_path_under_segment_cap",None,True)
    cost,ids=min(states[-1].values())
    # Old reconstruction on this one already-chosen path; no post-hoc choice.
    _,_,direct_run,base_weights,extra_weights=component.decoder(problem,original_ev,context,"control")
    reconstruct=component.prior.temporal.bind(component.prior.temporal.functional.decode,{
        "BASE_WEIGHTS":base_weights,"EVIDENCE_WEIGHTS":extra_weights,"run_features":direct_run,
        "pair_features":component.prior.temporal.resolution_features,"FEATURE_VERSION":FEATURE_VERSION})
    checked=reconstruct(replace(problem,edges=tuple(by_id[i] for i in ids)),original_ev,
        functional_evidence=functional_evidence,transition_budget=max(1,len(ids)))
    selected=checked["selected"]
    direct=score_path(problem,original_ev,ids,arm=arm,functional_evidence=functional_evidence,**kwargs)
    if selected is None or q(direct)!=q(F(cost,scale)):
        raise ValueError("joint_winner_independent_cost_mismatch:"+str((q(direct),q(F(cost,scale)),ids)))
    if tuple(s["semantic_group_ref"] for s in selected["segments"])!=ids:
        raise ValueError("joint_winner_path_changed")
    base_cost=f(selected["score_cost"])
    selected["score_cost"]=q(direct);selected["proposal_id"]="joint_nct_"+arm+"_"+selected["proposal_id"]
    selected["feature_version"]=FEATURE_VERSION
    selected["joint_nct_observations"]=path_observations(problem,original_ev,ids,arm=arm,context=context) if functional_evidence else []
    selected["joint_nct_score_cost"]=q(direct-base_cost)
    stats["winner_checked_with_original_features"]=True
    return result(checked["status"],selected,True)
