# 근음·조건부 전위·지속 베이스 역할

HARM-DEV-20260930-11 · 2026-09-30

## 목표와 설계

사용자의 다음 단계 승인에 따라 R06을 연결했다. 기존 후보 catalog의 `spelling_alternatives[].root_spelling`은 이미 존재하지만 다중 진행의 compact reading에서 빠져 있었다. 표시 문자열을 해석하거나 구성음의 첫 원소를 근음으로 단정하지 않고 이 필드를 출처와 함께 보존한다.

- compact version: `full-context-progression-0.2.0` (필드 추가).
- bass 모듈: `progression-bass-0.1.0`.
- 관찰 벡터: `progression-evidence-0.1.1` (전위 미계산 상태 문구 정정).
- 원래 catalog/Core schema는 변경하지 않는다. 과거 출력의 근음 미제공은 unknown으로 유지하고 자동 덮어쓰지 않는다.

## 일반 규칙

1. 실제 최저 MIDI 음의 철자를 검증한다. 최저음에 동음이명 철자가 공존하면 하나를 임의 선택하지 않는다.
2. 선택한 후보의 철자상 구성음이 아니면 비구성음 베이스로 보류한다. 장식 베이스·페달·다른 화음 가설을 경쟁 대안으로 둔다.
3. 근음이 명시되고 후보의 구성음 도수가1/3/5 또는1/3/5/7이며 blocker가 없을 때, 최저음의 도수에 따라 기본위치/1/2/3전위 후보를 낸다. 이는 해당 화음과 최저음의 구조적 베이스 역할을 전제로 한 후보이지 확정 화성 아니다.
4. 증6처럼 공급기가 근음을 부여하지 않은 후보는 그대로 근음 미정이다. 확장/비표준 음집합의 전위 기호는 이번에 일반3/7화음처럼 처리하지 않는다. 구성음 철자와 반음 변화는 원후보를 보존한다.
5. 동일 sounding event가 문맥 안에서 계속 최저음으로 유지되고 서로 다른 구성음 집합을 가진 진행을 지나 비구성음 상태가 생기면 지속 베이스 역할 후보를 기록한다.
6. 전체 sound가 관찰 문맥에 포함되고 양 끝은 구성음, 중간은 비구성음이면 `anchored_sustained_bass_shape`로 표시한다. 상성부 기능·진행 대조가 미확인이라 페달로 확정하지 않는다. 준비/복귀가 없거나 잘린 문맥이면 unresolved다. 피아노 sustain pedal을 추론한 것도 아니다.
7. 부분 평가 범위를 요청해도 지속음 문맥 검사는 전체 context에서 하며, 평가 범위와 겹치는 후보만 보고한다. 단일 지속 sound 범위만 지원하고 재타격/내성/상성부 페달은 후속이다.

## 변경 파일

- `src/musicanote_harness/harmony_progression_context.py`: 근음/출처 보존; 근음 없는 표시의 안전한 fallback.
- `src/musicanote_harness/harmony_progression_bass.py`: `cell_role`, `analyze`.
- `src/musicanote_harness/harmony_progression_evidence.py`: 별도 전위 계산 모듈과 관찰 벡터 상태 구분.
- `src/musicanote_harness/harmony_progression_evidence_trial.py`: 선택적 `--bass`, 기본 replay 동작 유지.
- `tests/test_harmony_progression_bass.py`:13개 테스트.

## 검증과 실행

테스트:3화음 각 전위,7화음3전위, 증6/근음 미제공, 확장음집합, 비구성음 베이스, blocker, 동음이명 비구성음, legacy근음, 같은 화음 지속의 비검출, 입력 불변, member→nonmember→member 양성 형태, 복귀 없는 반례, 표시 라벨과 독립적인 공급기 근음 전달. 전체1,662개 통과; 마지막 상태 문구 수정 후 진행 관련38개 재통과.

초기 검사는 근음 없는 후보의 label fallback을 두 인자로 호출해 기존 테스트 mock의 세 인자 계약과 충돌했다. 명시적 세 번째 인자 `None`을 넘기도록 수정했다. 음악적 판정 실패와 구별한다.

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_progression_context_trial --source output/harmony-shared-context-2026-09-30-r1 --baseline-source output/harmony-boundary-figures-2026-09-30-r2 --output output/harmony-progression-context-2026-09-30-r4
.venv/Scripts/python.exe -m musicanote_harness.harmony_progression_evidence_trial --source output/harmony-progression-context-2026-09-30-r4 --output output/harmony-progression-bass-2026-09-30-r2 --bass
```

새 출력 폴더로 재실행한다. r4는 이전13표본 계획을 동일 방식으로 재생성해 근음을 보존했다(12 ready/1 baseline 보류). bass r1은 관찰 벡터에 남아 있던 ‘근음 계약 없음’ 문구를 바로잡기 전 출력이며 보존했다. r2가 최종이다. plan/run-contract/source hash와 각 표본의 정확한 span/event/candidate refs를 보존한다. 주석 정답은 후보 생성/계산에 사용하지 않는다.

실제 replay는 이전과 같은5기술 path에서 시행했다. K281-3 sample16은7셀, K280-1 sample0/16/32/64는3/6/4/3셀이다. 총23셀 중15셀은 조건부 전위 후보,8셀은 비구성음 베이스 보류다.5개 bass 계산+이전5벡터+3동일 구성음 비교=13개 기술 실험이며13곡 정답 검사가 아니다.

7표본은 적격 저장 경로 없음,1표본은 baseline 보류 상태를 유지한다. Beethoven02-3의 이번 실제 경로 검증은 없다. 지속 베이스 형태 후보는 이5개 경로에서0개였으며, 페달 부재나 탐지 정확도로 해석하지 않는다. 합성 양성 검사는 있으나 실제 페달 양성·반례 검증은 남았다. 경로 자체가 기술적 가정이므로 전위 후보15개를 정답15개로 보고하지 않는다.

## 남은 일과 적용 상태

다음은 기능·목표화음 해결을 조건부 경로에 연결하고, 실제 페달 양성/반례와 후보 부족을 검증하는 것이다. 반복 attack 페달, 근음 생략의 신뢰도, 국소 조성, 구조적 베이스 선택, 최종 순위는 미완료다.

운영5173/구조 분석/원주석/Core/악보 화면은 그대로다. 기존8822화면에는 이번 계산이 추가되지 않았다. 외부 AI 호출·GitHub 업로드 없음. 사용자에게 새로운 음악적 정답 판단을 요구하는 단계는 아직 아니다.
