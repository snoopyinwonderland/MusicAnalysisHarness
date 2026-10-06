"""Label-blind consecutive attack-group sampling beyond delayed endpoints."""
from collections import defaultdict
from copy import deepcopy
from .formal_ir import q
from .harmony_joint import f
from .harmony_path_contrast import token
from .harmony_path_context import plan as context_plan
from .harmony_voice_paths import observe
from .harmony_candidate_catalog import propose
from .harmony_path_ornaments import explain

VERSION='continuous-figure-survey-0.1.0'
MAX_CONDITION_ASSIGNMENTS=20000


def plan(ir,span):
    a,b=f(span['start']),f(span['end'])
    if a<0 or b<=a:raise ValueError('invalid_span')
    notes={n['note_id']:n for n in ir['note_events']};lanes=defaultdict(lambda:defaultdict(list));skipped=[]
    for s in ir['sounding_events']:
        t=f(s['span']['start'])
        if not a<=t<b:continue
        ns=[notes.get(n) for n in s['source_note_ids']]
        keys={(n.get('part_id'),n.get('voice_id')) for n in ns if n}
        if not ns or not all(ns) or len(keys)!=1 or not all(next(iter(keys))):
            skipped.append({'event_ref':s['sounding_event_id'],'reason':'missing_lane_identity'});continue
        lanes[next(iter(keys))][t].append(s)
    samples=[]
    for lane,groups in sorted(lanes.items()):
        times=sorted(groups)
        for starts in zip(times,times[1:],times[2:]):
            events=[s for t in starts for s in groups[t]]
            end=max(f(s['span']['end']) for s in events)
            refs=sorted(s['sounding_event_id'] for s in events)
            sample={'sample_id':'cont_'+token([lane,[q(t) for t in starts],refs]),'lane':list(lane),
                'attack_group_onsets':[q(t) for t in starts], 'seed_event_refs':refs,
                'span':{'start':q(starts[0]),'end':q(end)},'abstention_reasons':[]}
            if end>b:sample['abstention_reasons'].append('complete_sound_outside_frozen_scope')
            if any(f(s['span']['end'])<=f(s['span']['start']) for s in events):sample['abstention_reasons'].append('nonpositive_duration')
            samples.append(sample)
    samples.sort(key=lambda s:(f(s['span']['start']),s['lane'],s['sample_id']))
    return {'version':VERSION,'scope':deepcopy(span),'samples':samples,'skipped_sounds':skipped,
        'selection':'every three consecutive attack-onset groups per explicit part/voice; no shape or chord filter',
        'harmony_labels_used':False,'independent_samples':False,
        'limits':['Overlapping samples are correlated, not independent success counts.',
                  'Held sounds may extend a sample; all intersecting notes remain observable.',
                  'Scope is frozen from earlier first-eight-physical-measure trials, not selected for this detector.']}


def analyze(ir,sample):
    result={'version':VERSION,'sample':deepcopy(sample),'conditions':[],
        'selected':None,'production_modified':False,'accuracy_measured':False}
    if sample['abstention_reasons']:
        result['status']='sample_scope_abstention';return result
    policy=context_plan(ir,sample['span'],{'span':sample['span']});result['context_policy']=policy
    if not policy['accepted']:
        result['status']='context_abstention';return result
    voices=observe(ir,sample['span'],sample['lane']);result['voices']=voices
    catalog=propose(ir,sample['span']);result['catalog']=catalog
    alternatives=[(c,i) for c in catalog['candidates'] for i in range(len(c['spelling_alternatives']))]
    result['candidates_without_spelling_refs']=[c['candidate_id'] for c in catalog['candidates'] if not c['spelling_alternatives']]
    if not voices['enumeration_complete']:
        result['status']='voice_enumeration_abstention';return result
    work=len(alternatives)*len(voices['assignments'])
    result['condition_assignment_count']=work;result['condition_assignment_limit']=MAX_CONDITION_ASSIGNMENTS
    if work>MAX_CONDITION_ASSIGNMENTS:
        result['status']='condition_budget_abstention_no_pruning';return result
    for candidate,index in alternatives:
        c=explain(voices,candidate,index)
        if c['all_note_time']!=voices['total_observed_note_time']:raise ValueError('unequal_candidate_evidence_scope')
        result['conditions'].append(c)
    result['status']='evaluated'
    result['same_lane_note_time_for_all_candidates']=True
    result['candidate_scope_is_hypothesis_not_detected_harmony']=True
    return result
