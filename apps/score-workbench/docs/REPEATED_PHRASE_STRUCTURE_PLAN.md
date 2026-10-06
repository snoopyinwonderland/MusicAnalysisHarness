# 반복 Phrase 구조 기반 경계 보정 — 구현 기획 v0.1

상태: **A 부분 완료(004–006 원본 입력 보존), B/C 관찰·정렬 초안, D 전체작품 shadow registry 구현·검증. E 독립 검토/보정 대기, F 미적용**. 갱신2026-09-22.
진입 문서: 이 문서. 이전 구현은 phrase-first-motif-v1.md 및 phrase v1.11–v1.14 기록을 참조한다.

## 1. 목표와 비목표

목표는 기존 Phrase 검출을 교체하지 않고, 작품 안에서 반복되는 리듬·선율 구조로 경계를 보정하는 것이다. 독립적으로 잘 잡힌 Phrase가 다른 곳에서 둘로 갈라졌을 때 대응을 찾아 병합 후보를 제안한다. 상위 Phrase를 병합해도 내부 Motif는 보존한다.

첫 검토 사례는 S-STRUCT-006 When We Disco다. 사용자 설명은 ‘앞의8분음표3개+4개 beam 묶음, 뒤의 음표/쉼표/3개 묶음과 변형된 후반’이다. 이는 **검증할 사용자 가설**이며 실제 XML 그룹을 확인하기 전 확정 특징으로 저장하지 않는다. ‘3+4’를 모든 작품의 하드코딩된 패턴으로 만들지 않는다. 최신 Phrase4+5의 정확한 이벤트 범위는 구현 시작 시 버전 고정 snapshot으로 확보한다.

비목표: 원본 악보 수정, 전체 화성 분석, 자동 학습, 모든 작품의 완전 분할, 특정마디/제목 예외, 기존 Core schema 의미 변경.

## 2. 현재 코드에서 재사용할 것과 보완점

- server/phrase-boundaries.mjs: 기존 경계 점수·cue·긴 쉼 보호를 baseline으로 유지한다.
- src/music/motifSimilarity.ts: 삽입/삭제 정렬과 melody/shape/rhythm/coverage 분리 방식 재사용. 현재 음표 중심 비교에 beam/rest/metrical 위치 채널은 별도로 보완한다.
- src/music/phraseMotifs.ts: 보정된 Phrase를 받아 내부 Motif를 계산한다. 전체 Phrase fallback을 확정 Motif와 구별하는 정책 유지.
- server/xml-target-verification.mjs: 원본 note 블록, 위치, staff/voice, rest 여부는 얻을 수 있다. beam 묶음/정확한 지속시간/타이 체인/안정 ID 계약은 이 도구만으로 완성되지 않는다. `beat`는 quarter 기반 offset+1이므로 지각적 기준박으로 그대로 사용하지 않는다.
- 현재 UI 분석은 단일 melody stream의 편의 이벤트를 쓰는 경로다. Canonical IR에 필요한 관찰이 있으면 그것을 우선 소비하고, 없으면 source-linked adapter를 사용한다. 이것을 완전한 IR 통합이라고 부르지 않는다.

## 3. 제안 파이프라인과 순환 방지

XML/IR 관찰 → 기존 Phrase 결과 동결 → 독립적인 기준 구간 확보 → 작품별 반복 구조 비교 → 경계 보정 제안 → 선택적으로 적용 → Motif 분석.

현재 분석은 Motif 관계가 Phrase에 영향을 주기도 한다. 새 보정에서는 현재 실행의 **보정 전 결과와 출처가 분리된 근거만** 기준으로 삼는다. 자신이 병합한 구간을 다시 정답 템플릿으로 채택하여 다음 병합을 정당화하지 않는다. v1은 단일 pass이며 반복 최적화하지 않는다. 새 템플릿은 다음 검토 버전에서만 승인한다.

## 4. 관찰 데이터 계약

별도 `notation_evidence` extension/adapter에 다음을 보존한다.

| 종류 | 필요한 정보 | 주의점 |
|---|---|---|
| 원본 참조 | source hash, score revision, event ID, part/voice/staff, XML 위치 | 실행 중 array index는 장기 ID가 아니다 |
| 기보음 | onset, notated duration, pitch spelling, note type/dots | quarter 좌표는 rational로 보존 |
| sounding/attack | tie chain, 누적 duration, attack 여부 | 타이 지속을 새 음으로 세지 않음 |
| beam | level, begin/continue/end/hook, 연결 note IDs | 1차/2차 beam, 마디 넘김, cross-staff 구별 |
| rest | 명시적 rest span과 inferred gap을 각각 기록 | 다른 성부의 발음/숨김 rest와 구별 |
| 박자 | time-signature timeline, 기준박 길이, grouping provenance | 비대칭·박감 모호함은 unknown/대안 유지 |
| 호흡 기호 | fermata/breath-mark/caesura, 원본 위치 | 확정 Phrase 종결과 동일시하지 않음 |

beam은 기보 관찰이며 구조 해석 자체가 아니다. 가사 때문에 beam이 끊기거나 편집기에 따라 재묶인 경우에도 음가·onset이 같으면 분석이 크게 달라지지 않아야 한다. beam 누락을 불일치로 감점하지 않고 해당 채널을 unavailable로 둔다.

기준박은 time-signature만으로 확정하지 않는다. 명시적 grouping 우선, 없으면 관례적 해석과 provenance를 저장한다. 속도/2박감에 따라 해석이 갈리는 경우 자동 병합을 보류할 수 있다. 음가·쉼은 기준박 비율과 주변 음가 비율을 둘 다 사용한다.

## 5. 리듬 단위와 작품별 템플릿

두 표현을 함께 사용한다.

1. 세밀한 attack/rest 연속열: 상대음정, contour, 기준박 대비 duration/onset, metric 위치.
2. 묶음 요약: beam group, 긴 도착음, rest, 재시작. source-note refs를 역추적 가능하게 둔다.

텍스처만 같은 작품들을 잘못 합치지 않도록 beam 개수만으로 일치를 판단하지 않는다. 반복음은 melodic 식별력이 낮더라도 작품 내부 rhythm 역할을 잃지 않게 보존한다.

템플릿은 `공통 앞부분 → 공통 연결부 → 변형 허용 후반 → 종결 후보`로 기술한다. 이 역할은 Analysis Layer의 가설이지 Core 속성이 아니다. 앞부분/후반 위치를 전체 길이의 고정 비율로 자르지 않고 여러 대응 구간의 정렬 결과로 추정한다.

첫 자동 적용 후보는 다음 중 하나로 제한한다.

- 전문가가 승인한 원본 문맥 포함 템플릿.
- 후보 병합 대상과 겹치지 않는 두 개 이상의 구간에서 확인되고, 외곽 경계가 각각 독립적 호흡/종결 근거로 지지되는 템플릿.

한 구간만 있는 경우 비교·병합 제안은 가능하되 자동 적용은 보류한다. 같은 구간의 여러 부분창을 독립 사례로 세지 않는다.

## 6. 변형·재등장 비교

조옮김 불변 음정/윤곽, 상대리듬, 쉼 위치, metric 위치, 선택적 beam 채널을 각각 정렬한다. 삽입·삭제는 허용하되 앞부분 누락을 높은 유사도로 숨기지 않는다. prefix coverage, 전체 coverage, terminal alignment를 따로 보고한다.

같은 음의 분할/합침은 해당 묶음 전체의 지속시간·onset·주변 음정이 대응하는지 확인한다. 리듬적 연장/축소와 화성적 Prolongation은 별개이다. 화성 근거가 없으면 후자로 라벨링하지 않는다.

확인된 작품 내부 템플릿은 이번 실행의 registry에 저장하고 거리64음 제한 없이 뒤 구간과 비교한다. 한 음씩 변형을 이어가며 가족이 무한히 넓어지는 현상을 막기 위해 새 occurrence는 원형과 승인 변형에 대조하고 정렬 근거를 남긴다. 새 occurrence를 즉시 새로운 기준형으로 승격하지 않는다.

## 7. 경계 병합 결정

인접한 두 Phrase를 합친 후보와 각각 유지하는 후보를 모두 평가한다. v1은 인접2개만 대상으로 하며3개 이상 병합은 다음 단계로 남긴다.

자동 병합에는 아래 조건이 모두 필요하다.

1. 결합 구간의 앞·뒤가 템플릿의 전체 구조에 대응한다. 단순 부분 일치는 부족하다.
2. 내부 경계가 다른 occurrences의 내부 호흡 위치에 대응한다.
3. 외곽의 시작/종결 근거가 내부 경계보다 강하고 결합안의 대응 품질이 유지안보다 충분히 좋다.
4. 명시적인 호흡/긴 쉼 보호/승인된 경계 등과 충돌하지 않는다.
5. 데이터 mapping·박자·beam 누락 때문에 결론이 뒤집힐 정도로 불확실하지 않다.

점수 가중치와 적용 margin은 지금 임의 숫자로 확정하지 않는다. 기존84/70 점수는 비교 기준선으로 기록하되 새 채널의 검증 없이 재사용하지 않는다. 검토 데이터로 문턱을 고정한 다음 독립 작품에 평가한다. 충돌 시 `keep / merge / cannot_judge` 후보를 모두 남긴다.

원래 내부 경계는 삭제하지 않고 `internal_motif_or_breath_candidate`로 남긴다. Motif 경계로 자동 확정하는 것도 아니다. 상위 Phrase 변경 후 Motif 분석은 재실행하며 기존 occurrence와의 대응표를 보존한다.

## 8. 기록과 UI

`structure_revision`, `engine_version`, `source_hash`, 기존/제안 span refs, template refs, 정렬쌍, 근거/반대근거, 각 점수, decision, human review를 보존한다. 화면 Phrase 번호는 바뀌므로 피드백 target으로 쓰지 않는다. 보정 전후 ID mapping을 만든다.

오른쪽 패널은 다음을 보여준다.

- 현재 구간 vs 제안 구간의 마디·박·시작/마지막 음.
- 대응하는 다른 Phrase 위치와 공통/변형 부위.
- ‘이 쉼은 내부 호흡으로 반복됨’과 병합에 반대하는 근거.
- 제안 보기, 기존 결과 유지, 승인/거절/판단 보류. 승인해도 Core는 바꾸지 않는다.

Phrase lane과 Motif lane은 분리 유지한다. 이번 단계에서 상세 UI 전체를 먼저 만들기보다 검토 JSON+기존 패널 근거 표시부터 시작한다.

## 9. 구현 단계와 완료 기준

| 단계 | 산출물 | 완료 조건 |
|---|---|---|
| A. 기준 고정 | S-STRUCT-006 최신 snapshot/피드백 구간, 기존1–6 사례 baseline | 버전·source hash·번호→event 대응 재현 가능 |
| B. 기보 증거 adapter | proposed server/notation-structure-evidence.mjs, mapping 검사 | beam/rest/tie 출처 검증, 미매핑은 경고·보류 |
| C. 후보·정렬 | proposed structure-template-aligner 모듈, 채널별 점수 | 재기보·조옮김·변형/비유사 반례 테스트 통과 |
| D. 작품 registry·shadow 제안 | proposed phrase-structure-proposals 모듈, 제안 JSON | 기존 결과는 불변, 앞/뒤 반복 검색과 예산 초과 상태 기록 |
| E. 검토·임계값 고정 | 전문가 판단/오류 유형/holdout 평가 | false merge 우선 점검, 근거 부족은 보류 |
| F. 선택적 적용 | feature flag, 우측 근거 표시, 변경 매핑 | opt-in 적용/즉시 baseline 복귀, Phrase/Motif lane 유지 |

모든 단계에서 개발 기록은 본 문서 상태와 development-log만 갱신한다. 사례별 의견은 evaluation/cases, 원본 snapshot은 case-assets에 둔다. 구현 버전 문서는 실제 적용 시에만 추가한다.

## 10. 테스트·출시 기준

필수 양성: 같은 Phrase가 내부 쉼 때문에 둘로 나뉜 경우, 조옮김, 종결음 길이 변형, 반복음 리듬, 먼 재등장, 후반 일부 삽입/누락.

필수 음성: 같은 리듬이지만 별개 Phrase, 실제 긴 휴지/caesura, 서로 다른 종결, 앞부분만 일치, ostinato, 동일 beam 개수의 다른 선율, 서로 다른 성부.

기보 불변성: beam을 생략/재묶은 동일 이벤트, 가사 유무, tie 분할 방식, divisions/tuplet, 박자 변환의 동등 표현. 강약/beam 변형으로 구조 증거가 바뀌는 경우에는 자동 결론 대신 민감도 경고를 허용한다.

기존 S-STRUCT-001–006은 개발 회귀에 사용하고, 같은 작품 다른 판본은 독립 holdout으로 세지 않는다. 최소10개 신규 작품을 초기 전문가 검토 파일럿으로 제안한다. 이는 통계적 성능 입증 규모가 아니다.

평가: 경계 precision/recall(정확 event 위치와 명시된 박 단위 허용오차를 별도 보고), false merge/false split, 사용자 승인된 구간 보존, Motif 재등장 회수, 보류율, mapping 실패율, 지연시간. 합의된 protected 경계 파손은0건이어야 하고, 신규 모호 사례는 정답으로 강제하지 않는다.

후보길이/비교수/시간 예산은 설정값으로 기록하고 초과 시 partial/abstain으로 종료한다. 전체재계산은 source+notation+engine version으로 cache 무효화한다. 성능 때문에 원본 경계/오류를 숨기지 않는다.

## 11. 화성 사례 확장

화성 데이터는 동일 리듬에서 ‘종결’과 ‘지속’을 구별하는 보조 증거로 유용하다. 하지만 Roman numeral 변화만으로 자르지 않는다. local key, cadence 후보, 비화성음 해결, prolongation 가설의 confidence/engine version/human 상태를 함께 참조한다.

가장 유용한 입력은 비슷한 리듬인데 종결 여부가 다른 대조 사례다. source-linked 음표·앞뒤문맥·설명·대안이 있어야 한다. 현재 단계에서는 화성 가설을 hard gate로 연결하지 않고 검토 패널의 supporting/conflicting evidence로만 둔다. 별도의 검증 뒤 가중치에 반영한다.

## 12. 다음 실행 범위

### 전체 작품 registry와 event 기반 의견 대조

- `server/phrase-structure-registry.mjs`는 동결된 기존 구간만 기준으로 앞/뒤의 모든 비중첩 구간과 인접2구간 결합안·각각 유지안을 비교한다. 거리64음 제한이 없고 새 제안을 기준형으로 승격하지 않는다. 기준 구간은 승인된 음악적 템플릿이 아닌 unreviewed-baseline이다. 정렬 예산 초과는 partial과 미방문 개수로 기록한다.
- `scripts/evaluate-structure-feedback.mjs`가 원본/입력/문서/코드 hash 및 음표 ID를 보존한다. 004/005/006에 총10,356회 정렬,102개 인접 결합 검토를 수행했다. 기존 보호34개는 keep, 나머지는 cannot_judge다. 보정되지 않은 수치로 병합을 승인하지 않는다.
- 위치가 명확한 문서 의견12건 중 현행 경계11건 일치,006의 index51 경계 제거1건 미해결. 004의 의견은 복수해석/당시 구간 번호 대응 보강이 필요하여 이번 event 기대 검증에는 포함하지 않았다. 사용자 선호이며 gold나 독립 평가 성적으로 부르지 않는다.
- 006 병합 대상의 최고 유사도94인 후반 반복은 coverage60, 끝음 미대응이고 첫 조각만 비교하면100이다. 즉 기존 Motif 점수의 부분 일치 성향으로 전체 Phrase 병합을 승인하면 위험하다. 결손 근거를 별도 출력하며 점수 순위만으로 합치지 않는다.
- 초기001–003의 events.json은 문맥 발췌이다. 전체 review-snapshot으로 둔갑시키지 않고 초기 구간 평가 입력으로 추후 별도 계약화해야 한다.
- 최신 산출물은 `evaluation/reports/structure-feedback-v2/review.md`. E의 독립 작품/전문가 검토와 병합 margin 보정 없이는 F 화면 자동 적용을 진행하지 않는다. 단순한 구현 미완료와 음악적 검증 대기를 구별한다.

### 기존 사례 일괄 관찰 검증

`scripts/audit-phrase-closure-cases.mjs`와 `evaluation/reports/phrase-closure-cases-v1/review.md`에 001–006 적용 범위와 보류 사유를 기록했다. 004/005/006은 각각298/444/431개 음표 전부 매핑, 현재 엔진 경계33/29/41개 모두 source duration/rest 대조 및 박자 환산 가능, 보호8/11/15개다. 이는 현재 엔진의 경계를 검사한 결과이지 사용자 정답 대비 정확도 또는 false-merge 평가가 아니다. 001–003은 원본 XML만 있고 review-snapshot.json이 없어 제외했다. 원본 및 입력 snapshot과 코드 hash를 보고서에 보존했다.

기존 사용자 피드백을 event ID 기반 기대 경계로 정리하고 현재 경계와 대조하는 단계가 남았다. 초기 사례의 입력 재구성은 당시 분석 입력 복원과 최신 parser 재파싱을 구별해서 기록해야 한다. 이번 실행은 운영 경계나 UI를 바꾸지 않는다.

### 박자 정규화와 경계 보호 대조 (shadow-v4)

최종 코드 해시 보고서는 `phrase-structure-shadow-v5/review.md`이며 v4와 판정은 동일하다. 관련7개 파일30개 테스트 통과.

- `phrase-meter-review.mjs`: 원본 part의 마디별 조표가 아닌 **박자표**를 읽고 상속한다. 일반 단순박자와 6/8·9/8·12/8의 관례적 복합박을 지원한다. 가산박자, staff별 박자, 마디중 변경, 종결 구간 중 박자 변경은 보류한다. 이는 연주 pulse 추정이나 완전한 MusicXML parser가 아니다.
- 기존 v1.14 기준(쉼4박 이상 또는 음가2박+쉼2박 이상, 호흡 표기)을 shadow 경계 보호에 재사용한다. 새 자동 병합 임계값은 만들지 않았다. 4/4와 4/8의 동일 기보 음가가 다른 결론을 내고, 박자·음가 동등 확대는 같은 판단을 유지하도록 테스트했다.
- S-STRUCT-006 Phrase1/2/3/5 종결은 보호, Phrase4→5 내부 경계는 보류. 같은 작품의 기존 종결을 대조했으나 독립 작품 holdout 검증은 아니다. 최신 보고서는 `phrase-structure-shadow-v4`이며 화면은 변경하지 않았다.
- 다음: 기존1–5 사례로 비교 폭을 넓히고, 전체 정렬의 종결 불일치/비유사 대조와 template registry를 검증한다. 보호되지 않음 ≠ 병합 승인 원칙을 유지한다.

### 원본 쉼 / tie 종결 대조 (shadow-v3)

`server/phrase-source-closure.mjs`는 동일 음높이 표기의 인접 tie start/stop과 뒤따르는 명시적 rest를 연결해 기존 음가/추정 gap과 비교한다. source ID와 종결 기보 위치를 보존하며 잘못된 tie, 비연속 시간, 다음 attack mapping 불일치, chord/grace는 보류한다. 박자 없는 마디 경계의 연속성은 조건부이므로 정식 Canonical tie-chain 검증을 대체하지 않는다.

S-STRUCT-006 Phrase4의 마지막 음(index50)은 1.5 quarter + 쉼0.5 quarter, Phrase5의 마지막 음(index56)은 tie 2음 누적2.5 quarter + 쉼5.5 quarter로 기존 데이터와 일치했다. 이는 내부 호흡보다 결합안 끝의 쉼이 길다는 관찰이며, 단독으로 병합을 확정하지 않는다. Phrase2 종결도 tie 2음 누적2.5 quarter + 쉼2.5 quarter로 확인했다. 정렬의 끝음 불일치가 tie 음가 누락 때문이라고 결론낼 근거는 없다.

최신 보고서: `evaluation/case-assets/S-STRUCT-006/phrase-structure-shadow-v3/review.md`. 대응 음 앞의 명시적 쉼 비교도 JSON에 추가했다. 유사도 점수와 운영 경계는 그대로다. 다음 단계는 meter 정규화와 비유사/강한 내부 종결 대조 사례 검증이다.

### C 비교기 / 제한적 shadow 실행

- `src/music/structureTemplateAlignment.ts`가 기존 다중 증거 Motif 정렬을 재사용해 전체 정렬, 연속 도입 대응, 끝음 대응, 추정 쉼 차이, event ID를 반환한다. 128음 초과/잘못된 입력은 보류한다. beam과 쉼은 현재 진단 자료이며 가중 점수에 추가하지 않았다.
- `scripts/compare-phrase-structure.mjs`로 인접 구간 결합과 각각 유지하는 안을 앞선 Phrase들과 비교한다. 자동 후보 탐색/작품 전체 template registry는 아직 구현하지 않았다. C 초안과 D의 제한적 수동 대상 보고서이지 C–D 전체 완료가 아니다.
- 최신 결과는 `evaluation/case-assets/S-STRUCT-006/phrase-structure-shadow-v2/review.md`. Phrase4+5는 기준1/2/3과 각각83/90/83, 도입8음 대응. 기준2와는 끝음이 대응하지 않는다. 수치는 보정된 확률이 아니며 서로 길이가 다른 유지안과 점수만으로 우열을 판단하지 않는다.
- 원본 hash, baseline engine hash, 비교기 의존 코드 hash, 범위와 기존 내부 경계 증거를 보존했다. v1 보고서는 결합구간 endMeasure가 첫 구간 값을 유지한 초기 초안이므로 v2를 기준으로 본다. 이전 파일은 덮어쓰지 않았다.
- UI/운영 경계는 변경하지 않았다. 다음은 명시적 쉼과 tie 종결 검증, meter 정규화, 비유사 대조 사례를 추가한 후 전체 registry로 확장하는 것이다.

### 2026-09-22 진행 결과

- scripts/prepare-phrase-structure-baseline.mjs가 source/engine hash와 버전, Phrase번호→event 범위를 고정한다. 기존 결과 폴더가 있으면 덮어쓰지 않는다. S-STRUCT-006/phrase-structure-v1-baseline에 생성했다. 사례1–5 전체 baseline 확장은 아직 남아 있다.
- server/notation-structure-evidence.mjs는 기존 XML 위치 adapter를 사용해 beam/rest/tie 표기, pitch spelling, 기보 duration fraction, source refs를 추출한다.431/431 이벤트 매핑,122 beam groups, 경고0을 확인했다.4/8/12/16마디의3+4개 beam 묶음을 확인했다.
- B는 아직 초안이다. onset은 기존 numeric adapter이며 마디중 divisions 변경 검증, canonical tie-chain 연결, meter timeline과 explicit grouping, cross-staff mapping 보강이 남았다. 따라서 자동 병합 근거 엔진에 아직 연결하지 않았다.
- 비교 구간과 사용자 의견은 evaluation/cases/s-struct-006-structure-baseline.md에 연결했다. 분석 코드/화면 경계는 변경하지 않았다. 다음은 B의 미지원 입력 검증과 C의 정렬이며, 전체3+4 묶음만으로 병합하지 않는다.

먼저 A–D까지 수행한다. 현재 화면의 경계는 유지한 채 S-STRUCT-006 Phrase4+5 결합안과 기존1–3 대응을 생성·비교한다. 사용자가 정렬과 근거를 확인한 뒤 E–F로 진행한다. 이번 기획 작성으로 자동 병합 적용까지 승인된 것으로 간주하지 않는다.
