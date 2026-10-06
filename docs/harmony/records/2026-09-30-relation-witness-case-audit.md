# 실제 해결 관계·경쟁 후보·원악보 문맥 감사

기록 ID: **HARM-DEV-20260930-26**. 새 화성 분석 개발 문서이며 인수인계 문서가 아니다.

## 1. 목적과 적용 범위

여러 작품으로 확대하라는 요청에 따라 이전 19개 작품 가족/33개 악보·악장/322개 관측 창의 실제 해결 관계를 점검했다. 이번 단계는 새 작품을 추가하거나 화성 엔진의 정답을 선택하는 작업이 아니라, 이미 생성된 조건부 음표 연결이 무엇을 보장하고 무엇을 보장하지 않는지 **독립적인 감사 코드**로 확인하는 작업이다.

특정 작품·마디의 화음을 조건식으로 넣지 않았다. 원주석 라벨과 사용자 교정을 입력으로 쓰지 않았다. 322개 전체 결과를 inventory에 남기고, 직접/시간 경로 지지가 있는 구간에서는 **정확히 같은 source/cut/target 범위를 갖는 모든 경쟁 후보**를 보존했다. 경쟁 후보를 정답 음성 사례로 간주하지 않는다.

결정: 감사 prototype으로 유지. 기존 직접/시간 gate, Core/parser/schema, 운영 5173, 구조 분석, 현재 열린 8822 화면, 정책/split/rights/gold/training/외부 API는 변경하지 않았다. Git commit/push도 하지 않았다.

## 2. 핵심 일반 규칙

1. `witness_exists`는 필요한 음표 연결의 **한 가능한 부분 대응**이지 화음 전체·실제 대위 성부·기능·조성·종지의 확정이 아니다.
2. 직접 해결의 source terminal identity와 target onset identity는 제한된 필수 구성음의 관측이다. 모든 구성음이 동시에 있는지와 구간 안에 한 번이라도 있는지는 별도 진단이다.
3. 관측된 비구성음은 자동 NCT로 면제하지 않는다. 직접 witness가 있어도 미설명 음, 미관측 구성음, doubled tendency의 미선택 연결이 남을 수 있다.
4. 시간 경로는 같은 명시적 part/voice 안의 정확히 닿는 지속/동음 재타격과 실제 해결 움직임을 요구한다. 쉼표·다른 성부의 새 동일음·옥타브 바뀐 동일 pitch class를 대신 끌어오지 않는다.
5. 한 query 안의 공동 가능성과 여러 경계가 공유하는 전곡 assignment는 다르다. 후자는 `not_measured`다.
6. 원상태, null query, 예산 보류, zero-duration 미지원, 대안 origin/index를 보존한다. source trace가 틀리면 조용히 고치거나 해당 사례를 쉬운 사례로 교체하지 않는다.
7. 철자는 exact rational alter+octave+MIDI 관계로 확인한다. microtone을 `int(alter)`로 절삭해서 일반 음에 합치지 않는다. 지원되지 않는 철자는 별도 보류다.
8. 원본 참조·기보음·음가 검증과 XML 전체 onset/반복/실음 검증을 구분한다. 부분 source 검사를 전곡 인증으로 부르지 않는다.

기존 교재의 이끎음 상행·7음 하행·화음 구성음·비화성음·성부 진행 개념을 실제 event 관계에 대조했다. 교재의 모든 예외나 NCT 규칙이 완성됐다고 주장하지 않는다. 특히 vii 계열의 감5음 진행, doubled tendency 전부의 해결, local key/function, 화성 리듬과 경계 선택은 남아 있다.

## 3. 구현과 결과 계약

새 모듈:

- `src/musicanote_harness/harmony_relation_case_audit.py`, `relation-case-audit-0.1.2`: 후보 origin/alternative/index, family shape, parent/local span, 전체 부모 IR의 event 집합·pitch/span/source note ID, 정확 철자, 명시적 lane, touching time, 필수 움직임, 비분기/비병합, 시간 carry/arrival/coverage를 검사한다.
- `src/musicanote_harness/harmony_relation_case_trial.py`, `relation-case-trial-0.1.2`: 동결 입력·권한 정책·코드 목록/hash, 모든 survey/query inventory, 원본과 cache 전체 relation JSON 동등성, 사례 저장, source trace, 실행 후 불변성을 관리한다.

새 검사 파일:

- `tests/test_harmony_relation_case_audit.py`: 40개. 직접/지연 양성, metadata 손상, 임의 추가 링크, 음높이/옥타브/방향/성부/시간 오류, carry 경로, 미관측음, 비구성음, doubled tone, microtone/zero-duration, 예산 보류, 모든 경쟁 origin, 입력 보존, 승격 금지, local 밖 근거 분리, 구성음 순서와 target triad subset 호환성.
- `tests/test_harmony_relation_case_trial.py`: 23개. source XPath/note ordinal, namespace, inherited divisions, 정확 음가, grace, enharmonic, 빈 값/중복/미지원, all-part context/tie/rest, 실제 동결 disk 입력, byte hash/JSON 동등성, sample 중복/누락, 정책 보호, 출력 덮어쓰기 금지, endpoint 집계 때 direct/temporal 목록 별도 보존.

결과는 `conditional_witness_rechecked`, `not_supported_in_saved_query`, `unsupported`로 구분한다. 손상된 저장 witness는 `failed_recheck`로 남긴다. 원 engine status는 별도 보존한다. `selected=null`, function/NCT/accuracy/gold/training=false, human review=`not_reviewed`, global assignment=`not_measured`다.

원 engine의 `required_link_options`와 temporal profiles는 검사 대상이지 임의로 정답을 만들어 주는 입력이 아니다. 저장된 실제 링크가 정확한 음표·움직임·시간·성부 조건을 만족하는지 재계산한다. 이 감사는 음성 query의 전체 탐색을 재실행하여 부정의 완전성을 증명하는 작업은 아니다.

## 4. 실행과 원자료 보존

정본 출력: `output/harmony-relation-case-audit-2026-09-30-r4/`.

```powershell
$env:PYTHONPATH = 'src'
& '.venv/Scripts/python.exe' -m musicanote_harness.harmony_relation_case_trial --reference 'output/harmony-breadth-trial-2026-09-30-r2' --cached 'output/harmony-geometry-cache-trial-2026-09-30-r2' --output 'output/harmony-relation-case-audit-2026-09-30-r4'
```

이미 존재하는 출력은 덮어쓰지 않는다. 재현 실행에서는 새 output 이름을 지정한다.

- `run-contract.json`: 817개 입력/248개 source Python 파일 hash와 코드 목록, 선정 기준, 권한·실험 범위.
- `report.json`: 전체 322개 survey/15,195개 query inventory와 원상태, 41개 사례 artifact 참조/hash, 중복 제거 집계, source 불일치, 보류와 한계.
- `samples/*.json.gz`: 실제 41개 지원 sample, 모든 동일 범위 경쟁 후보, 재검사, 주변 문맥, source trace, 원 cache artifact/hash.
- `sources/*/source.musicxml`: 지원이 있는 21개 package의 **변경하지 않은 전체 원본 MusicXML**.
- `sources/*/canonical_music_ir.json`: 해당 **변경하지 않은 전체 동결 IR**.
- `sources/*/provenance.json`: manifest entry/split/rights/pitch policy, source/IR 경로와 SHA.

각 group context는 앞뒤 한 마디를 더하고 모든 part의 note/rest/sounding event를 남긴다. 실제 sound span을 잘라 새 음처럼 만들지 않으며 tie chain의 원 note ID가 문맥 밖에 있더라도 보존한다. 따라서 context는 `observational_context_not_standalone_canonical_ir`이고, 재현의 정본은 전체 source XML/full IR snapshot이다. 불완전한 잘라낸 IR을 정식 schema라고 주장하지 않는다.

원XML의 indexed XPath, part, printed measure, source voice/staff, **note ordinal**(XML 전체 child index와 다름), raw written pitch, inherited divisions에 따른 duration, grace flag를 대조했다. XML onset/backup/forward/반복 전체를 새로 해석한 것은 아니며 concert certification도 없다. 원주석 파일은 hash만 확인하고 라벨을 분석에 입력하지 않았다. 로컬 내부 연구 자료이며 공개/학습/외부 전송 승인이 아니다.

## 5. 실제 결과 — 통과 수와 음악적 정답 수는 다름

| 항목 | 결과와 단위 |
|---|---|
| 전체 inventory | 19 work families / 33 packages / 322 창 / 15,195 관계 query |
| 지지 사례 저장 | 15 work families / 21 packages / 41 sample records |
| 직접 해결 | 578 query 재검사, 실패 0 |
| 시간 경로 | 16 query 재검사, 모두 직접 578에 포함 |
| 실제 지연 도착 | 0, `not_seen`; 기능 불가능/실패라고 단정하지 않음 |
| 지지 범위 | 125 group instances / package+exact-span 중복 제거 118개 |
| 철자 기반 가설 | 범위+family+quality+source/target members 중복 제거 552개 |
| 같은 범위 경쟁 | 1,919 query origins, 정답 음성 사례 아님 |
| source note trace | 6,934 일치 / 6 불일치 instances; 고유 음표 1,816 일치 / 4 불일치 |
| 입력/출력 | 817 input / 248 code hash·목록 불변, 모든 source/IR snapshot SHA 불변 |
| 시간 | r4 35.814초; 기존 엔진을 재실행한 속도 benchmark 아님 |

지원 41개 sample에는 총 5,140 query가 있으나, 1,919개 대조는 실제 지지 group과 정확히 같은 범위의 후보만 센다. 전체 inventory의 15,195 query와 혼동하지 않는다. 578개는 독립적인 578곡/정답/종지/secondary 화음 수가 아니다.

직접 578개에서 겹치는 진단:

- Source 전체 구성음이 cut 직전에 미완비: **229**.
- Target 전체 구성음이 onset에 미완비: **474**.
- Source interval에 비구성음 존재: **400**.
- Target interval에 비구성음 존재: **224**.
- 두 boundary의 전체 구성음이 완비하고 양쪽 interval 비구성음도 없는 query: **14**. 이 역시 전체 음악적 정답이 아니다.
- 미선택 critical source event가 남는 query: **74**. 미해결 확정이 아니라 doubled tendency 전부의 대응을 아직 계산하지 않았다는 진단이다.

독립 집계에서 direct578은 V267/V7 114/vii185/vii_half7 12/vii7 0이다. collection별 direct/temporal은 현악4중주80/1, 베토벤 소나타129/2, 쇼팽 마주르카137/5, 코렐리216/8, 모차르트 소나타16/0이다. 전체 필수 endpoint 관계는 중복 제거 51개(LT38+7th13)이므로 query 수를 고유 음표 연결 수로 세지 않는다.

시간16개 모두 critical arrival이 cut에서 즉시 발생했고 target 구성음도 onset에 이미 관측됐다. Corelli 일부 query는 source 근음이 cut 직전에는 없고 앞 구간에서 관측되는 분산형을 지지한다. **합성 지연 테스트 통과와 실제 지연 해결 양성 검증은 구별한다.**

전체 원상태:

| Direct | 개수 | Temporal | 개수 |
|---|---:|---|---:|
| identity prerequisite missing | 13,249 | identity abstention | 14,030 |
| witness exists | 578 | temporal possible | 16 |
| no compatible witness | 288 | no joint witness | 69 |
| blocked context | 916 | blocked context | 916 |
| nonpositive duration unsupported | 164 | nonpositive duration unsupported | 164 |

두 열은 같은 query 집합의 다른 검사이므로 합산하지 않는다. unsupported를 XML 손상 또는 음악적 음성으로 바꾸지 않았다.

## 6. 실제 사례와 경쟁 해석

대표 사례는 별도 정답 hardcoding 없이 전체 inventory에서 확인했다.

- Beethoven quartet `n03op18-3_02`, `cont_b5216c80972ada3b2969`: `[101,203/2) → [203/2,102)`의 F–A–C–E♭→B♭–D–F V7 관계 가설. A3→B♭3은 `note_3319515eb1d4 → note_ae565795bb62`; E♭5→D5는 `note_201c205fcc76 → note_94b45be24ac4`. 같은 범위의 target A♭ 추가 후보는 구성음 미관측으로 temporal 보류다. 한 연결이 어느 candidate quality를 최종 선택할지 결정해 주지 않는다.
- 같은 악장 `cont_f7f642b4a3f009eadb1a`: `[431/2,216) → [216,217)`의 A–C–E♭→B♭–D♭–F vii 가설. 도음 연결은 `note_0a038a77e408 → note_85eeae273bc5`, target tie continuation `note_6ea9f9d9ac5b`도 보존된다. 같은 범위 vii7 후보는 7음 하행 옵션이 없고 vii_half7 후보는 identity 부족이다. 경쟁 관계를 “음악적으로 잘못된 화음”으로 단정하지 않는다.
- Corelli `op01n01a`, `cont_b22c204849b8a67ffcf3`, cut38: source root G가 terminal에는 없지만 앞 구간에서 관측된다. 동시 수직 화음과 시간 누적 구성음의 차이를 보여 주되 critical arrival의 실제 지연 양성으로 세지 않는다.

각 사례의 정확 source XPath, note IDs, 원음가·기보, 양쪽 범위와 앞뒤 문맥은 해당 gzip/source snapshot에 저장돼 있다. 이번 단계에 새 악보 HTML을 생성하거나 기존 화면의 표시를 변경하지는 않았다.

## 7. 발견한 source locator 불일치와 조치

독립 source 대조에서 **4개 고유 음표**, 반복 문맥 집계로 6개 불일치를 발견했다. 같은 음높이·같은 onset의 grace/principal 쌍에서 source locator가 서로 바뀐 형태다.

| Package / raw 좌표 | 원본 사실과 동결 IR 참조 불일치 |
|---|---|
| Chopin `BI126-3op41-1`, m79 A4, note[4]/note[6] | raw grace0/principal1이 IR principal1/grace0 참조와 교환됨; `note_9f15da83a443`, `note_e7894af2c733` |
| Mozart `K280-1`, m47 D5, note[6]/note[8] | raw grace0/principal2가 IR principal2/grace0 참조와 교환됨; `note_1d9f2930fc98`, `note_f5aaa47b6556` |

pitch/part/voice/staff/ordinal 값은 일치하지만 duration/grace가 어긋난다. 원본 XML의 음악 이벤트 집합 자체는 IR과 대응하므로 XML이 손상됐다고 단정하지 않는다. 역사적 준비 보고서에 mapping version 없이 matched_count/complete만 있어, 동음·동시점 대응의 모호성이 유력하다. 현재 parser의 어느 버그인지까지는 확정하지 않았다.

해당 4개는 **앞뒤 한 마디 padding의 주변음**이다. 모든41지원 sample의 positive direct endpoint, temporal carry/target, positive interval member profile에는 포함되지 않는다. 따라서 이번578/16의 frozen-IR 내부 재검증을 무효화하지는 않지만, 주변 Canonical overlay/source trace를 완료로 표시해서는 안 된다.

조치:

- 3개 group context를 `source_note_review_required`로 표시.
- 고유 note ID/반복 instance 수/두 package/실제 witness 영향 여부를 report에 별도 저장.
- `source_note_fields_all_consistent=false`; `source_field_issue_witness_note_refs=[]`.
- 원본 XML·동결 IR을 수정하지 않았다. 새 IR revision/annotation remap은 별도 단계로 남겼다.

## 8. 감사 코드의 반례 보강과 실행 이력

독립 테스트에서 저장 positive의 family/path metadata를 바꾸거나 필수 role에 없는 임의 bass 링크를 추가해도 받아들이는 감사 구멍을 발견했다. 새 감사 코드에 origin metadata와 모든 선택 링크의 실제 role/motion 검사를 추가했다. 기존 화성 엔진 gate를 바꾼 것은 아니다.

추가 검토에서 parent 문맥 안이지만 local query 직전에 끝난 microtonal 음/누락 voice가 local 재검사를 불필요하게 막는 범위 문제를 발견했다. `[start,end)`와 zero-duration point를 구별하고 local 링크만 검사하도록 수정했다. 부모 전체의 IR event 동일성 검증은 계속 유지한다.

- r1: 578/16 검사 성공, source 불일치 발견. null query를 `not_computed`로 집계해 unsupported164를 별도 원상태로 보여 주지 못한 기록 한계가 있었다.
- r2: 원 top-level status와 모든15,195개 query inventory 보강, local 범위 보강, 고유 span/shape/source trace 및 영향을 별도 기록. r1을 삭제하거나 덮어쓰지 않았다. 실제 지지 결과578/16은 유지됐다.
- r3: 구성음 배열 순서만 바꾼 유효 후보가 거절되는 호환성 반례를 수정했다. 기존 엔진처럼 source exact-member set/target triad subset으로 검사하고 reordered triad/seventh-target 테스트2개를 추가했다. 동결 결과578/16 및모든source진단은r2와동일. r2의당시코드hash와새v0.1.2의hash는구별하며새정본을덮어쓰지않았다.
- r4: 독립 파일 감사에서 endpoint 집계의 list alias가 temporal16 양성의 direct.selected_links에 같은 링크를 중복 추가하는 저장 오류를 발견했다. engine 원query와지지집계는불변이나저장근거보존계약위반이므로r3를정본에서제외하고보존했다. 복사한목록으로만집계하는helper와회귀test를추가하고전체를다시저장했다. 직접/시간연결을서로합쳐하나의증명처럼표시하지않는다.
- r4 최종 파일 재대조: 저장된 직접 `selected_links` 578개와 시간 `selected_paths` 16개가 각각 원 cache query의 links/witness와 정확히 일치했다. 불일치0. 실행 후817입력/248코드hash와코드목록을다시검사해변경0을확인했다.
- 최종독립감사도41gzip/21sourceXML·IRsnapshot/provenance정책복사·817inputs/248codehash·목록을확인했다.2,497개감사행의interval/boundary구성음·비구성음과모든양성의철자/온음계·반음움직임/explicitpart·voice/touching·carry/비분기를독립산식으로대조해오류0. source불일치4음표는양성endpoint/전체profile에포함되지않음도다시확인했다. 이것은감사구현의정합성이지음악적정답인증이아니다.
- 새로운 코드 검사63개(40+23), 전체Python **2,049개/41.681초통과**. 기존 engraving layout warning1건은유지됐다. 테스트 수는 악곡 수나 정답률이 아니다.

## 9. 다음 우선순위

1. Source locator의 grace/principal 동음·동시점 구별 계약부터 수정/검증한다. 기보 type·duration·grace·tie·XML ordinal을 함께 대조하고, 매핑 version/provenance를 남긴다. 오래된 IR을 덮어쓰지 않으며 annotation ID 재연결 위험을 점검한다.
2. 이번 조건부 witness에 전체 구성음/미설명음/여러 성부의 공동성/경쟁 quality/생략 가설을 결합한다. 부족한 NCT를 모두 삭제하거나 넓은 pitch union으로 면제하지 않는다. 실제 지연 도착은 별도 양성/근접 반례로 검증한다.
3. 전체 악보에서 지지 연결·미설명 음·경쟁 해석을 나란히 표시하는 검토 화면을 연결한다. source 불일치 문맥에는 경고를 표시하며 실험/원주석/사용자 의견을 구별한다.
4. 관현악은 전음표 written/concert timeline·판본/time-grid/parts·정책을 확인한 뒤 같은 감사로 포함한다. 제한된30pitch probe를 총보 화성 검증으로 간주하지 않는다.

지금 단계에는 사용자의 정답 선택이 필수로 필요하지 않다. 먼저 기술적 trace 결함을 정리하고 실제 경쟁 해석을 악보에서 보여 줄 때 음악적 판단을 요청한다.
