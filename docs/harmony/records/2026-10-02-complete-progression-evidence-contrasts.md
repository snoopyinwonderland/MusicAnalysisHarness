# 완전한 진행 후보의 동일 성부 근거 비교

개발 단계: HARM-DEV-20261002-20. 화성 분석 연구용 계산이며 운영 화성 분석기의 정답 선택 단계가 아니다.

## 1. 목적과 앞 단계의 연결

[직전 단계](2026-10-02-delayed-resolution-obligations.md)는 하나의 명시 화음 변화 가정에서 이끎음·7음의 직접/지연 해결, local/boundary 음형과 원음의 구성음 여부를 동일 실제 성부 연결에서 대조했다.

이번 단계는 그 근거를 **같은 관측 구간 전체를 덮는 여러 진행 후보**로 올린다. 한 화음 유지와 중간 화음 변화, 서로 다른 근음·철자 후보, 조성 가정, 명시 기능/해결 전략의 차이를 구별한다. 각 대안이 구성음으로 받아들이는 원음, 조건부로 설명하는 비구성음, 설명하지 못한 원음, 자료 불확실성을 같이 보존한다.

설명량이 많다고 화성 정답·우승 후보·confidence를 자동 선언하지 않는다. 이끎음 해결이 가능해도 화음 구성음 제시와 베이스가 빈약할 수 있고, 원음 pooling이 많아도 실제 화성 변화나 음악적 기능을 확정하지 못할 수 있다.

## 2. 범위와 일반 규칙

- 원 색인의 **전체 구간 한 화음 유지(full hold)**와 **관측 cut 하나에서 나누는 두 화음 진행(one-cut)**만 사용한다. 각 원 partition은 같은 `analysis_span` 전체를 덮는다.
- 서로 다른 원 partition끼리 비교할 수 있다. 따라서 ‘한 화음으로 과병합했는가, 두 화음으로 불필요하게 나눴는가’에 필요한 원음/설명량의 차이를 얻는다. 같은 group으로 가장하거나 여러 one-cut을 이어 붙여 새로운 다화음 진행을 만들지 않는다.
- 비교 가능한 근거는 **하나의 등록된 실제 complete all-raw-lane witness**를 공유한다. 후보별로 유리한 성부 연결을 골라 합치지 않는다. 등록된 withheld/impossible/unknown bundle도 보류 대상으로 보존하며 그 경우 비교 가능이나 설명 완료로 선언하지 않는다. bundle 자체가 없는 경로는 부모 registry가 비었을 때만 허용한다. raw lane은 음악적 성부 역할이 확인된 성부와 다르다.
- 원 candidate origin과 spelling alternative ID를 보존한다. 같은 계산 descriptor를 공유해도 원 후보를 하나로 합쳐 없애지 않는다.
- 조표와 명시 key 가정은 확정 국소 조성이 아니다. key 후보가 unknown이거나 terminal에 후속 화음이 없어도 그 대안을 보존한다.
- 두 화음 후보의 명시 기능/해결 전략은 **검사할 가정**이다. 선택된 정답을 뜻하지 않는다. full hold에는 후속 화음 해결을 억지로 요구하지 않는다.
- 모든 시간은 유리수와 `[start,end)`다. slot별 관측을 합칠 때 원 총음가는 유지하고, 같은 sounding event의 설명 범위는 합집합으로 계산한다.
- 경쟁하는 기능 가정의 설명량을 서로 합쳐 최적 결과를 만들지 않는다. 한 path record의 계정에는 그 record가 선언한 가정의 근거만 쓴다.

현재 universe는 완전한 전곡의 임의 다화음 segmentation이 아니다. 원 관측 구간의 full-hold/one-cut 진행만 의미한다. 반복·전조·종지·예외 성부 해결을 포함한 전체 음악적 추론은 별도 후속 단계다.

## 3. 구현과 공개 계약

핵심: [factor_progression_evidence.py](../../../src/musicanote_harness/factor_progression_evidence.py).

실행기: [factor_progression_evidence_trial.py](../../../src/musicanote_harness/factor_progression_evidence_trial.py).

독립 검사: [핵심 검사](../../../tests/test_factor_progression_evidence.py), [실행기 검사](../../../tests/test_factor_progression_evidence_trial.py).

### 준비와 비교

`prepare_comparison_prepared`는 직전 단계가 발급한 authentic owned session만 받는다. 새 immutable/HMAC handle에 실제 부모 authority를 연결하고 현재의 transitive source contract를 비교 전후에 확인한다. raw `prepare_comparison`은 원 9개 입력의 실제 부모 재검증을 생략하지 않는다.

`compare_prepared(session, hypotheses, bundle_id, ...)`는 다음처럼 닫힌 selector 목록을 받는다.

```json
{
  "group_id": "원래_full_hold_또는_one_cut_group_ID",
  "variant_ids": ["첫_slot의_원후보_ID", "둘째_slot의_원후보_ID"],
  "key_id": "원래_key_가정_ID",
  "transition": {
    "family": "V7",
    "quality": "M",
    "strategy": "ordinary_role_existential",
    "declared_occurrences": null,
    "requested_explanations": null
  }
}
```

full hold는 `variant_ids`가 한 개이고 `transition=null`이다. 두 slot에는 명시 transition이 필요하다. `quality=M/m`은 가정한 **목표 3화음의 장/단조 형태**이며 확정 국소 key를 뜻하지 않는다. declared occurrence/요청 clause는 직전 계약을 그대로 따른다. 중복 selector, 외부 ID, 잘못된 slot 순서, 불완전한 범위, 등록되지 않은 geometry, 잘못된 자료형/임의 필드는 거부한다. 요청량 한도가 0이어도 잘못된 입력을 유효한 보류로 바꾸지 않는다.

### 출력

- `selector_inventory`: 요청한 모든 원 tuple·partition·origin/profile/key 참조와 가정. 보류 시에도 남는다.
- `hypotheses`: 각 완전 진행의 exact frozen profiles, 모든 slot의 5 family×2 quality 형태, 명시 transition의 실제 검사와 전체 계정.
- `function_shapes`: terminal 및 경쟁 형태도 모두 보존한다. `restored_function_shape_rows`/`tested_function_shapes`는 exact frozen 형태를 복구한 distinct 수다. `evaluated_transition_assumption_rows`는 명시 전제의 평가 수로 wrong-shape의 known negative도 포함한다. `assessed_transition_function_rows`는 실제 kernel·ordinary role inventory를 대조한 수다. 세 수를 동일한 motion 검사 완료 수로 합치지 않는다.
- `whole_path_account`: 원 구성음 분류와 총음가, 동일 completion의 조건부 설명량, sound별 credit 합집합 및 각 slot 계정.
- `axes`: 원음/source guard, literal core/bass, 과거 direct 결과, ordinary 해결, direct/boundary/delayed 적용 여부와 등록 local/boundary clause 수를 구별한다. 요청 전체 source/work 보류는 최상위 status/reasons에 남기며 그때 path 행은 만들지 않는다.
- `contrasts`: caller 순서 `i<j`의 쌍 비교. `right-minus-left` 음가 차이는 방향 표기일 뿐 선호/순위가 아니다. 동일 source/span/witness 및 양쪽 전체 계정이 있어야 비교 가능하다.
- `logical_universe`와 summary: 원 전체 진행·진행×key·function 행 분모, 실제 검사한 distinct tuple/function과 미검사량. selector 수나 비교 쌍 수를 곡 수·정답률로 바꾸지 않는다.

계정의 여섯 분류는 다음과 같다.

| 분류 | 의미 |
|---|---|
| `source_guarded_member` | 원자료 전제가 충족되는 가정 화음 구성음 |
| `conditional_combined_explained_nonmember` | 동일 실제 completion에서 등록된 조건부 근거가 설명한 비구성음 |
| `unexplained_nonmember_under_this_completion` | 이 가정·이 completion으로 아직 설명되지 않은 비구성음 |
| `unassessed_nonmember` | 필요한 실제 completion 없이 미검사한 비구성음 |
| `membership_unknown` | 철자 등으로 구성음 판정을 못한 원음 |
| `source_or_hypothesis_unsupported` | source/가정 blocker가 있는 원음 |

각 분류 합계는 원 총음가와 같다. source blocker가 있다고 원음을 지우거나 그 음가를 0으로 바꾸지 않는다.

## 4. 한도·unknown·보류

기본 한도는 hypotheses 64, unordered contrasts 4,096, 전체 요청 logical assessment work 100,000이다. 해당 요청 전체를 미리 계획하고 한도를 넘으면 **유리한 앞부분만 계산하지 않는다**.

whole hold의 hypotheses/contrasts는 비어 있지만 모든 selector identity와 원 universe, 보류 이유가 남는다. 부족한 profile/source/finite inventory로 work 총량을 알 수 없을 때도 전체 요청을 보류한다. 이는 해당 음악/화음이 실패했다는 뜻이 아니며 직전 저장 결과를 바꾸지 않는다. 다른 관측 문맥은 계속 실행한다.

이 work quota는 CPU·wall time·RSS·byte/lifetime 한도가 아니다. source/profile/가정 identity와 작은 등록 근거 inventory의 검증은 admission 전에 수행한다. unknown인 총량은 `null`, 알려진 0은 `0`으로 구별한다. 원 universe가 부분적으로 unknown이면 알려진 subtotal을 전체값으로 주장하지 않는다.

## 5. 실제 실행기의 기술 panel

실행기는 직전 r1의 동일 5개 문맥을 그대로 소비한다. 새 결과만 별도 output에 저장한다. 모든 parent 보고서·plan·stage record·원 input SHA·역대 producer SHA·목록·현재 source를 확인하고 실패 행과 미실행 분모도 남긴다. 직전 creation code inventory에는 정당한 당시 stage module만 허용하며 새 child module을 과거 plan에 소급 삽입하지 않는다.

기술 panel은 musical top-k나 대표 정확도 표본이 아니다.

1. 원 TT kernel 중 ID 사전순 첫 supported ordinary kernel과 실제 supporting bundle을 골라 **검사할 seed**로 삼는다. 없으면 첫 TT kernel과 무연결 control, TT 자체가 없으면 원 pair의 첫 후보를 사용한다.
2. seed의 원 exact 두 후보에 모든 원 key×모든 10 family/quality 가정을 붙인다.
3. 원 full hold 첫 후보를 모든 key에서 비교한다.
4. 동일 원 pair의 target descriptor가 다른 원 후보 하나를 모든 key에서 비교한다. 이것은 다른 근음/철자 등을 포함할 수 있는 descriptor probe이며 ‘항상 구성음 집합이 다른 후보’라는 뜻은 아니다.
5. 일반적인 원 5-key 자료에서는 60 selector, 1,770 unordered contrast를 요청한다. 이는 60 distinct 진행이 아니라 15 distinct 진행×key tuple이며, 보통 복구한 distinct function 형태는 250개다. shape identity는 원 tuple(key 포함)×slot×family×quality다.

selector가 2개 미만이면 별도 `fmpeprobehold_` **실행기용 최소 보류 record**를 저장한다. source 공급 부족뿐 아니라 유효한 full-hold-only/unknown-key 자료에서 selector가 하나일 때도 해당한다. 이는 core의 `compare_prepared`/`selector_inventory` record와 다르고, 생략된 세부 metric을 알려진 0으로 읽지 않는다.

seed의 사전 supported 상태는 전략별 조건부 근거의 기술 coverage를 검사하기 위한 것이다. 우승 화음·사례 대표성·기능 정확도·음악 정답률을 뜻하지 않는다. corpus/source의 화성 label을 추론 입력으로 쓰지 않는다.

## 6. 검증과 실행 기록

신규 검사·실제 실행·독립 감사·보호 SHA 확인을 서로 구별하여 기록한다.

### 6.1 신규 검사와 직전 회귀

동결 source에서 핵심 **37개/120.842초**, 실행기 **30개/124.108초**, 직전 지연 해결 핵심·실행기 **76개/340.205초**를 각각 통과했다. 이번 신규 검사는 67개이며 세 프로세스의 합계 143개를 한 번의 전체 Python 회귀로 표현하지 않는다. 실행기/직전 회귀의 outer elapsed는 각각 124.9428215초/341.0370624초다. 전체 Python 회귀는 이번 단계에서 아직 재실행하지 않았다.

검사는 exact origin/profile/function 복구, full-hold/one-cut 총음가, 동일 bundle의 major/minor 대안·무연결 반례, 모든 slot×10 형태와 terminal 보존, 반복 function selector의 distinct 분모, 명시 전략·source/work 한도·닫힌 자료형·외부/재봉인/authority 변경·부모 보존을 다룬다. genuine possible/control은 공개 registered API에서 검사했고, impossible/unknown bundle은 등록된 실제 r1에서 공개로 질의한 것으로 과장하지 않고 **순수 내부 helper 검사**로 별도 다뤘다.

핵심 초기 29개 실행은 94.754초에 27개 통과/fixture 오류 2개였다. 조표 없는 fixture에는 key가 unknown 하나뿐이고, profile hold에서는 등록 bundle이 없다는 계약을 fixture 기대가 어겼다. 실제 유효한 5-key 입력 및 bundle 없는 경로로 교정한 뒤 최종 fresh 37개를 검사했다. 실행기 초기 fixture도 key가 하나뿐이라 기술 panel이 두 후보 미만이 되어 정상 `_no_panel` 보류가 mock 비교를 건너뛰었다. fixture를 진짜 조표 입력으로 교정했으며 실패를 계산 성능 개선으로 세지 않는다.

개발 중에는 실제 kernel/ordinary inventory 없이 raw 계정만 계산한 wrong-family 대안을 `motion_assessed`로 세는 문제를 발견하고 수정했다. **가정의 형태 전제를 평가한 수**와 **실제 ordinary motion inventory를 대조한 수**를 분리한다. known shape mismatch의 원음 계정은 남기되 motion 검증 완료로 승격하지 않는다. 등록 clause identity 검증은 한도 admission 전에 한다. selector 변경과 현재 producer 계약은 prepared 비교 전후에 확인한다. raw wrapper의 한도 이름·자료형은 부모의 비싼 재검증 전에 확인한다.

### 6.2 동결 source/test SHA-256

| 파일 | SHA-256 |
|---|---|
| `factor_progression_evidence.py` | `c3c9ae28dca526093ec17e3fd395e7d6ba3123e0dfa044272b36c9ae40ffc6a2` |
| `factor_progression_evidence_trial.py` | `c2ed3b23fa6fe712cc6d79e6ae0d153144789a83e807d80ebae40cf0038e022b` |
| `test_factor_progression_evidence.py` | `eee616085e9bb239f42def0de69721975585ffd5b4ad28c7c069914300452a49` |
| `test_factor_progression_evidence_trial.py` | `0b4e4db72abe9c14d8950c178899bb61e331c9da77efdb86f7ab49b3f4e773d2` |

위 4개 source/test SHA는 실제 r1·독립 감사·최종 QA 후에도 같다. 직전 phase19의 source/test 4개도 동결 SHA와 일치한다.

### 6.3 실제 r1: 다섯 원 관측 구간

새 [실행 보고서](../../../output/factor-progression-evidence-2026-10-02-r1/report.json), [실행 계획](../../../output/factor-progression-evidence-2026-10-02-r1/run-plan.json), [문맥 색인](../../../output/factor-progression-evidence-2026-10-02-r1/context-index.json)을 별도 저장했다. **exit0 / 1,470.6946286초 / 5저장·0실패**다. 원 관측 구간 5개/15raw lanes를 검증한 것이며 다섯 전곡의 음악적 정확도를 검증했다는 뜻이 아니다.

| 원 문맥 | global quarter 구간 | 비교·저장 시간(초) | 원 총 note-time | logical work | 양성 selector / credit sound×selector 발생 |
|---|---|---:|---:|---:|---:|
| Beethoven quartet `n01op18-1_04` | `[262,270)` | 15.650634 | `53/2` | 8,640 | 0 / 0 |
| Beethoven sonata `01-1` | `[49,61)` | 31.320343 | `85/2` | 4,005 | 50 / 55 |
| Chopin mazurka `BI105-2op30-2` | `[10,22)` | 22.664079 | `75/2` | 11,770 | 0 / 0 |
| Corelli `op01n01a` | `[32,44)` | 32.277473 | `48` | 13,495 | 0 / 0 |
| Mozart sonata `K280-1` | `[18,27)` | 45.840135 | `33/2` | 5,505 | 5 / 5 |

총 note-time은 모든 관측 sounding event의 clipped 음가를 quarter 단위로 더한 값이다. 다성부 음이 겹쳐 있으므로 관측 구간 자체의 길이·음표 개수·연주 초와 같지 않다.

각 구간은 60 explicit selector·1,770 unordered contrast·15 distinct tuple×key·250 distinct function 형태·55 evaluated assumption·5 actual motion-assessed 행이다. 합계는 **300 selector·8,850 comparable contrast·75 distinct tuple×key·1,250 distinct 형태·275 evaluated assumption·25 actual motion 행**, whole-path 계정 300개와 logical work 43,415다. 5,750 displayed function body에는 selector 간 반복이 포함되며 1,250 distinct 형태와 구별한다. 모든 비교의 원 총음가 차이는 0이다.

‘양성 selector’는 조건부 설명 음가가 0보다 큰 전체 계정의 수다. Sonata에는 1sound credit인 selector 45개와 2sound credit인 selector 5개가 있어 50양성/55sound×selector 발생이다. Mozart는 5양성/5발생이다. 합계 55양성/60발생은 같은 음·가정의 반복을 포함하며 55개 독립 음악 정답이나 NCT 검수 승인 수가 아니다. 나머지 세 구간의 credit 0도 삭제하지 않는다. 등록 witness와 명시 가정이 달라지면 설명량은 달라질 수 있으며, 이 기술 panel이 모든 가능한 설명을 검색한 것은 아니다.

원 universe **1,068,810 paths / 5,344,050 path×key / 106,845,950 function 행**을 보존했다. 미검사 tuple×key는 5,343,975, 미복구 function 형태는 106,844,700, ordinary motion 미검사 행은 106,845,925다. whole cohort는 여전히 322문맥/1,013raw lanes 중 5/15이며 **317문맥/998lanes 미실행**, `cohort_complete=false`다. 8,850쌍을 원 universe 전체 검사로 표현하지 않는다.

r1 wall time에는 모든 이전 단계의 authentic cold replay와 출처·시간·현재 producer 검증이 포함된다. 위 구간별 시간도 저장·참조/불변 검사 등을 포함한다. 새 accessor의 lookup-only latency나 악보 UI 렌더링 속도로 해석하지 않는다.

실제 실행은 다음처럼 새 output 이름을 써서 재현할 수 있다. 기존 r1을 덮어쓰는 실행은 거부된다.

```powershell
$progressionTrial = @'
import sys
sys.path.insert(0, 'src')
from musicanote_harness.factor_progression_evidence_trial import run
report = run(
    'output/factor-delayed-obligations-2026-10-02-r1',
    'output/factor-progression-evidence-2026-10-02-r2'
)
print(report['summary'])
raise SystemExit(0 if report['scope_calculation_complete'] else 1)
'@
& '.\.venv\Scripts\python.exe' -c $progressionTrial
```

### 6.4 독립 저장 자료 감사와 출처 보호

독립 감사는 **전5문맥 PASS**, 실행 polling이 보고한 active 11.59초다. 짧은 호출 간 간격을 포함한 약15초 wall은 별도 계측하지 않았으므로 정밀한 전체 elapsed로 주장하지 않는다. 감사는 저장 객체를 문맥별로 읽고 frozen 순수 profile/function 투영과 **독립 유리수 interval·분류·credit union·분모·delta 산술**을 대조했다. 실제 부모 loader·owned session prepare·공개 compare의 새 cold replay는 하지 않았다. 실제 실행기의 authentic parent 재검증과 이 저장 자료 감사를 서로 구별한다.

- 300 selector의 모든 원 partition/key/origin/profile 참조와 exact function body 5,750개(반복 포함), distinct ledger를 확인했다.
- raw profile 행 발생 14,560개와 credit sound×selector 발생 60개를 원 sound의 clipped 음가·동일 registered bundle의 근거로 독립 재구성했다.
- 8,850개 모든 unordered 비교의 방향·두 hypothesis 참조·전체 note-time delta 0·각 분류의 차이를 확인했다.
- integer/`null`/boolean을 혼동하지 않는 저장 summary 및 원 실패/미실행 분모, winner/selected/rank/confidence 부재를 확인했다.
- 보호 input 4,519개와 현재 producer/schema 314개, 새8파일/직전8파일의 정확 목록·creation SHA, 실행 전 phase19 report/plan/index SHA가 일치했다. ROOT의 별도 전수 재확인도 **고유 input+code 4,521개, 새 등록7artifact 포함 4,528개, report 포함 4,529개: 변경0**이다.

별도 메타데이터 closure 대조(계측 1.2325602초)도 PASS다. 저장 core/transitive contract 5개와 현재 read-only contract, 부모 stage 참조40개, 300개 hypothesis scope/span, 275개 명시 delayed query의 scope/index/origin/key/bundle 참조와 모든 미승격 flag를 확인했다. 이 추가 검사도 공개 prepare/compare cold replay가 아니다.

새8파일은 총 **7,516,755bytes**다. 다음은 생성 시점 SHA-256이며 gzip 내부 semantic record SHA와 구별한다.

| 생성 파일 | SHA-256 |
|---|---|
| `run-plan.json` | `ef780fac21172b40c3e1c345f5c412a346752488f9f5805707b3cd5f89a05251` |
| `context-index.json` | `c2fb70eacc520cb905ce28bf3eb38ff1eddea471d4cdd45ca2baa48207e12092` |
| `report.json` | `0b1d3614a35c7753c8fb36154a50e136eda297becd5777595ae9f8c1e81847ec` |
| Quartet `fmpe_e80a35c8810502dfe953eca8.json.gz` | `d71eaafe1937d1a36dce147179a36e749d23f15b22ea1ad8e0a89fed198bc99e` |
| Sonata `fmpe_9e7d7eed751ecb5e82b6289f.json.gz` | `6c066216cf57f8645ae8557c8423bea5f770838fd6610f84ddf4fc8eb9dff3a5` |
| Chopin `fmpe_8c2a6bd18dd0a3f79a7decc7.json.gz` | `012b91b8d46468843f7b91e563f165454d99c74e1003201a0719d365e42618b3` |
| Corelli `fmpe_5333fc824a199c80a902ea19.json.gz` | `41031cbc05cefcca254d37b45c64c2567c10b16c9312540319159a7baf008597` |
| Mozart `fmpe_0a6ea648f9474ec22a56f0d2.json.gz` | `8e8c8327b41d23e80b1a8e2dd53381d03acec8e8a6995638b829a9b4e05a0d13` |

### 6.5 실제 원음이 연결된 두 계산 사례

다음은 저장 자료에서 읽은 receipt다. 공개 API를 다시 실행한 새 receipt나 사용자 음악 검수 정답으로 포장하지 않는다. 원 XML/IR과 앞뒤 문맥은 부모 자료 및 보호 closure를 통해 역추적하며 잘라낸 가짜 SOURCE annotation을 만들지 않는다.

**Sonata `01-1`: 원음을 지우지 않는 경계 설명과 full hold 비교.**

문맥 `cont_c746e2edd7221f185acf`, `[49,61)`의 `fmpepath_ed1e1c35842cff0cbc0934fa`는 `[49,101/2)`와 `[101/2,61)`의 원 partition이다. 원 후보는 `fmehseg_8411ba3591f30f3ffc1b319f` / `fmehseg_de6d24beb6174187436341dc`, key 가정은 `newkey_9cf83e185b3d35c9fdf68be8`이다. 동일 bundle `fmdobundle_3b710b74c6334fa5e02514af` 아래 E♭4(`sound_62e3ab64f929`)의 full sounding span `[49,53)`은 보존된다. LEFT에서 비구성음인 `[49,101/2)`의 `3/2`만 boundary geometry `fmbegeom_83977a0810d2757648460435`로 조건부 설명하고, RIGHT의 `[101/2,53)`은 해당 가정 구성음이다.

| 같은 원 관측 구간의 가정 | 구성음 | 조건부 설명 비구성음 | 미설명 비구성음 | 총 note-time |
|---|---:|---:|---:|---:|
| 위 one-cut path | `47/2` | `3/2` | `35/2` | `85/2` |
| 원 full hold `fmpepath_f65caaf6cb04dcf2aceb5c85` | `22/3` | `0` | `211/6` | `85/2` |

두 partition의 `fmpecontrast_76db01b35ee886355415e271`은 총음가 차이0과 구성음/설명량 차이를 저장한다. 이 첫 selector의 명시 `V/M` ordinary 전략은 **unassessed**다. 경계 근거가 `3/2`를 설명한다고 ordinary 해결 성공이나 올바른 V 화성으로 승격하지 않는 구체 사례다. 이 full hold는 사전순 첫 기술 대안이며 가장 좋은 모든 full hold를 대표하지 않는다.

**Mozart `K280-1`: 같은 구성음 계정에서 기능 전제만 바뀌는 비교.**

문맥 `cont_abd87b3d0e50ccea6e45`, `[18,27)`에서 `[18,23)` / `[23,27)`의 원 partition·두 origin·key(`newkey_ee61e5eca9b24c1391c12286`)·bundle(`fmdobundle_5db28e235b14ff9b1d971631`)을 고정한다. `fmpepath_0fbcc203940524d00f14b767`의 명시 `V/M`은 ordinary 가정이 미검사 상태이며, `fmpepath_5e088ced4b960f1ced0ecceb`의 명시 `V/m`은 해당 ordinary 전략을 충족하는 route `fmdoroute_e3b38f3f79570277f02b82d6`를 가진다. 여기서 `M/m`은 **가정 목표 3화음의 quality**로 국소 장/단조를 확정한 것이 아니다.

E5(`sound_4572034deed4`)의 full sounding span `[45/2,47/2)`에서 LEFT 구성음인 `[45/2,23)`은 그대로이고, RIGHT 비구성음 부분 `[23,47/2)`의 `1/2`만 해당 가정과 같은 witness 아래 조건부 설명한다. `fmpecontrast_fa9a5b9a4100ee91cbb21010`은 raw 구성음 분류 차이0·총음가 차이0, 조건부 설명 `+1/2` / 미설명 `-1/2`를 저장한다. 이는 최종 NCT·화음·국소 조성·cadence의 정답 선택이 아니라 **같은 관측음에서 가정별 근거를 따로 보존하는 기능**의 실제 예시다.

### 6.6 최종 파일 QA

새 source/test 4개·개발 문서3개, 총7파일의 strict UTF-8·NUL/U+FFFD·줄끝 공백 검사와 Python AST 4개·로컬 파일 링크125개가 모두 통과했다. read-only `git diff --check`도 exit0이며 해당7파일에서는 경고가 없었다. 생성/보호 SHA·목록은 §6.4의 별도 전수 확인과 동결4개/직전4개 source-test 확인으로 구별한다. 운영 적용이나 Git commit/push 완료로 표현하지 않는다.

독립 최종 문서 검수도 PASS다. 저장 보고서의 분모·complement와 위 Sonata/Mozart의 typed 참조·유리수 계정을 다시 대조했다. raw API의 모든 selector 검증이 cold replay 전에 끝난다는 과도한 문장만 실제 계약(한도 이름·자료형 선검사, prepared 비교 전후 identity/contract 확인)으로 정정했다. 코드 수정이나 부모 재실행은 필요하지 않았다.

## 7. 미승격과 다음 큰 단위

원 XML/Canonical Core/parser, 과거 output와 후보, 운영 악보 뷰어·구조 분석·생성·Git은 이번 연구 계산의 변경 대상이 아니다. 확정 화성·key·NCT·cadence·winner/rank/confidence·학습/Gold 승인도 하지 않는다.

다음에는 이 완전 진행의 근거 축을 명시 조성/적용화음/기능의 전후 문맥 및 cadence 전제로 연결한다. 설명량 하나로 후보를 고르는 대신 literal core/bass·시간순 제시·선택한 같은 성부 해결·경쟁 해석·예외/보류를 함께 검수한다. 더 긴 다화음 진행이나 새로운 segmentation은 별도 universe/예산 계약으로 추가해야 한다.
