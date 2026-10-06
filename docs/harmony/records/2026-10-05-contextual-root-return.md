# HARM-DEV-20261005-64 — 근음 지연과 베이스 회귀 문맥의 공동 점수

## 1. 목적과 범위

[단계63](2026-10-05-temporal-harmony-scoring.md)에서는 화음의 근음이 뒤늦게 관측된 시간을 soft cost로 추가했다. 베토벤의 과병합은 개선했지만, 쇼팽·코렐리의 맞던 해석을 과분할한 반례도 있었다. 이번에는 **실제 근음 관측**과 **앞서 나온 근음의 문맥상 지지**를 다른 채널로 둔다. 늦은 근음만으로 화음 변경을 강제하지 않는다.

새 [연구용 점수 모듈](../../../src/musicanote_harness/harmony_root_context_scoring.py)과 [비교 실행기](../../../src/musicanote_harness/harmony_root_context_trial.py)를 추가했다. 기존 봉인 모듈·후보 graph·source clock·MusicXML·Canonical Core·주석·운영 UI·MusicSearch·Composition·Claude Motif는 수정하지 않았다. 학습·API 호출·작품별 예외·Git commit/push도 하지 않았다.

이 자료는 이미 결과를 본 개발 자료다. 예측 봉인은 새 실행 중의 주석 유입을 막지만, 과거 노출을 없애거나 독립 blind test로 바꾸지 않는다. 분석의 정답을 원주석에 맞춰 강제하지 않는다.

## 2. 원자료에서 확인한 서로 다른 상황

- **Chopin `[28,61/2)`:** 실제 앞 베이스 E♭2는 `[27,28)`, 같은 명시 성부의 D♭4/G4는 `[28,29)`와 `[29,30)`, 다음 베이스 E♭3는 `[30,31)`이다. E♭가 계속 울린 것은 아니지만, 동일 성부의 근음→다른 구성음군→근음 회귀라는 대안 설명이 있다. D♭5→C5→B♭4의 선율도 별도로 보존하며 C5를 확정 NCT로 면제하지 않는다.
- **Corelli `[55,56)`:** 상성부 E5/G5는 `[54,56)`에 실제로 지속한다. 두 배음 베이스 성부 각각 C4→D4→E4→D4→C4로 이동하며 마지막 C4의 onset은 `223/4`다. 주어진 짧고 연속된 D는 경과 형태로 설명할 수 있는 후보이며, 독립 화음이라고 확정할 근거는 아니다.
- **Beethoven sonata `[105,109)`:** `[108,217/2)`의 G♯/B/D/F와 `[217/2,109)`의 G♯/B/D/E는 F→E의 구성음 교체가 실제로 있다. 같은 직전 베이스 E 회귀 문맥은 확인되지 않는다. G♯dim7→E7과 근음 생략 E9→E7은 여전히 경쟁 해석이며 Secondary 기능·국소 조성 확정은 이 실험 밖이다.

이름·작품·마디를 코드 조건에 쓰지 않는다. 위 사례들은 같은 전체 source/원 ID에서 규칙의 의미를 설명하는 개발 진단이다.

## 3. 일반 규칙

### 3.1 변하지 않는 관측 계약

근음의 첫 실제 관측 시각 `first_root_time`, original onset/release/tie, 원 note/sound ID는 그대로다. 이전 구간의 근음을 현재 구간의 sounding event·노출량·화음 구성음 합집합에 더하지 않는다. `missing_root`, 비구성음 노출 비용, 구성음 복잡도, 경계 비용도 제거하지 않는다. 실제 근음이 아예 없는 화음은 새 지연 항목으로 이중 벌점하지 않는다.

### 3.2 조건부 최근 최저음 근음 회귀

다음 근거가 **함께** 있을 때만 단계63의 지연 비용을 완화한다.

1. 구간 시작의 현행 기준 박자 한 개 이내에 끝난, 같은 철자의 실제 근음이 있다. 이 근음은 당시 최저 지속음이어야 한다. 단순히 위성부에 같은 음이 한 번 나왔다는 이유로 채택하지 않는다.
2. 구간에서 처음 나타나는 실제 근음도 최저음이며, 앞 근음과 동일한 명시 part/voice 성부다. 이 명시 성부가 실제 대위적 성부라는 확정은 아니다.
3. 앞 근음에서 회귀 근음까지 그 성부의 음표군이 빈틈없이 이어진다. 동일 onset·동일 release의 화음군은 허용하고, 길이가 다른 겹침이나 성부 교차를 임의로 연결하지 않는다.
4. 중간 음표군은 선택 후보의 실제 구성음으로 설명된다. 비구성음은 단음·같은 성부의 유효 직접 연결·준비/해결 구성음·반음/온음 순차·기준 박자 절반 이하·약한 박절의 경과/보조 형태가 함께 있을 때만 조건부 연결로 인정한다. 해당 원 비구성음 비용과 음가는 그대로다.
5. 근음이 없는 앞부분에서 다른 구성음이 적어도 두 종류 실제로 관측된다. 근음 회귀 선율만으로 화음을 만들지 않는다.
6. 원 tied clock을 확인한다. 실제 쉼·불명확한 철자/성부/clock·길이 다른 겹침·끼어든 grace·반복/ending 경계·원음표 손상 문맥은 새 credit을 보류하고 단계63의 비용을 유지한다.

```text
raw_delay = (first_root_time - run_start) / whole_context_width
context_supported_delay = raw_delay × 1/2  (위 문맥 근거가 있는 경우)
                         = raw_delay      (없거나 미지원인 경우)
coefficient = 기존 missing_root 규모 1/10
```

`1/2`는 실제 악보 전체 실험 전에 고정한 heuristic이다. 확률·학습된 신뢰도·최적 가중치가 아니며, 결과를 보고 0 또는 다른 값으로 다시 맞추지 않는다. 지연 비용을 완전히 없애거나 특정 근음 없는 화음을 금지하지 않는다.

### 3.3 지속과 교체의 receipt

각 지지 문맥에는 앞 근음의 원 span/ID, 회귀 근음 ID, 성부, 전체 연결 음표군 ID, 실제 prefix 구성음 ID, 조건부 순차 패턴을 저장한다. 근음 도착 직전/직후의 실제 지속 event 교집합, 사라진 철자, 새 철자도 따로 남긴다. 예컨대 **같은 E5/G5가 실제로 유지**되는 것과 **F→E로 교체**되는 것을 다시 확인할 수 있다.

이 지속/교체 receipt만으로 화음 유지의 최종 label을 정하지 않는다. `harmony_held_confirmed=false`, `confirmed_nct=false`, `voice_identity_confirmed=false`다. 여러 후보는 기존 공동 DAG 선택에서 원 비구성음·베이스·박절·기능적 해결 점수와 함께 경쟁한다. 더 넓은 rootless/페달/전조/다성 성부 분리 일반화는 미완료다.

## 4. 같은 후보·전체 분모·검증 방식

단계63에서 봉인한 63개의 원 graph, 44,204 edge와 14개의 전체 원 XML/관찰 IR을 그대로 재사용한다. 재파싱·후보 재생성·주석 정답 후보 삽입·graph cutoff·새 resource cap은 없다. 기존 보류 9개를 그대로 유지한 72구간을 비교한다. 매 완료 winner는 별도 unindexed 원음표 scorer로 검산한다.

| 조건 | 역할 |
|---|---|
| `baseline` | 원 고정 점수 control |
| `meter_credit` | 단계63 박자 비례 해결 credit control |
| `combined` | 단계63 박자 credit + 근음 지연 control |
| `bass_return` | combined + 이번 조건부 베이스 근음 회귀 |

세 control을 새로 decode하여 이전의 실제 segments/ID/cost와 동일함을 확인한다. 원 repeat/source-clock/grace 및 2M factored 연산 관문을 유지한다. 정확 rational 계산·동점 원 ID·union-run 점수도 유지한다. 기준 박자는 변경 박자/복합 박자의 기존 계약을 따른다.

현재 scope 밖의 앞 근음도 **전체 원 source**에서 확인한다. 단, 지원 문맥에 대해서는 앞 근음부터 회귀음 release까지 source-clock 관문을 추가로 적용하며, 앞 구간의 repeat/ending·grace barrier도 검사한다. 이 근음은 별도 contextual prior일 뿐 현재 범위에서 관측된 사실이 아니다.

모든 예측 packet을 물리 저장·SHA 봉인한 뒤에만 reference-bearing 보고서를 읽는다. 이전 반례/진단과 새 변경 구간은 전부 저장하며, 되돌아가서 선택이 같아진 사례도 삭제하지 않는다. 참조 witness 재채점은 봉인 뒤 사후 진단으로만 실행한다.

## 5. 실제 결과

15개 package/9개 명명 기반 작품군의 72구간, source-ready 14개 package/8가족에서 63개 선택·9개 보류, 완전 참조 51·부분/미지원 21을 유지했다. [정본 report](../../../output/harmony-root-context-2026-10-05-r1/report.json), SHA `94087347afb5f40b01e64574e77876ff1a047e1849fb15ff97472c88ff36109c`.

| 조건 | 완전 일치/51 | 근음+구성음 시간 | 작품군 macro | 경계 TP/FP/FN | 경계 F1 |
|---|---:|---:|---:|---:|---:|
| baseline | 15 | 25.3442% | 49.7134% | 50/29/13 | 70.4225% |
| meter credit | 15 | 25.5543% | 49.7960% | 48/21/15 | 72.7273% |
| combined | 15 | 26.3011% | 51.6722% | 49/22/14 | 73.1343% |
| bass return | 16 | 27.0012% | 51.9033% | 49/21/14 | 73.6842% |

세 control의 실제 경로·비용·평가표는 단계63과 동일하다. 새 조건은 combined 대비 **1구간만 선택이 바뀌어 1개 개선/0개 새 퇴행**, 정답 시간 `5/2` quarter 증가·완전 일치 1개 증가다. Baseline 대비는 10변경/시간 4개 증가·2개 감소·4개 같음, 완전 일치 2개 새 성공·1개 소실이다. 기존 성공 두 곳을 유지했으나 원 baseline의 두 시간 퇴행을 모두 해결한 것은 아니다.

근음만의 시간 일치는 34.7608%→35.1809%, 후보 ceiling 36/51와 prediction coverage 43.7106%는 그대로다. 전체 Roman·전위·국소 조성·NCT·종지 정확도는 측정하지 않았다. 겹치는 scope의 시간 합계를 고유 전곡 길이로 읽지 않는다. 새 credit이 실제 선택된 경로에 나타난 것은 1건이므로, 폭넓은 분산형 일반화가 검증됐다고 주장하지 않는다.

### 5.1 복원 — 기존 근음 회귀 문맥을 놓친 과분할

Chopin `[28,61/2)`는 combined의 G 기반 구간→E♭ 기반 다섯 구성음 구간에서 **E♭/G/B♭/D♭ 하나의 run**으로 돌아왔고 참조와 완전 일치했다. 실제 E♭ onset `30`은 그대로다. 지연 노출 `4/5`를 문맥 지지 때문에 `2/5`로 완화하여 추가 비용 `.08→.04`다.

동일한 원 E♭ 경로 비용은 `447/2800 ≈ .159643`(baseline) → `671/2800 ≈ .239643`(combined) → `559/2800 ≈ .199643`(bass return)이다. 기존 분리 경로는 combined/new 모두 `26/125 = .208`이다. **같은 점수 계약에서 후보 순위가 바뀐 것**이며 주석 화음에 맞춘 대체 출력이 아니다. [전체 source·구간·원 ID·네 조건 비용·사후 witness 사례](../../../output/harmony-root-context-2026-10-05-r1/cases/3e987ee8bfece8435be5.json.gz).

### 5.2 미해결 — 문맥 지지가 있어도 경쟁 비용이 아직 잘못 낮다

Corelli `[55,56)`의 원 C 경로에서도 조건부 회귀·두 경과 형태·실제 E5/G5 지속을 찾았다. 비용은 `369/1600 = .230625`에서 `309/1600 = .193125`로 낮아졌지만, E/G/B♭ → E/G/B♭/D → C/E/G의 세 run 경로 `663/4000 = .16575`가 여전히 이긴다. 그 후보의 B♭는 해당 범위에서 실제로 관측되지 않았지만 불완전 화음 비용을 지불하며 살아 있다. 구성음이 아닌 D의 베이스 노출과 run 안으로 제한된 NCT 설명, 관측하지 않은 B♭의 보충 비용 간 균형이 남는다.

따라서 **문맥 패턴을 찾았다는 것과 최종 화음을 잘 골랐다는 것을 구별**한다. 이 한 사례를 맞추기 위해 `1/2`를 0으로 바꾸거나 C 화음을 강제하지 않았다. [미해결 전체 source·지속음/순차 ID·비용 대조](../../../output/harmony-root-context-2026-10-05-r1/cases/43984eca2bd701128390.json.gz). Corelli의 별도 짧은 credit 퇴행 `[169/4,43)`도 그대로 남기며 [반례](../../../output/harmony-root-context-2026-10-05-r1/cases/ca9e8feb39a7aee296d1.json.gz)를 삭제하지 않는다.

Quartet의 11run→하나의 B♭7과 Sonata의 G minor→G♯dim7→E7 개선은 그대로다. 해당 베토벤 구간에는 이번 회귀 credit을 만들지 않았으므로 이전 해결을 취소하지 않는다. [Quartet](../../../output/harmony-root-context-2026-10-05-r1/cases/5a7f8e0ef80d4cf5d89a.json.gz), [Sonata](../../../output/harmony-root-context-2026-10-05-r1/cases/fe9b0e1f69963fe907c1.json.gz).

### 5.3 검사·사후 감사·계산 부담

- 신규 scorer 22개: 최근/오래된 근음·상성부 근음과 최저음 근음·정확 철자·반복/ending·grace·쉼·겹침·잘못된 clock·두 실제 구성음·조건부 순차 연결·변경/미지원 박자·원 데이터 보존 및 모든 interval/signature의 indexed/unindexed 대조.
- Tiny 12개 고정 DAG × 네 조건의 모든 경로를 세어 exact optimum·원 ID 동점 경로를 대조했다. 새로운 성부 근거도 완성 harmonic run에서만 채점하고 raw edge 절단에 따라 바뀌지 않는다.
- 신규 trial 8개/감사 3개: 기존 graph 재생성 금지, 세 control winner 동일, 봉인 뒤 참조, 9보류 분모 유지, 재귀적 주석 유입/graph/source/code 변조·덮어쓰기 거부.
- 신규 33개 + 관련 기존 484개 = **36모듈 517개 PASS / 33.426초**. repository 전체 suite나 517곡 분석을 뜻하지 않는다. [검사 결과](../../../output/harmony-root-context-2026-10-05-r1/test-validation.json).
- 첫 신규 trial 단위 검사의 disk graph 비교에서 Python tuple과 JSON array 직접 비교로 실패했다. 실험 결과를 바꾸지 않고 fixture 검사를 canonical JSON hash로 수정했다. 이후 33개와 관련 517개 검사를 통과했으며 실제 runner는 첫 실행에서 exit0이다.
- 사후 임시 ceiling 집계가 없는 키 `lattice_complete_reference_possible`로 0을 출력했다. 정본/평가표는 수정하지 않았고 실제 `lattice_hit` 키로 36을 재확인했다. 그 임시 0은 후보 부족 결과가 아니다.
- [사후 감사](../../../output/harmony-root-context-2026-10-05-r1/post-seal-audit.json)에서 **1,295고유SHA / 72×4 metric / 세 control 경로 / 14전체 source / 44,204원 edge / 252 winner 독립 비용 / 11개 이전·새 변경/진단 case**를 재생했다. 새 선택의 유효 회귀 receipt 1개와 사후 witness 비용까지 PASS다. [감사 코드](../../../scripts/audit_harmony_root_context.py).

Actual runner **197.298초 / exit0**다. 원 graph를 재사용하여 후보 생성 0회였다. 이번 arm 처리 합계는 baseline17.987초 / meter17.363초 / combined17.510초 / bass return107.094초다. 이 타이머에는 선택과 독립 비용 검산이 포함되므로, 검산 전 타이머인 단계63 decoder 수치와 직접 속도 비교하지 않는다.

새 arm은 동일 실행 내 combined보다 약6.1배 시간이 든다. 전체 source 문맥/최저음 조회와 반복된 source-clock 보호 비용이 있고, 미세 구간 하나의 수치 개선을 위해 이 부담을 운영에 추가할 근거는 아직 부족하다. 단일 local run 관측이며 speed benchmark가 아니다. 최적화 때는 원 source 검증과 같은 비용/선택을 보존해야 한다.

### 5.4 결정과 다음

**운영 미채택.** 최근 근음 회귀는 유용한 source-bound 특징으로 연구층에 보존하지만, 독립 작품 평가·고른 사례 커버리지·시간 비용·남은 후보/선택 오류를 확인하기 전에는 production 화성/종지/프레이즈 입력으로 승격하지 않는다. 2M 장문 보류 두 곳과 원 반복/source 보류도 그대로다.

다음 큰 문제는 **구성음 지속·비구성음의 성부 진행·새 구성음의 출현을 함께 평가하는 유지/교체 설명**과 실제로 관측하지 않은 구성음의 보충 비용이다. 작품별 root 예외나 이 사례의 가중치 조정 대신, 공통 run 특징으로 연결하고 보다 넓은 작품군에서 대조한다. 동시에 지금 문맥 특징의 반복 계산을 같은 입력·같은 비용으로 줄일 필요가 있다. 이후 train-only 가중치 학습과 비중복 작품 평가 J3~J5로 이어가며, 작은 반례 하나마다 운영 규칙을 즉시 바꾸지 않는다.

## 6. 재현

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_root_context_trial --source output/harmony-temporal-scoring-2026-10-05-r1 --output output/harmony-root-context-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/audit_harmony_root_context.py --root output/harmony-root-context-2026-10-05-r2
```

아직 없는 output 폴더를 사용한다. 전체 XML/IR와 graph는 이전 정본 경로를 SHA로 참조하므로, 새 prediction/case만 옮겨서는 재현되지 않는다. 이것은 중복 복제 없이 원자료·앞뒤 문맥을 보존하는 저장 방식이며, 원 악보나 Core를 고치지 않는다.
