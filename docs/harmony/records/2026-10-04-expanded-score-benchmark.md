# J3b — 추가 악보의 실제 화음 선택·평가와 큰 실패 원인

기록 ID: **HARM-DEV-20261004-56** · 2026-10-04.

상태: **확대 개발 평가의 실제 추론·주석 대조·사후 재채점 완료**. J3a 준비 목록을 계산했다. 독립 blind test·전곡 분석·full Roman 정확도·공개 모델 비교·운영 승격 완료는 아니다. 새 가중치를 학습하거나 새 음악 규칙을 특정 작품에 맞추지 않았다.

## 1. 실행 계약과 자료 범위

[J3a 준비](2026-10-04-common-benchmark-preparation.md) 정본 r2의 10명명 기반 작품군/16악보를 입력으로 고정했다. 원 manifest의 holdout인 **K282-1은 실행에서 제외**했다. 과거 전체 노출 이력이 미확인인 나머지는 내부 **확대 개발 자료**로 사용했으며 독립 test나 학습 승인으로 바꾸지 않았다.

15악보/9작품군의 Core와 원음표·쉼표를 검사했다. **14악보/8작품군이 source 관문을 통과**했다. K283-1은 중복 measure ID와 local onset 불일치 때문에 원본을 수정하지 않고 전체 6문맥을 보류했다. 준비 메타데이터 완전성과 실제 시간/ID binding의 검증은 다르다.

| Collection | 실행한 악보 | 동결 문맥 |
|---|---|---:|
| Beethoven quartets | n06op18-6_02, n08op59-2_02 | 12 |
| Beethoven sonatas | 07-2, 09-2 | 12 |
| Chopin mazurkas | BI145-1op50-1, BI145-2op50-2 | 10 |
| Corelli | op01n04a–d, op01n05a–d | 32 |
| Mozart sonatas | K283-1, source 관문에서 보류 | 6 |
| 합계 | 15시도 /14 source-ready | 72 /66 source-ready |

총보 교향곡은 이번 집합에 없었다. 현악4중주를 포함했지만 관현악 written/concert 및 이조 악기의 검증을 완료한 것은 아니다. 작품군은 명명 관례 기반의 보수적 그룹이며 15독립 작품 또는 전문가 확정 9독립 작품으로 해석하지 않는다.

### 입력·추론·정답의 분리

1. Source/코드 SHA와 고정 J2e 점수·예산을 `run-contract.json`에 먼저 저장했다. 퇴행한 [J2f 학습 weights](2026-10-04-functional-run-learning.md)는 사용하지 않았다.
2. Core의 note/rest/tie/sound/attack/measure/source ID와 정확한 시간을 유지한 관찰 전용 입력을 만들었다. Extension·제목/작곡가/metadata·조표 mode hint는 추론 입력에서 제외했다. 부모 Core 수정·migration·새 정식 IR revision이 아니라 실험용 입력 projection이다.
3. 원 MusicXML의 imported harmony를 제거하는 parser로 fresh note/rest replay와 physical measure binding을 검증했다. Source 악보를 읽는 것과 화성 정답을 해석하는 단계를 구별한다.
4. 모든 명시 part/voice lane의 전체 attack inventory에서 lane별 내부 quantile 1개를 골랐다. 문맥은 연속 3attack onset group과 지속 범위다. 같은 lane의 음이 드물면 매우 길어진다. 결과·라벨·성공 여부로 골라내지 않고 **전체 72문맥을 첫 추론 전에 동결**했다.
5. 후보 생성·기능적 대안 추가·공동 decoding은 관찰 IR와 동결 sample만 받는다. 후보는 전체 part의 구간 음을 사용한다. Seed lane은 문맥 선정/명시 성부 근거용이지 다른 part를 화성 계산에서 제외하는 선택이 아니다.
6. **72예측을 전부 gzip으로 저장하고 `prediction-freeze.json`에 SHA를 봉인한 다음에만** imported annotation/alignment JSONL의 라벨을 열었다. 입력 hash를 위해 먼저 읽은 bytes와 정답을 해석한 단계는 구별한다.
7. 보류/오류를 사후 성공 문맥으로 교체하지 않았다. 보류 예측도 지원 reference의 시간 분모에 남는다. Source binding 미검증은 정답의 검증 불가로 별도 마스킹했다.

학습0, 새 가중치 tuning0, holdout/split/권한 변경0, 외부 API 전송0, 운영 UI/서버/Git 변경0이다. DCML 출처·NC 내부 연구 범위와 상업 운영/배포 미승인을 유지한다.

## 2. 실제 측정값

공통 평가기의 exact rational quarter, `[start,end)`, 철자 보존 계약을 유지했다. 겹치는 문맥 시간의 합은 `3595/6` quarter이며 **고유 전곡 분석 길이가 아니다**. 72문맥 중 전체 root+members reference 지원51, 부분/미지원21이다.

| 지표 | 실제 결과 |
|---|---:|
| 화음 진행 선택 /보류 | 60 /12 |
| 완전 문맥 일치 | 15/51 =29.41% |
| 근음 exact-time 일치 | 32.87% |
| 근음+철자 구성음 exact-time 일치 | **23.99%** |
| 근음+구성음 작품군 macro | 44.77%, 지원8작품군 |
| 지원 reference 시간의 명시 prediction coverage | **41.05%** |
| 근음+구성음 32분 grid 일치 | 685/2855 =23.99% |
| 의미 화음 경계 TP/FP/FN | 48/18/15 |
| 의미 화음 경계 precision /recall /F1 | 72.73% /76.19% /74.42% |

전위·quality·local key·degree·full Roman의 공통 지원 분모는0, 점수는 null이다. Root+members 일치를 그 항목들의 성공으로 올리지 않는다. 경계 F1은 **완전 reference 51문맥 내부의 화음 signature 변화**이며 프레이즈/cadence 정확도가 아니다. 짧은 문맥·한 화음 문맥·부분 reference 제외·겹치는 lane 표본이 있어 전곡 성능으로 확대할 수 없다.

이전 J2e의33악보/322문맥과는 다른 작품·범위·표본이다. 이전 시간31.97%/전체20.31%와 이번23.99%/29.41%를 paired 개선/퇴행으로 부르지 않는다. 이번 결과는 새 개발 표본에서 **낮은 정확도와 낮은 시간 coverage를 드러낸 기준선**이다.

### Collection별 차이

| Collection | 전체 일치/완전 문맥 | 선택/동결 문맥 | Root+members 시간 | Prediction 시간 coverage |
|---|---:|---:|---:|---:|
| Beethoven quartets | 2/5 | 10/12 | 6.84% | 8.90% |
| Beethoven sonatas | 1/7 | 11/12 | 50.18% | 65.09% |
| Chopin mazurkas | 3/7 | 7/10 | 9.02% | 12.52% |
| Corelli | 9/32 | 32/32 | 53.76% | 100% |
| Mozart sonatas | 평가 불가 | 0/6 | null | null |

4중주/쇼팽은 짧은 문맥의 명명 오류뿐 아니라 매우 긴 미선택 문맥의 시간 분모 때문에 수치가 낮다. Corelli coverage100%도 정답100%를 뜻하지 않는다.

## 3. 정답이 후보에 있는가, 있는데 못 고르는가

완전 reference51문맥의 서로 배타적인 분류다.

| 분류 | 문맥 |
|---|---:|
| 확장 후보망에 정답 진행이 있고 실제 선택도 맞음 | 15 |
| 확장 후보망에 있지만 실제 선택이 틀림 | **18** |
| 확장 후보망에 정답 진행이 없음을 확인 | **15** |
| 후보망 계산 보류로 포함 여부 미확인 | 3 |

기능적 대안을 포함한 **확장 후보망 ceiling33/51=64.71%**와 원 search가 보존한 **24개 완전 진행의 hit11/51=21.57%**를 구별한다. 전자는 reference를 사용하는 사후 oracle 표현 가능성이지 선택 성능이 아니다. 원 24개는 추가 functional 후보를 포함하지 않는다.

| 확장 후보망 포함 | 원 보존24 포함 | 실제 정답 선택 | 문맥 |
|---|---|---|---:|
| true | true | true | 7 |
| true | true | false | 4 |
| true | false | true | 8 |
| true | false | false | 14 |
| false | false | false | 15 |
| unknown | false | false | 3 |

확인된 부재15는 local 철자 signature 부족12, 일치하는 연결/partition 없음3이다. 미확인3은 부재가 아니다. 원 24에 없어도 직접 decoder가 확장 후보망에서 맞게 고른8개가 있으므로 보존24만으로 최대 표현 능력을 판단하지 않는다.

**진단 문자열의 한계:** Runner는 확장 oracle에 control `candidate_hit=false`를 전달했다. 그래서 `candidate_ceiling.outcome=retention_or_search_budget_loss`가 포함33개 모두에 표시되지만 실제 보존 탐색 손실33건은 아니다. 원 report/예측/숫자는 보존하고 [정확한 cross table](../../../output/harmony-expanded-benchmark-2026-10-04-r1/diagnostics-r1/coverage-diagnosis-r2.json)로 설명을 정정했다. 후속 runner는 실제 retained hit 또는 별도 `reference_reachable` 이름을 사용해야 한다.

## 4. 영향이 큰 실패부터 처리

### A. Sparse lane의 세 attack이 긴 구간을 만드는 문제

기존 조사용 표본은 같은 lane의 연속 세 attack을 연결한다. 다른 part가 계속 연주해도 그 lane이 길게 쉬면 수십 quarter가 된다. Quartet의 `[59/2,118)`은 attack이 `59/2,116,235/2`이고 길이는88.5quarter다. 한 화음이라고 가정한 것은 아니지만 작은 context용 계산기가 16 notated denominator unit/128 sounds 관문에서 보류한다.

Quartet88.5, Chopin74와71.5quarter의 **3문맥이 지원 reference201quarter**를 차지한다. 장식음 보류2개5.5quarter와 함께 `baseline_not_ready`5개의 적격 시간은206.5quarter다. 별도 edge budget 보류1개4quarter도 있다. 지원 reference 약357.083quarter 중 이6보류의210.5quarter가 coverage를41.05%까지 낮춘다. 계산이 되는60문맥의 모든 적격 시간은 명시 prediction으로 덮였고 unknown-root만이 낮은 coverage의 원인은 아니다.

다음에는 **같은 평가 범위를 유지하며** 긴 관찰 구간을 bounded tile로 계산하고 지속음/원 ID를 carry하는 일반 경로를 먼저 설계한다. 세 attack 규칙의 조사용/시간 coverage용 역할도 구별한다. 긴 표본을 버리거나 성공 표본으로 바꾸어 점수를 올리지 않는다. Cap를 무조건 풀거나 한 화음으로 강제 병합하지 않는다.

### B. 0음가 grace 때문에 전체 문맥 보류

Sonata07-2와 Chopin 각1개, 총3문맥은 seed에 실제 grace가 있고 기존 `nonpositive_duration` 검사에서 전체를 보류했다. 마지막 Chopin 문맥은 긴 gap/repeat barrier도 있어 grace만 지원한다고 해결되지 않는다.

Core의 grace 기보와 일반 sounding time을 분리해 소비해야 한다. 음표 삭제나 임의 performed 음가 부여로 해결하지 않는다. 순서/anchor/source를 보존한 관찰 근거로 연결하고 일반 sounding span은 양의 duration 규칙을 유지한다. Grace가 아닌 실제 0/음수 오류는 별도 보류한다.

### C. Candidate 공급과 선택 점수의 부족

Local 철자 후보 부족12와18선택 오류가 모두 남아 있다. Corelli는 주석 Dminor→Emajor를 후보망에 갖고도 Dminor7→Bdim7→E7을 택했다. Seventh/확장 구성음으로 관측음을 덮는 이익과 NCT/분산형/기능 비용이 충분히 구별되지 않는 가능성을 보여 준다. 이것만으로 비화성음/기능을 확정하지 않는다. 같은 범위에서 triad/seventh, 유지/교체, 표면/기능 root와 실제 해결을 대조하는 일반 점수 개선이 필요하다. 가중치 재학습 전 표현/근거 공급 차이를 확인한다.

### D. Reference projection과 source clock

Pedal 기재75cell은 reference adapter 미지원으로`871/12`quarter를 unavailable로 남겼다. 겹치는 표본의 **주석 변환 미지원 cell 수**이지 AI의 pedal 판정 실패75독립 사례가 아니다. 별도 pedal role와 화음 구성음 계약이 필요하다.

Quartet n08op59-2_02 한 문맥에서 `268`과 `1005000000000000071/3750000000000000` 사이 약`1.8933e-14`quarter overlap을 발견했다. 인접2cell의 imported clock에 decimal residue가 있고 이 overlap 때문에 해당 문맥이 완전 분모에서 제외된다. 시간 점수24%의 큰 하락을 설명할 정도는 아니나 full-context/경계 분류에 중요하다. **사후 반올림으로 이번 점수를 재작성하지 않았다.** 원 TSV measure/beat·XML의 정확한 좌표로 확인한 adapter revision과 별도 paired report가 필요하다.

K283는 source binding 때문에6문맥이 보류된1악보다. 미지원113cell/169.5quarter를 음악적 정답 오류로 세지 않는다. 전체 replay는 음표16,490/쉼표1,776를 일대일 보존했지만 local onset 불일치2개가 있어 source ID 완전성과 시간 정확성도 구별한다.

## 5. 악보 재현 가능한 사후 사례

[사례·사후 재채점 audit](../../../output/harmony-expanded-benchmark-2026-10-04-r1/diagnostics-r1/audit.json)은 category별2개, 총8사례를 **평가 뒤 설명용으로** 골랐다. 새 표본/훈련 자료가 아니다. 원 XML 전체의 byte-identical 사본, 전체 관찰 IR gzip, source SHA/음표 ID, 정확한 범위, 실제 선택·주석·후보 ceiling을 연결한다. 앞뒤 마디가 있어 나중에 viewer에서 확인할 수 있다. 새 화면을 배포한 것은 아니다.

| 종류·악보 | Quarter 범위 | 실제 비교 |
|---|---|---|
| 선택 오류 · Quartet n08op59-2_02 | `[1411/4,1415/4)` | 주석 C#–E#–G#–B /근음 C#, 선택은 D# root 확장 후보 후 C#–E–G#–B로 바뀜 |
| 선택 오류 · Corelli op01n04b | `[20,23)` | 주석 D–F–A→E–G#–B, 선택 Dminor7→Bdim7→E7 |
| 후보 부족 · Quartet n06op18-6_02 | `[111/8,57/4)` | 주석 F–Ab–C–Eb→Eb–G–Bb(기능 root Bb), 선택 Abmajor→Gminor |
| 후보 부족 · Chopin BI145-1op50-1 | `[284,1143/4)` | 주석 G root/E–G–B→D–F#–A–C, 선택 E root/E–G–B→D–F#–A–C–G |
| 일치 · Quartet n08op59-2_02 | `[246,248)` | F–A–C–Eb, 동일 signature raw분할은 같은 화음 유지 |
| 일치 · 같은 Quartet | `[285,863/3)` | G–B–D→C#–E#–G#, 삼연음 좌표 보존 |
| 보류 · Quartet n06op18-6_02 | `[59/2,118)` | sparse lane 긴 범위, context 관문 보류 |
| 보류 · 같은 Quartet | `[167/2,175/2)` | edge budget 보류, ceiling도 unknown |

화음 이름은 원 pitch/구성음 shorthand이며 Roman/전위 검증 완료 주장이 아니다. 기능 root와 surface root가 다른 주석을 곧바로 오류로 단정하지 않는다. 전수72문맥은 원 report와 봉인 prediction에 보존했다.

## 6. 구현·검사·정본

추가 코드: [확대 runner](../../../src/musicanote_harness/harmony_expanded_benchmark.py), [15검사](../../../tests/test_harmony_expanded_benchmark.py), [사후 재채점 auditor](../../../scripts/audit_harmony_expanded_benchmark.py), [coverage 진단](../../../scripts/diagnose_harmony_expanded_coverage.py). 기존 scoring/parser/production 코드는 바꾸지 않았다.

신규15+관련340 = **355 PASS /9.468초**. Holdout/alias/노출·관찰 projection·source/timing/transposition 관문·작은 실제 decoding·디스크 전예측 봉인 후 정답 개방·오류/보류 분모·SHA 변조·덮어쓰기 금지를 검사했다. 최초 synthetic fixture에는 concert pitch/sounding duration이 빠져2검사가 실패했고 fixture를 수정했다. 실제 r1의 음악 규칙을 바꾼 실패/재실행은 아니다.

실제 r1은 **471.319초/exit0**, 실행 exception0이다. Auditor는72sealed prediction·전체 표본 inventory·입력/코드/출력 **602고유 physical SHA**를 확인하고 문맥/집계 점수를 정확히 재현했다. 같은 계약의 재채점이며 독립 음악 전문가의 정답 검수는 아니다. `progress.json`은 정답 개방 직전 incomplete snapshot이다. 완료 여부는 `report.json.complete=true`와 audit로 판단한다.

Coverage script 첫 실행은 covered key를 잘못 읽어 output 없이 실패했다. Key 수정 후 진단r1, seed grace/문맥 관문을 추가한r2를 새 파일에 생성했다. 두 진단/원 report를 보존했고 음악 선택·주석·평가 숫자를 수정하지 않았다.

최종 마무리에서 같은355회귀를 다시 실행해 **9.133초/exit0**로 통과했다.4개 새 Python 파일의 AST, 메인/로그/새 상세 기록의 replacement character0·로컬 링크 누락0, ledger의 이전2record 동일/신규9가족 포함/K282 미포함을 확인했다. 별도 audit r2도602guard와72봉인 예측·exact metric을 재현했다. `git diff --check`는 통과했고 기존 tracked5수정의 범위는 유지했다. 새 별도 문서/코드/output은 이번 작업 파일이며 commit/push하지 않았다.

- [Report](../../../output/harmony-expanded-benchmark-2026-10-04-r1/report.json):2,407,262B, SHA `71926c9155b81fd1d9792ec6cf1b79c31a1b9aa2e45c636e31e227990f3bf182`.
- [Audit·8사례](../../../output/harmony-expanded-benchmark-2026-10-04-r1/diagnostics-r1/audit.json):382,852B, SHA `bb1aee6e57787a0e5cdf3f61bb6512dc68dc536d3fd2d31d5304d106fdd8c703`.
- [Coverage/clock/cross table r2](../../../output/harmony-expanded-benchmark-2026-10-04-r1/diagnostics-r1/coverage-diagnosis-r2.json): SHA `b25cf73c9f938cba5a981b6cc4291e122ff33e103454e1085d65845bfce8d5b2`.
- Runner `harmony-expanded-benchmark-0.1.0` SHA `f8fb79d65d8f83642f4e035af28175ad1ae28cf8fa8999ef81f0bb2cf47f17e3`.
- Auditor code SHA `76d523d89075b2ebc3e6933c4ec2da1207f2618a52763ba74e9281f8dd3e1c1e`; coverage code SHA `8ad83e00f52384a6b374a11b9dd6de1b74632b416b71e8dbca76dbf698f9708a`.
- [노출 ledger v3](../experiments/2026-10-04-benchmark-exposure-ledger-v3.json)은 v2를 보존하고 이번9가족을 추가한다. K283도 Core/주석을 열었으므로 미래 새 blind test에서 가족 전체를 제외한다. Source 보류를 노출 없음으로 바꾸지 않으며 training/rights 승인도 부여하지 않는다.

재현은 새 output directory를 지정한다.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_expanded_benchmark --plan output/harmony-common-benchmark-2026-10-04-r2/independent-evaluation-plan.json --manifest output/harmony-dataset-manifest-2026-09-25.json --exposed output/harmony-candidate-recall-2026-10-04-r1/report.json --output output/harmony-expanded-benchmark-new-run
.\.venv\Scripts\python.exe -B scripts/audit_harmony_expanded_benchmark.py --source output/harmony-expanded-benchmark-new-run --output output/harmony-expanded-benchmark-new-run/diagnostics-r1
.\.venv\Scripts\python.exe -B scripts/diagnose_harmony_expanded_coverage.py --source output/harmony-expanded-benchmark-new-run --output output/harmony-expanded-benchmark-new-run/diagnostics-r1/coverage-diagnosis.json
```

같은 노출된 개발 자료의 재현이며 새 independent test가 아니다. Plan/manifest/exposed SHA pin이 다르면 거부한다.

## 7. 결정과 다음 순서

J3b 첫 확대 계산은 마감한다. 정확도가 충분하다는 결정은 아니다. **같은 고정 문맥의 긴 구간 bounded 계산/연결과 grace 계약 → 후보 공급·triad/seventh/NCT/기능 root 선택의 큰 오류 → 공통 native adapter를 갖춘 공개 모델 비교**를 우선한다. Decimal clock/pedal reference는 별도 검증된 adapter arm으로 비교하고 기존 분모/결과를 보존한다.

Learned weights 재학습이나 작품별 예외부터 붙이지 않는다. K283를 억지로 실행시키거나 교향곡 전 자료 정리를 이번 확대 평가 완료의 전제로 확대하지 않는다. Full Roman/전위/조성 출력·검증된 cadence·전체 악보 UI/피드백·구조 및 작곡편곡 연결은 별도 완료 기준이다. 사용자에게 정답을 더 입력받지 않아도 다음 큰 구현을 진행할 수 있다.
