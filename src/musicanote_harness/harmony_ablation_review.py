"""Fixed-cohort 2x2 ablation; replay checks and same-objective path diagnostics.

No annotation labels are read by the scoring functions. The pre-existing train
cohort is annotation-selected, so this is development diagnosis, not accuracy.
"""
import argparse
import json
from pathlib import Path
from .harmony_joint import f, prepare
from .harmony_multiscale_shadow import analyze, provider, VERSION, POLICY
from .harmony_multiscale_review import digest
from .harmony_context_sensitivity import compare_target, context_stable, stability_components
from .harmony_cost_diagnostic import transition
from .harmony_review_cohort import validate_split

ARMS = {
    'none': {'enable_distributed': False, 'enable_missing_fifth': False},
    'fifth_only': {'enable_distributed': False, 'enable_missing_fifth': True},
    'distributed_only': {'enable_distributed': True, 'enable_missing_fifth': False},
    'both': {'enable_distributed': True, 'enable_missing_fifth': True},
}
NAMES = {'none': '보완 없음 · 이전 temporal 재현', 'fifth_only': '5음 생략만',
         'distributed_only': '분산 누적만', 'both': '둘 다 · 직전 개선 후보 재현'}


def replay_matches(left, right):
    """Same partition, labels and costs, ignoring new metadata/evidence formatting."""
    if left.get('analysis_span') != right.get('analysis_span') or len(left['segments']) != len(right['segments']):
        return False
    if abs(left['path_cost']-right['path_cost']) > 1e-9:
        return False
    for a, b in zip(left['segments'], right['segments']):
        if (a['span'] != b['span'] or a['selected']['label'] != b['selected']['label'] or
                abs(a['selected']['cost']-b['selected']['cost']) > 1e-9):
            return False
    return True


def rescore_path(ir, result, switches):
    """Hold the entire saved path fixed; only switch evidence. No new search.

    Segment/transition costs are exactly those in analyze_joint. Report candidate
    ranks: a path evaluated here may have been excluded by the top-5 search gate.
    """
    rows, neighbors = prepare(ir)
    a, b = f(result['analysis_span']['start']), f(result['analysis_span']['end'])
    rows = [r for r in rows if r['start'] < b and r['end'] > a]
    choose = provider(ir.get('measures', []), **switches)
    previous = None
    segments = []
    for s in result['segments']:
        start, end, beat = f(s['span']['start']), f(s['span']['end']), f(s['beat_unit_quarter'])
        choices = choose(rows, neighbors, start, end, beat, limit=None)
        matching = [(rank, c) for rank, c in enumerate(choices, 1) if c['label'] == s['selected']['label']]
        if not matching:
            raise ValueError('fixed_path_candidate_not_proposed')
        rank, c = matching[0]
        duration = float((end-start)/beat)
        change, resolution = transition(previous, c)
        evidence_costs = {'legacy_complete_cell': 0., 'supplemental_base_cell': 0.,
                          'supplemental_distributed_window': 0.}
        for e in c['temporal_evidence']:
            evidence_costs[e['reason']] += duration*e['weight']*e['regret']
        if abs(sum(evidence_costs.values())-duration*c['temporal_regret']) > 1e-9:
            raise ValueError('evidence_cost_reconstruction_mismatch')
        parts = {'pooled_fit': duration*c['pooled_cost'], **evidence_costs,
                 'segment_charge': .15, 'label_change': change, 'resolution_discount': resolution}
        segments.append({'span': s['span'], 'label': c['label'], 'candidate_rank': rank, 'cost_parts': parts})
        previous = c
    keys = segments[0]['cost_parts'].keys() if segments else ()
    totals = {k: sum(s['cost_parts'][k] for s in segments) for k in keys}
    return {'segments': segments, 'cost_parts': totals, 'total_cost': sum(totals.values()),
            'all_segments_in_top_five': all(s['candidate_rank'] <= 5 for s in segments),
            'policy': 'fixed_complete_path_under_same_context_no_source_labels_no_reoptimization'}


def build(manifest, review_dir, previous_dir, output):
    out, source, prior_dir = Path(output), Path(review_dir), Path(previous_dir)
    if out.exists():
        raise ValueError('output_exists_choose_new_directory')
    entries = json.loads(Path(manifest).read_text(encoding='utf-8'))['entries']
    validate_split(entries)
    packages = {e['package_path']: e for e in entries}
    plan_path, queue_path = source/'plan/report.json', source/'plan/cases.jsonl'
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    queue_rows = list(map(json.loads, queue_path.read_text(encoding='utf-8').splitlines()))
    queue = {r['case_id']: r for r in queue_rows}
    previous = json.loads((prior_dir/'report.json').read_text(encoding='utf-8'))
    old_cases = {r['case_id']: r for r in previous['cases']}
    if len(packages) != len(entries) or len(queue) != len(queue_rows) or len(old_cases) != len(previous['cases']):
        raise ValueError('duplicate_input_identity')
    hashes = {'manifest_sha256': digest(manifest), 'plan_sha256': digest(plan_path), 'queue_sha256': digest(queue_path)}
    if plan['manifest_sha256'] != hashes['manifest_sha256'] or any(previous[k] != v for k, v in hashes.items()):
        raise ValueError('frozen_plan_changed')
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
        if old_cases[item['case_id']]['ir_sha256'] != item['ir_sha256']:
            raise ValueError('previous_ir_changed')
    code = ['harmony_ablation_review.py', 'harmony_multiscale_shadow.py', 'harmony_joint.py',
            'harmony_surface.py', 'harmony_temporal_shadow.py', 'harmony_cost_diagnostic.py',
            'harmony_context_sensitivity.py']
    report = {'version': 'harmony-ablation-review-0.1.0', 'engine_version': VERSION,
              'arms': ARMS, 'arm_names': NAMES, 'policy': POLICY, **hashes,
              'previous_report_sha256': digest(prior_dir/'report.json'),
              'code_sha256': {p: digest(Path(__file__).with_name(p)) for p in code},
              'cases': [], 'production_enabled': False, 'accuracy_measured': False,
              'reserved_contents_read': False, 'source_labels_used_for_inference': False}
    out.mkdir(parents=True); (out/'results').mkdir()
    (out/'run-contract.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    for item in plan['plan']:
        case_id = item['case_id']; case = queue[case_id]; entry = packages[case['package_path']]
        ir_path = Path(case['package_path'])/'canonical_music_ir.json'
        old_path, prior_path = source/'results'/(case_id+'.json'), prior_dir/'results'/(case_id+'.json')
        if (digest(ir_path) != item['ir_sha256'] or digest(entry['score_source_path']) != entry['score_sha256']
                or digest(prior_path) != old_cases[case_id]['result_sha256']
                or digest(old_path) != old_cases[case_id]['previous_result_sha256']):
            raise ValueError('input_content_changed')
        ir = json.loads(ir_path.read_text(encoding='utf-8'))
        if ir['score']['score_id'] != entry['score_id'] or ir['ir_document_id'] != entry['ir_document_id']:
            raise ValueError('ir_identity_mismatch')
        old, prior = (json.loads(p.read_text(encoding='utf-8')) for p in (old_path, prior_path))
        if any(r['case_id'] != case_id or r['target_span'] != case['target_span'] or len(r['runs']) != 2 for r in (old, prior)):
            raise ValueError('saved_result_identity_mismatch')
        runs = []
        for before, latest in zip(old['runs'], prior['runs']):
            if before['analysis_span'] != latest['analysis_span'] or before['margin_quarters'] != latest['margin_quarters']:
                raise ValueError('prior_context_changed')
            computed = {arm: analyze(ir, analysis_span=before['analysis_span'], **switches) for arm, switches in ARMS.items()}
            replay = {'none_vs_temporal': replay_matches(computed['none'], before['experiment']),
                      'both_vs_v01': replay_matches(computed['both'], latest['experiment'])}
            if not all(replay.values()):
                raise ValueError('replay_failed:'+case_id)
            matrix = {objective: {path_arm: rescore_path(ir, result, switches) for path_arm, result in computed.items()}
                      for objective, switches in ARMS.items()}
            for arm in ARMS:
                if abs(matrix[arm][arm]['total_cost']-computed[arm]['path_cost']) > 1e-8:
                    raise ValueError('selected_path_cost_mismatch')
            runs.append({'margin_quarters': before['margin_quarters'], 'analysis_span': before['analysis_span'],
                         **computed, 'replay_checks': replay, 'fixed_path_cost_matrix': matrix,
                         'deltas_vs_none': {arm: compare_target(computed['none'], r, case['target_span']) for arm, r in computed.items()}})
        summary = {'case_id': case_id, 'collection': item['collection'], 'target_span': case['target_span'],
                   'ir_sha256': item['ir_sha256'], 'previous_result_sha256': digest(old_path),
                   'multiscale_result_sha256': digest(prior_path),
                   'context_stable': {arm: context_stable(runs, arm, case['target_span'], 2) for arm in ARMS},
                   'stability_components': {arm: stability_components(runs, arm, case['target_span'], 2) for arm in ARMS},
                   'deltas': [{arm: run['deltas_vs_none'][arm] for arm in ARMS} for run in runs]}
        path = out/'results'/(case_id+'.json')
        path.write_text(json.dumps({**summary, 'runs': runs, 'arm_names': NAMES}, ensure_ascii=False, indent=2), encoding='utf-8')
        report['cases'].append({**summary, 'result_sha256': digest(path)})
        print(json.dumps({'completed': len(report['cases']), 'case_id': case_id, 'stable': summary['context_stable']}), flush=True)
    report['summary'] = {
        'case_count': len(report['cases']), 'new_inference_runs': len(report['cases'])*2*len(ARMS),
        'context_stable_counts': {a: sum(c['context_stable'][a] is True for c in report['cases']) for a in ARMS},
        'label_change_counts_vs_none': {a: sum(any(not d[a]['same_labels_at_all_target_times'] for d in c['deltas']) for c in report['cases']) for a in ARMS},
        'all_replays_passed': True,
    }
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for flag in ('manifest', 'review-dir', 'previous-dir', 'output'):
        p.add_argument('--'+flag, required=True)
    args = p.parse_args()
    build(args.manifest, args.review_dir, args.previous_dir, args.output)
