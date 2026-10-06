# 첫 후보 recall@24와 실제 선택 기준선

기록 ID: `HARM-DEV-20261004-47`

상태: **기존 저장 후보를 이용한 개발용 첫 측정 완료**. 새 점수 학습·독립 전곡 Roman 정확도·운영 뷰어 적용 완료가 아니다. 과거 검사 통과 수를 음악 정확도로 바꾸지 않는다.

## 1. 이번 요청과 실행 범위

사용자의 추가 검토를 반영했다.

- 이전 화면용 엔진은 이미 화음을 선택하며, 연구 엔진에도 경계×화음 공동 탐색이 있다. 실제 공백은 새 엔진의 음악적 점수·선택과 정확도 평가다.
- **J0 자료 정리는 첫 측정에 필요한 범위에서 최대30분**으로 제한했다. 이번 실행에서는 새 수집·전수 재정렬·DB·manifest 프레임워크를 만들지 않았다. 2026-09-30에 고정된33개 악보 package·19개 작품군·322개 문맥의 기존 manifest를 동결하고 첫 평가를 진행했다. 학습 자격 심사나 새로운 blind split 완성까지 J0 파일럿 완료로 주장하지 않는다.
- 정답이 **최대24개의 완전한 진행 후보** 안에 들어 있는지를 먼저 측정한다. 한 onset의 화음 이름24개 또는 모든 생성 가능한 path의 recall이 아니다.
- Melody 화음 파트는 분석에서는 weak/silver 자료지만, **해당 편곡을 재현하는 조건부 편곡 학습에서는 실제 기보가 target 정답**이다. 유일하게 가능한 편곡 또는 기능화성 정답이라는 뜻은 아니다. 아래 §7과 [작곡·편곡 기획](../MUSICAL_SEMANTICS_AND_GENERATION_ROADMAP.md#103-악보-형식이-아닌-변환-사례를-추출한다)에 반영했다.

평가를 위해 정답을 보고 후보를 새로 만들거나 좋은 구간만 다시 고르지 않았다. 기존322문맥을 전부 처리했다. 실제 실행은33.277초로 완료했고, 코드·검사·문서 작성 시간과 구분한다.

## 2. 구현과 지표 계약

추가 코드: [harmony_candidate_recall.py](../../../src/musicanote_harness/harmony_candidate_recall.py), 버전 `harmony-candidate-recall-0.1.0`.

### 2.1 정답 투영

기존 imported annotation JSONL의 DCML `globalkey`, `localkey`, `root`, `chord_tones`를 사용하여 **절대 근음 철자와 전체 화음 구성음 철자 집합**을 만든다. Relative fifths를 사용하므로 F♯와 G♭를 동일 철자로 뭉개지 않는다. Applied chord의 slash를 삭제해 다른 화음으로 비교하지 않는다. 원 Roman 라벨과 annotation ID는 그대로 보존한다.

원주석과 alignment의 대상이 동일하고 mapping이 `exact`/`verified_transform`일 때만 평가한다. 주석 공백·겹침·미검증 정렬·미지원 페달/근음과, 수정 IR에 대한 주석 binding을 검증하지 못한 경우는 별도 이유로 남긴다. 기존 IR을 고치거나 주석 범위를 새 IR에 임의 이식하지 않는다.

**측정한 것:** 유리수 시간 `[start,end)`의 근음·구성음 의미 일치. 서로 다른 라벨이 바뀌는 위치를 틀리면 시간 일치가 낮아진다. 같은 근음·구성음을 불필요하게 여러 번 나눈 경우는 이 지표에서 동일하다.

**아직 측정하지 않은 것:** 전위, 국소 조성, degree/function, 완전 Roman, NCT, cadence, 별도 경계 F1 및 독립 전곡 정확도. 예컨대 `V7/VI`의 구성음을 맞춘 것이 적용 대상까지 추론해 맞췄다는 뜻은 아니다.

### 2.2 첫 실제 선택 기준

저장된 원시 objective에서 아래 tuple이 가장 작은 path 하나를 선택한다.

```text
raw nonmember note-time / total note-time
→ blocked note-time / total note-time
→ spelling-unresolved note-time / total note-time
→ segment count
→ proposal ID (완전히 같은 점수의 결정론적 tie-break)
```

이는 **고정 규칙·미학습 기준선**이다. 어떤 특징을 먼저 보는지 명시했지만 교재 규칙 전체를 학습 점수로 결합한 decoder는 아니다. 낙관적 NCT 가능량을 확정 NCT 면제량으로 쓰지 않는다. Proposal ID는 음악적 증거가 아니며 의미 점수가 같은 경우의 재현용 순서다. `confidence=null`, `human_validated=false`를 유지한다.

선택 함수는 정답 인수를 받지 않는다. 실제 runner도 정답 파일을 읽기 전에 선택 결과를 만들며 evaluator의 gold가 선택에 도달하지 않는다. 선택 결과는 각 record의 `selected_prediction`에 범위·근음·구성음·semantic group ref로 저장한다. 생산 엔진의 현재 선택을 교체하지 않았다.

### 2.3 분모와 후보 상계

- 문맥의 전 시간이 평가 가능할 때만 전체 path의 `candidate_hit`과 `selected_hit`을 true/false로 판단한다. 부분 주석이면 null이다.
- 전 시간이 근음·구성음 기준으로 일치하는 후보가 하나라도 있으면 recall hit다.
- Oracle time agreement는 **보존된 완전 path 하나**의 최선 시간 일치다. 각 시간 cell에서 서로 다른 path를 골라 합친 상계가 아니다. Root oracle와 root+members oracle는 각각 다른 path일 수 있다.
- 후보0개인 평가 가능 문맥도 recall/선택 분모에 남긴다. 부분 평가 시간은 시간 지표에는 사용하고 전체 시간 대비 coverage를 함께 표시한다.
- 미리 노출된 train270/dev52문맥이며, 이 중 일부는 서로 겹친다. 322를322곡,33악장을33독립 작품 또는 누적 시간을 고유 전곡 시간으로 부르지 않는다.

## 3. 실제 첫 수치

정본: [실행 report.json](../../../output/harmony-candidate-recall-2026-10-04-r1/report.json).

| 측정 | 결과 | 정확한 분모/해석 |
|---|---:|---|
| 입력 | 33악보·19작품군·322문맥 | 기존 개발 snapshot 전부,5collection |
| 전체 문맥 평가 가능 | 256/322 | 나머지66은 부분/미지원 reference; 숨기지 않음 |
| 후보 recall@24 | **65/256 =25.39%** | 해당 문맥 전체의 근음+구성음 의미 정답 포함 |
| 첫 선택의 전체 문맥 일치 | **5/256 =1.95%** | 단순 미학습 tuple 기준선 |
| 정답 포함 문맥에서 올바른 선택 | 5/65 =7.69% | 후보 생성 ceiling과 선택 문제의 분리 진단 |
| 주석 평가 시간 coverage | 76.73% | eligible7895/8quarter ÷ 전체7717/6quarter; 겹친 시간 포함 |
| 선택 근음 시간 일치 | 21.70% | eligible시간 적분, 보류/후보 없음도0일치 |
| 선택 근음+구성음 시간 일치 | 2.84% | 전체 진행 일치와 다른 시간 지표 |
| 보존 path oracle 근음 시간 일치 | 45.04% | evaluator만 gold를 사용하는 진단 상계 |
| 보존 path oracle 근음+구성음 시간 일치 | 29.09% | 학습된 실제 성능이 아님 |

256개 완전 평가 문맥은 다음처럼 나뉜다.

| 오류/결과 | 문맥 수 |
|---|---:|
| 후보 안에 정답이 있고 선택도 맞음 | 5 |
| 후보 안에 정답이 있지만 선택 오류 | 60 |
| 보존된 후보는 있으나 정답 전체 진행이 없음 | 176 |
| 후보 자체가 없음 | 15 |

따라서 **정답을 선택할 수 없는191문맥**과 **선택기 개선 여지가 직접 확인된60문맥**을 구별한다. 176개가 원 lattice에도 전혀 없다는 뜻은 아니다. 생성 어휘·경계·retention/beam에서 어느 단계에 빠졌는지는 다음 진단이다.

전체322 중 보존 path0개31,1~23개170,24개121이다. 따라서 recall@24는 모든 구간에 정확히24개를 억지로 채운 결과가 아니다. Collection별 악보 수는 Beethoven quartets3, Beethoven sonatas5, Chopin mazurkas9, Corelli10, Mozart sonatas6이다. 이 다섯 collection을 전체17개 DCML collection이나 symphony 검증으로 일반화하지 않는다.

미지원 이유는 **시간 cell 발생 건수**로, 문맥 수와 중복 없는 음표/작품 수가 아니다: 페달 투영 미지원107, 수정 IR의 reference binding 미검증75, 정렬 미검증/불일치6, 근음 누락/모호1. 미지원 구간을 몰래 제외해 높은 정확도로 보고하지 않는다.

## 4. 실제 진단 사례와 판단

아래 measure/원 Roman은 imported source에서 읽은 표시다. 선택한 것은 아직 Roman이 아니라 절대 근음·구성음이다. 앞뒤 원악보를 새로 렌더링해 사람 검수를 완료한 사례로 주장하지 않는다. Report의 source artifact와 annotation ID로 원 문맥을 찾을 수 있다.

### 4.1 정답이 있으나 선택 오류 — 3화음과7화음

- Package: `dcml:beethoven-quartets:n01op18-1_01`, 원주석 m207.
- Sample `cont_3244c06fe647a34779cc`, `[2479/4,621)`.
- 원주석 `i.iv64`의 투영은 B♭ 근음과 `{B♭,D♭,F}`.
- 보존18후보 중 `pprop_e59cc1a1b72e4e7c88ba4f0f`가 전체 시간에 일치한다.
- 첫 선택은 `pprop_7f99b0b6970674171512d492`: B♭ 근음과 `{A,B♭,D♭,F}`. 근음 시간100%, 구성음 전체 일치0%다.

이 표본에서는 선택 결과가 주석보다 A음을 추가한 화음을 택했다. 전체 통계의 근음 대비 구성음 일치가 낮다는 점과 함께 **raw membership 최소화만으로 3/7화음 경쟁을 해결할 수 없다**는 반례다. 그 A음이 실제 NCT인지/다른 해석이 타당한지는 원음·성부/해결을 더 검토해야 하며, 이 측정만으로 주석이 항상 옳다고 확정하지 않는다.

### 4.2 정답이 보존 후보에 없음

- 같은 package의 원주석 m110, sample `cont_23589950367f4bbba6b4`, `[1333/4,334)`.
- 원주석 `I`의 투영은 C 근음과 `{C,E,G}`.
- 보존6후보에 이 전체 진행이 없고 oracle 근음 시간도0이다. 첫 선택은 D 근음의 `{A,C,D,F}`.

이것은 해당6후보를 잘 재순위화하는 것만으로 해결할 수 없다. 생성 어휘/시간창/beam retention을 분리 진단한다. C-major를 이 작품/마디에 하드코딩하지 않는다.

### 4.3 후보가 없는 구간

- Package `dcml:beethoven-sonatas:01-2`, 원주석 m1, sample `cont_958a865aa223ef4ce0ff`, `[2,7/2)`.
- 원주석은 `I(64)`→`I`; 투영은 F근음 아래 `{B♭,D,F}`→`{A,C,F}`다.
- 저장된 후보0, 선택null이다. `I(64)`를 일반 triad/inversion으로 억지 변환하지 않고 실제 source의 구성음 집합으로만 비교했다.

후보가 없는 문제와 후보는 있으나 선택한 문제를 섞지 않는다. 원 lattice 보류를 evaluator가 임의로 복구하거나 해당 구간을 성공으로 세지 않았다.

### 4.4 일치한 applied-chord 표본

- Package `dcml:chopin-mazurkas:BI105-3op30-3`, 원주석 m31, sample `cont_c14118599a2b6aea911c`, `[183/2,93)`.
- 원주석 `V7/VI`의 투영은 F근음과 `{A,C,E♭,F}`. 보존18후보 중 선택과 의미가 일치한다.

성공 표본도 하나 보존하지만, 이것을 Secondary function 추론 성공이나5개 성공이5독립 작품이라는 의미로 승격하지 않는다.

## 5. J0 마감과 다음 우선순위

**이번 첫 측정을 위한 J0는 범위를 동결하고 종료**한다. 기존 자격·노출 이력·source hash와 실패 이유를 report에 기록했다. 새로운 학습 manifest 및 독립 test 자격 확정은 학습/비교에 필요한 별도 잔여 항목이며, 이것을 이유로 첫 측정을 더 미루지 않았다.

다음은 J1의 큰 오류 구분을 끝내고 J2로 연결한다.

1. 같은 고정 개발 cohort에서 reference 진행이 **원 semantic lattice에 표현 가능한지**, 가능하지만24path에 보존되지 않은 것인지 구분한다. Gold는 evaluator 내부에서만 사용한다. Source key/reference 경계를 test 추론에 넣지 않는다.
2. 최소 같은 root/구성음 후보의3/7화음 과선택, 구성음 부족·장식음·전이/해결·분할 복잡도 특징을 실제 선택 점수에 연결한다. 낮은 성능 때문에 특정 작품의 정답을 조건식에 넣지 않는다.
3. 권한/자격이 확인된 DCML train에서 학습하고 dev에서 조정한다. 기존 `automatic_training=false`나 reserved/holdout을 자동 해제하지 않는다. 부분/미지원 레이블과 노출 이력도 보존한다.
4. 학습 점수로 lattice를 직접 decode하는 방식과24path 재순위화를 비교한다. Recall ceiling이 낮은 상태에서 재순위화 성능만 계속 개선하는 병목을 피한다.
5. 그 뒤 같은 전곡·split·label/time 계약의 독립 평가와 ChordGNN 비교를 진행한다. 현재 수치를 논문 CSR/RN 정확도와 같은 열로 비교하지 않는다.

새 규칙 전체·모든 코퍼스·모든 예외를 완성한 후에만 평가하는 순서로 돌아가지 않는다. 다음 업데이트에서도 동일 분모의 baseline/새 결과와 candidate ceiling을 함께 보고한다.

## 6. 검증·재현·보존

검사: 신규14개 모두 PASS. 기존 진행 탐색18개와 합쳐 **32개 PASS/0.728초**. 앞의 신규 단독 재실행14개를 다시 더해46개 검사로 세지 않는다. 최초 신규 검사에서1 FAIL은 test fixture의 adapter dict가 path와 semantic group에 공유되어 양쪽이 함께 바뀐 문제였다. Fixture를 deepcopy하여 참조 불일치 반례를 유효하게 만들었으며 validator gate는 약화하지 않았다.

검사 범위: 유리수/triplet, enharmonic 철자, 장단조/applied reference 투영, alignment/gap/overlap, 후보 없음/선택 실패, 경계 오차, reference 변경이 선택에 영향을 못 주는 것,24cap/partition/ref 검증, 부분 분모, physical gzip/JSON runner와 protected split/덮어쓰기 거부. Runner fixture는 수작업 synthetic ancestry이며 genuine MusicXML parser 검사로 주장하지 않는다. 실제322문맥은 기존 XML→IR 기반 저장자료이며 이번에 원XML을 다시 파싱하지 않았다.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m unittest test_harmony_candidate_recall test_harmony_progression_search -v
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_candidate_recall --previous output/harmony-progression-search-trial-2026-09-30-r1 --output output/harmony-candidate-recall-2026-10-04-r2 --expected-report-sha 72bf22df45a5b485f7ed44715bbb7994013a1098981e2cd08d879b3a0b9a2ec8
```

이미 생성된r1을 덮어쓰지 않는다. 위 재현 명령은 새r2 경로가 없을 때 사용한다.

- Frozen proposal report SHA: `72bf22df45a5b485f7ed44715bbb7994013a1098981e2cd08d879b3a0b9a2ec8`.
- 새 실행 report SHA: `f12397eb53544dfa153974a9f0006f7cb06467d09c10ce1ecaf8da2e2d21f0eb`.
- 평가/선택기 코드 SHA: `9ce241b559be08de3cf2d84cb1eb4082d50b332c31504e1d60744fb5a8a92740`.
- 실제390개 입력 파일의 SHA를 기록하고 종료 시 변경0을 확인했다. 새report1파일1,822,835B다. Report에는33개의 원 manifest와322개의 prediction/evaluation/reference records가 있다.
- 입력 추론은 source labels 미사용; evaluator는 주석 사용. Train/dev의 사후 진단이며 blind test가 아니다.
- 원 XML/Core/주석, 기존 후보/outputs, 기존 eligibility, 생산 분석/UI/서버·Git 설정은 변경하지 않았다. 가중치 학습·공개 모델 설치/실행·commit/push0이다.

최종 QA: 신규2Python AST, 변경6문서 strict UTF-8/replacement0, 로컬 링크287개/누락0, 작성 파일의 trailing whitespace0, 실제390입력 및 이전 단계45의3개pin 불변, 코드/report SHA 일치를 확인했다. 다중 문서 패치의 부분 반영과 README 요약 중복을 확인해 교정한 뒤 현재 요약은 각각1개임을 검사했다. `git diff --check` exit0이며 이전 tracked5의 LF→CRLF 경고만 유지한다.

## 7. 편곡 target과 분석 gold의 구별

동일 원자료에 task별 자격을 갖는다. 예를 들어 Melody 악보의 P2 화음 음표는:

- **편곡 재현/조건부 편곡 학습:** 대상 판본에서 만들어야 하는 pitch/onset/duration/tie/part 등의 기보 target이다. 정렬된 원선율·요청/편성에 대한 한 개의 실현 정답으로 보존한다.
- **화성 분석:** 위 음표에서 추정한 Roman/function/key/boundary는 weak/silver supervision이다. 기보가 있다는 이유만으로 검수된 기능화성 주석으로 바꾸지 않는다.

이 구별은 source의 품질·정렬·사용 권한·작품 가족 split을 생략하는 허가가 아니다. 편곡 target이 있어도 역할·질감·스타일 의도 또는 유일한 좋은 편곡은 자동으로 정답이 되지 않는다. 이 실행은 팝 편곡 학습을 새로 수행하지 않았다.
