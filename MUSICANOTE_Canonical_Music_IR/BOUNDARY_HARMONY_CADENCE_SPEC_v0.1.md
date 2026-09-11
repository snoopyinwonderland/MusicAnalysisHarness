# Boundary Harmony and Cadence Analysis v0.1

## Purpose

This increment analyzes only a bounded window around a proposed phrase boundary. It does not attempt exhaustive chord labelling over the complete score. Its theoretical source is `K:\MUSICANOTE_Harmony_Analysis_Harness_Guide.md`, especially the separation of observed sonority, surface chord, function, and governing harmony; the cadence minimum grammar; incomplete-voicing rules; short-span gate; and bounded phrase/cadence feedback.

The output is an Analysis Layer record. It MUST NOT modify Canonical Core or deterministic evidence.

## Input

- Canonical sounding and attack events, or a clearly marked transitional indexed-note adapter;
- a versioned phrase-boundary hypothesis;
- rational boundary time and `[start,end)` semantics;
- key-signature observation and meter evidence;
- all relevant parts, staves, and voices rather than the melody alone.

Lyrics, punctuation, capitalization, and lyric-derived gaps MUST NOT be inputs.

## Window and stages

The v0.1 prototype inspects up to eight quarter notes before and two quarter notes after the boundary. These are configuration values, not musical constants.

1. Construct attack/active/release observations.
2. Generate surface-chord candidates without treating every onset as a new harmony.
3. Merge adjacent identical candidates and suppress unsupported short spans.
4. Retain preparation, arrival, and immediate post-boundary context.
5. Compare relative-major and relative-minor key hypotheses derived from the observed key signature.
6. Propose PAC, IAC, HC, DC, plagal, or `no_clear_cadence` with evidence and counter-evidence.

A phrase boundary never proves a cadence. A V–I-like surface pattern never proves a phrase boundary. The two modules exchange bounded evidence while retaining independent strengths.

## Incomplete and stale evidence

- A root and fifth without a third MUST be displayed as `Root(no3)` or an equivalent ambiguous label, not as an asserted major/minor chord.
- A seventh-chord label with missing defining tones must retain omissions and reduced strength.
- A very short preparation chord is excluded unless its fit or another independent evidence class supports it.
- An arrival sonority that ended more than the configured recency allowance before the boundary is not reused as the boundary harmony.
- Sparse monophony may produce `insufficient_evidence`; the schema must allow no selected harmony or cadence.

## UI contract

Each phrase option SHOULD show a quickly scannable phrase identity:

`Phrase number · measure range · first pitch → last pitch · Cadence candidate`

The detail panel MUST state that boundary harmony is a local window rather than a start-to-end Phrase progression. It SHOULD render three explicit semantic fields: preparation before the terminal arrival, terminal/arrival harmony, and the first harmony after the boundary. Analysis records SHOULD expose these as `preparationRoman`, `arrivalRoman`, and `afterBoundaryRoman`; `romanDisplay` remains a backward-compatible compact representation using `preparation → arrival | after-boundary`.

The review-facing harmony values SHOULD use Roman numerals relative to the explicitly displayed selected-key hypothesis. Absolute root/quality labels MUST remain available in the analysis record for traceability and fallback. Roman labels are interpretations, not Canonical Core values, and must never be presented without the key hypothesis that governed them.

Campania MAY be used for Roman-numeral value glyphs only. Prose, Korean labels, punctuation/arrows, controls, key names, and pitch names MUST retain the normal UI font because Campania's music-analysis substitutions are not general-text typography. A bundled, licensed webfont is preferred to a machine-local font dependency.

The detail panel shows the raw boundary measure/beat only as secondary evidence. Cadence strength is labelled `uncalibrated evidence strength`, never probability. Unknown and withheld results are displayed explicitly rather than silently omitted.

## Governing harmony correction path

A short surface sonority MUST NOT by itself determine the governing terminal harmony or Cadence. When a reviewed case identifies a dominant arrival that the surface template misses, the implementation must improve general evidence handling—defining-tone completeness, non-chord-tone candidates, prolongation, bass/metrical support, and sequence-level cadence grammar—rather than add a score-specific label. AI output, human correction, and adjudication status remain separate Analysis/Annotation records.

## Deferred

- Canonical `note_id`, `attack_event_id`, and `sounding_event_id` linkage;
- local-key search beyond key-signature relative modes;
- NCT roles, cadential 6/4, augmented-sixth, applied-chord, rootless-jazz, modal, and blues profiles;
- dynamic-programming harmony segmentation;
- calibrated thresholds and adjudicated cadence evaluation data.

The transitional viewer implementation therefore remains a prototype and MUST NOT be exported as gold annotation.
