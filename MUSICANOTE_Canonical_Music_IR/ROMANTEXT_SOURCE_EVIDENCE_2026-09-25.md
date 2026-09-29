# RomanText 원자료 화성–악보 증거 비교기 — 2026-09-25

## 목적

정확한 시간 좌표에 붙은 RomanText 주석도 음악적으로 옳다고 자동 승인하지 않는다. 별도의 scorer가 주석이 주장하는 `key + Roman numeral`의 pitch-class template과 해당 `[start,end)` 구간의 실제 sounding event를 비교한다. 이 결과는 원자료 선별과 검토 우선순위에 쓰는 **호환 증거**이며 화성 정답, 보정된 confidence, human validation, training eligibility가 아니다.

source label은 scorer만 읽는다. Canonical Core나 blind analyzer에 다시 주입하지 않으므로 독립 분석 평가에서 label leakage를 막는다.

## 구현

- 코드: `src/musicanote_harness/romantext_evidence.py`
- 스키마: `schemas/romantext_source_evidence.schema.json`
- 곡별 산출물: `source_harmony_evidence.json`
- engine version: `romantext-source-evidence-0.1.1`

각 exact annotation에 대해 다음 증거를 계산한다.

1. Roman numeral과 조성에서 기대되는 pitch class
2. 구간에서 실제로 출현한 기대 구성음의 비율
3. 전체 sounding-duration weight 중 기대 구성음이 차지하는 비율
4. 새 attack만 따로 본 기대 구성음의 음가 비율
5. 구간 시작의 실제 최저음과 Roman numeral 전위가 기대하는 bass의 일치
6. 기대 구성음 누락과 외부 pitch class

외부 pitch class는 곧 오류가 아니다. 경과음, 보조음, 전타음, 계류음, 페달, 장식음이거나 source label의 불일치일 수 있으므로 진단 이름도 `possible_nct_or_label_mismatch`로 둔다.

## support band

| band | 휴리스틱 조건 | 의미 |
|---|---|---|
| `strong_support` | 기대음 출현 ≥ 75%, 구성음 음가 ≥ 70%, 시작 bass가 명시적으로 불일치하지 않음 | 표면 악보가 원자료 label을 강하게 지지 |
| `moderate_support` | 기대음 출현 ≥ 2/3, 구성음 음가 ≥ 55% | 누락·NCT가 있어도 상당한 지지 |
| `mixed_evidence` | 기대음 출현 ≥ 50% 또는 구성음 음가 ≥ 40% | 지지와 반대 증거가 함께 있음 |
| `weak_evidence` | 위 조건 미달 | 검토 우선순위가 높음 |
| `unscorable` | 좌표 ambiguous, Roman parse 실패, sounding evidence 없음 | 자동 판단하지 않음 |

이 임계값은 평가 자료를 통해 앞으로 조정할 heuristic이다. source label을 보면서 만든 값이므로 독립 모델 성능으로 보고하지 않는다.

## 실제 Bach 예제

평균율 1권 Prelude 1의 자동 RomanText 37개를 비교했다.

| band | 수 |
|---|---:|
| strong support | 33 |
| moderate support | 3 |
| mixed evidence | 1 |
| weak evidence | 0 |
| unscorable | 0 |

이 분포만으로 주석 정확도가 100%라고 말할 수 없다. 같은 pitch-class 집합을 갖는 기능적으로 다른 해석, 국소 조성 오류, 전위·지속·NCT 해석 오류는 표면 호환만으로 분리되지 않을 수 있다.

## UI

곡별 검토 화면의 화성 항목을 누르면 `악보 호환 증거` 카드에 다음을 표시한다.

- support band
- 기대 구성음 출현률
- 전체 구간 및 attack 기준 구성음 음가 비율
- 기대·누락·외부 pitch class
- 시작 bass와 기대 bass
- 이 수치가 correctness/confidence가 아니라는 경고

## 전수 검사 결과

좌표 정렬 결과 2,029쌍 가운데 exact 좌표가 하나 이상 있는 1,902쌍을 모두 검사했다. 8-worker 재개 가능 batch로 실행했으며 오류 쌍은 0개다. 나머지 127쌍은 exact 좌표가 없어 이 단계의 대상이 아니다.

산출물은 `output/romantext-source-evidence-all-2026-09-25/`에 있다.

- `romantext_evidence_summary.json`: 전체·코퍼스별 집계
- `romantext_evidence_pair_records.jsonl`: 1,902쌍의 곡별 분포와 검토 후보
- `romantext_evidence_review_candidates.jsonl`: 곡마다 우선순위 상위 20개까지 모은 triage 표본
- `pair_cache/`: 중단 후 재개할 수 있는 곡별 cache

재실행 명령은 다음과 같다. 같은 source hash와 evidence version의 cache는 다시 분석하지 않는다.

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m musicanote_harness.cli audit-romantext-evidence `
  'output\romantext-score-alignment-all-2026-09-24\romantext_alignment_records.jsonl' `
  --output 'output\romantext-source-evidence-all-2026-09-25' --workers 8
```

| band | 이벤트 수 | scorable 149,997개 중 비율 |
|---|---:|---:|
| strong support | 104,693 | 69.80% |
| moderate support | 28,107 | 18.74% |
| mixed evidence | 12,483 | 8.32% |
| weak evidence | 4,714 | 3.14% |
| unscorable | 8,174 | 별도 집계 |

`unscorable`은 정렬 비정확 8,025개와 sounding evidence 없음 149개다. flag는 서로 배타적이지 않으며 외부음 가능성 79,444개, 시작 bass 불일치 24,091개, 기대음 누락 35,691개, 낮은 구성음 음가 비율 12,570개였다. 이 숫자는 곧 오류 수가 아니다.

코퍼스별 scorable 분포도 차이가 있었다.

| corpus | pairs | strong | moderate | mixed | weak | unscorable |
|---|---:|---:|---:|---:|---:|---:|
| OpenScore Lieder | 1,063 | 68.09% | 18.75% | 9.23% | 3.93% | 6,981 |
| When in Rome | 839 | 73.29% | 18.72% | 6.47% | 1.53% | 1,193 |

이 차이는 주석 품질만이 아니라 성부 수, 피아노·성악 텍스처, 지속음과 NCT, source annotation model의 차이일 수 있다. 따라서 코퍼스 품질 순위로 해석하지 않는다. 후보 JSONL은 곡당 20개 cap 때문에 14,444행이며 전체 mixed/weak/unscorable 모집단과 같지 않다.

## 카탈로그 연결

검색 카탈로그에 곡별 strong/moderate/mixed/weak/unscorable 수를 붙였다. 필터는 `weak 포함`, `mixed/weak 포함`, `mixed/weak 없음`을 지원한다. 전수 검사에 없던 127쌍은 `증거 전수 검사 없음`으로 명시한다.

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m musicanote_harness.cli serve-romantext-catalog `
  'output\romantext-score-alignment-all-2026-09-24\romantext_alignment_records.jsonl' `
  --evidence-records 'output\romantext-source-evidence-all-2026-09-25\romantext_evidence_pair_records.jsonl' `
  --output 'output\romantext-catalog-reviews-2026-09-25' --host 127.0.0.1 --port 8766
```

곡 기준으로 weak가 하나 이상인 곡은 811개, mixed 또는 weak가 있는 곡은 1,422개, 검사됐으나 mixed/weak가 없는 곡은 480개다. 이것은 검토 작업량을 정하는 통계이지 곡·주석의 합격/불합격 수가 아니다.

## Reviewer triage 기록

곡별 검토 화면에서 화성을 선택하면 다음 1차 분류를 저장할 수 있다.

- 표면 악보와 호환
- 비화성음/장식음 가능성
- 전위/베이스 해석
- 국소 조성/일시적 으뜸화
- 정렬/시간축 문제
- 원자료 라벨 의심
- 판단 보류

선택 의견도 함께 기록한다. 저장 위치는 각 곡 검토 디렉터리의 `reviewer_annotations.jsonl`이다. 구현은 `src/musicanote_harness/romantext_review_store.py`, 스키마는 `schemas/romantext_reviewer_annotation.schema.json`에 있다.

이 저장소는 append-only다. 같은 annotation을 다시 검토해도 이전 행을 삭제하지 않고 새 행의 `supersedes_review_id`로 연결한다. 화면은 가장 최근 판단을 보여 준다. 1차 triage의 `training_eligible`은 항상 `false`이며, 별도 adjudication을 거쳐야 validated annotation이나 학습 자료로 승격할 수 있다. 따라서 원자료, 자동 evidence, reviewer triage가 서로 덮어쓰이지 않는다.

## 전후 진행·해결 증거

단일 구간의 pitch-class 호환성만으로 NCT나 기능을 판정하지 않기 위해 `romantext-context-evidence-0.1.0`을 추가했다. 구현은 `src/musicanote_harness/romantext_context_evidence.py`, 스키마는 `schemas/romantext_context_evidence.schema.json`, 곡별 산출물은 `source_harmony_context_evidence.json`이다.

각 exact 화성과 다음 exact 화성의 경계에서 다음을 기록한다.

- 이전·현재·다음 source label과 annotation ID
- 현재와 다음 화음이 기대하는 공통·신규 pitch class
- 두 구간 시작의 실제 최저음과 bass 이동 반음 수
- 같은 Canonical voice에서 현재 구간 마지막 attack과 다음 구간 첫 attack의 연결
- 각 성부 연결의 반음 간격과 순차 진행 여부
- 현재 label의 외부음이 다음 label의 기대 구성음으로 1–2반음 이동한 `possible_nct_resolution`

이 값은 기술적 경계 증거다. 음이 1–2반음 해결되어도 자동으로 경과음·전타음·계류음이라고 확정하지 않는다. 같은 voice ID가 실제 대위 성부를 완벽히 뜻하지 않을 수도 있으므로 성부 교차와 복합 텍스처에서는 reviewer가 악보를 확인해야 한다. 기존 support band도 이 증거로 자동 승격·강등하지 않는다.

Bach WTC I Prelude 1에서는 37개 레코드 중 다음 경계가 있는 36개를 계산했고, 엄격한 조건의 NCT 해결 후보 edge는 1개였다. m.16 `I6 → ii`에서는 실제 시작 bass가 E3에서 D3로 2반음 하행하고, 연결된 3개 voice 중 2개가 순차 진행으로 표시되었다. 이는 원자료 I6의 정오 판정이 아니라 mixed 사례를 해석할 추가 문맥이다.

### 문맥 증거 전수 실행

`output/romantext-context-evidence-all-2026-09-25/`에서 exact annotation이 있는 1,902곡 전부를 실행했다. 1,902곡이 완료됐고 오류는 0곡이다.

| 항목 | 수 |
|---|---:|
| exact-context records | 150,146 |
| 다음 exact 화성과 비교 가능한 경계 | 147,993 |
| 같은 voice의 순차 진행 edge | 161,942 |
| possible NCT resolution edge | 23,735 |
| NCT 해결 후보가 하나 이상인 경계 | 18,655 (12.61%) |
| 정지·2반음 이내 bass 경계 | 73,185 (49.45%) |
| 4·5도 계열 bass 경계 | 33,809 (22.84%) |
| 그 밖의 bass 이동 경계 | 40,905 (27.64%) |
| 시작 bass를 얻지 못한 경계 | 94 |

OpenScore Lieder의 NCT 해결 후보 경계 비율은 12.91%, When in Rome은 11.98%였다. 정지·순차 bass 비율은 각각 48.36%, 51.69%였다. 이 차이는 자동 분석 정확도의 차이가 아니라 텍스처·성부 기보·주석 밀도 차이를 함께 반영한다.

전수 산출물은 source evidence 전수 검사와 같은 summary/pair records/candidate JSONL 구조를 사용하지만 `context_evidence_version`과 문맥 집계를 추가한다. 후보 JSONL에는 이전·다음 label, 실제 bass 이동, 순차 edge 수, possible NCT resolution 수가 함께 들어간다.

## 다음 단계

1. **구현 완료:** weak/mixed 표본을 악보에서 분류하는 append-only reviewer triage UI와 저장소.
2. **부분 구현 완료:** 앞뒤 화성, 실제 bass motion, 성부별 경계 진행과 제한적 resolution 후보. local key 추론과 cadence-aware resolution은 아직 남아 있다.
3. 실제 검토 표본이 쌓이면 reason별 confusion matrix를 만들고 support threshold를 조정한다.
4. adjudication을 거치기 전에는 evidence band나 triage record를 training gold로 사용하지 않는다.
