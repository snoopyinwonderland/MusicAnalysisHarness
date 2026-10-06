"""One explicit COMPLETE historical completion under one owned read account.

All original metadata/creation/ancestor contracts are checked by the frozen
pure metadata consumer. Only the selected completion's complete ordered bodies
are parsed; all original and omitted denominators remain separate. This is not
a full-archive run, native authority, contrast calculation, writer or winner.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from weakref import WeakKeyDictionary

from . import shared_source_archive_bridge as bridge
from . import cross_batch_read_budget as budget
from . import shared_source_progression_contrast as shared
from .musical_pattern_observation import digest

old, sealed, replay, join = bridge.old, bridge.sealed, bridge.replay, bridge.join
VERSION = "scoped-source-archive-pilot-0.1.0"
AUTHORITY = "one_complete_original_saved_completion_not_full_archive_or_native_authority"
_PLANS, _ARCHIVES = WeakKeyDictionary(), WeakKeyDictionary()
# Pure dependency, NOT the old bridge's capability registry or public loader.
_load_metadata = bridge._load_metadata
_record, _batch, _job, _entry = bridge._record, replay._batch, replay._job, join._entry


def _flags():
    return {**bridge._flags(), "full_archive": False, "all_original_bodies_validated": False,
        "physical_original_request_admission": False}


class ScopedPlan:
    __slots__ = ("__weakref__",)

    def __new__(cls): raise ValueError("scoped_plan_factory_required")

    def __setattr__(self, name, value): raise AttributeError("immutable_owned_scoped_plan")

    def record(self):
        data = _plan(self)
        return {"version": VERSION, "authority": "declared_scope_not_original_membership",
            "directory": data["directory"], "selection": list(data["selection"]),
            "read_plan": data["read_plan"].record(), "original_metadata_membership_authenticated": False,
            "source_limits": asdict(data["source_limits"]), "group_limits": asdict(data["group_limits"]),
            "current_dependency_SHA": deepcopy(data["current"]), "flags": _flags()}


class ScopedArchive:
    __slots__ = ("__weakref__",)

    def __new__(cls): raise ValueError("scoped_archive_factory_required")

    def __setattr__(self, name, value): raise AttributeError("owned_scoped_archive")


def _plan(handle):
    if type(handle) is not ScopedPlan or handle not in _PLANS:
        raise ValueError("owned_scoped_plan_required_not_JSON")
    return _PLANS[handle]


def _archive(handle):
    if type(handle) is not ScopedArchive or handle not in _ARCHIVES:
        raise ValueError("owned_scoped_archive_required_not_JSON")
    return _ARCHIVES[handle]


class ScopedFailure(ValueError):
    def __init__(self, reason, *, plan=None, reader=None, metadata=None):
        self.report = {"version": VERSION, "reason": reason,
            "plan": None if plan is None else plan.record(),
            "read_ledger": None if reader is None else budget.read_ledger(reader),
            "metadata": deepcopy(metadata), "flags": _flags()}
        super().__init__(reason)


def plan_scoped_reads(directory, reads, *, source_index, completion_index,
        original_denominators, registered_sha256, inventory_roots, output_directory=None,
        read_limits=None, admission_limits=None, source_limits=None, group_limits=None):
    """Declare ALL metadata + ALL bodies of ONE completion before any parse.

    Historical registrations must be original expected SHA/root snapshots. New
    current dependencies are separate and never added to historical membership.
    """
    for value in (source_index, completion_index): old._limit(value, "original_selection_index")
    directory = str(budget._path(directory))
    if type(inventory_roots) is not tuple or not inventory_roots:
        raise ValueError("explicit_original_inventory_root_tuple_required")
    if admission_limits and any(k in admission_limits for k in
            ("max_file_bytes", "max_decoded_file_bytes", "max_total_decoded_bytes")):
        raise ValueError("one_cumulative_read_account_owns_byte_limits")
    settings = bridge.kernels._settings({} if admission_limits is None else admission_limits)
    source_limits = shared.SourceLimits() if source_limits is None else source_limits
    group_limits = shared.GroupLimits() if group_limits is None else group_limits
    if type(source_limits) is not shared.SourceLimits or type(group_limits) is not shared.GroupLimits:
        raise ValueError("typed_source_and_group_limits_required")
    if type(registered_sha256) is not dict:
        raise ValueError("exact_original_registered_SHA_map_required")
    registered, current = deepcopy(registered_sha256), {}
    modules = (bridge, bridge.kernels, budget, shared)
    paths = sorted({str(Path(module.__file__).resolve()) for module in modules} | {str(Path(__file__).resolve())})
    for path in paths:
        sha = old._file_sha(path)
        if path in registered and registered[path] != sha:
            raise ValueError("current_dependency_conflicts_with_original_SHA")
        current[path] = sha
    read_plan = budget.plan_read_run(reads, original_denominators=original_denominators,
        registered_sha256={**registered, **current}, inventory_roots=inventory_roots,
        source_archive_roots=(directory,), output_directory=output_directory, limits=read_limits)
    handle = object.__new__(ScopedPlan)
    _PLANS[handle] = {"directory": directory, "selection": (source_index, completion_index),
        "read_plan": read_plan, "registered": registered, "roots": deepcopy(inventory_roots),
        "current": current, "settings": settings, "source_limits": source_limits, "group_limits": group_limits}
    return handle


def _remaining_selected_membership(data, reader, metadata):
    planned, consumed = data["read_plan"].record()["reads"], reader.read_files
    if any(r["phase"] != "metadata" for r in planned[:consumed]):
        raise ValueError("complete_metadata_prefix_must_have_metadata_phase")
    jobs = [j for j in metadata["jobs"] if
        (j["request"]["source_index"], j["request"]["completion_index"]) == data["selection"]]
    if len(jobs) != 1:
        raise ValueError("exact_one_original_completion_selection_required")
    expected = [batch[name] for batch in jobs[0]["row"]["batches"] for name in ("comparison", "explanation")]
    remaining = planned[consumed:]
    if len(remaining) != len(expected):
        raise ValueError("all_selected_completion_body_occurrences_required_no_prefix_or_extra")
    for occurrence, info in zip(remaining, expected):
        if (occurrence["path"] != info["artifact"] or occurrence["sha256"] != info["sha256"]
                or occurrence["phase"] != "body"
                or occurrence["encoding"] != ("gzip-json" if Path(info["artifact"]).suffix == ".gz" else "json")
                or occurrence["physical_bytes"] is None or occurrence["decoded_bytes"] is None):
            raise ValueError("exact_ordered_selected_comparison_explanation_read_membership_required")
    return jobs[0], consumed


def open_scoped_archive(plan):
    data = _plan(plan)
    reader = budget.begin_reads(data["read_plan"])
    try:
        metadata = _load_metadata(data, reader)
        job, metadata_reads = _remaining_selected_membership(data, reader, metadata)
    except BaseException as exc:
        budget.finish_reads(reader)
        raise ScopedFailure("scoped_metadata_failure:" + type(exc).__name__ + ":" + str(exc),
            plan=plan, reader=reader) from exc
    handle = object.__new__(ScopedArchive)
    _ARCHIVES[handle] = {**data, **metadata, "reader": reader, "selected_job": job,
        "metadata_read_occurrences": metadata_reads, "source": None, "groups": (),
        "active_iterator": False, "failure": None, "body_failure": None, "finished": False,
        "source_plan": None, "group_plans": [], "source_holds": [], "group_holds": []}
    return handle


def _declarations(state):
    return [{"source_index": j["request"]["source_index"], "completion_index": j["request"]["completion_index"],
        "group_index": gi, "original": {"source_identity_sha256": j["case"]["source_identity_sha256"],
            "scope_ref": sealed._ref(j["case"]["scope"]), "lattice_ref": sealed._ref(j["case"]["lattice"]),
            **deepcopy(g)}} for j in state["jobs"] for gi, g in enumerate(j["groups"])]


def _counts(jobs):
    groups = [g for j in jobs for g in j["groups"]]
    return {"completion_requests": len(jobs), "selector_occurrences": sum(j["plan"]["planned_selectors"] for j in jobs),
        "batches": sum(j["plan"]["planned_batches"] for j in jobs), "groups": len(groups),
        "pairs": sum(g["planned_pairs"] for g in groups), "block_tasks": sum(g["planned_block_tasks"] for g in groups)}


def metadata_prepared(handle):
    state = _archive(handle)
    selected = state["selected_job"]
    declarations = _declarations(state)
    selection = state["selection"]
    return {"version": VERSION, "authority": AUTHORITY,
        "original_metadata_membership_authenticated": state["metadata_authenticated"],
        "selection": list(selection), "original_denominators": deepcopy(state["read_plan"].record()["original_denominators"]),
        "whole_original": _counts(state["jobs"]), "selected_completion": _counts([selected]),
        "omitted_completions": _counts([j for j in state["jobs"] if j is not selected]),
        "original_group_declarations": declarations,
        "selected_group_declarations": [deepcopy(d) for d in declarations if
            (d["source_index"], d["completion_index"]) == selection],
        "original_creation_code_files": len(state["plan"]["code"]),
        "original_parent_inventory_counts": [len(r["registered_sha256"]) for r in state["inventories"][1:]],
        "metadata_read_occurrences": state["metadata_read_occurrences"],
        "source_limits": asdict(state["source_limits"]), "group_limits": asdict(state["group_limits"]),
        "source_preflight": deepcopy(state["source_plan"]), "group_preflights": deepcopy(state["group_plans"]),
        "source_holds": deepcopy(state["source_holds"]), "group_holds": deepcopy(state["group_holds"]),
        "selected_body_terminal_validated": selected["consumed"], "prepared_groups": len(state["groups"]),
        "failure": state["failure"], "body_failure": state["body_failure"], "finished": state["finished"],
        "read_ledger": budget.read_ledger(state["reader"]), "selected": None, "flags": _flags()}


def _live(state):
    # Every reader exception passes through the scoped consumer and poisons
    # this state. Avoid O(batch_count^2) copies of the growing read ledger.
    if state["finished"] or state["failure"]:
        raise ValueError("terminal_or_failed_scope_cannot_issue_cached_capabilities")


def _source_inputs(state):
    case = state["selected_job"]["case"]
    # Both ORIGINAL bundles, but never entries borrowed from another request.
    bundles = {j["bundle"]["record_id"]: j["bundle"] for j in state["jobs"]
        if j["request"]["source_index"] == state["selection"][0]}
    return case, bundles


def source_preflight(handle):
    state = _archive(handle); _live(state)
    case, bundles = _source_inputs(state)
    try:
        plan = shared.preflight_saved_source(case["scope"], case["lattice"], bundles=bundles, limits=state["source_limits"])
        state["source_plan"] = plan.record()
        state["source_holds"] = [deepcopy(state["source_plan"])] if plan.reasons else []
        return deepcopy(state["source_plan"])
    except BaseException as exc:
        state["failure"] = "source_preflight_failure:" + type(exc).__name__
        raise


def source_prepared(handle):
    state = _archive(handle); _live(state)
    if state["source"] is not None: return state["source"]
    case, bundles = _source_inputs(state)
    try:
        source = shared.prepare_saved_source(case["scope"], case["lattice"], bundles=bundles, limits=state["source_limits"])
        _live(state)
        state["source"] = source
        state["source_plan"] = source.preflight_plan.record()
    except shared.WholeSourceHold as exc:
        state["failure"] = "whole_selected_source_hold_no_denominator_shrink"
        state["source_holds"] = [exc.plan.record()]
        state["source_plan"] = exc.plan.record()
        raise ScopedFailure(state["failure"], reader=state["reader"], metadata=metadata_prepared(handle)) from exc
    except BaseException as exc:
        state["failure"] = state["failure"] or "source_intrinsic_failure:" + type(exc).__name__
        raise
    return source


def iter_selected_entries(handle):
    """Yield validated whole batches; exhaustion validates terminal, not yield."""
    state = _archive(handle); _live(state)
    job = state["selected_job"]
    if state["active_iterator"] or job["iterator_started"]:
        raise ValueError("selected_iterator_no_restart_or_concurrency")
    job["iterator_started"], state["active_iterator"] = True, True
    case, bundle, plan = job["case"], job["bundle"], job["plan"]
    counts = replay._empty_counts(plan["planned_selectors"], plan["planned_batches"])
    counts["fresh_bundle_registrations"] = 1
    origins = {o["record_id"]: o for c in case["lattice"]["catalog_inventory"] for o in c["origins"]}
    keys = {k["record_id"]: k for k in case["lattice"]["keys"]}
    refs, seen = [], set()
    try:
        for batch in job["row"]["batches"]:
            _live(state)
            planned = {k: batch[k] for k in replay.PLAN_BATCH_KEYS}
            lo, hi = batch["selector_start"], batch["selector_end_exclusive"]
            selectors = case["proposal"]["selectors"][lo:hi]
            comparison = _record(batch["comparison"], replay.engine.native.COMPARISON_PREFIX, state["reader"], state["hashes"])
            explanation = _record(batch["explanation"], replay.engine.roles.PREFIX, state["reader"], state["hashes"])
            _batch(comparison, explanation, selectors, case, bundle, planned, state["replay_limits"])
            if len(comparison["paths"]) != len(selectors) or len(explanation["paths"]) != len(selectors):
                raise ValueError("all_selected_native_role_ordinals_required")
            entries = []
            for ordinal, (selector, path, role) in enumerate(zip(selectors, comparison["paths"], explanation["paths"])):
                if role["native_path_ref"] != sealed._ref(path):
                    raise ValueError("exact_selected_role_array_ordinal_required")
                identity = digest(path["logical_tuple"])
                if identity in seen: raise ValueError("duplicate_selected_logical_tuple_not_signature_alias")
                seen.add(identity)
                entries.append({"selector_index": lo + ordinal, "entry": _entry(path, role, selector,
                    comparison, explanation, case["lattice"], case["scope"], bundle, origins, keys)})
            replay._add_batch(counts, comparison, explanation, bundle)
            refs.append({**deepcopy(planned), "comparison_ref": sealed._ref(comparison), "explanation_ref": sealed._ref(explanation)})
            _live(state)
            job["validated_batches"] += 1
            job["entries"].extend(entries)
            yield {"completion_request_ref": sealed._ref(job["request"]), "batch_index": batch["batch_index"],
                "selector_start": lo, "selector_end_exclusive": hi, "entries": deepcopy(entries)}
            _live(state)
        _job(job["terminal"], case, job["binding"], plan, bundle, job["row"]["original_control"],
            refs, counts, state["replay_limits"], [])
        _live(state)
        if [r["selector_index"] for r in job["entries"]] != list(range(plan["planned_selectors"])):
            raise ValueError("whole_selected_selector_ordinal_inventory_required")
        job["consumed"] = True
    except BaseException as exc:
        state["failure"] = state["failure"] or "selected_completion_failure:" + type(exc).__name__
        state["body_failure"] = state["body_failure"] or state["failure"]
        raise
    finally:
        state["active_iterator"] = False
        if not job["consumed"]:
            state["failure"] = state["failure"] or "selected_iterator_closed_before_terminal_validation"
            state["body_failure"] = state["body_failure"] or state["failure"]


def _group_inputs(state):
    job = state["selected_job"]
    if not job["consumed"]: raise ValueError("whole_selected_body_terminal_membership_required")
    by_index = {r["selector_index"]: r["entry"] for r in job["entries"]}
    if len(by_index) != len(job["entries"]) or sorted(by_index) != list(range(job["plan"]["planned_selectors"])):
        raise ValueError("all_selected_original_selector_ordinals_required")
    return [(g, [by_index[i] for i in g["selector_indices"]]) for g in job["groups"]]


def _group_kwargs(group):
    return {"completion_request_ref": group["completion_request_ref"], "selector_indices": group["selector_indices"],
        "key_ref": group["key_ref"], "bundle_ref": group["bundle_ref"], "block_size": group["block_size"]}


def preflight_selected_groups(handle):
    state = _archive(handle); _live(state)
    inputs = _group_inputs(state)
    source = source_prepared(handle)
    try:
        plans = [{"group_index": gi, "original_group": deepcopy(group),
            "plan": shared.preflight_saved_group(source, entries, **_group_kwargs(group), limits=state["group_limits"]).record()}
            for gi, (group, entries) in enumerate(inputs)]
        _live(state)
        state["group_plans"] = plans
        state["group_holds"] = deepcopy([p for p in plans if p["plan"]["reasons"]])
        return deepcopy(plans)
    except BaseException as exc:
        state["failure"] = state["failure"] or "selected_group_preflight_failure:" + type(exc).__name__
        raise


def prepare_selected_groups(handle):
    state = _archive(handle); _live(state)
    if state["groups"]: return state["groups"]
    plans = preflight_selected_groups(handle)
    held = [p for p in plans if p["plan"]["reasons"]]
    if held:
        state["group_holds"] = deepcopy(held)
        state["failure"] = "whole_selected_group_preflight_hold_no_prefix_or_denominator_shrink"
        raise ScopedFailure(state["failure"], reader=state["reader"], metadata=metadata_prepared(handle))
    try:
        source = source_prepared(handle)
        groups = tuple(shared.prepare_saved_group(source, entries, **_group_kwargs(group), limits=state["group_limits"])
            for group, entries in _group_inputs(state))
        _live(state)
        state["groups"] = groups
        return groups
    except BaseException as exc:
        state["failure"] = state["failure"] or "selected_intrinsic_group_failure:" + type(exc).__name__
        raise ScopedFailure(state["failure"], reader=state["reader"], metadata=metadata_prepared(handle)) from exc


def finish_scoped_archive(handle):
    state = _archive(handle)
    if state["active_iterator"]:
        state["failure"] = state["failure"] or "scope_finished_with_active_selected_iterator"
        state["body_failure"] = state["body_failure"] or state["failure"]
    state["finished"] = True
    ledger = budget.finish_reads(state["reader"])
    complete = not state["body_failure"] and ledger["submitted_read_set_complete"] and state["selected_job"]["consumed"]
    intrinsic = complete and not state["failure"] and state["source"] is not None and len(state["groups"]) == len(state["selected_job"]["groups"])
    return {**metadata_prepared(handle), "read_ledger": ledger,
        "selected_completion_body_join_complete": complete,
        "selected_source_intrinsic_groups_complete": intrinsic,
        "completed_selected_completions": int(complete), "omitted_original_completion_requests": len(state["jobs"]) - 1,
        "full_archive_complete": False, "all_original_indexed_batches_join_validated": False,
        "all_original_source_intrinsic_groups_validated": False}
