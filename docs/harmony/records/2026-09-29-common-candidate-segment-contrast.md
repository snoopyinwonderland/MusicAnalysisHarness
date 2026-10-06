# 공통 화음 후보의 유지·분할 비교

기록 ID: HARM-DEV-20260929-02. 상태: 연구용 구현/실제 고정 표본 검사/전체 악보 표시. 운영 적용·정답률 검증은 아님.

## 문제와 목표

직전 연속 음형 검사는 관찰 구간 내에 한 화음이 유지된다고 가정했다. 경과/보조 형태가 설명돼도 그 화음이 실제 정답인지, 중간에서 다른 화음으로 바뀌는지 비교할 수 없었다. 이번 단계는 **같은 악보 음표·음가·성부 연결을 고정하고 유지/분할 양쪽의 설명을 비교**한다.

기존 `harmony_hold_change_contrast`는 이전 strict change gate의 후보에 한정됐다. 이번 모듈은 그 모듈을 대체하거나 판정 기준을 바꾸지 않고, 같은 음표/시간 보존 원칙을 공통 후보 카탈로그와 복수 성부 경로에 적용한다. 원주석이나 특정 작품/마디 규칙을 입력하지 않는다.

## 일반 규칙과 데이터 계약

1. 기존 연속 음형의 label-blind `plan.json` 184표본을 그대로 재사용한다. 각 sample이 계획과 동일한지 검사하고, 원본·IR hash·train split·내부 사용 권한을 확인한다.
2. 기존 단계에서 보류된 34표본은 그대로 보류한다. 통과한 150표본에서 연속3개 attack 음군의 두 번째와 세 번째 onset을 각각 **분할 가정**으로 사용한다. 300가정이며, 탐지된 화음 경계300개가 아니다.
3. 유지 후보는 전체 구간 카탈로그, 분할 후보는 앞/뒤 구간 카탈로그에서 생성한다. 모든 provider/철자 대안을 보존한다. 구간에 철자 대안이 없으면 `no_spelled_comparison`으로 보류한다. 후보가 아예 없는 것과 구별한다.
4. 후보 생성에는 전체 part가 참여한다. 음가 비교도 전체 part의 실제 sounding events에 대해 수행한다. 조건부 경과/보조 설명만 해당 표본의 명시적 part/voice로 제한한다. 이전 단계의 lane 음가와 이번 전체 score 음가를 혼동하지 않는다.
5. 모든 실제 onset/release와 가정 경계를 합친 동일 유리수 시간 셀을 양쪽에 사용한다. 경계에 걸린 지속음은 양쪽 셀로 나눠 계산하되 원 sound ID/onset/release는 그대로이며 전체 음가를 중복 계산하지 않는다.
6. 전체 관찰 범위에서 만든 **동일 성부 연결 assignment**를 양쪽에 사용한다. 앞/뒤에 유리한 연결을 따로 골라 조합하지 않는다. 무연결 대안도 보존한다.
7. `member`, `conditional_nonmember`, `unexplained_nonmember`, `spelling_unresolved`의 음가와 음표별 변화를 따로 저장한다. 조건부 NCT는 비구성음 내부의 설명 상태이며 삭제/확정 NCT/구성음 가산이 아니다.
8. 기존 후보 조건의 grace/철자/문맥 보류는 유지한다. 보류된 조건은 NCT 설명을 제공하지 않으며 후보 전제의 구성음 대조만 남긴다.
9. 각 side의 `철자 대안 수 × 전체 성부 조합 수 > 20,000`이면 pruning 없이 보류한다. 이번 실제 자료에서는 이 상한으로 추가 보류된 것은 없다.
10. 유지×앞×뒤×assignment의 전체 조합은 각각의 요소를 빠짐없이 저장하고 필요할 때 계산한다. 기본 표시를 위한 한 조합은 추천/우승 후보가 아니다. 가능한 조합 수를 실제 평가 건수로 보고하지 않는다.
11. 앞/뒤 철자 구성음 집합이 같다면 그 사실을 표시한다. 구간 분할 자체가 근음/품질/기능 변화의 증거는 아니다.

## 중요한 발견: 경계에 따른 NCT 설명의 비대칭

연속3음 설명은 세 음 전체가 같은 candidate scope에 들어와야 한다. 따라서 **동일 화음이라도 범위만 둘로 나누면 경계를 가로지르는 경과/보조 설명이 사라질 수 있다.** 이를 분할 오류나 유지 가정의 우세로 채점해서는 안 된다.

현재는 이 차이를 드러내고 한계로 명시한다. 서로 다른 화음 아래의 선행음/계류·경과·공통음 설명을 임의로 만들어 내지 않았다. 양쪽에서 문맥 길이가 같더라도 NCT 모델의 설명 가능 범위가 동일한 것은 아니다. `preferred=null`, `probability=null`, `harmonic_change_confirmed=false`를 유지한다.

## 실제 실행 결과

최종 출력: `output/harmony-segment-contrast-2026-09-29-r3/`.

| 악장 | 원표본 | 기존 보류 | 분할 가정 | 철자 대조 가능 | 철자 대안 부족 보류 | Python 미리보기 대조 |
|---|---:|---:|---:|---:|---:|---:|
| Beethoven Sonata 2 III | 43 | 0 | 86 | 30 | 56 | 21 |
| Mozart K281 III | 67 | 13 | 108 | 93 | 15 | 54 |
| Mozart K280 I | 74 | 21 | 106 | 82 | 24 | 45 |
| 합계 | 184 | 34 | 300 | 205 | 95 | 120 |

`ready` 표본150개는 입력 검사를 통과했다는 뜻이며, 모든 경계/후보가 비교 가능하다는 뜻이 아니다. 구간별 카탈로그에서 생성한 철자 조건8,365개 중918개는 조건부 설명이 보류됐다. 조건 보류와 경계의 철자 대안 부재는 서로 다른 수치다.

표본·분할 가정은 중첩된 train 사례다. 이 수치들은 정확도·화음 교체 검출 수가 아니다. 전체 조합을 점수화/학습하거나 최적 화성 경로를 선택하지 않았다. 기존 원표본184파일의 실행 전후 hash와 선정 계획 hash는 그대로다.

## 실제 사례 — K281 III

`reviewm_555ff701230fc0b8ee66`, sample15. printed measure2 +3quarter부터 measure3 +1quarter까지, 분할 가정은 measure3 +0quarter. 전 성부 note-time은6quarter, 경과음 관찰 lane의 note-time은2quarter다.

| 전제 | 구성음 음가 | 조건부 비구성음 설명 | 미설명 비구성음 | 철자 미정 |
|---|---:|---:|---:|---:|
| E♭ major 유지 | 9/2 | 1/2 | 1 | 0 |
| B♭ major → E♭ major 분할 | 11/2 | 0 | 1/2 | 0 |

- D4의 `[9,10)` quarter는 유지에서 미설명 비구성음, 분할의 앞 화음에서는 구성음이다.
- A5의 `[10,21/2)` quarter는 유지에서 B♭5–A5–G5의 조건부 경과음, 분할에서는 경계를 넘는 3음 설명 미지원으로 미설명 상태다.
- 두 해석 모두6quarter의 동일한 음표·음가를 설명한다. 설명 차이는 경쟁 가설이지 정답 판정이 아니다.
- 처음 표시되는 성부 연결은 해당 형태가 가능한 첫 조합이며 최적성/확률을 뜻하지 않는다. 드롭다운에서 무연결 대안도 볼 수 있다.
- UI는 원음표 위에 비교 라벨, 청록 관찰 범위, 주황 분할 가정 점선, 설명이 달라진 음의 보라색 표시를 제공한다. 일부 음가만 달라진 sound도 음표 전체를 칠할 수 있음을 화면에 알린다.
- local key가 미확정이므로 로마자 기능을 지어내지 않고 root/quality를 일반 글꼴로 표시한다. Campania 로마자 출력의 기존 정책을 변경하지 않는다.

이 기본 조합은 관찰 편의를 위한 사후 선택이다. 사용자가 음악적 판단을 승인한 사례로 저장하지 않는다.

## 코드·검증·실행 이력

- `src/musicanote_harness/harmony_segment_contrast.py`: grid, 전체 part membership, 동일 assignment profile, factorized build, 임의 조합 compare.
- `src/musicanote_harness/harmony_segment_contrast_trial.py`: 원계획 재사용/동일성 검사, 전체 표본 실행, hash 대조, 전체 악보 생성.
- `src/musicanote_harness/visual_review_assets/segment_contrast.js`: 선택 조합의 유리수 BigInt 계산과 음표 표시. float로 음가를 누적하지 않는다.
- `tests/test_harmony_segment_contrast.py`:13개. 고정 boundary·주석 독립, 전 성부 음가·지속음 보존, 동일 assignment, 같은 화음 분할/NCT 비대칭, 잘못된 partition/assignment/음표 참조 거부, 보류 조건, 예산 상한, 기존 보류 전파, 모든 요소 보존, 입력 불변, 철자 대안 부재 검사.
- 전체 Python 테스트1,499개 통과. Verovio encoded-break 경고1건, 실패 없음. 음악적 정답률 검증이 아니다.
- 최종 r3 브라우저에서 K281 전체 악보·분할 점선·D4/A5의 색칠을 확인했고, 표시된 유리수 합계가 저장된 Python 비교 결과와 일치했다. 연결2개 가정에서 유지의 조건부 NCT1/2, 무연결 가정에서는0 및 미설명3/2로 바뀌는 것을 확인했다. 음악적 검수 승인은 아니다.
- r1 계산 성공 후, 빈 철자 대안도 `boundary_ready`로 집계되는 상태 표현 문제를 확인했다. 실제 비교는 생성되지 않았지만 가용성 집계가 오해를 줄 수 있어 r2에서205가능/95보류로 구분하고 회귀 검사를 추가했다. r1은 중간 결과로 보존한다.
- r3는 원 sample/계획 일치 검증, 점선 경계와 음표별 설명 차이 UI를 추가한다. 카탈로그/비교 수치를 유리하게 바꾸지 않는다.
- 이번 작업은 기존 source snapshot IR을 사용하며 새 XML parser를 구현하거나 모든 코퍼스를 재검증한 것이 아니다. Core/원주석/기존 판정기/운영5173/구조 분석은 미변경이다. 인수인계 문서는 갱신하지 않는다.

## 재현

PowerShell, 프로젝트 루트:

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m unittest discover -s tests -q
.venv/Scripts/python.exe -m musicanote_harness.harmony_segment_contrast_trial --source output/harmony-continuous-survey-2026-09-29-r3 --output output/harmony-segment-contrast-new-run
.venv/Scripts/python.exe -m http.server 8817 --bind 127.0.0.1 --directory output/harmony-segment-contrast-2026-09-29-r3
```

출력 디렉터리는 새 이름을 쓴다. [악보 목록](http://127.0.0.1:8817/index.html), [K281 비교](http://127.0.0.1:8817/real-cases/reviewm_555ff701230fc0b8ee66/whole-score.html?sample=15). source-snapshot과 samples JSON에 앞뒤 원악보/IR/ID/조건/불확실성을 보존한다. 원자료와 출력은 로컬 연구용이며 GitHub에 업로드하지 않는다.

## 결정과 다음 단계

**채택:** 동일 음표·음가·전체 성부 연결 아래 양쪽 설명을 비교하는 연구 계약과 시각 진단.

**보류:** 최종 화음/경계 선택과 Phrase 되먹임. 미설명 음가가 줄었다는 이유만으로 분할을 선호하지 않는다.

**다음:** 경계를 넘는 NCT의 진입·이탈 문맥을 양쪽 후보에 연결하고, 화성 교체의 긍정 근거와 단순 범위 절단으로 사라진 설명을 구별한다. 이후 박절·화성 리듬·성부 해결 근거를 묶어 독립 평가한다. 후보 부족95가정도 실제 원인을 분류하되 임의의 root spelling을 채워 넣지 않는다. 비교 가능한 음악적 대안과 반대 증거가 준비될 때 사용자 검수를 요청한다.
