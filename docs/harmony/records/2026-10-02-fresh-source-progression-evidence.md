# 저장된 진행 후보의 fresh 성부·역할 근거 계산

## 개발 범위와 상태

2026-10-02, 화성 개발 단계29. 직전 단계28은 원음표에 근거한 3/7화음 다양성·single-slot 교체·형태별 관계와 None 요청을 저장했다. 이번 단위는 그 요청을 **원본 전체 IR에서 새로 발급한 native session의 실제 성부 연결과 조건부 역할 계산에 연결**한다. 교재 규칙과 원음표의 앞뒤 지속·진행 근거를 함께 사용하되 특정 악곡/마디의 정답을 코드에 넣지 않는다.

구현과 검사·실제 실행 상태는 아래에 별도로 기록한다. **새 runner의 계산/저장 실행 경로는 자동 승인 검토의 명시 승인 요구로 아직 미구현이다.** 원자료 direct admission부와 핵심 bridge를 구별한다. 이 문서의 계획 분모를 실행 완료나 음악 정답 수로 읽지 않는다. 최종 화음·NCT·key·cadence, 학습/Gold, 운영 뷰어·구조 분석·생성에는 승격하지 않는다.

## 일반 규칙 R01–R10

| 규칙 | 계약 |
|---|---|
| R01 | 저장 proposal/prior panel/scope/lattice를 strict JSON·seal·source joins로 먼저 검증한다. 저장 ID만으로 native 권한을 만들지 않는다. |
| R02 | 전체 IR과 원 scope에서 archived caps 그대로 fresh lattice를 한 번 만든다. 전체 supplier·catalog·ordered member/root·provider/pointer/alternative·key·시간/음표 출처가 동일해야 전 요청을 재연결한다. 드리프트는 whole-source hold이며 PC/근접 pitch로 부분 재매핑하지 않는다. |
| R03 | 결정론적 ID가 이전과 같을 수 있지만 새 session 소유 상태와 새 bundle 등록이 권한이다. 원 두 completion의 required links를 각각 새로 등록한다. |
| R04 | 원 controls·None·unknown key·불리한 요청·missing member 후보를 원순서대로 유지한다. 실제 해결 성공을 보고 앞의 후보를 골라내지 않는다. |
| R05 | 같은 completion의 첫 실제 pitch change를 확인한다. 뒤의 유리한 해결을 찾아 첫 불리한 변화를 건너뛰거나 다른 completion의 해결을 빌리지 않는다. 역할별 doubling은 OR, leading/seventh 역할 사이는 AND라는 기존 계약을 유지한다. |
| R06 | 수직 형태, source 구성음 관측, ordinary 실제 해결, key/기능/베이스·종지 전제와 조건부 NCT geometry를 별도 축으로 보존한다. Shape True를 Secondary 정답으로 바꾸지 않는다. |
| R07 | 타이의 원 attack/full sounding span·source note IDs·재발음 링크와 유리수 `[start,end)`를 보존한다. 같은 sound의 설명 clip union은 한 번만 계상한다. |
| R08 | 전체 배치 수와 모든 배치의 native 두 번+role 한 번의 비용을 계산한 후 첫 query를 실행한다. 하나라도 사전 한도를 초과하면 whole-job hold하며 favorable prefix를 반환하지 않는다. |
| R09 | 작은 배치는 계산/저장 단위이지 전체 경쟁 비교 단위가 아니다. Contrast/policy는 전체 동일 전제 경쟁자를 볼 수 있는 별도 adapter가 필요하다. |
| R10 | null·알려진0·미계산을 구별한다. 원음가 합계와 submitted/withheld 분모, 실패·불리한 근거·원자료 SHA를 유지한다. Terminal까지 소비하지 않은 stream은 완료가 아니다. |

## 구현 파일과 데이터 계약

- [`source_progression_replay.py`](../../../src/musicanote_harness/source_progression_replay.py): 저장 요청의 intrinsic validation, exact fresh rebind, immutable/HMAC 소유 bridge, 전체 작업 preplan, detached header/batch/terminal stream.
- [`source_progression_replay_trial.py`](../../../src/musicanote_harness/source_progression_replay_trial.py): 단계28의 exact6파일과 ancestry의7/7/148목록·creation SHA를 직접 admission하고 source identity별 원IR/scope/lattice/panel/proposal을 한 번 읽는 등록부. Append-only 계산/저장 `run()`·CLI는 아직 없다.
- [`test_source_progression_replay.py`](../../../tests/test_source_progression_replay.py), [`test_source_progression_replay_trial.py`](../../../tests/test_source_progression_replay_trial.py): 실제 작은 XML-derived 계약 검사와 저장/실행기 검사. 저장 mock은 음악 producer 검증이 아니다.

핵심 API는 `prepare_replay(..., prior_panel=...)`, `binding_prepared`, `plan_saved`, `stream_prepared`다. Bridge는 native session/state identity와 immutable request를 소유한다. 저장된 bundle ID는 등록 권한으로 사용하지 않는다. Binding/plan/job은 각각 `npsrebind_`, `npsreplayplan_`, `npsreplayjob_` seal을 사용한다.

Batch는 complete native path와 같은 실제 completion의 role sidecar를 함께 보존한다. Raw membership을 NCT로 덮어쓰지 않는다. Local·boundary·ordinary clause, 실패/보류 이유, source refs/full span, 후보/key/bundle, rational category/union 계정과 모든 terminal/boundary/function shape를 그대로 저장한다. 소비자에게 전달하기 전에 aggregate/ref snapshot을 확정하므로 packet 변경이 이후 계산을 바꾸지 않는다.

Source hold이면 새 native 권한은 없다. Job preplan hold이면 bundle 등록/native/role query는0이다. Bundle이 실제로 불완전하면 원 제출을 생략하지 않고 unassessed completion과 null credit을 보존한다. 갑작스러운 runtime batch hold도 이후 제출 위치를 임의 제거하지 않으며 전체 job은 incomplete로 남는다. API 예외로 stream이 끝나면 runner는 terminal 완료를 만들어내지 않는다.

`resolution_contexts_under_complete_bundle`은 complete bundle 아래 명시 관계의 **계산 활동 수**이지 해결 성립 수가 아니다. Native/role ordinary tri-state·개별 occurrence·joint prerequisite와 별도로 읽는다. `fresh_native_evaluation_performed`도 실제 computed path 존재만 뜻하며 정답/선택을 뜻하지 않는다.

## 분모와 사전 한도

직전 stage28의 **두 등록 구간/7raw lanes**, 네 원 completion, 4,025개 source selector → **8,050 selector×completion 발생**을 요청한다. 두 전곡의 분석이나 8,050개의 음악 정답이 아니다. 원272catalog/18,666origin/10key, 제안714paths·미제안42,137Cartesian paths와 원322문맥/1,013lanes·미실행320/1,006을 보존한다.

기본 한도는 batch3, max_selectors4,096, max_slots3, native query2,000,000/batch, role query100,000,000/batch, whole replay1,000,000,000,000/job, geometry100,000다. Native role 준비가 comparison을 다시 인증하므로 native 비교를 두 번 계상한다. 원 role union planner가 배치 크기에 대해 이차 bound를 가지므로 batch8/16/32/64를 임의로 늘리지 않는다.

Metadata-only 계산은 저장 proposal2+scope2를 읽고 producer/build/prepare/compare/role/propose0이었다. Batch3의 static bounds는 다음과 같다. 70,008,508,794는 논리 방문 단위이며 CPU 시간/RSS/bytes/정확도 예측이 아니다.

| 등록 source | selector/completion | batches/completion | native work 최대/batch | role work 최대/batch | native twice+role work/completion |
|---|---:|---:|---:|---:|---:|
| 베토벤 소나타01-1 등록 구간 | 2,315 | 772 | 38,826 | 7,633,172 | 3,768,793,837 |
| 베토벤 현악4중주 등록 구간 | 1,710 | 570 | 130,647 | 90,567,778 | 31,235,460,560 |

기본 batch3에서 전체4completion의 예정 batch2,684, native 비교 kernel5,368, role prepare/explain각2,684다. Native source prepare는2, bundle fresh 등록은4가 예정값이다. Read/output byte admission은 이 logical bound와 독립이다. 전체 본문을 메모리에 쌓지 않고 배치를 저장한 뒤 버린다.

### 실행 배치 크기의 사전 검토

독립 static 검토에서 frozen `native.compare_prepared`가 배치마다 **전체 lattice를 두 번 thaw**한다는 비용을 확인했다. Batch3 실행을 확정하지 않고 16/64의 source-size bounds를 먼저 비교했다. Pure planner/자체 role 산술1.0721158초, fresh producer/output0이며 음악적 성공/실패는 선택 기준에 쓰지 않았다.

Batch16은 소나타145/사중주107batch/completion, 최대 native201,184/666,256·role215,000,735/2,565,373,098, 전체4작업368,794,524,148 logical units다. 따라서 **실제 실행 사전 정책은 모든 작업에 동일 batch16/role3,000,000,000/native2,000,000/replay1,000,000,000,000**으로 정하고 기본3/100M은 유지한다. 예정 총batch504/native kernel1,008로 full-lattice 복사를 줄인다. Output admission·실제 시간/RSS는 별도로 점검하며 이를 정답률/운영 속도라고 읽지 않는다.

Batch64는 최대 native2,355,928와 전체 work1,448,102,564,940로 기본 native/whole budget을 넘고, 최대 role41,016,131,946이다. 그 크기는 이번 실행에 채택하지 않는다. Batch size/caps는 계산 허용량이며 음악적 지원 threshold 변경이 아니다.

Whole replay work에는 batch native 두 번과 role 한 번만 포함한다. Admission/digest/intrinsic validation, fresh 공급·session 준비, geometry bundle의 비용을 이 수에 포함했다고 주장하지 않는다. 공급은 원 lattice의 coordinate/catalog/variant/DP 한도, geometry는 별도100,000, 읽기/저장은 독립 bytes 한도로 제한하며 실제 시간/메모리는 따로 확인한다.

전체 신규 압축 산출물의2GiB 상한도 제안했으나 저장 실행기 차단으로 아직 구현하지 않았다. 구현 시 압축 후 exclusive write **이전** 남은 허용량을 검사하고 manifest/report 공간을 예약한다. 한도 초과는 남은 source/completion·selector 범위를 미실행으로 명시한 incomplete 결과로 남기며, 기존 파일을 삭제하거나 prefix를 완료로 표시하지 않는다. 현재 K 여유26,733,379,584bytes 점검은 read-only 진단이며 전체 출력 크기의 실측이 아니다.

## 전체 경쟁 비교·정책을 분리한 이유

기존 `native_progression_contrast.compare`와 `native_progression_policy.evaluate`는 요청256개 한도다. 이번 source의 같은 key 그룹은 각각463/342개로 한도를 넘는다. 네 completion의 동일 key 내 전체 pair는 **1,652,640**이며 원900pair의 완료를 확장해 읽어서는 안 된다.

임의 chunk의 pair를 합쳐 전체 비교 완료라고 하면 chunk 사이의 경쟁을 놓친다. 이번 native/role stream은 전체 submitted 위치의 실제 근거를 준비하지만 contrast/policy/winner는0이다. 다음 기능 단위는 원음표 정렬·동일 전제·key·bundle을 보존하면서 전체 competitor blocks를 다루는 bounded/streamed comparator다. 단순 budget 증액이나 chunk별 winner 합치기를 하지 않는다.

## 음악적 검증에서 주의할 실제 반례

Stage28의 E♭7 `[49,53)`→A♭triad `[53,57)`는 missing0/shape 호환이어도 whole ordinary True를 기대해서는 안 된다. 원 greedy completion에는 G4→A♭4 link가 있으나 D♭5에는 다음 실제 link가 없다. Leading 개별 지원과 seventh/whole ordinary 실패가 공존할 수 있다. No-link control은 그 completion의 해결 근거 부재이지 E♭7의 음악적 기각이 아니다. Ordinary credit 실패로 다른 local/boundary credit을 지워서도 안 된다.

타이 D♭5의 원 attack45와 fullspan `[45,101/2)` 및 notated notes의 음가4+3/2를 유지한다. Scope start49에서 새 attack을 만들어내지 않는다. Sonata/Quartet의 raw note-time85/2·53/2와 wall duration12·8을 구별한다.

## 검사·실제 실행·보존 기록

구현 및 독립 계약/음악 검토 진행 중. 별도 frozen proposal27+native role57의 기존84검사/143.571초 PASS이며 새 검사 수로 합산하지 않는다. 실제 실행·신규 검사·동결 SHA·정확 output 목록/bytes·보호 파일 변화·source별 지원/미상/실패 분모는 검증 후 이 절에 기록한다. 현재 예정값을 완료값으로 적지 않는다.

새 저장자료 admission 검사의 실행기 미의존7개/46.174초 PASS다. 총9개 draft 가운데 `run()`에 의존하는2개는 실행기 미구현으로 실행하지 않았으며, full storage suite PASS라고 표기하지 않는다. Temporary synthetic archive/mock 저장 검사이고 fresh 음악/corpus 검사와 다르다.

Root의 별도 **실제 저장자료 read-only admission**은27.8081182초, strict23파일/254,888,715decoded bytes, 보호4,784경로·exact6/7/7/148inventory를 확인했다. 두 source의 selector2,315/1,710와 각각 원 completion2개, 원322/1,013·선택2/7·미실행320/1,006을 확인했다. Fresh native/role/proposal/output 계산은0이다. 당시 core test 생성 전 current code346목록은 temporary 상태이고 원 historical343목록은 변경하지 않았다.

독립 정적 검토에서 runtime hold record의 ref 존재를 실제 evaluation으로 읽던 activity 표기와, withheld-empty proposal의 credit 합계를0으로 표시하던 edge를 교정했다. 실제 computed native/declared transition와 complete bundle의 수로 activity를 판단하고 whole hold의 aggregate credit는null로 보존한다. 정상 known-empty 요청의0과 구별한다. 기존 producer/음악지원 조건/저장 output은 바꾸지 않았다.

새 core synthetic 검사의 첫45개/68.8729256초는43PASS/1FAIL/1ERROR였다. ERROR는 fixture 배열명 `notes`를 실제 IR의 `note_events`로 잘못 참조한 검사 오류다. FAIL은 unknown key일 때 모든 joint가None이어야 한다고 가정한 검사 오류다. 기존 native 계약은 explicit key coordinate가None이어도 다른 gate가False이면 joint=False를 보존하므로, ‘unknown key를 기능 True로 확정하지 않음’과 literal key coordinateNone을 검사한다. 기대 교정은 지원 조건 완화나 producer/Core 수정이 아니다. 최종 검사는 아래에 별도 기록한다.

최종 새 core **47개/80.2411426초·실패/오류0 PASS**다. Single chord·leading/seventh ordinary·tied·rational·single-pitch known-empty의 genuine 작은 XML→IR fixture5종, public API·whole budget exact/one-below·original controls/unknown/None·HMAC/state/input/contract 변경·같은 completion·raw-time/union/null0·fault injection을 검사했다. Explicit mocks는 adversarial/budget/storage injection이며 실제 음악 양성이라고 읽지 않는다. 순수 tri-state helper1개를 포함하고 old TestCase를 상속해 이전 검사를 새 검사 수에 넣지 않았다.

추가한 두 metamorphic 검사에서 **batch3/64의 flattened native path와 role path 전체 JSON·순서·raw 계정이 정확히 동일**했다. 작은 fixture에서 배치 크기 변경이 음악 계산을 바꾸지 않음을 확인한 것이며 실제 batch16 corpus의 시간/메모리/정답률 검증이 아니다. Core PRE/POST SHA는 동일하고 초기 오류 교정으로 core 코드를 바꾸지 않았다.

최종 PASS 범위는 core47+admission-only7=**신규54개**이며 draft storage9개 전체 PASS나 실행기 완료가 아니다. 기존84회귀와 중간 재검사는 이54개에 합산하지 않는다. 원 core/XML/producer/output·Git·운영 UI는 그대로다.

### 현재 부분 산출물 SHA

아래는 현재 구현/초안의 동결 snapshot이다. 실행기 구현이 승인되면 runner와 storage test는 새 버전/SHA로 다시 검증해야 한다. 아직 실제 r1의 creation manifest/산출물 SHA는 없다.

| 파일 | SHA-256 |
|---|---|
| `src/musicanote_harness/source_progression_replay.py` | `e32d98f57a717f2a508512b5ae07eee9a44890635dcc9689dfc6f08910c0e888` |
| `src/musicanote_harness/source_progression_replay_trial.py` (admission부) | `45bd4d29f0efd85f9238fde33d5043cf170504f790c3218470b09c1619d13c6c` |
| `tests/test_source_progression_replay.py` | `dbff8de88df409ab14c0d4fe6cd549777d0612d71f2ed0d57962a53cde157ebc` |
| `tests/test_source_progression_replay_trial.py` (9개 draft/7개 실행) | `969defab93df499e30a1352a67c9d0b98b387317b7a817a5917d48452e8deb17` |

### 실행기 구현의 승인 차단

새 runner/test 두 파일에 계산·저장 실행 경로를 추가하는 patch가 자동 검토에서 두 번 차단됐다. 최초 read-only audit 범위에 해당하며 해당 side effect의 명시 사용자 승인이 부족하다는 사유다. 후속 구현 지시와 새 workspace 파일만 변경·producer 실행0·기존 코드/자료/결과 미변경이라는 범위 증거를 확인한 한 번의 재검토도 거부됐다. 다른 writer·경로·shell 쓰기로 우회하지 않았다.

사용자에게 두 새 파일의 실행기/저장 테스트 구현을 명시적으로 승인해 달라는 질문을 보냈다. 그 답 전에는 차단된 patch/실제 corpus replay를 진행하지 않는다. 별개 core 검사와 승인된 기존 admission 검사는 계속한다. 현재 실제8,050계산·새 source prepare·bundle·contrast/policy 실행은0이다. 작은 genuine XML 테스트의 fresh 계산은 실제 corpus 실행과 별도다.

최종 root QA는 네 Python AST·동결SHA4개·세 문서의 replacement-character/로컬139링크에서 오류0, read-onlydiffcheck exit0이다. Current code347/new4·원 historical343과 구별하고 runner `run()` 부재·새 실제r1 output directory 부재를 직접 확인했다. 기존 별개 tracked5파일의 사용자 변경/줄바꿈 경고는 유지한다. 새 core의 정적 독립 authority/packet/budget 감사에서도 앞의 두 교정 이후 추가 차단 결함은 발견하지 못했으며 이는 producer 재실행/음악 정확도 검수와 다르다.

## 남은 기능 단위

2026-10-03 후속: 사용자의 진행 답변을 근거로 한 새 runner 구현 patch도 자동 검토에서 거부됐다. 이전 코드/검사 SHA는 그대로다. [새 후속 기록](2026-10-03-replay-implementation-scope-and-progress.md)에 정확한 구현 승인 범위·진행률 판단·변경0을 기록했으며, 위2026-10-02 차단 이력은 보존한다.

그 후 사용자의 정확한 범위 “네” 승인으로 같은 두 새 파일의 구현을 재개하여 **run/CLI·제한 저장·packet/분모 검증과 최종22저장 검사**를 완료했다. 원 core/core test SHA는 그대로다. 위 admission-only 상태와 차단 이력은 당시 snapshot이며 현재 실행기 부재를 뜻하지 않는다. 실제 corpus8,050요청·새 계산 output·UI는 아직0이다. 구현/교정·최종검사/동결SHA·다음 미실행 명령은 [2026-10-03 후속 정본](2026-10-03-replay-implementation-scope-and-progress.md)을 따른다.

1. 새 native/role stream 계약·저장기 검증과 모든 제출의 실제 계산 및 SHA 보존 확인.
2. 전체 comparator/policy adapter와 cross-batch completeness·동일 전제 경쟁 검증.
3. 후보 다양성·실제 해결·전위·NCT·분산형의 여러 source/편성 일반화 검증.
4. 기존 운영 악보 viewer에 검증된 experimental layer를 연결하고 앞뒤 XML/IR·사용자 의견·분석 버전을 함께 저장.
5. 화성·역할·반주질감·모티프 전개 의미를 구조 분석·작곡/편곡이 별도 계층으로 소비.

기존 Core/XML/annotation/producer/output을 변경하지 않는다. Git/운영 UI/구조/생성은 이번 개발 단위의 변경 대상이 아니다.
