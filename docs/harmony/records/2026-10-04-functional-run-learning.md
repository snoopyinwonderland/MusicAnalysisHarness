# J2f — 합집합 화음 구간·기능적 해결 근거의 Train 전용 가중치 학습

기록 ID: **HARM-DEV-20261004-54** · 2026-10-04. [J2e 기능적 후보와 해결 근거](2026-10-04-functional-candidate-scoring.md)의 후속 화성 개발 기록이다. **구현·전체 검증은 완료했지만, 시간/macro/경계 퇴행으로 새 가중치는 미채택**이다. 운영 배포나 독립 정확도 평가의 완료 선언이 아니다.

## 1. 목적과 고정 계약

J2e에서 후보 ceiling과 실제 선택이 각각 개선됐지만, 실제 leading-tone motion을 독립 화음 교체로 과선택하는 실패도 있었다. 이번에는 새 후보·이론 규칙을 추가하지 않고 **동일한 20차원 근거의 가중치만 Train에서 학습**한다. 특정 제목/악보/마디의 정답 조건은 없다.

- 원33악보/19작품군/322문맥·원 split과 원 source XML/Canonical IR/measure revision을 유지한다. 전곡 길이나 독립322작품으로 환산하지 않는다.
- J2e의 원 후보 + 기능적6–4 대안 목록, span, root/members spelling, blocker, 원6 raw segment cap, 2,000,000 transition cap을 유지한다. Annotation에서 후보를 만들어 넣지 않는다.
- 기존15 관측 특징 +4 실제 조건부 pair 특징 +기능적 해석 복잡도1개, 합계20개다. `segment_count` 대신 **harmonic_run_count**를 사용한다. 인접 동일 signature의 raw edge는 하나의 합집합 run으로 점수를 받으며 같은 서명이 여러 조각이라는 이유로 보상을 받지 않는다.
- Source-bound 조표/박절/최저 지속음/장식 후보·원 blocker와 실제 선택된 다음 onset의6–4 및 dominant-family 해결 근거를 같은 점수에 넣는다. Literal root와 functional root는 분리한다. Polyphonic voice는 임의 연결하지 않으며 local key/Secondary·NCT·cadence 확정은 하지 않는다.
- 근거의 `None`은 비용 계산에서 mask하지만 사실의 false로 바꾸지 않는다. 실제 nonmember 노출은 남고 conditional ornament는 구성음 면제가 아니다.

## 2. 학습·선택 알고리즘

새 [20특징 학습기/정확 decoder](../../../src/musicanote_harness/harmony_functional_learning.py)와 [동결 비교 실행기](../../../src/musicanote_harness/harmony_functional_learning_trial.py)를 별도 추가한다. 과거 source/scorer/실험 결과는 수정하지 않는다.

학습 전 고정값은 **5epoch, update cap1/10, weight bound±4, weight precision1/1,000,000, 시간 loss1 +의미 경계 loss1/4**다. J2e 고정 비용을 초기값으로 쓴다. 한 개 arm만 사전에 선언하며 Dev로 epoch/checkpoint/가중치/arm을 선택하지 않는다. 학습 순서는 작품군→sample ID다.

1. 별도의 확인된 **로컬 비상업 연구 사용 계약**에서 승인된 Train entry만 받을 수 있다. 원 manifest의 운영 모델 학습 미승인은 수정하지 않는다. NC 조건/출처·LICENSE/README 물리SHA를 검사하며 상업 사용·운영 배포·외부API 전송·checkpoint 재배포는 허용하지 않는다.
2. Reference가 완전하고 기존 J2e 후보망/원 cap 안에서 표현 가능한 Train 문맥만 update 대상이다. Compatible path는 **기존 후보의 filter**이고 정답 후보 추가가 아니다. 불완전·미지원·자원 보류는 이유를 기록한다.
3. 현재 가중치에서 최저비용 compatible latent target과 `argmin(w·phi − loss)`의 training adversary를 정확히 찾는다. Time mismatch와 semantic boundary FP/FN을 함께 반영한다. 같은 signature의 raw edge cut는 false boundary가 아니다.
4. `delta = adversary_phi − target_phi`, `violation = loss − w·delta`, `tau = min(1/10, violation/||delta||²)`로 capped passive-aggressive cost update를 한다. Clip/quantize 후 실제 동일 pair의 잔여 violation을 기록한다. Positive loss인데 delta0이면 feature collision으로 기록하고 가상의 근거를 만들지 않는다.
5. 매 update 또는 skip 뒤 가중치를 평균한다. Resource cap에 도달하면 근사 winner를 학습에 넣지 않으며 averaging tick은 보존한다.
6. 추론에는 reference/loss 인자가 없다. 학습이 끝난 단일 평균 model과 같은 source-bound evidence를 사용한다. 추론을 마친 뒤에만 해당 문맥의 evaluation label을 읽는다.

DP 상태는 endpoint/raw count/run start/spelled signature다. 동일 run 확장은 현재 합집합 비용을 교체하며, 기능적 pair는 완료된 왼쪽 run과 **실제 선택된 다음 화음 도착**에서 계산한다. 후보 blocker와 training loss의 edge 노출만 raw-edge additive다. Exact Fraction을 공통 분모 정수로 변환하고 매 비용의 정확한 나눗셈을 확인한다. 가중치의 학습 precision과 시간을 float로 근사하는 것은 다르다.

전체 IR은 source SHA로 묶고, 문맥과 무관한 검증된 rows/neighbors/direct links만 같은 IR에서 공유한다. 각 bundle의 원음/clock 검사는 생략하지 않으며 관측 범위와 계산 cache는 문맥별이다. 최종 추론 뒤 재계산 가능한 cache만 해제한다.

## 3. 테스트와 전체 실행

최초 신규22개 +관련 회귀174개 = **196 PASS /2.675초**, 업데이트 방향/clip·잘못된 설정 검사 추가 뒤198 PASS /2.816초, 학습용 metadata 구별 검사 보완 뒤 최종 **신규24개 +회귀174개 =198 PASS /2.778초**,4AST PASS다. 테스트 중 synthetic6–4 split fixture가 실제 후보 공급 조건을 만족하지 않은 문제와, leakage fixture의 이전 physical pin을 갱신하지 않은 문제를 수정했다. 실제 음악의 규칙/가중치를 바꾼 수정이 아니다.

다음을 검사했다:20 exact weight contract, 기존 고정 decoder와 winner/cost 일치, 임의 signed weight 및 loss-augmented exhaustive optimum, union/split feature 동등성,6–4 role1회, raw blocker 보존, unknown mask, 시간 loss binding, 같은 signature 경계 비용, 원 candidate 불변, gold 비주입·Train/Dev/승인/중복/보류, 평균/재현성/clip, collision·model hash/사용 제한, 실제 파일 source/LICENSE/receipt 변조, parent 보존·덮어쓰기 금지.

최초 r1 실행은 원322문맥 검증·118적격 Train 확인 및 학습epoch2의40/118까지 진행한 뒤 metadata 감사로 중단했다. 학습 adversary에 `source_labels_used_for_selection=false`가 붙는 오해의 소지가 있어, training에서는 true·일반 inference에서는 false로 수정하고 `training_reference_labels_used`도 명시했다. 점수/손실/후보/학습 설정에는 변화가 없다. r1 output은 생성되지 않았으며 최종결과나 checkpoint가 아니다. 선택적 OS 성능 조회는 sandbox access denied였고 권한 확대/시스템 변경을 하지 않았다.

전체 재실행 r2를 **898.953초/exit0**으로 완료했다.33악보/19작품군/322문맥·완전256/부분66을 유지했다. 코드와 원 입력850개 고유 SHA가 종료 및 사후 검사에서 불변이다. 기존 prediction은 다시 추론하지 않았지만 모든 이전 선택 경로의20차원 비용이 원 J2e 고정 비용과 일치하며, 역사적 집계도 그대로 재계산했다. 운영UI·서버·Git는 변경하지 않았다.

## 4. 결과와 결정

### 학습 범위와 보류

승인된 Train270문맥 중 **15작품군의118문맥**이 완전 reference와 기존 후보망/원 cap의 target path를 갖는다. 이전110보다8개 늘어난 것은 J2e 기능적 후보망의 효과다. 나머지152문맥은 compatible complete path 없음75, 부분/미지원 reference49, lattice 불가28로 기록한다.75개는 후보/경계/연결/구간 cap 문제를 포함하며 모두 단순6segment 초과로 해석하지 않는다. Reference target 자격과 inference 자원 예산은 별개다.

118×5=**590 averaging tick**에서 update549·margin 충족 skip27·resource skip10·feature collision4회다. Epoch별 update는116/112/109/106/106이다. Resource skip은2문맥×5회이며 근사 winner를 쓰지 않는다. Collision은 **같은 Corelli 문맥1개에서4epoch**이며 독립4음악 사례가 아니다. Partial/미지원/보류 문맥은 전체 평가 분모에서 제거하지 않는다.

평균 model은 `functional_margin_6a30fbcea02c0901a4608ce8`이다. Confidence는 calibrated되지 않았으며 새 weights가 음악적 규칙을 참으로 증명하는 것은 아니다.

### 같은 분모의 최종 비교

시간 평가의7,895/8quarter는 겹친 문맥의 지원 시간이며 고유 전곡 길이가 아니다. 완전 일치·의미 경계는 완전256문맥, 시간 일치는 부분 reference66개의 지원 범위도 포함한다. 이 평가의 정답은 DCML annotation에서 얻은 **root+spelled members/time projection**이다. 전체 Roman/전위/조성/NCT/cadence 정답률이나 human 음악 검수를 뜻하지 않는다.

| 지표 | J2e 고정 점수 | J2f 학습 점수 |
|---|---:|---:|
| 구간 전체 root+members 일치 /256 | 52 (20.31%) | 55 (21.48%) |
| Root 시간 일치 | 41.48% | 38.11% |
| Root+spelled members 시간 일치 | 31.97% | 30.33% |
| 작품군 macro root+members | 39.08% | 37.03% |
| 경계 TP/FP/FN | 215/94/228 | 133/25/310 |
| 경계 precision /recall | 69.58% /48.53% | 84.18% /30.02% |
| 경계 F1 | 57.18% | 44.26% |
| 선택 /보류 | 288 /34 | 288 /34 |

완전 일치 회복16·유지39·퇴행13·양쪽 오답188·부분66이다. 시간 단위로는43문맥 이익·53퇴행·226동일이다. **완전 일치3개 증가만으로 개선을 선언하지 않는다.** 불필요 경계69개는 줄었지만 필요한 경계82개도 놓쳤다. 두 엔진 모두28baseline 불가 +3edge budget +3transition budget을 보존하며 새 자원 보류0·분모 제외0이다.

| Split | 고정 전체/시간/macro/F1 | 학습 전체/시간/macro/F1 |
|---|---|---|
| Train270 /완전205 | 45 /31.04% /39.51% /55.58% | 46 /29.30% /37.31% /42.48% |
| Dev52 /완전51 | 7 /36.12% /36.77% /62.03% | 9 /34.95% /35.54% /49.66% |

Dev의 완전 일치는7→9지만 시간과 경계가 동시에 내려갔다. 새 epoch/가중치를 Dev에서 고르지 않았으며 이전에 노출된 개발 cohort의 비교다. 독립 test 정확도가 아니다. 후보 정답 포함 확인은 **140/256으로 동일**하다. [후속 J3a 감사](2026-10-04-common-benchmark-preparation.md)에서 나머지116을 **확인된 후보 부재101 +보류로 포함 여부 미확인15**로 구별했다.101부재는 원 후보망을 유지한 가중치 조절만으로 해결할 수 없지만15보류를 확인된 누락으로 해석하지 않는다. 원 report와 prediction은 변경하지 않았다.

### 가중치와 실제 실패 원인

| 특징 비용 | 초기 | 평균 학습 |
|---|---:|---:|
| harmonic_run_count | 0.015 | 0.242866 |
| member_turnover | 0.020 | 0.250832 |
| unanchored_change | 0.040 | 0.233224 |
| extra_member_complexity | 0.100 | 0.834879 |
| nonmember_exposure | 1.000 | 2.031450 |
| metric_nonmember_exposure | 0.250 | 1.391667 |
| key_signature_foreign_member | 0.100 | 0.771609 |
| functional_role_complexity | 0.050 | 0.674353 |
| six_four_surface_and_held_bass | −0.100 | −0.563729 |
| six_four_direct_upper_paths | −0.050 | −0.234068 |
| dominant_family_leading_tone | −0.100 | −0.208537 |
| dominant_family_seventh_step | −0.050 | −0.457894 |

전체20가중치의 exact rational과 epoch/update/delta는 model에 있다. 위 값은 설명용 decimal이며 원 시간/점수는 Fraction이다. 구간·turnover·추가 구성음 비용이 커져 **화음 교체/7음의 설명을 피하는 경향**이 생겼다. 해결 근거 보상을 강화했어도 전체를 긴 triad run으로 합쳐 비용을 줄일 수 있다. 이 원인은 아래 실제 경로의 점수 차이를 분해해 확인했으며 모든 실패의 단일 원인으로 단정하지 않는다.

Raw edge1개 선택 문맥은51→76,6개는13→3이다. Raw edge 개수는 harmonic run 개수와 다르다. 병합 여부는 실제 signature 변화와 경계 지표로 판단한다.

### 실제 사례: 이익·퇴행·표현 충돌

사후 선택한8개 이익/퇴행 문맥을 [selection-changes](../../../output/harmony-functional-learning-2026-10-04-r2/selection-changes.json)에, 다음6개 비용 분해/충돌 증명을 [cost-diagnostics](../../../output/harmony-functional-learning-2026-10-04-r2/cost-diagnostics.json)에 보존했다. 이 진단에서 model/prediction을 수정하거나 재학습하지 않았다. 모든 사례는 원 context/search SHA·full IR SHA·원 group/source IDs·span·annotation을 참조한다. IR/XML은 기존 저장본으로 재현할 수 있으며 별도의 검수된 gold로 바꾸지 않는다.

- **Mozart K280-1** `cont_601fd25d1ccb611517dc` `[191,197)`: 시간 **15/4quarter 퇴행**. 기존5 harmonic run 대신 C#–E–G의 diminished triad를 전 구간에 유지했다. 새 weights에서 기존 경로 비용은 `67955987/32000000`, 새 경로는 `42270347/24000000`다. 새 경로는 nonmember/metric 비용이 늘어도 run4개 감소에서 `−121433/125000`, turnover 감소에서 `−31354/46875`를 얻어 더 싸다. J2e에서 시간 개선된 바로 그 사례가 다시 퇴행했다.
- **Corelli op01n01c**, Dev `cont_511bf50865c786f96c17` `[67,75)`: 시간 **3quarter 퇴행**. 후반 E-half-diminished7→Amajor를 A7 `[72,75)`로 합쳤다. Run/turnover 절약이 추가 구성음 및 nonmember 비용을 이기는 실제 pair다. Dev에서도 필요한 교체를 놓친다.
- **Chopin BI122op41-2** `cont_b914a66c2b7e86347337` `[112,117)`: 시간 **2quarter 퇴행**. A#7의7음을 버린 triad를 앞에 유지한다. 구성음 복잡도 감소의 기여 `−9183669/5000000`가 증가한 nonmember·metric 노출을 이겼다. 큰 합집합 과선택을 막는 하나의 비용이 genuine7화음도 억제할 수 있다.
- **Mozart K280-2** `cont_df654bd4dfbb9dfe2e44` `[3/4,5/2)`: 시간 **7/4quarter 회복**, 완전 일치로 바뀌었다. Dbmajor7 대신 reference의 Fminor triad를 선택했다. 같은 추가 구성음 비용은 이 경우에는 잘못된7음 과선택을 줄였다. 특정 작품 예외가 아니라 동일 feature의 이익/실패를 함께 기록한다.
- **Chopin BI105-4op30-4** `[288,296)`는 시간7/2quarter 이익이 있으나 완전 일치가 아니다. **Chopin BI105-3op30-3**, Dev `[359/2,187)`도2quarter 이익이 있으나 functional root가 다른6–4/적용화음 전 구간을 복구한 것이 아니다. 전체 변화 파일의 원주석/선택을 보존한다.
- **Beethoven Sonata03-2** `cont_b0b624e987d33699d356` `[14,31/2)`: J2e에서 회복한 기능적6–4→B7→E의 완전 일치를 이번에는 잃었다. Functional-role/run/turnover 비용을 피하면서 source-compatible 해결 근거도 사라지는 쪽이 싸졌다. 실제6–4 근거를 연결했다는 사실이 학습 후 그 근거의 선택을 보장하지 않는다.
- **Corelli op01n02c** `cont_48f19ae8308d345db155` `[29,35)`: training adversary의 F#aug→Eminor→F#aug와 compatible target의 F#major→Eminor→F#major가 **20차원 Fraction 벡터에서 정확히 동일**하다. C##와 C#의 철자는 원IR/후보에 보존되지만 현재 source/조표/노출·전이의 점수 요약에서 구별되지 않는다. Normalized time loss2/3이고 경계 loss0,4epoch collision이다. 모델의 최종 선택이나 원주석 정확성을 별도로 확정한 것은 아니다. 가중치 조절만으로 이 pair를 구별할 수 없음을 보여 준다.

**결정:** 공동 run/기능적 점수의 Train 학습 연결은 구현했지만 **새 가중치는 채택하지 않는다.** 완전 일치의 작은 이익보다 시간/macro/경계 퇴행이 크고, 중요한 이전 회복 사례도 잃었다. 고정 J2e 연구 baseline과 기존 운영UI는 유지한다. Dev를 보고 λ·penalty를 임의로 줄여 같은 표본을 반복 맞추지 않는다.

## 5. 출처와 재현

- Parent J2e [report](../../../output/harmony-functional-scoring-2026-10-04-r1/report.json) SHA `e3983219bc2b53fd102302514cecc74e9e98b54290cc3d295e3023c6e912f661`.
- Recall [report](../../../output/harmony-candidate-recall-2026-10-04-r1/report.json) SHA `f12397eb53544dfa153974a9f0006f7cb06467d09c10ce1ecaf8da2e2d21f0eb`.
- Integration [report](../../../output/harmony-context-integration-trial-2026-09-30-r1/report.json) SHA `22ff64ceb522cfde5039d07dc28935179e8c12add14ed52aaa0295f90e1bcebe`.
- 별도 연구 계약 [JSON](../experiments/2026-10-04-local-research-training-use.json) SHA `46bbd4871cc38e27d14fd19d317956f989a1ead6fa265ecb74d722272db4ee48`.
- `python -B -m musicanote_harness.harmony_functional_learning_trial --help`의 네 source pin과 새 output 경로를 지정한다. 기존 output 덮어쓰기는 거부한다.

최종 output4파일 총9,330,688B다. 정본 report/model/changes는 실행기가 만들고, cost-diagnostics는 완료 뒤 source를 재검사해 추가한 사후 진단이다. 기존3파일은 수정하지 않았다.

| Artifact | Bytes | SHA256 |
|---|---:|---|
| model.json | 1,847,292 | `062e46ecd529f6c19f2e3cd1e9f967831140561291161cfa2e63cb937dff158c` |
| report.json | 7,084,305 | `77350ac9eb04f11e663a6adb6d1d7fd2ff5b98d99b8495c42b8413308fc52594` |
| selection-changes.json | 309,243 | `b2c35f352fe8fb0314fd0864fb42fb4b6ce728c4bf895c5a314b78943c7f6588` |
| cost-diagnostics.json | 89,848 | `f065ee59a47dbb545a334256693fe6f7cf9c8e0376cf73efdcd04099ce512fa3` |

신규 source SHA: learning `6ac33cf4aa33b421a436961bc54f27c9b47a4d533ad0b3eda5dc7c6fa3ff2e9e`, trial `87429a05921331fb4fb2c0ab983e48060e064f8fc20ca15e9eee6694938827eb`. 원850 입력/code guard와 model/report binding을 사후 재검사했다. 원 Core/XML/주석·후보/부모 예측·원 권한·운영 UI·서버·다른 tracked 수정은 그대로다. 외부 API·모델 배포·Git commit/push0이다.

## 6. 다음 큰 단계

J2의 **학습 가능한 공동 decoder prototype**은 실제 숫자까지 얻었다. 하지만 학습 weights를 최종 운영 scorer로 승인한 것은 아니다. 다음은 원 계획의 **J3: 독립 작품 가족과 공통 평가표/공개 모델 비교 준비**로 진행한다. 고정 J2e와 미채택 J2f를 둘 다 비교 대상으로 보존하며, 자료 정리를 다시 무한 확장하지 않고 준비 범위를 timebox한다. 노출된 기존 cohort를 새 test로 이름만 바꾸지 않는다.

J4의 주요 개선 과제는 **화음 교체 필요성 대 유지 근거를 문맥적으로 구별하는 score**, true7음 대 장식 흡수, 기능적 root/국소 조성 및 누락 후보다. 글로벌 run/turnover/extra-member 비용 하나로 이들을 대신하면 안 된다. 이번 단일 실험의 실패를 근거로 이러한 큰 표현 문제를 먼저 다룬다. Loss 가중치/정규화·training 방식의 영향과 표현 부족은 분리 검증해야 하며, 아직 원인을 한 가지로 확정하거나 최적 hyperparameter를 찾은 것은 아니다.

Independent test/공개 모델의 같은 평가표·전체 Roman/전위/조성/NCT/cadence·운영UI 및 작곡/편곡 연결은 별도 완료 기준으로 남는다. 필요한 악보 피드백은 source-bound 이익/퇴행 사례에서 받되 사용자에게 모든 마디의 annotation 작성을 요구하지 않는다.
