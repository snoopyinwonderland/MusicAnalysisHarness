"""Fixed-partition cost audit, not a segmentation algorithm or musical gold label."""
from fractions import Fraction
import json
from pathlib import Path
from .harmony_joint import prepare, f
from .harmony_temporal_shadow import provider
from .formal_ir import q


def transition(previous, current):
    change=.04 if previous and previous['label']!=current['label'] else 0
    resolution=0
    if previous and previous['root'] is not None and current['root'] is not None:
        if previous['label'].endswith(':dominant7') and (previous['root']-current['root'])%12==7:
            resolution=-.06
    return change,resolution


def audit_partition(ir, points, beat=Fraction(1), cell_divisions=2, limit=5):
    points=list(map(Fraction,points));beat=Fraction(beat)
    if len(points)<2 or beat<=0 or any(b<=a for a,b in zip(points,points[1:])):
        raise ValueError('increasing_points_and_positive_beat_required')
    rows,neighbors=prepare(ir);choose=provider(cell_divisions=cell_divisions)
    states=[(0,[])]; candidate_lists=[]
    for a,b in zip(points,points[1:]):
        choices=choose(rows,neighbors,a,b,beat,limit=limit)
        candidate_lists.append({'span':{'start':q(a),'end':q(b)},'candidates':choices})
        nxt=[]
        for c in choices:
            best=None
            for cost,path in states:
                previous=path[-1]['candidate'] if path else None
                change,resolution=transition(previous,c)
                duration=float((b-a)/beat)
                parts={'pooled_fit':duration*c['pooled_cost'],
                       'temporal_regret':duration*c['temporal_regret'],
                       'segment_charge':.15,'label_change':change,'resolution_discount':resolution}
                item={'span':{'start':q(a),'end':q(b)},'candidate':c,'cost_parts':parts}
                option=(cost+sum(parts.values()),path+[item])
                if best is None or option[0]<best[0]:best=option
            nxt.append(best)
        states=nxt
    cost,path=min(states,key=lambda x:x[0])
    totals={k:sum(s['cost_parts'][k] for s in path) for k in path[0]['cost_parts']}
    return {'points':[q(x) for x in points],'beat':q(beat),'cell_divisions':cell_divisions,
            'candidate_limit':limit,'path':path,'totals':totals,'total_cost':cost,
            'candidate_lists':candidate_lists,'external_transition_costs_included':False,
            'policy':'supplied diagnostic cuts; no automatic boundary discovery; no source labels input'}


def compare(ir, points, **kwargs):
    keep=audit_partition(ir,[points[0],points[-1]],**kwargs)
    split=audit_partition(ir,points,**kwargs)
    fit=lambda r:r['totals']['pooled_fit']+r['totals']['temporal_regret']
    return {'continue':keep,'split':split,
            'split_minus_continue':split['total_cost']-keep['total_cost'],
            'fit_gain_before_segmentation_charges':fit(keep)-fit(split),
            'production_enabled':False,'calibrated':False}


def main():
    dest=Path('output/harmony-cost-diagnostic-2026-09-26');dest.mkdir(parents=True,exist_ok=True)
    # Previously observed failure windows: diagnostic selections, never inference overrides.
    cases=[('mozart-sonatas','K281-1',['9/2','6','13/2','7']),
           ('beethoven-sonatas','03-2',['3','15/4','4','17/4','19/4','5'])]
    summary=[]
    for collection,piece,points in cases:
        path=Path('output/dcml-batch-2026-09-24/pairs')/collection/piece/'canonical_music_ir.json'
        ir=json.loads(path.read_text(encoding='utf-8'))
        reports={str(limit):compare(ir,points,limit=limit) for limit in (5,None)}
        (dest/(piece+'.json')).write_text(json.dumps({'source':str(path),'split':'train',
            'selection':'known failure diagnostic; not held-out evaluation','reports':reports},indent=2),encoding='utf-8')
        for limit,r in reports.items():
            summary.append({'piece':piece,'candidate_limit':limit,'points':points,
                'continue_labels':[s['candidate']['label'] for s in r['continue']['path']],
                'split_labels':[s['candidate']['label'] for s in r['split']['path']],
                'continue_totals':r['continue']['totals'],'split_totals':r['split']['totals'],
                'difference':r['split_minus_continue'],'fit_gain':r['fit_gain_before_segmentation_charges']})
    (dest/'report.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
