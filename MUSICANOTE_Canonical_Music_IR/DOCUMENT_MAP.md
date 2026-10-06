# Canonical Music IR 문서 지도

## 먼저 읽을 문서

화성 분석 개발의 시작점은 별도 [개발 메인 문서](../docs/harmony/README.md)와 [개발 로그](../docs/harmony/DEVELOPMENT_LOG.md)다. 아래는 공통 계약과 기존 상세 기록의 지도다. 새 화성 개발 결과는 `docs/harmony/`에서 관리하며 인수인계 문서에 누적하지 않는다.

1. `README.md` — 문서 범위와 우선순위
2. `CANONICAL_MUSIC_IR_SPEC_v0.1.md` — 전체 계약
3. `DESIGN_PRINCIPLES.md` — 변경 불가 원칙
4. `ID_AND_TIME_COORDINATE_SPEC.md` — 공통 ID·시간축

## 주제별 정본

최신 후속: [실제 연속 음형의 조건부 화음 대조](HARMONY_CONTINUOUS_SURVEY_2026-09-29.md). 지연 끝점에 국한하지 않은 라벨 독립184개 표본, 같은 음가의 후보 대조, 전체 악보·재현·보류와 한계를 기록한다.

최신 후속: [성부 경로별 조건부 비화성음](HARMONY_PATH_ORNAMENTS_2026-09-29.md). 후보 철자/경로 가정별 경과·보조 설명, 비구성음 음가 보존, 실패 이력과 실제 검증 한계를 기록한다.

최신 후속: [연속 성부 경로 전체 조합](HARMONY_VOICE_PATHS_2026-09-29.md). 지역 대응을 연속 경로 분할로 만들고 음표1회 사용/음가 보존을 검증한다. 쉼 뒤 지연 해결과 구별한다.

최신 후속: [제한적 문맥 확대와 성부 복수 대응](HARMONY_PATH_CONTEXT_2026-09-29.md). 관찰 범위와 화음 범위를 구별하고, 지역 부분 대응/무연결을 저장한다. 기존 결과와 전체 악보 대조도 포함한다.

최신 후속: [공통 후보와 지연 경로의 조건부 설명](HARMONY_CATALOG_PATHS_2026-09-29.md). 중간 음 생략 없이 유지/도착/새 화음 대안을 구별하고 실제 문맥·성부 보류를 기록한다.

후속 화성 기록: [미세 시간축·분산 도착 감사](HARMONY_CATALOG_MICROTIME_2026-09-29.md). 실제 음 시작/종료 좌표에서의 후보 대조와 지연 연결의 불확실성을 다룬다.

최신 화성 구현 기록은 [공통 후보의 해결 관계 연결](HARMONY_CATALOG_RESOLUTION_2026-09-29.md)이다. 전체 악보 화면, 실험/운영 구분, 후보 수와 정확도의 차이 및 다음 작업을 함께 기록한다.

화성의 실제 악보 비교는 [최근 5사례 화면](../output/harmony-visual-review-2026-09-27-r7/index.html)에서 시작한다. 관련 개발 기록 (상세 기록은 공개 브랜치에서 제외)에 원자료/자동 환산 표기의 차이와 재현 명령을 남겼다.

화성·구조 분석과 작곡·편곡을 개발할 때는 [통합 실행 계획](HARMONY_COMPOSITION_HARNESS_IMPLEMENTATION_PLAN.md)을 먼저 읽는다. §2는 음악 용어, §6–8은 IR·주석·정렬, §9–10은 분석, §11–12는 스타일·생성, §14는 평가, §16은 단계별 작업 카드다. 이 계획은 기존 Core 규격을 바꾸지 않으며 새 계약은 제안 상태로 구별한다.

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
| 화성·구조·작곡·편곡 실행 순서 | [통합 실행 계획](HARMONY_COMPOSITION_HARNESS_IMPLEMENTATION_PLAN.md) |
| 음악적 역할·반주·배치·전개 및 과거 사례 보충 | [화성 개발의 의미 데이터·생성 로드맵](../docs/harmony/MUSICAL_SEMANTICS_AND_GENERATION_ROADMAP.md) |
| 코퍼스 조사 근거 | [로컬 자료 조사](CLASSICAL_HARMONY_CORPORA_AUDIT_2026-09-24.md) |
| 전체 파일 등록·DCML 정렬 확대의 현재 상태 | [등록·정렬 개발 기록](ALL_CORPORA_REGISTRY_AND_ALIGNMENT_2026-09-24.md) |
| 반복 엔딩 시간축·수입 품질 관문 | [반복 엔딩 정렬 검증](DCML_REPEAT_TIMELINE_ALIGNMENT_2026-09-24.md) |
| DCML 화성 주석 654쌍 표·악보 구조 전수 검사 | [빠른 전수 검사 기록](DCML_FAST_ANNOTATION_AUDIT_2026-09-24.md) |
| DCML MusicXML 392쌍 음표·마디·주석 정밀 정렬 | [전곡 정렬 결과](DCML_FULL_ANNOTATION_ALIGNMENT_2026-09-24.md) |
| RomanText·ChoCo JAMS 출처·형식 검사 | [주석 출처 검사](ROMANTEXT_CHOCO_ANNOTATION_SOURCE_AUDIT_2026-09-24.md) |
| RomanText와 sibling 악보의 마디·박자 좌표 연결 | [RomanText 정렬 파일럿](ROMANTEXT_SCORE_ALIGNMENT_PILOT_2026-09-24.md) |
| RomanText를 외부 주석으로 수입하고 악보에서 검토 | [RomanText 수입·검토 화면](ROMANTEXT_IMPORT_AND_REVIEW_2026-09-25.md) |
| RomanText 화성과 악보 구성음·베이스 증거 비교 | [RomanText source evidence](ROMANTEXT_SOURCE_EVIDENCE_2026-09-25.md) |
| 증6화음 실제 주석·생성 데이터 적합성 | [기초 조사](COMPOSITION_ARRANGEMENT_HARMONY_DATA_PLAN_2026-09-24.md) |
| 화성 사례 train/dev/holdout·작품군 누수 방지 | [Harmony Data Release](HARMONY_DATA_RELEASE_2026-09-25.md) |
| Local key·성부진행 retrieval 개선 평가 | [Harmony Retrieval Feature Ablation](HARMONY_RETRIEVAL_FEATURE_ABLATION_2026-09-25.md) |
| 전후 마디·진행·분산 형태별 사례와 유형 판단 | [Harmony Episode Model](HARMONY_EPISODE_MODEL_2026-09-26.md) |
| 분산화음 구간·비화성음 공동 판정 실험 | [Joint Harmony/NCT Pilot](JOINT_HARMONY_NCT_PILOT_2026-09-26.md) |
| 교과서 33개 단원·주석 사례·판단 규칙 연결 | 교과서–사례 실행 계획 (상세 기록은 공개 브랜치에서 제외) |
| 3화음·7화음·짧은 변화·NCT 검토 후보군 현재 상태 | 교과서–사례 실행 계획의 최신 개발 기록 (상세 기록은 공개 브랜치에서 제외) — 정답 승인 전 검토 대기열 |
| 절대 시간·지속음·전후 문맥을 보존한 화성 비교 | 교과서–사례 실행 계획의 최신 개발 기록 (상세 기록은 공개 브랜치에서 제외) — 2026-09-27, target-only 진단·화면 미적용 |
| 문맥 길이 민감도·실제 음표/주석 대조 | 교과서–사례 실행 계획의 최신 개발 기록 (상세 기록은 공개 브랜치에서 제외) — 5개 train 사례, 30회 계산·정답률 아님 |
| 화음 후보 비용·병합 원인·E# 등 철자 근거 | 교과서–사례 실행 계획의 최신 개발 기록 (상세 기록은 공개 브랜치에서 제외) — 동일 목적함수 재채점·진단 전용 |
| 신규30사례 층화 비교·현재 적용 판단 | 교과서–사례 실행 계획의 최신 개발 기록 (상세 기록은 공개 브랜치에서 제외) — 120회 계산, 문맥 민감성 잔존으로 화면 적용 보류 |
| 분산·생략7화음·장식음 경계의 실패 근거 | 교과서–사례 실행 계획의 최신 개발 기록 (상세 기록은 공개 브랜치에서 제외) — 우선5사례, 라벨 안정과 경계 안정 분리 |
| 유사 화성 사례 악보 비교·append-only 피드백 | [Harmony Case Review UI](HARMONY_CASE_REVIEW_UI_2026-09-25.md) |

## 규격과 구현 기록의 경계

이 디렉터리는 장기 유지할 논리 계약의 정본이며 화성 Harness의 코퍼스 수입·평가 파일럿 기록도 링크한다. 구조 분석 UI의 날짜별 코드 변경과 평가는 MusicStructureAnalyzer의 `docs/README.md`와 `docs/development-log.md`에서 관리한다. 구현 문서가 논리 계약과 충돌하면 계약을 우선하고 충돌을 `OPEN_QUESTIONS.md`에 기록한다.

`KYSING_*` 문서는 규칙의 근거가 되는 연구 결과이지 Core schema의 일부가 아니다. `CORE_LOGIC_SELF_CHECK_QUIZ_*`는 사용자 합의 확인 자료이며 규범 문서가 아니다.
# Harmony case retrieval

- [Harmony Case Retrieval Pilot — 2026-09-25](HARMONY_CASE_RETRIEVAL_PILOT_2026-09-25.md): 다른 작품의 source-linked harmony 사례·반례 검색, feature 계약, 실제 DCML 파일럿과 제한.
- [Harmony Data Release — 2026-09-25](HARMONY_DATA_RELEASE_2026-09-25.md): work-family/lineage manifest, 6,492개 사례 release, split 누수 검증.
- [Harmony Retrieval Feature Ablation — 2026-09-25](HARMONY_RETRIEVAL_FEATURE_ABLATION_2026-09-25.md): blind local-key·경계 성부진행 feature와 dev 982-case 비교.
- [Harmony Case Review UI — 2026-09-25](HARMONY_CASE_REVIEW_UI_2026-09-25.md): 현재 구간과 다른 작품의 후보 악보 비교, train-only 검색, append-only 평가.
