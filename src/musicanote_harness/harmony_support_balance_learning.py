"""Train-only bounded calibration on sealed historical path contrasts.

This is not fresh loss-augmented training or full candidate coverage. Only four
new coefficients move; old boundary/run/function/NCT weights remain fixed.
"""
from collections import Counter
from fractions import Fraction as F

from .harmony_support_balance import FEATURES,ZERO,FEATURE_VERSION,coefficients
from .harmony_candidate_recall import fraction as f,rational as q
from .harmony_structured_learning import validate_use_contract,content_hash,quantize,RESTRICTIONS
from .harmony_scored_decoder import feature_cost

VERSION="harmony-support-balance-learning-0.1.0"


def model_weights(model,contract,manifest,parent_sha):
    validate_use_contract(contract,manifest,parent_sha)
    if (model.get('version')!=VERSION or model.get('feature_version')!=FEATURE_VERSION
            or model.get('use_contract_sha256')!=content_hash(contract)
            or model.get('parent_recall_sha256')!=parent_sha
            or model.get('purpose')!='local_noncommercial_research'
            or model.get('restrictions')!={k:False for k in RESTRICTIONS}
            or model.get('dev_labels_used') is not False or model.get('base_weights_frozen') is not True
            or model.get('production_deployment') is not False):
        raise ValueError('invalid_balance_model_contract')
    return coefficients({k:f(v) for k,v in model['weights'].items()})


def fit(rows,contract,manifest,parent_sha,*,epochs=5,update_cap=F(1,10)):
    approvals=validate_use_contract(contract,manifest,parent_sha)
    if type(epochs) is not int or not 1<=epochs<=20 or type(update_cap) is not F or update_cap<=0:
        raise ValueError("invalid_balance_learning_configuration")
    rows=sorted(rows,key=lambda x:(x["entry"]["work_family_id"],x["sample_id"],x["contrast_id"]))
    seen=set()
    for row in rows:
        entry=row["entry"];key=entry["manifest_entry_id"]
        if entry.get("split")!="train" or key not in approvals:raise ValueError("unapproved_or_nontrain_contrast")
        if approvals[key]["manifest_entry_sha256"]!=content_hash(entry):raise ValueError("contrast_entry_binding_mismatch")
        if row["contrast_id"] in seen:raise ValueError("duplicate_training_contrast")
        seen.add(row["contrast_id"])
        delta={k:f(v) for k,v in row["feature_delta"].items()}
        if set(delta)!=set(FEATURES) or any(row["feature_available"].get(k) is not True for k in FEATURES):
            raise ValueError("unavailable_training_features")
        if f(row["loss"])<=0:raise ValueError("nonpositive_training_contrast_loss")
    if not rows:raise ValueError("no_eligible_training_contrasts")
    weights=dict(ZERO);totals=dict(ZERO);ticks=0;updates=[];history=[]
    for epoch in range(1,epochs+1):
        counts=Counter()
        for row in rows:
            delta={k:f(v) for k,v in row["feature_delta"].items()}
            gap=f(row["base_cost_gap"]);loss=f(row["loss"])
            before=loss-gap-feature_cost(delta,weights);norm=sum((v*v for v in delta.values()),F())
            if before<=0:counts["margin_satisfied"]+=1
            elif norm==0:counts["new_feature_collision"]+=1
            else:
                tau=min(update_cap,before/norm)
                new={k:quantize(max(F(),min(F(1),weights[k]+tau*delta[k]))) for k in FEATURES}
                counts["updated" if new!=weights else "bounded_no_change"]+=1
                after=loss-gap-feature_cost(delta,new)
                if new!=weights:updates.append({"epoch":epoch,"contrast_id":row["contrast_id"],
                    "before":q(before),"after":q(after),"tau":q(tau),"weights":{k:q(v) for k,v in new.items()}})
                weights=new
            ticks+=1
            for k,v in weights.items():totals[k]+=v
        history.append({"epoch":epoch,"statuses":dict(counts),"weights":{k:q(v) for k,v in weights.items()}})
    averaged=coefficients({k:quantize(v/ticks) for k,v in totals.items()})
    def violations(w):
        return [max(F(),f(r["loss"])-f(r["base_cost_gap"])-feature_cost({k:f(v) for k,v in r["feature_delta"].items()},w)) for r in rows]
    before,after=violations(ZERO),violations(averaged)
    return {"version":VERSION,"feature_version":FEATURE_VERSION,"weights":{k:q(v) for k,v in averaged.items()},
        "configuration":{"epochs":epochs,"update_cap":q(update_cap),"coefficient_bounds":[0,1],
            "old_weights_frozen":True,"dev_selection":False,"fresh_adversary_search":False},
        "purpose":"local_noncommercial_research","restrictions":{k:False for k in RESTRICTIONS},
        "use_contract_sha256":content_hash(contract),"parent_recall_sha256":parent_sha,
        "training_contrasts":len(rows),"training_samples":len({r["sample_id"] for r in rows}),
        "training_families":sorted({r["entry"]["work_family_id"] for r in rows}),
        "training_reference_labels_used":True,"dev_labels_used":False,"base_weights_frozen":True,
        "margin_violation_sum_before":q(sum(before,F())),"margin_violation_sum_after":q(sum(after,F())),
        "margin_worse_pairs":sum(a>b for a,b in zip(after,before)),"epochs":history,"updates":updates,
        "source_labels_used_at_inference":False,"production_deployment":False,"confidence_calibrated":False}
