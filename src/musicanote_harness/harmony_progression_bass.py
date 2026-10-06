"""Conditional inversion and sustained-bass-role evidence; never picks a chord."""
from copy import deepcopy
from .harmony_joint import f
from .harmony_catalog_resolution import pitch_pair
from .harmony_reading_voice_context import spelled_height, LETTERS
from .harmony_progression_evidence import vector

VERSION = 'progression-bass-0.1.0'


def degree(root, member):
    return (LETTERS.index(member[0])-LETTERS.index(root[0])) % 7 + 1


def cell_role(reading, lowest, events):
    root=reading.get('root_spelling'); members={tuple(m) for m in reading['members']}
    out={'root_spelling':deepcopy(root),'root_provenance':reading.get('root_provenance'),
         'bass_event_refs':deepcopy(lowest['event_refs']), 'inversion_candidate':None,
         'inversion_confirmed':False,'structural_bass_confirmed':False}
    if lowest['status']!='observed_lowest':
        return {**out,'status':lowest['status']}
    refs=lowest['event_refs']
    if any(spelled_height(events[sid]['pitch']) is None for sid in refs):
        return {**out,'status':'bass_spelling_unresolved'}
    pairs={tuple(pitch_pair(events[sid]['pitch'])) for sid in refs}
    out['bass_spellings']=[list(p) for p in sorted(pairs)]
    if len(pairs)!=1:
        return {**out,'status':'enharmonic_bass_conflict'}
    bass=next(iter(pairs))
    if bass not in members:
        return {**out,'status':'nonmember_bass_role_unresolved',
                'alternatives':['ornamental_bass','pedal_role','different_chord_hypothesis']}
    if root is None:
        return {**out,'status':'root_unavailable'}
    if tuple(root) not in members:
        return {**out,'status':'root_membership_contract_conflict'}
    degrees=[degree(root,m) for m in members]
    out['bass_degree_from_assumed_root']=degree(root,bass)
    if len(degrees)!=len(set(degrees)) or set(degrees) not in ({1,3,5},{1,3,5,7}):
        return {**out,'status':'nonstandard_or_extended_inversion_deferred'}
    if reading['abstention_reasons']:
        return {**out,'status':'candidate_blocked','blockers':deepcopy(reading['abstention_reasons'])}
    index={1:0,3:1,5:2,7:3}[degree(root,bass)]
    return {**out,'status':'conditional_on_chord_and_bass_role',
            'inversion_candidate':index,
            'withheld_reasons':['observed_lowest_not_yet_validated_as_structural_bass']}


def analyze(result,path,assignment_ref,evaluation_span=None):
    # Pedal geometry needs complete context, even when the requested display is shorter.
    full=vector(result,path,assignment_ref)
    target=vector(result,path,assignment_ref,evaluation_span) if evaluation_span else full
    events={s['sounding_event_id']:s for s in result['events']}
    readings=[result['edges'][c['edge']]['readings'][c['reading']] for c in path]
    roles=[]
    for cell in target['cells']:
        r=next(r for r in readings if f(r['span']['start'])<=f(cell['span']['start'])
               and f(cell['span']['end'])<=f(r['span']['end']))
        roles.append({'span':deepcopy(cell['span']),'candidate_ref':r['candidate_ref'],
                      'alternative_index':r['alternative_index'],
                      **cell_role(r,cell['lowest'],events)})
    pedal=[]
    for sid,s in sorted(events.items()):
        if f(s['span']['start'])>=f(target['evaluation_span']['end']) or f(s['span']['end'])<=f(target['evaluation_span']['start']):continue
        cells=[c for c in full['cells'] if sid in c['event_refs']]
        if not cells or not all(sid in c['lowest']['event_refs'] for c in cells):continue
        involved=[r for r in readings if f(r['span']['start'])<f(s['span']['end']) and f(r['span']['end'])>f(s['span']['start'])]
        if len({tuple(sorted(tuple(m) for m in r['members'])) for r in involved})<2:continue
        states=[c['membership'][sid] for c in cells]
        if 'nonmember' not in states:continue
        complete=f(full['context_span']['start'])<=f(s['span']['start']) and f(s['span']['end'])<=f(full['context_span']['end'])
        anchored=complete and states[0]==states[-1]=='member'
        blocked=sorted({b for r in involved for b in r['abstention_reasons']})
        pedal.append({'event_ref':sid,'sounding_span':deepcopy(s['span']),
            'membership_sequence':states,'complete_sound_in_context':complete,
            'both_ends_are_members':anchored,'candidate_blockers':blocked,
            'status':'anchored_sustained_bass_shape' if anchored and not blocked else 'sustained_bass_role_unresolved',
            'pedal_confirmed':False,'sustain_pedal_inferred':False,
            'alternatives':['pedal_role','suspension_or_other_ornament','incorrect_chord_path'],
            'withheld_reasons':['upper_voice_harmonic_function_not_validated','requires_competing_path_comparison']})
    return {'version':VERSION,'evidence':target,'bass_roles':roles,'sustained_bass_candidates':pedal,
            'selected':None,'production_modified':False,
            'limits':['Only continuous sounding-event bass shapes; repeated attacks and inner/upper pedals deferred.',
                      'Root from provider alternative, never display label; missing legacy roots stay unknown.']}
