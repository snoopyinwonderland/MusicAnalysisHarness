# EVAL-005 — 국소 옥타브 이동의 표시 정렬

날짜: 2026-09-22

## 문제

국소 음 하나를 ±12반음 옮기면 그 음으로 들어가는 interval과 나오는 interval이 모두 크게 달라진다. 기존 local alignment는 작품을 상위권에서 잘 회수하면서도 변경 음을 `deletion`으로 버리고, 뒤 음을 한 칸 당겨 대응한 다음 원본 음을 `insertion`으로 남기는 경로를 고르기도 했다. OCT02 복합 변형에서는 변경 음을 전혀 다른 높이에 연결했다.

이 문제는 후보 회수나 순위 실패가 아니라 악보 강조와 설명의 의미 오류다. 기존 20개 변형은 모두 원본 Top5였고 OCT01/02도 1위였다.

## 적용한 일반 규칙

- 후보 평가, local score, admission, ranking, Exact 판정이 끝난 뒤 사용자에게 반환할 정렬 경로만 제한적으로 재해석한다.
- 기존 경로에서 실제 관찰된 조옮김 offset만 후보로 사용한다.
- 전체 구간을 다시 대응했을 때 다음 조건을 모두 만족해야 한다.
  - 조옮김 후 일반 음은 전부 정확히 일치
  - residual이 정확히 ±12인 국소 옥타브 이동은 정확히 1개
  - Query와 후보 길이 차이만큼의 gap만 존재하며 최대 1개
  - 일반 substitution은 0개
  - 최소 4개 및 전체에서 한 음을 제외한 대응 coverage
- 통과하면 변경 음을 원본의 같은 pitch class 음에 직접 연결하고 `octave-displacement` 관계를 저장한다.
- 기존 점수와 Exact/Similar 분류는 바꾸지 않는다. 설명에도 강조 음·진단 전용 후처리임을 밝힌다.

## 검증

- 합성 단일 옥타브: 잘못된 delete-shift-insert 5-step 경로가 직접 4음 대응으로 복구됐다.
- 합성 복합 변형: 실제 후보 음 하나의 insertion은 유지하고 옥타브 음은 직접 대응했다.
- 일반 substitution이 남는 대조군에는 옥타브 해석을 만들지 않았다.
- `server/search-api.test.js` 92/92 통과.
- 후속 EVAL-002 회귀까지 포함한 서버 테스트는 93/93, 전체 회귀는 498/500 통과했다. 남은 2건은 변경 전부터 존재한 `FullScorePage` Motif 범위 기대값 실패이며 검색 정렬 경로와 무관하다. Production build는 통과했다.
- 저장된 실제 네 경로 재검증:
  - OCT01 local: Query 85 ↔ source 73, 일반 substitution 0, gap 0
  - OCT02 local: Query 68 ↔ source 80, 일반 substitution 0, gap 0
  - OCT01 octave+omission: Query 85 ↔ source 73, 일반 substitution 0, 실제 gap 1
  - OCT02 octave+omission: Query 68 ↔ source 80, 일반 substitution 0, 실제 gap 1

## 제한

- 두 개 이상의 옥타브 이동은 자동 재해석하지 않는다.
- 옥타브 외 음높이 변경이 함께 남으면 원래 정렬을 보존한다.
- 이 규칙은 옥타브 변형의 검색 점수를 높이지 않는다. 향후 실제 회수 실패가 확인되면 음성 대조군과 함께 후보 생성/점수를 별도로 검토해야 한다.
