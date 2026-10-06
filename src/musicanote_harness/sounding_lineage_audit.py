"""Pure notated-clock diagnostics; never repair or certify a sounding lineage.

Full source-note coverage and context-clipped coverage are separate. These are
facts about the supplied IR, not assertions about MusicXML authority, performed
timing, concert pitch, contrapuntal voice identity or musical roles.
"""
from collections import Counter
from copy import deepcopy

from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "sounding-lineage-audit-0.1.0"
SCHEMA_NAME = "musicanote-sounding-lineage-audit"
SCHEMA_VERSION = "0.1.0"
PREFIX = "msla_"


def _index(rows, key):
    result = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise ValueError("missing_or_duplicate_catalog_id:" + key)
        result[value] = row
    return result


def _span(start, end):
    return {"start": q(start), "end": q(end)}


def _checked_span(value, duration):
    a, b = span_bounds(value)
    if b > duration:
        raise ValueError("selection_or_context_outside_score")
    return a, b


def _cells(intervals, start, end):
    if end <= start:
        return []
    points = sorted({start, end} | {t for _, a, b in intervals for t in (a, b) if start < t < end})
    return [{"span": _span(a, b), "source_indices": [i for i, x, y in intervals if x < b and y > a]}
            for a, b in zip(points, points[1:])]


def _union(intervals):
    if not intervals:
        return f(q(0))
    a, b = min(x for _, x, _ in intervals), max(y for _, _, y in intervals)
    return sum((f(c["span"]["end"]) - f(c["span"]["start"])
                for c in _cells(intervals, a, b) if c["source_indices"]), f(q(0)))


def _ledger(timeline, span, declared, *, complete, clipped=False):
    intervals = [(r["source_index"], f(r["onset"]), f(r["end"]))
                 for r in timeline if f(r["end"]) > f(r["onset"])]
    known_sum = sum((f(r["notated_duration"]) for r in timeline), f(q(0)))
    if span is None:
        return {"span": None, "span_duration": q(0), "declared_sounding_duration": deepcopy(declared),
                "source_duration_sum": q(0), "source_union_duration": q(0), "covered_duration": q(0),
                "gaps": [], "overlaps": [], "outside_source_extents": [], "cells": [],
                "source_duration_sum_matches_span": False, "coverage_assessed": False,
                "timeline_complete": complete, "coverage_consistency_passed": False}
    a, b = f(span["start"]), f(span["end"])
    cells = _cells(intervals, a, b)
    covered = sum((f(c["span"]["end"]) - f(c["span"]["start"])
                   for c in cells if c["source_indices"]), f(q(0)))
    gaps = [deepcopy(c["span"]) for c in cells if not c["source_indices"]]
    overlaps = [deepcopy(c) for c in cells if len(c["source_indices"]) > 1]
    outside = []
    for i, x, y in intervals:
        for lo, hi in ((x, min(y, a)), (max(x, b), y)):
            if lo < hi:
                outside.append({"source_index": i, "note_id": timeline_by_index(timeline, i)["note_id"],
                                "span": _span(lo, hi)})
    if clipped:
        intervals = [(i, max(x, a), min(y, b)) for i, x, y in intervals if x < b and y > a]
        source_sum = sum((y - x for _, x, y in intervals), f(q(0)))
        outside = []  # Outside the clip is context, not a lineage error.
    else:
        source_sum = known_sum
    assessed = b > a
    return {"span": deepcopy(span), "span_duration": q(b - a),
            "declared_sounding_duration": deepcopy(declared), "source_duration_sum": q(source_sum),
            "source_union_duration": q(_union(intervals)), "covered_duration": q(covered),
            "gaps": gaps, "overlaps": overlaps, "outside_source_extents": outside, "cells": cells,
            "source_duration_sum_matches_span": source_sum == b - a,
            "coverage_assessed": assessed, "timeline_complete": complete,
            "coverage_consistency_passed": assessed and complete and not gaps and not overlaps
                                           and not outside and source_sum == b - a}


def timeline_by_index(timeline, index):
    return next(row for row in timeline if row["source_index"] == index)


def _sound(sound, notes, context):
    ids = sound["source_note_ids"]
    if not isinstance(ids, list) or any(not isinstance(n, str) or not n for n in ids):
        raise ValueError("malformed_source_note_ids")
    snapshots, timeline, missing = [], [], []
    codes = []
    if not ids:
        codes.append("empty_source_note_inventory")
    if len(set(ids)) != len(ids):
        codes.append("duplicate_source_note_reference")
    for i, nid in enumerate(ids):
        note = notes.get(nid)
        snapshots.append(deepcopy(note))
        if note is None:
            missing.append(nid)
            continue
        onset, duration = f(note["global_onset_quarter"]), f(note["notated_duration_quarter"])
        grace = note.get("grace", {}).get("is_grace") is True
        timeline.append({"source_index": i, "note_id": nid, "onset": q(onset),
                         "end": q(onset + duration), "notated_duration": deepcopy(note["notated_duration_quarter"]),
                         "tie_role": note.get("tie_role"), "is_grace": grace})
        if onset < 0 or duration < 0:
            codes.append("negative_notated_source_time")
        elif duration == 0 and not grace:
            codes.append("non_grace_nonpositive_source_duration")
    if missing:
        codes.append("missing_source_note_reference")
    a, b = f(sound["span"]["start"]), f(sound["span"]["end"])
    declared = f(sound["sounding_duration"])
    if a < 0 or b < a:
        codes.append("invalid_sounding_span")
    if declared != b - a:
        codes.append("declared_sounding_duration_differs_from_span")
    ordered = all(f(x["onset"]) <= f(y["onset"]) for x, y in zip(timeline, timeline[1:]))
    if not ordered:
        codes.append("source_onsets_not_in_stored_order")
    full = _ledger(timeline, sound["span"], sound["sounding_duration"], complete=not missing and bool(ids))
    if full["gaps"]:
        codes.append("full_source_timeline_gap")
    if full["overlaps"]:
        codes.append("full_source_timeline_overlap")
    if full["outside_source_extents"]:
        codes.append("source_extent_outside_sound_span")
    if not full["source_duration_sum_matches_span"]:
        codes.append("source_duration_sum_differs_from_sound_span")
    attack_id = sound.get("attack_note_id")
    attack = notes.get(attack_id)
    member = attack_id in ids
    attack_matches = attack is not None and f(attack["global_onset_quarter"]) == a
    first_matches = bool(timeline) and min(f(r["onset"]) for r in timeline) == a
    continuation = attack is not None and attack.get("tie_role") in ("continue", "stop")
    if not member:
        codes.append("attack_note_not_source_member")
    if attack is None:
        codes.append("missing_attack_note_reference")
    elif not attack_matches:
        codes.append("attack_onset_differs_from_sound_start")
    if not first_matches:
        codes.append("earliest_source_onset_differs_from_sound_start")
    if continuation:
        codes.append("attack_is_tie_continuation_or_stop_origin")
    grace_point = bool(timeline) and not missing and all(r["is_grace"] for r in timeline) and a == b
    timing = "grace_point_performed_timing_unknown" if grace_point else "positive_notated" if b > a else "unsupported_nonpositive"
    if grace_point:
        codes.append("grace_performed_timing_not_assessed")
    elif b <= a:
        codes.append("nonpositive_sounding_timing_not_supported")
    clipped = None
    if context is not None:
        c, d = f(context["start"]), f(context["end"])
        clip = _span(max(a, c), min(b, d)) if max(a, c) < min(b, d) else None
        if grace_point and c <= a < d:
            clip = deepcopy(sound["span"])
        clipped = _ledger(timeline, clip, None, complete=not missing and bool(ids), clipped=True)
        clipped["context_span"] = deepcopy(context)
        clipped["point_in_context"] = a == b and c <= a < d
    return {"sounding_event_ref": sound["sounding_event_id"], "sounding_event_snapshot": deepcopy(sound),
            "source_note_snapshots": snapshots, "source_timeline": timeline,
            "missing_source_note_refs": missing, "source_onsets_in_stored_order": ordered,
            "full_chain": full, "context_clipped": clipped,
            "attack_origin": {"attack_note_id": attack_id, "source_member": member, "exists": attack is not None,
                              "onset_matches_sound_start": attack_matches,
                              "first_source_onset_matches_sound_start": first_matches,
                              "tie_role": None if attack is None else attack.get("tie_role"),
                              "continuation_origin": continuation},
            "diagnostics": sorted(set(codes)), "source_clock_consistency_passed": not codes and b > a,
            "timing_status": timing, "semantic_eligible": False, "generation_ready": False}


def audit_sounding_lineage(ir, *, span=None, sound_ids=None, context_span=None):
    """Select by one span OR explicit IDs; an optional clip is not a selector.

    Empty IDs remain an empty, not-assessed diagnostic record. Unknown IDs are
    recorded, not silently dropped. Positive interval unions are exact rationals;
    grace points do not establish performed durations or continuous coverage.
    """
    if (span is None) == (sound_ids is None):
        raise ValueError("exactly_one_span_or_sound_ids_selector_required")
    notes = _index(ir["note_events"], "note_id")
    sounds = _index(ir["sounding_events"], "sounding_event_id")
    duration = f(ir["score"]["duration_quarters"])
    if not ir.get("ir_document_id") or not ir["score"].get("score_id") or not ir["source_files"]:
        raise ValueError("full_ir_document_score_source_binding_required")
    if context_span is not None:
        _checked_span(context_span, duration)
    if span is not None:
        c, d = _checked_span(span, duration)
        selected = []
        for sid, sound in sounds.items():
            a, b = f(sound["span"]["start"]), f(sound["span"]["end"])
            if (c <= a < d if a == b else min(a, b) < d and max(a, b) > c):
                selected.append(sid)
        clip = context_span if context_span is not None else span
        kind = "span"
        original_ids = None
    else:
        if not isinstance(sound_ids, (list, tuple)) or any(not isinstance(x, str) or not x for x in sound_ids):
            raise ValueError("explicit_sound_id_sequence_required")
        if len(set(sound_ids)) != len(sound_ids):
            raise ValueError("duplicate_selected_sound_id")
        selected, original_ids = list(sound_ids), list(sound_ids)
        clip, kind = context_span, "sound_ids"
    rows = [_sound(sounds[sid], notes, clip) for sid in selected if sid in sounds]
    missing = [sid for sid in selected if sid not in sounds]
    counts = Counter(code for row in rows for code in row["diagnostics"])
    if missing:
        counts["missing_selected_sounding_event"] += len(missing)
    passed = sum(row["source_clock_consistency_passed"] for row in rows)
    binding = {"score_id": ir["score"]["score_id"], "ir_document_id": ir["ir_document_id"],
               "ir_content_sha256": digest(ir), "source_files": deepcopy(ir["source_files"])}
    body = {"schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION, "producer_version": VERSION,
            "status": "complete_diagnostics" if selected else "empty_selection_not_assessed",
            "binding": binding, "selection": {"kind": kind, "span": deepcopy(span), "sound_ids": original_ids,
                "selected_sound_refs": selected, "context_span": deepcopy(clip),
                "context_span_basis": "explicit_context_span" if context_span is not None else "selector_span" if span is not None else "none"},
            "sounding_audits": rows,
            "summary": {"selected_sounds": len(selected), "audited_sounds": len(rows),
                        "missing_selected_sound_refs": missing, "source_clock_passed": passed,
                        "source_clock_failed": len(rows) - passed, "diagnostic_counts": dict(sorted(counts.items()))},
            "source_clock_consistency_passed": bool(selected) and not missing and passed == len(rows),
            "semantic_eligible": False, "generation_ready": False, "source_xml_certified": False,
            "voice_identity_certified": False, "performed_timing_certified": False, "concert_pitch_certified": False,
            "input_modified": False, "timing_basis": "original_IR_notated_source_clock_not_performed_timing",
            "limits": ["A full-chain failure is retained even when current clipped coverage is consistent.",
                       "Missing source notes make available-source coverage incomplete, not certified absence.",
                       "Diagnostics do not establish XML error, parser cause, voice identity or musical roles.",
                       "No sound span, source note membership, pitch, onset or duration is repaired."]}
    sha = digest(body)
    return {**body, "record_id": PREFIX + sha[:24], "record_sha256": sha}


def validate_audit(record, *, ir, span=None, sound_ids=None, context_span=None):
    """Check seal and fresh exact replay against explicitly supplied selection."""
    body = {k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}
    sha = digest(body)
    if record.get("record_sha256") != sha or record.get("record_id") != PREFIX + sha[:24]:
        raise ValueError("sounding_lineage_audit_seal_mismatch")
    fresh = audit_sounding_lineage(ir, span=span, sound_ids=sound_ids, context_span=context_span)
    if record != fresh:
        raise ValueError("stale_foreign_or_modified_sounding_lineage_audit")
    return True
