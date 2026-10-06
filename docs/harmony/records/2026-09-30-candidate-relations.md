# 임시 경로 밖의 후보 관계 검사

HARM-DEV-20260930-16 · 2026-09-30 · `candidate-relation-survey-0.1.0`

## 목표와 변경 원리

사용자의 다음 단계 승인에 따라 첫 보류 없는 reading을 조합한 기술 path 밖으로 검사 범위를 넓혔다. 이전에 적격 atomic path가 없던 표본도 interval lattice가 ready이면 계획을 만든다.

1. 기존 격자의 모든 왼쪽/오른쪽 연속 구간 중 같은 시점에서 닿는 쌍을 대상으로 한다. 최소 셀뿐 아니라 여러 셀을 합친 구간도 포함한다.
2. 모든 후보의 근음·철자를 사용해 V/V7/vii/vii7/vii_half7 형태와 장/단 목표 core 관계를 계획한다. 동음이명·출처·철자 대안·blocker를 보존한다. 표시 라벨/원주석/특정 작품 번호로 고르지 않는다.
3. 동일 구조의 서로 다른 후보 출처도 각각 보존한다. index로 원격자 edge/reading을 참조한다. 아직 순위나 확률을 계산하지 않는다.
4. 해당 두 구간의 직접 해결만 local context로 검사한다. 후보 공급기는 기존 전체 context에서 생성됐으며 그 출처는 그대로다. NCT·그 바깥 화성 문맥 전체의 적절성을 이 검사로 확정하지 않는다.
5. 모든 계획을 먼저 저장하고 그다음 검사한다. 표본의 pair 수가 실행 예산을 넘으면 부분집합을 정답처럼 고르지 않고 표본 단위로 보류한다.

## 코드와 테스트

- `src/musicanote_harness/harmony_candidate_relation_survey.py`: 형태 기반 전체 계획, local 직접 해결 질의, 보류.
- `src/musicanote_harness/harmony_candidate_relation_trial.py`:13표본 전체 계획 선저장, 원입력/IR hash 및 train/internal 권한 검사, 결과 저장.
- `tests/test_harmony_candidate_relation_survey.py`:8개 테스트.

첫 reading이 아닌 목표 후보 검출, 다른 출처 중복 보존, blocker 보존, 한도 초과시 부분 선택 금지, 표시 라벨 무관, 원입력 불변, 다른 IR 거부,0음가 event refs 보존을 검사했다. 전체1,712테스트 통과. 음악적 정확도는 미측정이다.

## 실행·실패 보존

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_candidate_relation_trial --source output/harmony-progression-context-2026-09-30-r4 --ir-source output/harmony-shared-context-2026-09-30-r1 --output output/harmony-candidate-relations-2026-09-30-r2 --max-pairs 1024
.venv/Scripts/python.exe -m unittest discover -s tests -q
```

기본 pair 예산512에서 시작한 r1은 K281 sample64의0음가 event가 양의 음가를 요구하는 track validator에 걸려 중단했다. 해당 에러만 명시적 미지원으로 분류하도록 수정했으며 원음표를 빼지 않았다. 다른 identity/참조 오류는 계속 에러로 처리한다. r1은 삭제하지 않았다.

r1에서 모든13표본 계획을 먼저 확인했다. r2는 고정 계획을 유지한 채 pair 예산1,024로 실행했다. 성부 대응 수백만 조합을 펼친 것이 아니라, 독립적인 후보 관계892/718개도 처리하기 위한 실행 한도다.8,699개인 큰 표본은 여전히 통째로 보류했다. 예산 확대 자체를 최종 성능 해결책으로 삼지 않는다.

`plan.json`, `run-contract.json`에 계획/코드/source report/IR report hash를 기록했다. 표본별 결과는 원후보/철자 대안/index, local/parent context, event refs, 증명/보류 사유를 보존한다. 표본의 원 IR/source 경로는 입력 결과 및 source-snapshot hash 체인으로 추적한다. 자료는 개발 train 집합이며 정답 주석을 계산에 사용하지 않았다.

## 실제 결과

| 표본 | 계획 관계 | 결과 |
|---|---:|---|
| Beethoven02-3 sample0/16/32 |각0|ordinary-family 대상 형태 없음; 양성 검증 아님|
| K281-3 sample0 |0|기존 baseline 보류|
| K281-3 sample16 |892|동시음 전제 부족892|
| K281-3 sample32/48 |각0|대상 형태 없음|
| K281-3 sample64 |125|0음가 미지원120, 기존 blocker5|
| K280-1 sample0 |0|대상 형태 없음|
| K280-1 sample16 |718|동시음 전제 부족694, 공동 직접 연결 없음24|
| K280-1 sample32 |112|동시음 전제 부족112|
| K280-1 sample48 |8,699|pair 예산 초과, 미검사|
| K280-1 sample64 |0|대상 형태 없음|

총10,546관계 계획 중1,847개를 검사하고8,699개를 보류했다.11표본의 처리는 끝났지만 그중7개는 대상 관계가0개다. baseline 보류1개와 pair 예산 보류1개를 별도 유지한다.

검사1,847개 = 동시음 전제 부족1,698 + 직접 연결 부재24 +0음가 미지원120 + 기존 blocker5. 직접 해결 증명0개. 후보·범위·출처가 겹칠 수 있으므로 관계 수는 독립 화음/마디/곡 수가 아니다. 이 표로 오답률이나 정확도 향상을 계산하지 않는다.

K281 sample16의892개 중 출발/도착 동시음 전제는 false/false586, false/true220, true/false86이다. 첫 후보 하나를 잘못 고른 문제만으로 설명하기 어렵고, 현재의 엄격한 말단/도착 동시음 전제가 핵심 진단 대상이다. 그러나 해당 후보들이 음악적으로 모두 옳다는 뜻도 아니다.

## 0음가 원자료 확인

K281 sample64의 미지원 source events는 아래3개다. 원 IR의 `grace.is_grace=true`를 확인했다. 잘못된 XML로 판정하거나 삭제하지 않는다.

- `sound_e4cba7732e2a` / `note_bb537d261602`: B♭4.
- `sound_5276637dfcfe` / `note_62dee9c4fa9d`: C5.
- `sound_496649e736b9` / `note_fc2f3dbf2882`: D5.

모두 global quarter28에서 start=end이며 grace order0/1/2, anchor_note_id=null이다. performed timing을 발명하지 않는다.120개 미지원 관계는3장식음이 겹치는 여러 범위/후보를 포함한 수치다.

## 다음 설계와 상태

다음은 출발 핵심음/도착 근음·3음이 한 시점에 모두 있어야 한다는 전제를, 분산형/지연 도착의 시간순 지지와 실제 성부 진행으로 검증하는 것이다. 임의의 넓은 창에 있는 음을 모아 조건을 통과시키면 과도한 병합이 되므로 양성·반례를 함께 설계해야 한다. grace timing/anchor 처리, 큰 후보 집합의 동일 계산 재사용도 별도 과제다.

이번에 후보 관계 범위를 넓힌 것은 맞지만 실제 해결 양성·독립 정확도는 아직 미완료다. Core/원주석/구조 분석/운영5173/기존8822화면은 그대로다. 외부 AI·GitHub 업로드 없음.
