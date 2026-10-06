# 단계74 — 완전 화음 진행의 학습용 경쟁 탐색

## 1. 목적과 이번 범위

[단계72](2026-10-05-online-score-refresh.md)는 방문 시점의 일반 승자만 대조했다. 현재 정답인 구간은 loss0으로 업데이트하지 않으므로, 다른 구간의 학습과 계수 평균 이후 가까운 오답이 이길 위험을 보호하지 못했다. [단계73](2026-10-05-online-score-dev-check.md)의 Dev 결과도 시간·경계 개선과 작품군 평균 퇴행이 함께 나타났다.

이번에는 **단계72의 이미 고정된 계수를 바꾸지 않고**, 참조 경로가 존재하는 Train118구간 모두에서 학습용 경쟁 경로를 찾는다. 기존 오답뿐 아니라 현재 정답도 포함한다. 목적은 새 대조가 실제로 생성되고 손실/점수가 정확한지 확인하는 것이다. **재학습·정확도 개선·새 Dev 평가·운영 승격 단계는 아니다.** 다음 학습에서 매 방문 경쟁 경로를 새로 찾을 수 있도록 독립 모듈을 만든다. 이 고정 대조 목록만 반복 학습하는 것으로 끝내지 않는다.

## 2. 일반 규칙과 수식

음표/시간·철자·근음 가설·원 후보망은 그대로 둔다. 이름과 경계를 공동 선택한 완전한 진행 `y`의 기존26특징 비용을 `C(w,y)`라 할 때, 학습용 경쟁 경로는 다음을 최소화한다.

`argmin_y [C(w,y) - L(y, reference)]`

`L = 잘못된 근음+철자 구성음의 시간 / 문맥 시간 + (1/4) × (추가 경계 + 빠진 경계) / max(1, 참조 의미 경계 수)`

이 손실은 전체 Roman·전위·국소 조성·NCT 정답률이 아니다. 같은 철자 signature가 이어지는 raw 조각은 의미 경계를 만들지 않는다. 참조 경계가 있는데 같은 signature로 계속 가면 빠진 경계 비용을 반드시 센다. 한 raw edge 내부의 참조 경계와 edge onset의 경계를 따로 계산하여 이중 계산을 피한다.

정답과 호환되는 원 후보 경로 중 같은 계수로 가장 낮은 비용인 `target`도 따로 선택한다. 후보에 없는 정답을 삽입하지 않는다. 비교의 margin은 `L(adversary) - [C(adversary)-C(target)]`다. Margin이 양수이고 두 경로 모두 관측 가능한 학습 차원의 차이가 있을 때 다음 학습의 gradient 대조가 된다. 관측 불가능한 특징은 추정0으로 채우지 않는다. Positive margin과 known-feature collision을 구별한다.

‘가까운 오답을 보호한다’는 개발 목적이지만 이 알고리즘은 비용이 가장 가까운 오답만 고르는 방식은 아니다. 비용이 더 높은 오답도 참조 손실이 충분히 크면 adversary가 된다. Margin/loss는 확률이나 실제 오답 발생 빈도가 아니다. Adversary의 오답 수를 ordinary 정확도 저하로 집계하지 않는다. 손실 비중을 Dev 결과에 맞춰 이번에 조정하지 않았다.

## 3. 탐색과 안전 계약

- 상태: 끝 시각, 사용한 raw edge 수, 현재 같은-signature run의 시작 시각, 현재 철자 signature.
- 같은 화음이 계속되면 기존 run 비용을 빼고 확장된 전체 run 비용을 다시 넣는다. Raw edge마다 별개의 화음 비용을 더하지 않는다.
- 교체할 때만 기존 전이/기능적 해결 근거를 센다. 학습용 경계 손실은 **같은 signature로 이어지는 onset에도** 계산한다.
- 양의 시간 DAG·동점의 ID 사전식 순서·기존 score-identical edge 병합과 같은 미래 상태의 Pareto 제거만 사용한다. Beam/정답 top-N/경험적 pruning은 없다.
- 시간과 점수는 정확 유리수다. 기존 박자 변경에 필요한 정수 배율을 보존하고 손실 분모만 추가한다.
- 승자 비용은 원 full-score 특징 및 원 `path_loss`로 독립 재계산한다. 원 functional decoder를 승자 chain에만 적용해 전체 source-linked packet을 복원한다.
- Raw cap6은 유지한다. 새 탐색 예산2,000,000의 단위는 `feasible_state_raw_edge_comparison`이다. **기존 일반 batched decoder의 factor operation 단위와 다르므로 같은 숫자를 동일 작업량/지연으로 해석하지 않는다.** 한도 도달 시 부분 승자를 반환하지 않는다.
- 일반 추론 API `Scorer.decode`에는 reference/loss 인자를 추가하지 않는다. Adversary와 target에는 `source_labels_used_for_selection=true`, `training_reference_labels_used=true`, `target_only=true`를 붙인다. Native analysis export가 거부한다.
- 원 NC 로컬 연구/출처 승인 계약을 검증한다. 상업적 운영·외부 API·자료 재배포의 승인은 추가되지 않는다.

## 4. 구현·실행 파일

- [26특징 run-aware 경쟁 탐색](../../../src/musicanote_harness/harmony_full_score_adversary.py)
- [고정 모델 Train 전체 대조 실행기](../../../src/musicanote_harness/harmony_full_score_adversary_trial.py)
- [탐색 검사](../../../tests/test_harmony_full_score_adversary.py), [대조/격리 검사](../../../tests/test_harmony_full_score_adversary_trial.py)
- [회귀 실행기](../../../scripts/validate_harmony_full_score_adversary.py), [사후 감사](../../../scripts/audit_harmony_full_score_adversary.py)

기존 단계72/73 및 sealed decoder는 수정하지 않았다. 새 개발 문서를 기존 인수인계 문서에 누적하지 않는다.

## 5. 검사·실패와 교정

신규13검사 통과. 무작위14 작은 DAG에서 여러 full-score 계수/원 raw cap 조건으로 가능한 모든 완전 경로를 열거해 `(cost-loss, ID 경로)`의 최소와 일치했다. 일반 승자가 정답이어도 양의 손실 경쟁 경로가 나오는 사례, 같은-signature 분할 불변, 경계 누락, 기능적 pair 근거, alias 동점/손실 일치, unsupported nullable 특징, 변경 박자·coarse grid, 보류 및 참조 export 차단을 검사했다.

초기 신규9검사 중8error는 승자 packet 복원에 일반 **batched** decoder를 쓰면서 `len(winner)`만 예산으로 준 오류였다. Batched 예산은 raw edge 수와 다른 연산 단위여서 chain도 보류했다. 원 functional reconstruction 함수에 승자 chain을 주는 것으로 새 모듈에서 교정했다. 기존 검사/원 점수/관문을 완화하거나 운영 decoder를 변경하지 않았다. 재실행13검사 모두 통과했다.

기존708+신규13=**721검사/61모듈 PASS**, failure/error0,73.8309053초. Repository 전체 suite는 아니다. 신규6Python 파일 strict UTF-8/AST 통과. [회귀 영수증](../../../output/harmony-full-score-adversary-validation-2026-10-05-r1.json) SHA `f695e26f6d0859e08b02f0319084579b0376bee2d6be79b562e08f5c04a5941c`.

## 6. 실제 실행 결과

Actual r1은 **374.9106002초/exit0**로 완료했다. 실행 시작 이후 code/test/script 변경0이다. [완료 report](../../../output/harmony-full-score-adversary-2026-10-05-r1/report.json) SHA `c924e50e3b6c1b663766bd0412acd7ba3885f6cc374645af5975c85892d3d71d`, [고정 실행 계약](../../../output/harmony-full-score-adversary-2026-10-05-r1/run-contract.json) SHA `74456bd5a995c357f332b6432d9ba53d6c3ed4afc5c4c19408e40144d297b8ec`. 고정 모델 SHA `029e2de31ab6e5d9e5fa65eb229c63fe649cce10ddd987dbab4c2b7f3f06f331`는 단계72와 동일하다.

| 항목 | 실제 결과 |
|---|---:|
| 원 Train / 이번 reachable 범위 | 270 / 118 |
| 나머지 제외 범위 — 삭제/신규 재평가하지 않음 | 152 |
| 전체 악장 source package / 명명 작품군 | 23 / 15 |
| 원 edge 수 — 변형/정답 삽입 없음 | 60,129 |
| 일반 선택 / 일반 전체 정답 | 118 / 60 |
| 완전한 adversary·target 대조 / 새 탐색 보류 | 116 / 2 |
| Positive margin / known 학습 gradient 가능 | 116 / 116 |
| 현재 일반 정답이면서 positive margin | 60 |
| 기존 일반 승자와 다른 경쟁 경로 | 110 |
| Positive margin인데 known 차원의 차이가 없는 충돌 | 0 |
| 바뀐 계수 / fit·Dev 신규 평가 | 0 / 0 |

일반118경로의 원 ID·비용이 단계72 post-fit 선택과 정확히 일치한다. 일반 지표도 단계72와 동일하게 전체60/118, 근음+철자 구성음 시간77.6573%·작품군 macro77.8664%, 근음 시간82.7966%, 경계F173.2143%다. **같은 모델/Train 내 재현이며 새 정확도 향상이나 독립 평가가 아니다.** 참조 범위는 겹칠 수 있으므로 총249.7083quarter를 유일한 악곡 분량으로 읽지 않는다.

116대조에 gradient가 있다고 해서26특징이 모두 관측된 것은 아니다. Conditional ornament 차원은45대조, 미관측3음/변화5음/7음 및 late-member 차원은 각각75대조에서 양쪽 availability가 성립하지 않아 다음 학습 gradient에서 제외해야 한다. Unsupported adversary를 음악적 정답으로 승격하지 않는다. 이번 손실을 실제 오답 발생 확률로 해석하지 않는다.

### 계산 한도와 지연

새 adversary 보류2개는 Beethoven Sonata02-2 `[3,8)` (`cont_e92872bb2c18325ddcfa`)와 Mozart K281-2 `[545/6,94)` (`cont_06279642b89b17cd3fe0`)다. 둘 다 일반 선택은 완전하지만 참조 전체와 일치하지 않았다. 각각 정확히2,000,000비교에서 adversary만 보류하고 부분 대조를 반환하지 않았다. 금지된 후보 제거/한도 상승/보류를 정답으로 계산하는 처리는 없다. 완료된 adversary의 최대 비교 수는647,608이다.

구간별 준비·일반/target/adversary 선택·receipt 저장을 합한 단일 실행 지연은 최소0.348초, 중앙값1.264초, nearest-rank p9510.091초, 최대54.498초다. 보류 두 구간은54.498/50.463초다. Adversary만의 순수 시간이나 여러 실행의 성능 보장은 아니다. 기존 batched operation과 단위가 달라2M 숫자만으로 지연을 비교하지 않는다. 다음 fit에서도 보류는 no-update로 남기고, 필요하면 동일 목적함수의 exact batching을 별도로 검증한다.

### 실제 대조 사례

**정답인 범위에도 학습 대조가 생기는 사례 — Beethoven Quartet01-4**

[원음표·전체 source 연결/세 경로 packet](../../../output/harmony-full-score-adversary-2026-10-05-r1/scopes/cont_00fe53c74ace3533c190.json.gz), `[265,533/2)`.

일반/target은 D♭–F–A♭의 한 run으로 참조와 일치한다. 일반 비용은 `56959/600000 ≈ .0949317`다. 경쟁 경로는 F–A♭–C → D♭–F–A♭–C → F–A♭–C, 세 run이며 비용 `2808493/3000000 ≈ .9361643`이다. 전체 시간이 불일치하고 거짓 경계2개라 손실3/2, margin `988151/1500000 ≈ .6587673`이다. 실제 분석이 이 오답을 골랐다는 뜻이 아니다. 기존 일반 승자 대조만 쓰면 loss0으로 빠졌던 범위에서도 margin 학습을 할 수 있음을 보여준다. 이 사례의 오답은 단순 비용 차이로 ‘아주 가까운’ 후보는 아니며 손실 가중 결과임을 함께 기록한다.

**기존 평균 모델 퇴행의 재확인 — Chopin Mazurka op30-4**

[원음표·특징 차이/세 경로 packet](../../../output/harmony-full-score-adversary-2026-10-05-r1/scopes/cont_635ba41c28793857d7b4.json.gz), `[6,35/4)`.

일반 결과는 D♯–F♯–A–C♯의 한 run이고 비용 `1403233/5500000 ≈ .2551333`, 손실19/44다. Target은 같은 감7음 집합 → G♯–B♯–D♯–F♯ → 앞 감7음 집합으로 돌아오는 세 run이고 비용 `6583331/22000000 ≈ .2992423`다. 경쟁 경로는 C♯를 뺀 D♯–F♯–A의 한 run이며 비용 `4955371/11000000 ≈ .4504883`, 손실5/4, margin `24172589/22000000 ≈ 1.0987540`다. 일반·target·adversary의 비용은 모두 **같은 고정 계수**에서 계산했다. 이전 세 ordinary 학습 방문에서 맞았지만 평균 후 가운데 G♯7이 사라진 단계72의 문제는 해결되지 않았으며, 이번에는 새 대조로 드러낸 것이다. 손실 탐색이 이 작품을 위한 화음 강제 조건을 추가한 것이 아니다.

### 사후 감사

[사후 감사](../../../output/harmony-full-score-adversary-2026-10-05-r1/post-seal-audit.json) PASS/exit0다. **2,212고유SHA·118Train범위/23전체 source/원60,129edge·116대조/손실/마진·352독립 경로 비용/원음표 source receipts·일반 Train지표**를 재계산했다. 감사 SHA `d9f8acb584d37092fd5e578a1a228ec563078d486a6e51972e0aa009abb5b971`, 감사 코드 SHA `2a0f18ac1edc8f49a6a2948d345c86ae0ea84c1381b343d372c2f3307c7477ff`다. 감사에서 새로운 decoder 탐색이나 fit은 하지 않는다. 작은 DAG의 전수 경로 검증과 실제 source 무결성 재생은 서로 다른 보증이다. Actual/감사 실패0이다. 사후 큰 JSON 출력 잘림은 compact 조회로 교정했고 문서 초안의 다른 언어 표기도 한국어로 고쳤다.

문서 최종 QA는 메인/로그/이번 정본3파일 strict UTF-8·로컬 링크282개·신규6Python AST/공백·고정 code pin419개·report/contract/audit SHA를 확인하여 통과했다. `git diff --check`도 통과했고 별개 tracked dirty5파일을 그대로 두었다. 기존5파일의 LF→CRLF 경고는 새 분석 실패가 아니며 줄바꿈 일괄 변환을 하지 않았다. 메인의 오래된 ‘현재 단계69’는 이전 기록으로 분리하고 최신 단계74/다음 순서를 명시했다.

## 7. 자료 보존과 다음 단계

각 범위에 ordinary/adversary/compatible target의 원 ID 경로, 동일 계수 비용,26특징/availability, 손실/경계/마진, 원음표 source support, 전체 XML/IR/앞뒤 문맥의 SHA-bound 부모 경로를 저장한다. 원 전체 악보를 잘라 새 정본으로 만들지 않는다. 기존61 Dev 사례는 부모 SHA 이력에서 보존되지만 이번 Train 대조를 별도의 인간 검수나 독립 테스트 사례로 승격하지 않는다.

다음은 새 adversary를 **매 학습 방문 현재 계수에서 재선택**하는 제한 margin 학습이다. 기존 초기 계수 신뢰 범위,24학습/2고정, known-both-paths gradient, 사전 고정 epoch/update cap/전체 방문 평균을 유지한다. 모델 고정 후 일반 추론을 재평가하며, Dev 최고 epoch/계수 튜닝은 하지 않는다. 나머지152범위(후보 부재·원 source/범위 보류 등), 장문 보류, 전체 Roman/전위/조성/종지/NCT 및 독립 Test/공개 모델 비교·운영 UI·작곡편곡 연결은 남는다.

## 8. 재현

PowerShell, workspace `K:\Music Analysis`:

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_full_score_adversary.py --prior-validation output/harmony-online-score-dev-validation-2026-10-05-r1.json --output output/harmony-full-score-adversary-validation-2026-10-05-r1.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_full_score_adversary_trial --output output/harmony-full-score-adversary-2026-10-05-r1
.\.venv\Scripts\python.exe -B scripts/audit_harmony_full_score_adversary.py --root output/harmony-full-score-adversary-2026-10-05-r1
```

출력이 이미 있으면 덮어쓰기를 거부한다. 재실행은 새 `-r2` 경로 등으로 하며 원 결과는 삭제하지 않는다. Actual 시작 이후 새 code/test/script는 수정하지 않는다.
