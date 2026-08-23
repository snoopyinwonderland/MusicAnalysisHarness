# MUSICANOTE Canonical Music IR Specification v0.1

## 1. Status

- Schema name: `musicanote-canonical-music-ir`
- Schema version: `0.1.0`
- Status: Draft for implementation review
- Scope: logical contract, prototype validation, fixture definition
- Out of scope: production migration, model training, final harmony/phrase inference

## 2. Purpose

Canonical Music IR은 MusicXML source의 프로그램별 차이를 흡수하고 모든 downstream module이 같은 score identity, event identity, rational timeline과 source lineage를 공유하게 한다. 사람 annotation과 특정 LLM 없이 완전히 생성 가능해야 한다.

## 3. Layer model

### Layer A — Source Reference

원본 파일과 XML 요소로 역추적하는 정보다. `source_file_id`, SHA-256, MusicXML version, part/measure/voice/staff, element ordinal, XPath 또는 동등한 locator를 포함한다. Core event의 `source_ref_id`는 반드시 이 layer의 record를 참조한다.

### Layer B — Canonical Core

Score, Part, Staff, Voice, Measure, NotatedNoteEvent, RestEvent, TieChain, SoundingEvent, AttackEvent, ChordOnsetGroup 및 score directions를 포함한다. Roman numeral, harmonic function, NCT, phrase, motif, cadence, local key, modulation, melody, climax, copyright risk는 금지한다.

### Layer C — Deterministic Derived Evidence

Core에서 동일 algorithm version과 config로 재계산할 수 있는 feature다. pitch class, metric strength, simultaneous pitch classes, register, density, lowest/top sounding pitch, interval, contour 등이 여기에 속한다. `HarmonicAtom`/vertical slice는 v0.1에서 derived cache로 권고하며 Core truth가 아니다.

### Layer D — External Analysis / Annotation Interface

AnalysisRecord, EvidenceRecord, AnnotationRecord, AnalysisState, CaseRecord가 Core ID 또는 SpanReference를 참조한다. 분석 모델은 교체 가능하고 Core는 유지된다.

## 4. Root document

Root는 다음 collection을 갖는다.

```text
schema_name, schema_version, ir_document_id
source_files, source_references
score, parts, staves, voices, measures
note_events, rest_events
tie_chains, sounding_events, attack_events
chord_onset_groups
directions
derived_evidence_cache (optional)
extensions (optional, registered only)
parser_manifest
validation_summary
```

Collection은 ID로 연결한다. 객체 안에 거대한 하위 객체를 중첩 복제하지 않는다.

## 5. Observation/interpretation boundary

허용:

```json
{"key_signature":{"fifths":0},"lowest_sounding_pitch":{"midi":48}}
```

금지:

```json
{"key":"C_major","chord":"V7/V","nct_type":"passing_tone","is_melody":true}
```

첫 예에서 조표와 최저 발음음은 재계산 가능하다. 두 번째 예는 음악적 해석이다.

## 6. Time contract

- canonical unit: quarter-note rational
- representation: `{numerator, denominator}`; denominator는 양수
- span semantics: `[start, end)`
- global time은 notated score timeline을 기본으로 한다.
- printed measure number와 sequential measure index를 분리한다.
- UI는 measure ID + beat rational을 표시하지만 저장된 span의 권위 좌표는 global quarter다.
- repeat-expanded playback timeline은 별도 mapping extension이며 notated timeline을 덮어쓰지 않는다.

## 7. Identity contract

ID는 의미 있는 prefix와 opaque deterministic token을 사용한다. annotation은 배열 index나 filename만 참조하지 않는다. 상세 규칙은 `ID_AND_TIME_COORDINATE_SPEC.md`를 따른다.

## 8. Pitch contract

Pitch는 written spelling을 보존한다: step, alter rational, octave, MIDI(가능한 경우), pitch class. F-sharp와 G-flat은 같은 MIDI여도 다른 spelling이다. Written pitch와 concert pitch는 별도 객체로 저장하며 parser가 임의로 한쪽을 폐기하지 않는다.

## 9. Duration contract

- `notated_duration`: 개별 기보 조각
- `tie_accumulated_duration`: tie chain 합계
- `sounding_duration`: attack부터 release까지
- `performed_duration`: v0.1 deferred extension

Tuplet은 표시 ratio와 rational duration을 모두 보존한다.

## 10. Voice/staff normalization

- Part는 악기/논리 파트, Staff는 시각적 보표, Voice는 시간 진행 lane이다.
- Voice identity는 staff identity와 독립적이어야 하며 cross-staff note는 logical voice와 display staff를 모두 참조한다.
- MusicXML `backup`/`forward`는 event가 아니라 source timeline instruction으로 소비하고, 정규화 후 voice onset 검증 근거로 남긴다.
- `<chord>` member는 같은 onset group을 공유하지만 개별 NoteEvent ID를 갖는다.
- cue, ossia, hidden rest, grace는 삭제하지 않고 flags/purpose로 보존한다.
- 한 part에 여러 instrument가 있으면 instrument timeline 또는 extension을 사용한다.

## 11. Grace notes

v0.1은 `is_grace`, `grace_order`, `anchor_note_id`, `slash`, source timing fields를 저장한다. canonical notated duration이 0이어도 ordering은 보존한다. performed time allocation은 extension이다.

## 12. Chord onset and simultaneity

`ChordOnsetGroup`은 MusicXML `<chord>` 또는 동일 notated onset group을 표현한다. `VerticalSlice`는 active sounding events의 derived view다. 어느 것도 분석적 harmony label을 포함하지 않는다.

## 13. Generic SpanReference

모든 analysis/annotation range는 global rational `[start,end)`를 권위 좌표로 쓰고 display locator를 함께 제공할 수 있다. Span은 중첩·교차 가능하며 tree 강제는 없다. Motif occurrence와 phrase, harmony span은 서로 독립 record다.

## 14. External interfaces

Analysis는 복수 hypothesis, confidence, evidence, selected index, status, engine version을 저장한다. Human annotation은 AI suggestion과 분리된다. Runtime working memory와 case library는 IR 문서 밖에 둔다.

## 15. Extension registry

`extensions`의 각 entry는 `name`, `version`, `owner`, `schema_uri`, `payload`를 요구한다. namespace는 reverse-domain 또는 `musicanote.<module>` 형식이다. Core field를 shadow하거나 동일 의미를 다른 단위로 재정의할 수 없다.

## 16. Storage profiles

- interchange/debug: JSON
- append-only analysis/annotation: JSONL
- large event/evidence tables: Parquet
- operation: PostgreSQL relational keys + JSONB payload
- low-latency binary transport: future protobuf/msgpack profile

논리 schema와 물리 storage는 분리한다. 어떤 format도 Core 의미를 변경할 수 없다.

## 17. v0.1 scope

필수: score metadata, part/staff/voice/measure, rational grid, note/rest, pitch spelling, global onset, tie chain, sounding/attack event, chord onset group, source reference, stable ID, SpanReference, schema/parser version.

선택: articulation, dynamic, slur, tuplet, grace, lyrics, repeat/barline. 선택 필드는 없으면 `null` 또는 빈 collection이며 추론값으로 채우지 않는다.

Deferred: performed timing, audio alignment, OMR confidence, pedal realization, fingering, microtonal MIDI mapping, expressive timing, inferred articulation.

## 18. Conformance

Conforming producer는 JSON Schema, hard validation, fixture regression, source traceability를 통과하고 parser manifest를 남겨야 한다. Conforming consumer는 unknown optional field와 registered extension을 무시할 수 있어야 하며 Core field 의미를 재해석하지 않아야 한다.

