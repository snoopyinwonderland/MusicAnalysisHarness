# 단계34 — 파일별 읽기 비용과 완전한 한 원 작업의 실제 검증

작성일: 2026-10-03. 화성 분석 **개발 기록**이다. [메인 문서](../README.md), [직전 단계33](2026-10-03-shared-source-archive-bridge-and-storage.md)와 연결한다. 원XML/Core/주석과 과거 계산은 수정하지 않는다.

## 목적과 범위

배치 사이의 진행 후보 대비를 실행하기 전에, 기본 자원 한도에서 **한 원 completion의 모든 배치와 후보**를 누락 없이 읽고 연결할 수 있는지 검증한다. 특정 작품에 맞춘 화성 규칙을 추가하는 단계가 아니다. 자료의 연결·계산 계약과 음악적 정답률을 구별한다.

이전 단계의 bridge 검사는 작은 실제 XML에서 만든 저장 packet을 사용했지만 역사 ancestry는 mock이었다. 이번에는 실제 phase29 저장 자료의 원 생성 코드/입력, 부모/조상 목록, 40개 메타데이터 읽기와 원 요청 membership을 검증한다. 본문은 선택한 한 completion만 처리한다. 원 전체 분모와 생략한 범위는 계속 기록한다.

## 새 구현

- [byte-only 비용 측정](../../../src/musicanote_harness/archive_read_cost_measurement.py): raw/gzip의 모든 member를 1MiB streaming으로 읽고 EOF, 실제 physical SHA/길이, decoded 길이를 측정한다. JSON 파싱이나 parser 권한을 발급하지 않는다.
- [비용 측정 통제 검사](../../../tests/test_archive_read_cost_measurement.py): 반복 읽기, gzip 다중 member, CRC/중단, cap+1 sentinel, 미상/0, 원 분모, exact inventory와 immutable receipt 등을 검사한다.
- [한 원 작업 scoped adapter](../../../src/musicanote_harness/scoped_source_archive_pilot.py): frozen pure metadata consumer를 재사용하되 새 owned capability/reader를 사용한다. metadata 뒤 남은 body 읽기 계획이 선택한 원 completion의 **전체 ordered comparison→explanation**인지 먼저 검사한다.
- [scoped 통제 검사](../../../tests/test_scoped_source_archive_pilot.py): 선택/미선택 분모, 잘못된 body 순서·ordinal, 부분 iterator, 마지막 yield 후 중단, cap hold, 캐시 capability 재사용과 body/group 완료 구별을 검사한다.
- [실제 실행/자원 계측](../../../tmp/scoped_archive_cost_pilot_20261003.py): bootstrap discovery, 파일별 비용 측정, 별도 scoped execution과 Windows working set/peak/physical 여유를 기록한다. producer/pair 계산을 호출하지 않는다.
- [root orchestration 통제 검사](../../../tests/test_scoped_archive_cost_pilot_runner.py): bootstrap 정상/parse실패/begin실패/계획hold/비용미상중단 모두 discovery에 기록되며 실패 비용이 빠지거나 미상이0으로 변하지 않는지 검사한다.

기존 단계32/33 파일은 동결했다. 새 adapter가 과거 private admission registry에 handle을 끼워 넣거나 현재 code glob을 역사 생성 목록으로 삼지 않는다. Source에는 해당 원 source의 두 original bundle을 공유하지만, 다른 completion의 결과 entry를 빌리지 않는다.

## 예산과 완료의 구별

1. 처음 원 manifest 3개와 조상 report 4개를 명시 read plan/ledger로 읽는다. 이 discovery 비용도 준비 작업에 포함한다.
2. 원 metadata40 + 선택 body214의 254 occurrence를 하나의 측정 phase로 고정한다. 준비 예산은 기본1GiB에서 discovery 비용과 overflow 확인용1byte를 뺀다. 반복 path도 다시 charge한다.
3. 측정이 완전하고 정확한 비용표가 확보된 뒤에만, 새 **별도 execution run**에서 같은254개를 JSON으로 다시 읽는다. execution의 기본 누적1GiB를 올리지 않는다.
4. 준비와 실행 비용을 각각 표시하고 합계도 기록한다. 합계가1GiB보다 작다고 주장하거나, 한 계정을 재시작해 예산을 초기화한 것으로 취급하지 않는다. SHA 검증 physical I/O는 decoded 비용과 별도다.
5. 선택 body/terminal join 완료, source intrinsic 준비, 모든 선택 group 준비, 실제 pair 대비, full archive 완료는 각각 다른 상태다. 이미 검증된 body는 뒤의 group 자원 hold 때문에 지워지지 않지만 추가 capability/부분 group 성공 승격은 금지한다.

Source/group 기본256MiB, decoded 단일 파일256MiB, physical 단일 파일64MiB, execution cumulative1GiB를 유지한다. 부족하면 원 group/entry/pair/task 분모를 유지한 whole hold다. 임의로 후보 수를 줄이거나 cap을 높이지 않는다.

## 실제 pilot의 결과 독립 선택

원 자료: `output/fresh-source-progression-evidence-2026-10-03-r1`의 **두 등록 구간**이다. 두 곡 전체나 전체 코퍼스가 아니다. 직전 비용 관찰의 네 completion proxy는 각각1,074,193,385 / 1,216,768,356 / 946,983,892 / 1,085,323,584decoded bytes였다. 기본1GiB에 들어갈 가능성이 있는 source1/completion0만 먼저 선택했다. 음악 결과가 좋아 보이는 후보/key/prefix를 선정한 것이 아니다.

| 범위 | 원 completion | selector occurrence | batch | group | 예정 pair | 예정 nonempty block |
|---|---:|---:|---:|---:|---:|---:|
| 원 전체 | 4 | 8,050 | 504 | 20 | 1,652,640 | 570 |
| 이번 선택 | 1 | 1,710 | 107 | 5 | 291,555 | 105 |
| 본문 생략 | 3 | 6,340 | 397 | 15 | 1,361,085 | 465 |

원 전체 metadata는 검증하되, 생략한3completion 본문을 이번에 검증했다고 하지 않는다. 모든 `full_archive`, winner/accuracy/producer/UI/production/training/Gold flags는 False다. 예정 pair/block 수는 **실제 계산 수가 아니다**.

## 실제 실행 기록

실행 명령:

```powershell
$env:PYTHONPATH = 'src;tests'
.\.venv\Scripts\python.exe -B tmp/scoped_archive_cost_pilot_20261003.py --output output/scoped-source-archive-cost-pilot-2026-10-03-r1
```

새 exclusive 출력: [pilot report](../../../output/scoped-source-archive-cost-pilot-2026-10-03-r1/pilot-report.json). 원 archive 안에 파일을 쓰지 않는다. 실행 중인 코드 SHA는 고정하고 최종 report가 생성된 후에만 최종 결과를 확정한다.

실제 원 역사 metadata/원 membership40개는103.4723689초에 검증됐고, 선택 body1,710entry/107batch와 원 terminal join은199.8731838초에 완료됐다. Source intrinsic 준비 이후5group 전체 사전 비용을 확인하고 whole resource hold로 종료했다. 총242.98192140005995초이며 PowerShell tool 종료코드는1이다(실행기 `main`은 의도한 resource hold에서2를 반환하며 native 비0을 PowerShell이1로 감쌌다). 이를 성공 exit0으로 표기하지 않는다. Body가 틀렸다는 실패가 아니라 다음 group 비교의 자원 한도 때문에 보류된 상태다.

## 검사와 발견/교정

- Author 측정21개/0.359초 PASS. Scoped 최종14개/72.605초 PASS. 작은 ancestry mock 검사는 실제40read 역사 검증으로 확대하지 않는다.
- Root 최종 측정21+scoped14의 **35개/74.403초 PASS**. 초기 root33개/65.591초는 중복 재검사다. 별도 기존 cumulative reader24개/0.366초 PASS이며 도구가 stdout 일부를 잘랐다(종료 요약/exit0 확인).
- 종료 뒤 root runner5개/0.085초 PASS를 추가해 **신규 고유40개**다. 기존 reader24개는 별도 회귀 검사다. Final scoped/measurement module SHA는 실제 r1 실행과 최종35개 검사에서 동일하다. Root runner 실패 경로의 마지막 교정은 실제 r1 실행 뒤이며, 그 교정은5개 소형 검사로 검증했다. 실제 corpus를 재실행하지 않았다.
- Scoped 초기12검사의10PASS+1FAIL+1ERROR는 invalid index가 API 전에 fixture를 참조한 문제와 서로 같은 content-addressed body를 다른 body라고 가정한 문제였다. 실제로 다른 registered metadata body와 직접 잘못된 선택 선언으로 교정했다. 중간3검사2PASS+1FAIL, 후속2검사15.509초PASS를 최종 고유 수에 더하지 않는다.
- 실제 runner의 iterator 반환은 한 entry가 아니라 한 **batch packet**이다. entry수는 packet의 `entries` 길이를 합산하고 batch수를 별도 기록하도록 실행 전에 교정했다. Whole hold의 dict plan과 owned plan을 구별하고 measurement begin 실패 receipt/종료 비용 계상을 보완했다.
- 독립 감사에서 bootstrap 실패 ledger가 discovery append 전에 빠질 수 있는 generic 오류 경로를 발견했다. r1의 두 bootstrap은 정상 종료하여 비용이 모두 기록되었으므로 이 실패 전용 문제는 r1 정상 비용을 바꾸지 않는다. 종료 뒤 `finally`에서 ledger를 먼저 discovery에 추가·저장하도록 교정했다. 계획 단계의 decode0/physical guard, begin 실패 snapshot, unconfirmed interrupt의null을 구별했다. 독립 최종 차분 감사 추가 차단0이다.
- 두 root 진단 one-liner는 각각 닫는 괄호와 read-plan dictionary field 추정 오류로 실패했다. 실제 실행이나 자료를 바꾸지 않았고, 최종 compact 진단 명령에서 올바른 키/산술을 확인했다. JSON 큰 dump의 tool truncation을 개별 artifact 검증이나 검사 수로 확대하지 않는다.

## 최종 관찰과 다음 단계

### 정확한 읽기 비용

| 구분 | occurrence | decoded bytes | physical payload 읽기 | SHA 검증 physical I/O |
|---|---:|---:|---:|---:|
| 준비: manifest/ancestor discovery | 7 | 1,837,094 | 1,837,094 | 5,513,990,435 |
| 준비: metadata40+선택body214 측정 | 254 | 950,488,899 | 83,105,354 | 5,845,579,447 |
| 별도 실행: 같은254개 JSON 파싱 | 254 | 950,488,899 | 83,105,354 | 5,932,412,271 |

Metadata40은442,194,447bytes, 선택 body214는508,294,452bytes다. 준비 전체952,325,993bytes, 별도 execution950,488,899bytes, 두 run 합계1,902,814,892bytes/515read occurrence다. SHA 검증 physical I/O 합계17,291,982,153bytes는 decoded budget 밖이지만 실제 읽기 비용이며 표에서 숨기지 않는다. 외부 소형 검사/읽기 전용 감사의 I/O까지 이 pilot 계정으로 측정한 것은 아니다.

R1 report의 `repeated_preparation_occurrences=0`은 당시 구현이 **측정 phase 내부**의 반복만 센 필드다. 그254개는 unique254이나 discovery7개를 측정에서 다시 읽으므로 준비 전체 반복은7개다. 최종 runner는 `repeated_measurement_occurrences=0`, `repeated_preparation_occurrences=7`로 구별했다. r1 출력은 고치거나 덮어쓰지 않았다.

### Source/group 상계와 메모리

Source: original bundle2, catalog136, origin7,285, sounding fact53, key5, input82,392,179B, encoded source 상계82,408,563B, work상계659,616,216. 기본한도를 통과하여 owned source를 준비했다. Encoded 상계는 RSS가 아니다.

5group 모두 원342entry/58,311pair/21nonempty block을 유지한다. 각 vector cell 상계16,141,032 > default10,000,000, work상계5,552,879,397 > default1,000,000,000이다.

| original group index | local input JSON bytes | catalog byte 상계 |
|---:|---:|---:|
| 0 | 101,325,836 | 1,662,147,732 |
| 1 | 101,471,305 | 1,663,311,484 |
| 2 | 101,553,125 | 1,663,966,044 |
| 3 | 101,763,509 | 1,665,649,116 |
| 4 | 97,068,884 | 1,628,092,116 |

모두 기본 catalog256MiB보다 크다. 세 가지 이유(`whole_vector_cells_exceeds_limit_no_prefix`, `whole_work_exceeds_limit_no_prefix`, `whole_catalog_bytes_exceeds_limit_no_prefix`)로 전체선택 group을 보류했으며 preparedgroup0·pair계산0이다. 근거가 틀리다는 뜻이나 음악 정답률이 아니다. Body failure는null, body/terminal join완료True, selected source+모든group완료False, fullarchiveFalse다.

Actual process peak working set3,233,386,496B(약3.01GiB), 최저 **관측** physical 여유11,533,078,528B다. Source/group JSON 상계를 memory 측정으로 바꾸거나 available memory의 하한을 보장하지 않는다. 약30초 heartbeat와 milestone의 process peak를 기록했으며 메모리 경쟁 작업 영향도 있을 수 있다.

### 출력/보존과 실행 revision

새 출력11파일/4,502,225physical bytes다. Report의 등록10artifact와 실제 bytes/SHA가 모두 일치하며, exact 목록은10개+`pilot-report.json`이다. Report는 자기 자신을 artifact hash에 넣어 자기 인증하지 않는다. 독립 진단의 report SHA:

`858788a3279c926b0fc1d7293b5dae08016d1d61f15e985a3adef9db2b6fa338` (403,981bytes).

실제 r1 runner SHA는 `87c4977d09ddbffe7282cbd8880f6d2a46d1a41925091355ca77522045ea3a5f`다. 종료 뒤 bootstrap 실패/반복 field를 교정한 최종 runner SHA는 `a52e3088fc312cc9baa4e482bf299c2c94ecb533d479960c58210f91611b1b2c`다. 정상 bootstrap/body 실제 관찰은 r1 기준이며, 최종 runner 전체 corpus 재실행을 주장하지 않는다. `root_current_code_changed=[]`는 r1 실행 시작→종료 사이의 상태다.

| 최종 새 파일 | SHA256 |
|---|---|
| archive_read_cost_measurement.py | `b693ecfe21b7892007f3fc6ed678ede79b62c9cef6418b43c5b9ad5c28c384bf` |
| test_archive_read_cost_measurement.py | `6db23dd1cdd1fb17bd3d05f20c2549cc9cab0aa570b379c6b60015eafa613c5a` |
| scoped_source_archive_pilot.py | `d325bbb8ea414895f5972c44fdef5a1258bd74e0600cd5834bfd43fd760a772a` |
| test_scoped_source_archive_pilot.py | `988e8c733b68f2abc877751330a61bdc972f0c25e1259568e4bea9a0c45aacd6` |
| scoped_archive_cost_pilot_20261003.py | `a52e3088fc312cc9baa4e482bf299c2c94ecb533d479960c58210f91611b1b2c` |
| test_scoped_archive_cost_pilot_runner.py | `edad8acce1cf2911677fa0f24a4936d7d58fdacac5bf61fe6ef2eb2aae3be681` |

선행25개 source/test/receipt SHA 변경0이며 별개 tracked5 사용자수정·원XML/Core/주석/과거 출력은 보존한다. Git commit/push·권한/설정 변경0이다. 최종 새6AST/9strict UTF-8 text/162local Markdown link/11artifact JSON·등록10output physical SHA/bytes·exact11목록·합계/완료flag QA 오류0이다. Read-only `git diff --check` exit0이며 기존 tracked5의 LF→CRLF 경고만 유지했다. Root 최종6새파일 SHA는 위 표와 일치한다.

### 다음 큰 개발 단위

1. **Whole-group compact local codec**: 원342개 모두를 보존하면서 source에 이미 있는 같은 음표·철자·타이·성부·시간·원 기록 참조를 반복 저장하지 않는다. Local은 원 path identity와 결과가 재구성 가능한 필요한 facet만 갖고, 원 pair 설명의 exact equivalence를 검사한다.
2. **Exact rational endpoint union**: 모든 path의 시간 atom을 단순 더한47,196 상계를 실제 공통 endpoint union으로 계산한다. 모든 원 span `[start,end)`, key/bundle/completion, rational 음가와 attack/sustain/multiplicity를 유지한다. Endpoint 계산 자체도 비용에 넣고, bounds가 커지면 whole hold한다.
3. 같은 원전체 group을 default 한도에서 다시 preflight하고, 통과한 경우에만 첫/max-cost bounded block의 실제시간/RSS/output reserve를 계측한다. 새 compact codec을 old group cap 우회 권한으로 취급하지 않는다. 이후 전체 pair 대비/중단 저장을 판단한다.

Authenticated reload/resume, 원4completion 전량 대비와 source-once corpus 저장, winner/새 엔진 UI/구조/생성 연결은 별도다. 화성 판단 정확도가 이번에 올라갔다고 주장하지 않는다. 모든 후보의 원음표·타이·성부·유리수 정보와 전체 원 분모를 보존한 채 **배치 밖 진행 후보 대비**의 실제 비용을 줄일 수 있게 하는 단계다.
