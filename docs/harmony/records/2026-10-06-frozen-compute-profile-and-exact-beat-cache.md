# 단계90 — 고정 점수의 계산 병목 측정과 박자 환산 재사용

## 결론과 적용 상태

단계89 다음 관문인 **같은 점수의 일반 계산 개선**을 진행했다. 과거 Train 시간 보류16구간 전부와 완료 control4구간을 측정하니, `beat_extent`가537,222회 호출되고 계측된 guarded 계산464.3050초 중191.6051초(약41.27%)가 해당 함수에서 사용됐다. 서로 다른 뒤 화음 후보에서도 같은 앞 구간의 박자 길이를 반복 계산하는 것이 큰 병목이다.

원 계산식을 그대로 재사용하는 **연구용** 구현을 추가했다. 원118 Train/23전체악장 source/15작품군/60,129edge의 저장된542경로·471전이를 대조해 상세 근거·availability·Fraction 비용이 동일함을 확인했다. 최종968관련검사/92모듈·사후4,491고유SHA 감사 PASS다.

**이번에 속도 향상·시간 보류 복구·정확도 향상을 측정한 것은 아니다.** 계측된20검색은 기존 엔진이다. 새 구현에서는 작은 fixture의 전체 탐색과 실제 저장 경로 재현만 수행했다. 원118 전체 fresh 선택과 고정 Dev 비교는 다음 단계다. UI·운영·Claude 편곡 연결은 계속 보류한다.

## 1. 측정 계약과 전체 범위

고정 모델은 단계88 순위 보호35, SHA `b6ff68e73bf6b5b9760107344f66f5c5626da2aa5c8b93ca061c21d6cbc74f38`다. 학습/가중치 탐색/새 negative나 target 탐색/현재 Dev 추론/작품 예외0이다. 부모 봉인 입력에는 노출된 Dev를 담은 과거 컨테이너가 있지만 이번 측정/최적화 판단은 원 Train만 사용했다.

선정은 **과거 시간 보류16개 전부** + **완료 graph의 edge 수 내림차순, 서로 다른 작품군에서 큰4개**다. 정답 여부·새 실행 시간·계측 결과로 선정하지 않았다. 전체20scope는13악장 package/11작품군/원46,755edge다. 20곡 또는 독립 Test라고 부르지 않는다.

기존6raw/2M feasible-state/raw-edge 비교/조건당20초 cooperative guard를 유지했다. 계측 도구 `cProfile`은 실행을 늦춘다. 실제 측정538.894749초/exit0, guarded464.305035초, source 준비61.411889초, scorer 생성1.496120초다. 결과1완료/19wall이며 원 완료control4개 중3개도 계측 상태에서는 보류됐다. **이는 새 캐시의 퇴행이나 coverage 평가가 아니다.** Cooperative guard라 단일 호출이 길면20초를 넘을 수 있고 최댓값38.935초였다. 부분 승자 반환은 하지 않았다.

## 2. 병목과 실제 사례

아래는20구간 합계다. 동일 이름의 함수는 원파일/줄 번호/호출자까지 원자료에 보존했다. 상속 함수 `transition_cost`의 합에는 서로 다른 계층이 들어간다. **누적 시간은 하위 호출을 포함하므로 행들을 합산하면 안 된다.**

| 함수 | 호출 수 | 자체 시간(초) | 누적 시간(초) |
|---|---:|---:|---:|
| `_delayed` |20|29.6977|463.2013|
| `resolution_features` |536,860|3.6043|224.6957|
| `beat_extent` |537,222|19.7646|191.6051|
| `transition_cost` |354,412|0.9618|62.2049|
| scalar `values` |354,386|4.0594|15.1717|
| 역할 `observe` |177,194|3.5907|31.1643|
| `history_pareto` |109|0.7829|0.9955|

화음 pair의 key에는 앞뒤 화음 철자와 뒤 구간 끝이 들어간다. 반면 `beat_extent(source,left_start,boundary)`는 원보의 박자와 앞 구간만으로 정해진다. 서로 다른 뒤 화음 가설에서도 같은 값인데 기존 `resolution_features`는 매번 계산했다. 악장 전체 마디 시간 목록을 순회하면서 Fraction 비교가 많아진다.

- **Beethoven quartet op18-1 I**, `cont_195ab0306a75a682b13e`, quarter `[2519/4,632)`,1,760edge. 계측20.011초 중pair15.961초/해결15.251초; scalar index 생성 전에 보류됐다. 역할 점수만 최적화하면 이 병목을 놓친다. [계측·출처 packet](../../../output/harmony-frozen-compute-profile-2026-10-06-r1/cases/cont_195ab0306a75a682b13e.json.gz), [원전체 XML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/1ba2f63511fc8a4457a0/source.musicxml).
- **Beethoven sonata02-2**, `cont_4f4f6dc881cf72de3728`, `[8,13)`,4,361edge. 계측38.935초/해결22.108초/박자 환산19.314초였다. 이 경우도 scalar 계산 전 보류다. [계측 packet](../../../output/harmony-frozen-compute-profile-2026-10-06-r1/cases/cont_4f4f6dc881cf72de3728.json.gz), [원전체 XML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/dada0c930a9521988b77/source.musicxml).
- **Chopin op41-2**, `cont_f7984c3d0be3d011040e`, `[3,8)`,684edge. Scalar282계산/8,156cache hit와role4,219entry가 있다. DP/유리수·역할 계산 부담도 남는다. 한 캐시로 모든 보류가 해결된다고 추정하지 않는다. [계측 packet](../../../output/harmony-frozen-compute-profile-2026-10-06-r1/cases/cont_f7984c3d0be3d011040e.json.gz).
- **완료 control Beethoven03-2**, `cont_c75feffc47980cdbdfb7`, `[67,271/4)`,515edge. 계측5.479초에도 완료했고 문맥 비용 약3초다. Source-only 환산 최적화 뒤 문맥/DP 부담을 별도 평가해야 한다. [계측 packet](../../../output/harmony-frozen-compute-profile-2026-10-06-r1/cases/cont_c75feffc47980cdbdfb7.json.gz).

20packet 모두 rational quarter span, 기존 source clock gate, 원 graph SHA/edge 수, 전체XML/IR 경로·SHA, 과거case 경로·SHA, 함수별 원파일/줄/호출자/횟수/자체·누적 시간을 갖는다. 원 note/sound ID·철자·음가·붙임줄은 해당 봉인 전체IR로 추적한다. 음악적 해석이나 human 정답으로 승격하지 않는다.

## 3. 구현 — 원 계산의 재사용만

`harmony_exact_beat_cache.py`의 `BeatCache`는 scorer 인스턴스/원source에 한정한다.

- Key는 정확한 `(start,end)` Fraction pair다. 화음/작품 이름·정답은 key에 없다.
- 최초 조회는 원 `beat_extent`를 그대로 실행한다. Float 환산·양자화·근사 적분·템포 추정0이다.
- 변박/복합박자/못갖춘마디는 원 함수의 의미를 유지한다. 박자 정보 부족의 `None`을0으로 바꾸지 않는다. 기존 unknown-meter의 bounded resolution credit도 그대로다.
- 다른 source, 교체된 마디/박자 timeline, 비양수 span은 거부한다. Cache hit도 span 검증을 생략하지 않는다. 분석 중 원source는 불변 계약이다.
- 기존 resolution/DP/scalar 함수의 **같은 bytecode**에 인스턴스별 private dependency만 연결했다. Module global·원 함수·기존 봉인 코드/모델을 수정하지 않았다.
- 원 상세 `path_receipt`와 최종 독립 비용 대조는 캐시 없는 기존 구현으로 남겼다. 근거 축소·원음표 삭제0이다.
- 새 후보·상태 가지치기·beam·cap 확대·계수 조정·불확실성 메우기·partial winner0이다.

Role의 weighted-cost cache 등 다른 최적화는 함께 넣지 않았다. 원인이 하나인 상태에서 실제 coverage 효과부터 확인한다.

## 4. 전체 Train 저장 경로 동등성

봉인 단계88의118scope를 모두 재준비하고542개 저장 경로를 재현했다. 과거 fresh/이전 모델 경로/평가용 target 등 원 packet의 모든 named witness를 보존했다. Target은 이미 만들어진 검증 증인이지 새 예측/생성용 화성 정답이 아니다.

| 항목 | 결과 |
|---|---:|
| 원 Train scope / 전체악장 source / 작품군 |118 /23 /15|
| 원 graph edge |60,129|
| 경로·비용·상세 근거 witness |542|
| scalar/role projection와 pair 값·상세 근거·비용 대조 전이 |471|
| 근거/availability/비용 차이 |0|
| 재현 중 캐시 조회 / 적분 / hit |506 /165 /341|
| 새 실제악보 winner 탐색 / 새 fit |0 /0|

재현183.514021초/exit0다. 회귀 검사와 병렬 실행했으며 속도 대조 실험으로 쓰지 않는다. 341hit은 저장 경로 재현의 수이고 새 전체 DP의 hit 수나 보류 복구율이 아니다. 118case 모두 기존 전체source·원 note/sound ID로 이어지는 출처를 보존한다.

## 5. 검사·감사·봉인

- 신규14검사 PASS: 작은 모든경로/음수·0·양수 문맥 가중치/lex winner·raw operation 동일성, 변박/복합박자, unknown/grace0/성부 clock 불명확, 원 함수/global/bytecode 보존, cache 격리, 잘못된source/span 거부, budget 보류, 저장 경로 재현.
- 최종968관련검사/92모듈 PASS, failure0/error0·116.067931초. 전repo 검사나968곡이 아니다.
- 계측20검색·실제118scope 재현·사후 감사 실패0. 계측 시작 뒤 profiler/test2 수정0, 재현 시작 뒤 신규7code/test/script 수정0이다. 문서 패치1회의 문맥 불일치는 파일 생성 전 거부됐고 재적용했다. 실행/검사 실패와 구별한다.
- 재현4,367input/119artifact/451code pins. 사후4,491고유SHA·20profile·원118case·542경로·471전이·60,129edge·23source 감사PASS. 기존542상세 receipt 동일성과 원봉인/선정/개수 재확인·새search/fit0이다.
- 원 Core/주석/부모봉인/권한/운영·UI·서버/Claude Phrase·Motif/Composition/MusicSearch/별개 tracked dirty5/Git를 보존했다. Merge/commit/push/API0이다.

| 산출물 | SHA256 |
|---|---|
| 계측 report |`2b560ae31c7c67e23a3e676fed53d1ea0d3fd920c4a6263a13e04260bf3ec054`|
| 계측 계약 |`f9fe1a56e093e194c433710f7c0f29f56e4b804f8f53ccc4ac051b504ac944d4`|
| 동등성 report |`0257a754d782c81131e64f1f655b9b909b2d2b1cd180321df9adc080db65280a`|
| 재현 계약 |`7782042c8d5f9324dafa29d0c8a65fb778136d78839512f05dcfb7ff4df0f6fa`|
| 사후 감사 |`7b82e634c0c5ba39ff43704174b8d0101758edd578f514a745a9d487259718bd`|
| 관련 회귀 |`3a32e1e5eca188ebcca922bc285ed3e2ab85bc693ea7dbd013a192fa5d7255cc`|

[계측report](../../../output/harmony-frozen-compute-profile-2026-10-06-r1/report.json), [동등성report](../../../output/harmony-exact-beat-replay-2026-10-06-r1/report.json), [감사](../../../output/harmony-exact-beat-replay-2026-10-06-r1/post-seal-audit.json), [회귀검사](../../../output/harmony-exact-beat-validation-2026-10-06-r1.json). Mutable progress는 봉인 정본이 아니며 report/감사가 정본이다.

## 6. 다음 관문

1. 같은 모델의 캐시 구현으로 원118 Train 전부 **fresh ordinary 선택**한다. 같은20초/2M/6raw·참조 없는 선택·모든보류 유지, 후보 축소/시간 확대0이다.
2. 원 완료 경로 ID/점수/근거·상태/operation 동일성을 비교한다. 새완료/이전완료 소실·전체 coverage/정확도와 공통완료 지표를 구별한다. 과거 시간은 controlled speed benchmark로 부르지 않는다.
3. 같은 고정 Dev 전체를 확인한다. 좋은 일부 작품만으로 채택하지 않고 Dev fit을 하지 않는다. 독립 Test는 별도다.
4. 남는 DP 상태/유리수·문맥 반복과 큰 Train의 화음 유지/교체·실제7음·NCT 경쟁 설명을 구별해 보완한다.

책 규칙 추가/전체NCT 정확도 검증 단계는 아니다. 다음 fresh 평가 전까지 운영 승격/편곡 자동 소비를 하지 않는다.

## 구현 파일과 재현

신규7파일은 `src/musicanote_harness/harmony_frozen_compute_profile.py`, `harmony_exact_beat_cache.py`, `harmony_exact_beat_replay.py`, `tests/test_harmony_frozen_compute_profile.py`, `test_harmony_exact_beat_cache.py`, `scripts/validate_harmony_exact_beat_cache.py`, `audit_harmony_exact_beat_cache.py`다.

PowerShell, `K:\Music Analysis`에서 새 output 이름으로 실행한다. 기존 봉인 파일을 덮어쓰지 않는다. 계측과 무거운 작업은 동시 실행하지 않는다.

```powershell
$env:PYTHONPATH = 'src;tests'
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_frozen_compute_profile --output output/harmony-compute-profile-NEW
.\.venv\Scripts\python.exe -B scripts/validate_harmony_exact_beat_cache.py --prior-validation output/harmony-ordinal-protection-dev-validation-2026-10-06-r1.json --output output/harmony-beat-validation-NEW.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_exact_beat_replay --profile-root output/harmony-compute-profile-NEW --output output/harmony-beat-replay-NEW
.\.venv\Scripts\python.exe -B scripts/audit_harmony_exact_beat_cache.py --root output/harmony-beat-replay-NEW --profile-root output/harmony-compute-profile-NEW
```

선행 [단계89](2026-10-06-ordinal-protection-dev-check.md), 정본 [화성 메인 개발 문서](../README.md)와 [화성 개발 로그](../DEVELOPMENT_LOG.md).
