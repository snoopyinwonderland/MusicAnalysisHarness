# Phrase Review Viewer Contract v0.1

## Purpose

MusicSearch owns the shared MusicXML/Verovio score viewer. Music Analysis Harness owns phrase evidence and analysis contracts. The viewer consumes versioned analysis data and writes review records; it does not implement a second phrase analyzer or add phrase labels to Canonical Core.

## Current prototype flow

```text
MusicXML / indexed notes
  -> local-boundary-evidence-v1.2 (lyrics excluded)
  -> complete phrase ranges plus supported candidate markers over the Verovio score
  -> evidence details in the right panel
  -> accept / reject / can't judge + reviewer comment
  -> append-only phrase review JSONL
```

The current score endpoint includes `phraseAnalysis`. Its `strength` is an uncalibrated evidence score, not a correctness probability. Harmony/cadence evidence is explicitly unavailable in this version.

## Viewer behavior

- The `Phrase 분석` layer is enabled on initial page entry. The control hides or restores the complete phrase overlay and review panel.
- The overlay draws every visible phrase range from the first analyzed note through the last analyzed note, using alternating colors and `P1`, `P2`, ... labels.
- Range labels expose human-readable measure extent and endpoint pitches (for example, `Phrase 1 · 17–18마디 · F#5→F#5`), with a visible end marker.
- Measure extent is derived from the `[start,end)` boundary time and includes silent measures; endpoint pitch names the last included attack and is not used as the range clock.
- A multi-system phrase is drawn as connected range segments above each affected staff system so its beginning and end remain identifiable.
- Selecting a Phrase from the review selector or clicking its `Phrase N` score label highlights all of its system segments for one second. Repeating the same selection must retrigger the highlight; an unrendered target page is engraved on demand before scrolling to it.
- Only `supported=true` candidates receive score markers in v0.1.
- A repeated/sequential cell demoted to `primaryLevel=subphrase-cell` remains in the analysis payload but does not split the default phrase band. The viewer may later expose these points as lighter optional cell ticks.
- A displayed boundary marker names the phrase beginning at that point (`P2 시작`, `P3 시작`, ...). Boundary index `i` means immediately before note/attack `i`; default phrase spans are non-overlapping `[start,end)` ranges, so the previous phrase ends at `i-1` and the next begins at `i`.
- Explicit overlapping membership must be represented by separate, versioned phrase spans or competing hypotheses. The viewer must not imply overlap merely because one event is used as a boundary anchor.
- Consequently, split labels such as `P1│P2` and split-color shared-note anchors are forbidden for ordinary boundaries and reserved for an explicit overlap hypothesis in the analysis payload.
- Clicking a marker selects the matching candidate in the right panel.
- The panel shows score location, evidence strength, and individual cues.
- The review selector is phrase-first: phrase number, measure range, first pitch, last pitch, and harmony-analysis availability precede raw boundary coordinates.
- If no versioned harmony record is connected, the UI must say `화성 분석 대기`; it must not synthesize a progression from the key signature or other incomplete evidence.
- Lyrics, punctuation, line breaks, and capitalization are not shown as production inference evidence.
- Turning the layer off changes only presentation; source MusicXML and analysis records remain unchanged.

## Review API

`POST /api/analysis/phrase-review`

The payload identifies the work, stream, analyzer version, boundary-before-note index, displayed score coordinate, candidate snapshot, verdict, and optional comment. The server writes one immutable JSON object per line. Allowed stored verdicts are `accepted`, `rejected`, and `ambiguous`; the UI presents `ambiguous` as `Can't Judge` (`판단 보류`) so it is not mistaken for an analytical phrase label.

Reviews default to `trainingEligible=false`. A UI click is evaluation evidence, not automatically a gold label. Promotion to a calibration or training set requires stable Canonical IR target resolution, reviewer provenance, and an explicit eligibility process.

The record may preserve an `analysisContext` snapshot containing the boundary-harmony and Cadence hypotheses visible at review time. This makes later algorithm changes auditable; the snapshot remains AI context and never becomes the human label.

## Shared ownership boundary

| Concern | Owner |
|---|---|
| MusicXML rendering, zoom/navigation, note hit targets | MusicSearch viewer |
| Canonical event IDs and exact time coordinates | Music Analysis Harness |
| Boundary evidence and versioned hypotheses | Music Analysis Harness |
| Overlay presentation and review interaction | MusicSearch viewer |
| Review schema and training eligibility policy | Shared contract, governed by Music Analysis Harness |

The projects may share one viewer without sharing implementation internals. Communication should move toward JSON Schema-validated records keyed by Canonical IR IDs.

## Transitional limitations

The current MusicSearch corpus uses `boundaryIndex` plus onset/measure/beat because its notes do not yet expose Canonical IR stable IDs. Before review data is treated as durable annotation, the viewer must receive `score_id`, `note_id` or `attack_event_id`, and rational global-quarter coordinates from the Canonical parser. Existing prototype records should then be migrated through note-content/time alignment and marked `exact`, `mapped`, `ambiguous`, or `orphaned`.

Position correction and missing-boundary insertion are deferred. v0.1 reviews only candidates already proposed by the analyzer. The next UI increment should allow selecting any attack event and submitting a `corrected` boundary target.

The v1.2 transitional analyzer also exposes `repeatedFigureRuns` and `rhythmicGestureGroups`. These are analysis hypotheses with `requiresCadenceReview=true`; they are not Canonical IR entities or validated human annotations.

## Next integration increment

1. Replace the index target with Canonical IR event IDs and rational time.
2. Add harmonic/cadential evidence as separate evidence references, never as Core fields.
3. Add missing-boundary/corrected-position review.
4. Build a review queue stratified by strong candidates, rejected candidates, and lyric-free instrumental controls.
5. Calibrate thresholds only after an adjudicated evaluation set exists.
