# S-STRUCT-006 반복 구조 비교 기준 — 2026-09-22

기준 디렉터리: ../case-assets/S-STRUCT-006/phrase-structure-v1-baseline/.
baseline.json은 보존된 원본 snapshot을 local-boundary-evidence-v1.14로 재분석한 결과이다. live 화면을 캡처한 것과 구별한다. source hash와 engine hash, source XML/입력 경로 및 현재 Phrase번호→event ID가 기록되어 있다. 기존 snapshot/XML은 수정하지 않았다.

| 비교 구간 | index 반열린 범위 | 기보 위치 |
|---|---|---|
| 기준 Phrase1 | [0,13) |4–6마디|
| 기준 Phrase2 | [13,29) |8마디–11마디 타이 지속 끝|
| 기준 Phrase3 | [29,42) |12–14마디|
| 검토 Phrase4 | [42,51) |16–17마디|
| 검토 Phrase5 | [51,57) |17–18마디|
| 사용자 병합안 | [42,57) |16–18마디|

baseline의 endMeasure는 마지막 attack의 기보 마디이다. Phrase2 마지막 attack은10마디이고 tie는11마디까지 지속한다. UI용 sounding 종료 표시는 별도 tie 참조를 사용해야 한다.

원본 관찰: 4/8/12/16마디의1차beam에는 각각3개와4개의음표로 된 완결 묶음이 존재한다. 이 관찰은 공통 도입부 가설을 지지하지만 Phrase4+5 병합의 충분조건은 아니다. 연결부 쉼과 변형 후반은 다음 정렬 단계에서 검증한다.

추출: 선율431/431 source event 매핑, 전체 선택 voice beam group122개, adapter warning0개. 음표 source ID는 동일 XML byte에서 재현되며 수정판 사이 ID 유지 계약은 아니다. 사용자 ‘합치는 것이 좋다’는 검토 선호이고 자동승인/gold label로 바꾸지 않았다.
