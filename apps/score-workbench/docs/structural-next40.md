# 구조 변형 후속 40개: 단일 삭제와 추가 치환

2026-09-16. 사용자 요청: 직전 변형에 한 개 변형을 추가한 검색, 음 한 개를 완전히 삭제한 검색을 수행하고 일반 규칙을 보완한다.

## 고정 실험

같은 원본 20개로 2유형씩 생성했다. 원래 음의 가운데 인덱스 floor(n/2)를 고정 선택하며 실패 결과에 따라 위치를 고르지 않는다.

- delete-one 20개: 원래 가운데 음을 duration까지 삭제. 뒤 음들이 당겨지고 기존 쉼표는 유지된다. 삭제 음이 기존 analyzerInferredIds에 있는지를 기록한다.
- combined-plus-one-semitone 20개: 직전 combined(경과/보조 삽입) Query에 해당 원래 음 +1반음 추가. parentCaseId와 기존/추가 변형을 모두 기록한다. 기둥 후보였더라도 제외하지 않는다.

`evaluation/reports/structural-next40-v1/suite.json`에 원본 Query, 새 Query, source context, 삭제/변경 상세, 원음 대응을 보존한다. 이번에는 보존 기둥 자체가 달라지는 반례도 포함되므로 직전의 기둥 보존 100개와 같은 난이도/정답 가정을 하지 않는다.

## 실행 상태와 재현

```powershell
node scripts/build-structural-next40.mjs evaluation/reports/structural-next40-v1
node scripts/run-structural-next40.mjs evaluation/reports/structural-next40-v1/suite.json evaluation/runs/structural-next40-baseline-v1
```

첫 명령은 새 폴더만 허용한다. 두 번째는 동일 fingerprint에서 재개 가능하며 결과를 덮어쓰지 않는다. 원 검색 코드/DB를 변경하지 않은 baseline이 진행 중이다. 최종 상태는 summary.json.remaining으로 확인한다. top100, 60초 제한, 실패도 개별 파일로 보존한다. 이 문서 작성 시 8/40건 완료: 삭제 2/4 회수, 추가치환 0/4 회수. 이는 중간 통계이며 최종 수치가 아니다.

현재 미회수 6개 모두 expected work의 초기 hit는 있고 상세 candidate에는 없었다. 같은 source의 다른 stream까지 없다는 의미로 확대하지 않는다. 상세 점수 가중치만 높이는 방식으로는 이 expected stream을 회수할 수 없다.

## 구현한 보완 후보 (production 미적용)

`server/single-omission.mjs`: 8–48음 Query가 단 하나의 전체 조옮김/템포 비율 아래에서 candidate의 내부 attack 하나를 제외한 모든 pitch와 음가 및 도착 간격에 일치해야 한다. 복수 생략/추가 치환/임의 옥타브 등치는 허용하지 않는다. 생략음이 기둥 후보일수록 비용을 높인다. sparse 구조 축약이 아닌 누락 입력 가설이며 exact로 승격하면 안 된다.

`server/single-omission-seeds.mjs`: 기존 interval-3 posting 근거 중 서로 겹치지 않는 두 Query 구간이 후보에서 정확히 한 음만큼 위치 차이를 보일 때 추가 후보를 제안한다. 전체 60개/작품당 2개 기본 제한, 새 DB 조회 없음. 단독으로 일치를 확정하지 않는다. 이 후보 cap/순위의 실제 recall과 오탐은 아직 미검증이다.

두 모듈 테스트 9개 통과: 전체 조옮김/템포, 유지 음가, 두 음 삭제 차단, 추가 오음 차단, 쉼표 치환과 구별, 반복음/동시음 혼합 차단, 기둥 생략 비용, 후보 위치 연결과 상한.

`scripts/diagnose-single-omission.mjs`로 원 구간을 직접 준 진단은 삭제 20/20을 인식했다. 기존 sparse gate는 이 직접 구간 정렬 중 2개를 차단했다. 이것은 강제 원 구간 비교이며 전체 DB 회수/순위 향상의 증거가 아니다. 진단 결과는 suite 폴더 `forced-span-diagnostic.json`에 저장했다.

## 다음 검증 및 주의

### 개선판 40개 완료 및 전후 악보 공개

개선판40개 완료: 음삭제19/20 회수(모두top5), 추가치환2/20 회수. timeout0. 기존 baseline은 음삭제12/20(1timeout 포함), 추가치환2/20이었다. 이전 성공이 미회수로 바뀐 사례0, 명확한 미회수→회수6, 기존 timeout→회수1. 음삭제가 모두 해결된 것은 아니며 추가치환 문제는 그대로다. 캐시/실행 순서가 다르므로 개별 지연 차이를 속도 개선율로 단정하지 않는다.

사용자 요청: 검색된 것/안 된 것을 악보로 표시하고 추가30개 테스트. `scripts/export-omission-ab.mjs` 및 `evaluation/reports/omission-ab-review-v1/index.html` 생성. 40개 카드마다 원본·변형Query·baseline·실험 결과를 나란히 표시한다. 원곡 미회수 시 다른 곡의1위 결과임을 명시한다. baseline timeout은 실패로 구분한다. 총159개 악보 렌더링/표시ID 검증 성공, 출력오류0. 일부 원XML 발췌에서 열린 tie/slur 경고가 있어 모든 곡선 표기의 완전성이나 청취 QA를 보증하지 않는다.

현재20개+첫holdout10개와 정규화 제목이 겹치지 않는 다른10곡으로 추가30개(원형/삭제/삭제+추가오음)를 만들었다. `evaluation/reports/omission-holdout2-v1/suite.json`에 저장, 직접 원 구간 mechanism 진단30개 통과. 추가30개 전체 검색은 첫holdout30개의 baseline/ON 종료 후 순차 실행 대기다. 첫holdout baseline은 실행 시작을 확인했다. 생성과 검색완료를 혼동하지 않는다.

순차 명령: `node scripts/run-omission-holdout-ab.mjs omission-holdout2 omission-holdout-enabled-v1`. 이번 추가30개는 전에 요청한30개와 별개이며, 각각 기존/개선판으로 검색하므로 추가60회 실행이다. 웹 서버 기본 기능은 여전히 OFF.

### 2026-09-16 추가 검증 승인과 진행

사용자: 테스트를 더 하고 괜찮으면 적용. 기존 baseline 40개는 종료: delete-one 12/20 회수(19완료, B06삭제 1 timeout), combined-plus-one-semitone 2/20 회수(20완료). timeout을 미회수와 같은 원인으로 단정하지 않는다.

실험 연결을 `MUSICANOTE_SINGLE_OMISSION=1`에만 활성화했다. 기본값 OFF이며 현재 웹 서버 설정은 바꾸지 않았다. 이 경로는 정확 검색 옵션, contour/rhythm 검색, low-information Query에서는 꺼진다. 기존 상세 정렬보다 좋은 단일 누락 정렬이 있을 때만 선택하고 strict 검증 완료 경로에 한하여 sparse gate를 통과시킨다. 기존 나머지 점수/허용 기준은 유지한다. 단일 누락 설명을 why에 추가하며 exact로 처리하지 않는다.

기존 검색 API 및 새 모듈 테스트 76개 통과. 동일40개 개선판은 `evaluation/runs/structural-next40-omission-v1`에서 실행 중. 완료 여부는 summary.remaining으로 확인한다.

추가로 처음20개와 정규화 제목이 다른 원본10개를 이전350/300/200/100 테스트 자료에서 선택했다. 원형10, 중간음삭제10, 삭제+다른음3반음변경10의 총30개. `evaluation/reports/omission-holdout-v1/suite.json`에 원본/변형/문맥 보존. 이는 새로운 음악 전문가 정답이나 완전히 새로운 데이터셋이 아니라 이번 튜닝 표본과 분리한 검증용 자료다. 판본/동명이곡 identity는 제목보다 엄밀한 후속 검토 필요.

추가30개 직접 원 구간 진단은 기대대로 통과: 삭제10만 single-omission으로 인식하고 원형10/추가오음10은 그 경로로 인식하지 않음. 일반 유사 검색에서는 추가오음 음악도 결과로 나올 수 있으며 그 사실만으로 오탐이라고 하지 않는다.

`scripts/run-omission-holdout-ab.mjs`는 앞40개 개선판 종료 후 추가30개를 baseline/실험 ON으로 순차 실행한다. 동시에 큰 DB worker를 여러 개 띄워 지연/메모리를 왜곡하지 않는다. 오류 시 원인을 기록하고 자동 배포하지 않는다. 생성기 최초350 자료만으로10곡 확보 실패 후 범위를 과거 자료 전체로 넓혀10곡 확보했다; 원본 점수로 선별하지 않았다.

적용 게이트: 삭제 회수 개선, 원형 정확검색 회귀 없음, 추가오음에 strict single-omission 설명이 붙지 않음, 비관련/반복음 후보 폭증 없음, p50/p95 및 timeout 비교, 실제 검색 정렬·색칠 검토. 모든 실험 종료 전 기본 ON으로 바꾸지 않는다. 두 번 이상 편집된 combined 변형 문제는 별도이며 이번 한 음 누락 모듈로 해결했다고 주장하지 않는다.

baseline 종료까지 검색 엔진을 변경하지 않는다. 이후 feature flag OFF 기본으로 제한형 후보 + 정렬 경로를 통합하고 동일 40개 A/B를 실행한다. 기존 exact/반복음/띄엄띄엄 오탐 반례를 회귀 검사한다. 새 경로를 아직 사이트에 적용하지 않았고, 40개 검색도 문서 작성 시 완료하지 않았다.

추가치환 실패는 단일 삭제 모듈만으로 해결되지 않는다. 변형에 따른 후보 근거 분산을 먼저 분석한다. 특정 작품 ID/title이나 원하는 순위는 검색 규칙에 사용하지 않는다. 이후 악보 검토 페이지에서도 변경음/삭제 위치와 실제 검색 구간을 분리해서 보여 준다.
# 최종 적용 상태 — 2026-09-16

사용자 승인으로 한 음 삭제 대응은 기본 ON으로 전환했다. 아래의 기본 OFF 설명은 과거 실험 시점 기록이다. 환경변수 MUSICANOTE_SINGLE_OMISSION=0으로 비활성화할 수 있다. Exact/rhythm/contour/저정보량 제외 조건은 유지한다.

삭제 총40개: 기존 회수25(Top5 25, timeout1), 개선 회수35(Top5 34, timeout0). 원형20개 회수20 유지. 삭제+다른음변경20개 회수1 유지. 지정 원본 파일 기준이며 작품 전체 정답률이나 검색된 구간의 음악적 타당성까지 확정한 수치는 아니다.
