# 단계37 — Proof-v2 streaming 저장과 완전한 원 요청 연결

이 문서는 **화성 분석 개발 기록**이다. 원자료·Canonical Core·기존 분석기·과거 결과를 수정하거나 인수인계 문서로 대체하지 않는다. [메인 개발 문서](../README.md)와 [변경 로그](../DEVELOPMENT_LOG.md)에서 현재 상태를 관리한다.

## 목적과 이번 범위

[단계36](2026-10-03-owned-proof-sharing-and-transient-lifetime.md)은 실제 같은 원 요청의1,710후보·107batch·5group을 기본 group 한도 안에서 준비했다. 실제 비교는0이고, catalog 길이는 owned memory 교환 표현의 측정치였으며 저장 완료가 아니었다.

이번 단위는 그 새 표현을 **원자료 한 번 저장 + group별 catalog + 전체 block 비교·저장**으로 연결하는 library와 소형 통제 검사다. 동결 old writer의 imports/registry를 갈아 끼우지 않고 별도 버전을 추가한다. 한 개의 group 또는 일부 batch가 성공한 것을 원 요청/전체 archive 성공으로 바꾸지 않는다.

실제1,710후보/291,555pair/105block의 새 전체 저장·비교 실행은 이번 기록과 구별한다. 이번에는 그 실제 corpus의 새 output 크기·시간·RSS·cap 통과를 아직 주장하지 않는다. 주석 정답과의 화성 정확도, 실제 악보 화면, 최종 진행/NCT/key/cadence 선택, 구조 분석·작곡편곡·학습/Gold 적용도 별도다.

## 문제와 설계 결정

동결 선행 writer는105tasks 각각64MiB를 예약하여 block만7,046,430,720B가 필요하다고 계산했다. 기본 전체 output2GiB보다 크다. 실제 길이가 작을 것이라는 추정, 일부 압축률의 외삽, cap 증가, 후보/블록 prefix 생략으로 이를 통과시키지 않는다.

새 writer는 exact owned group/task의 **compact 출력 schema에서 보수적인 byte 상계**를 계산하고, 원자료·모든 catalog·모든 task·run plan·최종 manifest를 전체로 예약한다. 상계가 여전히 너무 크면 그대로 전체 보류다. 상계의 구현 성공과 실제 corpus의 fit은 다르다.

추가한 세 역할은 다음과 같다.

| 파일 | 역할 |
|---|---|
| [streaming helper](../../../src/musicanote_harness/proof_shared_progression_streaming.py) | frozen source와 local DAG를 전체 thaw/export 없이 canonical UTF-8 JSON으로 stream; schema-derived block 상계 |
| [v2 storage writer](../../../src/musicanote_harness/proof_shared_progression_storage.py) | 동일 owned source 한 번 저장, 제출된 모든 group의 사전 예약·whole block 저장·중단/종료 진실 |
| [whole-request coordinator](../../../src/musicanote_harness/proof_shared_request_coordinator.py) | issued scoped reader를 직접 끝까지 소비하고 원 선언 전부와 연결; 동일 owned storage plan의 결과만 원 요청 범위로 확인 |

외부 JSON descriptor/이전 pilot report/사용자가 제공한 selector 목록만으로 capability를 복원하지 않는다. Private registry에는 다른 모듈의 핸들을 삽입하지 않는다. 정확한 issued state의 읽기 전용 확인과 새 모듈 자체의 factory 발급을 구별한다.

## Canonical streaming 계약

`source_stream_info`/`catalog_stream_info`는 byte/work/ref descriptor이고 권한이 아니다. `iter_source_json`/`iter_catalog_json`는 exact owned source/group을 다시 확인한다. Frozen `MappingProxyType`/tuple을 직접 순회하고 local payload는 이미 검증된 cached DAG bytes를 조각으로 읽는다. `export_source`, 전체 `export_catalog`, raw entry/facet materialization, DAG `record()`/decode를 저장 내부에서 호출하지 않는다.

기본 **emitted output chunk**는1MiB이며 작은 chunk를 명시할 수도 있다. 모든 transient 객체/정수 문자열의 크기가1MiB 이하라는 보증은 아니다. 문자열은 작은 문자 조각에서 JSON escaping과 UTF-8 인코딩을 하므로 큰 문자열 전체를 먼저 bytes로 복제하지 않는다. 따옴표·역슬래시·제어 문자·비ASCII와 정렬된 key를 보존한다. Float, 타입 subclass, 잘못된 UTF-8, bool을 integer로 쓰는 경우를 거부한다.

SHA는 전체 canonical JSON bytes의 실제 SHA256이다. 구조/Merkle SHA를 대신 사용하지 않는다. Stream descriptor를 만들기 위한 측정과 iterator의 재측정·직렬화 비용을 따로 예약하고, 실제 출력 SHA pass 및 파일 guard I/O를 무료로 취급하지 않는다. Source는 source cap, block은 block cap을 적용하며64MiB block cap을 source cap으로 잘못 적용하지 않는다.

Module-level worker와 `finally` 정리로 generator 중단·malformed task·보유된 traceback 때문에 새 임시 bank나 group이 GC 전까지 붙잡히는 것을 통제한다. 호출자가 이미 소유한 archive/source 자료의 수명과 저장 helper가 새로 만든 임시 복사의 수명은 다르다.

## Compact block 상계의 근거

`task_stream_bound(prepared, task)`는 exact task/source/group/catalog/refinement/selector inventory binding을 확인한다. 비교 결과를 시험 계산하거나 atom run/transfer를 계산하여 크기를 추정하지 않는다. Inspection은 endpoint·해당 entry summary·pair 개수에 비례하며 **pair×atom 계산을 사전 계획으로 숨기지 않는다**.

상계에 포함하는 항목은 다음과 같다.

- 모든 fixed key/literal, source/catalog/group refs, original selector와 entry index, record ID/SHA seal, block header·status·hold reasons·flags와 array comma/bracket.
- Shared cut의 원 assumption subtree 양쪽 전체 byte 길이. 근거 객체를 작은 라벨 하나로 줄이지 않는다.
- Left/right-only rational cuts, account delta·conditional credit의 음수/자리 올림·서로 다른 분모 곱 상계.
- 모든 가능한 category-transfer item, changed source segment와 aligned bass cell pointer의 최대 개수·각 index 자리수.
- 실제 sound endpoint 분모들의 decimal digit 합으로 얻은 product 상계와 atom 수에 따른 numerator 합 상계. 거대한 product를 생성하거나 유리수의 부동소수점 근사를 사용하지 않는다.
- 전체 task의 모든 `i<j` pair. 가장 큰 한 pair만 곱하는 단순 표본 추정보다 각 entry summary의 크기를 반영하되 아직 결과를 계산하지 않는다.

검사 budget은 이런 loop 전에 고정한다. Work 부족으로 전체 상계를 못 얻으면 `raw_block_byte_upper_bound=null`이며0이나 측정된 partial 합을 전체 상계로 보고하지 않는다. Known byte 상계가 pair/block 한도를 넘는 경우에도 whole task/group 보류를 원 pair/task 분모와 함께 남긴다.

이 상계는 `core.compare_block`의 **compact 출력**을 대상으로 한다. 원 legacy pair를 완전히 materialize한 JSON의 길이 상계가 아니다. Schema 변경 시 estimator와 regression fixture를 함께 versioning해야 한다.

## Source-once storage 계약

`GroupInput(original, source, prepared)`에는 closed original declaration과 exact owned v2 group/source가 들어간다. Source handle↔original source identity는 양방향으로 일치해야 하고 같은 source reference를 서로 다른 handle로 가장하지 못한다. Group의 request/key/bundle/selector/block size가 원 선언과 달라지면 발급하지 않는다. Held group을 빼고 admitted prefix만 제출해 원 요청을 완료 처리하지 않는다.

`plan_saved_run`은 원 denominator를 보존하지만, 자체 authority는 **caller-declared submitted group set**이다. 실제 원 archive의 모든 group이라는 증명은 coordinator에만 있다. Immutable plan은 handle tuple·작은 descriptor·run plan bytes를 유지하며 source/local catalog의 큰 raw bytes를 별도로 복제해 보관하지 않는다.

Default cap은 기존과 같다: 전체 output2GiB, run plan2MiB, manifest16MiB, block64MiB, source/local catalog256MiB. Groups128/tasks8192/sources16/protected files20000/inventory roots16의 count gate도 적용한다. v0.1은 uncompressed JSON만 지원하며 `compressed=True`를 명시 거부한다. 나중에 압축을 추가할 때도 raw schema 상계와 encoded 상계를 분리해야 한다.

모든 source·catalog·task 상계와 전체 예약이 통과한 뒤에만 `begin_storage`가 독립 새 output directory를 만든다. Source는 동일 owned handle별 한 번 저장한다. 원 archive 또는 protected inventory 안에 output을 생성하지 않는다. 계획 뒤 iterator를 통해 source/local bytes를 쓰고 실제 길이/SHA를 검증한다. Whole block 계산 후에는 예상 pairs/status/task/ref/seal을 대조하고 한 block 전체를 저장하거나 전체 보류한다. 부분 pair prefix 파일을 정본으로 내놓지 않는다.

명시 task cap이 알려진 schema 상계보다 작으면 계산 전에 whole-plan hold다. 예상 밖 runtime 크기 초과나 I/O 실패는 이미 계산된 수를 숨기지 않고 computed-but-unpersisted로 남긴다. Keyboard interruption 등으로 전체 계산 수를 확인할 수 없으면 unknown/unconfirmed로 남기고0으로 단정하지 않는다. 실패한 physical write attempt의 비용을 환불하거나 없는 일로 만들지 않는다.

제출된 모든 groups의 persisted pair/catalog/source와 종료 guard·정확 output inventory가 만족되어야 `submitted_group_set_complete=true`다. Run 도중 수치는 provisional이다. Manifest는 자기 자신의 write 성공을 스스로 증명할 수 없으므로 persisted terminal artifact와 returned owned terminal 결과를 구별한다. 재조회에서 output 변경을 발견하면 과거 성공 표시를 무조건 신뢰하지 않는다. Saved JSON의 authenticated reload/resume는 이번에 구현하지 않는다.

## 완전한 원 요청 coordinator

`prepare_selected_request(issued ScopedArchive)`는 새 scope만 받는다. 이전 metadata JSON, 이미 일부 소비한 iterator, finished/failed scope, old group이 이미 발급된 scope를 받지 않는다. Fresh scope의 처리 책임을 받은 뒤 생기는 count/work/source/group/read 실패는 reader를 종료하고 실제 read ledger를 진단에 보존한다. Invalid foreign handle을 대신 닫거나 되살리지 않는다.

전체/선택/생략의6개 원 분모를 exact integer로 확인하고 합이 맞아야 한다. 선택은 정확 한 completion이다. 모든 ordered group declaration의 selector가 원 `0..N-1`을 중복·누락 없이 partition해야 하며 request ref·pair/block 예정 수가 일치해야 한다. 각 body packet의 batch ordinal·selector start/end·entry 순서를 직접 확인한다. **마지막 yield를 받았다는 사실이 아니라 iterator exhaustion과 upstream terminal join**을 요구한다.

Source는 한 번 준비하고 모든 원 group을 같은 handle로 preflight한다. Original read terminal/SHA/inventory closure까지 완료한 뒤 모든 group이 complete/reasons empty일 때만 새 v2 group 전부를 발급한다. 하나라도 hold이면 coordinator는 whole request hold/prepared0이며 유리한 subset을 계속 저장하지 않는다. Explicit group limits는 issued scope의 정책을 강화할 수만 있고 높일 수 없다.

Original expected SHA/inventory roots/archive directory는 issued reader에서 얻는다. Caller의 빈 root 목록으로 이것들을 제거할 수 없으며, 동일 directory의 다른 membership이나 다른 expected SHA도 거부한다. 추가 보호 조건만 허용한다.

`RequestPreparation`은 source·모든 groups·정확 storage plan에 묶인 새 opaque immutable capability다. `record()`는 복사된 진단/설명이다. Final snapshot은 한 번만 canonical encode하고, 그 encoding cost는 signed state의 별도 integer로 보존한다. Self-referential work field를 맞추느라 같은 큰 report를 두 번 encode하지 않는다. Early hold도 이미 만들어진 진단을 넘길 뿐 budget 이후 숨겨진 JSON clone을 만들지 않는다.

`request_ledger(preparation, run)`는 정확 같은 owned storage plan에서 시작한 run만 받는다. Submitted coverage와 original selected counts를 대조하여 `selected_request_storage_complete`를 계산한다. 다른 같은 내용의 plan, JSON summary, 일부 group의 완료는 이를 복원하지 않는다. 원 전체4completion의 완료는 언제나 별도이며 `full_archive_complete=false`다. 동결 scoped reader가 실제 발급하지 않은 old group flag/prepared count는 false/0 그대로 둔다.

## 비용 계정의 구별

단계36의 group work8.65~8.90억은 core 검증/표현과 예약된 비교 비용의 모델이었다. 새 저장 단계에는 **추가** source/catalog stream 측정·encoding/SHA와 per-group schema-bound planning 비용이 있다. 새로운 per-group planning/source planning budget 기본1B와 `max_plan_finalization_work` 기본1B는 별도 단계 budget이다. 이들을 더한 총비용이 이전 core1B 안에 든다고 주장하지 않는다. 최종 manifest의 canonical 측정/encoding/hash 비용도 별도 저장 계정에서 사전 확인하며 무료로 숨기지 않는다.

Coordinator 기본1B의 scope는 작은 metadata guard·plain-JSON 검사/canonical encoding·count/selector indexing과 capability bookkeeping이다. Original body decode/read/SHA guard, core/source preparation, storage planning/streaming, physical I/O, 사용자에게 `record()`를 내보내는 copy/진단 소비 비용은 각각의 계약과 계정으로 구별한다. Logical work units를 CPU 시간/RSS/음악 정확도로 해석하지 않는다.

원 decoded read cap1GiB와 storage output cap2GiB는 서로 다르다. Source-once 저장은 동일 source의 저장 중복을 줄이는 것이지 역사 body의 decoded read를 없애는 것이 아니다. 실제 실행에서는 기존 원/선택/생략 수와 bootstrap/execution 누적 decoded·physical guard 비용을 계속 따로 기록해야 한다.

## 개발 중 검수와 교정

- 초안의 catalog descriptor field `source_ref`/`source_catalog_ref` 혼동을 독립 감사로 찾아 교정했다.
- Work hold의 nullable bound를 무조건 더하거나 `min()`하여 TypeError를 내던 경로를 whole-plan reasons/unknown 보존으로 교정했다.
- 낮은 task cap을 통과시킨 뒤 runtime overflow를 기대하던 정책은 알려진 schema bound를 이용한 **계산 전 전체 보류**로 강화했다.
- Metadata encoding을 실제로 한 뒤 work 한도를 보는 초안은 모든 logical pass의 사전 gate로 교정했다.
- Final work 자기참조 때문에 report를 두 번 encode하던 초안을 signed state의 별도 charge integer로 교정했다.
- Count/work/protection 실패가 body 소비 전 발생했을 때도 원 reader terminal/read costs가 남도록 변경했다.
- Caller의 빈 roots/높은 group limit로 original 정책을 약화시키는 경로를 닫았다.

특정 작품의 음악 규칙·마디 정답을 추가한 교정이 아니다. XML/Canonical Core/주석/기존43개 동결 파일과 별개 tracked5 변경은 보존 대상이다. Git commit/push·권한·설정·서버·브라우저·UI 변경은 하지 않는다.

## 검사와 완료 상태

초기 root16개 연결 검사98.937초/exit0는 통과했다. 그 실행 중 coordinator의 diagnostic/limit 통제 보완과 writer의 독립 검수가 진행되어 **최종 revision의 완료 검사로 대신 사용하지 않는다**. 최종 source/test SHA·고유 검사 수·회귀·독립 감사 결과는 아래에 확정한다. 작성자/독립 재검사나 AST/문서 QA는 고유 unit-test 수에 더하지 않는다.

소형 fixture는 genuine XML의 saved replay body와 owned source/group/physical 저장을 사용한다. 역사 ancestry metadata 단계는 **명시 mock**이다. 따라서 real40-file ancestry 성공/실제 corpus fit/화성 정확도의 실증이 아니다. Coordinator의 packet-shape pure controls는 별도 명시 mocked iterator이고 authority를 발급하지 않는다. Temporary test output은 fixture 수명 안의 검사용이며 사용자용 실제 악보 사례를 추가한 것이 아니다.

최종 고유 suite는64개(streaming16 + storage28 + coordinator20)이며 **63 PASS +1 SKIP**다. Windows symlink 생성 권한이 없는 이 환경에서는 storage의 동일 bytes symlink 대체 검사가1개 skip이다. 이것을 통과 검사로 세지 않고 OS 권한이 허용된 환경의 재검사 대상으로 남긴다. 별도 기존52개 회귀도 PASS다. 실제 corpus 실행이나 화성 정확도 검사가 아닌 library·소형 physical 연결의 최종 완료다.

| 최종 고정 모듈 | 검사 결과 |
|---|---|
| Streaming16 | 작성28.895초/독립27.322초,16 PASS |
| Storage28 | 작성61.347초/독립65.103초,27 PASS +1 symlink권한 SKIP |
| Coordinator20 | Root109.814초/독립108.021초,20 PASS |
| 기존 read-budget24 + native contrast28 |52 PASS/18.622초,exit0; 기존 파일 수정 없음 |

초기 writer26개/27.322초의4개 error는 duplicate hypothesis를 불법으로 만들어 놓은 fixture 오류였다. Genuine three-slot selector fixture로 바꿔 검사를 다시 했다. Reorder 이전 작성28개/56.690초는27PASS+1SKIP였다. 독립 중간28개/59.082초의26PASS+1FAIL+1SKIP는 검사 도중 writer source SHA가 바뀌어 guard가 정상 중단한 것이며, `_outputs`를 금지한 mock 안에서 예상하지 않은 emergency finish를 호출했다. 그 실행을 최종 revision 검수로 세지 않는다. 마지막 terminal manifest의 비용/attempt 예약을 report-copy 전에 두고 위 최종 SHA에서 다시 검사했다.

Root 중간 통합64개/200.258초는63PASS+1SKIP였으나 시작이 writer 마지막 reorder와 겹쳤다. 따라서 최종20개 coordinator를 fresh process에서 재검사하고, 독립 최종 streaming16/storage28 결과와 함께 최종 coverage를 확정했다. 독립 최종 세 suite의 실행 전후6파일 SHA는 아래 정본과 같고 추가 architecture/API 차단0이다. 반복/중간 실행 수를 더하여 신규 검사 수를 늘리지 않는다.

## 소형 physical 저장 관찰 — 실제 corpus와 구별

작성자의 **한 fresh tiny same fixture**는2selectors `[3,4]`/block size1/1task였다. Source canonical1,060,861B/보수적 예약1,076,004B, local98,096B, task schema 상계4,906B/실제 compact block4,060B다. 전체 보수적 예약20,053,740B, 실제 run plan12,305B/manifest 상계236,443B, physical output1,188,195B로 제출된 소형 set의 종료 검증까지 완료했다.

Source planning1,152,653/iteration5,487,889; local을 포함한 group planning92,338/local iteration402,765; plan finalization104,367=세 측정 pass38,269+한 serialization 예약66,098이다. Runtime 예약 stream5,890,654/block78,496/terminal3,783,088과 실제 raw SHA1,188,195B를 구별하고, physical file hash I/O9,950,790B/136완료 hash는 별도다. 소형 planning0.525111초/write+finish1.239717초이며 RSS는 이 관찰에서 측정하지 않았다.

Opaque refs/temporary 경로가 달라 다른 fixture 실행의 길이와 조금 다를 수 있다. 위 tuple은 한 동일 fixture끼리의 값이다. 출력 예약은 source/local helper의 보수적 upper bound와 block schema upper bound를 사용하며 최소 exact 실제 총 byte 예측이 아니다. 실제 block 길이는 상계를 도출한 **뒤에** 생성하여 대조했다. 이런 소형 값·비율로 실제342-entry/105task의 fit을 외삽하거나 압축/표본 admission을 하지 않는다. Temporary 검사 output은 영구 음악 사례/악보 검수 화면이 아니다.

## 실행 revision

| 새 파일 | SHA256 |
|---|---|
| `src/musicanote_harness/proof_shared_progression_streaming.py` | `b0dfb8a36255fd13022c85579e8a0b1d348c71b94f38c6044835486c4aaffa79` |
| `tests/test_proof_shared_progression_streaming.py` | `89a60ded48d1c7ef2135cc0fa6f64c16dac9e7ffc740ba1ade3deea6b450d94c` |
| `src/musicanote_harness/proof_shared_progression_storage.py` | `7c3c516501c76975c4b3f9d1db8b06ae4e0ed2115e183cea4cf4113ac85badd8` |
| `tests/test_proof_shared_progression_storage.py` | `12ea3734965430834ee71467bf60eb03117048c08d8d38a1d87dbb67508a174c` |
| `src/musicanote_harness/proof_shared_request_coordinator.py` | `3c10b62cb355ac01b3123d667a471260f1e334fa9a9d81b3da1ce21923376fce` |
| `tests/test_proof_shared_request_coordinator.py` | `1bbf6399c39d23b5f92e5316c51526aee5438fca4a452c6c3df8a967eb939d5f` |

검사 명령은 `PYTHONPATH=src;tests`에서 `.venv/Scripts/python.exe -B -m unittest`와 위 세 test module명을 사용했다. 최초 중간 통합 이후의 frozen final module 검사는 각각 별도 fresh process다. Predecessor는 `test_cross_batch_read_budget test_native_progression_contrast`를 실행했다. 원 actual corpus run이나 기존 실제 output의 재계산을 이 명령에 포함하지 않는다.

## 다음 큰 단위

1. 이 library·중단/종료 계약을 최종 고정하고 기존43파일·원자료/old 결과 불변을 확인한다.
2. 별도 fresh scoped 실행기에서 정확한 원 한 completion을 다시 admission한다. 앞선 JSON report에서 owned 권한을 복원하지 않는다.
3. 모든105tasks/source/local catalog의 whole schema bounds와 전체2GiB 예약을 **실제 같은 요청에서** 확인한다. Hold이면 숫자·원 분모·원인을 저장하고 pair 계산0을 유지한다.
4. 예약이 통과할 때만 bounded whole block 비교·source-once 저장을 수행하고, 실제 computed/persisted/held/unconfirmed·decoded/physical bytes·시간/RSS·SHA/inventory closure를 보고한다.
5. 그 다음 음악적 평가·진행 선택 정책과 악보 검수 화면으로 돌아간다. 기술 저장 성공만으로 화성 정답/secondary/NCT/cadence 개선을 선언하지 않는다.

Full archive의 나머지3completion/6,340후보, authenticated reload/resume, winner·production UI·구조/생성 연결은 별도다. Actual bounds가 큰 경우도 arbitrary cap 증가나 일부 entry 삭제로 성공시키지 않는다.

## 최종 보존·문서 QA

기존43개 동결 파일과 새6개 최종 source/test의 총49 SHA는 검사 종료 뒤 정본과 같고 변경0이다. Root6AST/3문서 strict UTF-8·replacement character0/167local Markdown file links·누락0을 확인했다. Read-only `git diff --check`는 exit0이며 원래 tracked5 파일과 LF→CRLF 경고만 남았다. Git/권한/설정/서버/UI/원 corpus 변경이나 원 actual 결과 재계산은 없다. 마지막 QA 이후 이 완료 기록만 추가했으며 최종6코드는 수정하지 않았다. 문서 QA와 SHA 조회는 신규 unit-test 수에 더하지 않는다.
