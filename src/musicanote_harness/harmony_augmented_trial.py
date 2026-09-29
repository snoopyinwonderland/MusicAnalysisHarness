"""Reproducible candidate-coverage audit, not a harmonic accuracy benchmark."""
import argparse
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
from .formal_ir import q
from .harmony_arpeggio_benchmark import write, digest, check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_augmented_candidates import propose, VERSION
from .harmony_open_candidates import window


def summary(r):
    cs=r['augmented_sixth_candidates']
    return {'base_candidates':len(r['base_window']['candidates']), 'augmented_proposals':len(cs),
        'pooled_complete':sum(c['pooled_complete'] for c in cs),
        'simultaneous_complete':sum(c['simultaneous_complete'] for c in cs),
        'with_joint_geometry':sum(bool((c['context_evidence'] or {}).get('joint_geometry')) for c in cs),
        'abstention_reasons':r['abstention_reasons']}


def controls(output):
    from music21 import converter, pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    specs={'It':['A-3','C4','F#4'], 'Ger':['A-3','C4','E-4','F#4'],
           'Fr':['A-3','C4','D4','F#4'], 'Ger43':['A-3','C4','D#4','F#4'],
           'dominant_respelling':['A-3','C4','E-4','G-4']}
    rows=[]
    for kind,ps in specs.items():
        for variant,tr,scale in [('base',False,F(1)),('transpose',True,F(1)),('scaled',False,F(1,2))]:
            dst=output/(kind+'-'+variant);dst.mkdir(parents=True)
            fixture={'scale':q(scale),'beat_type':int(4/scale),'events':[
                {'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,
                 'start':q(0),'duration':q(scale),'voice':str(i+1)} for i,p in enumerate(ps)]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(fixture),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml)
            check_roundtrip(fixture,ir)
            span={'start':q(0),'end':q(scale)};r=propose(ir,span)
            cs=[c for c in r['augmented_sixth_candidates'] if c['tonic_coordinate']==(['D',0] if tr else ['C',0])]
            if kind=='dominant_respelling':assert not cs
            else:assert any(c['family']==kind and c['pooled_complete'] and c['simultaneous_complete'] for c in cs)
            assert r['base_window']==window(ir,span)
            write(dst/'canonical_music_ir.json',ir);write(dst/'result.json',r)
            rows.append({'case':dst.name,'passed':True,'xml_sha256':digest(xml),**summary(r)})
    return rows


def build(source,unit30,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True)
    (output/'historical-unit30').mkdir()
    report={'version':VERSION,'fixed_windows':[],'historical_unit30':[],
        'accuracy_measured':False,'production_modified':False,
        'limits':['Fixed 24 windows are the same training works, not independent evaluation.',
                  'Unit30 locations/context were selected from annotations; only prediction is label-blind.',
                  'Historical Unit30 excerpts retain their old IR/mapping limitations; not corrected-IR gold.',
                  'No source key or family is passed to propose. No chord selection or new boundary search.']}
    write(output/'run-contract.json',{'version':VERSION,'source_report_sha256':digest(source/'report.json'),
        'unit30_report_sha256':digest(unit30/'report.json'),
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'selection':'all 24 frozen windows plus every historical Unit30 record, including skipped records',
        'licence':'internal research only; no redistribution or training permission inferred'})
    for row in load(source/'report.json')['real']:
        src=source/'real-cases'/row['case_id'];snap=src/'source-snapshot'
        prov=load(snap/'case-provenance.json')
        if prov['manifest_entry']['split']!='train' or not prov['manifest_entry']['rights']['internal_research_use']:
            raise ValueError('ineligible')
        for name,h in row['source_hashes'].items():
            if digest(snap/name)!=h:raise ValueError('source_changed')
        ir=load(snap/'candidate_revision_ir.json');saved=deepcopy(ir)
        (output/'fixed-windows'/row['case_id']).mkdir(parents=True)
        for i,item in enumerate(load(src/'manifest.json')):
            r=propose(ir,item['span']);assert r['base_window']==window(ir,item['span'])
            out=output/'fixed-windows'/row['case_id']/f'{i}.json';write(out,r)
            report['fixed_windows'].append({'case_id':row['case_id'],'window':i,'display':item['display'],
                'input_path':str(snap/'candidate_revision_ir.json'),'input_sha256':digest(snap/'candidate_revision_ir.json'),**summary(r)})
        assert ir==saved
    for path in sorted(unit30.glob('u30_*.json')):
        record=load(path);identity=record['identity']
        if identity['split']!='train' or not identity['rights']['internal_research_use']:raise ValueError('ineligible')
        row={'case_id':record['case_id'],'source_path':str(path),'source_sha256':digest(path),
             'historical_status':record['status'],'historical_quality':identity['quality']}
        excerpt=record.get('context_excerpt')
        if not excerpt:
            row['status']='no_excerpt_not_tested'
        else:
            # Only observation fields and frozen times cross the inference boundary.
            ir={k:excerpt[k] for k in ('note_events','sounding_events','measures')};saved=deepcopy(ir)
            try:
                r=propose(ir,excerpt['target_span'],excerpt['context_span'])
            except ValueError as exc:
                row.update(status='input_rejected',reason=str(exc))
            else:
                assert ir==saved
                write(output/'historical-unit30'/path.name,r)
                row.update(status='proposed',**summary(r))
                # Compare reference only after inference; this is candidate inclusion,
                # never a verdict that the source label or hypothetical key is right.
                h=(record.get('evidence') or {}).get('hypothesis')
                row['reference_coordinate_family_in_candidates']=None if not h else any(
                    c['family']==h['family'] and c['tonic_coordinate']==h['key'][:2]
                    for c in r['augmented_sixth_candidates'])
        report['historical_unit30'].append(row)
    report['xml_controls']=controls(output/'controls')
    write(output/'report.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--unit30',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=build(a.source,a.unit30,a.output)
    print({'fixed_windows':len(r['fixed_windows']),'historical_records':len(r['historical_unit30']),
           'xml_controls':len(r['xml_controls']),'output':str(a.output)})
