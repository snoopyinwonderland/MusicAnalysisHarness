"""Recheck all fixed Unit21 pairs for literal retention, including nonmatches."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .melodic_figuration import _members
from .rhythmic_figuration import VERSION, observe, condition_on_members
from .six_four_context import source_triad, triad
from .dominant_area_evidence import _exact


def build(source, output, expanded=False):
    src, out = Path(source), Path(output)
    if out.exists(): raise ValueError('output_exists')
    report = json.loads((src/'report.json').read_text(encoding='utf-8'))
    contract = json.loads((src/'run-contract.json').read_text(encoding='utf-8'))
    if digest(src/'run-contract.json') != report['contract_sha256']: raise ValueError('source_contract_hash_mismatch')
    entries = contract['entries']; validate_split(entries)
    if any(e['split'] != 'train' or e['rights'].get('internal_research_use') is not True for e in entries):
        raise ValueError('train_research_entries_required')
    if len({e['ir_document_id'] for e in entries}) != len(entries): raise ValueError('duplicate_ir_identity')
    entry_map = {e['ir_document_id']: e for e in entries}; cache = {}; cases = []; seen = set()
    for row in report['records']:
        path = src/(row['case_id']+'.json')
        if digest(path) != row['json_sha256']: raise ValueError('source_case_hash_mismatch')
        case = json.loads(path.read_text(encoding='utf-8')); e = case['identity']
        if entry_map.get(e['ir_document_id']) != e: raise ValueError('source_entry_mismatch')
        if e['ir_document_id'] not in cache:
            folder = Path(e['package_path'])
            if digest(e['score_source_path']) != e['score_sha256']: raise ValueError('score_hash_mismatch')
            for name, value in case['package_hashes'].items():
                if digest(folder/name) != value: raise ValueError('package_hash_mismatch')
            package = load_prepared_package(folder); ir = package['ir']
            if ir['ir_document_id'] != e['ir_document_id'] or ir['score']['score_id'] != e['score_id']:
                raise ValueError('ir_identity_mismatch')
            valid, _ = verified_annotations(package, e)
            cache[e['ir_document_id']] = (package, {a['annotation_id'] for a in valid}, case['package_hashes'])
        package, valid_ids, hashes = cache[e['ir_document_id']]
        if hashes != case['package_hashes']: raise ValueError('inconsistent_package_hashes')
        ids = case['target_annotation_ids']; key = (e['ir_document_id'], *ids)
        if len(ids) != 2 or any(i not in valid_ids for i in ids): raise ValueError('unverified_source_pair')
        sequence = [a['annotation_id'] for a in package['annotations']]; index = sequence.index(ids[0])
        if sequence[index:index+2] != ids: raise ValueError('nonadjacent_source_pair')
        if key in seen: raise ValueError('duplicate_pair')
        seen.add(key)
        group = package['annotations'][index:index+2]
        if group != case['source_annotations']: raise ValueError('source_annotation_mismatch')
        cases.append((key, case, group))
    # The fixed parent sample is enriched for 6/4 techniques, not for Unit22.
    # A separate run can inspect ALL supported adjacent pairs of the same train
    # cohort. No selecting on the observed outcome, and no label-gap bridging.
    excluded_pairs = Counter()
    if expanded:
        cases = []
        for e in entries:
            if e['ir_document_id'] not in cache:
                folder = Path(e['package_path'])
                if digest(e['score_source_path']) != e['score_sha256']: raise ValueError('score_hash_mismatch')
                package = load_prepared_package(folder); ir = package['ir']
                if ir['ir_document_id'] != e['ir_document_id'] or ir['score']['score_id'] != e['score_id']:
                    raise ValueError('ir_identity_mismatch')
                valid, _ = verified_annotations(package, e)
                hashes = {n: digest(folder/n) for n in ('canonical_music_ir.json', 'imported_annotations.jsonl', 'alignment_records.jsonl')}
                cache[e['ir_document_id']] = (package, {a['annotation_id'] for a in valid}, hashes)
            package, valid_ids, hashes = cache[e['ir_document_id']]
            anns = package['annotations']
            for left, right in zip(anns, anns[1:]):
                group = [left, right]; ids = [a['annotation_id'] for a in group]
                if any(i not in valid_ids for i in ids):
                    excluded_pairs['unverified_alignment'] += 1; continue
                items = [source_triad(a) for a in group]
                if not all(items):
                    excluded_pairs['unsupported_source_chord'] += 1; continue
                keys = [source_key(a) for a in group]
                if keys[0] != keys[1]:
                    excluded_pairs['different_supplied_keys'] += 1; continue
                spans = [a['target']['span'] for a in group]
                if not (0 <= _exact(spans[0]['start']) < _exact(spans[0]['end']) ==
                        _exact(spans[1]['start']) < _exact(spans[1]['end'])):
                    excluded_pairs['nonpositive_or_nontouching_spans'] += 1; continue
                parent = {'case_id': None, 'identity': e, 'package_hashes': hashes,
                          'target_span': {'start': spans[0]['start'], 'end': spans[1]['end']},
                          'conditional_harmony_links': {'supplied_chords': [triad(*item, *keys[0]) for item in items]}}
                cases.append(((e['ir_document_id'], *ids), parent, group))
    out.mkdir(parents=True)
    names = ['rhythmic_figuration.py', 'rhythmic_figuration_audit.py', 'melodic_figuration.py',
             'dominant_area_evidence.py', 'foundation_sonata_audit.py', 'formal_ir.py',
             'tonal_foundations.py', 'harmony_case_retrieval.py', 'harmony_review_cohort.py',
             'harmony_review_supplement.py', 'cadential_six_four_audit.py', 'harmony_curriculum.py',
             'six_four_context.py', 'root_position_context.py']
    run = {'version': VERSION, 'entries': entries, 'parent_directory': str(src.resolve()),
           'parent_report_sha256': digest(src/'report.json'), 'parent_contract_sha256': report['contract_sha256'],
           'selection': ('all supported verified adjacent touching same-key triad pairs in parent train cohort' if expanded else
                         'all fixed Unit21 adjacent pairs including nonmatches; source-supplied plain triads only'),
           'expanded_train_pairs': expanded,
           'source_conditioned': True, 'blind_accuracy_measured': False, 'production_enabled': False,
           'code_hashes': {n: digest(Path(__file__).with_name(n)) for n in names}}
    (out/'run-contract.json').write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding='utf-8')
    records = []; modes = Counter(); tags = Counter(); status = Counter()
    for key, parent, group in cases:
        ir = cache[key[0]][0]['ir']; spans = [a['target']['span'] for a in group]
        observation = observe(ir, *spans)
        chords = parent['conditional_harmony_links']['supplied_chords']
        members = [[list(p) for p in _members(c)] for c in chords]
        conditional = condition_on_members(observation, *members)
        cid = 'u22_'+hashlib.sha256('|'.join(key).encode()).hexdigest()[:16]
        record = {'case_id': cid, 'concept_id': 'hvl.unit22', 'identity': parent['identity'],
                  'package_hashes': parent['package_hashes'], 'parent_case_id': parent['case_id'],
                  'target_annotation_ids': list(key[1:]), 'source_annotations': group,
                  'context_excerpt': context_excerpt(ir, parent['target_span']),
                  'target_span': parent['target_span'], 'observation': observation,
                  'conditional_membership': conditional, 'source_conditioned': True,
                  'training_eligible': False, 'production_enabled': False}
        path = out/(cid+'.json'); path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        modes.update(r['boundary_mode'] for r in observation['retentions'])
        status.update(r['departure_status'] for r in observation['retentions'])
        case_tags = [t for r in conditional['records'] for t in r['compatibility_tags']]; tags.update(case_tags)
        records.append({'case_id': cid, 'parent_case_id': parent['case_id'],
                        'score': Path(parent['identity']['package_path']).name,
                        'printed_measures': [a['raw_fields'].get('mn') for a in group],
                        'source_labels': [a['raw_label'] for a in group],
                        'retention_count': len(observation['retentions']),
                        'compatibility_tags': case_tags, 'json_sha256': digest(path)})
    summary = {'score_count': len(cache), 'pair_count': len(records),
               'pairs_with_retention': sum(r['retention_count'] > 0 for r in records),
               'retention_count': sum(r['retention_count'] for r in records),
               'boundary_mode_counts': dict(modes), 'departure_status_counts': dict(status),
               'compatibility_tag_counts': dict(tags)}
    result = {'version': VERSION, 'summary': summary, 'records': records, 'excluded_pair_counts': dict(excluded_pairs),
              'contract_sha256': digest(out/'run-contract.json'), 'blind_accuracy_measured': False,
              'production_enabled': False}
    (out/'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--source', required=True); p.add_argument('--output', required=True)
    p.add_argument('--expanded', action='store_true')
    args = p.parse_args(); print(json.dumps(build(args.source, args.output, args.expanded)['summary'], indent=2))
