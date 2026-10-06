# Phrase 기반 Motif 분석 v1 — 2026-09-21

## 목적과 요청

기존 유사도 비교의 장점은 유지하되, 제한적인 exact-repeat/5음 rhythm-cell 후보 생성으로 음형을 누락하는 문제를 줄인다. 사용자 요청은 Phrase 안에서 Motif를 나누고, 앞의 Motif 재등장을 뒤의 Phrase에서도 인식하는 것이다. 화성 사례의 활용 가능성도 함께 검토한다.

## 실행 계약

- 화면의 buildMotifSpans에 Phrase가 전달되면 `src/music/phraseMotifs.ts`의 phrase-first-v1 경로를 사용한다. Phrase가 없는 호출만 기존 경로를 유지한다. 기존 회귀는 별도 경로임을 구별한다.
- 모든 비어 있지 않은 선율 Phrase에 전체 구간 후보를 만든다. 4음 미만이나 단순 반복음도 제거하지 않는다. 내부 분할을 못 하면 `phrase-whole-unresolved`이며 확정 Motif가 아니다. 화면 상세에 “Phrase 전체 · 내부 분할 보류”를 표시한다.
- 내부 cut는 양쪽에 최소 세 attack을 남기는 지점에서 생성한다. 주변 음가 중앙값 unit 대비 실제 gap >= max(0.5 quarter, unit), 또는 앞 음가 >= max(1 quarter, 2*unit)가 후보 근거다. 타이 합산 음가가 전달된 단일 선율 stream을 전제로 한다.
- 긴 음만으로 자르지 않는다. 양쪽 하위 구간 모두 다른 비중첩 구간과 반복/변형 대응이 있거나 실제 gap이 있을 때만 분할한다. gap 우선, 양쪽 반복 지지 다음, 동률은 중앙에 가까운 cut를 선택하는 결정론적 휴리스틱이다. 재귀 깊이 8 제한.
- 전체 Phrase 후보와 cut 사이 3–32 attack의 후보를 작품 전체에서 비교한다. 과거 64 attack 제한과 상승/하강·음정 다양성 제외 규칙은 새 경로에서 사용하지 않는다. 같은 Phrase 내부 비중첩 반복도 비교한다.
- 기존 compareMotifs의 삽입/삭제 허용 정렬, 멜로디·음형·리듬·coverage를 재사용한다. 대응 기준은 combined >=84, coverage >=70, melodic >=85, shape >=80. 미보정 휴리스틱이며 확률이 아니다.
- 부분 후보 pool 400, 비교 20,000회 제한(전체 Phrase 후보는 항상 보존). 한도 도달 시 searchTruncated로 명시한다. 시간 제한/불완전 탐색은 미반복의 증거가 아니다.
- 표시 가족은 시간 순서대로 기존 대표와 비교하여 번호를 공유하고 변형별 번호를 만든다. 현재 실행의 작품 내부 메모리이며 재학습/영구 Case Retrieval이 아니다. 각 구간에 parentPhraseNumber, analysisScope, algorithmVersion, recurrenceEvidence를 보존한다.
- Phrase 경계 자체 및 Core/XML은 변경하지 않는다. v1에서는 Phrase를 가로지르는 Motif를 만들지 않는다. 공유음, 경계 오류, 준비음이 앞 Phrase에 놓인 경우는 향후 복수 span 해석 대상으로 남긴다.

## 화성 사례

많은 사례를 저장하는 것만으로 자동 향상되지는 않는다. 원본 문맥·안정 ID·사용자 설명·대안·화성 가설과 검토 상태를 함께 보존하고, 경계/비경계의 대조 사례에서 규칙을 추출한 뒤 독립 작품으로 검증해야 한다. 같은 작품의 다른 판본은 train/test로 나누지 않는다.

유용한 대조: 같은 리듬과 도착음이지만 종지로 닫히는 경우 / 화성이 지속되어 이어지는 경우, 긴 음이 있어도 비화성음 해결이 남은 경우, 반복 음형 내부의 화음 변화. Harmony confidence와 engine version을 기록하고 불확실한 분석을 hard boundary로 사용하지 않는다. Prolongation은 단순 음가 증가와 구별한다. 화성 변화가 Motif 경계의 필수조건도 아니다.

이번 버전은 화성 라벨을 점수에 연결하거나 사례로 학습하지 않는다. 먼저 Phrase 내부 후보 생성과 재등장 회수를 검증한다.

## 검증과 한계

실행 결과: 관련 8개 테스트 파일/61개 테스트 통과, TypeScript 검사 및 프로덕션 빌드 통과. 기존 Verovio 외부 모듈/번들 크기 경고는 남아 있다.

신규 합성 테스트는 전체 Phrase fallback, 한 Phrase 내 반복, 긴 음만으로 오분할 방지, 64 attack 이후 조옮김/음가 변형, 단순 반복음, 원본 불변/범위 보존을 확인한다. 저장된 S-STRUCT-004 XML/event snapshot을 재사용하여 실제 화면 호출 경로에서 Phrase 전체의 빠짐없는 비중첩 범위 보존을 확인한다.

범위 보존은 음악적 정확도 검증과 다르다. 기존 3-3 등 번호와 분할은 새 후보 생성으로 바뀔 수 있다. beam 묶음, 화성 종지, prolongation-aware alignment, gold-label 정확도 및 브라우저 시각 검증은 이번 테스트가 보증하지 않는다. 다음은 기존 사용자 사례들의 새/옛 결과를 나란히 검토하고 잘못된 split/merge를 별도 기록하는 것이다.
