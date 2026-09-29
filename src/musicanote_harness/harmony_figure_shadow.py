"""Opt-in soft split penalty for recurrent complete arpeggio cells.

Never reward equal harmony across repetitions. Complete vertical replacements
inside a cell veto the penalty, even if their union fits one seventh chord.
"""
from fractions import Fraction as F
from .formal_ir import q
from .harmony_joint import prepare, f, analyze_joint
from .harmony_surface import TEMPLATES
from .harmony_multiscale_shadow import provider, continuous_sound
from .harmony_figure_evidence import observe
from .harmony_candidate_explanation import explain_path
from .harmony_bass import attach_bass
from .harmony_applied_context import attach_applied_context

VERSION='recurrent-figure-shadow-0.1.0'
DEFAULT_WEIGHT=.08


def complete_shapes(pcs):
    return [{'root':r,'quality':quality} for r in range(12) for quality,shape in TEMPLATES
            if pcs=={(r+d)%12 for d in shape}]


def inspect_cells(ir, analysis_span):
    evidence=observe(ir,analysis_span)
    rows,_=prepare(ir);cells={}
    for match in evidence['rhythmic_matches']:
        if not match['weak_pitch_variation_compatible']:continue
        for side in ('earlier','later'):
            cell=match[side];key=(cell['voice_id'],f(cell['span']['start']),f(cell['span']['end']))
            if key not in cells:cells[key]={**cell,'match_refs':[]}
            cells[key]['match_refs'].append(match['evidence_id'])
    output=[]
    for c in cells.values():
        a,b=f(c['span']['start']),f(c['span']['end']);unit=f(c['beat_unit'])
        active=[r for r in rows if r['start']<b and r['end']>a]
        pcs={r['pitch']%12 for r in active};shapes=complete_shapes(pcs)
        points=sorted({a,b}|{t for r in active for t in (r['start'],r['end']) if a<t<b})
        blocks=[]
        for x,y in zip(points,points[1:]):
            ps={r['pitch']%12 for r in active if r['start']<=x<r['end']}
            if blocks and blocks[-1]['pcs']==ps:blocks[-1]['end']=y
            else:blocks.append({'start':x,'end':y,'pcs':ps})
        guards=[]
        for left,right in zip(blocks,blocks[1:]):
            if min(left['end']-left['start'],right['end']-right['start'])<unit/4:continue
            if left['pcs']==right['pcs'] or not complete_shapes(left['pcs']) or not complete_shapes(right['pcs']):continue
            attacks=[r['id'] for r in active if r['start']==right['start'] and r['pitch']%12 in right['pcs']-left['pcs']]
            if not attacks:continue
            guards.append({'boundary':q(right['start']),'left_pcs':sorted(left['pcs']),
                           'right_pcs':sorted(right['pcs']),'new_member_attack_refs':sorted(attacks),
                           'reason':'complete_vertical_replacement_not_necessarily_confirmed_change'})
        reason=('sound_continues_past_cell' if c['last_sound_crosses_cell_end'] else
                'silence_inside_cell' if not continuous_sound(active,a,b) else
                'no_complete_pooled_shape' if not shapes else
                'vertical_replacement_guard' if guards else 'eligible_recurrent_complete_cell')
        output.append({**c,'all_sounding_event_refs':sorted(r['id'] for r in active),
                       'pooled_pitch_classes':sorted(pcs),'complete_shapes':shapes,
                       'change_guards':guards,'eligibility':reason})
    return output


def analyze(ir,analysis_span=None,*,weight=DEFAULT_WEIGHT,enable_guard=True,enable_distributed=True):
    if type(weight) not in (int,float) or not 0<=weight<=.15:raise ValueError('invalid_figure_weight')
    if type(enable_guard) is not bool:raise ValueError('guard_must_be_boolean')
    rows,_=prepare(ir)
    if analysis_span is None:
        if not rows:return {'engine_version':VERSION,'segments':[],'figure_cells':[],'production_enabled':False}
        analysis_span={'start':q(0),'end':q(max(r['end'] for r in rows))}
    cells=inspect_cells(ir,analysis_span)
    eligible=[c for c in cells if c['eligibility']=='eligible_recurrent_complete_cell' or
              (not enable_guard and c['eligibility']=='vertical_replacement_guard')]
    base=provider(ir.get('measures',[]),enable_distributed=enable_distributed,enable_boundary_contrast=True)
    def choose(rows,neighbors,start,end,beat,limit=5):
        choices=base(rows,neighbors,start,end,beat,limit=None)
        support=[c for c in eligible if f(c['span']['start'])<start<f(c['span']['end'])]
        result=[]
        for c in choices:
            # One fixed boundary charge, not a sum over voices/overlapping matches.
            charge=weight if support and c['root'] is not None else 0.
            normalized=charge/float((end-start)/beat)
            result.append({**c,'cost':c['cost']+normalized,'figure_split_cost':normalized,
                           'figure_split_charge':charge,
                           'figure_match_refs':sorted({r for s in support for r in s['match_refs']}) if charge else []})
        return sorted(result,key=lambda c:(c['cost'],c['label']))[:limit]
    result=analyze_joint(ir,candidate_provider=choose,analysis_span=analysis_span)
    result.update(engine_version=VERSION,figure_cells=cells,production_enabled=False,
                  figure_policy={'weight':weight,'guard_enabled':enable_guard,'enable_distributed':enable_distributed,
                                 'confidence_calibrated':False,'same_chord_across_repetitions_assumed':False})
    result['cost_explanation']=explain(result)
    return attach_applied_context(ir,attach_bass(ir,result))


def explain(result):
    base=explain_path(result,verify=False)
    figure=sum(float((f(s['span']['end'])-f(s['span']['start']))/f(s['beat_unit_quarter']))*
               s['selected'].get('figure_split_cost',0) for s in result['segments'])
    total=base['reconstructed_path_cost']+figure
    if abs(total-result['path_cost'])>1e-8:raise ValueError('figure_cost_reconstruction_failed')
    return {'base_objective':base,'figure_penalty':figure,'reconstructed_path_cost':total}
