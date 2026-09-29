"""Candidate-conditioned inversion and optional pedal reading, never Core facts.

Tertian factor order follows the triad/seventh and inversion chapters. Pedal
detection is a deliberately conservative heuristic, not a textbook theorem.
No annotation, local-key, title, measure-number or phrase inputs.
"""
from copy import deepcopy
from .harmony_joint import prepare, f
from .formal_ir import q
from .harmony_surface import TEMPLATES
from .harmony_candidate_explanation import spelling_evidence

VERSION='candidate-bass-realization-0.1.0'


def attach_bass(ir, result):
    out=deepcopy(result)
    rows,_=prepare(ir)
    byid={s['sounding_event_id']:s for s in ir['sounding_events']}
    all_cells=[]
    for index,segment in enumerate(out['segments']):
        a,b=f(segment['span']['start']),f(segment['span']['end'])
        active=[r for r in rows if r['start']<b and r['end']>a]
        points=sorted({a,b,*[max(a,r['start']) for r in active],*[min(b,r['end']) for r in active]})
        c=segment['selected'];template=dict(TEMPLATES).get(c['label'].partition(':')[2],())
        spelling=spelling_evidence(ir,segment['span'],c)
        supported=[s for s in spelling['candidates'] if not s['conflicting_event_refs']]
        spelled=len(supported)==1 and not spelling.get('unsupported_pitch_event_refs')
        expected=supported[0]['expected_members'] if spelled else []
        def factor(low, sounding):
            if low is None:return None,'silence'
            if not spelled or c.get('root') is None:return None,'unverified_spelling'
            if len({r['pitch']%12 for r in sounding})<2:return None,'sparse_sonority'
            distance=(low-c['root'])%12
            if distance not in template:return None,'bass_outside_candidate'
            ix=template.index(distance)
            bass_rows=[r for r in sounding if r['pitch']==low]
            if any(byid[r['id']]['pitch'].get('spelling','').rstrip('0123456789').replace('-','b')!=expected[ix] for r in bass_rows):
                return None,'bass_spelling_conflict'
            return ix,'conditional_on_selected_chord'
        cells=[]
        for x,y in zip(points,points[1:]):
            sounding=[r for r in active if r['start']<=x<r['end']]
            low=min((r['pitch'] for r in sounding),default=None)
            lows=[r for r in sounding if r['pitch']==low]
            ix,status=factor(low,sounding)
            upper=[r for r in sounding if r['pitch']>low] if low is not None else []
            upperlow=min((r['pitch'] for r in upper),default=None)
            # Upper chord may be incomplete after removing the pedal. Keep it conditional.
            ui,us=factor(upperlow,sounding)
            cell={'span':{'start':q(x),'end':q(y)},'lowest_midi':low,
                'bass_spellings':sorted({byid[r['id']]['pitch'].get('spelling') for r in lows}),
                'bass_event_refs':[r['id'] for r in lows], 'sounding_event_refs':[r['id'] for r in sounding],
                'inversion_index':ix,'status':status,'pedal_hypothesis':None,
                'upper_if_pedal_excluded':{'lowest_midi':upperlow,'inversion_index':ui,'status':us,
                    'bass_spellings':sorted({byid[r['id']]['pitch'].get('spelling') for r in upper if r['pitch']==upperlow}),
                    'bass_event_refs':[r['id'] for r in upper if r['pitch']==upperlow]},
                'selected_segment_index':index}
            cells.append(cell);all_cells.append(cell)
        segment['bass_realization']={'version':VERSION,'cells':cells,
            'policy':'acoustic_bass_conditional_on_selected_shape_not_structural_bass'}
    # A continuous lowest pitch class through >=3 segments and >=2 candidate roots.
    # Octave reattacks are allowed; silence or another bass PC terminates the run.
    runs=[]
    for cell in all_cells:
        pc=cell['lowest_midi']%12 if cell['lowest_midi'] is not None else None
        if runs and pc is not None and runs[-1][-1]['lowest_midi'] is not None and runs[-1][-1]['lowest_midi']%12==pc and runs[-1][-1]['span']['end']==cell['span']['start']:
            runs[-1].append(cell)
        else:runs.append([cell])
    pedals=[]
    for run in runs:
        if run[0]['lowest_midi'] is None:continue
        indexes={c['selected_segment_index'] for c in run}
        roots={out['segments'][i]['selected'].get('root') for i in indexes}-{None}
        a,b=f(run[0]['span']['start']),f(run[-1]['span']['end'])
        units=[f(out['segments'][i].get('beat_unit_quarter',q(1))) for i in indexes]
        upper={c['upper_if_pedal_excluded']['lowest_midi'] for c in run}-{None}
        if len(indexes)<3 or len(roots)<2 or len(upper)<2 or b-a<2*max(units):continue
        pedal={'pedal_id':f'pedal_{len(pedals)+1}','span':{'start':q(a),'end':q(b)},
            'pitch_class':run[0]['lowest_midi']%12,'status':'candidate_not_confirmed',
            'evidence_refs':sorted({r for c in run for r in c['bass_event_refs']}),
            'reason':'continuous_lowest_pc_across_changing_candidate_harmonies',
            'uses_source_annotation':False}
        pedals.append(pedal)
        for cell in run:cell['pedal_hypothesis']=pedal['pedal_id']
    out['bass_realization_version']=VERSION
    out['pedal_hypotheses']=pedals
    out.setdefault('limitations',[]).append('Inversion is conditional on chord choice; pedal is a hypothesis, not automatic bass removal')
    return out


def display_groups(segment):
    """Split only the realization display, never the parent harmonic segmentation."""
    result=[]
    for cell in segment.get('bass_realization',{}).get('cells',[]):
        key=(cell['inversion_index'],cell['status'],cell['pedal_hypothesis'],tuple(cell.get('applied_context_refs',[])),
             cell['upper_if_pedal_excluded']['inversion_index'] if cell['pedal_hypothesis'] else None)
        if result and result[-1]['key']==key and result[-1]['span']['end']==cell['span']['start']:
            result[-1]['span']['end']=cell['span']['end'];result[-1]['cells'].append(cell)
        else:result.append({'key':key,'span':deepcopy(cell['span']),'cells':[cell]})
    return result
