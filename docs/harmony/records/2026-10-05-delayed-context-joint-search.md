# 단계79 — 3-run 문맥의 지연 점수와 exact 화음·경계 공동 선택

## 1. 목적과 이번 단계의 범위

단계78의 유지+장식 대 새 화음7특징을 저장 경로의 진단에서 **실제 공동 선택**으로 연결한다. 새 계수의 학습·Dev 평가·운영 적용은 이번 단계에 포함하지 않는다. 기존26항·원 후보/시간/철자/ID/최대6 raw edge·2M 한도는 그대로다. 이 기록은 화성 개발 문서이며 구조 분석/인수인계 문서에 흩어 쓰지 않는다.

새 비용이0이면 기존 봉인 batched 선택기를 사용한다. 별도 강제 지연0조건은 새 상태 계산이 기존 결과와 동일한지 검증한다. 부호가 있는 수치 시험 계수는 `+1/8,-1/8,+1/8,...`로 실행 전 고정하며 학습된 음악 규칙이나 운영 권장 계수가 아니다.

## 2. 충분한 상태와 비용 확정 시점

기존 현재 run의 시작/signature만 기억하는 상태는 이 비용에 충분하지 않다. A→B의 장식 경쟁 근거는 C의 **완전한 끝 시각**에 따라 달라진다. C를 같은 화음의 raw 조각으로 연장하는 동안 그 비용을 미리 확정하면 잘못된 경계가 선택될 수 있다.

새 상태는 `(raw edge 수, 최근 세 union run의 시작/signature)`이며 endpoint는 각 상태 표의 위치다.

- A,B,C를 갖고 D가 시작하면, C의 끝이 확정되므로 A→B 비용을 한 번 더한다. B,C,D를 남긴다.
- 같은 signature의 raw 조각은 현재 union run을 연장한다. 기존 run 비용은 이전 누적값을 빼고 완전 run 값으로 바꾸되 문맥 비용을 중복 더하지 않는다.
- 작품/분석 범위 끝에서는 남은 A→B(다음C 있음), B→C(다음 없음) 비용을 모두 더한다. 1run은 알려진0이다.
- 같은 endpoint/세 run 이력에서만 raw edge 수와 비용/ID 사전 순서의 Pareto 제거가 가능하다. 서로 다른 앞 화음을 현재 화음이 같다는 이유로 합치지 않는다. Beam/상위N 필터는 없다.
- 동점이면 기존 raw ID tuple의 사전 순서다. 양의 길이 DAG 경로는 같은 endpoint에서 서로의 proper prefix일 수 없으므로 동일 suffix를 붙여도 tie 순서가 보존된다.

모든 점수/시간은 Fraction이다. 새 비용 계산의 지역2/3run을 넘겨도 bass coverage 분모는 **원 분석 범위의 전체 quarter 폭**, 음가 노출 분모는 **원 전체 sound overlap note-time**으로 유지한다. 원 같은-signature 분할 불변과 reference 없이 계산되는 source-clock/history/성부·grace 관문을 보존한다.

## 3. unknown과 기존 점수의 계약

새 비용은 각 전이에서 **available인 항만** 더한다. unavailable 전이의 부분 관찰 합은 receipt에 남지만 점수에 쓰지 않는다. 경로 전체의 availability는 모든 전이의 논리곱이다. 일부 전이만 알려진 항의 누적 score 합을 완전한0/확정 관측값으로 읽지 않고 전체 feature는 null이다.

향후 학습 gradient는 두 완전 경로에서 jointly available인 차원만 쓴다. 원26항의 unknown 정책은 변경하지 않는다. 알려지지 않은 성부/박자가 비용을 덜 내는 비교 가능성 문제를 숨기지 않으며, 이 구현만으로 그 음악적 문제를 해결했다고 주장하지 않는다.

기존 비용은 원 source scorer·원 기능/전이 정의로 계산하고, 최종 경로는 원 decoder의 해당 양의 chain으로 다시 구성해 기존 비용을 독립 검산한다. 새 전체 경로 비용은 지역화하지 않은 전체 run receipt와 일치해야 한다. Context/가중치/원 모듈 global 변경·없는 후보/가짜 attack 삽입·확정NCT·주석 대입0이다.

## 4. 구현과 실행 전 검증 계획

새6Python 파일:

- `src/musicanote_harness/harmony_context_joint_decoder.py`: 지연 점수/세 run 상태/exact 선택/최종 receipt.
- `src/musicanote_harness/harmony_context_joint_trial.py`: 봉인된23악장 Train source 재구성,588저장경로 대조,0계수 control 재선택, 작은 원 graph 수치 시험.
- `tests/test_harmony_context_joint_decoder.py`: 17검사. signed/기존 계수 변형의 tiny DAG 전수,4~6run 경쟁, 마지막 flush, raw 분할/동점/동일 edge, 변경박자/분수/성긴 grid/unknown/한도/원자료 보존.
- `tests/test_harmony_context_joint_trial.py`: 5검사. label 비사용 시험군 선정·fixed stress·전체 profile 재생/변조·target provenance·unknown 비용.
- `scripts/validate_harmony_context_joint_decoder.py`: 기존789검사 inventory에22신규를 추가한다.
- `scripts/audit_harmony_context_joint_trial.py`: 봉인 input과 원 graph·profile·기존/새 비용 재생. 새 탐색/fit/Dev는 수행하지 않는다.

17+5 합성 검사는 모두 PASS다(22검사·6.625초). 이 계획을 실행 전에 기록하고 아래 절에 완료 결과를 덧붙였다. 신규 함수/시험 코드에서 원 source를 삭제하거나 기존 봉인 코드를 수정하지 않는다.

실제 시험군은 승인 Train118범위 전체다. 원 graph edge 수≤100에서 `(edge 수,sample ID)`순으로 최초8개의 **서로 다른 source SHA**를 실행 전에 선택한다. 참조 화음/정오·타이틀로 선택하지 않는다. 이8개는 원 graph의 모든 edge를 그대로 두고 forced delayed0 및 signed stress를 실행한다. 전체118개는0계수 legacy 재선택을 비교한다. 수치 검산/지연 시험이지 음악적 정확도 평가가 아니다.

2M은 새 지연 decoder의 **feasible state/raw edge 비교 수**다. 기존 batched 연산과 단위가 달라 숫자가 같다고 지연 성능이 같지는 않다. 한도에 닿으면 부분 승자를 반환하지 않고 보류한다. 수치 시험의 보류를 성공 예측으로 세지 않는다. 전체118graph에 nonzero 새 계수로 확대하는 것은 제한 학습 및 계산량 점검 이후다.

## 5. 다음 단계와 보존

선택기 비용 계약과 실제 원자료 재생을 확정한 다음, 이전26항을 보존하는 제한 Train 학습을 진행한다. 저장 대조로 배운 margin은 정확도가 아니며, 새 일반 공동 선택의 정오/근음·구성음 시간/경계/작품군별 퇴행과 보류를 재측정해야 한다. 이후 모델 고정 Dev 비교이며 노출 Dev로 계수/epoch/threshold를 고르지 않는다.

NC 로컬 연구·출처/라이선스 SHA와 운영 학습 미승인을 유지한다. 원 XML/IR/Core/IDs·구조/Claude Phrase·Motif·MusicSearch/Composition·서버·별개dirty/Git 보존. API/merge/commit/push/화면 적용0이다. 독립 Test/fullRoman/국소조성/전체NCT·종지·편곡/작곡 평가 미완료다.

## 6. 실제 실행과 결과의 한계

`output/harmony-context-joint-search-2026-10-05-r1` actual은296.909185초/exit0로 완료했다. 승인 Train118범위/23전체 악장 source/15작품군·원60,129edge를 그대로 재구성했다. 기존 원2adversary 보류는 재탐색하지 않았으며152제외 parent scope를 승인 코호트에 끼워 넣지 않았다.

- 저장588경로/620전이/144조건부 형태를 지역화한 새 선택기 receipt와 원 단계78의 **전체 run profile**로 대조했다. 원26항 비용/원ID/원 source-span·anchor 대안·availability/partial/null이 같다. Signed 수치 계수 아래 known nonzero feature 누적 경로260개/비0 문맥 비용245개이며15개의 상쇄도 보존했다. 모든7항이 known인 경로는437개이고 나머지151개는 일부 unavailable이다. 원2보류를 포함한590조건을588완료로 바꿔 보고하지 않는다.
- 새7계수0의 legacy fresh ordinary 재선택118개는 단계75의 봉인된 ordinary 경로/비용과 모두 동일하다. 이는 기존 정답률 향상이나 단계75 가중치 재채택이 아니라 **연결의 무변경 control**이다.
- 실행 전 정한8개 원 graph의 강제 지연0·signed 수치 시험은 모두 끝까지 선택했다(원 edge10/17/29/43/48/49/50/52개,8source/6작품군). 각각의 새 raw 비교는5/11/23/77/78/248/198/42회이며2M 보류0이다. 양·음 부호를 갖는 계수로 경쟁 경로를 계산했으나, **8최종 승자는 두 조건에서 모두 동일하고 새 문맥 비용0**이다. 단순한 끝단/소규모 그래프가 많은 시험군이므로 이8개만으로 실제 NCT 경쟁이 있는 큰 graph의 선택 효과나 전체 지연 성능을 입증하지 않는다. Small winner가0이어도 저장경로260개에 known 비0 특징이 있다는 것과 모순되지 않는다.
- 새17검사에는 비0 signed7항/기존26계수 변형,4~6run 경합, future end가 달라지는 경우와 tiny DAG **모든 경로의 min(cost, ID)** 일치가 포함된다. 실제 source의8시험은 이 합성 전수 검사와 별도로 보고한다.

기존789+신규22=**811관련검사/72모듈 PASS**, failure/error0·92.630322초다. Repository 전체 suite나 음악 정답 검사811건이 아니다. 신규6Python strict UTF-8/AST/trailing whitespace PASS다. Actual을 시작한 뒤 해당 code/test/script 수정0이다. 최초로 없는 `harmony_full_score_scoring.py`를 읽으려 했던 경로 오류는 실제 `harmony_full_score.py`로 찾아 수정했고 코드/원자료/규칙은 바꾸지 않았다. 새 합성 검사·actual에는 실패/중단0이다.

**아직 새7계수를 학습하지 않았고 정확도를 평가하지 않았다.** 선택기 구현과 source 비용 검산은 끝났지만, 수치 시험에서0최종 비용을 본 것을 성능 개선으로 읽지 않는다. 다음 제한 Train 학습 후에는 원26항을 보존하며 실제 문맥이 작동하는 큰 graph의 fresh ordinary·보류/계산량/기존 정답 소실도 함께 확인한다. 원자료 재생/작품군별 정확도/독립 평가/운영 적용의 완료 기준은 서로 다르다.

메인/로그 갱신을 묶은 patch1회는 기존 단계78의 로그 제목을 잘못 기대해 검증 실패했다. 해당 시도에서 파일 변경0임을 확인하고 실제 제목을 읽어 다시 적용했다. Actual 코드/산출물/조건을 고친 실패가 아니다.

## 7. 봉인·재현

- [실제 완료 report](../../../output/harmony-context-joint-search-2026-10-05-r1/report.json): SHA `231e3743ef04ec9edb44f903abf6956d74889d03a831384fb186527c5c5718d8`.
- [사전 실행 계약](../../../output/harmony-context-joint-search-2026-10-05-r1/run-contract.json): SHA `8fd557e0451825abfc4bc726bef5fa387002717bf023b805ce0ec144242d6105`. 시험8scope/부호·계수/한도는 새 예측 전에 확정했다.
- [811검사 결과](../../../output/harmony-context-joint-validation-2026-10-05-r1.json): SHA `000450d92f7a52e4d9522d190c1b4c02a9f8c646d0988622374e129bb3ba6dcc`.
- 원 단계78 report/audit 및 단계75 모델 SHA는 그대로다. 모델은 `2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf`다.
- [사후 감사](../../../output/harmony-context-joint-search-2026-10-05-r1/post-seal-audit.json) PASS/exit0:3,081고유SHA/3,074봉인 input·원118scope/23source/60,129edge·588경로와 기존/새 비용·620전이/144형태·134fresh prediction 비용 receipt를 재생했다. 감사에서 새 search/fit/Dev0,Core/운영 모델 변경0이다. SHA `48f55f344ce5dc37ba009bc2db7ddb7e318f66a98476c34dea4c9d426ece906e`,audit code SHA `bac9948998ce098f68faa0deee92031aafc9ed0b045b3e9fb3b561f30a672014`. Code430/산출물119개의 실제 전후 pins도 변함없다. 이것은 source/비용 재생 감사이지 참조와134예측이 음악적으로 일치한다는 결과가 아니다.

아래 명령은 `K:/Music Analysis`에서 실행한다. 기존 output을 덮어쓰지 말고 존재하지 않는 새 경로를 사용한다.

```powershell
$env:PYTHONPATH='src;tests'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_context_joint_decoder.py --prior-validation output/harmony-context-competition-validation-2026-10-05-r3.json --output output/harmony-context-joint-validation-replay.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_context_joint_trial --output output/harmony-context-joint-search-replay
.\.venv\Scripts\python.exe -B scripts/audit_harmony_context_joint_trial.py --root output/harmony-context-joint-search-replay
```
