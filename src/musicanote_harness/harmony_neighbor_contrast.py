"""Compare fixed-harmony neighbor readings with member-based local alternatives.

Profiles are observations under hypotheses, not a score, probability or winner.
No source harmony annotation, inferred preparation, or deleted melody notes.
"""
from fractions import Fraction as F
from .formal_ir import q
from .harmony_joint import f
from .harmony_open_candidates import window
from .harmony_path_contrast import token

VERSION = 'neighbor-reading-contrast-0.1.0'


def profile(units, candidate, span, figure_refs):
    a,b = f(span['start']),f(span['end'])
    groups = {'figure':{},'other':{}}
    observed = set(); refs = []
    for sid,s in sorted(units.items()):
        duration = min(b,f(s['span']['end']))-max(a,f(s['span']['start']))
        if duration <= 0:continue
        refs.append(sid)
        midi=s['pitch'].get('midi_pitch')
        if isinstance(midi,(int,float)):observed.add(midi % 12)
        state = candidate['event_states'].get(sid,'spelling_unresolved')
        group = groups['figure' if sid in figure_refs else 'other']
        entry = group.setdefault(state,{'event_refs':[],'duration_quarters':F(0)})
        entry['event_refs'].append(sid);entry['duration_quarters'] += duration
    for group in groups.values():
        for entry in group.values():entry['duration_quarters'] = q(entry['duration_quarters'])
    return {'span':span,'event_refs':refs,'groups':groups,'other_event_evidence_present':bool(groups['other']),
            'missing_member_pcs':sorted(set(candidate['pcs'])-observed),
            'duration_semantics':'sum of clipped sound durations; polyphonic durations may exceed window duration',
            'confirmed_chord':False}


def minimum_changes(stages):
    """Label-change count in a hypothesis lattice, never a musical preference."""
    costs = {}
    for i,stage in enumerate(stages):
        labels = {c['label'] for c in stage['member_alternatives']}
        if not labels:return None
        costs = {label:(0 if i==0 else min(cost+(prev!=label) for prev,cost in costs.items())) for label in labels}
    return min(costs.values()) if costs else None


def compare(ir, parent):
    results = []; cache = {}
    units = parent['event_units']; figure_records = parent['double_neighbor_evidence']['records']
    for figure in figure_records:
        holds = [e for e in figure['candidate_explanations'] if e['status'] in (
            'conditional_double_neighbor_compatible','incomplete_double_neighbor_hypothesis')]
        if not holds:continue
        refs = figure['event_refs']; blocked = [r for r in figure['abstention_reasons'] if r!='preparation_anchor_not_observed_in_window']
        if blocked:continue
        # Only actual onset partitions; no arbitrary grid cuts or note extension.
        points = [f(units[sid]['span']['start']) for sid in refs]+[f(units[refs[-1]]['span']['end'])]
        if any(x>=y for x,y in zip(points,points[1:])):continue
        stages=[]
        for sid,a,b in zip(refs,points,points[1:]):
            span={'start':q(a),'end':q(b)}
            if (a,b) not in cache:cache[a,b]=window(ir,span)
            local=cache[a,b]
            # Parent candidates are retained only as explicit carried hypotheses.
            # A lone arrival note must not manufacture an observed complete chord.
            options={c['label']:(c,'parent_window_hypothesis') for c in parent['candidates'] if c['event_states'].get(sid)=='member'}
            for c in local['candidates']:
                if c['event_states'].get(sid)=='member':options[c['label']]=(c,'local_observation_candidate')
            alternatives=[]
            if not local['abstention_reasons']:
                for label,(c,origin) in sorted(options.items()):
                    alternatives.append({'candidate_ref':c['candidate_id'],'label':label,'origin':origin,
                        'profile':profile(units,c,span,set(refs)),
                        'source_root_hypotheses':c['root_hypotheses'],'selected':None})
            stages.append({'span':span,'focus_event_ref':sid,'member_alternatives':alternatives,
                'abstention_reasons':local['abstention_reasons']})
        fixed=[]
        for explanation in holds:
            c=next(c for c in parent['candidates'] if c['candidate_id']==explanation['candidate_ref'])
            outside=[]
            for side,a,b in [('before',f(parent['span']['start']),points[0]),('after',points[-1],f(parent['span']['end']))]:
                if a<b:outside.append({'side':side,'profile':profile(units,c,{'start':q(a),'end':q(b)},set(refs))})
            fixed.append({'candidate_ref':c['candidate_id'],'label':c['label'],'figure_status':explanation['status'],
                'profile':profile(units,c,figure['span'],set(refs)),
                'stage_profiles':[profile(units,c,s['span'],set(refs)) for s in stages],
                'surrounding_profiles':outside,'constant_harmony_is_assumption':True,'selected':None})
        sets=[{c['label'] for c in s['member_alternatives']} for s in stages]
        common=sorted(set.intersection(*sets)) if sets else []
        results.append({'contrast_id':'ncontrast_'+token([parent['window_id'],figure['evidence_id']]),
            'figure_ref':figure['evidence_id'],'event_refs':refs,'neighbor_refs':figure['neighbor_refs'],
            'span':figure['span'],'fixed_harmony_readings':fixed,'member_stages':stages,
            'constant_member_alternative_labels':common,
            'minimum_label_changes_if_all_figure_notes_are_members':minimum_changes(stages),
            'preparation_anchor_observed':figure['preparation_anchor_observed'],
            'preparation_inferred':False,'selection':None,'ranking_performed':False,
            'limits':['Label-change count is a combinatorial property, not a preference for fewer chords.',
                'Local stage chord identity is hypothesized over its full span, not guaranteed by a single note.',
                'Carried parent hypotheses and missing members remain explicit; no automatic root filling.',
                'Other-event membership is supporting or conflicting evidence, not an NCT truth label.',
                'Surrounding context is clipped to the parent window; empty context is unknown, not support.',
                'Alternatives outside the current triad/seventh templates may be missing.']})
    return {'version':VERSION,'records':results,'source_annotations_used':False,'selected':None}
