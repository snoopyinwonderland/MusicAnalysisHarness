# 원음표 근거의 화음 다양성·혼합 경로·형태별 진행 요청

개발일: 2026-10-02. 단계: HARM-DEV-20261002-28.

## 목적과 이번 단계의 경계

직전 [조건부 제안·보류 정책](2026-10-02-progression-proposal-hold-policy.md)의 다음 큰 기능 단위다. 당시 입력은 원음표의 pooled support로 고른 두 zipped 경로와 모든 cut의 일률 V7/M 요청에 제한됐다. 실제200가정의 strict 지원0을 보고 지원 조건을 낮추는 대신, **평가에 제출할 화음 후보·혼합 경로·관계 가정의 공급 범위**를 보강한다.

이번 산출물은 저장된 원음표에서 만드는 **새 요청 계획**이다. 새로운 native 진행 평가, 같은 성부 completion의 해결 판단, 화성 정답 선택 또는 기존 악보 UI의 개선 결과가 아니다. 기존 source/XML/Canonical Core/음표 ID·음가, 원주석, phase25/26/27 코드·산출물을 보존한다. 새 파일에만 제안과 후속 fresh 실행 계획을 저장한다. 어떤 작품명·마디 번호도 규칙의 조건으로 사용하지 않는다.

## 코드와 입력 계약

- 핵심: [`source_progression_proposals.py`](../../../src/musicanote_harness/source_progression_proposals.py), `source-progression-proposals-0.1.0`.
- 저장기: [`source_progression_proposal_trial.py`](../../../src/musicanote_harness/source_progression_proposal_trial.py), `source-progression-proposal-trial-0.1.0`.
- 핵심 검사: [`test_source_progression_proposals.py`](../../../tests/test_source_progression_proposals.py).
- 저장 검사: [`test_source_progression_proposal_trial.py`](../../../tests/test_source_progression_proposal_trial.py).

공개 API는 `propose(scope, lattice, prior_panel, *, work_budget=3000000, max_paths=512, max_selectors=4096)`다. `npsprop_` 결과는 원 scope/lattice/panel ref·full IR binding·rational span·native logical universe를 참조한다. 입력 seal·원 catalog/좌표/ordered origin·등록 key를 확인하고 원 source evidence/top2/control 순서를 다시 대조한다. 호출 시작/끝의 입력 digest와 현재 코드 계약을 비교한다. 이는 persistent 변경 검출이지 임의 동시 ABA 변경까지 보장하는 보안 인증이 아니다.

내용 seal은 live native authority가 아니다. 저장기는 phase27 creation SHA와 exact archive inventory, 원 full IR·source snapshots·scope/lattice/panel의 등록 관계, 원순서 네 completion/policy rows를 검증한다. 구간은 제목으로 합치지 않고 전체 source registration identity로 구별한다. 같은 source의 두 completion을 source 제안 두 번으로 중복 계산하지 않는다.

## 일반 음악 규칙 S01–S09

| 규칙 | 구현과 한계 |
|---|---|
| S01 | 기존 모든 control selector를 원순서로 유지한다. 불리한 V7/M·미선언 None 가정도 지우지 않는다. |
| S02 | 요청한 기존 whole/half/third partition의 모든 native origin을 관찰 음표와 대조한 후 대표를 만든다. 나머지 모든 lattice interval까지 source 평가했다고 주장하지 않는다. |
| S03 | `root`와 **ordered members**로 완전한 관례적 3/7화음 철자를 확인한다. `(triad/seventh, quality, spelled root)`마다 하나의 대표를 보존하고 nonordinary/unassessed의 대표 및 원 top2도 유지한다. PC 집합/동일 member SET만으로 ordinary·전위를 확정하지 않는다. |
| S04 | 실제 guarded 구성음의 미관측 수·member/nonmember/unknown/unsupported note-time과 source note/sound refs를 보존한다. 빠진 음은 자동 생략·분산형 완성·화음 부재가 아니다. |
| S05 | 원 두 zipped seed와 **한 slot만 바꾸는 모든 경로**를 제안한다. 두 slot 이상을 동시에 바꿔야 하는 경로는 여전히 빠진다. Eligible 전체 Cartesian origin path와 미제안 수를 따로 기록한다. |
| S06 | 각 cut에서 V/V7/vii/vii7/vii_half7 × 목표 M/m의 원 철자 형태를 확인한다. source shape와 target triad core shape가 모두 True일 때만 해당 관계 요청을 추가하고 None도 항상 보존한다. source의 넓은 member superset을 strict V7으로 축소하지 않는다. |
| S07 | 모든 등록 조성 가설과 unknown을 분리해 같은 완전 vector를 요청한다. 임시표·shape·적용 도수만으로 Secondary/Modulation/조성을 확정하지 않는다. |
| S08 | source proposal은 actual links·첫 변화·전체 leading/seventh obligations·NCT credit·독립 경계·종지를 계산하지 않는다. 같은 signature의 cut도 새로운 화성 교체로 인정하지 않는다. |
| S09 | 전체 원음 스캔·path construction·shape 호출·완전 vector 수와 한도를 확인하고 초과하면 전체 hold한다. favorable prefix를 저장하지 않는다. 기존 controls는 보존하되 부분 후속 평가를 예약하지 않는다. |

3화음을 빼놓지 않지만 일반 ii→V·지속/연장 관계까지 새로 지원했다고 주장하지 않는다. 현재 family 계약에 맞지 않는 관계는 None/미평가다. 분산화음·페달·생략·성부 재배치의 증거도 자동 만들지 않는다.

### I→IV와 적용화음 형태의 경쟁 예

C–E–G → F–A–C는 C major에서 일반 I→IV 진행일 수 있다. 동시에 기존 function kernel의 **F를 목표로 하는 V/M 형태**에도 맞는다. 따라서 None과 V/M 형태 요청을 둘 다 유지한다. 이 요청을 V/IV Secondary 확정으로 읽으면 안 된다. 실제 function은 같은 completion의 해결·문맥·조성·경쟁 해석을 추가 검증해야 한다. ‘일반 I→IV를 아직 지원하지 않음’은 V/M 형태 경쟁 요청을 삭제한다는 뜻이 아니다.

## 데이터와 분모

- `intervals`: requested catalog별 모든 native/eligible/rejected 수, quality/root bucket별 수·ordered signature 수·대표 ref·미제안 수, 원 top2와 새 대표의 실제 source evidence.
- `complete_proposal_paths`: 원 seed와 single-slot 교체 provenance, 각 원 origin ref와 전체 ordered partition.
- `partitions`: sampled paths 대 전체 eligible Cartesian origin paths와 미제안 수. 구조적으로 불가능한 quantile partition은 알려진0이며, 원 inventory 미상은 전체 hold/null과 다르다.
- `shape_request_groups`: path×key×cut의10형태 대조, None+compatible options, 각 cut options의 완전 vector Cartesian 수. `resolution_support`, `secondary_support`, `boundary_support`, `same_completion_ref`는 모두 null이다.
- `retained_control_selectors`/`additional_selectors`/`selectors`: 원 controls와 정확 fingerprint로 중복 제거한 새 요청을 구별한다. Alias는 기존 control 또는 새 요청의 index를 참조하며 근음/철자/출처를 바꿔 합치지 않는다.
- `native-replay-plan.json`: 두 source의 원 두 completion control을 각각 참조하는 **미실행** 계획이다. 같은 selectors를 네 번 복제하지 않고 결과 record/field pointer로 연결한다.

한 bucket 안의 모든 공급 origin을 제출하지 않는다. 같은 quality/root여도 다른 reading/provenance가 있을 수 있으며 미제안 수를 보존한다. Nonordinary 대표는 해당 전체 bucket의 제한된 표본이다. 제안 순서는 final rank가 아니며 `selected`, `rank`, `confidence`는 null이다. Source note-time은 동시 성부가 더해진 note-time이지 wall-time·확률·정답률이 아니다.

## 한도와 보류

기본 work3,000,000/path512/selector4,096은 논리 방문 allowance다. CPU 시간·RSS·음악 정확도 보장이 아니다. 전체 input tree·source diagnostics/refs·origin member 스캔과 정렬, 한 slot 대체 경로, path×key×cut×family/quality shape 및 vector materialization을 계상한다. Sound source guard는 call-local 한 번 캐시한다. 기존 source producer의 과거 결과나 후속 역할 성공을 보고 유리한 후보만 먼저 제출하지 않는다.

`max_paths`는 work로 사전 제한한 경로 구성 뒤의 결과 개수 제한이며 RAM 상한이 아니다. Selector 한도는 중복 제거 전 모든 vector와 기존 controls의 합으로 보수적으로 검사하므로 실제 unique selector 수보다 큰 한도가 필요할 수 있다. Full JSON input의 validation/digest visits도 비용에 포함하며, 한도는 음악 판단의 threshold와 구별한다.

`whole_source_proposal_hold`이면 새 intervals/paths/shape groups/aliases와 `additional_selectors`는 비어 있다. `retained_control_selectors`와 `selectors`에는 원순서 기존 controls만 남는다. Summary의 requested intervals/retained controls는 알려진 수, 나머지 계산 결과 수는 null이다. 확인된 empty source panel은0으로 계산되며 ‘원음악을 다 이해함’을 뜻하지 않는다. Read/output byte admission은 work limit와 별도로 보존한다.

## 검사·실제 실행·보존

### 개발 검사와 교정

핵심 최종27개/37.616초 PASS다. Genuine 작은 MusicXML→IR/native 입력을 fixture 준비에 사용하지만, 새 consumer 검사에서는 native/role/기존 panel producer 재실행을 금지한다. Core의 root별 bucket·ordered member·원 controls·혼합 경로·전체 vector·unknown key·whole hold·입력/계약 변경 검출을 검증한다. 이전 source panel47개/26.803초 회귀 PASS는 신규 검사 수에 합산하지 않는다.

초기23개/31.028초, 보강25개/36.074초 PASS 및 첫27개/36.626초의 fixture 기대 실패1건을 최종 검사와 구별한다. 해당 실패는 실제 fixture pool에 4개보다 많은 member의 origin이 있다고 가정한 검사 오류다. 실제 native origin을 위조하지 않고 기존 V7의 assumed members에9음을 더한 **pure shape 반례**로 교정했다. 이 반례는 새 실제 후보/완전 workflow 양성 검증이 아니다. 독립 검토로 root까지 분리한 ordinary bucket, 호출 전후 input/contract digest, path/shape/vector 사전 work reservation을 보강했다.

저장기의 독립 검토에서 정확한 원 seed·single-slot 경로/provenance/partition/interval 순서, literal signature, sound/source-note/full span/clip 연결, 알려진 planned work의 합계 대조를 보완했다. 이 검사는 저장된 선언·원 참조·유리수 산술의 일관성 검사이며 function/source guard/bucket/역할 producer를 재실행하지 않는다. 임시 줄바꿈 `if` 문법 오류는 동결 전에 교정했으며 root의4파일 AST 검사도 오류0이다. 저장 검사 중간19개/88.425초는 변경된 SHA를 다른 유효 guard가 거부해 fixture 정규식 기대1건이 실패했고, 보강20개/92.657초 PASS는 이후 참조 보강의 최종 검사와 구별한다.

새 storage mock의 혼합 경로를 보강한 첫23개/32.111초는 temporary phase25 fixture의 필드를 `panel` 대신 `source_panel`로 접근해 setup23오류였다. 이전 실제 코드/producer/output은 변경하지 않고 새 검사 fixture만 교정했다. 교정 후 focused end-to-end1개/4.880초 PASS는 최종 full suite의 고유 검사 수에 다시 더하지 않는다.

최종 storage-only23개/109.012초 PASS이며 신규 검사는 핵심27+저장23=50개다. 재실행·감사 산술·기존 회귀를 이 수에 더하지 않는다. 두 저장 파일과 앞선 두 핵심 파일을 동결한 뒤 실제 실행을 시작했다. 새 native/역할 producer나 function inference를 저장 검사로 재실행하지 않는다.

### 저장 전 admission과 제안 생성 사전 점검

Metadata-only admission은16.75508150004316초, strict21파일/215,581,434decoded bytes를 읽고 보호4,774경로 및 부모 exact7/7/148파일을 확인했다. 두 원 full IR/scope/lattice/panel을 source identity별로 한 번 읽었다. 소나타는136catalog/11,381origin/5key, 사중주는136/7,285/5key로 전체272catalog/18,666origin/10key를 admit했다. 이는 모든 origin의 음악적 source evidence를 평가한 수가 아니다. 이 점검의 proposal/native 계산·새 출력은0이다. 당시 storage test 파일 생성 전 current code342목록은 일시 상태이며 최종 creation inventory와 구별한다.

별도의 **새 제안 생성 preflight**는43.090566299972124초, source 두 개에서 `propose`를 각각 한 번 실행하고 intrinsic 저장 joins를 대조했다. Saved output/native 계산은0이고, 새 proposal 계산은2다. 결과를 본 뒤 음악 정책을 낮춘 것이 아니라, 전체 input/source/path/vector 비용과 출력 크기로 동일 실행 allowance를 확인했다. 모든 source에 work250,000,000/path2,048/selector16,384/decoded output134,217,728bytes를 사전 선언하고 기본3,000,000/512/4,096은 유지한다. Planned work는 각각49,873,750/47,165,094, 단일 record의 JSON bytes는20,758,214/18,412,538이다. 보호 입력 변경0이다.

### 단일 실제 r1 — source 요청 저장

[`source-grounded-progression-proposals-2026-10-02-r1`](../../../output/source-grounded-progression-proposals-2026-10-02-r1/report.json)은56.178466300014406초/exit0, source2저장·전체 hold0·failure0이다. Preflight와 별도 실행이며, 실제 r1에서도 proposal2/native0이다. Metadata registration·pure source 계산·intrinsic joins/저장이고 전곡/fresh native/역할/해결/cadence 평가가 아니다.

| 분모 | 소나타1번 등록 구간 | 현악4중주 등록 구간 | 합계 |
|---|---:|---:|---:|
| requested intervals | 6 | 6 | 12 |
| source-assessed origin 발생 | 558 | 423 | 981 |
| eligible / rejected | 330 / 228 | 285 / 138 | 615 / 366 |
| 제안 origin / 미제안 eligible origin | 232 / 98 | 189 / 96 | 421 / 194 |
| 완전 제안 경로 | 396 | 318 | 714 |
| 전체 eligible Cartesian 경로 | 31,679 | 11,172 | 42,851 |
| 미제안 Cartesian 경로 | 31,283 | 10,854 | 42,137 |
| 원 control / 추가 selector | 50 / 2,265 | 50 / 1,660 | 100 / 3,925 |
| 총 selector | 2,315 | 1,710 | 4,025 |
| 추가 compatible family/quality option 발생 | 290 | 100 | 390 |

Whole/half/third의 제안 경로는 소나타60/174/162, 사중주52/122/144다. 이 경로×5등록 key의 cut 발생은4,540, 각 cut의10종 checked shape 선언은45,400이며 추가 compatible option390과 구별한다. Bucket 발생은 소나타 triad89/seventh134/nonordinary6, 사중주75/108/3이며 원 top2 추가 때문에 bucket 수와 제안 origin 수가 꼭 같지는 않다. 음악 정답·곡·독립 chord 수 또는 정확도 수가 아니다. 원322문맥/1,013raw lanes, 선택2구간/7lanes와 미실행320/1,006, 등록pool5와 원 native universe를 보존했다.

[`native-replay-plan.json`](../../../output/source-grounded-progression-proposals-2026-10-02-r1/native-replay-plan.json)은 원 두 source의 두 completion controls를 각각 참조하는4개 **향후 작업**이다. Planned selector 발생8,050에는 동일 source 제안을 두 completion에 적용하는 반복이 포함되며 unique source selectors4,025와 구별한다. Retained control 발생200, fresh native session0/native evaluation0이다. 현재16미승격 flag는 모두False, selected/rank/confidence와 resolution/secondary/boundary/same-completion support는 계속null이다.

### 보존과 동결 SHA

정확6개 output/1,842,099bytes를 생성했다. Creation inputs4,774/current code·schema·tests343 및 artifact5를 보호했고 변경0이다. Root 별도 전수 stream SHA·exact inventory 검사도 report를 포함한 고유4,784경로, 신규6/부모7·7·148파일과 current343목록에서 변경0이다. 이전339creation code 목록을 소급 바꾸지 않는다. 실제 read21/215,581,434decoded bytes는 metadata 점검과 같은 입력을 다시 읽은 별도 실행이다.

| 동결 파일 | SHA256 |
|---|---|
| source core | `a294d80fe5c1f4c4fb202a68023fbaef13914c8e9cac5754f3900f9a9ad48e51` |
| source runner | `a6116e8cccbd3c17ed710ef17af195fe1f32021dfe64582559cb824842648d1f` |
| core tests | `b79a7abffdcb746f1681f0a039b7cc1fd78ff0d7dcc2b4c7683d91d76e608988` |
| storage tests | `33b86dca815ad122abb02c403d78a52dcc212f01697366ca15691d1c300c651b` |
| report | `3aad0d077220613092d5039d480ab83c41c874bf6bd208d94a7b8f0099d40208` |
| run plan | `59eb40b38531c07495a48afef993e0c69fe646f1a38ca8715fa72ee93e1ceca3` |
| context index | `a0e60172ae129314d21b5f3292bd0bd678eac696825c3ab493866ddacad45da0` |
| native replay plan | `833b87449711e2b8648ec311be79cfa551463eb5b822ca7cce169da6ab31cf22` |

### 독립 저장 감사와 실제 원음표 사례

독립 계약/산술 감사6,315,402유한 확인/18.0828762초, 오류0이다. 대부분 finite JSON visit 대조이므로 신규 unit test·음악 판단 수가 아니다. Stdlib만으로714경로의 원순서 provenance, 전체 Cartesian/미제안 수,3,570path×key 요청 그룹·45,400선언·3,985vector 발생·60ordered alias·4,025unique selector를 재구성했다. 원 controls100,421proposal의3,906member-sound record에 원 root/member/note/full-span/유리수 clip 및 pooled/raw 음가를 대조했다. Planned work49,873,750/47,165,094와4futurejobs·8,050selector 발생도 일치한다. 보호 union4,783경로와 별도 report pre/post SHA를 합친4,784, loaded19파일 및 신규6/부모7·7·148inventory 변경0이다. 초기 key prefix를 `newkey_` 대신 `fmekey_`로 가정해 중단한 감사 시도는 in-memory auditor만 교정했으며 제품/자료/결과를 바꾸지 않았다. Actual hold0이므로 held-job 차단은 코드/반례 검사이지 이번 actual negative coverage라고 주장하지 않는다.

별도 음악/source 감사는 본문182,248확인/6.9981626초, 원음가/tie 보충242확인/0.6377657초, 합산182,490/7.6359283초로 모두 오류0이다. 원 full IR/scope/lattice/prior 각2·신규6·동결core/runner2의 고유16파일 pre/post SHA 변경0이다. Requested981origin의 source guarding/member-time·ordered quality+root buckets·원 top2/controls·714mixed paths·4,025selectors·모든 omission을 독립 Fraction/set 산술로 대조했다. Unknown key의 checked 선언9,080도 삭제하거나 실패/0으로 바꾸지 않았다.299/421proposal에는 missing 구성음이 남아 있어 분산형 완성·전체 기능 지원을 주장할 수 없다. 총76sound/77note refs·원 release/음가와 raw note-time 소나타85/2·사중주53/2quarter를 확인했다. Scope wall-time12/8quarter와 다른 분모다.

실제 저장된 소나타 source 사례:

- `[49,53)`의 `fmilorigin_f918a2b9546bb9229804ca89`: E♭7 철자 E♭–G–B♭–D♭, guarded member-time95/6, missing0.
- `[53,57)`의 `fmilorigin_8ca77dddb2e47260ca10e7f1`: A♭ triad 철자 A♭–C–E♭, guarded member-time85/6, missing0.
- 저장 path235/341이 두 후보의 혼합 경로를 보존한다. 각각 lane0/slot0, lane1/slot1 교체 provenance이며 첫 cut `[None, V7/M]`, 다음 cut `[None]`과5registered key를 유지한다. 이는 source/target 형태가 맞는 **경쟁 요청**이다. actual links·전체 ordinary 해결·Secondary 기능·국소 조성·NCT를 새로 판정한 사례가 아니다.
- 원 `sound_cae7b39ad108`의 D♭5는 `note_2d60aad9c21b` onset45/duration4와 `note_b1e7cd2305c0` onset49/duration3/2, `tie_8f5b04834d7b`를 유지한다. Full span `[45,101/2)`와 scope 관측 시작49를 구별하며 실제 기보 attack45를49로 바꾸지 않는다.

저장기 측의 가벼운4JSON/hash/문서 검수0.009413초도 일치했다. 독립 본문 감사와는 별개다. 그 검수로 whole hold의 `selectors`에는 controls가 남는다는 표현과 compatible options390 대 전체shape45,400의 분모를 명확히 교정했다. 감사 전 및 최종 문서 추가 뒤 root QA는 새4파일 동결SHA·7text/4AST/140로컬링크·read-only diff check 오류0이며 기존 unrelated tracked5파일의 LF→CRLF 경고/수정은 보존했다.

모든 감사는 producer/propose/shape inference/native/역할 API 재실행과 파일 편집0이다. 원 source/XML/Core/주석·이전 code/output·악보 UI/구조/작곡편곡/Git/Gold·훈련은 미변경이며, 제안 생성과 이후 fresh native/role/정책 평가는 별도 실행으로 구별한다.

## 다음 큰 기능

새 제안을 **genuine fresh native session**의 source/supplier provenance와 exact 대조하여 재발급하고, 원 두 completion의 실제 required links를 다시 등록한 뒤 같은 completion에서 native 진행·역할·union·경쟁 비교·조건부 정책을 평가한다. 저장된 bundle ID나 예전 path ID를 새 session 권한으로 복제하지 않는다. 구간/철자·공급 provenance가 달라지면 근접 MIDI로 대신 매칭하지 않고 보류한다.

이번 source 요청으로 실제 양성과 반례가 늘어나는지는 그 후속 단계에서 판단한다. 이번 단계는 교재 신규 독해·정답률 개선·운영 UI/구조/작곡편곡/Gold·훈련 또는 Git 업로드 완료가 아니다.
