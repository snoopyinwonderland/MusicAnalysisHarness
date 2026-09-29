"""Save changed source-link/tie cases with adjacent original XML measures."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from .source_note_mapping_audit import write
from .cadential_six_four_audit import digest


def build(sequence_audit, tie_audit, output):
    sequence_dir = Path(sequence_audit); tie_dir = Path(tie_audit); out = Path(output)
    if out.exists(): raise ValueError('output_exists')
    seq_report = json.loads((sequence_dir / 'report.json').read_text(encoding='utf-8'))
    tie_report = json.loads((tie_dir / 'report.json').read_text(encoding='utf-8'))
    tie_entries = {r['score']: r for r in tie_report['scores']}
    out.mkdir(parents=True); records = []
    for entry in seq_report['scores']:
        sequence_path = sequence_dir / (entry['score'] + '.json')
        tie_path = tie_dir / (entry['score'] + '.json')
        if digest(sequence_path) != entry['sha256'] or digest(tie_path) != tie_entries[entry['score']]['sha256']:
            raise ValueError('audit_hash_mismatch')
        seq = json.loads(sequence_path.read_text(encoding='utf-8')); tie = json.loads(tie_path.read_text(encoding='utf-8'))
        before = {tuple(s['segment_ids']) for s in tie['impact']['before']}
        after = {tuple(s['segment_ids']) for s in tie['impact']['source_graph']['sounds']}
        changed_segments = {i for group in before ^ after for i in group}
        selected = [r for r in seq['observations'] if r['previously_unresolved'] or
                    'onset_in_measure' in r['proposed_changes'] or r['fingerprint'] in changed_segments]
        if not selected: continue
        measure_indices = {max(1, r['original']['measure_index'] + delta) for r in selected for delta in (-1, 0, 1)}
        source = Path(seq['identity']['score_source_path'])
        if digest(source) != seq['identity']['score_sha256']: raise ValueError('source_changed')
        root = ET.parse(source).getroot()
        for el in root.iter(): el.tag = el.tag.rsplit('}', 1)[-1]
        context = []
        for part in root.findall('part'):
            for index, measure in enumerate(part.findall('measure'), 1):
                if index in measure_indices:
                    context.append({'source_part_id': part.get('id'), 'source_measure_index': index,
                        'printed_measure_number': measure.get('number'),
                        'xml': ET.tostring(deepcopy(measure), encoding='unicode')})
        target = out / (entry['score'] + '.json')
        write(target, {'schema_name': 'musicanote-source-identity-case', 'schema_version': '0.1.0',
            'identity': seq['identity'], 'source_sha256': digest(source),
            'input_audit_hashes': {'sequence': digest(sequence_path), 'tie': digest(tie_path)},
            'selected_event_ids': [r['event_id'] for r in selected],
            'context_xml_measures': context,
            'context_event_provenance': [r for r in seq['observations'] if r['original']['measure_index'] in measure_indices],
            'old_tie_groups': [s for s in tie['impact']['before'] if set(s['segment_ids']) & changed_segments],
            'proposed_tie_groups': [s for s in tie['impact']['source_graph']['sounds'] if set(s['segment_ids']) & changed_segments],
            'open_grace_tie_issues': tie['impact']['source_graph']['issues'],
            'status': 'parser_evidence_not_musical_gold_not_published',
            'rendering_contract': 'Original full source is authoritative. XML measure excerpts may require inherited divisions/key/clef; do not parse them as a standalone score.'})
        records.append({'score': entry['score'], 'selected_events': len(selected), 'context_measures': len(context),
                        'case_file': str(target.resolve()), 'sha256': digest(target)})
    result = {'cases': records, 'case_count': len(records), 'production_modified': False,
              'code_sha256': digest(Path(__file__))}
    write(out / 'index.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--sequence-audit', required=True)
    parser.add_argument('--tie-audit', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(); print(json.dumps(build(args.sequence_audit, args.tie_audit, args.output), indent=2))
