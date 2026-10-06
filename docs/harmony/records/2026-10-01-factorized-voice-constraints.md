# 성부 연결의 손실 없는 제약 표현과 확대 준비

기록 ID: `HARM-DEV-20261001-06`

날짜: 2026-10-01

## 목적과 적용 경계

사용자의 계속 진행 요청에 따라 [진행·비화성음과 역할 연결](2026-10-01-progression-role-link.md)의 전역 성부 조합 병목을 처리한다. 이전143개 단위와 source XML/IR/화성 후보/주석/보류를 바꾸지 않고 새 연구용 sidecar를 추가한다. 음악적 화성·주요 선율·반주 역할을 자동 확정하거나 운영 화면을 갱신하는 단계는 아니다.

기존 코드는 정확한 release/attack 시간마다 부분 대응을 만들고 모든 시간의 대응을 곱해 assignment를 열거한다. 순차12음만 있어도11개 연결의 유지/무연결 선택으로2^11=2,048개가 된다. 이 중 유리해 보이는 일부를 고르는 것이 아니라, **각 시간의 제약을 따로 저장하고 특정 연결 요구가 함께 성립하는지 질의**한다.

## 일반 규칙과 기존 방식과의 동등성

1. 같은 raw part/voice와 정확한 rational release==attack에서만 연결 후보를 만든다. 휴지기를 건너뛰거나 서로 다른 lane·동일 sound의 tie continuation을 새 attack으로 연결하지 않는다.
2. 한 시각의 왼쪽 release 집합과 오른쪽 attack 집합 사이의 모든 injective partial matching을 유지한다. 아무것도 연결하지 않는 대안도 포함한다. held sound는 같은 원 event를 유지하며 endpoint로 재배치하지 않는다.
3. 서로 다른 boundary factor는 outgoing/incoming 선택에 대해 독립이다. 한 음이 앞 factor의 target이고 뒤 factor의 source인 것은 연속 chain이며 분기나 병합이 아니다. 양끝 시간은 context 바깥 연결을 추가하지 않는다.
4. n개 release/m개 attack의 무제약 대응 수는 `sum(comb(n,k)*comb(m,k)*factorial(k), k=0..min(n,m))`. 전역 대응 수는 factor별 수의 곱이다. 가능 조합 수는 관측 빈도·확률·confidence·역할 지지표가 아니다.
5. 질의는 required/forbidden 실제 edge들의 **공동 조건**을 사용한다. 두 required가 같은 source에서 서로 다른 target으로 가거나 같은 target으로 합쳐지면 충돌이다. required와 forbidden이 겹치는 경우도 불가능하다. 잘못된 참조/시간/다른 lane을 단순한 음악적 기각으로 바꾸지 않는다.
6. 금지 edge가 있는 local count는 작은 endpoint 집합의 subset DP로 정확 계산한다. state/transition 예산 초과는 보류하며 근사 숫자나 일부 성공 대안으로 대체하지 않는다. 전역 assignment를 모두 저장하지 않는다.
7. 성공 질의의 witness는 required edges만 둔 sparse completion이다. 해당 raw lane/context에 겹치는 positive sounding events를 모두 partition한다. rest/grace point/다른 lane과 개별 tie continuation 기보음을 이 partition에 포함했다고 주장하지 않는다. 실제 참조 ID는 graph/query SHA와 정확한 links에 묶인 별도 `vfcompletion_`이다. 기존 `vpaths_` token은 `legacy_geometry_id`라는 대조용 값에만 보존하며 옛 assignment inventory 소속을 주장하지 않는다. 최상·선호·확정 성부가 아니며 서로 다른 질의의 witness를 합쳐 하나의 해석으로 보지 않는다.
8. 질의 결과는 정확한 graph·IR 내용·scope·lane과 봉인된다. 원 IR을 받는 fresh `validate_graph`와 이어지는 `validate_query`를 함께 사용하여 재봉인한 오염을 대조한다. `query`/`validate_query`/`materialize_witness`만으로는 원 IR의 진실성을 확인할 수 없으며 static hash 일치만으로 source 정체성이 인증됐다고 하지 않는다.
9. 모든 positive sound의 원 span/source note/tie identity·clipped note-time을 보존한다. grace point는 sampled lane/다른 lane/위치불명을 구별해 저장하며 해당 constraint가 미지원이면 보류한다. 다른 lane의 grace를 삭제하거나 일반 attack으로 바꾸지 않는다.
10. 실제 화성/NCT에 쓰려면 각 패턴의 준비·해결·박절·membership 조건을 먼저 검사하고 정확한 요구 edge 집합을 질의해야 한다. 현재의 산술 대조 질의는 NCT 양성 사례가 아니다. 여러 패턴의 대안을 OR로 결합할 때 중복 지원 집합을 독립 표로 더하지 않는다.

기존 `musical_progression_role_link`에 새 completion ID를 옛 assignment인 것처럼 넣지 않는다. 후속 consumer adapter는 동일 화성 진행·동일 scope·하나의 공동 required/forbidden 요청에 준비/해결 패턴들의 요구를 모아야 한다. source/박자/membership blocker는 그대로 검사하며, 서로 다른 요청의 성공 witness를 합쳐 NCT나 분산 반주를 승인하지 않는다. 역할 슬롯은 실제 pitch/spelling·음가와 공개된 화성 가정에 연결하고, 원음의 삭제나 근음의 자동 창작으로 계산을 맞추지 않는다.

일반성은 악곡명/마디/음높이 hardcode가 없고 원 기하에만 의존한다는 의미다. 현재 touching 연결 계약은 실제 대위법 성부의 모든 종류, 지연 도착/휴지기 연결/성부 교환을 포괄하지 않는다.

이번 질의는 직접 endpoint edge에만 적용한다. `a→b→c`가 가능해도 `a→c`는 직접 edge가 아닐 수 있다. 따라서 `a→c`의 invalid 결과를 두 음이 같은 track에 속할 수 없다는 결론으로 사용하지 않는다. 모든 무연결 대안이 남으므로 조합 수만으로 서로 다른 두 음의 성부 연속성을 확정할 수도 없다.

### 산술 대조 예제

같은 raw lane의 `C4(1 quarter) → D4(1 quarter) → E4(1 quarter)`는 두 boundary에 연결/무연결이 각각 가능하여 총 4개의 geometry 대안을 가진다. `C→D`와 `D→E`를 함께 요구하면 하나만 남지만, 이것은 경과음의 준비·해결·화성 조건을 따로 만족하지 않은 **연결 가능성**이다. 두 음이 한 sound로 타이된 경우에는 새 공격·새 edge를 만들지 않는다.

2 release와 2 attack 사이의 부분 대응은 7개다. 특정 edge 하나를 요구하면 2개, 하나를 금지하면 5개, 모든 edge를 금지하면 무연결 1개다. 하나의 source를 서로 다른 두 target에 동시에 요구하면 0개/unsatisfiable이며, 존재하지 않는 직접 edge 요청은 invalid/null이다. 계산 한도 초과의 abstention/null도 0개와 구별한다. 4×4 boundary의 209개와 순차 12음의 2,048개는 기존 방식과 동등성을 검사하는 합성 대조이며 실제 음악 정답 수가 아니다.

## 기존 실제 병목 진단

기존143단위의 상태를 바꾸지 않고 읽기 전용으로 분류했다.

- voice inventory68: 전역 열거 한도63/빈 lane5; raw sound128 한도2는 그63에 중첩.
- early assignment15: 기존 전체 assignment128~1024. 전역열거/assignment 예산 관련63+15=78단위다.
- link budget3: 예정 pair288/256/168이며 전역 연결 숫자와 별도 병목이다.
- candidate-edge30/grace25/empty5/조건부 연결2는 별도로 남는다.

voice/assignment-held83단위의 저장 boundary에서 위 수식과 기존 local choices 및 전체 곱이 일치했다. 해당 geometry의 최대166events/68boundaries/427edges와 최대75자리 전역 대응 수를 확인했다. 따라서 작은 기하 정보를 유지하면서 매우 큰 조합을 표현할 수 있다. 이것은 실제 NCT 인식 향상이나 모든 화성 후보의 계산 가능성을 증명하지 않는다.

## 구현과 검증 상태

- 새 `src/musicanote_harness/harmony_factorized_voice_paths.py`: factor graph/required·forbidden 질의/정확 count/질의별 witness/fresh validator.
- 새 `src/musicanote_harness/harmony_factorized_voice_trial.py`: 기존 G1 모든 관찰×raw lane과 직전r2 상태를 연결하는 offline 실행기.
- 각 source에 대응하는 새 tests. 기존 voice paths/Core/schema/parser/화성·역할 link의 의미는 변경하지 않는다.

최종 집중 검사는 64개(graph 39/runner 25), 12.379초/OK다. 작은 2×2의 required/forbidden 81요청을 기존 완전 열거와 대조하고, 4×4 209개/순차 12음/5×5 1,546개, rational 1/3, 타이·held sound·rest gap·cross-staff·다른 lane, source/attack/tie 누락, budget/오염·재봉인·분모 보존과 stale SHA를 검사했다. 기존 방식과 대조하는 합성 테스트만 제한 열거를 사용한다.

최종 전체 Python **2,622개/127.874초/OK**. 관련 회귀 119개와 독립적인 비열거 계약 33개도 통과했다. 독립 `_unit` 대조는 이전 `observe/product/partial_matchings`를 실패하도록 차단한 상태에서 4/1/1 count·입력 불변을 확인했다. 실제 batch와 최종 전체 회귀는 동시 실행했으며 이 시간은 엔진 benchmark가 아니다. 음악 정답률·검수 완료를 뜻하지 않는다. 실제 완료 수치와 보존 검사는 아래에 별도로 기록한다.

### 실행기 보완 이력

첫 실행기 v0.1.0은 작은 이전 assignment까지 `legacy_observe`로 다시 계산하여 대조했다. 새 factor 계산 자체는 전역 열거를 하지 않았지만 실제 batch의 비교 단계에는 기존 열거 호출이 남았다. 독립 검토 후 10/27 observations, 47/143 units에서 r1을 Ctrl-C로 중단했고 report/index를 만들지 않았다. `output/factorized-voice-2026-10-01-r1/`의 plan 1개와 packet 47개를 보존하며 이 결과를 완료로 집계하지 않는다.

최종 실행기 v0.1.1은 기존 열거 함수를 import/호출하지 않는다. 모든 단위는 원 IR에서 positive sounding event와 clipped note-time을 독립적으로 투영해 대조하고, 이미 저장된 이전 inventory가 있을 때만 그 값과 비교한다. 기존 143개 중 inventory 118개(완전 열거 50/보류 68)와 null 25개(모두 이전 grace 보류)를 구별하며 null을 뒤늦게 재계산으로 채우지 않는다. 저장 assignment instances 7,567개는 과거 자료를 읽은 숫자이지 이번에 재열거하거나 음악적으로 승인한 결과가 아니다. 무제약 count 동등성은 이전 inventory가 complete인 범위에서만 선언한다.

초기 집중 검사 59개/9.986초와 전체 Python 2,617개/121.885초는 이 보완 전 실행기 버전의 결과다. 최종 버전 검사 수와 실제 완료 결과는 별도로 기록한다. 당시 전체 회귀와 r1은 동시 실행했으므로 elapsed를 엔진 속도 benchmark로 쓰지 않는다. 기존 layout warning 1건은 유지했다.

### API·재현·실제 자료 계약

- graph module: `factorized-voice-paths-0.1.0`; corrected runner: `factorized-voice-trial-0.1.1`.
- `factorize(ir, span, lane, max_events=4096, max_factors=4096, max_edges=65536)`는 literal snapshots와 전체 endpoint product를 저장한다. `validate_graph(..., ir, span, lane)`는 같은 원 입력으로 재구성한다.
- `query(graph, required_links=(), forbidden_links=(), work_budget=100000)`는 normalized request와 원 request를 함께 봉인한다. 정확한 count는 float/int JSON이 아닌 decimal string으로 저장한다. `exact_count`, `unsatisfiable_constraints`, `invalid_constraints`, `abstention`을 구별한다.
- `validate_query`는 같은 request/budget으로 재계산한다. `materialize_witness`는 `assignment`와 graph/query 참조를 포함하는 sealed wrapper 전체를 반환하며 caller의 입력을 수정하지 않는다.
- actual control은 ready graph마다 무제약, 모든 factor에서 첫 edge를 함께 요구, 모든 edge 금지의 3개다. 첫 edge 선정은 재현 가능한 산술 테스트일 뿐 유력한 선율/베이스 선택이 아니다. resource hold graph에는 성공 질의를 발명하지 않는다.
- output은 `run-plan.json`, 각 observation×lane의 gzip packet, `unit-index.json`, `report.json`이다. packet은 `baseline_unit`의 기존 status/reasons/출력 참조를 그대로 보존한다. report의 `complete`는 분모 처리·입력/코드 불변·예외 없는 계산이라는 뜻이지 음악적 분석 완료가 아니다.

PowerShell 재현 명령:

```powershell
$env:PYTHONPATH='K:/Music Analysis/src'
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_harmony_factorized_voice*.py'
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -m musicanote_harness.harmony_factorized_voice_trial --alignment output/musical-semantic-alignment-2026-10-01-r2 --baseline output/musical-progression-role-2026-10-01-r2 --output output/factorized-voice-2026-10-01-r2
```

실제 output 경로가 이미 있으면 덮어쓰지 않고 거부한다. 재현할 때는 새 이름을 사용한다. G1 report 포함 입력 파일 172개(등록 artifacts 171개), baseline report/등록 artifacts, 이전 producer source/schema와 새 전체 source/schema inventory를 시작/끝 모두 대조한다. 원 observation ID가 같아도 SHA가 다르면 baseline 연결을 거부한다.

### 실제 r2 결과

`output/factorized-voice-2026-10-01-r2/`는 **161.570초/exit 0**으로 완료했다. Python 3.12.14, music21 10.5.0, jsonschema 4.26.0, referencing 0.37.0 환경이다. source 코드는 실행 중 동결했다. 동일 14개 score files/27 observations/143 raw-lane units 전체를 유지했다.

| 항목 | 결과와 의미 |
|---|---|
| 새 geometry graph | ready 130/abstention 13. 의미 성부/화성/역할 성공 수가 아님 |
| 예전 열거 보류 | 63개 모두 새 geometry ready. 원 inventory는 그대로 보류 |
| 예전 early assignment 한도 | 15개 새 geometry ready. 위 63개와 합쳐 기존 조합 수 병목 78개를 표현 |
| 예전 grace 보류 25개 | 다른 lane 등의 point metadata를 보존한 geometry ready 17/새 geometry hold 8. 예전 grace/NCT 보류를 면제하지 않음 |
| 나머지 기존 상태 | lattice 30/link budget 3/conditional 2 모두 geometry ready지만 원 화성·역할 상태는 불변 |
| 새 보류 13개 | sampled grace/point timing 5개(두 reason 중첩) + empty lane 8개. 미지원 수행 시간/빈 positive lane을 연결 성공으로 만들지 않음 |
| literal instances | positive sounds 2,687/전체 문맥 point refs 33/factors 1,462. 보류 graph도 포함하고 겹치는 창/metadata 반복 instances를 독립 작품·음표 수로 세지 않음 |
| 산술 control | ready 130×3 = 390 requests, 모두 exact count와 query-local witness. 음악 패턴/경과음 양성 390개가 아님 |
| 단위별 최대치 | 166 positive events/68 factors/427 legal edges, 최대 전역 대안은 75자리 decimal string. 모든 assignment를 생성하지 않음 |
| 승인/운영 | human/training/gold/generation-ready 0. 기존 NCT inventory·143개 원 상태·화음/role 선택·운영 화면 변화 없음 |

최대 count는 `111499310106944486479178265531044292960055030118871503388677977297932779520`이다. observation `mpo_e2ac3551803197e3e9d1de73`, lane `part_27bd2a637206/voice_735c83db0935`의 값이며 신뢰도/음악적으로 타당한 해석의 수가 아니다. 가장 음표가 많은 단위와 가장 count가 큰 단위가 동일하다고 주장하지 않는다.

run-plan은 입력 623개와 현재 source/schema 280개의 SHA 및 전체 목록을 고정했다. input 623개는 G1/이전 r2 artifacts·report·이전 producer code의 보호 집합이지 623곡이 아니다. 등록 새 output은 plan 1/index 1/packet 143 = 145개이고 자체 report는 별도다. 실행기 최종 `inputs_and_code_unchanged`, `computation_integrity_passed`, `complete`는 모두 true다.

최종 독립 read-only 감사에서 위 623/280/145개와 별도 report의 SHA·inventory, 원 14개 IR/27개 observation/143고유 keys, baseline row/status/reasons와 전체 scope/source/IR binding이 모두 일치했다. 143 graph의 원 literal 투영·clipped note-time·point refs·factor 및 390 query/witness의 봉인·잔여 대응 수·직접 공동 조건·전체 sound partition·completion 계보를 독립 재계산하여 오류 0을 확인했다(16.280초). 이전 inventory 118개/미계산 null 25개는 원 상태 그대로다. null 25개 중 새 hold 8개는 sampled grace/point 5개와 empty 3개이고, old inventory hold 68개 중 새 hold는 empty 5개다. 기존 grace 보류의 17개 새 geometry ready를 음악적 성공으로 승격하지 않았다.

두 번째 독립 산술/partition 감사도 143 packet/390 completion을 대조해 일치했다. selected positive sound instances 2,687개가 참조하는 source-note instances 2,859개의 raw lane·공격 onset·정확 음가·연속 tie-chain·source 참조와 full span을 대조했다. 이 숫자는 harmonic chord tones나 고유 원음표 수가 아니다. 두 감사 모두 기존 전역 열거/새 화성 재계산이나 파일 쓰기가 없었다.

14 cases의 실제 XML/MXL SHA와 IR source_files, analysis.txt와 meter/source statement SHA 및 입력 등록도 일치했다. 독립 감사 초기에 legacy token의 JSON spacing과 grace status 문자열을 검사 스크립트가 잘못 기대한 두 assert는 검사 쪽을 정정한 뒤 전 143/390개를 대조했다. 제품 코드/결과를 바꾸거나 해당 단위를 검수 대상에서 제외하지 않았다.

중단 r1의 48개 파일(plan 1/packet 47)과 모든 SHA는 마지막까지 불변이고 report/index도 추가하지 않았다. 감사에서 고정한 file-map digest는 `40e041446339cbfb54d70ac72217d5088eb616ba25d05a3a0deae3b875fd99f7`이다. 최종 8개 변경 source/tests/docs의 strict UTF-8·replacement character·trailing whitespace 검사와 4개 개발 문서의 상대 링크 99개 검사는 모두 통과했다. `git diff --check`는 오류 0/기존 LF→CRLF 경고만 남았다. 새 untracked 파일은 별도 공백 검사로 대조했고 기존 dirty worktree를 stage/commit/정리하지 않았다.

| SHA-256 대상 | 값 |
|---|---|
| graph module | `b377651b4153cb8fcb61b3a4bc74b23e7479729fc55a7e214a7aa999189f597f` |
| final runner | `dd9f6bda73f671108c6d1c9f4f306181f4f31f80c3b9615a5ad4b3465b39bfaf` |
| r2 run-plan | `824080fd48aef518dbf1dc41125cd86b970490e09de66b9baad7cd47b27bb44b` |
| r2 report | `b939cd81e757febd460f244260fabdc3b291c50a08ffffebd53fc0fb690d7305` |

## 베토벤·모차르트 문맥을 연결할 다음 계약

기존322문맥의 window selector는 frozen continuous plan의 IR attack group/명시 lane quantile을 사용해 주석 라벨에 독립적이다. 다만 코호트 진입은 옛 score+annotation SHA pair 및 alignment eligibility를 계승했다. **window 선택의 라벨 독립**과 **주석 없는 독립 코호트**를 구별한다.

현재 G1 observation scope는 진짜 source statement와 alignment를 필수로 요구한다. 이전322문맥에 가짜 SOURCE를 만들거나 null refs를 넣어 기존 gate를 우회하지 않는다. 후속 버전의 별도 origin 계약은 다음처럼 계획한다.

| origin branch | 필수 provenance | 검증 |
|---|---|---|
| aligned_source_window | 실제 source_statement_ref/alignment_ref | 현행 SOURCE/정확 좌표 gate를 그대로 fresh replay |
| frozen_context_window | pair_id/plan_index/sample_id, 정확 bundle SHA, 전체 입력 sample packet SHA, selector/version, target policy | 원 integration index/packet/continuous plan/revision 선택을 대조 |

공통 scope의 score/IR document/content SHA/source files/target/context와 all-part literal 투영은 유지한다. `bundle.input_sample_content_sha256`는 전체 원 stored packet의 hash이며 `bundle.sample`만의 hash가 아니다. origin sealing만으로 부모의 진실성이나 판본 대응을 증명하지 않는다.

working IR은 integration의 measure revision에서 선택된 원본30/수정 후보3을 그대로 사용한다. 후보3은 parent/candidate/sidecar의 `validate_revision`을 요구한다. 같은 source SHA라도 parent와 candidate IR을 교환할 수 없다. 처음 target=context로 시작하면 `full_frozen_context` 정책을 선언하고 sampled lane을 all-part 필터로 쓰지 않는다. parent-bound locator/extension을 새 판본에 자동 retarget하거나 source-certified로 승격하지 않는다.

총322문맥과 기존 lattice ready291/hold31의 분모를 모두 보존한다. 새 origin branch에는 version dispatch와 registry/schema 참조 검사가 필요하며 옛0.1.0 SOURCE gate는 완화하지 않는다. OR 조건 누락·IR revision 교환·재봉인 sample mismatch·scope 끝점·lane 필터·부모 inventory 추가/누락을 반례로 둔다.

이 계획은 새 일반 observation이 이미 구현됐다는 뜻이 아니다. 큰 기능 우선순위는 성부 제약 확대 → 정확한 일반 문맥 연결 → 조성/secondary/기능/cadence·화음 상대 반주 슬롯의 공동 대안 비교다. 끝없는 source 정비나 개별 악곡 예외 처리로 전환하지 않는다.

## 보존과 운영

원 XML/IR/주석/이전 실험/권리·split/Gold·training·교정과 운영5173/8822·구조 분석을 변경하지 않는다. 외부 API 전송/Git upload도 없다. 화성·작곡/편곡 개발 이력은 이 별도 화성 개발 문서와 메인 로그에 기록한다.
