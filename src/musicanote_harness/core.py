from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from music21 import chord, converter, key, note, roman, stream

from .canonical import CanonicalIRBuilder, as_fraction, stable_id
from .validators import validate_ir


@dataclass(frozen=True)
class Position:
    measure: int
    beat: float
    offset_ql: float


@dataclass
class Candidate:
    label: str
    confidence: float
    evidence: list[dict[str, Any]] = field(default_factory=list)
    against: list[str] = field(default_factory=list)


def _round(value: float) -> float:
    return round(float(value), 6)


def _stable_id(*parts: object) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _part_id(part: stream.Part, index: int) -> str:
    return str(part.id or f"P{index + 1}")


class MusicHarness:
    """Deterministic observation layer plus evidence-bearing hypotheses."""

    schema_version = "musicanote-analysis-package-0.2"

    def parse(self, source: str | Path) -> dict[str, Any]:
        """Parse MusicXML without making musical-analysis claims."""
        source = Path(source)
        score = converter.parse(str(source))
        ir = CanonicalIRBuilder().build(score, source)
        return {"score": ir, "validation": validate_ir(ir)}

    def analyze(self, source: str | Path) -> dict[str, Any]:
        source = Path(source)
        score = converter.parse(str(source))
        ir = CanonicalIRBuilder().build(score, source)
        validation = validate_ir(ir)
        global_key = score.analyze("key")
        spans = self._harmonic_spans(score, global_key)
        boundaries = self._boundary_hypotheses(score)
        return {
            "schema_version": self.schema_version,
            "score": ir,
            "validation": validation,
            "analysis": {
                "global_key": {
                    "label": global_key.tonic.name + " " + global_key.mode,
                    "correlation": _round(global_key.correlationCoefficient),
                    "alternatives": [
                        {
                            "label": candidate_key.tonic.name + " " + candidate_key.mode,
                            "correlation": _round(candidate_key.correlationCoefficient),
                        }
                        for candidate_key in global_key.alternateInterpretations[:3]
                    ],
                },
                "harmonic_spans": spans,
                "boundary_hypotheses": boundaries,
            },
            "run": {
                "music21_version": __import__("music21").__version__,
                "observation_policy": "deterministic",
                "inference_policy": "candidates_with_evidence",
            },
        }

    def _harmonic_spans(self, score: stream.Score, global_key: key.Key) -> list[dict[str, Any]]:
        reduced = score.chordify()
        spans: list[dict[str, Any]] = []
        previous_label: str | None = None
        current: dict[str, Any] | None = None
        for sonority in reduced.recurse().getElementsByClass(chord.Chord):
            if not sonority.pitches:
                continue
            try:
                rn = roman.romanNumeralFromChord(sonority, global_key)
                label = rn.figure
            except Exception:
                label = "unknown"
            measure = sonority.getContextByClass(stream.Measure)
            measure_no = int(measure.number or 0) if measure else 0
            start = _round(sonority.getOffsetInHierarchy(score))
            end = _round(start + sonority.quarterLength)
            distinct = len(set(sonority.pitchClasses))
            confidence = min(0.9, 0.42 + 0.12 * distinct)
            evidence = [
                {"code": "sounding_pitch_classes", "value": sorted(set(sonority.pitchClasses))},
                {"code": "metric_position", "value": _round(sonority.beat)},
                {"code": "global_key_context", "value": global_key.tonic.name + " " + global_key.mode},
            ]
            if label == previous_label and current and abs(current["range"]["end_offset_ql"] - start) < 1e-6:
                current["range"]["end_offset_ql"] = end
                current["selected"]["evidence"].append({"code": "sustained_same_interpretation", "value": True})
                continue
            candidate = Candidate(label, confidence, evidence)
            current = {
                "span_id": f"hs_{stable_id(measure_no, start, label)}",
                "range": {"start_measure": measure_no, "start_beat": _round(sonority.beat), "start_offset_ql": start, "end_offset_ql": end},
                "selected": asdict(candidate),
                "alternatives": [],
                "status": "provisional" if confidence < 0.75 else "accepted_by_threshold",
            }
            spans.append(current)
            previous_label = label
        return spans

    def _boundary_hypotheses(self, score: stream.Score) -> list[dict[str, Any]]:
        measures = list(score.parts[0].getElementsByClass(stream.Measure)) if score.parts else []
        results: list[dict[str, Any]] = []
        for measure in measures:
            evidence: list[dict[str, Any]] = []
            local_events = list(measure.notesAndRests)
            if not local_events:
                continue
            last = local_events[-1]
            if isinstance(last, note.Rest):
                evidence.append({"code": "rest_at_measure_end", "weight": 0.28})
            pitched = list(measure.recurse().notes)
            if pitched and float(pitched[-1].quarterLength) >= 2:
                evidence.append({"code": "long_final_event", "weight": 0.22})
            if measure.number and int(measure.number) % 4 == 0:
                evidence.append({"code": "four_measure_hypermetric_position", "weight": 0.12})
            if not evidence:
                continue
            confidence = min(0.88, 0.25 + sum(e["weight"] for e in evidence))
            results.append({
                "boundary_id": f"bd_{stable_id(measure.number, measure.offset)}",
                "after_measure": int(measure.number or 0),
                "offset_ql": _round(measure.getOffsetInHierarchy(score) + measure.barDuration.quarterLength),
                "selected": {"label": "phrase_boundary_candidate", "confidence": _round(confidence), "evidence": evidence},
                "alternatives": [{"label": "continuation", "confidence": _round(1 - confidence)}],
                "status": "needs_review",
            })
        return results


def arrangement_plan(analysis: dict[str, Any]) -> dict[str, Any]:
    """Create a phrase-level plan; note realization is deliberately a later module."""
    boundaries = analysis["analysis"]["boundary_hypotheses"]
    events = analysis["score"]["notated_note_segments"]
    last_measure = max((e["measure"] for e in events), default=0)
    cuts = sorted({b["after_measure"] for b in boundaries if b["selected"]["confidence"] >= 0.5})
    if not cuts or cuts[-1] != last_measure:
        cuts.append(last_measure)
    textures = ["bass_plus_inner_tones", "broken_chord_with_linear_bass", "sustained_bass_moving_inner_voice", "cadential_reduction"]
    start = 1
    phrases = []
    for index, end in enumerate(cuts):
        if end < start:
            continue
        role = "closing" if end == last_measure else ("presentation" if index == 0 else "continuation")
        phrases.append({
            "phrase_id": f"phrase_{index + 1}", "measures": [start, end], "role": role,
            "texture": textures[-1] if role == "closing" else textures[index % 3],
            "density": "sparse" if index == 0 else ("reduced" if role == "closing" else "medium"),
            "constraints": ["melody_prominent", "change_texture_only_at_structural_event", "preserve_cadence_space"],
        })
        start = end + 1
    return {"schema_version": "musicanote-arrangement-plan-0.1", "score_id": analysis["score"]["score_id"], "phrases": phrases}


def write_package(result: dict[str, Any], destination: str | Path) -> None:
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "canonical_ir.json").write_text(json.dumps(result["score"], ensure_ascii=False, indent=2), encoding="utf-8")
    (destination / "analysis_hypotheses.json").write_text(json.dumps(result["analysis"], ensure_ascii=False, indent=2), encoding="utf-8")
    (destination / "run_manifest.json").write_text(json.dumps(result["run"], ensure_ascii=False, indent=2), encoding="utf-8")
    (destination / "validation_report.json").write_text(json.dumps(result["validation"], ensure_ascii=False, indent=2), encoding="utf-8")
    (destination / "arrangement_plan.json").write_text(json.dumps(arrangement_plan(result), ensure_ascii=False, indent=2), encoding="utf-8")
