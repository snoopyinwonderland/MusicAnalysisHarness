"""NCT discount ablation. Conservative rejection is not a true NCT classifier."""
import json
from pathlib import Path
from fractions import Fraction
from .harmony_joint import prepare, candidates, nct


def rejection_reasons(rows, r, hypothesis, start, end, neighbors):
    if hypothesis is None:return []
    reasons=[];p,nxt=neighbors.get(r['id'],(None,None))
    if hypothesis['type']=='suspension_like':
        reasons.append('preparation_harmony_unverified')
    if p is None or nxt is None:return reasons+['missing_neighbors']
    if p['end']!=r['start'] or r['end']!=nxt['start']:
        reasons.append('not_contiguous')
    if p['start']<start or nxt['end']>end:
        reasons.append('outside_candidate_span')
    if any(x['voice']==r['voice'] and x['id'] not in (p['id'],r['id'],nxt['id'])
           and x['start']<nxt['end'] and x['end']>p['start'] for x in rows):
        reasons.append('overlapping_voice_event')
    return reasons


def audit(ir,start,end,beat=Fraction(1)):
    start,end,beat=map(Fraction,(start,end,beat))
    if not start<end or beat<=0:raise ValueError('positive_window_required')
    rows,neighbors=prepare(ir)
    def strict(r,pcs,a,b,unit_neighbors,unit):
        h=nct(r,pcs,a,b,unit_neighbors,unit)
        return None if rejection_reasons(rows,r,h,a,b,unit_neighbors) else h
    modes={}
    for name,fn in [('legacy',None),('no_discount',lambda *args:None),('conservative',strict)]:
        modes[name]=candidates(rows,neighbors,start,end,beat,limit=None,nct_evaluator=fn)
    rejected=[];lookup={r['id']:r for r in rows}
    for c in modes['legacy']:
        for h in c['nct']:
            r=lookup[h['sounding_event_id']]
            reasons=rejection_reasons(rows,r,h,start,end,neighbors)
            rejected.append({'candidate':c['label'],'hypothesis':h,'reasons':reasons,
                             'accepted_by_conservative':not reasons,'confirmed_nct':False})
    observed={r['pitch']%12 for r in rows if r['start']<end and r['end']>start}
    ambiguity={name:{'tied_best':[{'label':c['label'],
                    'missing_pitch_classes':sorted(set(c['pcs'])-observed)}
                    for c in choices if abs(c['cost']-choices[0]['cost'])<1e-10],
                    'tie_break':'label_sort_not_musical_evidence'} for name,choices in modes.items()}
    return {'span':[str(start),str(end)],'beat':str(beat),'modes':modes,'discount_checks':rejected,
            'ambiguity':ambiguity,
            'production_enabled':False,'policy':'same candidates and weights; only NCT discount eligibility changes',
            'limits':['No spelling/metric/harmonic preparation classifier',
                      'Valid cross-boundary NCT may be rejected',
                      'Raw XML voice identity is not verified melodic voice']}


def main():
    out=Path('output/harmony-nct-audit-2026-09-26');out.mkdir(parents=True,exist_ok=True)
    summary=[]
    for collection,piece,windows in [('mozart-sonatas','K281-1',[(0,1),(1,2),('9/2',7),(6,'13/2'),('13/2',7)]),
                                    ('beethoven-sonatas','03-2',[(2,3),(4,'19/4')])]:
        path=Path('output/dcml-batch-2026-09-24/pairs')/collection/piece/'canonical_music_ir.json'
        ir=json.loads(path.read_text(encoding='utf-8'))
        results=[audit(ir,a,b) for a,b in windows]
        (out/(piece+'.json')).write_text(json.dumps({'source':str(path),'split':'train',
            'selection':'known error windows, not held-out evaluation','results':results},indent=2),encoding='utf-8')
        for r in results:
            summary.append({'piece':piece,'span':r['span'],
                'top':{k:[{'label':c['label'],'cost':round(c['cost'],6),'discounts':len(c['nct'])} for c in v[:3]] for k,v in r['modes'].items()},
                'ambiguity':r['ambiguity'],
                'rejected_hypotheses':sum(bool(h['reasons']) for h in r['discount_checks'])})
    (out/'report.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
