# 짧은 Query 지연 진단 — 2026-09-15

## 변경 범위

검색 후보·상한·정렬·입장 조건·점수는 변경하지 않았다. `searchDatabase`의 선택적 onProgress 콜백, worker progress 메시지, 별도 진단 CLI를 추가했다. 기본 호출에는 콜백이 없으며 사이트에 진행 메시지를 노출하지 않는다.

token count, postings, 후보 회수 완료, 후보 시작, decode, exact 구간 검사, alignment, 박자 조회, 구조/phrase 등 기존 profiled 함수의 시작·종료와 누적 시점을 기록한다. 부모 프로세스가 progress.jsonl에 즉시 보존하므로 worker가 timeout으로 종료되어도 앞선 로그는 남는다. 진행 메시지를 검색 완료로 오인하지 않도록 worker client를 수정하고 테스트했다.

세부 계측이 없는 연산도 있고 서로 포함되는 시간 항목도 있다. 전체 항목을 단순 합산해서 100%로 만들지 않는다. JSONL 쓰기/메시지 전송 오버헤드를 포함하므로 trace 실행시간 자체를 일반 사용자의 검색시간으로 보장하지 않는다.

## 재현 명령

```powershell
node scripts/trace-preclearance-query.mjs evaluation/runs/preclearance-review-diverse-2026-09-15/suite.json PC-REVIEW-22c02b91adea evaluation/runs/NEW-trace
node scripts/verify-search-trace.mjs evaluation/runs/NEW-trace evaluation/runs/NEW-trace-verification.json
```

두 출력 경로 모두 새 경로여야 한다. 입력 사례·코드 지문·DB size/mtime를 기록한다. 검색 timeout 60초, cache=1, profile=1이다. Ctrl+C를 지원한다. source XML/운영 설정이 바뀌면 비교를 새 실행으로 관리한다. 현재 DB의 강한 내용 해시와 모든 외부 파일 지문까지 수집하는 도구는 아니다.

verify는 시간 profile만 제외하고 **API의 JSON 직렬화 결과 전체**를 비교한다. 메모리의 undefined 필드는 JSON 저장에서 생략되므로 양쪽을 동일하게 직렬화한 뒤 비교한다. 순위·점수·설명·targets가 들어 있는 모든 결과 음표·alignment를 포함한다. 비교 실패 시 해시 차이를 보고하고 성공 파일을 만들지 않는다.

## 실제 결과

이전 반복음 Query의 60초 timeout 사례를 재실행했다. 이번 trace는 약 40.20초에 완료했다. 그 사이 OS/박자 cache 상태가 바뀌므로 timeout 해소를 새 계측 코드의 성능 개선으로 주장하지 않는다.

| 항목 | Trace 실행 | 이후 trace-off 실행 |
|---|---:|---:|
| engine total | 40.005초 | 4.632초 |
| 후보 회수 전체 | 10.704초 | 2.010초 |
| postings 조회 | 8.720초 | 0.408초 |
| 박자 조회 | 19.041초 | 0.107초 |
| exact 구간 검사 | 4.394초 | 0.129초 |
| decode | 2.480초 | 0.667초 |
| local alignment | 0.738초 | 0.501초 |

두 실행 모두 candidateKeys=2,534, uniqueWorksEvaluated=1,509, 결과 20개다. 120개 관련 테스트가 통과했다. 실제 전체 JSON 응답 해시는 양쪽 모두 `03a60dc516253d9112ac11e5858461b3ec3cd28914a10d57997471fc06c6f9a4`다.

저장 위치:

- `evaluation/runs/preclearance-trace-repeat-2026-09-15/`: input.json, progress.jsonl, result.json.
- `evaluation/runs/preclearance-trace-verification-2026-09-15.json`: 전체 응답 불변과 두 profile.

## 해석과 다음 개선

이번 trace에서는 local alignment보다 박자 정보 조회와 postings I/O가 훨씬 컸다. 후속 warm 실행의 격차는 cache/I/O 영향에 부합하지만 trace 오버헤드와 상태 변화가 섞였으므로 특정 최적화의 인과적 속도 향상 배율을 계산하지 않는다.

코드 확인: 새로 읽은 박자 timeline은 pendingMeterContexts에 모이고 flushMeterContexts는 검색 마지막에 실행된다. timeout으로 worker가 종료되면 그 worker의 아직 저장되지 않은 timeline은 사라질 수 있다. 이 때문에 불완료 검색이 다음 검색을 충분히 warm하지 못할 가능성이 있다. 이번에 쓰기 정책을 바꾸지는 않았다.

다음은 제한된 batch 단위 박자 cache 저장 또는 별도 사전 준비를 시험하는 것이다. 원본/인덱스 변경에 대한 무효화, 저장 실패 시 검색 의미 보존, timeout 후 재사용, cache cold/warm 분리 A/B가 필요하다. 이후 postings 데이터 접근 비용을 측정한다. 후보 수를 임의로 줄이거나 특정 Query 정답을 고정하는 방식으로 속도를 맞추지 않는다.
