# 다음 기능 단위 — 배치 밖까지 연결하는 진행 후보 대비

2026-10-03. [단계29 실제 replay](2026-10-03-fresh-replay-resource-preflight.md)가 실행 중인 동안 읽기 전용 코드 검토로 기획했다. 구현·실제 대비·정책 적용은 아직0이다. 현재 계산의 보호 코드/입력/분모/산출물을 바꾸지 않는다.

## 목적과 경계

Fresh native/role 결과를 모든 배치에 저장하는 것과, 그 결과를 서로 경쟁하는 진행으로 비교하는 것은 다른 기능이다. 같은 음악 구간·명시 key·한 원 completion의 완전 경로들을 함께 비교해야 한다. 저장 배치 경계가 음악적 경계나 후보 비교 범위를 결정해서는 안 된다.

기존 `native_progression_contrast`와 policy의256요청 제한은 유지한다. ≤256개의 조각을 기존 public API에 넣고 각 조각의 winner를 합치는 방식은 사용하지 않는다. 이번에는 **새 saved-only cross-batch adapter**의 명시 계약·검사·실행기를 개발한다. 원 intrinsic 의미, native/role 권한, 음악적 지원 규칙을 바꾸지 않으며 저장 SHA를 live native 권한으로 사용하지 않는다. 기존 `_pair`에 상당하는 두 검증 facet의 대비 의미를 새 계약에서 재현하고 작은 자료에서 기존 결과와 정확히 대조한다.

## 대상과 사전 분모

현재 등록된 두 구간의 모든 원 요청을 유지한다. 전곡 범위/새 후보 pool로 확장하거나 결과가 나쁜 후보를 미리 제외하는 단계가 아니다.

| 등록 구간 | 한 completion/key의 entry | 원 completion × key 그룹 | distinct unordered pair |
|---|---:|---:|---:|
| Sonata | 463 | 2 × 5 = 10 | 10 × C(463,2) = 1,069,530 |
| Quartet | 342 | 2 × 5 = 10 | 10 × C(342,2) = 583,110 |
| 전체 | 요청 발생8,050 | 20 | 1,652,640 |

이는 제출된 selector의 모든 쌍이며 모든 가능한 음악 진행을 탐색했다는 뜻은 아니다. Parent의 원322문맥/1,013raw lanes·선택2/7·미실행320/1,006·등록pool5·제안/미제안 경로 분모를 함께 보존한다.

Group identity에는 exact source/scope/lattice/key/bundle뿐 아니라 **원 completion request identity**도 포함한다. 두 completion의 bundle 본문이 우연히 같아도 원 요청과 분모를 합치지 않는다. 다른 key/completion의 유리한 근거를 한 후보로 모으지 않는다. Binding·원 selector index·origin·partition·transition vector·output refs의 exact join이 선행 조건이다.

단계29의 `computation_integrity_passed=true`만으로 전체 대비를 허용하지 않는다. 정상적인 whole hold에도 integrity는 참일 수 있다. 모든 원 indexed selector/native/role 위치와 정확한 terminal/body가 있어야 full comparable inventory다. 누락/withheld path가 있으면 원8,050entry/1,652,640pair 분모의 영향을 held/uncomputed로 보존하며 알려진 빈 요청으로 줄이지 않는다. 완전한 body 안의 role-path `unassessed`와 body 자체가 없는 미실행은 다르다.

## 한 번의 검증, 반복 가능한 작은 대비

1. 전체 manifest·hash·원순서 및 모든 native/role body를 한 번씩 검증한다. 원 source-note refs/철자/full tie/actual attack·유리수 시간·raw 계정·role union/unknown 계약을 유지한다.
2. 검증된 entry facet과 source/origin/sound/role evidence catalog를 만든다. 각 facet은 원본문을 재현할 수 있는 immutable ref를 갖고, 검증을 건너뛰는 요약-only entry를 받지 않는다.
3. Source별 모든 관련 cut/category/bass cell의 공통 유리수 refinement를 계산하고 각 entry의 vector를 한 번 전개한다. Fraction을 사용하거나 LCM/overflow가 검사된 정수 tick을 사용할 수 있다. Float 음가나 tolerance로 alignment를 고치지 않는다.
4. 고정된 group의 upper triangle을 bounded block으로 비교한다. 전체1,652,640쌍의 Python 객체/JSON을 한 번에 만들지 않는다.
5. 정확한 terminal과 모든 block/pair coverage를 확인한 후에만 전체 computed 대비 aggregate를 저장한다. 최종 화성/NCT/key/cadence·winner/confidence·학습/Gold/UI 승격은 하지 않는다.

공통 refinement의 목적은 pair마다 큰 source body를 복사하거나 반복 `_cover`를 수행하는 비용을 줄이는 것이다. 예상 형태 `O(N·atoms + pairs·atoms)`는 기획 방향이며 실측 성능 보장은 아니다. Time/space 상계·정규화 의미·작은 자료의 exact equivalence가 구현 검사 대상이다.

기존 `_pair`는 두 entry의 union 경계로 pair-specific cell을 만든다. 전역 atom의 단순 합계가 같다는 것만으로 equivalent라고 보지 않는다. Sound별 multiplicity·각 entry의 원 segmentation/cut·별도 bass-cell 경계를 유지하고, global atom에서 기존 pair cell을 결정론적으로 materialize/coalesce하여 그 구조/원음표 근거/음가까지 exact 대조해야 한다. 같은 category가 인접한다고 원 cut이나 다른 sound를 지우는 coalescing은 금지한다.

## Block coverage 계약

제안 block size는64이며 실행 전 확정한다. Sonata463은8block·36 upper-triangle block task/group, Quartet342는6block·21task/group이다. 10개씩 적용하여 총570task다. 비대각 block은 최대4,096쌍, 대각은 `i<j` combinations이며 tail을 그대로 포함한다.

각 block은 group/refinement/entry-inventory digest, ordered row/column index range, expected pair count, computed/held/unpersisted count, bytes와 output hash를 갖는다. Pair는 `(i,j), i<j` 순서를 사용한다. 대각과 비대각의 중복·누락, 같은 pair의 다른 block 재저장, group 밖 entry 또는 stale inventory를 거부한다. Block terminal은 전역 완료 terminal이 아니다.

## 저장할 최소 정보

긴 음표·철자·타이·source-note·베이스·ordinary/기능 본문은 shared catalog에 한 번 보존한다. Pair에는 다음을 저장하고 pointer로 상세 설명을 재구성한다.

- 두 entry index와 정확한 group/refinement 참조.
- Candidate-only/transition-only/양쪽 변경/partition 등 기존 대비 kind, alias·공통/서로 다른 cut.
- 여섯 category의 유리수 delta와 category transfer matrix, 바뀐 atom/bass-cell pointer.
- 원 raw 계정·role union·ordinary/functional 근거의 catalog pointer, 미상/미평가 사유.
- Pair calculation status, 논리 작업 charge, output provenance. 최종 음악적 outcome은 `null`이다.

최소화는 source evidence를 버리는 것이 아니다. Catalog pointer만으로 원 두 facet의 음표/시간/공통 조건과 대비 설명을 정확히 복원하는 검사와 schema가 필요하다. 새 codec/version을 명시하며 과거 큰 body를 소급 교체하지 않는다.

## 미상·보류·중단을 구별하는 규칙

`computed contrast`는 계산된 차이를 뜻하고 정답/승자를 뜻하지 않는다. Upstream **conditional explanation credit**이 `null`이면 그 credit의 delta도 `null`이며 미계산을0으로 바꾸지 않는다. 이는 관측된 여섯 category의 항상 유리수인 note-time delta와 별개다. Conditional credit 미상 때문에 관측 category 계정 전체를 null로 지우지 않는다. 음악적 미판정과 사전 budget whole hold, runtime hold, 저장 실패를 구별한다. 일부 entry 미지원/보류가 있으면 원 pair 분모와 영향 범위를 보존하고 지원된 prefix만 전체 완료로 보고하지 않는다.

모든 entry/pair/block·logical work·decoded/encoded bytes·최종 manifest reserve를 계산 전에 계획한다. 한도 초과는 전체 요청을 명시 보류한다. 예기치 않은 중단/partial write는 전체 계획 분모·저장 subtotal·미저장 complement·부분 bytes/hash를 남긴다. 완료 aggregate는 만들지 않는다. Exclusive write·원입력/과거출력 보호를 유지하고 기존 cap을 설명 없이 올리지 않는다.

## 자원 pilot와 완료 기준

현재900쌍 실험 시간에1,652,640/900을 곱해 runtime을 확정하지 않는다. 결과를 보기 전에 첫 block과 최대 pair/refinement/reference/encoded 상계 block을 선정해 두 원 completion에서 시간·peak memory·압축 크기를 계측한다. 상계가 실제 재료로 계산되지 못하면 미상으로 남긴다. Pilot 통과와 모든570task 완료는 구별한다.

구현/검사 순서는 작은 계약→저장/중단→현재 실제 body의 read-only admission→resource pilot→전체 대비다. 최소 반례는0/1entry·64/65entry·tail block·다른 batch의 경쟁 pair·같은 bundle의 두 원 요청·null/known zero·미지원/hold·중단/partial write·input/hash/refinement 변조·중복/누락 pair·float time 혼입이다. 작은 자료의 기존 대비 exact equivalence와 전체 pair coverage·원음가 보존의 독립 감사가 완료 조건이다.

이번 기능에서는 기존 policy256 한도로 전체 조건부 선택을 수행하지 않는다. **정책 적용은 deferred**로 명시한다. Pair 승리 수·설명량·member 수·cut 수를 합산해 winner를 만드는 방법은 계획에 포함하지 않는다. 이후 정책의 전체 scope 계약을 별도 기능으로 개발하고, 음악적 검수와 악보 UI 연결은 그 상태를 구별하여 진행한다.

## 읽기 전용 설계 검토

독립 코드 대조에서20group/1,652,640pair/570task의 산술과 구현0·policy/UI 미적용 상태를 확인했다. 큰 계약 위험 세 가지(전역 atom과 기존 pair cell의 exact 재구성, nullable conditional credit과 유리수 category delta 분리, integrity-only whole hold를 완료로 오인하지 않기)를 위 규칙에 보완했다. 실행 중 producer/코드/입력/결과 변경이나 대비 실험은 없었다.

보완 후 재검토에서도 추가 차단 결함은 발견하지 않았다. 다만20contrast group과 policy의 `partition + transition-vector` fixed-premise group은 다른 계층이며 혼동하지 않는다. 동일 signature의 origin alias는 보존하고, 같은 logical tuple의 중복 검증과 alias 보존을 구별하는 것이 구현 조건이다.
