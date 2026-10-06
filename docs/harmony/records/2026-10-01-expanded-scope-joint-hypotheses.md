# 새 문맥 범위의 화음·조성·성부 공동 가정

개발 항목: **HARM-DEV-20261001-12**. [메인 화성 개발 문서](../README.md)와 [직전 전후 관측·종지 전제 기록](2026-10-01-context-and-cadence-prerequisites.md)을 잇는다.

## 목적과 범위

직전 단계는 앞뒤 마디의 실제 음을 별도 관측으로 저장했다. 이번에는 그 envelope를 **새로 명시한 분석 범위**로 만들고, 그 범위에서 화음 후보·조성 가정·성부 연결 가정을 새로 계산한다. 원 분석 구간의 화음을 앞뒤 음으로 소급 정당화하거나 원 path/completion을 즉석 확장하지 않는다.

새 모듈을 동결하고 전체 회귀·고정 문맥 r1·두 독립 저장 감사와 대표 공개 fresh replay를 완료했다. 연구용 후보 비교와 음악적 정확도·운영 화면 적용·생성 승인은 별개다.

## 계약 분리

```text
동일한 full IR + 기존 frozen view/observation/audit + fmctx
  ├─ 과거 path/key/성부 bundle/종지 전제 — 그대로 보존
  └─ fmes: 새 analysis_span와 원 anchor_span
       ├─ 새 물리 범위의 정확한 source projection/lineage
       ├─ 새 범위의 모든 raw lane factor graph
       └─ 새 화음 path/조성 가정/공동 completion과 비교
```

기존 `fmview`는 `mfco`와 동결 selector의 실제 provenance를 요구한다. 새 범위의 관측을 그 ID로 다시 봉인하면 provenance를 위조하게 된다. 따라서 기존 모듈·schema를 수정하지 않고 별도 `fmes`와 새 해석 record namespace를 사용한다. 하위의 exact literal projection·lineage·geometry와 공통 화음 공급기를 재사용한다.

## 일반 규칙

### 1. 새 범위와 관찰

- 새 `analysis_span`은 검증된 `fmctx.envelope_span`과 같다. 원 context/target은 anchor와 원 참조로 별도 보존한다.
- 표기 번호가 아니라 물리 마디 clock으로 정한 기존 envelope를 사용한다. 모든 시간은 quarter 유리수, 범위는 `[start,end)`다.
- 전체 IR에서 음표·쉼표·source·타이·attack·철자와 원 full span/새 observed clip을 다시 추출한다. metadata-only 밖의 이웃을 분석 음으로 승격하지 않는다.
- 새 범위의 모든 raw lane에 새 factor graph를 만든다. 이전 그래프를 ID만 바꾸어 재사용하지 않는다. point/grace/모호한 owner/clock·pitch 불일치는 보류 이유로 남긴다.
- malformed sound span 때문에 literal projection과 graph inventory가 다르면 불일치를 그대로 드러낸다. 음표를 삭제하거나 graph에서 음을 가져와 원 source를 수선하지 않는다.

### 2. 후보와 조성

- 확장 범위의 attack/release cut을 관측하고, 전체 hold 및 각 cut의 완전한 두 구간 path vocabulary를 만든다. 이것은 전곡의 모든 길이·분할을 포괄한다는 주장이 아니다.
- 필요한 후보 공급 범위는 전체 span 및 모든 cut의 앞/뒤 span이다. 후보 공급기의 원 root·spelling alternatives·blocked/unknown/unspelled origins를 보존한다. 동음이명 철자를 MIDI로 합치지 않는다.
- 공급기 gate가 통과해도 화음 정답이나 100% vocabulary coverage가 아니다. 과도한 병합과 분할은 같은 범위의 경쟁 가정으로 남는다.
- 조표와 조성 해석을 구별한다. 물리 범위의 조표가 일관되고 완전할 때 major와 세 minor reference form 및 unknown을 경쟁 가정으로 둔다. mode hint를 조성 정답으로 사용하지 않는다. 변화/모호성/누락은 unknown으로 보류하며 변조가 없다고 단정하지 않는다.
- 예산 초과 시 일부 좋은 후보만 고르지 않는다. 전체 group의 계획 수와 원 공급 자료·보류 이유를 남긴다. 공급 자체가 미계산이면 path 수는 0이 아닌 unknown으로 표현한다.

### 3. 같은 성부 가정 아래의 비교

- raw 철자 membership/비구성음/미정 음가와 빠진 구성음을 분리한다. 비구성음 관측은 확정 NCT가 아니다.
- 최저음의 `conditional_bass_member_indices`는 일반 구성음 위치다. 실제로 철자·근음부터 검증한 완전한 보통 3/7화음 template만 `conditional_inversions`로 표현한다. 임의의 추가음·quartal·cluster 구성음 배열을 고전 화음의 전위로 부르지 않는다.
- 완전한 모든 lane의 하나의 completion을 각 경쟁 path/key에 공통 적용한다. 유리한 성부 연결을 다른 completion에서 하나씩 가져와 합치지 않는다.
- no-link baseline은 control이다. 음악적인 최선의 성부나 해결 부재 증명이 아니다.
- 이끎음과 7음의 실제 endpoint 진행은 필요한 link들을 공동 질의한다. 성부 내 injectivity/무연결 대안을 유지하며 불충족은 그 명시 가정 아래의 결과다.
- 각 edge의 원음은 자기 source-clock·철자·attack 참조 검사를 통과해야 한다. 다른 lane의 정상적인 같은 음이 잘못된 source를 대신 승인하지 않는다. 경계의 bass/core 검사와 개별 edge 검사 모두 필요하다.
- 구조 베이스·주선율·박절·협화·프레이즈 종결·국소 조성이 확정되지 않았으면 종지는 미확정이다. delayed resolution/NCT도 지원 전제 없이 강제 해석하지 않는다.

### 4. 비교 범위와 예산의 의미

공동 bundle의 실제 `assignment.links`를 모든 path/key에 적용한다. 현재 witness 생성은 필요한 연결만 materialize하며 나머지는 모두 무연결이다. 따라서 이 비교는 모든 가능한 성부 편성의 전수 열거나 성부 정답 선택이 아니다. 관측상의 동시음·구성음 profile은 segment별로 공유하고, 실제로 같은 완전한 bundle에 들어 있는 연결을 근거로 조건부 충족 여부를 저장한다.

기본 한도는 lane당 `max_events=4096`, `max_factors=4096`, `max_edges=65536`, 전체 공급 span `max_catalogs=128`, partition당 `path_budget=128`, group당 `pair_budget=4096`, 기능 형태 `overlay_pair_budget=65536`, 직접 endpoint/공동 조합 `max_motion_pairs=65536`이다. `pair_budget`은 path×key 및 공유 bundle×path×key의 계획량에 적용하는 한도이며, 두 path의 차이를 직접 계산한 쌍 비교 수가 아니다. 예산을 넘긴 전체 group은 보류한다. 미계산 supplier 자료·후보/variant 수와 그에 따른 path 수는 null이며, 계획한 span은 유지한다. 저장된 catalog span 수와 실제 supplier 계산 수를 구별한다.

## 구현과 저장

- `src/musicanote_harness/factor_expanded_scope.py`: 새 범위·literal·source guard와 모든 lane geometry.
- `src/musicanote_harness/factor_expanded_hypotheses.py`: 새 화음·조성 가정과 동일 completion의 조건부 비교.
- `src/musicanote_harness/factor_expanded_trial.py`: 완료된 직전 산출물 보호, append-only 실행·오류/보류/분모·SHA·코드 inventory 기록.
- 대응 tests는 변경·재봉인·foreign parents·source clock·half-open·tie·point/grace·동률·전체 예산·부모 보존·미승격을 검사한다.

원 XML/IR/revision/주석/old analyses·사용 정책·운영 parser/뷰어·구조 분석은 바꾸지 않는다. 학습/Gold/생성 승격, 최종 화음/종지 선택, 외부 API 전송, Git commit/push는 하지 않는다. 예산은 선택적 계산 materialization 기준이며 byte/RSS 상한이 아니다.

### 재실행과 계약 검사

```powershell
$env:PYTHONPATH = 'K:/Music Analysis/src;K:/Music Analysis/tests'
$env:PYTHONIOENCODING = 'utf-8'
& 'K:/Music Analysis/.venv/Scripts/python.exe' -m musicanote_harness.factor_expanded_trial --prerequisites 'K:/Music Analysis/output/factor-context-prerequisites-2026-10-01-r1' --output 'K:/Music Analysis/output/factor-expanded-joint-2026-10-01-r1'
```

산출물이 존재하면 실행기는 거부한다. 재실험은 존재하지 않는 새 output 이름을 사용한다. `prepare_scope`/`validate_scope`는 full IR과 모든 부모를 fresh replay한다. `check_scope(ir=...)`만으로 과거 부모 artifact의 권위가 확인되는 것은 아니다. `build_hypotheses`/`evaluate_hypotheses`와 각각의 validator는 동일 scope와 코드·schema fingerprint를 요구한다. 실행기는 부모 SHA/정확 파일 목록/선택한 원 group·lane·미실행 분모를 보호한다. 도중 평가가 실패해도 완료된 새 scope·후보와 과거 group은 저장하며 실패를 성공으로 세지 않는다.

## 검증·실제 실행·실패와 보완

### 구현 검사와 발견한 문제

- 신규 범위 34개/6.446초, 후보·평가 35개(최종 source에서 전체 33개/44.787초 및 추가 전위 2개/0.772초, attack masking 재검사 1개/9.147초), 실행기 11개/57.813초를 확인했다. 인접 129개/20.208초도 통과했다. 테스트 순서 보완 뒤 **전체 Python 3,103개/539.439초 OK**, 신규 80개를 포함한다. 작품 수·음악적 정답 수가 아니다.
- 독립 코드 감사에서 attack 참조가 잘못된 이끎음/7음이 정상적인 같은 음의 doubling에 가려 해결 edge로 쓰일 수 있는 누락을 찾았다. 자기 source guard를 통과해야 qualify하도록 하고, 잘못된 source는 raw profile과 blocker에 보존한다. 실제 건강한 doubling이 있는 반례도 검사했다.
- 공급기 members 배열의 인덱스를 추가음·비3도구성 화음의 고전적 전위처럼 표현하던 의미 문제를 수정했다. 일반 bass member index는 유지하고, 철자·근음·순서가 검증된 보통 3/7화음만 전위로 표기한다. C9와 add6/quartal/무순서 배열 반례를 추가했다.
- 첫 전체 회귀 3,103개/555.742초는 기존 `test_owned_compilation_seal_is_exact_and_has_no_caller_aliases`의 IndexError 1개로 실패했다. function ID의 digest 정렬은 관측 snapshot의 존재 순서가 아니다. source가 미관측인 관측은 빈 snapshot을 가질 수 있다. 테스트만 실제 snapshot을 전체 관측에서 찾고 존재를 확인한 뒤 변형하게 보완했다. 원 봉인·caller alias 없음·입력 불변·fresh 결과 일치 검사는 유지했다. 분석 source는 수정하지 않았다. 독립 resolution 42개/9.242초와 해당 검사 12개의 새 임시 identity 반복/2.946초를 통과했다.

### 고정 자료 r1 — 계산 완료와 실질 범위

`output/factor-expanded-joint-2026-10-01-r1`은 exit 0/758.445261초, 계산 오류 0으로 완료했다. 전체 회귀와 병행한 단일 wall-clock 계측이며 이전 단계와의 성능 비교 수치가 아니다. 원 5문맥/15raw lane/16group과 모든 기존 상태·보류를 유지했다. 모든 새 scope의 source inventory와 15개 새 graph가 준비되었으며 source guard 보류/미투영 sound는 0이다. 이는 음악적 해석 승인이나 정확도 검사 통과가 아니다.

| 자료군·악장 | 새 범위(quarter) | slots/sounds | 공급 span/후보 variants | 계획 group/한도 보류 | 실제 path/path×key rows |
|---|---|---|---|---|---|
| Beethoven quartet n01op18-1_04 | `[262,270)` | 57/53 | 31/2,308 | 16/15 | 116/580 |
| Beethoven sonata 01-1 | `[49,61)` | 26/23 | 31/3,139 | 16/16 | 0/0 |
| Chopin BI105-2op30-2 | `[10,22)` | 43/42 | 35/3,840 | 18/18 | 0/0 |
| Corelli op01n01a | `[32,44)` | 84/81 | 65/7,789 | 33/32 | 0/0 |
| Mozart K280-1 | `[18,27)` | 48/40 | 59/5,893 | 30/29 | 116/580 |

합계 notated slots 258/sounds 239, 공급 span 221개 모두 계산/variants 22,969개, 관측 cut 108개에서 계획 group 113개를 저장했다. 계획 path는 1,068,810개, 실제 materialize는 232개다. 110group은 전체 path 한도 보류이며, 준비 상태 3group 중 Corelli의 한 group은 완전 path 수 0으로 **계산상 빈 group**이다. 나머지 실제 비교는 두 full-hold group의 1,160 path×key rows/11,600 기능 형태 검사뿐이다. 각 범위의 조표 가정 5개(unknown 포함)를 보존하며 다섯 no-link all-lane bundle을 사용했다. 공동 직접 해결 shape는 0이며 최종 화음·종지·NCT·key 선택은 없다.

원 공급 종류는 base 16,196/additional-seventh 406/extended 6,303/augmented 64이며, 철자가 미정인 6,983 variants도 삭제하지 않았다. 직접 해결 0은 **실제 변화 진행의 미평가**다. 평가된 양수 path가 모두 full-hold이므로 다음 target segment가 없으며, 11,600 기능/움직임 형태가 보류된다. 새로운 분할 진행의 해결이 없다는 음악적 부정 증거가 아니다.

**모든 분할 진행을 분석한 결과가 아니다.** 원 short-window의 실제 해결이나 종지 전제 수를 새 해결 양성 수로 합산하지 않는다. 원 cohort 322문맥/1,013lane 중 미실행 317/998와 대기 작품군을 그대로 유지한다. 이 실행은 다섯 자료군의 다섯 문맥이지 전곡 다섯 작품 평가·정답률·holdout 검증이 아니다.

입력 4,428개/current source·schema 300개, 생성 artifacts 17개+report=18파일의 생성 시점 SHA와 정확 목록에서 변경 0이다. report SHA256: `e020fcecd301d461379558c0fa905f8a15219a6069f38f2a097d9294b70ae1fa`. 테스트 보완 파일은 실제 실행의 inputs/code 목록에 없고 분석 source 3개는 동결 후 불변이다. 이 세부 사항은 실행 중 변화와 strict run integrity를 혼동하지 않기 위해 기록한다.

### 독립 저장 감사

첫 독립 SHA/inventory 대조에서 보호 inputs 4,428/current code·schema 300, artifacts 17+report=18파일/18,902,732bytes가 모두 일치했다. 모든 239 positive source facts·15 ready graph와 source/geometry/미투영 보류 0, 원 5/15/16과 113 새 group 분모를 확인했다. 모든 다섯 scope의 full IR과 원 view/observation/audit/fmctx를 사용하는 공개 `validate_scope` fresh replay도 통과했다. sound/source-note/source-ref/철자/full span/새 clip/attack guard가 일치했고, 타이 4sound의 원 attack/source chain과 범위 밖 linked-context-only literal slots 2개도 보존했다. 원 anchor를 넘어서는 205sound의 full extent를 새 창에 추가했지만 원 창의 데이터는 바꾸지 않았다.

실제 source 대조에서 Beethoven A♭3 `[53,57)`→D♭4 `[57,59)`와 A♭4→F4의 후속음은 원 anchor overlap이 없음을 확인했다. Chopin A4 `[14,15)`도 원 anchor `[15,17)`와 overlap이 없다. Mozart F5 `[43/2,45/2)`와 E5 `[45/2,47/2)`는 이미 원 anchor에 겹친 음이다. 새 문맥의 출처 관측을 예전 해결이나 새 독립 해결 양성으로 합산하지 않는다. 원 packet/IR/fmctx digest와 report SHA도 재감사 후 불변이다.

다른 독립 evaluator 감사 28.504초에서 전체 221 supplier의 22,969 origin/spelling alternatives(미정 6,983 포함), 관측 cuts·공급 span·모든 partition/path 계획 곱, 232 실제 path와 25 scope별 key 가정, 모든 다섯 all-lane witness의 실제 연결, 전체 1,160 same-bundle incidence 및 raw note-time 합계를 대조했다. 모든 비교가 같은 bundle/key universe를 사용하고 비보통 화음이 conventional inversion으로 표시되지 않으며 source/학습/Gold/생성 flags 미승격임을 확인했다. 저장 검사는 음악적 정답 검수가 아니다.

대표 Mozart K280-1 context 68의 공개 fresh replay도 통과했다. loader 39.236초, `validate_scope`/full-parent `prepare_scope` 8.627초, `validate_hypotheses`/fresh builder 61.889초, `validate_evaluation`/fresh builder+evaluator 70.886초, 전체 191.353초다. 원 한도를 바꾸지 않고 59 supplier spans/5,893 variants/29cuts/30groups/116 full-hold paths/5keys/580 comparisons/5,800보류 기능 형태와 29분할 group의 전체 보류가 정확히 재현되었다. caller·저장 입력은 불변이다. 재현성과 미승격을 확인한 것이며 해당 모차르트 구간의 화성 정답을 사람이 승인한 검사가 아니다.

관련 11개 파일(새 source/test 6개·기존 test 보완 1개·문서 4개)의 strict UTF-8·NUL/U+FFFD·줄 끝 공백과 네 문서의 상대 링크를 최종 검사했다. read-only `git diff --check` 오류 0이고, 기존 별개 tracked 파일의 LF→CRLF 안내는 수정하지 않았다. untracked 파일은 별도 문자/공백 검사로 확인한다.

## 다음 큰 단계

확장 범위의 Cartesian path materialization이 먼저 해결할 큰 병목으로 확인되었다. 후보를 top-k로 솎거나 예산만 무작정 올리지 않고, 같은 모든 후보/분할의 profile·형태·성부 제약을 공유형/인덱스형으로 계산하는 후속 설계를 먼저 진행한다. 전체 분모·blocked/unknown·무연결·양립하지 않는 joint 대안은 계속 보존해야 한다. 이후 실제 분할 진행에서 미설명 음가·구성음의 시간순 배치·직접/지연 해결·장식/지속 경쟁 설명을 통합하고, 검증 가능한 결과를 전체 악보 화면의 실험 레이어로 연결한다. 특정 작품의 정답이나 한 사례의 숫자를 조건문에 넣지 않는다. 생성 단계는 역할·질감·배치 계층과 계속 분리해 관리한다.
