# EVAL-003 — 반복 attack 분할·병합 의미 보존

날짜: 2026-09-22

## 문제

`memory-variation-50-v1`의 repeat-split 10개는 한 지속음을 같은 음높이의 실제 attack 두 번으로 나눈 Query다. 타이가 아니며 총 음가는 유지된다. 기존 local alignment는 원곡을 대체로 상위권에서 회수했지만, 추가 attack을 일반 `deletion`으로만 표시하여 “누락 음”과 구별할 수 없었다.

## 적용한 일반 규칙

- 기존 `insertion`/`deletion`과 비용을 그대로 유지한다. 따라서 검색 점수, admission, Exact 판정은 완화하지 않는다.
- 정렬 완료 후 같은 음높이의 두 attack이 시간상 연속이고, 두 음가의 합이 하나의 공통 템포 비율 아래 상대편 지속음과 정확히 같을 때만 의미 주석을 붙인다.
- Query 쪽 attack이 둘이면 `repeat-split`, 후보 쪽 attack이 둘이면 `repeat-merge`다.
- 조옮김은 전체 대응 음의 중앙 음정 차이로 검증한다. 음높이, 연속 onset, 합산 음가 중 하나라도 다르면 주석을 붙이지 않는다.
- 주석은 원래 gap step에 선택 필드로 저장한다. 화면 강조의 candidate index와 기존 API 소비자는 그대로 동작한다.
- 결과 설명에는 타이·완전 일치가 아니며 실제 attack 분할/병합을 명시적으로 유지했다는 문장을 추가한다.

## 검증

- 합성 회귀에서 Query의 `.5 + .5` 반복 attack과 후보의 `1` 지속음을 `deletion + repeat-split`으로 보존했다.
- 반대 방향은 `insertion + repeat-merge`로 보존했다.
- 합산 음가가 맞지 않는 대조군에는 관계 주석이 생기지 않았다.
- `server/search-api.test.js` 89/89 통과.
- 실제 repeat-split 10개는 모두 상위권을 유지했다: MEM01 1위, MEM02 1위, MEM03 3위, MEM04 1위, MEM05 3위, MEM06 1위, MEM07 4위, MEM08 1위, MEM09 1위, MEM10 1위.
- MEM02~07·09·10은 지속음↔두 attack 관계가 실제 대표 구간에 있어 `repeat-split` 주석과 설명이 붙었다. MEM01·MEM08은 같은 KYSing 작품의 다른 반복 위치가 대표로 선택됐고 그 위치에는 실제 두 attack이 있어 17/17 직접 대응됐다. 따라서 관계를 거짓으로 만들지 않았다.
- MEM01·MEM08의 일시적 0건은 EVAL-002 제한 재평가가 10/17음의 낮은 coverage 경로를 고른 별도 회귀였다. similarity 우선·낮은 coverage 한정 lookback 보완으로 둘 다 1위 복구했다.

## 의도적으로 하지 않은 것

- repeat-split을 Exact로 승격하지 않았다.
- gap 비용을 낮추거나 총점을 올리지 않았다.
- 동음 반복이라는 이유만으로 느슨한 음가 근사를 허용하지 않았다.
- 타이를 반복 attack으로 해석하지 않았다. Query tie와 원본 tie는 그 전에 logical attack으로 합쳐지는 기존 계약을 유지한다.
