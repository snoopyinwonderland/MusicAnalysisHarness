# HARM-DEV-20261005-78 — 전후 화음 문맥의 유지/교체 경쟁 표현

화성 분석 **개발 기록**이다. 단계77의 단순 구성음 수 관문이 실제 오류를 구별하지 못한 결과를 따라, 원음표·앞뒤 화음·다른 성부를 함께 비교하는 표현을 구현한다. 인수인계 문서나 운영 엔진 배포 기록이 아니다.

## 1. 범위와 완료 기준

같은 원 후보망·동일 초기/단계72/단계75 ordinary 및 저장 epoch3 adversary/target에서 새 문맥 벡터를 추출한다. 학습 target은 분석 예측이 아니고 adversary는 손실을 찾기 위한 저장 경로다. 새 특징이 실제 Train 대조에 정보를 주는지 먼저 측정하며, 현재 이 벡터에는 가중치가 없고 새 decoder/선택/fit/Dev 평가/화면 변경은 하지 않는다.

원270Train 중 참조-compatible 경로가 있었던118구간을 그대로 사용하고 나머지152제외 상태와 기존2resource 보류를 보존한다. 23전체 악장 source/15명명 작품군·원60,129edge다. 전체 source가 연결돼 있다는 말은 전체 작품 모든 구간의 정확도를 측정했다는 뜻이 아니다. 중첩 scope/경계/음표 수는 고유 사례·곡 수와 다르다.

지난 단계77 C: 완료 결과는 삭제하거나 다시 봉인하지 않았다. K: 여유 약26.66GB를 읽기 전용으로 확인한 뒤 [정식 단계77 개발 기록](2026-10-05-transition-support.md), 메인 문서·로그에 반영했다. K:r1의 공간 부족 실패와 C:r2의 완료 이력 모두 보존한다.

## 2. 기존 코드와 이번에 추가한 것

- 기존 `harmony_evidence_scoring`의 짧은 약박·한 동일 화음 run 안 경과/보조음 조건은 유지한다.
- `harmony_joint_nct_scoring`은 과거 연구 코드로, 실제 선택된 두 화음 아래 transition 도착만 비교하며 미래 완전 run 전체를 점수에 넣는 이번 벡터와 다르다.
- `RootReturnContext`·`harmony_member_timing`의 준비/도착·원음표 시간 관문은 변경하지 않는다. 원 code seal/26특징/계수/기존 비용은 그대로 검산한다.
- 새 `harmony_context_competition` v0.1은 **완료된 왼쪽 run + 오른쪽 run + 다음 run**의 실제 선택된 화음에서 ‘왼쪽 화음을 계속 유지한다면’의 조건부 설명을 평가한다. 전 음형을 반복 수만으로 세지 않고 실제 source sound 음가의 합집합을 사용한다. 실제 corpus를 본 뒤 발견한 current anchor 관문의 자기 확인 문제는 원 v0.1을 보존한 별도 `harmony_context_competition_v2` v0.2에서 교정한다(§4.1).
- `harmony_context_competition_trial`과 별도 검사/validator/auditor를 추가했다. 원 Core/XML/주석/Claude Phrase·Motif/운영 서버/API/화면은 수정하지 않는다.

## 3. 음악적 계약 — 선율만으로 화음을 취소하지 않는다

### 3.1 경과·보조·이중 보조의 조건부 형태

명시된 같은 `(part_id, voice_id)` 성부에서 실제 sounding event가 정확히 이어질 때만 3음 또는4음 형태를 검사한다. 붙임줄의 continuation을 새 attack으로 만들지 않고 원 sounding event/source note IDs/원 spans를 보존한다. 동일 성부의 중첩·쉼·grace barrier·source clock 거부를 건너뛰지 않는다. 반음/온음 거리와 diatonic spelling을 함께 확인한다.

- 경과형: 두 방향의 순차 진행, 가정한 유지 화음에서 두 anchor가 구성음이다. 실제 선택 경로에서는 anchor의 일부 음가가 비구성음으로 해석될 수 있으며 그 상태도 별도로 저장한다. 양쪽 해석을 모두 확정 사실로 만들지 않는다.
- 보조형: 동일 철자·음고로 돌아오는 순차 상행/하행 형태이며 중간음은 가정한 유지 화음의 비구성음이다.
- 이중 보조형: 동일 anchor를 중심으로 반대편 위/아래 이웃 음 두 개를 거쳐 복귀한다. 가운데 두 음 사이 도약은 허용하지만 처음/끝의 순차 관계와 실제 연결을 확인한다.

**장식에 맞는 형태가 있어도 NCT나 화음 유지로 확정하지 않는다.** 같은 선율의 보조형이 실제 IV/V 등 화음 교체 위에 놓일 수 있다. 다른 성부의 새 구성음, 남는 비구성음, 이어지는 lowest를 별도로 남겨야 한다.

짧은 약박만 허용하는 hard filter를 추가하지 않는다. 중간음의 지역 박자 기준 길이/metric strength를 receipt에 따로 저장한다. 긴 음도 형태상 가능하지만 자동 장식 판정은 아니다. 끝음의 source 전체 음가까지 비교 문맥에 들어와야 하며 범위 밖 미래 화음을 빌리지 않는다. 따라서 범위 시작 전 준비·범위 밖 해결은 이번 표현의 명시적 미지원이다.

### 3.2 일곱 가지 점수 후보 특징

| 특징 | 의미 |
|---|---|
| `hold_explained_step_exposure` | 가정한 유지 화음에서 조건부 순차/회귀 형태로 설명 가능한 중간음의 실제 overlap 음가 |
| `hold_remaining_nonmember_exposure` | 그 설명으로 덮이지 않는 유지 화음의 비구성음; 다른 성부도 그대로 포함 |
| `reclassified_ornament_member_exposure` | 위 중간음을 실제 선택된 새 화음은 구성음으로 해석하는 충돌 |
| `selected_new_exclusive_unassigned_exposure` | 새 화음에만 속하는 새 attack 중 장식 형태에 배정되지 않은 overlap 음가; 독립 화음 지지로 **확정**한 뜻은 아님 |
| `continuing_left_member_exposure` | 경계를 넘어 실제로 계속 울리는 왼쪽 구성음 |
| `continuing_left_lowest_coverage` | 실제 lowest가 위 지속 구성음인 시간; 구조적 베이스 확정이 아님 |
| `dominant_credit_with_hold_conflict` | 기존 dominant 해결 credit의 원 pair가 위 조건부 장식 설명과 겹치는 상호작용; 기존 credit을 삭제하지 않음 |

음가 exposure는 원 scope의 실제 sounding overlap note-time으로, lowest coverage는 원 scope의 quarter-time으로 정규화한다. 모두 Fraction이며 중간 float 오차를 넣지 않는다. 같은 source sound를 여러 형태가 공유해도 한 구간 음가는 한 번만 세고 같은 종류의 기존 dominant credit도 boundary마다 한 번만 센다. 다른 오른쪽 run들은 겹치지 않는 `[start,end)`이므로 음가를 중복하지 않는다. raw edge를 같은 signature로 세분해도 completed-run profile이 같다.

### 3.3 unknown과 상반되는 설명

pitch/clock/명시 성부가 없거나 필요한 비구성음 lane이 polyphonic이면 조건부 특징은 `null`/availability=false다. 보이는 부분 합은 receipt일 뿐 학습 delta에는 쓰지 않는다. 이미 유지 화음의 구성음인 다른 성부의 중복 표기는 NCT 비구성음 domain을 불명으로 만들지 않는다. 도착 음이 없는 transition domain은 알려진0이지만 음악에 장식이 없다는 뜻은 아니다.

지역 박자를 모르면 geometry와 실제 source 음가는 남기고 meter-graded dominant conflict는 unavailable이다. source key/local tonic을 추측하지 않는다. 이 표현은 지연음·선행음·페달·도약/장식된 비인접 해결 전체 NCT 분류기를 완성하지 않는다.

가정한 유지 화음은 이전 **실제 선택 signature**이며 후보망에 새 화음을 삽입하지 않는다. 이 가정이 원 raw edge cap 아래 합법적 선택 경로로 존재한다고 보장하지 않는다. future exact joint search에는 기존 graph/cap을 통과하는 경로만 허용해야 한다.

## 4. 실제 실행·검사·자료 진단

신규20검사는 통과했다. 초기 합성 검사2개에서 기존 receipt의 `kind`를 feature 이름과 직접 비교해 충돌 credit을0으로 읽은 오류가 있었다. 실제 receipt는 family 접두부+`_leading_tone_to_selected_target`/`_seventh_to_selected_member`이므로 기존 형태에 맞춰 교정했고, 같은 출처 pair를 여러 번 출력해도 credit이 증식하지 않는 검사도 통과했다. 실제 corpus 실행 전에 교정했다.

이전760+신규20=780관련검사/69모듈 PASS, failure/error0·85.920622초다. repository 전체 suite나 음악적 정확도 검사가 아니다. 신규6Python AST/strict UTF-8/공백 검사 PASS다.

최초 actual r1에서 첫 구간이 수 분 동안 완료되지 않았다. 작품 전체 모든 geometry에 source-clock 관문을 선행 적용하는 비효율이 원인이었다. 해당 실행만 Ctrl-C로 중단해 exit1·완료report 없음이며 r1의 계약은 실패 이력으로 보존한다. 확인용 CIM 프로세스 조회는 권한 거부됐으며 외부 프로세스 종료/권한 변경은 하지 않았다. 실제 원음표·scope·관문 조건을 바꾸지 않고, 먼저 해당3-run/선택 화음/실제 중간음 조건을 만족한 형태만 시간 검증하도록 옮겼다. 동일 source의5arm은 Context와 관문 결과를 공유한다. 검증을 생략하거나 범위 밖 음을 지우는 수정이 아니다. lazy 검증/공유/다른 source Context 거부 검사1개를 추가했다. 수정 후 새r2/회귀 검사로 다시 실행하며 기존r1은 완료로 사용하지 않는다.

### 4.1 실제 사례로 current anchor 관문의 자기 확인 문제를 발견

r2(v0.1)는118scope/588path/620transition/110조건부형태를 완료했다(203.647220초). 781관련검사/69모듈 PASS·79.732063초, 2,951SHA/2,944봉인 input·23source/원60,129edge/588원 비용·벡터·delta·집계 재생 감사 PASS다. 현재 선택 경로에서도 anchor가 구성음이어야 한다는 보수적 관문이 있었고, 단계75 ordinary의 extra-time dominant conflict는1/4개만 관찰했다.

원음표를 보니 Quartet op18-1 mv1 m211의 `sound_833aa38e8b9a` E3 `[2523/4,631)` → `sound_ad5bcfa58a5b` F3 `[631,2525/4)` → `sound_5e0cb9712c63` G3 `[2525/4,1263/2)`는 순차 상행이었다. E-F-E 보조형이 아니다. 현재 잘못 삽입된 F화음은 G를 비구성음으로 읽으므로, v0.1의 anchor 관문이 ‘C화음을 유지하고 F를 경과형으로 설명하는’ 경쟁 가설까지 차단했다. 이는 원 주석을 맞추기 위한 작품 예외가 아니라 **현재 선택과 경쟁 해석을 같은 정답으로 강제하는 계약 문제**다.

v0.2는 두 anchor가 **가정한 유지 화음의 구성음**이어야 하는 조건을 유지한다. 대신 실제 선택 경로의 anchor membership을 veto로 쓰지 않고 source event ID/선택 화음/실제 overlap span별 대안으로 기록한다. 다른 성부의 남는 음, 현재 새 화음의 새 구성음, 지속 베이스, 원 해결 pair를 그대로 비교한다. candidate insertion/기존 score 변경/자동 NCT 확정은 없다. 원 v0.1/완료 r2와 검사는 보존하고 별도 v2 module/trial/validator/auditor/검사8개를 추가했다.

v2의 첫 합성 검사1개는 G를 유지하는 대조에서 모든 형태가 없어야 한다고 잘못 기대했다. E-F-G는 탈락하지만 별도의 G-A-B 경과형은 성립하므로, F는 설명되지 않고 A의 조건부 설명은 보존되는 검사로 교정했다. 규칙을 느슨하게 고친 것이 아니다. 8개 검사는 통과했다. 새r3/전체 회귀/사후 감사를 다시 수행한다.

### 4.2 v0.2 실제 corpus 완료 결과

r3는118scope/23전체 source/15작품군·원60,129edge에서588경로/620전이/144조건부 형태를 완료했다(202.495282초/exit0). 형태는 경과형55/보조형85/이중 보조형4이며 중첩 scope/path별 관찰 수이지 고유 NCT 정답 수가 아니다. 기존2adversary 보류를 다시 탐색하지 않았다. 원 비용/경로/학습 loss는 그대로이며 새 정확도 향상은 측정하지 않았다.

| 저장 경로 조건 | 완전 경로 | 전이 | 참조 시각의 조건부 형태 | 추가 시각의 조건부 형태 | 알려진 dominant conflict(참조/추가) |
|---|---:|---:|---:|---:|---:|
| 초기 ordinary |118|125|24|9|1 / 2|
| 단계72 ordinary |118|113|23|8|0 / 0|
| 단계75 ordinary |118|118|25|11|1 / 2|
| 저장 epoch3 adversary |116|153|0|18|0 / 0|
| 저장 epoch3 target |118|111|26|0|0 / 0|

참조 경계의 정확한 **시각**과 맞더라도 화음 이름/NCT가 정답이라는 뜻은 아니다. target의26형태/17경계는 특히 장식과 실제 화음 교체가 함께 있을 수 있다는 반례이며, 형태가 있으면 경계를 무조건 지우는 규칙은 미채택이다. 단계75의 기존 추가 dominant credit4개 중2개의 알려진 상호작용을 관찰했다. Sonata02-2에는 관련 원음표 형태가 있으나 다른 비구성음 lane의 겹침 때문에 unavailable로 남고, Quartet01-4에는 조건을 충족하는 완결 형태가 없었다. 4개 모두를 해결한 결과가 아니다.

### 4.3 실제 사례와 남는 반대 근거

- **Quartet op18-1 mv1 m211 / `cont_195ab0306a75a682b13e`:** 앞서 적은 E3-F3-G3를 C유지 아래 경과형으로 비교한다. 실제 선택 F화음에서는 G가 비구성음이라는 대안도 보존한다. F→G의 두 음가가 바뀌는 부분을 삭제하지 않는다. F화음 구간 `[631,2527/4)`에서 설명된 F=`sound_ad5bcfa58a5b`와 남는 A=`sound_62ac7196f1c0`를 구별한다. 전체 경로의 새 ‘설명/구성음 충돌’은 각각1/28, dominant conflict=1이지만, A와 다른 전이의 남는 음도 모두 저장한다. 화음 유지나 F의 NCT 확정은 아니다.
- **Mozart K281-2 / `cont_06279642b89b17cd3fe0`:** Ab-G-Ab 보조형에서 G=`sound_42924f8dcacb`, 뒤 G-Ab-G에서는 Ab=`sound_66e77479acf0`의 경쟁 설명을 관찰했다. `[187/2,281/3)`은 **참조 시각 경계**이면서 conflict가 있고 `[281/3,94)`은 추가 시각의 conflict다. 다른 음 `sound_e22ec4390bc0` 등을 남겨, 같은 음형 신호가 정답 시각과 추가 시각 모두에 나타나는 반례로 보관한다. 참조와 시각 일치인 현재 선택 Eb화음이 정답이라는 뜻은 아니다.
- **Sonata02-2 / `cont_4f4f6dc881cf72de3728`:** G-F#-E의 `sound_705473da2f55` → `sound_c09c5b3c352e` → `sound_6902e9295e4d`는 A7유지 아래 F#을 경과형으로 설명할 수 있다. 실제 D화음은 E를 비구성음으로 해석한다. 그러나 다른 원음표 `sound_45054c8f4762`의 lane 중첩 때문에 전체 관련 특징은 **null**이다. 관찰된 부분 합을 완전한0 또는 확인된 NCT로 바꾸지 않는다.

### 4.4 학습에 쓸 수 있는 정보량과 한계

현재 단계75 ordinary와 stored target의118대조에서 새7특징 중 jointly available 비0 delta가 있는 것은29개다(모두 기존 오류 구간).27개는7항 모두 available,2개는 일부 항만 available다. 원60오류 중14개는 새7항이 모두 알려진0 delta로 같고17개는 일부 unknown이면서 알려진 delta가 없다. 기존58정답 중44개는 모두 known/동일,14개는 부분 unknown/알려진 동일이다. **새7특징만으로60오류를 모두 풀 수 없으며 기존26항을 대체하지 않는다.** 전체7항의 jointly available 대조85개/모두0 delta58개라는 집계에 기존 오류14개도 포함돼 있다.

단계72 대조도 알려진 비0 delta29개, 초기32개, 의도적 손실 adversary84/116개다. adversary의 큰 숫자를 일반 추론 정확도로 읽지 않는다. 다음 제한 학습은 available 항만 사용하고 미지원 음형·잘못된 단일 화음 선택·근음/7음 생략 및 국소 조성 문제를 과장하지 않는다.

신규29+기존760=789관련검사/70모듈 PASS, error/failure0·81.217869초. 신규11Python 파일의 AST/UTF-8/공백 검사를 통과했다. 실제 실행을 시작한 뒤 해당 코드/검사/스크립트를 수정하지 않았다. 사후 감사는 아래 봉인 절에 기록한다.

## 5. 다음 연결 순서와 보존 조건

1. 실제 Train 대조에서 jointly available delta와 기존 점수 credit 충돌을 확인한다. 무정보/unknown 특징은0으로 채워서 학습하지 않는다.
2. 정보가 있는 특징의 soft 점수 방향/범위를 Train에서 정한다. 장식 형태가 보인다는 이유만으로 새 화음을 취소하는 hard rule은 금지한다. 분산형·생략된 근음·실제 짧은 secondary·진짜 A→B→A의 반례를 유지한다.
3. 이번 표현은 다음 **완전 run의 끝 시각**까지 형태를 관찰한다. v0.2의 다음 화음 signature는 선택 대안 receipt에 남지만 anchor membership의 veto/수치 조건으로 쓰지 않는다. 기존 arrival-only pair decoder에 그대로 넣으면 상태 압축/동점 비교가 잘못될 수 있다. 지난 run을 보류해 문맥 비용이 확정될 때 더하는 상태 계약과 마지막 run flush를 설계하고 tiny DAG 전수 검사/같은 signature 분할 불변부터 검증한다. 기존 cap/2M 한도를 유지하고 원 graph에 없는 유지 후보를 넣지 않는다.
4. 학습 후 original ordinary fresh 선택을 해야 선택 성과라고 말할 수 있다. target/adversary 또는 저장 pool의 비용 차이를 일반 정확도라고 보고하지 않는다. 고정 뒤 별도 Dev를 대조하고 운영 승격은 그 다음이다. 이미 노출된 Dev의 coefficient/threshold/epoch 튜닝은 하지 않는다.

NC 로컬 연구·출처/라이선스 SHA 계약과 기존 운영 학습 미승인을 유지한다. 자동 인간 승인/확정 gold 생성/원주석 수정0. Core/원 XML/IR/IDs·구조/Claude Phrase·Motif·MusicSearch/Composition·서버·Git·별개 dirty 보존이다. API/merge/commit/push0이다.

## 6. 봉인·사후 재생 감사·재현

v0.2의 사후 감사 PASS/exit0: 2,954고유SHA·2,944봉인 input을 확인하고118scope/23whole-source/원60,129edge·588경로/원 비용/벡터·620문맥 전이·144형태·원2보류·jointly available delta/모든 집계를 재생했다. 새 fit/search/Dev 실행은 없고 Core와 기존 score가 같음을 확인했다. 입력/코드/산출물 pins의 중복 경로를 합친 수이며 작품 수와 다르다.

- [완료 r3 report](../../../output/harmony-context-competition-2026-10-05-r3/report.json): `f2cec47280f3101a4b56b51c655ec7e8ec018b7d696b34b71022dc7d86583924`.
- [사전 실행 계약](../../../output/harmony-context-competition-2026-10-05-r3/run-contract.json): `2e5bef988d7442a615d3017681c81e3c04c515c93048500ec332d53d7ed8f7dc`.
- [사후 감사](../../../output/harmony-context-competition-2026-10-05-r3/post-seal-audit.json): `5d44c73906a89db05c00ee25b53fb8d04ff930268b965941bc90642701a9c286`. 감사 코드 SHA는 `1e6e4e638a97f3f8d650784aefbee59e1c49d530e682aa4e79edb834b1a693b9`다.
- [789검사 결과](../../../output/harmony-context-competition-validation-2026-10-05-r3.json): `b2e64ce4484109ecba14352ded7abe8669a885ff785ddf853899d2a75f7125ac`.
- 기존 모델 SHA `2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf` 그대로다. 새로운 모델을 고정하거나 운영에 적용한 것이 아니다.
- [v0.1 완료 r2 report](../../../output/harmony-context-competition-2026-10-05-r2/report.json): `6e11acbaf301ee3cdabd6b192cfe98cc57bd77d89c9abab917a630b1ee31aef3`; [r2 감사](../../../output/harmony-context-competition-2026-10-05-r2/post-seal-audit.json) `3b9c249f7bd2ef60e8dd95703ca3957c4175303275b450dcada8a5c36188c1a3`. 실패 r1/strict 완료 r2/대안 교정 완료 r3를 혼동하지 않는다.

11새 Python 파일은 원 v0.1 module/trial, v0.2 [관찰 module](../../../src/musicanote_harness/harmony_context_competition_v2.py)/[Train trial](../../../src/musicanote_harness/harmony_context_competition_trial_v2.py), 검사3파일, validator2/auditor2다. 모두 해당 actual 전에 확정했으며 봉인 후 수정0이다. `docs/harmony/README.md`·개발 로그·이 상세 기록을 함께 갱신하고 인수인계 문서는 이번에 수정하지 않았다.

다음 명령은 `K:/Music Analysis`에서 실행한다. 재실행 output은 **존재하지 않는 새 경로**를 쓴다. 이미 완료한 폴더의 감사 파일을 덮어쓰지 않는다.

```powershell
$env:PYTHONPATH='src;tests'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_context_competition_v2.py --prior-validation output/harmony-context-competition-validation-2026-10-05-r2.json --output output/harmony-context-competition-validation-replay.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_context_competition_trial_v2 --output output/harmony-context-competition-replay
.\.venv\Scripts\python.exe -B scripts/audit_harmony_context_competition_v2.py --root output/harmony-context-competition-replay
```

이 단계는 음악적 해석을 확정하기 전 **경쟁 설명/학습 가능한 정보/남는 모호함을 보존한 구현**이다. 모든 화음·전위·국소 조성·종지·NCT 정확도, 독립 Test/공개 모델 비교, 운영/작곡·편곡 연결은 별도 완료 기준으로 남는다.
