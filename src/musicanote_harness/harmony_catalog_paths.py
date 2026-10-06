"""Candidate-conditioned explanations of entire delayed arrival paths.

An arrival figure never proves a voice connection across its preceding rest.
Source hold, target arrival and local chord alternatives remain separate.
"""
from copy import deepcopy
from .formal_ir import q
from .harmony_joint import f
from .harmony_path_contrast import token
from .harmony_catalog_microtime import enrich
from .harmony_candidate_catalog import propose
from .harmony_catalog_resolution import pitch_pair
from .harmony_reading_voice_context import spelled_height
from .harmony_intervening_paths import assess as paths

VERSION = 'catalog-arrival-paths-0.1.0'


def condition(path, candidate, alternative_index, hypothesis):
    """One coherent spelling hypothesis; no pitch-class or endpoint shortcut."""
    events = {s['event_ref']: s for s in path['events']}
    arrivals = [events[sid] for sid in path['arrival_event_refs']]
    members = candidate['spelling_alternatives'][alternative_index]['members']
    x,y = (f(candidate['span'][k]) for k in ('start','end'))
    states = {}
    for s in arrivals:
        states[s['event_ref']] = ('spelling_unresolved' if spelled_height(s['pitch']) is None
            else 'member' if pitch_pair(s['pitch']) in members else 'nonmember_not_confirmed_nct')
    covered = bool(arrivals) and all(x <= f(s['span']['start']) and f(s['span']['end']) <= y for s in arrivals)
    extension = not covered
    blockers = sorted(set(path['abstention_reasons']) | set(candidate['abstention_reasons']))
    if extension and hypothesis != 'source_hold_counterfactual':
        blockers.append('arrival_not_covered_by_candidate')
    if 'spelling_unresolved' in states.values():blockers.append('spelling_unresolved')
    tags, ornaments = [], []
    if not blockers and arrivals:
        if len(arrivals)>=3 and not path['arrival_gaps'] and all(v=='member' for v in states.values()) \
                and len({tuple(pitch_pair(s['pitch'])) for s in arrivals})>=3:
            tags.append('chord_member_unfolding_compatible')
        for g in path['arrival_geometry']:
            a,m,b = g['event_refs']
            if g['pattern'] and [states[sid] for sid in (a,m,b)]==['member','nonmember_not_confirmed_nct','member']:
                ornaments.append({'event_refs':g['event_refs'],'middle_ref':m,
                    'conditional_role':g['pattern'].replace('_geometry','_candidate'),
                    'nct_confirmed':False,'remove_note':False})
        if ornaments:tags.append('local_ornament_geometry_compatible')
    return {'candidate_ref':candidate['candidate_id'],'alternative_index':alternative_index,
        'origin_pointer':candidate['origin_pointer'],'provider':candidate['provider'],
        'hypothesis':hypothesis,'candidate_span':candidate['span'],'arrival_covered':covered,
        'outside_candidate_span':extension,
        'outside_extension_assumption':extension and hypothesis=='source_hold_counterfactual','event_states':states,
        'compatible_patterns':tags,'conditional_ornaments':ornaments,
        'unexplained_nonmember_refs':[sid for sid,s in states.items() if s=='nonmember_not_confirmed_nct'
            and sid not in {o['middle_ref'] for o in ornaments}],
        'abstention_reasons':blockers,'status':'context_unresolved' if blockers else 'conditional_explanation_only',
        'selected':None,'used_for_ranking':False}


def local_alternatives(ir, path, span):
    """All onset/release cells in arrival segment, across all parts; no winner."""
    if not path['arrival_event_refs']:return []
    events={s['event_ref']:s for s in path['events']}
    start=f(events[path['arrival_event_refs'][0]]['span']['start'])
    stop=f(path['span']['end'])
    if start<f(span['start']) or stop>f(span['end']):return []
    points={start,stop}
    for s in ir['sounding_events']:
        points.update(f(s['span'][k]) for k in ('start','end') if start<f(s['span'][k])<stop)
    return [propose(ir,{'start':q(a),'end':q(b)}) for a,b in zip(sorted(points),sorted(points)[1:])]


def analyze(ir,left,right):
    result=enrich(ir,left,right)
    wanted={(h['group_id'],tuple(h['source_refs'])) for e in result['edges'] for h in e['delayed_endpoint_hypotheses']}
    audit=deepcopy(result['delayed_counterevidence'])
    audit['records']=[r for r in audit['records'] if (r['group_id'],tuple(r['source_refs'])) in wanted]
    observed=paths(ir,result['delayed_observation'],audit,[],[result['span']])
    bykey={(p['group_id'],tuple(p['source_refs'])):p for p in observed['records']}
    candidates=[{c['candidate_id']:c for c in cat['candidates']} for cat in (left,right)]
    records={};catalogs={}
    for edge in result['edges']:
        edge['arrival_path_refs']=[]
        for link in edge['delayed_endpoint_hypotheses']:
            key=(link['group_id'],tuple(link['source_refs']));path=bykey[key]
            if not path['all_intervening_refs_preserved']:raise ValueError('intervening_note_loss')
            pid=path['path_id']
            if pid not in records:
                records[pid]={'observation':path,'conditions':[],'alternative_cell_catalog_refs':[],
                             'local_cells_prove_change':False,'selected':None}
                for cat in local_alternatives(ir,path,result['span']):
                    wid=cat['providers']['base']['window_id'];catalogs[wid]=cat
                    records[pid]['alternative_cell_catalog_refs'].append(wid)
            for side,hyp in (('source','source_hold_counterfactual'),('target','target_arrival_hypothesis')):
                c=candidates[0 if side=='source' else 1][edge[side+'_candidate_ref']]
                alt=edge[side+'_alternative_index']
                cid='pcond_'+token([pid,c['candidate_id'],alt,hyp])
                entry=next((c for c in records[pid]['conditions'] if c['condition_id']==cid),None)
                if entry is None:
                    entry={'condition_id':cid,**condition(path,c,alt,hyp),'edge_refs':[]}
                    records[pid]['conditions'].append(entry)
                if edge['edge_id'] not in entry['edge_refs']:entry['edge_refs'].append(edge['edge_id'])
            edge['arrival_path_refs'].append(pid)
    result['arrival_path_assessment']={'version':VERSION,'paths':records,'local_catalogs':catalogs,
        'selection':'paths of existing delayed endpoint hypotheses only; not all melodic figures',
        'direct_status_changed':False,'source_labels_used':False,
        'limits':['Source hold beyond original span is an explicit counterfactual, never a retroactive fact.',
            'Local cell candidates preserve residuals/missing tones; their existence does not prove change.',
            'Path geometry remains blocked by polyphony, missing context, grace, meter or repeat uncertainty.',
            'No deletion, ranking, NCT truth, selected harmony or voice connection.']}
    return deepcopy(result)
