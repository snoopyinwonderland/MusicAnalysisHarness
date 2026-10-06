# 손실 없는 화음 진행 색인과 필요 시 공동 비교

개발 ID: **HARM-DEV-20261001-13**. 정본 진입점은 [화성 개발 메인 문서](../README.md)다. 기존 [확장 문맥 가정](2026-10-01-expanded-scope-joint-hypotheses.md)의 후속 개발이며 인수인계 문서가 아니다.

## 1. 해결할 큰 문제

이전 실제 실행은 5문맥의 221개 공급 구간, 22,969개 출처별 철자 variant와 1,068,810개 논리적 진행을 계획했다. 하지만 각 진행 객체와 비교 행을 실제로 펼쳐 저장하는 방식 때문에 113group 중 110group이 전체 한도 보류였다. 실제 비교한 232path는 두 full-hold에 한정되었다. 후보 수를 줄이거나 한도를 올려 해결하지 않는다.

이번 단계의 목표는 **모든 공급 후보의 전체 조합을 보존하면서 조합 객체의 일괄 생성을 피하는 것**이다. 필요할 때 특정 완전 진행·조성 조합의 계산을 꺼낼 수 있도록 만들며, 그 질의에서 실제 경계·구성음·베이스·이끎음/7음과 하나의 전체 성부 completion을 검사한다.

다음 세 수치는 엄격히 다르다.

| 수치 | 의미 | 의미하지 않는 것 |
|---|---|---|
| 논리적 진행 수 | 각 분할 slot의 모든 variant의 Cartesian product 크기 | 계산한 진행 수/정답 수 |
| 공유 descriptor 수 | 같은 의미 입력을 재사용할 수 있는 관찰 계산 단위 | 모든 음표별 profile을 이미 계산했다는 뜻 |
| 실제 질의 수 | 명시적으로 요청하여 저장한 완전 tuple의 계산 수 | 전체 조합의 exhaustive 검증/유력 후보 선택 |

## 2. 새 계약과 기존 자료 보존

새 파일은 `factor_indexed_hypotheses.py`, `factor_indexed_trial.py`와 각각의 검사다. 기존 `factor_expanded_scope/hypotheses/trial` 및 모든 저장 결과를 수정하지 않는다. 이전 materialization 한도와 상태는 역사 자료로 그대로 남긴다.

구현 파일은 [색인/질의/동일 bundle 비교](../../../src/musicanote_harness/factor_indexed_hypotheses.py), [append-only 실행기](../../../src/musicanote_harness/factor_indexed_trial.py), [색인 검사](../../../tests/test_factor_indexed_hypotheses.py), [실행기 검사](../../../tests/test_factor_indexed_trial.py)다. 이번 전체 회귀에서 수정한 기존 [cadence 검사](../../../tests/test_factor_cadence_prerequisites.py)는 테스트 한 개의 입력 지정만 바뀌었다.

- `fmiidx_`: 전체 symbolic universe와 모든 slot/variant/key, 출처별 참조, 공유 descriptor, resource/hold와 분모.
- `fmiprofile_`: 정확히 같은 의미 입력을 공유하는 지연 계산 descriptor. 실제 profile은 질의 시 계산한다.
- `fmiquery_`: 명시 group, 순서가 있는 모든 slot의 variant ID, 명시 key를 가진 완전 tuple의 계산.
- `fmibundle_`: 새 색인의 **동일한 전체 논리 universe**를 비교 대상으로 갖는 실제 multi-lane witness. 가짜 이전 path를 만들지 않는다.

색인에는 출처별 variant ID가 각각 남는다. 같은 pitch-class set이라고 후보를 합치지 않으며, root/member 철자·순서·microtonal·blocked/unknown·공급 원점도 보존한다. 공유할 수 있는 것은 의미 계산 입력이지 후보 정체성이나 음악적 해석이다. profile의 공급 metadata는 각 원점으로 복구한다.

조표에서 만든 기존 key/reference form과 explicit unknown도 그대로 보존한다. 실제 local key 추정이나 변조 확정은 이 단계에서 하지 않는다.

## 3. 색인과 계산 순서

```text
원 IR + 검증된 새 scope + frozen 공급 catalogue
  → 모든 분할의 ordered slot과 각 slot의 전체 variant IDs
  → 손실 없는 Cartesian universe / 정확한 조합 분모
  → 공유 의미 descriptor (아직 미계산)
  → 요청된 완전 tuple + key
  → 실제 profile / 기능 형태 / 경계 성부 endpoint
  → 이끎음·7음의 공동 required edges를 갖는 전체 lane bundle
  → 같은 symbolic universe 아래 조건부 비교 기록
```

기존 전체 IR·source-clock·written pitch·attack-origin·tie 및 `[start,end)` 계약을 그대로 사용한다. 음표를 제거하거나 source/음가 오류를 NCT/장식음으로 면제하지 않는다. grace/point·미지원 음정·관측 부족은 영향을 받는 주장에 보류 이유로 남긴다.

### 공개 인터페이스

```python
index = build_index(ir, scope, hypotheses, max_variants=65536)
validate_index(ir, scope, hypotheses, index)  # fresh descriptor 재구성

session = prepare_index(ir, scope, hypotheses, index)
result = query_prepared(session, group_id, variant_ids, key_id,
                        max_motion_pairs=65536)

# 다른 후보도 실제로 materialize한 동일 bundle 아래 비교한다.
assessment = assess_prepared(session, existing_bundle, group_id,
                             variant_ids, key_id, max_motion_pairs=65536)

# 한 번의 독립 질의
result = query(ir, scope, hypotheses, index, group_id, variant_ids,
               key_id, max_motion_pairs=65536)
```

owned prepared session은 원 입력과 alias를 공유하지 않는다. 현재 producer 계약과 봉인·원 scope/IR 연결을 검사하며, 질의 때 모든 catalogue/profile을 다시 만들지 않는다. 새 검증기는 저장된 supplier의 intrinsic 재생과 출처/variant/partition/count 일치를 검사한다. 이는 frozen supplier 전체를 원 IR에서 다시 제안하는 public fresh replay와 구별한다.

준비 호출은 변경되지 않는 입력으로 직렬 실행해야 한다. 호출 전후 digest와 현재 코드 검사는 순변경을 탐지하고 반환된 session은 원 입력에서 분리되지만, 다른 thread가 준비 중 잠깐 변경했다가 원상 복구하는 ABA 동시 변경에 대한 원자적 snapshot 보장은 아니다. 이번 실제 실행은 직렬 호출과 부모 전후 digest로 수행했다. 향후 동시 호출을 도입한다면 owned copy만으로 lookup을 구성하는 추가 검증 또는 입력 lock이 먼저 필요하다.

### 완전 tuple과 한도

한 분할의 variant 하나씩을 **순서대로 모두** 지정해야 한다. 다른 catalogue의 variant, foreign key, 부분 path, 중복/누락된 slot이나 재봉인한 count 변조는 허용하지 않는다. 단일·두 구간 분할 전체 product만 표현하며, 모든 다중 분할을 지원했다고 주장하지 않는다.

색인 resource 한도는 전체 색인을 보류한다. critical endpoint/joint edge 한도는 해당 질의의 전체 motion product를 보류하며 앞쪽 몇 개만 살리지 않는다. 숫자·bool·음수의 부정확한 설정을 금지한다. 이 한도는 정확한 byte/RSS 상한이나 음악적 기각 기준이 아니다.

## 4. 동일 성부 가정의 의미

기능 형태는 기존의 ordinary V/V7/vii/vii7/half-diminished7 × 장·단 target을 검사한다. 이것이 교재 전체 화음 유형의 최종 분석 완료 목록은 아니다. 후보 member와 실제 note-time을 대조하고, rootless/extended/nontertian의 일반 member index를 보통 3/7화음 전위와 혼동하지 않는다.

직접 이끎음과 7음은 release=attack 경계의 실제 철자·옥타브·근음 도착·하행 관계를 요구한다. 각 필수음의 source guard와 실제 경계 구성음/베이스를 함께 확인한다. 서로 다른 성부 가정에서 얻은 좋은 LT/7음 연결을 사후 합치지 않는다.

모든 bundle에는 실제 materialized links와 전체 raw-lane inventory, 동일한 색인 universe와 key 분모가 명시된다. no-link completion은 대조군이지 정답 성부가 아니다. 질의에 저장된 conditional joint motion과 symbolic universe 전체에 대한 incidence 조건을 구별하며, 아직 질의하지 않은 경쟁 조합의 결과를 발명하지 않는다.

따라서 count·query·witness를 confidence, 진짜 성부 정체성, 화음/NCT/cadence·tonicization/modulation 확정으로 승격하지 않는다. rank/selected 및 학습/gold/생성 자격은 없다.

## 5. 실제 실행과 재현 계획

기존 expanded r1의 report·등록 artifact SHA·정확 파일 목록·source/producer bytes 및 원 prerequisite→family 계보를 먼저 검사한다. 선택된 원 5문맥과 모든 원 group/lane/미실행 분모를 유지한다. 원 full IR와 모든 부모를 이용해 5scope를 fresh 검증하며 기존 selector/analysis를 재실행하거나 바꾸지 않는다.

각 nonempty ready group의 storage-order 첫 tuple과 마지막 tuple을 기술 대조용으로 요청한다(같으면 하나). key는 group 순번에 따라 기존 inventory에서 순환한다. 모든 기술 표본은 같은 문맥의 실제 no-link control bundle 아래 다시 비교하며, compatibility의 계산 분모를 따로 저장한다. 이는 **유력 화음 선택/음악 ranking이 아니라 명시적인 기술 표본**이다. 모호한 음악의 판정을 위한 대표성이나 전체 조합의 정확도를 보장하지 않는다. 색인 한도·공급 미확인·empty group은 분모와 상태를 보존하고 질의를 만들지 않는다.

```powershell
$env:PYTHONPATH = 'K:/Music Analysis/src;K:/Music Analysis/tests'
$env:PYTHONIOENCODING = 'utf-8'
& 'K:/Music Analysis/.venv/Scripts/python.exe' -m musicanote_harness.factor_indexed_trial `
  --expanded 'K:/Music Analysis/output/factor-expanded-joint-2026-10-01-r1' `
  --output 'K:/Music Analysis/output/factor-indexed-hypotheses-2026-10-01-r1'
```

저장 시 creation SHA를 고정하고 끝에 다시 계산하여 변경을 보고한다. 계산 중 source·schema·부모·출력 목록이 바뀌면 완료가 아니다. 실패/중단은 별도 디렉터리에 보존하고 재실행으로 덮어쓰지 않는다. 새 index·query 저장과 기존 결과의 불변을 별도로 검사한다.

색인/실행기의 동결 source SHA256은 각각 `963700bd311e690dfb559b754e2e66149d575e305dba1cd2b11a1f318b629b17`, `a0e6f2bd87c7109339a9a5d651db6b2ea362893cf1467b45feb992816b84f88e`다. 결과는 [실제 report](../../../output/factor-indexed-hypotheses-2026-10-01-r1/report.json), [전체 선택 문맥과 참조](../../../output/factor-indexed-hypotheses-2026-10-01-r1/context-index.json), [실행 계획과 보호 SHA](../../../output/factor-indexed-hypotheses-2026-10-01-r1/run-plan.json)에 있다. 기존 output을 재실행 대상으로 사용하지 말고 새 output 이름을 지정해야 한다.

```powershell
$env:PYTHONPATH = 'K:/Music Analysis/src;K:/Music Analysis/tests'
$env:PYTHONIOENCODING = 'utf-8'
& 'K:/Music Analysis/.venv/Scripts/python.exe' -m unittest test_factor_indexed_hypotheses test_factor_indexed_trial
& 'K:/Music Analysis/.venv/Scripts/python.exe' -m unittest discover -s 'K:/Music Analysis/tests' -p 'test_*.py'
```

## 6. 검증 결과

### 코드 검사와 발견한 문제

- 새 색인/질의/동일 bundle 비교 검사 39개와 실행기 검사 27개를 추가했다. 작은 공급기에서 103개 완전 tuple의 profile/function/motion, 125개 hold×key와 103개 동일 bundle incidence를 frozen eager kernel과 대조했다. 공동 이끎음·7음 양성, 서로 양립하지 않는 경쟁 연결, source/attack·타이·반개구간·전체 한도·재봉인 변조·숫자/bool alias도 검사한다.
- source 동결 이후 관련 core/expanded/context 136개/98.561초, 실행기 27개/186.132초 OK. 초기 병행 편집 중 producer SHA guard 오류 및 잘못된 empty-group 기대는 동결 전 검사 결과이며 최종 통과 수에 합산하지 않는다. SHA guard를 완화하지 않았고 빈 group의 논리 분모 0을 유지하며 질의만 생성하지 않도록 기대를 바로잡았다.
- 첫 전체 회귀에서 기존 cadence 테스트의 순서 가정을 발견했다. raw lane은 content 기반 ID 순으로 정렬되므로 index 0이 항상 최저음 lane이 아니다. 내부 F4→E4 lane을 빠뜨리면 관측 최저/최고음 transition 두 개는 여전히 완전하여 `missing=[]`가 맞았다. 분석기를 고치지 않고 같은 fixture에서 실제 G3 bass lane을 지정해 completion에서 제외하도록 테스트 한 개만 수정했다. 원 missing/unknown assertion을 유지하고, 누락 lane 정확성·관측 extreme 불변·정상 counterpart를 추가했다. cadence 39개/10.846초와 해당 검사 12회/4.193초 반복 통과. 첫 전체 실행은 통과로 보고하지 않는다.
- 수정 테스트 SHA256: `b3cf2b65c6dde76ae19b6522faef885b7585d2edce1bc9f565bcec31bd409a13`; 해당 production source `factor_cadence_prerequisites.py`는 전후 `738e4957501afca1f33f3be3a333deb28e89480d8d81c992b69bac692f37f27f`로 불변이다.
- 테스트 한 개의 입력 지정만 수정한 뒤 source를 유지한 **최종 전체 Python 3,169개/793.347초 OK, exit 0**다. 신규 66개를 포함한다. 첫 전체 3,169개/790.857초의 실패 이력과 최종 통과를 구별한다. 검사는 계약·재현·보존 검증이며 3,169곡 또는 화성 정답 수가 아니다.

### 실제 r1 실행

`output/factor-indexed-hypotheses-2026-10-01-r1`은 exit 0, **503.896700초, 계산 오류 0**이다. 기존 5문맥/15raw lanes/16group과 전체 322문맥/1,013lanes 중 미실행 317/998을 유지했다. 새 scope의 221공급 span/22,969개 출처 variant를 모두 보존하고 16,206개의 **미계산 공유 descriptor**를 만들었다. 모든 113group이 `ready_factorized_group`이며 그중 1group은 product 0이다. 이는 이전 110group의 path 객체 생성 한도를 새 표현에서 해소한 것이지, 과거 보류를 덮어쓰거나 음악적 근거 보류를 승인한 것이 아니다.

| 실제 문맥 | 논리적 진행 | 진행×조성 조합 | 출처 variant / 공유 descriptor | 실제 기술 질의 | 동일 bundle 비교 |
|---|---:|---:|---:|---:|---:|
| Beethoven quartet op.18 no.1 IV | 53,650 | 268,250 | 2,308 / 1,592 | 32 | 32 |
| Beethoven sonata no.1 I | 118,121 | 590,605 | 3,139 / 2,040 | 32 | 32 |
| Chopin mazurka op.30 no.2 | 183,103 | 915,515 | 3,840 / 2,670 | 36 | 36 |
| Corelli op.1 no.1 | 433,912 | 2,169,560 | 7,789 / 5,712 | 64 | 64 |
| Mozart sonata K.280 I | 280,024 | 1,400,120 | 5,893 / 4,192 | 60 | 60 |
| **합계** | **1,068,810** | **5,344,050** | **22,969 / 16,206** | **224** | **224** |

각 조합의 1/2 slot과 slot당 10개 기능 형태를 반영한 논리 분모는 106,845,950이다. 실제 저장한 기능 행은 4,380뿐이다. 전체 논리 분모와 실제 질의·compatibility 분모를 혼용하지 않는다. 기술 질의는 storage-order 첫/끝 대조이며 조성 5개 전부를 매 group에서 계산한 것도 아니다. report의 `scope_calculation_complete=true`는 선택한 색인 작업과 보호 검사 완료이고 `cohort_complete=false`, `all_logical_paths_evaluated=false`, `musical_accuracy_measured=false`는 그대로다.

보호 input 4,449개/current source·schema 302개, 생성 시점 SHA를 가진 등록 artifact 12개와 별도 report까지 총 13파일/10,782,444bytes를 저장했다. report SHA256은 `76d94b81ab6e2916430cef0405fe747641b45b059160c981872bf23fc582c596`다. 이전 expanded report SHA256 `e020fcecd301d461379558c0fa905f8a15219a6069f38f2a097d9294b70ae1fa`는 그대로다. actual 저장·보호 검사의 독립 재확인과 public replay 범위는 아래에 별도로 기록한다.

### 실제 저장 독립 감사와 해석 제한

첫 독립 전체 저장 감사 53.348초 OK. 정확 13파일/12 creation SHA, 모든 4,449 input/current code 302 SHA, 이전 report 불변, 221개 catalogue의 intrinsic validation과 22,969개 출처 variant의 canonical 재구성을 확인했다. 공급 origin은 base 16,196/additional7 406/extended 6,303/augmented 64이며 unspelled 6,983개와 unknown root 7,047개도 보존한다. 모든 224개 request/query identity와 224개 assessment의 봉인/참조/flags, 문맥마다 **같은 하나의 실제 all-lane no-link control bundle** 연결이 일치했다. 두 번째 독립 목록·SHA/product 검토도 같은 분모를 확인했다.

이어 public loader의 원 full IR/부모·scope fresh 검증, `prepare_index`와 **모든 224개 query + 모든 224개 동일 bundle assessment**의 canonical fresh replay를 완료했다. end 입력/code/output 재hash 포함 400.345725초, 첫 부모 계보 loader 22.780초, query 수 32/32/36/64/60과 저장 body·봉인이 모두 정확 일치했다. 호출 후 원입력/저장 결과 불변이고 차단 사항이 없었다. 이것은 선택한 실제 표본 전체의 재계산이다. 전체 5,344,050tuple이나 모든 completion을 재계산한 것이 아니며 optional frozen supplier `propose` 전체 재생은 별도 미실행이다.

두 번째 독립 감사에서도 모든 5문맥의 부모 계보/full IR/원 source와 scope를 fresh 재생했다. 합계 239positive sounds/258기보 slot(243notes+15rests)/15raw lanes, 4개의 온전한 contiguous tie chain과 창 밖 연결만 남는 2개 linked-only 계보가 일치했다. 옛 anchor 밖 sound 199개와 옛 anchor를 넘어서는 full span 205개를 버리지 않았다. 모든 239개의 source-clock/기보 pitch/고유 attack/raw owner/source ID가 exact이며 point/grace 0, source/graph inventory 한도 보류도 0이다. `validate_index` 전부와 원 anchor 끝을 포함한 cut 533/2, 57, 17, 159/4, 91/4의 대표 `validate_query`/`validate_assessment`가 저장 body·봉인과 일치했다. 부모 chain 23.611초/full fresh load_case 103.548초, 공개 index 87.043초/query 89.593초/assessment 92.171초(공개 API 합계 268.807초)다. 두 번째 감사 끝에서도 모든 보호 SHA·13파일 목록·이전 report가 불변이었다. 차단 사항은 없으며 공급기 전체 재제안 또는 100만 진행의 exhaustive 평가로 보고하지 않는다.

표본의 query 224개는 모두 `computed_logical_tuple_not_selected`, compatibility 224개는 모두 `computed_compatibility_under_existing_bundle`다. 실제 438개 profile 사용에서 원음표-시간 행의 membership은 member 6,410/nonmember 4,232/spelling-unresolved 1,104이며 **nonmember를 확정 NCT로 바꾸지 않는다**. 4,380개 function/동일 bundle 비교 행과 motion group은 모두 보류다. function의 source shape는 true 298/false 3,362/unknown 720, target shape는 true 39/false 1,561/unknown 2,780이다. 양쪽 shape가 함께 true인 행은 0이라 critical endpoint product 계획·qualified edge·conditional joint motion도 0이다. 이는 표본이 형태 전제를 통과하지 않았다는 뜻이지 관측 이끎음/7음 해결이 실패했다거나 전체 악보에 해결이 없다는 판정이 아니다. template/key projection에 저장된 primary/parallel/applied 이름도 화음 기능의 양성 인증이 아니다.

음표-시간 행 11,746개와 세부 cell 5,584개의 full sound refs·half-open clips·state별 rational 음가/합계 및 source guard를 독립 재계산했다. 같은 원음이 여러 후보 profile에 반복 등장한 수이며 고유 음표 수가 아니다. 철자 누락 cell 4,808개, ordinary template에 대한 조건부 전위 cell 962개, bass unknown cell 450개도 유지한다. 이 cell을 확정 전위·NCT·구조적 bass로 승격하지 않는다.

최종 문서/파일 QA에서 이번 source/test/doc 9파일의 strict UTF-8·NUL/U+FFFD·줄 끝 공백과 네 MD의 상대 링크 **128개, 오류 0**을 확인했다. read-only `git diff --check`도 오류 0이고 unrelated 기존 tracked 파일의 LF→CRLF 알림은 변경하지 않았다. untracked source/test/doc는 위 별도 문자·공백 검사로 확인했다. 마지막 보호 재검사에서도 input 4,449/code·schema 302/creation artifacts 12와 output 정확 목록, 새/이전 report SHA가 일치했다.

## 7. 범위와 다음 큰 기능

이번 단계는 후보를 버리지 않는 **색인·공유 계산 기반과 명시 질의**다. 전체 1,068,810개 진행의 최종 평가·선택, 모든 조성/시간 가설의 exhaustive 비교, 분산/지연 해결의 실제 양성 확대나 음악 정확도 향상이 아니다. 113group은 5full-hold와 108two-segment이며 Corelli의 cut=65/2, 두 slot variant 수 0×146인 two-segment group 하나가 known product 0이다. 빈 group을 unknown 또는 계산 실패로 바꾸거나 유리한 다른 cut으로 대체하지 않는다.

다음에는 의미 형태/target 호환을 먼저 색인하여 같은 의미의 계산을 반복하지 않는 bulk 조건부 비교를 준비한다. source shape가 맞지 않는 조합도 명시 이유와 전체 분모를 보존한다. 그 뒤에 분산형·지연 도착·조건부 NCT/지속 베이스 및 cadence 전제의 공동 근거를 연결한다. 필요한 사용자 의견은 whole-score에서 보여줄 수 있는 실제 후보·대안·원음표와 함께 요청한다.

### 다음 단계의 구현 순서와 필수 검사

1. **별도 의미 관계 계층:** frozen 색인을 덮어쓰지 않는다. source semantic descriptor×family×장/단 target 형태를 한 번 계산하고, 철자·근음·구성음·blocker가 명시된 target type과 연결한다. PC-set 또는 root 이름만으로 cache key를 만들지 않는다. origin ID와 각 block의 multiplicity를 보존한다.
2. **전제 결과의 완전한 분할:** match/mismatch/unknown relation block을 겹치지 않게 표현하며 원 product와 key/slot/function 전체 분모로 돌아가야 한다. shape mismatch는 해당 조건부 전제의 실패이지 화음 후보의 음악적 기각이 아니다. unknown은 unknown으로 남긴다. full-hold 및 two-segment의 마지막 slot처럼 `target=None`인 terminal 함수도 빠뜨리지 않는다. 특히 마지막 slot의 terminal 행은 앞 slot의 모든 origin 수만큼 반복되므로 공유 계산에서도 multiplicity를 유지한다.
3. **실제 경계·같은 성부 가정:** 필요한 motion만 scope/정확 경계/source·target membership/실제 graph·source guard/예산에 묶어 계산한다. 고정된 하나의 complete bundle 아래 qualified link들의 공동 AND를 검사하며 다른 bundle에서 좋은 이끎음·7음 연결을 합치지 않는다. 현 `assess_prepared`가 내부적으로 alternative bundle도 만드는 비용은 별도 fixed-bundle bulk accessor에서 줄일 수 있지만, joint 한도/보류의 의미를 바꾼다면 새로운 계약으로 명시한다.
4. **동등성·검증 후 확대:** 작은 완전 universe에서 모든 행을 frozen eager 계산과 대조하고 source/target unknown·origin duplicate·철자 이명동음·terminal multiplicity·whole-budget hold·상충 bundle 반례를 검사한다. 그 다음 기존 다섯 문맥의 정확 분모에서 일반 규칙을 검증하고, 양성 근거가 있는 실제 전체 악보 사례를 만든다. storage 첫/끝의 기술 표본이나 주석 정답을 보고 유리한 후보만 남기는 방식으로 정확도를 보고하지 않는다.

Core/XML/parser, 기존 annotation·rights/split·학습 정책, 운영 악보 뷰어·구조 분석·생성기·외부 API/Git는 이번 변경 범위가 아니다. 후속 편곡 슬롯은 정확한 음표/음가와 경쟁 가정·보류를 이어받으며 아직 선택하지 않은 화음을 생성의 정답으로 사용하지 않는다.
