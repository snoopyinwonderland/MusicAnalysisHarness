"""Offline sparse-cell support experiment. No annotation/key/phrase inputs.

Keep v0.3 complete-cell evidence. Only otherwise abstaining cells may borrow
one score-aligned, same-measure window. Charge its regret once per base cell,
not once per overlapping window. An eligible shape is evidence, not truth.
"""
from fractions import Fraction
from .formal_ir import q
from .harmony_joint import analyze_joint, candidates, prepare, f
from .harmony_temporal_shadow import bass_path
from .harmony_bass import attach_bass
from .harmony_applied_context import attach_applied_context
from .harmony_boundary_contrast import contrast_blocks, contrast_penalty, observation

VERSION = 'multiscale-support-shadow-0.5.0'
POLICY = {
    'base_cell_denominator_beats': '1/2',
    'additional_window_denominator_beats': [1, 2],
    'missing_fifth_qualities': ['dominant7', 'major7', 'minor7'],
    'window_origin': 'original_measure',
    'cross_silence': False,
    'regret_weight': 1,
    'only_supplement_legacy_abstentions': True,
    'production_enabled': False,
}


def shape_reason(candidate, observed):
    """Never waive the third/root or the quality-bearing diminished fifth."""
    if candidate['root'] is None or not observed:
        return None
    pcs = set(candidate['pcs'])
    if not observed <= pcs:
        return None
    missing = pcs-observed
    if not missing:
        return 'complete_shape'
    quality = candidate['label'].partition(':')[2]
    if quality in POLICY['missing_fifth_qualities'] and missing == {(candidate['root']+7) % 12}:
        return 'seventh_missing_only_fifth'
    return None


def continuous_sound(rows, start, end):
    cursor = start
    for row in sorted(rows, key=lambda r: r['start']):
        if row['end'] <= cursor:
            continue
        if row['start'] > cursor:
            return False
        cursor = max(cursor, row['end'])
        if cursor >= end:
            return True
    return False


def provider(measures=None, *, enable_distributed=True, enable_missing_fifth=True, enable_boundary_contrast=False):
    if any(type(s) is not bool for s in (enable_distributed,enable_missing_fifth,enable_boundary_contrast)):
        raise ValueError('ablation_switches_must_be_boolean')
    grids = sorted({(f(m['global_start_quarter']), Fraction(4, m['time_signature']['beat_type']))
                    for m in (measures or [])})
    cache = {}
    contrasts = None

    def inspect(rows, neighbors, a, b, beat):
        key = (a, b, beat)
        if key not in cache:
            active = [r for r in rows if r['start'] < b and r['end'] > a]
            observed = {r['pitch'] % 12 for r in active}
            local = candidates(rows, neighbors, a, b, beat, limit=None, min_shared_pcs=0)
            best = local[0]
            tied_best = [c for c in local if abs(c['cost']-best['cost']) < 1e-12]
            # Do not promote a worse eligible template to manufacture support.
            eligible = [(c, shape_reason(c, observed)) for c in tied_best]
            eligible = [(c, why) for c, why in eligible if why and
                        (enable_missing_fifth or why != 'seventh_missing_only_fifth')]
            legacy = (len(observed) >= 3 and best['root'] is not None and best.get('coverage', 0) == 1)
            supplemental = bool(eligible) and continuous_sound(active, a, b)
            cache[key] = (local, observed, active, legacy, supplemental, eligible)
        return cache[key]

    def choose(rows, neighbors, start, end, beat, limit=5):
        nonlocal contrasts
        if contrasts is None:
            contrasts=contrast_blocks(rows,measures or []) if enable_boundary_contrast else []
            choose.boundary_contrasts=contrasts
        choices = candidates(rows, neighbors, start, end, beat, limit=None)
        anchors = []
        x = start
        while x < end:
            origin, unit = next(((a, u) for a, u in reversed(grids) if a <= x), (Fraction(0), beat))
            next_measure = next((a for a, _ in grids if a > x), end)
            y = min(end, next_measure, origin+((x-origin)//(unit/2)+1)*(unit/2))
            support = inspect(rows, neighbors, x, y, unit)
            a, b = x, y
            if support[3]:
                reason = 'legacy_complete_cell'
            elif support[4]:
                reason = 'supplemental_base_cell'
            else:
                reason = None
                # No borrowing across a segment or measure boundary; shortest first.
                for width in ((unit, 2*unit) if enable_distributed else ()):
                    wa = max(start, origin+((x-origin)//width)*width)
                    wb = min(end, next_measure, origin+((x-origin)//width+1)*width)
                    if wa == x and wb == y:
                        continue
                    trial = inspect(rows, neighbors, wa, wb, unit)
                    if trial[4]:
                        support, a, b, reason = trial, wa, wb, 'supplemental_distributed_window'
                        break
            if reason:
                local, observed, active, _, _, eligible = support
                anchors.append((x, y, a, b, local, {
                    'cell_span': {'start': q(x), 'end': q(y)},
                    'support_span': {'start': q(a), 'end': q(b)},
                    'reason': reason,
                    'observed_pitch_classes': sorted(observed),
                    'event_refs': sorted(r['id'] for r in active),
                    'qualifying_best_shapes': [{'label': c['label'], 'reason': why,
                        'missing_pitch_classes': sorted(set(c['pcs'])-observed)} for c, why in eligible],
                }))
            x = y
        result = []
        for c in choices:
            penalty, evidence = 0.0, []
            if c['root'] is not None:
                for x, y, a, b, local, anchor in anchors:
                    fit = next(t for t in local if t['label'] == c['label'])
                    regret = max(0, fit['cost']-local[0]['cost'])
                    weight = float((y-x)/(end-start))
                    penalty += weight*regret
                    evidence.append({**anchor, 'weight': weight, 'regret': regret,
                                     'best_cost': local[0]['cost'], 'candidate_cost': fit['cost']})
            contrast,contrast_evidence=contrast_penalty(c,start,end,contrasts)
            result.append({**c, 'pooled_cost': c['cost'], 'cost': c['cost']+penalty+contrast,
                           'boundary_contrast_cost':contrast,'boundary_contrast_evidence':contrast_evidence,
                           'temporal_regret': penalty, 'temporal_evidence': evidence})
        return sorted(result, key=lambda c: (c['cost'], c['label']))[:limit]
    choose.boundary_contrasts=[]
    return choose


def analyze(ir, analysis_span=None, *, enable_distributed=True, enable_missing_fifth=True, enable_boundary_contrast=True):
    switches = {'enable_distributed': enable_distributed, 'enable_missing_fifth': enable_missing_fifth,
                'enable_boundary_contrast':enable_boundary_contrast}
    choose=provider(ir.get('measures', []), **switches)
    result = analyze_joint(ir, candidate_provider=choose, analysis_span=analysis_span)
    result['boundary_contrast_candidates']=[observation(c) for c in choose.boundary_contrasts]
    result.update(engine_version=VERSION, production_enabled=False, policy={**POLICY, **switches},
                  source_labels_used_for_inference=False, accuracy_measured=False)
    rows, _ = prepare(ir)
    for segment in result['segments']:
        segment['bass_path_evidence'] = bass_path(rows, segment)
        segment['boundary_contrast_at_start']=[c for c in result['boundary_contrast_candidates'] if c['boundary']==segment['span']['start']]
    result.setdefault('limitations', []).extend([
        'Fixed score-grid windows can straddle a real harmonic change',
        'Missing fifth does not imply a verified seventh chord or function',
        'No missing-root/third inference; no new NCT categories',
        'Denominator beat is not necessarily perceived pulse; uncalibrated shadow only',
    ])
    return attach_applied_context(ir, attach_bass(ir, result))
