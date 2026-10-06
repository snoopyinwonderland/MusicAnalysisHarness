# MUSICANOTE MusicSearch 문서 지도

- 구조 비교층 최신 통합: [Phrase 2층 개발 기록](phrase-layer-integration.md), [Motif 가족 연결 개발 기록](motif-family-integration.md) — 기본 OFF, 기존 경계·피드백 ID 보존

- 현재 반복 분석 개발: [리듬형 우선·경계 독립 반복/변형 분석](REPEAT_FIRST_ANALYSIS_PLAN.md) — 상세 단계와 첫 shadow 구현
- 이전 구조 분석 계획: [반복 Phrase 구조 기반 경계 보정](REPEATED_PHRASE_STRUCTURE_PLAN.md) — baseline 비교 registry 구현, 운영 보정 미적용

- Phrase 최신 보완: [긴 종결음·쉼과 반복 일관성 v1.14](phrase-sustained-closure-v1.14.md)

- Phrase 최신 수정: [반복과 긴 쉼 분리 v1.13](phrase-long-rest-v1.13.md)

- Phrase 최신 보정: [기준박 대비 종결 v1.12](phrase-relative-closure-v1.12.md)

- Phrase 최신 수정: [짧은 내부 쉼과 지속 종결 v1.11](phrase-articulation-v1.11.md)

- 구조 분석 최신 변경: [Phrase 기반 Motif v1](phrase-first-motif-v1.md)

이 파일이 인수인계의 단일 진입점이다. 물리적 파일 이동 대신 역할별 색인을 사용해 기존 링크와 사례 ID를 보존한다.

## 처음 읽는 순서

1. [현재 구현 상태](SYSTEM_STATUS.md) — 무엇이 동작하고 무엇이 미완성인가
2. [설치·데이터·재현](REPRODUCIBILITY.md) — 환경, 별도 데이터, 실행과 검증
3. [제품 요구사항](MUSICANOTE_Creator_Preclearance_Development_Spec_KO.md) — 목표이며 전부 구현됐다는 뜻은 아님
4. [사례 지식베이스](evaluation-case-knowledge-base.md) — Query, 설명, 악보 구간의 보존

## 현재 구현과 코드 연결

- [악기 샘플 음원 통합](sampled-playback-integration.md) — 네 악기 음색·사전 로딩·기본 소리 fallback, 기존 타이/seek/재생 위치 계약과 검증

- [작업별 에이전트·모델 라우팅](agent-model-routing.md) — Terra 회귀 테스트, Sol 규칙 변경, Luna 일일 수집의 역할·handoff 계약

- [소규모 회귀 3종 v1](small-regression-triad-v1.md) — Exact·리듬, 시작 위치, 오탐 대조군의 6개 실제 corpus Query

- [EVAL-002 긴 음 도착·점유 정렬](eval-002-held-arrival-alignment.md) — coverage 우선 제한 재평가와 낮은 coverage lookback

- [EVAL-003 반복 attack 분할·병합](eval-003-repeat-attack-semantics.md) — 점수 변경 없이 gap 의미와 설명을 보존

- [EVAL-004 반복 위치 결과 표현](eval-004-repeated-occurrence-reporting.md) — 작품 회수·대표 악보 조각·전체 등장 마디를 분리

- [EVAL-005 국소 옥타브 표시 정렬](eval-005-local-octave-alignment.md) — 점수 강화 없이 옥타브 음·실제 누락의 강조 관계를 분리

- [2/4 소규모 15회 검증](duple-meter-15-v1.md) — 단순 패턴 제외 및 누적 개선 반영 순서

- [Query 선별·박자 테스트 정책](query-selection-and-meter-test-policy.md) — 단순 음계 제외, 2/4 소규모 회귀, 불규칙 박자 grouping 제한

- [단순 패턴 리듬 우선 배점](pattern-rhythm-ranking.md) — 순차·동음반복 전용 70% 리듬, A/B와 후보 누락 제한

- [Query 복사·붙여넣기](query-copy-paste.md) — 테스트 악보에서 JSON/간단 표기 복사, 검색 화면 입력·Undo

- [순차진행·동음반복 검색 옵션](simple-pattern-search-options.md) — 상세 검색 허용 정책 및 미반영 개선 항목 현황

- [6/8·3/8 삭제 검증](eighth-meter-60-v1.md) — 박자별 새 원곡 5개, 두 삭제 시간 조건 비교

- [3/4 장식음 삭제 60회 평가](triple-meter-60-v1.md) — 새 원곡 10개, 시간 축소와 뒤 음 박자 위치 유지 비교

- [짧은 Query 90회 평가](short-query-90-v1.md) — 새 원형 10곡의 12/8/6음·음높이 변경·장식음 삭제

- [옥타브·장식음 복합 평가](octave-combination-20-v1.md) — 30회 완료, 원곡 상위권 회수와 변경 음 대응을 구별
- [검색 평가 개선안 통합 보류 목록](search-evaluation-improvement-backlog.md) — 평가 종료 후 일괄 검토, 현재 운영 반영 안 함

- [기억 입력 변형 50개 순차 평가](memory-variation-50-v1.md) — 5종 변형·대조군·독립 사례 묶음과 XML 문맥

- [Query 보완 추천 기획·구현](query-completion-plan.md) — 단일 음 추가/음높이/옥타브 제안, 적용·Undo, 검토 사례 JSON

- [장식음 두 개 삭제 실험](double-ornament-trial-v1.md) — 원형/한 음/두 음 삭제 실제 검색과 악보 비교
- [장식음 두 개 삭제 추가 실험](double-ornament-additional-v3.md) — 기존과 겹치지 않는 10개 구간, 30회 대조 검색

- [클래식 레퍼토리 수집 프로젝트 인수인계](../handoff/classical-repertoire-collection-2026-09-16/README.md) — 이 업무는 별도 프로젝트로 분리

- [한 음 삭제 개선 및 검증](structural-next40.md) — 기본 적용, 40개 삭제 검증, 롤백 설정
- [표시 점수 배점 실험](visible-ranking-v1.md) — 회귀로 기본 비활성
- [비교 악보 오선·음원 수정](omission-review-display-fix.md)

- [구조 변형 검색 2단계: XML 연결·20개 실제 자료 감사](structural-reduction-stage2-audit.md) — 200음 좌표 연결, 화성 정보 부재·보류 기록, 악보 미리보기 요구사항

- [구조 변형 검색 1단계: 독립 국소 축약 모듈](structural-reduction-stage1.md) — 타이/박자 계약, 관계 근거·반례 테스트; production 검색 미적용

- [실제 음악 5쌍: 검사 방향·자료 근거·검증 DB 계획](copyright-real-five-pairs.md)

- [다구간 변형 XML 24개 제작·검증·한계](copyright-multisegment-fixtures-v1.md) — 합성 원곡 4개, 실제 검색 전

- [검색 평가 재검토·다구간 차용 XML·저작권 검토 리포트 계획](copyright-multisegment-validation-plan.md) — 설계 제안, 미구현

- [성능 7단계: 후보 경계 캐시, 반복 검색 개선과 최초 비용](performance-stage-7.md)

- [S-STRUCT-004: 부분 Motif와 호흡 기호](structure-review-004.md)

| 영역 | 시작 문서 |
|---|---|
| 검색 설계·기존 한계 | [검색 감사](search-lab-audit.md), [아키텍처 결정](adr-001-search-architecture.md) |
| 성능 개선 기록 | performance-stage-1.md ~ performance-stage-5.md, [6단계 SQL 집계 A/B·기본 적용 보류](performance-stage-6.md) |
| Phrase/Motif 분석 | [최신 v1.9 오버레이](motif-phrase-structure-overlay-v1.9.md), [유사도 계약](motif-similarity-v0.2.md) |
| 구조 기반 사전검토 | [어댑터 감사](creator-preclearance-audit.md), [선별·검색](creator-preclearance-search-stage.md) |
| 사전검토 1단계 | [검색 worker·재개·캐시](preclearance-stage1-performance.md) |
| 사전검토 2단계 | [작품·판본 관계](preclearance-stage2-work-identities.md) |
| 사전검토 3단계 | [후보 중요도·보고서 계약](preclearance-stage3-importance.md) |
| 사전검토 4단계 | [실험용 검토 우선순위와 한계](preclearance-stage4-priority.md) |
| 사전검토 5단계 | [코퍼스 source 빈도 A/B](preclearance-stage5-frequency.md) |
| 사전검토 6단계 | [유형별 검토 Harness와 문맥](preclearance-stage6-review-harness.md) |
| 사전검토 7단계 | [검색 지연 계측과 cache 진단](preclearance-stage7-search-tracing.md) |
| 사전검토 8단계 | [박자 캐시 checkpoint와 실제 중단 검증](preclearance-stage8-cache-checkpoint.md) |
| 보고서 초안 | [Copyright Infringement Report 구현·재현·한계](copyright-infringement-report-v1.md) |
| 다음 비교 계획 | [Phrase-only/Motif A/B·복수 구간 집계·사이트 통합](preclearance-phrase-motif-ab-plan.md) |
| 다층 근거 구현 v2 | [Phrase/Motif·골격·Contour·리듬형·음형·원곡 제외](preclearance-musical-evidence-v2.md) |
| 실제 A/B 결과 | [Phrase 7개 vs Phrase 7개 + Motif 1개](preclearance-phrase-motif-ab-2026-09-16.md) |
| 개발 후 50개 평가 | [유형별 회수·문제·개선 후보·전체 사례 링크](preclearance-variation50-2026-09-16.md) |
| 검토 UI | [Phrase 검토 화면](phrase-review-viewer.md) |
| 주요 Motif 가족 목록 | [공통 집계와 비중 정의](motif-family-summary.md) |
| 운영 수집 | [KY 기록](ky-collection-log.md), [YouTube 기록](youtube-collection-log.md) |

## 평가와 증거

- [구조 변형 후속 40개: 단일 삭제·추가 치환](structural-next40.md) — baseline 진행 상태, 후보 탈락 진단, 미적용 보완 모듈

- [구조 변형 100개 악보 미리보기](structural-100-preview.md) — 원본/변형 200개 렌더링, 검토용 초안; 검색 미실행

- [기둥음 보존·장식 변형 검색 일반 규칙과 Schenker 연구 검토](structural-melody-search-rules-v1.md) — 설계, 구현/검증 전; 반례·데이터 계약·100개 테스트 계획 포함

- [실곡 후보 탈락 진단·Contour 실험·Phrase 외 구간 검색](real-pair-search-diagnostics-and-segments.md)

- [Twinkle–Ma Boy 회수 및 분산 유사성 개선 실행 계획](twinkle-distributed-similarity-plan.md)

- [실제 사례 기존 DB 검사와 Twinkle 분산 유사성 검토](copyright-real-existing-db-report-v1.md)

- `evaluation/runs/`: 실행 JSON, task checkpoint, 스냅샷. 최신 파일이라는 이유만으로 전문가 확정으로 취급하지 않는다.
- `evaluation/case-assets/`: 재현용 이벤트와 악보 맥락.
- `motif-100/200/300/350-...md`, `query-100-evaluation-report.md`: 당시 Query와 순위/문제 기록. 현재 모두 해결됐다는 의미가 아니다.
- [사전검토 실제 검색 평가](creator-preclearance-search-evaluation-2026-09-14.md): Stage 3의 입력 보고서로 이어지는 실행.
- [유형별 Query 파일럿](preclearance-review-pilot-2026-09-15.md): 12개 생성, 4개 실행, 3개 timeout 및 8개 미실행을 구분한 검토 자료.
- [개발 로그](development-log.md): 날짜순 변경 추적. 기존 일부 항목은 파일 끝에 추가되어 있으므로 날짜로 찾는다.

## 계획과 역사 문서

`*-plan.md`, `*-proposals-*.md`, `CODEX_PROMPT_*.md`는 제안/작업 입력이다. v1.4~v1.8 및 예전 stage 문서는 당시 계약과 회귀 이유를 남긴 역사 자료다. 현재 구현 상태 문서보다 우선하지 않는다.

Canonical IR 정본은 별도 MusicAnalysisHarness 저장소의 `MUSICANOTE_Canonical_Music_IR/README.md`이다. 외부 프로젝트 전체가 이 저장소에 포함됐다고 가정하지 않는다. 현재 사전검토는 로컬 구조 어댑터를 사용한다.

## 유지 규칙

변경마다 현재 구현 설명, 테스트/실행 증거, 개발 로그를 함께 갱신한다. 새 큰 문서는 이 지도에 연결한다. 실행 결과는 새 경로로 보존하고 코드/입력/분석 버전을 기록한다. 제품 규격과 실구현이 다르면 SYSTEM_STATUS에 명시한다. 키·개인 업로드·재배포 금지 악보는 문서/Git에 복사하지 않는다.
