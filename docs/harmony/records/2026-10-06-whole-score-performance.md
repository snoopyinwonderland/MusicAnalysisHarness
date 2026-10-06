# 단계100 — 전곡 계산 병목 측정·점수 동등 최적화

2026-10-06. 별도 화성 개발 기록. 단계99 뒤 사용자가 긴 곡의 계산 병목 개선을 승인했다. 기존 음악 점수/후보를 유지한 성능 adapter를 만들고 같은6곡에서 원구현과 한 번 비교했다.

## 결론

**60초 내 완료가3/6→4/6곡으로 늘었다.** 603셀 `Pledging My Love`가 최적화 구현에서38.66초에 끝났고 같은 실행의 원구현은60초 초과였다. 공통 완료3곡의 원셀 선택 경로·비용·특징·보류/출처·실제run·전체 후보catalog는 원구현 및 단계99 봉인과 모두같다. 각 최적화 승자는 원래 직접 점수로 재검산했다.

화음 판단의 정확도를 바꾼 개선이 아니다. 1006/1623셀의 긴2곡은 여전히60초 초과다. 전체6곡 분모의 근음+3화음 종류 일치율27.44% 대 봉인 기준선68.51%로 편곡 연결 관문FAIL이다. 작은 개발6곡이며 독립Test/전체234곡/상업적 생성 readiness를 승인하지 않는다. 화면/Claude/generation-ready 연결은 보류한다.

다음 큰 과제는 남은 긴 곡의 실행 비용이다. 이번 측정으로 확인한 초기화/반복 계산은 줄였지만 나머지2곡의 최종 병목을 측정한 것은 아니므로 특정 함수가 원인이라고 확정하지 않는다. 다음에는 후보 생성·검색·직접 검산·아카이브의 단계 시간을 구별하는 것이 필요하다. 계수/beam/timeout을 바꿔 통과시키거나 음악 규칙을 추가하는 루프로 돌아가지 않는다. 이번 실행은 종료했고 같은자료 재시도나234곡 확대는 하지 않았다.

## 구현 파일과 원칙

- [점수 동등 성능 모듈](../../../src/musicanote_harness/harmony_whole_score_fast.py)
- [제한 prefix 프로파일 실행기](../../../scripts/profile_harmony_whole_score_units.py)
- [원구현 대 최적화 비교 실행기](../../../scripts/run_harmony_whole_score_performance.py)
- [봉인 전 신규8검사](../../../tests/test_harmony_whole_score_fast.py)
- [실행 뒤 양수 역할2검사](../../../tests/test_harmony_whole_score_fast_positive_roles.py)
- [사전 계약](../WHOLE_SCORE_PERFORMANCE_PLAN.md)

버전 `local-beat-whole-score-supported-domain-0.2.1-performance`다. 단계99의26계수·기준박 점수·지원domain·원시간/음가/철자/source refs·beam8/2M/60초를 유지한다. 원 모듈의 globals나 bytecode를 수정하지 않고 별도 adapter와 private dependency binding을 사용한다. 기존 단계96–99·원 XML/IR/주석·모델은 보존한다.

### 실제 측정

파싱 뒤 같은603셀 곡의 **전체 IR 범위**를 두고 첫32셀에서 의도적으로 중단한 cProfile이다. 부분 승자를 제출하지 않았다. 17.214151초 중 검색 초기화8.795845초,32셀 consume5.517641초였다. Fraction 비교404만 회가 발생했다. pair cost2.638852초,run cost2.594997초, candidate propose3회약1.16초다. 함수 누적 시간은 서로 중첩돼 합산할 수 없다. profiler overhead가 있고 파싱/전체선택/최종 직접검산·저장 시간은 포함하지 않으므로 전곡 속도나 정확도 숫자로 읽지 않는다.

### 줄인 계산

1. 각 셀에서 전체음표를 훑는 대신 원 start/end를 sweep하여 half-open 활성 음 집합을 구한다. 원 event 순서는 유지한다. 셀·onset·release를 삭제/반올림하지 않는다.
2. span별 known/unknown와 전체노출 합을 재사용한다. 비구성음 적분은 전체노출−실제 구성음 노출의 정확한 Fraction 합으로 계산한다. 첫 root 양수셀은 동일 단조prefix에서 이진 탐색한다.
3. 기준박 변환에서 이미 덮어쓰는 옛 특징까지 다시 계산하지 않는다. 살아남는 조건부 passing/neighbor geometry·근음 지연/문맥 할인·늦은 구성음은 **동일 원 정의**로 계산한다. unknown은null이고 원박자/성부/준비·해결 관문은 유지한다.
4. 지원되는 적용/기능적6/4 전환이 아니면 원pair4항은모두0이므로 바로0비용이다. 지원 전환은 원pair 함수가 실제 사용하는 마지막 수직surface만 공급한다. 마지막 원음표 집합·베이스·명시성부 해결과 설명이 같아야 한다. 미래에 들리는 음을 앞구간의 실제 sounding으로 바꾸지 않는다.
5. 기존 WindowWorkspace의 원provider/window·원catalog validation을 사용하되 duplicate window를 재사용한다. defensive copy와 lease 시작/끝 source hash를 유지한다. 후보/미지원 확장형을 삭제하지 않는다.

검색pair cache는 원evidence의 cache와 분리했다. 원 직접 검산이 최적화pair 결과를 되읽는 자기검사가 되지 않도록 했다. 완료 승자는 단계99 **원 `UnitScorer`** 전체 비용과 정확히 같아야 제출한다. 이 검산과 archive 저장도60초에 포함된다.

## 통제 비교

사전 고정된 같은6곡을 원99 control과 새 adapter에서 각1회 실행했다. 전곡60초·동시4·재시도0이다. 박 템플릿 기준선은 단계99 봉인 결과를 정확도용으로 재사용했다. **이번에 기준선 시간을 새로 측정했다고 주장하지 않는다.** 두 새 예측과 기준선 해시를 먼저 봉인하고 같은6곡 gold를 읽었다. 실행/비교/채점/감사137.963008초, exit0이다.

| 곡 | 원셀 | 원99 control | 최적화 adapter | 원 결과 동등성 |
|---|---:|---:|---:|---|
| Reach For The Stars! | 88 | 3.75초 완료 | 2.70초 완료 | 경로/비용/전체catalog 같음 |
| It_S A Small World | 188 | 12.96초 완료 | 8.90초 완료 | 경로/비용/전체catalog 같음 |
| Family Of The Poor | 294 | 29.09초 완료 | 18.30초 완료 | 경로/비용/전체catalog 같음 |
| Pledging My Love | 603 | 60초 초과 | 38.66초 완료 | 원 전체승자 부재; 직접 원점수 검산PASS |
| Walking On Sunshine | 1006 | 60초 초과 | 60초 초과 | 부분 결과 제출 없음 |
| Experience | 1623 | 60초 초과 | 60초 초과 | 부분 결과 제출 없음 |

공통3곡은 이번control·이전99봉인과 `selected_path`, `page_inventory`, `score_cost`, `feature_values`, `feature_availability`, `actual_harmonic_runs`, `states_discarded`, `operations`, `spans` 및 전체catalog 내용 hash가 모두같다. 따라서 공통3곡의triad71.54%·전체pcs67.61%·베이스64.57%·제출경계F1 45.88%도같다. 완료3곡의 이번실행 시간은 모두줄었지만 동시작업 순서/CPU 경쟁이 있으므로 보편적인 속도배수로 일반화하지 않는다.

새로 완료한 Pledging은 실제화음162run·관찰베이스/무음 변화 포함285제출span이다. root68.91%·triad63.82%이며 봉인 기준선은root68.25%·triad64.68%다. 원control의 전체 승자가 없으므로 동일 최종승자를 선택했다고 비교 증명할 수는 없다. 원 직접 비용 검산을 통과한 근사beam 승자이며 전역최적을 주장하지 않는다.

### 전체6곡: 미완료 포함

| 지표 | 최적화 | 원99 control | 봉인 박 템플릿 기준선 |
|---|---:|---:|---:|
| 완료 | 4/6 | 3/6 | 6/6 |
| 근음 일치 | 28.32% | 18.93% | 71.00% |
| 근음+3화음 종류 | 27.44% | 18.74% | 68.51% |
| 전체 구성음 일치 | 24.63% | 17.71% | 57.90% |
| 베이스 일치 | 25.52% | 16.91% | 71.43% |
| coverage | 39.66% | 26.03% | 99.89% |
| 제출span 경계 F1 | 33.68% | 26.24% | 59.75% |

gold1848quarter의 전체분모를 유지했다. 전체triad차이 대기준선−41.0668%p, 곡별 paired bootstrap95% CI[−61.2610,+1.4664]%p이며 연결 관문FAIL이다. 미완료를 포함한 제출 성능이지 미완료곡의 국소 화음 정확도를0%로 측정한 것이 아니다.

최적화 완료4곡만 같은 기준선과 비교하면 gold736quarter에서 root71.12% 대70.79%, triad68.90% 대68.48%, 전체pcs61.86% 대58.15%, 베이스64.09% 대68.07%, 경계F1 44.44% 대54.44%다. 이는 다른 완료subset이며 공통3곡71.54%와 섞어 향상률을 만들지 않는다. 작은 개발자료에서 기준선보다 우월하다는 증거는 아니다. 제출span 경계에는 베이스 변화도 포함되며 순수화음 경계와 구별한다.

## 검사·저장·감사·보존

신규8+이전37=**45검사PASS**, failure0/error0이다. 모든합성span/candidate의 Fraction 비용, 변박/복합박, 미확인철자, 조건부음/준비 지연, 실제양수pair와원설명, 매셀frontier/버린상태/연산 수, 전체원catalog/Core/path동등성, 부분제출금지를 검사했다. 본실행에서 완료4곡 전부 원직접검산PASS다. 본실행 뒤 봉인 코드/계획/검사 수정0이다.

실행 뒤 별도 파일에 **실제로 양수가 되는 passing 할인과 준비된 늦은3음**의2검사를 추가했다. 일반 회귀에서 해당branch가0인 경우만 비교하는 위험을 보완했다. passing은 약박8분 경과음, 늦은3음은 준비된F4→E4와runstart1/first3의원할인1/8을 확인했다. 원구현/최적화 비용이 같았고 **최종47검사PASS**다. 봉인된8검사/원추론코드/예측/감사는 수정하거나 재실행하지 않았다. 새로 음악 정확도를 측정한 것이 아니다.

사후 **493해시감사PASS**, 불일치0·전체경로/전체catalog 대조PASS다. 원99의 원코드·모델·입력·기준선/완료경로·catalog, 새코드/계획/검사·profiler자료·두새제출을 보존했다. 완료4곡은 전체IR·원셀/철자/sourceID·미지원 확장형 포함전체catalog를 저장했다. window 재계산/재사용은Reach28/28, Small49/49, Family45/45, Pledging65/65다. timeout2곡은 부분승자를 제출하지 않고 전체catalog 저장을 보장했다고 주장하지 않는다.

본실행 전 파일 탐색에서 존재하지 않는 인덱스 파일명과 Windows `rg` pathname glob이실패했다. 올바른 디렉터리+`-g` 검색으로 교정했다. 작성 중 불필요표현/문자도 첫import 전에 정리했다. 첫import와 신규8검사는PASS였고 사후 음악 결과에 맞춰 코드를 수정하지 않았다.

- profile SHA: `06b774d067a17638890346542b4f948fdb9beb3f9149f7d7cd07c6d9ad42ade8`
- score SHA: `710f038c002d0ccbb2e3566228fc8bfd2d04331acd05c72e37aec4a7d06c65a1`
- equivalence SHA: `a4fb2b63a49b99e090497ddb83db0f44a91b28c5342464bb4066b02729ab91a1`
- audit SHA: `cc370de7755b29691d6409f2e7f9adfcc639be7dfbe0d259c58792ce7030259b`

실험 위치: `output/harmony-whole-score-performance-2026-10-06-r1/profile/`, `comparison/`. 기존dirty5·원XML/IR/주석·96–99봉인/모델·MusicSearch/Composition/화면/서버/Git은보존했다. fit/계수/beam/timeout변경·API·commit/push·Claude 연결0이며 DCML 유래계수의 로컬 비상업 연구 제한도 유지한다.

## 재현 가능한 검사

```powershell
$env:PYTHONPATH = 'K:\Music Analysis\src;K:\Music Analysis\tests'
& 'K:\Music Analysis\.venv\Scripts\python.exe' -B -m unittest test_harmony_whole_score_fast_positive_roles test_harmony_whole_score_fast test_harmony_whole_score_units test_harmony_whole_score test_harmony_whole_score_diagnosis test_harmony_test_a
```

실행기들은 기존output 덮어쓰기를 금지한다. 위자료는 완료된 한 번의 비교이며 동일자료를 자동 재실행하는 지시가 아니다. [전체 채점](../../../output/harmony-whole-score-performance-2026-10-06-r1/comparison/score.json), [경로/catalog 동등성](../../../output/harmony-whole-score-performance-2026-10-06-r1/comparison/equivalence.json), [봉인 감사](../../../output/harmony-whole-score-performance-2026-10-06-r1/comparison/audit.json).
