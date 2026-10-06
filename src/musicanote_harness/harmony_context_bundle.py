"""Join existing, label-blind context evidence without selecting a harmony.

The inventory is an index over every stored lattice alternative, not a new
candidate provider or optimizer. Raw membership time is never reduced by a
standalone NCT shape, omitted pitch, or a witness from a different assignment.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction
import hashlib
import json

from .formal_ir import q
from .harmony_joint import f
from .harmony_catalog_resolution import pitch_pair
from .harmony_reading_voice_context import spelled_height
from .harmony_progression_context import plan, evaluate
from .harmony_progression_evidence import lowest, vector
from .harmony_progression_bass import cell_role, analyze as bass_analyze
from .harmony_progression_resolution import analyze as resolution_analyze
from .harmony_missing_evidence import run as missing_run, validate_ir, role, overlap
from .harmony_incomplete_triads import omission

VERSION = 'harmony-context-bundle-0.1.0'
STATES = ('member', 'nonmember_not_confirmed_nct', 'spelling_unresolved')


def _hash(value):
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def _key(edge, reading):
    return {'edge': edge, 'reading': reading}


def _choice(lattice, choice):
    ei, ri = choice['edge'], choice['reading']
    if type(ei) is not int or type(ri) is not int or not 0 <= ei < len(lattice['edges']):
        raise ValueError('invalid_reading_key')
    edge = lattice['edges'][ei]
    if not 0 <= ri < len(edge['readings']): raise ValueError('invalid_reading_key')
    return edge, edge['readings'][ri]


def _blind(stored):
    # Only inspect calculation flags, never read annotation keys or labels.
    for value in [stored.get('summary', {}), *stored['stages'].values()]:
        if not isinstance(value, dict): raise ValueError('invalid_stored_stage')
        for flag in ('source_labels_used', 'source_annotation_used', 'accuracy_measured',
                     'production_modified', 'ranking_performed', 'engine_recomputed'):
            if value.get(flag, False) is not False: raise ValueError('nonblind_or_promoted_stage:' + flag)
        if value.get('selected') is not None: raise ValueError('stored_stage_has_selected_verdict')


def _validate_lattice(ir, sample, lattice):
    """Check all-part material and the complete factored interval/cell universe."""
    if lattice.get('plan', {}).get('context_span') != sample['span']:
        raise ValueError('sample_context_mismatch')
    validate_ir(lattice, ir)
    if lattice['plan'] != plan(lattice['events'], sample['span']):
        raise ValueError('stored_interval_plan_mismatch')
    if lattice['status'] != 'ready': return
    expected = lattice['plan']['intervals']
    if len(lattice['edges']) != len(expected): raise ValueError('stored_interval_loss')
    for edge, interval in zip(lattice['edges'], expected):
        if any(edge[k] != interval[k] for k in ('from', 'to', 'span')):
            raise ValueError('stored_interval_origin_mismatch')
    points = lattice['plan']['points']; events = lattice['events']
    expected_cells = [{'span': {'start': a, 'end': b},
                       'event_refs': [s['sounding_event_id'] for s in events
                                      if f(s['span']['start']) < f(b) and f(s['span']['end']) > f(a)]}
                      for a, b in zip(points, points[1:])]
    if lattice['cells'] != expected_cells: raise ValueError('stored_cell_event_coverage_mismatch')
    aids = [a['assignment_id'] for a in lattice['assignments']]
    pids = [p['pattern_id'] for p in lattice['patterns']]
    if len(set(aids)) != len(aids) or len(set(pids)) != len(pids):
        raise ValueError('duplicate_assignment_or_pattern_identity')
    source = {s['sounding_event_id']: s for s in events}
    for pattern in lattice['patterns']:
        if (not set(pattern['supporting_assignment_refs']) <= set(aids) or
                not set(pattern['event_refs']) <= set(source) or
                pattern['affected_event_ref'] not in source):
            raise ValueError('unknown_pattern_assignment_or_event')
        for req in pattern['requirements']:
            if (req['event_ref'] not in source or req['state'] not in STATES or
                    not f(source[req['event_ref']]['span']['start']) <= f(req['span']['start']) <
                    f(req['span']['end']) <= f(source[req['event_ref']]['span']['end'])):
                raise ValueError('invalid_pattern_requirement')


def _pattern_links(lattice, reading):
    links = []
    for pi, pattern in enumerate(lattice['patterns']):
        if (pattern['affected_event_ref'] not in reading['event_states'] or
                not overlap(pattern['nonmember_span'], reading['span'])): continue
        local = [req for req in pattern['requirements'] if overlap(req['span'], reading['span'])]
        conflicts = [req for req in local if reading['event_states'].get(req['event_ref']) != req['state']]
        links.append({'pattern_ref': pattern['pattern_id'], 'pattern_index': pi,
            'supporting_assignment_refs': deepcopy(pattern['supporting_assignment_refs']),
            'local_requirements_consistent': not conflicts,
            'local_conflicting_requirements': deepcopy(conflicts),
            'has_requirements_outside_interval': any(
                f(req['span']['start']) < f(reading['span']['start']) or
                f(req['span']['end']) > f(reading['span']['end']) for req in pattern['requirements']),
            'withheld_reasons': deepcopy(lattice['withheld_pattern_reasons'].get(pattern['pattern_id'], [])),
            'status': 'requires_complete_path_and_shared_assignment',
            'confirmed_nct': False, 'standalone_membership_exemption': False})
    return links


def _reading_inventory(lattice):
    events = {s['sounding_event_id']: s for s in lattice['events']}
    cell_basis = []
    for ci, cell in enumerate(lattice['cells']):
        cell_basis.append({'cell_index': ci, 'span': deepcopy(cell['span']),
            'event_refs': deepcopy(cell['event_refs']),
            'observed_lowest': lowest([events[sid] for sid in cell['event_refs']])})
    rows = []; unspelled = []
    for ei, edge in enumerate(lattice['edges']):
        cells = [c for c in cell_basis if f(edge['span']['start']) <= f(c['span']['start']) and
                 f(c['span']['end']) <= f(edge['span']['end'])]
        scoped = {sid for sid, s in events.items() if overlap(s['span'], edge['span'])}
        for ri, reading in enumerate(edge['readings']):
            if reading['span'] != edge['span'] or set(reading['event_states']) != scoped:
                raise ValueError('reading_event_or_span_mismatch')
            members = {tuple(m) for m in reading['members']}
            observed = defaultdict(list); totals = {state: Fraction() for state in STATES}; bass = []
            for sid in sorted(scoped):
                sound = events[sid]
                expected = ('spelling_unresolved' if spelled_height(sound['pitch']) is None else
                            'member' if tuple(pitch_pair(sound['pitch'])) in members else 'nonmember_not_confirmed_nct')
                if reading['event_states'][sid] != expected: raise ValueError('reading_membership_mismatch')
                if expected == 'member': observed[tuple(pitch_pair(sound['pitch']))].append(sid)
            for cell in cells:
                duration = f(cell['span']['end']) - f(cell['span']['start'])
                for sid in cell['event_refs']: totals[reading['event_states'][sid]] += duration
                bass.append({'cell_index': cell['cell_index'],
                    **cell_role(reading, cell['observed_lowest'], events)})
            expected_time = sum((min(f(edge['span']['end']), f(events[sid]['span']['end'])) -
                                 max(f(edge['span']['start']), f(events[sid]['span']['start'])) for sid in scoped), Fraction())
            if sum(totals.values(), Fraction()) != expected_time: raise ValueError('reading_note_time_loss')
            foreign = sorted(sid for sid in scoped if reading['event_states'][sid] == 'nonmember_not_confirmed_nct')
            unknown = sorted(sid for sid in scoped if reading['event_states'][sid] == 'spelling_unresolved')
            missing = [list(m) for m in sorted(members) if not observed[m]]
            ordinary = {'reading_index': ri, 'candidate_ref': reading['candidate_ref'],
                'alternative_index': reading['alternative_index'], 'root_spelling': reading.get('root_spelling'),
                'members': reading['members'], 'missing_members': missing,
                'candidate_blockers': reading['abstention_reasons'], 'other_nonmember_refs': foreign + unknown}
            omission_record = omission(ordinary)
            rows.append({'reading_key': _key(ei, ri), 'candidate_ref': reading['candidate_ref'],
                'alternative_index': reading['alternative_index'], 'origin_pointer': reading['origin_pointer'],
                'provider': reading['provider'], 'display_label': reading['display_label'],
                'origin_scope': 'candidate_catalog_for_exact_interval_and_parent_context',
                'span': deepcopy(edge['span']), 'root_spelling': deepcopy(reading.get('root_spelling')),
                'root_provenance': reading.get('root_provenance'), 'members': deepcopy(reading['members']),
                'provider_missing_spellings': deepcopy(reading['missing_spellings']),
                'missing_members': [{'pitch': m, 'member_role': role(m, reading.get('root_spelling')),
                    'available_elsewhere_in_parent_event_refs': sorted(sid for sid, s in events.items()
                        if spelled_height(s['pitch']) is not None and pitch_pair(s['pitch']) == m and
                        f(s['span']['end']) > f(s['span']['start'])),
                    'omission_confirmed': False, 'boundary_extension_authorized': False} for m in missing],
                'observed_member_event_refs': [{'pitch': list(m), 'event_refs': sorted(observed[m])} for m in sorted(members)],
                'unexplained_event_refs': foreign, 'spelling_unresolved_event_refs': unknown,
                'note_time': {state: q(value) for state, value in totals.items()},
                'total_note_time': q(expected_time), 'cell_indices': [c['cell_index'] for c in cells],
                'bass_roles': bass, 'candidate_blockers': deepcopy(reading['abstention_reasons']),
                'conditional_nct_links': _pattern_links(lattice, reading),
                'omission_hypothesis': omission_record, 'observational_competitor_reading_keys': [],
                'relation_refs': [], 'stored_omission_refs': [],
                'basis': 'all_part_sounding_events_exact_cells_under_one_stored_spelled_candidate',
                'note_time_basis': 'raw_membership_only_no_standalone_nct_or_omission_exemption',
                'confirmed_nct': False, 'arpeggiation_confirmed': False, 'selected': None})
        for ui, cid in enumerate(edge['unspelled_candidate_refs']):
            unspelled.append({'edge': ei, 'candidate_ref': cid, 'origin_list_index': ui,
                'status': 'stored_candidate_without_spelling_alternative',
                'basis': 'preserved_lattice_unspelled_candidate_ref_no_root_or_members_invented'})
    groups = defaultdict(list)
    for row in rows:
        observed = tuple(tuple(m['pitch']) for m in row['observed_member_event_refs'] if m['event_refs'])
        signature = (row['reading_key']['edge'], observed, tuple(row['unexplained_event_refs']),
                     tuple(row['spelling_unresolved_event_refs']))
        groups[signature].append(row)
    for group in groups.values():
        for row in group:
            row['observational_competitor_reading_keys'] = [deepcopy(other['reading_key']) for other in group if other is not row]
    return rows, unspelled, cell_basis


def _relation_links(lattice, survey, missing, by_key):
    planned = survey.get('plan', {}).get('pairs', []); results = survey.get('results', [])
    if survey['status'] == 'ready' and len(results) != len(planned): raise ValueError('survey_incomplete')
    rows = []
    for qi, pair in enumerate(planned):
        keys = {}; origins = {}
        for side in ('source', 'target'):
            choice = pair[side]; _, reading = _choice(lattice, choice)
            keys[side] = deepcopy(choice)
            origins[side] = {k: deepcopy(reading.get(k)) for k in
                             ('candidate_ref', 'alternative_index', 'provider', 'origin_pointer', 'span', 'root_spelling', 'members')}
            by_key[(choice['edge'], choice['reading'])]['relation_refs'].append({'query_index': qi, 'side': side})
        item = results[qi] if qi < len(results) else None
        if item is not None:
            if item['pair'] != pair: raise ValueError('pair_plan_mismatch')
            for side in ('source', 'target'):
                if (item[side + '_candidate_ref'] != origins[side]['candidate_ref'] or
                        item[side + '_alternative_index'] != origins[side]['alternative_index']):
                    raise ValueError('candidate_origin_mismatch')
        rows.append({'query_index': qi, 'reading_keys': keys, 'origins': origins,
            'family': pair['family'], 'target_quality': pair['target_quality'],
            'status': item['status'] if item else 'planned_not_executed_under_preserved_stage_abstention',
            'direct_status': item['query']['status'] if item and item.get('query') else None,
            'temporal_status': item['temporal_query']['status'] if item and item.get('temporal_query') else None,
            'relation_data_ref': {'stage': 'relations', 'result_index': qi} if item else None,
            'missing_evidence_ref': qi if qi < len(missing['results']) else None,
            'function_confirmed': False, 'whole_chord_explanation_confirmed': False})
    return rows


def _stored_omission_links(hold_change, lattice, by_key):
    count = 0
    for ci, chain in enumerate(hold_change.get('chain_comparisons', [])):
        for table_ref, table in chain.get('interval_tables', {}).items():
            ei = table['edge_index']
            for oi, hypothesis in enumerate(table.get('omission_hypotheses', [])):
                ri = hypothesis['reading_index']; edge, reading = _choice(lattice, _key(ei, ri))
                if (table['span'] != edge['span'] or hypothesis['candidate_ref'] != reading['candidate_ref'] or
                        hypothesis['alternative_index'] != reading['alternative_index']):
                    raise ValueError('stored_omission_origin_mismatch')
                by_key[(ei, ri)]['stored_omission_refs'].append({'chain_index': ci,
                    'interval_table_ref': table_ref, 'omission_index': oi})
                count += 1
    return count


def _path_bundle(ir, lattice, request, index):
    out = {'request_index': index, 'request': deepcopy(request), 'stages': {},
           'selected': None, 'path_is_preferred': False, 'reference_key_hypotheses': []}
    if lattice['status'] != 'ready':
        return {**out, 'status': 'preserved_lattice_abstention', 'reason': lattice['status']}
    try:
        if not isinstance(request, dict) or set(request) - {'request_id', 'path', 'assignment_ref', 'evaluation_span'}:
            raise ValueError('unsupported_path_request_fields')
        path = request['path']; aid = request['assignment_ref']
        if not isinstance(path, (list, tuple)) or not path: raise ValueError('complete_explicit_path_required')
        for choice in path: _choice(lattice, choice)
        evaluate(lattice, path, aid, request.get('evaluation_span'))
    except (ValueError, KeyError, TypeError, IndexError) as error:
        return {**out, 'status': 'invalid_explicit_path_request', 'reason': str(error)}
    # All three computations use the same complete path and sampled assignment.
    # Passing ir=ir to resolution would replace this assignment with a different
    # explicit-voice model; the bundle deliberately does not union those scopes.
    out['stages']['evidence'] = vector(lattice, path, aid, request.get('evaluation_span'))
    out['stages']['bass'] = bass_analyze(lattice, path, aid, request.get('evaluation_span'))
    out['stages']['resolution'] = resolution_analyze(lattice, path, aid, reference_keys=())
    return {**out, 'status': 'explicit_path_diagnostics_not_verdict',
            'resolution_scope': 'same_supplied_sampled_assignment_full_context'}


def bundle(ir, stored_sample, path_requests=()):
    """Assemble a breadth sample and optional complete paths, without mutation.

    The caller freezes source hashes, sample provenance, rights and split.
    No source annotations or local keys are parameters. Failed integrity checks
    raise; musical/algorithmic abstentions remain attached to their own stages.
    """
    before_ir = _hash(ir); before_sample = _hash(stored_sample); before_requests = _hash(path_requests)
    _blind(stored_sample)
    stages = deepcopy(stored_sample['stages'])
    lattice = stages['lattice']; survey = stages['relations']; hold_change = stages['hold_change']
    sample = stored_sample['sample']; rows = []; unspelled = []; basis = []; relations = []; omission_refs = 0
    if 'plan' in lattice:
        _validate_lattice(ir, sample, lattice)
    elif lattice['status'] == 'ready': raise ValueError('ready_lattice_missing_plan')
    missing = missing_run(lattice, survey, ir)
    stages['missing_evidence'] = missing
    if lattice['status'] == 'ready':
        rows, unspelled, basis = _reading_inventory(lattice)
        by_key = {(r['reading_key']['edge'], r['reading_key']['reading']): r for r in rows}
        relations = _relation_links(lattice, survey, missing, by_key)
        omission_refs = _stored_omission_links(hold_change, lattice, by_key)
    paths = [_path_bundle(ir, lattice, request, i) for i, request in enumerate(path_requests)]
    statuses = {name: value.get('status', 'no_stage_status') for name, value in stages.items()}
    counts = Counter({'stored_edges': len(lattice.get('edges', [])), 'stored_readings': sum(len(e['readings']) for e in lattice.get('edges', [])),
        'indexed_readings': len(rows), 'unspelled_candidate_refs': len(unspelled), 'indexed_relation_plans': len(relations),
        'missing_evidence_results': len(missing['results']), 'stored_omission_links': omission_refs,
        'explicit_path_requests': len(paths)})
    if lattice['status'] == 'ready' and counts['stored_readings'] != counts['indexed_readings']:
        raise ValueError('candidate_inventory_loss')
    result = {'version': VERSION, 'status': 'assembled_diagnostics_not_harmonic_readiness',
        'parent_ir_document_id': ir.get('ir_document_id'), 'score_id': ir.get('score', {}).get('score_id'),
        'input_ir_content_sha256': before_ir, 'input_sample_content_sha256': before_sample,
        'sample': deepcopy(sample), 'stored_summary': deepcopy(stored_sample.get('summary', {})),
        'stages': stages, 'stage_statuses': statuses, 'cell_basis': basis,
        'reading_inventory': rows, 'unspelled_candidates': unspelled, 'relation_inventory': relations,
        'explicit_paths': paths, 'counts': dict(counts), 'selected': None,
        'ranking_performed': False, 'confidence_generated': False, 'harmonic_analysis_confirmed': False,
        'source_labels_used': False, 'production_modified': False, 'annotation_retargeted': False,
        'gate_changed': False, 'core_modified': False, 'accuracy_measured': False,
        'preserved_stage_abstentions': [name for name, status in statuses.items() if status not in ('ready', 'evaluated')],
        'limits': ['Inventory completeness covers stored alternatives, not all possible harmonies or score-wide optimal paths.',
            'Raw membership note-time, NCT conditions and omission assumptions are correlated evidence, not independent votes.',
            'Same pitch-class content is not used to deduplicate different origins or enharmonic spellings.',
            'Pattern links alone explain no note: a complete path and one shared assignment are still required.',
            'Observed lowest pitch and conditional inversion are not structural bass or confirmed inversion.',
            'Relation witnesses explain only their stated constraints, not every chord constituent or foreign tone.',
            'Stored budgets, unsupported grace/voice/quality cases and all original stage data remain preserved.',
            'Source rights/split/hash and independent occurrence masks belong to the caller frozen contract; no promotion here.',
            'No automatic path, key, cadence, final confidence, human label or operating viewer change.']}
    if _hash(ir) != before_ir or _hash(stored_sample) != before_sample or _hash(path_requests) != before_requests:
        raise ValueError('context_bundle_mutated_inputs')
    return result
