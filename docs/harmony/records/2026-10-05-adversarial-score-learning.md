# 단계75 — 손실 경쟁 경로를 매번 갱신하는 화음 점수 학습

## 1. 목적과 비교 설계

[단계74](2026-10-05-full-score-adversary.md)의 정확한 경쟁 탐색을 실제 학습에 연결한다. 과거에 고정해 둔 오답 목록이나 현재 일반 승자만 학습하는 것이 아니라, **매 방문 현재 계수에서 adversary와 참조 호환 target을 새로 선택**한다. 일반 선택이 이미 맞아도 오답 경로와의 margin이 부족하면 업데이트한다. [단계72](2026-10-05-online-score-refresh.md)의 일반 승자 갱신과 비교하기 위해 초기 계수·Train 범위·방문 순서·3epoch·update cap·초기 trust box·전체 방문 평균을 그대로 둔다. 단계72의 평균 계수에서 다시 시작하거나 Dev에 맞춰 초기 신뢰 범위를 옮기지 않는다.

118개 참조 호환 범위만 학습하며 원 Train270개 중 나머지152개는 보존한다. 이152개가 모두 ‘정답 후보 부재’인 것은 아니다. 입력/시간 관문·부분 범위 등도 포함한다. 참조 후보를 원 lattice에 삽입하지 않는다. 학습에서 제외한 범위의 성능은 이번 결과로 주장하지 않는다.

## 2. 일반 수식·확정 설정

기존26특징의 완전 진행 비용을 `C(w,y)`라 할 때:

```text
negative = argmin_y [C(w,y) - L(y, reference)]
target   = argmin_reference_compatible_y C(w,y)
delta    = features(negative) - features(target)
violation = L(negative) - dot(w, delta)
gradient[k] = delta[k] if both paths observed k and k is trainable else 0
tau = min(1/50, violation / squared_norm(gradient))
w_next = project_and_quantize(w + tau * gradient, initial_trust_box)
```

Margin이 양수이고 알려진 학습 차원이 있을 때만 갱신한다. 알려진 차원의 차이가 없으면 collision, 탐색 한도에 걸리면 no-update로 기록한다. 보류한 방문도 계수 평균의 분모에는 포함한다. 업데이트의 동일 대조 사후 margin은 다른 구간의 정확도 개선을 뜻하지 않는다. 한도에 걸린 미완성 경로의 대조를 학습에 쓰는 것은 금지한다. 완전 경로의 일부 특징이 unknown인 경우에는 그 차원만 gradient에서 제외한다.

- 손실: 근음+철자 구성음의 시간 불일치와 의미 경계 오류. 경계 비중1/4는 기존 설정 그대로다.
- 24학습/2고정 계수, 양쪽 availability가 확인된 차원만 gradient에 사용한다. Nullable 값을 음악적으로 알려진0으로 바꾸지 않는다.
- 초기 계수의1/2~2배와 기존 부호/범위를 교차한 trust box, 6자리 소수 격자 안쪽으로 양자화한다. 초기0계수는0으로 유지한다.
- 3epoch, 작품군/sample ID의 고정 순서, 모든354방문의 사후 계수 평균. Dev 최고 epoch/모델 선택은 없다.
- 원 raw cap6, adversary2,000,000비교 예산. `feasible_state_raw_edge_comparison`과 일반 batched factor operation은 서로 다른 작업량이다.
- 원 XML/IR·철자·붙임줄·시간 좌표·후보 ID·완전 source 문맥은 보존한다.
- NC 로컬 연구 계약 검증. Adversary/target은 참조 사용·training-only로 남고 일반 추론은 참조를 사용하지 않는다. 운영/UI/Core/외부 API 승격은 하지 않는다.

## 3. 구현·검사

- [학습 연결과 새 모델 계약](../../../src/musicanote_harness/harmony_adversarial_score_learning.py): 기존 PA 업데이트/투영/평균 산술을 재사용하되 ordinary 목적함수 metadata를 새 손실 경쟁 목적함수로 교체하고 새 ID를 계산한다.
- [실제 Train 학습·고정·일반 재선택](../../../src/musicanote_harness/harmony_adversarial_score_trial.py): 매 방문 현재 계수/원 후보/ordinary·negative·target/26특징/availability/손실/출처/SHA를 저장한다. 학습 뒤 모델을 먼저 봉인하고 ordinary Train118범위를 재선택한다.
- [학습 검사](../../../tests/test_harmony_adversarial_score_learning.py), [실제 대조 계약 검사](../../../tests/test_harmony_adversarial_score_trial.py).
- [회귀 실행](../../../scripts/validate_harmony_adversarial_score.py), [최종 사후 감사 v2](../../../scripts/audit_harmony_adversarial_score_v2.py), [보존한 최초 감사 v1](../../../scripts/audit_harmony_adversarial_score.py).

신규10검사는 현재 계수 갱신·현재 정답도 margin 업데이트·보류 방문의 평균 포함·unknown 차원 gradient 차단·고정 계수/trust box·입력 보존·ordinary 목적함수의 오표기·비용/마진 불일치·부분 대조·Dev/미승인/중복·모델 tamper/권리·실제 run-aware 대조·덮어쓰기 거부를 확인했다. 신규6Python strict UTF-8/AST 및 신규10검사는 통과했다. 기존 sealed 모듈은 수정하지 않았다.

기존721+신규10=**731검사/63모듈 PASS**, failure/error0·78.5145549초다. Repository 전체 suite는 아니다. [회귀 영수증](../../../output/harmony-adversarial-score-validation-2026-10-05-r1.json) SHA `a55bf488ef9c7a67572b5085356e1c014bd658adfe7ead25d33e1f4d2ded825c`. 학습 전에 작은 검사10개가0.301초/OK였으며 실제 실행 시작 이후 code/test/script 변경0을 유지한다.

대조 생성 시점의 `weight_update_performed=false`는 아직 그 방문의 업데이트가 수행되기 전임을 뜻한다. 실제 업데이트/보류 여부는 `model.visits[].update.status`와 `weights_before/after`가 정본이다. 이 두 시점을 혼동하지 않는다.

## 4. 실제 결과와 감사

Actual r1은 **855.1949277초/exit0**로 완료했다. 입력 확인·준비를 포함한 모델 고정까지781.5819749초, 이후 일반 Train 재선택/저장/guard까지73.613초다. 원118범위/23전체 악장 package/15작품군·60,129edge이며 원 후보·한도·source 계약을 변경하지 않았다.

| Train 내 지표 — 동일118범위 | 초기 계수 | 이전 ordinary 학습(단계72) | 이번 손실 경쟁 학습 |
|---|---:|---:|---:|
| 전체 범위 일치 | 54/118 | 60/118 | 58/118 |
| 근음+철자 구성음 시간 일치 | 72.3344% | 77.6573% | 77.5572% |
| 위 지표의 작품군 macro | 72.8376% | 77.8664% | 77.5655% |
| 근음만 시간 일치 | 80.8944% | 82.7966% | 83.1971% |
| 근음만 작품군 macro | 80.8137% | 82.1935% | 82.4161% |
| 의미 경계 TP / FP / FN | 87 / 38 / 24 | 82 / 31 / 29 | 85 / 33 / 26 |
| 의미 경계 F1 | 73.7288% | 73.2143% | 74.2358% |

**혼합 결과/운영 미채택**이다. 초기 대비 시간/전체 일치는 개선했지만 더 직접적인 이전 단계72 대비 전체 일치60→58, 구성음 시간 약0.1001%p·작품군 macro 약0.3009%p 퇴행이다. 근음만/경계는 약간 개선했다. 목적함수와 탐색이 더 강해졌다고 정확도가 반드시 올라가는 것은 아니다. 이번 모델을 이전 운영/연구 기준선의 무조건적인 대체로 선택하지 않는다. 기존 정답 소실과 주석의 불확실성을 모두 보존한다.

354방문 중341실제 업데이트·7trust-box no-change·6resource no-update다. 완전 대조348개 모두 positive margin/known gradient를 갖고 collision0, 일반 승자가 참조와 맞으면서 positive margin인 방문173개도 포함했다. 3epoch의 업데이트/신뢰 범위 무변경/보류는 각각115/1/2,113/3/2,113/3/2다. 이 방문들은 독립 사례354개나 음악354곡이 아니다.

이전 단계72와 최종 경로가 다른 구간10개, 이전 전체 정답 소실3개/새 전체 정답1개다. 초기와 비교하면 소실3개/새 정답7개다. 나머지152범위는 이번 모델로 재평가하지 않았다. 근음+구성음 참조 평가 시간5993/24quarter는 겹치는 범위의 합으로 유일한 음악 분량이 아니다.

Known-both-paths gradient 제한도 유지된다. Conditional ornament129대조, absent-third/altered-fifth/seventh와 late-member205대조에서는 양쪽 availability가 성립하지 않아 해당 차원의 업데이트를 하지 않았다. 최종24학습 가능 계수 중23개가 초기와 달라졌고 `unknown_root=.2`와 고정2계수는 그대로다. 예를 들어 complexity `.1→.193457`, run count `.015→.021208`, lowest nonmember `.25→.180608`, functional role complexity `.05→.092232`다. 각각 범위 안의 학습 결과이지 새 음악적 사실/확률이 아니다.

### 계산 한도·지연

Sonata02-2 `[3,8)`와 Mozart K281-2 `[545/6,94)`의 adversary는 각 epoch 모두2M비교에서 보류했다. 두 구간을 미리 제외하거나 한도를 늘리지 않았다. **학습 보류여도 최종 ordinary 분석은 수행**하고, 다른 구간에서 학습한 가중치가 그 ordinary 결과를 바꿀 수 있다. K281-2의 raw 경로가 달라진 사실을 직접 학습 성공으로 해석하지 않는다.

354방문의 준비/선택/저장을 합한 시간은 최소0.031초·중앙0.420초·nearest-rank p958.948초·최대56.427초다. 첫 방문의 source 준비와 당시 병행 회귀 검사, 이후 준비 cache가 섞였으므로 순수 adversary 지연/운영 응답 보장이 아니다. 보류6방문은35.317~56.427초였다. 원2M의 두 연산 단위 차이는 유지한다.

### 실제 개선·퇴행과 비용 원인

아래 좌표는 quarter 기준 `[start,end)`이며 마디 표시는 저장된 전체 IR의 display 정보다. 모든 사례는 원 전체 XML/IR와 note/sounding IDs·전후 문맥의 SHA-bound 부모를 유지한다. 과거 경로 비용은 **이번 고정 계수로 다시 계산**했으므로 서로 다른 모델 비용을 직접 비교하지 않는다. 참조 주석과의 일치/불일치를 설명하는 것이며 인간 검수된 절대 정답으로 승격하지 않는다.

1. **경계 개선 — Beethoven Sonata03-2, m6~7 `[11,25/2)`**: [case](../../../output/harmony-adversarial-score-2026-10-05-r1/postfit/cont_db4f0a962816216e4545.json.gz). C♯7 → F♯7 → B삼화음의 첫 교체가11.5→11.75quarter로 이동해 참조와 전체 일치한다. 같은 계수 비용은 `.5102477341→.4863225675`, 차이 `-143551/6000000`다. 새 경로의 blocker비용은1/12 증가하지만 unanchored-change `.078136` 및 근음 지연 `.0291225`가 감소해 이를 넘는다. 마디/작품별 교체 강제 조건이 아니라 동일 전체 비용의 재선택이다.
2. **구성음 퇴행 — Beethoven Quartet01-4, m269 `[2147/4,1075/2)`**: [case](../../../output/harmony-adversarial-score-2026-10-05-r1/postfit/cont_05a973a926c1c81874af.json.gz). 근음F는 같지만 참조 F–A–C에 E를 추가한 F–A–C–E를 선택해 전체 일치가 소실된다. 비용 `.2228512667→.214665`, 차이 `-61397/7500000`다. Complexity `.193457`와 조건부 ornament credit 소실 `.1064302`의 불이익보다 비구성음/강세/lowest 비용 절감 `.1925666+.0553042+.0602027`이 조금 더 크다. **단순 경계 개선만으로 구성음 해석이 해결되지 않음**을 보여준다.
3. **진행 과병합 퇴행 — Sonata03-2, m52~53 `[103,209/2)`**: [case](../../../output/harmony-adversarial-score-2026-10-05-r1/postfit/cont_5f130fc395c3561ba6c4.json.gz). B7 → C삼화음 → G삼화음 대신 B7 → E–G–B를 선택해 참조 일치1.5→1quarter다. 비용 `.3827624667→.37021805`, 차이 `-150533/12000000`다. 새 leading-tone credit `.175876` 및 turnover/run/조표외/근음 이동 절감이 비구성음/강세/lowest 증가를 조금 넘는다. 기능적 해결 후보의 credit가 실제 교체를 덮는 위험이 남는다. 준비/해결을 확정했다는 뜻은 아니다.
4. **역할 해석 퇴행 — Sonata03-2, m8 `[14,31/2)`**: [case](../../../output/harmony-adversarial-score-2026-10-05-r1/postfit/cont_b0b624e987d33699d356.json.gz). 첫 E–G♯–B 음 집합은 같지만 기능적 근음B 가설을 surface 근음E로 바꿔 참조 전체 일치가 소실된다. 비용 `.2140888333→.2062213333`, 차이 `-3147/400000`다. 역할 복잡도 `.092232` 절감이 six-four credit 소실 `.067712`와 근음 이동 `.0166525` 증가를 넘는다. 단순 pitch set뿐 아니라 기능적 역할/앞뒤 해결의 점수 균형이 필요하다는 근거다. 이 예를 ‘E삼화음이면 언제나 오류’인 규칙으로 만들지 않는다.
5. **미해결 유지 — Chopin op30-4, m3 `[6,35/4)`**: [case](../../../output/harmony-adversarial-score-2026-10-05-r1/postfit/cont_635ba41c28793857d7b4.json.gz). 앞 D♯감7음 집합에 가운데 G♯7이 합쳐져 전체 한 run으로 남는다. 세 학습 방문 및 고정 평균 모델 모두 미해결이며, 새 계수에서 이전/새 같은 경로 비용은 모두 `.2992248636`다. 강한 대조가 생겼다는 사실만으로 해결했다고 보고하지 않는다.

추가로 Mozart K280-1 `[52,56)`은 참조와 맞는 시간이2→3quarter로 부분 개선됐고, Chopin `[152,154)`는 같은 C♯–E–G♯ 음 집합의 근음을 G♯→C♯로 바꾸어 맞는 시간이0→1quarter로 늘었지만 둘 다 전체 일치는 아니다. 변경10개 모두 postfit packet에 저장하며 선택한 성공 사례만 남기지 않는다.

### 실패·교정·사후 감사

최초 감사 v1은 첫 대조에서 `adversarial_full_source_contrast_changed`로 exit1했다. 조사 결과 재계산 ID 경로는 tuple, JSON 저장 경로는 list여서 직접 Python equality가 false였다. 세 경로의 순서/값은 같고 canonical JSON content hash는 일치했다. **봉인한 학습/실행/감사 v1 코드는 그대로 보존**하고 별도 v2에서 JSON 계약 동등성으로 비교했다. 배열 순서를 정렬하거나 수치/unknown을 완화하지 않는다. Postfit ID 비교도 list로 정규화했다. 모델/원자료/최종 경로/가중치 재학습은0이다.

[직렬화 회귀 검사](../../../tests/test_harmony_adversarial_serialization.py)4개와 [별도 영수증](../../../output/harmony-adversarial-serialization-validation-2026-10-05-r1.json)이 PASS다. Tuple/list의 JSON 동등성, 배열 순서 반전 거부, null과 알려진0 구별, 유리수/availability 변경 거부를 검사했다. 기존731검사와 별도로 실행해 총 관련735개이며 원731검사 영수증을 덮어쓰지 않았다. 별도 영수증 SHA `58733d37f949149b253437b935f8d8c323f5d0fb6f88d5207c80c79dae46c718`.

[최종 감사](../../../output/harmony-adversarial-score-2026-10-05-r1/post-seal-audit.json)는 **PASS/exit0**다. 2,696고유SHA·118범위/23전체 source·원60,129edge·354방문/348완전 대조·1,174독립 경로 비용·236동일 계수 source receipts·모든 업데이트/투영/전체 방문 평균·세 조건 지표를 재생했다. 새 탐색이나 다른 fit/checkpoint 선택은 하지 않았다. 원 실행 code pin421개는 변경0이다. 별도 v2 감사 코드는 자기 SHA `1e8e66324dd91942b9fe5eced9bc885d43fb99e3140f069aa9adf699ce72b0c7`로 결합한다. 보존 v1 SHA는 원 실행 계약에도 묶인다.

정본 SHA:

- [완료 report](../../../output/harmony-adversarial-score-2026-10-05-r1/report.json): `9146c3783006ae433041e3bc05d1db2266e6f9cb03d6b8771e6d046705b96034`
- [실행 계약](../../../output/harmony-adversarial-score-2026-10-05-r1/run-contract.json): `80af8b724c41701a9248b873d83c69893a1eb795df9cf1d08755f41a242dcd70`
- [고정 모델](../../../output/harmony-adversarial-score-2026-10-05-r1/model.json.gz): `2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf`
- [평가 전 모델 봉인](../../../output/harmony-adversarial-score-2026-10-05-r1/model-freeze.json): `4f237683c0eb1f1aa3b5afdf87f16682bd204903f3769c4f37874da5452e453f`
- [사후 감사](../../../output/harmony-adversarial-score-2026-10-05-r1/post-seal-audit.json): `2b315941ef3c180edbd29565d5cc6299652675167358842f462f054c65157b34`

사후 콘솔의 큰 결과 잘림과 요약 조회의 잘못된 key(`labels`/`matched_time`)는 실제 저장 schema의 `components.root_members`/`matched`를 확인한 compact 조회로 교정했다. 이는 실험 report 손실이 아니다. 중간 안내의 다른 언어 문장은 바로 한국어로 정정했고 최종 문서의 언어 QA를 별도로 수행한다.

최종 QA는 메인/로그/이번 정본3문서 strict UTF-8·언어·공백·로컬 링크293개, 신규8Python AST/UTF-8/공백, 원421code pin 및2,696고유 봉인 SHA·v2 감사 코드 연결을 확인해 PASS다. `git diff --check`도 PASS이며 기존 tracked dirty5파일을 그대로 보존했다. 기존5파일의 LF→CRLF 경고는 분석/감사 실패가 아니고 줄바꿈 일괄 변환을 하지 않았다. 초안에서 `unknown_root`를 초기0으로 적은 것은 실제 모델 `.2`를 확인해 교정했다.

## 5. 평가 해석과 남은 범위

이번 평가는 **학습 자료 안의 진단**이다. 근음+철자 구성음 시간, 전체 범위 일치, 경계 F1, 작품군 평균을 함께 비교하고 기존 정답 소실도 삭제하지 않는다. 전체 Roman/전위/국소 조성/NCT/종지의 완성이나 독립 Test 정확도가 아니다. 다음은 **이번 모델을 고정한 채 원 Dev 전범위를 같은 평가표로 비교**하는 단계다. 이미 노출된 Dev는 독립 Test가 아니며 학습·최고 epoch/계수 선택에 쓰지 않는다. 이번 Train 퇴행을 지우거나 Dev를 보고 손실 비중을 바꾸지 않는다. 원 후보 ceiling·source 관문·장문 보류·독립 작품 확대/공개 모델 비교·작곡/편곡 연결은 여전히 필요하다.

각 postfit 사례는 새 모델 계수 아래 새 승자와 이전 ordinary 승자의 비용/원음표 receipt를 함께 저장한다. 인간 의견·원주석은 별도 참조이며 Core의 사실로 덮어쓰지 않는다. 인간 검수 여부와 독립 사례 여부는 false로 보존한다. 이 코드에는 특정 악보/마디를 위한 규칙이 없다.

## 6. 재현

PowerShell, `K:\Music Analysis`:

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_adversarial_score.py --prior-validation output/harmony-full-score-adversary-validation-2026-10-05-r1.json --output output/harmony-adversarial-score-validation-2026-10-05-r1.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_adversarial_score_trial --output output/harmony-adversarial-score-2026-10-05-r1
.\.venv\Scripts\python.exe -B scripts/audit_harmony_adversarial_score_v2.py --root output/harmony-adversarial-score-2026-10-05-r1
```

이미 존재하는 출력은 덮어쓰지 않는다. 재실행은 새 r2 경로를 사용하며 원 결과는 삭제하지 않는다. 실제 실행 시작 이후 code/test/script는 수정하지 않는다.
