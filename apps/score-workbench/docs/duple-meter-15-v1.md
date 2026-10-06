# 2/4 소규모 검색 검증

2026-09-17 사용자 승인. 새 원곡 5개 × 12음 원형/한 음+음가 삭제/삭제 음가를 앞 음에 흡수 = 15회.

- 이전 harder-100, short-query-90, triple-meter-60, eighth-meter-60 원곡 제목 제외. 검색 결과를 보기 전에 XML로만 선별한다.
- 전체 순차진행/동음반복은 주 평가에서 제외한다. 원형과 변형 모두 검증한다. 짧은 순차 구간은 허용한다.
- 같은 성부의 연속 12음, 명확한 XML↔index 대응, 약박·짧은 경과음/보조음 후보를 사용한다. 확정 화성/셴커 분석이 아니다.
- 이번 표본은 마디 첫박 시작이다. 못갖춘마디 시작은 직접 검증하지 않으며, 못갖춘마디·쉼표 경계를 모두 포괄했다고 주장하지 않는다.
- 한 원곡의 세 조건을 독립 원곡 3개로 계산하지 않는다. Top10 회수는 긍정적이며 1위 강제는 하지 않는다.

## 재현

1. node scripts/build-duple-meter-suite.mjs
2. node scripts/audit-duple-meter-suite.mjs
3. MUSICANOTE_SINGLE_OMISSION=1, MUSICANOTE_VISIBLE_RANKING=0; node scripts/run-structural-next40.mjs evaluation/reports/duple-meter-15-v1/suite.json evaluation/runs/duple-meter-15-v1
4. node scripts/finish-duple-meter-evaluation.mjs

Query·선별 근거·전체 응답·원본 XML 문맥·진단은 evaluation/exports/duple-meter-15-v1에 보관한다. 결과 페이지는 /evaluation/reports/duple-meter-15-v1/index.html 이다. 새 순차·반복 전용 리듬 우선 로직이 있는 엔진 버전으로 실행하되 이번 Query에는 해당 패턴을 제외한다. 과거 엔진 결과를 같은 버전 성능으로 합산하지 않는다.

## 후속 개선 순서

1. EVAL-001: Exact 음가/쉼표 판정과 허용적 리듬 점수 분리. 완전 일치/작은 변형 대조 테스트부터 작성.
2. EVAL-002/003/005: 긴 음·음가 흡수·분할/합침·옥타브 변경 정렬과 표시를 공통 대응 규칙으로 검증.
3. EVAL-006/007/008: 특징적인 Query의 후보 누락/반복 대표 창/엄격 하한을 진단하고 회수·오탐·속도를 함께 비교.
4. EVAL-004: 반복 위치 UI 보완. 이후 불규칙 박자 grouping 계약과 입력 지원.

현재 상태: 15회 모두 완료. 오류·재시도 0건, 독립 사례 보관 검증 통과. 위 후속 개선 항목은 구현 완료가 아니다.

| 조건 | Top5 / Top10 | 반환 100개 내 회수 |
|---|---:|---:|
| 12음 원형 | 5/5 | 5/5 |
| 12→11음 삭제·시간 축소 | 3/5 | 3/5 |
| 12→11음 삭제·앞 음 음가 흡수 | 4/5 | 4/5 |

MICKEY MOUSE MARCH는 시간 축소에서 원곡 후보가 평가됐으나 low-information-floors에 걸렸고, 시간 유지에서는 2위였다. THE PROCESSION OF CELESTIAL BEINGS는 두 삭제 조건 모두 후보 평가 후 admission-floor에 걸렸다. 원형은 각각 2위·1위였다. 이번 미회수는 후보 목록 자체의 누락이 아니라 평가 후 통과 조건에서 발생했다. 2/4 박자 자체가 원인이라고 단정하지 않는다.

## 추가 검증 우선순위

새 원곡을 무작정 늘리기보다 기존 미회수 3건을 먼저 진단하고 공통 수정 전후를 비교한다. 다음 소규모 검증은 (1) 전체 템포 확대·축소와 부분 음가 변경의 구별, 쉼표 차이 Exact 판정 (2) 못갖춘마디/약박 시작·마디 경계 (3) 같은 음정·다른 리듬의 비정답 경쟁 후보다. 특히 비정답 라벨을 갖춘 대조군 없이 현재 성공 회수율을 오탐 억제 성능이라고 해석하지 않는다.

이번 전체 실행 성공 및 잘못된 alignment 인덱스 참조 0건은 실제 강조의 시각적 정확성 검증과 구분한다. 5/8·7/8 대량 검증은 grouping 지원 정리 후 진행한다.

선정된 원곡: A FISTFUL OF DOLLARS, ICH LIEBE DICH, MICKEY MOUSE MARCH, THE PROCESSION OF CELESTIAL BEINGS, A CHRISTMAS FESTIVAL. 모두 선택 구간의 실제 XML이 2/4인 판본이다.
