# J3c — 장식음 소비 계약·계산 타일과 같은 평가 구간의 복구 실험

기록 ID: **HARM-DEV-20261004-57** · 2026-10-04.

상태: **연구용 복구 경로 구현·실제 paired 평가·6문맥 fresh 재실행 완료**. 긴 문맥 문제가 모두 해결된 것은 아니다. 기존 60개 선택은 그대로 보존했고, 이전 추론 보류 6개 중 1개만 선택으로 복구했다. 아직 운영 viewer/production에 적용하지 않는다.

## 1. 문제와 이번 범위

[J3b 확대 기준선](2026-10-04-expanded-score-benchmark.md)은 15악보/9명명 기반 작품군 중 14악보/8가족이 source-ready였다. 72동결 문맥에서 60선택, 추론 보류6, source 보류6이었다. 특히 드문 seed lane의 연속3attack이 다른 성부의 긴 진행 전체를 감싸는 문제와 grace의0음가를 일반 지속음 오류로 취급하는 문제가 드러났다.

이번에는 새 작품/유리한 구간을 고르지 않고 **동일72문맥·동일 reference/unknown mask**를 사용했다. 복구 엔진에는 관찰 IR와 frozen sample만 전달한다. 작품 제목·번호·특정 마디·주석 정답을 조건으로 하는 규칙은 없다.

- 기존60선택: checksum-sealed prediction의 값을 그대로 재사용하는 control.
- Source-preflight 보류6: 복구 시도하지 않음. K283 중복 measure/local onset과 원 holdout 제외를 유지.
- Source-ready 추론 보류6: 새로운 bounded recovery를 실제 실행.
- 모든 새 prediction packet을 저장·봉인한 뒤에만 J3b의 주석 포함 report를 읽어 비교.
- 이미 노출된 개발 자료의 **fallback arm 비교**다. 새 엔진 단독 전곡/독립 blind test가 아니다.

기존 J2e 후보 공급·고정 음악 비용·기능적 해결 점수 함수를 재사용했다. J2f 학습 weights는 여전히 미채택이다. 새 학습·가중치 tuning·외부 API·권한/split 변경·Core migration·Git push는 하지 않았다.

## 2. 일반 장식음 규칙: 원본 보존과 소비 경로 분리

`grace_projection()`은 정식 Canonical IR를 고치거나 grace를 NCT로 확정하지 않는다. 부모 IR는 계속 보존하며, positive-time 계산용 consumer view를 별도로 만든다.

분리 가능한 sound의 필수 조건은 다음과 같다.

1. 원 sound의 `[start,end)`가0길이이고 저장된 sounding duration도0.
2. 모든 source note가 실제 존재하고 `grace.is_grace=true`.
3. 해당 note의 notated duration이0이고 onset이 sound의 시각과 동일.
4. Tie-chain으로 양의 지속음에 연결된 것이 아님.
5. 같은 source note가 다른 positive sound에도 사용되지 않음.

통과한 sound/note의 **원 ID·원 객체·anchor/order/slash 등 원 grace 정보·source reference**를 `grace_projection` receipt에 저장한다. 부모 snapshot은 전체 note/sound를 그대로 갖는다. 계산 view의 note/sound/attack/voice event list/chord group에서만 대응 요소를 분리한다. 이를 새로운 formal IR revision으로 저장하거나 schema-valid Core로 주장하지 않는다.

`performed_timing=null`이다. 0음가를 임의의16분음표로 늘리지 않으며 grace pitch에 실제 sounding exposure가 있었다고 가정하지 않는다. Positive-duration grace는 보통 음표로 바꾸지 않고 기존 unsupported 표식을 유지한다. Zero-duration non-grace·누락 source·불일치 clock·tie 혼합·음가 음수는 명시적으로 거부한다.

중요한 추가 방어: grace를 계산 view에서 빼면서 양쪽 음 사이에 가짜 direct voice link가 생기면 안 된다. 원 grace의 동일 part/voice와 clock이 끼어 있는 **경과/보조 triple 및 기능적 해결 direct link를 보류**한다. 따라서 이번 구현은 장식음의 음악적 기능 판정/시간 추정 완료가 아니다.

## 3. 일반 계산 타일 규칙: 화음 분할과 구별

`tile_plan()`은 frozen context를 정확한 quarter 유리수로 끝까지 계획한다. 원 attack/release와 measure start가 계산 grid를 만든다. Measure start를 추가하는 것은 긴 지속음/쉼 사이에서도 계산 범위를 만들기 위함이지 매 마디 화음 변경을 강제하는 것이 아니다.

각 타일은 최대12cell이며 기존 `harmony_path_context`의16denominator-unit/128sound 관문을 실제 통과해야 한다. 모든 part의 교차 sound를 사용한다. 타일 시작의 `carried_sound_refs`와 실제 `attack_sound_refs`는 따로 기록한다.

- 원 sound의 onset/release/tie duration/source IDs를 잘라 새 event로 만들지 않는다.
- 셀 노출시간만 `[max(start),min(end))`로 적분한다.
- 이전 타일에서 시작한 sound는 continuation이며 새 attack이 아니다.
- 타일별 최종 화음을 고른 후 이어붙이지 않는다.
- 각 타일 안의 모든 연속 interval에 기존 candidate catalog를 실행한다.
- Catalog 원본 hash·candidate ID·alternative index·provider·origin pointer·후보/관찰 span을 저장하고, 모든 part의 event coverage를 대조한다.
- 각 타일의 Edge를 **한 global Problem**에 연결하고 기존 run-aware functional decoder를 한 번 실행한다.
- 인접 Edge의 root+spelled member signature가 같으면 타일 seam을 넘어 하나의 harmonic run으로 합집합 비용을 계산한다. Direct 해결 근거도 원 source clock에서 얻는다.

### 사전 고정한 자원 계약

| 항목 | 이번 값 | 의미 |
|---|---:|---|
| 타일 cell | 12 | score-derived 계산 범위 제한 |
| 전체 context cell | 64 | 초과 시 전체 보류, 뒤 범위 삭제 없음 |
| 전체 positive sound | 256 | 초과 시 보류, 상성부/top-k 선택 없음 |
| 전체 후보 Edge | 20,000 | 초과 시 보류, 일부 후보를 성공처럼 사용하지 않음 |
| Global raw Edge budget | `6 × tile_count` | 새로운 명시 계약; 이전 global6과 같다고 주장하지 않음 |
| Decoder 전이 | 2,000,000 | 기존 cap 유지; 초과 시 exact optimum/선택을 주장하지 않음 |

Raw Edge 수는 음악적 화음 수와 다르다. 계산 seam을 통과하기 위해 같은 화음도 여러 Edge를 사용할 수 있다. 비용은 합쳐진 run에 적용한다. 이번 graph는 타일을 가로지르는 단일 후보 Edge를 직접 공급하지 않으므로, 같은 화음이 이어지려면 해당 signature가 각 타일에서 공급되어야 한다. 타일별 근음/3음 부재로 후보가 끊기는 문제는 **미해결**이다.

이 경로는 기존 sampled lane의 exhaustive assignment 관문을 성공이라고 덮어쓰지 않는다. 그 단계와 별개의 **score-bound 후보 adapter**다. 새 화성 비용의 voice 특징은 full source에서 clock-consistent·명시 voice·unambiguous direct geometry를 만족할 때만 사용하며 나머지는 None/보류로 둔다. 전체 polyphonic NCT 설명이나 성부 진행 제약의 완전 검증은 아니다.

Repeat/ending·meter change·measure gap 등의 전체 문맥 관문은 유지한다. 계산 타일로 나뉘었다는 이유만으로 반복을 건너뛰어 음을 잇거나 조성을 확정하지 않는다.

## 4. 같은72문맥에서의 실제 결과

정본: `output/harmony-bounded-recovery-2026-10-04-r1/report.json`.

| 지표 | J3b control | J3c fallback arm |
|---|---:|---:|
| 평가 문맥 / 완전 reference | 72 /51 | 72 /51 |
| 선택 /보류 | 60 /12 | 61 /11 |
| 완전 구간 일치 | 15/51 (29.41%) | **15/51 (29.41%)** |
| Root 시간 일치 | 32.87% | 33.22% |
| Root+members 시간 일치 | 23.99% | **24.34%** |
| Prediction 시간 coverage | 41.05% | **41.47%** |
| Root+members 작품군 macro | 44.77% | 45.85% |
| 완전 reference 후보망 ceiling | 33true /15false /3unknown | 36true /15false /0unknown |
| 의미 경계 TP /FP /FN | 48 /18 /15 | 49 /19 /14 |
| 경계 F1 | 74.42% | 74.81% |
| 실행 exception | 0 | 0 |

근음·구성음 적격 시간 분모는 기존 유리수 그대로다. 복구된 노출은 **3/2quarter**, 새 정답 일치 노출은 **5/4quarter**다. 완전 일치 수는 늘지 않았다. 전체 후보망 ceiling의 증가3개도 실제 정답 선택3개가 아니라 표현 가능성을 확인한 것이며, 2개는 여전히 decoder 예산 보류다.

32분 grid는 eligible2855 그대로, root match938→948, root+members685→695, covered1171→1183이다. Quality/inversion/local key/degree/full Roman은 적격0이므로 정확도는 null이며 성공/실패 비율로 바꾸지 않는다.

새로 분석된1문맥은 G minor → E-flat major까지 맞고 마지막1/4quarter를 G minor로 다시 잘못 변경한다. 따라서 **분석 가능 복구와 완전 음악적 정답을 구별**한다. 기존60control과 그 정답/오답은 모두 그대로다.

### 6개 실제 복구 시도

아래 IDs/곡명은 재현 사례의 식별자이지 알고리즘 조건이 아니다. 시간은 global quarter `[start,end)`다.

| 사례 | Span | 관찰/후보 상태 | 실제 선택 상태 |
|---|---|---|---|
| Quartet n06, `cont_12258980adb87c2e81fa` | `[59/2,118)` | 49타일/583points, global cell/sound cap | 보류 유지 |
| Quartet n06, `cont_e7191dd5889497e23dc1` | `[167/2,175/2)` | 4타일/42points/9,154Edge, reference 진행 공급 확인 | 2M 전이 보류 |
| Sonata07-2, `cont_f3c7cdac22d1e8650885` | `[105,109)` | 3타일/27points/3,790Edge, grace 입력 분리·reference 진행 공급 확인 | 2M 전이 보류 |
| Chopin op50-1, `cont_bd6b83571ed9664c9265` | `[279/2,141)` | 1타일/5points/159Edge,2,748전이 | 선택 복구;5/4q 정답·1/4q 오선택 |
| Chopin op50-2, `cont_0cdcf828cc361186885c` | `[74,148)` | 10타일/118points, global cell cap | 보류 유지 |
| Chopin op50-2, `cont_4deb605150276b91af16` | `[281/2,211)` | 11타일/121points, global cell/sound cap + repeat barrier | 보류 유지 |

Grace receipt의 count는 **전체 score consumer projection** 기준이다. 예를 들어 Sonata07의20grace가 모두 해당4quarter 안에 있다는 뜻이 아니다. 해당 source snapshot으로 범위를 대조해야 한다. 그 악보 전체에서 원 grace를 넘어가는17ornament triple/14direct link가 보류됐고 Chopin op50-1은7/5개였다.

후보 oracle의 `reference_reachable_selection_error` 문자열은 `selected_hit=false`인 경우를 넓게 묶는다. 이 중 위2개는 **음악적 오선택이 아니라 실제 decode 미완료/자원 보류**이며 반드시 row `status`와 함께 해석한다. 정답 진행의 witness는 gold를 사후 사용한 진단이지 선택 결과가 아니다. 새 adapter의 `retained24_measured=false`; 원 보존24와 비교하지 않는다. Oracle의 `unspelled_candidates_preserved=0`은 supplied graph의 빈 목록을 뜻하며 원 catalog에 spelling 없는 후보가0이라는 조사 결과가 아니다. 별도 raw unspelled inventory 확장은 미완료다.

## 5. 구현 파일과 검증

- `src/musicanote_harness/harmony_bounded_recovery.py`: 별도 grace 소비 view·full-clock evidence binding·타일 계획·source-bound candidate adapter·global joint decode.
- `src/musicanote_harness/harmony_bounded_recovery_trial.py`: 같은 frozen scope fallback runner·control 재사용·source 관문 유지·모든 예측 봉인 후 평가.
- `tests/test_harmony_bounded_recovery.py`: 신규27검사.
- `scripts/audit_harmony_bounded_recovery.py`: metric/분모/reference mask/control/SHA 검증 및6개 fresh inference 재실행·전체 source 사례 보존.
- 이 record, 메인 README, 개발 로그와 장기 계획의 작은 현재 상태 요약.

기존 parser·catalog·점수 함수·decoder·운영UI 코드를 수정하지 않고 새 모듈을 추가했다. 기존5개 tracked dirty 파일 중 장기 계획의 현재 상태 요약 외의 별도 변경은 건드리지 않았다.

검사에는0grace/positive grace 구별, 원 객체/ID 보존, 잘못된 source/tie/음가 거부, 가짜 voice link 억제, 모든 part/time coverage, carry와 attack 구별, repeat/meter/coverage 관문, 원 범위 끝 보존, cell/sound/candidate/전이 cap, 타일 간 same-signature run, 작은 graph exhaustive optimum, poisoning label 비사용, 실제 disk seal 순서, error 분모 유지·물리 snapshot tampering 등이 포함된다.

신규27검사는1.958초에 통과했고 관련 전체 회귀382검사는11.570초/exit0으로 통과했다. 이 숫자는 음악 정확도나382곡 통과를 의미하지 않는다.

최종4개 Python AST·8개 파일 strict UTF-8/깨진 문자·trailing whitespace·문서291local link 검사가 통과했다. 누락 링크/텍스트 문제0,680SHA 재확인 변경0, tracked diff whitespace 검사도 통과했다. 문서 연결 patch의 부분 적용 메시지 뒤 실제 파일 상태를 재확인하고 장기 계획 요약을 별도 적용했으며 중복 entry는 없다.

실제 paired run은 **162.033초/exit0**이었다. Quartet 4quarter의 dense graph는104.993초, Sonata07의4quarter는41.019초 후2M cap에서 보류됐다. 따라서 작은 타일만으로 빠른 inference가 확보됐다고 주장하지 않는다. 실제6회 fresh inference가 저장 prediction과 정확히 같고 72scope·60control·reference mask·metric이 재현됐다. **680고유 SHA guard가 종료/감사 모두 불변**이었다.

## 6. 재현 자료·사례 보존

출력 폴더: `K:/Music Analysis/output/harmony-bounded-recovery-2026-10-04-r1/`.

- `run-contract.json`, `prediction-freeze.json`, `predictions/*.json.gz`, `report.json`.
- `diagnostics-r1/audit.json`:72문맥 exact 재채점과6개 실제 재실행.
- `diagnostics-r1/cases/`: 복구 시도6개의 **전체 원 MusicXML 사본·전체 관찰 IR gzip·원 source IDs·평가/타일/grace/선택**. 앞뒤 context를 삭제한 짧은 텍스트만 저장하지 않는다.
- 이번 산출물은 기존 악보 viewer에 연결된 새 화면이 아니다. Root/member 평가 결과를 임의의 Roman/local key로 바꿔 표시하지 않는다.

주요 pins:

| 대상 | SHA256 |
|---|---|
| J3b control report | `71926c9155b81fd1d9792ec6cf1b79c31a1b9aa2e45c636e31e227990f3bf182` |
| J3c paired report | `a3bbd1ab7f6083e2ce5a3554396efb34f1620e51b72d1b8b36762dfa83f0d31f` |
| Recovery engine | `86b1a1f22efe53c720d001ab13c979c17c5f6cb80fdddcc55ed447b79ba57348` |
| Recovery runner | `3687aa42ce57a2b614d5a97a2f242c6e6ef88c9ca5d05d352de168a7fa5c91e8` |
| Auditor | `fe2dd04251a3ac8a097927a7e8694f6c8a3a17af4986c3a1d3d57678fe6e60c3` |
| Audit result | `7dee7e9d20976b1d764251e0208e5c1074cb9a934582bb978f04f565a0e70fa6` |

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m unittest test_harmony_bounded_recovery
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_bounded_recovery_trial --source output/harmony-expanded-benchmark-2026-10-04-r1 --output output/harmony-bounded-recovery-2026-10-04-r2
.\.venv\Scripts\python.exe -B scripts/audit_harmony_bounded_recovery.py --source output/harmony-bounded-recovery-2026-10-04-r1 --output output/harmony-bounded-recovery-2026-10-04-r1/diagnostics-r2 --replay
```

예시 r2/diagnostics-r2는 재현 시 **새 출력 폴더**다. 이미 존재하면 덮어쓰지 않는다. 기존 source/코드 hash가 달라지면 검증을 거부하며 원 정답을 clock-snap하거나 새 source revision으로 조용히 치환하지 않는다.

## 7. 결정과 다음 큰 작업

Grace 소비 계약과 tile carry/global joint 연결의 기본 구현은 완료했으나 **전체 long-context/실시간 성능 해결은 미완료**다. 운영 승격을 보류한다. 사용자에게 새 음악적 의견을 받아야 실행할 수 있는 blocker는 현재 없다.

다음은 단순 cap 확대나 타일 winner 이어붙이기가 아니라 **긴 문맥의 joint state/search 규모를 줄이는 계산 방식**이다.

1. 실제 dense context에서 상태 수·run-start/공통 prefix 중복·candidate signature 수·전이 비용을 측정한다. 정답 라벨이 아니라 계산 geometry로 계획한다.
2. 먼저 선택 의미가 같은 exact state 공유/계산 재사용을 검토한다. 그것만으로 부족하면 명시적인 bounded approximate joint search를 별도 arm으로 만든다.
3. 근사 arm은 pruning/state budget·대안 손실·unknown을 명시하고 `exact_optimum=false`로 표시한다. 타이·원 onset/release·같은 run·원 voice evidence는 계속 이어간다.
4. 장문 안의 근음/3음 부재 타일에서도 앞뒤 candidate를 전달할 수 있는 상태 인터페이스가 필요하다. 전달을 화음 확정/음표 삭제/조성 확정과 혼동하지 않는다.
5. 같은72scope 및 추가 여러 작품에서 시간 coverage와 후보 포함/실제 선택 정확도를 구별하여 검증한다. 기존 source/unknown mask·권한·holdout을 유지한다.
6. 이후 큰 후보 부재15/실제 선택 오류 및 공개 모델 native adapter 비교를 진행한다. 교향곡 이조/source 검증·full Roman/key/inversion 평가·음악적 역할과 작곡/편곡은 장기 범위에 남는다.

작은1/4quarter 오선택을 이 악보용 조건으로 고치기보다, 큰201quarter 미분석 범위와 dense 선택기 보류를 먼저 해결한다. DCML 내부 연구/NC 조건·외부/상업 이용 미승인은 그대로다.
