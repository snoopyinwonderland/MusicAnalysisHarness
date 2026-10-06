# 단계87 — Train 정답 보호를 실제 오답 경쟁 대조로 교정

## 목적과 범위

단계86에서 확인한 기존67개 보호 대조는 `negative_ids == target_ids`, scored delta0, known gradient0이었다. 정답을 잘 지키는 제약이 아니라 자기 자신과 비교한 기록이다. 원기록을 지우지 않고 비활성 이력으로 보존하며, **음악적 해석이 실제로 다른 경쟁 경로**를 만든다.

이번은 **학습 자료의 교정과 원악보 연결 검증**이다. 새 가중치 학습·새 ordinary 예측·Dev 재평가·운영/화면/Claude 편곡 연결은 하지 않는다. 정답 보호가 실제 학습과 선택에서 작동하는지는 다음 단계에서 검증해야 한다. 기술 검사 통과를 화성 정확도 향상으로 읽지 않는다.

## 실행 전에 고정한 계약

- 대상은 원래118 Train 범위/15작품 가족 중 보호69범위다. 기존 zero-loss67범위 전부와 단계83·85에서 추가로 맞힌 서로 다른2범위를 합친다. 나머지49범위와 과거152제외 범위도 이력/분모에서 없애지 않는다.
- 각69범위의 참조는 기존 Train의 완전하고 지원되는 참조이며, target은 이미 봉인된 reference-compatible 경로다. 정답 후보를 새로 삽입하거나 후보 누락·부분 주석·unknown을 메우지 않는다.
- 점수는 단계83의 봉인 역할35항 그대로다. 모델 SHA `3f2c10e7899b3e66696be82bc64e41530829cb48c23707c456dcc3231033d346`. 단계85의 퇴행 계수를 새 기준으로 채택하지 않는다.
- 원 graph/정확 Fraction 시간/철자/붙임줄/voice/전체 XML·IR·ID·6raw cap을 보존한다. 전이2,000,000/범위당20초 cooperative guard, 재시도0. 한도 보류에는 부분 승자를 반환하지 않는다.
- reference time/boundary loss가 **양수인 완전 경로만** 탐색 끝에서 허용한다. 그 안에서는 기존 ordinary35항 비용의 정확 최소를 구한다. `cost-loss` 탐색이 아니며 정답 정보를 inference에 넣는 기능도 아니다.
- 원음표·성부의 특징 계산에는 주석을 쓰지 않는다. **학습용 경쟁자 자격 결정에는 Train 주석을 쓰므로 blind prediction이라고 부르지 않는다.**
- 기존198개 양수-loss 대조는 그대로 유지한다. 새 경쟁자가 이미 있는 대조와 같은 semantic runs를 가지면 기존 대조에 연결하고 가중치 방문을 중복시키지 않는다. 새로 찾지 못한 범위를 성공 사례로 만들지 않는다.
- 원부모 산출물에 이미 노출된 Dev의 역사 컨테이너가 포함되지만 이번 Dev의 graph/target/평가나 계수 튜닝을 하지 않는다. 독립 Test 검증도 아니다. 기존 NC/내부 연구 계약과 운영 학습 미승인은 유지한다.

## 일반 탐색 규칙

### 음악적 차이와 ID 차이의 구별

같은 근음·철자 구성음이 `[0,1)`과`[1,2)`에 이어지면 union run은 `[0,2)` 하나다. 이를 한 raw edge로 쓰거나 여러 edge/ID로 쓰는 것은 같은 화성 해석이므로 오답으로 취급하지 않는다.

오답의 증거는 기존 loss의 두 항이다.

1. 어느 시간에 참조와 다른 **근음+철자 구성음**을 사용했다.
2. 실제 semantic boundary를 놓치거나 없는 semantic boundary를 만들었다.

현재 평가 범위는 root+members와 경계이며 전체 Roman/전위/국소 조성/NCT의 의미 정답을 보장하지 않는다.

### DP 상태

기존 endpoint/raw-count/마지막3union-run에 **지금까지 semantic error가 있었는지**라는 단조 boolean만 추가했다. 모든 loss 증분은 음수가 아니므로 한번 오류가 생긴 경로가 나중에 올바른 마지막 화음으로 돌아와도 오답 자격은 유지된다.

Pareto는 같은 endpoint/history/**error bit**끼리만 적용한다. 비용이 싼 정답 경로가 같은 history의 오답 경로를 지워 버리지 않도록 한다. 기존의 run 대체, 기능적 전이, 3-run delayed 문맥, 마지막2전이 flush를 유지한다. Beam/top-N 오답 필터·작품별 분기·새 음악 hard gate는 없다.

완료한 경쟁자는 원 상세35항 receipt와 기존 semantic loss로 다시 검산한다. cost는 확률/확신도/음악적 정확도가 아니며 결과는 `analysis_export_allowed=false`, `prediction=false`다.

### Gradient와 margin 진단

Whole-path unavailable은 null gradient로 남긴다. 실제 점수의 known-local partial 합과 학습의 jointly-known whole-path gradient를 구별한다. 양수-loss인데 알려진 trainable gradient가 없으면 그 충돌을 감추지 않는다.

현재 gap(경쟁자 비용−target 비용), 요구 margin, 위반, 기존±.05 trust box에서 해당 대조의 **알려진 gradient 차원만 움직일 경우**의 최대 gap도 기록한다. 이 개별 upper bound는 전체 계수의 가능한 모든 변화나 공동 학습 가능성/음악 정확도를 증명하지 않는다. 특히 다른 대조에서 학습된 계수가 이번 unknown partial 점수에 영향을 줄 수 있으므로 ‘전체 모델에서 절대 불가능’으로 확대하지 않는다.

## 구현 및 검사

- `src/musicanote_harness/harmony_train_protection_search.py`: 원35항의 error-bit delayed exact 최소 경쟁자.
- `src/musicanote_harness/harmony_train_protection_trial.py`: 원198개 유지/67개 비활성 이력,69보호 범위, source/case/vector/중복 연결/진단 봉인. fit 없음.
- `tests/test_harmony_train_protection_search.py`: signed 점수의 작은 graph 전수 비교, 같은 화음 raw 분할/동일 edge 중복, error-bit Pareto, cap/guard/부분 참조/unknown.
- `tests/test_harmony_train_protection_trial.py`: Train·봉인·새 정답 포함·35항/null-gradient·semantic dedup·개별 trust-box 진단·작은 전체 runner·no-fit/no-overwrite.
- `scripts/validate_harmony_train_protection.py`: 단계86의85모듈/915검사를 유지하고 신규2모듈/15검사를 추가.
- `scripts/audit_harmony_train_protection.py`: 봉인/원 source/target/양수-loss/35항 cost와 availability/새 벡터/중복/분모 재생. 새 fit/search 없음.

준비 중 default toy를3quarter로 줄이며0음가 음을 만든 fixture8ERROR를 확인하고, 명시된 양수음가 fixture로 교정했다. 작은 전체 runner fixture의 `work_family_id` 누락1ERROR도 교정했다. 원 parser/grace 관문을 약화하지 않았다. 모두 Actual 전에 교정했다.

신규15검사 PASS. 최종 **930관련검사/87모듈**, failure0/error0, **105.653593초 PASS**다. 전체 repository suite나930곡의 정답률이 아니다. 신규6Python AST/UTF-8 검사도 통과했다.

## 실제 실행 결과

Actual `output/harmony-train-protection-2026-10-06-r1`은 **370.995158초/exit0/complete=true**로 완료했다. 전체118record/15작품군을 유지하고, 보호69범위의 **23전체 악장 source·26,335원edge**에서 계산했다. 같은 raw cap/35계수/원 특징을 유지했다. 이것은118개의 새 분석 예측이나69곡의 정답률이 아니다.

| 집계 | 결과 | 의미 |
|---|---:|---|
| 보호 탐색 | 69범위 | 원래 맞힌67 + 추가로 맞힌2 |
| 실제 양수-loss 경쟁자 완료 | 62 | 정답과 다른 해석의 exact 최저비용 경로 |
| 시간 한도 보류 | 7 | 새 경쟁자/부분 승자 없음, case와 target 보존 |
| 새 양수-loss 대조 | 42 | 기존198개에 추가 |
| 기존 대조와 중복 연결 | 20 | 새 방문/가중치 중복 없음 |
| 다음 학습용 활성 대조 | 240 | 원198개 + 새42개 |
| 비활성 자기 비교 이력 | 67 | 원265개 중 loss0/동일path 기록 전부 보존 |
| 탐색하지 않은 원범위 | 49 | 원118분모/이력 유지 |

62개 경쟁자 모두 jointly-known trainable gradient에 비0 차이가 있다. 기존의0-gradient 자기 비교를 실제로 바꿀 수 있는 자료가 생겼다. **이 사실은 학습 후 정답을 지킨다는 증명이나 음악 정확도 향상은 아니다.**

### 현재 점수에서의 보호 상황

- 경쟁자 비용이 stored target보다 낮은 범위는6개다. 원래 old arm에서 맞힌 범위라고 현재의35항도 맞힌다고 가정하지 않는다. 이6개는 모두 이미 기존 양수-loss pool에도 같은 대조가 있었다. 따라서 이전 학습의 퇴행을 ‘오답 사례가 없어서만 생긴 문제’로 단정할 수 없다.
- 나머지56개는 target이 경쟁자보다 싸지만, 정규화 loss만큼의 margin까지 만족한 것은2개뿐이다. 현재 비용의 순위와 loss-margin 만족을 구별한다.
- 원±.05 trust-box에서 **그 대조의 알려진 gradient 차원만** 움직일 때 요구 margin까지 도달 가능한 것은4개다. 이는 기존 강한 요구 margin이 제한 조정과 잘 맞지 않을 수 있다는 진단이지, 전체 공동 모델의 불가능성이나 bounds 확대를 정당화하는 결과가 아니다.
- 별도 읽기 전용 대조에서 중복 연결20개는 기존 벡터와 `score_delta/gradient_delta/available/loss`까지 **모두 동일**함을 확인했다. semantic 중복을 이유로 서로 다른 수치의 대조를 버린 경우는 이번에는 없다.

보류7개는 Chopin op41-2`[3,8)`, Beethoven03-2`[107,110)`, Chopin op41-1`[242,247)`, Beethoven02-2`[93,96)`와`[3,8)`, Corelli op01n03a`[59/2,63/2)`, Mozart K281-1`[13/2,10)`다. 원 target과 source는 저장했지만 새 competition을 얻었다고 세지 않는다. cap/budget 변경·재시도·과거 경쟁자로 자동 대체하지 않았다.

모든69case에 전후 문맥을 재현하는 전체 XML/IR·SHA·원note/sound ID·원graph/target·경쟁자 또는 보류·35항 receipt/차이·availability·학습 자격을 저장했다. 실제 fit/새 계수/ordinary 정확도/운영 승격은0이다.

### 봉인 및 사후 감사

실행 시작 후 신규6code/test/script는 변경하지 않았다. 4,131input/72artifact/445code pins를 봉인했다. **사후 감사 PASS/exit0**: 4,210고유 SHA·4,202sealed 입력 재읽기·69source 범위/23전체 악장/26,335원edge·131상세 비용·114scalar 전이·240활성 벡터/67비활성 이력/118record를 재검산했다. 새 fit/search/Dev0이며 작은 graph의 exact 전수 검증과 실제 case의 비용·loss 재생을 구별한다.

| 산출물 | SHA256 |
|---|---|
| report | `9769f95b6fe91e2cc7e60bd18348f8897172f96d4b29c87e6c2b2b282570a2f5` |
| 사후 감사 | `658298065027cfd35ce8edc1a2dd559c968b6523781dfc68d41f03aa688b21f5` |
| 실행 계약 | `dc7c50785320171e745ed46f50e2fd4e97fd42be39e6dce978163edebfb2cac5` |
| 활성240벡터 | `3c6c138a1c90ff76ae563b4ffa8d788bc27fed1dd97f8107d3d1e58b2abe2573` |
| 관련 회귀 | `c72f4f60e50b99b18c0c5e20f00587c7eaf6c5e1065f29ee1fb656d29191f9dc` |

[report](../../../output/harmony-train-protection-2026-10-06-r1/report.json), [사후 감사](../../../output/harmony-train-protection-2026-10-06-r1/post-seal-audit.json), [회귀](../../../output/harmony-train-protection-validation-2026-10-06-r1.json). Actual/감사 실패0. 원Core/주석/부모봉인/권한/운영·UI/서버/Claude Phrase·Motif/Composition/MusicSearch/기존tracked dirty5/Git를 보존했다. merge/commit/push/API0이다.

## 실제 원악보 대조 — 자기 비교가 아닌 음악적 경쟁

아래는 이번 miner가 선택한 **오답 경쟁자**이지 새로운 자동 분석 결과가 아니다. 참조 기준의 자동 사례이며 human-validated label로 승격하지 않는다. 모든 시각은 전체 score의 quarter offset, `[start,end)`다. 음표와 feature는 원 XML/IR에 역추적되며, 개별 작품을 조건으로 하는 규칙은 없다.

### Beethoven Quartet op18-1 IV m133–134 — 유지 화음의 짧은 과분할

`cont_00fe53c74ace3533c190`, `[265,533/2)`. Target은 D♭–F–A♭를 전범위 유지한다. 가장 싼 양수-loss 경쟁자는 `[265,531/2)`를 F–A♭–C로 해석한 뒤 D♭–F–A♭에 복귀한다. 복귀 뒤의2raw edges는 같은 화음이므로 하나의 union run이다.

원 첫음들은 D♭4 `sound_d8d1550662d3`/`note_47893f878e74`, F4 `sound_5b46b545ccea`/`note_96a8e85d0174`, A♭4 `sound_8e057865dfa1`/`note_9f6497a74bba`, 모두`[265,531/2)`다. 원음이 C로 바뀐 것이 아니고 원 후보의 경쟁 해석을 찾은 것이다.

경쟁자−target gap은 `488203/3000000 ≈ +.162734333`로 현재 target이 싸다. 구성음 지지+.042022778/외부음+.197908667/단순성+.028387333과 문맥−.105584444가 상쇄된다. 요구 loss-margin `7/12`는 현재 gap보다 커서 아직 만족하지 못하지만 이를 ‘현재 선택 오답’과 혼동하지 않는다.

[학습 대조 사례](../../../output/harmony-train-protection-2026-10-06-r1/cases/cont_00fe53c74ace3533c190.json.gz), [원 전체 악보](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/c421f89dc2ddceec5a94/source.musicxml).

### Beethoven Quartet op18-1 IV m269 — 짧은 이웃음과 7화음 경쟁

`cont_05a973a926c1c81874af`, `[2147/4,1075/2)`. Target은 F–A–C를 유지하고, 경쟁자는 E를 더해 F–A–C–E로 읽는다. 경쟁자의2raw edges는 동일 화음이라 **새 화음 경계가 두 개 생긴 것은 아니다.**

실제 베이스 F3 `sound_a04ae05137a5`/`note_b437e86c2217` `[2147/4,537)`→E3 `sound_2499e7347984`/`note_bd140b9833c7` `[537,2149/4)`→F3 `sound_5b168af46292`/`note_9e6a4517a6cb` `[2149/4,1075/2)`가 있으며 C4/A4는`[536,537)`에서 들린다. 기존 receipt의 `neighbor_like`는 조건부 형태이며 확정 NCT로 바꾸지 않았다.

경쟁자 gap `-61397/7500000 ≈ -.008186267`: 외부음 비용−.201643267이 단순성 비용+.193457을 이겨 이 범위에서는 오답 경쟁자가 더 싸다. 양수-loss1/known 비0 gradient를 갖는 실제 반례다. 이 경우만을 위해 E음이나7화음을 삭제하는 규칙은 추가하지 않았다.

[학습 대조 사례](../../../output/harmony-train-protection-2026-10-06-r1/cases/cont_05a973a926c1c81874af.json.gz), [원 전체 악보](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/c421f89dc2ddceec5a94/source.musicxml). 두 Quartet 사례의 XML SHA는`8ff0da1ba6f57134e14e9152f30753c4f445e0315dfd567af882d5207626dd57`이며 원 IR file SHA는`aa3f85180cdf54fd19d5e1c9cb9b86fc63cc5200248c53e0ece93727579810ad`다.

### Chopin op41-4 m6 — 구성음이 같아도 분석 근음이 다른 경쟁

`cont_10052b9e53534d175091`, `[16,19)`. Target4raw edges는 A♭근음/A♭–C–E♭의 같은 화음이라 **한 개의 union run**이다. 경쟁자도 앞`[16,18)`는 동일하지만 마지막`[18,19)`의 분석 근음을 E♭로 바꾼다. 같은 구성음 집합이라도 분석 근음/기능적 six-four 가설은 별개이므로 기존 참조 기준으로 양수 loss가 된다. 베이스 음을 곧바로 근음으로 확정하지 않는다.

원 A♭2 `sound_346418bffe90`/`note_bf7de27ac4f1`는`[16,17)`에 있다. 마지막에는 E♭3 `sound_3990c2038a95`/`note_b74c224e19ba`, A♭3 `sound_b7ea0721bf99`/`note_3aaaa4950f5e`, C4 `sound_edcc323b25da`/`note_92cb557dc8fe`, E♭4 `sound_c3c751e59f3c`/`note_33b5d019f72d`가 모두`[18,19)`에 존재한다. E♭베이스 관찰과 A♭분석 근음 target을 구별했다. Source 안의 검증된0음가 grace도 원 IR에 보존하며 새 지속음으로 늘리지 않는다.

경쟁자 gap `18370427/78000000 ≈ +.235518295`로 현재 target이 싸다. 외부음+.027289795/단순성·움직임+.2082285다. 이를 새로 고친 분석 정답이라고 보고하지 않는다.

[학습 대조 사례](../../../output/harmony-train-protection-2026-10-06-r1/cases/cont_10052b9e53534d175091.json.gz), [원 전체 악보](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/9db492071fd6640e5a45/source.musicxml). XML SHA`b3c984794d352f71edc974505caba85cbd303d651fc23b8be33eb83fd0d7d31b`, IR file SHA`2d7477766091b7227a95e46e100b0363951ab3626109133ac9377d4c5cb5bd7c`.

## 다음 단계 — 학습과 실제 정답 보존을 별도로 검증

이 유효한 대조를 사용한 **한정 Train 학습 → 원118범위 fresh ordinary 선택 → 기존 정답 소실/새 복구/시간·작품군·경계/계산 보류 비교**가 다음 관문이다. 개별 margin 불충족을 해결하려고 Dev 가중치나 모든 bounds를 임의로 바꾸지 않는다. Protection margin과 실제 정답 보존을 구별하고, 필요한 경우 알려진 큰 충돌의 목표/규제를 Train 근거로 먼저 정한다.

그 뒤에만 고정 Dev를 다시 비교한다. 미채택 모델을 Claude 추론기나 운영 화면에 먼저 연결하지 않는다. 원음표·전후 XML/IR·의견·계산 버전을 보존하는 별도 화성 개발 기록을 계속 유지한다.

## 재현

PowerShell, repository root. 기존 output은 덮어쓰지 않고 새 이름을 사용한다.

```powershell
$env:PYTHONPATH = 'src;tests'
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_train_protection.py --prior-validation output/harmony-joint-balance-dev-validation-2026-10-06-r1.json --output output/harmony-train-protection-validation-NEW.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_train_protection_trial --output output/harmony-train-protection-NEW
.\.venv\Scripts\python.exe -B scripts/audit_harmony_train_protection.py --root output/harmony-train-protection-NEW
```

정본은 [화성 개발 메인](../README.md), [화성 개발 로그](../DEVELOPMENT_LOG.md)다. 앞 단계 결과는 [단계86](2026-10-06-joint-balance-dev-check.md)을 따른다.
