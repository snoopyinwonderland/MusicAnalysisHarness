# 원음표·쉼표 전체 순서와 physical measure 정체성 감사

기록 ID: **HARM-DEV-20260930-28** · 날짜: 2026-09-30

## 1. 이번 단계의 결과와 적용 상태

기존 고정 집합 **19개 작품 가족 / 33개 악보·악장**의 음표 44,607개와 쉼표 4,775개, 총 **49,382개 사건**을 원 MusicXML과 전수 대조했다. 정확 유리수 시간·기보음 철자·음가·타이·장식음·part/staff/명시적 voice·원 XML의 `<chord/>` marker·전체 lane 순서를 재현했다. 누락·거부·미검사 사건은 0개다.

동시에 세 악장의 부모 IR에서 **중복 measure ID 5묶음, 관련 사건 49개, 표시 번호 차이 5개, 마디 안 onset 차이 15개**를 확인했다. 원 XML의 `X1/X2/X3` 추가 마디가 정수 표시 번호로 바뀐 뒤 이전 마디와 같은 ID를 갖는 문제다. 전역 onset과 실제 마디 길이는 원자료와 일치한다.

이번 산출물은 **진단 sidecar**다. 새 Canonical Core revision을 만들거나 기존 문서를 교정한 것은 아니다. 이전 locator 수정 후보 26개 / 보류 7개, 41개 사례 / 125개 문맥과 annotation binding은 그대로 유지한다. 같은 사건이 반복되어 순서만으로 대응되는 30개는 독립 occurrence 인증으로 승격하지 않는다.

전체 Python **2,221개 테스트 / 49.634초 통과**는 코드 회귀 검사 결과다. 33개 음악의 화성 정답률이나 교재 전체 적용 완료를 뜻하지 않는다. 현재 운영 5173 및 기존 8822 악보 화면에는 이번 진단을 적용하지 않았다.

## 2. 목적과 선행 작업

사용자의 계속 진행 요청에 따라 [직전 불변 source locator 후보](2026-09-30-source-locator-revision.md)의 다음 과제를 진행했다. 특정 악보의 화성 해석을 선택하거나 사용자 의견을 정답으로 하드코딩하지 않았다.

직전 단계는 관찰 geometry가 유일한 경우에만 source locator를 교정했다. 다음 문제가 남았다.

1. 같은 pitch/onset/duration/tie/grace의 반복 장식음은 geometry만으로 개별 occurrence를 구별할 수 없다.
2. printed number로 만든 measure ID가 중복되면 원음표가 어느 물리적 마디에 속하는지 bare ID만으로 결정할 수 없다.
3. 원 XML voice와 기존 logical lane의 관계는 실제 대위법 성부와 별개다. source 참조 검증을 먼저 끝내야 성부·NCT·분산화음의 근거를 안전하게 연결할 수 있다.

따라서 음표뿐 아니라 **쉼표와 chord marker까지 포함한 전체 source sequence**를 재파싱하고, 해석을 바꾸지 않는 물리적 마디 진단을 추가했다. 화성 엔진, 기존 gate, production parser와 Core schema는 변경하지 않았다.

## 3. 입력 선정·정책·불변성

- 선정: [breadth r2 고정 계획](../../../output/harmony-breadth-trial-2026-09-30-r2/frozen-plan.json)의 33개 package 전체. 이전 부분 표본이나 첫 후보만 선별하지 않았다.
- 부모: 각 package의 full frozen IR 및 원 IR hash를 대조한다. source MusicXML·준비 자료·주석 파일은 기존 snapshot과 hash를 유지한다.
- 비교 기준: [locator revision r2](../../../output/source-locator-revision-trial-2026-09-30-r2/report.json)의 상태·미대응 ID·162개 artifact·정책·사례 목록. 새 결과 때문에 기존 후보/보류를 승격하지 않는다.
- split/권한: 기존 **train 27 / dev 6**, 33개 모두 `internal_research_use=true`. holdout, 미확인 권한 또는 관현악 보류 자료를 이 실험에 추가하지 않았다. 여기서 train은 기존 split 표기이지 이번에 학습을 실행했다는 뜻이 아니다.
- 화성 주석 파일의 바이트는 동결 대상이지만 **화성 라벨은 계산 입력에 사용하지 않는다**. raw measure label과 XML voice/notation은 관찰 자료다.
- 계약: 331개 입력 hash, 현재 `src/musicanote_harness/*.py` 254개 hash와 파일 목록, schema hash, parser 버전, 출력 hash를 저장한다. 입력/코드/출력의 변경은 성공으로 처리하지 않는다.

단순 `complete=true`는 실행 완료 표지다. 소비자는 반드시 `inputs_and_code_unchanged=true`, `artifacts_unchanged=true`와 CLI 종료 코드 0을 함께 확인해야 한다. 음악적 인증이나 migration 허가는 별도다.

## 4. 구현과 일반 규칙

### 4.1 전체 source lane 재현

[source_sequence_replay_audit.py](../../../src/musicanote_harness/source_sequence_replay_audit.py), 버전 `source-sequence-replay-audit-0.1.0`.

주요 함수: `raw_rows`, `match_ordered_lanes`, `audit`.

1. strict raw XML에서 part별 physical measure ordinal, note ordinal, divisions, backup/forward cursor와 정확 유리수 local/global onset을 재계산한다. XML을 정수 마디 번호나 기존 XPath에 맞춰 정렬하지 않는다.
2. 음표와 쉼표를 모두 보존한다. pitch spelling, grace/tie와 원 XML의 `<chord/>` 여부를 token에 포함한다. 이는 분석적 화음이 아니다. rest 뒤의 chord marker나 orphan chord는 보류한다.
3. source voice가 없으면 `None`으로 남긴다. 앞 음의 voice를 상속하거나 임의 1로 채우지 않는다. staff 생략은 XML의 기본 staff 1로 처리하되 빈 값·중복·비양수 값은 거부한다.
4. pinned music21 parser로 원자료를 다시 읽고 기존 legacy fingerprint 및 formal note/rest ID 생성식을 재현한다. 모든 fingerprint와 parent binding이 일치해야 한다. imported harmony는 메모리상 파싱 입력에서 제외하며 원 파일을 수정하지 않는다.
5. `part + physical measure + staff + source voice`의 **lane 전체 순서**가 exact token/global time과 일치할 때만 대응을 기록한다. fingerprint 정렬 collision queue나 과거의 잘못된 locator를 대응 기준으로 쓰지 않는다.
6. parser voice가 없을 때도 해당 physical measure/staff의 가능한 raw lane이 정확히 하나인 경우만 허용한다. 여러 lane이면 보류한다.
7. parent의 ID·전역 onset·음가·기보음·grace/tie·part/staff lineage를 검사한다. local onset 차이는 숨기거나 교정하지 않고 별도 진단한다.
8. 모든 parent 사건은 matched / rejected / unchecked 중 하나로 남는다. 모든 raw 사건도 대응 또는 unmatched 목록에 남긴다. 보류 시 미검사 사건을 분모에서 지우지 않는다.

반례·한계:

- 동일 token이 한 lane에 반복되면 재현된 순서가 있어도 각각의 occurrence를 독립적으로 인증한 것은 아니다. `reproducible_sequence_order_only`와 `independent_occurrence_certified=false`를 저장한다.
- 고유 token도 이번 실험은 pinned replay 진단이므로 독립 occurrence 인증 flag는 false다. 고유/반복의 증거 강도는 상태로 구별한다.
- malformed/중복 XML, 음가·pitch·tie 불일치, rest 누락, 원 source hash 변경, fingerprint/event ID 교환, 모호한 lane, 전역 시간 차이는 보류한다.
- 이번 계약은 기보 시간이다. repeat 재생 순서·performed timing·전곡 concert pitch 및 실제 대위법 성부를 인증하지 않는다.

### 4.2 물리적 마디 정체성

[source_physical_measure_audit.py](../../../src/musicanote_harness/source_physical_measure_audit.py), 버전 `source-physical-measure-audit-0.1.0`.

주요 함수: `audit(ir, source_measures, observations)`.

- `physical_measure_ordinal`은 source part 안에서 1부터 센다. `sequential_measure_index`는 부모 score grid에서 0부터 센다. printed label은 별도 문자열이다.
- raw partwise grid의 coverage·연속 시간·label·길이와 부모 ordered grid의 전역 onset/actual duration을 모두 대조한다. part 간 grid가 다르거나 순서/geometry가 맞지 않으면 보류한다.
- bare legacy measure ID는 중복될 수 있다. 진단 alias key는 **`{legacy_measure_id, sequential_measure_index}`**이며 target은 physical ordinal/sequence index다. 실제 새 measure ID나 migration mapping이 아니다.
- 모든 alias/event의 `retarget_executable=false`, 전체 `bare_measure_id_retarget_allowed=false`, `mapping_usable_for_migration=false`를 유지한다. 기존 annotation을 자동 재지정하지 않는다.
- note/rest membership은 검증된 source physical ordinal을 사용한다. 전역 half-open range만으로 grace를 다음 마디에 보내지 않는다. 전체 분석 span의 `[start,end)` 규칙 자체는 바꾸지 않는다.
- parser가 한 source part를 `P1-Staff2`처럼 분리한 경우의 display staff/source staff normalization을 진단할 수 있지만 Core staff를 변경하지 않는다. 실제 33개에서는 이 normalization 수가 0이며 지원은 합성 반례로 검사했다.
- 이 helper의 coverage는 공급된 parent observations다. 따라서 자체 `source_event_cardinality_verified=false`를 유지한다. 전체 raw XML cardinality는 replay runner와 독립 raw 재검사에서 별도로 확인한다.

### 4.3 고정 전체 실행

[source_sequence_replay_trial.py](../../../src/musicanote_harness/source_sequence_replay_trial.py), 버전 `source-sequence-replay-trial-0.1.0`.

주요 함수: `run(plan_path, previous_path, output)`.

- 전체 plan/previous package 집합·snapshot·policy·미대응 ID·기존 context 목록을 대조한다.
- package별 full replay/physical grid/qualified aliases/모든 note-rest observations/보류를 gzip에 저장한다. 원 XML과 full IR은 기존 SHA-identical snapshot을 참조한다. 원자료 또는 새 clipped IR을 만들지 않는다.
- 이전 locator 수정 후보는 그대로 유지하고, 이전 미매핑 34개를 새 observations와 대조한다. fresh mapper의 별도 43개 분모를 섞지 않는다.
- output이 이미 있으면 덮어쓰지 않는다. 코드 목록 및 모든 input/artifact hash를 종료 시 다시 확인한다. 변경된 실행은 CLI exit 2다.
- `source_labels_used`, `accuracy_measured`, `core_modified`, `production_modified`, `annotation_retargeted`, `gold_promoted`, `training_promoted`, `split_rights_changed`, `external_transmission`, `engine_recomputed`, `gate_changed`는 모두 false다.

## 5. 실제 실행 결과

정본: [r1 report](../../../output/source-sequence-replay-trial-2026-09-30-r1/report.json), [run contract](../../../output/source-sequence-replay-trial-2026-09-30-r1/run-contract.json).

환경: Python `.venv`, music21 **10.5.0**. 실제 실행 **167.690초 / exit 0**. 코드/입력/산출물 변경 0. 이 시간은 source audit 실행 시간이며 화성 엔진/UI benchmark가 아니다.

| 지표 | 결과 | 의미 |
|---|---:|---|
| 작품 가족 / 악보·악장 package | 19 / 33 | 이전 고정 집합의 전수 재검사 |
| note / rest | 44,607 / 4,775 | 총 49,382 사건 |
| full replay 완료 / physical mapping 완료 | 33 / 33 | 각각 계약 범위 내 완료; migration 인증 아님 |
| rejected / unchecked / unmatched raw | 0 / 0 / 0 | 사건을 분모에서 제외하지 않음 |
| 원 XML partwise physical measures | 8,698 | 여러 part의 같은 시간 마디를 각각 셈 |
| 공통 score grid physical measures | 3,432 | 악보별 공통 grid 합; 위 partwise 수와 구별 |
| raw lane / chord markers / grace events | 10,318 / 6,126 / 541 | independent raw 재파싱에서도 동일 |
| order-only occurrences | 30 | 개별 정체성 미인증 상태 유지 |
| 마디 오른쪽 끝 grace membership | 55 | 뒤 마디 시작과 같은 global time일 수 있음 |
| 이전 미매핑 재현 / 잔여 | 34 / 0 | 재현은 수정 후보 승격이 아님 |
| 입력 / 코드 / gzip artifact hash | 331 / 254 / 33 | 모두 불변 및 gzip CRC/JSON 검사 통과 |

### 5.1 이전 미매핑 34개와 fresh mapper 43개를 구별

이전 locator revision의 34개 = **order-only 30개 + 고유 token 4개**. 전체 sequence가 재현돼도 이전 보류 7개는 그대로다.

| package | 이전 미매핑 수 | 이번 order-only 수 |
|---|---:|---:|
| Beethoven quartet `n01op18-1_01` | 4 | 4 |
| Chopin `BI105-3op30-3` | 2 | 2 |
| Chopin `BI105-4op30-4` | 12 | 8 |
| Mozart `K281-3` | 16 | 16 |

Chopin op.30-4의 m27/m123 F♯6은 하나가 D6 grace와 같은 notated chord의 member이고 다른 하나는 독립 grace다. geometry만으로 같아 보였던 4개는 `<chord/>` marker로 구별된다. 이것이 화음 종류나 NCT 판정을 뜻하지는 않는다.

별도 current mapper의 43개 = 위 34개 + physical measure 문제의 고유 token 9개(Beethoven01-1의 1개,02-3의 8개). 이번에도 전부 재현되지만 **이전 trial 미매핑 분모는 34개**로 유지한다. 작은 분모로 바꿔 성공률을 높이지 않는다.

### 5.2 마디 ID 및 local onset 문제의 실제 위치

| package | 중복 ID 묶음 | 관련 note/rest | local onset 차이 | 표시 번호 차이 |
|---|---:|---:|---:|---:|
| Beethoven sonata `01-1` | 1 | 13 | 2 | 1 |
| Beethoven sonata `02-3` | 3 | 29 | 11 | 3 |
| Mozart sonata `K280-3` | 1 | 7 | 2 | 1 |
| 합계 | 5 | 49 | 15 | 5 |

| package | 원 XML label | physical ordinal / seq index | 부모 label | global start / duration |
|---|---|---|---|---|
| Beethoven01-1 | X1 | 50 / 49 | 48 | 192 / 1 |
| Beethoven02-3 | X1 | 10 / 9 | 8 | 24 / 1 |
| Beethoven02-3 | X2 | 47 / 46 | 44 | 132 / 1 |
| Beethoven02-3 | X3 | 56 / 55 | 52 | 156 / 1 |
| MozartK280-3 | X1 | 79 / 78 | 77 | 231/2 / 1/2 |

원인은 raw XML의 printed number 중복이 아니다. source의 추가 label이 importer/legacy의 정수 마디 번호로 합쳐진 뒤, [FormalIRAdapter](../../../src/musicanote_harness/formal_ir.py)의 `display_measure_map`이 그 번호를 key로 삼아 ID를 덮어쓰고 `_grid_for_event`가 같은 번호의 첫 마디를 반환한다. 따라서 ordered measure rows의 전체 시간은 맞아도 ID와 event local onset이 잘못될 수 있다. 이번에 이 기존 코드는 변경하지 않았다.

예: Beethoven01-1의 `note_7443c5fac110` / `rest_14d85f525764`는 global192·duration1이 맞지만, X1의 local onset은 부모 IR의3이 아니라 raw의0이다. MozartK280-3의2건은 양쪽 staff의 rest이며 local1이 아니라0이다. 음표만 검사하면 이 쉼표 문제를 놓친다.

Beethoven02-3의 `note_3919663de5fe` / `note_441442f684d3`는 physical56(X3)의 F♯4/G4 grace다. global157은 다음 physical57의 시작과 같지만, source에서는 X3의 오른쪽 끝 local1에 속한다. 부모 local3과의 차이를 진단하며 다음 마디로 자동 이동하지 않는다. 이2건도 local 차이15건에 포함된다.

## 6. 검증·반례·경고

이번 신규 **85테스트**: replay31 / physical measure37 / runner17. 전체2,221테스트 /49.634초 /OK.

- [replay tests](../../../tests/test_source_sequence_replay_audit.py): note/rest 순서, chord marker, rest→chord의 잘못된 표기, grace/tie, 타입·source hash·event ID, voice 누락/복수 후보, prefix 불일치·raw 초과, source/parent 불변, 보류 사건 분모.
- [physical tests](../../../tests/test_source_physical_measure_audit.py): grid 불일치·누락/중복, exact rational/ordinal 타입, source staff/voice, 중복 ID의 qualified aliases, right-edge grace, parent/replay pitch/tie/geometry 차이, 입력 불변, 부분 coverage.
- [runner tests](../../../tests/test_source_sequence_replay_trial.py): frozen plan/이전 실행/snapshot/policy 불일치, 권한 boolean, hash/파일 목록 변화, source/mapping inventory, 전체 event partition, 이전 cases/candidates 보존, output 덮어쓰기 거부.

두 독립 리뷰에서33 gzip의 CRC/SHA/JSON,331입력/254코드/파일 목록/contract SHA,33package의 rights/split/parent binding을 재검사했다. 별도 raw XML cursor로 다시 파싱하여49,382 rows,8,698 partwise 마디,10,318 lanes,6,126 chord markers,541 grace를 저장 observations와 전수 대조했고 불일치0이었다. 부모 fingerprint/ID 생성식, written pitch/tie/grace/global time,3,432grid, qualified aliases/event memberships, 전체 counts, 이전41cases/125contexts도 일치했다.

동일 token의 parser occurrence를 바꾸면 순서만으로 독립적인 참/거짓을 판별할 수 없다는 반례를 유지한다. 기존의 넓은 `source_identity_revision`을 이 이동의 대용품으로 사용하지 않았다. 호환 fingerprint/ID 재현과 독립 source occurrence 인증은 다르다.

실제 재파싱에는 기존 music21 경고가 나왔다: Beethoven02-2의 wedge/dashes, ChopinBI115-4op33-4의 pedal import. 이번 note/rest/token 재현을 방해하지 않았지만 모든 표정 기호·pedal의 fresh parse 보존을 인증한 것은 아니다. 원 XML/부모 IR은 보존돼 있다. 경고는 CLI 출력에서 확인했으며 이번 report의 구조화 필드에 저장하지는 않았다.

## 7. 재현 방법

작업 디렉터리: `K:\Music Analysis`. 기존r1을 보존하고 재실행에는 **아직 생성하지 않은 출력명**을 사용한다.

```powershell
$env:PYTHONPATH = 'src;tests'
.venv/Scripts/python.exe -B -m unittest discover -s tests -q
.venv/Scripts/python.exe -B -m musicanote_harness.source_sequence_replay_trial --plan output/harmony-breadth-trial-2026-09-30-r2/frozen-plan.json --previous output/source-locator-revision-trial-2026-09-30-r2 --output output/source-sequence-replay-trial-2026-09-30-r2
```

r1 contract SHA-256: `e46355a37a6f70a4db2f8940436879a09d748370a746df55bf2614c345edc3a9`. 코드를 변경해 재실행할 때는 기존 계약을 덮어쓰지 않고 새 revision으로 기록한다.

## 8. 다음 개발과 이동 위험

1. **physical measure 전용 불변 revision 계약**을 만든다. unique measure IDs/5printed labels/49event measure refs/15local onsets에 변경을 제한하고 score/note/rest/part/staff/voice/sounding/tie/attack/chord IDs, global time, pitch, duration, 배열 순서를 보호한다.
2. alias는 옛 ID 단독이 아니라 seq index를 포함하며 JSON-pointer diff와 새 document ID/parent binding을 저장한다. 옛 annotation/analysis는 옛 document에 남긴다. 모호한 옛 ID 참조의 자동 retarget은 금지한다. grace55건의 physical membership도 보호한다.

   마디 전용 교정만으로 `source_references.source_measure_number`와 XPath가 모두 교정되지는 않는다. 예를 들어 Beethoven01-1의 X1 note/rest는 부모 source ref에 번호48과 XPath null이 남아 있다. 이는 다음 locator 단계 또는 별도 허용 필드 계약에서 처리해야 하며, 물리적 마디 교정 완료를 source ref 전체 교정 인증으로 해석하지 않는다.

3. order-only30건은 별도 불확실성으로 유지하고 geometry exact와 섞어 ready로 만들지 않는다. 남은 source voice→logical lane은 별도 관찰·analysis interface로 다루며 source voice를 Core의 실제 대위법 성부로 바꾸지 않는다.
4. source 기반 계약이 갖춰지면 미설명음/NCT·공동 성부·경쟁 quality/생략 가설과 분산/지연 해결로 돌아간다. 이번 진단 통과를 NCT나 secondary의 음악적 정답 증가로 세지 않는다.
5. 관현악은 계속 전음표 written/concert·score-order transpose timeline·판본/박자/part 대응·권한 준비가 필요하다. 이번33악장에 대편성을 추가한 것은 아니다.

이 단계에서 사용자의 음악 해석 선택은 필수가 아니다. 일반 source 계약과 반례를 프로그램으로 먼저 검사할 수 있다. 음악적 경쟁 후보를 표시하고 선택할 단계에서는 전후 모든 part 문맥과 원문 설명을 보존한 뒤 다시 의견을 요청한다.

개발 메인: [README](../README.md) · 이력: [DEVELOPMENT_LOG](../DEVELOPMENT_LOG.md) · 규칙: [HARMONY_REASONING_RULES](../HARMONY_REASONING_RULES.md). Git commit/push, 외부 API, 권한 변경, 원자료 공개는 이번 범위에 포함하지 않는다.
