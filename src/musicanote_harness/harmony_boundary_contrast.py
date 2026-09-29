"""Stable multi-pitch replacement evidence; no key, annotation or phrase input.

This is a soft experimental penalty, not proof of a harmonic boundary. Preserve
arpeggiation and single-note figuration; do not infer a chord from a lone pedal.
"""
from fractions import Fraction
from .harmony_joint import f
from .harmony_surface import TEMPLATES
from .formal_ir import q

VERSION='stable-pitch-replacement-0.1.0'


def observation(c):
    return {'boundary':q(c['boundary']),
        'left_span':{'start':q(c['left']['start']),'end':q(c['left']['end'])},
        'right_span':{'start':q(c['right']['start']),'end':q(c['right']['end'])},
        'left_pitch_classes':sorted(c['left']['pcs']),'right_pitch_classes':sorted(c['right']['pcs']),
        'event_refs':sorted(c['left']['refs']|c['right']['refs']),
        'attack_refs':c['attack_refs'],'strength':c['strength'],
        'status':'boundary_evidence_not_confirmed_harmony_change'}


def contrast_blocks(rows, measures):
    points=sorted({t for r in rows for t in (r['start'],r['end'])})
    blocks=[]
    for a,b in zip(points,points[1:]):
        active=[r for r in rows if r['start']<=a<r['end']]
        pcs={r['pitch']%12 for r in active}
        refs={r['id'] for r in active}
        if blocks and blocks[-1]['pcs']==pcs:
            blocks[-1]['end']=b;blocks[-1]['refs']|=refs
        else:blocks.append({'start':a,'end':b,'pcs':pcs,'refs':refs})
    grid=sorted({(f(m['global_start_quarter']),Fraction(4,m['time_signature']['beat_type'])) for m in measures})
    templates=[intervals for _,intervals in TEMPLATES if len(intervals)==3]
    def complete(pcs):
        return len(pcs)==3 and any(pcs=={(root+d)%12 for d in shape} for root in range(12) for shape in templates)
    result=[]
    for left,right in zip(blocks,blocks[1:]):
        t=right['start'];old,new=left['pcs'],right['pcs']
        # The slower of the meters touched by the blocks is conservative at changes.
        units=[next((u for a,u in reversed(grid) if a<=x),Fraction(1)) for x in (left['start'],t)]
        unit=max(units)
        if min(left['end']-left['start'],right['end']-right['start'])<unit/2:continue
        if min(len(old-new),len(new-old))<2 or min(len(old),len(new))<3:continue
        if not (complete(old) or complete(new)):continue
        attacks=[r for r in rows if r['start']==t and r['pitch']%12 in new-old]
        if len({r['pitch']%12 for r in attacks})<2:continue
        result.append({'boundary':t,'left':left,'right':right,
                       'strength':.7*len(old^new)/(len(old)+len(new)),
                       'attack_refs':sorted(r['id'] for r in attacks)})
    return result


def contrast_penalty(candidate,start,end,contrasts):
    evidence=[];penalty=0.
    if candidate['root'] is None:return penalty,evidence
    for c in contrasts:
        t=c['boundary']
        if not start<t<end:continue
        left,right=c['left'],c['right']
        # One chord genuinely containing both sonorities may still span this change.
        if (left['pcs']|right['pcs'])<=set(candidate['pcs']):continue
        duration=min(t-max(start,left['start']),min(end,right['end'])-t)
        weight=float(duration/(end-start));amount=weight*c['strength'];penalty+=amount
        evidence.append({'boundary':q(t),'reason':'stable_multi_pitch_replacement',
            'left_span':{'start':q(left['start']),'end':q(t)},
            'right_span':{'start':q(t),'end':q(right['end'])},
            'left_pitch_classes':sorted(left['pcs']),'right_pitch_classes':sorted(right['pcs']),
            'event_refs':sorted(left['refs']|right['refs']),'attack_refs':c['attack_refs'],
            'weight':weight,'strength':c['strength'],'cost':amount,
            'status':'boundary_evidence_not_confirmed_harmony_change'})
    return penalty,evidence
