"""Read-only full note/rest replay; not an independent occurrence certification.

Reproduce the legacy parser fingerprints, then compare whole physical XML
measure/staff/voice sequences including rests, chord markers and exact time.
Identical repeated tokens retain order-only uncertainty. Old locators and voice
hints never break ties. No Canonical IR or annotation is rewritten here.
"""
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import music21
from jsonschema import Draft202012Validator, ValidationError
from .canonical import CanonicalIRBuilder, stable_id
from .dcml_import import parse_score_without_imported_harmony
from .source_sequence_audit import parser_rows, token
from .source_locator_revision import _children, _one, _text, canonical_bytes, observations, SCHEMA

VERSION = 'source-sequence-replay-audit-0.1.0'


def raw_rows(payload):
    """Strict written-score cursor; extent-based time only, never playback time.

    Measure starts are accumulated independently in each XML part. Missing
    duration/voice information is not silently inherited; an absent voice stays
    None. Empty measures/full-bar padding may disagree with the importer, in
    which case replay abstains instead of repairing time.
    """
    pitched = observations(payload)  # strict independent pitch/grace/tie probe
    root = ET.fromstring(payload); rows = []; measures = []; part_ids = set()
    for pi, part in enumerate(_children(root, 'part'), 1):
        pid = part.get('id')
        if not pid or pid in part_ids: raise ValueError('duplicate_or_missing_xml_part_id')
        part_ids.add(pid); divisions = None; global_start = Fraction(0)
        for mi, measure in enumerate(_children(part, 'measure'), 1):
            cursor = previous = extent = Fraction(0); ni = 0; previous_kind = None
            for node in measure:
                tag = node.tag.rsplit('}', 1)[-1]
                if tag == 'attributes' and _children(node, 'divisions'):
                    divisions = Fraction(_text(node, 'divisions'))
                    if divisions <= 0 or divisions.denominator != 1: raise ValueError('invalid_xml_divisions')
                elif tag in ('backup', 'forward'):
                    if divisions is None: raise ValueError('missing_xml_divisions')
                    duration = Fraction(_text(node, 'duration')) / divisions
                    if duration < 0: raise ValueError('negative_xml_duration')
                    cursor += duration * (1 if tag == 'forward' else -1)
                    if cursor < 0: raise ValueError('negative_xml_cursor')
                    extent = max(extent, cursor)
                elif tag == 'note':
                    ni += 1; chord = _one(node, 'chord') is not None; grace = _one(node, 'grace') is not None
                    if chord and previous_kind != 'note': raise ValueError('orphan_chord_marker')
                    onset = previous if chord else cursor
                    if not chord: previous = onset
                    text = _text(node, 'duration')
                    if text is None and grace: duration = Fraction(0)
                    elif text is None or divisions is None: raise ValueError('missing_xml_duration_or_divisions')
                    else: duration = Fraction(text) / divisions
                    if duration < 0: raise ValueError('negative_xml_duration')
                    path = f'/score-partwise/part[{pi}]/measure[{mi}]/note[{ni}]'
                    rest = _one(node, 'rest'); pitch = _one(node, 'pitch')
                    if rest is not None and (pitch is not None or grace or chord):
                        raise ValueError('unsupported_rest_geometry')
                    if rest is not None:
                        p = None; tie = 'none'; kind = 'rest'
                        if _children(node, 'tie'): raise ValueError('unsupported_rest_tie')
                    elif path in pitched:
                        raw = pitched[path]; p0 = raw['pitch']
                        p = (p0['step'], str(Fraction(p0['alter']['numerator'], p0['alter']['denominator'])), p0['octave'])
                        tie = raw['tie_role']; kind = 'note'
                    else: raise ValueError('unpitched_or_missing_pitch_not_supported')
                    staff = int(_text(node, 'staff', '1'))
                    if staff < 1: raise ValueError('nonpositive_xml_staff')
                    rows.append({'part': pid, 'measure_index': mi, 'measure_label': measure.get('number'),
                        'staff': str(staff), 'voice': _text(node, 'voice'), 'xpath': path,
                        'source_note_ordinal': ni, 'token': token(onset, duration, p, grace, tie),
                        'chord_marker': chord, 'kind': kind, 'global_onset': str(global_start + onset)})
                    extent = max(extent, onset + duration)
                    if not chord and not grace: cursor += duration
                    previous_kind = kind
            measures.append({'part': pid, 'measure_index': mi, 'label': measure.get('number'),
                             'start': str(global_start), 'duration': str(extent)})
            global_start += extent
    return rows, measures


def match_ordered_lanes(parsed, original):
    """Whole lane equality or abstain; repeated tokens are explicitly order-only.

    Containment voice may be absent only when one raw lane exists at that
    physical measure/staff. Conflicting explicit containers never fall back to
    old IR hints, old XPath, sorting by ID or a partial sequence.
    """
    raw_groups = defaultdict(list); parsed_groups = defaultdict(list); rejected = []
    for row in original: raw_groups[(row['part'], row['measure_index'], row['staff'], row['voice'])].append(row)
    for row in parsed:
        prefix = (row['part'], row['measure_index'], row['staff'])
        choices = [key for key in raw_groups if key[:3] == prefix and (row['voice'] is None or key[3] == row['voice'])]
        if len(choices) != 1:
            rejected.append({'fingerprint': row['fingerprint'], 'reason': 'ambiguous_or_missing_source_lane'})
        else: parsed_groups[choices[0]].append(row)
    matches = []; lanes = []
    def signature(row): return (row['token'], row['chord_marker'], row['kind'])
    for key, group in parsed_groups.items():
        raw = raw_groups[key]; reason = None
        if [signature(p) for p in group] != [signature(r) for r in raw]: reason = 'full_lane_sequence_mismatch'
        elif any(Fraction(p['global_onset']) != Fraction(r['global_onset']) for p, r in zip(group, raw)):
            reason = 'global_timeline_mismatch'
        if reason:
            rejected.extend({'fingerprint': p['fingerprint'], 'reason': reason} for p in group)
        else:
            frequencies = Counter(signature(r) for r in raw)
            for p, r in zip(group, raw):
                matches.append({'parser': p, 'original': r,
                    'occurrence_status': 'reproducible_sequence_order_only' if frequencies[signature(r)] > 1 else 'unique_token_in_source_lane',
                    'independent_occurrence_certified': False})
        lanes.append({'source_part_id': key[0], 'physical_measure_ordinal': key[1], 'source_staff': key[2],
            'source_voice': key[3], 'parser_events': len(group), 'source_events': len(raw),
            'status': reason or 'exact_full_sequence', 'contrapuntal_identity_certified': False})
    if len({m['original']['xpath'] for m in matches}) != len(matches): raise ValueError('source_locator_not_unique')
    return matches, rejected, lanes


def audit(old, source):
    """Reproduce parent IDs and musical material, retaining every exclusion."""
    source = Path(source); payload = source.read_bytes(); old_bytes = canonical_bytes(old)
    sha = hashlib.sha256(payload).hexdigest()
    if len(old['source_files']) != 1 or old['source_files'][0]['sha256'] != sha: raise ValueError('source_hash_mismatch')
    result = {'version': VERSION, 'music21_version': music21.__version__, 'source_sha256': sha,
        'parent_ir_document_id': old['ir_document_id'], 'parent_content_sha256': hashlib.sha256(old_bytes).hexdigest(),
        'status': 'blocked', 'blockers': [], 'observations': [], 'rejected': [], 'lanes': [], 'raw_measures': [],
        'counts': {'notes': len(old['note_events']), 'rests': len(old['rest_events']),
                   'unchecked_events': len(old['note_events']) + len(old['rest_events'])},
        'fingerprint_reproduced': False, 'core_modified': False, 'production_modified': False,
        'annotation_retargeted': False, 'source_labels_used': False, 'accuracy_measured': False,
        'independent_occurrence_certified': False, 'contrapuntal_identity_certified': False,
        'performed_or_concert_time_verified': False}
    try:
        Draft202012Validator(json.loads(SCHEMA.read_text(encoding='utf-8'))).validate(old)
        original, measures = raw_rows(payload); result['raw_measures'] = measures
        result['counts']['source_events'] = len(original)
        score, _, part_mapping = parse_score_without_imported_harmony(source)
        parsed = parser_rows(score, part_mapping); legacy = CanonicalIRBuilder().build(score, source)
        material = {r['segment_id']: r for r in legacy['notated_note_segments']}
        material.update({r['rest_id']: r for r in legacy['rest_events']})
        if len(material) != len(legacy['notated_note_segments']) + len(legacy['rest_events']): raise ValueError('duplicate_replayed_fingerprint')
        fingerprints = [p['fingerprint'] for p in parsed]
        if len(set(fingerprints)) != len(fingerprints) or set(fingerprints) != set(material):
            raise ValueError('legacy_fingerprint_not_reproduced')
        refs = {r['source_ref_id']: r for r in old['source_references']}
        if len(refs) != len(old['source_references']): raise ValueError('duplicate_source_ref_id')
        events = {}; event_ids = set(); used_refs = set()
        for n in old['note_events'] + old['rest_events']:
            eid = n.get('note_id', n.get('rest_id')); rid = n['source_ref_id']
            if eid in event_ids or rid in used_refs: raise ValueError('duplicate_event_or_shared_source_ref')
            event_ids.add(eid); used_refs.add(rid); ref = refs[rid]; fp = ref['local_fingerprint']
            if fp in events: raise ValueError('duplicate_parent_fingerprint')
            if ref['source_file_id'] != old['source_files'][0]['source_file_id']: raise ValueError('source_file_identity_mismatch')
            events[fp] = n
        if set(events) != set(fingerprints): raise ValueError('parent_fingerprint_not_reproduced')
        staffs = {s['staff_id']: s for s in old['staves']}
        parts = {p['part_id']: p for p in old['parts']}
        if len(staffs) != len(old['staves']) or len(parts) != len(old['parts']): raise ValueError('duplicate_part_or_staff_identity')
        def f(q): return Fraction(q['numerator'], q['denominator'])
        for p in parsed:
            fp = p['fingerprint']; n = events[fp]; m = material[fp]; kind = p['kind']
            expected = ('note_' if kind == 'note' else 'rest_') + stable_id(old['score']['score_id'], fp)
            if n.get('note_id', n.get('rest_id')) != expected: raise ValueError('event_identity_recipe_mismatch')
            if n['part_id'] != 'part_' + stable_id(old['score']['score_id'], p['legacy_part']): raise ValueError('parent_part_identity_mismatch')
            if n['display_staff_id'] != 'staff_' + stable_id(old['score']['score_id'], p['legacy_part'], p['legacy_staff']):
                raise ValueError('parent_staff_identity_mismatch')
            if f(n['global_onset_quarter']) != Fraction(p['global_onset']) or f(n['notated_duration_quarter']) != Fraction(p['token'][1]):
                raise ValueError('parent_event_time_changed')
            if kind == 'note':
                pitch = n['written_pitch']
                if (pitch['step'], str(f(pitch['alter'])), pitch['octave']) != p['token'][2] or pitch['spelling'] != m['pitch_spelling']:
                    raise ValueError('parent_event_pitch_changed')
                if pitch['midi_pitch'] != m['midi'] or n['tie_role'] != p['token'][4] or n['grace']['is_grace'] is not p['token'][3]:
                    raise ValueError('parent_event_pitch_tie_or_grace_changed')
                p['chord_marker'] = m.get('chord_member_index') is not None and m['chord_member_index'] > 0
            else:
                if 'rest_id' not in n or 'note_id' in n: raise ValueError('parent_event_kind_changed')
                p['chord_marker'] = False
            # Source part mapping is checked using parser lineage, not old ref hints.
            if parts[n['part_id']]['source_part_id'] not in (p['part'], p['part'] + '-Staff' + p['staff']):
                raise ValueError('source_part_lineage_mismatch')
            if staffs[n['display_staff_id']]['part_id'] != n['part_id']: raise ValueError('staff_part_membership_mismatch')
        result['fingerprint_reproduced'] = True
        matched, rejected, lanes = match_ordered_lanes(parsed, original)
        result['lanes'] = lanes; result['rejected'] = rejected
        rows = []
        for match in matched:
            p, r = match['parser'], match['original']; n = events[p['fingerprint']]
            rows.append({**match, 'event_id': n.get('note_id', n.get('rest_id')), 'kind': p['kind'],
                'source_ref_id': n['source_ref_id'], 'legacy_measure_id': n['measure_id'], 'logical_voice_id': n['voice_id'],
                'parent_onset_in_measure': str(f(n['onset_in_measure'])),
                'parent_local_onset_matches_source': f(n['onset_in_measure']) == Fraction(r['token'][0]),
                'source_voice_explicit': r['voice'] is not None})
        result['observations'] = rows
        matched_fp = {r['parser']['fingerprint'] for r in rows}; rejected_fp = {r['fingerprint'] for r in rejected}
        if matched_fp & rejected_fp or matched_fp | rejected_fp != set(fingerprints) or len(rejected_fp) != len(rejected):
            raise ValueError('replay_event_partition_mismatch')
        used = {r['original']['xpath'] for r in rows}; source_excluded = [r['xpath'] for r in original if r['xpath'] not in used]
        result['unmatched_source_paths'] = source_excluded
        counts = Counter(result['counts']); counts['unchecked_events'] = 0
        counts.update({'matched_notes': sum(r['kind'] == 'note' for r in rows),
            'matched_rests': sum(r['kind'] == 'rest' for r in rows), 'rejected_events': len(rejected),
            'unmatched_source_events': len(source_excluded), 'order_only_occurrences': sum(r['occurrence_status'] == 'reproducible_sequence_order_only' for r in rows),
            'local_onset_mismatches': sum(not r['parent_local_onset_matches_source'] for r in rows),
            'matched_missing_source_voice': sum(not r['source_voice_explicit'] for r in rows)})
        result['counts'] = dict(counts)
        result['status'] = 'complete_replay' if not rejected and not source_excluded else 'partial_replay'
    except (ValueError, KeyError, TypeError, ZeroDivisionError, ET.ParseError, ValidationError) as error:
        result['blockers'].append(str(error))
    if canonical_bytes(old) != old_bytes: raise ValueError('parent_modified_during_audit')
    if source.read_bytes() != payload: raise ValueError('source_modified_during_audit')
    return result
