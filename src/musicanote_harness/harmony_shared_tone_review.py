"""Retain triad-replacement / seventh-prolongation alternatives, never force a split.

Only fully observed stable vertical triads are covered. A shared pitch-class
union does not establish harmonic rhythm; local costs are not probabilities.
"""
from fractions import Fraction as F
import hashlib
from itertools import product
from collections import Counter

from .formal_ir import q
from .harmony_joint import prepare, f
from .harmony_surface import TEMPLATES, PITCH_NAMES
from .harmony_multiscale_shadow import provider, VERSION as BASE_VERSION
from .harmony_cost_diagnostic import transition
from .harmony_candidate_explanation import spelling_evidence

VERSION = 'shared-tone-competing-readings-0.1.0'


def shapes(pcs, size):
    return [{'root':r, 'label':f'{PITCH_NAMES[r]}:{quality}', 'pcs':sorted(pcs)}
            for r in range(12) for quality, intervals in TEMPLATES
            if len(intervals)==size and pcs=={(r+i)%12 for i in intervals}]


def local_scorer(ir, rows, neighbors, unit_at):
    """Shared existing objective; extraction leaves the vertical review unchanged."""
    choose=provider(ir.get('measures',[]),enable_boundary_contrast=True)
    scored={}
    def score(a,b,shape):
        key=(a,b)
        if key not in scored:
            scored[key]=choose(rows,neighbors,a,b,unit_at(a),limit=None)
        c=next(c for c in scored[key] if c['label']==shape['label'])
        duration=float((b-a)/unit_at(a))
        parts={'pooled_fit':duration*c['pooled_cost'],
               'temporal_regret':duration*c['temporal_regret'],
               'boundary_contrast':duration*c['boundary_contrast_cost'], 'segment_charge':.15}
        return {'span':{'start':q(a),'end':q(b)}, 'candidate':c, 'cost_parts':parts,
                'spelling':spelling_evidence(ir,{'start':q(a),'end':q(b)},c)}
    return score


def observe(ir, analysis_span=None):
    """No Core mutation, source-label input, or selected-path changes."""
    rows, neighbors = prepare(ir)
    if analysis_span is None:
        if not rows:return {'version':VERSION, 'alternatives':[], 'production_enabled':False}
        analysis_span={'start':q(0), 'end':q(max(r['end'] for r in rows))}
    start,end=f(analysis_span['start']),f(analysis_span['end'])
    if start<0 or end<=start:raise ValueError('invalid_analysis_span')
    measures=ir.get('measures',[])
    grid=sorted({(f(m['global_start_quarter']),F(4,m['time_signature']['beat_type'])) for m in measures})
    def unit_at(t):return next((u for a,u in reversed(grid) if a<=t),F(1))
    # Full-score blocks prevent a clipped analysis window inventing a duration.
    points=sorted({t for r in rows for t in (r['start'],r['end'])})
    blocks=[]
    for a,b in zip(points,points[1:]):
        active=[r for r in rows if r['start']<=a<r['end']]
        pcs={r['pitch']%12 for r in active}
        if blocks and blocks[-1]['pcs']==pcs:blocks[-1]['end']=b
        else:blocks.append({'start':a,'end':b,'pcs':pcs})
    score=local_scorer(ir,rows,neighbors,unit_at)
    alternatives=[];gates=Counter();examined=0
    for left,right in zip(blocks,blocks[1:]):
        a,t,b=left['start'],right['start'],right['end']
        if not start<=a<t<b<=end:continue
        examined+=1
        # Mixed meters need piecewise cost integration; do not silently use one beat.
        units={unit_at(a),unit_at(t)}|{u for x,u in grid if a<x<b}
        if len(units)!=1:
            gates['mixed_meter']+=1;continue
        unit=next(iter(units))
        if min(t-a,b-t)<unit/2:
            gates['blocks_shorter_than_half_denominator_beat']+=1;continue
        old,new=left['pcs'],right['pcs']
        ls,rs,unions=shapes(old,3),shapes(new,3),shapes(old|new,4)
        if not ls or not rs:
            gates['not_two_complete_vertical_triads']+=1;continue
        if len(old&new)!=2 or not unions:
            gates['not_two_common_pcs_with_seventh_union']+=1;continue
        before=[r for r in rows if r['start']<t<=r['end']]
        after=[r for r in rows if r['start']<=t<r['end']]
        new_attacks=[r for r in after if r['start']==t and r['pitch']%12 in new-old]
        if not new_attacks:
            gates['no_new_member_attack']+=1;continue
        old_releases=[r for r in before if r['end']==t and r['pitch']%12 in old-new]
        crossing=[r for r in rows if r['start']<t<r['end']]
        context=[r for r in rows if r['start']<b and r['end']>a]
        left_bass=min(r['pitch'] for r in before);right_bass=min(r['pitch'] for r in after)
        bass_attacks=[r['id'] for r in after if r['pitch']==right_bass and r['start']==t]
        merge=[];split=[]
        for shape in unions:
            s=score(a,b,shape)
            merge.append({'segments':[s], 'local_cost':sum(s['cost_parts'].values())})
        for lshape,rshape in product(ls,rs):
            l,r=score(a,t,lshape),score(t,b,rshape)
            change,resolution=transition(l['candidate'],r['candidate'])
            split.append({'segments':[l,r], 'transition_parts':{'label_change':change,'resolution_discount':resolution},
                          'local_cost':sum(l['cost_parts'].values())+sum(r['cost_parts'].values())+change+resolution})
        merge.sort(key=lambda r:r['local_cost']);split.sort(key=lambda r:r['local_cost'])
        digest=hashlib.sha256((str(a)+'|'+str(t)+'|'+str(b)+'|'+','.join(sorted(r['id'] for r in context))).encode()).hexdigest()[:20]
        alternatives.append({'evidence_id':'shared_'+digest, 'span':{'start':q(a),'end':q(b)},'boundary':q(t),
            'beat_unit_quarter':q(unit), 'left_pitch_classes':sorted(old),'right_pitch_classes':sorted(new),
            'common_pitch_classes':sorted(old&new), 'entering_pitch_classes':sorted(new-old),'leaving_pitch_classes':sorted(old-new),
            'event_refs':sorted(r['id'] for r in context), 'new_member_attack_refs':sorted(r['id'] for r in new_attacks),
            'old_member_release_refs':sorted(r['id'] for r in old_releases),
            'sustained_common_event_refs':sorted(r['id'] for r in crossing),
            'bass':{'before_midi':left_bass,'after_midi':right_bass,'changed':left_bass!=right_bass,
                    'new_attack_refs':sorted(bass_attacks),'continued_refs':sorted(r['id'] for r in crossing if r['pitch']==right_bass)},
            'merged_seventh':merge,'split_triads':split,
            'split_minus_merge_cost':split[0]['local_cost']-merge[0]['local_cost'],
            'selected_hypothesis':None,'review_status':'ambiguous_needs_context',
            'split_support':['complete_triads_on_both_sides','new_member_attack_and_old_member_release'],
            'merge_support':['complete_seventh_union','two_shared_pitch_classes'],
            'unresolved':['local_key_and_function','voice_leading_role','harmonic_rhythm','wider_context']})
    return {'version':VERSION,'cost_engine_version':BASE_VERSION,'analysis_span':analysis_span,
            'gate_audit':{'fully_contained_adjacent_pairs':examined,'first_failed_gate':dict(gates),
                          'accepted':len(alternatives),'counts_are_pairs_not_musical_errors':True},
            'alternatives':alternatives,'production_enabled':False,'source_labels_used':False,
            'selected_path_modified':False,'confidence_calibrated':False,
            'cost_scope':'local two-block counterfactual, no external transitions, figure split cost disabled',
            'limitations':['Exact vertical triads only; sparse arpeggios and NCT-rich textures can be missed',
                           'Denominator beat is not inferred pulse',
                           'Same observed notes can support different harmonic interpretations',
                           'Adjacent records overlap and are not independent cases']}
