# 단계67 — 구성음 지지와 지속 비구성음의 Train 전용 점수 균형

## 1. 목적과 결론

이론의 큰 개념/후보 목록이 만들어졌다는 것과 그 이론이 실제 선택기의 점수로 작동한다는 것은 다르다. 이번 작업은 단순 검증이 아니라 **네 가지 관측 특징의 구현 → 학습용 대조에서 추가 계수 결정 → 구간/화음 공동 선택 → 개발 자료 비교**다. NCT 전체 분류, 국소 조성/Roman/전위/종지 선택과 운영 승격은 완료되지 않았다.

결론은 **혼합된 결과/운영 미채택**이다. 근음+철자 구성음의 시간 일치는 27.0012%→28.3314%로 늘었지만, 정확 경계 F1은 73.6842%→71.2121%로 낮아졌다. 완전 일치 구간 수는 16/51로 같다. 개선 사례만 선택하여 새 계수를 채택하지 않았다. 같은 기존 후보망과 원음표를 보존하며 이전 실패 사례도 모두 이어 저장했다.

## 2. 새 관측 특징 — 해석 라벨이 아니다

| 특징 | 계산/의미 | 계산하지 않는 것 |
|---|---|---|
| `absent_third_exposure` | 선택한 tertian template의 철자 3음이 해당 완전 harmonic run에 실제로 없으면 run 폭/context 폭 | 3음 생략 금지, 실제 없는 음표 생성 |
| `absent_altered_fifth_exposure` | 감/증5음이 같은 방식으로 미관측일 때의 노출 | 완전5음에 추가 벌점, enharmonic 합치기 |
| `absent_seventh_exposure` | 7화음 후보의 7음이 미관측일 때의 노출. 3음과 평균하지 않는다 | 3화음을 반드시 7화음으로 확장 |
| `durable_nonmember_exposure` | 원 sounding duration이 원 onset의 박자 단위 이상인 비구성음의 **실제 run 교집합 시간 합 / context의 전체 note exposure** | structural tone/NCT 확정, 짧은 음표 삭제 |

단순박자는 `4/denominator` quarter, 복합 6/8·9/8·12/8은 dotted-quarter를 단위로 삼는다. 붙임줄을 포함한 **전체 원 sounding duration**을 보며, 계산 범위에 들어오는 노출량만 센다. 작품/마디별 예외, 선율파트 강제 선정, float 시간 근사, 원음표 duration 수정은 없다.

Known tertian shape/철자/박자 근거가 없으면 특징은 `unavailable`이다. Applicability가 없는 triad의 seventh나 perfect fifth의 altered-fifth는 0이다. 둘을 구별한다. 동일 signature의 연속 raw edge는 완전 run으로 합쳐 계산하므로 후보망의 조각 수만으로 벌점이 커지지 않는다.

이 특징은 Analysis/Evidence의 재계산 가능한 연구 점수 입력이고 Canonical Core에 해석 필드를 넣지 않는다. 원 nonmember 비용·기존 조건부 NCT 가점·화음 전이/경계/근음 회귀 비용은 그대로다. 긴 음이 suspension/pedal 등일 수 있으며, 이번 지속 특징이 그것을 부정하거나 NCT로 확정하지 않는다.

## 3. 학습 계약과 범위

기존 J2f 기록의 549 update + 4 collision 기록에서 `(sample_id, negative_path, compatible_target_path)`가 같은 것을 중복 제거했다. **116구간/220대조**이며, **23악장 source package**를 읽었다. 출처 clock 관문 실패는 0이었고 특징 미지원 때문에 40대조를 제외하여 **104구간/180대조/15작품군**으로 학습했다. 31구간에서 일부 또는 전부 대조가 미지원이다. 후보 부재 구간을 이 학습이 새로 해결했다는 뜻은 아니다.

Train 작품군: Beethoven sonatas 01·02·03, quartet n01op18-1, Mozart K280·K281, Corelli op01n02·op01n03, Chopin BI105-2op30·BI105-4op30·BI115-1op33·BI115-4op33·BI122op41·BI126-1op41·BI126-3op41. 악장 수와 작품군 수, 구간/대조 수를 작품 수처럼 혼용하지 않는다.

모든 negative/target ID는 기존 Train 후보망의 완전 경로이고, target이 기존 reference cells와 compatible인지 다시 확인했다. 기존 loss를 독립 재계산하고 원 후보 inventory SHA/개수/points/raw cap와 원 IR·XML 출처를 대조했다. 학습을 위해 정답 후보를 추가하지 않았다.

**제한된 additive calibration이지 새로운 full structured training이 아니다.** 과거 학습 도중 기록된 negative 경로를 재사용하여 fresh loss-augmented adversary 탐색을 하지 않았다. Negative pool은 전 후보를 대표하지 않으며 이전 모델의 선택 편향이 있다. 기존 모든 계수는 고정하고 새 네 계수만 5 epoch, capped passive-aggressive(`tau≤1/10`), nonnegative `[0,1]`, 1e-6 rational quantization/평균으로 정했다. Dev를 보고 scale·epoch·checkpoint·bounds를 바꾸지 않았다.

경로 비용은 `기존 비용(path) + w·새 특징(path)`다. 대조의 `delta = phi(negative) - phi(compatible target)`와 원 비용 차이를 사용하여 `loss - 원 비용 차이 - w·delta`의 margin 부족분을 줄인다. 손실은 시간 오류 + 정확 경계 오류의 기존 `1/4` 가중치이며 target은 원 graph 안의 주석 compatible 경로다. 이것은 likelihood/확률이나 보편적 음악 이론의 숫자를 학습한 것이 아니다.

| 추가 계수 | 학습 후 값 |
|---|---:|
| 미관측 3음 | 0.885548 |
| 미관측 감/증5음 | 0.941206 |
| 미관측 7음 | 0.878012 |
| 지속 비구성음 | 0.824534 |

Train margin violation 합은 200.478855→149.754271, update496회다. 20대조의 margin은 악화됐고, 새 특징 벡터도 같은 collision28대조가 매 epoch 남았다. **이 수치는 음악적 정확도/성능 향상 비율이 아니다.**

기존 승인 use contract의 비상업적 로컬 연구 자격과 출처/라이선스 SHA를 검증했다. 상업 운영·외부 API 전송·checkpoint 재배포·production deployment는 미승인 상태다. 원 corpus/manifest의 자격을 바꾸지 않았다.

## 4. Dev 예측/봉인과 비교

원 63graph/44,204edge와 14전체 XML/IR를 SHA 참조로 재사용했다. Dev 후보 생성은 0회다. Train에서는 원 inventory를 재구성하여 동일성을 확인한 것이며 모든 과정에서 후보 생성 0회라고 보고하지 않는다.

새 model을 먼저 고정하고 72예측을 저장한 뒤 **이번 비교의 step66 reference report**를 열었다. 이전 Train 부모 report는 Train/Dev 행을 함께 가진 JSON container여서 기존 Dev reference 행도 메모리에 로드된다. Train split·승인 entry만 학습 대조/특징/손실에 사용했고 Dev 행을 update·계수 선택·추론에 사용하지 않았다. `prediction-freeze`의 `labels_read/dev_labels_read=false`는 **이번 step66 평가 report를 아직 열지 않았다는 범위**다. 전체 이력에서 Dev 주석이 한 번도 읽히지 않았다는 뜻이 아니다. 이 실험은 이미 반복해서 본 **노출된 Dev 비교**이며 독립 blind Test가 아니다.

Train15작품군과 Dev9작품군의 named family ID 교집합은 0이다. 음악 내용/다른 판본을 포함한 전체 duplicate audit을 완료한 것은 아니다. 원9보류(연산2 + bounded/repeat1 + source6)를 재시도하거나 분모에서 제거하지 않았다. 완전 평가51/부분 평가21, 후보 ceiling36/51, 근음+구성음 예측 coverage43.7106%도 같다.

| 지표 | 기존 control | Train 추가 계수 |
|---|---:|---:|
| 선택/보류 | 63/9 | 63/9 |
| 완전 구간 일치 | 16/51 (31.3725%) | 16/51 (31.3725%) |
| 근음+철자 구성음 시간 일치 | 27.0012% | 28.3314% |
| 같은 지표 작품군 macro | 51.9033% | 52.8166% |
| 근음 시간 일치 | 35.1809% | 35.5309% |
| 정확 경계 TP/FP/FN | 49/21/14 | 47/22/16 |
| 정확 경계 F1 | 73.6842% | 71.2121% |

시간 일치는 지원 주석의 전체 eligible time을 분모로 하며, 보류/coverage 손실을 감추지 않는다. 근음+구성음 외 Roman·전위·local key·종지·전체 NCT 정확도를 측정한 결과가 아니다.

선택이 바뀐 **20record/18고유 exact range** 중 시간 일치 개선6/퇴행3/변화 없음11이다. 개선6개에는 동일 `[124,132)`의 두 record와 겹치는 다른 범위가 있어 독립6사례로 세지 않는다. 변경 경로와 이전18사례를 합쳐 29case를 저장했다. 각 case는 전체 원 MusicXML/IR 경로·SHA, 실제 원 note/sound IDs, 두 선택의 원 비용/추가 비용/새 특징/관측 근거, 사후 reference witness를 참조한다.

## 5. 실제 개선과 반례

- **Corelli op01n05a `[124,132)`**: `[126,132)` 전체를 G/B♭/D/F로 유지하던 경로 대신 `[126,128)` G/B♭/D와 뒤 음 집합을 구분해 주석 일치 시간이 2quarter 늘었다. 뒤 선택은 넓은 G/B/C/D/F 후보라 이 구간 전체의 의미를 정확히 이해했다고 보지 않는다. [동일 범위 대조](../../../output/harmony-support-balance-2026-10-05-r2/cases/e146c10d932bf1d6c977.json.gz).
- **Corelli op01n04a `[36,39)`**: 일치2→1quarter, `[37,39)`를 F/A/C/D/E♭/G라는 넓은 집합으로 합쳐 실제 경계를 놓쳤다. [퇴행과 source](../../../output/harmony-support-balance-2026-10-05-r2/cases/6a8ca6bf66e8cdc664fd.json.gz).
- **Corelli op01n04d `[73,76)`**: 일치1.5→0.5quarter, 원 C→F→G 대신 C→G/B/C/D/F로 합쳤다. [퇴행](../../../output/harmony-support-balance-2026-10-05-r2/cases/5858062670a337d1b0d6.json.gz).
- **Corelli op01n04c `[219/4,111/2)`**: 1/4quarter 퇴행도 포함했다. [case](../../../output/harmony-support-balance-2026-10-05-r2/cases/4b5f51164332a086b4cb.json.gz).
- **기존 미해결 Corelli op01n05c `[55,56)`**: 미관측 B♭를 쓴 E/G/B♭ 경로의 새 비용은 `.8716545`로 커지지만, 대신 미관측 완전5음 B를 허용한 E/G/B 계열 분리 경로 `.1886667`이 전체 C/E/G `.193125`를 계속 이긴다. 화음이 바뀌었을 뿐 정답 복원은 아니다. [원음·계수별 비용·witness](../../../output/harmony-support-balance-2026-10-05-r2/cases/43984eca2bd701128390.json.gz).
- **Chopin `[28,61/2)`**의 원 E♭7 해석은 비용 `.199642857`과 함께 유지했다. 앞 Sonata07-2의 Gminor→G♯dim7→E7 및 quartet B♭7 이전 개선도 기존 case를 통해 추적한다. [Chopin case](../../../output/harmony-support-balance-2026-10-05-r2/cases/3e987ee8bfece8435be5.json.gz).

새 role 특징을 계산할 수 없는 shape를 선택한 record는 control10→학습16개다. 특징 unavailable을 확정 관측0으로 표시하지 않았지만, 가용 특징만 합하는 점수는 **명칭/구성 역할 미지원 후보가 새 누락 비용을 피하는 비교 불균형**을 만들 수 있다. 넓은 음 집합을 정식 화음/NCT 설명으로 오인하지 않는다. 이 문제와 생략/분산/지연음/페달 설명을 고려하지 않은 지속 비용 때문에 계수만 높이는 개선은 불충분하다.

## 6. 구현과 검증/실패 이력

- [support scorer](../../../src/musicanote_harness/harmony_support_balance.py): 네 특징·박자 비례 원 지속음·원 run·직접/인덱스 계산·공동 DP/독립 비용.
- [Train 준비](../../../src/musicanote_harness/harmony_support_balance_training.py): 과거 대조 중복 제거, Train/승인/출처/후보/compatible target/loss 관문과 eligibility.
- [bounded learner](../../../src/musicanote_harness/harmony_support_balance_learning.py): 기존 계수 고정·추가4계수 학습·연구 model 소비 계약.
- [trial](../../../src/musicanote_harness/harmony_support_balance_trial.py): model 고정·72예측 봉인·기준선 불변·전체 평가·29case.
- [감사](../../../scripts/audit_harmony_support_balance.py), [회귀 실행](../../../scripts/validate_harmony_support_balance.py).
- 신규 [scorer](../../../tests/test_harmony_support_balance.py) 11 + [learner](../../../tests/test_harmony_support_balance_learning.py) 6 + [trial](../../../tests/test_harmony_support_balance_trial.py) 7 = **24검사**. Tiny DAG8개 전수 최소비용/lex tie, 모든 span의 직접/인덱스 값, meter/미지원/원악보 불변, Train-only·권한·봉인·출처/graph 변조 포함.
- 기존 관련580 + 신규24 = **604검사/45모듈 PASS**, failure/error0, 61.186초. 전체 repository suite는 아니다. 감사 확인 위장에 대한 추가 runtime fault check도 실행했으나 604개에 더하지 않았다.
- 첫 test 실행은 일반 `python` PATH가 없어 실패했다. 기존 `.venv/Scripts/python.exe`로 실행했다. 최초 16검사 중1error는 fixture에 없는 G7 조각을 요구한 검사 구성 문제로, 실제 기존 C 후보들의 같은-run 분할 대조로 수정했다.
- Actual r1은 Train2/116 처리 후 `index_missing_measure_boundary`로 중단했다. 과거 Train DAG가 현재 빠른 인덱스 요구인 모든 measure 시작점을 포함하지 않는 문제다. 원 graph에 point/후보를 추가하지 않고 **고정 Train 경로는 직접 원음표 계산**, Dev 공동 탐색은 검증된 원 인덱스를 사용하도록 분리했다. 실패 r1을 삭제/덮어쓰지 않았다. r1에는 model/Dev예측/report가 없다.
- Actual r2 완료/exit0, 325.364초(Train179.954초 포함). control/train arm 선택+검산 합은 38.932/35.828초다. 단일 실행이며 정식 속도 benchmark가 아니다.
- 사후 감사 PASS: **1,927고유SHA, Train180대조의 특징/compatible target/loss/원 비용, model fit 재생, 72×2조건 지표, 원44,204edge codec 왕복, 독립 승자 비용126개, 14전체 Dev source, 29case/witness**를 다시 확인했다. 새 Dev 추론은 재실행하지 않았으며 Train model fit은 감사에서 재생했다. 이 문서의 통과 검사 수를 음악적 정확도처럼 사용하지 않는다.
- 최종 문서/파일 검사: 새 변경12파일 strict UTF-8·replacement character0·trailing whitespace0, 메인/로그/이번 기록의 로컬 링크276개·누락0. 문서 교정 과정의 한 patch context 불일치는 원문을 다시 읽어 적용했고, 우발적인 혼합 언어 문구도 제거했다. 문서 갱신 후 봉인1,927SHA가 그대로이며 `git diff --check` exit0이다. 기존 tracked dirty5개의 LF→CRLF 경고는 기존 상태로 남아 있다.

## 7. 산출물과 재현

정본: [report](../../../output/harmony-support-balance-2026-10-05-r2/report.json), [model](../../../output/harmony-support-balance-2026-10-05-r2/model.json), [Train 대조/eligibility](../../../output/harmony-support-balance-2026-10-05-r2/training-contrasts.json.gz), [run contract](../../../output/harmony-support-balance-2026-10-05-r2/run-contract.json), [예측 봉인](../../../output/harmony-support-balance-2026-10-05-r2/prediction-freeze.json), [사후 감사](../../../output/harmony-support-balance-2026-10-05-r2/post-seal-audit.json), [회귀 검사](../../../output/harmony-support-balance-2026-10-05-r2/test-validation.json).

Report SHA `8039377b21f798a4b60077eabe7a636d5bcbf00bf5c233ad51dddd627247abee`.
Model SHA `de9fe82781d107d443999b2c3f1e769f002d2077e0e8c20aa0b6bb796ddca896`.
Train dataset byte SHA `80bee43d72c459959461ee17221924f4e1364681836ea47bea490574968d7966`.

원 output을 덮어쓰지 않는 재현:

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_support_balance_trial --source output/harmony-joint-nct-2026-10-05-r1 --output output/harmony-support-balance-2026-10-05-r3
.\.venv\Scripts\python.exe -B scripts/audit_harmony_support_balance.py --root output/harmony-support-balance-2026-10-05-r3
.\.venv\Scripts\python.exe -B scripts/validate_harmony_support_balance.py --prior-validation output/harmony-joint-nct-2026-10-05-r1/test-validation.json --output output/harmony-support-balance-2026-10-05-r3/test-validation.json
```

## 8. 다음 큰 단위와 채택 결정

1. **후보 설명과 점수의 비교 가능성**: 실제로 관측한 화음 구성음·분산/생략 근거와 아직 화음 역할을 해석하지 못하는 음 집합을 구별한다. 미지원 특징을 사실0/확정 NCT로 처리하지 않으며, 넓은 후보를 특정 작품 때문에 금지하지 않는다.
2. **화음 유지/교체와 지속 비구성음의 공동 설명**: 긴 비구성음을 무조건 다음 화음 근거로 보지 않고 실제 성부/준비/해결/베이스 회귀·지연음/페달 등 설명과 경쟁시킨다. 누락 벌점만 더 올리는 Dev 보정은 하지 않는다.
3. 필요한 source 특징이 준비되면 새로운 Train-only adversary 탐색으로 현재 모델이 놓치는 경로도 학습 대조에 포함하고, 별도 frozen/비중복 작품군에서 큰 오류와 coverage/퇴행을 평가한다. Full Roman·전위·local key·종지와 공개 모델 공통 비교는 별도 미완료 항목이다.

기존 Core/주석/운영 UI/서버/MusicSearch/Composition/Claude Motif/별개 dirty/Git는 수정하지 않았다. 이번 점수는 비상업적 로컬 연구 전용이며 운영 승격·API 호출·merge·commit·push는 없다. 기존 화면 엔진의 결과는 그대로다.

현재 상태는 [메인 개발 문서](../README.md), 단계별 변화/결정은 [개발 로그](../DEVELOPMENT_LOG.md)에 연결한다.
