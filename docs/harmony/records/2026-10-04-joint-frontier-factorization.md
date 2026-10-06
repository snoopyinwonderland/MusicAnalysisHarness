# J3d: 공동 탐색의 정확한 계산 재사용과 밀집 구간 복구

기록: HARM-DEV-20261004-58 / 2026-10-04. 화성 분석 **개발 기록**이며 인수인계 문서가 아니다. [직전 J3c](2026-10-04-bounded-context-and-grace.md)의 고정72구간을 그대로 사용한다.

## 1. 결과와 결정

이전에는 계산 한도로 선택하지 못한 밀집4quarter 두 구간에서, 기존 화성 점수·후보망을 유지한 **정확 공동 선택**을 완료했다. 실제 정답 향상과 계산 완료는 구별한다.

| 같은72구간의 지표 | J3c | J3d factored |
| --- | ---: | ---: |
| 선택 / 보류 | 61 / 11 | 63 / 9 |
| 완전 평가 가능한 구간 전체 일치 | 15 / 51 | 15 / 51 |
| 근음 시간 일치 | 33.22% | 34.47% |
| 근음+구성음 시간 일치 | 24.34% | 25.34% |
| 근음+구성음 작품군 macro | 45.85% | 49.71% |
| 참조 가능한 시간의 예측 coverage | 41.47% | 43.71% |
| 의미 경계 TP / FP / FN | 49 / 19 / 14 | 50 / 29 / 13 |
| 의미 경계 F1 | 74.81% | 70.42% |

기존61개 선택은 값 그대로 재사용했다. source 보류6개와 장문/context 보류3개는 유지했다. 두 복구 구간은 모두 완전 일치 실패이며 새 오경계10개가 생겼다. **계산 복구는 성공, 음악적 정확도 개선은 제한적, 운영/UI 승격은 보류**한다.

15악보/명명 기반9작품군을 시도한 기존 범위이고 source-ready는14악보/8작품군이다. 완전51/부분21·원 reference/unknown mask·분모·split·권한을 변경하지 않았다. 새 독립 blind test, 전곡 기능화성, full Roman/전위/local key/NCT/cadence 정확도를 측정한 것이 아니다. 미지원 평가 항목의 값은0%가 아니라 null이다.

## 2. 첫 시도는 충분하지 않았다

먼저 별도 `harmony_exact_frontier.py`를 구현했다.

- 같은 endpoint/run-start/spelled signature에서 더 적은 raw edge를 쓰며 비용·동점 ID 순서도 나쁘지 않은 상태만 남긴다.
- 원 onset/release/measure 경계의 cell 적분을 재사용하여 기존 run 특징을 정확한 Fraction으로 계산한다.
- 점수·미래 상태가 동일한 raw edge를 대표 ID로 계산하되 원 후보/출처는 보존한다. 음악적 기능이 같다는 뜻이 아니다.
- 남은 최소 raw edge 수로 segment cap 내 도달 불가능한 상태를 제거한다.

[첫 비교 결과](../../../output/harmony-exact-frontier-2026-10-04-r1/report.json)는 두 구간 모두2M에서 보류했다. 합계144.314초, 기존146.011초와 비슷하며 정확도/coverage는 그대로다. 실제 두 graph에서 score-equivalent duplicate edge는0개였다. 중복 제거 효과가 있었다고 주장하지 않는다. 이 실패를 남긴 뒤 점수 조정 없이 계산을 더 분해했다.

Sonata의 cProfile 재실행은121.271초/280,392,229call이다. Profiling overhead가 있어 일반 실행41초와 속도 비율을 직접 비교하지 않는다. 누적 시간에서 원 후보 생성76.492초, decoder41.328초, 그 안의 원 functional pair 평가29.790초가 컸다. 전체 악보를 interval마다 재조회하는 후보 생성은 이번 단계에서 변경하지 않았다.

## 3. 정확한 전이 factorization

상태는 기존과 동일하게 `(endpoint, raw_count, current_run_start, spelled_signature)`다. 근음과 enharmonic spelling을 유지한다.

화음이 바뀔 때, 같은 endpoint에서 같은 다음 signature·actual attack set으로 가는 후보는 다음의 이전 경로 최소값을 재사용할 수 있다.

```text
best[count, next_signature, attacks]
  = min(previous states with a different signature)
      prefix_cost
      + transition(previous_signature, next_signature, attacks)
      + functional_pair(previous_run_start, boundary, next_signature)

destination cost
  = best + new_run_cost(boundary, edge_end, next_signature)
         + original_edge_blocker_cost
```

각 raw count를 별도로 보존하므로 segment cap 조건이 바뀌지 않는다. Edge별 blocker와 끝 위치는 최소값을 구한 **뒤**에 각 원 edge에 더한다. 서로 다른 actual attack set을 합치지 않는다. 같은 signature를 연장할 때는 과거 run-start에 따라 합집합 특징이 달라지므로 위 최소화로 합치지 않고 그대로 계산한다.

이 계약은 기존 `pair_features`가 다음 raw edge의 end가 아니라 **선택된 경계 도착과 원 source의 전체 음표 clock**을 평가한다는 조건에 의존한다. 미래 feature version이 destination duration을 사용하면 이 factorization을 재검토해야 한다.

Pareto 증명: 같은 endpoint/run-start/signature에 도착한 A가 B보다 raw count가 작거나 같고 비용·동점 path ID 순서도 나쁘지 않으면, 동일 suffix의 모든 추가 비용과 run 교체 비용이 같고 A의 cap 여유가 더 크다. 양의 DAG에서 같은 endpoint의 경로는 서로의 prefix가 될 수 없으므로 공통 suffix를 붙여도 lexicographic tie-break가 보존된다. 음수 기능적 bonus가 있어도 성립한다. 더 적은 edge지만 더 비싼 경로, 같은 비용이지만 ID 순서가 더 나쁜 짧은 경로를 무조건 제거하지 않는다.

Beam/top-N/음표 pruning·gold insertion·조성/성부 guessing·타일별 winner stitching은 없다. 선언한 graph와 고정 점수의 optimum이지 음악적 최종 정답을 뜻하지 않는다.

## 4. 원 score/evidence의 보존

- RunIndex는 원 음표의 attack 시점 박절을 사용한다. 타이·타일 seam에서 새 attack을 만들지 않는다.
- 모든 양의 지속음/measure 경계가 fine grid에 없으면 거부한다. float rounding/누적 근사는 하지 않는다.
- missing metric/key/spelling/voice evidence의 None과 조건부 ornament의0/None을 구별한다.
- ornament의 준비·해결 전체 clock containment, 원 sound/note IDs와 grace 때문에 보류된 link를 유지한다.
- Functional pair의 계산 index만 frozen span과 교차할 수 있는 row·내부 경계의 direct link로 좁힌다. 이 범위 밖 row는 어떤 가능한 pair에도 소비되지 않는다.
- carry-in과 frozen end 뒤까지 지속되는 sound는 **원 start/end 그대로** 남는다. Core/전체 source evidence/neighbor row/권한/주석은 수정하지 않는다.
- 최종 선택 경로를 원 unindexed functional decoder로 다시 계산한다. 원 score 또는 path IDs와 다르면 fail closed한다. 이 검사는 선택 경로의 비용 재현이며 모든 실제 후보의 정답을 보증하는 검사는 아니다.

## 5. 계산 한도 단위와 실제 실행

숫자 한도2,000,000은 유지하지만 **카운터의 단위가 바뀌었다**. 이전은 논리적 raw arc 방문 수, 새 방식은 predecessor 비교·factored edge emission·same-run extension의 실제 연산 수다. 동일 단위의2M 전이를 더 많이 허용한 것으로 표현하지 않는다. 두 수를 함께 기록한다. 후보64cell/256sound/20kEdge·raw6×tile 관문은 그대로다.

| 원 frozen 구간 | 원 graph | factored 연산 | 나타내는 논리 전이 | 기존 중단 시간 → 새 완료 시간 |
| --- | ---: | ---: | ---: | ---: |
| Quartet n06op18-6_02 `[167/2,175/2)` | 42points / 9,154edges | 1,282,141 | 3,665,360 | 104.993s → 90.420s |
| Sonata07-2 `[105,109)` | 27points / 3,790edges | 675,552 | 2,199,343 | 41.019s → 30.971s |

두 구간 합계146.011초에 **중단**되던 것이121.391초에 **완료**되었다. 전체 paired run은125.428초/exit0이다. 같은 완료 작업끼리의 엄밀한 처리량 benchmark 또는 실시간 성능 보장은 아니다. 같은 컴퓨터의 background 부하 차이도 있을 수 있다.

Quartet의 pair index는1,917→50row/1,428→40link, Sonata는2,053→41row/1,053→15link다. 모든 part의 frozen 관측은 보존하며 저음/내성부를 없애서 줄인 수가 아니다. 원 전체 XML/IR은 별도 사례에 남긴다.

## 6. 실제 선택 실패와 다음 개선의 근거

### Quartet: 계산이 끝나니 과분할이 드러났다

원 참조는4quarter 전체의 Bb7 하나다. 새 선택은11개 harmonic run/13raw edge로 쪼개졌다. 처음 `[167/2,1009/12)` Bb7을 잡지만 짧은 Eb major·E diminished·F minor 등의 후보로 계속 교체한다. 시간상 근음 일치23/24quarter, 근음+구성음 일치7/12quarter이고 추가 경계10개다.

참조를 표현하는 원4edge witness는 후보망에 실제 존재한다. 따라서 이제 이 사례는 **후보 부재/자원 미확인**이 아니라 **선언 점수의 선택 오류**로 분류할 수 있다. NCT/보조음·분산 표면 변화와 실제 화성 교체 경쟁의 근거를 보완해야 하며 이 악보에만 Bb7을 고정하는 규칙은 금지한다.

### Sonata: 첫 G minor는 회복했지만 다음 두 화음을 합쳤다

참조: G minor `[105,108)` → G# diminished seventh `[108,217/2)` → E7 `[217/2,109)`.

선택: G minor `[105,108)` → root E·members E/G#/B/D/F `[108,109)`.

첫3quarter는 근음+구성음이 일치한다. 후반은 두 해석을5구성음 후보 하나로 합친 오선택이다. 전체 근음 일치7/2quarter, 근음+구성음3quarter다. 원 참조의4edge witness가 존재한다. 추가 탐색 비용이 아니라 **applied diminished/해결·arrival membership·화음 과병합 경쟁 점수**의 문제다. 조표와 국소 조성/Secondary 확정을 혼동하거나 이 특정 구간을 예외 처리하지 않는다.

둘의 근음+구성음 시간 개선 합계43/12quarter, coverage 증가8quarter다. 기존61선택을 유지한 paired 복구 설계여서 이전 선택의 회귀를 여기서 시험한 것은 아니다. 모든 작품에 새 backend를 적용했을 때의 검증은 별도다.

## 7. 파일과 재현

새 코드:

- [정확 prefix·Pareto backend](../../../src/musicanote_harness/harmony_exact_frontier.py), [첫 paired runner](../../../src/musicanote_harness/harmony_exact_frontier_trial.py)
- [전이 factorization backend](../../../src/musicanote_harness/harmony_batched_frontier.py), [factored paired runner](../../../src/musicanote_harness/harmony_batched_frontier_trial.py)
- [fresh replay·source/graph/mask/지표 audit](../../../scripts/audit_harmony_batched_frontier.py)
- tests의 `test_harmony_exact_frontier`, `test_harmony_exact_frontier_trial`, `test_harmony_batched_frontier`, `test_harmony_batched_frontier_trial`

최종 신규60+이전382=**442검사 통과/20.720초**다. 두 backend 각각30개의 고정 난수 tiny DAG의 모든 완성 경로와 최적 비용·동점 ID를 대조한다. 모든 toy interval의 원 특징/패턴·triplet/tie/carry·None·grace·cap·negative bonus·source tamper·reference seal·61control 재사용을 확인했다. 첫 테스트의 빈 members 참조는 기존 scorer도 정의되지 않은 분모0이므로 지원을 발명하지 않고 reject 조건을 명시했다. 합성 blocker의 임의1/7분모는 기존 exact scale 관문을 벗어나므로 실제 지원4분모로 검사했다. 실제 음악/weights를 바꾼 수정이 아니다.

실제 자료의 사후 audit도 완료했다. **760고유 입력/코드/산출물 SHA 불변**,72개 동일 범위·61선택 값 불변·주석/unknown mask·모든 지표의 정확 재채점,2개 새 추론 전체 receipt의 fresh replay 일치를 확인했다. 두 real graph에서 gold와 무관하게 정한64개씩 총128개 interval/signature의 indexed 특징과 conditional pattern을 원 구현과 대조해 모두 일치했다. 두 사례의 **전체 MusicXML 복사본·전체 observation IR gzip·원 source IDs·전후 평가·선택·계산 receipt**를 diagnostics에 저장했다. 새 정확도 sample이나 training label로 승격하지 않았다.

사후 코드/문서 QA:9Python AST·13파일 strict UTF-8/깨진 replacement character0·trailing whitespace0·로컬 문서 링크302개/누락0·tracked diffcheck 통과다. 기존5개의 LF→CRLF 경고와 사용자 수정은 유지했다. Audit 물리 SHA는 `2d565c3b873b6a29adcefd85443f5e0b8adc5f6a7d5f551fa8a2b22d33341ffb`다.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_batched_frontier_trial --source output/harmony-bounded-recovery-2026-10-04-r1 --output output/harmony-batched-frontier-2026-10-04-r2
.\.venv\Scripts\python.exe -B scripts/audit_harmony_batched_frontier.py --source output/harmony-batched-frontier-2026-10-04-r1 --output output/harmony-batched-frontier-2026-10-04-r1/diagnostics-r2 --replay
```

출력 폴더는 덮어쓰지 않는다. 예측72개를 물리 봉인한 **뒤** 원 주석 포함 baseline report를 연다. 성능 숫자를 보고 weight/epoch/작품 범위를 조정하지 않았다. 아직 human feedback 또는 상업 학습 허가를 추가하지 않았다.

정본:

- [factored 비교 report](../../../output/harmony-batched-frontier-2026-10-04-r1/report.json), SHA `d1f6b57e7297954c83e932b02e4418f1231874b67a4338c2404985f9c927f0f0`
- [실제 XML·전체 IR·원 ID·전후 평가 사례와 fresh audit](../../../output/harmony-batched-frontier-2026-10-04-r1/diagnostics-r1/audit.json)
- Engine SHA `00242ecb958e21768fea5d8b200b68e691bdbfccf0b3e2ddef057a66729279f2`
- Runner SHA `8363b0ab62bf71c6880f1b83aba430690bcea2f97e0f1a438ac73c81a5426c8b`
- Auditor SHA `16832e6ed4bb836c9f3776e1d55ba6d99266e28c0c5247278f5d054120efac6f`

## 8. 다음 순서와 범위 제한

1. 큰 장문3개의 global cell/sound 관문을 넘길 **전체 source index·후보 생성 재사용·streaming joint frontier**를 검증한다. 반복/meter/source 문제를 계산 한도로 착각하여 무조건 해제하지 않는다.
2. 이번 두 선택 실패의 비교 비용을 분석해 NCT/지속/교체, applied diminished 해결과5음 과병합의 **일반 증거**를 강화한다. 하나의 경계 벌점만 올려 과분할을 고치려 하면 Sonata 같은 과병합을 악화시킬 수 있다.
3. 새 backend를 이미 선택된 여러 작품에도 적용하는 control 검증, 독립 작품 범위와 공개 모델 공통 평가를 이어간다. 두 복구만으로 이를 완료했다고 하지 않는다.

기존 책 이론/화성 규칙·parser·Core/XML/원주석·NC 연구 권한·production/viewer/서버·Git 및 별개 사용자 수정은 유지했다. 외부 API·새 weight 학습·commit/push는0이다. 작은 악보별 예외를 만들지 않는다.
