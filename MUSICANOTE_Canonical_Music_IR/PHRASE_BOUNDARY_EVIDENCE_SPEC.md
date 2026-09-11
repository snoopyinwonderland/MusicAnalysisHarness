# Phrase Boundary Evidence Input Contract v0.1

## Status and purpose

This document defines the evidence that may be computed before phrase segmentation. It does not define phrase boundaries. A phrase analyzer consumes these records later and publishes uncertain, versioned Analysis Records.

Lyrics are never a required phrase-analysis input. Scores with lyrics may provide weak supervision during dataset construction, but lyric text, punctuation, line breaks, control symbols, and lyric-derived timing gaps MUST be excluded from production phrase-inference features. The same analyzer contract MUST operate unchanged on instrumental music.

## Readiness gates

Phrase inference MUST remain disabled until all of the following hold for the target corpus tier:

1. MusicXML-to-Core note mapping is complete.
2. Core-to-engraving note mapping is complete.
3. Canonical IR validates against its declared schema.
4. Tie, voice, staff, measure, and exact-time validators pass.
5. The metric-strength policy for the encountered meters is versioned.
6. Inclusion rules for cue, ossia, hidden, and grace events are declared.

Missing human annotations do not block evidence extraction. They do block claims about measured phrase accuracy and supervised threshold calibration.

## Candidate time points

Evidence frames are generated only at deterministic musical time points: attack onsets, sounding-event releases, measure boundaries, signature changes, barlines, repeats, endings, fermatas, and explicit directions.

Times use exact rational global-quarter coordinates and `[start, end)` spans. No frame may carry `phrase_boundary=true` in the deterministic layer.

## Required evidence families

| Family | Deterministic values | Notes |
|---|---|---|
| silence | global and per-voice attack/release gaps | Ties do not create attacks. |
| duration | preceding/following duration ratios and held-note releases | Exact rational values are authoritative. |
| meter | measure position, beat position, metric-strength policy result | Policy name/version is required. |
| texture | active voices, attacked voices, density change, vertical note count | Descriptive, not structural. |
| contour | interval and direction changes by logical voice | Declare written/concert pitch basis. |
| notation | fermata, slur endpoint, breath/caesura, barline/repeat/ending | Explicit source facts only. |
| directions | tempo, dynamics, rehearsal marks | Lyric content and textual meaning are excluded from the general phrase model. |
| harmony link | references to versioned harmony/cadence hypotheses | Never copied into deterministic evidence as fact. |

## Record shape

```json
{
  "evidence_id": "ev_phrase_frame_...",
  "type": "phrase_boundary_evidence_frame",
  "time": {"numerator": 16, "denominator": 1},
  "source_event_refs": ["note_...", "measure_..."],
  "observations": {
    "global_attack_gap_before": {"numerator": 1, "denominator": 2},
    "global_attack_gap_after": {"numerator": 0, "denominator": 1},
    "measure_position": {"numerator": 0, "denominator": 1},
    "active_voice_count_before": 2,
    "active_voice_count_after": 1,
    "explicit_fermata": false,
    "barline_style": "light-light"
  },
  "algorithm": {
    "name": "musicanote-phrase-boundary-evidence",
    "version": "0.1.0",
    "config_hash": "..."
  }
}
```

Absent observations are `null` or omitted; they are never silently treated as false. Every observation must be reproducible from Canonical Core plus a named deterministic policy.

## Later analysis contract

The Phrase Analyzer may combine these frames with versioned harmony, cadence, local-key, motif, and melodic-continuity hypotheses. Its output is an Analysis Record with alternatives, confidence, evidence references, engine version, and `[start,end)` spans. Phrase labels and selected boundaries never mutate Core or deterministic evidence.

## Hierarchical repetition and continuation

A local rest or attack gap is evidence for a possible division, not proof of a full phrase boundary. The Phrase Analysis Layer MUST be able to retain at least two levels:

- `phrase`: a primary phrase boundary shown in the normal review segmentation;
- `subphrase-cell`: an internal repeated or sequential cell boundary retained for inspection but suppressed from the primary segmentation.

When consecutive cells share a sufficiently similar normalized duration/IOI pattern and melodic contour, the analyzer may issue a `repeated-figure-continuation` hypothesis. It may then propose a `repeated-figure-run-start` and `repeated-figure-run-end` while preserving every internal gap as counter-evidence. A separate `rhythmic-gesture-continuation` hypothesis may connect two pickup-like gestures that share a short-short-long rhythmic prefix and are followed by a materially larger closing gap.

A `repeated-figure-run-end` alone MUST NOT cross the primary phrase-boundary threshold. It is a structural location hypothesis, not independent closure. Promotion requires a separate closure cue that already meets the configured boundary threshold and is not contradicted by strong temporal continuity. Implementations MUST expose `requiresIndependentClosureCue` and whether the run end was promoted. A fixed minimum phrase length MUST NOT be used as a substitute because genuinely short phrases remain possible.

These are versioned Analysis Layer hypotheses, not Canonical Core facts and not deterministic Layer C labels. Each record must expose the run/group ID, source boundary indices or stable event IDs, cell length, similarity evidence, raw pre-suppression strength, effective strength, hierarchy level, and whether cadence review is still required. Repetition alone MUST NOT prove non-boundary status: a sufficiently supported cadence, formal articulation, explicit fermata/breath, or human correction may preserve the internal point as a primary boundary.

The preferred future output is a set of competing spans rather than a destructive merge:

```text
primary hypothesis:   [run start, run end)
alternative:          [previous phrase start, run end)
internal cells:       [cell 1), [cell 2), ...
```

The prototype may select the first as the display default, but must retain the alternative and internal evidence for later calibration.

## No-lyric inference contract

The production feature vector may contain only score-derived musical evidence: attack/release gaps, rests, duration and IOI changes, metric position, melodic contour and interval behavior, register, slur/fermata/breath notation, texture and density changes, harmonic rhythm, local-key hypotheses, dominant/tonic arrival evidence, voice leading, repetition, and motif/form hypotheses.

Karaoke lyrics may be used only to propose noisy training targets. They belong to a dataset-construction namespace and MUST NOT appear in the feature payload consumed by the phrase analyzer. Evaluation MUST include lyric-free instrumental works.

An automated leakage test MUST reject inference inputs containing lyric characters, punctuation classes, line-break flags, lyric event IDs, KYSing symbols, or lyric-derived gap fields. The same score with lyrics present and removed MUST produce identical inference features and phrase predictions.

## Accuracy workflow

1. Run structural regression on a varied non-melody corpus.
2. Implement and unit-test each evidence family independently.
3. Display evidence frames in the review UI without selecting boundaries.
4. Create a small, carefully reviewed phrase-boundary calibration set.
5. Compare rule, statistical, and model candidates against that set.
6. Enable phrase suggestions only with calibrated confidence and visible alternatives.

## Change documentation gate

An algorithm version is not complete until its rule rationale, input/output fields, thresholds, regression fixtures, affected real-score examples, known counterexamples, and migration impact are recorded. Code, tests, this contract, the viewer implementation note, and the dated development log must reference the same analyzer version.
