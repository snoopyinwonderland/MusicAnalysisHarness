# 구조 변형 검색 1단계: 독립 국소 축약 모듈

2026-09-15. 사용자 요청: 연구 기반 일반 규칙 설계를 구현하기 시작한다.

## 구현과 적용 범위

- `server/structural-reduction.mjs`: 원본과 무관한 상대 곡/Query 입력 없이 분석한다. production 검색에서는 import하지 않는 실험 모듈이다. 기존 점수·후보 인덱스·DB는 변경하지 않았다.
- `normalizeStructuralSource`: 명시적인 sourceHash/event ID/part/voice/staff/time을 요구한다. 원본 속성 및 악보 ID를 복사 보존한다. 없는 박자나 시작 시점을 추측하지 않는다.
- 시간은 `{n,d}` 또는 정확한 소수 값을 사용한다. 1/3은 유리수로 전달해야 하며 .33203125를 임의로 1/3으로 고치지 않는다.
- `beatQ`는 마디 시작 기준 0-based quarter 단위다. 기존의 1-based beat 필드를 그대로 넣으면 안 된다. 외부 입력 어댑터는 다음 단계에 필요하다.
- tieChainId가 있고 동일 pitch/staff의 연속 시간과 continuation이 검증된 경우만 합친다. 모든 sourceEventIds/xmlNoteIds를 보존한다. cross-staff tie는 이번 구현에서 보류한다.
- metricSupport는 2/3/4박, 6/8·9/8·12/8, 명시 grouping을 지원한다. 6/4·불명확한 혼합박 및 pickup은 추정하지 않는다. 외부 meter timeline을 event별로 해석하는 어댑터는 아직 없다.
- local passing/neighbor 후보는 끝점 지지, 상대 음가/박자, 화성 문맥, phrase 보호, 반복 특징음 보호를 검사하고 blocked 이유도 기록한다.
- L1 실제 축약은 알려진 diatonicPitch와 높은 확신의 동일 화성/비화성 내부음 관계가 있을 때만 허용한다. 다른 경우 provisional 기록만 만들고 L0를 유지한다.
- high-confidence harmony/phrase 입력은 외부 분석의 가설이지 이 모듈이 생성한 정답이 아니다. 실제 DB에서 이런 필드를 확보하는 일은 미완료다.
- 원본 L0와 하나의 충돌 없는 L1만 반환한다. 반복 축약, L2, 장거리 관계, 고급 성부진행은 구현하지 않았다. 최소 기둥 수를 채우지 않는다.

## 검증

실행: `node node_modules/vitest/vitest.mjs run server/structural-reduction.test.js server/preclearance-musical-evidence.test.js`

신규 14개 + 기존 7개 테스트. 다음 반례를 포함한다: 잘못된 시간, part/voice 누락, 복합박·혼합박·pickup, 화성/표기 부재, 주요 음 보호, 화성 변화, gap/overlap, phrase 경계, 불명확한 attack, 성부/staff 혼합, 쉼표, 반복음, 타이 연결, 강박만 있는 선율, 원본 불변, 전체 옥타브 이동 불변성, 동시음 겹침.

이 테스트는 규칙 계약과 재현성을 검사한 것이며 실곡 검색 성능 개선을 입증한 것이 아니다. 아직 신규 100개 Query 검색이나 Verovio 시각 검증은 하지 않았다.

## 재현용 데이터와 다음 단계

반환물은 JSON 직렬화 가능하며 원본 source, soundingEvents, issues, anchors, relations, alternatives를 포함한다. 삭제된 원음은 relation.originalEventIds와 source.events로 복원된다. 출력은 소리/악보 파일 그 자체가 아니며 원 XML 또는 표기 어댑터와 연결해야 한다.

다음: 기존 DB/원 XML → 명시적 source 계약 어댑터, 문맥과 화성 가용성 감사 → 원본 20개 선별 및 기둥 보존 변형 100개/대조군 생성 → 기존 검색 baseline → 후보 인덱스 파일럿. 화성 정보가 없는 원본을 조용히 제외하여 성공률을 높이지 않고 가용성/보류율을 함께 보고한다.

설계 원문: [일반 규칙과 연구](structural-melody-search-rules-v1.md). 이 단계는 해당 문서 13장의 일부 구현이며 전체 분석기 완료가 아니다.
