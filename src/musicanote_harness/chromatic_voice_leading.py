"""Unit32 literal line geometry; no inferred harmony, reduction or function.

Runs use explicit IR voices only. Neither source harmony labels nor keys enter
the detector. A step pattern is not proof of a compositional sequence or scale.
"""
from collections import Counter, defaultdict
from itertools import combinations
from .dominant_area_evidence import _exact
from .formal_ir import q
from .foundation_sonata_audit import pitch_tuple
from .tonal_foundations import spelled_interval

VERSION='chromatic-voice-leading-0.1.0'


def _midi(p):return 12*(p[2]+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[p[0]]+p[1]


def _span(rows):return {'start':rows[0]['span']['start'],'end':rows[-1]['span']['end']}


def _blocks(ir,span):
    left,right=(_exact(span[k]) for k in ('start','end'))
    if not 0<=left<right:raise ValueError('positive_span_required')
    notes={n['note_id']:n for n in ir['note_events']}
    if len(notes)!=len(ir['note_events']):raise ValueError('duplicate_note_id')
    voices=defaultdict(list);seen=set();graces=[];missing=[]
    for s in ir['sounding_events']:
        sid=s['sounding_event_id'];a,b=(_exact(s['span'][k]) for k in ('start','end'))
        if sid in seen:raise ValueError('duplicate_sounding_id')
        seen.add(sid)
        if not 0<=a<=b:raise ValueError('invalid_sounding_time')
        if a>=right or b<left or (b==left and b>a):continue
        refs=s['source_note_ids']
        if not refs or s['attack_note_id'] not in refs or any(n not in notes for n in refs):raise ValueError('broken_note_reference')
        ns=[notes[n] for n in refs];p=list(pitch_tuple(s))
        if any(n.get('grace',{}).get('is_grace') for n in ns):
            graces.append({'event_id':sid,'source_note_ids':refs,'pitch':p,'span':s['span'],
                'structural_role':None,'reason':'notated_grace_not_assumed_ornamental'});continue
        if a==b:raise ValueError('zero_duration_non_grace')
        keys={(n.get('part_id'),n.get('voice_id')) for n in ns}
        v=next(iter(keys)) if len(keys)==1 else None
        if not v or not all(v):missing.append(sid);continue
        voices[v].append({'event_id':sid,'source_note_ids':refs,'pitch':p,'span':s['span'],'voice':list(v)})
    blocks=[];ambiguous=[];breaks=Counter()
    for voice,rows in sorted(voices.items()):
        rows.sort(key=lambda r:(_exact(r['span']['start']),r['event_id']))
        # Mark both sides of overlap, including a long event enclosing many
        # shorter notes. Sorting a notated chord must not invent a melody.
        max_end=None;block=[]
        for i,r in enumerate(rows):
            a,b=(_exact(r['span'][k]) for k in ('start','end'))
            overlap=(max_end is not None and max_end>a) or (i+1<len(rows) and _exact(rows[i+1]['span']['start'])<b)
            max_end=max(b,max_end) if max_end is not None else b
            if overlap:
                ambiguous.append(r['event_id']);breaks['polyphonic_voice']+=1
                if block:blocks.append(block);block=[]
                continue
            if block and _exact(block[-1]['span']['end'])!=a:
                breaks['gap']+=1;blocks.append(block);block=[]
            block.append(r)
        if block:blocks.append(block)
    return blocks,{'grace_events_pending_role':graces,'ambiguous_voice_event_ids':ambiguous,
                   'missing_voice_event_ids':missing,'block_breaks':dict(breaks)}


def _record(rows,pattern):
    intervals=[spelled_interval(a['pitch'],b['pitch']) for a,b in zip(rows,rows[1:])]
    steps=[x['semitones'] for x in intervals];windows=[]
    width=(12//abs(steps[0])) if pattern=='equal_step_run' else 8 if pattern=='alternating_one_two_run' else None
    if width:
        for i in range(len(rows)-width):
            if abs(_midi(rows[i+width]['pitch'])-_midi(rows[i]['pitch']))==12:
                windows.append({'first_index':i,'last_index':i+width,
                    'spelled_octave':rows[i]['pitch'][:2]==rows[i+width]['pitch'][:2]})
    return {'pattern':pattern,'span':_span(rows),'voice':rows[0]['voice'],'events':rows,
        'intervals':intervals,'semitone_steps':steps,'direction':'ascending' if steps[0]>0 else 'descending',
        'complete_octave_windows':windows,'contains_same_letter_inflection':any(abs(x['generic'])==1 for x in intervals),
        'harmonic_function':None,'sequence_confirmed':None,'scale_usage_confirmed':None,
        'basis':'ordered_touching_sounding_events_not_pitch_class_union'}


def _runs(rows):
    deltas=[_midi(b['pitch'])-_midi(a['pitch']) for a,b in zip(rows,rows[1:])]
    found=[];i=0
    while i<len(deltas):
        step=deltas[i];j=i+1
        while j<len(deltas) and deltas[j]==step:j+=1
        if abs(step) in (1,2,3,4,6) and j-i>=2:
            found.append(_record(rows[i:j+1],'chromatic_semitone_run' if abs(step)==1 else 'equal_step_run'))
        i=j
    # At least three alternating steps; four tones are still only a fragment.
    i=0
    while i<len(deltas):
        j=i+1
        while j<len(deltas) and abs(deltas[j]) in (1,2) and abs(deltas[j-1]) in (1,2) and deltas[j]*deltas[j-1]>0 and abs(deltas[j])!=abs(deltas[j-1]):j+=1
        if j-i>=3:found.append(_record(rows[i:j+1],'alternating_one_two_run'))
        i=max(i+1,j-1)
    return found


def pair_geometry(first,second):
    """Strict synchronized semitone runs only; oblique/staggered paths deferred."""
    a,b=first['events'],second['events']
    if first['pattern']!='chromatic_semitone_run' or second['pattern']!='chromatic_semitone_run':return None
    if first['voice']==second['voice'] or len(a)!=len(b):return None
    if any(any(_exact(x['span'][k])!=_exact(y['span'][k]) for k in ('start','end')) for x,y in zip(a,b)):return None
    if all(_midi(x['pitch'])>_midi(y['pitch']) for x,y in zip(a,b)):a,b=b,a
    if not all(_midi(x['pitch'])<_midi(y['pitch']) for x,y in zip(a,b)):return None
    vertical=[spelled_interval(x['pitch'],y['pitch']) for x,y in zip(a,b)]
    same_direction=first['direction']==second['direction']
    swap_pc=(_midi(a[0]['pitch'])%12==_midi(b[-1]['pitch'])%12 and _midi(b[0]['pitch'])%12==_midi(a[-1]['pitch'])%12)
    swap_spelling=a[0]['pitch'][:2]==b[-1]['pitch'][:2] and b[0]['pitch'][:2]==a[-1]['pitch'][:2]
    exchange=not same_direction and (vertical[0]['generic'],vertical[-1]['generic']) in ((6,10),(10,6)) and swap_pc
    if not same_direction and not exchange:return None
    return {'pattern':'parallel_chromatic_motion' if same_direction else 'six_ten_exchange_geometry',
        'span':_span(a),'lower_voice':a[0]['voice'],'upper_voice':b[0]['voice'],
        'lower_events':a,'upper_events':b,'vertical_intervals':vertical,
        'endpoint_exchange_pitch_class':swap_pc,'endpoint_exchange_spelling':swap_spelling,
        'stable_spelled_interval':len({(v['generic'],v['semitones']) for v in vertical})==1,
        'harmonic_prolongation':None,'cadence':None,'merge_recommended':None,
        'basis':'synchronized_explicit_IR_voices_not_reconstructed_structural_voices'}


def observe(ir,span):
    blocks,diagnostics=_blocks(ir,span)
    lines=[r for b in blocks for r in _runs(b)]
    groups=defaultdict(list)
    for r in lines:
        if r['pattern']=='chromatic_semitone_run':
            groups[tuple((_exact(x['span']['start']),_exact(x['span']['end'])) for x in r['events'])].append(r)
    pairs=[p for rows in groups.values() for a,b in combinations(rows,2) if (p:=pair_geometry(a,b))]
    return {'version':VERSION,'span':span,'lines':lines,'pairs':pairs,'diagnostics':diagnostics,
        'source_annotations_used_for_detection':False,'production_enabled':False,
        'limitations':['no latent voice separation; no highest-note substitution',
            'grace role is unresolved, not evidence of structural unimportance',
            'repeated attacks, gaps, overlap and direction changes break literal runs',
            'short equal-step/alternating patterns are not evidence of a whole scale',
            'parallel motion does not certify parallel 6/3 harmony',
            'staggered/oblique/partial/altered exchanges, suspension series and omnibus inference deferred',
            'no harmonic roots, keys, NCT, cadence, phrase or automatic boundary merging']}
