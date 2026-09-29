"""Train-only Unit 13 textbook links, source-conditioned and not accuracy evaluation."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .predominant_seventh import assess, VERSION
from .predominant_sonata_audit import span_observation
from .tonal_foundations import spelled_seventh_shapes


def source_family(annotation):
    r = annotation['raw_fields']
    if any(r.get(k) for k in ('changes', 'added_tones', 'relativeroot', 'pedal', 'special')):
        return None
    if r.get('figbass') not in ('7', '65', '43', '2', '42'):
        return None
    # DCML uses M for major seventh; % for half-diminished. Keep raw label too.
    triple = (r.get('numeral'), r.get('form', ''), r.get('chord_type'))
    if triple in (('ii', '', 'mm7'), ('ii', '%', '%7')):
        return 'supertonic'
    if triple in (('IV', 'M', 'MM7'), ('iv', '', 'mm7')):
        return 'subdominant'
    return None


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
    modules = ['predominant_seventh.py', 'predominant_seventh_audit.py', 'tonal_foundations.py',
               'foundation_sonata_audit.py', 'cadential_six_four_audit.py', 'predominant_sonata_audit.py',
               'harmony_case_retrieval.py', 'harmony_review_cohort.py', 'harmony_review_supplement.py',
               'harmony_curriculum.py']
    out.mkdir(parents=True)
    contract = {'version': VERSION, 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
                'entries': selected, 'selection': 'all verified unmodified ii7/ii%7/IVM7/iv7 and inversions in train sonatas',
                'context': 'target measures plus one measure before and after; original sounding durations retained',
                'source_keys_and_ranges_supplied': True, 'source_labels_used_for_selection': True,
                'blind_accuracy_measured': False, 'production_enabled': False,
                'code_hashes': {n: digest(Path(__file__).with_name(n)) for n in modules}}
    (out/'run-contract.json').write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding='utf-8')
    summaries, scores = [], []
    skipped, families, entries_count, exits_count = Counter(), Counter(), Counter(), Counter()
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
            family = source_family(a)
            if family is None:
                continue
            tonic, alter, mode = source_key(a)
            span = a['target']['span']
            context = context_excerpt(ir, span)
            result = assess(ir, span, context['context_span'], family, tonic, alter, mode)
            inventory = span_observation(ir, span)
            for s in inventory['slices']:
                s['complete_seventh_shapes'] = spelled_seventh_shapes([e['pitch'] for e in s['events']])
            cid = 'u13_' + hashlib.sha256((ir['ir_document_id']+'|'+a['annotation_id']).encode()).hexdigest()[:16]
            record = {'case_id': cid, 'concept_id': 'hvl.unit13', 'identity': e, 'package_hashes': hashes,
                      'target_annotation_id': a['annotation_id'], 'target_span': span,
                      'source_label': a['raw_label'], 'printed_measure': a['raw_fields'].get('mn'),
                      'source_context': annotations[max(0, i-1):i+3], 'context_excerpt': context,
                      'surface_inventory': inventory, 'evidence': result, 'source_conditioned': True,
                      'training_eligible': False, 'production_enabled': False}
            path = out/(cid+'.json')
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
            ec = Counter(r['entry']['status'] for r in result['records'])
            xc = Counter(r['departure']['status'] for r in result['records'])
            summaries.append({'case_id': cid, 'score': folder.name, 'collection': e['collection_id'],
                              'source_label': a['raw_label'], 'printed_measure': record['printed_measure'],
                              'family': family, 'conditional_seventh_events': len(result['records']),
                              'entry_statuses': dict(ec), 'departure_statuses': dict(xc),
                              'json_sha256': digest(path)})
            families[family] += 1
            entries_count.update(ec)
            exits_count.update(xc)
            count += 1
        scores.append({'score': folder.name, 'case_count': count, 'package_hashes': hashes})
    report = {'version': VERSION, 'summary': {'score_count': len(scores), 'case_count': len(summaries),
              'by_family': dict(families), 'entry_statuses': dict(entries_count),
              'departure_statuses': dict(exits_count),
              'cases_without_observed_conditional_seventh': sum(r['conditional_seventh_events'] == 0 for r in summaries)},
              'records': summaries, 'scores': scores, 'skipped': dict(skipped),
              'contract_sha256': digest(out/'run-contract.json'), 'blind_accuracy_measured': False,
              'production_enabled': False}
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.manifest, args.output)['summary'], indent=2))
