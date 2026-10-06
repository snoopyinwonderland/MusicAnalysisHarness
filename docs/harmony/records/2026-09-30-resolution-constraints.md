# 전체 성부 조합을 펼치지 않는 해결 관계 제약 검사

HARM-DEV-20260930-15 · 2026-09-30 · `resolution-constraints-0.1.0`

## 목표와 범위

이전 단계에서 실제5표본 중4개가 전역 대응 조합 한도에 걸렸다. 다음 단계 승인에 따라 **하나의 직접 해결 관계에 필요한 연결들이 공동으로 가능한가**를 검사한다. 전곡의 최적 성부/화음 진행을 계산하는 것은 아니다.

원 IR과 저장 events의 identity 검사를 유지한다. part/voice가 불명확하면 보류한다. 유효한 같은 lane의 음표들 중 끝 시각과 시작 시각이 일치하는 모든 링크를 생성하며, 이 graph 생성에는 음높이 근접도·화성 라벨·정답 주석을 쓰지 않는다.

## 계산 원리

1. 기존 화음 path에서 철자 기반 V/vii 관계와 대상 구간을 가져온다. 후보 blocker·인접성·출발 말단/도착 첫 시점의 동시음 전제를 먼저 검사한다.
2. 각 직접 해결 요구(이끎음→목표 근음,7음→목표 구성음 하행)에 해당하는 실제 링크를 graph에서 조회한다. 이는 화성 가설에 대한 질의이며 graph 자체나 실제 성부를 그 화성에 맞춰 바꾸는 것이 아니다.
3. 요구별 링크를 동시에 선택할 수 있는지 검사한다. 하나의 source가 서로 다른 target으로 분기하거나 여러 source가 같은 target으로 병합되면 허용하지 않는다.
4. 양립 가능한 대응이 있으면 그 링크만 포함하고 나머지 음은 고립 track으로 남긴 완전한 부분 대응을 만든다. 모든 음표를 한 번씩 보존하는지 확인하고 기존 resolution 모듈로 다시 검사한다.
5. 이 대응은 **존재 가능성을 증명하는 예**이지 추천/실제 대응이 아니다. 무연결 대안이 여전히 존재하므로 후보 개수를 확률로 해석하지 않는다.

부분 대응 모델에서는 나머지 링크를 선택할 의무가 없다. 따라서 요구 링크들이 분기/병합 없이 유효하면, 나머지 음들을 잇지 않는 확장이 항상 가능하다. 이것이 전체 경계·lane 조합을 열거하지 않아도 되는 이유다. 단, 모든 성부를 끝까지 연결해야 한다는 추가 조건이나 지연/겹침/교차-lane 연결 모델에는 이 결론을 그대로 적용하지 않는다.

질의별 증명 대응은 서로 다를 수 있다. 하나의 전곡 해석으로 합치려면 별도의 공동 일관성 검사가 필요하다. 현재는 관계별 존재성만 답한다.

## 보류와 계약

- 상태: `witness_exists`, `no_compatible_witness`, `query_budget_abstention`, `direct_identity_prerequisite_missing`, `nonadjacent_direct_query_not_applicable`, `blocked_context`.
- 전역 입력 보류: 위치 미정 sound, graph 링크 한도 초과. 양의 음가·ID·동일 원 IR을 검사한다.
- graph 링크 기본 한도8,192, 질의 탐색 검사 기본 한도4,096. 한도 초과는 거짓이 아니라 미정이다. 전체 대응 수에 따른1,024/256 제한을 재사용하지 않는다.
- 어떤 직접 해결 증거도 없다는 것은 기능 자체의 반증이 아니다. 지연 해결·분산형·다른 화음 path는 이 질의 밖이다.
- span/event refs, 요구별 가능한 링크, 증명 track, 기존 판정기 재검사 결과를 남긴다. `selected_assignment=null`, 확률 미계산, 기능 미확정.

## 구현과 검증

- `src/musicanote_harness/harmony_resolution_constraints.py`: graph 및 관계별 공동 링크 검사.
- `src/musicanote_harness/harmony_progression_evidence_trial.py`: 선택적 `--constraints`, 원 IR/hash 검증 재사용.
- `tests/test_harmony_resolution_constraints.py`:11개 검사.

4음→4음 합성 문제의209개 완전 열거와 새 질의의 양성/음성 존재성 결과를 비교했다. 새로운 검사는16개 로컬 링크에서 필요한2개 링크만 증명용 대응으로 연결한다. 동시음 전제가 부족한 반례와, 목표음은 있으나 진행 방향이 틀린 반례를 구별한다.

추가 검사: 기존 전체 열거 한도1에서 보류되던 경우에도 새 정확 질의 가능, merge/branch 충돌 거부, 탐색 한도는 거짓으로 보고하지 않음, graph 한도 초과시 부분 답 금지, lane 누락 보류, lane 간 연결 금지, 원입력 불변. 신규11/전체1,704테스트 통과.

초기 음성 테스트는 `no_compatible_witness`를 기대했으나 실제로 목표3음 자체가 빠져 `direct_identity_prerequisite_missing`이 맞았다. 기대값을 정정하고 목표3음을 유지한 잘못된 진행의 반례를 별도로 추가했다. 판정 조건을 완화하지 않았다.

## 재현과 실제 수치

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_progression_evidence_trial --source output/harmony-progression-context-2026-09-30-r4 --output output/harmony-resolution-constraints-2026-09-30-r1 --resolution --ir-source output/harmony-shared-context-2026-09-30-r1 --constraints
.venv/Scripts/python.exe -m unittest discover -s tests -q
```

새 output을 사용한다. run-contract/code/source/IR hash, 모든 기존 표본 상태 및 실험 결과를 보존한다. 정답 주석을 질의 입력으로 사용하지 않았다.

| 표본 | 로컬 링크 | 관계 질의 | 결과 |
|---|---:|---:|---|
| K281-3 sample16 |11|3|비인접2, 직접 동시음 전제 부족1|
| K280-1 sample0 |15|0|해당 기술 path에 대상 관계 없음|
| K280-1 sample16 |39|0|동일|
| K280-1 sample32 |29|0|동일|
| K280-1 sample64 |3|0|동일|

5표본 모두 graph 계산을 마쳤다. 이전 수백~수천만 전역 대응을 생성하지 않고97개 로컬 링크를 보존했다. 그러나 실제 질의3개 중 직접 해결 존재성 검색까지 필요한 조건을 만족한 것은0개다. ‘모두 계산 완료’는 화성 분석 성공/정확도 개선을 뜻하지 않는다.

전체23기술 실험은 이전18+새5이며, 적격 저장 경로가 없는7표본과 baseline 보류1표본은 제외 상태를 그대로 남겼다. Beethoven의 실제 해결 양성 검증은 아직 없다. first-reading technical probe가 실제 정답 path가 아니라는 제한도 여전하다.

## 다음 판단

직접 해결 질의의 전역 조합 병목은 피할 수 있음을 소규모 대조로 검증했다. 다음에는 첫 후보 경로만 보는 제한을 벗어나 동일 규칙으로 후보 간 관계 범위를 검사하고, 실제 양성·반례 및 지연 도착을 검증해야 한다. 기존 동시음 전제를 무작정 완화하거나 사용자가 준 특정 마디에만 규칙을 추가하지 않는다.

Core/원주석/구조 분석/운영5173/기존8822화면 미변경. 외부 AI·GitHub 업로드 없음. 사용자 음악적 판단은 실제 전체 악보 검토 사례를 마련한 후 요청한다.
