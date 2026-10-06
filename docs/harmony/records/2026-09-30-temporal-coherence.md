# 분산화음과 화성 교체의 시간 순서 대조

기록 ID: HARM-DEV-20260930-05 · 2026-09-30

## 목표와 적용 범위

직전 단계는 구간 전체에서 화음 구성음이 언젠가 출현하는지만 구별했다. 그러나 서로 다른 화음을 길게 합쳐도 구성음 집합이 완성될 수 있다. 이번에는 **음군의 시간 순서, 실제 최저음 흐름, 경계에서 지속하는 음, 선택한 성부 연결**을 공통 시간축에서 대조한다.

사용자의 계속 진행 승인에 따른 일반 규칙 개발이다. 특정 작품/마디 예외, 주석 정답 역주입, 새 교재 독해, 최종 화음 선택, 운영5173 적용은 하지 않았다. 이 단계는 관찰 근거 확장이며 분산화음 탐지 정확도를 입증한 단계는 아니다.

## 규칙과 데이터 계약

1. 각 후보 support profile의 정확한 `[start,end)` 셀을 시간순으로 읽는다. 구성음만/구성음과 비구성음 혼합/비구성음만/전 성부 쉼/음높이 미정으로 분류한다. 미정 음을 제외해 완전한 구성음 셀로 만들지 않는다.
2. 각 상태의 **실제 경과 시간**을 유리수로 누적한다. 성부별 음가 합인 기존 note-time과 별개이며 동음 중복으로 시간을 늘리지 않는다. 셀 누락·겹침·구간 미충족은 실패 처리한다.
3. 연속한 동일 상태를 run으로 묶되 원 cell index를 유지한다. 모든 구성음의 첫 누적 출현 시각을 기록하고, 전체 구간에 비구성음이 섞였는지 및 그 시각 전에 전 성부 쉼을 가로질렀는지 별도로 표시한다.
4. 실제 최저 MIDI pitch와 후보 membership의 시간 흐름을 기록한다. 최저음이 바뀌어도 같은 화음의 분산형일 수 있고, 최저음이 유지되어도 다른 화음일 수 있다. 이를 근음/구조적 베이스/전위 확정으로 바꾸지 않는다.
5. 앞 후보에서만 구성음인 실제 앞 구간 음과 뒤 후보에서만 구성음인 실제 뒤 구간 음을 따로 표시한다. 양쪽에 있어도 반대 해석에서 NCT일 수 있으므로 화음 교체 확정/점수가 아니다. 같은 구성음 집합의 분할은 이 증거로 구별할 수 없다.
6. 경계에서 실제 지속하는 sounding event의 앞/뒤 membership을 따로 기록한다. 같은 음표가 한쪽에서는 구성음, 다른 쪽에서는 비구성음일 수 있다.
7. 동일 전역 assignment의 경계 전후 성부 연결을 사용한다. 경계 뒤에 해결되는 경우도 실제 연결 시각과 함께 보존한다. source가 경계 이후에도 지속하면 **그 지속 부분의 역할**을 별도 필드로 기록해 member→member 요약에 숨기지 않는다. 무연결 assignment에서는 진행을 지어내지 않는다.
8. 철자/옥타브/MIDI 검증을 유지한다. 이명동음을 무조건 같은 구성음으로 만들지 않으며 기존 candidate abstention 사유를 유지한다.

화음 후보, 기존135음형과 조건부 NCT 설명량, Canonical Core와 원주석은 불변이다. 구성음만으로 이루어진 음군 역시 충분조건이 아니다(불완전한 음군, 휴지, 여러 화성 해석 가능). 비구성음은 **확인된 비화성음**을 뜻하지 않는다. 많은 비구성음이 자동 분할을 정당화하지 않는다.

## 구현

- `src/musicanote_harness/harmony_temporal_coherence.py`: `temporal-coherence-0.1.0`, profile_support/compare/augment.
- 별도 boundary `temporal_coherence`, top-level version 및 기본 선택의 `temporal_coherence_preview`만 추가한다. 후보 profile을 요소별로 저장하며 모든 조합을 펼치지 않는다.
- `harmony_temporal_coherence_trial.py`: 고정된184표본/117경계 재계산.
- 기존 `harmony_boundary_assessment_trial.run`에 선택적 stage를 추가하여 권한·원자료 hash·원계획·원필드 불변 검사를 재사용한다. 인자 생략 시 이전 단계의 동작을 유지한다. 이번 실제 실행은 새 stage 경로이며 이전 stage 전체 재실행은 하지 않았다.
- `visual_review_assets/segment_contrast.js`: 선택한 후보/성부 연결에 맞춰 시간순 run, 실제 최저음 흐름, 구별 구성음, 지속음 역할, 성부 진행을 표시한다. 기존 전체 악보 표시를 유지한다.

## 실행 및 결과

입력 `output/harmony-boundary-assessment-2026-09-30-r2/`.
출력 `output/harmony-temporal-coherence-2026-09-30-r2/`.

r1은 보존했다. r2에는 지속 source의 경계 이후 역할 필드와 실제 최저음 시간 흐름 UI를 추가했다. 두 실행의 통계는 같으나 preview JSON/코드/UI는 다르므로 완전 동일 출력으로 주장하지 않는다.

| 고정 검사 범위 | 표본 | 경계 | profile | 누적 구성음 완성 | 완성+비구성음 동반 | 울리는 음이 모두 구성음 |
|---|---:|---:|---:|---:|---:|---:|
| Beethoven 02-3 | 43 | 0 | 0 | 0 | 0 | 0 |
| Mozart K281-3 | 67 | 65 | 7,786 | 1,682 | 1,613 | 205 |
| Mozart K280-1 | 74 | 52 | 6,309 | 1,262 | 1,171 | 217 |
| 합계 | 184 | 117 | 14,095 | 2,944 | 2,784 | 422 |

서로 겹치는 후보/범위의 관측 수이며 실제 화음 수·정답 수·정확도가 아니다. 마지막 열에는 구성음이 일부만 관측된 후보도 있으므로 다른 두 열과 상호 배타적 분류가 아니다. 이번 범위의 구성음 완성 이전 전 성부 쉼 횡단은0개(합성 검사로는 검증). 베토벤0은 고정 범위에 추가 지속음 경계가 없다는 뜻이며 악장 전체의 부재가 아니다.

train/internal_research 권한과 source snapshot hash, 원계획/추가계획 hash, 기존184표본의 실행 전후 hash를 검증했다. 새 필드를 제거하면 이전 JSON과 완전히 같음을 모든 표본에서 검사했다. run-contract에는 원 report/코드/UI hash가 있다. 기존 counterfactual-checks는 이전 검사 기록으로 보존했고 이번 재실행 결과라고 주장하지 않는다.

## 실제 악보 사례

K281-3, `reviewm_555ff701230fc0b8ee66`, sample16, global `[9,13)`, boundary `21/2` (표기3마디+1/2quarter). 원본·IR은 해당 출력의 `source-snapshot`, hash는 report/run-contract에 있다.

- 기본 분할 뒤 Dmajor: `[21/2,11)`은 비구성음만, `[11,13)`은 구성음+비구성음. 실제 최저음은 E♭4→D4→C4. F♯은 여전히 미관측이다.
- 분할 뒤 E♭major로 바꾸면 `[21/2,11)`은 구성음만, `[11,12)` 혼합, `[12,25/2)` 비구성음만, `[25/2,13)` 혼합이다. 시작에는 E♭/G/B♭이 모두 있어도 **뒤 전체를 한 E♭ 화음으로 확정할 수 없는 이유**가 드러난다. 비구성음 구간이 곧 화성 교체의 정답이라는 뜻은 아니다.
- B♭4 `sound_0b9d0a329fff` (`note_4d67992530b4`) → A4 `sound_82e6cfa6216c` (`note_24b72caac4b0`) 연결은 global12에 발생한다. 기본 E♭→D 가정에서 B♭은 경계 전에 구성음이지만 경계 뒤 지속 부분은 비구성음이다. 이 중간 상태를 누락하지 않는다.
- 무연결 assignment를 선택하면 같은 화음 후보를 유지하더라도 성부 진행은 '연결 근거 없음'으로 바뀐다.

[전체 악보 검토](http://127.0.0.1:8822/real-cases/reviewm_555ff701230fc0b8ee66/whole-score.html?sample=16). 기본 선택은 반례 위험 검토용이며 추천 화성 분석이 아니다. 로컬 서버 실행 필요.

## 검증·재현

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m unittest discover -s tests -p test_harmony_temporal_coherence.py
.venv/Scripts/python.exe -m musicanote_harness.harmony_temporal_coherence_trial --source output/harmony-boundary-assessment-2026-09-30-r2 --output output/harmony-temporal-coherence-2026-09-30-r2
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -m http.server 8822 --bind 127.0.0.1 --directory output/harmony-temporal-coherence-2026-09-30-r2
```

기존 출력 디렉터리는 덮어쓰지 않으며 재실행 때 새 이름을 지정한다.

- 신규20/전체1,585테스트 통과(23.712초). 기존 Verovio encoded-break 경고1건, 실패0.
- 순수 분산형, 중간 비구성음, 전 성부 쉼, 셋잇단음표, 중복음, 혼합 다성부, 실제 최저음 이동, 미정 pitch, 같은 구성음 집합, 양쪽 고유 구성음, 지속 공통음, 무연결, 잘못된 assignment/시간 분할, 이명동음, 기존 결과·보류 보존 검사.
- 브라우저: 기본 선택의 시간 값과 Python 결과 대조, E♭ 전환 시 시간순 상태 변경, 무연결 시 진행 없음, 기본 복원, 전체 악보+패널 screenshot 검증.
- `git diff --check` 통과(기존 CRLF 안내). 운영 코드·원자료·주석·구조 분석 미변경. GitHub push 없음.

## 결정과 다음 단계

실험 근거 계층으로 유지한다. 아직 '같은 화음'과 '화음 교체'의 자동 최종 판정기가 완성된 것은 아니다. 다음은 혼합 구간을 기존 **조건부 NCT 설명과 동일 시간 셀에서 연결**하여, 단순한 분산형+장식과 실제 다른 화음을 경쟁 가설로 검증하는 것이다. 원주석과 사용자 의견은 독립 비교 대상으로 유지하고, 양성·반례를 함께 확인하기 전 임의 가중치/과도한 병합·분할 규칙을 운영에 적용하지 않는다.
