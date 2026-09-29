"""Controlled rendering-invariance benchmark, not corpus harmonic accuracy.

Expected harmonies are authored fixture intentions and never analyzer inputs.
All source events can be reconstructed from retained MusicXML and formal IR.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import html
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from music21 import converter,pitch
from .canonical import CanonicalIRBuilder
from .formal_ir import FormalIRAdapter,q
from .harmony_joint import f
from .harmony_multiscale_shadow import analyze,VERSION as ENGINE_VERSION
from .harmony_candidate_explanation import explain_path

VERSION='arpeggio-paired-benchmark-0.1.0'
TEXTURES=('block','ascending','descending','alberti','held_bass','overlapping','delayed_quality')
FAMILIES={
    'triad':((['C3','E4','G4'],0,'major'),(['G2','B3','D4','F4'],7,'dominant7')),
    'seventh':((['C3','E4','G4','B-4'],0,'dominant7'),(['F2','A-3','C4'],5,'minor')),
}
ARMS={
    'current':{},
    'no_distributed_supplement':{'enable_distributed':False},
    'no_boundary_contrast':{'enable_boundary_contrast':False},
}


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def events_for(names,texture,start):
    """Two-quarter cells. Isolate notation texture while retaining harmony intent."""
    if texture=='block':return [(n,F(start),F(2),'1') for n in names]
    if texture=='delayed_quality':
        return [(names[0],F(start),F(3,2),'1')]+[(n,F(start)+F(3,2),F(1,2),'1') for n in names]
    order=list(range(len(names)))
    if len(order)==3:order=[0,1,2,1]
    if texture=='descending':order=list(reversed(order))
    if texture=='alberti':order=[0,2,1,2] if len(names)==3 else [0,2,1,3]
    result=[]
    if texture=='held_bass':
        result.append((names[0],F(start),F(2),'2'))
        order=[1,2,1,2] if len(names)==3 else [1,2,3,2]
    for i,k in enumerate(order):
        duration=F(2)-F(i,2) if texture=='overlapping' else F(1,2)
        result.append((names[k],F(start)+F(i,2),duration,str(i+1) if texture=='overlapping' else '1'))
    return result


def fixture(family,texture,change,transpose=0,scale=F(1)):
    if family not in FAMILIES or texture not in TEXTURES:raise ValueError('unknown_fixture')
    first,second=FAMILIES[family];second=second if change else first
    events=[];expected=[]
    for start,(names,root,quality) in zip((0,2),(first,second)):
        for n,t,d,v in events_for(names,texture,start):
            p=pitch.Pitch(n).transpose(transpose)
            events.append({'pitch':p.nameWithOctave,'start':q(t*scale),'duration':q(d*scale),'voice':v})
        expected.append({'span':{'start':q(start*scale),'end':q((start+2)*scale)},
                         'root':(root+transpose)%12,'quality':quality})
    if not change:expected=[{**expected[0],'span':{'start':q(0),'end':q(4*scale)}}]
    return {'family':family,'texture':texture,'change':change,'transpose':transpose,'scale':q(scale),
            'duration':q(4*scale),'beat_type':int(4/scale),'events':events,'expected':expected,
            'oracle':'authored_chord_intention_not_unique_interpretation_or_corpus_gold'}


def source_xml(case):
    root=ET.Element('score-partwise',version='4.0')
    pl=ET.SubElement(root,'part-list');sp=ET.SubElement(pl,'score-part',id='P1')
    ET.SubElement(sp,'part-name').text='Controlled texture'
    part=ET.SubElement(root,'part',id='P1');measure=ET.SubElement(part,'measure',number='1')
    attr=ET.SubElement(measure,'attributes');ET.SubElement(attr,'divisions').text='8'
    ts=ET.SubElement(attr,'time');ET.SubElement(ts,'beats').text='4';ET.SubElement(ts,'beat-type').text=str(case['beat_type'])
    clef=ET.SubElement(attr,'clef');ET.SubElement(clef,'sign').text='G';ET.SubElement(clef,'line').text='2'
    cursor=F(0);previous=None
    for i,e in enumerate(sorted(case['events'],key=lambda e:(e['voice'],f(e['start'])))):
        onset,duration=f(e['start']),f(e['duration'])
        chord_member=previous==(e['voice'],onset)
        if not chord_member and cursor!=onset:
            move=ET.SubElement(measure,'backup' if onset<cursor else 'forward')
            ET.SubElement(move,'duration').text=str(int(abs(onset-cursor)*8))
            cursor=onset
        n=ET.SubElement(measure,'note',id=f'fixture_note_{i}')
        if chord_member:ET.SubElement(n,'chord')
        p=pitch.Pitch(e['pitch']);pe=ET.SubElement(n,'pitch');ET.SubElement(pe,'step').text=p.step
        if p.accidental:ET.SubElement(pe,'alter').text=str(int(p.accidental.alter))
        ET.SubElement(pe,'octave').text=str(p.octave)
        ET.SubElement(n,'duration').text=str(int(duration*8));ET.SubElement(n,'voice').text=e['voice']
        types={F(1,4):('16th',False),F(1,2):('eighth',False),F(3,4):('eighth',True),F(1):('quarter',False),F(3,2):('quarter',True),F(2):('half',False),F(4):('whole',False)}
        typ,dot=types[duration];ET.SubElement(n,'type').text=typ
        if dot:ET.SubElement(n,'dot')
        if not chord_member:cursor=onset+duration
        previous=(e['voice'],onset)
    return ET.tostring(root,encoding='unicode',xml_declaration=True)


def check_roundtrip(case,ir):
    expected=Counter((int(pitch.Pitch(e['pitch']).midi),f(e['start']),f(e['duration'])) for e in case['events'])
    observed=Counter((s['pitch']['midi_pitch'],f(s['span']['start']),f(s['span']['end'])-f(s['span']['start'])) for s in ir['sounding_events'])
    if expected!=observed:raise ValueError('fixture_musicxml_ir_roundtrip_failed')


def metrics(expected,result):
    start=f(expected[0]['span']['start']);end=f(expected[-1]['span']['end']);correct=F(0)
    actual=result['segments'];cursor=start
    for s in actual:
        a,b=f(s['span']['start']),f(s['span']['end'])
        if a!=cursor or b<=a:raise ValueError('invalid_output_partition')
        cursor=b
        c=s['selected']
        for e in expected:
            x,y=max(a,f(e['span']['start'])),min(b,f(e['span']['end']))
            if y>x and c['root']==e['root'] and c['label'].partition(':')[2]==e['quality']:correct+=y-x
    if cursor!=end:raise ValueError('incomplete_output_partition')
    eb={f(e['span']['start']) for e in expected[1:]}
    ab={f(s['span']['start']) for s in actual[1:]}
    return {'duration_match':float(correct/(end-start)),
        'missing_boundaries':[q(x) for x in sorted(eb-ab)],
        'extra_boundaries':[q(x) for x in sorted(ab-eb)],
        'exact_intention_match':correct==end-start and ab==eb}


def signature(result,transpose=0,scale=F(1)):
    return [(f(s['span']['start'])/scale,f(s['span']['end'])/scale,
             (s['selected']['root']-transpose)%12 if s['selected']['root'] is not None else None,
             s['selected']['label'].partition(':')[2]) for s in result['segments']]


def build(output):
    if output.exists():raise ValueError('output_exists_choose_new_revision')
    output.mkdir(parents=True)
    contract={'version':VERSION,'engine':ENGINE_VERSION,'textures':TEXTURES,'families':list(FAMILIES),
        'arms':ARMS,'transforms':['base','transpose_plus_2','half_duration_double_denominator'],
        'oracle':'constructed_intention_only','source_labels_used_for_inference':False,
        'production_modified':False,'cohort_accuracy_measured':False,
        'important':'no_distributed_supplement still retains basic pooled chord search',
        'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}}
    write(output/'run-contract.json',contract)
    rows=[];base={};markup=[]
    import verovio
    toolkit=verovio.toolkit();toolkit.setOptions({'inputFrom':'musicxml','pageWidth':1700,'pageHeight':800,'adjustPageHeight':True,'scale':35})
    for family in FAMILIES:
        for texture in TEXTURES:
            for change in (False,True):
                for transform,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
                    cid=f'{family}-{texture}-{"change" if change else "hold"}-{transform}'
                    folder=output/cid;folder.mkdir();case=fixture(family,texture,change,tr,scale)
                    source=folder/'score.musicxml';source.write_text(source_xml(case),encoding='utf-8')
                    score=converter.parse(source)
                    ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(score,source),source)
                    check_roundtrip(case,ir);write(folder/'canonical_music_ir.json',ir);write(folder/'fixture.json',case)
                    runs={arm:analyze(ir,**switches) for arm,switches in ARMS.items()}
                    for result in runs.values():explain_path(result)
                    evaluated={arm:metrics(case['expected'],r) for arm,r in runs.items()}
                    key=(family,texture,change)
                    normalized={arm:signature(r,tr,scale) for arm,r in runs.items()}
                    if transform=='base':base[key]=normalized
                    row={'case_id':cid,'family':family,'texture':texture,'change':change,'transform':transform,
                        'metrics':evaluated,'equivariant_to_base':{arm:sig==base[key][arm] for arm,sig in normalized.items()},
                        'source_sha256':digest(source),'ir_sha256':digest(folder/'canonical_music_ir.json')}
                    write(folder/'results.json',{'summary':row,'runs':runs});rows.append(row)
                    if transform=='base':
                        if not toolkit.loadFile(str(source)):raise ValueError('render_failed')
                        svg=toolkit.renderToSVG(1);(folder/'score.svg').write_text(svg,encoding='utf-8')
                        def show_path(items):return ' → '.join(f"[{f(s['span']['start'])}, {f(s['span']['end'])}) {s.get('selected',{}).get('label',str(s.get('root'))+':'+str(s.get('quality')))}" for s in items)
                        body='<p>작성 의도: '+html.escape(show_path(case['expected']))+'</p>'
                        for arm,r in runs.items():body+='<p>'+html.escape(arm)+': '+html.escape(show_path(r['segments']))+' · '+str(round(100*evaluated[arm]['duration_match'],1))+'% 음고류·종류 시간 일치</p>'
                        markup.append('<details><summary>'+html.escape(cid)+' · '+('의도 일치' if evaluated['current']['exact_intention_match'] else '불일치 / 검토 필요')+'</summary>'+svg+body+f'<p><a href="{cid}/score.musicxml">MusicXML</a> · <a href="{cid}/results.json">계산·근거</a></p></details>')
    summary={arm:{'cases':len(rows),'exact_intention_matches':sum(r['metrics'][arm]['exact_intention_match'] for r in rows),
        'mean_duration_match':sum(r['metrics'][arm]['duration_match'] for r in rows)/len(rows),
        'equivariance_failures':sum(not r['equivariant_to_base'][arm] for r in rows)} for arm in ARMS}
    write(output/'report.json',{'contract':contract,'summary':summary,'cases':rows})
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>분산화음 짝지은 검증</title><style>body{font:16px system-ui;max-width:1150px;margin:30px auto;background:#f5f7fa;color:#182636}details{background:white;padding:16px;margin:12px 0;border:1px solid #ccd5df}summary{cursor:pointer;font-weight:600}svg{width:100%;height:auto}p{line-height:1.6}</style><h1>분산화음 짝지은 검증</h1><p>합성 악보의 작성 의도와 계산 비교입니다. 실제 음악 정답률이 아닙니다. 같은 화음 유지(hold) / 실제 화음 교체(change)를 비교합니다. 숫자는 quarter 좌표이며 구간 끝은 제외합니다.</p><p>current: 현재 규칙 · no_distributed_supplement: 추가 분산 지지만 끔(기본 pooling 유지) · no_boundary_contrast: 병합 억제만 끔. 이조·음가 축소 결과는 <a href="report.json">전체 보고서</a>에 있습니다.</p>'+''.join(markup),encoding='utf-8')
    print(json.dumps(summary),flush=True)
    return summary


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    build(ap.parse_args().output)
