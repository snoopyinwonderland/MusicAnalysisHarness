"""Independent candidate checks against raw XML and archival annotations."""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from .source_identity_revision import f
from .source_note_mapping_audit import compare, xml_inventory, write
from .cadential_six_four_audit import digest


def records(path): return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def build(candidate, sequence):
    root=Path(candidate); sequence=Path(sequence)
    manifest=json.loads((root/'candidate_manifest.json').read_text()); totals=Counter(); scores=[]
    for entry in manifest['scores']:
        folder=root/entry['score']; seq=json.loads((sequence/(entry['score']+'.json')).read_text(encoding='utf-8'))
        for name,h in entry['hashes'].items():
            if digest(folder/name)!=h: raise ValueError('candidate_hash_mismatch')
        original=Path(seq['identity']['package_path']); source=Path(seq['identity']['score_source_path'])
        if digest(source)!=seq['identity']['score_sha256']: raise ValueError('source_hash_mismatch')
        ir=json.loads((folder/'canonical_music_ir.json').read_text(encoding='utf-8'))
        checks=compare(ir,xml_inventory(source))
        if any(c['status']!='exact' for c in checks.values()): raise ValueError('raw_note_comparison_failed')
        annotations=records(folder/'imported_annotations.jsonl'); old_annotations=records(original/'imported_annotations.jsonl')
        if len(annotations)!=len(old_annotations): raise ValueError('annotation_count_changed')
        for a,b in zip(old_annotations,annotations):
            normalized=deepcopy(b)
            if normalized.get('target'): normalized['target']['ir_document_id']=a['target']['ir_document_id']
            if normalized!=a: raise ValueError('annotation_changed_beyond_revision_target')
        alignments=records(folder/'alignment_records.jsonl'); old_alignments=records(original/'alignment_records.jsonl')
        if len(alignments)!=len(old_alignments): raise ValueError('alignment_count_changed')
        changed=0
        for a,b in zip(old_alignments,alignments):
            if a['annotation_id']!=b['annotation_id'] or a['mapping_status']!=b['mapping_status']: raise ValueError('alignment_status_changed')
            if b['target'] and b['target']['ir_document_id']!=ir['ir_document_id']: raise ValueError('stale_alignment_revision')
            if a.get('target') and a['target'].get('span')!=b['target'].get('span'): raise ValueError('annotation_span_changed')
            if a.get('target') and a['target'].get('point')!=b['target'].get('point'): raise ValueError('annotation_point_changed')
            expected=[]; attacked=[]
            if b.get('target') and 'span' in b['target'] and b['mapping_status'] in ('exact','verified_transform'):
                start=f(b['target']['span']['start']); end=f(b['target']['span']['end'])
                expected=[s['sounding_event_id'] for s in ir['sounding_events'] if end>start and f(s['span']['start'])<end and f(s['span']['end'])>start]
                attacked=[s['sounding_event_id'] for s in ir['sounding_events'] if s['sounding_event_id'] in set(expected) and start<=f(s['span']['start'])<end]
            elif b.get('target') and 'point' in b['target'] and b['mapping_status'] in ('exact','verified_transform'):
                instant=f(b['target']['point'])
                for s in ir['sounding_events']:
                    if f(s['span']['start'])<=instant<f(s['span']['end']):
                        expected.append(s['sounding_event_id'])
                        if f(s['span']['start'])==instant: attacked.append(s['sounding_event_id'])
            if expected!=b['sounding_event_ids'] or attacked!=b['attacked_sounding_event_ids']: raise ValueError('alignment_membership_wrong')
            changed+=set(a['sounding_event_ids'])!=set(b['sounding_event_ids']) or set(a['attacked_sounding_event_ids'])!=set(b['attacked_sounding_event_ids'])
        migration=json.loads((folder/'migration.json').read_text())
        counts={'xml_exact_notes':len(checks),'preserved_annotations':len(annotations),
            'alignment_membership_changed':changed,'sounds':len(ir['sounding_events']),
            'resolved_grace_buckets':len(migration['graph']['resolved_grace_buckets']),
            'unresolved_tie_endpoints':len(migration['graph']['issues'])}
        totals.update(counts); scores.append({'score':entry['score'],'counts':counts})
    result={'scores':scores,'summary':dict(totals),'manifest_sha256':digest(root/'candidate_manifest.json'),
            'code_sha256':digest(Path(__file__)),'production_modified':False}
    target=root/'independent_validation.json'
    if target.exists(): raise ValueError('validation_output_exists')
    write(target,result); return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--candidate',required=True); parser.add_argument('--sequence',required=True)
    args=parser.parse_args(); print(json.dumps(build(args.candidate,args.sequence)['summary'],indent=2))
