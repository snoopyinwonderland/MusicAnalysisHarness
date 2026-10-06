"""Bounded, label-blind observation expansion; never extend a chord hypothesis."""
from copy import deepcopy
from fractions import Fraction
from .formal_ir import q
from .harmony_joint import f
from .harmony_intervening_paths import assess
from .harmony_polyphonic_links import observe
from .harmony_catalog_paths import local_alternatives

VERSION = 'bounded-path-context-0.1.0'
MAX_DENOMINATOR_BEATS = 16
MAX_SOUNDS = 128


def plan(ir, original, path):
    """Minimal union, capped using notated denominator units (not inferred beat)."""
    a = min(f(original['start']), f(path['span']['start']))
    b = max(f(original['end']), f(path['span']['end']))
    ms = [m for m in ir.get('measures', []) if f(m['global_start_quarter']) < b
          and f(m['global_start_quarter']) + f(m['actual_duration_quarter']) > a]
    reasons = []
    meters = [m.get('time_signature', {}) for m in ms]
    unit = None
    if not meters or any(not m.get('beats') or not m.get('beat_type') for m in meters):
        reasons.append('meter_missing')
    elif any(m != meters[0] for m in meters):
        reasons.append('meter_changed')
    else:
        unit = Fraction(4, int(meters[0]['beat_type']))
        if (b-a)/unit > MAX_DENOMINATOR_BEATS:
            reasons.append('context_beat_limit_no_truncation')
    # Require continuous measure coverage, not merely a plausible endpoint.
    cursor = a
    for m in sorted(ms, key=lambda m: f(m['global_start_quarter'])):
        start = f(m['global_start_quarter']); end = start + f(m['actual_duration_quarter'])
        if start > cursor: reasons.append('measure_coverage_gap')
        cursor = max(cursor, end)
        bar = m.get('repeat_barline') or {}
        t = start if bar.get('location') == 'left' else end
        if a < t < b and any(bar.get(k) for k in ('repeat_direction', 'ending_number')):
            reasons.append('repeat_or_ending_barrier')
    if cursor < b: reasons.append('measure_coverage_gap')
    sounds = [s for s in ir['sounding_events'] if f(s['span']['start']) < b and f(s['span']['end']) > a]
    if len(sounds) > MAX_SOUNDS: reasons.append('context_sound_limit_no_pruning')
    old_ids = {s['sounding_event_id'] for s in sounds if f(s['span']['start']) < f(original['end'])
               and f(s['span']['end']) > f(original['start'])}
    return {'original_span':deepcopy(original), 'proposed_span':{'start':q(a),'end':q(b)},
            'accepted':not reasons, 'abstention_reasons':sorted(set(reasons)),
            'denominator_unit_quarters':q(unit) if unit else None,
            'denominator_units':q((b-a)/unit) if unit else None,
            'limits':{'denominator_units':MAX_DENOMINATOR_BEATS,'sounds':MAX_SOUNDS},
            'sound_refs':[s['sounding_event_id'] for s in sounds],
            'source_note_refs':sorted({n for s in sounds for n in s['source_note_ids']}),
            'added_sound_refs':[s['sounding_event_id'] for s in sounds if s['sounding_event_id'] not in old_ids],
            'chord_spans_extended':False,'labels_used_for_extent':False}


def augment(ir, baseline):
    """Append a new audit. Every pre-existing result remains byte-value equivalent."""
    result = deepcopy(baseline)
    rows = {}; catalogs = {}
    for pid, old in baseline['arrival_path_assessment']['paths'].items():
        p = old['observation']; policy = plan(ir, baseline['span'], p)
        entry = {'context_policy':policy,'selected':None,'used_for_ranking':False}
        rows[pid] = entry
        if not policy['accepted']: continue
        span = policy['proposed_span']
        audit = deepcopy(baseline['delayed_counterevidence'])
        audit['records'] = [r for r in audit['records'] if r['group_id']==p['group_id'] and r['source_refs']==p['source_refs']]
        fresh = assess(ir, baseline['delayed_observation'], audit, [], [span])['records']
        if len(fresh)!=1: raise ValueError('path_identity_mismatch')
        new = fresh[0]
        if new['events']!=p['events'] or not new['all_intervening_refs_preserved']:
            raise ValueError('observation_event_loss_or_change')
        entry['observation'] = new
        entry['cleared_context_reasons'] = sorted(set(p['abstention_reasons'])-set(new['abstention_reasons']))
        # Candidate membership/spans are deliberately the old hypotheses, not
        # extended simply because more score material is now observable.
        entry['conditions'] = []
        for c in old['conditions']:
            # No harmonic conditions are recomputed from local assignments.
            entry['conditions'].append({'condition_ref':c['condition_id'],
                'status':'original_candidate_scope_unchanged','candidate_span':c['candidate_span']})
        poly = observe(ir, [span])
        notes = {n['note_id']:n for n in ir['note_events']}
        source_notes = p['events'][next(i for i,e in enumerate(p['events']) if e['event_ref']==p['source_refs'][0])]['source_note_ids']
        lanes = {(notes[n]['part_id'],notes[n]['voice_id']) for n in source_notes}
        entry['polyphonic_observation'] = {**poly,
            'groups':[g for g in poly['groups'] if (g['part_id'],g['voice_id']) in lanes],
            'abstentions':[g for g in poly['abstentions'] if (g['part_id'],g['voice_id']) in lanes]}
        entry['alternative_cell_catalog_refs'] = []
        for cat in local_alternatives(ir,new,span):
            wid = cat['providers']['base']['window_id']; catalogs[wid] = cat
            entry['alternative_cell_catalog_refs'].append(wid)
        entry['connection_across_initial_gap_confirmed'] = False
        entry['global_voice_path_selected'] = None
    result['bounded_path_context'] = {'version':VERSION,'paths':rows,'local_catalogs':catalogs,
        'production_modified':False,'harmonic_results_changed':False,
        'limits':['Observation expansion is not chord duration extension.',
                  'Partial injective matchings are local alternatives, not global voice paths.',
                  'No gap bridging, closest-note selection, harmonic rerank or probability.',
                  'Only existing delayed-endpoint paths are examined.']}
    return result
