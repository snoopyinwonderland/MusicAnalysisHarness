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

`local-boundary-evidence-v1.7` records `repeated-motif-start` and `repeated-figure-run-start` as non-voting Motif-layer cues. They carry `contributesToPhraseStrength=false`. A coincident Phrase boundary requires an independent Phrase evidence score that already meets the Phrase threshold.

A recurrence whose attack distance is no more than twice its Motif length MAY be proposed as a local Motif-repetition group. Its internal start can be demoted to subphrase level while preserving the raw boundary evidence. Distant recurrence MUST NOT trigger automatic Phrase merging.

Two Motif relations with the same source-to-recurrence displacement and preserved internal spacing MAY define a parallel recurrence group. The second-cell starts SHOULD remain queryable Motif/subphrase articulations but SHOULD NOT be promoted to Phrase boundaries without independent closure or Cadence evidence. A sufficiently strong, separately derived Cadence MAY override this continuity evidence.

Motif-family similarity MAY use transposition-invariant interval sequence, melodic contour, normalized duration, and coverage. A changed ending MAY be represented as a prime variant such as `Motif 1′`; this label is an Analysis Layer hypothesis and MUST retain its similarity evidence and analyzer version.

An explicit tie continuation MUST NOT start a Phrase. If a boundary candidate falls on a barline-spanning tied sounding event and a same-pitch new attack occurs at its release, the boundary MAY move to that re-articulated attack. The decision MUST reference both the tie/sounding evidence and the new attack event.

For boundary-focused harmony, a terminal note tied into a following measure MUST be evaluated against the complete vertical sonority at the tie-continuation onset. Implementations MUST preserve MusicXML chord members; a monophonic retrieval stream is insufficient evidence for this decision. In Canonical IR this provenance SHOULD reference the tie chain, sounding event, attack events, and vertical slice IDs.

The shared score viewer MUST distinguish Phrase and Motif visually. Phrase spans use a thick solid upper lane; Motif candidates use a thin bracket-shaped dashed lower lane. Phrase and Motif display counters are independent and each begins at 1. The prototype orders Motif display numbers by score position; these display numbers are not stable analysis IDs. A master control is named `Structure Analysis`/`구조 분석`, while the underlying records and semantics remain separate.

Selecting either a Phrase or a Motif SHOULD open details for that same structural object. Roman-numeral harmony values MAY use a music-analysis font; pitch names, `unknown`, prose, controls, and other ordinary text MUST remain in the normal UI font.

The matched bounded signature proves a local relation but may cover only the shared opening of a longer cell. For display, the prototype uses the recurrence cycle: the first occurrence spans from its start to the next related start using `[start,end)`, and the second uses the same global-quarter duration; each endpoint snaps to the final attack before the exclusive end. It does not infer Motif closure from a cadence or reuse a Phrase endpoint. A short provisional Phrase boundary at a close recurrence start is demoted to an internal Motif/subphrase boundary only when Phrase-level closure evidence is absent.

Motif occurrence extent MUST NOT be inherited from a Phrase span. A bounded matching signature is relation evidence, not necessarily the complete Motif extent. Once a prototype occurrence is established from a local recurrence cycle or parallel-cell structure, its attack count SHOULD be projected to a distant recurrence. A duration-only difference at the final event MAY retain the same Motif variant identity when interval sequence, contour, and event coverage remain equivalent.

When two long passages of at least twelve aligned attacks show high transposition-normalized pitch agreement and rhythmic agreement, Phrase segmentation SHOULD be compared across the full source/recurrence pair. An internal boundary that appears only as local noise MAY be demoted to `internal-repeated-passage`; its original strength and evidence MUST be preserved. A separately validated Cadence, clear observed rest, or human correction MAY override this continuity hypothesis.

An `observed-gap` derived from notated attack durations MUST NOT be treated as a clear rest when the preceding tie chain carries its sounding event into the boundary measure. A strong observed gap not covered by a tie MAY override repeated-passage continuity. When a local recurrence cycle has already established a Motif prototype extent, a broader later partial match MUST NOT lengthen that prototype.

A Motif span ending on the attack of a tied sounding event retains its canonical `[start,end)` occurrence semantics. The viewer SHOULD additionally render the endpoint through all notated tie-continuation glyphs so a reviewer can see the complete held sound. This display extension MUST NOT create an extra attack or silently change the Analysis Record endpoint.

## Deferred

- Stable Motif and Motif-occurrence IDs linked to Canonical IR events;
- explicit transformation vocabulary;
- governing-harmony/Cadence integration;
- learned Phrase aggregation after sufficient reviewed annotations;
- stable cross-session mapping between review display numbers and versioned Motif occurrence IDs.
