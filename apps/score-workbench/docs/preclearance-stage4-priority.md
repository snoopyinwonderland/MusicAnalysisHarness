# 사전검토 4단계 — 실험용 검토 우선순위 v1

상태: 오프라인 계산·회귀 검증 완료, 전문가 보정 및 corpus 변별력 검증 전. 메인 검색 순위를 바꾸지 않는다. 이 점수는 사람이 무엇부터 검토할지 정하는 실험 지표이지 침해 확률이나 권리 판정이 아니다.

## 일반 규칙 (작품/Query별 고정 없음)

match 우선도 = 유사도 × 입력 정보량 계수 × √입력 정렬 비율 × √후보 연속성 × 구조 계수.

- 입력 정보량: 동일음 반복 비율과 음정 분포 entropy를 반반 반영한다. 정보량 계수는 0.5~1이다. 이 값은 corpus 희귀도가 아니다.
- 입력 정렬 비율: 해당 task 음표 ID 중 alignment에 들어간 고유 ID 비율. 전체 업로드 coverage와 구분한다.
- 후보 연속성: 정렬된 고유 후보 음표 수 / 첫 음부터 마지막 음까지 전체 후보 음표 수. 띄엄띄엄 뽑힌 구간은 감점한다.
- 구조 계수: 0.8 + 0.2 × 양쪽 공통 구조 근거의 jointSupport. 아직 없는 종지·형식·기둥음 점수를 만들지 않는다.
- 모든 계수는 1 이하. 구조 점수로 낮은 멜로디 유사도를 끌어올리지 않는다.
- 작품은 가장 높은 match 한 개로 대표한다. 중복 판본, 같은 구간 반복, 겹친 Query를 합산하지 않는다.
- 누락 근거는 점수를 채우지 않고 needs-review로 남긴다. 미확인 권리나 accessPolicy로 면책/감점하지 않는다.
- 구조가 없는 후보는 별도 검토 대상이다. null을 실제 0점으로 해석하거나 보고서에서 숨기면 안 된다.

## 저장 계약

`works` 순서와 기존 match 내용은 그대로 유지한다. 추가 필드 `priorityAssessment`에 match별 계수와 대표 match index를 기록한다. 별도 `priorityReview.ranking`에 searchRank와 reviewRank를 함께 제공한다. 입력 report 지문과 계산 코드 지문을 저장한다. calibrated=false, legalProbability=false, corpusDistinctiveness=null을 명시한다.

```powershell
node scripts/prioritize-preclearance.mjs evaluation/runs/preclearance-importance-worker-2026-09-15.json evaluation/runs/preclearance-priority-2026-09-15.json
```

output은 새 경로여야 한다. 기존 파일은 보존한다.

## 2026-09-15 검증

- 관련 6개 테스트 파일, 35개 테스트 통과. 반복음 감점, 조옮김 불변, 짧은 입력의 유한값, 중복 match 불변, 누락 구조 미추정, 생략음 감점을 확인했다.
- 26개 작품 그룹/56개 match에 적용했고, 추가 필드를 제외한 기존 works 전체가 동일함을 deep equality로 확인했다.
- ENDLESS LOVE: 검색 1위 → 검토 1위, 검토 점수 87.84. 대표 match의 유사도 100, 정렬 비율/연속성 모두 1.
- Chorale: 검색 3위 → 검토 2위, 67.46. 대표 유사도 77.33, 정보량 계수 0.9853.
- Lamentatio Jeremiae - Sabbato Sancto - Jod: 검색 2위 → 검토 3위, 66.76. 대표 유사도 91.74지만 정보량 계수 0.8170. 동일음 반복 비중이 더 높은 Query에 매칭된 결과였다.
- 마지막 두 사례의 역전은 계산식이 의도대로 적용됐다는 증거일 뿐, 음악적으로 적절하다는 전문가 확인이 아니다. 정보량 감점이 과한지 검토할 주요 사례로 보존한다.

## 남은 검증과 다음 단계

1. 반복음·음계·아르페지오·장식음·강한 Phrase/Motif 사례를 포함한 전문가 순위 라벨로 감점 범위를 비교한다. 이번 한 업로드의 순위를 정답으로 고정하지 않는다.
2. corpus 문서 빈도와 작품/판본 중복 처리 정책을 별도로 설계한다. 현재 결과 목록은 top-k로 잘렸으므로 그것만으로 희귀도를 추정하지 않는다. entropy가 높아도 흔한 관용구일 수 있다.
3. 임계값/상중하 위험 라벨은 전문가 검증 전 도입하지 않는다. 이후 보고서 UI와 권리 레이어에 연결한다.

단순 관용구의 감점은 아직 query-internal heuristic 단계다. 전체 corpus에 기반한 변별력 단계가 완료됐다고 보고하지 않는다.
