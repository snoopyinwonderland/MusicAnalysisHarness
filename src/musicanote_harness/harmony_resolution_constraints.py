"""Exact existential direct-resolution queries, without global voice products.

Answers possibility per harmonic relation, not a preferred voice assignment.
"""
from copy import deepcopy
from .harmony_joint import f
from .harmony_catalog_resolution import pitch_pair
from .harmony_reading_voice_context import spelled_height
from .harmony_progression_resolution import analyze as resolution
from .harmony_voice_paths import partition
from .applied_chords import hypothesis

VERSION='resolution-constraints-0.1.0'


def compatible_witness(groups, budget=4096):
    """Choose one edge per requirement, without branching or merging endpoints."""
    if type(budget) is not int or budget<1:raise ValueError('invalid_query_budget')
    if any(not edges for edges in groups.values()):
        return {'status':'no_compatible_witness','links':None,'checks':0}
    requirements=sorted(groups);checks=0;exceeded=False
    def search(i,edges):
        nonlocal checks,exceeded
        if i==len(requirements):return edges
        for edge in groups[requirements[i]]:
            if checks>=budget:exceeded=True;return None
            checks+=1;x,y=edge
            if any((x==a and y!=b) or (y==b and x!=a) for a,b in edges):continue
            found=search(i+1,edges if edge in edges else edges+[edge])
            if found is not None:return found
            if exceeded:return None
        return None
    witness=search(0,[])
    return {'status':'witness_exists' if witness is not None else 'query_budget_abstention' if exceeded else 'no_compatible_witness',
            'links':witness,'checks':checks,'witness_is_preferred':False}


def analyze(result,path,assignment_ref,ir,edge_budget=8192,query_budget=4096,*,geometry_cache=None):
    if type(edge_budget) is not int or edge_budget<1:raise ValueError('invalid_edge_budget')
    if type(query_budget) is not int or query_budget<1:raise ValueError('invalid_query_budget')
    strict=resolution(result,path,assignment_ref,ir=ir,geometry_cache=geometry_cache)
    notes={n['note_id']:n for n in ir['note_events']}
    if len(notes)!=len(ir['note_events']):raise ValueError('duplicate_note_id')
    events={s['sounding_event_id']:s for s in result['events']};lanes={};unlocated=[]
    partition(result['events'],[])  # Positive durations and lossless isolated tracks.
    for sid,s in events.items():
        ns=[notes.get(n) for n in s.get('source_note_ids',[])]
        keys={(n.get('part_id'),n.get('voice_id')) for n in ns if n}
        if not ns or not all(ns) or len(keys)!=1 or not all(next(iter(keys))):unlocated.append(sid)
        else:lanes[sid]=next(iter(keys))
    out={'version':VERSION,'context_span':deepcopy(result['plan']['context_span']),
         'path':deepcopy(path),'strict_explicit_result':strict,'queries':[],
         'selected_assignment':None,'probabilities_computed':False,'production_modified':False,
         'unlocated_event_refs':unlocated,'link_graph_uses_harmonic_labels':False}
    if unlocated:return {**out,'status':'unlocated_sounds_abstention'}
    # Geometry-only factor graph. Missing edges denote prohibited connections.
    graph=[]
    for x,a in sorted(events.items()):
        for y,b in sorted(events.items()):
            if lanes[x]==lanes[y] and f(a['span']['end'])==f(b['span']['start']):
                graph.append([x,y])
                if len(graph)>edge_budget:
                    return {**out,'status':'edge_budget_abstention','edge_budget':edge_budget}
    out['local_link_candidates']=graph
    readings=[result['edges'][p['edge']]['readings'][p['reading']] for p in path]
    for relation in strict['relations']:
        i,j=relation['source_path_index'],relation['target_path_index']
        query={'source_path_index':i,'target_path_index':j,'family':relation['family'],
               'function_confirmed':False,'all_assignments_supported':False}
        if relation['candidate_blockers']:
            out['queries'].append({**query,'status':'blocked_context','blockers':relation['candidate_blockers']});continue
        if j!=i+1:
            out['queries'].append({**query,'status':'nonadjacent_direct_query_not_applicable'});continue
        if not relation['source_terminal_identity'] or not relation['target_onset_identity']:
            out['queries'].append({**query,'status':'direct_identity_prerequisite_missing',
                'source_terminal_identity':relation['source_terminal_identity'],
                'target_onset_identity':relation['target_onset_identity']});continue
        h=hypothesis(relation['target_root'],relation['target_quality'],relation['family'])
        groups={'leading_tone_to_target_root':[]}
        seventh=h['chord']['members'][3] if len(h['chord']['members'])==4 else None
        if seventh:groups['seventh_down_step_to_target_member']=[]
        cut=f(readings[i]['span']['end']);target_members=readings[j]['members']
        for x,y in graph:
            a,b=events[x],events[y]
            if f(a['span']['end'])!=cut:continue
            heights=[spelled_height(s['pitch']) for s in (a,b)]
            if None in heights:continue
            p1,p2=pitch_pair(a['pitch']),pitch_pair(b['pitch'])
            steps=heights[1]-heights[0];semitones=b['pitch']['midi_pitch']-a['pitch']['midi_pitch']
            if p1==h['leading_tone'] and p2==relation['target_root'] and steps==1 and semitones==1:
                groups['leading_tone_to_target_root'].append([x,y])
            if seventh and p1==seventh and p2 in target_members and steps==-1 and semitones in (-1,-2):
                groups['seventh_down_step_to_target_member'].append([x,y])
        answer=compatible_witness(groups,query_budget)
        query.update(answer,required_link_options=groups)
        if answer['status']=='witness_exists':
            tracks=partition(result['events'],answer['links'])
            aid='constraint_witness_'+str(i)+'_'+str(j)+'_'+relation['family']
            if any(a['assignment_id']==aid for a in result['assignments']):raise ValueError('witness_id_collision')
            a={'assignment_id':aid,'links':answer['links'],'tracks':tracks}
            check=resolution({**result,'assignments':result['assignments']+[a]},path,aid)
            matched=next(r for r in check['relations'] if (r['source_path_index'],r['target_path_index'],r['family'])==(i,j,relation['family']))
            if matched['status']!='direct_resolution_supported_hypothesis':raise ValueError('witness_recheck_failed')
            query['witness_tracks']=tracks;query['witness_recheck']=matched
        out['queries'].append(query)
    out.update(status='ready',limits=[
        'Exact per-relation direct-resolution existence within same-lane touching partial matchings.',
        'No global assignment products. Independent query witnesses are NOT one shared score-wide interpretation.',
        'No-link assignment remains possible; an existential witness is not a probability or inferred voice.',
        'Delayed/intervening resolution, candidate path selection and full harmonic truth are not solved.'])
    return out
