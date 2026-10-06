# 단계71 — 기존 전체 음악 점수의 Train 전용 학습

## 1. 목적과 이번 범위

단계70에서 현재 선택기의 64오류 구간/13작품군·65고유 대조를 확보했다. 추가 다섯 특징이 모두 관측된41개 중21개는 delta0였지만, 기존 raw/metric/lowest nonmember·장식 근거·화음 복잡도까지 모두 같은 것은 아니었다. 이번에는 **기존 전체 점수의 균형**을 학습한다. 새 화음 어휘·음표 삭제·확정 NCT·작품/마디별 예외를 추가하지 않는다.

이 작업은 전체 비화성음 분석 완료나 생성기 구현이 아니다. 고전 화성의 joint 선택기 개선을 계속하며 재즈 전용 프로파일은 별도 미완료다. 원 XML/IR·주석·운영UI·MusicSearch/Claude/Composition·별개 dirty·Git를 보존한다.

## 2. 특징과 학습 계약

- 원 completed harmonic run·원 transition·기능적 pair·기존 다섯 지지 특징을 **26차원**으로 노출한다. Raw 비구성음·박절·최저음·조건부 경과/보조·구성음 누락·넓은 화음의 복잡도·근음 지연·의미 경계·조건부 기능 해결을 함께 비교한다.
- Blocker와 unresolved spelling의2계수는 원 값에 고정한다. 나머지24계수는 학습 가능하다. 비용은 `[0,2]`, 조건부 장식/기능 credit은 `[-2,0]`, run count는 `[1/10000,1/4]`로 부호/범위를 사전 고정한다. 짧은 화음·생략음·분산형을 금지하지 않는다. Run의 양성 비용 하한은 과분할을 무한히 보상하지 않기 위한 선택 점수 계약이지 음악적 최소 길이가 아니다.
- 시작점은 단계67 고정4계수 + 단계69 timing `.248879`이며, 나머지는 당시 기존 점수다. 초기 전체 벡터의 exact 비용과 winner가 단계69와 같아야 한다. 미채택 단계68 recipe는 쓰지 않는다.
- Stage70 ordinary current-winner65대조를 고정하여5epoch capped passive-aggressive update, step cap `1/10`,6자리 계수 quantization와 평균을 사용한다. 매 epoch 같은 pool이며 loss-augmented/online adversary 재탐색은 아니다. 개발 평가를 보고 epoch/계수/bounds를 고르지 않는다.
- `None`은 관측0이 아니다. 원 점수는 unavailable 부분의 항을 생략했고 이번에도 같다. 벡터에는 실제 관측된 합과 availability를 별도로 저장한다. **양쪽 경로에서 모두 계산 가능한 차원만 gradient를 낸다.** 다른 unavailable 차원이 변경된 계수 때문에 받는 영향까지 실제 예측/평가에서 확인한다. 이 방식을 완전한 missing-data 모델로 주장하지 않는다.
- 단, 알려진 음높이의 run에 비구성음이 전혀 없으면 비구성음에 조건부로 부여하는 장식 exposure의 대상 집합은 비어 있으므로0임을 증명할 수 있다. 이 경우만 기존 unassessed 값을 알려진0으로 표시한다. 음악적 장식이 없다거나 성부/NCT를 확정했다는 뜻이 아니며 비용은 기존 `None` 생략과 동일하다. 비구성음/미해결 음높이가 있으면 이 예외를 쓰지 않는다.
- 학습 target은 원 DCML 비교 주석에 맞는 경로이며 인간이 재승인한 정답이 아니다. 원 라이선스/승인 범위의 **NC 로컬 연구**로만 fit하며 모델·자료를 운영/상업/API/재배포용으로 승격하지 않는다.

## 3. 데이터·선택·평가의 분리

Stage70 report/pool/audit SHA와 기존 원 자료·code/artifact를 확인하고65대조의 전체 특징·loss·원 graph·target 호환성을 재계산한다. 전체 원악보는 보존된 source/IR SHA 참조로 연결하고 scope/원 note/sound IDs·비용·availability·근거를 저장한다. Parent JSON에 이미 노출된 Dev가 포함돼 있어 ‘어떤 Dev도 읽은 적 없음’이라는 방화벽을 주장하지 않는다. 현재 Dev를 fit에 쓰지는 않는다.

모델을 저장하고 SHA로 고정한 뒤, 기존 원63graph/72개 Dev 범위를 두 arm으로 새로 공동 선택한다. 초기 점수 arm은 단계69 timing winner/비용과 정확히 같아야 한다. 원 grid·edge/cap/2M 연산을 유지하고 이전9개 보류를 retry하거나 분모에서 숨기지 않는다. 모든 예측 packet을 봉인한 후 이번 reference report를 읽어 공통 평가를 수행한다. **이미 노출된 개발 자료이지 독립 Test 정확도가 아니다.**

기존31case를 유지하고 모든 새 변경을 원 source·두 조건의 특징별 비용·사후 oracle witness로 저장한다. Witness는 추론에 넣지 않으며 원 보류/부분 주석·ceiling·coverage·퇴행을 함께 보고한다. 새 weight로 정답 후보 부재75개가 해결됐다고 주장하지 않는다.

## 4. 구현과 검증

[전체 점수](../../../src/musicanote_harness/harmony_full_score.py), [학습](../../../src/musicanote_harness/harmony_full_score_learning.py), [Train 재계산](../../../src/musicanote_harness/harmony_full_score_training.py), [Dev 비교](../../../src/musicanote_harness/harmony_full_score_trial.py)를 새 파일로 추가했다. 기존 module globals와 sealed code는 바꾸지 않고 private binding으로 같은 exact decoder/reconstruction을 재사용한다.

[점수 검사](../../../tests/test_harmony_full_score.py), [학습 관문 검사](../../../tests/test_harmony_full_score_learning.py), [실행 계약 검사](../../../tests/test_harmony_full_score_trial.py)는 초기 비용/경로 일치·작은 DAG 전수 탐색·run 분할 불변·unknown/empty domain 구별·원 source/global 불변·고정/부호/bounds·Dev/권리/변조 거부를 검사한다. [관련 회귀 실행](../../../scripts/validate_harmony_full_score.py), [원자료/fit/비용/지표 사후 재생](../../../scripts/audit_harmony_full_score.py)도 추가했다.

신규20검사 PASS(1.336초), 신규20 + 이전 관련666 = **686검사/56모듈 PASS**, failure/error0·66.932초다. Repository 전체 suite는 아니다. 신규9개 Python 파일의 AST/strict UTF-8도 통과했다. [회귀 정본](../../../output/harmony-full-score-validation-2026-10-05-r1.json), SHA `535e30540a2b91ea831c28c11dc5f4d12d5b4d7aa33a39881349cb8ada09e0bb`.

첫 신규14검사와 추가6검사에서 failure/error는 없었다. 파일 탐색 중 예상했던 옛 모듈명 두 개가 실제 이름과 달라 경로 조회는 실패했지만, 존재하는 scoring/decode 모듈을 확인해 연결했다. 이를 parser/음악 규칙 실패로 세지 않는다. Actual 시작 후 code/test/script를 수정하지 않았다. 실제 실행·수치·채택 결정은 아래에 기록한다. 테스트 통과 자체를 화성 정확도 향상이라고 읽지 않는다.

## 5. Train 실제 결과

Stage70의65대조를 빠짐없이 재계산했다. **64범위·19전체 악장 패키지·13명명 작품군·원37,242edge**다. Stage70 전체270범위/27패키지와, 그 안에서 실제 선택 오류 대조가 있던 이번 학습 범위를 구별한다. 전체26차원에서 양쪽 관측 가능한 trainable delta가 전부0인 대조는0개다. 추가5차원 충돌21개가 해결된 새 분석 결과라는 뜻이 아니라, 기존 전체 점수에 학습할 차이가 있음을 확인했다는 뜻이다.

다음 수는 서로 겹치는 대조 수다. Raw nonmember45·metric46·lowest20·conditional ornament7·복잡도44·member turnover46·run count37개에 관측 가능한 차이가 있다. Conditional ornament는50/65에서 양쪽 available이며 나머지15는 gradient에서 제외한다. 역할/timing은41/65에서 available, timing 차이는 여전히1개다. 원 경과/보조의 제한된 근거만 사용했으며 전체NCT/국소조성을 새로 알아낸 것은 아니다.

5epoch update 수는54/40/36/37/37(합204), margin satisfied는10/24/28/27/27, bounded no change는각1이다. 평균 모델의 같은65대조 positive margin 합은 **70.010849→32.642504**, 악화한 대조도12개다. 이는 고정된 Train 경쟁 경로에서의 비용 분리이며 정확도나 독립 개선률이 아니다. 매 epoch 새 competitor를 찾지 않아 선택 편향이 남는다.

원 nonmember 계수1→`.272089`, extra-member complexity `.1→1.200644`, metric `.25→.018101`, lowest `.25→.014400`, conditional ornament `-.5→-.560928`, member turnover `.02→.563377`, run count `.015→.103682`로 바뀌었다. 고정된 두 계수는 그대로다. 누락/넓은 음집합/과분할의 이전 비용 균형이 크게 이동했으므로 기존7화음·기능적 해결·새 competitor의 퇴행 가능성을 Dev에서 확인한다. 임시 학습 수치만으로 운영에 넣지 않는다. 전체 계수와 epoch/개별 update는 실행의 `model.json`에 보존한다.

Train13명명 작품군과 Dev9작품군의 교집합은0이다. 전체 중복/편곡·악장 계보 감사는 수행하지 않았고, 이미 노출된 Dev를 독립 Test로 주장하지 않는다. 아래 개발 평가의 결과를 본 뒤 모델을 재학습하거나 계수/epoch를 바꾸지 않았다.

## 6. Dev 실제 결과 — 큰 퇴행으로 미채택

Actual r1은 **272.690초/exit0**, Train 재계산·fit은101.004초다. 모델 고정 후 원63graph/44,204edge·72범위를 두 arm으로 선택하고 예측을 봉인했다. 두 arm의 선택+독립 비용 검산은64.633/38.476초이며 한 번의 관측이다. 새 arm은 화음 run을 크게 줄였으므로 속도 향상으로 일반화하지 않는다.

| 공통 개발 평가 지표 | 초기 전체 점수(단계69 재생) | 학습 전체 점수 |
|---|---:|---:|
| 완전 평가 범위의 전체 일치 | 16/51 (31.3725%) | 5/51 (9.8039%) |
| 근음+철자 구성음의 시간 일치 | 28.8915% | 11.8320% |
| 위 시간 일치의 작품군 macro | 53.1500% | 12.8163% |
| 근음만의 시간 일치 | 35.5309% | 21.6336% |
| 정확 의미 경계 TP/FP/FN | 47/23/16 | 0/0/63 |
| 정확 의미 경계 F1 | 70.6767% | 0% |

분모는 원72범위/14전체 악장 source package/9명명 작품군이다. 선택63·보류9, 완전 평가51·부분21, 근음/구성음 prediction coverage43.7106%는 두 arm 모두 같다. 기존 후보 ceiling36/51도 유지되며 새 후보 생성은 없다. 원 보류는 source preflight6·bounded plan1·stream operation budget2를 그대로 유지한다. 부분 주석/미지원 projection·보류를 숨기지 않았고, whole Roman/전위/국소 조성/전체 NCT 정확도는 측정하지 않았다. 평가 시간은 겹치는 문맥을 포함하므로 고유 작품의 전체 길이가 아니다.

변경58record/56고유 exact range 중 시간 개선10·퇴행32·무변화16이다. 완전 평가에서 이전 전체 정답15개를 잃고4개를 새로 맞혔다. 초기 선택63범위의 의미 run 수 분포는1개11·2개20·3개28·4개3·5개1이었으나, **학습 후63범위 모두 의미상 한 화음 run**이 됐다. Raw edge는119개 남지만 같은 signature 조각이므로119개 화음이 아니다. 학습 arm의 raw 선택119개는 모두 구성음3개이며, 기능적6-4 후보도 포함되어 ordinary 삼화음만 선택됐다는 뜻은 아니다.

**결정: 이 학습 가중치는 기각하고 운영/화면에 적용하지 않는다.** Train 고정 대조의 margin 감소와 실제 선택 정확도는 다르다. 원 계산/학습·후보망·봉인 자료는 실패 실험으로 보존한다. 기존 화면 엔진·원 IR·Claude Phrase/Motif·주석/피드백·서버·Git는 바꾸지 않았다.

## 7. 원음표 연결 사례와 비용 진단

다음 비용은 모두 **같은 새 학습 계수로 계산한 초기 선택 경로 대 새 선택 경로**다. 다른 계수의 비용을 직접 비교한 것이 아니다. Quarter 구간은 원 global clock의 `[start,end)`이고, 전체 XML/IR SHA와 note/sound ID·앞뒤 source 문맥·경로/특징/availability·항별 비용·사후 주석 witness를 각 case에 보존했다. 인간 승인 상태는 false다. 아래는 사용자 정답을 새로 확정한 것이 아니라 기존 비교 주석과 선택의 차이를 설명하는 진단이다.

### 7.1 베토벤 소나타07-2 — 맞던 진행을 한 화음으로 병합

[사례 fe9b0e1f69963fe907c1](../../../output/harmony-full-score-2026-10-05-r1/cases/fe9b0e1f69963fe907c1.json.gz), sample `cont_f3c7cdac22d1e8650885`, `[105,109)`.

초기 경로는 G/B♭/D `[105,108)` → G♯/B/D/F `[108,108.5)` → E/G♯/B/D `[108.5,109)`였고 전체 참조에 일치했다. 새 경로는 D/F/A를 전 구간에 붙였다. 새 계수 아래 비용은 기존 경로 `5166211261/3720000000`(약1.388766) 대 새 경로 `8130951/15500000`(약0.524577)다.

새 경로−기존 경로에서 member turnover 비용은−0.694832, 넓은 구성음 복잡도는−0.300161, run count는−0.207364, 근음 이동은−0.061820이다. 반대로 nonmember 비용은+0.164570, durable nonmember는+0.116895, 늦은 식별음은+0.098435, metric/lowest는+0.012992/+0.014400이다. 실제 화음 교체를 제거하는 절감이 틀린 비구성음 설명의 비용보다 커져 병합했다. 음표 유실이나 후보 부재로 진단하지 않는다.

### 7.2 쇼팽 BI145-2 op50-2 — 7화음의 실제 근음을 지움

[사례 3e987ee8bfece8435be5](../../../output/harmony-full-score-2026-10-05-r1/cases/3e987ee8bfece8435be5.json.gz), sample `cont_1f300d84b87bfc76ff30`, `[28,61/2)`.

초기 E♭/G/B♭/D♭ 한 화음 대신 G/B♭/D♭가 전 구간을 차지했다. 새 계수 비용은 기존 `182795579/140000000`(약1.305683), 새 `28593107/140000000`(약0.204236)이다. 구성음 하나를 줄이면 복잡도 비용1.200644가 절감되고, 새 nonmember·lowest·metric·지연음 비용 증가는 이를 상쇄하지 못한다. 실제로 지속된 근음을 구성음에서 빼는 편향이며 모든 음을 NCT로 확정한 것은 아니다.

### 7.3 코렐리 op01n05a — 넓은 병합과 기능 역할의 미확정

[사례 f9c857091098f6748d8d](../../../output/harmony-full-score-2026-10-05-r1/cases/f9c857091098f6748d8d.json.gz), sample `cont_492fa0156728b85798a5`, `[120,132)`. 초기 D/A/F♯ `[120,126)` → G/B♭/D `[126,128)` → G/B/C/D/F `[128,132)`에서 새 경로는 analysis root D·구성음 G/B♭/D·`dominant_origin_six_four` 역할을 전 구간에 붙였다. 이 역할은 **미확정**이며 해결된 도미넌트/종지로 승격하지 않는다. 시간 일치8quarter를 잃었다.

새 계수 비용은 기존 `3040039501/1440000000`(약2.111139) 대 새 `16297571/48000000`(약0.339533). Turnover−0.826286·복잡도−0.800429·run count−0.207364의 절감이 durable+0.125824·nonmember+0.056685·기능 복잡도+0.020955를 압도한다. 관측 구성음 지지·기능 후보와 ordinary 후보의 비교 가능성도 남는 과제다.

### 7.4 같은 비용이 실제 과분할을 줄인 개선도 있음

[사례 ab54a219fb8e3a01e987](../../../output/harmony-full-score-2026-10-05-r1/cases/ab54a219fb8e3a01e987.json.gz), sample `cont_0dcaf64492bd12d76a0c`, Corelli `[123,126)`. 초기 D7 → B♭/D/F♯ 증삼화음 → D/A/F♯에서 새 D/A/F♯ 한 화음이 참조와 전체 일치하며2quarter를 회복했다. 새 계수 비용은 기존 `11303909/7500000`(약1.507188) 대 새 `5546059/24000000`(약0.231086). Turnover−0.619715·복잡도−0.400215·run count−0.207364·근음 이동−0.098912가 효과를 냈다. 따라서 병합/삼화음을 전역 금지하는 보정은 하지 않는다. 같은 벌점이 거짓 교체를 없애는 조건과 진짜 진행을 지우는 조건을 학습 자료에서 함께 비교해야 한다.

Train Quartet01-4 sample `cont_05a973a926c1c81874af`의 `[2147/4,1075/2)` F/A/C/E 대 F/A/C 고정 대조는 새 계수로1.304326 대0.0543344가 되어 target이 싸졌다. 이것은 이전5특징 충돌의 비용 분리이지 새 decoder가 실제로 정답을 선택했다는 검증이 아니다. Post-fit Train 재탐색은 하지 않았다.

## 8. 감사·실패 기록·정본

사후 감사 **PASS/exit0**. 3,071고유 SHA,65Train 전체 벡터/fit 모델 재생,64Train범위/19source,72Dev packet/14source·원44,204edge round-trip,126독립 winner 비용,192원자료 case receipt 비용,61case 및 두 arm 지표를 재생했다. 감사 중 새 decoder 탐색은 하지 않았다. 실제 실행의 선택/재구성 비용과 신규 tiny DAG 전수 탐색 검사도 구별한다. 기존31case를 포함한61개에 원source/IR와 새 경로/사후 witness를 보존했다.

Post-run 조회에서 gzip IR을 일반 UTF-8 파일로 읽는 임시 진단 명령은 `UnicodeDecodeError`로 실패했다. gzip-aware source loader를 사용하는 계약을 확인했으며 원자료·실행·감사 결과는 수정하지 않았다. 이후 PowerShell 조회에서 보고서 `metrics`가 아니라 실제 `tables`를 읽어 수치를 재확인했다. 문서 첫 patch의 줄 context가 전체 문장과 달라 적용이 거부됐고 정확한 context로 다시 적용했다. 이들은 actual/audit 실패가 아니다. Progress의 마지막 `complete=false`는 중간 checkpoint이고, 종료 정본 report의 `complete=true`/exit0가 완료 판정이다.

정본은 [출력 디렉터리](../../../output/harmony-full-score-2026-10-05-r1)다.

| 파일 | SHA256 |
|---|---|
| [report.json](../../../output/harmony-full-score-2026-10-05-r1/report.json) | `3269a812a414d9e59babae34a090aa84ed91c0fbcbf7c244c79f6d1838d57e53` |
| [model.json](../../../output/harmony-full-score-2026-10-05-r1/model.json) | `f55d2af20464aa5a8e6614e6a591b1bb35cb6105eaaa08ff533bcbe21e5151ca` |
| [training-vectors.json.gz](../../../output/harmony-full-score-2026-10-05-r1/training-vectors.json.gz) | `9b6e232319413d75a30dcef2c3cc9f6da8fb146f706f6052b69470300f25774c` |
| [run-contract.json](../../../output/harmony-full-score-2026-10-05-r1/run-contract.json) | `26907ca09d943b868ac02df2d1da4a1710a02dca5aafdd11679ec82a06b1eedd` |
| [prediction-freeze.json](../../../output/harmony-full-score-2026-10-05-r1/prediction-freeze.json) | `e644b6f7c3b784e4568c7e0d8963d3d6abe09e46d2ea2e54658ed1676d6acdce` |
| [post-seal-audit.json](../../../output/harmony-full-score-2026-10-05-r1/post-seal-audit.json) | `47c2309bf4fa3957d432ab1f9b2461ab86c4dd64c778d357349037f683dfda25` |

## 9. 해석과 다음 큰 개발 단계

현재 pool은 이전 선택 오류만65대조를 모았고, 원118개 reference-compatible Train 범위 중 **이전에 맞던54범위의 경쟁 오답을 막는 자료**가 빠져 있다. 고정5epoch 동안 새 점수로 부상하는 더 싼 오답도 다시 찾지 않았다. 수치와 항별 비용은 화음 교체/넓은 구성음 비용이 비구성음 비용을 압도하는 편향을 보여 준다. 선택 편향·고정 negative·전역 선형 점수의 조건 표현 부족이 원인일 가능성이 크지만, 어떤 요소가 얼마나 기여했는지는 별도 Train ablation 전에는 확정하지 않는다.

다음은 작은 계수/Dev 보정이 아니라 **Train 자료의 보호 대조와 현재 모델의 경쟁 경로 갱신**이다.

1. Reference-compatible118Train범위 전체에서 이전 정답도 포함하고, 현재 계수의 ordinary 또는 loss-augmented competitor를 매 학습 주기에 새로 찾는다. Target와 negative가 같으면 근거 없이 임의 정답/오답을 삽입하지 않는다. 미지원/후보 부재75·부분/보류는 그대로 구별한다.
2. 초기 점수에서 크게 벗어나지 않는 prior/trust-region/regularization 계약과, 관측·박절·최저음 대비 화음 복잡도/교체 비용의 균형을 Train에서만 정한다. 사전 범위·조건·비용을 고정하고 동일 원 후보망으로 독립 비용을 검산한다. 특정 악보/마디별 금지·7화음 강제·Dev sweep은 하지 않는다.
3. 학습 후 Train ordinary 선택을 실제 재계산해 margin 감소와 정답 선택을 분리한다. 모델/SHA 고정 후 현재 Dev는 퇴행 점검에만 쓰고, 독립 작품군 Test와 공개 모델의 공통 평가를 별도로 준비한다. 아직 independent Test/전체 Roman·국소조성·NCT/생성 성과를 주장하지 않는다.

이번 단계에서는 다음 모델을 추가로 fit하지 않았다. 실패를 기록하지 않은 채 UI에 연결하거나, 테스트 수/개발 로그 번호를 전체 완성률로 보고하지 않는다. 마감 시 이 기록·메인 문서·개발 로그의 strict UTF-8/치환 문자/로컬 링크 검사(누락0), 종료6개 정본 SHA·봉인 code SHA 재확인, `git diff --check`를 통과했다. 기존5개 tracked dirty의 목록은 같고 기존 LF/CRLF 경고는 남아 있다.

## 10. 재현

기존 출력 덮어쓰기를 거부한다. 새 이름을 사용한다.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_full_score.py --prior-validation output/harmony-fresh-train-validation-2026-10-05-r1.json --output output/harmony-full-score-validation-2026-10-05-r2.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_full_score_trial --source output/harmony-member-timing-2026-10-05-r1 --output output/harmony-full-score-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/audit_harmony_full_score.py --root output/harmony-full-score-2026-10-05-r2
```
