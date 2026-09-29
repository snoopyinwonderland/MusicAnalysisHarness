"""Audit existing IDs against parser containment and verified original XML.

Writes sidecar proposals only. Does not replace Core voice IDs, reconstruct ties,
rewrite source files, publish a dataset or change production analysis behavior.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import music21
from .canonical import CanonicalIRBuilder
from .dcml_import import parse_score_without_imported_harmony
from .source_note_mapping_audit import xml_inventory, compare, write
from .cadential_six_four_audit import digest
from .voice_provenance import VERSION, parser_voice_inventory, assess


def build(previous_audit, output):
    previous = Path(previous_audit); out = Path(output)
    if out.exists():
        raise ValueError('output_exists')
    report_path = previous / 'report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    out.mkdir(parents=True)
    contract = {
        'version': VERSION, 'music21_version': music21.__version__,
        'previous_report_sha256': digest(report_path),
        'mode': 'read_only_diagnostic_and_sidecar_proposals',
        'code_hashes': {name: digest(Path(__file__).with_name(name)) for name in
            ('voice_provenance.py', 'voice_provenance_audit.py', 'canonical.py',
             'dcml_import.py', 'source_note_mapping_audit.py')},
        'rest_mapping': 'not_audited',
        'logical_voice_migration': 'not_applied',
    }
    write(out / 'run-contract.json', contract)
    totals = Counter(); scores = []
    for entry in report['scores']:
        folder = previous / entry['score']
        repair_path = folder / 'repair.json'; candidate_path = folder / 'candidate_ir.json'
        if digest(repair_path) != entry['repair_sha256']:
            raise ValueError('repair_hash_mismatch')
        repair = json.loads(repair_path.read_text(encoding='utf-8'))
        e = repair['identity']; source = Path(e['score_source_path'])
        if e['split'] != 'train' or e['rights'].get('internal_research_use') is not True:
            raise ValueError('train_internal_research_only')
        if digest(source) != e['score_sha256'] or digest(candidate_path) != repair['candidate_sha256']:
            raise ValueError('input_hash_mismatch')
        paths = [source, candidate_path, repair_path, *[Path(e['package_path']) / n for n in repair['input_hashes']]]
        hashes = {str(p): digest(p) for p in paths}
        ir = json.loads(candidate_path.read_text(encoding='utf-8'))
        parsed, _, _ = parse_score_without_imported_harmony(source)
        legacy = CanonicalIRBuilder().build(parsed, source)
        observations = parser_voice_inventory(parsed)
        segments = {s['segment_id']: s for s in legacy['notated_note_segments']}
        if set(observations) != set(segments):
            raise ValueError('fingerprint_recipe_changed')
        raw = xml_inventory(source)
        gate = set(repair['mapping']['matched_note_ids_in_source_order'])
        checks = compare(ir, raw, gate)
        if any(r['status'] == 'mismatch' for r in checks.values()):
            raise ValueError('source_geometry_changed')
        refs = {r['source_ref_id']: r for r in ir['source_references']}
        voices = {v['voice_id']: v['source_voice_number'] for v in ir['voices']}
        rows = []; counts = Counter()
        for n in ir['note_events']:
            ref = refs[n['source_ref_id']]; key = ref['local_fingerprint']
            if key not in observations:
                raise ValueError('legacy_event_not_reproduced:' + n['note_id'])
            observation = observations[key]
            old = voices[n['voice_id']]
            if old != observation['legacy_context_voice']:
                raise ValueError('legacy_voice_not_reproduced')
            verified = checks[n['note_id']]['status'] == 'exact'
            xml_voice = raw[ref['source_xpath']]['voice'] if verified else None
            result = assess(old, observation, xml_voice, verified)
            rows.append({'note_id': n['note_id'], 'existing_voice_id': n['voice_id'],
                'source_ref_id': n['source_ref_id'], 'source_xpath': ref.get('source_xpath'),
                'source_part_id': ref['source_part_id'], 'source_staff': ref['source_staff'],
                'printed_measure': ref['source_measure_number'], 'pitch': n['written_pitch']['spelling'],
                'parser': observation, 'xml_voice': xml_voice, **result})
            counts[result['category']] += 1
            counts['notes'] += 1
            counts['legacy_xml_disagreements'] += result['legacy_xml_disagreement']
        if any(digest(p) != hashes[str(p)] for p in paths):
            raise ValueError('input_modified')
        destination = out / (entry['score'] + '.json')
        write(destination, {'identity': e, 'input_hashes': hashes, 'counts': dict(counts),
              'note_provenance': rows, 'core_modified': False,
              'warning': 'XML voice is a notation label, not inferred melody continuity. No ties rebuilt.'})
        totals.update(counts)
        scores.append({'score': entry['score'], 'counts': dict(counts), 'sha256': digest(destination)})
        print(entry['score'], dict(counts), flush=True)
    result = {'version': VERSION, 'scores': scores, 'summary': dict(totals),
        'inputs_unchanged': True, 'production_data_modified': False,
        'default_parser_modified': False, 'contract_sha256': digest(out / 'run-contract.json')}
    write(out / 'report.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--previous-audit', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.previous_audit, args.output)['summary'], indent=2))
