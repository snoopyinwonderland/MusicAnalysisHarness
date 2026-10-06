# 검색 성능 6단계 — SQL seed 집계 A/B (2026-09-16)

## 요청과 결론

남아 있는 속도 개선을 검색 후보·순위·점수·일치 음표를 바꾸지 않고 진행한다.
두 느린 Query를 재계측하고 후보 시작점 집계를 SQL로 옮긴 실험을 구현했다.
**기본 적용은 보류한다.** 동일 응답은 확인했지만 OS 캐시가 데워진 대조군보다 느렸다.
MUSICANOTE_SQL_SEED_AGGREGATION=1일 때만 실험 경로이며, 미설정/0이면 기존 경로다.
DB 스키마·색인·원본 XML·검색 점수 규칙·서비스 환경 설정은 변경하지 않았다.

## 측정

같은 suite의 각 Query를 한 worker에서 두 번 실행했다. 시간은 클라이언트 wall seconds.
각 행의 최초/반복은 worker 내 순서이며 **최초를 cold disk라고 해석하면 안 된다.**
실행 순서는 baseline → SQL → 기존 방식 control이다. 두 사례뿐이며 운영 p95의 추정값이 아니다.

| Query | baseline 최초 / 반복 | SQL 최초 / 반복 | 기존 control 최초 / 반복 |
|---|---:|---:|---:|
| PC50-b328cadd7e6c (반음 변경) | 47.456 / 9.428 | 15.389 / 15.254 | 14.393 / 9.393 |
| PC50-63107c35162f (원본) | 43.014 / 13.227 | 21.262 / 16.014 | 17.948 / 11.472 |

baseline 첫 실행의 postings 조회는 23.828 / 22.249초였으나 control 첫 실행에서는 1.762 / 1.785초다.
처음 SQL 실행의 개선처럼 보이는 차이는 캐시 영향과 구분할 수 없으며 SQL의 성능 향상으로 주장하지 않는다.
SQL 집계 자체는 매번 약 4.5~6.7초를 소비한다. 반복 검색의 기존 postings 캐시 이점을 대체하지 못했다.
control의 phraseContextMs는 최초 6.430 / 8.358초, 반복 5.397 / 5.177초였다.
따라서 다음 실험은 프레이즈 문맥의 입력·분석 버전을 키로 하는 bounded cache가 우선이다.
분석기 업데이트, 이벤트/화성 입력 변경, 메모리 상한, 기존 응답 동일성을 함께 검증해야 한다.
캐시 용량 상향과 사전 계산도 후속 후보이며 이번에 구현했다고 간주하지 않는다.

## 동일성

top-level profile만 제외한 **전체 반환 JSON** hash가 12회 실행에서 각 Query별로 같았다.
이는 요청 limit=30의 응답에 대한 검증이지 모든 corpus/Query의 동등성 증명이 아니다.
후보 수/평가 work 수도 각각 2591/1536, 2646/1521로 동일했다.
SQL 오류 fallback은 발생하지 않았고 SQL 집계 행 수와 시간이 실제 기록됐다.

- b328: f8ff76bc047608f1720177fbf4055c00ff3b86d6a11cdb4a3a60899dc05be24d
- 63107: e75781a23eccefbb6dbd5bffe0a7a13240682f910d89da21ff8a689e5d84897c

새 단위 테스트는 중복 token, 서로 다른 LIMIT, 시작점 0 clamp, 빈 postings,
Map/Set 삽입 순서와 deterministic randomized 30 fixtures를 legacy 참조와 비교한다.
실제 화면 캡처나 음표의 시각 검증은 이번 성능 실험에 포함하지 않았다.
동일성은 반환된 alignment/target 데이터도 포함한 JSON 기준이다.

## 구현과 재현

- server/sql-seed-aggregation.mjs: read-only materialized CTE, 동일 LIMIT prefix, SQL 집계 및 기존 Map encounter 순서 복원.
- server/search-api.mjs: opt-in 분기; 400개 초과 요청 또는 SQL 오류 시 legacy fallback.
- scripts/profile-search-cases.mjs: 기존 suite Query로 2회씩 실행, 새 출력 폴더만 허용,
  Query suite hash / DB size·mtime / search-api hash / 안전한 benchmark switch / 전체 응답 보존.
- server/sql-seed-aggregation.test.js: 순서까지 비교하는 회귀.

```powershell
$env:MUSICANOTE_SQL_SEED_AGGREGATION='1'
node scripts/profile-search-cases.mjs evaluation/runs/preclearance-variation50-final-2026-09-16/suite.json evaluation/runs/stage6-NEW-sql PC50-b328cadd7e6c PC50-63107c35162f
$env:MUSICANOTE_SQL_SEED_AGGREGATION='0'
node scripts/profile-search-cases.mjs evaluation/runs/preclearance-variation50-final-2026-09-16/suite.json evaluation/runs/stage6-NEW-control PC50-b328cadd7e6c PC50-63107c35162f
node node_modules/vitest/vitest.mjs run server/sql-seed-aggregation.test.js server/retrieval-cache.test.js
```

MUSICANOTE_RETRIEVAL_CACHE는 이 CLI에서 미지정 시 1이다. 사이트 환경을 바꾸지는 않는다.
동일 index·원본 XML·의존성·분석기 버전이 필요하다. manifest의 search-api hash는 전체 의존성 freeze가 아니며
DB size/mtime도 내용 hash를 대신하지 않는다. 측정 뒤에는 계측 오류 필드를 숫자로 바꾸고 환경 기록을 allowlist로 제한했다.
SQL 실험을 제거하려면 환경변수를 해제하면 된다. 별도 DB 복구나 재색인은 필요 없다.

## 보존 자료

각 경로의 manifest.json / summary.json / 사례별 전체 result JSON을 함께 읽는다.

- evaluation/runs/performance-stage6-baseline-2026-09-16/
- evaluation/runs/performance-stage6-sql-2026-09-16/
- evaluation/runs/performance-stage6-control-2026-09-16/

Query 원본과 유형·음표·음가·기대 source는 원래 50개 suite 및 Harness 사례에 보존하며
이번 기록은 성능 재측정이다. 전문가가 상위 결과의 음악적 정당성을 재판정한 테스트가 아니다.

