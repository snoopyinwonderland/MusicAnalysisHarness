"""Frozen all-pair pilot, including cases without an atomic technical probe."""
import argparse
from pathlib import Path
from collections import Counter
from .harmony_progression_evidence_trial import load,write,digest
from .harmony_candidate_relation_survey import plan,run,VERSION


def replay(source,ir_source,output,max_pairs=512,temporal=False):
    report=load(source/'report.json');ir_report=load(ir_source/'report.json')
    output.mkdir(parents=True,exist_ok=False)
    planned=[]
    for row in report['records']:
        path=Path(row['artifact'])
        if digest(path)!=row['sha256']:raise ValueError('input_changed')
        planned.append({'case_id':row['case_id'],'sample':row['sample'],'source':str(path),
                        'sha256':row['sha256'],'plan':plan(load(path))})
    write(output/'plan.json',{'version':VERSION,'source_report_sha256':digest(source/'report.json'),'samples':planned})
    write(output/'run-contract.json',{'version':VERSION,'max_pairs':max_pairs,'temporal_enabled':temporal,'plan_sha256':digest(output/'plan.json'),
        'ir_report_sha256':digest(ir_source/'report.json'),'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'source_labels_used':False,'accuracy_measured':False,'production_modified':False})
    rows=[];counts=Counter();temporal_counts=Counter()
    for item in planned:
        folder=ir_source/'real-cases'/item['case_id']/'source-snapshot'
        ref=next(r for r in ir_report['real'] if r['case_id']==item['case_id'])
        for name,h in ref['source_hashes'].items():
            if digest(folder/name)!=h:raise ValueError('snapshot_changed')
        rights=load(folder/'case-provenance.json')['manifest_entry']
        if rights['split']!='train' or not rights['rights']['internal_research_use']:raise ValueError('research_only')
        result=run(load(Path(item['source'])),load(folder/'candidate_revision_ir.json'),max_pairs,temporal)
        if result['plan']!=item['plan']:raise ValueError('plan_changed')
        dest=output/item['case_id']/f"{item['sample']}.json";write(dest,result)
        if digest(Path(item['source']))!=item['sha256']:raise ValueError('input_mutated')
        row={'case_id':item['case_id'],'sample':item['sample'],'pairs':len(item['plan']['pairs']),
             'status':result['status'],'summary':result.get('summary',{}),'temporal_summary':result.get('temporal_summary',{}),
             'artifact':str(dest),'sha256':digest(dest)}
        rows.append(row);counts.update(row['summary']);temporal_counts.update(row['temporal_summary'])
        print(row,flush=True)
    report={'version':VERSION,'records':rows,'summary':dict(counts),'temporal_enabled':temporal,
            'temporal_summary':dict(temporal_counts),'accuracy_measured':False,'production_modified':False}
    write(output/'report.json',report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--ir-source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-pairs',type=int,default=512);p.add_argument('--temporal',action='store_true');a=p.parse_args()
    replay(a.source,a.ir_source,a.output,a.max_pairs,a.temporal)
