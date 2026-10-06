# 6/8·3/8 장식음 삭제 검증

2026-09-17 사용자 승인. 박자별 새 원곡 5개씩, 12/8음 × 원형/음+음가 삭제/삭제 후 앞 음에 음가 흡수 = 60회 계획. 원형은 검색 전에 XML만으로 선정한다. 후보가 부족하면 다른 박자로 채우지 않는다.

- 기존 harder-100, short-query-90, triple-meter-60 원곡 제목을 제외한다. 같은 성부·연속 attack와 XML 좌표 대응이 명료한 구간을 사용한다.
- 6/8은 기존 선별기의 3+3 묶음, 3/8은 기존 세 개 8분음표 단위 처리를 그대로 평가한다. 3/8을 빠른 한 박으로 느끼는 해석까지 검증하는 것은 아니다. 약박의 짧은 경과음/보조음은 국소 후보이며 화성 분석 확정값이 아니다.
- 모든 음가는 4분음표 단위로 보존한다. 삭제 음가 흡수는 뒤 음 onset을 유지하지만 앞 음의 길이를 바꾸므로 순수 박자 위치 효과라고 단정하지 않는다.
- 박자별 독립 원곡은 5개다. 변형 30회를 서로 독립인 음악 30개로 계산하지 않는다. Top10을 긍정적으로 평가하고, 8→7음은 경계 사례로 다룬다. 원본 파일 회수와 작품/반복 구간 회수는 구별한다.
- 운영 검색 로직과 DB는 변경하지 않는다. 개선안은 보류 목록에 모은다.

## 재현

1. node scripts/build-eighth-meter-suite.mjs
2. node scripts/audit-eighth-meter-suite.mjs
3. MUSICANOTE_SINGLE_OMISSION=1, MUSICANOTE_VISIBLE_RANKING=0; node scripts/run-structural-next40.mjs evaluation/reports/eighth-meter-60-v1/suite.json evaluation/runs/eighth-meter-60-v1
4. node scripts/finish-eighth-meter-evaluation.mjs — 실행 오류 재시도, 악보·순위, Exact/후보 진단, 박자별 비교, 독립 XML·Query·결과 보관과 검증.

결과 페이지: /evaluation/reports/eighth-meter-60-v1/index.html

박자별 표: evaluation/reports/eighth-meter-60-v1/TIMING-COMPARISON.md

독립 사례: evaluation/exports/eighth-meter-60-v1

## 상태

60회 모두 완료. 첫 원형 시간초과 1건은 별도 180초 재시도에서 35초에 완료되어 원본 1위였다. 최종 실행 오류 0건, 독립 사례 60개와 원형별 XML/event 문맥 20개 검증 완료. 최초 오류 응답도 보존했다. 잘못된 alignment 인덱스 참조 0건은 실제 시각적 강조의 정확성 검증과는 구별한다.

| 박자 | 원형 길이 | 원형 Top10 | 삭제·시간 축소 Top10 | 삭제·음가 흡수 Top10 |
|---|---:|---:|---:|---:|
| 6/8 | 12 | 5/5 | 3/5 | 4/5 |
| 6/8 | 8 | 5/5 | 0/5 | 0/5 |
| 3/8 | 12 | 4/5 | 3/5 | 3/5 |
| 3/8 | 8 | 4/5 | 0/5 | 0/5 |

100위 내 회수는 6/8의 12음 삭제 두 조건 각각 4/5, 8음 삭제는 시간 축소 1/5·음가 흡수 2/5였다. 3/8은 12음 삭제 각각 3/5, 8음 삭제 각각 0/5였다. 8→7음은 경계 사례로 보존하며 미회수 자체를 모두 오류로 판정하지 않는다.

중요 진단: EM09 베토벤 소나타 10번 3악장은 원형부터 미회수였다. 12음 원형은 hit 목록에는 있지만 candidate 목록에서 빠졌고, 8음 원형은 hit 목록부터 없었다. 장식음 삭제 내성 문제로 합산하지 말고 후보 회수/좌표/stream 검증을 우선한다. EM03 12음 삭제는 두 조건 모두 low-information-floors 제외 근거가 있고, EM08 12음 삭제는 후보 평가와 admission-floor 제외 근거가 있다. 세부 원인은 추가 검토 대상으로 남긴다.

박자별 원곡 5개 편의 표본이며 서로 다른 원곡이므로 3/4 대비 박자 자체의 성능 저하라고 단정하지 않는다. Query·전체 응답·실행 지문·XML·음표 이벤트·순위·관찰·개선 후보는 export bundle에 보관했다. 검색 로직/DB 변경 없이 개선안은 계속 보류한다.

- 6/8: Ennio Morricone Medley, GAME OF THRONES, LET THERE BE PEACE ON EARTH, March Medley, My Favorite Things.
- 3/8: HE WAS BEAUTIFUL, Für Elise, Hedwig's Theme, Beethoven Piano Sonata No.10 Op.14 No.2 3rd, Piano Sonata No.12 Op.26 1st.
- 위 명칭은 데이터베이스 판본의 제목이며 원전의 모든 구간이 해당 박자라는 뜻은 아니다. 선택된 구간의 XML 박자만을 기준으로 한다.
