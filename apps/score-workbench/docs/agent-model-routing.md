# 작업별 에이전트·모델 라우팅

이 문서는 비용을 아끼면서 검색 품질을 보존하기 위한 프로젝트 규칙이다. 모델을 낮추더라도, 음악적 판단과 검색 규칙 변경의 검토 기준을 낮추지 않는다.

## 고정 역할

| 역할 | 사용자 에이전트 | 모델·reasoning | 허용 작업 |
|---|---|---|---|
| 회귀 테스트 | `musicanote_regression_tester` | GPT-5.6 Terra / medium | 고정 suite 실행, 순위·정렬·악보 렌더링 감사, 증거 묶음과 이슈 handoff 작성 |
| 검색 규칙 변경 | `musicanote_search_rule_engineer` | GPT-5.6 Sol / high | Terra handoff을 근거로 일반화된 규칙 수정, 음성 대조군·회귀 검증, 문서화 |
| 일일 수집 | 예약 작업 `ky` | GPT-5.6 Luna | KY·YouTube의 정해진 수집, 중복·한도·로그 처리. 음악적 판정이나 알고리즘 변경 금지 |

에이전트 정의는 `.codex/agents/`에 둔다. 해당 파일의 명시 모델은 일반 subagent 기본값보다 우선한다.

## 회귀 → 규칙 변경 handoff

1. Terra 테스트 에이전트는 변경 전의 고정 Query·원형 XML·실행 지문·전체 응답을 보존한다.
2. 회귀가 발견되면 `caseId`, 검색 mode/options, 기대·실제 rank, candidate admission 여부, 점수·정렬 근거, 악보 표시 상태, 일반화 가설을 handoff에 적는다.
3. Sol 규칙 엔지니어는 제목·작품·특정 Query를 고정하는 변경을 하지 않는다. 최소 한 개의 음성 대조군과 기존 suite 재실행으로 tradeoff를 확인한다.
4. Terra가 변경 후 같은 suite를 재검증하고, 결과와 남은 한계를 개발 로그·평가 보고서에 남긴다.

현재의 세 소규모 회귀 테스트도 이 절차를 따른다. 단순 실행은 Terra가 맡고, 실제 규칙 변경은 재현 가능한 실패가 확인된 경우에만 Sol로 넘긴다.
