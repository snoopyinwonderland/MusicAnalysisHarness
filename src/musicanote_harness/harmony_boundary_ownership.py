"""Bounded common-tone onset alternatives, never automatic boundary correction.

The selected path stays authoritative for existing consumers. This research
review layer compares complete, locally substituted paths under the unchanged
v0.5 objective. No source annotation, fixture intention, or phrase is an input.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json

from .formal_ir import q
from .harmony_joint import f, prepare
from .harmony_multiscale_shadow import VERSION as ENGINE_VERSION, provider, continuous_sound
from .harmony_candidate_explanation import explain_path, spelling_evidence

VERSION = 'common-tone-ownership-review-0.1.0'
POLICY = {
    'max_backward_denominator_beats': 2,
    'max_completion_denominator_beats': 2,
    'same_measure_only': True,
    'require_attacked_lowest_root': True,
    'require_complete_spelled_shape': True,
    'automatic_selection': False,
    'production_enabled': False,
}


def span(a, b):
    return {'start': q(a), 'end': q(b)}


def active(rows, a, b):
    return [r for r in rows if r['start'] < b and r['end'] > a]


def review(ir, result, *, diagnostics=None):
    """Return competing paths, leaving Core and selected analysis unmodified.

    Intentionally narrow v0.1: at an existing boundary only, look back for an
    attacked common root. The enlarged right window must complete a strictly
    spelled chord and introduce a pitch outside the previous chord. It cannot
    cross silence or the original measure. Each alternative replaces one pair;
    alternatives at different boundaries are NOT jointly optimized.
    """
    if result.get('engine_version') != ENGINE_VERSION:
        raise ValueError('unsupported_baseline_engine')
    selected = result['segments']
    if not selected:
        return {'version': VERSION, 'policy': POLICY.copy(), 'alternatives': [], 'selected_path_changed': False}
    baseline_cost = explain_path(result)['reconstructed_path_cost']
    cursor = f(selected[0]['span']['start'])
    for s in selected:
        a, b = f(s['span']['start']), f(s['span']['end'])
        if a != cursor or b <= a:
            raise ValueError('invalid_selected_partition')
        cursor = b
    switches = {k: result['policy'][k] for k in
                ('enable_distributed', 'enable_missing_fifth', 'enable_boundary_contrast')}
    choose = provider(ir.get('measures', []), **switches)
    rows, neighbors = prepare(ir)
    window_start, window_end = f(selected[0]['span']['start']), cursor
    rows = active(rows, window_start, window_end)
    measures = sorted(ir.get('measures', []), key=lambda m: f(m['global_start_quarter']))
    alternatives = []
    def trace(kind, reason, index, **detail):
        if diagnostics is not None:
            diagnostics.append({'diagnostic_version': 'ownership-gates-0.1.0',
                                'kind': kind, 'reason': reason, 'boundary_index': index, **detail})
    for index in range(1, len(selected)):
        left, right = selected[index-1:index+1]
        old = left['selected']
        if old['root'] is None or right['selected']['root'] is None:
            trace('boundary', 'unpitched_or_unknown_side', index)
            continue
        start, boundary, end = f(left['span']['start']), f(right['span']['start']), f(right['span']['end'])
        measure = next((m for m in reversed(measures) if f(m['global_start_quarter']) <= boundary), None)
        if measure is None:
            trace('boundary', 'missing_measure', index, boundary=q(boundary))
            continue
        origin = f(measure['global_start_quarter'])
        measure_end = origin + f(measure['actual_duration_quarter'])
        unit = Fraction(4, measure['time_signature']['beat_type'])
        old_pcs = set(old['pcs'])
        starts = sorted({r['start'] for r in rows if max(start, origin, boundary-2*unit) <= r['start'] < boundary
                         and r['start'] > start})
        trace('boundary', 'eligible' if starts else 'no_earlier_attack_within_measure_and_bound', index,
              boundary=q(boundary), previous_span=left['span'], next_span=right['span'],
              measure_start=q(origin), beat_unit=q(unit), considered_onsets=[q(a) for a in starts])
        for onset in starts:
            detail = {'onset': q(onset), 'boundary': q(boundary), 'previous_label': old['label'],
                      'next_label': right['selected']['label']}
            completion_end = min(end, measure_end, onset+2*unit)
            if completion_end <= boundary:
                trace('onset', 'completion_window_ends_before_new_evidence', index, **detail)
                continue
            prefix = active(rows, onset, boundary)
            prefix_pcs = {r['pitch'] % 12 for r in prefix}
            support = active(rows, onset, completion_end)
            observed = {r['pitch'] % 12 for r in support}
            detail.update(prefix_pitch_classes=sorted(prefix_pcs), support_pitch_classes=sorted(observed),
                          previous_pitch_classes=sorted(old_pcs),
                          prefix_event_refs=sorted(r['id'] for r in prefix),
                          support_event_refs=sorted(r['id'] for r in support))
            if not prefix_pcs or not prefix_pcs <= old_pcs or not (observed-old_pcs):
                reason = ('empty_prefix' if not prefix_pcs else 'prefix_outside_previous_chord'
                          if not prefix_pcs <= old_pcs else 'no_new_pitch_class')
                trace('onset', reason, index, **detail)
                continue
            if not continuous_sound(support, onset, completion_end):
                trace('onset', 'silence_in_completion_window', index, **detail)
                continue
            at_onset = [r for r in rows if r['start'] <= onset < r['end']]
            lowest = min(r['pitch'] for r in at_onset)
            roots = [r for r in at_onset if r['start'] == onset and r['pitch'] == lowest]
            root = lowest % 12
            detail.update(lowest_midi=lowest, attacked_lowest_refs=sorted(r['id'] for r in roots))
            if not roots or root == old['root'] or root not in old_pcs:
                reason = ('lowest_not_attacked' if not roots else 'lowest_is_previous_root'
                          if root == old['root'] else 'lowest_not_previous_chord_member')
                trace('onset', reason, index, **detail)
                continue
            new_left = next((c for c in choose(rows, neighbors, start, onset, f(left['beat_unit_quarter']), limit=None)
                             if c['label'] == old['label'] and c.get('coverage') == 1), None)
            if new_left is None:
                trace('onset', 'shortened_previous_chord_incomplete', index, **detail)
                continue
            # Candidate completeness is checked on bounded evidence, not the
            # possibly much longer right segment. No missing-root speculation.
            gate_counts = {'complete_lowest_root_shape': 0, 'whole_right_span_fits': 0,
                           'prefix_fits': 0, 'spelling_valid': 0, 'new_member_attacks': 0}
            accepted_before = len(alternatives)
            for candidate in choose(rows, neighbors, onset, end, unit, limit=None):
                if candidate['root'] != root or set(candidate['pcs']) != observed:
                    continue
                gate_counts['complete_lowest_root_shape'] += 1
                if any(r['pitch'] % 12 not in candidate['pcs'] for r in active(rows, onset, end)):
                    continue
                gate_counts['whole_right_span_fits'] += 1
                if not prefix_pcs <= set(candidate['pcs']):
                    continue
                gate_counts['prefix_fits'] += 1
                spelling = spelling_evidence(ir, span(onset, completion_end), candidate)
                readings = spelling['candidates']
                if (spelling['unsupported_pitch_event_refs'] or len(readings) != 1 or
                        readings[0]['conflicting_event_refs'] or readings[0]['missing_member_pcs']):
                    continue
                gate_counts['spelling_valid'] += 1
                previous_bass = [r['pitch'] for r in rows if r['start'] < onset and r['end'] >= onset]
                bass_motion = lowest-min(previous_bass) if previous_bass else None
                crossing = [r['id'] for r in at_onset if r['start'] < onset]
                new_members = [r for r in support if r['start'] >= boundary and r['pitch'] % 12 not in old_pcs]
                evidence = {
                    'prefix_span': span(onset, boundary), 'completion_span': span(onset, completion_end),
                    'root_attack_refs': sorted(r['id'] for r in roots),
                    'prefix_event_refs': sorted(r['id'] for r in prefix),
                    'completion_event_refs': sorted(r['id'] for r in support),
                    'new_member_attack_refs': sorted(r['id'] for r in new_members),
                    'common_pitch_classes': sorted(prefix_pcs), 'complete_pitch_classes': sorted(observed),
                    'bass_motion_semitones': bass_motion,
                    'register_reset_downward': bass_motion is not None and bass_motion <= -3,
                    'denominator_grid_aligned': (onset-origin) % unit == 0,
                    'backward_denominator_beats': q((boundary-onset)/unit),
                    'carried_event_refs': sorted(crossing), 'spelling': spelling,
                }
                if not new_members:
                    continue
                gate_counts['new_member_attacks'] += 1
                replacement = [
                    {'span': span(start, onset), 'selected': new_left, 'beat_unit_quarter': left['beat_unit_quarter'], 'status': 'hypothesis'},
                    {'span': span(onset, end), 'selected': candidate, 'beat_unit_quarter': q(unit), 'status': 'hypothesis'},
                ]
                path = deepcopy(selected[:index-1])+replacement+deepcopy(selected[index+1:])
                # Includes transitions to the next untouched segment; pair-only
                # scoring would hide a cost changed by the revised right chord.
                explained = explain_path({'segments': path}, verify=False)
                cost = explained['reconstructed_path_cost']
                counter = ['common_prefix_also_fits_previous_chord',
                           'anticipation_or_pedal_not_ruled_out', 'no_joint_multi_boundary_optimization']
                if boundary-onset > unit:
                    counter.append('quality_arrives_more_than_one_denominator_beat_later')
                if crossing:
                    counter.append('prior_sound_continues_across_proposed_start')
                identity = {'version': VERSION, 'index': index, 'boundary': q(boundary), 'onset': q(onset),
                            'label': candidate['label'], 'refs': evidence['completion_event_refs']}
                aid = 'ownership_'+hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
                alternatives.append({
                    'alternative_id': aid, 'boundary_index': index, 'current_boundary': q(boundary),
                    'proposed_boundary': q(onset), 'current_right_label': right['selected']['label'],
                    'proposed_right_label': candidate['label'], 'status': 'review_candidate_not_selected',
                    'evidence': evidence, 'counterevidence': counter,
                    'baseline_path_cost': baseline_cost, 'alternative_path_cost': cost,
                    'cost_delta': cost-baseline_cost, 'cost_interpretation': 'heuristic_not_probability',
                    'path_cost_explanation': explained, 'alternative_segments': path,
                })
            trace('onset', 'accepted_alternative' if len(alternatives)>accepted_before else
                  'candidate_rejected_at_'+next(k for k,v in gate_counts.items() if not v),
                  index, **detail, candidate_gate_counts=gate_counts,
                  alternative_ids=[a['alternative_id'] for a in alternatives[accepted_before:]])
    alternatives.sort(key=lambda a: (a['boundary_index'], a['cost_delta'], a['alternative_id']))
    return {'version': VERSION, 'baseline_engine': ENGINE_VERSION, 'policy': POLICY.copy(),
            'source_labels_used_for_inference': False, 'selected_path_changed': False,
            'alternatives': alternatives,
            'limitations': ['Only already selected adjacent boundaries are reviewed',
                            'No crossing measure, silence, or analysis window',
                            'Strict root/third/fifth/seventh spelling; no missing-tone or NCT exemption',
                            'Common-tone root-position restart only; inverted starts may be missed',
                            'Alternative recall is not improved selected-path accuracy']}
