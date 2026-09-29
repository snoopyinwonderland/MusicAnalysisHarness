"""Lossless repeated-pitch runs for conditional figures, never a score reduction."""
from .harmony_joint import f
from .harmony_reading_voice_context import voice_links, spelled_height
from .counterpoint_evidence import melodic_geometry
from .harmony_path_contrast import token

VERSION = 'reattack-figure-evidence-0.1.0'


def assess(ir, w):
    """Use only complete sounds inside a frozen window and explicit safe links.

    No extra context, nearest-pitch matching, note deletion or chord selection.
    A run is an evidence grouping, NOT a tie chain or a sounding event.
    """
    a, b = (f(w['span'][k]) for k in ('start', 'end'))
    notes = {n['note_id']: n for n in ir['note_events']}
    sounds = {s['sounding_event_id']: s for s in ir['sounding_events']}
    eligible = {}
    for sid, s in sounds.items():
        ns = [notes.get(n) for n in s['source_note_ids']]
        if (a <= f(s['span']['start']) < f(s['span']['end']) <= b
                and spelled_height(s['pitch']) is not None and ns and all(ns)
                and not any(n.get('grace', {}).get('is_grace') for n in ns)):
            eligible[sid] = s
    observed = voice_links(ir, w['span'])
    edges = {x['source_refs'][0]: x['source_refs'][1] for x in observed['links']
             if all(s in eligible for s in x['source_refs'])}
    predecessors = set(edges.values())
    groups = []; records = []

    def pitch_key(s):
        p = s['pitch']
        return p['step'], int(f(p['alter'])), p['octave']

    for head in sorted(set(eligible) - predecessors,
                       key=lambda s: (f(eligible[s]['span']['start']), s)):
        chain = [head]
        while chain[-1] in edges:
            chain.append(edges[chain[-1]])
        runs = []
        for sid in chain:
            if runs and pitch_key(eligible[runs[-1][-1]]) == pitch_key(eligible[sid]):
                runs[-1].append(sid)
            else:
                runs.append([sid])
        lane_groups = []
        for run in runs:
            g = {'group_id': 'run_' + token(run), 'event_refs': run,
                 'pitch': eligible[run[0]]['pitch'],
                 'span': {'start': eligible[run[0]]['span']['start'],
                          'end': eligible[run[-1]]['span']['end']},
                 'attacks': [{'event_ref': sid, 'span': eligible[sid]['span'],
                             'source_note_ids': eligible[sid]['source_note_ids']} for sid in run],
                 'attack_count': len(run), 'is_tie_chain': False,
                 'original_attacks_preserved': True}
            groups.append(g); lane_groups.append(g)
        for triple in zip(lane_groups, lane_groups[1:], lane_groups[2:]):
            if not any(g['attack_count'] > 1 for g in triple):
                continue  # Leave ordinary three-note figures to the existing module.
            geometry = melodic_geometry([pitch_key(eligible[g['event_refs'][0]]) for g in triple])
            if not geometry['pattern']:
                continue
            explanations = []
            for c in w['candidates']:
                states = [{c['event_states'].get(sid, 'unobserved') for sid in g['event_refs']}
                          for g in triple]
                compatible = (not w['abstention_reasons'] and states == [
                    {'member'}, {'nonmember_not_confirmed_nct'}, {'member'}])
                all_members = all(s == {'member'} for s in states)
                explanations.append({'candidate_ref': c['candidate_id'], 'label': c['label'],
                    'event_states': [sorted(s) for s in states],
                    'conditional_role': geometry['pattern'].replace('_geometry', '') if compatible else None,
                    'status': ('context_unresolved' if w['abstention_reasons'] else
                               'conditional_reattack_figure_compatible' if compatible else
                               'all_events_are_candidate_members' if all_members else
                               'membership_or_spelling_not_sufficient'),
                    'confirmed_nct': False, 'remove_note': False})
            refs = [sid for g in triple for sid in g['event_refs']]
            records.append({'evidence_id': 'reattack_' + token([w['window_id'], refs]),
                'group_refs': [g['group_id'] for g in triple], 'event_refs': refs,
                'middle_refs': triple[1]['event_refs'], 'geometry': geometry['pattern'],
                'span': {'start': triple[0]['span']['start'], 'end': triple[2]['span']['end']},
                'candidate_explanations': explanations, 'selected': None,
                'assumptions': ['one fixed candidate across the complete figure',
                    'same-spelled contiguous reattacks are a grouping, not sustained sound',
                    'accent, harmonic rhythm and contrapuntal voice identity unconfirmed'],
                'used_for_ranking': False})
    return {'version': VERSION, 'window_ref': w['window_id'], 'span': w['span'],
        'groups': groups, 'records': records, 'voice_abstentions': observed['abstentions'],
        'abstention_reasons': w['abstention_reasons'], 'selected': None,
        'source_annotation_used': False, 'production_modified': False,
        'limits': ['Only complete sounds inside the supplied frozen window.',
            'No rest, overlap, enharmonic respelling or chord boundary is silently bridged.',
            'A fixed chord across the window is a test assumption, not an observed fact.',
            'Do not count overlapping figures or repeated attacks as independent votes.',
            'No duration/accent threshold or automatic NCT/chord ranking.']}
