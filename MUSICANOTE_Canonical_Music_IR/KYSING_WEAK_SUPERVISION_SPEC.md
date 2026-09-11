# KYSing Weak Supervision for Phrase Learning v0.1

## 1. Goal

KYSing is used to discover musical characteristics near likely vocal phrase breaks. Lyrics are not phrase-analysis evidence and are not available to the production analyzer. The resulting analyzer must work unchanged on music without lyrics.

```text
KYSing lyric discontinuity
        -> noisy training target only
Canonical IR musical facts and versioned musical analyses
        -> lyric-free feature frame
        -> phrase boundary learner
        -> lyric-free production inference
```

## 2. Strictly separated data products

### `kysing_raw_events`

Stores original lyric/control events, timing, encoding diagnosis, file identity, and source location for filtering and audit only.

### `weak_boundary_targets`

Stores noisy target locations proposed from cleaned lyric discontinuities. Allowed labels are `weak_positive`, `weak_possible`, `hard_negative`, and `ambiguous`. Confidence is a training weight, not phrase-analysis confidence.

### `musical_feature_frames`

Stores only lyric-free musical features computed from Canonical IR. Training may join a frame to a weak target using an opaque frame ID. No raw or derived lyric field may enter this product.

## 3. Symbol and file filtering

Capitalization MUST NOT be used as phrase-boundary evidence. Classification must support Unicode scripts independently of language and must not require whitespace-separated words. A prefiltered word-count manifest is only a seed corpus, not proof of language-neutral coverage. Punctuation proposes weak supervision only; musical gaps are computed independently from notes. Chord-shaped short words remain ambiguous until stream context resolves their role.

Classify each raw event as `lexical`, `syllable_extension`, `vocal_control`, `display_control`, `metadata`, `corrupt`, or `unknown`.

Symbol-only events do not produce lexical content. Files below a versioned minimum count or ratio of lexical events are excluded from weak-target generation. The exclusion reason, category counts, encoding diagnosis, and parser version remain auditable. Thresholds are proposed only after inventorying the actual KYSing formats and symbol distribution.

## 4. Weak-target generation

Lyric discontinuities propose time locations; they do not explain the music and are not canonical facts.

- `weak_positive`: a strong temporal discontinuity or a location repeated consistently across verses.
- `weak_possible`: a plausible but insufficient discontinuity.
- `hard_negative`: a lyric/display break while musical motion remains continuous.
- `ambiguous`: uncertain alignment, encoding, or symbol meaning.

To avoid selection bias, training frames MUST also be sampled from non-lyric-selected positions throughout the score, including attacks, releases, rests, measure boundaries, harmonic changes, and matched control locations.

## 5. Lyric-free musical features

For every candidate time point, compute musical features over versioned before/after windows:

- rests and attack/release gaps by logical voice;
- preceding and following IOI and duration distributions;
- held-note releases and onset synchronization;
- exact meter position and versioned metric strength;
- melodic interval, contour, register, and directional change;
- slur endpoints, fermata, breath, and caesura when explicitly notated;
- active-voice, density, orchestration, and texture change;
- harmonic rhythm and vertical stability;
- versioned global/local-key hypotheses;
- dominant arrival, tonic arrival, and dominant-to-tonic resolution evidence;
- bass motion, upper-voice tendency-tone resolution, and voice-leading distance;
- repetition, motif recurrence, and parallel-location consistency.

`V`, `I`, and `V-I` are uncertain Analysis Layer features with confidence and key-hypothesis references. They are never Canonical Core facts and never mandatory boundary conditions. Non-cadential phrase breaks and internal cadences that are not phrase boundaries MUST both be represented during training and evaluation.

## 6. Training stages

1. Build an interpretable weighted-rule baseline.
2. Train logistic or gradient-boosted models on explicit lyric-free features.
3. Introduce a sequence model only after sufficient reviewed labels exist.
4. Optionally use teacher-student training, with the student receiving no lyric fields.

Duplicate files, transpositions, alternate karaoke versions, and arrangements of the same work MUST remain in one data split to prevent leakage.

## 7. Evaluation

Report results separately for held-out vocal works with lyrics hidden, lyric-free instrumental works, clear cadential boundaries, non-cadential boundaries, internal cadences that are not phrase boundaries, and meter/genre/tempo/texture groups.

Evaluation should report precision, recall, F1, boundary distance, calibration, and coverage using a declared time-tolerance policy. Weak targets alone cannot establish final accuracy; a small human-reviewed calibration and test set is required.

## 8. Mandatory leakage tests

The dataset build fails if an inference feature contains lyric text or character statistics, punctuation or line changes, lyric event counts or IDs, lyric-derived timing gaps, KYSing control symbols, or filenames/metadata correlated with weak labels.

Run the same score twice, once with lyrics present and once with lyrics removed. Inference features and phrase predictions MUST be identical.

## 9. Implementation order

1. Inventory KYSing formats, symbols, encodings, duplicates, and timing precision.
2. Implement event classification and auditable exclusion reasons.
3. Generate weak targets in an isolated dataset namespace.
4. Generate score-wide candidate locations independently of lyrics.
5. Implement lyric-free musical feature frames.
6. Connect versioned `V`, `I`, `V-I`, local-key, and voice-leading evidence.
7. Add schema and automated leakage validation.
8. Implement an explainable Phrase Rule v0.1 baseline.
9. Display candidates, supporting evidence, and counter-evidence in Review UI.
10. Evaluate on lyric-hidden vocal and lyric-free instrumental sets before model expansion.
