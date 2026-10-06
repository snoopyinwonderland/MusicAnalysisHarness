"""Four independent run costs; preserve the sealed 35-term search contract."""
from fractions import Fraction as F
from types import MethodType

from . import harmony_exact_beat_cache as parent
from . import harmony_context_joint_decoder as joint
from . import harmony_full_score as old
from . import harmony_partial_support as evidence
from .harmony_source_context_scoring import Delegate
from .harmony_joint_nct_scoring import completed_runs
from .harmony_temporal_scoring import bind

VERSION='harmony-partial-support-joint-score-0.1.0'
FEATURES=evidence.FEATURES
ZERO=dict.fromkeys(FEATURES,F())
q,f=evidence.q,joint.f


def coefficients(values):
    result=dict(values)
    if set(result)!=set(FEATURES): raise ValueError('invalid_partial_support_weight_keys')
    if any(type(v) is not F or not (0<=v<=2 if k==FEATURES[0] else -2<=v<=0)
           for k,v in result.items()): raise ValueError('invalid_partial_support_exact_weights')
    return result


class CostView(Delegate):
    def __init__(self,weights): super().__init__(old);self.weights=weights
    def feature_cost(self,values,weights):
        base=old.feature_cost({k:v for k,v in values.items() if k not in FEATURES},weights)
        return base+sum((self.weights[k]*values[k] for k in FEATURES if values.get(k) is not None),F())


class SourceView(Delegate):
    def __init__(self,scorer): super().__init__(scorer.original.source_scorer);self.sc=scorer
    def base_run(self,problem,source,a,b,sig):
        base,details=self.wrapped.base_run(problem,source,a,b,sig)
        return base|self.sc.observe(a,b,sig)[0],details


class Scorer(parent.Scorer):
    def __init__(self,graph,ev,weights,extra=ZERO,**args):
        super().__init__(graph,ev,weights,**args)
        self.partial_args=dict(args)
        self.extra_weights=coefficients(extra);self.extra_cache={}
        self.partial=evidence.Context(graph,ev,history_gate=args.get('history_gate'))
        source=SourceView(self);proxy=Delegate(self.original)
        proxy.source_scorer=source;self.original=proxy
        self._partial_delayed=MethodType(bind(joint.Scorer._delayed,
            {'old_score':CostView(self.extra_weights),'resolution_features':self.beat_cache.resolution}),self)

    def observe(self,a,b,sig):
        key=a,b,sig
        if key not in self.extra_cache: self.extra_cache[key]=self.partial.observe(a,b,sig)
        return self.extra_cache[key]

    def _delayed(self,budget): return self._partial_delayed(budget)

    def path_receipt(self,ids,*,target=False):
        receipt=super().path_receipt(ids,target=target)
        observations=[self.observe(a,b,sig) for a,b,sig in completed_runs(self.problem,ids)]
        known={k:sum((v[k] for v,r in observations if v[k] is not None),F()) for k in FEATURES}
        available={k:all(v[k] is not None for v,r in observations) for k in FEATURES}
        terms={k:known[k]*self.extra_weights[k] for k in FEATURES};added=sum(terms.values(),F())
        return receipt|dict(partial_support_version=VERSION,previous35_cost=receipt['cost'],
            partial_support_cost=q(added),cost=q(f(receipt['cost'])+added),
            partial_support=dict(features={k:q(known[k]) if available[k] else None for k in FEATURES},
                scored_available_feature_sums={k:q(v) for k,v in known.items()},availability=available,
                coefficients={k:q(v) for k,v in self.extra_weights.items()},
                term_costs={k:q(v) for k,v in terms.items()},observations=[r for v,r in observations]),
            candidate_graph_changed=False,source_labels_used=False,production_modified=False)

    def decode(self,**kwargs):
        if any(self.extra_weights.values()): kwargs['force_delayed']=True
        result=super().decode(**kwargs)
        result['partial_support_contract']=dict(version=VERSION,same_sealed_dp_bytecode=True,
            old35_weights_unchanged=True,new_run_costs_only=True,completed_union_runs=True,
            same_candidates_and_raw_cap=True,source_labels_used=False,production_modified=False)
        if result['selected']: result['selected']['proposal_id']='partial_support_'+result['selected']['proposal_id']
        return result
