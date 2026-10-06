# Phrase v1.11 — 짧은 내부 쉼과 지속 종결의 우선순위

검증: 관련9개 파일66개 테스트 및 TypeScript/프로덕션 빌드 통과(기존 Verovio 외부모듈/큰 번들 경고 유지). S-STRUCT-005 변경 후 초반 경계 index는15,20,33,46,56,66,79,84,92,97,104이다. 초반과77→79 반복 오류는 수정됐으나 후반84 등은 남아 재검토 대상이다. 기존 번호8–11 전체가 해결되었다고 해석하지 않는다.

2026-09-21. 사례: [S-STRUCT-005](../evaluation/cases/s-struct-005-review.md).

## 원인

관측 gap 점수는 주변 음 간격에 비례하므로 16분음표가 이어질 때 16분 쉼도 강한 경계가 된다. 뒤의 minimum-attack 후처리가 이 잘못된 경계부터 음수를 세고 진짜 종결 뒤 경계를 지운다. Motif가 Phrase 안에서 계산되므로 상위 경계 오류가 하위 분석에도 전달된다.

## 수정

`suppressShortArticulationBeforeArrival`를 minimum-attack 후처리 전에 실행한다. 0보다 크고 0.5 quarter 이하의 gap, 직전 음가 0.5 이하인 강한 경계만 검토한다. 다음 최대12 이벤트/8 quarter 안에 도착음 길이 >=max(1, 직전음가*3)이고 뒤 gap >=max(0.5, 첫gap*2)이 있으면 앞 경계를 내부 articulation 후보로 낮춘다. 명확한 별도 silence를 넘어 먼 종결을 근거로 병합하지 않는다. 입력 onset이 원본에 있어야 하며 원본 음가/타이는 바꾸지 않는다.

rawStrength와 `short-articulation-continuation` cue에 도착음 index, 양쪽 gap, rule ID를 보존한다. 명시적 호흡 근거가 있으면 억제하지 않으며, 최종 breath-symbol 처리도 유지한다. 기준은 초기 휴리스틱이고 cadence/반음 해결을 판단한 것이 아니다. Beam 그룹을 파싱해 판단한 것으로 주장하지 않는다.

새 규칙은 짧은 음/쉼을 모두 금지하지 않는다. 가까운 지속 종결과 더 강한 쉼이 없으면 기존 경계를 유지한다. 종결이 아닌 짧은 음 뒤 실제 Phrase 단절 등 반례는 추가 검토해야 한다. 이번 사례의 후반 모든 경계가 정답이라는 주장은 하지 않는다.
