# Pillar–Phrase 근거 분리 및 제한적 검토 계획

## 최신 진행: 단일 쉼 규칙 비교 완료

observed-gap의 실제 localUnit 입력/조건/attack 선택을 traceSink로 수집한다. 주변 onset이 추정됐으면 보류한다. ledger v0.2의 complete-rule은 이 cue의 계산만을 뜻하며 final boundary의 모든 부모가 확인됐다는 뜻이 아니다. 전체 complete는 false다.

현재 입력/XML/성부 해시를 확인한 뒤 Pillar following-gap이 쓰는 관찰과 비교한다. 중복/비교 범위 밖/확인 불가를 UI로 제공한다. 비교 범위 밖은 전체 Phrase에서 미사용이라는 뜻이 아니며 가산하지 않는다. 이 검토는 읽기 전용이고 경계 제안 규칙은 아직 실행하지 않는다. 이후 확대할 때도 현재의 scope 제한과 미확인 차단을 유지해야 한다.

2026-09-23 / 1단계 구현 완료. 아래 현재 위험 설명은 분리 전 상태의 기록이다. 2단계 이후는 계획이며 구현하지 않았다.

### 후속 상태: 2단계 부분 구현

규칙 ID/버전과 근거군, 입력 주변음 참조 구조화 및 generic auditEvidence 테스트 구현. 중복 관찰 제거·간접 의존·순환·누락·revision 검사 기반은 준비됐지만, 실제 Phrase 사용 근거 adapter와 원본 revision/전체 parent graph 연결은 아직 없다. 따라서 운영 근거는 모두 미검증이며 다음 단계의 shadow review로 전달하지 않는다. 이전 문단의 ‘2단계 미구현’은 이 갱신 이전 상태다. 다음 개발은 완전한 출처 기록과 Phrase adapter 연결이며 이를 완료하기 전 2단계 완료로 표시하지 않는다.

### 1단계 완료 기록

pillarCandidates는 phraseStarts를 입력 계약에서 제거했다. composePillarDisplay가 독립 결과와 별도 시작 힌트를 합성한다. 힌트만 있는 음은 reasons와 correspondences가 비어 있고 origin=phrase-hint-only로 표시된다. 독립 후보의 reasons/level/근거는 그대로 유지한다. UI는 보라색 힌트와 독립 후보를 구분하고 shared 보기는 힌트를 제외한다.

시작 위치 변경/제거의 독립 결과 불변, 짧은 엇박 표시 유지, 오래된 참조 무시, shared 제외 테스트 포함 관련 21개 테스트 통과. TypeScript 검사 통과. 실제 화면 토글 전후 프레이즈 목록 불변 확인. 아직 구조화된 근거 graph/간접 의존 감사는 없으며 화성 입력의 향후 provenance 검증도 2단계 과제다. 이 분리만으로 모든 근거가 통계적으로 독립이라고 주장하지 않는다.

## 1. 현재 위험

현재 pillarCandidates는 음가·박·왕복·반복·phraseStarts를 reasons에 합쳐 표시 등급을 정한다. 시작 근거가 후보 선정과 등급 모두에 영향을 줄 수 있다. shared 보기도 최종 후보의 correspondences만 확인하므로 독립 후보라고 단정할 수 없다. 현재 Pillar→Phrase 역방향 연결은 없으며 이를 유지한다.

## 2. 고정된 흐름

원본/Core → 독립 근거 → 독립 기둥 후보.
원본/Core → 기존 Phrase → 시작음 표시 힌트.
독립 후보 + 표시 힌트 → 화면.
독립 근거 + 고정된 기존 Phrase → 읽기 전용 재검토 의견.

표시 결과를 분석 입력으로 돌려보내지 않는다. 독립이란 정확하다는 뜻이 아니라 검토 대상 Phrase 해석에 의존하지 않는다는 뜻이다.

## 3. 결과 분리

- independentCandidates: phraseStarts를 받지 않는 함수에서 계산.
- phraseStartHints: noteId, phraseRef, analysisRunId를 가진 표시 기록.
- displayCandidates: 두 결과를 합친 보기. 시작 힌트만으로 추가된 음을 명시.

시작 힌트는 독립 후보의 점수·등급·색을 올리지 않는다. 시작음 강조는 배지로 유지한다. 반복 공통 보기는 독립 후보 중 대응 근거가 있는 음만 표시한다.

## 4. 구조화된 근거

Core가 아닌 Analysis Layer에 저장한다. 필수 필드:
evidenceId, scoreRevision, streamId, eventRefs, kind, family, origin, ruleId, ruleVersion, parameterHash, parentEvidenceRefs, dependsOnAnalysisRefs, observationKey, payload.

family는 timing/metric/melodic/recurrence/harmony/phrase.
origin은 source-derived/analysis-derived/human.
observationKey는 revision+사건+기초 관찰의 정체성이다.
payload는 kind별 타입/schema로 검증하며 자유 JSON으로 운영하지 않는다.
표시 문구는 구조화된 근거에서 생성한다. 한국어 문자열 includes로 계산하지 않는다.

## 5. 중복·순환 방지

1. 기존 Phrase의 사용 evidenceRefs를 기록한다.
2. 부모를 재귀적으로 따라가 기초 관찰과 분석 의존성을 펼친다. 부모 누락·순환·revision 불일치는 보류한다.
3. 같은 음의 길이를 장음/도착음/기둥음으로 바꿔 불러도 추가 표로 세지 않는다. 복합 근거를 분해해 기존 관찰은 표시만 한다.
4. 첫박과 기준 박 위치도 같은 관찰이면 중복 계산하지 않는다.
5. 정확 반복과 변형 정렬이 같은 대응을 설명하면 하나의 recurrence 묶음 안에 대안으로 보존한다.
6. 다른 근거군도 통계적으로 독립이라고 가정하지 않는다. 초판은 합산점수/확률 없이 기존·추가·충돌 목록을 제공한다.
7. 간접 부모라도 검토 대상 Phrase 실행에 의존하면 독립 검토에서 제외한다. phrase-start 라벨만 지우는 것으로는 부족하다.

기존 Phrase가 근거 ID를 제공하지 못하면 ‘중복 확인 미완료’로 표시하며 자동 적용은 금지한다.

## 6. 초기 검토 규칙 두 종류

### 도착 전에 끊었을 가능성

경계 뒤의 독립 지속/도착 후보와 직전 진행의 연결을 검토한다. 긴 쉼, 타이 단절, 성부 불명 등 반대 근거를 함께 기록한다. 기둥 하나만으로 오류를 단정하지 않는다. 검토 창은 실제 박 기준 1/2/4박의 민감도를 평가해 정한다. 원안과 대안은 별도 보존하고 장음=종지로 해석하지 않는다.

### 반복 구간의 경계 위치 차이

Phrase와 독립적으로 구한 대응으로 경계의 상대 위치를 비교한다. 정렬이 모호하거나 여러 후보면 보류한다. 화성·종결/지속 기능 차이로 다른 경계가 정당할 수 있으므로 강제 통일하지 않는다. 현재 4–6음/128 attack 대응은 국소 증거이지 전체 Phrase나 종지 동일성의 증명이 아니다.

## 7. 검토 기록과 UI

ReviewRecord 필드:
reviewId, ruleVersion, scoreRevision, baselinePhraseRunId, targetBoundaryRef, originalSpan, alternativeSpans([start,end)), evidenceRefs, alreadyUsedEvidenceRefs, independentNewEvidenceRefs, counterEvidenceRefs, unknowns.

status: suggested / abstained / accepted-for-case / rejected-for-case.
reviewerComment·reviewerId·reviewedAt은 선택. appliedToProduction은 초판에서 false 고정.
사람의 accept는 해당 사례 판단이지 일반 규칙/gold/training 자동 승격이 아니다.

‘경계 재검토 후보’ 스위치는 초기 OFF. 원래 Phrase 띠는 움직이지 않고 대안은 별도 점선 줄로 표시한다. 카드에는 원래 경계·대안·추가 근거·기존 근거·반대 근거·미확인을 보여준다. 부족하면 판정 보류. 초판에는 자동 적용 버튼을 두지 않는다.

## 8. 단계와 완료 조건

1단계: 독립 계산과 시작 힌트 합성 분리.
완료: phraseStarts 변경/제거에도 독립 후보·근거 deep-equal. 짧은 시작음 표시 유지. 표시 토글 전후 Phrase 불변.

2단계: 근거 ID·부모·관찰 key·run/revision, Phrase 근거 adapter.
완료: 중복·간접 순환·누락 참조·revision 검사 통과. 미지원 근거는 가산 금지.

3단계: 저장 스냅샷에서 두 검토 규칙 실행.
완료: 제안/반례 JSON 저장, 원래 Phrase 불변. 주석 없이 실행 가능하나 정확도 주장 금지.

4단계: 읽기 전용 비교 UI.
완료: 원안/대안/반대 근거 비교, 검토 기록 보존.

5단계: 자동 변경 검토 — 현재 범위 밖.
새 사용자 승인과 독립 평가 필요. 낮은 가중치로 임시 연결하지 않는다.

## 9. 평가

- 기존 Phrase / 독립 검토 추가 / 시작 힌트 유무를 동일 revision에서 비교한다.
- Melody/Piano Solo 등 같은 작품의 다른 버전은 한 그룹으로 묶어 개발/평가를 작품 단위로 분리한다.
- 기존에 좋았던 사례, 짧은 시작음, 당김음, 긴 쉼, 반복 종결 차이, 타이, 변박, 불확실한 성부를 포함한다.
- 적절한 제안 비율, 잘못된 경고, 보류율, 놓친 오류, 실행시간을 보고한다. 경고 전체를 평가하고 유리한 사례만 고르지 않는다.
- 허용된 복수 경계를 오답 처리하지 않고 미판정을 정답으로 세지 않는다. 사례 수·분포·불확실성을 함께 보고한다.
- 자동화 정확도 기준은 미정. 평가 사례 수와 오변경 비용을 먼저 정하고 결과를 보기 전에 채택 조건을 고정한다.

## 10. 다음 실행 범위

먼저 1단계만 구현한다. 이후 2→3단계 안전성 검증 후 4단계로 진행한다. 나중에 화성이 들어와도 동일 출처·중복 규칙을 적용한다. 특정 곡명·workId·마디 전용 규칙은 금지한다.

### 최신 진행 상태: 실제 Phrase adapter 연결

1단계 완료. 2단계의 generic 감사 기반에 이어 getWork의 실제 cues를 보존하는 phraseEvidenceLedger API adapter를 연결했다. 실제 입력/전달 XML/분석 코드 해시와 실행 참조가 있다. gap/continuity의 분자 입력만 partial로 추적하며 localUnit·guard·그룹화 부모는 아직 없다. 다른 규칙은 unmapped다. 현재 모든 기록은 complete=false이며 경계 판단 재사용은 차단한다. 다음 작업은 이 미연결 부모 추적과 Pillar의 동일 관찰 key 연결이다. adapter가 있다는 이유만으로 2단계 완료나 완전한 중복 검증을 주장하지 않는다.
