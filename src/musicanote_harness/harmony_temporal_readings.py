"""Common-time comparison of constant harmony and attack/release-cell alternatives.

Cells are evidence partitions, never committed harmonic boundaries. Membership,
missing spelling, sounding time and conditional ornament hypotheses stay separate.
"""
from .formal_ir import q
from .harmony_joint import f
from .harmony_open_candidates import window
from .harmony_member_timeline import observe as timeline
from .harmony_neighbor_contrast import profile
from .harmony_voice_figures import double_neighbors

VERSION = 'temporal-reading-evidence-0.1.0'


def compare(ir, span, context):
    a,b=(f(span[k]) for k in ('start','end'))
    x,y=(f(context[k]) for k in ('start','end'))
    if not 0<=x<=a<b<=y:
        raise ValueError('span_outside_frozen_context')
    parent = window(ir, span)
    figures = double_neighbors(ir, parent)
    fixed = []
    for c in parent['candidates']:
        ornament_refs = []
        for r in parent['conditional_figures']['records']:
            e = next(e for e in r['path_explanations'] if e['path_ref'] == c['candidate_id'])
            if e['conditional_role']:
                ornament_refs.append({'evidence_ref': r['evidence_id'], 'event_refs': r['event_refs'],
                                      'role': e['conditional_role'], 'confirmed': False})
        for r in figures['records']:
            e = next(e for e in r['candidate_explanations'] if e['candidate_ref'] == c['candidate_id'])
            if e['status'] in ('conditional_double_neighbor_compatible', 'incomplete_double_neighbor_hypothesis'):
                ornament_refs.append({'evidence_ref': r['evidence_id'], 'event_refs': r['event_refs'],
                                      'role': e['status'], 'confirmed': False})
        timing = timeline(ir, span, c, c['root_hypotheses'], context)
        fixed.append({'candidate': c, 'timeline': timing,
                      'profile': profile(parent['event_units'], c, span, set()),
                      'conditional_ornaments': ornament_refs,
                      'abstention_reasons': sorted(set(parent['abstention_reasons'] + timing['abstention_reasons'])),
                      'selected': None})
    stages = []
    for cell in parent['cells']:
        local = window(ir, cell['span'])
        options = {c['label']: (c, 'carried_whole_window_hypothesis') for c in parent['candidates']}
        for c in local['candidates']:
            options[c['label']] = (c, 'local_cell_observation_candidate')
        comparisons = []
        for label, (c, origin) in sorted(options.items()):
            # Parent root spelling is an explicit hypothesis, not an observed cell root.
            t = timeline(ir, cell['span'], c, c['root_hypotheses'], context)
            comparisons.append({'label': label, 'candidate_ref': c['candidate_id'], 'origin': origin,
                                'timeline': t,
                                'profile': profile(parent['event_units'], c, cell['span'], set()),
                                'abstention_reasons': sorted(set(local['abstention_reasons'] + t['abstention_reasons'])),
                                'selected': None})
        stages.append({'span': cell['span'], 'event_refs': cell['event_refs'],
                       'attack_refs': cell['attack_refs'], 'continued_refs': cell['continued_refs'],
                       'silence': cell['silence'],
                       'fixed_profiles': {c['candidate_id']: profile(parent['event_units'], c, cell['span'], set())
                                          for c in parent['candidates']},
                       'alternatives': comparisons})
    return {'version': VERSION, 'span': span, 'frozen_context': context,
            'event_units': parent['event_units'], 'fixed_readings': fixed, 'stages': stages,
            'conditional_figures': parent['conditional_figures'], 'double_neighbor_evidence': figures,
            'selected': None, 'ranking_performed': False, 'source_annotation_used': False,
            'limits': ['Attack/release cells are not inferred chord boundaries.',
                       'Carried roots remain hypotheses; outside members never fill cell missing members.',
                       'Fixed and changing readings cover the same events and half-open time.',
                       'No event is removed by a conditional NCT explanation.',
                       'Fewest residuals or missing members is not a chord-selection score.',
                       'Missing and unresolved spelling are not equivalent; neither is negative gold.',
                       'No key/function, cadence, pedal, final path or confidence is inferred.']}
