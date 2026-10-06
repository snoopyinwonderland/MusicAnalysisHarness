# 계류음 보류와 지연 구성음 대조

기록 ID: HARM-DEV-20260930-04 · 2026-09-30

## 목적과 범위

직전 단계의 실제 음정·박절·구성음 시간 지지를 사용하여, 하행 해결 형태를 계류음 정답으로 오인하지 않게 한다. 사용자의 계속 진행 승인에 따른 일반 규칙 개발이며 특정 작품 교정은 아니다. 새 교재 독해, 학습, 조성/화음 최종 선택, 운영5173 승격은 이번 범위에 없다.

계류음에는 준비·지속·불협화·해결 및 박절/양식 문맥이 필요하다. 현재 계산된 실제 최저음은 구조적 베이스가 아니고, 박자 분모 위치는 강약 판단이 아니다. 따라서 아직 미검증인 조건을 **명시적 보류 이유**로 저장한다. 모든 계류 후보를 확정하거나 단순한 협화 음정표로 제거하지 않는다.

## 구현 계약

- `harmony_boundary_assessment.py`, 버전 `boundary-assessment-0.1.0`.
- 기존 `temporal_observations`를 읽어 별도 `boundary_assessment`를 추가한다. Core, 원주석, 후보, 음형, 기존 조건부 설명량은 변경하지 않는다.
- 동일 span/구성음의 support profile마다 시작 셀의 구성음, 첫 관측 시각/셀, 늦게 관측된 구성음, 구간 끝까지 미관측된 구성음을 기록한다. spelling과 유리수 시각을 유지한다.
- 상태는 `all_members_at_entry`, `all_members_observed_with_delay`, `partial_members_observed`, `no_members_observed`, `unknown_pitch_limits_support`로 구분한다.
- 뒤늦게 모든 구성음이 나타나도 실제 분산화음 확정이 아니다. 한 구간에 우연히 여러 화음의 음이 모였을 수 있다. 구성음 생략 역시 자동 기각 사유가 아니다. 미정 pitch가 있으면 미관측을 확정 부재로 바꾸지 않는다.
- 기존 준비된 계류 후보만 이번 판단 대상으로 삼는다. 준비 onset·가정 경계·해결 onset을 실제 최저음 음정과 meter evidence에 연결하고 원 pattern/assignment refs를 보존한다.
- 구조적 베이스, 준비의 협화성, 경계의 불협화성, 해결의 협화성, 박절/양식, 화성 교체는 여전히 미확인이므로 `abstain`. 연결된 해결음과의 시간 간격 및 최저음 부재가 있으면 추가 보류 이유를 남긴다.
- 같은 음을 구성음으로 보는 유지/뒤 화음의 읽기 index를 경쟁 해석으로 저장한다. 이미 보류된 reading은 제외한다. 후보 개수는 투표·확률이 아니다.
- 전후 reading 조합과 assignment별 적용 조건은 기존 factorized pattern을 사용한다. 조합 전체를 데카르트 곱으로 부풀리거나 최고 후보를 선정하지 않는다.

## 실제 재계산

입력: `output/harmony-boundary-observations-2026-09-30-r2/`.

출력: `output/harmony-boundary-assessment-2026-09-30-r2/`. r1은 보존하며 r2에서 페이지 제목만 이번 단계명으로 갱신했다. 두 실행의 표본 JSON/보고서는 동일하다.

| 범위 | 표본 | 경계 | 시작에 전 구성음 | 지연 후 전 구성음 | 일부만 관측 | 계류 보류 |
|---|---:|---:|---:|---:|---:|---:|
| Beethoven 02-3 | 43 | 0 | 0 | 0 | 0 | 0 |
| Mozart K281-3 | 67 | 65 | 80 | 1,602 | 6,104 | 11 |
| Mozart K280-1 | 74 | 52 | 98 | 1,164 | 5,047 | 10 |
| 합계 | 184 | 117 | 178 | 2,766 | 11,151 | 21 |

구성음 열은14,095개 **중복 가능한 후보/범위 profile**의 집계이며 실제 화음 수가 아니다. 기존135음형 중21개의 계류 형태만 이번 명시적 보류 검사 대상이다.21개 모두 구성음으로 보는 경쟁 reading이 있다. 이것은21개가 틀렸다는 판정도, 정확도 향상 수치도 아니다. 베토벤0은 이전에 고정된 범위에서 지속음 내부 추가 경계가 없다는 뜻이지 악장 전체에 계류음이 없다는 뜻이 아니다.

모든 사례의 train/internal research 권한, 원자료 hash, 원계획/추가 경계계획 hash를 검증한다. 새 필드를 제거한 JSON이 이전 결과와 완전히 같은지 확인하고 이전184표본의 실행 전후 hash를 검사한다. `run-contract.json`에는 source report, 코드, UI hash를 남긴다. 기존 counterfactual-checks 파일은 이전 검사 기록으로 복사하며 이번에 다시 실행한 것으로 주장하지 않는다.

## 대표 악보 사례

- case: `reviewm_555ff701230fc0b8ee66` / Mozart K281-3 / sample16 / boundary0.
- 표기2마디+3quarter ~3마디+3quarter, global `[9,13)`, 경계 `21/2`.
- B♭4 `sound_0b9d0a329fff` (`note_4d67992530b4`) → A4 `sound_82e6cfa6216c` (`note_24b72caac4b0`).
- 원 pattern `boundary_nct_228db2cec7c3aca22fe6`와 원 성부 연결 가정은 유지.
- 분할 뒤 Dmajor를 선택하면 A/D는 늦게 관측되나 F♯은 끝까지 미관측. 따라서 '모든 구성음이 뒤늦게 모인 경우'와 구별된다. 계류음의 필수 조건은 미확인으로 표시한다.
- 분할 뒤 E♭major로 바꾸면 시작 셀에 E♭/G/B♭이 모두 있고 B♭은 구성음이다. 해당 선택에서 계류 설명이 비활성화된다. 뒤 구간 전체를 E♭major 정답으로 선언한 것은 아니다.
- 실제 최저음 E♭4와 B♭4의5도/7반음 및 A4 onset의 C4와6도/9반음은 그대로 보인다. 화성 판단과 관찰 근거를 혼합하지 않는다.

[전체 악보 검토](http://127.0.0.1:8821/real-cases/reviewm_555ff701230fc0b8ee66/whole-score.html?sample=16). 서버가 실행 중일 때 동작한다. 기본 Dmajor 조합은 반례 위험 설명용이지 추천 분석이 아니다.

## 검증과 재현

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m unittest discover -s tests -p test_harmony_boundary_assessment.py
.venv/Scripts/python.exe -m musicanote_harness.harmony_boundary_assessment_trial --source output/harmony-boundary-observations-2026-09-30-r2 --output output/harmony-boundary-assessment-2026-09-30-r2
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -m http.server 8821 --bind 127.0.0.1 --directory output/harmony-boundary-assessment-2026-09-30-r2
```

출력이 이미 있으면 덮어쓰지 말고 새 실행 디렉터리를 지정한다.

- 신규16개/전체1,565개 테스트 통과(22.336초). 기존 Verovio encoded-break 경고1건, 실패0.
- 합성 검증: 분산 출현/생략 구별, 미정 pitch, enharmonic 철자, 반복음 첫 관측, 보류/경쟁 reading, 기존 JSON 보존, evidence 누락, 다른 NCT 미변경, 분모 위치를 강세로 오인하지 않기.
- 실제184표본 재실행 및 원필드/hash 불변. r1/r2 표본과 report 동일 비교.
- 브라우저: 기본 Dmajor의 F♯ 미관측·보류 이유 표시, E♭major 전환 시 전 구성음 시작 관측과 계류 설명 비활성화, 기본 선택 복원, 전체 악보/패널 배치 확인.
- `git diff --check` 통과(기존 CRLF 변환 안내만 있음). 공개 push 안 함.

## 결정과 다음 단계

실험 증거/보류 계층으로 유지한다. **음악적 양성 검증과 최종 선택은 아직 미완료**이며 기존 설명량을 보류 후 정확도라고 재해석하지 않는다. 다음은 지연 구성음이 실제 같은 화음을 펼친 것인지, 중간에 다른 화음으로 바뀐 것인지 구별하는 시간적 일관성/베이스·성부 문맥 검사다. 계류음 조건을 검증할 때도 구조적 베이스와 박절 추정의 불확실성을 유지하고, 실제 양성·유사 반례를 함께 검증한다. 단순 미관측 개수로 후보를 제거하는 작업으로 대체하지 않는다.
