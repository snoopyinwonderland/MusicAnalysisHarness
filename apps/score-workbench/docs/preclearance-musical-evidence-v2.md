# 사전검토 다층 음악 근거 v2

2026-09-16. 사용자 요청: Phrase/Motif 비교, 복수 Phrase의 비선형 집계, 독립 기둥음 후보, Contour·리듬형·음형, 기존 사이트 진입, 업로드 원곡 제외. 개발 후 최종 변형 Query 50개를 실행한다.

## 구현

- `server/preclearance-search.mjs`: 기본 Phrase-only. 최대 7개 Phrase 검색을 보존하고 combined 모드에서 최대 3개 Motif 검색을 추가한다. 같은 음형/음가 signature는 중복 검색하지 않는다. 48음 초과 Phrase는 25% 겹치는 창으로 나누고 parentUnitIds를 보존한다. 선별 상한과 저정보량 필터는 여전히 적용된다.
- `server/preclearance-musical-evidence.mjs`: 독립 기둥음 후보, 구간별 음악 특성, Phrase 가족 단위 집계.
- `server/preclearance-report.mjs`, `scripts/export-preclearance-report.mjs`: 전체 match JSON에 새 근거를 보존하고 대표 비교 카드에 표시한다. 원곡 제외는 source/work ID 또는 명시적으로 검증된 업로드→canonical 작품 연결만 사용한다. 제목만 같은 다른 곡은 제거하지 않는다.
- `src/components/PreclearancePage.tsx`: 기존 앱의 `/preclearance`와 상단 Copyright Check 메뉴. 샘플 보고서 인라인 보기/큰 화면 링크. 인증 없는 파일 업로드 기능은 추가하지 않았다.

## 음악 특성 계약

### 독립적인 구조적 골격 후보

전체 원본 성부 snapshot에서 먼저 후보를 추출하고, 비교 구간에 들어 있는 후보만 나중에 선택한다. 비교 대상의 음높이에 맞춰 건너뛸 음을 고르지 않는다. 주변 9개 이내 음의 중앙 음가에 비해 1.5배 이상 긴 음, 강박/부강박 지지, Phrase 종결 가설 중 2개 이상을 요구한다. 약박의 짧은 순차 통과/이웃음과 tie continuation을 제외한다. 박자는 명시된 beat와 meter를 사용하며 없으면 임의 4/4 강박을 만들지 않는다. 4/4와 복합박자의 위계를 구분한다.

각 구간에 3개 이상 후보가 있어야 골격 음정열 점수를 계산한다. 부족하면 null/미확인이다. 화성적 안정성·종지·성부진행·Ursatz는 미구현이며 **Schenker-informed proxy**이지 정식 셴커 분석이 아니다. 후보 ID·시점·음높이·선택 이유를 JSON에 보존한다. 점수는 구간 edit-distance 계열 비교이며 새 검색 후보를 임의로 생성하거나 직접 검색 점수를 끌어올리지 않는다.

### Contour / 리듬형 / 음형

- Contour: 상대 음역으로 정규화한 시간축 16표본 envelope와 실제 음표 S/U/D 진행의 편집 거리. 정점 위치 차이도 별도 기록한다.
- 리듬형: 음가 중앙값 기준 비율의 로그 차이와 음표/쉼표 순서를 비교한다. 균일 템포 확대에 불변이다. 쉼 위치는 16표본 점유 상태로 별도 비교한다.
- 음형: 연속 두 음정의 repeat, step, return, successive-leaps, mixed 배열을 비교한다. 분산화음의 화성적 역할을 확정하지 않는다.
- 이 수치는 **선택 구간**의 기보적 특성이지 전체 곡의 청각적 분위기 점수가 아니다. 흔한 음형의 높은 일치가 직접 선율 일치나 법률 판단을 대신하지 않는다. 메인 검색 순위는 변경하지 않았다.

### 복수 Phrase

전체 입력 성부에서 정규화된 음높이·음가·onset signature가 같은 Phrase는 같은 가족으로 묶는다. 변형 가족의 완전한 동등성 판정은 후속 과제다. 각 match가 Phrase 음표의 70% 이상을 덮고 직접 유사도가 70 이상일 때만 지지로 인정한다. 임계값은 미보정 초기값이다.

가족별 최대 `similarity × coverage`를 S_i로 둔다. 최고 S를 기본으로 하며, 나머지 가족 지지의 합 E = sum(S_i/100)에 대해 `bonus = (100-S) × 0.2 × (1-exp(-E))`를 별도 실험 점수에 더한다. 같은 가족 반복, 내부 Motif, 다른 판본의 같은 match는 횟수만큼 가산하지 않는다. beta 0.2는 잠정 상한이며 법률 확률이 아니다.

음표/음가 coverage는 입력 전체 성부의 합집합 기준이다. 보존되지 않은 query 발생 위치를 억지로 일치 처리하지 않는다. 각각 70% 미만인 여러 분할 창을 합쳐 완전 Phrase로 확정하는 기능은 아직 없으며, 보수적으로 미확인으로 남는다. 순서/인접성·코퍼스 특징성으로 추가 가산하는 것은 후속 검증 항목이다.

## 원곡 제외

`data/work-identities.json` uploadBindings에 사용자가 원곡이라고 확인한 sourceId/workId→canonicalWorkId 관계와 근거를 보존했다. index 지문 불일치 시 binding을 사용하지 않는다. 보고서 JSON의 selfExclusion에 제외한 작품을 기록한다. 미래 업로드의 정체를 제목만으로 추정하지 않는다. 새 업로드 원곡 ID를 확인할 수 없으면 다른 판본 제외는 미확정이다.

최신 샘플: `evaluation/reports/copyright-infringement-report-2026-09-16-v2/`. 기존 v1.9 분석 근거를 새 후처리로 출력했다. 원곡 3판본/23match 제외 후 25작품/33match, 대표 A/B 악보 50개가 남는다. 이전 보고서는 삭제하지 않았다. HTML은 로컬용이며 배포 build에 evaluation 자산이 자동 포함되는 것은 아니다.

## 검증과 실행

개발 검증: 관련 131개/14파일 회귀 통과, TypeScript 및 Vite build 통과. 원곡 제외·50개 비교 악보·강조 ID·합성음 스케줄/취소 검증 완료. 진입 화면과 보고서 스크린샷은 샘플 폴더에 보관한다. 기존 Verovio chunk 경고는 남는다.

```powershell
node scripts/run-preclearance-search.mjs PREPARED.json NEW-report.json --mode=phrase
node scripts/run-preclearance-search.mjs PREPARED.json NEW-report.json --mode=combined
node scripts/compare-preclearance-modes.mjs evaluation/runs/preclearance-structure-2026-09-14.json NEW-ab-directory
node scripts/run-preclearance-variation50.mjs evaluation/runs/preclearance-review-diverse-2026-09-15/suite.json NEW-50-directory
```

A/B는 공유 Phrase 결과를 그대로 재사용한다. 시간은 A 총시간과 B 추가 비용으로 기록하며 독립 cold A/B가 아니다. 동일 총 task budget 실험과 음악 전문가의 오탐 판단은 구분한다.

50개는 5개 서로 다른 source 구간 × 원형/전조/전체 옥타브/한 음 옥타브/반음 변경/두 음 변경/전체 음가 2배/한 음 음가 변경/쉼 삽입/중간 음 삭제의 paired 구성이다. 전체 corpus의 대표 표본이 아니다. suite.json에 Query·원본 음표·앞뒤 문맥·분류·사람 검토 필드, 사례 JSON에 실제 전체 검색 결과와 alignment, summary.json/report.md에 순위·시간·문제/개선 후보를 보존한다. 원본 회수 확인을 위해 이 일반 검색 테스트에서는 원곡을 제외하지 않는다.

`preclearance-variation50-2026-09-16`은 사용자의 개발 우선 지시에 따라 중단한 조기 실행이며 최종 평가에 섞지 않는다. 최종 실행 경로는 `preclearance-variation50-final-2026-09-16`. API alignment 참조 검사와 실제 SVG 렌더링/음악적 정당성 검토는 서로 다르다.
