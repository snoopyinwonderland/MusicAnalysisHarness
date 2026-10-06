# Query 복사·붙여넣기

2026-09-17 사용자 요청. 테스트 결과의 원형/입력 Query 악보에 JSON 복사와 간단 표기 복사를 추가했다. 최근 5배치 305개 사례 페이지에 적용했고 공통 보고서 생성기도 갱신했다. 검색 응답·순위·원본 suite는 변경하지 않았다.

## 사용

- 검색 페이지의 Query 붙여넣기 → 내용을 붙임 → Query 불러오기. 검색은 자동 실행하지 않는다.
- JSON: schema=musicanote-query wrapper 또는 version=1 Query 객체를 지원한다. mode·meter·음표·쉼표·정확한 durationRatio·spelling·타이·잇단음표·상세 옵션을 읽는다. 이전 입력과 옵션은 Undo/Redo로 복원한다.
- 간단 표기: C4(0.5)-D♭4(1)-쉼표(0.5)-G4(2). 괄호는 4분음표=1박 기준이며 1/2는 0.5박이다. R/Rest/쉼표, #/♯/b/♭, C#4/C4#을 지원한다. 끝의 -는 허용한다.
- 간단 표기는 현재 mode·meter를 사용한다(contour 모드에서는 melody_rhythm으로 전환). 타이·잇단음표의 기보 관계 및 상세 옵션은 표현하지 않으므로 보존하려면 JSON을 사용한다. 간단 복사도 실제 durationRatio를 보존하며 음가를 반올림하지 않는다.
- 과거 테스트에 새 단순 패턴 허용 필드가 없으면 UI에서 두 허용 옵션은 false로 복원한다. 베토벤 EM09를 검색하려면 연속 순차 진행 검색 허용을 체크한다. 기존 Harness 실행 기록 자체는 바꾸지 않는다.
- 잘못된 JSON/음높이/음가/중복 ID는 현재 입력을 덮어쓰기 전에 오류를 표시한다. 붙여넣기에는 클립보드 읽기 권한이 필요 없다. 테스트 페이지 복사 권한이 없으면 선택 가능한 텍스트 영역을 제공한다.

## 검증

- npx vitest run src/music/queryImport.test.ts scripts/query-roundtrip.test.mjs src/music/queryEdit.test.ts: 17개 테스트 통과. 저장된 305개 Query의 JSON·간단 표기 왕복에서 음높이·음가·쉼표 동일 확인.
- npm run build 통과. 보고서 복사 스크립트 구문·중복 적용·script 종료 문자열 escaping 검증 포함.
- 브라우저에서 실제 클립보드 클릭과 Undo/Redo를 수동으로 확인하는 검수는 남아 있다.
