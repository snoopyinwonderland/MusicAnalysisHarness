"""Bounded, label-blind proposals over the complete stored interval lattice.

Search scores are proposal bookkeeping, never chord confidence.  In particular,
the local NCT bound is optimistic: a complete path and one shared assignment are
still required to explain even one foreign note in subsequent joint evaluation.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction
import hashlib
import json

from .formal_ir import q
from .harmony_joint import f

VERSION = 'harmony-progression-search-0.1.0'
STATES = ('member', 'nonmember_not_confirmed_nct', 'spelling_unresolved')


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def _hash(value):
    return hashlib.sha256(_json(value).encode('utf-8')).hexdigest()


def _key(choice):
    return choice['edge'], choice['reading']


def _union_length(intervals):
    cursor = None; total = Fraction()
    for start, end in sorted(intervals):
        if start >= end: continue
        if cursor is None or start >= cursor:
            total += end - start
        elif end > cursor:
            total += end - cursor
        cursor = end if cursor is None else max(cursor, end)
    return total


def _potential_plan(lattice):
    """Parse the fixed cell/shape geometry once, without changing any bound."""
    events = {s['sounding_event_id']: s for s in lattice['events']}
    cells = [(f(c['span']['start']), f(c['span']['end'])) for c in lattice['cells']]
    assignments = {item['assignment_id'] for item in lattice['assignments']}
    prepared = defaultdict(list)
    for pattern in lattice['patterns']:
        if lattice['withheld_pattern_reasons'].get(pattern['pattern_id']): continue
        if not assignments.intersection(pattern['supporting_assignment_refs']): continue
        sid = pattern['affected_event_ref']
        sound = events[sid]
        a = max(f(pattern['nonmember_span']['start']), f(sound['span']['start']))
        b = min(f(pattern['nonmember_span']['end']), f(sound['span']['end']))
        requirements = [(f(r['span']['start']), f(r['span']['end']), r['event_ref'], r['state'])
                        for r in pattern['requirements']]
        for ci, (ca, cb) in enumerate(cells):
            x, y = max(ca, a), min(cb, b)
            if x < y:
                local = [(event_ref, state) for ra, rb, event_ref, state in requirements if ra < cb and ca < rb]
                prepared[ci].append((sid, x, y, tuple(local), pattern['pattern_id']))
    return prepared


def _potential(prepared, cache, reading, start, end):
    """Union locally possible foreign-note spans, NOT activated NCT evidence."""
    if reading['abstention_reasons']: return Fraction(), []
    total = Fraction(); refs = set(); states = reading['event_states']
    for ci in range(start, end):
        patterns = prepared.get(ci, ())
        if not patterns: continue
        relevant = sorted({sid for sid, _, _, _, _ in patterns} |
                          {sid for _, _, _, reqs, _ in patterns for sid, _ in reqs})
        cache_key = ci, tuple((sid, states.get(sid)) for sid in relevant)
        if cache_key not in cache:
            intervals = defaultdict(list); cell_refs = set()
            for sid, x, y, requirements, pid in patterns:
                if states.get(sid) != 'nonmember_not_confirmed_nct': continue
                if any(states.get(sid) != state for sid, state in requirements): continue
                intervals[sid].append((x, y)); cell_refs.add(pid)
            cache[cache_key] = (sum((_union_length(v) for v in intervals.values()), Fraction()), cell_refs)
        length, cell_refs = cache[cache_key]; total += length; refs.update(cell_refs)
    # Different patterns/assignments may conflict. Their union is deliberately an
    # optimistic stored-vocabulary bound, never a licensed membership exemption.
    return total, sorted(refs)


def _groups(bundle):
    lattice = bundle['stages']['lattice']; groups = []; inventory = {}
    for row in bundle['reading_inventory']:
        key = _key(row['reading_key'])
        if key in inventory: raise ValueError('duplicate_inventory_reading')
        inventory[key] = row
    expected = {(ei, ri) for ei, e in enumerate(lattice['edges']) for ri in range(len(e['readings']))}
    if set(inventory) != expected: raise ValueError('search_inventory_loss_or_unknown_reading')
    points = lattice['plan']['points']; cells = lattice['cells']
    cell_durations = [f(c['span']['end']) - f(c['span']['start']) for c in cells]
    potential_plan = _potential_plan(lattice); potential_cache = {}
    for ei, edge in enumerate(lattice['edges']):
        if (type(edge['from']) is not int or type(edge['to']) is not int or
                not 0 <= edge['from'] < edge['to'] < len(points) or
                edge['span'] != {'start': points[edge['from']], 'end': points[edge['to']]}):
            raise ValueError('invalid_search_edge_geometry')
        by_signature = defaultdict(list)
        for ri, reading in enumerate(edge['readings']):
            row = inventory[(ei, ri)]
            if row['span'] != edge['span'] or reading['span'] != edge['span']:
                raise ValueError('search_inventory_span_mismatch')
            if (row['members'] != reading['members'] or row['root_spelling'] != reading['root_spelling'] or
                    row['candidate_blockers'] != reading['abstention_reasons']):
                raise ValueError('search_inventory_meaning_mismatch')
            totals = {state: Fraction() for state in STATES}
            for ci in range(edge['from'], edge['to']):
                cell = cells[ci]; duration = cell_durations[ci]
                if duration <= 0: raise ValueError('invalid_search_cell_duration')
                for sid in cell['event_refs']:
                    state = reading['event_states'].get(sid)
                    if state not in totals: raise ValueError('unknown_search_membership_state')
                    totals[state] += duration
            if ({s: q(totals[s]) for s in STATES} != row['note_time'] or
                    q(sum(totals.values(), Fraction())) != row['total_note_time']):
                raise ValueError('search_note_time_mismatch')
            signature = {'edge_index': ei, 'from': edge['from'], 'to': edge['to'], 'span': edge['span'],
                'root_spelling': reading['root_spelling'], 'root_provenance': reading.get('root_provenance'),
                'members': sorted(reading['members'], key=_json),
                'candidate_blockers': sorted(reading['abstention_reasons'], key=_json),
                'event_states': reading['event_states']}
            by_signature[_json(signature)].append((ri, reading, row, totals))
        for encoded, members in by_signature.items():
            semantic = json.loads(encoded)
            ordered = sorted(members, key=lambda item: (_json({k: item[1].get(k) for k in
                ('candidate_ref', 'alternative_index', 'origin_pointer', 'provider', 'display_label')}), item[0]))
            ri, reading, row, totals = ordered[0]
            potential, patterns = _potential(potential_plan, potential_cache, reading, edge['from'], edge['to'])
            raw = totals['nonmember_not_confirmed_nct']
            if not 0 <= potential <= raw: raise ValueError('invalid_local_nct_bound')
            total = sum(totals.values(), Fraction())
            origins = [{'reading_key': {'edge': ei, 'reading': item[0]},
                        **{k: deepcopy(item[1].get(k)) for k in
                           ('candidate_ref', 'alternative_index', 'origin_pointer', 'provider', 'display_label')}}
                       for item in ordered]
            groups.append({**semantic, 'group_id': 'pgroup_' + _hash(semantic)[:24],
                'origin_reading_keys': [deepcopy(o['reading_key']) for o in origins], 'origins': origins,
                'adapter_reading_key': {'edge': ei, 'reading': ri}, 'representative_origin_preferred': False,
                'objective_increment': {'raw_nonmember_note_time': q(raw),
                    'spelling_unresolved_note_time': q(totals['spelling_unresolved']),
                    'blocked_note_time': q(total if reading['abstention_reasons'] else Fraction()),
                    'optimistic_local_nct_potential_note_time': q(potential), 'total_note_time': q(total)},
                'potential_nct_pattern_refs': patterns,
                'local_nct_bound_is_exemption': False})
    return sorted(groups, key=lambda g: g['group_id'])


def _universe(groups, last):
    incoming = defaultdict(list)
    for group in groups: incoming[group['to']].append(group)
    semantic = defaultdict(int, {(0, 0): 1}); origin = defaultdict(int, {(0, 0): 1})
    for end in range(1, last + 1):
        for count in range(1, end + 1):
            for group in incoming[end]:
                semantic[end, count] += semantic[group['from'], count - 1]
                origin[end, count] += origin[group['from'], count - 1] * len(group['origins'])
    return {str(count): semantic[last, count] for count in range(1, last + 1)}, {
            str(count): origin[last, count] for count in range(1, last + 1)}


def _vector(prefix):
    if 'vector' in prefix: return prefix['vector']
    raw, unknown, blocked, potential, _ = prefix['values']
    return raw, raw - potential, blocked, unknown


def _ranks(prefix):
    if 'ranks' in prefix: return prefix['ranks']
    raw, bound, blocked, unknown = _vector(prefix)
    return ((raw, blocked, unknown, bound, prefix['refs']),
            (bound, blocked, unknown, raw, prefix['refs']),
            (blocked, unknown, bound, raw, prefix['refs']))


def _dominates(left, right):
    a, b = _vector(left), _vector(right)
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def _retain(candidates, limit):
    if len(candidates) <= limit: return sorted(candidates, key=lambda p: _ranks(p)[0]), Counter(), []
    lanes = [sorted(candidates, key=lambda p: _ranks(p)[lane]) for lane in range(3)]
    picked = []; seen = set(); cursors = [0, 0, 0]
    while len(picked) < limit:
        for lane, rows in enumerate(lanes):
            while cursors[lane] < len(rows) and rows[cursors[lane]]['refs'] in seen: cursors[lane] += 1
            if cursors[lane] < len(rows) and len(picked) < limit:
                item = rows[cursors[lane]]; cursors[lane] += 1
                picked.append(item); seen.add(item['refs'])
    counts = Counter(); examples = []; reason_by_vector = {}
    for item in candidates:
        if item['refs'] in seen: continue
        vector = _vector(item)
        if vector not in reason_by_vector:
            reason_by_vector[vector] = ('frontier_dominance_approximation' if any(_dominates(p, item) for p in picked)
                                        else 'state_capacity_approximation')
        reason = reason_by_vector[vector]
        counts[reason] += 1
        if len(examples) < 8:
            examples.append({'reason': reason, 'semantic_group_refs': list(item['refs']),
                             'objective_vector': [q(x) for x in _vector(item)]})
    return picked, counts, examples


def search(context_bundle, *, max_segments=6, per_state_limit=6,
           max_complete_paths=24, transition_budget=200000):
    """Return full-context proposals, with every approximation explicitly kept.

    The interval inventory remains complete in the supplied immutable bundle.
    Proposal search is bounded separately; neither a dominance exclusion nor a
    capacity exclusion is negative evidence about a harmony or NCT reading.
    """
    limits = {'max_segments': max_segments, 'per_state_limit': per_state_limit,
              'max_complete_paths': max_complete_paths, 'transition_budget': transition_budget}
    if any(type(value) is not int or value <= 0 for value in limits.values()):
        raise ValueError('positive_integer_search_budgets_required')
    before = _hash(context_bundle)
    if context_bundle.get('selected') is not None or context_bundle.get('source_labels_used', False) is not False:
        raise ValueError('nonblind_or_selected_search_bundle')
    lattice = context_bundle['stages']['lattice']
    out = {'version': VERSION, 'input_bundle_content_sha256': before,
        'input_ir_content_sha256': context_bundle.get('input_ir_content_sha256'),
        'sample': deepcopy(context_bundle['sample']), 'budgets': limits,
        'proposals': [], 'semantic_groups': [], 'unspelled_candidates': deepcopy(context_bundle['unspelled_candidates']),
        'selected': None, 'confidence_generated': False, 'source_labels_used': False,
        'harmonic_progression_confirmed': False, 'production_modified': False,
        'ranking_scope': 'bounded_computational_proposal_order_not_musical_preference',
        'objective': {'basis': 'exact_all_part_raw_note_time_with_separate_optimistic_local_NCT_bound',
            'dimensions': ['raw_nonmember_note_time', 'spelling_unresolved_note_time', 'blocked_note_time',
                           'optimistic_local_nct_potential_note_time'],
            'retention_lanes': ['raw_membership', 'optimistic_stored_vocabulary_bound', 'blocker_exposure'],
            'segment_count_is_diversity_stratum': True, 'segment_penalty': None,
            'local_nct_bound_is_exemption': False, 'missing_member_count_is_objective': False,
            'correlated_evidence_summed_as_votes': False},
        'limits': ['Search cannot propose unspelled candidates as invented spelled harmony.',
            'Local NCT potential may combine incompatible assignments; it is an optimistic bound only.',
            'Complete-path shared-assignment evaluation may reverse raw or bound proposal ordering.',
            'Same semantic members conserve raw note-time when split; segment count is not confidence.',
            'Semantic grouping retains all provider origins; its adapter reading is not a preferred origin.',
            'Stored candidate inventory is not all possible harmonies; exhaustiveness is vocabulary-relative.',
            'Every cap or approximate frontier exclusion is missing search coverage, not rejection evidence.']}
    if lattice['status'] != 'ready':
        return {**out, 'status': 'preserved_lattice_abstention', 'lattice_status': lattice['status'],
                'exhaustive': False, 'universe': {}, 'exclusions': [{'reason': lattice['status'], 'scope': 'whole_proposal_stage'}],
                'search_counts': {'transitions_executed': 0, 'complete_proposals': 0}}
    groups = _groups(context_bundle); out['semantic_groups'] = groups
    last = len(lattice['plan']['points']) - 1
    semantic_counts, origin_counts = _universe(groups, last)
    universe_total = sum(semantic_counts.values()); searched_segments = min(max_segments, last)
    eligible_total = sum(semantic_counts[str(k)] for k in range(1, searched_segments + 1))
    out['universe'] = {'stored_edges': len(lattice['edges']), 'stored_readings': len(context_bundle['reading_inventory']),
        'semantic_groups': len(groups), 'unspelled_candidate_refs': len(out['unspelled_candidates']),
        'complete_semantic_paths_by_segment_count': semantic_counts,
        'complete_origin_paths_by_segment_count': origin_counts,
        'complete_semantic_paths': universe_total, 'complete_origin_paths': sum(origin_counts.values()),
        'within_segment_limit_semantic_paths': eligible_total,
        'segment_limit_excluded_semantic_paths': universe_total - eligible_total}
    incoming = defaultdict(list)
    for group in groups: incoming[group['to']].append(group)
    states = {(0, 0): [{'refs': (), 'values': (Fraction(),) * 5}]}
    transitions = 0; exclusions = []; aggregate = Counter(); stopped = False
    if universe_total > eligible_total:
        exclusions.append({'reason': 'segment_limit_approximation', 'complete_semantic_paths': universe_total - eligible_total,
                           'excluded_segment_counts': list(range(searched_segments + 1, last + 1))})
    if out['unspelled_candidates']:
        exclusions.append({'reason': 'unspelled_candidate_path_capability_missing',
                           'candidate_refs_preserved': len(out['unspelled_candidates'])})
    for end in range(1, last + 1):
        for count in range(1, min(end, searched_segments) + 1):
            candidates = []
            for group in incoming[end]:
                values = group['objective_increment']
                inc = tuple(f(values[name]) for name in ('raw_nonmember_note_time', 'spelling_unresolved_note_time',
                    'blocked_note_time', 'optimistic_local_nct_potential_note_time', 'total_note_time'))
                for prefix in states.get((group['from'], count - 1), []):
                    if transitions >= transition_budget:
                        stopped = True; break
                    transitions += 1
                    candidate = {'refs': prefix['refs'] + (group['group_id'],),
                                 'values': tuple(x + y for x, y in zip(prefix['values'], inc))}
                    candidate['vector'] = _vector(candidate); candidate['ranks'] = _ranks(candidate)
                    candidates.append(candidate)
                if stopped: break
            kept, reasons, examples = _retain(candidates, per_state_limit)
            states[end, count] = kept; aggregate.update(reasons)
            if reasons:
                exclusions.append({'reason': 'approximate_prefix_frontier', 'end_point_index': end,
                    'segment_count': count, 'discarded_prefixes_by_reason': dict(reasons),
                    'discarded_examples': examples, 'examples_are_complete_ledger': False})
            if stopped: break
        if stopped: break
    if stopped:
        exclusions.append({'reason': 'transition_budget_approximation', 'stopped_at': {'end_point_index': end, 'segment_count': count},
                           'unexecuted_complete_paths_not_rejected': True})
    # Round-robin segment-count strata prevent a raw zero-mismatch subdivision
    # from crowding out governing-hold proposals solely because it uses more cuts.
    complete = {k: list(states.get((last, k), [])) for k in range(1, searched_segments + 1)}
    available = sum(len(rows) for rows in complete.values()); retained = []
    while len(retained) < min(max_complete_paths, available):
        for count in sorted(complete):
            if complete[count] and len(retained) < max_complete_paths: retained.append(complete[count].pop(0))
    if available > len(retained):
        exclusions.append({'reason': 'complete_path_capacity_approximation', 'discarded_complete_proposals': available - len(retained),
                           'retention': 'round_robin_segment_count_strata'})
    by_id = {g['group_id']: g for g in groups}
    expected_total = sum((f(c['span']['end']) - f(c['span']['start'])) * len(c['event_refs']) for c in lattice['cells'])
    for prefix in retained:
        raw, unknown, blocked, potential, total = prefix['values']
        path = [deepcopy(by_id[gid]['adapter_reading_key']) for gid in prefix['refs']]
        cursor = 0
        for gid in prefix['refs']:
            group = by_id[gid]
            if group['from'] != cursor: raise ValueError('search_produced_noncontiguous_path')
            cursor = group['to']
        if cursor != last or total != expected_total: raise ValueError('search_produced_incomplete_note_time')
        out['proposals'].append({'proposal_id': 'pprop_' + _hash({'sample': context_bundle['sample'], 'groups': prefix['refs']})[:24],
            'path': path, 'semantic_group_refs': list(prefix['refs']), 'complete_context_path': True,
            'representative_readings_are_adapter_only': True, 'origin_preference': None,
            'objective': {'raw_nonmember_note_time': q(raw), 'spelling_unresolved_note_time': q(unknown),
                'blocked_note_time': q(blocked), 'optimistic_local_nct_potential_note_time': q(potential),
                'optimistic_stored_vocabulary_residual_bound': q(raw - potential),
                'total_note_time': q(total), 'segment_count': len(path)},
            'proposal_order_is_harmonic_preference': False, 'selected': None})
    out.update(status='complete_path_proposals_not_verdict' if out['proposals'] else 'no_complete_path_proposal',
        exhaustive=(len(retained) == universe_total and not out['unspelled_candidates'] and not stopped),
        exclusions=exclusions, search_counts={'transitions_executed': transitions,
            'discarded_prefixes_by_reason': dict(aggregate), 'retained_complete_before_output_cap': available,
            'complete_proposals': len(retained), 'semantic_complete_paths_not_emitted': universe_total - len(retained),
            'prefix_exclusions_are_not_additive_complete_path_counts': True})
    if _hash(context_bundle) != before: raise ValueError('search_mutated_bundle')
    return out
