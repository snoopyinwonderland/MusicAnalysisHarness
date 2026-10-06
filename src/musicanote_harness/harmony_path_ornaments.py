"""Spelled, candidate-conditioned NCT geometry under alternative voice tracks.

Explaining an event does not remove it or change member/nonmember note-time.
The all-unconnected alternative makes common support intentionally stringent.
"""
from copy import deepcopy
from fractions import Fraction
from .formal_ir import q
from .harmony_joint import f
from .harmony_catalog_resolution import pitch_pair
from .harmony_reading_voice_context import spelled_height
from .counterpoint_evidence import melodic_geometry
from .harmony_voice_paths import partition
from .harmony_path_contrast import token

VERSION='path-conditioned-ornaments-0.1.0'


def explain(row,candidate,alternative_index,mode='candidate_scope'):
    if mode not in ('candidate_scope','source_hold_counterfactual'):raise ValueError('unknown_scope_mode')
    ca,cb=(f(candidate['span'][k]) for k in ('start','end'))
    ra,rb=(f(row['span'][k]) for k in ('start','end'))
    a,b=(ra,rb) if mode=='source_hold_counterfactual' else (max(ra,ca),min(rb,cb))
    members=candidate['spelling_alternatives'][alternative_index]['members']
    events={s['sounding_event_id']:s for s in row['events']}
    units={};totals={k:Fraction() for k in ('member','nonmember_not_confirmed_nct','spelling_unresolved')}
    for sid,s in events.items():
        duration=min(b,f(s['span']['end']))-max(a,f(s['span']['start']))
        if duration<=0:continue
        state='spelling_unresolved' if spelled_height(s['pitch']) is None else (
            'member' if pitch_pair(s['pitch']) in members else 'nonmember_not_confirmed_nct')
        units[sid]={'state':state,'observed_duration':q(duration),
                    'fully_in_scope':a<=f(s['span']['start']) and f(s['span']['end'])<=b}
        totals[state]+=duration
    blockers=list(candidate['abstention_reasons'])
    blockers.extend(r for r in row.get('path_warnings',[]) if r!='arrival_polyphony_or_sustained_overlap')
    if not row['enumeration_complete']:blockers.append('voice_path_enumeration_incomplete')
    if not units:blockers.append('empty_candidate_scope')
    if totals['spelling_unresolved']:blockers.append('spelling_unresolved')
    result={'candidate_ref':candidate['candidate_id'],'alternative_index':alternative_index,
        'origin_pointer':candidate['origin_pointer'],'provider':candidate['provider'],
        'candidate_span':deepcopy(candidate['span']),'mode':mode,
        'evaluation_span':{'start':q(a),'end':q(b)} if b>a else None,
        'outside_extension_assumption':mode=='source_hold_counterfactual' and (a<ca or b>cb),
        'event_units':units,'note_time_by_state':{k:q(v) for k,v in totals.items()},
        'all_note_time':q(sum(totals.values(),Fraction())),
        'scope':'one explicit part/voice only, not total score evidence',
        'abstention_reasons':sorted(set(blockers)),'patterns':[],'assignments':[],
        'selected':None,'nct_confirmed':False,'used_for_ranking':False,
        'counts_are_confidence':False,'member_totals_depend_on_assignment':False}
    if blockers:return result
    if len(row['assignments'])!=row['possible_assignments'] or not any(not a['links'] for a in row['assignments']):
        raise ValueError('incomplete_or_missing_no_link_alternative')
    patterns={};seen_assignments=set()
    for assignment in row['assignments']:
        aid=assignment['assignment_id']
        if aid in seen_assignments:raise ValueError('duplicate_assignment')
        seen_assignments.add(aid)
        verified=partition(row['events'],assignment['links'])
        if verified!=assignment['tracks']:raise ValueError('track_partition_mismatch')
        explained=set();refs=[]
        for chain in verified:
            for triple in zip(chain,chain[1:],chain[2:]):
                if any(sid not in units or not units[sid]['fully_in_scope'] for sid in triple):continue
                if [units[sid]['state'] for sid in triple]!=['member','nonmember_not_confirmed_nct','member']:continue
                ps=[events[sid]['pitch'] for sid in triple]
                geometry=melodic_geometry([(p['step'],int(f(p['alter'])),p['octave']) for p in ps])
                if geometry['pattern'] is None:continue
                key='pnct_'+token([candidate['candidate_id'],alternative_index,mode,triple,geometry['pattern']])
                if key not in patterns:
                    patterns[key]={'pattern_id':key,'event_refs':list(triple),'middle_ref':triple[1],
                        'conditional_role':geometry['pattern'].replace('_geometry','_candidate'),
                        'supporting_assignment_refs':[],'common_to_all_assignments':False,
                        'nct_confirmed':False,'remove_note':False}
                patterns[key]['supporting_assignment_refs'].append(aid)
                explained.add(triple[1]);refs.append(key)
        nonmembers={sid for sid,u in units.items() if u['state']=='nonmember_not_confirmed_nct'}
        remaining=nonmembers-explained
        explained_time=sum((f(units[sid]['observed_duration']) for sid in explained),Fraction())
        remaining_time=sum((f(units[sid]['observed_duration']) for sid in remaining),Fraction())
        if explained_time+remaining_time!=totals['nonmember_not_confirmed_nct']:raise ValueError('nonmember_time_loss')
        result['assignments'].append({'assignment_ref':aid,'pattern_refs':refs,
            'conditionally_explained_nonmember_refs':sorted(explained),
            'unexplained_nonmember_refs':sorted(remaining),
            'conditional_nonmember_time':q(explained_time),'unexplained_nonmember_time':q(remaining_time),
            'note_removed':False,'selected':False})
    for p in patterns.values():
        p['common_to_all_assignments']=set(p['supporting_assignment_refs'])==seen_assignments
        p['support']='common_conditional_geometry' if p['common_to_all_assignments'] else 'assignment_dependent'
    result['patterns']=list(patterns.values())
    return result


def augment(ir,baseline,left,right):
    result=deepcopy(baseline);records={}
    candidates={c['candidate_id']:c for cat in (left,right) for c in cat['candidates']}
    for pid,row in baseline['continuous_voice_paths']['paths'].items():
        if 'span' not in row:
            records[pid]={'status':'context_not_accepted','conditions':[]};continue
        conditions=[]
        for old in baseline['arrival_path_assessment']['paths'][pid]['conditions']:
            candidate=candidates[old['candidate_ref']]
            mode='source_hold_counterfactual' if old['hypothesis']=='source_hold_counterfactual' else 'candidate_scope'
            condition=explain(row,candidate,old['alternative_index'],mode)
            conditions.append({'condition_id':old['condition_id'],'edge_refs':old['edge_refs'],**condition})
        records[pid]={'conditions':conditions,'global_harmony_selected':None}
    result['path_conditioned_ornaments']={'version':VERSION,'paths':records,
        'production_modified':False,'harmonic_results_changed':False,
        'limits':['Contiguous three-note passing/neighbor geometry only, conditional on a single spelled chord.',
                  'Includes the no-link alternative; occurrence counts are not likelihoods.',
                  'No accent, preparation, suspension, double-neighbor or style verdict added here.',
                  'Nonmembers remain in note-time totals, including isolated or unexplained events.',
                  'Different candidate scopes must not be compared as if they cover identical evidence.']}
    return result
