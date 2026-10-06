"""Factorized cross-boundary NCT geometry under one global voice assignment.

No chord/voice winner, accent judgement, pitch substitution, or note removal.
Explanations apply only to explicit nonmember time intervals, never a whole
held event merely because one side of a boundary is nonharmonic.
"""
from copy import deepcopy
from fractions import Fraction
from .formal_ir import q
from .harmony_joint import f
from .harmony_reading_voice_context import spelled_height
from .harmony_voice_paths import partition
from .counterpoint_evidence import melodic_geometry
from .harmony_segment_contrast import compare as segment_compare, STATES
from .harmony_path_contrast import token

VERSION='cross-boundary-figures-0.1.0'
MEMBER='member'
NONMEMBER='nonmember_not_confirmed_nct'


def observe(result,boundary_index):
    b=result['boundaries'][boundary_index];answer={'version':VERSION,'patterns':[],
        'selected':None,'nct_confirmed':False,'ranking_performed':False,'status':b['status']}
    if result['status']!='ready' or b['status']!='ready':return answer
    events={s['sounding_event_id']:s for s in result['events']};a,z=f(result['span']['start']),f(result['span']['end']);cut=f(b['boundary'])
    patterns={};lane_ids={sid for track in result['assignments'][0]['tracks'] for sid in track}
    def full(sid):
        s=events[sid];return a<=f(s['span']['start'])<f(s['span']['end'])<=z and spelled_height(s['pitch']) is not None
    def match(side,req):
        return [i for i,r in enumerate(b[side]['readings']) if not r['condition']['abstention_reasons']
                and all(r['event_states'].get(sid)==state for sid,state in req.items())]
    def add(kind,refs,affected,interval,left_req,right_req,aid):
        li,ri=match('left',left_req),match('right',right_req)
        if not li or not ri:return
        key='boundary_nct_'+token([b['boundary'],kind,refs,affected,interval,left_req,right_req])
        if key not in patterns:patterns[key]={'pattern_id':key,'kind':kind,'event_refs':list(refs),
            'affected_event_ref':affected,'nonmember_span':interval,'left_requirements':left_req,'right_requirements':right_req,
            'left_reading_indices':li,'right_reading_indices':ri,'supporting_assignment_refs':[],
            'confirmed':False,'remove_note':False,'accent_assessed':False}
        patterns[key]['supporting_assignment_refs'].append(aid)
    for assignment in result['assignments']:
        tracks=partition([events[sid] for sid in lane_ids],assignment['links'])
        if tracks!=assignment['tracks']:raise ValueError('invalid_shared_voice_partition')
        aid=assignment['assignment_id']
        for track in tracks:
            for triple in zip(track,track[1:],track[2:]):
                if not all(full(s) for s in triple):continue
                if not f(events[triple[0]]['span']['start'])<cut<f(events[triple[-1]]['span']['end']):continue
                ps=[events[s]['pitch'] for s in triple]
                g=melodic_geometry([(p['step'],int(f(p['alter'])),p['octave']) for p in ps])
                if g['pattern'] is None:continue
                reqs={'left':{},'right':{}}
                for sid,state in zip(triple,(MEMBER,NONMEMBER,MEMBER)):
                    s=events[sid]
                    if f(s['span']['start'])<cut:reqs['left'][sid]=state
                    if f(s['span']['end'])>cut:reqs['right'][sid]=state
                add('cross_boundary_'+g['pattern'].replace('_geometry','_candidate'),triple,triple[1],
                    deepcopy(events[triple[1]]['span']),reqs['left'],reqs['right'],aid)
            for x,y in zip(track,track[1:]):
                if not full(x) or not full(y):continue
                xs,ys=events[x],events[y];xp,yp=xs['pitch'],ys['pitch']
                if f(xs['span']['end'])==cut==f(ys['span']['start']) and xp['midi_pitch']==yp['midi_pitch'] and spelled_height(xp)==spelled_height(yp):
                    add('anticipation_reattack_candidate',[x,y],x,deepcopy(xs['span']),{x:NONMEMBER},{y:MEMBER},aid)
                if f(xs['span']['start'])<cut<f(xs['span']['end']) and spelled_height(yp)-spelled_height(xp)==-1 and yp['midi_pitch']-xp['midi_pitch'] in (-1,-2):
                    add('prepared_suspension_candidate',[x,y],x,{'start':q(cut),'end':xs['span']['end']},
                        {x:MEMBER},{x:NONMEMBER,y:MEMBER},aid)
            for sid in track:
                if not full(sid):continue
                s=events[sid]
                if f(s['span']['start'])<cut<f(s['span']['end']):
                    add('anticipation_held_candidate',[sid],sid,{'start':s['span']['start'],'end':q(cut)},
                        {sid:NONMEMBER},{sid:MEMBER},aid)
    answer['patterns']=list(patterns.values())
    answer['limits']=['Passing/neighbor endpoints must be members in every segment they occupy; middle must be nonmember throughout.',
        'Suspension requires actually held prepared sound and linked downward step; reattack is not a tie.',
        'Anticipation can be same-spelled same-register reattack or actual sustain, not enharmonic proximity.',
        'Geometry remains conditional; accent, bass dissonance, duration/style, key/function and chord change are unconfirmed.',
        'Assignments and candidate indices are predicates, not independent votes.']
    return answer


def compare(result,boundary_index,hold_index,left_index,right_index,assignment_ref):
    old=segment_compare(result,boundary_index,hold_index,left_index,right_index,assignment_ref)
    evidence=result['boundaries'][boundary_index].get('boundary_figures')
    if evidence is None:evidence=observe(result,boundary_index)
    active=[p for p in evidence['patterns'] if left_index in p['left_reading_indices'] and right_index in p['right_reading_indices'] and assignment_ref in p['supporting_assignment_refs']]
    enhanced=deepcopy(old['split']);added=[]
    totals={k:Fraction() for k in STATES}
    for item in enhanced['items']:
        lo,hi=f(item['span']['start']),f(item['span']['end'])
        supports=[p['pattern_id'] for p in active if p['affected_event_ref']==item['event_ref'] and f(p['nonmember_span']['start'])<=lo and hi<=f(p['nonmember_span']['end'])]
        if supports and item['bucket'] in ('conditional_nonmember','unexplained_nonmember'):
            if item['bucket']=='unexplained_nonmember':added.append({'event_ref':item['event_ref'],'span':item['span'],'pattern_refs':supports})
            item['bucket']='conditional_nonmember';item['cross_boundary_pattern_refs']=supports
        totals[item['bucket']]+=hi-lo
    enhanced['note_time']={k:q(v) for k,v in totals.items()}
    if q(sum(totals.values(),Fraction()))!=old['split']['total_note_time']:raise ValueError('cross_boundary_note_time_loss')
    for key in ('member','spelling_unresolved'):
        if enhanced['note_time'][key]!=old['split']['note_time'][key]:raise ValueError('membership_changed')
    return {'version':VERSION,'baseline_comparison':old,'split_with_boundary_context':enhanced,
            'active_patterns':active,'newly_explained_cells':added,'preferred':None,'nct_confirmed':False,
            'limits':['Only unexplained nonmember time may gain a conditional explanation; no membership or total-time change.',
                      'This is not a fully symmetric NCT model or a harmonic-segmentation score.']}


def augment(baseline):
    result=deepcopy(baseline)
    for i,b in enumerate(result['boundaries']):b['boundary_figures']=observe(result,i)
    if 'preview_selection' in result:
        p=result['preview_selection'];result['boundary_context_preview']=compare(result,p['boundary'],p['hold'],p['left'],p['right'],p['assignment'])
    result['boundary_figures_version']=VERSION
    return result
