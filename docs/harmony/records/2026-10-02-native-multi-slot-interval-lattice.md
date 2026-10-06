# 여러 화음의 완전 진행을 위한 native interval lattice

개발 단위 `HARM-DEV-20261002-22`. 정본은 화성 [메인 개발 문서](../README.md)와 [개발 로그](../DEVELOPMENT_LOG.md)에서 연결한다. 기존 phase21 결과를 덮어쓰거나 운영 분석기의 정확도 향상을 선언하는 문서가 아니다.

## 1. 목적과 이번 범위

기존 factorized 공급은 전체 구간과 각 cut의 prefix/suffix만 있었다. 세 구간 `[a,b)→[b,c)→[c,d)`을 비교하려면 실제 중간 `[b,c)`의 공급과 새 완전 partition 계약이 필요하다. 기존 origin을 잘라 쓰거나 두 one-cut의 유리한 결과를 이어 붙이면 후보 출처와 성부 가정이 달라진다.

이번 구현은 다음을 제공한다.

1. 원 IR의 관측 endpoint grid 위 모든 양의 `[point_i,point_j)`에 대한 fresh 후보 공급.
2. 모든 완전 partition의 slot 수별 정확한 DAG count. 실제 진행 객체는 요청한 것만 계산한다.
3. 세 화음 이상을 포함하는 명시 complete selector와 하나의 등록된 전 raw-lane completion.
4. 원음표·tie·유리수 음가의 전체 계정, 실제 연결의 첫 음높이 변화, 조건부 기능·전위·종지 전제.
5. 조합·질의 한도와 전체 보류, immutable owned session, fresh 재검증 및 별도 저장 계약.

**아직 통합하지 않은 큰 부분:** 새 arbitrary partition에서의 local NCT·경계 계류/선행음 credit union. 기존 NCT 계층을 삭제한 것이 아니다. 이전 단계의 origin/completion은 새 내부 interval 계약이 아니므로 credit를 그대로 붙이지 않는다. 이번 계정의 `NCT_credited_note_time_quarters=null`은 미평가이지 0개 NCT 판정이 아니다. 이후 같은 새 completion에서 그 전제와 음가 합집합을 재계산해야 한다.

전체 전곡 탐색, 승자/점수/신뢰도, 국소 조성 확정, 최종 Secondary/NCT/Cadence, 학습/Gold 및 작곡·편곡 출력은 이번 단위의 범위가 아니다. 원 XML/Canonical Core/parser, 운영 악보·구조 분석·생성 코드와 Git 상태는 바꾸지 않는다.

## 2. 새로운 후보 공간과 출처

원 scope의 모든 sounding fact의 **full** start/end 중 전체 분석 span 내부에 있는 좌표를 사용한다. Analysis-source eligible 음만 골라 cut을 만들지 않는다. Grace/point와 source 보류도 원 관측을 유지하며 metric grid나 작품별 마디를 새 cut으로 넣지 않는다. 모든 좌표·clip·duration은 기존 유리수 계약과 `[start,end)`를 따른다.

좌표 수 M이면 실제 공급 구간 수는 `M(M−1)/2`이다. 각 구간은 `catalog.propose(ir, interval, full_analysis_span)`에서 다시 공급하고 provider pointer, 후보 번호, 모든 spelling alternative 및 spellingless origin을 보존한다. Provider가 같고 root/members가 같아도 provenance가 다른 origin은 서로 지우지 않는다. Enharmonic spelling을 PC로 축소하지 않는다.

새 식별자는 `fmilat_`(lattice), `fmilcat_`(interval), `fmilorigin_`(native origin/segment), `fmilbundle_`(completion), `fmiltuple_`(complete selector identity), `fmilpath_`(path), `fmilfunction_`(전환 전제), `fmilcompare_`(비교)다. 기존 `fmeh`/indexed path를 reseal하거나 legacy view를 위조하지 않는다.

Key는 원 fresh supplier의 조표-compatible reference forms와 unknown을 그대로 쓴다. 유효한 단일 조표의 경우 major, natural minor, harmonic minor, melodic minor ascending, unknown의 **총5개**다. 이것은 다섯 국소 조성을 알아냈다는 뜻이 아니며 mode hint를 추론 정답으로 삼지 않는다. 이번에는 새 key universe를 늘리지 않았다.

순수 profile/function/boundary/metric/degree/inversion/terminal/cadence kernel은 재사용한다. Literal boundary는 원 full scope의 관찰이므로 기존 순수 kernel의 observation ID/version을 유지할 수 있다. 이것이 이전 path나 prepared authority를 확장했다는 뜻은 아니다. 새 path/origin/bundle refs는 native 계약으로 연결한다.

### Source authority의 경계

`build_lattice`는 `expanded.check_scope(scope, ir=ir)`로 full IR binding·원음 source projection·geometry를 fresh 대조한다. `prepare_lattice`의 owned state는 그 입력에서 재구축된 새 결과를 보유한다. 이 API만으로 **현재 호출에 주어지지 않은 과거 parent 파일의 전체 음악 계산을 재실행했다**고 주장하지 않는다. 파일 SHA/저장 lineage 대조, 현재 IR/scope fresh replay, 이전 authentic parent cold replay는 서로 다른 검사다.

Producer contract는 native source, 실제 provider/template 소스, scope/schema와 재사용 context kernel의 transitive contract를 포함한다. 같은 checksum을 붙인 caller 수정 문서만으로 authority를 얻지 못한다.

## 3. DAG count와 분모

좌표 i에서 j로 가는 edge의 weight `w(i,j)`는 해당 **fresh supplier의 origin/spelling 대안 수**다. Root 종류나 서로 다른 음악적 화음 수가 아니다. 누락된 구간의 weight `null`은 공급 미계산이며, 계산한 빈 공급의 0과 구별한다.

`P[j,k] = Σ P[i,k−1] · w(i,j)`를 slot 수별로 계산한다. Cartesian 진행 목록을 만들지 않는다. 미계산 edge를 포함한 skeleton 수와 알려진 weighted subtotal을 함께 보존한다. Certified zero edge를 포함하면 그 skeleton은 unknown prefix가 있어도 곱이 0이다. Bool/float/negative weight를 정수 0이나 1로 받아들이지 않는다.

구간 수 k의 `P_k`가 알려진 경우:

| 값 | 정확한 의미 |
|---|---|
| `partition_skeletons` | 해당 k의 cut 조합 수 `C(M−2,k−1)` |
| `logical_paths` | origin 대안이 가중된 complete partition 수 `P_k` |
| `logical_path_keys` | `K·P_k`, K는 unknown 포함 key 후보 수 |
| `slot_occurrences` | `k·P_k`, key 가중 전 |
| `internal_transition_occurrences` | `(k−1)·P_k`, key 가중 전 |
| `internal_function_shape_rows` | `10·K·(k−1)·P_k` |
| `terminal_inclusive_function_shape_rows` | `10·K·k·P_k` |

10은 ordinary family5×target quality2의 형태 대안이다. 그 형태가 실제 연결이나 기능으로 성립했다는 뜻은 아니다. Transition-assumption vector 전체를 평가한 수도 아니며 `transition_assumption_vectors_materialized=0`을 유지한다. 전체 skeleton은 `2^(M−2)`다. 미계산 행은 `null`을 보존하고 큰 정수 count를 정확도·확률·곡 수로 표시하지 않는다.

## 4. 명시 진행과 하나의 실제 completion

Selector는 닫힌 형태다.

```json
{
  "origin_ids": ["native_origin_slot_1", "native_origin_slot_2", "native_origin_slot_3"],
  "key_id": "registered_original_key",
  "transition_assumptions": [null, {"family": "V7", "quality": "M"}]
}
```

모든 origin은 그 owned lattice에 등록된 원 대안이어야 한다. Positive ordered spans가 분석 구간 처음부터 끝까지 gap/overlap 없이 덮어야 한다. Foreign/duplicate origin, reverse order, 잘린 부분 partition, 빠진 전환 vector를 거부한다. `null`은 보통 진행에 ordinary dominant 해결 전략을 강요하지 않는다는 뜻이다. 예를 들어 ii→D7 단계는 미평가로 남기고 D7→G 단계만 V7/M의 ordinary 가정으로 대조할 수 있다.

`compile_bundle_prepared`는 **원 전체 scope의 모든 raw lane**의 graph에 필요한 링크 전체를 요청한다. 모든 lane의 실제 sparse witness가 등록되고 실제 links가 요청 union과 정확히 같아야 complete이다. 같은 lane에서 individually 가능한 두 요청도 한 source의 fork/두 source의 merge가 충돌하면 공동 completion은 보류한다. Pair witness를 독립적으로 합치거나 가장 가까운 음높이를 실제 성부라고 만들어 넣지 않는다.

Bundle ID만 복사해서 다른 session에 등록할 수 없다. 공개 반환값은 owned immutable snapshot을 바꾸지 못한다. State의 type·immutable storage·발급 handle/state identity·HMAC와 현재 producer contract를 확인한다. Dataclass copy로 state를 바꿔치기해도 인증되지 않는다.

### Actual first-change ordinary 전제

Cut 직전 살아 있는 source 이끎음/7음의 모든 occurrence를 기록한다. 한 tied sound의 지속은 self-link가 필요 없지만 다음 sound로의 재타격·해결은 그 **같은 bundle의 actual links**만 따른다. 첫 다른 full written pitch가 불리하면 그 뒤 유리한 음까지 건너뛰지 않는다. Endpoint는 즉시 다음 slot 내부와 겹치고 exact-spelled member여야 한다.

이끎음은 given derived root로 diatonic+1/semitone+1, 7음은 diatonic−1/semitone−1 또는−2의 ordinary 가정이다. Full source clock/pitch/attack/point guards를 유지한다. 역할 내 occurrence OR, 역할 간 AND를 사용하며 모든 doubling의 해결이나 보편적인 작법 금지를 주장하지 않는다. 같은 피치의 재타격 route도 실제 연결에서만 인정한다.

Guarded pooled core, explicit key coordinate, actual raw lowest guards, source/target shape, 같은 complete bundle, ordinary 전체 전제를 따로 저장하고 three-valued AND로 연결한다. Cut 순간 전체 구성음이 동시에 있어야 한다고 강제하지 않으며 pooled core 성공도 그 cut의 실제 화성 시작 증명은 아니다.

Before/at bass·upper, conditional degree/inversion, attack/tie, full release와 관찰 horizon, PAC/HC/IAC의 nominal 전제도 같은 path에 남긴다. Literal highest는 main melody가 아니고 lowest는 structural bass가 아니다. 국소 조성·구조적 성부·호흡/협화·performed timing 등이 미확립이면 cadence는 여전히 `confirmed=false`다. Nominal 전제가 통과해도 이번 계층은 최종 Cadence 판정을 출력하지 않는다.

`all_transitions_functionally_assessed`는 모든 내부 전환에 ordinary 가정이 **선언**됐다는 의미다. Full-hold에서는 내부 전환이 없어 공집합 조건상 True일 수 있다. 모든 key/function 전제가 충족됐다는 뜻으로 사용하지 않으며 실제 joint truth·undeclared count·각 전환 status를 따로 본다.

## 5. 원음가 보존과 한도

각 slot의 raw profile을 fresh origin으로 계산한다. 원 full sound span과 slot clip을 구별하고 source note refs, tie chain, attack을 유지한다. 전체 path의 clip 음가 합은 scope의 실제 positive sounding note-time 합과 같아야 한다. 여러 성부 overlap은 각 sound의 시간을 합하므로 elapsed span 길이와 다르다.

같은 tied sound가 두 cut을 넘으면 세 slot에 clip이 생길 수 있지만 전체 duration은 한 번만 합산된다. 원음/비구성음/미정·source 보류 state는 지우지 않는다. 경쟁 full-hold/one-cut/three-slot의 raw total은 같아야 한다. Provider ornament 표시를 joint NCT credit로 자동 사용하지 않는다.

Builder 기본 한도는 interior cut64/catalog1024/origin200000/DP work200000이다. Planned span 수와 DP recurrence 수 `M(M−1)(M+1)/6`를 먼저 확인한다. Grid/catalog/DP/source inventory 한도 보류는 supplier prefix를 만들지 않는다. 이때 모든 `i<j`라는 symbolic inventory 표현과 planned count, 알려진 skeleton 분모를 남긴다. Origin-index 한도만 넘으면 전체 fresh supplier body/count를 보존하되 **모든** origin list를 비운다.

Compare 기본 한도는 selector64/selector당 slot64/logical work200000이다. 모든 selector의 형식·complete partition과 요청 work를 먼저 확인해 whole hold한다. 가능한 앞쪽만 계산하지 않는다. `query_plan`은 실제 selector별 경계·same-known-lane extreme pair·extreme row·path 내부 terminal probe 발생, literal/Core source closure 크기, profile 교차와 ordinary actual route의 상한을 명시한다. Source note/tie/measure가 많아져도 sound 수만 같으면 같은 work로 보는 이전 초안의 결함을 보완했다. 현재 경계 관찰은 path마다 계산하므로 존재하지 않는 cross-path cache 절감을 주장하지 않는다. 이 source-size-aware logical visit 단위는 CPU초/bytes 보장이나 물리 메모리 상한이 아니다. Geometry work100000은 **raw lane별** exact count의 한도이며 완전 witness materialization의 자체 query replay 비용과 구별한다.

보류 lattice에 없는 origin을 caller가 새 ID로 만들어 질의할 수 없다. 비어 있는 selector list는 허용된 known-empty request지만 lattice 자체가 보류면 그 unavailable 상태도 유지한다.

## 6. 구현과 검증 기록

- [native core](../../../src/musicanote_harness/factor_interval_lattice.py): build/validate/prepare, registered bundle, complete compare/validate.
- [공개 계약 검사](../../../tests/test_factor_interval_lattice.py): 실제 synthetic MusicXML→IR→expanded scope에서 검사한다. 기존 TestCase를 상속해 이전 검사를 신규 개수로 늘리지 않는다.
- [native append-only 실행기](../../../src/musicanote_harness/factor_interval_lattice_trial.py): 등록된 이전 selection/파일과 정확 full IR을 입력한다. 과거 owned session은 재사용하지 않는다.
- [실행기 저장 계약 검사](../../../tests/test_factor_interval_lattice_trial.py): native 계산을 mock한 storage-only 검사이며 실제 작품의 음악 계산 검증과 구별한다.

개발 중 AST/import 점검은 통과했다. 별도 검토로 owned HMAC에 state identity를 추가하고 mutable/copied state를 거부했다. 미사용 임시 comprehension을 제거했으며 same-raw-lane literal pair에 unknown lane을 섞지 않는다. DP의 strict count/weight 자료형을 보강했다. Native creation/actual delayed route를 계산하면서 이전 계층의 “아무 새 path/completion도 만들지 않았다” 활동 flag를 False로 복사하는 모순도 제거했다. 확정/승격 금지 policy는 유지한다.

### 6.1 고유 신규 검사와 기존 회귀

최종 native 공개 검사 **55개/56.358초 PASS**다. 실제 synthetic MusicXML을 parse한 IR/scope를 사용한다. 세 구간 ii→D7→G의 joint 전제, None 전환과 explicit ordinary 가정, 원 key/unknown, no-link 대조, 두 cut을 넘는 tie, fork 충돌, first adverse pitch 뒤를 건너뛰지 않음, missing source attack, closed selector, whole budget/0/null, immutable/HMAC/state 교체, prepare 도중 입력 변경, selector 변경을 검사했다. 같은 sound/cut/profile이더라도 notated source closure가 늘면 work가 증가하여 전체 보류되는 반례도 확인했다. Synthetic 양성이 실제 작품의 정답 평가를 대신하지 않는다.

첫 신규52개 실행은 **50통과/2fixture·보조 함수 오류,40.684초**였다. Missing-attack 음을 upstream anchor 안에 두어 anchor 자체가 정상적으로 거부됐고, caller mutation 검사에서는 이미 지운 caller 자료로 링크를 다시 만드는 test helper가 실패했다. 테스트만 교정한52개는44.842초에 통과했다. 이후 공개 negative3개를 보강한55개가 최종 동결 결과다. 앞52개의 반복 실행을 신규 항목으로 더하지 않는다. 테스트 결함을 제품 source 변경으로 숨기지 않았다.

Root의 별도 기존 회귀는 expanded hypotheses/indexed hypotheses/progression context **3suite124개/254.307초, exit0/OK**다. 신규55개와 별도 프로세스이며 한 번의179개 전체 Python 실행이라고 하지 않는다. 직전 전체 검사 이력은 그 문서에 보존하고 이번 전체 재실행으로 바꾸지 않는다.

| 동결 파일 | SHA256 |
|---|---|
| factor_interval_lattice.py | `319fe057ed1ea1a203414398c4ab07a1e755664aa26698d787c2a6b06c849ebe` |
| test_factor_interval_lattice.py | `9a93a79c50fc015b6b0ac956351cd2d3918d755528207da7ec7810a5dfeca9a5` |

신규55개 실행 전후 source/test SHA가 동일했다. 별도 순수 helper 감사의 DP **4,164 weight 조합**은 2~4좌표 모든 edge의 `{null,0,1,2}`와 slot별 complete skeleton을 brute-force 대조했다. Unknown×known zero와 알려진 subtotal/미정 skeleton 수를 포함해 일치했다. Actual first-change helper의 adverse-change stop·같은 음 재타격·중간 source guard 반례도 통과했다. 이 helper 감사는 공개55개나 실제 작품 검증 수에 더하지 않는다.

### 6.2 실제 시험의 계획과 한계

원 phase21의5선택 문맥은 Quartet/Sonata/Chopin/Corelli/Mozart이며 관찰 cut15/15/17/32/29에서 모든 positive interval136/136/171/561/465, 총1,469개가 계획된다. 이는 원221 prefix/suffix/full span과 다르다. Planned skeleton은32,768/32,768/131,072/4,294,967,296/536,870,912다. 이 사전 산술을 실행 성공/화성 정답으로 보고하지 않는다.

Pilot은 observed half/thirds에 가까운 exact cut과 각 interval의 첫 native ID를 선택하는 **label-blind 기술 panel**이다. 원주석·특정 마디 정답을 선택에 쓰지 않는다. 각 key의 full-hold, two-slot, three-slot에 None 또는 explicit V7/M 전환 vector를 비교한다. 양성을 찾아내는 음악적 탐색 정책이 아니며 두 가정 벡터를 전체 기능 universe로 주장하지 않는다. No-link control과 최대20개 admissible endpoint matching의 한 greedy 기술 completion을 각각 독립 등록한다. Greedy matching은 실제 성부·최적 성부·음악적 해석으로 확정하지 않는다. 각 비교 내부는 끝까지 같은 bundle을 사용한다.

등록된 과거 selection/creation 파일은 bytes·SHA·정확 목록으로 보호한다. Sonata는 원 DCML IR이 아닌 등록된 제한 교정 `candidate_ir.json`과 binding이 맞으므로 그것을 사용한다. 다른 네 문맥도 정확 full IR의 content/binding을 대조한다. Source projection을 임의 full IR처럼 조립하지 않는다. 이번 실행은 native IR/scope fresh 공급이며 **전체 과거 parent cold replay가 아니다**. 전체322문맥/1,013lanes와 선택5문맥/15lanes, 미실행317/998을 구별한다.

최종 실행·실행기 검사·보호 확인은 다음 절에 기록한다.

### 6.3 실행기 검사와 동결

Storage-only 신규 검사 **35개/5.257초 PASS**이며 root의 같은35개 재검사도 **5.160초/exit0/OK**다. Native supplier·path 계산은 mock했으므로 음악적으로 다른35곡/실제 native query35건으로 세지 않는다. 등록 metadata/full IR의 exact binding, 닫힌 settings, planned/submitted/computed 분모, failed context의 성공 subtotal 제외, 0/null/전체 보류, source labels 미사용, exclusive 신규 파일 저장과 보호 SHA를 검사한다. 공개 core55개·실행기35개·기존 회귀124개는 서로 다른 실행의 고유 항목이며 한 번의214개 통합 검사라고 보고하지 않는다.

초기32개 storage 검사에서 re-sealed second context mock의 동일 ID가 기존 저장 파일과 충돌했다. Exclusive 저장 거부는 정상 동작이었고 두 context mock에 다른 fixture marker를 부여한 테스트만 수정했다. 기존 파일 덮어쓰기나 제품의 ID/저장 보호를 완화하지 않았다.

| 동결 파일 | SHA256 |
|---|---|
| factor_interval_lattice_trial.py | `87c5a9d7d7f9bf8298a73f8c9d1f1cc5ae17c41324cef8cd2b91b738046b1c97` |
| test_factor_interval_lattice_trial.py | `7b169cef38904feca84f6ae279f698f223864f134012f52183b2ee9f526d6dfc` |

별도 읽기 전용 metadata/full IR 조회는 등록5문맥·보호4,539path와 정확5full IR binding을 확인했다. Metadata 조회8.298486초, full IR 확인 포함 전체11.628702초는 실제 native 생성 시간이 아니다. 이 단계에도 original parent cold replay는 없었다. 소스·신규 검사4개와 직전 단계의4개 source/test 동결 SHA는 실제 시험 진행 중 재확인하여 불변이었다.

### 6.4 실제 r1 저장 결과와 독립 감사

단일 native r1은 **exit0/2,260.335986초**에 완료했다. 원5문맥/15raw lanes를 저장했고 실패0, 모든lattice ready, 전체 comparison 예산 보류0이다. 모든 입력·현재 producer·생성 파일 보호와 선택 분모 검사를 통과했다. `scope_calculation_complete=true`는 이번 선택 자료의 계산·저장 무결성이며 전체 logical path 실행·정확도·최종 음악 판정을 뜻하지 않는다. 문서 계약의 별도 읽기 전용 검토도 source authority/query budget/0/null/NCT 미통합/기능 선언과 성립/곡수·정확도 구별에서 오류를 발견하지 않았다.

| 실제 선택 문맥 | 내부 cut | fresh catalog | native origin 대안 | partition skeleton | 문맥 실행 초 |
|---|---:|---:|---:|---:|---:|
| Beethoven quartet n01op18-1_04 | 15 | 136 | 7,285 | 32,768 | 106.464992 |
| Beethoven Sonata01-1 | 15 | 136 | 11,381 | 32,768 | 100.001278 |
| Chopin BI105-2op30-2 | 17 | 171 | 14,018 | 131,072 | 137.528988 |
| Corelli op01n01a | 32 | 561 | 63,180 | 4,294,967,296 | 1,421.550976 |
| Mozart K280-1 | 29 | 465 | 37,583 | 536,870,912 | 483.227186 |
| 합계 | 108 | 1,469 | 133,447 | 4,832,034,816 | 전체 producer 시간과 구별 |

10개의 새 all-raw-lane bundle(5no-link/5greedy 기술 completion)은 모두 complete이며 기존 bundle을 바꾸지 않았다. Requested/submitted/computed selector는 각각250이고, 그중 full-hold50/two-slot100/three-slot100이다. Completion·전환 가정을 제외한 distinct origin path×key는75이며 전체5문맥의조성후보수합25와 작품별5개를 구별한다. 실제 path의 slot550/내부전환300/시작·끝 포함 boundary800, 원음가 보존250/250을 확인했다. 원 parent의22,969origin/113indexed group/1,068,810path/5,344,050path×key/106,845,950function row 분모는 별도로 그대로 보존했다. 새공급 대안 수를 기존원후보 소거·곡수·화성정답수로 읽지 않는다.

Native의 알려진 전체 weighted path 합은 `26790074492734755566661648414863502705912`이며 unknown nonzero skeleton0이다. 실제250요청이 이 전체 조합을 계산한 것이 아니다. Slot별 exact key/function/terminal 분모는 저장 universe에 있고 transition-assumption vector materialization은0이다. 전체322문맥/1,013lanes와 미실행317/998도 보존한다.

설정은 모든5문맥에 동일한 catalog1024/origin200000/DP200000/geometry100000/selector64/slot64 및 **query work2,000,000**이었다. Query의 기본200000을 실제 적용했다고 기록하지 않는다. Observed quantile/첫native ID/두transition vector의 label-blind 기술 panel이며 원주석·사용자정답으로 후보나cut을 골라내지 않았다.

정확28생성파일은5lattice/10bundle/10comparison과run-plan/context-index/report이며 총75,303,652bytes다. 등록입력4,539와현재producer·schema·명시신규test320개를 보호했다. Root의 별도 stream SHA 대조는 report를 포함한고유4,571creation path·현재code320목록·정확28output에서변경0이다. 이는 과거 parent의 authentic cold 음악 계산을 다시 수행했다는 뜻이 아니다.

| 저장 근거 | SHA256 |
|---|---|
| [report.json](../../../output/factor-interval-lattice-2026-10-02-r1/report.json) | `50fa943d8cc6b6ca86d3159928a919ad17ca379c1a3771f9667638bf51b53574` |
| [run-plan.json](../../../output/factor-interval-lattice-2026-10-02-r1/run-plan.json) | `2552670de8f6f38a3419942eff06cd6acbb53f9e39282fc2ae1348537cfc4a04` |
| [context-index.json](../../../output/factor-interval-lattice-2026-10-02-r1/context-index.json) | `77226ee8d39eda6ce2c284a84513c5e51c2a6ba304ab16a506a574b35d2556c2` |

진행 중 완료된 첫3문맥만의 별도 saved finite 감사는443catalog/32,684origin,150조건부경로/330slot/180내부전환/480boundary와6complete bundle의 원음가·tie·profile·same-bundle·unknown key·종지 전제를 대조했다. 첫 감사163,966assertions/19.004초와 추가query-plan/unknown/cadence 감사3,732assertions/6.468초는 모두 오류0이며 읽은 완료18파일(3lattice/3scope/6bundle/6comparison)의SHA 변경0이다. 합계167,698assertions는 유한 대조의 검사문 실행 수이지 독립 작품 수·신규 unittest 수·정답률이 아니다. 첫3의196,608partition skeleton을 독립 조합 산술로 대조했지만 나머지 거대한 skeleton은 열거하지 않고 독립 DP로 확인한다.

첫3panel의 선언90function에는 ordinary critical-note occurrence가0이며 모든joint는False, 나머지90undeclared 전환은None이었다. 따라서 실제작품의 F#→G 등 해결 양성을 검증한 자료가 아니다. 양성은 합성 공개55suite의 명시 사례에서 확인했으며 native ID 첫 대안을 고르는 기술 panel을 음악적 유력 후보나 Secondary 성능 평가로 승격하지 않는다. Source-size query work도 quartet748,495/Sonata225,745/Chopin406,200(각2comparison)의 저장 counter와2,000,000한도를 대조했다. 이 중간 감사 자체를 최종5문맥 감사나 공급 음악정답 검증이라고 하지 않는다.

### 6.5 최종 독립 saved finite 감사와 문서 QA

최종5문맥의 독립 metadata/creation SHA 및10bundle/10comparison의 작은 sidecar 감사는 **9,227assertions/4.424096초 PASS**다(별도 outer4.880196초). Exact 원parent metadata·creation closure와 Sonata교정full IR binding,5선택/15lanes·전체322/1,013·미실행317/998,등록inputs4,539/current code320/보호합집합4,543+27등록artifact+report=4,571경로,정확28파일/75,303,652bytes 및각생성SHA를대조했다. 1,469catalog/133,447origin/250computed/75distinct path×key/300internal/800boundary/10complete/보류·실패0을row별재합산했고모든path의raw음가보존·NCT credit null·미승격policy를확인했다. 신규4파일과직전4source/test동결SHA도불변이다. 대형lattice body나전체native 음악 계산을재실행한검사가아니다.

나머지2문맥의 대형lattice source·profile·DP·same-bundle·기능/종지 전제는한문맥씩로드·해제하는별도읽기전용finite 감사로마쳤다. 새로운 supplier/build/prepare나과거parent cold시험을재실행하지않았다.

Last2 첫saved 감사는437,300검사문/72.012초 중60건이 auditor의 `known_nonzero_skeletons == total binomial skeletons` 가정과 불일치했다. 실제fresh supplier에서 후보0인구간이 있어, 그구간을 포함한partition의 가중 곱은0이며 certified nonzero skeleton에서 제외되는 것이 제품의 올바른 계약이다. 불일치60건은Corelli32개/Mozart28개slot별행에 해당한다. 제품·원자료·저장결과는수정하지않고 nonzero edge에unit weight를주는독립DP로 검수 가정을 교정하여 재확인한다. 초기실행을PASS나신규437,300개음악정답으로집계하지않는다. 나머지전weightedDP·literal/time/tie/same-bundle·function/cadence/queryplan/body seal 검사는일치했으며 마지막2에도ordinary critical-note occurrence0이라는양성coverage한계가있다.

교정DP 부분재확인은252assertions/24.009초/오류0이다. Corelli의certified0 interval2개는전체4,294,967,296skeleton 중1,610,612,736개의nonzero skeleton을남기며, Mozart의certified0 interval11개는536,870,912중39,370,752개를남긴다. 나머지는공급미정이아니라known-zero edge를포함한partition이다. 첫3의196,608을더한전체nonzero skeleton은1,650,180,096,known-zero는3,181,854,720,unknown0으로원전체4,832,034,816과일치한다.

교정된last2 전체saved 감사는 **exit0/436,216assertions/71.113436초/오류0**이다. Corelli272,784확인/49.443초와Mozart163,431확인/18.514초,body/ref·최종SHA 확인을포함한총수/총시간을구별한다. 원note/tie/sounding/full IR과scope projection,모든100,763origin의supplier pointer·variant·seal,각slot별독립weighted/nonzero DP와구성음·source clock·raw rational 음가·same-bundle/queryplan/key/function/cadence를대조했다. 읽은완료14파일(2lattice/2scope/2full IR/4bundle/4comparison)의SHA변경0이다. 원본·code/test·output·문서에쓰기나fresh replay/cold/build/prepare 호출이없다.

마지막2에서100path/220slot/120내부전환/320boundary/6,070profile row/1,110extreme row/40actual link와3source tied sound를확인했다. 첫3의성공167,698확인/25.472초와합산한최종5문맥의saved finite 검수는 **603,914확인/96.585436초/오류0**이다. 이수는독립검사문의실행횟수이며unittest수·음악정답수·전logical path검증이아니다. 초기437,300/60불일치와교정부분252재확인을이최종PASS합계에더하지않는다. Metadata9,227확인/4.424096초는별도검사이며이합계와한번의통합실행으로표현하지않는다.

전체250개기술selector 결과의선언150function joint는False,나머지150undeclared 전환은None이다. Actual ordinary critical-note occurrence/양성occurrence0이며PAC/HC/IAC nominalTrue0·confirmed0이다. 이panel에서실제Secondary 해결양성·종지양성정확도를검증했다는주장은없고,합성55suite양성과별도실제작품검수공백을보존한다. 다음후보탐색/음악평가에서명시적해결전제가존재하는다양한실제사례를선택할필요가있지만원주석정답으로유리한결과를골라내지않는다.

최종문서spot 검수에서도실제표/분모/설정·비용·Sonata binding·미승격/후속미구현이일치했다. 새source/test4개와문서3개의strict UTF-8/NUL/U+FFFD/줄끝공백·4AST·130로컬링크검사는오류0이다. Read-only `git --no-optional-locks diff --check`는exit0이며기존별개tracked5파일의LF→CRLF경고는보존했다. 원IR/parser/Core/기존source/output/운영화면/구조/생성/Git을바꾸지않고신규연구계층·검사·정본개발문서만추가/갱신했다.

## 7. 다음 큰 단위

이 새 native interval/path/completion 계약에 local NCT·경계 계류/선행음·지연 ordinary 역할의 조건부 음가 합집합을 연결한다. 하나의 sound 시간이 여러 역할에 중복 가산되지 않게 하고, 같은 completion 아래 여러 경계의 설명·미설명·source 보류를 공동 대조한다. 기존 one-cut credit를 새 세 구간에 잘라 붙이지 않는다.

그 다음 넓은 local-key evidence, 후보 탐색/대조 정책과 다양한 작품·편성의 음악 검수, 전체 악보 뷰어 피드백으로 이어간다. 부족한 협화·음악적 성부·화성 시작 전제를 confidence로 덮거나 특정 악보의 정답을 조건문에 넣지 않는다.

운영 연결 전 성능도 별도로 관측한다. 정적 검토에서 구간마다 base window와 같은 full context window를 공급하는 경로, supplier 내부 및 builder의 반복 validation, origin 복사·재seal, 전체 lattice copy/freeze/thaw와 압축 저장이 비용 후보로 확인됐다. `_ref(scope)`는 ID/SHA 두 필드 참조이므로 그것을 반복 full-scope hashing의 원인으로 기록하지 않는다. Context별 supplier/window 호출 수·시간, 후보/origin 수·body 크기, seal/copy/freeze/thaw·압축 시간과 peak RSS를 분리 측정한 뒤 정확한 동일 입력·producer 계약을 보존하는 계산 공유를 검토한다. 현재는 프로파일링을 하지 않아 병목·개선률을 확정하지 않으며, 실행 중 코드 변경·예산 후퇴·후보 잘라내기를 하지 않았다.

실제r1의Corelli 계산 중 root의 읽기 전용 프로세스 조회에서 CPU 누적924.12→1,035.11→1,357.83초 증가를 확인했고 마지막 조회의 current working set은3,619.6MiB였다. 이것은 살아 있는 실행의 특정 시점 표본이지 context별 CPU 시간/peak RSS나 final 총시간 측정이 아니다. 이런 비용을 운영 속도나 대규모 처리 가능성으로 숨기지 않고, 전체 cohort 확대 전 정확한 공급·출처·동일 authority를 유지하는 계산 공유와 비용 관측을 필요 작업으로 남긴다.

### 7.1 다음 설명 계층의 기획 완료 기준 — 아직 미구현

별도 읽기 전용 후속 설계 검토에서 다음 계약을 권고했다. 기존 local/boundary/delayed 계산을 새 partition에 그대로 붙였다는 의미가 아니다.

1. Native lattice의 실제 발급 session·정확 selector·등록 bundle·resource limits에서 comparison을 재계산/대조한 뒤 별도 immutable/HMAC 설명 session을 발급한다. 저장 hash와 발급 권한을 구별한다.
2. `factor_temporal_explanations`의 interval union/duration/source guard, frozen state/motion, boundary의 literal pitch/ordinary step은 순수 kernel로 재사용할 수 있다. `factor_delayed_obligations`의 clause/account와 `factor_progression_evidence`의 aggregate는 의미·산술을 참고하되 native refs로 다시 구성한다. 옛 두-slot pair/group/route/role builder나 old owned producer에 가짜 ID를 넣지 않는다.
3. Local passing/neighbor-like는 같은 bundle의 연속 실제 두 링크, member→nonmember→member, full span의 slot 내부 위치·철자/음역·ordinary contour·source timing/attack 전제를 다시 판정한다. 가운데 비구성음 시간만 설명하고 최종 NCT·협화·accent 의미는 확정하지 않는다.
4. 모든 인접 native 경계에서 suspension-like preparation→held/reattacked→downward endpoint와 anticipation-like left nonmember→right member를 다시 계산한다. 원 tie 지속과 재타격의 실제 링크를 구별한다.
5. Delayed ordinary 역할은 명시 family/quality 가정과 실제 첫 변화 route·endpoint membership에만 연결한다. 역할 내 OR/역할 간 AND, 명시 occurrence 전략과 전체 doubling 의무를 구별한다. Unknown key의 literal motion을 Secondary 정답으로 승격하지 않는다.
6. 초기에는 보수적인 full-span/인접 pair envelope를 유지한다. 여러 cut을 넘는 sound는 full span과 각 clip을 보존하되 unsupported/미평가로 남길 수 있다. 향후 multicut credit는 지나가는 모든 slot의 membership·가정 지속·endpoint를 확인하는 별도 일반 규칙이 필요하다.
7. 같은 path/key/transition vector/bundle의 역할 구간만 sound별 합집합하고, 각 slot의 guarded nonmember와 교차한다. Endpoint/member/source 보류에는 credit를 주지 않는다. Credit≤guarded nonmember, 원 여섯 category 합=raw total, 전체 raw total=이번 phase22, per-sound union=설명량을 검사한다.
8. 모든 요청의 slot/boundary/실제 chain/clause/source closure/union endpoint 발생량을 먼저 계획하고 whole budget을 적용한다. 완전 no-link 아래 평가한 실패0/False와 source/completion/work 미평가null을 구별하며 유리한 prefix·기존 분모 변경을 금지한다.
9. Planned/evaluated/qualified/satisfied/withheld/unassessed clause, distinct geometry와 발생 수, 실제 union 음가를 별도 보고한다. 경쟁 key·bundle의 설명량을 합산하거나 이를 winner/confidence/Cadence/Gold/UI 적용으로 확대하지 않는다.
10. 공개 native 준비 경로에서 three-slot local 역할, held/reattacked suspension·anticipation, ordinary leading/seventh와 겹치는 union을 양성으로 검사한다. No-link/한 링크만 존재/fork·merge/adverse first-change/slot 밖 full span/multicut 미지원/enharmonic·음역/source hold·missing attack/point·grace/unknown/whole budget/foreign·copied authority 반례도 필수다. Pure helper 검사는 공개 검사와 따로 집계한다.
