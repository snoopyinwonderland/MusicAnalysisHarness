# Native 다중 화음 진행의 조건부 음표 역할과 union 계정

개발 기록 ID: `HARM-DEV-20261002-24`.

## 1. 목적과 범위

직전 [native interval lattice](2026-10-02-native-multi-slot-interval-lattice.md) §7.1에서 계획한 역할 설명을 새 native complete partition에 연결한다. 여러 slot의 관찰·화음 후보·명시 key·transition vector·실제 전 raw-lane completion이 같은 조건에서 성립해야 한다. 이전 two-slot 설명을 잘라 새 구간에 재봉인하지 않는다.

새 `factor_native_role_explanations`는 연구용 sidecar다. 기존 native `profiles`, `whole_path_account`, `function_shapes`, `transition_contexts`, cadence 전제를 수정하지 않는다. 원XML/IR/parser, frozen 공급기·이전 출력, 운영 뷰어/구조/생성 계산과 Git은 이번 범위가 아니다. 다음 파일들을 새로 추가한다.

- `src/musicanote_harness/factor_native_role_explanations.py`: 발급·역할 전제·합집합·검증.
- `src/musicanote_harness/factor_native_role_trial.py`: 제한된 실제 문맥의 append-only 실행.
- `tests/test_factor_native_role_explanations.py`: genuine XML→Core→native 공개 경로 검사.
- `tests/test_factor_native_role_trial.py`: 저장·입력 등록·실행 범위의 storage-only 검사.
- 이 문서, 메인 문서 최신 상태, 별도 화성 개발 로그.

## 2. 발급·연결 계약

`prepare_explanations(native_session, comparison)`은 등록된 native handle을 요구한다. 저장 record의 seal만 믿지 않고 **그 session에서 exact selectors, 등록 bundle ID, 원 resource limits로 `native.compare_prepared`를 다시 계산해 전체 typed JSON을 대조**한다. 일치한 결과만 별도 immutable/HMAC/weak-registry handle로 발급한다. Native 입력 자체는 기존 발급 절차에서 full IR와 scope를 검증한다. 저장 lattice/bundle을 신규 권한으로 사칭하지 않는다.

`explain_prepared(handle, query_work_budget=1000000)`은 새 role/path ID를 붙인다. Parent comparison/path/tuple/origin/key/bundle refs, exact partition, transition vector, 원 logical universe를 보존한다. ID 없는 raw account는 `{parent_path_ref, field: "whole_path_account", sha256}`로 연결한다. `validate_explanation_prepared`는 같은 owned session에서 새 계산 전체를 대조한다. 반환 dict를 수정해도 session 내부 결과는 바뀌지 않는다. 복사하거나 직접 만든 handle은 발급 권한이 없다.

Contract에는 native producer closure와 새 source·재사용 pure-helper source SHA가 들어간다. 새 계층은 shared-window 공급기를 frozen native에 소급 주입하지 않는다. Loaded-runtime의 임의 monkeypatch까지 방어하는 범용 보안 경계나 모든 parent 파일의 전체 cold replay를 선언하지 않는다.

상위 session handle만 아니라 발급 당시의 정확한 authenticated native state identity도 캡처한다. 별도로 유효하게 인증된 다른 parent state로 교체됐더라도 기존 child handle은 거부한다. 이는 white-box 발급 불변식 검사이며 공개적인 보안 취약점이 발견됐다는 주장과 다르다.

## 3. 일반 음악 규칙

### 3.1 Slot 내부 passing/neighbor-like 관계

같은 등록 completion의 실제 연속 링크 `x→y→z` 두 개를 요구한다. 가능한 graph edge를 실제 연결처럼 빌리지 않는다. 세 full sounding spans가 하나의 slot 안에 있어야 하며, 후보 아래 membership은 `member→nonmember→member`다. 두 이동은 정수 written pitch의 보통 순차 이동(동일 방향의 diatonic ±1, semitone ±1/±2)이다. Neighbor는 처음과 끝의 철자·octave가 같아야 한다. 가운데 sound만 설명한다.

Accent, consonance와 확정 passing/neighbor NCT 판정은 아직 없다. 한 slot이 triple을 자르면 full span을 보존하고 미판정으로 둔다. 한 edge만 있는 bundle에는 local triple이 성립하지 않는다.

### 3.2 인접 경계의 선행음·계류-like 관계

각 native adjacent pair에서 새로 계산한다. 준비 attack은 왼쪽 slot에, involved full sounding spans는 인접 pair의 full envelope에 들어와야 한다.

- **Held:** 동일 sounding event가 `start < cut < end`다. Tie continuation은 새 attack이나 가짜 self-link를 만들지 않는다.
- **Reattack:** 다른 sound ID, 정확한 `release=attack=cut`, 동일 written register와 실제 링크가 필요하다.
- **Anticipation-like:** 왼쪽 nonmember, 오른쪽 member. 왼쪽 clip만 설명한다. Intrinsic held anticipation은 no-link completion에서도 가능하다.
- **Suspension-like:** 왼쪽 preparation member, 오른쪽 carry nonmember, 동일 completion에서 첫 실제 pitch change가 하행 순차 target member여야 한다. Endpoint attack은 오른쪽 `[cut,end)`에 있어야 한다. 오른쪽 carry만 설명하고 해결 endpoint는 제외한다.

첫 변화가 불리해도 뒤의 유리한 음으로 건너뛰지 않는다. 두 cut을 넘는 지속음/해결 route는 이번 버전에서 **unassessed**다. Clip만 잘라 문맥 결손을 숨기지 않고 full spans와 proposed clips를 남긴다.

### 3.3 명시 ordinary 이끎음·7음 역할

Native의 actual first-change ledger를 참조하되, 그것만으로 credit하지 않는다. 명시 source/target function shape, source-critical member, endpoint attack 범위, 모든 route의 source/clock/pitch/attack/point/grace guard와 adjacent full envelope를 추가 검사한다. 원 native ordinary/cadence 결과는 바꾸지 않는다.

이끎음은 derived target root로 반음 상행, 7음은 target member로 보통 순차 하행이다. 역할별 occurrence **OR**, 필요한 역할 간 **AND**를 동일 bundle에서 계산한다. 한 doubling 성공이 모든 doubling 해결을 의미하지 않는다. Whole template이 미충족이면 그 ordinary stage의 clip credit은 없다. Local/boundary stage는 각각의 독립 전제가 충족될 때 별도로 남는다.

Unknown key에서 literal role/shape 설명은 가능하지만 Secondary/primary/tonicization/modulation/cadence를 확정하지 않는다. 이 단계는 key likelihood나 최종 화음 선택기 아니다.

Ordinary critical pitch 철자 자체가 없거나 source/target 후보가 spelling-withheld라면 template은 `None`이다. 준비된 역할의 실제 연결이 없는 known no-link 실패(`False`)와 구별한다. 원 native ledger를 덮어쓰지 않고 새 template의 `prerequisite_blockers`에 미판정 사유를 보존한다.

## 4. 유리수 시간·계정

모든 범위는 rational quarter의 `[start,end)`다. 하나의 exact native path/key/transition vector/bundle 안에서 지원되는 clip들을 sound별 union한다. 그 뒤 각 raw profile row와 **guarded nonmember** 시간에 교차한다. Member/unknown/unsupported 시간에는 credit하지 않는다. Local/boundary/ordinary가 겹쳐도 시간은 한 번만 계산한다.

여섯 범주를 보존한다.

| 범주 | 뜻 |
| --- | --- |
| `source_guarded_member` | 후보의 source-guarded 구성음 시간 |
| `conditional_explained_nonmember` | 이 동일 completion에서 조건부 설명된 시간 |
| `unexplained_nonmember_under_this_completion` | 평가했으나 이 completion에서 설명되지 않은 시간 |
| `unassessed_nonmember` | completion 등 평가 전제가 없는 시간 |
| `membership_unknown` | 철자 membership을 결정할 수 없는 시간 |
| `source_or_hypothesis_unsupported` | source/hypothesis guard가 부족한 시간 |

불변식: 여섯 범주 합=`raw total`, sound별 최종 union 음가 합=`credit`, `credit≤guarded nonmember`, parent raw states·total 불변이다. `None`과 `0`을 구별한다. Complete no-link의 실제 평가 실패는 False/0이지만, incomplete completion·source·whole work hold는 미판정이다. Held anticipation의 no-link 지원은 예외가 아니라 intrinsic carry 계약이다.

## 5. 예산·집계

새 질의는 source-note closure, 모든 제출 path의 slot/internal cut, local/boundary/ordinary clause 상한, 실제 route visit 상한, profile intersection과 union endpoint/visit 상한을 **전체 요청에 대해** 먼저 계획한다. 초과 시 전부 hold하며 유리한 prefix를 계산하지 않는다. 모든 budget은 bool을 허용하지 않는 nonnegative integer다.

이는 역할 질의의 보수적 logical-work 상한이다. CPU 시간·peak RSS·직렬화 byte 상한 또는 native 공급 비용을 뜻하지 않는다. Native lattice 생성·exact comparison replay는 준비 단계의 별도 비용이며 원 native caps를 따른다. 기존 provider window 공유 성능을 이번 native 비용으로 확대하지 않는다.

예상 clause 상한, 실제 evaluated/qualified/satisfied/failed/unassessed 발생, unique geometry와 credit sound occurrence를 별도 집계한다. Origin/key/path에 따른 반복 발생을 음악 정답·작품 수·confidence로 해석하지 않는다. 모든 selected/rank/confidence는 null이며 final harmony/NCT/key/cadence·Gold/학습/생성 승격 flags는 false다.

- `qualified`: source/hypothesis/full-span guard가 평가를 허용한다는 뜻이다. 음악적 전제의 참을 뜻하지 않는다.
- `evaluated_clauses`: 시도한 clause 전체 발생이며 `unassessed`도 포함한다.
- `satisfied_clauses`: 개별 전제 지원 수다. Ordinary의 다른 필수 역할이 실패하면 개별 `supported`라도 whole template=False, `clips=[]`일 수 있다. Credited clause/음가 수와 같지 않다.
- Source-note 참조 closure도 각 clause/route의 **반복 발생**을 예산에 포함한다. 긴 tie-chain 참조를 한 번만 세고 여러 가설에 무제한 복사하지 않는다.
- Native 전체 work hold에서도 원 request snapshot과 planned/withheld 분모를 보존한다. 역할 상한은 유효하게 검증된 exact selector 길이와 source inventory로 계산 가능한 보수적 수량이며 실제 역할 평가 수가 아니다. 빈 selector 요청은 query work=0인 known-empty다.

## 6. 검증·실제 실행 기록

### 6.1 공개/반례 검사와 교정 이력

최종 신규 **57개/96.814초**, 실패·오류0/exit0이다. 그중 긴 tie source-reference 상한의 pure arithmetic 검사1개를 다른 공개/API/white-box 검사와 구별한다. 모든 검사가 실제 음악 양성이거나 작품 수인 것은 아니다. Genuine XML→Core fixture를 조합하고 신규 native issuer·origin·full-scope bundle·comparison 경로를 사용한다. Old TestCase를 상속해 기존 검사 수를 증식하지 않았다.

검사에는 passing/neighbor, 세 slot, fractional thirds, member 경쟁 후보, held/tie/동음 재타격, anticipation/suspension/ordinary 단계 분리, 첫 불리한 변화, doubling, 같은 음의 여러 설명 union, missing edge/무연결/성부 branch·음역·enharmonic·grace/microtone/attack guard, multicut, unknown key, wrong family, 철자 미결정과 known no-link의 차이, 전체 budget/빈 요청, exact request/발급·변조를 포함한다.

초기 **52개/107.124초 중 50PASS·1FAIL·1ERROR**는 최종 통과에 더하지 않는다. Enharmonic fixture의 기대 origin이 genuine 공급에 없는데 있다고 가정한 것과 미판정 credit=`None`을 Fraction으로 읽은 테스트 가정을 수정했다. 음악 판정을 유리하게 만들려고 production/core XML을 수정한 것이 아니다. 다음56개/94.537초 PASS도 최종57개와 중복인 중간 검사다.

독립 검토에서 발견해 보완한 제품 계약 문제도 보존한다.

1. Parent 전체 hold에서 child planned/withheld 분모를 0으로 잃던 문제: 원 exact request snapshot과 분모를 유지했다.
2. Parent handle만 묶고 정확한 authenticated state identity를 묶지 않던 문제: 발급 당시 state identity를 HMAC/사용 전후 검사에 포함했다.
3. 긴 tie의 source-note refs를 한 번만 예산에 세던 문제: 각 clause/route 발생 상한에 반복 참조 비용을 포함했다. 빈 요청은 work=0으로 유지했다.
4. Ordinary critical spelling을 모르는 경우를 known failure=False로 처리하던 문제: prerequisite blockers와 template=None을 남기고 실제 no-link/wrong-shape=False와 구별했다.

같은 문제를 독립 genuine 공개 합성 사례로 재현했고 마지막 수정 후 4개 작은 사례 재검증6.653188초도 PASS다. 앞의 별도3개 공개+1개 pure 산술3.768초 검토와 구별하며 공식57 검사 수에 더하지 않는다. 실제 corpus/화성 정확도 검수가 아니다.

별도 기존 native 회귀 **55개/61.913초 PASS**도 확인했다. 신규57+기존55가 한 번의 통합 실행이었던 것처럼 표현하지 않는다. Core와 신규 tests는 최종 실행 전후 SHA가 같았다.

| 파일 | 최종 SHA256 |
| --- | --- |
| `factor_native_role_explanations.py` | `b88cb364b683f497b2697298a6d9a55e25d08e7e39ebaed2f771415bf0f9fd97` |
| `test_factor_native_role_explanations.py` | `2a1731c4d8e9e02aae697cfa96f466516b279a17f57f22c9fa2469be450915e9` |
| `factor_native_role_trial.py` | `05ce94431711b65037c90cc081c8f2912d61a19596c55fc80bc98a8a48770872` |
| `test_factor_native_role_trial.py` | `ff7a4222c0b3681fcdc467427d9745ee8f6c3dec6dabd04b08439b9f58473c98` |

저장/metadata/closed-count 검사는 mock native issuer/calculation을 사용하는 **storage-only15개/1.463초 PASS**다. Root 별도 동일15개/1.309초 재검사도 통과했지만 신규 항목으로 더하지 않는다. 최종 wording 동결 전 15개/1.304초 중간 PASS도 별개 고유15개가 아니다. 첫 저장 검사15개 중1오류는 직접 summary fixture에 comparison seal ID가 없던 테스트 가정이어서 fixture만 정정했다. 실제 metadata-only load10.4291943초 PASS는 아래 full IR/scope와 보호4,586경로를 확인했으며 native 공급/분석 실행이 아니다.

### 6.2 제한된 실제 실행

단일 r1 실행이 **exit0/119.366852초**에 완료됐다. 저장 결과는 `output/factor-native-role-2026-10-02-r1/`다. 같은 실행을 다시 cold 재검사하지 않았다.

실제 pilot은 등록된 Sonata 01-1의 full IR와 정확 expanded scope `[49,61)` 한 문맥으로 제한했다. Fresh native `prepare_lattice(record=None)` 한 번으로 해당 scope의 모든 interval 공급을 유지하며, 기술적 full/2-slot/3-slot selector와 no-link/명시 실제 bundle을 평가했다. 원 annotation의 정답이나 작품/마디 하드코드로 origin을 고르지 않았다. 원 선언 322문맥/1,013raw lanes와 이번 실행 범위를 구별한다. 양성0을 검증 공백으로 기록한다.

| 구분 | 실제 저장 수량 |
| --- | --- |
| 실행 문맥 / 원 raw lanes | 1 / 3 |
| 전체 선언 문맥 / raw lanes | 322 / 1,013 |
| 이번 미실행 선언 문맥 / raw lanes | 321 / 1,010 |
| Fresh native preparation | 1회 |
| Observed coordinate / fresh interval catalogs / origin 대안 | 17 / 136 / 11,381 |
| Registered complete bundle | no-link1 + greedy18actual links1 = 2 |
| Full / 2-slot / 3-slot 기술 selector 발생 | 각2 = 총6 |
| Distinct origin path×key / completion까지 구별 | 3 / 6 |
| 계산된 role paths / raw 음가 보존 | 6 / 6 |
| Clause 실제 발생 / 미판정 / known 실패 / supported | 89 / 85 / 4 / 0 |
| Ordinary template 미판정 발생 | 6 |
| Conditional credit / credit sound occurrence | 0 / 0 |
| Whole native comparison / role work hold | 0 / 0 |

각 path의 원 총음가는 **85/2 quarter-note-time**으로 같고, source/hypothesis unsupported·guarded member·guarded nonmember를 별도 보존한다. 이는 12quarter의 시간 길이와 다른 값으로, 동시 성부의 음가를 합산한 note-time이다. 두 bundle에서 같은 후보의 raw state 계정은 같다. No-link의24clause는 모두 미판정, greedy의65clause는61미판정/4실패다. Local neighbor12/passing29, boundary anticipation24/suspension24 발생이며 겹치는 blocker는 단순합으로 미판정85에 대응하지 않는다.

**실제 양성 검증 공백:** first-native-ID라는 고정 기술 패널 정책 때문에 unspelled supplier origin이 여러 slot에 포함됐다. `supplier_spelling_unresolved_no_root_invented`와 slot을 넘는 local full triple이 미판정의 근거다. 모든 boundary/ordinary 미판정을 평가된 ‘해결 실패’나 NCT 오류로 바꾸지 않았다. 실제 양성·credit0은 개선이 없다는 정답 판정도, 정확도 개선의 증명도 아니다. 합성 공개 검사의 양성은 실제 작품 양성 검수와 다르다. 이후 **음표·진행 전제에 기반한 bounded 후보 패널**로 실제 양성/반례를 추가해야 하며, 원주석 정답·특정 작품 규칙·유리한 사후 prefix는 사용하지 않는다.

예산은 사전에 native query2,000,000, role query3,000,000으로 명시했다. API role default1,000,000과 다르다. 두 bundle의 role whole-request 상한은 각각 **2,790,269**이며 결과를 본 뒤 예산을 늘리거나 후보를 바꾸지 않았다. Max3selector/3slots/greedy20links와 원 native 공급 cap64coordinates/1,024catalogs/200,000variants/200,000DP-work를 유지했다. 전체 logical universe는 저장하며 전체 logical path를 실제 실행한 것이 아니다.

정확 **10출력/5,199,000bytes**, 원inputs4,586/current code·schema·tests327의 union **4,590보호SHA** 변경0이다. 원 phase22의28파일·phase23의8파일 목록도 보존했다. 새10출력은9개 artifact hash와 최종 report1개다. Report SHA는 `5d46c59b995c8e025298cbcb464c6f6bfd78b69bc95fdde3656e18733196a0b4`다. 기존 원자료·코드·출력의 전체 parent-chain cold replay나 운영 적용이 아니다.

### 6.3 독립 저장 감사와 최종 QA

독립 saved finite/유리수 산술 감사는 **37,637 assertion / 12.883512100초 PASS**다. Fresh native preparation/comparison이나 old-parent 전체 cold replay는 실행하지 않았다. 저장된 등록 full IR/binding, source sound·note·attack·tie 음가·lane, 136 catalog/11,381 origin의 seal과 source refs, 두 bundle의 실제 canonical links, 여섯 selector/path/key/bundle/raw-account refs와 native request/universe를 대조했다. 전체 선언 322문맥/1,013lanes와 실행 1문맥/3lanes를 구별했다.

89개 clause 각각의 source/hypothesis guard, membership, 실제 first-change route, full-envelope/multicut 전제, predicate와 None/False, proposed/eligible clip 방향을 독립적으로 재계산했다. Sound별 Fraction union과 여섯 범주의 합은 **여섯 path 각각 원음가 85/2**를 보존했다. 결과는 85unassessed/4failed/0supported·credit0, ordinary template6개 모두 spelling/critical-role 전제가 없어 None과 일치했다. 이것은 저장 불변식·유한 반례·미판정 동작 검수이며 실제 양성 음악 검수나 정답률은 아니다. 공식 신규 검사 수에 assertion 수를 더하지 않는다.

초기 감사가 bundle의 링크 입력 순서까지 동일하다고 요구한 것은 감사자 가정이었다. Runner의 greedy 요청 순서와 native의 canonical sorted required links는 같은 쌍이므로 canonical 순서로 대조하도록 감사만 정정했다. 제품 코드·검사·출력은 수정하지 않았다.

Root 후속 stream SHA 재검사에서는 보호4,590경로·artifact9경로 변경0/정확10파일목록 일치(3.974654초)를 확인했다. Report까지 합친 전체 고유 생성·보호경로4,600개의 각 SHA를 확인하는 범위다. 독립 감사에서도 보호4,590SHA, 원 phase22/23의 정확28+8파일 목록과 신규10파일/5,199,000bytes가 일치했다. 원 parent 전체 cold replay가 아니다. Plan SHA=`ee5f789b0485fe0792d4f30f9c09ff3bf80402d075d3f319b3fe9041ba8ff632`, index SHA=`cfcff39ab23eaae745d70f9757e6fd9a4dc2e397a3b4b013835a3b6539db7c4f`다.

최종 QA에서 이번 source/test4개와 문서3개의 strict UTF-8/NUL/U+FFFD/행 끝 공백, Python AST4개, 세 문서의 로컬 파일 링크126개를 확인했고 오류0이다. 동결 source/test4개와 report/plan/index3개 SHA도 일치했다. Read-only `git diff --check`는 exit0이며 기존 별개 tracked5파일의 LF→CRLF 경고는 보존하고 이번 변경의 오류로 집계하지 않는다.

## 7. 다음 단계

먼저 같은 계약의 실제 역할 양성·반례 범위를 여러 작품에서 확보한다. 그 다음 이 evidence를 완전 진행 비교에 함께 소비하고, unknown/multicut·voice·key 전제가 부족한 구간을 별도 미해결 목록으로 남긴다. 역할 설명량 하나로 최종 화음을 선택하지 않는다. 실제 검수와 선택 정책이 준비되면 기존 전체 악보 뷰어로 연결한다. 작곡/편곡은 검증된 별도 분석·의미 레이어를 소비하며 Core를 수정하지 않는다.
