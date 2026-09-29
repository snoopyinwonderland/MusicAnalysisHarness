"""Run the fixed 30-case train cohort against saved temporal v0.3 outputs."""
import argparse
import hashlib
import json
from pathlib import Path
from .harmony_multiscale_shadow import analyze, VERSION, POLICY
from .harmony_context_sensitivity import compare_target, context_stable, stability_components
from .harmony_review_cohort import validate_split


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(manifest, review_dir, output):
    out, source = Path(output), Path(review_dir)
    if out.exists():
        raise ValueError('output_exists_choose_new_directory')
    entries = json.loads(Path(manifest).read_text(encoding='utf-8'))['entries']
    validate_split(entries)
    packages = {e['package_path']: e for e in entries}
    plan = json.loads((source/'plan/report.json').read_text(encoding='utf-8'))
    if plan['manifest_sha256'] != digest(manifest):
        raise ValueError('manifest_changed')
    queue = {r['case_id']: r for r in map(json.loads, (source/'plan/cases.jsonl').read_text(encoding='utf-8').splitlines())}
    # Validate all metadata before reading any reserved score contents.
    for item in plan['plan']:
        case = queue[item['case_id']]; entry = packages[case['package_path']]
        if any(r['split'] != 'train' for r in (item, case, entry)):
            raise ValueError('non_train_case')
        if item['target_span'] != case['target_span'] or item['collection'] != entry['collection_id']:
            raise ValueError('target_or_collection_changed')
        for k in ('score_id', 'ir_document_id', 'work_family_id', 'score_sha256', 'annotation_sha256', 'rights'):
            if case[k] != entry[k]:
                raise ValueError('identity_mismatch:'+k)
        if not entry['rights'].get('internal_research_use'):
            raise ValueError('internal_research_not_allowed')
    out.mkdir(parents=True)
    (out/'results').mkdir()
    code_paths = ['harmony_multiscale_shadow.py', 'harmony_multiscale_review.py', 'harmony_joint.py', 'harmony_surface.py']
    report = {'version': VERSION, 'policy': POLICY, 'manifest_sha256': digest(manifest),
              'plan_sha256': digest(source/'plan/report.json'), 'queue_sha256': digest(source/'plan/cases.jsonl'),
              'code_sha256': {p: digest(Path(__file__).with_name(p)) for p in code_paths},
              'cases': [], 'accuracy_measured': False, 'production_enabled': False,
              'reserved_contents_read': False, 'source_labels_used_for_inference': False}
    # Persist frozen parameters and hashes BEFORE the first experiment result.
    (out/'run-contract.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    for item in plan['plan']:
        case_id = item['case_id']; case = queue[case_id]; entry = packages[case['package_path']]
        ir_path = Path(case['package_path'])/'canonical_music_ir.json'
        if digest(ir_path) != item['ir_sha256'] or digest(entry['score_source_path']) != entry['score_sha256']:
            raise ValueError('source_changed')
        ir = json.loads(ir_path.read_text(encoding='utf-8'))
        if ir['score']['score_id'] != entry['score_id'] or ir['ir_document_id'] != entry['ir_document_id']:
            raise ValueError('ir_identity_mismatch')
        old_path = source/'results'/(case_id+'.json')
        old = json.loads(old_path.read_text(encoding='utf-8'))
        if old['case_id'] != case_id or old['target_span'] != case['target_span'] or len(old['runs']) != 2:
            raise ValueError('saved_result_identity_or_run_count')
        runs = []
        for prior in old['runs']:
            baseline = prior['experiment']
            if baseline['engine_version'] != 'temporal-support-shadow-0.3.0':
                raise ValueError('unexpected_previous_engine')
            experiment = analyze(ir, analysis_span=prior['analysis_span'])
            runs.append({'margin_quarters': prior['margin_quarters'], 'analysis_span': prior['analysis_span'],
                         'baseline': baseline, 'experiment': experiment,
                         'paired_target_delta': compare_target(baseline, experiment, case['target_span'])})
        summary = {'case_id': case_id, 'target_span': case['target_span'], 'collection': item['collection'],
                   'previous_result_sha256': digest(old_path), 'ir_sha256': item['ir_sha256'],
                   'context_stable': {k: context_stable(runs, k, case['target_span'], 2) for k in ('baseline', 'experiment')},
                   'stability_components': {k: stability_components(runs, k, case['target_span'], 2) for k in ('baseline', 'experiment')},
                   'deltas': [r['paired_target_delta'] for r in runs]}
        payload = {**summary, 'runs': runs, 'track_names': {'baseline': '이전 실험 · temporal v0.3', 'experiment': '이번 개선 후보 · multiscale v0.1'},
                   'source_labels_used_for_inference': False, 'production_enabled': False}
        path = out/'results'/(case_id+'.json')
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        report['cases'].append({**summary, 'result_sha256': digest(path)})
        print(json.dumps({'completed': len(report['cases']), 'case_id': case_id,
                          'context_stable': summary['context_stable'],
                          'labels_changed': any(not d['same_labels_at_all_target_times'] for d in summary['deltas'])}), flush=True)
    report['summary'] = {
        'case_count': len(report['cases']),
        'context_stable_counts': {k: sum(c['context_stable'][k] is True for c in report['cases']) for k in ('baseline', 'experiment')},
        'cases_with_label_changes': sum(any(not d['same_labels_at_all_target_times'] for d in c['deltas']) for c in report['cases']),
        'stability_gained': [c['case_id'] for c in report['cases'] if c['context_stable'] == {'baseline': False, 'experiment': True}],
        'stability_lost': [c['case_id'] for c in report['cases'] if c['context_stable'] == {'baseline': True, 'experiment': False}],
    }
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for flag in ('manifest', 'review-dir', 'output'):
        parser.add_argument('--'+flag, required=True)
    args = parser.parse_args()
    build(args.manifest, args.review_dir, args.output)
