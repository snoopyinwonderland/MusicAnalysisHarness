# Search performance stage 5: bounded parsed-work cache

## 2026-09-12 implementation

- 검색 점수, 후보 상한, 입장 기준과 순위 계산은 변경하지 않았다.
- SQLite `works.notes` JSON을 해독한 결과와 검색용 음표 배열을 서버 프로세스의 weight-bounded LRU에 보관한다.
- 기본 예산은 128 MiB이며 `MUSICANOTE_PARSED_CACHE_MB`로 조정할 수 있다. 항목 크기는 원본 JSON 바이트의 4배로 보수적으로 계산한다.
- 검색 DB 수정 시간이 달라지면 캐시 전체를 자동 무효화한다. 예산보다 큰 단일 작품은 캐시하지 않는다.
- 프로파일에 `parsedCacheHits`, `parsedCacheMisses`, `parsedCacheBytes`를 추가해 warm-query 효과와 메모리 사용량을 확인할 수 있다.
- 이 단계는 첫 검색의 n-gram retrieval이나 exact scan을 줄이지 않는다. 반복 검색과 겹치는 후보가 많은 연속 검색에서만 직접적인 효과를 기대한다.

## First measurement and correction

- `Q-M100-004` cold 36.6초 중 retrieval 28.1초, candidate evaluation 5.9초였다. 같은 프로세스의 두 번째 실행은 9.0초였지만 초기 LRU는 1,526개 후보의 순차 삽입으로 전부 축출되어 hit가 0이었다.
- 캐시 대상은 모든 seed 후보가 아니라 상위 full-stream 정밀 평가 작품으로 제한했다.
- 동일 Query 안에서 같은 token이 여러 위치에 반복될 때 `count(*)`와 postings SQL을 token당 한 번만 실행하고, 위치별 기존 상한에 맞는 prefix를 재사용한다. 후보 key·evidence·순위 계산은 바꾸지 않는다.

## Next measurement

동일한 느린 Query를 같은 프로세스에서 두 번 실행해 cold/warm 결과 ID·순위·점수의 완전 일치와 `decodeMs` 감소를 확인한다. 이후에도 큰 비중을 차지하는 단계에만 SQL-side aligned-start aggregation 또는 저비용 후보 사전 평가를 적용한다.

## Verified result

`Q-M100-004`를 같은 프로세스에서 두 번 실행했다. 두 실행 모두 기대 작품 1위, 결과 83개, candidate key 2,536개와 평가 작품 1,526개가 동일했다.

| Run | Total | Retrieval | Candidate evaluation | Decode | Cache hit/miss |
| --- | ---: | ---: | ---: | ---: | ---: |
| 첫 실행 | 7,323 ms | 4,067 ms | 2,951 ms | 888 ms | 0 / 1,526 |
| 두 번째 | 7,048 ms | 4,348 ms | 2,430 ms | 556 ms | 260 / 1,266 |

동일 사례의 직전 관측 100,644 ms 및 수정 전 같은-process cold 36,585 ms에 비해 긴 꼬리 지연이 크게 줄었다. OS 파일 캐시 상태가 다르므로 100.6초 대비 배율을 일반화하지 않지만, Query 내부 중복 token SQL 제거 후 retrieval이 28,097 ms에서 약 4.1–4.3초로 감소한 것은 같은 사례의 단계별 profile에서 확인했다.

다음 병목은 여전히 retrieval 약 4초와 1,526개 작품의 candidate evaluation 약 2.4–3.0초다. 다음 단계는 결과 보존형 SQL aligned-start 집계의 소규모 A/B 실험이다.
