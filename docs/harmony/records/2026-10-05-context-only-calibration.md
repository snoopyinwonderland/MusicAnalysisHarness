# 단계80 — 문맥7항 제한 학습과 큰 원 후보망의 재선택

## 1. 목적과 범위

단계79가 구현한 지연 공동 선택기에 실제로 학습한 계수를 넣는다. 기존26항의 단계75 계수는 모두 고정하고 새7항만 학습한다. 저장 대조의 margin 감소, 전체 후보망의 새 일반 선택, 참조와의 음악적 일치, 운영 승격을 구별한다.

원 승인 Train118범위/23전체 악장 source/15명명 작품군·원60,129edge를 유지한다. 원270Train 중152제외 범위를 새로 승인하거나 후보를 추가하지 않는다. 앞뒤 원음표, Fraction 시간, 철자, sound/note IDs, source-clock·성부·grace 관문, 최대6raw segment를 보존한다. 특정 작품/마디를 조건식에 넣지 않는다.

## 2. 학습 계약

학습 전에 다음을 코드와 실행 계약으로 고정했다.

| 항목 | 사전 설정 |
|---|---|
| 초기 계수 | 새7항 모두0, 기존26항 고정 |
| 반복 | 3epoch, 같은 봉인 대조 pool |
| 업데이트 | capped passive-aggressive, 최대1/20 |
| 신뢰 범위 | 새 각 계수 [-1/2, 1/2] |
| 수치 | Fraction 계산, 1,000,000분모 grid quantization |
| 순서 | 작품군·sample·contrast ID 순 |
| 최종 모델 | no-update를 포함한 모든 post-visit 계수 평균 |
| 모델 선택 | Dev에 맞춰 epoch·계수·threshold 선택하지 않음 |

단계79의 initial/단계72 ordinary/단계75 ordinary/저장 epoch3 adversary를 negative로, 저장 epoch3 reference-compatible target을 대조 기준으로 사용했다. 동일 scope의 같은 negative path는 한 번만 센다. 원2adversary 보류를 재탐색하거나 성공 대조로 바꾸지 않는다. Negative의 과거 선택이 Train label을 사용했는지도 별도 필드로 보존한다. Target은 학습용이며 분석 예측이 아니다.

이는 **봉인 fixed-pool calibration**이다. 이번 계수에서 매 방문 새 adversary/latent target을 찾는 online 학습은 아니며, 모든 가능한 오답 경로를 보호하지 못한다. 이전 정답 범위도 포함하고 zero-loss 대조를 버리지 않지만 전체 후보망의 근접 오답이 모두 pool 안에 있다는 뜻은 아니다.

경로 비용은 `기존26항 비용 + 새7항의 알려진 지역 항 누적 비용`이다. 대조의 부족 margin은 `loss - (negative 비용 - target 비용)`이며 비용을 낮추는 것이 선택 목표다. 업데이트는 양쪽 **전체 경로에서 known인 차원**에만 적용한다. 일부 지역이 unavailable인 차원은 gradient를 null로 남긴다. 알려진 지역에서만 계산한 부분 비용과, unknown 지역의 부분 관측은 구별한다. Unknown을 관찰 사실0으로 만들거나 확정 NCT로 승격하지 않는다.

권리 검사는 기존의 직접 사용자 확인·Train split·manifest entry SHA·라이선스/출처·로컬 비상업 연구 계약을 그대로 사용한다. 원 manifest의 운영 학습 미승인/자동 학습 false를 바꾸지 않는다. 상업/운영/API 전송/가중치 재배포 권한을 새로 부여하지 않는다.

## 3. Fresh 선택과 계산 한도

학습 모델/기존26계수/SHA를 먼저 고정한 다음 모든118원 scope에서 새로운 일반 공동 선택을 시도한다. 추론 함수에는 reference target이나 정답 loss를 넘기지 않는다. 참조와의 평가, 기존 경로/저장 target의 새 비용 대조는 선택 이후에 구성한다.

원 지연 exact decoder의2M feasible-state/raw-edge 비교 한도와6raw cap을 유지한다. 여기에 **scope당20초 cooperative wall guard**를 별도로 추가한다. Source run/문맥 계산 호출 전후에 clock을 검사하며, 하나의 분할 불가능한 호출에서는 조금 초과할 수 있다. Instance-local hook만 잠시 사용하고 정상/보류/예외 모두 복원한다. 봉인 코드/모듈 global 변경, beam, 후보 삭제는 없다.

Wall 한도에 닿으면 selected=null/exact=false로 남긴다. 부분 승자나 이전 엔진 결과를 새 모델의 성공 결과로 대신 반환하지 않는다. 중단 당시 raw operation count는 unknown으로 남긴다. 2M 숫자가 기존 batched decoder와 같은 계산량을 뜻하지 않는다는 단계79의 주의도 유지한다.

모든118범위의 정확도에는 새 계산 보류도 포함한다. 완료 선택이 된 범위만 양쪽을 짝지은 비교도 제공하되 **계산이 쉬운 범위로 편향된 보조 지표**로 표시한다. 새 실패를 분모에서 빼서 정확도가 오른 것처럼 보고하지 않는다. 계산 한도가 추가된 실험이므로 이전 무wall 결과와 속도/정확도를 단순히 같은 운영 조건으로 비교하지 않는다.

## 4. 구현과 검증

- `src/musicanote_harness/harmony_context_score_learning.py`: source-bound 연구 계약, old26 고정·새7 masked gradient·fixed pool/평균·model binding.
- `src/musicanote_harness/harmony_context_score_trial.py`: 봉인 원자료/pool 검사→학습→model freeze→118 fresh 시도→사후 평가와 source receipts.
- `tests/test_harmony_context_score_learning.py`: 결정론·기존 계수 보존·unknown/partial·zero-loss·signed bounds·권리/Dev/변조/출처 계약8검사.
- `tests/test_harmony_context_score_trial.py`: tiny DAG 전수 최소 일치·clock 보류/원 operation 보류·instance hook 복원·pool dedup/출처4검사.
- `scripts/validate_harmony_context_score.py`: 기존811 inventory+신규12검사.
- `scripts/audit_harmony_context_score.py`: source/원 graph/벡터·고정 평균 학습 산술·선택 비용·보류·전체/paired 지표 재생. 새 탐색/Dev/추가 모델 저장은 하지 않는다.

신규12검사 PASS/0.771초. 전체 관련 **823검사/74모듈 PASS**, failure/error0·88.969183초. Repository 전체 suite나 음악 정답823건은 아니다. Actual과 전체 regression 검사는 준비 단계부터 겹쳐 실행됐으므로 wall 시간은 전용/동일 부하의 speed benchmark가 아니다. Actual 시작 후 code/test/script를 수정하지 않는다.

## 5. 학습 결과 — 정확도와 구별

472negative 조건에서 duplicate path216개를 제외하고 원 resource 보류2개를 보존해 **254대조/118scope**를 학습했다. 이 중 zero-loss63개·known gradient collision126개다. 전체3epoch·762post-visit 평균에서340계수 업데이트, bound로 변경하지 못한 방문33개를 기록했다. Epoch마다 collision63개가 계속 남았다.

Positive margin 합은206.634371→189.763889로 줄었으나38대조는 악화했다. 이 수치만으로 화성 분석의 정확도가 향상됐다고 말하지 않는다. 새7항으로 구별할 정보가 없는 대조, unknown domain, pool 밖 오답은 남아 있다.

| 새 특징 | 고정 평균 계수 |
|---|---:|
| hold_explained_step_exposure | +0.106398 |
| hold_remaining_nonmember_exposure | -0.261219 |
| reclassified_ornament_member_exposure | +0.095754 |
| selected_new_exclusive_unassigned_exposure | -0.246107 |
| continuing_left_member_exposure | +0.434564 |
| continuing_left_lowest_coverage | +0.448075 |
| dominant_credit_with_hold_conflict | +0.330104 |

이 계수는 Train 대조에서 배운 비용 상호작용이다. 각 항을 독립 음악 법칙/확률/화음 삭제 관문으로 해석하지 않는다. 기존26항 모델 SHA는 `2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf`로 유지한다.

## 6. Fresh 결과와 사후 감사

Actual은 **1,039.879255초/exit0**로 완료했다. 원118scope/23전체 source/15작품군·60,129edge에서90개를 끝까지 exact 선택하고28개는20초 wall guard로 보류했다. 원2M raw 비교 한도 보류는0이다. 원152제외 parent scope는 보존했다. 전체 코드/이번 시험·스크립트432개 pins 및122산출물 pins가 actual 전후 동일하다. 이번 신규 Python 파일은6개다.

| 비교 | 범위 | 전체 일치 | 근음+철자 구성음 시간 | 작품군 macro | 경계F1 |
|---|---:|---:|---:|---:|---:|
| 기존 단계75, 전체 | 118 | 58/118 | 77.5572% | 77.5655% | 74.2358% |
| 새 모델, 보류 포함 전체 | 118 | 47/118 | 48.1061% | 45.1002% | 50.0000% |
| 기존, 새 계산이 완료된 paired 범위 | 90 | 46/90 | 77.6326% | 76.4116% | 70.2290% |
| 새 모델, 같은 paired 범위 | 90 | 47/90 | 76.8595% | 76.1441% | 69.2308% |

전체 분모의 예측 시간 coverage는100%→62.5897%다. 새3개가 완전 일치했지만 기존 정답14개를 소실했다. 이14개는 **다른 화음으로 선택한2개와 계산 보류12개**를 구별한다. 선택이 완료된90개만 보면 전체 정답은46→47로1개 증가했으나 시간/macro/경계는 모두 소폭 퇴행했다. 따라서 **계산 효율만의 문제가 아니며, 이번 계수는 미채택**이다. 쉬운 subset이나 margin 감소를 근거로 정확도 향상을 주장하지 않는다.

완료 선택11경로가 바뀌었고 그중 참조 일치 시간은4개 개선/4개 퇴행/3개 동일이다. 범위가 짧고 서로 겹칠 수 있어11개의 다른 작품/유일 악곡 시간으로 세지 않는다. 원15작품군은 베토벤 현악4중주 op18-1/소나타01·02·03, 모차르트 K280·K281, 쇼팽 마주르카7작품군, 코렐리 op01n02·n03다. 이번 승인 코호트에 교향곡/팝/다른 전곡을 새로 넣거나 일반화 성능을 측정하지 않았다.

**평가 범위:** Train 자료의 절대 근음+철자 구성음·의미 경계 일치다. 전위/국소 조성/전체 Roman/NCT/종지 정확도나 독립Test 성능이 아니다. 새 계수에 맞는 운영 threshold를 Dev에서 고르지 않았으며 이번에는 Dev 추론/평가를 하지 않았다. 미채택 결정을 먼저 기록하고 계산·표현·학습 대조를 보완한다.

### 원음표와 비용을 연결한 개선 사례

`cont_3244c06fe647a34779cc`는 베토벤 현악4중주 op18-1 1악장 전체 source의 quarter `[2479/4,621)` 범위다. 기존 선택은 B♭-D♭-F→D♭-F-A→B♭-D♭-F로 바뀌었지만, 새 선택은 의미상 B♭-D♭-F를 유지한다. Raw 두 조각이 같은 signature이면 한 harmonic run인 것도 보존했다. 참조의 근음+철자 구성음/경계와 일치했으며 full Roman이나 NCT 정답을 검증한 사례는 아니다.

원 두 명시 성부에서 중간 A가 양쪽 anchor로 회귀하는 `neighbor_like` 대안이 있다. A의 원 sound IDs는 `sound_edd88e596eeb`, `sound_9a32a1f858ef`이고 note IDs는 `note_5b520bf94a8d`, `note_f53a2cf198f9`다. 실제 지속 F/D♭(`sound_0389b3c15943`, `sound_59f6e5b3221d`)는 `[618,621)`에서 살아 있다. 새 근거는 이를 앞 화음 유지와 중간음의 조건부 장식 설명으로 비교한다. A를 원 IR에서 지우거나 보조음 확정 label을 Core에 넣지 않는다.

같은 새 모델에서 기존 경로 비용은 old26의0.169245+new7의0.4712508=0.6404958, 새 경로는 old26의0.2214026+new7의0=0.2214026다. 원26항만 보면 중간 화음 교체가 더 쌌지만, 문맥 비용을 함께 적용하니 유지 경로가 선택됐다. 단지 원 target을 반환하거나 해당 작품의 화음명을 조건식에 넣은 것이 아니다. 같은 새 계수 아래 두 경로의 비용을 대조했다.

전체 source XML/부모·working IR SHA/원 graph/성부와 앞뒤 anchor spans/두 선택의 costs·availability·source receipts는 [사례 packet](../../../output/harmony-context-score-learning-2026-10-05-r1/cases/cont_3244c06fe647a34779cc.json.gz)에 연결했다. 원 XML은 `output/source-locator-revision-trial-2026-09-30-r2/sources/1ba2f63511fc8a4457a0/source.musicxml`, SHA `221f4e5ffdfc47aeedb2e017e992318f29c5a3b85cde620cb8ab7af9e9b29894`다. 사람의 새 승인false이며 한 로컬 범위의 개선을 전곡/독립 정확도로 확대하지 않는다.

### 참조와 어긋난 원음표 반례도 보존

- 모차르트 K280-1 `[344,1379/4)`, `cont_7ac4f91c9a34b723f8cc`: 참조와 맞던 F-A-C 유지가 F-A-C→E-G-B♭→F-A-C로 과분할된다. 새 경로 old26 비용0.493306은 기존0.3971265보다 나쁘지만 새 문맥 비용-0.1017246667이 붙어0.3915813333으로 더 싸진다. `hold_remaining_nonmember_exposure`와 `selected_new_exclusive_unassigned_exposure`의 음수 비용이 설명된 장식 비용을 넘은 실제 선택 원인이다. [두 비용/원 IDs/전체 source 연결](../../../output/harmony-context-score-learning-2026-10-05-r1/cases/cont_7ac4f91c9a34b723f8cc.json.gz).
- 같은 작품 `[763/4,192)`, `cont_9a13eb950949fd01e0e7`: 참조와 맞던 A-C♯-E-G의 A7 유지가 A-C♯-E→E-G-B로 바뀐다. 기존 비용0.2587305, 새 old26 비용0.3450253667+문맥-0.19024725=0.1547781167이다. 비구성음/새 구성음 대안에 대한 보상이 genuine7화음 유지보다 크게 작용해 참조 일치 시간5/4quarter를 잃었다. [7화음 소실 반례](../../../output/harmony-context-score-learning-2026-10-05-r1/cases/cont_9a13eb950949fd01e0e7.json.gz).

대안들의 음악적 해석이 사람에게 재승인된 것은 아니다. 여기서 말하는 퇴행은 기존 DCML 참조 계약과의 불일치이며 주석이 모든 해석을 배제하는 절대 정답이라는 뜻은 아니다. 현재 판단의 비용 원인을 보존하되 특정 K280 조건식/7화음 강제/원음 삭제로 고치지 않는다. **남는 외부음이나 새 구성음이 있다는 사실만으로 새로운 화음이라고 판정하지 않도록**, 유지·NCT 설명/전후 해결·동일 원음의 중복 근거·scope 밖 anchor 미해결 여부와 함께 대조할 필요가 있다. 이는 다음 일반 설계 검토 항목이지 이번 실행에서 입증한 원인별 ablation 결과는 아니다.

### 봉인과 실행 과정

- [완료 report](../../../output/harmony-context-score-learning-2026-10-05-r1/report.json): `abdcd93b7e1d75bedfb68dbf9e24e71a09793ae7411a3afb95cb86cb33b8e119`.
- [사전 실행 계약](../../../output/harmony-context-score-learning-2026-10-05-r1/run-contract.json): `86cb6902189d746a381bfe92ac9ed6ce9223007ff21a49bae354258de4efae0d`.
- [고정 연구 모델](../../../output/harmony-context-score-learning-2026-10-05-r1/model.json.gz): `f27db2416de803d3245c960e827f3786f8b3947bc1fa538fc15c9d90f17096f4`. 운영 모델로 배포하지 않는다.
- [model freeze](../../../output/harmony-context-score-learning-2026-10-05-r1/model-freeze.json): `e0284db6ad806b16508e01c21c26f378325628c43da3dd4ea4e19f8003e56c3d`.
- [823검사 report](../../../output/harmony-context-score-validation-2026-10-05-r1.json): `e153617db6500dda2e095822fed7aebd1ee12f58a1161455f875b3d4f50b0c56`.
- [사후 감사](../../../output/harmony-context-score-learning-2026-10-05-r1/post-seal-audit.json) **PASS/exit0**:3,211고유SHA/3,204봉인 input·254벡터/고정 평균 모델 산술·원118scope/23source/60,129edge·326독립 경로 비용(90fresh+236baseline/target)·전체/paired 지표를 재생했다. SHA `d2efea5f69ae4fa5ef18443ae207ef468d7f944076bda7d94b3ff795b91e5c69`,audit code `e4ea454bc8055d3523cce328bccc4ff33eaeddbd34fcf03687911b286579a725`다. 새로운 decoder 탐색/Dev/추가 모델 저장0이며 감사의 학습 산술 재생은 새 실험 조건을 고르거나 가중치를 변경한 재학습이 아니다. 원 Core/운영 가중치가 변하지 않았고 단계79 완료 report/감사 SHA도 동일하다.

합성 검사/actual 실패·중단0이다. 실행 뒤 임시 비용 조회 command1회는 Python 코드에 literal `\n`을 넘겨 SyntaxError가 났고, list comprehension의 읽기 전용 조회로 교정했다. 문서 patch의 잘못된 context1회는 검증 실패/파일 변경0 후 실제 문장으로 교정했다. 요약 조회/CLI 최종 큰 출력의 잘림은 compact 조회로 확인했고, 초안의 다른 언어 잔여 표현은 한국어로 고쳤다. 봉인 코드/원자료/실험 조건/산출물을 바꾼 실패가 아니다.

## 7. 재현과 다음 결정

기존 output을 덮어쓰지 않고 존재하지 않는 새 경로를 사용한다. 아래 명령은 `K:/Music Analysis`에서 실행한다.

```powershell
$env:PYTHONPATH='src;tests'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_context_score.py --prior-validation output/harmony-context-joint-validation-2026-10-05-r1.json --output output/<new-validation>.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_context_score_trial --output output/<new-trial>
.\.venv\Scripts\python.exe -B scripts/audit_harmony_context_score.py --root output/<new-trial>
```

다음 큰 작업은 **exact 의미와 후보망을 보존하는 계산 효율 개선**이다. 이번28보류가 있으므로 raw budget/시간을 무작정 늘리거나 기존 결과를 fallback 정답처럼 반환하지 않는다. 동일 가중치·tiny DAG 전수/동점·unknown·분할/마지막 flush를 검증하고118원 scope에서 비용/보류를 재비교한다. 그 다음 genuine7화음 유지/외부음 설명의 반례와 fixed-pool 밖 새 오답을 Train에서 비교해 표현·학습을 보완한다. 현재 미채택 계수에 맞춘 Dev tuning이나 음악별 예외는 없다.

Fresh 전체/계산 보류/기존 정답 보호를 다시 확인한 모델만 고정 Dev 비교로 넘긴다. 선택된 작은 subset이나 margin만 보고 승격하지 않는다. 이후 고정 Dev 평가도 노출된 개발 자료의 퇴행 확인이며 독립 Test가 아니다.

독립 Test/공개 모델 공통 비교, 전체 Roman/국소 조성/전위/전체NCT·종지와 편곡·작곡 평가는 남아 있다. UI/서버/구조 분석/Claude Phrase·Motif/MusicSearch/Composition/Core/원주석/별개 dirty/Git를 보존하고 API/merge/commit/push/운영 적용0이다. 개발 기록은 화성 메인/로그와 이 문서에 관리하며 인수인계 문서에 누적하지 않는다.
