"""Freeze reviewer prose and reproducible score context without turning it into gold."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from xml.etree import ElementTree as ET
from .harmony_joint import f
from .formal_ir import q
from .harmony_arpeggio_benchmark import digest, write


def context_measures(ir, printed, padding=1):
    if padding < 0: raise ValueError('negative_padding')
    ordered=sorted(ir['measures'], key=lambda m:m['sequential_measure_index'])
    indices=set()
    for number in printed:
        matches=[i for i,m in enumerate(ordered) if m['printed_measure_number']==str(number)]
        if len(matches)!=1: raise ValueError('printed_measure_missing_or_ambiguous:'+str(number))
        i=matches[0];indices.update(range(max(0,i-padding),min(len(ordered),i+padding+1)))
    return [ordered[i] for i in sorted(indices)]


def cells(ir, measure):
    start=f(measure['global_start_quarter']);end=start+f(measure['actual_duration_quarter'])
    sounds=[s for s in ir['sounding_events'] if f(s['span']['start'])<end and f(s['span']['end'])>start]
    points=sorted({start,end}|{max(start,f(s['span']['start'])) for s in sounds}|{min(end,f(s['span']['end'])) for s in sounds})
    result=[]
    for lo,hi in zip(points,points[1:]):
        active=sorted((s for s in sounds if f(s['span']['start'])<hi and f(s['span']['end'])>lo),key=lambda s:(s['pitch']['midi_pitch'],s['sounding_event_id']))
        result.append({'span':{'start':q(lo),'end':q(hi)},'onset_in_measure_quarters':q(lo-start),
            'denominator_beat':q(1+(lo-start)*measure['time_signature']['beat_type']/4),
            'active_event_refs':[s['sounding_event_id'] for s in active],
            'attacked_event_refs':[s['sounding_event_id'] for s in active if f(s['span']['start'])==lo],
            'pitches':[s['pitch']['spelling'] for s in active],
            'lowest_sounding_pitch':active[0]['pitch']['spelling'] if active else None})
    return result


def archived_colors(ir, explanations, measure_ids):
    """Reproduce old view's categories; do not infer which button the user clicked."""
    notes={n['note_id']:n for n in ir['note_events'] if n['measure_id'] in measure_ids}
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']}
    result=[]
    for row in explanations:
        for pair in row['pairs']:
            memberships={}
            for cell in pair['cells']:
                for category,ids in cell['event_buckets'].items():
                    for sid in ids: memberships.setdefault(sid,set()).add(category)
            marked=[]
            for sid,categories in memberships.items():
                color='mixed' if len(categories)>1 else next(iter(categories))
                if color not in ('mixed','spelling_unresolved'): continue
                for nid in sounds[sid]['source_note_ids']:
                    if nid in notes:
                        n=notes[nid]
                        marked.append({'note_id':nid,'pitch':n['written_pitch']['spelling'],'measure_id':n['measure_id'],
                            'onset_in_measure':n['onset_in_measure'],'category':color,'underlying_categories':sorted(categories)})
            if marked: result.append({'candidate_ref':row['candidate_ref'],'merged_ref':pair['merged_ref'],'split_ref':pair['split_ref'],'purple_notes':marked})
    return result


def build(source, request_file, output):
    if output.exists(): raise ValueError('immutable_archive_choose_new_output')
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    request=read(request_file);ir=read(source/'canonical_music_ir.json');provenance=read(source/'case-provenance.json')
    entry=provenance['manifest_entry'];xml=source/Path(entry['score_source_path']).name
    required={**provenance['revision']['hashes'],xml.name:entry['score_sha256']}
    if any(digest(source/name)!=sha for name,sha in required.items()): raise ValueError('frozen_source_mismatch')
    printed=sorted({m for c in request['claims'] for m in c['printed_measures']},key=int)
    measures=context_measures(ir,printed,request['context_padding_physical_measures']);mids={m['measure_id'] for m in measures}
    target_mids={m['measure_id'] for m in ir['measures'] if m['printed_measure_number'] in printed}
    root=ET.parse(xml).getroot()
    for e in root.iter():e.tag=e.tag.rsplit('}',1)[-1]
    seqs={m['sequential_measure_index'] for m in measures};excerpts=[]
    for part in root.findall('part'):
        for i,measure in enumerate(part.findall('measure'),1):
            if i in seqs: excerpts.append({'source_part_id':part.get('id'),'sequential_measure_index':i,'printed_measure_number':measure.get('number'),'xml':ET.tostring(measure,encoding='unicode')})
    explanations=read(source/'path-explanation.json')['records']
    output.mkdir(parents=True);snapshot=output/'source-snapshot';shutil.copytree(source,snapshot)
    shutil.copyfile(request_file,output/'request.json')
    hashes={str(p.relative_to(source)):digest(p) for p in source.rglob('*') if p.is_file()}
    record={'schema_name':'musicanote-harmony-feedback-context','schema_version':'0.1.0',
        'created_at':datetime.now(timezone.utc).isoformat(),'score_id':ir['score']['score_id'],'ir_document_id':ir['ir_document_id'],
        'request':request,'status':'reviewer_feedback_with_observation_audit_not_gold',
        'context_measures':measures,'context_xml_measures':excerpts,
        'context_note_events':[n for n in ir['note_events'] if n['measure_id'] in mids],
        'measure_cells':{m['printed_measure_number']:cells(ir,m) for m in measures},
        'old_purple_categories_by_comparison':archived_colors(ir,explanations,target_mids),
        'actual_clicked_comparison':'not_recorded_do_not_assume',
        'full_score_reconstruction':'source-snapshot/'+xml.name,
        'excerpt_contract':'XML fragments require inherited attributes; use full original XML for reconstruction.',
        'snapshot_hashes':hashes,'request_sha256':digest(request_file),'code_sha256':digest(Path(__file__)),
        'training_eligible':False,'production_modified':False,'automatic_rule_update':False}
    write(output/'feedback-context.json',record)
    assert all(digest(source/n)==sha and digest(snapshot/n)==sha for n,sha in hashes.items())
    write(output/'verification.json',{'passed':True,'frozen_sources_unchanged':True,'snapshot_hashes_match':True,
        'context_printed_measures':[m['printed_measure_number'] for m in measures],
        'raw_feedback_preserved':read(output/'request.json')['raw_feedback']==request['raw_feedback']})
    return {'archive':str(output),'context_measures':len(measures),'purple_comparisons':len(record['old_purple_categories_by_comparison'])}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--request',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();print(build(a.source,a.request,a.output))
