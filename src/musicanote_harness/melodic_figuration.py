"""Unit21 bounded rhythmic-slot correspondences in compound melody.

These are traceable alternatives, not extracted voices, prolonged durations,
NCT labels, a reduction, or confirmation of harmony/cadence.
"""
from collections import defaultdict
from .diatonic_sequence import compare_voices
from .counterpoint_evidence import melodic_geometry
from .dominant_area_evidence import _exact
from .tonal_foundations import spelled_interval, LETTERS, NATURAL

VERSION = 'melodic-figuration-0.1.0'


def compare_blocks(ir, first_span, second_span):
    """Supply touching comparison windows, not labels or a desired resolution.

    Exact normalized onset/duration alignment is a deliberately narrow first
    implementation. A mismatch is abstention, not absence of compound melody.
    """
    base=compare_voices(ir,first_span,second_span)
    results=[]
    for voice in base['voices']:
        blocks=voice['blocks']
        reasons=list(voice['abstention_reasons'])
        if not voice['part_id'] or not voice['voice_id']:
            reasons.append('missing_explicit_voice_identity')
        comp=voice['comparison']
        if comp and not comp['normalized_rhythm_equal']:
            reasons.append('different_normalized_rhythm_no_forced_alignment')
        geometry=[]
        for bi,block in enumerate(blocks):
            if block['abstention_reasons']: continue
            for i in range(len(block['events'])-2):
                triple=block['events'][i:i+3]
                if any(_exact(a['release'])!=_exact(b['onset']) for a,b in zip(triple,triple[1:])): continue
                g=melodic_geometry([e['pitch'] for e in triple])
                if g['pattern']:
                    geometry.append({'block_index':bi,'event_refs':[e['event_id'] for e in triple],**g})
        groups=[]; mapping_consistent=False
        if not reasons:
            a,b=(block['events'] for block in blocks)
            grouped=defaultdict(list); forward=defaultdict(set); reverse=defaultdict(set)
            for i,(x,y) in enumerate(zip(a,b)):
                key=(tuple(x['pitch']),tuple(y['pitch']))
                grouped[key].append(i)
                forward[key[0]].add(key[1]); reverse[key[1]].add(key[0])
            mapping_consistent=all(len(v)==1 for v in [*forward.values(),*reverse.values()])
            for (left,right),indices in sorted(grouped.items(),key=lambda item:item[1][0]):
                members=[]
                for index in indices:
                    x,y=a[index],b[index]
                    members.append({'slot_index':index,'event_refs':[x['event_id'],y['event_id']],
                                    'source_note_refs':[x['source_note_ids'],y['source_note_ids']],
                                    'relative_onset':x['relative_onset'],
                                    'relative_duration':x['relative_duration']})
                groups.append({'left_pitch':list(left),'right_pitch':list(right),
                               'slot_evidence':members,'slot_count':len(indices),
                               'repeated_slot_support':len(indices)>=2,
                               'motion':spelled_interval(left,right),
                               'alternative_mapping_present':len(forward[left])>1 or len(reverse[right])>1,
                               'status':'candidate_correspondence_not_inferred_voice',
                               'intervening_events_role':'unassessed'})
        eligible=bool(not reasons and mapping_consistent and len(groups)>=2 and
                      any(g['repeated_slot_support'] for g in groups))
        results.append({'part_id':voice['part_id'],'voice_id':voice['voice_id'],
                        'blocks':blocks,'abstention_reasons':reasons,
                        'normalized_rhythm_equal':comp['normalized_rhythm_equal'] if comp else None,
                        'duration_scale_factor':comp['duration_scale_factor'] if comp else None,
                        'pitch_mapping_consistent':mapping_consistent,
                        'compound_correspondence_candidate':eligible,'slot_groups':groups,
                        'adjacent_melodic_geometry':geometry,'selected_projection':None})
    return {'version':VERSION,'basis':'score_events_and_supplied_windows_no_harmony_labels',
            'block_spans':[first_span,second_span],'voices':results,
            'excluded_grace_event_ids':base['excluded_grace_event_ids'],
            'nct_labels':None,'reduction':None,'cadence':None,'production_enabled':False,
            'limitations':['exact rhythm and event count only; unmatched variation not rejected as music',
                           'no cross-voice or cross-part inferred continuity; cross-staff same voice allowed',
                           'cross-boundary ties and polyphonic notated voices abstain without shortening notes',
                           'rhythmic-slot equivalence is not proven contrapuntal voice identity; neighbor figures can also match',
                           'no virtual sustain, no removal of intervening notes',
                           'supplied windows not independently found harmonic boundaries']}


def _members(chord):
    i=LETTERS.index(chord['root_step'])
    root=NATURAL[i]+chord['root_alter']
    third,fifth={'major':(4,7),'minor':(3,7),'diminished':(3,6),'augmented':(4,8)}[chord['quality']]
    return {(LETTERS[(i+d)%7],root+semitones-NATURAL[(i+d)%7]-(12 if (i+d)%7<i else 0)):name
            for d,semitones,name in ((0,0,'root'),(2,third,'third'),(4,fifth,'fifth'))}


def condition_on_triads(observation, left_chord, right_chord):
    """Separate hypothesis-dependent coverage and 6/4->5/3 projection candidate.

    Supplied membership is NOT observed harmonic truth. Complete union coverage
    is not simultaneity. Singleton slots remain explicitly weak evidence.
    """
    templates=[_members(c) for c in (left_chord,right_chord)]
    results=[]
    for voice in observation['voices']:
        groups=voice['slot_groups']; coverage=[]
        for bi,(block,template) in enumerate(zip(voice['blocks'],templates)):
            members=defaultdict(list); extra=[]
            for event in block['events']:
                member=template.get(tuple(event['pitch'][:2]))
                if member: members[member].append(event['event_id'])
                else: extra.append(event['event_id'])
            coverage.append({'block_index':bi,'member_event_refs':dict(members),'extra_event_refs':extra,
                             'all_three_members_present':len(members)==3,'union_is_simultaneous':False})
        def height(p): return 12*(p[2]+1)+NATURAL[LETTERS.index(p[0])]+p[1]
        paths=[]
        if (voice['compound_correspondence_candidate'] and left_chord['inversion']==2 and right_chord['inversion']==0
                and all(c['all_three_members_present'] and not c['extra_event_refs'] for c in coverage)):
            basses=[g for g in groups if g['left_pitch']==g['right_pitch'] and
                    g['left_pitch'][:2]==left_chord['expected_bass_spelling']==right_chord['expected_bass_spelling'] and
                    all(height(g['left_pitch'])<=height(h['left_pitch']) and
                        height(g['right_pitch'])<=height(h['right_pitch']) for h in groups)]
            for bass in basses:
                motions=[]
                for group in groups:
                    ivs=[spelled_interval(bass['left_pitch'],group[k])['generic'] for k in ('left_pitch','right_pitch')]
                    pair=tuple((iv-1)%7+1 for iv in ivs)
                    if all(iv>0 for iv in ivs) and pair in ((4,3),(6,5)) and group['motion']['semitones'] in (-1,-2):
                        motions.append({'relation':f'{pair[0]}_to_{pair[1]}','slot_group':group})
                if {'4_to_3','6_to_5'}<={m['relation'] for m in motions}:
                    paths.append({'bass_slot_group':bass,'upper_motion_groups':motions,
                                  'all_groups_have_repeated_support':bass['repeated_slot_support'] and
                                      all(m['slot_group']['repeated_slot_support'] for m in motions),
                                  'status':'conditional_compound_resolution_candidate',
                                  'needs_evidence':['harmonic_window_validity','metrical_and_formal_context',
                                                    'independent_voice_projection_review','intervening_events_explanation',
                                                    'other_voices_and_competing_harmony']})
        results.append({'part_id':voice['part_id'],'voice_id':voice['voice_id'],
                        'conditional_member_coverage':coverage,'compound_resolution_candidates':paths})
    return {'version':VERSION,'basis':'supplied_triad_hypotheses_plus_unselected_slot_projection',
            'supplied_chords':[left_chord,right_chord],'voices':results,'functional_verdict':None,
            'cadence':None,'production_enabled':False}
