"""Repeated lowest-note geometry and same-interval competing readings.

Not a pedal classifier: no pitches are exempted, no harmony is selected.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from .formal_ir import q
from .harmony_joint import f
from .harmony_catalog_resolution import pitch_pair
from .harmony_reading_voice_context import spelled_height
from .harmony_distributed_resolution import profile
from .harmony_missing_evidence import validate_ir, overlap

VERSION='repeated-bass-comparison-0.1.0'


def chains(lattice, ir):
    events={s['sounding_event_id']:s for s in lattice['events']}
    notes={n['note_id']:n for n in ir['note_events']}
    if len(notes)!=len(ir['note_events']):raise ValueError('duplicate_note_id')
    span=lattice['plan']['context_span']; eligible={}; withheld={}
    # Compute from actual sound spans, not from cached cells or instrument names.
    points=sorted({f(span['start']),f(span['end'])} | {
        f(s['span'][k]) for s in events.values() for k in ('start','end')
        if f(span['start'])<f(s['span'][k])<f(span['end'])})
    for sid,s in events.items():
        if f(s['span']['end'])<=f(s['span']['start']):withheld[sid]='nonpositive_timing';continue
        ns=[notes.get(n) for n in s['source_note_ids']]
        lanes={(n.get('part_id'),n.get('voice_id')) for n in ns if n}
        if not ns or not all(ns) or len(lanes)!=1 or not all(next(iter(lanes))):
            withheld[sid]='lane_unresolved';continue
        if spelled_height(s['pitch']) is None:withheld[sid]='pitch_unresolved';continue
        lowest=True
        for a,b in zip(points,points[1:]):
            if not f(s['span']['start'])<b or not f(s['span']['end'])>a:continue
            active=[e for e in events.values() if f(e['span']['start'])<b and f(e['span']['end'])>a]
            if any(spelled_height(e['pitch']) is None for e in active):
                withheld[sid]='coincident_pitch_unresolved';lowest=False;break
            if any(e['pitch']['midi_pitch']<s['pitch']['midi_pitch'] for e in active):lowest=False;break
        if lowest:eligible[sid]=next(iter(lanes))
    outgoing=defaultdict(list);incoming=defaultdict(list)
    for x in eligible:
        for y in eligible:
            a,b=events[x],events[y]
            if (eligible[x]==eligible[y] and f(a['span']['end'])==f(b['span']['start'])
                    and pitch_pair(a['pitch'])==pitch_pair(b['pitch'])
                    and a['pitch']['midi_pitch']==b['pitch']['midi_pitch']):
                outgoing[x].append(y);incoming[y].append(x)
    links={x:ys[0] for x,ys in outgoing.items() if len(ys)==1 and len(incoming[ys[0]])==1}
    tails=set(links.values());result=[]
    for sid in sorted(set(eligible)-tails, key=lambda s:(f(events[s]['span']['start']),s)):
        chain=[sid]
        while chain[-1] in links:chain.append(links[chain[-1]])
        if len(chain)<2:continue
        full={'start':deepcopy(events[chain[0]]['span']['start']),'end':deepcopy(events[chain[-1]]['span']['end'])}
        result.append({'chain_id':'repeated-bass:'+chain[0], 'event_refs':chain,
            'lane':list(eligible[sid]),'pitch':deepcopy(events[sid]['pitch']),'sounding_span':full,
            'observed_span':{'start':q(max(f(full['start']),f(span['start']))),'end':q(min(f(full['end']),f(span['end'])))},
            'touches_context_start':f(full['start'])<=f(span['start']),
            'touches_context_end':f(full['end'])>=f(span['end']),
            'complete_repetition_extent_known':False,'pedal_confirmed':False,'voice_identity_confirmed':False})
    return {'chains':result,'withheld_events':withheld,
            'ambiguous_links':[{'source':x,'destinations':ys} for x,ys in outgoing.items()
                               if len(ys)!=1 or len(incoming[ys[0]])!=1]}


def compare_interval(lattice, edge_index, chain):
    edge=lattice['edges'][edge_index]; events={s['sounding_event_id']:s for s in lattice['events']}
    pitch=pitch_pair(chain['pitch']); rows=[]
    for index,reading in enumerate(edge['readings']):
        observed=profile(events,reading)
        rows.append({'reading_index':index,'candidate_ref':reading['candidate_ref'],
            'alternative_index':reading['alternative_index'],'root_spelling':deepcopy(reading.get('root_spelling')),
            'members':deepcopy(reading['members']),'bass_is_member':pitch in reading['members'],
            'missing_members':observed['missing_members'],'nonmember_event_refs':observed['unexplained_event_refs'],
            'nonmember_bass_refs':[sid for sid in observed['unexplained_event_refs'] if sid in chain['event_refs']],
            'other_nonmember_refs':[sid for sid in observed['unexplained_event_refs'] if sid not in chain['event_refs']],
            'candidate_blockers':deepcopy(reading['abstention_reasons'])})
    return {'edge_index':edge_index,'span':deepcopy(edge['span']),'chain_ref':chain['chain_id'],
            'readings':rows,'bass_member_reading_indices':[r['reading_index'] for r in rows if r['bass_is_member']],
            'winner':None,'pedal_confirmed':False,'comparison_uses_same_events_and_interval':True}


def run(lattice, survey, ir):
    out={'version':VERSION,'status':survey['status'],'selected':None,'gate_changed':False,
         'production_modified':False,'accuracy_measured':False,'pair_results':[],'interval_comparisons':{}}
    if survey['status']!='ready':return out
    validate_ir(lattice,ir)
    geometry=chains(lattice,ir);out['geometry']=geometry;counts=Counter()
    counts['repeated_lowest_chains']=len(geometry['chains'])
    if len(survey['results'])!=len(survey['plan']['pairs']):raise ValueError('incomplete_survey')
    for pair,item in zip(survey['plan']['pairs'],survey['results']):
        if pair!=item['pair']:raise ValueError('pair_plan_mismatch')
        findings=[]
        for chain in geometry['chains']:
            sides={}
            for side in ('source','target'):
                choice=pair[side];edge=lattice['edges'][choice['edge']]
                if not overlap(edge['span'],chain['observed_span']):continue
                reading=edge['readings'][choice['reading']]
                if (reading['candidate_ref']!=item[side+'_candidate_ref'] or
                    reading['alternative_index']!=item[side+'_alternative_index']):raise ValueError('candidate_origin_mismatch')
                key=str(choice['edge'])+'|'+chain['chain_id']
                if key not in out['interval_comparisons']:
                    out['interval_comparisons'][key]=compare_interval(lattice,choice['edge'],chain)
                table=out['interval_comparisons'][key];baseline=table['readings'][choice['reading']]
                sides[side]={'comparison_ref':key,'original_reading_index':choice['reading'],
                             'bass_is_member':baseline['bass_is_member']}
                if not baseline['bass_is_member']:
                    counts['nonmember_bass_side_instances']+=1
                    if table['bass_member_reading_indices']:counts['with_bass_member_competitor']+=1
            if not sides:continue
            states=[sides[s]['bass_is_member'] for s in ('source','target') if s in sides]
            findings.append({'chain_ref':chain['chain_id'],'sides':sides,'membership_sequence':states,
                'pedal_confirmed':False,'bass_exempted':False,
                'return_anchor_verified':False,'harmonic_path_selected':False})
        if findings:counts['pairs_with_repeated_bass']+=1
        out['pair_results'].append({'pair':deepcopy(pair),'original_status':item['status'],'findings':findings})
    out.update(summary=dict(counts),limits=[
        'Unique same-lane touching same-spelled-pitch reattacks, lowest throughout each observed sound.',
        'No rest bridging, octave substitution, ambiguous unison selection, inner/upper pedal detection.',
        'Two candidate intervals cannot establish a member-nonmember-member return anchor.',
        'All same-interval competitors including blocked candidates preserved; no ranking or exemption.',
        'Repeated lowest sound is neither structural bass nor pedal proof; complete pattern extent is unknown.'])
    return out
