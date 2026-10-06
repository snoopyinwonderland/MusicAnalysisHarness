# 완전한 진행 후보의 조건부 조성·기능·종지 전제 연결

개발 기록 `HARM-DEV-20261002-21` · 2026-10-02. 현재 상태: 연구용 구현·동결 검사·실제 r1·저장 결과의 독립 감사 완료. 운영 적용이나 음악적 정답 판정 완료는 아니다. 이 문서는 화성 분석 개발 문서이며 인수인계 문서가 아니다.

## 1. 목적과 기존 단계와의 관계

[직전의 완전한 진행 공동 비교](2026-10-02-complete-progression-evidence-contrasts.md)는 같은 원음·구간·key 가정·실제 전 성부 completion 아래 full-hold/one-cut의 구성음, 조건부 비구성음 설명, 미설명 음가와 명시 기능 대안을 보존했다. 이번 단계는 그 **동일한 원 진행**에 경계 전후의 조성 좌표·전위·성부 진행·종결음 지속·뒤의 계속 여부를 연결한다. 화음 후보·경계·key·completion을 새로 선택하는 단계가 아니다.

사용자 방향은 큰 기능 단위를 먼저 처리하고, 교재에서 정리한 규칙을 실제 음표와 여러 작품에서 검증하며, 작곡·편곡에 활용할 해석 근거를 보존하는 것이다. 특정 작품·마디의 화성 기호를 조건식에 넣지 않는다. 기존 원XML/IR, 원주석, 과거 결과, parser, 운영 화면과 구조·생성 계산은 변경하지 않는다.

이번 일반 규칙은 [추론 규칙 설계](../HARMONY_REASONING_RULES.md)의 R01/R03/R05/R06/R07/R08/R09/R11/R12를 이어받는다. 각 장의 이론을 모두 구현했다거나 이번 결과가 검수된 음악 정답이라는 뜻은 아니다.

## 2. Native 연결 계약

### 2.1 같은 authority와 원 식별자

직전 단계의 authentic owned session과 saved comparison을 받아 그 기록을 원 selector·등록 bundle·저장 한도로 다시 대조한 후 새 authority를 만든다. 원 nine-parent API도 제공하되 실제 실행기는 구간당 한 번의 authentic parent 재검증을 공유한다. 300 selector마다 원자료 전체를 cold replay하지 않는다.

새 sidecar는 원 `logical_tuple`, `origin_refs`, `profile_refs`, `key_ref`, `bundle_ref`, 완전 partition과 `[start,end)` 분석 범위를 참조한다. 과거 `fmview`/legacy path로 위장하지 않는다. 기존 context/cadence 모듈의 순수 계산 원칙은 참고하되 그 모듈의 다른 provenance 계약을 꾸며 전달하지 않는다. 새 진행·더 큰 key universe·추가 completion을 만들지 않는다.

### 2.2 관찰과 조건부 해석 분리

- literal boundary는 start/internal/end 좌표마다 공유한다. 앞의 left limit은 `start < t <= end`, 뒤의 active sound는 `start <= t < end`로 구분한다.
- 원 onset, full sounding release, 관찰 clip, 새 attack, tie continuation과 지속은 서로 다른 값이다. 구간 끝 뒤의 관찰이 없다는 사실을 쉼표·종료로 바꾸지 않는다.
- 실제 최저음/최고음의 모든 동률 철자를 남긴다. 최저음은 구조적 bass, 최고음은 주요 melody라는 확정이 아니다. written/concert 불명확성도 보존한다.
- 후보 근음·ordered member·음계 form 아래 구성음 factor, 음도와 전위 근거를 계산한다. PC가 같다는 이유로 철자 차이를 버리지 않는다.
- 마디/박자와 유리수 beat coordinate는 기보 관찰이다. 실제 강세·호흡·지휘 beat나 performed timing을 확정하지 않는다.

### 2.3 같은 completion의 전후 연결

최저/최고 원음의 전후 pair와 직접·지연 ordinary 해결은 **동일한 등록 전 성부 completion**에서만 대조한다. 지속된 같은 sound의 intrinsic carry와 실제 새 sound로의 연결을 구분한다. 다른 completion, 다른 lane, 가장 가까운 pitch 또는 구간 밖 metadata에서 유리한 해결을 빌리지 않는다. XML raw lane 자체가 음악적 성부 확정은 아니다.

## 3. Secondary와 종지에 대한 규칙

### 3.1 Applied라는 문자열은 해결 증거가 아니다

직전 `_function`은 목표 근음의 key 좌표에 따라 `function_kind=applied`를 저장하면서 실제 source/target shape mismatch로 `status=withheld`일 수 있다. 따라서 applied 행 수를 Secondary 탐지 성공 수로 보고하지 않는다.

별도 축에 다음을 보존한다: 명시 V/vii family와 target quality의 exact spelling 형태, key 가정·scale form, 목표 음도·조표 밖 음 좌표, 실제 구성음/bass/source guards, 동일 bundle의 ordinary 역할·진행 근거. 이 조건들이 결합되어도 국소 조성·tonicization·modulation이나 최종 Secondary 정답을 확정하지 않는다. Unknown key 아래 음악적 연결 기하가 존재하는 것과 기능을 분류할 수 있는 것은 다르다.

### 3.2 Cadence는 전제를 구체화하되 아직 확정하지 않는다

도착 화음·이전 진행의 조건부 기능, 도착 순간의 실제 bass/upper와 전위/음도, 박절, 종결음의 full release, 뒤의 attack/rest/지속 관찰을 같은 경계에 연결한다. 도착 시점과 종결음 release는 다르다. V 도착 하나를 Half Cadence로, V→I 형태 하나를 PAC/IAC로 바꾸지 않는다.

기존의 미확립 의미 전제도 남긴다: 국소 조성의 확정, 구조적 bass/melody, 지각 강세, 협화 해석, phrase-terminal과 performed timing. PAC/HC/IAC 관련 전제는 후보 점검용이지 cadence 판정이나 학습 Gold가 아니다. Phrase 결과를 화성 근거로 끌어와 순환 강화하지 않는다.

현재 nominal PAC는 명시 dominant family·home tonic의 형태/quality와 관측 최저음의 조건부 root position·관측 최고음의 tonic degree를 대조한다. Nominal IAC는 화성 형태 조건까지만 대조하고 literal refinement는 미정이다. HC는 시작이 아닌 ending 후보의 dominant 음도·major/dominant-seventh 형태 조건이다. **이 nominal 값은 ordinary joint function, 실제 구조적 종결 또는 cadence verdict가 아니다.** Ordinary 같은-bundle 지원 상태와 실제 release/뒤의 계속 관찰은 별도 축으로 남는다.

## 4. 한도·분모·저장 규칙

모든 selector와 경계·전후 pair·논리 작업량을 계획한 후 전체 요청의 한도를 검사한다. 예산 초과시 유리한 일부만 계산해 남기지 않고 whole hold와 알려진 inventory/universe/보류 이유를 보존한다. 알려진 0, 미관측 null, False를 혼동하지 않는다. 공개 raw API의 한도 이름·자료형은 cold parent 작업 전에 검사한다.

기본 한도는 hypothesis 64, boundary observation 2,048, transition pair 4,096, query work 200,000이다. 구현과 단위 검사에서 실제 필드 의미·whole-hold 동작을 확인한다. 최종 진행 선택·rank·confidence·확정 화성/key/NCT/cadence·학습/Gold·운영 변경은 없다. Key 후보가 원 조표 관찰에서 생성되었다는 provenance는 숨기지 않되 조표를 실제 key 증명으로 쓰지 않는다.

이번 실행 대상은 직전 선택한 5문맥/15 raw lanes의 재현 가능한 기술 panel이다. 300 selector는 distinct 진행 300개 또는 300곡이 아니다. Selector 경계 발생 수, distinct tuple×key×boundary, literal context coordinate 수와 복원한 function 형태/실제 motion 평가 수를 따로 보고한다. 선언된 전체 322문맥/1,013 lanes와 미실행 317/998은 유지한다. 전체 음악 정확도 평가·전곡 분석 완료가 아니다.

새 결과는 기존 출력과 다른 직접 자식 폴더에 append-only로 저장한다. 모든 parent/원자료 SHA, 현재 producer/schema inventory, generated artifact 목록과 hash를 전후 대조한다. 저장 자료 산술/참조 감사는 authentic cold replay와 구별한다.

## 5. 구현 파일과 검증 계획

- Core: `src/musicanote_harness/factor_progression_context.py`.
- 실행기: `src/musicanote_harness/factor_progression_context_trial.py`.
- 검사: `tests/test_factor_progression_context.py`, `tests/test_factor_progression_context_trial.py`.
- 공개 API: `prepare_context_prepared`, `prepare_context`, `build_context_prepared`, `build_context`, `validate_context`.

신규 단위 반례는 applied 형태와 실제 해결의 분리, unknown key, wrong shape와 source guard, 동일 bundle 여부, equal-height enharmonic bass, tie carry/새 attack, release가 horizon 뒤에 있는 경우, rest 동안 다른 성부의 지속, 유리수 경계, full-hold/terminal, whole budget와 인증·바꿔치기 거부를 포함한다. Compound meter/pickup 등은 기존 cadence/context 회귀에서 대조하며 신규50개의 커버리지로 늘려 세지 않는다. Pure-helper 반례와 genuine prepared authority를 통한 공개 검사를 구별한다.

## 6. 검증·실제 실행 기록

### 6.1 발견·보완과 검사 이력

초기 신규 핵심 40개(실제 prepared authority를 쓰는 공개 검사30개 + 별도 pure-helper 반례10개)/101.593초는 통과했다. 이를 최종 동결 검사로 대신하지 않는다. 이후 실제 API의 primary/applied/unknown key 및 같은 bundle의 ordinary 근거, 인증/원자료 바꿔치기와 public raw API를 추가로 검사했다.

보강한 50개 중 첫 실행은49개 통과/1개 실패(167.381초, 전체168.170091초)였다. Unknown key의 `signature_used_for_candidate_universe`를 False로 기대한 검사가 원 provenance와 충돌했다. 실제 unknown 후보도 동일한 signature-derived universe 출처를 보존하며, 조성 좌표가 미정이라는 것과 후보 universe의 출처가 없다는 것은 다르다. 검사를 원 key의 provenance/declarations exact match와 unknown coordinate 보류를 대조하도록 고쳤다. Source나 원 key를 False로 바꿔 통과시키지 않았다. 최종 재검사를 별도로 기록한다.

자체 검토에서 HC dominant seventh의 기존 helper quality 이름 `major_minor_seventh`를 정확히 연결하고, 순수 boundary 시간 입력의 bool/float를 거부했다. 원 계정을 sealed record인 것처럼 참조하지 않고 phase20 path ref + JSON pointer + content SHA로 연결했다. 장·단조가 다른 parallel tonic은 원 기능 대안으로 보존하되 home cadence의 nominal 조건으로 삼지 않는다. 분석 시작의 첫 도착 화음은 ending/HC 후보로 삼지 않는다. 이는 최종 cadence 판정이 아니라 조건부 전제의 제한이다.

실행기 초기 storage-only mock 34개에서는 context identity를 빠뜨린 synthetic hold fixture 때문에 동일 record ID의 저장 충돌 1개가 발견됐다. Fixture를 교정하고 production no-overwrite 조건은 유지했다. 임시 in-memory placeholder 검사이며 core 검증으로 집계하지 않는다. 실제 native import의 중간 34개/2.267초와 최종 실행기 37개/2.591초(전체 3.412349초, exit0)는 별도 실행이다. 최종 source/test checksum은 전후 동일하다. 이 mocked runner 검사는 실제 corpus cold replay가 아니다.

Root의 별도 기존 회귀는 functional comparison/cadence prerequisites/context observation/phase20 core+runner **5suite 173개/267.587초 OK**다. 신규 검사와 합쳐 한 번의 전체 Python 실행이라고 하지 않는다. 직전 단계의 전체 검사·실제 결과 이력은 그 정본에 그대로 보존했다.

### 6.2 실제 자료의 읽기 전용 사전 계획

저장된 직전 5문맥에 순수 `_plan`만 적용한 2.474434초의 읽기 전용 점검에서 875 selector별 경계 발생, 605 same-raw-lane pair 발생, logical work 25,800, 문맥별 cache의 literal 좌표 합15/terminal probe 합43을 확인했다. 구간별 work는 Quartet 7,581/Sonata 4,210/Chopin 3,830/Corelli 5,679/Mozart 4,500으로 모두 기본 한도 안이다. 이는 authentic authority를 발급하거나 실제 phase21 결과를 저장한 검사가 아니다.

### 6.3 최종 동결 검사와 실제 r1

최종 신규 핵심 **50개(공개 계약40 + pure helper10)/166.253초 OK**, 전체 측정167.179014초다. 전후 test SHA가 같다. 실행기37개/2.591초에 이어 모든 source 동결 후 root가 실행기37개를 다시 검사해 **2.560초/exit0**로 통과했다. 기존5suite173개/267.587초는 별도 실행이다. 같은37개 재검사를 새 검사항목으로 더하지 않으며 고유 합계260개를 한 번의 전체 Python 실행으로 표현하지 않는다.

| 동결 파일 | SHA256 |
|---|---|
| factor_progression_context.py | `709f9619ca280ee95d2b4df5c0c9eb351045e5b96935286b63bf98339f75bc2f` |
| factor_progression_context_trial.py | `630fc792958db1c9eabf9f1bd617530427c64110e45652ca797f9089c52277cb` |
| test_factor_progression_context.py | `de4fd45b556c22a127c8f70c3488c330fbad031160533f5bca2958318db8e360` |
| test_factor_progression_context_trial.py | `d25c780594d96b75bf4de2947a7fa575b5ea962098836c439b624b1831cbceb0` |

동결 후 단일 authentic parent cold process로 실제 r1을 실행해 **exit0/1,594.719346초, 5문맥 저장·0실패**로 마쳤다. 재실행한 여러 cold 결과를 합친 수가 아니다. 이 시간은 전체 준비·재검증·계산·저장 비용이며 hot 조회나 운영 화면 지연 시간이 아니다. Source/tests는 실행 전후 동일하다.

산출물은 [report.json](../../../output/factor-progression-context-2026-10-02-r1/report.json), [run-plan.json](../../../output/factor-progression-context-2026-10-02-r1/run-plan.json), [context-index.json](../../../output/factor-progression-context-2026-10-02-r1/context-index.json)과 gzip sidecar5개, 총8파일/5,610,484bytes다. `scope_calculation_complete`, `computation_integrity_passed`, `selected_denominators_complete`, `inputs_and_code_unchanged`, `artifacts_unchanged`는 모두 True이고 failure/changed 목록은 비었다. 이 integrity 값은 음악적 정확도가 아니다.

| 실제 문맥 | 원 관찰 범위(global quarter) | selector 경계 발생 | same-raw-lane pair 발생 | logical work | joint conditional function | 조건부 전위 관찰 |
|---|---|---:|---:|---:|---:|---:|
| Beethoven Quartet n01op18-1_04 | [262,270) | 175 | 110 | 7,581 | 0 | 120 |
| Beethoven Sonata 01-1 | [49,61) | 175 | 110 | 4,210 | 4 | 110 |
| Chopin BI105-2op30-2 | [10,22) | 175 | 110 | 3,830 | 0 | 55 |
| Corelli op01n01a | [32,44) | 175 | 165 | 5,679 | 4 | 310 |
| Mozart K280-1 | [18,27) | 175 | 110 | 4,500 | 0 | 125 |
| 합계 | 5선택 문맥/15raw lanes | 875 | 605 | 25,800 | 8 | 720 |

원300selector/75distinct tuple×key를 보존했다. 875는 selector별 중복 발생이며 distinct tuple×key×boundary는200, cache의 literal context coordinate 합은15, terminal probe 합은43이다. Function 형태1,250개·전제 평가275개·실제 motion 평가25개, explicit key 좌표240path·unknown60path, PAC/HC/IAC 전제2,625개(875×3)는 서로 다른 분모다. Joint8은 검수된 Secondary8개가 아니고 조건부 전위720은 정확한 전위720개가 아니며, 2,625는 탐지한 종지 수가 아니다.

Root의 별도 저장 분포 대조에서 nominal HC는True15/False494/null366, PAC는True0/False271/null604, IAC는True0/False269/null606이었다. 세 타입별 분모는875이며 confirmed는 전부False다. HC nominal15는 ordinary 공동성공·국소 조성·phrase terminal을 확립한15종지가 아니다. 이 기술 panel에는 실제 자료의 PAC/IAC nominal 양성 검증이 없으며 해당 public fixture 반례 검사와 혼동하지 않는다. 후속 평가에서는 종지별 실제 양성·음성·모호한 구간의 작품군을 별도로 준비해야 한다.

이번 요청의 whole hold는0이다. 전체1,068,810진행/5,344,050진행×key/106,845,950function 행과 미평가5,343,975진행×key·106,844,700function 행을 유지했다. 선언된322문맥/1,013lanes 중 미실행317/998은 그대로다. 선택5문맥의 완료를 전체 cohort 완료로 바꾸지 않았다. 모든 selected/winner/confidence·확정 음악 해석·학습/Gold·생성·운영 승격 값은 None 또는 False다.

| 실제 r1 파일 | SHA256 |
|---|---|
| report.json | `f9d5f343fbba636ca2ee725ffe436cdf98dc8c62d2fa6734cc3b8ddd53e666cd` |
| run-plan.json | `95dd2ed7719820f0585ffdf361451503ca4cee5e790296c3f6dcf66d48ca5b07` |
| context-index.json | `4c74e0a8c63e925a1c2bb15fea67666258acbc6fa49f96573973a820d1bde8e0` |

보호 대상은4,529inputs와316current producer/schema이며 중복을 제외한union은4,531이다. 독립 metadata 감사는8출력의 정확한 목록/bytes/SHA, phase20 report/selection/panel과 inherited row 참조·분모의 보존을 확인했다. 원음표·tie·유리수 시간·동일 completion·기능 전제의 독립 finite 감사와 최종QA는 다음 절에 구별해서 기록한다.

### 6.4 분산 제시 의도를 확인하는 synthetic 양성 사례

이 항목은 corpus 음악 정답이 아닌 genuine fixture의 공개 prepared API 점검이다. G7→C 가정에서 B4/F4는 quarter0부터3까지 지속하고3에 C5/E4로 진행한다. Bass G3→C3, D4→G4는2에 변화한다. 따라서 cut2의 target에 E가 아직 없고, 완전한 C-E-G core는3–4에 제시된다.

Known C major 가정과 같은 실제 completion 아래에서 guarded pooled core·ordinary 연결·source/key/shape 조건이 joint conditional function 전제로 성립한다. Time presentation audit는 별도로 보존되며 이 success의 추가 gate나 cut2의 화성 시작 증명이 아니다. Cut에서 수직음집합이 완전해야 한다고 강제하지 않는다. 동시에 cut의 E 미관측 audit, 실제 B/F 지속과3의 새 attack, 원음가, 원 가정과 source guards는 남긴다. Unknown key counterpart는 같은 ordinary motion을 유지하지만 기능 좌표는 미정이다. 이 사례도 확정 화성/전위/국소 조성/Secondary/Cadence가 아니다.

### 6.5 실제 원음표에 연결된 양성·보류 사례

아래는 실제 r1 저장 자료에서 복구한 두 조건부 가정이다. 원주석을 정답으로 읽어 선택한 것이 아니며, 가정의 전제 통과를 실제 음악의 화성 시작·구조적 성부·종지 확정으로 해석하지 않는다. 음악명/마디 번호는 결과 설명이고 코드 조건이 아니다.

**Beethoven Sonata 01-1: 관측 cut의 불완전한 수직음과 뒤의 제시·지연 연결을 분리한다.** 저장 path index4 `fmpctxpath_22e4591ecd16d58d287e78ce`는 원 `fmpepath_5bce784c278ae7767cf4dfae`, partition `[49,101/2)→[101/2,61)`, key 가정 A♭ major `newkey_9cf83e185b3d35c9fdf68be8`, 실제 bundle `fmdobundle_3b710b74c6334fa5e02514af`를 그대로 사용한다. 가정은 G–B♭–D♭→A♭–C–E♭, explicit vii/M이며 이 key 아래 primary 좌표이다.

| 원 관찰 | sound / note ID | full sounding 범위 | 조건부 계산 |
|---|---|---|---|
| 13마디 B♭3, cut 전후 실제 최저음 | `sound_52e7b749f719` / `note_9737bdf159e9` | [49,53) | 앞 G diminished의3음이므로 관측 최저음 조건부1전위; 뒤 A♭ major에는 비구성음이므로 전위 null |
| 12–13마디 D♭5 tie, cut 직전 실제 최고음 | `sound_cae7b39ad108` / `note_2d60aad9c21b`, `note_b1e7cd2305c0` | [45,101/2) | 두 notated note와 tie `tie_8f5b04834d7b`를 보존 |
| 13마디 E♭5, cut에서 새 attack | `sound_d3f7db5b7806` / `note_da8356850f28` | [101/2,152/3) | 뒤 가정의 구성음, A♭ 가정의5음이며 실제 주요 melody 확정 아님 |
| G4→A♭4의 같은 raw lane 지연 연결 | `sound_c06632d0913f` / `note_409df3e18079` → `sound_7828a96022b7` / `note_f609dc1060e3` | [49,53)→[53,57) | 실제 route `fmdoroute_e5cd7f79bf239860f8264f97`의 required link가 같은 bundle 안에서 성립 |

Cut101/2(13마디 IR 기보 beat7/4)의 뒤 수직음에는 A♭와C가 아직 없고 B♭3도 지속한다. 이를 삭제하거나 member bass로 바꾸지 않는다. 뒤 후보의 완전하고 source-guarded한 literal core가 `[164/3,329/6)`, `[55,57)`에 제시되고, 같은 bundle의 G4→A♭4 ordinary 역할이 지원되므로 **joint conditional function 전제**는 True다. Boundary/time audit는 별도이며 이 True가 cut101/2를 실제 화성 시작으로 증명하지 않는다. 최상음 D♭5→E♭5의 별도 literal pair는 이 bundle에서 불충족이므로 위 이끎음 근거로 대신 쓰지 않는다.

Function context `fmpctxfunction_f00c6636717da16371718858`와 literal boundary `fmpctxboundary_a1cadf3a390e0e94edf6aafc`를 저장했다. 원 origin refs `fmehseg_8411ba3591f30f3ffc1b319f`/`fmehseg_de6d24beb6174187436341dc`는 boundary·factor에서도 같다. Function helper의 정규화된 source/target segment refs와 original origin refs는 다른 계약이며 서로 바꿔 저장하지 않았다. 이 vignette의 PAC/HC/IAC nominal은 모두False, confirmed도False이고 미확립 의미 전제7개는 유지한다.

**Mozart K280-1: 연결 하나가 맞아도 관측되지 않은 구성음을 채워 기능을 확정하지 않는다.** 저장 path index1 `fmpctxpath_5a7f8f20138f53a300bce1fa`, 원 `fmpepath_5e088ced4b960f1ced0ecceb`는 key 가정 F major `newkey_ee61e5eca9b24c1391c12286`, 실제 bundle `fmdobundle_5db28e235b14ff9b1d971631` 아래 C–E–G→F–A♭–C–E♭를 대조한다. Derived target triad는 F–A♭–C이고 실제 가정의7음E♭는 삭제하지 않는다. Target minor는 F major의 home quality와 다르므로 parallel 좌표를 보존하되 home cadence 조건은False다.

8마디 E5 `sound_4572034deed4`/`note_26d3d3f1cae2`는 `[45/2,47/2)`에 울려 cut23에서 같은 sound로 지속한다. F5 `sound_18baf37620b6`/`note_da443483ca5c`의 `[47/2,24)`로 향하는 실제 지연 route `fmdoroute_e3b38f3f79570277f02b82d6`는 같은 bundle에서 ordinary 역할을 지원한다. 앞 최저 C4 `sound_97e46ab03445`/`note_7958edb892e0`는 `[91/4,23)`에서 조건부 root position이다. 뒤 최저 A3 `sound_08b8c4c536a0`/`note_bdc610276abd`는 `[23,93/4)`이고 F minor7 가정의 비구성음이므로 inversion은null이다.

Function shape·explicit key·same bundle·ordinary 전제가 있어도 뒤 profile의 A♭/E♭가 source-guarded pooled core에서 미관측이다. 따라서 `guarded_pooled_literal_core_present=False`, `joint_conditional_functional_evidence=False`로 보류한다. Function context는 `fmpctxfunction_98cb8a710af3c38533ada5a2`, boundary는 `fmpctxboundary_051a4fe02886f78253e98f7c`다. Expected spelling으로 missing literal evidence를 채우지 않으며 이 보류도 음악 자체의 오류 판정이 아니다.

### 6.6 독립 감사와 최종 보호 확인

전체5문맥의 최종 읽기 전용 saved finite/source 감사도 **7.400초/147,454 assertions 및 유리수 대조/PASS**다. 이는 저장 유한 자료를 원IR·parent·실제bundle에서 독립 복원한 감사이며 fresh 공개 prepare/build 재실행이나 147,454개 신규 단위 검사·작품수·정답률이 아니다. Script의 초기 phase20 row digest 비교 대상/배열명 가정을 교정한 뒤 최종 실행했으며 제품/출력은 바꾸지 않았다.

원300selector의 path/key/partition/function bodies/account pointer·raw snapshot과875경계 관찰, 원음표·source refs·tie, before/at·attack·기보metric·최저/최고음, full release/horizon/beat-unit ratio·뒤의 attack/rest/active sound, 605same-bundle pair truth를 재계산했다. Distinct tuple×key×boundary200/literal15/probe43와function 형태1,250/전제평가275/motion25, key-known240/unknown60, joint8·inversion720·cadence2,625 및 universe/complement는 모두 일치했다.

Candidate factor/전위는 저장 helper를 호출하지 않고 exact step/alter membership·letter distance·given-root의 ordinary triad/seventh semitone template·source blockers·관측 최저음/동률 철자로 독립 계산했다. 음도는 explicit tonic과 major/natural-minor/harmonic-minor/melodic-minor-ascending offsets로 재계산했다. Joint는 원 function shape/ordinary query/key projection을 exact 대조하고, 원음에서 계산한 guarded pooled membership/최저음 guards를 포함한9전제의 three-valued conjunction과 비교했다. **이 감사는 phase20 ordinary role/kernel 자체를 재실행하지 않고 authentic saved parent body를 전제로 사용했다.** 실제r1의 parent authentic 재검증, 신규 public 검사, 이번 저장 감사의 범위를 구별한다.

Pair별 결과는 같은 sound carry110/실제 required-link 성립55/이 bundle에서 불충족440이다. 불충족을 전 가능한 성부의 부재로 확대하지 않는다. Tie 관련 extreme occurrence175를 full source chain과 대조했다. Cached terminal43개 중 boundary와 release가 다른 것은24, endpoint release10/beyond horizon1은 모두 following unknown을 보존했다. Nominal cadence 분포도§6.3과 같고 confirmed는 전부False다. 독립 문서·실제 두 사례 검수에서도 source note/pitch/time/같은bundle·cut와뒤core 차이·nominal 판정의 제한이 일치했다.

독립 metadata 감사와 별도로 root가 실제 creation SHA closure를 다시 전수 대조했다. Inputs/code/artifacts/report를 합친 고유4,539개에서 변경0, 정확8출력/5,610,484bytes, 현재316producer/schema, 신규4개·직전4개source/test의 동결SHA가 모두 일치했다. 이 root 검사2.951859초는 저장된 bytes/목록의 대조이며 fresh 공개 context 실행이나 음악적 정확도 평가가 아니다.

문서·코드7파일의 strict UTF-8/NUL/U+FFFD/줄끝공백, Python AST4개, 로컬파일링크124개를 검사해 오류0이었다. 최종 감사 기록을 반영한 뒤 동일 QA도 재확인했다. Read-only `git diff --check`도 exit0이며 commit/push/branch 또는 기존 dirty 파일 수정은 하지 않았다.

## 7. 다음 큰 단위와 한계

다음 큰 단위는 **여러 전환을 가진 완전 진행의 새 인증 lattice/공동 비교 계약**이다. 기존 full-hold/one-cut만으로는 `ii→V/V→V` 같은 세 화음 이상의 진행을 같은 전 성부 completion 아래 공동 설명할 수 없다. 먼저 현재의 key 후보와 unknown을 보존해 multi-slot 진행·모든 전환의 ordinary/조건부 역할 계정을 한 completion에서 대조한다. 구간별 기존 winner를 이어 붙이거나 서로 다른 completion의 해결을 합치지 않는다.

국소 조성 후보를 먼저 무작정 늘리면 ≤2slot 진행의 좌표 수만 커진다. 더 넓은 local-key evidence authority는 후속 독립 버전으로 설계하며 기존 tuple에 몰래 key를 추가하지 않는다. 위 내용은 다음 설계 계획이며 이번 구현/실행 범위가 아니다.

다음 구현의 최소 계약과 완료 조건은 다음과 같다.

1. `[cut_i,cut_j)`의 genuine 내부 공급 span도 가진 새 interval lattice를 만든다. 기존 prefix/suffix variant를 잘라 가짜 origin으로 만들지 않는다.
2. Segment 수별 exact DP로 논리 완전 partition을 count/index하고 필요시 명시된 complete selector만 복원한다. 모든 조합 객체의 무제한 materialization을 피하면서 미실행·unknown 분모를 유지한다.
3. 세 slot 이상에서 모든 경계의 ordinary/지연/조건부 음표 역할을 **하나의 실제 전 성부 completion**으로 공동 대조하고 전체 원음가의 union 계정을 유지한다. 개별 경계의 독립 witness를 합치지 않는다.
4. Phase21의 순수 boundary/음도/전위/release 전제 계산을 새 native reference 계약 아래 사용한다. 원phase20/21의 key/path/bundle을 확장한 것처럼 위장하지 않는다.
5. 전체 요청의 slot/selector/경계/의무/pair/work 한도를 먼저 확인해 whole hold하며, winner/confidence·확정 NCT/cadence로 승격하지 않는다.
6. 기존1·2slot 동등성, 두 경계를 넘는 tie/계류, 서로 충돌하는 해결 의무, 불필요한 split, key unknown, 같은 raw time 보존을 반례로 검증한다. 실제 pilot은 정답 라벨을 보지 않은 기존 여러 작품군의 multi-change 구간과 cohort controls로 고르고 특정 작품 정답을 조건식에 넣지 않는다.

전체 arbitrary 전곡 탐색·국소 조성 인증·family 음악적 정확도 평가·운영 UI 적용은 다음 계약을 구현했다고 자동 완료되지 않는다. 이후 넓은 key evidence, 여러 작품/편성 검수와 전체 악보 피드백으로 순차 연결한다.

많은 주석이 있다는 것과 모든 역할·성부·조성을 설명할 수 있다는 것은 다르다. 최종 cadence/Secondary/조성 판단 및 전체 악보 UI 연결은 별도의 검증과 적용 단계다. 이후 작곡·편곡은 조건부 화성·음표 역할·질감·배치 계획을 소비하고 결과를 동일 IR로 재검증해야 한다.
