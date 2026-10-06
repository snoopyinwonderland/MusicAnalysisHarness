# 단계29 — 자원 사전 점검과 실제 원자료 replay 완료

2026-10-03. [실행기 구현·저장 검사](2026-10-03-replay-implementation-scope-and-progress.md)의 다음 개발 단위다. 사용자는 “다음은 자원 사전 점검 후 실제8,050요청 계산”이라는 안내에 “네”라고 승인했다. 원본·기존 엔진·과거 결과는 유지한다. 사전 점검과 전체 제출 계산, 음악적 정확도 및 UI 적용은 별개다.

## 상태와 범위

실제 자원 pilot는 **384.5278678999748초/exit0**로 완료했다. 이어 동일한 사전 정책의 **원4completion/8,050요청/504batch 전체 실제 계산도5074.453444299987초/exit0로 완료**했다. 두 등록 구간의 모든 제출 위치가 계산·저장됐으며 전체 작업 보류·누락·미완료·부분 파일은0이다. 최종1025파일/183,060,358bytes와 참조·저장 해시 및 원음가 계정을 검사했다. 이는 화성 정답률·최종 진행 선택·악보 UI 적용 완료가 아니다. 아래 pilot와 실행 중 검수는 당시의 범위로 보존하고, 전체 종료 검수는 마지막 절에 구별한다.

Pilot의8batch/128selector occurrence는 별도의 자원 표본이다. 전체8,050에128을 더하지 않는다. Pilot는 입력을 읽고 fresh native/role 계산의 시간·메모리·JSON/gzip bytes를 관찰했으며 계산 본문이나 원자료를 저장/변경하지 않았다. 원본·기존 엔진·과거 결과는 전체 실행에서도 유지했다.

원 stage28의 두 **등록 구간**과 네 원 completion이 대상이다. 소나타2,315selector와 사중주1,710selector를 각각 no-link/원 greedy-link 조건에서 요청하므로 전체8,050발생이다. 두 전곡이나8,050곡이 아니다. 원322문맥/1,013raw lanes 중 선택2/7·미실행320/1,006과 등록pool5를 유지한다.

원 greedy-link는 `bounded_same_raw_lane_greedy_technical_probe`인 자동 생성 성부 연결 후보다. 실제 원음표 사이의 link를 사용하지만 사람 검수로 확정된 성부 분석/정답 completion이라고 주장하지 않는다. 두 원 가정을 별도로 보존하고, 그 아래의 조건부 지원과 음악적 채택을 구별한다.

## 결과에 독립적인 표본 선정

[보존한 resource probe](../../../tmp/source_progression_resource_probe_20261003.py)는 전체 plan을 먼저 계산한다. Source별 첫 batch와 `charged_work`·`native_query_work`·`role_query_work` 각각 최대인 batch를 고른다. 동률은 원순서에서 가장 이른 위치를 택하고 중복 위치는 한 번만 측정한다. 같은 selector 범위를 두 원 completion에 모두 적용한다. 분석 True/False·해결·credit·원주석의 정답을 선정 기준으로 사용하지 않는다.

첫 batch는 controls 중심이므로 그것만으로 추가1/2/3slot 경로의 비용을 대표했다고 주장할 수 없다. 두 source의 모든 key·origin·transition 가정과 원 selector 순서는 유지하며 subset를 새 전체 요청으로 바꾸거나 archived ID로 native 권한을 사칭하지 않는다.

## 측정과 보존 계약

- Direct admission/전체 numerical plan → 사전 표본 고정 → source별 fresh `native.prepare_lattice(full_IR, scope)` → 전체 fresh lattice/provenance와 원본문 exact equality → 원 completion별 새 bundle → 선택 batch의 native 비교/role prepare/role explain → frozen runner의 `_batch` 검증 → JSON/gzip 크기 측정 순서다.
- `role.prepare`의 native 재인증 시간도 별도로 측정한다. 전체 IR/scope·원 lane link·source-note ID/음가/타이/actual attack·rational account를 유지한다. 저장 artifact를 live native session으로 재사용하지 않는다.
- Probe는 **whole stream/terminal completion이 아닌 public native/role API의 독립 자원 표본**이다. 계산 body와 winner·confidence·최종 화성/NCT/key/cadence·학습/Gold·UI·구조·생성은 저장/승격하지 않는다.
- 입력·현재 코드·probe의 SHA closure와 원6/7/7/148 부모 목록을 전후 확인한다. 과거 code 목록에 신규 파일을 소급 추가하지 않는다.
- Windows `GlobalMemoryStatusEx`와 현재 probe process의 `GetProcessMemoryInfo`를 이용해 available physical memory·현재/peak working set·private bytes를 관찰한다. 약30초마다 heartbeat를 출력한다. WMI의 read-only 조회는 access denied였으며 앱 설정/권한을 바꾸지 않고 접근 가능한 현재 process 계측을 사용했다.
- 사전 disk free는26,732,724,224bytes, 총 physical memory33,444,220,928bytes이며 첫 probe 시작의 available physical은15,997,345,792bytes다. 시점별 변동 수치이며 프로그램에 보장되는 전용 자원이 아니다.
- 전체 실행의 기본 총2GiB/decoded record128MiB/manifest16MiB 저장 한도는 유지한다. 128MiB는 **본문 생성 후의 저장 검사**이지 producer RSS 상한이 아니다. 선택 표본의 측정으로 모든504batch의 시간/RSS/출력 상한을 증명할 수 없다.

Pilot 재현 명령은 다음과 같다. 아래 resource probe와 후속 full replay 명령을 구별한다.

```powershell
$env:PYTHONPATH = 'src'
./.venv/Scripts/python.exe -B tmp/source_progression_resource_probe_20261003.py --parent 'output/source-grounded-progression-proposals-2026-10-02-r1'
```

## 검사 및 미해결 사항

Windows 메모리 helper import와 순수 표본 선정 tie/dedup control은 PASS이며 producer0이었다. 독립 정적 감사에서도 전체 계획·원 completion·권한과 저장 상한을 확인했고 기존 runner/core SHA는 불변이다. 이는 실제 음악 분석 검사 수로 더하지 않는다.

이 절은 pilot 착수 당시의 검사 범위다. Pilot 실측과 후속 actual replay 종료 결과는 아래에 기록했다. Bundle 등록/직렬화 비용과 초기 등록/GC 비용을 pilot batch 본문 평균에 포함했다고 주장하지 않는다. 전체 경쟁 비교와 음악적 악보 검수는 후속 단계다.

## Pilot 실측 결과

[제한 계측 receipt](../../../reports/source-progression-resource-preflight-2026-10-03-r1.json)는 root가 tool stdout의 개별 표본8개와 보이는 마지막 보존/count/time 필드에서 정리한 관찰 기록이다. 마지막 tool 출력 일부가 잘려 원stdout 전체를 보관한 것으로 가장하지 않는다. Sealed analysis, 전체 완료 record, 음악 정답 dataset이 아니다. Probe 원코드와 selector slice/digest로 재현할 수 있다.

각 source의 세 비용 최대 위치가 모두 **batch2/[32,48)**였으므로 first batch0/[0,16)와 두 위치를 측정했다. 전체 preplan은504batch·8,050selector·원4completion이며 원 source별 계획145/107batch·2,315/1,710selector를 유지했다. 두 원 completion에 동일한 위치를 적용했다.

| Source | Completion | Batch / selector 범위 | 측정 batch 처리 초 | Comparison+explanation gzip bytes |
|---|---|---|---:|---:|
| Sonata | no-link | 0 / `[0,16)` | 12.1722304 | 206,246 |
| Sonata | no-link | 2 / `[32,48)` | 11.2970932 | 372,849 |
| Sonata | 원 greedy | 0 / `[0,16)` | 9.8219314 | 251,546 |
| Sonata | 원 greedy | 2 / `[32,48)` | 11.4001098 | 422,190 |
| Quartet | no-link | 0 / `[0,16)` | 8.8664562 | 238,304 |
| Quartet | no-link | 2 / `[32,48)` | 10.6412409 | 423,233 |
| Quartet | 원 greedy | 0 / `[0,16)` | 8.8544149 | 297,436 |
| Quartet | 원 greedy | 2 / `[32,48)` | 10.8983546 | 482,941 |

Batch 처리 초는 native 비교·role 준비(내부 native 재인증 포함)·role 설명·intrinsic validation·두 body JSON/gzip 시간의 합이다. Bundle 등록·초기 준비·GC·파일 저장/검수 비용은 포함하지 않는다. First batch는1slot10/2slot6, max batch는3slot16이었다. 각 측정의 native/role status는 computed이며 path16/16으로 요청16개와 일치했다. 보류된 저비용 표본을 성공 크기/시간으로 추정한 것이 아니다.

Admission+전체 numerical planning은81.91356340004131초, source별 fresh 준비81.33389649994206/91.96139719989151초다. 두 fresh lattice는 decoded103,401,361/81,201,706bytes·gzip4,094,861/3,300,575bytes이며 전체 archived본문/provenance와 정확히 일치했다. 최대 individual comparison decoded5,083,361bytes, explanation2,388,367bytes, 표본8쌍 gzip 합2,694,745bytes다. Peak working set1,947,295,744bytes(약1.81GiB), 관측 메모리 여유 약14~16GB에서 계산했다. 실제 측정이지 hard RSS 한도나 전체 출력 상한의 증명은 아니다.

Reader23파일/254,888,715decoded bytes·보호4,789경로 SHA와 exact6/7/7/148inventory의 변화0이다. 보호4,789는 기존 closure에 현재 새 core/runner/test 및 probe를 추가한 이번 범위이며 과거4,784creation 목록을 소급 수정한 숫자가 아니다. 전체 completed job/terminal은0이고 원8,050분모는 유지했다. Unit test/곡/음악 정답 수와 합산하지 않는다.

### 동결과 측정 한계

- Probe SHA: `49b76bc281e0a7a7d87b145b46b2cca6bd133cd1c1864c4ea15d2105934c0206`.
- Compiled receipt SHA: `a331eeb124d4941100662d1e4c0ef4e0a4b69bc01eae25cf97f8419a5acf2afc`.
- 기존 runner/core 및 두 test의 SHA는 [직전 정본](2026-10-03-replay-implementation-scope-and-progress.md)과 같다.
- 독립 정적 검토의 향후 권고는 admission 후 fresh 준비 직전 headroom 추가 검사, bundle 등록/압축 비용 계측, held sample의 명시 제외, 출력 thread lock이다. 이번 모든 sample은 정상 computed16/16였고 peak/available-memory heartbeat를 관찰했다. 종료 후 원 probe를 소급 고쳐 이미 실행한 버전이라고 만들지 않았다.

독립 계측 receipt 감사는103확인/0.6266386초 PASS다. Saved proposal의 실제 selector slice/digest/slot 수·원 completion/context와8개 위치,128 native/role path·비용/시간/bytes 산술을 대조했다. Body 합decoded39,607,004/gzip2,694,745bytes, 두 lattice 합decoded184,603,067/gzip7,395,436bytes다. 측정 subtotal262.9941582초와 나머지121.5337097초(입력/계획/bundle/GC/보존 등 미분해 비용)를 구별했다. Producer/cold 재실행·음악 정답 검수·파일 편집은 없으며103을 unit test 수로 합산하지 않는다.

특히 pilot는 public native 준비를 직접 호출했고 전체 runner는 bridge의 proposal/binding freeze·원 전체 mapping 검증과 writer를 추가한다. 따라서 pilot peak1.81GiB는 full bridge/stream/writer peak의 실측이 아니다. 실제 전체 실행의 heartbeat에서 관측한 더 큰 peak와 여유를 별도로 기록한다.

## 전체 실제 실행 — 착수 기록

메모리·disk headroom과128MiB decoded/총2GiB 상한에 대해 표본에서 차단 요인은 발견하지 못했다. 같은 전체 분모/원순서/조건/비용 한도인 batch16·role3B·native2M·replay1T·geometry100K를 그대로 사용하여 **원4completion의 모든8,050요청**을 실행하기로 했다. 표본당 약9~12초는 관측 범위이고 전체504batch가1시간 이상 걸릴 수 있다는 사전 안내를 했다. 결과에 따라 지원 조건이나 음악 threshold를 바꾸지 않았다.

[관찰 wrapper](../../../tmp/run_source_progression_replay_monitored_20261003.py)는 frozen runner의 `run()`을 수정 없이 호출한다. Detached progress event·현재 process 메모리·약30초 heartbeat를 단일 lock으로 출력한다. Heap/body/입력·claim은 바꾸지 않는다. Wrapper SHA는 `fb1dba8500137e75dbba8534b0b395f737a9aa233fe29b0cc8e813794163ae46`이며 연구 관찰용이다.

```powershell
$env:PYTHONPATH = 'src'
./.venv/Scripts/python.exe -B tmp/run_source_progression_replay_monitored_20261003.py --parent 'output/source-grounded-progression-proposals-2026-10-02-r1' --output 'output/fresh-source-progression-evidence-2026-10-03-r1'
```

이번 새 exclusive 출력은 `output/fresh-source-progression-evidence-2026-10-03-r1/`이다. Admission/full preplan은46.86386510008015초에서2source/4job/8,050selector/504batch·368,794,524,148logical units를 확인했고 최초 run-plan/plans를 저장했다. 이는 착수 시점의 snapshot이며 당시 저장 prefix를 전체 완료로 승격하지 않았다. 아래 실행 중 감사도 각 검사 당시 닫힌 파일만 대상으로 했다. 전체 output SHA/inventory·실제 모든 분모·실패/보류·원자료 보호와 종료 검수는 마지막 절에 기록한다. 전체 경쟁 비교/policy/winner·음악 정답률·악보 UI·구조·생성·Git은 별도 단계다.

### 실행 중 닫힌 두 배치의 원음표 연결 감사

첫 Sonata/no-link 작업의 이미 저장이 끝난 batch0·2만 독립 읽기 전용 검수했다. Comparison `fmilcompare_4b319b978d0c71b01ae3581f`/`fmilcompare_86b947cb03bb6c190a251214`와 explanation `fmnrole_233416f18ee827930ff7723c`/`fmnrole_1427d2a8241cad171bc1f9ef` 두 쌍이다. 아직 쓰고 있는 파일·다른 batch·없는 terminal/전체 completion은 검사하지 않았다.

최종78,605 유한 산술/참조 확인·불일치0/4.3720723001초 PASS다. 원 selector slice `[0,16)`/`[32,48)`·동일 fresh lattice/key/origin/no-link bundle·account pointer, 32path/70slot/38internal transition/754profile row/512cell/102boundary/328clause를 대조했다. 읽은11파일의 크기/SHA 전후 변화0이며 producer/replay/cache 재실행·파일 편집0이다. 이 수는 unit test/음악 정답/전체 완료 수가 아니다.

분석 scope는 `[49,61)`·23sound/24source-note refs이며 모든 path의 원 음가 계정 `85/2` quarter-note-time이 보존된다. 실제 `sound_cae7b39ad108`/`tie_8f5b04834d7b`는 D♭5 `note_2d60aad9c21b`(12마디, onset45, duration4, tie start)→`note_b1e7cd2305c0`(13마디, onset49, duration3/2, tie stop)다. Full sounding span `[45,101/2)`와 observed span `[49,101/2)`를 구별하며 49의 tie stop을 새 attack으로 만들지 않는다. Scope 이전의 before 관측은 빈 배열이지만 full continuing refs/source snapshots에는 과거 onset45와 전체 타이가 남는다.

이번 no-link의328조건부 clause는 failed/credit0이다. 실제 성부 연결을 제공하지 않은 조건에서의 전제 불충족이며 최종 NCT/화음/Cadence 기각으로 읽지 않는다. Greedy 조건이나 다른 작업의 결과를 이 표본과 합쳐 지원으로 만들지 않는다.

감사기 초기 `KeyError: 'lane'`는 `raw_lanes` 행에 lane 필드가 있다고 가정한 오류이며 `lane_inventory[*].lane`으로 교정했다. 이후71,327확인 중102→32불일치도 제품 결함이 아니라 감사기의 기대 규약을 바로잡은 이력이다. Sound 원순서 대신 API의 sound-ref 정렬, full span 대신 horizon의 observed span으로 before/at inventory를 대조했다. 최종78,605PASS와 초기 실패/재검사 수를 합산하지 않는다. Carry 보존 검사가 추가되어 최종 확인 수가 증가했다. 코드·입력·결과는 수정하지 않았다.

두 쌍의 압축 파일 바이트 SHA256은 다음과 같다. 모두 이번 exclusive 출력 아래의 경로다.

| 상대 경로 | SHA256 |
|---|---|
| `comparisons/fmilcompare_4b319b978d0c71b01ae3581f.json.gz` | `39d2ea5d9294185d24b7b1ac86c0fead05fa85ecf95f3e8800f096e02ab9b3c4` |
| `explanations/fmnrole_233416f18ee827930ff7723c.json.gz` | `d1967f6fac2d9295acbf3022a09a66b4784af47ffd99b3cf1e82976f88a240b0` |
| `comparisons/fmilcompare_86b947cb03bb6c190a251214.json.gz` | `4b915dc4a4b97534f889f0b8b836a7c79cda426b2c31ef13e99f2a4b5fea6745` |
| `explanations/fmnrole_1427d2a8241cad171bc1f9ef.json.gz` | `d2b9380e7439d9b841d6a6fb5c4ef4f21f922d12cb899de4a6642adaeae5c01c` |

보존 확인11파일은 위4개와 현재 fresh lattice/bundle/binding/run-plan4개, 원 expanded scope·candidate IR·source-grounded proposal3개다. Exact scope `fmes_f676809634ab4fb9acf34b03`, lattice `fmilat_a5daac1f9d08a81d4995b0b2`, bundle `fmilbundle_32b745ced2a06ef628660a12`, binding `npsrebind_ba24f2977ad38a9715506779`, proposal `npsprop_7a680abd13e7a30354fe49b5`에 한정했다. 이는 전체 저장 inventory/입력 closure의 종료 검수와 별개다.

### 첫 원 completion 완료와 같은 요청의 실제 성부 연결 대조

첫 Sonata/no-link job은 observer elapsed1,660.2500814초에서 `computed_native_role_source_requests_not_selected`로 끝났다. 원2,315selector/145contiguous batch의 정확한 `[0,2315)` coverage, native 호출290(독립 비교와 role 내부 재인증)·role prepare/explain145개씩, computed internal transition3,150=명시370+None2,780, native/role 원음가 보존2,315개씩을 저장 terminal과 원 proposal/plan에서 확인했다. 이는 전체145본문을 별도로 다시 검수한 수가 아니다. 전체 no-link terminal에는 supported clause630·conditional credit1,260quarter-note selector-occurrence 합계가 있어, 위 batch0·2의328clause failed/credit0을 전체 job에 일반화하지 않는다. Slot 내부 geometry로 설명 가능한 경우와 외부 성부 link가 필요한 경우를 구별한다.

이어 같은 원 selector 범위의 greedy batch0·2(각16path)를 읽기 전용 대조했다. Batch0의268clause는 supported10/failed200/unassessed58, batch2의488clause는36/356/96이다. Original profiles/whole raw account는 같은 selector의 no-link와 동일하며 모든 path85/2가 보존된다. Separate union credit의 selector-occurrence 합계는5/3와12이며 다른 조건과 합쳐 하나의 음악 정답/전체 점수로 만들지 않는다. 원18link·동일 bundle/ref·source-note/tie/full span·clipped credit/여섯 category union을 대조했다.

실제 batch2/path9의13마디 G4 `[49,53)`→14마디 A♭4 `[53,57)`는 주어진 성부 link 아래 leading motion=true이지만 seventh motion=false라서 whole ordinary=false/joint=false를 유지한다. Leading 관련 NCT clip도 빈 배열이며 부분 해결을 전체 Secondary/NCT/화음 정답으로 승격하지 않는다. 14마디 C5→B4→C5의 조건부 neighbor,14→15마디 C5 재발음→B♭4의 조건부 suspension도 원음표와 실제 link에 연결되는 지원 사례다. 이 명칭은 해당 가정 아래의 clause 설명이며 최종 채택 라벨이 아니다.

후속 독립 감사는9,618유한 확인/불일치0/4.4844681000초·읽은17파일 크기/SHA 전후 변화0이다. 첫 terminal/분모 산술과 두 greedy 표본만 검수했고 그 밖의 body·둘째 job terminal/전체8,050완료를 검사한 것은 아니다. Producer/replay/파일편집0이며 앞선78,605감사 또는 unit test 수와 합산하지 않는다.

Neighbor의 실제 C5→B4→C5 음가는1/6·1/6·1이며 두 원 link를 보존한다. Suspension-like C5→C5→B♭4는1·1·2이고 carry kind는`reattack`이다. 같은 높이의 재발음을 타이로 바꾸지 않는다. Leading 부분 사례의 exact path는 `fmilpath_115de5f51ea246a29efb1eb3`이다.

후속 확인의 압축 바이트 SHA256(같은 출력 기준)은 다음과 같다.

| 상대 경로 | SHA256 |
|---|---|
| `jobs/npsreplayjob_232ab438cb454aadf55e1481.json.gz` | `05a1067dc948f53deb603c7b12385d7de467a6af8201c1b96bc8a0dccbe9c622` |
| `comparisons/fmilcompare_32150b26777e6de97fb18e50.json.gz` | `79b8307099ee10cbf999fec5224cf50aabe0f11218bfcd1bfb19192c85a265d8` |
| `explanations/fmnrole_3e436c3ad8531fd81be03d6a.json.gz` | `f15e06a1b2360271539ee3f7067b1cd67129e3fac44d0ce03babc67f309613e5` |
| `comparisons/fmilcompare_813d0fb1fa80da576b050289.json.gz` | `1a5c8fdd5f5575a518855367644e7a709e7741a5773a72a02a90d56adf77cde4` |
| `explanations/fmnrole_ba034cd22dfe170efe2c5390.json.gz` | `1bc1719d4589fc13ba42a94e9b72860f277793b71371c8a5786e2ed712bbadc3` |
| `bundles/fmilbundle_c637f032bcb0e8fed00fc3b3.json.gz` | `f7a1e264150899e33752f954aa8e272c3c70a9232ff90e71d68270f19699d5f7` |
| `plans/npsreplayplan_85f6b9c37a449e5a4b41b921.json.gz` | `3040d80dc9046505bc9eaa00d62f2d71f407c945a10cec151698453cf4a1ed7a` |

### Quartet의 다성 원자료 연결 감사

두 번째 source의 fresh 준비는elapsed3,190.4115440초에 완료됐다. Source별 job index는0/1로 재시작하며 원 네 요청 identity와 source index를 함께 사용한다. 첫 Quartet/no-link 작업의 닫힌 batch0·2만 검수했고 현재 writer 파일이나 전체 작업을 검사하지 않았다.

최종164,050유한 확인/불일치0/3.6907966000초·읽은11파일 크기/SHA 전후 변화0이다. 원 proposal slice `[0,16)`/`[32,48)`·source별 plan1,710/107·fresh binding/scope/bundle/원IR 참조,32path/1,696profile row/512cell/102boundary/268clause를 대조했다. Source는53sound/53source-note/tie0이며 각 native/role path의 raw53/2와 여섯 category 합계가 보존된다. Literal raw lane별 관측 음가 합계 `8+8+8+5/2=53/2`와도 일치한다. 신규 producer/재계산/파일편집0이며 이번 감사는 처음부터 불일치0이었다. 앞선 Sonata 감사기 교정 이력이나 unit test 수와 합산하지 않는다.

132마디의 실제 동시 관측은 아래와 같다. 각 음표 duration은1/2quarter다. 최저음 변화는 관측이며 structural bass/화음 전위 확정이 아니다.

| Onset | 네 raw lane의 동시 음표 | 관측 최저음 |
|---|---|---|
| 262 | C3·A♭3·E♭5·E♭6 | C3 / `sound_fe4de7d72284` |
| 525/2 | B♭2·A♭3·D♭5·F6 | B♭2 / `sound_8c0d684da86e` |

두 표본의268clause는 no-link 가정 아래 failed/known credit0이며 전역 NCT 부재·화음 기각·음악 정답률을 뜻하지 않는다. 다른 batch와 Quartet의 terminal/전체 completion 완료 여부는 이 감사의 범위가 아니다.

두 쌍의 압축 바이트 SHA256(같은 새 출력 기준)은 다음과 같다.

| 상대 경로 | SHA256 |
|---|---|
| `comparisons/fmilcompare_ce7d1f096bc9f6296476d3f7.json.gz` | `19f4b7e3d0d22098240c648d2693a0ece0dd7fbc7f2207445bf8e9a05da0b73c` |
| `explanations/fmnrole_dcdbf3b0eb7ffe5ed4c9e561.json.gz` | `bd4dc03ff63e5af7fc31b8a5046ef180ae5805ff3bdf99fc643cf74c4574b834` |
| `comparisons/fmilcompare_2472e00207d80b820580b4e3.json.gz` | `8c206cb7e2ea8674618723e25ad973030de08babd15fbed0fa78f59cdca02b48` |
| `explanations/fmnrole_aeca75c5a79a1361423ad79b.json.gz` | `deed8f81e0fc281e1f7a7da900df692e54f01b94b89986e60dce91fb89ac4022` |

### Source0의 두 completion 저장 구조 전수 대조

닫힌 두 Sonata job의580comparison/explanation body를 한 배치씩 읽어 top seal/ref·원 selector 순서·source/key/origin/partition/vector/completion join·저장 raw-account Fraction 합계·terminal 산술을 대조했다. 최종85,289유한 확인/오류0/60.1126766초, 읽은594고정 파일 전후 SHA 변화0·누적 decoded JSON1,435,867,593bytes다. 실제 화성/NCT/role supplier predicate나 producer는 재실행하지 않았으며 unit test/음악 정답 검수 수가 아니다.

각 job은2,315native/role paths·145contiguous batch·마지막11요청이며 key5개당463씩·누락/반복/hold0이다. Source0합계4,630요청/290batch·native comparison 호출580·role prepare/explain290개씩, fresh binding 준비1과 별도 두 bundle을 보존했다. 저장 설명 credit1260/1 및16915/6(selector-occurrence 합계), unknown/uncomputed credit0, ordinary/joint true0/0 및20/8을 재합산해 일치했지만 조건부 지원을 음악적 정답으로 인증하지 않는다. 당시 범위 밖3,420요청/214batch/2job와 원전체8,050/504/4분모는 그대로다.

No-link terminal SHA는위의 `05a1067d…`와 같고 greedy terminal `npsreplayjob_4f41a094…`의 압축 SHA는 `42fe2d7963e5a3265a22df038a8a20c67ffbda1a35fad34a820ca5ac69e593de`다. Run-plan의 registered creation/code와 직접 대조한 경로는7개에 한정했으며 전체4,788보호 closure를 다시 검사한 것으로 보고하지 않는다. 나머지는 읽은 파일의 전후 보존 검사다.

준비 감사기의 `planned_work`/실제 `planned_query_work` KeyError(1.5284093초)와 context-index의 자료형 탐색 오인은 감사기 기대를 교정한 이력이다. 제품/자료 오류가 아니며 최종 PASS에 재검사/초기 실패 수를 더하지 않았다. 전체 report/index는 아직 생성되지 않아 이 감사에서 읽거나 완료를 선언하지 않았다.

### Quartet의 같은 요청/성부 연결 후보 대조

Quartet greedy의 닫힌 batch0·2를 같은 no-link selector에 독립 대조했다. 신규11,880유한 확인/불일치0/3.7585691001초·읽은16파일 크기/SHA 전후 변화0이며 기존 no-link164,050확인은 합산하지 않는다. 실제20link의 같은 raw lane·release=attack·범위 내 조건, 원profile/raw account/key/origin/partition,32path의raw53/2·여섯 category·conditional clip union이 일치한다. 별도 작은 저장 spot2파일도 SHA 변화0이지만 전수 predicate 검사로 합산하지 않는다.

Greedy batch0의324clause는 supported5/failed307/unassessed12·credit5/2, batch2의520clause는8/432/80·credit4(selector-occurrence 합계)다. 이 표본의 양성은 local passing이며 ordinary 전체/개별 leading 양성은 관측하지 못했다. 미관측을 전체 작업의 부재로 일반화하지 않는다.

실제132마디 C3 `[262,525/2)`→B♭2 `[525/2,263)`→A♭2 `[263,527/2)`는 각음가1/2이며 두 원 link 아래 가운데 B♭2만1/2 conditional credit을 받는다. Batch2/selector8의 clause는 `fmnroleclause_1a1663ea985dd3f91a3700f3`다. 반대로 G♭2 `[527/2,264)`→F2 `[264,529/2)`→D♭4 `[529/2,265)`는 실제 link가 있어도 첫cut529/2를 넘어 full triple이 한 slot에 포함되지 않는다. 따라서 unassessed/creditNone/clips빈배열을 유지하며 slot 밖 음가를 빌려 support를 만들지 않는다. Failed leading 예의134마디 F4 `[267,535/2)`는 source-member만참이고 target-shape/first-change/endpoint guard는거짓이다. 이 조건부 전제들을 최종 NCT/화음 정답으로 승격하지 않는다.

신규 압축 바이트 SHA256(같은 출력 기준)은 다음과 같다. Producer/계산 재실행/파일편집은 없으며 나머지 greedy body/terminal/전체 완료는 이 표본 감사 밖이다.

| 상대 경로 | SHA256 |
|---|---|
| `comparisons/fmilcompare_17aee994647a53aef6eaea54.json.gz` | `ed4b0f1e6a3219893c09df4361cdc8b19ad769af1800617944a9ec0a4015bdb9` |
| `explanations/fmnrole_222e75aef17ad7627c0f3504.json.gz` | `db4edf784d2db4c59ff6ff1cb926017a69542523ae758fbf974e78255fc38528` |
| `comparisons/fmilcompare_b36d25f5a64a562be425b63f.json.gz` | `fbf1c466bed9066c197e04a0d6551c7027f0db7c33cee76e13acf8f496447562` |
| `explanations/fmnrole_cb952a3dea05510ac0d6bc77.json.gz` | `c58d256e928dd5a68b1654f55438565ee9c5f348e3a1f945beb2bdf98a885bca` |

## 전체 완료 및 종료 검수

최종 [report](../../../output/fresh-source-progression-evidence-2026-10-03-r1/report.json), [context-index](../../../output/fresh-source-progression-evidence-2026-10-03-r1/context-index.json), [run-plan](../../../output/fresh-source-progression-evidence-2026-10-03-r1/run-plan.json)을 저장한 뒤 runner가 **exit0**로 정상 반환했다. Official status는 `fresh_source_replay_saved_not_selected`이며 `computation_integrity_passed=true`, `submitted_nonempty_requests_completed=true`, `known_empty_request_set=false`다. Whole completion holds·incomplete/unstarted·missing terminal·failure·observer error·partial file은 모두0/빈목록이다. 각 원 작업의 terminal은 `computed_native_role_source_requests_not_selected`다. 제출 계산 완료와 음악 해석의 채택을 분리한다.

### 원 요청 분모와 네 작업

| 등록 source / 원 가정 | 요청 | 연속 batch / 마지막 요청 수 | Key별 요청 | Conditional credit 합계 |
|---|---:|---:|---|---:|
| Beethoven Sonata 01-1 / no-link | 2,315 | 145 / 11 | 5 × 463 | 1260/1 |
| Beethoven Sonata 01-1 / 원 greedy | 2,315 | 145 / 11 | 5 × 463 | 16915/6 |
| Beethoven Quartet n01op18-1_04 / no-link | 1,710 | 107 / 14 | 5 × 342 | 0/1 |
| Beethoven Quartet n01op18-1_04 / 원 greedy | 1,710 | 107 / 14 | 5 × 342 | 1555/2 |

소나타 context86/`cont_c746e2edd7221f185acf`, 사중주 context1905/`cont_00fe53c74ace3533c190` 두 등록 구간만 대상이다. Context-index의 jobs는 source별 배열이며 job index0/1이 source마다 재시작한다. Source/key/원 completion request identity를 함께 사용한다. Original no-link/greedy를 독립 보존하고 그중 좋은 부분을 합쳐 새 completion으로 만들지 않는다. 각 path의 관측 raw note-time은 소나타85/2, 사중주53/2다. Conditional credit은 selector occurrence를 합친 note-time 산술이며 음표 수·곡 길이·분석 정확도 또는 조건 간 승자 점수가 아니다. 사중주 no-link의0/1은 **계산된 알려진0**이지 미상값 대체가 아니다.

- 전체 native/role computed path 및 raw-time 보존은 각각8,050이다. 각 원 path가 하나의 요청 위치에 대응하며 두 계산 종류를 합쳐16,100개의 서로 다른 요청이라고 세지 않는다.
- Completed batch504, direct comparison 및 role 내부 재인증을 포함한 native comparison calls1,008, role prepare/explain504개씩이다. Fresh bridge 준비2와 verified native preparations2, 별도 bundle registrations4다.
- 원 declared322contexts/1,013raw lanes 중 이번 selected2/7이며 미실행320/1,006을 유지한다. Registered context pool은5다. 선택한 원 proposal714path/4,025selector에 원 두 completion을 각각 적용한8,050발생이며 원 Cartesian42,851path 중 제안하지 않은42,137을 평가했다고 주장하지 않는다.

### 저장된 조건부 지원과 미상

| 항목 | 실제 저장 집계 | 의미/제한 |
|---|---|---|
| Role clauses | supported6,310 / failed118,425 / unassessed19,390 | 전체144,125발생의 조건부 설명; NCT 정답률 아님 |
| Individual ordinary support | 275발생 | 개별 motion 지원과 전체 ordinary/joint truth는 다름 |
| Whole ordinary template truth | true20 / false980 / unknown9,760 | 총10,760 internal transition 문맥; native와 role 집계 일치 |
| Joint functional truth | true8 / false990 / unknown9,762 | 명시 기능/전체 해결 전제의 결합; 화성·Secondary 정답 판정 아님 |
| Conditional explained note-time 합계 | 14570/3 | 모든 selector occurrence의 중복을 포함한 합계 |
| Raw account unknown/uncomputed | 0 / 0 | 모든 요청 계정 계산 완료; clause unassessed와 구별 |

Computed internal transition contexts10,760 중 explicit declared functional contexts1,000, complete bundle 아래의 resolution contexts1,000이다. 많은 ordinary unknown은 원 요청의 `None` 기능 가정에 해당하며 누락된 batch나 미완료 계산으로 세지 않는다. Joint unknown이 ordinary보다2많다는 사실도 그대로 보존한다. 이 집계만으로 그2건의 새로운 음악 해석을 만들지 않는다. Role clause의 unassessed도 완전한 저장본문 안의 전제 보류이며 미계산 요청과 구별한다.

최종 selected는null이다. Full contrast·all logical paths·policy·winning harmony·NCT/function/secondary/cadence 확정·musical accuracy·training/Gold·generation-ready·production modified flags는 모두false다. 원주석 label이나 supplier ornament를 조건부 NCT credit의 권한으로 사용하지 않는다.

### 전체 자원 실측과 보존된 관찰

Official elapsed는**5,074.453444299987초(약84.57분)**, 마지막 wrapper 반환 관측은5,075.105362400063초다. Source fresh 준비 시간은 소나타106.71809720003512초, 사중주96.58278669998981초다. 각각의 절대 완료elapsed153.6139187/3190.4115440초를 준비 소요시간으로 오해하지 않는다.

| Source / 가정 | 작업 시작→종료 소요 초 | Batch 소요 초 최소 / 중앙 / 최대 |
|---|---:|---:|
| Sonata / no-link | 1,506.6358974 | 7.3617952 / 9.7610289 / 14.1333645 |
| Sonata / 원 greedy | 1,431.7994590 | 7.5020268 / 9.2618847 / 12.9175394 |
| Quartet / no-link | 894.8358724 | 6.1856983 / 8.1828507 / 11.2948581 |
| Quartet / 원 greedy | 977.0471483 | 6.4619293 / 8.9559789 / 13.3887470 |

Full process peak working set는 **2,508,488,704bytes/약2.336GiB**, 관측된 physical available 최솟값은13,371,228,160bytes/약12.453GiB다. Pilot1.81GiB와 full bridge/stream/writer2.336GiB는 별도 측정이다. 메모리 관찰은 샘플값이며 실제 메모리 hard cap, 이후 full-contrast 자원 보장 또는 정확한 예상 시간으로 쓰지 않는다. 저장한 모든 계산 body/manifest의 물리 합계183,060,358bytes는 약174.58MiB이며 기본2GiB/decoded record128MiB/manifest16MiB reserve를 유지했다. 지원 조건이나 결과 threshold는 바꾸지 않았다.

[전체 실행 관찰 receipt](../../../reports/fresh-source-progression-resource-observations-2026-10-03-r1.json)는 root가 수집한 parsed JSON stdout684event를 정리한 별도 연구 기록이다. Heartbeat165, admission complete1, source prepare start/end각2, job start/end각4, saved batch504, report saved1, returned1이다. Source/job/batch별504고유 위치와 selector end의 연속성을 대조했고 원 실측값을 보존했다. 별도의 `admission_started` stdout 행은 retained list에 없어 원stdout 전체 archive라고 주장하지 않는다. Sealed native analysis의 권한이나 음악 정답 dataset이 아니며 frozen1025output 목록 밖의 `reports/`에 저장한다. Receipt SHA는 `e3f42d8616073001e89ae74410f1c3b60b6f7ef086b545f2ed51e34cb158cb91`다.

### 최종 저장 계약의 독립 감사

읽기 전용 **67,141 consistency checks/58.2992549초/오류0**이다. 정확1025파일은 comparisons504 + explanations504 + bindings2 + bundles4 + jobs4 + lattices2 + plans2 + manifests3다. Report의 artifact_hashes1024는 self-report를 제외한 exact inventory이며 실제 모든 SHA가 일치했다. Total output/manifest reserve 산술, 전체2sources/4ordered completion/8,050selector/504contiguous batch 및 key별 분모를 원proposal/plan/completion/header/job/index에 대조했다. Missing/repeated/held/incomplete positions0이다.

Source0의 이전580comparison/explanation 본문 검수는 닫힌 두 terminal의 동일 physical SHA와 exact batch refs 및 최종 writer artifact_hashes 재검사로 연결해 재사용했다. 당시 개별580파일의 임시 SHA 목록은 파일로 보존하지 않았으므로 그 잃어버린 목록과 직접 다시 비교했다고 주장하지 않는다. Quartet 신규428본문은 한 배치씩 seal/ref/order/count/raw Fraction 합계·terminal truth/clause/credit 집계를 읽었다. Product predicate/producer/actual replay를 다시 실행하지 않았다.

이번 감사가 읽은1034경로의 전후 SHA는 불변이다. 누적 decoded JSON1,196,973,679bytes이며 그중 creation input/code와 직접 대조한 범위는9경로다. Root가 **별도로4,784registered inputs +347code의 union4,788경로 전체 SHA**를 검사했으며6.4173322초/변경0이다. 원 부모 output의 exact inventory6/7/7/148도 등록 경로 집합과 실제 recursive 목록을 대조해 누락·추가0이다. Pilot 보호4,789는 probe를 추가한 별도 범위이며 actual 등록4,788로 소급 변경하지 않는다.

위 검수 수, 앞선 source0/표본 감사 수, pilot103확인과 기존 unittest를 합산해 음악 정답/새 테스트 수로 보고하지 않는다. 이번에는 보호 엔진/test를 바꾸지 않아 full actual replay를 unittest 재실행으로 가장하지 않았다. 원XML/Core/IDs/주석·기존 코드·과거 결과와 별개tracked5파일은 유지했다. Frozen output에 receipt/문서 파일을 추가하지 않았다.

### 종료 manifest와 네 terminal의 물리 SHA256

| 저장 상대 경로 | SHA256 |
|---|---|
| `report.json` | `ebf40c6c472a3aa85b890aa780598ca22bfc0385a59176bfc100ca4226d24793` |
| `context-index.json` | `a18f178bc0cb56c8f4518cf71fd4ba9f3220dad7766439bbef23cb6dae2b93b5` |
| `run-plan.json` | `2b7486af432a133f269b253dcd4376e893cba75c36eb5f8875f4f0be45de5700` |
| `jobs/npsreplayjob_232ab438cb454aadf55e1481.json.gz` | `05a1067dc948f53deb603c7b12385d7de467a6af8201c1b96bc8a0dccbe9c622` |
| `jobs/npsreplayjob_4f41a09463103f31c32bd25f.json.gz` | `42fe2d7963e5a3265a22df038a8a20c67ffbda1a35fad34a820ca5ac69e593de` |
| `jobs/npsreplayjob_9b01c19d55b1c2353f918003.json.gz` | `66e6471780a06fd443eeec86b26f232e20993117c84a73dbdbcebf0e83509ba9` |
| `jobs/npsreplayjob_2db1fec7d3b4a3e5f06365a8.json.gz` | `14079d0fff3c44cee4dbc9de77497df2fb6ae53099dc58a69d4391d548d822cc` |

### 문서 및 동결 코드 최종 QA

Root 최종 QA에서 화성 개발 MD4개 strict UTF-8·NUL/깨진 대체문자 검사와152개 local Markdown 링크를 확인했고 오류0이다. 두 관찰 helper AST도 PASS이며 producer를 실행하지 않았다. 원 replay core/runner/tests4개 + probe/wrapper2개 + 새 관찰 receipt1개, 총7개 동결 SHA의 변화0이다. `git diff --check`는exit0이며 기존 별개tracked5파일의 LF→CRLF 경고만 유지했다. Git commit/push·원 권한/설정 변경은 하지 않았다.

## 다음 개발 단위

이 단계의 full actual replay는 완료했다. [Cross-batch 진행 후보 대비 기획](2026-10-03-cross-batch-progression-contrast-plan.md)을 구현할 차례다. 같은 source/scope/lattice/key/bundle/**원 completion request**의20그룹에서 전체1,652,640pair를 bounded570block task로 대조한다. 검증된 저장 body를 source fact catalog/facet으로 공유하고 pair별 exact cell/refinement·category delta·nullable conditional credit를 보존한다. 기존 public256한도/음악 의미를 바꾸거나 batch별 winner를 합치지 않는다.

다음은 small legacy-equivalence와 null/hold/refinement/원분모 보존 검사, 결과 독립 resource pilot를 먼저 한다. 이번 턴의 cross-batch adapter 구현·pair 실제 계산·policy/winner/UI/구조/생성은0이다. 별도 읽기 전용 최종 기획 검토에서는 추가 차단 결함이나 과장을 발견하지 못했다. 기술 저장/계산 검수에 사용자 음악 판단은 필요하지 않았고, 실제 경쟁 화성 해석을 악보에서 비교할 단계에 이르면 의견이 필요한 구간을 제시한다.
