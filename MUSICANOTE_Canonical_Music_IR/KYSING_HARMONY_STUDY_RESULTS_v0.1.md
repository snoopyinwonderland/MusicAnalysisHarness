# KYSing 화성·휴지 비교 연구 v0.1

30곡의 41,412개 음악 프레임에 가사와 무관한 화성 후보를 연결했다.

| 음악적 문맥 | 프레임 수 |
|---|---:|
| 휴지 뒤 진입 + V-I 후보 | 27 |
| 연속 진입 + V-I 후보 | 734 |
| 휴지 뒤 진입 + V-I 후보 없음 | 3,911 |
| 연속 진입 + V-I 후보 없음 | 36,740 |

이 수치는 고유 프레이즈나 정확도 통계가 아니다. 같은 시점의 여러 성부가 포함된다. 이전 가사 연결 사례 수와 분모가 다르다. 특히 휴지 뒤 새 음의 화음과 휴지 직전 종결 화음은 서로 다른 시간 좌표이므로, 현재 표는 종지 검출을 검증하지 않는다.

## 구현된 후보 분석

- 각 onset의 동시 음군을 한 번만 분석한다.
- 전후 16 quarter 및 최대 전후 64 onset의 음군에서 음계 포함 비율을 계산한다.
- 24개 장단조 템플릿 중 상위 4개 후보를 보존한다. 이는 검증된 local-key 판정이 아니다.
- 후보별 I/i, V, V7 pitch-set Jaccard 일치도와 전체 구성음 포함 여부를 저장한다.
- 같은 조성 후보에서 4 quarter 이내의 이전 V/V7과 현재 I/i가 모두 완전한 음군인 경우 V-I 후보로 기록한다.
- confidence와 selected_hypothesis는 null이다. 결과는 training_eligible=false다.

## 관찰과 해석 한계

현재 조건에서 V-I 후보가 있어도 연속 진입하는 프레임이 더 많았다. 따라서 V-I를 곧바로 프레이즈 경계 라벨로 쓰는 규칙은 타당하지 않다. 다만 734개가 모두 실제 내부 종지라는 의미도 아니다. 조성 후보 오류, 비화성음, 표면적 음군 변화가 포함될 수 있다.

휴지와 화성 변화가 겹치는 27개는 우선 검토할 사례다. 이들 역시 종결 위치·선율 성부·타이 종료가 검증되기 전에는 정답으로 승격하지 않는다.

## 다음 필수 검증

1. 연구용 frame source reference를 Canonical IR의 안정 ID에 연결한다.
2. 파트별 마디 길이를 비교하고 불일치 곡을 격리한다.
3. 타이 체인을 sounding event로 병합하고 melisma 종료를 정렬한다.
4. 휴지 시작 직전, 휴지 구간, 다음 attack의 화성을 각각 비교한다.
5. 동일 시점 다성부를 deduplicate한 사례와 성부별 사례를 구분한다.
6. 모든 조성 후보가 부적절할 수 있도록 unknown을 허용하고, I/V 외의 화음 어휘와 bass/voice-leading을 추가한다.
7. 악보에서 사례를 검토한 뒤 규칙·가중치 보정을 진행한다.

## 실행

```powershell
$env:PYTHONPATH='src'
& '.\.venv\Scripts\python.exe' -m musicanote_harness.kysing_harmony_study output\kysing-study output\kysing-harmony-study
```

코드: `src/musicanote_harness/kysing_harmony_study.py`. 곡별 가설·비교 사례와 report.json은 `output/kysing-harmony-study/`에 생성한다. 테스트 7개가 통과했다. 새 테스트는 불완전 단음의 과잉 판정 방지와 가사 필드 변경 불변성을 검사한다. 프레이즈 예측 정확도는 아직 평가하지 않았다.
