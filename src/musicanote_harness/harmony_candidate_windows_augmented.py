"""Additive augmented-sixth adapter using caller-supplied candidate windows.

The original provider's candidate construction and payload are preserved;
only its two window calculations are supplied by the caller instead.
"""
from .harmony_augmented_candidates import (
    VERSION, FAMILIES, f, offset, hypothesis, theory_observe, token,
)


def from_windows(ir, span, context_span, base, context):
    context_span = context_span or span
    if not (0 <= f(context_span['start']) <= f(span['start']) < f(span['end']) <= f(context_span['end'])):
        raise ValueError('invalid_context')
    blockers = sorted(set(base['abstention_reasons'] + context['abstention_reasons']))
    units = base['event_units']
    candidates = []
    # Unsupported timing/spelling cannot establish an exact-spelled pair.
    if not {'unsupported_pitch', 'grace_timing'} & set(blockers):
        spelling = {sid: (u['pitch']['step'], int(f(u['pitch']['alter']))) for sid, u in units.items()}
        observed = set(spelling.values())
        for flat6 in sorted(observed):
            tonic = offset(flat6, -5, -8)
            for family in FAMILIES:
                # Major and minor yield identical shapes. 'major' is only the
                # legacy theory constructor's coordinate, never an inferred mode.
                h = hypothesis((*tonic, 'major'), family)
                if tuple(h['roles']['sharp4']) not in observed:
                    continue
                expected = {tuple(p) for p in h['members']}
                states = {sid: 'member' if p in expected else 'nonmember_not_confirmed_nct'
                          for sid, p in spelling.items()}
                cells = []
                for cell in base['cells']:
                    actual = {spelling[sid] for sid in cell['event_refs']}
                    bass = {spelling[sid] for sid in cell['bass_refs']}
                    cells.append({'span': cell['span'], 'event_refs': cell['event_refs'],
                        'all_members_present': expected <= actual,
                        'exact_family_only': actual == expected,
                        'bass_refs': cell['bass_refs'],
                        'bass_member_roles': sorted(k for k, p in h['roles'].items() if tuple(p) in bass),
                        'bass_outside_family': bool(bass - expected)})
                evidence = None
                if not blockers:
                    legacy = theory_observe(ir, span, context_span, h)
                    # Do not leak its supplied key/bass assumptions as observations.
                    evidence = {k: legacy[k] for k in ('version', 'critical_paths', 'joint_geometry')}
                    evidence['basis'] = 'conditional_on_proposed_tonic_and_family_not_a_key_verdict'
                candidates.append({'candidate_id': 'aug6_' + token([base['window_id'], tonic, family]),
                    'family': family, 'tonic_coordinate': tonic, 'mode': None,
                    'compatible_modes': ['major', 'minor'], 'root': None,
                    'roles': h['roles'], 'members': h['members'],
                    'critical_pair_refs': {role: sorted(sid for sid, p in spelling.items() if p == tuple(h['roles'][role]))
                                           for role in ('flat6', 'sharp4')},
                    'missing_spellings': [list(p) for p in sorted(expected - observed)],
                    'extra_spellings': [list(p) for p in sorted(observed - expected)],
                    'event_states': states, 'pooled_complete': expected <= observed,
                    'simultaneous_complete': any(c['all_members_present'] for c in cells),
                    'cells': cells, 'context_evidence': evidence,
                    'abstention_reasons': blockers, 'selected': None, 'function': None})
    return {'version': VERSION, 'span': span, 'context_span': context_span,
        'base_window': base, 'augmented_sixth_candidates': candidates,
        'abstention_reasons': blockers, 'source_labels_used': False,
        'selected': None, 'production_enabled': False,
        'limits': ['Critical pair proposes a coordinate; no inferred local key or function.',
                   'Window pooling does not establish simultaneity or a single harmony.',
                   'Missing critical member prevents proposal; enharmonic respelling is not inferred.',
                   'No root, confidence, NCT, cadence, boundary or ranking verdict.',
                   'Direct unique-voice resolution evidence only; polyphonic voices may abstain.',
                   'Separate candidate extension; legacy template scorers are not generalized yet.']}
