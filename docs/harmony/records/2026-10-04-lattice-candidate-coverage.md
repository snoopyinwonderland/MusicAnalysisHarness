# 후보망과 보존된24진행 사이의 누락 원인

기록 ID: `HARM-DEV-20261004-48`

상태: **J1의 후보 누락 진단 완료**. 기존 후보망·탐색·선택 결과를 변경하지 않았다. 정답을 사용한 경로 존재 확인은 evaluator oracle이며 실제 추론·학습 성능 향상이 아니다.

## 1. 목적과 고정 범위

[첫 recall@24](2026-10-04-candidate-recall-and-first-selection.md)에서 확인된191개 후보 누락을 다음처럼 구분한다.

- 정답 진행이 원래 저장된 spelled 후보망에도 없는가?
- 원 후보망에는 있지만 구간 수 제한·prefix 보존·최종24path·계산 예산에서 사라졌는가?
- 앞 단계가 보류돼 후보망 자체를 검사할 수 없는가?

같은33악보·19작품군·322개 개발 train/dev 문맥을 전부 사용한다. Gold를 보고 새로운 화음·경계·음표를 생성하지 않는다. 미지원/부분 reference66개와 완전 평가256개 분모는 이전과 같다. 이번 단계는 새 코퍼스 정렬이나 DB 작업이 아니다.

## 2. 구현과 일반 규칙

추가: [harmony_lattice_recall.py](../../../src/musicanote_harness/harmony_lattice_recall.py), 버전 `harmony-lattice-recall-0.1.0` 및 [검사](../../../tests/test_harmony_lattice_recall.py).

1. 앞 단계 recall report와 저장 search/native context의 해시·sample·provenance를 연결한다. 모든 native reading이 semantic group의 origin으로 정확히 한 번 보존됐는지, 시간점/edge/철자/원 membership state/보류 이유가 동일한지 검사한다. 과거 parser나 후보 생성·공동 비교를 재실행하지 않는다.
2. 원주석에서 이미 평가용으로 투영한 **절대 근음+구성음 철자**가 해당 edge의 전 시간에 일치할 때만 reference-compatible edge로 인정한다. 같은 철자 집합의 반복 annotation cut은 필수 경계가 아니다. 전위·key/function만 다른 cut을 이번 축에서 경계로 세지 않는다.
3. DAG에서 각 시간점에 도달하는 최소 edge 수와 한 개의 결정론적 witness를 저장한다. 지수 개수의 모든 path를 열거하지 않는다. 최소 수가 기존 `max_segments=6` 이하면 원 탐색 범위에서 표현 가능하다. 무제한 구간 수에서만 가능한 경우를 별도 분류한다.
4. 시간 cell마다 서로 다른 path의 좋은 부분을 골라 연결 성공이라고 하지 않는다. 겹쳐서 전체 시간을 덮는 후보가 존재해도 실제로 이어지는 partition이 없으면 실패다.
5. Native lattice가 `baseline_not_ready`/예산 등으로 보류됐으면 `lattice_hit=null`이다. 그룹이 없다는 이유만으로 화음 어휘 부족이라고 단정하지 않는다. 초기 읽기 확인에서 이런 lattice에는 `plan` 자체가 없음을 확인해 별도 분기로 처리했다.
6. 모든 retained hit는 기존 구간 제한 아래 원 lattice witness가 있어야 한다. 이전 recall 평가를 재계산해 완전히 같음을 확인하고 과거 수치는 바꾸지 않는다.

**Oracle의 한계:** 이 진단은 근음·구성음·시간 표현 가능성이다. Group에 원 보류가 있어도 해당 철자·시간 의미를 대조할 수 있으며 보류를 해제하지 않는다. Witness 전체의 성부 연결/NCT/function 가정이 음악적으로 일관됨을 증명하거나 원주석이 유일한 타당한 분석임을 선언하지 않는다. Unspelled 후보는 숫자만 보존하며 임의의 철자/근음을 만들어 path에 넣지 않는다.

## 3. 실제 결과

정본: [report.json](../../../output/harmony-lattice-recall-2026-10-04-r1/report.json). 실제322개 전체 실행132.356초/exit0.

| 측정 | 결과 | 의미 |
|---|---:|---|
| 완전 reference 평가 | 256/322 | 부분/미지원66 유지 |
| Native 후보망도 검사 가능 | 241/256 | 후보망 보류15는 unknown |
| 원 후보망에6구간 이내 정답 진행 존재 | **132/256=51.56%** | 후보망 보류를 성공으로 세지 않은 확보 coverage; 실제 정확도 아님 |
| 검사 가능한 후보망에서의 포함률 | 132/241=54.77% | 위256분모와 구별 |
| 기존24path 안 정답 포함 | **65/256=25.39%** | 이전 수치 그대로 |
| 원 후보망에 있으나 보존 탐색에서 누락 | **67** | 가능한132 중50.76%; 최종24cap만의 원인으로 단정하지 않음 |
| 기존 실제 단순 선택 일치 | 5/256=1.95% | 이번에 새로 개선된 성능이 아님 |

이전191개 후보 누락의 분해:

| 원인 분류 | 문맥 수 | 후속 처리 |
|---|---:|---|
| 원 후보망에 있으나 보존/탐색 예산에서 누락 | 67 | 학습 점수로 원 lattice를 직접 decode; prefix/output/transition 손실 별도 점검 |
| 필요한 local spelled root+members 후보 부족 | 85 | 짧은 창·관측/생략·어휘·근음/철자 지원을 구분; 앞뒤 문맥을 이용한 일반 후보 생성 |
| Local 후보는 시간을 덮지만 이어지는 정답 partition 없음 | 22 | 후보가 제시되는 시간 범위와 hold/change 경쟁을 개선 |
| 최소 정답 partition이6segment 초과 | 2 | 문맥 길이·화성 변화에 맞춘 상태/구간 비용; 한도만 무조건 올리지 않음 |
| 후보망 자체가 보류 | 15 | 입력/시간 문제 또는 실제 예산 보류를 구분; 생성 실패와 섞지 않음 |
| 합계 | **191** | 이전176개 후보 불일치+15개 후보 없음과 일치 |

정답 존재/선택 실패60, 선택 성공5를 더하면 완전 평가256이다. 별도 `semantic_change_point_absent`는 이 고정 표본에서0개다. **경계 문제가 전혀 없다는 뜻은 아니다.** 위22개처럼 시간점은 있어도 해당 경계를 사용하는 화음 후보가 유효 범위에 없을 수 있다.

무제한 최소 witness의 segment 분포는1:53개,2:42개,3:29개,4:4개,5:2개,6:2개,7:1개,10:1개다. 마지막 두 개만6segment 제한 밖이다. 관측된 primary 분류의 우선순위는 원인은닉을 막기 위해 명시됐으며, 중복 원인 여부는 local coverage와 compatible edge coverage 등의 세부 필드를 함께 읽는다.

Split별로 train270 중 full205/lattice hit110/retained hit56, dev52 중 full51/lattice hit22/retained hit9다. Dev는 이미 개발에 노출된 자료로 독립 blind test가 아니다. 새 학습 허가·자격·완료 수로 이 숫자를 전환하지 않는다.

## 4. 실제 음악 사례

### 4.1 정답 진행은 있으나 보존 단계에서 사라짐

- `dcml:beethoven-quartets:n01op18-1_01`, sample `cont_195ab0306a75a682b13e`, `[2519/4,632)`.
- Reference-compatible 진행: `[2519/4,630)` F근음 `{A♭,C,F}` → `[630,632)` C근음 `{C,E,G}`.
- Witness `pgroup_10ae46d20fbbaaa1ea765f6d` → `pgroup_ddf91a71fec273102574eb0c`, 최소2segment/기존한도6, 두 group의 blockers는 빈 목록이다.
- 원 탐색은20,556전이, prefix 제외20,328개, 최종 출력 전36path/출력24path다. Prefix 제외와 최종cap이 모두 있어 어느 한 단계가 모든 정답 path를 제거했다고 이 ledger만으로 확정하지 않는다. 두 group을 합친 정답 진행이 최종 보존24에 없다는 사실은 확인했다.

이것은 새로운 화음 종류를 추가해야만 해결되는 문제가 아니다. 원 lattice를 학습 음악 점수로 직접 탐색하는 이유가 된다. F-minor→C-major를 이 작품용 룰로 넣지 않는다.

### 4.2 화음 후보의 범위가 맞지 않아 연결할 수 없음

- `dcml:beethoven-sonatas:01-2`, sample `cont_b9233d3cf382fd28cede`, `[573/4,1149/8)`.
- Reference는 `[573/4,287/2)` E근음 `{B♭,D♭,E,G}` → `[287/2,1149/8)` C근음 `{B♭,C,E,G}`다.
- Local matching candidate가 덮는 시간은3/8quarter 전체지만, edge 전 시간에 reference 의미가 일치하는 coverage는1/8quarter다. 시작점에서 다음 시간점으로 이어지는 정답 partition이 없다.

두 화음의 이름/구성음이 어딘가 존재한다는 것만으로 진행을 인식했다고 할 수 없다. 관측을 모으는 창과 화음 적용 범위를 구별하고, 짧은 구간 후보를 앞뒤 근거로 보완할 필요가 있다. Gold 경계를 생산 입력에 주입하는 방식은 사용하지 않는다.

### 4.3 짧은 관측 창에서 화음 근거가 부족한 표본

- [이전 사례 §4.2](2026-10-04-candidate-recall-and-first-selection.md#42-정답이-보존-후보에-없음)의 quartet sample `cont_23589950367f4bbba6b4`, `[1333/4,334)`.
- Reference는 C근음 `{C,E,G}`이나 원 spelled lattice에서도 matching time0/3/4quarter다. 따라서 이 표본은24path 보존만 고쳐서는 해결되지 않는다.
- 실제 native sound는 F3/F4→E3/E4→D3/D4이며 각 구간1/4quarter, 동음 중복도 보존돼 있다. 이 창 안에는 reference의 C/G가 관측되지 않는다.

이 관측은 짧은 표면 음집합만으로 유지 화음/비화성음 역할을 판단하는 한계의 사례다. Reference의 C-major 해석이 앞뒤 구간에 의해 지지되는지와 정렬/주석의 타당성도 검토해야 한다. 여기서 C/G 음표를 가상으로 추가하거나 곧바로 source가 틀렸다고 바꾸지 않는다.

### 4.4 고정 segment 한도 밖의 진행

- `dcml:chopin-mazurkas:BI105-4op30-4`, sample `cont_53478ca9c1f3ae54c982`, `[288,296)`.
- 원 후보망에는 F𝄪근음7화음과 D♯근음7화음이 반복되다가 구성음 변화 및 G♯근음7화음으로 이어지는 reference-compatible 진행이 있다. 최소10segment이며 기존6한도 밖이다.
- Witness의10개 원 group ID/시간/근음/구성음은 report와 native context에 보존했다. F𝄪를 G로 enharmonic 치환해 맞췄다고 하지 않는다.

이 사례는 동일 길이와 변화 횟수를 가정한 한도에 예외가 있다는 근거지만 전체 후보를 무제한 열거해야 한다는 뜻은 아니다. Segment cost와 화음/key 상태를 유지하는 직접 DP/beam 설계에서 해결한다.

## 5. 다음 개발: J2 공동 점수와 직접 decoding

후보망 진단이 큰 작업을 계속 미루는 새 infrastructure 단계가 되지 않도록 이번 분류를 마감한다. J0 재수집/재정렬로 돌아가지 않는다.

1. 기존 교재·NCT/관측/생략·전위·전이/해결 근거를 **점수 특징과 availability mask**로 연결한다. 상관된 membership/음가/관측 수를 독립 표처럼 중복 보상하지 않는다. 음악적 보류는 무조건 삭제할 이유가 아니다.
2. Root+members뿐 아니라 이후 RN의 key/function/inversion을 유지할 state 계약으로 확장한다. 같은 끝 시간/segment 수만으로 서로 다른 이전 화음을 압축해 전이 점수를 잃지 않는다. 기존24path 재순위화는 비교 arm으로만 유지한다.
3. 허가·자격이 확인된 train에서 규칙 가중치를 학습하고 dev에서 규제/길이 비용·탐색 폭을 조정한다. 기존 `automatic_training=false` 등을 자동 변경하지 않는다. 목표 진행이 원 후보망에 없는 경우를 모델 선택 실패로 위장하거나 gold boundary로 추론 후보를 보충하지 않는다.
4. 85개 후보 부족과22개 적용 범위 실패는 새로운 어휘만이 아니라 짧은 표면 창·생략/NCT/앞뒤 화음 유지 여부도 조사한다. 일반 문맥 확장/soft 후보로 고치되 원 음표/Core는 유지한다.
5. 같은256/322분모에서 후보 coverage·실제 선택·시간 일치와 비용을 함께 비교한다. 독립 test/전곡 RN·공개 모델 평가는 준비된 뒤 별도로 진행한다.

현재51.56%는 **표현 가능성 상계**다. 실제 선택은 여전히 이전5/256이며, 새로운 학습·추론 개선 수치 없이 상승했다고 말하지 않는다.

## 6. 검증·재현·보존

신규20개와 기존 recall14+search18을 합쳐 **52개 PASS/0.869초**. 신규 단독 실행20개를 다시 더하지 않는다. 실제 native 후보망 검증은322/322 완료했다. Synthetic physical gzip/JSON runner와 실제 corpus 저장자료를 구별한다. Unit test는 새 MusicXML parser 검사나 음악52곡 검수 수가 아니다.

검사: candidate origin 누락·의미 변경, 유리수 union, 최소 witness/순서 불변/비변경, enharmonic/root unknown, annotation의 같은-label cut, semantic boundary 누락, disconnected local coverage,6segment 제한, partial/unavailable/null, retained hit의 witness 필수, 이전 입력 SHA 변경 및 output 덮어쓰기 거부, oracle와 선택의 구별.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m unittest test_harmony_lattice_recall test_harmony_candidate_recall test_harmony_progression_search -v
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_lattice_recall --previous output/harmony-candidate-recall-2026-10-04-r1 --output output/harmony-lattice-recall-2026-10-04-r2 --expected-report-sha f12397eb53544dfa153974a9f0006f7cb06467d09c10ce1ecaf8da2e2d21f0eb
```

R1은 보존하며 재현은 없는r2 경로에서 실행한다.

- 부모 recall report SHA: `f12397eb53544dfa153974a9f0006f7cb06467d09c10ce1ecaf8da2e2d21f0eb`.
- 새 report SHA: `d2be3a53917c627c22c7e64b425dfdd462e94a1cfed3c42d8d0330dff6c05acc`,1파일988,872B.
- 새 실행 코드 SHA: `9f60de27f9889b6963d2fe10fb67187744d8bf3a431fe97e6cbba34737802754`.
- 실행에서714개 입력 SHA를 확인하고 종료 시 변경0을 검증했다. 이전 평가 코드와390입력, 추가 native context322, 부모 report를 포함한다.
- 원XML/IR/Core/주석·candidate inventory·search/proposals·기존 선택·기존 outputs·자격/권한·운영UI/서버/Git은 보존한다. 학습·승격·공개 모델 실행·commit/push0이다.

최종 QA: 신규2Python AST, 변경4문서 strict UTF-8/replacement0·trailing whitespace0, 로컬 링크264개/누락0을 확인했다. Report/code SHA 일치, 실제714입력 및 이전 단계45의3pin 불변,322/256/191 분모 분해, 메인 문서·로그·장기 계획의 신규 요약 각각1개를 검증했다. `git diff --check` exit0이며 기존 tracked5의 LF→CRLF 경고만 유지한다.
