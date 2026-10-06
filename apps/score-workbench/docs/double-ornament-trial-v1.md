# 장식음 두 개 삭제 파일럿 — 2026-09-16

## 최종 결과: v2

최종 기준은 [v2 보고서](../evaluation/reports/double-ornament-trial-v2/REPORT.md)와 같은 폴더의 suite.json, results.json, index.html이다. 아래 v1 계획은 변경 이력으로 보존한다.

| 조건 | 검색 완료 | 원본 파일 Top5 | 원래 구간 회수 |
|---|---:|---:|---:|
| 원형 16음 | 7/7 | 7/7 | 7/7 |
| 장식음 1개 삭제 | 7/7 | 7/7 | 7/7 |
| 장식음 2개 삭제 | 7/7 | 7/7 | 6/7 |

v1의 일부 원형이 긴 쉼을 포함해 14마디까지 벌어지는 것을 확인했다. 검색 성적과 무관하게 최대 쉼 1박, 총 길이 24박 이하라는 입력 품질 조건을 추가해 v2를 만들었다. 최종 7개는 모두 서로 다른 원본 파일, 4/4, 떨어진 장식음 두 개다. 연속 두 음은 조건을 만족하지 않아 시험하지 않았다. 기둥음을 확정한 것이 아니라 약박·짧은 음가·경과/보조 형태로 보수적으로 선별한 후보다.

가장 무도회(ORN04-delete2)는 원형 6–10마디 대신 반복 구간 22–26마디가 1위다. 보존된 14음의 음높이와 음가가 대응하며 onset은 모두 64박 뒤다. 따라서 곡 찾기는 성공이나 지정한 원래 위치 회수 지표에는 실패로 남긴다.

현재 검색 로직을 그대로 사용했다. 두 음 삭제 전용 규칙이나 특정 곡 우대는 추가하지 않았다. 사전 보류 기준(70% 미만 또는 20%p 하락)에 해당하지 않으므로 장식음 두 개 삭제 시나리오를 배제하지 않고 회귀 사례로 보존한다. 7개 편의 표본이므로 짧은 Query, 연속 삭제, 복합박자까지 성공한다고 일반화하지 않는다.

실행 결과는 evaluation/runs/double-ornament-trial-v2에 있다. 21개 중 8개는 동일 엔진·DB fingerprint와 의미적으로 동일한 Query를 확인한 v1 실행 결과를 재사용하고 13개를 새로 실행했다. reuse.json과 각 결과에 출처를 남겼다. 최종 오류·시간초과는 없고 재시도도 0개다. 중단된 v1 결과는 삭제하지 않는다.

재현: 새 출력 디렉터리로 build-double-ornament-trial.mjs 실행 → MUSICANOTE_SINGLE_OMISSION=1, MUSICANOTE_VISIBLE_RANKING=0으로 run-structural-next40.mjs 실행 → report-double-ornament-trial.mjs에 batch 이름 전달. 최종 보고서 재생성은 node scripts/report-double-ornament-trial.mjs double-ornament-trial-v2.

## 초기 v1 계획 (최종 수치 아님)

요청: 기둥음 삭제를 제외하고 장식음 두 개 삭제를 실제 검색. 성공률이 크게 떨어지면 범위 확장을 보류한다. 이번 작업은 현재 검색 검증이며 신규 검색 로직 개발은 포함하지 않는다.

## 선별

- 이전 XML 감사20곡을 입력 풀로 사용. 검색 결과를 보지 않고 XML만으로 선별.
- 동일 part/staff/voice, 실제 XML 박자, diatonic pitch의 2도 순차진행 사용.
- 원형16음, 두 음 삭제 후14음. 실제 쉼표 보존. 2/4,3/4,4/4,6/8,9/8,12/8 지원, 변박/불명 박자 제외.
- 타이·cue·grace·겹침, XML→색인 좌표 중복/불명확한 경우 제외.
- 삭제음: 약박(metricSupport<0.5), 길이<=0.5박, 주변 음보다 길지 않은 경과/보조 형태. 주변 음에 강박 또는 상대적으로 긴 음가 근거가 적어도 하나 있어야 한다.
- 떨어진 두 음은 각자 경과/보조음 근거를 가지고 인덱스 간격>=3. 연속 두 음은 네 음 사이 같은 방향 2도 진행.
- 조건을 만족한9개 원형(떨어진7, 연속2). 한 곡에서 두 유형이 가능해 독립 작품9개는 아님. 목표수량을 위해 조건을 완화하지 않았다.
- 화성/사람 분석 없는 잠정 장식음 후보. 확정 Schenker 분석이나 기둥 판정으로 부르지 않는다.

## 시간과 통제

삭제 음표의 음가도 제거해 후속 음을 당긴다. 기존 쉼표는 보존한다. 원형의 약박음을 삭제해도 Query의 후속 박 위치가 달라진다. 기둥 도착 시각까지 보존하는 연주상의 축약은 별도 시험이다.

원형/첫 장식음 삭제/두 장식음 삭제 총27 Query. MUSICANOTE_SINGLE_OMISSION=1, MUSICANOTE_VISIBLE_RANKING=0. 제한60초, top100. 오류와 미회수를 구분한다.

## 재현과 보존

1. `node scripts/build-double-ornament-trial.mjs evaluation/reports/double-ornament-trial-v1` (새 경로만 허용)
2. 위 환경변수를 설정한 뒤 `node scripts/run-structural-next40.mjs evaluation/reports/double-ornament-trial-v1/suite.json evaluation/runs/double-ornament-trial-v1`
3. `node scripts/report-double-ornament-trial.mjs`

suite.json에 원형·Query·삭제음·XML 좌표·문맥·원본SHA256·색인 타임라인 연결을 보존한다. runs에는 전체 검색 응답과 후보 탈락 trace, manifest에는 DB파일 크기/수정시각과 엔진/suite 해시를 기록한다. 보고서는 sourceId 파일 회수, 정규화 제목 후보, 동일 workId에서 원형 보존음 onset/pitch80% 이상 대응하는 구간 회수를 구분한다. 제목만으로 동일 작품을 확정하지 않는다.

검색 전 판단 기준: 원형 회수 성공 사례에서 두 음 삭제 회수가70% 미만 또는20%p 이상 하락하면 전용 지원 개발을 우선순위에서 보류. 작은 편의 표본으로 통계적 일반화하지 않는다. 시간초과 재시도는 별도 기록한다.

최종 수치: [실험 보고서](../evaluation/reports/double-ornament-trial-v1/REPORT.md). index.html에서 원형·삭제1·삭제2 악보와 삭제 대상 표시, 부드러운 합성음을 확인한다.
