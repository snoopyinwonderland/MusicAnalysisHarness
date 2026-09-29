"""Replay full measure/voice sequences to recover legacy source identities.

Diagnostic sidecars only: no Core rewrite, no production mapping fallback.
Unlike a hash-sorted collision queue, this checks an entire ordered source lane
including rests, durations, spelling, ties, grace and exact local onset. Existing
IDs are reproduced from the pinned parser's traversal fingerprints.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET
import argparse
import hashlib
import json
import music21
from music21 import stream, note
from .canonical import CanonicalIRBuilder, _part_id, _staff_id, _voice_id, _iter_pitch_members, fraction, stable_id
from .voice_provenance import containing_voice
from .engraving import _tie_role
from .dcml_import import parse_score_without_imported_harmony
from .source_note_mapping_audit import write
from .cadential_six_four_audit import digest

VERSION = 'source-sequence-audit-0.1.0'


def token(onset, duration, pitch, grace, tie):
    return (str(Fraction(onset)), str(Fraction(duration)), pitch, bool(grace), tie)


def xml_rows(source):
    root = ET.parse(source).getroot()
    for el in root.iter():
        el.tag = el.tag.rsplit('}', 1)[-1]
    if root.tag != 'score-partwise':
        raise ValueError('score_partwise_required')
    rows = []; measures = {}
    for pi, part in enumerate(root.findall('part'), 1):
        divisions = 1; global_start = Fraction(0)
        for mi, measure in enumerate(part.findall('measure'), 1):
            cursor = previous = extent = Fraction(0); ni = 0
            for el in measure:
                if el.tag == 'attributes' and el.findtext('divisions'):
                    divisions = int(el.findtext('divisions'))
                elif el.tag in ('backup', 'forward'):
                    cursor += Fraction(el.findtext('duration', '0')) / divisions * (1 if el.tag == 'forward' else -1)
                    extent = max(extent, cursor)
                elif el.tag == 'note':
                    ni += 1; is_chord = el.find('chord') is not None
                    onset = previous if is_chord else cursor
                    if not is_chord: previous = onset
                    duration = Fraction(el.findtext('duration', '0')) / divisions
                    grace = el.find('grace') is not None
                    p = el.find('pitch')
                    if p is not None:
                        pitch = (p.findtext('step'), str(Fraction(p.findtext('alter', '0'))), int(p.findtext('octave')))
                    elif el.find('rest') is not None:
                        pitch = None
                    else:
                        raise ValueError('unpitched_not_supported')
                    rows.append({'part': part.get('id'), 'measure_index': mi,
                        'measure_label': measure.get('number'), 'staff': el.findtext('staff', '1'),
                        'voice': el.findtext('voice'), 'xpath': f'/score-partwise/part[{pi}]/measure[{mi}]/note[{ni}]',
                        'source_note_ordinal': ni, 'token': token(onset, duration, pitch, grace, _tie_role(el)),
                        'global_onset': str(global_start + onset)})
                    extent = max(extent, onset + duration)
                    if not is_chord and not grace: cursor += duration
            measures[(part.get('id'), mi)] = {'label': measure.get('number'), 'start': str(global_start), 'duration': str(extent)}
            global_start += extent
    return rows, measures


def parser_rows(score, source_part_mapping):
    rows = []; parts = list(score.parts)
    raw_ids = [_part_id(p, i) for i, p in enumerate(parts)]; counts = Counter(raw_ids)
    for pi, part in enumerate(parts):
        pid = raw_ids[pi] if counts[raw_ids[pi]] == 1 else f'{raw_ids[pi]}__part_{pi + 1}'
        measures = {id(m): i for i, m in enumerate(part.getElementsByClass(stream.Measure), 1)}
        split_staff = raw_ids[pi].rsplit('-Staff', 1)[1] if '-Staff' in raw_ids[pi] else None
        for ordinal, element in enumerate(part.recurse().notesAndRests):
            measure = element.getContextByClass(stream.Measure)
            if measure is None or id(measure) not in measures:
                raise ValueError('missing_containing_measure')
            old_voice = _voice_id(element); staff = _staff_id(part, element)
            onset = fraction(element.getOffsetInHierarchy(score)); duration = fraction(element.quarterLength)
            local = fraction(element.getOffsetInHierarchy(measure))
            base = {'part': source_part_mapping[raw_ids[pi]], 'measure_index': measures[id(measure)],
                'staff': split_staff or staff, 'voice': containing_voice(element)['voice'],
                'global_onset': str(onset), 'parser_measure_start': str(fraction(measure.getOffsetInHierarchy(score))),
                'legacy_voice': old_voice, 'legacy_staff': staff, 'legacy_part': pid, 'parser_ordinal': ordinal}
            if isinstance(element, note.Rest):
                fingerprint = 'rest_' + stable_id(pid, staff, old_voice, int(measure.number or 0), onset, duration, ordinal)
                rows.append({**base, 'fingerprint': fingerprint, 'kind': 'rest',
                             'token': token(local, duration, None, False, 'none')})
            else:
                for member, pitch, tie in _iter_pitch_members(element):
                    fingerprint = 'seg_' + stable_id(pid, staff, old_voice, int(measure.number or 0), onset, pitch.nameWithOctave, ordinal, member)
                    p = (pitch.step, str(Fraction(str(pitch.accidental.alter if pitch.accidental else 0))), pitch.octave)
                    rows.append({**base, 'fingerprint': fingerprint, 'kind': 'note',
                        'token': token(local, duration, p, element.duration.isGrace, tie or 'none')})
    return rows


def match_sequences(parsed, original):
    """Full ordered lane equality or abstain; never partial positional matching."""
    raw_groups = defaultdict(list); parsed_groups = defaultdict(list); rejected = []
    for r in original:
        raw_groups[(r['part'], r['measure_index'], r['staff'], r['voice'])].append(r)
    for p in parsed:
        prefix = (p['part'], p['measure_index'], p['staff'])
        choices = [key for key in raw_groups if key[:3] == prefix and (p['voice'] is None or key[3] == p['voice'])]
        if len(choices) != 1:
            rejected.append({'fingerprint': p['fingerprint'], 'reason': 'ambiguous_or_missing_source_lane'})
            continue
        parsed_groups[choices[0]].append(p)
    matches = []
    for key, group in parsed_groups.items():
        raw = raw_groups[key]
        if [p['token'] for p in group] != [r['token'] for r in raw]:
            rejected.extend({'fingerprint': p['fingerprint'], 'reason': 'full_lane_sequence_mismatch'} for p in group)
            continue
        if any(p['global_onset'] != r['global_onset'] for p, r in zip(group, raw)):
            rejected.extend({'fingerprint': p['fingerprint'], 'reason': 'global_timeline_mismatch'} for p in group)
            continue
        matches.extend((p, r) for p, r in zip(group, raw))
    if len({r['xpath'] for _, r in matches}) != len(matches):
        raise ValueError('source_locator_not_unique')
    return matches, rejected


def build(previous_audit, output):
    previous = Path(previous_audit); out = Path(output)
    if out.exists(): raise ValueError('output_exists')
    old = json.loads((previous / 'report.json').read_text(encoding='utf-8'))
    out.mkdir(parents=True)
    contract = {'version': VERSION, 'music21_version': music21.__version__,
        'prior_report_sha256': digest(previous / 'report.json'),
        'policy': 'complete_ordered_lane_exact_token_and_global_time_match',
        'code_hashes': {n: digest(Path(__file__).with_name(n)) for n in
            ('source_sequence_audit.py', 'canonical.py', 'formal_ir.py', 'dcml_import.py', 'voice_provenance.py')},
        'publication': 'diagnostic_sidecars_only', 'production_modified': False}
    write(out / 'run-contract.json', contract)
    totals = Counter(); reports = []
    for entry in old['scores']:
        folder = previous / entry['score']; repair_path = folder / 'repair.json'
        if digest(repair_path) != entry['repair_sha256']: raise ValueError('repair_hash_mismatch')
        repair = json.loads(repair_path.read_text(encoding='utf-8')); e = repair['identity']
        source = Path(e['score_source_path']); candidate = folder / 'candidate_ir.json'
        if e['split'] != 'train' or e['rights'].get('internal_research_use') is not True: raise ValueError('rights_split_gate')
        if digest(source) != e['score_sha256'] or digest(candidate) != repair['candidate_sha256']: raise ValueError('source_hash_mismatch')
        inputs = [source, candidate, repair_path, *[Path(e['package_path']) / n for n in repair['input_hashes']]]
        hashes = {str(p): digest(p) for p in inputs}
        ir = json.loads(candidate.read_text(encoding='utf-8'))
        score, _, mapping = parse_score_without_imported_harmony(source)
        legacy = CanonicalIRBuilder().build(score, source)
        parsed = parser_rows(score, mapping); original, measures = xml_rows(source)
        segments = {r['segment_id']: r for r in legacy['notated_note_segments']}
        rests = {r['rest_id']: r for r in legacy['rest_events']}
        if {p['fingerprint'] for p in parsed} != set(segments) | set(rests): raise ValueError('legacy_fingerprint_not_reproduced')
        refs = {r['source_ref_id']: r for r in ir['source_references']}
        events = {refs[n['source_ref_id']]['local_fingerprint']: n for n in ir['note_events'] + ir['rest_events']}
        if set(events) != {p['fingerprint'] for p in parsed}: raise ValueError('existing_event_identity_not_reproduced')
        matched, rejected = match_sequences(parsed, original)
        old_unresolved = set(repair['mapping']['unmatched_ir_note_ids']); observations = []; counts = Counter()
        counts['notes'] = len(ir['note_events']); counts['rests'] = len(ir['rest_events'])
        counts['previous_unresolved'] = len(old_unresolved)
        for p, r in matched:
            n = events[p['fingerprint']]; nid = n.get('note_id', n.get('rest_id')); ref = refs[n['source_ref_id']]
            def f(q): return str(Fraction(q['numerator'], q['denominator']))
            if f(n['global_onset_quarter']) != r['global_onset']: raise ValueError('existing_global_onset_changed')
            if f(n['notated_duration_quarter']) != r['token'][1]: raise ValueError('existing_duration_changed')
            if p['kind'] == 'note':
                pitch = n['written_pitch']
                if (pitch['step'], f(pitch['alter']), pitch['octave']) != r['token'][2]:
                    raise ValueError('existing_pitch_changed')
                if n['tie_role'] != r['token'][4] or n['grace']['is_grace'] != r['token'][3]:
                    raise ValueError('existing_tie_or_grace_changed')
            # Global time/part identity is reproduced independently; local onset
            # and printed labels may differ in the archived formal adapter.
            counts['matched_' + p['kind']] += 1
            counts['resolved_previous_unresolved'] += nid in old_unresolved
            changes = {}
            for field, before, after in (
                ('source_xpath', ref.get('source_xpath'), r['xpath']),
                ('source_measure_number', ref['source_measure_number'], r['measure_label']),
                ('onset_in_measure', f(n['onset_in_measure']), r['token'][0]),
                ('source_voice', ref.get('source_voice'), r['voice'])):
                if before != after: changes[field] = {'before': before, 'after': after}
            for field in changes: counts['changed_' + field] += 1
            observations.append({'event_id': nid, 'kind': p['kind'], 'fingerprint': p['fingerprint'],
                'source_ref_id': n['source_ref_id'], 'original': r, 'parser': p, 'proposed_changes': changes,
                'previously_unresolved': nid in old_unresolved,
                'basis': 'full_measure_staff_voice_sequence_and_global_time_replay'})
        counts['unresolved_events'] = len(rejected)
        counts['remaining_previous_unresolved'] = counts['previous_unresolved'] - counts['resolved_previous_unresolved']
        result = {'identity': e, 'input_hashes': hashes, 'counts': dict(counts),
            'observations': observations, 'rejected': rejected, 'core_modified': False}
        target = out / (entry['score'] + '.json'); write(target, result)
        if any(digest(p) != hashes[str(p)] for p in inputs): raise ValueError('input_modified')
        reports.append({'score': entry['score'], 'counts': dict(counts), 'sha256': digest(target)})
        totals.update(counts); print(entry['score'], dict(counts), flush=True)
    result = {'version': VERSION, 'summary': dict(totals), 'scores': reports,
        'inputs_unchanged': True, 'production_modified': False, 'contract_sha256': digest(out / 'run-contract.json')}
    write(out / 'report.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--previous-audit', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(); print(json.dumps(build(args.previous_audit, args.output)['summary'], indent=2))
