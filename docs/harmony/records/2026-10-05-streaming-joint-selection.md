# HARM-DEV-20261005-62 — 장문 공동 선택의 페이지 계산·재개와 실제 한계

## 1. 결과와 적용 상태

**계산 페이지를 넘는 공동 선택과 저장·재개는 구현·검증했지만 실제 장문 2구간의 분석 완료는 아직 못 했다.** 둘 다 누적 2,000,000 factored 연산 한도에서 선택 없이 보류했다. 저장 방식 개선을 정확도 상승으로 보고하지 않는다.

- 이전 15개 악보 package / 9개 명명 기반 작품군 / 동결 72구간을 유지했다. 기존 70구간의 결과는 재사용하고 자원 제한만 있던 2구간만 새로 계산했다. 새로운 72개 작품이나 독립 blind 평가가 아니다.
- 63선택 / 9보류, 완전 문맥 15/51, 근음+구성음 시간 일치 25.3442%, coverage 43.7106%, 경계 F1 70.4225%는 **전부 이전과 같다**. 전위·Roman·국소 조성 전체 정확도를 이 표로 측정하지 않는다.
- 7개 계산 페이지 / 원 후보 edge 21,288개와 완료 페이지 checkpoint 5개를 저장했다. 전체 XML/Canonical IR 및 원 note/sound/성부·시간 ID를 보존했다. 두 candidate inventory는 미완성이며 새 candidate ceiling을 계산하지 않았다.
- 관련 29개 모듈 453 PASS / 27.536초, 사후 검사기의 표현 오류 재현·실제 변조 거부 2 PASS / 0.335초다. 합계 455개 **코드 검사**이지 455곡의 정답이나 repository 전체 suite 통과가 아니다.
- 사후 v2 검사에서 1,020개 고유 SHA, 72개 범위·metric, 70개 기존 결과, 7개 page와 5개 checkpoint를 확인했다.

연구용 adapter/runner만 추가했다. 기존 봉인 후보·점수·parser/Core/XML/주석, MusicSearch 화면·서버, Composition, Claude Motif 작업, Git·권한·가중치는 변경하지 않았다. 이번에는 새 화성 UI 결과가 없다. API·학습·merge·commit·push는 하지 않았다.

## 2. 변경 이유와 보존 계약

[단계61](2026-10-05-source-clock-quarantine.md) 뒤 남은 장문 3구간 중 2개는 global 64cell/256sound 저장 관문 때문에 시작할 수 없었다. 다른 1개는 반복·ending 경계도 포함하므로 계속 보류한다.

원 fine grid, 각 계산 타일의 모든 interval 후보, 모든 part의 실제 음, 원 spelling·source onset/release·tie·grace 계약을 유지한다. 계산 타일 경계를 음악적 화음 경계로 해석하지 않는다. 같은 signature가 타일을 넘으면 하나의 harmonic run 점수를 전체 합집합에서 계산한다. 다른 signature는 실제 선택된 다음 화음과의 전이·해결 근거를 계산한다.

페이지 사이에 아래 상태를 전달한다.

- raw-edge 사용 수, 현재 harmonic run 시작점, spelled root+members.
- exact integer score, 동점 판정용 원 candidate ID 전체 경로.
- 누적 연산 수·statistics와 읽은 원 edge ID ledger.
- source/evidence SHA, 전역 시간 grid·노출량·raw cap·고정 가중치·페이지 범위·설정 binding.

완료 전에는 페이지별 승자나 임시 화음을 출력하지 않는다. 완료한 선택은 원 scorer로 비용과 원 ID 경로를 재계산한다. 이는 **선언된 후보망·점수의 최적성**이지 음악적 정답 보장이 아니다. 이번 실제 두 사례는 완료하지 못했으므로 최적성을 주장하지 않는다.

## 3. 자원 계약 — 바뀐 것과 안 바뀐 것

| 항목 | 이번 계약 |
|---|---|
| global 64cell / 256sound | 자원 사유만 페이지 방식으로 대체. 음/시간 grid 삭제·축소 없음 |
| 후보 edge 20,000 | 종전 global 상한을 **페이지별 20,000**으로 변경. 전체 수는 별도 합산 |
| 타일 | 기존 최대 12cell 및 meter/source/repeat 관문 유지 |
| raw-edge 사용 cap | 기존 6 × 전체 타일 수 유지 |
| decoder 연산 | 전체 문맥 누적 2,000,000 유지. 재개 시 0으로 재설정하지 않음 |
| live state | 100,000, 초과 시 보류. beam 선택·음악 후보 pruning 없음 |
| exact 재계산 memo | run/pair/transition 각각 4,096, signature integral 64. eviction은 exact 재계산 |
| 미래 최소 edge 수 | 전체 DAG가 아직 없으므로 남은 페이지 수의 안전한 하한. 점수 근사 아님 |
| 구성음 수 | 현재 catalog 최대 7개 계약. 더 많으면 오류 보고, 묵시적 삭제 없음 |

전체 source/evidence, checkpoint frontier의 원 경로와 ID ledger는 보존하므로 전곡 메모리가 일정하다는 주장은 하지 않는다. 캐시 eviction·재시작은 계산량/시간을 바꿀 수 있다. 저장을 줄여도 후보와 전역 상태 조합은 사라지지 않는다. 페이지 수 하한은 full DAG의 최단 경로 하한보다 느슨할 수 있다.

## 4. 실제 두 사례

| 원 자료/동결 문맥 | 범위 (quarter) | fine cell/전체 타일 | 만든/완료 페이지 | 만든 원 edge | 누적 연산 | 관측 시간 |
|---|---|---:|---:|---:|---:|---:|
| Beethoven quartet `n06op18-6_02`, `cont_12258980adb87c2e81fa` | `[59/2,118)` | 582 / 49 | 4 / 3 | 10,231 | 2,000,000 | 127.173초 |
| Chopin mazurka `BI145-2op50-2`, `cont_0cdcf828cc361186885c` | `[74,148)` | 117 / 10 | 3 / 2 | 11,057 | 2,000,000 | 63.599초 |

전체 runner는 201.949초 / exit 0이다. 회귀 검사를 병행한 한 번의 관측이므로 엄밀한 speed benchmark는 아니다. represented logical transition은 각각 9,551,923 / 8,220,764이며 factored 연산과 다른 단위다. peak live state는 59,531 / 48,566으로 중단 원인은 state 상한이 아니라 연산 한도다.

첫 페이지를 디스크에서 읽어 새 session에 실제 복원했다. Quartet은 204,895연산, Chopin은 290,972연산을 그대로 이어 갔다. 이후 완료 페이지도 checkpoint로 보존했다. Quartet 4번째/Chopin 3번째 페이지에서 한도에 도달했으며 미완료 페이지를 재개 가능한 checkpoint로 위장하지 않는다.

- [Quartet 전체 source·IR·페이지·checkpoint 사례](../../../output/harmony-streaming-joint-2026-10-05-r1/cases/1f9a33c9111b19358cbc/case.json)
- [Chopin 전체 source·IR·페이지·checkpoint 사례](../../../output/harmony-streaming-joint-2026-10-05-r1/cases/4fd69a01475dbfbb21d1/case.json)

같은 Chopin의 `[281/2,211)` 문맥은 `repeat_or_ending_barrier`도 있으므로 새 계산 대상에 넣지 않았다. 기존 source-preflight 6보류도 유지했다. 보류 문맥을 평가 분모에서 삭제하지 않았다.

## 5. 주석·source·결과 봉인

resource-only 적격성은 기존 보류 상태·source clock·source blockers로 판정했다. 곡명/정답 화음/주석으로 구간이나 가중치를 바꾸지 않았다. 페이지마다 원 edge와 origin group/functional receipt를 SHA로 연결한다. 시간 노출량과 점수는 전체 문맥 기준이며 타일마다 다시 정규화하지 않는다.

전체 72개 예측·사례·페이지·checkpoint SHA를 저장한 후 처음으로 reference-bearing report를 열어 평가했다. `baseline_prediction_reused`가 이번 재사용 여부의 권위 필드다. 이전 `accepted_prediction_reused`는 단계61 source-clock replay의 역사적 필드이며 이번 fresh 계산의 표시로 읽지 않는다.

이미 노출된 개발 자료다. 봉인은 실행 중 주석 유입·사후 예측 변경을 방지하지만 독립 미공개 평가를 만들지는 않는다. 새 candidate ceiling은 `null`, historical ceiling은 따로 보존한다. 부분 후보 수를 정답 포함률이나 원 전체 후보망으로 보고하지 않는다.

## 6. 검증과 실패 기록

- 새 stream 30검사: exhaustive tiny DAG·정확 점수·동점 ID·음이름·negative bonus·raw cap·모든 interval feature 증명을 새 decoder에도 적용했다. 여러 페이지 same-run, 캐시 eviction, 매 페이지 JSON 재개, source/evidence·목표 변경 거부, 미완료/중단 시 선택 없음, 잘못된 winner ledger를 검사했다.
- 새 trial 9검사: resource-only 적격성, 실제 저장·재개, 봉인 전 reference 미개방, 기존 선택/반복 보류 유지, code/packet/reference 변조·주석 오염·출력 덮어쓰기 거부를 검사했다.
- 관련 회귀 포함 453 PASS다. 실제 선택이 새로 없으므로 실제 장문 winner 정답·exact optimum 검증은 미완료다. 완료 선택 검증은 합성 예제에서 수행했다.
- **사후 v1 실패:** JSON 배열과 메모리 tuple의 직접 비교로 `checkpoint_replay_changed`가 났다. 파일 변조·연산 초기화·음악 결과 불일치가 아니라 검사기 표현 비교 문제다. 원 report/예측/코드와 v1 검사기를 보존했다.
- v2는 canonical JSON SHA로 같은 값을 비교한다. operations/cost 변경을 계속 거부하는 2검사를 추가했다. 1,020SHA/72scope/70control/7page/5checkpoint 재생 PASS다. v2는 원 report 생성 후 추가했으므로 자체 SHA를 사후 audit에 별도 기록한다.
- 문서의 첫 생성 patch는 README의 불완전한 행 매칭 때문에 적용 전 실패했다. 파일이 생성되지 않았음을 확인하고 정확한 context로 분리 적용했다. 음악 코드/봉인 출력 수정은 없었다.
- 마무리 검사: 11파일 UTF-8·대체문자 없음, Python AST 7파일, 문서 로컬 링크 253개, 봉인 SHA 1,020개와 v2 자체 SHA 불변, `git diff --check` 통과다. 기존 tracked dirty 5경로를 보존했고 Git write는 하지 않았다.

## 7. 산출물과 재현

- [stream 계산기](../../../src/musicanote_harness/harmony_streaming_joint.py), [동결 runner](../../../src/musicanote_harness/harmony_streaming_joint_trial.py).
- [stream 검사](../../../tests/test_harmony_streaming_joint.py), [trial 검사](../../../tests/test_harmony_streaming_joint_trial.py), [사후 표현/변조 검사](../../../tests/test_harmony_streaming_joint_audit.py).
- [보존한 v1 검사기](../../../scripts/audit_harmony_streaming_joint.py), [사후 v2 검사기](../../../scripts/audit_harmony_streaming_joint_v2.py).
- [실제 report](../../../output/harmony-streaming-joint-2026-10-05-r1/report.json), [실행 계약](../../../output/harmony-streaming-joint-2026-10-05-r1/run-contract.json), [예측 봉인](../../../output/harmony-streaming-joint-2026-10-05-r1/prediction-freeze.json), [v2 audit](../../../output/harmony-streaming-joint-2026-10-05-r1/post-seal-audit-v2.json), [검사 기록](../../../output/harmony-streaming-joint-2026-10-05-r1/test-validation.json).

Report SHA: `9b241d30c26966741af1c4bcddfa4ba07e2c29a70def5e2648c02adb65973a60`.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m unittest test_harmony_streaming_joint test_harmony_streaming_joint_trial test_harmony_streaming_joint_audit
```

실행 재현은 `python -B -m musicanote_harness.harmony_streaming_joint_trial --source output/harmony-source-clock-2026-10-05-r1 --output <새 폴더>`를 사용한다. 기존 output은 덮어쓰지 않는다. 사후 v2 audit의 `--root`도 새 실행 폴더를 가리킨다.

## 8. 다음 우선순위와 보류

저장 관문과 중단/재개는 검증했으나 **exact 탐색 상태 조합은 여전히 너무 크다**. cap을 무조건 올리거나 세부 checkpoint 작업을 반복하는 대신 큰 음악적 선택 오류와 후보 복잡도를 먼저 처리한다.

1. 완료 구간에서 드러난 **하나의 지속 화음의 과분할**과 **해결 관계의 두 화음의 과병합**을 함께 점수 비교한다. 특정 작품의 정답을 하드코딩하지 않는다.
2. 장문 exact 기준선은 보류 상태로 보존한다. 필요 시 별도 명시적 근사 arm에서 후보 손실·최적성 미확인·시간/coverage/경계 퇴행을 함께 평가한다. 단계62에서는 근사 arm이나 운영 승격을 구현하지 않았다.
3. 음악적 결과가 바뀔 때 전체 악보의 전후 비교를 제공한다. 이번 resource 보류만으로 사용자에게 음악 판단을 요구하지 않는다. 반복 unfolding·국소 조성·Roman/전위·화성→종지 연결은 별도 미완료다.

Motif는 Claude 작업 완료 후 별도 검토·병합하며 혼합하지 않는다.
