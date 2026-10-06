"""Frozen relation audit with exact-span controls and reconstructable context.

No engine rerun, annotation label input, automatic selection or production edit.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
from time import perf_counter
import xml.etree.ElementTree as ET
from fractions import Fraction
from copy import deepcopy

from .formal_ir import q
from .harmony_joint import f
from .harmony_progression_evidence_trial import digest, write
from .harmony_geometry_cache_trial import inputs, load_hashed_json
from .harmony_relation_case_audit import run as audit, pitch_identity
from .harmony_source_transposition import parse_written_pitch

VERSION = 'relation-case-trial-0.1.2'


def _payload(path, expected):
    payload = Path(path).read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError('consumed_input_hash_mismatch:' + str(path))
    return payload


def _children(node, name):
    return [child for child in node if child.tag.rsplit('}', 1)[-1] == name]


def _text(node, name, default=None):
    children = _children(node, name)
    if len(children) > 1: raise ValueError('duplicate_xml_' + name)
    if not children: return default
    return children[0].text.strip() if children[0].text else None


def source_index(payload):
    """Raw indexed notes only: NOT a new onset/repeat/concert-pitch parser."""
    root = ET.fromstring(payload)
    if root.tag.rsplit('}', 1)[-1] != 'score-partwise':
        raise ValueError('unsupported_source_layout')
    result = {}
    for pi, part in enumerate(_children(root, 'part'), 1):
        divisions = None
        for mi, measure in enumerate(_children(part, 'measure'), 1):
            ni = 0
            for child in measure:
                tag = child.tag.rsplit('}', 1)[-1]
                if tag == 'attributes':
                    raw = _text(child, 'divisions')
                    if _children(child, 'divisions'):
                        divisions = Fraction(raw) if raw else None
                elif tag == 'note':
                    ni += 1
                    path = f'/score-partwise/part[{pi}]/measure[{mi}]/note[{ni}]'
                    result[path] = {'source_part_id': part.get('id'), 'source_measure_number': measure.get('number'),
                        'source_voice': _text(child, 'voice'), 'source_staff': _text(child, 'staff', '1'),
                        'note_ordinal': ni-1, 'raw_duration': _text(child, 'duration'),
                        'divisions': divisions, 'grace': bool(_children(child, 'grace')),
                        'source_xml': ET.tostring(child, encoding='unicode'),
                        'pitch_probe': parse_written_pitch(child)}
    return result


def trace_note(note, references, index):
    ref = references.get(note.get('source_ref_id'))
    row = {'note_id': note['note_id'], 'source_ref': deepcopy(ref),
           'xml_onset_reparsed': False, 'concert_pitch_verified': False}
    if not ref or ref.get('source_xpath') not in index:
        return {**row, 'status': 'unresolved_locator', 'checks': {}}
    raw = index[ref['source_xpath']]
    checks = {key: ref.get(key) == raw[key] for key in ('source_part_id', 'source_measure_number', 'source_voice')}
    try:
        checks['source_staff'] = int(ref['source_staff']) == int(raw['source_staff'])
        checks['source_element_index_is_note_ordinal'] = ref['source_element_index'] == raw['note_ordinal']
    except (ValueError, TypeError, KeyError):
        checks['source_staff_or_ordinal'] = False
    probe = raw['pitch_probe']; duration = None; unsupported = []
    if probe['status'] == 'source_written_pitch_observed':
        try:
            checks['written_pitch'] = pitch_identity(note['written_pitch']) == pitch_identity(probe['written_pitch'])
        except (ValueError, KeyError, TypeError):
            unsupported.append('ir_written_pitch_unsupported')
    else:
        unsupported.append(probe.get('reason', 'source_pitch_unsupported'))
    try:
        if raw['raw_duration'] is None and raw['grace']:
            duration = Fraction(0)
        elif raw['divisions'] is None or raw['divisions'] <= 0:
            unsupported.append('missing_or_invalid_divisions')
        elif raw['raw_duration'] is None:
            unsupported.append('missing_duration')
        else:
            duration = Fraction(raw['raw_duration']) / raw['divisions']
        if duration is not None:
            checks['notated_duration'] = duration == f(note['notated_duration_quarter'])
        checks['grace_flag'] = raw['grace'] == bool(note.get('grace', {}).get('is_grace'))
    except (ValueError, ZeroDivisionError, KeyError):
        unsupported.append('duration_probe_unsupported')
    status = 'source_note_fields_rechecked' if all(checks.values()) and not unsupported else (
        'source_note_field_mismatch' if not all(checks.values()) else 'source_note_probe_unsupported')
    return {**row, 'status': status, 'checks': checks, 'unsupported': unsupported,
            'raw_source_note_xml': raw['source_xml'], 'written_pitch_probe': probe,
            'observed_notated_duration_quarter': q(duration) if duration is not None else None,
            'raw_duration': raw['raw_duration'], 'divisions': q(raw['divisions']) if raw['divisions'] is not None else None}


def context(ir, span, source_notes):
    """One measure either side, all parts and complete tie chains; no clipped IR."""
    start, end = f(span['start']), f(span['end'])
    measures = sorted(ir['measures'], key=lambda m: m['sequential_measure_index'])
    relevant = [i for i, m in enumerate(measures) if f(m['global_start_quarter']) < end and
                f(m['global_start_quarter']) + f(m['actual_duration_quarter']) > start]
    if not relevant: raise ValueError('context_measure_not_found')
    selected = measures[max(0, min(relevant)-1): min(len(measures), max(relevant)+2)]
    left = min(f(m['global_start_quarter']) for m in selected)
    right = max(f(m['global_start_quarter'])+f(m['actual_duration_quarter']) for m in selected)
    def overlaps(a, b): return a < right and b > left or a == b and left <= a < right
    sounds = [s for s in ir['sounding_events'] if overlaps(f(s['span']['start']), f(s['span']['end']))]
    required = {nid for s in sounds for nid in s['source_note_ids']}
    notes = [n for n in ir['note_events'] if n['note_id'] in required or overlaps(
        f(n['global_onset_quarter']), f(n['global_onset_quarter'])+f(n['notated_duration_quarter']))]
    rests = [r for r in ir['rest_events'] if overlaps(f(r['global_onset_quarter']),
        f(r['global_onset_quarter'])+f(r['notated_duration_quarter']))]
    refs = {r['source_ref_id']: r for r in ir['source_references']}
    traces = [trace_note(n, refs, source_notes) for n in notes]
    issues = sorted(t['note_id'] for t in traces if t['status'] != 'source_note_fields_rechecked')
    return {'record_kind': 'observational_context_not_standalone_canonical_ir',
            'span': {'start': q(left), 'end': q(right)}, 'all_parts_preserved': True,
            'event_spans_clipped': False, 'full_score_snapshot_required_for_reconstruction': True,
            'measures': deepcopy(selected), 'note_events': deepcopy(notes), 'rest_events': deepcopy(rests),
            'sounding_events': deepcopy(sounds), 'source_note_trace': traces,
            'source_fields_status': 'source_note_review_required' if issues else 'source_note_fields_rechecked',
            'source_field_issue_note_ids': issues, 'xml_onset_reparsed': False,
            'source_fields_certify_harmony': False}


def witness_note_refs(group, sounds):
    """Collect endpoint provenance without mutating saved partial matchings."""
    endpoints = set()
    for row in group['audits']:
        links = list(row['direct'].get('selected_links', []))
        links.extend(link for path in row['temporal'].get('selected_paths', []) for link in path['links'])
        for link in links:
            endpoints.update(nid for sid in link for nid in sounds[sid]['source_note_ids'])
    return endpoints


def run(reference, cached, output):
    reference, cached, output = map(Path, (reference, cached, output))
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    report, packages, chosen, hashes = inputs(reference)
    cache_paths = [cached/name for name in ('report.json', 'run-contract.json')]
    hashes.update({str(path.resolve()): digest(path) for path in cache_paths})
    cache_report = load_hashed_json(cache_paths[0], hashes[str(cache_paths[0].resolve())])
    if (cache_report.get('complete') is not True or cache_report.get('inputs_unchanged') is not True or
            cache_report.get('status_counts') != {'equal': len(report['records'])} or
            cache_report.get('source_labels_used') is not False or cache_report.get('accuracy_measured') is not False):
        raise ValueError('invalid_cache_reference')
    def key(row): return row['pair_id'], row['sample_id'], row['plan_index']
    cached_rows = {key(row): row for row in cache_report['records']}
    if len(cached_rows) != len(cache_report['records']) or set(cached_rows) != set(chosen):
        raise ValueError('cache_sample_coverage_mismatch')
    for row in cached_rows.values():
        hashes[row['artifact']] = row['sha256']; _payload(row['artifact'], row['sha256'])
    code = {str(p.resolve()): digest(p) for p in Path(__file__).parent.glob('*.py')}
    output.mkdir(parents=True, exist_ok=False)
    write(output/'run-contract.json', {'version': VERSION, 'reference': str(reference.resolve()),
        'cached': str(cached.resolve()), 'input_hashes': hashes, 'code_hashes': code,
        'selection': 'all frozen surveys inventoried; all supported span groups and EVERY same-span competitor audited',
        'selection_uses_engine_status': True, 'unbiased_accuracy_cohort': False,
        'source_labels_used': False, 'engine_recomputed': False, 'production_modified': False,
        'gold_promoted': False, 'training_promoted': False, 'external_transmission': False})
    records = []; totals = Counter(); statuses = {'direct': Counter(), 'temporal': Counter()}
    snapshots = {}; sources = {}; irs = {}; trace_counts = Counter(); inventory = []; errors = []
    unique_traces = {}; issue_packages = set(); issue_endpoint_refs = set(); exact_groups = set(); supported_shapes = set()
    supported_packages = set(); supported_families = set(); started = perf_counter()
    for number, original_row in enumerate(report['records'], 1):
        pair = original_row['pair_id']; cache_row = cached_rows[key(original_row)]
        if cache_row['source_artifact_sha256'] != original_row['sha256']:
            raise ValueError('cache_source_artifact_mismatch')
        cache_artifact = load_hashed_json(cache_row['artifact'], cache_row['sha256'], compressed=True)
        if cache_artifact['sample'] != chosen[key(original_row)]: raise ValueError('sample_identity_mismatch')
        survey = cache_artifact['relations']
        original = load_hashed_json(original_row['artifact'], original_row['sha256'], compressed=True)
        if original['sample'] != cache_artifact['sample'] or original['stages']['relations'] != survey:
            raise ValueError('cache_relation_not_equal')
        query_inventory = []
        for query_index, row in enumerate(survey.get('results', [])):
            values = {}
            for side, field in (('direct', 'query'), ('temporal', 'temporal_query')):
                values[side] = row[field]['status'] if row.get(field) else None
                statuses[side][values[side] if values[side] is not None else row['status']] += 1
            query_inventory.append({'query_index': query_index, 'pair': row['pair'],
                'original_engine_status': row['status'], **values,
                'unsupported_event_refs': row.get('unsupported_event_refs', [])})
        positive = any((row.get('query') or {}).get('status') == 'witness_exists' or
            (row.get('temporal_query') or {}).get('status') == 'temporal_resolution_possible' for row in survey.get('results', []))
        entry = {'pair_id': pair, 'sample_id': original_row['sample_id'], 'plan_index': original_row['plan_index'],
                 'survey_status': survey['status'], 'query_count': len(survey.get('results', [])), 'has_supported_query': positive,
                 'query_inventory': query_inventory, 'source_artifact': cache_row['artifact'],
                 'source_artifact_sha256': cache_row['sha256']}
        inventory.append(entry)
        if not positive: continue
        source = packages[pair]['source']; policy = source['manifest_entry']
        supported_packages.add(pair); supported_families.add(policy['work_family_id'])
        if pair not in snapshots:
            folder = output/'sources'/hashlib.sha256(pair.encode()).hexdigest()[:20]
            folder.mkdir(parents=True, exist_ok=False)
            xml_path = policy['score_source_path']; xml_bytes = _payload(xml_path, policy['score_sha256'])
            ir_bytes = _payload(source['frozen_ir_path'], source['ir_sha256'])
            xml_snapshot, ir_snapshot = folder/'source.musicxml', folder/'canonical_music_ir.json'
            xml_snapshot.write_bytes(xml_bytes); ir_snapshot.write_bytes(ir_bytes)
            snapshots[pair] = {'source_xml': str(xml_snapshot.resolve()), 'source_xml_sha256': policy['score_sha256'],
                'canonical_ir': str(ir_snapshot.resolve()), 'canonical_ir_sha256': source['ir_sha256'],
                'manifest_entry': deepcopy(policy), 'pitch_policy': deepcopy(source['pitch_policy']),
                'internal_only': True, 'reconstruction': 'unaltered full source XML and full frozen IR; not clipped fragment'}
            sources[pair] = source_index(xml_bytes); irs[pair] = json.loads(ir_bytes)
            write(folder/'provenance.json', snapshots[pair])
        try:
            result = audit(original['stages']['lattice'], survey, irs[pair])
            contexts = []
            for group in result['groups']:
                value = context(irs[pair], group['span'], sources[pair]); contexts.append(value)
                trace_counts.update(t['status'] for t in value['source_note_trace'])
                for trace in value['source_note_trace']:
                    unique_traces[(pair, trace['note_id'])] = trace['status']
                issues = set(value['source_field_issue_note_ids'])
                if issues: issue_packages.add(pair)
                sounds = {s['sounding_event_id']: s for s in value['sounding_events']}
                endpoints = witness_note_refs(group, sounds)
                for row in group['audits']:
                    if row['query_index'] in group['positive_query_indices']:
                        readings = [original['stages']['lattice']['edges'][row['pair'][side]['edge']]['readings'][row['pair'][side]['reading']]
                                    for side in ('source', 'target')]
                        supported_shapes.add((pair, tuple(f(group['span'][k]) for k in ('start', 'cut', 'end')),
                            row['pair']['family'], row['pair']['target_quality'],
                            tuple(tuple(m) for m in readings[0]['members']), tuple(tuple(m) for m in readings[1]['members'])))
                affected = sorted(issues & endpoints)
                value['source_field_issue_witness_note_ids'] = affected
                issue_endpoint_refs.update((pair, nid) for nid in affected)
                exact_groups.add((pair, tuple(f(group['span'][k]) for k in ('start', 'cut', 'end'))))
            result.update(sample=cache_artifact['sample'], source_snapshot=snapshots[pair], group_contexts=contexts,
                          source_relation_artifact=cache_row['artifact'], source_relation_sha256=cache_row['sha256'])
            totals.update(result['summary']); status = 'audited'
        except (ValueError, KeyError, IndexError, TypeError, ZeroDivisionError) as error:
            # Failed rechecks stay visible. They are not replaced with easy cases.
            result = {'status': 'failed_recheck', 'error': str(error), 'source_snapshot': snapshots[pair],
                      'sample': cache_artifact['sample'], 'original_survey': survey}
            errors.append({**entry, 'error': str(error)}); status = 'failed_recheck'
        destination = output/'samples'/Path(cache_row['artifact']).name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(gzip.compress(json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode(), mtime=0))
        records.append({**entry, 'status': status, 'artifact': str(destination.resolve()), 'sha256': digest(destination)})
        print(f'[{number}/{len(report["records"])}] {pair}: {status}', flush=True)
    changed = [path for path, expected in {**hashes, **code}.items() if digest(Path(path)) != expected]
    changed.extend(sorted({str(p.resolve()) for p in Path(__file__).parent.glob('*.py')}.symmetric_difference(code)))
    snapshot_changes = []
    for snapshot in snapshots.values():
        for field in ('source_xml', 'canonical_ir'):
            if digest(Path(snapshot[field])) != snapshot[field+'_sha256']: snapshot_changes.append(snapshot[field])
    result = {'version': VERSION, 'complete': True, 'frozen_surveys_inventoried': len(inventory),
        'frozen_packages': len(packages), 'frozen_work_families': report['unique_work_families'],
        'supported_samples': len(records), 'supported_packages': len(supported_packages),
        'supported_work_families': len(supported_families), 'summary': dict(totals),
        'all_query_inventory_count': sum(e['query_count'] for e in inventory),
        'unique_supported_span_groups': len(exact_groups), 'unique_supported_shape_span_groups': len(supported_shapes),
        'original_query_statuses': {side: dict(counts) for side, counts in statuses.items()},
        'source_trace_counts': dict(trace_counts), 'source_trace_counts_unit': 'repeated note/context instances, not unique notes',
        'unique_source_trace_counts': dict(Counter(unique_traces.values())),
        'source_field_issue_packages': sorted(issue_packages), 'source_field_issue_witness_note_refs': sorted(issue_endpoint_refs),
        'source_note_fields_all_consistent': not issue_packages,
        'source_field_issue_notes': [{'pair_id': pair, 'note_id': nid, 'status': status}
            for (pair, nid), status in unique_traces.items() if status != 'source_note_fields_rechecked'],
        'records': records, 'survey_inventory': inventory, 'failed_rechecks': errors,
        'changed_input_paths': changed, 'snapshot_changes': snapshot_changes, 'inputs_unchanged': not changed,
        'snapshots_unchanged': not snapshot_changes, 'source_labels_used': False, 'accuracy_measured': False,
        'engine_recomputed': False, 'gate_changed': False, 'production_modified': False,
        'actual_delayed_positive': 'not_seen' if not totals['actual_delayed_rechecked'] else 'observed_conditionally',
        'limits': ['Existential partial links are not full harmonic truth or actual contrapuntal voices.',
            'Exact-span controls are competing hypotheses, not gold negative harmonies.',
            'Source-note locators/written pitch/duration are rechecked; XML onsets/repeats/concert pitch are not certified.',
            'No source labels, independent accuracy, human review, gold/training or public redistribution approval.'],
        'elapsed_seconds': perf_counter()-started}
    write(output/'report.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--cached', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(); result = run(args.reference, args.cached, args.output)
    print(json.dumps({key: result[key] for key in ('summary', 'source_trace_counts', 'inputs_unchanged', 'failed_rechecks')}))
    if result['failed_rechecks'] or not result['inputs_unchanged'] or not result['snapshots_unchanged']:
        raise SystemExit(1)


if __name__ == '__main__': main()
