# 역사 원 요청 연결과 Source-once 저장 — 2026-10-03

## 1. 목적과 범위

단계33 개발 문서다. [직전 Source 공유 core·누적 읽기 계정](2026-10-03-source-shared-contrast-and-cumulative-read-budget.md)을 역사적 원 archive의 요청·selector에 연결하고, 공유 원자료를 한 번만 저장하는 별도 adapter를 만든다. 오래된 분석기와 XML/Core, annotation, producer, 원 archive, 과거 결과는 보존한다. 인수인계 문서에 누적하지 않는다.

이 단위는 연구용 library와 작은 합성 XML 저장 검사다. 실제 전량 body join, 1,652,640pair 대비, 독립 음악 정확도, 최종 화성/key/cadence/winner, 악보 UI/구조/생성/학습·Gold 또는 Git 공개 작업이 아니다. 원 request의 정체성과 파일의 진위를 확인하는 것은 음악적으로 올바른 화음 판정과 별개다.

## 2. 구별해야 하는 완료 상태

| 상태 | 뜻 | 뜻하지 않는 것 |
|---|---|---|
| Caller-declared read plan | 경로·SHA·정확한 읽기 순서·파일별 bytes와 전체 분모를 선언 | 역사적 원 요청의 인증 |
| Metadata admission | 생성 당시 code·부모 목록·원 source/request/key/bundle/selector를 대조 | Body의 전량 검증·음악 정확도 |
| Indexed body join | 모든 원 batch의 comparison/explanation·ordinal·terminal을 대조 | 새 대비 pair의 계산·저장 |
| Shared intrinsic groups | 원 key/request 그룹의 profile·clause·union을 새 source 계약으로 검사 | Live native authority·화음 정답 선택 |
| Submitted-group storage complete | 제출한 그룹의 source/local catalog/block·terminal 저장 및 파일 guard 통과 | 전체 archive 범위 완료·authenticated reload |

같은 bundle을 사용하더라도 서로 다른 원 completion request는 합치지 않는다. Source는 같은 owned handle일 때만 공유하며, 같아 보이는 JSON 또는 caller-declared source identity만으로 재발급 권한을 만들지 않는다.

## 3. 구현 경로와 API

두 새 library의 버전은 각각 `shared-source-archive-bridge-0.1.0`, `shared-source-progression-storage-0.1.0`이다. 직전 core/reader와 frozen predecessor는 수정하지 않았다.

- [새 archive bridge](../../../src/musicanote_harness/shared_source_archive_bridge.py): 완전한 upfront ordered `ReadInput` 및 기대 `InventoryRoot`를 받아 `plan_archive_reads → open_archive → metadata_prepared/source_prepared → iter_completion_entries → prepare_original_groups → finish_archive`로 연결한다. 모든 metadata/body/repeated read는 **하나의 owned 누적 reader**를 사용한다. 과거 `_ADMISSIONS`에 새 handle을 등록하거나 과거 loader를 monkeypatch하여 권한을 만들지 않는다.
- [새 source-once storage](../../../src/musicanote_harness/shared_source_progression_storage.py): `GroupInput(original, source, prepared, hold_reasons)`를 `plan_saved_run → begin_storage → write_block/write_prepared_group → ledger → finish`로 저장한다. 원자료 catalog를 source마다 한 번 저장하고, 각 local catalog와 compact block은 정확한 source ref를 참조한다. 저장기는 원 archive 인증을 독자적으로 수행하지 않는다.
- [Archive 검사](../../../tests/test_shared_source_archive_bridge.py), [저장 검사](../../../tests/test_shared_source_progression_storage.py), [독립 읽기→공유→저장 연결 검사](../../../tests/test_shared_source_storage_integration.py)를 별도 관리한다.

전체 source/body를 읽어 경로를 찾은 다음 reader를 새로 시작하거나, metadata 비용을 없었던 것으로 처리하지 않는다. 파일별 정확 decoded 비용이 없는 경우 계획 보류가 정상이며, aggregate 합계나 gzip trailer의 ISIZE를 파일별 정확 비용인 것처럼 사용하지 않는다.

JSON을 읽기 전의 예약은 caller 선언에 대한 검사다. 역사적 membership은 metadata를 대조한 뒤에만 확인할 수 있다. 이때 jobs/batches에서 도출한 **전체 remaining ordered comparison→explanation occurrence**와 같은 reader의 아직 읽지 않은 계획을 정확히 대조한다. Metadata-only·body 누락·추가·재배열 계획이면 body/source/group 준비 전 실패해야 한다. 이 검사 없이 첫 completion만 준비한 뒤 나중에 unplanned read에서 실패하는 방식은 완전 원 비용 예약을 우회할 수 있어 허용하지 않는다.

## 4. 자원·중단·보호 규칙

기본 누적 decoded1GiB, source/group256MiB, 전체 output2GiB, plan2MiB, manifest16MiB, block64MiB는 임의로 올리지 않는다. Source와 local catalog·모든 nonempty block·terminal 용량을 비교 전에 예약한다. Count gate는 큰 catalog export나 quadratic task 생성보다 먼저 적용한다. Whole hold는 원 분모와 이유를 남기며 유리한 prefix를 계산하지 않는다.

입력/기대 root와 output은 plan/begin/finish의 전체 SHA·정확 목록으로 확인한다. 새 저장기는 block마다 고정된 직접 계산 code, owned source/group 정체성 및 새 파일의 실제 bytes/SHA를 확인하고, 다른 등록 입력·과거 출력의 변조는 terminal 전체 검사 이전에 완료를 부여하지 않는 방식으로 탐지한다. 이는 매 block마다 수천 입력과 모든 과거 출력 전체를 재해시하는 비용을 줄이기 위한 명시 정책이며, 중간 persisted 수는 terminal 이전에는 provisional이다.

Exclusive 새 출력 폴더만 사용하고 등록 원 archive/root 안에 결과를 저장하지 않는다. 계산 시도·확인된 계산·저장된 pair·보류·미계산·계산됐으나 미저장·불확실한 계산과 partial/unknown physical fragment를 구별한다. 실패 비용은 환불하지 않는다. On-disk report는 자기 자신의 마지막 write 성공을 인증하지 않으며 owned `finish` 반환과 구별한다. 저장 JSON에서 권한을 복구하거나 resume하는 기능은 이번 범위가 아니다.

## 5. 실제 자료 실행의 현재 한계

원 saved replay는 **두 등록 구간·4completion·8,050entry 발생·20group·1,652,640예정pair·570예정 nonempty block**이다. 작품 전곡 수나 음악 정답 수가 아니다. 원 전체322문맥/1,013lanes 중 이번 source에 포함되지 않은320/1,006도 그대로다.

직전 guarded byte-stream receipt의 old34 metadata read +1,008body는3,007,200,897decoded bytes로 기본1GiB를 넘었다. 새 bridge는 추가 ancestry metadata를 검증하므로40 ordered metadata read가 필요하며, 이전 합계를 새 실행의 정확 비용으로 재사용하지 않는다. 이전 receipt에는 개별 body의 decoded 비용 지도가 없다. 따라서 이번에는 실제 전량 ReadPlan 성공이나 실제 resource pilot을 선언하지 않는다. Root archive의 index644,009bytes, plan930,748bytes, report210,945bytes가 작다는 사실도 나머지 read의 비용·membership 인증을 대체하지 않는다.

Source sharing은 decode 양을 줄이지 않는다. 실제463/342-entry local group의 encoded/refinement 상계·메모리·runtime과 전체 결과 용량은 아직 미측정이다. 한 key의 selector가 여러 batch에 흩어져 있으면 해당 group을 준비하려 해도 원 completion 전체 body 읽기가 필요할 수 있다. 좋은 일부 entry만 골라 실제 pilot의 성공 근거로 쓰지 않는다.

다음 실제 실행 전에는 결과와 무관한 전체 파일별 비용 측정·scope/자원 정책을 먼저 정한다. Byte-only 측정에도 명시 한도와 SHA/기대 root guard를 적용하고 같은 logical run에서 재파싱할 경우 측정 read 비용을 계속 계상해야 한다. 필요한 경우 별도 측정/실행 단계와 양쪽의 비용을 명확히 보고한다. 현재 default 한도에서는 미상/초과 whole hold가 정직한 결과다.

현재 strict bridge는 원4request의 완전 body 목록을 요구한다. 기본 한도를 유지한 pilot은 이를 조용히 줄여 실행하는 것이 아니라 **완전한 한 원 completion을 별도로 선언하는 versioned scoped adapter**가 먼저 필요하다. 전체4request/8,050entry/1,652,640pair와 생략 범위를 계속 표시하고 full archive는 false로 유지한다. Quartet no-link completion은 old 비용 proxy상 metadata 포함 약0.95GB여서 검토 후보이나, 새40read·파일별 비용·group 상계·RSS를 실측하지 않았으므로 현재 실행 가능하다고 확정하지 않는다. Key group이 batch마다 흩어져 있으면 일부 entry만 읽어 pilot 성공을 주장하지 않는다.

## 6. 검수·교정·최종 검사

독립 최종 감사에서 추가 차단은 발견되지 않았다. 아래 문제를 교정하고 같은 코드 SHA에서 root 최종 검사를 완료했다. 새로운 고유 검사 수를 기존 subset 재검사나 JSON visit 수와 합산하지 않는다.

이번 검수에서 드러난 계약 문제는 다음과 같다. 특정 악보의 화성 정답을 수정한 것이 아니다.

- 역사적 code SHA를 ancestor와 extension map 합칠 때 덮어쓸 수 있는 충돌을 거부하도록 보완했다. 오늘의 code glob을 과거 생성 목록에 더하지 않는다.
- 동일 원 source identity를 서로 다른 source handle/bundle subset으로 나누어 중복 저장하는 경우를 막고, public metadata에 완전한 original group declaration과 source/completion/group 위치를 제공한다. Root 통합은 private archive state에 접근하지 않는다.
- Source/group의 cap 보류에도 원 전체 metadata·read ledger·분모와 구체적인 offending plan을 보존한다. Boolean index와 terminal/failed handle에서의 새로운 source/group 발급을 막는다.
- 완전 remaining body 계획을 metadata 뒤에 확인하여 비용이 누락된 계획의 body/source/group prefix 작업을 막는다.
- 마지막 batch yield 후라도 job terminal 검증을 끝내지 않았다면 미완료다. Active iterator 상태에서 finish한 뒤 generator를 재개하여 과거 terminal을 나중에 완료로 승격할 수 없어야 한다.
- SHA/physical fragment 관찰 중 중단과 output symlink를 fail-closed로 처리하고 provisional 저장 수를 확정 성공과 구별한다.

### 6.1 최종 검사와 범위

| 실행 | 수·시간 | 결과·분모 |
|---|---|---|
| Root 신규 세 suite | **48개/142.691초** | Bridge16 + storage28 + root 연결4, PASS/exit0 |
| Root 기존 core/admission 회귀 | **41개/80.930초** | 별도 기존 검사, PASS/exit0 |
| Bridge 작성 최종 | 16개/89.776초 | 같은 최종 source/test SHA, root48과 중복 |
| Storage 작성 최종 | 28개/35.432초 | 같은 최종 source/test SHA, root48과 중복 |
| Root 초기 read→source→storage | 3개/3.860초 | root 연결4 중 subset, 중복 |

실행 명령은 프로젝트 root에서 다음과 같다. 별도 환경에서는 프로젝트 venv를 먼저 선택하고 `PYTHONPATH=src;tests`를 설정한다.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m unittest test_shared_source_archive_bridge test_shared_source_progression_storage test_shared_source_storage_integration
.\.venv\Scripts\python.exe -B -m unittest test_cross_batch_progression_contrast test_cross_batch_progression_admission
```

Bridge16은 genuine 작은 XML에서 만든 saved native/role packet과 owned cumulative reader를 연결하지만 **ancestry 단계는 명시적으로 mock**이다. Real metadata entry point의 strict count 음성 검사와 순수 역사 code 충돌 검사는 포함하되 실제40read 역사 ancestry의 성공을 전수 검증한 것은 아니다. 저장28은 genuine source/local/pair 검사 및 명시 mock의0/1/64/65 task geometry·중단/위조 통제를 포함한다. Root4는 세 genuine saved-read 연결과 public 원 group declaration→source0의 완전 두 request 저장을 검사한다. 마지막 연결도 ancestry는 mock이고, 원4request 분모/다른 source의 미검증 intrinsic 범위를 유지한다. 기존 body 전량 검증이나 음악 정답률로 확대하지 않는다.

Source 한 번 저장, 동일 bundle의 다른 request 유지, 원 selector와 rational legacy pair exact 복원, 타이·null/관측0 보존, read 완료와 pair/저장 완료 분리, whole output hold·partial 저장을 검사했다. Root 통합은 private archive state 또는 과거 admission registry에 접근하지 않으며 saved-only 검사 동안 native/role producer 재실행을 금지했다.

초기 bridge10/63.795초 및 후속15/79.017초 PASS는 최종 lifecycle 추가 전 재검사다. Storage 초기24 중 기존 디렉터리 fixture1ERROR는 보호 입력을 포함한 상위 디렉터리를 대상으로 골라 더 엄격한 보호 오류가 발생한 것이며, 독립 sibling 대상으로 교정했다. 감사 보완 관련5/9.561초 PASS 뒤 최종28을 검사했다. 이 수를48개의 신규 고유 검사에 더하지 않는다.

### 6.2 작은 저장 관찰

Storage 작성 측 genuine 두 request/두 pair fixture에서 source raw1,060,861bytes가 gzip78,582bytes로 **한 번** 저장됐다. Local catalog는 각각 raw232,223bytes, gzip17,126/17,127bytes다. 물리/시도 output137,835bytes, 전체 사전 예약156,145,782bytes, manifest upper134,448bytes를 구별한다. 원 분모8,050/1,652,640/4는 fixture 선언이며 실제 corpus를 읽어 얻은 값이 아니다. 모든 승격 flag는 false다. 이 작은 비용을 실제463/342-entry 비용·RSS로 선형 외삽하지 않는다.

## 7. 보존·동결 및 다음

선행20개 동결 source/test/receipt의 초기·최종 SHA는 변경0이다. 선행15 목록은 [저장·읽기 예산 기록](2026-10-03-cross-batch-storage-and-read-budget.md), 추가5는 [직전 공유/reader 기록](2026-10-03-source-shared-contrast-and-cumulative-read-budget.md)의 최종 SHA를 사용하며, 이번에 전체4,788개 historical closure를 다시 전수 인증했다고 주장하지 않는다. 별개 tracked5 사용자 변경도 그대로다.

최종 새5개 파일 SHA는 다음과 같다.

| 파일 | SHA256 |
|---|---|
| `src/musicanote_harness/shared_source_archive_bridge.py` | `5eadb642c0c7a6156f3f4fe895fc60261bf2e1ebc031dc788af2b6837aa0a091` |
| `tests/test_shared_source_archive_bridge.py` | `2343eb4a56f263874d9663e79ac42fff7e1ad5d1bc60abdb2fa99df6a01061ef` |
| `src/musicanote_harness/shared_source_progression_storage.py` | `72f50f1accdf952c55d1a4ead5b2307cdee09c1b6305b0d0732292d1f950f437` |
| `tests/test_shared_source_progression_storage.py` | `624ed635c6f099c7eeada2fb117c3c4949dd7dea4b0fc116c2fb050c917ddcb9` |
| `tests/test_shared_source_storage_integration.py` | `c3ba86f588432500c58f4971a46d781506fc12a8b3edf5f3d90503aa96113a96` |

Root 최종 QA는 **선행20+신규5의25SHA 변경0, 새5AST/8strict UTF-8 text/158local Markdown file link 오류0**, read-only `git diff --check` exit0다. 기존 tracked5의 LF→CRLF 경고만 남았다. 이번 새 corpus output·실제 full body join/pair·UI·Git commit/push·권한/설정 변경은0이다. 테스트는 임시 합성 파일만 만들며 원자료·과거 결과·Core/producer/운영 화면은 수정하지 않았다.

다음 큰 단위는 새 저장/읽기 계약을 통과한 **명시 자원 정책·파일별 비용 지도와 결과 독립 실제 pilot**이다. 이후 전체 대비의 비용과 후보 설명을 검토하고, 일반 음악 제약 기반 제안/보류 정책 및 전체 악보 검증으로 돌아간다. 기반 계약 검사 통과를 음악 정확도 개선이나 작곡·편곡 완료로 읽지 않는다.
