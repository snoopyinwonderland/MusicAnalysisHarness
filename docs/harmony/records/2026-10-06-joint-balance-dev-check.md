# 단계86 — 고정된 26항·35항 모델의 Dev 비교

## 목적과 사전 고정

단계85에서 같은 Train 대조의 margin 합은 감소했지만 실제 공동 선택은 퇴행했다. 이를 성공으로 채택하지 않고, **기준 old26 / 단계83 역할35 / 단계85 공동35**를 원래 Dev에서 비교한다. 이번 작업은 다시 학습하는 단계가 아니다.

- 대상: 원래 Dev 72 record, 계산 가능한 63 graph. 원래 계산하지 못한 9개도 분모와 상태를 보존한다.
- Train 15작품군과 Dev 9작품군의 이름 ID가 겹치지 않는다. 악장/판본의 전체 중복 감사나 독립 Test를 대신하지 않는다.
- 전체 원 XML/IR, Fraction 시간축, grace projection, 붙임줄, 철자, 음표 ID, graph/edge와 raw cap을 바꾸지 않는다.
- 같은 cap6/2,000,000전이와 조건당 20초 cooperative guard. 중단 시 부분 승자를 반환하거나 재시도하지 않는다.
- 세 조건 순서와 모든 계수를 실행 전에 고정했다. 조건마다 새 특징 cache를 사용하되 공통 source/clock 준비를 공유하므로 통제된 속도 벤치마크는 아니다.
- 추가9계수가 정확히 0인 old26은 기존 exact batched 선택기를 사용한다. 같은 목적함수의 계산 최적화이며 새35항을 쓰는 조건과 알고리즘 실행량이 같다는 주장은 하지 않는다.
- fit/Dev 튜닝/sweep/checkpoint 선택/loss-augmented 탐색/reference-compatible 탐색/새 후보/정답 도달성 필터를 하지 않는다.
- 원래부터 노출된 Dev와 과거 계보 자료를 사용한다. 새 runner는 모든 새 예측을 봉인한 뒤 이번 평가용 참조 report를 읽지만 **블라인드 독립 정확도는 아니다.**

## 세 조건의 모델 출처

| 조건 | 고정된 계수 | 모델 SHA256 |
|---|---|---|
| `frozen_old26` | 단계75의 기존26항 + 문맥7/역할2는 0 | `2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf` |
| `frozen_member_role35` | 단계83: old26 + 문맥7 + 역할2 | `3f2c10e7899b3e66696be82bc64e41530829cb48c23707c456dcc3231033d346` |
| `frozen_joint35` | 단계85: 위35항 중28항의 제한 공동 조정 | `a65d2238ba5392e5fd05b7a2c3758f2d01f312eea70b003b6b31a534840027e2` |

모델의 봉인 report/audit/권리 계약을 검증하며 `model_weights`만 읽는다. `learning.fit`은 호출하지 않는다. 위 모델은 검증용 모델이며 old26을 현재 화면의 운영 엔진과 동일한 것으로 부르지 않는다.

## 구현 파일과 검증 설계

- `src/musicanote_harness/harmony_joint_balance_dev_trial.py`: 세 고정 점수의 원 graph 재선택, 예측 봉인 후 평가, 모든 attempted 사례/경쟁 경로 비용 저장.
- `tests/test_harmony_joint_balance_dev_trial.py`: 덮어쓰기 금지, Train 모델 봉인, no-fit tiny graph 전수 최적값, zero-extra legacy 동일성, wall/원 보류, 봉인→평가 순서, 공통 완료와 resource 손실의 분리.
- `scripts/validate_harmony_joint_balance_dev.py`: 단계85의 84모듈/906개 inventory를 유지하고 신규9검사 추가.
- `scripts/audit_harmony_joint_balance_dev.py`: 봉인 SHA/원 source·graph·clock/선택 비용·35항 ledger/scalar 상세 전이/모든 case/지표를 재생한다. 새 fit/search는 하지 않는다.

단위 검사 준비 중 잘못 가정한 `harmony_full_score.ZERO` 상수 때문에 1ERROR가 있었다. 기존 유효26항 fixture로 교정한 뒤 신규9검사 PASS. 실제 실행 전에 코드 변경을 끝냈다. 최종 관련 회귀는 **915검사/85모듈, failure0/error0, 107.986039초 PASS**다. 전체 repository suite나 915곡의 정확도를 뜻하지 않는다. 새4Python의 UTF-8/AST/공백 검사도 통과했다.

## 비교와 사례 보존 계약

전체72와 세 조건 모두 완료한 공통 subset의 root+members 시간 일치·작품군 macro·semantic boundary F1·전체 범위 일치를 함께 보고한다. pair별 공통 완료 subset도 별도로 저장한다. 계산 보류 때문에 정답을 잃은 경우와 완료 후 잘못 고른 경우를 합쳐 설명하지 않는다.

63 attempted scope 모두 다음을 보존한다. 좋아진 사례만 남기지 않는다.

- 원 전체 MusicXML/Canonical IR 경로와 SHA, 앞뒤 문맥을 재현하는 source 연결.
- 원 graph/시간 범위/ID와 세 조건의 실제 승자 또는 보류.
- 각 조건의 같은 계수 아래 세 승자 경로의 35항 특징·availability·cost.
- 참조-compatible 저장 witness가 있는 경우, 예측 봉인 **후**의 비용 대조. 이 witness는 분석 예측이나 inference input이 아니다.
- 이전 단계76의 모든63case 연결과 이번 평가 결과.

Unknown은 알려진0으로 바꾸지 않는다. 알려진 부분 합의 계산 정책과 원 whole-path availability를 함께 보존한다. 비용 차이는 확률/음악적 정확도/확정 NCT가 아니다. root+members 일치는 Roman/국소 조성/전위/NCT 전체 정확도도 아니다.

## 실행 결과

Actual `output/harmony-joint-balance-dev-2026-10-06-r1`은 **1,274.467090초/exit0/complete=true**로 완료했다. 원72 record/63 graph·60고유 범위·44,204edge·14전체 악장 source·9작품군을 유지했다. 평가 완전51/부분21을 보존했다. 원래 보류9를 재시도하지 않았다.

| 조건 | 새 계산 완료 | 새20초 보류 | 원9보류 | 전체 범위 일치(평가 가능51) | 근음+구성음 시간 | 작품군 macro | 참조 시간 coverage | 경계 F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 기준 old26 | 62 | 1 | 9 | 16 | 29.7550% | 45.0578% | 42.5904% | 76.1905% |
| 단계83 역할35 | 46 | 17 | 9 | 14 | 19.4632% | 25.3458% | 27.4679% | 61.8557% |
| 단계85 공동35 | 46 | 17 | 9 | 13 | 17.9230% | 23.9660% | 27.4679% | 61.7021% |

전체 참조 eligible time은 약357.083333quarter이며 원래 겹치거나 중복되는 범위가 포함된다. Unavailable reference time은 약242.083333quarter로 따로 남긴다. Macro는 root+members를 평가할 수 있는8작품군이며 나머지를0정답으로 채우지 않는다. 완료 개수와 coverage는 서로 다른 분모다.

세 조건이 **모두 완료한46 record**(8작품군, 전체 범위 평가 가능37/부분9)의 공통 비교:

| 조건 | 전체 범위 일치(평가 가능37) | 근음+구성음 시간 | 작품군 macro | 경계 TP/FP/FN | 경계 F1 |
|---|---:|---:|---:|---|---:|
| 기준 old26 | 11 | 65.5055% | 44.7735% | 30/10/11 | 74.0741% |
| 단계83 역할35 | 14 | 70.8581% | 46.4159% | 30/4/11 | 80.0000% |
| 단계85 공동35 | 13 | 65.2506% | 44.3525% | 29/2/12 | 80.5556% |

해석과 결정:

- **단계83 역할35**는 공통 완료에서 기준 대비 새 정답3/기존 정답 소실0·시간+5.3526%p로 도움이 된다. 전체에서는 기준이 완료한16개를 추가로 보류하고 그 안의 정답5개를 잃는다. 전체 수치의 악화를 순수 판정 오류로 설명하지 않는다. Train에서의 혼합 결과와 계산 부담이 남아 있어 운영 미채택을 유지한다.
- **단계85 공동35**는 단계83과 같은46개를 완료했으므로 이 둘의 정확도 차이는 coverage 차이가 아니다. 변경6 record/5고유 범위 중 시간 개선1/악화4/동일1, 기존 정답1소실/새 정답0이다. 시간70.8581%→65.2506%·macro46.4159%→44.3525%로 퇴행했다. 경계 F1만80→80.5556%로 오른 것은 FP2개 감소와 TP1개 소실/FN1개 증가가 함께 생긴 결과다. 성공으로 단정하거나 화음 판정 퇴행을 숨기지 않는다. **공동 조정 계수는 운영 미채택**이다.
- 기준 대비 역할35의 공통 변경16 record/15고유 범위는 시간 개선6/악화4/동일6이며 전체 변경32에는 추가 보류16이 포함된다. 공동35의 기준 대비 공통 변경14에는 개선4/악화6/동일4, 기존 정답 소실0/새 정답2다. 전체 변경30에는 같은 추가 보류16과 기존 정답5의 계산 소실이 포함된다.
- 기준의 이번 완료62개는 단계76의 같은모델 경로/비용과 **모두 동일**하다. 새20초 보류1개는 과거의 완료와 구별해 기록했다. 과거에는 같은20초 guard가 없었으므로 과거 전체 지표와 단순 속도·정확도 비교를 하지 않는다.
- 현재 운영 모델·화면·Claude 편곡 입력의 교체, 새 학습/Dev 계수 조정은 하지 않았다.

## 원악보 사례와 같은 계수의 비용

다음은 자동 검증 사례이며 human-validated 정답으로 새 승격하지 않는다. 사례-specific rule을 추가하지 않는다. 모든63case에는 전체 원 XML/IR·앞뒤 문맥·원note/sound ID·세 경로·각 같은계수 경쟁비용이 있으며 아래는 주요 차이를 설명하기 위한 발췌다.

### 1. Corelli op01n05d, m31 — F→C→F 정답 소실

`cont_42166b98e96d236572b6`, `[90,93)`, 6/8. 단계83은 참조와 같은 F `[90,91)`→C `[91,91.5)`→F `[91.5,93)`를 선택했다. 공동35는 앞1.5quarter를 A단3화음으로 병합하여 뒤F에 연결했다. 새 비용에서 잘못된 경로가 이전 정답보다 `-66019/6000000 ≈ -0.011003167` 싸다.

비용 차이(공동35 승자−이전35 경로)는 구성음 지지−.020314500, 외부음 설명+.072495917, 단순성/움직임−.126022000, 기능적 해결+.058625333, 문맥+.004212083이다. 원음표를 못 읽은 것이 아니라 이 비용의 상쇄가 오답을 고른 경우다.

- C5 `sound_7523ddb2bd52` / `note_74ceb9286939`: `[90,91.5)`, 1.5quarter 지속.
- F5 `sound_f2db11e8b013` / `note_c464dc189d9e`: `[90,91)`.
- E5 `sound_294c45de0f50` / `note_411a0d22abc1`: `[91,91.5)`.
- C4 `sound_028f26806a7a` / `note_8768da229b32`: `[91,91.5)`, 다른 기록 성부에도 동일음이 존재한다. 중복 성부를 삭제해 설명하지 않는다.
- F3 `sound_92e4e8f8c8c3` / `note_ea94fcf13879`: `[91.5,92.5)`.

Source package `10f5096b6d393d5b9309`. XML SHA `9e536828269db147f2ea1303c932ed5004927da2b809025be758814ac04249d1`, IR content SHA `337b11d08c2ceeba5459e402ea07c96a72ed4273ce9200143be49e5a29c3ddca`. [사례](../../../output/harmony-joint-balance-dev-2026-10-06-r1/cases/675a922cf55f7bbad819.json.gz), [원악보](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/10f5096b6d393d5b9309/source.musicxml).

### 2. Corelli op01n05a, m21–22 — 근음 D의 복구가 다시 소실

`cont_85d80062c7022aa8b8ff`와`cont_26c2f8b6fd72b9c9bd49`는 **같은 `[124,132)` 범위의 두 원record**다. 중복임을 표시하되 기존 분모를 사후 변경하지 않는다. 기준은 `[124,126)`에서 B♭-D-F♯를, 단계83은 참조의 D-F♯-A를 골랐다. 공동35는 다시 B♭-D-F♯를 골랐다. 새 비용 차이는 `-18231/32000000 ≈ -0.000569719`: 외부음−.003960156/단순성−.025454000을 문맥+.028844438이 완전히 상쇄하지 못한다.

실제 F♯4 `sound_d17fda059a3c` / `note_64c3e3dbebf1`는 `[120,126)`에서 지속하고, D3 `sound_80af4e71d064` / `note_5c81e541c6f1`는 `[124,126)`에서 들린다. B♭4 `sound_80106fe1131c` / `note_a0b2d62e2d7f` `[124,125)`→A4 `sound_5ee659c80afb` / `note_bc234d06035c` `[125,126)`도 존재한다. 이 관계를 기록하되 확정 NCT/특정 작품 예외로 쓰지 않는다. 뒤`[130,132)`의 참조G7도 세 모델 모두 G단3화음으로 남아 전체 일치는 모두false다. 따라서 복구/소실은 부분 시간2quarter의 변화이며 ‘전체 정답을 두 개 잃었다’가 아니다.

Source package `e157ec9d8d06c1083b45`. XML SHA `b767273cb4533fe347c15bac1dff36452ee9cc0ad6f669003c1ad641ac855f60`, IR content SHA `764ccc072f2164f90e993f4e850ef96bc2bd54e46e35422b19477992b4d38203`. [첫 사례](../../../output/harmony-joint-balance-dev-2026-10-06-r1/cases/e146c10d932bf1d6c977.json.gz), [중복 원record](../../../output/harmony-joint-balance-dev-2026-10-06-r1/cases/fde70cf5517606b2a93a.json.gz), [원악보](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/e157ec9d8d06c1083b45/source.musicxml).

### 3. Beethoven Sonata07-2 m63 — 실제 E♭/C를 읽고도 D3화음으로 병합

`cont_a34e326e65fe7c9b7662`, `[747/4,375/2)`. 참조는 F♯-A-C-E♭이며 이전 두 조건은 첫D3화음 뒤 F♯감7 구성음을 일부 고른다. 공동35는 전범위를 D-F♯-A로 병합했다. F♯4/A4는 `[186,187.5)`에 지속하지만, E♭4 `sound_28dc7a52b39f` / `note_067a13afd3e9`와 C5 `sound_b6dd140eeefb` / `note_8a519760cc0e`는 `[187,187.25)`에 실제로 존재한다. 새 비용 차이 `-745511/15750000 ≈ -0.047334032`: 외부음 비용+.301736429에도 단순성−.264507556/문맥−.072790714/역할−.011772190 이익이 커서 병합한다. 이를 XML 읽기 누락이나 확정 NCT로 단정하지 않는다.

Source package `a86ada3752f6688ea503`. XML SHA `53762a8b17faaeac368ddfa0cfccff60b050d49fc93c9f92476087dde4a211da`, IR content SHA `ce060889fac0841f9bd0a89aaa22def8f8d7d58739a08963ce9b36bde4df4077`. [사례](../../../output/harmony-joint-balance-dev-2026-10-06-r1/cases/2e759ecfbb34e7532a21.json.gz), [원악보](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/a86ada3752f6688ea503/source.musicxml).

## 사후 감사와 봉인

사후 감사 PASS/exit0. **5,945고유 SHA·72예측·14source·44,204원edge·154승자 비용·462같은계수 경쟁비용·108평가전용 witness 비용·618scalar 상세전이·63전체case/이전63case 연결·전체/공통 지표 재생**을 확인했다. 새 fit/decoder search0이며 원9보류를 보존했다. Actual 및 감사 중 실패0, Actual 시작 뒤 신규4code/test/script 변경0이다.

| 산출물 | SHA256 |
|---|---|
| report | `da0ede3f679ef066b0d09759a44723b4f7bad94596788a53122a8100a80107a8` |
| 실행 계약 | `6730e6d62eb4ca44aba329bc57db9244d2207c2ebc5d6a1135c88b3df5f68b77` |
| 예측 봉인 | `e738e417a36abeab9545a0d38be7ad2373e50f136ca994d4dfee436f32ef1d80` |
| 사후 감사 | `1e61c8bc17a5dbd348efc06aabd9e71f4be6b04c325958806b40ba599b98da14` |
| 관련 회귀 | `e969dbd99aefea87a92c46f99e17fbf51c9548107b8e61e368b238fc5a2218d7` |

상세 파일: [report](../../../output/harmony-joint-balance-dev-2026-10-06-r1/report.json), [감사](../../../output/harmony-joint-balance-dev-2026-10-06-r1/post-seal-audit.json), [회귀](../../../output/harmony-joint-balance-dev-validation-2026-10-06-r1.json). 원 Core/주석/부모 봉인/권한·운영/UI/서버·Claude Phrase/Motif/Composition/MusicSearch·기존5개 tracked dirty/Git를 보존했다. merge/commit/push/API 호출0이다.

## 다음 큰 문제 — 효과 없는 정답 보호 대조

실행 중 별도로 **봉인된 Train 자료만** 읽어 단계85의 zero-loss 대조를 확인했다. 총67개 모두 `negative_ids == target_ids`이고, 35항의 scored delta 및 알려진28항 gradient가 전부0이다. 따라서 이67개는 정답을 지키는 제약을 실질적으로 주지 못한다. 데이터가 있으니 보호가 작동한다고 표현하지 않는다.

다음 학습 단계에서는 이미 맞는 Train 구간에도 **정답 경로와 별개의 실제 오답 경쟁 경로**를 만들고, 정답의 비용이 더 낮게 유지되는지 비교해야 한다. 서로 다른 ID만 갖는 의미적으로 같은 분할을 오답으로 간주하지 않는다. 기존 정답과 새로 복구한 정답을 모두 보호하되 부족한 후보·부분 주석·unknown을 정답으로 채우지 않는다. Dev에서 발견한 오답을 학습 target으로 넣거나 Dev에 맞춰 계수를 고르는 작업은 하지 않는다.

이는 다음 단계의 계획이며 이번 세 모델/예측/봉인을 변경하지 않았다. 전체 Roman·국소 조성·NCT 의미 검증과 계산 보류를 줄이는 문제는 여전히 별개로 남는다.

## 재현

PowerShell, repository root. 새 output 이름을 사용하며 기존 봉인 산출물은 덮어쓰지 않는다.

```powershell
$env:PYTHONPATH = 'src;tests'
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_joint_balance_dev.py --prior-validation output/harmony-joint-balance-validation-2026-10-05-r1.json --output output/harmony-joint-balance-dev-validation-NEW.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_joint_balance_dev_trial --output output/harmony-joint-balance-dev-NEW
.\.venv\Scripts\python.exe -B scripts/audit_harmony_joint_balance_dev.py --root output/harmony-joint-balance-dev-NEW
```

화성 개발의 정본은 [메인 개발 문서](../README.md)와 [개발 로그](../DEVELOPMENT_LOG.md)다. 앞 단계의 제한 공동 조정/Train 퇴행은 [단계85 기록](2026-10-05-joint-score-balance.md)을 따른다.
