# 다중 진행의 목표 화음과 해결 근거

HARM-DEV-20260930-12 · 2026-09-30 · `progression-resolution-0.1.0`

## 목표·기존 이론 연결

다음 단계 승인에 따라 기존 `applied_chords.hypothesis`, `seventh_context.chord`, `harmony_catalog_resolution.project/keys_checked`의 이론 계약을 다중 path에 연결했다. 새 교재 독해나 모든 적용화음 인식 완성을 뜻하지 않는다. 이전 catalog 간 비교의 보수적 직접 해결 조건은 유지하되 더 뒤에 오는 목표 가설도 별도 기록한다.

## 규칙과 데이터 계약

1. 후보의 명시적 근음·철자로 V/V7/vii/vii7/vii_half7의 음집합과 일치하는지 검사한다. 표시 라벨/음계 밖 음의 존재만으로 판단하지 않는다. 목표는 장/단3화음 core를 갖는 후보이며 전위는 이 관계의 필수 조건이 아니다.
2. 전체 path를 빈틈없이 검증하고 하나의 공급된 성부 연결 가정을 유지한다. 역행/중복 분기/시간상 닿지 않는 연결을 거부한다. 실제 악보의 모든 성부를 새로 연결하는 모듈은 아니다.
3. 이끎음은 목표 근음으로 실제 반음+상행2도,7음은 목표 후보의 구성음으로 실제1~2반음+하행2도인지 검사한다. 같은 pitch의 재타격 연쇄는 source refs와 함께 보존한다.
4. 출발 화음의 마지막에 핵심음들이 실제 지속하고, 도착 시작에 근음/3음이 실제 관측되며, 필요한 진행이 모두 인접 경계에서 성립하고 blocker가 없을 때만 `direct_resolution_supported_hypothesis`로 표시한다. 이것도 기능 확정은 아니다.
5. 늦게 도착한 해결·중간 구간을 거친 목표는 근거를 버리지 않고 arrival/경유 path를 기록하되 이번 직접 해결 조건으로 승격하지 않는다. 미관측은 반증/벌점으로 쓰지 않는다. shape만 맞거나 준비/해결이 불충분하면 `shape_relation_only`, blocker가 있으면 `blocked_context`다.
6. 국소 조성이 주어지지 않으면 목표 상대적 관계만 기록한다. 출처가 명시된 별도 조성 가설이 있을 때만 기존 projection을 통해 `V7/IV` 등의 조건부 기호를 낸다. 조표를 조성으로 확정하거나 primary/secondary·전조·종지를 자동 확정하지 않는다.

event IDs, source/target candidate refs, path indices, exact spans, 성부 가정, 실제 도착 시각, 부족한 direct relations, key 가정 출처를 보존한다. 출발/목표 및 중간 후보의 보류 사유도 유지한다. 근음 없는 과거 compact 후보는 추정 복구하지 않는다.

## 코드와 테스트

- `src/musicanote_harness/harmony_progression_resolution.py`: 다중 경로의 관계와 실제 진행 근거.
- `src/musicanote_harness/harmony_progression_evidence_trial.py`: 선택적 `--resolution`; 기존 기본 동작 유지.
- `tests/test_harmony_progression_resolution.py`:15개 테스트.

검사 내용: V/V7/vii 직접 형태·해결, 감7/반감7 형태,7음의 잘못된 진행, 무연결 가정, 지연 도착 보존, 중간 path 경유의 비승격, 조옮김 불변, 출처 있는 조성 projection, blocker, legacy root, 동음이명 철자 반례, 잘못된 성부 연결 거부, 원입력 불변. 전체1,677테스트 통과. 구성 fixture의 성공은 실제 작품의 정확도 결과와 구별한다.

## 실제 표본 재실행

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_progression_evidence_trial --source output/harmony-progression-context-2026-09-30-r4 --output output/harmony-progression-resolution-2026-09-30-r1 --resolution
.venv/Scripts/python.exe -m unittest discover -s tests -q
```

새 output으로 재실행한다. run-contract의 코드 hash, source report 및 각 표본 hash, 기존 source-snapshot/IR/event refs 체인으로 추적한다. 기존 표본·주석·경로를 변경하지 않았다. 개발 train 표본이며 독립 평가 아니다.

총13표본 중5개의 저장 기술 path를 검사했다. K281-3 sample16에서 형태 관계3개가 나왔으며 모두 shape-only다. K280-1 sample0/16/32/64는 해당 기술 path의 관계0개다. 전체 직접 해결 지지0개를 실패율/정답률/세컨더리 부재로 해석하지 않는다. 경로 자체가 첫 보류 없는 후보의 기술적 조합이고 선택된 성부도 일부이므로 실제 정답 화음·전체 성부를 포괄하지 않는다.

5개의 관계 검사+기존5벡터+3동일 구성음 비교=13기술 실험이다. 별도7표본은 적격 저장 path 없음,1개는 baseline 보류로 남겨 제외를 명시한다. Beethoven 표본에서 실제 양성 검증이 된 것은 아니다. 정답 주석은 계산 입력으로 읽지 않았다.

## 한계와 다음 우선순위

- 이번 ordinary family 검사는 exact spelled set을 사용한다. extended/증6을 일반 V7로 억지 축약하지 않으며 기존 전용 공급기와 후속 연결해야 한다.
- 목표 onset/출발 terminal의 동시음 조건은 보수적이다. 분산형·지연/회피 해결은 근거가 있어도 이번 gate에서는 보류될 수 있다.
- sampled 성부 연결이 이끎음과7음의 서로 다른 성부를 함께 포함하지 못할 수 있다. 다음은 실제 양성·반례에서 전체 성부 연결 범위와 후보 가설을 점검하는 것이 우선이다. 무조건 조건을 완화하지 않는다.
- 형태/개수/자기일관성만으로 개선율을 보고하지 않는다. 실제 의미 검증 후에 경로 순위·화면/운영 적용을 결정한다.

운영5173/기존8822화면/구조 분석/Core/원주석 미변경. API 호출·GitHub 업로드 없음. 사용자에게 새 음악적 판정을 요구할 단계는 아직 아니며, 실제 검토가 필요한 지점에서는 전체 악보와 함께 요청한다.
