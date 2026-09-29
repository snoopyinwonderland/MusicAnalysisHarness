"""Conditional I/i, V, V7 support of a supplied melodic path; no key inference."""
from .tonal_foundations import scale_degree
from .counterpoint_evidence import melodic_geometry

VERSION = 'tonic-dominant-evidence-0.1.0'


def assess_bass_path(pitches, chord_candidates, event_ids, tonic_step, tonic_alter=0, mode='major'):
    """Conditional tonic/dominant inversion bass evidence; upper support is unknown.

    Uses explicit viio6 for the book's VII6 (leading-tone diminished triad),
    never treats arbitrary major VII6 as equivalent. Inputs are three attacks;
    held bass spanning multiple harmonic slices needs a separate adapter.
    """
    tonic='I' if mode=='major' else 'i'
    specs={tonic:(tonic,1,0),tonic+'6':(tonic,3,1),
           'V':('V',5,0),'V6':('V',7,1),'viio6':('viio',2,1),
           'V7':('V7',5,0),'V65':('V7',7,1),'V43':('V7',2,2),'V42':('V7',4,3)}
    if any(c not in specs for c in chord_candidates):
        raise ValueError('unsupported_bass_chord_candidate')
    # Reuse validated scale coordinates and melodic geometry, not its chord conclusions.
    seed=assess_path(pitches,[tonic]*3,event_ids,tonic_step,tonic_alter,mode)
    observations=[]
    for s,c in zip(seed['supports'],chord_candidates):
        family,degree,inversion=specs[c]
        coordinate=s['coordinate']
        observations.append({'event_id':s['event_id'],'chord_candidate':c,
                             'chord_family_under_candidate':family,'candidate_inversion':inversion,
                             'bass_coordinate':coordinate,
                             'expected_bass_degree':degree,
                             'bass_matches_candidate':coordinate['degree']==degree and coordinate['diatonic_to_candidate']})
    matched=all(o['bass_matches_candidate'] for o in observations)
    geometry=seed['melodic_geometry']
    labels=tuple(chord_candidates)
    role=None
    if matched and geometry['pattern']=='neighbor_geometry':
        if labels==(tonic,'V6',tonic):role='neighboring_dominant_candidate'
        elif labels in ((tonic,'viio6',tonic),(tonic+'6','viio6',tonic+'6')):
            role='neighboring_leading_tone_chord_candidate'
    if matched and geometry['pattern']=='passing_geometry' and labels in (
            (tonic,'viio6',tonic+'6'),(tonic+'6','viio6',tonic)):
        role='passing_leading_tone_chord_candidate'
    if matched and geometry['pattern']=='neighbor_geometry' and labels in (
            (tonic,'V65',tonic),(tonic,'V43',tonic),
            (tonic+'6','V43',tonic+'6'),(tonic+'6','V42',tonic+'6')):
        role='neighboring_dominant_seventh_candidate'
    if matched and geometry['pattern']=='passing_geometry' and labels in (
            (tonic,'V43',tonic+'6'),(tonic+'6','V43',tonic),
            ('V','V42',tonic+'6'),('V7','V42',tonic+'6')):
        role='passing_dominant_seventh_candidate'
    bass_resolutions=[]
    for i,iv in enumerate((geometry['approach'],geometry['departure'])):
        a,b=observations[i:i+2]
        kind=None
        if a['bass_matches_candidate'] and b['bass_matches_candidate']:
            if labels[i]=='V65' and labels[i+1]==tonic and iv['generic']==2 and iv['semitones']==1:
                kind='leading_tone_bass_step_up'
            if labels[i]=='V42' and labels[i+1]==tonic+'6' and iv['generic']==-2 and iv['semitones'] in (-1,-2):
                kind='chordal_seventh_bass_step_down'
        if kind:
            bass_resolutions.append({'event_refs':event_ids[i:i+2],'type':kind})
    expansions=[]
    for i in range(2):
        a,b=observations[i:i+2]
        if (a['bass_matches_candidate'] and b['bass_matches_candidate']
            and a['chord_family_under_candidate']==b['chord_family_under_candidate']
            and a['candidate_inversion']!=b['candidate_inversion']):
            expansions.append({'event_refs':event_ids[i:i+2],
                               'type':'same_chord_family_position_change_candidate'})
    return {'version':'first-inversion-bass-evidence-0.2.0',
            'key_hypothesis':seed['key_hypothesis'],'bass_observations':observations,
            'bass_geometry':geometry,'middle_role_candidate':role,'expansion_candidates':expansions,
            'bass_resolution_evidence':bass_resolutions,
            'upper_voice_support':'unassessed','harmony_verified':False,'cadence':None,
            'production_enabled':False,
            'limitations':['Explicit key, chord hypotheses, bass voice and three attacks required',
                           'No implied bass, voice exchange or tritone resolution inferred',
                           'No automatic harmony merge or phrase boundary change']}


def assess_path(pitches, chord_candidates, event_ids, tonic_step, tonic_alter=0, mode='major'):
    """Three source-linked pitches with explicit chord and local-key hypotheses.

    Caller supplies a coherent voice path and timing alignment. Candidate chord
    membership is distinct from passing/neighbor geometry and from NCT truth.
    This function does not evaluate whether the proposed chords actually sound.
    """
    if mode not in ('major','minor'):
        raise ValueError('major_or_minor_hypothesis_required')
    if len(pitches)!=3 or len(chord_candidates)!=3 or len(event_ids)!=3:
        raise ValueError('three_aligned_events_required')
    if any(not isinstance(e,str) or not e for e in event_ids) or len(set(event_ids))!=3:
        raise ValueError('three_distinct_source_event_ids_required')
    tonic_label='I' if mode=='major' else 'i'
    factors={tonic_label:{1:1,3:3,5:5},'V':{5:1,7:3,2:5},'V7':{5:1,7:3,2:5,4:7}}
    if any(c not in factors for c in chord_candidates):
        raise ValueError('unsupported_chord_candidate')
    form='major' if mode=='major' else 'harmonic_minor'
    geometry=melodic_geometry(pitches)
    supports=[]
    for p,c,e in zip(pitches,chord_candidates,event_ids):
        coordinate=scale_degree(p[0],p[1],tonic_step,tonic_alter,form)
        factor=factors[c].get(coordinate['degree']) if coordinate['diatonic_to_candidate'] else None
        supports.append({'event_id':e,'chord_candidate':c,'coordinate':coordinate,
                         'chord_factor_under_candidate':factor,
                         'member_under_candidate':factor is not None,'nct_label':None})
    transitions=[]
    for i in range(2):
        a,b=supports[i:i+2]
        iv=geometry['approach'] if i==0 else geometry['departure']
        is_return=chord_candidates[i] in ('V','V7') and chord_candidates[i+1]==tonic_label
        transitions.append({'event_refs':event_ids[i:i+2],
                            'dominant_to_tonic_hypothesis':is_return,
                            'seventh_step_down_to_tonic_third':is_return and a['chord_factor_under_candidate']==7
                                and b['chord_factor_under_candidate']==3 and iv['generic']==-2
                                and iv['semitones'] in (-1,-2),
                            'leading_tone_step_up_to_tonic':is_return and a['chord_factor_under_candidate']==3
                                and b['chord_factor_under_candidate']==1 and iv['generic']==2
                                and iv['semitones']==1})
    return {'version':VERSION,'key_hypothesis':{'tonic_step':tonic_step,'tonic_alter':tonic_alter,'mode':mode},
            'melodic_geometry':geometry,'supports':supports,'transitions':transitions,
            'cadence':None,'key_inferred':False,'harmony_verified':False,'production_enabled':False,
            'limitations':['Explicit aligned voice path and chord hypotheses required',
                           'No bass/inversion/rhythm/phrase-ending evidence assessed',
                           'No decorated or cross-voice resolution tracking',
                           'Nonmembership is not proof of a non-chord tone']}
