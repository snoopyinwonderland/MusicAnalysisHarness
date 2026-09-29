"""Unit27 dual-key evidence, not an automatic modulation or cadence verdict.

Keys and chord hypotheses are explicit inputs. Common membership, local syntax,
duration and annotated key runs remain separate; none is a sufficient decision.
"""
from .applied_chords import offset
from .seventh_context import chord
from .tonal_foundations import SCALES, major_degree
from .dominant_area_evidence import _exact
from .formal_ir import q
from .foundation_sonata_audit import pitch_tuple
from .predominant_sonata_audit import span_observation

VERSION = 'diatonic-modulation-0.1.0'


def validate_key(key):
    step, alter, mode = key
    major_degree(step, alter, step, alter)
    if mode not in ('major', 'minor'):
        raise ValueError('major_minor_key_required')
    return step, alter, mode


def triads(key, include_harmonic_minor=False):
    step, alter, mode = validate_key(key)
    forms = ['major'] if mode == 'major' else ['natural_minor']
    if mode == 'minor' and include_harmonic_minor:
        forms.append('harmonic_minor')
    result = []
    for form in forms:
        scale = SCALES[form]
        for i in range(7):
            third = scale[(i+2) % 7] + 12*((i+2)//7) - scale[i]
            fifth = scale[(i+4) % 7] + 12*((i+4)//7) - scale[i]
            quality = {(4,7):'M', (3,7):'m', (3,6):'o', (4,8):'+'}[(third,fifth)]
            result.append({'degree':i+1, 'form':form,
                           'chord':chord(offset([step,alter],i,scale[i]),quality)})
    return result


def key_relation(old, new):
    old, new = validate_key(old), validate_key(new)
    if old == new:
        kind, degree = 'same_key', 1
    elif old[:2] == new[:2]:
        kind, degree = 'parallel_mode_not_diatonic_goal', 1
    else:
        target = chord(new[:2], 'M' if new[2]=='major' else 'm')
        matches = [t for t in triads(old) if t['chord']['members']==target['members']]
        degree = matches[0]['degree'] if matches else None
        kind = 'closely_related_diatonic_goal' if matches else 'outside_diatonic_goal_profile'
    return {'old_key':list(old), 'new_key':list(new), 'relation':kind,
            'degree_in_old_natural_form':degree, 'modulation':None}


def memberships(h, key):
    """Triad core membership is NOT full chord membership for a seventh."""
    if h is None:
        return None
    c = chord(h['root'], h['quality'], h['inversion'])
    return [{'degree':t['degree'], 'form':t['form'],
             'full_triad':len(c['members'])==3}
            for t in triads(key, True) if t['chord']['members']==c['members'][:3]]


def harmonic_roles(h, key):
    if h is None:
        return None
    c = chord(h['root'],h['quality'],h['inversion'])
    step,alter,mode = validate_key(key)
    tonic = chord([step,alter], 'M' if mode=='major' else 'm')
    dominant = chord(offset([step,alter],4,7),'M')
    roles = []
    # Tonic 6/4 is not treated as a stable arrival; seventh extensions excluded.
    if c['members']==tonic['members'] and c['inversion'] in (0,1):
        roles.append('tonic_triad_shape')
    if c['members'][:3]==dominant['members'] and c['quality'] in ('M','Mm7') and (len(c['members'])==4 or c['inversion']!=2):
        roles.append('dominant_shape')
    for t in triads(key):
        if t['degree'] in (2,4) and t['chord']['members']==c['members'][:3]:
            form = SCALES['major' if mode=='major' else 'natural_minor']
            scale_notes = {tuple(offset([step,alter],i,s)) for i,s in enumerate(form)}
            if all(tuple(p) in scale_notes for p in c['members']):
                roles.append('predominant_shape')
    return sorted(set(roles))


def compare_context(rows, old, new):
    """Ordered hypothesis rows; unknowns, gaps and overlaps never get bridged."""
    relation = key_relation(old,new)
    ids = [r['ref'] for r in rows]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('unique_nonempty_refs_required')
    times = [(_exact(r['span']['start']),_exact(r['span']['end'])) for r in rows]
    if any(a<0 or b<=a for a,b in times):raise ValueError('positive_span_required')
    if any(a[0]>b[0] for a,b in zip(times,times[1:])):raise ValueError('ordered_rows_required')
    compared = []
    for r in rows:
        h=r.get('hypothesis'); before=memberships(h,old); after=memberships(h,new)
        compared.append({'ref':r['ref'],'span':r['span'],
            'old_memberships':before,'new_memberships':after,
            'common_triad_compatible':None if h is None else bool(before and after and len(h['members'])==3),
            'new_key_role_candidates':harmonic_roles(h,new), 'pivot_verified':None})
    pairs=[]; triples=[]; breaks=[]
    for i in range(1,len(rows)):
        if times[i-1][1]!=times[i][0]:
            breaks.append({'left_ref':ids[i-1],'right_ref':ids[i],
                           'reason':'gap' if times[i-1][1]<times[i][0] else 'overlap'})
            continue
        if ('dominant_shape' in (compared[i-1]['new_key_role_candidates'] or []) and
            'tonic_triad_shape' in (compared[i]['new_key_role_candidates'] or [])):
            pairs.append(ids[i-1:i+1])
            if i>=2 and times[i-2][1]==times[i-1][0] and 'predominant_shape' in (compared[i-2]['new_key_role_candidates'] or []):
                triples.append(ids[i-2:i+1])
    markers=[{'ref':r['ref'],'source_label':r['source_cadence']} for r in rows if r.get('source_cadence')]
    return {'version':VERSION,'relation':relation,'rows':compared,'timeline_breaks':breaks,
        'dominant_tonic_shape_pairs':pairs,'predominant_dominant_tonic_shape_triples':triples,
        'source_cadence_markers':markers,
        'modulation':None,'tonicization':None,'cadence':None,'pivot':None,
        'basis':'supplied_keys_and_harmony_hypotheses', 'production_enabled':False,
        'limitations':['common triad does not establish a pivot; pivot is not required',
            'even a short PD-D-T progression can be a tonicization',
            'no fixed duration threshold proves modulation',
            'no phrase/form/metric or soprano-cadence evidence inferred',
            'sequential, passing and nested key areas remain competing explanations',
            'unknown hypotheses are not skipped; absence of a pattern is not a negative label']}


def source_key_transitions(rows):
    """Contiguous verified source-key runs; returned spans are annotation extents.

    Each input row has ref/span/key/verified. Missing or unverified rows break a
    run, never disappear. No minimum duration or minimum chord-count filtering.
    """
    def usable(r):
        if r.get('verified') is not True or r.get('key') is None or not r.get('span'):return False
        validate_key(r['key'])
        a,b=(_exact(r['span'][k]) for k in ('start','end'))
        if a<0 or b<=a:raise ValueError('positive_span_required')
        return True
    flags=[usable(r) for r in rows];runs=[]
    refs=[r['ref'] for r in rows]
    if len(set(refs))!=len(refs):raise ValueError('unique_refs_required')
    def touching(i,j):return _exact(rows[i]['span']['end'])==_exact(rows[j]['span']['start'])
    for i in range(1,len(rows)):
        if not (flags[i-1] and flags[i] and touching(i-1,i)) or rows[i-1]['key']==rows[i]['key']:continue
        end=i+1
        while end<len(rows) and flags[end] and rows[end]['key']==rows[i]['key'] and touching(end-1,end):end+=1
        cause='score_annotation_end' if end==len(rows) else 'unverified_or_missing' if not flags[end] else 'nonadjacent' if not touching(end-1,end) else 'changed_source_key'
        runs.append({'start_index':i,'stop_index':end,'old_key':list(rows[i-1]['key']),
            'new_key':list(rows[i]['key']),'annotation_refs':refs[i:end],
            'span':{'start':rows[i]['span']['start'],'end':rows[end-1]['span']['end']},
            'duration_quarters':q(_exact(rows[end-1]['span']['end'])-_exact(rows[i]['span']['start'])),
            'termination':cause,'next_key':rows[end]['key'] if cause=='changed_source_key' else None,
            'is_modulation_ground_truth':False})
    return runs


def observe_support(ir, span, h):
    """Literal full-chord support, held notes included; union is not simultaneity."""
    a,b=(_exact(span[k]) for k in ('start','end'))
    if a<0 or b<=a:raise ValueError('positive_span_required')
    c=chord(h['root'],h['quality'],h['inversion']);expected={tuple(p) for p in c['members']}
    notes={n['note_id']:n for n in ir['note_events']}
    if len(notes)!=len(ir['note_events']):raise ValueError('duplicate_note_id')
    seen=set();sounds=[];excluded=[]
    for s in ir['sounding_events']:
        sid=s['sounding_event_id'];x,y=(_exact(s['span'][k]) for k in ('start','end'))
        if sid in seen:raise ValueError('duplicate_sounding_id')
        seen.add(sid)
        if x<0 or y<x:raise ValueError('invalid_event_time')
        if x>=b or y<=a:continue
        refs=s['source_note_ids']
        if not refs or s['attack_note_id'] not in refs or any(n not in notes for n in refs):raise ValueError('broken_note_reference')
        pitch_tuple(s)
        if any(notes[n].get('grace',{}).get('is_grace',False) for n in refs):excluded.append(sid)
        else:sounds.append(s)
    inventory=span_observation({'sounding_events':sounds},span)
    matches=[]
    for cell in inventory['slices']:
        ps=[e['pitch'] for e in cell['events']];actual={tuple(p[:2]) for p in ps}
        if actual==expected:
            low=min(ps,key=lambda p:12*(p[2]+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[p[0]]+p[1])
            if low[:2]==c['expected_bass']:matches.append(cell)
    union={tuple(e['pitch'][:2]) for e in inventory['union_events']}
    return {'hypothesis':c,'span':span,'complete_vertical_matches':matches,
        'silent_spans':[cell['span'] for cell in inventory['slices'] if not cell['events']],
        'union_events':inventory['union_events'],'missing_spellings':[list(p) for p in sorted(expected-union)],
        'extra_spellings':[list(p) for p in sorted(union-expected)],'held_at_start_ids':inventory['held_at_start_ids'],
        'excluded_grace_refs':excluded,'union_is_simultaneous':False,'harmonic_function_verified':None}
