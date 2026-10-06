# 완전한 화음 진행의 원음표 정렬 비교 — 2026-10-02

## 1. 목적과 이번 범위

직전 [원음표 근거 후보 패널](2026-10-02-source-evidence-role-panel.md)의 두 등록 구간에 저장된 200개 조건부 계정을 비교한다. 저장 당시 최대 세 selector씩 나눈 batch는 저장 단위일 뿐 음악적 비교 범위가 아니다. 같은 문맥·전체 IR·scope·lattice·key 가정·전체 성부 completion에 속한 모든 batch를 모아, 완전 진행끼리 원음표와 동일 시간축에서 대조한다.

이번 구현은 **저장 근거 비교 adapter**다. Native session을 재발급하지 않고, 화음 공급기·역할 전제 판정기를 재실행하지 않는다. 원 profile 및 음가 합집합의 산술은 source facts에서 다시 검증한다. 저장 seal만으로 live authority를 주장하지 않으며, 실행기는 이전 생성 당시 파일 SHA와 정확 목록·참조·입력 순서를 먼저 검사한다.

이 작업은 최종 화성 선택, 실제 조성/NCT/cadence 확정, 정확도 측정, AI 학습, 운영 악보 화면이나 구조·작곡·편곡 연결이 아니다. 이런 승격은 모두 보류한다. 특정 작품·마디·사용자 정답을 알고리즘 조건에 넣지 않는다.

## 2. 비교 종류

모든 제출 key 가정을 유지하되 서로 다른 key 또는 서로 다른 completion의 설명을 합치지 않는다. 같은 key와 bundle의 pair는 다음 네 종류로 구분한다.

| 종류 | 고정되는 전제 | 달라지는 것 | 해석 제한 |
|---|---|---|---|
| `candidate_only` | 같은 구간 분할·명시 기능 vector | 화음 origin | 엄격한 경쟁 후보 대비 |
| `transition_only` | 같은 분할·ordered root/member 형태 | 명시 기능 vector | 새 기능 가정의 효과, 기능 확정 아님 |
| `candidate_and_transition` | 같은 구간 분할 | 후보와 기능 가정 모두 | 한 요소의 효과로 설명 금지 |
| `partition` | 같은 전체 source/key/completion | 분할·후보·기능 기회 수 등이 달라질 수 있음 | 경계만 변경한 효과로 설명 금지 |

공통 cut에서의 기능 가정, 왼쪽/오른쪽에만 있는 cut을 따로 기록한다. Full-hold의 빈 vector와 여러 slot의 None vector를 동일 길이 vector처럼 취급하지 않는다. 서로 다른 slot 수의 명시 V7/M도 동일 해결 의무 수라고 주장하지 않는다.

같은 ordered root와 members·같은 partition/vector의 alias는 **shape control**로 표시한다. 원 blockers·source premises·credit까지 같다는 보증이나 항상 zero gain이라는 주장은 아니다. 단지 enharmonic MIDI가 같거나 member-set만 같다고 기능/전위까지 같은 alias로 합치지 않는다. 원 member 순서는 기존 ordinary tertian shape의 admission에 영향을 줄 수 있다. 이번 실제 panel은 다른 signature의 경쟁 후보를 제안했으므로 실제 alias 양성은 0일 수 있다. Pure synthetic alias 검사는 실제 음악 coverage와 구별한다.

## 3. 음악적 비교 축

### 3.1 원음표별 여섯 범주와 이동

양쪽 partition 경계, 원 sounding event의 관찰 범위, 실제 credit union 끝점을 합쳐 공통 refinement를 만든다. 각 atom은 같은 `sound_ref`의 같은 `[start,end)`이며 유리수로 계산한다.

- source-guarded member
- conditional explained nonmember
- unexplained nonmember under this completion
- unassessed nonmember
- membership unknown
- source/hypothesis unsupported

범주별 오른쪽−왼쪽 delta와 6×6 transfer를 계산하고, **category가 달라진 atom**을 `changed_source_segments`에 저장하여 원음높이·source note IDs·full sound span·후보와 실제 credit clause refs를 붙인다. 같은 category 안에서 origin·slot·credit clause만 달라지는 경우까지 이 배열이 모두 열거하는 것은 아니다. 그런 변화는 각 facet의 전체 `source_segments`와 `bass_cells`를 함께 확인한다. Raw note-time은 양쪽 모두 같은 값이어야 하고 모든 transfer의 합 및 delta 합0을 검증한다. 구성음으로 흡수한 음과 조건부 NCT로 설명한 음은 같은 음악적 결론이 아니다.

### 3.2 동시 구성음과 순차 구성음

각 slot의 required member 수, 철자별 첫 source-guarded 관찰 시점·원음표 refs·관찰 음가를 기록한다. Sound의 실제 시작이 slot보다 앞인지, 별도 attack인지, tie chain인지도 보존한다. 첫 관찰 시점은 performed onset이나 새 attack 추정이 아니다.

동시 clock cell의 missing spelling과 전체 slot의 pooled missing spelling을 구별한다. 기존 raw cell의 guard 필드를 그대로 유지하면서 attack/pitch/clock 및 grace/point guard를 모두 만족하는 별도 strict 관찰도 계산한다. Pooled core가 갖춰졌다고 분산화음·실제 화성이 확정된 것은 아니다.

큰 member-set이 원음을 더 많이 포함하는 편향을 드러내지만 임의의 복잡도 penalty를 부여해 승자를 고르지는 않는다. 실제 지원되지 않는 추가 구성음은 누락 정보로 남긴다.

### 3.3 베이스·전위·경계

양쪽 clock cell을 정렬해 같은 실제 최저음 refs, 조건부 member index·전위·shape admission·guard·missing spelling을 비교한다. 같은 낮은 높이의 모든 source sounds를 유지한다. 이 축의 시간은 clock duration이며 여러 음을 합한 note-time과 섞지 않는다. 최저음은 structural bass나 pedal의 확정값이 아니다.

인접 slot의 ordered root/member signature가 같으면 `cut_signature_observations`에 표시한다. 추가 grid cut이나 같은 화음 후보의 반복 자체를 실제 화음 교체의 증거로 해석하지 않는다. 반대로 같은 signature라는 사실만으로 경계를 자동 삭제하지 않는다.

### 3.4 실제 진행과 조건부 NCT

원 native transition의 function shape·first actual change strategy·key/core/bass prerequisite axes·profile literal evidence를 그대로 참조·보존한다. 원 role의 ordinary template OR/AND 및 None/False를 유지한다. 개별 leading-tone row가 supported여도 전체 template이 False이면 ordinary credit가 없는 상태를 바꾸지 않는다.

기존 local/boundary/ordinary credit는 같은 completion의 sound별 rational union이다. 새 pair는 attribution만 비교하며 원 credit를 늘리거나 다른 completion의 유리한 부분을 합치지 않는다. Reattack carry를 tie 또는 확정 suspension으로 재명명하지 않는다. 저장된 역할 전제 자체를 이번에 독립 음악적 정답으로 재판정한 것은 아니다.

## 4. 구현과 자원 계약

- Core: [native_progression_contrast.py](../../../src/musicanote_harness/native_progression_contrast.py), version `native-progression-contrast-0.1.0`.
- 실행기: [native_progression_contrast_trial.py](../../../src/musicanote_harness/native_progression_contrast_trial.py).
- Core 검사: [test_native_progression_contrast.py](../../../tests/test_native_progression_contrast.py).
- 저장 검사: [test_native_progression_contrast_trial.py](../../../tests/test_native_progression_contrast_trial.py).

Core는 `compare(scope, lattice, entries, bundles=..., max_pairs=..., work_budget=...)`이다. Entry는 원 native path·role path·comparison ref·explanation ref를 갖는다. 원 scope/lattice/key/origin/bundle과 tuple·partition·account pointer를 대조한다. 원 profile을 pure source arithmetic으로 재검증하고 native raw account 및 role union account를 exact 비교한다. 입력을 수정하지 않는다.

모든 제출 pair를 사전에 계획한다. Cover 함수의 반복 선형 스캔을 포함하는 이차적 refinement work, credit clip 스캔, source note closure 복사, raw profile/계정 검사를 포함한다. Pair/work cap 초과는 전체 요청 hold이며 앞부분만 성공으로 저장하지 않는다. 계획 pair 수와 미실행 수는 유지한다. Identity hash/JSON admission은 별도 reader byte cap의 대상이며 CPU/RSS 상한 보장이라고 표현하지 않는다.

Reader는 압축 파일 크기·해제 후 개별/전체 byte·entry 수를 제한한다. 입력 cap 초과는 새 출력 생성 전에 fail closed한다. Output은 workspace output 아래 새 direct directory에만 생성하고 기존 parent나 결과를 덮어쓰지 않는다. 최종 checksum과 정확 inventory로 입력·코드·산출물 불변을 확인한다.

## 5. 개발 중 발견과 교정

1. 초기 core AST 검사에서 PREFIX와 AUTHORITY 선언을 붙여 쓴 작성 오류를 발견해 분리했다. 실제 계산 전에 교정했다.
2. 초기 신규22검사에서20PASS/2FAIL이었다. 두 resealed-tamper fixture가 다른 모듈의 기본 prefix로 봉인되어 목적한 검증보다 먼저 seal 검사에 걸렸다. 정확한 native/role prefix로 fixture만 교정했다. 원 parser/Core/자료는 바꾸지 않았다.
3. 독립 검토에서 role account만 재계산하면 원 raw-state 요약 일부를 복사하므로 위조된 raw-state를 놓칠 수 있음을 확인했다. `native._account` pure 산술과 parent whole account의 exact 대조 및 반례를 추가했다.
4. 독립 검토에서 pair의 cover 내부 반복을 선형 budget으로 계산한 문제를 발견했다. 실제 row/cell/union clip 길이로 endpoint×cover visits 및 반복 source-reference 복사 비용을 계획하도록 보강했다. 재검토에서 clips가 비어 있는 failed/unassessed clause도 각 atom의 attribution scan에서 방문한다는 누락을 발견하여 atom×전체 clause 수를 추가하고 별도 planner-only 반례를 넣었다. CPU/RSS 상한으로 주장하지 않는다.
5. 첫 실제 metadata-only loader는 greedy link 순서 때문에 관계 검사를 거부했다. Saved index는 원 greedy 순서, bundle은 canonical sorted 순서를 보존한다. 중복 없는 같은 edge-set과 canonical order 동등성을 검사하도록 새 runner만 교정했다. Cold native/role producer나 실제 contrast 실행·출력 생성은 없었다.

중간 검사23/15.434초,24/16.448초,27/15.961초 및 strict guard 보완 후27/17.917초 PASS는 최종 실행 수에 합산하지 않는다. 초기 storage15/33.937초와 중간17/36.475초·18/38.374초 PASS 및 metadata-only 실패도 최종 저장 검사/실제 대비 결과와 구별한다.

## 6. 비교에 사용할 원음표 사례

다음은 직전 저장자료의 독립 읽기로 고른 예시다. 새로운 정답 annotation 또는 최종 화성 해석이 아니다. 마디·작품명·ID는 위치 식별 정보일 뿐 알고리즘 조건이 아니다. 전체 IR와 원 파일이 연결되어 앞뒤 음표·음가를 재현할 수 있다.

### 6.1 현악사중주 m132의 C3–B♭2–A♭2

각각1/2quarter다. 같은 key·full-hold·actual completion에서 7-member A♭ 후보는 member53/2+credit0, B♭를 제외한6-member 후보는 member26+passing-like credit1/2다. 양쪽 모두 member+credit53/2이며 미설명0이다. B♭2가 구성음에서 조건부 경과음으로 이동하는 atom을 볼 수 있어야 한다. 설명량 또는 많은 구성음만으로 어느 후보도 자동 선택하지 않는다.

### 6.2 소나타 m13–15의 구성음/NCT 이동

동일3slot·None/None·key·actual bundle에서 A는 E♭–G–B♭–D♭–C → A♭ triad → B♭–D–F–A♭–C, B는 E♭7 → A♭–C–E♭–G♭ → B♭–D♭–F–A♭이다. A의 member241/6+credit1/6, B의39+4/3는 둘 다121/3이며 미설명13/6이다.

원 m13 D♭5–C5–D♭5와 m14 C5–B4–C5는1/6,1/6,1quarter다. m14끝 C5(1)→m15첫 C5(1)→B♭4(2)의 두 C5는 tie가 아니라 별도 attack이다. m15 베이스 D♭4(2)→D4(2)는 A/B가 서로 다른 절반을 nonmember로 남긴다. 더 많은 credit이 베이스 교체 문제를 해결한 것으로 표시하지 않는다.

### 6.3 빠진 구성음과 전체 해결 실패

위 B의 m14 A♭7 후보에 실제 G♭의 guarded pooled 지원이 없다. 명시 V7/M 경로에서 G4(4)→A♭4(4)의 개별 leading motion이 supported여도 seventh first-change 연결과 전체 ordinary template은 실패하여 **ordinary 해결 credit은0**이다. 별도 local/boundary 역할의 credit4/3까지0으로 바꾸는 것은 아니다. Missing core·target shape·전체 역할 의무를 각각 확인해야 한다. Full-hold 대 split의 차이도 경계만 바꾼 효과로 표시하지 않는다.

### 6.4 현악사중주 m133의 D♭ triad와 같은 후보 cut

F2–A♭3–D♭5–A♭6의1/2quarter 음군 뒤에 D♭4–F4–A♭4가1/2quarter로 반복된다. Full-hold와3slot의 member음가는 둘 다53/2·credit0이지만 후자는 D♭ triad의 조건부 root-position과 동시 core 지원을 보여 준다. `267.5` 전후의 두 slot은 같은 ordered D♭ triad다. 추가 cut을 실제 화음 변화라고 확정하지 않는다.

## 7. 최종 검사·실제 실행·보존 결과

### 7.1 동결 검사와 출처

최종 신규 핵심 **28개/16.233초**, storage-only **18개/42.561초**가 PASS다. 두 프로세스의 결과이며 중간 재검사나 기존 fixture의 회귀 항목을 다시 합산하지 않는다. 핵심 테스트는 genuine XML→Core/native/role synthetic fixture와 pure helper/planner control을 구별한다. Storage 테스트의 실제 contrast는 mock이며 실제 음악 실행으로 세지 않는다.

독립 재검토에서 native raw account exact match·cover² 및 source closure·atom×empty-credit-clause 비용의 수정이 모두 확인됐고 추가 차단 결함은 발견되지 않았다. 음악 계약 읽기 검토에서 category 변경만 열거하는 배열과 shape alias의 제한을 문서에 명시했다.

| 동결 파일 | SHA256 |
|---|---|
| `src/musicanote_harness/native_progression_contrast.py` | `becbde62bae4fa38df5b009da527a6212adf77d4e989c1e2199faa8f57e0eb7e` |
| `src/musicanote_harness/native_progression_contrast_trial.py` | `e00140b18931821633fb5b7a2bb1dd0e9c6445a70664562524cc2b0c41a8186d` |
| `tests/test_native_progression_contrast.py` | `877c6e0af94b52cc7bc811ab5a233c60b08721af7d91d4186f9971c627fb6429` |
| `tests/test_native_progression_contrast_trial.py` | `3db57a8ded4faf5f3dad9545e6b687554890749141ec83562b4bd77f65ed5333` |

Runner SHA를 전달한 중간 메시지에서 `b5`가 중복된 오타는 실제 파일 재확인으로 교정했다. 위 표가 정본이며 source를 수정한 것은 아니다.

### 7.2 결과 관찰 전 한도 결정

최종 metadata+pure planner만 읽은 사전 검사 **20.5475888초**는 compare/native prepare/역할 producer/새 output 생성0이다. 부모 정확148파일·고유4,752보호 경로, bounded reader151회/277,539,482 decoded bytes를 확인했다. 파일 read 수는 unique score 수가 아니다. 앞선21초 metadata 검사 및 link-order 교정 전 거부와 구별한다.

각 completion의 50entry·5등록 key 가정·225pair를 유지한 계획은 다음과 같다.

| 문맥·completion | Entry 검증/facet work | Pair refinement work | 전체 planned work |
|---|---:|---:|---:|
| Sonata01-1 no-link | 608,325 | 1,223,280 | 1,831,605 |
| Sonata01-1 actual greedy | 639,675 | 1,262,520 | 1,902,195 |
| Quartet no-link | 2,776,045 | 1,921,500 | 4,697,545 |
| Quartet actual greedy | 2,838,760 | 1,938,000 | 4,776,760 |

기본 work2,000,000은 변경하지 않았다. 이 기본값이면 Quartet 두 그룹은 전체 hold된다. 실제 결과를 보지 않고 사전 계획만으로 **네 그룹 동일 work5,000,000·max_pairs2,000**을 선택했다. 한도가 부족할 때 유리한 앞부분만 실행하거나 계산 도중 한도를 올리지 않는다. 이 숫자는 내부 계획 단위이지 seconds·peak RSS 또는 음악적 정확도 아니다.

### 7.3 실제 단일 saved-contrast 실행

[새 결과 폴더](../../../output/native-progression-source-contrasts-2026-10-02-r1/)의 단일 r1은 exit0/**55.895776199991815초**에 완료했다. `saved_progression_contrast_probe_complete_not_selected`, integrity=True, 실패0·전체 hold0이다. 네 그룹 모두 계산됐고 200facet의 원음가가 보존됐다. Fresh native prepare/role predicate 재실행은0이다.

실행 환경은 workspace의 `.venv/Scripts/python.exe -B`, `src` import path이며 `native_progression_contrast_trial.run("output/source-evidence-role-2026-10-02-r1", "output/native-progression-source-contrasts-2026-10-02-r1", work_budget=5000000)`을 한 번 호출했다. 재검증 실행은 다른 새 direct output 이름을 써야 한다. 기존 r1 이름으로 재실행하면 append-only 검사가 거부한다. 이 단계의 사전 metadata 검사와 저장 감사는 이 실행을 다시 호출하지 않았다.

| 실제 비교 종류 | Pair 수 |
|---|---:|
| 같은 partition/vector의 candidate-only | 100 |
| 같은 partition/ordered shape의 transition-only | 80 |
| 같은 partition에서 후보와 기능 둘 다 변경 | 80 |
| 서로 다른 partition | 640 |
| 합계 | 900 |

각 그룹50entry/225pair이며 no-link control과 actual greedy completion을 별도로 유지했다. Actual shape alias0이고 실제 비교에서 alias 양성의 정확도를 검증했다고 주장하지 않는다. Original cohort322문맥/1,013raw lanes, selected2/7·unexecuted320/1,006과 registered pool5를 유지한다. 두 구간은 두 작품의 전곡이 아니다. 원 native universe와, 직전 fixed 세 partition의42,851 eligible paths 중 기술 panel 제안12/미제안42,839라는 별도 분모도 새 contrast의 `logical_universe`와 부모 연결로 유지한다. Fixed panel 분모를 전체 logical universe로 대체하거나 전체 경로를 실행했다고 표현하지 않는다.

정확7output/3,056,742bytes는 plan·index·report 및4gz sidecar다. 부모148파일·4,752입력 SHA와335current code/schema/tests의 고유4,756보호 경로,6artifact의 생성 SHA를 확인했다. 코드/부모/아티팩트 변경0이다. Report를 포함한 최종 보호 경로 합계는4,763이다. 실행 도중 코드/한도를 바꾸지 않았고 기존 결과를 덮어쓰지 않았다.

| 정본/산출물 | SHA256 |
|---|---|
| `report.json` | `2db574a87f15d7df2789896e482dad59ad5f2987dc0dcc809c9002b2dfc30f5f` |
| `run-plan.json` | `c726294807b2896bd9036bc5d333228043ce18c102c930d4fc1fe8d67444f2b1` |
| `context-index.json` | `8401ebfe0676812a3d4f23efc608ac944b52258c719518c371be98e8b0abff02` |

Sidecar의 파일SHA는 report의 `artifact_hashes`, 내부 record ref는 index에서 확인한다. Internal content hash와 압축 파일 hash는 다른 값이다.

| Context/completion | 새 contrast record ID |
|---|---|
| Sonata no-link | `npccontrast_f54c5b45d9089ac96011cf7c` |
| Sonata actual greedy | `npccontrast_02178a322edb15f6940c2318` |
| Quartet no-link | `npccontrast_a46562f25ff05dcc17c463d3` |
| Quartet actual greedy | `npccontrast_fa2e799d022c539b22d77818` |

### 7.4 독립 저장 감사와 최종 QA

독립 metadata/참조/SHA 감사 **60,753유한 확인/13.9759738초 PASS**다. Strict saved JSON/gzip154reads로 원 full IR2의 content SHA·binding·source snapshot, 부모68batch와 새200entry/facet의 ordered refs·key/bundle/partition/vector/raw account pointer,900pair의 종류·rational transfer와 delta 및 분모를 확인했다. `load_inputs`/compare/native/role producer 호출이나 파일 수정은0이다. Creation 고유4,756보호 경로·current335code inventory·부모148/새7파일 exact, report/plan/index 및 네 source/test 동결 hash가 일치했다.

Root 별도 전수 stream SHA 검수 **1.8966553초/고유4,763경로 변경0**, 새7/부모148 inventory의 누락/추가0과 current335code inventory가 일치했다. Root QA7파일 strict UTF8/NUL/U+FFFD/줄끝공백·4AST·135로컬링크 오류0이다. Read-only `git diff --check`는 exit0이며 기존 별개 tracked5파일의 LF→CRLF 경고만 있었다. 이 다섯 파일의 사용자 변경은 건드리지 않았다.

독립 stdlib-only source/Fraction oracle 감사 **5,257,597유한 확인/18.0094096초 PASS**다. 200facet을 원 scope/native profile 및 saved role clip union에 대조하고,900pair의 전체 pair set·same key/bundle·4kind·35,100source-category atom·14,400bass-clock atom·모든 delta/transfer를 재산술했다. 실제 cover row visits533,160은 저장 planned pair bounds 이내였고 네 planned work를 exact 대조했다. 읽은151saved artifacts의 pre/post SHA와 정확 새7파일도 불변이다. Compare/native/role producer 호출이나 코드/파일 편집0이다.

독립 음악/source 감사 **108,089유한 확인/17.2802213초 PASS**다. 네 sidecar의200facet/900pair를 부모 exact refs/account/prerequisites 및 원 full IR 음표·onset/음가·sourceRef·타이·실제 최저음·ordered member 관찰·여섯 category/credited clause refs와 대조했다. 두 scope의23+53sound, 원raw85/2·53/2quarter를 보존하고 새7산출물의 pre/post SHA 변경0이었다. 원음표 연결 검수이며 화성/NCT/조성을 정답으로 승인한 것은 아니다.

네 선별 사례는 별도 **107유한 확인/1.2175661초 PASS**이며 공통 source 감사와 합산108,196확인/18.4977874초다. 이 단계의 음악 확인은 다음 exact saved refs로 재현할 수 있다.

- **§6.1 Quartet:** actual sidecar `npccontrast_fa2e799d022c539b22d77818`, left `fmilpath_4d14902b5b082d6ea174bf51` → right `fmilpath_b00b72380e72416bd3a8b5fc`. B♭2 `note_213e6b67ab58`/`sound_8c0d684da86e`는 printed m132·sequential index131, onset525/2·duration1/2다. `fmnroleclause_2cc395fa01f42745e63718d9`의 실제 C3→B♭2→A♭2 연결에서 member→conditional explained1/2 이동, no-link의 credit0을 확인했다.
- **§6.2 Sonata:** actual sidecar `npccontrast_02178a322edb15f6940c2318`, left `fmilpath_4a422e76a09dd982450cf1ca` → right `fmilpath_f132717aba4809cd1336e45b`. C5 `note_e2a1b25dcd7a`/`sound_f7604d13ebfc`와 `note_52fc80602b9b`/`sound_45909d61d285`는 각각 onset56/57·duration1·tie=None·별도 attack이다. `fmnroleclause_1534c8e49e79310f34bbd28c`의 reattack 및 [57,58) credit,4changed category atoms·member−7/6/credit+7/6을 확인했다.
- **§6.3 Sonata:** 같은 actual sidecar에서 full-hold `fmilpath_5c892da4f5b3d6b73e7d4893` 대 위 split은 `partition` 대비다. D♭5 `sound_cae7b39ad108`의 실제 attack45·full[45,101/2)·observed49·`tie_8f5b04834d7b`를 보존했다. Explicit `fmilpath_dc0ee624c06d71c3b79a9686`의 G♭는 미관측이며 `fmnroleclause_7e5f4579f66ce355224a0109`의 leading supported/whole ordinary 및 joint False/clips[]가 그대로다. 개별 해결이 전체 화음 해결로 승격되지 않는다.
- **§6.4 Quartet:** 같은 actual sidecar에서 위 full-hold 대 `fmilpath_2bde878712f287750db5016e`의 partition 대비다. Printed m133·index132의 [529/2,265)에서 D♭4 `note_6f9e46d296ef`/`sound_a5c465b77c58`가 실제 최저음이며 F4/A♭4와 동시 지원된다. 조건부 bass 해석은 다르지만 category delta0·changed[]다.535/2cut의 양쪽 ordered D♭ triad가 같다는 관찰도 실제 화음 교체나 자동 경계 삭제로 승격하지 않는다.

Root도 위 네 pair의 저장 category account·missing spelling·비교 종류·같은-signature cut을 읽기 전용으로 확인했다. 문서의 ordinary credit0이 전체 credit0으로 읽힐 수 있는 표현을 §6.3에서 한정했다. 코드/저장 결과를 바꾼 것은 아니다. 별도 세 문서의 독립 정합 검토도 수치·분모·SHA·무승격 표현 일치였으며, 메인 문서의 과거 “고정 자료 전체” 표현을 “당시 고정된 기술 패널의 제출 범위”로 좁혔다.

Saved 확인 횟수는 새 unittest 또는 곡/음표/음악 정답 수가 아니다. 새 cold 재실행·정답률/전곡 평가도 아니며 운영 악보 UI·구조·작곡/편곡은 아직 미변경이다. 문서 교정 후 root 최종 합동 QA **2.0341876초**,7파일text/4AST/135로컬링크·고유4,763creationSHA·부모148/새7inventory 오류/변경0과 read-only diffcheck exit0을 재확인하여 **이번 연구용 구현·실제 저장 대비·독립 검수를 완료했다.**

## 8. 다음 큰 단위

이 공동 비교에서 원음표 설명의 trade-off와 확실한 근거 결손을 확인한 뒤, 일반 음악적 제약을 적용한 진행 제안/보류 정책을 설계한다. 설명량 최대화, member-set 확장 또는 작은 grid cut 증가를 승자 선정으로 쓰지 않는다. Key/기능·실제 core·성부 해결·전후 화성 리듬을 여러 작품군에서 검사하고 기존 전체 악보 뷰어에 보일 조건부 비교/피드백 범위를 결정한다.

부족한 화성 근거를 프레이즈 추정이나 특정 사례 예외로 메우지 않는다. 최종 작곡·편곡은 검증된 화성 및 별도 역할/질감/배치 자료를 소비하는 다음 계층이며 이번 비교 데이터만으로 generation-ready라고 선언하지 않는다.
