# 명시 해결 전략과 같은 성부 가정의 지연 해결

개발 단위: **HARM-DEV-20261002-19**. 직전 [경계 계류·선행음 근거](2026-10-02-boundary-role-explanations.md)는 동결·보존한다. 화성 분석 개발 기록이며 인수인계 문서가 아니다.

## 1. 목적과 범위

화음 형태가 맞아도 이끎음과 7음이 실제 성부에서 어떻게 이어지는지, 구성음이 경계보다 늦게 나타나는지, 여러 설명이 **하나의 동일한 전 성부 연결 가정**에서 함께 가능한지 확인해야 한다. 한 vertical slice 또는 서로 다른 성부 가정의 성공을 모아서 화음·secondary·NCT를 확정하지 않는다.

이번 단위는 원 자료와 이전 결과를 변경하지 않는 연구용 레이어다. 원 source/Canonical Core/parser·이전 output·운영 뷰어·구조 분석·작곡/편곡 생성기를 변경하지 않는다. 특정 작품·마디·사용자 정답에 따른 조건식을 넣지 않는다. 교재에서 정리한 ordinary 해결 가정을 명시하고, 실제 음표·성부 연결과 대조한다. 스타일 예외까지 모두 구현된 것으로 표현하지 않는다.

## 2. 세 층의 계약

### 2.1 물리적 관찰 목록

- 원래 indexed group의 touching LEFT/RIGHT와 pair envelope만 쓴다. 새로운 임의 구간을 덧붙이지 않는다.
- source는 경계의 LEFT 극한에서 실제 살아 있어야 한다: `start < cut <= end`. 경계에서 새로 attack한 음은 LEFT 출발음으로 세지 않는다.
- 모든 이끎음·7음 후보와 doubling, 원 sound/note 참조·철자·octave·tie/attack·clock/eligibility/consistency·guard를 보존한다.
- 같은 sound의 실제 지속과 동음·같은 octave의 재타격을 분리한다. 지속 자체에 가짜 self-link를 만들지 않는다.
- 첫 다른 음 또는 종료까지의 중립 경로를 보존한다. 상행·하행·동음의 기하 관계를 관찰하는 단계이며, suspension geometry로 제한하지 않는다.
- 첫 변화가 해결 규칙에 맞지 않으면 그 지점을 건너뛰어 뒤의 유리한 음을 택하지 않는다. 잘못된 첫 변화와 종료/미해결을 남긴다.
- 새 경로의 involved **full** sound span과 source attack은 pair 안에 있어야 한다. 범위 밖이면 해당 새 경로를 보류한다. 이전 direct 축은 원래 guard/결과 그대로 보존한다. 서로 다른 guard를 가진 두 축을 무조건 동치라고 주장하지 않는다.

관찰됐다는 것만으로 모든 이끎음 doubling에 상행 의무를 자동 부과하지 않는다.

### 2.2 명시한 ordinary 전략

| 전략 | 실제 검사 | 해석하지 않는 것 |
|---|---|---|
| `ordinary_role_existential` | 역할 안에서 qualified 경로 OR, 필요한 역할 간 AND | 한 이끎음 성공을 모든 doubling 성공으로 확대하지 않음 |
| `declared_occurrence_set` | 명시한 `(role,sound)` 발생음별 경로 OR, 지정 발생음 전체 AND | 지정하지 않은 음을 해결 완료 또는 실패로 만들지 않음 |

지정되지 않은 발생음은 개별 의무를 부여하지 않지만, 관찰과 역할 근거는 ledger에 남긴다. 전략이 요구한 빈 역할, guard 보류, 전체 inventory 미완성은 성공 조건에서 없어지지 않는다. 명시 집합 전략은 요구한 발생음만 증명하며, 빈 명시 집합으로 의무가 성립했다고 만들지 않는다. 이끎음만 지정한 부분 집합은 `declared_strategy_satisfied=True`여도 `required_role_coverage_complete=False`, `whole_ordinary_template_satisfied=False`일 수 있다. 그 부분의 조건부 설명량이 성립해도 미요구 7음·doubling의 해결까지 증명하지 않는다.

ordinary 이끎음 경로는 실제 첫 변화가 spelling/register 기준 **diatonic +1, semitone +1**, derived target root여야 한다. ordinary 7음은 **diatonic −1, semitone −1 또는 −2**, 실제 RIGHT 후보의 구성음이어야 한다. literal endpoint membership과 derived triad core 포함 여부는 별도다. extended target의 구성음으로 유지되는 carried tone도 경로 검사는 가능하지만 비구성음 설명량은 0일 수 있다.

전략 실패는 그 ordinary 모델이 성립하지 않았다는 뜻이다. 화음 부재·악곡 오류·최종 NCT 또는 다른 예외 전략 실패가 아니다. frustrated leading tone, 성부 전이, 스타일별 doubling 정책 등은 명시적으로 미평가다. raw lane을 bass/inner voice의 확정 음악적 역할로 자동 해석해 예외를 적용하지 않는다.

### 2.3 동일한 실제 completion

carry·재타격·해결과 선택적으로 요청한 local/boundary 설명의 모든 필수 edge가 **같은 실제 all-raw-lane witness**에 존재해야 한다. 역할별로 따로 가능한 witness를 합쳐 성공으로 만들지 않는다.

기존 completion body를 새로운 버전으로 재봉인하지 않는다. 새 요구 집합의 전 성부 completion을 직접 만들고, 기존 bundle은 원 body 그대로 유지한다. bulk에서 가능한 모든 선택적 NCT completion을 검사했다고 주장하지 않는다. 명시한 lazy joint 요청은 별도 technical record로 보존하며 원 bulk/session을 변경하지 않는다.

## 3. 화음 제시와 설명량

다음 축을 구별한다.

1. 원 direct 모델의 source/target 경계 core/bass/guard 전제와 보류 이유.
2. 실제 첫 변화 endpoint의 RIGHT literal membership·derived core 여부·음정·register.
3. RIGHT 안에서 구성음들이 나타나는 실제 시간순 제시와 동시 core/bass 관찰.
4. 명시한 전략과 동일 completion에서의 충족 여부.

경계에서 target core가 부족해도 이후 endpoint는 조건부 목표 후보와 맞을 수 있다. 이는 지연된 화음 제시의 증거 후보이지 pitch pooling을 통한 지속 화음 인증이 아니다. 한 역할의 해결로 전체 화음·조성·secondary·cadence를 확정하지 않는다.

local contour·경계 계류/선행음·delayed carry 설명을 **선택한 동일 실제 completion의 연결 아래 재평가**한다. 공개 질의는 등록된 기존 또는 새 bundle을 사용할 수 있고, lazy compile은 별도 새 bundle을 만든다. sound별, LEFT/RIGHT별 clipped `[start,end)` interval union을 사용한다. 같은 음시간을 중복 가산하지 않는다. raw member/nonmember/unknown·원음가·특징적 구성음과 bass/change 근거는 삭제하거나 덮어쓰지 않는다. source guard가 실패하거나 설명 대상이 이미 member면 NCT 설명량으로 credit하지 않는다. 해결 endpoint 자체를 비구성음이라고 만들어 설명량에 넣지 않는다.

## 4. 공유 계산·한도·보호

- 모든 기존 source/target/type/family/quality TT specification을 소비한다. 과거 direct 양성 3kernel이나 boundary NCT subset만으로 후보를 줄이지 않는다.
- 원 origin·catalog·descriptor·path/key/function 분모와 false/unknown/terminal complement를 보존한다. 이전 실제 10,274 TT kernel/51,370가중 형태 행 및 전체106,845,950 function-shape 행은 다른 단위의 수다.
- physical routes, exact-profile 역할 predicate, OR/AND 계획과 unique required-link 집합을 공유한다. 백만 원 origin 진행을 객체로 펼치지 않는다.
- route/depth/kernel/role/joint/new completion의 **전체 계획**을 먼저 센다. 한도 초과 시 전체 해당 축을 보류하고 유리한 prefix/top-k/pruning을 남기지 않는다.
- `query_work_budget`은 선택한 설명량·geometry 계산의 명시 작업량에 대한 admission 한도다. immutable profile 복구와 역할/선택 clause predicate 평가도 호출 안에서 먼저 수행하므로, 전체 CPU·메모리·모든 predicate 작업의 상한이라고 주장하지 않는다. 알려진 불가능과 한도 때문에 미평가인 결과를 구별한다.
- 확인된 빈 결과 `0`과 전체 계획 미정 `null`을 구별한다. 알려진 subtotal이 있어도 전체 unknown을 0으로 바꾸지 않는다. 관련 pair가 전혀 없는 경우는 해당 축의 알려진 0이다.
- authentic eight-parent 입력과 issued owned handle을 사용한다. source 계약·SHA/HMAC·immutable cache·typed closed body·정확 origin/profile·현재 producer/schema 목록을 검증한다. caller 재봉인, foreign session, stale 계약과 우회 캐시는 authority가 아니다.
- frozen dict 전용 pitch helper를 부를 때 immutable 값을 소유한 dict로 복구한다. 자료형 불일치 때문에 pitch를 unknown으로 바꾸지 않는다.
- 실행기는 부모 source replay를 한 번만 완료하고 그 소유된 handles를 계속 쓴다. 새 append-only output만 만들고 모든 실패/미실행 행의 분모를 남긴다.

구현 계약:

- [핵심 모듈](../../../src/musicanote_harness/factor_delayed_obligations.py): 물리적 목록·ordinary 역할 predicate·공동 completion·공개 query/compile.
- [실행기](../../../src/musicanote_harness/factor_delayed_obligation_trial.py): authentic 부모·append-only 저장·보호 및 분모 감사.
- [핵심 검사](../../../tests/test_factor_delayed_obligations.py), [실행기 검사](../../../tests/test_factor_delayed_obligation_trial.py).

기본 한도는 route4,096/chain16/kernel65,536/role65,536/joint65,536/new bundles65,536/query work100,000이다. 한도는 음악적 확률이나 정확도가 아니다. zero 또는 작은 한도도 같은 전체 보류 계약으로 검사한다.

공개 질의의 `finite_clause_coverage`는 요청한 local/boundary clause만 설명했는지, 등록된 유한 clause 목록 전체를 해당 witness에서 대조했는지를 구별한다. 전체 NCT 종류 또는 음악 전체의 설명 완료가 아니다. `False AND Unknown = False`, `True AND Unknown = Unknown`을 유지하며, source·예산 전체 보류를 경로 부재의 확정 실패로 바꾸지 않는다.

### 저장 집계와 공개 질의의 의미

bulk의 weighted conditional은 **그 화음 가정을 주었을 때** 명시 ordinary 역할 전략이 하나의 실제 공동 witness에서 성립하는 origin pair×key 행이다. guarded 대안이 남아 있어도 알려진 양성 witness로 existential 가정은 성립할 수 있지만, unknown 대안의 전체 개수나 모든 doubling의 해결을 확정하지 않는다. withheld는 해당 ordinary 모델에서 필요한 공동 proof가 없다고 검사된 행이며, 다른 전략·화음·음악 자체의 오류가 아니다. unassessed에는 다른 function-shape의 complement와 source/작업량/geometry 보류가 남는다. 완전 분모를 알 때 세 집계는 전체 function 행을 분할하고, 분모 자체가 미정이면 해당 전체값은 `null`로 유지한다.

bulk의 origin 질의·공동 설명량 계산 수는 0이다. 공개 질의에서 `same_completion_combined_accounts_computed=True`가 된 것은 해당 origin·조성·witness의 raw 음시간 계정을 계산했다는 뜻이다. 전역 inherited NCT/지연 해결 확정 flag는 여전히 False이며, 전곡·모든 NCT 종류·최종 화성 해석 완료를 뜻하지 않는다. 질의 작업량 보류 시 exact profiles/조성별 function은 남고 affirmative 해결·계정 결과는 `null`이다.

## 5. 검증 계획과 현재 상태

**연구용 구현·source/test 동결·신규76개·관련이전202개 검사·실제 r1·독립 저장 대조 완료.** 기존 frozen 결과를 수정하지 않는다. 최종 음악 해석·운영 적용 완료와 구별한다.

핵심 양성/반례:

- genuine held/동음 재타격 이끎음·7음과 direct subset의 공통 guard 비교.
- 역할 존재 전략과 명시 doubling 집합 전략의 서로 다른 OR/AND 결과.
- 첫 변화 실패 뒤 늦은 성공을 건너뛰지 않음, terminal/guard/fullpair-outside 보존.
- 각각 가능한 역할 edge가 공동으로 불가능한 경우 성공 0, 예산 미평가와 불가능 구별.
- incomplete target-at-cut, endpoint membership, RIGHT 시간순 제시를 별도 축으로 보존.
- 같은 NEW completion에서 local/boundary/delayed interval union과 raw 음가 합계 불변.
- caller 재봉인·foreign parent/session·stale code·invalid caps·0/unknown·실패 분모의 보존.

읽기 전용 source metadata 사전 조사에서 기존 선택 5문맥의 neutral route는 **335 source-cut occurrences/381경로/최대10edge**다. 원 부모를 완전 재검증하거나 이번 새 계산을 끝낸 수가 아니다. 전체곡/음악정답/최종 통과 수로 세지 않는다. Sonata의 source 한 개는 pair 앞에서 시작하므로 새 strict full-span 축의 보류 반례가 된다.

실제 검증은 이전 Sonata/Quartet/Chopin/Corelli/Mozart 구간을 보존해 먼저 재현한다. 전체322문맥/1013raw lanes 중 선택5/15, 미실행317/998은 이번 단위로 없어지지 않는다. 넓은 작품/편성 검증은 후속 큰 단위이며 이 5구간을 전곡 검증으로 표현하지 않는다.

### 5.1 동결 검사와 발견·교정 이력

최종 신규 **핵심50개/251.326초**는 fixture 교정 후 별도 fresh 프로세스에서 실패·오류0으로 통과했다. **실행기26개/53.135초**는 동일 동결 source·실행기 test bytes의 앞선 fresh 프로세스에서 두 번째 timed suite로 통과했다. 그 프로세스의 첫 핵심 suite는 아래 기록한 fixture 오류1개를 포함하므로, 두 suite가 각각 독립 cold 프로세스였거나 76개 모두를 한 번에 통과한 것으로 표현하지 않는다. 최종 통과 검사 합계는76개다. 핵심 프로세스의 별도 outer 계측252.106초는 module load를 포함한다. source/test 전후 SHA가 모두 같았다.

동결 전 검증에서 확인한 구현 결함은 `defaultdict(Counter())`의 callable 오류, frozen local membership/완성도 필드명 불일치, 목표 구성음이 다른 역할 memo의 정체성, 불가능한 all-lane bundle의 부분 연결 차용, unknown 요청 clause를 0으로 축약하는 AND 처리, 전체 IR 투영에서 누락된 sound가 있을 때 저장된 발생 목록을 전체 개수로 오인하는 경우다. 새 모듈 안에서 교정했으며 원 source/Core/기존 계산 모듈은 수정하지 않았다. fully source-guarded cut/core audit도 frozen eligibility-only cell 값과 별도로 기록한다.

검사 fixture·기대값 문제는 구현 결함과 구별한다. 처음 disjoint 역할을 불가능하다고 기대했던 fixture는 실제로 양립 가능해, F→E와 F→E♭ 경쟁 연결의 공동 불가능 반례로 바꿨다. source 변경 중 발행된 handle의 current-contract 거부는 정상 보호 동작이며 fresh 검사를 다시 돌렸다. work=0이라도 geometry의 closed-form 가능성이 확인된 경우는 unknown이 아니고, 명시 계정 계산의 예산 보류와 구별한다. provisional74개/264.316초에서는73통과·1기대값 실패였으며, bundle cap 아래에도 알려진 false/0 branch는 0이라는 기대값을 교정했다.

첫 final-source50개 실행은49통과·1fixture 오류/207.435초였다. incomplete source의 ready graph를 기존 frozen boundary producer가 **새 모듈 호출 전** 거부했기 때문이다. source는 그대로 두고, genuine held-graph 부모를 통해 새 전체 입력을 검사하고 ready-graph neutral 함수는 별도 직접 검사하도록 fixture만 교정했다. focused1개/1.207초 후 위 fresh 최종50개를 통과했다. 실행기26개는 동일 동결 source와 동일 실행기 test SHA에서 통과했으며 이 이전 실패를 최종 통과로 섞지 않는다.

직접 연결되는 이전 direct-grounding·local·boundary 핵심/실행기 6suite **202개/847.427초 OK/exit0**도 한 번의 통합 실행으로 확인했다. PowerShell outer 계측849.4433394초와 unittest 시간을 구별한다. 신규76개와 이전202개의 통과 합계는278개지만, 278개 한 번의 실행이나 전체 Python 재검사로 표현하지 않는다. 전체 Python은 이번 단위에서 다시 실행하지 않았으며, 직전 동결 단계의3,453개 통과 기록은 별도로 보존한다.

| 동결 파일 | SHA256 |
|---|---|
| `factor_delayed_obligations.py` | `64484f8460bb9f5cff4d4e9b2fa77152baaa67ad8ca3056c02d0508e9c40ebbc` |
| `factor_delayed_obligation_trial.py` | `b5d5680178e8b3e332f16291d2af59f535c5829ca32c2e9f0b7328e43f524675` |
| `test_factor_delayed_obligations.py` | `ecdb8d6611a8d1fdb296437292201dd6f5d4392fcb0bf16a48121318341504fd` |
| `test_factor_delayed_obligation_trial.py` | `392fd915bfccfb3b154bf07dbaebce0cbf4c20ccd1dfa1ba00b9167a1263fbe4` |

### 5.2 실제 r1과 정확한 집계 단위

[실제 실행 보고서](../../../output/factor-delayed-obligations-2026-10-02-r1/report.json), [실행 계획](../../../output/factor-delayed-obligations-2026-10-02-r1/run-plan.json), [문맥·artifact 색인](../../../output/factor-delayed-obligations-2026-10-02-r1/context-index.json). exit0, **1,152.8614031999605초**, 5저장/0실패다. 보호된 이전 계층을 한 번 cold 재검증한 시간과 새 저장·마지막 SHA 검사를 포함한 실행기 시간이지 UI/lookup-only 응답 시간이 아니다.

| 문맥 | source-cut 발생 목록 | neutral 경로 / 최대edge | TT kernels | 역할 경로 options | 공동 choices | 새 / 기존 bundle | 조건부 가중 행 / withheld |
|---|---:|---:|---:|---:|---:|---:|---:|
| Beethoven Quartet n01op18-1_04 `[262,270)` | 50 | 50 / 10 | 533 | 158 | 33 | 4 / 43 | 165 / 2,500 |
| Beethoven Sonata 01-1 `[49,61)` | 56 | 68 / 3 | 763 | 536 | 57 | 5 / 17 | 285 / 3,530 |
| Chopin BI105-2op30-2 `[10,22)` | 46 | 80 / 2 | 1,943 | 887 | 0 | 0 / 19 | 0 / 9,715 |
| Corelli op01n01a `[32,44)` | 128 | 128 / 3 | 4,330 | 1,826 | 179 | 11 / 58 | 505 / 21,145 |
| Mozart K280-1 `[18,27)` | 55 | 55 / 1 | 2,705 | 729 | 50 | 2 / 16 | 250 / 13,275 |
| 합계 | **335** | **381 / 전역최대10** | **10,274** | **4,136** | **319** | **22 / 153** | **1,205 / 50,165** |

335는 원108touching pair에서 source-cut에 살아 있는 발생 incidence이며239unique sounding facts나곡수가 아니다. 381은 첫변화/terminal까지의 경로,4,136은 source 역할 predicate에 걸리는 경로 option incidence, 별도 역할 predicate 정의는16,395개다. 319 공동 choices는22distinct required-link 집합의 실제 all-lane bundle로 공유되며 이번 자료에서는 모두 geometry 가능이다. 불가능/unknown 반례는 신규 synthetic 검사에 있고, 실제5문맥에 unknown bundle이 나온 것으로 쓰지 않는다. `max_planned_chain_edges`의 보고서 정수 subtotal19는 문맥별최대10+3+2+3+1의합이며전역최대가 아니다.

모든 기존10,274TTspec/51,370eligible weighted행을 보존했다. 전체 function 분모는 **1,205conditional +50,165withheld +106,794,580unassessed =106,845,950**이다. conditional은241TTkernels×5key후보의 가정별 중복행이며,319choices·22bundles·악곡수/음악정답/confidence와 다른 단위다. source-cut literal core/bass·endpoint·뒤 구성음 제시는 별도이며양성의자동화성선택은 없다. Chopin의0은 이 ordinary 전략에 대한 확인된0이지자료미정 또는음악오류가 아니다.

원22,969origin·16,206descriptor·1,068,810논리paths·5,344,050path×key와 전체322문맥/1,013raw lanes 중 미실행317/998은 유지됐다. bulk origin질의/공동설명량/명시occurrence집합/예외전략계산은각각0이며,공개검사와구별한다. `selected/rank/confidence=null`과최종화성·NCT·조성·cadence·Gold/학습·생성·운영미승격을 유지한다.

### 5.3 출처와 생성 파일 보호

실행 plan은4,509input paths/현재312producer·schema를 보호하며중복을제거한고유input+code는4,511개다. 정확8생성파일의크기는17,176,998bytes이다. 실행 전 생성SHA를 이후자료로새로덮어쓰지않는다. ROOT별도전수검사에서도input/code/artifact고유4,518개파일SHA·currentcode목록·정확8출력목록 불일치0,보고서creationSHA별도확인이다.

| artifact | SHA256 |
|---|---|
| `report.json` | `cee0af597cf8004915554ecb2ad3639e83c22943ef9d39a70092c31670b0e311` |
| `run-plan.json` | `70d8312ab1917fdfd702a545bb2ebf2ea6f0fcf3f7b8e7b22d90841c1dca7f9d` |
| `context-index.json` | `04bbebf5738c4351adad9cf83123ab6656ef2391814411826a7dcc89f275c06b` |
| Quartet `fmdo_179eff51c48633b2f9d173f1.json.gz` | `ed9c44b9fab95febdb30e7861e50b0bfc13e5affd1f9d3dbcdd2154d4025e906` |
| Sonata `fmdo_d65cec0e707e930e437b47c4.json.gz` | `570aafcd2e8b5c8a4633da69f8501241dee15c0a37c63804d237dedb3bf45d4c` |
| Chopin `fmdo_395d9cf7852d93c322b98611.json.gz` | `a94c59141270d9dff58c78434ec694c715f19855a9f3872828b3452a198cdd50` |
| Corelli `fmdo_fb159c83ec44133bc86ee736.json.gz` | `a53af1a2bdb5333edbebe68573e49cbc4285521d3cf0797d8feee7bf0b9700df` |
| Mozart `fmdo_28d85793bd9b40196a91b2a2.json.gz` | `c8e7740e89e1f54085af1ed40aca92cc369bf2ce6db66e13a83fcd58b61c87fe` |

### 5.4 실제 원음표의 조건부 사례 — Quartet

독립 **공개 query**에서 검사한 Violin II의 printed m132→133이다. 악보의 source facts와 candidate를 구별한다.

| 원음표 / sound | pitch | 실제 quarter span |
|---|---|---|
| `note_f6641f5dcdce` / `sound_8626cdff1479` | C5 | `[263,527/2)` |
| `note_28ae306e5050` / `sound_68bd23b0addb` | C5 재타격 | `[527/2,264)` |
| `note_9ce6e2098c7f` / `sound_bde5c0edb2b8` | D♭5 | `[264,529/2)` |

raw lane은 `part_225c5c3cef38/voice_a51d43ef72ce`이고 cut은 `527/2`다. 두 실제 링크 `sound_8626cdff1479→sound_68bd23b0addb→sound_bde5c0edb2b8`가 동일한 complete bundle 안에 있어야 한다. 첫 변화 C5→D♭5의 diatonic/semitone은+1/+1이다. 주어진 후보 C–E♭–G♭→D♭–F–A♭에서의 ordinary 이끎음 경로라는 **조건부 증명**이지 실제 화음·조성의 정답 선언이 아니다.

재현 selectors: group `fmehgroup_ee6bb245a73f65625fd2cbce`, LEFT/RIGHT origins `fmehseg_43b3c9d1f8090ad3d9b18e40` / `fmehseg_42e3bf18ad5bfedc3fa04c6b`, key `newkey_dc6e435f5287ac4bef6c8cc6`, family/quality `vii/M`, kernel `fmdokernel_3ed4a397e26b76f36b31cc11`, route `fmdoroute_bd781e3a0f792914ad3c73d5`, bundle `fmdobundle_439ccb4fb5719aea18d73708`. 공개 query ID는 `fmdoquery_7abc5e0f4f5695e98d27772b`다. 이 참조들은 원 IR·공급 후보와 연결되며 작품 전용 코드 조건이 아니다.

LEFT raw 음시간은 member5/2 +nonmember7/2 =total6, 조건부 credit0이다. RIGHT는 member19 +nonmember3/2 =total41/2이며 가운데 재타격 `[527/2,264)`의 **1/2quarter만** union credit로 설명한다. 남은 nonmember1quarter는 설명되지 않은 것으로 남는다. 해결 endpoint 자체는 비구성음 설명량에 넣지 않는다.

이전 direct 상태는 withheld다. source-cut에는 E♭ core가 부족하고 A♭ bass는 nonmember이며, target-cut에는 D♭/F core와 member bass가 부족하다. 뒤의 guarded literal target-core `[264,270)` 관찰은 별도 축으로 남겨 두므로, 위 경로 양성으로 그 보류를 지우거나 계속 유지되는 화음을 인증하지 않는다.

### 5.5 실제 원음표의 조건부 사례 — Sonata

Beethoven Sonata01-1 문맥86의 printed m13→14다. 이 예는 **독립적으로 일치 확인한 저장 body의 실제 경로·음시간 산술**이며, 새 공개 query receipt를 추가 실행한 것으로 세지 않는다. 해당 conditional kernel의 모든5key는 위 공개 cohort 검사에 이미 포함됐다.

후보 E♭–G–B♭–D♭ `[49,305/6)`→A♭–C–E♭ `[305/6,61)`, family/quality `V7/M`, cut=`305/6`이라는 가정을 준다. 아래 span은 **sounding event 전체 지속**이며 개별 notated note 하나의 음가로 오인하지 않는다. 원 tie/note 정보는 이전 IR/부모 참조에서 보존한다.

| 역할 | 원 note 참조 / sound | pitch와 실제 sounding span |
|---|---|---|
| 이끎음 source | `note_409df3e18079` / `sound_c06632d0913f` | G4 `[49,53)`, cut을 넘어서 실제 지속 |
| 이끎음 endpoint | `note_f609dc1060e3` / `sound_7828a96022b7` | A♭4 `[53,57)` |
| 7음 source | `note_e07ae5076fc3` / `sound_ba0fa309391c` | D♭5 `[152/3,305/6)` |
| 7음 endpoint | `note_468106ff1d67` / `sound_0fcb664c2818` | C5 `[305/6,51)`, 경계에서 직접 해결 |

이끎음 route `fmdoroute_a0b8da957345d3c3fc2082a5`와7음route `fmdoroute_b6963cb0878aec467c0dc178`가 **같은** bundle `fmdobundle_a729f90c8033bd9528ed64bb`에 있다. G4의 실제 지속에 가짜 self-edge를 붙이지 않는다. 원 group `fmehgroup_ad2034155764f0185f8426af`, LEFT/RIGHTorigins `fmehseg_9430bcaff033c394b14982c5` / `fmehseg_3cdc03286c897942121d8b2c`, descriptors `fmiprofile_43371de51875239b2dcdb8b9` / `fmiprofile_27c91624d9a80260490ecc90`, kernel `fmdokernel_f7d63d94a6fdb0ec4bb35662`로 재현한다.

LEFT raw member/total22/3, nonmember0, credit0이다. RIGHT는 member37/2 +nonmember50/3 =total211/6이다. G4 `[305/6,53)`의 **13/6quarter만** 조건부 union credit이며 나머지29/2quarter는 unexplained로 남는다. 이 saved-account 산술에서 local/boundary가 추가 credit을 만들지 않는다. 동일 complete 무연결 control `fmgrbundle_80bdbc30550151318a39f16a`는 ordinary=False, RIGHTcredit0/unexplained50/3이며 rawtotal은같다.

source-cut core는완전하지만 target-cut에는A♭가없고B♭bass는nonmember다. 이후 fully guarded literal target-core `[164/3,329/6)`, `[55,57)`의 관찰은 따로 둔다. 이전 direct의 `withheld_direct_motion_prerequisites`는바뀌지않는다. 위13/6credit으로계속유지되는E♭7→A♭화성·비화성음·종지정답을확정하거나raw음을삭제하지않는다.

### 5.6 독립 검사의 범위와 시간

독립 실행은 원 authentic 부모를 **한 번 cold 재검증863.827799초** 후, 새 source 동결 SHA를 확인한 다음 각 문맥을 순차적으로 검사했다. 5문맥의 finite/public oracle **496.769870초**, 저장된 child body·출처·목록의 최종 대조 **7.561262초**, 합계 active audit 시간 **1,368.158931초/전5문맥 PASS**다. 대기 시간을 합산한 총 wall이나 실제r1 실행기 시간으로 읽지 않는다.

원335발생/381경로·첫변화/terminal·fullpair/clock/spelling/sourceguard, 전체10,274TTspec·16,395역할predicate·4,136routeoption·319OR×ANDchoices/22새bundle, 원153bundle의body, literal cut/core/bass/time축과 weighted complement를 독립 대조했다. 실제 source 및 부모 inventory는 완전했고, NEW22geometry는 모두 가능이었다. synthetic에서 검사한 작업량/불가능/unknown 반례를 실제 corpus 결과라고 합쳐 쓰지 않는다.

공개 질의의 정확한 분할은 **1,518 =1,205양성 semantic kernel×key +301무연결 control +12명시 occurrence 집합**이다. 301control에는 양성241kernel의무연결대조와별도음형/시간반례60개가 포함된다. 그60개를다시더하지않는다. 별도12lazycompile요청에서15실제bundle assessment가나왔으며, 합계1,533function/query bodies·3,066exact frozen profiles와 per-sound union/raw음시간 불변을 확인했다. 이는241양성TTkernel의전5key와선택한control/declared/compile검사이며,전체100만path·모든origin/key/bundle조합전수검사는아니다.

실제r1이저장되기전에독립 expected bodies를 만들었고,저장후 **5개 전체body와typedref/digest가모두일치**했다. protected4,509inputs·312producer·exact8output/17,176,998bytes·모든7ancestor의원output목록/creationSHA도일치했다. 재실행된source계약이나output을현결과에맞춰고쳐인증하지않았다.

메모리에서는 cold loader가 먼저 5개 old issued handles를 보유했다. 이후 case별 authentic handle→새 body→finite/public 검사를 완료한 뒤 해당 old/new authority와 중복 snapshot을 해제해, **5개 new 세대까지 5개 old 세대와 함께 누적 보유하지 않았다.** 중립 metadata로 source authority를 대체하거나 cold 부모 재생을 우회하지 않았다. 이 운영 조정은 논리 schema/음악 판정 변경이 아니다. 저장 대조와 사례 기록 후 독립 audit 프로세스도 exit0으로 종료해 캐시나 helper 파일을 남기지 않았다.

### 5.7 최종 문서·출처 QA

새 source/test4개·개발문서3개의 strict UTF-8/NUL/U+FFFD/공백과4Python AST,3문서의123로컬파일링크를검사해오류0이다. 새4source/test동결SHA·현재312producer/schema목록·정확8출력목록과input/code/artifact/report고유4,519개creationSHA를최종재확인해변경0이다. 독립 문서 spot check에서 실제 Quartet/Sonata의음표·sound음가·동일bundle·계정·조건부표현과검사실행구분도일치했다.

읽기전용 `git diff --check` exit0이다. 기존 별개 tracked파일5개의LF→CRLF경고는보존했으며line-ending정리나Git변경을실행하지않았다. 첫shell QA command의인용문법오류는실행전ParserError로끝났고,read-only inlinecode의PowerShell인용을고친후위검사를완료했다. source/계산결함이나테스트실패로세지않는다.

## 6. 후속 완료 기준

이번 연구 단위의 계약·검사·실제 저장·독립 감사는 완료했다. 다음 큰 단위는 이 근거를 **동일한 완전 진행의 경쟁 화성·조성/기능 설명**에 연결하는 것이다. ordinary 경로 한 개나 가정별 중복 수로 winner/confidence를 만들지 않고, 원음·literal core/bass·NCT·전후 해결·보류가 같은 진행/witness에서 함께 설명되는지 대조한다. 예외 전략/성부 전이·전체 Python 회귀·더 넓은 작품/편성 및 음악 검수는 운영 승격 전에 구별하여 검증한다.

이후 조성/기능·cadence의 강한 필수 전제, 더 넓은 작품군/편성, 독립 음악 검수, 운영 악보 레이어와 사례 피드백을 구분하여 진행한다. 생성기·편곡 성능 개선을 이번 계산 수만으로 선언하지 않는다. 원 source/Canonical Core/parser·기존 output·운영 악보 뷰어·구조 분석·생성 및 Git을 이번 단위로 변경하지 않았다.
