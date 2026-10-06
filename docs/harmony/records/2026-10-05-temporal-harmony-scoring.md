# HARM-DEV-20261005-63 — 과분할·과병합의 시간 근거 점수 대조

## 1. 목적과 적용 범위

[단계62](2026-10-05-streaming-joint-selection.md)의 장문 계산 보류 뒤, 저장·checkpoint 작업을 더 늘리지 않고 **실제 화음을 잘못 고르는 큰 원인**으로 돌아왔다. 화음 이름과 경계는 여전히 같은 후보 DAG에서 함께 선택한다. 경계를 먼저 확정하지 않으며, 주석에 맞는 후보를 사후 삽입하지 않는다.

새 연구용 점수 모듈과 네 조건의 비교 실행기를 추가했다. **결합 조건의 시간·경계 지표는 개선됐지만 완전 일치는 15/51로 같고 세 구간의 시간 일치가 퇴행하여 운영 승격은 보류했다.** 기존 봉인 엔진·보고서·production 화면·서버·MusicSearch·Composition·Claude Motif·원 XML·Canonical Core·주석·권한은 변경하지 않는다. 현재 연구 결과를 운영 화성 분석이나 종지·프레이즈 판단으로 자동 승격하지 않는다.

원래 노출된 개발 자료에서의 비교다. 예측을 전부 봉인한 다음 주석을 여는 것은 이번 계산의 라벨 유입을 막는 절차이며, 과거 결과 노출을 지우거나 독립 blind test를 만드는 절차는 아니다. 전위·Roman·국소 조성·NCT·종지 전체 정확도는 이 실험의 평가 대상이 아니다.

## 2. 두 오류의 다른 원인

### 2.1 짧은 움직임을 독립 화음으로 과분할

Beethoven quartet의 기존 `[167/2,175/2)` 선택은 13개 raw edge / 11개 harmonic run이었다. 여러 짧은 선행음→해결음 연결도 독립 화음 경계마다 같은 크기의 해결 보너스를 받았다. 실제 선택에는 이끎음 해결 보너스 5회, 합계 `-1/2`가 있었다. 이는 성부의 실제 연결에 근거한 관찰이지만, **성부 해결의 존재가 짧은 순간의 독립 화음 기능까지 입증하지는 않는다.**

한 경계 벌점을 일괄 올리면 다른 작품의 진짜 화음 변화를 합칠 수 있다. 따라서 boundary penalty는 유지하고 해결 보너스의 시간 지지량만 분리해 검토한다.

### 2.2 뒤에 나온 근음으로 앞 구간까지 설명하는 과병합

Beethoven sonata의 기존 `[105,109)` 선택은 G minor `[105,108)` 뒤 E/G♯/B/D/F의 다섯 구성음을 `[108,109)` 하나로 합쳤다. 원 run 특징은 근음이 합집합의 **어느 시점에든** 나오면 `missing_root=0`이다. 따라서 뒤늦은 E 출현이 앞부분부터 E가 관측된 것처럼 유리하게 계산될 수 있다.

다만 앞부분을 근음 생략 확장화음으로 읽는 해석도 원리상 가능하다. 근음 생략·전위·펼친 화음을 금지하지 않으며, 원 주석을 음악적 절대 정답으로 선언하지 않는다. 근음의 첫 실제 관측 시점은 약한 추가 근거이지 기능 확정이나 강제 경계가 아니다.

## 3. 두 일반 규칙과 네 조건

구현은 [harmony_temporal_scoring.py](../../../src/musicanote_harness/harmony_temporal_scoring.py)에 있다. 작품 ID·마디 번호·주석 화음 이름은 입력 규칙에 없다.

### 3.1 박자에 비례한 해결 credit

완료된 왼쪽 harmonic run의 각 시간 구간을 해당 마디의 기존 beat-unit 계약으로 나누고 합산한다. 변경 박자도 구간별로 적분한다.

```text
support_beats = ∫ dt / local_notated_beat_unit
credit_factor = min(1, support_beats)
new_pair_feature = old_pair_feature × credit_factor
```

4/4의 1/4 quarter, 3/8의 같은 길이, 6/8의 같은 길이는 같은 짧음으로 처리하지 않는다. 기존 compound meter 계약인 6/9/12의 8분음표 박자는 점4분음표 기준이다. 박자 미지원은 0점/근거 부재로 만들지 않고 기존 bounded credit을 유지하며 미지원 receipt를 남긴다.

왼쪽 구간이 한 기준 박자 이상이면 원 보너스를 유지하고 더 길다고 무제한 늘리지 않는다. 실제 짧은 화음·해결 후보를 삭제하지 않는다. 왼쪽 run 길이는 지지량을 대략적으로 반영하는 **고정 heuristic**이지 확률이나 독립 화음의 지속시간 정답은 아니다. 긴 쉼을 포함한 run 등 추가 한계가 있다.

다음 raw edge의 끝 시각에 의존하지 않으므로 기존 전이 factorization과 같은 정확 탐색을 사용할 수 있다.

### 3.2 근음의 지연된 첫 관측

양의 실제 sounding event 중 철자가 일치하는 근음을 run 내부에서 찾는다. carry-in 근음도 run 시작부터 관측한 것으로 읽으며 새 attack은 요구하지 않는다.

```text
first_root_time = min(max(run_start, original_root_onset))
root_deferred_presence = (first_root_time - run_start) / whole_context_width
coefficient = 기존 missing_root 계수 1/10
```

- 근음이 한 번도 나오지 않으면 새 항목은 0이다. 기존 `missing_root`가 이미 평가하므로 이중 벌점을 주지 않는다.
- 근음이나 spelling이 미지원이면 새 항목도 미지원이다. 음고류로 enharmonic 철자를 덮어쓰지 않는다.
- 근음이 먼저 나오고 이후 사라지는 분산형은 지연 0이다. 계속 수직으로 완전한 화음일 것을 요구하지 않는다.
- run 이전/이후의 근음을 끌어와 현재 run을 설명하지 않는다. 원 source onset·release·tie를 유지한다.
- `1/10`은 기존 계수의 규모를 재사용한 한 개의 고정값이다. 이번 자료로 학습하거나 coefficient sweep을 하지 않았다. 확률·최적 가중치라는 주장은 없다.
- 이 항목만으로 근음 없는 화음이나 불완전 분산화음을 잘못 억제할 수 있으므로 별도 arm으로 퇴행을 확인한다. 분석적 root와 augmented-sixth tonal coordinate 등의 차이도 추가 점검 대상이다.

| 조건 | 해결 credit | 근음 첫 관측 |
|---|---|---|
| `baseline` | 원 고정 보너스 | 원 `missing_root`만 |
| `meter_credit` | 박자 비례 | 원 `missing_root`만 |
| `deferred_root` | 원 고정 보너스 | 약한 지연 항목 추가 |
| `combined` | 박자 비례 | 약한 지연 항목 추가 |

기존 계수 값과 경계 벌점은 같지만 비baseline의 **점수 계약은 바뀐다**. 이를 “가중치/선택 결과 무변경”으로 표현하지 않는다.

## 4. 같은 후보와 동결 범위

[실행기](../../../src/musicanote_harness/harmony_temporal_scoring_trial.py)는 기존 72구간 중 선택이 있던 **63구간 전부**를 다시 계산한다. 원자료/반복/장문 자원 관문으로 보류된 9구간은 재시도하거나 분모에서 삭제하지 않는다. 알려진 오류 두 곳만 고르는 실험이 아니다.

기존 선택 60개는 원 J3b graph 경로, bounded recovery 3개는 원 J3c graph 경로를 재구성한다. source-clock 관문을 다시 확인하고, 각 scope의 graph를 한 번만 생성해 네 조건에 똑같이 넘긴다. 원 후보 origin·functional receipt·raw cap·source IDs·half-open rational 시간·양의 지속음·grace 보류를 저장한다. 후보 부족을 새 점수로 해결했다고 주장하지 않는다.

매 scope에서 이전 선택의 기존 비용을 재계산하고, fresh baseline이 원 선택의 실제 segments/ID/cost와 같은지 확인한다. 네 조건의 완료 winner도 독립 unindexed scorer로 검산한다. 2M factored 연산·exact rational cost·동점 원 ID·Pareto 계약은 유지한다. resource abort는 후보를 몰래 자르거나 근사 승자를 출력하지 않는다.

전체 72개 예측 packet을 물리적으로 저장·SHA 봉인한 **후에만** 기존 reference-bearing report를 읽는다. 평가 참조와 evaluator witness는 선택 단계에 전달하지 않는다. witness 비용은 봉인 뒤 별도 진단에서만 계산한다.

## 5. 실제 결과

15개 기존 package / 9개 명명 기반 작품군 / 동결 72구간을 유지했다. source-ready 14개 package / 8가족의 63구간을 네 조건으로 새로 선택했으며 9보류는 유지했다. 완전 참조 구간 51개와 부분/미지원 21개도 그대로다. [정본 report](../../../output/harmony-temporal-scoring-2026-10-05-r1/report.json), SHA `9995b34a4c8ff3a0e6b2bc7bd08cefb2ef3d4911a379766ba5e9bb6681c757f0`.

| 조건 | 완전 일치/51 | 근음+구성음 시간 | 작품군 macro | 경계 TP/FP/FN | 경계 F1 |
|---|---:|---:|---:|---:|---:|
| baseline | 15 | 25.3442% | 49.7134% | 50/29/13 | 70.4225% |
| meter credit | 15 | 25.5543% | 49.7960% | 48/21/15 | 72.7273% |
| deferred root | 14 | 25.4142% | 51.1916% | 51/34/12 | 68.9189% |
| combined | 15 | 26.3011% | 51.6722% | 49/22/14 | 73.1343% |

네 조건 모두 선택 63 / 보류 9, prediction coverage 43.7106%다. 후보 ceiling 36/완전51도 같다. 원음 spelling 근음만의 시간 일치는 baseline 34.4691%, combined 34.7608%다. 불완전 참조 시간은 component별 분모에서 따로 관리하고, 미선택 시간은 0 match/0 coverage로 남긴다. 겹치는 scope가 있으므로 시간 합계를 실제 전곡 길이 또는 고유 마디 수로 읽지 않는다.

| 조건 | 바뀐 scope | 시간 일치 증가/감소/같음 | 완전 일치 새 성공/소실 |
|---|---:|---:|---:|
| meter credit | 3 | 1/1/1 | 0/0 |
| deferred root | 9 | 3/2/4 | 1/2 |
| combined | 11 | 4/3/4 | 2/2 |

**두 대표 오류의 개선을 전체 정답률 상승으로 과장하지 않는다.** Combined는 시간 일치 +0.9568 percentage point / 경계 F1 +2.7118 point지만 완전 일치는 유지됐다. Deferred-root 단독은 완전 일치와 경계 F1을 악화시켰다. 계수 값을 후속 grid search로 맞추거나 불리한 scope를 삭제하지 않았다. 세 퇴행도 전체 source/IR 사례로 보존한다.

### 5.1 대표 개선 — 두 조정이 다른 역할을 한다

- **Quartet `[167/2,175/2)`:** baseline 11run → meter 5run → root 11run → combined 1run. Combined는 B♭/D/F/A♭의 B♭7을 전체 범위에 선택했고 참조와 완전 일치했다. baseline 정답 시간 `7/12` → combined `4`, 증가 `41/12` quarter다. 원 경로의 비용은 baseline `3346051/8736000 ≈ .383019`, combined 점수로 재채점하면 `2076917/2912000 ≈ .713227`이다. 참조 B♭7 원 witness 비용은 네 조건 모두 `124879/249600 ≈ .500316`이다. 같은 점수 계약 안에서 순위가 바뀐 것이다. [전체 source·IR·선택·credit·지연 근거 사례](../../../output/harmony-temporal-scoring-2026-10-05-r1/cases/5a7f8e0ef80d4cf5d89a.json.gz).
- **Sonata `[105,109)`:** baseline/meter 2run → root/combined 3run. G minor `[105,108)` → G♯/B/D/F `[108,217/2)` → E/G♯/B/D `[217/2,109)`가 참조와 완전 일치했고 시간 `3` → `4`다. 원 합친 E 근음은 실제 `217/2`에서 처음 나타나며 delay `1/2`, exposure feature `1/8`, 추가 비용 `1/80`이다. 원 합친 경로 `.148917` → 새 점수 `.161417`, 분리 witness `.153941`로 순위가 바뀐다. 이것을 Secondary 기능·국소 조성까지 검증했다고 하지 않는다. [전체 source·IR·근음 시점·원 ID 사례](../../../output/harmony-temporal-scoring-2026-10-05-r1/cases/fe9b0e1f69963fe907c1.json.gz).

### 5.2 중요한 반례 — 근음의 늦은 출현이 항상 화음 변경은 아니다

- **Chopin `[28,61/2)`:** 원 E♭ 해석은 전체 참조와 일치했지만 root/combined가 두 run으로 나누어 정답 시간 `5/2`를 잃었다. 실제 근음은 `30`에서 나와 delay `2`, normalized `4/5`, 비용 `2/25`가 붙었다. 근음보다 다른 구성음이 먼저 나오는 해석을 과도하게 불리하게 만든 실제 반례다. “분산형을 금지하지 않는다”는 단위 계약만으로 이 위험이 해결되지 않았다. [퇴행 원 XML/IR·비용·선택](../../../output/harmony-temporal-scoring-2026-10-05-r1/cases/3e987ee8bfece8435be5.json.gz).
- **Corelli `[55,56)`:** 원 C 해석이 전체 참조와 일치했으나 root/combined는 E 기반 화음들 뒤 C로 나누어 정답 시간 `3/4`를 잃었다. 실제 C는 `223/4`에서 처음 나타나며 추가 비용 `3/40`이다. 같은 observation을 근거로 잘못 과분할한 사례다. [퇴행 원 XML/IR·비용·선택](../../../output/harmony-temporal-scoring-2026-10-05-r1/cases/43984eca2bd701128390.json.gz).
- **Corelli `[169/4,43)`:** meter/combined에서 짧은 해결 credit을 줄인 뒤 새 경로가 정답 시간을 `1/4` 덜 설명했다. 원래도 완전 오답이었으므로 완전 일치 수는 같지만 부분 정확도는 악화됐다. 짧은 화음도 기능적일 수 있는 대조로 남긴다. [퇴행 원 XML/IR·비용·선택](../../../output/harmony-temporal-scoring-2026-10-05-r1/cases/ca9e8feb39a7aee296d1.json.gz).

따라서 “근음 지연 = 화음 변경” 규칙으로 승격하지 않는다. 지연은 관찰 특징으로 남기고, 실제 베이스 유지·기존 구성음의 성부 진행·생략/펼침·경쟁 화음의 설명력과 연결해 평가해야 한다. 특정 Chopin/Corelli 예외를 넣어 두 대표 성공만 남기는 방식은 금지한다.

### 5.3 계산 시간과 감사

실제 runner 518.160초 / exit0. Graph 생성 401.558초, baseline/meter/root/combined의 decoder 합계 각각21.599/21.599/20.817/22.044초다. 단일 관측이며 전체 speed benchmark는 아니다. 완성된63graph는44,204 원edge다. source 수14와 candidate edge 수44,204를 독립 작품 수/성공 수로 읽지 않는다.

[사후 감사](../../../output/harmony-temporal-scoring-2026-10-05-r1/post-seal-audit.json)에서1,202고유SHA·72scope×4metric·63fresh baseline·14전체source·44,204edge codec·252winner 독립비용·11변경/진단사례 및 원 reference witness 비용을 재생했다. 새 추론/학습 없이 통과했다. [감사 코드](../../../scripts/audit_harmony_temporal_scoring.py).

## 6. 사례의 재현 형태

14개 source-ready package의 전체 원 MusicXML과 관찰 IR을 scope별로 중복 복제하지 않고 source case 폴더에 저장한다. 각 graph/prediction/case는 전체 source 경로·물리 SHA·IR content SHA·구간 및 원 note/sound/source refs를 참조한다. 원 source에는 앞뒤 문맥까지 포함되어 있어 음악적으로 작은 차이를 다시 볼 수 있다.

알려진 두 오류와 선택이 바뀐 모든 scope에 네 selected path의 비용·원 ID·박자 credit receipt·근음 첫 관측 시점·해당 원 event IDs를 저장한다. 참조 진행의 witness가 있으면 같은 네 점수로 **사후** 대조하되 `source_labels_used_to_create_this_path=true`로 구별한다. AI/사용자 검수 정답으로 승격하지 않는다.

이번에는 새 브라우저 UI·운영 layer를 연결하지 않는다. 연구용 점수의 효과·퇴행부터 확인한 후 전체 악보 위의 비교 사례로 연결하는 것이 다음 표시 작업이다.

## 7. 코드 검사와 실패 기록

- 신규 scorer 18개: 변경 박자·상대 길이·unknown·carry/rootless/enharmonic·분산형·every-interval indexed/unindexed 일치, 원 module global 불변, 20개 고정 tiny DAG × 네 조건의 exhaustive optimum/cost/동점 비교.
- 신규 trial 8개: graph codec·독립 비용·네 예측 봉인 뒤 참조·보류 분모 유지·원 source 보존·code/source/라벨 변조 거부·overwrite 거부.
- 사후 감사 3개: Python tuple/JSON array canonical 값 일치·실제 결과 변조 거부·inference packet의 reference 유입 거부.
- 첫 private-binding smoke는 기존 helper가 outer bytecode만 검사해 `binding_dependency_not_used`로 실패했다. 기존 helper/봉인 코드는 수정하지 않고, 새 모듈에 nested code의 실제 dependency 사용을 확인하는 별도 binder를 추가했다. 새 binder도 unsupported/missing/invented dependency를 거부한다.
- 회귀 실행기 첫 호출에서 이전 `test_modules`가 목록이 아니라 개수였으므로 `int + list` TypeError로 테스트 시작 전에 실패했다. 원 파일을 바꾸지 않고 실제 목록 필드 `modules`를 사용해 재실행했다.
- 사후 compact 집계 첫 명령은 미지원 `candidate_ceiling=None`을 합계에 넣어 TypeError로 중단됐다. 원 결과를 수정하지 않고 Boolean 지원 여부로 세어 완전51중36을 확인했다. 본체 runner/정본/감사는 모두 exit0이며 이 두 임시 확인 명령 실패는 음악 계산 오류가 아니다.
- 관련 33개 모듈 **484개 검사 PASS / 32.880초**. repository 전체 suite가 아니며 484곡을 분석한 수가 아니다. [검사 결과](../../../output/harmony-temporal-scoring-2026-10-05-r1/test-validation.json).

## 8. 재현과 다음

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_temporal_scoring_trial --source output/harmony-streaming-joint-2026-10-05-r1 --output output/harmony-temporal-scoring-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/audit_harmony_temporal_scoring.py --root output/harmony-temporal-scoring-2026-10-05-r2
```

출력은 기존 폴더를 덮어쓰지 않으므로 아직 없는 별도 디렉터리를 지정한다. 새 run은 같은 source/후보/점수 조건의 재생이며 새로운 독립 평가 자료가 아니다.

**결정: 운영 미채택.** 큰 두 오류의 개선과 세 퇴행을 함께 보존하며 성공 사례에 맞춰 계수를 더 높이지 않는다. 다음은 근음 지연을 곧바로 벌점으로 사용하는 한계를 보완할 **펼침/생략/베이스·성부 지속과 경쟁 화음의 공동 설명**을 고정된 별도 조건으로 대조한다. 더 넓은 작품군 비중복 자료에서 독립 검증하는 J3~J5도 남는다. 기능·국소 조성·NCT 미지원과 후보 부족은 따로 관리한다. 기존 운영/종지/프레이즈 입력과 Claude Motif를 건드리지 않는다. 장문 2M 보류도 이번 실험으로 해결됐다고 하지 않는다.
