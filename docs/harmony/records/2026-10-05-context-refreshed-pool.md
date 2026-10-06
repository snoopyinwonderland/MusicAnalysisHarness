# 단계82 — 새로 드러난 오답과 정답 보호를 포함한 문맥 점수 재검증

## 1. 질문과 사전 계약

단계81은 계산 효율만 개선했고 음악 점수를 개선하지 않았다. K280의 F화음 과분할은 새 선택 경로가 이전 pool에 없었지만, genuine A7의 축소 경로는 이미 학습 대조에 있었다. 따라서 **pool의 빈틈과7특징/학습 한계**를 구별해야 한다. 외부음 잔여와 새 전용 구성음 근거는 같은 sound를 포함할 수 있으나 서로 다른 가설 관계이므로 중복 자체를 버그로 확정하거나 한쪽을 임의로 삭제하지 않는다.

이번은 큰 오류에 대한 한 번의 통제된 Train 갱신 실험이다. 이전254대조에 이전 모델의104완료 중 sample+ordered raw IDs로 새로 나타난 모든 경로를 추가한다. 정답 여부로 거르지 않고 zero-loss 경로도 보호 대조로 남긴다. 기존14보류는 mining 성공으로 바꾸거나 부분 경로로 대신하지 않는다. 같은 경로는 재가중하지 않는다.

학습은 기존 방식 그대로 새7계수0에서 시작해3epoch, cap1/20, bounds±1/2, exact Fraction 및6자리 quantization, 모든 post-visit 평균이다. 기존26계수는 고정한다. 이전 미채택 계수에서 이어 학습하지 않는다. 참조 compatible target은 원 봉인 Train target이며 새로운 label-aware target/adversary 탐색은 하지 않는다. Known-both gradient와 지역 known-only score/null·partial 관측 계약을 보존한다. 특정 작품·마디 조건식,7화음 hard gate, 음 삭제, 추론 중 주석 조회를 넣지 않는다.

모델 고정 후 원118scope/23전체source/15명명 작품군·60,129edge와 동일6raw/2M/20초 cooperative guard로 fresh ordinary를 실행한다. 전체118 및 이전 모델과 공통 완료 subset, 기존26 baseline과의 비교를 모두 보고한다. 참조는 평가/Train loss용이지 inference의 선택 입력이 아니다. Dev 재학습/추론/평가·운영/UI 변경은 하지 않는다. 내부 로컬 비상업 연구 계약/원33package의 운영 학습 미승인을 유지한다.

사전 성공 판단은 단순 margin 감소가 아니라 전체 분모·동일 완료 범위의 근음+철자 구성음 시간, 경계, 작품군 macro와 기존 정답 보호다. 일부 사례 개선만으로 운영 승격하지 않는다. 이번 데이터는 Train이며 독립Test/전체 Roman·전위·국소 조성·NCT 정확도가 아니다.

## 2. 구현과 준비

- `harmony_context_refresh_trial.py`: 이전 source/pins/권한 확인, unique blind path mining, source/target/손실 재생, 기존7항 학습 호출, model freeze, exact scalar fresh118, JSON path identity 정규화 비교.
- `test_harmony_context_refresh_trial.py`: duplicate/abstention 재시도 금지, provenance·unknown gradient·zero-loss·old26 보존·reset·metadata·guard·집계 비교.
- `validate_harmony_context_refresh.py`: 이전838 inventory에 기존counter-v2 3검사와 이번 검사를 추가한다.
- `audit_harmony_context_refresh.py`: source/새 대조/학습 산술/승자 및 경쟁 경로 상세 비용/scalar/전체 지표를 재생한다. 새 decoder search/Dev/추가 model 저장은 하지 않는다.

코드/검사는 actual 전에 확정한다. 원 단계79~81 코드/자료/계수/산출물은 고치지 않고 새 파일/새 output만 사용한다. 신규9검사 PASS/0.338초. 읽기 전용 source preflight도 PASS: 3,343input SHA 확인, 이전254+새11=265대조다. 이전104선택 중93중복은 재가중하지 않고14보류는 mining에서 재시도하지 않았다. 새11중4zero-loss 보호/7known-gradient collision이 있으며, 새 오답 중에도 현재7특징으로 차이를 주지 못하는 것이 남는다. 각11새 대조의 전체 source/원 graph/원음표 상세 receipt·봉인 target·손실을 다시 검산했다. 이번은 매 방문 adversary를 찾는 online 학습이 아니다.

## 3. 실행 결과

Actual은 **681.342607초/exit0**, 원118범위/23전체 악장 source/15명명 작품군·60,129edge에서104exact 선택/14wall 보류다. 이전 모델과 공통 완료104이며 회복/신규 보류0이다. 경로 변경은1개, 이전 정답 소실0/새 정답1이다. 원152제외 parent범위와6raw/2M/20초 cooperative 계약을 보존했다.14계산 보류를 정답이나 부분 승자로 대체하지 않았다.

| 비교 조건/분모 | 전체 진행 일치 | 근음+철자 구성음 시간 | 작품군 macro | 경계F1 | 시간 coverage |
|---|---:|---:|---:|---:|---:|
| 기존26 / 원118 | 58/118 | 77.5572% | 77.5655% | 74.2358% | 100% |
| 이전7항 / 원118 | 55/118 | 58.3848% | 56.6621% | 61.3065% | 75.0042% |
| 갱신7항 / 원118 | 56/118 | 58.4849% | 56.7434% | 61.9289% | 75.0042% |
| 기존26 / 같은 완료104 | 53/104 | 78.2202% | 76.2965% | 73.3728% | 100% |
| 이전7항 / 같은 완료104 | 55/104 | 77.8420% | 76.1242% | 72.6190% | 100% |
| 갱신7항 / 같은 완료104 | 56/104 | 77.9755% | 76.2325% | 73.4940% | 100% |

이전7항 모델보다는 공통 완료104의 시간/macro/경계와 전체 일치가 소폭 개선됐다. 그러나 기존26에 비해 시간/macro는 여전히 낮고 전체118coverage도75%다. 따라서 **일부 개선/운영 미채택**이다. 기존26 대비 정답6소실은 실제 다른 선택1개(A7)와 자원 보류5개를 구별한다. 갱신계수를 미채택 상태로 저장하고 원 운영/화면 가중치는 바꾸지 않았다. 독립Test/전곡/fullRoman/전위/국소 조성/NCT 성능이 아니다.

학습은265대조/795방문/357업데이트·bound 무변경29회였고, 매 epoch positive-margin known feature collision66개가 남았다. 동일 새 pool에서 margin 합은0계수212.958920→새196.714029로 줄지만, **이전 모델196.636469보다 조금 나쁘다**. Margin은 정확도가 아니므로 이 차이를 숨기거나 epoch/계수/순서를 결과에 맞춰 고르지 않았다.43대조의 margin은0계수보다 악화했고, negative가 target보다 싼 대조는0계수99/이전91/새90개다.

### 개선과 미해결을 원음표에 연결

- [K280 F화음 유지 개선 packet](../../../output/harmony-context-refreshed-pool-2026-10-05-r1/cases/cont_7ac4f91c9a34b723f8cc.json.gz): `[344,1379/4)`의 이전 F-A-C→E-G-B♭→F-A-C 대신 F-A-C 유지가 선택됐다. **같은 새 계수 아래** 유지 비용0.3971265, 이전 경로 old26비용0.493306+새문맥-0.069514=0.423792다. 새로운 chord 후보/성부/원음표나7음 유지 관문을 넣은 결과가 아니다. 계수 갱신으로 원 후보의 우선순위가 바뀌었다.
- [K280 A7 소실 미해결 packet](../../../output/harmony-context-refreshed-pool-2026-10-05-r1/cases/cont_9a13eb950949fd01e0e7.json.gz): `[763/4,192)`의 A7 target 비용0.2587305보다 A-C♯-E→E-G-B의0.3450253667-0.17817375=0.1668516167이 여전히 싸다. 이전과 같은 raw 경로/참조 불일치다. 원 음표/음가·성부/상세 비용·이전 packet/전체XML·IR SHA와전후 source를 보존한다. 이7화음 소실을 해결했다고 하지 않는다.

두 사례는 동일 전체 K280 source와 연결된다. 모델의 human_validated는false이며, 원주석/관찰/조건부 음형 설명을 한 확정 label로 합치지 않는다. 이번 갱신에 쓰인11새 대조는 별도 `mined/` packet에 원 source/전후/두 receipt·손실·target provenance를 함께 저장했다.

## 4. 같은 선형 항의 충돌 — 원자료 대조

전체 재선택과 별도로265저장 대조를 읽기 전용으로 점검했다. 모든 차원이 known이고 두 항의 delta만 동일하게 비0인 대조18개가 있다. `u = weight(hold_remaining_nonmember_exposure) + weight(selected_new_exclusive_unassigned_exposure)`라고 두면 아래 두 대조에서는 나머지5항 delta가 정확히0이다. 두 비용 차이는 `negative_cost - target_cost = legacy_gap + delta*u`다. Target이 경쟁 경로보다 비싸지 않으려면 이 값이0이상이어야 한다.

| 원 Train 대조 | legacy gap | 두 항 각각의 delta | target 우선에 필요한 조건 |
|---|---:|---:|---|
| K280-1, `cont_9a13eb950949fd01e0e7`의 `epoch3_adversary` | 1294423/15000000 | +3/8 | u ≥ -1294423/5625000 (약 -0.230120) |
| Chopin BI105-2op30-2, `cont_9d29b21fdced352125a1`의 같은 arm | -2698067/45000000 | -1/10 | u ≤ -2698067/4500000 (약 -0.599570) |

두 부등식은 동시에 성립하지 않는다. Margin/학습 cap/계수 trust bounds를 빼고 **단순 두 저장 경로의 우선순위만** 보아도 그렇다. 이는 현재 old26고정+7선형항 계약 아래 두 특정 target/경쟁 경로를 함께 순위 교정할 수 없다는 제한적 증명이다. 모든 가능한 경로의 전역 오류율 하한이나 모든 작품의 분석 불가능성을 증명하는 것은 아니다. Target/negative는 원 Train loss 기반 생성이며 원주석이 유일한 인간 해석이라고 선언하지 않는다.

K280의 target은 `[763/4,192)` A-C♯-E-G 유지이며 경쟁 경로는 A-C♯-E→E-G-B다. Chopin `[98,101)`의 target은 B-D-F♯→F♯-A-C♯이고 경쟁 경로는 root F♯/members B-D-F♯를 한 구간에 유지한다. 단지7화음에 큰 보상을 주거나 외부음 보상을 일괄 제거해서 다른 상황도 해결된다고 할 수 없다. 근음/구성음의 대응·새 구성음의 실제 역할·지속과 성부 해결을 구별하는 표현, 그리고 고정 기존 점수와의 상호작용을 후속으로 점검해야 한다.

원 source/원 sound와 target/negative completed runs는 [K280 원 대조](../../../output/harmony-context-competition-2026-10-05-r3/cases/cont_9a13eb950949fd01e0e7.json.gz), [Chopin 원 대조](../../../output/harmony-context-competition-2026-10-05-r3/cases/cont_9d29b21fdced352125a1.json.gz)에 남아 있다. 전체 [K280 MusicXML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/53b63759291ef82365ab/source.musicxml) SHA `db3c7765e36c1c3eb6da4e69fd4910cb5c0158502d5f0e59f0339da90e3d2a9f`, [Chopin MusicXML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/5c080f16d704fc413e11/source.musicxml) SHA `6846ee87f5c7b3e32c24006ae4c6bc55150552499ee86fc5a01e7c11806ebe7d`다. 새 dataset의 두 row/availability/legacy gap/delta는 실행 후 전체 source 감사에서 재생한다. Read-only Fraction assert는 PASS다.

## 5. 검사·봉인·사후 감사·재현

[850검사 report](../../../output/harmony-context-refresh-validation-2026-10-05-r1.json)는78모듈 PASS/failure0/error0·91.788554초다. 이전838+기존counter-v2 3+신규9이며 repository 전체 suite나850곡/음악 정답이 아니다. Actual 전에 완료했다. 새4Python의 UTF-8/AST/공백과434actual code pins도 확인했다. Actual 시작 이후 code/test/script 수정0이다.

[사후 감사](../../../output/harmony-context-refreshed-pool-2026-10-05-r1/post-seal-audit.json) PASS/exit0: 3,480고유SHA/3,475봉인 input 재확인·265학습 대조/11새 source proof·고정 fit/평균 산술 재생·118원 source scope/23source/60,129edge·444독립 상세 경로 비용/403scalar-상세 전이 및 전체 지표 재생이다. 새 decoder search/Dev/추가 모델 저장0이며 원 자료/Core/운영 계수/이전 산출물 변경0이다. 집계 path IDs는 tuple/list 정규화 후 비교해 이전 오류를 반복하지 않았다.

- [Actual report](../../../output/harmony-context-refreshed-pool-2026-10-05-r1/report.json): `ffb9b6bd49a97af745b769f00664dbeac5bd107c902ccf263bd442944d088c67`.
- [Run contract](../../../output/harmony-context-refreshed-pool-2026-10-05-r1/run-contract.json): `1281ee60fe398547851f62bc689adeb571c411cc534a867fb27eae9d5d806d94`.
- [Model](../../../output/harmony-context-refreshed-pool-2026-10-05-r1/model.json.gz): `2b36a64aa933a228d3d71396b3be899be2336afc39e1c217dd4e63ef6fc447dd`.
- [Model freeze](../../../output/harmony-context-refreshed-pool-2026-10-05-r1/model-freeze.json): `165841058ca3ba9871e6e516ab80b57e6104d6db5ade3c5aebcaf09e4bdd35a7`.
- [Training vectors](../../../output/harmony-context-refreshed-pool-2026-10-05-r1/training-vectors.json.gz): `c179514e151b3469895ce4bdabcec190e4a602f1f57438bb5c54d7eb9b623217`.
- Validation SHA `e5eedf19f55903bc532ba52911b0082253595847ab9b83618d50e56cd0c361f6`,audit SHA `8491823e2ce2ac012b6cbad5931a7c6a8b0b095ec66317ed8d4d926e05ef9ce7`,audit code SHA `b3400abbb41c5e222cb54d798d16e2a2ab357e9aecbbaae0ea2e1dc252153da8`.

신규 코드/회귀/actual/감사의 실패·중단0이다. 별도 읽기 전용 IR 조회에서 span을 nested coordinate로, staff를 `staff_id`로 가정해 KeyError2회가 있었고, 실제 rational span/`display_staff_id` 계약을 확인했다. 이를 원 IR/음악 규칙 변경으로 처리하지 않았다. 문서 patch의 잘못된 중복 context1회는 파일 변경0으로 실패 뒤 교정했고 초안의 다른 언어 잔여도 한국어로 복구했다. 최종 큰 stdout 잘림은 저장 report의 compact 조회로 보완했다. 이러한 엔지니어링 조회 오류를 음악적 성공/보류 집계에 넣지 않는다.

새 output을 사용하며 기존 output을 덮어쓰지 않는다. 아래는 `K:/Music Analysis`에서 실행한다.

```powershell
$env:PYTHONPATH='src;tests'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_context_refresh.py --prior-validation output/harmony-context-scalar-validation-2026-10-05-r1.json --output output/<new-validation>.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_context_refresh_trial --output output/<new-trial>
.\.venv\Scripts\python.exe -B scripts/audit_harmony_context_refresh.py --root output/<new-trial>
```

## 6. 다음 판정

이 통제된 갱신으로 A7 소실이 남았고 단순 선형 순위 충돌도 확인했다. 따라서 다음은 반복 pool 갱신/같은7항 weight sweep이 아니라 **source-bound 구성음 지지·근음과 구성음의 대응·장식 설명의 상호작용 표현**을 보완한다. 기존26고정 조건에서 생긴 한계와 새 특징의 부족을 구별하고, 유지/실제 교체/분산형·결측/경계 잘림을 함께 대조한다. 정답에 맞춘 임의 음 삭제나 특정 작품 예외를 만들지 않는다. 남은14자원 보류는 별도 backlog로 유지한다.
