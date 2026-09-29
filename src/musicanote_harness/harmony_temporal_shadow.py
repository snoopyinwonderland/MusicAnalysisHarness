"""Experimental within-span local-fit regret; no annotation/phrase inputs."""
from fractions import Fraction
import json
from pathlib import Path
from .harmony_joint import analyze_joint, candidates, f, prepare
from .formal_ir import q
from .harmony_surface import TEMPLATES
from .harmony_context_shadow import crop

VERSION = 'temporal-support-shadow-0.3.0'


def provider(complete_local_scoring=True, cell_divisions=1, measures=None):
    if type(cell_divisions) is not int or cell_divisions not in (1,2):
        raise ValueError('cell_divisions_must_be_1_or_2')
    # Cache is scoped to one IR/run. Cells are score-aligned, not fitted to labels.
    cache = {}
    grids = sorted({(f(m['global_start_quarter']), Fraction(4, m['time_signature']['beat_type']))
                    for m in (measures or [])})

    def choose(rows, neighbors, start, end, beat, limit=5):
        choices=candidates(rows,neighbors,start,end,beat,limit=None)
        cells=[]; x=start
        while x<end:
            origin, local_beat = next(((a,u) for a,u in reversed(grids) if a<=x), (Fraction(0),beat))
            cell=local_beat/cell_divisions
            next_measure=next((a for a,_ in grids if a>x),end)
            y=min(end,next_measure,origin+((x-origin)//cell+1)*cell)
            key=(x,y,local_beat)
            if key not in cache:
                # A globally proposed chord must still be scored when locally unsupported.
                # The >=2 shared-PC filter is for proposing candidates, not evaluating them.
                local=candidates(rows,neighbors,x,y,local_beat,limit=None,
                                 min_shared_pcs=0 if complete_local_scoring else 2)
                observed={r['pitch']%12 for r in rows if r['start']<y and r['end']>x}
                # Sparse/silent windows do not justify forcing a change.
                usable=(len(observed)>=3 and local[0]['root'] is not None
                        and local[0].get('coverage',0)==1)
                cache[key]=(local,usable)
            local,usable=cache[key]
            if usable:cells.append((x,y,{c['label']:c for c in local},local[0]['cost']))
            x=y
        result=[]
        for c in choices:
            penalty=0; evidence=[]
            if c['root'] is not None:
                for x,y,lookup,best in cells:
                    fit=lookup.get(c['label'])
                    # Silence/sparse evidence still abstains. Full scoring covers all templates.
                    if fit is None:continue
                    regret=max(0,fit['cost']-best)
                    penalty+=float((y-x)/(end-start))*regret
                    if regret>0:
                        evidence.append({'start':str(x),'end':str(y),'regret':regret,
                                         'best_cost':best,'candidate_cost':fit['cost']})
            result.append({**c,'pooled_cost':c['cost'],'cost':c['cost']+penalty,
                           'temporal_regret':penalty,'temporal_evidence':evidence})
        return sorted(result,key=lambda c:(c['cost'],c['label']))[:limit]
    return choose


def bass_path(rows, segment):
    """Lowest sounding pitch, conditional template factor; not structural bass.

    NCT/pedal/spelling may invalidate an inversion interpretation. No score changes.
    """
    start,end=f(segment['span']['start']),f(segment['span']['end'])
    active=[r for r in rows if r['start']<end and r['end']>start]
    points=sorted({start,end,*[max(start,r['start']) for r in active],
                   *[min(end,r['end']) for r in active]})
    candidate=segment['selected'];root=candidate['root']
    quality=candidate['label'].partition(':')[2]
    template=dict(TEMPLATES).get(quality,())
    result=[]
    for a,b in zip(points,points[1:]):
        sounding=[r for r in active if r['start']<=a<r['end']]
        low=min((r['pitch'] for r in sounding),default=None)
        refs=[r['id'] for r in sounding if r['pitch']==low]
        distance=(low-root)%12 if low is not None and root is not None else None
        factor=template.index(distance) if distance in template else None
        result.append({'span':{'start':q(a),'end':q(b)},'lowest_midi':low,
                       'event_refs':refs,'inversion_index_under_template':factor,
                       'status':'conditional_pc_only_not_verified_inversion'})
    return result


def analyze(ir, complete_local_scoring=True, cell_divisions=1, analysis_span=None):
    result=analyze_joint(ir,candidate_provider=provider(complete_local_scoring,cell_divisions,
                        ir.get('measures',[]) if analysis_span is not None else None),analysis_span=analysis_span)
    result.update(engine_version=VERSION,production_enabled=False,
                  temporal_policy='denominator-beat subdivision; fixed regret weight 1; sparse cells abstain',
                  cell_divisions=cell_divisions)
    result['cell_grid_policy']='original_measure_origin' if analysis_span is not None else 'legacy_zero_origin'
    rows,_=prepare(ir)
    for segment in result['segments']:
        segment['bass_path_evidence']=bass_path(rows,segment)
    result.setdefault('limitations',[])
    result['complete_local_scoring']=complete_local_scoring
    result['limitations']+=['Experimental local-fit weight uncalibrated',
        'Notated denominator beat, not compound/perceived pulse',
        'May oversegment ornaments; sparse cells abstain',
        'Same original NCT and seventh-absorption biases remain']
    return result


def main():
    out=Path('output/harmony-temporal-resolution-2026-09-26');out.mkdir(parents=True,exist_ok=True)
    summaries=[]
    for collection,piece in [('mozart-sonatas','K281-1'),('beethoven-sonatas','03-2')]:
        path=Path('output/dcml-batch-2026-09-24/pairs')/collection/piece/'canonical_music_ir.json'
        ir=crop(json.loads(path.read_text(encoding='utf-8')),Fraction(8))
        baseline=analyze_joint(ir); previous=analyze(ir); shadow=analyze(ir,cell_divisions=2)
        report={'source':str(path),'range_quarters':[0,8],'baseline':baseline,'whole_beat':previous,'half_beat':shadow,
                'production_enabled':False,'accuracy_measured':False,'split':'train'}
        (out/(collection+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
        def compact(r):return [{'start':str(f(s['span']['start'])),'end':str(f(s['span']['end'])),
                              'label':s['selected']['label']} for s in r['segments']]
        summaries.append({'piece':piece,'baseline':compact(baseline),'whole_beat':compact(previous),'half_beat':compact(shadow)})
    (out/'report.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':main()
