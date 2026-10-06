# Source 공유 대비와 전체 누적 읽기 예산

기록 ID: `HARM-DEV-20261003-32` · 날짜: 2026-10-03.

이 문서는 화성 분석 **개발 문서**다. 직전 [저장·중단 처리와 실제 읽기 예산](2026-10-03-cross-batch-storage-and-read-budget.md)의 자원 차단을 보완하는 별도 구현 단위다. 새 두 library·소형 연결·독립 검수를 완료했다. 실제 archive bridge/공유 저장 adapter/전체 대비는 아직 없으며 기존 파일을 새 계약으로 소급 변경하지 않는다.

## 1. 목적과 범위

원 completion/key별 완전 진행 후보를 비교할 때, 모든 group에 동일한 scope/lattice/bundle 전체를 복사하는 방식을 피한다. 원자료는 한 번 소유하고, group은 자기 원 요청·selector·entry·검증 facet·유리수 refinement와 공유 원자료 참조만 갖게 한다. 동시에 metadata와 body를 읽는 모든 loader가 **한 개의 누적 읽기 계획/계정**을 사용하도록 새 기반을 만든다.

이는 특정 악곡의 화음 정답을 바꾸는 작업이 아니다. XML/Core/원음표 ID/타이/주석/기존 producer/과거 결과는 보존한다. 설명량을 winner/confidence 또는 학습/Gold로 바꾸지 않는다. UI·구조·작곡·편곡 연결도 이번 단위의 범위가 아니다.

전체 흐름은 다음과 같다.

```text
등록된 물리 SHA + 순서 있는 전체 읽기 계획
    → whole-budget 사전 검사 → 하나의 누적 reader
    → Source(scope/lattice/bundles) 한 번 소유
        → 원 request A/key별 group → bounded pair block
        → 원 request B/key별 group → bounded pair block
```

이 화살표는 목표 연결 계약이다. Frozen archive admission과 저장 runner의 실제 연결 완료를 뜻하지 않는다. 새 library의 caller-declared 제출 집합과 역사 원 archive 전체 요청의 인증은 별개다.

## 2. 이전 문제와 구별해야 할 비용

[동결 자원 관찰 receipt](../../../reports/cross-batch-read-budget-observations-2026-10-03-r1.json)에 기록된 실제 두 등록 구간/원4completion은 8,050entry, 20group, 1,652,640예정pair, 570비어 있지 않은 block이다. 곡 수나 음악적 정답 수가 아니다.

| 문제 | 이전 관찰 | 이번 해결 방향 |
|---|---|---|
| Group마다 full lattice 포함 | 10회/source면 lattice 직렬화 합계 1,846,030,670bytes | Source catalog 한 번, group에는 source 참조 |
| 보수적 old catalog 상계 | lattice만으로 827,210,888 / 649,613,648bytes, group cap 256MiB 초과 | source bytes와 group-local bytes/work를 별도 계획 |
| 누적 decode | metadata 포함 3,007,200,897bytes, 기존 1GiB보다 1,933,459,073bytes 큼 | 읽기 전 전체 occurrence 상계 예약, 부족하면 전체 hold |
| Loader마다 계정 재설정 가능 | old reader를 별개 생성하면 전체 합을 보호하지 못함 | 소유된 reader 하나와 exact-next read 순서 |
| 오류 읽기 미계상 | old reader는 successful bounded read만 charge | 실패/부분/미상 소비를 환불하지 않고 종료 상태에 보존 |

**Source 공유는 decode 2.8GiB를 1GiB로 줄이지 않는다.** 앞의 직렬화 합계는 RSS 실측이 아니며 새 codec의 실제 대형 source/group 비용도 아직 측정 전이다. 이번 단위에서 기본 한도를 임의로 올리지 않는다. 전체 비교 실행 전 별도 입출력 codec/필요 자원 정책과 결과 독립 pilot가 필요하다.

## 3. Source 공유 계약

- 새 버전/별도 owned source 및 group handle을 사용한다. Old `PreparedGroup`을 위조하거나 private 발급 상태에 새 JSON을 등록하지 않는다.
- Full scope/lattice/bundles의 seal·binding·source closure를 source factory에서 검증하고 immutable하게 소유한다. 외부 export는 복사본이며 재주입 계산 권한이 아니다.
- 각 group의 원 request, key, bundle, selector 순서/ID는 그대로다. 같은 bundle을 참조해도 서로 다른 원 completion request를 합치지 않는다.
- Source cap과 local group bytes/work cap을 분리한다. 큰 entry/pair 수는 quadratic task/pair 배열이나 intrinsic 계산을 시작하기 전에 count gate로 보류한다.
- Profile/role clause/union 계정을 동일 source에 재검증한다. 검증용 작은 projection은 원 sealed source를 재봉인한 새 음악 자료가 아니다.
- Compact pair는 새 codec이다. 복원 결과는 기존 pair 설명과 정확히 같아야 한다. Rational note-time·원 row-index cell·bass fact·타이/재공격·alias·원음표 multiplicity·unknown과 0을 보존한다.
- 빈 group도 original key/bundle identity가 필요하다. 원 요청 미상과 실제 0pair를 혼동하지 않는다.
- Source 공유형 group을 frozen storage에 억지로 넣지 않는다. 새 storage adapter, 원 archive membership bridge, authenticated reload/resume는 별도 단계다.

## 4. 전체 읽기 예산 계약

- 순서 있는 **모든 read occurrence**와 등록된 물리 SHA를 먼저 고정한다. 같은 파일을 두 번 읽으면 decode 비용도 두 번 예약/계상한다.
- 기본 cap은 total decoded 1GiB, 파일당 decoded 256MiB, physical 64MiB를 유지한다. Missing/unknown byte budget은 0이 아니다.
- 전체 합이 부족하면 첫 body를 읽거나 부분 비교를 시작하기 전에 whole hold한다. 원 요청/group/pair 등 입력된 전체 분모를 복사해 보존한다.
- 소유 reader는 exact-next occurrence만 허용한다. 새 loader가 별개 계정을 열거나 임의로 skip/reorder하여 완료를 만들 수 없다.
- Bounded gzip stream과 읽기 전후 physical SHA를 사용한다. Decode 실패/oversize/JSON 실패에 따른 시도 및 부분 소비는 환불하지 않는다. 확인 불가능한 소비를 성공 0으로 적지 않는다.
- 필요 시 exact inventory root를 보호하고 새 output을 보호 archive 안에 두지 못하게 한다. Physical SHA 확인 비용과 decoded JSON 비용은 서로 다른 계정이다.
- JSON 중복 key와 nonfinite 숫자를 거부한다. Metadata elapsed 같은 finite float의 허용과 음악적 rational no-float 계약은 별개다. 읽기 성공만으로 음악적 body/profile 검증 완료를 선언하지 않는다.
- Submitted ordered reads의 완료가 full archive original membership나 live native authority를 뜻하지 않는다. Frozen admission은 이 새 reader로 연결하기 전까지 이전 동작이다.

## 5. 구현과 검증

### 5.1 새 파일과 API

| 파일 | 역할 |
|---|---|
| [shared_source_progression_contrast.py](../../../src/musicanote_harness/shared_source_progression_contrast.py) | 별도 Source/Group planning·owned handle·compact block·원 pair 설명 복원 |
| [cross_batch_read_budget.py](../../../src/musicanote_harness/cross_batch_read_budget.py) | 전체 ordered read 예약·한 번 발급하는 누적 reader·실패/terminal ledger |
| [test_shared_source_progression_contrast.py](../../../tests/test_shared_source_progression_contrast.py) | 소형 genuine XML의 공유/음악 사실 보존·budget/위조/변경 반례 |
| [test_cross_batch_read_budget.py](../../../tests/test_cross_batch_read_budget.py) | 작은 physical JSON/gzip 파일과 whole hold·실패/미상·SHA/inventory 검사 |
| [test_shared_source_read_budget_integration.py](../../../tests/test_shared_source_read_budget_integration.py) | Root 작성: 실제 XML에서 만든 saved body → 하나의 reader/source → 별개 원2request 연결 |

Source API는 `SourceLimits`, `SourcePlan`, `preflight_saved_source`, `prepare_saved_source`, `PreparedSource.export_source()`다. Group API는 `GroupLimits`, `GroupPlan`, `preflight_saved_group`, `prepare_saved_group`, `SharedPreparedGroup.export_catalog()/iter_blocks()`, `compare_block`, `materialize_pair`다. 새 prefix/codec은 old catalog와 호환이라고 가장하지 않는다.

Read API는 `ReadInput`, `InventoryRoot`, `ReadLimits`, `plan_read_run`, `begin_reads`, `RegisteredReader.read(path)`, `read_record`, `read_ledger`, `finish_reads`다. 선언한 decoded 길이는 **caller reservation**이지 측정 인증이 아니다. Runtime 실제 길이가 정확히 같아야 성공한다. 같은 plan에서 두 번째 reader 발급은 금지한다.

Source retained byte 상계는 source 입력 canonical JSON bytes + 고정 16,384byte wrapper 예약이며 actual encoded bytes를 다시 확인한다. Source work 상계는 입력 bytes×8+count 비용이다. Local group은 source의 full lattice를 직렬화하지 않고 선택된 origin projection·scope의 임시 복사 비용을 work에 포함한다. Default source 256MiB와 group 256MiB cap은 별개며, 전체 output/RSS를 이 두 cap의 단순 합으로 보장하지 않는다.

### 5.2 독립 검수에서 발견한 문제와 교정

1. **원 입력 변경 검사 누락:** 첫 구현의 `before` digest가 사용되지 않았고 catalog와 원 entry가 같은 객체라 마지막 비교가 항등이었다. Default key/bundle 정규화 전 metadata 참조를 보존하고 원 entry/selector/request/key/bundle digest를 다시 대조하도록 고쳤다.
2. **동결 직전 변경 창:** 새 source sealer는 full deepcopy를 피하므로 동결 전 digest 검사만으로 부족했다. Source/group와 숫자 point cache를 먼저 동결한 뒤 원 입력 digest와 owned source 상태를 마지막 확인하며, 그 이후에는 frozen 자료만 사용한다. 동결 callback 변경 반례를 추가했다.
3. **다른 자료의 참조 유입:** Lattice 분석 span·key full-scope segment·origin의 source/scope/catalog ID/span·bundle의 lattice/binding/span 연결을 명시 검증한다. 다시 seal한 잘못된 참조도 받지 않는다. 이것이 whole native reconstruction이나 원 archive membership 인증이라는 뜻은 아니다.
4. **작은 공유 비용의 누락:** Group에서 필요한 scope 및 선택 origin의 임시 projection 비용을 source에서 한 번 계산한 byte inventory로 work 상계에 포함했다. 모든 origin을 group마다 재복사하지 않는다.
5. **누적 reader의 거대한 반복 해시:** 초기 버전은 각 read 전후 모든 보호 파일을 반복 해시했다. Full registered SHA/exact root 검사는 plan/begin/finish에 하고, 매 read에서는 target/current-code 전후 및 같은 open target의 physical SHA를 검사한다. 다른 보호 파일의 변경은 최종 전체 guard에서 submitted completion을 차단한다. `read_complete`와 terminal 전체 integrity를 구별한다. 비용 카운터는 보존하며 대형 archive 성능은 아직 미측정이다.
6. **오류/중단 ledger와 count 경계:** 암묵적으로 추가하는 current-code 파일도 registered count cap에 포함한다. Begin/finish guard 중단은 원 분모와 hash 비용 미상(null)을 보존한 종료 상태로 바꾸고 재시작을 막는다. Decode/JSON 실패의 byte charge는 환불하지 않는다.
7. **Source cap 경계의 자기 의존:** 초기 상계에 `serialized limits bytes×4`를 넣어 cap의 자리 수를 바꾸면 상계 자체도 바뀌었다. 실제 source record는 limits 본문을 저장하지 않으므로 고정 wrapper 예약으로 바꾸고 exact cap/minus1 반례를 통과시켰다.
8. **Task metadata의 타입 우회:** 새 block의 네 SHA 필드는 정확한 `str`만 받으며 pair도 plain dict를 요구한다. 사용자 equality 동작으로 외부 metadata가 유입되지 않도록 마지막 타입 검사와 대상 재검사를 추가했다.

### 5.3 검사 상태

| 검사 | 최종 결과 | 범위 |
|---|---|---|
| Source/shared group | 작성27개/47.275초 PASS, 마지막 타입 변경 대상1개/2.133초 PASS | Genuine XML·원 pair exact equality·source once·cap/위조/변경 반례 |
| 누적 reader | 작성24개/0.443초 PASS | Physical JSON/gzip·repeated occurrence·whole hold·실패/미상·SHA/inventory |
| Root 최종 합동 | **54개/50.965초 PASS** | 위27+24 및 root XML 연결3, 최종 source/test SHA 상태에서 재검사 |
| 별도 기존 회귀 | **41개/93.696초 PASS** | Frozen core25+admission16 |

새 고유 검사는54개다. Root 연결의 초기3개/2.747초, reader 독립 이전23개/0.426초와 source geometry2개/0.046초, 마지막1개 대상 검사는 subset/재검사이지 별도 고유 검사 수가 아니다. 독립 최종 차분 검수의 추가 차단 문제는0이다.

초기 shared source22개/36.541초 실행에서는 source cap exact/minus1 기대1개가 실패했고 §5.2의 자기 의존 상계를 교정했다. 이어 genuine 음악 사실4개와 freeze-window1개를 추가한27개가 통과했으며, 마지막 metadata 타입 변경 후 root가 전체54개를 다시 통과시켰다. 초기 실패/중간 실행을 최종 통과 수에 더하지 않는다.

작은 `passing` XML의 관찰은 source encoded 1,060,861bytes/상계1,076,004/work8,491,040, local catalog encoded232,162bytes/local input176,285/상계1,608,764/work640,792다. Frozen source index의 origin은 모두 원 catalog 내부의 같은 객체다. 관찰용 export 한 번만 복제했으며 group/block에서 full source export는 없다. 이 숫자는 실제 corpus/RSS/속도 개선 실측이 아니다.

실제 corpus full body join/pair 계산, 새 corpus output, UI·정책 변경은 이번 단위에서0이다. Fixture factory의 native/role 호출은 작은 합성 XML 입력을 만들기 위한 것이고 saved-only 연결 안에서는 producer 호출을 금지한다.

### 5.4 여전히 미확인인 자원과 범위

Source 공유 library가 완성돼도 실제20group이 default cap에서 전부 admissible인지는 **미확인**이다. Local entry/facet/refinement의 상계는 여전히 커질 수 있으며, 정확한 새 비용은 실제 planner/pilot로 측정해야 한다. Source 한 번의 wrapper bytes, 준비 과정 peak memory, 각 group의 local encoded bytes/work, 570block의 실제 output/runtime은 미측정이다. 기존 관찰만으로 새로운 codec의 실제 성공이나 속도 향상을 선언하지 않는다.

누적 reader는 역사 archive의 root membership/creation snapshot/원 terminal/selector 집합을 인증하는 loader가 아니다. Frozen admission/storage는 아직 기존 type/API를 사용한다. 새 source/group handle을 old private state에 등록하거나 frozen 함수에 monkeypatch하여 이 경계를 우회하지 않는다.

### 5.5 동결 SHA와 보존

| 신규 파일 | SHA256 |
|---|---|
| `shared_source_progression_contrast.py` | `556ee3e7e5b2d0b7e414035e5cbe037571e415a40e6d9c4551fff37bdac267c2` |
| `cross_batch_read_budget.py` | `827bbed177ee6c1180077b8d012d80c6da811ac59be1dba507a021088e33e882` |
| `test_shared_source_progression_contrast.py` | `8c2f5b790e0995d6c23be4b332b54e0f21dc5a08b65b9a2da869c5d2dfcbe546` |
| `test_cross_batch_read_budget.py` | `f918f78b3bd8e829596915cdb3df97b63b9056375507809e0d2ffa01c040aa2d` |
| `test_shared_source_read_budget_integration.py` | `dba3e93e7e032d0219693fad28bb6acbfeebf9fae36fe5149dcaa69374672819` |

Root가 선행 동결**15파일**을 검사해 SHA 변경0을 확인했다. 범위는 admission/core source/test4 + storage source/test/연결3 + replay source/test4 + resource probe/wrapper2 + resource/read-budget receipt2다. 전체 과거4,788SHA를 이번 단위에서 다시 검사한 것은 아니다.

원XML/Core/주석/과거 output/선행 producer·별개 tracked5 사용자 변경은 보존했다. 신규 corpus output, Git commit/push, 권한·설정 변경은0이다.

최종 QA는 새5Python AST·8strict UTF-8 text·156local Markdown link·새5/선행15동결 SHA에서 오류/변경0이다. Read-only `git diff --check`는 exit0이고, 기존 tracked5의 LF→CRLF 경고만 유지했다. Git 상태의 tracked5 목록도 동일하다. 문서 갱신 후 최종 QA를 재확인하며 새로운 음악적 완료를 선언하지 않는다.

## 6. 다음 큰 단계와 완료 판단

1. 새 reader/source/group을 역사 원 completion/selector 집합에 연결하는 **버전 있는 archive bridge**. Caller-declared membership를 원 archive 인증으로 바꾸지 않는다.
2. Source catalog 한 번 저장 + local group/block 저장의 새 adapter. Whole output 예약·중단/부분 저장·최종 coverage는 직전 저장 계약과 같은 수준으로 검증한다.
3. 입출력 전체 자원 정책을 결정하고 결과와 무관하게 선정한 first/max-cost 실제 group pilot. 시간/RSS/decoded bytes/실제 encoded output·원 refs equality를 계측한다.
4. Pilot를 통과한 범위에서 전체 원4completion/20group 대비. 전체 1,652,640pair 계산/저장 완료와 음악적 선택·정확도를 구별한다.
5. 그 후 조건부 근거를 종합하는 일반 진행 판단 정책과 여러 작품군 평가, 전체 악보 UI와 feedback case 연결. 최종 화성/종지·구조·작곡/편곡 승격은 별도 검증을 거친다.

화성 엔진 기반의 큰 기능 순서는 [메인 개발 문서](../README.md)를 따른다. 자원·참조 오류는 다음 계산을 무효화하므로 여기서 먼저 해결하되, 개별 악곡의 미세 정답 보정으로 개발 범위를 확대하지 않는다.
