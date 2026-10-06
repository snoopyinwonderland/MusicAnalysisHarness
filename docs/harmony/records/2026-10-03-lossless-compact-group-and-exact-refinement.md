# 단계35 — 무손실 local group과 정확한 유리수 경계 결합

상태: 새 library·검사·실제 resource-only pilot 완료. 실제 선택5group은 전체 연산 한도에서 보류됐다. 화성 정답률이나 화면 적용 완료 문서가 아니다.

## 목적과 기존 문제

사용자의 “네”는 [단계34](2026-10-03-scoped-archive-resource-pilot.md) 뒤의 다음 개발을 진행하라는 요청으로 해석했다. 음악 규칙을 작품별로 변경하지 않고, 여러 완전한 진행 후보를 동일 원음표에서 비교하는 기반의 자원 병목을 해결한다. 구조·화성의 최종 선택과 작곡·편곡은 이 비교 근거를 소비하는 후속 단계다.

직전 실제 한 원 completion은 1,710 selector/107 batch/5 group이며 group마다342 entry/58,311 pair/21 block이다. Source 준비는 통과했지만 이전 group의 보수적 상계는 다음처럼 기본 한도를 넘었다.

| 항목 | 단계34 상계 | 기본 한도 |
|---|---:|---:|
| Refinement atoms | 47,196 | 200,000 |
| Vector cells | 16,141,032 | 10,000,000 |
| Work units | 5,552,879,397 | 1,000,000,000 |
| Local catalog bytes | 1,628,092,116~1,665,649,116 | 268,435,456 |

이전 결과를 삭제하거나 한도를 높이지 않는다. 후보 prefix를 골라 성공으로 바꾸지도 않는다. 원4 completion/8,050selector/504batch/20group/1,652,640예정pair/570예정block과 생략 범위는 계속 보존한다. 이 숫자는 곡 수가 아니다.

## 일반 계약

### 무손실 표현과 음악적 합병의 구별

- 동일 JSON subtree는 representation node만 공유한다. 원 ordered entry occurrence·selector·comparison/explanation ref·native/role path body·key/bundle·원음표 alias·타이/재발음·철자·음가를 유지한다.
- 압축은 같은 음악적 의미로 간주하는 연산이 아니다. F♯/G♭, 지속/재발음, 여러 원음표·동일 시점의 note-time multiplicity를 합치거나 삭제하지 않는다.
- Bool/int, unknown/null/유리수0, list 순서와 dictionary key를 구별하는 versioned typed codec을 사용한다. float·순환·subclass·중복/미존재/forward ref는 거부한다.
- 일반 codec의 JSON reload는 codec 교환만 검증한다. 과거 source/archive/분석 권한을 되살리는 경로가 아니다.
- Canonical Core/원 XML/주석/기존 producer·이전 source/group/read adapter·UI/구조·정책은 변경하지 않는다. 새 group handle은 이전 private registry에 삽입하지 않는다.

### 실제 endpoint union과 pair 의미 보존

- 각 sounding-event와 bass의 실제 `Fraction` start/end 집합을 정렬하여 전체 후보의 공통 grid를 계산한다. 단순히 모든 후보의 행 수 상계를 더하는 것과 구별한다.
- 각 atom은 원 facet row index를 참조한다. Pair 설명을 복원할 때 양쪽 원 row index가 모두 같은 인접 atom만 합친다.
- 세 번째 후보가 새 endpoint를 추가해도 첫 두 후보의 원 pair 설명·구간·slot/origin/clause refs는 달라지면 안 된다. category가 같다는 이유만으로 서로 다른 원 row를 합치지 않는다.
- 원음가, source-note/tie refs, 구성음/조건부 설명/미상, bass·전위·partition·candidate/transition 대비를 이전 순수 비교 함수의 결과와 정확히 대조한다. 높은 조건부 설명량을 승자 점수로 쓰지 않는다.

### 단계별 자원 gate

Count gate → 원 logical input bytes/visits/depth → 필요한 source projection 및 intrinsic entry 검증/facet → 실제 endpoint union·atoms/vector gate → DAG canonicalization과 refinement/index/pair work 예약 → whole group admission 순서다. 자원 검사는 해당 큰 할당/전개 전에 실행한다.

중복 node를 저장하지 않는다고 원 hash/검증/traversal 비용을 없애지 않는다. Encode의 preflight/intern/postflight와 decode의 논리적 확장량을 따로 계상한다. 작은 DAG라도 지수적으로 늘어나는 원 list occurrence는 bottom-up multiplicity/bytes/visits/depth 검사를 먼저 통과해야 한다. Unknown 비용을0으로 바꾸지 않는다.

Source256MiB, group catalog256MiB/work1B/vector10M, 누적 read1GiB 등 기존 default는 그대로다. Catalog encoded bytes는 RSS가 아니다. Frozen scoped iterator는 private raw entries를 보관하고 root public packet도 copy하므로 실제 pilot에는 두 raw tree와 staged DAG가 동시에 존재할 수 있다. 실제 peak/시간을 측정하기 전 메모리 감소라고 주장하지 않는다.

## 구현 파일과 API

이번 단계의 새 파일만 변경한다.

- `src/musicanote_harness/lossless_json_dag.py`, `tests/test_lossless_json_dag.py`: exact typed structural codec, owned immutable handle, bounded import/decode/subtree access.
- `src/musicanote_harness/compact_source_progression_contrast.py`, `tests/test_compact_source_progression_contrast.py`: genuine issued `shared.PreparedSource`에 연결한 새 local group·exact refinement·기존 pair 설명 복원.
- `tmp/compact_scoped_group_pilot_20261003.py`, `tests/test_compact_scoped_group_pilot_runner.py`: 원 전체 selected request membership과 비용 지도·새 그룹 preflight를 연결하는 root 실측기/pure controls.

핵심 호출은 `preflight_saved_group(...) → GroupPlan.record() → prepare_preflight(plan)`다. 이미 검증한 immutable draft를 사용하므로 prepare 때 expensive preflight를 다시 하지 않는다. 실제5 group은 **모든 preflight가 통과한 후에만** 발급한다. 한 group이라도 보류면 원 전체 요청의 prepared group은0이며 나머지 계획/분모는 보존한다.

최종 API·코드 SHA는 아래에 확정했다. Source와 group 파일의 저장·authenticated resume는 이 새 codec에 맞춘 별도 후속 계약이다.

## 실제 pilot의 읽기·권한·범위

직전 step34 SHA-bound 비용표는 advisory cost로만 사용한다. 원 report/run-plan/context-index와 step34 report/비용표를 owned bounded bootstrap으로 읽고, 새 scoped reader에서 전체40 역사 metadata+선택214body를 다시 읽어 원 SHA·정확 inventory·ordered membership/terminal join을 검증한다. 비용표 JSON으로 이전 reader/source 권한을 복원하지 않는다.

원 closure는 원 manifest에서 다시 도출한다. 새 실행 코드 hash는 역사 creation code와 별도로 기록한다. Bootstrap+새 execution의 logical decoded 합계를 기본1GiB에 사전 예약하고 반복읽기와 physical guard I/O를 구별한다. 원 source1/completion0 선택은 단계34의 비용 기준을 그대로 따르며 유리한 음형/분석 결과로 재선정하지 않는다.

1,710 entry/107 batch를 원5 group selector에 정확히 재연결한다. 새compact 준비 결과와 frozen scoped adapter의 old group 완료 flag는 별개다. Whole archive/full corpus/음악 정확도/최종 화성·winner/UI/구조/작곡편곡/학습·Gold 완료는 항상 별도로 남긴다.

## 검증과 발견 기록

- Root pure runner6개: 초기0.007초·최종 재검사0.006초 PASS. Advisory 비용표의 incomplete/unknown/bool/SHA/total·원 전체 그룹 coverage/중복/prefix/pair denominator controls다. 실제 historical archive 성공으로 확대하지 않는다.
- 독립 감사에서 open/begin 실패 시 handle을 받지 못했어도 이미 소비한 read ledger를 보존하도록 교정하고, 최종 SHA 관찰 자체의 예외를 unknown/실패로 기록했다. 추가2개를 포함한 root8개/0.007초와 재검사0.006초 PASS다. 다중 파일 patch 도구가 기대행 오류를 보고했지만 첫 파일은 이미 부분 적용되어 있었으므로 내용을 확인하고 나머지 테스트 파일을 별도로 적용했다. 중복 patch나 원자료 수정은 없었다.
- DAG 최종 author24개/0.032초 PASS, root의 DAG24+runner8 고유32개/0.035초 PASS다. 초기 root DAG23/0.027초는 subset이고 고유 수에 더하지 않는다. Author의 추가24-suite 최초1 ERROR는 테스트 함수 삽입 위치의 `NameError`이며 수정했다. Incremental exchange import work와 final encoded-copy 사전 gate를 보완했고 독립 감사의 추가 차단0이다.
- 소형 synthetic 계량: 서로 다른 selector50 occurrences와 반복 attributed row의 원 logical60,753B/753visits가 typed DAG6,907B/109nodes가 된다. 원50 occurrences·source-note aliases를 exact 복원하고 codec work198,240을 계상했다. 실제 corpus 성능이나 음악 정답률이 아니다. Shared-list 35단계 doubling 반례는10,000B/visit 제한에서 interning/materialization 전 expanded lower bound12,285B/6,143visits/depth13으로 보류했으며 전체 지수 JSON을 직렬화하지 않았다.
- 기존 reader24개/0.363초, 기존 순수 native 대비28개/16.826초 PASS다. 기존 자료의 인터페이스 회귀이며 새 화성 선택 정확도로 해석하지 않는다.
- Compact author 최종 자체23개/60.134초 PASS·2 AST PASS, root 최종 신규55개(DAG24+compact23+runner8)/61.403초 PASS다. 초기44개/82.418초에는 imported 기존25개가 포함되어 있었고 이를 정리한 중간 자체21개/53.679초도 재검사 이력이지 고유 수에 더하지 않는다. 입력/카탈로그 크기를 bytes object와 byte length로 혼동한 계산, weak plan registry의 self-key strong retention, 원 raw guard/seal pass·catalog export/hash/freeze의 비용 누락, 복원 전 source closure·wrapper 한도를 교정했다.
- Genuine 소형2-entry 검사는 원 input176,205B, DAG logical227,293B→encoded88,333B, 최종 localcatalog97,050B(상계97,416B), 실제atoms9/vector18, wholework3,122,125/canonical1,156,966/catalog finalization398,914다. 이전 local rawcatalog 약232,223B와 비교한 작은 표본 계량이며 실제342-entry나 RSS 감소를 뜻하지 않는다.
- 진행 중 readonly diagnostics에서 전체 root-map 출력이53,263tokens로 잘렸고, 예상한 로그 파일명/미작성 테스트 파일 경로 조회가 각각 실패했다. 종료 후 report를 넓은 property 제외 방식으로 출력한 조회도116,708tokens로 잘렸다. 이후 명시 scalar/property와 작은 집계로 검증했다. 분석/원파일 수정은 없으며 tool 오류·잘린 출력은 성공 검사로 세지 않는다.
- 선행31 source/test/receipt SHA와 신규6 source/test SHA는 실제 실행 전 동결했다. 종료 뒤 총37SHA 변경0이다. 새 실행 코드10개에 대한 report의 final guard도 changed/uncertain0이다. 기존 별개 tracked5 사용자수정과 많은 기존 untracked 파일은 보존한다.
- 아래 실제 결과는 신규 고유55검사·기존52회귀와 별개다. 재검사와 subset 수, JSON 유한 일관성 확인 수를 고유 검사 수로 합산하지 않는다.

## 실제 한 원 completion 전체의 resource-only pilot

명령과 새 exclusive 결과 위치:

```powershell
$env:PYTHONPATH = 'src;tests'
.\.venv\Scripts\python.exe -B -m unittest test_lossless_json_dag test_compact_source_progression_contrast test_compact_scoped_group_pilot_runner -q
.\.venv\Scripts\python.exe -B tmp/compact_scoped_group_pilot_20261003.py --output output/compact-scoped-group-pilot-2026-10-03-r1
```

최종 [pilot-report.json](../../../output/compact-scoped-group-pilot-2026-10-03-r1/pilot-report.json)은1002.4669633000158초·45자원 관찰이다. Shell tool은 exit1을 보고했고, runner의 명시 whole-resource-hold 종료 계약은 return2다. 예외 crash나 성공으로 바꾸지 않는다. Failure는 `whole_selected_compact_resource_hold; no prefix group promoted`다. 실행 중/종료 후6새 파일 revision은 동일하다.

### 범위·읽기·보호

- 선택은 직전과 동일한 source1/completion0이다. 등록 현악사중주 구간의 원1completion/1,710selector/107batch/5group/291,555예정pair/105예정block이며 전곡/곡 수가 아니다. 그룹마다342entry/58,311pair/21block이다.
- 원 전체4completion/8,050selector/504batch/20group/1,652,640예정pair/570예정block과 생략3completion/6,340selector/397batch/15group/1,361,085예정pair/465예정block을 유지한다.
- Bootstrap4reads2,189,683B+advisory cost receipt1read1,614,677B=3,804,360decoded B. 새 execution254reads=950,488,899decoded B다. 합계954,293,259B는 원 default1,073,741,824B 이내이며 bootstrap을 뺀 실행 한도1,069,937,464B를 사용한다. 전체259ordered read occurrences/256unique paths/반복3이며 반복은 원 report/run-plan/context-index 각각2회뿐이다. 이전 단계의 별도 두 read 계정을 이번 한 계정으로 소급 변경한 것이 아니다.
- 새 execution은40metadata+214native/role bodies의 모든254reads가 완료됐고 failed/held/incomplete/never-attempted0이다. 원1,710entry/107batch join과 selected-body terminal이 모두 확인됐다. 역사 creation347파일·ordered parent inventory6/7/7/148·원 membership/SHA·scoped 종료 guard를 검증했다.
- Ledger의 physical SHA guard19,604attempts/5,964,744,346B와 compressed/raw body 물리 읽기86,909,714B를 합치면6,051,654,060B다. 이는 decoded 예산과 별도인 파일 I/O 계정이며 RSS·새 음악 계산량·최종 QA 읽기까지의 전체 OS I/O가 아니다. 미완료/unknown/error attempt0이다.
- Source preflight는 input82,392,179B/record 상계82,408,563B/work659,616,216,2bundle/136catalog/7,285origin/53sound/5key로 통과했다. Immutable source를 한 번 발급했지만 producer나 native/role 근거를 다시 계산하지 않았다.

### 정확한 경계 결합의 효과와 남은 hold

| 항목 | 단계34 각 group | 단계35 각 group |
|---|---:|---:|
| 시간 atom | 보수적 상계47,196 | 실제 endpoint union69 |
| Vector cells | 16,141,032 | 23,598 |
| 전체 work 상계 | 5,552,879,397 | 1,617,278,315~1,682,682,609 |
| 실제 encoded catalog | 미생성 | 미생성·unknown |
| 실제 group 발급/pair 계산 | 0/0 | 0/0 |

시간 격자 gate는 통과했지만 canonicalization 단계에서 **모든5group의 whole work가 기본1,000,000,000을 초과**했다. 각 group 전체 분모를 그대로 보류하며 일부 candidate/block만 승격하지 않았다.

| Group | 원 logical input B | DAG expanded B | canonicalization work | whole work 상계 |
|---|---:|---:|---:|---:|
| 0 | 101,325,701 | 131,907,009 | 573,017,040 | 1,676,813,801 |
| 1 | 101,471,170 | 132,109,759 | 573,828,040 | 1,678,788,569 |
| 2 | 101,552,990 | 132,200,509 | 574,234,528 | 1,679,860,275 |
| 3 | 101,763,374 | 132,475,699 | 575,366,104 | 1,682,682,609 |
| 4 | 97,068,749 | 126,313,501 | 548,055,472 | 1,617,278,315 |

위 work는 staged logical traversal/byte 상계로 CPU 명령 수·실제 실행 시간·전체 job work가 아니다. 각 group에는 raw guard/seal의 반복8×bytes+visits, projection 약1.767M, intrinsic validation/facet19,813,053, endpoint943,920, pair reservation261,233,280도 포함한다. 불충분한 gate에서 멈췄으므로 `dag_encoded_bytes`/`actual_catalog_bytes`/`catalog_byte_upper_bound`/`catalog_finalization_work`는 null이다. 소형 fixture의 압축률을 실제342-entry 결과로 전용하지 않는다.

`all_original_entries_retained=false`는 성공한 immutable compact bank가 발급되지 않았다는 뜻이다. 원1710입력의 read/join 완료와 구별하며 원파일·후보를 삭제했다는 뜻이 아니다. Frozen scoped terminal의 old group완료False와 새 compact whole-passFalse도 별개 계약이다. Full archive, all-original-body/group 완료, winner·rank·최종 harmony/NCT/key/cadence·UI·구조·작곡편곡·training/Gold는 미승격이다.

### 실제 메모리와 임시 비용표 수명

이번 process peak working set은9,393,307,648B(약8.75GiB), 최저 관측 physical 여유는4,422,107,136B다. 직전 단계34 peak3,233,386,496B(약3.01GiB)보다 증가했다. 984.046초의 group4 종료 시 current working set9,323,069,440B, 993.876초 마지막 관찰에서는4,536,303,616B로 내려갔으나 정확한 최종 current RSS는 미관찰이다. Runner는 다섯 preflight 뒤 `gc.collect()`를 호출한다. 관찰만으로 감소분 전체의 원인을 단정하지 않으며 peak·현재값·encoded bytes·decoded 예산을 서로 혼동하지 않는다.

별도 readonly synthetic diagnostic에서 `lossless_json_dag._preflight`의 recursive `visit` closure가 자기 자신과 cost memo를 참조하여 종료 뒤 GC까지 memo 수명을 연장함을 확인했다. Memo는 비용 tuple/digest를 보존하지만 원 mutable 입력 객체를 직접 보존하는 것은 아니다. DAG owned handle 수는0으로 유지돼 issued-handle 누수와도 구별한다. 입력1,500rows/509,385B로 실제 archive를 다시 읽거나 frozen 파일을 수정하지 않았다.

- 자동GC+weakref/profile4회: current7,837,060B/closure4개 → 명시GC뒤12,132B/0개.
- Profiler 없는 독립 자동GC3회: current2,089,605→4,001,922→5,914,207B, GC직전5,914,231→직후1,660B/596객체 수거.
- 이는 tracemalloc 소형 재현이며 RSS 측정이 아니다. 실제 약8.75GiB 전부의 원인·영구 누수·수정 완료라고 주장하지 않는다. Python allocator의 OS 반환도 별개다. 이번 실행 code freeze를 유지했으므로 이 임시 수명 문제는 아직 미수정이다.

Profiler 없이 재현하는 작은 명령(파일 쓰기 없음):

```powershell
$env:PYTHONPATH = 'src'
$step35Diagnostic = @'
import gc, json, tracemalloc
from musicanote_harness import lossless_json_dag as dag
rows = [{'source_ref':'source-'+str(i),'source_note_ids':['note-'+str(i)+'-a','note-'+str(i)+'-b'],'range':{'start':{'n':i%16,'d':1},'end':{'n':i%16+1,'d':1}},'role':'candidate','padding':'common payload '*12} for i in range(1500)]
assert len(json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()) == 509385
gc.enable(); gc.collect(); tracemalloc.start()
for i in range(3):
    result = dag.preflight_json(rows)
    del result
    print(i+1,tracemalloc.get_traced_memory())
before = tracemalloc.get_traced_memory()[0]
collected = gc.collect()
print('before/after/collected',before,tracemalloc.get_traced_memory()[0],collected)
tracemalloc.stop()
'@
$step35Diagnostic | .\.venv\Scripts\python.exe -B -
```

## 산출물·revision과 독립 확인

새 출력은 정확11JSON/902,174B이며 report등록10artifact의 SHA/bytes·추가/누락0을 독립 감사했다. Report 자체SHA는 `a30dec5606d9a9599958733dbed143a3d2221dbd5486a42c940137242fd80500`다. Metadata40/전체254reads·1710/107join·5whole hold/발급0/pair0·분모와 미승격flags가 일치한다. 원archive 본문을 감사에서 다시 읽거나 재해시하지 않았다.

| 신규 동결 파일 | 실행 전/종료 후SHA256 |
|---|---|
| `src/musicanote_harness/lossless_json_dag.py` | `8d71ec368d81e10a077b19df59ea1f4406cdbfecdbdb55a358dda9dc0c559b8b` |
| `tests/test_lossless_json_dag.py` | `b48c1685fd997c11337d99d7414791e44641e37f9dd1d41ed02cadcc5a8e8d46` |
| `src/musicanote_harness/compact_source_progression_contrast.py` | `f64d33092a552be7483f297fa931e382f95abfbf266dfc7ea6749034a06a4a65` |
| `tests/test_compact_source_progression_contrast.py` | `39bd1995cd59e38fabbdbb83abf81df50c8c55ced5f725048043cb0a377baacb` |
| `tmp/compact_scoped_group_pilot_20261003.py` | `4a859d8b73ef10bb18b887d7ee0173c15c47e156ba08059016da3de96f5cac82` |
| `tests/test_compact_scoped_group_pilot_runner.py` | `1e82a37b27f47b2738da32b8cc0e8a1af9f081b99051341614ac5ae129a3e8b6` |

종료 뒤 root 확인은 선행31+신규6SHA변경0, read-only `git diff --check` exit0이며 기존tracked5변경만 유지했다. 기존LF→CRLF경고는 그대로이고 Git commit/push·권한·설정 변경0이다. 독립 최종 추가 차단0이며 ordered254parser reads는 plan path/phase/read_id/ordinal/decoded/physical과 모두 일치했다. Terminal failure=null은 scoped body-read 완료에 한정하여 root의 compact resource hold와 구별한다. Read-plan5와 root-report10 current-code 보호 목록은 서로 다르며 공유3SHA가 일치한다.

최종 root QA: 새6AST·3문서 strict UTF-8/금지 replacement/NUL 문자·158local file links·11JSON/등록10outputSHA와bytes/exact11목록·비용 산술·5whole preflight/unknown/미승격flags 모두PASS다. 문서와 JSON 유한 일관성 검사는 신규55unit tests나 화성 정확도 검사로 합산하지 않는다.

## 다음 큰 개발 단위와 완료 기준

이번에는 음악 해석을 바꾸지 않고 비교 기반을 개선했다. Exact endpoint grid는 해결됐지만 raw 검증·복사·canonicalization work와 transient memory 병목은 남았다. 다음은 다음 순서다.

1. 새 versioned 후속에서 recursive cost memo 수명을 명시적으로 끝내고 실패/hold 경로에서도 임시 자료를 정리한다. 원입력·후보와 traceback/ledger는 보존하며 성공 뒤 GC에만 의존하지 않는다.
2. 같은 exact immutable source/group binding에 한해 raw seal/검증 증명을 공유한다. JSON reload·foreign handle·변조·원 occurrence·selector·ref·null/0와 한도의 의미는 유지한다. 단순히 비용 항목을 지우거나 기존 private authority를 위조하지 않는다.
3. 기존 pair equivalence/third-candidate/타이·alias·multiplicity/unknown controls와 신규 memory-lifetime/whole-work controls를 검증한다. 소형 pass 이후 동일 원1,710/107/5 scope에서 byte/work/RSS/terminal을 재측정한다.
4. 원전체5group이 default gate를 실제 통과할 때만 새 source-once 저장·출력/중단 예산·authenticated reload/resume와 완전 비교로 넘어간다. 한 원completion의 기술 통과도 전체 코퍼스나 음악 정확도로 확대하지 않는다.

최종 화성 선택·음악적 검수·기능/cadence·전체 악보UI·구조·생성 연결은 큰 실행 순서의 후속 범위를 유지한다. Cap 증가·후보 생략·작품별 예외는 이번 hold의 해결책으로 쓰지 않는다.
