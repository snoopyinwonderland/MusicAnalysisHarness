# EVAL-008 — 같은 음정 진행의 리듬 일치 occurrence 선택

## 사례

- 평가 사례: `short-query-90-v1-SH02-L6-original`
- 기대 작품: `work-bfef6f9da3828ed1`, `ANGEL`
- Query 음가: `[0.5, 0.5, 0.5, 0.5, 1, 0.5]`
- 실제 기대 위치: raw index 249, 137마디 시작
- 기존 대표 위치: raw index 232, 131마디 시작
- 기존 위치 음가: `[1, 0.5, 0.5, 0.5, 0.5, 1]`

두 위치는 조옮김을 허용한 interval 진행이 같다. 기존 검색은 모든 interval-exact occurrence 중 phrase evidence가 높은 곳 하나를 먼저 고르고, 그 뒤에 리듬을 계산했다. 따라서 131마디가 interval 100/rhythm 71.25로 평가됐고 리듬까지 정확한 137마디는 정밀 점수에 도달하지 못했다.

## 일반 규칙

Melody + Rhythm 검색의 대표 occurrence 선택 순서는 다음과 같다.

1. 리듬까지 Exact인 occurrence가 있으면 그 집합을 사용한다.
2. 같은 집합 안에서는 phrase evidence, conflict 수, 앞선 위치 순으로 대표를 고른다.
3. 리듬 Exact occurrence가 없을 때만 interval-exact 대표로 내려간다.
4. Melody Only는 계속 interval 대표를 사용한다.
5. Absolute/Exact Interval이 명시한 required span은 최우선으로 유지한다.

이 변경은 작품 ID, 제목, 마디 번호를 참조하지 않는다. 점수식을 바꾸지 않고 평가할 실제 위치만 바로잡는다.

## 결과

| 항목 | 변경 전 | 변경 후 |
|---|---:|---:|
| 기대 작품 순위 | Top 200 밖 | 1위 |
| 대표 위치 | 131마디 | 137–138마디 |
| 분류 | 기대 작품 미반환 | Exact |
| 총점 | — | 100 |
| Rhythm | 71.25인 다른 반복만 평가 | 100 |
| Meter | — | 100 |
| Skeleton | — | 100 |

서버 집중 테스트 83/83 통과. 리듬 일치 우선, interval fallback, Melody Only 유지, required span 우선의 네 경로를 고정했다.
