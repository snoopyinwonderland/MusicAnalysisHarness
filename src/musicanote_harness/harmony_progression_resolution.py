"""Spelled target relations on full paths, with assignment-dependent resolution."""
from copy import deepcopy
from .applied_chords import hypothesis, FAMILIES
from .seventh_context import chord
from .harmony_joint import f
from .harmony_catalog_resolution import pitch_pair, keys_checked, project
from .harmony_reading_voice_context import spelled_height, voice_links
from .harmony_progression_context import evaluate

VERSION = 'progression-resolution-0.2.0'


def analyze(result,path,assignment_ref,reference_keys=(), *, ir=None,geometry_cache=None):
    evaluate(result,path,assignment_ref)  # Same partition and assignment contract.
    keys=keys_checked(reference_keys)
    events={s['sounding_event_id']:s for s in result['events']}
    assignment=next(a for a in result['assignments'] if a['assignment_id']==assignment_ref)
    link_scope='sampled_assignment'
    diagnostics=None
    supplied_links=assignment['links']
    if ir is not None:
        # Do not combine heuristic assignment edges and explicit-voice edges.
        # Verify the score before using any additional part/voice information.
        span=result['plan']['context_span']
        source_events={s['sounding_event_id']:s for s in ir['sounding_events']}
        if len(source_events)!=len(ir['sounding_events']):raise ValueError('duplicate_ir_sound')
        expected={sid for sid,s in source_events.items() if f(s['span']['start'])<f(span['end']) and f(s['span']['end'])>f(span['start'])}
        if expected!=set(events):raise ValueError('ir_context_event_coverage_mismatch')
        for sid,s in events.items():
            for key in ('pitch','span','source_note_ids'):
                if s.get(key)!=source_events[sid].get(key):raise ValueError('ir_event_identity_mismatch')
        diagnostics=voice_links(ir,span,geometry_cache=geometry_cache)
        supplied_links=[l['source_refs'] for l in diagnostics['links']
                        if all(sid in events for sid in l['source_refs'])]
        link_scope='unique_contiguous_explicit_ir_voices'
    links={}
    for x,y in supplied_links:
        if x not in events or y not in events or x in links:
            raise ValueError('invalid_or_branching_assignment_link')
        if f(events[x]['span']['end'])!=f(events[y]['span']['start']) or f(events[x]['span']['start'])>=f(events[y]['span']['start']):
            raise ValueError('nonforward_or_nontouching_assignment_link')
        links[x]=y
    readings=[result['edges'][p['edge']]['readings'][p['reading']] for p in path]
    def overlap(s,span):
        return f(s['span']['start'])<f(span['end']) and f(s['span']['end'])>f(span['start'])
    def pair(s):
        return pitch_pair(s['pitch']) if spelled_height(s['pitch']) is not None else None
    def present_at(reading, pitches, at_end=False):
        t=f(reading['span']['end' if at_end else 'start'])
        return all(any(pair(s)==p and (f(s['span']['start'])<t<=f(s['span']['end']) if at_end else
                       f(s['span']['start'])<=t<f(s['span']['end'])) for s in events.values()) for p in pitches)
    relations=[]
    for i,source in enumerate(readings):
        if source.get('root_spelling') is None:continue
        for j in range(i+1,len(readings)):
            target=readings[j];root=target.get('root_spelling')
            if root is None:continue
            tm={tuple(m) for m in target['members']}
            for quality in ('M','m'):
                target_core=chord(root,quality)['members']
                if not {tuple(m) for m in target_core}<=tm:continue
                for family in FAMILIES:
                    h=hypothesis(root,quality,family)
                    if source['root_spelling']!=h['chord']['root'] or {tuple(m) for m in source['members']}!={tuple(m) for m in h['chord']['members']}:continue
                    critical={'leading_tone':h['leading_tone']}
                    if len(h['chord']['members'])==4:critical['seventh']=h['chord']['members'][3]
                    required={'leading_tone_to_target_root'}
                    if 'seventh' in critical:required.add('seventh_down_step_to_target_member')
                    evidence=[]
                    for sid,s in events.items():
                        if not overlap(s,source['span']):continue
                        role=next((k for k,p in critical.items() if pair(s)==p),None)
                        if role is None:continue
                        chain=[sid]; current=sid
                        while current in links:
                            dest=links[current]
                            if pair(events[dest])==pair(s) and events[dest]['pitch'].get('midi_pitch')==s['pitch'].get('midi_pitch'):
                                chain.append(dest); current=dest
                            else:break
                        dest=links.get(current)
                        if dest is None:continue
                        d=events[dest]
                        if pair(d) is None:continue
                        at=f(d['span']['start'])
                        if not f(target['span']['start'])<=at<f(target['span']['end']):continue
                        delta=d['pitch']['midi_pitch']-s['pitch']['midi_pitch']
                        steps=spelled_height(d['pitch'])-spelled_height(s['pitch'])
                        tag=None
                        if role=='leading_tone' and pair(d)==root and delta==1 and steps==1:tag='leading_tone_to_target_root'
                        if role=='seventh' and tuple(pair(d)) in tm and delta in (-1,-2) and steps==-1:tag='seventh_down_step_to_target_member'
                        if tag:
                            evidence.append({'source_ref':sid,'same_pitch_chain':chain,'target_ref':dest,
                                'relation':tag,'arrival':deepcopy(d['span']['start']),
                                'at_boundary':j==i+1 and at==f(source['span']['end']),
                                'assignment_ref':assignment_ref if ir is None else None,
                                'link_scope':link_scope})
                    terminal_pitches=list(critical.values())
                    if len(terminal_pitches)==1:
                        terminal_pitches.append(h['chord']['members'][0 if family=='V' else 2])
                    terminal=present_at(source,terminal_pitches,True)
                    arrival=present_at(target,target_core[:2])
                    blockers=sorted({b for r in readings[i:j+1] for b in r['abstention_reasons']})
                    tags={e['relation'] for e in evidence if e['at_boundary']}
                    supported=not blockers and terminal and arrival and required<=tags
                    relations.append({'source_path_index':i,'target_path_index':j,
                        'source_candidate_ref':source['candidate_ref'],'target_candidate_ref':target['candidate_ref'],
                        'source_span':deepcopy(source['span']),'target_span':deepcopy(target['span']),
                        'family':family,'target_root':deepcopy(root),'target_quality':quality,
                        'intervening_path_indices':list(range(i+1,j)),
                        'source_terminal_identity':terminal,'target_onset_identity':arrival,
                        'voice_evidence':evidence,'missing_direct_relations':sorted(required-tags),
                        'candidate_blockers':blockers,'key_projections':project(h,keys),
                        'status':'blocked_context' if blockers else 'direct_resolution_supported_hypothesis' if supported else 'shape_relation_only',
                        'function_confirmed':False,'cadence_confirmed':False,'modulation_confirmed':False})
    return {'version':VERSION,'path':deepcopy(path),'assignment_ref':assignment_ref,
            'resolution_link_scope':link_scope,'voice_diagnostics':diagnostics,
            'context_span':deepcopy(result['plan']['context_span']),'reference_key_hypotheses':keys,
            'relations':relations,'selected':None,'source_labels_used':False,'production_modified':False,
            'limits':['Only exact spelled ordinary V/vii families; extended/augmented-sixth forms deferred.',
                      'Delayed and intervening-target links are retained but not promoted by direct-resolution gate.',
                      'Sampled assignment or separate explicit IR voice evidence; never a union of both.',
                      'Explicit IR voices are not verified contrapuntal voices; polyphonic matching stays deferred.',
                      'Missing relation is not disproof; no key inference or ranking.']}
