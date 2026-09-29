"""Unit29 conditional bII evidence. No inferred key, cadence or NCT verdict."""
from collections import defaultdict
from .applied_chords import offset, hypothesis as applied
from .seventh_context import chord, source_chord
from .diatonic_modulation import validate_key, observe_support
from .dominant_area_evidence import _exact
from .foundation_sonata_audit import pitch_tuple
from .tonal_foundations import spelled_interval

VERSION = 'neapolitan-evidence-0.1.0'


def hypothesis(key, inversion=1):
    step, alter, mode = validate_key(key)
    return chord(offset([step, alter], 1, 1), 'M', inversion)


def source_reference(annotation, key):
    if key is None:return None
    h = source_chord(annotation, *key)
    if h is None or h['quality'] != 'M' or h != hypothesis(key, h['inversion']):return None
    return h


def context_roles(h, key):
    """Shape compatibility only; e.g. tonic 64 is not a tonic arrival."""
    step, alter, mode = validate_key(key)
    if h is None:return None
    h = chord(h['root'], h['quality'], h['inversion'])
    root = [step, alter]; dominant = offset(root, 4, 7)
    roles = []
    if h['quality'] == 'M' and h == hypothesis(key, h['inversion']):
        roles.append('neapolitan_triad_shape')
    if h['root'] == dominant and h['quality'] in ('M', 'Mm7'):
        if h['quality'] == 'Mm7' or h['inversion'] != 2:roles.append('dominant_shape')
    if h['root'] == offset(root, 6, 11) and h['quality'] in ('o', 'o7', '%7'):
        roles.append('leading_tone_shape')
    if h == chord(root, 'm' if mode == 'minor' else 'M', 2):
        roles.append('tonic64_possible_dominant_decoration')
    for family in ('V', 'V7', 'vii', 'vii7', 'vii_half7'):
        if h['inversion'] == 3 and family in ('V','vii'):continue
        if h == applied(dominant, 'M', family, h['inversion'])['chord']:
            roles.append('applied_to_dominant_shape');break
    return roles


def compare_context(rows, key):
    """Retain every original neighbor. Unknowns/gaps never imply a connection."""
    validate_key(key)
    refs = [r['ref'] for r in rows]
    if any(not isinstance(r, str) or not r for r in refs) or len(set(refs)) != len(refs):
        raise ValueError('unique_refs_required')
    times = [tuple(_exact(r['span'][k]) for k in ('start', 'end')) for r in rows]
    if any(a < 0 or b <= a for a, b in times):raise ValueError('positive_span_required')
    if any(a[0] > b[0] for a, b in zip(times, times[1:])):raise ValueError('ordered_rows_required')
    roles = [context_roles(r.get('hypothesis'), key) if r.get('verified') is True and r.get('key') is not None and tuple(r['key']) == tuple(key) else None for r in rows]
    paths = []
    for i, rs in enumerate(roles):
        if 'neapolitan_triad_shape' not in (rs or []):continue
        chain = [refs[i]]
        for j in range(i+1, len(rows)):
            if times[j-1][1] != times[j][0] or roles[j] is None:break
            nxt = roles[j];chain.append(refs[j])
            if any(r in nxt for r in ('dominant_shape', 'leading_tone_shape')):
                paths.append({'refs':chain, 'goal_shapes':nxt, 'function_confirmed':None});break
            if not any(r in nxt for r in ('neapolitan_triad_shape', 'tonic64_possible_dominant_decoration', 'applied_to_dominant_shape')):break
    return {'roles':[{'ref':ref,'shape_candidates':r} for ref,r in zip(refs,roles)],
            'compatible_paths':paths,'cadence':None,'modulation':None,'function':None,
            'basis':'supplied_key_and_chord_hypotheses_not_blind_inference'}


def observe(ir, span, context_span, key, inversion=1):
    h = hypothesis(key, inversion)
    a,b = (_exact(span[k]) for k in ('start','end'))
    left,right = (_exact(context_span[k]) for k in ('start','end'))
    if not 0 <= left <= a < b <= right:raise ValueError('invalid_context')
    notes = {n['note_id']:n for n in ir['note_events']}
    if len(notes) != len(ir['note_events']):raise ValueError('duplicate_note_id')
    rows=[];voices=defaultdict(list);seen=set();excluded=[]
    for s in ir['sounding_events']:
        sid=s['sounding_event_id'];x,y=(_exact(s['span'][k]) for k in ('start','end'))
        if sid in seen:raise ValueError('duplicate_sounding_id')
        seen.add(sid)
        if x<0 or y<x:raise ValueError('invalid_event_time')
        if x>=right or y<left:continue
        refs=s['source_note_ids'];ns=[notes.get(n) for n in refs]
        if not refs or s['attack_note_id'] not in refs or any(n is None for n in ns):raise ValueError('broken_note_reference')
        if any(n.get('grace',{}).get('is_grace',False) for n in ns):excluded.append(sid);continue
        if x==y:raise ValueError('zero_duration_non_grace')
        identities={(n.get('part_id'),n.get('voice_id')) for n in ns}
        voice=next(iter(identities)) if len(identities)==1 else None
        if voice and not all(voice):voice=None
        r={'event_id':sid,'pitch':list(pitch_tuple(s)),'source_note_ids':refs,
           'span':s['span'],'voice':list(voice) if voice else None,'x':x,'y':y}
        rows.append(r)
        if voice:voices[voice].append(r)
    def public(r):return {k:v for k,v in r.items() if k not in ('x','y')}
    def ambiguous(r):return any(o is not r and max(o['x'],r['x'],left)<min(o['y'],r['y'],right) for o in voices[tuple(r['voice'])])
    def next_event(r):
        if not r['voice']:return 'missing_voice',None
        if ambiguous(r):return 'ambiguous_voice',None
        if r['y']>=right:return 'context_censored',None
        matches=[o for o in voices[tuple(r['voice'])] if o['x']==r['y']]
        if not matches:return 'no_touching_event',None
        if len(matches)!=1 or ambiguous(matches[0]):return 'ambiguous_voice',None
        return 'direct',matches[0]
    def departure(r):
        chain=[r]
        while True:
            status,dest=next_event(chain[-1])
            if dest is None or dest['pitch']!=r['pitch']:return chain,status,dest
            chain.append(dest)
    tonic=list(key[:2]);leading=offset(tonic,6,11);paths=[]
    for r in rows:
        if r['x']>=b or r['y']<=a or r['pitch'][:2]!=h['root']:continue
        chain,status,dest=departure(r);tags=[];second=None;second_status=None;mid_chain=[]
        motion=spelled_interval(r['pitch'],dest['pitch']) if dest else None
        if motion and dest['pitch'][:2]==leading and motion['generic']==-3 and motion['semitones']==-2:
            tags.append('flat2_to_leading_descending_diminished_third')
        if motion and dest['pitch'][:2]==tonic and motion['generic']==-2 and motion['semitones']==-1:
            mid_chain,second_status,second=departure(dest)
            if second:
                m=spelled_interval(dest['pitch'],second['pitch'])
                if second['pitch'][:2]==leading and m['generic']==-2 and m['semitones']==-1:tags.append('flat2_tonic_leading_filled_diminished_third')
        if motion and dest['pitch'][:2]==offset(tonic,1,2) and motion['generic']==1 and motion['semitones']==1:
            tags.append('flat2_to_natural2_not_automatic_error')
        paths.append({'event':public(r),'same_pitch_chain':[public(x) for x in chain],
            'departure_status':status,'departure':public(dest) if dest else None,'motion':motion,
            'middle_chain':[public(x) for x in mid_chain],'second_status':second_status,
            'second_departure':public(second) if second else None,'geometry_tags':tags,'resolution_verified':None})
    return {'version':VERSION,'hypothesis':h,'source_span':span,'context_span':context_span,
        'literal_support':observe_support(ir,span,h),'flat2_paths':paths,'excluded_grace_refs':excluded,
        'harmonic_function':None,'nct_labels':None,'cadence':None,'production_enabled':False,
        'limitations':['explicit key, inversion and span required; not blind classification',
            'literal spelling retained; no enharmonic respelling or omitted-tone inference',
            'touching monophonic IR voice only; no transfer, gaps or implied resolution',
            'figuration may follow home or bII scale; extra tones are not automatically NCT',
            'passing/neighboring bII, tonicization, pivot and apparent bII65 remain alternatives']}
