"""Bounded source-evidence proposals, not harmonic winners or role labels.

Every requested interval scans its complete native origin inventory before
choosing two distinct spelling signatures. Only exact raw guarded note-time
orders proposals. No supplier ornament, annotation label or role outcome is
used. The resulting two zipped paths are NOT the Cartesian product.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import hmac
from math import prod
from pathlib import Path
import secrets
from weakref import WeakKeyDictionary

from . import factor_expanded_hypotheses as kernels
from . import factor_indexed_hypotheses as owned
from . import factor_interval_lattice as native
from . import factor_temporal_explanations as temporal
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "factor-source-evidence-panel-0.1.0"
PREFIX = "fmsep_"
POLICY = "guarded_pooled_spelling_support_two_zipped_paths_fixed_observed_quantiles_all_keys"
_SESSIONS = WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)


def _contract():
    return {"version": VERSION, "native_contract": native._contract(),
        "sources": [{"module": m.__name__, "sha256": sha256(Path(m.__file__).read_bytes()).hexdigest()}
                    for m in (kernels, temporal, owned)],
        "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest()}


class _PreparedPanel:
    __slots__ = ("__weakref__",)


@dataclass(frozen=True)
class _State:
    native_session: object
    native_state: object
    contract_sha256: str
    authentication: bytes


def _auth(handle, state):
    return hmac.digest(_SECRET, owned._encoded([id(handle), id(state),
        id(state.native_session), id(state.native_state), state.contract_sha256]), "sha256")


def _issued(handle):
    if type(handle) is not _PreparedPanel or handle not in _SESSIONS:
        raise ValueError("internally_issued_source_panel_required")
    state = _SESSIONS[handle]
    if (type(state) is not _State or state.contract_sha256 != digest(_contract())
            or not hmac.compare_digest(state.authentication, _auth(handle, state))
            or native._issued(state.native_session) is not state.native_state):
        raise ValueError("source_panel_native_state_or_current_contract_changed")
    return state


def prepare_panel(native_session):
    """Capture an issued immutable native state; saved seals are not authority."""
    before = _contract()
    native_state = native._issued(native_session)
    handle = _PreparedPanel()
    state = _State(native_session, native_state, digest(before), b"")
    object.__setattr__(state, "authentication", _auth(handle, state))
    if before != _contract() or native._issued(native_session) is not native_state:
        raise ValueError("source_panel_parent_or_contract_changed_during_preparation")
    _SESSIONS[handle] = state
    _issued(handle)
    return handle


def _partitions(points):
    if len(points) < 2 or points != sorted(set(points)):
        raise ValueError("strict_positive_native_coordinate_inventory_required")
    inside = list(range(1, len(points) - 1))
    a, b = points[0], points[-1]

    def nearest(ratio):
        return min(inside, key=lambda i: (abs(points[i] - (a + (b - a) * ratio)), points[i])) if inside else None

    half = nearest(Fraction(1, 2))
    thirds = [nearest(Fraction(1, 3)), nearest(Fraction(2, 3))]
    return [("whole_hold", [0, len(points) - 1]),
            ("nearest_half_two_slots", None if half is None else [0, half, len(points) - 1]),
            ("nearest_thirds_three_slots", None if None in thirds or thirds[0] >= thirds[1]
             else [0, *thirds, len(points) - 1])]


def _signature(origin):
    if (origin["root"] is None or not origin["members"]
            or not all(kernels._integer_pitch(p) for p in [origin["root"], *origin["members"]])):
        return None
    # Octave-insensitive exact spelling, not MIDI/pitch-class equivalence.
    root = kernels._pitch_key(origin["root"])
    members = tuple(sorted({kernels._pitch_key(p) for p in origin["members"]}))
    return root, members


def _evidence(scope, origin):
    signature = _signature(origin)
    root, members = (None, ()) if signature is None else signature
    totals = {name: Fraction() for name in ("member", "nonmember", "unknown", "unsupported")}
    observed, member_sounds, root_time = set(), [], Fraction()
    for sound in scope["sound_facts"]:
        if sound["point"]:
            continue
        clip = kernels._overlap(sound["span"], origin["span"])
        if clip is None:
            continue
        a, b = span_bounds(clip)
        duration = b - a
        pitch = kernels._pitch_key(sound["pitch"])
        if kernels._source_blockers(sound) or temporal._guard_codes(sound):
            totals["unsupported"] += duration
        elif pitch is None or signature is None:
            totals["unknown"] += duration
        elif pitch in members:
            totals["member"] += duration
            observed.add(pitch)
            member_sounds.append({"sound_ref": sound["sound_ref"],
                "source_note_refs": deepcopy(sound["source_note_refs"]),
                "full_sound_span": deepcopy(sound["span"]), "observed_span": clip})
            if pitch == root:
                root_time += duration
        else:
            totals["nonmember"] += duration
    reasons = ["hypothesis:" + reason for reason in origin["blockers"]]
    if signature is None:
        reasons.append("integral_written_root_and_members_unavailable")
    if totals["member"] == 0:
        reasons.append("no_guarded_literal_member_note_time")
    missing = None if signature is None else len(set(members) - observed)
    body = {"origin_ref": kernels._ref(origin), "eligible": not reasons,
        "reasons": sorted(set(reasons)), "missing_guarded_member_spellings": missing,
        "guarded_pooled_member_note_time": q(totals["member"]),
        "guarded_root_note_time": q(root_time),
        "raw_note_time_by_support": {key: q(value) for key, value in totals.items()},
        "member_sound_evidence": member_sounds,
        "root": deepcopy(origin["root"]), "members": deepcopy(origin["members"]),
        "source_ornaments_used": False, "source_annotation_labels_used": False,
        "simultaneous_core_certified": False, "selected": None, "confidence": None}
    order = (missing if missing is not None else 1000000, -totals["member"], -root_time,
             () if signature is None else signature, origin["record_id"])
    return body, order, signature


def _plan(scope, entries, key_count, specs):
    requested_pairs = {pair for _, indices in specs if indices is not None
                       for pair in zip(indices, indices[1:])}
    available_pairs = {tuple(entry["point_indices"]) for entry in entries}
    complete_inventory = (requested_pairs <= available_pairs
                          and all(entry["status"] == "ready_native_interval" for entry in entries))
    origins = sum(len(entry["origins"]) for entry in entries)
    sounds = len(scope["sound_facts"])
    references = sum(len(sound["source_note_refs"]) for sound in scope["sound_facts"])
    # Repeated evidence closures, all scan/sort work and complete selectors.
    # Exact spelling membership and repeated evidence closures are not unit
    # cost when a provider emits an extended member set or a long tie chain.
    scan = sum((sounds + references + 1) * (1 + len(origin["members"] or ()))
               for entry in entries for origin in entry["origins"])
    sorting = sum(len(entry["origins"]) * max(1, len(entry["origins"]).bit_length()) for entry in entries)
    counts = {tuple(entry["point_indices"]): (len(entry["origins"])
              if entry["status"] == "ready_native_interval" else 0 if entry["variant_count"] == 0 else None)
              for entry in entries}
    path_bounds = []
    for _, indices in specs:
        if indices is None:
            path_bounds.append(0)
            continue
        slot_counts = [counts.get(pair) for pair in zip(indices, indices[1:])]
        if 0 in slot_counts:
            path_bounds.append(0)  # Known empty annihilates the complete path.
        elif None in slot_counts:
            path_bounds.append(None)
        else:
            profiles = 1 if len(slot_counts) == 1 else 2
            path_bounds.append(min(2, prod(slot_counts)) * key_count * profiles)
    selector_upper = None if None in path_bounds else sum(path_bounds)
    structural_upper = sum((2 * key_count * (1 if len(indices) == 2 else 2))
                           for _, indices in specs if indices is not None)
    return {"requested_intervals": len(requested_pairs), "available_intervals": len(entries),
        "available_origin_inventory": origins,
        "origin_evaluations": origins if complete_inventory else None,
        "source_sound_visits": origins * sounds if complete_inventory else None,
        "source_reference_visit_upper_bound": origins * references if complete_inventory else None,
        "available_materialized_sorting_work": sorting,
        "sorting_comparison_upper_bound": sorting if complete_inventory else None,
        "selector_upper_bound": selector_upper,
        "structural_selector_upper_bound": structural_upper,
        "planned_selection_work": None if selector_upper is None or not complete_inventory else scan + sorting + selector_upper * 10,
        "semantics": "whole_request_logical_work_not_CPU_RSS_or_accuracy"}


def panel_prepared(handle, *, max_selectors=64, selection_work_budget=3000000):
    for name, value in (("max_selectors", max_selectors), ("selection_work_budget", selection_work_budget)):
        native._integer(value, name)
    state = _issued(handle)
    scope = owned._thaw(state.native_state.data["scope"])
    lattice = owned._thaw(state.native_state.data["lattice"])
    points = [f(v) for v in lattice["coordinate_times"]]
    specs = _partitions(points)
    inventory = {tuple(e["point_indices"]): e for e in lattice["catalog_inventory"]}
    pairs = sorted({pair for _, indices in specs if indices is not None
                    for pair in zip(indices, indices[1:])})
    entries = [inventory[pair] for pair in pairs if pair in inventory]
    keys = sorted(lattice["keys"], key=lambda key: key["record_id"])
    plan = _plan(scope, entries, len(keys), specs)
    reasons = []
    if lattice["status"] != "ready_native_interval_lattice":
        reasons.append("whole_native_lattice_unavailable")
    if not scope["context_sound_inventory_complete"]:
        reasons.append("complete_source_inventory_unavailable")
    if plan["selector_upper_bound"] is None:
        reasons.append("requested_native_selector_bound_unavailable")
    elif plan["selector_upper_bound"] > max_selectors:
        reasons.append("whole_panel_selector_bound_exceeds_budget_no_prefix")
    if plan["planned_selection_work"] is None:
        reasons.append("requested_native_selection_work_unavailable")
    elif plan["planned_selection_work"] > selection_work_budget:
        reasons.append("whole_panel_selection_work_exceeds_budget_no_prefix")
    if len(entries) != len(pairs):
        reasons.append("requested_native_interval_inventory_unavailable")
    reports, chosen, selectors, paths, partition_rows = [], {}, [], [], []
    eligible_sizes, signature_sizes = {}, {}
    eligible_total = rejected_total = 0
    if not reasons:
        for entry in entries:
            evaluated = [_evidence(scope, origin) for origin in entry["origins"]]
            eligible = sorted((row for row in evaluated if row[0]["eligible"]), key=lambda row: row[1])
            primary = eligible[0] if eligible else None
            competitor = next((row for row in eligible if row[2] != primary[2]), None) if primary else None
            proposals = [row[0] for row in (primary, competitor) if row is not None]
            chosen[tuple(entry["point_indices"])] = proposals
            eligible_sizes[tuple(entry["point_indices"])] = len(eligible)
            signature_sizes[tuple(entry["point_indices"])] = len({row[2] for row in eligible})
            eligible_total += len(eligible)
            rejected_total += len(evaluated) - len(eligible)
            reports.append({"catalog_id": entry["catalog_id"], "point_indices": deepcopy(entry["point_indices"]),
                "span": deepcopy(entry["span"]), "native_origins": len(evaluated), "eligible_origins": len(eligible),
                "rejected_origins": len(evaluated) - len(eligible),
                "rejection_reason_occurrences": dict(Counter(reason for row in evaluated if not row[0]["eligible"] for reason in row[0]["reasons"])),
                "distinct_eligible_spelling_signatures": len({row[2] for row in eligible}),
                "proposals": proposals, "proposal_count": len(proposals),
                "omitted_eligible_origins": len(eligible) - len(proposals),
                "status": "source_evidence_proposals_not_winners" if proposals else "known_no_evaluable_candidate"})
        seen_paths = set()
        for name, indices in specs:
            row = {"partition_kind": name, "point_indices": indices, "complete_proposed_paths": 0,
                   "eligible_cartesian_origin_paths": None, "eligible_cartesian_signature_paths": None,
                   "omitted_eligible_cartesian_origin_paths": None,
                   "reasons": [], "status": "computed_source_panel_partition"}
            if indices is None:
                row.update(status="unavailable_structural_partition", reasons=["observed_quantile_cuts_not_distinct"])
            elif any(not chosen[pair] for pair in zip(indices, indices[1:])):
                row.update(status="known_no_complete_evaluable_candidate_path", reasons=["slot_has_no_evaluable_origin"],
                    eligible_cartesian_origin_paths=0, eligible_cartesian_signature_paths=0,
                    omitted_eligible_cartesian_origin_paths=0)
            else:
                row["eligible_cartesian_origin_paths"] = prod(eligible_sizes[pair] for pair in zip(indices, indices[1:]))
                row["eligible_cartesian_signature_paths"] = prod(signature_sizes[pair] for pair in zip(indices, indices[1:]))
                for position in range(2):
                    slot_rows = [chosen[pair] for pair in zip(indices, indices[1:])]
                    # A missing competitor repeats the primary; dedup complete IDs.
                    ids = [rows[min(position, len(rows) - 1)]["origin_ref"]["record_id"] for rows in slot_rows]
                    if tuple(ids) in seen_paths:
                        continue
                    seen_paths.add(tuple(ids))
                    row["complete_proposed_paths"] += 1
                    paths.append({"partition_kind": name, "proposal_lane": position, "origin_ids": ids})
                    for key in keys:
                        for assumption in ([None] if len(ids) == 1 else [None, {"family": "V7", "quality": "M"}]):
                            selectors.append({"origin_ids": deepcopy(ids), "key_id": key["record_id"],
                                "transition_assumptions": [deepcopy(assumption) for _ in range(len(ids) - 1)]})
                row["omitted_eligible_cartesian_origin_paths"] = row["eligible_cartesian_origin_paths"] - row["complete_proposed_paths"]
            partition_rows.append(row)
    result = kernels._seal({"version": VERSION, "contract": _contract(), "policy": POLICY,
        "scope_ref": kernels._ref(scope), "lattice_ref": kernels._ref(lattice),
        "analysis_span": deepcopy(scope["analysis_span"]), "logical_universe": deepcopy(lattice["universe"]),
        "native_request": {key: deepcopy(lattice[key]) for key in ("status", "reasons", "resource_limits")},
        "query_plan": plan, "resource_limits": {"max_selectors": max_selectors, "selection_work_budget": selection_work_budget},
        "intervals": reports, "partitions": partition_rows, "complete_proposal_paths": paths, "selectors": selectors,
        "keys": [kernels._ref(key) for key in keys], "status": "whole_source_panel_hold" if reasons else "computed_source_evidence_panel_not_selected",
        "reasons": reasons, "summary": {"native_interval_catalogs": len(lattice["catalog_inventory"]),
            "native_origins": lattice["materialized_origins"], "requested_intervals": len(pairs),
            "evaluated_origin_occurrences": None if reasons else eligible_total + rejected_total,
            "eligible_origin_occurrences": None if reasons else eligible_total,
            "rejected_origin_occurrences": None if reasons else rejected_total,
            "complete_proposal_paths": len(paths), "submitted_selectors": len(selectors),
            "planned_selector_upper_bound": plan["selector_upper_bound"],
            "unsubmitted_selector_bound": None if plan["selector_upper_bound"] is None else plan["selector_upper_bound"] - len(selectors)},
        "selected": None, "rank": None, "confidence": None,
        "flags": {"source_annotation_labels_used": False, "supplier_ornaments_used": False,
            "role_outcomes_used_for_proposal": False, "winning_harmony_selected": False,
            "NCT_confirmed": False, "cadence_confirmed": False, "training_eligible": False, "gold_eligible": False},
        "limitations": ["Pooled source note-time includes simultaneous voices; it is not elapsed time or probability.",
            "Missing guarded spellings and support order do not certify a chord, a simultaneous core or an NCT.",
            "Two zipped complete paths omit mixed cross-slot combinations; the native universe is unchanged.",
            "Uniform V7/M and every registered key are explicit hypotheses, not inferred functions or local keys.",
            "Full-span, actual-link and first-change requirements are checked separately by the native role engine."]}, PREFIX)
    _issued(handle)
    return result


def validate_panel_prepared(handle, record):
    kernels._check(record, PREFIX)
    if not owned._same(record, panel_prepared(handle, **record["resource_limits"])):
        raise ValueError("stale_foreign_or_modified_source_panel")
    return True
