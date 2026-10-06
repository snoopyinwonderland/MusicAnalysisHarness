# HARM-DEV-20261001-09 — 같은 성부 가정의 조성·적용화음·해결·종지 근거

진입점은 [화성 개발 메인 문서](../README.md)다. 개발 기록이며 인수인계 문서나 분석 정확도 승인서가 아니다. 이전 [공동 음악 의미 계산](2026-10-01-factor-conditioned-musical-meaning.md)의 원자료·결과는 보존한다.

## 1. 목적과 현재 진행 상태

이번 큰 기능은 **명시적 조성 가정 → ordinary V/vii 계열의 기능 가정 → 실제 이끎음/7음 진행 → 같은 성부의 NCT 제약 → 경쟁 진행과 종지 전제**를 연결하는 것이다. 임시표가 있다는 이유만으로 secondary를 판정하거나, 앞뒤 후보의 연결을 각각 골라 합치지 않는다.

새 네 모듈과 대응 테스트의 연구용 구현을 동결했고, 신규 111개 및 전체 Python 2,917개 회귀 검사를 통과했다. 실제 검증은 전체 cohort가 아닌 첫 context의 모든 group을 보존하는 별도 pilot으로 제한한다. 구현 상태와 음악적 검수/운영 적용을 구별한다. 최종 조성·화음·전위·NCT·cadence 선택이나 작곡/편곡 실현은 이번에 하지 않는다.

## 2. 일반 규칙과 자료 계약

| 레코드 | 역할 | 확정하지 않는 것 |
|---|---|---|
| `fmkey_` | 명시적으로 제공한 전체 context 조성/scale-form 가정 | 조표가 실제 key라는 추론 |
| `fmfunc_` | 모든 ordinary 가족/target quality의 철자 형태와 원 source/실제 다음 segment/가정 target 분리 | 기능·secondary·전조·실제 해결 |
| `fmres_` | 실제 source sound와 다음 sound의 시간/옥타브/철자/required carry edge 조건 | 조건부 shape가 정답이라는 주장 |
| `fmcmb_` | 같은 view/context의 전체 경쟁 path registry와 raw lane별 하나의 query/witness | 성부 선택, 독립 witness 합치기 |
| `fmfj_` | 명시적 LT/7음/NCT 요청의 OR 대안×AND 공동 가능성 | OR counts의 합계 confidence, 미검사 branch의 승인 |
| `fmreval_` | 공통 bundle에서 각 실제 해결 조건의 만족·미만족·보류 | 한 bundle의 미만족이 모든 해석의 실패라는 주장 |
| `fmbound_` / `fmfcmp_` | 관찰 최저/최고음·정확한 기보 박자·동시음·뒤 지속·경쟁 해석별 전제 | 구조적 베이스/선율, 지각 accent, 협화, PAC/HC 확정 |

모든 레코드는 version·현재 내용 seal·working IR/source/view/path refs·rational `[start,end)`에 묶는다. caller hypothesis는 SOURCE 주석/사람 정답으로 위장하지 않는다. 해석·권한·training/gold/generation eligibility는 승격하지 않는다. Core/parser/운영뷰어/구조 분석·기존 source 및 output·Git은 이번 작업에서 변경하지 않는다.

### 조성 가정

- public compiler는 명시적인 전체 context key track만 사용한다. key signature나 source Roman numeral을 몰래 읽지 않는다.
- 실제 trial의 가정 제안은 **context와 겹치는 모든 마디의 조표**를 관찰한다. 유일하고 표준 정수 fifths가 일관되면 호환 장조, 자연/화성/상행가락 단음계의 단조, `unknown`을 모두 제시한다.
- 조표가 변하거나 누락·모호·비표준이면 `unknown`만 둔다. 첫 마디/첫 조표를 실제 조성으로 선택하지 않는다. `mode_hint`도 확정값으로 쓰지 않는다.
- 이 다섯 가지는 모든 국소 key의 완전 탐색이 아니다. `unknown`은 signature 밖 조성·전조·다른 해석을 남긴다. 상행가락 단음계는 reference form이지 음표의 방향에 따른 자동 규칙이 아니다.
- microtone은 rational 철자 그대로 보존한다. 12-TET용 기존 순수 helper에는 denominator 1인 값만 전달하며 int truncation으로 1/2 alter를 0으로 바꾸지 않는다.

### Ordinary 기능 형태

`V`, `V7`, `vii`, `vii7`, `vii_half7` × target `M/m`을 전부 선언한다. source의 실제 root/member 철자와 가정 가족이 일치하는지, 실제 다음 path segment가 가정 target root/triad core와 맞는지 별도로 저장한다. 추가 target members·누락음·원 blocker는 버리지 않는다.

home tonic과 같으면 primary/parallel 형태, 다른 target이면 applied 형태의 **가정 좌표**다. `I` 형태가 `V/IV`로도 이어질 수 있고, 임시표 없는 applied 형태와 임시표 있는 primary가 가능하다. 임시표는 proof가 아니다. 다음 segment가 없으면 기대 target을 실제 도착 화음으로 발명하지 않는다. unknown key여도 source/target shape 관찰은 유지한다.

### 실제 해결

- 이끎음은 실제 register에서 상행 한 diatonic step와 정확히 +1 semitone, target-root 철자로의 진행을 검사한다.
- 7음은 실제 register에서 하행 한 diatonic step와 −1/−2 semitone, 가정 target member로의 진행을 검사한다.
- source sound의 실제 종료/target sound의 실제 attack과 다음 path span membership을 확인한다. pitch class만 맞고 octave나 철자 방향이 틀리면 해결로 승격하지 않는다.
- 지연은 같은 pitch/register의 carry만 통과하며 모든 연속 edge를 같은 bundle이 가져야 한다. 쉼의 틈·누락된 연결을 지어내지 않는다. 다른 장식 경로는 미지원으로 남긴다.
- 실제 다음 음의 identity/time/motion과 target boundary의 완전 triad 존재는 별도다. 분산화음의 구성음이 나중에 모였다는 사실을 경계의 동시 화음 증명으로 바꾸지 않는다.
- 원 full sound duration/source clock/pitch/tie/attack-origin 및 grace 전제 보류를 유지한다. 잘린 현재 clip이 맞는다고 full 계보의 결함을 승인하지 않는다.

화음 change 시점, 최초 critical sound의 실제 release, 마지막 carry sound의 release는 별도 좌표로 보존한다. 초기 pilot에서 change를 release처럼 명명한 필드는 동결 전에 교정했다.

### 같은 bundle의 공동 제약

한 bundle이 **전체 경쟁 path registry**와 연결된다. 각 path/key가 자신에게 유리한 witness를 따로 선택할 수 없다. 모든 raw lane endpoint가 disjoint이고 각 lane query/witness는 정확한 원 geometry에 바인딩된다. 누락 lane은 unknown이지 연결 불가의 증명이 아니다.

한 요청 안의 alternatives는 OR, 여러 명시적 요청은 AND다. 두 doubled leading tone을 항상 모두 해결하라고 강제하지 않는다. 실제 trial의 요청 범위는 모든 critical-voice singleton, 같은 function의 LT×7음 pair, 각각과 같은 path의 canonical NCT 한 규칙의 조합이다. 이는 모든 고차 multi-rule subsets의 완전 탐색은 아니다. 요청·branch·계산 예산은 전체 count를 먼저 검사하고 유리한 부분만 실행하지 않는다. 전체 OR 질의가 unknown이면 성공 branch 일부를 새 비교에 소비하지 않는다.

### 진행·종지 근거

같은 completion에서 raw 구성음/비구성음/미정 음가, 조건부 NCT 음가, 실제 LT/7음, 경계의 최저/최고음·기보 박자·뒤 지속/쉼을 독립 축으로 비교한다. 반복된 all-part denominator를 lane 수만큼 합치지 않는다. blocked 후보의 raw membership은 보존하고 qualified 보류를 별도로 둔다.

tonic/dominant/deceptive-like 도착의 **가정 형태 호환성**은 표시 가능하지만, 내부 V 도착이 곧 Half Cadence는 아니다. 가장 낮은 음이 구조적 bass인 것도 아니고, generic 4th+6th가 보이면 협화 6/4인 것도 아니다. PAC/HC는 구조적 성부·phrase terminal·지각 accent·협화 전제가 미확정이면 보류한다. 창의 끝에 도달한 것은 곡/phrase의 종결 증거가 아니다.

## 3. 실행 범위·예산·재현

입력은 완료된 frozen voice, source lineage, factor musical meaning 출력이다. 19작품군/33악보파일/322context/1,013raw lane의 분모와 모든 원 group/path/control·source/기존 단계 상태를 유지한다. 이전 output manifest와 현재 working IR/observation/audit/후보 group을 fresh 재생한다. 원 engine/selector/geometry producer는 재호출하지 않는다.

cohort 자체는 원 score–annotation hash pair와 정렬 적격성에 의존한다. 그 안의 관측 창 선정과 이번 추론은 harmonic label을 소비하지 않는다. 독립 holdout/33전곡 정답률로 세지 않는다.

기본 guard: 원 path-pair 4,096, path×key interpretation-pair 65,536, group의 formal function rows 16,384, joint requests 256; 각 함수의 formal rows 512, 해결 rows+모든 chain observation slots 1,024, carry chain edges 8, OR branch 256/질의 work 100,000. full inventory를 먼저 검사한다. 보류된 group은 원 inventory/정확 count·사유를 유지하며 첫 후보나 첫 chain으로 대체하지 않는다.

전체 cohort의 후속 실행 명령이다. **이번 단계에는 아래 전체 실행을 하지 않았다.** 실제 pilot은 별도 이름·version·완료 플래그로 저장하며 전체 실행 결과로 소비하지 않는다.

```powershell
$env:PYTHONPATH='K:/Music Analysis/src'
$env:PYTHONIOENCODING='utf-8'
./.venv/Scripts/python.exe -m musicanote_harness.factor_functional_trial `
  --baseline output/frozen-context-voice-2026-10-01-r1 `
  --lineage output/frozen-context-sound-lineage-2026-10-01-r1 `
  --musical-meaning output/factor-conditioned-musical-meaning-2026-10-01-r1 `
  --output output/factor-conditioned-functional-resolution-2026-10-01-r1
```

출력은 새 직계 폴더와 exclusive creation만 사용한다. 생성 시점 SHA·exact inventory, input/code hash·parent inventory를 종료 때 확인한다. 전체 실행기의 `complete`는 계산/보존 무결성이고 musical accuracy/human validation이 아니다. 별도 pilot은 `pilot_complete`와 `cohort_complete=false`를 쓰고 전체 실행기의 `complete` 필드는 갖지 않는다.

## 4. 개발 중 발견·보완 기록

- root key cue 테스트의 첫 fixture는 `key_signature=null`을 Core에서 허용된다고 가정하여 1오류를 냈다. 실제 Core 계약은 object와 nullable fifths였다. Core를 느슨하게 바꾸지 않고 malformed cue probe를 명시 mock으로 분리했으며 같은 9검사 재실행은 0.714초 통과했다.
- 독립 검토가 path-pair count만으로 path×5key interpretation pairs를 보호하지 못함을 발견했다. 별도 전체 interpretation-pair guard를 **배열 생성 전에** 추가했다.
- blocked segment를 raw unknown으로 바꾸면 기존 raw 음가와 달라지는 결함을 독립 검토가 발견했다. 비교 모듈에서 raw membership 보존/qualified 보류를 분리하고 반례를 추가했다.
- 전체 OR가 resource unknown인 상태에서 가능한 branch만 비교에 소비하는 wrapper 결함을 발견했다. fully-assessed joint_possible일 때만 bundle을 소비하며 원 branch 진단은 모두 저장한다.
- 동일 V7의 엄격한 LT와 7음이 각각 다른 pitch로 해결되므로, 인위적인 충돌을 음악적 사례로 만들지 않는다. 실제 doubled LT가 한 tonic target을 경쟁하거나 실제 LT B4→C5와 canonical B4→A4→G4 passing이 같은 outgoing edge를 경쟁하는 반례를 사용한다.
- group 하나에서 계산 예외가 나면 다른 group을 모두 잃을 수 있던 wrapper를 보완했다. 각 실패의 원 group ID/status/planned count와 오류를 보존하고 다음 group을 계속 검사한다. 실패가 있는 실행을 완료로 승인하지 않는다.
- 실제 첫 group 전체 후보 pilot의 계산 비용을 점검했다. 후보/음표를 줄이거나 원 예산을 몰래 바꾸지 않고 exact canonical input과 code/schema 계약을 사용하는 bounded immutable memo, 공통 boundary/view/bundle의 반복 투영을 구현했다. memo는 최대 512개/직렬화된 retained bytes 64 MiB 제한이며 프로세스 전체 RAM 제한이라는 뜻은 아니다. prepared bundle은 immutable snapshot/실제 code·schema bytes/약한 lifecycle registry에 묶이고 public validator는 fresh 계산을 수행한다. 호출자의 seal이나 skip flag를 신뢰하지 않는다.

## 5. 최종 코드 검증

소스 동결 후 신규 111개 검사(overlay 19, resolution 39, comparison 36, runner 17)가 50.621초에 통과했다. 별도 resolution/comparison 75개 재검사도 24.312초에 통과했다. 최종 전체 Python 회귀는 **2,917개/304.438초/OK**다. 이전 2,806개에 이번 111개가 더해진 코드 검사 수이며 악곡 수·음악 정답률이 아니다.

검사에는 직접/지연 해결 양성, 실제 철자·옥타브·시간 반례, 동일 outgoing edge를 놓고 경쟁하는 LT/NCT, doubled LT의 target 경쟁, 예산 보류, 변조·잘못 재봉인한 자료, immutable prepared/public fresh 동등성, 전체 OR 미검사 branch, group 실패 보존이 포함된다. 합성 양성을 실제 악곡 검증으로 세지 않는다.

## 6. 실제 고정 자료 pilot — 전체 cohort 실행과 분리

저장 위치는 [`output/factor-conditioned-functional-resolution-pilot-2026-10-01-r1`](../../../output/factor-conditioned-functional-resolution-pilot-2026-10-01-r1/pilot-report.json)이다. 전체 부모 registry의 첫 context를 순서대로 선택했으며 화성 라벨이나 유리한 결과를 보고 선택하지 않았다. 원 cohort가 주석/정렬 자격을 계승한 점은 그대로다.

- context key: `dcml:beethoven-quartets:n01op18-1_01`, `1340`, `cont_e19939557bb600b9a92a`.
- observation: `mfco_1c4bf40e559b9c80e463ae5c`; view: `fmview_7d62fe7a464f776d2adb61a2`, 내용 SHA `7d62fe7a464f776d2adb61a22b0163b82e19875af2166811f1e979f041aa5a0c`.
- rational 범위: `[308,619/2)` quarter. 주변 source/measure snapshots·원 spelling/음가/타이/전체 working 및 historical IR·audit/revision을 함께 저장했다. 새 XML이나 재생성 악보를 만들었다는 뜻은 아니다.
- 선언된 전체 분모는 19작품군/33package/322context/1,013raw lane. **이번 실행은 1package/1context/4raw lane**이며 나머지 321context/1,009lane는 미실행이다. 이를 33악곡 완료로 집계하지 않는다.
- raw lane 4개 중 geometry ready 3개와 `empty_lane` 보류 1개를 모두 보존했다. source gate는 clock-consistent 3개/no-positive 1개이며 성부·화성의 의미 승인이 아니다.
- 원 group 3개 전부 유지: `hold:full`의 31hold + 31동일구성음 split controls = 62path를 계산했다. `change:617/2`의 계획384path와 `change:309`의 계획744path는 원 `withheld_path_budget`로 남겼다. 보류를 첫 후보 샘플링으로 대체하지 않았다.
- 전체 62path×5key tracks = 310overlay, formal function rows 4,650개, resolution rows 10,430개, 공통 baseline bundle 1개, evidence vectors 310개/쌍 차이47,895개를 저장했다. 두 보류 group에 overlay 결과를 발명하지 않았다.
- **function 4,650개 및 resolution 10,430개는 전부 보류**다. source 형태 호환390개도 실제 다음 target 전제가 없거나 맞지 않아 확정되지 않았다. hold path의 후속 segment 부재/같은-member split의 target 형태 불일치가 주요 제한이다. 그러므로 joint requests/branches/조건부 해결 양성은0이며 secondary 인식 향상·악곡 내 secondary 부재를 주장하지 않는다.
- pilot 전체124.033초, 세 group 평가103.711초, 계산 오류0. `pilot_complete=true`, `cohort_complete=false`; 전체 실행 `complete` 필드는 없다. 음악 정확도/사람검수/학습/gold/생성/UI/구조 분석 승격은 없다.
- 보호 input SHA4,379개/current source·schema293개/관련 test4개와 exact parent inventory를 대조했다. 등록artifact5개 + pilot-report1개를 새로 저장했으며 원자료/부모output/code 변동0이다. 각 artifact 생성 SHA는 보고서에, 부모와 코드 SHA는 pilot-plan에 있다.
- pilot-report SHA: `0b2af700692ee06c31ee76ad80db397948474a24ae4c3823978651e67e693c54`.

저장 파일: `pilot-plan.json`, `case.json.gz`, `working-ir.json.gz`, `historical-ir.json.gz`, `source-observation-audit.json.gz`, `pilot-report.json`. case 안에는 모든 원 group, 결과, ready graph, full completion bundle/query/witness, key/functional/resolution/evidence snapshots와 참조가 있다. 전체 실행기의 완료 manifest로 오인하지 않도록 별도 `factor-functional-scoped-pilot-0.1.0` version을 사용한다.

동결 후 같은 실제 group의 별도 단계별 측정은 function4.240초/resolution31.347초/bundle0.261초/comparison73.240초, public fresh replay78.620초였다. 초기 combined pilot243.996초와 측정 조건/캐시 상태가 동일하지 않아 통제된 속도 개선율로 계산하지 않는다. public fresh replay는 새 입력 검증·bundle 준비·재계산의 동등성 검사이고 후보가 음악적 정답임을 인증하는 검수가 아니다.

### 저장 결과의 독립 감사

독립 검토가 보호된 전체 index와 선언322context/1,013lane, 실행1/4 및 미실행321/1,009를 exact 대조했다. group3개/원 stage·final status·source gate·working/historical IR·observation/audit 부모 copy가 모두 일치했다. 전체 sound/note/measure/source-ref snapshots와 rational 좌표가 원 IR과 맞으며 code/input/test/artifact SHA 및 출력6파일 inventory도 통과했다.

공통 baseline의 no-link query/witness를 저장 factor에서 별도로 계수해 4/4/49 counts와 3/3/6 event endpoint partition을 확인했다. 같은 전체62path registry를310overlay/evaluation이 공유하며 boundary records3개, literal motion slots11,530개와 thin assessment refs10,430개의 seal/참조 대상도 닫혀 있다. 함수4,650/해결·bundle assessments10,430 모두보류, 쌍 차이47,895, request/solution0을 독립 집계했다. 이 감사는 query/producer 재실행이나 음악 정답 검수가 아니다.

또 다른 검토는 원 IR/mfco/audit로 public view exact replay0.734초와 **저장 baseline 비교 `fmfcmp_10a55eff6746f3f9e0f1322b`의 public fresh replay68.219초**를 통과했다. 새 factor geometry producer 호출을 금지한 상태였고 입력 내용은 불변이었다. 기존 단계의 분모·원시 근거를 다시 생성해 바꾸거나 cache 출력만 신뢰한 검사가 아니다.

최종 관련12파일의 strict UTF-8/NUL/U+FFFD/후행 공백 검사는0오류다. 화성4문서의 상대 링크109개/깨진 링크0개, 의도치 않은 일본어 문자0개를 독립 확인했다. read-only `git diff --check`도 오류0이지만 현재 새파일/문서는 untracked이므로 그것만으로 새파일 검증을 대체하지 않았다. 다른 기존 workspace 변경과 `.git`은 건드리지 않았다.

## 7. 코드 위치와 다음 단계

- `src/musicanote_harness/factor_functional_overlay.py`
- `src/musicanote_harness/factor_functional_resolution.py`
- `src/musicanote_harness/factor_functional_comparison.py`
- `src/musicanote_harness/factor_functional_trial.py`
- `tests/test_factor_functional_overlay.py`, `test_factor_functional_resolution.py`, `test_factor_functional_comparison.py`, `test_factor_functional_trial.py`

다음 큰 단계는 후보·원음·보류 분모를 줄이지 않는 공유 평가/대량 비교 비용 개선과, 실제 change path를 포함한 여러 고정 문맥의 기능·cadence 전제 검증이다. 첫 pilot을 이유로 비용이 큰 전체322context 실행을 완료 처리하지 않는다. 이후 대표 전곡 악보 표시·사람 피드백, 구조 분석의 제한적 소비를 진행한다. 지금 원주석/교재 규칙을 무시하거나 생성 목표를 잊은 것이 아니라, 그 규칙이 실제 동일 성부와 시점에서 성립하는지 검증할 공통 기반을 마련하는 단계다. 화음 상대 슬롯/반주 의미와 생성 로드맵은 유지하지만 G1 전체·생성기 완료는 아니다.
