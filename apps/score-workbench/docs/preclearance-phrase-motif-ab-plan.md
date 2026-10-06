# Phrase/Motif 비교 및 복수 프레이즈 근거 집계 계획

2026-09-15 사용자 요청: Phrase는 비교적 안정적이나 Motif 분석은 개발 중이므로 Phrase-only와 혼합 검색을 비교한다. 여러 프레이즈 일치를 단순 배수로 계산하지 않는다. 기존 검색 사이트 상단 메뉴로 분석 화면에 진입한다.

## 확인한 현재 상태

- structure-analysis-adapter.mjs의 structureSearchQueries 기본 kinds는 phrase와 motif 모두다. 외부 프로젝트 분석기를 운영 연동한 것이 아니라 현재 저장소 로컬 어댑터를 사용한다.
- preclearance-search.mjs는 7~48음, 저정보량 제외, 중복/겹침 억제 후 최대 7개를 선정한다. 두 종류가 같은 budget을 경쟁한다.
- 작품 coverage는 query event ID 합집합, priority는 maximum-not-sum이다. 복수 독립 Phrase의 추가 근거는 아직 별도 보정하지 않는다.

## 제안 실험 (아직 실행 전)

1. 같은 입력 snapshot/분석 버전/DB/검색 설정으로 Phrase-only A를 실행한다. 긴 Phrase는 삭제하지 않고 겹치는 검색 창으로 분할하되 원래 Phrase ID를 유지한다. 경계 불확실성도 기록한다.
2. B는 A의 Phrase를 그대로 유지하고 Motif 후보를 추가한다. Phrase가 Motif에 밀려 빠지지 않게 한다. 중복 작업은 재사용하되 처리시간은 cold/warm 및 총 추가 비용을 분리한다.
3. 같은 총 task budget 비교도 별도로 기록한다. B의 향상이 단순 검색량 증가 때문인지 구분한다. Motif-only는 선택적 진단군이지 제품 기본이 아니다.
4. 검색 회수·사람 검토 상위 후보의 적절성·새로 찾은 유효 구간·흔한 음형 오탐·시간·강조 정합성을 비교한다. 특정 작품 순위를 고정하지 않는다.
5. 잠정 제품 기본은 Phrase-only 권고. Motif는 충분한 이득이 검증되면 보조 후보 생성으로 사용하고 독립 침해 근거처럼 합산하지 않는다. 아직 기본값은 변경하지 않았다.

## 복수 구간 집계 설계

원본 Phrase ID, query/candidate event ID, 구간 좌표, 작품/판본 ID를 보존한다. 동일 Phrase의 분할 창, 내부 Motif, 반복 판본과 같은 부분의 중복 검색은 하나의 증거 가족으로 묶는다.

보고서는 최고 구간 유사도, 중복 제거 음표/시간 coverage, 서로 다른 Phrase 가족 수, 반복 횟수, 순서/연속성, 대상 성부 내 비중을 분리한다. 같은 Phrase가 두 번 반복된 경우와 서로 다른 두 Phrase가 일치한 경우를 구분한다. 같은 음형의 다른 작품 일치는 한 작품에 합산하지 않는다.

실험용 순위는 최고 근거를 기본으로 하고 두 번째 이후의 새 coverage·특징성에 한정해 포화되는 보너스를 검토한다. 예: S + (100-S) * beta * (1-exp(-E)); E는 중복 제거 추가 근거, beta는 전문가 사례로 보정할 상한이다. 이는 제안 휴리스틱이며 확률/법률 점수도 아니고 아직 구현한 공식도 아니다. 순서 일치는 보강 근거이지 순서 변경 사례의 탈락 조건이 아니다. 현재 source 빈도는 canonical 작품 희귀도와 다름에 주의한다.

## 문서 유사도 검사에서 참고한 범위

- Crossref/iThenticate: 일치 텍스트 비율과 표절 판단을 구분한다. https://www.crossref.org/documentation/similarity-check/similarity-report-understand/
- PAN Text Alignment: 구간 precision/recall 및 하나의 사례를 여러 조각으로 검출하는 granularity를 평가한다. https://pan.webis.de/clef14/pan14-web/text-alignment.html
- 이 원칙을 음표/시간 합집합과 증거 가족에 적용하되 문서 점수나 내부 알고리즘을 음악 침해 판정에 그대로 이식하지 않는다.

## 사이트 통합 계획

별도 사이트가 아니라 기존 앱 상단 Copyright Check 메뉴 → /preclearance 경로 → 입력/분석 상태/결과 → 보고서 상세 구조를 사용한다. 기존 악보·재생 컴포넌트를 재사용하고 HTML/JSON 내보내기는 유지한다. 현재 정적 보고서 링크와 실제 업로드 기능을 혼동하지 않게 한다. 인증/비공개 보관/삭제 정책 없는 공개 업로드는 보류한다. 메뉴/경로는 아직 구현 전이다.
