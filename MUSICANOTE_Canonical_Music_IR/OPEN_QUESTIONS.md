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

The minimum blocking decisions are OQ-002/003/004 (identity and source mapping), OQ-009 (metric policy boundary), OQ-010 (pitch-basis API), OQ-014 (inclusion policy), and OQ-017/018 (annotation migration). Parser prototyping and schema validation can proceed before the rest are closed.

