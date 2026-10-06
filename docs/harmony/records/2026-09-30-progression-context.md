# 다중 화음 구간과 전체 문맥 계산

HARM-DEV-20260930-09 · 2026-09-30 · prototype `full-context-progression-0.1.0`

## 문제와 사용자 방향

직전117경계의 주석 진단에서1화음 유지/2화음 분할만으로 비교할 수 없는 내부 변화와 페달 문제가 확인됐다. 사용자는 단순 방식에 한계가 있으므로 더 심층적인 상세 규칙을 먼저 만들고, 필요하면 AI 활용도 고려하도록 요청했다. 개발 해석은 ‘복잡한 조건을 무작정 추가’가 아니라 동일 문맥에서 여러 진행의 근거·반례·불확실성을 비교하는 것이다.

전체 계획은 [상세 추론 규칙](../HARMONY_REASONING_RULES.md)에 분리했다. 이번에 교재를 새로 독해하거나 그 규칙 전체를 운영 엔진에 적용한 것은 아니다.

## 구현

- `src/musicanote_harness/harmony_progression_context.py`: attack/release 격자, 모든 연속 구간의 후보, 철자 대안/원후보 pointer, 전체 문맥 음형과 성부 연결, 여러 구간 path 평가.
- `src/musicanote_harness/harmony_progression_context_trial.py`: 계산 전13표본 계획 고정, 원입력/hash/자료 권한 검사, 저장 및 계약 검사.
- `tests/test_harmony_progression_context.py`:15개 테스트.

관찰 `context_span`, 평가 `evaluation_span`, 가정된 화음 진행 `segments`를 분리한다. 예를 들어 가운데 경과음의 설명은 앞뒤 음표와 그 화음 가정을 참조하되 평가 음가에 외부 음을 더하지 않는다. 모든 경로는 전체 문맥을 빈틈/중복 없이 덮어야 한다. 실제 음표·철자·음가는 Core에서 삭제하지 않는다.

한 셀부터 전체 문맥까지 가능한 연속 구간을 생성한다. 각 구간은 기존 공통 후보 공급기를 동일 전체 문맥으로 호출한다. 후보 조합을 모두 펼쳐 저장하지 않고 구간별 후보와 path 참조를 사용한다.256구간 예산을 넘으면 임의 가지치기 대신 표본 전체를 보류한다. 정답 라벨은 격자/후보 생성에 입력하지 않는다.

NCT는 선택한 성부 연결과 경로의 모든 관련 구간에서 필수 구성음/비구성음 상태가 성립할 때만 조건부 설명으로 활성화한다. 후보 자체에 보류 사유가 있으면 확정 근거처럼 쓰지 않는다. 최종 화음 기능이나 NCT 정답을 선언하지 않는다.

## 재현과 자료

입력은 `output/harmony-shared-context-2026-09-30-r1`, 보관 baseline은 `output/harmony-boundary-figures-2026-09-30-r2`다. 작품별 기존 표본의0,16,32,…번을 선택한13개 pilot이며184개 전체 검사는 아니다. 작품은 Beethoven02-3, Mozart K281-3/K280-1이다. 기존 개발용 train 자료로 독립 평가 집합이 아니다.

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_progression_context_trial --source output/harmony-shared-context-2026-09-30-r1 --baseline-source output/harmony-boundary-figures-2026-09-30-r2 --output output/harmony-progression-context-2026-09-30-r3
.venv/Scripts/python.exe -m unittest discover -s tests -q
```

재실행은 새 output 이름을 사용한다. `plan.json`은 입력 경로/hash·격자·복구 provenance, `run-contract.json`은 코드 hash와 계획 hash, `report.json`은 표본별 상태·산출물 hash를 보존한다. 각 표본 JSON에 음표 refs, 정확한 span, 후보 구성음/보류 및 원공급기 재현 pointer가 있다. compact 후보의 origin pointer는 현재 파일 위치가 아니라 재생성 가능한 원 catalog 위치라는 한계도 기록한다.

## 결과와 해석

| 항목 | 결과 |
|---|---|
| 계획된 표본 |13|
| 후보 생성 ready |12|
| 기존 baseline부터 보류 |1: K281-3 sample0|
| 연속 구간 후보 위치 |227|
| 후보 reading/철자 대안 |6,689|
| 전체 문맥 음형 |31|
| 동일 구성음의 전체/최소 구간 분할 불변 검사 |3 통과|
| 여러 구간의 음가 보존 검사 |5 통과|
| 신규/전체 코드 테스트 |15/1,639 통과|

후보/음형 수는 정답 수가 아니다. 동일 구성음 검사는 공통으로 지원되는 대표 구성음 집합 하나를 사용했다. 음가 검사의 path는 각 최소 구간의 첫 보류 없는 후보를 고른 기술적 probe이며 추론된 화성 진행이 아니다. 일부 표본은 최소 구간에 보류 없는 후보가 없어 이 검사를 실행하지 못했다. 빈 checks를 성공이나 오류로 세지 않는다. 긴 구간의 후보 존재가 모든 짧은 구간의 후보 지원을 뜻하지 않는다.

K281 sample16은7개 셀/28개 구간에서1,163 reading을 생성했고7구간 probe의 음가가 보존됐다. 이것은 이전1회 분할의 표현 한계를 넘는 계산 계약 검사이지, 원주석의 I6→IV→I6→viio6를 자동으로 맞혔다는 뜻이 아니다.

## 실행 중 문제와 보존

- r1: 표본 출력 하위 폴더 생성 누락으로 중단. 생성 처리를 추가하고 실패 출력은 보존했다.
- r2: 이전 단계의 `no_additional_held_boundary` placeholder를 실제 분석 부재로 취급해5 ready/8 보류로 집계. 새 지속음 경계 없음은 이전 분석 없음이 아니다.
- r3: placeholder의 `previous_sample_sha256`와 일치하는 보관 baseline만 복구하고 출처를 계획에 명시.12 ready/1 실제 baseline 보류. 보류를 강제로 후보화하거나 기존 결과를 덮어쓰지 않았다.

## 제한과 다음 단계

현재는 순위 없는 경로 계산기다. 최적 path 탐색, 기능·국소 조성 공동 추론, 페달 역할, 복잡한 다성부 연결, 독립 음악적 정확도는 미완료다. 관찰 성부의 연결 대안을 쓰며 모든 성부 연결을 완전히 해결한 것도 아니다. NCT·화음 후보 공급기의 누락/보류가 후속 경로를 제한한다.

다음은 상세 규칙의 지지/반박/보류 벡터를 경로에 연결하고, 베이스·전위·페달·목표 화음 해결을 각각 검증하는 것이다. 구간을 많이 나누면 구성음 설명량이 늘어나는 편향을 반례로 평가한 뒤 순위/탐색을 도입한다. AI는 필요시 같은 ID·시간·근거 validator를 따르는 후보 비교 보조로 설계하며 이번에는 API 호출·외부 전송·학습을 하지 않았다.

Core/원주석/운영5173/구조 분석은 변경하지 않았다. 새 UI를 만들지 않았으며8822/8824 등 기존 화면은 이전 이분 비교 실험이다. 다중 path 판단이 화면에 적용됐다고 해석하지 않는다.
