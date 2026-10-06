"""Four source-bound support features, added to an unchanged research score.

Not a structural-tone or NCT classifier. Zero coefficients reproduce step66
control. Missing roles and durable nonmembers stay observations, not chord bans.
"""
from fractions import Fraction as F
from functools import lru_cache

from . import harmony_component_support_scoring as prior
from .harmony_joint_nct_scoring import completed_runs
from .harmony_evidence_scoring import metric
from .harmony_functional_scoring import shapes
from .harmony_scored_decoder import feature_cost
from .seventh_context import chord, QUALITIES
from .harmony_candidate_recall import fraction as f, rational as q

VERSION = "harmony-support-balance-0.1.0"
FEATURE_VERSION = "separate-missing-roles-and-durable-nonmembers-0.1.0"
FEATURES = ("absent_third_exposure", "absent_altered_fifth_exposure",
            "absent_seventh_exposure", "durable_nonmember_exposure")
ZERO = dict.fromkeys(FEATURES, F())


def coefficients(values=None):
    result = dict(ZERO if values is None else values)
    if set(result) != set(FEATURES) or any(type(x) is not F or not 0 <= x <= 1 for x in result.values()):
        raise ValueError("invalid_support_balance_coefficients")
    return result


@lru_cache(maxsize=4096)
def roles(signature):
    qualities = shapes(signature)
    if len(qualities) != 1: return None
    quality = qualities[0]; members = tuple(map(tuple, chord(signature[0],quality)["members"]))
    return members[1], members[2] if QUALITIES[quality][1] != 7 else None, members[3] if len(members)==4 else None


def support_features(problem, source, start, end, signature, *, index=None):
    width = problem.points[-1]-problem.points[0]
    if not problem.points[0] <= start < end <= problem.points[-1]:
        raise ValueError("invalid_support_feature_span")
    details = []
    if index is None:
        active = [e for e in source.events if e.start < end and start < e.end]
        known = {e.pitch for e in active if e.pitch is not None}
        available = bool(known) and all(e.pitch is not None for e in active)
        durable = []; unavailable = False
        for e in active:
            _,unit = metric(source,e.start)
            if unit is None: unavailable = True
            elif e.pitch not in signature[1] and e.end-e.start >= unit:
                durable.append(e)
        durable_value = (sum((min(end,e.end)-max(start,e.start) for e in durable),F())/problem.total_note_time
                         if available and not unavailable else None)
    else:
        i,j=index.positions[start],index.positions[end]
        known={t for t,p in index.presence.items() if p[j]>p[i]}
        available=bool(known) and index.unresolved[j]==index.unresolved[i]
        durable_value=(sum((p[j]-p[i] for t,p in index.durable.items() if t not in signature[1]),F())/problem.total_note_time
                       if available and index.duration_unknown[j]==index.duration_unknown[i] else None)
    selected_roles=roles(signature)
    values={k:(F(int(t is not None and t not in known))*(end-start)/width
               if available and selected_roles is not None else None)
            for k,t in zip(FEATURES[:3],selected_roles or (None,None,None))}
    values[FEATURES[3]]=durable_value
    if index is None:
        details=[{"kind":"separated_member_support", "span":{"start":q(start),"end":q(end)},
            "roles":selected_roles,"observed_spellings":sorted(known),
            "values":{k:None if v is None else q(v) for k,v in values.items()},
            "durable_nonmember_event_ids":sorted(e.event_id for e in durable),
            "source_note_ids":{e.event_id:list(e.source_note_ids) for e in active},
            "confirmed_nct":False,"structural_tone_confirmed":False,"omission_prohibited":False,
            "unobserved_notes_invented":False,"raw_nonmember_cost_removed":False,
            "duration_rule":"full_sounding_duration_at_least_one_meter_unit_at_original_onset",
            "source_labels_used":False}]
    return values,details


class Scorer:
    def __init__(self,problem,ev,values=None,*,build_index=True,**args):
        self.problem,self.ev,self.args=problem,ev,args
        self.weights=coefficients(values)
        self.context=prior.ComponentContext(ev,**args)
        _,Parent,base_run,base_weights,extra_weights=prior.decoder(problem,ev,self.context,"control")
        self.base_run=base_run
        def run(p,source,a,b,sig):
            original,patterns=base_run(p,source,a,b,sig)
            extra,details=support_features(p,source,a,b,sig)
            return original|extra,patterns+details
        class SupportIndex(Parent):
            def __init__(self,p,source):
                super().__init__(p,source)
                self.durable={};self.duration_unknown=[F()]
                durables={};unknown=[]
                for e in source.events:
                    _,unit=metric(source,e.start)
                    if unit is None:unknown.append(e)
                    elif e.pitch is not None and e.end-e.start>=unit:
                        durables.setdefault(e.pitch,[]).append(e)
                for token,events in durables.items():
                    prefix=[F()]
                    for a,b in zip(self.points,self.points[1:]):
                        prefix.append(prefix[-1]+sum((max(F(),min(b,e.end)-max(a,e.start)) for e in events),F()))
                    self.durable[token]=prefix
                for a,b in zip(self.points,self.points[1:]):
                    self.duration_unknown.append(self.duration_unknown[-1]+sum((max(F(),min(b,e.end)-max(a,e.start)) for e in unknown),F()))
            def features(self,a,b,sig):
                original,patterns=super().features(a,b,sig)
                extra,_=support_features(self.problem,self.source,a,b,sig,index=self)
                return original|extra,patterns
        temporal=prior.prior.temporal
        extra_weights=extra_weights|self.weights
        reconstruct=temporal.bind(temporal.functional.decode,{
            "BASE_WEIGHTS":base_weights,"EVIDENCE_WEIGHTS":extra_weights,"run_features":run,
            "pair_features":temporal.resolution_features,"FEATURE_VERSION":FEATURE_VERSION})
        self.chosen=temporal.bind(temporal.frontier.decode,{
            "BASE_WEIGHTS":base_weights,"EVIDENCE_WEIGHTS":extra_weights,"RunIndex":SupportIndex,
            "pair_features":temporal.resolution_features,"original_decode":reconstruct})
        self.index=SupportIndex(problem,ev.source) if build_index else None

    def path_features(self,ids,*,indexed=False):
        if not ids or len(ids)>self.problem.max_segments:raise ValueError("invalid_support_balance_path")
        if indexed and self.index is None:raise ValueError('support_index_not_built')
        values=dict(ZERO);availability=dict.fromkeys(FEATURES,True)
        for a,b,sig in completed_runs(self.problem,ids):
            extra,_=support_features(self.problem,self.ev.source,a,b,sig,index=self.index if indexed else None)
            for k,v in extra.items():
                if v is None:availability[k]=False
                else:values[k]+=v
        return values,availability

    def base_cost(self,ids):
        return prior.score_path(self.problem,self.ev,ids,arm="control",**self.args)

    def score_path(self,ids):
        return self.base_cost(ids)+feature_cost(self.path_features(ids)[0],self.weights)

    def decode(self,*,transition_budget=2_000_000):
        result=self.chosen(self.problem,self.ev,transition_budget=transition_budget)
        if result["selected"] is not None:
            s=result["selected"];ids=tuple(x["semantic_group_ref"] for x in s["segments"])
            direct=self.score_path(ids)
            if q(direct)!=s["score_cost"]:raise ValueError("support_balance_winner_cost_mismatch")
            values,availability=self.path_features(ids)
            s["proposal_id"]="support_balance_"+s["proposal_id"]
            s["feature_version"]=FEATURE_VERSION
            s["support_balance"]={"values":{k:q(v) for k,v in values.items()},"availability":availability,
                "coefficients":{k:q(v) for k,v in self.weights.items()},
                "additional_cost":q(feature_cost(values,self.weights)),"confirmed_nct":False}
        result["support_balance_contract"]={"version":VERSION,"source_labels_used":False,
            "base_weights_frozen":True,"new_coefficients_only":True,"omission_prohibited":False,
            "raw_nonmember_cost_removed":False,"complete_nct_classifier":False,"production_modified":False}
        return result
