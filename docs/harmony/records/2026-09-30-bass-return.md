# 반복 베이스의 세 구간 복귀와 상성부·경쟁 해석

HARM-DEV-20260930-20 · 2026-09-30 · `bass-return-comparison-0.1.0`

## 목표와 범위

사용자의 다음 단계 승인에 따라, 두 구간만으로는 확인할 수 없었던 반복 베이스의 앞·중간·뒤 membership을 비교한다. 단순 페달 인정이나 최적 화음 선택이 아니라 **후보 진행별 관측 근거를 분리 저장**하는 실험이다.

기존 원음표·주석·직접 해결·시간 해결 gate·운영5173·구조 분석·기존8822화면은 변경하지 않는다. 외부 AI 호출/학습/GitHub 업로드 없음.

## 일반 규칙

1. 이전의 같은 part/voice·철자·옥타브·연속 release/onset·지속 중 최저음 조건을 통과한 반복 chain을 그대로 사용한다. 원 IR 일치를 먼저 검증한다.
2. 관찰된 chain 범위 안의 attack/release grid에서 **가능한 모든 두 경계 조합**을 계획한다. 각각 앞/중간/뒤3구간으로 완전히 덮는다. 한 chain당256분할 한도 초과시 일부를 고르지 않고 보류한다.
3. 각 구간의 모든 reading은 원출처/index·철자·누락음·비구성음·blocker와 함께 보존한다. membership상 베이스가 구성음→비구성음→구성음인 조합을 별도 그룹으로 기록한다.
4. `clean_membership_return_possible`의 좁은 관측 조건: 각 후보 구성음이 실제로 모두 관측되고, 반복 chain 이외에 설명 안 된 음이 없고, 기존 blocker가 없다. 중간의 베이스는 여전히 비구성음으로 남아 있으며 NCT 면제하지 않는다. 이것은 생략 화음/장식이 있는 음악이 틀렸다는 조건이 아니다.
5. 후보 조합은 좌/중/우 index 그룹으로 저장한다. 모든 조합을 객체로 펼치지 않는다. 조합 수는 세 그룹 크기의 곱이며 확률/신뢰도가 아니다. 전체 voice/NCT assignment의 양립을 아직 증명한 것이 아니다.
6. 동일 세 구간에서 베이스를 계속 구성음으로 포함하는 대안과, 동일 전체 범위를 한 화음으로 덮는 대안을 유지한다. 큰 화음 집합이 음을 더 많이 포함한다고 승자로 고르지 않는다.
7. 모든 셀의 반복 bass sound refs와 그 밖의 sound refs/철자 집합을 저장한다. “그 밖의 음”은 최상성부 하나를 고른 멜로디가 아니라 bass chain 이외의 실제 음 전체다. 성부나 음표를 지우지 않는다.
8. 관찰 chain이 부모 문맥 양끝에 닿으면 전체 반복의 시작·끝은 미확인이다. membership 복귀 형태가 있어도 음악적 페달의 준비/해결, 기능·조성·종지까지 확정하지 않는다.

## 구현과 검증

- `src/musicanote_harness/harmony_bass_return.py`: 전체 분할 계획, 구간별 후보 표 재사용, 세 구간 후보 그룹, 실제 다른 성부 셀, 한 화음 대안.
- `harmony_missing_evidence_trial.py`: `--bass-return` 추가. `--repeated-bass`와 동시 선택은 거부. 원 snapshot/계획/출력 provenance 검증 재사용.
- `tests/test_harmony_bass_return.py`: 신규11 / 전체 **1,766테스트 통과**. 합성 membership 복귀, 누락음/다른 비구성음/blocker 반례, 모든 구간 구성음일 때 잘못된 페달 형태 금지, 전체 합집합 화음 자동 선택 금지, 다른 음표 보존, 출처 대안 보존, 예산 보류, 입력 불변, 다른 IR 거부.

## 고정 실행

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_missing_evidence_trial --source output/harmony-distributed-resolution-2026-09-30-r1 --ir-source output/harmony-shared-context-2026-09-30-r1 --output output/harmony-bass-return-2026-09-30-r1 --bass-return
.venv/Scripts/python.exe -m unittest discover -s tests -q
```

13표본 중 기존 baseline 보류1 / pair 예산 보류1을 유지했다. 나머지11표본 중2개에서 앞서 관측한 반복 chain이 있었다. grace timing 문제가 해결됐다는 뜻은 아니다.

| 표본 | 관찰 범위 | 모든 세 구간 분할 | 결과 |
|---|---|---:|---|
| K280-1 sample16 |global quarter `[6,9)`|10|membership 복귀 형태9, 형태도 없음1|
| K280-1 sample32 |global quarter `[12,14)`|3|membership 복귀 형태3|

총13분할 중12개는 형태 후보 조합이 있으나 `clean` 조건을 통과하는 조합은0이다. 나머지1개는 membership 복귀 형태도 없다. 이는 후보 관측 조건 결과이며 페달의 정답률/오답률이 아니다. 합성 양성은 통과했지만 실제 musical gold 검증은 아직 미완료다.

## 실제 막힌 지점

`reviewm_6fb07c245142d9e0421f`(Mozart K280-1) sample16의 두 경계 global quarter7,8을 예로 들면:

| 구간 | 실제 관측과 해당 후보 | 부족한 근거 |
|---|---|---|
| `[6,7)` |F3 반복, F/A 관측. F–A–C 후보(edge1/reading0)|C 미관측. F–A–C♯ 후보도 존재하므로5음 철자를 직접 관측했다고 할 수 없음|
| `[7,8)` |E–G–B♭ 후보(edge12/reading1)는 모두 관측. 반복 F3만 후보 밖|F3의 페달 역할 미확정; 기능/성부 해결 공동 검증 필요|
| `[8,9)` |F–A–C–E♭ 후보(edge19/reading7)는 모두 관측|이 후보를 최종 선택한 것은 아니며 local key/기능 미검증|

이 분할의 clean reading 수는 앞0 / 중간1 / 뒤1이다. 앞의 F–A를 불완전한 F화음으로 볼 여지는 있으나 현재 실험은 구성음을 발명하지 않아 보류한다. augmented/다른 불완전 화음 가능성, 다른 경계, 넓은 관찰 문맥도 남는다. 특정 곡이므로 F major로 하드코딩하지 않는다.

재현: `output/harmony-bass-return-2026-09-30-r1/reviewm_6fb07c245142d9e0421f/16.json`. `chain_comparisons[0].comparisons`에서 cut_times7/8, `interval_tables`의1/12/19를 확인한다. bass chain 시작 ref `sound_a4786aed9e98`, 전체6개 원 sound refs는 geometry에 있다. 원 IR은 기존 `harmony-shared-context-2026-09-30-r1/real-cases/reviewm_6fb07c245142d9e0421f/source-snapshot/candidate_revision_ir.json`에 고정되어 있다.

## 결정과 다음 단계

세 구간 비교를 실험 계층에 유지하며 화면/운영에 승격하지 않는다. 다음은 **불완전 화음·구성음 생략을 별도 가설로 표현**하는 것이다. “5음이 없으니 언제나 생략”이 아니라 관측 근음/3음/7음, 생략한 음의 역할, 경쟁 quality, 전후 실제 진행과 근거를 따로 보존해야 한다. 생략 가설로 후보 수가 늘어났다는 사실을 정확도 향상으로 계산하지 않는다. 이어 NCT/페달/해결의 공동 성부 대응과 전체 문맥을 검증한다.
