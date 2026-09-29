"""Attach acoustic bass and adjacent-window resolution evidence; never choose truth."""
from collections import defaultdict, Counter
from copy import deepcopy
from .harmony_joint import f
from .harmony_surface import TEMPLATES
from .harmony_reading_voice_context import voice_links, relation
from .harmony_path_contrast import token
from .harmony_voice_figures import octave_links, double_neighbors

VERSION='inclusive-candidate-context-0.2.0'
LETTERS='CDEFGAB'
TARGET_TRIAD={'major':'major','minor':'minor','dominant7':'major','major7':'major','minor7':'minor'}


def bass_evidence(window,candidate):
    intervals=dict(TEMPLATES)[candidate['label'].split(':')[1]]
    cells=[]
    for cell in window['cells']:
        refs=cell['bass_refs'];factors=[]
        for sid in refs:
            p=window['event_units'][sid]['pitch'];distance=(p['midi_pitch']-candidate['root'])%12
            factors.append(intervals.index(distance) if candidate['event_states'][sid]=='member' and distance in intervals else None)
        index=factors[0] if factors and len(set(factors))==1 and factors[0] is not None else None
        status='conditional_factor' if index is not None else 'silence' if cell['silence'] else 'bass_unexplained_or_spelling_unresolved'
        cells.append({'span':cell['span'],'bass_refs':refs,'bass_spellings':[window['event_units'][sid]['pitch']['spelling'] for sid in refs],
            'factor_index':index,'status':status})
    onset=cells[0]['factor_index'] if cells else None
    return {'cells':cells,'onset_factor_index':onset,'onset_inversion_hypothesis':onset,
        'observed_factor_indices':sorted({c['factor_index'] for c in cells if c['factor_index'] is not None}),
        'uniform_factor':bool(cells) and onset is not None and all(c['factor_index']==onset for c in cells),
        'structural_bass_confirmed':False,'inversion_confirmed':False,
        'policy':'Acoustic lowest sound under this candidate. Arpeggio bass changes do not automatically change harmonic inversion.'}


def root_relation(source,target):
    sq=source['label'].split(':')[1];tq=target['label'].split(':')[1]
    if tq not in TARGET_TRIAD or not source['root_hypotheses'] or not target['root_hypotheses']:return None
    delta=(source['root']-target['root'])%12
    kind='dominant_to_target' if sq in ('major','dominant7') and delta==7 else 'leading_tone_to_target' if sq in ('diminished','diminished7','half-diminished7') and delta==11 else None
    if kind is None:return None
    required=3 if kind=='dominant_to_target' else 1
    if any((LETTERS.index(t['root_spelling'][0])-LETTERS.index(s['root_spelling'][0]))%7!=required for s in source['root_hypotheses'] for t in target['root_hypotheses']):return None
    return kind


def direct_relations(link,source,target):
    if source['event_states'].get(link['source_refs'][0])!='member' or target['event_states'].get(link['source_refs'][1])!='member':return []
    tags=relation(link,source,target)
    tq=target['label'].split(':')[1]
    if tq in TARGET_TRIAD and tq not in ('major','minor'):
        triad={**target,'label':target['label'].split(':')[0]+':'+TARGET_TRIAD[tq]}
        # Only expand the allowed target quality for root-directed motion.
        # Keep original candidate PCs: seventh-to-member still uses full shape.
        tags+=relation(link,source,triad)
    return sorted(set(tags)-{'same_spelled_pitch_reattack'})


def attach(ir,proposals):
    out=deepcopy(proposals);records=out['records'];by_start=defaultdict(list)
    voices=voice_links(ir,out['analysis_span']);octaves=octave_links(ir,out['analysis_span']);links_at=defaultdict(list)
    for link in voices['links']+octaves['links']:
        if f(link['source_span']['end'])==f(link['target_span']['start']):links_at[f(link['target_span']['start'])].append(link)
    for r in records:
        by_start[f(r['span']['start'])].append(r)
        r['double_neighbor_evidence']=double_neighbors(ir,r)
        for c in r['candidates']:
            c['context_evidence']={'bass':bass_evidence(r,c),'following_edge_refs':[],'preceding_edge_refs':[]}
    edges=[];skipped=Counter()
    for left in records:
        boundary=f(left['span']['end'])
        for right in by_start[boundary]:
            blockers=sorted(set(left['abstention_reasons']+right['abstention_reasons']))
            # A meter/repeat change exactly at the join is not inside either window.
            for m in ir['measures']:
                start=f(m['global_start_quarter']);end=start+f(m['actual_duration_quarter']);bar=m.get('repeat_barline') or {}
                point=start if bar.get('location')=='left' else end
                if point==boundary and any(bar.get(k) for k in ('repeat_direction','ending_number')):blockers.append('repeat_at_join')
            before=[m for m in ir['measures'] if f(m['global_start_quarter'])<boundary]
            after=[m for m in ir['measures'] if f(m['global_start_quarter'])<=boundary]
            if before and after and max(before,key=lambda m:f(m['global_start_quarter']))['time_signature']!=max(after,key=lambda m:f(m['global_start_quarter']))['time_signature']:blockers.append('meter_change_at_join')
            if blockers:skipped['blocked_window_pairs']+=1;continue
            links=[l for l in links_at[boundary] if l['source_refs'][0] in left['event_refs'] and l['source_refs'][1] in right['event_refs']]
            for source in left['candidates']:
                for target in right['candidates']:
                    kind=root_relation(source,target)
                    if kind is None:continue
                    supports=[]
                    for link in links:
                        tags=direct_relations(link,source,target)
                        if tags:supports.append({'source_refs':link['source_refs'],'relations':tags,'source_pitch':link['source_pitch']['spelling'],'target_pitch':link['target_pitch']['spelling'],
                            'part_id':link['part_id'],'voice_id':link['voice_id'],
                            'link_status':link['status'],'dependency_group':link.get('dependency_group')})
                    eid='ctx_'+token([source['candidate_id'],target['candidate_id']])
                    edge={'edge_id':eid,'source_candidate_ref':source['candidate_id'],'target_candidate_ref':target['candidate_id'],
                        'source_window_ref':left['window_id'],'target_window_ref':right['window_id'],'boundary':left['span']['end'],
                        'source_label':source['label'],'target_label':target['label'],'source_span':left['span'],'target_span':right['span'],
                        'root_relation':kind,'direct_voice_support':supports,'evidence_status':'root_relation_plus_direct_voice' if supports else 'root_relation_only',
                        'source_residual_count':len(source['residual_event_refs']),'target_residual_count':len(target['residual_event_refs']),
                        'source_missing_pcs':source['missing_member_pcs'],'target_missing_pcs':target['missing_member_pcs'],
                        'applied_function_confirmed':False,'cadence_confirmed':False,'lack_of_direct_support_is_counterevidence':False,
                        'selected':None}
                    edges.append(edge);source['context_evidence']['following_edge_refs'].append(eid);target['context_evidence']['preceding_edge_refs'].append(eid)
    out['context_version']=VERSION;out['context_edges']=edges;out['voice_observations']=voices;out['octave_observations']=octaves
    unique={(tuple(s['source_refs']),tag) for e in edges for s in e['direct_voice_support'] for tag in s['relations']}
    out['context_summary']={'candidate_edges':len(edges),'with_direct_support':sum(bool(e['direct_voice_support']) for e in edges),
        'unique_voice_pair_relation_units':len(unique),'skipped':dict(skipped),'edge_counts_are_independent_votes':False,
        'octave_links':len(octaves['links']),'octave_dependency_groups':len({l['dependency_group'] for l in octaves['links']}),
        'double_neighbor_geometry_occurrences':sum(len(r['double_neighbor_evidence']['records']) for r in records),
        'conditional_double_neighbor_occurrences':sum(r['double_neighbor_evidence']['conditional_count'] for r in records),
        'incomplete_double_neighbor_occurrences':sum(any(e['status']=='incomplete_double_neighbor_hypothesis' for e in figure['candidate_explanations']) for r in records for figure in r['double_neighbor_evidence']['records'])}
    out['context_limits']=['Root relations are relative to candidate targets, not V/V or local key confirmation.',
        'Adjacent exact windows only; equal-count synchronized pure octaves allow conditional step links; other polyphony remains deferred.',
        'No pruning, cost change, confidence, automatic selection, or source-label input.',
        'Onset acoustic factor proposes an inversion, not a confirmed structural bass.']
    return out
