# 동일 계약의 후보 시간창 계산 공유

기록 ID: `HARM-DEV-20261002-23`

작성일: 2026-10-02

상태: 새 연구용 공급기 구현·공개 검사·실제 소규모 동등성/비용 시험 완료. 운영 미연결.

## 1. 목적과 순서

직전 [native interval lattice](2026-10-02-native-multi-slot-interval-lattice.md)는 실제 5문맥의 1,469 fresh 구간을 계산하는 데 약38분이 필요했다. 특히 Corelli의 한 문맥에 약24분이 걸렸다. 다음 큰 목표인 같은 완전 진행/성부 가정의 local·boundary NCT 설명 합집합을 연결하기 전에, 명확한 반복 계산 하나를 줄이고 결과가 바뀌지 않는지 먼저 검증한다.

화음 종류·분산형·비화성음 판정 규칙이나 후보 수를 줄이는 작업이 아니다. 특정 작품/마디/정답을 조건에 넣지 않는다. 기존 교재 규칙을 새로 모두 적용했다는 뜻도 아니다.

## 2. 발견한 반복과 공유 범위

기존 `harmony_candidate_catalog.propose`는 augmented와 extended 공급기를 각각 호출한다. 각각 target window와 fixed context window를 다시 계산한다. 좁은 N개 구간이라면 구조상 `4N`번 window 호출이다. Base와 context가 같으면 기존 공급기는 같은 window를 총2번 계산한다.

새 방식은 고정 context window를 한 번 계산하고, 각 raw target window를 한 번 계산해 두 공급기에 전달한다. 한 batch 내 중복 요청은 한 번만 계산하지만 요청 occurrence 순서와 반환 수는 유지한다. Batch 밖에 보존하는 것은 고정 context window 하나뿐이다. Base window 및 catalog 전체를 계속 쌓는 무제한 캐시는 만들지 않는다.

다음 항목은 여전히 target별로 계산한다.

- Exact spelling·후보 관문·ID·순서·missing/extra members.
- Cell별 sounding/attack/continued/bass refs와 유리수 note-time.
- Base의 conditional ornaments, augmented/extended의 target+context+hypothesis별 실제 해결 observer.
- 추가 7화음, 모든 provider의 normalized records 및 기존 validation.

전체 문맥 후보를 좁은 구간으로 잘라 쓰거나, 후보 가정이 다른 근거를 이전하지 않는다. Base/additional seventh는 **base blockers만**, augmented/extended는 **base+context blockers**를 사용하던 구분을 그대로 둔다. 구간 밖 grace/unsupported pitch를 base 후보까지 전파하지 않는다.

## 3. 새 코드와 API

| 파일 | 역할 |
|---|---|
| `src/musicanote_harness/harmony_candidate_windows_augmented.py` | 원 augmented 본문에서 window 계산만 분리한 명시적 adapter |
| `src/musicanote_harness/harmony_candidate_windows_extended.py` | 원 extended 본문에서 window 계산만 분리한 명시적 adapter |
| `src/musicanote_harness/harmony_candidate_windows_catalog.py` | 기존 ordered normalization/helper/validation을 그대로 이용 |
| `src/musicanote_harness/harmony_shared_candidate_supply.py` | Full IR 소유 snapshot, fixed context cache, 전체 batch 예산·출처·측정 |
| `src/musicanote_harness/harmony_shared_candidate_supply_trial.py` | 등록된 5문맥의 작은 구간 표본에서 untouched baseline과 비교 |
| `tests/test_harmony_shared_candidate_supply.py` | Genuine MusicXML→IR 동등성·소유권·예산 검사 |
| `tests/test_harmony_shared_candidate_supply_trial.py` | 저장·선택·기존 결과 보호 검사. 음악 정확도 검사가 아님 |

```python
session = prepare_supply(full_ir, context_span,
    max_ir_bytes=268435456, max_context_window_bytes=33554432)
result = supply_catalogs(session, exact_spans,
    max_requests=1024, max_window_calls=1024, max_output_bytes=67108864)
```

`result.catalogs`는 기존 공급기와 동일한 JSON payload 목록이다. 버전·계산 공유·시간·source binding 등은 **바깥 receipt**에만 있다. 기존 후보/ID/engine_version에 새로운 native 권한을 사칭하지 않는다. `session_binding`은 분리된 복사본을 반환한다.

Adapter는 기존 함수 전역을 monkeypatch하거나 function globals를 복제하지 않는다. 명시적 본문 복사이므로 향후 원 공급기 수정 시 동등성 검사와 adapter 동기화가 필요하다. 원 provider/helpers는 재사용한다. 연구용 내부 adapter에 임의 window를 직접 전달하는 것은 source 인증 경로가 아니다. 소유된 public 공급 경로를 사용해야 한다.

## 4. 입력·ID·불변성·freshness 계약

- 원 파일/과거 parent 재생 권한이 아니라 **현재 전달된 전체 IR content**를 소유한다. 문맥 projection으로 입력을 바꾸지 않는다. 기존 theory observer가 문맥 밖 ID/시간도 검사하므로 전체 IR이 필요하다.
- 입력은 string key·표준 JSON 값만 받는다. 시간 span은 closed `{start,end}`와 integer numerator/positive denominator, `[start,end)`이며 bool/float 시간을 받지 않는다.
- Span key는 숫자값만이 아니라 축약하지 않은 **raw rational JSON 표현**까지 포함한다. 원 candidate/window ID만으로 source 동일성을 판단하지 않는다.
- Frozen 소유 snapshot·실제 발급 session/state/cache identity와 HMAC를 확인한다. 복제 handle·다른 session cache·snapshot 변조·cache plain-digest 재봉합은 거부한다.
- 외부 catalog/receipt는 내부 cache와 alias를 공유하지 않는다. 원 입력을 이후 수정해도 기존 session의 소유 snapshot은 바뀌지 않는다. 새 입력을 보려면 새 session이 필요하다.
- Conservative relative-import source closure와 loaded function identity/semantic code/defaults/상수를 검사한다. Facade VERSION만 보는 계약이 아니다.
- 정상 실행 전후 producer와 소유 자료를 확인한다. 동시 runtime/file mutation은 허용하지 않는다. 일시적인 A→B→A 변화를 전부 감지한다는 보장은 하지 않는다. 같은 세션의 동시 요청도 거부한다.
- Runtime identity가 포함된 계약은 process-local freshness다. 다른 프로세스의 동일 숫자 identity나 장기 portable native 발급권을 주장하지 않는다.

전체 ordered canonical JSON을 비교한다. 배열 순서·pointer·candidate ID·provider body·rational wire·음가·false/null·JSON type이 모두 대상이다. Python `==`나 candidate 수/PC set만 같다고 동등성을 선언하지 않는다.

## 5. 예산과 상태

전체 raw 요청 목록과 distinct span을 먼저 계획한다. Request/window 예산을 초과하면 계산 결과 prefix를 반환하지 않는다. Cache hit도 복사·확인·반환 비용이 있고, 시간/메모리 비용을 0으로 보지 않는다.

| 상태 | catalogs | candidate counts |
|---|---|---|
| 정상 빈 후보 | 실제 catalog 있음 | `0` |
| 요청 0개 성공 | `[]` | `[]` |
| Request/window/retained context/output byte 예산 보류 | `null` | `null` |

Context/output byte 한도는 전체 window를 계산하거나 해당 catalog를 serialize한 뒤에야 실제 크기를 알 수 있다. 초과 시 반환을 전체 보류하고 실패 batch는 cache를 데우지 않는다. 시도한 계산 횟수는 receipt에 남긴다. 이 한도들은 총 RSS·wall-clock 상한이 아니다. IR snapshot은 직렬화 크기 상한이며 임의 source의 모든 parser 오류 순서까지 기존과 동일하다고 주장하지 않는다.

## 6. 검증 및 발견/교정

### 6.1 구현 과정

- 세 adapter의 AST 본문 대조는 window 계산 제거/provider 전달 변경을 제외하고3/3 일치했다. 첫 AST 감사 스크립트가 semicolon 두 Assign 중 하나만 변환한 오류는 감사 스크립트에서 교정했으며 제품 결함이 아니었다.
- 초기 genuine 실행에서 `marshal.dumps(code)`의 실행 후 직렬화 SHA 변화가 정상 실행을 producer 변경으로 오인했다. 의미적 `co_code`·재귀 constants/names/arguments/locals/freevars/line/exception attributes fingerprint로 바꿨다. 첫 오류 기록은 최종 통과 검사 수에 더하지 않는다.
- 독립 검토에서 mutable 소유 상태/cache 인증, nested output에 의한 과거 output 트리 변경, public timing에서 입구 인증 비용 누락, SHA merge가 과거 기대값을 덮어쓰는 위험을 발견해 각각 frozen/HMAC·경로/목록 검사·외부 계측·conflict-checked 등록으로 보완했다.

### 6.2 공개/회귀 검사

신규 핵심44개/49.441초(외부50.365초)는 독립 fresh process에서 PASS다. 원 시험 클래스를 상속하지 않고 genuine MusicXML→IR fixture를 사용했다. Full/narrow/네 provider/동음이명/tie/grace/microtone/rest·meter·repeat/raw rational/중복/빈 후보·빈 요청/strict cap/context byte 경계/원본과 반환값 mutation/foreign handle·state·cache·code 변조 및 실제 window 호출 수를 검증했다.

초기35개는11PASS·23 freshness errors·1 binding 기대값 failure/31.715초였다. Semantic fingerprint 교정 뒤44개 첫 실행은43PASS·1 fixture failure/48.983초였다. 후자는 기존 FormalIRAdapter가 repeat_barline을 아직 None으로 두는 문제다. **시험 fixture에서 원본 XML barline/repeat를 읽어 해당 관찰 필드를 복원했다고 명시**하고 단일1.102초 확인 뒤 최종44를 재실행했다. 운영 parser에서 repeats가 구현됐다고 주장하지 않는다. 실패/중간 실행을 최종 통과 개수에 더하지 않는다.

기존4suite72개/0.453초는 별도 실행에서 PASS다. 새 저장/선택 guard8개/0.034초도 PASS다. 이는 한 번의 전체 repository 검사나 음악 정확도 비율이 아니다. Root 최종 합동 재검사와 독립 saved audit는 아래 최종 QA에 별도로 기록한다.

### 6.3 실제 소규모 공급기 비교

원 phase22의 같은 등록 full IR 5개와 같은 expanded context span을 사용한다. 베토벤 현악4중주·피아노소나타1번, 쇼팽 마주르카, 코렐리, 모차르트 소나타다. Sonata는 기존 제한 교정 `candidate_ir.json`의 exact content binding을 유지한다.

각 문맥에서 전체+관측 endpoint grid의 세 부분+첫 부분 재요청, 즉5 occurrence/4 distinct span을 label-blind로 선택한다. 원본 whole IR은 유지하고 주석 라벨을 추론에 쓰지 않는다. Fresh untouched `legacy.propose`와 새 cold/warm 결과의 **전체 JSON**을 비교한다. 오래된 lattice에 저장된 catalog를 replay하거나 native builder/prepare/모든 logical path를 재실행하는 시험은 아니다.

Baseline 계산 시간과 baseline 최종 serialization 시간을 분리한다. Shared는 `prepare`+cold public call 전체와 warm public call 전체를 외부에서 측정하여 입구 HMAC·source 확인 비용을 포함한다. 이는 보수적인 작은 sequential probe이며 동일 실행 경로의 full native benchmark가 아니다. RSS/peak memory는 측정하지 않는다.

실제 단일 `r1`은 exit0, 전체42.751915초에 완료했다. **5선택 문맥/25요청 occurrence/20서로 다른 context+span/2,602후보 occurrence**의 cold/warm 전체 JSON은 untouched baseline과 일치했다. 중복 첫 구간을 제외한 distinct20 catalog의 후보 합계는2,116이다. 후보 수는 음악 정답·곡 수가 아니다.

| 문맥 | 전역 quarter 범위 | 원 공급기 계산(초) | 새 prepare+cold public(초) | 새 warm public(초) |
|---|---|---:|---:|---:|
| Beethoven quartet n01op18-1_04 | `[262,270)` | 2.129400 | 2.492205 | 1.731566 |
| Beethoven sonata 01-1 | `[49,61)` | 1.328522 | 2.166314 | 1.360015 |
| Chopin BI105-2op30-2 | `[10,22)` | 1.747539 | 2.137166 | 1.356652 |
| Corelli op01n01a | `[32,44)` | 6.768506 | 3.230620 | 2.444603 |
| Mozart K280-1 | `[18,27)` | 2.720773 | 2.660620 | 1.777985 |
| 합계 | 5문맥 | **14.694741** | **12.686926** | **8.670821** |

원 공급기의 최종 catalog 목록 serialization은 별도로0.326212초, 계산+serialization 합계15.020953초였다. Shared column은 HMAC/freshness/JSON snapshot·복사/정규화/validation/직렬화·반환을 포함한다. 단발 호출에서는 quartet/sonata/chopin이 더 느렸고, warm에서도 sonata가 원 계산보다 약간 느렸다. 공유가 모든 작은 요청에 이득인 것은 아니다. 시간의 큰 감소가 확인된 문맥은 Corelli다. 현재 이 수치로 이전38분 lattice의 새 소요 시간을 추정하지 않는다.

실측 새 window 호출은 cold20회, warm15회다. 기존90회는 기존 함수의 branch 구조상 횟수이며 계측값과 구별한다. Cache hit의 비용을 공짜라고 기록하지 않았다. 네 provider의 후보/음가/근거와 모든 false/null 정책은 그대로다. 해결 observer·catalog 계산/복사 비용은 여전히 남아 있다.

출력: `output/shared-candidate-supply-2026-10-02-r1/`. 정확8파일/1,012,788bytes(5context gzip+plan/index/report)이다. 등록된 full IR·scope·기존 phase22 출력/producer/test 및 새 code/test의 고유365경로 SHA를 전후 보호했고 변경0이다. 기존 phase22의 exact28파일 목록도 전후 동일했다. 이365는 과거4,539 전체 input cold replay를 대체하지 않는다. Report의7 artifact 등록과 report 자기 파일은 별도로 확인한다.

Root는 동일 신규44+storage8의 합동52개를 별도 fresh process에서 재검사하여50.827초/exit0 PASS를 확인했다. 앞44/8을 추가52로 중복 집계하지 않는다.

주요 output SHA256:

- Report: `0dd988642db23904a69f64d2f20b24dfd00d889d4479ec5abfd1e836ba2ca694`.
- Plan: `4e1984a33b44c1e32e3f2d1bed7b2eb537c8de8ca4a5afbe20114ede8773f909`.
- Index: `82c772f29fbe06122cc48b8a4a597275736bdfec36a997960bae00a501d6bc7b`.

Source/test 동결 SHA는 run-plan의 `protected_sha256`에 등록한다. Adapter3·공급기·실행기·신규test2 모두 실제 trial 전후 및 root 후속365경로 검사에서 동일하다. Root는 별도로 exact8output의등록7SHA+report와전체1,012,788bytes를확인했다. 최종10파일 stricttext/7AST/124로컬링크·read-only `git diff --check`는 QA에 포함한다. 기존5파일의 LF→CRLF 경고는 그대로이며 이번 source 변경이 아니다.

독립 saved audit도 **270,745 assertion/3.630563초 PASS**다. 이는 새 unit test 수나 음악정답 수가 아니라 저장 finite/산술/출처 확인 수다. 5문맥/25occurrence/20distinct/2,602후보, base263cell·candidate30,766cell, context별 sound union239/note union243의 source trace와 half-open attack/carry/equal-lowest·원span·typed origin/order·rational note-time을 대조했다. Provider occurrence는 base1,862/additional seventh46/extended686/augmented8이다. 분석 승격이나 종류별 정확도 수가 아니다.

5gzip body↔index↔plan, baseline 저장digest·cold body·cold/warm receipt SHA/bytes, canonical catalog 목록 합계30,311,752bytes와report의시간/수집계(1e-9허용)를확인했다. 새8output/과거phase22의exact28파일75,303,652bytes/보호365SHA·원code·등록5fullIR/5scope파일과contentbinding·seal·score/source identity는검사전후불변이다. Report자기SHA도동일했다.

감사는 baseline/공개 producer/native builder를 다시 실행하지 않았다. Warm 별도 payload 저장본은 없으므로 그 부분은 receipt fingerprint 일치 범위로 확인했다. Process-local runtime identity를 다른 프로세스의 발급 권한으로 재생하지 않았다. 실제 trial의 fresh cold/warm 동등성 검사와 독립 saved 확인을 구별한다.

## 7. 미변경·다음 단계

원 parser/Core/XML, 과거 provider/native lattice/source/tests/출력, UI·구조 분석·생성·Git은 변경하지 않는다. 새 공급기가 빠르더라도 기존 phase22 산출물의 producer 권한에 소급 주입하지 않는다. 원4,539 inputs에 새 보호 권한을 발급했다고 주장하지 않는다.

다음 큰 단위는 새 native path와 **같은 실제 completion**의 local/boundary 조건부 음표 역할 합집합이다. 기존의 준비·지속·첫 변화·해결·ordinary critical obligation을 재사용하고 raw 음가와 보류·대안은 보존한다. 이번 공유기를 소비하려면 별도 새 native producer 버전/계약을 만들고 baseline과 다시 비교해야 한다. NCT/cadence 양성 실제 작품군 검수 공백도 여전히 남는다.

전체 lattice 소비 단계에서는 원 음표·candidate·분모를 빠뜨리지 않는 bounded batch/streaming 계약이 필요하다. 이번 기본1024요청/64MiB 반환 한도를 실제 전체1,469 interval 처리 완료로 오인하지 않는다. 한도를 무작정 높이기보다 전체 planned inventory와 batch별 completed/held 상태를 유지하고, 중간 반환물을 유리한 후보 prefix나 완전한 native lattice로 승격하지 않는 방식으로 설계한다. 원음가·동일 가정·불확실성 검증이 비용 절감보다 우선이다.

빠른 후보 계산은 최종 화성/조성/NCT/종지 선택, 신뢰도 보정, Gold/학습 승인 또는 편곡 생성 완성을 뜻하지 않는다.
