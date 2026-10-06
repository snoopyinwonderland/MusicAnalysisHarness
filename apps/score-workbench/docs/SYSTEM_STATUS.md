# 현재 구현 상태 — 2026-09-15

## 후속 2026-10-05

Query·추천·검색 결과·상세 악보에 피아노/바이올린/비올라/첼로 샘플 음색을 연결했다. 기존 단일 검색 성부의 타이·음가·쉼표·예약 시계와 seek/재생 위치 계산은 유지하며, 준비되지 않은 음원은 기본 소리로 대체한다. 여러 파트 합주 재생을 추가한 것은 아니다. [구현·재현·제한](sampled-playback-integration.md).

## 후속 2026-09-16

성능 7단계: 후보 경계 수치 캐시(기본 활성, 추정 64MiB LRU)를 추가했다. 두 Query 반복 8.986→6.510초, 11.699→8.900초, 전체 응답 동일. 최초 실행은 저장/키 생성으로 느려지는 tradeoff가 있다. 분석기 변경 시 worker 재시작 필요. [최종 측정/제한/해제 방법](performance-stage-7.md).

검색 성능 6단계: 두 Query 총 12회 A/B/control에서 전체 응답 hash 일치. SQL 집계는 warm 기존 방식보다 느려 opt-in 실험으로만 보존하며 기본 적용하지 않았다. 다음 병목은 프레이즈 문맥 재계산(약 5~8초)이다. [측정·재현·한계](performance-stage-6.md).

실제 A/B 완료(Phrase 7 vs 동일 Phrase+Motif 1). 개발 후 50개 변형 테스트도 수행했다. 최초 49개 완료/1개 timeout, 해당 1개 별도 재시도 완료. 원본 source 회수 32/50, 1위 29/50. 개별 음높이 변경/삭제 취약성과 표본 편향을 확인했으며 개별 결과를 강제로 보정하지 않았다. [최종 50개 평가](preclearance-variation50-2026-09-16.md).

기본 Phrase-only, 보조 Motif A/B, 독립 기둥음 proxy, Contour/리듬형/음형, 복수 Phrase 가족의 제한적 점수를 구현했다. `/preclearance` 메뉴에서 로컬 샘플 보고서를 확인한다. 사용자 확인 원곡은 검증된 ID 연결로 제외한다. 메인 검색 순위와 법률 판단은 변경하지 않는다. 131개 회귀 및 build 통과. 자세한 범위/남은 한계는 [v2 계약](preclearance-musical-evidence-v2.md)을 우선한다. 아래는 이전 단계의 역사적 상태다.

## 데이터 흐름

MusicXML 원본 → compact 논리 음표 index → SQLite/n-gram 검색 → alignment → Verovio 악보 표시.

별도 사전검토: 이벤트 스냅샷 → Phrase/Motif 어댑터 → 최대 7개 Query 선별 → 같은 검색 엔진 → 검증된 작품/판본 집계 → 후보 구조 중요도 보강 → 오프라인 Copyright Infringement Report 초안.

| 영역 | 코드 | 상태 |
|---|---|---|
| 웹 검색/API | vite.config.ts, server/search-api.mjs, src/ | 기존 사이트; Vite middleware가 API도 제공 |
| 구조 스냅샷 | server/structure-analysis-adapter.mjs, phrase-boundaries.mjs | 로컬 분석기 버전·이벤트 지문 보존 |
| 사전검토 Query 선별·집계 | server/preclearance-search.mjs | 오프라인 CLI 검증 |
| 검색 재개/시간 제한 | scripts/run-preclearance-search.mjs, server/search-worker-client.mjs | task checkpoint와 manifest |
| 작품·판본 연결 | server/work-identity.mjs, data/work-identities.json | 확인된 관계만 병합; 모든 작품에 완성된 registry 아님 |
| 후보 중요도 | server/preclearance-importance.mjs | 반복·박자·음가 및 Phrase/Motif 관계; 미확인 항목 null |
| 긴 성부 분석 | server/structure-worker.mjs | worker 시간 제한·취소, CLI에서 사용 |
| 검토 우선순위 | server/preclearance-priority.mjs | 별도 실험 순서; corpus 희귀도와 전문가 보정은 미완료 |
| 코퍼스 빈도 A/B | server/preclearance-frequency.mjs, frequency-worker.mjs | 5음정 패턴의 source별 빈도; baseline을 유지하는 별도 비교, canonical 작품 빈도 아님 |
| 유형별 검토 Harness | server/preclearance-review-cases.mjs, scripts/run-preclearance-review-suite.mjs | 12개 논리 이벤트 사례 선별, 파일럿 검색, 사람 판단은 unreviewed |

현재 검증: 구조 보강 26그룹/30성부/56구간 성공. 기존 순위·점수·alignment는 유지한다. 전체 검색·법률 판단 성능 검증으로 확대 해석하지 않는다.

## 아직 구현되지 않았거나 제한된 범위

- Creator 업로드부터 최종 보고서까지의 인증·비공개 보관·삭제·운영 job/UI는 완성되지 않았다.
- 중요도는 해당 스냅샷의 성부 안 비중이다. 모든 파트를 고려한 작품 전체의 중요도나 전문가의 Schenker 분석이 아니다.
- 외부 구조 분석기의 새 버전을 자동 배포·전체 corpus 재분석하는 운영 연동은 미완성이다.
- 사전검토 후처리는 별도 CLI다. 메인 사이트 순위에 아직 반영하지 않는다.
- 구조 worker timeout은 성부 읽기+구조 분석을 제한한다. 후속 중요도 계산과 파일 저장 전체에 대한 하드 deadline은 아니다.
- 구조 보강에는 검색 단계와 같은 영속 task별 resume가 아직 없다. 취소 시 부분 보고서를 저장하며 재실행에는 새 경로를 사용한다.
- 관할별 권리 확인과 운영용 최종 보고서는 후속 단계다. HTML/JSON 초안은 구현했으며 미확인 권리를 명시한다. 표시용 accessPolicy를 법률적 권리 확인으로 간주하지 않는다.

실제 source 빈도 A/B는 95,813파일·64패턴 측정 완료. 26개 작품의 baseline 순위와 동일했으며 품질 향상은 아직 입증하지 못했다. 다음 순서: 균형 있는 사례의 전문가 비교와 판본 편향 검증 → 보고서/권리 레이어 → 업로드·운영 연결. 특정 Query의 특정 정답 순위를 고정하지 않는다. [우선순위 실험](preclearance-stage4-priority.md), [빈도 측정](preclearance-stage5-frequency.md)을 참고한다.

유형별 파일럿에서 4개 중 3개가 60초 timeout, 나머지도 55.32초였다. 현재 우선 진단은 짧은 Query의 단계별 처리시간이다. [파일럿 결과](preclearance-review-pilot-2026-09-15.md)는 12개 생성/4개 실행/8개 미실행과 사람 미검토를 구분한다.

후속 계측: 반복음 사례 trace 40.0초, warm trace-off 4.6초; 전체 API JSON 결과 동일. 큰 비용은 박자 조회와 postings였다. [진단 근거](preclearance-stage7-search-tracing.md)를 참조한다.

최신 후속 구현: 박자 캐시 32개 단위 저장과 강제 중단/재사용 동등성 검증 완료. 이전 4개 Query 모두 60초 내 완료(4.7/44.1/48.4/7.1초). 아직 느린 최초 실행은 남는다. [8단계 근거](preclearance-stage8-cache-checkpoint.md).

[보고서 초안](copyright-infringement-report-v1.md)은 26그룹/56일치/52개 A/B 악보를 HTML과 JSON으로 출력한다. 관련 회귀 127개, TypeScript/build 통과. 역사적 v1.9 분석 근거로 만들었으며 현재 v1.10으로 재분석한 결과가 아니다. 다음은 전문가 검토와 권리 증거, 비공개 업로드 운영 연결이다.
