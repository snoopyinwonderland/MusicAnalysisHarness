# 화음 유지·교체 평가 전 참조 범위 검사

HARM-DEV-20260930-08 · `reference-boundary-diagnostic-0.1.0`.

## 결론

기존 고정184표본의 지속음 내부117경계를 원주석과 연결했다. **현 유지1화음/분할2화음 계약으로 수치 비교 가능한 경계는0개였다. 정답률0%가 아니다.**

- 105개: 선택한 경계의 왼쪽 또는 오른쪽 구간 안에서 이미 주석이 변한다. 전체 범위에 한 화음 또는 두 화음만 적용하는 가정으로 해당 주석 진행을 재현할 수 없다. 한 번의 변화라도 선택 경계와 위치가 다르면 이 항목에 포함한다.
- 12개: 주석상 유지이지만 모두 `pedal`이 있다. 기존 엄격한 참조 구성음 변환기에서 페달을 지원하지 않으므로 강제로 지우거나 일반 화음으로 변환하지 않았다.
- Beethoven 02-3은 이번117개 추가 경계 집합에 경계0개. Mozart K281-3은65개 모두 한쪽 내부 변화, K280-1은52개 중40개 한쪽 내부 변화/12개 페달이다.

따라서 이전 단계2,194건 불변성 통과를 실제 화음 유지/교체 탐지 성능으로 확대 해석할 수 없다. 이번에 독립 양성·반례 평가를 **완료한 것이 아니라 평가 적합성을 검사하여 공백을 발견**했다. 데이터 부족 전체나 교재 페달 이론 미구현 전체를 의미하지 않고 이 참조 변환기/실험 계약의 제한이다.

## 검사 규칙과 데이터 분리

1. 기존 표본·경계·후보를 고정하고 주석은 사후 진단 모듈에만 입력한다. 주석으로 analyzer 후보/경계를 다시 생성하지 않는다.
2. 원MusicXML/주석파일 hash, 패키지 revision, 단일 `exact` 또는 `verified_transform` alignment와 span 일치를 확인한다. 각 원주석의 provenance를 그대로 보존한다.
3. 구/신 IR의 sequential index, 유리수 시작/실제 길이/명목 길이/박자가 같은지 검사한다. printed number 변경은 별도로 기록한다. 구 IR 음표/sounding ID를 신 IR에 옮겨 붙이지 않고 공통 시간축 span만 사용한다.
4. `[start,end)` 모든 하위 시간 셀을 덮는 주석이 정확히 하나여야 한다. 공백·겹침·미검증 주석은 건너뛰어 연결하지 않는다.
5. 각 비교 측 내부의 key/numeral/form/figbass/quality/변형/secondary/pedal/special이 일정해야 한다. 같은 label의 연속 record는 같은 의미라면 유지로 볼 수 있다.
6. 구성음 변화와 같은 구성음의 전위/기능 변화는 분리한다. 구성음 일치 검사는 전위 또는 로마자 기능 정확도를 측정하지 않는다.
7. 지원하는 참조의 구성음과 일치하는 기존 후보 존재 여부를 기록하고 대표 min/max 연결 가정에서 공통 문맥 비교를 수행할 준비를 했다. 후보 부재/참조 미지원/평가 부적합은 각각 다른 상태다. 이번 실제 표본에는 이 수치 대조까지 도달한 사례0개다.
8. 참조조건 대조의 미설명 음가 차이는 최종 점수/승자가 아니다. 결과의 `preferred`는 null이며 확정 정답·학습 자격·운영 적용은 부여하지 않는다.

## 실제 사례

K281-3 `reviewm_555ff701230fc0b8ee66` sample16, `[9,13)` quarter의 원주석은 **I6 → IV → I6 → viio6**다. 기존 실험의 ‘유지 C major / 분할 E♭ major → D major’는 후보 비교 방법을 보여 주는 예시이지 이 진행의 예측 결과가 아니다. 주석에 네 단계가 있으므로 현재1회 분할로 정답 비교하면 잘못된 평가가 된다.

K280-1의 주석 `F.I[I{`, `V43`, `I]`는 raw `pedal=I` 정보를 함께 갖는다. 화면에 V43만 보인다고 페달 정보를 없애면 안 된다. 원표기/전체 raw fields/시간 범위/source locator는 report의 `source_annotations`에 보존한다.

Beethoven 02-3에서 sequential index9의 printed number가8→X1로 바뀌지만 시작24quarter/길이1quarter/3/4박자는 같다. 이것은 시간 이동이 아니다. 모든 마디 표기 변경을 score별 `printed_number_changes`에 기록했다.

## 구현·실행·실패 기록

- `src/musicanote_harness/harmony_reference_boundary.py`: 참조 coverage, 의미 분류, 기존 후보 대조.
- `src/musicanote_harness/harmony_reference_boundary_trial.py`: hash/revision/시간축 검사, 전 고정경계 replay, 결과표.
- `tests/test_harmony_reference_boundary.py`:17개 신규 검사. 유지/교체/전위/공백/겹침/미검증/경계 외 변화/secondary·페달 미지원/반열린 범위/원자료 불변 등.
- 입력: `output/harmony-shared-context-2026-09-30-r1/`.
- 최종 출력: `output/harmony-reference-boundary-2026-09-30-r5/`의 `run-contract.json`, `report.json`, `index.html`.
- r1: digest에 문자열을 전달한 실행 오류. Path 변환 후 수정.
- r2: printed number까지 시간축 동일성으로 요구하여8→X1에 중단. 실제 시간축과 표시 번호 변경을 분리하고 회귀 검사 추가.
- r3/r4: 계산 완료. r4에는 페달 제외 이유 및 원주석 전체를 추가. r5는 같은 수치에 한국어 상태·Campania 화음 표기·평가 가능0개 안내를 추가. 모든 중간 출력 보존.

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_reference_boundary_trial --source output/harmony-shared-context-2026-09-30-r1 --output output/harmony-reference-boundary-2026-09-30-r5 --review-base http://127.0.0.1:8824
.venv/Scripts/python.exe -m unittest discover -s tests
```

재실행은 미존재 출력 경로로 한다. 전체1,624개 Python 테스트 통과. r5의 표시 변경 후 replay도 동일 수치로 완료. 기존 분석 입력·주석 패키지 hash는 실행 전후 동일. 원주석은 scorer에만 공개하며 자료는 train/internal research이고 독립 held-out 검증이 아니다.

## 화면과 다음 개발 순서

[진단 목록](http://127.0.0.1:8825/index.html). 원주석 진행과 제외 이유를 나란히 보고 각 표본의 전체 악보로 이동한다. 기존 악보의 후보 선택을 원주석으로 자동 변경하지 않는다. 링크는 sample만 지정하므로 특정 경계/화음을 자동 선택한다고 오해하지 말아야 한다. Campania는 화음 문자열에만 사용한다. 로컬 서버8824/8825 필요.

다음 우선순위:

1. 관찰 문맥과 화음을 부여하는 판단 구간을 분리한다. 앞뒤 장식/성부 진행은 넓은 문맥에서 보되 하나의 화음이 유지된다고 가정하는 구간은 별도로 둔다.
2. 주석이 아닌 실제 attack/release와 박절로 다중 경계 후보 격자를 먼저 고정한다. 각 구간 후보를 연결한 여러 화음의 진행과 전체 유지 가정을 비교한다. 기존 frozen 사례는 버리지 않고 새 계획/version으로 병행한다.
3. 화음 구성음과 페달음 역할을 별도 모델로 참조 변환하고 실제 지속/재타격 근거를 검사한다. 페달을 구성음으로 일괄 흡수하거나 제거하지 않는다.
4. 새 결과를 고정한 뒤 주석과 연결하여 유지/교체/전위 변화/페달/미지원별 coverage를 보고한다. 이후 양성·반례를 검수하고 독립 작품군 평가로 확대한다.

현재 사용자에게117개를 일일이 판정하도록 요청할 단계는 아니다. 먼저 비교 계약을 실제 진행에 맞춰 확장한다. Core/운영5173/구조 분석/최종 후보 선택은 이번에 변경하지 않았다.
