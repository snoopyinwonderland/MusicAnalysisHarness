# 장식음 두 개 삭제 추가 실험 — 2026-09-16

## 요청과 범위

장식음 두 개 삭제 테스트를 추가한다. 현재 검색 알고리즘과 운영 설정을 수정하지 않는다. 기존 v2의 원형 구간 및 이번 신규 구간끼리 겹치지 않도록 색인 onset 범위를 검사한다.

## 선별

- 이전 XML 감사 20곡을 입력 풀로 사용하며 검색 결과를 보기 전에 표본을 확정했다.
- v2와 동일하게 동일 part/staff/voice, 약박·짧은 음가·경과음/보조음 형태와 주변 지지 근거를 요구한다. 화성 분석에 따른 확정 장식음 판정은 아니다.
- 원형 16음, 1개 삭제 15음, 2개 삭제 14음. 삭제한 음가도 제거하며 기존 쉼표는 보존한다.
- 총 길이 24박 이하, 개별 쉼 1박 이하. 음역·음가·실제 XML 문맥과 삭제 이유를 suite.json에 보존한다.
- 10개 원형 모두 떨어진 두 음 삭제다. 연속 삭제는 조건을 통과한 사례가 없어 포함하지 않는다.
- 5개 원본 작품의 10개 구간이다. 같은 곡의 다른 반복/변형 구간이 포함되므로 독립적인 10곡 성능으로 해석하면 안 된다. 순차 선별의 편향이 있으며 이번 결과를 보고 선별 규칙을 완화하지 않는다.
- 모두 4/4이며 원형의 음높이·음가·쉼표열을 직렬화하면 고유한 열은 8개다. 서로 다른 위치라도 동일 선율 반복일 수 있다. 결과를 본 뒤 제거하지 않고 원래 10개 표본을 그대로 보고한다.

## 실행

1. node scripts/build-double-ornament-trial.mjs evaluation/reports/double-ornament-trial-v3 evaluation/reports/double-ornament-trial-v2/suite.json
2. MUSICANOTE_SINGLE_OMISSION=1, MUSICANOTE_VISIBLE_RANKING=0 환경에서 node scripts/run-structural-next40.mjs evaluation/reports/double-ornament-trial-v3/suite.json evaluation/runs/double-ornament-trial-v3
3. node scripts/report-double-ornament-trial.mjs double-ornament-trial-v3

생성기는 기존 경로를 덮어쓰지 않으므로 재실행은 새 batch 경로를 사용한다. 단계 1의 생성기에는 XML onset과 색인 onset을 혼용하지 않도록 후속 안전 수정이 있다. 현재 suite의 기존/신규 구간 중복은 별도 색인 좌표 검사에서 모두 0건이었다.

원본 파일 회수(top100), Top5, 지정 원래 구간 회수(동일 성부·보존음 onset/pitch 80% 이상)를 구분한다. 다른 반복 구간을 찾은 경우 곡 회수는 성공이어도 원래 구간 회수는 실패로 남긴다. 오류와 미회수도 구분한다.

## 최종 결과

30회 모두 완료(오류·시간초과 없음). 원형/1음 삭제 Top5 각각 10/10, 두 음 삭제 8/10. 고유 Query 기준 두 음 삭제 7/8이다. 가장 무도회의 같은 선율 두 위치가 실패했고, 원본 work는 후보에 있었으나 대상 index 52/140 대신 시작 0의 창이 평가되어 admission-floor에서 탈락했다. 원인을 특정 곡 예외나 점수 완화로 해결하지 않는다.

대표 구간 음표 대응은 5/10, 6/10, 4/10이나 반복 구간 대표 선택이 포함된 지표다. CARO MIO BEN은 실제 onset 대응은 완전하지만 마디 표기 번호가 1만큼 달라 단순 마디 비교와 구분했다. 상세 해석은 [최종 검토](../evaluation/reports/double-ornament-trial-v3/REVIEW.md).

사전 20%p 하락 기준에 해당하여 두 음 삭제 전용 확장은 보류한다. 중복을 제외하면 감소폭 12.5%p이며 표본이 작다는 한계도 함께 기록한다. 기존 검색 기능을 제거하거나 수정하지 않았다.

## 자료

- 원형·Query·XML 문맥·삭제 근거: evaluation/reports/double-ornament-trial-v3/suite.json
- 실행 환경 fingerprint 및 전체 응답: evaluation/runs/double-ornament-trial-v3/
- 결과 표와 악보: evaluation/reports/double-ornament-trial-v3/REPORT.md 및 index.html
- 이전 실험: docs/double-ornament-trial-v1.md
- 변형 무결성·중복 검사·반복 구간 대응: node scripts/audit-double-ornament-trial.mjs double-ornament-trial-v3 → audit.json
