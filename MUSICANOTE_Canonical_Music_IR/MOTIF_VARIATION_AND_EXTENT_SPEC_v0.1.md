# MUSICANOTE Motif Variation and Extent Specification v0.1

## 1. Purpose

This specification defines how MUSICANOTE proposes Motif cores, completes occurrence extents, recognizes transformed occurrences, groups Motif families, and separates work-internal structural role from cross-work retrieval value.

Exact equality is evidence, never the definition of Motif identity. Motif identity is a versioned Analysis Layer hypothesis supported by Canonical events and deterministic evidence.

## 2. Layer contract

### Canonical Core observations

- stable Note, Attack, Sounding Event, Voice, Staff, Measure, and source IDs;
- rational onset and duration;
- written and concert pitch spelling;
- tie-chain membership;
- MusicXML beam number and begin/continue/end/hook value;
- rest, grace, articulation, slur, fermata, and metric facts when present.

### Deterministic evidence

- normalized beam groups;
- attack sequence and tie-aware sounding duration;
- interval, contour, pitch-class, register, duration-ratio, IOI-ratio, and metric-position sequences;
- rest/gap evidence;
- local duration baseline and long-arrival ratio;
- repeated-note ratio, pitch entropy, rhythmic entropy, and onset-grid pattern;
- alignment maps between candidate occurrences.

### Analysis Layer hypotheses

- Motif core and complete occurrence span;
- Motif family and occurrence/variant identity;
- transformation tags;
- work-internal role;
- retrieval distinctiveness;
- candidate alternatives, confidence, and evidence references.

Phrase, Cadence, harmony, and local key remain separate Analysis records. They may provide evidence but MUST NOT be copied into Motif Core facts.

## 3. Beam information

### 3.1 Source preservation

For every notated note, preserve every MusicXML `<beam>` element as:

```json
{
  "number": 1,
  "value": "begin",
  "source_ref_id": "src_note_..."
}
```

Allowed normalized values are `begin`, `continue`, `end`, `forward-hook`, and `backward-hook`. Unknown source values remain in a source extension and produce a validation warning.

### 3.2 Normalized beam groups

Create deterministic `beam_group_id` values separately per score, part, staff, voice, beam level, and uninterrupted begin-to-end chain. Cross-staff notation retains the logical voice and records every displayed staff. Grace and cue groups MUST NOT silently merge with ordinary attack groups.

Derived beam evidence contains:

- `beam_group_id` and level;
- ordered note and Attack Event IDs;
- `[start,end)` span;
- attack count;
- complete/incomplete/orphan status;
- tie-aware terminal Attack Event;
- source beam references.

Beam membership raises grouping evidence but never proves a Motif. A beam group can be accompaniment, scale passage, or merely engraving convenience.

## 4. Candidate proposal channels

The analyzer MUST retain the proposal channel instead of collapsing all candidates into one list.

1. `exact_core_anchor`: exact transposition-invariant interval/rhythm signature.
2. `approximate_melodic`: tolerant melodic/rhythmic sequence alignment.
3. `beam_rhythm_cell`: recurrent beam-group rhythm and contour.
4. `repeated_note_rhythm`: low-pitch-entropy but recurrent rhythm cell.
5. `short_correspondence`: two-to-three-attack correspondence at parallel structural positions.
6. `phrase_parallel_unit`: unit bounded by comparable internal Phrase evidence.
7. `human_seed`: explicit annotation, stored separately from model hypotheses.

Exact anchors receive high localization precision but no automatic privilege in family identity or complete extent.

## 5. Core and complete extent

Every occurrence SHOULD distinguish:

- `core_span`: the smallest stable identity-bearing aligned region;
- `occurrence_span`: the complete musical gesture;
- optional `lead_in_span`;
- optional `arrival_span`;
- `alignment_map` from family prototype events to occurrence events.

The displayed bracket uses `occurrence_span`. A diagnostic view may show the core inside it.

Phrase boundaries MUST NOT be copied blindly as Motif boundaries. A Phrase or subphrase boundary is one extent candidate among beam, rest, metric, duration, tie, contour, harmonic-arrival, and recurrence-consistency evidence.

## 6. Long-arrival extension rule

After locating a core, inspect up to the next three Attack Events or the next strong incompatible boundary, whichever comes first. Propose extension when at least two independent signals hold:

- following duration is at least 2.5 times the local median attack duration;
- the attack closes the current primary beam group or immediately follows it;
- matched occurrences have aligned arrival position even when duration differs;
- contour reverses, stabilizes, or reaches a repeated terminal pitch;
- metric position is stronger than the preceding short attacks;
- a rest, fermata, breath, tie-chain completion, or substantial release gap follows;
- Harmony/Cadence layer reports arrival or prolongation support.

Reject or lower extension when the candidate begins a new beam group, continues a sequential pattern, introduces a new independent rhythmic cell, or aligns with the next occurrence's core onset.

Terminal duration is compared categorically as `short`, `medium`, `long`, or `sustained`, as well as numerically. Two- versus three-beat arrivals can therefore remain the same structural arrival with a `duration_variation` tag.

## 7. Repeated-note rhythmic Motif

A pitch-identity filter MUST NOT discard a candidate solely because interval diversity is low. Propose `repeated_note_rhythm` when:

- there are at least four Attack Events, unless retained only as a fragment;
- pitch entropy is low or one/two pitch classes dominate;
- normalized duration/IOI pattern recurs at least twice in the work;
- attack grouping, metric placement, or terminal arrival is sufficiently consistent;
- the rhythm is more informative than a uniform repeated pulse.

Store melodic distinctiveness and rhythmic distinctiveness separately. Such a cell may receive high internal-role confidence and low retrieval eligibility.

## 8. Short corresponding figures

Two-to-three-attack material is stored as `motivic_fragment`, not automatically as a complete Motif. It may support a family when at least two of the following hold:

- it occurs at parallel positions in two or more Phrase frames;
- it preserves contour or scale-degree function under transposition;
- it consistently prepares the same core family;
- rhythm and metric placement recur;
- surrounding harmony or bass function is comparable.

A fragment MAY participate in family evidence and Phrase linkage but MUST NOT be used as a standalone cross-work search query unless expanded with context.

## 9. Approximate occurrence alignment

Family discovery SHOULD use local sequence alignment rather than fixed-length equality. The alignment supports pitch substitution, duration change, insertion/deletion of ornament notes, repeated-note expansion/compression, and terminal extension/truncation.

Recommended feature channels:

- transposition-invariant interval magnitude;
- interval direction and melodic contour;
- normalized duration and IOI in log-ratio space;
- metric-position correspondence;
- beam-group position;
- scale degree when a local-key hypothesis exists;
- terminal-arrival role;
- insertion/deletion coverage.

Every match stores per-channel scores, alignment coverage, edit operations, and transformation tags. A high total score MUST NOT hide a very low coverage score.

## 10. Internal role versus retrieval distinctiveness

Each occurrence stores independent scores:

```json
{
  "internal_role": {
    "score": 0.86,
    "evidence": ["phrase_parallelism", "rhythmic_recurrence"]
  },
  "retrieval_distinctiveness": {
    "score": 0.31,
    "eligible": false,
    "against": ["low_pitch_entropy", "common_rhythm"]
  }
}
```

`internal_role` considers recurrence within the work, Phrase position, development, response, and structural return. `retrieval_distinctiveness` considers corpus frequency, pitch/rhythm entropy, length, and expected false matches. Low retrieval value MUST NOT delete a structural Motif hypothesis.

## 11. Motif-family multi-evidence decision

Family grouping uses a scored hypothesis, not a single rhythm-family key. Recommended initial uncalibrated weights are:

- interval alignment: 0.25;
- contour: 0.15;
- duration/IOI rhythm: 0.20;
- metric and beam position: 0.10;
- core coverage/edit cost: 0.15;
- complete-extent and arrival correspondence: 0.10;
- Phrase-position/internal-role correspondence: 0.05.

These weights are review defaults, not musical truth. Store the raw channels so they can be recalibrated without reparsing MusicXML.

Suggested review bands:

- `>= 0.84`: same-family candidate;
- `0.72–0.84`: competing same-family/new-family hypotheses;
- `< 0.72`: normally separate, while preserving fragment evidence.

When the two best family hypotheses differ by less than 0.05, mark the assignment `ambiguous` and retain both. Never create `Motif 2′` merely because two candidates share a rhythm-family name.

## 12. Transformation vocabulary

The v0.1 Analysis Layer supports:

- `transposition`;
- `interval_substitution`;
- `contour_preserving_variation`;
- `rhythmic_augmentation` / `rhythmic_diminution`;
- `duration_redistribution`;
- `repeated_note_expansion` / `repeated_note_compression`;
- `ornamental_insertion` / `ornamental_deletion`;
- `terminal_substitution`;
- `arrival_extension` / `arrival_truncation`;
- `fragment_recall`;
- `sequence_restatement`.

Transformation labels are hypotheses with evidence and confidence.

## 13. Suggested Analysis Record

```json
{
  "analysis_type": "motif_occurrence",
  "family_hypotheses": [
    {"family_id": "mf_001", "score": 0.87},
    {"family_id": "mf_004", "score": 0.82}
  ],
  "selected_family_id": "mf_001",
  "core_span": {"start_event_id": "atk_10", "end_event_id_exclusive": "atk_16"},
  "occurrence_span": {"start_event_id": "atk_10", "end_event_id_exclusive": "atk_17"},
  "arrival_span": {"start_event_id": "atk_16", "end_event_id_exclusive": "atk_17"},
  "alignment_map": [],
  "transformations": ["arrival_extension"],
  "channel_scores": {},
  "internal_role": {},
  "retrieval_distinctiveness": {},
  "evidence_refs": [],
  "engine_version": "motif-analyzer-v0.2"
}
```

All spans use Canonical `[start,end)` semantics and stable IDs.

## 14. Processing order

1. Parse and validate Canonical events, ties, beams, and rational time.
2. Build deterministic attack, beam, metric, rhythm, contour, and gap evidence.
3. Propose cores through all candidate channels.
4. Align approximate occurrences and retain alternatives.
5. Decode complete extents using multi-evidence boundaries.
6. Cluster family hypotheses with uncertainty.
7. Score internal role and retrieval distinctiveness independently.
8. Compare with Phrase/Harmony/Cadence records without mutating them.
9. Render core, complete extent, transformations, and reasons in the review UI.
10. Store human accept/correct/reject as separate Annotation Records.

## 15. Required regression fixtures

- exact core with two- versus three-beat terminal arrival;
- repeated-note rhythm with low melodic entropy;
- two-to-three-note Phrase-opening correspondence;
- ornament insertion/deletion;
- transposed contour with one changed interval;
- rhythmic augmentation and diminution;
- beam group that is not a Motif;
- Motif crossing or nested inside a proposed Phrase boundary;
- two plausible family assignments within the ambiguity margin;
- structurally important Motif that is ineligible for cross-work retrieval.

## 16. Current implementation gap

The Canonical enrichment parser already reads MusicXML `<beam>` elements into `notation.beams`. The current schema leaves `notation` open and the MusicSearch event cache does not carry normalized beam groups. Therefore beam normalization, schema validation, event-cache transport, and analyzer consumption remain implementation work.

