"""Replay frozen relation diagnostics; no new candidates or promoted labels."""
import argparse
from collections import Counter
from pathlib import Path
from .harmony_progression_evidence_trial import load, write, digest
from .harmony_missing_evidence import run, VERSION


def replay(source, ir_source, output, repeated_bass=False, bass_return=False, incomplete_triads=False, omission_voice_context=False, hold_change_context=False):
    if sum((repeated_bass,bass_return,incomplete_triads,omission_voice_context,hold_change_context))>1:raise ValueError('choose_one_audit')
    engine=run;version=VERSION
    if repeated_bass:
        from .harmony_repeated_bass import run as engine, VERSION as version
    if bass_return:
        from .harmony_bass_return import run as engine, VERSION as version
    if incomplete_triads:
        from .harmony_incomplete_triads import run as engine, VERSION as version
    if omission_voice_context:
        from .harmony_omission_voice_context import run as engine, VERSION as version
    if hold_change_context:
        from .harmony_hold_change_context import run as engine, VERSION as version
    report=load(source/'report.json'); plan=load(source/'plan.json'); contract=load(source/'run-contract.json')
    ir_report=load(ir_source/'report.json')
    if digest(source/'plan.json') != contract['plan_sha256']: raise ValueError('plan_changed')
    if digest(ir_source/'report.json') != contract['ir_report_sha256']: raise ValueError('ir_report_changed')
    output.mkdir(parents=True,exist_ok=False)
    write(output/'run-contract.json',{'version':version,'source_report_sha256':digest(source/'report.json'),
        'source_plan_sha256':digest(source/'plan.json'),'ir_report_sha256':digest(ir_source/'report.json'),
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'source_labels_used':False,'gate_changed':False,'production_modified':False})
    rows=[]; counts=Counter()
    for row in report['records']:
        saved=next(s for s in plan['samples'] if (s['case_id'],s['sample'])==(row['case_id'],row['sample']))
        paths={Path(row['artifact']):row['sha256'],Path(saved['source']):saved['sha256']}
        folder=ir_source/'real-cases'/row['case_id']/'source-snapshot'
        ref=next(r for r in ir_report['real'] if r['case_id']==row['case_id'])
        paths.update({folder/name:h for name,h in ref['source_hashes'].items()})
        for p,h in paths.items():
            if digest(p)!=h: raise ValueError('input_changed')
        rights=load(folder/'case-provenance.json')['manifest_entry']
        if rights['split']!='train' or not rights['rights']['internal_research_use']: raise ValueError('research_only')
        answer=engine(load(Path(saved['source'])),load(Path(row['artifact'])),load(folder/'candidate_revision_ir.json'))
        dest=output/row['case_id']/f"{row['sample']}.json";write(dest,answer)
        for p,h in paths.items():
            if digest(p)!=h: raise ValueError('input_mutated')
        item={'case_id':row['case_id'],'sample':row['sample'],'status':answer['status'],
              'summary':answer.get('summary',{}),'artifact':str(dest),'sha256':digest(dest)}
        rows.append(item);counts.update(item['summary']); print(item,flush=True)
    answer={'version':version,'records':rows,'summary':dict(counts),'accuracy_measured':False,'gate_changed':False}
    write(output/'report.json',answer);return answer


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('source','ir-source','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--repeated-bass',action='store_true')
    parser.add_argument('--bass-return',action='store_true')
    parser.add_argument('--incomplete-triads',action='store_true')
    parser.add_argument('--omission-voice-context',action='store_true')
    parser.add_argument('--hold-change-context',action='store_true')
    args=parser.parse_args();replay(args.source,args.ir_source,args.output,args.repeated_bass,args.bass_return,args.incomplete_triads,args.omission_voice_context,args.hold_change_context)
