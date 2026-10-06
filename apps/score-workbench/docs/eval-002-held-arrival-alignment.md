# EVAL-002 — 긴 음 도착·점유 정렬과 제한 재평가

날짜: 2026-09-19, 보완 2026-09-22

## 기본 규칙

- Melody + Rhythm local alignment는 각 구간의 대표 음가로 전체 템포를 정규화한다.
- 긴 Query 음을 매우 짧은 후보 attack에 대응시키면 held coverage 비용을 준다.
- insertion/deletion 뒤에는 직전 raw 음이 아니라 직전 실제 대응 음부터의 도착 간격을 비교한다.
- 긴 음 누락이 보일 때만 가까운 시작점을 제한적으로 다시 정렬한다.

## 2026-09-22 보완

인접 시작점 재평가가 raw cost만 비교하면 Query 음을 많이 삭제한 짧은 경로가 더 낮은 비용으로 선택될 수 있었다. 재평가 선택은 coverage를 포함한 normalized similarity를 우선하고, similarity가 같을 때만 raw cost를 tie-break로 사용한다.

정상 coverage 경로는 기존처럼 앞쪽 4개 시작점만 본다. 최초 경로 coverage가 75% 미만인 실패 형태에만 최대 8개까지 확장한다. 일반 full scan을 넓힌 것이 아니다.

MEM01/MEM08 repeat-split은 기대 KYSing 작품이 후보에 있었지만 10/17음 경로(coverage 58.82%)가 선택되어 query-coverage에서 탈락했다. 보완 후 둘 다 1위로 복구됐고 17음이 모두 대응됐다. 선택된 다른 반복 위치에는 실제 두 attack이 있어 거짓 `repeat-split` 관계는 붙이지 않았다.

## 검증

- 합성 held-arrival, 전체 템포 x2, 장식음 삽입, 짧은 반복 대조 유지.
- 낮은 raw cost와 높은 phrase coverage가 경쟁하는 17음 회귀 추가.
- 서버 검색 테스트 93/93 통과.

