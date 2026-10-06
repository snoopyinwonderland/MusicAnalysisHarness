# 단계91 — 정확한 박자 환산 재사용의 전체 Train 재분석

## 목적과 적용 범위

단계90의 저장 경로 동등성 증명 다음으로, **원 Train 118구간 전체를 실제로 다시 탐색**한다. 23개 전체 악장 source/15작품군/60,129개 원 graph edge를 보존한다. 118곡이나 독립 Test가 아니다.

이번 단계는 화성 규칙이나 후보·가중치를 바꾸는 작업이 아니다. 같은 점수로 제한 시간 안에 계산을 마칠 수 있는지 확인한다. 고정 모델은 단계88의 순위 보호35, SHA `b6ff68e73bf6b5b9760107344f66f5c5626da2aa5c8b93ca061c21d6cbc74f38`다. 이미 학습된 모델을 불러오며 새 학습/계수 탐색/Dev 활용/작품별 분기0이다.

운영/UI/Claude 편곡 연결은 아직 하지 않는다. 이번 Train 결과 뒤 **같은 고정 모델의 Dev 재분석**이 필요하다. 큰 화음/NCT 오답, 국소 조성·기능·전위, 독립 성능 및 편곡 입력 의미 계약은 별도 관문이다.

## 실행 계약

- 같은 원 graph, 6raw segment cap, 2,000,000 feasible-state/raw-edge 비교, 구간당20초 cooperative guard를 유지한다. 개별 함수가 길면20초를 넘을 수 있다. 부분 승자/과거 승자 fallback/재시도0이다.
- 단계90 cache는 source-local `(start,end)` Fraction의 박자 길이만 재사용한다. 원 source/조표·박자·철자·음가·성부·붙임줄·unknown·DP bytecode·상세 비용식·독립 winner 검사는 그대로다.
- 새 scorer 인스턴스와 cache로 매 구간을 분석한다. `cProfile` 계측이나 병렬 무거운 검사를 하지 않는다.
- 모든118예측을 별도 packet으로 저장하고 `prediction-freeze.json`을 만든 **뒤** 주석 평가와 저장 경로 재현을 한다. Target은 평가 증인이지 예측 입력이 아니다.
- 과거 완료와 새 완료의 교집합에서는 raw 경로 ID, Fraction 비용, 상세 근거, transition 수 및 DP 진단이 모두 같아야 한다. 다르면 실패한다.
- 전체118의 보류 포함 지표와 공통 완료 지표를 따로 보고한다. 새로 완료됐지만 주석과 틀린 구간도 보고한다. 과거 wall 시간과의 비교는 같은 시점/하드웨어 부하를 통제한 속도 실험이 아니다.
- 전체 XML/IR 경로·SHA, source clock gate, rational span, 원 note/sound ID를 추적할 수 있는 provenance, 과거 case·예측 freeze의 경로와 SHA를 유지한다.

## 신규 파일

- `src/musicanote_harness/harmony_exact_beat_train_trial.py`: 고정 모델/증명 pin 검증, 전체 ordinary 탐색, 예측 선봉인, 과거/새 경로 재현 및 구분 집계.
- `tests/test_harmony_exact_beat_train_trial.py`: 실행 계약10개 검사.
- `scripts/validate_harmony_exact_beat_train.py`: 단계90의968검사를 유지하고 새10검사를 더한다.
- `scripts/audit_harmony_exact_beat_train.py`: 새 탐색/학습 없이 source·상세 비용·projection·과거 동등성·평가 및 집계를 재현한다.

기존 단계90 cache/봉인 code/test/script, 부모 모델/출력, 원 Core·주석 및 다른 프로젝트는 수정하지 않았다. 새4코드도 실제 탐색을 시작한 뒤 수정하지 않는다.

## 검증 및 산출물

실행 전 새10검사 PASS, 이어 최종978관련검사/93모듈 PASS·failure0/error0·109.936208초다. 전체 repository 검사나 작품 수가 아니다. 검증 출력은 [validation](../../../output/harmony-exact-beat-train-validation-2026-10-06-r1.json)이다.

실제 실행934.549119초/exit0로 완료됐다. `output/harmony-exact-beat-train-2026-10-06-r1/`의118예측을 먼저 봉인한 뒤118case의 평가·경로 재현을 수행했다. 실행 중 `progress.json`은 진행용이며 [report.json](../../../output/harmony-exact-beat-train-2026-10-06-r1/report.json)이 정본이다. 사후 감사는 별도 실행하고 그 결과를 아래에 기록한다.

## 전체 결과 — 보류 복구와 음악적 변경 없음

| 비교 항목 | 과거 단계88 | 이번 캐시 |
|---|---:|---:|
| 원118구간 완료 / 시간 보류 |102 /16|102 /16|
| 원118 전체 진행 일치 |58 /118|58 /118|
| 원118 근음+구성음 시간 일치율 |58.384782%|58.384782%|
| 원118 예측 시간 coverage |73.602536%|73.602536%|
| 원118 작품군 macro |56.429810%|56.429810%|
| 원118 의미적 경계 TP / FP / FN |60 /24 /51|60 /24 /51|
| 원118 의미적 경계 F1 |61.538462%|61.538462%|
| 공통 완료102의 진행 일치 |58 /102|58 /102|
| 공통 완료102 근음+구성음 시간 일치율 |79.324416%|79.324416%|
| 공통 완료102 작품군 macro |77.350301%|77.350301%|
| 공통 완료102 경계 TP / FP / FN |60 /24 /16|60 /24 /16|
| 공통 완료102 경계 F1 |75.000000%|75.000000%|

원118 전체의 평가 시간은 `5993/24`quarter, 일치 시간 `3499/24`, 예측 coverage `4411/24`다. 공통 완료102의 평가 시간은 `4411/24`다. 보류16개를 제거한79.32%를 전체 성능으로 제시하지 않는다. 모든118은 근음+구성음이 평가 가능하지만 quality/전위/local key/degree/Roman의 평가 가능한 시간이0인 이번 진단이다. NCT 전체 정확도·생성 품질·독립 Test 성능을 주장하지 않는다.

공통 완료102의 raw ID·정확한 비용·상세 근거·transition 수·DP 진단 차이0이다. 새 경로/새 정답/기존 정답 소실/기존 완료 소실/과거 보류 복구는 모두0이다. 과거 보류16개도 동일 집합이다. 과거 저장542named witness를 모두 보존하고 새 fresh102를 더해 **644개 상세 비용·555개 scalar/role 및 pair 전이**를 재현했다. 원6raw/2M/20초를 늘리거나 보류에 과거 승자를 넣지 않았다.

## 계산량과 시간 — 통제된 속도 실험이 아님

탐색 당시 cache 조회 `1,039,894`, hit `1,039,226`, 원 박자 적분 `668`, 각 scope의 cache entry 합 `668`이다. 같은 구간의 중복 적분은 줄었지만 다음의 DP·문맥·역할 비용 계산은 그대로 남는다. 이는 **탐색 중 캐시 진단**이며 캐시 없는 독립 상세 winner 검사/사후 재현의 원 함수 호출까지 포함한 전체 프로그램 호출 수는 아니다.

| 시간 항목(초) | 과거 단계88 | 이번 캐시 |
|---|---:|---:|
| 원118 guarded 탐색 합 |518.573657|481.796521|
| 공통102 guarded 탐색 합 |178.256523|157.639713|
| 공통102 guarded 중앙값 |0.337792|0.273135|

이번 source 준비179.032699초/scorer 생성8.646768초이며 guarded 최대20.770245초다. Cooperative guard의 단일 함수 초과는 그대로 허용하고 부분 승자는 반환하지 않는다. 이번934.549119초의 총 실행에는 입력 pin 검증·예측 저장·source 재준비·644경로 재현·평가·최종 봉인이 포함된다. 과거 총 실행과는 절차가 달라 전체 시간을 직접 대조하지 않는다.

현재 조건의 guarded 합이 줄었다는 관찰은 남기되, 과거 실행과 같은 시점·하드웨어 부하를 통제하지 않았으므로 보장된 speedup은 아니다. 단계90의 cProfile 누적 약41%는 계측 오버헤드의 영향도 받으며 이번 native wall시간 감소율이 아니다. **큰 구간을 더 분석할 수 있게 됐다는 성공은 이번에는 없다.**

## 원악보 사례 — 정답 유지·오답 유지·보류 유지

모든118case는 전체 XML/IR를 참조한다. 아래는 계산 결과 보존을 보여 주는 사례이고, 새 화성/NCT 규칙이나 사람이 검증한 정답이 아니다. 음악적 선택은 같은 고정 모델의 결과를 그대로 기록한다.

### 1. Beethoven quartet op18-1 IV — 완료된 정답 유지

`cont_00fe53c74ace3533c190`, quarter `[265,533/2)`에서 D♭근음/D♭–F–A♭를 선택했다. 주석의 근음+구성음과 일치하고 과거와 같은 raw ID·비용 `3433/20000`이다. 이번 guarded0.206412초, cache440조회/437hit/3적분이다.

원 D♭4 `sound_d8d1550662d3` / `note_47893f878e74`, F4 `sound_5b46b545ccea` / `note_96a8e85d0174`, A♭4 `sound_8e057865dfa1` / `note_9f6497a74bba`는 모두 `[265,531/2)`다. 뒤 D♭4 `sound_7d199134832a` / `note_620701f653ed`는 `[531/2,266)`로 이어진다. 구간만 보고 동시음을 새로 만들거나 철자를 MIDI로 축약하지 않았다.

[새 예측·상세 근거·과거 연결](../../../output/harmony-exact-beat-train-2026-10-06-r1/cases/cont_00fe53c74ace3533c190.json.gz), [원전체 XML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/c421f89dc2ddceec5a94/source.musicxml), [원전체 IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/c421f89dc2ddceec5a94/parent_ir.json).

### 2. Beethoven sonata03 II — 분석 완료는 음악적 정답이 아님

`cont_c75feffc47980cdbdfb7`, quarter `[67,271/4)`는1.254415초에 완료했으나 주석 기준 진행은 **오답인 채 유지**됐다. 선택은 B–D♯–F♯ `[67,539/8)` → A–C–E `[539/8,135/2)` → E–G–B `[135/2,271/4)`다. 비용 `68046259/495000000`, cache2,728조회/2,718hit/10적분이며 과거와 동일하다.

B5 `sound_223f460cfe55` / `note_88fef2d9605b` `[67,269/4)`, F♯4 `sound_5fb19b467157` / `note_1b5ef64c61ae` `[537/8,269/4)`, D♯4 `sound_23fd994de19a` / `note_ecbf42e9b4da` `[269/4,539/8)`, A5 `sound_6b54e90d619c` / `note_f07fe8da9a0b` `[269/4,135/2)`를 모두 보존한다. 뒤늦은 구성음/성부 이동/경계 판단이 캐시로 개선되는 것은 아니다. 상세 conditional pattern도 `confirmed_nct=false` 계약을 그대로 유지한다.

[새 예측·오답·상세 비용](../../../output/harmony-exact-beat-train-2026-10-06-r1/cases/cont_c75feffc47980cdbdfb7.json.gz), [원전체 XML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/be2c6ed93388f5ce8d17/source.musicxml), [원전체 IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/be2c6ed93388f5ce8d17/parent_ir.json).

### 3. Beethoven quartet op18-1 I — 많은 hit에도 시간 보류

`cont_195ab0306a75a682b13e`, quarter `[2519/4,632)`, 원1,760edge. Cache51,303조회/51,293hit/10적분으로 중복은 줄었으나 guarded20.161844초에 보류됐다. **Winner/cost는 null**이다. 저장 target이나 이전 다른 모델의 경로를 예측으로 대신 반환하지 않는다.

앞서 살아 있는 F4 `sound_acba34926454` / `note_814192258b83`와 A♭4 `sound_cf16892c52fb` / `note_ff359333e1d8`는 `[1259/2,630)`, B4 `sound_28daad5c0200` / `note_69853cef6bab`는 `[2519/4,630)`, 다음 E4 `sound_d02cc029b7d3` / `note_9da63b6e9a1d`, G4 `sound_a52af97faa98` / `note_bb09b7470969`는 `[630,631)`다. Scope 시작 이전 onset이 살아 있는 음도 원전체 IR로 추적한다. 부분 악보로 새로 자르지 않는다.

[새 보류·cache 진단·원본 연결](../../../output/harmony-exact-beat-train-2026-10-06-r1/cases/cont_195ab0306a75a682b13e.json.gz), [원전체 XML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/1ba2f63511fc8a4457a0/source.musicxml), [원전체 IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/1ba2f63511fc8a4457a0/parent_ir.json).

## 결정과 다음 순서

1. 이번 cache는 실제 전체 Train에서 의미·비용을 보존했지만 보류 복구는0이다. 이를 새 음악적 정확도 개선이나 운영 승격으로 제시하지 않는다.
2. 예정된 **고정 Dev를 같은20초/2M/6raw로 재분석**해 계산 coverage와 공통 완료 동등성을 확인한다. 현재 Dev를 이용한 계수/후보/특징 조정은 하지 않는다. 이미 노출된 Dev이지 독립 Test가 아니다.
3. 그 뒤에는 작은 최적화에 계속 붙들리지 않고 큰 Train 화음/NCT 오답을 우선한다. 고정 점수의 계산 문제와 후보/점수/국소 조성의 음악적 문제를 분리한다. 후보 정답 포함률·선택 오류·unknown을 함께 보고한다.
4. 전체 Roman/기능/전위·국소 조성 계약과 독립 성능이 갖춰진 뒤 Claude 편곡의 참고 입력 및 A/B를 진행한다. UI/운영 엔진 교체·기둥음/프레이즈에 불확실한 결과를 강제 투입하지 않는다.

사용자에게 새 음악 해석을 확정해 달라는 요청은 이번 단계에 필요하지 않았다. 새 음악적 가설을 비교해야 하는 단계에서 전체 악보로 피드백을 요청한다.

## 사후 감사·봉인·보존

[사후 감사](../../../output/harmony-exact-beat-train-2026-10-06-r1/post-seal-audit.json) PASS·exit0이다.4,736고유SHA를 확인하고4,730봉인 입력을 재로드했다.118scope/23전체source/60,129원edge, 과거542저장경로를 빠짐없이 포함한644상세비용,555scalar/role projection 및 pair 값·근거·비용, 공통102승자·DP진단 동등성, 예측 선봉인, 전체/공통 집계를 재현했다. 새 search/fit/Dev0이다.

실제 run의4,612input/238artifact/451code pins를 유지했다. Actual/감사 실패0·실행 시작 후 새4코드 수정0이다. UI·운영 weights·원 Core·원 주석·부모 봉인 결과·권한·서버·Claude Phrase/Motif/Composition·MusicSearch·별개 기존 tracked dirty5를 보존했고, merge/commit/push/API 호출0이다. 문서는 별도 화성 **개발** 폴더에만 누적했다.

| 정본 | SHA-256 |
|---|---|
| [report](../../../output/harmony-exact-beat-train-2026-10-06-r1/report.json) |`09d170b697ca3190c850da76a646946eff75b52fd2585ad10ec8435fb67a9cce`|
| [run contract](../../../output/harmony-exact-beat-train-2026-10-06-r1/run-contract.json) |`5dd8130a63ccb6ee9502c02ae34fe0c51d9170a2d038ef282419d529ea0618ed`|
| [prediction freeze](../../../output/harmony-exact-beat-train-2026-10-06-r1/prediction-freeze.json) |`53ff1b5ad4d11154b63f0becbb389786469e363461c9c31817344113616b5528`|
| [audit](../../../output/harmony-exact-beat-train-2026-10-06-r1/post-seal-audit.json) |`5770611df3045023f1a56be21d816fa192101e53b38fc37a5982863ea15027ef`|
| [validation](../../../output/harmony-exact-beat-train-validation-2026-10-06-r1.json) |`a8abaf740f7039b2d901754ace6c098ea90f35d75468e4ea264f4ff0704fdb94`|

고정 모델의 원SHA는 `b6ff68e73bf6b5b9760107344f66f5c5626da2aa5c8b93ca061c21d6cbc74f38`이며 새 모델 파일을 만들지 않았다. 부모 단계90의 report/audit와 단계88의 report/model/freeze/audit도 모두 pin 검증했다.

## 재현 절차

기존 결과 폴더를 덮어쓰지 않으므로 새 output 경로를 사용한다. 봉인된 기존4코드와 부모 자료의 SHA가 같아야 실행된다. 동일 wall guard라도 당시 부하에 따라 완료 집합이 달라질 수 있다.

```powershell
$env:PYTHONPATH='src;tests'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_exact_beat_train.py --prior-validation output/harmony-exact-beat-validation-2026-10-06-r1.json --output output/harmony-exact-beat-train-validation-new.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_exact_beat_train_trial --output output/harmony-exact-beat-train-new --validation output/harmony-exact-beat-train-validation-new.json
.\.venv\Scripts\python.exe -B scripts/audit_harmony_exact_beat_train.py --root output/harmony-exact-beat-train-new
```
