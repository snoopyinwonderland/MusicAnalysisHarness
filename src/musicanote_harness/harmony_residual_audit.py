"""Explain residuals under a frozen chord pair without erasing competing readings."""
from .harmony_joint import f
from .harmony_open_candidates import window
from .harmony_voice_figures import double_neighbors
from .harmony_reading_voice_context import voice_links

VERSION='conditional-residual-audit-0.1.0'


def audit_pair(ir, left, right, source, target, cache=None):
    if left['span']['end']!=right['span']['start']:
        raise ValueError('nonadjacent_windows')
    cache={} if cache is None else cache
    boundary=f(right['span']['start'])
    whole={'start':left['span']['start'],'end':right['span']['end']}
    links=voice_links(ir,whole)
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']}
    common_blocks=sorted(set(left['abstention_reasons']+right['abstention_reasons']))
    # A join may itself be a repeat/meter barrier although each side is clear.
    key=('whole',str(whole))
    if key not in cache:cache[key]=window(ir,whole)
    common_blocks=sorted(set(common_blocks+cache[key]['abstention_reasons']))
    explanations={};sides=[]
    def add(sid,kind,refs,assumptions):
        explanations.setdefault(sid,[]).append({'kind':kind,'event_refs':refs,
            'assumptions':assumptions,'confirmed_nct':False,'remove_note':False})
    for side,w,c in [('before',left,source),('after',right,target)]:
        for r in w['conditional_figures']['records']:
            e=next(e for e in r['path_explanations'] if e['path_ref']==c['candidate_id'])
            if e['conditional_role'] and not common_blocks:
                add(r['middle_ref'],e['conditional_role'],r['event_refs'],['fixed_harmony_through_complete_figure'])
        key=('double',w['window_id'])
        if key not in cache:cache[key]=double_neighbors(ir,w)
        for r in cache[key]['records']:
            e=next(e for e in r['candidate_explanations'] if e['candidate_ref']==c['candidate_id'])
            if e['status']=='conditional_double_neighbor_compatible' and not common_blocks:
                for sid in r['neighbor_refs']:add(sid,'double_neighbor',r['event_refs'],['fixed_harmony_through_complete_figure'])
    if not common_blocks:
        for link in links['links']:
            x,y=link['source_refs']
            # Literal same-spelled reattack across the candidate chord boundary.
            if (f(link['source_span']['end'])==boundary==f(link['target_span']['start'])
                and link['semitones']==0 and link['diatonic_steps']==0
                and source['event_states'].get(x)=='nonmember_not_confirmed_nct'
                and target['event_states'].get(y)=='member'):
                add(x,'anticipation_reattack_compatible',[x,y],
                    ['asserted_chord_change','same_spelled_pitch_reattack','accent_and_function_unconfirmed'])
            # True sounding continuity, not two notes guessed to be tied.
            s=sounds[x]
            if (f(s['span']['start'])<boundary<f(s['span']['end'])
                and f(link['target_span']['start'])<f(right['span']['end'])
                and source['event_states'].get(x)=='member'
                and target['event_states'].get(x)=='nonmember_not_confirmed_nct'
                and target['event_states'].get(y)=='member'
                and link['semitones'] in (-1,-2) and link['diatonic_steps']==-1):
                add(x,'prepared_suspension_geometry',[x,y],
                    ['asserted_chord_change','prepared_member_held_across_change','accent_unconfirmed'])
    for side,w,c in [('before',left,source),('after',right,target)]:
        residuals=[]
        for sid in c['residual_event_refs']:
            alternatives=[]
            for cell in w['cells']:
                if sid not in cell['event_refs']:continue
                key=('cell',str(cell['span']))
                if key not in cache:cache[key]=window(ir,cell['span'])
                local=cache[key]
                for candidate in local['candidates']:
                    if candidate['event_states'].get(sid)=='member':
                        alternatives.append({'span':cell['span'],'candidate_ref':candidate['candidate_id'],
                            'label':candidate['label'],'missing_member_pcs':candidate['missing_member_pcs'],
                            'residual_event_refs':candidate['residual_event_refs'],
                            'abstention_reasons':local['abstention_reasons'],
                            'status':'local_membership_only_not_confirmed_change'})
            e=explanations.get(sid,[])
            residuals.append({'event_ref':sid,'pitch':sounds[sid]['pitch'],'source_note_ids':sounds[sid]['source_note_ids'],
                'original_span':sounds[sid]['span'],'conditional_nct_explanations':e,
                'finer_cell_alternatives':alternatives,
                'status':'conditional_nct_explanation_available' if e else 'unresolved',
                'all_alternatives_remain_open':True})
        sides.append({'side':side,'candidate_ref':c['candidate_id'],'label':c['label'],'span':w['span'],
            'residuals':residuals,'unresolved_count':sum(not r['conditional_nct_explanations'] for r in residuals),
            'spelling_unresolved_refs':[sid for sid,state in c['event_states'].items() if state=='spelling_unresolved']})
    return {'version':VERSION,'source_label':source['label'],'target_label':target['label'],
        'boundary':right['span']['start'],'sides':sides,'abstention_reasons':common_blocks,
        'voice_abstentions':links['abstentions'],'selected':None,'used_for_ranking':False,
        'limits':['A conditional NCT explanation does not erase a residual or select a chord.',
                  'Local cell membership may have missing members and other residuals; it does not prove another chord.',
                  'Accent, local key, appoggiatura, escape tone, pedal and decorated resolutions remain unconfirmed.',
                  'Anticipation reattack and true sounding suspension are distinct hypotheses.',
                  'Complete neighbor preparation required; no cross-rest or polyphonic nearest-pitch guess.']}
