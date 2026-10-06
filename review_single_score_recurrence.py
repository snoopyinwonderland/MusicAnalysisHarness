import argparse,html,json,hashlib
from pathlib import Path
from single_score_melody_review import parse_source,hypotheses,fq
from single_score_recurrence import discover,assess,long_fill_candidates

def run(paths,out):
    out=Path(out)
    if out.exists():raise ValueError('Refusing overwrite')
    out.mkdir(parents=True);sections=[]
    for i,path in enumerate(paths,1):
        data=Path(path).read_bytes();digest,events,warnings=parse_source(data);base=hypotheses(events)
        byid={n['id']:n for n in base['sounding']};notes=[byid[id] for id in base['baseline']]
        repeats=discover(notes);long_candidates=long_fill_candidates(notes,repeats)
        relations=base['relations']+long_candidates;review=assess(relations,repeats)
        for r,state in zip(relations,review):
            if r.get('contradictions'):state['state']='blocked';state['contradictions']=r['contradictions']
        folder=out/str(i);folder.mkdir();(folder/'source.musicxml').write_bytes(data)
        report=dict(source=Path(path).name,sourceHash=digest,events=events,baseline=base,longCandidates=long_candidates,recurrence=repeats,assessment=review,parseWarnings=warnings,
            codeHashes={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ['single_score_melody_review.py','single_score_recurrence.py','review_single_score_recurrence.py']})
        (folder/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        def fmt(ns):return ' → '.join(f"m{n['printedMeasure']} {n['spelling']}({fq(n['duration'])}q)" for n in ns)
        labels={'recurring-material-protect':'반복에서 유지됨 · 제외하지 않도록 보호','variation-review':'변형 차이 검토 · 반주 확정 아님','insufficient-evidence':'근거 부족 · 보류','blocked':'기보 근거 충돌 · 제외 금지'}
        rows=[]
        for relation,state in zip(relations,review):
            a,z=relation['start'],relation['endExclusive']; evidence=(state['retainedEvidence'] or state['variationEvidence'])[:2]
            counterpart=[]
            for e in evidence:
                p=repeats['pairs'][e['pairIndex']];b,y=e['otherRange']
                counterpart.append(fmt(notes[b:y]))
            rows.append('<tr><td>'+html.escape(fmt(notes[max(0,a-1):z+1]))+'</td><td>'+html.escape(fmt(notes[a:z]))+'</td><td>'+html.escape(labels[state['state']])+'</td><td>'+html.escape('\n'.join(counterpart) or '확인된 대응 없음')+'</td></tr>')
        # Show longest windows first; these are not claimed as independent families.
        samples=sorted(repeats['pairs'],key=lambda p:(-len(p['matches']),-min(p['coverage'])))[:8]
        details=''.join('<details><summary>반복 대응 후보 · '+str(len(p['matches']))+'음 대응</summary><p>'+html.escape(fmt(notes[p['left'][0]:p['left'][1]]))+'</p><p>'+html.escape(fmt(notes[p['right'][0]:p['right'][1]]))+'</p></details>' for p in samples)
        counts={s:sum(x['state']==s for x in review) for s in labels}
        sections.append('<section><h2>'+html.escape(Path(path).name)+'</h2><p>'+html.escape(str(dict(status=repeats['status'],comparisons=repeats['comparisons'],overlappingPairCandidates=len(repeats['pairs']),assessment=counts)))+f'</p><a href="{i}/review.json">근거·전체 대응·원본 event JSON</a> · <a href="{i}/source.musicxml">원본 MusicXML</a><table><tr><th>앞뒤 문맥</th><th>기존 채움 후보</th><th>반복 검증 결과</th><th>같은 악보의 대응 문맥</th></tr>'+''.join(rows)+'</table>'+details+'</section>')
        print(json.dumps(dict(source=Path(path).name,status=repeats['status'],comparisons=repeats['comparisons'],pairs=len(repeats['pairs']),longCandidates=len(long_candidates),assessment=counts),ensure_ascii=False))
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>작품 내부 반복 검토</title><style>body{font:16px/1.6 sans-serif;margin:28px}td,th{border:1px solid #ccc;padding:8px;white-space:pre-wrap}table{border-collapse:collapse;width:100%}section{margin:40px 0}details{padding:8px;background:#f6f7f8}</style><h1>작품 내부 반복으로 선율 후보 검토</h1><p>단일 Piano Solo XML만 입력. 상대 Melody판과 Phrase 결과를 사용하지 않습니다. 반복 창은 서로 겹칠 수 있어 독립적인 반복 횟수가 아닙니다. 원본이나 운영 분석은 변경하지 않습니다. 이 페이지는 음열 검토표이며 오선 오버레이가 아닙니다.</p>'+''.join(sections),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('sources',nargs='+');a=p.parse_args();run(a.sources,a.out)
