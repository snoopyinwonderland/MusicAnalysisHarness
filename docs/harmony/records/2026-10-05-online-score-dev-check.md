# 단계73 — 고정 온라인 모델의 별도 Dev 성능 확인

## 1. 목적과 사전 계약

단계72는 참조 경로가 있는118Train범위에서 전체 일치54→60·근음+철자 구성음 시간72.3344%→77.6573%로 개선했지만 기존 정답2개를 잃고 경계F1이 조금 내려갔다. 이 결과를 운영 정확도로 읽지 않고, **이미 고정된 모델을 원 Dev 전체에 적용**한다. 새 fit·계수 sweep·최고 epoch 선택·새 화음/NCT 규칙·작품/마디별 예외는 없다.

- 원 단계69 Dev72구간/63graph/44,204edge·14전체 악장 source/9명명 작품군·선택63/보류9·완전51/부분21의 목록을 유지한다. 참조 경로가 후보에 있는 구간만 골라내지 않는다. 원 보류도 분모에 남기며 이번에 후보/cap을 바꾸어 재시도하지 않는다.
- 비교 arm은 같은 초기 전체 점수와 단계72 고정 평균 모델이다. 초기 점수의 원 경로 ID·exact 비용·집계 지표가 단계69 `timing_calibrated`와 같은지 검사한다. 실패한 단계71 모델로 시작하지 않는다.
- 단계72 모델·report·model-freeze·감사 SHA 및 NC 로컬 연구/출처 계약을 확인하고 모델은 다시 fit하지 않는다. 원26특징/24trainable/2고정 계수·시간/철자/붙임줄·최대6raw edge/2Mbudget·원 graph를 유지한다.
- 두 arm ordinary 선택72개를 먼저 파일/SHA로 봉인하고 그 뒤 이번 평가의 참조 report를 열어 지표를 계산한다. 추론에서는 target/reference-compatible decoder를 호출하지 않는다. 참조 witness는 봉인 뒤 사례의 비용 진단에만 사용한다.
- 이전부터 노출된 Dev이고 계보 확인용 부모 JSON에도 Dev행이 있다. **독립 blind Test가 아니다.** 새 Dev fit/계수 조정·상업/API/운영/체크포인트 재배포로 승격하지 않는다.

## 2. 구현·검증

[고정 모델 평가](../../../src/musicanote_harness/harmony_online_score_dev_trial.py), [계약 검사](../../../tests/test_harmony_online_score_dev_trial.py), [관련 회귀](../../../scripts/validate_harmony_online_score_dev.py), [사후 감사](../../../scripts/audit_harmony_online_score_dev.py)를 별도 추가했다. 기존 단계72 이하 code/test/script는 수정하지 않는다. 전체 XML/IR·note/sound IDs·원 graph·전후 문맥·두 경로와 비용의 연결을 유지한다. 단계71의 이전61사례 파일은 삭제하지 않고 새 사례에서 연결한다.

신규8검사는 기존 출력 거부, 고정 Train 전용 모델/감사 계약, 부분/보류/후보 부재를 포함한 구간 목록, duplicate/누락 거부, ordinary 선택의 주석/fit 미사용, 초기 path/cost/보류 일치, 모든 예측 봉인 후 참조 개방, 출처 SHA를 확인했다. **8PASS/0.367초**, 신규4Python AST/strict UTF-8 PASS다. 기존700+신규8의 **708검사/59모듈 PASS**, failure/error0·66.252초이며 repository 전체 suite는 아니다. [관련 회귀 정본](../../../output/harmony-online-score-dev-validation-2026-10-05-r1.json), SHA `332317b815273d28a58bc1d2b3f661f62b43697c16591498f3a1ac075c1d6d15`다. 실행 전 모델/출처2,149읽기 검산은 PASS였고 fit을 재실행하지 않았다. 실제 Dev와 사후 감사 결과는 아래에 별도로 기록한다.

## 3. 실제 결과와 결정

Actual r1은 **145.055초/exit0**다. 모델을 다시 fit하지 않았고 실행 시작 후 code/test/script를 수정하지 않았다. 원72구간/63graph/44,204edge·14전체 악장 패키지/9작품군을 그대로 선택/평가했다. 63선택/9원보류(자원2·bounded plan1·source preflight6), 완전51/부분21·원 후보 ceiling36/51을 유지했다. 학습 작품군15개와 Dev명명 작품군9개의 ID 교집합은0이지만 전체 중복/노출 감사가 완료된 독립 Test는 아니다.

| 동일 Dev 목록·기준 | 초기 전체 점수 | 단계72 고정 평균 모델 |
|---|---:|---:|
| 완전 평가 구간 일치 | 16/51 (31.3725%) | 19/51 (37.2549%) |
| 근음+철자 구성음 시간 일치 | 28.8915% | 31.9253% |
| 위 시간 일치 작품군 macro | 53.1500% | 46.3740% |
| 근음만 시간 일치 | 35.5309% | 35.4959% |
| 근음만 작품군 macro | 62.1404% | 52.7027% |
| 정확 의미 경계 TP/FP/FN | 47/23/16 | 48/11/15 |
| 정확 의미 경계 F1 | 70.6767% | 78.6885% |
| 예측 coverage / 선택 / 보류 | 43.7106% / 63 / 9 | 43.7106% / 63 / 9 |

새 전체 정답4개를 얻고 이전 전체 정답1개를 잃었다. 선택이 바뀐21record/20고유 exact range 중 시간 개선13·퇴행3·동일5record다. 시간 차이가0이 아닌16record는15고유 exact range이며, 전체72범위에 중복/겹침이 있어 시간 증가를 유일한 음악 길이로 읽지 않는다. 의미 run 수는 초기1개11·2개20·3개28·4개3·5개1에서 새1개13·2개26·3개21·4개3으로 바뀌었다. 단계71의 전체 단일화 붕괴와는 다르다.

**결정: 혼합 결과/운영 승격 보류.** 시간 micro와 경계는 좋아졌지만 작품군 평균과 근음은 퇴행했다. 높은 숫자 하나만 골라 일반적 성능 향상으로 보고하지 않는다. 원 보류 때문에 관측 가능한 화성 시간의 예측 coverage도43.71%에 머문다. Whole Roman·전위·국소 조성·전체 NCT·종지 정확도나 편곡/작곡 성능을 측정한 것이 아니다. 초기 점수는 원 단계69 결과와 path/cost/table 모두 같아 비교 기준이 변하지 않았다.

작품군별 근음+구성음 시간 일치(분모가 존재하는8작품군의 macro에 사용):

| 작품군 / 원 범위 수 | 초기 | 고정 모델 |
|---|---:|---:|
| Beethoven Sonata07-2 / 7 | 87.8661% | 78.6611% |
| Corelli op01n05a~d / 16 | 68.3333% | 80.6667% |
| Beethoven Sonata09-2 / 5 | 66.6667% | 0% |
| Chopin op50-2 / 5 | 3.8817% | 4.2514% |
| Beethoven Quartet06-2 / 6 | 5.2718% | 5.2718% |
| Beethoven Quartet08-2 / 6 | 80.9524% | 80.9524% |
| Corelli op01n04a~d / 16 | 46.7105% | 53.9474% |
| Mozart K283-1 / 6 | 참조 성분 평가 불가 | 참조 성분 평가 불가 |
| Chopin op50-1 / 5 | 65.5172% | 67.2414% |

Sonata09-2는5scope 중 이 성분의 평가 가능 시간이1.5quarter인 작은 분모다. 아래 한 구간에서 기존1quarter 일치를 잃어 macro가 크게 내려간다. 작은 분모라고 삭제하거나0을 unknown으로 바꾸지 않는다. K283-1은 원 참조 adapter에서 이 성분의 평가 가능한 분모가 없어 양쪽 `null`이며, 주석/악보 전체가 없다는 뜻도 자동0점이라는 뜻도 아니다.

## 4. 원음표 연결 사례

단계71의61사례/58고유 exact range를 모두 이어 저장했다. 이번 변경21record가 그 목록 안에 있어 새 case 수를 더하지 않는다. 각 file에는 두 ordinary 경로와 source receipts, 참조 witness(존재할 때), 기존 case의 SHA-bound 경로, 원 XML/IR·원 note/sound IDs·전후 문맥이 연결된다. 아래 비용은 모두 **같은 새 고정 가중치** 아래 초기 선택 경로와 새 선택 경로의 비교다. Source/support/availability는 원대로 보존하고 인간 재승인 정답으로 기록하지 않는다. 범위는 exact global quarter의 `[start,end)`다.

### 4.1 Corelli op01n05c `[50,54)` — 교체 지점과 F삼화음 개선

Sample `cont_74ea0855a9436cd08d1b`. 초기 C/E/G `[50,103/2)` → D/F/A/C `[103/2,54)`에서, C/E/G `[50,52)` → F/A/C `[52,54)`로 바뀌어 참조 전체를 맞혔다(+5/2quarter). [두 경로·원음표 비용 사례](../../../output/harmony-online-score-dev-2026-10-05-r1/cases/09867e47711cff22d6d9.json.gz).

새 계수 아래 초기 경로 `20618957/78000000`(약.264346) 대 새 `29236171/130000000`(약.224894)다. 구성음 복잡도 감소−.103955가 missing member 증가+.047535 및 nonmember 증가+.016783 등을 상쇄한다. 원 후보에 존재하는 F삼화음과52시점이 실제 선택된 것이며 전역7화음 배제 규칙은 아니다.

### 4.2 Corelli op01n05c `[55,56)` — 거짓 화음 교체를 없앰

Sample `cont_a2dc7ad844e2efd469d0`. 초기 E/G/B → E/G/B/D → C/E/G에서 전 구간 C/E/G로 바뀌어 참조 전체를 맞혔다(+3/4quarter). [두 경로·원음표 비용 사례](../../../output/harmony-online-score-dev-2026-10-05-r1/cases/43984eca2bd701128390.json.gz).

새 계수 비용 초기 `51507031/240000000`(약.214613) 대 새 `1173271/8000000`(.146658875)다. 비구성음 비용+.109088·lowest+.040389·늦은 근음+.031670은 늘지만 missing/복잡도/교체/run 비용 절감과 기존 조건부 순차 장식 근거−.0636885가 이를 상쇄한다. 단순 병합 금지는 이 개선을 막으므로, 유지와 실제 교체를 같은 비용 아래 비교해야 한다. NCT 유형을 새로 확정하거나 원음표를 삭제하지 않았다.

### 4.3 Beethoven Sonata07-2 `[15/2,10)` — 맞던 감7화음의 근음/구성음 소실

Sample `cont_eb5de0924f8f9cf17c1b`. 초기 C♯/E/G/B♭ → G/B♭/D → C♯/E/G/B♭의 참조 일치에서 첫 `[15/2,17/2)`만 E/G/B♭로 바뀌어1quarter와 전체 정답을 잃었다. [두 경로·원음표 비용 사례](../../../output/harmony-online-score-dev-2026-10-05-r1/cases/aa182a8793a3fa933cbe.json.gz).

새 계수 비용 초기 `4173611/12500000`(.33388888) 대 새 `8162543/25000000`(.32650172)다. Nonmember+.06981632·metric+.01307792보다 구성음 복잡도−.0665312·조표외 구성음−.0113923·근음 이동/turnover 절감이 조금 더 크다. `conditional_step_ornament_exposure`는 양쪽 available가 아니며 accumulator0을 관측된 NCT 부재로 읽지 않는다. 임시표/감7의 실제 진행을 더 잘 설명할 필요가 있지만 Dev에서7화음 강제/계수 재조정은 하지 않는다.

### 4.4 Beethoven Sonata09-2 `[69/2,36)` — 실제 D♯감7 진행의 교체를 늦춤

Sample `cont_df5ed708102ebec7500b`. 초기 A/C/E `[69/2,35)` → D♯/F♯/A/C `[35,36)`에서 새 A/C/E `[69/2,71/2)` → F♯/A/C `[71/2,36)`로 바뀌었다. 참조는 F♯/A/C `[69/2,35)` → D♯/F♯/A/C `[35,36)`라 초기도 전체 오답이었지만 뒤1quarter는 맞았다. 새 선택은 그1quarter 일치를 잃었다. [두 경로·원음표 비용 사례](../../../output/harmony-online-score-dev-2026-10-05-r1/cases/14badef09599c34f77e6.json.gz).

새 계수 비용 초기 `2043919/10000000`(.2043919) 대 새 `6009557/30000000`(약.200319)다. 비구성음+.116361·metric+.021797 증가보다 구성음 복잡도−.110885·조표외 구성음−.018987·전이 절감이 크다. 3음/7음의 역할·전후 지지와 경제적인 작은 음 집합 사이의 오판이다. 특정 작품의D♯를 반드시 넣는 규칙으로 해결하지 않는다.

다음은 단계72 Train 반례에서 이미 결정한 **Train-only loss-augmented 경쟁 탐색**이다. Ordinary 승자가 아직 맞아도 손실을 가진 가까운 오답을 학습 대조로 드러내고, 같은 completed-run/전이 점수와 원 cap 아래 작은 DAG 전수 탐색으로 검증한다. 이 Dev 결과를 보고 계수나 epoch를 재설정하지 않으며, 다음 모델의 독립 Test/공개 모델 비교 및 source/후보 부재 문제도 여전히 남는다.

## 5. 사후 감사·보존·정본

사후 감사 **PASS/exit0**: 3,614고유SHA·14전체 source/원44,204edge 복원·72봉인 예측 packet·126독립 승자 비용·192case receipt 비용·61사례/두 arm 지표 재생을 확인했다. 모델 fit/새 decoder 탐색은 감사에서 실행하지 않았다. Stage72 모델 SHA는 그대로 `029e2de31ab6e5d9e5fa65eb229c63fe649cce10ddd987dbab4c2b7f3f06f331`이며 학습 가중치/원 code를 변경하지 않았다.

정본:

- [결과 report.json](../../../output/harmony-online-score-dev-2026-10-05-r1/report.json), SHA `9bdd36259ed5dad8ab5edd34786a6adeb54c0a956a26bb37f79e2f2bf60f8443`.
- [사전 run-contract.json](../../../output/harmony-online-score-dev-2026-10-05-r1/run-contract.json), SHA `23915c3b9bd2a2418c6a3b0fe631a3fdaeb537e4c4f7b7f4d1c5c3f4b5d46b47`.
- [참조 개방 전 prediction-freeze.json](../../../output/harmony-online-score-dev-2026-10-05-r1/prediction-freeze.json), SHA `999aa6b02dbf4505fed277a9b1d6d45fab00b2048db8ca21c4e8e577b4f0b434`.
- [사후 감사](../../../output/harmony-online-score-dev-2026-10-05-r1/post-seal-audit.json), SHA `a32167145f04217d5aba2b71212500deb46f19c897636bb7a047698de170809e`; 감사 code SHA `2d87f1e82bad69dfbb0ad5a7bf10c4adcb3a12629cf52a933dcddc0dd1f55d2d`.

Actual/검사/감사는 실패0이다. 사후 단발 조회는 `PYTHONPATH`를 설정하지 않아1회 import 실패했고 환경을 명시해 다시 조회했다. QA의 ceiling 조회는 Train의 `reachable` 필드를 Dev에 가정하여1회 KeyError가 났고, 원 Dev schema의 `lattice_hit` 필드로 다시 확인했다. 과도한 receipt 출력의 잘림은 요약 조회로 교정했으며 원 artifact/code를 수정하지 않았다. 중간 progress의 `complete=false`와 완료 report의 `complete=true`를 구별한다. 문서 초안의 다른 언어 잔여 표현은 한국어로 교정했다.

UI/서버/Core/원주석/MusicSearch/Composition/Claude Phrase·Motif/별개 dirty/Git는 유지했다. API/운영 승격/merge/commit/push0이다. 개발 기록·선택/원음표 사례와 검사 정본만 추가했다.

## 6. 재현

출력 덮어쓰기를 거부한다. 최초 r1의 완성/실패 여부와 무관하게 다음 재실행은 새 r2 경로를 사용한다.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_online_score_dev.py --prior-validation output/harmony-online-score-validation-2026-10-05-r1.json --output output/harmony-online-score-dev-validation-2026-10-05-r2.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_online_score_dev_trial --output output/harmony-online-score-dev-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/audit_harmony_online_score_dev.py --root output/harmony-online-score-dev-2026-10-05-r2
```
