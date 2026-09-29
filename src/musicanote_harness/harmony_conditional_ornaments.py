"""Path-conditioned contiguous melodic figures. Never labels or deletes NCTs."""
from collections import defaultdict, Counter
from .harmony_joint import f
from .counterpoint_evidence import melodic_geometry
from .harmony_reading_voice_context import spelled_height
from .harmony_path_contrast import token

VERSION = 'path-conditioned-ornaments-0.1.0'


def assess(ir, explanation):
    notes={n['note_id']:n for n in ir['note_events']}
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']}
    x,y=(f(explanation['comparison_span'][k]) for k in ('start','end'))
    lanes=defaultdict(list);skipped=Counter();records=[]
    for s in sounds.values():
        if f(s['span']['start'])>=y or f(s['span']['end'])<=x:continue
        ns=[notes.get(i) for i in s['source_note_ids']]
        ids={(n.get('part_id'),n.get('voice_id')) for n in ns if n}
        if not ns or not all(ns) or len(ids)!=1 or not all(next(iter(ids))):
            skipped['missing_or_cross_lane_identity']+=1;continue
        if any(n.get('grace',{}).get('is_grace') for n in ns):
            skipped['grace_sound']+=1;continue
        lanes[next(iter(ids))].append(s)
    for lane,ss in sorted(lanes.items()):
        ss.sort(key=lambda s:(f(s['span']['start']),s['sounding_event_id']))
        for triple in zip(ss,ss[1:],ss[2:]):
            a,m,b=triple;refs=[s['sounding_event_id'] for s in triple]
            if f(a['span']['start'])<x or f(b['span']['end'])>y:
                skipped['full_triple_outside_context']+=1;continue
            if any(f(s['span']['end'])<=f(s['span']['start']) or spelled_height(s['pitch']) is None for s in triple):
                skipped['unsupported_pitch_or_duration']+=1;continue
            if f(a['span']['end'])!=f(m['span']['start']) or f(m['span']['end'])!=f(b['span']['start']):
                skipped['gap_or_overlap']+=1;continue
            if any(o['sounding_event_id']!=s['sounding_event_id'] and f(o['span']['start'])<f(s['span']['end']) and f(o['span']['end'])>f(s['span']['start']) for s in triple for o in ss):
                skipped['polyphonic_lane']+=1;continue
            geometry=melodic_geometry([(s['pitch']['step'],int(f(s['pitch']['alter'])),s['pitch']['octave']) for s in triple])
            if not geometry['pattern']:skipped['other_geometry']+=1;continue
            path_results=[]
            for path in explanation['paths']:
                cells=[(c,e) for c,e in zip(explanation['cells'],path['cells']) if f(c['span']['start'])<f(b['span']['end']) and f(c['span']['end'])>f(a['span']['start'])]
                shapes={(e['candidate']['root'],e['candidate']['label'],tuple(e['candidate']['pcs'])) for _,e in cells}
                states=[set(e['states'][sid] for _,e in cells if sid in e['states']) for sid in refs]
                base={'path_ref':path['path_ref'],'event_states':[sorted(v) for v in states],
                      'uses_edge_extension_assumption':any(e['outside_extension_assumption'] for _,e in cells),
                      'conditional_role':None,'confirmed_nct':False,'remove_note':False}
                if explanation['abstention_reasons']:status='context_unresolved'
                elif len(shapes)!=1:status='crosses_candidate_chord_change'
                elif states==[{'member'},{'nonmember_not_confirmed_nct'},{'member'}]:
                    status='conditional_ornament_compatible';base['conditional_role']=geometry['pattern'].replace('_geometry','')
                elif all(v=={'member'} for v in states):status='all_three_are_candidate_members'
                else:status='membership_or_spelling_not_sufficient'
                path_results.append({**base,'status':status})
            has_ornament=any(p['status']=='conditional_ornament_compatible' for p in path_results)
            records.append({'evidence_id':'orn_'+token([explanation['candidate_ref'],refs]),'event_refs':refs,'middle_ref':refs[1],
                'part_id':lane[0],'voice_id':lane[1],'span':{'start':a['span']['start'],'end':b['span']['end']},
                'geometry':geometry['pattern'],'path_explanations':path_results,
                'competing_member_explanation':has_ornament and any(p['status']=='all_three_are_candidate_members' for p in path_results),
                'selected':None,'used_for_ranking':False})
    return {'version':VERSION,'candidate_ref':explanation['candidate_ref'],'records':records,'skipped':dict(skipped),
        'summary':{'geometry_triples':len(records),'conditional_ornament_triples':sum(any(p['status']=='conditional_ornament_compatible' for p in r['path_explanations']) for r in records),
            'competing_member_triples':sum(r['competing_member_explanation'] for r in records)},
        'production_modified':False,'source_annotation_used':False,
        'limits':['One explicit monophonic lane; contiguous triples only; no inner-voice guessing.',
            'Same harmonic candidate must cover the entire triple. Rest/chord change cannot be skipped.',
            'No accent/duration threshold: geometry compatibility is not an NCT probability.',
            'Suspension, pedal and decorated/nonadjacent resolution remain unconfirmed.',
            'Do not sum overlapping triples as independent support or select a chord by ornament count.']}
