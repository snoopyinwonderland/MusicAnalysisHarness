"""Bounded complete cross-lane products of partial voice matchings, not votes."""
from copy import deepcopy
from itertools import product
from math import prod
from .harmony_voice_paths import observe, partition
from .harmony_path_contrast import token
from .harmony_progression_resolution import analyze as resolution

VERSION = 'progression-polyphony-0.1.0'
MAX_COMBINATIONS = 256


def analyze(result, path, assignment_ref, ir, max_combinations=MAX_COMBINATIONS):
    if type(max_combinations) is not int or max_combinations < 1:
        raise ValueError('invalid_combination_budget')
    # Includes exact context-event and score-revision checks; not a fallback winner.
    strict=resolution(result,path,assignment_ref,ir=ir)
    notes={n['note_id']:n for n in ir['note_events']}
    if len(notes)!=len(ir['note_events']):raise ValueError('duplicate_note_id')
    lanes=set();unlocated=[]
    for s in result['events']:
        ns=[notes.get(n) for n in s.get('source_note_ids',[])]
        keys={(n.get('part_id'),n.get('voice_id')) for n in ns if n}
        if not ns or not all(ns) or len(keys)!=1 or not all(next(iter(keys))):
            unlocated.append(s['sounding_event_id'])
        else:lanes.add(next(iter(keys)))
    out={'version':VERSION,'context_span':deepcopy(result['plan']['context_span']),
         'path':deepcopy(path),'strict_explicit_result':strict,'lanes':[],
         'unlocated_event_refs':unlocated,'max_combinations':max_combinations,
         'assignments':[],'selected_assignment':None,'counts_are_confidence':False,
         'production_modified':False,'harmonic_labels_used_for_links':False}
    if unlocated:return {**out,'status':'unlocated_sounds_no_partial_selection','enumeration_complete':False}
    for lane in sorted(lanes):
        out['lanes'].append(observe(ir,out['context_span'],lane))
    total=prod(l['possible_assignments'] for l in out['lanes'])
    out['possible_combinations']=total
    if any(l['abstention_reasons'] for l in out['lanes']):
        return {**out,'status':'lane_enumeration_abstained','enumeration_complete':False}
    if total>max_combinations:
        return {**out,'status':'global_budget_abstention_no_pruning','enumeration_complete':False}
    for combination in product(*(l['assignments'] for l in out['lanes'])):
        links=[pair for a in combination for pair in a['links']]
        tracks=partition(result['events'],links)
        aid='poly_'+token([out['context_span'],links])
        hypothesis={'assignment_id':aid,'links':links,'tracks':tracks}
        working={**result,'assignments':result['assignments']+[hypothesis]}
        evidence=resolution(working,path,aid)
        evidence['resolution_link_scope']='bounded_same_ir_lane_partial_matchings'
        for relation in evidence['relations']:
            for link in relation['voice_evidence']:
                link['link_scope']='bounded_same_ir_lane_partial_matchings'
        out['assignments'].append({**hypothesis,
            'lane_assignment_refs':[a['assignment_id'] for a in combination],
            'resolution':evidence})
    out.update(status='ready',enumeration_complete=True)
    # Counts expose sensitivity to the voice hypothesis; never choose the maximum.
    supported=[a['assignment_id'] for a in out['assignments'] if any(
        r['status']=='direct_resolution_supported_hypothesis' for r in a['resolution']['relations'])]
    out['assignments_with_any_direct_support']=supported
    out['limits']=['No nearest-pitch preference or harmonic-label-directed matching.',
        'No cross-part/voice links, rest bridging, overlapping transitions, splitting or merging.',
        'All partial matchings include unmatched notes and the no-link alternative.',
        'Support under some assignments is conditional possibility, not confirmed voice identity or probability.']
    return out
