# 단계72 — 이전 정답을 포함한 Train 경쟁 경로 갱신

## 1. 목적과 사전 결정

단계71의 고정 오류65대조 전체 점수 학습은 Dev 시간 일치28.8915%→11.8320%·완전16/51→5/51로 크게 퇴행하여 미채택했다. 이전 정답을 학습에서 제외했고 새 계수로 생기는 더 싼 오답을 다시 찾지 않았다는 문제가 있다. 이것이 퇴행의 단독 원인이라고 확정하지 않고, **이전 정답 보호·현재 승자 갱신·초기 점수 신뢰 범위**를 함께 갖춘 Train 전용 실험을 한다. 이번에는 Dev를 새로 추론/평가하지 않는다.

새 화음/NCT 규칙·정답 후보·원음표 삭제·작품/마디별 예외는 추가하지 않는다. 이전에 만들었던 원26특징, 같은 후보망/정확 시간/붙임줄/철자/자원 상한을 유지한다. 전체 NCT·국소 조성·Roman·종지·작곡편곡 성과를 주장하지 않는다. 기존 화면과 Claude Phrase/Motif는 바꾸지 않는다.

## 2. 자료와 학습 계약

- 승인된 단계70 원 Train270범위 중 source clock 통과·reference-compatible 경로가 있는 **118범위/23악장 패키지/15명명 작품군·원60,129edge**를 모두 사용한다. 이전 정답54개와 선택 오류64개를 포함한다. 후보 부재/cap·부분/보류 등을 포함하는 나머지152범위는 원 기록에 남기며 새 가중치 평가를 한 것처럼 합산하지 않는다. 범위를 좁혔으므로54/118을 이전 전체 Train54/205와 같은 정확도 분모로 비교하지 않는다.
- Stage67 네 계수+Stage69 timing의 초기 전체 점수에서 시작한다. 단계71 실패 모델은 초기값으로 쓰지 않는다. 원26차원 중24차원 trainable·2고정 계수는 그대로다.
- **3epoch·update cap1/50·초기값 신뢰 배율2**를 실제 Train 실행 전에 고정한다. 양성/음성 부호별 초기 계수 절대값의1/2~2배와 기존 전역 bounds를 교차한다. 초기0은0이다. 6자리 grid는 trust box 안쪽으로 양자화하며 고정 계수는 바꾸지 않는다. 신뢰 배율은 음악적 확률/음악적 금지 규칙이 아니다.
- 작품군/표본 ID 순으로 매 방문 현재 가중치의 **ordinary joint winner**와 같은 가중치의 참조-compatible latent target을 다시 선택한다. Target은 Train에서만 주석을 사용하고 화면/일반 추론으로 내보내지 않는다. 같은 signature의 여러 raw edge는 완료 run 단위로 계산한다.
- **Loss-augmented search는 이번에 구현하지 않았다.** 이전 정답도 매 회 방문하고 현재 점수에서 틀리게 바뀌면 새 대조를 만든다. 아직 맞는 구간에서 모든 가까운 오답을 예방적으로 찾는 margin 보장은 없으며 negative pool은 불완전하다.
- 원 normalized spelling/time+boundary loss1/4, 양쪽에서 known인 차원만 gradient, capped PA·projection·전체 방문의 평균을 사용한다. Margin 만족/관측 feature collision/trust box 제한/자원 보류를 구별한다. None을 관측0으로 임의 대입하지 않는다.
- Epoch의 최고 결과를 골라 배포하지 않고 **모든 방문 후 가중치의 평균**을 한 번 고정한다. Model SHA를 저장한 뒤118범위에서 ordinary 선택을 실제 재계산한다. 이는 학습 자료 내 진단이며 독립 정확도가 아니다. 현재 Dev fit/평가/계수 sweep은 없다.
- 원 NC 로컬 연구 사용 계약과 출처·라이선스 SHA를 유지한다. 부모 JSON에는 이미 노출된 Dev행이 있어 ‘한 번도 Dev를 읽지 않았다’고 주장하지 않는다. 새 Dev 자료는 학습/재추론에 넣지 않는다. 상업/운영/API/체크포인트 재배포는 승격하지 않는다.

## 3. 구현과 검증

[학습·신뢰 범위](../../../src/musicanote_harness/harmony_online_score_learning.py), [Train 실제 실행](../../../src/musicanote_harness/harmony_online_score_trial.py), [학습 검사](../../../tests/test_harmony_online_score_learning.py), [실행 계약 검사](../../../tests/test_harmony_online_score_trial.py), [관련 회귀](../../../scripts/validate_harmony_online_score.py), [사후 감사](../../../scripts/audit_harmony_online_score.py)를 새로 추가했다. 기존 단계71 이하 봉인 code/test/script는 수정하지 않는다.

원118범위의 graph/source/clock/target/loss 준비만 범위별 cache로 재사용한다. 현재 가중치의 ordinary와 target 선택은 cache하지 않는다. 각 epoch의 두 경로·26벡터/availability·비용·source scope SHA·model 업데이트·전체 XML/IR SHA 연결을 저장한다. Post-fit ordinary의 결과/원 ID·평가도 따로 저장한다. 입력/코드/출력 SHA를 마감 시 다시 확인한다.

신규14검사는 초기 가중치의 신뢰 범위·내향 quantization·현재 가중치 전달/재방문·이전 정답의 새 오류·unknown/resource 보류·모델 평균/재현·권리/Dev/변조 거부·원source 보존·actual source 특징 대조·덮어쓰기 거부를 검사했다. **14PASS/0.326초**. 신규6Python AST/strict UTF-8 PASS. 기존 관련686+신규14 = **700검사/58모듈 PASS**, failure/error0·67.439초이며 repository 전체 suite는 아니다. [회귀 정본](../../../output/harmony-online-score-validation-2026-10-05-r1.json), SHA `39b64dd18543e8ef1359c25137f6e563b0c45a841c6203ebebfed872a25f6931`. 실제 음악적 성과는 다음 절에 별도로 기록한다. 초안의 다른 언어 잔여 문구는 한국어로 교정했다.

## 4. 실제 결과와 결정

Actual r1은 **434.361초/exit0**, 원자료 준비·354회 방문·fit/model 고정까지374.424초다. 실행 시작 후 code/test/script는 수정하지 않았다. 118범위/23전체 악장 source/15명명 작품군·원60,129edge를 유지했다. 3epoch의 현재 정답/업데이트/trust제한 수는56/62/0,56/61/1,59/58/1이다. 합계171정답 방문·181업데이트·2trust box 제한·자원 보류0이다. 회차마다 서로 다른 계수 아래 평가이므로 이를118개에 대한 최종 정확도로 읽지 않는다.

모든 방문 가중치를 평균하고 model SHA를 고정한 뒤118범위를 ordinary로 실제 재분석했다.

| 동일한 reference-reachable Train 범위만의 진단 | 초기 점수 | 고정 평균 모델 |
|---|---:|---:|
| 전체 범위 일치 | 54/118 (45.7627%) | 60/118 (50.8475%) |
| 근음+철자 구성음 시간 일치 | 72.3344% | 77.6573% |
| 위 시간 일치 작품군 macro | 72.8376% | 77.8664% |
| 근음만 시간 일치 | 80.8944% | 82.7966% |
| 정확 의미 경계 TP/FP/FN | 87/38/24 | 82/31/29 |
| 정확 의미 경계 F1 | 73.7288% | 73.2143% |
| 선택/보류 | 118/0 | 118/0 |
| 평가 가능한 시간의 예측 coverage | 100% | 100% |

새 전체 정답8개를 얻고 이전 정답2개를 잃었다. 의미 선택이 달라진23범위 중 시간 개선16·퇴행4·무변화3이다. 의미 run 수 분포는 초기1개43·2개36·3개30·4개7·5개2에서, 새1개46·2개36·3개32·4개3·5개1로 바뀌었다. 단계71처럼 모든 구간을 한 화음으로 만드는 붕괴는 없다. 그러나 경계 재현율/F1이 조금 내려간 혼합 결과다.

초기→평균 계수는 nonmember1→`.872704`, 구성음 복잡도.1→`.166328`, turnover.02→`.029594`, run count.015→`.018983`, metric.25→`.163474`, lowest.25→`.161556`, conditional ornament−.5→`−.509508`이다. Stage71처럼 복잡도1.200644/turnover.563377로 급증하지 않는다. 26개 전체 계수·354visit·epoch/averaging/availability는 [model.json.gz](../../../output/harmony-online-score-2026-10-05-r1/model.json.gz)에 보존한다.

**결정: 연구 후보로 보존하고 운영/화면 적용은 보류한다.** 개선은 학습 자료 내, 그중 참조 경로가 후보에 있는118범위만의 결과다. 원270범위 중 나머지152범위의 새 성능·현재 Dev·독립 Test·whole Roman/전위/국소 조성/전체 NCT 정확도는 이번에 측정하지 않았다. 현재계수 갱신+확대cohort+신뢰범위를 결합했으므로 각 요소의 단독 기여를 증명하는 ablation도 아니다. 초기72.3344%와 단계71 Dev28.8915%는 다른 자료/분모이며 비교해 개선 폭을 부풀리지 않는다.

## 5. 원음표 연결 사례·남은 한계

각 방문 파일은 원 SHA-bound scope packet의 전체 XML/IR·note/sound IDs·전후 문맥·원 graph로 연결된다. Post-fit 파일에는 실제 새 선택 경로가 있고, 원scope에는 초기 선택/참조가 있다. 같은 새 평균 계수 아래 초기 경로와 새 경로 비용을 독립 계산했으며, 다른 계수의 비용을 직접 비교하지 않았다. 범위는 global quarter의 `[start,end)`이다. Target는 Train 주석을 사용한 경로이지 인간 재승인 정답이나 blind prediction이 아니다.

### 5.1 Quartet01-4 — F 삼화음과 추가 E의 비용 균형 개선

Sample `cont_05a973a926c1c81874af`, Beethoven quartet n01op18-1_04 `[2147/4,1075/2)`. 초기 F/A/C/E를 새 F/A/C로 바꾸어3/4quarter와 전체 범위를 참조에 일치시켰다. [첫 방문·초기 경로/target/벡터](../../../output/harmony-online-score-2026-10-05-r1/visits/1-cont_05a973a926c1c81874af.json.gz), [고정 모델의 실제 선택](../../../output/harmony-online-score-2026-10-05-r1/postfit/cont_05a973a926c1c81874af.json.gz).

새 계수 아래 초기 비용.185311 대 새.178169다. 추가 E를 비구성음으로 두는 비용은 증가하지만, 조건부 순차 장식 근거와 구성음 복잡도 절감이 이를 소폭 상쇄한다. NCT가 없어서 실패했던 것이 아니라 기존 근거의 점수 균형 문제였던 대조다. 특정 작품의 E를 무조건 빼는 규칙을 추가하지 않았다.

### 5.2 Corelli op01n03a — 넓은 단일 후보를 실제 두 화음으로 바꿈

Sample `cont_b857a89b132bfce41df1`, `[91/2,95/2)`. 초기 F♯/A♯/C♯/D/E 한 후보에서 C♯/E/G♯ `[91/2,46)` → D/F♯/A `[46,95/2)`로 바뀌어2quarter와 전체 범위를 맞혔다. [고정 모델 선택](../../../output/harmony-online-score-2026-10-05-r1/postfit/cont_b857a89b132bfce41df1.json.gz), [학습 방문](../../../output/harmony-online-score-2026-10-05-r1/visits/1-cont_b857a89b132bfce41df1.json.gz).

새 계수 비용은 초기 `525071/1250000`(.4200568) 대 새 `1313813/4000000`(.32845325)다. 넓은 구성음 비용 감소가 새 두 화음의 run/교체·비구성음 비용 증가를 상쇄한다. 새 근음/철자는 원 후보에서 선택했으며 XML에 음을 추가한 것이 아니다. 화음 이름의 Roman/국소조성은 여기서 확정하지 않는다.

### 5.3 Beethoven Sonata02-2 — 첫 A7의 G를 제거한 퇴행

Sample `cont_e92872bb2c18325ddcfa`, `[3,8)`. 초기 A/C♯/E/G `[3,4)` → D/F♯/A `[4,6)` → A/C♯/E/G `[6,8)`의 참조 일치에서, 첫 구간만 A/C♯/E로 바뀌어1quarter와 전체 정답을 잃었다. [고정 모델 선택](../../../output/harmony-online-score-2026-10-05-r1/postfit/cont_e92872bb2c18325ddcfa.json.gz), [학습 방문](../../../output/harmony-online-score-2026-10-05-r1/visits/1-cont_e92872bb2c18325ddcfa.json.gz).

새 계수 아래 초기 비용 `47207261/210000000`(약.224796) 대 새 `2157601/10000000`(.2157601)다. 구성음 복잡도−.0332656가 실제 G의 nonmember/metric/lowest 비용 증가를 압도한다. 이곳에 맞춰7화음을 강제하거나 가중치를 고치지 않았다. 실제7음의 지속·강세·해결 및 전후 선택 아래 NCT 설명을 더 잘 비교해야 한다.

### 5.4 Chopin op30-4 — 방문 때 모두 정답이어도 평균 모델은 퇴행

Sample `cont_635ba41c28793857d7b4`, BI105-4op30-4 `[6,35/4)`. 초기 D♯/F♯/A/C♯ `[6,15/2)` → G♯/B♯/D♯/F♯ `[15/2,8)` → D♯/F♯/A/C♯ `[8,35/4)`에서, 전 구간 D♯/F♯/A/C♯로 병합되어1/2quarter와 전체 정답을 잃었다. [고정 모델 선택](../../../output/harmony-online-score-2026-10-05-r1/postfit/cont_635ba41c28793857d7b4.json.gz), [첫 방문](../../../output/harmony-online-score-2026-10-05-r1/visits/1-cont_635ba41c28793857d7b4.json.gz).

새 계수 비용 초기 `6583331/22000000`(약.299242) 대 병합 `1403233/5500000`(약.255133)다. 세 번의 방문에서 ordinary loss는 모두0이라 이 범위에서 업데이트하지 않았다. 하지만 다른 범위에서의 업데이트와 전체 평균이 가까운 오답을 유리하게 만들었다. **모든 이전 정답을 재방문하는 것과 모든 경쟁 오답을 margin으로 보호하는 것은 다르다.** Ordinary 갱신의 명확한 한계이며 이 실패를 학습 성공으로 숨기지 않는다.

다음 실행은 **이미 고정된 이번 모델의 별도 Dev 성능·퇴행 확인**이다. 노출된 개발 자료의 결과이지 독립 Test로 보고하지 않으며, Dev를 보고 계수를 재설정하지 않는다. 그 뒤의 큰 학습 보완은 완료 run/전이와 같은 exact 점수 아래 **Train-only loss-augmented 경쟁 탐색**을 연결하는 것이다. 현재 정답인 구간도 위험한 가까운 오답을 비교할 수 있어야 한다. 원 후보/cap/unknown/원 비용 검산을 유지하고 작은 DAG 전수 탐색으로 실제 최적 탐색을 검증한다.

## 6. 사후 감사와 정본

사후 감사는 **PASS/exit0**다. 2,083고유 SHA, 23전체 악장 패키지의 원60,129edge 복원, 118Train범위의 원자료 특징/availability/loss를 확인했다. 354방문의 ordinary/target 대조·update·현재 계수 순서·전체 평균 모델을 다시 계산하고, 826경로 비용(354×2+118)과 initial/post-fit 지표를 독립 재생했다. 이는 **새 decoder 탐색을 다시 실행한 것은 아니다.** 실제 선택의 비용/참조 호환성을 검산했으며 탐색의 최적성은 별도 작은 DAG 전수 경로 검사로 확인했다. Dev의 새 추론/평가도 없다.

Actual report는 `complete=true`다. Progress의 마지막 online checkpoint는 `complete=false`,354/354이고 별도 post-fit은118/118 완료다. 중간 checkpoint를 완료 정본으로 오해하거나 사후에 수정하지 않는다. 기존 화면·Core/원주석·서버·MusicSearch/Composition/Claude Phrase·Motif/별개 dirty/Git를 유지하며 API/운영 승격/merge/commit/push0이다.

정본과 SHA:

- [실제 결과 report.json](../../../output/harmony-online-score-2026-10-05-r1/report.json): `2c442cc37756e26958d550da90c238ecef8fb6792a00cfd9274edf40d75860d1`.
- [고정 평균 model.json.gz](../../../output/harmony-online-score-2026-10-05-r1/model.json.gz): `029e2de31ab6e5d9e5fa65eb229c63fe649cce10ddd987dbab4c2b7f3f06f331`.
- [사전 run-contract.json](../../../output/harmony-online-score-2026-10-05-r1/run-contract.json): `f2ca60b9d0bae844c5e81c6b6644965f4af6a726ad695066dcb4e62f39fd37ff`.
- [post-fit 전 model-freeze.json](../../../output/harmony-online-score-2026-10-05-r1/model-freeze.json): `a07e5b902424fd2798cd43fdf55788e37b9ae19f59573a27f80a878cb573ce50`.
- [사후 감사 post-seal-audit.json](../../../output/harmony-online-score-2026-10-05-r1/post-seal-audit.json): `6da04003ca3a48617058e8dc3ced1e5975fdc9e5a449a530495d22567f30421f`.

감사 code SHA는 `e1306a08240009000e8b627f49b727ff0e4ce69862bb7b29d933f0568c9ebe6c`다. 이번 실제 학습/회귀/감사에 실패는 없었으며 결과의 음악적 한계·퇴행은 위 절에 별도로 기록했다. 수백 검사 통과나 감사 성공을 전체 음악적 정확도로 대신하지 않는다.

## 7. 재현

기존 출력 덮어쓰기를 거부한다. 새 디렉터리/파일을 사용한다.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_online_score.py --prior-validation output/harmony-full-score-validation-2026-10-05-r1.json --output output/harmony-online-score-validation-2026-10-05-r2.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_online_score_trial --output output/harmony-online-score-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/audit_harmony_online_score.py --root output/harmony-online-score-2026-10-05-r2
```
