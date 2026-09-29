"""Opt-in, immutable candidate revision from verified sequence replay.

Never updates a production manifest. Note/rest/source-ref identities and source
annotation labels/spans remain stable; changed grouping identities get aliases.
"""
import argparse
from collections import defaultdict, Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from jsonschema import Draft202012Validator
from .canonical import stable_id
from .formal_ir import q
from .ordered_grace_ties import resolve
from .source_sequence_audit import xml_rows
from .source_enrichment import enrich_from_mapped_musicxml
from .source_note_mapping_audit import write
from .cadential_six_four_audit import digest

VERSION = 'source-identity-revision-0.1.0'
SCHEMAS = Path(__file__).resolve().parents[2] / 'MUSICANOTE_Canonical_Music_IR' / 'schemas'


def f(value): return Fraction(value['numerator'], value['denominator'])


def alignment_membership(sounds, target):
    overlapping=[]; attacked=[]
    if 'point' in target:
        start=end=f(target['point']); point=True
    else:
        start=f(target['span']['start']); end=f(target['span']['end']); point=False
        if end<start: raise ValueError('negative_alignment_span')
        if end==start: return [],[]
    for s in sounds:
        x=f(s['span']['start']); y=f(s['span']['end'])
        if (x<=start<y if point else x<end and y>start):
            overlapping.append(s['sounding_event_id'])
            if (x==start if point else start<=x<end): attacked.append(s['sounding_event_id'])
    return overlapping,attacked


def membership_aliases(before, after, id_field, members):
    result = []
    by_id={n[id_field]:n for n in after}; member_index=defaultdict(set)
    for n in after:
        for member in members(n): member_index[member].add(n[id_field])
    for old in before:
        matches=set()
        for member in members(old): matches.update(member_index[member])
        unchanged = by_id.get(old[id_field])==old
        result.append({'old_id': old[id_field], 'new_ids': sorted(matches),
            'status': 'unchanged' if unchanged else 'review_changed_semantics',
            'automatic_annotation_retarget': unchanged})
    return result


def revise(old, observations, source):
    ir = deepcopy(old); score_id = ir['score']['score_id']
    events = {n.get('note_id', n.get('rest_id')): n for n in ir['note_events'] + ir['rest_events']}
    if len(observations) != len(events) or {r['event_id'] for r in observations} != set(events):
        raise ValueError('complete_bijective_event_mapping_required')
    raw_rows, raw_measures = xml_rows(source)
    if {r['original']['xpath'] for r in observations} != {r['xpath'] for r in raw_rows}:
        raise ValueError('complete_source_mapping_required')
    raw_by_path = {r['xpath']: r for r in raw_rows}
    for r in observations:
        # Serialized tuples become lists; compare canonical JSON encodings.
        if json.dumps(r['original'], sort_keys=True) != json.dumps(raw_by_path[r['original']['xpath']], sort_keys=True):
            raise ValueError('source_observation_changed')
    parts = list(dict.fromkeys(r['part'] for r in raw_rows))
    grids = [[(key[1], v) for key, v in raw_measures.items() if key[0] == part] for part in parts]
    if any(grid != grids[0] for grid in grids[1:]): raise ValueError('unaligned_part_measure_grids')
    old_measures = sorted(ir['measures'], key=lambda m: m['sequential_measure_index'])
    if len(old_measures) != len(grids[0]): raise ValueError('measure_count_changed')
    measure_alias = defaultdict(set); new_measures = []
    for old_m, (index, raw) in zip(old_measures, grids[0]):
        if f(old_m['global_start_quarter']) != Fraction(raw['start']): raise ValueError('measure_start_changed')
        m = deepcopy(old_m)
        m.update(measure_id='measure_' + stable_id(score_id, 'physical-v1', index),
            printed_measure_number=raw['label'], sequential_measure_index=index-1,
            actual_duration_quarter=q(raw['duration']))
        new_measures.append(m); measure_alias[old_m['measure_id']].add(m['measure_id'])
    ir['measures'] = new_measures
    ir['score']['pickup_measure'] = next((m['measure_id'] for m in new_measures if m['pickup']), None)
    refs = {r['source_ref_id']: r for r in ir['source_references']}
    voices = {}; segments = []; seg_to_note = {}; grace_lanes = defaultdict(list)
    for row in observations:
        n = events[row['event_id']]; raw = row['original']; p = row['parser']
        if raw['voice'] is None: raise ValueError('unknown_source_voice')
        if f(n['global_onset_quarter']) != Fraction(raw['global_onset']) or f(n['notated_duration_quarter']) != Fraction(raw['token'][1]):
            raise ValueError('event_time_changed')
        n['measure_id'] = new_measures[raw['measure_index']-1]['measure_id']; n['onset_in_measure'] = q(raw['token'][0])
        key = (n['part_id'], n['display_staff_id'], raw['voice'])
        if key not in voices:
            voices[key] = {'voice_id': 'voice_' + stable_id(score_id, 'source-lane-v1', *key), 'part_id': key[0],
                'default_staff_id': key[1], 'source_voice_number': key[2], 'event_ids': [], 'inference': None}
        n['voice_id'] = voices[key]['voice_id']; voices[key]['event_ids'].append(row['event_id'])
        refs[n['source_ref_id']].update(source_xpath=raw['xpath'], source_measure_number=raw['measure_label'],
            source_voice=raw['voice'], source_staff=int(raw['staff']), source_element_index=raw['source_note_ordinal']-1)
        if row['kind'] == 'note':
            start = Fraction(raw['global_onset']); duration = Fraction(raw['token'][1])
            segments.append({'segment_id': row['fingerprint'], 'part_id': p['legacy_part'], 'staff_id': p['legacy_staff'],
                'voice_id': raw['voice'], 'measure': raw['measure_index'], 'onset_ql': str(start), 'end_ql': str(start+duration),
                'pitch_spelling': n['written_pitch']['spelling'], 'midi': n['written_pitch']['midi_pitch'],
                'tie_role': n['tie_role'], 'source_order': (raw['measure_index'], raw['source_note_ordinal'])})
            seg_to_note[row['fingerprint']] = n['note_id']
            if n['grace']['is_grace']:
                grace_lanes[(n['voice_id'], raw['measure_index'], raw['global_onset'])].append((raw['source_note_ordinal'], n))
    ir['voices'] = list(voices.values())
    for staff in ir['staves']:
        staff['voice_ids'] = [v['voice_id'] for v in ir['voices'] if v['default_staff_id'] == staff['staff_id']]
    for lane in grace_lanes.values():
        for ordinal, (_, n) in enumerate(sorted(lane, key=lambda x:x[0])):
            n['grace']['order'] = ordinal; n['grace']['anchor_note_id'] = None
    graph = resolve(segments)
    if graph['issues'] or graph['chain_problems']: raise ValueError('unresolved_tie_graph')
    old_sounds = {tuple(s['source_note_ids']): s for s in old['sounding_events']}
    old_attacks = {a['sounding_event_id']:a for a in old['attack_events']}
    sounds = []; ties = []; attacks = []
    for sound in graph['sounds']:
        ids = [seg_to_note[s] for s in sound['segment_ids']]; attack = ids[0]
        start = q(sound['attack_onset_ql']); end = q(sound['sounding_end_ql'])
        previous = old_sounds.get(tuple(ids))
        same = previous and previous['span'] == {'start':start,'end':end} and previous['attack_note_id'] == attack
        sid = previous['sounding_event_id'] if same else 'sound_' + stable_id(score_id, VERSION, *ids, start, end)
        tid = (previous.get('tie_chain_id') if same else 'tie_' + stable_id(sid)) if len(ids)>1 else None
        pitch = events[attack]['concert_pitch']; duration = q(f(end)-f(start))
        sounds.append({'sounding_event_id':sid,'source_note_ids':ids,'pitch':pitch,'span':{'start':start,'end':end},
            'sounding_duration':duration,'attack_note_id':attack,'tie_chain_id':tid})
        if tid: ties.append({'tie_chain_id':tid,'source_note_ids':ids,'sounding_pitch':pitch,'span':{'start':start,'end':end},'total_duration':duration,'attack_note_id':attack})
        prior_attack = old_attacks.get(sid) if same else None
        attacks.append({'attack_event_id':prior_attack['attack_event_id'] if prior_attack else 'attack_'+stable_id(sid),
                        'note_id':attack,'sounding_event_id':sid,'global_onset_quarter':start})
    ir.update(sounding_events=sounds, tie_chains=ties, attack_events=attacks)
    # Inject verified IDs into an in-memory source; notation enrichment must not
    # reuse the old hash-sorted grace mappings. Rebuild ONLY actual XML chords.
    root = ET.parse(source).getroot()
    for el in root.iter(): el.tag=el.tag.rsplit('}',1)[-1]
    by_path = {r['original']['xpath']:r['event_id'] for r in observations}
    groups = []; group = []
    def finish_group():
        if len(group)>1:
            first=events[group[0]]; gid='nog_'+stable_id(score_id,'source-chord-v1',*group)
            groups.append({'chord_onset_group_id':gid,'voice_id':first['voice_id'],
                           'global_onset_quarter':first['global_onset_quarter'],'note_ids':list(group)})
            for nid in group: events[nid]['chord_member']=True; events[nid]['chord_onset_group_id']=gid
    note_ids={n['note_id'] for n in ir['note_events']}
    for n in ir['note_events']: n['chord_member']=False; n['chord_onset_group_id']=None
    for pi, part in enumerate(root.findall('part'),1):
        for mi, measure in enumerate(part.findall('measure'),1):
            group=[]
            for ni, el in enumerate(measure.findall('note'),1):
                nid=by_path[f'/score-partwise/part[{pi}]/measure[{mi}]/note[{ni}]']
                el.attrib.pop('{http://www.w3.org/XML/1998/namespace}id',None); el.set('id',nid)
                if el.find('chord') is None: finish_group(); group=[]
                if nid in note_ids: group.append(nid)
                else: finish_group(); group=[]
            finish_group()
    ir['chord_onset_groups']=groups
    enrich_from_mapped_musicxml(ir,ET.tostring(root,encoding='unicode'))
    ir['parser_manifest']={'parser_name':'source-identity-candidate-migration','parser_version':VERSION,
        'normalization_policy_version':VERSION,'options':{'parent_ir_document_id':old['ir_document_id'],
        'publication':'candidate_not_production','grace_time':'notated_zero_no_performance_inference',
        'grace_order':'zero_based_within_voice_physical_measure_global_onset','anchor_policy':'null_not_inferred'}}
    ir['validation_summary']={}
    ir['ir_document_id']='ir_'+stable_id(old['ir_document_id'],VERSION,json.dumps(ir,sort_keys=True,separators=(',',':')))
    aliases={}
    for collection, field, members in (
        ('voices','voice_id',lambda n:n['event_ids']),('sounding_events','sounding_event_id',lambda n:n['source_note_ids']),
        ('tie_chains','tie_chain_id',lambda n:n['source_note_ids']),('attack_events','attack_event_id',lambda n:[n['note_id']]),
        ('chord_onset_groups','chord_onset_group_id',lambda n:n['note_ids'])):
        aliases[collection]=membership_aliases(old[collection],ir[collection],field,members)
    aliases['measures']=[{'old_id':k,'new_ids':sorted(v),'automatic_annotation_retarget':False} for k,v in measure_alias.items()]
    return ir, {'aliases':aliases,'graph':graph,'note_rest_source_ref_ids':'preserved','parent_ir_document_id':old['ir_document_id']}


def validate_revision(old, ir):
    Draft202012Validator(json.loads((SCHEMAS/'canonical_music_ir.schema.json').read_text())).validate(ir)
    measures={m['measure_id']:m for m in ir['measures']}; voices={v['voice_id']:v for v in ir['voices']}
    if len(measures)!=len(ir['measures']): raise ValueError('duplicate_measure_id')
    if ir['score']['score_id']!=old['score']['score_id']: raise ValueError('score_id_changed')
    old_events={n.get('note_id',n.get('rest_id')):n for n in old['note_events']+old['rest_events']}
    events={n.get('note_id',n.get('rest_id')):n for n in ir['note_events']+ir['rest_events']}
    if set(events)!=set(old_events): raise ValueError('event_ids_changed')
    for eid,n in events.items():
        for field in ('global_onset_quarter','notated_duration_quarter','written_pitch','concert_pitch','source_ref_id','tie_role'):
            if n.get(field)!=old_events[eid].get(field): raise ValueError('protected_field_changed:'+field)
        if f(n['global_onset_quarter'])!=f(measures[n['measure_id']]['global_start_quarter'])+f(n['onset_in_measure']): raise ValueError('local_global_inconsistent')
        if eid not in voices[n['voice_id']]['event_ids']: raise ValueError('voice_membership_missing')
    used=[nid for s in ir['sounding_events'] for nid in s['source_note_ids']]
    if Counter(used)!=Counter(n['note_id'] for n in ir['note_events']): raise ValueError('sound_note_partition_changed')
    source_refs={r['source_ref_id'] for r in ir['source_references']}
    if source_refs!={r['source_ref_id'] for r in old['source_references']}: raise ValueError('source_ref_ids_changed')
    members=[eid for v in ir['voices'] for eid in v['event_ids']]
    if Counter(members)!=Counter(events.keys()): raise ValueError('voice_event_partition_changed')
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']}; ties={t['tie_chain_id']:t for t in ir['tie_chains']}
    for s in sounds.values():
        if f(s['span']['end'])-f(s['span']['start'])!=f(s['sounding_duration']): raise ValueError('sound_duration_mismatch')
        if s['attack_note_id']!=s['source_note_ids'][0]: raise ValueError('attack_note_mismatch')
        if s.get('tie_chain_id') and ties[s['tie_chain_id']]['source_note_ids']!=s['source_note_ids']: raise ValueError('tie_membership_mismatch')
    for a in ir['attack_events']:
        s=sounds[a['sounding_event_id']]
        if a['note_id']!=s['attack_note_id'] or a['global_onset_quarter']!=s['span']['start']: raise ValueError('attack_reference_mismatch')
    for group in ir['chord_onset_groups']:
        if group['voice_id'] not in voices or any(events[n]['chord_onset_group_id']!=group['chord_onset_group_id'] for n in group['note_ids']):
            raise ValueError('chord_group_reference_mismatch')
    return {'schema':True,'stable_event_ids':True,'exact_local_global_time':True,'sound_partition':True}


def build(sequence_audit, output):
    src=Path(sequence_audit); out=Path(output)
    if out.exists(): raise ValueError('output_exists')
    report=json.loads((src/'report.json').read_text()); out.mkdir(parents=True)
    rows=[]
    for entry in report['scores']:
        path=src/(entry['score']+'.json')
        if digest(path)!=entry['sha256']: raise ValueError('audit_hash_mismatch')
        data=json.loads(path.read_text(encoding='utf-8'))
        if data['identity']['split']!='train' or data['identity']['rights'].get('internal_research_use') is not True:
            raise ValueError('train_internal_research_only')
        for p,h in data['input_hashes'].items():
            if digest(p)!=h: raise ValueError('input_hash_mismatch')
        old_path=next(Path(p) for p in data['input_hashes'] if Path(p).name=='candidate_ir.json')
        old=json.loads(old_path.read_text(encoding='utf-8'))
        ir,migration=revise(old,data['observations'],data['identity']['score_source_path'])
        ir['validation_summary']=validate_revision(old,ir)
        target=out/entry['score']; target.mkdir()
        write(target/'canonical_music_ir.json',ir); write(target/'migration.json',migration)
        # Labels, IDs and span coordinates remain immutable. Only revision
        # targets and derived sound memberships are rebuilt in new files.
        package=Path(data['identity']['package_path'])
        annotations=[json.loads(line) for line in (package/'imported_annotations.jsonl').read_text(encoding='utf-8').splitlines() if line]
        alignments=[json.loads(line) for line in (package/'alignment_records.jsonl').read_text(encoding='utf-8').splitlines() if line]
        by_ann={a['annotation_id']:a for a in annotations}
        for a in annotations:
            if a.get('target'): a['target']['ir_document_id']=ir['ir_document_id']
        for a in alignments:
            a['ir_document_id']=ir['ir_document_id']; a['method_version']=VERSION
            if a.get('target'): a['target']['ir_document_id']=ir['ir_document_id']
            native=by_ann[a['annotation_id']]['native_target']; mc=int(native['mc'])
            a['measure_id']=ir['measures'][mc-1]['measure_id'] if 1<=mc<=len(ir['measures']) else None
            a['sounding_event_ids']=[]; a['attacked_sounding_event_ids']=[]
            if a.get('target') and a['mapping_status'] in ('exact','verified_transform'):
                a['sounding_event_ids'],a['attacked_sounding_event_ids']=alignment_membership(ir['sounding_events'],a['target'])
        for name, records in (('imported_annotations',annotations),('alignment_records',alignments)):
            schema='imported_annotation.schema.json' if name=='imported_annotations' else 'alignment_record.schema.json'
            validator=Draft202012Validator(json.loads((SCHEMAS/schema).read_text()))
            for record in records: validator.validate(record)
            (target/(name+'.jsonl')).write_text(''.join(json.dumps(a,ensure_ascii=False)+'\n' for a in records),encoding='utf-8')
        for p,h in data['input_hashes'].items():
            if digest(p)!=h: raise ValueError('original_modified')
        summary={'score':entry['score'],'ir_document_id':ir['ir_document_id'],'notes':len(ir['note_events']),
            'rests':len(ir['rest_events']),'sounds':len(ir['sounding_events']), 'annotations':len(annotations),
            'resolved_grace_buckets':len(migration['graph']['resolved_grace_buckets']),
            'hashes':{p.name:digest(p) for p in target.iterdir() if p.is_file()},'validation':ir['validation_summary']}
        rows.append(summary); print(entry['score'],'candidate validated',flush=True)
    result={'version':VERSION,'status':'candidate_only_not_published','scores':rows,
        'sequence_report_sha256':digest(src/'report.json'),'originals_unchanged':True,'production_modified':False,
        'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in ('source_identity_revision.py','ordered_grace_ties.py','voice_tie_impact.py','source_enrichment.py')}}
    write(out/'candidate_manifest.json',result); return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--sequence-audit',required=True); parser.add_argument('--output',required=True)
    args=parser.parse_args(); build(args.sequence_audit,args.output)
