"""Pure diagnostic physical-measure audit of independently verified replay rows.

No XML locator or half-open global range assigns an event to a measure here.
Membership comes from the supplied exact physical replay observation, including
zero-duration grace notes at a measure's right edge. Qualified aliases are
diagnostics, not a migration table permitting bare legacy-ID retargeting.
"""
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json

VERSION = 'source-physical-measure-audit-0.1.0'


def _bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _fraction(value):
    if isinstance(value, dict):
        n, d = value['numerator'], value['denominator']
        if type(n) is not int or type(d) is not int or d <= 0:
            raise ValueError('invalid_exact_rational')
        return Fraction(n, d)
    if not isinstance(value, (str, int, Fraction)) or isinstance(value, bool):
        raise ValueError('inexact_or_invalid_time')
    return Fraction(value)


def _ordinal(value):
    if type(value) is not int or value < 1:
        raise ValueError('invalid_physical_measure_ordinal')
    return value


def _source_part(value):
    if not isinstance(value, str) or not value:
        raise ValueError('invalid_source_part_identity')
    if '-Staff' in value:
        base, number = value.rsplit('-Staff', 1)
        if not base or not number.isdigit() or int(number) < 1:
            raise ValueError('invalid_split_staff_identity')
        return base
    return value


def _source_staff(source_part, staff):
    if type(staff['staff_number']) is not int or staff['staff_number'] < 1:
        raise ValueError('invalid_parent_staff_number')
    if '-Staff' in source_part:
        return int(source_part.rsplit('-Staff', 1)[1]), 'split_source_part_suffix'
    return staff['staff_number'], 'display_staff_number'


def _observed_staff(value):
    if not isinstance(value, str) or not value.isdigit() or int(value) < 1:
        raise ValueError('invalid_observation_source_staff')
    return int(value)


def _token(value):
    if not isinstance(value, (list, tuple)) or len(value) != 5:
        raise ValueError('invalid_observation_token')
    local, duration, pitch, grace, tie = value
    local, duration = _fraction(local), _fraction(duration)
    if local < 0 or duration < 0 or type(grace) is not bool:
        raise ValueError('invalid_observation_geometry')
    if pitch is not None:
        if not isinstance(pitch, (list, tuple)) or len(pitch) != 3:
            raise ValueError('invalid_observation_pitch')
        step, alter, octave = pitch
        if not isinstance(step, str) or step not in tuple('ABCDEFG') or type(octave) is not int:
            raise ValueError('invalid_observation_pitch')
        pitch = (step, _fraction(alter), octave)
    if tie not in ('none', 'start', 'stop', 'continue'):
        raise ValueError('invalid_observation_tie')
    return local, duration, pitch, grace, tie


def _unique(rows, key):
    result = {}
    for row in rows:
        value = row[key]
        if value in result:
            raise ValueError('duplicate_ir_identity:' + key)
        result[value] = row
    return result


def audit(ir, source_measures, observations):
    """Audit a physical grid plus verified replay observations, without mutation.

    ``source_measures`` rows: part, measure_index (one based), label, start,
    duration. Observation rows: event_id, kind, original, parser, using the
    source_sequence_replay_audit row contract. The caller must independently
    verify whole lanes and freeze the raw-source/parent inputs. This function
    rechecks exact event geometry but cannot certify omitted raw XML events or
    independently distinguish identical occurrences in the same source lane.
    """
    before = _bytes([ir, source_measures, observations])
    result = {
        'version': VERSION, 'parent_ir_document_id': ir.get('ir_document_id'),
        'parent_content_sha256': hashlib.sha256(_bytes(ir)).hexdigest(),
        'status': 'blocked', 'blockers': [], 'grid': [], 'duplicate_measure_ids': [],
        'qualified_aliases': [], 'events': [], 'unmapped_event_ids': [], 'counts': {},
        'observation_contract': 'independently_verified_full_lane_replay_rows',
        'coverage_scope': 'parent_ir_note_rest_events',
        'source_event_cardinality_verified': False,
        'bare_measure_id_retarget_allowed': False,
        'independent_occurrence_certified': False,
        'performed_or_concert_time_verified': False,
        'core_modified': False, 'candidate_created': False,
        'annotation_retargeted': False, 'source_labels_used': False,
        'source_measure_labels_observed': True,
        'accuracy_measured': False, 'gold_promoted': False, 'training_promoted': False,
    }
    try:
        parts = _unique(ir['parts'], 'part_id')
        staffs = _unique(ir['staves'], 'staff_id')
        refs = _unique(ir['source_references'], 'source_ref_id')
        events = {}; used_refs = set()
        for kind, field, idfield in (('note', 'note_events', 'note_id'),
                                    ('rest', 'rest_events', 'rest_id')):
            for event in ir[field]:
                eid = event[idfield]
                if eid in events: raise ValueError('duplicate_event_identity')
                if event['source_ref_id'] not in refs: raise ValueError('missing_source_reference')
                if event['source_ref_id'] in used_refs: raise ValueError('shared_event_source_reference')
                used_refs.add(event['source_ref_id'])
                events[eid] = (kind, event)
        old_measures = sorted(ir['measures'], key=lambda m: m['sequential_measure_index'])
        indices = [m['sequential_measure_index'] for m in old_measures]
        if any(type(i) is not int for i in indices) or indices != list(range(len(old_measures))):
            raise ValueError('noncontiguous_or_duplicate_measure_sequence')
        by_id = defaultdict(list)
        for measure in old_measures: by_id[measure['measure_id']].append(measure)
        result['duplicate_measure_ids'] = [
            {'legacy_measure_id': mid,
             'sequential_measure_indices': [m['sequential_measure_index'] for m in rows]}
            for mid, rows in by_id.items() if len(rows) > 1]

        raw_grid = {}; source_parts = {_source_part(p['source_part_id']) for p in parts.values()}
        for row in source_measures:
            pid, ordinal = row['part'], _ordinal(row['measure_index'])
            if pid not in source_parts: raise ValueError('unexpected_source_grid_part')
            key = pid, ordinal
            if key in raw_grid: raise ValueError('duplicate_source_physical_measure')
            start, duration = _fraction(row['start']), _fraction(row['duration'])
            if start < 0 or duration < 0: raise ValueError('negative_source_measure_geometry')
            if row['label'] is not None and (not isinstance(row['label'], str) or not row['label'].strip()):
                raise ValueError('invalid_source_measure_label')
            raw_grid[key] = (row, start, duration)
        expected_grid = {(pid, i + 1) for pid in source_parts for i in indices}
        if set(raw_grid) != expected_grid: raise ValueError('incomplete_or_extra_source_physical_grid')
        for pid in sorted(source_parts):
            cursor = Fraction(0)
            for ordinal in range(1, len(old_measures) + 1):
                _, start, duration = raw_grid[pid, ordinal]
                if start != cursor: raise ValueError('noncontiguous_source_physical_grid')
                cursor += duration

        for ordinal, old in enumerate(old_measures, 1):
            rows = [raw_grid[pid, ordinal] for pid in sorted(source_parts)]
            if len({(r['label'], start, duration) for r, start, duration in rows}) != 1:
                raise ValueError('source_part_physical_grid_disagreement')
            row, start, duration = rows[0]
            if (_fraction(old['global_start_quarter']) != start or
                    _fraction(old['actual_duration_quarter']) != duration):
                raise ValueError('parent_physical_grid_time_mismatch')
            target = {'physical_measure_ordinal': ordinal,
                      'sequential_measure_index': old['sequential_measure_index']}
            result['grid'].append({**target, 'legacy_measure_id': old['measure_id'],
                'parent_printed_measure_number': old['printed_measure_number'],
                'source_measure_label': row['label'], 'global_start_quarter': str(start),
                'actual_duration_quarter': str(duration),
                'printed_label_matches': old['printed_measure_number'] == row['label']})
            result['qualified_aliases'].append({
                'key': {'legacy_measure_id': old['measure_id'],
                        'sequential_measure_index': old['sequential_measure_index']},
                'target': target, 'source_measure_label': row['label'],
                'bare_legacy_id_ambiguous': len(by_id[old['measure_id']]) > 1,
                'retarget_executable': False,
            })

        seen = set(); locators = set()
        for observation in observations:
            eid = observation['event_id']
            if eid in seen: raise ValueError('duplicate_observed_event_identity')
            seen.add(eid)
            if eid not in events: raise ValueError('unknown_observed_event_identity')
            kind, event = events[eid]
            original, parser = observation['original'], observation['parser']
            if observation['kind'] != kind or original['kind'] != kind or parser['kind'] != kind:
                raise ValueError('observation_event_kind_mismatch')
            ordinal = _ordinal(original['measure_index'])
            if ordinal != _ordinal(parser['measure_index']): raise ValueError('replay_physical_measure_disagreement')
            for key in ('part', 'staff'):
                if original[key] != parser[key]: raise ValueError('replay_source_lane_disagreement')
            for row in (original, parser):
                if row['voice'] is not None and (not isinstance(row['voice'], str) or not row['voice'].strip()):
                    raise ValueError('invalid_observation_source_voice')
            if parser['voice'] is not None and original['voice'] != parser['voice']:
                raise ValueError('replay_source_voice_disagreement')
            raw_token, parsed_token = _token(original['token']), _token(parser['token'])
            if raw_token != parsed_token: raise ValueError('replay_token_disagreement')
            if (type(original.get('chord_marker')) is not bool or
                    type(parser.get('chord_marker')) is not bool or
                    original['chord_marker'] != parser['chord_marker']):
                raise ValueError('replay_chord_geometry_disagreement')
            if _fraction(original['global_onset']) != _fraction(parser['global_onset']):
                raise ValueError('replay_global_onset_disagreement')
            if original['xpath'] in locators: raise ValueError('duplicate_verified_source_locator')
            locators.add(original['xpath'])
            part = parts[event['part_id']]; staff = staffs[event['display_staff_id']]
            if staff['part_id'] != event['part_id']: raise ValueError('parent_staff_part_disagreement')
            if _source_part(part['source_part_id']) != original['part']:
                raise ValueError('parent_source_part_disagreement')
            effective_staff, normalization = _source_staff(part['source_part_id'], staff)
            if effective_staff != _observed_staff(original['staff']):
                raise ValueError('parent_source_staff_disagreement')
            if parser['fingerprint'] != refs[event['source_ref_id']]['local_fingerprint']:
                raise ValueError('parent_replay_fingerprint_disagreement')
            row, start, duration = raw_grid[original['part'], ordinal]
            local, note_duration, pitch, grace, tie = raw_token
            if original['measure_label'] != row['label']: raise ValueError('source_grid_event_label_disagreement')
            if start + local != _fraction(original['global_onset']): raise ValueError('source_global_local_disagreement')
            if local > duration or local + note_duration > duration:
                raise ValueError('source_event_outside_physical_measure')
            if local == duration and not grace and note_duration == 0:
                raise ValueError('unsupported_non_grace_right_edge_event')
            if (_fraction(event['global_onset_quarter']) != start + local or
                    _fraction(event['notated_duration_quarter']) != note_duration):
                raise ValueError('parent_source_event_time_disagreement')
            if kind == 'note':
                p = event['written_pitch']
                if ((p['step'], _fraction(p['alter']), p['octave']) != pitch or
                        event['grace']['is_grace'] is not grace or event['tie_role'] != tie):
                    raise ValueError('parent_source_pitch_grace_tie_disagreement')
            elif pitch is not None or grace or tie != 'none': raise ValueError('invalid_rest_observation')
            old = old_measures[ordinal - 1]
            if event['measure_id'] not in by_id: raise ValueError('missing_parent_measure_reference')
            if event['measure_id'] != old['measure_id']: raise ValueError('parent_physical_measure_reference_disagreement')
            result['events'].append({'event_id': eid, 'kind': kind,
                'legacy_measure_id': event['measure_id'],
                'legacy_referenced_sequence_indices': [m['sequential_measure_index'] for m in by_id[event['measure_id']]],
                'resolved_physical_measure_ordinal': ordinal,
                'resolved_sequential_measure_index': ordinal - 1,
                'source_measure_label': row['label'],
                'parent_staff_number': staff['staff_number'],
                'source_staff_number': effective_staff,
                'source_staff_normalization': normalization,
                'parent_onset_in_measure': str(_fraction(event['onset_in_measure'])),
                'source_onset_in_measure': str(local),
                'local_onset_matches': _fraction(event['onset_in_measure']) == local,
                'global_onset_quarter': str(start + local), 'notated_duration_quarter': str(note_duration),
                'grace_at_physical_right_edge': grace and local == duration,
                'membership_basis': 'supplied_exact_physical_replay_not_global_range',
                'occurrence_status': observation.get('occurrence_status', 'not_supplied'),
                'independent_occurrence_certified': False, 'retarget_executable': False})
        result['unmapped_event_ids'] = [eid for eid in events if eid not in seen]
        result['status'] = ('complete_parent_event_mapping' if not result['unmapped_event_ids']
                            else 'partial_parent_event_mapping')
    except (KeyError, TypeError, ValueError, ZeroDivisionError, IndexError) as error:
        result['blockers'].append(str(error))
        result['status'] = 'blocked'
    verified = {r['event_id'] for r in result['events']}
    result['unmapped_event_ids'] = [r.get('note_id', r.get('rest_id'))
        for field in ('note_events', 'rest_events') for r in ir.get(field, [])
        if r.get('note_id', r.get('rest_id')) not in verified]
    counts = Counter({'notes': len(ir.get('note_events', [])), 'rests': len(ir.get('rest_events', [])),
                      'physical_measures': len(ir.get('measures', [])),
                      'duplicate_measure_id_groups': len(result['duplicate_measure_ids']),
                      'supplied_observations': len(observations), 'verified_event_memberships': len(result['events']),
                      'unmapped_parent_events': len(result['unmapped_event_ids']),
                      'printed_label_mismatches': sum(not r['printed_label_matches'] for r in result['grid']),
                      'local_onset_mismatches': sum(not r['local_onset_matches'] for r in result['events']),
                      'duplicate_id_event_memberships': sum(len(r['legacy_referenced_sequence_indices']) > 1 for r in result['events']),
                      'split_source_staff_normalizations': sum(r['source_staff_normalization'] == 'split_source_part_suffix' for r in result['events']),
                      'grace_right_edge_memberships': sum(r['grace_at_physical_right_edge'] for r in result['events'])})
    result['counts'] = dict(counts)
    result['mapping_usable_for_migration'] = False
    if _bytes([ir, source_measures, observations]) != before:
        raise ValueError('inputs_modified_during_physical_measure_audit')
    return result
