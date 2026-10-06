# 다성 XML 표기의 부분 대응과 조합 한도

HARM-DEV-20260930-14 · 2026-09-30 · `progression-polyphony-0.1.0`

## 목표와 일반 규칙

사용자 승인에 따라 하나의 XML voice 안에 동시에 적힌 여러 음의 연결 가능성을 검사한다. 기존 `harmony_voice_paths.observe/partition`과 `harmony_polyphonic_links.partial_matchings`를 재사용한다. 새로운 음표 매칭 원리를 발명하거나 이전 엔진을 교체한 것은 아니다.

- 동일 part/voice 내에서 끝 시각과 시작 시각이 일치하는 음들끼리 가능한 모든 부분 대응을 만든다. 악보의 음높이 거리나 화성 라벨로 순위를 매기지 않는다.
- 일부 음만 잇는 경우, 모두 안 잇는 경우, 고립음을 보존한다. 음표를 branch/merge하거나 누락하지 않는다. 지속하는 sound 자체를 새 attack으로 잘라 잇지 않는다.
- 각 lane의 전체 연결 가설을 결합한 다음, 모든 sound가 정확히 한 track에 남는지 검증한다. 각 가설에 대해 같은 화음 path의 해결 근거를 별도로 계산한다.
- ‘어떤 대응에서는 해결 가능’과 ‘그 대응이 실제 성부’는 다르다. 지지 가설 개수는 확률/투표/정답 수가 아니다. 최적 대응은 선택하지 않는다.
- lane 정보 누락·lane 열거 한도·전체 조합 한도 초과는 보류한다. 일부 후보를 정답처럼 남기지 않는다. 현재 기본 전체 한도256, 기존 lane 한도1,024는 연구용 안전 한도다.

## 변경 파일

- `src/musicanote_harness/harmony_progression_polyphony.py`: 완전 bounded 조합, 보류, 성부 가설별 resolution.
- `src/musicanote_harness/harmony_progression_evidence_trial.py`: 선택적 `--polyphony`; `--resolution --ir-source`가 필요하다.
- `tests/test_harmony_progression_polyphony.py`:8개 테스트.

원 IR과 저장된 events의 identity 검사, 내부 연구 자료 권한/hash 검증은 직전 단계를 재사용한다. 기존 sampled/explicit 결과를 덮어쓰지 않는다. 원주석과 작품명은 매칭에 입력하지 않는다.

## 구성 검사

4음 화음 두 개가 한 voice에 있는 합성 사례에서 가능한 부분 대응은209개다. 모두 계산하고 무연결을 포함하는지, 모든 sound가 각 가설의 track들에 정확히 한 번 존재하는지 검사했다. 일부 대응에서 이끎음/7음 해결이 지지되지만 다른 대응에서는 지지되지 않는다. 양쪽을 모두 보존한다.

추가 반례:208개 한도이면209개 중 일부를 선택하지 않고 보류, source voice 누락 보류, 명시적4개 lane이면16개 부분 조합으로 lane 간 연결 금지, 원입력 불변, 잘못된 한도 거부. 신규8/전체1,693테스트 통과. 이 결과는 실제 작품의 음악적 정확도 검증이 아니다.

## 실제 실행과 결과

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_progression_evidence_trial --source output/harmony-progression-context-2026-09-30-r4 --output output/harmony-progression-polyphony-2026-09-30-r1 --resolution --ir-source output/harmony-shared-context-2026-09-30-r1 --polyphony
.venv/Scripts/python.exe -m unittest discover -s tests -q
```

새 output 폴더를 쓴다. run-contract/code hash, 원표본 hash와 IR 경로/hash, 각 lane 경계와 대응 refs, track 및 보류 사유를 보존한다. 결과의23실험은 이전18+이번5이며23개 작품의 정답 검사가 아니다.

| 표본 | 가능한 전체 조합 | 실제 계산한 전체 대응 | 상태 |
|---|---:|---:|---|
| K281-3 sample16 |1,536|0|전체256 한도 보류|
| K280-1 sample0 |882|0|전체256 한도 보류|
| K280-1 sample16 |14,306,656|0|lane1,024 한도 보류|
| K280-1 sample32 |157,216|0|lane1,024 한도 보류|
| K280-1 sample64 |8|8|열거 완료; 직접 해결 지지0|

가능한 조합 수는 각 시간 경계의 부분 대응 개수 곱으로 계산한 것이며, 보류된 수백만 조합을 실제 평가했다는 뜻이 아니다. 보류 출력에는 지지 가설 개수가 없으므로 미검사/미정이다. 이를0개나 null을 포함한 배열의 길이1로 세지 않는다.

기존13표본 중 적격 저장 path가 없는7개와 baseline 보류1개는 여전히 별도 제외된다. 실제 Beethoven 양성 해결 검증은 이루어지지 않았다. 완전 열거를 완료한1표본도 기술적으로 선택한 화음 경로이며 음악적 정답률을 측정하지 않았다.

## 결론과 다음 설계

새로 확인한 병목은 **성부 대응 조합의 폭증**이다. 이번 prototype을 대규모 악보의 최종 계산 방식으로 쓰면 안 된다. 해법은 한도만 키우거나 화성 정답에 맞는 연결을 미리 고르는 것이 아니다.

다음 단계에서는 lane/경계의 부분 대응을 분리 저장하고, 이끎음·7음 등의 실제 해결에 필요한 연결 제약을 함께 만족할 수 있는지 검사한다. 같은 음이 두 성부로 분기/병합되지 않는 공동 일관성을 유지하며, 작은 문제에서 이번 완전 열거 결과와 비교해야 한다. 제한된 계산은 보류/정확한 포함 범위를 보고한다. 휴리스틱 탐색 도입은 별도 정확도 검증이 필요하다.

음악적 양성 실제 검증·지연 해결 승격·국소 조성·최적 화음 path·화면/운영 적용은 남았다. Core/원주석/구조 분석/운영5173/기존8822화면은 변경하지 않았다. 외부 AI와 GitHub 업로드 없음.
