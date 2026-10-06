"""One whole owned scoped request -> v2 groups -> source-once storage plan.

This coordinator consumes the public original-body iterator itself. Metadata
JSON, a prior resource receipt and a caller's selector list are not admission.
The frozen scoped reader's old group flags remain unchanged. Read closure,
v2 group admission, storage reservation and actual persisted comparisons are
separate truths, and none selects a musical interpretation or a full archive.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
from pathlib import Path
import secrets
from weakref import WeakKeyDictionary

from . import scoped_source_archive_pilot as scoped
from . import cross_batch_progression_storage as original_codec
from . import cross_batch_read_budget as reads
from . import lossless_json_dag_v2 as dag
from . import proof_shared_source_progression_contrast as core
from . import shared_source_progression_contrast as source_core

VERSION = "transfer-bound-whole-request-coordinator-0.2.0"
_SECRET = secrets.token_bytes(32)
_PREPARATIONS = WeakKeyDictionary()


@dataclass(frozen=True, slots=True)
class RequestLimits:
    max_selector_occurrences: int = 131072
    max_batch_packets: int = 8192
    max_groups: int = 128
    max_metadata_bytes: int = 4194304
    max_coordination_work: int = 1000000000

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError("exact_nonnegative_request_limit_required:" + name)


class WholeRequestHold(ValueError):
    def __init__(self, reason, report):
        # A diagnostic snapshot is deliberately not a preparation capability.
        # Transfer the already-created diagnostic; do not perform a hidden,
        # potentially large second serialization after an early budget hold.
        self.report = report
        super().__init__(reason)


class RequestFailure(ValueError):
    """A failed invocation with its non-refundable original-reader terminal."""
    def __init__(self, reason, terminal):
        self.report = {"failure": reason, "read_terminal": terminal,
            "prepared_v2_groups": 0, "pairs_evaluated": 0,
            "full_archive": False, "flags": original_codec._flags()}
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class _State:
    record: bytes
    source: source_core.PreparedSource
    groups: tuple
    storage_plan: object
    coordination_work: int
    signature: bytes = b""


def _signature(owner, state):
    return hmac.digest(_SECRET, repr((id(owner), id(state.record), id(state.source),
        id(state.groups), id(state.storage_plan), state.coordination_work)).encode("ascii"), "sha256")


class RequestPreparation:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("owned_whole_request_factory_required_not_JSON")

    def __setattr__(self, name, value):
        raise AttributeError("immutable_owned_request_preparation")

    def record(self):
        state = _issued(self)
        result = json.loads(state.record)
        # Keep the final encoding cost OUT of the encoded snapshot itself;
        # self-referential sizing must not cause an uncharged second encoding.
        result["coordination_work_upper_bound"] = state.coordination_work
        return result

    @property
    def storage_plan(self):
        return _issued(self).storage_plan


def _issued(handle):
    if type(handle) is not RequestPreparation or handle not in _PREPARATIONS:
        raise ValueError("owned_whole_request_preparation_required_not_summary")
    state = _PREPARATIONS[handle]
    if (type(state) is not _State or type(state.record) is not bytes
            or type(state.groups) is not tuple
            or type(state.coordination_work) is not int or state.coordination_work < 0
            or not hmac.compare_digest(state.signature, _signature(handle, state))):
        raise ValueError("owned_whole_request_state_changed")
    source_core._source_issued(state.source)
    for group in state.groups:
        if core._issued(group).source is not state.source:
            raise ValueError("exact_owned_source_required_for_every_group")
    return state


def _denominators(metadata, limits):
    for key in ("whole_original", "selected_completion", "omitted_completions"):
        count = metadata[key]
        if type(count) is not dict or set(count) != {"completion_requests", "selector_occurrences",
                "batches", "groups", "pairs", "block_tasks"}:
            raise ValueError("closed_original_request_denominators_required")
        if any(type(v) is not int or v < 0 for v in count.values()):
            raise ValueError("exact_original_request_denominators_required")
    for key, value in metadata["whole_original"].items():
        if value != metadata["selected_completion"][key] + metadata["omitted_completions"][key]:
            raise ValueError("original_selected_omitted_denominators_disagree")
    selected = metadata["selected_completion"]
    if selected["completion_requests"] != 1:
        raise ValueError("exactly_one_whole_original_request_required")
    if (selected["selector_occurrences"] > limits.max_selector_occurrences
            or selected["batches"] > limits.max_batch_packets or selected["groups"] > limits.max_groups):
        raise WholeRequestHold("whole_request_count_limit_no_prefix", {"metadata": metadata})
    return selected


def _counts(metadata, limits):
    selected = _denominators(metadata, limits)
    declarations = metadata["selected_group_declarations"]
    if type(declarations) is not list or not declarations or len(declarations) != selected["groups"]:
        raise ValueError("all_original_nonempty_group_declarations_required")
    assigned = []
    originals = []
    for ordinal, declaration in enumerate(declarations):
        if (type(declaration) is not dict or declaration.get("group_index") != ordinal
                or type(declaration.get("group_index")) is not int
                or [declaration.get("source_index"), declaration.get("completion_index")] != metadata["selection"]
                or any(type(declaration.get(k)) is not int for k in ("source_index", "completion_index"))):
            raise ValueError("exact_ordered_selected_group_declaration_required")
        original, _ = original_codec._original(declaration["original"])
        originals.append(original)
        assigned.extend(original["selector_indices"])
    if sorted(assigned) != list(range(selected["selector_occurrences"])):
        raise ValueError("groups_must_partition_every_original_selector_exactly_once")
    if (sum(o["planned_pairs"] for o in originals) != selected["pairs"]
            or sum(o["planned_block_tasks"] for o in originals) != selected["block_tasks"]):
        raise ValueError("original_group_pair_or_block_denominator_disagrees")
    if len({original_codec._raw(o["completion_request_ref"]) for o in originals}) != 1:
        raise ValueError("independent_completion_requests_must_not_be_unioned")
    return originals


def _collect(archive, originals, expected):
    """Exhaustion, not the last yield, authenticates the upstream terminal."""
    by_selector = {}
    iterator = scoped.iter_selected_entries(archive)
    packet = row = None
    complete = False
    packets = 0
    try:
        for packet in iterator:
            if (type(packet) is not dict or type(packet.get("batch_index")) is not int
                    or packet["batch_index"] != packets
                    or packet["completion_request_ref"] != originals[0]["completion_request_ref"]
                    or type(packet.get("entries")) is not list
                    or type(packet.get("selector_start")) is not int
                    or type(packet.get("selector_end_exclusive")) is not int
                    or packet["selector_start"] != len(by_selector)
                    or packet["selector_end_exclusive"] - packet["selector_start"] != len(packet["entries"])):
                raise ValueError("whole_ordered_request_batch_required")
            for row in packet["entries"]:
                index = row.get("selector_index") if type(row) is dict else None
                if (type(index) is not int or index != len(by_selector)
                        or index >= expected["selector_occurrences"] or type(row.get("entry")) is not dict):
                    raise ValueError("exact_request_selector_order_no_prefix_or_duplicate")
                by_selector[index] = row["entry"]
            packets += 1
            if packets > expected["batches"]:
                raise ValueError("extra_request_batch_not_declared")
        if packets != expected["batches"] or len(by_selector) != expected["selector_occurrences"]:
            raise ValueError("all_original_request_batches_and_selectors_required")
        complete = True
        return by_selector, packets
    finally:
        try:
            iterator.close()
        except BaseException:
            if complete:
                raise
        finally:
            if not complete:
                by_selector.clear()
            iterator = packet = row = None


def _snapshot(value, limits, spent):
    # One logical scan plus the plain-JSON check and canonical encoding.
    # Reserve all three passes before ANY whole snapshot serialization.
    remaining = limits.max_coordination_work - spent
    stat = dag.preflight_json(value, limits=dag.DagLimits(
        max_expanded_bytes=limits.max_metadata_bytes,
        max_work_units=max(0, remaining // 3)))
    work = spent + 3 * stat["charged_work_units"]
    if work > limits.max_coordination_work:
        raise WholeRequestHold("whole_coordination_work_limit_no_prefix",
            {"coordination_work_upper_bound": work, "metadata_bytes": stat["expanded_bytes"]})
    raw = original_codec._raw(value)
    if len(raw) != stat["expanded_bytes"]:
        raise ValueError("canonical_metadata_size_contract_changed")
    return raw, work


def _protected_inputs(archive, supplied, roots, archive_roots):
    # Copy expected registrations from an issued reader, never today's glob.
    state = scoped._archive(archive)
    expected = dict(state["hashes"])
    for path, sha in state["current"].items():
        if path in expected and expected[path] != sha:
            raise ValueError("conflicting_current_and_historical_SHA")
        expected[path] = sha
    if supplied is not None:
        if type(supplied) is not dict or any(expected.get(p, sha) != sha for p, sha in supplied.items()):
            raise ValueError("caller_cannot_override_expected_archive_SHA")
        expected.update(supplied)
    issued_roots = tuple(reads.InventoryRoot(r["directory"], dict(r["registered_sha256"]))
        for r in state["inventories"])
    # Extra caller constraints may strengthen, but never replace/remove, the
    # exact root membership authenticated by this original scoped reader.
    roots = issued_roots + (() if roots is None else tuple(roots))
    by_directory = {}
    for root in roots:
        if type(root) is not reads.InventoryRoot:
            raise ValueError("typed_expected_inventory_root_required")
        directory = str(Path(root.directory).resolve())
        if directory in by_directory and by_directory[directory].registered_sha256 != root.registered_sha256:
            raise ValueError("caller_cannot_override_original_inventory_membership")
        by_directory[directory] = root
    roots = tuple(by_directory.values())
    archive_roots = (state["directory"],) + (() if archive_roots is None else tuple(archive_roots))
    for module in (scoped, core, source_core, dag):
        path = str(Path(module.__file__).resolve())
        sha = original_codec._file_sha(path)
        if path in expected and expected[path] != sha:
            raise ValueError("current_request_dependency_SHA_changed")
        expected[path] = sha
    path = str(Path(__file__).resolve())
    sha = original_codec._file_sha(path)
    if path in expected and expected[path] != sha:
        raise ValueError("request_coordinator_SHA_conflict")
    expected[path] = sha
    return expected, roots, archive_roots


def prepare_selected_request(archive, *, limits=None, group_limits=None, storage_limits=None,
        protected_sha256=None, protected_roots=None, source_archive_roots=None):
    """Consume one fresh owned scope completely, then reserve ALL v2 output.

    This closes the scoped reader; it cannot be restarted or used to issue old
    groups afterwards. Storage reason(s) are an honest whole-request hold;
    merely obtaining this object does not authorize begin_storage on a hold.
    """
    from . import transfer_bound_progression_storage as storage
    limits = RequestLimits() if limits is None else limits
    if type(limits) is not RequestLimits:
        raise ValueError("typed_whole_request_limits_required")
    # Validate ownership/freshness before taking responsibility for closing it.
    owned = scoped._archive(archive)
    if owned["finished"] or owned["failure"] or owned["body_failure"] or owned["active_iterator"] or owned["selected_job"]["consumed"] or owned["groups"]:
        raise ValueError("fresh_owned_original_request_required_not_saved_metadata")
    by_selector = {}
    plans, prepared, items = [], [], []
    source = terminal = None
    finish_attempted = False
    local_entries = None
    initial = after = originals = registrations = report = raw = state = None
    group = plan = saved = records = original = None
    try:
        group_limits = owned["group_limits"] if group_limits is None else group_limits
        if (type(group_limits) is not source_core.GroupLimits
                or any(getattr(group_limits, name) > getattr(owned["group_limits"], name)
                    for name in group_limits.__dataclass_fields__)):
            raise ValueError("group_limits_may_only_tighten_owned_original_request")
        initial = scoped.metadata_prepared(archive)
        if initial["original_metadata_membership_authenticated"] is not True:
            raise ValueError("authenticated_original_metadata_required")
        selected = _denominators(initial, limits)
        raw, spent = _snapshot(initial, limits, 0)
        raw = None
        # Budget the count/partition/ref checks, indexing, packet validation and
        # group indexing before those loops. No pair-by-atom planning is done.
        n = selected["selector_occurrences"]
        indexing = 32 * (n + selected["groups"] + selected["batches"]) + 8 * n * max(1, n.bit_length())
        spent += indexing + 1024  # bounded capability/HMAC issue bookkeeping
        if spent > limits.max_coordination_work:
            raise WholeRequestHold("whole_coordination_index_work_limit_no_prefix", {"metadata": initial})
        originals = _counts(initial, limits)
        registrations = _protected_inputs(archive, protected_sha256, protected_roots, source_archive_roots)
        by_selector, packets = _collect(archive, originals, initial["selected_completion"])
        after = scoped.metadata_prepared(archive)
        if (after["selected_body_terminal_validated"] is not True or after["failure"] is not None
                or after["selected_group_declarations"] != initial["selected_group_declarations"]):
            raise ValueError("whole_request_exhaustion_and_unchanged_declarations_required")
        source = scoped.source_prepared(archive)
        for original in originals:
            local_entries = [by_selector[i] for i in original["selector_indices"]]
            plans.append(core.preflight_saved_group(source, local_entries,
                completion_request_ref=original["completion_request_ref"], selector_indices=original["selector_indices"],
                key_ref=original["key_ref"], bundle_ref=original["bundle_ref"],
                block_size=original["block_size"], limits=group_limits))
            local_entries.clear()
        finish_attempted = True
        terminal = scoped.finish_scoped_archive(archive)
        if (terminal["failure"] is not None or terminal["body_failure"] is not None
                or terminal["selected_completion_body_join_complete"] is not True
                or terminal["read_ledger"]["submitted_read_set_complete"] is not True):
            raise WholeRequestHold("original_read_terminal_guard_failed_no_v2_promotion", {"read_terminal": terminal})
        records = [p.record() for p in plans]
        if any(p.reasons or p.stage != "complete" for p in plans):
            raise WholeRequestHold("whole_original_v2_group_hold_no_prefix",
                {"read_terminal": terminal, "all_original_group_preflights": records,
                    "prepared_v2_groups": 0, "pairs_evaluated": 0})
        for original, plan in zip(originals, plans):
            group = core.prepare_preflight(plan)
            prepared.append(group)
            items.append(storage.GroupInput(original, source, group))
        saved = storage.plan_saved_run(items, original_denominators=initial["original_denominators"],
            protected_sha256=registrations[0], protected_roots=registrations[1],
            source_archive_roots=registrations[2], limits=storage_limits)
        report = {"version": VERSION, "authority": "one_owned_original_selected_request_not_full_archive",
            "selection": initial["selection"], "whole_original": initial["whole_original"],
            "selected_completion": initial["selected_completion"], "omitted_completions": initial["omitted_completions"],
            "read_terminal": terminal, "all_original_group_preflights": records,
            "prepared_v2_groups": len(prepared), "storage_plan": saved.record(), "pairs_evaluated": 0,
            "coordination_work_scope": "metadata_guard_encoding_and_selector_indexing_only_separate_from_source_group_storage",
            "coordination_work_before_final_snapshot": spent, "full_archive": False,
            "saved_JSON_restores_capability": False, "flags": original_codec._flags()}
        raw, final_work = _snapshot(report, limits, spent)
        handle = object.__new__(RequestPreparation)
        state = _State(raw, source, tuple(prepared), saved, final_work)
        _PREPARATIONS[handle] = _State(state.record, state.source, state.groups, state.storage_plan,
            state.coordination_work, _signature(handle, state))
        return handle
    except BaseException as error:
        if not finish_attempted:
            finish_attempted = True
            try:
                terminal = scoped.finish_scoped_archive(archive)
            except BaseException as finish_error:
                terminal = {"finished": False, "terminal_error": type(finish_error).__name__, "costs_confirmed": False}
        # Retain diagnostic costs, not the new private source/group copies.
        if hasattr(error, "report") and type(error.report) is dict:
            error.report.setdefault("read_terminal", terminal)
            raise
        if isinstance(error, (KeyboardInterrupt, SystemExit, GeneratorExit)):
            error.read_terminal = terminal
            raise
        raise RequestFailure(type(error).__name__ + ":" + str(error), terminal) from error
    finally:
        by_selector.clear()
        if local_entries is not None:
            local_entries.clear()
        plans.clear(); prepared.clear(); items.clear()
        source = group = plan = saved = local_entries = state = None
        initial = after = originals = terminal = report = raw = records = original = registrations = owned = None


def request_ledger(preparation, storage_run):
    from . import transfer_bound_progression_storage as storage
    state = _issued(preparation)
    # Readonly ownership comparison; never insert a foreign storage registry.
    if storage._store(storage_run)["data"] is not storage._plan(state.storage_plan):
        raise ValueError("same_owned_request_storage_run_required")
    saved = storage.ledger(storage_run)
    report = preparation.record()
    expected = report["selected_completion"]
    coverage = (saved["planned_submitted_groups"] == expected["groups"]
        and saved["planned_submitted_entries"] == expected["selector_occurrences"]
        and saved["summary"]["planned_pairs"] == expected["pairs"])
    return {"version": VERSION, "selection": report["selection"],
        "whole_original": report["whole_original"], "selected_completion": expected,
        "omitted_completions": report["omitted_completions"], "original_selected_read_closure_verified": True,
        "same_request_storage_coverage": coverage,
        "selected_request_storage_complete": coverage and saved["submitted_group_set_complete"],
        "storage": saved, "full_archive_complete": False, "flags": original_codec._flags()}
