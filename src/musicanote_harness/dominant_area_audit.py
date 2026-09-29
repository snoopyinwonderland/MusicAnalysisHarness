"""Unit 15 source-conditioned applied-to-V and annotated V-area case collection."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from music21 import key as m21key
from .cadential_six_four_audit import digest, source_key
from .harmony_case_retrieval import _f, load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .dominant_area_evidence import observe, VERSION


def applied_anchor(a):
    r = a['raw_fields']
    if r.get('localkey_is_minor') != '0' or r.get('relativeroot') != 'V':
        return False
    if any(r.get(k) for k in ('changes', 'added_tones', 'pedal', 'special')):
        return False
    n, form, fig, ct = (r.get(k, '') for k in ('numeral', 'form', 'figbass', 'chord_type'))
    return ((n == 'V' and not form and ((fig in ('', '6') and ct == 'M') or
             (fig in ('7', '65', '43', '2', '42') and ct == 'Mm7'))) or
            (n == 'vii' and form == 'o' and fig == '6' and ct == 'o'))


def dominant_regions(annotations):
    """Source labels define runs, NOT musically proven modulation boundaries."""
    groups = []
    for i, a in enumerate(annotations):
        r = a['raw_fields']
        g = r.get('globalkey', '')
        eligible = bool(g and g[0].isupper() and r.get('localkey') == 'V' and r.get('localkey_is_minor') == '0')
        if not eligible:
            continue
        if (groups and groups[-1][-1] == i-1 and
            annotations[i-1]['raw_fields']['globalkey'] == g and
            _f(annotations[i-1]['target']['span']['end']) == _f(a['target']['span']['start'])):
            groups[-1].append(i)
        else:
            groups.append([i])
    return groups


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
    modules = ['dominant_area_evidence.py', 'dominant_area_audit.py', 'tonal_foundations.py',
               'predominant_sonata_audit.py', 'foundation_sonata_audit.py', 'cadential_six_four_audit.py',
               'harmony_case_retrieval.py', 'harmony_review_cohort.py', 'harmony_review_supplement.py',
               'harmony_curriculum.py']
    contract = {'version': VERSION, 'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'entries': selected,
                'selection': 'train sonatas: Unit15 applied V/V and viio6/V in source local major; contiguous source V areas in global major',
                'reference_policy': 'applied case home=source local key; area case home=source global key',
                'boundaries': 'source annotation boundaries, not inferred tonal boundaries',
                'source_conditioned': True, 'blind_accuracy_measured': False, 'production_enabled': False,
                'code_hashes': {n: digest(Path(__file__).with_name(n)) for n in modules}}
    (out/'run-contract.json').write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding='utf-8')
    records, scores = [], []
    skipped, kinds = Counter(), Counter()
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
        cases = [('applied_to_local_V', [i]) for i, a in enumerate(annotations) if applied_anchor(a)]
        cases += [('source_dominant_area', g) for g in dominant_regions(annotations)]
        for kind, indices in cases:
            first, last = indices[0], indices[-1]
            a = annotations[first]
            if kind == 'applied_to_local_V':
                tonic, alter, _ = source_key(a)
            else:
                token = a['raw_fields']['globalkey']
                key = m21key.Key(token[:1]+token[1:].replace('b', '-'))
                tonic = key.tonic.step
                alter = int(key.tonic.accidental.alter) if key.tonic.accidental else 0
            span = {'start': a['target']['span']['start'], 'end': annotations[last]['target']['span']['end']}
            context = context_excerpt(ir, span)
            target_ev = observe(ir, span, tonic, alter)
            context_ev = observe(ir, context['context_span'], tonic, alter)
            cid = 'u15_'+hashlib.sha256((ir['ir_document_id']+'|'+kind+'|'+a['annotation_id']).encode()).hexdigest()[:16]
            record = {'case_id': cid, 'concept_id': 'hvl.unit15', 'kind': kind,
                      'identity': e, 'package_hashes': hashes, 'target_span': span,
                      'target_annotation_ids': [annotations[i]['annotation_id'] for i in indices],
                      'target_source_labels': [annotations[i]['raw_label'] for i in indices],
                      'printed_measure_range': [a['raw_fields'].get('mn'), annotations[last]['raw_fields'].get('mn')],
                      'source_context': annotations[max(0, first-2):last+3],
                      'context_excerpt': context, 'target_evidence': target_ev, 'context_evidence': context_ev,
                      'source_conditioned': True, 'training_eligible': False, 'production_enabled': False}
            path = out/(cid+'.json')
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
            records.append({'case_id': cid, 'score': folder.name, 'collection': e['collection_id'],
                            'kind': kind, 'printed_measure_range': record['printed_measure_range'],
                            'target_source_labels': record['target_source_labels'],
                            'annotation_count': len(indices),
                            'target_raised_fourth_count': len(target_ev['raised_fourth_event_refs']),
                            'context_shared_triad_slice_count': len(context_ev['shared_diatonic_triad_slices']),
                            'json_sha256': digest(path)})
            kinds[kind] += 1
        scores.append({'score': folder.name, 'case_count': len(cases), 'package_hashes': hashes})
    report = {'version': VERSION, 'summary': {'score_count': len(scores), 'case_count': len(records),
              'by_kind': dict(kinds), 'cases_with_target_raised_fourth': sum(r['target_raised_fourth_count'] > 0 for r in records),
              'cases_with_context_shared_triad_shape': sum(r['context_shared_triad_slice_count'] > 0 for r in records)},
              'records': records, 'scores': scores, 'skipped': dict(skipped),
              'contract_sha256': digest(out/'run-contract.json'), 'blind_accuracy_measured': False, 'production_enabled': False}
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.manifest, args.output)['summary'], indent=2))
