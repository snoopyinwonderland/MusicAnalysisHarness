# 강도 2 멜로디 변형 100개

미실행 0개. 변형 100개와 원형 대조 20개는 별도 통계다. 음가는 4분음표=1. 동일 제목을 피한 기존 motif 자료의 편의 표본이며, 서로 떨어진 도약 두 개와 2박 이하 쉼을 요구하므로 순차 진행 위주 음악의 대표 표본이 아니다.

검색 알고리즘/기준은 실행 중 변경하지 않았다. 전체 DB, top 100 반환 기준. 기존 50개 top 30 통계와 단순 증감 비교하지 않는다. API alignment 검사와 실제 SVG 강조 검증은 다르다.

```json
{
  "selection": "20 distinct normalized titles from earlier motif suites; two separated leaps and no gap >2 required; paired convenience sample, not population sample",
  "remaining": 0,
  "variants": {
    "attempted": 100,
    "completed": 95,
    "failed": 5,
    "sourceFound": 46,
    "top1": 26,
    "top5": 44,
    "sourceWindowFound": 40,
    "invalidAlignment": 0,
    "medianSeconds": 17.90940770000033,
    "p95Seconds": 52.70243919999991
  },
  "controls": {
    "attempted": 20,
    "completed": 18,
    "failed": 2,
    "sourceFound": 18,
    "top1": 12,
    "top5": 18,
    "sourceWindowFound": 16,
    "invalidAlignment": 0,
    "medianSeconds": 30.56809340000013,
    "p95Seconds": 54.934494299999905
  },
  "variantsWhoseControlRetrieved": {
    "attempted": 90,
    "completed": 86,
    "failed": 4,
    "sourceFound": 40,
    "top1": 24,
    "top5": 38,
    "sourceWindowFound": 34,
    "invalidAlignment": 0,
    "medianSeconds": 17.90940770000033,
    "p95Seconds": 49.68440700000012
  },
  "byKind": {
    "two-pitches": {
      "attempted": 20,
      "completed": 18,
      "failed": 2,
      "sourceFound": 3,
      "top1": 0,
      "top5": 3,
      "sourceWindowFound": 2,
      "invalidAlignment": 0,
      "medianSeconds": 35.13438789999997,
      "p95Seconds": 59.69217040000018
    },
    "two-octaves": {
      "attempted": 20,
      "completed": 20,
      "failed": 0,
      "sourceFound": 1,
      "top1": 0,
      "top5": 1,
      "sourceWindowFound": 1,
      "invalidAlignment": 0,
      "medianSeconds": 28.509576899999754,
      "p95Seconds": 46.032123300000094
    },
    "two-rhythm-pairs": {
      "attempted": 20,
      "completed": 20,
      "failed": 0,
      "sourceFound": 20,
      "top1": 13,
      "top5": 20,
      "sourceWindowFound": 18,
      "invalidAlignment": 0,
      "medianSeconds": 7.610212999999989,
      "p95Seconds": 14.813634999999776
    },
    "two-leaps": {
      "attempted": 20,
      "completed": 17,
      "failed": 3,
      "sourceFound": 2,
      "top1": 0,
      "top5": 0,
      "sourceWindowFound": 1,
      "invalidAlignment": 0,
      "medianSeconds": 39.88293649999995,
      "p95Seconds": 55.70824219999998
    },
    "two-rest-splits": {
      "attempted": 20,
      "completed": 20,
      "failed": 0,
      "sourceFound": 20,
      "top1": 13,
      "top5": 20,
      "sourceWindowFound": 18,
      "invalidAlignment": 0,
      "medianSeconds": 6.617746999999974,
      "p95Seconds": 10.628664799999912
    }
  },
  "interpretation": "Source recall is not a human musical relevance judgment. Paired convenience sample. Top 100, not old top 30. SVG/audio not validated."
}
```

| 사례 | 원본 | 변형 | Query | 원형 순위 | 변형 source / 구간 순위 | 문제 및 개선 방향 |
|---|---|---|---|---|---|---|
| Q-H100-001 | 실비오는 소리에 | two-pitches | E4(1) A4(1) D#5(2) B4(4) B3(1) E4(1) B4(2) C#5(4) Rest(1) F#5(0.5) G#5(0.5) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-002 | 실비오는 소리에 | two-octaves | E4(1) A4(1) C#6(2) B4(4) B3(1) E4(1) D4(2) C#5(4) Rest(1) F#5(0.5) G#5(0.5) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-003 | 실비오는 소리에 | two-rhythm-pairs | E4(1) A4(1) C#5(4) B4(2) B3(1) E4(1) D5(4) C#5(2) Rest(1) F#5(0.5) G#5(0.5) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-004 | 실비오는 소리에 | two-leaps | E4(1) A4(1) C#5(2) B4(4) E4(1) E4(1) A4(2) C#5(4) Rest(1) F#5(0.5) G#5(0.5) | 1 | — / — | 검색 실패: Search timed out after 60000ms |
| Q-H100-005 | 실비오는 소리에 | two-rest-splits | E4(1) A4(1) C#5(1) Rest(1) B4(4) B3(1) E4(1) D5(1) Rest(1) C#5(4) Rest(1) F#5(0.5) G#5(0.5) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-006 | 창가에 | two-pitches | G4(2) B4(2) D5(1.75) D5(0.25) E5(1) G5(1) F#4(4) Rest(1) A5(1) F5(1) D5(1) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-007 | 창가에 | two-octaves | G4(2) B4(2) C6(1.75) D5(0.25) E5(1) G5(1) A3(4) Rest(1) A5(1) F5(1) D5(1) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-008 | 창가에 | two-rhythm-pairs | G4(2) B4(2) C5(1.875) D5(0.125) E5(1) G5(1) A4(4.5) Rest(1) A5(0.5) F5(1) D5(1) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-009 | 창가에 | two-leaps | G4(2) G#4(2) C5(1.75) D5(0.25) E5(1) G5(1) A4(4) Rest(1) E5(1) F5(1) D5(1) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-010 | 창가에 | two-rest-splits | G4(2) B4(2) C5(0.875) Rest(0.875) D5(0.25) E5(1) G5(1) A4(2) Rest(2) Rest(1) A5(1) F5(1) D5(1) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-011 | 잃어버린 우산 | two-pitches | F#5(2) C#5(1) B5(0.25) G#5(0.25) F#5(0.25) G#5(0.25) A#5(2) Rest(0.5) F#5(0.5) A5(0.5) C#6(0.25) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-012 | 잃어버린 우산 | two-octaves | F#5(2) C#5(1) A6(0.25) G#5(0.25) F#5(0.25) G#5(0.25) C#5(2) Rest(0.5) F#5(0.5) A5(0.5) C#6(0.25) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-013 | 잃어버린 우산 | two-rhythm-pairs | F#5(2) C#5(1) A5(0.375) G#5(0.125) F#5(0.25) G#5(0.25) C#6(2.25) Rest(0.5) F#5(0.25) A5(0.5) C#6(0.25) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-014 | 잃어버린 우산 | two-leaps | F#5(2) C#5(1) E5(0.25) G#5(0.25) F#5(0.25) G#5(0.25) C#6(2) Rest(0.5) B5(0.5) A5(0.5) C#6(0.25) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-015 | 잃어버린 우산 | two-rest-splits | F#5(2) C#5(1) A5(0.125) Rest(0.125) G#5(0.25) F#5(0.25) G#5(0.25) C#6(1) Rest(1) Rest(0.5) F#5(0.5) A5(0.5) C#6(0.25) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-016 | 누구라도 그러하듯이 | two-pitches | A4(4) D5(2) F#5(1) G#5(1) A5(1.5) B5(0.5) A5(0.5) A5(0.25) E5(0.75) C5(0.5) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-017 | 누구라도 그러하듯이 | two-octaves | A4(4) D5(2) E6(1) G#5(1) A5(1.5) B5(0.5) C5(0.5) A5(0.25) E5(0.75) C5(0.5) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-018 | 누구라도 그러하듯이 | two-rhythm-pairs | A4(4) D5(2) E5(1.5) G#5(0.5) A5(1.5) B5(0.5) C6(0.625) A5(0.125) E5(0.75) C5(0.5) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-019 | 누구라도 그러하듯이 | two-leaps | A4(4) A#4(2) E5(1) G#5(1) A5(1.5) B5(0.5) C6(0.5) A5(0.25) G#5(0.75) C5(0.5) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-020 | 누구라도 그러하듯이 | two-rest-splits | A4(4) D5(2) E5(0.5) Rest(0.5) G#5(1) A5(1.5) B5(0.5) C6(0.25) Rest(0.25) A5(0.25) E5(0.75) C5(0.5) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-021 | HE WILL HOLD ME FAST | two-pitches | F4(1) A#4(1) C5(1) A4(1) F4(1) A#3(1) E4(3) Rest(1) G4(1) Rest(0.5) F4(0.5) C4(1) | 2 | 2 / 2 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-022 | HE WILL HOLD ME FAST | two-octaves | F4(1) A#4(1) A#5(1) A4(1) F4(1) A#3(1) G3(3) Rest(1) G4(1) Rest(0.5) F4(0.5) C4(1) | 2 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-023 | HE WILL HOLD ME FAST | two-rhythm-pairs | F4(1) A#4(1) A#4(1.5) A4(0.5) F4(1) A#3(1) G4(3.5) Rest(1) G4(0.5) Rest(0.5) F4(0.5) C4(1) | 2 | 2 / 2 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-024 | HE WILL HOLD ME FAST | two-leaps | F4(1) F#4(1) A#4(1) A4(1) F4(1) A#3(1) D4(3) Rest(1) G4(1) Rest(0.5) F4(0.5) C4(1) | 2 | 11 / 11 | 상위 후보 악보 비교 필요; 원곡 강제 상향 금지 |
| Q-H100-025 | HE WILL HOLD ME FAST | two-rest-splits | F4(1) A#4(1) A#4(0.5) Rest(0.5) A4(1) F4(1) A#3(1) G4(1.5) Rest(1.5) Rest(1) G4(1) Rest(0.5) F4(0.5) C4(1) | 2 | 2 / 2 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-026 | CAN'T SMILE WITHOUT YOU | two-pitches | F#4(2) G4(2) C#5(2) A4(1) Rest(0.332) E4(0.332) G4(0.3359) G#4(2) A4(1.5) E4(0.5) B4(0.5) | 1 | — / — | 검색 실패: Search timed out after 60000ms |
| Q-H100-027 | CAN'T SMILE WITHOUT YOU | two-octaves | F#4(2) G4(2) B5(2) A4(1) Rest(0.332) E4(0.332) G4(0.3359) B3(2) A4(1.5) E4(0.5) B4(0.5) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-028 | CAN'T SMILE WITHOUT YOU | two-rhythm-pairs | F#4(2) G4(2) B4(2.5) A4(0.5) Rest(0.332) E4(0.332) G4(0.3359) B4(2.75) A4(0.75) E4(0.5) B4(0.5) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-029 | CAN'T SMILE WITHOUT YOU | two-leaps | F#4(2) G4(2) B4(2) A4(1) Rest(0.332) G#4(0.332) G4(0.3359) B4(2) A4(1.5) G#4(0.5) B4(0.5) | 1 | — / — | 검색 실패: Search timed out after 60000ms |
| Q-H100-030 | CAN'T SMILE WITHOUT YOU | two-rest-splits | F#4(2) G4(2) B4(1) Rest(1) A4(1) Rest(0.332) E4(0.332) G4(0.3359) B4(1) Rest(1) A4(1.5) E4(0.5) B4(0.5) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-031 | Defying Gravity (From 'Glee') | two-pitches | D5(3) F#4(0.5) B4(3.5) D4(1) F#4(1.5) E4(0.5) C#4(2) Rest(1) A4(0.5) A4(1) E5(1.5) | 2 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-032 | Defying Gravity (From 'Glee') | two-octaves | D5(3) F#4(0.5) A5(3.5) D4(1) F#4(1.5) E4(0.5) E3(2) Rest(1) A4(0.5) A4(1) E5(1.5) | 2 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-033 | Defying Gravity (From 'Glee') | two-rhythm-pairs | D5(3) F#4(0.5) A4(4) D4(0.5) F#4(1.5) E4(0.5) E4(2.25) Rest(1) A4(0.25) A4(1) E5(1.5) | 2 | 2 / — | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-034 | Defying Gravity (From 'Glee') | two-leaps | D5(3) B4(0.5) A4(3.5) G4(1) F#4(1.5) E4(0.5) E4(2) Rest(1) A4(0.5) A4(1) E5(1.5) | 2 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-035 | Defying Gravity (From 'Glee') | two-rest-splits | D5(3) F#4(0.5) A4(1.75) Rest(1.75) D4(1) F#4(1.5) E4(0.5) E4(1) Rest(1) Rest(1) A4(0.5) A4(1) E5(1.5) | 2 | 2 / — | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-036 | TOP GUN ANTHEM | two-pitches | E5(3) C5(1) G5(2) A4(0.75) B4(0.75) C5(0.5) A4(0.5) F4(0.5) A4(0.5) C5(0.5) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-037 | TOP GUN ANTHEM | two-octaves | E5(3) C5(1) F6(2) A4(0.75) B4(0.75) C5(0.5) C4(0.5) F4(0.5) A4(0.5) C5(0.5) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-038 | TOP GUN ANTHEM | two-rhythm-pairs | E5(3) C5(1) F5(2.375) A4(0.375) B4(0.75) C5(0.5) C5(0.75) F4(0.25) A4(0.5) C5(0.5) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-039 | TOP GUN ANTHEM | two-leaps | E5(3) C5(1) F5(2) D5(0.75) B4(0.75) C5(0.5) C5(0.5) A#4(0.5) A4(0.5) C5(0.5) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-040 | TOP GUN ANTHEM | two-rest-splits | E5(3) C5(1) F5(1) Rest(1) A4(0.75) B4(0.75) C5(0.5) C5(0.25) Rest(0.25) F4(0.5) A4(0.5) C5(0.5) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-041 | BRED DINA VIDA VINGAR | two-pitches | A5(1) C#6(1) F#5(1) F#5(0.5) D5(0.5) C#5(0.5) C#5(0.5) A5(2) B5(0.5) C#6(0.5) | 3 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-042 | BRED DINA VIDA VINGAR | two-octaves | A5(1) C#6(1) E6(1) F#5(0.5) D5(0.5) C#5(0.5) E4(0.5) A5(2) B5(0.5) C#6(0.5) | 3 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-043 | BRED DINA VIDA VINGAR | two-rhythm-pairs | A5(1) C#6(1) E5(1.25) F#5(0.25) D5(0.5) C#5(0.5) E5(1.5) A5(1) B5(0.5) C#6(0.5) | 3 | 3 / 3 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-044 | BRED DINA VIDA VINGAR | two-leaps | A5(1) C#6(1) A5(1) F#5(0.5) D5(0.5) C#5(0.5) E5(0.5) F5(2) B5(0.5) C#6(0.5) | 3 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-045 | BRED DINA VIDA VINGAR | two-rest-splits | A5(1) C#6(1) E5(0.5) Rest(0.5) F#5(0.5) D5(0.5) C#5(0.5) E5(0.25) Rest(0.25) A5(2) B5(0.5) C#6(0.5) | 3 | 3 / 3 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-046 | 가장 무도회 | two-pitches | D5(3) G4(1) D5(1.5) D5(0.5) E5(1) G5(0.5) A5(0.5) A5(3) G5(0.5) A5(0.5) | 미회수/실패 | — / — | 검색 실패: Search timed out after 60000ms |
| Q-H100-047 | 가장 무도회 | two-octaves | D5(3) G4(1) C6(1.5) D5(0.5) E5(1) G5(0.5) C5(0.5) A5(3) G5(0.5) A5(0.5) | 미회수/실패 | — / — | 원형도 미회수/실패: 변형 탓으로 단정 금지 |
| Q-H100-048 | 가장 무도회 | two-rhythm-pairs | D5(3) G4(1) C5(1.75) D5(0.25) E5(1) G5(0.5) C6(2) A5(1.5) G5(0.5) A5(0.5) | 미회수/실패 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-049 | 가장 무도회 | two-leaps | D5(3) C5(1) C5(1.5) D5(0.5) E5(1) G5(0.5) G#5(0.5) A5(3) G5(0.5) A5(0.5) | 미회수/실패 | — / — | 원형도 미회수/실패: 변형 탓으로 단정 금지 |
| Q-H100-050 | 가장 무도회 | two-rest-splits | D5(3) G4(1) C5(0.75) Rest(0.75) D5(0.5) E5(1) G5(0.5) C6(0.25) Rest(0.25) A5(3) G5(0.5) A5(0.5) | 미회수/실패 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-051 | CARO MIO BEN | two-pitches | F#4(1) Rest(1) G4(1) G#4(0.5) E4(0.5) A4(0.5) D5(0.5) B3(0.5) G4(0.5) F#4(1) E4(0.75) | 3 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-052 | CARO MIO BEN | two-octaves | F#4(1) Rest(1) G4(1) F#5(0.5) E4(0.5) A4(0.5) D5(0.5) D3(0.5) G4(0.5) F#4(1) E4(0.75) | 3 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-053 | CARO MIO BEN | two-rhythm-pairs | F#4(1) Rest(1) G4(1) F#4(0.75) E4(0.25) A4(0.5) D5(0.5) D4(0.75) G4(0.25) F#4(1) E4(0.75) | 3 | 4 / 4 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-054 | CARO MIO BEN | two-leaps | F#4(1) Rest(1) G4(1) F#4(0.5) E4(0.5) F4(0.5) D5(0.5) G4(0.5) G4(0.5) F#4(1) E4(0.75) | 3 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-055 | CARO MIO BEN | two-rest-splits | F#4(1) Rest(1) G4(1) F#4(0.25) Rest(0.25) E4(0.5) A4(0.5) D5(0.5) D4(0.25) Rest(0.25) G4(0.5) F#4(1) E4(0.75) | 3 | 3 / 3 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-056 | 혼자이고 싶어요 | two-pitches | C5(3.25) A4(0.25) C#5(0.25) C5(0.25) B4(1) B3(0.3333) C#4(0.3333) G4(0.3333) B4(1) B3(0.3333) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-057 | 혼자이고 싶어요 | two-octaves | C5(3.25) A4(0.25) B5(0.25) C5(0.25) B4(1) B3(0.3333) E3(0.3333) G4(0.3333) B4(1) B3(0.3333) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-058 | 혼자이고 싶어요 | two-rhythm-pairs | C5(3.25) A4(0.25) B4(0.375) C5(0.125) B4(1) B3(0.3333) E4(0.5) G4(0.1667) B4(1) B3(0.3333) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-059 | 혼자이고 싶어요 | two-leaps | C5(3.25) A4(0.25) B4(0.25) C5(0.25) B4(1) E4(0.3333) E4(0.3333) G4(0.3333) G#4(1) B3(0.3333) | 1 | — / — | 검색 실패: Search timed out after 60000ms |
| Q-H100-060 | 혼자이고 싶어요 | two-rest-splits | C5(3.25) A4(0.25) B4(0.125) Rest(0.125) C5(0.25) B4(1) B3(0.3333) E4(0.1667) Rest(0.1667) G4(0.3333) B4(1) B3(0.3333) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-061 | 새 타령 (한국 민요) | two-pitches | D#5(0.75) G5(0.25) F5(0.25) D5(0.25) G5(1.5) C5(1) C5(0.5) G5(0.5) G4(0.75) C5(0.25) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-062 | 새 타령 (한국 민요) | two-octaves | D#5(0.75) G5(0.25) D#6(0.25) D5(0.25) G5(1.5) C5(1) D#4(0.5) G5(0.5) G4(0.75) C5(0.25) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-063 | 새 타령 (한국 민요) | two-rhythm-pairs | D#5(0.75) G5(0.25) D#5(0.375) D5(0.125) G5(1.5) C5(1) D#5(0.75) G5(0.25) G4(0.75) C5(0.25) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-064 | 새 타령 (한국 민요) | two-leaps | D#5(0.75) G5(0.25) D#5(0.25) D5(0.25) G5(1.5) F5(1) D#5(0.5) G5(0.5) C5(0.75) C5(0.25) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-065 | 새 타령 (한국 민요) | two-rest-splits | D#5(0.75) G5(0.25) D#5(0.125) Rest(0.125) D5(0.25) G5(1.5) C5(1) D#5(0.25) Rest(0.25) G5(0.5) G4(0.75) C5(0.25) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-066 | 팔베개 | two-pitches | F5(2) G5(1) F5(0.3333) G5(0.3333) A#5(0.3333) D6(1.75) A5(0.25) A5(1) D5(0.3333) F#5(0.3333) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-067 | 팔베개 | two-octaves | F5(2) G5(1) D#6(0.3333) G5(0.3333) A#5(0.3333) D6(1.75) C5(0.25) A5(1) D5(0.3333) F#5(0.3333) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-068 | 팔베개 | two-rhythm-pairs | F5(2) G5(1) D#5(0.5) G5(0.1667) A#5(0.3333) D6(1.75) C6(0.75) A5(0.5) D5(0.3333) F#5(0.3333) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-069 | 팔베개 | two-leaps | F5(2) G5(1) F#5(0.3333) G5(0.3333) A#5(0.3333) D6(1.75) C6(0.25) A5(1) G5(0.3333) F#5(0.3333) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-070 | 팔베개 | two-rest-splits | F5(2) G5(1) D#5(0.1667) Rest(0.1667) G5(0.3333) A#5(0.3333) D6(1.75) C6(0.125) Rest(0.125) A5(1) D5(0.3333) F#5(0.3333) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-071 | 짝사랑 | two-pitches | C#5(3) G#4(0.75) C#5(0.25) C#5(3) G#4(0.75) E4(0.25) D#4(4) Rest(0.75) B4(0.25) C#5(0.75) B4(0.25) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-072 | 짝사랑 | two-octaves | C#5(3) G#4(0.75) B5(0.25) C#5(3) G#4(0.75) E4(0.25) F#3(4) Rest(0.75) B4(0.25) C#5(0.75) B4(0.25) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-073 | 짝사랑 | two-rhythm-pairs | C#5(3) G#4(0.75) B4(1.75) C#5(1.5) G#4(0.75) E4(0.25) F#4(4.125) Rest(0.75) B4(0.125) C#5(0.75) B4(0.25) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-074 | 짝사랑 | two-leaps | C#5(3) C5(0.75) B4(0.25) C#5(3) C5(0.75) E4(0.25) F#4(4) Rest(0.75) B4(0.25) C#5(0.75) B4(0.25) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-075 | 짝사랑 | two-rest-splits | C#5(3) G#4(0.75) B4(0.125) Rest(0.125) C#5(3) G#4(0.75) E4(0.25) F#4(2) Rest(2) Rest(0.75) B4(0.25) C#5(0.75) B4(0.25) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-076 | 토요일 밤 | two-pitches | D4(0.5) D5(0.25) G#5(0.25) D4(0.25) D5(0.25) F#5(0.25) B3(0.25) F#5(1) Rest(1) A3(0.5) A4(0.5) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-077 | 토요일 밤 | two-octaves | D4(0.5) D5(0.25) F#6(0.25) D4(0.25) D5(0.25) F#5(0.25) D3(0.25) F#5(1) Rest(1) A3(0.5) A4(0.5) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-078 | 토요일 밤 | two-rhythm-pairs | D4(0.5) D5(0.25) F#5(0.375) D4(0.125) D5(0.25) F#5(0.25) D4(0.75) F#5(0.5) Rest(1) A3(0.5) A4(0.5) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-079 | 토요일 밤 | two-leaps | D4(0.5) D5(0.25) F#5(0.25) G4(0.25) D5(0.25) F#5(0.25) D4(0.25) F#5(1) Rest(1) D4(0.5) A4(0.5) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-080 | 토요일 밤 | two-rest-splits | D4(0.5) D5(0.25) F#5(0.125) Rest(0.125) D4(0.25) D5(0.25) F#5(0.25) D4(0.125) Rest(0.125) F#5(1) Rest(1) A3(0.5) A4(0.5) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-081 | I SAW MOMMY KISSING SANTA CLAUS | two-pitches | B5(2) Rest(1) G5(1) F#5(3) Rest(1) A5(1) G5(1) E5(1) Rest(0.5) A4(0.5) A5(1) G5(1) E5(1) | 2 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-082 | I SAW MOMMY KISSING SANTA CLAUS | two-octaves | B5(2) Rest(1) G5(1) E6(3) Rest(1) A5(1) G5(1) E5(1) Rest(0.5) C4(0.5) A5(1) G5(1) E5(1) | 2 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-083 | I SAW MOMMY KISSING SANTA CLAUS | two-rhythm-pairs | B5(2) Rest(1) G5(1) E5(3.5) Rest(1) A5(0.5) G5(1) E5(1) Rest(0.5) C5(1) A5(0.5) G5(1) E5(1) | 2 | 2 / 2 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-084 | I SAW MOMMY KISSING SANTA CLAUS | two-leaps | B5(2) Rest(1) G5(1) E5(3) Rest(1) F5(1) G5(1) E5(1) Rest(0.5) C5(0.5) E5(1) G5(1) E5(1) | 2 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-085 | I SAW MOMMY KISSING SANTA CLAUS | two-rest-splits | B5(2) Rest(1) G5(1) E5(1.5) Rest(1.5) Rest(1) A5(1) G5(1) E5(1) Rest(0.5) C5(0.25) Rest(0.25) A5(1) G5(1) E5(1) | 2 | 2 / 2 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-086 | AQUA | two-pitches | G4(1) B4(0.75) B4(0.25) A4(1.5) D4(0.5) G4(1) F#4(1) B4(1.5) D4(0.5) E4(0.5) | 미회수/실패 | 2 / 2 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-087 | AQUA | two-octaves | G4(1) B4(0.75) A5(0.25) A4(1.5) D4(0.5) G4(1) A3(1) B4(1.5) D4(0.5) E4(0.5) | 미회수/실패 | 2 / 2 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-088 | AQUA | two-rhythm-pairs | G4(1) B4(0.75) A4(1) A4(0.75) D4(0.5) G4(1) A4(1.75) B4(0.75) D4(0.5) E4(0.5) | 미회수/실패 | 2 / 2 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-089 | AQUA | two-leaps | G4(1) B4(0.75) A4(0.25) A4(1.5) G4(0.5) G4(1) A4(1) B4(1.5) G4(0.5) E4(0.5) | 미회수/실패 | — / — | 원형도 미회수/실패: 변형 탓으로 단정 금지 |
| Q-H100-090 | AQUA | two-rest-splits | G4(1) B4(0.75) A4(0.125) Rest(0.125) A4(1.5) D4(0.5) G4(1) A4(0.5) Rest(0.5) B4(1.5) D4(0.5) E4(0.5) | 미회수/실패 | 2 / 2 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-091 | Haru's Memories | two-pitches | B5(2) G#5(1) C#5(2) G#5(1) A5(0.5) B5(0.5) F#5(1) F#5(1) B4(2) F#5(1) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-092 | Haru's Memories | two-octaves | B5(2) G#5(1) B5(2) G#5(1) A5(0.5) B5(0.5) A4(1) F#5(1) B4(2) F#5(1) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-093 | Haru's Memories | two-rhythm-pairs | B5(2) G#5(1) B4(2.5) G#5(0.5) A5(0.5) B5(0.5) A5(1.5) F#5(0.5) B4(2) F#5(1) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-094 | Haru's Memories | two-leaps | B5(2) G#5(1) E5(2) G#5(1) A5(0.5) B5(0.5) A5(1) F#5(1) E5(2) F#5(1) | 1 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-095 | Haru's Memories | two-rest-splits | B5(2) G#5(1) B4(1) Rest(1) G#5(1) A5(0.5) B5(0.5) A5(0.5) Rest(0.5) F#5(1) B4(2) F#5(1) | 1 | 1 / 1 | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-096 | A WHOLE NEW WORLD | two-pitches | E6(1) D6(0.5) D6(1.5) Rest(0.5) F5(0.5) E6(0.6641) F6(0.668) A5(1.668) Rest(0.5) F5(0.5) A5(1) G5(0.5) | 3 | 3 / — | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-097 | A WHOLE NEW WORLD | two-octaves | E6(1) D6(0.5) C7(1.5) Rest(0.5) F5(0.5) E6(0.6641) F6(0.668) C5(1.668) Rest(0.5) F5(0.5) A5(1) G5(0.5) | 3 | — / — | 원형 회수/변형 미회수: 후보 누락과 admission 탈락 분리 진단 |
| Q-H100-098 | A WHOLE NEW WORLD | two-rhythm-pairs | E6(1) D6(0.5) C6(1.75) Rest(0.5) F5(0.25) E6(0.6641) F6(0.668) C6(1.918) Rest(0.5) F5(0.25) A5(1) G5(0.5) | 3 | 4 / — | 회수됨; 음악적 순위 정당성은 별도 검토 |
| Q-H100-099 | A WHOLE NEW WORLD | two-leaps | E6(1) D6(0.5) C6(1.5) Rest(0.5) F5(0.5) B5(0.6641) F6(0.668) C6(1.668) Rest(0.5) A#5(0.5) A5(1) G5(0.5) | 3 | 20 / — | 상위 후보 악보 비교 필요; 원곡 강제 상향 금지 |
| Q-H100-100 | A WHOLE NEW WORLD | two-rest-splits | E6(1) D6(0.5) C6(0.75) Rest(0.75) Rest(0.5) F5(0.5) E6(0.6641) F6(0.668) C6(0.834) Rest(0.834) Rest(0.5) F5(0.5) A5(1) G5(0.5) | 3 | 4 / — | 회수됨; 음악적 순위 정당성은 별도 검토 |

## 보존 자료
suite.json: 원형·100 Query·변경 내역·앞뒤 2마디 논리 이벤트·기대 좌표·엔진/DB 지문. 사례 JSON: 실제 top 100 결과와 정렬. summary.json: 개별 상태와 지연. 원본 음원이나 원래 판면 복제는 포함하지 않으며 events로 선율과 쉼을 재기보할 수 있다.

## 후속 검토
실패 사례는 원형 대비로 분류하고, 상위 후보의 완전 일치 여부와 음정/리듬/박절 점수 및 실제 구간을 비교한다. 동일 원곡의 다른 판본이 상위일 수 있다. humanReview는 아직 unreviewed다.

## 별도 시간 초과 재시도
180초 제한. 최초 실행 통계는 위에 그대로 보존하며 재시도 지연을 섞지 않는다.
```json
{
  "timeoutMs": 180000,
  "primaryUnchanged": true,
  "warning": "Separate retry with different warm-cache conditions, not primary latency samples",
  "runs": [
    {
      "caseId": "Q-H100-004",
      "kind": "two-leaps",
      "status": "completed",
      "elapsedMs": 15078.384600000001,
      "sourceRank": null
    },
    {
      "caseId": "Q-H100-026",
      "kind": "two-pitches",
      "status": "completed",
      "elapsedMs": 15321.488099999999,
      "sourceRank": null
    },
    {
      "caseId": "Q-H100-029",
      "kind": "two-leaps",
      "status": "completed",
      "elapsedMs": 27342.595099999995,
      "sourceRank": null
    },
    {
      "caseId": "CTRL-B10",
      "kind": "control",
      "status": "completed",
      "elapsedMs": 19346.435600000004,
      "sourceRank": 1
    },
    {
      "caseId": "Q-H100-046",
      "kind": "two-pitches",
      "status": "completed",
      "elapsedMs": 38316.3799,
      "sourceRank": null
    },
    {
      "caseId": "Q-H100-059",
      "kind": "two-leaps",
      "status": "completed",
      "elapsedMs": 16307.70289999999,
      "sourceRank": null
    },
    {
      "caseId": "CTRL-B18",
      "kind": "control",
      "status": "completed",
      "elapsedMs": 18009.678199999995,
      "sourceRank": 2
    }
  ]
}
```

## XML / Verovio 검증
렌더링 94개, 검색 결과 없음 6개. 미해결 좌표/누락 ID 0개. 각 Query의 대표 결과 하나를 검사한 것이며 모든 반환 결과의 육안/청취 검증은 아니다.