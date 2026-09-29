"""Unit23 spelled hypotheses and literal member paths; no functional verdict."""
from collections import defaultdict
from .dominant_area_evidence import _exact
from .foundation_sonata_audit import pitch_tuple
from .tonal_foundations import LETTERS, NATURAL, spelled_interval

VERSION = 'leading-tone-seventh-0.1.0'


def hypothesis(tonic, alter=0, mode='minor', quality='diminished_seventh', inversion=0):
    if mode not in ('major', 'minor') or quality not in ('diminished_seventh','half_diminished_seventh'):
        raise ValueError('unsupported_mode_or_quality')
    if type(inversion) is not int or inversion not in range(4): raise ValueError('invalid_inversion')
    spelled_interval((tonic,alter,4),(tonic,alter,4))
    i=LETTERS.index(tonic); base=NATURAL[i]+alter
    def degree(index,semitones):
        return [LETTERS[(i+index)%7],base+semitones-NATURAL[(i+index)%7]-12*((i+index)//7)]
    # Member spelling is preserved; °7's symmetric pitch classes do not pick a root.
    members={'root':degree(6,11),'third':degree(1,2),'fifth':degree(3,5),
             'seventh':degree(5,8 if quality=='diminished_seventh' else 9)}
    profile=('unit23_basic_minor' if mode=='minor' and quality=='diminished_seventh' else
             'unit23_basic_major' if mode=='major' and quality=='half_diminished_seventh' else
             'mixture_or_other_context_requires_review')
    return {'tonic':[tonic,alter],'mode':mode,'quality':quality,'inversion':inversion,
            'members':members,'expected_bass_spelling':list(members.values())[inversion],
            'tonic_fifth':degree(4,7),'textbook_profile':profile,
            'typical_tonic_arrival_inversion':[0,1,1,2][inversion],
            'arrival_inversion_is_requirement':False,'functional_verdict':None}


def source_candidate(annotation):
    r=annotation['raw_fields']
    if any(r.get(k) for k in ('changes','added_tones','relativeroot','pedal','special')): return None
    inv={'7':0,'65':1,'43':2,'2':3,'42':3}.get(r.get('figbass'))
    if inv is None: return None
    minor=r.get('localkey_is_minor')
    if minor not in ('0','1') or r.get('numeral')!=('#vii' if minor=='1' else 'vii'): return None
    quality={('o','o7'):'diminished_seventh',('%','%7'):'half_diminished_seventh'}.get((r.get('form'),r.get('chord_type')))
    return (quality,inv) if quality else None


def trace_members(ir, target_span, context_span, chord):
    """Paths conditioned on supplied member spelling, not harmony correctness.

    Record all members, including internal motions and censored/ambiguous paths.
    Neither a matching shape nor an expected step selects a final analysis.
    """
    a,b=(_exact(target_span[k]) for k in ('start','end'))
    left,right=(_exact(context_span[k]) for k in ('start','end'))
    if not 0<=left<=a<b<=right: raise ValueError('invalid_context_or_target_span')
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
        keys={(n.get('part_id'),n.get('voice_id')) for n in ns}
        key=next(iter(keys)) if len(keys)==1 else None
        if key and not all(key):key=None
        row={'event_id':sid,'pitch':list(pitch_tuple(s)),'source_note_ids':list(refs),
             'original_span':s['span'],'voice':key,'x':x,'y':y}
        rows.append(row)
        if key:voices[key].append(row)
    def public(r):return {k:v for k,v in r.items() if k not in ('x','y')}
    def ambiguous(r):
        return any(o is not r and max(o['x'],r['x'],left)<min(o['y'],r['y'],right) for o in voices[r['voice']])
    def neighbor(r,entry=False):
        edge=r['x'] if entry else r['y']
        if edge<=left if entry else edge>=right:return 'context_censored',None
        candidates=[o for o in voices[r['voice']] if (o['y']==edge if entry else o['x']==edge)]
        if not candidates:return 'no_touching_event',None
        if len(candidates)!=1 or ambiguous(candidates[0]):return 'ambiguous_voice',None
        return 'direct',candidates[0]
    records=[]
    for r in rows:
        if r['x']>=b or r['y']<=a:continue
        member=next((name for name,p in chord['members'].items() if r['pitch'][:2]==p),None)
        if member is None:continue
        chain=[r];entry=None;dest=None
        if r['voice'] is None:entry_status=exit_status='missing_or_mixed_voice'
        elif ambiguous(r):entry_status=exit_status='ambiguous_voice'
        else:
            entry_status,entry=neighbor(r,True)
            while True:
                exit_status,dest=neighbor(chain[-1])
                if not dest or dest['pitch']!=r['pitch']:break
                chain.append(dest)
            if dest:exit_status='direct_pitch_change'
        motion=spelled_interval(r['pitch'],dest['pitch']) if dest else None
        expected=None
        if dest and member=='root':
            expected=dest['pitch'][:2]==chord['tonic'] and motion['generic']==2 and motion['semitones']==1
        if dest and member=='seventh':
            expected=dest['pitch'][:2]==chord['tonic_fifth'] and motion['generic']==-2 and motion['semitones'] in (-1,-2)
        entry_motion=spelled_interval(entry['pitch'],r['pitch']) if entry else None
        entry_shape=None
        if member=='seventh' and entry_motion:
            entry_shape=('common_pitch' if entry['pitch']==r['pitch'] else
                         'step_from_tonic_fifth' if entry['pitch'][:2]==chord['tonic_fifth'] and entry_motion['generic']==2 and entry_motion['semitones'] in (1,2) else
                         'descending_step_entry' if entry_motion['generic']==-2 and entry_motion['semitones'] in (-1,-2) else 'other_entry')
        at_or_after=bool(dest and dest['x']>=b)
        records.append({'member':member,'event':public(r),'entry_status':entry_status,
                        'entry_event':public(entry) if entry else None,'entry_motion':entry_motion,
                        'seventh_entry_geometry':entry_shape,'same_pitch_attack_chain':[public(x) for x in chain],
                        'departure_status':exit_status,'departure_event':public(dest) if dest else None,
                        'departure_motion':motion,'expected_step_geometry':expected,
                        'departure_at_or_after_target_end':at_or_after,
                        'exit_step_candidate':bool(expected and at_or_after),
                        'resolution_verified':None})
    return {'version':VERSION,'basis':'supplied_chord_members_and_literal_same_voice_paths',
            'hypothesis':chord,'target_span':target_span,'context_span':context_span,
            'records':records,'excluded_grace_event_ids':excluded,'functional_verdict':None,'cadence':None,
            'nct':None,'production_enabled':False,
            'limitations':['only immediate touching pitch change after same-pitch repeats',
                'polyphonic explicit voices abstain; no transferred resolution or pitch sorting',
                'internal motion distinguished from departure beyond supplied harmonic span',
                'independent member paths do not prove simultaneous interval resolution',
                'seventh descending to tonic fifth is also compatible with dominant embellishment',
                'metric hierarchy, arrival harmony, pedal and phrase elision unassessed']}
