# J2a — 음악 근거 점수와 원 후보망의 직접 공동 선택

기록 ID: **HARM-DEV-20261004-49** · 2026-10-04. J2의 첫 구현이며 **가중치 학습 또는 J2 전체 완료가 아니다**. 현재 [개발 메인 문서](../README.md), [J0–J5 계약](2026-10-04-joint-decoding-and-benchmark-review.md), [원 후보망 coverage 진단](2026-10-04-lattice-candidate-coverage.md)을 따른다.

## 1. 문제와 이번 범위

단계47은 보존된 최대24개 진행을 단순 원시 비구성음 비율로 골랐다. 단계48에서 원 후보망에는 있지만 보존 탐색에서 잃은 정답 진행67개를 확인했다. 이번에는 **음악적 관측 특징의 고정 점수로 원 후보망을 직접 탐색**하여 구간과 화음을 함께 선택한다. Gold witness를 선택기로 전달하거나 특정 작품/마디의 정답을 삽입하지 않는다.

사용자는 DCML의 규칙 가중치 학습과 빠른 객관적 수치를 요청했다. 기존33개 package의 실제 자격을 확인하니 전부 `automatic_training=false`, `model_training_approved=false`, `licence_status=unverified`다. 내부 연구·개발 진단의 자격과 학습 자격은 다르므로 그대로 보존한다. **학습하지 않은 비교를 실제 수행하고, 학습은 출처별 조건 확인 뒤 별도 단계에서 한다.** 자동으로 자격을 바꾸거나 외부 API로 원자료를 전송하지 않았다.

## 2. 일반 음악 점수의 계약

첫 점수는 다음 비용의 합을 최소화한다. 고정 초기값이며 DCML 정답을 보고 조정한 값이 아니다. 특징의 의미·단위·mask를 함께 저장하므로 다음 학습 단계에서 같은 특징을 사용할 수 있다.

| 특징 | 계산 및 초기 가중치 |
|---|---|
| 비구성음 노출 | 원 sound의 후보 비구성음 음표-시간 / 문맥 전체 음표-시간; 1 |
| 철자 미지원 노출 | 지원 못 하는 철자의 음표-시간 / 문맥 전체 음표-시간; 1/2 |
| 후보 보류 노출 | 기존 blocker가 있는 후보의 음표-시간 / 문맥 전체 음표-시간; 1/4 |
| 관측되지 않은 구성음 | 구간 길이 / 문맥 길이 × 관측되지 않은 후보 구성음 비율; 3/10 |
| 관측되지 않은 근음 | 같은 시간 가중치를 사용; 1/10 |
| 추가 구성음 복잡도 | 같은 시간 가중치 × max(구성음 수−3,0); 1/10 |
| 근음 미판정 | 같은 시간 가중치 × 근음 철자 미지원; 1/5 |
| 분할 복잡도 | 각 segment 1개; 3/200 |
| 새 attack 없는 교체 | 화음이 바뀌면서 새 구성음의 실제 attack이 경계에 없는 경우; 1/25 |
| 근음 이동 | 두 근음 pitch-class의 작은 이동 거리 / 6; 3/200 |
| 구성음 교체량 | 두 구성음 집합의 대칭차 / 합집합 크기; 1/50 |

이 비용들은 **관측 근거와 약한 복잡도 prior**다. 근음이 빠졌다고 화음을 탈락시키지 않으며, 화음 수가 적거나 이동이 작다고 음악적 정답이라는 뜻도 아니다. 추가 구성음 비용은 7화음을 금지하는 규칙이 아니고, 짧은 추가음까지 모두 화음 구성음으로 흡수하는 기존 편향을 대조하는 초기값이다. 상관된 관측 특징이므로 독립 증거 투표나 보정된 확률로 표시하지 않는다. 초기값의 개선/악화는 실험으로 구별해야 한다.

`F#`/`Gb`, double accidental의 철자를 유지한다. Pitch-class는 **이동량 특징에만** 사용하며 정확한 구성음 일치와 상태 ID에는 철자를 쓴다. 음표 중복·옥타브 doubling의 음표-시간은 원 입력과 동일하게 유지한다. 관현악의 doubling에 대한 일반화는 이번 결과로 입증하지 않는다.

### 아직 점수에 연결하지 않은 해석

하나의 성부 가정 안에서 검증된 NCT 설명, 실제7음 해결, 국소 조성, 적용화음/목표 해결, 박절 상대 경계 및 structural bass는 `null` + availability=false다. Missing이 false가 된 것이 아니다. 기존 교재 규칙을 폐기하지 않았지만 **모든 교재 규칙이 점수에 연결됐다고 하지 않는다.** 다음 J2b에서는 이 특징과 동일 전제의 역할·기능 근거를 연결한다.

기존 `optimistic_local_nct_potential_note_time`은 충돌 가능한 국소 상계이므로 비용에서 빼지 않는다. 이를 NCT가 설명한 음가로 바꾸지 않았다. `candidate_blockers`는 출력에 그대로 보존하며 이번 soft cost만으로 원래 readiness를 true로 승격하지 않는다. 선택은 `selected_untrained_hypothesis`, confidence=null, human_validated=false, music_constraints_fully_validated=false다.

### 시간과 길이0 기보

좌표·음가·점수·가중치를 유리수로 계산한다. 구간은 `[start,end)`이며 구간마다 raw 비율의 분모를 바꾸지 않고 **문맥 전체 음표-시간**으로 통일한다. 미래의 학습 가중치가 음수라도 DAG이므로 정확한 최적화가 가능하며 API는 signed rational을 받는다.

실제 실행에서 길이0 sound가 존재했다. 원 event/state/ID를 보존하되 지속 근거·구성음 presence·performed attack으로 더하지 않으며 임의 음가를 발명하지 않는다. `zero_duration_observation_refs`에 문맥의 해당 ID를 저장한다. 길이0만 있는 문맥은 `no_positive_sounding_exposure`로 보류한다. 실제 grace 여부/연주 timing을 이 표본 필드만으로 확정하지 않는다. 음수 음가·ID 중복·source/음가 불일치와 관측·candidate/objective 불일치는 오류로 거부한다.

## 3. 탐색과 비교 실험

새 DP 상태는 **(끝 시간점, segment 수, 직전 근음+구성음 철자)**다. 직전 화음을 버리고 싼 prefix 하나만 남기면 전이 점수의 최적해를 잃는 반례를 검사했다. 새로운 성부/조성/지연 해결 특징이 이전 role/state에 의존하면 그 상태도 확장해야 하며 현재 signature 상태가 그 문제까지 해결한 것은 아니다.

- 기존 원 후보·모든 origin·시간·기보는 그대로 쓴다. 후보를 재생성하거나 주석으로 추가하지 않는다.
- 기존 최대6segment는 유지한다. prefix beam/final24 보존 제한은 새 직접 decoder에는 없다.
- 현재 additive 1차 점수와6segment 제한 아래 exact DAG 최소 비용을 구한다. 음악적 exact 정답이라는 의미가 아니다.
- 2,000,000 전이 예산을 넘으면 임시 winner를 반환하지 않고 별도 보류한다. 기존 lattice 보류도 유지한다.
- 출력은 선택 구간의 원 group/adapter/event refs, 특징 값/mask, segment/transition 비용, 총 비용, 버전을 포함한다.

같은 입력에서 네 arm을 비교한다.

1. **retained_raw_baseline:** 단계47의 원 선택 기준선.
2. **retained_music:** 동일24후보를 새 음악 점수로만 재순위화.
3. **direct_segment_only:** 원 후보망에서 새 segment 점수로 선택하되 전이 점수는0.
4. **direct_joint_music:** 원 후보망에서 segment+transition 점수로 직접 선택.

따라서 1→2는 점수 효과, 2→4는 같은 점수 아래 보존 탐색 제거 효과, 3→4는 현재 전이 점수 효과를 분리한다. 모든 선택을 고정한 뒤 evaluator만 reference cells를 사용한다. 변경된 정답이 같은 입력의 선택을 바꾸지 않는 physical runner 검사도 포함한다.

## 4. 측정 범위와 실제 결과

기존322문맥/33악보 package/19작품 가족을 그대로 사용한다. Train270/dev52는 이미 노출된 개발 자료이며 새로운 independent test가 아니다. 평가 가능한256문맥, 부분/미지원66을 유지한다. 평가는 **절대 근음 + 철자를 보존한 구성음 집합의 정확한 시간 일치**이며 Roman/function/전위/key/NCT/cadence 전체 정확도가 아니다.

실제322문맥 전체 실행은 **252.139377초 / exit0**으로 완료했다. 모든 arm은291선택/31보류이며 보류는 기존 `baseline_not_ready`28·`edge_budget_abstention_no_pruning`3이다. 새 전이 예산에 걸린 문맥은0이다.

| Arm | 문맥 전체 일치 / 256 | 근음 시간 일치 | 근음+구성음 시간 일치 | 정확한 의미 경계 F1 |
|---|---:|---:|---:|---:|
| 기존24·raw 기준선 | 5 (1.95%) | 21.70% | 2.84% | 15.71% |
| 기존24·음악 점수 | 37 (14.45%) | 34.51% | 19.39% | 45.73% |
| 원 후보망·segment만 | 37 (14.45%) | 40.99% | **31.01%** | **57.35%** |
| 원 후보망·segment+transition | **50 (19.53%)** | 40.47% | 30.15% | 57.26% |

시간 일치의 공통 적격 분모는 `7895/8` quarter이며 원 개발 시간 coverage76.73%다. 보류는0정답 시간으로 분모에 남긴다. 의미 경계는 완전 평가256문맥의 **root+spelled member 집합 변화**만 계산하며 같은 집합의 전위/기능/key 변화, 구간 바깥 경계는 평가하지 않는다. 문맥이 겹치므로443개 참조 경계는 전곡의 고유443경계가 아니다.

Joint 경계 TP209/FP78/FN234, precision72.82%/recall47.18%다. Segment-only TP236/FP144/FN207, precision62.11%/recall53.27%다. 전이 비용이 과분할을 줄였지만 일부 필요한 경계도 억제했다. **전체 문맥 성공 수만으로 joint가 모든 지표에서 더 낫다고 할 수 없다.** 작품 가족 macro root+members도 joint38.35% 대 segment-only40.71%다. 두 arm을 유지하고 학습/기능 근거 단계에서 이 trade-off를 개선한다. 처음 결과를 보고 가중치를 다시 맞추지는 않았다.

Train205완전 문맥에서 기준선4→joint44, dev51완전 문맥에서1→6이다. Dev 시간 root+members는 기준선1.11%→joint30.45%, segment-only32.25%다. Dev도 과거 노출된 자료라 독립 일반화나 논문 공통 성능으로 보고하지 않는다.

원 기준선에서 틀렸다가 joint 전체 일치로 바뀐46, 반대로 전체 일치에서 틀린 것으로 바뀐1, 기존 정답을 유지한4다. 단계48의 보존 손실67개 중 이번 실제 선택으로 완전히 회복한 것은10개다. **원 lattice ceiling132/256는 그대로이며50/256과 다른 지표다.** Local 후보 부족85·연결22 등을 점수 변경으로 해결했다고 하지 않는다.

Feature 준비32.450초, joint decode58.635초, segment-only43.279초,24path 점수0.442초다. 나머지는 입력 로딩·hash/평가·저장 전 검증이며 전곡 UI latency와 다르다. Joint 실제 전이8,028,132개, 가장 큰 한 문맥1,243,807개다. 이 수는 정답 수가 아니다. 길이0 이벤트가 있는 문맥6개/고유 원 sound9개를 보존했다.

### 실제 사례·반례

모든 사례의 group/adapter/event ID, 시간, 비용/mask와 원 context/search 경로·SHA는 [실제 보고서](../../../output/harmony-scored-decoder-2026-10-04-r1/report.json)에 저장된다. 앞뒤 원 악보와 score/annotation binding은 보호된 입력 package를 그대로 참조한다. 다음 표는 선택 근거와 미해결 오류를 대조한 것이며 사람이 승인한 새 Gold가 아니다.

| 사례 | 관측/선택/평가 |
|---|---|
| Beethoven sonata03-2, `cont_5f130fc395c3561ba6c4`, `[103,209/2)` | 원24에 완전 정답이 없던 진행. B근음 `{A,B,D#,F#}` `[103,104)` → C `{C,E,G}` `[104,835/8)` → G `{B,D,G}` `[835/8,209/2)`를 직접 선택해 전 범위가 참조와 일치했다. 첫 B7 범위의 비용89/600에 비구성음1/15·추가 구성음2/3의 가중 비용이 포함되어도 이어지는 두 구간/전이의 전체 비용86/375가 유리했다. B7을 무조건 금지하지 않는 실제 예다. 동일 B집합의 두 annotation onset은 의미 경계로 세지 않았다. **Applied function을 맞혔다는 평가는 아니다.** |
| Quartet `cont_3244c06fe647a34779cc`, `[2479/4,621)` | 이전은 B♭minor에 A음을 추가한7화음으로 흡수했다. 새 선택은 B♭minor → D♭ `{A,D♭,F}` → B♭minor로 나눠5/4시간 중3/4만 맞혔다. 추가음 흡수는 줄였으나 장식음을 별도 화음으로 만든 오류가 남았다. NCT/유지 근거를 연결해야 하며 이 사례가 해결됐다고 하지 않는다. |
| Quartet `cont_195ab0306a75a682b13e`, `[2519/4,632)` | 정답 Fminor→Cmajor가 원 후보망에 있으나 새 선택도 B근음7화음 → Cmajor → Cmajor7이다. 화음 교체 시점630은 회복했으나 불필요한 뒤 분할·처음 오판이 남아9/4중7/4만 구성음 일치한다. 직접 탐색만으로 올바른 선택을 보장하지 않는 예다. |
| Mozart K280-1, `cont_85c52e26badf779896f7`, `[288,289)` | 원 기준선은 참조 C7 `{B♭,C,E,G}`와 전체 일치했으나 새 점수는 실제 창에 C/E/G만 있는 C3화음을 택해 구성음0/1이 됐다. Missing/복잡도 비용의 반례다. 앞뒤 화음 유지·7음 역할 없이 local presence만으로 생략된7음과3화음을 판별할 수 없다. 원주석을 수정하거나 이 작품의 예외를 추가하지 않는다. |
| Quartet `cont_23589950367f4bbba6b4`, `[1333/4,334)` | F→E→D만 관측되는 짧은 창이며 Cmajor 후보가 원 목록에 없다. 새 선택도 Dminor이고 구성음 일치0이다. 85개 후보 밖 오류는 다음 문맥/후보 생성 개선 대상이다. |

## 5. 구현·재현

- [선택기](../../../src/musicanote_harness/harmony_scored_decoder.py): `harmony-scored-decoder-0.1.0`, 특징 `stored-spelled-music-features-0.1.0`. `prepare`, `decode`, `evaluation_path`에 Gold 인자를 두지 않는다.
- [분리된 실험 실행기](../../../src/musicanote_harness/harmony_scored_decoder_trial.py): `harmony-scored-decoder-trial-0.1.0`, 원 hash/manifest/코드·입력 종료 불변 검사, 동일 분모 및 split별 비교.
- [검사](../../../tests/test_harmony_scored_decoder.py): 실제 score 코드와 synthetic parent receipts를 쓰는 physical gzip 실행기. 실코퍼스 정확도와 unit test 통과를 별도로 보고한다.
- 입력: [단계47 결과](../../../output/harmony-candidate-recall-2026-10-04-r1/report.json), [단계48 결과](../../../output/harmony-lattice-recall-2026-10-04-r1/report.json), 양쪽이 pin한 기존 원 context/search/score/annotation 파일.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m unittest test_harmony_scored_decoder test_harmony_lattice_recall test_harmony_candidate_recall test_harmony_progression_search
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_scored_decoder_trial --recall output/harmony-candidate-recall-2026-10-04-r1/report.json --lattice output/harmony-lattice-recall-2026-10-04-r1/report.json --expected-recall-sha f12397eb53544dfa153974a9f0006f7cb06467d09c10ce1ecaf8da2e2d21f0eb --expected-lattice-sha d2be3a53917c627c22c7e64b425dfdd462e94a1cfed3c42d8d0330dff6c05acc --output output/harmony-scored-decoder-2026-10-04-r1
```

출력 폴더가 이미 있으면 거부하므로 재실행 때는 새 이름을 쓴다. 원 코드·Core·XML·주석·예전 분석 결과·학습 자격·운영 UI와 서버·Git은 바꾸지 않는다. 이번 연구 선택기를 화면용 엔진으로 바로 승격하지 않았다.

### 실패·검사·보존

- 첫 실제 실행은129번째 Chopin `BI115-3op33-3`의 `sound_8e952f1ff0c3` `[106,106)`에서 새 검사기가 길이0을 음수와 함께 거부해 중단됐다. 완성 출력 폴더는 생성되지 않았다. 원 reading에는 이 ID가 있고 음표-시간은0이었다. 양의 지속 근거에서만 제외하고 원 ID/state는 보존하는 방식으로 교정했다. 음수/중복/source 불일치 검사는 유지한다.
- 수정 후 신규33 + 기존52 = **85 PASS / 0.881초**. 전이 상태 반례, exhaustive 작은 DAG와 exact 결과 대조, 유리수·enharmonic·tie continuation·길이0·미지원 mask·원 objective 오염·cap/예산 보류·참조 변경·학습 gate·protected split·physical hash·overwrite를 포함한다. 첫83검사와 재실행을 독립 표본으로 합산하지 않는다.
- 새 report는1파일 **4,075,400B**, SHA `e197fc16b2199f985a39c780aa2468606cdaf8188c4fc7aad920b8e777c49825`다. 입력/코드718개를 종료까지 보호했다.
- Decoder SHA `d2043d4165de4f5f3302fb1a0e672d1a08f582dfce2d1e86ee837b15c3c83b47`; trial SHA `3ab6ddf58d4e251e5f736c8e289f6dd458f58624570da0d99e4e534fedd8bc93`다. 고정 가중치는 report에 유리수로 포함된다.
- 원47의 기준선 수치/분모 및48의 후보망·원음·주석은 변하지 않았다. 운영 UI/서버·source Core·학습/자격/원주석/과거 예측·Git commit/push 변경0이다.
- 사후 검증: 코드/검사3개 AST 통과, 변경4문서 strict UTF-8/replacement0·로컬 링크273개/누락0,718입력/코드 SHA 재대조 변경0, 단계45의 report/정책/실행기3pin 불변, `git diff --check` exit0이다. 이전5개 tracked 파일의 LF→CRLF 경고만 유지한다. 메인/로그/계획의 새 등록은 각1개로 중복0이다.

## 6. 다음 단계와 결정

J2a의 비교를 근거로 초기 score를 유지/수정/기각한다. 다음은 **출처별 학습 사용 조건 확인 → 적격 train 자료에만 가중치 학습 → dev 비교**다. 자격 확인을 전체 코퍼스 재정리로 확대하지 않고 현재 필요한 출처부터 마감한다. 내부 연구가 가능하다고 기존 학습 허가=false를 자동으로 true로 바꾸지 않는다.

현재 [manifest schema v0.1](../../../MUSICANOTE_Canonical_Music_IR/schemas/harmony_dataset_manifest.schema.json)의 `model_training_approved`도 const=false다. 따라서 단순히 boolean을 뒤집는 것은 허가 확인도 아니고 유효한 v0.1 문서도 아니다. 다음 단계에서는 확인된 사용 근거/출처·작업별 승인과 원 manifest ID/hash를 연결하는 별도 버전의 최소 학습 계약을 사용하며, 기존 manifest와 과거 실험의 자격 이력은 그대로 둔다. 이번 `training_eligibility`는 audit 함수로서 학습 실행이나 새 권한 발급을 하지 않는다.

동시에 후보 밖85·구간 연결22의 영향을 보존하고, 동일 성부 가정의 NCT/7음 해결·국소 조성/적용화음 근거를 점수에 연결한다. 첫 학습 결과와 full Roman/inversion/key 출력 계약을 마련한 뒤 새로운 전곡/독립 작품 및 공개 모델 공통 평가로 이동한다. UI 연결은 연구 점수와 기존 완전 분석의 범위를 명확히 구별할 수 있을 때 한다.
