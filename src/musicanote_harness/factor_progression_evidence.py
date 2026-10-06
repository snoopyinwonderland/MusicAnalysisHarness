"""Same-scope complete-partition evidence contrasts, without selecting harmony.

The original one- or two-slot catalogue tuple is the path: no concatenation,
new segmentation, new key, new completion, or enlarged logical universe is
introduced here.  One explicitly supplied transition assumption is assessed
under one registered actual all-raw-lane completion.  Other function shapes,
including terminal shapes, remain present and motion-unassessed.
"""
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import hmac
from pathlib import Path
import secrets
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import factor_boundary_explanations as boundary
from . import factor_delayed_obligations as delayed
from . import factor_expanded_hypotheses as frozen
from . import factor_indexed_hypotheses as indexed
from . import factor_temporal_explanations as temporal
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "factor-progression-evidence-0.1.0"
PREFIX = "fmpe_"
PATH_PREFIX = "fmpepath_"
CONTRAST_PREFIX = "fmpecontrast_"
CAPS = ("max_hypotheses", "max_comparisons", "query_work_budget")
DEFAULTS = dict(zip(CAPS, (64, 4096, 100000)))
CATEGORIES = delayed.CATEGORIES
_SESSIONS = WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)


def _flags():
    return {**delayed._flags(), "final_harmony_confirmed": False,
        "final_key_confirmed": False, "path_selected": False,
        "ranking_computed": False, "contrast_is_confidence": False,
        "all_functional_assumptions_motion_assessed": False,
        "complete_partition_is_harmony_confirmation": False}


def _contract():
    return {"version": VERSION, "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "delayed_contract": delayed._contract()}


def _seal(body, prefix):
    return frozen._seal(body, prefix)


def _ref(record):
    return frozen._ref(record)


def _caps(values):
    for name in CAPS:
        indexed._integer(values[name], name)


class _PreparedComparison:
    __slots__ = ("__weakref__",)


@dataclass(frozen=True)
class _State:
    data: object
    upstream_session: object
    upstream_state: object
    contract_sha256: str
    authentication: bytes


def _auth(handle, state):
    return hmac.digest(_SECRET, indexed._encoded([id(handle), id(state), id(state.data),
        id(state.upstream_session), id(state.upstream_state), state.contract_sha256]), "sha256")


def _issued(handle):
    if type(handle) is not _PreparedComparison or handle not in _SESSIONS:
        raise ValueError("internally_issued_progression_comparison_session_required")
    state = _SESSIONS[handle]
    if (type(state) is not _State or not isinstance(state.data, MappingProxyType)
            or state.contract_sha256 != digest(_contract())
            or not hmac.compare_digest(state.authentication, _auth(handle, state))):
        raise ValueError("progression_session_current_contract_or_owned_state_changed")
    upstream = delayed._issued(state.upstream_session, delayed._SESSIONS, delayed._PreparedObligations)
    if upstream is not state.upstream_state:
        raise ValueError("progression_owned_upstream_authority_changed")
    return state, upstream


def prepare_comparison_prepared(delayed_session):
    """Accept only an authentic, replay-validated phase-19 authority handle."""
    upstream = delayed._issued(delayed_session, delayed._SESSIONS, delayed._PreparedObligations)
    contract = _contract()
    metadata = {name: _ref(upstream.data[name]) for name in ("scope", "index", "obligations")}
    handle = _PreparedComparison()
    state = _State(indexed._freeze(metadata), delayed_session, upstream, digest(contract), b"")
    object.__setattr__(state, "authentication", _auth(handle, state))
    if (delayed._issued(delayed_session, delayed._SESSIONS, delayed._PreparedObligations) is not upstream
            or not indexed._same(contract, _contract())):
        raise ValueError("progression_upstream_or_code_changed_during_preparation")
    _SESSIONS[handle] = state
    _issued(handle)
    return handle


def prepare_comparison(ir, scope, hypotheses, index, relations, grounding,
                       temporal_record, boundary_record, record):
    """Fresh public preparation retains the parent's exact owned replay."""
    caller = [ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record]
    before, contract = digest(caller), _contract()
    result = prepare_comparison_prepared(delayed.prepare_obligations(*caller))
    if before != digest(caller) or not indexed._same(contract, _contract()):
        raise ValueError("progression_parent_inputs_or_code_changed")
    return result


def _closed(value, keys, name):
    if type(value) is not dict or any(type(k) is not str for k in value) or set(value) != set(keys):
        raise ValueError("closed_typed_progression_contract_required:" + name)


def _transition(state, group_id, value):
    _closed(value, {"family", "quality", "strategy", "declared_occurrences", "requested_explanations"}, "transition")
    if (type(value["family"]) is not str or value["family"] not in frozen.FAMILIES
            or type(value["quality"]) is not str or value["quality"] not in ("M", "m")
            or type(value["strategy"]) is not str):
        raise ValueError("explicit_supported_progression_function_assumption_required")
    declarations = value["declared_occurrences"]
    if declarations is not None:
        if type(declarations) is not list:
            raise ValueError("typed_progression_declared_occurrence_list_required")
        for row in declarations:
            _closed(row, {"role", "sound_ref"}, "declared_occurrence")
    delayed._declarations(state, group_id, value["strategy"], declarations)
    requests = value["requested_explanations"]
    if requests is not None:
        if type(requests) is not list:
            raise ValueError("typed_progression_explanation_list_required")
        seen = set()
        for row in requests:
            _closed(row, {"stage", "geometry_id", "side"}, "requested_explanation")
            if (any(type(v) is not str for v in row.values()) or row["stage"] not in ("local", "boundary")
                    or row["side"] not in ("left", "right")):
                raise ValueError("typed_progression_explanation_request_required")
            identity = (row["stage"], row["geometry_id"], row["side"])
            if identity in seen:
                raise ValueError("duplicate_requested_explanation")
            seen.add(identity)
    canonical = deepcopy(value)
    if declarations is not None:
        canonical["declared_occurrences"] = sorted(declarations, key=lambda r: (r["role"], r["sound_ref"]))
    if requests is not None:
        canonical["requested_explanations"] = sorted(requests, key=lambda r: (r["stage"], r["geometry_id"], r["side"]))
    return canonical


def _selection_identity(state, selector):
    _closed(selector, {"group_id", "variant_ids", "key_id", "transition"}, "hypothesis_selector")
    data = state.data
    group_id, ids, key_id = selector["group_id"], selector["variant_ids"], selector["key_id"]
    if type(group_id) is not str or group_id not in state.lookups["groups"]:
        raise ValueError("explicit_original_progression_group_required")
    group = indexed._thaw(data["index"]["path_groups"][state.lookups["groups"][group_id]])
    slots = group["slots"]
    if len(slots) not in (1, 2):
        raise ValueError("complete_original_one_or_two_slot_partition_required")
    if (type(ids) is not list or len(ids) != len(slots)
            or any(type(v) is not str or v not in slot["variant_ids"] for v, slot in zip(ids, slots))):
        raise ValueError("complete_ordered_original_progression_variant_ids_required")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate_progression_origin")
    if type(key_id) is not str or key_id not in state.lookups["keys"]:
        raise ValueError("registered_original_progression_key_required")
    a, b = span_bounds(data["scope"]["analysis_span"])
    bounds = [span_bounds(s["span"]) for s in slots]
    if (bounds[0][0] != a or bounds[-1][1] != b or any(x >= y for x, y in bounds)
            or any(left[1] != right[0] for left, right in zip(bounds, bounds[1:]))):
        raise ValueError("original_partition_must_cover_exact_analysis_span")
    if len(slots) == 1:
        if selector["transition"] is not None:
            raise ValueError("fullhold_has_no_transition_assumption")
        transition = None
    else:
        transition = _transition(state, group_id, selector["transition"])
    key = indexed._thaw(data["index"]["keys"][state.lookups["keys"][key_id]])
    origins = [None if v not in state.lookups["variants"] else
        indexed._thaw(data["index"]["variant_inventory"][state.lookups["variants"][v]]) for v in ids]
    if transition is not None:
        # Clause identity must be checked even when a later admission cap
        # prevents planning or assessment.  This does not restore profiles.
        delayed._explanation_clauses(state, group_id, origins, transition["requested_explanations"])
    logical_tuple = indexed._tuple_identity(data["index"], group, ids, key)
    identity = {"selector": deepcopy(selector), "logical_tuple": logical_tuple, "group_id": group_id,
        "indexed_group_id": group["indexed_group_id"], "partition": deepcopy(group["partition"]),
        "slot_spans": [deepcopy(s["span"]) for s in slots], "origin_variant_ids": list(ids),
        "origin_refs": [None if o is None else _ref(o["variant"]) for o in origins],
        "profile_refs": [None if o is None else deepcopy(o["profile_ref"]) for o in origins], "key_ref": _ref(key)}
    return identity, group, origins, key, transition


def _plan(state, selection):
    """Pre-count the selected assessments, never their favorable prefix.

    This logical quota is deliberately not a CPU, byte, RSS or lifetime cap.
    The small frozen clause/role inventories can be inspected for planning;
    no profile, membership account or delayed query is computed here.
    """
    identity, group, origins, key, transition = selection
    data = state.data
    profile_count = 0
    profiles_available = True
    for origin in origins:
        did = None if origin is None else origin["profile_ref"]["record_id"]
        if did not in state.lookups["profiles"]:
            profiles_available = False
        else:
            profile_count += len(data["grounding"]["profile_inventory"][state.lookups["profiles"][did]]["row_ids"])
    requested = None if transition is None else transition["requested_explanations"]
    clauses, descriptors, sounds, full_count = delayed._explanation_clauses(state, group["group_id"], origins, requested)
    if transition is None and any(c["stage"] != "local" for c in clauses):
        raise ValueError("fullhold_boundary_geometry_not_applicable")
    known = profile_count + len(clauses)
    complete = (profiles_available and group["logical_path_count"] is not None
        and data["scope"]["context_sound_inventory_complete"] is True
        and data["temporal"]["summary"]["local_contour_relation_inventory_complete"])
    if transition is not None:
        function = None if any(o is None for o in origins) else frozen._function({}, origins[0]["variant"],
            origins[1]["variant"], key["segments"][0], transition["family"], transition["quality"])
        kernel = None
        if all(o is not None for o in origins):
            kkey = (group["group_id"], origins[0]["profile_ref"]["record_id"], origins[1]["profile_ref"]["record_id"],
                transition["family"], transition["quality"])
            if kkey in state.lookups["kernels"]:
                kernel = indexed._thaw(data["obligations"]["obligation_kernel_inventory"][state.lookups["kernels"][kkey]])
        ordinary, choices = delayed._strategy(state, kernel, transition["strategy"], transition["declared_occurrences"], set(), False)
        known += sum(len(r["occurrence_assessments"]) for r in ordinary["role_assessments"]) + sum(map(len, choices))
        complete = complete and data["boundary"]["summary"]["membership_inventory_complete"] and (
            (function is not None and function["status"] != "conditional_function_shape") or ordinary["inventory_complete"])
    return {"planned_query_work_items": known if complete else None, "known_stored_query_work_subtotal": known,
        "clauses": clauses, "descriptors": descriptors, "sounds": sounds, "all_clause_count": full_count}


def _function_shapes(origins, key, transition, transition_assessed, assumption_evaluated):
    rows = []
    for slot, origin in enumerate(origins):
        following = None if slot + 1 == len(origins) else origins[slot + 1]
        for family in frozen.FAMILIES:
            for quality in ("M", "m"):
                function = None if origin is None else frozen._function({}, origin["variant"],
                    None if following is None else following["variant"], key["segments"][0], family, quality)
                explicit = transition is not None and slot == 0 and family == transition["family"] and quality == transition["quality"]
                rows.append({"slot": slot, "source_variant_id": None if origin is None else origin["variant_id"],
                    "target_variant_id": None if following is None else following["variant_id"],
                    "family": family, "quality": quality, "function": function,
                    "terminal": slot + 1 == len(origins), "explicit_transition_assumption": explicit,
                    "transition_assumption_evaluated": explicit and assumption_evaluated,
                    "motion_assessed": explicit and transition_assessed,
                    "motion_status": "assessed_only_this_explicit_transition_assumption" if explicit and transition_assessed else "unassessed",
                    "function_confirmed": None})
    return rows


def _aggregate(profiles, accounts):
    if accounts is None or any(p is None for p in profiles) or any(a is None for a in accounts):
        return None
    total = sum((f(a["total_note_time"]) for a in accounts), Fraction())
    categories = {name: sum((f(a["note_time"][name]) for a in accounts), Fraction()) for name in CATEGORIES}
    raw_names = set(accounts[0]["raw_note_time"])
    if any(set(a["raw_note_time"]) != raw_names for a in accounts):
        raise ValueError("whole_path_raw_membership_category_mismatch")
    raw = {name: sum((f(a["raw_note_time"][name]) for a in accounts), Fraction()) for name in sorted(raw_names)}
    spans_by_sound = defaultdict(list)
    for account in accounts:
        for row in account["credited_intervals_by_sound"]:
            spans_by_sound[row["sound_ref"]].extend(row["spans"])
    credited = [{"sound_ref": sid, "spans": temporal._union(spans)} for sid, spans in sorted(spans_by_sound.items())]
    credit = sum((temporal._duration(row["spans"]) for row in credited), Fraction())
    if sum(categories.values(), Fraction()) != total or sum(raw.values(), Fraction()) != total:
        raise ValueError("whole_path_raw_note_time_loss")
    if credit != categories["conditional_combined_explained_nonmember"]:
        raise ValueError("whole_path_per_sound_interval_union_credit_mismatch")
    assessed = all(a["conditional_explanation_note_time"] is not None for a in accounts)
    return {"raw_note_time": {k: q(v) for k, v in raw.items()}, "total_note_time": q(total),
        "note_time": {k: q(v) for k, v in categories.items()},
        "conditional_explanation_note_time": q(credit) if assessed else None,
        "credited_intervals_by_sound": credited, "slot_accounts": deepcopy(accounts),
        "combined_accounting_basis": "disjoint_original_slots_and_per_sound_interval_union_under_one_actual_completion",
        "competing_function_credits_pooled": False}


def _path(state, selection, plan, bundle, budget):
    identity, group, origins, key, transition = selection
    complete = bundle is not None and bundle["status"] == "complete_all_lane_witness"
    if transition is not None:
        query = delayed._query(state, group["group_id"], *identity["origin_variant_ids"], key["record_id"],
            transition["family"], transition["quality"], bundle, transition["strategy"],
            transition["declared_occurrences"], transition["requested_explanations"], budget)
        if query["planned_query_work_items"] != plan["planned_query_work_items"]:
            raise ValueError("progression_whole_request_query_work_plan_mismatch")
        profiles, accounts = query["profiles"], query["combined_accounts"]
        assessments = query["explanation_assessments"]
        assumption_evaluated = query["status"] != "whole_delayed_query_source_or_work_inventory_hold"
        transition_assessed = (assumption_evaluated and query["obligation_kernel_ref"] is not None
            and query["ordinary_strategy"]["inventory_complete"]
            and query["ordinary_strategy"]["role_assessments"] is not None)
    else:
        restored = [boundary._profile(state, v) for v in identity["origin_variant_ids"]]
        profiles = [p for p, _ in restored]
        links = set() if bundle is None else temporal._links(bundle)
        explained, assessments = [], []
        for clause in plan["clauses"]:
            satisfied = complete and clause["qualified"] and all(tuple(e) in links for e in clause["required_links"])
            if satisfied:
                explained.extend(clause["explained_items"])
            assessments.append({"stage": clause["stage"], "geometry_id": clause["geometry_id"], "side": clause["side"],
                "blockers": clause["blockers"], "status": "conditional_explanation_under_this_same_completion" if satisfied else
                "unassessed_completion" if not complete else "withheld_clause_prerequisites" if not clause["qualified"] else
                "not_satisfied_under_this_completion_not_global_absence"})
        accounts = [delayed._account(profiles[0], plan["descriptors"][0], plan["sounds"], explained, complete)]
        query, transition_assessed, assumption_evaluated = None, False, False
    account = _aggregate(profiles, accounts)
    source_blockers = sorted({c for p in profiles if p is not None for c in p["blockers"]})
    row_guards = [{"sound_ref": row["sound_ref"], "blockers": sorted(set(temporal._guard_codes(plan["sounds"][row["sound_ref"]])
        + frozen._source_blockers(plan["sounds"][row["sound_ref"]])))} for p in profiles if p is not None for row in p["rows"]]
    axes = {"same_complete_all_lane_bundle": complete,
        "completion_certified_impossible": bundle is not None and bundle.get("geometry_condition_status") == "impossible",
        "source_sound_inventory_complete": state.data["scope"]["context_sound_inventory_complete"],
        "profiles_available": all(p is not None for p in profiles), "hypothesis_blockers": source_blockers,
        "source_guard_ledger": row_guards, "combined_accounts_computed": account is not None,
        "direct_motion_applicable": transition is not None, "boundary_explanation_applicable": transition is not None,
        "delayed_ordinary_applicable": transition is not None,
        "registered_local_clause_count": sum(c["stage"] == "local" for c in plan["clauses"]),
        "registered_boundary_clause_count": sum(c["stage"] == "boundary" for c in plan["clauses"]),
        "registered_delayed_transition_count": 0 if transition is None else 1,
        "ordinary_strategy": None if query is None else deepcopy(query["ordinary_strategy"]),
        "old_direct_status": None if query is None else query["old_direct_status"],
        "literal_core_and_time_audit": None if query is None else deepcopy(query["literal_core_and_time_audit"]),
        "slot_literal_core_and_bass": [None if p is None else deepcopy(p["cells"]) for p in profiles],
        "terminal_function_motion_assessed": False, "whole_path_harmony_assessed": False}
    return _seal({"version": VERSION, **identity, "scope_ref": _ref(state.data["scope"]),
        "analysis_span": indexed._thaw(state.data["scope"]["analysis_span"]), "bundle_ref": None if bundle is None else _ref(bundle),
        "profiles": profiles, "function_shapes": _function_shapes(origins, key, transition, transition_assessed, assumption_evaluated),
        "transition_assumption": deepcopy(transition), "transition_assessment": query,
        "whole_path_account": account, "explanation_assessments": assessments, "axes": axes,
        "planned_query_work_items": plan["planned_query_work_items"],
        "known_stored_query_work_subtotal": plan["known_stored_query_work_subtotal"],
        "finite_clause_coverage": "all_registered_for_selected_origins" if transition is None or transition["requested_explanations"] is None else "explicit_requested_subset",
        "known_registered_finite_clause_subtotal": plan["all_clause_count"],
        "unrequested_registered_clause_count": plan["all_clause_count"] - len(plan["clauses"]),
        "status": "computed_conditional_whole_path_evidence_not_selected" if account is not None else "whole_path_account_unassessed",
        "reasons": [] if account is not None else ["whole_path_account_not_available"],
        "selected": None, "rank": None, "confidence": None, "flags": _flags()}, PATH_PREFIX)


def _contrast(left, right, i, j):
    reasons = []
    if not indexed._same(left["scope_ref"], right["scope_ref"]) or not indexed._same(left["analysis_span"], right["analysis_span"]):
        reasons.append("same_source_and_analysis_span_required")
    if not indexed._same(left["bundle_ref"], right["bundle_ref"]):
        reasons.append("same_actual_bundle_required")
    if not left["axes"]["same_complete_all_lane_bundle"] or not right["axes"]["same_complete_all_lane_bundle"]:
        reasons.append("complete_actual_all_raw_lane_bundle_required")
    if left["whole_path_account"] is None or right["whole_path_account"] is None:
        reasons.append("both_whole_path_accounts_required")
    delta = None
    raw_delta = None
    total_delta = None
    if not reasons:
        a, b = left["whole_path_account"], right["whole_path_account"]
        if f(a["total_note_time"]) != f(b["total_note_time"]):
            raise ValueError("same_scope_complete_partition_raw_note_time_invariant_failed")
        delta = {k: q(f(b["note_time"][k]) - f(a["note_time"][k])) for k in CATEGORIES}
        raw_delta = {k: q(f(b["raw_note_time"][k]) - f(a["raw_note_time"][k])) for k in a["raw_note_time"]}
        total_delta = q(Fraction())
    return _seal({"version": VERSION, "left_index": i, "right_index": j,
        "left_hypothesis_ref": _ref(left), "right_hypothesis_ref": _ref(right),
        "left_logical_tuple_ref": _ref(left["logical_tuple"]), "right_logical_tuple_ref": _ref(right["logical_tuple"]),
        "same_original_partition": left["group_id"] == right["group_id"],
        "comparable": not reasons, "category_note_time_delta": delta,
        "raw_membership_note_time_delta": raw_delta, "total_note_time_delta": total_delta,
        "delta_orientation": "right_minus_left_in_caller_order_not_a_preference",
        "status": "computed_same_scope_category_contrast_not_ranking" if not reasons else "contrast_unassessed",
        "reasons": reasons, "winner": None, "selected": None, "rank": None, "confidence": None,
        "flags": _flags()}, CONTRAST_PREFIX)


def _summary(state, selections, paths, contrasts, plans, whole_hold):
    universe = state.data["obligations"]["logical_universe"]
    requested = {row[0]["logical_tuple"]["record_id"] for row in selections}
    tested = {p["logical_tuple"]["record_id"] for p in paths}
    shapes = {(p["logical_tuple"]["record_id"], r["slot"], r["family"], r["quality"])
        for p in paths for r in p["function_shapes"] if r["function"] is not None}
    assessed = {(p["logical_tuple"]["record_id"], r["slot"], r["family"], r["quality"])
        for p in paths for r in p["function_shapes"] if r["motion_assessed"]}
    evaluated = {(p["logical_tuple"]["record_id"], r["slot"], r["family"], r["quality"])
        for p in paths for r in p["function_shapes"] if r["transition_assumption_evaluated"]}
    tuples = universe["logical_path_key_tuples"]
    functions = universe["logical_function_rows"]
    tuple_unknown = universe["unknown_product_groups"] != 0
    known_work = sum(p["known_stored_query_work_subtotal"] for p in plans)
    planned_work = None if whole_hold and not plans or any(p["planned_query_work_items"] is None for p in plans) else sum(p["planned_query_work_items"] for p in plans)
    return {**{k: indexed._thaw(universe[k]) for k in ("logical_paths", "logical_path_key_tuples", "logical_function_rows", "unknown_product_groups")},
        "planned_hypotheses": len(selections), "computed_hypotheses": len(paths),
        "planned_comparisons": len(selections) * (len(selections) - 1) // 2, "computed_comparisons": len(contrasts),
        "comparable_comparisons": sum(c["comparable"] for c in contrasts),
        "unique_requested_logical_tuples": len(requested), "tested_logical_path_key_tuples": len(tested),
        "known_unassessed_logical_path_key_tuple_subtotal": tuples - len(tested),
        "unassessed_logical_path_key_tuples": None if tuple_unknown else tuples - len(tested),
        "restored_function_shape_rows": len(shapes), "tested_function_shapes": len(shapes),
        "unassessed_function_shapes": None if functions is None or tuple_unknown else functions - len(shapes),
        "known_unassessed_function_shape_subtotal": None if functions is None else functions - len(shapes),
        "assessed_transition_function_rows": len(assessed),
        "unassessed_transition_function_rows": None if functions is None or tuple_unknown else functions - len(assessed),
        "evaluated_transition_assumption_rows": len(evaluated),
        "unassessed_transition_assumption_rows": None if functions is None or tuple_unknown else functions - len(evaluated),
        "whole_path_accounts_computed": sum(p["whole_path_account"] is not None for p in paths),
        "planned_query_work_items": planned_work, "known_stored_query_work_subtotal": known_work,
        "count_semantics": "distinct_exact_original_tuple_keys_and_slot_family_quality_rows_not_selector_multiplicity_or_confidence"}


def compare_prepared(session, hypotheses, bundle_id, *, max_hypotheses=64, max_comparisons=4096, query_work_budget=100000):
    """Contrast explicit whole paths under a single registered completion.

    All selectors are validated and all requested logical work is planned
    before any assessment.  A request hold emits no favorable partial panel.
    """
    limits = dict(zip(CAPS, (max_hypotheses, max_comparisons, query_work_budget)))
    _caps(limits)
    authority, state = _issued(session)
    if type(hypotheses) is not list:
        raise ValueError("explicit_progression_hypothesis_selector_list_required")
    no_bundle = bundle_id is None and not state.lookups["bundles"]
    if not no_bundle and (type(bundle_id) is not str or bundle_id not in state.lookups["bundles"]):
        raise ValueError("registered_actual_same_universe_obligation_bundle_required")
    contract = _contract()
    try:
        before = digest([hypotheses, bundle_id])
    except (TypeError, ValueError) as error:
        raise ValueError("typed_JSON_progression_selector_list_required") from error
    selections, seen = [], set()
    for selector in hypotheses:
        selection = _selection_identity(state, selector)
        canonical = {"group_id": selector["group_id"], "variant_ids": selector["variant_ids"],
            "key_id": selector["key_id"], "transition": selection[4]}
        identity = indexed._encoded(canonical)
        if identity in seen:
            raise ValueError("duplicate_progression_hypothesis_selector")
        seen.add(identity)
        selections.append(selection)
    bundle = None if no_bundle else indexed._thaw(state.data["registered_bundles"][state.lookups["bundles"][bundle_id]])
    n = len(selections)
    reasons = []
    if n > max_hypotheses:
        reasons.append("whole_hypothesis_inventory_budget_hold_no_prefix")
    if n * (n - 1) // 2 > max_comparisons:
        reasons.append("whole_pair_contrast_inventory_budget_hold_no_prefix")
    plans = []
    if not reasons:
        plans = [_plan(state, selection) for selection in selections]
        if any(plan["planned_query_work_items"] is None for plan in plans):
            reasons.append("whole_selected_source_or_assessment_inventory_unknown_no_prefix")
        elif sum(plan["planned_query_work_items"] for plan in plans) > query_work_budget:
            reasons.append("whole_query_work_budget_hold_no_prefix")
    paths, contrasts = [], []
    if not reasons:
        paths = [_path(state, selection, plan, bundle, query_work_budget) for selection, plan in zip(selections, plans)]
        available_totals = {f(p["whole_path_account"]["total_note_time"]) for p in paths if p["whole_path_account"] is not None}
        if len(available_totals) > 1:
            raise ValueError("same_scope_complete_partition_raw_note_time_invariant_failed")
        contrasts = [_contrast(paths[i], paths[j], i, j) for i in range(n) for j in range(i + 1, n)]
    record = state.data["obligations"]
    result = _seal({"version": VERSION, "contract": contract, "binding": indexed._thaw(record["binding"]),
        "analysis_span": indexed._thaw(record["analysis_span"]),
        **{name + "_ref": indexed._thaw(record[name + "_ref"]) for name in
            ("scope", "hypotheses", "index", "relations", "grounding", "temporal", "boundary")},
        "obligations_ref": _ref(record), "logical_universe": indexed._thaw(record["logical_universe"]),
        "bundle_ref": None if bundle is None else _ref(bundle), "bundle_id": bundle_id,
        "bundle_status": None if bundle is None else bundle["status"],
        "selectors": deepcopy(hypotheses), "selector_inventory": [deepcopy(s[0]) for s in selections],
        "hypotheses": paths, "contrasts": contrasts, "resource_limits": limits,
        "summary": _summary(state, selections, paths, contrasts, plans, bool(reasons)),
        "status": "whole_comparison_source_or_work_hold" if reasons else "computed_same_scope_evidence_not_selected",
        "reasons": reasons, "selected": None, "preferred": None, "winner": None, "rank": None, "confidence": None,
        "flags": _flags(), "resource_limit_semantics": "whole_request_logical_assessment_quota_no_prefix_not_CPU_byte_RSS_or_lifetime_bound",
        "validation_semantics": "authentic_owned_phase19_authority_before_and_after_with_current_transitive_code_contract",
        "limits": ["Original fullhold and one-cut partitions cover the same scope; they are never concatenated into a longer path.",
            "An incomplete primary source or selected assessment inventory holds the whole requested panel, not a favorable prefix.",
            "One explicit transition strategy is an assumption, not a winner or a universal doubling obligation.",
            "Only clauses satisfied under this one actual all-raw-lane completion can credit nonmember intervals.",
            "Terminal and competing function shapes survive without motion assessment; their unknowns are not failures.",
            "Category differences do not infer harmony, key, NCT, cadence, ranking, confidence, training or musical accuracy."]}, PREFIX)
    current, upstream = _issued(session)
    if current is not authority or upstream is not state or before != digest([hypotheses, bundle_id]) or not indexed._same(contract, _contract()):
        raise ValueError("progression_selectors_authority_or_code_changed_during_comparison")
    return result


def compare(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record,
            comparison_hypotheses, bundle_id, **options):
    if set(options) - set(CAPS):
        raise TypeError("unknown_progression_comparison_limit")
    _caps({**DEFAULTS, **options})
    return compare_prepared(prepare_comparison(ir, scope, hypotheses, index, relations, grounding,
        temporal_record, boundary_record, record), comparison_hypotheses, bundle_id, **options)


def validate_comparison(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record,
                        comparison_hypotheses, bundle_id, result, **options):
    """Replay the real current parent chain, not a caller's re-sealed body."""
    frozen._check(result, PREFIX)
    if not indexed._same(result, compare(ir, scope, hypotheses, index, relations, grounding, temporal_record,
            boundary_record, record, comparison_hypotheses, bundle_id, **options)):
        raise ValueError("stale_foreign_modified_or_promoting_progression_comparison")
    return True
