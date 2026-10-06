# 사전검토 1단계: 실행 안정화와 조회 재사용

2026-09-14. 기존 검색의 후보 상한·음악적 점수·정렬 논리는 유지한다.

## 확인한 병목

이전 7개 실행 총 370.8초 중 박자 조회 201.43초, 후보 회수 140.33초였다. 정렬은 약 9초다. 박자 조회는 원본 XML에서 part timeline을 읽는 경로이며 기존 meter-context.sqlite에 영속 캐시가 이미 있다. 최초 실행의 원본 조회 비용과 이후 warm 비용을 구별해야 한다. 이번 단계에서 박자 계산이나 4/4 fallback 규칙을 변경하지 않았다.

## 검색 작업자

Node worker thread 한 개를 재사용한다. 동기 검색이 메인 실행을 막지 않으므로 SIGINT/SIGTERM 및 task timeout으로 작업자를 실제 종료할 수 있다. 기본 timeout은 구간당 180초다. timeout 뒤에는 새 작업자로 다음 구간을 실행한다. 캐시는 작업자 생존 기간 안에서 유지된다.

## 재개와 저장

보고서 옆 `.job` 디렉터리에 manifest와 task별 JSON을 둔다. 임시 파일을 쓴 뒤 rename하여 완료 기록이 반쯤 저장되는 것을 피한다. 완료 task만 재사용하며 실패 task는 다시 실행한다.

manifest는 전체 구조 snapshot hash, 선별 설정, 검색 코드/분석기 코드 hash, DB 경로·크기·mtime 및 WAL mtime, 검색 환경을 포함한다. 바뀌면 resume을 거절하고 새 실행 경로를 요구한다. 오래된 결과를 새 분석 결과에 섞지 않는다.

동일 job의 동시 실행은 PID lock으로 차단한다. resume 시 프로세스가 존재하지 않는다는 ESRCH 결과가 있을 때만 이전 lock을 제거한다. PID가 살아 있거나 접근 여부가 불명확하면 덮어쓰지 않는다.

```powershell
node scripts/run-preclearance-search.mjs prepared.json report.json --timeout-ms=180000
node scripts/run-preclearance-search.mjs prepared.json report.json --resume --timeout-ms=240000
# 내부 검증용: 최초 실행과 resume 모두 동일한 제한을 사용한다.
node scripts/run-preclearance-search.mjs prepared.json small-report.json --max-tasks=1
```

Ctrl+C로 취소하면 완료 task를 보존한다. 실행시간 제한만 바꾸는 것은 resume 가능하다. 검색 설정이나 max-tasks 변경은 불가하다. 운영 UI 취소 버튼, 분산 job queue, 자동 스케줄링은 이번 범위에 없다.

## 후보 캐시

`MUSICANOTE_RETRIEVAL_CACHE=1`에서만 작동한다. 사전검토 CLI는 기본 on, 기존 사이트 검색은 기존 기본값 off다. `--cache=0`으로 비교 가능하다.

- token count와 정확히 같은 token/LIMIT의 SQL row 목록만 저장한다.
- SQL 결과 순서와 제한은 바꾸지 않는다. 다른 LIMIT의 prefix를 추측해 재사용하지 않는다.
- 후보 목록 약 32MiB와 token count 약 2MiB의 별도 LRU로 제한한다. 큰 목록이 작은 count 항목을 밀어내지 않게 분리했다. 실제 JS heap 전체의 엄밀한 상한은 아니다.
- 검색 DB 크기/mtime 변경 시 메모리 캐시를 비운다. 인덱스 갱신은 실행을 멈춘 후 새 worker/job으로 시작하는 운영 규칙을 유지한다.
- countQueryMs, postingsQueryMs, retrievalCacheHits, retrievalCacheBytes를 profile에 추가했다.

## 검증

작업자 timeout/취소/재생성, 캐시 무효화와 순서 보존, 구조·검색 준비 테스트 50개 및 기존 검색 회귀 테스트 73개 통과.

실제 A/B는 이전 보고서의 동일 7개 Query를 캐시 off → on → on 순서로 실행한다. profile을 제외한 전체 검색 반환값의 hash가 모두 같아야 통과한다. 순차 실행의 디스크/박자/파싱 cache 효과를 포함하므로 off 대비 전체 단축을 새 후보 캐시만의 인과 효과라고 주장하지 않는다.

결과: evaluation/runs/preclearance-cache-ab-2026-09-14.json.

첫 A/B에서 큰 Query의 캐시 적중이 0인 경우를 발견했다. 원인은 단일 LRU에서 큰 후보 목록이 count 항목을 축출한 것이다. 최종 분리 구현은 `preclearance-cache-final-2026-09-14.json`에서 이전 cache-off 전체 반환 hash와 비교한다.

## 남은 제한

최초 박자 timeline 생성 비용은 남는다. 이를 줄이려면 신규 인덱스 빌드 단계에서 검증된 박자 timeline을 함께 저장하는 작업이 적절하다. 전체 코퍼스 재색인은 이번에 실행하지 않는다. 후보 구축의 메모리/정렬 비용 역시 SQL 캐시와 별도로 계측해야 한다.

## 최종 실제 검증 결과

최종 7개 Query 모두 이전 cache-off 전체 반환 hash와 일치했다. exact/similar 순서, 점수, alignment, 설명과 악보 이벤트까지 비교하며 profile만 제외한다.

| Query | 캐시 off (초) | 최종 첫 실행 (초) | 최종 재사용 (초) |
|---|---:|---:|---:|
| 1 | 21.575 | 10.757 | 2.415 |
| 2 | 67.313 | 16.090 | 12.404 |
| 3 | 20.439 | 9.544 | 3.309 |
| 4 | 26.795 | 13.148 | 5.627 |
| 5 | 9.863 | 6.311 | 5.651 |
| 6 | 11.300 | 6.426 | 2.871 |
| 7 | 12.028 | 3.752 | 2.907 |
| 합계 | 169.313 | 66.028 | 35.185 |

별도 프로세스·순차 실행이며 OS/박자/parsed cache가 관여한다. 79.2%의 관측 단축을 후보 캐시만의 효과 또는 일반 p95 개선으로 주장하지 않는다. 최종 count cache 분리 후 모든 Query에서 적중이 확인됐다.

실제 CLI 검증:

- 1개 구간 검색 6.567초 → 동일 manifest resume 0.018초, reused=1.
- `--cache=0`으로 설정을 바꾼 resume은 기존 결과를 변경하기 전에 거절됐다.
- 1ms 제한으로 작업자 종료 및 partial 기록을 확인했다. 이후 180초 제한 resume은 실패 구간을 재실행해 6.299초에 completed, reused=0이었다.
- 테스트용 보고서: `evaluation/runs/preclearance-resume-check-2026-09-14.json`, `preclearance-timeout-check-2026-09-14.json`. timeout 보고서는 성공 재개 결과로 갱신되며 위 실패 과정은 본 기록과 실행 로그에 남긴다.

기존 웹 검색은 캐시 기본 off이며 이번 사전검토 CLI에서 먼저 on으로 검증했다. 웹 화면 업로드·취소 버튼은 아직 없다.
