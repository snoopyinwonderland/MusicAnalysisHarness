# Search Evaluation Case Knowledge Base

## 2026-09-16 추가 평가 연결

2026-09-17 짧은 Query 90회 완료: evaluation/exports/short-query-90-v1/index.json. 10곡의 12/8/6음 paired 원형·변형, 30개 공유 XML 문맥, 전체 응답·재시도·선별/변형 감사·Exact 진단을 포함한다. 작품 회수와 원본 파일 순위, 자동 관찰과 확정 음악적 판단을 구분한다. 상세: docs/short-query-90-v1.md.

기억 입력 변형 50개와 대조 15개: evaluation/exports/memory-variation-50-v1/index.json이 독립 사례 묶음 진입점이다. cases/에는 전체 Query·변형 설명·원본 좌표·실행 결과 참조, base-assets/에는 공유 원본 MusicXML(앞뒤 최대 2마디)과 이벤트 snapshot을 둔다. 모든 케이스는 기존 musicanote-evaluation-case/v1 검증을 거친다. 수집 단계의 pending와 실제 실행 완료 상태를 구분한다. 결과/개선 검토는 docs/memory-variation-50-v1.md.

Phrase/Motif A/B: `evaluation/runs/preclearance-phrase-motif-ab-2026-09-16/` 및 [비교 해석](preclearance-phrase-motif-ab-2026-09-16.md).

최종 paired 변형 50개: `evaluation/runs/preclearance-variation50-final-2026-09-16/`. 평가 후 `scripts/package-variation50-evidence.mjs`로 기존 `musicanote-evaluation-case/v1` 스키마의 사례 파일, 5개 공유 원본 XML/이벤트 문맥, Query별 상위 결과와 개선 후보를 `evaluation/exports/preclearance-variation50-2026-09-16/`에 정리한다. 자동 분류는 automatic-unreviewed이며 음악적 정당성 라벨을 임의로 채우지 않는다. 조기 중단한 비-final 실행은 최종 통계에서 제외한다.

사용자가 제시한 미묘한 음악적 판단을 단순 메모나 특정 작품 예외가 아니라 재현 가능하고 유형화 가능한 증거로 보존한다.

## 한 사례의 세 층

1. `evaluation/cases/<case>.json`: 원본 Query, 사용자 설명, 기대 결과, 진단, 제안, 실행 이력과 유형화 메타데이터의 정본이다.
2. `evaluation/case-assets/<caseId>/context.musicxml`: 일치 구간과 기본 앞뒤 2마디를 포함한 독립 재현용 MusicXML이다. 음높이·음가뿐 아니라 조표, 박자, 음자리표, 쉼표, tie와 표기 spelling을 보존한다.
3. `evaluation/case-assets/<caseId>/events.json`: 검색과 규칙 학습용 event snapshot이다. work/source/stream, part, staff, voice, measure label/ordinal, beat, onset, duration, pitch, spelling, tie, target 좌표를 기계 판독 가능하게 둔다.

MusicXML은 표기 재현의 정본이고 event snapshot은 비교·검색·통계용 파생 자료다. Music Analysis의 전체 Canonical IR을 복제하지 않는다. 향후 Canonical IR의 안정된 note/event ID가 제공되면 `identity`와 각 event에 외부 참조를 추가한다.

## 유형화와 룰 학습

`knowledgeBase.classification`은 다음을 분리한다.

- `phenomenonTypes`: tie, passing-note, phrase-boundary, sparse-alignment, downbeat-overaccent처럼 관찰된 현상
- `musicalFunctions`: pillar, passing, neighbor, anticipation, phrase-ending carryover 등 사람이 검토한 기능
- `contextualConditions`: 이 판단이 성립하는 박자·성부·프레이즈·화성·반복 조건
- `exclusions`: 겉모양은 비슷하지만 같은 규칙을 적용하면 안 되는 조건
- `confidence`: unreviewed, user-confirmed, analyst-confirmed, corpus-validated

`knowledgeBase.ruleLearning`에는 일반화 후보와 반례를 함께 둔다. 규칙은 최소한 `if`, `then`, `because`, `evidenceTargets`, `scope`, `exceptions`, `confidence`를 가져야 한다. 특정 `workId`나 고정 음표열은 production 조건으로 사용하지 않고 회귀 fixture의 증거로만 쓴다.

## 문맥 캡처

```powershell
pnpm harness:capture-context -- --case Q-P1-006 --work work-af9d06a2cc0ef485-a71ddd21 --start 23 --end 29 --before 2 --after 2 --targets "88:68,90:68,92:70"
```

- 기본 문맥은 앞뒤 2마디다. 프레이즈 경계나 tie가 범위를 넘으면 필요한 만큼 늘린다.
- 기존 asset을 실수로 덮어쓰지 않는다. 원본 또는 인덱스가 바뀌어 의도적으로 새 snapshot을 만들 때만 `--force`를 사용한다.
- SHA-256 지문으로 MusicXML과 event snapshot의 출처 변화를 추적한다.
- 캡처 후 사람은 `musicalFunctions`, `contextualConditions`, `exclusions`, `candidateRules`, `counterexamples`를 검토한다. 자동 추론값을 사람의 확정 판단으로 취급하지 않는다.

## 재사용

- 검색 후보 회수·순위 A/B 회귀
- target 음표 및 tie/성부 강조 회귀
- 유사 현상별 사례 검색
- 규칙 후보의 양성 사례와 반례 비교
- 향후 phrase/structural layer 및 Canonical IR과 연결

새 사례는 완전한 Query와 정확한 work/stream/마디/target 좌표가 확보되는 즉시 캡처한다. 좌표가 불완전한 과거 사례는 추측해서 채우지 않고 `draft`로 유지한다.

## 신규 테스트의 필수 보존 규칙

- 이후 자동/사용자 Query 테스트는 보고서만 작성하지 않고 독립 case JSON도 남긴다. 사용자 설명, 자동 관찰, 진단 가설, 검증된 해결 방법을 서로 다른 필드로 구분한다.
- 실행 전 원형/변형 Query, 변형된 event ID, 변형 규칙, 기대 원본 좌표를 확정한다. 실행 후 전체 응답, 순위, 음표 정렬, 오류/재시도, 알고리즘·DB 지문을 추가한다.
- MusicXML과 event snapshot은 앞뒤 문맥을 포함하고 해시를 보존한다. 보고용 악보 재기보는 원본 XML을 대체하지 않는다.
- cases, base-assets, runs, suite.json, index.json을 같은 export batch에 넣어 폴더째 이동할 수 있게 한다. 같은 원형의 XML은 공유한다.
- 자동 검색 성공을 사람의 음악적 정당성 판단으로 표시하지 않는다. 미검증 개선안은 proposed-not-implemented로 남긴다.
- 과거 모든 대화가 동일 형식으로 완전 이관되었다고 가정하지 않는다. 누락 정보는 비워 두고 기존 보고서/Query 파일의 출처를 연결한다.

## 자동 Motif Harness

자동 변형 Query에도 동일한 `knowledgeBase` 계약을 적용한다. 같은 원형에서 나온 pitch·octave·rhythm·leap·rest 변형 다섯 개는 동일한 원본 문맥을 공유하므로 MusicXML을 중복 저장하지 않고 `base-assets/Bxxx` bundle 하나를 참조한다.

```powershell
pnpm harness:capture-motif-contexts -- --suite motif-350 --before 2 --after 2
```

자동 선택 원형과 자동 구조 해석은 사람의 음악적 판정이 아니다. 따라서 `confidence: automatic-unreviewed`와 제외 조건을 유지하며, 사람이 확인한 뒤에만 음악적 기능과 후보 규칙을 채운다.
