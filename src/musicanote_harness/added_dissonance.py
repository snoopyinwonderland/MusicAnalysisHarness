"""Unit28 added tones relative to an explicit dominant-seventh reference.

This is not a jazz extension classifier or an NCT verdict. The base reference
does not assert that its absent tones are present in the score.
"""
from collections import defaultdict
from copy import deepcopy
from .applied_chords import offset, source_harmony
from .seventh_context import chord
from .dominant_area_evidence import _exact
from .foundation_sonata_audit import pitch_tuple
from .formal_ir import q
from .tonal_foundations import spelled_interval, LETTERS, NATURAL

VERSION='added-dissonance-0.1.0'
EXTENSIONS={'minor_ninth':(1,1),'major_ninth':(1,2),'fourth_or_eleventh':(3,5),
            'minor_sixth_or_thirteenth':(5,8),'major_sixth_or_thirteenth':(5,9)}


def source_reference(annotation,key):
    """A deliberately counterfactual base, NEVER the full modified source chord."""
    r=annotation['raw_fields']
    if r.get('numeral')!='V' or r.get('chord_type')!='Mm7' or r.get('form') or r.get('pedal') or r.get('special'):return None
    probe=deepcopy(annotation)
    for k in ('changes','added_tones'):probe['raw_fields'][k]=''
    c=source_harmony(probe,*key)
    if c is None or c['quality']!='Mm7':return None
    return {'base':c,'source_modifiers':{k:r.get(k,'') for k in ('changes','added_tones','relativeroot')},
        'source_annotation_id':annotation['annotation_id'],
        'basis':'hypothetical_dominant_seventh_reference_not_full_source_label',
        'source_modifier_semantics_applied':False}


def observe(ir,span,context_span,base):
    c=chord(base['root'],base['quality'],base['inversion'])
    if c['quality']!='Mm7':raise ValueError('dominant_seventh_reference_required')
    a,b=(_exact(span[k]) for k in ('start','end'));left,right=(_exact(context_span[k]) for k in ('start','end'))
    if not 0<=left<=a<b<=right:raise ValueError('invalid_context_span')
    notes={n['note_id']:n for n in ir['note_events']}
    if len(notes)!=len(ir['note_events']):raise ValueError('duplicate_note_id')
    rows=[];seen=set();voices=defaultdict(list);excluded=[]
    for s in ir['sounding_events']:
        sid=s['sounding_event_id'];x,y=(_exact(s['span'][k]) for k in ('start','end'))
        if sid in seen:raise ValueError('duplicate_sound_id')
        seen.add(sid)
        if x<0 or y<x:raise ValueError('invalid_event_time')
        if x>=right or y<left:continue
        refs=s.get('source_note_ids',[])
        if not refs or s.get('attack_note_id') not in refs or any(n not in notes for n in refs):raise ValueError('broken_note_reference')
        grace=any(notes[n].get('grace',{}).get('is_grace',False) for n in refs)
        if grace:excluded.append(sid);continue
        if x==y:raise ValueError('zero_nongrace_duration')
        keys={(notes[n].get('part_id'),notes[n].get('voice_id')) for n in refs}
        voice=next(iter(keys)) if len(keys)==1 else None
        if voice and not all(voice):voice=None
        r={'event_id':sid,'pitch':list(pitch_tuple(s)),'span':s['span'],
           'source_note_ids':list(refs),'voice':list(voice) if voice else None,'x':x,'y':y}
        rows.append(r)
        if voice:voices[voice].append(r)
    def public(r):return {k:v for k,v in r.items() if k not in ('x','y')}
    def ambiguous(r):return any(o is not r and max(o['x'],r['x'],left)<min(o['y'],r['y'],right) for o in voices[tuple(r['voice'])])
    def neighbor(r,entry=False):
        if not r['voice']:return 'missing_voice',None
        if ambiguous(r):return 'ambiguous_voice',None
        edge=r['x'] if entry else r['y']
        if (edge<=left if entry else edge>=right):return 'context_censored',None
        found=[o for o in voices[tuple(r['voice'])] if (o['y']==edge if entry else o['x']==edge)]
        if not found:return 'no_touching_event',None
        if len(found)!=1 or ambiguous(found[0]):return 'ambiguous_voice',None
        return 'direct',found[0]
    def departure(r):
        chain=[r]
        while True:
            status,nxt=neighbor(chain[-1])
            if nxt is None or nxt['pitch']!=r['pitch']:return chain,status,nxt
            chain.append(nxt)
    spellings={name:offset(c['root'],*v) for name,v in EXTENSIONS.items()}
    spellings['seventh']=c['members'][3]
    target=[r for r in rows if r['x']<b and r['y']>a];paths=[]
    for r in target:
        role=next((k for k,p in spellings.items() if p==r['pitch'][:2]),None)
        if role is None:continue
        es,prev=neighbor(r,True);chain,status,nxt=departure(r)
        motion=spelled_interval(r['pitch'],nxt['pitch']) if nxt else None
        intended={'minor_ninth':c['root'],'major_ninth':c['root'],
            'fourth_or_eleventh':c['members'][1],
            'minor_sixth_or_thirteenth':c['members'][2],
            'major_sixth_or_thirteenth':c['members'][2]}.get(role)
        step=bool(motion and motion['generic']==-2 and motion['semitones'] in (-1,-2))
        later=None
        if nxt:_,_,later=departure(nxt)
        roots=[o for o in target if o['pitch'][:2]==c['root'] and max(o['x'],r['x'],a)<min(o['y'],r['y'],b)]
        root_intervals=[{'root_event_id':o['event_id'],'interval':spelled_interval(o['pitch'],r['pitch'])} for o in roots]
        paths.append({'role':role,'event':public(r),'entry_status':es,'entry':public(prev) if prev else None,
            'same_pitch_chain':[public(x) for x in chain],'departure_status':status,'departure':public(nxt) if nxt else None,
            'motion':motion,'descending_step_geometry':step,
            'arrives_at_reference_target_spelling':bool(step and intended and nxt['pitch'][:2]==intended),
            'departure_position':None if not nxt else 'inside_supplied_span' if nxt['x']<b else 'at_or_after_supplied_end',
            'retained_to_supplied_end':chain[-1]['y']>=b,
            'following_pitch_after_departure':public(later) if later else None,
            'root_then_seventh_geometry':bool(role in ('minor_ninth','major_ninth') and nxt and later and
                step and nxt['pitch'][:2]==c['root'] and later['pitch'][:2]==c['members'][3] and
                spelled_interval(nxt['pitch'],later['pitch'])['generic']==-2 and
                spelled_interval(nxt['pitch'],later['pitch'])['semitones'] in (-1,-2)),
            'simultaneous_root_intervals':root_intervals,'resolution_verified':None,'nct_label':None})
    points=sorted({a,b,*[max(a,r['x']) for r in target],*[min(b,r['y']) for r in target]})
    cells=[];core=[tuple(p) for p in c['members']]
    for x,y in zip(points,points[1:]):
        active=[r for r in target if r['x']<=x<r['y']];actual={tuple(r['pitch'][:2]) for r in active}
        bass=min(active,key=lambda r:12*(r['pitch'][2]+1)+NATURAL[LETTERS.index(r['pitch'][0])]+r['pitch'][1]) if active else None
        present={role:tuple(c['members'][i]) in actual for i,role in enumerate(('root','third','fifth','seventh'))}
        extensions=[name for name,p in spellings.items() if name!='seventh' and tuple(p) in actual]
        alternatives=[]
        if any(n in extensions for n in ('minor_ninth','major_ninth')):
            if present['root'] and present['third'] and present['seventh']:
                alternatives.append('dominant_seventh_plus_ninth_support_not_verdict')
                if not present['fifth']:alternatives.append('fifth_absent_with_identity_tones_present')
            if not present['third'] and all(present[k] for k in ('root','fifth','seventh')):
                alternatives.append('upper_supertonic_shape_over_root_pedal_function_unverified')
            if not present['root'] and all(present[k] for k in ('third','fifth','seventh')):
                alternatives.append('leading_tone_seventh_or_rootless_ninth_compete_no_root_invented')
        if 'fourth_or_eleventh' in extensions and not present['third'] and present['root'] and present['seventh']:
            alternatives.append('fourth_replacing_third_shape')
        if any(n in extensions for n in ('minor_sixth_or_thirteenth','major_sixth_or_thirteenth')) and not present['fifth'] and present['root'] and present['seventh']:
            alternatives.append('sixth_replacing_fifth_shape')
        cells.append({'span':{'start':q(x),'end':q(y)},'event_refs':[r['event_id'] for r in active],
            'reference_members_present':present,'extension_spellings_present':extensions,
            'bass_event_ref':bass['event_id'] if bass else None,
            'reference_root_is_lowest':bass['pitch'][:2]==c['root'] if bass else None,
            'alternative_shape_candidates':alternatives,
            'unexplained_event_refs':[r['event_id'] for r in active if tuple(r['pitch'][:2]) not in core and r['pitch'][:2] not in spellings.values()]})
    return {'version':VERSION,'base_reference':c,'target_span':span,'context_span':context_span,
        'events':[public(r) for r in target],'paths':paths,'slices':cells,'excluded_grace_refs':excluded,
        'harmonic_label':None,'nct_labels':None,'boundary_change':None,'production_enabled':False,
        'limitations':['source key/base/span conditioned, not blind harmony inference',
            '9/11/13 role names describe spelled classes; actual compound intervals are separately observed',
            'descending geometry can be a passing event rather than a resolution',
            'IR voice identity may differ from contrapuntal voice; gaps/polyphony cause abstention',
            'no inferred preparation/accent, transferred/implied resolution or pedal function',
            'Classical/Romantic textbook profile is not a universal rule for jazz or modern harmony']}
