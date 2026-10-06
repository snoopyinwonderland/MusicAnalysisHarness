# 생략 화음 가설과 실제 성부 움직임의 대조

HARM-DEV-20260930-22 · 2026-09-30 · `omission-voice-context-0.1.0`

## 목적과 이번 결정

앞 단계의5음 생략 가설이 계산 가능해졌다는 사실을 화성 정답으로 승격하지 않고, 실제 음표 연결이 그 진행을 지지하는지 검사한다. 특정 작품·음높이·마디 번호에 대한 예외는 없다.

결과는 **화음 형태의 가능성과 실제 성부 해결이 다를 수 있음**을 보여 준다. 기존 K280 표본의 E–G–B♭ → F–A–C–E♭ 후보에는 E→F 이끎음 해결을 지지하는 경로가 없다. 실제 위 성부는 F5→E5→E♭5다. 이는 좁은 일반 해결 모델의 근거 부족이며, 해당 음악이나 다른 화성 해석의 기각이 아니다.

## 일반 규칙과 데이터 계약

1. 원 IR의 전체 문맥 event IDs/pitch/span/source-note 일치를 검사한 뒤, 모든 관련 sound의 명시적 part/voice를 사용한다. 같은 XML voice가 실제 대위 성부라는 확정은 하지 않는다.
2. 연결 graph는 화음 라벨 없이 생성한다. 같은 part/voice의 정확히 닿는 sound만 연결 후보로 둔다. 쉼·다른 성부·옥타브 치환으로 빈 연결을 보충하지 않는다. 같은 voice의 cross-staff 이동을 staff 차이만으로 차단하지 않는다.
3. 경계를 통과하는 한 sound는 `held_sound` 한 개로 보존한다. 자기 자신으로 연결하는 graph edge나 새로운 attack을 만들지 않는다. 경계에서 새로 시작하는 음과 구별한다.
4. 보조음형 복귀는 실제 같은 옥타브/철자 음에서 순차 진행한 뒤 같은 음으로 돌아오는 관찰 경로다. 중간 동음 재타격은 보존한다. 기보상2도와 실제1/2반음의 방향도 같아야 한다. 이 모양만으로 NCT를 확정하지 않는다.
5. 각 복귀 경로가 반복 최저음의 연결과 함께 가능한지 검사한다. 서로 다른 경로의 출발음/도착음 공유로 분기·병합이 생기면 동시에 선택할 수 없다. 상충 경로도 삭제하지 않고 상태와 원음표 refs를 보존한다.
6. 반복 최저음 연결은 공동 대응의 제약일 뿐이다. `carried_event_refs=[]`로 전달해 비구성음 설명량을 충족시키지 않는다. 이 단계는 페달·구조적 베이스·NCT 면제를 하지 않는다.
7. 모든 adjacent interval reading 쌍의 ordinary V/V7/vii/vii7/vii_half7 형태 관계를 검사한다. 목표 장/단3화음의 근음/3음은 실제 관측되어야 한다. 이끎음의 상행 반음,7음의 하행2도는 실제 동일 lane의 닿는/동음 지속 경로로 검사한다. 생략 가정의 음표를 endpoint로 만들지 않는다.
8. 조건부 세 구간 조합에서는 양쪽 경계의 필수 연결과 반복 베이스 연결을 **한 공동 부분 대응**에서 검사한다. 각 경계의 서로 다른 witness를 무조건 합치지 않는다. 성공도 `critical_motion_matching_possible`일 뿐 전체 성부·화음 기능의 증명이 아니다.
9. 앞 단계의 strict status, missing members, omission 조건부 그룹, 전체 한 화음 대안, 관측상 같은 증·7화음 경쟁 후보를 모두 보존한다. 생략 모델 미지원이 곧 경쟁 후보의 탈락은 아니다.
10. edge/path/query/조합 및 복귀 경로 쌍 검사에는 한도가 있다. 초과는 명시적 보류이며, 일부 성공만 남겨 전체 검사처럼 보고하지 않는다. graph·복귀 경로·critical path의 한도 초과에서는 해당 부분 목록을 비운다.

`neighbor_return_geometry`는 contour와 대응의 관찰이고, `neighbor_roles`는 주어진 reading 아래의 membership이다. 원형이 보조음처럼 보여도 가운데 음이 해당 화음의 구성음이면 NCT로 면제하지 않는다. 하위 solver의 `temporal_resolution_possible` 상태는 이 contour 질의에서는 **부분 대응이 가능하다는 뜻만** 갖는다. 화성 해결·정답·선택 확률이 아니다.

## 구현

- `src/musicanote_harness/harmony_omission_voice_context.py`: geometry, held/touching 움직임, 순차 복귀 경로, 강제 베이스/경로 동시 가능성, 모든 reading 쌍의 형태·실제 이끎음/7음 경로, 조건부 공동 질의.
- `harmony_missing_evidence_trial.py`: 선택적 `--omission-voice-context`. 기존 audit flags와 동시에 선택할 수 없다. 고정 입력/계획/IR hash, 내부 연구 권한, 실행 전후 무변경 검사를 재사용한다.
- `tests/test_harmony_omission_voice_context.py`: 양성·반례·예산 보류·원입력/strict 결과 보존·JSON 재현 검사를 별도 관리한다.

Core/원주석/기존 strict gate/운영5173/구조 분석/8822악보 화면은 변경하지 않았다. 외부 AI/API/학습/GitHub 업로드 없음.

## 코드 검증

신규 집중 검사 **25개**, 전체 Python **1,804개** 통과(전체23.656초). 이 수치는 음악적 정답률이 아니다.

- 하/상 복귀와 동음 재타격, 두 A3 경로의 분기·병합 충돌, 반복 베이스를 빌린 경로의 충돌.
- 실제 leading-tone/7음 해결 양성, E→E♭ 반례, 미관측 음표 endpoint 금지, 쉼/다른 lane/옥타브/이명동음 방향 충돌 반례.
- held sound 한 개 보존과 가짜 self-link 금지, edge/path/query/조합/경로 쌍 한도 보류, 원입력과 기존 strict/생략 결과 불변, 잘못된 IR 거부.
- JSON 직렬화 및 순환 witness 재발 방지, 전체 화성/페달/NCT 면제 없음.

최종13개 출력 artifact와 실행 code hashes를 다시 검사했다. `git diff --check` 통과. 기존 파일의 LF→CRLF 안내와 기존 layout warning은 별도이며 이번 테스트 실패는 없다.

## 고정 실험 결과

최종 출력: `output/harmony-omission-voice-context-2026-09-30-r3/`.

기존13표본에서 baseline1개/관계 예산1개 보류를 유지했다. 반복 최저음 chain2개, 기존 두-cut 분할13개를 보존했다.

| 검사 | 결과 | 해석 |
|---|---|---|
| 조건부 세 구간 비교 |1개 검사/12개 적격 조합 없음 | 기존 생략 가설 적격 범위 유지 |
| 적격 조합의 critical motion | 공동 witness0개 | E→F 연결을 실제로 찾지 못함 |
| contour 경로 instances |11개 | 중복 분할과 베이스 충돌 후보 포함; 고유 음악 사례 수 아님 |
| 반복 베이스와 양립 가능한 contour instances |2개 | 같은 분할의 서로 경쟁하는 A3 복귀 경로 |
| 베이스와 충돌하는 contour instances |9개 | 가능한 graph 이동과 공동 대응을 구별 |

K280 sample16의 두 경계 quarter7/8, 원음 관찰:

| 구간 | 반복 최저음 이외 실제 음 | 앞 단계 후보 |
|---|---|---|
| `[6,7)` | A3 재타격, F5 | F–A–C, C 생략 가정 |
| `[7,8)` | G3/B♭3 재타격, E5 | E–G–B♭, F3는 비구성음으로 남음 |
| `[8,9)` | A3/C4 재타격, E♭5 | F–A–C–E♭ |

검사한 conditional reading indices는 `[0,1,7]`이다. source candidate `open_f3472963da7433c519f9`에서 target `open_31dc01b350c5d95a245f`의 F-major core로 가는 vii 형태는 있지만, `sound_cdeb09f45e28`(E5)→`sound_5962650bce09`(E♭5)는 diatonic0/semitone−1이다. 기대한 E→F 상행 반음과 다르다. 실제 출발·도착음을 보존하고 critical path를 빈 목록으로 기록했다.

같은 경계의 lower/upper neighbor contour 대안:

- A3(`sound_198a55da794f`)→G3(`sound_e4380b54af97`)→G3(`sound_eca784c243e5`)→A3(`sound_5c9cf68de57e`).
- 같은 출발 A3→B♭3(`sound_eb767d0a591d`)→B♭3(`sound_f884b0ce301a`)→같은 도착 A3.

각각은 반복 베이스와 공동 부분 대응이 가능하나, 둘을 동시에 쓰면 같은 A3의 분기·병합이 생겨 불가능하다. F3→G3→F3 contour도 graph에는 있지만 원래 F3 반복 연결을 빼앗으므로 양립 불가로 저장했다. 조건부 화음 진행에서는 G/B♭도 구성음이므로 두 A3 contour에 NCT 라벨을 붙이지 않았다.

원 IR: `output/harmony-shared-context-2026-09-30-r1/real-cases/reviewm_6fb07c245142d9e0421f/source-snapshot/candidate_revision_ir.json`. 검사 결과에는 원 sound refs와 유리수 시간이 남아 있다.

## 개발 중 발견과 수정

- 독립 검토에서 E♯→F♭처럼 diatonic 방향과 실제 pitch 방향이 반대인 경우를 확인했다. ordinary neighbor 조건에 두 방향 일치를 추가했다. 특정 pitch 예외가 아니다.
- r1은 initial motion/contour 진단 출력이다. 강제 베이스와 contour 공동 질의를 추가한 r2는 자기 option을 witness로 저장하여 JSON circular reference로 중단됐다. 순수 links/빈 coverage의 별도 constraint 객체를 생성하도록 수정했고 r3 전체 실행은 성공했다. r1/r2 출력은 삭제하지 않았다.
- 단일 held 음표용 테스트 fixture는 기존 공통 fixture가 필요로 하는 quarter1 grid point가 없어 실패했다. held 음표를 변경하는 대신 독립 lane의 짧은 음으로 grid를 제공해 검사 의도를 유지한다.

## 재현

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_missing_evidence_trial --source output/harmony-distributed-resolution-2026-09-30-r1 --ir-source output/harmony-shared-context-2026-09-30-r1 --output output/harmony-omission-voice-context-2026-09-30-replay --omission-voice-context
.venv/Scripts/python.exe -m unittest discover -s tests -p test_harmony_omission_voice_context.py -v
.venv/Scripts/python.exe -m unittest discover -s tests -q
```

출력에는 아직 생성하지 않은 폴더 이름을 사용한다. 고정 원자료의 hash 불일치는 거부한다.

## 남은 작업과 다음 순서

전체 한 화음/복수 화음 후보 중 어느 것이 시간 안의 각 음을 설명할 수 있는지, 원음을 삭제하지 않고 공동 assignment로 비교한다. 이어서 다성 비화성음·반음계 진행·반복 저음의 역할을 검사한다. E→F가 없다는 이유만으로 다른 답을 자동 선택하지 않는다.

실험 정답률·최적 경계·조성/기능/종지·전체 성부 확정은 미완료다. 위 결과를 최종 화성 표시로 운영 viewer에 반영하지 않는다. 실제 여러 후보를 같은 전체 악보에 제시하는 단계에서 사용자의 판단이 필요한 모호한 지점을 명시한다.
