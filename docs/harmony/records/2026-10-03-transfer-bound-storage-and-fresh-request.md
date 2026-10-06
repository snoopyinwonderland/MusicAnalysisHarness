# 단계40 — 지원 집합·정확한 유리수 상계의 저장 연결과 실제 요청 재검증

## 1. 목표와 현재 상태

단계39의 `proof_shared_transfer_bounds`를 실제로 소비하는 별도 versioned 저장 실행기를 만든다. 원 후보·음표·타이·철자·유리수 음가·pair JSON을 유지하면서 **전체 저장 예약이 기본 한도 안에 들어갈 때에만** 비교와 물리 저장을 시작한다. 이전 실행기의 전역 함수를 교체하거나 저장 JSON으로 실행 권한을 복원하지 않는다.

2026-10-03 새 연결의 최종 검사와 소형 물리 저장, 같은 실제 요청의 fresh admission 및 전체 예약 재검증을 완료했다. **전체 예약은 기본 한도를 통과했고 실제239,356pair를 저장했다.**600초 cooperative 저장 예산에 따라19task/52,199pair를 남긴 정상 partial 결과다. 작은 예제의 성공이나 이 자원 검증을 전체 corpus·화성 정확도 성공으로 확대하지 않는다.

음악적 해석 선택, 화성 정답률, 구조 분석·작곡편곡 연결, 운영 악보 화면 적용은 이번 저장 검증의 완료 범위가 아니다. 특정 작품/마디에 한정한 조건은 추가하지 않는다.

## 2. 파일과 버전 경계

| 새 파일 | 역할 |
|---|---|
| [transfer_bound_progression_storage.py](../../../src/musicanote_harness/transfer_bound_progression_storage.py) | 새 지원 집합/LCM proof를 소비하는 source-once 저장 v0.2 |
| [transfer_bound_request_coordinator.py](../../../src/musicanote_harness/transfer_bound_request_coordinator.py) | fresh 원 한 요청의 전체 읽기·준비·예약과 같은 owned 저장 run 연결 v0.2 |
| [test_transfer_bound_progression_storage.py](../../../tests/test_transfer_bound_progression_storage.py) | 저장 회귀 통제와 새 연결 반례 |
| [test_transfer_bound_request_coordinator.py](../../../tests/test_transfer_bound_request_coordinator.py) | 원 요청 전체 범위·소유권·종료 결과 통제 |
| [transfer_bound_request_storage_pilot_20261003.py](../../../tmp/transfer_bound_request_storage_pilot_20261003.py) | 동일 실제 원 요청의 fresh 재검증 실행기 |
| [test_transfer_bound_request_storage_pilot_runner.py](../../../tests/test_transfer_bound_request_storage_pilot_runner.py) | 명시 mocked runner 통제 |
| [transfer_bound_storage_fixture_pilot_20261003.py](../../../tmp/transfer_bound_storage_fixture_pilot_20261003.py) | 합성 XML에서 실제 새 writer의 exclusive 물리 저장 관찰 |

앞의 storage/coordinator/actual runner 및 세 검사는 frozen 단계37/38 파일의 **별도 snapshot**으로 시작했다. 중복이 생기는 이유는 과거 파일 SHA·registry·실행 결과를 유지하기 위해서다. 신규 범용 구현을 기존 production에 적용하거나 과거 검사를 새 코드의 결과로 소급하지 않는다. 후속 안정화 때 공통 구현 추출을 별도 migration으로 판단한다.

버전은 `transfer-bound-progression-storage-0.2.0`, `transfer-bound-whole-request-coordinator-0.2.0`이다. 저장 plan/run은 서로 다른 private registry와 HMAC를 사용한다. 이전 `StoragePlan`과 새 plan의 JSON descriptor 어느 것도 새 저장 실행을 승인하지 않는다. Frozen core가 생성하는 compact pair/block의 의미·버전은 변경하지 않는다.

## 3. 일반 계약과 처리 순서

```text
fresh 원 한 completion의 전체 read/terminal 검증
  → 모든 owned source/group의 원 membership 확인
  → source·catalog serialization 상계
  → group별 support/LCM proof 한 번 준비
  → 같은 proof로 모든 task의 transfer-array 상계
  → source + catalog + 모든 block + plan + manifest 전체 예약
  → 한도 안일 때만 atomic compare / exclusive save
  → 입력·코드·출력 SHA / exact inventory 종료 검증
  → 같은 owned 요청과 더 늦은 terminal ledger 연결
```

- Group별 proof를 한 번 준비하고 정확한 같은 owned group에 묶어 plan에 보유한다. Task마다 proof를 새로 만들거나 결과를 보고 지원 집합을 좁히지 않는다.
- Proof 준비 작업량과 각 task의 inspection 작업량을 기존 group 저장 planning 예산에 함께 계상한다. Source planning, core 계산, stream serialization, 물리 SHA I/O, coordinator metadata 작업량은 서로 다른 계정이며 이를 모두 core의 한도 안에 포함됐다고 주장하지 않는다.
- 지원 집합은 모든 원 row 종류를 포함한다. Credit 0/null, 원음표의 의미가 미상인 row도 삭제하지 않는다. Exact LCM과 전체 sound-span 분자 상계만 사용하며 float onset·표본 압축률을 사용하지 않는다.
- 전체 output 2GiB, block 64MiB, source 256MiB, plan 2MiB, manifest 16MiB 및 기본 작업 한도는 유지한다. 새 `StorageLimits`는 모든 필드를 기본값보다 **낮추기만** 허용한다.
- Proof 준비가 보류되면 전체 원 선언·selector/task/pair 분모를 유지한다. 미확인 block/whole 상계는 null이며 가능한 prefix를 계산하거나 output directory를 만들지 않는다.
- 비교 직전 proof의 소유 group을 다시 확인한다. 비교 호출 전 실패는 `interrupted_before_comparison`이며 미계산 수가 알려진 상태다. 비교를 시도한 뒤 반환이 확인되지 않은 경우의 unknown computation과 구별한다.
- 새 bounds module도 current-code protection에 포함한다. Terminal 전체 input/output closure 전 persisted count는 provisional이며 저장 manifest가 자기 자신의 성공을 인증하지 않는다.
- 같은 원 요청의 coordinator가 더 늦게 수행한 postterminal storage guard를 최종 snapshot으로 사용한다. Full original archive 완료는 별도이며 이번 선택 요청 완료로 승격하지 않는다.

## 4. 검사·교정 이력

중간 연결 검사는 **77개/158.626초, 실패0·Windows symlink 권한 SKIP1**이었다. 실행 중 pre-comparison 중단 기록과 proof 준비 보류의 작업 계상을 보완했으므로 이 중간 검사를 최종 revision 인증으로 사용하지 않는다.

추가한 직접 반례 7개는 **37.165초 PASS**다. 최종 전체 suite에 포함되므로 추가 검사 횟수로 이중 합산하지 않는다.

1. 모든 storage limit의 기본값 초과 거부.
2. 이전 plan/new JSON의 새 writer 실행 거부와 output 미생성.
3. Group proof 준비 1회·모든 task 동일 proof·준비/inspection 작업의 정확한 합산·bounds code 보호.
4. 작은 같은 후보 집합에서 구 whole hold를 새 예약으로 해소하되 한도 증가·후보 생략 없이 모든 pair 저장.
5. 명시적으로 주입한 proof preparation work hold에서 원 분모 유지·상계 null·비교/출력0.
6. 명시적으로 주입한 비교 전 proof binding 실패에서 계산0·unknown computation0·미계산 task 전체 유지.
7. GC를 끈 상태에서도 plan 해제 후 proof가 남지 않는 수명 통제.

최종 신규 suite는 저장35+coordinator20+runner29의 **84개**다. 저장/coordinator/runner의 기존 77개 통제는 새 연결로 이식한 통제이고 새 직접 반례는 7개다. Coordinator ancestry와 runner API는 명시적으로 mock한 검사이며 실제 corpus admission은 아래 별도 실행에서만 판단한다. Windows symlink 검사가 skip되면 해당 OS 동작 검증을 완료로 보고하지 않는다.

최종 전체 suite는 **84개/194.668초, 83 PASS +1 Windows symlink 권한 SKIP**다. 별도 기존 transfer bounds21+streaming16+proof core34의 **71개/106.875초 PASS**도 확인했다. 실행 중 소형 pilot와 actual admission이 병행됐으므로 시간을 직전 단독 실행과 직접 성능 비교하지 않는다. 중간77개·직접7개 재검사는 최종84개에 중복 합산하지 않는다. Root 검수이며 이전 독립 감사의 승인 결과를 새 revision에 소급하지 않는다. Final QA는 아래 보존 절에 기록한다.

## 5. 작은 XML의 실제 물리 저장

명령:

```powershell
$env:PYTHONPATH = 'src;tests'
.venv/Scripts/python.exe -B tmp/transfer_bound_storage_fixture_pilot_20261003.py --output output/transfer-bound-storage-fixtures-2026-10-03-r1
```

합성 XML **2group·5entry·4pair**의 source/catalog/block/manifest를 새 writer로 저장했다. Historical ancestry나 coordinator를 mock하여 실제 admission으로 주장한 실행이 아니다. 이 실행에서는 coordinator 자체를 사용하지 않았으며 이전 writer는 상계만 계획했다.

- 구 block 상계: **25,961B**.
- 신 block 상계: **19,526B**.
- 실제 저장 block: **16,683B**, 새 상계 이내.
- 전체 output 예약: 구 **26,203,087B**→신 **26,196,652B**, 실제 physical output **7,351,094B**. Plan/manifest 예약은 기본값 그대로다.
- Persisted pair: **4/4**, owned terminal의 제출 group 집합 저장 완료.
- 시간: **26.5114015초**, exit0.
- Report: [report.json](../../../output/transfer-bound-storage-fixtures-2026-10-03-r1/report.json), **89,659B**, SHA256 `d47a89c4c06691b57612b8cd7eaeaf2662ce24136ba3f498d3b60cd19e939d8a`.
- 새 코드·fixture·runner의 전후 SHA와 actual physical output closure를 확인했다. Full corpus·음악적 정답·UI 적용의 의미는 없다.
- 별도 root 확인에서도 물리 파일10개의 길이·완전 stream SHA가 모두 일치했고 합계7,351,094B였다.2개의 source는 각각 한 번 저장했고 local catalog2개·block4개·run plan/manifest를 포함한다.

Whole 예약에는 block 외 source/catalog와 plan/manifest가 포함되므로 block 절감률을 전체 예약의 절감률로 쓰지 않는다. Report 자체는 pilot 관찰 파일이며 저장 run의 예약과 output inventory 바깥에 있다.

## 6. 실제 원 요청의 fresh 재검증

실행 명령:

```powershell
$env:PYTHONPATH = 'src;tests'
.venv/Scripts/python.exe -B tmp/transfer_bound_request_storage_pilot_20261003.py --output output/transfer-bound-whole-request-storage-pilot-2026-10-03-r1
```

선정은 단계34부터 동일한 **byte-only source1/completion0**이며 화성 결과나 유리한 상계를 보고 바꾸지 않았다. 새 run은 이전 JSON에서 capability를 재생성하지 않고 original metadata/body·read terminal을 다시 검증한다.

| 원 분모 | 전체 | 선택 요청 | 생략 요청 |
|---|---:|---:|---:|
| completion requests | 4 | 1 | 3 |
| selector occurrences | 8,050 | 1,710 | 6,340 |
| batches | 504 | 107 | 397 |
| groups | 20 | 5 | 15 |
| pairs | 1,652,640 | 291,555 | 1,361,085 |
| block tasks | 570 | 105 | 465 |

이는 작품 수가 아니라 저장 요청·후보 비교의 분모다. 선택 원 데이터의 문맥은 2개 context/7개 raw lane이며 전체 원 cohort는 322context/1,013raw lane이다. 일반화 검증에 충분한 작품 수라고 주장하지 않는다.

실제 전체 예약은 **1,067.1329381초에 반환**됐다. Reason0이며 기본 한도를 통과하여 실제 atomic 비교·저장이 시작됐다. 종료 결과는 아래와 같으며 전체 비교 완료는 아니다.

| 예약 항목 | 단계38 | 단계40 |
|---|---:|---:|
| Source-once | 82,408,563B | 82,408,563B |
| Local catalog 합계 | 64,758,220B | 64,758,220B |
| 전체105 block 상계 | 3,715,273,325B | 1,041,833,105B |
| Plan+manifest | 18,874,368B | 18,874,368B |
| Whole 예약 | 3,881,314,476B | **1,207,874,256B** |
| 기본 output limit | 2,147,483,648B | 2,147,483,648B |

같은 모든 후보/음표에서 전체 예약이2,673,440,220B 줄었다. 단지 저장 상계의 정교화이며 분석 결과·후보·주석 정확도 향상을 의미하지 않는다. 각 group342entry 중12개는1종류,330개는2종류의 지원 집합을 갖는다. Category 조합은 모든 pair의 임의36개 대신 최대4개가 가능함을 증명했다. Sound endpoint106개/53sound atom의 LCM2·전체 span 분자 상계53으로 rational JSON폭32B를 증명했다. 이 값들은 결과 전 owned 원 row/endpoint에서 얻었고 최종 role/NCT 선택이 아니다.

각 group의 proof 준비 작업량은609,679이며 **한 번만** 계상했다. 추가 task inspection을 포함한 저장 planning 작업은362,469,823~362,470,237로 기본1B 안이다. 최댓값 block 상계15,244,676B<64MiB, pair 상계3,869B도 기본값 안이다. Source/catalog/pair/body 저장에서 데이터 제거·cap 증가는 없었다.

저장 단계의 **600초 예산은 atomic block 사이에만 확인하는 cooperative 중단 기준**이며 한 block의 runtime/RSS 상한이 아니다. 시간 예산에 도달하면 이미 계산한 결과와 전체 미계산 task를 남기는 partial 결과로 기록한다. 그 부분을 완료나 새 요청의 유리한 prefix로 승격하지 않는다.

### 실제 종료 결과

- Status `partial_storage_wall_budget_reached`, failure null, exit0. 총 **1,702.1672661초**(약28분22초), storage elapsed **629.6710309초**다. 마지막 atomic block 반환과 종료/추가 guard를 포함하므로600초의 hard wall upper bound로 해석하지 않는다.
- **86/105task·239,356/291,555pair 계산·저장**, computed-unpersisted/held/storage-held/unknown-computation 모두0. **19task·52,199pair 미계산**이며 원 분모와 task 범위를 그대로 남겼다.
- 앞4group은 각58,311pair/21task 모두 저장, 마지막 group은6,112pair/2task를 저장했다. 마지막 group의 나머지52,199pair/19task는 미계산이다. Group 순서는 원 선언 순서이며 유리한 결과를 골라 진행한 것이 아니다.
- Source1·local catalog5·block86·run plan/manifest의 물리 **94파일/827,880,027B**, 전체 예약1,207,874,256B 이하. 물리 해시/정확 inventory/입력·출력 보호 closure 통과, 오류·미확인 guard·unknown physical output0이다.
- Owned terminal의 `storage_integrity_passed`/`physical_closure_verified_terminally`는 true지만 `all_planned_pairs_computed`/`submitted_group_set_complete`/`selected_request_storage_complete`는 false다. 같은 원 요청의 storage coverage는 true이며 full original archive 완료는 false다.
- Bootstrap6read **4,058,934decoded B** +execution254read **950,488,899decoded B** =**954,547,833B<1GiB**. Execution254read 모두 완료했고 failed/held/never0이다. 물리 SHA I/O·serialization/planning 작업은 별도 계정이다.
- Resource 관찰145개, peak working set **5,169,995,776B**(약4.815GiB). 이는 process RSS의 실제 관찰이지8MiB proof retained logical 한도나 output2GiB의 메모리 보장이 아니다. 직전 peak5,164,068,864B보다 메모리가 줄었다고 주장하지 않는다.
- Actual current-code14개 전후 SHA 모두 확인, changed/uncertain0. 원자료·Core·주석·old registry·과거 결과·winner/UI/구조/생성·학습/Gold 변경0이다.
- [실제 pilot-report.json](../../../output/transfer-bound-whole-request-storage-pilot-2026-10-03-r1/pilot-report.json): **3,085,719B**, SHA256 `a36cb92a7e4aaddbc6da2684a671d85ef0894bda4d436698c6b39e3a91bb864e`. Root가 report의7개 외부 artifact와94개 storage 파일의 길이/SHA를 별도로 대조했고 불일치0, top-level8JSON 합계6,514,014B다.

일부 tool stdout은 토큰 한도로 잘렸지만145개의 원 resource/atomic 이벤트는 실제 report에 모두 남았다. 요약값은 stdout의 마지막 몇 줄이 아니라 final report와 파일 대조에서 확인했다. 본문의 반환된 owned terminal과 저장 manifest의 self-certification 불가 계약을 유지한다.

## 7. 원자료 보존과 동결

선행49+단계38 actual runner/검사2+단계39 신규3의 **54개 frozen 파일 SHA 변경0**을 실제 실행 착수 전에 확인했다. 원XML/Core/주석·이전 저장 실행기/registry·과거 outputs·별개 tracked5 사용자 변경은 유지한다. Git commit/push, 권한·Codex 설정·서버·운영 UI 변경은 요청 범위에 포함하지 않았다.

실제 실행 중 새7Python의 AST와3개 개발 문서의 strict UTF-8·local link180개를 확인했다. 종료 결과를 반영한 최종 QA에서도 **7AST/3문서 strict UTF-8/183local links** 오류0, 누락 링크·replacement/zero-width 문자0, read-only `git diff --check` exit0이며 기존 tracked5의 LF→CRLF 경고만 유지한다. 종료 후에도 선행54+새7의61SHA 변경0, actual 외부7artifact/storage94파일 길이·SHA 오류0을 확인했다. 같은 검사/QA 재실행을 신규 고유 검사 수로 더하지 않는다.

보조 `Win32_Process` CIM CPU 조회는 Windows 접근 거부로 실패했다. 권한 상승·설정 변경 없이 생략했고 작업은 정상 종료했다. 이후 pilot 생성 시각과 일치하는 `Get-Process` 관찰에서 CPU 시간을 확인했지만 이를 음악적/작업별 진척도 측정으로 쓰지 않는다.

이번 새 7파일의 동결 SHA:

| 파일 | SHA256 |
|---|---|
| transfer_bound_progression_storage.py | `f124b332be4425167691566f8d70750a5d1aa8f3f673efd98b0dca750a51ec43` |
| transfer_bound_request_coordinator.py | `433a8b32146b5a179d3adf40be32827a967cd1cb1abdc9ae110d6396f28d610d` |
| test_transfer_bound_progression_storage.py | `dcefe23ab5dfa53aa6ee6dd9c4e53f6a46bab672ca40e3e7f92f13da27263136` |
| test_transfer_bound_request_coordinator.py | `f94aa9b7e90be7fa91f49be147101e34b15558b3d25309a8ddf82016249e93c4` |
| transfer_bound_request_storage_pilot_20261003.py | `7f8614152a60e609da65d4dc04a8faeaa5741f349bf813996ec91b039d70e5af` |
| test_transfer_bound_request_storage_pilot_runner.py | `33247cf385fe98f4b852c2904f658d584d18c464227e707b23a22746bb9bdc62` |
| transfer_bound_storage_fixture_pilot_20261003.py | `c333e099161db1161265a12c752cf5bcc6cd98bc24345c24b9d0d5395cb53a50` |

## 8. 다음 단계 결정 기준

1. 실제 전체 예약 fit은 확인했다. 새 음악 해석/정확도 결론으로 확대하지 않고 모든 원 후보·한도를 유지한다.
2. 다음은 남은19task/52,199pair를 포함한 **전체 요청의 안전한 연속 실행**이다. Authenticated reload/resume 또는 실행 자원 정책/성능 개선은 별도 versioned 단위이며 JSON만 읽고 완료 권한을 부여하지 않는다. 이번 일부 저장을 전체 요청 완료로 고쳐 쓰지 않는다.
3. 후보 공동 비교 완료 후에도 winner를 설명 길이로 정하지 않는다. 조성·기능·NCT·지속/분산형·해결/종지의 근거와 대안을 보존하는 음악적 선택 단계가 필요하다.
4. 작품군·주석 계보를 분리한 독립 주석 대조, 원음표 근거의 불일치 검토와 전곡 표시를 다음 큰 기능 단위에서 수행한다. 수천 기술검사/후보 통과를 화성 정답률로 사용하지 않는다.

선행 수식·증명과 실제 이전 hold는 [단계39](2026-10-03-category-support-and-exact-transfer-bounds.md), [단계38](2026-10-03-whole-request-storage-resource-pilot.md)를 참고한다.
