# Canonical Music IR 문서 지도

## 먼저 읽을 문서

1. `README.md` — 문서 범위와 우선순위
2. `CANONICAL_MUSIC_IR_SPEC_v0.1.md` — 전체 계약
3. `DESIGN_PRINCIPLES.md` — 변경 불가 원칙
4. `ID_AND_TIME_COORDINATE_SPEC.md` — 공통 ID·시간축

## 주제별 정본

| 주제 | 정본 문서 |
|---|---|
| Entity와 Core 필드 | `ENTITY_REFERENCE.md` |
| Analysis/Evidence 연결 | `ANALYSIS_INTERFACE_SPEC.md` |
| Human Annotation | `ANNOTATION_EXTENSION_SPEC.md` |
| Phrase 경계 evidence | `PHRASE_BOUNDARY_EVIDENCE_SPEC.md` |
| 경계 화성·Cadence | `BOUNDARY_HARMONY_CADENCE_SPEC_v0.1.md` |
| Phrase/Motif 계층 | `MOTIF_PHRASE_LAYERING_SPEC_v0.1.md` |
| Motif 변형·범위·가족 | `MOTIF_VARIATION_AND_EXTENT_SPEC_v0.1.md` |
| 검토 화면 | `PHRASE_REVIEW_VIEWER_CONTRACT_v0.1.md` |
| 검증·이전 | `VALIDATION_RULES.md`, `VERSIONING_AND_MIGRATION.md` |
| 미확정 문제 | `OPEN_QUESTIONS.md` |

## 규격과 구현 기록의 경계

이 디렉터리는 장기 유지할 논리 계약의 정본이다. 날짜별 코드 변경, UI 구현 세부, 평가 결과는 MusicStructureAnalyzer의 `docs/README.md`와 `docs/development-log.md`에서 관리한다. 구현 문서가 이 정본과 충돌하면 정본을 우선하고 충돌을 `OPEN_QUESTIONS.md`에 기록한다.

`KYSING_*` 문서는 규칙의 근거가 되는 연구 결과이지 Core schema의 일부가 아니다. `CORE_LOGIC_SELF_CHECK_QUIZ_*`는 사용자 합의 확인 자료이며 규범 문서가 아니다.
