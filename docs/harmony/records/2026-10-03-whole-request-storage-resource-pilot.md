# 단계38 — 실제 원 요청의 전체 저장 예약·자원 검증

화성 분석의 **개발 문서**다. [메인 문서](../README.md), [개발 로그](../DEVELOPMENT_LOG.md), [단계37](2026-10-03-proof-v2-streaming-storage-and-whole-request.md)과 연결한다. 원XML/Core/주석·기존 분석기·과거 결과는 수정하지 않는다.

## 전체 계획에서의 위치

7개 큰 기능 중 현재 집중 단위는 **3. 여러 화음 진행의 공동 비교와 탐색**이다. 1(IR 입력·추적)과2(문맥 후보/NCT/분산형/베이스)의 연구용 기반을 연결했으며,4(조성·Secondary·기능·종지)도 연구용 전제를 구현했지만 최종 해석 선택과 통합 검증은 남아 있다. 5(다양한 작품·편성의 독립 정확도 평가),6(새 엔진의 전곡 악보 화면),7(구조 분석·작곡편곡 연결)의 완료를 선언하지 않는다.

원 P0–P13 계획에서는 P5/P6 개발과 P4 검증에 해당한다. 작곡·편곡 로드맵은 G0 기반과 G1 일부 연결이며 생성기 G2–G6 완료가 아니다. **화성 엔진 기반은 중간 지점에 가깝지만, 안정적인 자동 화성 분석이나 전체 작곡·편곡 목표의50% 완료를 뜻하지 않는다.** 작업 난도·검증 범위가 다른 기능의 개수, 단계38이라는 번호, 검사/후보 수로 퍼센트를 계산하지 않는다. 통합 계획 §16의 과거 상태는 이력이며 현재 상태는 최신 개발 기록을 따른다.

## 실행 전 범위와 결정

- 같은 byte-only selection `(source_index=1, completion_index=0)`을 유지한다. 음악 결과가 좋은 후보를 새로 고르지 않는다.
- 원 전체4completion/8,050selector/504batch/20group/1,652,640pair/570task, 선택1/1,710/107/5/291,555/105, 생략3/6,340/397/15/1,361,085/465를 보존한다. 곡 수가 아니다.
- 원40metadata·선택107batch의214body 전체를 fresh SHA/inventory/원순서로 admission하고, coordinator가 iterator exhaustion·모든 원 group·read terminal을 확인한다. 과거 report/JSON으로 핸들을 복원하지 않는다.
- Source-once 및5group 전체/105task의 저장 byte/work 상계를 **비교 전** 계산한다. Source/catalog256MiB, block64MiB, output2GiB 및 기존 group/source work 기본 한도를 높이지 않는다.
- 전체 상계에 보류가 있으면 `begin_storage`/비교를 호출하지 않는다. 확인되지 않은 전체 상계는null, 확인된 partial 계정은 별도다. 후보·원분모를 줄여 fit로 바꾸지 않는다.
- 전부 통과한 경우에만 원순서 atomic block으로 비교·저장한다. 실행기에 고정한600초는 **storage 단계의 block 호출 사이 cooperative stop**이다. 한 block 내부·admission/planning·terminal guard의 최대 실행시간 보증이 아니다. 중단하면 uncomputed/unpersisted 범위와 원 전체 분모를 남긴다.
- `finish` 뒤 같은 owned plan의 `request_ledger`를 확인하고 더 늦은 postterminal guard snapshot을 정본으로 쓴다. 부분 저장·unknown·guard오류를 완료로 승격하지 않는다. 최종 화음/winner/confidence·학습/Gold/UI는 별도다.

## 추가 파일과 검사

- [실제 실행기](../../../tmp/proof_shared_request_storage_pilot_20261003.py): 동결 선행 helper를 읽기 전용으로 재사용하며 새 output만 생성한다.
- [실행기 통제 검사](../../../tests/test_proof_shared_request_storage_pilot_runner.py): 최종 고유29개 PASS, 작성0.023초/root0.019초다. Closed-six 분모·정확한 integer·전체 task/pair coverage, 알려진 저장 예약, whole hold에서 API미호출,600초 block사이 중단, same-owned request join, failure/unknown/null와 더 늦은 guard snapshot을 검사한다. **명시적 mocked API 검사**이며 실제 corpus admission/음악 정확도와 구별한다.
- 기존 `test_cross_batch_read_budget test_native_progression_contrast`52개/18.194초 PASS다. 재검사를 새로운 고유 검사 수로 더하지 않는다.
- 독립 실행기 계약 감사의2개 권고(시작 전 full reservation·전체 task/pair coverage 확인, request join의 postterminal snapshot 사용)를 반영했다. 음악적 판정/후보 삭제/한도 증가는 없다.
- 초기 root23검사 중1실패 및 작성 중29검사의4실패는 최신 join snapshot/coverage 형식과 mocked fixture가 어긋난 상태의 중간 실행이었다. Fixture를 바로잡고 최종29개를 통과했으며 실행기 검증을 약화하지 않았다. Root가 잘못 지정한 존재하지 않는 `test_native_progression_completion`은 loader error였고, 같은 명령의 scoped runner14검사는 통과했다(합계15/77.241초,exit1). 올바른 기존52개 명령을 별도로 다시 실행했다. 이 중간 실행을 성공 suite나 추가 고유 수로 세지 않는다.

최종 신규 SHA256:

| 파일 | SHA256 |
|---|---|
| `tmp/proof_shared_request_storage_pilot_20261003.py` | `4574debfff421b6fca825c7868ab592147c8b86a0cbe66e1876552ce5d484d2f` |
| `tests/test_proof_shared_request_storage_pilot_runner.py` | `27afb841e59fba95eefa251571ff236cb51347945662f8c54f9e1bdf4f68606d` |

기존 동결49SHA의 실행 전 변경0을 확인했다. 별개 tracked5 사용자 수정은 보존한다.

## 이번 결과

실제 실행을 완료했다. **원 요청의 읽기·5group 준비 및105task 저장 상계는 확인됐지만, 전체 output 예약이 기본2GiB를 넘어서 비교·저장은 시작하지 않았다.** 유일한 보류 이유는 `whole_output_reservation_exceeds_limit_no_prefix`다. 실행기 exit0은 이 보류를 정상적으로 기록했다는 뜻이지 저장/화성 분석 완료가 아니다.

| 항목 | 실제 결과 |
|---|---|
| 선택 범위 |1completion/1,710selector/107batch/5group/291,555pair/105task |
| 전체 output 보수 예약 |3,881,314,476B, 약3.615GiB; `output_reservation_complete=true` |
| 기본 전체 한도 |2,147,483,648B; 초과1,733,830,828B |
| source-once 예약 |82,408,563B; canonical 교환 길이82,393,428B, 아직 디스크 source 저장은 아님 |
| local catalog 예약 합 |64,758,220B |
| 모든 block 예약 합 |3,715,273,325B; group마다743,054,665B |
| plan + manifest 예약 |2,097,152 +16,777,216 =18,874,368B |
| 각 block |105개 모두 상계 확인·개별64MiB 통과;2,978,454~52,815,024B |
| 실제 비교/저장 |pair0, storage 시작false, `comparison-storage` 미생성 |
| 실제 경과/메모리 |1,055.972411초,37관찰, process peak working set5,164,068,864B(약4.809GiB) |

예약 산술은 `82,408,563 +64,758,220 +3,715,273,325 +18,874,368 =3,881,314,476`이다. 이는 **보수적인 schema 상계의 합**이며 실제 비교 JSON이3.88GB 생성됐다는 뜻이 아니다. 소형 fixture의 압축률/출력률을 실제 자료에 외삽하지 않는다. 각 block이 개별 통과해도 전체 예약이 실패하면 prefix를 실행하지 않는다.

5group 모두342entry/58,311pair/21task·69atoms/23,598vector cells를 유지했다. Core whole work는888,143,168/888,845,940/889,226,932/890,230,520/865,341,814로 기본1B 안이다. 추가 stream planning은 group마다332,002,224~332,002,638, source planning89,177,616이며 이전 core1B에 포함된 비용으로 주장하지 않는다. Plan finalization11,199,395=measurement4,827,352+serialization6,372,043, coordinator6,085,194도 별도다. Manifest byte 상계8,954,585B<16MiB다. Runtime stream/manifest 실제 실행 비용은 이번에 발생하지 않았다.

### 읽기·보호·완료 진실

Bootstrap6read의4,058,934decoded B와 execution254read의950,488,899B를 함께 계상하여954,547,833B<기본1GiB다. Execution은 원40metadata+107batch의214body를 전부 읽었으며 planned/attempted/completed254, failed/held/never0이다. Source2bundle/136catalog/7,285origin/53sounds/5key와 원분모를 보존한다. 선택1,710은 곡·정답 수가 아니다.

Execution physical83,105,354B와 bootstrap4,058,934B(합87,164,288B)는 decoded와 별도다. 읽기 guard physical SHA 시도는 execution5,932,412,271B/19,487회, bootstrap35,240,176B/146회다. Storage planning current-code hash502,836B/14회도 별도 계정이다. 전체 file I/O를 decoded 한도 안에 든 비용이라고 해석하지 않는다.

Read terminal finished/body join/read-set complete=true, failure/body_failure=null이며 current13code 변경·미확인0이다. 원 old scoped reader의 intrinsic/prepared는false/0 그대로다. 새 v2 준비5개와 이를 혼동하지 않는다. Writer plan의 보호5829files와 기본 정책을 coordinator가 연결했으나, output hold 때문에 writer begin/terminal full closure는 실행하지 않았다. **저장된 대비0·winner/최종harmony/NCT/key/cadence·음악 정확도·UI/구조/생성·학습/Gold 승격0**이다.

### 출력과 재현

- 실행: `PYTHONPATH=src;tests`에서 `.venv/Scripts/python.exe -B tmp/proof_shared_request_storage_pilot_20261003.py --output output/proof-whole-request-storage-pilot-2026-10-03-r1`.
- [실제 report](../../../output/proof-whole-request-storage-pilot-2026-10-03-r1/pilot-report.json), [완전 요청 준비](../../../output/proof-whole-request-storage-pilot-2026-10-03-r1/whole-request-preparation.json), [저장 미시작 사유](../../../output/proof-whole-request-storage-pilot-2026-10-03-r1/storage-execution.json).
- 정확8JSON/4,491,663B. Report2,044,550B와 나머지7artifact의 physical SHA/bytes는 독립 감사로 확인한다. Report SHA256: `0a1efb6a53451af978817fd62bf25db81cbca0ef4e8c2fe4df1976eb828a2398`.
- 신규2파일은 실행 중 변경하지 않았고 원자료/기존 결과/Git/서버·운영 화면은 변경하지 않았다. 원 한 요청의 점검 결과이며 전체4completion/8,050후보 완료가 아니다.

## 결과에 따른 다음 설계 결정

전체 예약의 약95.7%가 **105block의 보수 상계**다. Source/catalog만 줄여서는1.73GB 초과를 해결할 수 없다. 결과 이전에는 assumption 중복도 후보 원인으로 검토했지만, **실제 descriptor와 코드식을 대조하니 우선 원인은 category-transfer의 전체 종류 조합 상계**였다. 추정을 실제 측정과 구별하고 우선순위를 수정한다.

현재6종류 category의 모든36조합을 pair마다 예약한다. 최대 category 문자열45B×양쪽, rational142B, field/syntax39B로 한 item271B이고 array 상계9,793B다.291,555pair에서 이 항목의 보수 예약만 **2,855,198,115B**, 모든 block 상계의 약76.8503%다. 그 안의 rational 폭 반복1,490,429,160B·category 문자열944,638,200B·나머지 syntax420,130,755B를 구별한다. 이는 실제 pair 결과를 계산한 양이 아니라 현재 schema 상계 공식의 분해다. 독립 감사의 최초 합계2,855,200,115B 표기 오타는2,855,198,115B로 정정했다.

다음 큰 단위는 **후보를 유지한 category-transfer 지원 집합 증명과 정확한 유리수 상계**다.

1. 각 owned entry의 실제 source rows에서 나타날 수 있는 category 집합을 사전예산으로 검사한다. Pair의 transfer 조합 상계는 왼쪽/오른쪽 지원 집합의 Cartesian product와 sound atom 수로 제한한다. 최종 역할/화음 선택이나 pair 계산을 먼저 하는 것이 아니며, 실제로 발생 가능한 transfer를 빠뜨리지 않는 proof/반례부터 검사한다.
2. Endpoint inventory에 묶인 **예산 제한 gcd/LCM proof**와 numerator magnitude 상계를 검토한다. 현재 반복되는 모든 분모의 곱 폭은 유효하지만 느슨할 수 있다. Bigint 작업량/메모리를 계산 전에 제한하며 max denominator·float·일반 음악 추측값으로 낮추지 않는다.
3. 위 두 큰 항목을 먼저 개선·검증한 뒤 잔여 병목이 있으면 transition assumption 본문을 catalog-bound cut/node reference로 저장하는 별도 codec을 검토한다. 참조는 정확한 catalog/refinement/source에 묶이고 원 legacy pair·canonical SHA를 정확히 재구성해야 한다. 기존 frozen codec의 의미를 바꾸지 않는다.

실제 개선폭/새2GiB fit은 아직 미확인이다. 결과를 먼저 계산해 평균 byte로 admission하거나 압축률 표본을 정답처럼 쓰지 않는다.

이후 같은 원 한 completion을 새 default 전체 상계로 재검증하고 통과하면 대비를 저장한다. 단순한 기보/특정 작품 예외를 더하는 단위가 아니다.1,055초의 admission/계획 비용은 운영 화면용 성능과도 별도 검증이 필요하다.

## 화성 주석은 어디까지 검증 기준인가

사용자가 이번 실행 중 확인한 질문을 기록한다. **주석을 기준으로 대조하는 기존 평가 부분은 있지만, 최근 단계38은 주석 일치/음악 정답률 검사가 아니다.** 계산·보존 계약, 후보 근거의 전제 성립, 수입 주석과의 일치, 실제 음악 해석의 타당성을 구별한다.

- [기존 DCML surface diagnostic](../../../src/musicanote_harness/harmony_surface_eval.py)은 분석기에 정답 주석을 주지 않고 scorer에서만 주석을 읽는다. 정렬 승인된 일부 단순 로마자 화음의 완전한 beat를 대상으로 **pitch-class template 일치**를 대조한다. 전위·Secondary·NCT·국소 조성·종지 전체 정확도 검사가 아니다.
- [기존 case retrieval 평가](../../../src/musicanote_harness/harmony_case_retrieval_eval.py)는 주석의 raw label/화음 family와 검색된 사례의 label을 비교한다. 사례 검색 성능이며 새 악보에서 경계를 찾고 전곡 화성을 선택하는 end-to-end 정확도로 환산하지 않는다.
- [분산형 통제 benchmark](../../../src/musicanote_harness/harmony_arpeggio_benchmark.py)는 작성된 합성 악보의 의도·표현 불변성을 검사한다. 실제 corpus의 유일한 정답 주석이나 음악 정확도가 아니다.
- 이번 원1,710후보/105task 실행은 source/ID/시간/음가·근거 보존과 비용/저장 예약을 검사했다. 새 joint 엔진의 최종 해석과 주석을 전곡으로 대조한 결과는 아직 없다.

후속 음악적 평가는 분석/사례 검색용 자료와 평가용 작품 가족·주석 계보를 분리하고, 검증할 악보 자체의 정답 주석을 분석 입력으로 사용하지 않는 blind 모드를 기준으로 한다. 예측 구간/화음/전위/국소 조성·Secondary/종지의 일치를 각각 보고하고, 원 주석의 누락·오류·복수 해석은 원음표·철자·베이스·해결 문맥과 human correction으로 별도 검수한다. 주석과 다르다는 이유만으로 반드시 오답으로 확정하지 않으며, 미지원 축은 제외 분모/보류로 공개한다. 이는 다음 평가 설계 기준이며 이번 단계의 정확도 구현 완료가 아니다.

## 독립 검수와 최종 보호

독립 actual 결과 감사는 새8JSON·등록7artifact의 SHA/bytes·정확한 output 목록과 예약 산술, 원/선택/생략 분모,105task 상계·별도 work/read 비용·보류 및 미승격을 확인했다. 추가 차단0이며 원 body replay/음악 정답 심사를 수행한 것은 아니다. 최대 pair 상계13,013B도 기존4MiB 안이다.

최종 기존49동결SHA 변경0, 신규runner/test SHA는 위 정본과 동일하며 read-only `git diff --check` exit0이다. 기존 tracked5수정 및 그 LF→CRLF 경고는 그대로 유지했다. 최종 문서 UTF-8/로컬 링크·신규2AST 검사 결과는 개발 로그에 반영한다. Source/core·실제 결과 파일은 수정하지 않는다.

## 다음 큰 기능

전체 예약이 통과하면 동일 원 요청의 대비 근거를 끝까지 저장·검증하고 음악적 선택 정책으로 연결한다. 보류라면 결과를 보고 **저장 표현/보수 상계의 구조적 비용**을 우선 개선한다. 작은 음악 사례별 예외, cap 증가, 좋은 prefix, 불확실한 압축률로 우회하지 않는다. 그 뒤 조성·해결·NCT의 통합 판단을 다양한 작품에서 검증하고 전체 악보 화면에 연결한다.
