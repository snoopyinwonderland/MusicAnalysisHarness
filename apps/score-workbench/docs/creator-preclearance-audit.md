# Creator Pre-clearance: Phrase/Motif 연동 감사 및 ADR

2026-09-14. 이번 범위는 공통 연동과 버전 갱신 계약이다.

## 실제 구조

- React/Vite/TypeScript UI, Node ESM 서버, Vitest. API는 Vite middleware plugin이다.
- `server/search-api.mjs`의 `searchDatabase`가 SQLite 검색을 실행하고 `getWork`가 악보와 분석을 제공한다.
- 작곡 Harness 대화의 최근 작업도 이 저장소의 `server/phrase-boundaries.mjs`를 수정했다. 별도 복사본 없이 이 함수를 직접 공유한다.
- `local-boundary-evidence-v1.9`는 boundaries, motifCells, motifRelations 및 연속성 근거를 반환한다. calibrated:false이며 확률형 confidence가 없다.
- Music Analysis의 `MOTIF_PHRASE_LAYERING_SPEC_v0.1.md`는 두 계층 분리, 반개구간 시간, 원본 이벤트 참조를 규정한다. Motif는 Phrase 경계를 넘을 수 있다.
- 현재 UI의 Motif 확장 범위와 검색 signature의 범위는 다르다. bounded signature를 완전한 Motif라고 단정하지 않는다.

## 구현 결정

`server/structure-analysis-adapter.mjs`가 공유 분석기를 호출해 Phrase와 Motif unit을 만든다. 각 unit은 이벤트 ID, quarter 시간 [start,end), 마디 label/ordinal, family, Phrase 관계와 원시 근거를 가진다. confidence는 null로 보존한다. 원본 events와 rawAnalysis도 저장한다.

이벤트 ID는 source snapshot 범위의 참조다. 완성된 Canonical Core ID로 가장하지 않는다. staff 변경은 허용하지만 서로 다른 part/voice를 한 선율로 합치거나 동시 화음을 평탄화하는 입력은 거절한다.

snapshotId는 원본/이벤트/identity 지문, parser/analyzer/adapter/contract version, 설정 지문으로 결정한다. 분석기 규칙 변경 시 producer는 version을 갱신해야 한다. 변경된 코드는 실행 프로세스 재시작 후 새 분석에 반영된다.

`structureRefreshPlan`은 변경 시 structure/selection/search/aggregation/report 재계산 계획을 반환한다. 이전 결과는 보존하고 사용자 수정값은 재검토한다. 이 함수는 갱신 worker 자체가 아니다.

동일 이벤트 구간의 Phrase/Motif는 하나의 검색 task에 여러 unitId를 연결한다. 다른 겹치는 구간은 overlap 참조를 저장한다. 후속 집계에서는 event coverage 합집합을 사용해야 하며 단순 중복 가산은 금지한다.

## 오프라인 실행

```powershell
node scripts/prepare-preclearance-structure.mjs evaluation/case-assets/S-STRUCT-003/events.json evaluation/runs/preclearance-structure-2026-09-14.json
pnpm exec vitest run server/structure-analysis-adapter.test.js server/phrase-boundaries.test.js
```

CLI는 기존 파일을 덮어쓰지 않는다. 세 번째 인수로 이전 출력 JSON을 주면 변경 계획도 저장한다. 기존 asset에 원본 파일 hash가 없으면 event-snapshot 지문임을 명시한다. 현재는 검색 task를 준비하며 검색을 실행하지 않는다.

## 다음 단계와 제한

- XML/MIDI 정규화, tie logical event 검증, Canonical ID 연결.
- 중요도와 길이에 따른 검색 task 선정, 실제 후보 검색과 작품 집계.
- 버전 배포 registry, corpus 갱신 worker, correction UI.
- 비공개 업로드, owner 인증, 보관/삭제, 검토 우선순위 보정.
- 전체 corpus p50/p95와 MIDI E2E는 아직 측정하지 않았다. fixture 실행시간을 검색 성능으로 취급하지 않는다.

전체 재색인이나 DB migration은 없다. 이번 모듈은 오프라인 단계이며 기존 검색/UI에는 연결하지 않았다. rollback은 새 CLI/모듈 호출을 중단하면 된다.

## 검증 결과

- 2026-09-14: 어댑터 및 공유 분석기 테스트 39개 통과.
- S-STRUCT-003 실제 보존 사례: 구조 unit 23개, 동일 구간 중복 제거 후 검색 준비 task 22개.
- `evaluation/runs/preclearance-structure-2026-09-14.json`에 입력 이벤트, 분석 버전, 원시 근거, Phrase/Motif와 Query를 함께 저장했다.
- 최초 단계에서는 이 22개를 자동 검색하지 않았다. 후속 구현은 `creator-preclearance-search-stage.md`의 중요도 선별·검색·집계 기록을 참조한다.
