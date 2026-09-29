"""Label-blind, bounded delayed connection hypotheses. Never direct resolutions.

Denominator-beat units are deliberately not inferred compound-meter tactus.
Rest/silence is recorded, not removed; an empty matching always remains possible.
"""
from collections import defaultdict, Counter
import hashlib
from itertools import combinations
from fractions import Fraction
from .formal_ir import q
from .harmony_joint import f
from .harmony_polyphonic_links import partial_matchings, MAX_ENDPOINTS
from .harmony_reading_voice_context import spelled_height

VERSION = 'delayed-link-hypotheses-0.1.0'


def observe(ir, contexts):
    spans = sorted(set((f(c['start']), f(c['end'])) for c in contexts))
    if any(a < 0 or b <= a for a, b in spans): raise ValueError('invalid_context')
    notes = {n['note_id']: n for n in ir['note_events']}
    lanes = defaultdict(list); skipped = Counter()
    for s in ir['sounding_events']:
        ns = [notes.get(n) for n in s.get('source_note_ids', [])]
        keys = {(n.get('part_id'), n.get('voice_id')) for n in ns if n}
        if not ns or any(n is None for n in ns) or len(keys) != 1 or not all(next(iter(keys))):
            skipped['missing_or_cross_voice_identity'] += 1; continue
        if f(s['span']['end']) <= f(s['span']['start']):
            skipped['zero_or_negative_duration'] += 1; continue
        if any(n.get('grace', {}).get('is_grace') for n in ns):
            skipped['grace_timing_unresolved'] += 1; continue
        lanes[next(iter(keys))].append(s)
    meters = sorted(ir.get('measures', []), key=lambda m:f(m['global_start_quarter']))
    groups = []; abstentions = []; counts = Counter()
    for (part, voice), sounds in sorted(lanes.items()):
        for release in sorted({f(s['span']['end']) for s in sounds}):
            containing = [(a,b) for a,b in spans if a < release < b]
            if not containing: continue
            source = sorted((s for s in sounds if f(s['span']['end']) == release), key=lambda s:s['sounding_event_id'])
            base = {'time':q(release), 'part_id':part, 'voice_id':voice,
                    'source_refs':[s['sounding_event_id'] for s in source]}
            if any(f(s['span']['start']) == release for s in sounds):
                counts['direct_attack_left_to_direct_module'] += 1; continue
            future = sorted({f(s['span']['start']) for s in sounds if f(s['span']['start']) > release})
            current = next((m for m in reversed(meters) if f(m['global_start_quarter']) <= release), None)
            if current is None or not current.get('time_signature', {}).get('beat_type'):
                abstentions.append({**base, 'reason':'meter_unknown'}); continue
            unit = Fraction(4, current['time_signature']['beat_type'])
            if unit <= 0: raise ValueError('invalid_meter')
            first = future[0] if future else None
            if first is None or first-release > 2*unit:
                abstentions.append({**base, 'reason':'no_attack_within_two_denominator_beats'}); continue
            eligible = [b for a,b in containing if first < b]
            if not eligible:
                abstentions.append({**base, 'reason':'target_outside_same_context'}); continue
            end = min(first+unit, max(eligible))
            changes = [m for m in meters if release < f(m['global_start_quarter']) < end and m['time_signature'] != current['time_signature']]
            barriers = []
            for m in meters:
                bar = m.get('repeat_barline') or {}
                boundary = f(m['global_start_quarter'])+(0 if bar.get('location')=='left' else f(m['actual_duration_quarter']))
                if release <= boundary < end and any(bar.get(k) for k in ('repeat_direction','ending_number')):
                    barriers.append(m)
            if changes or barriers:
                abstentions.append({**base, 'reason':'meter_change_or_repeat_barrier'}); continue
            target = sorted((s for s in sounds if first <= f(s['span']['start']) < end), key=lambda s:(f(s['span']['start']),s['sounding_event_id']))
            if max(len(source),len(target)) > MAX_ENDPOINTS:
                abstentions.append({**base, 'reason':'endpoint_limit_no_silent_pruning'}); continue
            held = [s for s in sounds if f(s['span']['start']) < release < f(s['span']['end'])]
            rests = [r for r in ir.get('rest_events', []) if (r.get('part_id'),r.get('voice_id')) == (part,voice)
                     and f(r['global_onset_quarter']) < first and f(r['global_onset_quarter'])+f(r['notated_duration_quarter']) > release]
            edges = []
            for s in source:
                for d in target:
                    hs,hd = spelled_height(s['pitch']),spelled_height(d['pitch'])
                    edges.append({'source_refs':[s['sounding_event_id'],d['sounding_event_id']],
                        'source_pitch':s['pitch'], 'target_pitch':d['pitch'], 'source_span':s['span'], 'target_span':d['span'],
                        'semitones':d['pitch']['midi_pitch']-s['pitch']['midi_pitch'], 'diatonic_steps':None if hs is None or hd is None else hd-hs,
                        'delay_quarters':q(f(d['span']['start'])-release),
                        'intervening_attack_refs':[v['sounding_event_id'] for v in target if f(v['span']['start']) < f(d['span']['start'])],
                        'status':'delayed_connection_hypothesis_not_direct_resolution', 'contrapuntal_voice_identity_confirmed':False})
            target_ids = [s['sounding_event_id'] for s in target]
            edge_index = {tuple(e['source_refs']):i for i,e in enumerate(edges)}; assignments = []
            for pairs in partial_matchings(base['source_refs'],target_ids):
                indices = [edge_index[p] for p in pairs]; es = [edges[i] for i in indices]
                assignments.append({'edge_indices':indices, 'unmatched_source_refs':[s for s in base['source_refs'] if s not in {p[0] for p in pairs}],
                    'unmatched_target_refs':[s for s in target_ids if s not in {p[1] for p in pairs}],
                    'motion_semitones':sum(abs(e['semitones']) for e in es),
                    'crossing_count':sum((a['source_pitch']['midi_pitch']-b['source_pitch']['midi_pitch'])*(a['target_pitch']['midi_pitch']-b['target_pitch']['midi_pitch'])<0 for a,b in combinations(es,2)),
                    'selected':False})
            gid='dlink_'+hashlib.sha256(('|'.join([str(release),str(end),part,voice]+base['source_refs']+target_ids)).encode()).hexdigest()[:20]
            groups.append({**base, 'group_id':gid, 'target_refs':target_ids, 'held_refs':[s['sounding_event_id'] for s in held],
                'first_attack':q(first), 'target_window_end':q(end), 'window_truncated_by_context':end < first+unit,
                'beat_unit_quarter':q(unit), 'first_attack_gap_beats':q((first-release)/unit),
                'evidence_grade':'delayed_up_to_one_denominator_beat' if first-release <= unit else 'delayed_one_to_two_denominator_beats_weak',
                'rest_refs':[r['rest_id'] for r in rests], 'rest_status':'explicit_rest_observed' if rests else 'no_explicit_rest_observed_not_proof_of_continuity',
                'edges':edges, 'assignments':assignments, 'selected_assignment':None, 'harmonic_labels_used':False,
                'assignment_counts_are_confidence':False, 'eligible_as_direct_resolution':False, 'used_for_ranking':False})
    return {'version':VERSION, 'groups':groups, 'abstentions':abstentions, 'skipped_sound_reasons':dict(skipped), 'skipped_release_reasons':dict(counts),
        'source_annotations_used':False, 'production_enabled':False,
        'limits':['First next attack only; gap <= 2 denominator beats; arrival window < 1 denominator beat',
            'All intervening attacks preserved; no ornament/NCT deletion or inferred voice crossing',
            'Delayed same-voice hypotheses, not direct resolutions; no harmonic reranking',
            'No match is an explicit alternative; larger groups abstain without pruning']}
