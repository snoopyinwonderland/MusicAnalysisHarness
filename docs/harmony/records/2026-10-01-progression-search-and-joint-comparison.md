# 여러 화음 진행의 자동 제안 탐색과 동일 성부 가정 공동 비교

기록 ID: `HARM-DEV-20261001-01`

착수: 2026-09-30, 기록: 2026-10-01

상태: 연구용 구현·전체 고정 자료 실행·독립 대조 완료. 운영 뷰어·구조 분석에 승격하지 않았다.

## 목적과 이전 단계의 차이

사용자 방향은 “큰 것부터 처리하고 작은 것은 나중에 보완”이며 이번 요청은 “계속하죠”다. 특정 작품의 정답이나 새로운 음악 해석을 입력한 요청이 아니다.

직전 [공통 문맥 통합](2026-09-30-context-integration-and-measure-revision.md)은 같은 음표·시간에서 모든 후보, 조건부 NCT, 베이스, 미관측 구성음, 생략 가정과 원 관계를 연결했다. 그러나 실제 322개 문맥에 완전한 화음 진행을 자동으로 제안하지는 않았다.

이번 큰 기능은 아래 두 가지다.

1. 같은 문맥 전체를 덮는 **여러 화음 진행**을 자동 제안한다. 한 화음을 길게 유지하는 가설과 여러 화음으로 분할한 가설을 함께 남긴다.
2. 제안한 진행 전체를 **동일한 하나의 성부 연결 가정**에서 다시 평가하고 진행 간 차이를 계산한다. 서로 다른 성부 가정의 유리한 부분을 합치지 않는다.

최종 승자·로마자 기능·조성·cadence·신뢰도는 아직 선택하지 않는다. 이 단계는 단일 구간별 첫 후보를 이어 붙이는 방식에서 벗어나는 계산 기반이며, 완성된 자동 화성 분석기나 정답률 향상 선언이 아니다.

## 구현 파일과 계약

| 파일 | 역할 | 버전 |
|---|---|---|
| `src/musicanote_harness/harmony_progression_search.py` | 제한된 완전 진행 제안 탐색 | `harmony-progression-search-0.1.0` |
| `src/musicanote_harness/harmony_progression_joint_comparison.py` | 같은 assignment의 완전 진행 평가와 쌍별 비교 | `progression-joint-comparison-0.1.0` |
| `src/musicanote_harness/harmony_progression_search_trial.py` | 이전 고정 자료 전체 실행·정책·hash·분모 보호 | `harmony-progression-search-trial-0.1.0` |

각 모듈에 대응하는 `tests/test_harmony_progression_*.py` 3개를 추가했다. 기존 production parser, Core schema, source XML 및 원주석을 수정하지 않는다.

```text
기존 frozen context bundle
  → 다양한 완전 진행 제안 + 탐색 제외 기록
  → 각 진행 × 각 성부 가정의 정확한 전체 평가
  → 같은 성부 가정 안의 진행 쌍별 차이
  → 후속 조성·기능·경계 선택 단계 (아직 승자 없음)
```

API:

```python
search(bundle, max_segments=6, per_state_limit=6,
       max_complete_paths=24, transition_budget=200000)
compare(bundle, search_result, max_assignments=64,
        max_evaluations=4096, max_comparisons=8192)
```

## 탐색의 일반 규칙

### 같은 관찰과 모든 출처를 유지

기존 lattice의 exact interval edge와 철자가 있는 reading을 사용한다. 새 음높이·근음·비화성음을 발명하지 않는다. 철자 미정 후보는 별도로 보존하며 현재 path 계산 지원 부족을 기록한다.

같은 edge 안에서 근음 철자·근음 provenance·구성음·보류·event membership이 같은 reading은 계산용 semantic group으로 묶는다. provider·origin·원 reading key는 전부 남긴다. 계산 adapter reading 하나를 사용하지만 그 출처를 음악적으로 선호하거나 같은 증거를 여러 표로 세지 않는다. origin별 생략 가정과 경쟁 해석도 제거하지 않는다.

### 음표-시간과 낙관적 NCT 가능량은 별개

모든 시간은 정확한 rational quarter 좌표와 `[start,end)`다. `note_time`은 각 sounding event의 겹치는 시간을 모든 part에 걸쳐 합한 값이다. 실제 연주 시간이나 악곡 길이가 아니다.

탐색에 사용하는 값:

- 원시 비구성음 음표-시간: 현재 후보의 구성음으로 설명되지 않는 실제 음의 시간.
- 철자 미지원 음표-시간.
- 보류 후보에 노출된 음표-시간.
- 저장된 음형 규칙이 국소적으로 설명할 **가능성**이 있는 낙관적 NCT 음표-시간.

마지막 값은 완전한 진행이나 하나의 공통 assignment를 만족한 NCT 판정이 아니다. 서로 양립하지 않는 assignment의 가능성이 포함될 수 있으므로 탐색의 optimistic bound로만 사용한다. 같은 셀·같은 실제 음의 겹치는 시간은 합집합으로 계산해 중복 설명량을 늘리지 않는다. 원시 membership 순서와 bound 순서를 함께 남겨 optimistic bound 하나에 탐색이 종속되지 않도록 한다.

미관측 구성음 개수는 탐색 점수에 넣지 않는다. 분산형을 잘게 자르면 각 조각에서 관측된 음이 달라져 이 값이 과분할을 보상할 수 있기 때문이다. 실제 공동 비교의 origin별 진단에는 미관측 음과 생략 가정을 그대로 남긴다.

### 유지·분할 다양성과 탐색 제외

DP 상태는 `(끝 시간점, segment 수)`다. 원시 membership, optimistic NCT bound, 보류 노출의 세 retention lane을 사용한다. segment 수는 다양성을 유지하는 층이지 임의 가중치를 더한 경계 벌점이나 신뢰도가 아니다. 완전 진행 출력도 segment 수별로 돌아가며 선택한다.

prefix dominance와 state capacity로 제외한 것은 **근사 탐색의 누락**이다. 음악적으로 틀렸다는 판정이 아니다. 같은 prefix의 원시 목적 값이 더 좋아도 전후 기능·성부 맥락에서 음악적으로 더 좋은 진행을 놓칠 수 있다. 각 상태의 제외 수와 제한된 예시를 기록하고 예시를 전체 ledger로 가장하지 않는다.

segment 상한, transition 상한, 완전 진행 출력 상한, 철자 미지원 후보는 각각 기록한다. 정확한 전체 semantic/origin 경로 수와 실제 실행 전이·출력 진행 수를 구별한다. 저장 후보 어휘의 모든 경로 수조차 모든 가능한 음악 해석의 수는 아니다. JSON의 큰 정수는 Python의 exact integer이며, 추후 JavaScript 소비에서는 손실 없는 정수 계약이 필요하다.

작은 transition 예산이 문맥 끝까지 도달하기 전에 소진되면 `no_complete_path_proposal`을 남긴다. 부분 진행을 완전 진행으로 출력하거나 원래 긴 유지 가설을 평가했다고 주장하지 않는다.

## 공동 비교의 일반 규칙

모든 출력 진행 × 모든 저장 assignment를 계획한다. 하나의 평가에서는 전체 문맥의 시작부터 끝까지 연속한 진행과 단 하나의 assignment를 사용한다.

각 평가에 연결하는 것:

- 모든 원음의 원시 membership, 조건부 NCT, 보류 NCT, 미설명 비구성음, 철자 미지원 음가.
- 시간 셀별 실제 최저음, 조건부 전위와 비구성음 베이스의 경쟁 역할.
- 각 segment의 구성음 관측 시간, 미관측 음·생략 가정·모든 origin.
- 경계 양쪽의 구별 구성음, 지속음, 같은 구성음 집합, 경계 수와 시점.
- 같은 sampled assignment 아래의 목표 화음/이끎음/7음 해결 관계.
- 기존 explicit-IR voice 범위의 직접·시간 관계를 별도의 원근거로 연결.

저장된 explicit-IR 관계와 sampled assignment 관계를 하나의 성부 증명으로 합치지 않는다. 원주석의 key/label을 해결 계산에 전달하지 않는다. 미관측음을 생성하지 않고 생략 가정을 관측 사실로 바꾸지 않는다.

진행 쌍의 비교는 같은 assignment 안에서만 한다. 각 음가 bucket의 exact delta, 경계 증감, 같은 구성음 시간 흐름, membership 증가와 추가 경계를 함께 저장한다. 결과의 `preferred`, `selected`는 null이다.

**구성음의 시간 전체 합집합이 완전하다**는 것과 **분산화음으로 정확히 해석했다**는 것은 다르다. 또한 같은 구성음 집합이라도 근음·전위·기능이 다를 수 있다. 같은 구성음만으로 변화 또는 무변화를 확정하지 않는다. 경계를 늘려 구성음 일치가 증가한 것은 정확도 향상이 아니다.

### 비교 예산과 국소 보류

- assignment 또는 평가 개수 상한 초과: 해당 문맥의 전체 평가를 보류하고 inventory·계획을 유지한다. 일부 유리한 가정만 골라 평가하지 않는다.
- 쌍별 비교만 상한 초과: 모든 진행별 평가는 저장하고, 쌍별 비교 전체만 보류한다. 일부 유리한 진행 쌍을 출력하지 않는다.
- 기존 baseline/edge 보류: 기존 문맥과 상태를 유지하고 해당 제안·비교 단계를 보류한다.

한 문맥의 보류 때문에 322개 전체 분모를 줄이거나 다른 음악으로 바꾸지 않는다. source/성부/장식 미지원은 해당 판단의 한계로 남기며 다음 큰 기능을 무기한 중단하지 않는다.

## 계산 비용과 검증 중 보완

탐색의 고정 셀·음형 geometry, 목적 vector/rank 및 dominance 계산을 재사용한다. 공동 비교의 원 origin·미관측음·저장 관계·관측 베이스는 진행별 불변 근거로 재사용한다. assignment 의존 NCT와 해결은 매번 다시 계산한다. 캐시 결과는 deep copy로 분리하며 음악 규칙이나 예산을 완화하지 않았다.

가장 큰 실제 문맥 하나는 압축 해제한 JSON이 약513MB였다. 이 문맥의 9,218 reading에서24개 진행과198,136전이를 유지하면서 탐색 smoke 시간은51.56초에서35.40초로 줄었다. 단일 사례·부분 계산 측정이며 전체 엔진/화면 속도 향상이나 음악 정확도 향상이 아니다.

실행기의 preflight는 전체 입력을 검사하지만 key/row만 기억한다. 실계산 시 같은 파일/hash를 다시 확인해 한 문맥씩 처리하고 iteration 끝에 큰 객체를 해제한다. 322개 decoded bundle을 동시에 메모리에 올리는 방식은 사용하지 않는다. 원본 hash·정책·전체 분모 검사를 생략한 최적화가 아니다.

작성 중 runner의 search count 필드 연결과 mutation 검출 위치를 보완했다. Search가 입력을 바꾼 뒤 비교기의 hash 검사가 먼저 실패하던 경우를 runner의 즉시 mutation 검사로 구별한다. 거짓 정상 결과를 허용하는 규칙 변경은 아니다.

## 실제 고정 자료 실행과 검증

실행 정본 경로는 `output/harmony-progression-search-trial-2026-09-30-r1/`이다. 날짜가 넘어간 뒤에도 착수 시 정한 고정 output 이름을 유지했다. exit0이며 `complete`, `inputs_and_code_unchanged`, `artifacts_unchanged`가 모두 true다. runner 처리 시간은695.874초이며 입력 preflight를 포함한 전체 작업 시간이나 화면 성능은 아니다.

고정 범위는 직전과 같은19개 작품 가족/33개 악보·악장/322개 문맥이다. lattice ready291과 이전 끝단계 ready243은 다른 지표다. 322개를322곡이나322개 정답으로 해석하지 않는다. 정책은 원래 train27/dev6·internal research33이며 holdout 사용·권한 승격은 없다.

### 제안과 평가 결과

| 항목 | 실제 결과 | 의미 |
|---|---:|---|
| 고정 문맥 | 322 | 이전과 완전히 동일한 표본·분모 |
| 완전 진행을 제안한 문맥 | 291 | 나머지31은 baseline28/edge한도3의 기존 보류 |
| 실제 탐색 전이 | 1,800,273 | 후보 prefix 확장 instances. 독립 음악 판단 수 아님 |
| 출력 상한 전 완전 제안 | 6,377 | state retention 후의 계산 후보 |
| 출력 완전 진행 | 5,513 | 문맥 전체를 덮는 제안. 최적 진행/정답 아님 |
| 진행×assignment 평가 | 39,006 | 같은 성부 가정에서 음가와 조건부 근거 계산 |
| 동일 assignment 쌍별 비교 | 281,946 | 평가 refs와 exact delta. 승자 선택 없음 |

공동 비교 상태는 다음과 같다.

- 완전한 출력 진행 평가와 모든 쌍별 비교 완료:275문맥.
- 모든 진행별 평가 완료, 쌍별 비교만 예산 보류:8문맥.
- assignment 상한으로 해당 문맥 평가 전체 보류:8문맥.
- 기존 lattice 보류 그대로 유지:31문맥.
- evaluation 상한/transition 상한으로 새로 보류한 문맥은0이다. 원래의 relation 예산 보류48개는 삭제하거나 성공 상태로 덮지 않았다.

현재 semantic group은153,588개로 실제 stored reading 수와 같다. 이 자료에서는 묶음에 의한 개수 감소가 없었으며 그룹화 자체가 속도 향상의 원인이라고 주장하지 않는다. 모든 원 origin과 철자 미정111,904candidate refs가 보존된다.

탐색 제외는 prefix 근사286문맥, 출력 완전 진행 상한81문맥, segment 상한45문맥, 철자 미지원289문맥이다. 이 집계는 서로 겹치므로 더해서 보류 문맥 수로 만들지 않는다. 저장된 철자 어휘의 전 경로를 실제로 출력한 문맥은2개뿐이다. 그2개조차 전체 음악 해석에 대해 exhaustive라는 뜻은 아니다. 미출력 semantic path의 합계는71,604,933,290,722,367,514,148이며, DP로 계산한 경우의 수이지 그만큼 경로를 열거·검사한 수가 아니다.

### 실제 비교가 드러낸 차이

- 같은 구성음 흐름의1,385쌍에서는 원시 membership와 같은 assignment의 조건부 음가 차이가 모두0이었다. 단순 경계 삽입 때문에 설명량이 증가하지 않았다. 근음/기능/전위까지 같은 음악적 해석이라고 확정하는 검사는 아니다.
- 경계가 증가하면서 원시 구성음 일치도 증가한47,809쌍을 따로 표시했다. 이는 과분할 위험 검토 자료이지 잘못된 분할47,809개 또는 정확도 향상47,809개가 아니다.
- 낙관적 NCT 가능량이 양수인 평가4,433개, 실제 조건부 NCT 설명량이 양수인 평가513개였다. 낙관적 값보다 실제 설명량이 작은4,064개 평가를 확인했다. 실제 설명량이 낙관적 상한을 넘은 경우는0이다. 평가마다 path/assignment가 다르므로 고유 음형·작품·정답 수로 세지 않는다.
- sampled assignment의 해결 관계 instances는 형태 관계만4,374개, 문맥 보류740개, 직접 해결을 지지하는 조건부 가설20개였다. 마지막20개는 중복 path/assignment에서 생길 수 있으며 최종 secondary/조성/cadence 또는 화성 정답20개가 아니다. 별도 explicit-IR 관계 증명과 합쳐 강화하지 않았다.

### 재현 가능한 계산 사례

아래는 새 사용자 승인 사례가 아니라 실제 계산을 읽기 위한 예다. artifact의 `previous_context_artifact`/SHA에서 모든 기존 stage와 source/IR provenance에 접근한다. 문맥·원음 refs·모든 경쟁 후보는 부모 bundle에 있고 새 진행·assignment·평가 refs는 이번 artifact에 있다. 원 XML/IR을 편집하거나 특정 작품 조건식을 만들지 않았다. 좌표 `q`는 global quarter이며 마디 번호가 아니다.

1. **같은 구성음의 단순 분할:** `dcml:beethoven-quartets:n01op18-1_01`, `cont_e19939557bb600b9a92a`, q`[308,619/2)`; artifact `samples/620ee0a4825a194f681d.json.gz`. assignment `vpaths_4aa40384b2b0eec2238f`에서 `pprop_9bc7e2671fb0f8b392d2617b`와 `pprop_5c52eb25f6f95da25282ab60`을 비교한다. q309경계가 하나 추가돼도 모든 원시/조건부 bucket의 delta는0이다. 평가 refs는 `joint_1fc2e79913c4ae0b0644`, `joint_3f3acfb3b4844535e79d`다.
2. **분할의 구성음 증가가 승자는 아님:** 같은 artifact/assignment에서 `pprop_7631c0a56fb5f74620cdfc1f`→`pprop_5c52eb25f6f95da25282ab60`은 q309경계 추가와 함께 member 음표-시간이1quarter 증가한다. 미설명 비구성음은1quarter 줄지만 `preferred=null`이다. 다른 화음을 더 많이 배치하면 원음과 일치하기 쉬운 문제를 드러낼 뿐 올바른 경계라고 확정하지 않는다.
3. **NCT 잠재값을 면제로 쓰지 않는 반례:** `dcml:chopin-mazurkas:BI126-3op41-1`, `cont_bd93d59db6ff9fed0552`, q`[177,182)`; artifact `samples/02099c19d097bc193b29.json.gz`. `pprop_1cec3561037fd6d44187178f`/`vpaths_8766953b4bfa4c36cc16`/`joint_e380a3262112043f2a3b`의 optimistic potential은3/4quarter지만 실제 조건부 NCT는0, active pattern은없음, 미설명 비구성음은4quarter다. 음을 삭제하거나 가능량3/4을 실제 설명으로 빼지 않았다.

악보 화면에 이번 진행 제안을 올린 것은 아니다. 최종 기능·경계 선택과 독립 음악 검수를 거친 뒤 전체 악보 위에서 원주석/계산/경쟁 해석을 구별해 확인해야 한다.

### 코드 검사·불변성·독립 대조

- 신규51개 검사:search18/joint24/runner9. 최종 전체 Python2,343개/76.290초/OK. 기존 layout warning1건은 유지한다. 이전 병행 실행의2,343개/77.467초는 동결 전 검사이며 최종 수치와 구별한다.
- root runner 검사는 입력/정책/binding/분모/hash/덮어쓰기/잘못된 예산/입력 mutation을 포함한다. search/joint 검사는 경로 연속성·같은 구성음 분할·reading 순서·origin·공동 assignment·낙관적 bound·출처 혼합·예산/보류를 다룬다.
- 실행 계약의 입력 hash 항목1,209개, 현재 Python source260개, 신규 sample artifact322개의 변경0건. 입력 목록에 과거 코드/결과가 포함되어 현재 source 목록과 중복하므로 수를 더해 서로 다른 파일 수로 보고하지 않는다. contract SHA와 source 파일 목록도 검사한다.
- 독립 read-only 대조133.115초:모든322 identities·33packages·19families·정책·원분모·input/code/artifact/hash·전체origin·완전path universe의 독립DP계산 일치.5,513진행의 인접·전체범위·원음가,39,006평가의 원시/조건부음가·NCT조건,281,946동일assignment쌍의refs/exactdelta/예산·inventory를 대조해 불일치0이었다. 지정한 쇼팽 반례도 직접 확인했다.
- 최종 선택/확정 화성/신뢰도/accuracy/production/source-label 승격은 모두 없었다. `selected`, `preferred`는 null이다. 자기일관성·원음가 보존 검사를 독립 음악 정확도 검수로 바꾸지 않는다.
- source/test/개발 문서10파일의 replacement character·trailing whitespace와 로컬 문서 링크102개를 별도 검사해 문제0건이었다. `git diff --check`는 기존 tracked 변경에 대해 통과했으며 저장소의 CRLF 경고는 남는다. untracked 신규 파일도 위 별도 검사에 포함했다.

## 보존과 남은 큰 기능

원 XML/부모 IR/마디 revision/주석/rights/split/Gold/학습 자격/외부 전송/Git/production parser/Core schema/운영5173·기존8822화면/구조 분석을 변경하지 않았다. 자동 근음 생성·최종 local key·기능·cadence·confidence·전곡 최적 진행 선택도 하지 않았다.

다음 큰 단계는 제안과 공통 근거 위에 **조성·적용화음·기능·종지 및 경계 선택**을 연결하는 것이다. 탐색의 수치 순서를 곧바로 음악적 정답 순서로 올리지 않는다. 같은 원음/시간을 설명하는 경쟁 진행, 과병합/과분할, 전위와 기능만의 변화, 해결 지지, 설명되지 않는 음을 함께 대조한다. 이후 작품 가족별 독립 평가와 전체 악보 검토를 거쳐 운영에 승격한다.

## 재현

기존 output을 덮어쓰지 않으므로 재실행에는 새로운 output 경로를 사용한다.

```powershell
$env:PYTHONPATH = 'src;tests'
.venv/Scripts/python.exe -m musicanote_harness.harmony_progression_search_trial --previous output/harmony-context-integration-trial-2026-09-30-r1 --output output/harmony-progression-search-trial-2026-09-30-r1
.venv/Scripts/python.exe -m unittest test_harmony_progression_search test_harmony_progression_joint_comparison test_harmony_progression_search_trial
.venv/Scripts/python.exe -m unittest discover -s tests
```
