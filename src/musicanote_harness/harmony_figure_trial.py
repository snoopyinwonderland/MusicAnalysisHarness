"""Predefined synthetic counterexamples and frozen real-case figure-cost trial."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
import shutil
from xml.etree import ElementTree as ET
from music21 import converter,pitch
from .canonical import CanonicalIRBuilder
from .formal_ir import FormalIRAdapter,q
from .harmony_arpeggio_benchmark import source_xml,check_roundtrip,metrics,signature,digest,write
from .harmony_figure_shadow import analyze,VERSION
from .harmony_joint import f
from .harmony_context_sensitivity import context_stable

KINDS=('same_chord','different_chords_between_cells','change_inside_cell_shared_seventh_union','change_inside_cell_disjoint')
ARMS={'off':{'weight':0},'low':{'weight':.04},'on':{'weight':.08},'high':{'weight':.12},'unguarded':{'weight':.08,'enable_guard':False}}


def fixture(kind,transpose=0,scale=F(1)):
    if kind not in KINDS:raise ValueError('unknown_kind')
    events=[];expected=[]
    def add(name,start,duration,voice):
        p=pitch.Pitch(name).transpose(transpose)
        events.append({'pitch':p.nameWithOctave,'start':q(start*scale),'duration':q(duration*scale),'voice':voice})
    for cell in range(4):
        if kind in KINDS[:2]:
            changed=kind=='different_chords_between_cells' and cell>=2
            names=['G3','B3','D4','G4'] if changed else ['C3','E3','G3','C4']
            for i,name in enumerate(names):add(name,F(cell)+F(i,4),F(1,4),'1')
        else:
            shared=kind=='change_inside_cell_shared_seventh_union'
            upper=['G4','E4','G4','E4'] if shared else ['G4','E4','C#5','A#4']
            for i,name in enumerate(upper):add(name,F(cell)+F(i,4),F(1,4),'1')
            for a,names,root,quality in [(F(cell),['C3','E3','G3'],0,'major'),
                (F(cell)+F(1,2),['E3','G3','B3'] if shared else ['F#3','A#3','C#4'],4 if shared else 6,'minor' if shared else 'major')]:
                for name in names:add(name,a,F(1,2),'2')
                expected.append({'span':{'start':q(a*scale),'end':q((a+F(1,2))*scale)},'root':(root+transpose)%12,'quality':quality})
    if kind=='same_chord':expected=[{'span':{'start':q(0),'end':q(4*scale)},'root':transpose%12,'quality':'major'}]
    if kind=='different_chords_between_cells':expected=[{'span':{'start':q(a*scale),'end':q(b*scale)},'root':(r+transpose)%12,'quality':'major'} for a,b,r in [(0,2,0),(2,4,7)]]
    return {'kind':kind,'events':events,'duration':q(4*scale),'beat_type':int(4/scale),'expected':expected,
            'transpose':transpose,'scale':q(scale),'oracle':'authored_intention_not_corpus_gold'}


def load(p):return json.loads(p.read_text(encoding='utf-8'))
def fixture_xml(case):
    if f(case['scale'])!=F(1,2):return source_xml(case)
    # Preserve the archived generator. Its notation map stops at 16ths;
    # half-scale these fixtures by doubling divisions and halving note types.
    expanded={**case,'events':[{**e,'start':q(2*f(e['start'])),'duration':q(2*f(e['duration']))} for e in case['events']]}
    root=ET.fromstring(source_xml(expanded))
    for e in root.findall('.//divisions'):e.text=str(2*int(e.text))
    types={'whole':'half','half':'quarter','quarter':'eighth','eighth':'16th','16th':'32nd'}
    for e in root.findall('.//note/type'):e.text=types[e.text]
    return ET.tostring(root,encoding='unicode',xml_declaration=True)

def verify(p,sha):
    if digest(p)!=sha:raise ValueError('snapshot_hash_mismatch:'+str(p))


def build(source,output):
    if output.exists():raise ValueError('output_exists_choose_new_revision')
    # Decisions and cohort are frozen before calculation; don't optimize weight
    # against whichever real score happens to improve.
    output.mkdir(parents=True)
    contract={'version':VERSION,'arms':ARMS,'kinds':KINDS,'source_path':str(source.resolve()),
              'source_report_sha256':digest(source/'report.json'),
              'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
              'production_modified':False,'source_labels_used_for_inference':False}
    write(output/'run-contract.json',contract);synthetic=[]
    for kind in KINDS:
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            cid=kind+'-'+name;out=output/'synthetic'/cid;out.mkdir(parents=True)
            case=fixture(kind,tr,scale);xml=out/'score.musicxml';xml.write_text(fixture_xml(case),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml)
            check_roundtrip(case,ir);write(out/'canonical_music_ir.json',ir);write(out/'fixture.json',case)
            runs={arm:analyze(ir,**options) for arm,options in ARMS.items()}
            row={'case_id':cid,'kind':kind,'transform':name,'source_sha256':digest(xml),'ir_sha256':digest(out/'canonical_music_ir.json'),
                 'metrics':{arm:metrics(case['expected'],r) for arm,r in runs.items()},
                 'guarded_cells':sum(c['eligibility']=='vertical_replacement_guard' for c in runs['on']['figure_cells']),
                 'changed':signature(runs['off'])!=signature(runs['on'])}
            write(out/'results.json',{'summary':row,'runs':runs});synthetic.append(row)
    real=[];prior=load(source/'report.json')
    for item in prior['cases']:
        cid=item['case_id'];src=source/'real-cases'/cid;out=output/'real-cases'/cid;out.mkdir(parents=True)
        provenance=load(src/'case-provenance.json');entry=provenance['manifest_entry'];plan=provenance['frozen_plan']
        if any(provenance[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not entry['rights']['internal_research_use']:
            raise ValueError('ineligible_case')
        score_name=Path(entry['score_source_path']).name
        verify(src/score_name,entry['score_sha256']);verify(src/'canonical_music_ir.json',plan['ir_sha256'])
        for filename in (score_name,'canonical_music_ir.json','case-provenance.json','results.json'):
            shutil.copyfile(src/filename,out/filename)
        ir=load(src/'canonical_music_ir.json');comparisons=[]
        for old in load(src/'results.json')['runs']:
            runs={arm:analyze(ir,old['analysis_span'],**options) for arm,options in ARMS.items()}
            if signature(runs['off'])!=signature(old['experiment']) or abs(runs['off']['path_cost']-old['experiment']['path_cost'])>1e-8:
                raise ValueError('zero_weight_does_not_reproduce_frozen_current')
            comparisons.append({'analysis_span':old['analysis_span'],'margin_quarters':old['margin_quarters'],**runs})
        row={'case_id':cid,'collection':item['collection'],
             'changed_contexts':sum(signature(r['off'])!=signature(r['on']) for r in comparisons),
             'weight_sensitive_contexts':sum(signature(r['low'])!=signature(r['high']) for r in comparisons),
             'context_stable':{arm:context_stable(comparisons,arm,provenance['case']['target_span'],2) for arm in ('off','on')}}
        write(out/'trial-results.json',{'summary':row,'runs':comparisons});real.append(row)
        print(cid,row['changed_contexts'],row['context_stable'],flush=True)
    report={'contract':contract,'synthetic':synthetic,'real':real,
            'summary':{'synthetic_cases':len(synthetic),'real_cases':len(real),
                       'real_changed_contexts':sum(r['changed_contexts'] for r in real),
                       'stable':{arm:sum(r['context_stable'][arm] is True for r in real) for arm in ('off','on')},
                       'weight_sensitive_contexts':sum(r['weight_sensitive_contexts'] for r in real)}}
    write(output/'report.json',report);print(report['summary'],flush=True)
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();build(args.source,args.output)
