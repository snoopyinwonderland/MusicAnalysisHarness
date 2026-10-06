# HARM-DEV-20261005-66 — 선택되는 앞뒤 화음에 조건부 NCT 설명 연결

## 1. 결과와 적용 결정

[단계65](2026-10-05-component-support-ablation.md)의 다음 작업을 이어갔다. 순차 음형에 가점을 주기 전에 **실제로 경쟁하는 앞뒤 화음의 구성음 관계**를 확인하는 전이 점수를 공동 선택기에 추가했다. 실제 구성음의 경계 이후 지속까지 요구하는 조건도 별도로 비교했다.

**이번 실험은 정확도 향상을 입증하지 못했다. 운영에 채택하지 않는다.** 앞뒤 구성음 관계만 요구한 조건은 맞던 쇼팽 화음 하나를 과분할했다. 실제 공통 구성음 지속까지 요구한 조건은 그 퇴행을 피했지만 기존 선택·비용·지표와 모두 같다. 후자의 최종 선택 경로에서 사용된 새 NCT credit은 0개다. 따라서 이를 비화성음 분석 완성이나 새로운 음악적 정확도 향상으로 보고하지 않는다.

새 코드는 연구용이다. 기존 MusicSearch 화면 엔진, Phrase/Motif, Core, 원악보·주석, 별개 dirty 파일, Git 상태를 변경하지 않았다. 서버·API·외부 모델 실행·학습·merge·commit·push는 하지 않았다.

## 2. 사용자 질문 — 비화성음을 다 마치고 넘어온 것인가

**아니다.** 교재의 개념 정리, 후보 형태 구현, 선택 점수 연결, 음악적 정확도 검증, 운영 적용을 구별해야 한다.

| 범위 | 현재 있는 것 | 완료하지 않은 것 |
|---|---|---|
| 경과음·보조음 | 명시 성부의 연속 음형, 후보 화음에 조건부인 구성음→비구성음→구성음 설명. 짧은 약박 등 제한 조건에서 점수 연결 | 다성부/반복/강박/장식된 해결을 포괄하는 유형별 정확도 |
| 지연음·선행음 | 실제 sounding event의 경계 통과 또는 같은 음의 재타격 등 조건부 형태 검사 | 선택되는 양쪽 화음·강세·준비·해결을 모두 연결한 일관된 최종 판정 |
| 이중 보조음/Changing Tone | 완전 준비 형태 등 후보·사례 코드 | 새 공동 선택기 전체 점수 연결과 유형별 검증 |
| 전타음·도약 비화성음·페달 등 | 이론/관찰/경쟁 해석 계약 및 일부 후보 근거 | 전체 유형을 고르는 검증된 분류기 |

근거: [규칙 설계 계약](../HARMONY_REASONING_RULES.md), [교재/후보 구현 이력](../../../MUSICANOTE_Canonical_Music_IR/HARMONY_TEXTBOOK_CASE_CURRICULUM.md)의 2026-09-29 잔여음 감사, [조건부 시간·국소 NCT 설명](2026-10-01-temporal-and-local-nct-explanations.md). 기존 지연음·선행음 등의 후보는 `confirmed_nct=false`인 설명이며, 새 점수에 모두 연결된 것이 아니다. 이 자료군에는 아직 독립 NCT 정답과 유형별 precision/recall을 이용한 전체 검증이 없다.

현재 순서는 다음과 같다.

1. 원악보/IR의 시간·ID·붙임줄 관문과 이론 규칙/사례 구축.
2. 화음 구간×화음 종류 후보, 공동 선택기, 첫 평가 및 가중치 학습 비교.
3. **현재:** 앞뒤 화음·경계·NCT·지속/교체·생략을 공동 비교하고 큰 선택 오류를 검증.
4. 필요한 NCT 유형·성부/준비/해결을 확장하고 비중복 작품군/공개 모델 평가와 조성·기능·종지 검증.
5. 검증된 새 엔진을 악보 화면과 사례 피드백, 구조 분석, 작곡/편곡에 순차 연결.

NCT를 모두 먼저 확정한 뒤 화음을 분석하지 않는다. 같은 음도 화음 가정에 따라 구성음이 될 수 있으므로 두 가지를 함께 검증한다. J0~J2 파일럿은 실행했고 J3 확대 개발 평가/준비와 J4 큰 오류 개선을 진행 중이다. J3 frozen test/공개 모델 비교 및 J5의 운영 일반화·생성 연결은 미완료다. 연구 기록 번호나 unit test 수를 전체 진척률로 환산하지 않는다.

## 3. 일반 규칙과 공동 선택 계약

### 3.1 세 비교 조건

| 조건 | 점수 |
|---|---|
| `control` | 단계65의 control, 즉 단계64 근음 회귀 문맥 점수를 유지 |
| `selected_roles` | control + 실제 선택되는 앞뒤 화음 아래 성립하는 경과/보조 형태의 전이 credit |
| `shared_support` | selected_roles 조건 + 두 종류 이상의 실제 구성음이 양쪽 화음에 속하고 경계 이후에도 지속할 때만 credit |

단계65의 미관측 식별음 추가 비용이나 무조건적인 cross-run 순차 credit을 그대로 채택한 것이 아니다. 세 조건·계수 `-1/2`는 실제 대조 전에 고정했다. Dev sweep/새 가중치 학습/작품·마디별 예외는 없다.

### 3.2 한정된 전이 근거

기존 source-clock·성부·철자·박절 검사를 통과한 준비음 p, 가운데 음 r, 도착음 n을 소비한다.

- p는 완료되는 왼쪽 harmonic run 안에서 시작한다. 준비음을 앞의 미확정 화음들에서 빌리지 않는다.
- r은 짧은 약박 순차 경과/보조 형태이며, r의 끝과 n의 시작이 실제 후보 경계와 정확히 맞닿는다.
- p와 n은 왼쪽 화음 구성음, r은 왼쪽 비구성음이다. n은 **선택되는 오른쪽 화음에도** 속해야 한다.
- 가운데 음 동안 실제로 두 종류 이상의 왼쪽 구성음이 지속해야 한다. 분산된 관측을 가짜 지속음으로 만들지 않는다.
- shared_support 조건에서는 그 실제 지속음 중 두 종류 이상이 오른쪽 구성음이면서 실제 release가 경계보다 늦어야 한다.
- 해당 전후 문맥의 원 XML/IR source-clock 관문을 통과해야 한다. 미지원 반복/ending·grace·성부 겹침/단절·철자/박자 문제는 유지한다.

이는 **화성 지속 설명에 부여하는 이번 한정 credit의 조건**이지 모든 비화성음의 보편적인 정의가 아니다. 실제 화음 교체에서는 두 공통음 지속이 없을 수도 있다. 이 조건을 모든 NCT의 hard filter로 확대하지 않는다.

```text
전이 특징 = 조건을 충족한 가운데 음의 길이 / 문맥 전체 원음 노출량
새 비용   = 기존 run/전이 비용 + (-1/2) × 전이 특징
```

원 비구성음 비용을 삭제하거나 NCT를 확정하지 않는다. 철자, 실제 source note/sounding event ID, 선택되는 좌우 signature, 근거 범위, 보류 이유를 따로 저장한다. Confidence를 비용값으로 바꾸지 않는다.

### 3.3 탐색 중 적용과 시간 범위

새 특징은 **공동 DP 탐색의 전이 비용**이다. 먼저 선택한 경로를 사후 재순위화하는 방식이 아니다. 완료 왼쪽 run의 시작/끝과 실제 오른쪽 signature를 상태에 연결하고, 같은 signature의 raw edge 분할은 하나의 harmonic run으로 계산하여 credit을 중복하지 않는다.

오른쪽 화음 소속은 n의 **도착 시점**에 대한 조건이다. n의 전체 음가 끝까지 같은 오른쪽 화음이 유지된다고 가정하지 않는다. 전체 준비/도착 음가의 source-clock 검증과 그 음가 전체의 화성 소속 확정은 다르다. 이 제한 덕분에 같은 오른쪽 signature/attack 집합의 전이를 묶는 factorization이 성립한다. 원 raw-edge cap, 동점 ID 순서, 정확 유리수 비용과 2M 계산 예산을 유지한다.

작은 DAG 10개×3조건의 모든 경로를 직접 채점해 최적 비용/동점 선택을 대조했다. 실제 63개 승자도 독립 경로 채점으로 검산했다. 정확 탐색이라는 말은 **선언한 비용의 최적화**이며 음악적으로 올바른 분석을 뜻하지 않는다.

## 4. 실제 범위와 측정

기존 15악장/악보 package·명명 기반 9작품군의 72구간을 그대로 사용했다. 14package/8지원 작품군의 source가 준비됐고 K283의 6구간은 기존 시간/ID 보류다. 63개 선택 구간의 원 44,204edge를 재사용했으며 후보 재생성은 0회다. 이전 9보류(2M 2개, 반복/계획 1개, source 6개)를 모든 조건의 분모에 남겼다. 완전 평가 가능 51구간, 부분 평가 21구간이며 후보 ceiling은 36/51로 같다.

72예측을 모두 저장·봉인한 다음 참조 report를 열었다. 추론에 주석/사용자 정답을 입력하지 않았다. **이미 노출된 개발 자료이며 겹치는 구간도 있으므로 독립 blind 평가가 아니다.** Full Roman·전위·국소 조성·종지·NCT 전체 정확도도 아니다.

| 조건 | 전체 진행 일치 / 완전51 | 근음+철자 구성음 시간 일치 | 작품군 macro | 경계 TP/FP/FN | 경계 F1 |
|---|---:|---:|---:|---|---:|
| control | 16 | 27.0012% | 51.9033% | 49/21/14 | 73.6842% |
| selected_roles | 15 | 26.3011% | 51.6722% | 49/22/14 | 73.1343% |
| shared_support | 16 | 27.0012% | 51.9033% | 49/21/14 | 73.6842% |

시간 coverage는 모두 43.7106%다. Whole denominator, 시간 분모, macro를 서로 대체하지 않는다. Control의 원 비용·선택·평가표가 단계65와 같다.

selected_roles는 3개 기록에서 선택이 바뀌었다. 쇼팽은 5/2quarter 일치를 잃었고, 코렐리 두 기록은 같은 `[124,132)` 음악 범위의 중복 문맥으로 시간 일치 변화가 0이다. 독립 3개 음악 개선 사례가 아니다. 선택된 경로의 새 조건부 근거는 selected_roles 3출현, shared_support 0출현이다. 세 조건 모두 63선택/9보류이며 새로운 예산 보류는 없다.

실제 runner는 260.153초/exit0다. 조건별 선택+독립 채점 합계는 control 50.219초, selected_roles 60.472초, shared_support 59.782초다. 다른 활동이 있는 Windows 실행의 한 관측이며 정식 속도 benchmark가 아니다. 후속 audit/회귀는 runner 종료 후 병렬 실행했다.

## 5. 실패를 설명하는 원악보 사례

### 5.1 쇼팽 — 앞뒤 화음 소속만으로는 잘못된 분할도 유리해진다

`dcml:chopin-mazurkas:BI145-2op50-2`, `cont_1f300d84b87bfc76ff30`, `[28,61/2)`.

Control의 E♭7 전체 비용은 `559/2800 ≈ 0.199643`이다. Gdim `[28,30)` → E♭major `[30,61/2)` 경쟁 경로는 기존 비용 `129/560 ≈ 0.230357`이다. D♭5→C5→B♭4 형태에서 p/n이 Gdim 구성음이고 도착 B♭은 E♭major에도 속한다. 이 소속 관계만으로 C5를 조건부 경과로 가점하면 `-1/28`이 붙어 비용이 `109/560 ≈ 0.194643`이 된다. 잘못된 분할이 전체 E♭7보다 유리해진다.

가운데 C5 동안 실제 G4/D♭4가 지지하지만, 선택된 경계 이후 두 공통 구성음의 양성 지속은 없다. 원 ID `sound_a1488d475c80`, `sound_f7e73160e8fe`를 참조한 shared_support 대조는 `fewer_than_two_actual_shared_members_at_arrival`로 이 credit을 보류한다. 분할 비용은 다시 `129/560`이고 control의 전체 E♭7이 유지된다. 실제 release를 바꾸거나 새로운 음을 생성하지 않았다.

**교훈:** 준비/도착 음의 소속이 맞는 것은 필요 근거일 수 있으나 화음 유지/교체의 정답 증명은 아니다. 공통음 지속 관문은 이 퇴행을 피했지만 일반적인 NCT 인식을 개선했다고 증명하지 못했다. 선택 경로에서 credit 0인 결과를 성공적인 NCT 검출로 보고하지 않는다.

[원음·비용·좌우 조건부 근거 case](../../../output/harmony-joint-nct-2026-10-05-r1/cases/3e987ee8bfece8435be5.json.gz), [전체 원 MusicXML](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/368d46f4807d08ac9fad/source.musicxml), [전체 Canonical IR](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/368d46f4807d08ac9fad/canonical-ir.json.gz).

### 5.2 코렐리 — 누락/생략 문제는 이번 NCT 관문만으로 풀리지 않는다

`op01n05c`, `[55,56)`: 세 조건 모두 E/G/B♭ → E/G/B♭/D → C/E/G를 선택하며 비용은 `663/4000 = 0.16575`다. 실제로 관측하지 않은 B♭을 허용한 후보가 전체 C/E/G의 사후 witness 비용 `309/1600 = 0.193125`보다 낮은 문제가 남는다. Candidate의 구성음을 적었다고 원악보에 그 음을 만들어 넣은 것은 아니다. 이번 새 credit으로 해결했다고 보고하지 않는다.

[코렐리 원source/비용 case](../../../output/harmony-joint-nct-2026-10-05-r1/cases/43984eca2bd701128390.json.gz).

`op01n05a`, `[124,132)`: selected_roles가 B♭ 기반 A포함 후보 대신 A없는 후보를 고른 두 문맥은 동일한 범위와 원 지속음에 의존한다. 새 이웃음 형태 credit으로 비용은 줄었으나 주석과의 시간 일치는 늘지 않았다. 두 개의 독립 변화나 성능 향상으로 세지 않는다. [대조1](../../../output/harmony-joint-nct-2026-10-05-r1/cases/e146c10d932bf1d6c977.json.gz), [대조2](../../../output/harmony-joint-nct-2026-10-05-r1/cases/fde70cf5517606b2a93a.json.gz).

단계65의 18사례를 모두 이어 보존했다. 이전 Sonata의 Gminor→G♯dim7→E7과 quartet의 B♭7 결과도 유지한다. 새 case는 전체 원 XML/IR 경로·SHA, 원음표 ID, 모든 조건의 실제 경로/비용/전이 근거와 사후 reference witness를 참조한다. Reference witness는 예측 봉인 이후의 비용 진단용이며 추론에는 쓰지 않는다. 이번 새 화면 제작은 하지 않았다.

## 6. 구현 파일, 검증 및 실패 기록

| 파일 | 역할 |
|---|---|
| [harmony_joint_nct_scoring.py](../../../src/musicanote_harness/harmony_joint_nct_scoring.py) | 선택되는 좌우 화음 조건·전이 점수·정확 공동 DP·독립 경로 비용 |
| [harmony_joint_nct_trial.py](../../../src/musicanote_harness/harmony_joint_nct_trial.py) | 세 조건 실행·기존 범위/보류 유지·예측 봉인·주석 대조·18사례 저장 |
| [audit_harmony_joint_nct.py](../../../scripts/audit_harmony_joint_nct.py) | 출처/코드/예측 SHA와 비용·원graph·지표·사례 사후 재생 |
| [validate_harmony_joint_nct.py](../../../scripts/validate_harmony_joint_nct.py) | 기존 관련553검사 + 신규27검사 실행 |
| [scoring 검사](../../../tests/test_harmony_joint_nct_scoring.py) | 신규17개: 실제 소속·지속·박절·철자·관문·raw 분할 불변·전수 최적/동점 |
| [trial 검사](../../../tests/test_harmony_joint_nct_trial.py) | 신규8개: 봉인/누출·입력/graph 변조·기존 보류·덮어쓰기 거절 |
| [audit 검사](../../../tests/test_audit_harmony_joint_nct.py) | 신규2개: 미확정 결과의 승인 위장/보류 credit 거절 |

- 신규27검사 PASS, 10.782초. 최종 관련 **580검사/42모듈 PASS**, failure/error0, 57.665초. 전체 repository test suite를 실행했다는 뜻은 아니다.
- 사후 감사 PASS: **1,495고유SHA**, 72구간×3조건 지표 재생, 14전체 XML/IR, 원 44,204edge codec 왕복, **189승자 비용** 독립 재계산, 18사례와 사후 witness 비용/근거 재생. 새 추론/학습을 감사 때 재실행하지 않았다.
- 첫 scorer 검사 16개 중 5error: 4개는 최종 선택 경로 복원에 factored 연산 budget을 raw edge 수로 준 구현 문제였다. 이미 선택한 경로 하나만 기존 unbatched 복원기로 읽도록 새 모듈을 고쳤다. 비용 최적화나 예산을 느슨하게 바꾼 것은 아니다. 나머지1개는 fixture의 raw neighbor row에 없는 identity 접근이었고 정규화된 후보 identity를 읽도록 고쳤다. 기존 검사 기대값/원봉인 모듈은 변경하지 않았다.
- 실제 r1은 완료했으며 실패 partial runner/rerun은 없다. 기준선 report SHA와 이전 봉인 코드의 불변을 확인했다. 사후 분석의 후보 ceiling은 실제 `lattice_hit` 36 true/15 false/21 null로 확인했다.
- 문서 검증: 메인/개발 로그/이번 기록 strict UTF-8, replacement character0, 로컬 링크274개/누락0, 신규8파일 trailing whitespace0. `git diff --check` exit0이며 기존5개 tracked dirty 파일의 LF→CRLF 경고는 그대로다. 문서 수정은 실험의 pinned code/input을 바꾸지 않았고 report SHA도 같다.

## 7. 산출물과 재현

정본: [report.json](../../../output/harmony-joint-nct-2026-10-05-r1/report.json), [run contract](../../../output/harmony-joint-nct-2026-10-05-r1/run-contract.json), [예측 봉인](../../../output/harmony-joint-nct-2026-10-05-r1/prediction-freeze.json), [사후 감사](../../../output/harmony-joint-nct-2026-10-05-r1/post-seal-audit.json), [회귀 검사](../../../output/harmony-joint-nct-2026-10-05-r1/test-validation.json).

Report SHA: `3388bcb8dd0279a7c1781fa946afc3e53f4bd11498c6f87ccf37194ca8c7762d`.

원 72예측, source reference, 18case를 새 output 아래 저장했다. 원graph/전체 악보는 SHA 경로로 재사용한다. 같은 파일을 복사하지 않아도 원악보를 재현할 정보가 유지된다. 기존 r1을 덮어쓰지 않는 재현:

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_joint_nct_trial --source output/harmony-component-support-2026-10-05-r2 --output output/harmony-joint-nct-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/audit_harmony_joint_nct.py --root output/harmony-joint-nct-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/validate_harmony_joint_nct.py --prior-validation output/harmony-component-support-2026-10-05-r2/test-validation.json --output output/harmony-joint-nct-2026-10-05-r2/test-validation.json
```

## 8. 다음 큰 개발 단위

다음은 같은 공통음 관문을 계속 세분화하는 작업보다 **화음 유지/교체·생략과 비화성음 설명의 점수 균형**이다. 실제 앞뒤 화음에서 장식 설명이 성립하는 조건은 유지하되, 구성음의 실제 제시/지속, 누락 가능성, 준비·해결·전이 증거를 구별하고 새로운 Train 전용 특징/학습 대조로 연결한다. 지속 공통음이 없다는 이유로 실제 화음 교체의 모든 NCT를 제거하지 않는다.

유형 확장은 영향이 큰 미설명음부터 준비·강세·실제 tie/성부·해결을 확인한다. 모든 교재 예외 구현을 첫 평가의 전제로 삼지 않고, 주요 오류 개선과 비중복 작품군/공개 모델 평가를 병행한다. 확인된 개선과 coverage/퇴행을 측정한 뒤 새 엔진을 운영 화면에 연결한다. 국소 조성/Roman/전위/종지 선택 정확도, 장문 2M 문제, NCT 전체 검증, 작곡편곡 생성은 남아 있다.

기존 자료의 출처/이용 조건, 비상업적 로컬 연구 자격 및 운영 학습 미승인 상태는 바꾸지 않았다.

현재 상태·순서는 [메인 개발 문서](../README.md) 앞부분을 기준으로 삼는다. 사례·실패·채택 결정을 [개발 로그](../DEVELOPMENT_LOG.md)에 연결했다.
