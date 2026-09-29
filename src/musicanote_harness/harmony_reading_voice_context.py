"""Conditional voice-leading observations for saved competing chord readings.

Do not infer inner-voice connections inside a notated chord, turn lack of direct
resolution into an error, or feed source harmony/phrase annotations back in.
"""
from collections import Counter,defaultdict
from fractions import Fraction as F
from .formal_ir import q
from .harmony_joint import f,prepare
from .harmony_surface import TEMPLATES
from .harmony_shared_tone_review import shapes
from .harmony_multiscale_shadow import continuous_sound
from .harmony_candidate_explanation import spelling_evidence

VERSION='reading-voice-context-0.1.0'
LETTERS='CDEFGAB'
NATURAL=dict(zip(LETTERS,(0,2,4,5,7,9,11)))


def spelled_height(p):
    step=p.get('step');octave=p.get('octave');alter=p.get('alter');midi=p.get('midi_pitch')
    if step not in NATURAL or type(octave) is not int or not isinstance(alter,dict) or midi is None:return None
    accidental=f(alter)
    if accidental.denominator!=1 or 12*(octave+1)+NATURAL[step]+accidental!=midi:return None
    return 7*octave+LETTERS.index(step)


def voice_links(ir,context_span):
    """Only unique contiguous nonoverlapping successors in an explicit IR voice."""
    rows,_=prepare(ir);notes={n['note_id']:n for n in ir.get('note_events',[])}
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']};voices=defaultdict(list);reason={}
    for r in rows:
        s=sounds[r['id']];refs=s.get('source_note_ids') or [s.get('attack_note_id')]
        identities={(notes[n].get('part_id'),notes[n].get('voice_id')) for n in refs if n in notes}
        if len(identities)!=1 or len([n for n in refs if n in notes])!=len(refs):
            reason[r['id']]='missing_or_cross_voice_source_identity';continue
        identity=next(iter(identities))
        if not identity[0] or not identity[1]:reason[r['id']]='missing_explicit_part_or_voice';continue
        voices[identity].append(r)
    start,end=f(context_span['start']),f(context_span['end'])
    if start<0 or end<start:raise ValueError('invalid_context_span')
    links=[];abstentions=Counter();observations=[]
    def in_context(r):return r['start']<end and r['end']>start
    for r in rows:
        if in_context(r) and r['id'] in reason:
            abstentions[reason[r['id']]]+=1;observations.append({'event_ref':r['id'],'status':reason[r['id']]})
    for (part,voice),sequence in voices.items():
        sequence=sorted(sequence,key=lambda r:(r['start'],r['id']))
        for r in sequence:
            if not in_context(r):continue
            status=None
            if any(n['id']!=r['id'] and n['start']<r['end'] and n['end']>r['start'] for n in sequence):
                status='polyphonic_source_voice'
            later=[n for n in sequence if n['start']>r['start']]
            first=min((n['start'] for n in later),default=None)
            targets=[n for n in later if n['start']==first]
            if not status and not targets:status='no_successor'
            if not status and len(targets)!=1:status='ambiguous_successor_chord'
            if not status:
                n=targets[0]
                if n['start']>=end:status='successor_outside_context'
                elif n['start']!=r['end']:status='gap_or_overlap_not_direct'
                elif any(other['id']!=n['id'] and other['start']<n['end'] and other['end']>n['start'] for other in sequence):status='polyphonic_target_voice'
            if status:
                abstentions[status]+=1;observations.append({'event_ref':r['id'],'status':status});continue
            p1,p2=sounds[r['id']]['pitch'],sounds[n['id']]['pitch']
            h1,h2=spelled_height(p1),spelled_height(p2)
            links.append({'source_refs':[r['id'],n['id']],'part_id':part,'voice_id':voice,
                'source_pitch':p1,'target_pitch':p2,'source_span':{'start':q(r['start']),'end':q(r['end'])},
                'target_span':{'start':q(n['start']),'end':q(n['end'])},
                'semitones':n['pitch']-r['pitch'],'diatonic_steps':h2-h1 if h1 is not None and h2 is not None else None,
                'status':'unique_contiguous_explicit_ir_voice','xml_voice_identity_verified':False,
                'contrapuntal_voice_identity_confirmed':False})
    return {'links':links,'abstentions':dict(abstentions),'event_statuses':observations,
            'context_span':context_span,'polyphonic_voice_matching':'deferred_no_nearest_pitch_guess'}


def relation(link,source,target):
    """Conditional chord-role compatibility, not applied function or cadence."""
    delta,diatonic=link['semitones'],link['diatonic_steps']
    pc=link['source_pitch']['midi_pitch']%12;dest=link['target_pitch']['midi_pitch']%12
    root=source.get('root');quality=source['label'].partition(':')[2];shape=dict(TEMPLATES).get(quality)
    if root is None or not shape or pc not in source['pcs'] or dest not in target['pcs']:return []
    tags=[]
    if delta==0 and diatonic==0:tags.append('same_spelled_pitch_reattack')
    if delta in (-1,-2) and diatonic==-1:
        if len(shape)==4 and pc==(root+shape[3])%12:tags.append('conditional_seventh_down_step_to_member')
        if quality in ('diminished','diminished7','half-diminished7') and pc==(root+6)%12:tags.append('conditional_diminished_fifth_down_step_to_member')
    tq=target['label'].partition(':')[2];tr=target.get('root')
    if tq in ('major','minor') and tr is not None and dest==tr and delta==1 and diatonic==1:
        dominant=quality in ('major','dominant7') and (root-tr)%12==7 and pc==(root+4)%12
        leading=quality in ('diminished','diminished7','half-diminished7') and (root-tr)%12==11 and pc==root
        if dominant or leading:tags.append('conditional_dominant_family_leading_tone_up')
    return tags


def compare(ir,candidate):
    """Attach separate evidence; preserve all saved hypotheses/costs/selection."""
    a,t,b=f(candidate['span']['start']),f(candidate['boundary']),f(candidate['span']['end'])
    if not 0<=a<t<b:raise ValueError('invalid_candidate_span')
    unit=f(candidate['beat_unit_quarter'])
    if unit<=0:raise ValueError('invalid_beat_unit')
    rows,_=prepare(ir);score_end=max((r['end'] for r in rows),default=b)
    context={'start':q(max(F(0),a-2*unit)),'end':q(min(score_end,b+2*unit))}
    observed=voice_links(ir,context);links=observed['links']
    internal=[p for p in links if f(p['source_span']['start'])<t<=f(p['source_span']['end'])
              and f(p['target_span']['start'])>=t and f(p['target_span']['start'])<b]
    following=[p for p in links if f(p['source_span']['start'])<b<=f(p['source_span']['end']) and f(p['target_span']['start'])>=b]
    preceding=[p for p in links if f(p['source_span']['end'])==a and f(p['target_span']['start'])==a]
    # External harmonies are blind complete-PC observations, not borrowed source
    # labels or the answer of one competing path. Keep every fitting template.
    grid=sorted({(f(m['global_start_quarter']),F(4,m['time_signature']['beat_type'])) for m in ir.get('measures',[])})
    def unit_at(x):return next((u for onset,u in reversed(grid) if onset<=x),unit)
    external=[]
    for side in ('preceding','following'):
        for width in (1,2):
            x,y=(a-width*unit,a) if side=='preceding' else (b,b+width*unit)
            if x<f(context['start']) or y>f(context['end']):continue
            units={unit_at(x)}|{u for onset,u in grid if x<=onset<y}
            if units!={unit}:continue
            active=[r for r in rows if r['start']<y and r['end']>x]
            if not continuous_sound(active,x,y):continue
            pcs={r['pitch']%12 for r in active}
            for c in shapes(pcs,3)+shapes(pcs,4):
                complete=max(min(max(x,r['start']) for r in active if r['pitch']%12==pc) for pc in pcs)
                span={'start':q(x),'end':q(y)}
                external.append({'side':side,'span':span,'candidate':c,'event_refs':sorted(r['id'] for r in active),
                    'all_members_observed_by':q(complete),'spelling':spelling_evidence(ir,span,c),
                    'status':'complete_pooled_shape_not_selected_harmony'})
    readings=[]
    for kind in ('merged_seventh','split_triads'):
        for index,path in enumerate(candidate[kind]):
            source=path['segments'][0]['candidate'];target=path['segments'][-1]['candidate']
            evaluations=[]
            for p in internal:
                evaluations.append({'source_refs':p['source_refs'],'relations':relation(p,source,target),
                    'semitones':p['semitones'],'diatonic_steps':p['diatonic_steps'],
                    'source_member':p['source_pitch']['midi_pitch']%12 in source['pcs'],
                    'target_member':p['target_pitch']['midi_pitch']%12 in target['pcs'],
                    'function_confirmed':False})
            outside=[]
            for ext in external:
                src,dst=(ext['candidate'],source) if ext['side']=='preceding' else (target,ext['candidate'])
                pairs=preceding if ext['side']=='preceding' else following
                rels=[{'source_refs':p['source_refs'],'relations':relation(p,src,dst),
                       'semitones':p['semitones'],'diatonic_steps':p['diatonic_steps']} for p in pairs
                      if (ext['side']=='preceding' and f(p['source_span']['end'])>f(ext['span']['start'])) or
                         (ext['side']=='following' and f(p['target_span']['start'])<f(ext['span']['end']))]
                outside.append({'side':ext['side'],'external_span':ext['span'],'external_candidate':ext['candidate'],
                    'external_members_observed_by':ext['all_members_observed_by'],'relations':rels,
                    'function_confirmed':False})
            readings.append({'reading_type':kind,'reading_index':index,'conditional_labels':[s['candidate']['label'] for s in path['segments']],
                'internal_relations':evaluations,'direct_relation_observed':any(e['relations'] for e in evaluations),
                'external_comparisons':outside,
                'spelling_evidence':[s['spelling'] for s in path['segments']],
                'source_cost_unchanged':path['local_cost'],'absence_is_counterevidence':False,'selected':None})
    return {'version':VERSION,'candidate_ref':candidate['evidence_id'],'context_span':context,
        'voice_observations':observed,'preceding_links':preceding,'internal_links':internal,'following_links':following,
        'readings':readings,'external_shape_candidates':external,'reranking_performed':False,'source_annotation_used':False,'function_confirmed':False,
        'limits':['Explicit IR voice is not verified contrapuntal identity; polyphonic voices abstain',
                  'Cross-staff is permitted within the same explicit part/voice; cross-voice tie identity abstains',
                  'Only direct contiguous spelled motion is classified; distributed/ornamental resolutions may be missed',
                  'No direct relation is not evidence that a reading is wrong',
                  'External windows are 1 or 2 denominator beats; all complete pooled shapes are alternatives',
                  'External shape completion time is explicit; later tones do not prove the chord was complete at the boundary',
                  'Pitch-class chord hypotheses and their spelling may be wrong; no inferred key, modulation, cadence or NCT label']}
