"""Source-bound clock gate before harmonic exposure, without Core repair.

An inconsistent sound is not shortened, split, or silently removed. Only a
requested interval intersecting its conservative risk envelope is withheld.
Unlocatable/ambiguous source identities block all intervals. Voice changes are
reported, not assumed to invalidate a physically contiguous cross-staff tie.
"""
from collections import Counter, defaultdict
from copy import deepcopy

from .harmony_candidate_recall import fraction as f, rational as q
from .harmony_progression_search import _hash
from .harmony_window_workspace import infer as original_infer

VERSION = "harmony-source-clock-gate-0.1.0"


def _pitch(value):
    if (not isinstance(value, dict) or value.get("step") not in tuple("CDEFGAB")
            or type(value.get("octave")) is not int):
        raise ValueError("unavailable_spelled_pitch")
    return value["step"], f(value["alter"]), value["octave"]


def _index(rows, field, errors):
    result = {}
    for row in rows:
        ident = row.get(field)
        if not isinstance(ident, str) or not ident:
            errors.add("missing_"+field)
        elif ident in result:
            errors.add("duplicate_"+field)
        else:
            result[ident] = row
    return result


def audit(ir):
    """Check all sound/note clocks from the pinned IR, not annotation labels.

    XML source positions are retained as references; this does not independently
    reparse XML or certify parser voice/tie normalization. Rational values are
    compared exactly. A bad stored span may UNDERstate source note duration, so
    the risk envelope is the union envelope of both stored and observed clocks.
    """
    before = _hash(ir); errors = set()
    notes = _index(ir["note_events"], "note_id", errors)
    sounds = _index(ir["sounding_events"], "sounding_event_id", errors)
    owners = defaultdict(list)
    for ident, sound in sounds.items():
        for nid in set(sound.get("source_note_ids", [])):
            owners[nid].append(ident)
    records = []
    for ident, sound in sorted(sounds.items()):
        reasons = set(); warnings = set(); times = []; observed = []
        source_ids = sound.get("source_note_ids", [])
        if not source_ids:
            reasons.add("empty_source_note_chain"); errors.add("empty_source_chain_unlocatable")
        if len(set(source_ids)) != len(source_ids): reasons.add("duplicate_note_in_chain")
        if any(len(owners[nid]) > 1 for nid in source_ids): reasons.add("note_shared_between_sounds")
        try:
            a, b = f(sound["span"]["start"]), f(sound["span"]["end"])
            times.extend((a, b))
            duration = f(sound["sounding_duration"])
            if a < 0 or b < a or duration < 0: reasons.add("negative_or_reversed_sound_clock")
            if duration != b-a: reasons.add("declared_duration_span_mismatch")
        except (KeyError, TypeError, ValueError):
            a = b = duration = None; errors.add("unlocatable_sound_clock")
            reasons.add("invalid_sound_coordinate")
        try:
            pitch = _pitch(sound["pitch"])
        except (KeyError, TypeError, ValueError):
            pitch = None; reasons.add("unavailable_sound_pitch")
        for nid in source_ids:
            note = notes.get(nid)
            if note is None:
                errors.add("missing_source_note_unlocatable"); reasons.add("missing_source_note")
                continue
            try:
                onset, dur = f(note["global_onset_quarter"]), f(note["notated_duration_quarter"])
                times.extend((onset, onset+dur))
                if onset < 0 or dur < 0: reasons.add("negative_source_note_clock")
                observed.append((onset, dur, note))
            except (KeyError, TypeError, ValueError):
                errors.add("unlocatable_source_note_clock"); reasons.add("invalid_note_coordinate")
                continue
            try:
                if _pitch(note["concert_pitch"]) != pitch: reasons.add("different_spelled_concert_pitch")
            except (KeyError, TypeError, ValueError):
                reasons.add("unavailable_source_note_pitch")
        ordered = sorted(observed, key=lambda row: (row[0], row[2]["note_id"]))
        parts = {n.get("part_id") for _, _, n in ordered}
        voices = {(n.get("part_id"), n.get("voice_id")) for _, _, n in ordered}
        if len(parts) > 1: reasons.add("chain_crosses_parts")
        if len(voices) > 1: warnings.add("multiple_normalized_voice_ids")
        grace = bool(ordered) and all(n.get("grace", {}).get("is_grace") for _, _, n in ordered)
        zero_grace = (a is not None and a == b and duration == 0 and grace
                      and sound.get("tie_chain_id") is None
                      and all(onset == a and dur == 0 for onset, dur, _ in ordered))
        if a is not None and ordered:
            cursor = a
            for onset, dur, _ in ordered:
                if onset != cursor: reasons.add("noncontiguous_source_clock")
                if dur <= 0 and not zero_grace: reasons.add("nonpositive_non_grace_duration")
                cursor = onset+dur
            if cursor != b: reasons.add("source_release_mismatch")
            if sound.get("attack_note_id") != ordered[0][2]["note_id"]: reasons.add("attack_note_mismatch")
        if a is not None and a == b and not zero_grace: reasons.add("zero_sound_not_verified_grace")
        risk = {"start": q(min(times)), "end": q(max(times))} if times else None
        records.append({"sounding_event_id": ident, "source_note_ids": list(source_ids),
            "stored_span": deepcopy(sound.get("span")), "risk_span": risk,
            "passed": not reasons, "reasons": sorted(reasons), "warnings": sorted(warnings),
            "zero_time_grace": zero_grace,
            "source_notes": [{"note_id": n["note_id"], "source_ref_id": n.get("source_ref_id"),
                "part_id": n.get("part_id"), "voice_id": n.get("voice_id"),
                "display_staff_id": n.get("display_staff_id"),
                "onset": q(onset), "duration": q(dur), "release": q(onset+dur)}
                for onset, dur, n in ordered]})
    if _hash(ir) != before: raise ValueError("clock_audit_mutated_core")
    counts = Counter(reason for row in records for reason in row["reasons"])
    return {"version": VERSION, "source_ir_sha256": before, "records": records,
        "global_blockers": sorted(errors), "sounds": len(ir["sounding_events"]),
        "passed": sum(row["passed"] for row in records), "failed": sum(not row["passed"] for row in records),
        "multi_note_sounds": sum(len(row["source_note_ids"]) > 1 for row in records),
        "zero_time_graces": sum(row["zero_time_grace"] for row in records),
        "reason_counts": dict(counts), "source_clock_basis": "canonical_note_to_sound_contract",
        "raw_xml_independently_reparsed": False, "source_labels_used": False,
        "core_repaired": False, "sound_split_shortened_or_deleted": False}


class SourceClockGuard:
    """One immutable source lease. Invalidity is checked BEFORE delegation."""
    def __init__(self, ir):
        self.ir = ir; self.source_sha256 = _hash(ir)
        self._audit = audit(ir); self._audit_sha256 = _hash(self._audit)
        self.valid = True

    def check_source(self):
        if (not self.valid or _hash(self.ir) != self.source_sha256
                or _hash(self._audit) != self._audit_sha256):
            self.valid = False
            raise ValueError("clock_guard_source_or_audit_changed")

    def report(self):
        self.check_source()
        return deepcopy(self._audit)

    def scope(self, span):
        self.check_source(); a, b = f(span["start"]), f(span["end"])
        if not 0 <= a < b: raise ValueError("invalid_clock_guard_scope")
        affected = []
        for row in self._audit["records"]:
            if row["passed"]: continue
            risk = row["risk_span"]
            if risk is None:
                affected.append(row); continue
            x, y = f(risk["start"]), f(risk["end"])
            if (x < b and a < y) or (x == y and a <= x < b): affected.append(row)
        return {"version": VERSION, "source_ir_sha256": self.source_sha256,
            "audit_sha256": self._audit_sha256, "span": deepcopy(span),
            "accepted": not affected and not self._audit["global_blockers"],
            "global_blockers": list(self._audit["global_blockers"]),
            "affected_sounds": deepcopy(affected), "span_convention": "[start,end)",
            "risk_policy": "whole_invalid_sound_and_source_note_envelope",
            "candidate_generation_allowed": not affected and not self._audit["global_blockers"],
            "core_repaired": False}

    def infer(self, sample, *, delegate=original_infer):
        gate = self.scope(sample["span"])
        if not gate["accepted"]:
            return {"version": VERSION, "status": "source_clock_abstention", "selected_prediction": None,
                "source_clock_gate": gate, "transitions": 0, "lattice_edge_count": 0,
                "exact_optimum_under_declared_graph": False, "source_labels_used_at_inference": False,
                "production_modified": False, "formal_core_modified": False}, None
        try:
            result, graph = delegate(self.ir, deepcopy(sample))
        finally:
            self.check_source()
        return {**result, "source_clock_gate": gate}, graph
