"""Bounded, score-only recovery of previously unavailable research contexts.

This is a consumer projection, NOT a replacement Canonical IR/parser. Zero-time
grace notation is retained in a separate source-bound channel; no performed
duration is invented. Tile seams are computation boundaries, not chord labels.
Candidates from all tiles enter ONE run-aware decoder; no tile winner stitching.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F

from .harmony_candidate_catalog import propose
from .harmony_candidate_recall import fraction as f, rational as q
from .harmony_evidence_scoring import source_evidence
from .harmony_functional_scoring import prepare_functional_evidence, supply, decode
from .harmony_lattice_recall import signature
from .harmony_path_context import plan as context_plan
from .harmony_progression_search import _hash
from .harmony_scored_decoder import Edge, Problem

VERSION = "harmony-bounded-recovery-0.1.0"
# Resource contract fixed before the paired corpus run, not musical thresholds.
CONFIG = {"tile_cells": 12, "global_cells": 64, "global_sounds": 256,
          "global_candidate_edges": 20000, "raw_edges_per_tile_budget": 6,
          "decoder_transition_budget": 2000000}


def grace_projection(ir):
    """Remove only verified zero-time grace from the positive-time consumer.

    Original objects/IDs/notes/ties stay untouched in the caller's Core. The
    returned view is NOT schema-validated or persisted as a canonical revision.
    Positive-duration grace and zero-duration non-grace remain unsupported.
    """
    before = _hash(ir); view = deepcopy(ir)
    notes = {n["note_id"]: n for n in ir["note_events"]}
    if len(notes) != len(ir["note_events"]): raise ValueError("duplicate_note_id")
    omitted = []; note_ids = set()
    for s in ir["sounding_events"]:
        a, b = f(s["span"]["start"]), f(s["span"]["end"])
        if b < a: raise ValueError("negative_sound_duration")
        if a != b: continue
        chain = [notes.get(n) for n in s["source_note_ids"]]
        if (not chain or not all(chain) or s.get("tie_chain_id") is not None
            or f(s["sounding_duration"]) != 0
            or any(not n.get("grace", {}).get("is_grace")
                   or f(n["notated_duration_quarter"]) != 0
                   or f(n["global_onset_quarter"]) != a for n in chain)):
            raise ValueError("zero_sound_not_verified_grace")
        omitted.append(deepcopy(s)); note_ids.update(s["source_note_ids"])
    if any(note_ids.intersection(s["source_note_ids"]) for s in ir["sounding_events"]
           if s not in omitted): raise ValueError("grace_note_shared_with_positive_sound")
    sound_ids = {s["sounding_event_id"] for s in omitted}
    view["sounding_events"] = [s for s in view["sounding_events"] if s["sounding_event_id"] not in sound_ids]
    view["note_events"] = [n for n in view["note_events"] if n["note_id"] not in note_ids]
    # Keep consumer ID lists coherent; no source objects are altered.
    for v in view.get("voices", []):
        if "event_ids" in v: v["event_ids"] = [n for n in v["event_ids"] if n not in note_ids]
    view["attack_events"] = [a for a in view.get("attack_events", [])
                             if a.get("sounding_event_id") not in sound_ids
                             and a.get("note_id", a.get("attack_note_id")) not in note_ids]
    for group in view.get("chord_onset_groups", []):
        group["note_ids"] = [n for n in group["note_ids"] if n not in note_ids]
    view["chord_onset_groups"] = [g for g in view.get("chord_onset_groups", []) if g["note_ids"]]
    receipt = {"original_ir_sha256": before, "consumer_view_sha256": _hash(view),
        "grace_sounding_events": omitted, "grace_note_events": [deepcopy(notes[n]) for n in sorted(note_ids)],
        "performed_timing": None, "positive_time_geometry_only": True,
        "formal_canonical_revision": False, "original_core_modified": False}
    if _hash(ir) != before: raise ValueError("projection_mutated_core")
    return view, receipt


def intersecting(ir, a, b):
    return [s for s in ir["sounding_events"] if f(s["span"]["start"]) < b and a < f(s["span"]["end"])]


def tile_plan(ir, span):
    a, b = f(span["start"]), f(span["end"])
    if not 0 <= a < b: raise ValueError("invalid_context_span")
    sounds = intersecting(ir, a, b)
    # Measure starts also allow safe bounded computation through long held
    # sounds/silence. They do not force a change of harmonic signature.
    points = sorted({a, b} | {f(s["span"][k]) for s in sounds for k in ("start", "end") if a < f(s["span"][k]) < b}
                    | {f(m["global_start_quarter"]) for m in ir["measures"] if a < f(m["global_start_quarter"]) < b})
    tiles = []; cursor = 0
    while cursor < len(points)-1:
        accepted = None
        for end in range(cursor+1, min(len(points), cursor+CONFIG["tile_cells"]+1)):
            scope = {"start": q(points[cursor]), "end": q(points[end])}
            policy = context_plan(ir, scope, {"span": scope})
            if policy["accepted"]: accepted = end, scope, policy
        if accepted is None:
            return {"status": "unsplittable_observation_cell", "span": deepcopy(span),
                    "points": [q(t) for t in points], "tiles": tiles, "uncovered_from": q(points[cursor])}
        end, scope, policy = accepted
        x, y = points[cursor], points[end]
        tiles.append({"tile_index": len(tiles), "span": scope, "context_policy": policy,
            "start_index": cursor, "end_index": end,
            "carried_sound_refs": sorted(s["sounding_event_id"] for s in sounds if f(s["span"]["start"]) < x < f(s["span"]["end"])),
            "attack_sound_refs": sorted(s["sounding_event_id"] for s in sounds if f(s["span"]["start"]) == x),
            "original_sound_spans_unchanged": True})
        cursor = end
    whole = context_plan(ir, span, {"span": span})
    blockers = [r for r in whole["abstention_reasons"]
                if r not in ("context_beat_limit_no_truncation", "context_sound_limit_no_pruning")]
    if len(points)-1 > CONFIG["global_cells"]: blockers.append("global_cell_budget_no_truncation")
    if len(sounds) > CONFIG["global_sounds"]: blockers.append("global_sound_budget_no_pruning")
    return {"status": "ready" if not blockers else "bounded_plan_abstention", "span": deepcopy(span),
        "points": [q(t) for t in points], "tiles": tiles, "blockers": sorted(set(blockers)),
        "whole_context_policy": whole, "tile_seams_are_harmonic_boundaries": False,
        "global_raw_edge_budget": CONFIG["raw_edges_per_tile_budget"]*len(tiles)}


def bound_evidence(view, span, grace_receipt):
    a, b = f(span["start"]), f(span["end"])
    ev = source_evidence(view, {"input_ir_content_sha256": _hash(view),
        "parent_ir_document_id": view["ir_document_id"], "score_id": view["score"]["score_id"],
        "stages": {"lattice": {"events": intersecting(view, a, b)}}})
    graces = grace_receipt["grace_note_events"]
    notes = {n["note_id"]: n for n in view["note_events"]}
    identities = {s["sounding_event_id"]: {(notes[n].get("part_id"), notes[n].get("voice_id")) for n in s["source_note_ids"]}
                  for s in view["sounding_events"]}
    def intervenes(p, n):
        return any((g.get("part_id"), g.get("voice_id")) in identities[p["id"]]
                   and p["start"] <= f(g["global_onset_quarter"]) <= n["start"] for g in graces)
    # Removing unknown performed timing must not manufacture a direct melodic
    # resolution/NCT link over an intervening grace note.
    removed = [eid for eid, (p, n) in ev.neighbors.items() if intervenes(p, n)]
    for eid in removed: del ev.neighbors[eid]
    functional = prepare_functional_evidence(view, ev)
    links = [link for link in functional.links if not intervenes(*link)]
    functional.voice_statuses["grace_intervening_direct_links_withheld"] = len(functional.links)-len(links)
    functional.links = tuple(links)
    return ev, functional, {"ornament_neighbor_triples_withheld": len(removed),
                            "direct_functional_links_withheld": functional.voice_statuses["grace_intervening_direct_links_withheld"]}


def build_problem(view, plan, ev):
    points = tuple(f(t) for t in plan["points"]); total = sum((min(e.end, points[-1])-max(e.start, points[0]) for e in ev.events), F())
    if plan["status"] != "ready": return Problem(points, (), 0, total, plan["status"]), []
    if total <= 0: return Problem(points, (), 0, total, "no_positive_sounding_exposure"), []
    edges = []; origins = []; catalog_count = 0
    for tile in plan["tiles"]:
        lo, hi = tile["start_index"], tile["end_index"]
        for i in range(lo, hi):
            for j in range(i+1, hi+1):
                a, b = points[i], points[j]; scope = {"start": q(a), "end": q(b)}
                catalog = propose(view, scope, tile["span"]); catalog_count += 1
                active = [(e, min(e.end, b)-max(e.start, a)) for e in ev.events if e.start < b and a < e.end]
                ids = {e.event_id for e, _ in active}
                if ids != set(catalog["providers"]["base"]["event_units"]): raise ValueError("catalog_all_part_event_loss")
                exposure = sum((d for _, d in active), F()); grouped = defaultdict(list)
                catalog_sha = _hash(catalog)
                for c in catalog["candidates"]:
                    for ai, alt in enumerate(c["spelling_alternatives"]):
                        sig = signature((alt["root_spelling"], alt["members"]))
                        blockers = tuple(sorted(c["abstention_reasons"]))
                        # Augmented-sixth tonic coordinate is not a tertian root.
                        provenance = (c["provider"] == "augmented", _hash(c.get("tonal_coordinate")))
                        grouped[sig, blockers, provenance].append({"catalog_sha256": catalog_sha, "candidate_id": c["candidate_id"],
                            "alternative_index": ai, "origin_pointer": c["origin_pointer"], "provider": c["provider"],
                            "context_span": tile["span"], "candidate_span": scope})
                for (sig, blockers, provenance), refs in sorted(grouped.items(), key=lambda x: repr(x[0])):
                    root, members = sig; gid = "bounded_"+_hash([i, j, sig, blockers, provenance])[:24]
                    raw = sum((d for e, d in active if e.pitch is not None and e.pitch not in members), F())
                    unresolved = sum((d for e, d in active if e.pitch is None), F())
                    # Only blocker exposure is used from raw edges by the
                    # run-aware decoder. All other terms recompute on UNION runs.
                    features = {"blocker_exposure": exposure/total if blockers else F(),
                                "nonmember_exposure": raw/total, "unresolved_spelling_exposure": unresolved/total}
                    edges.append(Edge(gid, i, j, a, b, sig, features,
                        frozenset(e.pitch for e, d in active if e.start == a and d > 0 and e.pitch is not None),
                        tuple(sorted(ids)), blockers, {"bounded_origin_group": gid}))
                    origins.append({"group_id": gid, "origins": refs})
                    if len(edges) > CONFIG["global_candidate_edges"]:
                        return Problem(points, (), plan["global_raw_edge_budget"], total, "global_candidate_budget_no_pruning"), origins
    plan["catalog_intervals"] = catalog_count
    return Problem(points, tuple(edges), plan["global_raw_edge_budget"], total, "ready"), origins


def infer(ir, sample):
    """No reference, title, composer, work-family or baseline winner argument."""
    before = _hash(ir); view, grace = grace_projection(ir)
    permissible = {"nonpositive_duration"} if grace["grace_sounding_events"] else set()
    remaining = sorted(set(sample.get("abstention_reasons", []))-permissible)
    plan = tile_plan(view, sample["span"])
    if remaining:
        plan.update(status="sample_scope_abstention", blockers=remaining)
    ev, functional, links = bound_evidence(view, sample["span"], grace)
    problem, origins = build_problem(view, plan, ev)
    expanded, receipts = supply(problem, functional)
    chosen = decode(expanded, functional, transition_budget=CONFIG["decoder_transition_budget"])
    if _hash(ir) != before or _hash(view) != grace["consumer_view_sha256"]: raise ValueError("recovery_mutated_inputs")
    return {"version": VERSION, "status": chosen["status"], "selected_prediction": chosen["selected"],
        "transitions": chosen["transitions"], "exact_optimum_under_declared_graph": chosen["exact_optimum_under_declared_score"],
        "grace_projection": grace, "tile_plan": plan, "link_withholding": links,
        "lattice_edge_count": len(expanded.edges), "functional_candidate_receipts": receipts,
        "candidate_origin_groups": origins, "source_labels_used_at_inference": False,
        "production_modified": False, "formal_core_modified": False}, expanded
