"""Compare evidence coverage, never treat missing support as disproof or a vote.

An observed motion is one evidence unit even when two harmonic roles or window
widths explain it. Bass/occupancy features already used to form a candidate are
not new independent evidence for selecting it.
"""
from collections import defaultdict
from .harmony_joint import f
from .formal_ir import q

VERSION='reading-evidence-contrast-0.1.0'
CONDITIONAL={'conditional_seventh_down_step_to_member',
             'conditional_diminished_fifth_down_step_to_member',
             'conditional_dominant_family_leading_tone_up'}


def compare(candidate,voice):
    if candidate['evidence_id']!=voice['candidate_ref']:raise ValueError('candidate_identity_mismatch')
    expected={(kind,i) for kind in ('merged_seventh','split_triads') for i in range(len(candidate[kind]))}
    readings={(r['reading_type'],r['reading_index']):r for r in voice['readings']}
    if set(readings)!=expected or len(readings)!=len(voice['readings']):raise ValueError('incomplete_or_duplicate_readings')
    links={tuple(p['source_refs']):p for p in voice['voice_observations']['links']}
    units={}
    def collect(key,side,ext,p,window=None):
        refs=tuple(p['source_refs'])
        if refs not in links:raise ValueError('missing_voice_link')
        # Do not split one physical movement into separate votes for its labels.
        shape=None if ext is None else (ext['root'],ext['label'],tuple(sorted(ext['pcs'])))
        identity=(side,refs,shape)
        unit=units.setdefault(identity,{'side':side,'source_refs':list(refs),'external_candidate':ext,
            'motion':links[refs],'evaluated':set(),'support':defaultdict(set),'windows':[]})
        unit['evaluated'].add(key)
        tags=set(p['relations']) & CONDITIONAL
        if tags:unit['support'][key].update(tags)
        if window and window not in unit['windows']:unit['windows'].append(window)
    for key,r in readings.items():
        original=candidate[key[0]][key[1]]
        if r['source_cost_unchanged']!=original['local_cost']:raise ValueError('saved_cost_mismatch')
        for p in r['internal_relations']:collect(key,'internal',None,p)
        for ext in r['external_comparisons']:
            for p in ext['relations']:collect(key,ext['side'],ext['external_candidate'],p,ext['external_span'])
    evidence=[]
    for unit in units.values():
        families={key[0] for key in unit['support']}
        complete=unit['evaluated']==expected
        if not complete:status='incomplete_comparison'
        elif len(families)==2:status='shared_between_families'
        elif families:status=next(iter(families))+'_only_conditional_support'
        else:status='no_conditional_support'
        evidence.append({**{k:v for k,v in unit.items() if k not in ('evaluated','support')},
            'status':status,'all_readings_evaluated':complete,
            'supports_every_reading':bool(expected) and set(unit['support'])==expected,
            'per_reading':[{'reading_type':key[0],'reading_index':key[1],
                'status':'conditional_support' if key in unit['support'] else 'unobserved_not_counterevidence' if key in unit['evaluated'] else 'not_evaluated',
                'relations':sorted(unit['support'].get(key,set()))} for key in sorted(expected)],
            'independent_vote':False,'ranking_weight':None})
    b=candidate['bass'];before,after=b['before_midi'],b['after_midi']
    if before is None or after is None:bass_status='insufficient_observation'
    elif b['continued_refs']:bass_status='continued_lowest_event'
    elif b['new_attack_refs']:bass_status='same_pitch_reattack' if before==after else 'new_lowest_pitch_attack'
    else:bass_status='lowest_change_without_attack'
    return {'version':VERSION,'candidate_ref':candidate['evidence_id'],'span':candidate['span'],'boundary':candidate['boundary'],
        'readings':[{'reading_type':key[0],'reading_index':key[1],
            'labels':[s['candidate']['label'] for s in candidate[key[0]][key[1]]['segments']],
            'source_cost_unchanged':candidate[key[0]][key[1]]['local_cost']} for key in sorted(expected)],
        'evidence_units':evidence,
        'boundary_observations':{'bass_status':bass_status,'bass':b,
            'entry_delay_beats':q(f(candidate['entry_delay_quarters'])/f(candidate['beat_unit_quarter'])),
            'exclusive_member_gap_quarters':q(f(candidate['first_exclusive_attack'])-f(candidate['last_exclusive_release'])),
            'sustained_common_event_refs':candidate['sustained_common_event_refs'],
            'occupancy_quarters':candidate['occupancy_quarters'],
            'scope':'candidate_construction_features_not_additional_votes',
            'bass_is_harmonic_root':False},
        'has_family_differentiating_support':any(e['status'].endswith('_only_conditional_support') for e in evidence),
        'selected_hypothesis':None,'reranking_performed':False,'source_annotation_used':False,
        'limits':['One-family conditional support does not disprove the other reading',
            'Shared support does not distinguish the two families, even if role tags differ',
            'External chord is a pooled candidate; overlapping windows are not votes',
            'IR voice, contrapuntal identity and function remain unverified',
            'Bass changes, exclusive-member replacement and spelling are not independent proof of a new chord']}
