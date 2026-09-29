"""Bounded context evidence for tied candidates; never resolves a tie by name."""
from fractions import Fraction
import json
from pathlib import Path
from .formal_ir import q
from .harmony_joint import prepare, candidates


def inspect(ir,start,end,context=1,beat=1):
    start,end,context,beat=map(Fraction,(start,end,context,beat))
    if start>=end or context<=0 or beat<=0:raise ValueError('positive_window_and_context_required')
    rows,_=prepare(ir)
    left=max(Fraction(0),start-context);right=end+context
    bounded=[r for r in rows if r['start']<right and r['end']>left]
    # Rebuild neighborhood in the declared context; outside notes cannot set local cost.
    ids={r['id'] for r in bounded}
    subset={**ir,'sounding_events':[s for s in ir['sounding_events'] if s['sounding_event_id'] in ids]}
    rows,neighbors=prepare(subset)
    ranked=candidates(rows,neighbors,start,end,beat,limit=None)
    tied=[c for c in ranked if abs(c['cost']-ranked[0]['cost'])<1e-10]
    sets=[set(c['pcs']) for c in tied]
    discriminating=set.union(*sets)-set.intersection(*sets) if len(sets)>1 else set()
    observations=[]
    for r in rows:
        if r['pitch']%12 not in discriminating:continue
        region='before' if r['end']<=start else ('after' if r['start']>=end else 'inside')
        observations.append({'event_id':r['id'],'pitch':r['pitch'],'spelling':r['spelling'],
             'voice_id':r['voice'],'region':region,
             'observed_span':{'start':q(max(left,r['start'])),'end':q(min(right,r['end']))},
             'compatible_candidates':[c['label'] for c in tied if r['pitch']%12 in c['pcs']]})
    # Monophonic, contiguous, boundary-crossing voice links only. No voice reassignment.
    links=[]
    for r in rows:
        if not r['voice']:continue
        for boundary in (start,end):
            if r['end']!=boundary:continue
            following=[s for s in rows if s['voice']==r['voice'] and s['start']==boundary]
            if len(following)!=1:continue
            s=following[0]
            if any(t['voice']==r['voice'] and t['id'] not in (r['id'],s['id'])
                   and t['start']<s['end'] and t['end']>r['start'] for t in rows):continue
            links.append({'boundary':q(boundary),'event_refs':[r['id'],s['id']],
                          'voice_id':r['voice'],'semitone_motion':s['pitch']-r['pitch'],
                          'resolution_confirmed':False})
    return {'version':'harmony-ambiguity-context-0.1.0','target_span':{'start':q(start),'end':q(end)},
            'context_span':{'start':q(left),'end':q(right)},'score_id':ir.get('score',{}).get('score_id'),
            'ir_document_id':ir.get('ir_document_id'),'hypotheses':tied,
            'status':'ambiguous' if len(tied)>1 else ('insufficient_evidence' if tied[0]['root'] is None else 'single_local_candidate'),
            'selected_hypothesis':None,'display_order_is_evidence':False,
            'discriminating_pitch_classes':sorted(discriminating),'context_observations':observations,
            'boundary_voice_links':links,'production_enabled':False,
            'limits':['Surrounding pitches may belong to a different harmony',
                      'Pitch-class compatibility does not prove spelling/function',
                      'No contextual reranking or calibrated confidence',
                      'Observed voice continuity is not validated musical voice identity']}


def main():
    out=Path('output/harmony-ambiguity-context-2026-09-26');out.mkdir(parents=True,exist_ok=True)
    source=Path('output/dcml-batch-2026-09-24/pairs/mozart-sonatas/K281-1/canonical_music_ir.json')
    ir=json.loads(source.read_text(encoding='utf-8'))
    reports=[inspect(ir,a,b) for a,b in [(0,1),(6,'13/2'),('13/2',7)]]
    (out/'K281-1.json').write_text(json.dumps({'source':str(source),'split':'train',
        'selection':'previously identified ambiguous windows','records':reports},indent=2),encoding='utf-8')
    print(json.dumps([{'span':r['target_span'],'status':r['status'],
        'labels':[c['label'] for c in r['hypotheses']],
        'context_notes':len(r['context_observations']),'voice_links':len(r['boundary_voice_links'])} for r in reports],indent=2))


if __name__=='__main__':main()
