# 손실 없는 화음 관계와 실제 음표·직접 해결 근거

2026-10-01. 직전 [형태·목표 화음·조성 관계](2026-10-01-lossless-function-relations.md)를 이어가는 화성 개발 기록이다. 작곡·편곡 활용 기획은 [별도 로드맵 §10](../MUSICAL_SEMANTICS_AND_GENERATION_ROADMAP.md#composition-arrangement-application-plan)에 보존한다. 이번에는 생성기를 만들지 않고 분석 근거의 검증 순서를 유지한다.

## 1. 목적과 범위

같은 피치클래스나 화음 이름만으로 실제 악보의 화성을 인정하지 않는다. 다음을 서로 구별한다.

1. 가정한 화음의 철자·구성음과 다음 화음의 형태가 맞는가.
2. 원음표가 실제 구간에서 언제까지 울리는가. 어떤 음이 가정 구성음이고 어떤 음이 아닌가.
3. 경계의 실제 베이스·구성음과 출처 검사가 해당 직접 해결 판단을 뒷받침하는가.
4. 이끎음과 7음의 실제 철자·음역·진행이 교재의 직접 해결 형태에 맞는가.
5. 필요한 모든 연결이 **하나의 실제 전 성부 completion** 안에서 함께 가능한가.

5까지 충족해도 화성 정답·secondary 확정·국소 조성·종지 확정은 아니다. 단지 특정 화음/다음 화음/성부 가정에서 직접 해결의 조건부 형태를 설명할 수 있다는 뜻이다. 비화성음과 지연 해결을 모두 평가했다고 해석해서도 안 된다.

이전 공급 후보·출처·철자 대안·false/unknown·terminal·원예산 보류를 줄이거나 원 결과를 갱신하지 않는다. 특정 작품·제목·마디의 정답을 조건식에 넣지 않는다.

## 2. 새 코드와 경계

- 핵심: [`factor_grounded_relations.py`](../../../src/musicanote_harness/factor_grounded_relations.py).
- 실행기: [`factor_grounded_relation_trial.py`](../../../src/musicanote_harness/factor_grounded_relation_trial.py).
- 검사: [`test_factor_grounded_relations.py`](../../../tests/test_factor_grounded_relations.py), [`test_factor_grounded_relation_trial.py`](../../../tests/test_factor_grounded_relation_trial.py).

기존 parser/Core/source/확장 scope/index/형태 관계의 코드는 변경하지 않는다. 새 계약은 원 IR과 검증된 새 scope, 공급 가정, 색인, 형태 관계를 소비한다. 이전 `fmview`나 NCT/resolution 엔진의 부모를 임의 변환·재봉인해 인증된 것처럼 제공하지 않는다.

기본 API는 `build_grounding` / `validate_grounding` / `prepare_grounding`, 완전한 원후보 tuple의 `query_grounded_prepared`, 하나의 기존 실제 bundle 아래 `assess_grounded_prepared`다. build/prepare 입력은 불변으로 직렬화해야 한다. 복사 전후 hash 검사가 일시적 변경 후 원복되는 concurrent ABA의 원자적 snapshot을 보장하지는 않는다.

## 3. 모든 literal profile

형태 관계에서 공유한 type은 구간을 제외한 exact root/ordered members/blocker다. 실제 note-time profile은 같은 key로 공유할 수 없다. **같은 scope·정확한 유리수 span·root·ordered members·blockers**의 indexed descriptor를 사용한다.

각 descriptor는 기존 순수 profile 계산을 실제 원음표 관찰로 재현한다.

- `[start,end)`의 양수 overlap, full source span과 구간 clip.
- spelled member / nonmember-not-confirmed-NCT / unknown.
- 모든 실제 onset/release로 나눈 수직 cell의 활동음·침묵·실제 최저음/베이스.
- 실제 베이스가 가정 구성음인지, ordered member index와 보통 3/7화음 조건에서의 전위 후보.
- 구간별 missing spelling과 출처 guard를 통과한 구성음의 누락.
- 구간 overlap 음가 합과 정확한 유리수 incidence. full source duration과 clip의 합은 구별한다.

`nonmember`는 passing tone 등의 확정 라벨이 아니다. `member` 역시 화음 정답 인증이 아니다. 정확히 같은 값을 갖는 row/cell만 interning하고, descriptor별 순서와 참조를 유지한다. 질의 때 원 `segment_ref`·missing fields·supplier 상태·출처를 복구한다. 서로 다른 구간이나 enharmonic 철자를 근음/PC가 같다는 이유로 합치지 않는다.

tie continuation은 같은 sounding event의 지속이며 새 attack이 아니다. source-clock/철자/attack 진단과 grace/point 상태는 보존한다. 관찰된 clip이 정상이라는 이유로 full-chain 원문 오류를 면제하지 않는다.

## 4. 직접 해결 kernel과 성부 공동 가정

앞뒤 두 slot의 **형태 전제까지 충족하는 경우**만 실제 직접 해결을 평가한다. exact source/target profile descriptor·family·target quality가 같은 순수 계산을 공유하되 original variant, group, key 가정과 분모는 유지한다. 조성 투영은 key별로 복구하며 실제 endpoint 계산은 key-independent라고 명시한다. unknown key가 국소 조성의 자동 추론으로 바뀌지 않는다.

기존 직접 해결의 필수 전제를 그대로 따른다.

- source의 경계 직전 cell과 target의 경계부터 cell을 구별한다.
- 가정 화음의 구성음이 실제 경계에서 충분히 울리고 출처가 확인돼야 한다. 목표 triad-core의 형태 호환과 후보의 **전체** 구성음 sounding은 서로 다른 전제다.
- 실제 베이스가 구성음이어야 하는 직접 해결 모델의 제한을 유지한다. 분산형/계류/지연 해결 때문에 이 전제가 안 맞으면 보류한다.
- endpoint의 source eligibility·full clock·written pitch·attack lineage·ordinary spelling/음역을 확인한다.
- 같은 raw lane의 touching geometry에서 이끎음의 spelled 상행 반음과 목표 근음, 7음의 spelled 순차 하행을 평가한다.
- pitch-class만 같은 다른 옥타브, enharmonic 대체, 다른 raw lane을 자동으로 같은 성부로 사용하지 않는다.
- qualified edge 중 LT·7음에 필요한 연결 전체를 요구한 **하나의 all-lane witness**를 만든다. 모든 lane이 같은 bundle에 참여하며 미요구 연결은 무연결 대안으로 남는다.

raw lane은 원 악보의 관찰 분류이며 실제 대위법 성부의 인증이 아니다. 여기서의 completion은 가능한 성부 연결 가정이다. 가까운 음높이·성부 번호만으로 연결을 확정하지 않는다.

### 독립 witness를 합치면 안 되는 반례

G7→C에서 같은 F4가 C-major 후보의 E4로 내려가거나 C-minor 후보의 E-flat4로 내려갈 수 있다고 하자. 두 해석은 각각 가능한 성부 연결을 갖더라도, 하나의 F4가 그 한 completion에서 두 목적음으로 동시에 이어진다고 인정할 수 없다. 같은 bundle 아래 supported/withheld를 각각 계산한다. 이는 일반적인 경쟁 가정 검사이며 특정 작품의 정답 규칙이 아니다.

## 5. 분모·보류·예산

모든 original origin/공급 catalogue/shape state/key projection/terminal multiplicity는 원 관계를 통해 보존한다. 새 layer에서 모든 logical 진행이나 1억 function row 객체를 만들어야 하는 것은 아니다.

- 전체 descriptor 수가 `max_profiles`를 넘으면 profile 전체를 보류한다. 앞부분만 계산한 뒤 전수 평가라고 하지 않는다.
- 전체 직접 해결 kernel inventory가 `max_motion_kernels`를 넘으면 해당 inventory 전체를 보류한다. 이미 계산한 literal profiles는 보존한다.
- kernel의 **전체** endpoint 수와 qualified LT/7음 joint product를 먼저 센다. `max_motion_pairs` / `max_joint_options` 초과 시 그 kernel 전체를 보류하고 유리한 prefix를 골라 쓰지 않는다.
- 이 limit은 descriptor/kernel/endpoint/joint-product 수에 대한 제한이지 bytes/RSS/실제 처리 시간 보장이 아니다. row/cell 사용 수도 따로 기록한다.
- known `0`, unknown `None`, budget hold, prerequisite withheld, geometry hold를 구별한다.

joint 연결이 실제 geometry에서 불가능하다고 판명된 exact `0`은 미지수가 아니다. boundary/source 전제와 전체 한도를 통과한 kernel에서 모든 joint 대안을 저장한다. valid와 known-impossible이 함께 있으면 valid의 조건부 지원을 보존한다. 실제 unknown/예산 보류가 섞이면 전체 지원 판단을 보류한다. 상위 색인/공급 inventory가 보류된 경우의 알려진 참조·부분 관찰도 유지하고, 후보 snapshot이 없다고 질의에서 KeyError를 내거나 빈 inventory를 전체 완료로 인정하지 않는다.

새 direct-motion 분모는 다음과 같다.

`grounded conditional direct` + `assessed direct-prerequisite withheld` + `unassessed direct` = 알려진 전체 logical function rows.

원래 shape-false/unknown/terminal/blocker인 행은 direct motion을 실제 계산했다고 하지 않는다. 이를 별도 motion-ineligible symbolic complement와 `unassessed direct`에 포함한다. shape-positive여도 예산·geometry 보류는 assessed negative로 바꾸지 않는다. 후보/key 조합 수를 서로 다른 화음이나 악곡 수로 읽지 않는다.

## 6. 실행기 보호

새 실행 전 원 shape stage의 completed report·closed policy·선택 목록·부모 report SHA·정확 artifact inventory·폴더/파일명/참조/status/SHA를 검사한다. 등록된 indexed/expanded/prerequisite/family 체인의 모든 보호 입력을 연결하고 모든 원 shape sample을 공개 함수 질의로 재현한다. 원 literal profile/motion 실행 결과는 과거 기록이며 새 parent 검사에서 재계산한 것으로 주장하지 않는다.

새 결과는 `output/`의 새 direct child에만 append-only로 저장한다. 실패 전에 각 context의 알려진 분모를 집계한다. 새 계산 실패나 메모리 입력 변조가 발생해도 원 분모·원 단계·기존 보류를 지우지 않는다. metric의 정수 subtotal과 unknown context 수, saved/failed context 수를 구별한다. 실행 종료 때 입력/코드/산출물의 생성 시 SHA와 전체 inventory를 대조하며 변한 파일을 새 SHA로 흡수하지 않는다.

## 7. 검증·실제 실행

### 코드 검증과 보완 이력

동결 핵심 검사 **47개/115.083초 OK**, 실행기 검사 **25개/392.891초 OK**다. 기존 두 신규 검사 모듈을 제외한 **211개 모듈/3,251개 회귀 검사/1,254.530초 OK**도 별도 실행했다. 기존 source의 검사 전후 hash 차이는 없었다. 새 72개와 기존 3,251개, 총 3,323개의 검사가 각 해당 실행에서 통과했으며, 3,323개를 하나의 통합 실행에서 검사했다고 기록하지 않는다. 검사 수는 작품 수·화성 정답 수가 아니다.

완료 전 발견·보완 사항도 보존한다.

1. 공동 geometry의 확정 불가능 `0`을 unknown으로 취급하던 초안을 고쳤다. 가능한 대안과 불가능한 대안을 모두 보존하고 실제 unknown만 전체 지원 보류로 둔다.
2. 상위 색인이 전체 한도로 보류돼 snapshot이 없을 때 알려진 ID가 남는 경우의 질의 오류와 빈 profile을 완료로 취급하던 경로를 고쳤다. 알려진 분모와 미계산 `None`을 분리한다.
3. ready와 unknown inventory가 함께 있을 때 실제 baseline이 없는 상태를 별도 상위 보류로 처리한다. 알려진 kernel은 지우지 않는다.
4. 직접 움직임의 순수 계산에도 실제 첫 선언 key를 전달한다. key-independent 계산이라는 이유로 가짜 부모 key를 만들지 않는다.
5. 직접 해결은 profile의 첫/마지막 cell만 읽으므로 그 경계 값만 해당 계산에 전달한다. 모든 literal row/cell은 별도로 보존하고 원 순수 계산과 대조한다.
6. 확대 핵심 검사에서 첫 40개 중 fixture 오류 2개, 다음 46개 중 존재하지 않는 공급 후보를 고른 fixture 오류 1개를 발견했다. 선언된 staff, 실제 중첩 `sound` 경로, 실제 dominant added-tone 공급 후보로 테스트만 고쳤다. 동결 최종 47개는 모두 통과했다. 초기 실행을 최종 통과로 집계하지 않는다.
7. 실행기의 동결 전 검사는 source 변경 때문에 중단했고 당시 16개 진행을 25개 통과로 기록하지 않는다. 최종 동결 실행과 별도 저장/실패 검사 2개/34.982초를 구별한다.

검사 범위는 작은 전체 tuple의 원 function body 대조, weighted 분모, major/minor 경쟁 연결, 하나의 공동 bundle, tie/쉼/반개구간/cross-staff·raw lane, grace/microtonal 관찰과 직접 모델 보류, octave-equivalent 비순차 진행 거절, 건강한 doubling과 잘못된 출처 분리, extended target의 triad-core와 전체 sounding 차이, endpoint/joint 전체 예산 및 exact zero, 입력·session·산출물 변조와 실패 분모 보호를 포함한다.

### 실제 r1

새 결과는 [별도 실행 report](../../../output/factor-grounded-relations-2026-10-01-r1/report.json), [계획](../../../output/factor-grounded-relations-2026-10-01-r1/run-plan.json), [문맥 목록](../../../output/factor-grounded-relations-2026-10-01-r1/context-index.json)에 저장했다. 실행은 **exit 0/811.000201초/5문맥 저장/계산 오류 0**이다. 부모 관계의 공개 질의 4,380개를 실행 전 재현하는 시간도 포함한다. 별도 읽기 전용 부모 감사의 377.425911초를 새 r1 시간에 더하지 않는다.

| 실제 작품 문맥 | literal profiles | 직접 motion kernels | 실제 endpoint 쌍 | 실제 joint 대안 | actual bundles | 조건부 직접 진행의 가중 행 |
|---|---:|---:|---:|---:|---:|---:|
| Beethoven 현악4중주 Op.18 No.1/4악장 | 1,592 | 533 | 158 | 2 | 3 | 10 |
| Beethoven 소나타 No.1/1악장 | 2,040 | 763 | 212 | 0 | 1 | 0 |
| Chopin Op.30 No.2 마주르카 | 2,670 | 1,943 | 713 | 0 | 1 | 0 |
| Corelli Op.1 No.1a | 5,712 | 4,330 | 1,169 | 2 | 3 | 5 |
| Mozart K280/1악장 | 4,192 | 2,705 | 416 | 0 | 1 | 0 |
| 합계 | 16,206 | 10,274 | 2,668 | 4 | 9 | 15 |

각 행은 해당 악곡의 **선택된 한 문맥**이며 전곡 화성 검사 완료가 아니다. 기존 전체 cohort 322문맥/1,013raw lanes 중 이 실행은 5문맥/15lanes만 계산했다. 미실행 317문맥/998lanes와 원 16groups·새 113groups, 221catalogues·22,969origin, 1,068,810paths·5,344,050path×key·106,845,950function 행 분모는 불변이다. 최종 진행을 선택하지 않는다.

16,206개 profile의 ordered row 사용은 528,468회, cell 사용은 249,951회다. exact value 공유 뒤 저장된 row는 1,374개, cell은 9,770개다. 음표·음가 삭제나 후보 축소가 아니라 같은 값의 공유다. 원 variant·span·ordered member·출처를 질의에서 복구한다.

qualified-role product는 **205개 사전 계수/4개 실제 joint 계산**이다. 나머지는 별도 boundary/source 전제를 충족하지 않아 geometry를 검사한 것처럼 세지 않는다. actual bundles 9개는 무연결 control 5개와 실제 required-link completion 4개다. `same_bundle_assessments_computed=20,000`은 각 저장 bundle 아래의 kernel 대조 수이며, 20,000개의 독립 성부 연결·악곡·해결 정답이 아니다. 신규 실행 자체의 `queried_logical_tuples=0`; 감사에서 재현하는 질의는 별도다.

가중 partition은 **조건부 직접 근거 15 + 실제 직접 전제 보류 51,355 + direct 미평가 106,794,580 = 106,845,950**이다. 15는 3개 직접 kernel × 선언 key 5개의 중복 가정 수다. 실제 joint 대안은 4개로, 한 kernel의 두 서로 다른 성부 대안을 독립 음악 정답 두 개로 취급하지 않는다. 원 shape false/unknown/terminal 보완 분모 106,794,580을 실제 direct negative로 바꾸지 않는다. known/unknown metric 중 이 r1의 unknown context는 0이며, 일반 실행기의 unknown 처리 검사는 별도로 존재한다.

실제 원음표 예는 다음과 같다. 베토벤 현악4중주의 q[262,264)→[264,270) 가정에서 C5 q[527/2,264)→D♭5 q[264,529/2)의 이끎음 진행, G♭2→F2의 7음 하행이 같은 V7 completion에서 함께 가능했다. 코렐리의 q[32,38)→[38,44) 가정에서는 서로 다른 두 raw lane의 B2→C3가 vii 형태의 별도 대안이다. 이 예는 공급 가정 아래의 실제 음표 연결이며 local key·secondary·종지·확정 화음에 대한 사용자 검수 결과가 아니다.

0이 나온 베토벤 소나타·쇼팽·모차르트 문맥을 “화성 없음”으로 해석하면 안 된다. 이 직접 모델에서는 경계의 전체 구성음 sounding/출처, 실제 구성음 베이스와 touching endpoint가 주요 병목이었다. 예를 들어 모차르트의 2,705kernels 모두 target 경계 전체 구성음 전제가 미충족이다. 미관측 구성음 때문에 guard까지 모두 확인할 수 없는 경우와 원문이 잘못된 경우를 같은 오류로 보지 않는다. 다음 분산형/NCT/지연 모델에서 다룰 이유를 그대로 보존한다.

### 독립 감사와 보호

첫 독립 읽기 전용 저장 감사는 통과했다. 실행 전후 inputs 4,479/code 306/artifact 7개의 SHA와 모든 ancestor inventory·새 8파일 inventory가 일치한다. 전 5문맥의 22,969origin/221catalogues/25key records/113groups/239source facts의 시간·참조·봉인·출처, 16,206profile descriptor/10,274motion kernel/9bundle과 각 bundle의 실제 qualified-link incidence·가중 partition, report의 정수/None/분모/saved5/failed0 집계를 확인했다. 서로 다른 witness를 합친 결과가 아님을 대조했다.

두 번째 독립 의미 감사의 전 5문맥 순수 oracle 대조는 **600.738초/불일치 0**으로 통과했다. 전 16,206descriptor의 정확 profile/22,969origin 복구, 10,274kernel의 실제 endpoint 옵션·blocker·계수, 전 9actual bundle의 fresh geometry/witness와 20,000same-bundle incidence가 일치했다. row 사용 528,468/cell 사용 249,951/endpoint 쌍 2,668/qualified edges 690/205planned products/4actual joint도 재현했다. qualified edge 690개가 각각 충분한 공동 해결을 의미하지는 않는다.

같은 두 번째 감사에서 이어 실행한 공개 `prepare_grounding`의 **전 5문맥 fresh rebuild**도 통과했다. 전 224기술 tuple의 정확 profile/4,380function body, 지원 kernel 3개×선언 key5=15질의, 같은 실제 bundle의 조건부 양성 assessment20개, 무연결 control의 음성 assessment15개를 공개 함수로 재현했다. Corelli의 두 공동 대안 때문에 양성 assessment20개와 지원 질의15개는 서로 다른 분모다. 이 단계는 `validate_grounding` entry point를 별도로 호출했다고 기록하지 않으며, 공개 prepare가 수행하는 전체 부모/자료 검사·재구축과 원 순수 oracle 대조를 구별한다.

두 번째 감사의 **전체 932.019410초/불일치 0**은 앞 순수 대조 600.738초와 뒤 공개 대조를 모두 포함한다. 전 10,274kernels의 status는 conditional3/prerequisite-withheld10,271과 일치했고 최종 inputs/code/artifacts·모든 inventory/report SHA가 불변이었다. 테스트 fixture·첫 진단·감사 replay를 저장 r1 결과나 음악적 정확도로 합산하지 않는다.

profile row의 member249,650/nonmember272,865/unresolved5,953 합528,468은 가정별 incidence이며 고유 source sound239개와 다른 분모다. 모든 실제 row 사용의 source guard는 적격이었다. 이번 missing-member에 동반한 source boundary guard10,120/target10,146 보류는 미관측 구성음의 확인 불가이지 그 수만큼 원출처가 손상됐다는 뜻이 아니다. 각 저장 bundle의 key-independent kernel incidence는 conditional5/not-satisfied-under-this-bundle4/prerequisite-withheld19,991=20,000이다. 공개 양성 assessment20개는 실제 joint 대안×key를 질의한 별도 분모이며 이 incidence를 confidence나 독립 음악적 투표로 합산하지 않는다.

독립 문서 검토에서는 최고음이 없는 원 profile를 잘못 설명한 문구를 실제 최저음/베이스로 교정하고, overlap 음가·전제를 통과한 kernel의 전체 joint 대안 범위를 명시했다. 최종 source/test/doc 7파일의 strict UTF-8·NUL/U+FFFD·줄끝 공백·Python AST, 3문서의 로컬 링크118개 오류0, read-only `git diff --check` exit0다. 기존 unrelated LF→CRLF 알림은 보존했다. QA 뒤 코드/입력/실제 report·정확 inventory도 다시 확인했다.

보호 계획에는 inputs 4,479개/current code·schema 306개가 등록됐다. 새 artifact 7개와 report를 포함한 정확 inventory는 8파일/15,153,439bytes다. 동결 SHA-256은 다음과 같다.

| 대상 | SHA-256 |
|---|---|
| 신규 core | `3c13662030ccb886353b1d713f2da123cc2457d1f81bbc67a2373eddd820ad95` |
| 신규 실행기 | `c7ea0ebf84770118ed084298b44df6bb6eeb4f135e17b01625f41bc419b28509` |
| 실제 r1 report | `fa37223f675e04d598f94fbd3b08becbd96b38ce5ad65bbefe134b7dac9de3ce` |
| 불변 부모 relation report | `8c4eab24a50b945225ca228ba42a61fc2a11acf9447ae5dd4dcbf0ae68381ac3` |
| 핵심 검사 | `cdf7dffcf3b0fe68145eb7c45b8c59cb886415dc3954b25ba2f67429a9e682f4` |
| 실행기 검사 | `b4eadfec509cea76db36adfc152c3d74b444150fb6336e0c8cca97e0e0be74ff` |

원 parser/Core/XML·과거 결과·운영 악보 화면/구조 분석·API·Git을 변경하지 않았다. confidence/selected·NCT/cadence·학습/Gold/생성 승격은 없다.

### 재현 명령

저장 r1을 덮어쓰지 않는다. 다음은 같은 동결 입력을 **새 폴더**에서 실행하는 예다. 생산 버전/부모 SHA가 달라지면 이전 결과와 같은 실행으로 간주하지 않는다.

```powershell
Set-Location -LiteralPath 'K:/Music Analysis'
$env:PYTHONPATH = 'K:/Music Analysis/src;K:/Music Analysis/tests'
$env:PYTHONIOENCODING = 'utf-8'
$groundingRunOutput = 'K:/Music Analysis/output/factor-grounded-relations-new-run'
if (Test-Path -LiteralPath $groundingRunOutput) { throw '새 실행 폴더를 지정하세요.' }
& './.venv/Scripts/python.exe' -u -m musicanote_harness.factor_grounded_relation_trial --relations 'K:/Music Analysis/output/factor-function-relations-2026-10-01-r1' --output $groundingRunOutput --max-profiles 65536 --max-motion-kernels 65536 --max-motion-pairs 65536 --max-joint-options 65536
```

핵심/실행기 검사는 각각 `python -m unittest test_factor_grounded_relations`와 `python -m unittest test_factor_grounded_relation_trial`이며 위 `PYTHONPATH` 설정이 필요하다. 두 테스트의 실제 동결 통과 이력은 이 절 앞에 기록했다. 새 output을 만들었다는 사실만으로 음악적 정확도 검수나 운영 적용이 이뤄진 것은 아니다.

## 8. 미구현과 다음 순서

이번 direct kernel은 비화성음·지연/복합 해결을 확정하지 않는다. 한순간의 전체 구성음 sounding이 어려운 분산형도 기존 직접 모델의 제한 때문에 보류될 수 있다. 이를 특정 작품의 예외나 source guard 완화로 억지로 통과시키지 않는다.

다음 큰 작업은 새 scope의 literal/source/성부 가정을 인증된 그대로 소비하는 **조건부 NCT·시간상 분산 제시·지연 해결 연결**이다. raw membership과 원음가를 유지한 채 같은 completion 아래 실제 설명량과 미설명 구간을 대조한다. 이후 조성·전체 진행·종지의 경쟁 해석을 평가하고 악보 화면에 연결한다. 교재 전체 적용, 최종 화음/NCT/cadence, 음악정답률, gold/training/생성/운영 승격은 별도 완료 기준이다.

다음 단계의 구현 단위는 다음 순서를 따른다.

1. **새 scope용 조건부 설명 계약:** 이번 source·ordered profile·actual bundle 참조를 직접 소비한다. 예전 NCT 엔진의 다른 부모 계약을 재봉인해서 같은 입력이라고 위장하지 않는다. 원 비구성음을 삭제하거나 NCT로 확정하지 않고, 설명 후보·필수 전제·보류·original note-time을 별도 보존한다.
2. **NCT의 같은 성부 연결:** 경과·보조·선행·준비된 계류 등의 실제 준비/이탈/복귀·진행을 한 completion 아래 대조한다. 필요한 음이나 박자·출처·연결을 확인할 수 없으면 해당 규칙을 보류한다. 하나의 음가를 경쟁 규칙들이 중복으로 설명했다고 합산하지 않는다.
3. **시간상 분산 제시와 지연 해결:** 단일 boundary cell의 완전 구성음 조건과 구간 동안의 순차 제시를 별도 모델로 둔다. 구성음의 제시 순서·지속·재타격·공통음·베이스·앞뒤 화음의 경쟁 설명을 대조한다. 구간의 PC 합집합이 맞는다는 이유만으로 한 화음을 인정하지 않으며, 이미 바뀐 화음의 음을 앞 화음의 누락음으로 끌어오지 않는다. 이끎음·7음이 늦게 해결되는 시간 경로도 필요한 모든 연결이 같은 completion에서 함께 성립해야 한다.
4. **공동 비교와 범위 확대:** 같은 후보 universe·같은 문맥에서 직접 모델과 시간 모델의 설명량/미설명·전제·충돌을 대조한다. 첫 5문맥의 실패 이유를 검증한 뒤 준비된 나머지 cohort로 단계적으로 확대하고 whole-budget 보류와 미실행 분모를 유지한다. 합성 검사·실제 악보 재현·사람의 음악적 검수는 구별한다.

이는 다음 개발 계획이며 위 1–4를 이번 r1에서 실행하거나 NCT·분산형 판정 완료로 선언한 것이 아니다.
