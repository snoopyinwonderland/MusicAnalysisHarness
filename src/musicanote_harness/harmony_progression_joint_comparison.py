"""Compare complete progression proposals under one shared voice assignment.

The result is a conditional, exact-time account, not an optimizer or a harmony
verdict. Proposal search, source rights and all-part IR identity checks belong
to the caller. Stored explicit-voice relation queries are kept separate from
the sampled assignment used for NCT accounting and progression resolution.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import hashlib
from itertools import combinations
import json

from .formal_ir import q
from .harmony_joint import f
from .harmony_progression_evidence import vector
from .harmony_progression_bass import cell_role
from .harmony_progression_resolution import analyze as resolution_analyze

VERSION = 'progression-joint-comparison-0.1.0'
MAX_ASSIGNMENTS = 64
MAX_EVALUATIONS = 4096
MAX_COMPARISONS = 8192
RAW_STATES = ('member', 'nonmember_not_confirmed_nct', 'spelling_unresolved')


def _hash(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                     separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _key(choice):
    return choice['edge'], choice['reading']


def _reading(lattice, choice):
    if not isinstance(choice, dict) or set(choice) != {'edge', 'reading'}:
        raise ValueError('invalid_choice_fields')
    ei, ri = choice['edge'], choice['reading']
    if type(ei) is not int or type(ri) is not int or not 0 <= ei < len(lattice['edges']):
        raise ValueError('invalid_choice')
    edge = lattice['edges'][ei]
    if not 0 <= ri < len(edge['readings']): raise ValueError('invalid_choice')
    return edge, edge['readings'][ri]


def _validate_path(lattice, path):
    if not isinstance(path, (list, tuple)) or not path:
        raise ValueError('complete_explicit_path_required')
    cursor = 0
    for choice in path:
        edge, reading = _reading(lattice, choice)
        if edge['from'] != cursor or edge['to'] <= cursor:
            raise ValueError('invalid_path_partition')
        if reading['span'] != edge['span']:
            raise ValueError('reading_span_mismatch')
        cursor = edge['to']
    if cursor != len(lattice['plan']['points']) - 1:
        raise ValueError('incomplete_context_path')


def _inventory(proposals):
    if isinstance(proposals, dict):
        rows = proposals['proposals']
        groups = proposals.get('semantic_groups', [])
        provenance = {k: deepcopy(v) for k, v in proposals.items() if k != 'proposals'}
    elif isinstance(proposals, (list, tuple)):
        rows, groups = proposals, []
        provenance = {'status': 'explicit_proposal_inventory', 'exhaustive': False}
    else:
        raise ValueError('invalid_proposal_inventory')
    if not isinstance(rows, (list, tuple)) or not isinstance(groups, (list, tuple)):
        raise ValueError('invalid_proposal_inventory')
    ids = [r.get('proposal_id') for r in rows]
    if any(not isinstance(pid, str) or not pid for pid in ids) or len(set(ids)) != len(ids):
        raise ValueError('invalid_or_duplicate_proposal_id')
    gids = [g.get('group_id') for g in groups]
    if len(set(gids)) != len(gids): raise ValueError('duplicate_semantic_group_id')
    return rows, {g['group_id']: g for g in groups}, provenance


def _origins(lattice, proposal, groups):
    refs = proposal.get('semantic_group_refs')
    if refs is None: return [[deepcopy(c)] for c in proposal['path']]
    if len(refs) != len(proposal['path']): raise ValueError('proposal_group_length_mismatch')
    output = []
    for choice, gid in zip(proposal['path'], refs):
        if gid not in groups: raise ValueError('unknown_semantic_group')
        group = groups[gid]; edge, reading = _reading(lattice, choice)
        keys = group['origin_reading_keys']
        if not keys or choice not in keys or len(set(_key(k) for k in keys)) != len(keys):
            raise ValueError('semantic_group_missing_or_duplicate_origin')
        for key in keys:
            other_edge, other = _reading(lattice, key)
            if key['edge'] != choice['edge'] or other_edge['span'] != edge['span']:
                raise ValueError('semantic_group_cross_interval')
            for field in ('root_spelling', 'root_provenance', 'members', 'abstention_reasons', 'event_states'):
                a, b = reading.get(field), other.get(field)
                if field == 'members': a, b = sorted(map(tuple, a)), sorted(map(tuple, b))
                if a != b: raise ValueError('semantic_group_nonidentical_reading')
        output.append(deepcopy(keys))
    return output


def _bass(lattice, path, evidence):
    """Reuse one vector and the existing role API; do not recompute accounting."""
    events = {s['sounding_event_id']: s for s in lattice['events']}
    readings = [lattice['edges'][c['edge']]['readings'][c['reading']] for c in path]
    roles = []
    for cell in evidence['cells']:
        reading = next(r for r in readings if f(r['span']['start']) <= f(cell['span']['start'])
                       and f(cell['span']['end']) <= f(r['span']['end']))
        roles.append({'span': deepcopy(cell['span']), 'candidate_ref': reading['candidate_ref'],
                      'alternative_index': reading['alternative_index'],
                      **cell_role(reading, cell['lowest'], events)})
    sustained = []
    for sid, sound in sorted(events.items()):
        cells = [c for c in evidence['cells'] if sid in c['event_refs']]
        if not cells or not all(sid in c['lowest']['event_refs'] for c in cells): continue
        involved = [r for r in readings if f(r['span']['start']) < f(sound['span']['end'])
                    and f(r['span']['end']) > f(sound['span']['start'])]
        if len({tuple(sorted(map(tuple, r['members']))) for r in involved}) < 2: continue
        states = [c['membership'][sid] for c in cells]
        if 'nonmember' not in states: continue
        complete = (f(evidence['context_span']['start']) <= f(sound['span']['start'])
                    and f(sound['span']['end']) <= f(evidence['context_span']['end']))
        anchored = complete and states[0] == states[-1] == 'member'
        blockers = sorted({b for r in involved for b in r['abstention_reasons']})
        sustained.append({'event_ref': sid, 'sounding_span': deepcopy(sound['span']),
            'membership_sequence': states, 'complete_sound_in_context': complete,
            'both_ends_are_members': anchored, 'candidate_blockers': blockers,
            'status': 'anchored_sustained_bass_shape' if anchored and not blockers else 'sustained_bass_role_unresolved',
            'pedal_confirmed': False, 'sustain_pedal_inferred': False,
            'alternatives': ['pedal_role', 'suspension_or_other_ornament', 'incorrect_chord_path'],
            'withheld_reasons': ['upper_voice_harmonic_function_not_validated', 'requires_competing_path_comparison']})
    return {'bass_roles': roles, 'sustained_bass_candidates': sustained,
            'role_status_counts': dict(Counter(r['status'] for r in roles)),
            'inversion_confirmed': False, 'structural_bass_confirmed': False}


def _raw(evidence):
    totals = {state: Fraction() for state in RAW_STATES}
    names = {'member': 'member', 'nonmember': 'nonmember_not_confirmed_nct', 'unknown': 'spelling_unresolved'}
    for cell in evidence['cells']:
        duration = f(cell['span']['end']) - f(cell['span']['start'])
        for state in cell['membership'].values(): totals[names[state]] += duration
    if sum(totals.values(), Fraction()) != f(evidence['accounting']['total_note_time']):
        raise ValueError('raw_note_time_loss')
    return {state: q(value) for state, value in totals.items()}


def _missing(index, origins):
    rows = []
    for pi, keys in enumerate(origins):
        for choice in keys:
            if _key(choice) not in index: raise ValueError('missing_reading_inventory_origin')
            row = index[_key(choice)]
            rows.append({'path_index': pi, 'reading_key': deepcopy(choice),
                'candidate_ref': row['candidate_ref'], 'alternative_index': row['alternative_index'],
                'missing_members': deepcopy(row['missing_members']),
                'omission_hypothesis': deepcopy(row['omission_hypothesis']),
                'observational_competitor_reading_keys': deepcopy(row['observational_competitor_reading_keys']),
                'stored_omission_refs': deepcopy(row['stored_omission_refs']),
                'omission_exempts_foreign_notes': False})
    return rows


def _relation_index(bundle):
    index = {}
    for row in bundle.get('relation_inventory', []):
        pair = (_key(row['reading_keys']['source']), _key(row['reading_keys']['target']))
        index.setdefault(pair, []).append(row)
    return index


def _stored_relations(index, origins):
    links = []
    for i, (left_keys, right_keys) in enumerate(zip(origins, origins[1:])):
        for left in left_keys:
            for right in right_keys:
                for row in index.get((_key(left), _key(right)), []):
                    links.append({'source_path_index': i, 'target_path_index': i + 1, **deepcopy(row),
                        'voice_evidence_scope': 'stored_separate_explicit_ir_voice_pair_query',
                        'merged_with_sampled_assignment': False,
                        'whole_path_resolution_confirmed': False,
                        'witness_exempts_other_foreign_notes': False,
                        'same_semantic_pair_origin_variants_are_independent_votes': False})
    return links


def _account(bundle, proposal, assignment_ref, fixed):
    lattice = bundle['stages']['lattice']; path = proposal['path']
    evidence = vector(lattice, path, assignment_ref)
    raw = _raw(evidence)
    if 'bass' not in fixed: fixed['bass'] = _bass(lattice, path, evidence)
    bass = deepcopy(fixed['bass'])
    resolution = resolution_analyze(lattice, path, assignment_ref, reference_keys=())
    blocked = Fraction()
    for cell in evidence['cells']:
        reading = next(lattice['edges'][c['edge']]['readings'][c['reading']] for c in path
                       if f(lattice['edges'][c['edge']]['span']['start']) <= f(cell['span']['start'])
                       and f(cell['span']['end']) <= f(lattice['edges'][c['edge']]['span']['end']))
        if reading['abstention_reasons']:
            blocked += (f(cell['span']['end']) - f(cell['span']['start'])) * len(cell['event_refs'])
    return {'evaluation_id': 'joint_' + _hash([proposal['proposal_id'], assignment_ref])[:20],
        'proposal_id': proposal['proposal_id'], 'assignment_ref': assignment_ref,
        'status': 'conditional_full_path_account_not_verdict', 'evidence': evidence,
        'raw_note_time': raw, 'blocked_candidate_note_time': q(blocked),
        'bass': bass, 'sampled_assignment_resolution': resolution,
        'missing_and_omission_by_origin': deepcopy(fixed['missing_and_omission_by_origin']),
        'stored_adjacency_relations': deepcopy(fixed['stored_adjacency_relations']),
        'summary': {'segments': len(path), 'boundaries': len(evidence['boundaries']),
            'conditional_note_time': deepcopy(evidence['accounting']['note_time']),
            'total_note_time': deepcopy(evidence['accounting']['total_note_time']),
            'same_member_set_boundaries': sum(b['same_member_sets'] for b in evidence['boundaries']),
            'two_sided_differentiating_member_boundaries': sum(b['two_sided_differentiating_members'] for b in evidence['boundaries']),
            'sampled_resolution_status_counts': dict(Counter(r['status'] for r in resolution['relations']))},
        'selected': None, 'confidence_generated': False, 'confirmed_nct': False,
        'function_confirmed': False, 'harmonic_progression_confirmed': False}


def _member_trajectory(evidence):
    rows = []
    for cell in evidence['cells']:
        segment = next(s for s in evidence['segments']
                       if f(s['evaluated_span']['start']) <= f(cell['span']['start'])
                       and f(cell['span']['end']) <= f(s['evaluated_span']['end']))
        rows.append((cell['span'], tuple(sorted(map(tuple, segment['members'])))))
    return rows


def _delta(first, second):
    if first['assignment_ref'] != second['assignment_ref']:
        raise ValueError('cross_assignment_comparison_forbidden')
    a, b = first['evidence'], second['evidence']
    if a['context_span'] != b['context_span'] or a['accounting']['total_note_time'] != b['accounting']['total_note_time']:
        raise ValueError('comparison_context_or_note_time_mismatch')
    raw = {k: q(f(second['raw_note_time'][k]) - f(v)) for k, v in first['raw_note_time'].items()}
    conditional = {k: q(f(b['accounting']['note_time'][k]) - f(v)) for k, v in a['accounting']['note_time'].items()}
    first_cuts = {f(x['time']) for x in a['boundaries']}; second_cuts = {f(x['time']) for x in b['boundaries']}
    same_members = _member_trajectory(a) == _member_trajectory(b)
    return {'assignment_ref': first['assignment_ref'],
        'first_evaluation_ref': first['evaluation_id'], 'second_evaluation_ref': second['evaluation_id'],
        'first_proposal_id': first['proposal_id'], 'second_proposal_id': second['proposal_id'],
        'raw_note_time_delta_second_minus_first': raw,
        'conditional_note_time_delta_second_minus_first': conditional,
        'blocked_candidate_note_time_delta_second_minus_first': q(f(second['blocked_candidate_note_time']) - f(first['blocked_candidate_note_time'])),
        'boundary_count_delta': len(b['boundaries']) - len(a['boundaries']),
        'second_only_boundary_times': [q(t) for t in sorted(second_cuts - first_cuts)],
        'first_only_boundary_times': [q(t) for t in sorted(first_cuts - second_cuts)],
        'same_spelled_member_sets_on_all_cells': same_members,
        'raw_membership_invariant': all(f(v) == 0 for v in raw.values()),
        'conditional_accounting_invariant_under_same_assignment': all(f(v) == 0 for v in conditional.values()),
        'same_member_sets_alone_do_not_establish_change': same_members,
        'membership_gain_with_more_boundaries': f(raw['member']) > 0 and len(b['boundaries']) > len(a['boundaries']),
        'interpretation': 'membership_gain_is_not_accuracy_gain; compare_scope_and_boundaries_without_a_winner',
        'preferred': None, 'accuracy_measured': False, 'harmonic_change_confirmed': False}


def compare(bundle, proposals, max_assignments=MAX_ASSIGNMENTS,
            max_evaluations=MAX_EVALUATIONS, max_comparisons=MAX_COMPARISONS):
    """Account for every proposal x assignment, then compare within assignment.

    Search provenance and exclusions are preserved verbatim. A capped search
    never becomes exhaustive by passing this comparison. Assignment/evaluation
    budgets abstain for the whole sample; a pairwise-only budget preserves all
    calculated accounts but emits no favorite subset of comparisons.
    """
    for value in (max_assignments, max_evaluations, max_comparisons):
        if type(value) is not int or value < 1: raise ValueError('invalid_joint_comparison_budget')
    before_bundle, before_proposals = _hash(bundle), _hash(proposals)
    if isinstance(proposals, dict):
        if proposals.get('version', '').startswith('harmony-progression-search-') and 'input_bundle_content_sha256' not in proposals:
            raise ValueError('search_bundle_binding_missing')
        if 'input_bundle_content_sha256' in proposals and proposals['input_bundle_content_sha256'] != before_bundle:
            raise ValueError('search_bundle_hash_mismatch')
        if 'sample' in proposals and proposals['sample'] != bundle.get('sample'):
            raise ValueError('search_sample_mismatch')
        if proposals.get('selected') is not None: raise ValueError('selected_search_input_forbidden')
        for flag in ('source_labels_used', 'source_annotation_used', 'accuracy_measured', 'confidence_generated'):
            if proposals.get(flag, False) is not False: raise ValueError('nonblind_or_promoted_search_input:' + flag)
    for value in (bundle, bundle['stages']['lattice']):
        if value.get('selected') is not None: raise ValueError('selected_input_forbidden')
        for flag in ('source_labels_used', 'accuracy_measured', 'production_modified', 'ranking_performed', 'confidence_generated'):
            if value.get(flag, False) is not False: raise ValueError('nonblind_or_promoted_input:' + flag)
    rows, groups, provenance = _inventory(proposals)
    lattice = bundle['stages']['lattice']; assignments = lattice.get('assignments', [])
    aids = [a['assignment_id'] for a in assignments]
    if len(set(aids)) != len(aids): raise ValueError('duplicate_assignment_identity')
    planned_evaluations = len(rows) * len(assignments)
    planned_comparisons = len(rows) * (len(rows) - 1) // 2 * len(assignments)
    out = {'version': VERSION, 'status': None, 'sample': deepcopy(bundle.get('sample')),
        'input_bundle_content_sha256': before_bundle, 'input_proposals_content_sha256': before_proposals,
        'proposal_inventory': deepcopy(list(rows)), 'search_provenance': provenance,
        'assignment_inventory': deepcopy(assignments), 'evaluations': [], 'pairwise_comparisons': [],
        'plan': {'proposals': len(rows), 'assignments': len(assignments),
            'planned_evaluations': planned_evaluations, 'planned_pairwise_comparisons': planned_comparisons,
            'max_assignments': max_assignments, 'max_evaluations': max_evaluations, 'max_comparisons': max_comparisons,
            'selection': 'all emitted complete proposals x all stored assignments; comparisons only within one assignment'},
        'evaluation_inventory_complete': False, 'pairwise_comparison_inventory_complete': False,
        'comparison_scope_exhaustive_over_all_harmonies': False,
        'selected': None, 'ranking_performed': False, 'confidence_generated': False,
        'source_labels_used': False, 'accuracy_measured': False, 'production_modified': False,
        'harmonic_progression_confirmed': False, 'gate_changed': False,
        'preserved_stage_statuses': deepcopy(bundle.get('stage_statuses', {})),
        'limits': ['Search completeness applies only to its explicit emitted inventory and preserved exclusions.',
            'A sampled voice assignment is one conditional model; explanations from different assignments are never unioned.',
            'Stored direct/temporal relation queries use separate explicit-IR voice scopes and explain no extra foreign notes.',
            'Membership, duration, conditional NCT, omitted-tone assumptions and resolution are correlated evidence, not votes.',
            'A complete union of observed members is not a confirmed arpeggiation or a correct governing span.',
            'Observed lowest and conditional inversion are not verified structural bass or final inversion.',
            'Same members do not imply the same root, inversion, harmonic function or cadence.',
            'No annotation key/label, preferred path, final confidence or operating viewer is changed.']}
    if lattice['status'] != 'ready': out['status'] = 'preserved_lattice_abstention'
    else:
        origins = []
        for row in rows:
            _validate_path(lattice, row['path'])
            origins.append(_origins(lattice, row, groups))
        if not rows: out['status'] = 'no_emitted_complete_proposals'
        elif not assignments: out['status'] = 'no_stored_assignments'
        elif len(assignments) > max_assignments: out['status'] = 'assignment_budget_abstention_no_pruning'
        elif planned_evaluations > max_evaluations: out['status'] = 'evaluation_budget_abstention_no_pruning'
        else:
            reading_index = {_key(row['reading_key']): row for row in bundle['reading_inventory']}
            relation_index = _relation_index(bundle)
            fixed = [{'missing_and_omission_by_origin': _missing(reading_index, keys),
                      'stored_adjacency_relations': _stored_relations(relation_index, keys)} for keys in origins]
            for assignment in assignments:
                accounts = [_account(bundle, row, assignment['assignment_id'], context)
                            for row, context in zip(rows, fixed)]
                out['evaluations'].extend(accounts)
                if planned_comparisons <= max_comparisons:
                    out['pairwise_comparisons'].extend(_delta(a, b) for a, b in combinations(accounts, 2))
            out['evaluation_inventory_complete'] = True
            out['pairwise_comparison_inventory_complete'] = planned_comparisons <= max_comparisons
            out['status'] = ('evaluated_joint_diagnostics_not_verdict' if out['pairwise_comparison_inventory_complete'] else
                             'evaluated_paths_pairwise_budget_abstention_no_pruning')
    out['counts'] = {'executed_evaluations': len(out['evaluations']),
                     'executed_pairwise_comparisons': len(out['pairwise_comparisons']),
                     'origin_readings_not_independent_votes': sum(len(keys) for row in rows
                         for keys in ([groups[gid]['origin_reading_keys'] for gid in row.get('semantic_group_refs', [])]
                                      if row.get('semantic_group_refs') else [[c] for c in row.get('path', [])]))}
    if _hash(bundle) != before_bundle or _hash(proposals) != before_proposals:
        raise ValueError('joint_comparison_mutated_inputs')
    return out
