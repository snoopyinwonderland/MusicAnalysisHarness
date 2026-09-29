"""Unit 16 train-only source-conditioned sonata cases, not a blind evaluation."""
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
from .mediant_evidence import observe, VERSION


def anchor_kind(a):
    r = a['raw_fields']
    if any(r.get(k) for k in ('changes', 'added_tones', 'pedal', 'special')):
        return None
    minor = r.get('localkey_is_minor')
    if minor not in ('0', '1'):
        return None
    n, f, fig, ct, rel = (r.get(k, '') for k in ('numeral', 'form', 'figbass', 'chord_type', 'relativeroot'))
    if rel:
        if rel != ('III' if minor == '1' else 'iii'):
            return None
        if n == 'V' and not f and ((fig in ('', '6') and ct == 'M') or
                                  (fig in ('7', '65', '43', '2', '42') and ct == 'Mm7')):
            return 'applied_dominant_to_mediant'
        return None
    if fig not in ('', '6', '64'):
        return None
    if (n, f, ct) == (('III', '', 'M') if minor == '1' else ('iii', '', 'm')):
        return 'source_mediant_triad'
    if minor == '1' and (n, f, ct) == ('VII', '', 'M'):
        return 'source_natural_VII'
    if (n, f, ct) == (('#vii', 'o', 'o') if minor == '1' else ('vii', 'o', 'o')):
        return 'source_leading_tone_triad'
    # bVII in a minor-key DCML row is NOT silently treated as natural VII.
    return None


def mediant_regions(annotations):
    groups = []
    for i, a in enumerate(annotations):
        r = a['raw_fields']
        home = r.get('globalkey', '')
        if not (home[:1].islower() and r.get('localkey') == 'III' and r.get('localkey_is_minor') == '0'):
            continue
        if (groups and groups[-1][-1] == i-1 and annotations[i-1]['raw_fields']['globalkey'] == home and
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
    modules = ['mediant_evidence.py', 'mediant_audit.py', 'dominant_area_evidence.py', 'tonal_foundations.py',
               'predominant_sonata_audit.py', 'foundation_sonata_audit.py', 'cadential_six_four_audit.py',
               'harmony_case_retrieval.py', 'harmony_review_cohort.py', 'harmony_review_supplement.py', 'harmony_curriculum.py']
    contract = {'version': VERSION, 'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'entries': selected,
                'selection': 'train Mozart/Beethoven sonatas; plain local III/iii, natural VII, leading-tone triads, V/III or V/iii; contiguous source III runs in global minor',
                'reference_policy': 'single anchor: source local key; III area: source global minor key',
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
        cases = [(anchor_kind(a), [i]) for i, a in enumerate(annotations) if anchor_kind(a)]
        cases += [('source_relative_major_area', g) for g in mediant_regions(annotations)]
        for kind, indices in cases:
            first, last = indices[0], indices[-1]
            a = annotations[first]
            if kind == 'source_relative_major_area':
                token = a['raw_fields']['globalkey']
                key = m21key.Key(token[:1]+token[1:].replace('b', '-'))
                tonic, alter, mode = key.tonic.step, int(key.tonic.accidental.alter) if key.tonic.accidental else 0, 'minor'
            else:
                tonic, alter, mode = source_key(a)
            span = {'start': a['target']['span']['start'], 'end': annotations[last]['target']['span']['end']}
            context = context_excerpt(ir, span)
            target_ev = observe(ir, span, tonic, alter, mode)
            context_ev = observe(ir, context['context_span'], tonic, alter, mode)
            cid = 'u16_'+hashlib.sha256((ir['ir_document_id']+'|'+kind+'|'+a['annotation_id']).encode()).hexdigest()[:16]
            record = {'case_id': cid, 'concept_id': 'hvl.unit16', 'kind': kind,
                      'identity': e, 'package_hashes': hashes, 'target_span': span,
                      'target_annotation_ids': [annotations[i]['annotation_id'] for i in indices],
                      'target_source_labels': [annotations[i]['raw_label'] for i in indices],
                      'printed_measure_range': [a['raw_fields'].get('mn'), annotations[last]['raw_fields'].get('mn')],
                      'source_context': annotations[max(0, first-2):last+3],
                      'context_excerpt': context, 'target_evidence': target_ev, 'context_evidence': context_ev,
                      'source_conditioned': True, 'training_eligible': False, 'production_enabled': False}
            path = out/(cid+'.json')
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
            readings = sorted({v for s in target_ev['slices'] for sh in s['complete_shapes'] for v in sh['compatible_readings']})
            records.append({'case_id': cid, 'score': folder.name, 'collection': e['collection_id'],
                            'kind': kind, 'printed_measure_range': record['printed_measure_range'],
                            'target_source_labels': record['target_source_labels'], 'annotation_count': len(indices),
                            'compatible_shape_readings': readings, 'json_sha256': digest(path)})
            kinds[kind] += 1
        scores.append({'score': folder.name, 'case_count': len(cases), 'package_hashes': hashes})
    report = {'version': VERSION, 'summary': {'score_count': len(scores), 'case_count': len(records),
              'by_kind': dict(kinds), 'cases_with_relevant_complete_shape': sum(bool(r['compatible_shape_readings']) for r in records)},
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
