# 진행 후보 대비의 저장·중단 계약과 읽기 예산

2026-10-03. 화성 분석 개발 기록. 선행 [비교 기반](2026-10-03-cross-batch-contrast-implementation.md)과
[전체 대비 설계](2026-10-03-cross-batch-progression-contrast-plan.md)를 이어간다.
이 문서는 인수인계 문서가 아니다.

## 목적과 현재 범위

비교를 계산하는 것과 결과를 완전하게 저장하는 것은 다른 작업이다.
부분 저장이나 중단을 전체 완료로 보고하면 이후 화성/NCT/구조/생성 판단의
근거가 잘못된다. 이번 단위에서는 submitted prepared group의 저장 계획,
exclusive write, block별 ledger와 완료/보류/중단의 분모 계약을 개발한다.

새 저장 모듈과 작은 검사·연결 검사의 구현 및 검수를 완료했다.
실제 corpus의 전체 body 의미 검증과 1,652,640pair 계산/저장·최종 선택·UI 적용은
이번 단위에서 수행하지 않는다. 저장 계층은 새로운 음악적 정답 규칙이 아니다.
원 음표/시간/철자/타이·역할 근거와 null을 비교 core 그대로 보존한다.

## 저장 단위와 authority 경계

새 저장 계층은 검증된 core `PreparedGroup`을 소비한다. JSON summary를 다시
봉인하거나 원 group 일부 entry만 전달하여 검증 완료 권한을 만들지 않는다.
Catalog/group/refinement/entry inventory와 원 selector 위치·completion request·
key/bundle의 정확한 연결을 유지한다. 같은 bundle의 별개 원 요청을 합치지 않는다.

Caller가 제공한 원 group/denominator 선언은 복사·고정하며 원 archive의
physical SHA·membership 검증 증명 그 자체는 아니다. Submitted group 저장 완료와
전체 archive 대비 완료를 분리한다. `full_contrast_evaluated`·원 archive 승인·
native authority·winner·음악 정답률·Gold/학습·generation/UI 승격은 주장하지 않는다.
실제 archive admission은 선행 loader와 이후 전체 실행기의 책임이다.

Core의 정확한 task geometry를 따른다. 0/1entry의 pair/task는0이다.
65entry의 마지막 singleton 대각은 pair가 없으므로 task로 세지 않는다.
선행 metadata의 단순 grid 삼각 수를 합성 fixture의 exact core coverage와 혼동하지
않으며 기존 동결 admission 코드를 이번에 수정하지 않는다.

## 한도와 상태의 일반 규칙

1. 전체 선언의 entry/group/block/pair 분모를 고정하고, catalog·block·run plan·
   종료 manifest의 encoded 용량을 비교 전에 예약한다. 보수적 상계가 cap을
   넘거나 필요한 비용이 미상이면 원 분모를 유지한 whole hold다.
2. Existing output을 덮어쓰지 않는다. 새 디렉터리와 파일은 exclusive 생성한다.
   입력/현재 계산 코드/기존 결과와 겹치는 경로에는 쓰지 않는다.
3. 한 번에 bounded block만 계산/저장한다. 동일 block의 중복·누락·재정렬·다른
   group/refinement·원 selector inventory 변경을 exact 검사한다.
4. 전체 attempt bytes를 파일 열기 전에 charge한다. Disk write가 일부만 되어도
   예약을 돌려주지 않으며 physical fragment의 bytes/SHA와 시도량을 기록한다.
5. Computed, persisted, held, not-yet-confirmed, computed-but-unpersisted를 구별한다.
   Missing body·disk 오류·budget hold를 known-zero나 음악적 실패로 바꾸지 않는다.
   Core가 결과를 반환하기 전 interrupt되면 이미 일부 산술을 했을 수 있다.
   `computed_pairs`는 검증된 완전 pair record 수이며, attempted arithmetic 수가 아니다.
   `unconfirmed_computation_pairs`·`calculation_attempted`를 함께 남긴다.
   따라서 `uncomputed_pairs`는 아직 **결과가 확인되지 않은** remainder로 해석한다.
6. 예상 밖 actual encoded 초과는 해당 block 전체 보류다. 유리한 prefix pair만
   저장하거나 그것을 block 전체 결과로 집계하지 않는다.
7. Final manifest까지 성공하고 제출한 원 group/task/pair ledger를 exact 대조해야
   submitted computation/storage 완료다. 중단 complement와 false promotion flags를
   항상 유지한다. 검수 무결성이 참이어도 음악적 정확도가 참인 것은 아니다.
8. Full archive read/decoded cap, core logical-work/catalog cap, physical/RSS, output
   encoded cap과 manifest reserve는 서로 다른 예산이다. 하나의 cap 통과를
   다른 cap의 통과로 사용하지 않는다.

부분 제출 수로 원 분모를 대체하지 않는다. 실제 기존 전체 예정은 두 등록 구간/
4원 completion/8,050entry/20group/1,652,640pair/570task이며 전곡 수가 아니다.
Original322문맥/1,013raw lanes·미실행320/1,006도 선행 문서처럼 유지한다.

## 실제 읽기 예산 점검 — 완료

독립 read-only 검수는 phase29 정확1,025파일과 등록1,024artifact의 physical SHA,
creation input/code union4,788SHA 및 ordered parents6/7/7/148목록을 대조했다.
변경·불일치0이다. Creation code347은 당시 parent343+replay4이며 현재 code glob을
역사 생성 목록으로 쓰지 않는다. 원본·body·JSON·코드·예산을 변경하지 않았다.

아래 decoded bytes는 trailer ISIZE 추정이 아니라 **1MiB buffer의 gzip streaming
실측**이며 읽기 전후 등록 physical SHA를 확인했다. Body JSON parsing, intrinsic
음악 의미 검증, pair 계산은0이다. 물리 크기나 누적 decoded bytes는 RSS가 아니다.

| Source / 원 completion | Entries / batches | Native decoded bytes | Role decoded bytes |
|---|---:|---:|---:|
| Sonata / no-link | 2,315 /145 | 511,191,414 | 124,312,531 |
| Sonata / greedy probe | 2,315 /145 | 511,214,918 | 266,863,998 |
| Quartet / no-link | 1,710 /107 | 434,147,240 | 74,147,212 |
| Quartet / greedy probe | 1,710 /107 | 434,109,330 | 212,524,814 |
| 합계 | 8,050 /504 | 1,890,662,902 | 677,848,555 |

Native+role는1,008파일/173,737,183compressed bytes/2,568,511,457decoded bytes다.
전체 phase29 physical archive는183,060,358bytes다. Metadata admission은34read/
438,689,440decoded bytes이며 unique33파일/438,683,098decoded bytes다.
Phase28 `report.json` 하나의6,342bytes만 반복 읽기다.
전체 admission+body 비용은**3,007,200,897bytes(약2.800674GiB)**다.
숫자·실측 범위·사전 pilot 위치는 [별도 관찰 receipt](../../../reports/cross-batch-read-budget-observations-2026-10-03-r1.json)에 보존한다.

기존 기본 cumulative decoded cap은1,073,741,824bytes(1GiB)다.
따라서 기본 cap으로 전체 요청을 읽고도 완료라고 선언할 수 없다.
초과량은1,933,459,073bytes다. Metadata 후 여유635,052,384bytes지만 첫 Sonata/
no-link completion의 body만635,503,945bytes가 필요하다. 원 read 순서의 마지막
batch144/role/selectors `[2304,2315)`에서879,604bytes를 더하면누적1,074,193,385bytes로
451,561bytes 초과한다. 이는 실측 byte를 이용한 **예측 보류**이지 실제 join 실행이 아니다.
단일 파일 최대는native5,083,361/role2,388,367/metadata103,401,361decoded bytes로
256MiB file cap 이하이므로 이번 차단은 per-file 문제가 아니라 cumulative cap이다.
Cap을 몰래 높이거나 반복 loader로 누적 charge를 초기화하지 않는다.
현재 작은 library 검사와 read-only 비용 조사부터 하고, 실제 큰 group pilot에서
읽기/메모리/출력 예산을 각각 명시한 뒤 전체 실행 여부를 정한다.

### 별개 catalog 예산과 중복 문제

현 core는 각 group에 전체 source lattice를 포함하고 catalog preflight 상계를
`input_json_bytes * 8`부터 계산한다. Creation-bound canonical lattice는Sonata
103,401,361bytes/Quartet81,201,706bytes다. **Lattice만의 상계 하한**도 각각
827,210,888/649,613,648bytes로 default `max_catalog_bytes=268,435,456`를 넘는다.
따라서 현재 default로 실제20group은 모두 whole hold가 되어야 한다.
이는 코드에서 도출한 하한이지 실제 group/core preflight를 실행한 결과가 아니다.

Source당10group catalog에 lattice를 복제하면serialized lattice만1,846,030,670bytes다.
Source당 한 번 공유하면184,603,067bytes다. 이는 RAM 절약 실측이 아니며 Python
container·deep copy·facet·freezing·temporary serialization의 peak RSS는 아직 미상이다.
새 source-shared codec/API를 검증해야 하며 이번에 동결 core의 cap을 높이지 않는다.

Storage 기본 block cap64MiB를570task 각각에 상계로 예약하면 block 부분만
38,252,052,480bytes(35.625GiB)다. 이는 **보수적인 최대 예약**이지 실제 output
실측이나 저장 필요량 확정치가 아니다. Catalog와 manifest도 별도 예약해야 한다.
이 상계가 cap을 넘으면 먼저 whole hold하며, 이후 실제 pilot로 더 타이트한
declared bound를 정하거나 codec/source evidence 공유를 개선한다.
더 작은 declared cap도 actual overflow 시 whole block을 보류해야 한다.

20catalog의 각256MiB 한도까지 더한 느슨한 envelope는43,620,761,600bytes다.
이것도 manifest 전의 최대 예약이지 실제 필요량이 아니다. 관찰 시 K: 여유는
25,357,078,528bytes였으며 시간에 따라 바뀐다. 실제 pair codec 용량/manifest/
부분 저장 fragment와 peak RSS·시간은 미상으로 남긴다.

### 결과와 무관하게 고정할 pilot

- 원4completion 각각의 첫batch0/selectors `[0,16)`.
- Sonata의 native+role body 크기 최대 proxy: batch120/`[1920,1936)`.
  No-link5,635,163bytes, greedy6,585,268bytes다.
- Quartet의 최대 proxy: batch2/`[32,48)`. No-link6,175,630bytes,
  greedy7,471,184bytes다. 후자의 compressed 쌍은482,941bytes다.
- 다음 contrast pilot의 deterministic first group/block는원source0/completion0/
  첫registered key에서 diagonal `[0,64)×[0,64)` 2,016pair와 off-diagonal
  `[0,64)×[64,128)` 4,096pair다. 이는 최대 refinement/reference/encoded cost라는
  증거가 아니다. 진짜 최대 비용은 validated entry-level cost plan 이후 선정한다.

이 byte-read proxy를 음악 결과가 좋은 표본으로 고른 것이 아니며, body/contrast
pilot 실행 완료라고 보고하지 않는다.

## 구현·발견·검사 이력

### 구현/API와 완료 범위

- [저장 모듈](../../../src/musicanote_harness/cross_batch_progression_storage.py)
  `GroupInput`은 source identity·scope/lattice·원 completion request·key/bundle·
  ordered original selectors·원 entry/pair/task/block size를 선언하고, 발급된
  `PreparedGroup` 또는 명시 whole-group hold만 허용한다.
- `plan_saved_run()`은 전체 제출 분모를 고정한다. Count gate를 catalog export/
  quadratic task materialization 전에 검사하고, exact core의 nonempty task를
  생성한다. Full catalog encoded bound와 각 task declared stored-byte cap 및
  run plan/final manifest의 전체 예약이 끝나야 저장을 시작할 수 있다.
- `StorageLimits` 기본은 total output2GiB/run plan2MiB/final manifest16MiB/
  block64MiB/groups128/tasks8,192다. 자동 확장하지 않는다. Caller의 per-task cap은
  낮추기만 가능하며0처럼 명백히 불가능한 positive task는 계산 전 whole hold다.
  Final manifest는 임의 cap만 예약하는 것이 아니라 bounded destination/path·
  metadata·task ledger·attempt/error rows에서 보수적 상계를 도출한다.
- `begin_storage()`는 기존 directory를 거부하고 새 directory 및 `run-plan.json`을
  exclusive 생성한다. `write_block()`은 exact next task만 내부 core로 계산한다.
  `write_prepared_group()`은 해당 원 group의 모든 task를 이어서 저장한다.
- `ledger()`와 `finish()`는 원 분모·완료/보류/중단 complements와 물리 attempt를
  복사해 반환한다. Manifest 실패·output SHA/목록 변경·source 변경 시 complete는
  거짓이다. 완료 후 `ledger()`/`finish()`를 다시 호출할 때도 guard를 확인한다.
- Fixed current code SHA guard는 **storage/core 두 파일**이며 전체 dependency
  closure가 아니다. 추가 source/code SHA는 optional caller map을 전달했을 때만
  검증한다. 이 scope를 archive physical admission으로 확대하지 않는다.
  이 library만으로 historical archive roots의 exact inventory를 승인하는 것이
  아니며, 다음 실제 runner가 그 root 안의 새 output 배치를 거부하고 원목록을
  전후 검증해야 한다. New directory라는 사실만으로 그 의무를 대체하지 않는다.

On-disk `report.json`은 자기 자신의 성공 write를 인증할 수 없으므로
`terminal_persisted=false`/`submitted_group_set_complete=false`의 pre-terminal
coverage를 저장한다. 최종 manifest의 physical bytes/SHA 검증 후 **owned finish
return**만 submitted completion을 보고한다. 이 JSON을 다시 seal한다고 계산
권한이 되지 않는다. 저장 JSON의 exact round-trip 검사는 재사용 가능한 authenticated
reload나 재시작 resume 구현 완료와 다르다.

**이번에 없는 기능:** 전체 original archive membership을 storage에 위임하는
runner/CLI, source-shared large-catalog codec, authenticated catalog reload,
restart/resume, 실제20group 전체 계산, policy/winner/cadence 채택, 악보 UI·구조·
생성·학습/Gold다. Library는 호출자가 제출한 group set까지만 완료를 말한다.

### 검수 중 발견과 교정

1. 첫 구현에는 final manifest cap만 예약되어 작은 reserve로도 body를 계산할 수
   있었다. Derived final-ledger bound와 destination UTF-8 cap을 **비교/쓰기 전**
   검사하도록 교정했다. Known positive task의0 cap도 prefix 계산 없이 보류한다.
2. 저장된 catalog/block가 변조되거나 외부 파일이 추가돼도 이전 persisted 숫자로
   완료를 보고할 위험을 발견했다. 각 output의 실제 bytes/SHA와 정확한 directory
   inventory를 비교 전/후·terminal·종료 후 재호출에 확인한다.
3. Partial run-plan/catalog/block/final write와 catalog gzip 실패의 경로를 보완했다.
   시도 bytes는 미리 charge하고 fragment가 읽히지 않으면 physical bytes/SHA를
   `null`과 diagnostic으로 남긴다. 실패와 known-zero를 혼동하지 않는다.
4. Core 반환 전 interrupt는 확인된 pair0과 실제 산술 미실행을 구별하도록
   attempted/confirmed/unconfirmed 상태를 추가했다. Boolean alias가 integer
   task/pair 좌표와 같다고 통과하지 않도록 exact type guard도 보완했다.
5. Root 연결 검사의 request/bundle ref는 string이 아니라 dict다. 초기 작성의
   set hash 가정을 deterministic JSON identity로 교정했다. 제품/악보 오류가 아니다.
6. Resource receipt의322문맥/1,013raw lanes를 registered로 잘못 이름 붙인 것을
   **declared**로 교정했다. Actual registered pool5·selected2/7을 따로 기록했다.
   Receipt run-plan SHA의 초기 전사1문자 누락도 실제3manifest SHA 대조 전에 교정했다.
7. 같은 issued group을 caller source identity만 바꿔 두 번 제출하는 선언을
   duplicate로 거부한다. Source identity는 보존할 metadata이지 새로운 pair
   분모를 발급하는 권한이 아니다. 서로 다른 원 completion request는 분리하며,
   empty core가 key를 `null`로 표현해도 원 empty key group의 선언은 보존한다.

[저장 검사](../../../tests/test_cross_batch_progression_storage.py)는 genuine 작은
XML/native/role의 two-entry·null/known-zero와 명시 mock admission의64/65entry
geometry를 구별한다. 65개의 genuine 음악 가설을 검증한 것으로 가장하지 않는다.
[Root 연결 검사](../../../tests/test_cross_batch_progression_storage_integration.py)는
genuine XML에서 만든 저장 body를 saved iterator→core→storage로 연결하고 원2요청/
같은bundle별 분모·selector·모든 pair의 기존 설명 exact reconstruction을 확인한다.
Ancestor archive admission은 mock이며 실제 corpus physical admission 검사가 아니다.

### 최종 검사와 동결

| 검사 | 고유 수 | 최종 root 실행 | 결과/범위 |
|---|---:|---:|---|
| 새 storage suite | 26 | 46.854초 | PASS, 작은 genuine/XML + 명시 mock geometry/IO |
| 새 saved-body 연결 suite | 2 | 27.559초 | PASS, 작은 genuine body + mock ancestor admission |
| 기존 cross-batch core 회귀 | 25 | 44.652초 | PASS, 기존 코드는 동결 |
| 기존 saved admission 회귀 | 16 | 41.722초 | PASS, 기존 코드는 동결 |

신규 고유28개·기존 회귀41개다. Root는 storage의 duplicate-edge 교정 후26+2를
최종 재실행했다. 작성자의 초기24개42.392초, 중간26개46.458초와 root의 이전
26개43.592초/연결2개28.325초는 이력이며 최종 고유 수에 더하지 않는다.
독립 pure3개0.016초도26개 suite의 재검사 subset이다. 독립 전체 코드 검수와
최종 duplicate 차분 검수는 추가 차단0이다. 이 수와 앞선 물리4,788SHA/1,024artifact
검사를 합산해 음악 정답률이나 새 작품 수로 보고하지 않는다.

최종 고정 SHA256은 다음과 같다. 문서 자신의 hash를 자기 본문에 넣지는 않는다.

| 파일 | SHA256 |
|---|---|
| `src/musicanote_harness/cross_batch_progression_storage.py` | `9382ed9f7dfe56621a943ab552f571188c825b41ce931cb5db4d6dd1d86afabd` |
| `tests/test_cross_batch_progression_storage.py` | `d9b89bc310b390bdaf4e5bbd190642054f94a70320e3acf3ace6abc47a6fc040` |
| `tests/test_cross_batch_progression_storage_integration.py` | `7b2f728797e03eb14a33ceee4a1f5cf1630e94cb0aa86dcf37423e23578e95ae` |
| `reports/cross-batch-read-budget-observations-2026-10-03-r1.json` | `082ee1bc64d4b7f7fb3821fe4ca9611cff1b5b0f756deadd57315f86d8989dee` |

Root는 source replay/core/runner/tests4·앞단 admission/core/tests4·관찰
probe/wrapper/receipt3의 기존 고정11SHA를 확인했고 변경0이다.
최종 QA는 새3AST·코드/MD/receipt7파일 strict UTF-8 및 NUL/대체문자 검사·
154local Markdown 링크·신규4고정SHA·기존11고정SHA·receipt 산술/원3manifest
physical SHA를 확인해 오류0이다. `git diff --check`도exit0이며 별개 tracked5
파일의 기존 LF→CRLF 경고만 유지했다. Commit/push나 권한/앱 설정 변경은 없다.
원본/기존 parser/Core/producer/과거 결과와 별개 tracked5변경은 보존했다.

### 아직 측정하지 않은 실행 비용

현재 library는 각 block 호출에서 앞선 task를 scan하고 전체 ledger를 복사하며,
기존 output을 재해시한다. Bounded task 수가 있어도 큰 run의 metadata/I/O 비용은
누적될 수 있다. 이를 source-shared codec과 함께 후속 실제 pilot에서 측정/개선한다.
이번 작은 검사의 시간이나 full replay의 과거 실측을 full contrast 속도/RSS
보장으로 쓰지 않는다. 대형 계산을 이 library에 곧바로 연결하지 않은 이유다.

## 다음 단계

1. 새 저장 계층의 최종 검사·독립 검수와 동결은 완료했다. 전체 runner 완료와는 다르다.
2. 전체 cumulative decoded accounting과 source-shared catalog 계약을 먼저 만든다.
   원 archive→전체 original membership bridge 및 authenticated reload를 별도
   versioned adapter로 연결한다. 기존 source/core snapshot과 기본 cap은 보존한다.
3. 첫/max-cost group과 block을 결과와 무관하게 선정해 실제 facet·RSS·시간·
   JSON/gzip 크기를 측정한다. 완전 original group과 일부 표본을 구분한다.
4. 명시 전체 예산이 충족될 때만 전체20group/570task/1,652,640pair를 실행한다.
   최종 proposal/hold 정책·음악적 검수·악보 표시·생성 연결은 그 이후 단계다.

영구적인 음악적 목표와 단계는 [메인 개발 문서](../README.md)와
[작곡·편곡 로드맵](../MUSICAL_SEMANTICS_AND_GENERATION_ROADMAP.md)을 따른다.
