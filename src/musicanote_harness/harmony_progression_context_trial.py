"""Fixed systematic pilot of the multi-interval contract, before reading labels."""
import argparse
from collections import Counter
from pathlib import Path
from .harmony_arpeggio_benchmark import write, digest
from .harmony_shared_tone_trial import load
from .harmony_progression_context import plan, build, evaluate, VERSION


def run(source,output,baseline_source=None):
    if output.exists():raise ValueError('choose_new_output')
    previous=load(source/'report.json');frozen=[]
    for row in previous['real']:
        folder=source/'real-cases'/row['case_id']
        for index in range(0,row['samples'],16):
            path=folder/'samples'/f'{index}.json';sample=load(path);resume=None
            if sample['status']=='no_additional_held_boundary' and baseline_source is not None:
                original=path;original_hash=digest(original)
                path=baseline_source/'real-cases'/row['case_id']/'samples'/f'{index}.json'
                if digest(path)!=sample['previous_sample_sha256']:raise ValueError('archival_sample_hash_mismatch')
                resume={'placeholder_path':str(original),'placeholder_sha256':original_hash,
                        'reason':'no new held cut is not missing analysis; use exact archived baseline'}
                sample=load(path)
            frozen.append({'case_id':row['case_id'],'title':row['title'],'sample':index,
                           'source_path':str(path),'sha256':digest(path),
                           'archival_resume':resume,
                           'plan':plan(sample['events'],sample['span']) if sample['status']=='ready' else None})
    output.mkdir(parents=True)
    write(output/'plan.json',{'version':VERSION,'selection':'indices 0,16,32,... per frozen work; no source annotations read',
                             'samples':frozen,'source_report_sha256':digest(source/'report.json')})
    write(output/'run-contract.json',{'version':VERSION,'plan_sha256':digest(output/'plan.json'),
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'source_labels_used':False,'production_modified':False,'accuracy_measured':False})
    records=[];counts=Counter()
    for entry in frozen:
        folder=source/'real-cases'/entry['case_id'];snapshot=folder/'source-snapshot'
        provenance=load(snapshot/'case-provenance.json')['manifest_entry']
        if provenance['split']!='train' or not provenance['rights']['internal_research_use']:raise ValueError('research_only')
        original=next(r for r in previous['real'] if r['case_id']==entry['case_id'])
        for name,h in original['source_hashes'].items():
            if digest(snapshot/name)!=h:raise ValueError('snapshot_changed')
        path=Path(entry['source_path']);baseline=load(path)
        result=build(load(snapshot/'candidate_revision_ir.json'),baseline)
        row={k:entry[k] for k in ('case_id','title','sample')};row['status']=result['status'];counts[result['status']]+=1
        checks=[]
        if result['status']=='ready':
            if result['plan']!=entry['plan']:raise ValueError('plan_changed')
            last=len(result['plan']['points'])-1;edges=result['edges']
            whole=next(i for i,e in enumerate(edges) if e['from']==0 and e['to']==last)
            atomic=[next(i for i,e in enumerate(edges) if e['from']==j and e['to']==j+1) for j in range(last)]
            def available(ei):
                out={}
                for ri,r in enumerate(edges[ei]['readings']):
                    if not r['abstention_reasons']:out.setdefault(tuple(sorted(tuple(m) for m in r['members'])),ri)
                return out
            maps=[available(i) for i in [whole,*atomic]]
            shared=set(maps[0])
            for m in maps[1:]:shared &= set(m)
            aid=max(result['assignments'],key=lambda a:len(a['links']))['assignment_id']
            if shared:
                members=sorted(shared)[0]
                hold=[{'edge':whole,'reading':maps[0][members]}]
                split=[{'edge':ei,'reading':m[members]} for ei,m in zip(atomic,maps[1:])]
                h=evaluate(result,hold,aid);s=evaluate(result,split,aid)
                if h['cells']!=s['cells'] or h['note_time']!=s['note_time']:raise ValueError('same_members_partition_changed')
                checks.append({'kind':'same_members_all_atomic_segments','passed':True,'hold':hold,'split':split})
            # Arbitrary first available reading on each interval tests time accounting only.
            if all(m for m in maps[1:]):
                probe=[{'edge':ei,'reading':next(iter(m.values()))} for ei,m in zip(atomic,maps[1:])]
                ev=evaluate(result,probe,aid)
                if ev['total_note_time']!=baseline['total_note_time']:raise ValueError('path_note_time_loss')
                result['technical_probe']={'policy':'first unblocked reading per atomic edge, NOT inferred music',
                                           'evaluation':ev}
                checks.append({'kind':'multi_segment_note_time_conservation','passed':True,'segments':len(probe)})
            row.update(edges=len(edges),cells=last,readings=sum(len(e['readings']) for e in edges),patterns=len(result['patterns']))
        row['checks']=checks;dest=output/entry['case_id']/f"{entry['sample']}.json"
        dest.parent.mkdir(parents=True,exist_ok=True);write(dest,result)
        row['artifact']=str(dest);row['sha256']=digest(dest);records.append(row)
        if digest(path)!=entry['sha256']:raise ValueError('baseline_mutated')
        print(row['title'],row['sample'],row['status'],len(checks),flush=True)
    report={'version':VERSION,'summary':dict(counts),'records':records,'accuracy_measured':False,'production_modified':False}
    write(output/'report.json',report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--baseline-source',type=Path)
    a=p.parse_args();print(run(a.source,a.output,a.baseline_source)['summary'])
