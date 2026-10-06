# J3a — 공통 평가기와 독립 작품 검증 준비

기록 ID: **HARM-DEV-20261004-55** · 2026-10-04.

상태: **공통 평가기 구현·기존 결과 재현·확대 자료 메타데이터 검사 완료**. 독립 악보의 새 화성 추론이나 공개 모델 비교를 완료한 것은 아니다. [직전 J2f](2026-10-04-functional-run-learning.md)의 미채택 결정과 기존 운영 화면을 유지한다.

## 1. 이번 단계의 범위

원 계획 J3의 첫 단계다. 기존 개발 결과와 공개 모델을 같은 시간축·분모에서 평가할 수 있도록 만들고, 이미 본 작품을 새 blind test로 세지 않도록 이력을 확인한다. 전체 코퍼스 재수입, DB 재설계, 가중치 재학습, 새 이론 규칙 보완으로 범위를 확대하지 않았다.

추가 파일:

- [공통 평가기](../../../src/musicanote_harness/harmony_common_benchmark.py), `harmony-common-benchmark-0.1.0`.
- [동결 재현·메타데이터 실행기](../../../src/musicanote_harness/harmony_benchmark_preparation.py), `harmony-benchmark-preparation-0.1.0`.
- [평가 검사](../../../tests/test_harmony_common_benchmark.py), [실제 파일 실행기 검사](../../../tests/test_harmony_benchmark_preparation.py).
- 노출 이력 [초기 snapshot](../experiments/2026-10-04-benchmark-exposure-ledger.json), [최종 v2](../experiments/2026-10-04-benchmark-exposure-ledger-v2.json). 기존 split/rights를 수정하지 않는 별도 기록이다.

## 2. 공통 평가 계약

시간은 exact rational global quarter, 구간은 `[start,end)`다. 서로 다른 엔진이 낸 결과는 같은 source-bound score clock으로 먼저 변환해야 한다.

| 항목 | 규칙 |
|---|---|
| 근음 | step/alter 철자 일치. F#과 Gb를 합치지 않음 |
| 근음+구성음 | 근음 및 중복 제거된 구성음 철자 집합. 정렬 순서는 무관 |
| Quality / inversion / local key / degree / Roman | adapter가 명시적으로 제공한 라벨만 비교. 근음/음집합의 성공으로 이 항목을 성공 처리하지 않음 |
| Reference 미지원 | 해당 항목의 unavailable time을 별도 보고 |
| Prediction 미지원·보류 | 지원된 reference 분모에 남고 일치0·prediction coverage0 |
| 시간 일치 | 구간 교집합의 정확한 유리수 길이를 적분 |
| 작품군 macro | 작품군마다 적격 시간 일치율을 계산한 뒤 평균 |
| 경계 | 완전 reference 문맥의 근음+구성음 변화. 동일 signature raw 분할은 새 경계가 아님 |
| 전체 구간 일치 | 문맥 전체가 지원될 때만 true/false. 부분 reference는 null |

Onset 출력은 다음 onset 전까지 유지하고, 마지막 출력은 score end까지 유지한다. 첫 예측보다 앞선 구간은 unknown이며 첫 화음으로 메우지 않는다. 중복 onset은 임의 선택하지 않고 집계 adapter를 요구한다. Native float 또는 `partitura_onset_beat`를 quarter로 간주하지 않는다. 실제 source beat-map 및 written/concert, pickup, meter/repeat 정책의 binding 검증은 외부 adapter 단계에 남아 있다.

32분음표 표본 평가는 **1/8 quarter 간격, global phase0, 구간 안의 k/8 시점에서 활성 라벨**로 별도 계산한다. 기존 시간/경계를 반올림하지 않는다. 논문의 CSR과 같은 32분음표 단위를 사용하지만 라벨·split·grid phase·전처리의 재현을 검증하지 않았으므로 **논문 재현 점수로 부르지 않는다**.

## 3. 기존 결과의 실제 재현

동일33악보/19작품군/322문맥에서 J2e 고정 점수와 J2f 미채택 학습 점수를 새 평가기로 다시 채점했다. 새 추론/학습은 실행하지 않았다. 기존 report의 전체 일치·적격 시간·근음/구성음 시간·작품군 macro·경계 TP/FP/FN/P/R/F1과 정확히 일치함을 실행기가 검사한다.

| 지표 | J2e 고정 | J2f 학습·미채택 |
|---|---:|---:|
| 전체 일치 /완전256 | 52 | 55 |
| 근음 exact-time 일치 | 41.48% | 38.11% |
| 근음+구성음 exact-time 일치 | 31.97% | 30.33% |
| 근음+구성음 작품군 macro | 39.08% | 37.03% |
| 경계 TP/FP/FN | 215/94/228 | 133/25/310 |
| 경계 F1 | 57.18% | 44.26% |
| 근음+구성음 32분 표본 일치 | 2525/7894 =31.99% | 2395/7894 =30.34% |
| 선택 /보류 | 288 /34 | 288 /34 |

적격 시간은 `7895/8` quarter, reference 미지원 시간은 `7183/24` quarter다. 두 엔진 모두 명시된 근음·구성음 prediction의 적격 시간 coverage는59.33%다. 문맥 선택 비율과 시간 coverage는 다르다. 겹치는 개발 문맥의 시간이며 고유 전곡 길이가 아니다. 나머지 quality/inversion/local key/degree/Roman의 현재 지원 분모는0이므로 일치율은 **null**,0%나 성공률100%가 아니다.

### 후보 누락과 선택 오류의 구별

| 완전256문맥의 결과 | J2e | J2f |
|---|---:|---:|
| 정답 진행이 후보망에 있고 선택도 맞음 | 52 | 55 |
| 후보망에 정답이 있지만 선택 오류 | 88 | 85 |
| 후보망에서 정답 진행 부재를 확인 | 101 | 101 |
| 자원/입력 보류로 후보망 포함 여부 미확인 | 15 | 15 |

후보 정답 포함 확인140/256은 기존 수치와 같다. **나머지116개 모두를 확인된 후보 누락으로 해석하면 안 된다:**101부재 +15미확인이다. J2f 기록의 해당 설명을 정정하며 원 prediction/report/수치는 바꾸지 않는다. 처음 전체 실행 시 이15개의 null을 bool로 요구해 출력 생성 전에 실패했다. null을 false로 바꾸지 않고 별도 unavailable category로 수정한 뒤 회귀 검사와 전체 실행을 완료했다.

## 4. 독립 자료 자격 감사와 확대 후보

### 기존43개 manifest의 holdout

7개 holdout package/3작품군의 메타데이터만 검사했다. 원 악보·IR·주석 내용을 새로 읽지 않았다.

- **Mozart K279:**2026-09-24 surface/unfolded 실험에서 이미 결과와 주석 비교가 문서에 기록돼 있다.9월25일 split 지정보다 앞선 노출이다.3악장 전부 새 독립 test에서 제외한다. 원 manifest를 dev로 몰래 변경하지 않고 이력을 sidecar로 남긴다.
- **Beethoven quartet n02op18-2:**1·4악장은 현재 메타데이터 관문을 통과하지만 blind 승인 완료가 아니다.2악장은 source note mapping이 불완전하다.
- **Mozart K282:**원 manifest의 `blind_evaluation=false`를 유지한다. Exact-only ratio0은 verified-transform 정렬을 부정하는 근거가 아니므로 새 준비 snapshot의 정렬 검사를 별도로 한다. 새 snapshot이 좋아졌다고 원 자격을 자동 승인하지 않는다.

### 기존392개 준비 snapshot의 확대 검사

5collection/392package를 preparation report의 identity·정렬·note mapping 메타데이터로만 확인했다. 새 원 MusicXML/TSV/IR 내용 또는 화음 라벨은 평가용으로 열지 않았다.145개의 **명명 관례 기반 작품군**이며 작품 계보를 전문가가 확정한145독립 작품이라는 뜻은 아니다.

분류는 우선순위가 있는 상호 배타적 package 수다.

| 분류 | Package |
|---|---:|
| 알려진 개발 작품군·byte/lineage alias 또는 과거 음악적 노출로 제외 | 53 |
| 정렬 또는 source note mapping 미완전 | 144 |
| 작품군 identity 미해결 | 5 |
| 메타데이터 준비 후보, 전체 노출 이력은 아직 미확인 | 190 |

190개는83작품군에 속한다. 내부 원본 데이터의 사용 허가, blind eligibility 또는 전체 정렬 검증 완료를 의미하지 않는다. 교향곡 데이터는 이5collection의392package에 없으므로 이번 실행의 편성 검증에 포함했다고 주장하지 않는다.

결과/화음 라벨이 아니라 명명 관례의 작품 키 순서로, collection당 최대2작품군을 사전 고정해 **10작품군·16악보**를 다음 검증 준비 대상으로 저장했다. 적격 메타데이터를 가진 악장 목록이며 그 작품의 모든 악장이 적격이라는 뜻은 아니다. 가족의 다른 악장을 다른 split으로 이동하지 않는다.

| Collection | 다음 준비 작품군 | 저장된 악보 |
|---|---|---|
| Beethoven quartets | n06op18-6, n08op59-2 | 각2악장, 총2개 |
| Beethoven sonatas | 07,09 | 각2악장, 총2개 |
| Chopin mazurkas | BI145-1op50, BI145-2op50 | 각1개, 총2개 |
| Corelli | op01n04,op01n05 | 각a–d, 총8개 |
| Mozart sonatas | K282,K283 | 각1악장, 총2개 |

초기r1에는 기존 cohort 밖인 Beethoven08이 아직 history-unknown 후보로 포함됐다. 후속으로 [개발 보관 기록](../archive/DEVELOPMENT_HISTORY_THROUGH_2026-09-29.md)의 Op.13 검증·사용자 의견을 확인하고 ledger v2에서 **전체08가족 제외**를 추가했다. 원 r1/ledger v1은 보존하고 동일 evaluator/code로 r2를 실행했다. 학습/점수/평가 분모는 변경하지 않았다. r1은 임시 준비 snapshot이며 최종 일정 정본은r2다.

현재10작품군은 **staged candidate**, frozen blind test가 아니다. 작품 간 중복·판본·다른 코퍼스와 UI/검색/과거 실험의 노출, 원 annotation 제거한 입력, IR/repeat/시간 revision binding, 명시된 실행 정책, 외부 checkpoint 학습 중복을 확인한 뒤 첫 평가를 실행한다. 내용 검토가 필요해 노출된 것은 개발/진단 자료로 표시하고 별도 최종 holdout과 구별한다.

## 5. 공개 모델의 실제 준비 상태

공식 source를 다시 확인했다. [ChordGNN README](https://github.com/manoskary/ChordGNN)는 별도 Python3.8/PyTorch1.12 환경과 W&B checkpoint를 설명한다. [공식 inference 코드](https://github.com/manoskary/ChordGNN/blob/main/analyse_score.py)는 native onset/measure와 여러 component를 디코딩한 뒤 MusicXML에 표기를 만든다. 원 native 출력을 확보해 source clock에 매핑하는 adapter가 필요하다. 화면용 MusicXML에 쓴 Roman만 다시 읽어 원 prediction과 동등하다고 가정하지 않는다.

[AnalysisGNN README](https://github.com/manoskary/analysisgnn)는 construction 상태와 Roman resolve/onset·beat aggregation TODO를 명시한다. 실제 출력 계약과 checkpoint를 검증하기 전까지 공통 완제품 비교 결과를 만들지 않는다.

[ChordGNN 논문 §4–5](https://arxiv.org/html/2307.03544v2)는 같은 split, component별 CSR 및 onset RN을 구별한다. 학습 source에 Beethoven quartets/sonatas, TAVERN/WiR 등과 추가 Mozart 자료가 있으므로 로컬 test에 넣었다는 이유만으로 pretrained overlap이 없다고 할 수 없다. **Checkpoint별 원 training manifest 확인 전에는 overlap=unknown**이다. 논문 표의 숫자와 이번 root+members 개발 숫자를 직접 순위 비교하지 않는다.

공개 repo를 읽었지만 모델 설치/다운로드/실행은0이다. Git HTTPS helper가 없는 환경에서 revision 조회가 실패했고, 별도 API revision 조회는 socket 접근 제한으로 실패했다. 권한 확대나 기존 venv를 변경하지 않았다. 정확한 commit/checkpoint pin은 pending이며 dynamic source 조회를 재현성 pin이라고 부르지 않는다. 자체 평가 준비·기존 결과 재현은 이 미해결 항목과 독립적으로 완료했다.

## 6. 검증·정본·재현

신규38 +직전 관련198 +manifest/cohort7 = **243 PASS /3.147초**. Exact/grid 차이·삼연음·끝 제외·enharmonic·동일 화음 분할·미지원 component·보류 분모·macro·native beat reject·onset prefix/마지막 범위·training adversary reject·source/hash/split/부모 숫자 변조·null ceiling·준비 후보의 승인 비승격·덮어쓰기 금지를 검사했다. 인공 검사 수를 음악적 정확도로 해석하지 않는다.

정본 전체r2는 **1.505초/exit0**이며 report/code/metadata/원 입력 **1,253고유 physical SHA**를 종료 시 확인했다. Source map1249 +code map5의 중복1을 제거한 값이다. 원 J2f의850입력/코드 guard도 그대로 포함한다. 개발 자료 두 arm의322문맥씩 **644채점 record**이며644독립 사례가 아니다.

- [정본 report](../../../output/harmony-common-benchmark-2026-10-04-r2/report.json):291,326B, SHA `05384c37daba6edd6f99d77a612451f0ede81966a3d3c2542c892a26a767a682`.
- [문맥·arm별 채점](../../../output/harmony-common-benchmark-2026-10-04-r2/common-evaluation.jsonl):1,525,432B, SHA `5dac5cc22829d7550575d7aa71ff0521c8edc389bf265f4dc3d7a104619dc46c`.
- [다음 준비 목록·392개 메타데이터 검사](../../../output/harmony-common-benchmark-2026-10-04-r2/independent-evaluation-plan.json):521,542B, SHA `f504636ca42212c122680650f57c564bf564c768f73ebe6c579b242d92dfa5dd`.
- 공통 evaluator source SHA `0ab045c19b64d4e4f4834d4492ef9acb63bbe0d5dc3e3648f4be7a0bbdb6d440`, runner SHA `031f77c75b88a4445e775c5b26f05559ee7eac29e0aa05af22a45b66918ca8fc`.
- Ledger v2 SHA `3ba128e611e85e43a66515301e6da17693f131cac43de3feb0741459ea54860d`.

`python -B -m musicanote_harness.harmony_benchmark_preparation --help`의 manifest/recall/baseline/learned/ledger/batch와 각6 SHA를 지정한다. 경로/입력 pin은 정본 report에 보존돼 있다. 새 output만 허용한다. 실제 score inference, model training, 공개 모델 실행, 원 split/rights 변경, Core/XML/주석/운영UI/서버 변경, Git commit/push는0이다.

## 7. 다음 단계와 완료 기준

**J3b: 이10작품군의 실행 관문 확인 → 동일 모델의 첫 확대 blind/개발 평가 → 공개 모델 native adapter·격리 환경 준비** 순서다. 이력을 모르는 작품을 독립이라고 부르거나 이미 본 작품을 새 이름으로 test에 넣지 않는다. 공통 입력과 라벨 mapping, checkpoint 및 중복 상태가 준비되면 ChordGNN을 우선 비교하고 AnalysisGNN은 실제 출력 준비 후 추가한다.

현 엔진의 전체 Roman/전위/조성 출력 미지원 때문에 공통 표의 그 열은 아직 비어 있다. 후보 recall과 실제 선택 성능을 먼저 측정하며, 새 평가에서 드러나는 큰 후보/문맥 표현 오류는 J4에서 처리한다. 모든 교재 예외·자료 정리 완료를 첫 확대 실행의 전제로 삼지 않는다. 운영 승격과 구조·작곡·편곡 연결은 별도 완료 기준을 유지한다.
