"""Unit26 spelled applied-chord hypotheses and explicit contextual evidence.

No accidental prerequisite, forced resolution, inferred modulation or cadence.
DCML labels are an audit adapter, never presented as blind score inference.
"""
from collections import defaultdict
import re
from .seventh_context import chord, source_chord
from .tonal_foundations import LETTERS, NATURAL, SCALES, major_degree, spelled_interval
from .dominant_area_evidence import _exact
from .foundation_sonata_audit import pitch_tuple
from .predominant_sonata_audit import span_observation

VERSION='applied-chords-0.1.0'
FAMILIES={'V':('M',4,7),'V7':('Mm7',4,7),'vii':('o',6,11),
          'vii7':('o7',6,11),'vii_half7':('%7',6,11)}


def offset(root,steps,semitones):
    major_degree(*root,'C');i=LETTERS.index(root[0]);j=i+steps
    return [LETTERS[j%7],NATURAL[i]+root[1]+semitones-NATURAL[j%7]-12*(j//7)]


def target_reference(token,tonic,alter=0,mode='major'):
    if mode not in ('major','minor'):raise ValueError('invalid_mode')
    major_degree(tonic,alter,tonic,alter)
    m=re.fullmatch(r'([b#]?)(I|II|III|IV|V|VI|VII|i|ii|iii|iv|v|vi|vii)',token)
    if not m:raise ValueError('single_major_or_minor_target_required')
    degree=('I','II','III','IV','V','VI','VII').index(m[2].upper())
    scale=SCALES['natural_minor' if mode=='minor' else 'major']
    root=offset([tonic,alter],degree,scale[degree]+{'':0,'b':-1,'#':1}[m[1]])
    return chord(root,'M' if m[2].isupper() else 'm')


def hypothesis(target_root,target_quality,family,inversion=0):
    if target_quality not in ('M','m'):raise ValueError('major_minor_target_required')
    if family not in FAMILIES:raise ValueError('unsupported_applied_family')
    target=chord(target_root,target_quality)
    quality,steps,semitones=FAMILIES[family]
    h=chord(offset(target_root,steps,semitones),quality,inversion)
    return {'family':family,'chord':h,'target':target,'leading_tone':offset(target_root,6,11),
            'textbook_profile':'outside_basic_target_profile' if family=='vii_half7' and target_quality=='m' else 'basic_target_compatible',
            'profile_is_universal_prohibition':False,'function_confirmed':None}


def source_applied(annotation,tonic,alter=0,mode='major'):
    r=annotation['raw_fields'];token=r.get('relativeroot','')
    if not token or r.get('localkey_is_minor')!=('1' if mode=='minor' else '0'):return None
    if any(r.get(k) for k in ('changes','added_tones','pedal','special')):return None
    try:target=target_reference(token,tonic,alter,mode)
    except ValueError:return None
    n,form,ct,fig=(r.get(k,'') for k in ('numeral','form','chord_type','figbass'))
    leading='#vii' if target['quality']=='m' else 'vii'
    family={('V','','M'):'V',('V','','Mm7'):'V7',
            (leading,'o','o'):'vii',(leading,'o','o7'):'vii7',(leading,'%','%7'):'vii_half7'}.get((n,form,ct))
    if family is None:return None
    inv=({'':0,'6':1,'64':2} if family in ('V','vii') else {'7':0,'65':1,'43':2,'2':3,'42':3}).get(fig)
    return hypothesis(target['root'],target['quality'],family,inv) if inv is not None else None


def source_harmony(annotation,tonic,alter=0,mode='major'):
    app=source_applied(annotation,tonic,alter,mode)
    return app['chord'] if app else source_chord(annotation,tonic,alter,mode)


def contextualize(h,previous=None,following=None,home=None):
    h=hypothesis(h['target']['root'],h['target']['quality'],h['family'],h['chord']['inversion'])
    def matches(c):
        if c is None:return None
        c=chord(c['root'],c['quality'],c['inversion'])
        return c['members'][:3]==h['target']['members']
    before,after=matches(previous),matches(following);roles=[]
    if after:roles.append('forward_target_compatible')
    if before and after:roles.append('connects_statements_of_target')
    elif before:roles.append('back_relating_possible_needs_larger_context')
    continuations=[]
    if following is not None:
        following=chord(following['root'],following['quality'],following['inversion'])
        for family in FAMILIES:
            candidate=hypothesis(h['target']['root'],h['target']['quality'],family)['chord']
            if following['members']==candidate['members']:continuations.append(family)
    if after is False:
        roles.append('continues_applied_family_candidate' if continuations else 'target_not_immediate_intervening_irregular_or_altered_harmony_open')
    home_coordinates=[];warnings=[]
    if home:
        tonic,alter,mode=home
        if mode not in ('major','minor'):raise ValueError('invalid_mode')
        for s,a in h['chord']['members']:
            c=major_degree(s,a,tonic,alter);i=c['degree']-1
            c['alteration_from_home_form']=c['alteration_from_major']+SCALES['major'][i]-SCALES['natural_minor' if mode=='minor' else 'major'][i]
            home_coordinates.append(c)
        if h['family']=='V' and h['chord']['root']==[tonic,alter] and mode=='major':warnings.append('identical_to_home_tonic_triad_not_applied_proof')
        root=major_degree(*h['chord']['root'],tonic,alter)
        if mode=='major' and (root['degree'],root['alteration_from_major'])==(3,0):warnings.append('altered_mediant_or_secondary_mixture_competes')
    return {'previous_has_target_triad_core':before,'following_has_target_triad_core':after,
            'role_candidates':roles,'following_applied_family_compatibility':continuations,'home_coordinates':home_coordinates,'warnings':warnings,
            'applied_function':None,'tonicization':None,'modulation':None,'cadence':None,
            'basis':'supplied_harmonic_context_not_independent_inference'}


def observe(ir,span,context_span,h):
    h=hypothesis(h['target']['root'],h['target']['quality'],h['family'],h['chord']['inversion'])
    a,b=(_exact(span[k]) for k in ('start','end'));left,right=(_exact(context_span[k]) for k in ('start','end'))
    if not 0<=left<=a<b<=right:raise ValueError('invalid_context_or_target_span')
    notes={n['note_id']:n for n in ir['note_events']}
    if len(notes)!=len(ir['note_events']):raise ValueError('duplicate_note_id')
    rows=[];voices=defaultdict(list);seen=set();excluded=[]
    for s in ir['sounding_events']:
        sid=s['sounding_event_id'];x,y=(_exact(s['span'][k]) for k in ('start','end'))
        if sid in seen:raise ValueError('duplicate_sounding_id')
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
        matches=[o for o in voices[tuple(r['voice'])] if (o['y']==edge if entry else o['x']==edge)]
        if not matches:return 'no_touching_event',None
        if len(matches)!=1 or ambiguous(matches[0]):return 'ambiguous_voice',None
        return 'direct',matches[0]
    target=[r for r in rows if r['x']<b and r['y']>a];paths=[]
    critical={'leading_tone':h['leading_tone']}
    if len(h['chord']['members'])==4:critical['seventh']=h['chord']['members'][3]
    for r in target:
        role=next((k for k,v in critical.items() if r['pitch'][:2]==v),None)
        if role is None:continue
        entry_status,entry=neighbor(r,True);chain=[r]
        while True:
            status,dest=neighbor(chain[-1])
            if not dest or dest['pitch']!=r['pitch']:break
            chain.append(dest)
        motion=spelled_interval(r['pitch'],dest['pitch']) if dest else None
        tags=[]
        if motion:
            if role=='leading_tone' and motion['generic']==2 and motion['semitones']==1 and dest['pitch'][:2]==h['target']['root']:tags.append('leading_tone_to_target_root')
            if role=='seventh' and motion['generic']==-2 and motion['semitones'] in (-1,-2):tags.append('seventh_descending_step')
        entry_motion=spelled_interval(entry['pitch'],r['pitch']) if entry else None
        paths.append({'role':role,'event':public(r),'entry_status':entry_status,'entry':public(entry) if entry else None,
                      'entry_motion':entry_motion,'same_pitch_chain':[public(s) for s in chain],
                      'departure_status':status,'departure':public(dest) if dest else None,'motion':motion,'geometry_tags':tags,
                      'destination_in_target_triad':dest['pitch'][:2] in h['target']['members'] if dest else None,
                      'at_or_after_supplied_end':bool(dest and dest['x']>=b),'resolution_verified':None})
    inventory=span_observation(ir,span);members={tuple(p) for p in h['chord']['members']}
    for cell in inventory['slices']:
        # Grace may have a nonzero source duration: use the validated non-grace rows.
        cell['events']=[r for r in cell['events'] if r['event_id'] not in excluded]
        pitches=[r['pitch'] for r in cell['events']];unique={tuple(p[:2]) for p in pitches}
        lowest=min(pitches,key=lambda p:12*(p[2]+1)+NATURAL[LETTERS.index(p[0])]+p[1]) if pitches else None
        cell['complete_supplied_match']=unique==members and lowest[:2]==h['chord']['expected_bass'] if lowest else False
    inventory['union_events']=[r for r in inventory['union_events'] if r['event_id'] not in excluded]
    inventory['held_at_start_ids']=[r for r in inventory['held_at_start_ids'] if r not in excluded]
    union={tuple(r['pitch'][:2]) for r in target}
    return {'version':VERSION,'hypothesis':h,'target_span':span,'context_span':context_span,
            'events':[public(r) for r in target],'critical_paths':paths,'surface':inventory,
            'missing_spellings':sorted(members-union),'extra_event_refs':[r['event_id'] for r in target if tuple(r['pitch'][:2]) not in members],
            'excluded_grace_event_ids':excluded,'union_is_simultaneous':False,'function_confirmed':None,'production_enabled':False,
            'limitations':['key, target, family, inversion and ranges are supplied',
                'IR voice continuity is not guaranteed contrapuntal voice identity',
                'only touching same-voice paths after repeated pitch; no transfer/delay/pedal inference',
                'independent leading-tone and seventh paths do not prove simultaneous resolution',
                'absence of direct resolution does not refute applied function',
                'no harmony boundary, cadence, tonicization or modulation decision']}
