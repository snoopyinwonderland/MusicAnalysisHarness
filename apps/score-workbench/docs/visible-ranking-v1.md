# 표시 점수와 순위 일관성 실험 — 2026-09-16

## 사용자 사례
변형 Caro Mio Ben Query에서 기다리는 마음: 총점88, interval90/rhythm55/meter90/structural34. Caro Mio Ben 피아노: 총점87, interval98/rhythm69/meter91/structural87. 사용자 제공 값이며 현재 서버 재검색으로 동일 응답을 확보한 것은 아님.

기존 S100-055의 Query, 실제 음표 및 정렬은 evaluation/runs/structural-baseline-v1/S100-055.json에 보존되어 있다. 그 저장 결과는 Caro Mio Ben 다른 판본이 이미1위이고 지정 Quartet 원본 파일이8위였다. sourceRank를 작품 전체 순위로 설명하면 안 된다. 현재 사용자의2위와 당시8위는 동일 지표가 아니다.

## 원인과 실험
기존 총점은 local55% + surface45% + 보정(-3~1). local에 이미 박자/구조/기둥 보너스가 포함된다. 표시4항목의 가중 평균이 아니므로 역전 가능.

실험: interval70%, rhythm15%, meter10%, structural5%, local 보정±1, 기타 보정±0.5. Exact100, Similar 상한97 유지. Schenker-informed는 휴리스틱이며 확정 분석으로 취급하지 않는다. 특정 작품 조건 없음. MUSICANOTE_VISIBLE_RANKING=1에서만 활성, 기본 OFF.

## 검증 및 적용 판단
단위 테스트69개 통과(실험 함수의 단조성/보정 상한/제시 점수 프로필 포함). 저장100개 재채점은 개선1, 하락11, 지정 원본Top5 99→96. 후보 재검색이 아니고 기존 최종 보정이 저장되지 않아0으로 두었다. 결과 evaluation/reports/visible-ranking-v1/replay.json, 재현 node scripts/audit-visible-ranking.mjs.

회귀 때문에 기본 적용 보류. 다음은 하락11개에서 다른 판본 우선인지 실제 열화인지 악보와 정렬을 검토하고, 정렬 대응률/삽입누락 비용을 명시적으로 분리해 보정하는 것. 최종적으로 동일 DB/Query의 전체 검색 A/B 필요. 표시 점수만으로 모든 차이를 단정하지 않는다.
