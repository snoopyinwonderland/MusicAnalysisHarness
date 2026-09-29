"""Source-conditioned Unit 14 sonata links; no cadence gold or production change."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .harmony_case_retrieval import _f, load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .predominant_sonata_audit import span_observation
from .tonal_foundations import spelled_triad_shapes, spelled_seventh_shapes
from .tonal_role_context import propose, source_symbol, VERSION


def build(manifest_path, output):
    out = Path(output)
    if out.exists():
        raise ValueError('output_exists')
    raw = Path(manifest_path).read_bytes()
    entries = json.loads(raw)['entries']
    validate_split(entries)
    selected = [e for e in entries if e['split'] == 'train' and
                e['collection_id'] in ('mozart-sonatas', 'beethoven-sonatas')]
    if len({e['package_path'] for e in selected}) != len(selected):
        raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected):
        raise ValueError('research_not_permitted')
    out.mkdir(parents=True)
    modules = ['tonal_role_context.py', 'tonal_role_audit.py', 'tonal_foundations.py',
               'cadential_six_four_audit.py', 'foundation_sonata_audit.py', 'predominant_sonata_audit.py',
               'harmony_case_retrieval.py', 'harmony_review_cohort.py', 'harmony_review_supplement.py',
               'harmony_curriculum.py']
    contract = {'version': VERSION, 'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'entries': selected,
                'selection': 'all plain root IV/iv/vi/VI and IV6/iv6 in train sonatas; do not require textbook neighbors',
                'neighbors': 'immediate annotation, touching span, same source key; otherwise no supplied neighbor',
                'source_conditioned': True, 'blind_accuracy_measured': False, 'production_enabled': False,
                'code_hashes': {n: digest(Path(__file__).with_name(n)) for n in modules}}
    (out/'run-contract.json').write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding='utf-8')
    records, scores = [], []
    skipped, role_counts, cadence_counts, collection_counts = Counter(), Counter(), Counter(), Counter()
    for e in selected:
        folder = Path(e['package_path'])
        hashes = {n: digest(folder/n) for n in ('canonical_music_ir.json', 'imported_annotations.jsonl', 'alignment_records.jsonl')}
        if digest(e['score_source_path']) != e['score_sha256']:
            raise ValueError('score_hash_mismatch')
        p = load_prepared_package(folder)
        ir = p['ir']
        if ir['ir_document_id'] != e['ir_document_id'] or ir['score']['score_id'] != e['score_id']:
            raise ValueError('ir_identity_mismatch')
        annotations, rejected = verified_annotations(p, e)
        skipped.update(rejected)
        count = 0
        for i, a in enumerate(annotations):
            # Exclude unrelated records before requiring source-key metadata.
            if a['raw_fields'].get('numeral') not in ('IV', 'iv', 'vi', 'VI'):
                continue
            key = source_key(a)
            symbol = source_symbol(a, key[2])
            if symbol not in ('IV', 'iv', 'IV6', 'iv6', 'vi', 'VI'):
                continue
            span = a['target']['span']

            def neighbor(index, direction):
                if index < 0 or index >= len(annotations):
                    return {'symbol': None, 'reason': 'score_edge'}
                x = annotations[index]
                xs = x['target']['span']
                touching = (_f(xs['end']) == _f(span['start']) if direction == 'previous'
                            else _f(span['end']) == _f(xs['start']))
                reason = ('nonadjacent' if not touching else 'source_key_change' if source_key(x) != key else None)
                sym = source_symbol(x, key[2]) if reason is None else None
                return {'annotation_id': x['annotation_id'], 'symbol': sym,
                        'reason': reason or ('supported' if sym else 'unsupported_source_symbol')}

            left, right = neighbor(i-1, 'previous'), neighbor(i+1, 'following')
            hypothesis = propose(left['symbol'], symbol, right['symbol'], key[2])
            context = context_excerpt(ir, span)
            inventory = span_observation(ir, span)
            for cell in inventory['slices']:
                pitches = [x['pitch'] for x in cell['events']]
                cell['complete_triad_shapes'] = spelled_triad_shapes(pitches)
                cell['complete_seventh_shapes'] = spelled_seventh_shapes(pitches)
            cid = 'u14_'+hashlib.sha256((ir['ir_document_id']+'|'+a['annotation_id']).encode()).hexdigest()[:16]
            record = {'case_id': cid, 'concept_id': 'hvl.unit14', 'identity': e, 'package_hashes': hashes,
                      'target_annotation_id': a['annotation_id'], 'target_span': span,
                      'source_key_hypothesis': {'tonic_step': key[0], 'tonic_alter': key[1], 'mode': key[2]},
                      'source_label': a['raw_label'], 'printed_measure': a['raw_fields'].get('mn'),
                      'neighbors': {'previous': left, 'following': right},
                      'source_context': annotations[max(0, i-2):i+3],
                      'source_cadence_field': a['raw_fields'].get('cadence') or None,
                      'context_excerpt': context, 'target_surface_inventory': inventory,
                      'conditional_role_candidates': hypothesis,
                      'source_conditioned': True, 'training_eligible': False, 'production_enabled': False}
            path = out/(cid+'.json')
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
            roles = [x['role'] for x in hypothesis['role_hypotheses']]
            cadences = [x['type'] for x in hypothesis['cadence_hypotheses']]
            records.append({'case_id': cid, 'score': folder.name, 'collection': e['collection_id'],
                            'printed_measure': record['printed_measure'], 'source_label': a['raw_label'],
                            'supplied_symbols': hypothesis['input_symbols'], 'role_candidates': roles,
                            'unverified_cadence_candidates': cadences, 'source_cadence_field': record['source_cadence_field'],
                            'json_sha256': digest(path)})
            role_counts.update(roles)
            cadence_counts.update(cadences)
            collection_counts[e['collection_id']] += 1
            count += 1
        scores.append({'score': folder.name, 'case_count': count, 'package_hashes': hashes})
    report = {'version': VERSION, 'summary': {'score_count': len(scores), 'case_count': len(records),
              'by_collection': dict(collection_counts), 'source_conditioned_role_candidates': dict(role_counts),
              'unverified_cadence_candidates': dict(cadence_counts),
              'cases_without_matching_role_pattern': sum(not r['role_candidates'] for r in records)},
              'records': records, 'scores': scores, 'skipped': dict(skipped),
              'contract_sha256': digest(out/'run-contract.json'),
              'blind_accuracy_measured': False, 'production_enabled': False}
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.manifest, args.output)['summary'], indent=2))
