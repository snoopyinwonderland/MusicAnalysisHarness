"""Unit30 supplied-key augmented-sixth evidence, never a root/function verdict."""
from collections import defaultdict
from .applied_chords import offset
from .diatonic_modulation import validate_key
from .dominant_area_evidence import _exact
from .formal_ir import q
from .foundation_sonata_audit import pitch_tuple
from .predominant_sonata_audit import span_observation
from .tonal_foundations import LETTERS, NATURAL, spelled_interval

VERSION = 'augmented-sixth-0.1.0'


def hypothesis(key, family, bass_role='flat6'):
    step, alter, mode = validate_key(key)
    if family not in ('It','Ger','Fr','Ger43'):raise ValueError('unsupported_family')
    tonic=[step,alter]
    roles={'flat6':offset(tonic,5,8),'tonic':tonic,'sharp4':offset(tonic,3,6)}
    if family=='Ger':roles['flat3']=offset(tonic,2,3)
    if family=='Fr':roles['natural2']=offset(tonic,1,2)
    if family=='Ger43':roles['sharp2']=offset(tonic,1,3)
    if bass_role not in roles:raise ValueError('bass_role_outside_family')
    return {'family':family,'key':list(key),'roles':roles,'members':list(roles.values()),
        'expected_bass':roles[bass_role],'bass_role':bass_role,'goal_pitch':offset(tonic,4,7),
        'root':None,'basis':'supplied_key_family_and_bass_role'}


def source_reference(annotation, key):
    """Explicitly support observed DCML It/Ger expansions, not slash erasure.

    DCML special labels already expand to altered applied vii; b3 is part of
    that encoding, not an arbitrary modifier to ignore. Fr/Ger43 await adapter
    verification with source examples, though their theory shapes are supported.
    """
    r=annotation['raw_fields'];family=r.get('special')
    fig={'It':'6','Ger':'65'}.get(family)
    if key is None or fig is None:return None
    if r.get('localkey_is_minor')!=('1' if key[2]=='minor' else '0'):return None
    required={'chord_type':family,'numeral':'vii','form':'o','figbass':fig,
              'changes':'b3','relativeroot':'V','chord':family+'6'}
    if any(r.get(k)!=v for k,v in required.items()):return None
    if any(r.get(k) for k in ('pedal','added_tones')):return None
    return hypothesis(key,family)


def pc(p):return (NATURAL[LETTERS.index(p[0])]+p[1])%12


def observe(ir, span, context_span, h):
    h=hypothesis(h['key'],h['family'],h['bass_role'])
    a,b=(_exact(span[k]) for k in ('start','end'));left,right=(_exact(context_span[k]) for k in ('start','end'))
    if not 0<=left<=a<b<=right:raise ValueError('invalid_context')
    notes={n['note_id']:n for n in ir['note_events']}
    if len(notes)!=len(ir['note_events']):raise ValueError('duplicate_note_id')
    rows=[];voices=defaultdict(list);seen=set();excluded=[];sounds=[]
    for s in ir['sounding_events']:
        sid=s['sounding_event_id'];x,y=(_exact(s['span'][k]) for k in ('start','end'))
        if sid in seen:raise ValueError('duplicate_sounding_id')
        seen.add(sid)
        if x<0 or y<x:raise ValueError('invalid_event_time')
        if x>=right or y<left:continue
        refs=s['source_note_ids'];ns=[notes.get(n) for n in refs]
        if not refs or s['attack_note_id'] not in refs or any(n is None for n in ns):raise ValueError('broken_note_reference')
        p=list(pitch_tuple(s))
        if any(n.get('grace',{}).get('is_grace',False) for n in ns):excluded.append(sid);continue
        if x==y:raise ValueError('zero_duration_non_grace')
        identities={(n.get('part_id'),n.get('voice_id')) for n in ns}
        voice=next(iter(identities)) if len(identities)==1 else None
        if voice and not all(voice):voice=None
        r={'event_id':sid,'pitch':p,'source_note_ids':refs,'span':s['span'],
           'voice':list(voice) if voice else None,'x':x,'y':y}
        rows.append(r);sounds.append(s)
        if voice:voices[voice].append(r)
    def public(r):return {k:v for k,v in r.items() if k not in ('x','y')}
    def ambiguous(r):return any(o is not r and max(o['x'],r['x'],left)<min(o['y'],r['y'],right) for o in voices[tuple(r['voice'])])
    def following(r):
        if not r['voice']:return 'missing_voice',None
        if ambiguous(r):return 'ambiguous_voice',None
        if r['y']>=right:return 'context_censored',None
        matches=[o for o in voices[tuple(r['voice'])] if o['x']==r['y']]
        if not matches:return 'no_touching_event',None
        if len(matches)!=1 or ambiguous(matches[0]):return 'ambiguous_voice',None
        return 'direct',matches[0]
    target=[r for r in rows if r['x']<b and r['y']>a];paths=[];resolved=[]
    for r in target:
        role=next((k for k in ('flat6','sharp4') if r['pitch'][:2]==h['roles'][k]),None)
        if role is None:continue
        chain=[r]
        while True:
            status,dest=following(chain[-1])
            if dest is None or dest['pitch']!=r['pitch']:break
            chain.append(dest)
        m=spelled_interval(r['pitch'],dest['pitch']) if dest else None
        direction=-1 if role=='flat6' else 1
        goal=bool(dest and dest['pitch'][:2]==h['goal_pitch'] and m['generic']==2*direction and m['semitones']==direction)
        paths.append({'role':role,'event':public(r),'same_pitch_chain':[public(c) for c in chain],
            'departure_status':status,'departure':public(dest) if dest else None,'motion':m,
            'semitone_to_goal':goal,'resolution_verified':None})
        if goal:resolved.append((role,r,chain[-1],dest))
    pairs=[];pair_ids=set()
    for role,low,ll,ld in resolved:
        if role!='flat6':continue
        for role2,up,ul,ud in resolved:
            if role2!='sharp4' or low['voice']==up['voice']:continue
            # Last source tones must overlap the supplied span, with synchronous
            # departure and a real destination overlap. Separate paths are not enough.
            x,y=max(ll['x'],ul['x'],a),min(ll['y'],ul['y'],b)
            if x>=y or ld['x']!=ud['x'] or max(ld['x'],ud['x'])>=min(ld['y'],ud['y'],right):continue
            before=spelled_interval(low['pitch'],up['pitch']);after=spelled_interval(ld['pitch'],ud['pitch'])
            kind=None
            if before['generic']>=6 and (before['generic']-6)%7==0 and before['semitones']==10+12*((before['generic']-6)//7):
                if after['semitones']==before['semitones']+2:kind='augmented_sixth_outward_to_octaves'
            if before['generic']<=-3 and (-before['generic']-3)%7==0 and before['semitones']==-2-12*((-before['generic']-3)//7):
                if after['semitones']==before['semitones']+2:kind='diminished_third_inward_to_unison_or_octaves'
            identity=(ll['event_id'],ul['event_id'],ld['event_id'],ud['event_id'])
            if kind and identity not in pair_ids:
                pair_ids.add(identity)
                pairs.append({'kind':kind,'source_refs':[ll['event_id'],ul['event_id']],
                'destination_refs':[ld['event_id'],ud['event_id']], 'source_overlap':{'start':q(x),'end':q(y)},
                'arrival':q(ld['x']),'before_interval':before,'after_interval':after,'harmonic_resolution_verified':None})
    surface=span_observation({'sounding_events':sounds},span);expected={tuple(p) for p in h['members']}
    for cell in surface['slices']:
        pitches=[e['pitch'] for e in cell['events']];actual={tuple(p[:2]) for p in pitches}
        bass=min(pitches,key=lambda p:12*(p[2]+1)+NATURAL[LETTERS.index(p[0])]+p[1]) if pitches else None
        cell['spelled_family_complete']=actual==expected
        cell['supplied_bass_matches']=bass[:2]==h['expected_bass'] if bass else False
        cell['pitch_class_family_complete']={pc(p) for p in actual}=={pc(p) for p in expected}
        cell['enharmonic_only']=cell['pitch_class_family_complete'] and not cell['spelled_family_complete']
        cell['tonic_count']=sum(p[:2]==h['roles']['tonic'] for p in pitches)
    union={tuple(r['pitch'][:2]) for r in target}
    return {'version':VERSION,'hypothesis':h,'source_span':span,'context_span':context_span,'surface':surface,
        'missing_spellings':[list(p) for p in sorted(expected-union)],'extra_spellings':[list(p) for p in sorted(union-expected)],
        'critical_paths':paths,'joint_geometry':pairs,'excluded_grace_refs':excluded,'union_is_simultaneous':False,
        'function':None,'cadence':None,'modulation':None,'nct_labels':None,'production_enabled':False,
        'limitations':['key, family, bass role and span supplied; not blind chord classification',
            'root not assigned; chromatic interval geometry does not establish function',
            'IR voice may not represent contrapuntal strand; chordal voices abstain',
            'no delay, transfer, elided V7 resolution, chromatic bass detour or pedal inference',
            'enharmonic-only match remains an alternative, never silently respelled',
            'no automatic parallel-fifth error, cadence or phrase boundary']}
