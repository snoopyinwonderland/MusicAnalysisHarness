"""Whitelist-only, read-only research reference for an arrangement consumer.

Never export target/evaluation/annotation labels. Research winner selection
does NOT imply operational adoption, human validation, or permission to use
the hypothesis as a hard generative constraint. No harmony function is guessed.
"""
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json

VERSION = '0.1.0'
SCHEMA = 'musicanote-harmony-arrangement-reference'
ALLOWED_ARMS = ('fresh', 'previous_context', 'frozen_old26')
UNAVAILABLE = ('roman', 'function', 'local_tonic', 'inversion', 'cadence',
               'confirmed_nct', 'semantic_voice_role', 'accompaniment_style')


def fraction(v):
    if (not isinstance(v, dict) or set(v) != {'numerator', 'denominator'}
            or type(v['numerator']) is not int or type(v['denominator']) is not int or v['denominator'] <= 0):
        raise ValueError('invalid_arrangement_rational')
    return F(v['numerator'], v['denominator'])


def rational(v):
    return {'numerator': v.numerator, 'denominator': v.denominator}


def span(value):
    a, b = fraction(value['start']), fraction(value['end'])
    if not 0 <= a < b:
        raise ValueError('invalid_arrangement_scope')
    return a, b


def spelling(value, *, nullable=False):
    if value is None and nullable:
        return None
    if (not isinstance(value, (tuple, list)) or len(value) != 2 or value[0] not in tuple('ABCDEFG')
            or type(value[1]) is not int):
        raise ValueError('unsupported_arrangement_spelling')
    return {'step': value[0], 'alter': rational(F(value[1]))}


def absolute_tpc(pitch):
    """musicomp uses C=0 absolute fifths; NOT MuseScore's C=14 offset."""
    if pitch is None:
        return None
    alter = fraction(pitch['alter'])
    if alter.denominator != 1:
        raise ValueError('microtonal_musicomp_tpc_not_supported')
    return {'F': -1, 'C': 0, 'G': 1, 'D': 2, 'A': 3, 'E': 4, 'B': 5}[pitch['step']]+7*alter.numerator


def harmonic_runs(ids, graph, source_ir, scope):
    """Reconstruct union runs from ORIGINAL candidate edges, not reference labels."""
    if not ids or len(ids) > graph['max_segments'] or len(set(ids)) != len(ids):
        raise ValueError('invalid_arrangement_path')
    edges = {e['group_id']: e for e in graph['edges']}
    if len(edges) != len(graph['edges']):
        raise ValueError('duplicate_arrangement_edge_id')
    sounds = {s['sounding_event_id']: s for s in source_ir['sounding_events']}
    notes = {n['note_id'] for n in source_ir['note_events']}
    a, end = span(scope); cursor = a; runs = []; previous = None
    for identifier in ids:
        if identifier not in edges:
            raise ValueError('arrangement_path_edge_missing')
        e = edges[identifier]; start, stop = span({'start': e['start'], 'end': e['end']})
        if start != cursor or stop > end:
            raise ValueError('arrangement_noncontiguous_path')
        signature = json.dumps(e['signature'], separators=(',', ':'))
        root, members = e['signature']; root = spelling(root, nullable=True)
        members = [spelling(m) for m in members]
        event_ids = sorted(set(e['source_event_ids']))
        if any(i not in sounds or not set(sounds[i]['source_note_ids']) <= notes for i in event_ids):
            raise ValueError('arrangement_source_event_missing')
        if any(not (fraction(sounds[i]['span']['start']) < stop and start < fraction(sounds[i]['span']['end'])) for i in event_ids):
            raise ValueError('arrangement_source_event_not_in_span')
        if signature == previous:
            runs[-1]['span']['end'] = rational(stop)
            runs[-1]['source_sounding_event_ids'] = sorted(set(runs[-1]['source_sounding_event_ids']) | set(event_ids))
        else:
            runs.append({'span': {'start': rational(start), 'end': rational(stop)},
                         'analysis_root': root, 'member_spellings': members,
                         'source_sounding_event_ids': event_ids})
        cursor, previous = stop, signature
    if cursor != end:
        raise ValueError('arrangement_path_does_not_cover_scope')
    for run in runs:
        run['source_note_ids'] = sorted({n for i in run['source_sounding_event_ids'] for n in sounds[i]['source_note_ids']})
        root = absolute_tpc(run['analysis_root']); tones = [absolute_tpc(m) for m in run['member_spellings']]
        if root in tones:
            tones = [root, *(v for v in tones if v != root)]
        run['musicomp_candidate'] = {'start': str(fraction(run['span']['start'])),
                                    'end': str(fraction(run['span']['end'])),
                                    'root_absolute_tpc': root, 'tones_absolute_tpc': tones,
                                    'bass_absolute_tpc': None, 'key': None, 'rn': None, 'function': None,
                                    'margin': None, 'source': 'experimental_analysis',
                                    'root_is_literal_member': root is not None and root in tones,
                                    'chordspan_ready': False}
    return runs


def build(packet, graph, source_ir, *, binding):
    """Caller must SHA-verify the packet, graph, model and whole source bundle."""
    required = ('case_sha256', 'model_sha256', 'scope_artifact_sha256',
                'whole_musicxml_sha256', 'whole_ir_sha256')
    if binding.get('verified') is not True or any(not isinstance(binding.get(k), str) or len(binding[k]) != 64
                or any(c not in '0123456789abcdef' for c in binding[k]) for k in required):
        raise ValueError('unverified_arrangement_binding')
    if (packet['model_sha256'] != binding['model_sha256']
            or packet['original_scope_sha256'] != binding['scope_artifact_sha256']
            or packet['full_source_paths']['whole_musicxml_sha256'] != binding['whole_musicxml_sha256']
            or packet['full_source_paths']['working_ir_sha256'] != binding['whole_ir_sha256']
            or packet['source_clock_gate']['accepted'] is not True
            or packet['source_labels_used_for_inference'] is not False):
        raise ValueError('arrangement_source_contract_mismatch')
    span(packet['sample_span']); hypotheses = []; groups = {}; fresh_id = None
    receipts = packet['post_search_cost_receipts']
    for arm in ALLOWED_ARMS:
        receipt = receipts.get(arm)
        if receipt is None:
            continue
        if receipt['source_labels_used'] is not False or receipt['target_path_created_using_labels'] is not False:
            raise ValueError('arrangement_label_conditioned_path_forbidden')
        ids = receipt['existing_path_ids']; runs = harmonic_runs(ids, graph, source_ir, packet['sample_span'])
        key = json.dumps(runs, sort_keys=True, separators=(',', ':'))
        if key not in groups:
            identity = json.dumps([source_ir['ir_document_id'], binding['whole_ir_sha256'],
                                   binding['model_sha256'], packet['sample_span'], runs],
                                  sort_keys=True, separators=(',', ':'))
            h = {'hypothesis_id': 'href_'+hashlib.sha256(identity.encode()).hexdigest()[:24],
                 'source_arms': [], 'raw_path_variants': [], 'harmonic_runs': runs,
                 'score_cost': deepcopy(receipt['cost']), 'confidence': None,
                 'unavailable_analysis': {k: None for k in UNAVAILABLE}, 'human_validated': False}
            groups[key] = h; hypotheses.append(h)
        h = groups[key]
        if fraction(h['score_cost']) != fraction(receipt['cost']):
            raise ValueError('arrangement_union_score_disagreement')
        h['source_arms'].append(arm); h['raw_path_variants'].append(list(ids))
        if arm == 'fresh':
            fresh_id = h['hypothesis_id']
    selected = packet['result'].get('selected')
    if (selected is None) != (fresh_id is None):
        raise ValueError('arrangement_winner_receipt_mismatch')
    if selected is not None and (list(receipts['fresh']['existing_path_ids']) != [s['semantic_group_ref'] for s in selected['segments']]
            or receipt_target_flag(selected) or selected['score_cost'] != receipts['fresh']['cost']):
        raise ValueError('arrangement_selected_path_mismatch')
    hypotheses.sort(key=lambda h: (fraction(h['score_cost']), h['hypothesis_id']))
    restrictions = {'local_noncommercial_research_only': True, 'production_deployment': False,
                    'external_api_transmission': False, 'checkpoint_redistribution': False,
                    'automatic_training': False, 'use_as_hard_harmony_constraints': False}
    return {'schema_name': SCHEMA, 'schema_version': VERSION,
            'sample_id': packet['sample_id'], 'score_id': source_ir['score']['score_id'],
            'ir_document_id': source_ir['ir_document_id'], 'requested_scope': deepcopy(packet['sample_span']),
            'scope_convention': '[start,end)', 'whole_score_analysis': False,
            'time_policy': {'origin': 'first_notated_measure_start', 'unit': 'quarter',
                            'pickup': 'actual_length', 'ties': 'sounding_event_union',
                            'repeats': 'not_unfolded', 'float_time': False},
            'source_ref': deepcopy(packet['full_source_paths']),
            'analysis_ref': {k: binding[k] for k in required},
            'engine_status': packet['result']['status'], 'research_selected_hypothesis_id': fresh_id,
            'hypotheses': hypotheses, 'alternatives_complete': False,
            'score_semantics': 'same_research_model_cost_lower_is_better_not_probability',
            'unresolved': selected is None, 'production_adopted': False,
            'generation_ready': False, 'read_only_reference': True, 'restrictions': restrictions,
            'warnings': ['experimental_weights_not_promoted', 'uncalibrated_cost_not_confidence',
                         'missing_local_key_function_inversion_and_cadence',
                         'source_voices_not_validated_musical_roles',
                         'no_accompaniment_pattern_realizer_in_this_export'],
            'training_target_or_evaluation_labels_exported': False}


def receipt_target_flag(selected):
    return selected.get('source_labels_used_for_selection') is not False
