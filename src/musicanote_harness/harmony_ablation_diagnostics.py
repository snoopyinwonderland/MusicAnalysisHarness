"""Explain context-edge sensitivity by rescoring a wider-context path in a smaller window.

Only the proposed path is clipped. Original notes, tie spans and full-score voice
neighbors are untouched. This is a diagnostic, never a production segmentation rule.
"""
import argparse
import copy
import json
from fractions import Fraction
from pathlib import Path
from .formal_ir import q
from .harmony_joint import f
from .harmony_ablation_review import ARMS, rescore_path
from .harmony_multiscale_review import digest
from .harmony_candidate_explanation import explain_candidate
from .harmony_review_cohort import validate_split


def clip_path(result, span, measures):
    a, b = f(span['start']), f(span['end'])
    if not f(result['analysis_span']['start']) <= a < b <= f(result['analysis_span']['end']):
        raise ValueError('diagnostic_window_must_be_contained')
    path = []
    for original in result['segments']:
        x, y = max(a, f(original['span']['start'])), min(b, f(original['span']['end']))
        if y <= x:
            continue
        s = copy.deepcopy(original)
        s['span'] = {'start': q(x), 'end': q(y)}
        measure = next((m for m in sorted(measures, key=lambda m: f(m['global_start_quarter']), reverse=True)
                        if f(m['global_start_quarter']) <= x), None)
        s['beat_unit_quarter'] = q(Fraction(4, measure['time_signature']['beat_type']) if measure else Fraction(1))
        path.append(s)
    return {'analysis_span': span, 'segments': path, 'diagnostic_only': True,
            'warning': 'selected candidate costs are stale until rescore_path; not a new engine result'}


def build(manifest, review_dir, ablation_dir, audit_dir, output):
    out, source, root, audit_root = Path(output), Path(review_dir), Path(ablation_dir), Path(audit_dir)
    if out.exists():
        raise ValueError('output_exists_choose_new_directory')
    entries = json.loads(Path(manifest).read_text(encoding='utf-8'))['entries']; validate_split(entries)
    packages = {e['package_path']: e for e in entries}
    queue = {r['case_id']: r for r in map(json.loads, (source/'plan/cases.jsonl').read_text(encoding='utf-8').splitlines())}
    report = json.loads((root/'report.json').read_text(encoding='utf-8'))
    audit = json.loads((audit_root/'report.json').read_text(encoding='utf-8'))
    cases = {c['case_id']: c for c in report['cases']}
    if any(r['manifest_sha256'] != digest(manifest) or r['queue_sha256'] != digest(source/'plan/cases.jsonl') for r in (report, audit)):
        raise ValueError('manifest_or_queue_changed')
    for c in audit['cases']:
        case = queue[c['case_id']]; entry = packages[case['package_path']]
        if case['split'] != 'train' or entry['split'] != 'train':
            raise ValueError('non_train_case')
        if not entry['rights'].get('internal_research_use'):
            raise ValueError('internal_research_not_allowed')
        for k in ('score_id', 'ir_document_id', 'score_sha256', 'annotation_sha256', 'rights'):
            if case[k] != entry[k]:
                raise ValueError('identity_mismatch:'+k)
    out.mkdir(parents=True)
    summaries = []
    for c in audit['cases']:
        cid = c['case_id']; case = queue[cid]; entry = packages[case['package_path']]
        input_path, ir_path = root/'results'/(cid+'.json'), Path(case['package_path'])/'canonical_music_ir.json'
        if digest(input_path) != cases[cid]['result_sha256'] or digest(ir_path) != cases[cid]['ir_sha256']:
            raise ValueError('diagnostic_input_changed')
        ir = json.loads(ir_path.read_text(encoding='utf-8'))
        if ir['ir_document_id'] != entry['ir_document_id'] or ir['score']['score_id'] != entry['score_id']:
            raise ValueError('ir_identity_mismatch')
        data = json.loads(input_path.read_text(encoding='utf-8'))
        if data['case_id'] != cid or data['target_span'] != case['target_span']:
            raise ValueError('case_changed')
        small, large = data['runs']
        transplanted = {}
        for arm, switches in ARMS.items():
            alternative = clip_path(large[arm], small['analysis_span'], ir['measures'])
            chosen = small['fixed_path_cost_matrix'][arm][arm]
            try:
                cost = rescore_path(ir, alternative, switches)
            except ValueError as exc:
                if str(exc) != 'fixed_path_candidate_not_proposed':
                    raise
                # Context clipping can remove the required >=2 shared pitch classes.
                # Do not bypass the proposer merely to obtain a comparable number.
                transplanted[arm] = {'clipped_wider_path': None, 'chosen_smaller_path': chosen,
                                     'alternative_minus_chosen': None,
                                     'status': 'clipped_candidate_not_proposed',
                                     'attempted_path': [{'span': s['span'], 'label': s['selected']['label']} for s in alternative['segments']]}
            else:
                transplanted[arm] = {'clipped_wider_path': cost, 'chosen_smaller_path': chosen,
                                     'alternative_minus_chosen': cost['total_cost']-chosen['total_cost'],
                                     'status': 'rescored'}
        # Explain only existing selected candidates, not source-labelled substitutes.
        selected_explanations = []
        for run in data['runs']:
            selected_explanations.append({'margin_quarters': run['margin_quarters'],
                'arms': {arm: [explain_candidate(ir, s['span'], s['selected'], f(s['beat_unit_quarter']))
                               for s in run[arm]['segments']] for arm in ARMS}})
        payload = {'case_id': cid, 'target_span': case['target_span'], 'ablation_sha256': digest(input_path),
                   'ir_sha256': digest(ir_path), 'transplanted_paths': transplanted,
                   'selected_path_explanations': selected_explanations,
                   'source_labels_used_for_inference': False, 'production_enabled': False,
                   'limits': ['Costs compare complete paths within the SAME smaller context and SAME objective',
                              'Top-five candidate gate and approximate path pruning still matter',
                              'No new boundaries or musical gold labels are created']}
        dest = out/(cid+'.json'); dest.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        summaries.append({'case_id': cid, 'result_sha256': digest(dest),
                          'alternative_minus_chosen': {arm: v['alternative_minus_chosen'] for arm, v in transplanted.items()}})
    final = {'version': 'harmony-ablation-diagnostics-0.1.0', 'cases': summaries,
             'ablation_report_sha256': digest(root/'report.json'), 'audit_report_sha256': digest(audit_root/'report.json'),
             'code_sha256': digest(__file__), 'production_enabled': False, 'accuracy_measured': False}
    (out/'report.json').write_text(json.dumps(final, indent=2), encoding='utf-8')
    print(json.dumps(final, indent=2))
    return final


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for flag in ('manifest', 'review-dir', 'ablation-dir', 'audit-dir', 'output'):
        p.add_argument('--'+flag, required=True)
    args = p.parse_args()
    build(args.manifest, args.review_dir, args.ablation_dir, args.audit_dir, args.output)
