"""Unit33 source-conditioned alternatives and independent literal transitions."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .chromatic_voice_leading_audit import context_annotations
from .applied_chords import source_harmony
from .augmented_sixth import source_reference
from .dominant_area_evidence import _exact
from .diatonic_modulation import key_relation, source_key_transitions, observe_support
from .chromatic_tonal_context import (VERSION, reinterpretations, compare_following,
                                     observe_transition, common_tone_support)


def build(manifest_path, output):
    out = Path(output)
    if out.exists():
        raise ValueError('output_exists')
    raw = Path(manifest_path).read_bytes()
    entries = json.loads(raw)['entries']
    validate_split(entries)
    entries = [e for e in entries if e['split'] == 'train' and e['collection_id'] in ('mozart-sonatas', 'beethoven-sonatas')]
    if len({e['package_path'] for e in entries}) != len(entries):
        raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in entries):
        raise ValueError('research_not_permitted')
    names = ['chromatic_tonal_context.py', 'chromatic_tonal_context_audit.py', 'chromatic_voice_leading.py',
             'chromatic_voice_leading_audit.py', 'augmented_sixth.py', 'diatonic_modulation.py',
             'applied_chords.py', 'seventh_context.py', 'cadential_six_four_audit.py',
             'harmony_case_retrieval.py', 'harmony_review_cohort.py', 'harmony_review_supplement.py',
             'foundation_sonata_audit.py', 'predominant_sonata_audit.py', 'dominant_area_evidence.py',
             'formal_ir.py', 'tonal_foundations.py', 'harmony_curriculum.py']
    out.mkdir(parents=True)
    contract = {'version': VERSION, 'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'entries': entries,
                'selection': 'all source o7/Mm7/Ger records plus preceding record of every verified adjacent source key change',
                'context': 'immediate successor only; unsupported/unverified/missing/gapped context never skipped; one measure margin',
                'source_conditioned': True, 'production_enabled': False, 'training_eligible': False,
                'code_hashes': {n: digest(Path(__file__).with_name(n)) for n in names}}
    (out / 'run-contract.json').write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding='utf-8')
    records, scores, excluded = [], [], Counter()
    for e in entries:
        folder = Path(e['package_path'])
        if digest(e['score_source_path']) != e['score_sha256']:
            raise ValueError('score_hash_mismatch')
        hashes = {n: digest(folder / n) for n in ('canonical_music_ir.json', 'imported_annotations.jsonl', 'alignment_records.jsonl')}
        p = load_prepared_package(folder)
        ir, anns = p['ir'], p['annotations']
        if ir['ir_document_id'] != e['ir_document_id'] or ir['score']['score_id'] != e['score_id']:
            raise ValueError('ir_identity_mismatch')
        valid, skips = verified_annotations(p, e)
        excluded.update(skips)
        ids = {a['annotation_id'] for a in valid}
        rows = []
        for a in anns:
            ok = a['annotation_id'] in ids
            key, h = None, None
            if ok:
                try:
                    key = source_key(a)
                except ValueError:
                    excluded['unsupported_source_key'] += 1
                if key:
                    h = source_reference(a, key) or source_harmony(a, *key)
            rows.append({'ref': a['annotation_id'], 'span': (a.get('target') or {}).get('span'),
                         'verified': ok, 'key': key, 'hypothesis': h})
        transitions = {tr['start_index'] - 1: tr for tr in source_key_transitions(rows)}
        for i, (a, row) in enumerate(zip(anns, rows)):
            raw_type = a['raw_fields'].get('chord_type')
            if raw_type not in ('o7', 'Mm7', 'Ger') and i not in transitions:
                continue
            nxt = rows[i + 1] if i + 1 < len(rows) else None
            status = 'observed'
            if not row['verified']: status = 'current_unverified'
            elif nxt is None: status = 'next_absent'
            elif not nxt['verified']: status = 'next_unverified'
            elif _exact(row['span']['end']) != _exact(nxt['span']['start']): status = 'nonadjacent'
            ev = observe_transition(ir, row['span'], nxt['span']) if status == 'observed' else None
            h = row['hypothesis']
            nh = nxt['hypothesis'] if status == 'observed' else None
            alternatives = reinterpretations(h)
            target = ({'start': row['span']['start'], 'end': nxt['span']['end']} if ev
                      else row['span'] if row['verified'] else None)
            ctx = context_excerpt(ir, target) if target else None
            # Generic vertical support uses tertian chords only. Aug6 literal
            # support remains in Unit30; do not coerce it into a root chord.
            support = observe_support(ir, row['span'], h) if row['verified'] and h and not h.get('family') else None
            cid = 'u33_' + hashlib.sha256((ir['ir_document_id'] + '|' + row['ref']).encode()).hexdigest()[:16]
            case = {'case_id': cid, 'concept_id': 'hvl.unit33', 'identity': e, 'package_hashes': hashes,
                    'status': status, 'current': row, 'next': nxt, 'source_annotation': a,
                    'source_key_run': transitions.get(i),
                    'key_relation': key_relation(row['key'], nxt['key']) if ev and row['key'] and nxt['key'] else None,
                    'alternatives': alternatives, 'following_shape_comparisons': compare_following(alternatives, nh),
                    'literal_transition': ev, 'current_literal_support': support,
                    'common_tone_comparison': common_tone_support(ev, h, nh) if ev else None,
                    'context_excerpt': ctx,
                    'source_context': context_annotations(anns, ids, ctx['context_span']) if ctx else [],
                    'source_conditioned': True, 'production_enabled': False, 'training_eligible': False}
            path = out / (cid + '.json')
            path.write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding='utf-8')
            records.append({'case_id': cid, 'score': folder.name, 'measure': a['raw_fields'].get('mn'),
                            'label': a['raw_label'], 'raw_type': raw_type, 'status': status,
                            'source_key_change': i in transitions, 'alternative_count': len(alternatives),
                            'literal_tags': dict(Counter(tag for link in ev['direct_voice_links'] for tag in link['tags'])) if ev else {},
                            'held_common_count': len(case['common_tone_comparison']['held_common_event_ids']) if case['common_tone_comparison'] else 0,
                            'json_sha256': digest(path)})
        scores.append({'score': folder.name, 'identity': e, 'package_hashes': hashes})
    tags = Counter()
    for r in records: tags.update(r['literal_tags'])
    summary = {'score_count': len(scores), 'case_count': len(records),
               'status_counts': dict(Counter(r['status'] for r in records)),
               'source_types': dict(Counter(r['raw_type'] for r in records)),
               'source_key_change_cases': sum(r['source_key_change'] for r in records),
               'with_template_alternatives': sum(r['alternative_count'] > 0 for r in records),
               'literal_tags': dict(tags), 'with_held_common_events': sum(r['held_common_count'] > 0 for r in records)}
    report = {'version': VERSION, 'summary': summary, 'records': records, 'scores': scores,
              'excluded_annotations': dict(excluded), 'contract_sha256': digest(out / 'run-contract.json'),
              'blind_modulation_accuracy_measured': False, 'production_enabled': False, 'training_eligible': False}
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.manifest, args.output)['summary'], indent=2))
