# 단계81 — 음악 점수·후보를 바꾸지 않는 문맥 계산 효율

## 1. 목적과 범위

단계80의 미채택 모델을 다시 학습하지 않고 계산 효율만 검사한다. 기존26항과 문맥7항, 원118Train scope/23전체 악장 source/15명명 작품군·원60,129edge, 원152제외 범위를 유지한다. Dev/UI/운영 모델이나 음악 규칙을 바꾸지 않는다. 계산 보류가 줄어드는 것은 가중치의 음악적 정확도 향상과 구별한다.

## 2. 변경하지 않는 것과 최적화

- 봉인 `harmony_context_joint_decoder.Scorer`의 세 run 지연 DP, raw-edge 비교 순서·2M 한도·cap6·동점 ID·history Pareto·끝의 두 전이 flush를 **상속 그대로** 사용한다. 후보 삭제/beam/음악별 예외/새 유지 후보0이다.
- 탐색 중에는 점수에 필요한7값/availability만 계산한다. 기존 상세 `Context.conflict`가 만드는 음표별 JSON·음형 설명·수직 cell·선택 anchor의 대안 설명은 **선택 이후 원 구현으로 재생**한다. 원 상세 값과 승자 비용은 그대로 검산한다.
- 실제 source의 onset/release로 exact Fraction cell을 한 번 만들고 최저 실제 sounding IDs를 보관한다. 비교 범위의 음가·unknown·held bass coverage를 signature와 무관한 domain cache로 재사용한다. Cell clipping은 [start,end)이며 쉼/중첩/동음 lowest를 보존한다. 높은 성부나 가상 근음으로 베이스를 대체하지 않는다.
- v0.2의 다음 run signature는 scalar 판단의 veto가 아니라 상세 설명에만 쓰인다. Scalar cache에서는 그 signature만 생략하되 다음 run의 **완성 end**는 유지한다. 원 detailed receipt는 다음 signature를 생략하지 않는다. 이 등가성은 다른 `Context` subclass에 일반화하지 않고 정확한 봉인v0.2 type만 허용한다.
- 경과/보조/이중 보조 형태의 양 anchor, 명시 성부·clock·contiguity·grace·history 관문은 유지한다. 여러 형태의 같은 중간음은 합집합으로 계산한다. Resolution credit은 explained pair와 실제 기존 상세 pair가 겹칠 때만 원 계약대로 반영한다. Explained 음이0인 경우 충돌 credit0은 빈 domain 증명이지 unknown의 대입이 아니다.
- Unavailable local feature는 null이고 점수에서 제외한다. Partial 관측은 별도로 유지한다. 전체 길이/전체 note-time 정규화도 같다. Lowest coverage의 지역 폭 곱/나눗셈은 Fraction으로 상쇄해 동일 전체 quarter폭에 직접 나눈다.

Scalar index는 첫 비용 호출 때 lazy 생성하므로 20초 cooperative wall guard 안에 들어간다. Source-run·상세 profile뿐 아니라 scalar 값 호출 전후에도 clock을 검사한다. Instance hook은 정상/보류/예외에서 모두 복구한다. 부분 승자나 이전 엔진 fallback을 반환하지 않는다. 원20초는 hard kill이 아니며 한 호출은 초과할 수 있다. 생성 setup 시간은 별도로 기록하고 최종 detailed winner replay 시간은 guard 안에 포함한다.

등가성의 범위는 제한적이다. 연속한 지역 runs `A=[a,b), B=[b,c), C=[c,d)`의 v0.2 scalar는 `(a,b,c,d,A.signature,B.signature)`에만 의존한다. 다음 signature는 원 receipt의 anchor 대안/next 표시에는 남지만 수치/availability에는 영향을 주지 않는다. 다음 end `d`는 성부의 실제 해결 anchor가 범위 안에 있는지를 바꾸므로 생략할 수 없다. 끝의 두-run 경우는 `d=c`다. 이 7값의 exact dot product만 원 DP에 공급하고 기존26항을 건드리지 않아, 원 탐색 순서·동점·모든 값이 동일하면 state 및 operation count도 동일하다. 승자 비용만 같다고 모든 음형 설명이 같다고 추정하지 않고 지역 observed/known/null 각각을 원 상세 값과 다시 대조한다.

## 3. 검증 계획과 실행 상태

신규 scalar/guard15합성 검사에 signed계수·모든 작은 경로의7값/unknown·전수 최소/lexical동점·중복edge·4~6run·분할/flush·Fraction/성긴grid·silence/원sound clipping·unknown meter·명시 성부·실제 pair credit·부분관측·barrier·예외복구를 포함한다. 기존823검사 목록도 그대로 실행한다. 합성 검사 수를 곡 수/음악 정확도로 보고하지 않는다.

신규15검사는 통과했다. 첫 초안의 synthetic negative-onset fixture는 기존 source validator가 거부했고, row pitch=None fixture는 원 pair 계산 자체가 지원하지 않아 실패했다. 유효 nonnegative source/clipped query와 실제 missing-row 관찰로 교정했다. Tuple에 pop 사용1회, lightweight evidence를 full source scorer로 구성한2fixture 오류도 actual 전 교정했다. 원 parser/규칙/실험 조건을 완화하지 않았다.

전체 회귀838검사/76모듈 PASS,failure/error0·92.509986초다. Actual 중 별도 읽기 전용 double-neighbor `C-D-B-C`/Fraction 음가의 scalar·상세 값 대조도 PASS이며 코드/검사 파일을 바꾸지 않았고838개에 더해서 보고하지 않는다. 실제118fresh와 사후 원자료/비용 감사는 완료했다. 집계의 tuple/list 표현 차이는 아래 별도v2에서 정정했고 신규3정정 검사도 통과했다. 838개는 전체 repository suite가 아니라 이전 inventory+신규15검사이며, 정정3개를 그 report에 사후 추가하지 않는다.

## 4. 실제 비교의 판정 계약

모델 SHA `f27db2416de803d3245c960e827f3786f8b3947bc1fa538fc15c9d90f17096f4`와 기존26계수를 실행 전에 검증한다. 원자료와 과거3204봉인 inputs/계수/라이선스 계약을 변경하지 않는다. 이번 fit/Dev 탐색0이다.

같은118범위에 새 ordinary를 시도하며 단계80에서 완료한 경로와 이번도 완료한 경로는 **raw IDs·Fraction 비용·상세 receipt·DP operation count·모든 DP diagnostics까지 동일**해야 한다. 다른 결과면 실패로 처리한다. 원28보류는 같은 순서/후보/비용으로 새 계산을 시도하되 이전 보류에서 partial winner를 복구하지 않는다.

모든118분모와 새 계산 보류를 포함한 참조 일치, 같은 모델의 과거 결과 대비 완료/보류, 기존26모델 대비 음악 지표를 따로 보고한다. 원근음+구성음의 시간 일치가 전체 Roman/전위/국소조성/전체NCT·종지/독립Test 정확도를 뜻하지 않는다. 과거 wall 수치는 부하·cache 상황이 다른 **비통제 역사 비교**이므로 엄격한 배속 benchmark라고 보고하지 않는다.

모든 case는 전체XML/parentIR/workingIR·source SHA·원note/sound IDs·전후 full spans·source clock·원graph·기존 및 새 경로·상세 비용을 연결한다. 세부 악보 사례는 복원 가능한 원자료와 함께 보존하고 계산 효율을 개선했다는 이유로 UI에 미채택 가중치를 올리지 않는다.

## 5. 실제 결과와 결정

Actual **665.970685초/exit0·104exact 선택/14wall 보류**다. 같은 모델의 단계80 대비 원90완료는 raw IDs·Fraction 비용·상세 receipt·DP 연산/diagnostics까지 **90개 모두 동일**하다. 원28보류 중14개가 새로 완료됐고 이전 완료의 새 보류0이다. 새 완료14개 중8개가 참조 진행 전체와 일치하고6개는 다르다. 원 scope/후보를 늘려 얻은 결과가 아니며, 새로 계산되는 것과 옳게 판단하는 것을 구별한다.

| 조건/분모 | 완료/전체 | 전체 진행 일치 | 근음+철자 구성음 시간 | 작품군 macro | 경계F1 | 시간 coverage |
|---|---:|---:|---:|---:|---:|---:|
| 기존26 모델 / 원118 | 118/118 | 58/118 | 77.5572% | 77.5655% | 74.2358% | 100% |
| 같은7항 모델의 단계80 / 원118 | 90/118 | 47/118 | 48.1061% | 45.1002% | 50.0000% | 62.5897% |
| 같은7항 모델의 단계81 / 원118 | 104/118 | 55/118 | 58.3848% | 56.6621% | 61.3065% | 75.0042% |
| 기존26 모델 / 이번 완료104 paired | 104/104 | 53/104 | 78.2202% | 76.2965% | 73.3728% | 100% |
| 같은7항 모델 / 이번 완료104 paired | 104/104 | 55/104 | 77.8420% | 76.1242% | 72.6190% | 100% |

같은 모델의 전체118지표가 오른 것은 보류를 줄여 coverage가 증가한 결과다. 기존26 모델과 이번 완료104를 맞춘 비교도 시간/macro/경계는 조금 퇴행한다. 따라서 **7항 계수 미채택을 유지**한다. 효율 backend의 연구용 등가성 확인과 모델의 음악적 승격은 별도다. 원90공통 선택의 음악적 판단을 바꾸거나 단계80의 두 선택 퇴행을 해결한 작업이 아니다.

기존26 모델 대비 원118의 기존 정답7소실은 선택 퇴행2+아직 계산 보류인 기존 정답5이며 새 정답4다. 이번 완료104의 경로 변경은13개다. 같은7항 모델 대비 변경 경로14개는 전부 과거 보류에서 새로 생긴 완료이고 기존 완료90의 변경0이다. 이 변경 수는 아래v2 정정 자료를 기준으로 읽는다.

완료104 탐색에서 scalar197,137회/동일 scalar cache hit1,480,721회를 기록했고 탐색용 detailed profile 생성0이다. 최종 승자 재생에는 원 상세 자료를 그대로 생성한다. 공통90의 fresh 선택 시간 합은 역사224.226794초→이번38.989538초,중앙값.775424초→.225909초다. 전체 과거1,039.879255초→이번665.970685초도 **비통제 역사 비교**이며, cache·부하·원 guard 차이 없이 측정한 확정 배속으로 쓰지 않는다.

남은14wall 보류의 sound/source evidence 계산과 지연 DP는 그대로다. 최대32.095280초는 원 guard가 cooperative인 한 호출 초과 사례이지20초 hard limit을 보장한 것이 아니다. 단순 예산 확대/부분 승자 반환을 하지 않았다. 단계81의 이득으로 남은 음악 점수의 큰 반례를 검토할 여유를 얻었으며, 남은 모든 계산 병목을 해결했다고 선언하지 않는다.

## 6. 원악보와 연결되는 실제 사례

- **새로 계산 완료:** [베토벤 Quartet op18-1 4악장,cont_ccf6196d34ffa1d948e5](../../../output/harmony-context-scalar-efficiency-2026-10-05-r1/cases/cont_ccf6196d34ffa1d948e5.json.gz). 원 quarter `[509/2,1537/6)`에서 C-E♭-G → C-E-G-B♭ → F-A♭-C를 선택하고 참조 전체와 일치했다. 새 fresh1.786002초이며 과거는20.005초에서 승자 없이 보류했다. 이는 새 음악 규칙이 이 진행을 고친 사례가 아니라 **같은 비용의 exact 선택을 완료한 사례**다. 원 전체 [MusicXML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/c421f89dc2ddceec5a94/source.musicxml)의 SHA는 `8ff0da1ba6f57134e14e9152f30753c4f445e0315dfd567af882d5207626dd57`이다. Parent/working IR·원 IDs·sound spans·전후 문맥·source clock와 상세 비용은 packet에 연결한다. Roman/local key/전위/NCT를 새로 확정하지 않는다.
- **유지 완료 예:** [Chopin BI126-1op41-4,cont_10052b9e53534d175091](../../../output/harmony-context-scalar-efficiency-2026-10-05-r1/cases/cont_10052b9e53534d175091.json.gz). 원 quarter `[16,19)`의 A♭-C-E♭ 유지 진행을 선택해 참조와 일치했다. 새 fresh4.463349초,과거20.037초 보류다. 원 전체 [MusicXML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/9db492071fd6640e5a45/source.musicxml) SHA는 `b3c984794d352f71edc974505caba85cbd303d651fc23b8be33eb83fd0d7d31b`이며 동일 source/IR/원note·sound/음가 자료를 보존한다. 음악 이름의 대조를 조건문에 넣지 않는다.
- **아직 해결하지 않은 음악 퇴행:** [K280-1,cont_7ac4f91c9a34b723f8cc](../../../output/harmony-context-scalar-efficiency-2026-10-05-r1/cases/cont_7ac4f91c9a34b723f8cc.json.gz)는 F-A-C → E-G-B♭ → F-A-C 과분할을 그대로 선택한다. [K280-1,cont_9a13eb950949fd01e0e7](../../../output/harmony-context-scalar-efficiency-2026-10-05-r1/cases/cont_9a13eb950949fd01e0e7.json.gz)는 참조 A7 유지 대신 A-C♯-E → E-G-B 축소/교체를 여전히 선택한다. 두 경로·cost·원 상세 receipt는 단계80과 동일하다. [이전 원음표/두 비용 진단](2026-10-05-context-only-calibration.md)을 잃지 않고 다음 점수 균형의 일반 반례로 연결한다. 인간이 승인한 유일 해석이라고 바꾸지 않는다.

## 7. 봉인·감사·정정과 재현

- [Actual report](../../../output/harmony-context-scalar-efficiency-2026-10-05-r1/report.json) SHA `d9a27279ce46407968c354a5e9a36a18bd7e1dfe1eb314a7870f50ef66d38297`. 아래 경로 변경2집계 정정 외 원 결과를 보존한다.
- [Run contract](../../../output/harmony-context-scalar-efficiency-2026-10-05-r1/run-contract.json) SHA `16e2c2058607c81b91e40532c2b58a47096226e43371b3c0af32d24f607ae7c6`.
- [838검사 report](../../../output/harmony-context-scalar-validation-2026-10-05-r1.json) SHA `659e5fb85e66747cdf36fa330ceb9a8d718463067d28d81c9e6344e1449e11a7`.
- [사후 원자료/상세 비용 감사](../../../output/harmony-context-scalar-efficiency-2026-10-05-r1/post-seal-audit.json) PASS/exit0,3,338고유SHA/3,331봉인 inputs·118scope/23source/60,129edge·312독립 상세 경로 비용/275scalar-상세 전이 재생·지표 검산. SHA `a697a3294e9fc17dc46d0ff7e56d57525bf580b232c1d1459a61c4247e1a2541`,audit code `eb6c8543c0d6fb22927e1c347bb0407645237a30730240d33bb59ea6d0b91418`다. 새 탐색/fit/Dev0이다.
- **정본 집계 보완:** [v2 metric correction](../../../output/harmony-context-scalar-efficiency-2026-10-05-r1/post-seal-metric-correction-v2.json) PASS/exit0,3,342SHA/118저장 path 재검산. SHA `c50dc4d5781489e5c531fe349af34742d266e73aba2c4e1a687f201fd4c4e004`이며 `corrected_tables`가 변경 경로 수의 정본이다. 최초 runner가 fresh IDs의 tuple과 저장 baseline의 list를 그대로 비교해 두 `path_changed_with_complete_selection`을104로 과대 집계했다. 정규화 후 같은 모델 대비14,기존26 대비13이다. 두 leaf 외 whole hits/시간/macro/경계/coverage·예측/계수/score/원자료 변경0임을 검사했다. 최초 감사는 같은 pre-JSON 표현으로 그 오류 수치를 재생했으므로 그 감사만으로 이 두 집계가 올바르다고 읽지 않는다. 원report/원auditor/runner/test6파일을 고치지 않고 별도audit script+3검사로 정정했다. 후속 runner는 경로 ID 배열을 정규화한 뒤 비교해야 한다.

Actual 시작 뒤 최초6code/test/script 수정0이며434code/119artifact pins를 검증했다. 이후 v2의 script/test2파일만 별도 추가해 자체 code pins로 봉인했다. 새8Python UTF-8/AST/공백과 개발 문서/링크 QA를 별도로 확인한다. Actual/원 비용 감사/v2 실행 실패·중단0,원 weight/Core/주석/서버/UI/Git 변경0이다. 문서의 잘못된 partial context patch2회는 적용 실패/파일 변경0 뒤 올바른 문장으로 교정했고, 큰 최종 출력 잘림은 저장report의 compact 조회로 보완했다. 합성 fixture 초안 오류와 집계 정정은 성공 기록에서 지우지 않는다.

최종 문서 링크 검사에서 정규식 오류1회가 있었고, split 기반 읽기 전용 검사로 바꾸어12링크의 존재를 확인했다.8Python/3개 개발 문서의 UTF-8·공백 QA와553봉인 pins 및 v2 code pins 검증은 통과했다.

다음은 `K:/Music Analysis`에서 실행하는 새 trial의 재현 명령이다. 기존 output은 덮어쓰지 않는다. v2 정정 계약은 이번r1의 고정 SHA에 대한 것이므로 다른 새 report에 그대로 적용하지 않는다. 다음 runner는 정규화한 집계 계약을 사용해야 한다.

```powershell
$env:PYTHONPATH='src;tests'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_context_scalar.py --prior-validation output/harmony-context-score-validation-2026-10-05-r1.json --output output/<new-validation>.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_context_scalar_trial --output output/<new-trial>
.\.venv\Scripts\python.exe -B scripts/audit_harmony_context_scalar.py --root output/<new-trial>
# 이번 r1의 별도 정정 확인: output이 이미 있으면 재작성하지 않고 읽는다.
Get-Content -LiteralPath output/harmony-context-scalar-efficiency-2026-10-05-r1/post-seal-metric-correction-v2.json -Raw
```

## 8. 다음

Exact 등가성과 큰 효율 비교는 완료했다. 남은14보류의 추가 최적화에만 붙들리지 않고 **genuine7화음 유지와 외부음 설명의 점수 경쟁·fixed-pool 밖 오답**을 Train에서 먼저 보완한다. 새 음악 규칙은 다음 별도 작업이며 이번 계산 최적화로 해결했다고 하지 않는다. 유지/교체의 알려진 부분값과 unavailable,실제 전후 성부 해결/동일 sound의 근거 중복·장식 설명을 함께 비교하고7음 보존 hard gate/작품별 예외를 만들지 않는다.

이후 조건을 고정한 Dev 퇴행 확인/독립 Test가 필요하다.14보류/원152제외·source 미지원은 별도 backlog로 남긴다. Core/원주석/UI/구조/Claude Phrase·Motif/MusicSearch/Composition/서버/별개 dirty/Git 변경0이며 인수인계가 아닌 화성 개발 문서에 기록한다. API/외부 전송/commit/push/merge0이다.
