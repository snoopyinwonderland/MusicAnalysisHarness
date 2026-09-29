"""Unit25 conditional seventh successions and competing apparent-chord evidence.

Source keys/chords/ranges are supplied in audits. No inferred function, NCT,
transferred resolution, cadence, or boundary update is returned as a fact.
"""
from collections import defaultdict
import re
from .dominant_area_evidence import _exact
from .formal_ir import q
from .foundation_sonata_audit import pitch_tuple
from .tonal_foundations import LETTERS, NATURAL, SCALES, major_degree, spelled_interval, spelled_triad_shapes

VERSION = 'seventh-context-0.1.0'
QUALITIES = {'M':(4,7), 'm':(3,7), 'o':(3,6), '+':(4,8),
             'MM7':(4,7,11), 'mm7':(3,7,10), 'Mm7':(4,7,10),
             'o7':(3,6,9), '%7':(3,6,10), '+M7':(4,8,11), 'mM7':(3,7,11)}


def chord(root, quality, inversion=0):
    major_degree(*root, 'C')
    if quality not in QUALITIES: raise ValueError('unsupported_quality')
    distances=(0,*QUALITIES[quality])
    if type(inversion) is not int or inversion not in range(len(distances)): raise ValueError('invalid_inversion')
    ri=LETTERS.index(root[0]);base=NATURAL[ri]+root[1];members=[]
    for j,d in enumerate(distances):
        index=ri+2*j
        members.append([LETTERS[index%7],base+d-NATURAL[index%7]-12*(index//7)])
    return {'root':list(root),'quality':quality,'inversion':inversion,'members':members,
            'expected_bass':members[inversion],'basis':'supplied_hypothesis'}


def source_chord(annotation, tonic, alter=0, mode='major'):
    """Strict DCML spelling adapter; retains minor-root convention, no slash erasure."""
    if mode not in ('major','minor'): raise ValueError('invalid_mode')
    major_degree(tonic,alter,tonic,alter)
    r=annotation['raw_fields']
    if r.get('localkey_is_minor') != ('1' if mode=='minor' else '0'): return None
    if any(r.get(k) for k in ('changes','added_tones','relativeroot','pedal','special')): return None
    match=re.fullmatch(r'([b#]?)(I|II|III|IV|V|VI|VII|i|ii|iii|iv|v|vi|vii)',r.get('numeral',''))
    if not match:return None
    quality=r.get('chord_type');form=r.get('form','')
    if quality not in QUALITIES:return None
    expected_form={'o':'o','o7':'o','%7':'%','+':'+','+M7':'+M','MM7':'M','mM7':'M'}.get(quality,'')
    if form!=expected_form:return None
    upper=quality in ('M','MM7','Mm7','+','+M7')
    if match[2].isupper()!=upper:return None
    fig=r.get('figbass','');seventh=len(QUALITIES[quality])==3
    inv=({'7':0,'65':1,'43':2,'2':3,'42':3} if seventh else {'':0,'6':1,'64':2}).get(fig)
    if inv is None:return None
    degree=('I','II','III','IV','V','VI','VII').index(match[2].upper())
    ti=LETTERS.index(tonic);idx=ti+degree
    scale=SCALES['natural_minor' if mode=='minor' else 'major']
    ra=NATURAL[ti]+alter+scale[degree]+{'':0,'b':-1,'#':1}[match[1]]-NATURAL[idx%7]-12*(idx//7)
    return chord([LETTERS[idx%7],ra],quality,inv)


def succession(hypotheses):
    if len(hypotheses)<2:raise ValueError('at_least_two_chords_required')
    cs=[chord(h['root'],h['quality'],h['inversion']) for h in hypotheses]
    relations=[]
    for a,b in zip(cs,cs[1:]):
        step=(LETTERS.index(b['root'][0])-LETTERS.index(a['root'][0]))%7
        semitones=(NATURAL[LETTERS.index(b['root'][0])]+b['root'][1]-NATURAL[LETTERS.index(a['root'][0])]-a['root'][1])%12
        relations.append({'root_steps_up_mod7':step,'root_semitones_up_mod12':semitones,'root_family':{3:'descending_fifth_or_ascending_fourth',1:'ascending_second_or_descending_seventh',5:'descending_third_or_ascending_sixth'}.get(step,'other'),
            'third_can_be_next_seventh':len(b['members'])==4 and a['members'][1]==b['members'][3],
            'actual_bass_direction':None})
    patterns=[];steps=[r['root_steps_up_mod7'] for r in relations]
    if len(cs)>=4 and any(len(c['members'])==4 for c in cs):
        if all(s==3 for s in steps):patterns.append('descending_fifth_root_chain')
        if all(s==5 for s in steps):patterns.append('descending_third_root_chain')
        if steps==[5,3,5] and [h['inversion'] for h in cs]==[0,1,0,1] and [len(h['members']) for h in cs]==[3,4,3,4]:patterns.append('ascending_five_six_variant')
    return {'relations':relations,'pattern_candidates':patterns,'sequence_confirmed':None,
            'needs_evidence':['actual_voice_rhythm_and_bass_paths','score_support_for_hypotheses','larger_context'],
            'basis':'supplied_chord_roots_not_score_sequence_detection'}


def observe(ir, target_span, context_span, hypothesis, following=None):
    h=chord(hypothesis['root'],hypothesis['quality'],hypothesis['inversion'])
    if len(h['members'])!=4:raise ValueError('seventh_required')
    nxt=chord(following['root'],following['quality'],following['inversion']) if following else None
    a,b=(_exact(target_span[k]) for k in ('start','end'))
    left,right=(_exact(context_span[k]) for k in ('start','end'))
    if not 0<=left<=a<b<=right:raise ValueError('invalid_context_or_target_span')
    notes={n['note_id']:n for n in ir['note_events']}
    if len(notes)!=len(ir['note_events']):raise ValueError('duplicate_note_id')
    rows=[];voices=defaultdict(list);seen=set();excluded=[]
    for s in ir['sounding_events']:
        sid=s['sounding_event_id'];x,y=(_exact(s['span'][k]) for k in ('start','end'))
        if sid in seen:raise ValueError('duplicate_sounding_event_id')
        seen.add(sid)
        if x<0 or y<x:raise ValueError('invalid_event_span')
        if x>=right or y<left:continue
        refs=s.get('source_note_ids',[]);ns=[notes.get(n) for n in refs]
        if not refs or s.get('attack_note_id') not in refs or any(n is None for n in ns):raise ValueError('broken_note_reference')
        grace=any(n.get('grace',{}).get('is_grace',False) for n in ns)
        if x==y and not grace:raise ValueError('zero_duration_non_grace')
        if grace:excluded.append(sid);continue
        keys={(n.get('part_id'),n.get('voice_id')) for n in ns};key=next(iter(keys)) if len(keys)==1 else None
        if key and not all(key):key=None
        row={'event_id':sid,'pitch':list(pitch_tuple(s)),'source_note_ids':list(refs),'original_span':s['span'],
             'voice':list(key) if key else None,'x':x,'y':y}
        rows.append(row)
        if key:voices[key].append(row)
    def public(r):return {k:v for k,v in r.items() if k not in ('x','y')}
    def ambiguous(r):return any(o is not r and max(o['x'],r['x'],left)<min(o['y'],r['y'],right) for o in voices[tuple(r['voice'])])
    def neighbor(r,entry=False):
        if r['voice'] is None:return 'missing_voice',None
        if ambiguous(r):return 'ambiguous_voice',None
        edge=r['x'] if entry else r['y']
        if (edge<=left if entry else edge>=right):return 'context_censored',None
        matches=[s for s in voices[tuple(r['voice'])] if (s['y']==edge if entry else s['x']==edge)]
        if not matches:return 'no_touching_event',None
        if len(matches)!=1 or ambiguous(matches[0]):return 'ambiguous_voice',None
        return 'direct',matches[0]
    target=[r for r in rows if r['x']<b and r['y']>a];paths=[]
    for r in target:
        if r['pitch'][:2] not in (h['members'][0],h['members'][3]):continue
        role='root' if r['pitch'][:2]==h['members'][0] else 'seventh'
        chain=[r];entry_status,entry=neighbor(r,True)
        while True:
            status,dest=neighbor(chain[-1])
            if not dest or dest['pitch']!=r['pitch']:break
            chain.append(dest)
        motion=spelled_interval(r['pitch'],dest['pitch']) if dest else None
        tags=[]
        if motion and abs(motion['generic'])==2 and abs(motion['semitones']) in (1,2):
            if role=='seventh' and motion['generic']==-2:tags.append('seventh_down_step')
            if role=='root' and motion['generic']==2:tags.append('root_up_step')
        # Cross-voice coincidences are candidates, never proof of a transferred resolution.
        cross=[];edge=chain[-1]['y']
        if role=='seventh' and r['voice'] is not None and not ambiguous(r) and edge<right:
            for other in rows:
                if other['voice'] is None or other['voice']==r['voice'] or other['x']!=edge:continue
                interval=spelled_interval(r['pitch'],other['pitch'])
                kind=('same_register_descending_step' if interval['generic']==-2 and interval['semitones'] in (-1,-2) else
                      'same_pitch_seventh_handoff' if r['pitch']==other['pitch'] else None)
                if kind:cross.append({'kind':kind,'event':public(other),'destination_voice_ambiguous':ambiguous(other),'at_or_after_target_end':edge>=b,'verified':False})
        paths.append({'role':role,'event':public(r),'entry_status':entry_status,'entry':public(entry) if entry else None,
                      'chain':[public(s) for s in chain],'departure_status':status,'departure':public(dest) if dest else None,
                      'motion':motion,'geometry_tags':tags,'at_or_after_target_end':bool(dest and dest['x']>=b),
                      'destination_in_following_members':dest['pitch'][:2] in nxt['members'] if dest and nxt else None,
                      'cross_voice_coincidences':cross,'resolution_confirmed':None})
    members={tuple(p) for p in h['members']};union={tuple(r['pitch'][:2]) for r in target};cells=[]
    points=sorted({a,b,*[max(a,r['x']) for r in target],*[min(b,r['y']) for r in target]})
    for x,y in zip(points,points[1:]):
        active=[r for r in target if r['x']<=x<r['y']]
        spellings={tuple(r['pitch'][:2]) for r in active}
        lowest=min(active,key=lambda r:12*(r['pitch'][2]+1)+NATURAL[LETTERS.index(r['pitch'][0])]+r['pitch'][1]) if active else None
        cells.append({'span':{'start':q(x),'end':q(y)},'event_refs':[r['event_id'] for r in active],
                      'complete_supplied_match':spellings==members and lowest['pitch'][:2]==h['expected_bass'] if lowest else False})
    # The same 4-note collection may be a triad plus an active added tone.
    upper=h['members'][1:];triad_shapes=spelled_triad_shapes([(s,alt,4) for s,alt in upper]);alternatives=[]
    if any(s['quality'] in ('major','minor') for s in triad_shapes) and h['inversion'] in (1,2):
        alternatives.append({'role':'triad_with_added_sixth' if h['inversion']==1 else 'first_inversion_triad_with_added_fourth',
                             'triad_members':upper,'added_member':h['members'][0],'status':'unselected_spelling_compatible',
                             'upward_motion_event_refs':[p['event']['event_id'] for p in paths if 'root_up_step' in p['geometry_tags']],
                             'needs_evidence':['governing_triad_established','actual_bass_and_triads_supported','metric_and_voice_context','competition_with_independent_seventh']})
    return {'version':VERSION,'hypothesis':h,'following_hypothesis':nxt,'target_span':target_span,'context_span':context_span,
            'events':[public(r) for r in target],'paths':paths,'vertical_cells':cells,
            'missing_spellings':sorted(members-union),'extra_event_refs':[r['event_id'] for r in target if tuple(r['pitch'][:2]) not in members],
            'apparent_alternatives':alternatives,'union_is_simultaneous':False,'excluded_grace_event_ids':excluded,
            'selected_harmony':None,'apparent_chord_confirmed':None,'cadence':None,'production_enabled':False,
            'limitations':['supplied harmony/key/windows; no blind accuracy',
                'direct same-voice pitch change only after same-pitch reattacks; no gaps bridged',
                'cross-voice pitch coincidence does not identify a transferred resolution',
                'delayed resolution vs extended harmony needs independent harmonic trajectory',
                'pedal, upper-voice exchange, metric hierarchy and phrase function unassessed']}
