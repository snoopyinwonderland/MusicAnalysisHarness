"""Regression and lossless-envelope audit; does not measure harmony accuracy."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
from .formal_ir import q
from .harmony_arpeggio_benchmark import write,digest,check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_candidate_catalog import propose,VERSION
from .harmony_open_candidates import window


def summary(r):
    counts=Counter(c['provider'] for c in r['candidates'])
    durations={str(c['total_note_time_quarters']) for c in r['candidates']}
    assert len(durations)<=1
    return {'providers':dict(counts),'candidates':len(r['candidates']),
        'additional_seventh_qualities':dict(Counter(c['quality'] for c in r['providers']['additional_sevenths'])),
        'validation':r['validation'],'equal_note_time':True}


def controls(output):
    from music21 import converter,pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    specs=[('aug_major7',['C3','E3','G#3','B3'],'+M7',[]),
           ('minor_major7',['C3','E-3','G3','B3'],'mM7',[]),
           ('missing_fifth',['C3','E3','B3'],'+M7',[['G',1]]),
           ('respelling',['C3','E3','A-3','B3'],'+M7',[['G',1]]),
           ('rootless',['E-3','G3','B3'],None,None),
           ('no_seventh',['C3','E3','G#3'],None,None)]
    rows=[]
    for kind,ps,quality,missing in specs:
        for variant,tr,scale in [('base',False,F(1)),('transpose',True,F(1)),('scaled',False,F(1,2))]:
            dst=output/(kind+'-'+variant);dst.mkdir(parents=True)
            fixture={'scale':q(scale),'beat_type':int(4/scale),'events':[
                {'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,
                 'start':q(0),'duration':q(scale),'voice':str(i+1)} for i,p in enumerate(ps)]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(fixture),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml)
            check_roundtrip(fixture,ir);span={'start':q(0),'end':q(scale)};r=propose(ir,span)
            cs=[c for c in r['providers']['additional_sevenths'] if c['root_coordinate']==(['D',0] if tr else ['C',0])]
            if quality is None:assert not cs
            else:
                c=next(c for c in cs if c['quality']==quality)
                expected=([['A',1]] if tr and missing else missing)
                assert c['missing_spellings']==expected
            assert r['providers']['base']==window(ir,span)
            write(dst/'canonical_music_ir.json',ir);write(dst/'catalog.json',r)
            rows.append({'case':dst.name,'passed':True,'xml_sha256':digest(xml),**summary(r)})
    return rows


def build(source,augmented,extended,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True)
    write(output/'run-contract.json',{'version':VERSION,'sources':{str(p):digest(p/'report.json') for p in (source,augmented,extended)},
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'cohort':'same 24 train windows, all 45 existing augmentation/extension controls; 18 new authored XML controls',
        'rights':'internal research only; no training/redistribution approval inferred'})
    report={'version':VERSION,'fixed_windows':[],'prior_controls':[],'accuracy_measured':False,'production_modified':False,
        'limits':['Lossless candidate envelope does not rank, infer function or automatically choose boundaries.',
            'Same training windows, not held-out accuracy; prior controls use their frozen IR.',
            'New seventh gate requires observed root/third/seventh; fifth omission generates competing readings.']}
    for row in load(source/'report.json')['real']:
        src=source/'real-cases'/row['case_id'];snap=src/'source-snapshot'
        prov=load(snap/'case-provenance.json')
        if prov['manifest_entry']['split']!='train' or not prov['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible')
        for name,h in row['source_hashes'].items():
            if digest(snap/name)!=h:raise ValueError('source_changed')
        ir=load(snap/'candidate_revision_ir.json');old=deepcopy(ir)
        dst=output/'fixed-windows'/row['case_id'];dst.mkdir(parents=True)
        for i,item in enumerate(load(src/'manifest.json')):
            r=propose(ir,item['span']);assert r['providers']['base']==window(ir,item['span'])
            write(dst/f'{i}.json',r)
            report['fixed_windows'].append({'case_id':row['case_id'],'window':i,'display':item['display'],
                'input_path':str(snap/'candidate_revision_ir.json'),'input_sha256':digest(snap/'candidate_revision_ir.json'),**summary(r)})
        assert ir==old
    for origin,provider in ((augmented,'augmented'),(extended,'extended')):
        for row in load(origin/'report.json')['xml_controls']:
            src=origin/'controls'/row['case']
            if digest(src/'score.musicxml')!=row['xml_sha256']:raise ValueError('control_changed')
            ir=load(src/'canonical_music_ir.json');prior=load(src/'result.json')
            r=propose(ir,prior['span'],prior['context_span'])
            assert r['providers']['base']==prior['base_window']
            assert r['providers'][provider]=={k:v for k,v in prior.items() if k!='base_window'}
            dst=output/'prior-controls'/provider/row['case'];dst.mkdir(parents=True)
            write(dst/'catalog.json',r)
            report['prior_controls'].append({'case':row['case'],'provider':provider,
                'input_path':str(src/'canonical_music_ir.json'),'input_sha256':digest(src/'canonical_music_ir.json'),
                'prior_result_sha256':digest(src/'result.json'),'provider_unchanged':True,**summary(r)})
    report['xml_controls']=controls(output/'controls');write(output/'report.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('source','augmented','extended','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();r=build(a.source,a.augmented,a.extended,a.output)
    print({'fixed_windows':len(r['fixed_windows']),'prior_controls':len(r['prior_controls']),
           'new_xml_controls':len(r['xml_controls']),'output':str(a.output)})
