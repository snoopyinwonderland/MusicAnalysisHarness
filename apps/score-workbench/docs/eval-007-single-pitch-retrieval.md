# EVAL-007 — 짧은 Query의 단일 음 변형 후보 회수

## 문제

`short-query-90-v1-SH03-L8-pitch-change`는 8개 실제 음 가운데 한 음만 원형과 다르다. 정밀 정렬에 원곡만 전달하면 `UN DI, FELICE` 6–9마디는 local 98.62, rhythm 100으로 평가되지만, 기존 검색에서는 n-gram 후보 축소 단계에서 사라져 순위가 없었다.

한 음의 변화는 그 음 앞뒤 두 interval을 바꾸고, 겹치는 interval 3-gram과 5-gram을 여러 개 동시에 파괴한다. 이 때문에 긴 구간 대부분이 일치해도 하나 남은 흔한 anchor가 수천 작품과 경쟁할 수 있다.

## 진단 결과

- 기대 작품: `work-7c5ee0ca6528fe87`
- Query: 3/4, Melody + Rhythm, 실제 음 8개와 쉼표 2개
- 변경 전: `inHits=true`, `inCandidates=false`, 순위 없음
- 전체 후보 작품 순위: 6,963
- 전역 후보를 뺀 생존 anchor 내부 작품 순위: 459/4,705
- 기대 위치: source note index 12, 6–9마디
- 기대 후보만 scope로 정밀 평가: 97점, local 98.62, interval 93.8, rhythm 100, meter 100, skeleton 100

작은 anchor별 reserve는 이 작품을 회수하지 못했다. 450개 안팎의 검증 없는 reserve를 넣으면 회수할 수 있었지만 비용과 오탐 위험이 커서 폐기했다.

## 적용한 일반 규칙

다음 조건을 모두 만족할 때만 제한형 후보 lane을 사용한다.

1. Query가 Melody 또는 Melody + Rhythm이고 실제 음 수가 8–12개다.
2. 반복음·단순 패턴으로 판정된 저정보량 Query가 아니다.
3. Absolute/Exact Interval/Exact Pitch 옵션이 아니다.
4. 양끝 interval 3-gram anchor 중 하나가 살아 있다.
5. 후보의 같은 길이 구간이 하나의 전역 조옮김 아래 정확히 한 음에서만 다르다.
6. Melody + Rhythm에서는 템포를 정규화한 리듬 형태가 90점 이상이다.

각 양끝 anchor에서 작품당 한 위치, 최대 600작품만 검사한다. 정밀 평가로 넘기는 후보는 전체 최대 40개다. 이 lane은 점수·Exact·admission threshold를 변경하지 않는다.

## 검증

실제 SH03 재실행 결과:

| 항목 | 변경 전 | 변경 후 |
|---|---:|---:|
| 기대 작품 순위 | 없음 | 1위 |
| 구간 | 평가 안 됨 | 6–9마디 |
| 최종 점수 | — | 97 |
| Local similarity | — | 98.62 |
| Rhythm | — | 100 |
| Candidate keys | 기존 실행에서 기대 후보 제외 | 2,664 |
| 평가 작품 | — | 1,534 |
| Cold 실행 | 약 27초로 관찰된 적 있음 | 약 8.4초 |

합성 회귀는 다음을 고정한다.

- 한 조옮김 아래 정확히 한 음만 다른 경우를 인식한다.
- 두 음 이상이 다르면 이 lane을 사용하지 않는다.
- 첫 anchor와 마지막 anchor가 서로의 슬롯을 독점하지 않는다.
- 리듬 83.125인 대조군은 90점 하한에서 제외하고, 전체 템포만 두 배인 리듬 100 후보는 유지한다.

집중 실행 `npm test -- --run server/search-api.test.js`: 79/79 통과. 전체 테스트는 484/486 통과하며, 실패 2개는 검색 서버와 무관한 `FullScorePage` Motif 범위 기대값이다.

## 의도적 제외

- 6음 Query 한 음 변경은 변화 비율이 커서 이 예외를 적용하지 않는다.
- 12음 전체 순차진행처럼 식별력이 낮은 Query는 일반 회수 대상이 아니다. 상세 검색에서 명시적으로 허용하는 정책과 분리한다.
- 장식음 삭제, 두 음 변경, 옥타브 치환은 각각 EVAL-006/EVAL-005 및 별도 omission 경로에서 검증한다.
- 이 규칙은 특정 작품 ID나 제목을 참조하지 않는다.
