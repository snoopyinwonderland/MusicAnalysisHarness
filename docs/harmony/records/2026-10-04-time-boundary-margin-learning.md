# J2c — 시간·의미 경계 손실을 반영하는 공동 선택 학습

기록 ID: **HARM-DEV-20261004-51** · 2026-10-04. [J2b](2026-10-04-structured-weight-learning.md)의 과병합 퇴행을 보완하는 실험이다. [J0–J5](2026-10-04-joint-decoding-and-benchmark-review.md)의 J2 후속이며, 기존 고정 score/후보/원주석·이전 실험 결과를 변경하지 않는다.

## 실행 전 고정한 계약

새 음악 종류나 특정 악보 예외를 추가하지 않는다. 기존11개의 관측 특징, original lattice/6segment cap과322개 동일 train/dev 문맥을 유지한다. 일반 추론은 기존 exact decoder로 수행하며 주석을 받지 않는다. **학습 때에만** 완전 train reference와 아래 loss를 받는 adversary 탐색을 추가한다.

```text
시간 오류 = 근음+철자 구성음이 틀린 시간 / 문맥 전체 시간
경계 오류 = (의미 변화 경계 FP + FN) / max(1, 원주석의 의미 변화 경계 수)
loss = 시간 오류 + λ × 경계 오류
학습 adversary = argmin(관측 특징 비용 − loss)
latent target = 기존 후보 중 train reference와 양립하는 최소 비용 완전 경로
violation = target 비용 − adversary 비용 + loss
δ = adversary 특징 합 − target 특징 합
τ = min(1/10, violation / ||δ||²)
weight ← weight + τδ
```

- 미리 정한 두 arm: `margin_time_only`의 λ=0, `margin_time_boundary`의 λ=1/4. 5epoch/작품군→sample ID 순서/평균 weight, 절댓값 한도4와1e-6 weight 정밀도,2M transition 예산을 사용한다. Dev를 보고 epoch·λ·arm을 소급 선택하지 않는다.
- 두 새 arm 사이에서 경계 loss의 영향을 분리한다. J2b와는 loss뿐 아니라 **업데이트 방법도** perceptron→capped passive-aggressive로 달라지므로 단일 원인 실험이라 부르지 않는다.
- 모든 시간/손실/특징/점수 계산은 Fraction이다. Weight만 제한 정밀도로 반올림하며 IR 시간 grid는 변경하지 않는다. Clip/반올림 이후의 실제 같은 pair violation을 저장한다. 정확한 margin 충족을 자동 주장하지 않는다.
- loss는 probability가 아니다. 주석 의미 경계가0인 문맥의 FP가 여러 개면 normalized boundary error가1보다 클 수 있다.
- 경계는 단순한 annotation onset/edge 분할이 아니라 **인접 근음+spelled members의 변화**다. Same-signature 구간을 나눈 것에는 FP가 없다. Edge 내부 경계는 FN, edge onset의 잘못된 변화/미변화는 FP/FN으로 분해한다. `[start,end)`와 strict interior로 중복 계상을 막는다.
- Adversary는 endpoint/segment count/previous signature 상태의 exact DAG이며 원 후보를 삽입하지 않는다. 예산 초과는 winner 없이 보류하며 업데이트하지 않는다.
- 양의 violation인데 특징 벡터가 같으면 weight로 분리할 수 없는 **feature collision**으로 기록한다. 가짜 업데이트나 NCT 설명을 만들지 않는다. 기존 unavailable NCT/해결/key/metric/structural bass를 관측 사실로 바꾸지 않는다.
- Fit에는 train만 들어간다. 완전 compatible path를 가진110개 예정 범위만 학습하고 나머지 원322문맥을 평가에서 제거하지 않는다. 새 추론 API는 reference/loss 인자가 없으며 confidence=null이다.
- 기존 [로컬 연구 사용 계약](../experiments/2026-10-04-local-research-training-use.json)의 제한 범위를 유지한다. 원 manifest 권한은 변경하지 않고 상업 적용·외부 API·체크포인트 배포를 하지 않는다. 출처 licence 면제/상업 권리 확인으로 해석하지 않는다.

결과 보고에서는 전체/root+members 시간·작품군 macro·전체 문맥 일치·정확 경계 precision/recall/F1을 같은 분모로 모두 제시한다. 한 지표가 오르면 다른 지표의 퇴행을 숨기지 않는다. 두 모델은 연구 비교 후보이며 이번 측정만으로 운영 weight를 변경하지 않는다. 기존 개발 자료에서 나온 수치는 독립 test 정확도가 아니다. 이 비교 뒤 큰 후속은 후보 밖 오류와 아직 점수에 들어가지 않은 실제 NCT/해결·교체 근거이며, 자료 관리 작업으로 되돌아가 목표를 늘리지 않는다.

## 구현·검증 및 실제 결과

[새 학습기](../../../src/musicanote_harness/harmony_margin_learning.py), [동결 비교 실행기](../../../src/musicanote_harness/harmony_margin_learning_trial.py), [검사](../../../tests/test_harmony_margin_learning.py)를 별도로 추가했다. 기존 J2a/J2b 코드는 불변이다. 실행기는 입력·옛 code/report·출처 SHA와 가족 split을 검증하고 고정 선택을 재계산한다. 양쪽 모델 학습을 마친 뒤 label-blind prediction을 모두 만들고 evaluator가 주석을 읽는다. Output은 새 폴더만 허용한다.

구현과 신규21+기존106=127검사/1.325초, Python3파일 AST를 확인했다. 작은 합성 DAG의 모든 완전 경로를 열거하여 loss와 evaluator의 시간/FP/FN이 같고 adversary 최적 비용이 exhaustive 결과와 같은지 검사했다. Clip·feature collision·자원 보류·사용 계약·모델 변조·원자료 hash·양쪽 arm의 실제 물리 fixture도 검사한다. 상위 receipts와 source licence는 합성 fixture이며 corpus 검증과 구별한다.

실제322문맥을 **647.491493초 / exit0**에 비교했다. Train270중110reachable 완전 문맥/각5epoch·550tick을 학습했다. 제외160은 compatible complete path 없음83, partial/미지원49, lattice unavailable28이다. J2b와 동일하며 train의 전체 partial65와49를 혼동하지 않는다. 양쪽 모두291선택/31원보류(28baseline_not_ready·3edge budget), 완전256/부분66, 적격7895/8quarter를 유지했다. 이 시간은 겹치는 개발 문맥의 합이지 고유 악보 길이가 아니다.

| 지표 | J2a 고정 joint | J2b perceptron | 시간 margin | 시간+경계 margin |
|---|---:|---:|---:|---:|
| 전체 문맥 일치 / 완전256 | 50 | 46 | 42 | 45 |
| 전체 root 시간 일치 | 40.47% | 38.01% | 38.78% | 37.67% |
| 전체 root+spelled members 시간 일치 | 30.15% | 28.84% | 28.37% | 26.71% |
| 전체 작품군 macro root+members | 38.35% | 37.26% | 33.72% | 30.75% |
| 의미 경계 F1 | 57.26% | 41.12% | 48.01% | 41.89% |
| Train 문맥 일치 / 완전205 | 44 | 40 | 38 | 40 |
| Train root+members 시간 일치 | 30.08% | 28.64% | 27.46% | 25.67% |
| Dev 문맥 일치 / 완전51 | 6 | 6 | 4 | 5 |
| Dev root+members 시간 일치 | 30.45% | 29.76% | 32.46% | 31.35% |
| Dev 작품군 macro root+members | 31.71% | 36.41% | 30.03% | 28.75% |
| Dev 의미 경계 F1 | 59.89% | 42.47% | 54.09% | 45.21% |

시간 margin의 경계 TP151/FP35/FN292, precision81.18%/recall34.09%다. 시간+경계 margin은 TP124/FP25/FN319, precision83.22%/recall27.99%다. 고정 점수의 TP209/FP78/FN234보다 FP는 줄었지만 FN이 늘었다. **경계 loss를 넣었다는 사실만으로 필요한 화음 교체를 복구하지 못했다.** 시간-only는 J2b 대비 경계F1을 회복했지만 고정 점수에는 미달한다. Dev의 시간 일치는 두 arm 모두 소폭 상승했으나 전체 일치·macro·경계는 퇴행하므로 전체 개선으로 보고하지 않는다. 기존 segment-only의 전체 시간31.01%도 유지한다.

고정 joint 대비 시간 arm의 전체 일치 개선8/퇴행16/유지정답34/계속오답198/부분66, 시간+경계 arm은9/14/36/197/66이다. 학습 가능한110train 안에서도44→38/40이므로 단순한 train 개선/dev 퇴행식 과적합이라고 단정하지 않는다. Loss/update 방법·특징 표현·latent target과5epoch 수렴은 모두 진단 대상이다.

시간 arm의 업데이트104/102/96/95/95=492, 양의 margin feature collision6/7/9/9/9=40회/11고유문맥이다. 시간+경계 arm은107/103/99/98/98=505, collision3/5/6/6/6=26회/7고유문맥이다. 업데이트 예산 보류0, 실제 clipped update0, 같은 pair의 violation이 줄지 않은 업데이트0이다. 그러나 마지막 epoch도95/98업데이트이므로 수렴이나 모든 margin 충족을 입증하지 않는다. Collision 횟수는 작품 수가 아니다.

## 실제 음악·특징 진단

[선택 변화12행/11고유문맥](../../../output/harmony-margin-learning-2026-10-04-r1/selection-changes.json)은 양쪽 arm 각각 큰 시간 개선3/퇴행3을 사후 선택했다. Epoch/weight/arm을 다시 조정하는 데 사용하지 않았다. 각 행에 원 entry/XML 경로·context/search 물리SHA·reference cell·고정/이전/새 예측의 group ID·유리수 범위·철자와 평가를 보존했다.

- **개선, Beethoven quartet03op18-3_02 Dev:** `cont_fefea272c529502d810d`, `[911/8,233/2)`. 시간 arm은 B♭ triad→F triad로 일치 시간을0→5/2quarter로 늘렸다. 동일 B♭ 화음을 둘로 나눈 raw partition도 보존했다. 개선 사실과 불필요 분할을 함께 기록한다.
- **퇴행, Chopin BI105-4op30-4:** `cont_635ba41c28793857d7b4`, `[6,35/4)`. 고정 D# root7→G# root7→D# root7의11/4quarter 전체 일치가 D# triad 하나의 의미로 바뀌어0이 됐다. 구성음 누락 비용·추가 구성음 비용을 학습했어도 필요한7화음을 선택하지 못한 사례다.
- **과병합 유지, Chopin BI126-3op41-1:** `cont_351b01f7c138841b1279`, `[242,247)`. J2b가 잘못 합친 A# diminished triad를 시간+경계 arm도 유지했다. Raw2segment로 나눴지만 같은 signature라 의미 경계는0이다. 고정4/5quarter 일치→0이라는 퇴행을 복구하지 못했다.
- **같은 화음을 분할하는 현상:** Corelli `op01n01b` Dev `cont_5a5f9e68f26d8e26ed78`, `[32,38)`의 시간+경계 결과는 F triad 하나의 의미를6개 raw edge로 표현했다. 의미 일치2→4quarter의 개선은 있지만6개의 서로 다른 화음을 찾은 것이 아니다.

두 arm의 평균 segment_count 비용은0.015→**−0.070648/−0.191968**로 바뀌었다. 반면 member_turnover 비용은0.02→0.203069/0.428154다. 최대6개 raw edge를 선택한 문맥은 고정0→34/39이며, 실제 화음 교체보다 same-signature 분할로 보상을 받는 경우가 있다. 이는 **기보/후보 edge 수와 음악적 화음 수가 다른 점수 표현 문제**다. Signed DAG의 수학적 최적해라는 사실이 이 결과를 음악적으로 좋게 만들지는 않는다. 사후 음표/구간 삭제나 source ID 병합으로 숨기지 않았다.

[Feature collision 원증거2사례](../../../output/harmony-margin-learning-2026-10-04-r1/feature-collisions.json)에서는 학습 adversary/compatible target의11차원 Fraction 벡터가 완전히 같음을 실제 재계산했다. 원 note/sounding ID는 group과 source context에 연결하며 model/ref/학습epoch·원주석·부모SHA를 보존한다.

1. Mozart `K280-2`, `cont_0566ef20e6a0f5b38d99`, `[1,3)`: F `{F,A,C}`와 F `{F,A♭,C}`의 벡터가 같다. 비구성음 노출0, missing member1/3, root 누락0 등이다. 관측되는 부분 음정/현재 좁은 문맥만으로 빠진3음을 구별하지 못한다. 조표 적합성/조성 후보·앞뒤 문맥을 연결할 근거가 필요하다.
2. Mozart `K280-1`, `cont_7ac4f91c9a34b723f8cc`, `[344,1379/4)`: F `{F,A,C#}`와 F `{F,A,C}`가 같은 비구성음 노출1/3·missing member1/3·root 누락0·segment2·전이0을 갖는다. 서로 다른 실제 음의 의미를 단순 합계가 같게 만든 사례다. 시간·박절과 동일 성부 준비/해결을 구별하는 근거가 필요하다.

이 **특정 pair는 어떠한11개 선형 weight로도 상대 비용을 다르게 만들 수 없다.** 일반 추론의 group ID tie-break가 우연히 정답을 고를 수는 있으므로 collision=현재 추론 오답이라고 확대하지 않는다. 모든 오류가 collision 때문이라고도 단정하지 않는다. 실제 margin 감소와 음악적 선택 개선은 별개이며 경계 loss만으로 부족하다는 실증이다.

## 결정과 다음 큰 단계

**새 weight 두 개 모두 채택 보류.** 고정 score/기존 segment-only 비교를 유지하고 운영 악보 화면은 변경하지 않았다. Dev에 맞춘 λ/epoch 반복 실험도 하지 않았다. 원 XML/Core/주석/후보/과거 결과·권한과 사용자 교정은 불변이다. 기존 코드2개를 포함한735고유 입력/코드SHA를 종료 및 사후 재대조하여 변경0을 확인했다.

J2d의 큰 단위는 **이미 작성한 음악적 근거를 선택 점수에 연결**하는 것이다. 계속 weight/자료 관리만 보완하지 않는다.

1. **분할에 덜 흔들리는 표현:** raw edge 수와 semantic chord change 수를 분리하는 새 feature version을 설계한다. Same-signature 분할만으로 음악적 이득을 얻지 않게 하고, 분산화음의 지속과 부분 구간에서 안 보인 구성음을 별도 관측 근거로 표현한다. 기존 segment_count 의미는 소급 변경하지 않는다.
2. **조성·성부·해결·문맥 연결:** 조표는 관찰, local key는 분석 후보로 유지한다. Source 범위 안팎의 실제 tie/attack·음가·박절·bass와 동일 성부의 준비/해결을 점수에 연결한다. 교재/기존 규칙의 근거를 재사용하고 NCT·Secondary 여부는 가정별 경쟁으로 둔다. 정답 주석을 추론 feature로 가져오지 않는다.
3. **같은 분모에서 재측정 후 범위 확대:** 새 특징의 ablation/후보 recall/선택을 한 번에 비교한다. 후보 밖85·연결22·cap2·보류15의 ceiling은 별도 문제이며 weight로 해결했다고 하지 않는다. 이후 독립 작품/전곡·공개 모델 공통평가와 Roman/전위/key/NCT/cadence 소비로 진행한다.

이 진단은 계획/우선순위이며 J2d 구현 완료가 아니다. 이번 실패로 공동 구간·화음 선택 방식 자체가 불가능하다고 결론내리지 않는다. 더 복잡한 모델/AI를 쓸 때에도 먼저 실제 관측·근거를 연결해야 한다.

## 재현·파일·보존

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m unittest test_harmony_margin_learning test_harmony_structured_learning test_harmony_scored_decoder test_harmony_lattice_recall test_harmony_candidate_recall test_harmony_progression_search
```

실행기에는 J1 recall/lattice, J2a baseline, J2b learned report와 기존 사용 계약을 각각 물리 SHA로 pin한다. `--recall --lattice --baseline --learned --contract`, 각각의 `--expected-*-sha`와 새 `--output`이 필요하다. 아래 report의 input/code hash와 J2a/J2b 기록으로 완전히 재현 가능하며 기존 output은 overwrite하지 않는다.

새 실제 output은5파일 **11,771,744B**다. Physical file hash는 들여쓰기 전 canonical JSON/model ID hash와 구별한다.

| 파일 | 크기(B) | 물리 SHA256 |
|---|---:|---|
| [report.json](../../../output/harmony-margin-learning-2026-10-04-r1/report.json) | 9,135,364 | `abea4f003bc6dae1947ede55b23ed2c7da9944e079e59015f957ec472d378193` |
| [시간 model](../../../output/harmony-margin-learning-2026-10-04-r1/margin_time_only-model.json) | 1,208,989 | `29b4cbae4fd108ad2c5511c9465bce06bb54ff3395e09159877e42a2fc92dc9b` |
| [시간+경계 model](../../../output/harmony-margin-learning-2026-10-04-r1/margin_time_boundary-model.json) | 1,234,113 | `d4ffe87d14eb14fc62541a5513c3c05b7fe120a19c63786659f8364d671369ad` |
| [선택 변화](../../../output/harmony-margin-learning-2026-10-04-r1/selection-changes.json) | 177,177 | `3a81c05a00e4e18ddb4c4645c05ed242cc84b6e1ea7e725c2864762b67393361` |
| [특징 충돌](../../../output/harmony-margin-learning-2026-10-04-r1/feature-collisions.json) | 16,101 | `5ac92419f00244957cee8c18fbd1cbc1ce784b192f17b74f7813185b9c2c9fcd` |

학습 코드 SHA `c2ce422349edda4bcde590cdbfc0a80ed7c5ed259ca52abc25992cfbdaf04234`, 실행기 SHA `6a9e97545338a6b1da369040e87056016ee30b02aa60a541966be70c972e8d1d`다. 외부 API·원자료/weight 배포·상업 운영·UI/서버 교체·Git commit/push0이다. 초기 사후 출력에서 불필요한 전체 split/epoch 상세를 한꺼번에 출력하여 도구 출력이 잘렸고, 항목을 축약해 다시 읽었다. 원 파일/예측은 변경하지 않았다.

최종 문서 검증: 변경4문서 strict UTF-8/replacement0·로컬 링크282/누락0, 메인 현재 상태/로그 기록51/장기 계획 링크 등록은 각1개다. 여러 문서 patch의 부분 적용 뒤 도구가 재시도해 실패로 보고했으나 실제 적용된 메인/로그는 확인해 유지하고 미적용 계획만 별도로 적용했다. 중복 기록과 실행 중 상태는 없다. `git diff --check` exit0이며 기존5개 tracked 파일의 LF→CRLF 경고는 유지한다. 원735고유 입력/코드 SHA 사후 재대조 변경0이다. 다른 기존 수정은 보존했고 이번 계획 단락만 추가했다.
