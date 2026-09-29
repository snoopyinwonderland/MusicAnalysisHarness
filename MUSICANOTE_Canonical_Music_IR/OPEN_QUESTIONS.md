# Open Questions and Recorded Conflicts

These issues are intentionally unresolved rather than silently decided.

| ID | Question or conflict | Provisional direction | Required before |
|---|---|---|---|
| OQ-001 | Existing output calls itself `musicanote-canonical-ir-0.2`, while this first formal contract is `0.1.0`. | Treat them as different schema families and build an adapter. | Prototype integration |
| OQ-002 | Existing score ID derives partly from file name and size, while durable annotation needs identity independent of location. | Introduce source-file identity plus registry-backed score/work identity. | Annotation persistence |
| OQ-003 | Raw XPath is traceable but fragile under harmless XML edits. | Store element ordinal/path plus local fingerprint; do not use XPath as entity ID. | Parser implementation |
| OQ-004 | MusicXML voices can cross staves and voice numbers may be missing or reused. | Separate logical voice from display staff; define deterministic inference policy. | Parser implementation |
| OQ-005 | Printed timeline and playback-expanded repeat timeline differ. | v0.1 uses written timeline; add playback map extension later. | Repeat-aware analysis |
| OQ-006 | Existing `HarmonicAtom` is persisted near Core, but the guides describe it as an observation interval. | Define it as deterministic derived cache. | Compatibility adapter |
| OQ-007 | No `mn-event-tokens-v1` implementation was found. | Specify mapping only after locating its external definition or owner. | Token export |
| OQ-008 | No annotation DB/schema/API was found in this repository. | Adopt record schema first; choose DB after UI/query requirements. | Annotation UI |
| OQ-009 | Beat hierarchy in compound/additive meter needs a shared policy. | Store exact position; version metric-strength policy separately. | Metric evidence |
| OQ-010 | Written versus concert pitch basis for analyzer inputs is not universal. | Preserve both; each analyzer declares its basis. | Harmony/similarity APIs |
| OQ-011 | Grace-note performed timing is not deterministic from notation alone. | Store order/anchor/source timing only in Core. | Audio/performance integration |
| OQ-012 | MIDI cannot exactly express general microtones. | Permit exact rational alter and nullable MIDI. | Microtonal corpus |
| OQ-013 | Multiple instruments in one MusicXML part and mid-score instrument changes need identity rules. | Add instrument timeline or sub-part extension after corpus audit. | Orchestral parsing |
| OQ-014 | Cue, ossia, hidden notes/rests may or may not participate in analytical sounding events. | Preserve flags; use versioned inclusion policy. | Parser implementation |
| OQ-015 | Source hash may be raw bytes or normalized XML. | Require raw SHA-256; optionally add normalized semantic hash. | Stable ID implementation |
| OQ-016 | Persist all vertical slices or generate on demand? | Generate/cache on demand keyed by IR hash and algorithm version. | Harmony optimization |
| OQ-017 | How much source editing may retain a `score_id`? | Registry decision plus alignment report; never infer solely from hash. | Annotation migration |
| OQ-018 | Annotation mapping acceptance threshold is unknown. | Measure exact/mapped/ambiguous/orphan rates on real edits before automation. | Production migration |
| OQ-019 | Parser support for repeats, endings, cadenza measures, and tie chains across playback jumps is incomplete. | Keep written order authoritative in v0.1 and declare unsupported cases. | Production validation |
| OQ-020 | Extension namespace ownership and schema registry governance are not assigned. | MUSICANOTE-controlled registry with named owners and review. | Third-party extensions |

## Decisions required before production code

### Harmony/composition integration audit — 2026-09-24

The following conflicts were found while writing [the implementation plan](HARMONY_COMPOSITION_HARNESS_IMPLEMENTATION_PLAN.md). These are proposals, not schema migrations already applied.

| ID | Question or conflict | Provisional direction | Required before |
|---|---|---|---|
| OQ-021 | Existing Analysis hypotheses require numeric confidence; local Human Annotation requires annotator/timestamp and restricts properties. Imported corpus labels may have none of these and need dialect/provenance metadata. | Create independently versioned ImportedAnnotation and AlignmentRecord contracts. Preserve missing values; do not invent confidence, reviewers, dates, or local acceptance. | P0/P3 import contracts |
| OQ-022 | Cadence arrival and structural ending can be points, whereas the current analysis target contract is entity/span-based. | Design a typed, revision-bound point reference and compatible adapter. Do not fabricate tiny spans or equate arrival with the next phrase start. | P0 target decision; P3/P7 integration |
| OQ-023 | Current boundary harmony runs on selected Phrase boundaries and cadence scoring consumes boundary evidence. Feeding it back as independent evidence would create a circular dependency. | Independent candidate windows and H0 analysis; provenance DAG, primitive-evidence deduplication, shadow evaluation before Phrase changes. | P5/P7 |
| OQ-024 | ID documentation mentions normalized source bytes, while OQ-015 recommends raw SHA-256. | Require raw asset hash for provenance; store semantic/normalized hashes separately. Reconcile documentation and fixtures before registry rollout. | P0/P1 |
| OQ-025 | Core prose mentions fields such as directions/derived caches that are not all admitted by the strict root schema; prototype data also differs from the formal entity contract. | Publish field coverage and loss reports; resolve storage/extension placement explicitly, validate adapters, and preserve unsupported source data. Do not silently add root fields or merely relabel the prototype version. | P0/P2 |
| OQ-026 | DCML Beethoven 01-1 has an inserted MusicXML measure printed `X1`; music21 assigns its E-flat note to normalized measure `48`. Ordinal/time agreement alone does not recover that source XML note locator. | Keep the two affected annotations ambiguous; design an explicit source-measure alias/insert map and prove note-level round-trip before approval. Never infer `X1=48` from this score alone. | P2/P3 corpus expansion |
| OQ-027 | Six zero-duration grace notes in Beethoven 01-1 have TSV onset one quarter earlier than music21's notation onset. | Preserve both native and IR times; treat the four overlapping annotations as ambiguous until a grace anchor/time policy is documented and tested on more works. | P2/P3 corpus expansion |
| OQ-028 | music21 may split one two-staff MusicXML part into two internal parts (`P1-Staff1/2`), while other scores keep two original source parts. | Pilot importer records the transform and maps both lanes to source P1 with distinct staff numbers; test cross-staff/voice migration and establish canonical policy before production. | P2 production adapter |

### Appendix review conflicts recorded 2026-09-27

| ID | Question or conflict | Provisional direction | Required before |
|---|---|---|---|
| OQ-029 | Appendix r4 XML comparison found paired duration disagreements in Beethoven02-2 m3 and MozartK281-3 m139 (4 notes, 2 contexts). The rendering-ID queue key omits voice/duration, so equal onset/pitch candidates can be paired incorrectly. Whether source mapping or Core timing is wrong must be reproduced, not assumed. | Quarantine `app_19d5877f54e436d9` and `app_c3533364bf824aad`; retain raw XML and existing IDs; add a general collision fixture and migration mapping before any reimport. See curriculum latest record and verification.json. | Reduction integration / affected case reuse |
| OQ-030 | HVL uppercase Stufe labels do not encode major quality; 5–6 can be interval motion, not inversion. DCML is case-sensitive and raw labels can also contain key/cadence markers. | Preserve raw label, explicit notation profile and semantic scope. No generic uppercasing or automatic full-label conversion. New envelope is not a parser. | Textbook/corpus label integration |
| OQ-031 | User-facing upper-staff Phrase policy differs from latent principal melody, which may lie mid-texture across hands (Appendix II). | Keep existing production policy; represent latent melody/reduction as separate hypotheses. Register transfer and implied tones must not alter observed Core events. | Melody/Pillar/reduction promotion |


### Existing minimum decisions

2026-09-27 candidate revision update: ordered-grace-ties-0.1.0 resolves the single zero-time bucket by verified source order in one lane, with all-or-abstain explicit endpoints. Candidate source-identity-revision r4 has zero unresolved tie endpoints in the12-score cohort, physical-measure coordinates and corrected source voices, stable note/rest/source-ref IDs and review-required aliases for changed groupings.2,467 annotation labels/span/point coordinates are preserved; only revision targets and alignment sound membership change. No production manifest/parser/UI migration. Gates remaining: affected harmony/NCT recalculation, visual score review, external human targets referencing changed voice/measure/sound IDs. Performed grace timing/anchors and cross-PartStaff voice identity remain deferred; see curriculum latest record.

2026-09-27 sequence/tie follow-up: full ordered measure/staff/voice replay (source-sequence-audit r2) supplies source identities for all29 previously unresolved notes and validates16,067notes/2,018rests.22 local onsets/printed labels need correction due to nonnumeric measure-label collisions, with global time/duration unchanged. The voice-tie-impact r3 shadow graph joins9 unique cross-voice explicit tie edges but conservatively blocks4 endpoints around zero-duration grace ties (MozartK281-3 m43); earlier r2 bypassed grace and must not be promoted. Identity recovery is not performed-timing resolution. New revision/aliases, physical measure indexing and grace tie ordering/anchors remain release gates. Old datasets/default parser are unchanged. See curriculum latest record and source-identity-cases archive.

2026-09-27 voice follow-up: voice-provenance-0.1.0 reproduces temporal Voice context leakage in a two-measure MusicXML fixture. All12,083 mismatching voice hints in the fixed12-score audit occur without a containing Voice in the current measure;2,786 explicit containing voices match XML. Source-verified note-level proposals are saved in `output/voice-provenance-audit-2026-09-27-r1/` without changing Core or the default parser. Migration remains blocked on identity/revision/annotation aliases, rest coverage and tie/sounding-event impact checks;29 unresolved source mappings remain abstentions. See curriculum development record for evidence and staged migration gates.

2026-09-27 OQ-029 update: the hash-order collision was reproduced and fixed in source-note-mapping-0.2.0. Existing note IDs/durations are preserved. Candidate copies pass all17 original appendix contexts;35 previously mismatched note links are corrected in12scores. Old packages/manifests remain archival; publication of a new IR revision is pending.29 unresolved notes (including repeated grace notes and earlier source-measure issues) are retained as abstentions. Logical voice hints disagree with XML in many uniquely mapped events; provenance/parent-Voice extraction needs a separate migration-safe investigation. See the latest curriculum record and `output/source-note-mapping-repair-2026-09-27-r1/report.json`.

The minimum blocking decisions are OQ-002/003/004 (identity and source mapping), OQ-009 (metric policy boundary), OQ-010 (pitch-basis API), OQ-014 (inclusion policy), and OQ-017/018 (annotation migration). Parser prototyping and schema validation can proceed before the rest are closed.
