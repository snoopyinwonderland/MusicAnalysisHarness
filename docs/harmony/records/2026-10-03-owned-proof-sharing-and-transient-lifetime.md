# 단계36 — 소유한 불변 검증 증명과 임시 자료 수명

상태: 새 versioned library·고유96검사/기존52회귀·독립 코드 검수와 같은 원 요청의 실제 resource-only pilot를 완료했다(exit0). 원5group 모두 기본 gate를 통과하여 새 owned group5개를 발급했다. Pair 계산은0이며 음악적 정확도나 화면 적용 완료 문서가 아니다.

## 목적과 선행 결과

[단계35](2026-10-03-lossless-compact-group-and-exact-refinement.md)에서는 모든 음표/후보/근거를 보존하며 exact endpoint union을 만들었다. 실제 한 원completion의 5group은 각342entry/58,311pair/21block·atoms69/vector23,598이지만 whole work1,617,278,315~1,682,682,609로 기본1B를 넘었다. 실행1002.4669633초/peak9,393,307,648B였고 prepared0/pair0이다. 이 기존 결과와 당시6파일/선행31파일은 동결한다.

이번에는 음악 규칙을 새로 바꾸지 않고 동일 입력을 다시 측정·복사·해시하는 비용과 GC까지 남는 임시 memo의 수명을 줄인다. 원XML/Core/주석·원 selector/path/role/음표ID·유리수 음가·철자·타이/재발음·note-time multiplicity·unknown/null/0·legacy pair 설명은 유지한다. 특정 작품/마디 예외나 cap 증가는 하지 않는다.

## 안전한 공유의 범위

- Caller의 mutable JSON은 검증 증명이 아니다. 사전 logical expansion 검사를 거쳐 직접 소유한 불변 snapshot에만 새 proof를 발급한다. Snapshot에 원 mutable list/dict를 빌려 붙이지 않는다.
- Measurement 뒤 실제 immutable snapshot의 exacttyped 내용/비용/fingerprint가 같음을 확인한다. 이후 caller mutation과 무관한 owned snapshot을 대상으로 계산한다. Imported JSON/claimed SHA/record ID/foreign handle은 proof나 음악/archive 권한을 복원하지 않는다.
- 같은 typed subtree를 공유하더라도 원 occurrence/순서/selector/ref를 합치지 않는다. Raw legacy record seal은 canonical JSON SHA이고 structural Merkle fingerprint와 다르므로 서로 대체하지 않는다. Parent SHA도 child SHA만 결합해 원 JSON hash 대신 쓰지 않는다.
- Exact owned node의 canonical seal-body 해시/검증 결과는 한 번 계산해 재사용할 수 있다. 실제 남는 parent canonical byte hashing, intrinsic role/account/clause 검증·facet·source projection·endpoint/refinement/pair·encoded exchange/catalog finalization 비용은 계속 계상한다.
- 증명의 source/completion/key/bundle/selector/path/role/원음표 binding이 달라지면 재사용하지 않는다. 작은 요약 또는 성공 flags가 동일하다는 이유로 공유하지 않는다.
- 새 group capability는 별도 registry에 발급한다. 이전 private group/archive registry에 삽입하거나 old frozen terminal의 미완료 flag를 새 성공으로 변경하지 않는다.

## 임시 메모리 계약

Preflight뿐 아니라 encode/decode/import의 recursive helper가 memo/intern/nodes/costs 또는 owned bank를 자기 closure로 GC까지 붙들지 않게 한다. Module-level recursion/명시 state를 사용하고 성공/hold/error 경로의 transient buffers를 정리한다. 예외 traceback을 보관한 경우에도 비용표/복사 bank가 불필요하게 남지 않는지 검사한다.

GC-disabled synthetic controls는 실제 음악/전체RSS 측정과 별개다. `gc.collect()` 호출을 추가해서 현상을 숨기지 않는다. 원 archive/body·실패 이유·read ledger·traceback 자체는 지우지 않으며 OS allocator 반환과 Python 객체 수명도 구별한다.

## 새 파일과 역할

- `src/musicanote_harness/lossless_json_dag_v2.py`, `tests/test_lossless_json_dag_v2.py`: 새 immutable JSON proof·측정/encoding 공유와 helper lifetime.
- `src/musicanote_harness/proof_shared_source_progression_contrast.py`, 해당 test: exact binding의 validation proof와 새 local group·원 row-pointer 대비.
- `tmp/proof_shared_scoped_group_pilot_20261003.py`, `tests/test_proof_shared_scoped_group_pilot_runner.py`: 같은 fresh scoped read/원 전체5group/resource 관찰. Root helper는 summary gate만 제공하고 group 발급은 owned library가 재검증한다.

기존 GroupLimits/source/read 기본한도와 frozen37파일은 유지한다. 새 코드를 실행 직전에 동결하며 실행 후 같은 SHA와 원출처 guard를 확인한다. Source-once 저장/완전 비교·authenticated reload/resume는 actual default gate를 통과한 뒤 별도 계약으로 진행한다.

## 검증·진행 기록

- 시작 시 선행37 source/test/receipt SHA변경0과 기존tracked5 사용자수정을 확인했다. `AGENTS.md` 검색 결과는 없음이다.
- Root의 새 runner 초기12개/0.014초, baseline scope/unknown controls2개 추가 후14개/0.016초 PASS다. 직전 pure controls8개를 새 runner에 재연결한 회귀와 새 readiness/baseline6개이며 초기/subset/재검사를 중복 합산하지 않는다. 모든 원 group 분모/whole hold·empty/prefix/unknown/bool/incomplete 거부와 explicit GC workaround 부재를 검사한다. 실제 corpus 실행은 이 검사에 포함하지 않는다.
- 새 DAG/core 구현과 독립 감사 결과·문제/교정·최종검사·실제 실행은 아래 완료 시 추가한다. Reviewer는 원 archive 본문을 다시 읽거나 수정하지 않는다.
- 독립 검수에서 count gate 뒤 owned snapshot의 후보 수가 바뀔 수 있는 간격과, composition 할당 전에 전체 source/intrinsic/seal/pair 비용을 뺀 남은 예산을 확인해야 하는 점을 발견했다. 작성자에게 교정을 요청했던 당시 진행 상태이며 최종 해결/검사 여부는 아래에 구별해 기록한다.
- Root의 초기 `rg` 조회에서 추정한 두 모듈명이 없어 exit1을 받았으며 실제 legacy imports의 모듈명으로 확인했다. 읽기 전용 진단 오류이고 원자료 수정·성공 검사로 세지 않는다.
- 작성 중 core 자체23개/42.392초 PASS 뒤 확장32개/47.368초에 lifetime2개가 실패했다. Recording Mock이 proof 인수를 보관하는 test instrumentation 문제를 non-recording wrapper로 바꾼 focused2개/2.778초는 PASS다. 이후34개/44.042초 재검사에서는 작성 중 DAG의 signed-state 전환과 겹쳐 mappingproxy deepcopy 관련28ERROR를 받았고 helper에서 교정 중이다. 이 실패 실행과 부분검사를 최종PASS로 바꾸지 않으며 helper revision이 안정된 뒤 전체검사를 다시 한다.
- Root의 기존DAG24+새runner14 재검사38개/0.341초 PASS는 위 root14와 중복을 포함한다. 최종 신규 수에 합산하지 않는다. 기존 reader/native 회귀52개/19.500초 PASS는 별도 실행했다.
- 새 helper의 초기39개 중 gate/cleanup2실패와 초기46개의 잘못된 cap 기대값1실패를 교정했다. 독립 검수에서 malformed-path와 final record-copy 중단의 traceback이 owned bank/부분 export를 붙들 수 있는 경로를 추가로 확인하여 facade/worker `finally`와 부분 list 정리, GC-disabled retained-traceback 검사를 보완했다. Helper 최종48개/0.749초 PASS, 독립 helper48+runner14=62개/0.995초 PASS다. 이전46/47/부분검사는 고유 수에 더하지 않는다.
- Core의 소형 full-plan 출력에서 모든 원 roots를 보존했는데 성공 stage가 `catalog_finalization`으로 남아 `all_original_entries_retained=false`가 되는 summary 오류를 발견했다. 새 root whole gate는 이 상태를 안전하게 거부했을 것이며 false success가 아니라 불필요한 보류다. Final catalog seal 전에 `stage=complete`를 명시하고 stream 검사에 retention/stage assertion을 추가했다.
- Root의 새 helper48+core34+runner14=96개/57.538초 PASS 실행은 마지막 core stage/assertion 편집과 시간상 겹쳐, helper48/runner14는 고정판 검사로 인정하되 core34는 마지막 SHA에서 별도 재검사했다. 중간 PASS를 최종판에 소급하지 않는다.
- 최종 SHA에서 root core34/55.107초 PASS, 작성 core34/56.536초 PASS, 독립 core34/55.306초 PASS다. Helper48+runner14 고정판과 합한 신규 고유 수는96개다. 독립 최종 추가 차단0을 확인한 뒤 새 output에서 실제 pilot를 시작했다. Unit tests에 실제 음악 정확도나291,555pair 완료를 포함시키지 않는다.
- Root의 개발 문서 patch1회는 bullet prefix context가 맞지 않아 무변경 실패했고 정확한 context로 다시 적용했다. 자료/코드 변경이나 성공 검사로 세지 않는다.

## 확정 API·비용 모델

`lossless_json_dag_v2` schema version은 `0.2.0`이다. `freeze_json`은 한 input guard와 한 snapshot validation, 즉 `2×(expanded bytes+visits)`에 exact fragment-size measurement와 fragment serialization을 더한다. `encode_proof`는 mutable tree 재측정 없이 같은 owned nodes를 쓰되 final exchange serialization과 실제 codec SHA scan `2×encoded bytes`를 추가한다. `compose_proofs`는 captured key/handle tuple을 한 번 고정하고 inherited proof 비용과 reindex/root hash/fragment 비용을 구별한다. Work units는 시간/RSS/음악 정확도가 아니다.

`proof_shared_source_progression_contrast` version은 `0.2.0`이다. `preflight_saved_group`→owned `GroupPlan`→`prepare_preflight`가 기본 경로다. `record()`는 외부 summary일 뿐 capability가 아니다. Entry/facet export·block compare·원 pair materialization은 exact legacy semantics를 유지한다. Snapshot/decode/seal/domain/facet/endpoint/refinement/pair/composition/encoding/catalog finalization 비용을 각각 계상한다. Late hold에서는 직전 완료 stage의 group bound와 codec attempted cumulative lower bound를 diagnostics로 분리 보존하며, 두 수치를 그대로 더하지 않는다. 미측정 단계의 값은 `null`이며0으로 바꾸지 않는다.

## 소형 메모리 관찰 — 실제 pilot와 구별

원1500row synthetic fixture의 logical509,385B/37,501visits/depth5에서 automatic GC를 끈 채 preflight4회 후 traced current는144,512→144,844→144,960→145,844B, peak1,913,330B·issued handles0였다. Explicit GC 호출0이다. 직전 helper에서 memo가 GC까지 누적되던 소형 재현과 달리 새 worker는 임시 state를 즉시 정리한다. 이것은 Python traced allocation 관찰이며 실제342entry/RSS 전체 원인이나 음악 정확도 실증은 아니다.

50occurrence 소형 fixture는 logical60,753B/753visits를 encoded6,907B/109nodes로 보존했고 decode exact equality가 참이다. Whole codec work145,876=123,012(two logical passes)+2,235(fragment sizing)+6,815(fragment serialization)+6,907(final serialization)+6,907(codec SHA)다. 단계35의 같은 fixture198,240은 이전3pass와 codec SHA 누락의 다른 staged accounting이며 단순 같은 의미의 계수 비교로 취급하지 않는다.

소형 genuine2entry의 같은 새 fixture를 두 구현에 함께 전달한 최종 관찰은 다음과 같다. 매 fixture의 opaque refs가 달라 초기 측정과 byte 숫자가 조금 다르므로 아래 최종 같은 fixture끼리만 비교한다.

| 항목 | 동결 단계35 | 새 owned-proof 구현 |
|---|---:|---:|
| Raw input / visits | 176,373B / 14,254 | 176,373B / 14,254 |
| Exact atoms / vector / pairs | 9 / 18 / 1 | 9 / 18 / 1 |
| Whole work units | 3,123,999 | 1,670,773 |
| Preflight seconds | 0.794738 | 0.281810 |
| DAG expanded bytes | 228,070 | 228,221 |
| Encoded bytes | 87,861 | 89,079 |
| Actual catalog bytes | 96,545 | 98,051 |

새 work는 snapshot510,460+decode191,722+seal206,820+source projection139,142+intrinsic1,160+endpoint360+canonical484,457+pair1,462+finalization134,932+refinement252+transition measurement6=1,670,773이다. Canonical484,457은 facet freeze154,429+composition151,870+encode/SHA178,158이다. Input guard1/snapshot validation1, seal/account canonical passes12/distinct nodes8/cache hits0이다. 이 소형에는 seal cache hit가 없으며 절감은 owned 검증/표현 경로의 재측정·복사 감소다. 저장 크기는 오히려 조금 커졌다. 실제 corpus fit/RSS나 화성 정확도 향상 주장으로 확대하지 않는다.

## 실행 revision과 보존

아래6파일은 실제 실행 직전 고정했다. 이전37파일 SHA 변경0·기존tracked5 사용자 변경은 보존했다. Git commit/push·권한/설정 변경은 없다.

| 새 파일 | SHA256 |
|---|---|
| `src/musicanote_harness/lossless_json_dag_v2.py` | `246fee53d02901f893a14c3302aef6282375369e19c638c5581617f25e2052dd` |
| `tests/test_lossless_json_dag_v2.py` | `2706a1484fe40249f176dbfd2cfa04b48e3caa20dce3272e1bbfcab8926dd72a` |
| `src/musicanote_harness/proof_shared_source_progression_contrast.py` | `1814869d6a228d7f8477f6d7f5aedd5cd36c83390a2de6d63f1dd31b58c4794f` |
| `tests/test_proof_shared_source_progression_contrast.py` | `e1b7f9d9fcdd6cc1dab5d87d56c15009cdf18e9b77298bc35a7eb271627fcd67` |
| `tmp/proof_shared_scoped_group_pilot_20261003.py` | `8c79679472b146e71325821274127914c02967709fa85ebf4d75fbee2ea89381` |
| `tests/test_proof_shared_scoped_group_pilot_runner.py` | `9b321f159cfa086e6e344c1d5df0e37cde53c91739ac33c62cca21751b6d3451` |

실행 명령: `PYTHONPATH=src;tests` 상태에서 `.venv/Scripts/python.exe -B tmp/proof_shared_scoped_group_pilot_20261003.py --output output/proof-shared-scoped-group-pilot-2026-10-03-r1`. Actual code의 전체 current SHA를 시작/끝에 검증한다. 코드·기본 cap·이전 결과는 실행 중 변경하지 않는다.

## 실제 resource pilot의 고정 범위

직전 동일 source1/completion0을 비용 기준으로 유지한다. 원 전체4completion/8,050selector/504batch/20group/1,652,640예정pair/570예정block과 선택1/1710/107/5/291555/105·생략3/6340/397/15/1361085/465를 보존한다. Metadata40+선택body214의 전체254execution reads는 fresh SHA/정확 inventory/원ordered membership·selected terminal join을 다시 검증한다. Bootstrap에는 SHA-bound 단계35 report도 추가하여 자원 baseline만 대조하고 이전 authority는 복원하지 않는다. Bootstrap+execution 누적decoded는 기본1GiB에 사전 예약하고 physical guard I/O·RSS와 구별한다. 기존 세 archive/pilot 출력 안에 새 output을 생성하지 않는다.

모든5group preflight가 default gate를 통과해야 group 발급을 수행한다. 한 group이라도 hold이면 전체 요청의 prepared0이며 prefix 승격은 없다. Resource-only pilot의 실제 pair 계산은0으로 남긴다. 전체코퍼스/최종harmony/NCT/key/cadence·winner/confidence·UI/구조·작곡편곡/학습·Gold는 별도 후속이다.

## 실제 완료 결과

[실제 report](../../../output/proof-shared-scoped-group-pilot-2026-10-03-r1/pilot-report.json)의 SHA256은 `410c90e53bed9c8faf71298c0a232d1ee84b28ddfac811a4c2be37306cec701d`, 전체 새 출력은11JSON/908,370B(등록10artifact와 report1)다. Library에서 측정한 아래 encoded/catalog bytes는 owned memory 표현의 정확한 교환 길이이며, 이번 pilot가 그 catalog 전체를 디스크에 저장했다는 뜻은 아니다. Pilot 출력은 계획·읽기·자원 관찰 receipt다.

| 원 group index | Raw input B | 단계35 whole work | 새 whole work | Encoded DAG B | Actual catalog B |
|---|---:|---:|---:|---:|---:|
| 0 | 101,325,701 | 1,676,813,801 | 888,143,168 | 10,568,164 | 12,970,223 |
| 1 | 101,471,170 | 1,678,788,569 | 888,845,940 | 10,569,364 | 12,971,423 |
| 2 | 101,552,990 | 1,679,860,275 | 889,226,932 | 10,567,988 | 12,970,043 |
| 3 | 101,763,374 | 1,682,682,609 | 890,230,520 | 10,568,143 | 12,970,202 |
| 4 | 97,068,749 | 1,617,278,315 | 865,341,814 | 10,472,869 | 12,874,514 |

5group 모두342entry/58,311pair/21block·actual atoms69/vector23,598, `stage=complete`, `reasons=[]`, 모든 원 entry 보존이다. Input guard1/snapshot validation1, canonical seal/account hash passes4,400/distinct nodes4,016/cache hits300은 group마다 같다. Source 입력82,392,179B/상계82,408,563B/work659,616,216, bundles2/catalogs136/origins7,285/sounds53/keys5도 기본 cap을 통과했다. 비교 예정pair 비용까지 포함한 whole work가865,341,814~890,230,520으로 기본1B 안에 들어왔으며, 이전보다46.49~47.09% 줄었다. 실제 pair는 아직0이다. Encoded 합52,746,528B/catalog 합64,756,405B는 서로 다른 표현의 길이이므로 두 수를 이중 저장량으로 합치지 않는다.

Bootstrap5+1=6reads/4,058,934decoded B + execution254reads/950,488,899B = logical total954,547,833B < 기본1GiB(여유119,193,991B)다. 총260ordered occurrences/257unique/반복3이며 execution의 실패/보류/미실행0이다. Exact40metadata+214body와1,710selector/107batch의 ordered joins·selected terminal, 역사 code347·부모6/7/7/148 inventories를 확인했다. 원전체4completion/8,050selector/504batch/20group/1,652,640예정pair/570block 중 선택1/1710/107/5/291555/105, 생략3/6340/397/15/1361085/465는 바뀌지 않았다.

Physical execution body83,105,354B와 bootstrap4,058,934B를 합한87,164,288B, SHA guard5,967,069,895B/19,615attempts는 decoded budget과 별개다. Physical I/O 합6,054,234,183B를 logical954,547,833B에 더해 decoded cap으로 취급하지 않는다. Root 조회에서 큰 terminal 객체를 통째로 출력해 한 번 truncation되었으며 이후 scalar 필드만 추출했다. 출력 truncation은 underlying JSON 검증 실패나 자료 삭제가 아니다.

실행919.403516초/exit0, resource observations43회·peak working set5,163,905,024B(4.809GiB), 최소 sampled available9,317,195,776B다. 단계35의1002.466963초/peak9,393,307,648B와 같은 범위에서 시간 약8.29%, peak 약45.03% 감소했다. 단일 실행 관찰이며 CPU/RSS 상계 보증이나 GC 한 가지 원인만의 효과를 뜻하지 않는다. 마지막 자원 관찰은908.4800719초/current working set4,920,270,848B다. 그 뒤 최종 guards와 report 저장까지 포함한 정확한 종료 currentRSS는 별도 측정하지 않았다. 원 mutable archive 입력과 owned catalog가 아직 살아 있는 시점이며 작은 GC-disabled 검사와 구별한다. Explicit `gc.collect()`0이다.

원 scoped reader terminal은 `finished=true`, `failure/body_failure=null`, selected body/terminal join=true다. 동결 reader가 발급하지 않은 **old intrinsic-group/prepared flag는 false/0 그대로**다. 새 root/library의 owned v2 whole readiness=true·prepared5·서로 다른 group refs5와 별도로 기록하며 old registry/terminal을 성공으로 바꾸지 않았다. 이 fresh process가 종료되면 live owned handles의 authority는 끝난다. Saved pilot JSON이 그것을 복원하지 않는다. Full archive/실제 전체 대비·winner/confidence·NCT/key/cadence확정·UI/구조·작곡편곡·Gold/학습은 전부 미승격이다.

## 최종 결과·다음

Default whole-group gate가 실제 같은 요청에서 통과했다. 다음 큰 단위는 **새 proof-v2 source-once 저장 adapter와 완전한 요청의 비교 coordinator**다. 동결 old writer의 imports/registry를 바꾸지 않고 public reader→owned source/declarations/전체 iterator join→새 v2 preflight/전 group gate→발급→bounded compare/write를 연결한다. Source는 한 번 저장하고 cached DAG bytes+작은 owned metadata를 stream하여 raw entry/facet 전체 export·eager duplicate buffer를 피한다. Whole-block 저장/불확실한 계산·완료/미저장 수·SHA/정확 output terminal도 보존한다.

선행 writer의 기본105tasks×64MiB 예약은7,046,430,720B로 기존2GiB output cap을 catalog/source/manifest 전부터 초과한다. 다음 단계는 schema-derived 보수적인 compact block 상계 또는 명시적으로 낮은 task cap을 먼저 결정해야 한다. 전체 cap 증가, 후보/블록 prefix 생략, 일부 관찰의 압축률 외삽으로 통과시키지 않는다. 여러 원 completion의 통합을 선언하지 않는다.

새 process에서는 fresh same-scope reads와 owned re-admission이 필요하며 authenticated reload/resume는 별도 계약이다. 저장 완료/실제 pair coverage/음악 정확도/운영 적용을 이번 준비 성공으로 대체하지 않는다.

## 최종 독립 감사와 QA

독립 감사에서 신규11JSON·정확 목록/regular non-symlink·등록10artifact의 byte/SHA·report SHA, current10code와 scoped dependency5SHA·신규6동결SHA, 원4request의2315/2315/1710/1710 selector partition·20group/원 pair/block과 선택/생략 분모를 확인했다.5plan seal/entries/pairs/blocks/atoms/vector·whole work/catalog 상계·selected ordered260read/모든 비용·source seal과 한도·old scoped terminal/v2 readiness 구별·미승격 flags에 불일치0/추가 차단0이다. 원 corpus body를 다시 읽거나 수정하지 않고 새 summary/receipts만 감사했다.

Root의 새6AST,3문서 strict UTF-8/깨진 replacement character0,161local Markdown file links,11JSON의 duplicate-key/nonfinite 거부·등록10output SHA/bytes·정확11목록/908,370B·same plan/rootflags/decoded 산술·current10 guard를 모두 PASS했다. 선행37+신규6의 총43 SHA 변경0, read-only `git diff --check` exit0이고 기존tracked5 및 LF→CRLF 경고만 유지했다. 문서 QA와 재검사 수를 신규고유96 unit tests에 합산하지 않는다. 최종 QA 뒤 개발 문서의 완료 기록만 추가했고 실행6코드/검사·원자료/결과는 변경하지 않았다.
