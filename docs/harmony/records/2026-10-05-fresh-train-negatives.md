# 단계70 — 현재 공동 선택기의 Train 오류 재추출

## 1. 목적과 이번 범위

단계69에서는 승인된 과거220대조 중 timing을 학습할 수 있는180개를 사용했지만 실제 delta가 있는 것은8개뿐이었다. 같은 과거 경로에 scalar를 추가하는 실험만 반복하면 현재 선택기가 실제로 틀리는 곳을 학습에서 놓칠 수 있다. 이번 단계는 **현재 점수로 승인 Train 전체를 다시 선택하여 새로운 오류 대조를 저장**한다. 새 음악 규칙이나 가중치 학습을 이번 진단에 섞지 않는다.

원 J2f 보고서의270 Train 구간을 전부 대상으로 한다. 과거 update/collision이 있던116구간만 고르지 않는다. Parent JSON에는52개의 역사적 Dev 행도 들어 있으나 현재 후보 재구성·선택·target 탐색·평가·대조에는 승인 Train만 사용한다. 부모를 읽은 사실을 ‘Dev 데이터를 전혀 본 적 없음’으로 표현하지 않는다. **Train 안의 진단이며 독립 일반화 정확도가 아니다.**

고전 화성 작업을 계속하며 재즈 전용 프로파일은 이번에 추가하지 않는다. 특정 작품·마디·사용자 정답을 후보/점수의 예외로 넣지 않는다.

## 2. 고정한 선택 계약

- Control: 단계67의 고정4계수. 비교 arm: 같은4계수 + 단계69 timing `.248879`.
- 단계68 recipe 벌점은 사용하지 않는다. 이번 두 계수 파일은 기존 SHA에 고정하고 재학습하지 않는다.
- 원 Train source/IR·원 후보점/edge/최대6 raw edge와2,000,000 factored 연산 예산을 유지한다. 후보 ceiling은 보존된 어휘와 cap의 표현 가능성이지 정확도가 아니다.
- Source-clock 관문 실패는 격리한다. 부분 주석·지원 밖 주석은 정답을 꾸며내지 않으며 평가 가능한 시간만 별도로 집계한다. 후보 부재와 자원 보류도 숨기지 않는다.
- 이전 Train graph는 일부 실제 마디 경계를 포함하지 않아 prefix index의 검증에 실패할 수 있다. 원 후보점에 경계를 끼워 넣는 대신 **원음표를 직접 읽는 feature backend**로 sealed joint decoder를 privately bind한다. 계산하는 음악적 비용은 같고 reconstruction으로 winner 비용을 독립 검산한다.
- Ordinary prediction API에는 reference/loss 인자가 없다. 각 구간의 두 ordinary 예측을 먼저 별도 파일/SHA로 저장한 후 Train reference-compatible target을 탐색한다. Source binding 준비 과정에서는 Train 주석의 동일성도 확인하므로 전체 데이터 방화벽을 주장하지 않는다. 이 봉인은 **target 검색이 ordinary 선택을 덮어쓰거나 참조로 바꾸지 않았는지** 확인하는 절차다.

## 3. 후보 ceiling·선택 오류·새 대조

Reference의 exact root+spelled members와 겹치는 원 후보 edge만 남기는 Train 전용 compatible graph를 만든다. 여기에도 정답 후보를 삽입하지 않는다. 최소 raw edge 수를 DAG에서 정확히 구해 다음을 구별한다.

1. 부분/지원 밖 reference 또는 원 graph 보류: ceiling 미확인.
2. Compatible path 자체가 없음: 원 후보망에 정답 경로 없음.
3. 경로는 있으나 최소 raw edge 수가 cap 초과: cap 때문에 정답 진행 표현 불가.
4. 정답 경로가 있고 ordinary가 틀림: 현재 선택 오류.

4번에서는 같은 점수의 compatible graph에서 가장 낮은 비용의 target을 고른다. Ordinary winner와 target 사이의 기존 normalized time + semantic boundary loss(경계 가중치1/4), base cost, 다섯 source feature, 각각의 availability를 저장한다. Target에는 `source_labels_used_for_selection=true`, `training_reference_labels_used=true`, `target_only=true`를 붙인다. 일반 분석 결과/화면으로 내보내면 안 된다. Target 탐색의 자원 보류도 기록하며 재시도나 cap 증가로 없애지 않는다.

이번 hard negative는 **ordinary current winner**다. 틀린 경로의 loss를 최대로 확대하는 loss-augmented adversary는 아직 아니다. 모든 가능한 음형의 negative pool 완성, 매 epoch 새 adversary 생성이나 최종 weights 재학습이라고 표기하지 않는다.

같은 source/negative/target ID 대조는 arm 간 중복 제거한다. 원 raw partition/alias ID가 바뀌어 ‘새 음악 사례’처럼 보이는 것을 막기 위해, 과거220대조와 비교할 때 **완료된 동일-signature harmonic runs**도 비교한다. Exact raw 경로의 새 수와 의미상 새 음형/경로의 수를 구별한다.

Unknown 특징은 null/availability=false로 보존한다. 모든 값이0인 positive-loss 충돌도 저장한다. 가중치에 정보를 주지 않는 대조를 대조 개수만으로 유효한 학습 정보라고 세지 않는다. 역할 미지원/functional6-4/페달의 공정 비교, 실제 앞뒤 조성/베이스/NCT 문맥, 새로운 후보 연결의 필요성을 다음 학습 전에 판단할 자료다.

## 4. 저장과 검증

구현: [직접 source scorer·ceiling·대조](../../../src/musicanote_harness/harmony_fresh_train_negatives.py), [승인 Train 전체 실행](../../../src/musicanote_harness/harmony_fresh_train_trial.py), [사후 검산](../../../scripts/audit_harmony_fresh_train.py), [회귀 실행](../../../scripts/validate_harmony_fresh_train.py).

모든 구간마다 ordinary 예측 packet과 scope/case packet을 만든다. Scope에는 원 graph codec·source context/search artifact SHA·전체 원 IR content SHA·원 reference·선택/target 경로·계수별 비용·source note/sound ID와 support receipts를 저장한다. 원 전체 XML/IR는 이미 보존된 SHA-bound context를 통해 연결하며 절단한 부분 악보로 대체하지 않는다. 새 대조 파일과 실행 계약·source/code/artifact hash를 함께 저장한다.

신규 [backend/ceiling/대조 검사](../../../tests/test_harmony_fresh_train_negatives.py), [cohort/분류 검사](../../../tests/test_harmony_fresh_train_trial.py)15개 통과. 초기 ceiling 합성 fixture에서 graph에 없는 뒤쪽 G edge를 정답으로 잡아1FAIL이 있었다. 실제 존재하는 G→C 경로로 fixture를 고쳤고 후보/검사 조건/기존 code를 완화하지 않았다. 신규15 + 이전 관련651 = **666검사/53모듈 PASS**, failure/error0·72.256초다. Repository 전체 suite나 음악적 정확도 수치가 아니다. [회귀 정본](../../../output/harmony-fresh-train-validation-2026-10-05-r1.json), SHA `99e4284e074acba2dff45fd12b6467b5fa5eb4bbd9fe66aea37d25e4f60fc149`.

Actual 시작 후 code/test/script를 바꾸지 않는다. 모든 파일은 기존 출력 덮어쓰기를 거부한다. 사후 검산은 source를 다시 읽어 원 graph/clock·ceiling·ordinary/target 비용·fresh 대조·source receipts·과거 pool 비교·공통 지표를 재생한다. Audit은 새 선택기 탐색을 재실행하는 것이 아니다. 실제 탐색은 run에서 exact decoder·reconstruction 검산으로 수행했고 작은 graph의 전체 열거와 indexed/direct 일치도 합성 검사로 확인했다.

## 5. 실제 결과

Actual r1은 **738.113초/exit0**로 완료했다. 원126,679edge·270구간·27전체 악장 source·16명명 작품군을 빠짐없이 저장했고 source-clock 범위 관문270개 모두 통과했다. 범위 관문 통과가27개 전체 XML의 무오류를 보장한다는 뜻은 아니다. 단선율27곡을 새로 수집했다는 뜻이 아니라 이미 승인된 악장/판본 패키지를 전부 다시 계산한 것이다. 과거 대조를 만든 source는23악장/15작품군이었고 이번 전체 Train에는 대조가 없던 source도 들어 있다. 서로 겹치는 구간을 포함하므로 quarter time 총합을 고유 악보의 재생시간으로 읽지 않는다.

| 구분 | 단계67 고정4계수 | 같은 점수 + 단계69 timing |
|---|---:|---:|
| 선택 / 보류 | 242 / 28 | 242 / 28 |
| 완전 평가 가능 / 부분·지원 밖 | 205 / 65 | 205 / 65 |
| 전체 구간 일치 | 54/205 (26.3415%) | 54/205 (26.3415%) |
| 근음+철자 구성음 시간 일치 | 32.1860% | 32.1860% |
| 작품군 macro | 40.5283% | 40.5283% |
| 근음 시간 일치 | 40.5013% | 40.6253% |
| 정확 경계 TP/FP/FN | 154/58/179 | 155/58/178 |
| 정확 경계 F1 | 56.5138% | 56.7766% |

**학습에 이미 사용된 Train의 진단 수치**이며 Dev72의28.33%와 다른 분모다. 운영 정확도·새 모델 학습 성과·전체 Roman/전위/local key/종지/NCT 정확도가 아니다. 이번 일반 선택기 status는 sealed reconstruction의 `selected_untrained_hypothesis` 문자열을 그대로 물려받지만, 실제 네/다섯 계수는 실행 계약의 **기존 Train-calibrated model SHA**에 고정되어 있다. status 이름만 보고 모든 계수를 미학습이라고 판단하지 않는다. 새 weights는 만들지 않았다.

후보 ceiling은118/205(57.5610%)다. 270구간의 상호 배타적 현재 분류는 **reference 일치54 / 정답 경로가 있으나 선택 오류64 / 정답 경로 부재 또는 cap75 / 선택된 부분 주석49 / 원 후보망 보류28**이다. 전체65부분 주석 중16개는 원 후보망 보류28 안에 들어 있고, 그28 중12개는 완전 주석이다. 따라서 부분65와 보류28을 단순히 더하여 분모에서 제거하지 않는다.

75는 compatible path 부재74와 cap 초과1로 나뉜다. 원 보류28은 `baseline_not_ready`26·`edge_budget_abstention_no_pruning`2다. Fresh 선택/target 탐색에서 새 transition-budget 보류는 없었으며 target128개 비교를 완료했다. 정답 경로가 존재하는118개 중54일치·64선택 오류라는 구별이 다음 점수 학습의 범위다. 후보망의75개 오류는 같은 weights를 바꾸는 것만으로 해결할 수 없다.

### 새 학습 대조의 정보량

- 64오류 구간/13명명 작품군에서 두 arm 간 중복을 제거한 **65 fresh 대조**를 저장했다. Raw alias/partition 차이뿐 아니라 완료된 harmonic-run 기준으로도 **50개는 과거220대조에 없던 negative/target 진행**이다. 모든 가능한 negative를 찾았다는 의미는 아니며 구간 간 악곡 반복/중복 감사도 별도다.
- 다섯 추가 특징이 양쪽 모두 관측 가능한 대조는41개, unavailable을 포함한 것은24개다.24개도 버리지 않고 저장했다. 그 안의 durable nonmember 특징은 모두 사용 가능하지만 나머지 역할/timing의 비교 가능성은 보장되지 않는다.
- **관측 가능한41개 중21개는 추가 다섯 특징이 모두 동일**, 차이가 있는 것은20개다. 전체65의 accumulator delta0은35개이나 그중14개에는 unavailable이 있어 ‘실제 전체 특징이 완전히 같다’는 증거로 쓰지 않는다. 기록된 null 관측을 사실상의0으로 해석하지 않는다.
- 특징별 nonzero delta는 미관측3음14·변화5음3·7음5·지속 nonmember16·late timing1이다. 앞의 네 역할과 timing은41개에서 available이고 durable은65개에서 available이다. 숫자들은 서로 겹치므로 합해서 독립 사례 수로 사용하지 않는다.
- Timing 값이 있는 negative1개·target0개다. 따라서 같은 late-entry scalar만 다시 학습하는 것으로 큰 향상을 기대할 근거가 부족하다. Fresh pool을 만들었어도 **전체 점수 특징/NCT·베이스·복잡도 균형을 검토해야 한다**는 결론이다.

두 arm에서 바뀐 ordinary 경로는2구간이다. Sonata02-2 `[8,13)`은 여전히 선택 오류지만 마지막 D 삼화음의 시작을11→12로 바꾸어 정확 경계 하나를 복구한다. Root+members time은 같고 주석의 G#/B/D/F# 화음과 A 삼화음을 여전히 맞히지 못한다. Negative는 A/C#/E/G 7화음에서 A/C#/E/G# 및 A/C#/E/F#/G의 어휘 밖 넓은 집합으로 바뀌며 timing을 피한다. 미지원 shape의 공정 비교가 여전히 문제다. [전체 source·두 경로·target·receipt](../../../output/harmony-fresh-train-2026-10-05-r1/scopes/cont_4f4f6dc881cf72de3728.json.gz).

Sonata02-3 `[11,18)`은 부분/지원 밖 reference 구간에서 바뀌며 root time만1quarter 늘고 전체 root+members 일치는 늘지 않는다. 부분 평가의 작은 이익을 완전 성공으로 세지 않는다. [보존 사례](../../../output/harmony-fresh-train-2026-10-05-r1/scopes/cont_2d39ed144d91b8afe319.json.gz). 두 scope 모두 이미 노출된 Train이다.

정본: [report](../../../output/harmony-fresh-train-2026-10-05-r1/report.json), [fresh 대조](../../../output/harmony-fresh-train-2026-10-05-r1/training-contrasts.json.gz), [실행 계약](../../../output/harmony-fresh-train-2026-10-05-r1/run-contract.json). Report SHA `b542fa2e7e82bc02b49edc70d3f71bfbbad1fb9b951a318200d8d6759381c532`, 대조 byte SHA `f6daa18bdd7296fc86090abf8c61736843a635067e0695eea1012eaef2745d6e`, 계약 SHA `ea95f204f2037b2670c70a420774d74088e05771088ef247a76df6189e1f5c80`. Progress JSON은 loop 마지막 checkpoint(`complete=false`)이며 **종료/완료 여부는 report의 `complete=true`가 정본**이다.

사후 source/비용/지표 감사는 **exit0 / PASS**다. 1,595고유 SHA·270승인 Train 범위·27전체 source 연결·원126,679edge 복원·540ordinary packet·612독립 경로 비용·128arm 대조·65고유 대조와 두 arm의 공통 지표를 재생했다. 새 decoder 탐색이나 weight fit을 수행한 것은 아니다. [감사 정본](../../../output/harmony-fresh-train-2026-10-05-r1/post-seal-audit.json), byte SHA `828d615429e733796f6e45f98fcbe00eb0bc1f6aea0d92d2defbf65347bce2bb`. 새 계수/운영 승격은 없다.

여기서 ‘정답 경로’는 원 DCML 주석의 비교 target을 뜻하며, 각 해석을 인간이 다시 승인했다는 의미는 아니다. 사례에는 human_validated=false를 유지한다. 교재·음표·주석 간 충돌은 source를 고치지 않고 별도 검토/annotation correction으로 남기는 원칙을 유지한다.

### 새 대조에서 드러난 점수 충돌 사례

베토벤 현악4중주1번 op.18-1의4악장 Train 구간 `cont_05a973a926c1c81874af`, `[2147/4,1075/2)`는 reference가 F/A/C 삼화음이다. 현재 ordinary 선택은 F/A/C/E 7화음으로 비용 `.115`, compatible target의 F/A/C는 `149/600=.248333…`이다. 원 raw 두 edge의 같은 signature를 한 run으로 계산한다. 다섯 추가 특징은 두 경로에서 모두0이고 availability는 true다.

그렇다고 기존 source 근거가 전혀 없는 것은 아니다. Target의 E에는 같은 명시 성부의 **조건부 neighbor-like** 관계가 이미 탐지되어 `conditional_step_ornament_exposure=1/5`다. 원 event ID는 `sound_a04ae05137a5 → sound_2499e7347984 → sound_5b168af46292`다. 이 근거의 기존 credit은 `-1/2 × 1/5=-.1`이지만, target은 raw nonmember `.2`·metric `.05`·lowest `1/12`·run `.015`도 지불한다. Ordinary는 E를7음으로 포함시켜 raw nonmember 비용을 피하고 extra-member `.1` + run `.015`만 지불한다. **NCT 후보를 못 찾은 오류와, 후보 근거가 있는데 점수 균형 때문에 선택하지 않은 오류는 다르다.**

이 구간에서5계수만 바꾸면 delta0이므로 선택을 고칠 수 없다. 그러나 기존 전체 score feature까지 모두 같다는 뜻도 아니다. 기존 raw/metric/lowest/conditional ornament/complexity 항목은 다르므로 **현재 전체 점수 특징의 Train 학습**을 검토할 이유가 된다. E를 확정 NCT로 지우거나 이 작품의 F 삼화음을 강제하지 않는다. [원 구간·전체 source 연결·두 경로와 receipt](../../../output/harmony-fresh-train-2026-10-05-r1/scopes/cont_05a973a926c1c81874af.json.gz).

## 6. 재현과 다음 단계

기존 출력은 덮어쓰지 않고 새 이름을 사용한다.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_fresh_train_trial --output output/harmony-fresh-train-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/audit_harmony_fresh_train.py --root output/harmony-fresh-train-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/validate_harmony_fresh_train.py --prior-validation output/harmony-member-timing-validation-2026-10-05-r1.json --output output/harmony-fresh-train-validation-2026-10-05-r2.json
```

새 pool에서 유효한 특징 차이·지원 어휘·target이 실제로 충분한지 확인한 다음 **Train 전용의 joint selector 학습**으로 이어간다. 특징이 모두 같은 오류나 후보에 정답이 없는 오류를 같은 weight fit으로 고칠 수 있다고 가정하지 않는다. Loss-augmented/current-score hard negatives와 실제 선택된 앞뒤 화음의 문맥 특징은 별도로 검증한다. 이미 노출된 Dev와 독립 Test·공개 모델 비교, 전체 Roman/전위/local key/종지/NCT·장문 자원 보류는 미완료다.

이번 작업은 NC 로컬 연구 계약을 유지하며 새로운 권리·상업적 운영 허가를 부여하지 않는다. UI·Core/원 XML/원주석·MusicSearch/Claude/Composition·별개 dirty·Git·API 전송은 변경하지 않는다.
