# 단계89 — 순위 보호 모델의 고정 Dev 비교

## 목적과 변경 범위

단계88의 Train 개선이 다른 개발 작품군에서도 유지되는지 확인한다. 이번 단계에서 모델을 다시 학습하거나 Dev 결과에 맞춰 계수를 고르지 않는다. 기준26 / 단계83 역할35 / 단계88 순위 보호35의 전계수와 비교 순서를 사전에 고정했다.

이 문서는 화성 **개발 기록**이다. 인수인계 문서나 구조 분석 로그에 누적하지 않는다. 실행·검사·사후 감사를 완료했다. **Train에서는 소폭 개선됐지만 이번 Dev에서 단계83 역할35 대비 추가 개선은 없었다. 운영 미채택이다.**

## 사전 계약

- 원 Dev 72 record / 63 graph / 60고유 시간 범위 / 14전체 악장 source / 9작품군을 유지한다. 원9보류, 부분 주석, 정답 후보 부재를 제외하지 않는다.
- 같은 원 graph·44,204edge·raw cap6·2,000,000전이·조건당20초 cooperative guard다. 새 cache를 조건마다 만들며 중단 시 부분 승자를 반환하거나 재시도하지 않는다.
- 추가9항이0인 기준26은 같은 점수의 기존 exact batched decoder를 사용한다. 세 조건의 실행량이나 통제된 속도 벤치마크라는 주장은 하지 않는다.
- 원 XML/IR, 붙임줄, grace, 철자, 음표 ID, Fraction 시간축과 source-clock 검증을 보존한다. 모든 새 예측을 봉인한 뒤 이번 평가 참조 report를 읽는다.
- 이미 노출된 Dev 및 역사 계보 자료를 사용한다. Train과 Dev의 이름 작품군 ID는 분리하지만 전체 판본/악장 중복 감사 또는 독립 Test를 대신하지 않는다.
- fit/sweep/checkpoint 선택/loss-augmented 탐색/reference-compatible 탐색/작품별 예외/후보 정책 변경/운영 승격은0이다. 계수는 단계88의 활성240대조·실제 경쟁62개 및 봉인 모델로부터 검증해서 읽는다.

| 조건 | 계수 출처 | 모델 SHA256 |
|---|---|---|
| `frozen_old26` | 기존26 + 추가9항0 | `2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf` |
| `frozen_member_role35` | 단계83의 역할35 | `3f2c10e7899b3e66696be82bc64e41530829cb48c23707c456dcc3231033d346` |
| `frozen_ordinal35` | 단계88의 순위 보호35 | `b6ff68e73bf6b5b9760107344f66f5c5626da2aa5c8b93ca061c21d6cbc74f38` |

## 구현과 검증 항목

새4파일만 추가하고 앞 단계 봉인 코드를 수정하지 않았다. 단계86의 검증 패턴과 동일한35항 scorer를 재사용한다.

- `src/musicanote_harness/harmony_ordinal_protection_dev_trial.py`: 고정 모델 검증·원63graph 재선택·72예측 선봉인·사후 참조 평가·모든 attempted 사례 저장.
- `tests/test_harmony_ordinal_protection_dev_trial.py`: 신규10검사. 봉인 모델 요구, 실제 Train pool로부터 no-fit 계수 재생, tiny graph 전수 최적값, zero-extra legacy 동일성, wall/원 보류 보존, 예측 봉인→참조 순서, 공통 완료/계산 손실 분리.
- `scripts/validate_harmony_ordinal_protection_dev.py`: 단계88 검증 SHA와89모듈/944검사 inventory를 유지한다. 신규10검사를 추가한다.
- `scripts/audit_harmony_ordinal_protection_dev.py`: 모든 SHA·원source·graph·clock·승자/경쟁/witness 비용·scalar/detailed 전이·전사례·전체/공통 지표를 읽기 전용으로 재생한다. 추가 fit/search는 하지 않는다.

모든63 attempted 사례에는 전체 source XML/IR 경로와 SHA, 앞뒤를 재현할 수 있는 원시간/음표 ID, 세 조건의 승자 또는 보류, 각 조건의 같은 계수로 재계산한 경쟁 경로 비용을 보존한다. 참조 witness는 **예측 봉인 이후 평가 전용**이며 추론에 입력하지 않는다. 원9보류도 예측 inventory에 남긴다. Unknown과 알려진0을 섞지 않는다.

## 결과 해석 기준

전체72, 세 모델 공통 완료, 각 모델 쌍 공통 완료를 분리한다. 근음+구성음 시간 일치, 작품군 macro, 경계 F1, 전체 범위 일치, 계산 coverage와 정답 소실/신규 정답을 함께 본다. 검사 통과 수는 곡 수 또는 음악 정확도가 아니다. 이 비교는 전체 Roman·전위·국소 조성·NCT 정확도를 측정하지 않는다.

## 실행 결과와 결정

Actual `output/harmony-ordinal-protection-dev-2026-10-06-r1`은 **1,190.943504초 / exit0 / complete=true**다. 원72 record / 63graph / 60고유 범위 / 14전체 악장 source / 9작품군 / 44,204edge를 유지했다. 원9보류는 재시도하지 않았다. 완전 평가51 / 부분21을 유지했고, 이름 ID 기반 Train15작품군과 Dev9작품군은 겹치지 않는다.

| 조건 | 새 완료 | 새20초 보류 | 원 보류 | 전체 범위 일치(완전 평가51) | 근음+구성음 시간 | 작품군 macro | 참조시간 coverage | 경계 F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 기준26 | 62 | 1 | 9 | 16 | 29.7550% | 45.0578% | 42.5904% | 76.1905% |
| 단계83 역할35 | 46 | 17 | 9 | 14 | 19.4632% | 25.3458% | 27.4679% | 61.8557% |
| 단계88 순위 보호35 | 46 | 17 | 9 | 14 | 19.4632% | 25.3458% | 27.4679% | 61.8557% |

원 전체 참조 eligible time은 약357.083333quarter, unavailable reference time은 약242.083333quarter다. 범위가 겹치거나 중복되는 원record를 사후 제거하지 않았다. Macro는 근음+구성음을 평가 가능한8작품군이며 다른1작품군을0정답으로 채우지 않는다. 완료 구간 수와 시간 coverage는 분모가 다르다.

**세 조건 공통 완료46 record**의 비교(완전 평가37 / 부분9):

| 조건 | 전체 범위 일치(완전 평가37) | 근음+구성음 시간 | 작품군 macro | 경계 TP/FP/FN | 경계 F1 |
|---|---:|---:|---:|---|---:|
| 기준26 | 11 | 65.5055% | 44.7735% | 30/10/11 | 74.0741% |
| 단계83 역할35 | 14 | 70.8581% | 46.4159% | 30/4/11 | 80.0000% |
| 단계88 순위 보호35 | 14 | 70.8581% | 46.4159% | 30/4/11 | 80.0000% |

판단:

- 새 순위 보호35와 역할35의 완료 집합·raw path IDs·의미적 화음 진행은 **모두 동일**하다. 변경0 / 신규 정답0 / 기존 정답 소실0 / 계산 복구·소실0이다. 비용은 계수가 달라 재계산됐지만 비용 변화만으로 음악적 개선이라고 부르지 않는다.
- 단계88 Train 공통102의56→58 개선을 Dev 개선으로 확대해 주장할 수 없다. 이번 Dev는 **추가 개선 없음·퇴행 없음**이다. 순위 보호가 모든 새 작품에 충분하다는 증명도 아니다.
- 기준26 대비 공통 완료에서는 시간+5.3526%p / 신규 정답3 / 소실0이다. 그러나 기준26이 완료한16개를 두35모델은 추가로 보류하며 그중 기준 정답5개가 있다. 전체 범위 일치16→14 / 전체시간29.7550%→19.4632%를 계산 coverage 문제와 구별한다. 원9보류와 새17wall을 합쳐 같은 원인으로 설명하지 않는다.
- 기준26의 이번 완료62개는 과거 단계76의 같은 모델 경로·비용과 전부 동일하다. 과거 완료1개는 새20초 제한에서 보류됐다. 과거는 동일한20초 guard가 없었으므로 속도 우위를 주장하지 않는다.
- 단계86의 미채택 공동35는 공통46의13일치 / 시간65.2506%였다. 이번 순위 보호35는 그 퇴행을 보이지 않고 역할35 수준을 유지한다. 이는 **역사적 대조**이지 이번에 공동35까지 네 조건을 재실행한 결과가 아니다.
- 운영 화면·Claude 편곡 추론기 교체는 하지 않았다. 독립 Test / 전체 Roman·전위·국소 조성·NCT / 작곡·편곡 성능 검증은 여전히 남아 있다.

## 원악보 사례 — 유지된 판단과 미해결을 함께 보존

전체63case를 저장했다. 아래 사례는 참조 기반 자동 검증이며 human-validated 정답이나 작품 전용 규칙으로 승격하지 않는다. 시간은 quarter 기준 `[start,end)`다. 모든 사례는 전체 XML/IR과 앞뒤 원음표를 참조한다.

### Corelli op01n05d m31 — 앞선 정답 유지

`cont_42166b98e96d236572b6`, `[90,93)`, 6/8. 기준26은 F화음을 유지했다. 역할35와 순위 보호35는 참조의 F `[90,91)` → C `[91,91.5)` → F `[91.5,93)`를 모두 선택했다. 새 계수의 승자 비용은−0.073910406, 참조 witness와의 차이는0이다. 단계86 공동35의 A단3화음→F 병합 퇴행은 이번에 발생하지 않았다. 새로 발견한 정답이 아니라 기존 정답의 유지다.

- C5 `sound_7523ddb2bd52` / `note_74ceb9286939`: `[90,91.5)`, 1.5quarter 지속.
- E5 `sound_294c45de0f50` / `note_411a0d22abc1`: `[91,91.5)`, 0.5quarter 지속.
- F3 `sound_92e4e8f8c8c3` / `note_ea94fcf13879`: `[91.5,92.5)`, 1quarter 지속.

[이번 사례](../../../output/harmony-ordinal-protection-dev-2026-10-06-r1/cases/675a922cf55f7bbad819.json.gz), [전체 원악보](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/10f5096b6d393d5b9309/source.musicxml), [전체 IR](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/10f5096b6d393d5b9309/canonical-ir.json.gz). XML SHA `9e536828269db147f2ea1303c932ed5004927da2b809025be758814ac04249d1`, IR content SHA `337b11d08c2ceeba5459e402ea07c96a72ed4273ce9200143be49e5a29c3ddca`.

### Corelli op01n05a m21–22 — 근음 유지, 뒤7음은 아직 누락

`cont_85d80062c7022aa8b8ff`, `[124,132)`. 역할35와 새 모델 모두 첫 `[124,126)`에서 D–F♯–A를 선택한다. 기준26의 B♭–D–F♯보다 참조와 맞는 시간2quarter가 늘지만, 뒤 `[130,132)`의 참조 G7은 여전히 G단3화음으로 남아 **전체 일치는false**다. 같은 `[124,132)`의 원record `cont_26c2f8b6fd72b9c9bd49`도 유지하며 두 독립 음악 사례로 세지 않는다.

원음표는 F♯4 `sound_d17fda059a3c` / `note_64c3e3dbebf1` `[120,126)`와 D3 `sound_80af4e71d064` / `note_5c81e541c6f1` `[124,126)`다. B♭4 `sound_80106fe1131c` / `note_a0b2d62e2d7f` `[124,125)` → A4 `sound_5ee659c80afb` / `note_bc234d06035c` `[125,126)`도 보존했다. NCT 유형을 이 사례 설명만으로 확정하지 않는다. 새 승자 비용−0.151804113은 참조-compatible witness보다−0.416077046 싸므로, 참조를 읽을 수 있어도 현재 점수가 오답을 선호하는 문제는 남아 있다.

[이번 사례](../../../output/harmony-ordinal-protection-dev-2026-10-06-r1/cases/e146c10d932bf1d6c977.json.gz), [중복 원record](../../../output/harmony-ordinal-protection-dev-2026-10-06-r1/cases/fde70cf5517606b2a93a.json.gz), [전체 원악보](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/e157ec9d8d06c1083b45/source.musicxml), [전체 IR](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/e157ec9d8d06c1083b45/canonical-ir.json.gz). XML SHA `b767273cb4533fe347c15bac1dff36452ee9cc0ad6f669003c1ad641ac855f60`, IR content SHA `764ccc072f2164f90e993f4e850ef96bc2bd54e46e35422b19477992b4d38203`.

### Beethoven Sonata07-2 m63 — 과도한 병합은 피했으나 조기 구간은 미해결

`cont_a34e326e65fe7c9b7662`, `[747/4,375/2)`. 세 조건 모두 처음 `[186.75,187)`은 D–F♯–A, 이후 `[187,187.5)`는 F♯–A–C–E♭를 선택한다. 원 raw 두 분할이 같은 후반 화음인 것을 두 새로운 화음으로 설명하지 않는다. 전체 참조는 F♯감7 구성음이므로 앞부분은 여전히 불일치다.

E♭4 `sound_28dc7a52b39f` / `note_067a13afd3e9`와 C5 `sound_b6dd140eeefb` / `note_8a519760cc0e`는 모두 `[187,187.25)`에 실제 존재한다. 단계86 공동35처럼 전부 D3화음으로 병합하지 않았지만, 새 승자는 참조 witness보다−0.164811267 싸다. 임시표 읽기 누락 또는 해결된 NCT라고 단정하지 않는다.

[이번 사례](../../../output/harmony-ordinal-protection-dev-2026-10-06-r1/cases/2e759ecfbb34e7532a21.json.gz), [전체 원악보](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/a86ada3752f6688ea503/source.musicxml), [전체 IR](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/a86ada3752f6688ea503/canonical-ir.json.gz). XML SHA `53762a8b17faaeac368ddfa0cfccff60b050d49fc93c9f92476087dde4a211da`, IR content SHA `ce060889fac0841f9bd0a89aaa22def8f8d7d58739a08963ce9b36bde4df4077`.

## 최종 검사·감사·봉인

신규10검사와 단계88의944검사를 합쳐 **954관련검사 / 90모듈 PASS**, failure0/error0,126.342858초다. 전체 repository suite / 954곡이 아니다. 준비·Actual·사후 감사 실패0이다. Actual 시작 후 새4code/test/script 수정0이며 6,015 input / 137 artifact / 447 code pins를 유지했다.

사후 감사 **PASS / exit0**: 6,156고유SHA / 72예측 / 원9보류 / 14source / 44,204edge / 154승자비용 / 462동일계수 경쟁비용 / 108평가전용 witness 비용 / 627scalar 상세전이 / 전체63case / 이전63case 연결 / 전체·공통 지표를 재생했다. 추가 fit/search0이다. 원 XML/IR의 위9개 sound와 source-note 연결도 별도로 읽어 확인했다.

| 산출물 | SHA256 |
|---|---|
| report | `82ec2ecd234f4ed6165ddeb3d94392c7b05c9f22b7ac62ddb40de004d5f4f2ee` |
| 실행 계약 | `68a87c2f8545eaf7945118b1c20cf131c462f0a104f516b7d9567949b9d9eb88` |
| 예측 봉인 | `7e256d40056a581a106e541cc1af74a2e1063ccb9596c582a2ea08a16a9af2e5` |
| 사후 감사 | `072924e3de0d15baf145a94fd8519d7885e9110e923bc72e85298579bb7505c4` |
| 관련 회귀 | `4edee09710f90f0d9026d2508320daeeb37f5654d80300f9a161c71990690227` |

[Report](../../../output/harmony-ordinal-protection-dev-2026-10-06-r1/report.json), [사후 감사](../../../output/harmony-ordinal-protection-dev-2026-10-06-r1/post-seal-audit.json), [관련 회귀](../../../output/harmony-ordinal-protection-dev-validation-2026-10-06-r1.json). Mutable `progress.json`는 봉인 대상이 아니며 완료 여부의 정본은 report와 감사다. 원 Core/주석/부모봉인/권한/운영·UI·서버/Claude Phrase·Motif/Composition/MusicSearch/별개 tracked dirty5/Git를 보존했다. Merge/commit/push/API0이다.

## 다음 큰 관문

작은 Dev 차이를 얻으려고 다시 계수를 조정하지 않는다. 순위 보호 모델은 Train 소폭 개선·Dev 유지 수준의 연구 후보로만 남긴다.

1. **같은 점수로 복잡한 구간의 계산 보류를 줄이는 일반 계산 개선.** 먼저 원 Train의 보류 구간과 완료 control에서 DP 상태 확장 / source-only 특징 재계산 / 유리수 비용 계산을 구별해 측정한다. 라벨을 사용한 가지치기·후보 축소·cap 확대·부분 승자 반환은 금지한다. 단계81의 scalar 분리 이후에도 반복되는 계산을 점검한다.
2. 개선 구현은 원음표·availability·Fraction 비용·완료 경로 ID의 동일성을 검증하고 원118 Train 전체와 같은 고정 Dev 전체에서 확인한다. 유리한 몇 구간의 속도만으로 coverage 개선을 선언하지 않는다. 이는 성능 측정 단계이며 이번에는 아직 새 최적화 코드를 적용하지 않았다.
3. 화음의 유지·교체 / 실제7음 / 비화성음 설명의 **큰 Train 오답군**을 계속 보완한다. 계산 효율만 높여도 앞서 틀린 구간의 화음 판정이 저절로 좋아지는 것은 아니다. 독립 Test·전체 Roman/국소 조성·NCT 의미·생성 연결 관문을 유지한다.

Dev에서 본 세 음악 사례는 진단 기록이지 새 학습 target 또는 작품 전용 분기 조건이 아니다.

## 재현

PowerShell, `K:\Music Analysis`에서 새 output 이름을 사용한다. 기존 봉인 파일은 덮어쓰지 않는다.

```powershell
$env:PYTHONPATH = 'src;tests'
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_ordinal_protection_dev.py --prior-validation output/harmony-ordinal-protection-validation-2026-10-06-r1.json --output output/harmony-ordinal-protection-dev-validation-NEW.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_ordinal_protection_dev_trial --output output/harmony-ordinal-protection-dev-NEW
.\.venv\Scripts\python.exe -B scripts/audit_harmony_ordinal_protection_dev.py --root output/harmony-ordinal-protection-dev-NEW
```

선행은 [단계88 Train 한정 학습](2026-10-06-ordinal-protection-learning.md), 정본은 [화성 메인 개발 문서](../README.md)와 [화성 개발 로그](../DEVELOPMENT_LOG.md)다.
