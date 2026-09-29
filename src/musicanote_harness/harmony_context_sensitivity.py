"""Train-only, bounded context sensitivity diagnostics; never an accuracy metric."""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

from .formal_ir import q
from .harmony_joint import analyze_joint, f
from .harmony_temporal_shadow import analyze as temporal
from .harmony_review_comparison import target_segments
from .harmony_review_cohort import validate_split

VERSION = 'harmony-context-sensitivity-0.1.0'


def projection(result, target):
    """Reject holes/overlaps rather than counting missing output as agreement."""
    segments = target_segments(result, target)
    cursor = f(target['start'])
    for s in segments:
        if f(s['span']['start']) != cursor or f(s['span']['end']) <= cursor:
            raise ValueError('invalid_target_coverage')
        cursor = f(s['span']['end'])
    if cursor != f(target['end']):
        raise ValueError('incomplete_target_coverage')
    return segments


def compare_target(left, right, target):
    a, b = f(target['start']), f(target['end'])
    lhs, rhs = projection(left, target), projection(right, target)
    points = sorted({a, b, *(f(s['span'][k]) for seq in (lhs, rhs) for s in seq for k in ('start', 'end'))})
    changed = []
    for x, y in zip(points, points[1:]):
        labels = [next(s['selected']['label'] for s in seq
                       if f(s['span']['start']) <= x < f(s['span']['end'])) for seq in (lhs, rhs)]
        if labels[0] != labels[1]:
            changed.append({'span': {'start': q(x), 'end': q(y)}, 'left': labels[0], 'right': labels[1]})
    mismatch = sum((f(s['span']['end'])-f(s['span']['start']) for s in changed), Fraction(0))
    old, new = ({f(s['span']['start']) for s in seq[1:]} for seq in (lhs, rhs))
    return {'disagreement_quarters': q(mismatch), 'disagreement_fraction': q(mismatch/(b-a)),
            'changed_intervals': changed, 'added_internal_boundaries': [q(t) for t in sorted(new-old)],
            'removed_internal_boundaries': [q(t) for t in sorted(old-new)],
            'same_labels_at_all_target_times': mismatch == 0, 'same_internal_boundaries': old == new,
            'accuracy_measured': False}


def edge_support(result, target):
    """Diagnostic support only; a search-window edge is not an inferred boundary."""
    bounds = {f(s['span']['start']) for s in result['segments'][1:]}
    a, b = (f(result['analysis_span'][k]) for k in ('start', 'end'))
    return {k: (None if f(target[k]) in (a, b) else f(target[k]) in bounds) for k in ('start', 'end')}


def context_stable(runs, engine, target, expected_count):
    if len(runs) != expected_count:
        return None
    first = runs[0][engine]
    edges = edge_support(first, target)
    for run in runs[1:]:
        delta = compare_target(first, run[engine], target)
        if not delta['same_labels_at_all_target_times'] or not delta['same_internal_boundaries']:
            return False
        if edge_support(run[engine], target) != edges:
            return False
    return True


def stability_components(runs, engine, target, expected_count):
    """Separate harmonic label stability from source-target edge support stability."""
    keys = ('target_labels', 'internal_boundaries', 'target_edge_support')
    if not runs or len(runs) != expected_count:
        return {k: None for k in keys}
    result = {k: True for k in keys}
    first = runs[0][engine]; edges = edge_support(first, target)
    for run in runs[1:]:
        delta = compare_target(first, run[engine], target)
        result['target_labels'] &= delta['same_labels_at_all_target_times']
        result['internal_boundaries'] &= delta['same_internal_boundaries']
        result['target_edge_support'] &= edge_support(run[engine], target) == edges
    return result


def build(manifest, comparison_dir, output, margins=(1, 2, 4)):
    margins = sorted(set(Fraction(m) for m in margins))
    if len(margins) < 2 or min(margins) <= 0:
        raise ValueError('need_two_positive_context_margins')
    manifest_data = Path(manifest).read_bytes()
    entries = json.loads(manifest_data)['entries']
    validate_split(entries)
    packages = {e['package_path']: e for e in entries}
    if len(packages) != len(entries):
        raise ValueError('duplicate_manifest_package')
    source = Path(comparison_dir)
    plan_data = (source/'report.json').read_bytes()
    report = json.loads(plan_data)
    if report['manifest_sha256'] != hashlib.sha256(manifest_data).hexdigest():
        raise ValueError('manifest_changed')
    queue_data = (source/'cases.jsonl').read_bytes()
    queue_rows = list(map(json.loads, queue_data.decode('utf-8').splitlines()))
    queue = {r['case_id']: r for r in queue_rows}
    if len(queue) != len(queue_rows):
        raise ValueError('duplicate_queue_case')
    # Check every selected identity/split before opening any score/IR contents.
    for item in report['plan']:
        case = queue[item['case_id']]; entry = packages[case['package_path']]
        if any(r['split'] != 'train' for r in (item, case, entry)):
            raise ValueError('non_train_case')
        if item['target_span'] != case['target_span']:
            raise ValueError('target_changed')
        if item['collection'] != case['collection'] or case['collection'] != entry['collection_id']:
            raise ValueError('collection_mismatch')
        for key in ('score_id', 'ir_document_id', 'work_family_id', 'score_sha256', 'annotation_sha256', 'rights'):
            if case[key] != entry[key]:
                raise ValueError('manifest_case_mismatch:'+key)
    out = Path(output); out.mkdir(parents=True, exist_ok=True)
    summaries = []
    for item in report['plan']:
        case = queue[item['case_id']]; entry = packages[case['package_path']]
        data = (Path(case['package_path'])/'canonical_music_ir.json').read_bytes()
        if hashlib.sha256(data).hexdigest() != item['ir_sha256']:
            raise ValueError('live_ir_hash_mismatch')
        if hashlib.sha256(Path(entry['score_source_path']).read_bytes()).hexdigest() != entry['score_sha256']:
            raise ValueError('live_score_hash_mismatch')
        ir = json.loads(data); target = case['target_span']
        if ir['ir_document_id'] != entry['ir_document_id'] or ir['score']['score_id'] != entry['score_id']:
            raise ValueError('live_ir_identity_mismatch')
        runs = []; skipped = []
        for margin in margins:
            a, b = max(Fraction(0), f(target['start'])-margin), f(target['end'])+margin
            span = {'start': q(a), 'end': q(b)}
            active = [s for s in ir['sounding_events'] if f(s['span']['start']) < b and f(s['span']['end']) > a]
            points = {f(s['span'][k]) for s in active for k in ('start', 'end') if a <= f(s['span'][k]) <= b}
            if b-a > 12 or len(points) > 72 or len(active) > 240:
                skipped.append({'margin_quarters': q(margin), 'reason': 'complexity_cap'}); continue
            baseline = analyze_joint(ir, analysis_span=span)
            experiment = temporal(ir, cell_divisions=2, analysis_span=span)
            run = {'margin_quarters': q(margin), 'analysis_span': span,
                   'baseline': baseline, 'experiment': experiment,
                   'paired_target_delta': compare_target(baseline, experiment, target),
                   'target_edge_support': {k: edge_support(r, target) for k, r in
                                           (('baseline', baseline), ('experiment', experiment))}}
            run['delta_from_smallest_executed_context'] = {
                k: compare_target(runs[0][k], run[k], target) for k in ('baseline', 'experiment')} if runs else None
            runs.append(run)
        summary = {'case_id': item['case_id'], 'collection': item['collection'], 'target_span': target,
                   'ir_sha256': item['ir_sha256'], 'runs_completed': len(runs), 'skipped': skipped,
                   'context_stable': {k: context_stable(runs, k, target, len(margins)) for k in ('baseline', 'experiment')}}
        summary['stability_components'] = {k: stability_components(runs, k, target, len(margins))
                                           for k in ('baseline', 'experiment')}
        (out/(item['case_id']+'.json')).write_text(json.dumps({**summary, 'runs': runs}, indent=2), encoding='utf-8')
        summaries.append(summary)
    result = {'version': VERSION, 'manifest_sha256': hashlib.sha256(manifest_data).hexdigest(),
              'source_plan_sha256': hashlib.sha256(plan_data).hexdigest(),
              'source_queue_sha256': hashlib.sha256(queue_data).hexdigest(),
              'margins_quarters': [q(m) for m in margins], 'cases': summaries,
              'accuracy_measured': False, 'production_enabled': False, 'reserved_contents_read': False,
              'limits': ['Small train sample; no gold accuracy claim',
                         'Joint max-span/pruning/transition policy unchanged',
                         'Full-score nearest voice neighbors; bounded harmony path history',
                         'Stable output can still be wrong; source spans are not required boundaries']}
    (out/'report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', required=True)
    p.add_argument('--comparison-dir', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    build(args.manifest, args.comparison_dir, args.output)
