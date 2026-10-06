"""Bounded immutable measure-core correction, not a parser/annotation migration.

Only duplicate physical-measure identities, their printed labels, and verified
note/rest measure pointers/local onsets may change. Source locators and source
direction extensions remain immutable and explicitly parent-bound. The pure
function rechecks a frozen replay package, not the source-file bytes themselves;
the caller must verify the package/source/parent artifact hashes independently.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction
import hashlib
import json

from jsonschema import Draft202012Validator, ValidationError

from .canonical import stable_id
from .source_locator_revision import SCHEMA, canonical_bytes, changes
from .source_physical_measure_audit import audit as physical_audit

VERSION = 'source-physical-measure-revision-0.1.0'
REPLAY_VERSION = 'source-sequence-replay-audit-0.1.0'
PACKAGE_VERSION = 'source-sequence-replay-trial-0.1.0'
SOURCE_DIRECTION_NAMESPACE = 'com.musicanote.source-directions'


def _hash(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _f(value):
    return Fraction(value['numerator'], value['denominator'])


def _q(value):
    value = Fraction(value)
    return {'numerator': value.numerator, 'denominator': value.denominator}


def _equal(a, b):
    return canonical_bytes(a) == canonical_bytes(b)


def _strings(value, pointer=''):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _strings(child, pointer + '/' + key.replace('~', '~0').replace('/', '~1'))
    elif isinstance(value, list):
        for i, child in enumerate(value): yield from _strings(child, pointer + '/' + str(i))
    elif isinstance(value, str): yield pointer, value


def _recheck(parent, package):
    if package.get('version') != PACKAGE_VERSION: raise ValueError('unsupported_replay_package_version')
    for flag in ('source_labels_used', 'core_modified', 'annotation_retargeted', 'engine_recomputed'):
        if package.get(flag) is not False: raise ValueError('unsafe_replay_package_flag:' + flag)
    replay = package['replay']; entry = package['manifest_entry']; snapshot = package['parent_snapshot']
    if replay.get('version') != REPLAY_VERSION: raise ValueError('unsupported_replay_version')
    if (replay.get('status') != 'complete_replay' or replay.get('fingerprint_reproduced') is not True or
            replay.get('blockers') or replay.get('rejected') or replay.get('unmatched_source_paths')):
        raise ValueError('complete_verified_replay_required')
    for flag in ('core_modified', 'production_modified', 'annotation_retargeted', 'source_labels_used',
                 'accuracy_measured', 'independent_occurrence_certified', 'contrapuntal_identity_certified',
                 'performed_or_concert_time_verified'):
        if replay.get(flag) is not False: raise ValueError('unsafe_replay_flag:' + flag)
    if (entry['split'] not in ('train', 'dev') or
            entry['rights'].get('internal_research_use') is not True):
        raise ValueError('split_rights_gate')
    if len(parent['source_files']) != 1: raise ValueError('single_frozen_source_required')
    source_sha = parent['source_files'][0]['sha256']
    if (replay['parent_ir_document_id'] != parent['ir_document_id'] or
            replay['parent_content_sha256'] != _hash(parent) or
            entry['ir_document_id'] != parent['ir_document_id'] or
            entry['score_id'] != parent['score']['score_id']):
        raise ValueError('parent_replay_binding_mismatch')
    if source_sha != replay['source_sha256'] or source_sha != entry['score_sha256'] or source_sha != snapshot['source_xml_sha256']:
        raise ValueError('frozen_source_binding_mismatch')
    observations = replay['observations']; counts = replay['counts']
    expected = {'notes': len(parent['note_events']), 'rests': len(parent['rest_events']),
        'matched_notes': sum(o['kind'] == 'note' for o in observations),
        'matched_rests': sum(o['kind'] == 'rest' for o in observations),
        'source_events': len(observations), 'rejected_events': 0,
        'unchecked_events': 0, 'unmatched_source_events': 0}
    for key, value in expected.items():
        if type(counts.get(key)) is not int or counts[key] != value:
            raise ValueError('replay_coverage_count_mismatch:' + key)
    physical = physical_audit(parent, replay['raw_measures'], observations)
    if physical['status'] != 'complete_parent_event_mapping' or physical['blockers']:
        raise ValueError('physical_membership_recheck_blocked:' + ','.join(physical['blockers']))
    if not _equal(physical, package['physical_measure_audit']): raise ValueError('stored_physical_audit_mismatch')
    by_id = {n.get('note_id', n.get('rest_id')): n for n in parent['note_events'] + parent['rest_events']}
    refs = {r['source_ref_id']: r for r in parent['source_references']}
    lane_groups = defaultdict(list)
    for o in observations:
        n = by_id[o['event_id']]; p = o['parser']; raw = o['original']; kind = o['kind']
        if o['source_ref_id'] != n['source_ref_id'] or p['fingerprint'] != refs[n['source_ref_id']]['local_fingerprint']:
            raise ValueError('replay_source_ref_binding_mismatch')
        expected_id = ('note_' if kind == 'note' else 'rest_') + stable_id(parent['score']['score_id'], p['fingerprint'])
        if o['event_id'] != expected_id: raise ValueError('parent_event_identity_recipe_mismatch')
        if (n['part_id'] != 'part_' + stable_id(parent['score']['score_id'], p['legacy_part']) or
                n['display_staff_id'] != 'staff_' + stable_id(parent['score']['score_id'], p['legacy_part'], p['legacy_staff'])):
            raise ValueError('parent_lane_identity_recipe_mismatch')
        if Fraction(p['parser_measure_start']) + Fraction(p['token'][0]) != Fraction(p['global_onset']):
            raise ValueError('parser_global_local_time_mismatch')
        if (o['legacy_measure_id'] != n['measure_id'] or o['logical_voice_id'] != n['voice_id'] or
                o['parent_onset_in_measure'] != str(_f(n['onset_in_measure'])) or
                o['parent_local_onset_matches_source'] is not (_f(n['onset_in_measure']) == Fraction(raw['token'][0])) or
                o['source_voice_explicit'] is not (raw['voice'] is not None) or
                o.get('independent_occurrence_certified') is not False):
            raise ValueError('replay_parent_observation_metadata_mismatch')
        lane_groups[(raw['part'], raw['measure_index'], raw['staff'], raw['voice'])].append(o)
    only = missing_voice = 0
    expected_lanes = {}
    for key, rows in lane_groups.items():
        signature = lambda o: canonical_bytes([o['original']['token'], o['original']['chord_marker'], o['kind']])
        freq = Counter(signature(o) for o in rows)
        for o in rows:
            expected_status = ('reproducible_sequence_order_only' if freq[signature(o)] > 1
                               else 'unique_token_in_source_lane')
            if o['occurrence_status'] != expected_status: raise ValueError('occurrence_uncertainty_mismatch')
            only += expected_status == 'reproducible_sequence_order_only'
            missing_voice += o['original']['voice'] is None
        expected_lanes[key] = len(rows)
    lanes = replay['lanes']; seen = set()
    for lane in lanes:
        key = lane['source_part_id'], lane['physical_measure_ordinal'], lane['source_staff'], lane['source_voice']
        if key in seen or key not in expected_lanes: raise ValueError('replay_lane_inventory_mismatch')
        seen.add(key)
        if (lane['status'] != 'exact_full_sequence' or type(lane['source_events']) is not int or
                type(lane['parser_events']) is not int or
                lane['source_events'] != expected_lanes[key] or lane['parser_events'] != expected_lanes[key] or
                lane.get('contrapuntal_identity_certified') is not False):
            raise ValueError('replay_lane_inventory_mismatch')
    if seen != set(expected_lanes): raise ValueError('replay_lane_inventory_mismatch')
    for key, value in {'order_only_occurrences': only, 'matched_missing_source_voice': missing_voice,
                       'local_onset_mismatches': physical['counts']['local_onset_mismatches']}.items():
        if type(counts.get(key)) is not int or counts[key] != value: raise ValueError('replay_coverage_count_mismatch:' + key)
    return physical


def _build(parent, package):
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding='utf-8'))).validate(parent)
    physical = _recheck(parent, package)
    duplicate = {r['legacy_measure_id'] for r in physical['duplicate_measure_ids']}
    aliases = []; new = deepcopy(parent); allowed = set(); changed_ids = set()
    by_seq = {r['sequential_measure_index']: r for r in physical['grid']}
    replacements = {}
    for i, m in enumerate(parent['measures']):
        seq = m['sequential_measure_index']; row = by_seq[seq]
        if m['measure_id'] not in duplicate:
            if not row['printed_label_matches']: raise ValueError('label_change_outside_duplicate_measure_group')
            continue
        target_id = 'measure_' + stable_id(parent['ir_document_id'], VERSION, row['physical_measure_ordinal'], m['measure_id'])
        replacements[seq] = target_id; changed_ids.add(m['measure_id'])
        new['measures'][i]['measure_id'] = target_id; allowed.add('/measures/' + str(i) + '/measure_id')
        if not row['printed_label_matches']:
            new['measures'][i]['printed_measure_number'] = row['source_measure_label']
            allowed.add('/measures/' + str(i) + '/printed_measure_number')
        aliases.append({'key': {'legacy_measure_id': m['measure_id'], 'sequential_measure_index': seq},
            'physical_measure_ordinal': row['physical_measure_ordinal'], 'new_measure_id': target_id,
            'automatic_annotation_retarget': False, 'requires_explicit_revision_selection': True})
    if len({m['measure_id'] for m in new['measures']}) != len(new['measures']): raise ValueError('new_measure_id_collision')
    memberships = {r['event_id']: r for r in physical['events']}
    for field, idfield in (('note_events', 'note_id'), ('rest_events', 'rest_id')):
        for i, n in enumerate(parent[field]):
            row = memberships[n[idfield]]; seq = row['resolved_sequential_measure_index']
            if n['measure_id'] not in duplicate:
                if not row['local_onset_matches']: raise ValueError('local_change_outside_duplicate_measure_group')
                continue
            new[field][i]['measure_id'] = replacements[seq]
            allowed.add('/' + field + '/' + str(i) + '/measure_id')
            if not row['local_onset_matches']:
                new[field][i]['onset_in_measure'] = _q(row['source_onset_in_measure'])
                allowed.add('/' + field + '/' + str(i) + '/onset_in_measure')
    # Only the registered source-direction observation extension may retain
    # parent-bound measure references. Any additional Core/unknown-extension
    # reference is a blocker, never guessed from a timestamp or bare ID.
    residuals = []
    for pointer, value in _strings(parent):
        if value not in changed_ids or pointer in allowed: continue
        components = pointer.split('/')
        if (len(components) == 7 and components[1] == 'extensions' and components[3:5] == ['payload', 'directions'] and
                components[-1] == 'measure_id'):
            extension = parent['extensions'][int(components[2])]
            if (extension.get('name') == SOURCE_DIRECTION_NAMESPACE and extension.get('version') == '0.1.0' and
                    extension.get('owner') == 'musicanote-parser' and
                    extension.get('schema_uri') == 'https://schemas.musicanote.com/extensions/source-directions/0.1.0'):
                residuals.append({'json_pointer': pointer, 'value': value,
                    'parent_ir_document_id': parent['ir_document_id'], 'namespace': SOURCE_DIRECTION_NAMESPACE,
                    'binding': 'preserved_parent_document_only', 'rebound': False})
                continue
        raise ValueError('additional_ambiguous_measure_reference:' + pointer)
    if not duplicate:
        return None, physical, aliases, residuals, allowed
    new['ir_document_id'] = 'ir_' + stable_id(parent['ir_document_id'], VERSION, _hash(new))
    allowed.add('/ir_document_id')
    return new, physical, aliases, residuals, allowed


def _sidecar(parent, package, candidate, physical, aliases, residuals, allowed):
    pointers = changes(parent, candidate) if candidate is not None else []
    counts = Counter({'duplicate_measure_id_groups': len(physical['duplicate_measure_ids']),
        'changed_measure_ids': len(aliases), 'changed_printed_labels': physical['counts']['printed_label_mismatches'],
        'changed_event_measure_refs': physical['counts']['duplicate_id_event_memberships'],
        'changed_local_onsets': physical['counts']['local_onset_mismatches'],
        'preserved_parent_bound_extension_refs': len(residuals),
        'order_only_occurrences_retained': package['replay']['counts']['order_only_occurrences'],
        'grace_right_edge_memberships_preserved': physical['counts']['grace_right_edge_memberships']})
    return {'version': VERSION, 'status': ('not_required' if candidate is None else
        ('candidate_core_ready_parent_bound_residuals' if residuals else 'candidate_core_ready')),
        'blockers': [], 'parent_ir_document_id': parent['ir_document_id'],
        'candidate_ir_document_id': candidate['ir_document_id'] if candidate is not None else None,
        'parent_content_sha256': _hash(parent),
        'candidate_content_sha256': _hash(candidate) if candidate is not None else None,
        'protected_projection_sha256': _hash(parent),
        'verified_replay_package_content_sha256': _hash(package),
        'physical_recheck_content_sha256': _hash(physical),
        'source_sha256': parent['source_files'][0]['sha256'],
        'parent_snapshot': deepcopy(package['parent_snapshot']), 'pair_id': package['pair_id'],
        'allowed_scope': 'note_rest_measure_core_only',
        'qualified_measure_aliases': aliases, 'json_pointer_diffs': pointers,
        'allowed_json_pointers': sorted(allowed), 'counts': dict(counts),
        'preserved_parent_bound_references': residuals,
        'extensions_content_sha256': _hash(parent.get('extensions')),
        'source_references_content_sha256': _hash(parent['source_references']),
        'source_references_residual': {'binding': 'preserved_parent_document_only',
            'locators_repaired': False, 'complete_source_locator_certification': False},
        'requires_explicit_revision_selection': True, 'bare_measure_id_retarget_allowed': False,
        'extensions_rebound': False, 'standalone_extension_consumption_allowed': False,
        'annotation_retargeted': False, 'old_analysis_rebound': False,
        'production_modified': False, 'parser_modified': False, 'schema_modified': False,
        'independent_occurrence_certified': False, 'source_file_bytes_rechecked_by_pure_function': False,
        'source_labels_used': False, 'accuracy_measured': False, 'gold_promoted': False,
        'training_promoted': False, 'production_ready': False, 'fully_portable': False,
        'verification_payload': deepcopy(package)}


def validate_revision(parent, new, sidecar):
    """Recreate exact authorized changes; sidecar cannot widen the allowlist."""
    package = sidecar['verification_payload']
    expected, physical, aliases, residuals, allowed = _build(parent, package)
    if expected is None or not _equal(new, expected): raise ValueError('forbidden_or_incorrect_physical_revision_change')
    expected_sidecar = _sidecar(parent, package, expected, physical, aliases, residuals, allowed)
    if not _equal(sidecar, expected_sidecar): raise ValueError('physical_revision_sidecar_mismatch')
    if new['ir_document_id'] == parent['ir_document_id']: raise ValueError('revision_document_id_not_new')
    reduced = deepcopy(new); reduced['ir_document_id'] = parent['ir_document_id']
    for i, old in enumerate(parent['measures']):
        reduced['measures'][i]['measure_id'] = old['measure_id']
        reduced['measures'][i]['printed_measure_number'] = old['printed_measure_number']
    for field in ('note_events', 'rest_events'):
        for i, old in enumerate(parent[field]):
            reduced[field][i]['measure_id'] = old['measure_id']
            reduced[field][i]['onset_in_measure'] = deepcopy(old['onset_in_measure'])
    if not _equal(reduced, parent): raise ValueError('protected_projection_changed')
    if any(d['pointer'] not in allowed and not any(d['pointer'].startswith(p + '/') for p in allowed)
           for d in changes(parent, new)):
        raise ValueError('outside_physical_revision_allowlist')
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding='utf-8'))).validate(new)
    return True


def revise(parent_ir, verified_replay_package):
    """Return (new immutable candidate or None, diagnostic/provenance sidecar)."""
    before = canonical_bytes([parent_ir, verified_replay_package])
    report = {'version': VERSION, 'status': 'blocked', 'blockers': [],
        'parent_ir_document_id': parent_ir.get('ir_document_id'),
        'parent_content_sha256': _hash(parent_ir), 'candidate_ir_document_id': None,
        'verified_replay_package_content_sha256': _hash(verified_replay_package),
        'allowed_scope': 'note_rest_measure_core_only', 'annotation_retargeted': False,
        'production_modified': False, 'extensions_rebound': False,
        'standalone_extension_consumption_allowed': False, 'production_ready': False}
    candidate = None
    try:
        candidate, physical, aliases, residuals, allowed = _build(parent_ir, verified_replay_package)
        proposed = _sidecar(parent_ir, verified_replay_package, candidate, physical, aliases, residuals, allowed)
        if candidate is not None: validate_revision(parent_ir, candidate, proposed)
        report = proposed
    except (ValueError, KeyError, TypeError, IndexError, ZeroDivisionError, ValidationError) as error:
        candidate = None; report['status'] = 'blocked'; report['blockers'].append(str(error))
        report['candidate_ir_document_id'] = None
    if canonical_bytes([parent_ir, verified_replay_package]) != before:
        raise ValueError('inputs_modified_during_physical_measure_revision')
    return candidate, report
