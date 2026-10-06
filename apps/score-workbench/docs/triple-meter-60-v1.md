# 3/4 장식음 삭제 — 60회 비교 검증

2026-09-17 사용자 실행 승인. 검색 알고리즘 변경 없이 수행하며 개선안은 마지막에 모아서 검토한다.

## 설계

- 기존 harder-100 및 short-query-90 원곡을 제외한 새 원곡 10개를 XML만으로 먼저 선정한다.
- 3/4만 사용한다. 12음과 그 prefix 8음을 각각 원형, 한 음+음가 삭제, 한 음 삭제 후 앞 음으로 음가 흡수하여 검색한다. 총 60회다.
- 삭제 대상은 짧고 약박인 순차진행 경과음/보조음 후보다. 같은 성부·연속 attack·XML 대응이 명료한 구간을 사용한다. 화성 분석으로 확정한 장식음은 아니다.
- 음가 흡수는 뒤 음들의 onset을 유지하지만 앞 음 길이를 바꾸므로 두 조건의 차이를 순수 박자 위치 효과라고 단정하지 않는다.
- 8→7음은 경계 사례이며 미회수를 모두 실패로 간주하지 않는다. 12→11음과 비교한다. 원곡 1위는 요구하지 않는다.
- 같은 원곡의 6조건을 독립 음악 60개의 성공률로 해석하지 않는다. 무관한 곡 라벨이 없으므로 오탐률은 산출하지 않는다.

## 재현

1. node scripts/build-triple-meter-suite.mjs
2. node scripts/audit-triple-meter-suite.mjs
3. MUSICANOTE_SINGLE_OMISSION=1, MUSICANOTE_VISIBLE_RANKING=0; node scripts/run-structural-next40.mjs evaluation/reports/triple-meter-60-v1/suite.json evaluation/runs/triple-meter-60-v1
4. node scripts/retry-double-ornament-trial.mjs triple-meter-60-v1
5. node scripts/report-memory-variation.mjs triple-meter-60-v1
6. node scripts/package-memory-variation.mjs triple-meter-60-v1
7. node scripts/audit-evaluation-bundle.mjs triple-meter-60-v1

Query, 삭제 근거, 원본 XML 앞뒤 문맥, event snapshot, 전체 검색 응답과 실행 지문은 evaluation/exports/triple-meter-60-v1에 보존한다. 보고 화면은 /evaluation/reports/triple-meter-60-v1/index.html이다.

## 상태

60회 모두 완료. 실행 오류/재시도 0건. 독립 사례 60개·XML 문맥 20개 검증 완료, 잘못된 alignment 인덱스 참조 0건. 이는 실제 강조 표시의 시각적 정확성까지 검증했다는 뜻은 아니다.

| 원형 길이 | 조건 | Top10 | 반환 100개 내 원본 회수 |
|---|---|---:|---:|
| 12 | 원형 | 10/10 | 10/10 |
| 12→11 | 음+음가 삭제 | 10/10 | 10/10 |
| 12→11 | 앞 음으로 음가 흡수 | 9/10 | 10/10 |
| 8 | 원형 | 10/10 | 10/10 |
| 8→7 | 음+음가 삭제 | 2/10 | 4/10 |
| 8→7 | 앞 음으로 음가 흡수 | 1/10 | 1/10 |

8→7 시간 축소에서는 Changing Partners 2위, CHIM CHIM CHER-EE 4위, ALWAYS WITH ME 27위, ARRIETTY'S SONG 28위였다. 시간 유지에서는 Changing Partners만 2위로 반환됐다. 나머지 여섯 원곡은 두 조건 모두 후보 목록에 없었다. 시간 유지의 추가 미회수 세 건은 후보에 존재하므로 선별 누락과 구분하여 후속 감사한다.

긴 Query는 이번 표본에서 안정적으로 회수되었지만 짧은 Query의 후보 누락은 남아 있다. 뒤 음 박자 위치 유지가 자동으로 성능을 높이지 않았으며 앞 음 음가 변경과 검색 경로를 함께 검토해야 한다. 다른 원곡을 쓴 앞선 4/4 결과와 비교해 박자 자체의 우열을 주장하지 않는다.

Exact 표시 상위 후보 130건 중 25건이 독립 음가/onset 감사에서 추가 검토 대상으로 표시됐다. 이는 오탐률이 아니며 기존 Exact 판정 검토 항목과 함께 보류한다. 상세 순위는 TIMING-COMPARISON.md, 실제 응답·Query·관찰·개선안은 독립 export에 저장했다. 운영 검색 변경 없음.
