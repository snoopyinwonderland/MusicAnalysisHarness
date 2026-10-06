"""Non-ranking proposal/hold policy over validated, archived progression evidence.

This adapter does not infer a key, issue native authority, replay a supplier or
re-evaluate NCT predicates. A content seal is NOT provenance authentication:
the caller must verify the archive's creation hashes and exact parent inventory.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction

from . import factor_expanded_hypotheses as sealed
from . import factor_interval_lattice as native
from . import native_progression_contrast as parent
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "native-progression-policy-0.1.0"
PREFIX = "nppolicy_"
AUTHORITY = parent.AUTHORITY
RULE_VERSION = "progression-proposal-hold-rules-0.1.0"
RULES = {
    "P01": "Source and hypothesis uncertainty is not musical disproof.",
    "P02": "An explicit key hypothesis is required, never inferred from a signature.",
    "P03": "Missing guarded members need evidence; omission is not automatic.",
    "P04": "Known shape mismatch concerns only the declared function requirement.",
    "P05": "Whole ordinary obligations must hold under the same completion.",
    "P06": "Literal lowest notes are not certified structural bass or pedal.",
    "P07": "Empty or undeclared transition vectors cannot pass vacuously.",
    "P08": "Unexplained source time remains a review need, not confirmed NCT.",
    "P09": "Repeated signatures and extra cuts do not prove harmonic change.",
    "P10": "Only exact key/bundle/partition/vector groups share fixed premises.",
}
STATUSES = ("conditional_function_supported_alternative", "held_missing_evidence",
            "not_supported_under_declared_requirements")
AXES = {"source_shape_compatible", "target_triad_core_shape_compatible",
    "function_shape_prerequisites_available", "known_explicit_key_coordinate",
    "same_registered_complete_all_raw_lane_bundle", "guarded_pooled_literal_core_present",
    "observed_lowest_source_guards_passed", "actual_ordinary_role_rows_available",
    "whole_explicit_ordinary_template_satisfied"}


def _nodes(value):
    if type(value) is dict:
        return 1 + sum(1 + _nodes(v) for v in value.values())
    if type(value) is list:
        return 1 + sum(_nodes(v) for v in value)
    return 1


def _premise(facet):
    return {k: deepcopy(facet[k]) for k in ("key_ref", "bundle_ref", "partition", "transition_assumptions")}


def _ref_member(ref, inventory, name):
    parent._plain_ref(ref)
    item = inventory.get(ref["record_id"])
    if item is None or sealed._ref(item) != ref:
        raise ValueError("foreign_saved_policy_" + name)
    return item


def _tri(value):
    if value is not None and type(value) is not bool:
        raise ValueError("strict_tristate_policy_evidence_required")
    return value


def _truth(values):
    return False if False in values else None if None in values else bool(values)


def _literal_projection(scope, origin, slot_index, sounds, cache):
    """Recheck literal arithmetic only; this is not a chord or role supplier."""
    oid = origin['record_id']
    if oid not in cache['profiles']:
        cache['profiles'][oid] = sealed._profile(scope, origin)
    profile, members = cache['profiles'][oid], origin['members']
    presentation = []
    for member in members or []:
        occurrences = [r for r in profile['rows'] if sealed._pitch_key(r['pitch']) == sealed._pitch_key(member)
            and cache['guards'][r['sound_ref']]['strict'] and not origin['blockers']]
        presentation.append({'spelling': deepcopy(member),
            'first_guarded_observed_time': q(min(f(r['observed_span']['start']) for r in occurrences)) if occurrences else None,
            'source_note_time_quarters': q(sum((f(r['observed_span']['end']) - f(r['observed_span']['start'])
                for r in occurrences), Fraction())), 'sound_refs': [r['sound_ref'] for r in occurrences],
            'observations': [{'sound_ref': r['sound_ref'], 'source_note_refs': sounds[r['sound_ref']]['source_note_refs'],
                'full_sound_span': r['full_span'], 'observed_span': r['observed_span'],
                'attack_note_ref': sounds[r['sound_ref']]['attack_note_ref'], 'tie_chain_ref': sounds[r['sound_ref']]['tie_chain_ref'],
                'attack_before_slot': f(r['full_span']['start']) < f(origin['span']['start'])} for r in occurrences]})
    slot = {'slot_index': slot_index, 'origin_ref': sealed._ref(origin), 'span': origin['span'],
        'root': origin['root'], 'members': members, 'member_presentations': presentation,
        'required_member_count': None if members is None else len(members),
        'missing_guarded_spellings': None if members is None else [r['spelling'] for r in presentation if r['first_guarded_observed_time'] is None],
        'pooled_support_is_not_arpeggio_confirmation': True}
    cells = []
    for cell in profile['cells']:
        strict = {sealed._pitch_key(sounds[sid]['pitch']) for sid in cell['sound_refs']
            if cache['guards'][sid]['strict']}
        cells.append({'slot_index': slot_index, 'origin_ref': sealed._ref(origin), **deepcopy(cell),
            'strict_guard_missing_spellings': None if members is None or origin['blockers'] else
                [p for p in members if sealed._pitch_key(p) not in strict],
            'strict_bass_source_guards_passed': None if not cell['bass_refs'] else all(
                cache['guards'][sid]['strict'] for sid in cell['bass_refs'])})
    return slot, cells, profile


def _validate_facet(facet, entry, scope, keys, bundles, origins, sounds, cache):
    for name in ("native_path_ref", "role_path_ref", "comparison_ref", "explanation_ref"):
        parent._plain_ref(facet[name])
        if facet[name] != entry[name]:
            raise ValueError("ordered_saved_policy_entry_reference_mismatch")
    key = _ref_member(facet["key_ref"], keys, "key")
    bundle = _ref_member(facet["bundle_ref"], bundles, "completion")
    if any(facet[k] is not None for k in ("selected", "rank", "confidence")):
        raise ValueError("saved_policy_cannot_consume_promoted_facet")
    partition = facet["partition"]
    if not partition or len(partition) != len(facet["slot_presentations"]):
        raise ValueError("whole_saved_policy_partition_required")
    bounds = [span_bounds(s) for s in partition]
    if (any(a >= b for a, b in bounds) or bounds[0][0] != span_bounds(scope["analysis_span"])[0]
            or bounds[-1][1] != span_bounds(scope["analysis_span"])[1]
            or any(a[1] != b[0] for a, b in zip(bounds, bounds[1:]))):
        raise ValueError("whole_contiguous_saved_policy_partition_required")
    slots = facet["slot_presentations"]
    chosen, profiles, expected_cells = [], [], []
    for i, slot in enumerate(slots):
        origin = _ref_member(slot["origin_ref"], origins, "origin")
        if (slot["slot_index"] != i or slot["span"] != partition[i]
                or origin["span"] != slot["span"]
                or any(origin[k] != slot[k] for k in ("root", "members"))):
            raise ValueError("saved_policy_slot_origin_mismatch")
        expected_slot, cells, profile = _literal_projection(scope, origin, i, sounds, cache)
        if digest(slot) != digest(expected_slot):
            raise ValueError('saved_policy_literal_member_projection_mismatch')
        chosen.append(origin)
        profiles.append(profile)
        expected_cells.extend(cells)
        for member in slot["member_presentations"]:
            for observed in member["observations"]:
                sound = sounds.get(observed["sound_ref"])
                if sound is None or any(observed[a] != sound[b] for a, b in (
                        ("source_note_refs", "source_note_refs"), ("full_sound_span", "span"),
                        ("attack_note_ref", "attack_note_ref"), ("tie_chain_ref", "tie_chain_ref"))):
                    raise ValueError("saved_policy_note_attack_tie_closure_mismatch")
    a, b = span_bounds(scope["analysis_span"])
    expected = {sid for sid, s in sounds.items() if max(a, f(s["span"]["start"])) < min(b, f(s["span"]["end"]))}
    if set(facet["source_segments"]) != expected:
        raise ValueError("saved_policy_source_sound_coverage_mismatch")
    totals = {category: Fraction() for category in parent.CATEGORIES}
    assessed = facet['account']['status'] == 'conditional_account_not_NCT_verdict'
    if not assessed and facet['account']['status'] != 'unassessed_completion_raw_time_preserved':
        raise ValueError('saved_policy_account_assessment_status_required')
    conditional_ranges = defaultdict(list)
    credit_rows = facet['account']['explained_intervals_by_sound']
    credited = {r['sound_ref']: [span_bounds(s) for s in r['spans']] for r in credit_rows}
    if len(credited) != len(credit_rows) or any(sid not in expected for sid in credited):
        raise ValueError('saved_policy_unique_source_credit_union_required')
    for sid, ranges in credited.items():
        if (any(not max(a, f(sounds[sid]['span']['start'])) <= x < y <= min(b, f(sounds[sid]['span']['end'])) for x, y in ranges)
                or any(left[1] >= right[0] for left, right in zip(ranges, ranges[1:]))):
            raise ValueError('saved_policy_canonical_source_credit_union_required')
    for sid, rows in facet["source_segments"].items():
        sound = sounds[sid]
        cursor = max(a, f(sound["span"]["start"]))
        end = min(b, f(sound["span"]["end"]))
        for row in rows:
            x, y = span_bounds(row["span"])
            i = row["slot_index"]
            if (type(i) is not int or not 0 <= i < len(slots) or x != cursor or not x < y <= end
                    or not bounds[i][0] <= x < y <= bounds[i][1]
                    or row["origin_ref"] != slots[i]["origin_ref"] or row["category"] not in totals):
                raise ValueError("saved_policy_source_atom_closure_mismatch")
            state = sealed._state(sound, chosen[i])
            has_credit = any(c <= x < y <= d for c, d in credited.get(sid, []))
            category = ('source_or_hypothesis_unsupported' if chosen[i]['blockers'] or cache['guards'][sid]['role_blocked']
                else 'source_guarded_member' if state == 'member' else 'membership_unknown' if state == 'spelling_unresolved'
                else 'unassessed_nonmember' if not assessed else 'conditional_explained_nonmember' if has_credit
                else 'unexplained_nonmember_under_this_completion')
            if row['raw_state'] != state or row['category'] != category:
                raise ValueError('saved_policy_raw_membership_or_credit_mismatch')
            if row['category'] == 'conditional_explained_nonmember':
                conditional_ranges[sid].append(row['span'])
            totals[row["category"]] += y - x
            cursor = y
        if cursor != end:
            raise ValueError("saved_policy_source_atom_gap")
    if ({k: q(v) for k, v in totals.items()} != facet["account"]["note_time_quarters"]
            or sum(totals.values(), Fraction()) != f(facet["account"]["raw_total_note_time_quarters"])):
        raise ValueError("saved_policy_source_account_mismatch")
    raw = native._account(scope, profiles)
    account = facet['account']
    actual_union = {sid: parent.temporal._union(ranges) for sid, ranges in conditional_ranges.items()}
    if actual_union != {r['sound_ref']: r['spans'] for r in credit_rows}:
        raise ValueError('saved_policy_credit_union_atom_closure_mismatch')
    if (account['raw_state_note_time_quarters'] != raw['raw_state_note_time_quarters']
            or account['raw_time_conserved'] is not True or account['union_counted_once'] is not True
            or assessed and account['conditional_explanation_note_time_quarters'] != q(totals['conditional_explained_nonmember'])
            or assessed and account['guarded_nonmember_note_time_quarters'] != q(
                totals['conditional_explained_nonmember'] + totals['unexplained_nonmember_under_this_completion'])
            or not assessed and account['guarded_nonmember_note_time_quarters'] is not None
            or not assessed and account['conditional_explanation_note_time_quarters'] is not None):
        raise ValueError('saved_policy_raw_state_or_credit_account_mismatch')
    count = len(partition) - 1
    if any(len(facet[name]) != count for name in ("transition_assumptions", "actual_transition_evidence", "ordinary_templates", "transition_context_refs")):
        raise ValueError("saved_policy_transition_coverage_mismatch")
    for i, (assumption, ev, template) in enumerate(zip(facet["transition_assumptions"], facet["actual_transition_evidence"], facet["ordinary_templates"])):
        if ev["context_ref"] != facet["transition_context_refs"][i] or template["cut_index"] != i:
            raise ValueError("saved_policy_transition_reference_mismatch")
        _tri(ev["joint_conditional_functional_evidence"])
        _tri(template["satisfied"])
        if assumption is None:
            if (ev["function_shape"] is not None or ev["ordinary_strategy"] is not None or ev["prerequisite_axes"] is not None
                    or ev['joint_conditional_functional_evidence'] is not None or template['satisfied'] is not None):
                raise ValueError("undeclared_policy_function_has_evidence")
            continue
        shape, axes = ev["function_shape"], ev["prerequisite_axes"]
        if shape is None or type(axes) is not dict or set(axes) != AXES:
            raise ValueError("closed_declared_policy_axes_required")
        if (shape["family"] != assumption["family"] or shape["target_quality"] != assumption["quality"]
                or shape["source_span"] != partition[i] or shape["target_span"] != partition[i + 1]
                or template["native_function_context_ref"] != ev["context_ref"]):
            raise ValueError("saved_policy_declared_function_mismatch")
        for value in axes.values():
            _tri(value)
        expected_shape = sealed._function(scope, chosen[i], chosen[i + 1], key['segments'][0], assumption['family'], assumption['quality'])
        strategy = ev['ordinary_strategy']
        known = native.context._key_context(key)['key_coordinate_prerequisites_available']
        expected_axes = {'source_shape_compatible': shape['shape_compatible'],
            'target_triad_core_shape_compatible': shape['target_shape_compatible'],
            'function_shape_prerequisites_available': shape['status'] == 'conditional_function_shape',
            'known_explicit_key_coordinate': None if not known else shape['key_projection']['target_coordinate'] is not None,
            'same_registered_complete_all_raw_lane_bundle': bundle['status'] == 'complete_all_lane_witness',
            'guarded_pooled_literal_core_present': _truth([native.context._profile_axes(profiles[j], chosen[j])['guarded_pooled_core_present'] for j in (i, i + 1)]),
            'whole_explicit_ordinary_template_satisfied': strategy['whole_ordinary_template_satisfied']}
        if (digest(shape) != digest(expected_shape) or any(axes[k] is not v for k, v in expected_axes.items())
                or ev['joint_conditional_functional_evidence'] is not _truth(list(axes.values()))
                or strategy['same_complete_bundle'] is not True):
            raise ValueError('saved_policy_shape_axes_or_joint_join_mismatch')
        truths = template.get('role_truths', [])
        for value in truths:
            _tri(value)
        expected_whole = None if template.get('prerequisite_blockers') else _truth(truths)
        if (template['satisfied'] is not expected_whole or template['satisfied'] is True and
                (strategy['whole_ordinary_template_satisfied'] is not True or not truths)):
            raise ValueError('saved_policy_whole_template_join_mismatch')
        actual_links = {tuple(link) for link in bundle['materialized_witness_links']}
        for role in strategy['role_assessments']:
            _tri(role['satisfied_under_this_bundle'])
            for occurrence in role['occurrences']:
                route = occurrence['route_sound_refs']
                if (not route or any(sid not in sounds for sid in route)
                        or occurrence['source_sound_ref'] != route[0]
                        or occurrence['endpoint_sound_ref'] is not None and occurrence['endpoint_sound_ref'] != route[-1]
                        or occurrence['full_sound_spans'] != [sounds[sid]['span'] for sid in route]
                        or occurrence['source_note_refs'] != sounds[occurrence['source_sound_ref']]['source_note_refs']
                        or any(tuple(link) not in actual_links for link in occurrence['actual_required_links'])):
                    raise ValueError('saved_policy_ordinary_route_closure_mismatch')
                _tri(occurrence['satisfied_under_this_bundle'])
                if occurrence['satisfied_under_this_bundle'] is not (not occurrence['blockers'] and bundle['status'] == 'complete_all_lane_witness'):
                    raise ValueError('saved_policy_ordinary_occurrence_truth_join_mismatch')
            if role['satisfied_under_this_bundle'] is not any(o['satisfied_under_this_bundle'] is True for o in role['occurrences']):
                raise ValueError('saved_policy_ordinary_role_truth_join_mismatch')
        if strategy['whole_ordinary_template_satisfied'] is not (bool(strategy['role_assessments']) and
                all(r['satisfied_under_this_bundle'] is True for r in strategy['role_assessments'])):
            raise ValueError('saved_policy_ordinary_whole_truth_join_mismatch')
    if digest(facet['bass_cells']) != digest(expected_cells):
        raise ValueError('saved_policy_literal_bass_projection_mismatch')
    return key


def _alternative(facet, key):
    diagnostics = []
    def add(rule, reason, effect="hold", **target):
        diagnostics.append({"rule_id": rule, "reason": reason, "effect": effect, "target": deepcopy(target)})
    if any(s["tonic"] is None or s["mode"] == "unknown" for s in key["segments"]):
        add("P02", "explicit_key_coordinate_unavailable")
    categories = facet["account"]["note_time_quarters"]
    for category in parent.CATEGORIES[2:]:
        if f(categories[category]) > 0:
            add("P01" if category in ("membership_unknown", "source_or_hypothesis_unsupported") else "P08",
                category, source_note_time_quarters=categories[category])
    for slot in facet["slot_presentations"]:
        if slot["root"] is None or slot["members"] is None:
            add("P01", "root_or_spelling_unavailable", slot_index=slot["slot_index"])
        if slot["missing_guarded_spellings"] is None:
            add("P03", "guarded_member_presence_unassessed", slot_index=slot["slot_index"])
        elif slot["missing_guarded_spellings"]:
            add("P03", "missing_guarded_member_needs_omission_or_redistribution_evidence",
                slot_index=slot["slot_index"], spellings=slot["missing_guarded_spellings"])
    transitions = []
    if not facet["transition_assumptions"]:
        add("P07", "no_internal_functional_relation_not_vacuous_support")
    for i, (assumption, ev, template) in enumerate(zip(facet["transition_assumptions"], facet["actual_transition_evidence"], facet["ordinary_templates"])):
        if assumption is None:
            add("P07", "internal_functional_relation_not_declared", cut_index=i)
            transitions.append({"cut_index": i, "status": "undeclared", "context_ref": deepcopy(ev["context_ref"]),
                "joint_support": None, "ordinary_template_support": None, "individual_roles": []})
            continue
        axes = ev["prerequisite_axes"]
        for axis, value in axes.items():
            if value is not True:
                effect = "not_supported_under_declared_requirement" if value is False and axis in (
                    "source_shape_compatible", "target_triad_core_shape_compatible") else "hold"
                add("P04" if effect != "hold" else "P03" if axis == "guarded_pooled_literal_core_present"
                    else "P02" if axis == "known_explicit_key_coordinate" else "P05",
                    axis + ("_false" if value is False else "_unassessed"), effect,
                    cut_index=i, observed_value=value)
        if template["satisfied"] is not True:
            add("P05", "whole_role_template_not_satisfied_under_this_completion" if template["satisfied"] is False
                else "whole_role_template_unassessed", cut_index=i, observed_value=template["satisfied"])
        if ev["joint_conditional_functional_evidence"] is not True:
            add("P05", "joint_functional_support_not_demonstrated", cut_index=i,
                observed_value=ev["joint_conditional_functional_evidence"])
        strategy = ev["ordinary_strategy"]
        transitions.append({"cut_index": i, "status": "assessed_declared_strategy",
            "context_ref": deepcopy(ev["context_ref"]), "joint_support": ev["joint_conditional_functional_evidence"],
            "ordinary_template_support": template["satisfied"],
            "individual_roles": deepcopy(strategy["role_assessments"]), "prerequisite_axes": deepcopy(axes),
            "shape_blockers": deepcopy(ev["function_shape"]["blockers"])})
    bad_bass = [c for c in facet["bass_cells"] if not c["silence"] and
                (c["bass_source_guards_passed"] is not True or c["strict_bass_source_guards_passed"] is not True)]
    if bad_bass:
        add("P06", "literal_bass_source_guards_not_demonstrated", cells=[
            {"span": c["span"], "bass_refs": c["bass_refs"]} for c in bad_bass])
    repeated = [c for c in facet["cut_signature_observations"] if c["same_assumed_ordered_root_members"]]
    if repeated:
        add("P09", "same_signature_cut_requires_independent_boundary_evidence", times=[c["time"] for c in repeated])
    failed = any(d["effect"] == "not_supported_under_declared_requirement" for d in diagnostics)
    status = STATUSES[2] if failed else STATUSES[1] if diagnostics else STATUSES[0]
    return {"entry_refs": {k: deepcopy(facet[k]) for k in ("native_path_ref", "role_path_ref", "comparison_ref", "explanation_ref")},
        "premises": _premise(facet), "status": status, "diagnostics": diagnostics,
        "transition_assessments": transitions, "account_pointer": {
            "parent_native_path_ref": deepcopy(facet["native_path_ref"]), "parent_role_path_ref": deepcopy(facet["role_path_ref"]),
            "field": "account", "sha256": digest(facet["account"])},
        "claim_scope": "declared_strategy_under_this_saved_completion_not_harmony_verdict",
        "selected": None, "rank": None, "confidence": None}


def evaluate(scope, lattice, contrast, *, bundles, work_budget=2000000):
    """Keep every submitted alternative; propose only non-ranked conditional support.

    Work is a conservative tree/reference visit allowance, not wall time/RSS.
    Byte/decode admission and immutable creation provenance belong to the runner.
    """
    native._integer(work_budget, "work_budget")
    if type(bundles) is not dict:
        raise ValueError("saved_policy_bundle_map_required")
    before = digest([scope, lattice, contrast, bundles])
    sealed._check(scope, "fmes_")
    sealed._check(lattice, native.PREFIX)
    sealed._check(contrast, parent.PREFIX)
    if (contrast["version"] != parent.VERSION or contrast["source_authority"] != AUTHORITY
            or contrast["scope_ref"] != sealed._ref(scope) or contrast["lattice_ref"] != sealed._ref(lattice)
            or lattice["scope_ref"] != sealed._ref(scope)
            or any(r["binding"] != scope["binding"] or r["analysis_span"] != scope["analysis_span"] for r in (lattice, contrast))
            or contrast["flags"] != parent._flags() or any(v is not False for v in contrast['flags'].values())
            or any(contrast[k] is not None for k in ("selected", "rank", "confidence"))):
        raise ValueError("unpromoted_same_source_saved_policy_inputs_required")
    entries, facets = contrast["submitted_entry_refs"], contrast["facets"]
    if len(entries) > 256 or contrast["summary"]["submitted_entries"] != len(entries):
        raise ValueError("bounded_exact_saved_policy_entry_list_required")
    identities = [digest(e["native_path_ref"]) for e in entries]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate_saved_policy_entry")
    grouped = defaultdict(list)
    for i, facet in enumerate(facets):
        grouped[digest(_premise(facet))].append(i)
    n = len(scope['sound_facts'])
    slot_work = sum(4 * (n + 1) * (n + sum(len(s['source_note_refs']) for s in scope['sound_facts'])
        + len(slot['members'] or []) + 1) for fa in facets for slot in fa['slot_presentations'])
    unique_origins = {slot['origin_ref']['record_id'] for fa in facets for slot in fa['slot_presentations']}
    # _profile copies literal diagnostics once per cached origin. Strict/role
    # guards are evaluated once per sound, not inside every active-cell scan.
    slot_work += 4 * _nodes(scope['sound_facts']) * (len(unique_origins) + 1)
    credit_work = 0
    for facet in facets:
        credit_counts = {r['sound_ref']: len(r['spans']) for r in facet['account']['explained_intervals_by_sound']}
        credit_work += sum(len(rows) * (credit_counts.get(sid, 0) + 1) for sid, rows in facet['source_segments'].items())
    plan = {"planned_work": 4 * _nodes([scope, lattice, contrast, bundles]) + len(entries) ** 2 + slot_work + credit_work,
        "literal_profile_and_reference_work": slot_work,
        "source_credit_cover_work": credit_work,
        "submitted_entries": len(entries), "planned_groups": len(grouped) if facets or not entries else None,
        "semantics": "whole_tree_reference_visit_allowance_not_CPU_time_or_accuracy"}
    reasons = []
    for sid, bundle in bundles.items():
        sealed._check(bundle, native.BUNDLE_PREFIX)
        if sid != bundle['record_id'] or bundle['scope_ref'] != sealed._ref(scope) or bundle['binding'] != scope['binding']:
            raise ValueError('foreign_saved_policy_bundle')
    if any(bundle['status'] != 'complete_all_lane_witness' for bundle in bundles.values()):
        reasons.append('saved_completion_witness_withheld_whole_policy_hold')
    if contrast["status"] == "whole_saved_contrast_hold":
        if facets or contrast["pairs"]:
            raise ValueError("parent_whole_hold_has_partial_evidence")
        reasons.append("parent_contrast_whole_hold_no_evidence_prefix")
    elif contrast["status"] != "computed_saved_progression_contrasts_not_selected" or len(facets) != len(entries):
        raise ValueError("complete_saved_contrast_or_whole_hold_required")
    if plan["planned_work"] > work_budget:
        reasons.append("whole_policy_work_exceeds_budget_no_prefix")
    alternatives, groups = [], []
    if not reasons:
        keys = parent._lookup(lattice["keys"], "policy_key")
        origins = parent._lookup([o for c in lattice["catalog_inventory"] for o in c["origins"]], "policy_origin")
        sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
        if len(sounds) != len(scope["sound_facts"]):
            raise ValueError("duplicate_saved_policy_source_sound")
        guards = {}
        for sid, sound in sounds.items():
            blocked = bool(parent.temporal._guard_codes(sound))
            guards[sid] = {'strict': not sealed._source_blockers(sound) and not blocked, 'role_blocked': blocked}
        cache = {'profiles': {}, 'guards': guards}
        for facet, entry in zip(facets, entries):
            key = _validate_facet(facet, entry, scope, keys, bundles, origins, sounds, cache)
            alternatives.append(_alternative(facet, key))
        for premise, indices in grouped.items():
            groups.append({"group_id": "nppgroup_" + premise[:24], "premises": _premise(facets[indices[0]]),
                "alternative_indices": indices, "conditional_support_indices": [i for i in indices if alternatives[i]["status"] == STATUSES[0]],
                "held_indices": [i for i in indices if alternatives[i]["status"] == STATUSES[1]],
                "declared_requirement_not_supported_indices": [i for i in indices if alternatives[i]["status"] == STATUSES[2]],
                "competition": "fixed_premise_conditional_alternatives_no_unique_winner", "selected": None})
    else:
        alternatives = [{"entry_refs": deepcopy(e), "premises": None, "status": "held_whole_request",
            "diagnostics": [], "transition_assessments": [], "account_pointer": None,
            "claim_scope": "no_partial_policy_evaluation", "selected": None, "rank": None, "confidence": None} for e in entries]
    counts = Counter(a["status"] for a in alternatives)
    summary = {"submitted_entries": len(entries), "evaluated_entries": 0 if reasons else len(alternatives),
        "withheld_entries": len(entries) if reasons else 0, "fixed_premise_groups": None if reasons else len(groups),
        "conditional_function_supported_alternatives": None if reasons else counts[STATUSES[0]],
        "held_alternatives": None if reasons else counts[STATUSES[1]],
        "declared_requirement_not_supported_alternatives": None if reasons else counts[STATUSES[2]],
        "diagnostic_reason_counts": None if reasons else dict(sorted(Counter(
            d["reason"] for a in alternatives for d in a["diagnostics"]).items()))}
    result = sealed._seal({"version": VERSION, "rule_version": RULE_VERSION, "rules": RULES,
        "source_authority": AUTHORITY, "parent_contrast_ref": sealed._ref(contrast),
        "scope_ref": sealed._ref(scope), "lattice_ref": sealed._ref(lattice),
        "binding": deepcopy(scope["binding"]), "analysis_span": deepcopy(scope["analysis_span"]),
        "logical_universe": deepcopy(contrast["logical_universe"]), "submitted_entry_refs": deepcopy(entries),
        "query_plan": plan, "resource_limits": {"work_budget": work_budget}, "alternatives": alternatives,
        "fixed_premise_groups": groups, "summary": summary, "reasons": reasons,
        "status": "whole_saved_policy_hold" if reasons else "computed_saved_progression_policy_not_selected" if entries else "empty_saved_policy_request",
        "selected": None, "rank": None, "confidence": None, "flags": parent._flags(),
        "limitations": ["A supported proposal is a non-ranked conditional alternative, not final harmony or NCT.",
            "Missing members, unassessed evidence and failed ordinary strategies do not reject a chord globally.",
            "No member/credit/cut-count score, unique winner or cross-key/completion promotion is computed.",
            "Literal bass/inversion, pooled support and same-signature cuts remain conditional observations.",
            "Creation hashes must be checked by the caller; no live authority or role replay is issued."]}, PREFIX)
    if digest([scope, lattice, contrast, bundles]) != before:
        raise ValueError("saved_policy_inputs_modified")
    return result
