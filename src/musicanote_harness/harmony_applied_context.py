"""Runtime bridge to textbook applied-chord hypotheses, without source labels.

Only adjacent selected harmonies are examined. A terminal sounding support span
prevents late chromatic tones from being projected backwards over a pooled span.
Pitch-pair compatibility is not proof of contrapuntal voice identity or function.
"""
from copy import deepcopy
from .applied_chords import hypothesis, contextualize
from .harmony_candidate_explanation import spelling_evidence
from .harmony_joint import prepare, f
from .formal_ir import q

VERSION = 'applied-context-bridge-0.1.0'
FAMILY = {'major':'V', 'dominant7':'V7', 'diminished':'vii',
          'diminished7':'vii7', 'half-diminished7':'vii_half7'}


def token(name):
    return [name[0], name.count('#')-name.count('b')]


def name(pair):
    return pair[0]+('#'*pair[1] if pair[1]>0 else 'b'*(-pair[1]))


def supported(ir, segment):
    evidence=spelling_evidence(ir,segment['span'],segment['selected'])
    choices=[c for c in evidence['candidates'] if not c['conflicting_event_refs']]
    return choices[0] if len(choices)==1 and not evidence.get('unsupported_pitch_event_refs') else None


def attach_applied_context(ir, result):
    out=deepcopy(result)
    rows,_=prepare(ir)
    pitches={s['sounding_event_id']:s['pitch'] for s in ir['sounding_events']}
    def spelled(r):
        p=pitches[r['id']]
        return [p.get('step'),int(f(p['alter']))] if p.get('alter') else None
    for s in out['segments']:
        s['applied_context_hypotheses']=[]
    for i,(s,target) in enumerate(zip(out['segments'],out['segments'][1:])):
        family=FAMILY.get(s['selected']['label'].partition(':')[2])
        tq={'major':'M','minor':'m'}.get(target['selected']['label'].partition(':')[2])
        boundary=f(s['span']['end'])
        if not family or not tq or boundary!=f(target['span']['start']):continue
        source_spelling=supported(ir,s);target_spelling=supported(ir,target)
        if not source_spelling or not target_spelling:continue
        h=hypothesis(token(target_spelling['root_spelling']),tq,family)
        if [name(p) for p in h['chord']['members']]!=source_spelling['expected_members']:continue
        # Target root and third must actually sound at the immediate boundary.
        following=[r for r in rows if r['start']<=boundary<r['end']]
        if not all(any(spelled(r)==p for r in following) for p in h['target']['members'][:2]):continue
        cells=s.get('bass_realization',{}).get('cells',[])
        critical=[h['leading_tone']]
        if len(h['chord']['members'])==4:critical.append(h['chord']['members'][3])
        else:critical.append(h['chord']['root'] if family=='V' else h['chord']['members'][1])
        tail=[]
        for cell in reversed(cells):
            active=[r for r in rows if r['id'] in cell['sounding_event_refs']]
            if not all(any(spelled(r)==p for r in active) for p in critical):break
            tail.insert(0,cell)
        if not tail:continue
        terminal=[r for r in rows if r['id'] in tail[-1]['sounding_event_refs']]
        pairs=[]
        for r in terminal:
            for n in following:
                if r['end']!=boundary or n['start']!=boundary or not r['voice'] or r['voice']!=n['voice']:continue
                delta=n['pitch']-r['pitch'];kind=None
                if spelled(r)==h['leading_tone'] and spelled(n)==h['target']['root'] and delta==1:
                    kind='leading_tone_up_semitone'
                elif len(h['chord']['members'])==4 and spelled(r)==h['chord']['members'][3] and spelled(n) in h['target']['members'] and delta in (-1,-2):
                    # Require a spelled descending second, not enharmonic unison.
                    if ('CDEFGAB'.index(spelled(r)[0])-'CDEFGAB'.index(spelled(n)[0]))%7==1:
                        kind='seventh_down_step'
                if kind:pairs.append({'relation':kind,'source_refs':[r['id'],n['id']],
                                      'status':'same_notated_voice_pitch_pair_compatible_not_voice_identity'})
        relations={p['relation'] for p in pairs}
        ready='leading_tone_up_semitone' in relations and (len(h['chord']['members'])==3 or 'seventh_down_step' in relations)
        hid=f'applied_{i}_{i+1}'
        record={'hypothesis_id':hid,'family':family,'textbook_hypothesis':h,
            'context':contextualize(h,following=h['target']),
            'target_segment_index':i+1,'target_span':deepcopy(target['span']),
            'support_span':{'start':deepcopy(tail[0]['span']['start']),'end':q(boundary)},
            'parent_harmony_span':deepcopy(s['span']),
            'status':'resolution_supported_candidate' if ready else 'shape_relation_only',
            'resolution_pairs':pairs,'function_confirmed':False,'uses_source_annotation':False,
            'evidence_refs':sorted({r for cell in tail for r in cell['sounding_event_refs']}|{r['id'] for r in following}),
            'limits':['Selected source and target chords may be wrong',
                      'No inferred home key, tonicization, modulation or cadence',
                      'No reranking or harmonic boundary update; distributed-only critical tones may be missed']}
        s['applied_context_hypotheses'].append(record)
        for cell in tail:cell.setdefault('applied_context_refs',[]).append(hid)
    out['applied_context_version']=VERSION
    return out


def applied_projection(record, reference_key, inversion_index):
    """Conditional display key is never fed back to the blind hypothesis builder."""
    if record['status']!='resolution_supported_candidate' or not reference_key or inversion_index is None:return None
    from music21 import key, pitch, chord, roman
    from music21.exceptions21 import Music21Exception
    from .harmony_visual_review import key_token
    h=record['textbook_hypothesis']
    try:
        home=key.Key(key_token(reference_key))
        target=chord.Chord([pitch.Pitch(name(p).replace('b','-')+'4') for p in h['target']['members']])
        target_rn=roman.romanNumeralFromChord(target,home,preferSecondaryDominants=False)
        # Home tonic resolution is primary; a diatonic I -> IV is not evidence of tonicization.
        if token(home.tonic.name.replace('-','b'))==h['target']['root']:return None
        home_names={p.name for p in home.pitches}
        if not any(name(p).replace('b','-') not in home_names for p in h['chord']['members']):return None
        seventh=len(h['chord']['members'])==4
        figures=('7','65','43','2') if seventh else ('','6','64')
        if not 0<=inversion_index<len(figures):return None
        prefix={'V':'V','V7':'V','vii':'viio','vii7':'viio','vii_half7':'viiø'}[record['family']]
        return {'text':prefix+figures[inversion_index]+'/'+target_rn.romanNumeral,
            'status':'conditional_display','policy':'resolution_candidate_under_supplied_display_key',
            'hypothesis_id':record['hypothesis_id'],'used_for_inference':False,
            'reference_key':reference_key,'function_confirmed':False}
    except (ValueError,Music21Exception):return None
