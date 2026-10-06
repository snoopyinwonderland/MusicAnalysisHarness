"""Replay frozen technical paths, without selecting or ranking musical readings."""
import argparse
import hashlib
import json
from pathlib import Path

from .harmony_progression_evidence import VERSION, vector, compare


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def run(source, output, include_bass=False, include_resolution=False, ir_source=None, include_polyphony=False, include_constraints=False):
    report_path = source/'report.json'; report_hash = digest(report_path)
    source_report = load(report_path)
    output.mkdir(parents=True, exist_ok=False)
    write(output/'run-contract.json', {'version':VERSION, 'source_report_sha256':report_hash,
        'selection':'all saved technical probes and same-member checks; no new musical path selection',
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'include_bass_roles':include_bass,
        'include_resolution':include_resolution,
        'ir_source':str(ir_source) if ir_source else None,
        'include_polyphony':include_polyphony,
        'include_constraints':include_constraints,
        'source_labels_used':False, 'accuracy_measured':False, 'production_modified':False})
    records=[]
    for item in source_report['records']:
        original=Path(item['artifact'])
        if digest(original)!=item['sha256']: raise ValueError('input_hash_changed')
        result=load(original); outputs=[]
        if result['status']=='ready':
            probe=result.get('technical_probe')
            if probe:
                e=probe['evaluation']
                outputs.append({'kind':'technical_probe_vector',
                    'result':vector(result,e['path'],e['assignment_ref'])})
                if include_bass:
                    from .harmony_progression_bass import analyze
                    outputs.append({'kind':'conditional_bass_roles',
                        'result':analyze(result,e['path'],e['assignment_ref'])})
                if include_resolution:
                    from .harmony_progression_resolution import analyze as resolution
                    outputs.append({'kind':'conditional_target_relations',
                        'result':resolution(result,e['path'],e['assignment_ref'])})
                    if ir_source is not None:
                        snapshot=ir_source/'real-cases'/item['case_id']/'source-snapshot'
                        provenance=load(snapshot/'case-provenance.json')['manifest_entry']
                        if provenance['split']!='train' or not provenance['rights']['internal_research_use']:
                            raise ValueError('research_only')
                        source_entry=next(r for r in load(ir_source/'report.json')['real'] if r['case_id']==item['case_id'])
                        for name,h in source_entry['source_hashes'].items():
                            if digest(snapshot/name)!=h:raise ValueError('ir_snapshot_changed')
                        ir_path=snapshot/'candidate_revision_ir.json'
                        outputs.append({'kind':'explicit_multivoice_target_relations',
                            'ir_path':str(ir_path),'ir_sha256':digest(ir_path),
                            'result':resolution(result,e['path'],e['assignment_ref'],ir=load(ir_path))})
                        if include_polyphony:
                            from .harmony_progression_polyphony import analyze as polyphony
                            outputs.append({'kind':'bounded_polyphonic_target_relations',
                                'ir_path':str(ir_path),'ir_sha256':digest(ir_path),
                                'result':polyphony(result,e['path'],e['assignment_ref'],load(ir_path))})
                        if include_constraints:
                            from .harmony_resolution_constraints import analyze as constraints
                            outputs.append({'kind':'factorized_direct_resolution_query',
                                'ir_path':str(ir_path),'ir_sha256':digest(ir_path),
                                'result':constraints(result,e['path'],e['assignment_ref'],load(ir_path))})
            for check in item['checks']:
                if check['kind']=='same_members_all_atomic_segments':
                    aid=max(result['assignments'],key=lambda a:len(a['links']))['assignment_id']
                    value=compare(result,check['hold'],check['split'],aid)
                    if value['first']['cells']!=value['second']['cells']:
                        raise ValueError('same_members_observations_changed')
                    outputs.append({'kind':'same_members_comparison','result':value})
        status='ready' if outputs else 'no_saved_eligible_path' if result['status']=='ready' else result['status']
        dest=output/item['case_id']/f"{item['sample']}.json"
        write(dest,{'version':VERSION,'status':status,'source_sha256':item['sha256'],
                    'experiments':outputs,'selected':None,'musical_accuracy_measured':False})
        records.append({'case_id':item['case_id'],'sample':item['sample'],'status':status,
                        'experiments':len(outputs),'artifact':str(dest),'sha256':digest(dest)})
        if digest(original)!=item['sha256']: raise ValueError('input_mutated')
    if digest(report_path)!=report_hash: raise ValueError('report_mutated')
    final={'version':VERSION,'include_bass_roles':include_bass,'include_resolution':include_resolution,
           'records':records,'experiment_count':sum(r['experiments'] for r in records),
           'accuracy_measured':False,'production_modified':False}
    write(output/'report.json',final)
    return final


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--bass',action='store_true')
    p.add_argument('--resolution',action='store_true');p.add_argument('--ir-source',type=Path)
    p.add_argument('--polyphony',action='store_true');p.add_argument('--constraints',action='store_true');a=p.parse_args()
    if a.ir_source is not None and not a.resolution:p.error('--ir-source requires --resolution')
    if a.polyphony and a.ir_source is None:p.error('--polyphony requires --ir-source')
    if a.constraints and a.ir_source is None:p.error('--constraints requires --ir-source')
    print(run(a.source,a.output,a.bass,a.resolution,a.ir_source,a.polyphony,a.constraints)['experiment_count'])
