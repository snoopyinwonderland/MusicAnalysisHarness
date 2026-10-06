# 명시적 여러 성부의 해결 근거

HARM-DEV-20260930-13 · 2026-09-30 · `progression-resolution-0.2.0`

## 문제와 일반 규칙

이끎음과7음이 서로 다른 성부에 있을 때, 이전 sampled assignment만으로는 둘의 해결을 함께 보지 못할 수 있다. 다음 단계 승인에 따라 기존 `harmony_reading_voice_context.voice_links`를 다중 경로 해결 계산에 연결했다. 추가 교재 독해/전체 성부 추론 완성을 뜻하지 않는다.

1. 원 IR을 선택적으로 입력한다. context에 겹치는 sounding event 집합, pitch/span/source-note refs가 저장 경로의 events와 일치해야 한다. 다른 악보나 다른 revision의 ID를 끼워 넣지 않는다.
2. 실제 part/voice ID별로 다음 음이 하나뿐이고 source와 target에 중첩 음이 없으며 시간상 직접 닿는 연결만 사용한다. 같은 voice가 staff를 옮기는 것은 연결 단절 근거가 아니다.
3. 한 XML voice에 chord notes가 겹치거나 후속음이 모호하면 보류한다. 가장 가까운 음을 임의로 고르거나, 누락된 voice를 sampled assignment로 채우지 않는다.
4. sampled 연결과 explicit-IR 연결은 합집합이 아니다. 같은 path를 각각의 근거 범위에서 따로 계산해 비교한다. 원 NCT assignment와 후보/음표는 바꾸지 않는다.
5. 추가 연결의 출처/part/voice/span, 보류 event와 사유를 보존한다. explicit IR voice도 원 XML과의 동일성이 별도로 검증된 음악적 성부라고 선언하지 않는다. 기존 모듈의 `xml_voice_identity_verified=false`, `contrapuntal_voice_identity_confirmed=false`를 유지한다.

## 변경 파일

- `src/musicanote_harness/harmony_progression_resolution.py`: 선택적 keyword `ir`, identity 검사, 별도 link scope 및 diagnostics. 기존 호출 호환 유지.
- `src/musicanote_harness/harmony_progression_evidence_trial.py`: `--ir-source`; source hash/자료 권한 검증 후 추가 비교. 기존 모드 그대로.
- `tests/test_harmony_progression_resolution.py`: 기존 fixture의 선택적 IR 반환만 추가.
- `tests/test_harmony_progression_multivoice.py`:8개 검사.

## 검증

합성 양성: C7→F에서 E→F와 B♭→A가 서로 다른 명시적 성부로 움직이면 두 진행이 함께 지지된다. 같은 path에서 무연결 sampled 가정은 shape-only로 남는다. 이 비교는 연결 범위 차이를 검증하며 음악적 정답률이 아니다.

반례/보존: 잘못된7음 방향, 모든 음을 한 다성 XML voice에 넣은 경우, voice 누락, 같은 voice의 cross-staff, 다른 pitch IR 거부, 누락 sound 거부, 원입력 불변. 전체1,685테스트 통과.

초기 합성 양성2개가 실패한 이유는 이전 fixture의 수동 B♭→A 연결과 XML voice 번호가 달랐기 때문이다. 원 fixture는 수동 assignment 테스트로 그대로 두고 새 explicit-IR fixture에서 도착 A/C의 voice 번호를 교정했다. 실제 소스 악보를 고치거나 알고리즘 조건을 느슨하게 바꾼 것이 아니다.

## 실제 표본과 실행

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_progression_evidence_trial --source output/harmony-progression-context-2026-09-30-r4 --output output/harmony-progression-multivoice-2026-09-30-r1 --resolution --ir-source output/harmony-shared-context-2026-09-30-r1
.venv/Scripts/python.exe -m unittest discover -s tests -q
```

재실행 때는 새 출력 폴더를 쓴다. run-contract/code hash/source artifact hash와 각 결과의 원 IR 경로/hash를 저장했다. IR 입력은 기존 source-snapshot/manifest의 train·internal research 권한과 파일 hash를 검사한다. 원주석을 추론 입력으로 읽지 않았다.

| 표본 | 명시적 연결 수 | 다성 source voice 보류 | context 밖 후속음 보류 | 목표 관계 |
|---|---:|---:|---:|---|
| K281-3 sample16 |9|2|3|3개 모두 shape-only|
| K280-1 sample0 |1|10|1|0|
| K280-1 sample16 |2|16|1|0|
| K280-1 sample32 |2|12|1|0|
| K280-1 sample64 |3|0|2|0|

연결17개는 실제 해결17개가 아니다. 보류42+8은 event 관측 수이며 표본 간 중복 가능성이 있다. 추가 성부를 보았어도 직접 해결 지지0개다. 선택 경로가 기술적 조합이고 다성 voice·도착 timing 제약이 있어, 기능 부재/오답률로 읽지 않는다.

18기술 실험=기존5벡터+3동일 구성음 비교+5sampled 해결+5explicit 해결이다. 총13표본 중7개는 저장된 적격 path 없음,1개 baseline 보류로 여전히 제외된다. Beethoven 표본의 실제 양성 해결 검증은 이번에도 없다. 합성 양성은 통과했지만 실제 해결 양성 목표는 아직 미완료다.

## 판단과 다음 과제

이 단계에서 검사 가능한 성부 범위는 넓어졌으나 음악적 정확도 향상을 주장할 수 없다. 다음은 다성 XML voice 안에서 여러 음을 어떻게 대응시킬지에 대한 보수적인 복수 연결과 지연 도착 근거, 그리고 실제 해결이 있는 양성/반례의 경로 검증이다. 정답과 맞도록 연결을 하나 고르거나 직접 해결 조건을 일괄 완화하지 않는다.

Core/원주석/운영5173/구조 분석/기존8822화면은 변경하지 않았다. 외부 AI·학습·GitHub 업로드 없음. 이번에 사용자에게 새로운 음악적 판단을 요청하지 않으며, 실제 검토 대상이 마련되면 전체 악보로 제시한다.
