"""Source-only seventh-release evidence, not a chord boundary or NCT label.

Inspect a completed union run. A previously sounding seventh can disappear
while the underlying spelled triad continues. Keep one local notated beat of
allowance for distributed presentation, using the original sounding releases
(including ties), not attack-only durations. Never charge a never-heard seventh
again. This module does not fit weights, select chords or alter old scorers.
"""
from fractions import Fraction as F

from .harmony_support_balance import roles
from .harmony_temporal_scoring import beat_extent
from .harmony_joint_nct_scoring import completed_runs
from .harmony_candidate_recall import rational as q

VERSION = 'harmony-seventh-release-evidence-0.1.0'
FEATURE = 'supported_triad_seventh_release_tail'
ALLOWANCE_BEATS = F(1)


def observe(problem, ev, start, end, signature, *, history_gate=None):
    """Return a Fraction or None, with all source witnesses and assumptions.

    Support is the union of positive sounding spans, not a simultaneous chord.
    Reappearance of a seventh resets the terminal tail. Silence, a different
    bass, or a missing triad member does not become a confirmed new harmony.
    """
    if not problem.points[0] <= start < end <= problem.points[-1]:
        raise ValueError('invalid_member_release_span')
    selected_roles = roles(signature)
    active = tuple(r for r in ev.rows if r['start'] < r['end'] and r['start'] < end and start < r['end'])
    receipt = dict(version=VERSION, kind='seventh_release_tail_observation',
        span=dict(start=q(start), end=q(end)), root_spelling=signature[0], members=signature[1],
        allowance_beats=q(ALLOWANCE_BEATS), source_ir_content_sha256=ev.source.source_ir_content_sha256,
        source_event_ids=sorted(r['id'] for r in active),
        source_note_ids={r['id']: list(r['source_note_ids']) for r in active},
        interpretation='possible_change_in_supported_chord_content',
        confirmed_boundary=False, confirmed_nct=False, function_confirmed=False,
        simultaneous_triad_required=False, omission_prohibited=False,
        source_labels_used=False, score_changed=False, feature=None,
        seventh_event_ids=[], tail_support_event_ids=[], last_seventh_release=None,
        tail_span=None, tail_beats=None, complete_triad_union_in_tail=False)

    def finish(value, reason):
        receipt.update(feature=None if value is None else q(value), availability=value is not None,
                       reason=reason)
        return value, receipt

    if selected_roles is None:
        return finish(None, 'unsupported_literal_tertian_shape')
    # Non-seventh hypotheses have known zero, not an unsupported latent seventh.
    if selected_roles[2] is None:
        return finish(F(), 'no_seventh_in_this_hypothesis')
    if not active or any(not r['clock_valid'] or r['token'] is None for r in active):
        return finish(None, 'unavailable_positive_source_clock_or_pitch')
    if history_gate is not None and not history_gate(start, end):
        return finish(None, 'source_clock_gate_rejected')
    sevenths = tuple(r for r in active if r['token'] == selected_roles[2])
    receipt['seventh_event_ids'] = sorted(r['id'] for r in sevenths)
    if not sevenths:
        return finish(F(), 'never_heard_seventh_left_to_existing_absence_feature')
    release = min(end, max(r['end'] for r in sevenths))
    receipt['last_seventh_release'] = q(release)
    if release == end:
        return finish(F(), 'seventh_still_sounding_at_run_end')
    receipt['tail_span'] = dict(start=q(release), end=q(end))
    tail = tuple(r for r in active if r['start'] < end and release < r['end'])
    triad = set(signature[1]) - {selected_roles[2]}
    support = tuple(r for r in tail if r['token'] in triad)
    receipt['tail_support_event_ids'] = sorted(r['id'] for r in support)
    complete = (triad <= {r['token'] for r in support}
                and any(r['end'] >= end for r in support))
    receipt['complete_triad_union_in_tail'] = complete
    if not complete:
        return finish(F(), 'no_complete_triad_union_after_seventh_release')
    total_beats = beat_extent(ev.source, problem.points[0], problem.points[-1])
    tail_beats = beat_extent(ev.source, release, end)
    receipt['tail_beats'] = None if tail_beats is None else q(tail_beats)
    if total_beats is None or tail_beats is None:
        return finish(None, 'unknown_meter_not_imputed')
    if total_beats <= 0:
        raise ValueError('invalid_member_release_beat_domain')
    value = max(F(), tail_beats - ALLOWANCE_BEATS) / total_beats
    receipt['normalization_scope_beats'] = q(total_beats)
    return finish(value, 'triad_supported_tail_with_one_beat_allowance')


def observe_path(problem, ev, ids, *, history_gate=None):
    """Coalesce identical adjacent signatures; raw XML cuts cannot add cost."""
    observations = [observe(problem, ev, a, b, sig, history_gate=history_gate)
                    for a, b, sig in completed_runs(problem, ids)]
    known = sum((v for v, _ in observations if v is not None), F())
    available = all(v is not None for v, _ in observations)
    return dict(version=VERSION, feature_name=FEATURE,
        known_partial_sum=q(known), availability=available,
        feature=q(known) if available else None,
        observations=[r for _, r in observations],
        source_labels_used=False, coefficients_fitted=False, score_changed=False,
        whole_path_unknown_is_not_zero=True, confirmed_nct=False)
