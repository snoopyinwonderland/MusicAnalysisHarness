"""Unit31 competing chromatic shapes and direct paths, not function labels."""
from collections import defaultdict
from copy import deepcopy
from .applied_chords import offset, source_harmony
from .seventh_context import chord
from .diatonic_modulation import validate_key, observe_support
from .augmented_sixth import pc
from .dominant_area_evidence import _exact
from .foundation_sonata_audit import pitch_tuple
from .tonal_foundations import spelled_interval

VERSION='chromatic-embellishment-0.1.0'


def mixture_routes(h,key):
    """Selected Unit31 major-mode additions; not an exhaustive mixture grammar."""
    step,alter,mode=validate_key(key)
    if h is None or mode!='major':return []
    h=chord(h['root'],h['quality'],h['inversion'])
    definitions=[('simple_bIII','simple',2,3,'M'),('simple_v','simple',4,7,'m'),
        ('simple_bVII','simple',6,10,'M'),('secondary_III','secondary',2,4,'M'),
        ('secondary_VI','secondary',5,9,'M'),('double_bii','double',1,1,'m'),
        ('double_biii','double',2,3,'m'),('double_bvi','double',5,8,'m'),('double_bvii','double',6,10,'m')]
    return [{'name':name,'type_hypothesis':kind,'selected':False,'mixture_confirmed':None}
        for name,kind,s,d,quality in definitions
        if h['members']==chord(offset([step,alter],s,d),quality)['members']]


def augmented_source(annotation,key):
    key=validate_key(key)
    r=annotation['raw_fields']
    if r.get('chord_type')!='+' or r.get('form')!='+':return None
    if any(r.get(k) for k in ('changes','added_tones','pedal','special')):return None
    inv={'':0,'6':1,'64':2}.get(r.get('figbass',''))
    if inv is None:return None
    # Parse the root via an explicit hypothetical major counterpart. Do not
    # strip a slash: existing applied adapter accepts only a single target.
    base=deepcopy(annotation);base['raw_fields'].update(form='',chord_type='M')
    h=source_harmony(base,*key)
    return chord(h['root'],'+',inv) if h else None


def altered_dominant(root, alteration, inversion=0):
    """Theory template only; no source-modifier adapter or style verdict."""
    if type(alteration) is not int or alteration not in (-1,1):raise ValueError('signed_semitone_required')
    base=chord(root,'Mm7',inversion);members=deepcopy(base['members']);members[2][1]+=alteration
    return {'members':members,'expected_bass':members[inversion],'fifth_alteration':alteration,
        'base_reference':base,'basis':'supplied_dominant_seventh_reference','function':None}


def common_tone_comparison(current,target):
    a=chord(current['root'],current['quality'],current['inversion'])
    b=chord(target['root'],target['quality'],target['inversion'])
    if a['quality']!='o7' or b['quality'] not in ('M','m','Mm7'):raise ValueError('diminished7_and_supported_target_required')
    usual=[b['root'],offset(b['root'],1,3),offset(b['root'],3,6),offset(b['root'],5,9)]
    variant=[b['root'],offset(b['root'],2,3),offset(b['root'],3,6),offset(b['root'],5,9)]
    actual={tuple(p) for p in a['members']}
    return {'target_root_common_spelling':b['root'] in a['members'],
        'target_root_common_pitch_class':pc(b['root']) in {pc(p) for p in a['members']},
        'usual_spelling_match':actual=={tuple(p) for p in usual},
        'flat3_variant_match':actual=={tuple(p) for p in variant},
        'pitch_class_shape_match':{pc(p) for p in a['members']}=={pc(p) for p in usual},
        'target_minor_caution':b['quality']=='m','target64_not_stable_tonic':len(b['members'])==3 and b['inversion']==2,
        'common_tone_function':None,'applied_function':None,'cadence':None,
        'basis':'supplied_neighbor_hypotheses_not_sustained_tone_evidence'}


def direct_paths(ir,span,context_span,spellings):
    """Unambiguous IR voice, immediate entry and exit after same-pitch attacks."""
    a,b=(_exact(span[k]) for k in ('start','end'));left,right=(_exact(context_span[k]) for k in ('start','end'))
    if not 0<=left<=a<b<=right:raise ValueError('invalid_context')
    notes={n['note_id']:n for n in ir['note_events']}
    if len(notes)!=len(ir['note_events']):raise ValueError('duplicate_note_id')
    voices=defaultdict(list);rows=[];seen=set();excluded=[]
    for s in ir['sounding_events']:
        sid=s['sounding_event_id'];x,y=(_exact(s['span'][k]) for k in ('start','end'))
        if sid in seen:raise ValueError('duplicate_sounding_id')
        seen.add(sid)
        if x<0 or y<x:raise ValueError('invalid_event_time')
        if x>=right or y<left:continue
        refs=s['source_note_ids'];ns=[notes.get(n) for n in refs]
        if not refs or s['attack_note_id'] not in refs or any(n is None for n in ns):raise ValueError('broken_note_reference')
        pitch=list(pitch_tuple(s))
        if any(n.get('grace',{}).get('is_grace',False) for n in ns):excluded.append(sid);continue
        if x==y:raise ValueError('zero_duration_non_grace')
        keys={(n.get('part_id'),n.get('voice_id')) for n in ns};v=next(iter(keys)) if len(keys)==1 else None
        if v and not all(v):v=None
        row={'event_id':sid,'pitch':pitch,'span':s['span'],'source_note_ids':refs,'voice':list(v) if v else None,'x':x,'y':y}
        rows.append(row)
        if v:voices[v].append(row)
    def public(r):return {k:v for k,v in r.items() if k not in ('x','y')}
    def ambiguous(r):return any(o is not r and max(o['x'],r['x'],left)<min(o['y'],r['y'],right) for o in voices[tuple(r['voice'])])
    def neighbor(r,entry=False):
        if not r['voice']:return 'missing_voice',None
        if ambiguous(r):return 'ambiguous_voice',None
        edge=r['x'] if entry else r['y']
        if (edge<=left if entry else edge>=right):return 'context_censored',None
        matches=[o for o in voices[tuple(r['voice'])] if (o['y']==edge if entry else o['x']==edge)]
        if not matches:return 'no_touching_event',None
        if len(matches)!=1 or ambiguous(matches[0]):return 'ambiguous_voice',None
        return 'direct',matches[0]
    paths=[]
    for r in rows:
        if r['x']>=b or r['y']<=a or r['pitch'][:2] not in spellings:continue
        es,entry=neighbor(r,True);chain=[r]
        while True:
            status,dest=neighbor(chain[-1])
            if dest is None or dest['pitch']!=r['pitch']:break
            chain.append(dest)
        paths.append({'event':public(r),'entry_status':es,'entry':public(entry) if entry else None,
            'same_pitch_chain':[public(x) for x in chain],'departure_status':status,'departure':public(dest) if dest else None,
            'entry_motion':spelled_interval(entry['pitch'],r['pitch']) if entry else None,
            'departure_motion':spelled_interval(r['pitch'],dest['pitch']) if dest else None})
    return {'paths':paths,'excluded_grace_refs':excluded,'all_context_events':[public(r) for r in rows]}


def observe_augmented(ir,span,context_span,h):
    h=chord(h['root'],h['quality'],h['inversion'])
    if h['quality']!='+':raise ValueError('augmented_triad_required')
    ev=direct_paths(ir,span,context_span,[h['members'][2]])
    fifth=offset(h['root'],4,7);sixth=offset(h['root'],5,9)
    for p in ev['paths']:
        before=p['entry'];after=p['departure'];em=p['entry_motion'];dm=p['departure_motion'];tags=[]
        if before and before['pitch'][:2]==fifth and em['generic']==1 and em['semitones']==1:tags.append('perfect5_to_augmented5_chromatic_rise')
        if after and after['pitch'][:2]==sixth and dm['generic']==2 and dm['semitones']==1:tags.append('augmented5_to_sixth_semitone_rise')
        p['geometry_tags']=tags;p['nct_verdict']=None
    ev.pop('all_context_events')
    return {'version':VERSION,'hypothesis':h,'source_span':span,'context_span':context_span,
        'literal_support':observe_support(ir,span,h),'fifth_paths':ev,
        'harmonic_function':None,'nct_label':None,'production_enabled':False,
        'limitations':['supplied root/spelling/span; symmetric pitch-class roots not inferred',
            'only direct upper fifth geometry; bass descent, 5-6-5 and long figuration deferred',
            'augmented triad is not proof of an independent harmonic change']}


def observe_common_tone(ir,span,next_span,context_span,current,target):
    current=chord(current['root'],current['quality'],current['inversion'])
    target=chord(target['root'],target['quality'],target['inversion'])
    comparison=common_tone_comparison(current,target)
    edge=_exact(span['end']);na,nb=(_exact(next_span[k]) for k in ('start','end'))
    if edge!=na or nb<=na:raise ValueError('adjacent_positive_target_required')
    ev=direct_paths(ir,span,context_span,current['members'])
    available_end=min(nb,_exact(context_span['end']))
    if available_end<=edge:raise ValueError('following_context_required')
    for p in ev['paths']:
        dest=p['departure'];motion=p['departure_motion']
        p['step_into_supplied_target_span']=bool(dest and edge<=_exact(dest['span']['start'])<available_end
            and dest['pitch'][:2] in target['members'] and abs(motion['generic'])==2 and abs(motion['semitones']) in (1,2))
    # Presence across the boundary is stronger than pitch-class intersection,
    # but still does not prove all voices jointly resolved or a neighboring role.
    common=[]
    for p in ev['paths']:
        if p['event']['pitch'][:2]!=target['root']:continue
        chain=p['same_pitch_chain']
        if _exact(chain[0]['span']['start'])<edge<_exact(chain[-1]['span']['end']):
            common.append({'event_refs':[x['event_id'] for x in chain],
                'kind':'held_sounding_event' if len(chain)==1 else 'touching_same_pitch_reattacks',
                'not_sustained_proof':len(chain)>1})
    # Several selected attacks can yield suffixes of the same touching chain.
    common=[c for c in common if not any(set(c['event_refs'])<set(o['event_refs']) for o in common)]
    ev.pop('all_context_events')
    return {'version':VERSION,'comparison':comparison,'source_span':span,'next_span':next_span,
        'context_span':context_span,'current_hypothesis':current,'target_hypothesis':target,
        'literal_support':observe_support(ir,span,current),'voice_paths':ev,'common_root_links':common,
        'common_tone_function':None,'cadence':None,'production_enabled':False,
        'limitations':['source-conditioned adjacent hypotheses; not a common-tone classifier',
            'spelling alternatives retained; no enharmonic rewriting',
            'no simultaneous multi-voice resolution claim; minor/64 need special care',
            'common-tone augmented6 and apparent dominant7 deferred']}
