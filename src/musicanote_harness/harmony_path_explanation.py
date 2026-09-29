"""Explain fixed one-/two-chord paths over identical event-time cells.

An extended edge chord is a TEST assumption, not a discovered harmonic span.
No NCT deletion, winner, cost adjustment, or source-annotation input.
"""
from fractions import Fraction
from itertools import product

from .formal_ir import q
from .harmony_joint import f
from .harmony_candidate_explanation import spelling_evidence
from .harmony_reading_voice_context import spelled_height

VERSION = 'fixed-path-explanation-0.1.0'


def explain(ir, candidate, context):
    a,b=f(candidate['span']['start']),f(candidate['span']['end']); t=f(candidate['boundary'])
    ca,cb=f(context['start']),f(context['end']);unit=f(candidate['beat_unit_quarter'])
    if not (0<=ca<=a<t<b<=cb and unit>0):raise ValueError('invalid_candidate_or_context')
    x,y=max(ca,a-unit),min(cb,b+unit)
    sounds=sorted((s for s in ir['sounding_events'] if f(s['span']['start'])<y and f(s['span']['end'])>x),key=lambda s:s['sounding_event_id'])
    notes={n['note_id']:n for n in ir['note_events']}
    blockers=[]
    if x!=a-unit or y!=b+unit:blockers.append('edge_context_truncated')
    meters=ir.get('measures',[])
    at_start=max((f(m['global_start_quarter']) for m in meters if f(m['global_start_quarter'])<=x),default=None)
    signatures={str(m['time_signature']) for m in meters if f(m['global_start_quarter'])==at_start or x<f(m['global_start_quarter'])<y}
    if at_start is None or len(signatures)!=1:blockers.append('meter_unavailable_or_changed')
    for m in meters:
        bar=m.get('repeat_barline') or {};bt=f(m['global_start_quarter'])+(0 if bar.get('location')=='left' else f(m['actual_duration_quarter']))
        if x<bt<y and any(bar.get(k) for k in ('repeat_direction','ending_number')):blockers.append('repeat_or_ending_barrier')
    if any(n.get('grace',{}).get('is_grace') and x<=f(n['global_onset_quarter'])<y for n in notes.values()):blockers.append('grace_timing_unresolved')
    paths=[]
    for kind in ('merged_seventh','split_triads'):
        for index,path in enumerate(candidate[kind]):
            segs=path['segments']
            boundaries=[(f(s['span']['start']),f(s['span']['end'])) for s in segs]
            if not boundaries or boundaries[0][0]!=a or boundaries[-1][1]!=b or any(lo>=hi for lo,hi in boundaries) or any(l[1]!=r[0] for l,r in zip(boundaries,boundaries[1:])):
                raise ValueError('path_must_partition_same_core_span')
            prepared=[]
            for seg in segs:
                c=seg['candidate'];sp=spelling_evidence(ir,seg['span'],c)
                # One coherent root spelling must explain all core member notes;
                # do not union incompatible enharmonic interpretations.
                members={s['sounding_event_id'] for s in sounds if f(s['span']['start'])<f(seg['span']['end']) and f(s['span']['end'])>f(seg['span']['start']) and s['pitch']['midi_pitch']%12 in c['pcs']}
                roots=[r for r in sp['candidates'] if members<=set(r['supported_event_refs'])]
                prepared.append({'span':seg['span'],'candidate':{k:c[k] for k in ('root','label','pcs')},'root_hypotheses':roots})
            paths.append({'path_ref':kind+':'+str(index),'kind':kind,'index':index,'segments':prepared,
                'original_local_cost':path.get('local_cost'),'selected':None})
    points=sorted({x,a,t,b,y}|{max(x,f(s['span']['start'])) for s in sounds}|{min(y,f(s['span']['end'])) for s in sounds})
    cells=[]
    for lo,hi in zip(points,points[1:]):
        if hi<=lo:continue
        active=[s for s in sounds if f(s['span']['start'])<hi and f(s['span']['end'])>lo]
        cells.append({'span':{'start':q(lo),'end':q(hi)},'region':'before' if hi<=a else 'after' if lo>=b else 'core',
            'event_refs':[s['sounding_event_id'] for s in active]})
    by_id={s['sounding_event_id']:s for s in sounds}
    def member(s,seg):
        p=s['pitch']
        if spelled_height(p) is None:return 'spelling_unresolved'
        if p['midi_pitch']%12 not in seg['candidate']['pcs']:return 'nonmember_not_confirmed_nct'
        acc=int(f(p['alter']));name=p['step']+('#'*acc if acc>0 else 'b'*(-acc))
        if not seg['root_hypotheses']:return 'spelling_unresolved'
        # Ambiguous root hypotheses must agree rather than selecting a convenient one.
        return 'member' if all(name in r['expected_members'] for r in seg['root_hypotheses']) else 'spelling_unresolved'
    for path in paths:
        evaluations=[]
        for cell in cells:
            lo=f(cell['span']['start'])
            segment=next((s for s in path['segments'] if f(s['span']['start'])<=lo<f(s['span']['end'])),path['segments'][0] if lo<a else path['segments'][-1])
            evaluations.append({'states':{sid:member(by_id[sid],segment) for sid in cell['event_refs']},
                'candidate':segment['candidate'],'outside_extension_assumption':cell['region']!='core'})
        path['cells']=evaluations
    pairs=[]
    for merged,split in product([p for p in paths if p['kind']=='merged_seventh'],[p for p in paths if p['kind']=='split_triads']):
        comparisons=[];exclusive=set();unresolved=False
        for cell,l,r in zip(cells,merged['cells'],split['cells']):
            buckets={k:[] for k in ('both_members','merged_only_member','split_only_member','neither_member','spelling_unresolved')}
            for sid in cell['event_refs']:
                ls,rs=l['states'][sid],r['states'][sid]
                bucket='spelling_unresolved' if 'spelling_unresolved' in (ls,rs) else 'both_members' if ls==rs=='member' else 'merged_only_member' if ls=='member' else 'split_only_member' if rs=='member' else 'neither_member'
                buckets[bucket].append(sid)
                if bucket in ('merged_only_member','split_only_member'):exclusive.add(sid)
                if bucket=='spelling_unresolved':unresolved=True
            comparisons.append({'event_buckets':buckets})
        # Union over time per PC, not summed voices. This is a diagnostic exposure,
        # NOT a score: a larger chord template trivially admits more tones.
        exposure={region:{k:Fraction(0) for k in ('merged_only_member','split_only_member','neither_member')} for region in ('before','core','after')}
        for cell,comp in zip(cells,comparisons):
            for k in exposure[cell['region']]:
                pcs={by_id[sid]['pitch']['midi_pitch']%12 for sid in comp['event_buckets'][k]}
                exposure[cell['region']][k]+=(f(cell['span']['end'])-f(cell['span']['start']))*len(pcs)
        pairs.append({'merged_ref':merged['path_ref'],'split_ref':split['path_ref'],'cells':comparisons,
            'diagnostic_pc_quarter_exposure':{r:{k:q(v) for k,v in vs.items()} for r,vs in exposure.items()},
            'exclusive_event_refs':sorted(exclusive),'status':'context_unresolved' if blockers else 'spelling_unresolved' if unresolved else 'different_explanation_not_winner' if exclusive else 'same_observed_membership_not_equivalent_harmony',
            'selected':None,'ranking_weight':None,'independent_vote':False})
    return {'version':VERSION,'candidate_ref':candidate['evidence_id'],'core_span':candidate['span'],'comparison_span':{'start':q(x),'end':q(y)},
        'boundary':candidate['boundary'],'context':context,'abstention_reasons':sorted(set(blockers)), 'cells':cells,'paths':paths,'pairs':pairs,
        'event_units':{s['sounding_event_id']:{'pitch':s['pitch'],'source_note_ids':s['source_note_ids'],'original_span':s['span']} for s in sounds},
        'selected':None,'used_for_ranking':False,'source_annotation_used':False,
        'limits':['Edge chords are extended ONLY as explicit competing assumptions; no harmonic span was changed.',
            'All sounding intervals/rests are preserved; nonmember is not an NCT diagnosis.',
            'PC-time exposure favors larger templates and MUST NOT be used alone to choose a path.',
            'Membership equivalence does not establish equivalent function, cadence or prolongation.']}
