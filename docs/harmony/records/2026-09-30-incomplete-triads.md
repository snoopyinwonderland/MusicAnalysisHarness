# 불완전3화음의 명시적5음 생략 가설

HARM-DEV-20260930-21 · 2026-09-30 · `incomplete-triad-hypotheses-0.1.0`

## 목적

앞선 세 구간 비교에서 F–A만 관측되어 막힌 경우를, C라는 실제 음표를 만들지 않고 **불완전 화음의 생략 가설**로 표현한다. 특정 작품/pitch/마디에 맞춘 예외가 아니다. 모든 ordinary major/minor triad에 같은 규칙을 사용한다.

이번 단계는 새로운 음악적 증거를 발견한 것이 아니라, 기존 관측으로 가능한 가정을 명시적으로 저장하는 것이다. 가정의 도입과 정확도 향상은 다르다.

## 일반 규칙과 제한

1. 후보가 철자로 정확한 장/단3화음이어야 한다. 근음과3음이 실제 관측되고, 미관측 구성음이 완전5도 음 하나일 때 `ordinary_fifth_omission_assumption`을 기록한다.
2. `assumed_missing_pitch`, `assumed_quality`, `observed_required_members`를 별도로 저장한다. 기존 `missing_members`를 지우지 않으며 sound/note/rest/attack을 추가하지 않는다. `virtual_events_created=false`, `assumption_is_evidence=false`다.
3. 기존 blocker나 반복 bass chain 이외의 비구성음이 있으면 이 가설을 조건부 세 구간 비교에 넣지 않는다. 생략 가설로 비화성음 설명까지 면제하지 않는다.
4. 근음/3음/복수 구성음의 누락, 증·감화음의 특징적5음,7화음/확장화음의 생략은 이번 좁은 모델 밖이다. 미지원 후보를 삭제하거나 음악적으로 불가능하다고 판정하지 않는다.
5. 같은 interval에서 실제 관측된 구성음 집합과 남는 비구성음 refs가 같은 reading들을 `observationally_equivalent_reading_indices`로 보존한다. 표시 라벨/선호 근음/원주석을 쓰지 않는다. F–A는 장3화음과 증3화음 등을 구별하기에 부족하다.
6. 기존 strict clean 그룹과 새 가설 그룹을 별도로 저장한다. `omission_comparison`의 가능한 조합과 가정 의존 조합 수를 구분한다. 원 strict status/clean count/기존 판정은 불변이다.
7. 장/단3화음5음 생략 가설이 비교 가능하다고 해서 그 quality가 다른 후보보다 우세하다는 뜻은 아니다. `quality_confirmed=false`, `omission_confirmed=false`, `pedal_confirmed=false`, `joint_voice_assignment_verified=false`, `selected=null`을 유지한다.
8. 후속 검증은 경쟁 quality/근음, 전후 화음과 실제 성부의 공동 일관성이다. 아직 확률/순위/최적 경계/기능/종지를 계산하지 않는다.

## 구현·검증

- `src/musicanote_harness/harmony_incomplete_triads.py`: ordinary triad5음 가정, 관측상 구별 불가능한 후보 목록, strict/assumption 그룹 분리.
- `harmony_missing_evidence_trial.py`: 선택적 `--incomplete-triads`; 다른 audit flag와 동시 선택 금지. 기존 고정 source/계획/IR hash 및 권한 검사 재사용.
- `tests/test_harmony_incomplete_triads.py`: 신규13 / 전체 **1,779테스트 통과**. 장/단·조옮김, 근음/3음/복수 누락·증감/7화음 보류, blocker/다른 비구성음 보존, 증화음 경쟁 후보 보존, 라벨 무관, strict 결과·원입력 불변, 완전 화음에 불필요한 생략 가정 금지를 검사했다.

Core/원주석/기존 strict gate/운영5173/구조 분석/8822화면 불변. 외부 AI/API/학습/GitHub 업로드 없음.

## 고정 실행

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_missing_evidence_trial --source output/harmony-distributed-resolution-2026-09-30-r1 --ir-source output/harmony-shared-context-2026-09-30-r1 --output output/harmony-incomplete-triads-2026-09-30-r1 --incomplete-triads
.venv/Scripts/python.exe -m unittest discover -s tests -q
```

기존13표본/보류2개/관찰 반복 chain2개를 유지했다. 이전 모든13분할을 그대로 비교했다.

| 표본 | 조건부 결과 |
|---|---|
| K280-1 sample16,10분할 |1분할은5음 생략을 명시적으로 가정하면 비교 가능,9분할은 여전히 부족|
| K280-1 sample32,3분할 |3분할 모두 여전히 부족|

**strict clean 양성은 여전히0**이다. 새 조건부 분할1개/조합1개는 가정 아래의 가능성이며, 신규 정답/독립 실제 양성/정확도 향상이 아니다. 계산 가능한 가설의 범위가 늘어난 것이다.

## 실제 가설과 경쟁 후보

K280-1 `reviewm_6fb07c245142d9e0421f`, sample16, global quarter 경계7/8:

- `[6,7)`, edge1/reading0: `open_85626bdc812c130dbed0`. F와 A는 관측, C는 미관측. F–A–C 후보의5음 생략을 가정한다.
- 같은 edge의 reading1(F–A–C♯), reading2(F–A–C–E♭), reading3(F–A–C–E)도 현재 관측만으로 구별되지 않음을 보존했다. 이 모델은 그 후보들의 생략 해석을 아직 지원하지 않으므로 지지 없음이 곧 기각은 아니다.
- `[7,8)`, edge12/reading1: E–G–B♭가 관측되며 F3 반복이 후보 밖에 남는다. F3를 자동 NCT/페달로 면제하지 않는다.
- `[8,9)`, edge19/reading7: F–A–C–E♭가 관측된다. 앞의 가정된 C와 뒤의 실제 C를 같은 관측으로 합치지 않는다.

조건부 그룹은 `[[0],[1],[7]]`, 생략 가정 그룹은 `[[0],[],[]]`다. 기존 status는 `membership_return_shape_only`, `clean_combination_count=0`으로 그대로다.

결과: `output/harmony-incomplete-triads-2026-09-30-r1/reviewm_6fb07c245142d9e0421f/16.json`. 원 IR: `output/harmony-shared-context-2026-09-30-r1/real-cases/reviewm_6fb07c245142d9e0421f/source-snapshot/candidate_revision_ir.json`. 실제 sound refs는 동일 결과의 geometry/upper_cells 및 고정 lattice를 참조한다.

## 다음

실험 계층 유지. 이 조건부 진행을 실제 성부 변화·준비/해결과 대조하고, 같은 관측을 설명하는 경쟁 후보를 같은 기준으로 비교해야 한다. 단지 지원 모델이 먼저 구현된 ordinary triad를 우승으로 삼지 않는다. 정확한 해석이 여전히 경쟁하면 그때 전체 악보 위에 대안을 표시해 사용자 검토를 요청한다.
