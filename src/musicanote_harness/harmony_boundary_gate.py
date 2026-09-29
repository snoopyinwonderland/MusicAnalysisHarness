"""Conservative short-change discount experiment, not a textbook-derived constant."""
from fractions import Fraction
import json
from pathlib import Path
from .formal_ir import q
from .harmony_joint import analyze_joint
from .harmony_temporal_shadow import provider, analyze as temporal
from .harmony_context_shadow import crop


def gate(rows,start,end,beat,previous,current):
    result={'charge':.15,'eligible':False,'evidence_refs':[],
            'policy':'short-change-gate-0.1.0'}
    if (previous is None or previous['root'] is None or current['root'] is None
        or previous['label']==current['label'] or not beat/4<=end-start<=beat):return result
    pcs=set(current['pcs']);novel=pcs-set(previous['pcs'])
    attacks=[r for r in rows if r['start']==start and r['end']>=start+beat/4
             and r['pitch']%12 in novel]
    if len({r['pitch']%12 for r in attacks})<2 or len({r['voice'] for r in attacks if r['voice']})<2:
        return result
    active=[r for r in rows if r['start']<end and r['end']>start]
    points=sorted({start,end,*[max(start,r['start']) for r in active],
                   *[min(end,r['end']) for r in active]})
    supported=Fraction(0);refs=set()
    for a,b in zip(points,points[1:]):
        notes=[r for r in active if r['start']<=a<r['end']]
        if {r['pitch']%12 for r in notes}==pcs:
            supported+=b-a;refs.update(r['id'] for r in notes)
    result['complete_support_duration']=q(supported)
    if supported>=beat/4 and supported/(end-start)>=Fraction(1,2):
        result.update(charge=.075,eligible=True,evidence_refs=sorted(refs),
                      new_attack_refs=sorted(r['id'] for r in attacks))
    return result


def analyze(ir):
    cache={}
    def cached(rows,a,b,beat,previous,current):
        key=(a,b,beat,previous['label'] if previous else None,current['label'])
        if key not in cache:cache[key]=gate(rows,a,b,beat,previous,current)
        return cache[key]
    r=analyze_joint(ir,candidate_provider=provider(cell_divisions=2),segment_policy=cached)
    r.update(engine_version='short-change-gate-shadow-0.1.0',production_enabled=False,
             policy_limits=['Uncalibrated fixed thresholds', 'Complete vertical support only',
                            'Requires two new pitch classes in two known voices',
                            'Arpeggiated, one-tone, held-bass changes may be missed'])
    return r


def main():
    out=Path('output/harmony-boundary-gate-2026-09-26');out.mkdir(parents=True,exist_ok=True)
    summary=[]
    for collection,piece in [('mozart-sonatas','K281-1'),('beethoven-sonatas','03-2')]:
        source=Path('output/dcml-batch-2026-09-24/pairs')/collection/piece/'canonical_music_ir.json'
        ir=crop(json.loads(source.read_text(encoding='utf-8')),Fraction(8))
        base=temporal(ir,cell_divisions=2);experiment=analyze(ir)
        (out/(piece+'.json')).write_text(json.dumps({'source':str(source),'split':'train',
            'baseline':base,'experimental':experiment,'accuracy_measured':False},indent=2),encoding='utf-8')
        def compact(r):return [{'span':s['span'],'label':s['selected']['label'],
                               'discount':s.get('segment_policy',{}).get('eligible',False)} for s in r['segments']]
        summary.append({'piece':piece,'baseline':compact(base),'experiment':compact(experiment)})
    (out/'report.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
