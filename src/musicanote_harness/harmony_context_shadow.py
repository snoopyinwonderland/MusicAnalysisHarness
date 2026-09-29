"""Offline A/B integration of melodic geometry into automatic chord/span search."""
import json
from pathlib import Path
from fractions import Fraction
from time import perf_counter
from .harmony_joint import candidates, analyze_joint, f
from .counterpoint_evidence import extract
from .formal_ir import q

VERSION='geometry-context-shadow-0.1.0'


def provider(ir):
    geometry=extract(ir)
    by_middle={r['event_refs'][1]:r for r in geometry['records']}

    def choose(rows, neighbors, start, end, beat, limit=5):
        active=[r for r in rows if r['start']<end and r['end']>start]
        if not active:return candidates(rows,neighbors,start,end,beat)
        lookup={r['id']:r for r in rows}
        weights={r['id']:float(min(end,r['end'])-max(start,r['start'])) for r in active}
        total=sum(weights.values())
        bass=min(r['pitch'] for r in active if r['start']<=max(start,min(x['start'] for x in active))<r['end'])%12
        result=[]
        for c in candidates(rows,neighbors,start,end,beat,limit=None):
            if c['root'] is None:
                result.append(c);continue
            pcs=set(c['pcs']);unexplained=0;support={pc:0 for pc in pcs};evidence=[]
            for r in active:
                record=by_middle.get(r['id']);eligible=False
                if record:
                    first,last=(lookup[x] for x in (record['event_refs'][0],record['event_refs'][2]))
                    eligible=(first['start']>=start and last['end']<=end
                              and first['pitch']%12 in pcs and last['pitch']%12 in pcs
                              and r['end']-r['start']<=beat/2)
                member=r['pitch']%12 in pcs
                # Same geometry examined whether or not middle pitch fits the template.
                if eligible:
                    evidence.append({'event_refs':record['event_refs'],'pattern':record['pattern'],
                                     'member_under_candidate':member,'nct_confirmed':False})
                if member:
                    support[r['pitch']%12]=max(support[r['pitch']%12],.2 if eligible else 1)
                else:
                    unexplained+=weights[r['id']]*(.2 if eligible else 1)
            coverage=sum(support.values())/len(pcs)
            loss=.7*unexplained/total+.3*(1-coverage)+.04*(bass!=c['root'])
            result.append({**c,'baseline_local_cost':c['cost'],'cost':loss,'nct':[],
                           'coverage':coverage,'unexplained_weight_ratio':unexplained/total,
                           'context_evidence':evidence,'support_by_pc':support})
        return sorted(result,key=lambda c:(c['cost'],c['label']))[:limit]
    return choose,geometry


def analyze(ir):
    choose,geometry=provider(ir)
    result=analyze_joint(ir,candidate_provider=choose)
    result.update(engine_version=VERSION,production_enabled=False,
                  geometry_count=len(geometry['records']),
                  limitations=['Experimental fixed weights, not probabilities',
                               'No local-key inference or Unit 7-9 conditional role integration yet',
                               'Only contiguous monophonic short interior geometry supported',
                               'No suspension discount in this shadow scorer',
                               'Phrase and source annotations never inputs'])
    return result


def crop(ir,end):
    return {**ir,'sounding_events':[{**s,'span':{**s['span'],'end':q(min(f(s['span']['end']),end))}}
                                   for s in ir['sounding_events'] if f(s['span']['start'])<end],
            'measures':[{**m,'actual_duration_quarter':q(min(f(m['actual_duration_quarter']),end-f(m['global_start_quarter'])))}
                        for m in ir['measures'] if f(m['global_start_quarter'])<end]}


def main():
    dest=Path('output/harmony-context-shadow-2026-09-26');dest.mkdir(parents=True,exist_ok=True)
    reports=[]
    for collection,piece in [('mozart-sonatas','K281-1'),('beethoven-sonatas','03-2')]:
        source=Path('output/dcml-batch-2026-09-24/pairs')/collection/piece/'canonical_music_ir.json'
        ir=crop(json.loads(source.read_text(encoding='utf-8')),Fraction(8))
        t=perf_counter();baseline=analyze_joint(ir);experimental=analyze(ir)
        report={'source':str(source.resolve()),'range_quarters':[0,8],
                'baseline':baseline,'experimental':experimental,
                'seconds':round(perf_counter()-t,3),'accuracy_measured':False,'production_enabled':False}
        (dest/(collection+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        reports.append({'piece':piece,'seconds':report['seconds'],
                        'baseline_labels':[s['selected']['label'] for s in baseline['segments']],
                        'experimental_labels':[s['selected']['label'] for s in experimental['segments']],
                        'geometry_count':experimental['geometry_count']})
    (dest/'report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(reports,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
