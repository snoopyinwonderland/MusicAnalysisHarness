"""Fixed, stratified train diagnostic expansion; no parameter tuning or gold claims."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from .formal_ir import q
from .harmony_joint import f
from .harmony_review_cohort import validate_split
from .harmony_context_sensitivity import build as run_sensitivity, compare_target, projection

CATEGORIES = ('distributed', 'vertical', 'incomplete', 'short_change', 'seventh', 'geometry')


def categories(row):
    tags = set(row['tags']); result = []
    for tag, category in [('distributed_complete_shape_candidate', 'distributed'),
                          ('complete_vertical_shape_present', 'vertical'),
                          ('no_complete_shape_needs_review', 'incomplete'),
                          ('source_short_change_candidate', 'short_change')]:
        if tag in tags:result.append(category)
    if any(t.startswith('source_seventh_') for t in tags):result.append('seventh')
    if any(t.startswith('geometry_') for t in tags):result.append('geometry')
    return result


def select(rows, per_category=5, family_cap=4):
    if per_category < 1 or family_cap < 1:raise ValueError('positive_caps_required')
    ids = [r['case_id'] for r in rows]
    if len(ids) != len(set(ids)):raise ValueError('duplicate_case')
    if any(r['split'] != 'train' for r in rows):raise ValueError('non_train_case')
    chosen = []; used = set(); families = Counter(); collections = Counter()
    for category in CATEGORIES:
        for _ in range(per_category):
            pool = [r for r in rows if r['case_id'] not in used and category in categories(r)
                    and families[r['work_family_id']] < family_cap]
            if not pool:break
            r = min(pool, key=lambda r: (collections[r['collection']], families[r['work_family_id']], r['case_id']))
            chosen.append((category, r)); used.add(r['case_id'])
            families[r['work_family_id']] += 1; collections[r['collection']] += 1
    return chosen


def aggregate(items):
    """Review flags, never automatic accuracy or regression verdicts."""
    strata = {}; review = []
    for category in CATEGORIES:
        group = [r for r in items if r['stratum'] == category]
        wide = [run for r in group for run in r['runs'] if f(run['margin_quarters']) == 2]
        strata[category] = {'cases': len(group), 'paired_cases_at_margin_two': len(wide),
            'baseline_context_stable': sum(r['context_stable']['baseline'] is True for r in group),
            'experiment_context_stable': sum(r['context_stable']['experiment'] is True for r in group),
            'unknown_stability': sum(any(v is None for v in r['context_stable'].values()) for r in group),
            'label_changes': sum(not w['delta']['same_labels_at_all_target_times'] for w in wide),
            'internal_boundary_changes': sum(not w['delta']['same_internal_boundaries'] for w in wide),
            'more_segments': sum(w['target_segments']['experiment'] > w['target_segments']['baseline'] for w in wide),
            'fewer_segments': sum(w['target_segments']['experiment'] < w['target_segments']['baseline'] for w in wide)}
    for r in items:
        flags = []; stability = r['context_stable']
        if stability['baseline'] is True and stability['experiment'] is False:flags.append('lost_context_stability')
        if stability['experiment'] is False:flags.append('experiment_context_sensitive')
        wide = next((w for w in r['runs'] if f(w['margin_quarters']) == 2), None)
        if wide:
            if r['stratum'] == 'short_change' and not all(v is True for v in wide['target_edge_support']['experiment'].values()):
                flags.append('short_change_proxy_edges_not_both_supported')
            if r['stratum'] == 'distributed' and wide['target_segments']['experiment'] > 1:
                flags.append('distributed_proxy_contains_internal_boundary')
            if not wide['delta']['same_labels_at_all_target_times']:flags.append('candidate_labels_changed')
        if flags:review.append({'case_id': r['case_id'], 'stratum': r['stratum'], 'flags': flags,
                                'musical_error_confirmed': False, 'review_status': 'unreviewed'})
    review.sort(key=lambda r: ('lost_context_stability' not in r['flags'],
                              'experiment_context_sensitive' not in r['flags'], r['case_id']))
    return {'strata': strata,
            'gained_context_stability': sum(r['context_stable']['baseline'] is False and r['context_stable']['experiment'] is True for r in items),
            'lost_context_stability': sum(r['context_stable']['baseline'] is True and r['context_stable']['experiment'] is False for r in items),
            'both_context_sensitive': sum(r['context_stable']['baseline'] is False and r['context_stable']['experiment'] is False for r in items),
            'review_queue': review, 'accuracy_measured': False}


def summarize_saved(output):
    path = Path(output)/'report.json'; report = json.loads(path.read_text(encoding='utf-8'))
    if report['version'] != 'harmony-medium-review-0.1.0':raise ValueError('unsupported_report_version')
    report['aggregate'] = aggregate(report['cases'])
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report['aggregate'], indent=2)); return report


def build(manifest, comparison_dir, output):
    manifest_raw = Path(manifest).read_bytes(); entries = json.loads(manifest_raw)['entries']; validate_split(entries)
    packages = {e['package_path']: e for e in entries}
    if len(packages) != len(entries):raise ValueError('duplicate_manifest_package')
    source = Path(comparison_dir)
    previous_raw = (source/'report.json').read_bytes(); previous = json.loads(previous_raw)
    if previous['manifest_sha256'] != hashlib.sha256(manifest_raw).hexdigest():raise ValueError('manifest_changed')
    queue_raw = (source/'cases.jsonl').read_bytes()
    rows = list(map(json.loads, queue_raw.decode('utf-8').splitlines()))
    if len({r['case_id'] for r in rows}) != len(rows):raise ValueError('duplicate_case')
    # Complete metadata/split preflight before any score or IR is read.
    for r in rows:
        e = packages[r['package_path']]
        if r['split'] != 'train' or e['split'] != 'train':raise ValueError('non_train_case')
        for key in ('score_id', 'ir_document_id', 'work_family_id', 'score_sha256', 'annotation_sha256', 'rights'):
            if r[key] != e[key]:raise ValueError('manifest_case_mismatch:'+key)
        if r['collection'] != e['collection_id']:raise ValueError('collection_mismatch')
    previous_ids = {r['case_id'] for r in previous['plan']}
    eligible = []; excluded = []; cache = {}
    for r in sorted(rows, key=lambda r: r['case_id']):
        a, b = f(r['target_span']['start']), f(r['target_span']['end'])
        if a < 0 or b <= a:raise ValueError('invalid_target')
        reason = ('previous_smoke_case' if r['case_id'] in previous_ids else
                  'target_longer_than_four_quarters' if b-a > 4 else None)
        if reason:
            excluded.append({'case_id': r['case_id'], 'reason': reason}); continue
        package = r['package_path']; e = packages[package]
        if package not in cache:
            data = (Path(package)/'canonical_music_ir.json').read_bytes(); ir = json.loads(data)
            if ir['ir_document_id'] != e['ir_document_id'] or ir['score']['score_id'] != e['score_id']:
                raise ValueError('live_ir_identity_mismatch')
            if hashlib.sha256(Path(e['score_source_path']).read_bytes()).hexdigest() != e['score_sha256']:
                raise ValueError('live_score_hash_mismatch')
            cache[package] = (ir, hashlib.sha256(data).hexdigest())
        ir, irhash = cache[package]
        if any(m.get('ir_sha256') and m['ir_sha256'] != irhash for m in r['members']):
            raise ValueError('saved_ir_hash_mismatch')
        left, right = max(Fraction(0), a-2), b+2
        active = [s for s in ir['sounding_events'] if f(s['span']['start']) < right and f(s['span']['end']) > left]
        points = {f(s['span'][k]) for s in active for k in ('start', 'end') if left <= f(s['span'][k]) <= right}
        if len(points) > 40 or len(active) > 120:
            excluded.append({'case_id': r['case_id'], 'reason': 'fixed_complexity_cap'}); continue
        eligible.append(r)
    chosen = select(eligible)
    out = Path(output); plan_dir = out/'plan'; plan_dir.mkdir(parents=True, exist_ok=True)
    policy = {'category_order': list(CATEGORIES), 'per_category': 5, 'family_cap': 4,
              'margin_quarters': [1, 2], 'target_max_quarters': 4, 'onset_release_cap': 40, 'sound_cap': 120,
              'selection': 'least represented collection, then family, then stable case ID; rare strata first',
              'source_tags_are_proxies_not_gold': True, 'exclude_previous_smoke_ids': sorted(previous_ids)}
    plan = [{**{k: r[k] for k in ('case_id', 'collection', 'target_span', 'split')}, 'stratum': category,
             'ir_sha256': cache[r['package_path']][1]} for category,r in chosen]
    code_hashes = {name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                   for name in ('harmony_joint.py', 'harmony_temporal_shadow.py')}
    planning = {'manifest_sha256': hashlib.sha256(manifest_raw).hexdigest(), 'plan': plan, 'policy': policy,
                'source_queue_sha256': hashlib.sha256(queue_raw).hexdigest(),
                'source_smoke_report_sha256': hashlib.sha256(previous_raw).hexdigest(),
                'engine_code_hashes': code_hashes, 'eligible_cases': len(eligible), 'exclusions': excluded,
                'eligible_category_counts': dict(Counter(c for r in eligible for c in categories(r))),
                'selected_stratum_counts': dict(Counter(c for c,r in chosen))}
    # Freeze selection before producing or inspecting any new inference outputs.
    (plan_dir/'report.json').write_text(json.dumps(planning, indent=2), encoding='utf-8')
    (plan_dir/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for c,r in chosen), encoding='utf-8')
    print(json.dumps({'selected': len(plan), 'strata': planning['selected_stratum_counts'], 'policy_frozen': True}), flush=True)
    sensitivity = run_sensitivity(manifest, plan_dir, out/'results', margins=(1, 2))
    items = []
    for r, (category, case) in zip(sensitivity['cases'], chosen):
        if r['case_id'] != case['case_id']:raise ValueError('result_order_mismatch')
        detail = json.loads((out/'results'/(r['case_id']+'.json')).read_text(encoding='utf-8'))
        runs = []
        for run in detail['runs']:
            delta = compare_target(run['baseline'], run['experiment'], case['target_span'])
            runs.append({'margin_quarters': run['margin_quarters'], 'delta': delta,
                         'target_segments': {k: len(projection(run[k], case['target_span'])) for k in ('baseline', 'experiment')},
                         'target_edge_support': run['target_edge_support']})
        items.append({'case_id': r['case_id'], 'collection': r['collection'], 'stratum': category,
                      'work_family_id': case['work_family_id'], 'tags': case['tags'],
                      'context_stable': r['context_stable'], 'runs': runs})
    summary = {'version': 'harmony-medium-review-0.1.0', 'policy': policy, 'cases': items,
               'aggregate': aggregate(items),
               'selected_count': len(chosen), 'family_count': len({r['work_family_id'] for c,r in chosen}),
               'collection_counts': dict(Counter(r['collection'] for c,r in chosen)),
               'engine_code_hashes': code_hashes, 'accuracy_measured': False, 'production_enabled': False,
               'reserved_contents_read': False, 'limitations': ['Development sample, not blind evaluation',
                   'Strata are source/geometry proxies; greater segmentation is a review flag, not confirmed error',
                   'Short-target and complexity caps exclude some harder passages',
                   'No weights, source annotations, or training eligibility changed']}
    (out/'report.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('cases','policy')}, indent=2))
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--manifest')
    p.add_argument('--comparison-dir'); p.add_argument('--output', required=True)
    p.add_argument('--summarize', action='store_true')
    a = p.parse_args()
    if a.summarize:summarize_saved(a.output)
    else:
        if not a.manifest or not a.comparison_dir:p.error('--manifest and --comparison-dir are required for inference')
        build(a.manifest, a.comparison_dir, a.output)
