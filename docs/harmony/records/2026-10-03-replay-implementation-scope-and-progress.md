# 단계29 후속 — 실행기 구현 범위와 전체 진행 위치

2026-10-03. [단계29 정본](2026-10-02-fresh-source-progression-evidence.md)의 후속 개발 기록이다. 이전 차단·검사 이력은 지우지 않는다.

## 최초 재시도와 차단 snapshot

사용자는 “진행하세요. 지금까지 절반 정도 했나요.”라고 답했다. 직전 질문은 원본·기존 분석기를 유지하면서 새 실행기/저장 테스트 두 파일을 구현하는 승인을 요청한 것이었다. 이를 근거로 새 runner의 검증·집계·제한 저장기 코드 추가를 시도했지만 자동 승인 검토가 다시 거부했다.

검토 사유는 fresh native/role replay 실행과 출력 쓰기 경로가 초기 read-only 범위를 넘어가며, 제한된 runner/test 추가 승인이 그 전체 구현을 명확히 허용하지 않는다는 것이다. 이번 거부 patch의 대상은 아래 새 runner 한 파일뿐이었다. 코드가 적용되지 않았으며 다른 agent·파일·shell 쓰기로 우회하지 않았다. 사용자에게 정확한 코드 구현 범위와 실제 corpus 실행을 구분해 다시 확인한다.

| 파일 | 당시 승인 전 내용 | SHA-256 |
|---|---|---|
| `src/musicanote_harness/source_progression_replay_trial.py` | 265줄/19,884bytes. 설정·helper·direct `load_inputs()`만 있음 | `45bd4d29f0efd85f9238fde33d5043cf170504f790c3218470b09c1619d13c6c` |
| `tests/test_source_progression_replay_trial.py` | 149줄/7,355bytes. 9개 draft, 이전 admission-only 7개 실행 | `969defab93df499e30a1352a67c9d0b98b387317b7a817a5917d48452e8deb17` |

이 승인 전 시점에는 `run()`·`main()`·CLI entrypoint·packet writer·binding/job/summary 저장 검증·진행 알림·총 압축 출력2GiB 제한이 없었다. Core SHA `e32d98f57a717f2a508512b5ae07eee9a44890635dcc9689dfc6f08910c0e888`와 core test SHA `dbff8de88df409ab14c0d4fe6cd549777d0612d71f2ed0d57962a53cde157ebc`도 이전 snapshot과 같았다.

당시 차단 턴의 검증은 파일·API·SHA와 tracked status의 read-only 확인이었다. 그때 새 테스트 재실행·실제 악보 replay·새 계산 산출물은0이었다. 이전 신규54개 통과를 새로운 검사 수로 합산하지 않았다. 기존 별개 tracked5파일의 변경도 그대로 유지했다. 새 엔진의 화면·구조·생성·학습/Gold·Git 변경은 없었다.

## 확인한 구현 범위

승인 대상은 위 두 새 Python 파일에만 fresh native/role replay를 호출하는 `run()`/CLI, 원 제출 순서와 네 completion 전체를 보존하는 batch 저장·검증, append-only/exclusive 쓰기·압축 출력 총2GiB 상한과 manifest 예약, 진행 알림, synthetic/mock 저장 테스트를 구현하는 것이다. 기존 원본 XML/IR/주석·producer·과거 결과는 변경하지 않는다.

이 승인은 **코드 구현과 synthetic/mock 테스트**의 범위다. 실제8,050 selector×completion의 corpus 실행은 구현·검사 동결 후 시간/메모리/출력 사전 점검을 거쳐 별도로 진행하며, 이번 차단 상태에서 시작하지 않는다. 전체 경쟁 비교·승자 선택·운영 UI 승격은 이 코드 구현 범위에 포함하지 않는다.

## 정확한 범위 승인 후 재개

사용자는 위 범위를 명시한 최종 질문에 “네”라고 답했다. 그 직접 승인을 근거로 새 두 파일의 코드 구현과 synthetic/mock 검사를 재개했다. 첫 `apply_patch`는 정상 적용되어 새 runner에 closed plan/binding/job 검증, accepted batch의 path/call/truth/clause/Fraction 집계, exclusive 압축 writer와 기본 총2GiB·manifest16MiB 예약 한도를 추가했다. 이전 차단 patch를 다른 경로로 우회한 것이 아니며 사용자 승인을 받은 같은 두 파일에만 구현한다.

이후 run/CLI·packet 순서·진행 알림·중단 처리와 저장 테스트의 연결을 완료했다. 위 SHA/줄수 표는 **승인 전 snapshot**으로 보존하고 최종 동결 SHA는 아래에 별도로 기록한다. 기존 core/core test와 원본·기존 코드/결과는 유지한다. 실제 corpus replay·운영 UI·구조·생성은0이다. 구현/검사 통과와 실제 음악 정확도는 별개다.

### 재개 후 독립 검사 — 실행기 완성 전

Root가 기존 core의47개 합성 XML/API 검사를 재실행해 **47/47 PASS, 68.132초**를 확인했다. 이전47개와 같은 suite이므로 새47개를 추가한 것으로 합산하지 않는다. 두 frozen SHA는 그대로다.

별도 genuine bridge 검사는 `single`·`tied`·ready-empty·held-empty의4개 synthetic 요청에서 실제 `prepare_replay`/`stream_prepared` 결과를 새 runner의 binding/plan/batch집계/job 검증에 연결했다. **18확인/8.6846701초 PASS**이며 single/tied 각각55selector, ready-empty의 rational0과 held-empty의null을 보존했다. 이18은 unit test 수나 실제 음악 정답 수가 아니다. Corpus·`run()`·계산 산출물 생성은 없고 fixture의 임시 XML만 사용했다.

재현은 `tests/test_source_progression_replay.py`의 fixture를 composition으로 준비하고 위4요청을 `fx.inputs()`로 얻어, real core API→새 `_binding`/`_plan`→`_validate_batch`/`_add_batch`→`_job` 순서로 검사한다. 원 TestCase를 상속/전체 재실행한 것으로 세지 않는다. Genuine packet 검사와 archive/storage mock의 역할을 구별한다. 이 시점의 module import도 성공했지만 run/CLI 완성 또는 전체 저장 검사 통과를 뜻하지 않는다.

## 실행기 구현 완료 — 코드·저장 계약 검증 범위

새 [runner](../../../src/musicanote_harness/source_progression_replay_trial.py)와 [저장 테스트](../../../tests/test_source_progression_replay_trial.py) 두 파일을 완성했다. 기존 [fresh core](../../../src/musicanote_harness/source_progression_replay.py)와 그 테스트는 수정하지 않았다. 새 코드가 fresh 계산을 호출할 수 있다는 것과 실제 corpus를 실행했다는 것은 구별한다. **이번 단위의 실제 corpus 계산·산출물은0**이다.

### 처리 순서와 계약

1. Direct `load_inputs()`로 단계28의 정확한 저장자료·등록 원 전체 IR·부모 목록·creation SHA를 확인한다. 과거 producer나 과거 실행기를 재실행하지 않는다.
2. 모든 원 source와 completion의 전체 selector/batch 계획을 먼저 계산한다. 출력·fresh query 전에 논리 예산과 manifest 공간을 검사한다. 과거 결과는 요청이며 fresh native 권한으로 재사용하지 않는다.
3. Source마다 fresh bridge를 준비하고 전체 IR/scope/lattice와 origin mapping의 동일성을 검사한다. 원 completion마다 별도 fresh bundle을 사용한다. 서로 다른 성부 completion의 유리한 근거를 합치지 않는다.
4. Header → 원순서의 모든 indexed batch → terminal → iterator exhaustion을 확인한다. Path/source/원음가·유리수 계정·계약 버전·예산·refs·상태·보류 이유를 검사하고 검증된 comparison/explanation 쌍만 저장·집계한다. 순서 변경·누락·추가 packet·가짜 terminal은 완료로 인정하지 않는다.
5. 입력/코드/부모 목록과 새 저장파일의 SHA·목록을 대조하고 index/report를 저장한다. 저장된 prefix, 보류, 미계산 범위와 모든 원 completion 위치를 남긴다. 실패 후 생성 파일을 지우거나 과거 결과를 덮어쓰지 않는다.

저장 구조는 `run-plan.json`, `plans/`, `bindings/`, `lattices/`, `bundles/`, `comparisons/`, `explanations/`, `jobs/`, `context-index.json`, `report.json`이다. 각 본문은 ID와 SHA로 참조하는 gzip JSON이며 gzip `mtime=0`과 exclusive `xb` 쓰기를 사용한다. 같은 ID의 같은 본문만 중복 저장을 생략하고 충돌은 거부한다. Report의 artifact 목록에는 final index SHA가 포함되며 report 자체는 자기 SHA 목록에 넣지 않는다.

### 중단·분모·자원 규칙

- 기본 총 신규 출력 상한은 **2GiB = 2,147,483,648bytes**다. 더 작은 한도는 가능하지만 이번 구현에서 이보다 큰 설정은 거부한다. 본문 decoded 한도128MiB와 기본 final manifest 예약16MiB는 별도다. 논리 계산 예산은 시간/RSS/출력 bytes 한도가 아니다.
- 모든 계획 위치에 대해 보수적인 manifest 크기를 사전 계산하고, 마지막 실제 index/report encoded bytes도 다시 검사한다. Batch 본문은 manifest 예약을 소비할 수 없다. 압축 후 쓰기 전에 bytes를 예약하므로 부분 쓰기/OSError도 한도를 빠져나가지 않는다. 남은 부분 파일의 bytes/SHA와 예약량을 기록한다.
- 예산 또는 파일 쓰기 실패 시 뒤 계산을 멈추고 미시작 source/completion·미저장 selector 범위를 보존한다. 다른 계약/packet 오류는 해당 작업을 incomplete로 남긴다. Stream은 `finally`에서 닫는다.
- Aggregate 분모는 **모든 계획 작업**이다. 완료 terminal만 골라 분모를 줄이지 않고 terminal·검증 저장 prefix·미계산 placeholder를 모두 반영한다. 실제로 알 수 없는 runtime 호출 수를 prefix 합계로 가장하지 않는다.
- Known-empty 완료 요청의 exact rational0과 held-empty의 unknown/null을 구별한다. `known_empty_request_set`은 무결성이 유지되고 **모든 작업이 완료된 빈 요청**일 때만 True다. 저장된 runtime-hold terminal도 incomplete complement에 남는다.
- CLI는 구조 무결성 실패 report면 exit1이다. 정상 구조로 저장된 whole hold는 exit0일 수 있으므로 exit0 자체가 음악 정확도나 nonempty 제출 완료가 아니다. `computation_integrity_passed`, `computed_completion_requests`, `whole_completion_holds`, `incomplete_or_unstarted_completion_requests`, `submitted_nonempty_requests_completed`를 함께 읽는다.
- Progress callback은 admission/source 준비/job/batch 저장/report 경계에서 detached event를 전달한다. 관찰자 예외는 제한된 별도 오류 목록에 남기며 계산 packet을 바꾸지 못한다. **개별 native 계산 내부 heartbeat·CPU/RSS 상한은 아직 없다.**

최종 화성/NCT/key/cadence·winner·rank/confidence·UI·구조·작곡편곡·Gold/학습에는 승격하지 않는다. `selected=None`과 미승격 flags를 유지한다. Credit는 별개 completion의 selector occurrence 합이며 작품 전체 원음표의 중복 없는 설명 비율이나 정확도가 아니다.

### genuine 형식 연결에서 발견한 교정

| 발견 | 원인과 수정 | 회귀 확인 |
|---|---|---|
| Real native query plan 거부 | `unique_literal_coordinate_times`는 rational **list**인데 scalar integer 한도로 검사했다. List 항목의 exact 유리수 검증으로 교정 | Genuine tied packet이 header/batch/terminal 전체 검증을 통과 |
| Real bundle의 `selected=False` 거부 | Witness/assignment의 문자 그대로 False를 승격으로 오인했다. Nested False는 허용하고 top-level 결과의 selected/rank/confidence는 exact None을 별도 강제 | Genuine bundle 연결과 승격/자원 변조 반례 |
| Hold·부분 작업이 집계에서 사라짐 | 저장 terminal 유무로 incomplete를 세거나 완료 summary만 합산했다. 모든 계획 위치와 runtime hold complement를 유지 | 저장 hold terminal·미계산/부분 저장 분모/null 검사 |
| 부분 파일이 bytes 한도를 회피할 가능성 | 성공한 쓰기만 bytes에 더했다. 쓰기 시도 전에 예약하고 partial physical size/SHA를 보존 | Short/OSError injection과 exclusive 충돌 검사 |
| 보류된 빈 요청을 known-empty로 표시 | Selector0만으로 빈 완료를 판정했다. 전체 작업 완료·무결성을 추가 요구 | Genuine ready-empty와 held-empty 구별 |
| 실패 CLI가 성공 종료 | Incomplete report를 반환해도 비정상 종료가 없었다. 무결성 실패면 exit1 | Producer 없이 CLI failure injection |

계약의 ready/held 상태와 이유의 일관성, 독립 계산 counter/terminal 참조, 모든 batch 위치와 final manifest 상한도 보완했다. 교정은 이 두 새 파일의 검증/저장 문제이며 기존 producer·음악적 지원 조건·정답 threshold 변경이 아니다. 특정 음악 정답에 맞춘 조건은 추가하지 않았다.

## 최종 검사와 동결

작성 담당자의 최종 저장 suite는 **22/22 PASS, 89.970초**, root 독립 재검사도 **동일22/22 PASS, 90.783초**다. 초기19PASS/84.236초는 중간 결과이며 추가19개로 합산하지 않는다. 기존 admission-only7개도 이22개에 포함되어 있으므로 별도로 더하지 않는다. Genuine tied XML의 실제 core packet을 검증하는 검사와 genuine ready/held-empty 검사가 포함되며 archive admission·`run()`의 저장/중단은 synthetic/mock fixture로 검사했다. 실제 corpus 음악 정답 검사는 아니다. 최종 문서/보존 QA 결과는 아래에 기록한다.

Root의 기존 core47/47 PASS/68.132초는 위22개와 별도 suite다. 기존 core 검사 수는 신규47개가 아니며 전체 repository 회귀 검사라고도 하지 않는다. 별도 genuine18확인은 unit test 수로 더하지 않는다.

Root의 실제 저장자료 **read-only admission** 재확인은 **28.211113000055775초 PASS**다. Producer 호출을 AssertionError로 차단한 상태에서 reader23파일/254,888,715decoded bytes·보호4,784경로와 exact6/7/7/148inventory를 확인했다. 두 source·원 completion4개·planned selector occurrence8,050을 보존했다. Fresh prepare/compare/role·신규 corpus output은0이다. CLI `--help`도 exit0/1.400초이며 계산 실행이 아니다.

| 최종 코드·테스트 | 줄/bytes | SHA-256 |
|---|---:|---|
| `source_progression_replay_trial.py` | 956 / 67,691 | `7556b9b358097907a89fa29332550b7f4327c7aceed66470dc5fcd1ed2f0d72a` |
| `test_source_progression_replay_trial.py` | 470 / 28,676 | `7dac35e0b9422e48ed6ee4a32af9e0391135a978b1828bc85a02a721af6365ec` |
| 기존 `source_progression_replay.py` — 불변 | — | `e32d98f57a717f2a508512b5ae07eee9a44890635dcc9689dfc6f08910c0e888` |
| 기존 `test_source_progression_replay.py` — 불변 | — | `dbff8de88df409ab14c0d4fe6cd549777d0612d71f2ed0d57962a53cde157ebc` |

신규 runner/tests를 과거343개 creation-code 목록에 소급 추가하지 않는다. 새 실행의 code inventory에서 현재 버전을 보호한다. 기존 별개 tracked5파일은 보존하며 Git 쓰기·원XML/Core/주석·운영UI 변경은 없다.

독립 최종 정적 검토에서도 genuine witness의 False와 top-level None 검증, known-empty/held-empty 구별, permanent genuine packet 검사가 정확히 연결되어 추가 차단 결함을 발견하지 못했다. 지정 네 SHA도 일치했다. 별도 producer/corpus 실행이나 파일 변경은 없으며 정적 검토를 실제 음악 정확도 평가로 읽지 않는다.

최종 root QA는 **네 Python AST·동결 SHA4개, 개발문서4개 strict UTF-8/NUL/replacement-character 검사·로컬149링크 모두 PASS**다. Read-only `git diff --check`는 exit0이며 기존 tracked5파일의 LF→CRLF 경고만 있었다. Tracked status도 같은5파일이며 별개 수정은 보존했다. 예시 corpus 출력 디렉터리의 부재를 직접 확인했다. 개발문서4개만 갱신했고 과거 phase29 기록은 snapshot을 지우지 않고 후속 정본에 연결했다.

## 실제 실행의 다음 단계 — 이번 단위에서는 미실행

먼저 시간/메모리/디스크 사전 점검을 하고, 이후 모든 원4completion을 실행한다. 부분 pilot를 전체 submitted 완료로 표현하지 않는다. 직전 phase29의 결과 관찰 전 static policy인 **batch16/role3,000,000,000/native2,000,000/replay1,000,000,000,000/geometry100,000**을 유지한다. 계획은504batch/native kernel1,008·368,794,524,148 logical units이며 실측 시간이 아니다. 기본 batch3을 그대로 전체 corpus에 쓰면 보수적인 manifest 예약을 넘을 수 있어 query/output 전에 거부될 수 있다. Batch 정책은 source-size 비용으로 정한 것이며 음악적 기준 완화가 아니다.

아래는 **다음 단계 재현용 명령 예시이며 실행하지 않았다**. 출력은 ROOT의 `output/` 바로 아래 아직 존재하지 않는 새 디렉터리여야 한다. 기존 디렉터리 덮어쓰기·내부 재개·기존 파일 삭제는 하지 않는다.

```powershell
$env:PYTHONPATH = 'src;tests'
./.venv/Scripts/python.exe -B -m musicanote_harness.source_progression_replay_trial --parent 'output/source-grounded-progression-proposals-2026-10-02-r1' --output 'output/fresh-source-progression-evidence-2026-10-03-r1' --batch-size 16 --role-query-work-budget 3000000000 --native-query-work-budget 2000000 --replay-work-budget 1000000000000 --geometry-work-budget 100000
```

원 두 등록 구간은 Sonata `dcml:beethoven-sonatas:01-1` context86의2,315selector와 Quartet `dcml:beethoven-quartets:n01op18-1_04` context1905의1,710selector다. 각각 두 completion에서 계산하므로8,050요청이며 **두 전곡이나8,050곡이 아니다**. 원322문맥/1,013raw lanes 중 선택2/7·미실행320/1,006과 등록pool5의 나머지를 보존한다. 다음 실제 실행이 성공해도 cross-batch 전체 경쟁 비교1,652,640pair·정책·winner는 별도 bounded adapter 단계다.

## “절반 정도인가”에 대한 개발 기준

[메인 문서의 큰7기능](../README.md)과 [생성 로드맵](../MUSICAL_SEMANTICS_AND_GENERATION_ROADMAP.md)을 기준으로 읽는다. 단계29라는 번호나 unit test 수·후보/selector 수는 음악 정확도 또는 전체 진행률의 분자가 아니다. 기능별 남은 구현·검수 비용이 다르므로 정확한50%를 측정했다고 주장할 수 없다.

- 화성 분석의 **기반·계산 엔진 구축은 중간 지점에 가까워졌다**. 제한된 IR 교정, 원음표 추적, 같은 문맥의 조건부 근거 통합, 진행 비교 prototype, 조성/기능/종지 전제 연결이 있다.
- 믿고 쓰는 **자동 화성 분석 완성**은 그보다 이르다. 다양한 새 진행의 실제 근거 계산과 전체 경쟁 비교, 독립 작품·편성 평가 및 전문가 악보 검수가 남아 있다.
- **작곡·편곡까지 포함한 전체 목표는 아직 절반 전**으로 보는 것이 타당하다. 의미 데이터 계약·일부 역할/질감 관찰은 있지만 전개/배치 계획기·편성별 음표 실현기·완성곡 생성과 음악적 품질 검증은 후속이다. 이 표현도 측정된 퍼센트가 아닌 기능 상태에 따른 정성 평가다.

큰 잔여 묶음은 다음과 같다.

1. Fresh 모든 제출 계산과 cross-batch 경쟁자를 놓치지 않는 전체 비교·조건부 해석.
2. 국소 조성·Secondary·기능·종지를 실제 전후 성부 문맥에서 통합 검증.
3. 연구 표본 밖 독립 작품과 여러 편성/총보의 정확도·자원·악보 검수.
4. 새 엔진의 전체 악보 레이어·피드백·구조 분석 연결과 순환 강화 방지.
5. 역할/반주/전개 사례를 소비하는 계획기·피아노/실내악 실현기·독립 생성 검증.

## 다음 결정

정확한 범위 승인에 따른 새 두 파일의 구현·synthetic/mock 검사는 완료했다. 실패/보류/미실행을 완료나0으로 바꾸지 않으며, 악곡별 정답 조건이나 사례에 맞춘 지원 threshold를 추가하지 않았다. 실제 corpus 사전 점검·전체 계산·전체 비교·악보 검수/적용은 별도 단계로 남긴다.
