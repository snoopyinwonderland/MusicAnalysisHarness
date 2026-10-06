# 기억 입력 변형 50개 — 순차 평가 및 케이스 저장

## 계획

사용자 승인에 따라 10개 원형 × 5종 변형 50개를 실제 검색한다. 원형 대조 10개와 역순 도전 대조 5개를 추가해 총 65회다. 선별과 변형은 검색 전에 확정한다.

1. 장식음 후보 삭제 후 음가를 직전 음에 합치기: 이후 기둥 도착 시각 유지.
2. 지속음을 같은 높이의 두 번 공격으로 분할: 타이 없음.
3. 인접한 서로 다른 두 음가를 균등화: 합계 4박 이하, 총 길이 유지.
4. 긴 음의 끝 0.5박을 쉼표로 바꾸기: 다음 음 도착 시각 유지.
5. 첫 음 생략: 입력 시작 위치 이동, 기본 startsOnDownbeat=true 가정의 영향 포함.

원형은 기존 XML 감사 표본 중 정확히 같은 pitch/duration/rest 열을 중복 제거해 순서대로 10개 선택한다. 여러 구간이 같은 곡에 속하며 4/4 편의 표본이다. 역순 대조는 원본을 찾으면 무조건 오류인 음성 정답 집합이 아니다. 관련성 및 상위 후보의 정당성은 음악적 검토가 필요하다.

## 보존과 재현

- 생성: scripts/build-memory-variation-suite.mjs (기존 출력 경로 덮어쓰지 않음)
- Query 원형·변형·음가·쉼표·변경 ID·설명: evaluation/reports/memory-variation-50-v1/suite.json
- 실행: MUSICANOTE_SINGLE_OMISSION=1, MUSICANOTE_VISIBLE_RANKING=0으로 scripts/run-structural-next40.mjs에 suite와 evaluation/runs/memory-variation-50-v1 전달
- 전체 순위/음표 정렬/후보 trace/실행 fingerprint: 위 runs 폴더. 시간초과는 검색 미회수와 분리하며 180초 재시도는 별도 retry 파일.
- 독립 사례 모음: evaluation/exports/memory-variation-50-v1/index.json 및 cases/*.json. 기존 musicanote-evaluation-case/v1 검증기를 통과한다.
- 재현 MusicXML·event snapshot·SHA256: 같은 exports 폴더의 base-assets. 원본 구간 앞뒤 최대 2마디 XML을 공유 참조한다. 캡처 실패는 manifest에 명시한다.
- 포장: node scripts/package-memory-variation.mjs. 실행 중에는 pending, 완료 후 각 사례의 결과 참조를 갱신한다.

## 판단

원본 source 파일 회수/Top5와 지정된 원형 구간 대응, 반복 위치 목록, 정렬된 음표 수, 추천 기능 작동을 구별한다. 후보 미진입·위치 창 누락·점수 탈락·구간 대표 선택을 별도로 기록한다. 검색 알고리즘 변경은 이번 실험에 포함하지 않고 개선 후보를 보고한다.

## 최종 결과 — 2026-09-16

65회 모두 완료, 실행 오류/재시도 0회. 검색 실행 시간 합계 약 1,010초이며 동시 부하·준비 작업을 포함한 사용자 대기시간 벤치마크는 아니다.

| 유형 | 원본 파일 Top5 | 지정 원형의 대표 구간 대응 |
|---|---:|---:|
| 원형 대조 | 10/10 | 9/10 |
| 장식음 삭제 + 앞 음에 길이 합침 | 10/10 | 10/10 |
| 지속음 → 같은 높이 두 음 | 10/10 | 9/10 |
| 두 음의 길이 균등화 | 10/10 | 9/10 |
| 음 끝 0.5박 → 쉼표 | 10/10 | 9/10 |
| 첫 음 생략 | 10/10 | 9/10 |

변형 50개 모두 Top5이며 순위 하락은 없었다. AQUA 리듬 균등화만 원본 파일 4위→2위이고 나머지는 원형과 같다. 3·4위 원본 앞에도 같은 작품의 다른 파일들이 나타나므로 작품 단위 성적과 파일 단위 성적을 혼동하지 않는다. 역순 대조 5개에서는 원본 파일을 회수하지 않았다. 다른 곡은 1위 점수 약 73.5–82.1로 반환되며, 이것만으로 오탐률을 계산할 수 없다.

### 발견한 문제와 보완 우선순위

1. **일반 검색의 Exact 분류에서 음가/쉼표 차이 소실.** 쉼표 변형 10개 모두 Exact 100점이었다. server/search-api.mjs의 rhythmValues는 다음 attack까지 간격을 사용하고, rhythmShapeSimilarity의 허용적 결과를 일반 Exact bucket 판정에도 사용한다. 음 끝을 줄이고 그 길이만큼 쉬면 attack 간격은 같아진다. 검색 후보 허용은 유지하되 Exact는 공통 템포 배율 하에서 실제 duration와 silence gap을 별도 검증해야 한다. 리듬 균등화에서도 MEM05/MEM08이 Exact 100이므로 긴 리듬 비율을 2로 제한하는 압축과 판정 경로를 함께 감사한다. 상세 검색 체크박스의 엄격 경로 전체를 검증했다는 뜻은 아니다.
2. **곡을 찾지만 정렬이 틀어진 사례.** MEM10-absorb-ornament(잃어버린 우산)는 1위, 약 89.8점이지만 3박 F4를 뒤의 0.5박 F4에 연결하고 3박 F#4를 누락했다. rhythm 점수는 약 47.9. 유지된 도착 시각·긴 음의 coverage·음가 근거로 경쟁 경로를 비교하는 보완을 우선 검토한다. 특정 작품 예외나 단순 threshold 완화는 하지 않는다.
3. **반복 음 분할의 설명 가능성.** repeat-split 10개는 추가된 공격 하나가 unmatched로 남는다. 원본 1음과 입력 2음의 관계를 일대다 split/merge로 표현하는 방식을 검토한다. 이것을 전부 틀린 강조로 단정하지 않는다.
4. **반복 위치와 대표 결과를 구분.** MEM09-original은 45마디 대신 17마디를 대표로 반환하지만 occurrence에 17·45마디가 모두 있다. 단순 위치 불일치를 실패로 집계하지 않는다. 원형 대비 사례의 실제 대응 target도 계속 보존한다.
5. **Query 추천의 범위.** 이번 65개에서 제안 0건. 현 추천기는 제한된 1음 피치 보정/누락 보완용으로 엄격한 리듬·정렬 조건을 사용한다. 추천 결함으로 즉시 판단하지 않고 리듬/분할 추천을 별도 제품 범위로 검토한다.

코드 근거와 수치 관찰은 review.json 및 각 독립 case JSON에 저장했다. 개선안은 proposed-not-implemented 상태이며 운영 검색 로직·점수·DB는 변경하지 않았다.

### 산출물과 검증 범위

- 비교 악보/소리: http://127.0.0.1:5173/evaluation/reports/memory-variation-50-v1/index.html
- 집계 및 전체 Query: evaluation/reports/memory-variation-50-v1/{REPORT.md,results.json,suite.json,review.json}
- 이동 가능한 사례 묶음: evaluation/exports/memory-variation-50-v1/ (cases 65개, base-assets 10개, runs 전체 응답, suite.json, index.json, 실행 manifest)
- 스키마 65개, 모든 로컬 자산/응답 참조, XML/event SHA256 검증 통과. 전체 결과 alignment의 잘못된 인덱스 참조 0건.
- 원형/변형 악보 130개 생성 및 지정 SVG ID 확인, 페이지 HTTP 200. 브라우저 자동화 런타임 실패로 실제 화면의 모든 강조·배치에 대한 시각 검증은 완료하지 못했다. 인덱스 검사 통과가 화면 강조의 완전성을 보장하지 않는다.
- 기존 편의 표본 10개 원형, 모두 4/4의 16음 중심이라 일반화에 한계가 있다. 다음 holdout에는 새 작품·짧은 Query·3/4·6/8·연속 변형을 추가하되 이번 케이스를 튜닝/검증 양쪽 정답으로 재사용하지 않는다.
