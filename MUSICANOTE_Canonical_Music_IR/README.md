# MUSICANOTE Canonical Music IR v0.1

이 디렉터리는 MUSICANOTE의 MusicXML 기반 분석·검색·편곡 시스템이 공유하는 내부 음악 데이터 계약의 첫 정식 규격이다.

Canonical Music IR은 MusicXML을 단순히 JSON으로 옮긴 결과가 아니다. 서로 다른 작성 프로그램과 XML 구조를 정규화하면서도 원본으로 역추적할 수 있고, 관찰 가능한 사실과 해석적 분석을 분리하며, 모든 분석기가 동일한 ID와 시간축을 사용하게 하는 장기 안정 표현이다.

## 화성·구조 분석과 작곡·편곡의 다음 개발

화면으로 확인: [화성 실험 5사례 악보 비교](../output/harmony-visual-review-2026-09-27-r7/index.html). 원자료·기존 계산·실험 계산을 악보 위 구간과 로마자로 비교한다. 로컬 서버 실행 중에는 [사례 목록](http://127.0.0.1:8767/)으로 열 수 있다.

**화성 개발을 이어받을 때는 [화성 개발 인수인계](HARMONY_DEVELOPER_HANDOFF.md)부터 읽는다.** 현재 적용 상태, 코드·사례 위치, 재현 명령, 기록 양식과 데이터 전달 주의사항을 한곳에 정리했다. 날짜별 상세 변경은 화성 개발 기록 (상세 기록은 공개 브랜치에서 제외)에 이어 쓴다.

개발자에게 전달할 실행 계획은 [화성·구조 분석 및 작곡·편곡 Harness 실행 계획](HARMONY_COMPOSITION_HARNESS_IMPLEMENTATION_PLAN.md) 한 문서에서 시작한다. 현재 코드의 제한, 코퍼스와 IR·주석의 연결, 알고리즘, 스타일 데이터, P0–P13 작업 카드와 검증 기준을 담고 있다. 구현과 검증은 [전체 코퍼스 등록·정렬 확대](ALL_CORPORA_REGISTRY_AND_ALIGNMENT_2026-09-24.md), [654쌍 주석 전수 검사](DCML_FAST_ANNOTATION_AUDIT_2026-09-24.md), [392쌍 정밀 정렬](DCML_FULL_ANNOTATION_ALIGNMENT_2026-09-24.md), [RomanText·ChoCo 출처 검사](ROMANTEXT_CHOCO_ANNOTATION_SOURCE_AUDIT_2026-09-24.md), [RomanText 2,029쌍 좌표 정렬](ROMANTEXT_SCORE_ALIGNMENT_PILOT_2026-09-24.md), [RomanText 수입·악보 검토](ROMANTEXT_IMPORT_AND_REVIEW_2026-09-25.md), [RomanText 악보 호환 증거](ROMANTEXT_SOURCE_EVIDENCE_2026-09-25.md), [반복 엔딩 정렬](DCML_REPEAT_TIMELINE_ALIGNMENT_2026-09-24.md), [DCML 수입](DCML_HARMONY_IMPORT_PILOT_2026-09-24.md), [독립 한 박 표면 화음](BLIND_SURFACE_HARMONY_PILOT_2026-09-24.md), [펼친 구간 화성](UNFOLDED_HARMONY_PILOT_2026-09-24.md) 개발 기록을 확인한다. 코퍼스 전체 파일을 등록했지만 모든 형식의 주석 수입이나 학습은 아직 완료되지 않았다. 후자의 두 분석기는 기능화성·NCT·종지·조성 판정이나 작곡 엔진이 아니며, 구조 분석에 아직 공급하지 않는다.

근거 자료는 [코퍼스 조사](CLASSICAL_HARMONY_CORPORA_AUDIT_2026-09-24.md)와 [증6화음·작곡·편곡 데이터 조사](COMPOSITION_ARRANGEMENT_HARMONY_DATA_PLAN_2026-09-24.md)다. 실행 계획은 아래 Core 계약을 대체하지 않는다.

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

- `DOCUMENT_MAP.md`: 처음 읽을 문서, 주제별 정본, 구현 기록의 위치를 구분한 문서 지도
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

구조 분석 UI의 날짜별 구현 변경과 평가는 MusicStructureAnalyzer 저장소의 `docs/README.md`에서 찾는다. 이 폴더에는 Canonical IR과 화성 Harness의 장기 계약 및 관련 코퍼스 수입·평가 파일럿 기록을 유지한다.
