# Creator Pre-clearance: 선별·검색·작품 집계

2026-09-14. 오프라인 내부 검증 단계.

## 실행 경로

구조 스냅샷 → Phrase/Motif Query → 특징·길이·반복 선별 → 기존 searchDatabase → source/canonical work 집계.

`server/preclearance-search.mjs`와 `scripts/run-preclearance-search.mjs`를 추가했다. 기존 검색 점수와 후보 회수 논리는 변경하지 않는다.

## 선별 계약

- 최대 7개, 먼저 3개 primary, 나머지 secondary. 이 역할은 자동 검토 제안이다.
- 기본 7~48음. 짧은 구간은 too-short, 긴 구간은 needs-subdivision으로 기록한다. 긴 구간을 임의로 절단하지 않는다.
- 동일한 조옮김 불변 음높이·비례 음가 패턴은 occurrence로 모아 한 번 검색한다. 리듬만 같은 Motif family를 동일 선율로 합치지 않는다.
- 반복음 비율 65% 초과 또는 서로 다른 interval이 3종 미만이면 low-information으로 보류한다. 이 기준은 미보정이며 음계·아르페지오 판정 전체를 대신하지 않는다.
- 선택 구간과 짧은 쪽 기준 70% 넘게 겹치면 추가 검색을 보류한다.
- melody-role이 알려져 있고 0.35 미만이면 보류한다. 알려지지 않으면 미확인 경고를 남긴다.
- 명세의 여섯 중요도 항목을 보존하되 관측 가능한 role·선택 후보 내 반복만 계산한다. 구조적 위치/종지/구조음/박절 중요도는 null이며 유효 가중치만 재정규화한다.
- 선정 순서에는 중요도 추정 55%, 길이 35%, 작품 내 음가 비중 10%의 임시 기준을 사용한다. 이것은 침해 점수나 중요도 정답이 아니다. 설정과 hash를 보고서에 저장한다.

## 검색과 집계

출발 음의 원본 beat가 있으면 선행 쉼표로 박절 위상을 보존한다. beat는 현 검색 IR의 quarter 기반 좌표다. 입력은 logical melodic event 기준이어야 하며 원본 MIDI/XML의 tie 정규화는 후속 단계다.

현재 엔진의 반환 상한은 task당 30개다. 이는 내부 retrieval 후보 상한과 다르다. 기존 엔진은 긴 query에 최대 1400 seed 등을 사용하며, 이번 작업은 이를 변경하지 않는다. title이 아닌 sourceId/workId로 자기 자신을 제외한다. canonicalWorkId가 있으면 판본을 합치고, 없으면 동일 source 파일 내 part/voice를 합친다. 제목만으로 다른 판본을 합치지 않는다.

대표는 가장 높은 localSimilarity다. 반복 점수를 합산하지 않으며 coverage는 실제 정렬된 query event ID의 합집합이다. 후보 importance는 null, 기존 occurrenceImportance는 별도 proxy로만 보존한다. corpus distinctiveness와 양쪽 importance 보정이 없으므로 reviewPriority는 null, reviewLevel은 not-calibrated다.

각 실행에는 제출 Query, 원본 구조 snapshotId, 선택 이유, 제외 이유, elapsedMs, 엔진 profile, 정렬 path, 실제 일치 음표, 마디와 성부, why 설명을 저장한다. 자동 사례이므로 전문가 판정으로 승격하지 않는다.

```powershell
node scripts/run-preclearance-search.mjs evaluation/runs/preclearance-structure-2026-09-14.json evaluation/runs/preclearance-search-2026-09-14.json
```

출력 경로는 새 파일이어야 한다. 오류는 failed/partial로 기록한다. 완료 task는 `.tasks.jsonl`에 점진 저장한다. 프로세스 강제 종료 시 running 파일이 남을 수 있다. 운영용 job queue/timeout/retry는 아직 미구현이다. 최초 실제 실행은 checkpoint 기능 추가 전에 시작했으므로 완료 보고서만 남긴다.

## 검증

관련 테스트 46개 통과: 공유 분석기, 공통 계약, 반복/겹침 억제, 박절 위상, 자가 검색 제외, 작품 집계, 실패 및 checkpoint 처리. 실제 DB 실행 결과는 별도 JSON 보고서에 기록한다.

보고서 요약: `node scripts/summarize-preclearance-search.mjs report.json NEW-summary.md`. Query의 음높이·음가·쉼표, 실행 시간과 순위를 표로 생성한다.

## 다음 단계

희소성 DF와 후보 작품 중요도 분석, 전문가 평가에 의한 선정 기준 보정, 검색 worker의 시간 제한/취소/점진 저장, XML/MIDI 입력 정규화와 비공개 업로드 UI.

## 실제 실행 결과

`preclearance-search-2026-09-14.json`: 7개 모두 completed, 370.8초, 28개 작품 그룹. 구간별 9.9~85.7초. source가 다른 ENDLESS LOVE 세 판본이 유사도 100 및 대표 Query coverage 100%로 회수됐다. 입력과 동일 source는 제외됐다.

다른 곡 최고 유사도 91.74인 Lamentatio Jeremiae는 coverage 10.7%다. 이는 긴 작품 중 특정 구간의 검색 점수이며 작품 전체의 위험 수준으로 해석할 수 없다. 전문가 검토는 아직 없다.

실제 제한: canonical work identity가 없어 동일 작품 판본 세 개를 묶지 못했다. 이를 제목만으로 임의 병합하지 않았다. 향후 검증된 작품 매핑이 필요하다.

profile의 구간별 retrieval은 6.9~60.4초, alignment는 0.75~3.03초였다. 후보 key 2392~2620개, 평가 stream 1482~1525개로, 반환 30개보다 내부 작업이 훨씬 크다. 우선 후보 회수 및 나머지 평가 단계의 세부 시간을 개선해야 한다. 이 단일 실행으로 서버 성능의 일반화 지표를 주장하지 않는다.

Query와 상위 20개 순위는 `creator-preclearance-search-evaluation-2026-09-14.md`, 전체 정렬 근거는 `evaluation/runs/preclearance-search-2026-09-14.json`에 있다. 최초 실제 실행에는 이후 추가한 checkpoint와 searchCodeHash가 없으므로 그 필드를 사후 추정해 채우지 않는다.
