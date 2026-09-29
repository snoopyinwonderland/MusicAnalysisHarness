"""Shadow-only impact of replacing legacy voice hints with XML voice labels."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from .canonical import CanonicalIRBuilder, as_fraction
from .cadential_six_four_audit import digest
from .source_note_mapping_audit import write

VERSION = 'voice-tie-impact-0.2.1'


def source_tie_graph(segments):
    """Explicit, contiguous, mutually unique tie edges, independent of voice.

    Written time only: repeats/jumps and ambiguous unisons remain unresolved.
    Same spelled pitch and source part required; no inferred enharmonic ties.
    """
    rows = {s['segment_id']: s for s in segments}
    if len(rows) != len(segments): raise ValueError('duplicate_segment_id')
    ends = defaultdict(list); starts = defaultdict(list); grace_barriers = set()
    for s in segments:
        if as_fraction(s['end_ql']) <= as_fraction(s['onset_ql']):
            if s['tie_role'] != 'none':
                grace_barriers.add((s['part_id'], s['pitch_spelling'], as_fraction(s['onset_ql'])))
            continue
        if s['tie_role'] in ('start', 'continue'):
            ends[(s['part_id'], s['pitch_spelling'], as_fraction(s['end_ql']))].append(s['segment_id'])
        if s['tie_role'] in ('stop', 'continue'):
            starts[(s['part_id'], s['pitch_spelling'], as_fraction(s['onset_ql']))].append(s['segment_id'])
    edges = []
    for key in sorted(ends):
        if key not in grace_barriers and len(ends[key]) == 1 and len(starts.get(key, [])) == 1:
            edges.append((ends[key][0], starts[key][0]))
    successor = dict(edges); predecessor = {right: left for left, right in edges}
    sounds = []; issues = []; builder = CanonicalIRBuilder()
    for s in segments:
        sid = s['segment_id']
        if s['tie_role'] in ('start', 'continue') and sid not in successor:
            issues.append({'code': 'unresolved_source_tie_outgoing', 'segment_id': sid})
        if s['tie_role'] in ('stop', 'continue') and sid not in predecessor:
            issues.append({'code': 'unresolved_source_tie_incoming', 'segment_id': sid})
        if sid in predecessor: continue
        sound = builder._new_sounding_event(s, tied=s['tie_role'] != 'none')
        current = sid
        while current in successor:
            current = successor[current]
            sound['segment_ids'].append(current)
            sound['sounding_end_ql'] = rows[current]['end_ql']
            sound['crosses_measure_boundary'] = rows[current]['measure'] != s['measure']
        sounds.append(sound)
    sounds.sort(key=lambda s: (as_fraction(s['attack_onset_ql']), s['pitch_midi'], s['sounding_event_id']))
    return {'sounds': sounds, 'issues': issues,
        'grace_barriers': [[part, pitch, str(time)] for part, pitch, time in sorted(grace_barriers)], 'edges': [
        {'left': a, 'right': b, 'voice_changed': rows[a]['voice_id'] != rows[b]['voice_id'],
         'staff_changed': rows[a]['staff_id'] != rows[b]['staff_id']} for a, b in edges],
         'chain_problems': check_chains(sounds, segments)}


def check_chains(sounds, segments):
    by_id = {s['segment_id']: s for s in segments}; problems = []
    for sound in sounds:
        chain = [by_id[i] for i in sound['segment_ids']]
        for left, right in zip(chain, chain[1:]):
            reasons = []
            if left['end_ql'] != right['onset_ql']: reasons.append('noncontiguous')
            if left['pitch_spelling'] != right['pitch_spelling']: reasons.append('pitch_mismatch')
            if left['tie_role'] not in ('start', 'continue') or right['tie_role'] not in ('continue', 'stop'):
                reasons.append('tie_role_mismatch')
            if reasons: problems.append({'left': left['segment_id'], 'right': right['segment_id'], 'reasons': reasons})
    return problems


def impact(segments, xml_voices):
    """Keep segment identities/time/pitch; recompute only in an isolated copy."""
    proposed = deepcopy(segments)
    for s in proposed:
        if xml_voices[s['segment_id']] is None: raise ValueError('unknown_source_voice')
        s['voice_id'] = xml_voices[s['segment_id']]
    def ordered(rows):
        return sorted(rows, key=lambda s: (as_fraction(s['onset_ql']), s['part_id'], s['staff_id'], s['voice_id'], s['midi']))
    builder = CanonicalIRBuilder()
    before, before_issues = builder._sounding_events(ordered(segments))
    after, after_issues = builder._sounding_events(ordered(proposed))
    graph = source_tie_graph(ordered(proposed))
    old = {tuple(s['segment_ids']): s for s in before}; new = {tuple(s['segment_ids']): s for s in after}
    return {'before': before, 'after': after, 'source_graph': graph,
        'removed_groups': [old[k] for k in sorted(old.keys() - new.keys())],
        'added_groups': [new[k] for k in sorted(new.keys() - old.keys())],
        'before_issues': before_issues, 'after_issues': after_issues,
        'before_chain_problems': check_chains(before, segments),
        'after_chain_problems': check_chains(after, proposed)}


def build(sequence_audit, output):
    source_dir = Path(sequence_audit); out = Path(output)
    if out.exists(): raise ValueError('output_exists')
    report = json.loads((source_dir / 'report.json').read_text(encoding='utf-8'))
    out.mkdir(parents=True)
    contract = {'version': VERSION, 'sequence_report_sha256': digest(source_dir / 'report.json'),
        'code_hashes': {n: digest(Path(__file__).with_name(n)) for n in ('voice_tie_impact.py', 'canonical.py')},
        'mode': 'shadow_only_keep_all_existing_datasets',
        'cross_staff_policy': 'voice_only_baseline_keeps_staff_scope; graph_uses_input_part_scope',
        'partstaff_limit': 'legacy PartStaff IDs stay separate; graph does not merge importer-split parts',
        'grace_policy': 'any_zero_duration_tie_blocks_that_pitch_time_bucket_no_bypass'}
    write(out / 'run-contract.json', contract); totals = Counter(); scores = []
    for entry in report['scores']:
        path = source_dir / (entry['score'] + '.json')
        if digest(path) != entry['sha256']: raise ValueError('sequence_hash_mismatch')
        data = json.loads(path.read_text(encoding='utf-8'))
        for p, h in data['input_hashes'].items():
            if digest(p) != h: raise ValueError('source_input_changed')
        candidate_path = next(Path(p) for p in data['input_hashes'] if Path(p).name == 'candidate_ir.json')
        ir = json.loads(candidate_path.read_text(encoding='utf-8'))
        by_id = {n['note_id']: n for n in ir['note_events']}
        notes = [r for r in data['observations'] if r['kind'] == 'note']
        if len(notes) != len(by_id): raise ValueError('incomplete_source_mapping')
        segments = []; xml_voices = {}; id_map = {}
        for row in notes:
            n = by_id[row['event_id']]; p = row['parser']; raw = row['original']
            start = Fraction(raw['global_onset']); duration = Fraction(raw['token'][1]); seg = row['fingerprint']
            segments.append({'segment_id': seg, 'part_id': p['legacy_part'], 'staff_id': p['legacy_staff'],
                'voice_id': p['legacy_voice'], 'measure': raw['measure_index'],
                'onset_ql': str(start), 'end_ql': str(start + duration),
                'pitch_spelling': n['written_pitch']['spelling'], 'midi': n['written_pitch']['midi_pitch'],
                'tie_role': n['tie_role']})
            xml_voices[seg] = raw['voice']; id_map[seg] = n['note_id']
        result = impact(segments, xml_voices)
        expected = {tuple(s['source_note_ids']) for s in ir['sounding_events']}
        replay = {tuple(id_map[i] for i in s['segment_ids']) for s in result['before']}
        if expected != replay: raise ValueError('archival_sounding_groups_not_reproduced')
        counts = {'notes': len(notes), 'old_sounding_events': len(result['before']), 'new_sounding_events': len(result['after']),
            'removed_groups': len(result['removed_groups']), 'added_groups': len(result['added_groups']),
            'before_chain_problems': len(result['before_chain_problems']), 'after_chain_problems': len(result['after_chain_problems']),
            'before_parser_issues': len(result['before_issues']), 'after_parser_issues': len(result['after_issues'])}
        graph = result['source_graph']
        graph_groups = {tuple(s['segment_ids']) for s in graph['sounds']}
        before_groups = {tuple(s['segment_ids']) for s in result['before']}
        counts.update({'graph_sounding_events': len(graph['sounds']), 'graph_issues': len(graph['issues']),
            'graph_chain_problems': len(graph['chain_problems']),
            'graph_cross_voice_edges': sum(e['voice_changed'] for e in graph['edges']),
            'graph_cross_staff_edges': sum(e['staff_changed'] for e in graph['edges']),
            'graph_removed_groups': len(before_groups - graph_groups),
            'graph_added_groups': len(graph_groups - before_groups)})
        target = out / (entry['score'] + '.json')
        write(target, {'identity': data['identity'], 'counts': counts, 'impact': result,
            'segment_to_existing_note_id': id_map, 'source_sequence_sha256': digest(path),
            'automatic_promotion': False, 'production_modified': False})
        for p, h in data['input_hashes'].items():
            if digest(p) != h: raise ValueError('source_input_modified')
        totals.update(counts); scores.append({'score': entry['score'], 'counts': counts, 'sha256': digest(target)})
        print(entry['score'], counts, flush=True)
    final = {'version': VERSION, 'summary': dict(totals), 'scores': scores, 'production_modified': False,
        'contract_sha256': digest(out / 'run-contract.json'),
        'release_gate': 'review_changed_groups_and_chain_problems_before_new_revision'}
    write(out / 'report.json', final); return final


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--sequence-audit', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(); print(json.dumps(build(args.sequence_audit, args.output)['summary'], indent=2))
