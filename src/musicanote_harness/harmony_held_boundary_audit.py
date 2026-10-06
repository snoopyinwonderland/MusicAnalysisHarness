"""Label-blind coverage audit of attacks occurring under held lane sounds.

The earlier lane-onset sampling is retained. Extra cuts are observations from
all parts, not chord-change labels. Scope and voice assignments stay frozen.
"""
from copy import deepcopy
from .formal_ir import q
from .harmony_joint import f

VERSION='held-boundary-coverage-0.1.0'


def plan(result):
    answer={'version':VERSION,'status':result['status'],'cuts':[],
            'source_labels_used':False,'scope_changed':False,
            'selection':'every observed attack under a complete held lane sound; retain old/new distinction'}
    if result['status']!='ready':return answer
    a,z=f(result['span']['start']),f(result['span']['end'])
    ids={sid for t in result['assignments'][0]['tracks'] for sid in t}
    old={f(b['boundary']) for b in result['boundaries']}
    sounds=result['events']
    for cut in sorted({f(s['span']['start']) for s in sounds if a<f(s['span']['start'])<z}):
        held=[s for s in sounds if s['sounding_event_id'] in ids
              and a<=f(s['span']['start'])<cut<f(s['span']['end'])<=z]
        if not held:continue
        answer['cuts'].append({'boundary':q(cut),'already_tested':cut in old,
            'held_event_refs':sorted(s['sounding_event_id'] for s in held),
            'attack_event_refs':sorted(s['sounding_event_id'] for s in sounds if f(s['span']['start'])==cut)})
    return answer


def invalidate_condition(result,boundary_index,side,reading_index,reason):
    """Counterfactual abstention, never a mutation of real score evidence."""
    out=deepcopy(result)
    out['boundaries'][boundary_index].pop('boundary_figures',None)
    out['boundaries'][boundary_index][side]['readings'][reading_index]['condition']['abstention_reasons'].append(reason)
    return out
