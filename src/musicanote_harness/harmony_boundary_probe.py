"""Offline, bounded-context continue/change comparisons. No automatic promotion."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
from .formal_ir import q
from .harmony_joint import prepare, candidates, f

VERSION = 'harmony-boundary-probe-0.1.0'


def probe(ir, start, boundary, end, beat=Fraction(1)):
    start,boundary,end,beat=map(Fraction,(start,boundary,end,beat))
    if not start < boundary < end or beat <= 0:
        raise ValueError('positive_context_and_interior_boundary_required')
    rows,_=prepare(ir)
    # Rebuild neighbors only from the declared observation window. No hidden future labels.
    selected={r['id'] for r in rows if r['start']<end and r['end']>start}
    subset={**ir,'sounding_events':[s for s in ir['sounding_events'] if s['sounding_event_id'] in selected]}
    rows,neighbors=prepare(subset)
    before=candidates(rows,neighbors,start,boundary,beat)
    after=candidates(rows,neighbors,boundary,end,beat)
    continued=candidates(rows,neighbors,start,end,beat)
    left_weight=float((boundary-start)/beat);right_weight=float((end-boundary)/beat)
    alternatives=[]
    for c in continued:
        alternatives.append({'interpretation':'continue','labels':[c['label']],
                             'cost':(left_weight+right_weight)*c['cost'],
                             'hypotheses':[c]})
    for a in before:
        for b in after:
            if a['label']==b['label']:
                continue
            alternatives.append({'interpretation':'change','labels':[a['label'],b['label']],
                                 'cost':left_weight*a['cost']+right_weight*b['cost']+.15,
                                 'hypotheses':[a,b]})
    alternatives.sort(key=lambda x:(x['cost'],x['interpretation'],x['labels']))
    attacked=[r for r in rows if r['start']==boundary]
    carried=[r for r in rows if r['start']<boundary<r['end']]
    released=[r for r in rows if r['end']==boundary]
    def refs(rs):
        return [{'sounding_event_id':r['id'],'pitch':r['pitch'],
                 'onset':q(r['start']),'release':q(r['end'])} for r in rs]
    best_keep=next((x for x in alternatives if x['interpretation']=='continue'),None)
    best_change=next((x for x in alternatives if x['interpretation']=='change'),None)
    # Keep both interpretations even when one ranks below the display shortlist.
    return {'version':VERSION,'context_span':{'start':q(start),'end':q(end)},
            'boundary':q(boundary),'beat_unit':q(beat),'attacked':refs(attacked),
            'carried':refs(carried),'released':refs(released),
            'before_candidates':before,'after_candidates':after,
            'best_continue':best_keep,'best_change':best_change,'ranked_alternatives':alternatives[:6],
            'status':'review_required','automatically_selected':None,'calibrated':False,
            'limitations':['Existing heuristic scorer including known seventh-absorption bias',
                           'No automatic boundary or NCT confirmation',
                           'Single supplied beat unit; mixed-meter context requires separate probes',
                           'Five chord candidates per window; alternatives are not exhaustive',
                           'Pedal/performed timing not inferred; releases are notated sounding releases']}


def run(ir_path, output, max_boundaries=16):
    ir=json.loads(Path(ir_path).read_text(encoding='utf-8'))
    rows,_=prepare(ir)
    measures=sorted({(f(m['global_start_quarter']),f(m['global_start_quarter'])+f(m['actual_duration_quarter']),
                     m['time_signature']['beats'],m['time_signature']['beat_type']) for m in ir['measures']})
    results=[];skipped=[]
    times=sorted({r['start'] for r in rows}|{r['end'] for r in rows})
    for t in times:
        index=next((i for i,(a,b,_,_) in enumerate(measures) if a<=t<b),None)
        if index is None:continue
        window=measures[max(0,index-1):index+2]
        if len({(m[2],m[3]) for m in window})!=1:
            skipped.append({'boundary':q(t),'reason':'mixed_meter'});continue
        left,right=window[0][0],window[-1][1]
        if not left<t<right:continue
        beat=Fraction(4,window[0][3])
        if window[0][2] in (6,9,12):beat*=3
        result=probe(ir,left,t,right,beat)
        result['beat_policy']='conventional_notated_group_not_perceived_pulse'
        results.append(result)
        if len(results)>=max_boundaries:break
    report={'version':VERSION,'ir_document_id':ir['ir_document_id'], 'ir_path':str(Path(ir_path).resolve()),
            'input_policy':'IR_only; no_annotation_or_phrase_input','probes':results,
            'skipped':skipped,'production_enabled':False}
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'probes':len(results),'skipped':len(skipped),'output':str(dest)}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ir',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();print(json.dumps(run(args.ir,args.output),ensure_ascii=False))
