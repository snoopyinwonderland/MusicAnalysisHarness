"""Ordered attack paths and chord-conditioned explanations, never NCT truth.

Textbook geometry is reused from counterpoint_evidence. The saved harmonic
context is a hypothesis, not a gold annotation or an independent vote.
"""
from collections import Counter, defaultdict
import hashlib
import json

from .formal_ir import q
from .harmony_joint import f
from .harmony_reading_voice_context import spelled_height
from .counterpoint_evidence import melodic_geometry
from .harmony_candidate_explanation import spelling_evidence

VERSION = 'intervening-path-explanation-0.1.0'


def assess(ir, observed, counterevidence, roles, contexts):
    sounds = {s['sounding_event_id']: s for s in ir['sounding_events']}
    notes = {n['note_id']: n for n in ir['note_events']}
    groups = {g['group_id']: g for g in observed['groups']}
    spans = [(f(c['start']), f(c['end'])) for c in contexts]
    if any(a < 0 or b <= a for a, b in spans):
        raise ValueError('invalid_context')

    def lane(s):
        ns = [notes.get(n) for n in s.get('source_note_ids', [])]
        keys = {(n.get('part_id'), n.get('voice_id')) for n in ns if n}
        return next(iter(keys)) if ns and all(ns) and len(keys) == 1 and all(next(iter(keys))) else None

    by_lane = defaultdict(list)
    for s in sounds.values():
        if lane(s):
            by_lane[lane(s)].append(s)
    condition_cache = {}
    rows = []
    for prior in counterevidence['records']:
        src, dst = [sounds[sid] for sid in prior['source_refs']]
        group = groups[prior['group_id']]
        a, first, stop = f(src['span']['start']), f(group['first_attack']), f(dst['span']['end'])
        target_onset = f(dst['span']['start'])
        identity = lane(src)
        pool = by_lane[identity] if identity and identity == lane(dst) else []
        timeline = sorted((s for s in pool if f(s['span']['start']) < stop and f(s['span']['end']) > a),
                          key=lambda s: (f(s['span']['start']), s['sounding_event_id']))
        arrivals = [s for s in timeline if first <= f(s['span']['start']) <= target_onset]
        ordered = defaultdict(list)
        for s in timeline:
            ordered[f(s['span']['start'])].append(s['sounding_event_id'])
        blockers = []
        if not pool:
            blockers.append('missing_or_cross_lane_identity')
        if not any(x <= a and stop <= y for x, y in spans):
            blockers.append('full_path_outside_frozen_context')
        if any(spelled_height(s['pitch']) is None for s in timeline):
            blockers.append('unsupported_or_inconsistent_pitch_spelling')
        if any(f(s['span']['end']) <= f(s['span']['start']) for s in arrivals):
            blockers.append('nonpositive_duration')
        if identity and any(n.get('part_id') == identity[0] and n.get('voice_id') == identity[1]
               and n.get('grace', {}).get('is_grace') and a <= f(n['global_onset_quarter']) < stop
               for n in notes.values()):
            blockers.append('grace_timing_unresolved')
        # Do not sort simultaneous notes by pitch into a fictional melody.
        if any(s['sounding_event_id'] != t['sounding_event_id']
               and f(s['span']['start']) < f(t['span']['end'])
               and f(t['span']['start']) < f(s['span']['end'])
               for s in arrivals for t in timeline):
            blockers.append('arrival_polyphony_or_sustained_overlap')
        crossed = [m for m in ir.get('measures', []) if a < f(m['global_start_quarter']) < stop]
        initial = max((m for m in ir.get('measures', []) if f(m['global_start_quarter']) <= a),
                      key=lambda m: f(m['global_start_quarter']), default=None)
        if initial is None or any(m['time_signature'] != initial['time_signature'] for m in crossed):
            blockers.append('meter_unavailable_or_changed')
        for m in ir.get('measures', []):
            bar = m.get('repeat_barline') or {}
            t = f(m['global_start_quarter']) + (0 if bar.get('location') == 'left' else f(m['actual_duration_quarter']))
            if a < t < stop and any(bar.get(k) for k in ('repeat_direction', 'ending_number')):
                blockers.append('repeat_or_ending_barrier')
                break
        gaps = [{'after_ref': s['sounding_event_id'], 'before_ref': t['sounding_event_id'],
                 'span': {'start': s['span']['end'], 'end': t['span']['start']}}
                for s, t in zip(arrivals, arrivals[1:]) if f(s['span']['end']) < f(t['span']['start'])]
        rest_refs = [r['rest_id'] for r in ir.get('rest_events', [])
                     if (r.get('part_id'), r.get('voice_id')) == identity
                     and f(r['global_onset_quarter']) < stop
                     and f(r['global_onset_quarter']) + f(r['notated_duration_quarter']) > a]
        geometry = []
        if not blockers:
            for left, middle, right in zip(arrivals, arrivals[1:], arrivals[2:]):
                if f(left['span']['end']) != f(middle['span']['start']) or f(middle['span']['end']) != f(right['span']['start']):
                    continue
                triples = [left, middle, right]
                ps = [(s['pitch']['step'], int(f(s['pitch']['alter'])), s['pitch']['octave']) for s in triples]
                shape = melodic_geometry(ps)
                geometry.append({'event_refs': [s['sounding_event_id'] for s in triples],
                                 'pattern': shape['pattern'], 'nct_label': None})

        # Deduplicate overlapping explanations; provenance is not a vote count.
        conditions = {}
        for role in roles:
            for comp in role['comparisons']:
                if comp['group_id'] != prior['group_id'] or comp['source_refs'] != prior['source_refs']:
                    continue
                ctx = comp['target_chord_context']
                candidate = ctx['candidate']
                key = json.dumps([ctx['span'], candidate['root'], candidate['label'], sorted(candidate['pcs'])], sort_keys=True)
                entry = conditions.setdefault(key, {'span': ctx['span'], 'candidate': {
                    k: candidate[k] for k in ('root', 'label', 'pcs')}, 'provenance': []})
                ref = {'candidate_ref': role['candidate_ref'], 'reading_type': comp['reading_type'], 'reading_index': comp['reading_index']}
                if ref not in entry['provenance']:
                    entry['provenance'].append(ref)
        explanations = []
        for key, cond in sorted(conditions.items()):
            candidate = cond['candidate']; x, y = f(cond['span']['start']), f(cond['span']['end'])
            if key not in condition_cache:
                condition_cache[key] = spelling_evidence(ir, cond['span'], candidate)
            spelling = condition_cache[key]
            # One coherent root spelling must support all relevant members.
            member_ids = {s['sounding_event_id'] for s in arrivals if s['pitch']['midi_pitch'] % 12 in candidate['pcs']}
            coherent = [c for c in spelling['candidates'] if member_ids <= set(c['supported_event_refs'])]
            fully_covered = bool(arrivals) and all(x <= f(s['span']['start']) and f(s['span']['end']) <= y for s in arrivals)
            checks = [{'event_ref': s['sounding_event_id'], 'pc_member': s['pitch']['midi_pitch'] % 12 in candidate['pcs'],
                       'fully_in_context': x <= f(s['span']['start']) and f(s['span']['end']) <= y} for s in arrivals]
            tags = []; ornaments = []
            eligible = not blockers and fully_covered and bool(coherent)
            if eligible:
                if not gaps and len(arrivals) >= 3 and len(member_ids) == len(arrivals) and len({s['pitch']['midi_pitch'] % 12 for s in arrivals}) >= 3:
                    tags.append('chord_member_unfolding_compatible')
                for g in geometry:
                    left, middle, right = g['event_refs']
                    if g['pattern'] and left in member_ids and right in member_ids and middle not in member_ids:
                        ornaments.append({**g, 'conditional_role': g['pattern'].replace('_geometry', '_candidate'),
                                          'status': 'conditional_on_one_sustained_chord_not_confirmed_nct'})
                if ornaments:
                    tags.append('local_ornament_geometry_compatible')
            explanations.append({**cond, 'arrival_covered': fully_covered, 'membership': checks,
                'coherent_root_spellings': [c['root_spelling'] for c in coherent],
                'spelling_evidence': spelling, 'compatible_patterns': tags, 'conditional_ornaments': ornaments,
                'unexplained_nonmember_refs': sorted({s['sounding_event_id'] for s in arrivals} - member_ids - {o['event_refs'][1] for o in ornaments}),
                'status': 'conditional_explanation_only' if eligible else 'abstain_incomplete_context_spelling_or_path',
                'independent_vote': False, 'selected': None})
        event_refs = [s['sounding_event_id'] for s in timeline]
        rows.append({'path_id': 'ipath_' + hashlib.sha256(json.dumps([prior['group_id'], prior['source_refs']]).encode()).hexdigest()[:20],
            'group_id': prior['group_id'], 'source_refs': prior['source_refs'], 'span': {'start': q(a), 'end': q(stop)},
            'events': [{'event_ref': s['sounding_event_id'], 'pitch': s['pitch'], 'span': s['span'], 'source_note_ids': s['source_note_ids']} for s in timeline],
            'attack_groups': [{'onset': q(t), 'event_refs': ids} for t, ids in sorted(ordered.items())],
            'arrival_event_refs': [s['sounding_event_id'] for s in arrivals], 'initial_gap': {'start': src['span']['end'], 'end': q(first)},
            'arrival_gaps': gaps, 'rest_refs': rest_refs, 'abstention_reasons': blockers,
            'arrival_geometry': geometry, 'conditional_explanations': explanations,
            'prior_review_reasons': prior['review_reasons'], 'restart_alternative': bool(prior['prior_matching_patterns']),
            'earlier_target_refs': prior['earlier_identical_target_refs'],
            'all_intervening_refs_preserved': set(prior['intervening_attack_refs']) <= set(event_refs),
            'voice_connection_confirmed': False, 'nct_confirmed': False, 'independent_resolution_vote_allowed': False,
            'selected': None, 'used_for_ranking': False})
    return {'version': VERSION, 'records': rows, 'source_annotation_used': False, 'production_modified': False,
        'summary': {'paths': len(rows), 'paths_with_blockers': sum(bool(r['abstention_reasons']) for r in rows),
            'paths_with_conditioned_explanation': sum(any(e['compatible_patterns'] for e in r['conditional_explanations']) for r in rows),
            'pattern_occurrences_not_independent_votes': dict(Counter(tag for r in rows for e in r['conditional_explanations'] for tag in e['compatible_patterns']))},
        'limits': ['Arrival subpath explanation does not prove a connection across the initial rest',
            'Three-member unfolding and contiguous triples only; latent voices and compound ornaments deferred',
            'Candidate chord may be wrong; PC membership without coherent spelling never confirms a role',
            'No source/target-only shortcut, ranking change, deleted note, inferred key or confirmed NCT']}
