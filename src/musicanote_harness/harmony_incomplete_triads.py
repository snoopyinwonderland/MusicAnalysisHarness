"""Explicit ordinary-triad fifth-omission assumptions, never virtual notes.

Keeps observationally indistinguishable alternatives and the strict baseline.
"""
from collections import Counter
from copy import deepcopy
from .seventh_context import chord
from .harmony_bass_return import run as bass_return

VERSION='incomplete-triad-hypotheses-0.1.0'


def observed_signature(row):
    missing={tuple(p) for p in row['missing_members']}
    observed=tuple(sorted(tuple(p) for p in row['members'] if tuple(p) not in missing))
    return observed,tuple(sorted(row['nonmember_event_refs']))


def omission(row):
    base={'candidate_ref':row['candidate_ref'],'alternative_index':row['alternative_index'],
          'reading_index':row['reading_index'],'missing_members':deepcopy(row['missing_members']),
          'virtual_events_created':False,'omission_confirmed':False,'quality_confirmed':False,
          'eligible_for_conditional_comparison':False}
    if not row['missing_members']:return {**base,'status':'no_omission_needed'}
    root=row['root_spelling']
    if root is None:return {**base,'status':'root_unavailable'}
    matched=None
    for quality in ('M','m'):
        template=chord(root,quality)['members']
        if {tuple(m) for m in template}=={tuple(m) for m in row['members']}:
            matched=(quality,template);break
    if matched is None:return {**base,'status':'other_quality_or_extended_omission_deferred'}
    quality,template=matched
    if row['missing_members'] != [template[2]]:
        return {**base,'status':'root_third_or_multiple_missing_deferred'}
    # Root and third must both be observed; no chord-tone or bass exemption.
    blockers=list(row['candidate_blockers'])
    if row['other_nonmember_refs']:blockers.append('other_nonmembers_require_independent_evidence')
    return {**base,'status':'ordinary_fifth_omission_assumption',
            'assumed_missing_pitch':deepcopy(template[2]),'assumed_quality':quality,
            'observed_required_members':deepcopy(template[:2]),'blockers':blockers,
            'eligible_for_conditional_comparison':not blockers,
            'required_later_evidence':['competing_quality_and_root_comparison','surrounding_harmony_and_voice_consistency'],
            'assumption_is_evidence':False}


def augment_chain(chain):
    out=deepcopy(chain)
    if chain['status']!='ready':return out
    for table in out['interval_tables'].values():
        assumptions=[]
        for row in table['readings']:
            a=omission(row)
            # No label or preferred root: all candidates explaining exactly the
            # same observed members/nonmembers remain competing descriptions.
            a['observationally_equivalent_reading_indices']=[r['reading_index'] for r in table['readings']
                if r['reading_index']!=row['reading_index'] and observed_signature(r)==observed_signature(row)]
            assumptions.append(a)
        table['omission_hypotheses']=assumptions
    for comparison in out['comparisons']:
        groups=[];assumption_groups=[]
        for side,ref in enumerate(comparison['interval_refs']):
            table=out['interval_tables'][ref];member=side!=1
            additions=[a['reading_index'] for a in table['omission_hypotheses']
                if a['eligible_for_conditional_comparison'] and table['readings'][a['reading_index']]['bass_is_member']==member]
            assumption_groups.append(additions)
            groups.append(sorted(set(comparison['clean_return_reading_groups'][side]) | set(additions)))
        count=len(groups[0])*len(groups[1])*len(groups[2])
        comparison['omission_comparison']={
            'reading_groups':groups,'assumption_reading_groups':assumption_groups,
            'combination_count':count,'assumption_dependent_combination_count':count-comparison['clean_combination_count'],
            'status':'possible_under_explicit_omission_assumptions' if count>comparison['clean_combination_count'] else
                     'strict_support_only' if count else 'still_insufficient',
            'pedal_confirmed':False,'omission_confirmed':False,'quality_confirmed':False,
            'joint_voice_assignment_verified':False,'selected':None}
    return out


def run(lattice,survey,ir):
    base=bass_return(lattice,survey,ir)
    out={**base,'version':VERSION,'baseline_version':base['version'],'baseline_summary':deepcopy(base.get('summary',{}))}
    out['chain_comparisons']=[augment_chain(c) for c in base['chain_comparisons']]
    counts=Counter()
    for chain in out['chain_comparisons']:
        for comparison in chain['comparisons']:
            counts[comparison['omission_comparison']['status']]+=1
    out['summary']=dict(counts)
    out['omission_limits']=[
        'Only exact ordinary major/minor triads missing the perfect fifth; other qualities, seventh and root omissions deferred.',
        'Observed root and third are insufficient to identify the fifth or choose quality; all observational competitors retained.',
        'Conditional combinations contain assumptions, not new observations or musical accuracy gains.',
        'Strict statuses and missing-pitch lists remain unchanged; no source events or notes added.']
    return out
