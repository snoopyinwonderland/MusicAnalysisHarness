# 공통 화성 문맥 통합과 제한된 마디 IR 교정

기록 ID: HARM-DEV-20260930-29

## 목적과 개발 우선순위

사용자는 세부 사례에 오래 머무르기보다 큰 기능을 먼저 완성하고 작은 문제는 나중에 보완하기를 요청했다. 이번 단계는 확인된 마디 정체성 오류만 제한 교정한 뒤, 기존에 구현한 후보·비화성음·분산형·베이스·해결 근거를 공통 문맥으로 연결한다. 새로운 source 감사 주제로 계속 확장하지 않는다.

음표·시간·ID 손상이나 평가 자료 유출처럼 계산을 무효화하는 문제는 먼저 해결한다. 미지원 장식음·성부·해석 충돌은 해당 판단의 보류로 남긴다. 같은 작품의 마디 번호·정답 라벨을 조건식에 넣지 않는다.

## 구현 계약

### 제한된 새 IR 후보

`source_physical_measure_revision.py` v0.1.0은 `revise(parent_ir, verified_replay_package)`와 `validate_revision(parent, candidate, sidecar)`를 제공한다. frozen replay·physical grid·event coverage를 재검증하고 중복 마디 ID에 한하여 다음을 교정한다.

- 중복 ID를 가진 각각의 physical measure에 새 결정론적 ID를 부여한다. 기존 ID와 sequential index의 qualified alias를 저장한다.
- 원 XML의 X1/X2/X3 표시 번호, 검증된 note/rest measure 참조와 local onset을 교정한다.
- 새 document ID와 전체 JSON-pointer diff, 보호 projection·입력/출력 hash를 저장한다.
- global onset, pitch, duration, 음표/쉼표/실음/attack/tie ID, 배열 순서 및 나머지 모든 필드는 보호한다.
- 마디 오른쪽 끝 grace는 global time이 다음 마디 시작과 같아도 원 physical measure 소속을 유지한다.

기존 주석은 부모 document에 남는다. 원 source locator와 extension은 이번 교정 범위 밖이다. 등록된 source-directions extension의 중복 measure 참조는 정확 pointer와 부모 binding을 sidecar에 남기고 byte-identical하게 보존한다. 이 후보를 standalone extension 소비에 사용해서는 안 된다. 다른 Core/미등록 extension의 모호한 참조는 별도 보류한다. 원자료·production parser·Core schema를 변경하지 않는다.

이전 source-locator revision 26개와 이번 physical-measure 후보는 서로 다른 revision이다. 둘을 결합하거나 기존 annotation을 자동 재지정하지 않았다. 순서로만 재현되는 동일 occurrence도 독립 인증으로 승격하지 않는다.

### 공통 문맥 계산 묶음

`harmony_context_bundle.py` v0.1.0의 `bundle(ir, stored_sample, path_requests=())`는 기존 continuous/contrast/lattice/relations/hold_change 결과 전체를 보존하며 다음을 새로 계산한다.

- 각 exact interval의 모든 철자 대안에 공통 `edge + reading` 키를 부여하고 provider·origin·근음·구성음·원음 ID를 연결한다.
- 모든 part의 sounding events와 정확 시간 셀을 검증하고 구성음/미설명 비구성음/철자 미지원 음가를 따로 계산한다. 긴 음과 타이를 삭제하거나 유리한 부분만 취하지 않는다.
- 같은 셀에서 실제 최저음과 조건부 전위를 연결한다. 구조적 베이스·전위 확정이 아니다.
- 미관측 구성음의 역할과 부모 문맥 내 관측을 구별한다. 생략 가설 및 관측상 동등한 경쟁 quality를 보존한다.
- 조건부 NCT의 supporting assignment·requirement·구간 밖 조건·충돌을 연결한다. 단독 음형 링크로 비구성음을 면제하지 않는다.
- 직접/시간 해결의 모든 계획·원 query·상태를 해당 후보 키에 연결하고 `harmony_missing_evidence.run`을 실제 호출한다.

membership 음가, NCT 조건, 생략 가정은 서로 연관된 근거다. 독립 투표처럼 합산하지 않으며 대안의 조건부 설명량을 합쳐 정답으로 만들지 않는다. 분산 구성음의 시간순 관측도 최종 분산화음 확정과 구별한다.

명시적인 **완전한 path + 하나의 assignment** 요청에만 기존 progression evidence/bass/resolution 계산을 연결한다. 첫 후보를 자동 선택하지 않는다. evidence/bass의 evaluation span과 resolution의 전체 context 범위를 명시한다. 원주석의 local key를 resolution에 전달하지 않는다. selected/confidence/cadence/최적 화성 진행은 만들지 않는다.

### 고정 자료 실행

`harmony_context_integration_trial.py` v0.1.0은 이전 breadth/replay의 frozen plan·report·contract·source/preparation/IR/artifact hash, rights/split/pitch policy 및 sample ID/lane/span을 검증한다. 모든 package와 고정 표본을 유지하며 실패 표본을 쉬운 표본으로 교체하지 않는다.

새 마디 후보는 note/rest/measure Core 범위로만 소비한다. 저장된 화성 stages는 global sounding geometry가 같음을 확인해 재사용하며 전체 엔진 재실행으로 보고하지 않는다. 새 계산의 stage 상태와 이전 상태를 따로 집계한다. 조립 성공(`assembled_diagnostics_not_harmonic_readiness`)은 화성 준비나 정확도 성공이 아니다.

## 실제 실행과 검증

정본은 `output/harmony-context-integration-trial-2026-09-30-r1/`이다. 실행 완료, exit 0이며 `complete`, `inputs_and_code_unchanged`, `artifacts_unchanged` 모두 true다. runner가 기록한 처리 시간은 466.097초이며 입력 preflight 이전 시간을 포함하는 전체 작업/화면 성능 측정은 아니다. 592 input·257 Python source·358 artifact와 코드 목록을 보호했고 변경 0건이다.

### 고정 자료의 공통 문맥 결과

- 기존 **19개 작품 가족, 33개 악보·악장, 322개 고정 구간** 전부 저장했다. 정책은 train 27/dev 6, internal research 33 그대로이며 holdout을 실행하거나 권한을 승격하지 않았다.
- 제한 교정 후보는 3개, 나머지 30개는 `not_required`다. 후보 없음과 실패를 혼동하지 않는다. 실제 blocked revision은 0개다.
- 기존 상태 ready 243 / relation 예산 보류 48 / baseline 보류 28 / edge 예산 보류 3을 그대로 유지했다. 새 묶음의 조립 완료 322개를 화성 성공 322개로 보고하지 않는다.
- 준비된 lattice 291개에서 **5,614개 interval edge와 153,588개 철자 reading**을 공통 인덱스에 연결했다. 철자 대안이 없는 기존 candidate ref 111,904개도 별도로 보존했다. 후보 조합 반복 instances이며 고유 화음/독립 작품/정답 수가 아니다.
- 기존 relation 계획 282,000개를 모두 연결했다. 예산 내 실제 query는 기존과 같은 15,195개이고, 해당 query에 새 missing/NCT 근거 진단을 실제 계산했다. 282,000개 모두 해결을 재계산했다는 뜻이 아니다.
- 기존 생략 가설 origin 링크 2,500개를 연결했다. 관측상 동등한 경쟁 후보를 유지하며 생략음을 생성하거나 모든 비구성음을 NCT로 면제하지 않았다.
- 이 실험의 explicit complete path 요청은 0개다. 완전 path를 입력하면 세 progression 계산을 함께 사용하는 API/회귀 검사는 있으나, 실제 322개에서 자동 최적 진행을 선택하거나 새로운 path 순위를 산출한 것은 아니다.
- 기존 continuous/contrast/lattice/relations/hold_change 전체 JSON이 그대로 유지됐다. 새 reading inventory·cellwise bass·missing evidence·origin 연결은 실제 새 계산이다. `engine_recomputed=false`와 새 근거 계산을 혼동하지 않는다.

독립 대조에서도 33package/322sample identity set과 전체 592 input·257 code·358 artifact·contract SHA가 일치했다. 원 breadth와 새 묶음의 재사용 stages **1,610개 전체 JSON** 및 배열/상태/문맥 binding이 동일했고, reading/관계/생략 링크 집계와 원 보류 분모도 일치했다. 세 후보의 보호 projection은 별도로 검사했다. 차단 문제 없이 종료했으며 위 수치 어느 것도 화성 정답률이나 사람 검수 승인 수가 아니다.

### 코드 및 제한 교정 검사

- 신규 71개: physical revision 40, context bundle 18, disk runner 13. 전체 Python 2,292개 검사 통과, 75.061초. 기존 layout warning 1건은 유지한다. 실제 자료 실행과 병행한 회귀 시간이며 엔진/뷰어 성능 측정이 아니다.
- 작성 중 test fixture의 `display_label`, `frozen_plan_sha256` 누락과 tuple 반례 변경 방식을 실제 계약에 맞춰 보완했다. 잘못된 fixture를 허용하기 위해 운영 규칙을 약화하지 않았다.
- 세 실제 후보를 revision validator와 별도로 대조했다. 허용한 document/measure/label/note-rest measure/local 필드를 복원하면 부모 JSON 전체와 일치한다. 새 measure ID의 유일성과 document ID 변경도 확인했다.

| 후보 package | 교정 measure ID | 교정 label | 교정 event 참조 | 교정 local onset | 부모에 남은 direction 참조 |
|---|---:|---:|---:|---:|---:|
| dcml:beethoven-sonatas:01-1 | 2 | 1 | 13 | 2 | 3 |
| dcml:beethoven-sonatas:02-3 | 6 | 3 | 29 | 11 | 5 |
| dcml:mozart-sonatas:K280-3 | 2 | 1 | 7 | 2 | 0 |
| 합계 | 10 | 5 | 49 | 15 | 8 |

첫 두 후보의 상태는 `candidate_core_ready_parent_bound_residuals`이며 세 번째는 `candidate_core_ready`다. 어느 것도 source locator/extension/annotation을 포함한 완전한 production migration을 뜻하지 않는다. 교정한 ID 10개는 기존 중복 ID 5묶음의 서로 다른 physical measure 10개이며, 오류 10곡이나 화성 정답 10개가 아니다.

원 XML/부모 IR/기존 manifest/주석/이전 source 수정 후보/production parser/Core schema/rights/split/Gold/학습/외부 API/Git/운영 5173/현재 8822 화면/구조 분석 판단을 변경하지 않았다. source locator의 미교정과 parent-bound extension 잔여 참조를 숨기지 않는다. 사용자의 새로운 화성 해석 선택은 이번 제한 교정/연결 작업의 필수 입력이 아니다.

## 다음 큰 단계

다음은 같은 문맥에서 여러 **완전한 화음 진행**과 성부 가정을 공동 비교하는 단계다. 과도한 병합/분할, 실제 미설명 음, 지연 구성음, NCT 조건, 베이스·전위와 전후 해결을 함께 비교한다. 탐색 예산과 제외 경로는 기록하고 최종 조성·기능·종지 판정 및 독립 정확도 검증은 별도로 진행한다.

새로운 미지원 장식음 하나 때문에 전체 계획을 다시 source 정비로 돌리지 않는다. 정보가 부족한 해당 구간은 보류하고 다른 지원 구간의 기능 통합을 계속한다. 운영 뷰어·구조 분석·작곡/편곡 승격은 이후 검증 단계다.

## 재현

PowerShell에서 workspace root를 기준으로 실행한다. 기존 output을 덮어쓰지 않으므로 재실행에는 새 output 경로를 지정한다.

```powershell
$env:PYTHONPATH = 'src;tests'
.venv/Scripts/python.exe -m musicanote_harness.harmony_context_integration_trial --breadth output/harmony-breadth-trial-2026-09-30-r2 --replay output/source-sequence-replay-trial-2026-09-30-r1 --output output/harmony-context-integration-trial-2026-09-30-r1
.venv/Scripts/python.exe -m unittest test_source_physical_measure_revision test_harmony_context_bundle test_harmony_context_integration_trial
.venv/Scripts/python.exe -m unittest discover -s tests
```
