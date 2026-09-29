"""Archive residual role hypotheses for every frozen change proposal."""
import argparse
from collections import Counter
from fractions import Fraction as F
import html
import json
from pathlib import Path
import re
import shutil
from .formal_ir import q
from .harmony_joint import f
from .harmony_residual_audit import audit_pair,VERSION
from .harmony_open_candidates import window
from .harmony_arpeggio_benchmark import write,digest,check_roundtrip
from .harmony_shared_tone_trial import load


def controls(output):
    from music21 import converter,pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    anticipation=[('C3',0,2,'1'),('E3',0,2,'2'),('G3',0,2,'3'),('C4',0,1,'4'),('D4',1,1,'4'),('D4',2,2,'4'),('G2',2,2,'1'),('B3',2,2,'2')]
    accompaniment=[('C3',0,1,'1'),('E3',0,1,'2'),('G3',0,1,'3')]+[(p,t,d,v) for p,v in [('G2','1'),('B2','2'),('D3','3')] for t,d in [(1,1),(2,2)]]
    specs={'anticipation':(anticipation,2,7),
        'suspension':(accompaniment+[('C4',0,2,'4'),('B3',2,2,'4')],1,7),
        'reattack_not_suspension':(accompaniment+[('C4',0,1,'4'),('C4',1,1,'4'),('B3',2,2,'4')],1,7),
        'passing':([(p,0,4,v) for p,v in [('C3','1'),('E3','2'),('G3','3')]]+[('C4',0,F(1,2),'4'),('D4',F(1,2),F(1,2),'4'),('E4',1,1,'4'),('E4',2,2,'4')],2,0)}
    rows=[]
    for kind,(events,boundary,target) in specs.items():
        baseline=None
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            dst=output/(kind+'-'+name);dst.mkdir(parents=True)
            fixture={'scale':q(scale),'beat_type':int(4/scale),'events':[{'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,'start':q(t*scale),'duration':q(d*scale),'voice':v} for p,t,d,v in events]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(fixture),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml);check_roundtrip(fixture,ir)
            left=window(ir,{'start':q(0),'end':q(boundary*scale)});right=window(ir,{'start':q(boundary*scale),'end':q(4*scale)})
            get=lambda w,root:next(c for c in w['candidates'] if c['root']==root and c['label'].endswith(':major'))
            r=audit_pair(ir,left,right,get(left,tr),get(right,(target+tr)%12))
            roles=sorted(e['kind'] for side in r['sides'] for n in side['residuals'] for e in n['conditional_nct_explanations'])
            if kind=='anticipation':assert 'anticipation_reattack_compatible' in roles
            elif kind=='suspension':assert 'prepared_suspension_geometry' in roles
            elif kind=='reattack_not_suspension':assert 'prepared_suspension_geometry' not in roles
            else:assert roles
            if baseline is None:baseline=roles
            else:assert roles==baseline
            write(dst/'canonical_music_ir.json',ir);write(dst/'residual-audit.json',r)
            rows.append({'case':dst.name,'roles':roles,'passed':True,'xml_sha256':digest(xml)})
    return rows


def page(src,dst,records):
    source=(src/'whole-score.html').read_text(encoding='utf-8');payload=[]
    labels={'anticipation_reattack_compatible':'선행음 형태 · 다음 화음에서 같은 음 재타격',
            'prepared_suspension_geometry':'준비된 지속음의 하행 해결 형태 · 강세 미확정',
            'passing':'경과 형태','neighbor':'보조 형태','double_neighbor':'이중 보조 형태'}
    for i,r in enumerate(records):
        rows=[]
        for side in r['sides']:
            rows.append('<h4>'+('앞' if side['side']=='before' else '뒤')+' '+html.escape(side['label'])+' — 미해결 '+str(side['unresolved_count'])+'음</h4>')
            for n in side['residuals']:
                k=len(payload);payload.append({'ids':n['source_note_ids'],'conditional':bool(n['conditional_nct_explanations'])})
                roles=' / '.join(labels.get(e['kind'],e['kind']) for e in n['conditional_nct_explanations']) or '아직 설명되지 않음'
                options=sorted({a['label']+(' (누락 '+str(len(a['missing_member_pcs']))+'PC)' if a['missing_member_pcs'] else '') for a in n['finer_cell_alternatives']})
                rows.append('<p><button data-residual="'+str(k)+'">'+html.escape(n['pitch']['spelling'].replace('-','♭'))+'</button> '+html.escape(roles)+'</p><details><summary>더 작은 구간의 구성음 대안 '+str(len(options))+'개 — 화음 교체 확정 아님</summary><p>'+html.escape(', '.join(options) or '관측 후보 없음')+'</p></details>')
        pattern=r'(<article><button data-proposal="'+str(i)+r'">.*?)(</article>)'
        source,n=re.subn(pattern,lambda m:m[1]+'<details><summary>미설명음별 검토</summary>'+''.join(rows)+'</details>'+m[2],source,count=1,flags=re.S)
        assert n==1
    source=source.replace('화음 교체 관문','미설명음 대조')
    source=source.replace('</header>','<p>아래 미설명음 버튼: 보라=조건부 NCT 설명 있음, 주황=미해결. 어느 경우도 음표 삭제/화음 선택이 아닙니다. <a href="residual-audits.json">음별 대안·원음표·시간 근거</a></p></header>')
    script='const residualPayload='+json.dumps(payload)+';document.querySelectorAll("[data-residual]").forEach(b=>b.onclick=()=>{const p=residualPayload[+b.dataset.residual];let first;document.querySelectorAll(".scorepage .note").forEach(n=>{n.classList.remove("before","after","shared","unexplained");if(p.ids.includes(n.dataset.id||n.id)){n.classList.add(p.conditional?"shared":"unexplained");first=first||n;}});if(first)first.scrollIntoView({block:"center",behavior:"smooth"});});'
    source=source.replace('</style>','.unexplained{fill:#c05600!important;color:#c05600!important}summary{cursor:pointer;padding:8px}</style>')
    # Original proposal clicks must also clear the residual marker.
    source=source.replace('n.classList.remove("before","after","shared")','n.classList.remove("before","after","shared","unexplained")')
    source=source.replace('</body>','') if '</body>' in source else source
    source=source.replace('</html>','<script>'+script+'</script></html>')
    (dst/'whole-score.html').write_text(source,encoding='utf-8')


def build(source,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);prior=load(source/'report.json')
    write(output/'run-contract.json',{'version':VERSION,'source_report_sha256':digest(source/'report.json'),
        'selection':'every prior change proposal, no label/feedback filtering','no_extra_score_context':True,
        'cohort':'same frozen train works, not holdout','code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}})
    report={'version':VERSION,'real':[],'production_modified':False,'prior_selection_changed':False,'accuracy_measured':False}
    for old in prior['real']:
        src=source/'real-cases'/old['case_id'];dst=output/'real-cases'/old['case_id'];dst.mkdir(parents=True)
        prov=load(src/'source-snapshot'/'case-provenance.json')
        if prov['manifest_entry']['split']!='train' or not prov['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible')
        for n,h in old['source_hashes'].items():
            if digest(src/'source-snapshot'/n)!=h:raise ValueError('changed_source')
        shutil.copytree(src/'source-snapshot',dst/'source-snapshot')
        ir=load(src/'source-snapshot'/'candidate_revision_ir.json');path=src/'gate-results.json';before=digest(path)
        prior_records=load(path)['records'];records=[];cache={};counts=Counter();unique=set();unique_roles=set()
        for oldr in prior_records:
            left=oldr['left_window'];right=oldr['right_window']
            for p in oldr['change_proposals']:
                x=next(c for c in left['candidates'] if c['candidate_id']==p['source_candidate_ref']);y=next(c for c in right['candidates'] if c['candidate_id']==p['target_candidate_ref'])
                r=audit_pair(ir,left,right,x,y,cache);r['proposal_ref']=p['proposal_id'];records.append(r)
                for side,c in zip(r['sides'],(x,y)):
                    assert {n['event_ref'] for n in side['residuals']}==set(c['residual_event_refs'])
                    for n in side['residuals']:
                        unique.add(n['event_ref']);counts['residual_occurrences']+=1
                        counts['conditional_explanation_occurrences']+=bool(n['conditional_nct_explanations'])
                        counts['unresolved_occurrences']+=not bool(n['conditional_nct_explanations'])
                        for e in n['conditional_nct_explanations']:unique_roles.add((n['event_ref'],e['kind']))
                assert r['selected'] is None and not r['used_for_ranking']
        assert before==digest(path)
        shutil.copyfile(path,dst/'gate-results.json');write(dst/'residual-audits.json',{'version':VERSION,'records':records})
        page(src,dst,records)
        row={'case_id':old['case_id'],'title':old['title'],'proposals':len(records),**dict(counts),'unique_residual_sounds':len(unique),
             'unique_sound_role_pairs':len(unique_roles),'roles':sorted({r for _,r in unique_roles}),'prior_gate_sha256':before,'source_hashes':old['source_hashes']}
        report['real'].append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    report['controls']=controls(output/'controls');write(output/'report.json',report)
    links=''.join('<li><a href="real-cases/'+r['case_id']+'/whole-score.html">'+html.escape(r['title'])+'</a> — '+str(r['proposals'])+'개 기존 교체 가설</li>' for r in report['real'])
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>남은 미설명음 대조</h1><p>조건부 NCT 설명과 더 작은 구간의 구성음 대안을 구별합니다. 잔여음을 삭제하거나 기존13대안에서 정답 하나를 고른 것은 아닙니다.</p><ul>'+links+'</ul><a href="report.json">검증 보고서</a></html>',encoding='utf-8')
    print('Controls passed: '+str(len(report['controls'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.source,a.output)
