# 단계76 — 고정 손실 경쟁 모델의 Dev 비교와 미채택

## 1. 결과와 결정

**단계75의 새 모델은 단계72 모델보다 Dev 성능이 퇴행했다. 운영에 적용하지 않는다.** Train의 일부 경계 개선이 다른 작품의 개선으로 이어지지 않았다. 더 복잡한 학습 탐색 자체가 음악적 정확도를 보장하지 않는다는 반례다.

사전 고정한 세 모델을 같은 원 Dev 자료에서 ordinary decoder로 다시 선택했다. 참조와 양립하는 경로만 고르거나 loss-augmented 추론으로 정답을 주입하지 않았다. 초기 모델과 단계72 모델의 경로·비용·평가표는 이전 실행과 동일하게 재현됐다. 다음은 Dev 계수 조정이 아니라 **Train에서 화음 구성음/NCT 설명과 실제 화음 유지·교체 증거의 표현을 점검하는 작업**이다.

## 2. 사전 계약과 구현

- 세 조건: `initial_full_score`(학습 전 전체 점수), `online_frozen_full_score`(단계72 고정 모델), `adversarial_frozen_full_score`(단계75 고정 모델).
- 단계72/75의 report·model·freeze·사후 감사 SHA와 학습 자료/로컬 이용 계약을 확인했다. 단계75는 직렬화 비교를 교정한 **봉인 감사 v2**를 요구한다. 재학습·새 epoch·최고 checkpoint 선택·parameter sweep은 없다.
- 원 72scope/63graph/44,204edge·14전체 악장 source/9명명 작품군을 사용했다. 15개 pair ID 중 Mozart K283-1의6개 source-preflight 보류를 포함한다. 원 보류9개(연산2/계획1/source6)는 모든 조건에서 그대로 남기고 재시도하지 않는다.
- 부분 참조, 정답 경로 부재, 원 보류를 제외하지 않았다. 완전 평가51개·부분21개, 참조-compatible 후보 ceiling36/51 및 동일 coverage를 보존한다. ceiling은 정확도가 아니다.
- 기존26특징·24학습/2고정 계수, 최대6 raw edge/2M 연산 한도, 원 source/철자/음가/붙임줄/half-open 시간·IDs·grace 관문을 바꾸지 않았다.
- **고정 모델 → 원음표 ordinary 선택72개 저장 → prediction-freeze → 이번 평가 참조 report 개방 → 지표/사례 비용** 순이다. 과거 lineage 컨테이너는 이미 노출돼 있으므로 독립 blind Test라는 주장은 하지 않는다.
- 전체 attempted63개를 case로 저장했다. 기존61case를 모두 연결하고2개를 추가했다. 63record/60고유 exact 범위이며 중복·겹침은 분모에서 임의 제거하지 않았다. 모든 case는 전체 XML/IR·전후 문맥·원 note/sound IDs·세 경로·26특징/availability·각 동일 계수의 경쟁 경로 비용·사후 reference witness를 참조한다. 인간 확정/새 gold로 승격하지 않는다.
- JSON 비교는 canonical content hash를 사용한다. tuple/list의 JSON 배열 표현 차이를 허용하되 배열 순서·정확 수치·null/known-zero를 보존한다. 이전 봉인 code/artifact는 수정하지 않았다.

새 파일:

- [세 조건 Dev runner](../../../src/musicanote_harness/harmony_adversarial_score_dev_trial.py)
- [입력·봉인·추론·직렬화 검사](../../../tests/test_harmony_adversarial_score_dev_trial.py)
- [관련 회귀 validator](../../../scripts/validate_harmony_adversarial_score_dev.py)
- [원음표 비용/경로/지표 사후 auditor](../../../scripts/audit_harmony_adversarial_score_dev.py)

## 3. 실제 측정

아래 수치는 원 주석의 **근음+철자 구성음 투영과의 일치**다. 전체 Roman/전위/국소 조성/종지/NCT 정확도가 아니다. ‘전체 일치’는 완전 평가 가능한51scope에서 그 투영 진행이 전체적으로 맞는 수다. 시간 지표에는 부분 평가 구간의 알려진 참조 부분도 포함한다.

| 지표 | 초기 전체 점수 | 단계72 모델 | 단계75 새 모델 |
|---|---:|---:|---:|
| 선택 / 원 보류 | 63 / 9 | 63 / 9 | 63 / 9 |
| 전체 일치 / 완전 평가 | 16 / 51 | 19 / 51 | 16 / 51 |
| 근음+구성음 시간 일치 | 28.8915% | 31.9253% | 30.3034% |
| 근음+구성음 작품군 macro | 53.1500% | 46.3740% | 45.3804% |
| 근음만 시간 일치 | 35.5309% | 35.4959% | 34.1890% |
| 근음만 작품군 macro | 62.1404% | 52.7027% | 52.0326% |
| 의미 경계 TP / FP / FN | 47 / 23 / 16 | 48 / 11 / 15 | 48 / 19 / 15 |
| 의미 경계 F1 | 70.6767% | 78.6885% | 73.8462% |
| 근음+구성음 prediction coverage | 43.7106% | 43.7106% | 43.7106% |

참조 eligible 시간은 약357.083333quarter, 겹침 포함 scope 시간은 약599.166667quarter다. 고유 작품 전체 연주시간으로 해석하지 않는다. 근음+구성음 matched 시간은 약103.166667 → 114 → 108.208333quarter다. 저장된 기존 rational 표현은 그대로 사용했고 역사 자료의 float 유래 긴 분모를 이번에 재작성하지 않았다.

단계72 → 단계75는 시간 **-1.6219%p**, macro **-0.9936%p**, 경계F1 **-4.8424%p**다. 근음만의 시간도 -1.3069%p다. 새로 맞은 전체 구간0/이전 정답 소실3, 의미 경로 변경10record/10고유 범위 중 시간 개선0·퇴행5·동일5다. 초기 → 새 모델은 전체16개 동일, 이전 정답 소실3/새 정답3·변경20record이고 시간 개선10·퇴행5·동일5다. 초기 대비 소폭 시간 개선만 골라 ‘새 모델이 더 좋다’고 보고하지 않는다.

### 작품군별 근음+구성음 시간 일치

| 작품군 | scope 수 | 참조 eligible quarter | 초기 | 단계72 | 단계75 |
|---|---:|---:|---:|---:|---:|
| Beethoven Sonata07-2 | 7 | 239/24 | 87.8661% | 78.6611% | 78.6611% |
| Chopin op50-1 | 5 | 29/2 | 65.5172% | 67.2414% | 65.5172% |
| Corelli op01n04 a–d | 16 | 38 | 46.7105% | 53.9474% | 52.6316% |
| Mozart K283-1 | 6 | 0 | null | null | null |
| Corelli op01n05 a–d | 16 | 75 | 68.3333% | 80.6667% | 80.6667% |
| Beethoven Quartet06-2 | 6 | 607/8 | 5.2718% | 5.2718% | 2.5810% |
| Beethoven Quartet08-2 | 6 | 약7 | 80.9524% | 80.9524% | 80.9524% |
| Beethoven Sonata09-2 | 5 | 3/2 | 66.6667% | 0% | 0% |
| Chopin op50-2 | 5 | 541/4 | 3.8817% | 4.2514% | 2.0333% |

Mozart는 이 투영의 eligible 시간이0이므로 macro에 들어가는 작품군은8개다. Sonata09-2의1.5quarter 같은 작은 분모도 작품군 macro에 동일한 비중으로 들어간다. 긴 Quartet/Chopin의 보류·낮은 일치와 작은 분모의 macro를 함께 봐야 한다. Train15/Dev9 명명 가족의 교집합0이지만 전체 중복/편곡 누출 감사는 미완료이고, 이 자료는 이미 노출된 Dev다.

## 4. 원음표와 같은 새 계수로 확인한 퇴행

아래 비용은 **단계75의 같은 계수**로 단계72 경로와 단계75 경로를 각각 다시 계산한 값이다. 서로 다른 모델 점수를 그대로 빼지 않는다. 낮은 점수가 주석보다 음악적으로 옳다는 뜻은 아니다. 원음표/참조/경쟁 해석 모두 보존한다.

### 4.1 Chopin op50-2 m10~11 — 7화음이 감3화음으로 축소

`cont_1f300d84b87bfc76ff30`, `[28,61/2)`. [case](../../../output/harmony-adversarial-score-dev-2026-10-05-r1/cases/3e987ee8bfece8435be5.json.gz), [전체 XML](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/368d46f4807d08ac9fad/source.musicxml), [전체 IR](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/368d46f4807d08ac9fad/canonical-ir.json.gz).

단계72와 주석은 전체 E♭–G–B♭–D♭/근음E♭이다. 새 모델은 같은 전체 범위를 G–B♭–D♭/근음G로 바꿔 참조 matched2.5quarter를 모두 잃었다. 실제 E♭3은 `[30,31)`에서 울리고(`sound_d14682a7fd30` / `note_1158bfbcca21`), B♭4도 `[30,61/2)`에서 나온다. 앞 D♭5 `[28,59/2)` → C5 `[59/2,30)` → B♭4의 순차 진행은 receipt에 남으며 NCT 확정/원 비구성음 면제는 아니다.

새 계수의 이전 경로 비용 `.3251977500`보다 감3화음 `.3206816214`가 약 `.0045161286` 싸다. 추가 구성음 복잡도 절감 `-.193457`과 근음 지연 절감 `-.069894`가 실제 비구성음/지속/강세/lowest 비용 증가를 압도한다. 새 감3화음의 늦은3음 비용은 증가하지만 보호하지 못했다. **E♭를 못 읽은 parser 오류가 아니라, 읽은 원음을 비구성음으로 설명하는 후보의 점수 균형 문제**다. 모든 G감3화음을 금지하는 규칙으로 고치지 않는다.

### 4.2 Beethoven Quartet06-2 m42~44 — 빠른 색채 진행에 과분할

`cont_e7191dd5889497e23dc1`, `[167/2,175/2)`. [case](../../../output/harmony-adversarial-score-dev-2026-10-05-r1/cases/5a7f8e0ef80d4cf5d89a.json.gz), [전체 XML](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/2755c72f00b3ace4d57a/source.musicxml), [전체 IR](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/2755c72f00b3ace4d57a/canonical-ir.json.gz).

주석/단계72의 전체 B♭–D–F–A♭가 새 모델에서는 B♭7 → E♭3화음 → E감3화음 → F단7화음 → B♭7의5run으로 나뉜다. 범위 시작의 B♭3/D4/F4/A♭4는 원 onset167/2에 실제로 함께 있다. m43에는 D–E♭–E–F–F♯–G…의 빠른 상행이 있고, 새 첫 경계1021/12에서 E♭5가 attack한다(`sound_26fa215e62ad` / `note_b05c3e832796`); m44의 E5→F5도 원 onset173/2→693/8이다. **새 attack이 있다는 사실과 새로운 화음이 성립한다는 해석은 다르다.**

이전 경로 `.5645646106` → 새 경로 `.5156765745`, 차이 약 `-.0488880361`이다. `dominant_family_leading_tone` 절감 `-.351752`가 run/교체/무근거 경계/근음 도약 등의 추가 비용을 크게 압도한다. 맞던 전체 구간을 잃고 matched시간은49/24quarter 감소한다. 이 수치는 해결 credit의 누적/조건·실제 베이스와 화성 유지·교체 근거를 점검할 이유이며, **중복 credit 버그나 이 모든 음이 확정 NCT라는 판정을 이번에 증명한 것은 아니다.** 실제 secondary 진행까지 하드 필터로 제거하지 않는다.

### 4.3 Chopin op50-1 m47 — 마지막 짧은 D5에 새 경계

`cont_bd6b83571ed9664c9265`, `[279/2,141)`. [case](../../../output/harmony-adversarial-score-dev-2026-10-05-r1/cases/8cf0737357d4d6126364.json.gz), [전체 XML](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/911478658f27c8e09214/source.musicxml), [전체 IR](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/911478658f27c8e09214/canonical-ir.json.gz).

주석/단계72는 G단3화음 `[279/2,140)` → E♭3화음 `[140,141)`이다. 새 모델은 E♭3화음을563/4까지 유지하다 마지막1/4quarter를 G단3화음으로 다시 바꿨다. D5의 실제 onset563/4와 음가1/4(`sound_5f9b8042f310` / `note_e688e529409c`), 계속 울리는 G4·B♭4는 보존돼 있다. E♭5 `[140,563/4)`도 저장했다. 전체 정답 하나와 matched1/4quarter를 잃는다.

이전 경로 `.2129822292` → 새 경로 `.2052830000`, 차이 `-.0076992292`다. 비구성음·강세·조표 이탈 비용 절감이 추가run/교체/근음 도약 비용을 이긴다. 짧은 종료음을 항상 NCT라 하거나 특정 마디 경계를 금지하지 않는다. 지속된 화음·선율 해소가 함께 설명되는 일반 근거가 필요하다.

### 4.4 그 밖의 변경도 보존

Corelli op01n04d `[81,84)`에서 A단3화음의 마지막1/2quarter가 C3화음으로 갈라져 부분 일치가 감소했다([case](../../../output/harmony-adversarial-score-dev-2026-10-05-r1/cases/36e5091ddc63fda7a799.json.gz)). Chopin op50-2 `[347/2,175)`의 부분 참조도1/2quarter 감소한다. Sonata09-2의 세 부분 참조 구간과 Sonata07-2/Corelli op01n05a의 무변화 시간 변경도10변경 목록에 그대로 남았다. Partial의 `selected_hit=null`을 오답0이나 전체 정답으로 바꾸지 않는다.

## 5. 검사·감사·성능·보존

- **회귀:** 이전731 + 직렬화4 + 새 Dev8 = **743검사/65고유 모듈 PASS**, failure/error0,81.074초. 전체 repository의 모든 검사를 실행했다는 뜻은 아니다. 새8개 단독도 PASS했다.
- **Actual:** r1 완료/exit0,231.552초. 조건별 선택+검산 합계 초기67.938/단계72 39.538/새40.748초, 중앙 `.202720/.162586/.170491`초, 최대29.188/16.067/15.807초다. 첫 조건의 source 준비/cache와 동시 회귀 실행이 있어 정식 속도 비교나 새 모델의 성능 개선으로 주장하지 않는다.
- **감사:** 4,370고유SHA·72예측·원63graph/44,204edge·14전체 source·원 보류9·189승자 비용/특징/availability·189case receipt·567동일 계수 경쟁 비용·108평가 전용 witness 비용·63case/이전61연결·세 지표/모든 비교 목록 재생 **PASS/exit0**다. 새 search/fit이 아니다. 실제 선택 비용이 같은 계수 경쟁 경로 비용보다 높지 않은지도 확인했다.
- **실패 이력:** 새 검사/actual/감사 실패0. 준비 중 예전 기록 파일명을 `online-score-dev-validation.md`로 조회한1회 경로 오류는 실제 `online-score-dev-check.md`로 확인했다. 문서의 단발 Python 조회가 cp949 출력에서1회 중단돼 `PYTHONIOENCODING=utf-8`로 재조회했다. 원 문서가 깨진 것이 아니라 출력 인코딩 문제다. 긴 문서/receipt 콘솔 잘림은 compact 조회로 보완했고 봉인된 artifact나 조건을 변경하지 않았다.
- 신규4Python UTF-8/AST/줄끝 공백 검사 PASS, 기존5tracked dirty 보존·git diff --check PASS(기존 LF→CRLF 경고만 있음). 봉인 뒤 code/test/script는 수정하지 않았다.
- 최종 메인/로그/정본3문서의 UTF-8·깨진 글자/다른 언어 문자·공백 및291개 로컬 링크 검사 PASS, 원 실행의421 code pin 변화0·최종 감사와 report/auditor SHA 연결 PASS다. 초안의 다른 언어 문자2개는 한국어로 교정했다. 정본에 저장된 원 데이터와 모델은 수정하지 않았다.
- 원 Core/XML/주석·source eligibility·NC 로컬 연구 제한을 유지했다. 외부 API/상업 운영 허가를 추가하지 않았다. UI/서버/MusicSearch/Composition/Claude Phrase·Motif/별개 dirty/Git 변경0, merge/commit/push0. 이번 화면 표시도 바뀌지 않는다.

## 6. 다음 개발 순서

1. **더 강한 학습이나 Dev 가중치 조정보다 score의 음악적 표현을 먼저 점검한다.** Train의 초기/단계72/단계75 및 현재 fresh adversary 대조에서 (a)3화음·7화음의 실제 구성음/늦은근음/생략, (b)빠른 순차·반음계 진행과 실제 화음 교체, (c)leading-tone 해결 credit과 지속 베이스/성부·화성 지지를 나눠 확인한다. 이번 Dev 사례는 위험 종류를 보여주는 개발 반례이고 새 학습 target으로 넣지 않는다.
2. Credit의 정규화/누적과 unsupported/nullable 역할의 비용 비교 가능성을 검토한다. 일반화 가능한 **증거/상호작용 특징**으로 표현하되 특정 작품 예외, 정답 화음 강제, unknown을 known-zero로 변환, 과도한 하드 필터를 만들지 않는다. 원음표와 준비·해결은 보존하며 전체 NCT를 완성했다고 주장하지 않는다.
3. Train에서 작은 완전 탐색/반례와 다양한 작품의 회귀를 먼저 통과시킨 뒤 새 후보/특징 계약을 고정한다. 후보 recall과 선택 오류를 분리하고 같은 원 Dev의 결과를 숨기지 않는다. 양성/음성 모두 있는 비교가 필요하다.
4. 독립 작품/중복·편곡 누출 감사 및 공개 모델의 공통 조건 비교를 별도로 진행한다. 새 모델의 안정성이 입증되기 전 UI·종지·구조 분석을 교체하지 않는다. 국소 조성/전위/전체 Roman·NCT/장문 보류·작곡편곡 연결도 완료되지 않았다.

## 7. 정본과 재현

- [결과 report](../../../output/harmony-adversarial-score-dev-2026-10-05-r1/report.json), SHA `6eb4037bfd5c69c24c12acdb17cf32a04885a398853e8cabf48807a3eeb1821c`.
- [run contract](../../../output/harmony-adversarial-score-dev-2026-10-05-r1/run-contract.json), SHA `c1c23f70f59900d5fb7779e5b674667bf6b8e3c6499f1edaec6b19ca8c78c92b`.
- [예측 봉인](../../../output/harmony-adversarial-score-dev-2026-10-05-r1/prediction-freeze.json), SHA `87511f72dd590c7532ce64f4a3a59711c91b04795e9d97ead59cb2359522589a`.
- [사후 감사](../../../output/harmony-adversarial-score-dev-2026-10-05-r1/post-seal-audit.json), SHA `6c1c008c498e32bb2e3b48c130986944d9862f65536d5d9933b4f8a9f5a865af`.
- [743검사 결과](../../../output/harmony-adversarial-score-dev-validation-2026-10-05-r1.json), SHA `184b48b81821bbc3da519e4bb1986b859996de0e7b0d14093c72dbc0dc73fde4`.
- 사용한 단계75 모델 SHA `2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf`, 단계72 모델 SHA `029e2de31ab6e5d9e5fa65eb229c63fe649cce10ddd987dbab4c2b7f3f06f331`.

기존 출력을 덮어쓰지 않는다. 재실행은 새 r2경로를 사용한다. 평가 뒤 code/계수를 바꿔 같은 r1을 다시 만들지 않는다.

```powershell
$env:PYTHONPATH = 'src;tests'
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_adversarial_score_dev.py --prior-validation output/harmony-adversarial-score-validation-2026-10-05-r1.json --output output/harmony-adversarial-score-dev-validation-2026-10-05-r2.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_adversarial_score_dev_trial --output output/harmony-adversarial-score-dev-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/audit_harmony_adversarial_score_dev.py --root output/harmony-adversarial-score-dev-2026-10-05-r2
```
