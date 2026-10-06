# 단계41 — Fresh 원 요청과 독립 pin을 이용한 남은 비교의 연속 실행

> 현재 상태: 구현·최종 검사·실제 선택 요청의 전체 비교 저장 완료. 2026-10-03 착수, 2026-10-04 종료. 파일명/기록 ID는 착수일을 유지한다. 전체 원 archive·최종 화성 선택·정확도·UI 완료는 아니다.

## 1. 목적과 음악적 범위

사용자의 “네”에 따라 [단계40](2026-10-03-transfer-bound-storage-and-fresh-request.md)의 남은 **19task/52,199pair**를 진행한다. 과거86task/239,356pair의 정상 저장을 전체 요청 완료로 고쳐 쓰지 않는다. 전체 선택 요청은1,710selector/5group/105task/291,555pair 그대로다. 전체 원자료4request/20group/1,652,640pair와 생략3request/15group/1,361,085pair도 보존한다.

이번 단위는 계산·저장의 안전한 연속 실행이다. 새 화성 이론, 작품별 정답, 후보 필터, 최종 winner, Core 변경을 추가하지 않았다. 조성·기능·NCT·지속/분산형·해결/종지의 음악적 대조는 같은 기존 pair JSON으로 유지된다. Pair 수는 화성 정답률이나 작품 수가 아니다. 음악적 선택·독립 주석 평가·전곡 화면 적용은 이후 단계다.

## 2. 새 구현과 신뢰 경계

- Library: [transfer_bound_storage_continuation.py](../../../src/musicanote_harness/transfer_bound_storage_continuation.py), `transfer-bound-storage-continuation-0.1.0`.
- Actual runner: [transfer_bound_storage_continuation_pilot_20261003.py](../../../tmp/transfer_bound_storage_continuation_pilot_20261003.py).
- Unit: [test_transfer_bound_storage_continuation.py](../../../tests/test_transfer_bound_storage_continuation.py).
- Explicit mocked runner controls: [test_transfer_bound_storage_continuation_pilot_runner.py](../../../tests/test_transfer_bound_storage_continuation_pilot_runner.py).

기존 v0.2 storage/coordinator/runner와 그 private registry는 변경하지 않는다. 새 Checkpoint/ContinuationPlan/ContinuationRun은 별도 owned registry와 process HMAC으로 발급한다. 공개 `record()`는 설명용 복사본이다. JSON/가짜 handle/기존 StorageRun은 continuation 권한이 아니다.

이어 실행에는 서로 다른 두 근거가 필요하다.

1. **독립적으로 확인한 이전 실행 report의 고정 SHA.** Actual runner가 단계40 root 관찰값 `a36cb92a7e4aaddbc6da2684a671d85ef0894bda4d436698c6b39e3a91bb864e`를 상수로 pin한다. Report 안의 자기 seal이나 나중에 공격자가 다시 계산한 SHA를 신뢰하지 않는다. API 호출자는 pin의 독립 출처를 보장해야 한다. 범용 API가 외부 신뢰 자체를 발명하지 않는다.
2. **원자료를 다시 읽고 검증한 fresh RequestPreparation.** 같은 source/catalog/group/refinement/entry inventory, 원 selector 순서, 모든 task와 원 전체/선택/생략 분모를 이전 receipt와 대조한다. 남은 계산은 새 owned group와 그 transfer proof만 사용한다.

이전 성공 artifact94개와 top-level 다른7개 및 pinned report1개의 경로·길이·SHA/정확 파일 inventory를 보호 입력으로 등록한다. 이전 block 본문 약800MB를 다시 decode/계산하지 않는다. 그 결과의 재사용 권위는 **외부에서 관찰된 frozen writer의 receipt + physical SHA + fresh identity binding**이다. 이를 이전 본문을 새로 음악적으로 검증했다거나 저장 JSON에서 실행 capability를 복원했다고 설명하지 않는다.

최소 지원 checkpoint는 기존 v0.2 writer의 **clean confirmed prefix**다. Held/computed-unpersisted/unknown/실패 task가 있으면 재사용을 보류하며 중간 hole이나 순서 바뀐 성공은 받지 않는다. 임의 snapshot, 다른 writer version, 여러 continuation chain의 일반 재개는 이번 구현의 완료 범위가 아니다.

## 3. 일반 실행 규칙

- 모든 원 group/task를 먼저 결합한다. 새로운 출력에는 남은 task만 원 순서대로 쓰며 중복·건너뛰기·재정렬·외부 task/bool index를 거부한다.
- Source/catalog는 확인된 과거 파일을 **borrowed input**으로 참조한다. 새 writer의 source/catalog 저장 수로 다시 세거나 출력 폴더에 복제하지 않는다.
- 새 destination은 원 archive와 이전 출력 밖의 새 폴더다. `xb` exclusive write·chunk 상한·완전 stream SHA·flush/fsync·물리 재확인을 사용한다. 기존 파일을 덮어쓰지 않는다.
- Pair 계산은 frozen `core.compare_block`을 호출하고 동일 validator로 exact ordered pair/source/task를 확인한다. Core-confirmed·persisted·held·unknown·아직 미계산을 따로 남긴다.
- 계산 전 실패는 known uncomputed, 계산 시작 뒤 반환 미확인은 unknown computation, 반환 확인 뒤 저장 실패는 computed-unpersisted다. 일부 성공을 전체 완료로 승격하지 않는다.
- Per-block current code guard는 provisional이다. 종료 전후와 종료 후 ledger 조회에서 원 입력·이전 결과·current code·새 출력 inventory를 전체 확인한다. 새 terminal manifest의 write/물리 확인이 끝나야 selected request 완료가 가능하다. 이후 파일 변경이 발견되면 완료를 철회한다.
- 저장 manifest는 자신의 write 성공을 스스로 증명하지 못한다. Actual report는 `finish` 뒤 다시 guard한 **더 늦은 owned ledger**를 기록한다.
- 600초 cooperative 예산은 atomic task 사이에서만 확인한다. 한 task의 hard runtime/RSS 제한이라고 주장하지 않는다.

## 4. 자원 계정

기본 cap은 늘리지 않는다. 이전 저장의 actual physical **827,880,027B**와 새 모든 남은 block 상계, 새 plan2MiB와 새 manifest16MiB를 **합친 논리적 저장 예약**을 기본2GiB와 비교한다. 기존 manifest가 새 manifest까지 포괄한다고 간주하지 않는다. 새 writer의 write byte 계정과 combined physical 계정을 분리한다. Pilot 관찰 JSON은 storage 실행의 출력 inventory와 별도이다.

Pinned report의3,085,719decoded B도 이번 실행에 다시 읽은 비용으로 계상한다. Original bootstrap4,058,934B와 fresh execution950,488,899B에 더하면 **957,633,552B<1GiB**다. 먼저 읽은 receipt를 fresh reader의 남은 cumulative allowance에서 차감한다. 물리 SHA I/O는 decoded JSON 계정과 별도다.

Receipt timing/memory의 finite float는 bounded metadata reader로 검사한다. 음악·작업 권위에 필요한 부분만 projection하여 no-float snapshot으로 보존한다. 원 자료의 유리수 음가·onset·pitch/tie를 변환하지 않는다. Metadata 크기/visit 측정과 encoding 작업을 별도로 예약하고 실제 manifest allocation 전에 상계를 확인한다.

## 5. 소형 검증과 실제 실행 상태

최종 신규 **31검사 PASS/315.429초**: genuine packet/physical continuation23개와 explicit mocked orchestration8개다. Complete checkpoint의0새비교, held Core, 계산 전 proof 실패, 계산 반환 미확인, short write, terminal 실패, 후속 파일 변경, manifest/전체 byte cap, finite diagnostic float projection/NaN 거부를 포함한다. Positive fixture에서 이전 registry 복원 없이 fresh request와 남은 pair의 저장 bytes가 `core.compare_block` 원 결과와 정확히 같았다. 기존 원자료 ancestry는 해당 소형 fixture에서 **명시적으로 mock**했으므로 실제 corpus 입증이나 음악적 정답 검증으로 쓰지 않는다.

기존 storage/coordinator/runner 회귀 **84개 중83 PASS +1 Windows symlink권한 SKIP/197.734초**. 최초15/189.335초와8/0.005초는 중간 subset 확인이며 최종31개에 더해 신규 검사 수로 세지 않는다. 선행 동결61파일 SHA 변경0, 새4Python AST·3문서 strict UTF-8/local link179개 오류0, `git diff --check` exit0을 확인했다. 별개 tracked5의 기존 LF→CRLF 경고는 유지한다.

Actual 명령:

```powershell
$env:PYTHONPATH = 'src;tests'
.venv/Scripts/python.exe -B tmp/transfer_bound_storage_continuation_pilot_20261003.py --output output/transfer-bound-storage-continuation-pilot-2026-10-03-r1
```

실제 실행은 원 요청/source1/completion0을 유지했다. Pinned prior102파일을 확인하고 original metadata/body를 다시 검증한 뒤 모든 새19task를 원 순서대로 실행했다. Fresh 전체 예약이1,109.0067865초에 반환됐고 reason0이다. 저장 단계에서 후보·음표·한도나 실행 중 코드/과거 outputs를 바꾸지 않았다.

### 실제 종료와 독립 재확인

- Status `selected_request_storage_complete_not_selected`, failure null, exit0. 전체 **1,275.8928276초**(약21분16초), continuation 저장 단계 **150.5114686초**다. 대부분은 fresh 전체 원 요청 검증·예약 비용이며19새 atomic task만 계산했다. 모든 이전 task를 새로 재계산한 것은 아니다.
- **새19task/52,199pair** 계산·저장 + **이전86task/239,356pair** trusted receipt 재사용 = **105task/291,555pair** 전체 선택 요청 저장 완료. 양쪽 computed-unpersisted/held/unknown/미계산0이며 최종 selected request integrity/physical closure/terminal manifest true다.
- 원 전체4request/570task/1,652,640pair 가운데 이번 완료는1request/105task/291,555pair다. 생략3request/465task/1,361,085pair는 이번에도 실행하지 않았다. Full archive 완료 false, 최종 winner/confidence/rank/musical outcome null이며 training/Gold/운영·UI false다.
- 새 writer 출력은 **21파일**(block19 +run plan1 +manifest1)/**149,794,182B**다. 이전 storage94파일/827,880,027B와 합쳐 **115storage 파일/977,674,209B**이며 원본 source/catalog는 이전 보호 입력으로만 참조한다.
- 새 출력 전체 예약 **206,319,188B**, 이전 physical을 포함한 combined 예약 **1,034,199,215B<2,147,483,648B**다. Combined actual977,674,209B≤예약이다. Manifest 사전 상계9,123,647B<16MiB, plan finalization 작업 상계37,132,085<1B다. 이전105block의 상계와 actual prefix를 섞어 모든 것이 재계산됐다고 보고하지 않는다.
- Receipt 포함 bootstrap7read **7,144,653decoded B** +fresh execution254read **950,488,899B** = **957,633,552B<1GiB**다. Fresh execution254개 전부 완료했고 그 read terminal도 complete다. Source/NCT·기능 producer를 새로 replay한 것과 구별한다.
- Resource 이벤트65개, peak working set **5,174,620,160B**(약4.819GiB)다. Runtime/RSS hard bound나 음악적 성능 수치가 아니다. Actual runner current-code15개 모두 전후 SHA confirmed, changed/uncertain0. Continuation per-block current-code 보호는22개이며 전체 registered input 보호와 별도다.
- [Actual pilot-report.json](../../../output/transfer-bound-storage-continuation-pilot-2026-10-03-r1/pilot-report.json): **3,986,751B**, SHA256 `3be83bd74abaa5c7d149ba74cb75b7f47477fd9ed95c18e14e61f8b41bafb317`.
- Root가 이전 출력root102파일과 새 storage21파일, 실제 report의 외부8artifact를 별도로 SHA/길이/정확 파일 inventory 대조했다. 오류/누락/foreign0. New top-level9JSON은8,356,172B이며 pilot 관찰 파일이므로 storage 예약/21파일에 더해 완료 수를 세지 않는다. 종료 후 이전 frozen61+새4Python의 **65SHA 변경0**,4AST·3문서 strict UTF-8·최종181local links 오류0도 확인했다. 중간179link 확인과 최종181 확인을 새 기능 수로 합산하지 않는다.

실행 중 Windows `Get-Process`로 시작 시각23:40:57.666+09:00과 CPU1,047.875초를 관찰했다. 이는 실행이 계산 중임을 확인한 보조 진단이며 후보별 진척도·음악적 검증이 아니다. 권한/설정 변경은 하지 않았다. 날짜가 자정을 넘었어도 같은 run이며 이전 파일을 새 날짜로 이동하거나 다시 만들지 않았다.

## 6. 결정과 다음 큰 단위

이전 정상 결과를 재계산하지 않고 새 요청 권한 아래 결합하는 방향을 채택했다. 원 후보·이론 근거·음표·주석·기본 cap은 보존했다. Actual terminal과 독립 physical 재대조 모두 통과하여 **이번 선택 요청의 전체 비교 저장**을 완료로 판단한다. 단계40 partial 결과는 수정하거나 소급 완료로 바꾸지 않는다.

이번4Python snapshot SHA:

| 파일 | SHA256 |
|---|---|
| transfer_bound_storage_continuation.py | `2265f31a76068a1aa29b778e5556f9f3d19b6733374297d04d6f3117fee4dbc6` |
| transfer_bound_storage_continuation_pilot_20261003.py | `11b94439a5e5fd6a54406a026cbf2eefd1a1db63b29d7af422d1ca43faf22459` |
| test_transfer_bound_storage_continuation.py | `9c55bbf9d7973d09b9836927299e1f794d63facc2a4af20d0dd1c82b0753c126` |
| test_transfer_bound_storage_continuation_pilot_runner.py | `7b2bdc80a413c87a4b35b4e53f6c766744c3a0dec1e9af0199a4815433299fd3` |

선택 요청의 모든 비교가 저장되어도 전체 원 cohort나 최종 화성 엔진 완료는 아니다. 다음 큰 단위는 **완전한 공동 비교 결과에서 후보 선택에 필요한 음악적 증거의 충족/충돌을 점검**하고, 조성·적용화음·기능·종지의 가설을 연결하여 독립 원주석 대조로 가는 것이다. 설명 길이·저장 성공·기술 검사 수로 winner를 정하지 않는다. 다른 요청 확대와 전체 악보 표시도 완료된 범위를 분명히 남긴 채 진행한다.

Git commit/push·운영5173·서버·Core·주석 수정은 이번 요청에 포함하지 않는다. 개발 문서는 `docs/harmony`에 별도로 유지하며 인수인계 문서를 새로 만들지 않는다.
