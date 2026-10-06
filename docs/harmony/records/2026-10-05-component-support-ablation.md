# HARM-DEV-20261005-65 — 구성음 지지와 구간을 넘는 순차 문맥 점수 대조

## 1. 결과와 적용 결정

화성 개발을 [단계64](2026-10-05-contextual-root-return.md)에서 이어갔다. 두 일반 특징을 별도 연구 모듈로 구현하고, 같은 72구간의 네 조건을 비교했다. **새 점수는 이번 자료에서 정확도를 높이지 못했으므로 운영에 채택하지 않는다.** 계산 검증의 통과와 음악적 정확도 향상을 구별한다.

- 관측하지 않은 3음·변화된 5음·7음에 추가 soft cost를 주는 조건.
- 실제 구성음 두 종류 이상이 지속할 때, 현재 화음 구간 밖의 준비·해결음을 포함하는 짧은 순차 문맥을 조건부 근거로 쓰는 조건.
- 두 조건을 함께 쓰는 조건과 직전 단계64 점수 그대로의 control.

63구간의 네 선택기를 새로 실행했고, 이전 9보류는 분모에 남겼다. Control의 선택·비용·평가표는 단계64와 동일하다. 새 특징의 비용·원음표 근거는 보존하지만, MusicSearch의 화성 화면·Phrase·Motif 계산은 변경하지 않았다. 앞서 완료한 Claude 통합 작업과 이번 화성 점수 실험은 별개다.

## 2. 구현 위치와 보존 범위

| 파일 | 역할 |
|---|---|
| [harmony_component_support_scoring.py](../../../src/musicanote_harness/harmony_component_support_scoring.py) | 특징·원자료 문맥·정확 공동 선택·독립 경로 비용 |
| [harmony_component_support_trial.py](../../../src/musicanote_harness/harmony_component_support_trial.py) | 네 조건 실행, 예측 봉인, 주석 대조, 사례 보존 |
| [audit_harmony_component_support.py](../../../scripts/audit_harmony_component_support.py) | 봉인 후 SHA·원 후보망·선택 비용·평가 재생 |
| [validate_harmony_component_support.py](../../../scripts/validate_harmony_component_support.py) | 이전 관련 검사 517개와 신규 36개 실행 |
| [scoring 검사](../../../tests/test_harmony_component_support_scoring.py) | 25개 |
| [trial 검사](../../../tests/test_harmony_component_support_trial.py) | 8개 |
| [audit 검사](../../../tests/test_audit_harmony_component_support.py) | 3개 |

기존 봉인 점수 모듈을 수정하지 않고 private dependency binding으로 새 scorer를 연결한다. 원 63graph/44,204edge, 전체 원 MusicXML·관찰 Canonical IR, ID·onset·release·tie·철자·source-clock·grace·repeat/ending 관문을 유지한다. 후보 재생성·정답 후보 삽입·작품/마디별 예외·새 cap·parameter sweep·학습은 없다. 기존 별개 dirty 파일도 수정하지 않았다. 외부 API·권한 변경·merge·commit·push는 이번 작업에서 하지 않았다.

## 3. 일반 규칙과 관찰/해석 구별

### 3.1 관측되지 않은 화음 식별 구성음

기존 철자 기반 3화음/7화음 template의 quality가 하나로 확인되는 후보만 소비한다. 다음 구성음을 식별 구성음으로 취급한다.

- 3음.
- 완전5도가 아닌 변화된 5음: 감5도/증5도.
- 7화음의 7음.

근음·완전5도에는 **이번 추가 벌점**을 적용하지 않는다. 기존 missing-member·missing-root 비용은 그대로 남는다. 후보를 금지하거나 근음/5음 생략을 자동 승인하는 규칙이 아니다.

```text
unobserved_defining_member_exposure
  = (관측되지 않은 식별 구성음 수 / 식별 구성음 수)
    × (완성 harmonic run 길이 / 현재 분석 문맥 길이)
추가 계수 = 기존 missing_root 규모인 1/10
```

관측은 완성 run 안에서 실제 양성 sounding time이 있는 철자의 합집합으로 판단한다. 분산화음의 3음이 나중에 나타나면 관측한 것으로 센다. 모든 구성음의 수직 동시 발음을 요구하지 않는다. 미지원 철자·양성 관측 부재·모호한 template·비3도쌓기/기능적 6–4 등의 미지원 후보는 `None`을 유지한다.

이는 **그 후보를 지지하지 못한 관측**이지, 해당 화음이 음악적으로 불가능하다는 증명은 아니다. 실험용 후보 특징이며 Canonical Core의 확정 화성 필드로 저장하지 않는다. 실제 울리지 않은 구성음을 sounding event에 더하지 않는다.

### 3.2 실제 두 구성음 지속 + 구간을 넘는 순차 문맥

다음 조건을 모두 만족해야 새 credit을 계산한다.

1. 전체 원 source의 실제 직접 연결 `준비음→중간음→해결음`이다. 같은 명시 part/voice이며 원 clock과 철자가 유효하다. 가까운 음높이를 임의로 성부 연결하지 않는다.
2. 중간음이 기준 박자 절반 이하이고 약한 박절이며, 기존 반음/온음의 diatonic/chromatic passing/neighbor geometry를 만족한다. 미지원 박자는 보류한다.
3. 현재 후보에서 중간음은 비구성음, 준비·해결음은 구성음이다.
4. 별도의 실제 sounding event들이 중간음 전체 시간에 걸쳐 지속하고, 그중 현재 후보의 구성음이 **서로 다른 철자로 두 종류 이상** 있다. 같은 음의 doubling이나 연속 분산음의 합집합을 실제 지속으로 바꾸지 않는다.
5. 준비음 또는 해결음의 시간 범위가 현재 harmonic run 밖에 있다. 이미 같은 run에서 받은 기존 순차 credit은 이 특징으로 다시 세지 않는다.
6. 준비음 시작부터 해결음 끝까지 source-clock 관문이 통과하며, 그 성부의 grace와 repeat/ending barrier가 없다. 쉼·끊긴 tie·불명확 성부는 보류한다.

```text
held_member_step_support_exposure
  = 조건을 만족한 원 중간음의 현재 run과 겹치는 음가 합 / 전체 note-time
추가 계수 = 기존 conditional_step_ornament_exposure 계수 -1/2
```

원 비구성음·박절·최저 비구성음 비용은 제거하지 않는다. 준비/해결음을 현재 run의 실제 관측이나 노출량으로 옮기지 않는다. `confirmed_nct=false`, `harmony_held_confirmed=false`, `voice_identity_confirmed=false`를 유지한다. 이 실험은 확정 NCT 분류기가 아니다.

**남은 중요 한계:** 준비/해결음이 다른 선택 구간에 속하더라도 그 구간의 실제 선택 화음과 역할을 조건으로 삼지는 않는다. Source clock이 올바르다는 사실은 그 음악적 설명이 올바르다는 뜻이 아니다. 아래 쇼팽 퇴행에서 이 차이가 드러났다.

### 3.3 영수증과 정확 계산

각 후보의 식별 구성음/미관측 구성음, 실제 관측 event IDs와 정규화 값을 남긴다. 순차 문맥에는 준비·중간·해결의 sound/source note IDs, 실제 지속 지지음 IDs·철자, 원 문맥과 credit span을 저장한다. 모든 범위는 rational `[start,end)`다. Confidence·human validation은 확정하지 않는다.

Prefix index와 원음표 직접 scanner를 따로 두며, 각 선택 경로의 최종 비용을 직접 scorer로 다시 계산한다. 2M factored 연산 계약, 동점 ID, 동일 철자 harmonic run의 합집합 점수, 이전 근음 회귀와 기능적 해결 점수는 유지한다.

## 4. 표본·봉인·평가 한계

- 이전 15개 악보 package/9명명 기반 작품군 중 14개 전체 source가 준비된 같은 확대 개발 자료다.
- 같은 72구간: 네 조건 모두 63선택/9보류, 완전 평가 51/부분 평가 21.
- 보류는 source-preflight 6, stream-operation-budget 2, bounded-plan 1이다. 이번에는 다시 시도하지 않았으며 분모에서 제외하지 않았다.
- 원 후보 포함 ceiling `36/51`, 지원 시간 예측 coverage `43.7106%`, root+members 지원 작품군 8은 그대로다.
- 72개의 label-free prediction을 모두 저장하고 SHA 봉인한 **후에만** 이전 reference-bearing report를 연다. Graph·원 전체 XML/IR·기존 코드 SHA도 검사한다.
- 이 자료는 이전 개발에서 이미 노출되었다. 봉인은 이번 inference의 정답 유입을 막지만 독립 blind test를 만들지는 않는다. 구간들은 독립 작품 수가 아니며 겹침이 있을 수 있다.
- 평가 대상은 근음+철자 구성음과 semantic boundary다. Full Roman·전위·국소 조성·NCT·종지 정확도는 이번에 측정하지 않았다. 원주석을 절대 정답으로 승격하거나 사용자 검수 승인으로 표시하지 않는다.
- DCML의 기존 연구용 사용·운영/배포 제한은 변경하지 않는다. 이번에 새 가중치 학습도 하지 않았다.

## 5. 실제 전체 비교

비율은 지원 참조 시간 전체를 분모로 하며, 예측 보류 시간을 지우지 않는다. 아래 표는 전곡/모든 종류의 화성 정확도가 아니다.

| 조건 | 완전 일치 / 51 | 근음+구성음 시간 일치 | 작품군 macro | 경계 TP / FP / FN | 경계 F1 |
|---|---:|---:|---:|---:|---:|
| `control` — 단계64 | 16 | 27.0012% | 51.9033% | 49 / 21 / 14 | 73.6842% |
| `defining_member` | 16 | 26.9312% | 51.8210% | 48 / 21 / 15 | 72.7273% |
| `held_step` | 15 | 26.3011% | 51.6722% | 49 / 21 / 14 | 73.6842% |
| `combined` | 16 | 26.9312% | 51.8210% | 48 / 20 / 15 | 73.2824% |

근음만의 시간 일치는 순서대로 35.1809 / 35.2509 / 34.3407 / 34.9708%다. 근음만 조금 좋아진 조건도 구성음과 경계가 악화했으므로 향상으로 채택하지 않는다.

선택 내용이 변한 구간은 전체 합집합 10개다.

| 조건 | 변경 구간 | 구성음 시간 이익 / 퇴행 / 동일 |
|---|---:|---:|
| `defining_member` | 5 | 0 / 1 / 4 |
| `held_step` | 5 | 0 / 1 / 4 |
| `combined` | 9 | 0 / 1 / 8 |

`combined`는 `held_step`의 쇼팽 퇴행을 피하지만 control보다 좋아지지는 않는다. 경계 FP 한 개 감소를 전체 향상으로 보고하지 않는다.

## 6. 원악보·비용에서 확인한 대표 사례

아래 시간은 **global quarter offset**이며 마디 번호가 아니다. 원 전체 악보·Canonical IR과 전후 source, ID, 각 조건의 선택/비용, 참조 witness를 연결했다. Witness는 예측 봉인 후 진단에만 사용했고 inference에는 넣지 않았다. 이전 11사례를 모두 유지하여 총 18사례를 저장했다. 이는 새 웹 화면 생성이나 18개 독립 검수 작품을 뜻하지 않는다.

### 6.1 쇼팽 — 새 순차 credit이 맞던 전체 화음을 다시 분할

[사례 3e987ee8bfece8435be5](../../../output/harmony-component-support-2026-10-05-r2/cases/3e987ee8bfece8435be5.json.gz), `BI145-2op50-2`, `[28,61/2)`.

- Control은 E♭/G/B♭/D♭ 하나이며 참조와 `5/2 quarter` 일치한다. 비용 `559/2800 ≈ .199643`.
- `held_step`은 `[28,30)` G/B♭/D♭와 `[30,61/2)` E♭/G/B♭로 나누어 참조 일치 시간이 0이 된다.
- 그 분할 경로의 control 비용은 `129/560 ≈ .230357`이나 새 credit 뒤 `109/560 ≈ .194643`가 되어 전체 E♭7보다 싸진다.
- 실제 지속 G/D♭와 D♭5→C5→B♭4의 순차 문맥이 분할한 왼쪽 Gdim 후보에도 credit을 주었다. 해결음의 소속 화음까지 공동 조건으로 보지 않는 한, 사실인 선율 연결로 틀린 화음 분할을 지지할 수 있다.
- 결합 조건에서는 왼쪽 Gdim의 미관측 3음 B♭와 오른쪽 E♭major의 미관측 3음 G 비용도 들어가 그 경로가 `713/2800 ≈ .254643`가 된다. 전체 E♭7 run에서는 G도 실제 관측되므로 전체 선택을 유지한다. 이 한 사례의 상쇄를 일반 성공으로 주장하지 않는다.

### 6.2 코렐리 — B♭ 보충을 억제해도 다른 생략 후보가 이김

[사례 43984eca2bd701128390](../../../output/harmony-component-support-2026-10-05-r2/cases/43984eca2bd701128390.json.gz), `op01n05c`, `[55,56)`.

상성부 E5/G5의 실제 지속과 베이스 C4→D4→E4→D4→C4 문맥은 이전 단계에서 보존했다. 마지막 C4 onset은 `223/4`다.

- Control은 E/G/B♭ → E/G/B♭/D → C/E/G의 세 run, 비용 `.16575`다. B♭는 관측되지 않았으나 후보 구성음으로 가정한 것이다. 원음표에 B♭를 만들어 넣은 것은 아니다.
- 이 경로의 새 식별 구성음 벌점 뒤 비용은 `2389/12000 ≈ .199083`다.
- 그러나 E/G/**B** → E/G/**B**/D → C/E/G 경로가 `283/1500 ≈ .188667`로 새로 이긴다. 관측되지 않은 완전5음 B에는 이번 추가 비용이 없다. 기존 generic missing-member 비용은 남아 있다.
- 전체 C/E/G 참조 witness의 비용은 네 조건 모두 `309/1600 = .193125`다. 기존 same-run 순차 credit이 이미 들어 있어 이번 cross-run 특징으로 이중 credit을 주지 않는다.
- 따라서 구성음 한 종류의 보충을 다른 종류로 바꿨을 뿐, 참조 일치 시간은 계속 `1/4 quarter`다. 올바른 전체 해석의 승리는 아니다.

이는 생략을 무조건 금지하거나 coefficient를 이 작품에 맞게 바꿀 이유가 아니다. 지속·베이스 역할·생략 근거·경쟁 화음의 실제 진행을 함께 표현할 필요가 있다는 반례다.

### 6.3 코렐리 — 실제 변화음 해석도 악화할 수 있음

[사례 4b5f51164332a086b4cb](../../../output/harmony-component-support-2026-10-05-r2/cases/4b5f51164332a086b4cb.json.gz), `op01n04c`, `[219/4,111/2)`.

- Control은 `[219/4,221/4)` D/F/A → `[221/4,111/2)` F♯/A/C이며 일치 시간 `1/2 quarter`다.
- 식별 구성음/결합 조건은 `[219/4,55)` D/F/A → `[55,111/2)` D/F♯/A로 바꾸어 일치 시간 `1/4 quarter`를 잃는다.
- 원 control 경로 비용 `.100444`는 추가 벌점 뒤 `.117111`가 되고, 바뀐 경로 `.102222`가 이긴다.
- 이 자료의 원 reference witness가 없다는 사실도 보존한다. 추가 판정 없이 이를 확정 secondary/NCT label로 바꾸지 않는다.

### 6.4 이전 큰 개선의 유지와 나머지 사례

- [베토벤 소나타 07-2](../../../output/harmony-component-support-2026-10-05-r2/cases/fe9b0e1f69963fe907c1.json.gz), `[105,109)`: Gminor → G♯dim7 → E7의 세 run과 참조 일치 `4 quarter`, 비용 `28633/186000`를 네 조건 모두 유지했다. 기능/국소 조성 확정까지 검사한 것은 아니다.
- [베토벤 현악4중주 n06op18-6_02](../../../output/harmony-component-support-2026-10-05-r2/cases/5a7f8e0ef80d4cf5d89a.json.gz), `[167/2,175/2)`: 전체 B♭7, 일치 `4 quarter`, 비용 `124879/249600`을 유지했다.
- 다른 변화/기존 반례의 pair/sample ID와 전체 source 위치는 [report의 cases/changed](../../../output/harmony-component-support-2026-10-05-r2/report.json)에 기록했다. 선택이 변했으나 시간 점수가 같다는 이유로 숨기거나 성공으로 세지 않는다.

## 7. 실행 중 발견한 문제와 계산 비용

첫 시험 실행은 test helper의 이전 모듈 참조 깊이가 잘못되어 7 error/1 pass였다. Fixture/import 경로를 수정한 뒤 8개 trial 검사가 통과했다. 음악 규칙 변경은 아니었다.

실제 corpus r1은 사용하지 않을 전체 source 순차 문맥까지 즉시 source-clock 검증하여 느려졌다. 4/72구간 완료 후 중단했고, partial prediction·[중단 사유](../../../output/harmony-component-support-2026-10-05-r1/interrupted.json)를 그대로 남겼다. 이 실행은 prediction-freeze나 정확도 report가 없고 reference report도 열지 않았다.

이후 점수·계수·필수 관문은 유지한 채 다음 계산 순서만 변경했다.

- 중간음이 현재 관측 범위 밖이면 후보 run과 겹칠 수 없으므로 계산 준비를 생략한다. 준비·해결·실제 지속음과 근음 이력은 전체 원 source에서 가져온다.
- 준비/해결의 구성음 조건과 두 실제 지속 구성음 조건을 만족하여 **credit을 사용할 때** source-clock 관문을 실행한다. 사용된 credit의 검증은 생략하지 않는다.
- 같은 immutable context의 동일 최저음/clock 조회는 memoize한다. 원 source mutation·SHA 변화는 계속 거부한다.

[부분 실행 동등성](../../../output/harmony-component-support-2026-10-05-r2/lazy-gate-equivalence.json): r1에서 실제 완료한 4구간×4조건의 선택 내용 SHA가 r2와 모두 같다. 전체 범용 속도/정확도 증명은 아니며, 신규 lazy-but-mandatory 검사와 독립 비용 검산을 함께 사용한다.

정본 r2의 실제 runner 시간은 `186.962초`다. 선택+독립 검산을 포함하는 조건별 합계는 control `30.825`, defining `33.665`, held `33.465`, combined `32.534초`다. 원 graph는 재생성하지 않았다. 이전 단계와 서로 다른 저장/문맥 계산 조건이므로 정식 speed benchmark나 실시간 운영 보장으로 부르지 않는다.

사후 자료 조회 명령 한 번은 report 최상위의 `arms`를 잘못 읽어 `KeyError`가 났다. 실제 경로 `records[].arms`로 바로잡았다. 봉인 report나 선택 결과는 변경하지 않았다.

## 8. 검증과 봉인 정본

- 신규 36 + 관련 회귀 517 = **553개 / 39모듈 PASS**, failure/error 0, `44.105초`. 저장소 전체 test suite 통과를 뜻하지 않는다.
- 8개 tiny DAG×4조건의 전수 경로 최적/동점, 모든 시험 interval의 index/direct 비교, delayed 3음·7음 부재·감/증5음·철자/미지원, 실제 지속과 doubling/분산형 구별, 쉼/성부/clock/grace/repeat, overlap-only·이중 credit 방지, 원 코드/자료 불변·변조·봉인을 검사했다.
- 사후 감사 **1,395고유 SHA**, 14개 전체 source, 원 44,204edge round-trip, 63×4 = **252선택 비용** 독립 검산, 72×4 평가 재생, 18사례/사후 witness 비용 검산을 통과했다.
- 결합 조건의 실제 선택에는 cross-run held-step receipt 7개, 미관측 식별 구성음이 있는 run 10개가 있다. 이를 확정 NCT/생략 정답 수로 해석하지 않는다.

정본: [report](../../../output/harmony-component-support-2026-10-05-r2/report.json), [실행 계약](../../../output/harmony-component-support-2026-10-05-r2/run-contract.json), [예측 봉인](../../../output/harmony-component-support-2026-10-05-r2/prediction-freeze.json), [검사 결과](../../../output/harmony-component-support-2026-10-05-r2/test-validation.json), [사후 감사](../../../output/harmony-component-support-2026-10-05-r2/post-seal-audit.json).

Report SHA256:
`05b0893a6be4f0406972cfa317112142b3a5a2d51128602163e29ae14c3394b8`

Audit code SHA256:
`c5ddff3e856b9b1d06fdc1f806da49d14f15ae0028742f6d671e2b721c4be76c`

## 9. 재현

`K:\Music Analysis`에서 실행한다. 봉인된 r2를 덮어쓰지 않으며, 아래 r3도 이미 있으면 다른 새 경로를 사용한다.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_component_support_trial --source output/harmony-root-context-2026-10-05-r1 --output output/harmony-component-support-2026-10-05-r3
.\.venv\Scripts\python.exe -B scripts/audit_harmony_component_support.py --root output/harmony-component-support-2026-10-05-r3
.\.venv\Scripts\python.exe -B scripts/validate_harmony_component_support.py --prior-validation output/harmony-root-context-2026-10-05-r1/test-validation.json --output output/harmony-component-support-2026-10-05-r3/test-validation.json
```

재현 시 원 input/code/artifact SHA가 달라지면 봉인 오류로 멈추는 것이 정상이다. 이를 우회하거나 예전 결과에 새 점수를 덮어쓰지 않는다. 원 모듈을 바꾼 새 개발은 별도 버전/출력/대조 기준을 만들어야 한다.

## 10. 다음 순서와 미완료

1. **큰 선택 오류 우선:** source 순차 형태만이 아니라 실제 공동 선택된 앞뒤 화음의 준비/해결 역할·지속 지지·구성음 교체를 연결하는 transition 또는 명시 latent-role 특징을 설계한다. 서로 경쟁하는 화음에서도 같은 NCT 설명을 무조건 빌려 쓰지 못하게 한다. 생략 후보의 실제 근거와 미관측 member를 따로 기록한다.
2. **비교를 먼저 설계:** 이번 두 퇴행, 이전 과병합/과분할과 원 큰 성공 사례를 모두 control에 남긴다. 한 작품의 성공을 위해 고정 계수를 반복 조절하거나 새 판정의 결과를 원 Core에 넣지 않는다. 새 feature는 기존 정확 joint decoder와 분리하여 전수 toy 검증 후 실제 동일 분모에서 비교한다.
3. **이후 Train 전용 가중치와 넓은 평가:** 고정 특징의 설명력/충돌을 확인한 뒤 승인된 Train만 학습한다. 기존 Dev 결과에 맞춘 sweep 대신 작품군 비중복 평가와 J3–J5 공통 평가/공개 모델 비교를 이어간다. 남은 장문 2M 보류·source 미지원·전위/국소조성/Roman 평가는 별도 미완료다.
4. **화면 적용 관문:** 음악적 이익과 퇴행·지연이 확인된 때에만 별도 비교 레이어로 올린다. 이번에는 정확도 상승이 없으므로 현재 운영 화면을 유지한다. 사용자 의견을 요청할 특정 새 사례 화면은 아직 만들지 않았으며 이번 단계 수행에 추가 음악 판정은 필수는 아니다.

이번 결과는 규칙을 버리거나 더 복잡하게 만들기만 하자는 결론이 아니다. **원자료 사실을 찾는 규칙과 경쟁 해석 중 선택하는 점수의 차이를 실제 오류·비용으로 드러낸 것**이다. 해당 근거는 다음 공동 설명 모델의 검증 자료로 남긴다.
