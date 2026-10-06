# 짧은 Query 12·8·6음 변형 90회

## 사전 설계

2026-09-17. 사용자 승인에 따라 새 원형 10곡 × 길이 12/8/6음 × 원형/음높이 변경/장식음 삭제 = 90회. 검색 엔진 변경 없이 실행하고 개선안은 마지막에 함께 검토한다.

- 선별은 검색 전에 XML만으로 수행한다. 기존 harder-100의 20개 작품 제목을 제외했으며 직전 기억/옥타브 테스트 작품과 겹치지 않는다. 전체 과거 프로젝트의 모든 사례와 독립임을 보장하는 표본은 아니다.
- 로컬 MusicXML 목록의 결정적 순서로 최대 100개 원본을 검사했다. 역할 점수가 높은 첫 성부에서 12개의 연속 단선율 attack, 한 박자, 첫 음 downbeat, 짧은 쉼표, 첫 6음 내 3개 이상 pitch, 삭제 후보 근거를 요구한다.
- 3/4: 13 JOURS EN FRANCE, ANGEL, UN DI FELICE. 나머지 7곡은 4/4. 목표했던 6/8 후보는 선별 범위 내 엄격 조건을 통과하지 못했다. 6/8 성능 검증은 이번 결과로 주장하지 않는다.
- 12음의 prefix 8음/6음을 사용한다. 세 길이 모두 같은 네 번째 음을 ±1/±2반음 변경한다. source별로 +1/-1/+2/-2를 번갈아 적용한다.
- 삭제는 첫 6음 내부의 약박·짧은 순차진행 passing/neighbor 후보 하나다. 앞뒤 음의 강박/상대 길이 근거를 보존한다. 확정 화성/셴커 분석이 아니다.
- 삭제 음가도 제거해 이후 onset이 당겨진다. 12/8/6음의 삭제 변형 실제 입력은 11/7/5음이며 최소 입력 조건을 지킨다.
- 후보 품질을 통과한 원형만 고르는 편의 표본이다. 90개는 독립 음악 90개가 아니라 10곡의 paired 조건이며, 무관한 곡 정답 라벨이 없으므로 false-positive rate를 계산하지 않는다.

## 평가 기준

원곡 1위 유지가 필수는 아니다. 확인 가능한 Top5·Top10은 긍정적으로 평가하고 원형부터 미회수인지, 변형 때문에 Top10 밖으로 내려간 것인지 구분한다. 원본 파일 회수와 같은 작품의 다른 파일, 반복 대표 구간과 실제 대응 음, 실패/timeout/재시도를 분리한다. 상위 후보의 순위 정당성은 숫자만으로 단정하지 않는다.

## 재현 및 자료

- 생성: node scripts/build-short-query-suite.mjs (기존 batch 덮어쓰지 않음)
- 실행: MUSICANOTE_SINGLE_OMISSION=1, MUSICANOTE_VISIBLE_RANKING=0; node scripts/run-structural-next40.mjs evaluation/reports/short-query-90-v1/suite.json evaluation/runs/short-query-90-v1
- 오류만 재시도: node scripts/retry-double-ornament-trial.mjs short-query-90-v1
- 보고/포장/검증: node scripts/report-memory-variation.mjs short-query-90-v1; node scripts/package-memory-variation.mjs short-query-90-v1; node scripts/audit-evaluation-bundle.mjs short-query-90-v1
- 정본: evaluation/reports/short-query-90-v1/suite.json 및 selection.json 해시
- 독립 케이스: evaluation/exports/short-query-90-v1/ — Query·수정 근거·XML·event snapshot·전체 응답·순위·문제·개선안. 10곡 × 3길이의 snapshot 30개를 공유한다.
- 페이지: http://127.0.0.1:5173/evaluation/reports/short-query-90-v1/index.html

계속 보존할 개선안: [통합 보류 목록](search-evaluation-improvement-backlog.md).

## 사용자 검토 기준 보충 (2026-09-17)

- 6→5음 삭제는 큰 변형이므로 미회수를 핵심 실패로 삼지 않고 스트레스 관찰로 보존한다. 8→7음은 경계 사례로, 전부 회수해야 하는 것은 아니지만 Top10 0/10의 경로는 진단한다. 원시 결과/순위는 바꾸지 않는다.
- 8→7음은 반환 100개 내 4건: SH01 38위, SH05 74위, SH08 73위, SH10 33위. SH02/03/06/07/09는 candidates에 원본이 없고, SH04는 후보 평가 후 low-information-floors에서 제외됐다. 후보 탈락의 세부 원인은 추가 감사 대상이다.
- 최근 세 배치 185회는 4/4 158회, 3/4 27회다. 3/4는 원곡 3개 × 길이 3개 × 조건 3개이며 독립 원곡 27개가 아니다. 전체 역사적 테스트의 분포라고 일반화하지 않는다.
- 다음 계획(미실행): 새로운 3/4 원곡 10개 × 12/8음 × 원형/삭제 후 시간 축소/삭제 음가를 앞 음에 흡수하여 뒤 onset 유지 = 60회. 검색 전에 원형을 선정하고 삭제 근거·음가·박자 위치를 보존한다. 시간 유지 조건도 앞 음 음가가 바뀌므로 순수 음높이 삭제로 해석하지 않는다.
- 평가 기준은 user-review-policy.json으로 독립 export에 보존한다. 운영 로직 개선은 계속 보류한다.

## 최종 결과

90개 모두 실행 완료. 최초 시간초과 2건(SH01-L12-original, SH06-L8-original)은 별도 재시도에서 모두 완료했으며 최초/재시도 응답을 함께 보존했다. 아래는 원본 source 파일 기준이며, 이 표본에서는 Top5와 Top10 수가 같았다.

| 원형 길이 | 조건 | Top5 / Top10 | 반환 100개 안 회수 |
|---:|---|---:|---:|
| 12 | 원형 | 10/10 | 10/10 |
| 12 | 한 음 높이 변경 | 10/10 | 10/10 |
| 12 | 장식음 삭제 → 11음 | 8/10 | 8/10 |
| 8 | 원형 | 10/10 | 10/10 |
| 8 | 한 음 높이 변경 | 6/10 | 7/10 |
| 8 | 장식음 삭제 → 7음 | 0/10 | 4/10 |
| 6 | 원형 | 9/10 | 9/10 |
| 6 | 한 음 높이 변경 | 2/10 | 2/10 |
| 6 | 장식음 삭제 → 5음 | 0/10 | 1/10 |

SH01-L8-pitch-change는 원본 파일 33위지만 같은 작품 13 JOURS EN FRANCE의 다른 편성이 1–3위다. 작품 회수는 긍정적이며 원본 파일 Top10 미달과 구분한다. 다른 모든 동일 제목을 자동으로 같은 작품이라고 판정하지 않았다.

## 확인된 문제와 정상적인 순위 저하

1. **엄격 통과 조건과 삭제의 충돌:** SH05-L12-ornament-delete, SH09-L12-ornament-delete는 원곡 후보가 평가됐으나 low-information-floors에서 제외됐다. 특히 WAY BACK THEN은 pitch/interval 100, rhythm 약 87.7, coverage 1인데 meter 약 24로 하한 미달이다. 삭제 후 박자 이동·정렬·정책을 함께 검토한다(EVAL-006). 전역 threshold는 변경하지 않았다.
2. **후보 축소에서 누락:** SH03-L8-pitch-change는 hits에는 원곡 stream이 있으나 candidates에서 빠졌다. 정밀 점수 조정보다 후보 축소 단계 감사가 먼저다(EVAL-007).
3. **잘못된 반복 구간 선택:** SH02-L6-original(ANGEL)은 원형 그대로인데 원곡이 반환 100개에 없었다. 정확한 137마디/인덱스249 대신 같은 음정·다른 리듬의 131마디/인덱스232를 평가했다. 실제 원형 음가는 인덱스와 XML에서 일치한다. 대표 창 선정과 결과 제한을 따로 검토한다(EVAL-008).
4. **정상적인 순위 저하도 있음:** SH01-L8-ornament-delete는 38위지만 상위 10개가 별도 수치 감사에서 음정·음가·onset 비율을 모두 만족한다. 이런 경우 원곡 우선 고정보다 더 긴 특징적 입력을 유도하는 편이 타당하다.
5. **Exact 과대분류 재확인:** SH05-L8-ornament-delete 앞의 Exact 일부는 공통 템포 정규화 후에도 0.25박 음가/onset 차이가 있다. 앞서 보류한 EVAL-001과 같은 분류 문제로 모았다.

## 추가 감사와 검증 범위

- 완료 응답에서 각 Query의 상위 10개 이내 Exact 후보 총 297개를 독립 감사했다. 공통 조옮김·중앙값 템포 정규화 후 실제 duration/onset을 비교하며 오차 허용은 Query 박 단위 1/64다. 78개가 추가 검토 대상으로 표시됐다. 이는 반복 후보를 포함한 진단 수이며 오탐률/법적 판단/정확도 확률이 아니다. 상세 검색 Exact 옵션의 회귀 전체를 검증한 것도 아니다.
- 자동/수동 관찰 37개 케이스를 review.json에 기록했다. 정상적인 다른 판본 회수와 순위 저하도 포함되므로 37개를 오류 수로 읽으면 안 된다.
- 90개 Query의 변형 수·길이·쉼표·삭제 근거 검증 통과. case schema·독립 bundle 참조·MusicXML/event SHA256 검증 통과. 반환 alignment의 잘못된 인덱스 참조 0건.
- 비교 악보 180개 생성 및 SVG ID 확인. 낮은 음역은 기존 자동 bass clef 선택을 사용한다. 전체 화면/청각에 대한 사람의 검토는 남아 있다.
- 이 표본의 원형에는 저음 성부와 반주형도 포함된다. 사람에게 친숙한 주선율만의 성능으로 해석하면 안 된다. 3/4 세 곡·4/4 일곱 곡이며 6/8은 미검증이다.
- 운영 검색 알고리즘·점수·DB는 변경하지 않았다. 개선안은 모두 보류하며, 1위 강제나 특정 작품 boost는 추가하지 않았다.

추가 진단 재현: node scripts/audit-short-exact-results.mjs; node scripts/review-short-query-results.mjs. strict-exact-audit.json, review.json 및 suite 검증은 독립 export에도 포함된다.
