"""Train-only Unit 18 four-chord windows; supplied harmony vs actual voice geometry."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .dominant_area_evidence import _exact
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .predominant_sonata_audit import span_observation
from .tonal_foundations import spelled_triad_shapes
from .diatonic_sequence import VERSION, source_triad, propose, compare_voices


def windows(annotations, verified_ids=None):
    """Keep source order; unverified/unsupported intervening entries are barriers."""
    for i in range(len(annotations)-3):
        group = annotations[i:i+4]
        if verified_ids is not None and any(a['annotation_id'] not in verified_ids for a in group):
            continue
        items = [source_triad(a) for a in group]
        if not all(items):
            continue
        keys = [source_key(a) for a in group]
        if any(k != keys[0] for k in keys):
            continue
        spans = [a['target']['span'] for a in group]
        if any(_exact(s['end']) <= _exact(s['start']) or _exact(s['start']) < 0 for s in spans):
            continue
        if any(_exact(a['end']) != _exact(b['start']) for a, b in zip(spans, spans[1:])):
            continue
        yield i, [x[0] for x in items], [x[1] for x in items], keys[0]


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
    names = ['diatonic_sequence.py', 'diatonic_sequence_audit.py', 'root_position_context.py',
             'dominant_area_evidence.py', 'formal_ir.py', 'cadential_six_four_audit.py',
             'harmony_case_retrieval.py', 'harmony_review_cohort.py', 'harmony_review_supplement.py',
             'predominant_sonata_audit.py', 'foundation_sonata_audit.py', 'tonal_foundations.py',
             'harmony_curriculum.py']
    contract = {'version': VERSION, 'entries': selected, 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
                'selection': 'all four immediate verified touching plain triads, root/first inversion, same supplied key; keep nonmatches',
                'source_conditioned': True, 'blind_accuracy_measured': False, 'production_enabled': False,
                'code_hashes': {n: digest(Path(__file__).with_name(n)) for n in names}}
    (out/'run-contract.json').write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding='utf-8')
    records, scores = [], []
    skipped, patterns, abstentions = Counter(), Counter(), Counter()
    for e in selected:
        folder = Path(e['package_path'])
        hashes = {n: digest(folder/n) for n in ('canonical_music_ir.json', 'imported_annotations.jsonl', 'alignment_records.jsonl')}
        if digest(e['score_source_path']) != e['score_sha256']:
            raise ValueError('score_hash_mismatch')
        package = load_prepared_package(folder)
        ir = package['ir']
        if ir['ir_document_id'] != e['ir_document_id'] or ir['score']['score_id'] != e['score_id']:
            raise ValueError('ir_identity_mismatch')
        valid, rejected = verified_annotations(package, e)
        skipped.update(rejected)
        annotations = package['annotations']
        count = 0
        for i, symbols, inversions, key in windows(annotations, {a['annotation_id'] for a in valid}):
            group = annotations[i:i+4]
            result = propose(symbols, inversions, *key)
            spans = [a['target']['span'] for a in group]
            span = {'start': spans[0]['start'], 'end': spans[-1]['end']}
            geometry = compare_voices(ir, {'start': spans[0]['start'], 'end': spans[1]['end']},
                                      {'start': spans[2]['start'], 'end': spans[3]['end']})
            inventories = []
            for s, c in zip(spans, result['candidates']):
                inv = span_observation(ir, s)
                for cell in inv['slices']:
                    cell['complete_triad_shapes'] = spelled_triad_shapes([r['pitch'] for r in cell['events']])
                    cell['supplied_shape_supported'] = any(all(sh[k] == c[k] for k in
                        ('root_step', 'root_alter', 'quality', 'inversion')) for sh in cell['complete_triad_shapes'])
                inv['union_is_simultaneous'] = False
                inventories.append(inv)
            cid = 'u18_'+hashlib.sha256((ir['ir_document_id']+'|'+group[0]['annotation_id']).encode()).hexdigest()[:16]
            record = {'case_id': cid, 'concept_id': 'hvl.unit18', 'identity': e, 'package_hashes': hashes,
                      'target_span': span, 'target_annotation_ids': [a['annotation_id'] for a in group],
                      'target_source_labels': [a['raw_label'] for a in group],
                      'printed_measure_range': [group[0]['raw_fields'].get('mn'), group[-1]['raw_fields'].get('mn')],
                      'source_context': annotations[max(0, i-2):i+6], 'context_excerpt': context_excerpt(ir, span),
                      'conditional_harmonic_patterns': result, 'voice_geometry': geometry,
                      'surface_inventories': inventories, 'source_conditioned': True,
                      'training_eligible': False, 'production_enabled': False}
            path = out/(cid+'.json')
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
            tags = [p['pattern'] for p in result['pattern_candidates']]
            patterns.update(tags)
            for voice in geometry['voices']:
                abstentions.update(voice['abstention_reasons'])
            shifted = sum(bool(v['comparison'] and v['comparison']['nonzero_shifted_rhythm_and_spelled_shape'])
                          for v in geometry['voices'])
            records.append({'case_id': cid, 'score': folder.name, 'collection': e['collection_id'],
                            'symbols': symbols, 'inversions': inversions, 'patterns': tags,
                            'printed_measure_range': record['printed_measure_range'],
                            'shifted_rhythm_shape_voice_count': shifted,
                            'comparable_voice_count': sum(v['comparison'] is not None for v in geometry['voices']),
                            'any_complete_support_per_span': [any(c['supplied_shape_supported'] for c in inv['slices']) for inv in inventories],
                            'json_sha256': digest(path)})
            count += 1
        scores.append({'score': folder.name, 'case_count': count, 'package_hashes': hashes})
    summary = {'score_count': len(scores), 'case_count': len(records), 'pattern_candidate_counts': dict(patterns),
               'cases_without_harmonic_pattern': sum(not r['patterns'] for r in records),
               'cases_with_shifted_voice_geometry': sum(r['shifted_rhythm_shape_voice_count'] > 0 for r in records),
               'cases_with_both_features': sum(bool(r['patterns']) and r['shifted_rhythm_shape_voice_count'] > 0 for r in records),
               'voice_abstention_counts': dict(abstentions)}
    report = {'version': VERSION, 'summary': summary, 'records': records, 'scores': scores,
              'skipped': dict(skipped), 'contract_sha256': digest(out/'run-contract.json'),
              'blind_accuracy_measured': False, 'production_enabled': False}
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.manifest, args.output)['summary'], indent=2))
