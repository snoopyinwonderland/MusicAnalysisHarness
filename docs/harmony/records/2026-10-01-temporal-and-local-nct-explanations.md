# 분산된 구성음 제시와 조건부 경과·보조음의 공동 근거

## 1. 목적과 범위

2026-10-01 사용자의 계속 진행 요청에 따라 직전 literal/direct 단계의 다음 기능을 개발한다. 실제 음표가 시간에 걸쳐 화음 구성음을 제시하는 방식과, 특정 화음 가정 아래 경과·보조 음형을 이루는 원음표를 같은 성부 연결에서 대조한다. 특정 작품이나 마디 번호를 규칙에 넣지 않는다.

이번 단위는 **한 exact descriptor 구간 안의 시간순 구성음 제시와 조건부 경과·보조 음형**이다. 경계를 넘는 선행음·계류, 지연 해결, 분산화음/페달/최종 화음 확정은 후속 단위다. 작은 부분 사례에 맞춰 기존 규칙이나 원음표를 제거하지 않는다.

직전 정본은 [실제 음표·시간과 직접 해결 근거](2026-10-01-literal-and-direct-motion-grounding.md), 상위 설계는 [문맥 추론 규칙](../HARMONY_REASONING_RULES.md)이다. 이 문서는 인수인계가 아닌 별도의 화성 **개발 기록**이다.

## 2. 착수 때 발견한 검증 범위 문제

직전 실제 5문맥의 9개 all-lane completion에는 직접 연결이 총 5개 있으나, 연속된 두 연결 `x→y→z`를 함께 갖는 직접 세 음표 경로는 없다. 그 묶음만 사용하면 경과음·보조음 양성이 없다는 결과가 계산 방식상 강제된다. 이를 음악에 그런 음형이 없다는 증거로 사용할 수 없다.

따라서 다음을 분리한다.

- 기존 `fmgr` bundle은 몸체와 출처를 그대로 보존하는 비교 자료다.
- 새 expanded geometry에서 **필수 두 연결 전체**를 요구한 별도 typed local-chain bundle을 만든다.
- 다른 lane도 포함한 하나의 실제 completion에서 두 연결이 함께 가능해야 한다. 각각 가능한 두 witness를 합치지 않는다.
- 필수 연결 이외의 부분은 무연결 대안으로 명시한다. 이것은 실제 악보의 정답 성부나 최고의 성부 연결을 선택한 것이 아니다.

과거 `fmview`/path로 부모를 위장하거나 이전 묶음을 늘려 재봉인하지 않는다.

## 3. 일반 음악 규칙

### 3.1 조건부 경과·보조 음형

원 sounding event 세 개의 **전체 지속 범위**가 한 descriptor 안에 있고, 같은 raw lane의 순차 연결이 가능해야 한다. 세 음표의 철자·음역을 보존해 두 번의 보통 순차 진행을 검사한다.

- 회원 관계가 `구성음 → 비구성음 → 구성음`이다.
- 같은 방향의 두 순차 진행은 경과 음형 후보다.
- 첫 음과 마지막 음의 같은 철자·음역 복귀는 보조 음형 후보다.
- source-clock, pitch spelling, attack, grace/point, full tie/원출처 전제를 지킨다.
- raw lane은 검증된 음악적 독립 성부와 같다고 선언하지 않는다.

이것은 **조건부 contour 설명**이다. 박절·강세·협화 판단이 완료되었다는 뜻이 아니며 NCT 확정 라벨, confidence, harmonic winner로 승격하지 않는다. 구간 밖의 지지음을 가져와 같은 화음이라고 가정하지 않는다.

### 3.2 설명량과 원 관찰의 분리

설명 대상으로 삼는 것은 가운데 비구성음뿐이다. 같은 sound/descriptor/bundle의 설명 구간을 유리수 `[start,end)`로 합집합하여 중복 음가를 막는다. 설명을 붙여도 원 member/nonmember/unknown row와 원 note-time이 그대로 남는다. source 보류·미관측 구성음·경쟁 후보도 남는다.

동시음 여러 개의 note-time 합과 시간축에서 구성음이 존재하는 구간 합집합은 다르다. 두 값을 구별하고, 조건부 설명 시간이 원 비구성음 시간보다 커지지 않게 검사한다.

### 3.3 시간에 걸친 구성음 제시

각 descriptor의 ordered member별로 실제 제시 음표·겹치는 구간·합집합 음가·첫 관측과 실제 attack을 기록한다. 이전 구간에서 시작해 지속되는 음은 이 구간에서 새로 공격한 음과 다르다.

동시 완전 구성음 구간과, 여러 시점의 구성음을 합친 분산 제시는 따로 기록한다. 후자의 음집합에 모든 구성음이 있다는 이유만으로 분산화음·화음 지속·경계 없음이라고 확정하지 않는다. 진짜 화음 변화, 다른 비구성음, 미관측 구성음, 조성/기능 대안은 계속 비교해야 한다.

## 4. 구현 계약과 계산 공유

새 core는 `factor_temporal_explanations`, 새 append-only 실행기는 `factor_temporal_explanation_trial` v0.1.0이다. 원 IR·scope·hypotheses·index·relations·grounding을 authentic replay한 **owned 입력 session**을 사용한다. 공개 build는 이 준비 과정을 호출하고, 실행기는 문맥별 한 번 준비한 session을 재사용한다.

전체 후보를 top-k로 자르지 않는다. 원 descriptor·variant·group·key와 logical 분모를 보존하면서 같은 geometry/회원 관계/설명량만 공유한다. descriptor 질의는 descriptor/presentation/account와 `grounded_profile_ref`를 반환하며 `profile=null`이다. 원 variant 질의만 출처별 supplier/segment 필드까지 포함한 exact frozen profile을 복구한다. 두 질의의 결과를 동일한 원 profile 반환이라고 표현하지 않는다.

전체 geometry, membership relation, 새 bundle, account template에 각각 명시적 한도를 둔다. 초과 시 일부 prefix만 계산하고 전체 완료라고 표시하지 않는다. 알려진 0과 미계산 `null`, 실패·보류·미실행 문맥을 구별한다. 성부 연결 geometry 질의의 work 한도 역시 부분 답을 완전한 답으로 돌려주지 않는다.

공개 계약은 `prepare_inputs`/`build_explanations_prepared`, fresh `build_explanations`/`validate_explanations`, 저장 결과를 검증하는 `prepare_explanations`, exact descriptor/원 variant 질의 `query_descriptor_prepared`/`query_origin_prepared`로 구별한다. 입력과 결과는 소유한 immutable session에 보관하고 현재 producer·부모 참조·seal·내용을 검증한다. 호출자 JSON을 바꾸어 session을 바꿀 수 없으며, 매 lookup마다 전체 부모를 재실행하지 않는다. 동시 편집에 대한 atomic ABA snapshot이나 무제한 수명/RSS 보장을 주장하지 않는다.

| 전체 한도 | 기본값 | 단위 |
|---|---:|---|
| `max_geometry_candidates` | 4,096 | 실제 두 edge로 가능한 raw 세 음표 geometry |
| `max_membership_relations` | 65,536 | descriptor와 contour의 유한 관계 레코드 |
| `max_new_bundles` | 4,096 | 새 필수 두 edge의 all-lane completion |
| `max_account_templates` | 262,144 | 구별되는 설명량 template |
| `query_work_budget` | 100,000 | 새 bundle의 raw-lane별 `geometry.query` DP 작업량 |

이는 candidate materialization/성부 연결 질의 예산이지 파일 byte·RSS 상한이 아니다. `query_work_budget`은 새 bundle을 만들 때 각 raw lane의 geometry 질의에 따로 전달된다. run/bundle 전체 또는 prepared descriptor/origin lookup의 총 예산이 아니며 closed-form completion은 0에서도 exact일 수 있다. membership predicate 비교 수와 저장 relation 수도 다르다. origin→descriptor 및 descriptor→relation 색인을 공유하고, 같은 ordered members/pitch의 회원 판정을 공유하지만 원 모든 쌍·origin·key의 정확한 가중 분모는 유지한다. geometry는 전체 incoming×outgoing 수를 먼저 세어 초과 시 prefix를 만들지 않는다.

설명량 계정은 `source_guarded_member`, `conditional_explained_nonmember`, `unexplained_nonmember_under_this_completion`, `unassessed_nonmember`, `membership_unknown`, `source_or_hypothesis_unsupported`를 구별한다. category note-time의 합은 원 raw total이며, weighted raw/category total은 실제 구간의 물리 note-time×정확한 logical tuple multiplicity와 같아야 한다. 많은 동시 음표의 additive note-time이 구간 길이보다 큰 것은 오류가 아니므로 시간축 합집합과 혼동하지 않는다.

`bundle_id=null`은 실제 bundle이 아예 없는 경우의 명시적 보류에만 허용한다. 실제 bundle이 있는 universe에서는 등록된 원/새 bundle ID를 전달해야 한다. 다른 completion의 설명량을 합하거나 설명 가능성이 큰 completion을 정답으로 고르지 않는다. 기존 bundle 몸체와 원 typed reference는 바꾸지 않는다.

## 5. 검증 계획

- 같은 bundle에 두 연결이 있는 양성 및 무연결/한 연결만 있는 대조.
- 순차 상·하행/보조 복귀, 다른 음역·철자·반음계/미분음·회원 관계 반례.
- full source/attack/tie guard, point/grace, raw lane, 구간 밖 지지음 보류.
- 원 profile/부모 bundle/weighted origin 분모와 source hash 불변.
- middle sound 설명 합집합, polyphonic note-time과 시간 합집합, 설명량 상한.
- 전체 한도와 0/unknown, 실패한 문맥에서도 원 분모 보존.
- 실제 직전 5문맥의 모든 exact descriptor에 실행하고 저장 결과·공개 질의를 재현.

검사 개수나 후보 수는 음악 정답률이나 작품 수가 아니다. 이 단계의 새 근거는 아직 운영 악보 뷰어/구조 분석/작곡·편곡에 적용하지 않는다.

### 5.1 개발 중 발견·교정과 검사 이력

- 핵심 테스트의 초기 43개 중 4개는 fixture 기대가 잘못되었다. `work_budget=0`도 closed-form exact completion이 가능할 수 있고, 한도 보류 시 부모 baseline bundle 자체가 없을 수 있으며, point/grace descriptor 질의는 그 descriptor의 보류를 검사해야 한다. 테스트 기대를 고치고 반례를 추가했다.
- 마지막 49개 중 empty/unknown 대조 fixture는 실제 C3-only/max-variants=0 입력이 알려진 빈 product였는데 unknown을 기대했다. 해당 실행은 중단하고 비어 있지 않은 C–E–G contrast로 테스트만 바꿨다. 중단한 실행을 통과로 세지 않는다.
- 최종 동결 핵심 테스트 **49개/189.060초 OK**. 동결 source SHA 전후 불변. 별도 마지막 weighted/raw·0/unknown·관계 한도·경과음 검사 4개/13.805초도 통과했지만 중복 횟수를 신규 테스트 수에 더하지 않는다.
- 실행기 초기 21개 실행은 temp fixture의 function-samples 폴더 누락으로 20개 오류(2.400초), 다음은 foreign 폴더 및 삭제된 부모 artifact hash refresh 순서 기대 2개 오류(8.765초)였다. 신규 테스트 fixture만 고쳤으며 production source guard를 완화하지 않았다. 수정 후 21개/9.183초, flag를 `_stage_enabled`로 명확히 한 뒤 21개/9.457초 OK다.
- 최종 동결 실행기 테스트 **21개/9.959초 OK**. 공개 준비/조회, 원출처 복구, current producer·삭제/추가 artifact·허위 부모/seal·caller mutation·실패 분모 보존을 포함한다. 최종 전체 회귀 결과는 아래 실제 실행 완료 절에 별도로 적는다.
- 순차 C4–D4–E4와 지속 C3/G3 합성 양성은 raw 12 quarter note-time 중 가운데 D4의 **1 quarter**만 조건부 설명한다. 원 member 11/nonmember 1은 그대로이며 `1/12 quarter`로 표현하지 않는다. 1개 또는 무연결 bundle은 같은 양성을 만들지 않는다.

실제 실행 전 in-memory inventory 계산은 16,206 descriptors/239 triples/71 새 chain requests가 기본 한도 안에 있음을 보여 주었다. 이것은 실행 계획 점검이며 저장 결과·음악 정확도 검증으로 합산하지 않는다. 최종 실제 수는 다음 절의 저장 report가 기준이다.

## 6. 실제 r1 실행과 결과

구현을 동결한 뒤 새 폴더 [factor-temporal-explanations-2026-10-01-r1](../../../output/factor-temporal-explanations-2026-10-01-r1)에 실행했다. [report.json](../../../output/factor-temporal-explanations-2026-10-01-r1/report.json)은 exit 0, **1,103.237084초/계산 실패 0**이며 scope/계산 integrity/분모/입력·code/저장물 불변 검사를 모두 통과했다. 전체 부모 authentic replay·저장·hash 검사를 포함한 시간이다. 아래 각 case 시간은 새 계산·저장만의 시간이며 전체 경과 시간과 동일하지 않다.

### 6.1 표본 범위와 계산량

| 작품군의 선택 문맥 | global quarter 범위 | 제시 profiles | raw triples | 조건부 descriptor×contour 쌍 | 새 bundle | 새 계산·저장 초 |
|---|---|---:|---:|---:|---:|---:|
| 베토벤 현악4중주 Op.18 No.1 IV | `[262,270)` | 1,592 | 45 | 931 | 5 | 20.900 |
| 베토벤 피아노 소나타 No.1 I | `[49,61)` | 2,040 | 17 | 1,273 | 5 | 33.471 |
| 쇼팽 마주르카 Op.30 No.2 | `[10,22)` | 2,670 | 79 | 2,393 | 10 | 35.605 |
| 코렐리 Op.1 No.1의 선택 악장 | `[32,44)` | 5,712 | 73 | 22,389 | 38 | 120.050 |
| 모차르트 피아노 소나타 K.280 I | `[18,27)` | 4,192 | 25 | 6,228 | 13 | 67.859 |

이는 **5작품군의 각 1구간**, 5문맥/15 raw lanes 검사다. 5곡 전곡 분석 완료가 아니다. 원 선언 322문맥/1,013 lanes 중 나머지 **317문맥/998 lanes는 미실행**이다. [context-index.json](../../../output/factor-temporal-explanations-2026-10-01-r1/context-index.json)에 원 context key·구간·parent ref·각 상태·시간을 보존한다.

- 원 22,969 origin variants/113 indexed groups, 1,068,810 logical paths/5,344,050 path×key tuples/106,845,950 function-shape 행 분모는 불변이다. 모든 완전 진행의 화성을 선택·평가한 수가 아니다.
- **16,206** 시간순 구성음 제시 레코드, **239** raw triple geometries를 저장했다. 실제 회원 관계 predicate **839,026쌍**을 원 분모로 보존하고 정확히 같은 값을 **3,227** 관계 레코드로 공유했다.
- 그중 **33,214** descriptor×contour 쌍은 full source/span/member/순차 contour 전제를 통과하며 **805,812**쌍은 이유를 남겨 보류했다. 조건부 쌍 수는 같은 음형을 여러 구간·화음 가정에서 재사용한 수이므로 33,214개 독립 비화성음 정답이나 confidence가 아니다.
- **71** 새 whole-chain completion은 모두 필수 두 연결이 같은 all-lane witness에 있다. 기존 **9** bundle은 exact body·typed ref를 그대로 보존했다. 새/기존 completion은 서로 다른 대안이다.
- raw 239 geometry 중 순차 방향·복귀 형태를 통과한 것은 경과형45/보조형28=73개이며 나머지166개는 형태 보류다. 73개 중 모든 full-span/member/descriptor 전제를 만족하는 대안이 있는 geometry는71개다. 음형 형태만 통과하면 모든 구간·화음 아래 NCT로 쓰는 것이 아니므로73과71을 혼동하지 않는다.
- **49,420** 설명량 templates와 **347,226** descriptor×actual-bundle 계정을 baseline/33,214 sparse override로 저장했다. **2,195** weighted group 계정에서 모든 origin/key/product의 raw/category 음가 총량을 대조했다. 서로 다른 bundle의 조건부 시간을 합산하지 않는다.
- 모든 5레코드는 `ready_descriptor_local_temporal_explanations`, 저장 5/실패 0이며 이 실행의 unknown metric ledger는 `{}`다. 일반 unknown/source/한도 보류 계약을 없앤 것이 아니며 synthetic 반례로 따로 검사했다.
- `conditional_local_contour_stage_enabled=true`는 이 계산 단계가 켜졌다는 뜻이다. 완전 NCT·강세/협화·boundary NCT·지연 해결·최종 화성/key/function/cadence·음악 정확도·training/Gold/generation/UI의 완료는 여전히 선언하지 않는다.

### 6.2 실제 음표로 보는 조건부 설명과 남겨 둔 대안

소나타 No.1 I의 선택 구간에서 실제 **C5 `[57,58)` → B♭4 `[58,60)` → A♭4 `[60,61)`**는 두 번의 순차 하행이다. source note는 각각 `note_52fc80602b9b`, `note_e1923fe52338`, `note_2e8cd0a88b1b`이며 sounding refs와 source pitch/tie/attack 자료까지 저장되어 있다.

예시 descriptor `fmiprofile_732762ffe6ad557f2c521beb`는 `[49,61)`의 D♭–F–A♭–C 구성음 **가정**이다. 이에 대해 두 끝음은 member이고 B♭4는 nonmember이며 세 full span이 모두 내부에 있다. 새 `fmtebundle_08af7b79ed9290c9ac87e8fe`에서 두 필수 연결이 함께 성립할 때 account `fmteaccount_96c9e90ec819e2cf880ca2bc`는 가운데 B♭4의 **2 quarter**만 조건부 설명한다.

| 같은 descriptor·bundle의 note-time | quarter |
|---|---:|
| 원 member | `133/6` |
| 원 nonmember | `61/3` |
| 원 전체 | `85/2` |
| 조건부 설명된 nonmember | `2` |
| 이 completion 아래 미설명 nonmember | `55/3` |

원 nonmember `61/3`을 삭제하거나 `2`만큼 member로 바꾸지 않는다. 이것으로 D♭ 계열이 실제 그 구간의 최종 화음이라는 뜻은 아니며 경쟁 화음·경계·구성음 제시의 대안이 모두 남는다. B♭를 구성음으로 포함하는 다른 descriptor에서는 같은 음형의 역할 판정이 달라질 수 있다. no-link completion에서 두 연결을 만족하는 것으로 만들지도 않는다. 이 사례는 조건부 추론의 **작동과 한계**를 보여 주며 작품별 정답 조건으로 사용하지 않는다.

읽기 전용 사례 추출의 초기 진단에서 typed `geometry_ref`/`supported_geometry_refs` 객체를 문자열 ID와 직접 비교해 `StopIteration`이 나온 2회는 진단 질의만 교정했다. 최종 typed ID로 해당 bundle/account와 가운데 2 quarter를 확인했으며 producer/data 수정이나 실제 실행 실패로 집계하지 않는다.

### 6.3 동결·출처·재현

원 grounding 부모 [report.json](../../../output/factor-grounded-relations-2026-10-01-r1/report.json)의 SHA256은 `fa37223f675e04d598f94fbd3b08becbd96b38ce5ad65bbefe134b7dac9de3ce`이며 그대로다. 새 report SHA256은 **`690ea921d9551a2fa7c88e9ff59ed1ff5db090cb68ae19317364f0d33ca7c8fb`**다. run-plan에 보호 input **4,489**개와 current producer/schema **308**개 SHA·정확 목록, 기본 한도, original selection/declared·unexecuted 분모를 저장했다.

새 출력은 run-plan/context-index/5 gz 레코드/report의 **정확히 8파일, 39,725,336 bytes**다. 첫 7개 creation SHA는 report가 참조하며 report 자신의 SHA는 이 문서에 따로 기록한다. 원 Core/XML/parser/기존 분석·부모 output/운영 악보/구조/작곡·편곡/API/Git은 변경하지 않았다.

동결 파일 SHA256:

```text
factor_temporal_explanations.py        cba63dac8c86ec79afb33d7d63832c3a45f9255a9ed16648252db377919abcb1
factor_temporal_explanation_trial.py   e8e1e41ac7fe9f434bc385c490d5eb1ca4cdc2c89fb9db108e905b2e2e3839ba
test_factor_temporal_explanations.py   80e679a2bb8922d202f795ee1a730a992664275850dca224243fe3e16d2a6bbd
test_factor_temporal_explanation_trial.py f3c0bf50c6a84f79ddc95afe86258624736607ff6e9fe2713107f432b313bfe7
```

PowerShell 재현 예시(저장된 r1을 덮어쓰지 말고 아직 없는 새 output을 지정한다):

```powershell
$env:PYTHONPATH = 'K:/Music Analysis/src;K:/Music Analysis/tests'
$env:PYTHONIOENCODING = 'utf-8'
& 'K:/Music Analysis/.venv/Scripts/python.exe' -m musicanote_harness.factor_temporal_explanation_trial --grounding 'K:/Music Analysis/output/factor-grounded-relations-2026-10-01-r1' --output 'K:/Music Analysis/output/factor-temporal-explanations-2026-10-01-r2'
& 'K:/Music Analysis/.venv/Scripts/python.exe' -m unittest test_factor_temporal_explanations test_factor_temporal_explanation_trial -q
& 'K:/Music Analysis/.venv/Scripts/python.exe' -m unittest discover -s tests -p 'test_*.py' -q
```

## 7. 최종 검증 상태

최종 동결 전체 Python 회귀는 **3,393개/1,926.964초 OK/exit 0**다. 직전 3,323개+이번 신규70개를 한 번의 `unittest discover`에서 수집·실행한 실제 결과다. 앞 단계에서 서로 나눠 실행한 결과를 이번 통합 실행이라고 바꾸지 않는다. 새 source/test 4파일은 동결 해시 그대로며 기존 producer/자료도 불변이다. 검사 출력의 fixture 경과 로그와 기존 layout encoded-break 경고는 테스트 실패가 아니었으며 해당 기존 코드/자료를 바꾸지 않았다. 검사 개수는 음악 정답률이 아니다.

독립 저장/공개 질의 검증도 **1,697.670381초/exit 0/전체 5문맥 통과**다. 새 파일을 만들거나 source/data를 수정하지 않고 메모리 안에서 점검했다.

- original 여섯 입력(IR/scope/hypotheses/index/relations/grounding)의 authentic 전체 부모 loader를 한 번 fresh replay하고 원 22,969 origins/16,206 descriptors·keys·source/profile/order·분모를 대조했다.
- 실제 239 geometries의 방향/음역/철자·full sound span/source guard, **839,026** 모든 descriptor 회원 관계쌍과 **3,227** 유한 관계 레코드를 독립 oracle로 확인했다. 회원 관계를 공유하되 원쌍이 누락되지 않는지 검사했다.
- member presentation의 원/guarded interval 합집합·additive note-time·actual attack과 첫 관측을 대조했다. 이번 5문맥의 모든 source attack ref는 literal note projection 안에 있으며, 이 표본에서는 attack 정보가 범위 밖에 있는 반례는 발생하지 않았다. synthetic guard 검사를 실제 반례 출현으로 바꾸지 않는다.
- **49,420** 모든 account templates, **347,226** 모든 descriptor×actual-bundle 계정, **2,195** weighted group 계정의 middle-only 설명 합집합/원 raw/member/nonmember/unknown 및 총량을 확인했다. 71 새 bundle의 두 필수 연결이 같은 actual all-lane completion에 있고 9 historical bundle은 exact body·typed ref가 그대로다.
- 공개 `prepare_explanations`를 각 문맥 한 번 제대로 호출하여 저장 body를 fresh 재현했다. 모든 **71새 chain bundle+5무연결 controls=76**에서 descriptor 질의76개와 origin 질의76개, **총152개**를 대조했다. 원 출처별 frozen profile body 복구도 일치했다. 이 준비/질의 과정의 645.489683초는 전체 준비를 포함하며 lookup-only/UI 응답시간으로 발표하지 않는다.
- 문맥별 oracle/공개 준비·조회 포함 시간은 현악4중주77.738초, 소나타74.362초, 쇼팽121.547초, 코렐리430.886초, 모차르트174.620초다. 앞의 r1 계산 시간과 다른 검증 실행이다.
- 독립 검토의 §6.2 소나타 source notes/정확 구간/ordered D♭–F–A♭–C·가운데2quarter·raw/member/nonmember/같은bundle이 일치했다. descriptor-vs-origin 반환과 raw-lane DP 예산 표현은 독립 문서 검토로 정확히 고쳤다.
- 감사 전후 보호 **4,489inputs/308current producer·schema/정확8출력**의 생성 시 SHA·현재 목록과 report SHA가 모두 불변이다. 주 실행 뒤 root의 별도 전수 SHA·정확 출력 목록 검사도 변경0이었다.

이번 독립 검사는 original multiplicity·조건부 축·공개 재현의 일관성을 확인한 것이다. 1,068,810개 Cartesian 경로를 펼쳐 최종 화성을 고르거나 강세/협화·NCT/cadence/음악 정확도·학습 적격을 검수한 것은 아니다. 기존 4개의 direct required bundle도 저장 몸체/모든 계정 대조에는 포함하되 이번 152개의 공개 질의는 새71+무연결5에 한정했다.

파일/문서 QA: 새source2/test2/독립개발문서1 및 기존main/log2의 **7파일** strict UTF-8·NUL/U+FFFD·줄끝 공백·Python AST, 동결 source/test SHA와3문서 **117개 로컬 파일 링크** 오류0. read-only `git diff --check` exit0이며 기존 unrelated LF→CRLF 경고는 보존했다. 원 Code/Core/UI/전체 cohort/음악 정확도를 거짓 승격하지 않는다는 독립 문서 검토도 통과했다. 인수인계 문서가 아닌 이 기록과 화성main/log를 갱신하고 기존 상세 기록은 덮어쓰지 않았다.

## 8. 다음 큰 기능 단위

다음은 **구간 경계를 넘는 NCT와 지연 해결**의 공동 근거다. 준비음/선행음/계류·재타격과 지속·원타이·실제 attack/release·대상 화음의 전후 회원 관계를 expanded envelope에서 비교하고, 필요한 여러 연결이 하나의 actual completion에 함께 성립하는지 검사한다. 한 구간 내부의 이번 경과·보조 contour를 경계에 그대로 붙여 해결했다고 선언하지 않는다.

그다음 구성음의 시간순 제시, 경계 NCT, 베이스/페달 대안, 실제 해결을 같은 문맥 진행 안에서 합쳐 화음 변화와 지속 대안을 비교한다. 여러 시점의 pitch-class 합집합을 분산화음 정답으로 삼거나 source guard를 완화하지 않는다. 운영 화면/구조/생성 연결은 해당 큰 단위의 검증 뒤 별도로 수행한다.

후속 구현의 완료 기준은 다음과 같다. 이는 이번 구현 완료 목록이 아니다.

1. 범위/관찰과 실제 진행 가정을 분리한다. 구간 밖의 음을 지금 descriptor의 구성음이라고 가져오지 않고, 경계 양쪽 후보·원span·같은 key/bundle을 명시한 새 레코드로 참조한다.
2. 준비→잔류/재타격→해결의 전체 원 sounding chain을 요구한다. 타이 지속과 새 attack, source 누락·시간 중첩·다성 lane의 대체 경로를 구별하고 각각의 불충족/unknown 이유를 유지한다.
3. 같은 completion에서 필수 연결 전체가 성립해야 한다. 경과/보조·계류/선행·지연 해결별로 서로 다른 유리한 witness를 조합하지 않고 경쟁 interpretation을 보존한다.
4. 설명받는 음/구간만 반개구간 합집합으로 계상한다. cross-boundary NCT가 설명된다는 이유로 유지/변화의 원 constituent·베이스·distinctive-member 증거를 삭제하지 않는다.
5. 양성뿐 아니라 새 attack/지속 대조, 해결 없음/지연 범위 초과, 경쟁 화음에서의 member 대조, 교차 성부·점음/grace·철자/음역·0/unknown·whole 한도 반례를 검사한다. 실제 여러 작품군의 저장/공개 결과를 재현하며 정답률은 별도 음악 검수에서 측정한다.

이번 cold 실행은 authentic 전체 부모 replay가 큰 비중을 차지한다. 이 18분여를 운영 UI의 버튼 응답 시간으로 받아들이거나 매 클릭마다 같은 전체 lineage를 재검증하는 방식으로 연결하지 않는다. 이미 구현한 owned prepared lookup과 별개로, 운영 적용 시에는 검증된 버전·source binding의 재사용/무효화 및 필요한 악보 구간만 전달하는 계약과 응답시간 검사를 추가해야 한다. 이를 위해 원 hash·출처 guard를 생략하지 않는다.
