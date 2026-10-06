# 가짜 주석 없는 기존 문맥 관찰과 성부 제약 연결

기록 ID: **HARM-DEV-20261001-07**. 날짜: 2026-10-01.

## 목표와 기존 단계

사용자는 이전 단계를 승인하고 계속 진행하도록 요청했다. 직전 [성부 factor graph](2026-10-01-factorized-voice-constraints.md)의 14악보파일/27관찰/143raw lane 검사는 원주석 `Pedal`의 명시적 구간을 출발점으로 했다. 이번에는 그 표본에만 머무르지 않고, 이미 보존된 Beethoven/Mozart/Chopin/Corelli 등의 **19작품군/33package/322문맥**을 같은 손실 없는 계산으로 연결한다.

이번 큰 기능 단위는 **일반 관찰의 출처 계약과 기존 문맥 연결**이다. 조성/secondary/기능/종지나 역할의 최종 선택을 구현했다고 선언하지 않는다. 기존 322문맥의 진행 제안/공동 비교와 원래 화성 단계의 후보·보류는 보존한다. 사례의 특정 제목/마디/음높이는 계산 조건에 넣지 않는다.

## 분리한 계약

새 `frozen_context_observation` v0.1.0은 별도 schema/`mfco_` ID를 사용한다. 원주석 SOURCE에 정확히 정렬된 기존 `musical_pattern_observation` v0.1.0과 그 SOURCE/좌표 gate는 바꾸지 않는다. 새 계약에 `source_statement_ref`나 `alignment_ref`를 가짜로 만들거나 null로 완화해 넣지 않는다. 기존 SOURCE 소비자는 새 관찰을 그대로 승인하지 않는다.

공통 binding은 score ID, **실제 선택한 working IR**의 document ID/canonical content SHA, 원 `source_files`, 유리수 `[start,end)`다. 이번 target 정책은 `full_frozen_context`: target=context이며, 사람 주석에 해당하는 범위라고 주장하지 않는다.

새 `origin.kind=frozen_context_window`에는 다음을 남긴다.

- `(pair_id, plan_index, sample_id)`, 원 sample 전체와 선정 lane/index.
- selector 버전/방법, 원 score+annotation hash pair와 역사적 alignment 자격에 의존하는 cohort 이력.
- 역사적 parent IR과 working IR의 별도 identity/hash, 명시적 revision 선택.
- integration index/packet, 원 stored packet, frozen plan row/package, revision row/sidecar, parent IR의 **각 logical content SHA**.
- 원 gzip/IR 파일의 **byte SHA**와 artifact 경로. 파일 byte SHA, IR canonical SHA, bundle SHA를 대체해서 쓰지 않는다.
- 기존 stage/final/revision 상태와 미검수/비학습/비생성 자격.

관찰 레코드의 seal은 내부 동등성 검사다. 단독 seal을 원자료 출처 인증으로 간주하지 않는다. 부모를 다시 제공한 pure validator는 exact origin/binding을 재구성한다. 파일 권위·등록 inventory·원 source bytes·selector 전체 재생·물리 마디 교정은 runner가 따로 확인한다.

## 창 선정과 전체 파트의 분모

기존 breadth v0.1.1은 전체 악보의 36,820개 attack-group window 중 **각 명시적 lane의 내부 quantile 2개**를 선택했다. 창 선정에 화성 라벨이나 성공 여부를 쓰지 않는다. 그러나 cohort 자체는 역사적 score+annotation identity와 alignment admission에 의존하므로, 완전히 annotation-independent 평가 표본이라고 부르지 않는다. train 27/dev 6 package이며 holdout은 포함하지 않는다.

새 관찰은 sample lane만 추출하지 않는다. context와 겹치는 모든 part의 note/rest와 point grace를 보존하고, tie/chord/grace anchor의 바깥 연결 음표를 context-only로 닫는다. 이 literal closure에서 관측된 `(part_id,voice_id)` 전부가 raw-lane 분모다. 악보 전체에 등록되어 있지만 이 context에서 전혀 관측되지 않은 silent voice를 새로 추가하는 계약은 아니다.

읽기 전용 독립 사전 감사에서 **322문맥/1,013raw lane**이 확인됐다. 양의 sounding event를 가진 lane 973개, 나머지 rest/grace 등의 raw-only lane 40개다. 양성 sound가 없는 단위를 제외해 분모를 줄이지 않는다. 계산 준비 여부/예산/원 stage 상태를 확인하기 전에 문맥별 전체 lane을 선언한다.

## 부모·판본 검증과 보존

입력 정본은 `output/harmony-context-integration-trial-2026-09-30-r1/`이다. 상위 breadth r2와 source-sequence-replay r1을 연결한다. integration 등록 artifacts 358개(322packet/33sidecar/3candidate IR)와 report/contract 2개, 정확한 360파일 inventory를 대조한다.

33package의 선택은 원 IR 30개/제한 measure-core candidate 3개다. `validate_revision(parent,candidate,sidecar)`를 fresh 호출하고, `not_required`도 replay payload로 다시 확인한다. 같은 source XML SHA라는 이유로 parent/candidate IR을 교체할 수 없다. 두 candidate의 direction extension 잔여 참조는 여전히 parent-bound다. source locator나 주석/extension의 자동 retarget을 하지 않는다.

`bundle.parent_ir_document_id`는 이름과 달리 실제 bundle 입력인 **working IR** ID다. 역사적 parent는 packet provenance에서 별도로 대조한다. `bundle.input_sample_content_sha256`은 **원 stored packet 전체**의 canonical digest이며 내부 `sample`이나 gzip byte SHA가 아니다. 기존 5stage 1,610개는 원 packet과 exact content 동등성을 대조하고 복제/재계산하지 않는다.

새 runner는 integration의 직접 input/producer 계약과 상위 breadth/replay의 명시적 input hash를 보호한다. integration의 직접 목록 밖에 있던 cohort 원파일 2개와 replay 상위 input 98개도 포함한다. breadth의 `inventory.json`, `progress.json`, 33개 source provenance 파일은 알려진 진단 artifact로 별도 byte snapshot하며 provenance 내용은 frozen plan의 source와 정확히 대조한다. 이 진단을 성공 표본 선정이나 음악 판단에 사용하지 않는다.

과거 breadth의 producer code hash는 후속 캐시 구현으로 달라졌다. **과거 엔진을 재실행하지 않고 보존된 stage를 읽는 계약**이므로 옛 breadth code와 현재 code가 같아야 한다고 요구하지 않는다. 실제 재생하는 selector/revision/current factor code와 schema는 새 run plan에서 freeze하며, integration producer의 보호 code도 대조한다. 이번 보호 범위는 명시적 부모 계약/input 집합이지 repository의 모든 과거 실험에 대한 무제한 재귀 보증이 아니다.

## 계산과 해석의 경계

새 `harmony_frozen_context_voice_trial` v0.1.0은 직전 `_unit`의 검증된 factor 계산을 재사용한다. 정확 release=attack인 동일 raw lane의 모든 부분 대응과 무연결을 보존하며 global enumeration은 하지 않는다. 전체 IR의 독립 literal positive projection, fresh graph replay, 원 source/attack/tie 계보를 대조한다.

ready graph마다 다음 **산술/분할 control**만 계산한다.

1. 무제약 count와 sparse completion.
2. 각 boundary의 한 edge를 동시에 요구한 단일 공동 조건.
3. 모든 edge를 금지한 무연결 control(count=1).

이 control이나 witness를 NCT/성부/화성의 음악적 지지로 쓰지 않는다. 별도 질의의 witness들을 하나의 해석으로 합치지 않는다. count는 확률/신뢰도가 아니다. sampled grace/point, 빈 positive lane, 계보 오류나 resource 한도는 보류하며 결과 단위를 제거하지 않는다.

원 lattice ready 291/보류 31, 끝단계 ready 243/보류 79를 geometry ready와 혼동하지 않는다. 원 annotation/hash/권리/split 및 전체 stage 내용은 그대로 유지한다. 새 observation에는 화성 가정/역할/최종 NCT를 붙이지 않는다.

## 구현 파일과 실행 상태

- `src/musicanote_harness/frozen_context_observation.py`
- `docs/harmony/schemas/frozen_context_observation.schema.json`
- `tests/test_frozen_context_observation.py`
- `src/musicanote_harness/harmony_frozen_context_voice_trial.py`
- `tests/test_harmony_frozen_context_voice_trial.py`
- `src/musicanote_harness/sounding_lineage_audit.py`
- `tests/test_sounding_lineage_audit.py`
- `src/musicanote_harness/harmony_frozen_context_lineage_trial.py`
- `tests/test_harmony_frozen_context_lineage_trial.py`
- 이 상세 기록 및 별도 화성 README/개발 로그/생성 로드맵.

첫 구현의 전체 회귀·실제 cohort run·두 독립 출력 감사를 완료했다. 이어 inherited source-clock/attack-origin 문제를 검사하는 별도 sidecar의 전체 실행과 두 독립 감사를 완료했다. 기존 output은 덮어쓰지 않는다.

구현 중 실제 부모 대조에서 두 계약 오류를 확인해 보완했다. 첫째, integration bundle은 원 5stage를 보존하면서 `missing_evidence`를 추가하므로 전체 stage dict 동등성은 잘못된 조건이었다. 원 stage projection의 exact 동등성과 알려진 추가 stage만 허용하는 검사로 수정한다. 둘째, integration의 직접 hash 목록에 없는 breadth 진단/provenance를 등록 목록과 구별해 보호하고, 재실행하지 않는 obsolete breadth producer code와 현재 code의 동등성을 잘못 요구하지 않도록 분리했다. 모두 기존 자료 오류나 음악적 오판으로 해석하지 않으며 새 실제 output 생성 전의 개발 검증이다.

추가로 새 runner의 첫 fixture 실행에서 `observations/` 디렉터리 미생성으로 19개 중 6개가 오류를 냈다. 저장 경로 생성을 보완한 뒤 최종 신규 runner 29개가 모두 통과했다. 독립 검토에서 결과 파일의 최종 hash만 새로 기록하면 중간 변조를 정상 결과로 채택할 수 있음을 확인하여 **생성 직후 byte SHA와 최종 정확 inventory**를 대조하도록 했다. 파일 교체·누락·추가의 세 반례를 포함한다. output은 기존 breadth/replay/integration 안에 생성하지 못하도록 workspace `output/`의 **존재하지 않는 직계 하위 폴더**만 허용한다. 입력 계획의 hash map도 별도 copy로 동결한다.

## 검증 결과와 범위

첫 신규 테스트는 observation adapter 19개와 runner 29개, 총 **48개**다. runner 단독 29개/34.765초, adapter+기존 SOURCE+revision 71개/6.141초, 관련 모듈 177개/62.573초를 통과했다. 첫 전체 Python 회귀는 **2,670개/155.312초/OK**다. 이 숫자는 검증 프로그램의 수이며 음악 작품 수나 화성 정답 수가 아니다.

source-clock 보완은 pure auditor **16개**와 새 sidecar runner **25개**, 추가 **41개/50.715초/OK**다. 이번 기록의 신규 검사는 합계 **89개**이고, 보완 후 최종 전체 Python 회귀는 **2,711개/208.777초/OK**다. 독립 읽기 코드 검토 및 보완 전 39개/46.993초 재실행에도 차단 문제는 없었다. 이후 명시적 selector 변조와 point/실제 충돌 혼합의 두 반례가 더해졌다. 두 focused 실행의 숫자를 서로 더하거나 음악적 양성 수로 사용하지 않는다.

부모 자료의 독립 읽기 대조는 전체 322개의 plan/sample/index/packet/IR 판본 연결과 원 5stage 1,610개의 exact 보존, all-part raw lane 1,013개와 직접 입력 1,209파일의 불변을 확인했다. runner 사전 적재는 상위 명시적 input까지 확장한 **1,344파일**을 보호한다. 다른 분모를 합산하지 않는다. 실제 5문맥의 pure contract compatibility 검사도 원 IR/제한 candidate/기존 예산 보류를 포함해 통과했다.

### 실제 r1 결과와 두 독립 감사

`output/frozen-context-voice-2026-10-01-r1/`은 **1,914.840초/exit 0**으로 완료했다. 19작품군/33악보파일/322관찰/1,013raw lane을 모두 유지한다. geometry ready **942**, 보류 **71=빈 positive lane 40+장식/point timing 미지원 31**이다. grace와 point 두 reason의 31은 같은 단위에 중첩하며 62개 보류로 합산하지 않는다.

ready graph의 정확 산술 control과 query-local completion은 각각 **2,826개**다. positive sound instances 5,937, context point instances 288, factors 3,554, 최대 count는 123자리다. 중복 문맥/graph에 노출된 instances는 전곡 고유 음표 수가 아니다. 기존 보류 문맥에서 나온 geometry ready 239개도 원 화성 단계 보류를 승격하지 않는다. 원 끝단계 ready 243/pair-budget 48/baseline 28/edge-budget 3 및 stage별 전체 목록은 불변이다.

두 독립 읽기 감사가 전체 322identity·sample/selector·working-IR/revision/hash·원 5stage 1,610개·all-part literal slots 6,717개·1,013분모와 index를 대조했다. 모든 factor의 release/attack endpoint·닫힌형식 부분 대응 수·공동 required/no-link 조건·seal·completion ID·chain partition이 일치한다. 원 SOURCE/legacy 전역 열거/화성/NCT를 다시 실행한 검사가 아니다.

입력 **1,344**/current code·schema **283**/새 등록 artifacts **1,338**의 SHA와 정확 inventory가 불변이다. 실제 파일은 report 포함 **1,339**개다. 보고서의 complete/input-code/artifact/computation-integrity는 strict true, 변경/누락/추가 0이다. 단 이는 저장된 IR에 대한 보존·산술 검사이며, 아래 기존 full-chain 결함을 인증하거나 없애지 않는다. scoped sound 5,396개를 IR binding별 중복 제거한 별도 시간 대조에서 1개 결함을 확인했다. 어떤 창에도 나타나지 않은 전곡의 모든 sound를 전수 검사한 수치가 아니다.

원자료/부모 IR/주석/기존 outputs/parser/Core schema/권리·split/gold/학습/운영5173·구조분석/악보뷰어/API/Git는 변경하지 않았다. human-validated/training/gold/generation-ready는 모두 0이며 음악 정답률을 측정하지 않았다.

### 재현 명령

PowerShell에서 repository root와 기존 `.venv`를 사용한다. output 이름은 반드시 새 폴더로 바꾸고 기존 결과를 삭제하거나 덮어쓰지 않는다.

```powershell
$env:PYTHONPATH = 'K:/Music Analysis/src'
$env:PYTHONIOENCODING = 'utf-8'
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -m musicanote_harness.harmony_frozen_context_voice_trial --integration 'K:/Music Analysis/output/harmony-context-integration-trial-2026-09-30-r1' --output 'K:/Music Analysis/output/frozen-context-voice-2026-10-01-r1'
```

실행 전 모든 package의 selector/물리 revision을 fresh 대조하고, 실행 시 package별로 다시 확인한다. 전곡 IR을 모든 lane에서 반복 hash/scan하는 현재 구조는 큰 편성에서 비용이 커질 수 있다. 후속 최적화는 exact package snapshot에 연결한 geometry-only preparation을 검토할 수 있으나 이번 실제 실행에서 cache/근사 pruning/예산 상향은 추가하지 않았다.

### 실제 저장 형태의 예

`observations/mfco_1c4bf40e559b9c80e463ae5c.json`은 Beethoven 현악4중주 Op18-1 제1악장의 기존 `cont_e19939557bb600b9a92a` 창에서 생성됐다. `[308,619/2)` quarter의 네 part/voice를 보존하며, 하나는 `rest_692353a266a6`, `rest_3f2d7f9155eb`만 가진다. 그 lane도 결과 분모에 남는다. scope의 working IR은 `ir_99bb0d9355c3`, origin은 `frozen_context_window`이며 seed lane과 모든 실제 lane은 다르다. 원 SOURCE 주석을 만들어 넣지 않는다.

파일의 source XML SHA, working IR canonical SHA, 원 packet canonical SHA와 gzip byte SHA는 각각 별도 필드에 저장한다. 이 예는 계약의 실제 적용 사례이지 특정 악장의 판정 규칙·페달/화성 정답·독립 평가 양성이 아니다. 완전한 음표/음가/계보는 레코드의 literal 영역과 원 working IR에서 재현한다.

## 독립 검사에서 발견한 기존 타이·성부 결함

실제 r1의 산술 대조 중 `dcml:chopin-mazurkas:BI105-3op30-3` / plan 465 / `cont_27fdd32812c31998d906`에서 기존 full-chain 결함을 발견했다. 원 working IR은 `ir_21240d693587`, canonical SHA는 `a3655cfcd565eaf87c15c2ae0fe278b2503c8acf39fb386194ad4e6a4aaeb9f0`이다. 관찰은 `mfco_e1c5a4cbeda927ffd8a27271`, 선택 lane 단위는 `f056f51132f58713.json.gz`이다.

- 저장된 F3 `sound_b4ac7c23b582`는 `[216,234)`이지만 source notes는 onset 216/219/228/231, 각각 3quarter로 합 12quarter다. full span 18quarter와 다르고 `[222,228)`에 source-member 공백이 있다.
- 독립 원 XML 대조에서 P2의 73–78번째 물리 마디는 모두 voice 1의 F3, duration 36/divisions 12=3quarter, 연속 start/stop+start/stop tie다. **XML은 끊기지 않았으며 실제 6quarter 쉼이 아니다.**
- IR의 onset 222/225 음표 `note_26ef2ed8b152`/`note_5d53312d434f`만 다른 voice로 배정됐다. 별도 `sound_147beb25df56`/`tie_7a707c6ae4ec`가 `[222,228)`을 가지며 첫 continuation을 attack으로 취급한다. 두 sound의 합은 24quarter지만 원 6notes의 합은 18quarter다.
- 기존 `canonical._sounding_events`는 continuation 연결 시 이전 end와 새 onset의 연속성을 검사하지 않는다. `canonical._voice_id`의 이전 Voice 문맥 상속은 voice 오배정의 가능한 원인이지만 재파싱 원인 분석 전까지 추정으로 둔다. 신규 관찰/revision이 이 결함을 만들지 않았다.
- 현재 sampled context `[216,220)`의 원음표 coverage는 연속 4quarter로 맞는다. **현재 clipped coverage 불변과 full-source lineage 인증 실패를 구별**한다. storage/provenance 및 factor 산술 일치가 기존 derived sound의 음악적 정확성을 인증하지 않는다.

r1은 원상태 진단 결과로 완결·보존한다. 원 XML/IR/parser를 즉석 덮어쓰거나 그 악장만의 예외 규칙을 만들지 않는다. 전체 scoped sound의 span-duration/source-duration sum/source-member adjacency를 일반 검사로 대조하고, 불일치 계보를 후속 의미 해석에서 보류하는 별도 versioned audit를 추가했다. 실제 영향과 중복 제거한 분모는 아래 결과에 기록한다. 이 source guard가 통과해도 화성/NCT/성부 역할이 승인되는 것은 아니다.

### 별도 source-clock 진단의 계약

`sounding_lineage_audit` v0.1.0은 정확히 하나의 span 또는 명시적 sound ID 목록을 받아, supplied IR의 notated clock만 대조한다. `msla_` ID/seal과 score·IR document/content SHA·원 source inventory를 연결하고, fresh validator가 명시적으로 제공한 IR/선택/문맥으로 전체 결과를 재생한다. 원 sound와 source notes의 snapshots 및 순서를 보존한다. XML 권위·실제 대위법 성부·실음·연주시간·화성/NCT/역할을 인증하지 않는다.

각 sound의 **full chain**과 **context-clipped** ledger를 따로 저장한다. source duration 합, interval union, 실제 coverage, 공백, 중첩, sound 범위 밖 음가, attack origin, continuation/stop을 새 attack으로 둔 상태 등을 유리수로 대조한다. source 합이 span과 우연히 같아도 gap/overlap이 있으면 통과시키지 않는다. missing source ID/null snapshot, 빈 선택, 음가 미지원은 제거하거나 0으로 채워 인증하지 않는다. point grace는 기보 관측을 보존하되 performed timing은 unknown으로 둔다. 이 unknown은 손상된 XML 또는 음악적 오류의 증거가 아니다.

별도 `harmony_frozen_context_lineage_trial` v0.1.0은 **완료·보호된 frozen-context voice r1**을 부모로 삼는다. 동일한 322관찰/1,013raw lane 전체를 유지하고 literal closure의 모든 sound를 검사한다. whole-context full-chain 상태와 각 lane의 실제 active/point sound에 영향을 주는 상태는 분리한다. 다른 lane의 결함 때문에 현재 lane의 음가까지 틀렸다고 주장하지 않는다. rest-only lane은 `not_applicable`이지 음악 해석 승인이나 실패 표본 삭제가 아니다.

입력·옛 code·원 output의 정확 byte SHA와 inventory를 보호하고, observation literal/IR을 사전 대조한다. 이미 완료한 8부모 원 stage 검사를 source-clock sidecar 생성 때 다시 해제·재실행하지 않는다. 대신 보호된 baseline과 가벼운 package/revision/원 index·scope/origin content bindings를 연결한다. 기존 unit packet/geometry의 별도 canonical SHA·status/reasons·probe inventory를 gate에 남긴다. baseline producer의 옛 code inventory와 새 auditor의 additive inventory는 별도로 동결한다.

새 output의 artifact는 생성 직후 SHA와 최종 정확 inventory로 대조한다. 진단 계산/저장/보존의 `complete`와 source-clock의 통과 여부는 다르다. 실제 불일치를 발견했어도 진단 작업 자체는 complete일 수 있다. 신규 sidecar는 후속 소비자용 guard이며 production parser·기존 IR·기존 geometry/status·5173/UI를 수정한 것이 아니다.

sidecar 개발 검토에서 raw-note ownership은 존재하지 않는 `core_projection.note_events`가 아니라 `slots[].core_event`에서 가져오도록 바로잡았다. 전체 옛 stage gzip을 반복 해제하는 최초 검증 경로도 보호된 완료 baseline+fresh literal 사전 검사와 실행 시 seal/byte/provenance 대조로 줄였다. 근사 계산이나 표본 pruning은 하지 않는다. 초기 테스트의 첫 lane/slot이 rest인 점, mock 대상 함수명, note의 `written_pitch`와 sound의 `pitch` 차이로 난 fixture 오류도 보완했다. 이 오류들을 실제 악보 실패로 집계하지 않는다.

장식음만 미확인인 경우는 `withheld_point_timing_not_assessed`, 실제 양의 sound 계보와 충돌하는 경우는 `withheld_source_clock_conflict`로 구별한다. 두 종류가 혼합되면 실제 충돌 보류를 지운 채 point-only로 분류하지 않는다. auditor가 전달받은 IR/관찰/명시적 선택 ID 목록을 바꾸는 반례, 원 input/code 변화, output 생성 직후 교체·누락·추가도 검사한다. 실패 결과의 분모는 그대로 남긴다.

### source-clock sidecar 실제 r1 결과

`output/frozen-context-sound-lineage-2026-10-01-r1/`은 **794.265초/exit 0**으로 완료했다. 사전 literal 대조 동안 output을 생성하지 않으므로 처음에는 진행 출력이 없다. 전곡 Core schema/참조를 문맥별로 반복 검사하는 비용이 남아 있다. 후속 immutable package preparation은 exact binding을 유지하는 최적화로 검토하되, 이번 run 도중 코드를 바꾸거나 검사를 생략하지 않았다. 완료 baseline의 대형 옛 stage gzip을 다시 해제하지 않는 정책은 25개 runner 테스트에서도 확인했다.

동일한 33package/322관찰/1,013raw lane이다. whole-context source-clock 통과 **281**, 불일치 또는 미평가 **41**이며 진단 계산 오류는 **0**이다. 개별 lane의 guard는 다음처럼 나뉜다.

| 개별 lane 상태 | 수 | 의미 |
|---|---:|---|
| `source_clock_consistent_not_semantic_approval` | 926 | 선택한 active 음의 기보 clock 대조 일치. 화성/NCT/역할 승인 아님 |
| `not_applicable_no_positive_sounds` | 40 | 양의 sound가 없는 raw lane도 분모에 보존 |
| `withheld_point_timing_not_assessed` | 31 | 장식음의 performed timing 미확인. XML 오류 아님 |
| `withheld_source_clock_conflict` | 16 | 아래 음가 불일치 1단위와 attack-origin 보류 15단위 |

새 audit의 literal closure sound 노출은 **6,033instances**, IR canonical SHA+sound ID로 중복 제거한 **5,405sounds**다. graph마다 모든 context point를 반복 참조한 직전 geometry의 point instances 288, 이번 문맥별 grace 진단 84, 고유 grace points 83은 서로 다른 분모다. 새 범위는 active sound 외에 linked context-only sound도 포함하므로 앞의 active/scoped 5,396개와 직접 비율 비교하지 않는다.

- **실제 full 음가 불일치:** 앞의 F3 한 sound/한 lane 단위다. audit `msla_c67dc1243c14ba4b161a87a6`는 full source 합/coverage 12q 대 span 18q와 gap `[222,228)`을 보존하고, clip `[216,220)`의 합/coverage 4q·gap 없음도 별도로 보존한다.
- **attack-origin 보류:** 18audit instances/12고유 sounds(11stop origin/1continue origin)다. 이 12개는 full coverage가 연속하며 음가 합=span, 중첩/공백은 없다. 유일한 blocker는 IR이 tie continuation/stop을 attack origin으로 둔 상태다. 양의 음가 오류 12건 또는 XML 오류 12건이라고 부르지 않는다. 15lane 단위에 영향을 주며 원 XML/실제 시작 여부의 원인 규명·교정은 후속이다.
- **전체 영향:** 위 두 종류의 source-clock guard 보류는 16lane/15문맥/6IR·score binding이다. 기존 geometry에서는 모두 ready였지만 원 geometry/status는 그대로 보존하고 별도 guard를 덧붙인다.
- **현재 문맥 음가:** positive active instances **5,937개 모두** clipped coverage 대조가 통과했다. 12positive closure instances는 현재 문맥 밖이어서 clip 미평가다. 따라서 이번 보류를 현재 구간 음표가 모두 사라지거나 잘못 늘어난 것으로 해석하지 않는다. full 계보/새 attack의 신뢰 문제와 현재 음가를 분리한다.

두 독립 읽기 감사에서 전체 source/sound snapshots, exact Fraction sweep의 full/clipped ledger·attack 진단·seal, 모든 context/lane key와 guard 분류가 일치했다. 새 등록 artifacts **325**/실파일 **326**, 보호 input **2,708**/current code·schema **285** 및 이전 baseline 1,338+report/상위 integration·breadth·replay inventory/SHA는 불변이다. input/code 집합의 중복을 제거한 보호 파일은 2,710개이며 분모를 단순 합산하지 않는다. 부모/working binding은 historical 290관찰/candidate 32관찰로 원33package의 명시적 판본 선택을 계승한다. 기존 ready942/보류71, byte/canonical geometry SHA·reasons·probe inventory·원 stage 상태도 모두 보존했다.

`complete`, `inputs_and_code_unchanged`, `artifacts_unchanged`, `computation_integrity_passed`는 strict true다. 전체 `source_clock_consistency_passed`는 false가 맞다. 변경 목록/계산 오류는 빈 목록/0이며 human/training/gold/generation은 모두 0이다. 생성·의미 해석 자격을 승인하지 않았다. independent ledger/gate 감사는 8.45초, 보존 감사는 대기 포함 550.179초였다. 이 시간들을 실제 sidecar runtime이나 음악 정확도로 합산하지 않는다.

마무리 검사에서 이번 13개 변경 파일의 strict UTF-8/대체문자·trailing whitespace, 네 개발 문서의 상대 링크 101개, 해당 변경 범위의 `git diff --check`가 통과했다. 최종 독립 문서 대조에서도 실제 수치와의 충돌·완료된 sidecar의 오래된 진행중 표시는 없었다. 인수인계 문서나 구조 분석 로그로 옮기지 않고 화성 개발의 메인/로그/상세 기록/생성 로드맵에 같은 상태를 반영했다.

새 sidecar 재현 명령은 다음과 같다. 존재하는 r1을 덮지 말고 다른 새 output 이름을 선택한다.

```powershell
$env:PYTHONPATH = 'K:/Music Analysis/src'
$env:PYTHONIOENCODING = 'utf-8'
.venv/Scripts/python.exe -m musicanote_harness.harmony_frozen_context_lineage_trial --baseline 'K:/Music Analysis/output/frozen-context-voice-2026-10-01-r1' --output 'K:/Music Analysis/output/frozen-context-sound-lineage-2026-10-01-r1'
```

## 다음 큰 기능

이 연결 다음에는 factor graph의 **공동 required/forbidden 조건을 실제 음형의 준비·해결·박절·화음 membership과 결합**한다. 경쟁 화음 진행과 같은 성부 가정에서 조성·secondary·기능·cadence 및 chord-relative 반주 슬롯 대안을 비교한다. 주석 라벨을 소비하지 않는 창 관찰만으로 페달/분산반주를 확정하지 않는다. 코호트의 역사적 주석/alignment 의존은 그대로다. 이후 독립 검증과 전체 악보 뷰어 승격, 구조/작곡/편곡 연결을 진행한다. 별도로 보류된 관현악 실음/판본/정책을 이번 cohort에 몰래 승인하지 않는다.

다음 구현의 완료 기준은 다음 네 가지다. 산술 control을 음악 판단으로 이름만 바꿔 공급하지 않는다.

1. 기존 조건부 음형·직접/시간 해결의 실제 note IDs에서 필요한 연결/금지 연결을 만들고, 관측 박절·지속·membership과 가설을 분리해 저장한다.
2. 같은 진행 대안에서 여러 규칙이 **같은 성부 대응 하나 아래 함께 성립하는지** 검사한다. 규칙별로 가능한 서로 다른 witness를 하나의 음악 해석처럼 합산하지 않는다.
3. 구간의 모든 원음가를 구성음/조건부 설명/미설명/미지원으로 보존하고, 유지·화음 변화·불완전 구성·반주 역할의 경쟁 대안을 동일 문맥에서 대조한다.
4. 새 전체 분모에서 실제 계산 가능/조건 충돌/원래 보류/시간 범위 부족을 분리하고, 사람이 확인할 실제 양성·근접 반례를 전체 악보로 보여 줄 준비를 한다. confidence calibration·최종 선택·generation-ready는 이 계약만으로 승인하지 않는다.

### 후속 의미 계층의 최소 접점과 주의사항

독립 코드 검토에서 다음을 확인했다. 아래는 다음 구현의 요구사항이며 이번에 의미 evaluator까지 적용했다는 뜻이 아니다.

- `musical_role_evidence`/`musical_progression_role_link`는 기존 SOURCE observation의 validator/scope 계약을 사용하고, `progression_context.evaluate`는 legacy `supporting_assignment_refs`를 요구한다. 새 `mfco_` 관찰과 `vfcompletion`을 이 구버전 schema나 old assignment 재고로 위장하지 않는다. **별도 versioned common observation view와 factor-conditioned evaluator**를 만들어 필요한 literal 사실을 연결해야 한다.
- 현재 `factor.query`는 직접 edge들의 AND(`required`)와 NOT(`forbidden`)를 계산한다. 기존 `resolution_constraints.required_link_options`의 OR 대안을 전부 required로 평탄화하면 잘못된 branch/merge 충돌을 만든다. 각 규칙의 OR은 명시적 대안 clause로 보존하고 공동 가능성을 계산해야 한다. `a→c` 직접 edge 부재는 `a→b→c`로 같은 track이 되는 가능성의 부재가 아니다.
- 첫 의미 구현은 contiguous triple/실제 지속 계류처럼 직접 연결 조건을 정확히 표현할 수 있는 primitive부터 시작하되 미지원 다단계/OR을 삭제하거나 음악적으로 기각하지 않는다. 조건/시간 전제/가정/미설명 음가를 결과에 남긴다.
- 두 진행이 서로 다른 query에서 각각 존재 증명을 얻었다고 **같은 성부 가정의 비교**가 되지는 않는다. 그 주장은 두 해석의 조건을 함께 만족하는 하나의 completion에서만 가능하다. 공동 조건이 불가능하면 `incompatible_joint_constraints` 또는 `distinct_voice_hypotheses`로 분리하며 witness들을 union하지 않는다.

후속 prototype의 최소 interface는 아래 네 연산으로 나눈다. 현재 API로 구현됐다는 뜻은 아니다.

```text
compile_rules(observation_view, harmony_path, metric_facts, graph_refs)
  -> rule family, note/sound IDs, exact spans, fact/assumption prerequisites,
     required-link alternative clauses, forbidden links, blockers
solve_joint(compiled_rules, budget)
  -> geometry status, query/completion refs, unknown/unsupported/conflict
compare_under_completion(path_a, path_b, one_completion)
  -> 같은 target/cells의 raw membership, conditional coverage, unexplained time
slots_under_hypothesis(observation_view, harmony_path, one_completion)
  -> 원 onset/duration/octave/tie/attack, 상대 degree, role alternatives/blockers
```

literal projection, 화성 가정의 root/member/blocker, all-part cell membership, 중복 없는 note-time 및 기존 local passing/neighbor/held/reattack 규칙 정의는 재사용할 수 있다. 그러나 전역 assignment를 돌며 old refs를 만드는 `shared_context.catalog/build` 흐름 자체는 새 factor evaluator가 아니다. 박절은 working IR의 qualified measure와 basis를 보존하고 denominator beat를 tactus/연주 강세로 치환하지 않는다. observed lowest와 structural bass, 구성음 membership과 consonance, root와 key/function은 서로 다른 전제다. 미지원·미관측은 false가 아니라 unknown/withheld다. 원 meter/silence blocker를 새 NCT/geometry가 면제하지 않는다.

다음 큰 기능의 첫 범위는 passing/neighbor의 두 direct edges, 실제 held/prepared suspension·anticipation 및 broken-chord/held-bass 상대 슬롯 대안의 공동 대조다. 명시적 local-key 가정이 없는 기능/cadence 판단은 unassessed로 남겨 다른 부분을 막지 않는다. 규칙별 가능한 연결이 공동으로는 branch/merge 충돌하는 반례, no-link, 다른 member 해석, 준비/바깥 문맥 부족, 동일 membership의 음가 partition 불변을 함께 검사한다. 같은 event-time의 여러 후보 설명량을 중복 합산하지 않는다.
