# 단계85 — 기존·문맥·구성음 역할 점수의 제한적 공동 균형

날짜: 2026-10-05. **로컬 비상업 연구·운영 미적용·편곡 연결 보류.**

제한 학습, 원 118개 Train 구간의 ordinary 재선택, 사후 감사를 완료했다. **공동 조정 모델은 미채택**이다. 학습 대조의 손실은 감소했지만 동일하게 완료된 102개 구간의 정답 진행은 56→52개로 줄었다. 아래에 이익과 퇴행을 모두 보존한다. 고정 Dev 비교는 아직 실행하지 않았다.

## 1. 목적과 사전 계약

사용자의 ‘더 진행’ 요청에 따라 [단계84의 비용 분해와 다음 계획](2026-10-05-score-balance-and-arrangement-reference.md)을 실행한다. A7 축소·실제 교체와 장식 설명·근음 소실의 비용 상쇄를 새2항만 올려 해결하지 않고 기존 점수와 함께 제한적으로 조정한다. 특정 작품/마디/피드백 ID를 규칙 분기에 넣지 않는다.

- source 특징은 같은35항이다. 원 후보·source XML/전체 IR·철자·음가·붙임줄/attack·명시 성부·nullable 관측·시간 분모·합집합 run·기존 DP는 바꾸지 않는다.
- **28조정/7고정**: 구성음 지지7 + 비구성음 설명5 + 단순성/이동7 + 문맥7 + 구성음 역할2를 조정한다. 입력 불확실성3와 functional-resolution4는 고정한다.
- 초기값은 단계83 봉인35계수다. 각 조정 계수는 **초기±1/20**와 원 의미별 bounds의 교집합 안에 둔다. 기존26의 sign/bounds를 유지하고 문맥/역할은 ±1/2 안으로 제한한다.
- 같은265Train 대조/67zero-loss 대조를 모두 남긴다. 새 negative/target 검색, correctness 기반 대조 제외, Dev 최고 checkpoint 선택을 하지 않는다.
- 3epoch, update tau cap1/20, gradient norm 기반 step, 매 방문 후 전체 평균, 원 precision을 사용한다. 전체795방문이며 no-update 방문도 평균에 포함한다.
- score에는 이전 정책의 known-local 부분 합이 들어갈 수 있지만 gradient는 두 경로 모두 whole-path known인 조정 차원만 사용한다. unknown을0 관측으로 만들지 않는다.
- 모델을 먼저 봉인한 뒤 원118구간에서 같은6raw/2M·20초 cooperative guard로 새 ordinary 선택을 한다. 참조 target은 fitting/사후 평가용이며 새 추론 선택 입력이 아니다.
- 현재 Dev를 재구성하거나 학습하지 않는다. 과거 부모 컨테이너에 이미 노출된 Dev 자료가 포함돼 있다는 사실과 이번 추론 미사용은 구별한다. 고정 Dev 비교는 다음 관문이다.

## 2. 파일과 변경 범위

- [제한 공동 학습](../../../src/musicanote_harness/harmony_joint_balance_learning.py):35항 점수의28차원 조정,7고정, trust box/권한/manifest/모델 바인딩.
- [Trial/Scorer](../../../src/musicanote_harness/harmony_joint_balance_trial.py): 원 source 준비/DP·source-bound receipt를 재사용한다. 학습 단계에서 기존26/7이 고정됐다는 이전 metadata는 새 계약으로 명시적으로 교정하고,35계수가 선택 동안 고정됐음을 기록한다. Proposal ID는 모든35계수와 경로를 묶는다.
- [학습 검사10개](../../../tests/test_harmony_joint_balance_learning.py), [선택/출처 검사5개](../../../tests/test_harmony_joint_balance_trial.py).
- [회귀 runner](../../../scripts/validate_harmony_joint_balance.py), [사후 감사 runner](../../../scripts/audit_harmony_joint_balance.py).

이전 봉인 code/model/report·원 Core/주석은 고치지 않았다. `K:\Music Composition`, MusicSearch의 Claude Phrase/Motif·현재 UI/운영 weights·서버·Git 및 기존 tracked dirty는 그대로다. 새 연구 모델을 후보 export/편곡 엔진에 주입하지 않는다.

## 3. 학습 결과 — 정확도가 아님

265대조,28조정 차원에 known 비0gradient가 있는 대조198,3epoch·795방문·571update다. Epoch 상태는 각각 update191/190/190, margin 만족71/71/71, bounds로 변화 없음3/4/4다. 모든7고정 계수는 같고 모든28조정 계수는 초기±.05 안이다.

Margin violation 합은194.2192426748194→185.96913550229837, violation 대조 수196→194다. **66대조는 margin이 악화**했다. 전체 손실 합 감소를 일반 화음 정확도 증가로 보고하지 않는다.

67zero-loss 대조는 모두 유지됐고 초기/새 모델에서 margin 위반0이다. 다만 이들의28차원 known delta가 모두0이므로 **기존 정답을 강하게 보호하는 독립 제약은 아니다.** 이후 새 ordinary 선택에서 기존 정답이 소실되는지 반드시 검사한다. 정답 대조를 평균에 포함한 것과 다른 경쟁 경로가 더 싸지지 않았다는 보장은 다르다.

현재 계수의 예: missing_root .147025→.190641, harmonic_run_count .021208→.041164, absent_seventh .814829→.768812, continuing_left_member .433274→.479520, supported extension .084749→.123608, durable change −.292985→−.312702. 표시 소수 대신 계산은 Fraction을 사용한다. 학습 후 새로운 튜닝/sweep/epoch 선택은 하지 않는다.

같은 이전 blind 경로와 target을 새 모델에서 재생한 gap은 K280 A7 −.010193058, Chopin literal held −.041490367, op18-1 근음 소실 −.405726134다. 이들 두 경로의 상대 비용은 아직 오답 쪽을 선호한다. K281-2의 이전 fresh와 target은 같은 경로여서 차0이다. **저장 pair 비용은 이번 fresh 승자나 최종 해결 여부가 아니다.** 새 DP 결과와 구별한다.

## 4. 검사와 수정 이력

처음14신규검사에서1FAIL/2ERROR였다. 두 ERROR는 toy의 마지막 음을 end=3으로 줄여 만든 검증되지 않은0음가와 wall guard에 Fraction 값을 준 fixture 문제였고, 정상 source/float guard 입력으로 교정했다. 원 decoder의 검증을 완화하지 않았다.

FAIL은 바뀌지 않아야 할 비격자 초기 계수를 평균/반올림하면서 바꾸는 새 학습기의 문제였다. Zero gradient 차원은 방문 중 그대로 유지하고 평균도 초기와 같으면 정확히 보존하도록 Actual 전에 수정했다. 다른 항목의 known update가 있어도 unknown 항의 비격자 초기값을 바꾸지 않는 회귀1개를 추가했다. 이후 신규15검사 PASS다.

최종 **906관련검사/84모듈 PASS·failure0/error0·104.983539초**다. Stage84의82모듈을 그대로 포함한 regression inventory이며 repository 전체나 음악 정확도 검사라는 뜻은 아니다. 작은 DAG의35계수 변경/전수 경로 최솟값, 기존35 초기 receipt 일치, guard 보류, source masks/gradient/bounds/권한·평균·metadata·ID를 검사했다.

완료 산출물의 SHA는 다음과 같다. 실행 시작 후 새 code/test/script 6개를 고치지 않았다.

| 파일 | SHA256 |
|---|---|
| model.json.gz | `a65d2238ba5392e5fd05b7a2c3758f2d01f312eea70b003b6b31a534840027e2` |
| run-contract.json | `7afa97608a31eda8746c5900fbfccc53c82f94373837a2b4363cb3ccc1b32e19` |
| training-vectors.json.gz | `a70a4e6a94a639622afc3255c70f0f6623c829744576e44d5fa3784b0072818c` |
| model-freeze.json | `a87aeaf27be9f7cf1ee783dde8ddb0829518aa425fe9961f33c83bb084b1ee7d` |
| validation r1 | `cf8483bf68c22f2a0a874fcdbe59fdc260177f8867024e6a2e740bbdb00ea0b5` |
| report.json | `d95ef8ed4d63968c752774db705e1b8472c77e67a5b7cfa09efbd36242929358` |
| post-seal-audit.json | `a8ca0d6efb86f08d54fa7d1cd5c601e4e1353883f34315da361d2cacb133f51d` |

[회귀 결과](../../../output/harmony-joint-balance-validation-2026-10-05-r1.json).

## 5. 실제 선택 결과와 채택 판단

Actual r1은 **761.455190초, exit 0**으로 끝났다. 같은 118개 Train 범위, 23개 전체 악장 source package, 15개 작품 가족, 원 후보망 60,129 edge를 사용했다. 118은 곡 수가 아니다. 여러 구간이 겹칠 수 있으며 이 자료는 학습/개발 자료다.

102개 exact 선택, 16개 wall-budget 보류다. 단계83과 완료/보류 범위가 정확히 같아서 새 자원 회복/손실은 각각 0이다. 완료 102개에는 14개 작품 가족이 있다. 각 완료 결과는 선언된 점수/후보망 아래의 최솟값이지 음악적 정답이나 확률이라는 뜻이 아니다.

### 전체 118개 — 보류를 분모에서 빼지 않음

| 점수 | 선택 / 보류 | 정답 진행 / 전체 범위 | 근음+구성음 시간 일치 | 작품 가족 macro | 시간 coverage | 정확 경계 F1 |
|---|---:|---:|---:|---:|---:|---:|
| 기존26 baseline | 118 / 0 | 58 / 118 | 77.5572% | 77.5655% | 100.0000% | 74.2358% |
| 단계83 구성음 역할 모델 | 102 / 16 | 56 / 118 | 57.6840% | 55.7712% | 73.6025% | 60.8247% |
| **단계85 공동 조정** | **102 / 16** | **52 / 118** | **56.0821%** | **54.2084%** | **73.6025%** | **59.1398%** |

### 공통 완료 102개 — 동일 범위에서 음악적 변화 대조

| 점수 | 정답 진행 | 근음+구성음 시간 일치 | 작품 가족 macro | 정확 경계 F1 |
|---|---:|---:|---:|---:|
| 기존26 baseline | 53 / 102 | 78.8937% | 76.9061% | 73.6196% |
| 단계83 | 56 / 102 | 78.3723% | 76.4567% | 74.2138% |
| **단계85** | **52 / 102** | **76.1959%** | **74.4862%** | **72.8477%** |

단계83 대비 12개 완료 경로가 바뀌었다. 기존 정답 6개를 잃고 새 정답 2개를 얻었다. 남은 4개는 두 모델 모두 전체 진행이 틀리다. 근음+구성음 일치 시간은 3457/24→3361/24 quarter로 4 quarter 줄었다. 기존26 대비 전체에서는 정답 10개 소실/4개 획득이며, 소실 중 5개는 원래 있었던 연구 엔진의 자원 보류다. 공통 완료 범위만 비교하면 기존26의 정답 5개 소실/4개 획득이다.

기존26은 현재 실험의 비교 기준선이지 현재 모든 화면 엔진을 뜻하지 않는다. 이 표는 Roman/전위/국소 조성/NCT 분류 정확도가 아니다. 참조가 없는 항목은 null/미평가로 남는다. 보류를 제외한 높은 수치만 운영 성능으로 제시하지 않는다.

**판단: 운영 미채택.** 손실 합이 약 4.25% 감소해도 실제 선택의 모든 주요 paired 지표가 낮아졌다. 제한 폭을 임의로 늘리거나 잘된 작품만 남기는 추가 fit/sweep는 하지 않는다. 이전 모델도 미채택이므로 단계83으로 새로 운영 승격하는 것이 아니라 **기존 운영 상태를 유지**한다.

총 실행 시간은 이전 단계83보다 짧지만 음악 점수에 따른 탐색 상태, 캐시, 부하가 달랐다. 이번 Actual 시작과 회귀 검사가 일부 겹쳤다. 통제된 반복 속도 측정이 아니므로 계산 성능 향상으로 보고하지 않는다.

## 6. 원악보 연결 사례 — 이익도 실패도 보존

모든 118개 [case packet](../../../output/harmony-joint-balance-2026-10-05-r1/cases/)은 전체 XML/부모 및 working IR의 경로·SHA, 원 note/sounding IDs, 시간 범위, 원 후보망 SHA, 이전 packet, 새 모델 SHA, 새 선택/이전 선택/기존26/저장 target의 같은 새 점수 receipt를 갖는다. 원 악보를 잘라 다시 파싱하거나 음가·철자를 바꾸지 않았다. 정답은 사후 비교에만 사용했고 사용자에게 이 결과의 검수 승인을 요구하거나 받지는 않았다.

### 6.1 K281-2 m6 — 이전 복구가 재소실

[새 case](../../../output/harmony-joint-balance-2026-10-05-r1/cases/cont_b495db380fce051abef0.json.gz), [전체 XML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/ccbca834fb4f500d0cec/source.musicxml), [전체 IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/ccbca834fb4f500d0cec/parent_ir.json).

- 범위 `[15/2,9)`, 3/8. 단계83의 E♭-G-B♭ `[15/2,8)` → C-E♭-G `[8,17/2)` → A♭-C-E♭ `[17/2,9)`가 정답이었다. 단계85는 처음 둘을 Cminor `[15/2,17/2)`로 병합했다.
- 원 E♭2 `sound_012b0e1557ef`/`note_aaf2d17cc63e`는 `[15/2,8)`, C4 `sound_de753a276549`/`note_543466cdfa0f`는 `[8,17/2)`다. C4를 앞 시간에 새로 소급 생성한 것은 아니다. **원 입력은 그대로인데 뒤에 제시된 C를 긴 Cminor 가설이 설명하는 비용이 더 싸졌다.**
- 같은 새 모델에서 오답 비용 .039060133 < target .040697700, 차 −.001637567이다. 구성음 지지 +.025350333와 역할 +.104234보다 단순성 −.081469와 문맥 −.0497529의 합이 더 큰 이익이다.
- 이 오답은 이미 pool의 `ctx_22ecbe583b5d9813ce6bed14`에 있었다. Gap +.030100589→−.001637567로 뒤집혔다. 따라서 모든 퇴행을 ‘못 본 경쟁 경로’ 탓으로 돌릴 수 없다. 고정된 연성 margin 목적과 공동 상쇄도 원인이다.
- XML SHA `9d5b37979ce0b92fa8ee275f9578fbecaf92ee15796db48f6f3d14e8769a5ae6`, IR SHA `423cec5ea75c0c056310f268b5413b71a80e563de7b3ce5e290f28329c998385`. 역사적 원 manifest의 exact-alignment 0/미승인 필드를 지우지 않았으며 이후 source/시간 관문과 제한 연구 계약을 상속한다. 자동 gold 승인으로 바꾸지 않는다.

### 6.2 Beethoven quartet op18-1 IV m269 — 새 정답 1

[새 case](../../../output/harmony-joint-balance-2026-10-05-r1/cases/cont_05a973a926c1c81874af.json.gz), [전체 XML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/c421f89dc2ddceec5a94/source.musicxml), [전체 IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/c421f89dc2ddceec5a94/parent_ir.json).

범위 `[2147/4,1075/2)`, 2/4. 이전 F-A-C-E 가설을 F-A-C로 바꾸어 참조와 일치했다. 베이스 성부는 F3 `[2147/4,537)` → E3 `[537,2149/4)` → F3 `[2149/4,1075/2)`다. 가운데 E3의 `sound_2499e7347984`/`note_bd140b9833c7`와 양옆 F3의 `sound_a04ae05137a5`/`sound_5b168af46292`를 보존했다. 이 형태를 F의 조건부 보조음 설명과 비교할 수 있으나 **NCT label의 최종 검수 완료는 아니다.**

동일 새 가중치에서 이전 F-A-C-E 경로보다 새 target 경로가 .051455800 싸다. 이 구간의 복구를 다른 m111의 A7 근음 소실까지 해결됐다고 확대하지 않는다. 같은 전체 source여도 두 문제의 역할이 다르다.

### 6.3 Chopin op33-1 — 새 정답 2

[새 case](../../../output/harmony-joint-balance-2026-10-05-r1/cases/cont_059eaab892e6b5a75494.json.gz), [전체 XML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/a10b687fd43585ed8ac6/source.musicxml), [전체 IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/a10b687fd43585ed8ac6/parent_ir.json).

범위 `[54,58)`에서 F#major → C#7 → F#major의 이름은 유지하고 첫 경계를 223/4→56으로 늦춰 참조와 일치했다. 선율 E#5 `sound_532499b0a606`/`note_1a16568f3d08`는 `[223/4,56)`의 짧은 음이다. 반면 C#4, G#4, C#5, E#5, B5의 다음 attack군은 56에 시작한다. 조기 선율음을 이유로 다음 화음 전체를 일찍 시작시키지 않는 쪽이 선택됐다. 이것도 전체 NCT 확정으로 저장하지 않는다.

새 경로는 이전 경로보다 .001449549 싸다. XML SHA `1e5592088dc107ece936d427f216f3d46fa7106de309198df07f7d87d914c864`, IR SHA `108f32fe6dfba1ccb1308dfc0ea5cc0cd362c4b057e8e1494b9ed131ebe4ed65`다.

### 6.4 Beethoven sonata 03-2 m53 — 새 과병합

[새 case](../../../output/harmony-joint-balance-2026-10-05-r1/cases/cont_665010fd6fb925791874.json.gz), [전체 XML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/be2c6ed93388f5ce8d17/source.musicxml), [전체 IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/be2c6ed93388f5ce8d17/parent_ir.json).

범위 `[104,419/4)`, 2/4. 참조/이전의 Cmajor → Gmajor `[835/8,209/2)` → Cmajor가 새 선택에서 전체 Cmajor로 병합됐다. 짧지만 실제 B1/B2, D3/D4, G3가 함께 attack한다. B1 `sound_80260118e5e3`/`note_5834aaa455b5`, D3 `sound_335091d9c006`/`note_4caf5f4af2e8`, G3 `sound_91455760abe2`/`note_e0b2c340bbdf`다. **짧다는 이유만으로 실제 수직 화음군을 단일 장식음처럼 처리할 수 없다.**

오답−target 비용은 비구성음 설명 +.146994767와 단순성/이동 −.213846000의 합 −.066851233다. 기존보다 run-count/complexity 비용이 커지면서 이 실제 중간 화음을 지우는 것이 더 싸졌다. 새 오답은 기존 pool의 negative에 없었다. XML SHA `9696f1045d4bcde1709834ccbad47eadbcea8ed7b57f246f03258b0f053944aa`, IR SHA `63442f61150f4df4041514197fc3fb5987784b3b484095981984598e330999f5`다. 운영용 근본 위치/전위 확정값을 추가한 것은 아니다.

### 6.5 나머지 변경과 계속 남은 큰 반례

정답 6개 소실은 K281-2 위 사례, sonata 03-2 위 사례와 아래 4개다.

| case ID | source / quarter 범위 | 변화 | 일치 시간 |
|---|---|---|---:|
| `cont_db4f0a962816216e4545` | 03-2 / `[11,25/2)` | 첫 C#7의 B를 빼 C#major로 축소 | 3/2→3/4 |
| `cont_f41266f5b8bb32113d13` | 03-2 / `[23/4,13/2)` | 양쪽 B7을 D#dim으로 바꾸며 B 근음 소실 | 3/4→1/4 |
| `cont_3c1d12613ca1c3f676ee` | op30-2 / `[15,17)` | Gmajor→Dmajor를 Gmajor로 병합 | 2→1 |
| `cont_af060991925775e5a143` | K280-2 / `[447/4,113)` | G-B♭-D♭-F를 B♭minor로 바꾸며 G 근음 소실 | 5/4→0 |

K281-2를 제외한 새 정답 소실 5개는 pool 밖의 새로운 negative 경로다. Zero-loss 방문 유지가 이들 새로운 경쟁을 막지 못했다. 위 모든 case는 같은 이름의 파일로 `cases/`와 report에 남으며 source 경로/ID/이전 경로/target/새 receipt를 함께 읽을 수 있다.

두 모델 모두 오답인 변경 4개도 제외하지 않았다: `cont_77516ace33e61d09a1a8`(03-2, 일치11/8→1), `cont_9df37946f35905644fbd`(Corelli op01n03b,1→1/2), `cont_8a3b05f4ac110414df84`(K280-2,0→0), `cont_846309fad7a207f7989e`(sonata01-2,0→0). 이 목록과 위 8개가 총 12개 변경이다.

이전에 집중한 K280 A7 `cont_9a13eb950949fd01e0e7`, Chopin held `cont_9d29b21fdced352125a1`, quartet m111 `cont_2cb186940b3312c2a145`는 **이번 fresh도 경로가 같고 계속 오답**이다. 새 비용의 fresh−target은 각각 −.010193058, −.041490367, −.405726134다. 첫 gap이 작아진 것을 실제 해결로 보고하지 않는다. 원음/역할의 자세한 반례는 [단계83](2026-10-05-member-role-interactions.md)과 [단계84](2026-10-05-score-balance-and-arrangement-reference.md)에 연결해 보존한다.

## 7. 사후 감사와 실행 재현

[최종 report](../../../output/harmony-joint-balance-2026-10-05-r1/report.json), [사후 감사](../../../output/harmony-joint-balance-2026-10-05-r1/post-seal-audit.json).

- **4,129개 고유 SHA**, 봉인 입력 reload 4,122개, training vector 265개, 학습 update/평균 산술 재생 PASS.
- 원 118개 scope, 23개 전체 source, 60,129 edge, 독립 상세 경로 비용 440개와 검증 대상 scalar/detailed 전이 387개를 재생했다. Aggregate/서로 다른 비용 항의 합/known masks/source ID·span이 같다.
- 감사는 추가 decoder 탐색이나 Dev 실행을 하지 않았다. 학습 산술을 재생했지만 새 모델/checkpoint를 저장하지 않았다. 전수 원 후보망의 최솟값을 다시 탐색한 것과 구별한다.
- report는 input 4,001, artifact 122, code 442개의 경로별 pin을 갖는다. 서로 중복되는 경로가 있어서 합계와 고유 SHA 수가 다르다. 부모 source/model/code/원 Core·주석/운영 weights는 그대로다.
- Actual/audit 실패·중단 0이다. 사후 읽기 전용 요약에서 JSON Fraction을 coefficients에 바로 준 1 ValueError는 Fraction으로 변환하여 교정했고, 저장 모델·실험 코드를 바꾸지 않았다. PowerShell properties count의 enumeration 출력과 긴 stdout은 저장 JSON의 길이/정본 table로 확인했다.
- 최종 문서 3개의 strict UTF-8/대체문자/혼입 문자/공백을 확인했고 이 기록의 로컬 링크 25개가 존재한다. 새 코드 6개의 AST/UTF-8/공백/Actual 시작 SHA도 같았다. 별개 tracked dirty 5개 목록은 유지하며 수정하지 않았다.

관련 회귀 재실행은 반드시 새 파일 경로를 사용한다.

```powershell
$env:PYTHONPATH = 'src;tests'
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_joint_balance.py --prior-validation output/harmony-score-balance-validation-2026-10-05-r1.json --output output/harmony-joint-balance-validation-REPRO-r1.json
```

Actual도 새 디렉터리에만 실행한다. 코드/source가 봉인 pin과 달라졌으면 오류로 중단하며 새 버전 실험으로 구분해야 한다.

```powershell
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_joint_balance_trial --output output/harmony-joint-balance-REPRO-r1
.\.venv\Scripts\python.exe -B scripts/audit_harmony_joint_balance.py --root output/harmony-joint-balance-REPRO-r1
```

이미 있는 디렉터리/audit에 이 명령을 다시 실행하여 덮어쓰지 않는다. Wall-budget은 cooperative guard여서 반복 실행 시 완료 범위가 달라질 수 있다. 이번 모델/원 파일은 봉인 정본이며 재실행의 지연이나 resource 변화를 음악적 정확도 변화와 분리한다.

## 8. 다음 관문과 편곡 연결 상태

1. 이번 모델과 초기 모델을 더 고치지 않고 **고정 Dev의 같은 입력/후보망/예산에서 기존26·단계83·단계85를 비교**한다. 단계85의 Train 퇴행을 숨기지 않고 일반화 진단으로만 사용한다. 이미 노출된 Dev이므로 independent blind test라고 부르지 않으며 최고 epoch/Dev 점수에 맞춘 학습을 하지 않는다.
2. 이후의 학습 개선은 새 DP 오답을 포함하는 대조와 **실제로 구별되는 정답 보호 조건**을 우선한다. Zero delta 방문이나 평균 손실만으로 안전성을 주장하지 않는다. Short multi-voice chord change와 단일 성부 장식, 이미 앞 화음의 구성음인 새 attack, 실제 근음 소실을 구별하는 큰 의미/점수 문제를 다룬다. 특정 작품/마디 분기를 만들지 않는다.
3. 생성 연결 전에는 국소 tonic/기능/Roman/베이스·전위와 NCT 대안의 의미 계약, 요청한 전체 범위 coverage, 별도 정확도, melody-only 화성 계획과 given-chord 국소 재화성의 8–16마디 A/B가 필요하다. **Claude 추론기 교체와 실제 편곡 연결은 계속 보류**한다. 이번 실패를 source 주석/given 화음을 덮어쓰거나 hard generation constraint로 쓰지 않는다.

이번 turn은 새로운 음악 이론/전체 NCT 구현을 완료한 단계가 아니라, 기존 35개 음악적 근거를 실제 선택에 공동 반영한 제한 실험과 검증이다. 전체 Test/공개 모델 비교, Roman/조성/전위/종지/NCT의 최종 정확도, 장문 자원 보류 및 작곡·편곡 생성 검증은 남아 있다.
