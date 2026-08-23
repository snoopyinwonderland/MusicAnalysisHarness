# Validation Rules and Regression Strategy

## 1. Severity

Validators emit `error`, `warning`, or `info`, with rule ID, entity refs, source refs, and suggested remediation. Errors make the IR invalid; warnings preserve a usable but qualified document.

## 2. Timeline validation

- rational denominators are positive; duration numerators are non-negative
- ordinary notes/rests have positive notated duration; grace notes follow the grace contract
- global onset equals measure global start plus onset in measure
- event order is deterministic even when onset is equal
- voice overlap is allowed only for declared chord members, cross-staff display, or explicit overlap policy
- backup/forward cursor normalization reproduces all voice onsets
- actual measure duration is consistent with contained timeline; under/overfull measures are flagged with pickup/cadenza exceptions
- meter changes take effect at their declared positions

## 3. Tie validation

- each chain has one attack note and ordered source notes
- linked notes have compatible written/concert pitch under the selected policy
- continuation notes do not create Attack Events
- chain onset, total duration, and release equal the union of contiguous components
- orphan starts/stops, branching chains, gaps, and overlapping components are reported

## 4. Pitch validation

- step/alter/octave and written MIDI agree when MIDI is representable
- pitch class equals MIDI modulo 12 for 12-TET integral MIDI
- spelling and accidental display are distinguished; an omitted display accidental is not inferred as displayed
- concert pitch equals written pitch plus declared transposition
- microtonal pitches MAY have null MIDI and MUST retain exact alter

## 5. Measure, voice, and notation validation

- printed measure number is never used as the sequential index
- sequential indices are unique and monotonic
- pickup status is explicit when actual duration differs for that reason
- staff, voice, chord-onset, slur, articulation, and lyric references resolve
- chord members share onset but are not labeled as harmonic chords
- cross-staff events retain logical voice and display staff independently
- grace order and anchor resolve; cue/ossia/hidden status is preserved when parsed

## 6. Source traceability and referential integrity

Every note/rest MUST resolve to a Source Reference and Source File. All referenced IDs MUST exist and have compatible entity types. Source element order/locator collisions are errors. Hash algorithm and raw-byte hash are required for source files.

## 7. Derived evidence validation

Derived values MUST identify algorithm and version or be defined by the Core schema. A reproducibility validator MAY recompute pitch class, active pitch set, metric position, and vertical slices and compare exact results. Analytical labels in deterministic evidence are schema-boundary errors.

## 8. Round-trip and regression

The required test is MusicXML → Canonical IR → equivalent event reconstruction, not byte-identical MusicXML. Compare ordered attacks, written/concert pitch spelling, rests, exact onsets/durations, voices/staves, ties, meter/key-signature timelines, and notation flags selected for v0.1.

Regression corpus categories: monophony, piano two-staff, multiple voices, barline ties, tuplets, grace notes, cross-staff, pickup, meter/key changes, repeats, transposing instruments, arpeggiation, and dense polyphony. Each fixture stores source hash, parser/policy versions, expected validation codes, and a canonical semantic digest.

## 9. Release gate

A schema release requires JSON Schema meta-validation, all example fixtures passing, zero unresolved internal references, deterministic double-parse equality, and documented expected warnings. A production migration additionally requires annotation-target migration measurement on a representative corpus.

