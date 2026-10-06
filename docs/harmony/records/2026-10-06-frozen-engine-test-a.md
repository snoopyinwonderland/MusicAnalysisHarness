# 고정 연구 엔진 v1과 234곡 전곡 시험 A

## 목적과 선정

사용자의 "빠른 마무리와 연결 판단" 제안을 실행한다. 최근 계수/특징 실험을 중단하고 기존26 모델을 고정했다. 기존 Dev는 완료율을 포함하면 기준26이 후속35보다 나았으며, 공통 완료 subset의70.8581%를 전체 성능으로 해석하지 않는다. [사전 계획](../FROZEN_ENGINE_TEST_A_PLAN.md).

연구 엔진 v1은 `harmony_full_score.Scorer`에 기존26계수를 그대로 전달한다. 화면용 템플릿 엔진이나 Claude 추론기를 이 모델의 실험 결과로 바꿔 부르지 않는다. 원 MusicXML 전체 → 기존 Canonical IR → 전체 scope 원관문 → 기존 후보 공급/공동선택의 최소 연결만 구현했다. 계수·화음/NCT 특징·자원 한도는 바꾸지 않았다. 국소 승자 연결, 앞부분만 제출, 정답으로 범위 자르기, 실패곡 재시도는 없다.

원 모델: `output/harmony-adversarial-score-2026-10-05-r1/model.json.gz`, SHA256 `2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf`. 기존 비상업적 로컬 연구 제한을 유지하며 운영/상업 허가를 새로 부여하지 않는다.

## 채점 보완과 검사

Claude 프로젝트 파일은 변경하지 않았다. 이 저장소의 `src/musicanote_harness/harmony_test_a.py`에서 구간 정렬·중첩·양의 길이·pc와 자체 악보 범위를 검사하고, 경계는 ±1/2quarter 일대일 최대 매칭한다. 누락곡의 정답 시간과 경계 FN을 모두 유지하고 bass null을 근음으로 대입하지 않는다. triad의 no-third→sus 분류는 원 채점기와 호환되도록 유지하며 이 지표의 한계를 명시한다.

중첩 예측200% 문제/경계2→1 중복 만점/null bass/누락곡 경계/유리수/범위/동일 제출/합치기 등을 대상으로 신규11검사 PASS다. 최초 실행은 PYTHONPATH 누락으로 import 실패했고 환경을 해당 호출에 한정해 지정한 뒤 통과했다. 이 검사 수는 음악 정확도나11곡 검증을 뜻하지 않는다. 채점 입력234곡 모두 구간 유효성 검사를 통과했다.

## 예비 확인과 본실행

예비 파싱: `5 Centimeters Per Second End Theme` Piano Solo의 자체 길이는159quarter. 기준선은 전체 입력을 완료했고 연구 엔진은279 시간 셀/471 sounding events가 기존64셀/256음 한도를 넘어 보류했다. 예비 확인에는 gold 일치율을 계산하지 않았고 계수를 변경하지 않았다.

실행 코드: `scripts/run_harmony_test_a.py`. 234곡×2조건, 곡당60초/동시4프로세스/재시도0. 원악보 harmony 요소는 메모리 파싱에서 제거하고 모든 성부를 사용한다. 양쪽에 동일한 원 sounding clock 관문을 적용한다. 기보 시간/Fraction/붙임줄/반복 미전개를 사용한다. gold 길이·리드시트·정답 화음은 worker에 전달하지 않는다.

기준선은 분모 박 창에서 시간 가중 구성음 지지와 관찰 완전성을 고정108개(12근음×9종 3·7화음) 템플릿에 맞춘다. 복잡도와 최저음=근음의 작은 고정 tie-break 항이 있다. 학습이나 gold 조정은 없다. 구성음 집합은 화음 template이며 비화성음을 포함한 관찰 집합을 답으로 내보내지 않는다. 최저음이 구성음이 아니면 bass=null이다. 이는 구조적 베이스/전위가 검증됐다는 의미가 아니다.

입력은 반주 라이브러리 holdout234곡이다. 기존 화성 문서의 정규화 제목을 대조하되 과거 이력이 불완전하므로 완전 독립 Test라고 인증하지 않는다. 기존 노출의 가능성이 있는 subset과 기록상 발견되지 않은 subset을 분리한다. 입력/코드/모델과 두 조건의 예측을 고정한 뒤 채점한다.

추가 출처 점검: 고정26 모델의 기존 Train report에서 XML/musicxml/mxl 원본 해시27개를 추출하여 시험234개 원본과 대조했으며 exact hash overlap은0이다. 모델 report의 SHA는 `9146c3783006ae433041e3bc05d1db2266e6f9cb03d6b8771e6d046705b96034`다. 같은 작품의 다른 판본/피드백 노출까지 부정하는 증명은 아니다. 제목 문자열 검사에서 잡힌 `Ordinary`는 `ordinary joint winner`/`ordinary analysis claims`라는 기술 문구의 겹침으로, 실제 곡 노출의 증거가 아니다. 자동 제목 제외 subset은 보수적 참고표일 뿐 독립성 인증이 아니다. 공식 지표는 사전 계획대로 전체234곡을 유지한다.

원 실행 자료: `output/harmony-frozen-test-a-2026-10-06-r1/`.

## 완료 결과 — 전곡 연결 보류

234곡×2조건=468작업을 실행/채점/감사까지 **1,135.882235초(약18분56초)**에 완료했다. `progress.json`은 complete=true, phase=scored_and_audited다. 예측을 먼저 고정한 다음 채점했으며 추가 fit/계수 변경/재시도는 없다.

| 항목 | 고정 연구 엔진 v1 | 분모 박 템플릿 기준선 |
|---|---:|---:|
| 전곡 해답을 산출한 곡 | 0 / 234 | 231 / 234 (98.72%) |
| 전곡 자원 관문 보류 | 231 | 0 |
| 원음표/sounding 시간축 보류 | 3 | 3 |
| 60초 시간 초과 / 실행 오류 | 0 / 0 | 0 / 0 |
| 근음 시간 일치율 | 0%* | 64.6969% |
| 근음+3화음 종류 시간 일치율 | 0%* | 56.5929% |
| 전체 구성음 집합 시간 일치율 | 0%* | 42.9235% |
| bass 시간 일치율 | 0%* | 67.1501% |
| 화음 시간 coverage | 0% | 98.2776% |
| 경계 Precision / Recall / F1 | 0 / 0 / 0 | 34.0582 / 96.0123 / 50.2805% |
| 곡당 중앙 / p95 실행 시간 | 4.2632 / 27.9917초 | 5.2164 / 29.0987초 |

*전체234곡의 gold74,432.5quarter를 분모에 유지하고 보류를 결과 없음으로 채점한 **전곡 제출 점수**다. 연구 엔진이 실제 화음을 선택한 뒤 모두 틀렸다는 뜻이 아니며, 국소 화음 인식 정확도가0%임을 측정한 것이 아니다. 연구 엔진의 시간도 대부분 파싱+관문 검사 시간이지 전곡 탐색 완료 시간이 아니다. 기준선의 bass는 관찰 최저음 후보이며 구조적 베이스/전위 정확도가 아니다. triad는 근음과 종류가 함께 맞아야 하며 7음·전위·국소 조성까지 맞았다는 지표가 아니다.

사전 기준은 triad +5%p·paired bootstrap95% CI 하한>0·root/완주율 비퇴행이다. 실제 차이는 **−56.5929%p**, CI **[−58.4111, −54.6089]%p**(2,000회/seed20261006), 관문 FAIL, 결정은 **do_not_connect**다. 이 CI도 보류를 포함한 제출 성능 차이이며 두 분석기의 국소 화음 품질 비교로 해석하지 않는다.

## 실패 원인과 해석

1. **전곡 크기 계약이 준비되지 않았다.** 시간축 관문을 통과한231곡의 시간 셀은88~1,623개, sounding events는225~3,282개다. 모든231곡이 기존64셀 상한을 넘는다. 기존 연구 엔진의 제한된 scope 계약을 전곡에 그대로 적용해 실제 선택 전에 보류했으며, 기준선보다 인식이 나쁘다는 음악적 원인 분석은 이 시험으로 할 수 없다. 한도를 몰래 풀거나 다른 엔진/국소 경로를 연결해 같은 v1 결과로 내지 않았다.
2. **3곡의 입력 표현에 sounding 불연속이 있다.** Beggin_, Oukashou, The Marsh House는 `noncontiguous_source_clock`으로 양쪽 모두 보류했다. 예를 들어 Beggin_의 한 sound는 `[75/4,19)`와 `[20,21)`의 원음표를 `[75/4,21)`로 합쳐 중간 쉼을 지속음처럼 표현하고 있었다. 이는 XML 자체 오류 확정이 아니라 기존 파서/IR의 붙임줄 연결을 포함한 시간축 정합성 문제다. 이 고정 시험에서 원악보/IR을 수리하거나 해당 곡만 예외 처리하지 않았다.
3. **기준선도 완성 분석기가 아니다.** 근음64.70%/triad56.59%이고, 박 창에서 자주 화음을 바꾸어 경계 recall은 높지만 precision은34.06%다. 국소 조성·적용화음의 기능·NCT·종지·편곡 안전성을 검증한 결과가 아니다. 점수가 연구 엔진보다 높다고 Claude 편곡 입력으로 자동 승격하지 않는다.

전체234곡에서 파싱한 score_duration 문자열은 gold의 total_quarters와 일치했고, 원입력의 제거된 harmony 기호 수는0이었다. 길이 일치가 모든 내부 화음 위치/편곡자 해석의 정답성을 보증하는 것은 아니다. 정답은 제공된 리드시트 화음 기호이며, Piano Solo의 모든 경과/장식 화성에 대한 완전한 정답이나 고전 Roman 분석 정답이 아니다. 곡 전체의 서술적 조성/화음 역할을 이번 지표로 측정했다고 말하지 않는다.

## 최종 검사와 원 채점 도구의 실패

- 신규 채점 검사11개를 최종 재실행하여 전부 PASS했다. 전체 과거 검사 수천 개나 음악 정확도 검증으로 확대하지 않는다.
- 전곡 시험 후 별도1마디 C4–E4–G4 fixture에서 실제 `harmony_full_score.Scorer`/고정26계수 연결을 실행했다. `[0,4)`, root_pc=0, pcs=[0,4,7], bass_pc=0으로 완료했다. 원 선택기의 status명 `selected_untrained_hypothesis`는 그대로 보존했다. 이 software smoke는 234곡의 성공 수에 더하지 않으며 확신도 보정/음악적 일반화 증명도 아니다.
- Claude 원 CLI `python -m musicomp.tools.harmony_benchmark score <제출>`를 두 조건 모두 실행했으나 `report()`의 `per_song` 집계에서 **KeyError: 'root'**로 exit1이었다. 예측이 없는 곡의 row는 gold만 가지는데 report가 root를 필수로 읽는다. 따라서 원 CLI의 최종 참고 수치는 산출하지 못했다. 원 채점기를 수정하거나 보류곡을 누락시켜 오류를 우회하지 않았다. 연결 판단은 누락곡/unknown을 보존하는 로컬 보완 채점기 결과로 했다.
- 모델/원입력/실행 코드/두 제출 **702개 해시**의 단일 사후 감사 PASS, 불일치0. 원출처와234개의 전체 Canonical IR은 engine job별 gzip JSON에 보존한다. 이번 코드/시험은 기존 화면·서버·Claude 프로젝트/Git를 바꾸지 않는다.

## 결정과 보존할 자산

세 단계의 판단을 마쳤다. **현재 연구 엔진 v1은 Claude 편곡에 연결하지 않는다.** generation-ready v0.2를 만들거나 외부 어댑터/운영 배포를 시작하지 않는다. 계수·특징 조정으로 이번 결론을 미루지 않으며 과거 문서의 ‘다음 실험’을 자동으로 재개하지 않는다.

원악보 IR·출처 추적·R01–R12 규칙 계약·교재 정리·국소 검증/실패 사례·고정 모델을 재사용 가능한 연구 자산으로 남긴다. 이는 화성 이론 작업이 무가치하다는 결론이 아니다. **전곡 실행 경로 없이 국소 계수 실험으로 편곡 연결 여부를 판단해 온 순서가 적절하지 않았음**을 이번 시험이 확인했다. 별도 재개를 결정한다면 우선 과제는 전곡 처리/검증 가능한 실행 경로이며, 추가 교재 항목이나 작은 계수 실험이 아니다. melody-only 시험 B, 기존 화면 엔진의 전곡 품질, 공개 모델 비교는 실행하지 않았고 이번 결과로 대체하지 않는다.

## 파일과 재현

- 사전 계약: [FROZEN_ENGINE_TEST_A_PLAN.md](../FROZEN_ENGINE_TEST_A_PLAN.md).
- 실행 코드: [run_harmony_test_a.py](../../../scripts/run_harmony_test_a.py), [harmony_test_a.py](../../../src/musicanote_harness/harmony_test_a.py), [채점 검사](../../../tests/test_harmony_test_a.py).
- [전체 결과](../../../output/harmony-frozen-test-a-2026-10-06-r1/corrected-score.json), [곡별 상태](../../../output/harmony-frozen-test-a-2026-10-06-r1/statuses.json), [고정 입력/코드](../../../output/harmony-frozen-test-a-2026-10-06-r1/freeze.json), [예측 선봉인](../../../output/harmony-frozen-test-a-2026-10-06-r1/prediction-freeze.json), [감사](../../../output/harmony-frozen-test-a-2026-10-06-r1/audit.json).
- [기준선 제출](../../../output/harmony-frozen-test-a-2026-10-06-r1/baseline-submission.json), [연구 엔진 제출](../../../output/harmony-frozen-test-a-2026-10-06-r1/engine-submission.json). 후자는 songs={}를 그대로 보존한다.
- 결과 SHA256: `473a9b6c207d528b97dedd1e25bab54ad9bb6ad54bdbd30c14744d090131bfd6`.
- 감사 SHA256: `4bc376a4a34793be4f7638f3e699cf729311b7fdd6673613a2444a377a7b7cea`.
- 모델/코드 고정 SHA256: `e30a65063c98099ae27645b22d23fd2475eec39df37448fd574ed0c5fc6018ac`.

실행한 PowerShell 명령은 아래와 같다. 동일 출력 폴더가 존재하면 runner는 덮어쓰기를 거부한다. 향후 재현 실행은 별도 새 출력 경로를 명시해야 하며 이번에 추가 재실행하지 않았다.

```powershell
$env:PYTHONPATH = 'K:\Music Analysis\src'
& 'K:\Music Analysis\.venv\Scripts\python.exe' -B scripts/run_harmony_test_a.py --output 'K:\Music Analysis\output\harmony-frozen-test-a-2026-10-06-r1' --timeout 60 --workers 4
& 'K:\Music Analysis\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p test_harmony_test_a.py -v
```
