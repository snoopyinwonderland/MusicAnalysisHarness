# MUSICANOTE Canonical Music IR v0.1

이 디렉터리는 MUSICANOTE의 MusicXML 기반 분석·검색·편곡 시스템이 공유하는 내부 음악 데이터 계약의 첫 정식 규격이다.

Canonical Music IR은 MusicXML을 단순히 JSON으로 옮긴 결과가 아니다. 서로 다른 작성 프로그램과 XML 구조를 정규화하면서도 원본으로 역추적할 수 있고, 관찰 가능한 사실과 해석적 분석을 분리하며, 모든 분석기가 동일한 ID와 시간축을 사용하게 하는 장기 안정 표현이다.

## 문서 우선순위

1. `CANONICAL_MUSIC_IR_SPEC_v0.1.md`
2. `ID_AND_TIME_COORDINATE_SPEC.md`, `ENTITY_REFERENCE.md`
3. JSON Schema
4. 나머지 인터페이스·운영 문서
5. 현재 prototype 구현

문서 사이 충돌은 `OPEN_QUESTIONS.md`에 기록한다. Production migration은 이 규격의 범위 밖이다.

## 네 층

```text
Layer A  Source Reference
Layer B  Canonical Core
Layer C  Deterministic Derived Evidence
Layer D  External Analysis / Annotation Interface
```

## 파일

- `DESIGN_PRINCIPLES.md`: 변경되지 않아야 할 설계 철학
- `ENTITY_REFERENCE.md`: Core entity와 필드 계약
- `ID_AND_TIME_COORDINATE_SPEC.md`: 안정 ID, rational time, span 규칙
- `ANALYSIS_INTERFACE_SPEC.md`: 분석·evidence 연결 계약
- `ANNOTATION_EXTENSION_SPEC.md`: 사람 검수와 교정 데이터
- `PHRASE_BOUNDARY_EVIDENCE_SPEC.md`: 프레이즈 분할 이전의 결정론적 증거 계약
- `PHRASE_REVIEW_VIEWER_CONTRACT_v0.1.md`: MusicSearch 공유 악보 레이어와 검수 저장 계약
- `BOUNDARY_HARMONY_CADENCE_SPEC_v0.1.md`: 프레이즈 경계 주변의 제한적 화성 진행·Cadence 가설 계약
- `MOTIF_PHRASE_LAYERING_SPEC_v0.1.md`: Motif occurrence/group과 Phrase span을 분리하는 계층 계약
- `MOTIF_VARIATION_AND_EXTENT_SPEC_v0.1.md`: beam, 변형 정렬, core/complete extent, 반복음·짧은 음형, 가족 판정과 검색 식별력 분리 규칙
- `CORE_LOGIC_SELF_CHECK_QUIZ_v0.1_KO.md`: Canonical IR과 Phrase 분석 핵심 논리의 사용자 합의 점검 문제
- `CORE_LOGIC_SELF_CHECK_QUIZ_v0.1_ANSWER_KEY_KO.md`: 객관식 해설과 주관식 검토 기준(퀴즈를 푼 뒤 확인)
- `VERSIONING_AND_MIGRATION.md`: SemVer와 migration 정책
- `VALIDATION_RULES.md`: hard/soft validator와 regression 규칙
- `OPEN_QUESTIONS.md`: 구현 전에 결정할 충돌·미확정 사항
- `schemas/`: 논리 계약을 검증하는 JSON Schema
- `examples/`: 해석을 Core에 섞지 않은 작은 fixture

## 현재 구현과의 관계

`src/musicanote_harness/canonical.py`는 v0.2 prototype이다. 이 문서의 v0.1.0은 첫 정식 계약 버전이며 숫자가 더 작아도 prototype의 downgrade를 뜻하지 않는다. 구현이 규격을 충족하면 별도 migration과 함께 정식 schema version으로 전환한다.
