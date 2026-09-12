# MUSICANOTE Motif / Phrase Layering Specification v0.1

## Principle

Motif and Phrase are separate Analysis Layer concepts. Neither belongs in Canonical Core. A Motif boundary is not a Phrase boundary, and repetition does not prove closure.

## Structural hierarchy

```text
Canonical Note / Attack / Sounding Event
  ↓
Motif Occurrence
  ↓
Motif Group or Transformation Family
  ↓
Phrase Hypothesis
  ↓
Section / Form Hypothesis
```

A Phrase may contain multiple Motif occurrences. Motifs may cross a proposed Phrase boundary, and a Phrase may contain no confidently identified Motif. All spans use Canonical IR `[start,end)` time semantics and stable event references.

## Motif Analysis Record

A Motif record SHOULD contain a versioned motif identity, occurrence spans, source event references, similarity/transformation evidence, alternatives, confidence or uncalibrated strength, and analyzer version. Repetition starts, internal cells, sequence/transposition relations, and run endpoints are Motif-layer evidence.

## Phrase Analysis Record

A Phrase record SHOULD contain a span hypothesis, boundary hypotheses, closure evidence, alternatives, confidence or uncalibrated strength, and analyzer version. Its principal evidence classes are temporal/breathing separation, melodic closure, rhythmic closure, governing harmony and Cadence, and human review when available.

Phrase analysis MAY reference Motif occurrence or group IDs as supporting context. It MUST NOT convert a Motif start or end into a Phrase boundary without independent Phrase-level evidence.

## Aggregation rule

Several Motif occurrences may be grouped into one Phrase when Phrase-level closure is absent between them and continuity evidence supports the larger span. An internal Motif boundary remains queryable even when it is not selected as a Phrase boundary. Suppression means “not selected at this structural level,” never deletion of evidence.

## Annotation rule

Human labels for Motif identity, Motif membership, Phrase span, and Phrase boundary MUST be stored as separate annotation types. Correcting a Phrase boundary must not silently rewrite Motif occurrences, and correcting a Motif must not silently rewrite a Phrase.

## Current prototype contract

`local-boundary-evidence-v1.4` records `repeated-motif-start` and `repeated-figure-run-start` as non-voting Motif-layer cues. They carry `contributesToPhraseStrength=false`. A coincident Phrase boundary requires an independent Phrase evidence score that already meets the Phrase threshold.

## Deferred

- Stable Motif and Motif-occurrence IDs linked to Canonical IR events;
- explicit transformation vocabulary;
- governing-harmony/Cadence integration;
- learned Phrase aggregation after sufficient reviewed annotations;
- independent Motif and Phrase overlays in the shared score viewer.
