"""Unit 20: conditional 6/4 roles and separate direct IR motion evidence.

No cadence decision, metric inference, latent voice extraction or relabeling.
"""
from collections import defaultdict
from .six_three_context import source_triad as previous_source_triad, triad as previous_triad
from .root_position_context import root_relation
from .dominant_area_evidence import _exact
from .foundation_sonata_audit import pitch_tuple
from .formal_ir import q
from .tonal_foundations import LETTERS, NATURAL, spelled_interval, spelled_triad_shapes

VERSION = 'six-four-context-0.1.0'


def source_triad(annotation):
    raw = annotation['raw_fields']
    figure = raw.get('figbass', '')
    if figure not in ('', '6', '64'):
        return None
    item = previous_source_triad({'raw_fields': {**raw, 'figbass': ''}})
    return (item[0], {'':0, '6':1, '64':2}[figure]) if item else None


def triad(symbol, inversion, tonic, alter=0, mode='major'):
    if type(inversion) is not int or inversion not in (0, 1, 2):
        raise ValueError('triad_inversion_required')
    c = previous_triad(symbol, min(inversion, 1), tonic, alter, mode)
    if inversion == 2:
        i = LETTERS.index(c['root_step'])
        j = (i+4) % 7
        fifth = {'major':7, 'minor':7, 'diminished':6, 'augmented':8}[c['quality']]
        c['expected_bass_spelling'] = [LETTERS[j], NATURAL[i]+c['root_alter']+fifth-NATURAL[j]-(12 if j<i else 0)]
        c['inversion'] = 2
    return c


def propose(symbols, inversions, tonic, alter=0, mode='major'):
    if len(symbols) != 3 or len(inversions) != 3:
        raise ValueError('three_supplied_triads_required')
    cs = [triad(s,i,tonic,alter,mode) for s,i in zip(symbols,inversions)]
    bass = [c['expected_bass_spelling'] for c in cs]
    br = [root_relation({'root_step':a[0],'root_alter':a[1]},
                        {'root_step':b[0],'root_alter':b[1]}) for a,b in zip(bass,bass[1:])]
    roles = []
    def add(role, indices, sections, needs, **extras):
        roles.append({'role':role, 'indices':indices, 'sections':sections, 'status':'candidate',
                      'needs_evidence':['actual_score_support','governing_harmony_and_metric_context',*needs], **extras})
    def family(a,b):
        return all(a[k]==b[k] for k in ('root_step','root_alter','quality'))
    def step(r):
        return (r['diatonic_steps_up_mod7'],r['semitones_up_mod12']) in ((1,1),(1,2),(6,10),(6,11))
    if inversions[1] == 2:
        if all(step(r) for r in br) and br[0]['diatonic_steps_up_mod7']==br[1]['diatonic_steps_up_mod7']:
            add('moving_bass_passing_six_four',[0,1,2],[5,6],
                ['same_bass_voice_and_register_stepwise_motion','upper_voice_support','middle_harmonic_independence_unresolved'])
        if bass[0]==bass[1]==bass[2] and family(cs[0],cs[2]) and inversions[0]==inversions[2]==0:
            relation = root_relation(cs[0],cs[1])
            if relation['diatonic_steps_up_mod7']==3 and relation['semitones_up_mod12']==5:
                add('stationary_bass_neighbor_six_four',[0,1,2],[4],
                    ['same_voice_3_4_3_and_5_6_5','bass_continuity'], weak_beat_required=False)
    for i,c in enumerate(cs):
        if c['inversion'] != 2:
            continue
        if c['symbol'] == ('viio' if mode=='major' else '#viio'):
            add('incomplete_dominant_four_two_alternative',[i],[17],
                ['actual_bass_degree4','bass_seventh_resolution','dominant_context','retain_literal_diminished_triad'],
                alternative='V42_without_root', source_wording_conflict='section17_vs_review12')
        for j in (i-1,i+1):
            if (0<=j<3 and c['quality'] in ('major','minor')
                    and cs[j]['inversion']!=2 and family(c,cs[j])):
                add('bass_arpeggiation_or_retrospective_stability',[min(i,j),max(i,j)],[13,14,15],
                    ['actual_bass_register_path','sustained_governing_harmony','exclude_expanded_cadential_context'],
                    oscillating_accompaniment_confirmed=False)
        if i<2 and cs[i+1]['inversion']==0 and bass[i]==bass[i+1]:
            rel = root_relation(cs[i+1],c)
            if rel['diatonic_steps_up_mod7']==3 and rel['semitones_up_mod12']==5:
                add('stationary_bass_six_four_to_five_three',[i,i+1],[3,9,10,12],
                    ['direct_or_traced_decorated_4_3_and_6_5','actual_bass_continuity','relative_accent_and_formal_goal'],
                    dominant_destination_candidate=cs[i+1]['symbol']=='V', strong_beat_required=False)
    return {'version':VERSION, 'basis':'supplied_hypotheses_not_blind_detection',
            'key_hypothesis':{'tonic_step':tonic,'tonic_alter':alter,'mode':mode},
            'candidates':cs,'nominal_bass_relations':br,'role_candidates':roles,
            'selected_role':None,'cadence':None,'phrase_boundary':None,'merge_recommended':None,
            'production_enabled':False,'limitations':[
                'nominal bass spelling does not prove a bass voice or register',
                'weak accent does not exclude cadential function; strong accent does not prove it',
                'seventh destinations, decorated paths, transfer, elision and exceptional finals deferred',
                'no candidate is not evidence of no six-four role']}


def assess_direct(ir, before_time, after_time):
    """Key/label-independent two-instant 6/4 -> 5/3 geometry.

    Only explicitly monophonic part/voice matches; no pitch sorting into voices.
    Full sounding spans retained, including ties. No metric/cadence verdict.
    """
    a,b = _exact(before_time), _exact(after_time)
    if a<0 or a>=b:
        raise ValueError('ordered_nonnegative_instants_required')
    notes = {n['note_id']:n for n in ir['note_events']}
    if len(notes)!=len(ir['note_events']):
        raise ValueError('duplicate_note_id')
    rows, seen = [], set()
    for s in ir['sounding_events']:
        sid=s['sounding_event_id']
        if sid in seen: raise ValueError('duplicate_sounding_id')
        seen.add(sid)
        x,y=(_exact(s['span'][k]) for k in ('start','end'))
        if x<0 or y<x: raise ValueError('invalid_sounding_span')
        if not (x<=a<y or x<=b<y): continue
        n=notes.get(s.get('attack_note_id'))
        if n is None: raise ValueError('missing_attack_note_reference')
        if n.get('grace',{}).get('is_grace'): continue
        pitch=list(pitch_tuple(s))
        rows.append({'event_id':sid,'pitch':pitch,'source_note_ids':s['source_note_ids'],
                     'original_span':s['span'],'voice_ref':[n.get('part_id'),n.get('voice_id')],
                     'on':x,'off':y})
    def height(row):
        p=row['pitch']; return 12*(p[2]+1)+NATURAL[LETTERS.index(p[0])]+p[1]
    active=[[r for r in rows if r['on']<=t<r['off']] for t in (a,b)]
    lows=[[r for r in group if height(r)==min(map(height,group))] if group else [] for group in active]
    groups=[defaultdict(list),defaultdict(list)]
    for d,group in zip(groups,active):
        for r in group:
            if all(r['voice_ref']): d[tuple(r['voice_ref'])].append(r)
    motions, ambiguous = [], []
    bass_pairs=[]
    for ident in sorted(set(groups[0])&set(groups[1])):
        xs,ys=groups[0][ident],groups[1][ident]
        if len(xs)!=1 or len(ys)!=1:
            ambiguous.append(list(ident)); continue
        x,y=xs[0],ys[0]
        continuous=x['event_id']==y['event_id'] or x['off']==y['on']
        is_bass=x in lows[0] and y in lows[1] and x['pitch']==y['pitch'] and continuous
        if is_bass: bass_pairs.append((x,y))
        motions.append({'voice_ref':list(ident),'event_refs':[x['event_id'],y['event_id']],
                        'direct_temporal_connection':continuous,'stationary_lowest_voice':is_bass,
                        'semitones':height(y)-height(x),'relation':None})
    shapes=[spelled_triad_shapes([r['pitch'] for r in group]) for group in active]
    surface=any(s['inversion']==2 for s in shapes[0]) and any(s['inversion']==0 for s in shapes[1])
    # A spelled, same-register stationary bass must be established before labeling
    # upper motions; retained duplicate basses are evidence, not sorted voice pairs.
    for m in motions:
        x=next(r for r in rows if r['event_id']==m['event_refs'][0])
        y=next(r for r in rows if r['event_id']==m['event_refs'][1])
        if not m['direct_temporal_connection'] or m['semitones'] not in (-1,-2): continue
        for lo,hi in bass_pairs:
            iv1=spelled_interval(lo['pitch'],x['pitch'])['generic']
            iv2=spelled_interval(hi['pitch'],y['pitch'])['generic']
            if iv1>0 and iv2>0:
                pair=((iv1-1)%7+1,(iv2-1)%7+1)
                if pair in ((4,3),(6,5)): m['relation']=f'{pair[0]}_to_{pair[1]}'
    links={m['relation'] for m in motions}
    return {'version':VERSION,'basis':'score_events_without_key_or_harmony_labels',
            'instants':[q(a),q(b)],'complete_triad_shapes':shapes,
            'bass_event_pairs':[[x['event_id'],y['event_id']] for x,y in bass_pairs],
            'motion_evidence':motions,'ambiguous_voice_refs':ambiguous,
            'surface_pair_supported':bool(surface),
            'direct_resolution_geometry_supported':bool(surface and bass_pairs and {'4_to_3','6_to_5'}<=links),
            'events':[{k:v for k,v in r.items() if k not in ('on','off')} for r in rows],
            'metric_relation':'unassessed','functional_verdict':None,'cadence':None,
            'production_enabled':False,
            'limitations':['two instants only','no latent polyphonic voice separation',
                           'no decorated or transferred resolution reconstruction','geometry is not a cadence']}
