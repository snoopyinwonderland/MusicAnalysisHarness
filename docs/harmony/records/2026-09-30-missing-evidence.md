# 구성음 누락 위치와 조건부 비화성음 근거 감사

HARM-DEV-20260930-18 · 2026-09-30 · `missing-evidence-audit-0.1.0`

## 목적과 구현

사용자가 승인한 다음 단계: 직전 분산·지연 실험의 보류를 원인별로 구별한다. 새로 조건을 완화하거나 화음을 확정하는 작업이 아니라, 어떤 음·범위·가설이 부족한지 재현 가능하게 만드는 진단이다.

- `src/musicanote_harness/harmony_missing_evidence.py`: 원 IR 일치, 저장 profile 재계산 일치, 후보 출처/범위 일치 검사. 구간 밖의 구성음과 저장 NCT 음형의 후보별 조건을 대조한다.
- `src/musicanote_harness/harmony_missing_evidence_trial.py`: 고정 입력/계획/IR hash와 train/internal 권한을 검사하고 별도 결과 저장. 실행 후 입력 불변 확인.
- `tests/test_harmony_missing_evidence.py`: 신규 13개 / 전체 Python **1,743개 통과**. 기존 layout warning만 있으며 실패 없음.

Core/원주석/직접 해결/시간 해결 gate/운영5173/기존8822화면은 변경하지 않았다. 외부 AI 호출, 학습, GitHub 업로드 없음.

## 일반 진단 계약

### 구성음

후보 구간의 관측되지 않은 철자 구성음을 근음/3음/5음/7음 역할로 구분한다. 근음 철자를 기준으로 하므로 조옮김에 같은 규칙을 적용한다.

1. `available_elsewhere_in_parent`: 같은 부모 문맥에는 있지만 해당 후보 구간 밖에 있는 음. 원 sound refs와 실제 span을 보존한다. 인접 화음의 음일 수 있으므로 경계 확장/병합을 허가하지 않는다.
2. `not_observed_in_parent`: 제한된 부모 문맥에도 없는 음. 실제 생략, 문맥 절단, 잘못된 후보 등을 **아직 구별하지 못한 상태**다. `omission_confirmed=false`를 유지한다.

부모 범위를 넘어 전곡에서 같은 pitch를 찾아 화음 근거로 가져오지 않는다. 미관측음을 만들어 내거나, 5음/3음/근음 누락을 동일하게 면제하지 않는다.

### 비화성음

기존 전체 문맥의 조건부 음형 중 대상 음과 시간 범위가 겹치는 것을 참조한다. 다음을 확인한다.

- 모든 requirement의 sound/assignment ID가 존재하고 requirement 시간이 해당 sound 안에 있는가.
- 두 후보 구간과 겹치는 모든 requirement에서 요구한 구성음/비구성음 상태가 실제 철자 membership과 같은가.
- pair 바깥의 화음 문맥이 필요한가. 바깥 조건을 버려서 통과시키지 않는다.
- 기존 계류 등의 보류 조건이 남아 있는가.
- 비구성음의 전체 음가를 설명하는지, 일부 시간만 설명하는지.

결과는 `membership_conflict`, `requires_external_candidate_context`, `withheld_conditions`, `conditional_pattern_compatible`로 분리한다. 호환 결과도 실제 NCT 확정이 아니며, supporting assignment refs를 보존한다. 서로 다른 assignment에서 나온 음형을 합쳐 하나의 성부 해석으로 선언하지 않는다. 이 작업은 새로운 다성 NCT 검출기를 구현한 것이 아니다.

## 실행과 결과

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_missing_evidence_trial --source output/harmony-distributed-resolution-2026-09-30-r1 --ir-source output/harmony-shared-context-2026-09-30-r1 --output output/harmony-missing-evidence-2026-09-30-r1
.venv/Scripts/python.exe -m unittest discover -s tests -q
```

기존 13표본 계획을 보존했다. 실행된 1,847관계 중 profile이 있는 1,722관계를 감사했다. 125관계는 이전의 grace timing 미지원120/기존 blocker5로 profile이 없어 미감사. 8,699관계 예산 보류 및 baseline 보류1표본은 재해석하지 않았다. 7개 처리 표본은 대상 관계가0이었다.

| 진단 | 수 |
|---|---:|
| 구간 밖 부모 문맥에 있는 구성음 |1,494|
| 부모 문맥에도 없는 구성음 |2,584|
| 누락 역할: 근음 / 3음 / 5음 / 7음 |13 / 1,952 / 831 / 1,282|
| 후보별 비구성음 instances |11,338|
| 겹치는 저장 음형이 없는 비구성음 instances |8,226|
| 음형 대조: membership 충돌 |4,965|
| 음형 대조: 바깥 화음 문맥 필요 |803|
| 음형 대조: 조건부 호환 |550|

수치는 **후보 관계·좌우 구간별로 중복될 수 있는 instances**다. 고유 음표 수/독립 사례 수/정답 수가 아니다. 550개 호환을 550개 화음 해결 성공이나 신규 NCT 확정으로 계산하지 않는다. 관측되지 않은 구성음은 총4,078 instances이며 역할별 합과 일치한다. 미관측이 단순 5음 생략만으로 설명된다고 볼 수 없다.

결과 artifact SHA-256을 모두 재확인했다. `git diff --check` 오류 없음(기존 CRLF 안내만 있음); 새 미추적 파일의 실행 검증은 위 테스트가 담당한다.

## 실제 후속 대상: 반복 베이스와 경쟁 화음

`reviewm_6fb07c245142d9e0421f`(Mozart K280-1), sample16, 부모 global quarter `[6,9)`:

- 양쪽 후보 구성음이 모두 관측된 관계76개를 별도로 확인했다.
- 76개 모두 출발 후보의 비구성음에 F3가 있고, 출발 비구성음 중 적어도 하나는 전체 음가를 설명하는 호환 저장 음형이 없다.
- 반복되는 F3의 refs에는 `sound_a4786aed9e98`(`[6,13/2)`)와 `sound_7bae7121eca4`(`[13/2,7)`) 등이 있다. 원음표를 삭제하지 않는다.
- 첫 진단 관계는 source edge2/reading1 (`open_f9e1fb12df8661942954`), target edge16/reading19이며 source span `[6,15/2)`, local pair `[6,17/2)`다. 이 관계를 음악적 정답으로 선정한 것은 아니다.

재현 파일: `output/harmony-missing-evidence-2026-09-30-r1/reviewm_6fb07c245142d9e0421f/16.json`. 원 IR: `output/harmony-shared-context-2026-09-30-r1/real-cases/reviewm_6fb07c245142d9e0421f/source-snapshot/candidate_revision_ir.json`. 전체 구성음/대안 읽기는 고정 `harmony-progression-context-2026-09-30-r4`의 해당 표본을 함께 참조한다.

현재 확인한 것은 “F3가 후보 밖에 남는다”는 사실이지 “F3가 페달이다”라는 결론이 아니다. 다음은 일반 규칙으로 **동일 성부·동일 pitch의 반복 베이스 흐름**, 주변 구성음/비구성음 전환, 베이스를 구성음으로 포함하는 경쟁 화음, 중간에 다른 화음이 섞였을 가능성을 함께 검사한다. 임의의 sustained/repeated bass를 비화성음으로 면제하지 않는다. 별도로 조건부 NCT assignment와 해결 assignment의 공동 일관성, 생략 화음/문맥 절단 판정이 남는다.
