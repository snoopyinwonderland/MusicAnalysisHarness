"""Frozen whole-song Test A. No gold, title-dependent rules, fitting or retries.

The research arm retains native full-scope limits. It does NOT stitch local
winners into a pretend whole-score result. Evaluation is a separate phase.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import random
from time import perf_counter
import traceback

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / 'output/harmony-adversarial-score-2026-10-05-r1/model.json.gz'
MODEL_SHA = '2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf'
VERSION = 'frozen-old26-native-whole-score-v1'
SCORER_VERSION = 'test-a-nonoverlap-one-to-one-unknown-preserving-v1'
TEMPLATES = ((0, 4, 7), (0, 3, 7), (0, 3, 6), (0, 4, 8),
             (0, 4, 7, 10), (0, 4, 7, 11), (0, 3, 7, 10),
             (0, 3, 6, 10), (0, 3, 6, 9))
NATURAL = dict(zip('CDEFGAB', (0, 2, 4, 5, 7, 9, 11)))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    """Generated execution artifacts, not source-file editing."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def fraction(v):
    return F(v['numerator'], v['denominator']) if isinstance(v, dict) else F(str(v))


def read_score(path):
    from .dcml_import import parse_score_without_imported_harmony
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    score, removed, _ = parse_score_without_imported_harmony(Path(path))
    ir = FormalIRAdapter().convert(CanonicalIRBuilder().build(score, path), path)
    total = max([fraction(ir['score']['duration_quarters'])] +
                [fraction(m['global_start_quarter']) + fraction(m['actual_duration_quarter'])
                 for m in ir['measures']])
    if total <= 0:
        raise ValueError('empty_score')
    return ir, total, removed


def sounding_rows(ir):
    rows = []
    for s in ir['sounding_events']:
        a, b = fraction(s['span']['start']), fraction(s['span']['end'])
        midi = s['pitch'].get('midi_pitch')
        if a < b and midi is not None:
            rows.append((a, b, int(midi)))
    return rows


def merge_spans(spans):
    result = []
    for s in spans:
        if (result and result[-1]['end'] == s['start'] and
                all(result[-1][k] == s[k] for k in ('root_pc', 'pcs', 'bass_pc'))):
            result[-1]['end'] = s['end']
        else:
            result.append(dict(s))
    return result


def beat_template_baseline(ir, total):
    """Fixed denominator-beat duration-weighted template matching, all staves."""
    sounds = sounding_rows(ir)
    spans = []
    for m in ir['measures']:
        start = fraction(m['global_start_quarter'])
        end = min(total, start + fraction(m['actual_duration_quarter']))
        denominator = m.get('time_signature', {}).get('beat_type')
        if not denominator:
            continue  # unknown meter stays a gap
        unit = F(4, int(denominator))
        a = start
        while a < end:
            b = min(a + unit, end)
            weights = Counter()
            active = [(x, y, p) for x, y, p in sounds if x < b and a < y]
            for x, y, p in active:
                weights[p % 12] += min(b, y) - max(a, x)
            if weights:
                exposure = sum(weights.values(), F())
                lowest = min(p for _, _, p in active) % 12
                candidates = []
                for root in range(12):
                    for i, template in enumerate(TEMPLATES):
                        pcs = sorted({(root + t) % 12 for t in template})
                        support = sum((weights[p] for p in pcs), F()) / exposure
                        completeness = F(len(set(pcs) & set(weights)), len(pcs))
                        fit = F(65, 100) * support + F(35, 100) * completeness
                        fit -= F(15, 1000) * max(0, len(pcs) - 3)
                        fit += F(2, 100) * (root == lowest)
                        candidates.append((-fit, root, i, pcs))
                _, root, _, pcs = min(candidates)
                spans.append(dict(start=str(a), end=str(b), root_pc=root, pcs=pcs,
                                  bass_pc=lowest if lowest in pcs else None))
            a = b
    return merge_spans(spans), {'status': 'complete', 'template_count': len(TEMPLATES) * 12}


def native_engine(ir, total):
    """Unchanged full-scope guard -> original supply -> old26 exact selector."""
    from .harmony_bounded_recovery import CONFIG, grace_projection, tile_plan, bound_evidence
    from .harmony_candidate_recall import rational as q
    from .harmony_source_clock import SourceClockGuard
    from .harmony_window_workspace import WindowWorkspace
    from .harmony_functional_scoring import supply
    from .harmony_full_score import Scorer, coefficients
    if digest(MODEL) != MODEL_SHA:
        raise ValueError('frozen_model_changed')
    model = json.loads(gzip.decompress(MODEL.read_bytes()))
    if (model.get('production_deployment') is not False or
            model.get('source_labels_used_at_inference') is not False):
        raise ValueError('invalid_model_use_contract')
    weights = coefficients({k: fraction(v) for k, v in model['weights'].items()})
    view, grace = grace_projection(ir)
    span = {'start': q(F()), 'end': q(total)}
    sounds = view['sounding_events']
    points = {F(), total}
    points.update(fraction(s['span'][k]) for s in sounds for k in ('start', 'end')
                  if 0 < fraction(s['span'][k]) < total)
    points.update(fraction(m['global_start_quarter']) for m in view['measures']
                  if 0 < fraction(m['global_start_quarter']) < total)
    blockers = []
    if len(points) - 1 > CONFIG['global_cells']:
        blockers.append('global_cell_budget_no_truncation')
    if len(sounds) > CONFIG['global_sounds']:
        blockers.append('global_sound_budget_no_pruning')
    # Exact early evaluation of existing native guards, not a new limit.
    info = dict(native_cells=len(points) - 1, native_sounds=len(sounds), native_limits=CONFIG,
                source_labels_used=False, model_sha256=MODEL_SHA)
    if blockers:
        return [], dict(info, status='native_whole_scope_abstention', blockers=blockers)
    clock = SourceClockGuard(ir)
    gate = clock.scope(span)
    if not gate['accepted']:
        return [], dict(info, status='source_clock_abstention', source_clock_gate=gate)
    plan = tile_plan(view, span)
    if plan['status'] != 'ready':
        return [], dict(info, status=plan['status'], blockers=plan.get('blockers', []))
    _, ev, _ = bound_evidence(view, span, grace)
    graph, _ = WindowWorkspace(view).build(plan, ev.source)
    graph, _ = supply(graph, ev)
    sc = Scorer(graph, ev, weights, grace_notes=grace['grace_note_events'],
                history_gate=lambda a, b: clock.scope({'start': q(a), 'end': q(b)})['accepted'])
    result = sc.decode(transition_budget=CONFIG['decoder_transition_budget'])
    selected = result['selected']
    if selected is None:
        return [], dict(info, status=result['status'], transitions=result.get('transitions'))
    by_id = {e.group_id: e for e in graph.edges}
    sounds = sounding_rows(ir)
    output = []
    for seg in selected['segments']:
        e = by_id[seg['semantic_group_ref']]
        root, members = e.signature
        if root is None:
            continue
        pc = lambda token: (NATURAL[token[0]] + token[1]) % 12
        pcs = sorted({pc(t) for t in members})
        active = [p for x, y, p in sounds if x <= e.start < y]
        bass = min(active) % 12 if active else None
        output.append(dict(start=str(e.start), end=str(e.end), root_pc=pc(root), pcs=pcs,
                           bass_pc=bass if bass in pcs else None))
    return merge_spans(output), dict(info, status='complete', selector_status=result['status'])


def worker(path, arm, output):
    t = perf_counter()
    try:
        source_hash = digest(path)
        ir, total, removed = read_score(path)
        parse_seconds = perf_counter() - t
        from .harmony_source_clock import SourceClockGuard
        from .formal_ir import q
        gate = SourceClockGuard(ir).scope({'start': q(F()), 'end': q(total)})
        if not gate['accepted']:
            spans, details = [], dict(status='source_clock_abstention', source_clock_gate=gate)
        else:
            spans, details = (native_engine(ir, total) if arm == 'engine' else beat_template_baseline(ir, total))
        if digest(path) != source_hash:
            raise ValueError('source_changed_during_inference')
        if arm == 'engine':
            Path(output).with_suffix('.ir.json.gz').write_bytes(gzip.compress(
                json.dumps(ir, ensure_ascii=False, separators=(',', ':')).encode('utf-8'), mtime=0))
        result = dict(arm=arm, source_sha256=source_hash, source_file=str(path),
                      score_duration=str(total), parse_seconds=parse_seconds,
                      seconds=perf_counter() - t, harmony_elements_removed=removed,
                      spans=spans, **details)
    except Exception as exc:
        result = dict(arm=arm, status='error', seconds=perf_counter() - t,
                      error=f'{type(exc).__name__}: {exc}', traceback=traceback.format_exc())
    write(output, result)


def third(pcs, root):
    iv = {(p - root) % 12 for p in pcs}
    if 4 in iv:
        return 'aug' if 8 in iv and 7 not in iv else 'maj'
    if 3 in iv:
        return 'dim' if 6 in iv and 7 not in iv else 'min'
    # Gold compatibility: also accepts no-third triads as the original scorer.
    # The limitation is documented; bass unknown is never imputed.
    return 'sus'


def validated_spans(spans, total=None):
    result = []
    previous_end = None
    for s in spans:
        if not isinstance(s.get('start'), str) or not isinstance(s.get('end'), str):
            raise ValueError('time_must_be_fraction_string')
        a, b = F(s['start']), F(s['end'])
        root, pcs, bass = s['root_pc'], s['pcs'], s.get('bass_pc')
        if not 0 <= a < b or (total is not None and b > total):
            raise ValueError('invalid_span_extent')
        if previous_end is not None and a < previous_end:
            raise ValueError('unsorted_or_overlapping_spans')
        if (type(root) is not int or not 0 <= root < 12 or not isinstance(pcs, list) or
                not pcs or len(set(pcs)) != len(pcs) or
                any(type(p) is not int or not 0 <= p < 12 for p in pcs) or root not in pcs):
            raise ValueError('invalid_pitch_class')
        if bass is not None and (type(bass) is not int or not 0 <= bass < 12):
            raise ValueError('invalid_bass')
        result.append(dict(start=a, end=b, root=root, pcs=set(pcs), bass=bass))
        previous_end = b
    return result


def boundary_matches(gold, pred, tolerance=F(1, 2)):
    """Maximum cardinality monotone one-to-one tolerance matching."""
    g, p = sorted(set(gold)), sorted(set(pred))
    i = j = hit = 0
    while i < len(g) and j < len(p):
        if abs(g[i] - p[j]) <= tolerance:
            hit += 1
            i += 1
            j += 1
        elif p[j] < g[i]:
            j += 1
        else:
            i += 1
    return hit, len(p), len(g)


def compare(gold, pred):
    totals = {k: F() for k in ('gold', 'covered', 'root', 'triad', 'pcs', 'bass')}
    for g in gold:
        totals['gold'] += g['end'] - g['start']
        for p in pred:
            d = min(g['end'], p['end']) - max(g['start'], p['start'])
            if d <= 0:
                continue
            totals['covered'] += d
            totals['root'] += d * (g['root'] == p['root'])
            totals['triad'] += d * (g['root'] == p['root'] and third(g['pcs'], g['root']) == third(p['pcs'], p['root']))
            totals['pcs'] += d * (g['pcs'] == p['pcs'])
            totals['bass'] += d * (p['bass'] is not None and g['bass'] == p['bass'])
    hit, np, ng = boundary_matches([s['start'] for s in gold[1:]], [s['start'] for s in pred[1:]])
    return {k: float(v) for k, v in totals.items()} | dict(boundary_tp=hit, boundary_pred=np, boundary_gold=ng)


def aggregate(rows):
    keys = ('gold', 'covered', 'root', 'triad', 'pcs', 'bass', 'boundary_tp', 'boundary_pred', 'boundary_gold')
    sums = {k: sum(r[k] for r in rows) for k in keys}
    den = sums['gold']
    tp, np, ng = (sums[k] for k in ('boundary_tp', 'boundary_pred', 'boundary_gold'))
    return dict(songs=len(rows), gold_quarters=den,
                **{k: sums[k] / den if den else None for k in ('root', 'triad', 'pcs', 'bass', 'covered')},
                boundary_precision=tp / np if np else 0,
                boundary_recall=tp / ng if ng else 0,
                boundary_f1=2 * tp / (np + ng) if np + ng else 0)


def score_submissions(gold_file, submissions, statuses, output):
    # Called only after both prediction files have been sealed by the runner.
    gold = json.loads(Path(gold_file).read_text(encoding='utf-8'))['songs']
    reports = {}
    for arm, submission in submissions.items():
        rows = []
        for s in gold:
            g = validated_spans(s['gold'], F(s['total_quarters']))
            predicted = submission['songs'].get(s['title'], [])
            p = validated_spans(predicted)  # own-score bounds checked separately
            rows.append({'title': s['title'], **compare(g, p)})
        reports[arm] = dict(summary=aggregate(rows), rows=rows)
    if len({r['title'] for r in reports['engine']['rows']}) != len(gold):
        raise ValueError('duplicate_gold_title')
    rng = random.Random(20261006)
    er, br = reports['engine']['rows'], reports['baseline']['rows']
    intervals = []
    for _ in range(2000):
        indices = [rng.randrange(len(gold)) for _ in gold]
        den = sum(er[i]['gold'] for i in indices)
        intervals.append(sum(er[i]['triad'] - br[i]['triad'] for i in indices) / den if den else 0)
    intervals.sort()
    delta = reports['engine']['summary']['triad'] - reports['baseline']['summary']['triad']
    completed = {a: sum(r.get('status') == 'complete' for r in statuses[a]) for a in submissions}
    numerical_gate = (delta >= .05 and intervals[50] > 0 and
                      reports['engine']['summary']['root'] >= reports['baseline']['summary']['root'] and
                      completed['engine'] >= completed['baseline'])
    result = dict(scorer_version=SCORER_VERSION, reports=reports, completed_songs=completed,
                  triad_delta=delta, paired_bootstrap_95_ci=[intervals[50], intervals[1949]],
                  bootstrap_samples=2000, bootstrap_seed=20261006,
                  numerical_gate_passed=numerical_gate,
                  decision='experimental_connection_candidate' if numerical_gate else 'do_not_connect',
                  no_whole_score_solution_is_not_measured_local_chord_accuracy=True)
    write(output, result)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--worker', required=True)
    ap.add_argument('--arm', choices=('engine', 'baseline'), required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    worker(args.worker, args.arm, args.output)


if __name__ == '__main__':
    main()
