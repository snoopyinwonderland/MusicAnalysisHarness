"""Immutable, note-locator-only repair candidates; not a parser migration.

Current exact geometry mapping is rechecked against independently indexed raw
XML. No stale XPath, enumeration order or source annotation labels break ties.
All provenance and gates live in a sidecar, not untyped Canonical Core fields.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from jsonschema import Draft202012Validator, ValidationError

from .engraving import musicxml_with_canonical_ids, SOURCE_MAPPING_VERSION, XML_ID
from .source_enrichment import _written_pitch

VERSION = 'source-locator-revision-0.1.1'
SCHEMA = Path(__file__).resolve().parents[2] / 'MUSICANOTE_Canonical_Music_IR/schemas/canonical_music_ir.schema.json'
LOCATOR_FIELDS = frozenset(('source_part_id', 'source_measure_number', 'source_voice',
                           'source_staff', 'source_element_index', 'source_xpath'))
NOTATION_FIELDS = frozenset(('accidental_display', 'stem', 'beams', 'fermata', 'slurs',
                            'tuplets', 'articulations', 'time_modification'))


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _f(value):
    return Fraction(value['numerator'], value['denominator'])


def _children(node, name):
    return [child for child in node if child.tag.rsplit('}', 1)[-1] == name]


def _text(node, name, default=None):
    values = _children(node, name)
    if len(values) > 1: raise ValueError('duplicate_xml_field:' + name)
    if not values: return default
    if not values[0].text or not values[0].text.strip():
        raise ValueError('empty_xml_field:' + name)
    return values[0].text.strip()


def _one(node, name):
    values = _children(node, name)
    if len(values) > 1: raise ValueError('duplicate_xml_field:' + name)
    return values[0] if values else None


def _notation(note):
    group = _one(note, 'notations')
    nodes = list(group) if group is not None else []
    mod = _one(note, 'time-modification')
    return {
        'accidental_display': _text(note, 'accidental'), 'stem': _text(note, 'stem'),
        'beams': [{'number': b.get('number', '1'), 'value': b.text.strip() if b.text else None}
                  for b in _children(note, 'beam')],
        'fermata': any(n.tag.rsplit('}', 1)[-1] == 'fermata' for n in nodes),
        'slurs': [{'number': n.get('number', '1'), 'type': n.get('type')}
                  for n in nodes if n.tag.rsplit('}', 1)[-1] == 'slur'],
        'tuplets': [{'number': n.get('number', '1'), 'type': n.get('type')}
                    for n in nodes if n.tag.rsplit('}', 1)[-1] == 'tuplet'],
        'articulations': [n.tag.rsplit('}', 1)[-1] for container in nodes
                         if container.tag.rsplit('}', 1)[-1] == 'articulations' for n in container],
        'time_modification': {'actual_notes': int(_text(mod, 'actual-notes')),
                             'normal_notes': int(_text(mod, 'normal-notes'))} if mod is not None else None,
    }


def observations(payload):
    """Physical part/measure/note ordinals and exact local cursor, independently.

    No repeat unfolding, global offset reconstruction or concert conversion.
    Rest locators are deliberately not repaired by this pitched-note adapter.
    """
    root = ET.fromstring(payload)
    if root.tag.rsplit('}', 1)[-1] != 'score-partwise': raise ValueError('unsupported_source_layout')
    rows = {}; part_ids = set()
    for pi, part in enumerate(_children(root, 'part'), 1):
        part_id = part.get('id')
        if not part_id or part_id in part_ids: raise ValueError('duplicate_or_missing_xml_part_id')
        part_ids.add(part_id); divisions = None
        for mi, measure in enumerate(_children(part, 'measure'), 1):
            cursor = previous = Fraction(0); ni = 0
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
                elif tag == 'note':
                    ni += 1; grace = _one(node, 'grace'); chord = _one(node, 'chord') is not None
                    onset = previous if chord else cursor
                    if not chord: previous = onset
                    raw_duration = _text(node, 'duration')
                    if raw_duration is None and grace is not None: duration = Fraction(0)
                    elif raw_duration is None or divisions is None: raise ValueError('missing_xml_duration_or_divisions')
                    else: duration = Fraction(raw_duration) / divisions
                    if duration < 0: raise ValueError('negative_xml_duration')
                    pitch = _one(node, 'pitch')
                    if pitch is not None:
                        # Reject blank/duplicate fields before the lenient old pitch helper.
                        _text(pitch, 'step'); _text(pitch, 'octave'); _text(pitch, 'alter', '0')
                        roles = [t.get('type') for t in _children(node, 'tie')]
                        if len(roles) != len(set(roles)) or any(t not in ('start', 'stop') for t in roles):
                            raise ValueError('invalid_xml_tie_roles')
                        role = 'continue' if set(roles) == {'start', 'stop'} else (roles[0] if roles else 'none')
                        path = f'/score-partwise/part[{pi}]/measure[{mi}]/note[{ni}]'
                        rows[path] = {
                            'source_part_id': part_id, 'source_measure_number': measure.get('number'),
                            'source_voice': _text(node, 'voice'), 'source_staff': int(_text(node, 'staff', '1')),
                            'source_element_index': ni - 1, 'source_xpath': path,
                            'physical_measure_ordinal': mi, 'onset': onset, 'duration': duration,
                            'pitch': _written_pitch(node), 'grace': grace is not None, 'tie_role': role,
                            'mapped_note_id': node.get('id') or node.get(XML_ID),
                            'notation': _notation(node),
                            'slash': (grace.get('slash') == 'yes') if grace is not None and grace.get('slash') else None,
                        }
                    if not chord and grace is None: cursor += duration
    return rows


def _unique(rows, field):
    values = {row[field]: row for row in rows}
    if len(values) != len(rows): raise ValueError('duplicate_ir_identity:' + field)
    return values


def geometry_index(ir):
    parts = _unique(ir['parts'], 'part_id'); staffs = _unique(ir['staves'], 'staff_id')
    ordered = sorted(ir['measures'], key=lambda m: m['sequential_measure_index'])
    indices = [m['sequential_measure_index'] for m in ordered]
    if len(set(indices)) != len(indices): raise ValueError('duplicate_measure_sequence_index')
    positions = {m['measure_id']: i + 1 for i, m in enumerate(ordered)}
    measures = _unique(ir['measures'], 'measure_id')
    return {'parts': parts, 'staffs': staffs, 'measures': measures, 'positions': positions}


def _expected_geometry(note, ir, index=None):
    index = index or geometry_index(ir)
    parts, staffs, measures, positions = (index[k] for k in ('parts', 'staffs', 'measures', 'positions'))
    part = parts[note['part_id']]; source_part = part['source_part_id']
    staff = staffs[note['display_staff_id']]['staff_number']
    if '-Staff' in source_part:
        source_part, staff_number = source_part.rsplit('-Staff', 1); staff = int(staff_number)
    return {'part': source_part, 'staff': staff, 'printed': measures[note['measure_id']]['printed_measure_number'],
            'physical_measure': positions[note['measure_id']]}


def check_note(note, ref, rows, ir, index=None):
    raw = rows.get(ref.get('source_xpath'))
    if raw is None: return {'status': 'missing_locator', 'checks': {}}
    geometry = _expected_geometry(note, ir, index)
    checks = {field: ref.get(field) == raw[field] for field in LOCATOR_FIELDS}
    checks.update(written_pitch=note['written_pitch'] == raw['pitch'],
                  onset=_f(note['onset_in_measure']) == raw['onset'],
                  duration=_f(note['notated_duration_quarter']) == raw['duration'],
                  grace=note['grace']['is_grace'] == raw['grace'], tie_role=note['tie_role'] == raw['tie_role'],
                  part=geometry['part'] == raw['source_part_id'], staff=geometry['staff'] == raw['source_staff'],
                  printed_measure=geometry['printed'] == raw['source_measure_number'],
                  physical_measure=geometry['physical_measure'] == raw['physical_measure_ordinal'])
    return {'status': 'exact' if all(checks.values()) else 'mismatch', 'checks': checks,
            'source_xpath': raw['source_xpath'], 'source_grace': raw['grace'],
            'source_duration': str(raw['duration']), 'source_onset': str(raw['onset'])}


def changes(old, new, path=''):
    """Exact JSON pointers with missing distinct from JSON null."""
    if canonical_bytes(old) == canonical_bytes(new): return []
    if isinstance(old, dict) and isinstance(new, dict):
        result = []
        for key in sorted(set(old) | set(new)):
            pointer = path + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in old or key not in new:
                result.append({'pointer': pointer, 'before_present': key in old, 'after_present': key in new,
                               'before': deepcopy(old.get(key)), 'after': deepcopy(new.get(key))})
            else: result.extend(changes(old[key], new[key], pointer))
        return result
    if isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
        return [change for i, (a, b) in enumerate(zip(old, new)) for change in changes(a, b, path + '/' + str(i))]
    return [{'pointer': path, 'before_present': True, 'after_present': True,
             'before': deepcopy(old), 'after': deepcopy(new)}]


def validate_revision(old, new):
    """Allowlist over the whole document, not only a few hand-picked entities."""
    reduced = deepcopy(new); reduced['ir_document_id'] = old['ir_document_id']
    oldnotes = _unique(old['note_events'], 'note_id'); newnotes = _unique(reduced['note_events'], 'note_id')
    oldrefs = _unique(old['source_references'], 'source_ref_id'); newrefs = _unique(reduced['source_references'], 'source_ref_id')
    if set(oldnotes) != set(newnotes) or set(oldrefs) != set(newrefs): raise ValueError('forbidden_revision_change:identity_set')
    note_refs = {n['source_ref_id'] for n in oldnotes.values()}
    other_refs = {r['source_ref_id'] for r in old.get('rest_events', [])}
    if note_refs & other_refs: raise ValueError('shared_note_rest_source_ref')
    for nid, note in newnotes.items():
        # Restore only observed notation subfields and slash. Unknown extension
        # fields and expression evidence remain immutable, not a free JSON escape.
        for field in NOTATION_FIELDS:
            if field in oldnotes[nid]['notation']: note['notation'][field] = deepcopy(oldnotes[nid]['notation'][field])
            else: note['notation'].pop(field, None)
        if 'slash' in oldnotes[nid]['grace']: note['grace']['slash'] = oldnotes[nid]['grace']['slash']
        else: note['grace'].pop('slash', None)
    for rid in note_refs:
        for field in LOCATOR_FIELDS:
            if field in oldrefs[rid]: newrefs[rid][field] = deepcopy(oldrefs[rid][field])
            else: newrefs[rid].pop(field, None)
    if canonical_bytes(reduced) != canonical_bytes(old): raise ValueError('forbidden_revision_change:outside_locator_notation_allowlist')
    if new['ir_document_id'] == old['ir_document_id']: raise ValueError('revision_document_id_not_new')
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding='utf-8'))).validate(new)


def revise(old, source):
    source = Path(source); payload = source.read_bytes(); source_sha = hashlib.sha256(payload).hexdigest()
    if len(old['source_files']) != 1 or old['source_files'][0]['sha256'] != source_sha:
        raise ValueError('source_hash_mismatch')
    notes = _unique(old['note_events'], 'note_id'); refs = _unique(old['source_references'], 'source_ref_id')
    if len({n['source_ref_id'] for n in notes.values()}) != len(notes): raise ValueError('shared_note_source_ref')
    if any(n['source_ref_id'] not in refs for n in notes.values()): raise ValueError('missing_note_source_ref')
    if any(refs[n['source_ref_id']]['source_file_id'] != old['source_files'][0]['source_file_id'] for n in notes.values()):
        raise ValueError('source_file_identity_mismatch')
    report = {'version': VERSION, 'mapping_version': SOURCE_MAPPING_VERSION,
              'parent_ir_document_id': old['ir_document_id'], 'parent_ir_content_sha256': hashlib.sha256(canonical_bytes(old)).hexdigest(),
              'source_sha256': source_sha, 'source_layout': 'score-partwise',
              'status': 'blocked', 'blockers': [], 'candidate_ir_document_id': None,
              'before_checks': {}, 'after_checks': {}, 'changed_note_ids': [], 'changed_source_ref_ids': [],
              'production_modified': False, 'annotation_retargeted': False, 'gold_promoted': False,
              'training_promoted': False, 'concert_pitch_verified': False, 'global_time_reparsed': False,
              'rest_locators_rechecked': False, 'requires_explicit_revision_selection': True}
    try:
        Draft202012Validator(json.loads(SCHEMA.read_text(encoding='utf-8'))).validate(old)
        raw = observations(payload); geometry = geometry_index(old)
        report['before_checks'] = {nid: check_note(n, refs[n['source_ref_id']], raw, old, geometry) for nid, n in notes.items()}
        mapped, mapping = musicxml_with_canonical_ids(source, deepcopy(old)); report['mapping'] = mapping
        if not mapping['complete']:
            report['blockers'].append('incomplete_or_ambiguous_note_mapping'); return None, report
        mapped_rows = observations(mapped.encode('utf-8'))
        # The rendering adapter may assign IDs; every other parsed observation
        # must be exactly the independently read source observation at that path.
        def without_id(row): return {k: v for k, v in row.items() if k != 'mapped_note_id'}
        if set(raw) != set(mapped_rows) or any(without_id(raw[p]) != without_id(mapped_rows[p]) for p in raw):
            raise ValueError('mapped_xml_observation_changed')
        assignment = {row['mapped_note_id']: row for row in mapped_rows.values()}
        if len(assignment) != len(mapped_rows) or set(assignment) != set(notes): raise ValueError('mapped_note_bijection_failed')
        candidate = deepcopy(old); newrefs = {r['source_ref_id']: r for r in candidate['source_references']}
        after = {}
        for note in candidate['note_events']:
            row = assignment[note['note_id']]; ref = newrefs[note['source_ref_id']]
            ref.update({field: deepcopy(row[field]) for field in LOCATOR_FIELDS})
            after[note['note_id']] = check_note(note, ref, raw, candidate, geometry)
            note['notation'].update(deepcopy(row['notation'])); note['grace']['slash'] = row['slash']
        report['after_checks'] = after
        if any(row['status'] != 'exact' for row in after.values()):
            raise ValueError('independent_source_note_geometry_mismatch')
        report['changed_note_ids'] = [n['note_id'] for n in candidate['note_events']
                                      if canonical_bytes(n) != canonical_bytes(notes[n['note_id']])]
        report['changed_source_ref_ids'] = [r['source_ref_id'] for r in candidate['source_references']
                                            if canonical_bytes(r) != canonical_bytes(refs[r['source_ref_id']])]
        # The parent remains unchanged even when the repair is a no-op. A new
        # deterministic revision carries this audit's policy, never a random ID.
        identity = {'version': VERSION, 'mapping_version': SOURCE_MAPPING_VERSION,
                    'parent': old['ir_document_id'], 'source_sha256': source_sha, 'candidate': candidate}
        candidate['ir_document_id'] = 'ir_' + hashlib.sha256(canonical_bytes(identity)).hexdigest()[:24]
        validate_revision(old, candidate)
        if source.read_bytes() != payload: raise ValueError('source_changed_during_revision')
        report.update(status='candidate_ready', candidate_ir_document_id=candidate['ir_document_id'],
                      musical_event_contract_unchanged=True, schema_validated=True,
                      candidate_ir_content_sha256=hashlib.sha256(canonical_bytes(candidate)).hexdigest(),
                      changes=changes(old, candidate),
                      source_file_id=old['source_files'][0]['source_file_id'],
                      observed_notation_fields=sorted(NOTATION_FIELDS),
                      grace_notation_fields=['slash'],
                      logical_voice_certified=False, all_notation_certified=False,
                      annotation_policy='existing records stay on parent; changed source/notation evidence requires recheck, no automatic retarget')
        return candidate, report
    except (ValueError, KeyError, TypeError, ZeroDivisionError, ValidationError, ET.ParseError) as error:
        report['blockers'].append(str(error)); return None, report
