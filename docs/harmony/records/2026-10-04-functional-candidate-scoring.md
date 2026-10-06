# J2e — 6–4 기능적 후보와 선택된 다음 화음의 해결 근거

기록 ID: **HARM-DEV-20261004-53** · 2026-10-04. [J2d 음악적 근거 점수](2026-10-04-musical-evidence-scoring.md)의 후속이며, 원 후보 공급을 별도로 확장하고 같은 개발 분모에서 실제 선택을 비교한다. 화성 개발 문서다. 운영 배포나 교재 독해 완료를 분석 정확도와 혼동하지 않는다.

## 1. 목적과 일반 규칙

J2d에서 원주석 `V(64)/vi`의 기능적 root와 표면 3화음 root가 다르다는 병목을 확인했다. 이를 특정 작품의 답으로 삽입하지 않고 다음 일반 규칙을 구현한다.

1. 원 major/minor 3화음과 원 음표·철자·time·blocker는 보존한다. 원 후보의 구성음 모두가 실제 구간의 합집합에서 관찰되고, 그 5음이 최저 지속음인 양의 시간 셀이 있으면 **dominant-origin 6–4 후보**를 추가할 수 있다. 합집합이 곧 동시 수직화음이라는 주장은 하지 않는다. `surface_root_spelling`과 `analysis_root_spelling`을 별도 보존한다. 조표·mode hint·작품 제목·원화성 label로 만들지 않는다.
2. 후보 추가만으로 기능이 확정되지 않는다. 추가 해석에는 고정 복잡도 비용을 부여한다. 현재 실제로 **선택한** 다음 화음과의 관계에서만 기능적 pair 점수를 받는다. 가능한 미래 후보가 존재한다는 이유만으로 보상을 주지 않는다.
3. 6–4 → 5–3/7: 경계 직전의 실제 마지막 양의 셀과 경계 도착 음군을 대조한다. 표면 6–4 구성음과 다음 dominant 구성음이 관찰되고, 같은 철자·register의 최저음이 동일 sounding event 또는 clock-consistent 같은 part/voice의 직접 재타격으로 유지되면 약한 조건부 근거다. 양의 음가를 임의로 늘리지 않는다. 추가로 clock-consistent 단선 explicit voice의 4→3 및 6→5가 직접 연결되면 별도 근거다. 다성 voice에서는 상성부 연결을 임의로 맞추지 않는다. **이 근거는 cadence 판정이 아니다.**
4. Dominant/leading-tone family → 목표 화음: 교재 Unit26의 철자 기반 `hypothesis()`를 재사용한다. 다음 선택된 major/minor 3화음, 또는 M/m triad core를 가진 7화음을 목표로 V/V7/vii/vii7/half-diminished7 관계를 비교한다. 실제 leading tone의 반음 상행 및 실제 7음의 하행 순차 해결을 source event ID로 연결한다. 임시표는 필수조건도 충분조건도 아니다. **local key가 아직 없으므로 primary/Secondary 여부는 unresolved**이며 tonicization/modulation을 확정하지 않는다.
5. 연결이 없거나 다성·source clock이 모호하면 근거를 주지 않는다. 미탐지는 기능 부정의 벌점이 아니다. 비구성음 노출을 면제하거나 NCT 정답으로 바꾸지 않는다. 원 candidate blocker 비용도 유지한다.

기존 규칙 코드: [Unit11](../../../src/musicanote_harness/cadential_six_four.py), [Unit20](../../../src/musicanote_harness/six_four_context.py), [Unit25](../../../src/musicanote_harness/seventh_context.py), [Unit26](../../../src/musicanote_harness/applied_chords.py). 기존 supplied-hypothesis audit 함수나 원주석 adapter를 blind inference로 호출한 것은 아니다. Unit25/26의 chord/hypothesis vocabulary와 실제 source-bound geometry를 연결했다. 교재 규칙의 metric/형식/지연·전이 해결 등 전체 조건을 완전히 구현한 것은 아니다.

## 2. 구현 계약

- 새 [functional scorer](../../../src/musicanote_harness/harmony_functional_scoring.py)와 [동결 비교 실행기](../../../src/musicanote_harness/harmony_functional_scoring_trial.py). 원 scorer/생성기 파일은 변경하지 않는다.
- Source/full IR content SHA·sound/source-note chain·attack·철자/octave/MIDI·tied clock과 원 artifact의 physical SHA를 확인한다. full source clock이 깨진 voice는 direct link에서 제외한다. grace의 performed time은 추정하지 않는다.
- `supply()`는 원 edge tuple 뒤에 새 대안만 붙인다. points, 원6 raw segment cap, 기존 보류와 blocker를 유지한다. 같은 span/signature/blocker 새 후보를 중복 생성하지 않는다. 원 source/Core/annotation에는 기능적 root를 쓰지 않는다.
- 공동 decoder의 상태는 endpoint/raw-count/run-start/spelled-signature다. 인접 동일 signature를 합집합 run으로 계산하고, 현재 완료된 왼쪽 run에서 다음 선택 onset의 pair 근거를 점수에 넣는다. 도착음의 원 sounding span은 다음 raw edge보다 길어도 보존한다. 다음 edge의 우연한 잘림 때문에 도착 근거가 사라지지 않는다.
- Fraction primitive cost를 정확한 common-denominator 정수 단위로 계산한다. 반올림/float 점수가 아니다. 2,000,000 transition cap에 도달하면 근사 winner 대신 보류한다. beam/24개 답안 pruning이나 cap 확대는 없다.
- Confidence/calibration/human validation/functional verdict/cadence는 제공하지 않는다. 선택된 분석도 미학습 hypothesis다.

### 실행 전 고정한 새 점수

| 항목 | 비용 |
|---|---:|
| 기능적 6–4 해석 복잡도/run | +1/20 |
| 6–4 표면 + 실제 최저음 유지 | −1/10 |
| 추가 4→3 및 6→5 direct geometry | −1/20 |
| dominant family leading tone → 선택된 목표 근음 | −1/10 |
| dominant family seventh → 선택된 구성음 하행 step | −1/20 |

J2d의15 관측 특징/고정 비용을 유지한다. 새 비용은 본 corpus 결과 전에 고정했으며 train fitting이나 Dev tuning이 아니다. `functional_supply_control`은 같은 후보/복잡도 비용에서 pair bonus를 끄고, `functional_supply_and_resolution`은 켠다. 원 J2d 결과와 두 새 arm을 함께 보고한다.

## 3. 검증과 실행

새 기능 검사25 + 실제 파일 runner 검사5, 관련 기존151 = **181 PASS / 1.098초**. Surface/functional root 분리, source hash, 원 후보 불변, spelling/microtone 보류, 완전 관측 요구, 실제 6–4 및 dominant-family 해결, polyphonic link 보류, tied clock 오류, key/label/title 비사용, 7화음 목표, whole/split 비용, exhaustive 최적해, exact cap/자원 보류, 물리 변조, gold 변경 시 prediction 불변을 검사했다.

20문맥 smoke는 실행 경로·자원 확인용이며 `complete=false`다. 39.592초/exit0,3악보/2작품군에서 실행됐다. Smoke 결과를 전체 정확도로 사용하거나 가중치 선택에 사용하지 않는다. 코드 검토에서 다음 V7도 applied family의 목표가 될 수 있도록 7화음의 triad core 지원을 추가하고 고정 비용은 변경하지 않은 뒤 전체 실행을 시작했다. Smoke는 최종 코드의 전체 결과가 아니다.

전체322문맥 실행을 **449.734초/exit0**으로 완료했다. 원자료/원 후보/기존 score·예측/권한/운영UI·서버/Git는 변경하지 않았다. 새 실제 후보·선택만 별도 output에 생성했다. 기존 선택의 winner는 이번에 다시 추론하지 않았지만, J2d report/code/input SHA를 확인하고 각 이전 선택 경로의 비용을 원 source와 기존 scorer에서 재계산해 일치시켰다. 이전 모든 arm의 집계도 그대로 재확인했다.

## 4. 전체 비교 결과

같은 **33악보 / 19작품군 / 322문맥 / 완전256·부분66**이다. Overlapping eligible time7,895/8quarter는 고유 전곡 길이나 독립 표본 수가 아니다. Partial reference66개도 시간 평가의 지원 범위에 포함하고, 완전 일치/경계 평가는 지원되는256개에서 비교한다. 이번 단계는 full Roman/전위/NCT/cadence 정확도가 아니다.

### 후보 공급과 실제 선택의 분리

- 원 후보망에서 정답 진행을 표현할 수 있는 문맥132/256 → **140/256(54.69%)**, +8이다. 이는 reference를 이용한 evaluator oracle이며 실제 정답 선택8개 증가를 뜻하지 않는다. 원 candidate ceiling은 잃은 구간0이다.
- 201문맥에 총4,261개 기능적 후보 reading을 추가했다. 이는 곡 수/정답 수가 아니다. 원 후보 제거0, 원6segment cap와 points 변경0이다.
- 후보/복잡도 비용만 추가한 control의 시간·완전 일치·경계와 실제 semantic 경로는 J2d와 동일했다. **새 후보만 늘려서는 실제 선택이 개선되지 않았다.**
- 해결 근거를 연결한 arm에서 실제 새 기능적 후보를7문맥에 선택했다. 직결 상성부가 없는 경우에도 실제 수직 표면과 동일 sounding bass 유지가 별도 약한 근거로 남는다.7문맥이 모두 맞았다는 뜻은 아니다.

| 지표 | J2d / 후보 control | 후보 + 해결 근거 |
|---|---:|---:|
| 구간 전체 root+members 일치 /256 | 51 | **52** |
| Root 시간 일치 | 40.11% | **41.48%** |
| Root+spelled members 시간 일치 | 30.46% | **31.97%** |
| 작품군 macro root+members | 37.59% | **39.08%** |
| 경계 TP/FP/FN | 209/85/234 | 215/94/228 |
| 경계 precision / recall | 71.09% /47.18% | **69.58% /48.53%** |
| 경계 F1 | 56.72% | **57.18%** |

전체 일치 회복1, 기존 정답 유지51, 전체 일치 퇴행0, 양쪽 오답204다. 그러나 시간 단위로는16문맥 이익·2문맥 퇴행·304동일이다. 전체 일치 퇴행0을 모든 부분이 개선된 것으로 해석하지 않는다. 실제로 불필요 경계9개가 늘었고 경계 precision은 내려갔다.

| Split | J2d 전체/시간/macro/F1 | 후보 + 해결 전체/시간/macro/F1 |
|---|---|---|
| Train270 / 완전205 | 44 /30.11% /38.39% /55.14% | 45 /31.04% /39.51% /55.58% |
| Dev52 / 완전51 | 7 /32.04% /33.34% /61.54% | 7 /36.12% /36.77% /62.03% |

새 fitting/Dev weight 선택은 없으며, 이미 노출된 개발 cohort의 비교다. 새 independent test 정확도가 아니다. 두 arm 모두 **288선택/34보류**로 J2d의28baseline_not_ready·3edge-budget·3transition-budget 보류를 그대로 유지했다. 새 자원 보류0, 분모 제외0이다.

### 실제 사례와 실패

- **Beethoven Sonata03-2** `cont_b0b624e987d33699d356` `[14,31/2)`은 새 완전 일치 사례다. 표면 Emajor/B를 **surface root E + functional root B, members B/E/G#**로 유지하고 다음 B7, 이어 Emajor로 진행한다. Source bass `sound_c56a7d8127cb`가 동일 sounding event로6–4→B7까지 지속된다. 직결 upper voice의4→3/6→5는 unavailable이고, 표면+실제 동일 bass 근거 −1/10이 선택에 들어갔다. 기능적6–4 후보의복잡도 +1/20도 유지했다. 원 annotation `ann_15292af1e85d_27/28/29`와 root/member/time projection은 일치하지만 cadence/음악적 최종 정답 검수를 한 것은 아니다.
- **Corelli op01n01a**, Dev `cont_a387814f1e471fa70c51` `[18,23)`: 시간 일치가4quarter 증가했다. 이전 큰 구성음 집합/병합 진행 대신 D-root7화음→Gmajor→Cmajor→Adiminished→Bbmajor로 선택하고, 실제 B→C 및 A→Bb leading-tone 경로를 붙였다. 모든 구간을 완전 정답으로 간주하지 않는다.
- **Mozart K280-1** `cont_601fd25d1ccb611517dc` `[191,197)`: 시간 일치11/4quarter 증가. G7→Cmajor의 실제 leading-tone 도착 근거를 사용하면서 이전5구성음 집합 과선택 일부를 벗어났다. Secondary 여부는 local key 미지원으로 unresolved다.
- **Chopin BI126-1op41-4** `cont_8120f6da80814e235cdb` `[168,171)`: **3/2quarter 퇴행**. Ebmajor→Abmajor의 G→Ab 실제 경로가 −1/10 보상을 받아, reference의 Eb7 유지 해석을 짧은 triad 전이로 나누었다. **실제 leading-tone motion이 있어도 독립 화음 교체가 확정되는 것은 아니다.** 단순 보상 count의 과분할 편향을 주요 실패로 남긴다.
- **Beethoven Quartet n01op18-1_01** `cont_195ab0306a75a682b13e` `[2519/4,632)`: **1/2quarter 퇴행**. Bdim7→C 및 C→F 계열 direct 경로는 관찰되지만 뒤 Fmajor7 선택이 reference의 Am7/C 유지와 달라졌다. 한 해결음만으로 전체 화음·경계를 과확정하지 않아야 한다.

8개 새 ceiling은 Sonata01-2의3문맥, Sonata03-2의1문맥, Chopin BI105-2op30-2/BI115-4op33-4의3문맥, MozartK280-2의1문맥이다. 모든 sample/span/origin은 report에 있다. J2d에서 문제를 발견한 **Chopin BI105-3op30-3**는 이번에 새 완전 일치로 회복되지 않았다. 이 특정 사례를 맞추기 위해 추가 예외나 weight tuning을 하지 않았다.

선택된 path의 조건부 근거 occurrence는6–4 표면/유지7·직결4/6 해결4, V-leading22·V7-leading13·V7-seventh15·vii-leading12·vii7-leading2·vii7-seventh1·half-diminished-leading1이다. 이는 overlapping context와 중복 source motion을 포함하며 정확한NCT/Secondary label 수가 아니다.

**결정:** 공급·선택 연결은 완료했고 후보 ceiling 및 시간/macro/F1에 제한적 개선이 있다. 하지만 전체 일치1개 증가·경계 precision 퇴행·local-key와 polyphonic/decorated resolution 미지원이 있어 **운영 화면 적용은 보류**한다. 기존 운영 score/UI는 유지한다.

## 5. 산출물과 재현

실제 output: [report.json](../../../output/harmony-functional-scoring-2026-10-04-r1/report.json), [selection-changes.json](../../../output/harmony-functional-scoring-2026-10-04-r1/selection-changes.json),2파일 총15,832,241B. 기존 output은 덮어쓰지 않았다. 모든 새 후보의 origin group·literal/functional root·span·source IDs·blocker를 보존하고, 사후 gain/loss5사례는 context/source SHA와 원 reference를 연결했다. 새 완전 회복 및8ceiling 사례는 전체 report에 있다. 참조 witness는 evaluator의 후보 ceiling이며 실제 prediction과 분리한다. Full pinned IR/source XML 및 source-context/search artifact는 원 저장 위치와 물리 hash로 역추적하고 복제/변형하지 않는다.

**847고유 입력/코드 SHA가 실행 종료 및 사후 재검사에서 모두 불변**이다. 신규 source2개의 물리SHA:

- functional scorer: `8a281b4a5ad59454b4f069efb530bafa3b33a5badd4f9620d7d2a6388d9d311a`
- trial: `427f8503d93aad515b73849f77a53a746c3af9440e6a70cd16fab76ba60c27a0`

| Artifact | Bytes | SHA256 |
|---|---:|---|
| report.json | 15,136,750 | `e3983219bc2b53fd102302514cecc74e9e98b54290cc3d295e3023c6e912f661` |
| selection-changes.json | 695,491 | `e570be4e52ab87fe34480e6a82062dfdbc4351e7f2887d85442f04568474e6fb` |

`python -B -m musicanote_harness.harmony_functional_scoring_trial --help`를 따른다. Previous J2d report SHA `808b72c6db9d66bf91fc79ad58b3d0249fb34757dd5490ce09cfd445656aa928`, recall SHA `f12397eb53544dfa153974a9f0006f7cb06467d09c10ce1ecaf8da2e2d21f0eb`, integration SHA `22ff64ceb522cfde5039d07dc28935179e8c12add14ed52aaa0295f90e1bcebe`를 pin한다. Same33악보/19작품군/322문맥이며, 이전 후보 ceiling132/256과 실제 선택51/256·시간30.46%를 비교한다. 독립 test/전곡/full Roman 정확도가 아니다.

## 6. 남은 큰 작업

후보 control만으로는 선택이 바뀌지 않았고, 해결 보상이 실제 선택을 바꾸었으나 일부 내부 motion을 독립 전이로 과선택했다. **다음 큰 작업은 새 run/기능적 전이20특징의 train-only 학습**이다. 원11 edge-additive 특징 학습을 그대로 호출하지 않고 합집합 run·기능적 해석 비용·실제 조건부 pair를 표현한다. 시간/경계 손실과 source 사용 조건을 유지하고 Dev tuning/특정 작품 예외는 하지 않는다. 후보 ceiling140/256 밖의116오류는 가중치만으로 해결했다고 주장하지 않는다.

전역·local key/Secondary 판정·7음·지연 해결·큰 음 집합의 장식 흡수는 별도 주요 과제다. 전체 Roman/전위/NCT·cadence·독립 작품 benchmark와 운영UI 승격·작곡편곡 연결은 남아 있다. 새 점수 사용 여부는 독립 평가와 실제 악보 검토 뒤 판단한다.
