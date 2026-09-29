"""Unit24 conditional modal coordinates and unselected mixture templates.

Neither a chromatic note nor a matching chord proves mixture, tonicization,
modulation, a cadence, or a stylistic voice-leading error.
"""
from collections import defaultdict
from .dominant_area_evidence import _exact
from .formal_ir import q
from .foundation_sonata_audit import pitch_tuple
from .tonal_foundations import LETTERS, NATURAL, MAJOR, major_degree, spelled_interval

VERSION = 'mixture-evidence-0.1.0'


def templates(tonic, alter=0, mode='major'):
    if mode not in ('major','minor'):raise ValueError('major_or_minor_required')
    major_degree(tonic,alter,tonic,alter)
    ti=LETTERS.index(tonic);base=NATURAL[ti]+alter
    def spelling(degree,delta):
        index=ti+degree-1
        return [LETTERS[index%7],base+MAJOR[degree-1]+delta-NATURAL[index%7]-12*(index//7)]
    definitions = (
        [('minor_tonic','primary',[(1,0),(3,-1),(5,0)]),
         ('minor_subdominant','primary',[(4,0),(6,-1),(1,0)]),
         ('diminished_supertonic','primary',[(2,0),(4,0),(6,-1)]),
         ('half_diminished_supertonic','primary',[(2,0),(4,0),(6,-1),(1,0)]),
         ('diminished_leading_seventh','primary',[(7,0),(2,0),(4,0),(6,-1)]),
         ('lowered_submediant','primary',[(6,-1),(1,0),(3,-1)]),
         ('major_mediant','secondary',[(3,0),(5,1),(7,0)]),
         ('major_submediant','secondary',[(6,0),(1,1),(3,0)])]
        if mode=='major' else [('major_tonic_in_minor','primary',[(1,0),(3,0),(5,0)])])
    return [{'family':name,'mixture_type_hypothesis':kind,'members':[spelling(*d) for d in degrees],
             'degree_coordinates':degrees,'selected':False} for name,kind,degrees in definitions]


def source_candidate(annotation):
    r=annotation['raw_fields']
    if any(r.get(k) for k in ('changes','added_tones','relativeroot','pedal','special')):return None
    key=(r.get('localkey_is_minor'),r.get('numeral'),r.get('form',''),r.get('chord_type'))
    families={('0','i','','m'):'minor_tonic',('0','iv','','m'):'minor_subdominant',
              ('0','ii','o','o'):'diminished_supertonic',('0','ii','%','%7'):'half_diminished_supertonic',
              ('0','vii','o','o7'):'diminished_leading_seventh',('0','bVI','','M'):'lowered_submediant',
              ('0','III','','M'):'major_mediant',('0','VI','','M'):'major_submediant',
              ('1','I','','M'):'major_tonic_in_minor'}
    family=families.get(key)
    seventh=family in ('half_diminished_supertonic','diminished_leading_seventh')
    inversion=({'7':0,'65':1,'43':2,'2':3,'42':3} if seventh else {'':0,'6':1,'64':2}).get(r.get('figbass',''))
    return (family,inversion) if family and inversion is not None else None


def observe(ir,target_span,context_span,tonic,alter=0,mode='major'):
    patterns=templates(tonic,alter,mode)
    a,b=(_exact(target_span[k]) for k in ('start','end'))
    left,right=(_exact(context_span[k]) for k in ('start','end'))
    if not 0<=left<=a<b<=right:raise ValueError('invalid_context_or_target_span')
    notes={n['note_id']:n for n in ir['note_events']}
    if len(notes)!=len(ir['note_events']):raise ValueError('duplicate_note_id')
    rows=[];voices=defaultdict(list);seen=set();excluded=[]
    for s in ir['sounding_events']:
        sid=s['sounding_event_id']
        if sid in seen:raise ValueError('duplicate_sounding_event_id')
        seen.add(sid);x,y=(_exact(s['span'][k]) for k in ('start','end'))
        if x<0 or y<x:raise ValueError('invalid_event_span')
        if x>=right or y<left:continue
        refs=s.get('source_note_ids',[]);ns=[notes.get(n) for n in refs]
        if not refs or s.get('attack_note_id') not in refs or any(n is None for n in ns):raise ValueError('broken_source_note_reference')
        grace=any(n.get('grace',{}).get('is_grace',False) for n in ns)
        if x==y and not grace:raise ValueError('zero_duration_non_grace')
        if grace:excluded.append(sid);continue
        p=list(pitch_tuple(s));degree=major_degree(*p[:2],tonic,alter)
        keys={(n.get('part_id'),n.get('voice_id')) for n in ns};key=next(iter(keys)) if len(keys)==1 else None
        if key and not all(key):key=None
        coord=(degree['degree'],degree['alteration_from_major']);tags=[]
        if mode=='major' and coord in ((3,-1),(6,-1)):tags.append('parallel_minor_pitch_compatible')
        if mode=='minor' and coord==(3,0):tags.append('major_third_in_minor_context')
        if mode=='minor' and coord in ((6,0),(7,0)):tags.append('ordinary_minor_scale_variant_not_mixture_proof')
        row={'event_id':sid,'pitch':p,'source_note_ids':list(refs),'original_span':s['span'],
             'voice':list(key) if key else None,'degree':coord[0],'alteration_from_major':coord[1],
             'coordinate_tags':tags,'x':x,'y':y}
        rows.append(row)
        if key:voices[key].append(row)
    def public(r):return {k:v for k,v in r.items() if k not in ('x','y')}
    target=[r for r in rows if r['x']<b and r['y']>a]
    points=sorted({a,b,*[max(a,r['x']) for r in target],*[min(b,r['y']) for r in target]})
    cells=[]
    for start,end in zip(points,points[1:]):
        active=[r for r in target if r['x']<=start<r['y']]
        cells.append({'span':{'start':q(start),'end':q(end)},'event_refs':[r['event_id'] for r in active],
                      'spellings':sorted({tuple(r['pitch'][:2]) for r in active}),
                      'lowest_spelling':min(active,key=lambda r:12*(r['pitch'][2]+1)+NATURAL[LETTERS.index(r['pitch'][0])]+r['pitch'][1])['pitch'][:2] if active else None})
    union={tuple(r['pitch'][:2]) for r in target};coverage=[]
    for pattern in patterns:
        members={tuple(p) for p in pattern['members']};matches=[]
        for cell in cells:
            if set(cell['spellings'])==members:
                matches.append({'span':cell['span'],'event_refs':cell['event_refs'],
                                'inversion':pattern['members'].index(cell['lowest_spelling'])})
        coverage.append({'hypothesis':pattern,'member_event_refs':{f'{s}:{alt}':[r['event_id'] for r in target if r['pitch'][:2]==[s,alt]] for s,alt in pattern['members']},
                         'missing_spellings':sorted(members-union),
                         'extra_event_refs':[r['event_id'] for r in target if tuple(r['pitch'][:2]) not in members],
                         'complete_vertical_matches':matches,'union_is_simultaneous':False})
    def ambiguous(r):
        return any(o is not r and max(o['x'],r['x'],left)<min(o['y'],r['y'],right) for o in voices[tuple(r['voice'])])
    paths=[]
    for r in target:
        if not r['coordinate_tags']:continue
        entry=None;entry_status='context_censored';entry_tags=[]
        if r['voice'] is None:entry_status='missing_or_mixed_voice'
        elif ambiguous(r):entry_status='ambiguous_voice'
        elif r['x']>left:
            preceding=[s for s in voices[tuple(r['voice'])] if s['y']==r['x']]
            if not preceding:entry_status='no_touching_event'
            elif len(preceding)!=1 or ambiguous(preceding[0]):entry_status='ambiguous_voice'
            else:
                entry_status='direct';entry=preceding[0]
                if entry['pitch'][0]==r['pitch'][0] and entry['pitch'][2]==r['pitch'][2] and abs(entry['pitch'][1]-r['pitch'][1])==1:
                    entry_tags.append('entry_same_voice_chromatic_inflection')
        dest=None;status='context_censored'
        if r['voice'] is None:status='missing_or_mixed_voice'
        elif ambiguous(r):status='ambiguous_voice'
        elif r['y']<right:
            following=[s for s in voices[tuple(r['voice'])] if s['x']==r['y']]
            if not following:status='no_touching_event'
            elif len(following)!=1 or ambiguous(following[0]):status='ambiguous_voice'
            else:status='direct';dest=following[0]
        motion=spelled_interval(r['pitch'],dest['pitch']) if dest else None;tags=[]
        if dest:
            if r['pitch'][0]==dest['pitch'][0] and r['pitch'][2]==dest['pitch'][2] and abs(r['pitch'][1]-dest['pitch'][1])==1:
                tags.append('same_voice_chromatic_inflection')
            if mode=='major' and r['alteration_from_major']==-1 and r['degree'] in (3,6) and dest['degree']==r['degree']-1 and dest['alteration_from_major']==0 and motion['generic']==-2 and motion['semitones']==-1:
                tags.append('lowered_degree_descending_step')
        paths.append({'event_ref':r['event_id'],'entry_status':entry_status,'entry_event':public(entry) if entry else None,
                      'entry_motion':spelled_interval(entry['pitch'],r['pitch']) if entry else None,
                      'departure_status':status,'departure_event':public(dest) if dest else None,
                      'motion':motion,'geometry_tags':entry_tags+tags,'nct_verdict':None})
    return {'version':VERSION,'basis':'score_events_under_supplied_tonic_mode_and_windows_no_source_chord_label',
            'key_hypothesis':{'tonic':tonic,'alter':alter,'mode':mode},'target_span':target_span,'context_span':context_span,
            'events':[public(r) for r in target],'coordinate_paths':paths,'template_coverage':coverage,
            'excluded_grace_event_ids':excluded,'selected_harmony':None,'mixture_confirmed':None,'modulation':None,
            'picardy_third':None,'cadence':None,'production_enabled':False,
            'limitations':['conditional coordinates are not inferred tonality',
                'borrowed pitch may be a figuration tone rather than an independent harmony',
                'secondary mixture is not secondary dominant; applied interpretation remains a competing hypothesis',
                'major tonic in minor is not Picardy third without terminal/formal context',
                'direct same-voice chromatic motion is not a cross-relation or a style violation',
                'cross-voice relations, doubling exceptions, extended mixture and phrase role not implemented']}
