# 경쟁 화성 진행·조건부 비화성음과 역할 근거 연결

기록 ID: `HARM-DEV-20261001-05`

날짜: 2026-10-01

## 목적과 이전 단계의 차이

사용자의 계속 진행 요청에 따라 [지속·재타격·순차 음군 근거](2026-10-01-musical-role-evidence.md)를 [여러 화성 진행과 공통 성부 가정](2026-10-01-progression-search-and-joint-comparison.md)에 연결한다. 이번 요청은 새 작품의 화성 정답이나 특정 마디의 예외 규칙을 추가한 것이 아니다.

이전 역할 evidence는 literal geometry와 명시적 화성 가정에 따른 member/nonmember/unknown을 저장했지만, 전후 연결을 요구하는 조건부 비화성음 패턴과 직접 연결되지 않았다. 이제 같은 음표-시간에 대해서 **화성 가정 → 원시 membership → 해당 진행과 한 assignment를 모두 만족하는 NCT 가설 → 역할 형태의 대안**을 추적한다.

현재는 연구용 연결이다. 실제 선율·내성·반주 역할을 선택하는 분류기, 반주 style 확정, 편곡 생성기, G1 전체 완료가 아니다. 화성의 조성·적용화음·기능·종지 연결 계획은 유지한다.

## 일반 규칙

1. 같은 score/IR document/content SHA/source files와 같은 context를 사용한다. 제목·마디 번호·MIDI만 같은 다른 판본을 연결하지 않는다.
2. 완전한 진행은 context 전체를 빈틈이나 중첩 없이 덮어야 한다. 각 segment의 원래 root/member spelling/extent/보류를 복사한다. 관측 구성음 합집합이나 미관측 음으로 새 화음을 발명하지 않는다.
3. 화성 track은 assignment 독립이다. 비화성음 설명은 **proposal + 단 하나의 sampled assignment**에 종속된다. 서로 다른 연결의 유리한 조각을 합치지 않는다.
4. raw part/voice lane은 기보 정체성이다. sampled assignment는 그 lane 안의 가능한 연속 연결이다. 둘 다 주요 선율·베이스·내성·반주라는 의미 역할을 확정하지 않는다.
5. member/nonmember/unknown의 원시 음표-시간은 바뀌지 않는다. NCT에 조건부 지지가 있어도 nonmember를 관측 구성음으로 바꾸지 않는다. 미지원 철자와 보류 후보의 unknown도 NCT로 면제하지 않는다.
6. NCT record에는 형태·전후 요구 음·정확한 span·동일 assignment·지원/보류 이유와 원음표/source references를 남긴다. 계류음의 미검증 박절/불협화/준비 조건은 그대로 보류한다.
7. 페달 형태와 NCT 설명이 같은 음을 설명할 수 있으며 경쟁 화성에서는 구성음일 수도 있다. 한 해석으로 다른 해석을 삭제하거나 서로 독립된 표로 합산하지 않는다.
8. 순차 profile은 기존의 attacks-only 관측이다. 화음 구성음 선율과 분산 반주를 구별하는 최종 판정이 아니며, 조건부 NCT가 존재한다고 기존 profile의 blocker를 자동 해제하지 않는다.
9. 모든 구간은 rational quarter와 `[start,end)`이다. 원 tie extent/attack/source note를 보존하고 profile에 연결된 시간 셀의 범위를 제한한다.

## 입력과 구현 계약

- `src/musicanote_harness/musical_progression_role_link.py` 최종 v0.1.1: `link(ir, observation, bundle, proposal, assignment_ref, *, pitch_policy, search_result=None)`. 반환값은 sealed sidecar다. 공개 `validate_link(...)`는 seal 확인과 전체 입력의 fresh replay를 요구한다. 검색의 `semantic_group_refs`가 있는 proposal은 원 `search_result`가 필수이며 모든 group/origin reading/adapter origin을 대조한다. representative origin 하나를 음악적 승자로 삼지 않는다.
- 같은 모듈의 `prepare_context(...)`, `link_prepared(context, proposal, assignment_ref)`, `validate_link_prepared(record, context, proposal, assignment_ref)`는 내부에서 검증한 불변 입력만 공유한다. caller hash/skip flag/dict를 prepared context로 받아들이지 않는다.
- `src/musicanote_harness/musical_progression_role_trial.py` 최종 v0.1.1: 기존 G1 inventory의 모든 observation × 모든 raw lane을 시도하는 offline 실행기.
- 각 파일에 대응하는 새 `tests/test_musical_progression_role_*.py`를 둔다. 기존 Core/observation/assumption/role schema와 production 코드의 의미는 변경하지 않는다.

sidecar에는 immutable binding, observation/bundle/proposal/pitch-policy/search-result SHA, 원 proposal와 assignment, 모든 candidate origin, assignment 독립 harmony assumption track, 기존 role evidence, full-path progression evidence, raw note-time, source-note별 연결, 조건부 NCT와 unresolved role links가 있다. `semantics`는 화성 선택/NCT 확정/페달·분산화음 확정/역할 검수/생성 준비를 모두 false로 표시한다.

이번 sidecar는 별도 JSON Schema를 추가하지 않고 기존 nested schema와 **전체 재계산 validator**를 사용한다. 저장 문서만의 hash 검사가 아니라 원 입력과 계산 의미를 대조한다. 운영/교환 계약으로 승격할 때 static schema와 저장소 index를 추가해야 한다. 기존 schema에 자유 분석 필드를 끼워 넣지 않는다.

## 음높이 기준과 source policy

FormalIRAdapter의 현재 `concert_pitch`/sound.pitch는 written pitch를 복사하며, parser manifest는 `concert_transposition` unavailable을 명시한다. 따라서 원 IR에서 해당 sound의 실제 attack written pitch와 연결된 note/tie/lane/time을 확인하고 frozen score의 XML transpose를 검사한다. part의 transposition=0이나 같은 MIDI만으로 통과하지 않는다.

새 실행의 기준은 `written_IR_not_concert_certified`다. 현재 source/IR digest와 명시적 `harmonic_replay_allowed=true`, `nonzero_source_transposition=false`, `malformed_or_unsupported_transposition=false`, `concert_pitch_normalization_verified=false`가 필요하다. source transpose의 비영/미지원/불완전 선언은 all-part harmony 계산을 보류한다. 선언 없음은 실음 인증이 아니다. 현재 G1의14개 snapshot에서 transpose 선언0, sound/attack written pitch 차이0, microtonal note0을 별도로 확인했지만 관현악 전반에 일반화하지 않는다. grace는 literal evidence에 남기며 기존 progression geometry가 지원하지 않는 context 단위만 보류한다. 현재 runner의 compressed MXL source transpose probe는 미구현이며 해당 입력은 보류한다.

## 고정 자료와 예산

입력은 `output/musical-semantic-alignment-2026-10-01-r2/`의14 score files/27 observations다. 기존 source coordinate/alignment를 fresh replay하며 source RN은 후보 생성기·정답으로 전달하지 않는다. **주석에서 선정된 구간**이라는 표본 편향은 그대로 명시한다.

각 raw lane은 별도 assignment family다. 화음 후보/원시 membership/role geometry는 모든 part를 본다. 한 lane에서 계산한 NCT를 다른 lane의 assignment와 합치지 않는다. 단일 lane만 주요 선율로 선택하지도 않는다.

초기 예산: edges256, segments4, per-state prefix2, complete proposals8, transitions200000, assignments64, role links128/단위. 기존 검색의 근사 제외와 candidate blocker를 보존한다. assignment/link 한도를 넘으면 **해당 단위 전체**를 보류하고 inventory를 유지한다. 가장 그럴듯한 assignment 몇 개만 남겨 성공 상태로 만들지 않는다. assignment 한도는 성부 inventory 뒤, 비싼 lattice/catalog 생성 전에 검사한다. 독립 voice enumeration 한도에 먼저 걸린 단위는 그 이유를 보존하며 작은 성공 subset으로 바꾸지 않는다.

`report.complete`는 고정 분모 처리와 입력/코드 무변경·계산 integrity를 뜻한다. 음악 분석 전부 완료가 아니다. 예상된 grace/예산/성부 inventory 보류도 자료에 남기며, 예상치 못한 계산 예외는 `integrity_or_computation_abstention`으로 저장하고 `computation_integrity_passed=false`, `complete=false`를 반환한다. 예외가 났다고 해당 lane이나 literal 음표 기록을 버리지 않는다.

오래된322개 harmony context를 이번14악보/27구간과 제목으로 연결하거나 자동 backfill하지 않는다.

## 실제 실행 이력

초기 `output/musical-progression-role-2026-10-01-r1/`은 v0.1.0의 전 후보 fresh replay로 시작했다. 실행을15분이상진행했으나 첫 eligible 32-link 단위의 반복 검증이 끝나지 않아 2026-10-01 06:27:40 Asia/Seoul에 개발자가 Ctrl-C로 중단했다(exit1). 입력이나 음악적 guard 오류가 검출된 것은 아니다. 입력172/source·schema278 SHA와 전체 목록은 중간 독립 대조에서 불변이었다.

run plan·7 literal 기록·30 보류 packet과 별도 `INTERRUPTED.md`를 보존한다. 30개는 voice inventory21/lattice5/grace3/early assignment1이다. **최종143분모 검사와 report는 없으므로 r1을 전체 완료나 최종 수치로 쓰지 않는다.** 후보 pruning이나 한도 증가 대신, 아래의 immutable context/role 공유를 구현하고 다른 디렉터리 r2로 다시 실행했다.

### 최종 r2 실행과 분모

`output/musical-progression-role-2026-10-01-r2/`는 v0.1.1로 **984.677초 / exit0**에 완료했다. `report.complete=true`, `inputs_and_code_unchanged=true`, `computation_integrity_passed=true`다. 이는 정해진 분모와 보존·계산 검사가 끝났다는 뜻이며 음악적 판정의 완료가 아니다.

| 단위 상태 | raw lane 단위 수 | 보존한 이유 |
|---|---:|---|
| 조건부 연결 계산 완료 | 2 | 두 구간의 각각 한 raw lane; 선택된 화성·역할이 아님 |
| 성부 inventory 보류 | 68 | global assignment 열거 한도63, 빈 lane5. 원 reason 배열의 lane sound 한도2는 일부 단위에서 중첩 |
| lattice 보류 | 30 | edge 한도 초과; 유리한 subset으로 pruning하지 않음 |
| 장식음 timing 보류 | 25 | 현재 progression geometry의 grace point 미지원; literal 자료에는 보존 |
| early assignment 예산 보류 | 15 | 전체 inventory가64를 초과하여 비싼 후보 계산 전에 보류 |
| path × assignment 예산 보류 | 3 | 전체128-link 예산 초과; 일부 pair만 성공으로 보고하지 않음 |
| 합계 | 143 | 14 score files / 27 observations의 모든 raw lane |

27 literal role 기록과143 packet을 모두 저장했다. 2개 단위의 **40 proposal × assignment link instances**는32(8진행×4연결)와8(8진행×1연결)이다. assignment 독립 harmony track/conditional role evidence는 각각 **16개 고유 기록**이며40개의 서로 독립된 음악적 지지표가 아니다. 같은 구간의 분할·quality 대안도 독립 악곡으로 세지 않는다. `independent_piece_count=null`을 유지한다.

**실제 active NCT pattern link는0개다.** 합성 양성·반례에서는 assignment 차이에 따른 조건부 NCT 계정이 검증됐지만 이번 실제 자료에서 인식 능력 향상을 검증한 것은 아니다. 원 후보의 박자·무음 blocker도 유지한다. 검수/training/gold/generation-ready는 전부0이고 accuracy는 측정하지 않았다.

16고유track의40 **track–segment incidences**는 usable14/blocked26이며 blocker는 `meter_missing_or_changed`18와 `silence_inside_window`8이다. 같은 segment ID를 제거한30개 고유 segment records는 usable11/blocked19(박자13/무음6). 모든16track에 적어도 하나의 blocked segment가 있으며9개는 전체 blocked,7개는 usable/blocked 혼합,전체 usable path는0이다. 즉2개 단위의 계산 완료는 전 구간의 화성/역할 해석 가능성을 뜻하지 않는다. 이 코드는 기존 후보 공급기의 보류 이유이지 원 XML에 박자가 없거나 음악적으로 침묵이 화성 유지를 금지한다는 독립 진단이 아니다. 따라서 NCT0을 성부 조합만의 문제로 설명하지 않으며, 다음 실제 확대에서 공급기 판단의 적용 범위도 구별해 대조한다.

### 재현 명령·환경·출력 계약

workspace root에서 다음을 실행한다. 기존 r2 디렉터리를 다시 쓰면 거부되므로 재실행 시에는 **존재하지 않는 새 output 디렉터리**를 지정한다. 입력과 예산을 바꿔서 같은 실험 이름을 재사용하지 않는다.

```powershell
$env:PYTHONPATH='K:/Music Analysis/src'
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe -m musicanote_harness.musical_progression_role_trial --alignment output/musical-semantic-alignment-2026-10-01-r2 --output output/musical-progression-role-2026-10-01-r2
```

실제 환경: Windows / Python3.12.14 / music21 10.5.0 / jsonschema4.26.0 / referencing0.37.0. schema·source·input의 경로와 SHA, 선택 기준/예산/실음 미인증, 재사용 계약은 `run-plan.json`; 모든 lane의 상태·이유·packet SHA는 `unit-index.json`; 최종 집계·artifact SHA와 한계는 `report.json`에 보존한다. 계산 예외/입력 변경0이다.

- link module SHA256: `27b8475d14989b7b25d8e11127ca5d171a35ff0c960c46bea74ce9b8a29cde65`.
- trial module SHA256: `289260387bac7efa013072165a761f89dbe71cc969ed9dbb7eb422043efdd45e`.
- report file SHA256: `77ca734d12578f856d8bf343f3326767e997c01914f489ec717a046814324eee`.

### 실제 자료 대조

1. **Coleridge-Taylor, Op.57 No.6 — Too late for love.** source relative path `OpenScore-LiederCorpus/Coleridge-Taylor,_Samuel/6_Sorrow_Songs,_Op.57/6_Too_late_for_love/analysis.txt`, physical line21의 명시적 Pedal endpoint에서 이전 G1이 선정한 구간이다. observation `mpo_384c7cc3a07ead81a65f61a8`, exact source case `source_case_fe67fa9d7a66969f6756b816`, G1 artifact directory `cases/39c7a7728069dc954988864e/`. target q[29,32), context q[26,36), lane `part_eb353edbe691/voice_8036fd13bb64`. 새 packet은 `observations/3b431046694272d43d9751bd/5df8909948973066.json.gz`. 원주석 화음 기호는 추론 입력/정답으로 주지 않았다. 첫 proposal의4개 assignments는 같은 track/role을 공유하며 member89/2, unexplained nonmember13, conditional/withheld/spelling-unresolved0을 유지한다. 이 수치는 모든 part의 **quarter-note-time 합**이며 elapsed10quarters나13음표라는 뜻이 아니다. 첫 path에는 `meter_missing_or_changed`가 있어 역할 해석을 보류한다. 32 link 전부의 active NCT는0이다. 시간 셀의 raw 구성음 대응이 있다고 blocker를 제거하거나 해당 label을 확정하지 않는다.
2. **Maude Valérie White — A Memory.** source relative path `OpenScore-LiederCorpus/White,_Maude_Valérie/3_Little_Songs/2_A_Memory/analysis.txt`, physical line25의 명시 endpoint. observation `mpo_e84728d1fa1dbbb6a6b693cb`, source case `source_case_20e55247e05cc3dd44703f5f`, G1 directory `cases/74fb3aa37d2626289b48c5e1/`. target q[75/2,39), context q[33,45), lane `part_1cc8f1f7c8ff/voice_5c246e4e0749`. packet `observations/b3afa67f895f75bf16ae457a/79a6a8fee30ac97c.json.gz`에8진행×1assignment를 보존했다. 첫 전체 유지 path는 `silence_inside_window`로 보류하고 분할 대안도 보존한다. 첫 path의 raw member99/2·nonmember0은 전부 옳은 화음이라는 판정이 아니다. 다른 quality 대안에서는 member46·nonmember7/2로 달라진다. 이 음악의 확정 종지/반주 style이나 source copy/range 검증 완료를 주장하지 않는다.

G1 snapshot filename에서 나온 title `score`는 작품 식별자로 사용하지 않았다. 원 경로·statement/hash·IR binding을 따르며 두 작품에 맞춘 코드 조건은 없다.

## 대조 예제와 회귀 검사

독립 XML→정식 IR fixture의 `C4(1 quarter) → D4(1 quarter) → E4(2 quarters)`에 관측 C–E–G 구성음 가정을 둔다. C→D→E 연결을 가진 assignment에서는 D4의 1 quarter가 `conditional_nonmember`로 설명되지만, 같은 원음·같은 화성에서 무연결 assignment는 그 1 quarter를 `unexplained_nonmember`로 남긴다. **두 경우 모두 D4의 raw nonmember 1 quarter와 화성 track은 동일하다.** 조건부 설명만 다르며 경과음으로 최종 검수한 것은 아니다.

이 조건부 경과음이 있다고 순차 질감의 `nonmember_or_unknown_attacks_present` blocker를 없애거나 분산 반주라고 판정하지 않는다. 준비된 하행 계류 형태도 박절·불협화·준비·해결의 검증이 부족하면 `withheld_nonmember`와 원 보류 사유를 유지한다. 셋잇단음표의 1/3 quarter, 타이로 연결된 두 기보음/한 sound/한 attack, 범위 밖 lane의 grace point, 같은 구성음의 유지/분할도 독립 대조한다.

초기 v0.1.0 신규 검사50개(link35/runner15), 전체 Python **2,544개 / 94.267초 / OK**. 두 source module이 고정된 상태에서 실행했으며 기존 layout warning 1건은 유지했다. seal 재발급 뒤 원음·시간·candidate origin·assignment·pattern·source 정책을 바꿔도 fresh replay가 검출하는 반례, 누락/중복 lane·input/source/코드 변경·예산 초과·계산 예외에서도 분모/literal 보존하는 반례를 포함한다. 검사 수를 악곡 수나 음악적 정확도로 해석하지 않는다.

v0.1.1의 최종 신규 검사는64개(link49/runner15)다. Prepared/public fresh 결과의 모든 assignment별 canonical byte equality, 연결/무연결의 서로 다른 NCT 계정, context·geometry1회/proposal별track·role1회/vector호출별fresh, 입력/반환/내부 cache 오염과 재hash 조작·다른 handle 교환·실제 schema 내용 변경을 검사한다. registry는 weak lifecycle이며 opaque context가 해제되면 큰 snapshot을 계속 전역 보관하지 않는다. runner는 전체 source/schema 목록 및 부모 artifact 추가/삭제도 최종 재대조한다. 관련 회귀119개18.08초OK; 최종 전체 Python **2,558개 / 96.863초 / OK**. 독립 추가19개 all-assignment 기록에서도 근음 미정·1/3 quarter·타이·context 밖 coverage holes·보류 후보를 public fresh와 대조해 전부 동일했고 원 입력은 불변이었다. 이것도 음악 정답19개라는 뜻은 아니다.

최종 실제 r2의 별도 bounded 감사에서 입력172/code·schema278/등록 output artifact172 SHA와 전체 목록,143고유 raw-lane keys/27literal/25grace units,40 link·16track·16role seal, 전체 proposal×assignment 쌍과 raw 음가 보존을 대조해 모두 일치했다. output172는 plan1/index1/literal27/packet143이며 자체 report는 별도 SHA로 기록한다. 같은32 links의3,680 notated source overlap refs도 exact rational/source로 대조했다. 별도 process에서 첫 실제 link `mprl_15e4e22e18805a225eb2c2ee` 하나를 공개 `validate_link`로 독립 fresh 재생한 결과15.354초/전체23.735초/exit0, equality와 원 record·7개 호출 입력 digest·관련 파일 SHA 불변을 확인했다. 이 actual smoke는 한 link의 cache-bypass 의미 일치이며40개 전부의 비싼 독립 catalog 재실행이나 음악 전문가 검수가 아니다. r1의30보류 packet body와7literal도 새 r2에서 동일하게 보존됐다.

같은 `PYTHONPATH` 환경에서 전체 회귀를 재현하는 명령은 `.venv/Scripts/python.exe -m unittest discover -s tests`다. 변경한 source2/tests2/화성 개발 문서4/r1중단 기록1의 strict UTF-8·replacement character·trailing whitespace·로컬 Markdown link 검사도 통과했다. tracked 파일의 `git diff --check`는 오류0/기존 LF→CRLF 경고만 있으며, 새 untracked 파일은 별도 문자/공백 검사로 대조했다. 원 dirty worktree의 다른 변경을 정리·stage·commit하지 않았다.

처음 link fixture 27개 실행 중 interval plan을 훼손한 반례는 `stored_interval_plan`보다 먼저 `incomplete_context_path`에서 차단됐다. 테스트의 예상 오류 문자열만 정정했으며 source guard나 음악 규칙을 완화하지 않았다. 실제 실행 전 탐색 smoke에서 840 assignments를 비싼 catalog 계산 뒤 보류하는 낭비가 확인되어 중단했다. 최종 runner는 같은 inventory를 보존하면서 이 한도를 lattice 생성 전에 검사한다. smoke 중단은 새 r1 corpus 결과의 실패나 성공으로 세지 않는다.

## 상태·남은 과제

이 단계는 관측과 조건부 설명을 연결하는 계약이다. 실제 역할 선택과 정확도 개선은 음악 검수와 더 다양한 positive/negative 사례가 필요하다. 긴 구간의 assignment/interval 조합 보류를 무작정 한도 증가로 해결하지 않는다. 후속에는 필요한 관계별 제약·factorized 계산, 일반 observation provenance와 이전 Beethoven/Mozart 문맥의 명시적 판본 연결, 조성·기능·종지/역할의 공동 대안 비교를 기능 단위로 진행한다.

현재27관찰은 source Pedal endpoint에서 선정됐으므로 긴 베이스/지속음에 편향돼 있다. raw lane을 모두 시도했지만 복잡한 선율·피아노 lane은 조합 한도에 걸린다. `musical_pattern_observation`의 현행 계약은 source statement/alignment를 요구하므로, 이전322화성문맥을 연결하기 위해 가짜 source 주석을 만들지 않는다. 다음에는 **주석 독립적인 관찰 계획 provenance**를 별도 연구 extension으로 설계해 exact working-IR/revision·문서/hash·원 source·all-part 문맥을 보존하고, 같은 positive/negative 조건을 실제 Beethoven/Mozart 음형에서도 대조한다. Core 의미를 바꾸거나 임의 title mapping으로 범위를 늘리지 않는다.

### 계산 비용·v0.1.1 보완과 다음 큰 구현 단위

이번 v0.1.0은 correctness-first fresh replay이며 batch 안에서도 `link`와 `validate_link`가 각각 payload를 재구성한다. 각 payload의 pattern 검사도 모든 cuts × assignments를 다시 계산하므로 P proposals × A assignments를 연결할 때 이 부분은 대략 P × A²로 반복된다. 실제 실행의 첫 32-link 단위가 느린 이유를 '음악이 어렵다'만으로 설명하지 않는다.

기존 판단의 의미를 바꾸지 않는 **불변 문맥 준비와 제약 기반 공유 계산**으로 대응한다. 아래1·2의 invariant 공유는 이번v0.1.1에서 구현했고,3의 lossless 성부 factorization은 후속 큰 기능이다.

1. 실제 IR/observation/policy/bundle/search 내용의 canonical bytes/digest와 engine versions·Core/pattern/assumption/role의 실제 schema SHA 계약을 묶은 `prepared_context` 내부에서 geometry·lattice·assignment partition·pattern inventory를 한 번 대조한다. process-local private 인증과 opaque handle로 내부 state 교환/오염을 검사하며 caller가 건넨 hash 문자열만 신뢰하지 않는다. immutable snapshot을 사용하고 cache-bypass 결과와 전체 equality를 검사한다. 공개 `validate_link`의 독립 fresh replay는 유지한다. 이 내부 공유 계약은 외부 교환 서명이나 다른 process에서 영구 cache 인증을 제공하는 기능이 아니다.
2. literal geometry는 IR+observation 단위, harmony track/role evidence는 정확한 proposal 및 lineage 단위로 공유할 수 있다. 원 assignment를 읽지 않는 부분만 공유한다. NCT accounting·active/withheld pattern·그 accounting index를 참조하는 source/role 연결은 반드시 proposal × 단 하나의 assignment 단위로 재계산한다.
3. 그 뒤 성부 연결의 독립 matching components를 손실 없는 DAG/decision diagram 또는 동등한 제약 표현으로 보존한다. touching time·같은 raw lane·분기/병합 금지와 원 membership 같은 검증된 관계만 hard constraint로 쓴다. 음역·도약 크기·최상성부 추정으로 유리한 연결만 잘라내지 않는다. 원 assignment ID/계보와 무연결 대조를 유지하고, future resolution이 읽는 관계까지 포함해 equivalent 여부를 판단한다.

자료 공유는 원 후보를 하나의 해석으로 병합하거나 음악적 지지표 수를 늘리는 일이 아니다. 계산 확대 뒤 조성·secondary·기능·cadence의 공동 해석과 chord-relative 반주 슬롯을 원래 계획대로 연결한다. 별도의 장기 source 정비만 계속하며 이 기능들을 무기한 미루지 않는다.

Core/parser/source XML/주석/기존 output/권리·split/Gold·training/외부 API/Git/운영5173·8822/구조 분석은 이번 단계에서 변경하지 않는다. 사용자의 음악 해석 선택이 필요한 실제 경쟁 사례는 전체 악보와 앞뒤 범위를 함께 준비한 뒤 요청한다.
