"""Fresh, same-completion evidence for every admitted saved-source request.

An archive is a request, not native authority. Exact fresh supplier equality
precedes an owned session; every original completion is registered anew.
Small batches bound role-union work, not the global competitor universe.
No contrast, policy, winner, harmonic answer, UI or training promotion occurs.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import hmac
from pathlib import Path
import secrets
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import factor_expanded_hypotheses as kernels
from . import factor_expanded_scope as expanded
from . import factor_indexed_hypotheses as owned
from . import factor_interval_lattice as native
from . import factor_native_role_explanations as roles
from . import source_progression_proposals as proposals
from . import source_progression_proposal_trial as saved_validation
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "source-progression-replay-0.1.0"
PREFIX = "npsreplayjob_"
BINDING_PREFIX = "npsrebind_"
PLAN_PREFIX = "npsreplayplan_"
DEFAULTS = dict(max_selectors=4096, max_slots=3, batch_size=3,
    replay_work_budget=1000000000000, native_query_work_budget=2000000,
    role_query_work_budget=100000000, geometry_work_budget=100000)
_SESSIONS = WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)


def _contract():
    return {"version": VERSION, "native_contract": native._contract(),
        "role_contract": roles._contract(), "proposal_contract": proposals._contract(),
        "sources": [{"module": m.__name__, "sha256": sha256(Path(m.__file__).read_bytes()).hexdigest()}
            for m in (saved_validation, owned)],
        "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest()}


def _flags():
    return {name: False for name in ("archived_ids_used_as_native_authority",
        "source_annotation_labels_used", "supplier_ornaments_used_as_NCT_credit",
        "independent_completions_unioned", "all_logical_paths_evaluated",
        "full_contrast_evaluated", "policy_evaluated", "winning_harmony_selected",
        "function_confirmed", "secondary_confirmed", "cadence_confirmed", "NCT_confirmed",
        "training_eligible", "gold_eligible", "generation_ready", "production_modified",
        "musical_accuracy_measured")}


def _limits(values):
    if set(values) - set(DEFAULTS):
        raise ValueError("unknown_source_replay_limit")
    result = {**DEFAULTS, **values}
    for name, value in result.items():
        native._integer(value, name)
    if not 1 <= result["batch_size"] <= 64:
        raise ValueError("source_replay_batch_size_1_through_64_required")
    return result


def _validate_saved(scope, lattice, proposal, prior_panel):
    proposals._nodes([scope, lattice, proposal, prior_panel])
    proposals._validate_sources(scope, lattice, prior_panel)
    saved_validation._validate_result(proposal,
        {"scope": scope, "lattice": lattice, "panel": prior_panel}, proposal["resource_limits"])
    if not owned._same(proposal["contract"], proposals._contract()):
        raise ValueError("current_saved_proposal_contract_required")


def _plan(scope, lattice, proposal, limits):
    origins = {o["record_id"]: o for e in lattice["catalog_inventory"] for o in e["origins"]}
    keys = {k["record_id"]: k for k in lattice["keys"]}
    selectors = proposal["selectors"]
    batches = []
    # Numerical planning only: no profiles, actual routes, native sessions or
    # explanations are produced here. ALL batches precede the first query.
    for index, lo in enumerate(range(0, len(selectors), limits["batch_size"])):
        hi = min(lo + limits["batch_size"], len(selectors))
        values = selectors[lo:hi]
        selections = [(s, [origins[oid] for oid in s["origin_ids"]], keys[s["key_id"]]) for s in values]
        np = native._query_plan(scope, selections)
        rp = roles._plan(scope, [], values)
        batches.append({"batch_index": index, "selector_start": lo, "selector_end_exclusive": hi,
            "native_query_work": np["planned_query_work"], "role_query_work": rp["planned_query_work"],
            "charged_native_comparisons": 2,
            "charged_work": 2 * np["planned_query_work"] + rp["planned_query_work"]})
    reasons = []
    if proposal["status"] != "computed_source_progression_proposals_not_evaluated":
        reasons.append("complete_saved_source_proposal_unavailable")
    if lattice["status"] != "ready_native_interval_lattice":
        reasons.append("complete_saved_native_lattice_unavailable")
    if len(selectors) > limits["max_selectors"]:
        reasons.append("whole_source_selector_request_exceeds_budget_no_prefix")
    if any(len(s["origin_ids"]) > limits["max_slots"] for s in selectors):
        reasons.append("whole_source_slot_request_exceeds_budget_no_prefix")
    if any(b["native_query_work"] > limits["native_query_work_budget"] for b in batches):
        reasons.append("a_native_batch_exceeds_predeclared_budget_no_prefix")
    if any(b["role_query_work"] > limits["role_query_work_budget"] for b in batches):
        reasons.append("a_role_batch_exceeds_predeclared_budget_no_prefix")
    total = sum(b["charged_work"] for b in batches)
    if total > limits["replay_work_budget"]:
        reasons.append("whole_source_replay_work_exceeds_budget_no_prefix")
    return kernels._seal({"version": VERSION, "proposal_ref": kernels._ref(proposal),
        "scope_ref": kernels._ref(scope), "lattice_ref": kernels._ref(lattice),
        "selector_inventory_sha256": digest(selectors), "planned_selectors": len(selectors),
        "retained_control_selectors": len(proposal["retained_control_selectors"]),
        "additional_selectors": len(proposal["additional_selectors"]), "batches": batches,
        "planned_batches": len(batches), "planned_replay_work": total,
        "native_comparison_work": sum(2 * b["native_query_work"] for b in batches),
        "role_explanation_work": sum(b["role_query_work"] for b in batches),
        "resource_limits": limits, "status": "whole_source_replay_request_hold" if reasons else "ready_native_role_batches",
        "reasons": sorted(set(reasons)), "flags": _flags(),
        "semantics": "logical_native_twice_plus_role_once_per_batch_not_CPU_RSS_or_accuracy",
        "full_contrast_status": "deferred_whole_competitor_adapter_required_not_batch_comparison"}, PLAN_PREFIX)


def plan_saved(scope, lattice, proposal, *, prior_panel, **limits):
    before = digest([scope, lattice, proposal, prior_panel])
    contract = _contract()
    _validate_saved(scope, lattice, proposal, prior_panel)
    result = _plan(scope, lattice, proposal, _limits(limits))
    if before != digest([scope, lattice, proposal, prior_panel]) or not owned._same(contract, _contract()):
        raise ValueError("source_replay_plan_inputs_or_contract_changed")
    return result


class _PreparedReplay:
    __slots__ = ("__weakref__",)


@dataclass(frozen=True)
class _State:
    native_session: object
    native_state: object
    data: object
    contract_digest: str
    authentication: bytes


def _auth(handle, state):
    return hmac.digest(_SECRET, owned._encoded([id(handle), id(state), id(state.data),
        id(state.native_session), id(state.native_state), state.contract_digest]), "sha256")


def _issued(handle):
    if type(handle) is not _PreparedReplay or handle not in _SESSIONS:
        raise ValueError("issued_fresh_source_replay_session_required")
    state = _SESSIONS[handle]
    if type(state) is not _State or type(state.data) is not MappingProxyType:
        raise ValueError("source_replay_immutable_owned_state_required")
    if (state.contract_digest != digest(_contract())
            or not hmac.compare_digest(state.authentication, _auth(handle, state))):
        raise ValueError("stale_or_modified_source_replay_session")
    if state.native_session is not None and native._issued(state.native_session) is not state.native_state:
        raise ValueError("source_replay_native_parent_state_identity_changed")
    return state


def prepare_replay(ir, scope, archived_lattice, proposal, *, prior_panel):
    before, contract = digest([ir, scope, archived_lattice, proposal, prior_panel]), _contract()
    _validate_saved(scope, archived_lattice, proposal, prior_panel)
    expanded.check_scope(scope, ir=ir)
    session = native_state = fresh = None
    preparations = 0
    reasons = []
    if proposal["status"] != "computed_source_progression_proposals_not_evaluated":
        reasons.append("complete_saved_source_proposal_unavailable")
    if archived_lattice["status"] != "ready_native_interval_lattice":
        reasons.append("complete_saved_native_lattice_unavailable")
    if not reasons:
        # No saved record is passed: authority is freshly built from full IR.
        session = native.prepare_lattice(ir, scope, **archived_lattice["resource_limits"])
        preparations = 1
        native_state = native._issued(session)
        fresh = native.lattice_prepared(session)
        if not owned._same(fresh, archived_lattice):
            reasons.append("whole_fresh_supplier_inventory_or_provenance_drift_no_partial_rebind")
            session = native_state = None
    origin_maps = []; key_maps = []
    if session is not None:
        used = {oid for s in proposal["selectors"] for oid in s["origin_ids"]}
        for entry in fresh["catalog_inventory"]:
            for origin in entry["origins"]:
                if origin["record_id"] in used:
                    origin_maps.append({"archived_ref": kernels._ref(origin), "fresh_ref": kernels._ref(origin),
                        "catalog_id": entry["catalog_id"], "point_indices": deepcopy(entry["point_indices"]),
                        "exact_complete_origin_body_match": True})
        key_maps = [{"archived_ref": kernels._ref(key), "fresh_ref": kernels._ref(key),
                     "exact_complete_key_body_match": True} for key in fresh["keys"]]
        # IDs may coincide deterministically; this validation uses fresh state.
        for selector in proposal["selectors"]:
            native._selector(native_state, selector)
    receipt = kernels._seal({"version": VERSION, "contract": contract,
        "source_binding": deepcopy(scope["binding"]), "scope_ref": kernels._ref(scope),
        "analysis_span": deepcopy(scope["analysis_span"]), "logical_universe": deepcopy(archived_lattice["universe"]),
        "archived_lattice_ref": kernels._ref(archived_lattice),
        "fresh_lattice_ref": None if fresh is None else kernels._ref(fresh),
        "proposal_ref": kernels._ref(proposal), "prior_panel_ref": kernels._ref(prior_panel),
        "origin_mappings": origin_maps, "key_mappings": key_maps,
        "retained_control_selectors": len(proposal["retained_control_selectors"]),
        "additional_selectors": len(proposal["additional_selectors"]), "total_selectors": len(proposal["selectors"]),
        "selector_inventory_sha256": digest(proposal["selectors"]),
        "fresh_native_preparations": preparations, "native_authority_issued": session is not None,
        "status": "whole_source_rebind_hold" if reasons else "ready_fresh_source_proposal_replay",
        "reasons": reasons, "selected": None, "rank": None, "confidence": None, "flags": _flags()}, BINDING_PREFIX)
    data = owned._freeze({"binding": receipt, "proposal": proposal,
        # A held bridge needs numerical planning but no live native authority.
        "held_scope": scope if session is None else None,
        "held_lattice": archived_lattice if session is None else None})
    if (before != digest([ir, scope, archived_lattice, proposal, prior_panel])
            or not owned._same(contract, _contract())):
        raise ValueError("source_replay_inputs_or_contract_changed_during_preparation")
    handle = _PreparedReplay()
    state = _State(session, native_state, data, digest(contract), b"")
    object.__setattr__(state, "authentication", _auth(handle, state))
    _SESSIONS[handle] = state
    _issued(handle)
    return handle


def binding_prepared(handle):
    return owned._thaw(_issued(handle).data["binding"])


def lattice_prepared(handle):
    state = _issued(handle)
    return None if state.native_session is None else native.lattice_prepared(state.native_session)


def _truth(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "unknown"
    raise ValueError("strict_replay_evidence_tristate_required")


def _validate_batch(comparison, explanation, selectors, scope, lattice, bundle):
    kernels._check(comparison, native.COMPARISON_PREFIX)
    kernels._check(explanation, roles.PREFIX)
    if (comparison["selectors"] != selectors or comparison["scope_ref"] != kernels._ref(scope)
            or comparison["lattice_ref"] != kernels._ref(lattice)
            or comparison["bundle_ref"] != kernels._ref(bundle)
            or explanation["native_comparison_ref"] != kernels._ref(comparison)
            or explanation["bundle_ref"] != comparison["bundle_ref"]
            or explanation["native_request"]["selectors"] != selectors
            or explanation["summary"]["planned_paths"] != len(selectors)):
        raise ValueError("exact_fresh_batch_source_selector_completion_join_required")
    raw = sum((f(s["observed_span"]["end"]) - f(s["observed_span"]["start"])
               for s in scope["sound_facts"] if not s["point"]), Fraction())
    for path, selector in zip(comparison["paths"], selectors):
        kernels._check(path, "fmilpath_")
        if (path["logical_tuple"]["transition_assumptions"] != selector["transition_assumptions"]
                or [r["record_id"] for r in path["origin_refs"]] != selector["origin_ids"]
                or path["key_ref"]["record_id"] != selector["key_id"]
                or f(path["whole_path_account"]["raw_total_note_time_quarters"]) != raw
                or path["whole_path_account"]["raw_time_conserved"] is not True):
            raise ValueError("native_batch_exact_path_and_raw_time_required")
    if comparison["status"] != "whole_comparison_hold" and len(comparison["paths"]) != len(selectors):
        raise ValueError("complete_native_batch_denominator_required")
    native_paths = {p["record_id"]: p for p in comparison["paths"]}
    if explanation["status"] != "whole_explanation_hold" and len(explanation["paths"]) != len(comparison["paths"]):
        raise ValueError("complete_role_batch_denominator_required")
    for path in explanation["paths"]:
        kernels._check(path, "fmnrolepath_")
        parent = native_paths[path["native_path_ref"]["record_id"]]
        account = path["account"]
        if (path["native_path_ref"] != kernels._ref(parent)
                or path["origin_refs"] != parent["origin_refs"] or path["key_ref"] != parent["key_ref"]
                or path["bundle_ref"] != parent["bundle_ref"]
                or path["raw_account_pointer"]["sha256"] != digest(parent["whole_path_account"])
                or f(account["raw_total_note_time_quarters"]) != raw
                or sum((f(v) for v in account["note_time_quarters"].values()), Fraction()) != raw
                or account["raw_time_conserved"] is not True or account["union_counted_once"] is not True):
            raise ValueError("role_batch_exact_parent_rational_conservation_required")
    return True


def stream_prepared(handle, required_links, **limits):
    """Yield detached header/batches/terminal; exhaustion is required for completion.

    Budget holds return header+terminal, not a favorable computed prefix.
    Unexpected runtime holds preserve every subsequent submitted position.
    """
    settings = _limits(limits)
    state = _issued(handle)
    binding, proposal = (owned._thaw(state.data[k]) for k in ("binding", "proposal"))
    scope = owned._thaw(state.data["held_scope"] if state.native_session is None else state.native_state.data["scope"])
    lattice = owned._thaw(state.data["held_lattice"] if state.native_session is None else state.native_state.data["lattice"])
    proposals._nodes(required_links)
    if type(required_links) is not list:
        raise ValueError("ordered_explicit_original_completion_links_required")
    links_before = digest(required_links)
    links = deepcopy(required_links)
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    for pair in links:
        if (type(pair) is not list or len(pair) != 2 or any(type(s) is not str or s not in sounds for s in pair)
                or sounds[pair[0]]["lane"] is None or sounds[pair[0]]["lane"] != sounds[pair[1]]["lane"]):
            raise ValueError("exact_same_original_source_raw_lane_links_required")
    plan = _plan(scope, lattice, proposal, settings)
    reasons = sorted(set(plan["reasons"] + binding["reasons"]))
    summary = {"planned_selectors": len(proposal["selectors"]), "native_computed_paths": 0, "role_computed_paths": 0,
        "planned_batches": plan["planned_batches"], "completed_batches": 0,
        "native_comparison_calls": 0, "role_preparation_calls": 0, "role_explanation_calls": 0,
        "fresh_bundle_registrations": 0, "ordinary_individual_supported_occurrences": 0,
        "computed_internal_transition_contexts": 0, "declared_internal_function_contexts": 0,
        "resolution_contexts_under_complete_bundle": 0,
        "whole_ordinary_template_truths": {k: 0 for k in ("true", "false", "unknown")},
        "role_whole_ordinary_template_truths": {k: 0 for k in ("true", "false", "unknown")},
        "joint_functional_truths": {k: 0 for k in ("true", "false", "unknown")},
        "role_clause_status_occurrences": {}, "raw_time_conserved_native_paths": 0,
        "raw_time_conserved_role_paths": 0, "unknown_role_accounts": 0}
    bundle = None
    if not reasons:
        bundle = native.compile_bundle_prepared(state.native_session, links,
            geometry_work_budget=settings["geometry_work_budget"])
        summary["fresh_bundle_registrations"] = 1
    yield {"packet_type": "header", "binding_ref": kernels._ref(binding), "plan": deepcopy(plan),
        "bundle": deepcopy(bundle), "status": "whole_source_replay_request_hold" if reasons else "ready_native_role_batches",
        "reasons": deepcopy(reasons)}
    refs = []; known_credit = Fraction(); clause_counts = Counter()
    if not reasons:
        for batch in plan["batches"]:
            _issued(handle)
            if links_before != digest(required_links):
                raise ValueError("original_completion_links_changed_during_replay")
            lo, hi = batch["selector_start"], batch["selector_end_exclusive"]
            selectors = deepcopy(proposal["selectors"][lo:hi])
            comparison = native.compare_prepared(state.native_session, selectors, bundle["record_id"],
                max_hypotheses=settings["batch_size"], max_slots=settings["max_slots"],
                query_work_budget=settings["native_query_work_budget"])
            summary["native_comparison_calls"] += 1
            role_session = roles.prepare_explanations(state.native_session, comparison)
            summary["native_comparison_calls"] += 1
            summary["role_preparation_calls"] += 1
            explanation = roles.explain_prepared(role_session, query_work_budget=settings["role_query_work_budget"])
            summary["role_explanation_calls"] += 1
            _validate_batch(comparison, explanation, selectors, scope, lattice, bundle)
            del role_session
            summary["native_computed_paths"] += len(comparison["paths"])
            summary["role_computed_paths"] += len(explanation["paths"])
            for path in comparison["paths"]:
                summary["raw_time_conserved_native_paths"] += 1
                for ctx in path["transition_contexts"]:
                    summary["computed_internal_transition_contexts"] += 1
                    if ctx["function_shape"] is not None:
                        summary["declared_internal_function_contexts"] += 1
                        if bundle["status"] == "complete_all_lane_witness":
                            summary["resolution_contexts_under_complete_bundle"] += 1
                    summary["joint_functional_truths"][_truth(ctx["joint_conditional_functional_evidence"])] += 1
                    ordinary = ctx["ordinary_strategy"]
                    summary["whole_ordinary_template_truths"][_truth(None if ordinary is None else ordinary["whole_ordinary_template_satisfied"])] += 1
                    if ordinary:
                        summary["ordinary_individual_supported_occurrences"] += sum(
                            o["satisfied_under_this_bundle"] for r in ordinary["role_assessments"] for o in r["occurrences"])
            for path in explanation["paths"]:
                summary["raw_time_conserved_role_paths"] += 1
                for template in path["ordinary_templates"]:
                    summary["role_whole_ordinary_template_truths"][_truth(template["satisfied"])] += 1
                clause_counts.update(row["status"] for row in path["clauses"])
                credit = path["account"]["conditional_explanation_note_time_quarters"]
                if credit is None:
                    summary["unknown_role_accounts"] += 1
                else:
                    known_credit += f(credit)
            if comparison["status"] == "whole_comparison_hold" or explanation["status"] == "whole_explanation_hold":
                reasons.extend(["unexpected_runtime_batch_hold", *comparison["reasons"], *explanation["reasons"]])
            else:
                summary["completed_batches"] += 1
            refs.append({**deepcopy(batch), "comparison_ref": kernels._ref(comparison),
                         "explanation_ref": kernels._ref(explanation)})
            _issued(handle)
            # Aggregate/ref snapshots precede detached delivery. Caller mutation
            # cannot influence future batches or terminal counts.
            yield {"packet_type": "batch", "batch_index": batch["batch_index"], "selector_start": lo,
                   "selector_end_exclusive": hi, "comparison": comparison, "explanation": explanation}
            del comparison, explanation
    if links_before != digest(required_links):
        raise ValueError("original_completion_links_changed_during_replay")
    summary.update(withheld_native_paths=len(proposal["selectors"]) - summary["native_computed_paths"],
        withheld_role_paths=len(proposal["selectors"]) - summary["role_computed_paths"],
        uncomputed_role_accounts=len(proposal["selectors"]) - summary["role_computed_paths"],
        role_clause_status_occurrences=dict(sorted(clause_counts.items())),
        known_conditional_explained_note_time_selector_occurrence_subtotal=q(known_credit))
    summary["conditional_explained_note_time_selector_occurrence_sum"] = (
        None if reasons or summary["unknown_role_accounts"] or summary["uncomputed_role_accounts"] else q(known_credit))
    complete = (not reasons and summary["completed_batches"] == plan["planned_batches"])
    record = kernels._seal({"version": VERSION, "contract": _contract(), "binding_ref": kernels._ref(binding),
        "proposal_ref": kernels._ref(proposal), "scope_ref": kernels._ref(scope), "lattice_ref": kernels._ref(lattice),
        "analysis_span": deepcopy(scope["analysis_span"]), "logical_universe": deepcopy(lattice["universe"]),
        "plan_ref": kernels._ref(plan), "bundle_ref": None if bundle is None else kernels._ref(bundle),
        "required_links": deepcopy(links), "fresh_registered_links": None if bundle is None else deepcopy(bundle["materialized_witness_links"]),
        "bundle_status": None if bundle is None else bundle["status"], "batch_refs": refs,
        "resource_limits": settings, "summary": summary,
        "status": "computed_native_role_source_requests_not_selected" if complete else (
            "whole_source_replay_request_hold" if not refs else "incomplete_native_role_source_replay"),
        "reasons": sorted(set(reasons)), "fresh_native_evaluation_performed": summary["native_computed_paths"] > 0,
        "same_completion_resolution_evaluated": summary["resolution_contexts_under_complete_bundle"] > 0,
        "selected": None, "rank": None, "confidence": None,
        "flags": _flags(), "full_contrast_status": "deferred_whole_competitor_adapter_required_not_batch_comparison",
        "limitations": ["All submitted positions, not all logical paths or complete works, are calculated.",
            "Role geometry and union credit remain conditional; musical interpretation is not confirmed.",
            "No cross-batch contrast or policy is evaluated; no winner follows from these counts.",
            "Null credit for unassessed/withheld accounts is not zero and is never silently omitted."]}, PREFIX)
    _issued(handle)
    yield {"packet_type": "summary", "record": record}
