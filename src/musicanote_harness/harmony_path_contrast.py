"""Compare frozen chord conditions on the SAME all-voice arrival window.

Membership differences are review evidence, not harmonic truth or votes.
An absent exclusive pitch never proves an omitted chord member impossible.
"""
from collections import Counter
from fractions import Fraction
from itertools import combinations
import hashlib
import json

from .formal_ir import q
from .harmony_joint import f
from .harmony_reading_voice_context import spelled_height

VERSION = 'all-voice-path-contrast-0.1.0'


def token(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]


def compare(ir, paths):
    sounds = {s['sounding_event_id']: s for s in ir['sounding_events']}
    notes = {n['note_id']: n for n in ir['note_events']}
    units = {}; records = []
    for path in paths['records']:
        arrivals = [sounds[i] for i in path['arrival_event_refs']]
        if not arrivals:
            records.append({'path_id': path['path_id'], 'status': 'no_arrival_events', 'pairs': []})
            continue
        a = min(f(s['span']['start']) for s in arrivals)
        b = max(f(s['span']['end']) for s in arrivals)
        span = {'start': q(a), 'end': q(b)}
        # Retain ALL parts/voices, including held sounds and both endpoints.
        active = sorted((s for s in sounds.values() if f(s['span']['start']) < b and f(s['span']['end']) > a), key=lambda s:s['sounding_event_id'])
        active_ids = {s['sounding_event_id'] for s in active}
        facts = []; occupancy = {}
        for s in active:
            x,y = max(a,f(s['span']['start'])),min(b,f(s['span']['end']))
            uid = 'psound_'+token(s['sounding_event_id'])
            units[uid] = {'event_ref': s['sounding_event_id'], 'source_note_ids': s['source_note_ids'],
                          'pitch': s['pitch'], 'original_span': s['span'], 'independent_vote': False}
            facts.append({'unit_ref': uid, 'event_ref': s['sounding_event_id'], 'overlap_span': {'start':q(x),'end':q(y)},
                'held_at_start': f(s['span']['start']) < a, 'attacked_in_window': a <= f(s['span']['start']) < b,
                'in_arrival_lane_path': s['sounding_event_id'] in path['arrival_event_refs']})
            occupancy.setdefault(s['pitch']['midi_pitch']%12,[]).append((x,y))
        # Union occupancy avoids inflating duration for unison/octave doubling.
        pc_durations = {}
        for pc, intervals in occupancy.items():
            end = a; total = Fraction(0)
            for x,y in sorted(intervals):
                total += max(Fraction(0), y-max(end,x)); end = max(end,y)
            pc_durations[str(pc)] = q(total)
        conditions = {}; excluded = []
        for e in path['conditional_explanations']:
            c = e['candidate']; key = token([c['root'],c['label'].partition(':')[2],sorted(c['pcs'])])
            if not (f(e['span']['start']) <= a and b <= f(e['span']['end'])):
                excluded.append({'candidate_key':key,'span':e['span'],'reason':'does_not_cover_same_window'})
                continue
            cond = conditions.setdefault(key, {'candidate_key':key,'candidate':c,'conditions':[],
                'root_spelling_support':{},'pattern_signatures':{}})
            provenance={'span':e['span'],'provenance':e['provenance'],'status':e['status']}
            if provenance not in cond['conditions']:cond['conditions'].append(provenance)
            for root in e['spelling_evidence']['candidates']:
                arrival_members={s['sounding_event_id'] for s in arrivals if s['pitch']['midi_pitch']%12 in c['pcs']}
                if root['root_spelling'] in e['coherent_root_spellings'] and arrival_members <= set(root['supported_event_refs']):
                    cond['root_spelling_support'].setdefault(root['root_spelling'],set()).update(set(root['supported_event_refs']) & active_ids)
            # A broad tag alone is insufficient: compare the same underlying notes.
            if 'chord_member_unfolding_compatible' in e['compatible_patterns']:
                ids = path['arrival_event_refs']; sig='pattern_'+token(['unfolding',ids])
                cond['pattern_signatures'][sig]={'type':'unfolding','event_refs':ids}
            for o in e['conditional_ornaments']:
                sig='pattern_'+token([o['conditional_role'],o['event_refs']])
                cond['pattern_signatures'][sig]={'type':o['conditional_role'],'event_refs':o['event_refs']}
        for cond in conditions.values():
            support=cond['root_spelling_support']
            cond['root_spelling_support']={r:sorted(ids) for r,ids in sorted(support.items())}
            all_members={s['sounding_event_id'] for s in active if s['pitch']['midi_pitch']%12 in cond['candidate']['pcs']}
            cond['all_member_spelling_consistent']=bool(support) and any(all_members<=ids for ids in support.values())
            cond['event_membership']={}
            for s in active:
                sid=s['sounding_event_id']; pc=s['pitch']['midi_pitch']%12
                if spelled_height(s['pitch']) is None:state='unsupported_pitch'
                elif pc not in cond['candidate']['pcs']:state='nonmember_not_confirmed_nct'
                elif any(sid in ids for ids in support.values()):state='member_under_spelling_hypothesis'
                else:state='pc_member_spelling_unresolved'
                cond['event_membership'][sid]=state
            cond['unobserved_member_pcs']=sorted(set(cond['candidate']['pcs'])-set(occupancy))
            cond['selected']=None
        unsupported=[s['sounding_event_id'] for s in active if spelled_height(s['pitch']) is None]
        grace=[n['note_id'] for n in notes.values() if n.get('grace',{}).get('is_grace') and a<=f(n['global_onset_quarter'])<b]
        pairs=[]
        for left,right in combinations(sorted(conditions),2):
            l,r=conditions[left],conditions[right]
            buckets={k:[] for k in ('shared_member','left_member_only','right_member_only','neither_member','spelling_unresolved')}
            for sid in sorted(active_ids):
                x,y=l['event_membership'][sid],r['event_membership'][sid]
                good='member_under_spelling_hypothesis'; outside='nonmember_not_confirmed_nct'
                bucket=('shared_member' if x==y==good else 'left_member_only' if x==good and y==outside else
                        'right_member_only' if y==good and x==outside else 'neither_member' if x==y==outside else 'spelling_unresolved')
                buckets[bucket].append(sid)
            lhs,rhs=set(l['pattern_signatures']),set(r['pattern_signatures'])
            blocked=bool(path['abstention_reasons'] or unsupported or grace)
            status=('context_or_voice_unresolved' if blocked else 'spelling_unresolved' if buckets['spelling_unresolved'] or not l['all_member_spelling_consistent'] or not r['all_member_spelling_consistent'] else
                    'observed_membership_difference_not_winner' if buckets['left_member_only'] or buckets['right_member_only'] else 'no_observed_membership_difference')
            pairs.append({'left':left,'right':right,'status':status,'event_buckets':buckets,
                'shared_pattern_refs':sorted(lhs&rhs),'left_only_pattern_refs':sorted(lhs-rhs),'right_only_pattern_refs':sorted(rhs-lhs),
                'selected':None,'independent_vote':False,'ranking_weight':None})
        records.append({'path_id':path['path_id'],'group_id':path['group_id'],'source_refs':path['source_refs'],
            'comparison_span':span,'all_voice_events':facts,'pitch_class_occupancy_quarters':pc_durations,
            'conditions':sorted(conditions.values(),key=lambda c:c['candidate_key']),'excluded_conditions':excluded,'pairs':pairs,
            'unsupported_pitch_refs':unsupported,'grace_refs':grace,'path_abstentions':path['abstention_reasons'],
            'initial_gap':path['initial_gap'],'prior_review_reasons':path['prior_review_reasons'],
            'status':'paired_conditions' if pairs else 'fewer_than_two_full_window_conditions',
            'selected':None,'used_for_ranking':False})
    return {'version':VERSION,'records':records,'event_units':units,
        'summary':{'paths':len(records),'paths_with_comparison':sum(bool(r['pairs']) for r in records),
            'pair_statuses_not_independent_votes':dict(Counter(p['status'] for r in records for p in r['pairs'])),
            'unique_sound_units':len(units)},'production_modified':False,'source_annotation_used':False,
        'limits':['Compare only fully covering frozen chord conditions on the same arrival window',
            'Membership difference may be an ornament, omitted member, pedal or wrong chord; no winner inferred',
            'Same sound unit reused across windows is not an independent vote; no scalar confidence',
            'Other voices are observed without claiming voice-leading identity or assigning NCT labels',
            'Spelling support may depend on a root observed in the wider frozen context; it is not new independent evidence']}
