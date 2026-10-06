# 국소 옥타브 이동 및 장식음 누락 복합 평가

## 사전 설계 (2026-09-17)

사용자 지시에 따라 검색 알고리즘은 바꾸지 않고, 개선안은 [통합 보류 목록](search-evaluation-improvement-backlog.md)에 누적한다.

- 이전 memory-variation-50-v1의 원형 10개를 그대로 사용한다. 새로운 독립 표본이 아니라 변형 강도 비교다.
- 원형 대조 10개 → 한 음 ±12반음 이동 10개 → 같은 이동 + 떨어진 장식음 후보 하나 삭제 10개 순서, 총 30회.
- 중간에 가까운 내부 음을 결정적으로 선택한다. 장식음 삭제 위치와 앞뒤 두 event 이내를 제외해 두 변화가 같은 음에 겹치지 않도록 한다. 위/아래 이동 각 5개.
- 삭제 음가는 직전 음에 흡수해 후속 onset과 Query 전체 길이를 유지한다. 원형 16음→복합 변형 15음이다. 짧은/약박 장식음 후보는 확정 Schenker 분석 라벨이 아니다.
- 모든 케이스는 검색 전에 확정하고 selection 해시를 저장한다. 원형 대조도 새로 검색한다.
- source 파일 Top5, 원래 구간, 정렬 및 누락, 추천 결과를 구분한다. 실패 시 후보 진입/창 평가/점수 탈락 근거를 보존한다.

## 재현과 보존

1. node scripts/build-octave-combination-suite.mjs (기존 경로 덮어쓰지 않음)
2. MUSICANOTE_SINGLE_OMISSION=1, MUSICANOTE_VISIBLE_RANKING=0으로 node scripts/run-structural-next40.mjs evaluation/reports/octave-combination-20-v1/suite.json evaluation/runs/octave-combination-20-v1
3. 실행 실패만 node scripts/retry-double-ornament-trial.mjs octave-combination-20-v1 로 별도 재시도 기록.
4. node scripts/report-memory-variation.mjs octave-combination-20-v1
5. node scripts/package-memory-variation.mjs octave-combination-20-v1

사례 묶음: evaluation/exports/octave-combination-20-v1/ — cases, base-assets, runs, suite, index 및 실행 지문. 원형·변형 Query·정확한 수정 ID/음높이/음가·XML 문맥·전체 응답·문제와 제안을 포함한다.

## 최종 결과와 검토 (2026-09-17)

표시 보완: 페이지 맨 위에 사례별 원형/변형 검색 순위 요약표, 각 악보 위에 원곡 순위 배지, 아래에 실제 상위 10개 검색 결과 표를 추가했다. 원본 파일이 10위 밖이면 해당 행도 추가하며 실제 순위를 유지한다. 기대한 원본 파일 행은 연녹색으로 구별한다. 저장된 검색 응답을 다시 표시한 것으로 검색 로직/점수는 변경하지 않았다.

| 조건 | 원본 파일 Top5 | 지정 원형의 대표 구간 대응 | 추천 발생 |
|---|---:|---:|---:|
| 원형 대조 | 10/10 | 9/10 | 0 |
| 한 음 ±12반음 | 10/10 | 9/10 | 7 |
| 옥타브 + 장식음 삭제 | 10/10 | 8/10 | 0 |

첫 원형의 60초 제한 시간초과는 별도 180초 제한 재시도에서 약 14.4초에 완료했다. 최초 실패와 재시도 모두 보존했다. 검색 엔진 해시와 DB 크기/수정 시각은 이전 batch와 동일하다.

사용자 평가 기준: 변형은 원곡이 확인 가능한 상위권에 남으면 긍정적이다. 1위 유지가 필수는 아니며 순위 하락 자체를 결함으로 보지 않는다. 변형되어도 다른 후보보다 유사하면 1위도 가능하다. 이번 20개 변형의 회수 성적은 모두 긍정적이다.

### 순위와 분리한 음표 대응 관찰

- OCT01/OCT02-local-octave: 변경 음은 원본 음에 대응하지 않고 deletion으로 제외됐다. 나머지 선율로 원곡을 1위 회수했다. 10개 중 8개는 변경 음을 원래 음높이의 source 음에 substitution으로 대응했다.
- OCT01-octave-plus-omission: 변경 음이 deletion. OCT02 복합 변형은 변경 음 68(원형 80)을 source 74에 연결한다. 대응 경로의 시각적·음악적 정당성은 추가 검토 대상이며 곡 회수 실패는 아니다.
- OCT10 복합 변형은 반복 대표 구간 차이와 일부 query 미대응이 함께 있다. 특정 원래 구간을 대표로 강제하는 규칙은 만들지 않는다.
- 단일 옥타브 변형의 추천 7건은 발생 수이며 모두 정답 추천이라고 판정한 것은 아니다. 복합 오류는 현재 보수적인 추천 범위 밖이라 제안이 없다.

개선안은 통합 보류 목록 EVAL-005에 추가하고 운영 검색은 수정하지 않았다. Query·변경 ID·XML·전체 응답·위 관찰은 독립 케이스 묶음에 보존한다.

### 검증 및 보기

- 원형/변형 비교 악보 60개 생성, 지정 SVG ID 검사 통과. 실제 화면의 모든 배치를 시각 검증했다는 뜻은 아니다.
- 30개 케이스 스키마·로컬 참조·XML/event 해시 검증 통과, 잘못된 alignment 인덱스 0건. validation.json에 결과 저장.
- 비교 페이지: http://127.0.0.1:5173/evaluation/reports/octave-combination-20-v1/index.html
- 집계: evaluation/reports/octave-combination-20-v1/results.json 및 REPORT.md
