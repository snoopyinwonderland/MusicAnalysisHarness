# HARM-DEV-20261005-77 — 화음 유지/교체의 실제 구성음 지지 점검

화성 분석 **개발 기록**이다. 인수인계 문서가 아니다. 단계76의 고정 모델 Dev 퇴행을 따라, Dev에 가중치를 맞추지 않고 기존 Train 선택 경로를 원음표와 다시 대조한다.

## 1. 상태와 저장 위치

실제 진단118범위와 사후 독립 재계산 감사를 완료했다. 검사 통과는 음악적 정확도 향상을 뜻하지 않는다. 새 가중치 학습·새 선택·운영/UI 적용은 없다.

K: 저장 공간이 0바이트여서 첫 실행은 38/118구간 저장 후 `OSError: [Errno 28] No space left on device`로 종료했다. 39번째 case는 0바이트이며 완료 report/사후 감사가 없다. `K:/Music Analysis/output/harmony-transition-support-2026-10-05-r1`을 완료 결과로 사용하지 않는다. 40개 파일/337,079바이트의 부분 산출물은 실패 기록으로 보존했다. 다른 악보/실험·사용자 파일은 삭제하지 않았다.

C: 여유 142,299,418,624바이트를 확인하고 허용된 작업 폴더의 `r2`로 다시 실행해 완료했다. 원 코드·원자료는 K: 그대로다. 다음 개발 시점에 K: 여유 26,657,849,344바이트를 확인하고 이 정식 개발 기록·메인 문서·로그에 반영했다. 원 C: 결과/기록과 실패한 K:r1은 삭제하지 않았다. [당시 반영 대기본](<C:/Users/snoop/.codex/visualizations/2026/08/14/019fffe2-e831-7f32-a7d1-2b93c5a39b2c/harmony-transition-support-2026-10-05-r2/PROJECT_DOCUMENT_UPDATES.md>)도 보존한다.

## 2. 실제 계산에서 확인한 한계

현재 점수는 완전한 화음 run과 원음표·음가를 사용한다. 경계/화음 공동 선택과 해결 credit도 이미 있다. 이번 작업은 이 기능이 없다고 주장하거나 경계를 먼저 고정하는 엔진으로 바꾸는 것이 아니다.

- `pair_features`는 선택된 앞뒤 철자 화음에 맞는 명시 성부의 인접 해결을 찾는다. 이끎음 반음 상행과 7음 순차 하행은 각각 경계당 최대 1이다. 여러 성부가 같은 종류의 해결을 보이더라도 1을 여러 번 더하지 않는다.
- 박자 기반 credit 배율은 **왼쪽 run의 길이**다. 오른쪽 화음이 실제로 얼마 동안/몇 구성음으로 지지되는지를 이 보상의 조건으로 사용하지 않는다. 미확인 박자는 원 credit을 유지하고 미확인 사실을 기록한다.
- 해당 해결을 보이는 한 성부가 있어도, 다른 성부/베이스가 그 도착 화음을 지지하는지는 별개다. 합성 검사에서는 B→C의 한 성부만 있어도 G7→C 후보에 이끎음 credit이 붙음을 재현했다. 이것은 관찰 한계이지 이 사례를 자동으로 비화성음이라고 확정한 것이 아니다.
- 같은 경계에서 같은 움직임의 중복 credit 버그는 확인되지 않았다. 여러 **다른** 경계의 보상이 경로 전체에 누적되는 것과 구별한다.
- note-time/구간 폭으로 정규화한 누락·비구성음 비용과 경계마다 더하는 비용/보상이 섞여 있다. 이 단위 차이 자체가 잘못이라고 단정하지 않고, 동일 계수의 완전 경로 비용으로 기록한다.

## 3. 새 label-blind 관찰 계약

새 모듈은 점수를 바꾸지 않는다. `observe_path(problem, ev, ids)`에 정답 화음·종지·NCT·제목·작품 ID를 입력하지 않는다. 입력 경로가 학습 정답으로 선택되었는지 여부는 trial의 별도 provenance다.

인접한 같은 철자 화음 edge들을 먼저 **완전 run**으로 합친다. 경계마다 오른쪽 전체 run과 처음 한 지역 박(전체 run 끝으로 제한)을 각각 관찰한다. 바뀌는 박자는 해당 위치의 beat unit을 적분하고, 박자가 미확인이면 처음 한 박 관찰은 null, 전체 run 관찰은 보존한다. 첫 raw edge의 끝을 완전 run 끝으로 잘못 사용하지 않는다.

각 창에 다음을 보존한다.

- 원 sounding/note ID와 원음표 전체 시간 범위, 철자, 명시 part/voice 및 voice-clock availability.
- 실제 구성음들의 합집합, 오른쪽 화음만의 구성음, 생략된 구성음.
- 각 원 onset/release로 나눈 셀의 수직 구성음 수와 정확한 음가 비중.
- 왼쪽·오른쪽 화음을 지지하는 수직 상태, 최저 sounding 음의 membership, 지속 공통음과 새 attack.
- 실제 해결 pair IDs, 기존 raw/meter-scaled credit, 기존 점수의 동일 계수 receipt.

F♯/G♭ 등의 철자는 합치지 않고 옥타브 doubling은 다른 구성음으로 세지 않는다. 쉼은 관찰된 0, 미확인 음높이는 null이다. 분산 제시로 전체 구성음이 나타나도 한순간 두 구성음이 겹치지 않을 수 있으므로 **수직 두 음 조건을 화음 탈락 필터로 쓰지 않는다**. `harmony_change_confirmed`/`nct_confirmed`는 false다. 관찰 특징을 해석 확정으로 승격하지 않는다.

## 4. 자료와 비교 조건

원270Train범위 중 이전부터 참조 경로가 존재한118범위를 그대로 사용한다. 제외152범위를 새 정답 후보로 보정하거나 조용히 버리지 않는다. 예정 범위는23전체 악장 source/15명명 기반 작품 가족·원60,129edge다. 가족 분리는 완전한 판본/중복 누출 감사를 대체하지 않는다.

다음 **저장된** 다섯 경로를 사용한다. 새 search/fit/epoch 선택은 하지 않는다.

| 경로 | 역할 |
|---|---|
| 초기 ordinary | 원 기준선 |
| 단계72 고정 ordinary | 이전 학습 모델 |
| 단계75 고정 ordinary | 최근 미채택 모델 |
| 단계75 epoch3 adversary | 마지막 방문 계수로 선택했던 학습 경쟁 경로 |
| 단계75 epoch3 target | 마지막 방문의 참조 호환 latent target |

모든 비용 receipt는 **동일한 단계75 고정 평균 계수**로 다시 측정한다. epoch3의 path를 평균 모델의 새 승자라고 부르지 않는다. adversary/target은 정답 정보를 사용한 학습 전용이며 운영 예측/독립 정확도에 포함하지 않는다. 원 두 adversary의 계산 한도 보류는 retry/부분 gradient 없이 유지한다.

원 전체 MusicXML·parent/working IR·measure revision·clock gate·전후 source provenance를 path/SHA로 연결한다. 새 excerpt ID나 clipped 음가를 만들지 않는다. 겹치는 여러 scope의 경계 발생 수는 고유 경계·고유 음표·작품 수가 아니다.

reference 진단은 source profile 계산 뒤 별도 필드에 붙인다. `reference_boundary_at_exact_time`은 root+철자 구성음 계약의 경계이며 전위만의 변화나 NCT 정답이 아니다. 시각이 맞아도 화음 이름까지 맞는다는 뜻은 아니다. 주석과 다른 경계를 확정 음악 오류로 읽지 않는다.

## 5. 검사와 실패 보완

신규17검사는 분산형, doubling, 단일 성부 해결 credit, 여러 성부의 보상 상한, 지속음/원 음가, unknown, 쉼, 변경 박자, 같은 화음 내부 raw 분할 불변성, enharmonic 철자, 불완전 path 거부, 원 IR/기존 비용 불변, 참조 진단 분리와 보류를 다룬다.

기존743검사를 포함한 **760검사/67모듈 PASS**, failure/error0,79.657586초다. 전체 repository suite는 아니다. 초기 합성 test의 pitch metadata에서 `midi_pitch` 누락, receipt key의 오기를 보완한 뒤 새 코드/검사를 봉인했다. 원 엔진이나 과거 봉인 코드는 수정하지 않았다.

회귀 결과: [검사 JSON](<K:/Music Analysis/output/harmony-transition-support-validation-2026-10-05-r1.json>). AST/UTF-8/공백 검사 신규6Python 파일 PASS. 사후 감사 완료 수치는 아래에 있다.

## 6. 실제 진단 결과와 의사결정

실제 진단의 r2는 **118/118범위,23전체 악장 source/15작품 가족·원60,129edge**,217.692133초/exit0다. 118case(압축 합계796,762바이트)에 전체 source 경로/SHA, 원 IDs/음가, 다섯 경로와 같은 계수 비용·원26특징/availability, source profile 및 별도 참조 진단을 보존했다. 590개 예정 path 중588개 존재/2개 기존 resource 보류이며, 사후 감사도 통과했다.

| 저장된 경로 | 존재 path | 참조 계약 전체 일치 | 실제 화음 경계 발생 | 참조 시각과 일치 | 참조 시각에 없는 추가 경계 | 추가 경계 중 dominant 해결 credit |
|---|---:|---:|---:|---:|---:|---:|
| 초기 ordinary |118|54|125|87|38|2|
| 단계72 고정 ordinary |118|60|113|82|31|0|
| 단계75 고정 ordinary |118|58|118|85|33|4|
| 저장 epoch3 adversary |116|0|153|7|146|2|
| 저장 epoch3 target |118|118|111|111|0|0|

target의 마지막 열은 추가 경계 자체가 없어0이다. target의 전체 일치118은 참조를 사용해 골라 둔 경로의 계약 재검산이지118개 blind 정답이 아니다. adversary는 일부러 손실이 큰 학습 경쟁 경로이므로 ordinary 정확도로 읽지 않는다. 원 Train 수치54/60/58과 경계 발생은 이전 결과와 동일하며 **새 정확도 향상은 없다**. 단계72→75의 저장 raw path 변경10범위, 시간 오류 증가4/감소3/동일111이다. 이 합계에는 경로가 바뀌지 않은 범위도 포함한다.

### 6.1 단순한 구성음 수 필터는 채택하지 않는다

단계75 ordinary의 추가33경계와 해결 credit이 있는 추가4경계 모두 오른쪽 전체 run에서 적어도2구성음이 나타났다. credit을 받은 추가4경계의 전체 합집합은3/3/3/4구성음이다. 따라서 ‘도착 화음을 다른 구성음도 지지하면 된다’는 단순 임계값은 이번 손실을 막지 못한다. 첫 한 박에서도 구성음은3/3/2/4개다.

‘왼쪽의 두 구성음 지지 시간이 오른쪽보다 길다’라는 이진 수직 비중 비교도 다섯 조건에서 사례0이다. 공통 구성음·분산 제시·창 선택 때문에 양쪽 지지가 동시에 성립할 수 있다. 이것을 학습에 도움되는 feature라고 선언하지 않는다.

반대로 참조 호환 target111경계에는 **수직 두 구성음이 한 번도 겹치지 않는 경우2개**, 오른쪽만의 구성음이 없는 경우3개가 있다. 2개는 전체 합집합에서는 적어도2구성음이 나타난다. ‘수직 두 음/새 구성음이 반드시 있어야 교체’라는 hard gate는 참조 호환 진행까지 제외한다. 실제 source 사례는 아래와 같다.

### 6.2 원음표를 보존한 Train 사례

모든 예는 source/학습 주석 계약에 따른 진단이며 확정 NCT·검수 정답이나 작품별 규칙이 아니다. 비용 차이는 새 경로−단계72 경로를 **같은 단계75 고정 계수**로 비교한 값이다. cost가 내려갔다고 음악적으로 개선된 것이 아니다.

1. **Beethoven Quartet op18-1,1악장 m210~211**, `cont_195ab0306a75a682b13e`, `[2519/4,632)`.
   - 참조 target은 F단3화음→C장3화음이며630부터632까지 C가 유지된다. 새 경로는631에서 F장3화음을 넣었다가2527/4에서 C장7형으로 돌아간다.
   -631의 E→F 직접 해결은 `sound_833aa38e8b9a → sound_ad5bcfa58a5b`로 실제 명시 성부에 있다. 새 F run `[631,2527/4)`은3구성음이 나타나며 F/A라는 새 구성음도2개다. 수직 지지 비중은 왼쪽/오른쪽 모두1/3이므로 구성음 수/두 음 지지 필터로는 구별되지 않는다.
   - 추가 leading credit 비용−.175876이 nonmember +.03438689,root motion +.033305,turnover +.03718953,run +.021208 등을 압도한다. 전체 gap−.06985413,참조 시간 오류1/9→4/9다. 참조에서 유지되는 C 안의 실제 음 진행을 대안 설명으로 비교하는 **전후 문맥/장식 유지 모델**이 필요하다.
2. **Beethoven Quartet op18-1,4악장 m111**, `cont_2cb186940b3312c2a145`, `[220,664/3)`.
   - 참조는 A7 유지다. 이전은 A를 기능적 근음으로 하는 D–F–A surface를, 새 경로는 D단3화음 근음으로 `[441/2,221)`에 둔다.
   - 실제 G→F 순차 해결 pair는 `sound_4e4dbd848530 → sound_20b842c722d9`다. 세 구성음/두 새 구성음과 오른쪽 수직 지지 비중1이므로 단순 지지 문턱을 통과한다.
   - 시간 오류5/8은 이전/새 경로 같고 gap−.002359다. 새7음 해결 credit−.044873뿐 아니라6-4 역할 비용 변화가 함께 작용하므로 ‘해결 credit만 고치면 해결’이라고 단정하지 않는다.
3. **Beethoven Sonata02-2 m3~5**, `cont_4f4f6dc881cf72de3728`, `[8,13)`.
   - 참조는 `[9,12)`의 A장3화음 뒤12에서 D장3화음이다. 새 경로는 A7을 `[9,11)`로 보고 G→F♯의 원 pair `sound_705473da2f55 → sound_c09c5b3c352e`를 근거로11에서 D장3화음으로 일찍 교체한다.
   - `[11,12)`에 D 화음 두 구성음이 나타나고 `[11,13)`에는 세 구성음/두 새 구성음이 나타난다. gap−.00907884지만 시간 오류7/10은 이전과 같다. 이것은 준비/지속·화음 아래에서의 음 역할과 **교체 시점 경쟁**을 따로 설명해야 한다는 사례다.
4. **Mozart K281-2 m61~63**, `cont_06279642b89b17cd3fe0`, `[545/6,94)`.
   - 참조 마지막 `[187/2,94)`은 C단3화음인데 새 경로는 E♭장3화음→A♭장7형으로 나눈다.281/3에서 G→A♭ 원 pair `sound_42924f8dcacb → sound_66e77479acf0`가 있고 오른쪽 네 구성음이 모두 나타난다.
   - gap−.18221622이며 시간 오류6/19은 이전과 같고 전체 boundary loss는 소폭 줄었다. 추가 경계가 있다는 이유로 전체 경로가 무조건 퇴행했다고 세지 않는다. 참조의 국소/기능적 해석과 실제 surface chord의 구별도 남는다. 이 sample의 학습 adversary resource 보류는 원상태로 보존했다.
5. **Mozart K280-1 m18**, `cont_d49ef2818a4d1118a324`, target `[53,54)`.
   - 원 source는 E♭,C,B♭가1/3quarter씩 차례로 나타난다. target C단3화음의 구성음 E♭/C 두 개가 분산 제시되고 B♭는 해당3화음의 구성음으로 세지 않는다. 그 음을 확정NCT라고 지우지 않는다.
   - 원 IDs `sound_30814717ce15`, `sound_9d4f8a909509`, `sound_2640f39f9b99`와 source 음가를 보존했다. 어느 순간도 target 구성음 두 개가 겹치지 않는다. 수직 두 음 관문은 이 참조 호환 경로를 제거한다.
6. **Mozart K281-3 m112**, `cont_9e8aa7e3ced171e52304`, target `[449,1349/3)`.
   - C와B♭가각1/3quarter로 순서대로 나타난다. 원 `sound_eac60c920bdf`, `sound_6d41da604370`는 C7 target의 두 구성음이지만 서로 겹치지 않는다. 이 역시 수직 필터의 반례이며 target이 참조를 사용한 조건이라는 점을 유지한다.

각 case는 이 폴더 `cases/<sample_id>.json.gz`에 있다. 관찰/전체 source/원 경로와 비용이 함께 있으며 악보는 `full_source_paths.whole_musicxml_path`로 전체를 재현할 수 있다. 원음표를 특정 짧은 화면 범위로 잘라 버리지 않았다.

### 6.3 다음 개발은 문맥 경쟁 표현을 먼저 구현한다

이 단계의 결론은 **새 support 숫자 몇 개를 바로 학습하거나 해결 credit에 수직 관문을 붙이지 않는다**는 것이다. 다음은 원 Train에서 ‘화음 유지+장식/성부 진행’과 ‘실제 새 화음’이라는 두 설명이 같은 원음표에 대해 경쟁하도록 표현한다.

1. 인접한 세 완전 run의 화음/음가와 실제 성부를 확인해, 중심 구간의 원음이 앞 화음 아래에서 준비·진행·되돌아감으로 설명될 수 있는지 기록한다. 앞뒤 같은 화음이라는 사실만으로 중간 화음을 장식/NCT라고 확정하지 않는다.
2. 기존 교재 기반 조건부 passing/neighbor/지연·선행·이중 보조 후보를 가져오되, **실제로 선택되는 앞뒤 화음**, 명시 성부의 원 연결, 원 박자/붙임줄/음가 아래서 성립하는 설명만 연결한다. 미지원 성부/국소 조성은 null/보류이며 벌점0이라는 확정 사실로 만들지 않는다.
3. 같은 음을 원 비구성음 비용에서 삭제하지 않고, 지속 베이스·남는 구성음·새 화음의 독립 구성음 제시·분산형·회귀/확장·7음의 존재를 함께 대조한다. genuine secondary/짧은 화음/근음 생략/분산형을 반례로 반드시 포함한다. 하나의 물리적 사건에 동시에 양립할 수 없는 설명을 중복 보상하지 않는다.
4. 우선 Train에서 실제 대조가 생기는지와 반례 손실을 점검한다. 새 공동 점수에 soft interaction으로 연결한 뒤 사전 고정 fit→ordinary 재선택→Dev 확인을 진행한다. Dev가 나쁘다고 거기서 계수/threshold/최고 epoch를 다시 고르지 않는다.

3/7화음 축소·기능적6-4와 국소 조성 문제를 이번 단순 transition profile로 해결했다고 주장하지 않는다. 독립Test/공개 모델 비교, 장문 후보 보류, 전체 Roman/전위/종지/NCT 정확도·운영/구조·작곡편곡 연결도 남아 있다.

### 6.4 봉인과 감사

- Report SHA: `7e9830ebab3a14dfd466fce18effce19f66bd6cb5e83d7f2a499a12198e9a172`.
- Contract SHA: `25e73acc5da63cefff68ab089287f7d9329243c44a041cbfe6324763bb2689a5`.
- 기존 고정 모델 SHA: `2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf`.
- 회귀 SHA: `393de7f3eb928fa9cd9777de6b9b3c9a3911d7b612836ddea209a97e3fda5eb1`.
- 이번 run code pins424개이며 완료 후 code/test/script 변경0. 감사는 모델/문맥/권리/SHA, 모든 저장 경로와26특징·동일 계수 비용, 원음표 profile와 별도 참조 진단/집계를 재생했다.
- **감사 PASS/exit0:** 2,824고유 SHA,2,816봉인 입력 재로드,118범위/23전체source/원60,129edge,588저장 경로·동일 계수 비용,620경계 source profile,원2보류와 모든 집계 재생. 새 search/fit/Dev 사용0, source Core와 기존 점수 불변을 확인했다.
- Audit SHA: `9f302f80c00a241876502a367e17b2c5b5cd270e3464fe8725c08aa9bfd77cb4`.
- [완료 report](<C:/Users/snoop/.codex/visualizations/2026/08/14/019fffe2-e831-7f32-a7d1-2b93c5a39b2c/harmony-transition-support-2026-10-05-r2/report.json>), [실행 계약](<C:/Users/snoop/.codex/visualizations/2026/08/14/019fffe2-e831-7f32-a7d1-2b93c5a39b2c/harmony-transition-support-2026-10-05-r2/run-contract.json>), [사후 감사](<C:/Users/snoop/.codex/visualizations/2026/08/14/019fffe2-e831-7f32-a7d1-2b93c5a39b2c/harmony-transition-support-2026-10-05-r2/post-seal-audit.json>). r1의 부분 출력과 r2의 완료 산출물을 구별한다.

## 7. 재현과 보존

새 파일은 [관찰 모듈](<K:/Music Analysis/src/musicanote_harness/harmony_transition_support.py>), [Train runner](<K:/Music Analysis/src/musicanote_harness/harmony_transition_support_trial.py>), 두 `tests/test_harmony_transition_support*.py`, [validation](<K:/Music Analysis/scripts/validate_harmony_transition_support.py>), [audit](<K:/Music Analysis/scripts/audit_harmony_transition_support.py>)다.

K: 프로젝트에서 `PYTHONPATH=src;tests`, `PYTHONIOENCODING=utf-8`을 설정하고 `.venv/Scripts/python.exe -B`로 runner의 `--output`에 **존재하지 않는** 여유 공간 경로를 준다. 감사는 같은 Python으로 `scripts/audit_harmony_transition_support.py --root <output>`이다. 새 search/fit 없이 원 manifest/source/model/코드 SHA와 전체 저장 경로의 비용·profile·집계를 재생한다.

NC 로컬 비상업 연구 계약은 그대로다. 원 manifest의 운영 학습/외부 API/재배포 미승인을 승인으로 덮어쓰지 않는다. UI/Core/원주석·MusicSearch/Composition·Claude Phrase/Motif·서버·다른 dirty 파일·Git 변경0, merge/commit/push0다.
