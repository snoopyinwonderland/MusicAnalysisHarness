# 유형별 검토 Harness — 파일럿

## 목적과 범위

반복음, 순차진행, 분산화음 유사형, 혼합 도약의 연속 8음 구간을 이전 후보의 전체 성부 스냅샷에서 선별한다. 분산화음 유사형은 음정 모양을 뜻하며 실제 화성/모티프라는 사람 판정이 아니다. 띄엄띄엄 음표를 고르지 않는다.

유형당 3개를 요청하고 확인된 canonical 작품, 그 외 title+artist 샘플링 키로 같은 유형 안의 작품 중복을 줄인다. 이 키는 선별용일 뿐 검색 결과 병합에 쓰지 않는다. 자료가 모자라면 부족한 수를 그대로 보고한다. 같은 작품이 서로 다른 유형에 쓰이는 것은 허용한다.

현재 모집단은 한 업로드의 후보 30성부이므로 전체 corpus의 대표 표본이 아니다. 각 유형의 원형/반음 수정/옥타브 이동이 서로 다른 원형에서 만들어지므로 완전한 paired A/B가 아니다. 추후 paired 변형 및 다양한 작품 모집단으로 확대해야 한다.

## 증거 보존

`suite.json`에 Query 전체, 원래 음표 8개, 앞뒤 최대 2마디의 논리 이벤트, source/work/stream, snapshotId, 유형, 변형 및 humanReview를 보존한다. 마디 ordinal이 없으면 앞뒤 8개 attack 문맥임을 명시한다. 스냅샷의 논리 음은 원본 MusicXML의 레이아웃/타이 인쇄 형태를 완전히 복제하는 자료가 아니다. 기존 원본 snapshot과 source를 함께 유지한다.

`humanReview`의 검토자·원본 회수 필요성·선호 후보 ID·순위 이유·음악적 기능은 null/unreviewed로 둔다. 사람이 판정하지 않은 것을 자동으로 전문가 라벨로 올리지 않는다. `knowledgeBase.classification`과 `ruleLearning`으로 일반 사례 형식에 연결한다.

각 검색은 60초 worker 제한, top 20, 결과 전체와 오류를 사례별 JSON에 보존한다. sourceRank는 해당 파일의 회수 순위다. sourceWindowRank는 같은 indexed stream에서 원래 attack 하나 이상이 alignment에 포함되는 첫 순위일 뿐 전체 구간/붉은 음표 정확성 검사가 아니다. 다른 판본이 대신 검색돼도 원본 source 미회수로 나올 수 있으므로 음악적 실패 판정에는 추가 검토가 필요하다.

## 재현

```powershell
node scripts/run-preclearance-review-suite.mjs evaluation/runs/preclearance-importance-worker-2026-09-15.json evaluation/runs/NEW-review-suite --max-cases=4
node scripts/summarize-preclearance-review-suite.mjs evaluation/runs/NEW-review-suite docs/NEW-review-summary.md
```

기본 max-cases는 12다. 이번 실행은 유형별 원형 1개씩 총 4개를 먼저 검색하고 나머지 8개는 미실행으로 명시한다. 디렉터리는 새 경로여야 한다. index 지문/코드 지문을 기록한다. 강제 종료하면 summary가 없을 수 있지만 이미 저장한 사례별 파일은 유지된다. 운영 resume는 아직 없으므로 다른 새 경로로 실행한다.

## 2026-09-15 실행 기록

- 관련 테스트 43개 통과.
- 초기 `preclearance-review-12-2026-09-15`는 동일 작품 편성 중복이 많아 중단했다. 첫 반복음 Query의 timeout과 원래 suite는 보존했다. 완료된 benchmark로 취급하지 않는다.
- 개선 선별 `preclearance-review-diverse-2026-09-15`는 유형당 3개, 총 12개 Query를 보존했다. 원형 4개 검색을 파일럿으로 실행했다.
- 첫 반복음 Query에서 60초 timeout을 재현했다. 이 경우 회수 순위는 알 수 없으며 검색 성능 문제로 분리한다.
- 최종 실행 결과는 연결된 파일럿 요약과 summary.json에서 확인한다. 전체 악보 렌더링, A/B 전문가 선호 및 새 12개 Query의 corpus 빈도 재측정은 아직 수행하지 않았다.

최종 파일럿: [Query와 실행 결과](preclearance-review-pilot-2026-09-15.md). 4개 중 3개(반복음·순차진행·분산화음형)는 각각 60초 timeout. 혼합 도약형은 55.32초에 완료, 원본 source와 원래 구간 attack이 포함된 결과가 3위였다. index 지문은 실행 전후 동일했다. 나머지 8개는 미실행이다. 네 원형이 모두 ENDLESS LOVE에서 선별되어 장르/작품 일반화 검증은 아니다.

따라서 다음 작업은 짧고 흔한 Query의 후보 회수·정렬·구조 보강 시간 분리 계측이다. timeout을 회수 실패나 유사도 품질 저하로 단정하지 않고 원인을 확인한다. 기존 search-api의 profile은 완료 시 반환되므로 timeout 이전의 진행 지표를 저장하는 진단 경로가 필요하다.

이 단계는 개선 효과의 입증이 아니라 재현 가능한 진단/사람 검토 자료 생성이다. 다음은 timeout의 후보량/정렬 시간을 프로파일링하고, 전문가 라벨 없이 순위를 임의 조정하지 않는 것이다.
