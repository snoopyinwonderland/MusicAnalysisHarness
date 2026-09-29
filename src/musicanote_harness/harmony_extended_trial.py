"""Frozen windows, historical Unit28 inputs, and MusicXML controls for coverage."""
import argparse
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
from .formal_ir import q
from .harmony_arpeggio_benchmark import write, digest, check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_extended_candidates import propose, VERSION
from .harmony_open_candidates import window


def summary(r):
    cs=r['extended_candidates']
    return {'base_candidates':len(r['base_window']['candidates']),'extended_proposals':len(cs),
        'root_coordinates':len(r['references']),'pooled_complete':sum(c['pooled_complete'] for c in cs),
        'simultaneous_complete':sum(c['simultaneous_complete'] for c in cs),
        'proposal_support_simultaneous':sum(c['proposal_support_simultaneous'] for c in cs),
        'root_absent_proposals':sum(not c['root_observed'] for c in cs),
        'missing_third_proposals':sum('third' in c['missing_core_roles'] for c in cs),
        'contextual_paths':sum(len((ref['context_evidence'] or {}).get('paths',[])) for ref in r['references']),
        'abstention_reasons':r['abstention_reasons']}


def controls(output):
    from music21 import converter, pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    core=['C3','E3','G3','B-3']
    specs=[('minor9',core+['D-4'],['minor_ninth']),('major9',core+['D4'],['major_ninth']),
        ('fourth11',core+['F4'],['fourth_or_eleventh']),('minor6_13',core+['A-4'],['minor_sixth_or_thirteenth']),
        ('major6_13',core+['A4'],['major_sixth_or_thirteenth']),
        ('rootless9',['E3','G3','B-3','D4'],['major_ninth']),
        ('omitted5',['C3','E3','B-3','D4'],['major_ninth']),
        ('combined',core+['D4','A4'],['major_ninth','major_sixth_or_thirteenth']),
        ('triad_add9',['C3','E3','G3','D4'],None),('respelling',core+['C#4'],None)]
    rows=[]
    for kind,ps,roles in specs:
        for variant,tr,scale in [('base',False,F(1)),('transpose',True,F(1)),('scaled',False,F(1,2))]:
            dst=output/(kind+'-'+variant);dst.mkdir(parents=True)
            fixture={'scale':q(scale),'beat_type':int(4/scale),'events':[
                {'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,
                 'start':q(0),'duration':q(scale),'voice':str(i+1)} for i,p in enumerate(ps)]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(fixture),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml)
            check_roundtrip(fixture,ir);span={'start':q(0),'end':q(scale)};r=propose(ir,span)
            cs=[c for c in r['extended_candidates'] if c['root_coordinate']==(['D',0] if tr else ['C',0])]
            if roles is None:assert not cs
            else:
                c=next(c for c in cs if set(c['added_roles'])==set(roles))
                assert c['root_observed']==(kind!='rootless9')
                assert c['pooled_complete']==(kind not in ('rootless9','omitted5'))
                assert c['simultaneous_complete']==c['pooled_complete']
                assert c['proposal_support_simultaneous']
            assert r['base_window']==window(ir,span)
            write(dst/'canonical_music_ir.json',ir);write(dst/'result.json',r)
            rows.append({'case':dst.name,'passed':True,'xml_sha256':digest(xml),**summary(r)})
    return rows


def build(source,unit28,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);(output/'historical-unit28').mkdir()
    report={'version':VERSION,'fixed_windows':[],'historical_unit28':[],
        'accuracy_measured':False,'production_modified':False,
        'limits':['Fixed 24 windows reuse training works, not independent evaluation.',
            'Historical 202 Unit28 cases were annotation-selected and retain old IR/mapping limitations.',
            'Source modifiers were not fully interpreted in Unit28; reference root is not an extended-chord gold label.',
            'Only score events and frozen times enter inference. Comparisons follow inference.',
            'Dominant-seventh added-tone profile only; no automatic functional Roman numeral.']}
    write(output/'run-contract.json',{'version':VERSION,'source_report_sha256':digest(source/'report.json'),
        'unit28_report_sha256':digest(unit28/'report.json'),
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'selection':'all 24 frozen windows and all 202 historical Unit28 saved cases',
        'licence':'internal research only; no training or redistribution permission inferred'})
    for row in load(source/'report.json')['real']:
        src=source/'real-cases'/row['case_id'];snap=src/'source-snapshot'
        prov=load(snap/'case-provenance.json')
        if prov['manifest_entry']['split']!='train' or not prov['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible')
        for name,h in row['source_hashes'].items():
            if digest(snap/name)!=h:raise ValueError('source_changed')
        ir=load(snap/'candidate_revision_ir.json');saved=deepcopy(ir)
        dst=output/'fixed-windows'/row['case_id'];dst.mkdir(parents=True)
        for i,item in enumerate(load(src/'manifest.json')):
            r=propose(ir,item['span']);assert r['base_window']==window(ir,item['span'])
            write(dst/f'{i}.json',r)
            report['fixed_windows'].append({'case_id':row['case_id'],'window':i,'display':item['display'],
                'input_path':str(snap/'candidate_revision_ir.json'),'input_sha256':digest(snap/'candidate_revision_ir.json'),**summary(r)})
        assert ir==saved
    for path in sorted(unit28.glob('u28_*.json')):
        record=load(path);identity=record['identity'];excerpt=record['context_excerpt']
        if identity['split']!='train' or not identity['rights']['internal_research_use']:raise ValueError('ineligible')
        ir={k:excerpt[k] for k in ('note_events','sounding_events','measures')};saved=deepcopy(ir)
        row={'case_id':record['case_id'],'source_path':str(path),'source_sha256':digest(path),'historical_quality':identity['quality']}
        try:r=propose(ir,excerpt['target_span'],excerpt['context_span'])
        except ValueError as exc:row.update(status='input_rejected',reason=str(exc))
        else:
            assert ir==saved
            write(output/'historical-unit28'/path.name,r)
            cs=[c for c in r['extended_candidates'] if c['root_coordinate']==record['reference']['base']['root']]
            row.update(status='proposed',**summary(r),reference_root_has_proposal=bool(cs),
                       reference_root_proposals=len(cs),reference_root_added_roles=sorted({v for c in cs for v in c['added_roles']}))
        report['historical_unit28'].append(row)
    report['xml_controls']=controls(output/'controls');write(output/'report.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--unit28',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=build(a.source,a.unit28,a.output)
    print({'fixed_windows':len(r['fixed_windows']),'historical_records':len(r['historical_unit28']),
           'xml_controls':len(r['xml_controls']),'output':str(a.output)})
