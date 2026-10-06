# MUSICANOTE 개발 기록

## 2026-09-23 — 연속 지속음의 마지막 종결 및 리듬 재시작 근거

- phrase-boundaries v1.17: sustained-ending-rhythmic-restart 근거 추가. 동일한 알려진 박자에서 최소 한 마디(최소 3 기준박) 지속한 음 뒤, 다음 마디 강박의 새 attack과 후속 3음의 짧은 리듬을 확인한다. 연속 온음표 중간에는 적용하지 않는다. glyph가 아닌 박자 대비 sounding duration을 사용한다.
- 새 근거 점수 0.68은 미보정 규칙 점수이며 확률/종지 확정이 아니다. 합산으로 중복 가산하지 않고 기존 점수와 max를 취한다. 기존 반복/최소 길이 억제는 유지. 타이 continuation, 겹침, meter 변경/누락, 불충분한 후속 문맥은 제외. 원본/기둥음/화성 판단 변경 없음. ledger에서는 새 근거를 미연결로 취급하며 완전 추적을 주장하지 않는다.
- sustained-ending 및 기존 boundary/ledger/Pillar gap 47개 테스트 통과. 연속 온음표 마지막만 선택, 4/2 박자 상대 길이, 타이/겹침/입력 누락/느린 음형/원본 불변 검사 포함.
- Especially for You 사례: 원본에서는 m3 duration 충돌로 생긴 경계가 남아 m5 후보 0.68이 minimum-phrase-attacks에 의해 0.49로 억제된다. 진단용 복제 입력에서 F5 duration을 3 quarter로 가정하면 첫 supported 경계가 m5 시작(index11)로 이동한다. 원본 수정/특정 곡 예외 없음. 입력 정합성 문제는 별도 후속 과제.
- 사례 원본/API/설명: K:/Music Analysis/reports/reviewer-cases/especially-first-phrase-2026-09-23/. 재현 스크립트 audit_especially_phrase_case.mjs.

## 2026-09-23 — observed-gap 단일 규칙 추적 및 Pillar 쉼 관찰 비교

- analyzePhraseBoundaries에 optional traceSink 추가. localUnit의 duration/IOI 입력과 선택 결과, 실제 쉼 분자, 조건, attack 선택을 별도 수집. trace ON/OFF의 반환 결과 deep-equal 검증. 검색의 기본 실행은 trace 없음.
- ledger v0.2: 명시적 주변 timing과 source/input/engine context가 있을 때 observed-gap 단일 cue만 complete-rule로 표시. 추정 onset을 거치면 partial 유지. 전역 complete/autoApply는 false. final Phrase 결정의 전체 출처 완료와 구별.
- pillarGapAudit는 브라우저 SHA256으로 현재 XML·notes·stream을 ledger와 대조한 후 같은 위치의 observed-gap과 following-gap 입력을 비교한다. 동일 키는 중복으로, 다른 키는 해당 쉼 규칙 범위 밖 관찰로 분리한다. 범위 밖 관찰을 전체 Phrase의 새 증거로 인정하거나 가산하지 않는다. 참조 누락·구버전·대상 규칙 부재는 확인 불가.
- 화면에 ‘쉼 근거 중복 검토’ 추가. Can't Smile Without You: complete-rule 23개, partial 176개, unmapped 197개. 기둥음 쉼 16곳 중 15 비교/1 확인 불가. 독립 160/시작 힌트 18 유지 확인.
- 관련 61개 테스트 및 TypeScript 검사 통과. source/analysis 불변, localUnit 기록, inferred onset 보류, 오래된 입력/XML/성부/참조 누락 차단 검사 포함. 경계 자동 변경과 신규 점수는 없음.

## 2026-09-23 — 실제 Phrase 근거 ledger API 연결 (부분 추적)

- server/phrase-evidence-ledger.mjs 추가. 실제 analysis.boundaries[].cues를 별도 기록으로 옮기고 SHA256 XML/input/engine-source revision 및 runId로 묶는다. sourceRevision은 API가 전달하는 XML의 해시이며 원본 파일 byte hash와 동일하다고 주장하지 않는다.
- observed-gap/observed-continuity의 현음 onset·직전음 onset/durationRatio를 관찰 참조로 연결. localUnit/조건문/후속 grouping 부모는 미연결이므로 partial. 다른 규칙은 unmapped로 보존. 모든 기록 complete=false, autoApply=false, reviewEligibility=blocked-incomplete-lineage.
- getWork 응답에 별도 phraseEvidenceLedger 추가. 기존 Phrase 결과 객체 및 strength/경계 계산은 변경하지 않음. Pillar 패널에서 실제 버전·부분 추적/미연결 수를 볼 수 있게 연결.
- 원본 불변·실제 cue 수 대응·revision 변경·알 수 없는 규칙/누락값 검사를 추가. 기존 Phrase 테스트 포함 56개 및 TypeScript 검사 통과.
- 운영 API Can't Smile Without You에서 partial 199개, unmapped 197개 및 차단 상태 확인. 다음 과제는 localUnit/guard의 완전한 의존 기록과 Pillar primitive key 정렬이며, 아직 근거 간 전체 중복 검증이나 경계 제안 실행은 하지 않는다.

## 2026-09-23 — 근거 구조화 및 출처 감사 기반 (2단계 부분 구현)

- pillarEvidence.ts에 규칙 ID/버전, timing/metric/melodic/recurrence 근거군, 입력 주변음 참조를 추가. 설명과 계산 분리: temporal gate는 한국어 includes 대신 규칙 ID 사용. 후보의 evidence는 모두 reviewEligibility=unverified이며 source revision 검증 완료를 주장하지 않는다.
- 근거군을 UI에 묶어 표시. 첫박/기준 박 등 관련 규칙을 독립 투표처럼 보이지 않게 한다. 기존 후보 선택/색상 등급은 이번 단계에서 변경하지 않음. 근거군 수는 독립성이나 신뢰확률이 아니다.
- auditEvidence 기반 구현: primitive observation key 중복 제거, 간접 Phrase 의존/순환/누락/다른 revision/중복 ID/불완전 leaf 차단. 기존 Phrase 근거 목록이 없으면 baseline-unverified이며 additional은 빈 배열, autoApply는 항상 false.
- 아직 운영 Phrase 근거 adapter와 전체 parent graph는 연결되지 않았다. 현재 local-input 근거를 완전한 graph로 위장하지 않는다. 화면에 ‘프레이즈 사용 근거와의 중복 확인 미완료’ 표시. 프레이즈 자동 변경 없음.
- 관련 27개 테스트 및 TypeScript 검사 통과. Can't Smile Without You 화면에서 근거 묶음·미완료 안내 및 독립 160/시작 힌트 18 유지 확인.

## 2026-09-23 — Pillar/Phrase 근거 분리 1단계 완료

- pillarCandidates의 phraseStarts 입력 제거. 독립 계산은 시작음 위치와 무관하게 실행. pillarDisplay.ts의 composePillarDisplay가 표시용 phraseHints와 origin을 별도로 합성한다. 독립 후보의 이유/등급/대응 증거를 바꾸지 않는다.
- 시작 힌트로만 추가한 음은 보라색, 독립 후보는 기존 등급 색 유지. UI 후보별 목록에 출처 명시. shared 보기는 독립 대응 후보만 표시. Phrase/원본/검색 로직 변경 없음.
- 시작 위치 이동/제거 불변성, 힌트 제거 복원, 짧은 엇박 보존, stale 참조, shared 제외 검사를 포함한 21개 테스트 및 TypeScript 검사 통과.
- Can't Smile Without You 화면: 독립 160개 + 표시 힌트 18개. 보라색 18개 확인. shared 보기 후보 112개/렌더링 98개 및 힌트 0개 확인. 표시 토글 전후 프레이즈 선택 목록 동일.
- 2단계의 구조화된 근거·중복/간접 순환 감사 및 Pillar→Phrase 검토 로직은 아직 미구현. 관련 설계 문서에 단계 상태 갱신.

## 2026-09-23 — Pillar/Phrase 순환 방지 구체 계획

- docs/pillar-phrase-evidence-firewall-plan.md 작성. 독립 후보/시작 표시 힌트 분리, 구조화된 출처, 중복 제거, 읽기 전용 검토, 작품 단위 평가와 완료 조건 정의.
- 현재 시작 힌트도 reasons.length를 바꾸며 shared 보기도 독립 후보만은 아니라는 점 기록. 다음 구현 범위는 독립 계산과 표시 힌트 분리.
- 이번에는 설계 문서만 작성. 기존 분석/렌더링과 프레이즈 경계는 변경하지 않음.

## 2026-09-23 — 프레이즈 시작음의 기둥 후보 가치 보강

- 화면에 표시하는 동일 phraseSpans의 startNote ID/phraseNumber를 optional phraseStarts 입력으로 전달한다. 짧은 음/엇박/다운비트 여부와 무관하게 유효한 시작음은 후보로 보존하며, 이유에 현재 프레이즈 해석 의존성을 표시한다. 시작음 단독 근거는 tentative이며 확정 구조음이 아니다.
- 프레이즈 경계를 새로 계산하거나 변경하지 않는다. 반복 공통 보기는 여전히 반복 대응이 있는 후보만 표시한다. 원본/화성/검색 불변, 특정 곡 조건 없음.
- 짧은 엇박 시작음, 근거 제거 시 복원, 오래된/잘못된 참조 무시, 원본 불변 검사 추가. 관련 19개 테스트 및 TypeScript 검사 통과.
- Can't Smile Without You 브라우저: 전체 후보 178개, 현재 페이지 표시 162개, 시작음 근거가 있는 색칠 음 20개 확인. 자동 프레이즈 경계가 잘못된 경우 이 근거도 잘못될 수 있다.

## 2026-09-23 — 기둥음 전체/반복 공통 골격 검토 보기

- PillarReviewPanel에 전체 기둥 후보 / 반복 공통 골격 후보 선택 추가. 공통 보기는 correspondences가 있는 기존 후보만 추리는 비파괴 필터이며 별도의 심층 축약 알고리즘이나 확정 구조음 등급이 아니다. 단발성 중요 음이 제외될 수 있음을 명시.
- 후보별 대응 음 목록에서 마디·박·음높이, 조옮김 반음, 대응 구간 시간 배율, 규칙 버전 표시. 분석 결과 재계산 및 악보 재조판 없이 memoized 후보를 필터링하여 색칠만 전환한다.
- 필터 가역성/원본 및 provenance 보존/빈 결과 테스트 추가. 관련 17개 테스트와 TypeScript 검사 통과.
- Can't Smile Without You 브라우저에서 전체 160개(로딩 페이지 표시 144개) → 공통 112개(표시 98개) → 전체 복원 확인. 원본/화성/Phrase/Motif 변경 없음. 기존 관련 없는 작업 파일은 유지.

## 2026-09-23 — Pillar v0.3 반복·장식 변형의 공통 음 보강

- pillarVariation.ts: 4음 기준 창과 4–6음 비교 창을 정렬한다. 첫음 기준 조옮김, onset 간격의 0.5–2배 확대/축소, 짧은 삽입음 최대 2개, 내부음 하나의 1반음 변화 허용. 대응 onset 오차는 기준 창 첫/끝 onset 간격의 8% 이내. 끝음은 조옮김 후 일치해야 한다.
- 실제 일치한 음만 양방향 note ID / transposition / timeScale / ruleVersion 근거 보존. 바뀐 내부음과 삽입 장식음은 대응 근거에서 제외한다. 쉼으로 떨어진 창, 음높이 정보가 빈약한 반복, 리듬만 같은 창은 배제한다.
- 128 attack 거리의 제한된 앞방향 비교, 음당 최대 8개 근거. 장거리 전체곡 정렬, 구간 전체 계층 축약, 완전한 Motif 가족 분류는 아니다. 4음보다 짧은 골격 대응은 아직 지원하지 않는다.
- 기존 기둥 후보의 시간/진입/왕복 근거 gate를 유지하며 공통 골격 증거를 추가한다. 오른쪽 후보별 근거에 상대 마디·박을 표시한다. 특정 곡/마디 예외 없음. 화성 판정, 원본, Phrase/Motif 경계 변경 없음.
- 삽입 장식, 조옮김, 시간 확대, 약한 변형, 리듬-only 오탐, 반복음, 쉼, 원본 불변 테스트 포함 총 12개 테스트 및 TypeScript 검사 통과.
- 렌더러 계약 포함 최종 15개 테스트 통과. 브라우저에서 Can't Smile Without You의 4마디→30마디, 5마디→13/31마디, 6마디→14마디 대응 설명 확인. 후보 160개, 현재 3쪽 표시 144개. 음악적 타당성은 사용자 검토 대상이며 후보 증가를 정확도 향상으로 단정하지 않는다.

## 2026-09-23 — Pillar v0.2 박 단위 표면 골격

- 작품별 예외 없이 XML 박자 timeline을 입력하여 기준 박 이상 지속+박 위치, 쉼 뒤 진입, 엇박의 다음 박 점유, 4박자 중간 강박을 후보 근거로 추가. 복합박자(6/8 등)는 점음표 pulse 사용. 복합/비정형 조합 박자는 추정하지 않고 기존 근거만 사용.
- 한두 박 이내 연속 A–B–A 순차 왕복에서 기준 박에 놓인 첫 A를 축약 가설 후보로 보존한다. 내부 B를 비화성음으로 확정하지 않는다. 이는 국소 규칙이며 전체 계층 축약/변형 정렬은 미구현.
- Can't Smile Without You 브라우저에서 4마디 F#, 6마디 양음, 7–10마디 주요 음, 12마디 업빗 D의 색칠 확인. 11–12마디 B는 왕복 기준음 후보. 후보 증가가 음악적 정확도 향상 자체를 의미하지는 않는다.
- 화성 모듈, 원본/Core, Phrase/Motif 경계 및 검색 데이터는 변경하지 않았다. 9개 단위 테스트 및 TypeScript 검사 통과.
- 재현 사례: K:/Music Analysis/reports/reviewer-cases/pillar-beat-anchors-2026-09-23 (전체 XML, API snapshot, 사용자 대안 annotation, SHA256). Gold/training 대상 아님.

## 2026-09-23 — 서버 재시작 및 기둥음 색칠 실제 검증

- localhost:5173 서버를 재시작했다. Three Times a Lady 악보 렌더링 정상 확인.
- 재생/search용 SVG ID와 Pillar 패널의 추정 ID 불일치로 후보가 0개 표시되는 문제 발견. 렌더러가 원본 XML note 순서를 data-source-note-index로 SVG에 전달하고 패널이 이를 사용하도록 수정했다. 검색/재생 ID 및 분석 규칙은 유지한다. 이 인덱스는 동일 XML의 뷰 연결용이며 영구 Canonical ID가 아니다.
- 브라우저에서 후보 69개 중 현재 로딩된 3/4쪽에 67개 색칠 확인(스크린샷 및 DOM). 토글 해제 후 표시 0개, 기둥음 title 제거 및 색상 스타일 복원 확인. 원본 XML·Phrase·Motif 변경 없음.
- pillarCandidates 및 renderer contract 테스트, TypeScript 검사 통과. source-note 매핑 계약 회귀 검사 추가.

## 2026-09-23 — Pillar 버튼 영문 명칭 적용 및 브라우저 점검

- PillarReviewPanel 토글을 Highlight Pillar Notes / Hide Pillar Highlights로 변경하고 후보 표시 설명을 추가했다. 색칠 on/off 로직과 원본/경계는 유지.
- pillarCandidates4테스트 및 TypeScript 검사 통과. 기존 HAKUNA MATATA 브라우저에서 Highlight Pillar Notes 버튼과109개 후보 표시 확인. 다만 Verovio WASM 메모리 할당 오류로 악보 자체가 렌더링되지 않아 실제 색칠 검증은 막혔다. 새 Three Times a Lady 검토 탭도 로딩 지연 후 브라우저 조회 timeout. 클릭 색칠 성공으로 보고하지 않는다.

## 2026-09-23 — 기둥음 후보 색칠 초판 및 화성 확장 계약

- pillarCandidates.ts/PillarReviewPanel 추가, 기존 FullScorePage 오른쪽에 실험 토글. 지속/도착/공백/첫박/4음 반복 근거를 모아 원본 음표 anchor 색칠. 원본/검색/경계 변경 없음. Schenker 배경구조 판정은 하지 않는다.
- 사용자 요청에 따라 optional harmonyEvidence를 별도 채널로 설계. noteId/analysisId/version/evidenceRefs와 지지·충돌/AI·human 상태 보존. 화성 미입력 시 기존 결과 유지. API/화성 adapter와 세부 UI는 화성 모듈 단계에서 추가한다.
- 설계·제한: docs/pillar-candidates-v01.md. 브라우저 실제 표시 검증은 미완료.

## 2026-09-22 — 지속시간 evidence 제한적 운영 반영

- S-STRUCT-006/kysing/28021.xml의3성부에 sd/stm만 notes JSON에 추가. U: 원본 hash/기존 notes 동등성 검증, exact before/after 행 백업, 단일 트랜잭션/저장 확인. ID/음가/grams/피드백 참조 유지. 전체 DB 백업이나 재색인은 아님.
- 004/005는 예상ID 조회 실패로 제외,Three Times a Lady 공격음 변경은 보류. 기록/행 백업: `K:/Music Analysis/reports/tie-evidence-publish-2026-09-22/`. 실제 viewer 신규 표시 검증은 아직 미완료.

## 2026-09-22 — 지속시간 증거 API·Phrase/Motif 끝음 표시 연결

- sounding-evidence.mjs에서 유효한 sd/stm만 optional soundingEvidence로 전달. corpusNotes/구조 snapshot API와 CorpusNote 타입 연결. 검색 durationRatio/경계 점수는 유지한다.
- FullScorePage 공통 끝음 표시에서 실제 지속이 더 길면 검색 음가와 실제 tie 지속 quarter를 병기. 과거 row는 기존 표시 유지하며 데이터 부재를 추정하지 않는다.
- 관련2파일4테스트 및 TypeScript 검사 통과. 운영 DB 미갱신/새 표시 브라우저 실증 미완료. `K:/Music Analysis/reports/tie-staging-2026-09-22/API_AND_VIEWER.md`에 범위와 배포 전제 기록. 기존 unrelated edits는 보존했다.

## 2026-09-22 — Tie 수정 staging 인덱스 및 구조 회귀

- 운영 DB와 별개 audit.sqlite에4원본9성부 저장, row export로 현행 경계 분석. sd/stm은 soundingEvidence로 분리하고 점수에 미반영임을 assert. API 운영 연결/DB 갱신은 아직 없음.
- 기존 event onset+pitch 매핑 전부 성공. API snapshot의 meter/기보 문맥 보강 후 사용자 선호11/12로 이전과 같음.004/005/006 경계 동일,Three Times a Lady 양손각1attack복원/상성부 기존 경계동일/하성부 기존 경계점수1곳변화. 간소입력 meter 누락으로 생긴 초기 검사 차이는 검사기를 수정했다.
- 산출물/입력 계약/제한: `K:/Music Analysis/reports/tie-staging-2026-09-22/README.md`. 운영 코드/화면은 이번 단계에서 변경하지 않았다.

## 2026-09-22 — 운영 파서 tie 연속성 및 지속시간 보존 수정

- build-musicxml-search-index.py: 최고음 투영 전 성부/pitch tie 검증, 별도 sd/stm 증거 보존. 기존 검색 d 유지. 투영 후 합산에도 onset/release 연속성 검사 추가하여 쉼을 건너 합산하지 않는다. tieWarnings 추가. 운영 DB 재생성/API의 새 필드 소비는 아직 하지 않았다.
- 복합4테스트 통과. 실제4원본+4변형 회귀에서004/005/006 검색음열 동일. Three Times a Lady87–88마디 끊긴 tie 분리로 양손각1음 증가, 입력별 start/stop 경고8개. 후속 index ID 이동 가능성을 migration risk로 기록했다.
- `K:/Music Analysis/reports/production-tie-fix-2026-09-22/README.md` 및 전체 출력/hash 저장. 기존 unrelated 수정 보존. UI 변화/전체 corpus 정확도 향상은 주장하지 않는다.

## 2026-09-22 — 복합 tie 운영 파서 진단2건 재현

- `K:/Music Analysis/audit_complex_ties.py`로4합성 XML을 실제 parse_musicxml에 입력. 정상 마디간 tie/최고음 유지 tie는 기대 일치. 더 높은 attack 아래의 tie 지속은2→1quarter로 단축, 쉼을 건너는 malformed tie는1+쉼1+1을3quarter로 합산.
- 최고음 투영 후 tie 합산, 연속성 검사 부재가 각 원인이다. 검색 단선율 정책과 실제 sounding 보존 계약을 구분해야 하며 운영 수정/인덱스 재생성은 하지 않았다.
- fixture/전체 출력/코드 hash/한계: `K:/Music Analysis/reports/complex-ties-2026-09-22/README.md`. 실제 작품 발생 빈도나 프레이즈 영향은 아직 미측정.

## 2026-09-22 — 운영 XML 인덱서 tie 분할 검사

- production parse_musicxml 직접 호출, 기존4원본/4분할본 비교. 9성부(실제 변형5/대조4) 모두 onset/duration/pitch/기보 위치 동일. tie provenance 차이는 유지. corpusNotes 관련 매핑 후 경계 엔진 전체 결과9/9 동일.
- 인덱스/DB/운영 코드 변경 없음. UI/meter/notation 후처리 전체 E2E가 아닌 파서+경계 단위 검사. 최고음 투영과 tie 합산 순서가 실험 파서와 달라 화음 속 tie는 후속 검사가 필요하다.
- 원본/변형/전체 결과/한계: `K:/Music Analysis/reports/production-tie-notation-2026-09-22/README.md`.

## 2026-09-22 — XML tie 분할 불변성 실험

- 원본4악보에서 각10개 단순 음을 두 tie 음으로 나누는 복사본 생성. 실험 XML adapter의 sounding 합산→최고음 baseline→현행 경계 엔진 비교. 네 baseline 및 프레이즈 전체 결과 동일, 변형기2테스트 통과. 운영 인덱서/전체 meter·breath 입력 검사와 구별한다.
- 006 전체 sounding981음의 multiset은 같으나 동시음 순서가 달라짐(sourceElementIndex 정렬 의존). Three Times a Lady 원본/변형 모두88마디4개 unresolved tie 경고. 원인 해결은 하지 않고 미해결로 기록했다.
- 원본/변형/전체 출력/해시/한계: `K:/Music Analysis/reports/phrase-tie-notation-2026-09-22/README.md`. 운영 분석/UI 변경 없음.

## 2026-09-22 — 음높이 이동 프레이즈 불변성 검사

- `K:/Music Analysis/audit_phrase_transposition.mjs`와 테스트 추가. 고정4사례에 ±1/2/7/12반음, 총32변형을 경계 엔진 입력에 적용. 모든 경계 판정/강도/연속성 및 전체 분석 JSON 동일. 원본 입력 불변성과 XML/snapshot hash 확인, 변형 입력/전체 결과 저장.
- 신규3개+앞 검사기3개 테스트 통과. pitchMidi 입력 수준 검사이며 XML 이조→재파싱, 조표/화성/음이름의 전체 이조 검증은 아니다. 과분할 정확도를 보증하지 않는다. 운영 코드/UI 변경 없음.
- 결과 및 재현: `K:/Music Analysis/reports/phrase-transposition-2026-09-22/README.md`. 다음 대상은 tie 등 동등 기보 정규화다.

## 2026-09-22 — 프레이즈 선호 회귀·반복 일관성 자동 검사

- `K:/Music Analysis/audit_phrase_consistency.mjs`와 검사기 테스트 추가. 기존004/005/006 snapshot 및 Three Times a Lady 두 대안을 현재 경계 엔진으로 재분석하고 원본/hash/전체 결과/양쪽 경계 cue 보존. 선호 라벨과 복수 대안은 gold와 구분하며 운영 수정 없음.
- 선호12개 중11개 일치. 006 index51은 쉼·IOI 근거 .9로 남아 병합 선호와 불일치. Three Times a Lady는 두 대안 끝 경계 모두 검출되지만 내부1개/3개 추가 분할. 탐지된 반복 내부198전이 불일치0은 미탐지 반복의 정확도를 보장하지 않는다.
- 네 입력 결정론 확인, 검사기3테스트 통과. 결과: `K:/Music Analysis/reports/phrase-consistency-2026-09-22/README.md`. 실시간 viewer 전체 후처리/이조/기보 변경 테스트는 포함하지 않았다.

## 2026-09-22 — Three Times a Lady 첫 프레이즈 대안 사례

- 사용자 정정 링크의 Piano Solo 원본과 자동 분석 snapshot을 보존했다. 전주/5→8마디 첫2분음표/5→11마디 첫음의 두 대안을 별도 human annotation으로 저장. 실제 XML 끝음은 Bb5와 Ab4이며 사용자 원문 유지. 앞뒤4–12마디 문맥과 전체 원본/source hash 연결.
- `K:/Music Analysis/reports/reviewer-cases/three-times-a-lady-phrase-alternatives-2026-09-22/README.md`. 단일 정답 선택/운영 경계 변경 없음. 긴 도착음과 긴 선율 공백을 별도 근거로 기록하며 화성/계층은 미확정.

## 2026-09-22 — 생략 후보 첫 사용자 검토 저장

- A Whole New World 21마디 B3–D4/skip-1: 사용자가 생략해도 무방한 과도한 장식 멜로디로 판단했다. 원문과 assistant 정규화 해석을 분리한 `K:/Music Analysis/reports/single-score-skip-paths-v01/1/human-annotation.json` 저장. source hash/event ID 및 원본 XML/문맥/반복 증거 연결.
- 반주로 재분류하지 않으며 원본/AI 가설/운영 분석 변경 없음. 사례 하나로 일반 임계값을 변경하지 않고 학습 데이터 적격성도 아직 미승인으로 유지한다.

## 2026-09-22 — 생략 후보 원본 오선 비교 화면

- `review_skip_scores.py`/`render_skip_scores.mjs`로 원본 XML의 추적 ID와 Verovio 조판을 연결했다. 후보 문맥과 동일 악보의 대응 반복 페이지를 나란히 표시하고 좁은 화면에서는 위아래 배치한다. 주황색 검토 음/파란색 대응 anchor, 차단 이유 표시. 원본 음표 삭제나 운영 분석 변경 없음.
- 원본 hash 대조, 강조 SVG anchor18개 존재 검증. 브라우저에서 첫 후보의 실제 오선/양손/조표/강조 표시 확인. 산출물은 `K:/Music Analysis/reports/single-score-skip-paths-v01/index.html`, 재현 방법은 같은 폴더 README. 현재 전체 페이지 문맥이며 정밀 발췌나 자동 판정 UI는 아니다.

## 2026-09-22 — 반복·완결 beam 기반 생략 경로 실험

- `single_score_skip_paths.py` 추가. 같은 악보의 대응 anchor 사이에 추가된 2–16개 attack 중 완결 primary beam/음가 비율/동일 성부/연속 시간을 만족하는 묶음만 미선택 대안 경로로 저장한다. tie·부분 beam·다른 반복에서 유지되는 음을 보호하며 후보들을 자동 병합하지 않는다.
- A Whole New World 검토용1개, Last Night 차단3개. 검토용은 반주 확정이 아니며 실제 선율을 생략할 위험이 남는다. 이전 partial 반복 결과를 hash 확인 후 재사용했으며 전수 탐색이나 정확도 향상을 주장하지 않는다.
- 22개 테스트 통과. 원본/입력/앞뒤 context/대응 증거/대안 전체 ID/코드 hash: `K:/Music Analysis/reports/single-score-skip-paths-v01/README.md`. 운영 분석/UI 변경 없음. 다음은 오선에서 원본과 대응 문맥을 함께 검토하는 단계다.

## 2026-09-22 — 복수 선율 경로 오프라인 비교 v0.1

- `single_score_paths.py`: 최고음 baseline, 원본 voice별 경로, 음정 이동/voice 연속성/상단 음역을 비교하는 두 전역 DP 경로 추가. 모두 미선택 가설이며 원본 event/tie/sourceIds/실제 공백 유지. Melody판이나 Phrase 정답 입력 없음.
- 두 우선곡의 상단 staff는 단일 pitched voice여서 voice 경로는 baseline과 동일했다. 약한 음역 가중치에서 화음 구성음 선택만 각각4/7개 달라졌다. 정확도 향상으로 보고하지 않는다. 모든 onset에 음을 선택하므로 반주 채움 문제는 아직 해결하지 못한다.
- 17개 테스트 통과. 보고서/원본/경로별 전체 전이/코드 hash: `K:/Music Analysis/reports/single-score-paths-v01/README.md`. 운영 화면/분석 변경 없음. 다음은 beam·리듬 단위와 반복 대응을 근거로 생략 허용 경로를 검토하며, 화성 의존 판단은 보류한다.

## 2026-09-22 — 반복 탐색 시간대 분산 및 긴 채움 후보 v0.2

- 단일 악보 오프라인 반복 탐색의 12,000회 예산을 시간 사분위 쌍/창 길이 bucket에 순환 배정해 후반부도 탐색한다. 양 끝 대응음 사이의 긴 낮은 음군을 새 후보로 생성하되 voice/tie/beam/시간 충돌을 보존하고 자동 제거하지 않는다.
- 두 Piano Solo 실행: A Whole New World 대응 창43→45, Last Night9→25. 겹친 창이며 정확도/독립 반복 수가 아니다. 둘 다 partial. 실제 긴 채움 후보는0개로 여전히 미해결이다. Last Night의 삽입 run3개는 낮은 음역 조건에 미달했다. 곡별 예외나 임계값 완화 없음.
- 13개 단위 테스트 통과. 원본 XML/전체 event/코드 hash/coverage/판정 및 한계는 `K:/Music Analysis/reports/single-score-recurrence-v02/README.md`와 같은 폴더에 보존했다. 운영 분석/UI 변경 없음. 다음 검토 대상은 복수 선율 경로와 리듬 변형 대응이며 화성적 연장은 보류한다.

## 2026-09-22 — 단일 악보 내부 반복으로 채움 후보 재검토

- 오프라인 `single_score_recurrence.py` 추가. 다른 편곡/기존 Phrase 없이 리듬 seed→삽입/누락 허용 대응→채움 후보 보호/변형 검토/보류. 반복의 유지 근거를 삭제 방지에 사용하며 반주/주선율 확정으로 해석하지 않는다.
- A Whole New World43개 대응 창,기존 후보2개 제외 보호/1개 보류. Last Night9개 대응 창,기존 채움 후보0개는 미해결. 둘 다12000정렬 예산 partial이므로 미발견/후반부 커버리지에 대한 부정 판단 금지. 겹친 창은 독립 반복으로 세지 않는다.
- 11단위 테스트 통과. 상세 보고서/원본/JSON/음열 검토표: `K:/Music Analysis/reports/single-score-recurrence-v01/`. 운영 viewer/분석 변경 없음. 원본 오선 오버레이,새 긴 채움 후보 생성,폭넓은 리듬 변형 정렬은 후속 단계로 명시했다.

## 2026-09-22 — 단일 악보 선율 후보 첫 오프라인 프로토타입

- 비교 상대 없이 작동하도록 Python 표준 XML adapter와 보수적인 낮은 채움음 후보를 구현했다. 원본 rational 시간/쉼/beam/tie/구성음/source reference 보존, tie 연결 후 baseline 투영. 실제 쉼이나 beam/tie와 충돌하는 후보는 억제한다. 원본·현재 운영 분석 변경 없음.
- Piano Solo만 입력한 두 우선곡 실행: A Whole New World353 baseline음 중3개 관계 후보, Last Night499 baseline음 중0개. 정답률이나 개선으로 보고하지 않는다. 국소 규칙만으로 이전의 긴 채움 음형 문제를 포착하지 못했으며 반복 기반 구간·경로 비교가 다음 단계다. 해당 곡에 맞춘 임계값 완화 없음.
- 테스트6개 통과. 코드와 검토표/원본/JSON/한계는 `K:/Music Analysis/reports/single-score-melody-v01/README.md`에 연결. HTML은 오프라인 음군 검토표이며 운영 악보 오버레이가 아니다. Melody판/기존 Phrase 라벨은 후보 생성 입력에서 제외했다.

## 2026-09-22 — Melody/Piano 편곡 격차6쌍 오프라인 감사

- 사용자 긍정 피드백이 있었던 A Whole New World/Last Night of the World 우선, Always With Me/Find the Way/Beauty and the Beast/Whole Nine Yards 추가 비교. 현재v1.16 분석을12판에 실행하고 원본 XML·자동 결과·hash·진단 정렬을 보존했다. 과거 사용자 승인 결과나 Melody 자동 경계를 gold로 간주하지 않았다.
- 핵심 발견: 반주가 melody gap을 채워 경계를 누락하는 경우와 추가 음형 때문에 과분할하는 경우가 함께 존재한다. Phrase 수는13→37,34→46,14→18,30→24,16→10,14→19. 개수 차이는 정확도 지표가 아니다.
- Last Night7–8마디 원본을 대조해 기준판의 긴 tie가 피아노판에는 실제로 없고 짧은 attack+반주 음형으로 바뀐 것을 확인했다. 가상의 tie/음가를 복원하는 방식은 피한다. A Whole New World13마디의1박 선율 공백이 피아노판에서는0으로 계산되는 것도 API 근거와 대조했다.
- 우선순위: 정보 보존형 선율 경로 → 선율 호흡/반주 활동 분리 → 골격/complete extent 반복 비교 → 화성 자료 후 비화성음·연장 판단. 기존 structural-reduction은 국소3음+화성 근거 중심이라 현재 문제의 직접 대체품이 아니다.
- 보고서: `K:/Music Analysis/reports/arrangement-gap-2026-09-22/README.md`. 원본12개와 전체 자동 결과는 같은 폴더에 보존. 운영 파서/경계/Motif 규칙은 변경하지 않았다. 진단 정렬은 반복 위치 오정렬 가능성이 있어 경계 이식에 사용하지 않았다.

## 2026-09-22 — 검색 성부와 최상성부 구조 분석 분리

- 사용자 원칙: 다른 파트/베이스 검색으로 들어와도 Phrase·Motif는 최상성부 기준, 베이스는 화성·프레이즈 호흡의 보조 근거. 검색 일치음·재생 성부·검색 work ID는 변경하지 않는다.
- `structure-stream.mjs` 일반 선택 정책: MusicXML part-list 배치 순서 → 위쪽 staff → 같은 staff 내 전체 성부 중앙 음높이. 파트 번호/검색 role 점수/특정 제목·마디 예외 없음. 검색용 structural 축약 성부는 제외하며 쉼마다 다른 성부로 전환하지 않는다. 이 선택은 의미론적 주선율 확정이나 시점별 최고음 합성이 아니다. 교차 성부/역할 이동 및 인덱스에 누락된 성부는 추가 검토 대상이다.
- 전체 악보 API의 opt-in `structure=1` 응답에 선택 근거와 별도 structureWork를 제공한다. 기존 검색 API 계약은 유지한다. source별 선택을64개 한도 캐시한다. 제한 미리보기/발췌는 허용된 검색 성부만 유지하며 UI에 제한 상태를 표시한다.
- FullScorePage의 Phrase/Motif·구간 검토·피드백·사례 미리보기는 분석 work를 사용한다. SVG는 검색/재생 앵커와 별도 analysisStreamId의 분석 앵커를 연결한다. 경계 화성은 기존 전 성부 sounding evidence를 사용한다. 베이스 호흡을 새 점수로 직접 반영하는 규칙은 추가하지 않았다.
- HAKUNA MATATA 검증: 원래 링크 P1:2:2/568음 유지, 구조 분석 P1:1:1/637음. 상성부로 직접 접속한 결과와 Phrase 분석 JSON 동일. Chrome에서 상성부 분석선과 서로 다른 검색·분석 성부 안내를 확인했다. work ID의 충돌 방지 suffix를 검토 API가 거부하던 검증식도 허용된 hex suffix에 한해 수정했다.
- TypeScript 검사 및4파일19테스트 통과. 선택 규칙3테스트는 비순차 part ID/role 무시/같은 staff 상성부/축약 제외/후보 없음 검증을 포함한다. 전체 곡의 음악적 타당성은 전수 검증하지 않았다.

## 2026-09-22 — 제안 보기 전환 시 전체 재조판 제거

- FullXmlNotation의 XML→Verovio 조판 effect에서 Phrase/Motif/제안 범위를 분리했다. 원본 음표에 렌더용 ID를 최초 한 번 부여하고, 현재 분석 범위의 DOM 앵커는 별도 layout effect에서 연결한다. tie chain은 같은 part/staff/voice의 기존 규칙을 유지한다. 음표 매칭 결과는 현재 조판 인스턴스 안에서 재사용하며 원본 XML이나 Canonical IR은 변경하지 않는다.
- SVG 페이지를 memo 컴포넌트로 유지해 오버레이/선택/로딩 상태 변경으로 내부 SVG DOM을 재설정하지 않는다. 제안 범위 전환 시 기존 페이지와 지연 로딩 상태를 유지한다. Phrase 클릭의 페이지 탐색은 최신 범위를 참조한다.
- 렌더링 작업 중과 지연 로딩 대기를 구분했다. 대기는 '표시 준비 완료 · 나머지 페이지는 스크롤하면 불러옵니다', 실행 중은 '악보 렌더링 진행 중'으로 표시한다. 작업 중 추가 로딩 버튼은 비활성화한다.
- TypeScript 검사 및 5파일22테스트 통과(기존 tie/악보 설정/여백/preview20개 + 조판 의존성·memo 계약2개). 새 계약 테스트는 소스 구조 검사이며 브라우저 통합 테스트를 대체하지 않는다. 첫 테스트는 설치된 TypeScript 패키지에 compiler AST API가 없어 실패하여 런타임 AST 의존성 없는 계약 검사로 정정했다.
- Chrome에서 3/6 대기 안내, 추가 로딩 후6/6 완료, 제안 보기 전환 후6/6 유지와 제안4범위·기존 Motif 표시를 확인했다. 최초 XML 조판은 여전히 메인 스레드에서 실행한다. 최초 로딩의 시간별 프로파일링/Worker 이전/세션 간 SVG 캐시는 이번 변경에 포함하지 않았으며 속도 향상 비율은 측정하지 않았다. 작품별 예외 및 분석 규칙 변경 없음.

## 2026-09-22 — 제안 범위 상단 여백 및 페이지 내 배치

- 제안 Phrase 표시를 기존 Motif 스타일에서 분리했다. 페이지 첫 줄은 라벨·끝점까지 들어갈 상단 여백(52 CSS px)을 확보하고, 제안선은 각 system 위 별도 lane에 배치한다. 페이지 상단과 좌우 경계를 기준으로 표시 좌표를 제한하며 긴 시작 라벨은 오른쪽 밖으로 넘치지 않게 안쪽으로 이동한다. 좁은 화면에서 라벨만 말줄임하며 전체 문구는 title/접근성 이름에 유지한다.
- 전체 악보의 실제 page/system/note 좌표를 사용한다. 악보 ID·마디 번호별 예외, Phrase/Motif 분석 결과 및 사용자 제안 범위 변경 없음. 기존 현재 경계와 Motif 좌표 계산은 유지한다.
- 순수 배치 함수 회귀4개와 기존 여백2개/preview1개, 총7테스트 및 TypeScript build 검사 통과. Chrome 제안 보기에서 페이지 전환부와 오른쪽 끝의 라벨이 종이 안에 배치되고 제안선이 마디 번호 위로 분리되는 것을 스크린샷으로 확인했다. 반응형의 좁은 폭 경계는 단위 테스트로 검증했으며 모든 악보의 실화면 전수 검증은 하지 않았다.

## 2026-09-22 — 현재 경계 / 사용자 제안 Phrase 미리보기 전환

- 읽기 전용 structure-preview API와 StructurePreviewPanel 추가. 저장 사례의 사용자 제안 범위를 불러온다. 특정 work 분기를 넣지 않으며 feedback-revision-02.json이 있는 사례를 검색한다. 알고리즘이1334후보 중 자동 선택한 결과로 표시하지 않는다.
- 작품/성부/전체 음표 identity와 범위 ID·정렬·중복을 검사한다. 제안 보기에서는 baseline Phrase 띠/패널을 숨기고 상단 제안 점선과 기존 Motif를 표시한다. 다시 현재 경계로 돌아가면 원본 분석 표시가 복구된다. 분석 데이터/피드백 자체는 수정하지 않는다.
- Chrome 실제 악보에서32–39/40–47/48–55/56–65 네 범위의 오버레이와 패널 목록, 현재 경계 복귀를 확인했다. 제안 화면을 켜 두었다. 페이지 지연 로딩에 따라 띠는 양끝 페이지가 렌더링된 뒤 나타난다.
- TypeScript build 검사 및 범위/identity 검사3테스트 통과. 기존 test-only node:fs import가 browser tsconfig에서 오류를 일으켜 해당 테스트 import에 한정한 expect-error 주석을 추가했다. 검토 화면은 Vite 로컬 개발 API이며 별도 production 서버 배포 기능은 아니다.

## 2026-09-22 — 경계 독립 반복 범위 및 상하위 대응 검토

- `repeat-hierarchy.mjs` 추가: 리듬 seed→선율/윤곽→가변 길이 도착음 범위 정렬. 기존 Phrase 분할을 탐색 입력에서 배제했다. 공통 시작의 짧은/긴 반복을 parent/child로 연결하며 부분 모티프만으로 상위 경계를 결정하지 않도록 근거를 분리한다.
- 기존 경계 연결은 후보 생성 이후 별도 함수에서 수행한다. partial-frame 충돌, 대응 지점의 쉼 차이, 시작 경계 누락과 keep/group 대안을 기록한다. 화성 판정·자동 병합·UI 변경 없음.
- S-STRUCT-009의 선호4범위를 모두 후보로 회수. 다만1334후보 및20000정렬 한도 partial로 과잉 후보 정리/선택은 미완료다. 008은1731정렬48후보. 원본/입력/코드/피드백 hash와 보고서를 evaluation/reports/repeat-hierarchy-{008,009}-v1에 보존했다.
- 첫4000정렬 테스트에서 큰 반복이 누락되어 원인을 예산 순서로 확인했다. 오프라인 예산을20000으로 명시하며 실시간 운영 활성화는 하지 않았다. 절대 마디/제목/work ID 예외 없음. 상세 계약과 한계는 REPEAT_FIRST_ANALYSIS_PLAN.md에 통합했다.
- 최종 서버49파일342테스트 통과. 전체 병렬 실행에서 신규 실사례 테스트가 기본5초를 넘겨 시간초과했으므로 해당 오프라인 테스트만20초로 지정했다(알고리즘/정확도 임계값 변경 아님). 별도 실행 약4초, 부하 시6초 이상으로 실시간 적용 전 성능 개선이 필요하다.

## 2026-09-22 — S-STRUCT-009 범위 정정 및 복수 해석 보존

- 사용자 정정32–39 /40–47 /48–55 /56–65를 feedback-revision-02.json에 event ID 범위[49,67)/[67,86)/[86,105)/[105,129)로 보존했다. 마지막 D5는63마디 onset에서65마디까지 이어지는 누적 타이음이므로63마디에서 범위를 자르지 않는다.
- 첫 등장 Phrase1+2는 상위 한 Phrase로 묶는 것을 선호하되 기존 분리도 허용한다는 의견을 함께 저장했다. 단일 정답으로 강제하지 않는다. 기존45–50마디 질의는 superseded로 표시하고 원문은 유지했다.
- v1.16 기준 내부62/95/99/116 경계와48마디 시작86의 누락을 다음 일반 규칙 평가 대상으로 지정했다. 이 index/마디는 평가 데이터일 뿐 운영 분기에 쓰지 않는다. 새 production 변경 없음.

## 2026-09-22 — 화면 반영 확인과 MERRY-GO-ROUND 반복 경계 진단

- ALWAYS WITH ME 라이브 API v1.16 및 Chrome 화면에서 Phrase2 12–20마디, Phrase12 70–73마디를 확인하고 최신 악보 탭을 열었다.
- S-STRUCT-009에 MERRY-GO-ROUND OF LIFE의 전체 XML/전체 snapshot/사용자 설명을 저장했다. Phrase1+2와6+7의18개 pitch가 모두 일치하나 rhythm/rest는 다르다. index58은 recurring-motif-answer-continuation이 raw .925를 .49로 억제했고62는 원형13에 없는1quarter gap으로 .833 경계가 됐다. 반복 미탐만이 아니라 부분 frame 보정과 국소 쉼 검출의 충돌이다.
- 추가45–50마디 의견은 feedback-addendum.md에 보존. API상45마디는 C5–Bb4–C5이고 첫 주제 재등장 D4–G4–Bb4–D5는48마디(index86)여서 시작음 확인 전 임의 경계 변경을 하지 않았다. 이 새 사례에 production 규칙 추가 없음.

## 2026-09-22 — 짧은 음형의 인접 변형 반복을 Phrase 내부로 묶기

- 사용자 추가 의견: ALWAYS WITH ME(v1.15) Phrase12와13을 병합. 현재 API에서도 v1.15/274음 및 경계226/230/241을 확인했다. 70마디 G4–B4–D5–G5와71마디 F#4–A4–D5–F#5는 동일 리듬의 상승 음형 변형이다. 기존230 경계는0.5quarter 쉼과 pitch/IOI 도약으로 strength1이었다.
- v1.16 `short-cell-continuity.mjs`: frozen 경계 안의4–8음/최대4기준박 짧은 단위와 다음 구간의 시작 음형을 비교한다. 동일 음가/attack간격, 동일 윤곽, 음정 차이2반음 이내, 후속 구간 최소2배 attack 수, 더 긴 최종 호흡을 모두 요구한다. 긴 쉼·호흡표기·타이 continuation·박자 미상/변화는 제외한다. 악보 ID/제목/절대 pitch/특정 마디 예외 없음.
- 해당 경계는 subphrase-cell 근거로 보존하고 Phrase만 합친다. 별도의 Motif 가족 확정/번호 지정은 하지 않는다. 화성 완결성은 판단하지 않는다. `shortCell:false`로 이 규칙만 비활성화 가능하며 API 캐시 버전에 모듈을 추가했다.
- 초기5사례 비교에서008의230 경계만 변경,004–007은 불변. 재현 스크립트 scripts/capture-short-cell-review.mjs는 원본 XML/hash 참조, 앞뒤 contextNotes, 사용자 설명과 전후 결과를 evaluation/reports/short-cell-008-v1/case.json에 저장한다. 전체 서버 회귀 결과는 아래 후속 기록을 참고한다.
- 최종 서버 회귀48파일338테스트 모두 통과. 사례 파일 저장 완료. 운영 브라우저에서 새 버전의 실제 렌더링은 아직 미확인이다.

## 2026-09-22 — 전체 반복의 짧은 내부 호흡 일반 규칙 운영 적용

- 사용자 승인으로 Phrase 엔진 v1.15에 `whole-repeat-duration-rest-continuity`를 활성화했다. 단일 Phrase 대 인접 두 Phrase의 전체 대응과 정확한 국소 음가→쉼 치환을 함께 요구한다. 제목/work ID/특정 마디/절대 음높이 분기는 없다. 이전 실험 후보를 모두 승인하는 변경이 아니다.
- 긴 쉼·명시적 호흡·미상 박자·타이 continuation 등을 보호한다. 동일 attack 수와 동일 템포에 한정하며 화성 해석은 하지 않는다. frozen baseline 비교와4096회 한도를 사용하고 `repeatBreath:false`로 롤백 가능하다.
- ALWAYS WITH ME 저장 사례에서 index35만 억제되어 기존 Phrase2+3이 합쳐지고 양끝30/60은 유지됐다. 다른004–007 저장 사례의 경계는 모두 불변. 제목/ID/조옮김/printed measure 변경 테스트도 통과했다.
- 관련3파일47테스트 통과. 결과는 evaluation/reports/repeated-breath-production-v1/regression.json. API Phrase 캐시 버전에 새 모듈을 포함하고 UI 근거 설명을 추가했다. 실제 실행 서버 재시작/브라우저 결과 검증은 별도이며 이번 테스트만으로 화면 적용 확인을 주장하지 않는다.
- 추가 서버 전체 회귀:47파일334테스트 모두 통과.

## 2026-09-22 — 반복 검토 보고서 수동 불러오기 UI

- 오른쪽 RepeatReviewPanel에서 review-ui.json을 수동으로 불러와 후보 하나를 선택한다. 작품/성부와 전체 음표 ID·pitch·onset·duration·마디/박 일치를 확인하고 범위 참조를 검증한다. 원본 XML 전체 동일성을 검증하는 기능은 아니다.
- 원형/재등장 범위를 기존 Phrase/Motif와 별도의 점선 높이(+44px)에 표시한다. 끝 표식 포함, 검토 표시 끄기 가능. 내부 렌더러의 범위 매핑을 재사용하되 reviewOnly는 Motif 가족/분석/번호 데이터에 포함하지 않는다. 제한 미리보기에서는 비활성화한다.
- 평가 스크립트가 review-ui.json을 추가 출력한다. 첫 자료는 evaluation/reports/repeat-review-ui-008-v1/review-ui.json. 기존 경계 자동 수정·피드백 저장·실시간 분석 API는 이번 범위가 아니다.
- TypeScript build 검사 통과. 실제 브라우저의 위치·가독성 시각 검증은 아직 미실시이며 다음 확인 대상이다.

## 2026-09-22 — 반복 검토 예산 분배와 기존 경계 대조

- 가변 범위 리뷰를 그룹별 round-robin(v0.2)으로 변경했다. 그룹별 정렬 수·미검토/partial 상태를 보존한다. 상위 반복 탐색과 그룹 내부 순서의 편향은 아직 남으며 전체 악곡 균등 탐색이라고 주장하지 않는다.
- `server/repeat-boundary-review.mjs`에서 후보 생성 후 저장 당시 Phrase 경계를 event ID로 대조한다. 동일 범위쌍은 중복 제거하고, 직접 대응된 attack의 경계 차이를 보고하되 자동 병합은 하지 않는다.
- 004/006/008 v2 보고서에서 고유 범위쌍22/33/43개, 경계 차이가 있는 범위쌍1/21/4개. ALWAYS WITH ME의 원형4–12마디/재등장12–20마디 내부 경계0/1 차이가 리뷰에 올라왔다. 범위 대안 수를 오류 수로 해석하지 않는다.
- 관련5파일26테스트 통과. 신규 검증은 작은 예산의 그룹별 배분, baseline 불변, 대응 경계 차이 및 일치 반례를 포함한다. UI/운영 경계 변경 없음. 상세는 REPEAT_FIRST_ANALYSIS_PLAN.md, 보고서는 evaluation/reports/repeat-elastic-{004,006,008}-v2.

## 2026-09-22 — YouTube 제목·작곡가 이중 검증

- `Always With Me`라는 제목만 공유한 찬송가가 히사이시 조 작품에 연결된 오류를 수정했다. 기존 제목 전용 캐시는 무효화하고 공개·한국 재생 가능·외부 삽입 가능 상태를 API로 확인한 `G8UKEJQLkNs`를 작품 ID `work-15fa42f2e80b3722`에 연결했다.
- 결과 카드가 수집 요청에 workId·title·composer를 함께 전달한다. 후보는 제목뿐 아니라 영상 제목·채널·설명의 작곡가 크레딧도 일치해야 하며, 작품 ID별 캐시를 제목 공용 캐시보다 우선한다.
- YouTube Search Queries 분당 제한은 일일 소진으로 고정하지 않고 다음 실행에서 재시도할 수 있게 했다. `quotaExceeded`와 `dailyLimitExceeded`만 당일 소진 상태로 유지한다.

## 2026-09-22 — 준비부 대응과 가변 길이 반복 범위 후보

- `server/repeat-elastic-extent.mjs` 추가. 리듬 우선 탐색 이후 앞3음/뒤4음의 제한 범위에서 준비부 대응과 서로 다른 attack 수의 종결을 검토한다. 선행 음정·리듬의 별도 검증과 최초 anchor/양끝 직접 대응을 요구한다.
- 내부 긴 쉼/호흡표기를 보호하고 박자 미상·변경은 보류한다. 준비부의 attack 수가 다른 경우, 엄격한 split/merge 의미 판정, XML rest 검증, 화성 완결성은 미완료로 명시했다. 특수 work ID/마디/pitch 예외 없음.
- 004/006/008 저장 악보를 실행해 후보12/44/71개를 보존했다. 004/008은500정렬 예산 소진,006은236정렬로 제한 범위 완료. 후보 수는 정확도나 독립 등장 수가 아니다. 운영 경계/UI 변경 없음.
- 보고서는 `evaluation/reports/repeat-elastic-{004,006,008}-v1`이며 입력/XML/코드 hash를 기존 manifest에 포함했다. 상세 계획과 미보정 필터는 `REPEAT_FIRST_ANALYSIS_PLAN.md`의 R3 2차에 통합했다.
- 관련5파일24테스트 통과. 신규7테스트는 준비부 회수·서로 다른 attack 수·관련 없는 선행 pitch/음가 반례·긴 호흡 및 박자 미상/변경·예산 한도·입력 불변을 확인한다. 음악적 정확도 평가는 별도이며 독립 holdout 검증 전이다.

## 2026-09-22 — 일일 KY·YouTube 수집

- KY 공식 조회 100개에서 100개를 신규 매칭해 누적 1,704개가 됐다. 원본 XML과 검색 DB는 변경하지 않았다.
- YouTube는 API 키가 설정됐지만 Pacific 날짜 상태에 분당 제한 HTTP 429가 남아 있어 추가 호출 없이 안전 중단했다. 기존 92/95 호출과 cursor 1,344를 보존했다.

## 2026-09-22 — 반복 창 중복 정리와 종결 범위 리뷰

- `server/repeat-extent-review.mjs` 추가. 같은 상대 위치의 포함 창을 최초 대표에만 묶어 변형의 변형으로 범위를 무제한 확장하지 않는다. 그룹은 가족 판정이 아니며 운영 Phrase/Motif를 바꾸지 않는다.
- 양쪽 대응 종결음의 기준박 대비 음가·뒤 쉼으로 끝 후보를 수집하고, 내부의 긴 쉼/호흡표기를 가로지르면 차단한다. 화성/종지 판단 없이 `cannot_judge`를 유지한다. 시작 준비부 복원과 XML rest 검증은 미완료다.
- S-STRUCT-008 v2에서300창→97그룹. 원형[0,30)과 사용자 제안 Phrase2+3 [30,60)의 전체 범위가 검토 후보로 회수됐다. 탐색은 여전히300정렬 예산의 partial이며 전체 회수율을 주장하지 않는다.
- 탐색/범위 리뷰9테스트와 기존 registry/정렬 회귀8테스트, 총17테스트 통과: 실제008 범위 회수, 중복 정리, 입력 불변, 내부 호흡표기 차단, 박자 미상 보류 포함. 결과와 코드/입력 hash는 `evaluation/reports/repeat-first-008-v2`에 보존했다. 상세 계획은 `REPEAT_FIRST_ANALYSIS_PLAN.md`의 R3 상태를 갱신했다.

## 2026-09-22 — 리듬형 우선 경계 독립 반복 탐색 착수

- 상세 단계/계약/한계/검증 기준을 REPEAT_FIRST_ANALYSIS_PLAN.md에 정리하고 문서 지도에 연결했다. 리듬형 선탐색→선율 약한 변형→전체 정렬→기존 경계 재검토 순서를 따른다.
- server/repeat-first.mjs는 Phrase 경계 없이 attack열 시작쌍을 비교한다. 조옮김/약한 선율 변화와 상대 onset 간격을 허용하고, 정렬 후 duration/rest 재배분 후보를 별도 보존한다. 저정보 반복음과 미보정 후보를 확정 가족으로 부르지 않는다.
- S-STRUCT-008 원형0/재등장30을 회수하고4/34의1.5박→1박+쉼0.5박 변형을 확인했다. 실행 결과는 evaluation/reports/repeat-first-008-v1. 정렬300회 한도로 partial이며28개 변형 관찰은 겹친 창 중복 포함이다. 전체 음악 회수율로 해석하지 않는다.
- 관련3파일14테스트 통과. 운영/UI 경계와 화성 해석 변경 없음. 다음은 후보 중복/예산 공정성, core/완결 범위, split/merge 리듬 비교를 강화하는 단계다.

## 2026-09-22 — ALWAYS WITH ME 반복 내부 호흡 사례

- S-STRUCT-008: Phrase2+3 병합 의견과 XML/입력/음표 ID를 보존. 원형의1.5quarter 음가가 재등장에서1quarter+0.5quarter 쉼으로 바뀌어 국소 분할이 생긴 것을 확인했다. 전체 결합 비교92/coverage93은 검토 증거이며 자동 병합 확률이 아니다.
- 반복 대응의 음가→쉼 치환을 검증할 사례로 등록. 화성 해석 및 운영 경계 변경 없음. 상세는 evaluation/cases/s-struct-008-review.md.

## 2026-09-22 — VOICES THAT CARE 경계 재배치 사례

- S-STRUCT-007로 원본 전체 XML/분석 snapshot/사용자 의견/ID 기반 구간을 보존. 10마디 무쉼 도착 뒤 경계 누락과14마디 최소attack 억제의 연쇄 영향을 구분했다.
- 원본 Ab3+C4와 Bb3를 확인하고 비화성음/전타음 해석은 사용자 가설로 분리했다. 화성 데이터 전 임의 확정 및 production 변경 없음. 상세는 evaluation/cases/s-struct-007-review.md.

## 2026-09-22 — EVAL-002 낮은 coverage 시작점 재평가 보완

- 인접 시작점 재평가가 raw cost만 비교해 16/17음 대응보다 10/17음 대응을 고르는 회귀를 수정했다. coverage가 포함된 similarity를 우선하고 동률에서만 raw cost를 사용한다.
- 정상 coverage는 기존 4개 lookback을 유지하고, 최초 coverage 75% 미만 실패 형태만 최대 8개로 확장한다. 전체 후보 scan이나 순위식을 넓히지 않았다.
- 같은 KYSing 원본을 쓰는 MEM01·MEM08 repeat-split은 결과 0건에서 모두 1위, 17/17 직접 대응으로 복구됐다. 서버 테스트 93/93 통과. 상세는 `docs/eval-002-held-arrival-alignment.md`.

## 2026-09-22 — EVAL-005 국소 옥타브 표시 정렬

- 한 음의 ±12 이동 때문에 해당 음이 deletion되고 뒤 음들이 밀려 강조되는 문제를 수정했다. 점수·후보·Exact는 바꾸지 않고 최종 API 정렬과 강조 관계만 제한적으로 재구성한다.
- 나머지 음이 한 조옮김 아래 전부 정확하고, 옥타브 residual 정확히 1개, 길이 차이에 해당하는 gap 최대 1개, 일반 substitution 0개일 때만 `octave-displacement`를 기록한다.
- 저장된 OCT01/02 단일·복합 네 사례에서 변경 음이 원본의 같은 pitch class에 직접 연결됐다. 복합 변형의 실제 omission gap은 유지됐다. 후속 EVAL-002 회귀까지 포함한 서버 테스트 93/93, production build 통과. 전체 회귀는 498/500이며 남은 2건은 기존 `FullScorePage` Motif 범위 테스트다. 상세는 `docs/eval-005-local-octave-alignment.md`.

## 2026-09-22 — EVAL-004 반복 위치 결과 표현 계약 확인

- 같은 작품의 반복 구간 때문에 대표 악보 조각과 테스트 의도 구간이 달라지는 문제를 검색 오답과 분리했다. 평가 자료는 작품 순위·대표 창 겹침·원래 반복 위치 포함 여부를 별도 필드로 보존한다.
- 운영 API와 결과 카드에 이미 구현된 반복 횟수·마디 및 파트별 등장 목록을 확인했다. 동일 작품을 반복 위치마다 중복 결과로 만들거나 특정 테스트 마디를 대표로 고정하지 않는다.
- 기존 65개 평가에서 대표 구간 차이 5개는 모두 작품 회수 성공이고 원래 시작 마디도 occurrence 목록에 있었다. 상세는 `docs/eval-004-repeated-occurrence-reporting.md`.

## 2026-09-22 — EVAL-003 반복 attack 분할·병합 의미 보존

- 한 지속음을 같은 음높이의 실제 attack 두 번으로 나눈 Query를 일반 누락으로만 설명하던 문제를 수정했다. 기존 insertion/deletion과 비용은 유지하고 정렬 step에 `repeat-split` 또는 `repeat-merge` 관계를 추가한다.
- 같은 음높이, 연속 onset, 공통 템포 아래 합산 음가가 모두 정확할 때만 관계를 붙인다. 타이·Exact로 승격하거나 점수·admission을 완화하지 않는다.
- 실제 repeat-split 10개는 모두 기존 1–4위 순위를 유지한다. 8개는 지속음↔두 attack 관계와 설명이 확인됐고, MEM01·MEM08은 작품의 다른 반복 위치에 실제 두 attack이 있어 17/17 직접 대응으로 표시됐다.
- 서버 테스트 89/89 통과. 상세 계약과 제한은 `docs/eval-003-repeat-attack-semantics.md`.

## 2026-09-22 — EVAL-006 반복음 Query의 엄격한 장식음 누락

- 반복음 Query의 박자·equality 하한을 낮추지 않고, 10음 이상에서만 기존 단일 누락 검증기를 허용했다. 유지된 모든 음의 높이·음가·도착 간격이 하나의 조옮김·템포 아래 맞고 내부 실제 attack 하나만 빠진 경우에만 low-information floor의 좁은 예외가 된다.
- 검증된 omission 경로는 더 높은 fuzzy alignment보다 강한 증거로 취급하되, 삽입 비용과 Similar 분류를 유지한다. 6음·8음 경계 Query, 두 음 누락, 유지 음의 음높이/음가가 다른 경우에는 적용하지 않는다.
- SH05 `2 Become 1`은 미회수에서 3위 Similar 96.45로, SH09 `WAY BACK THEN`은 작품 1위로 회수됐다. 2/4 DM03·DM04 네 조건도 모두 1–2위로 회수됐다.
- 관련 96/96 테스트 및 production build 통과. 전체 494개 중 492개 통과, 기존 `FullScorePage` Motif 범위 테스트 2개는 계속 실패한다. 상세 기록은 `docs/eval-006-strict-ornament-omission.md`.

## 2026-09-22 — EVAL-008 리듬 일치 반복 구간 선택

- 같은 작품 안에 조옮김 기준 interval이 같은 반복이 여러 번 있을 때 Melody + Rhythm 검색도 phrase evidence가 높은 interval 반복을 대표로 고르던 오류를 수정했다. 리듬까지 정확한 occurrence가 있으면 그 집합을 먼저 사용하고, 없을 때만 interval 대표 구간으로 내려간다.
- `SH02-L6-original`의 `ANGEL`은 기존에 131마디의 다른 리듬이 선택되어 Top 200 밖이었으나, 수정 후 Query 음가 `[0.5,0.5,0.5,0.5,1,0.5]`와 같은 137–138마디가 1위 Exact 100점으로 회수됐다.
- Melody Only, Exact 옵션, rhythm-exact가 없는 fallback은 각각 기존 의미를 유지하는 단위 테스트를 추가했다. 서버 집중 테스트 83/83 통과. 상세 기록은 `docs/eval-008-rhythm-occurrence-selection.md`.

## 2026-09-22 — EVAL-007 단일 음 변형 후보 회수

- 8–12음 Query에서 음 한 개가 바뀌면 겹치는 interval n-gram 두 개가 동시에 깨져 원곡이 정밀 평가 전에 사라지는 사례를 진단했다. SH03 원곡은 hits에는 있었지만 작품 후보 순위 6,963, 남은 anchor 안 459위였다.
- 일반 후보 수 확대와 검증 없는 anchor reserve는 폐기했다. 양끝 interval anchor 안에서 한 조옮김 아래 정확히 한 음만 다른 후보를 확인하고, Melody + Rhythm에서는 템포 정규화 리듬 90점 이상만 최대 40작품 복구한다. Exact 옵션·저정보량 Query에는 적용하지 않는다.
- 실제 SH03 재검색에서 `UN DI, FELICE` 6–9마디가 순위 없음에서 1위(97점)로 복구됐다. 후보 회수는 점수·Exact 판정을 우회하지 않고 기존 정밀 정렬과 admission 검사를 그대로 거친다.
- 서버 집중 테스트 79/79 통과. 전체 486개 중 484개 통과, 기존 `FullScorePage` Motif 범위 테스트 2개는 계속 실패하며 이번 검색 서버 변경 범위와 무관하다. 근거와 재현 조건은 `docs/eval-007-single-pitch-retrieval.md`에 기록했다.

## 2026-09-22 — 악보 페이지 상단 자동 여백

- Tell Me 화면에서 첫 system의 bounding box가 페이지 상단보다 약3.5px 위에 위치했다. 모든 전체 악보 페이지에서 SVG 대비 실제 system 위치를 측정하여 40px 상단 공간을 확보하도록 FullXmlNotation을 수정했다. 분석 이름표의 위쪽 돌출 공간도 포함한다. XML/음표/분석 결과는 변경하지 않는다.
- 여백은 SVG 기준으로 계산해 ResizeObserver 재실행 시 누적되지 않으며, 창 크기 변경과 지연 로딩된 페이지에도 재계산한다. 발췌 악보 경로는 변경하지 않았다.
- 실제 Tell Me 첫3페이지 확인: 추가 padding44/12/12px, system 상단 여유 각각 약40.5px. 브라우저 스크린샷으로 첫 줄 표시 확인. 재시작 후 꺼져 있던 로컬5173 서버도 복구했다.
- 다른 악보 When We Disco 첫3페이지도 padding44/9/9px, 상단 여유40.4–40.7px로 확인했다. 곡 ID별 예외는 없다.
- 새 여백 단위 테스트2개와 TypeScript 검사 통과. 함께 실행한 FullScorePage 검사21개 통과/모티프 범위 관련2개 실패(uses parallel relation cells / does not invent Motifs). 이번 레이아웃 작업에서 모티프 분석이나 해당 테스트 기대값은 변경하지 않았다.

## 2026-09-22 — 전체 작품 shadow registry / event 기반 사용자 의견 대조

- 검증:9개 파일39개 테스트 통과. 이는 회귀 검사이며 독립 악보에서의 음악적 정확도 평가는 아니다.

- 동결 baseline의 앞·뒤 반복을 모두 대조하고 self-overlap/순환 승격을 방지하는 registry 구현. 비교 예산과 partial 상태, 결합/유지 대안, 끝음/coverage 부족 사유를 보존한다.
- 기존3개 사례10,356회 정렬·102개 결합 검토. 문서상 위치가 명확한 의견12건 중11건 현행 일치, When We Disco index51 병합 요청은 미해결. 최고 유사도94 후보도 coverage60/끝음 미대응이라 자동 승인을 막아야 함을 확인했다.
- 원본/snapshot/의견 문서/코드 hash와 event 참조를 `evaluation/reports/structure-feedback-v2`에 저장. UI와 production 분석은 변경하지 않았다. 통합 계획의 오래된 상태 요약도 갱신했다.

## 2026-09-22 — 기존 사례 004–006 일괄 원본 대조

- 검증: 관련6개 파일25개 테스트 통과(실제3개 사례 재계산 포함).

- `audit-phrase-closure-cases.mjs`로 원본/snapshot/code hash를 보존한 오프라인 보고서 생성. 1,173개 음표 매핑,103개 현행 경계의 source/박자 대조 가능,34개 보호 조건 해당. 나머지69개는 병합 승인 아님.
- 001–003은 review-snapshot.json 부재를 기록하고 제외했다. 전체 결과는 `evaluation/reports/phrase-closure-cases-v1/review.md`. 사용자 정답 기반 정확도 평가는 아직 아니다.
- 실제3개 사례 회귀 테스트 추가. 운영 알고리즘과 화면 변경 없음. 통합 계획12절에 남은 event 기반 기대 경계 검증을 기록했다.

## 2026-09-22 — 박자 정규화 / 경계 보호 shadow 검증

- 최종 검증:7개 파일30개 테스트 통과. self-closing 빈 마디 상속 보강 후 코드 hash를 반영한 최신 결과는 `phrase-structure-shadow-v5/review.md`이다(v4와 음악적 결과 동일).

- 원본 박자표 기반 기준 박 환산과 보수적 보호 정책 추가. 복잡/변경 박자는 보류하고 기존 v1.14 보호 기준만 재사용한다. 운영 알고리즘/UI는 변경하지 않았다.
- S-STRUCT-006: Phrase4 끝 쉼0.5박은 판단 보류, Phrase5 끝 쉼5.5박 및 앞선1–3의 종결은 보호됐다. `phrase-structure-shadow-v4/review.md`에 기록했다.
- 합성 대조는 단순/복합박, 동등 시간 확대, 미지원/변경 박자, 호흡 기호, 원본 불일치를 다룬다. 이는 독립 작품 정확도 평가를 대체하지 않는다. 단계별 진행은 통합 계획12절에 기록했다.

## 2026-09-22 — 원본 tie / 명시적 쉼 비교

- sourceClosure 관찰 모듈과 테스트 추가. 인접 tie 표기와 명시적 rest를 source ID로 보존하고 기존 duration/gap과 대조한다. 연결 불명확/복잡 입력은 보류하며 마디 경계는 meter 미검증의 조건부 관찰이다.
- S-STRUCT-006 내부 경계는 쉼0.5 quarter, 결합안 끝은 tie 누적2.5 + 쉼5.5 quarter로 원본과 일치했다. 결합 지지 후보이나 아직 종결 판정이나 자동 병합으로 사용하지 않는다.
- `phrase-structure-shadow-v3`에 재현 정보와 대응 구간의 쉼 대조를 저장했다. 운영 경계/유사도 점수/UI 변경 없음. 상세 내용은 통합 계획12절에 기록했다.

## 2026-09-22 — 반복 Phrase 구조 비교기와 shadow 보고서

- 기존 Motif 다중 증거 정렬을 재사용한 `structureTemplateAlignment` 추가. event 연결, 도입 연속 대응, 종결 대응, 추정 쉼 차이를 분리하며 자동 병합하지 않는다.
- S-STRUCT-006의 Phrase4+5 결합안과 각각 유지하는 안을 앞선1–3과 비교했다. 도입8음은 대응하지만 종결 불일치도 있어 판단 보류. 최신 보고서는 `evaluation/case-assets/S-STRUCT-006/phrase-structure-shadow-v2/review.md`.
- source/baseline/comparator hash와 결과를 저장했다. 초기 v1의 결합 끝마디 메타데이터 오류는 v2에서 수정하고 이전 기록은 보존했다. 운영 분석/UI 변경 없음.
- Node에서 같은 TS 비교기를 직접 실행하도록 noEmit TypeScript 설정에 allowImportingTsExtensions를 켰다. 구체적 단계/남은 일은 `REPEATED_PHRASE_STRUCTURE_PLAN.md` 12절을 기준으로 관리한다.
- 검증: 관련10개 파일81개 테스트 통과, TypeScript 검사와 Vite production build 통과. Verovio 브라우저 외부화/큰 번들 경고는 남아 있다. 이 테스트 수는 음악적 정확도 입증이 아닌 구현 회귀 검증이다.

## 2026-09-21 — 로컬 개발 서버 감시 범위 축소

- Vite 개발 서버가 대용량 `data`·`evaluation`·`docs` 트리를 HMR 대상으로 감시하며 I/O 대기 상태에 빠져 5173 포트는 열려 있어도 20초 이상 응답하지 않는 현상을 확인했다.
- 해당 트리는 API가 요청 시 직접 읽으므로 HMR 감시에서 제외했다. 재시작·초기 최적화 뒤 루트 응답은 0.003초, 악보 API 응답은 0.069초로 확인됐다. 소스 코드 변경 HMR은 유지된다.

## 2026-09-21 — YouTube 제목 검증·캐시 정리

- 대표 영상 수집기는 공개·임베드 가능 여부만으로 후보를 선택하지 않고, 작품 제목의 식별 단어가 후보 영상 제목에 짧은 제목은 100%, 그 밖에는 75% 이상 일치할 때만 저장하도록 보완했다. 조회 수는 동률 후보의 보조 기준일 뿐 제목 불일치를 보완할 수 없다.
- 기존 자동 매칭도 API 호출 없이 재검사해 제목 불일치 208건을 제거했다. 예를 들어 `FIND THE WAY`에 잘못 붙어 있던 Bruno Mars의 `Just The Way You Are` 영상은 제거되었다. 다음 정규 수집에서 적합한 영상이 있을 때만 다시 채워진다.
- 수집 모듈을 import해 테스트·점검할 때는 직접 실행이 아니면 API 호출을 절대 시작하지 않게 분리했다.

## 2026-09-21 — 악보 상세 상단 텍스트 검색

- 기존 카탈로그 텍스트 검색을 악보 상세의 sticky 상단 도구 막대에도 배치했다. 상세 화면에서도 제목·작곡가·키워드 자동완성 결과를 바로 선택해 다른 악보로 이동할 수 있다.
- 좁은 화면에서는 상단 도구 막대의 별도 줄로 넓혀 재생·분석 제어와 겹치지 않게 했다. 기존 카탈로그 검색 API와 결과 동작은 바꾸지 않았다.

## 2026-09-21 — 일일 KY·YouTube 수집

- KY 공식 메타데이터는 한국 날짜 한도 100회 조회를 모두 사용해 100개를 신규 매칭했다. 누적 1,604개, cursor 1,604, 남은 미처리 XML 13,048개이며 검색 DB와 원본 XML은 변경하지 않았다.
- YouTube 대표 영상은 Pacific 날짜 2026-09-20에 92회 검색 뒤 Search Queries 분당 한도 429를 받아 중단했다. 추가 호출·우회·검색 DB 동기화는 수행하지 않았으며 state와 캐시는 보존했다.

## 2026-09-17 — 2/4 15회 검증 완료

- 원형 5/5, 시간 축소 삭제 3/5, 음가 흡수 삭제 4/5가 Top5(=이번 Top10)로 회수됐다. 오류·재시도 0건, 독립 사례 검증 완료.
- MICKEY MOUSE MARCH 시간 축소는 low-information-floors, THE PROCESSION OF CELESTIAL BEINGS 두 삭제 조건은 admission-floor 제외 근거 확인. 세 건 모두 후보는 존재했다.
- 대량 새 테스트보다 기존 통과 하한·정렬 문제 개선과 비정답 대조/Exact·쉼표/못갖춘마디 소규모 회귀를 우선하도록 docs/duple-meter-15-v1.md에 정리했다. 검색 로직은 이번 결과 확인 중 변경하지 않았다.

## 2026-09-17 — 2/4 소규모 검증 착수

- 새 원곡 5개, 12음 원형/한 음 삭제/삭제 음가 흡수의 15회 검증을 시작했다. 모든 원형·변형에 단순 전체 순차진행·동음반복 제외 기준을 확인했고 음수·박자·시간 변화 검증도 통과했다.
- 복사 버튼 포함 악보 30개와 진행 페이지를 생성했다. 실제 응답·오류 재시도·진단·독립 사례 저장을 연결했다. 아직 최종 성공률이 아니다.
- 이어서 적용할 공통 개선의 순서는 docs/duple-meter-15-v1.md에 기록했다. 테스트 중 검색 엔진과 DB는 변경하지 않는다.

## 2026-09-17 — 주 평가 Query 선별 범위 조정

- 전체 단순 순차진행/동음반복은 향후 주 평가 표본에서 제외하고 별도 스트레스 사례로 보존한다. 기존 테스트·통계는 변경하지 않았다. 기계 가독 정책: evaluation/query-selection-policy.json.
- 2/4는 소규모 마디 경계 회귀를 권장. 5/8·7/8은 고정 grouping과 5/8 입력 지원 부재를 먼저 정리해야 하므로 대량 테스트는 후순위. 아직 새 테스트나 grouping 변경은 실행하지 않았다.
- 상세: docs/query-selection-and-meter-test-policy.md.

## 2026-09-17 — 단순 패턴 리듬 우선 배점

- 사용자 승인으로 전체 순차진행·동음반복의 melody_rhythm 검색에만 리듬 70%·멜로디 30%를 적용했다. 실제 음가/간격의 공통 템포 비교와 음정 90점 하한, 보조 보정 ±1점을 사용한다.
- 최초 A/B에서 리듬만 강화하면 음정이 덜 맞는 결과가 올라오는 부작용을 발견하여 하한을 추가했다. 두 실험의 Query/전체 응답은 pattern-rhythm-v1/v2에 따로 보존한다.
- 일반 멜로디 배점은 유지. 베토벤 원형 후보 누락은 별도 미해결. 세부 기준·제한·롤백: docs/pattern-rhythm-ranking.md.

## 2026-09-17 — 테스트 Query 복사·검색 입력 붙여넣기

- 원형/변형 악보에 JSON·간단 표기 복사를 추가하고 최근 305개 사례 페이지에 반영했다. 저장된 검색 결과는 변경하지 않았다.
- 검색 입력에 JSON/음높이(음가)-표기 자동 판별, 오류 안내, Undo/Redo 전체 Query 복원을 연결했다. 간단 표기는 4분음표=1박, 현재 박자 사용. 타이/잇단음표/옵션까지 보존하려면 JSON을 사용한다.
- 17개 테스트, 305개 저장 Query 왕복, build 통과. 자세한 사용·제한·검증: docs/query-copy-paste.md.

## 2026-09-17 — 단순 순차진행·동음반복 검색 옵션

- 두 허용 체크박스를 상세 검색에 추가했다. 새 UI는 기본 해제, 전체 6음 이상 단순 패턴만 안내 후 중단한다. 허용하면 기존 검색을 실행하고 점수/후보 제한은 바꾸지 않는다.
- Query JSON·세션 복원에 옵션을 보존하고, 필드가 없는 기존 Harness/API는 종전 정책을 유지한다. 베토벤 EM09가 과거에 새 정책으로 차단되었다고 해석하지 않는다.
- 단위 테스트 6개와 build, 베토벤 Query 안내 반환 통합 검증 통과. 세부 기준·제한·미반영 8개 항목: docs/simple-pattern-search-options.md.

## 2026-09-17 — 6/8·3/8 60회 검증 완료

- 재시도 1건 포함 최종 60회 완료, 실행 오류 0건. 6/8 12→11음 Top10은 시간 축소 3/5·음가 흡수 4/5, 3/8은 각각 3/5. 두 박자 모두 8→7음 Top10은 0/5였다.
- EM09는 원형부터 미회수: 12음은 hits 이후 후보 선별에서, 8음은 hits 단계부터 누락. 변형 내성 문제와 구분하여 후보 회수 진단을 우선한다.
- 독립 사례 60개, XML/event 문맥 20개, 최초/재시도 응답, 비교표와 진단을 저장·검증했다. docs/eighth-meter-60-v1.md에 최종 수치와 제한을 기록했다. 운영 알고리즘 개선은 보류.

## 2026-09-17 — 6/8·3/8 삭제 검증 실행

- 각 박자 5개 원곡을 검색 전 XML 선별로 확보했다. 12/8음 × 원형/삭제+시간 축소/삭제+앞 음 음가 흡수의 60개 Query를 생성하고 박자·음수·뒤 onset 검증을 통과했다.
- 실제 검색과 후처리 실행 중. 결과는 evaluation/reports/eighth-meter-60-v1, 재사용 사례·XML 문맥은 evaluation/exports/eighth-meter-60-v1에 저장한다. 아직 완료 통계가 아니다.
- 비교 페이지 순위 표에 박자 열을 추가했다. 박자별 성적은 별도 TIMING-COMPARISON.md/JSON으로 생성한다. 운영 검색과 DB는 변경하지 않았다.
- 설계·재현·제한: docs/eighth-meter-60-v1.md.

## 2026-09-17 — 3/4 검증 최종 결과

- 60회 완료, 실행 오류 0건. 12→11음 삭제 Top10은 시간 축소 10/10, 음가 흡수 9/10. 8→7음은 각각 2/10, 1/10. 원형 20개는 모두 Top5.
- 짧은 Query의 여섯 원곡은 두 삭제 조건 모두 후보에서 제외됐다. 시간 유지 조건이 무조건 유리하지 않으며 후보 선별과 음가 흡수 대응을 후속 검토한다. 수정은 보류한다.
- 60개 독립 사례와 XML 문맥·응답·순위·진단을 보관하고 검증했다. 상세: docs/triple-meter-60-v1.md 및 evaluation/reports/triple-meter-60-v1/TIMING-COMPARISON.md.

## 2026-09-17 — 3/4 장식음 삭제 60회 검증 실행

- 사용자 승인으로 기존 테스트와 겹치지 않는 3/4 원곡 10개를 XML 기준으로 선별했다. 원형 12/8음, 장식음 한 음과 음가 삭제, 삭제 음가를 앞 음에 흡수하여 뒤 음 onset 유지의 60개 Query를 생성했다.
- 60개 변형의 음수·박자·시작 시각 검증을 통과하고 실제 검색을 시작했다. 완료 결과는 evaluation/reports/triple-meter-60-v1에 기록한다. 이 항목은 실행 착수 기록이며 최종 성공률 주장이 아니다.
- 원형/변형 비교 악보 120개와 순위 표를 생성했다. 미실행은 명시하고, 완료 후 오류 재시도·최종 보고·독립 사례 XML 보관·검증을 수행하는 후처리를 실행했다.
- 검색 엔진과 DB는 변경하지 않았다. 8→7음은 경계 사례이며 1위 유지나 전부 회수를 요구하지 않는다. 설계와 재현: docs/triple-meter-60-v1.md.

## 2026-09-16 — Query 보완 추천 1단계

- 상위 검색 결과의 정렬에서 한 음 추가·반음/온음 변경·한 옥타브 변경 후보를 만들고, 일정 조옮김/템포에서 전체 음표·음가·도착 위치가 일치할 때만 최대 3개 제안한다.
- Query 아래 추천 악보와 붉은 변경음, 원형/추천 재생, 적용 및 기존 Undo/Redo를 연결했다. 검색 당시 Query와 다르면 숨긴다. 기존 검색 점수·후보 검색 로직은 변경하지 않았다.
- 사용자 명시적 확인과 원형/추천/음표 근거를 JSON으로 다운로드한다. 서버 자동 수집과 Harness 자동 import는 후속 단계다.
- 관련 테스트 32개와 build 통과. 저장 응답 51개 재생에서 한 음 삭제 17/17 원형 복원 추천, 원형/두 음 삭제 각 17개에는 추천 없음. 브라우저 런타임 연결 실패로 실제 클릭 검수는 미완료.
- 기획·재현·제한: docs/query-completion-plan.md. 결과: evaluation/reports/query-completion-v1/replay.json.

## 2026-09-16 클래식 레퍼토리 수집 업무 분리

- 클래식 작곡가·작품 목록, 보유 대조, 판본/권리 검증, XML 수집 큐를 MusicSearch 개발 대화에서 별도 프로젝트로 넘기기로 했다.
- `handoff/classical-repertoire-collection-2026-09-16`에 최신 v4 XLSX, coverage/validation JSON, 생성·대조·검증 스크립트, 데이터 계약, 재현 절차, 결정 이력, 다음 단계, 새 프로젝트 시작 프롬프트를 묶었다.
- 거대한 `*.inspect.ndjson`, 검색 DB, 원본 악보 파일은 제외했다. 최신 XLSX 복사본은 원본과 SHA-256이 동일하고, 15개 시트와 오류 문자열 부재를 확인했다.
- 앞으로 MusicSearch는 전달받은 XML의 파싱·색인·검색·렌더링을 담당하고, 새 프로젝트는 레퍼토리 범위·권위 목록·출처·권리·판본·수집 품질을 담당한다.

## 2026-09-16 한 음 삭제 대응 기본 적용

- 사용자 승인으로 제한형 single-omission 후보/정렬을 기본 활성화. MUSICANOTE_SINGLE_OMISSION=0으로 롤백 가능.
- 내부 음 하나 삭제만 허용. 남은 모든 음높이·음가·도착 간격을 동일 조옮김/템포로 검증. Exact 옵션, 리듬/contour 전용, 저정보량 Query에는 적용하지 않음. 완전 일치로 승격하지 않음.
- 삭제40개: 원본 파일 회수25→35, Top5 25→34. 기존1 timeout 포함. 원형20개20→20, 삭제+다른 음 변경20개1→1. 다른 판본을 포함한 작품 단위 회수와 구분.
- 과거 baseline 재현 스크립트는 미지정 시 명시적으로 OFF, A/B 실행기는0/1을 지정. 이미 저장된 결과는 덮어쓰지 않음.
- 새 표시 점수 중심 배점은 회귀로 기본 OFF 유지(MUSICANOTE_VISIBLE_RANKING=1 실험 전용). 구조 축약 모듈도 독립 연구 단계이며 이번 승인으로 일괄 활성화하지 않음.
- 오선 CSS 참조/부드러운 합성음 수정과 Query·결과·악보 비교 자료도 함께 백업. 세부 근거는 structural-next40.md, visible-ranking-v1.md, omission-review-display-fix.md.

## 2026-09-16 예약 KY / YouTube 수집

- KY: 1회 조회, 신규 0. 번호 1790에서 Possible block page 재발하여 중단. 누적 1,005, 미매칭 12,043. 우회하지 않음.
- YouTube: PT 2026-09-15 search95회, 신규94/no-match1, 누적videoId745, cursor780. API 키 설정 확인, 비밀 값 미출력. 오류 없음.
- YouTube worker에 배타 lock/실패 포함 사전 호출 계수/당일 오류 재시도 방지/KR 허용목록 검사를 추가했다. 실제 수집95회 정상 완료.
- 메타데이터/영상 캐시만 갱신. 원 XML 수정 및 검색 DB 동기화는 하지 않음. 상세 일일 로그는 각 collection-log 문서 참조.

## 실곡 검색 계획 실행 — 진단·변박·Contour·연속 구간

- 특정 작품 가산 없이 후보 단계 추적을 추가했다. 기존 Twinkle 7개 결과는 추적 전후 동일했고 Ma Boy는 모두 정밀 비교 전에 누락됐다.
- 변박/표시 마디/ordinal 전달과 스냅샷 박자 무효화, 박자·시작 박이 다른 반복의 분리를 보완했다. Jesus of Suburbia 7개 검색과 비교 리포트 생성 완료, 참조곡 미회수로 기록했다.
- 약 250MB의 전체 코퍼스 contour 부가 색인과 상세 윤곽 후보 보충을 실험했다. Ma Boy 미회수 및 비용 증가로 기본 적용하지 않았다. 상한 전 후보가 지나치게 넓은 원인과 고정 길이의 한계를 기록했다.
- 사용자 추가 의견에 따라 Phrase / 연속 구간 / 혼합을 오프라인 선택 옵션으로 구현하고, 연속 구간으로 Twinkle 재검색을 진행했다. 웹 실행 버튼은 아직 연결하지 않았다.
- [상세 결과·재현·한계와 남은 작업](real-pair-search-diagnostics-and-segments.md)에 연결한다.

## Twinkle 공개 주석 47·48 검토

- 사용자가 제공한 두 공개 분석 글을 읽고 출처와 대응 마디, 검증되지 않은 화성/배치 가설을 별도 JSON에 보존했다. 본문 관찰과 실제 XML/청취 검증을 구분한다.
- 길이가 다른 구간의 부분 변형 비교, 겹치는 15마디의 중복 집계 방지, 근음/화음 성질/베이스 분리와 다층 문맥 비교를 실행 계획에 추가했다. 가사 비교는 데이터 확인 후의 선택적 보조 근거로 보류했다.
- 현재 윤곽/음형 레이어가 후보 회수 이후에 적용된다는 제한을 확인했다. 검색 코드·점수는 이번 검토에서 변경하지 않았다.

## Twinkle–Ma Boy 1차 목표 실행 계획

- 사용자가 Twinkle 리포트에서 Ma Boy 자동 회수를 1차 목표로 지정했다. 기본 리포트 상위 10개 안의 근거 있는 자동 회수를 통과 기준으로 제안하고, 특정 작품 가산이나 지정 비교의 검색 성공 집계를 금지했다.
- 데이터/판본 감사 → 단계별 탈락 추적 → 원인별 일반 검색 A/B → 분산 구절 집계 → 나머지 4쌍과 오탐 대조군의 순서로 계획했다. [상세 계획](twinkle-distributed-similarity-plan.md)에 재현 자료와 완료 기준을 기록했다.
- 이번 변경은 계획 문서이며 검색 논리 수정이나 새 검색 실행은 하지 않았다.

## 실제 기존 DB 리포트와 Twinkle 분산 유사성 기준선

- 실행 종료: Twinkle/Ma Boy와 When Love Takes Over/Clocks 모두 선택 7개 Query의 반환 결과에서 참조곡 미회수. 2곡 합계 14개 검색은 오류 없이 완료했다. Jesus of Suburbia는 준비 도구의 변박 unknown 전달 때문에 0 Query/검색 미실행으로 보류했다. 3곡 모두 성공한 것으로 집계하지 않는다.
- 완료된 두 후보 리포트 합계 40개 SVG와 오디오 스케줄 검증을 통과했다. `evaluation/reports/real-pairs-existing-v1/review.html`에서 결과와 미실행 이유를 확인할 수 있다.

- 기존 참조곡이 확인된 3쌍의 업로드 검사 runner를 추가했다. 파서 입력, 구조 스냅샷, 개별 Query checkpoint, 자기 일치 제외 내역, 검색 JSON과 비교 리포트를 별도 보존한다. 운영 DB와 원본 XML은 수정하지 않는다.
- Twinkle은 7개 Query 모두 완료했으나 Ma Boy 미회수. 14–15마디도 선별되어 검색됐으며 단순 구간 미검사만으로 설명할 수 없다. 나머지 구간/후보 생성/허용 조건/반환 제한 진단은 남아 있다.
- 사용자 설명을 유형화 가능한 `twinkle-review-brief.json`에 기록했다. 분산 변형, 독립 구절과 반복의 구분, 흔한 음형의 과대 합산 방지를 검토 요건으로 삼는다. 법적 양성 정답이나 작품별 순위 가산은 부여하지 않았다.
- [실행 범위·재현·결과·남은 과제](copyright-real-existing-db-report-v1.md)에 연결했다. Twinkle 20개 SVG와 오디오 스케줄 검증 통과; 청취 검증은 미실시.

## 실제 음악 저작권 비교 사례 5쌍 확인

- 사용자가 제공한 K:/Copyright Infringement Case의 XML 10개와 보조 파일을 확인했다. 합성 샘플 대신 실제 5쌍을 다음 검증 대상으로 삼는다.
- 웹의 비교/영향 자료를 조사해 입력 5곡과 선행 참조 5곡을 정리했다. 법적 침해 확정 라벨은 부여하지 않았다. Twinkle은 Lemon19 곡이며 기존 Musicanote의 14–16 vs Ma Boy 10–12 주석을 발견했다.
- 기존 DB를 읽기 전용 조회해 입력곡의 자기 일치 제외 필요와 기존 참조 판본을 확인했다. 운영 DB 추가·수정·실제 음악 검색은 아직 하지 않았다.
- [조사와 비공개 검증 레이어 계획](copyright-real-five-pairs.md), evaluation/real-cases/five-pairs/manifest.json에 역할·경로·근거를 보존했다.

## 다구간 변형 MusicXML 24개 제작

- 사용자 승인 후 새로 만든 합성 원곡 4개로 6유형 × 4박자 = 24개 입력 제작. 원곡/입력/숨겨진 evaluator 정답/이벤트/XML·SVG ID mapping/재현 recipe를 분리 보존했다.
- 원곡 포함 28개 Verovio 렌더 성공, 388개 대응 이벤트 검증, 실제 파서 round-trip과 모든 마디 합/타이 검증 통과. 초기 묶음은 남기고 타이 보강 최종본을 multisegment-v1-final에 보존했다.
- 운영 DB와 검색 로직을 변경하지 않았다. 실제 검색·청취·법적 판정은 미실행이며 누적 검색 횟수에 합산하지 않는다. [제작 결과](copyright-multisegment-fixtures-v1.md).

## 검색 평가 재검토 및 다구간 저작권 검증 설계

- 사용자 요청: 누적 약 400개 테스트를 재검토하고 일반 유사 검색과 저작권 검토를 구분, 원곡 여러 구간을 변형한 MusicXML 업로드 테스트와 구간별 경고를 고안.
- 300/350 세트와 후속 50개 문서를 확인했다. 서로 다른 버전·표본·source 판정 때문에 단일 통합 성공률로 주장하지 않는다.
- 4개 권한 확인 원곡 × 6유형=24개 파일럿, 차용 family/발생/양쪽 비중, self-exclusion 누출 방지, 전곡 검사 범위, 음악적 근거와 권리 확인을 분리한 계획을 작성했다.
- 이번은 설계이며 XML 생성·검색 재실행·점수/리포트 코드 변경은 하지 않았다. [계획과 평가 지표](copyright-multisegment-validation-plan.md).

## 2026-09-15 예약 KY·YouTube 수집

- KY 안전 보호 보강 후 1회 요청에서 Possible block page로 중단했다. 신규 0, 누적 1,005, 남은 12,043. 실제 차단 확정은 아니며 실패 상태를 보존하고 같은 날 재요청하지 않는다.
- YouTube는 키 설정 확인, PT 2026-09-14 기존 호출 100회로 95회 한도 도달. 추가 API 요청 없음. 누적 videoId 651, cursor 685.
- 각 수집 로그와 KY 일별 목록 갱신. 원본 XML·검색 DB는 변경하지 않았다. KY 차단 의심 감지와 일반 문구의 구분은 후속 점검 대상이다.

## 2026-09-16 — 검색 성능 7단계 후보 경계 캐시

- 요청에 따라 문맥 계산 재사용을 구현했다. 입력 전체 fingerprint와 분석기 revision, process-local 64MiB LRU, 후보 경계의 수치 배열 저장을 적용한다. Query/정렬별 비교 및 점수 규칙은 그대로다.
- 초기 키/용량 실패 실험도 보존했다. 최종 두 Query 반복 실행은 약 28%/24% 단축, 최초는 약 3.1/4.6초 증가했다. ON/OFF 전체 반환 JSON hash 동일. 일반적인 전체 성능 향상으로 과장하지 않는다.
- 45개 관련 회귀 및 타입 검사/build 통과. 문서/명령/실험 경로는 [성능 7단계](performance-stage-7.md). 다음은 fingerprint 비용과 혼합 workload 검증이다.

## 2026-09-16 — 검색 성능 6단계 SQL 집계 실험

- 사용자 요청에 따라 남은 성능 개선을 진행했다. 두 느린 Query를 baseline/SQL/control에서 각각 2회, 총 12회 검색했다. Query·전체 결과·프로파일·hash를 새 실행 폴더에 보존했다.
- SQL 집계 구현 및 순서 보존 회귀를 추가했다. 실제 응답은 같았지만 control 반복 9.393/11.472초 대비 SQL 15.254/16.014초로 느려 기본값은 기존 경로로 유지한다. 첫 실행의 큰 개선처럼 보이는 값은 OS 캐시 영향을 받으므로 성능 향상으로 주장하지 않는다.
- 기본 점수/검색 규칙/서비스 설정/DB 색인은 변경하지 않았다. 다음 개선 후보는 프레이즈 문맥 bounded cache이며 아직 미구현이다. [상세 측정과 재현](performance-stage-6.md).

## 2026-09-16 — 사전검토 다층 근거와 개발 후 평가

- 최종 평가 완료: A/B 7 vs 8 task, 50개 최초 49완료/1timeout. timeout은 별도 재시도에서 완료했지만 원본 미회수. 전체 원본 source 회수 32/50, 1위 29/50, top5 30/50, 최초 완료 중앙 9.008초/p95 51.576초.
- 50개 표준 Harness 사례와 5개 공유 XML/이벤트 문맥을 evaluation/exports/preclearance-variation50-2026-09-16에 보존했다. 유형별 Query/상위 결과/문제/개선 후보, 표본 편향과 미검토 사항은 [최종 문서](preclearance-variation50-2026-09-16.md)에 기록했다.
- A/B에서 발견된 미연결 피아노 원곡 판본을 XML 메타데이터/파일 지문으로 확인해 registry에 추가했다. 일반 검색 평가 코드와 점수는 변경하지 않았다. 과거 A/B와 최초 실패 기록은 유지한다.

- Phrase 우선/보조 Motif, 긴 Phrase 분할, 독립 기둥음 후보, Contour·리듬형·음형, 복수 Phrase 비선형 집계를 구현하고 131개 관련 회귀 및 build를 통과했다.
- 기존 검색 메뉴에 Copyright Check를 추가했다. 새 샘플은 25작품/33일치/50악보이며 사용자 확인 원곡의 3판본/23일치는 제외 근거와 함께 남겼다.
- 사용자 추가 요청으로 마지막에 paired 변형 Query 50개를 실행한다. 처음 조기 시작한 실행은 개발 우선 지시에 따라 중단·보존하고 최종 결과에서 제외한다. 이후 코드 검증이 끝난 뒤 A/B→최종 50개 순으로 실행한다.
- 구현/한계/재현은 [다층 근거 v2](preclearance-musical-evidence-v2.md). 셴커 분석, 법률 확률, 전문가 순위 정답이 자동 확정되었다고 주장하지 않는다.

## 2026-09-15 — Phrase 중심 사전검토 비교 요청

- 사용자 의견: 안정화 중인 Motif보다 Phrase를 우선하고 두 방식의 실제 효과를 비교한다. 복수 Phrase 일치는 단순 합산하지 않으며 기존 사이트 메뉴로 진입한다.
- 현재 두 종류가 최대 7개 task budget을 공유하며 작품 priority는 maximum-not-sum인 것을 코드로 확인했다.
- 공정한 A/B, 중복/반복과 독립 Phrase 구분, 포화 보너스 후보와 사이트 통합안을 [계획 문서](preclearance-phrase-motif-ab-plan.md)에 기록했다. 이번에는 조사·설계이며 기본값/점수/메뉴를 변경하거나 A/B를 실행하지 않았다.

## 2026-09-15 — 지연 진단 후속과 Copyright Infringement Report 초안

- 박자 캐시를 32개씩 transaction 저장해 검색 worker 중단 뒤 재사용하도록 했다. 별도 캐시에서 32개 저장 직후 취소했고 재실행 결과 hash가 기존 방식과 같았다. 후보/점수 규칙은 변경하지 않았다.
- 이전 4개 파일럿 모두 60초 안에 완료했다(4.670/44.089/48.374/7.123초). 원본 source 순위는 1/1/1/3. 나머지 8개 미실행과 느린 최초 실행은 남아 있으며 전체 성능 해결로 주장하지 않는다.
- 기존 Endless Love 사전검토 근거를 HTML/JSON 보고서로 출력했다. 26개 작품 그룹·56개 일치와 대표 A/B Verovio 악보 52개, 합성음 재생, 권리 미확인, 구조/빈도/반복 근거를 포함한다. 법률 판정이나 침해 확률은 제공하지 않는다.
- 최종 산출물: evaluation/reports/copyright-infringement-report-2026-09-15-final/. 강조 대상·JS·오디오 스케줄/취소 검증, 데스크톱/좁은 화면 확인 완료. 실제 청취와 원본 판면 동등성 검증은 미실시.
- 관련 회귀 127개/14파일 및 TypeScript/build 통과. 최종 신규 7개 회귀 재실행도 통과. 기존 구조 분석 변경을 보존했고 실행을 막던 breath-symbol 모듈의 누락 괄호만 수정했다. 현재 분석기 v1.10과 보고서에 보존한 v1.9 근거를 구분한다.
- 상세 계약과 재현: [캐시 검증](preclearance-stage8-cache-checkpoint.md), [보고서 초안](copyright-infringement-report-v1.md). 업로드 인증/보관/삭제/운영 UI와 전문가·권리 검토는 후속 단계다.

## 기록 완료 기준

- 알고리즘·schema·UI 동작을 바꾸는 작업은 코드만 수정한 상태를 완료로 보지 않는다.
- 같은 변경에서 규칙의 목적과 한계, 데이터 계약, 회귀 테스트, 실제 악보 전후 결과, 알려진 미해결 문제를 관련 명세와 날짜별 개발 로그에 함께 기록한다.
- 분석기 버전, 코드, 테스트, API payload, 뷰어 문서의 버전 표기가 일치해야 한다.

## 2026-09-11 프레이즈 반복 음형 계층화 v1.2

- Phrase 검토 상호작용을 추가했다. 오른쪽 드롭다운에서 Phrase를 선택하거나 악보 위 `Phrase N` 구간 띠/라벨을 클릭하면 해당 Phrase의 모든 system segment가 1초 동안 두 번 강조된다. 같은 Phrase 재선택도 새 token으로 DOM key를 갱신해 animation을 다시 시작한다. 아직 렌더링하지 않은 뒤쪽 Phrase는 해당 Verovio page를 우선 렌더링한 뒤 그 구간으로 스크롤한다.
- 악보의 경계 막대 문구를 `P1│P2`에서 `P2 시작` 형식으로 바꿨다. 현재 기본 phrase span은 서로 겹치지 않는 `[start,end)`이므로 막대는 두 구간이 공유하는 음이 아니라 뒤 Phrase가 시작되는 위치를 뜻한다. `P1│P2`와 반반 색 anchor는 향후 분석 payload가 명시적인 overlap membership을 제공할 때만 사용할 수 있다.
- 사용자 검토 사례 `work-25517ce2d093550b`에서 기존 분석기가 15–18마디 반복 음형의 각 1박 공백을 독립 프레이즈 경계로 채택한 원인을 확인했다. 기존 채택 경계는 note index 33/37/41 및 106/110/114였고 모두 `observed-gap`이 과대 지배했다.
- `local-boundary-evidence-v1.2`에 반복 진행 계층을 추가했다. 3–8 attack 길이의 연속 cell이 정규화한 duration, IOI, contour에서 반복되면 전체 run의 시작·끝을 primary phrase 후보로 만들고 내부 gap은 `subphrase-cell`로 보존한다.
- 내부 경계는 삭제하지 않는다. 기존 점수를 `rawStrength`에 보존하고 `repeated-figure-continuation`, `primaryLevel`, `suppressedBy`를 기록한다. run에는 `cellLengthInAttacks`, `cellCount`, `internalBoundaryIndices`, `similarity`, `requiresCadenceReview`를 반환한다.
- 같은 작품의 기존 6·7번 구간은 음정 윤곽의 exact 반복이 아니라 두 pickup 제스처가 `[1,1,2]` duration prefix를 공유하고 뒤에 6 quarter의 큰 공백이 오는 구조였다. 이를 `rhythmic-gesture-continuation`으로 별도 모델링해 index 70의 내부 쉼을 subphrase로 낮추고 index 65–74를 한 primary 구간으로 유지했다.
- 실제 API 재검증에서 15마디 2박 C#5(index 29)부터 19마디 1박 E5 직전까지 하나의 구간이 되었고, 16/17/18마디 시작 index 33/37/41은 내부 cell로 보존됐다. 36–39마디의 반복도 index 102–118 한 구간으로 합쳐졌다. 사용자 화면상의 C 음은 조표 적용 written pitch로 API에서 C#5이며, 옥타브 표기 차이는 향후 Canonical IR/engraving ID 연결에서 재검증한다.
- 화면 검증에서 boundary index를 양쪽 phrase의 공통 음으로 표시하던 별도 UI 오류를 발견했다. 경계 `i`는 note `i` 직전이라는 분석 계약에 맞춰 기본 span을 `[start,end)`로 변경했다. 따라서 Phrase 2는 m15 b1 B3(index 28)에서 끝나고 Phrase 3은 m15 b2 C#5(index 29)에서 시작한다. 실제 overlap은 향후 별도 hypothesis가 있을 때만 표시한다.
- 비연속 attack만으로 구간 마디를 표시해 Phrase 1이 1–4마디로 축약되는 문제도 확인했다. 다음 경계가 m11 b1이면 시간 span의 끝을 m10으로 표시하고, endpoint pitch는 마지막 포함 음표를 별도로 유지하도록 수정했다. Chrome 검증에서 Phrase 2 `11–15마디 E4→B3`, Phrase 3 `15–18마디 C#5→B5`가 확인됐다.
- 단위 테스트에 4-cell 반복 진행, 2-gesture chain과 그 반례 2개, 비중첩 `[start,end)` span, 침묵 마디, `P2 시작` 표시 및 재선택 flash key 사례를 추가했다. 관련 3개 파일의 테스트 40개와 TypeScript/Vite production build가 통과했다. 전체 suite의 직전 실행은 이번 변경과 무관한 기존 evaluation case의 `createdAt` 누락 1건 때문에 204개 중 203개 통과했다.
- Phrase 5를 만든 2-gesture 규칙에는 작품 ID·마디·음높이·제목 상수가 없다. 같은 rhythm prefix만 같거나 큰 종결 공백만 있는 경우에는 합치지 않도록 반례 2개를 추가했다. 현재 코퍼스에서 결정론적으로 고른 500곡(105,306 attacks) 표본을 점검한 결과 repeated-run은 100곡/239건, narrower rhythmic-gesture rule은 12곡/17건(작품 기준 2.4%)에만 발동했다. 이는 규칙이 한 작품 전용이 아님을 확인하는 적용 범위 검사일 뿐, 17건이 모두 음악적으로 옳다는 정확도 증명은 아니다.
- 상세 설계, threshold, 실제 전후 표, 오탐 방지 조건과 deferred cadence 결합은 `docs/phrase-boundary-v1.2-repetition-hierarchy.md`에 기록했다.

## 2026-09-06 Query 300개 평가 보고서 대조 및 Harness 이관

- `docs/query-100-evaluation-report.md`를 현재 생산 검색 코드와 대조했다. 문서에는 300개 Query 표가 있으나 실측 서술은76개이고, 실행 당시 Query JSON·work/source/stream ID·target onset·결과 snapshot·코드/DB 식별자가 없어76.3%를 재현 가능한 현재 성능 수치로 사용하지 않는다.
- 중간 오음, 쉼표, tie, 장식음, tempo scaling, 반복 occurrence, 짧은 Query 등의 변형 분류는 유용하다고 판단했다. 표300행을 별도 draft JSONL로 정규화하는 importer를 추가했다. meter와 downbeat 시작 여부는 추측하지 않는다.
- 반복 결과는 프레이즈·박자 문맥을 우선하고 완전 동률일 때만 앞 occurrence를 택하는 방향으로 유지한다. 저음역만으로 베이스를 감점, 일반 melody 검색에서 음정 반전까지 원곡으로 회수, mod12/2-gram 채널 즉시 기본 활성화, interval exact를 “주제부100% 일치”로 표시하는 제안은 채택하지 않았다.
- m3/s3 후보 채널은 BWV114 등 실제 후보 조기 탈락 사례와 연결되는 후속 실험으로 보존한다. 현재 구조 가중치는 화성 검증이 없는 휴리스틱이므로 별도 인덱스와 held-out 평가 없이 Schenker 정답이나 재현율 보장으로 부르지 않는다.
- 검증: 보고서300행을 중복 없이 모두 변환했고30개 범주, Q061 타이 그룹, Q269 한·일문 제목을 확인했다. 전체18개 파일/166개 테스트, TypeScript와 Vite build, diff 공백 검사를 통과했다. Verovio 대형 bundle 경고는 기존과 동일하다.

## 2026-09-05 중단 작업 재개 · 경계 분석 1단계 · F4 타이 강조 · 점8분음표

- 사용자 요청: 중단 전 계획을 누락 없이 재개하고 경제적인 모델 사용, 특정 KY 결과의 staff2 F4 확인, Query에 점8분음표 추가, search-performance-proposals-and-tests 문서 검토 후 타당한 제안 반영.
- 재개 당시 완료물: 경계 분석 모듈과 19개 테스트, legacy 사례/스키마/export 대부분. 미완료물: A/B runner는 shebang만 있었고 검색 연결 및 실제 비교는 없었다. 저장된 파일에서 이어 작성했으며 기존 사용자 변경이나 DB를 되돌리지 않았다.
- 실행 계획: docs/phrase-context-execution-plan.md. 경계 분석은 원곡 전체 stream의 보조 evidence로만 계산하고 m+r 유사 검색의 최종 순위를 ±3점 이내 보정한다. 새로운 음 생략·후보 통과 완화·정답 작품 고정은 없다. contour null 정렬 참조 오류도 통합 검사에서 방지했다.
- Harness: 정본 7건(실행 가능6/불완전 원문1), validator/export 및 생산 경로 A/B runner 완성. 0-based 보고서 순위 오류를 1-based로 바로잡고 검사 추가. 원본 실행 보고서는 보존하고 정정본을 별도 저장했다. Porgy 2→1위, BWV772 2위 유지, BWV114 기대 결과 Top100 미확인. 공통 결과의 실제 일치 마디/음표 변경0건. 캐시 영향을 포함한 실행 시간 차이를 가속 효과로 주장하지 않는다.
- Q-P1-006: 꺼져 줄게 잘 살아 (Feat.용준형 Of 비스트), work-af9d06a2cc0ef485-a71ddd21, source kysing/57982.xml, stream P3:1:1. F4는 원본25마디4박 staff1/voice1→26마디1박 staff1/voice1의 타이다. 같은 마디 staff2/voice5의 F4 stop이 DOM상 뒤에 나와 이전 색칠 루프가 잘못 따라갔다. 검색이 성부를 섞은 것이 아니라 표시 단계 오류임을 원본/DB 대조로 확인했다.
- 타이 강조는 동일 part/staff/voice, 시간 순서, 바로 다음 onset의 stop만 따른다. 중간 새 어택·쉼표·끊어진 타이는 넘어가지 않는다. 검색 결과 조각과 상세 화면의 공유 component에 적용하고 실제 사례 형태로 회귀 검사했다. 원본 XML과 검색 인덱스는 수정하지 않았다.
- Query: .5와1 사이에 .75(점8분음표)를 추가하고 MEI dur=8/dots=1로 그린다. 기존 tuplet/tie/나머지 음가 유지. 새 Query 원문16events/15notes와 진단은 evaluation/cases/q-p1-006-cross-staff-tie-highlight.json에 보존했다.
- 성능 제안 검토: 테스트/Harness와 보수적 경계 분석 채택. BLOB압축 예상 수치·band DP재현율100%·코어수 비례가속 보장은 미검증으로 정정. 단순 템포배율 게이트, 반주 Query 자체를 오탐 취급하는 테스트, 고정60/40 점수식은 그대로 적용하지 않았다. 표본/회귀 검증 후 실험하도록 문서에 기록했다. K28.93GiB/U44.38GiB 여유 확인, 대형 DB 재구축·교체는 하지 않았다.
- 모델: 사용자 비용 절감 요청에 따라 작은 음가 수정은 Luna, 타이 표시 수정은 Terra, A/B runner는 Sol에 맡겼다. 현재 대화의 주 모델을 바꾸는 도구는 확인되지 않아 변경했다고 주장하지 않는다.
- 검증: 경계/생산 연결25개 검사 통과. 보고서 순위 회귀 검사까지 포함한 최종 전체17개 파일/164개 검사와 TypeScript 검증 통과, Vite build 통과. 정본7건 JSONL/CSV export 및 diff 공백 검사 통과. Verovio 대형 bundle 경고는 남아 있으며 브라우저 직접 시각 검증은 별도다.
- 2026-09-06 재개 마무리: 위 구현을 유지하고 Q-P1-006의 타이 강조 수정 상태와 단위 검증 근거를 갱신했다. 순위 정답 미확정/브라우저 확인 대기는 해결 완료로 바꾸지 않았다.
- 2026-09-06 재검증: 기본5초 제한에서는 실제 코퍼스를 읽는 catalog text search 첫 검사가9.3초로 timeout(163통과/1실패)했다. 검색 코드나 검사 기대값은 변경하지 않고 실행 옵션 --testTimeout=20000으로 재실행해164개 전체 통과(전체1.95초), TypeScript/export도 통과했다. 캐시/초기 읽기 지연에 민감한 검증이며 성능 문제가 해결됐다는 뜻은 아니다.

## 2026-09-05 프레이즈 자동 분석과 사람 주석 연계 검토

- 요청: 별도 프로젝트의 사람 분석 데이터 수집이 완료되기 전에 프레이즈를 자동 분석할 수 있는지와 한계를 설명한다.
- 현재 프레이즈 규칙과 사용자 Analysis Harness 지침, LBDM 및 다중 단서 분할 연구를 확인했다. 현 구현은 국소 단서 추정이며 완전한 화성/종지/셴커 분석은 아니다. 고정 analysisConfidence 수치도 검증된 확률이 아니다.
- docs/query-testing-next-round.md에 경계 후보·불확실성 처리, 원래 연속 검색 보존, 타이 공격과 화성 중요도의 분리, 사람 주석의 안정적 식별자 및 독립 평가 연결 방안을 기록했다.
- 분석은 사전 계산된 보조 계층으로 연결하고, 정답 회수/오탐/정확한 음표 대응 개선을 검증한 뒤 도입하는 방향을 제안했다. 이번 요청은 설명이므로 검색 코드·DB·외부 분석 프로젝트를 수정하지 않았다.

## 2026-09-05 검색 Query 검증 범위와 다음 테스트 계획

- 요청: 중간 음 변경과 음 생략 외에 검증할 검색 사례 및 개선 방향을 제안한다.
- 현재 개별 정본 4개는 모두 melody_rhythm·4/4·유사 검색이다. Porgy 등 legacy/개발 기록의 사례도 있으며, 사용자 테스트 전체가 네 개라는 뜻은 아니다. 단위 검사와 실제 코퍼스 검증을 구별했다.
- docs/query-testing-next-round.md에 허용 변화/구별할 변화의 A/B 테스트 8종, 첫 15 Query 라운드, 작품·구간·음표·오탐 평가, 미사용 작품 검증 및 기록 항목을 정리했다.
- Legacy 이관, schema 일관성, production 경로 전체 suite 보고서는 보완 과제로 남겼다. 이번에는 검색 알고리즘·가중치·DB를 변경하거나 새로운 Query가 통과했다고 표시하지 않았다.

## 2026-09-05 Laudate pueri Dominum 다중 파트 페이지 조판

- 사례: work-cc948ac1b2056317-e2ac527d, P4, 38–39마디. 원본은 5파트이며 39·45마디에 print new-page=yes가 있다.
- 기존 1900×2700·scale 24에서 여러 system이 70–80% 수준으로 과도하게 가로 압축됐고, 고정 placeholder 비율도 다중 파트용 페이지 조정과 연결되지 않았다.
- 5파트 이상 전체 악보에만 2100×3100·scale 21 적응형 조판을 적용했다. 4파트 이하는 기존 1900×2700·scale 24를 유지한다. 검색 결과 excerpt도 변경하지 않았다.
- 실제 렌더 진단에서 목표 38마디는 4쪽, 원본 39마디 page break는 5쪽으로 유지됐고, 목표 주변의 반복 압축 경고가 크게 감소했다. placeholder aspect-ratio도 실제 pageWidth/pageHeight CSS 변수와 동기화했다.
- Computer Use 화면 캡처는 helper가 두 번 종료되어 불가능했다. Verovio 출력 계산으로 검증했으며 브라우저 시각 확인은 남아 있다. 테스트 95개와 TypeScript 검증 통과.

## 2026-09-05 KY 공식 메타데이터 첫 증분 반영 및 검색 성능 3단계

- backfill 105개는 기존 DB 행의 제목 수정 대상이 아니라, 과거 메타데이터 미매칭으로 인덱스에서 제외됐던 XML임을 확인했다.
- 105개 전용 inventory를 생성하고 XML 105개를 실패 없이 파싱했다. 419 melody streams와 331,185 n-grams를 별도 SQLite로 만든 뒤 활성 DB에 단일 트랜잭션으로 병합했다. 병합 ID 전체는 data/kysing-metadata/index-merge-2026-09-05.json에 보존한다.
- 현재 코퍼스는 95,625 works / 384,425 melody streams. 강원도 아리랑·경상도 청년·당신은 몰라의 source, 제목, 가수와 FTS/API 텍스트 검색을 확인했다. 원본 XML은 변경하지 않았다.
- 검색 단계별 profiler를 추가했다. Q-P1-004에서 local alignment보다 MusicXML 박자표 조회가 큰 병목임을 확인했다.
- source+part의 정확한 meter timeline을 meter-context.sqlite에 영속 저장하고, 활성 검색 DB 수정 시 자동 무효화한다. 별도 프로세스 재실행 비교에서 7,124→2,322 ms, meter lookup 4,265→83 ms. 검색 규칙·점수·후보 수는 변경하지 않았다.
- 테스트 94개와 TypeScript 검증 통과. 세부 결과는 docs/performance-stage-3.md와 evaluation/runs/performance-stage-3-meter-cache.json에 기록했다.


## 2026-09-05 KY 공식 메타데이터 자동 수집

- 자동화 ky가 미매칭 번호 100개를 1.5초 간격으로 조회했다. 공식 번호 일치와 비어 있지 않은 제목을 확인한 신규 100개를 저장했다.
- 누적 105개, cursor 105, 전체 pending 목록 13,048개 중 미처리 12,943개. 429 및 실행 오류 없음.
- 수집 JSON·상태와 날짜별 목록을 갱신했다. 원본 XML과 검색 DB는 변경하지 않았다.

## 2026-09-05 KY 제한 상세 악보 자동 재조판

- 사용자가 Fly Away(work-94ed97f401dcce21) 사례 진단 후 제안한 자동 재조판에 동의. 적용 범위는 노래방 research-preview 상세 화면으로 한정했다.
- 상세용 단일 파트 XML에서 print new-page=yes 및 new-system=yes 요소와 그 안의 전체 악보용 system 간격을 제거한다. Verovio가 현재 단일 파트와 화면 크기에 맞춰 재조판한다.
- 일반/public-domain 악보와 검색 결과의 작은 excerpt에는 적용하지 않아 원본 조판을 유지한다.
- 실제 API 검증: 이 사례의 상세 응답은 경계 때문에 21마디·1파트이며 강제 page/system break는 0개다. excerpt는 원본 조판 경로를 사용한다. 회귀 테스트 94개와 TypeScript 검증 통과.

## 2026-09-05 Fly Away 제한 악보 페이지 나눔 진단

- work-94ed97f401dcce21, kysing/84180.xml, 80–82마디 사례. 원본 P1/P2/P3 모두 78·90마디 시작에 print new-page=yes가 있다. 인근 new-system은 71·74·81·84·87마디.
- 상세 렌더링은 FullXmlNotation.tsx의 breaks=encoded로 원본 나눔을 유지한다. 검색 파트만 추출한 제한 미리보기에도 3파트 전체 악보의 페이지 지시가 남아 여백이 생긴다.
- 진단 요청이므로 조판 동작은 변경하지 않았다. 개선 후보: 제한 미리보기에 한하여 원본 강제 페이지 나눔과 간격을 제거하고 자동 재조판.

## 2026-09-05 처녀 뱃사공 가사 손상 진단 및 KY 상세 범위 확장

- 사례: work-cd00a09e05bd1b29-d08f9a8a, kysing/03008.xml, 20–22마디. Query는 이번 요청에 제공되지 않았다.
- 원본 파일은 strict UTF-8 디코딩에 성공하지만 U+FFFD 대체 문자가 318개 이미 저장되어 있다. 해당 마디의 lyric/text가 깨진 가사이며 음악 기호나 렌더러 폰트 문제가 아니다. 손실된 가사를 추측하여 복원하거나 삭제하지 않았다.
- 노래방 research-preview 상세 범위를 앞뒤 각 4마디에서 10마디로 확장. 원본 XML과 검색된 파트만 제공하는 제한 정책은 유지. 결과 조각은 일치 마디만 유지한다.
- 실제 API 검증: 상세 10–32마디 23개, excerpt 20–22마디 3개, 두 경우 모두 part 1개. 시작 ordinal offset도 각각 10/20으로 일치. 단위 테스트 93개 통과. 브라우저 시각 검증은 미실시.

## 2026-09-04 Q-P1-005 Mystery of Love 강조 누락 수정

- 사용자 Query와 targets는 evaluation/cases/q-p1-005-empty-measure-highlighting.json에 별도 저장.
- 빈 measure self-closing 태그가 다음 마디와 합쳐져 metadata/조각 추출 순번이 어긋났다. 실제 25–26마디를 32–33으로 표시했다.
- 원본 파일은 유지하고 서버의 공통 XML 읽기 단계에서 빈 마디 태그를 명시적 시작/종료 태그로 정규화했다. 재색인이 아닌 표시 좌표 처리 수정이다.
- 회귀 테스트 포함 93개 통과. 실제 API의 25–26마디 음표와 7개 targets 좌표 확인. 브라우저 시각 검증은 아직 하지 않았다. 기존 결과는 재검색 권장.

## 2026-09-04 Le quattro stagioni 9마디 끊긴 곡선 진단

- 사례: work-543780a0f9415f4d, P1:1:1, 표시 9마디.
- 원본 MusicXML에 F5–E♭5 및 C5–B♭4 각각 slur line-type=dashed 시작과 stop이 명시되어 있다. 잘린 타이나 인코딩 문제가 아니라 원본의 파선 슬러이다.
- 해당 판본에서 파선으로 지정한 편집 의도는 XML만으로 확정할 수 없다. 원본 기호 및 렌더링 코드는 변경하지 않았다.

## 2026-09-04 속도 개선 2단계: 후보 구간 정렬 실험

- 요청: 다음 속도 개선 작업 실행 및 개발 기록 유지.
- 전곡 local alignment를 seed 주변의 병합 구간으로 제한하는 선택형 경로를 추가했다. 기본 검색·contour·전곡 exact 검사는 유지한다.
- Q-P1-002, 003, 004 원본 fixture를 변경하지 않고 비교 실행기와 별도 JSON 보고서를 추가했다. Query 파일 hash, 순위, 점수, 작품 및 마디 범위를 저장한다.
- 초기 두 사례는 47.6→8.2초, 43.1→9.1초이나 상위 100개의 구성 변화가 있어 기본 적용을 보류한다. 결과 수가 같다는 이유로 재현율 보존을 주장하지 않는다.
- 상세: docs/performance-stage-2.md 및 evaluation/runs/performance-stage-2.json. 단위 테스트 92개와 TypeScript 검증 통과.
## 2026-09-04 · KY 일일 수집 설정과 PDMX 중복 템포 진단

- work-0e8609b50c02be68-30d416f5는 노래방 자료가 아닌 PDMX의 Phyllis go take thy pleasure이며 선택 stream은 P5:2:5이다. XML에 stem 방향이 지정되어 있으므로 음역만으로 일괄 뒤집지 않았다.
- 템포 중복: 원본 P1의 1마디, staff 1에 quarter=140 방향 요소가 다섯 번 들어 있다. default-y만 0/31.46/62.92/94.38/125.83로 달라 원본의 중복 지시가 표시된다. 뒤쪽에는 실제 템포 변화도 있어 전체 템포 삭제는 부적절하다. 이번에는 원인만 확인했으며 악보를 변경하지 않았다.
- KY 수집은 9월 3일 오전 9:37 이후 5건 상태에서 멈춰 있었고 기존 일일 자동화는 확인되지 않았다.
- 자동화 ky를 매일 오전 9시, 최대 100개 미매칭 번호 조회, 요청 간격 1.5초 이상으로 생성했다. 중복 실행 방지, 공식 번호 일치 검증, 실패 기록, 원본 XML 보존을 지시했다.
- 수집 요약은 docs/ky-collection-log.md, 날짜별 신규 목록은 docs/ky-collection/YYYY-MM-DD.md에 기록한다. 오늘 실제 수집 실행은 하지 않았으며 설정과 기존 기록 정리만 완료했다.

## 2026-09-04 · 1234 Back 악보의 물음표 진단

- 요청 사례: work-046bdc640e4f7062, 73–75마디, 금영 46277.xml.
- 원본 파일은 유효한 UTF-8이지만 U+FFFD 대체문자 1,354개가 이미 저장되어 있다. 전체 lyric 요소 1,159개 중 677개가 손상 문자를 포함한다.
- 73마디 음표의 lyric/text에도 대체문자가 확인되므로 Verovio 폰트 문제가 아니라 원본 가사 데이터 손상이다. 언제 손상됐는지는 현재 XML만으로 확정할 수 없다.
- 현재 XML의 인코딩 변경만으로는 복구 불가. 원본 MIDI 가사 이벤트의 바이트 또는 손상 전 자료가 필요하다.
- 이번 요청은 원인 확인이므로 악보와 가사를 자동 삭제하거나 변경하지 않았다. 표시 개선안은 손상 가사만 숨기고 정상 가사·음표는 유지하는 것이다.

## 2026-09-04 · 멜로디 검색 작곡가 인코딩 및 TITLE 제거

- 요청: 텍스트 검색은 Schönberg인데 멜로디 검색 편곡본에는 Sch鰊berg가 남는 차이를 해결하고 상세 페이지의 TITLE 라벨을 제거한다.
- 원인: 일부 편곡본의 legacy byte 문자열을 인코딩 복구하면서 한자 손상 이름이 새로 만들어졌다. 기존 이름 정규화는 디코딩 전에만 실행되어 그 결과를 놓쳤다.
- 해결: 서버에서 디코딩 후에도 이름 정규화를 수행한다. ResultCard는 sessionStorage에 남은 이전 검색 결과의 작곡가도 표시 시 정규화한다. 일본어·중국어의 정상 이름은 보존한다.
- UI: 상세 페이지의 TITLE 라벨만 제거하고 실제 작품 제목과 작곡가 표시는 유지한다.
- 검증: Q-P1-004의 6개 멜로디 결과가 모두 Claude-Michel Schönberg로 표시되는지 검증 스크립트를 추가했다. 데이터 원본이나 검색 점수는 변경하지 않았다.
- 기록 원칙: 앞으로도 사용자 요청, 원인, 수정 방법, 검증 여부를 이 개발 기록에 남기고 Query 사례·실행 결과는 evaluation/에 별도 보존한다.

## 2026-09-03 검색 일치 구간·전체 악보 렌더링 안정화

- 사용자 UI 회귀 사례에서 `<measure>` 정규식이 `<measure-style>`을, `<time>` 정규식이 `<time-modification>`을 오인하는 태그 경계 오류를 확인했다. 실제 태그 경계를 공백 또는 `>`로 제한하여 반복 마디·셋잇단음표 악보의 잘못된 조각 절단, divisions 상속 실패, 음표 겹침과 강조 누락을 함께 수정했다.
- 상세 화면과 결과 조각의 강조 음표가 달랐던 `A Lover's Concerto` 사례는 수정 후 양쪽 모두 14개로 일치했다. `THE POWER OF LOVE` 누락 사례도 조각과 상세에서 각각 10개의 강조 요소가 확인되었다.
- 화음 구성음마다 동일한 코드명이 lyric으로 복제된 XML은 같은 마디·staff·onset·가사 번호·텍스트의 중복을 렌더링 직전에 한 번만 남긴다. 원본 XML은 변경하지 않는다.
- 중국어 악기명 `降B調小號`를 `B-flat Trumpet`으로 표시하며, 자주 쓰이는 중국어 간체·번체 악기명 번역표를 API와 악보 XML 응답에 적용했다.
- 검색 결과가 기본 `P1:1:1` 이외의 stream이면 제목 위에 악기명과 Part/Staff/Voice를 표시한다. 상세 화면 제목 아래에는 작곡가 또는 노래방 가수 정보를 표시한다.
- 4마디를 초과하는 악보 조각은 음표 크기를 유지한 채 내용 너비를 늘리고 가로 스크롤로 탐색한다.
- `THE LAST NIGHT OF THE WORLD`의 작곡가 표기를 원본 XML에서 다시 동기화하여 `Claude-Michel Schönberg`로 복구했다. 정상 Latin 악센트를 CJK로 재해석하지 않도록 인덱싱·표시 복구 규칙도 보완했다.
- Phase 1 Harness에 `Q-P1-003` BWV Anh. 114 사례를 추가했다. 직접 정렬에서는 18마디 후보가 Contour 100, Rhythm 92.5, local similarity 79.60이지만 200개 검색 결과 후보에는 진입하지 못했다. 최종 Downbeat 가중치만 올려서는 이미 탈락한 후보를 복구할 수 없으므로 metrical-skeleton retrieval 채널이 필요하다.
- PDMX `Chant du départ` 사례에서 정상적인 프랑스어 악센트를 Shift-JIS/GB 계열 문자로 다시 해석하던 메타데이터 복구 오류를 수정했다. 정상 Latin 확장 문자는 보존하며, CSV 원본으로 특정 작품의 DB·FTS 메타데이터를 다시 동기화하는 도구를 추가했다.
- 노래방 `research-preview` 상세 화면은 검색 일치 마디 앞뒤 4마디씩, 보통 최대 10마디를 제공한다. 결과 목록과 상세 상단의 작은 검색 일치 구간은 정확한 일치 마디만 표시한다.
- 페이지별 진행 상태 문구를 실제 처리 단계에 맞게 `악보 렌더링 진행 중`과 `악보 렌더링 완료`로 정리했다.
- 재현 사례: `work-619552326277915e`, 4–5마디. 원본 XML과 검색 음표 데이터는 정상이지만 검색 일치 구간과 전체 악보가 비어 있었다.
- 전체 악보 실패 원인은 선택적 `playbackNotes`의 기본값으로 매 렌더마다 새 배열을 만들던 데 있었다. 렌더 효과가 상태를 다시 갱신하면서 React의 최대 업데이트 깊이 오류가 반복되었다. 모듈 범위의 고정 빈 배열을 사용하도록 수정했다.
- Verovio WASM 초기화는 화면의 악보 컴포넌트마다 반복하지 않고 하나의 초기화 Promise를 공유한다. 각 악보는 이 런타임에서 별도 toolkit을 생성한다.
- 검색 일치 구간은 브라우저에서 전체 XML을 다시 자르지 않는다. `/api/work`에 `excerpt=1`을 전달하여 서버가 목표 part와 정확한 ordinal 마디만 담은 작은 MusicXML을 반환하고, 클라이언트는 이를 즉시 조판한다. 이 사례의 응답은 137,092자에서 23,011자로 줄었고 Verovio 1페이지 렌더링이 확인되었다.
- 상세 화면 상단도 결과 카드와 같은 `SearchExcerpt` 경로를 사용하도록 통일하여 두 화면의 조각 생성 방식이 달라지는 회귀를 막았다.
- 로딩 문구는 `악보 조각을 불러오는 중…` 대신 `검색 일치 구간을 불러오는 중…`으로 변경했다. 렌더링 예외는 더 이상 빈 화면으로 숨기지 않고 오류 메시지와 개발자 콘솔에 표시한다.
- 대용량 전체 악보는 목표 페이지를 우선 3쪽씩 렌더링하고, 나머지는 스크롤 또는 `다음 3쪽 불러오기`로 요청할 때만 추가한다. 다른 탭의 100쪽 이상 악보가 백그라운드에서 계속 조판되는 문제를 방지한다.
- 검증: Vitest 9 files / 81 tests 통과, TypeScript 및 Vite production build 통과.

이 문서는 사용자 요청, 구현 결정, 검증 상태와 다음 작업을 누적 기록한다. 기능을 변경할 때마다 관련 항목과 검증 결과를 갱신한다.

## 2026-08-30: 원본 연속 선율 우선·장식음 예외 제한

- 검색 기본 단위는 대상 MusicXML의 같은 part/staff/voice에 있는 연속 sounding melody 전체로 유지한다.
- 중간 음표를 건너뛰는 sparse alignment는 일반 규칙이 아니라 제한된 예외로 취급한다.
- 원본 `<cue/>` 표기는 편집자가 명시한 강한 보조층 근거이므로 단독으로 예외를 허용한다.
- 자동 추론 음표는 `passing/neighbor 형태`, `대표 음가의 60% 이하인 짧은 음`, `metric weight 0.5 미만의 약박` 세 신호 중 최소 두 가지를 동시에 만족해야 가벼운 보조음으로 인정한다.
- passing tone처럼 보인다는 이유 하나만으로 긴 음이나 박절상 중요한 음을 건너뛰지 않는다.
- 일반 stream에서 두 음 이상을 건너뛸 때는 건너뛴 음의 80% 이상이 위 조건으로 설명되어야 검색 결과를 허용한다.
- 1박은 metric 1.0, 3박은 0.65, 나머지 정박은 0.45, offbeat는 0.2로 구분하여 downbeat 이외의 박절 계층도 구조 가중치에 반영한다.
- cue 기반 structural stream과 원본 surface stream을 모두 인덱스에 보존하므로 일반 선율 검색 능력을 없애지 않는다.

## 2026-08-30: Beauty and the Beast upbeat 결과 진단·Tuplet 설계

- 제보 Query로 `work-4229f41fc20f9574` 26–28마디 결과를 재현했다.
- 실제 선택 후보는 26마디 3.5박에서 시작하는 `E4–F4–D5–C5–C4–E4–G4–F4`였다.
- Query와 U/D 방향열이 모두 같아 contour 100점, rhythm DTW 83점이었지만 meter 15점, structural reduction 43점에 불과했다.
- Query 첫 downbeat에 대응하는 후보 downbeat가 없는데도 기존 최대 -8점 감점만 적용되어 local similarity 66점, 전체 3위로 노출된 것이 원인이었다.
- 중요 박 일치는 최대 +6점, 중요 박 불일치는 최대 -14점으로 조정했다. 해당 결과의 local similarity는 60점으로 내려갔다.
- 감점 후에도 corpus 내 상대 순위가 3위로 남아, downbeat 대응 0개·structural 50점 미만·최종 local 65점 미만을 동시에 만족하는 `surface-only weak match`는 일반 결과에서 제외하도록 했다. 제보된 Beauty and the Beast 결과는 더 이상 반환되지 않는다.
- Tuplet 입력은 선택한 음표 수 N을 actual-notes로 고정하고 `N notes in the time of M`의 normal-notes M을 고르는 방식을 권장한다.
- 기본 preset은 3:2, 2:3, 5:4, 6:4, 7:4로 두고, 선택 음표들의 written duration에 M/N을 곱해 실제 재생·검색 시간을 계산한다.
- 첫 구현에서는 같은 written note value를 가진 음표만 한 tuplet으로 묶고, 혼합 음가는 후속 단계에서 custom span으로 확장한다.
- QueryEvent에는 tupletGroup, actualNotes, normalNotes, writtenDuration을 보존하고 MusicXML에는 time-modification과 시작/끝 tuplet notation을 생성한다.
- 검색은 표기 음가가 아니라 effective duration과 IOI를 사용하고, Exact rhythm 검색에서는 tuplet ratio까지 반영된 실제 시간이 같아야 한다.
- 장기적으로 `Advanced search` 접이식 패널에 Exact interval, 쉼표 처리, 리듬 허용 범위, downbeat 기준, 구조 가중치와 결과 내 재검색을 모으는 방향을 채택한다.

## 2026-08-30: Schenker-informed 기둥선 검색

- 완전 자동 셴커 분석이라는 표현 대신 `Schenker-informed structural reduction` 보조 계층으로 구현했다.
- 각 선율 음에 강박, 상대적으로 긴 음가, 프레이즈 양끝, 국소 최고·최저음을 더하고 경과음·보조음을 빼서 `structuralWeight`를 계산한다.
- 동일 방향의 양쪽 step으로 연결되는 가운데 음은 passing, 앞뒤 음이 같고 step으로 이탈·복귀하는 음은 neighbor로 분류한다.
- passing/neighbor는 최소 가중치를 유지하되 local alignment의 삽입·삭제·대체 비용을 낮춘다. 따라서 장식음 수와 표면 리듬이 달라도 기둥음 진행이 정렬될 수 있다.
- weight 0.62 이상의 음을 기둥선으로 축약한다. 기둥음이 너무 적으면 weight 상위 음을 시간순으로 보충하여 최소 비교선을 만든다.
- Query 기둥선과 후보 기둥선을 별도의 transposition-invariant local alignment로 비교한다.
- 구조 similarity 90 이상은 confidence에 따라 최대 +8점, 75 이상은 최대 +4점, 60 이상은 최대 +1점을 준다.
- 구조가 다를 때는 별도의 구조 벌점을 주지 않는다. 표면 선율 점수는 그대로 유지하여 구조 분석의 불확실성이 결과를 과도하게 떨어뜨리지 않게 했다.
- 결과의 Structural score와 Why this matched에 축약된 Query/후보 기둥음 수, 구조 similarity와 bonus 여부를 표시한다.
- 장식음과 다른 표면 리듬을 사이에 둔 동일 기둥선, passing/neighbor 저가중치, 다른 기둥선 무벌점 회귀 테스트를 추가했다.
- 전체 테스트 43개 통과.

## 2026-08-30: Exact interval·결과 내 재검색·Downbeat 가중치

- Melody only와 Melody + Rhythm에 `Exact interval only` 옵션을 추가했다.
- Exact는 절대 MIDI pitch 고정이 아니라 일정한 조옮김을 허용한 연속 음정열의 완전 일치로 정의한다.
- Melody only Exact는 음정열만 비교하고 리듬은 무시한다.
- Melody + Rhythm Exact는 음정열과 내부 쉼표가 만든 IOI 및 마지막 음가까지 정확히 같아야 한다. insertion, deletion, substitution은 허용하지 않는다.
- Exact 결과 설명에 조옮김 허용과 모드별 완전 일치 조건을 명시한다.
- `Search within results` 옵션을 추가했다. 현재 결과에 들어 있는 work ID 집합을 다음 API 요청의 scope로 전달하고, n-gram 후보를 정렬하기 전부터 해당 작품군으로 제한한다.
- 결과가 없거나 첫 검색 전에는 결과 내 재검색을 비활성화하며, Clear 및 Contour 전환 시 scope를 해제한다.
- 두 옵션 상태를 sessionStorage에 보존하고 Copy Query JSON에는 Exact 설정을 포함한다.
- Downbeat는 독립 bonus가 아니라 정렬된 중요 박의 증거로 사용한다. Query downbeat와 후보 downbeat가 선율적으로 일치하면 최대 +4점, 중요한 박이 어긋나면 최대 -8점을 적용한다.
- 결과의 meter score와 Why this matched 설명에 실제 downbeat 대응 개수를 반영한다.
- Exact interval, rhythm 조건, 결과 scope와 downbeat 증거 회귀 테스트를 추가하여 전체 40개 테스트 통과.
- 프로덕션 빌드 통과 및 로컬 브라우저에서 두 옵션의 배치, 활성/비활성 상태와 Exact 검색 동작을 확인했다.

## 2026-08-30: 검색 개선 1–3단계 구현

- Query의 sounding note마다 누적 onset을 계산하고 내부 쉼표 길이를 다음 음까지의 IOI에 보존한다. 선행 쉼표는 첫 sounding onset을 기준으로 정규화되므로 검색에 영향을 주지 않는다.
- corpus note에도 인덱스의 절대 onset을 전달하여 query와 후보가 같은 IOI 표현으로 rhythm DTW에 들어가도록 했다.
- 리듬 오차는 전역 tempo 정규화 뒤 log2 ratio로 계산하며 약 9% 이하는 dead zone으로 무감점 처리한다. 이후에는 선형+제곱 비용으로 큰 변화가 빠르게 불리해진다.
- Melody + Rhythm 최종 점수에 비선형 rhythm gate를 적용했다. 85점 이상은 무감점, 65–85는 약한 감점, 45–65는 큰 감점, 45 미만은 강한 감점이다.
- 제보 Query에서 기존 `Lead the Way` 오탐은 rhythm 54.9점, local similarity 54.9점으로 내려갔다. 이전 값은 rhythm 43.8점, local similarity 77.3점이었다. 새 voice 파서로 인덱스를 재생성하면 비정상 후보 stream 자체도 제거된다.
- Contour는 S/U/D 방향 완전 일치를 계속 필수로 하고 step/leap은 soft ranking evidence로만 사용한다.
- 그린 선의 4px 이하 수직 흔들림은 S로 보고, 나머지 선분 이동량 중앙값의 1.8배이면서 최소 14px 이상인 명확한 움직임만 leap으로 해석한다.
- step/leap 경계에서 멀수록 shape confidence를 높이고, 애매한 제스처는 결과 순위에 적게 반영한다.
- Contour는 sounding point만 만들기 때문에 쉼표를 무시한다.
- 관련 회귀 테스트를 34개로 확장했다.

## 2026-08-30: 리듬·구조·Contour 검색 점수 설계안

- Melody + Rhythm은 전역 tempo 정규화 뒤 각 대응 IOI/duration ratio의 `abs(log2(q/c))` 오차를 사용한다.
- 작은 리듬 변화에는 dead zone과 완만한 quadratic 비용을 적용하고, 중간 범위 이후 비용을 가파르게 높이는 piecewise loss를 권장한다.
- 초기값 제안: 약 9% 이하는 무감점, 9–25%는 작은 감점, 25% 이상은 급격한 감점. 실제 relevance set으로 보정한다.
- rhythm score 85 이상은 최종 순위에 거의 영향을 주지 않고, 65–85는 완만한 감점, 45–65는 큰 감점, 45 미만은 하위 bucket 또는 제외하는 gate를 Melody + Rhythm 모드에 추가한다.
- 쉼표는 독립 pitch event로 비교하지 않되, 앞 음 onset에서 다음 음 onset까지의 IOI에 포함한다. 선행 쉼표는 무시할 수 있지만 내부 쉼표는 리듬 정보로 보존한다.
- 현재 melody local alignment는 음정 크기, U/D/S 방향, step/leap 형태, insertion/deletion을 이미 비용화한다. 향후 query 길이·구조 중요도에 따라 비용을 보정한다.
- downbeat 일치 자체에 무조건 bonus를 주지 않고, 양쪽의 중요한 박절 위치에 대응한 음이 선율적으로도 일치할 때 match weight를 높이며 중요한 박의 불일치는 더 크게 벌점화한다.
- Schenker 검색은 완전 자동 분석이라고 부르지 않고 `structural reduction` 또는 `Schenker-informed` 보조 점수로 구현한다.
- surface, reduced foreground/중경층 후보, phrase anchor의 3단계 stream을 만들고 passing/neighbor tone 축약 뒤 각 단계의 interval/contour local alignment를 비교한다.
- 구조 점수는 duration, downbeat, chord-tone support, tie sustain, local registral prominence, phrase/cadence 위치와 분석 confidence로 산출하며 최종 bonus는 약 10점 이내로 제한한다.
- Contour 검색의 필수 조건은 S/U/D 방향열 일치로 단순화하고 step/leap은 soft bonus로만 사용한다.
- 그린 선의 step/leap 의도는 절대 반음뿐 아니라 각 stroke의 비영(非零) 수직 이동 중앙값과 비교한다. 다른 선분보다 약 1.8배 이상 크게 움직인 선분을 leap 후보로 보고 차이가 클수록 bonus confidence를 높인다.
- Contour의 쉼표는 무시한다. 방향은 연속된 sounding point 사이에서 계산하므로 검색 의미가 유지된다.

## 2026-08-29: Query 복사와 Lead the Way 오탐 재현

- 입력 영역 도구 모음에 `Copy Query` 버튼을 추가했다.
- 현재 mode, meter, 모든 음표·쉼표의 pitch, duration, tie 정보를 포함한 `musicanote-query` JSON을 클립보드에 복사한다.
- 복사 성공 시 버튼이 잠시 `Copied` 상태로 바뀌며, 실패하면 브라우저 클립보드 권한 안내를 표시한다.
- 제보 Query `E4(0.5), F4(1), A4(1), G4(1), rest(1), E4(0.5), F4(1), A4(1), G4(1)`로 `work-1e88e39d02541341`을 재현했다.
- 기존 잘못된 후보 stream `F2–B♭2–D3–C3–A2–B♭2–D3–C3`과 local similarity 77점, contour 100점, rhythm DTW 44점으로 정렬된 것을 확인했다.
- 화음 voice 상속 파싱 오류가 주원인이며, 낮은 리듬 점수 결과를 별도 탈락시키지 않는 현재 기준도 오탐 노출에 기여했다.

## 2026-08-29: 속성이 없는 못갖춘마디와 화음 voice 상속

- Huey Lewis의 `4. The Power of Love, Piano Solo.musicxml.xml`은 첫 마디가 4/4의 1박 길이지만 `implicit="yes"`가 없고 `number="1"`로 저장되어 있었다.
- 첫 마디의 실제 cursor 길이가 박자표의 정규 마디 길이보다 짧은지도 계산하여 못갖춘마디를 판정하도록 확장했다.
- 이 경우 첫 마디는 0, 다음 XML 마디 2는 표시 마디 1이 되도록 이후 숫자 마디 번호 전체에 offset을 적용한다.
- Verovio 상세 악보·악보 조각, 검색 API 표시 번호, 새 MusicXML 인덱스가 같은 판정법을 사용한다.
- `work-1e88e39d02541341`은 `Lead the Way` 피아노 파트의 F2–B♭2–D3–C3 반복을 잡은 결과였으나, 화음 후속 음표에 `<voice>`가 생략되었을 때 voice 1로 새로 분리한 기존 파서 때문에 생긴 잘못된 검색 스트림임을 확인했다.
- 화음 후속 음표는 직전 화음 시작 음표의 voice와 staff를 상속하도록 인덱서 파싱을 수정했다. 인덱스 재생성 후 해당 오탐은 제거 대상이다.
- Python 파서 컴파일 및 Huey Lewis 원본 표본 파싱 확인, 전체 테스트 29개와 프로덕션 빌드 통과.

## 2026-08-29: 못갖춘마디 번호와 악보 조각 재생 위치

- MusicXML 첫 마디에 `implicit="yes"`가 있으면 표시 마디 번호를 `0`으로 정규화한다.
- 검색 엔진 내부의 1부터 시작하는 마디 순번과 MusicXML의 표시 마디 번호를 분리했다.
- 표시 번호 `0`을 falsy 값으로 오인해 내부 순번 `1`로 바꾸던 API fallback 오류를 제거했다.
- 악보 상세 화면과 검색 결과 악보 조각 모두 원본 MusicXML의 마디 번호를 사용한다.
- 앞으로 새로 만드는 검색 인덱스도 첫 implicit measure를 `0`으로 기록한다.
- 실제 corpus의 `3. Carrying You, Piano Solo.xml`에서 첫 마디가 `implicit="yes" number="0"`이고 인덱스에도 `mn: "0"`으로 보존되는 것을 확인했다.
- 검색 결과 악보 조각의 재생 막대를 시간 비율 기반 애니메이션에서 Verovio SVG 음표의 실제 x좌표 기반 이동으로 변경했다.
- 재생 중 현재 음표가 가로 스크롤 영역 중앙에 오도록 자동 스크롤하며, tie로 합쳐진 음은 첫 음표 위치에서 합산 길이만큼 유지한다.
- 전체 테스트 27개와 Vite 프로덕션 빌드 통과.

## 프로젝트 기준

- 검색 corpus: 당분간 `K:/Music Analysis/musicxml`의 MusicXML 데이터
- 악보 렌더링: Verovio
- 검색 구조: compact MusicXML melody stream + SQLite n-gram 역색인 + 후보 정밀 비교
- 최소 query: 음표 4개. 일반 선율은 6–12음, contour는 8–12음 권장
- 원본 표기 보존: 조표, 임시표, 음자리표, 파트, 마디 번호, tie와 쉼표는 원본 MusicXML 기준

## 누적 요청 및 구현 상태

### Query 입력

- Clear 뒤에도 빈 오선과 건반 유지
- Delete last 및 선택 음표 삭제
- 음표별 음가 조절과 64분음표–온음표 입력
- 음가 단계: 0.0625, 0.125, 0.25, 0.5, 1, 1.5, 2, 3, 4박
- 인접한 동일 음 두 개를 선택해 tie 생성; 검색·재생에서는 하나의 sounding event로 병합
- 오선 음표 선택과 수직 드래그 pitch 수정
- Melody only에서는 stem 없는 note head 사용
- 독립 contour 패널, Undo/Redo/Clear 및 contour 전용 검색
- 허밍 입력 실험 기능
- 긴 query 재생 뒤 기본 query로 되돌아가던 상태 문제 수정
- 2026-08-28: Query 건반 범위를 C2–E6(MIDI 36–88)로 확장

### 검색 및 파싱

- MusicXML을 melody/interval/contour/rhythm 특징으로 파싱
- tie chain 병합, source part/staff/voice 식별
- 3-gram 역색인으로 후보 위치 검색
- Melody, Melody + Rhythm, Contour 모드별 점수 분리
- Contour 검색은 이전 오선 query와 분리; U/D/S 전체 일치만 허용하고 Step/Leap 일치를 우선
- 2026-08-28: n-gram 후보 뒤에 semi-global Smith–Waterman 방식 local alignment 추가
  - 후보 앞뒤 자유 절단
  - 장식음/추가음 insertion과 query 누락 deletion 허용
  - 음정, 방향, Step/Leap, 리듬 비율의 모드별 비용
  - query coverage 75% 미만 후보 제거

### 검색 결과와 상세 악보

- 결과별 원본 MusicXML 악보 조각, 파트 이름, 재생, YouTube iframe
- 검색에 감지된 음표만 붉게 표시
- 화음 구성음 하나가 감지되면 같은 onset의 chord stack 전체 강조
- tie continuation 전체 강조
- 원본 조표, 박자표, 음자리표, 임시표, 쉼표와 마디 번호 유지
- 검색 파트만 발췌하고 상세 페이지에서는 전체 XML 악보 표시
- 악보 조각 클릭 시 상세 악보의 일치 위치로 이동
- 카드 악보는 620px 고정 engraving 폭과 가로 스크롤 사용
- 상세 악보 페이지 여백·배율·페이지 하단 잘림 조정
- 2026-08-28: 결과 악보 재생 시 마디 경계 표시용 tie 조각을 다시 하나의 sounding event로 병합
- tie로 합산된 전체 음가 동안 oscillator를 한 번만 attack하고 지속하도록 수정
- 검색 결과 악보 위에 시간 진행을 따라가는 붉은 세로 playhead 추가
- 쉼표 첫 이벤트에 원본 음표 전체를 메타데이터로 덮어써 쉼표가 음표로 재생되던 오류 수정

### 분석과 외부 데이터

- pitch, rhythm, measure density 통계
- 4–8음 가변 길이 interval motif 분석
- motif 점수: 반복 횟수 × 완만한 길이 보너스 × 평균 지속시간 보너스
- 긴 motif에 포함되는 짧은 중복 패턴 억제
- YouTube Data API 일일 quota 범위의 대표 영상 backfill 스크립트와 상태 파일
- 외부 재생 불가 영상 제외를 위한 embeddable/syndicated 조건

### 백업

- 로컬 Git 저장소와 첫 백업 커밋 `e5d8ba8` 생성
- GitHub `snoopyinwonderland/MusicSearch` 원격 연결
- 대용량 재생성 인덱스(SQLite/JSONL), 환경변수, node_modules 및 build 산출물 제외
- GitHub 저장소 Private 전환은 이메일 본인 확인 대기 중이며 아직 push하지 않음

## 검색 개선 로드맵

1. **Local alignment** — 1차 구현 완료, 비용 보정 진행
   - 실제 대응 음표 경로, insertion/deletion 및 결과 악보 인덱스 검증 완료
   - 정렬 비용을 평가 query set으로 보정
   - 반음 경과음은 작은 substitution으로 해석될 수 있으므로 실제 정답 세트에서 insertion 경계를 보정
2. **제한적 rhythm DTW** — 1차 구현 완료
   - n-gram/local alignment 후보의 실제 일치 span에만 적용
   - 전체 템포 확대·축소에 불변인 duration 비교
   - 22% diagonal band와 1:1, 1:2, 2:1 대응만 허용
   - Melody + Rhythm 최종 유사도에 22% 반영; Melody only와 Contour에는 미적용
3. **음표 분할·병합 규칙**
   - 긴 음과 반복음, tie 유무가 다른 동등 표현, grace note 처리
4. **Melody stream 개선**
   - polyphony, chord top/bottom/metric voice, 피아노 양손과 교차 성부
5. **구조적 음표 검색**
   - 강박, 긴 음, 프레이즈 경계, 종지, 음역 극점 기반 salience
6. **다중 인덱스 및 대규모 평가**
   - exact/coarse interval, contour, rhythm, structural n-gram
   - 정답 세트 기반 Recall@K, MRR, 구간 IoU 측정

## 저작권 제한 corpus 공개 정책

### 2026-08-28 요청

- 노래방 MIDI corpus를 한국 가요 저작권·유사도 연구와 검색에 활용
- MIDI 제작자의 전체 편곡/악보는 공개하지 않음
- 검색 결과 악보 조각과 상세 화면의 제한된 문맥만 제공하는 방안 검토
- 저장 공간과 공개 정책이 준비될 때까지 한국 가요 MIDI corpus 추가는 보류하고 검색 엔진 개선을 우선

### 권장 설계

- 원본 MIDI와 전체 변환 악보는 비공개 저장소에만 보관하고 직접 다운로드 API를 두지 않는다.
- 공개 검색 인덱스에는 interval/contour/rhythm n-gram, 통계와 opaque source ID만 저장한다.
- 작품별 권리 상태를 `licensed`, `public-domain`, `research-preview`, `metadata-only`, `blocked`로 관리한다.
- `research-preview`는 검색 일치 음표 중심의 최소 문맥만 서버에서 즉시 렌더링하고 영구 SVG/MusicXML URL을 만들지 않는다.
- 상세 화면은 전체 악보 대신 일치 지점 전후의 제한된 문맥과 분석 설명을 제공한다.
- 사용자가 임의 마디로 이동하거나 연속 조각을 조합해 전체 악보를 복원하지 못하도록 한다.
- 악보 조각에 출처, 연구/비평 목적, 권리자 및 삭제 요청 경로를 표시하고 접근 로그와 rate limit을 둔다.
- MIDI 재생은 원곡/편곡을 복원할 수 있는 긴 재생 대신 검색된 짧은 단선율 또는 합성된 비표현적 preview로 제한한다.
- 허용 길이를 고정 마디 수만으로 결정하지 않고, 전체 대비 비중·핵심성·시장 대체 가능성과 이용 목적을 함께 검토한다.
- 실제 공개 전 한국저작권위원회 상담 또는 음악저작물/편곡 이용허락 검토를 거친다.

## 최근 검증

- 2026-08-28: 전체 테스트 26개 통과
- local alignment 전용 테스트: 전조된 내부 구간, 반복 장식음 insertion, query note deletion
- 실제 SQLite 검색 결과의 alignment index가 악보 조각 범위 안에 있는지 통합 검증
- rhythm DTW: 전역 tempo augmentation, 1→2 음가 분할, 상이한 리듬 페널티 검증
- 마디 경계를 넘는 표시용 tie 조각이 재생 직전에 하나의 2박 sounding event로 복원되는지 검증
- TypeScript 및 Vite 프로덕션 빌드 통과

### 2026-08-30 — A Whole New World 21마디 순위 회귀 수정

- 문제 원인: `E–F–A–G / 쉼표 / E–F–A–G` 쿼리와 조옮김 관계로 연속 음정열이 완전히 같은 21마디 선율이, 길게 타이된 기둥음 때문에 rhythm DTW에서 과도한 감점을 받아 상위 결과에서 사라짐.
- 일반 유사 검색에서도 전체 후보 선율을 대상으로 조옮김 불변의 연속 음정열 완전 일치 구간을 별도로 검출하도록 변경.
- 완전한 음정열 증거가 있으면 타이·긴 지속음 때문에 리듬 점수가 검색 결과 자체를 제거하지 않도록 감점 폭을 제한함. 단, 리듬 차이는 순위 결정에 계속 반영함.
- 리듬을 단순 절대 IOI뿐 아니라 `short / normal / long` 반복 형태와 포화된 상대 길이로 비교하는 phrase-shape 점수를 추가함. 긴 기둥음은 `long`으로 유지하되 무한히 큰 오차처럼 계산하지 않음.
- exact interval 결과에서는 잘린 8음 창의 불안정한 구조 보너스와 n-gram 적중 개수가 과도하게 순위를 바꾸지 않도록 제한함.
- Solo/Duet/Trio/Quartet 중 같은 선율의 중복 판본이 있으면 편성명이 붙지 않은 canonical 판본에 작은 대표성 보너스를 부여함.
- 회귀 결과: `A Whole New World.xml`의 20–23마디(핵심 기둥음 21마디)가 전체 1위, 잘못 우선되던 Piano Solo 44–45마디는 해당 곡 결과 중 후순위.
- 자동 테스트 50개 및 프로덕션 빌드 통과.

### 2026-08-30 — Schenker 관점의 구조적 재순위화 보강

- 기본 검색 후보는 원본의 연속 멜로디로 유지하고, 구조 분석은 후보를 띄엄띄엄 새로 만드는 기본 경로가 아니라 재순위화 계층으로만 사용함.
- 기둥음 중요도에 강박, 긴 음가, MusicXML에서 병합된 타이, 음역의 국소 극점, 쉼표 전후 프레이즈 경계를 함께 반영함.
- 쉼표 직전의 종결음과 쉼표 뒤의 재진입음을 강한 프레이즈 경계로 처리해, 쿼리의 쉼표와 대상 악보의 긴 타이·지속음이 서로 다른 표면 표기여도 골격을 비교할 수 있게 함.
- 단순히 두 이웃 사이를 순차 진행한다는 이유만으로 passing/neighbor로 낮추지 않음. 짧은 음가 또는 약박이라는 표면 증거가 함께 있을 때만 장식음 역할을 부여함.
- cue 음표는 계속 가장 강한 장식층 증거로 취급하고, 일반 음표를 건너뛰는 sparse alignment는 기존처럼 생략 음표의 80% 이상이 명확하게 설명될 때만 허용함.
- 구조 일치 보너스는 일반 유사 결과에서 최대 12점으로 제한함. 이미 연속 음정열이 완전히 일치한 결과에는 최대 3점만 허용해 구조 분석이 리듬·연속 선율 증거를 압도하지 않게 함.
- `A Whole New World` 21마디 계열은 구조 점수 100으로 최상위에 유지되고, 리듬 형태가 덜 맞는 동일 음정열 곡들은 그 아래로 정렬됨.
- 장식음 분류, 강박 보호, 쉼표 경계, 긴 타이 기둥음 및 실제 순위 회귀를 포함한 자동 테스트 52개 통과. 프로덕션 빌드 통과.

### 2026-08-30 — 분석 보고서 반영: 박자표별 metric hierarchy

- 외부 `analysis_report.md`의 음악이론 검토를 반영함. 가장 높은 우선순위로 지적된 4/4 중심의 metric weight 모델을 교체함.
- 기존 문제: 3/4의 3박을 4/4의 중강박처럼 처리하고, 6/8을 길이만 3인 단순박자로 보며, 후보 악보의 실제 MusicXML 박자표 대신 query 박자표로 후보 구조를 분석하고 있었음.
- `metricWeightAt(position, meter)`와 `parseMeter()`를 추가해 박자표별 계층을 분리함.
  - 2/4: 1박 > 2박 > 분할박
  - 3/4: 1박 > 동일한 2·3박 > 분할박
  - 4/4: 1박 > 3박 > 2·4박 > 분할박
  - 6/8·9/8·12/8: 점4분음표 단위의 복합박 그룹 시작을 강박으로 처리
  - 5/4: 기본 3+2 그룹, 7/8: 기본 2+2+3 그룹으로 처리
- query와 후보가 서로 다른 박자표여도 각각의 metric hierarchy를 계산한 뒤 강도 수준을 비교하도록 `metricalEvidence`를 변경함.
- 검색 후보마다 해당 구간의 MusicXML 박자표를 읽어 structural annotation과 metric score에 사용함. 중간 박자 변경도 후보 시작 마디를 기준으로 반영하며, 반복 XML 파싱을 줄이기 위한 meter cache를 추가함.
- MusicXML의 `3+2` 같은 additive `<beats>` 값도 합산해 읽도록 보완함.
- 검색 UI의 박자 선택 항목을 2/4, 3/4, 4/4, 5/4, 3/8, 6/8, 7/8, 9/8, 12/8, unknown으로 확장함.
- 악보 조각의 beat 좌표는 4분음표 단위이므로 6/8 마디를 6이 아닌 3단위로 채우도록 쉼표·타이 분할 계산을 수정함.
- 보고서의 두 번째 높은 우선순위도 반영: spelling의 음이름 글자 간격을 이용해 `F–G♯` 같은 증2도는 contour에서 step, `C–E♭` 같은 단3도는 leap으로 구별함.
- 단순·복합·비대칭 박자, 서로 다른 meter hierarchy 비교, 증2도/단3도 구별, 6/8 악보 조각 길이 및 기존 검색 순위를 포함한 자동 테스트 59개 통과. 프로덕션 빌드 통과.

### 2026-08-30 — 낮은 품질 결과가 목록에 남는 원인 진단

- 사용자 화면의 `All Out of Love`, Violin, 89–90마디 결과를 확인함. Query는 `E–F–A–G / 4분쉼표 / E–F–A–G`, 첫 E는 8분음표이고 나머지는 4분음표인 기존 4/4 query.
- 감지된 후보는 `E♭–F–G♭–E♭–C–D♭–E♭–C`의 연속 8음으로, 삽입·누락 없이 U-U-D-D-U-U-D contour만 완전히 같음.
- component score는 pitch 71, interval 84, contour 100, rhythm 50, meter 58, structural 43, 최종 local similarity 40임. 구조 보너스는 적용되지 않음.
- sparse melody 오검출은 아님. 연속 8음을 사용했기 때문에 `sparseAlignmentAllowed`의 장식음 80% 조건은 검사할 건너뛴 음 자체가 없음.
- 남은 직접 원인 1: 검색 API가 최소 합격점 없이 요청된 상위 20개를 채워 반환하므로 40점 후보도 18위에 표시됨.
- 남은 직접 원인 2: 낮은 결과 제거 조건이 `metric.matches === 0`일 때만 동작함. 이 후보는 시작음이 4.25박의 약박이지만 뒤쪽 음 하나가 query의 중강박 계층과 일치하여 `metric.matches=1`이 되고 필터를 우회함.
- 권장 후속 수정: 정확 음정열 결과는 유지하되 일반 Melody+Rhythm 결과에 최소 local/interval/rhythm admission threshold를 두고, 결과 수가 20개보다 적더라도 낮은 품질 결과로 채우지 않음. 박절 일치 한 곳만으로 저점 필터 전체를 해제하지 않도록 조건을 분리함.

### 2026-08-30 — 결과 합격 기준 및 상세 화면 정렬 경로 수정

- 기존 수정 사항을 보존한 상태에서 현재 검색 코드와 두 사용자 제보 구간을 다시 확인함.
- 검색 결과는 `limit`를 목표 개수가 아닌 최대 개수로만 취급함. 조건을 통과한 작품이 적으면 결과 수도 그대로 적게 반환함.
- 일반 Melody+Rhythm 결과의 기본 합격 조건을 local similarity 55 이상, interval 65 이상, rhythm 55 이상으로 설정함.
- 구조적으로 확실한 변형은 local 50, interval 60, rhythm 45, structural 82 이상일 때만 제한적으로 예외 허용함. 조옮김 불변의 연속 음정열 완전 일치와 순수 contour 검색은 별도 의미가 있으므로 이 gate에서 제외함.
- `All Out of Love` Duet/Trio 89–90마디는 contour 방향만 100이고 local 40, rhythm 50, structural 43이므로 결과에서 제외됨.
- 상세 악보 화면이 URL의 마디 범위 안에서 query를 임의로 다시 정렬하던 로직을 수정함. 검색 결과 카드가 서버 alignment의 `onset:pitch` 대상 목록을 URL에 전달하고, 상세 화면은 이를 원본 전체 악보의 음표에 정확히 매핑함.
- 이전 링크처럼 target parameter가 없는 경우에는 session에 보존된 검색 결과 alignment를 우선 복원하고, 그것도 없을 때만 기존 local fallback을 사용함.
- `A Whole New World.xml` 20–23마디에서 첫 감지 음표가 앞 프레이즈의 4분음표가 아니라 20마디 2.5박의 `F♯4` 8분음표임을 회귀 테스트로 고정함.
- 저점 contour 우연 일치 제외, 결과 수 미충족 허용, 구조 예외, 첫 target 경계를 포함한 자동 테스트 62개 및 프로덕션 빌드 통과.
## 2026-08-30 — 프레이즈 문맥 기반 검색 구간 선택

- 특정 작품·쿼리·음높이를 고정하는 순위 규칙 대신 일반적인 프레이즈 증거 모델을 추가했다.
- `MUSICANOTE_Analysis_Harness_Guide.reviewed.md`의 Sounding Event 원칙에 맞춰 타이 continuation은 새 attack/phrase opening으로 취급하지 않는다.
- 쉼표 전후, 새 attack, 긴 지속음, 타이의 마디 경계 통과를 이용해 `phraseOpeningConfidence`와 `phraseClosingConfidence`를 별도로 계산한다.
- 같은 조옮김 음정열이 여러 곳에 존재하면 첫 출현을 고정 선택하지 않고 모든 출현의 프레이즈 문맥을 비교한다.
- 이전 프레이즈를 마치는 타이 지속음에서 시작하는 후보는 감점하고, 쉼표 뒤 새 attack에서 시작하는 후보를 우선한다.
- 파일명에 `solo/duet/trio/quartet`가 있는지로 판본 순위를 조정하던 `canonicalEditionBonus`를 제거했다.
- MusicXML 인덱서가 병합 Sounding Event의 tie-start provenance를 보존하도록 했다.
- 특정 work ID의 순위를 고정하던 테스트를 제거하고, 합성 음표열로 프레이즈 역할과 복수 출현 선택 논리를 검증한다.
- 검증: Vitest 62개 통과, TypeScript/Vite production build 통과.
## 2026-08-31 — Query 임시표 표기와 Exact 진단

- Query MEI 생성기가 `♯`·`♭` Unicode 표기를 해석하지 못해 MIDI 기반 sharp으로 되돌리던 문제를 수정했다.
- 같은 마디에서 G♯ 뒤 G처럼 동일 음이름을 원래 높이로 되돌릴 때 `accid="n"`을 명시해 제자리표가 표시되도록 accidental state를 추적한다.
- 건반에 ♯/♭ 선택 버튼을 추가했다. 선택은 이후 입력 음의 기본 spelling에 적용하며 sessionStorage에도 보존한다. 기존 음표는 유지하므로 한 Query에서 두 표기를 함께 쓸 수 있다.
- 건반 범위는 E6까지 유지하되 가장 높은 E6 키의 텍스트 라벨은 제거했다.
- Exact 검색은 spelling을 비교하지 않고 MIDI 기반 조옮김 불변 음정열과 리듬만 비교한다는 회귀 테스트를 추가했다. A♯/B♭ 및 G♯/A♭은 같은 Exact pitch evidence로 처리한다.
- 제보된 Hymne à l’amour 구간을 재현한 결과 음정열은 100점으로 완전 일치한다. 다만 Query의 두 번째 G♯4는 1박이고 원본 A♭4는 0.5박이므로 Melody+Rhythm Exact가 아니며 rhythm score는 약 93.61점이다. 이는 enharmonic spelling 때문이 아니다.
- 검증: Vitest 65개 통과, TypeScript/Vite production build 통과.

# 사용자 검증 Query와 오류 사례

이 장은 개발 중 사용자가 직접 입력한 Query, 기대 결과, 발견된 오류를 회귀 검증 자료로 보존한다. 작품 ID나 Query에 맞춘 production 예외를 만드는 용도가 아니다. 각 사례에서 드러난 일반 규칙을 합성 단위 테스트와 corpus 통합 테스트로 검증한다.

## Query 카탈로그

### Q-01 — 기본 7음 연속 선율

- 모드: Melody 또는 Melody + Rhythm
- 음표: `C4(1)–E4(1)–A4(1)–G4(1)–F4(1)–E4(1)–D4(1)`
- 용도: 검색 결과 악보 조각의 배율, 음자리표·조표·박자표 표시 일관성 확인
- 당시 지적: 결과마다 악보 조각 크기가 달랐고 일부 조각에서 음자리표·조표·박자표가 사라졌다.

### Q-02 — 반복 구절과 내부 쉼표

- 모드: Melody + Rhythm, 4/4
- 음표: `E4(0.5)–F4(1)–A4(1)–G4(1)–rest(1)–E4(0.5)–F4(1)–A4(1)–G4(1)`
- contour: `U–U–D–D–U–U–D`이며 쉼표는 방향 계산에서 제외
- 용도: 내부 쉼표 IOI, rhythm DTW, downbeat, phrase boundary, sparse alignment, 결과 합격 기준 검증
- 주요 기대 결과: 조옮김된 `A Whole New World` 20–23마디의 연속 선율이 상위에 나와야 한다.
- 발견된 문제:
  - `work-1e88e39d02541341`에서 잘못 분리된 피아노 voice가 `Lead the Way` 오탐으로 노출됨.
  - `work-4229f41fc20f9574` 26–28마디에서 약박 선율이 contour 100만으로 과대평가됨.
  - `work-f28d9adc7c2a5c75` 89–90마디에서 낮은 품질 후보가 결과 수를 채우기 위해 남음.
  - `work-40153ba016a3ef1f` 20–23마디에서 앞 프레이즈의 타이 종결음이 첫 일치음처럼 표시됨.
  - 긴 타이 기둥음 때문에 정작 적절한 `A Whole New World` 구간이 순위에서 사라진 회귀가 있었음.
- 일반화된 수정: voice 상속, 최소 합격 기준, phrase opening/closing confidence, 타이 continuation 비-attack 처리, 복수 Exact 출현의 문맥 비교.

### Q-03 — Hymne à l’amour 반음계·내부 쉼표 Query

- 모드: Melody + Rhythm, 4/4
- 최종 Query:

```text
B♭4(0.5)–A♭4(0.5)–G4(1)–rest(0.5)–
G4(0.5)–G4(0.5)–B4(0.5)–D5(0.5)–F5(0.5)–E♭5(2)
```

- 최초 입력에서는 `A♯4–G♯4–G4 … D♯5`로 표기했고 두 번째 음가를 1박으로 입력함.
- 원본과 맞게 B♭/A♭/E♭로 respell하고 두 번째 음가를 0.5박으로 수정한 뒤 interval 100, rhythm 100의 Exact가 됨.
- 용도: 이명동음, 제자리표, Exact interval/rhythm, 같은 pitch 반복 target 표시 검증
- 발견된 문제:
  - Unicode `♯/♭`를 MEI parser가 읽지 못해 sharp 기본 표기로 돌아감.
  - G♯ 뒤 G에 제자리표가 표시되지 않음.
  - 건반에서 sharp/flat 입력 선호를 선택할 수 없었음.
  - `work-2a0425eab04e0285` 11–13마디 상세 화면이 같은 마디의 동일 pitch 중 잘못된 음을 색칠함.
- 일반화된 수정: spelling과 MIDI identity 분리, accidental state 추적, 입력 기본 spelling 선택, XML note의 measure/pitch뿐 아니라 정확한 beat까지 target 매핑.

### Q-04 — 긴 Query

- 길이: 약 20개 음표
- 용도: Query 재생과 상태 보존 검증
- 당시 지적: 재생은 끝까지 되었지만 재생 후 Query가 기본 Query로 교체됨.
- 기대 동작: 재생 상태와 Query 편집 상태를 분리하고 재생 종료 뒤 입력 event를 변경하지 않는다.

### Q-05 — Contour draw Query

- 기본 토큰: `S`, `U`, `D`; 쉼표는 무시
- 세부 가중치: 명확한 이동 폭일 때 Step/Leap 일치에 추가 가중치
- 당시 지적:
  - 이전 오선 Query가 contour 검색에 남아 있는 듯한 결과가 나타남.
  - 입력 contour와 무관한 후보가 노출됨.
  - 띄엄띄엄 고른 음의 방향만 같아 contour 100이 되는 결과의 의미가 부족함.
- 기대 동작: contour 전용 검색은 오선 pitch/rhythm Query와 완전히 분리하고 U/D/S 전체 방향 일치를 입장 조건으로 사용한다.

### Q-06 — 동일음 두 개의 Query tie 입력

- 입력: 인접한 같은 pitch의 음표 두 개를 오선 또는 음가 패널에서 선택한 뒤 `Tie` 실행
- 당시 지적: 음가 조정 패널에는 `⌒`가 표시되고 Query 데이터에도 `tieGroup`이 생기지만 Verovio 오선에는 타이 곡선이 나타나지 않음.
- 원인: MEI `<tie startid/endId>` control element를 `<section>` 바로 아래에 두어 Verovio가 오선 control event로 해석하지 못함.
- 해결: tie chain의 첫 note에 `tie="i"`, 마지막 note에 `tie="t"`, 중간 note에 `tie="m"` 역할을 직접 기록한다.
- 회귀 조건: 두 음표의 MEI tie 역할, 한 번의 playback attack, 검색 전 Sounding Event 병합을 각각 독립적으로 검증한다.

## 결과·표시 오류 사례 레지스트리

| ID | 작품·구간 | 사용자 지적 | 일반 회귀 조건 | 상태 |
|---|---|---|---|---|
| R-01 | 초기 전체 검색 | 결과가 계속 `Reach for the Stars!, Piano Solo`만 표시 | mock/default 결과가 실제 API 응답을 덮지 않아야 함 | 수정됨 |
| R-02 | `work-798afc456b55aacb`, 63–71 | 일치 구간이 너무 넓고 마디 전체가 칠해짐 | alignment가 선택한 실제 음표만 강조 | 수정 후 반복 확인 대상 |
| R-03 | 같은 구간 | 악보 조각은 63마디, 상세는 62마디; 마디선·번호 없음 | pickup offset을 포함해 XML 표시 번호를 단일 기준으로 사용 | 수정됨 |
| R-04 | 같은 구간 | 원본은 flat인데 조각은 sharp, 낮은음자리표 구간이 높은음자리표로 표시 | 원본 spelling·clef·key signature 보존 | 수정 후 corpus 회귀 필요 |
| R-05 | 같은 상세 화면 | 페이지 아래가 잘리고 음표가 크며 악보가 빡빡함 | Verovio page margin/scale로 모든 system bbox 보존 | 수정 후 시각 회귀 필요 |
| R-06 | `work-7c19379be93970a6`, 161–166 | tie와 쉼표 처리 오류, D5 tie chain 일부만 강조·재생 | tie chain은 한 Sounding Event, 모든 표기 segment를 강조 | 수정됨 |
| R-07 | 같은 구간 | 감지 음표 패널에 피아노 파트가 섞이고 바이올린만 표시되지 않음 | 검색된 part/staff/voice만 excerpt에 유지 | 수정됨 |
| R-08 | `work-01dcd7e4c462fc59`, 29–30 | 조표·파트명 누락, `파레파레` 원본 음표 소실, 조각과 상세 29마디 불일치 | 원본 마디는 삭제하지 않고 match만 색칠; effective attributes 복원 | 수정 후 시각 회귀 필요 |
| R-09 | `work-2f04f3fbe151954c`, 13 | 화음의 네 번째 attack에서 세 음만 색칠 | root와 모든 `<chord/>` sibling을 함께 강조 | 수정됨 |
| R-10 | `work-1e88e39d02541341`, 45–52 | 빨간 음표가 하나도 없어 무엇을 찾았는지 알 수 없음 | 결과 alignment target을 상세 URL과 session에 보존 | 수정됨 |
| R-11 | `work-4229f41fc20f9574`, 26–28 | 프레이즈와 무관한 upbeat 음들이 선택됨 | 중요 박 불일치와 낮은 structural/rhythm 근거를 입장 조건에 반영 | 수정됨 |
| R-12 | `work-f28d9adc7c2a5c75`, 89–90 | 띄엄띄엄 선택한 음 때문에 contour 100 | sparse skip은 명확한 cue/passing/neighbor 증거가 있을 때만 허용 | 수정됨 |
| R-13 | `work-40153ba016a3ef1f`, 20–23 | 앞 프레이즈 마지막 4분음표가 첫 match로 표시 | 타이 종결 sustain은 새 phrase attack이 아님 | 수정됨 |
| R-14 | `work-2ca726d2e2f7b93e`, 3–5 | sharp/flat 때문에 Exact가 아닌 것처럼 보임 | Exact identity는 MIDI interval; rhythm Exact는 실제 IOI·음가까지 동일 | 진단 완료 |
| R-15 | `work-2a0425eab04e0285`, 11–13 | 반복 G 등 빨간 표시 위치가 잘못됨 | XML `divisions/backup/forward/chord`로 계산한 beat까지 target과 일치 | 수정됨 |

## 입력·재생·탐색 UI 오류 사례

- Clear 후 건반과 빈 오선까지 사라짐: Query event만 비우고 입력 UI는 유지해야 한다.
- Delete가 무엇을 지우는지 불명확함: 선택 음표가 있으면 선택 항목, 없으면 마지막 event를 삭제하고 버튼 문구로 대상을 표시한다.
- 건반 수가 적음: C2–E6 범위를 제공하되 최고 E6 텍스트 라벨은 표시하지 않는다.
- ♯/♭ 선택 버튼 추가 뒤 건반 아래쪽이 잘림: 선택 버튼을 keyboard flow 밖의 absolute overlay로 배치하여 150px 건반 영역을 밀어내지 않게 한다.
- ♯/♭ 버튼이 건반 위를 가림: 건반 왼쪽에 전용 여백을 예약하고 버튼을 위아래로 배치하여 어느 key와도 겹치지 않게 한다.
- 0.5·1박 외 길이 변경 반응 부족: 1/64부터 온음표까지 duration과 오선 공간을 함께 갱신한다.
- `+` 음가 순서: 1.5, 2, 3, 4를 사용하고 2.5·3.5는 제거한다.
- tie 재생 시 attack 반복: tie group을 collapse하여 한 번 attack하고 합산 duration만큼 유지한다.
- 오선 음표 선택·drag 수정: 클릭 선택과 수직 drag pitch 변경을 지원한다.
- 악보 조각 재생선이 왼쪽에 고정: 재생 event 위치를 따라가고 가로 스크롤도 동기화한다.
- 상세 페이지에서 돌아올 때 Query 소실: Query·검색 결과·스크롤을 sessionStorage에 보존한다.
- 검색 결과로 돌아가기 버튼이 새 검색 화면으로 이동: browser history를 사용해 기존 결과 상태로 복귀한다.

## 회귀 테스트 운영 원칙

1. 위 work ID는 corpus 통합 진단용 fixture 식별자이며 production 점수 규칙에서 참조하지 않는다.
2. 핵심 규칙은 작품명·마디·pitch를 고정하지 않은 합성 음표열 단위 테스트로 검증한다.
3. corpus 테스트는 “특정 작품이 무조건 1위”보다 target의 part/staff/voice/measure/beat/pitch와 최소 품질 조건을 검증한다.
4. 사용자 Query JSON은 `schema: musicanote-query` 원형을 보존하되, 회귀 fixture에서는 무작위 event ID를 제거하고 의미 있는 고정 ID를 사용한다.
5. 수정 상태가 “시각 회귀 필요”인 항목은 브라우저 screenshot 기준 이미지를 추가한 뒤 완료로 승격한다.

## 2026-08-31 — Query tie 오선 표시와 건반 영역 수정

- 사용자 검증 사례 Q-06을 추가했다.
- Query MEI tie를 note-level `i/m/t` 역할로 출력하여 Verovio가 실제 타이 곡선을 그리도록 수정했다.
- 기존 tie control element 문자열 검사 대신 시작·종료 note의 tie 역할을 검사하는 회귀 테스트로 교체했다.
- ♯/♭ 선택 토글이 keyboard layout 높이에 포함되어 white key 하단을 자르던 문제를 수정했다. 토글을 absolute overlay로 바꿔 건반의 원래 높이를 보존한다.
- 검증: Vitest 65개 통과, TypeScript/Vite production build 통과.

## 2026-08-31 — ♯/♭ 입력 버튼 배치 보정

- 가로 배치된 accidental toggle이 왼쪽 건반을 가리는 사용자 검증 사례를 기록했다.
- keyboard에 데스크톱 76px, 모바일 62px의 왼쪽 전용 여백을 확보했다.
- ♯과 ♭ 버튼을 세로로 배치하고 해당 여백 안에 고정하여 white/black key와 겹치지 않도록 했다.
## 2026-08-31 — 상세 악보의 동음 반복 target 표시 수정

- `work-2a0425eab04e0285` 11–13마디 Exact 결과의 URL target과 서버 alignment를 대조했다. 올바른 target은 11마디 4·4.5박, 12마디 1·2.5·3·3.5·4·4.5박, 13마디 1박이다.
- 상세 화면의 기존 XML 마커는 마디·pitch·staff·voice만 비교하여 같은 마디에 같은 pitch가 반복되면 앞선 다른 음표를 고를 수 있었다.
- MusicXML의 `divisions`, `backup`, `forward`, `chord`, `grace`를 따라 각 XML note의 정확한 beat를 계산하고 target beat까지 일치할 때만 색칠하도록 수정했다.
- 수정된 B♭–A♭–G Query는 interval, rhythm 모두 100점이며 해당 결과가 Exact임을 확인했다.
- 건반의 ♯/♭ 버튼은 기존 Query 전체를 일괄 변환하지 않고 이후 입력의 기본 spelling만 바꾸도록 조정했다. 따라서 한 Query 안에서 필요할 때 버튼을 전환해 sharp과 flat을 함께 입력할 수 있다.
- 기존 음표 하나만 이명동음으로 바꾸는 기능은 선택 음표 대상 `Respell (♯↔♭)` 명령으로 확장하는 방식을 채택한다.
- 검증: Vitest 65개 통과, TypeScript/Vite production build 통과.
## 2026-08-31 — 검색 결과 클릭 기반 YouTube 백필

- 기존 수집 방식: YouTube Data API `search.list`로 `곡명 official music`을 최대 10개 검색하고, `videos.list`로 공개 여부·외부 임베드 가능 여부·한국 지역 차단·조회수를 확인한다.
- 제목 token 일치율, `official/topic/vevo/soundtrack/ost` 표기, 조회수를 결합해 대표 영상을 선택한다.
- `Piano Solo`, `Violin`, `Duet`, `Trio`, `Quartet` 등 편성명을 제거한 정규화 song title을 cache key로 사용한다. 같은 곡의 여러 편성은 하나의 대표 영상을 공유한다.
- 기존 오류: cache 파일은 `works[normalizedTitle]` 구조인데 검색 서버가 최상위 work ID/title만 조회하여 저장된 영상이 검색 결과에 재사용되지 않았다. 서버 lookup을 실제 cache schema에 맞게 수정했다.
- 검색 결과 악보 조각을 클릭하면 `/api/youtube/backfill/start`에 곡 제목을 `keepalive` POST하고 상세 페이지 이동과 동시에 background worker를 시작한다.
- 클릭한 곡을 첫 검색 대상으로 우선 처리한 뒤 corpus cursor를 이어가며 Pacific Time 기준 하루 최대 100회의 `search.list` 한도까지 백필한다.
- 동시에 여러 결과를 눌러도 서버당 worker 하나만 실행한다. 이미 worker가 동작 중이면 새 process를 만들지 않는다.
- 저장 파일 `data/youtube-matches.json`에는 `titleKey`, `normalizedTitle`, video ID/URL/title/channel/viewCount, embeddable, selectedAt, 검색 query와 편성 공유 여부를 보존한다.
- `data/youtube-backfill-state.json`에는 Pacific date, searchCalls, corpus cursor, 마지막 API 오류와 quota 소진 여부를 저장하여 다음 실행에서 이어간다.
- 같은 날 검색 결과가 없었던 제목은 반복 호출하지 않고 다음 Pacific day에 다시 시도한다.
- 현재 로컬 환경에는 `YOUTUBE_API_KEY`가 설정되어 있지 않다. 이 경우 클릭 endpoint는 worker를 시작하지 않고 `configured: false`를 반환한다.
- 공식 문서 기준 `search.list`는 별도 일일 100회 검색 한도를 사용하고 `videos.list`는 호출당 1 unit이다.
- 검증: 정규화 제목의 편성 공유 cache 테스트를 추가하여 Vitest 66개 통과, TypeScript/Vite production build 통과.
## 2026-08-31 — 상단 음악 카탈로그 키워드 검색

- 상단 메뉴 바에 곡명·작곡가·MusicXML 파일명·파트 키워드로 검색하는 카탈로그 검색창을 추가했다.
- 2글자 이상 입력하면 180ms debounce 후 `/api/catalog/search`를 호출하고 최대 12개의 곡을 자동완성 목록으로 표시한다.
- Solo/Duet/Trio/Quartet 등 편성만 다른 동일 곡은 정규화 제목을 기준으로 한 번만 표시한다.
- 항목을 선택하면 similarity target을 임의 생성하지 않고 `browse=1` 전체 악보 탐색 화면으로 이동한다. 이 화면에서는 검색 일치 패널·붉은 강조·감지 음표 재생을 숨긴다.
- 현재 약 8천 작품에는 별도 Elasticsearch 운영이 과도하므로 SQLite를 유지한다.
- 다음 `index:sqlite` 실행부터 `works_fts` FTS5 virtual table을 만들고 Unicode/diacritic-aware 전문 검색을 사용한다.
- 기존 SQLite 파일에는 FTS table이 없으므로 title/normalized title/composer/source의 case-insensitive LIKE 검색으로 자동 폴백한다.
- 데이터가 수십만~수백만 곡으로 증가하고 다중 서버, 형태소 분석, 복합 facet, typo tolerance가 필요해질 때 OpenSearch/Elasticsearch 이전을 재검토한다.
- 모바일에서는 검색 아이콘만 보이다가 focus 시 헤더 폭으로 확장한다.
- 검증: 카탈로그 검색·편성 중복 제거 테스트를 추가하여 Vitest 67개 통과, TypeScript/Vite production build 통과.
## 2026-08-31 — Tuplet 구현 상태 점검과 결과 악보 playhead 정렬

- Tuplet은 앞서 `N notes in the time of M`, QueryEvent 필드, effective duration 계산 원칙까지만 설계했으며 실제 입력 버튼·MEI 표기·검색 처리는 아직 구현되지 않았음을 확인했다.
- 구현 순서는 (1) 3:2/2:3/5:4/6:4/7:4 preset과 다중 음표 선택, (2) written/effective duration 분리, (3) MEI tuplet bracket/number, (4) 재생·Exact rhythm·복사 JSON 회귀 검증으로 유지한다.
- 검색 결과 playhead는 존재했지만 SVG 전체 음표 개수와 재생 event ordinal의 비율로 위치를 추정했다. 화음·쉼표·tie·반복음이 있으면 실제 음표와 대응하지 않는 것이 원인이었다.
- 원본 XML의 part/staff/voice/measure/beat/pitch로 각 재생 event에 `data-playback-index`를 부여하고, 재생기는 이 ID 순서의 정확한 SVG 음표로 이동하도록 수정했다.
- playhead를 3px로 굵게 하고 상단에 붉은 삼각형 포인터를 추가해 밝은 악보에서도 위치를 식별할 수 있게 했다.
- 가로 overflow가 있는 악보 조각은 현재 음표가 viewport 중앙에 오도록 기존 자동 스크롤을 유지한다.

### 구현 완료 및 재검증

- 문제 재현: playhead가 재생 시작 시의 SVG node 목록을 보관했기 때문에 Verovio/React 재렌더 뒤에는 제거된 node를 추적했다. `playbackNotes` 배열도 매 render마다 새로 생성되어 악보 재렌더를 반복시켰다.
- 해결: 재생 event 목록을 `useMemo`로 고정하고, 각 attack 시점마다 현재 DOM에서 정확한 `data-playback-index`를 다시 조회한다.
- 브라우저 검증: 첫 검색 결과에 playback marker 6개가 연결되었고, 재생 0.3초 후 playhead `left=373.545px`, 1.2초 후 `left=482.104px`로 실제 이동함을 확인했다.
- Tuplet 입력은 오선/음가 패널에서 연속 event를 2개 이상 선택하는 방식으로 구현했다. 같은 음가일 때는 선택 개수가 N이 되고, 혼합 음가일 때는 `표기 음가 합 ÷ 선택 구간의 최소 표기 음가`로 실제 subdivision 수 N을 계산한다. 기본 normal notes는 2개→3, 3개→2, 5개 이상→4이며 `in 2 / in 3 / in 4`에서 사용자가 합계를 바꿀 수 있다.
- QueryEvent에 `tupletGroup`, `actualNotes`, `normalNotes`, `writtenDuration`을 추가했다. `writtenDuration`은 악보에 보이는 음가, `durationRatio = writtenDuration × M/N`은 재생·검색에 쓰는 실제 시간이다.
- Verovio용 MEI에는 `<tuplet num="N" numbase="M">`를 생성하여 bracket/number를 표시하고, 내부 음표에는 effective duration이 아닌 written duration을 기록한다.
- 이미 묶인 Tuplet 전체를 다시 선택하면 `Remove tuplet`으로 해제할 수 있다. Tuplet 내부 음가 slider를 바꿀 때에도 N:M 비율을 보존한다.
- Query 사례 Q-07: 동일 음가 3개를 선택해 3:2 적용. 각 음표가 8분음표라면 JSON에는 `writtenDuration: 0.5`, `durationRatio: 0.333…`, `actualNotes: 3`, `normalNotes: 2`가 저장되어야 한다. 기존 문제는 Tuplet 버튼과 표기/재생 경로가 전혀 없었던 것이며, 위의 written/effective duration 분리로 해결했다.
- 검증: Vitest 68개 통과, TypeScript/Vite production build 통과. 실제 브라우저에서 3개 선택 시 `Tuplet 3:2` 활성화와 적용 후 각 음가 패널의 `· 3:2` 표시를 확인했다.

### Query 사례 Q-08 — 쉼표 및 혼합 음가 Tuplet

- 문제: 최초 구현의 활성화 조건이 `음표만`, `모두 같은 writtenDuration`으로 제한되어 있어 쉼표가 포함된 튜플릿과 `4분음표 + 8분음표` 같은 혼합 음가 튜플릿을 만들 수 없었다.
- 판단: Tuplet의 time modification은 그룹 안의 각 event에 동일한 `M/N` 비율을 적용하며, event가 음표인지 쉼표인지 또는 written duration이 서로 같은지는 성립 조건이 아니다.
- 해결: 연속된 event 2개 이상이라는 조건만 유지했다. 음표와 쉼표를 함께 선택할 수 있고 서로 다른 written duration도 허용한다.
- 예: 4분음표 + 8분음표를 선택하면 event는 2개지만 최소 단위인 8분음표 세 칸이므로 N을 3으로 추론해 `Tuplet 3:2`를 제안한다. 4분음표는 `1 × 2/3 = 0.666… beat`, 8분음표는 `0.5 × 2/3 = 0.333… beat`로 재생·검색된다. 합은 1 beat이며 악보에는 각각 4분음표와 8분음표로 유지된다.
- 회귀 테스트에 4분음표 + 8분음표 + 8분쉼표 혼합 그룹을 추가해 MEI 안에서 각각 `dur="4"`, `dur="8"`, `<rest dur="8">`로 보존되는지 확인했다. Vitest 69개와 production build가 통과했다.

## 2026-08-31 — 검색 결과 점수 축 재구성 및 모티프 중요도

- 사용자 의견: Pitch와 Interval은 조옮김 허용 검색에서 같은 선율 관계를 중복 설명하는 느낌이 강하다. Downbeat, Schenker 분석, 해당 음악에서의 반복·비중을 결과 근거로 표시하는 편이 낫다.
- UI 점수 축을 `Melody Interval`, `Rhythm`, `Downbeat Weight`, `Schenker-Informed`로 재구성했다. Pitch 점수는 회귀 분석과 내부 진단을 위해 응답에 보존하지만 일반 결과 카드에서는 숨긴다. 점수 항목은 Title Case를 적용한다. 일반 문장에서는 `Schenker-informed`가 자연스럽지만 UI 항목명에서는 `Schenker-Informed`로 표기한다.
- `Downbeat weight`는 Query의 meter와 후보 MusicXML의 실제 meter를 각각 사용해 중요 박 대응과 충돌을 계산한 `scores.meter`이다. 따라서 4/4의 1·3박 규칙을 다른 박자에 그대로 적용하지 않는다.
- `Schenker-informed`는 완전한 Schenker 분석을 주장하지 않는다. 강박, 지속음, tie, 프레이즈 경계, 음역상 돌출을 기둥음 근거로 사용하고 짧은 경과음·보조음은 낮춘 structural reduction 유사도다.
- 기존 `Occurrence importance`는 사실상 stream melody-role 값에 가까워 반복성을 충분히 설명하지 못했다. 새 `Motif importance`는 (1) 해당 파트의 melody-role 50%, (2) 같은 interval motif의 반복 횟수 35%, (3) 반복 구간이 전체 파트에서 차지하는 비중 15%를 결합한다.
- 완전 interval 일치는 전 구간 occurrence를 세고, 유사 결과는 n-gram retrieval에서 독립적으로 검출된 후보 시작점 수를 근사 반복 횟수로 사용한다. 결과의 Why 항목에는 추정 반복 횟수와 중요도 점수를 함께 표시한다.
- 이 중요도는 현재 설명용 보조 점수이며 local melodic similarity를 덮어쓰지 않는다. 반복이 많다는 이유만으로 덜 닮은 결과가 상위에 오는 것을 방지하기 위한 결정이다.

## 2026-09-01 — 카탈로그 다중 단어 AND 검색

- 문제 사례: `I christmas`처럼 서로 떨어진 두 단어를 입력하면 FTS가 없는 기존 SQLite fallback에서 전체 문자열을 연속 구문으로 검색하여 결과가 0개였다.
- 검색어를 Unicode 단어 token으로 분리하고 모든 token을 포함해야 하는 AND 검색으로 변경했다. 단어 순서와 두 단어 사이의 거리는 제한하지 않는다.
- 한 글자 `I`를 단순 `%i%` 또는 prefix로 처리하면 `White Christmas`, `Christmas In Our Hearts`도 잘못 통과하므로, SQL 후보를 가져온 뒤 제목을 Unicode 단어 단위로 다시 나눈다. 한 글자 검색어는 완전한 단어 일치, 두 글자 이상은 단어 prefix 일치로 검증한다.
- 따라서 `ALL I WANT FOR CHRISTMAS IS YOU`, `I'LL BE HOME FOR CHRISTMAS`는 검색되지만 `White Christmas`는 `I christmas` 결과에서 제외된다.
- 제목에서 결과가 없을 때만 작곡가·원본 파일명 등 metadata 전체의 token AND 검색으로 fallback한다.

## 2026-09-01 — 악보 상세 화면 제목·스크롤·분석 명칭

- 상세 화면 sticky toolbar에 `TITLE` eyebrow와 실제 작품 제목을 추가했다. MusicXML 내부 credit/title은 계속 제거하므로 악보 본문과 중복되지 않는다.
- `Melody analysis`는 선율 이외의 리듬·모티프·밀도 통계도 포함하므로 `Analysis and Statistics`로 변경했다.
- 기존 자동 스크롤은 `scrollIntoView(start)` 후 고정값 115px을 다시 빼는 두 단계 동작이라 화면이 튀었고, sticky 검색 악보 조각이 본문을 가리는 문제가 있었다.
- 검색 악보 조각의 sticky를 해제하고 문서 흐름에 두었다. 자동 이동은 목표 음표의 현재 좌표에서 viewport 높이의 20%(최소 110px)를 한 번에 계산해 즉시 배치한다.
- 검색 악보 조각을 클릭한 수동 이동은 같은 위치 계산을 사용하되 smooth behavior를 적용한다. 초기 로드 애니메이션과 사용자의 이후 스크롤을 방해하는 반복 보정은 사용하지 않는다.

## 2026-09-01 — 상세 악보 최초 1회 스크롤과 Trepak/내성부 검색

- Query 사례 Q-09: `G4 G4 F#4 G4 G4 E4 D4 C4 E4 D4 D4 C#4`, 음가 `.5 .25 .25 .5 .5 .5 .5 .5 .5 .5 1 1`, Melody + Rhythm, 4/4.
- 원본 인덱스에서 Trepak은 이 11개 interval을 피아노판 6회, 바이올린판 6회 등 여러 위치에 정확히 포함한다. 원 악보의 마지막 두 D–C# 음가는 각각 .25지만 Query는 1이므로 Rhythm은 약 83점이며 완전 rhythm match는 아니다.
- 누락 원인은 결과 threshold가 아니라 refinement 전 후보 절단이었다. 기존에는 동일 작품의 반복 위치도 각각 상위 350개 슬롯을 사용해 다른 작품을 밀어냈다.
- 후보를 work/stream별 최대 3곳으로 제한하고 첫 번째 후보를 모든 stream에 우선 배분한 뒤 두 번째·세 번째 후보를 추가하는 다양화 방식을 적용했다.
- 다중 stream 인덱스 확장 뒤에는 후보가 26,000개 stream으로 늘어났다. 긴 정확 interval 근거가 단순 contour/rhythm 반복보다 먼저 refinement되도록 interval n-gram retrieval evidence에 3배 가중치를 적용하고, 같은 시작점에서 Query의 모든 interval 3-gram이 확인된 후보는 refinement 우선 큐에 넣는다. 특정 제목이나 Query를 고정하지 않는다.
- 흔한 3-interval gram은 token당 3,000행 조회 제한을 넘겨 뒤쪽 stream을 누락할 수 있다. 제한을 크게 늘려 검색 시간을 악화시키는 대신 5-interval gram(`i5`)을 인덱스에 추가하고 긴 Query 후보 생성에서 6배 retrieval evidence로 사용한다.
- 후보 refinement 상한은 8음 이상 Query 900개, 짧은 Query 350개로 구분한다. 긴 동기의 recall을 보존하면서 4음 Query가 다중 stream 26,000개 환경에서 과도하게 느려지는 것을 막는다.
- MusicXML 파서는 원래 `(part, staff, voice)`별 stream을 만들었지만 JSON에서는 역할 상위 4개만 보존하고 SQLite builder는 첫 stream만 색인했다. 파서의 4개 제한을 제거하고 SQLite가 보존된 모든 stream을 고유 ID로 색인하도록 수정했다.
- 기존 v2 JSON에서 보존된 stream들을 즉시 재색인해 SQLite가 약 8천 대표 stream에서 26,000 melody stream으로 확장됐다. 기존 `search.sqlite`는 `search.sqlite.pre-multistream`으로 보존했다. 아직 JSON에서 잘렸던 5번째 이하 stream은 다음 전체 MusicXML 재파싱 때 추가된다.
- 상세 악보의 자동 위치 이동은 `streamId:start:end` key별 최초 한 번만 허용한다. Verovio pages가 다시 생성되거나 parent가 재렌더되어도 같은 상세 페이지에서는 사용자의 수동 스크롤을 되돌리지 않는다.
- 같은 작품/stream에서 실제 검출된 surface 선율과 리듬이 완전히 같은 반복은 카드 여러 장으로 만들지 않고 최고 위치 카드 하나에 `동일 선율·리듬 N회 · 마디 …`로 표시한다. Query와 rhythm이 일부 달라도 후보 악보 안에서 서로 같은 반복은 세며, 변형 반복은 이 목록에 섞지 않는다.
- 각 part/staff/voice의 melody-role을 최종 ranking에 최대 12점 범위의 감점으로 반영한다. 내성부·반주 voice는 검색 대상에서 제거하지 않되 대표 선율보다 아래에 정렬한다.
- 같은 MusicXML source의 여러 파트에서 검출 구간의 실제 interval+normalized rhythm signature가 같으면 가장 melody-role이 높은 파트 한 장을 대표 카드로 사용한다. 카드 안에 파트별 순번, 파트 이름, 동일 등장 횟수, 마디 목록을 표시한다.
- Query에 대한 유사도만 같고 실제 검출 surface melody/rhythm이 다른 variation은 같은 파트 목록으로 합치지 않는다.
## 2026-09-01 한국어 MusicXML 제목 인코딩 복구

- 사례: `work-446c05b114906da2`의 상세 화면 제목이 `³» ÁÖ¸¦ °¡±îÀÌ ÇÏ°Ô ÇÔÀº`로 표시되었다.
- 원인: 실제 CP949/EUC-KR 한국어 바이트가 원본 XML의 문자 인코딩 처리 과정에서 Latin-1 문자로 해석된 뒤 검색 인덱스에 저장되었다. 폰트나 React 렌더링 문제는 아니다.
- 확인: 해당 문자열을 CP949로 복구하면 `내 주를 가까이 하게 함은`이다.
- 해결: 인덱서가 제목, movement title, 작곡가, 파트 이름을 읽을 때 Latin-1→CP949 변환 결과에서 한글 문자가 실제로 증가하는 경우에만 복구한다. 프랑스어·독일어 등 정상적인 Latin 문자는 변환하지 않는다.
- 기존 인덱스를 전부 다시 만들기 전에도 상세 화면, 검색 결과, 텍스트 검색 결과, YouTube 제목 정규화에서 같은 안전 검사를 수행해 올바른 제목을 즉시 표시한다. 다음 전체 재인덱싱부터는 저장 데이터 자체도 올바르게 생성된다.
- 후속 보완: 향후 일본어와 중국어 간체·번체 자료를 위해 복구 후보를 UTF-8, CP949/EUC-KR, Shift_JIS, GB18030, Big5로 확대했다. 이미 올바른 Unicode 문자열은 바이트 재해석 대상에서 제외하고, 복구 결과에 실제 한글·가나·한자가 증가할 때만 채택한다.
- 회귀 사례로 한국어 `내 주를 가까이 하게 함은`, 일본어 `日本語タイトル`, 중국어 간체 `简体中文标题`, 중국어 번체 `繁體中文標題`, 정상 유럽어 `Prélude in C♯ minor`를 검증한다.

## 2026-09-01 Trepak 긴 Query의 한 음 변화와 후보 recall

- Query 사례 Q-10: `G4 G4 F#4 G4 G4 E4 D4 C4 E4 D4 D4 C#4 D4 A3`, 음가 `.5 .25 .25 .5 .5 .5 .5 .5 .5 .25 .5 1 1 1`, Melody + Rhythm, 4/4.
- 문제: Trepak 원본과 직접 local alignment하면 전조된 선율의 앞부분이 연속 일치하고 전체 유사도가 약 90점인데도 검색 결과에서 완전히 사라졌다.
- 진단: Trepak은 retrieval 후보에는 포함되어 있었다. Melody Interval 94.6, contour 92.3, rhythm DTW 47.2, 리듬까지 반영한 local score 78.6이었지만, 기존 admission의 rhythm 최소 55 조건 때문에 refinement 뒤에서 제거되었다. Query 뒤쪽 음가가 원본과 여러 곳 달라 “음 하나의 pitch 차이”보다 rhythm 차이가 크게 계산된 사례다.
- 해결: interval gram 완전 일치 보너스가 한 음 변화로 갑자기 사라지지 않도록 높은 gram coverage에 연속적인 후보 보너스를 주었다. 또한 8음 이상이며 interval 90 이상·contour 85 이상인 강한 긴 선율은 rhythm factor의 하한을 0.78로 둔다. rhythm 차이는 약 90점의 melodic local alignment를 약 71점까지 낮추지만 기존처럼 약 45점으로 반감해 탈락시키지는 않는다. 최종 admission은 local 68 이상, rhythm 40 이상을 요구하므로 exact match로 취급하지 않는다.

### Query 사례 Q-11: Rhythm이 약한 강한 Trepak 선율

- Query: Q-10 뒤에 `B3` 온음표를 추가하고 앞부분의 두 `D4`를 각각 8분음표로 입력한 15음 Query.
- 비교 결과 `She's Always a Woman` 52–53마디는 Melody Interval 85.0, contour 78.6, rhythm 66.1이었고, Trepak은 Melody Interval 96.8, contour 92.3, rhythm 41.8이었다.
- 기존 곱셈식에서는 rhythm 66.1이 전자의 낮은 멜로디 점수를 유지시키고 rhythm 41.8이 Trepak의 강한 멜로디를 과도하게 압축해 순서가 뒤집혔다.
- Melody + Rhythm 정렬 비용을 선율 92%(interval 48%, direction 30%, step/leap 14%)와 rhythm 8%로 변경했다. 정렬 후에는 local melodic alignment 88%와 Rhythm DTW 12%를 가산 결합한다. 리듬 완전 일치는 이점을 주지만 중간 수준의 리듬 점수가 약한 멜로디를 과도하게 구제하지 못한다.
- 8음 이상 강한 선율 예외의 rhythm 하한은 35로 조정하되 interval 90, contour 85, local 68 조건을 유지한다.

### Query 사례 Q-12: 가운데 한 음의 반음 변경

- 원본 Query: `F4 A4 C5 E5 G5`, 8분쉼표, `G5 C5 A4 A4 C5`; 변경 Query는 두 번째 G5만 G#5로 올렸다.
- 원본 결과의 가장 강한 melodic evidence는 `I Loves You, Porgy`로 Pitch 93.0, Melody Interval 87.6, Contour 88.9였다. 기존 1위 `Blue Christmas`는 Pitch 74.0, Melody Interval 79.8이지만 Rhythm 91점 때문에 위에 올라 멜로디 우선 정책과 맞지 않았다.
- 한 음의 pitch substitution은 앞뒤 interval 두 개를 바꾸며, 겹치는 interval 3-gram과 5-gram 여러 개를 동시에 파괴한다. 변경 전후 한쪽에 남은 5-interval 연속 일치는 6개 음의 전조 동형을 뜻하므로 강한 retrieval 근거다.
- interval 5-gram retrieval 가중치를 6에서 50으로 높여 가운데 한 음이 달라도 양쪽의 긴 정확 조각으로 원곡 후보가 refinement에 진입하도록 했다. 최종 local alignment에서는 바뀐 음과 두 interval의 불일치가 정상적으로 감점된다.
- 추가 진단: `I Loves You, Porgy` 전체 stream에 직접 정렬하면 원본은 Pitch 98, Interval 93.8, Rhythm 100이고 변경 Query도 Pitch 97, Interval 90.7, Rhythm 100이었다. 그런데 정확한 구간은 stream 뒤쪽에 있으며, 작품별 시작점 상위 3개 제한 때문에 앞쪽의 반복 n-gram 시작점만 refinement되고 진짜 구간은 평가되지 않았다.
- 8음 이상 Query는 작품별 시작점 후보를 3개에서 8개로, 전체 refinement 후보를 900개에서 1,400개로 확대했다. 작품을 결과에 여러 번 표시하려는 변경이 아니라, 내부적으로 여러 시작점을 비교한 뒤 가장 좋은 구간 하나를 선택하기 위한 recall 보완이다.
- 작품별 30개·전체 3,000개 시작점 확장도 실험했으나 정확 구간은 복구하지 못하고 약 24초가 걸려 폐기했다. 문제 구간을 구성하는 정확 n-gram 자체가 SQL 조회 제한에서 seed가 되지 않으면 시작점 개수만 늘려도 해결되지 않는다.
- 최종 방식은 n-gram evidence를 작품별로 합산해 상위 160개 melody stream을 고른 뒤, 각 stream 전체에 semi-global local alignment를 한 번 수행하는 2단계 refinement다. 나머지 작품에는 기존의 제한된 시작점 정렬을 유지한다. 이 방식은 한 음 변화로 정확 seed가 사라져도 작품 수준 근거와 전체 정렬을 결합해 실제 구간을 복구한다.
## 2026-09-01 Query 선택 음표 반음 이동 버튼

- 음가 조정 카드 왼쪽의 빈 공간에 위·아래 화살표를 세로로 배치했다. 오선이나 음가 카드에서 음표를 선택한 뒤 위 화살표는 +1 semitone, 아래 화살표는 -1 semitone을 적용한다.
- 여러 음표를 선택하면 모두 같은 간격으로 이동하며 쉼표는 바뀌지 않는다. tie 음표 중 하나를 선택하면 tie의 음정 동일성을 보존하기 위해 같은 tie group 전체를 함께 이동한다.
- 기존 flat 표기 음표는 이동 후에도 flat 선호를 보존하며, natural 음에서 검은 건반으로 이동할 때는 Query 건반의 현재 sharp/flat 설정을 따른다. 변경은 Undo/Redo history와 오선, 재생, 검색 Query에 즉시 반영된다.
## 2026-09-01 Search Evaluation Harness 진행 원칙

- 앞으로 개발의 중심을 제안된 검색 개선 과제와 사용자가 실행하는 실제 Query 사례로 전환한다.
- 특정 사례에 결과를 하드코딩하지 않고 Query, 기대 작품·구간, 문제 유형, 수정 전후 순위와 점수, 해결 방법을 구조화된 evaluation case로 누적한다.
- 구현 계획은 `docs/search-evaluation-harness-plan.md`에 정리했다. Phase 1은 JSONL case schema, 실제 production 검색 CLI, Recall@K·MRR·latency report, 기존 Query 사례 이관으로 구성한다.
- 정답을 사용자가 나중에 알려 주려는 사례는 먼저 `draft`로 저장하고 검색기의 독립적인 추론을 기록한 뒤, 정답 확인 후 `verified`로 승격한다.
- 이후 검색 가중치·threshold·retrieval 변경은 단일 Query 성공만으로 채택하지 않고 전체 verified suite의 정확도와 latency 회귀를 함께 확인한다.
## 2026-09-02 Harness 1단계 사용자 Query 검증 라운드

- 지금부터 사용자가 수행하는 여러 검색 테스트를 Phase 1 Harness의 평가 사례로 수집한다.
- 저장 위치는 `evaluation/cases/user-queries-phase1.jsonl`이며 기록 규칙은 같은 폴더의 `README.md`에 명시했다.
- 각 사례에는 Query 원문, 문제 설명, 정답 공개 전 시스템 예측, 확인된 정답 작품·파트·구간, 수정 전후 순위·세부 점수·latency, 원인, 일반화된 해결 방법, 전체 suite 회귀 결과를 보존한다.
- 정답 미확인 사례는 `draft`, 사용자 확인이 끝난 사례는 `verified`, 전체 평가 회귀까지 통과한 사례만 `resolved`로 구분한다.
- 동일 Query를 수정해 다시 실행하는 경우 기존 사례를 덮어쓰지 않고 variant 또는 후속 run으로 연결해 변화 과정을 남긴다.
## 2026-09-02 Phase 1 사례 Q-P1-001 — 내부 음 변경과 interval 이중 영향

- Query 원문과 baseline을 `evaluation/cases/user-queries-phase1.jsonl`에 `Q-P1-001`로 기록했다.
- 기대 결과는 사용자가 명시한 `I Loves You, Porgy`다. 현재 검색은 71개 결과, 약 20.5초, 목표 결과 없음, 1위 `Wet Hands`였다.
- 목표 stream 직접 정렬은 melodic alignment 92, Pitch 98, Melody Interval 93.8로 강하므로 최종 유사도보다 candidate/full-stream refinement 선택 실패가 직접 원인이다.
- 작품별 full-scan 우선순위를 모든 시작점 evidence 합계로 계산하면 반복 패턴이 많은 긴 stream이 과도하게 유리하다. 작품별 최강 시작점 evidence의 최댓값으로 변경해 실제 motif 근거를 우선한다.
- 후속 검증에서 여전히 recall이 부족하면 interval 4-gram 색인을 추가한다. 최종 Melody Interval은 인접 edge 오차와 중앙값 전조 제거 후 note-wise pitch residual을 결합해 한 음 변화가 두 edge에서 중복 벌점되는 문제를 줄일 예정이다.
- 작품 evidence 합계를 최강 시작점의 최댓값으로 바꾸자 Q-P1-001 latency는 약 20.5초에서 4.3초로 감소했지만 목표 recall은 아직 실패했다.
- 종합 evidence 상위 100개뿐 아니라 interval evidence 상위 80개와 rhythm evidence 상위 60개 stream의 합집합을 full-stream refinement 대상으로 사용한다. Rhythm은 이 단계에서 최종 점수 보너스가 아니라 후보 recall 채널로만 사용된다.
- Feature별 후보 분리만으로도 Q-P1-001은 복구되지 않았다. 목표 작품에 query prefix의 interval 3-gram `[4,3,4]`와 `[3,4,3]`이 각각 12회 있지만 corpus 전체 빈도는 1,864회와 2,795회여서 개별 seed의 식별력이 낮았다.
- 인접한 interval 3-gram 두 개가 동일한 `(workId,start)`에서 만나는 교집합에 20점 evidence를 주는 interval 4-gram equivalent seed를 추가했다. SQLite 재색인 없이 기존 index로 5개 연속 음의 전조 동형을 식별하며, 한두 개의 내부 pitch 변경으로 모든 5-gram이 파괴되는 경우를 보완한다.
- 4-interval seed를 일반 interval evidence에만 합치면 흔한 3-gram 후보에 다시 묻혔다. 별도의 작품 evidence 채널을 만들고 동일 작품 내 4-interval seed occurrence를 누적해 상위 60개 stream을 full scan 합집합에 추가한다.
- 목표 작품은 full scan 대상이며 시작점 0·102·200이 모두 evidence 172였지만, breadth-first 다양화가 1,400개 작품의 첫 후보만 채우면서 작품별 두 번째 이후 시작점이 실제 refinement에 들어가지 않는 결함이 있었다.
- Full-scan 합집합에 든 작품은 evidence 상위 시작점 4개를 `deepSeedCandidates`로 별도 보존한다. 전체 stream alignment가 선택한 melodic 반복과 각 seed의 rhythm·metric 문맥을 함께 비교해 같은 작품에서 더 적합한 occurrence를 선택한다.
### Q-P1-001 후속 — interval 중복 벌점과 보조 점수 상한

- Deep seed 적용 후 `I Loves You, Porgy` 22–24마디가 2위로 복구됐다. Pitch 98, Interval 93.8, Rhythm 100, latency 약 5.2초였다.
- 당시 1위 `Misty`는 Pitch 65, Rhythm 49인데 Downbeat 79와 structural 92가 과도하게 보상했다. 목표 곡은 metric score 15에서 -14를 받아 멜로디 우선 원칙과 맞지 않았다.
- Melody Interval을 adjacent edge interval 60%와 median-transposition 제거 후 note-wise residual 40%로 결합한다. 한 pitch 오차가 두 interval edge에 영향을 주더라도 note residual에서는 한 번만 벌점된다.
- Local melodic alignment도 기존 DP similarity 70%와 robust Melody Interval 30%로 결합한다. Downbeat adjustment는 -5~+4, structural bonus는 최대 10으로 제한해 보조 분석이 강한 멜로디·리듬 증거를 뒤집지 못하게 했다.
- 최종 Q-P1-001 결과는 `I Loves You, Porgy` 22–24마디 1위, Pitch 97.2, robust Interval 95.1, Rhythm 100, local 88.5, ranking 92.2다. 동일 프로세스 내 측정 latency는 5.3초와 2.8초로 변동했다.
- Smoke regression에서 Trepak 15음 Query와 이전 Porgy G# Query도 각각 1위를 유지했다. 다만 latency는 Trepak 22.2초, G# 사례 8.3초로 편차가 커 Phase 1 성능 계측의 우선 과제로 남긴다.
- Vitest 8개 파일, 76개 테스트가 통과했다.

## 2026-09-02 Q-P1-001-V2 — 두 개의 큰 음높이 변경에 대한 견고성 확인

- 직전 검증 변형을 기준으로 내부 두 음을 크게 바꿨다: A4→E4(-5반음), G4→D♭4(-6반음).
- `I LOVES YOU, PORGY`는 22–24마디 결과로 4위에 남았다. 1–3위가 같은 제목의 판본 중복이므로 고유 제목 기준으로는 사실상 2위다.
- 벌점은 분명하게 적용되었다. Pitch는 97.2→82.7, Melody Interval은 95.1→73.9, local similarity는 88.5→66.4, ranking은 92.2→70.0으로 내려갔다. Rhythm은 94.2로 비교적 높게 유지되었다.
- 따라서 두 개의 큰 오음 때문에 목표가 완전히 소실되지는 않으면서도 순위와 멜로디 점수가 충분히 내려가는 방향은 긍정적이다. 다만 한 사례만으로 일반 성능을 입증할 수 없으므로 무관한 음형의 negative control과 1·2·3·4음 변경 sweep을 추가해야 한다.
- 검색 latency는 8.7초로 여전히 Phase 1 성능 개선 대상이다.

## 2026-09-03 PDMX classical 검색 코퍼스 통합

- `K:\PDMX.csv`와 `K:\mxl`을 대조해 `classical`, `subset:all_valid=True`, `subset:deduplicated=True`인 49,625작품을 선택했다. 누락 MXL은 0건이다.
- K 드라이브 여유 공간은 62.18GB, U 드라이브는 184.65GB였다. 빌드 중간 산출물과 XML 캐시는 `U:\MusicSearch-PDMX`에 만들고 최종 SQLite만 K에 배치했다.
- `scripts/build-pdmx-inventory.py`를 추가해 해시형 MXL 경로와 song name, title, composer, genre, license 및 PDMX metadata를 연결했다.
- MusicXML 인덱서가 PDMX 메타데이터를 보존하고 화면 제목은 `song_name → title → XML title`, 작곡가는 `composer_name → artist_name → XML composer` 순서로 선택하게 했다.
- 500작품 pilot은 실패 0건, 2,135 melody stream, 269,600음, SQLite 89.64MB였다.
- 단일 프로세스 파싱은 약 16 files/s까지 내려갔으나 8-worker ProcessPool을 추가해 평균 82.9 files/s로 개선했다. 전체 49,625작품 파싱은 실패 0건으로 완료되었다.
- 전체 PDMX v2는 198,137 melody stream, 26,588,886음, 2.061GB JSONL이다. 기존 8,111작품과 병합한 결과는 57,736작품이며 work hash 중복은 0건이다.
- SQLite builder는 입력·출력 CLI 경로를 받고, gram index를 모든 행 입력 뒤 일괄 생성하도록 변경했다. 통합 DB는 224,353 melody stream, 11.391GB다.
- 같은 Q-P1-001 Query A/B에서 기존 DB는 cold 11.40초/warm 1.93초, 통합 DB는 cold 4.52초/warm 2.10초였다. 데이터가 약 7.1배 늘었지만 warm latency 증가는 약 9%였다.
- MXL 상세 악보를 위해 `scripts/extract-pdmx-musicxml.py`로 49,625개 XML 캐시(14.889GB)를 U에 생성했다. 실패는 0건이며 서버는 `.mxl` source를 자동으로 XML 캐시에 연결한다.
- Unicode line separator가 JSONL reader에서 행 경계로 오인되는 문제를 수정해 ASCII LF만 레코드 경계로 처리한다. 한국어·일본어·중국어 간체·번체 metadata 복구 테스트를 포함해 Vitest 76개와 production build가 통과했다.
- 기존 DB는 `data/search-index-v2/search.sqlite.pre-pdmx`로 보존하고 통합 DB를 기본 `search.sqlite`로 전환했다. PDMX 제목 검색, 작곡가 표시, 전체 XML 상세 로딩을 검증했다.

## 2026-09-03 PDMX 통합 후 결과 수와 cold latency 개선

- 검색 API와 화면 요청의 결과 상한을 20개에서 100개로 늘렸다. admission 기준을 통과한 결과가 적으면 일정 수를 억지로 채우지 않고 실제 통과 결과만 반환한다.
- 100개 결과 자체의 추가 비용은 작았지만 첫 검색이 약 21초까지 늘어나는 현상을 확인했다. 주원인은 초기 후보 약 1,400개에서 local alignment 전에 원본 XML을 반복해서 열어 박자를 읽는 순서였다.
- 1차 정렬은 Query 박자로 수행하고 local alignment의 coverage·sparse 조건을 통과한 후보에만 원본 박자를 읽도록 순서를 변경했다. 최종 metrical score와 결과 표시는 여전히 원본 박자를 사용한다.
- 원본 XML에는 64개 LRU cache를 추가하고 SQLite에는 256MB page cache와 4GB memory map을 설정했다.
- Q-P1-001, 100개 결과 기준 cold latency는 21.06초에서 5.36초로 약 74.5% 감소했고 warm latency는 2.64초에서 2.30초로 줄었다. `I LOVES YOU, PORGY` 1위는 유지됐다.
- 대규모 stream 중복 때문에 `I christmas` 텍스트 검색 후보가 한 작품의 여러 파트로 채워지는 문제를 발견해 FTS pre-dedup 후보 폭을 확대했다.
- Vitest 76개와 production build가 통과했으며 localhost:5173 서버를 재시작했다.

## 2026-09-03 반복 마디 번호가 있는 PDMX 악보 조각 축소 오류

- 사례: `work-bd980e8b68c3e32f`, Etude op.849, 검색 표시 마디 13–15.
- 이 MXL은 여러 연습곡이 한 part에 연속 수록되어 총 1,253마디이며, 각 곡에서 마디 번호가 다시 1부터 시작한다.
- 기존 excerpt 추출은 XML의 인쇄 마디 번호가 13–15인 마디를 전부 선택해 75마디·1,642음표를 한 조각에 넣었다. 그 결과 전체 악보처럼 극단적으로 축소되었다.
- 검색 인덱스의 절대 XML 마디 순번을 `measureOrdinal`로 표시 번호와 별도 보존했다. excerpt 추출과 음표 강조·재생 위치 매칭은 ordinal을 우선하고, 일반 악보에서는 기존 표시 마디 번호를 fallback으로 사용한다.
- 수정 후 해당 조각은 실제 검색된 절대 13–15번째 마디 3개·60음표만 포함한다. 반복 마디 번호 배열에서 ordinal 13–15만 선택하는 회귀 테스트를 추가했다.
- Vitest 9개 파일·77개 테스트와 production build가 통과했다.

## 2026-09-03 KYSing 매칭 코퍼스와 특정 파트 제한 미리보기

- API 메타데이터와 직접 연결된 KYSing XML 37,826개를 `research-preview` 인벤토리로 만들었다. 원본 XML은 `U:\KYSing_MusicXML`에 변경 없이 유지한다.
- 인덱스 source ID에는 `kysing/` 접두사를 붙여 기존 Music Analysis 및 PDMX 파일명과 충돌하지 않게 했다. 제목·가수·작곡가·작사가·금영 번호·등록일과 메타데이터 출처를 별도 보존한다.
- 검색 결과와 상세 화면은 검색된 `part + staff + voice`가 속한 part 하나만 사용한다. 다른 악기 part는 CSS로 가리지 않고 서버가 만드는 MusicXML 응답에서 제거한다.
- 제한 상세 화면은 일치 구간 전후 2마디만 포함한다. 첫 마디에 필요한 divisions·조표·박자·음자리표 attributes는 앞선 마디에서 복원한다. 검색 구간이 없는 카탈로그 직접 접근에는 XML을 제공하지 않는다.
- `restrictedPreviewXml` 회귀 테스트는 다중 파트 원본에서 목표 part만 남고 다른 score-part/part가 제거되며 제한된 6마디와 유효 attributes만 반환되는지 검사한다.
- 공식 금영 미매칭 백필 도구는 기본 하루 100건, 1.5초 간격으로 동작하고 매 10건마다 결과와 cursor를 저장한다. 5곡 pilot에서 5곡 모두 복구했으며 중단 후 재개 상태를 확인했다.

## 2026-09-03 금영 곡목 메타데이터 스냅샷

- Manana 기본 금영 endpoint는 전체 목록이 아니라 최신 20곡만 반환하며 `page` 인자를 처리하지 않았다.
- 곡번호 endpoint가 부분 일치 결과를 반환하는 성질을 이용해 숫자 1–9를 각각 한 번 조회하고 곡번호로 중복 제거했다. 총 45,758개의 금영 곡목을 확보했다.
- 원본 스냅샷은 `data/kysing-metadata/kumyoung-2026-09-03-all.json`, 검증 결과는 `data/kysing-metadata/kumyoung-2026-09-03-report.json`에 저장했다. 재현용 스크립트는 `scripts/download-kysing-metadata.mjs`이다.
- KYSing XML 50,874개 중 37,826개(74.35%)가 파일명의 선행 0을 제거한 금영 곡번호와 직접 일치했다. 13,048개는 Manana 목록에 없었다.
- 누락 표본 114, 120, 121, 122번은 금영 공식 검색에서는 각각 정상적으로 제목과 가수가 확인되었다. 따라서 번호 체계 불일치가 아니라 비공식 목록의 과거곡 누락으로 판단한다.
- 공식 사이트 누락 보완은 13,048건을 한꺼번에 요청하지 않는다. 공식 데이터 제공 가능 여부를 우선 확인하고, 필요할 경우 요청 간격·재시작 가능한 캐시·일일 상한을 둔 별도 백필 작업으로 수행한다.

## 2026-09-03 악보 조각 재생 지연과 KYSing 제한 공개 준비

- 악보 조각 재생이 잠시 밀린 뒤 빠르게 몰려 나오는 현상은 각 음의 `setTimeout` 콜백 안에서 `AudioContext`를 새로 만들던 구조와 대형 Verovio 렌더링의 메인 스레드 점유가 결합한 문제였다.
- 한 번의 사용자 재생 동작에서 AudioContext 하나를 만들고 모든 attack/release를 Web Audio 자체 시계에 미리 예약하도록 변경했다. 재생 위치 표시는 DOM 타이머를 계속 사용하지만, 화면 렌더링 지연이 소리의 박자까지 밀어내지는 않는다.
- `U:\KYSing_MusicXML`에는 XML 50,874개, 약 42.35GB가 있다. K 드라이브 여유 공간은 약 60.5GB, U 드라이브는 약 96.9GB이다.
- KYSing 원본은 `research-preview`로 분류한다. 검색 인덱스에는 특징량과 검색용 단선율을 넣되, 상세 API가 전체 XML을 브라우저로 보내서는 안 된다.
- 공개 조각은 검색된 part/staff/voice와 일치 구간 주변의 제한된 마디만 서버에서 새 MusicXML로 구성한다. 다른 파트와 범위 밖 마디는 CSS 마스킹이 아니라 응답 데이터에서 제거하여 개발자 도구로 복구할 수 없게 한다.
- 상세 화면도 전체 악보 대신 동일한 제한 조각과 분석 통계만 제공하며, 임의 마디 탐색·원본 다운로드·연속 구간 조합은 허용하지 않는다. 구체적인 공개 마디 수와 재생 길이는 권리 검토 후 설정한다.
- 표본 XML에는 작품 제목·작곡가가 없고 숫자 파일명과 파트 정보만 있어, 유용한 검색 결과 표시를 위해 별도의 노래 번호–제목–작곡가 메타데이터 매핑이 필요하다.
- Vitest 9개 파일·77개 테스트와 production build가 통과했다.

## 2026-09-03 악보 조각 템포 중복 및 대용량 전체 악보 빈 화면

- 사례: PDMX 검색 결과의 악보 조각에 같은 템포 표시가 반복되고, 상세 화면의 전체 악보는 그려지지 않았다.
- 원인: 조각 생성 시 MusicXML의 중복 metronome/sound tempo 지시를 모두 유지했고, 전체 악보는 Verovio의 모든 페이지 SVG를 동기적으로 만든 뒤에야 React 화면에 한꺼번에 반영했다.
- 일반화 수정: 악보 조각에서 연속된 동일 템포 지시만 제거한다. 실제 템포 변화와 템포 이외의 direction은 그대로 유지한다.
- 대용량 전체 악보는 두 페이지 단위로 화면에 점진적으로 반영하고 페이지 사이에 브라우저 렌더링 시간을 양보한다. 수백 페이지짜리 합본 XML도 전부 끝날 때까지 빈 화면으로 남지 않는다.
- 점진 렌더링 중 목표 페이지가 아직 없을 때 자동 스크롤 완료로 잘못 기록하지 않도록 수정했다. 목표 음표가 실제 DOM에 나타난 뒤 최초 한 번만 이동한다.
- Vitest 9개 파일·77개 테스트와 production build가 통과했다.
## 2026-09-03 — 금영(KYSing) 매칭 데이터 반영과 제한 악보 공개

- 원본 보존 위치: `U:\KYSing_MusicXML` (50,874 XML, 약 42.35GB). 원본 파일은 수정·이동·삭제하지 않는다.
- 확보한 금영 메타데이터 45,758곡과 파일명을 대조해 37,826개 파일(74.35%)을 1차 매칭했다. 파싱 실패는 0건이었다.
- 기존 데이터와 합칠 때 중복 레코드 3,623개를 제거했다. 최종 통합 JSONL은 45,914개 고유 작품이며, 검색 DB는 약 18.9GB다.
- 금영 데이터는 `metadata.accessPolicy = "research-preview"`로 저장한다. 서버는 `kysing/` 소스를 `U:\KYSing_MusicXML`에서만 읽는다.
- 검색 결과/상세 화면의 악보는 매치된 `streamId`의 part 하나만 남기고, 일치 구간 앞뒤 2개 ordinal measure만 포함한다. 필요한 이전 `attributes`(조표·박자·음자리표 등)는 첫 표시 마디에 이식한다.
- 검색 구간이 없는 금영 상세 요청에는 XML을 반환하지 않는다. 결과 응답에는 `accessPolicy: "research-preview"`, `fullScoreAvailable: false`를 표시한다.
- 빈 `targets` 문자열이 `Number('') === 0` 때문에 유효 onset처럼 해석되던 오류를 수정했다.
- 실제 샘플 검증: 무구간 XML 길이 0, 제한 미리보기 part 1개, score-part 1개, 주변 measure 4개.
- 새 DB 기준 단순 4음 melody 검색(20개 제한): cold 약 2.1초, warm 약 0.43초/0.34초. 후보 생성은 n-gram 인덱스를 사용하지만 대규모 데이터에서 cold latency 추가 개선이 필요하다.
- 기존 DB는 `data/search-index-v2/search.sqlite.pre-kysing`으로 보존했다.
- 검증: Vitest 9 files / 78 tests 통과, TypeScript 및 Vite production build 통과.

## 2026-09-03 통합 DB 복구 및 KYSing 미리보기 범위 수정

- KYSing 병합 때 기준으로 사용한 중간 JSONL에는 8,111개 작품만 남아 있어, 전체 PDMX DB에 있던 `Invention in C major BWV 772`를 포함한 다수 작품이 검색 대상에서 누락된 것을 확인했다.
- 전체 PDMX DB와 KYSing DB를 stable stream ID로 합친 28.44GB 통합 DB를 생성해 `data/search-index-v2/search.sqlite`로 활성화했다. 직전의 불완전 DB는 `search.sqlite.kysing-incomplete`, 전체 PDMX 원본은 `search.sqlite.pre-kysing`으로 보존했다.
- Q-P1-002 동일 쿼리에서 BWV 772는 2위(91.2345점, Pitch/Interval/Contour 100, Rhythm 82.75)로 복구되었고, 기존 1위였던 KYSing `기억 속의 멜로디`는 상위 20개에서 제외됐다. Monteverdi 작품이 근소하게 1위인 것은 사용자가 허용한 유사 클래식 결과 범위에 해당한다.
- 제한 미리보기 API에서 생략된 `ordinalStart`를 `Number(null) === 0`으로 해석해 실제 `start` 마디를 무시하던 오류를 수정했다. 이제 `start=79`는 ordinal 77–81의 5마디 미리보기를 반환한다.
- 잘라낸 첫 마디 중간에 clef-only `<attributes>`가 있으면 이전 divisions/time/key를 상속하지 못하던 오류를 수정했다. 각 속성을 이전 마디들에서 독립적으로 찾아 첫 음표 앞에 합성하며, 빠른 16분음표들의 beat와 강조 위치가 정확히 계산된다.
- 서버에서 이미 잘라낸 제한 XML을 클라이언트가 원래 ordinal로 다시 자르던 이중 trim을 제거하고, `previewOrdinalStart` offset으로 마디와 강조 음표를 연결했다.
- MusicXML에 검색 음표 색상을 직접 기록해 Verovio가 beam 내부 개별 note ID를 보존하지 않는 경우에도 모든 감지 음표가 붉게 표시되게 했다.
- `MusicXML 쨌 Soprano Guitar`의 `쨌`은 UTF-8 가운데점 `·`이 잘못 해석된 mojibake였다. 화면용 구분자를 정상 `·`로 교체했다.
- `사랑,두려움` 사례의 검색 stream은 `Carillon, S3`이며 79마디는 16분음표 16개의 빠른 반주형이다. 기존의 비정상적인 오선은 잘못 자른 마디와 divisions 누락 때문이었고 이는 수정됐다. 다만 이 stream이 선율 결과로 채택되는 현상은 현재 melody-role 공식이 높은 음역·단선율·긴 stream을 선율로 과대평가하고, 동일 비율 리듬 정규화가 4분음표 query와 16분음표 반주를 동일 리듬으로 볼 수 있는 별도의 검색 품질 문제다. 특정 곡 예외가 아니라 반주 texture 판별을 Phase 1 harness에 추가한다.
- 검증: 통합 DB schema, BWV/KYSing 동시 title 조회, Q-P1-002 재검색, 브라우저에서 KYSing 79마디의 5마디 제한 미리보기와 16개 음표 강조(조각·상세 합계 32개)를 확인했다.

## 2026-09-03 검색 중 코퍼스 규모 동적 표시

- 검색 버튼의 `Searching 8,111 works…`는 초기 코퍼스 규모를 `App.tsx`에 직접 적어 둔 상수였으며, 현재 DB를 조회하지 않았다.
- 검색 DB 통계 API `/api/search/v2/stats`를 추가해 고유 source 작품 수와 실제 검색 stream 수를 반환하도록 했다.
- 현재 활성 통합 DB의 실제 규모는 95,520 works / 384,006 melody streams다. 작품 하나의 part·staff·voice가 여러 melody stream이 될 수 있으므로 두 수치를 구분해서 표시한다.
- 통계를 불러온 뒤 검색 중에는 `Searching 95,520 works · 384,006 melody streams…`를 표시한다. API 응답 전에는 부정확한 숫자 대신 `Searching indexed corpus…`를 표시한다.
- 검증: 통계 API 응답, Vitest 9 files / 80 tests, TypeScript 및 Vite production build 통과.

## 2026-09-03 PDMX 악보 조각 강조 및 대용량 전체 악보 우선 렌더링

- 회귀 사례: `Domine salvam fac` 25–28마디, `Brandenburg Concerto No.2 BWV 1047` 7–8마디, `Invention in C major BWV 772` 7마디 상세 화면을 점검했다. 세 XML 모두 API에서 정상 반환됐지만 Verovio 렌더링이 느렸고, public-domain 조각의 붉은 강조가 누락됐다.
- public-domain excerpt를 ordinal 범위로 자른 뒤 내부 마디 index가 다시 1부터 시작했지만 target은 원래 ordinal을 유지해 매칭되지 않았다. 잘라낸 첫 ordinal만큼 position offset을 적용해 조각과 전체 악보가 동일한 음표를 강조하도록 수정했다. 못갖춘마디가 있어 표시 7마디가 XML ordinal 8인 경우도 처리한다.
- 전체 악보가 큰 경우 과거에는 1페이지부터 순서대로 Verovio SVG를 만든 뒤 목표 페이지에 도달했다. 이제 전체 페이지 자리를 먼저 예약하고 `getPageWithElement()`로 검색 음표가 있는 모든 페이지를 우선 렌더링한다. 나머지 페이지는 악보 순서를 유지한 채 점진적으로 채운다.
- 아직 생성되지 않은 페이지에는 `전체 악보 렌더링 중 · page n/N` placeholder를 표시한다. 전체 악보는 고정 page height로 렌더링해 앞 페이지가 추가될 때 목표 위치가 밀리거나 페이지 아래가 잘리는 현상을 줄였다.
- 브라우저 검증: Brandenburg는 조각 9개와 전체 악보 9개, BWV 772와 Domine salvam fac는 각각 조각 10개와 전체 악보 10개의 붉은 target을 확인했다. 대용량 Brandenburg는 101페이지 중 목표가 걸친 두 페이지를 먼저 렌더링했다.

## 2026-09-03 대용량 전체 악보 페이지별 진행 상태

- Brandenburg처럼 101쪽인 악보에서 목표 페이지를 먼저 표시한 뒤 나머지 페이지가 오랫동안 같은 `렌더링 중` 문구로 남아, 작업이 멈춘 것처럼 보이는 문제를 개선했다.
- 검색 일치 페이지 다음에는 1쪽으로 되돌아가지 않고 목표 쪽과 거리가 가까운 앞뒤 페이지부터 채운다. 사용자가 보고 있는 구간의 연속된 주변 페이지가 먼저 나타난다.
- 전체 악보 조판을 시작하기 전부터 `전체 악보 구조를 분석하는 중 · Verovio 조판 준비` 상태를 표시하고 pulse animation을 적용했다.
- 페이지 수가 결정되면 sticky 진행 패널에 `rendered / total pages`와 progress bar를 표시한다. 빈 페이지에도 해당 page 번호와 대기 상태를 표시한다.
- 각 SVG 페이지를 만든 뒤 `requestIdleCallback`으로 브라우저에 렌더링·스크롤·입력 처리 시간을 양보한다. 이를 통해 긴 동기 조판 루프가 여러 페이지에 걸쳐 화면 갱신을 굶기지 않게 했다.

## 2026-09-06 Motif 기반 변형 Query 100개 실제 검색 평가

- 실제 28.66GB 검색 DB에서 KYSing 6곡, MusicXML 7곡, PDMX 7곡의 모티프 후보 20개를 선별했다. 박자는 4/4 15곡, 3/4 2곡, 6/8 2곡, 3/2 1곡이다.
- 각 원형에 중간 음높이 ±1, 내부 한 음 옥타브 이동, 국소 리듬 재분배, 특징적 도약 축소, 쉼표 삽입/길이 변화의 다섯 변형을 적용해 총 100개 Query를 만들었다.
- 생산 `searchDatabase`를 Top100으로 실제 실행했다. 결과는 Top1 78, Top5/Top100 86, 미회수 14였으며 실행 오류는 없었다. 회수된 사례의 중앙 및 p90 순위는 모두 1이었다.
- 원곡 직접 local alignment 진단을 추가한 결과 미회수 14개가 모두 입장 기준을 통과했다. 순위 감점 문제가 아니라 한 음 변경으로 인접 interval seed가 함께 깨지거나 흔한 gram의 후보 제한에서 사라지는 전단 recall 문제로 분류했다.
- 변형별 Top100은 pitch 12/20, octave 15/20, rhythm 20/20, leap 19/20, rest 20/20이다. 다음 개선은 희귀 gram 우선, 좌우 분할 seed, bounded fallback 순으로 A/B 평가한다.
- 결과가 존재한 99개 모두 검색 alignment 좌표가 excerpt XML에 해석됐고 Verovio SVG에 붉은 target이 보존됐다. 결과 0개인 Q-M100-097만 강조 대상이 없었다.
- 검색 latency는 평균 15.67초, 중앙 9.93초, p90 32.68초, 최장 63.75초였다.
- 원자료는 `evaluation/motif-100/cases.jsonl`, 실행 snapshot은 `evaluation/runs/motif-100-latest.json`, 사람이 읽는 전체 보고서는 `docs/motif-100-search-evaluation.md`에 저장했다. 실행기는 사례별 원자 저장과 동일 DB·코드·Query hash 기반 재개를 지원한다.

## 2026-09-06 KY 공식 메타데이터 자동 수집

- 예약 시간을 놓친 뒤 같은 날짜에 수동 재개했다. 공식 조회 100개가 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 205개, cursor 205, 미처리 12,843개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-06.md에 저장했다.

## 2026-09-06 YouTube 대표 영상 일일 수집 예약

- 한 작업에는 heartbeat 자동화 하나만 연결할 수 있어 별도 오전 10시 예약 대신 기존 `ky` 자동화에 YouTube 수집을 통합했다. 매일 한국시간 오전 9시에 KY 수집 후 순서대로 실행한다.
- `scripts/youtube-backfill.mjs`와 기존 title-key cache/state를 사용하며, 하루 최대 search call은 기본 quota 여유를 위해 95회로 설정했다.
- 공개·외부 재생 가능·syndicated 가능·한국 비차단 영상만 저장하고, 편성이 다른 같은 곡은 정규화 제목으로 대표 영상을 공유한다. quota 오류는 우회하지 않는다.
- 현재 `YOUTUBE_API_KEY`가 설정되어 있지 않아 실제 API 호출은 하지 않는다. 예약은 활성 상태이며 키가 예약 실행 환경에 제공된 뒤부터 수집된다.
- 운영 규칙과 실행 기록 위치는 docs/youtube-collection-log.md이다.

## 2026-09-06 Motif 100 후보 회수 보완 및 독립 Motif 200 실행

- 첫 100개에서 확인한 candidate retrieval 누락을 보완했다. 긴·정보량 높은 Query는 interval posting을 확대하고, Query의 서로 떨어진 위치에서 같은 후보 시작점을 지지하는 seed에 가산점을 준다. 반복음 위주의 낮은 정보량 Query는 후보 폭발 방지를 위해 제외한다.
- 동일 100개 A/B는 Top1 78→88, Top5/Top100 86→98, 누락 14→2였다. 회수 12개, 신규 누락 0개, 1위→2위 이동 1개다.
- 정확도 대가로 p50 9.93→22.79초, p90 32.68→46.16초가 되어 posting 회수의 성능 재설계가 다음 우선순위다.
- Harness에 `--suite motif-100|motif-200`을 추가했다. motif-200 생성 시 motif-100의 sourceId를 제외해 다른 작품 20개를 선택한다.
- 독립 Motif 200을 100/100 실행했다. Top1 64, Top5 97, Top10/Top100 98, 누락 2이며 강조 XML/SVG 실패는 0이다. 평균 30.36초, p50 23.68초, p90 55.32초, 최대 110.62초다.
- 실행 중 일부 원본 MusicXML의 열린 slur/tie Verovio 경고를 확인했다. 후속 Harness에는 검색 실패와 분리된 source-notation-integrity 기록을 추가한다.
- 동시에 발생한 브라우저 `Failed to fetch`는 검색 부하가 아니라 5173 Vite 서버가 꺼져 있던 것이 원인이었다. 개발 서버를 PID 23524로 다시 시작하고 `http://127.0.0.1:5173/` 응답을 확인했다.

## 2026-09-06 상세 검색·리듬 Query·전체 악보 재생

- 과거 상세 검색 후보를 다시 확인했다. 사용자가 기억하지 못한 항목은 `쉼표 포함 여부`였고, 기존 문서에는 Exact interval, 쉼표 처리, 리듬 허용 범위, Downbeat 기준, 구조 가중치, 결과 내 재검색을 한 접이식 패널로 모으는 방향이 기록돼 있었다.
- `상세 검색` 버튼을 누르면 checkbox 패널이 아래로 펼쳐진다. Exact Interval, Exact Pitch, Exact Rhythm, Include Rests, Strengthen Downbeat Weight, Search within results를 배치했다.
- Exact Interval은 조옮김을 허용한 음정열 완전 일치, Exact Pitch는 옥타브를 포함한 MIDI 음높이 완전 일치, Exact Rhythm은 전체 tempo/음가 배율을 정규화한 상대 IOI·음가 완전 일치다. 복수 체크는 AND 조건이다. 기존 `absoluteExactOnly` Query는 호환용으로 계속 읽는다.
- Include Rests를 끄면 Query의 rest event를 제거한 뒤 onset을 다시 계산한다. 원곡 음표를 임의 삭제하는 옵션은 아니다.
- Strengthen Downbeat Weight는 우선 기존 metric adjustment의 양·음 방향을 2배로 적용한다. UI에 실험값임을 표시했고, 확정 배율은 Harness A/B로 정한다.
- `Rhythm only` 모드를 추가했다. Query 음표와 쉼표를 오선 대신 한 직선 위의 note head/rest glyph와 길이 비례 폭으로 표시하고 rhythm n-gram 및 제한형 rhythm DTW만으로 검색한다. 실제 5173 API에서 0.5:0.5:1:2 Query가 656ms에 Exact 결과 3개를 반환했다.
- 선택된 event 뒤에 C4 또는 rest를 삽입하는 Insert Note/Insert Rest를 추가했다. 선택이 없으면 끝에 넣는다. 한 번의 `commit`으로 처리되어 Undo/Redo 한 단계에 보존된다.
- 여러 event가 선택된 상태에서 각 음가 카드의 +/−를 누르면 선택된 모든 음표·쉼표의 written duration을 각자 한 단계씩 함께 변경한다. tuplet은 written/effective 비율을 유지한다.
- 악보 상세/카탈로그 전체 화면에 `화면 악보 전체 재생`을 추가했다. public-domain은 표시된 전체 stream, research-preview는 실제 제한 XML에 포함된 마디만 재생한다. tie는 한 attack으로 합치며 현재 음표에 붉은 세로 playhead를 표시한다.
- 검증: Query 편집·검색 관련 Vitest 63개 통과, TypeScript 및 Vite production build 통과, 실제 Rhythm-only API smoke test 통과.
- Windows 브라우저 자동화 helper가 sandbox 초기화 오류로 두 번 종료되어 최종 육안 클릭 검증은 남아 있다. 사용자의 브라우저 수동 확인 또는 helper 복구 후 panel layout, 삽입 위치, 다중 +/−, 긴 전곡 재생을 추가 확인한다.

### 리듬 경계와 악보 재생 탐색 보완

- Rhythm only 직선에서 이벤트마다 오른쪽 세로 경계선을 그리고 첫 이벤트에는 왼쪽 경계도 표시했다. 각 칸의 가로 폭은 음가 비율, 경계는 음표·쉼표가 끝나는 지점을 나타낸다.
- Insert Rest의 일반 추가 아이콘을 제거하고 실제 4분쉼표 glyph `𝄽`로 교체했다.
- 전체 악보 상단에 음표 단위 재생 위치 range를 추가했다. 정지 중 이동하면 다음 재생 시작점과 붉은 막대가 바뀌고, 재생 중 이동하면 기존 Web Audio 예약을 중단한 뒤 선택 위치부터 다시 예약한다.
- 붉은 막대가 화면 밖으로 이동하면 해당 음표를 화면 중앙으로 부드럽게 스크롤한다.
- 관련 Vitest 25개와 production build가 통과했다.
- 기존 Vite PID 23524는 정적 페이지도 23.6초 걸리는 비정상 상태여서 해당 프로세스만 교체했다. 새 PID 35288에서 첫 응답 702ms와 5173 포트 정상 상태를 확인했다.

## 2026-09-06 검색 속도 4단계: 적응형 interval posting

- 모든 interval 3-gram을 최대 250,000행 읽던 고회수율 경로를 적응형으로 교체했다. 일반 gram은 16,000행, 좌우 절반의 희귀 gram은 50,000행, Query 첫·마지막 gram은 100,000행까지만 읽는다.
- 단순 16,000행 제한에서 빠진 `Q-M100-081`을 분석했다. 내부 한 음 변형 때문에 희귀 중간 gram은 원곡과 달라졌고, 실제 surviving seed는 Query 양 끝의 흔한 gram이었다. 따라서 희귀도만이 아니라 변형 후에도 보존될 가능성이 큰 edge evidence를 확장한다.
- 16개 회귀 묶음은 전면 확장과 같은 found 12/16, Top5 12/16을 유지했다. 최종 경계 검증에서 `Q-M100-004`는 1위/9.19초, `Q-M100-081`은 1위/12.73초였다.
- 최종 전체 100개 재실행 중 일부 사례가 1–2분의 긴 꼬리 지연을 보여 중단했다. 실행 결과는 원자 저장되어 있으며, 다음 candidate evaluation 최적화 뒤 전체 Motif 100/200을 다시 실행한다.
- 진단 및 회귀 도구로 `scripts/diagnose-adaptive-postings.mjs`, `scripts/benchmark-adaptive-postings.mjs`를 추가했다. 상세 설계와 측정은 `docs/performance-stage-4.md`에 기록했다.
- 검색 API Vitest 57개와 TypeScript/Vite production build가 통과했다.

## 2026-09-06 Q-P1-007 희소 downbeat 과대평가와 표시 순위

- Query와 문제 제보를 `evaluation/cases/q-p1-007-sparse-downbeat-ranking.json`에 원문 음높이·음가·쉼표, 대상 work/range, 수정 전후 실측치와 함께 보존했다.
- `우리 함께라면` P3:1:1의 4–15마디는 한 마디에 한 음꼴의 희소한 선율인데 기존 Downbeat Weight가 100이었다. 기존 산식이 Query의 중요 박만 검사하고 Query 약박이 후보 강박으로 과도하게 대응하는 경우를 검사하지 않은 것이 원인이었다.
- 모든 alignment pair에서 `Query metric weight < .5`이고 `candidate metric weight >= .65`인 over-accent를 계산해 Downbeat 점수와 보정을 감점한다. 특정 작품·파트 예외는 넣지 않았다.
- 실제 재검색에서 해당 결과는 Downbeat 100→63, 순위 9→14, 최종 ranking 94.01→89.34로 조정됐다. Melody Interval 90.92와 Rhythm 44.01은 그대로여서 변경 범위가 박절 과대평가에 한정됨을 확인했다.
- 카드의 큰 숫자는 과거 `localSimilarity`였지만 목록은 retrieval·phrase·melody-role을 포함한 `ranking`으로 정렬해 숫자와 순서가 달라 보였다. 이제 Similar 카드의 큰 숫자를 실제 `ranking`인 Match score로 표시한다. Exact 결과를 Similar보다 먼저 두는 기존 정책은 유지한다.

## 2026-09-07 점진적 악보 렌더링과 재생 위치 동기화 · Rhythm glyph

- 전체 악보는 검색 일치 페이지를 먼저 렌더링한 뒤 가까운 페이지와 앞쪽 페이지를 점진적으로 채우지만, 재생 컨트롤은 실제 SVG에 어느 playback index가 나타났는지 전달받지 못했다.
- 각 페이지 SVG에서 렌더된 playback index의 최소·최대값과 전체 렌더 완료 여부를 `FullXmlNotation`에서 `FullScorePage`로 전달한다. 사용자가 slider를 직접 조작하지 않은 동안에는 재생 시작 위치가 현재 렌더된 가장 앞 음표로 계속 이동하며, 첫 페이지까지 렌더되면 전체 악보 첫 음표로 갱신된다.
- 사용자가 재생 위치 slider를 직접 옮긴 뒤에는 자동 동기화가 그 선택을 덮어쓰지 않는다. callback은 stable ref를 사용해 재생 상태 변화가 Verovio 전체 재조판을 다시 시작하지 않게 했다.
- Rhythm only 직선의 단순 검은 note head를 written duration에 따른 온·2분·4분·8분·16분·32분·64분 음표 glyph로 교체했다. 쉼표도 같은 음가별 glyph를 사용하며 점음표와 tuplet 비율을 표시한다. 칸 경계와 음가 비례 폭은 유지한다.
- 검증: rhythm glyph 및 FullXmlNotation 관련 Vitest 9개, TypeScript 검증, production build 통과.

## 2026-09-07 Q-P1-008 Similar 점수 보정 · Downbeat 4배 옵션

- 제공 Query를 `evaluation/cases/q-p1-008-similar-score-calibration.json`에 보존하고 실제 생산 검색으로 재현했다. 수정 전에는 Melody Interval 92.92, Rhythm 81.17인 Similar 결과도 retrieval·구조 가산점 뒤 100으로 clamp되어 Exact와 구별되지 않았다.
- Exact 결과의 최종 Match score는 100으로 고정한다. Similar는 `55% local similarity + 45% surface score`로 다시 보정하고, retrieval·phrase·part-role 보정 합계는 -3~+1 범위로 제한하며 최종 상한을 97로 둔다. melody+rhythm surface score는 Melody Interval 75%와 Rhythm 25%다.
- 실제 재검색에서 Exact TOP GUN ANTHEM은 100을 유지했고 상위 Similar는 97, 97, 97, 95.22, 94.91로 분리됐다. `À Dieu dame`은 100에서 94점대로 내려갔다.
- 1위 Exact의 Rhythm은 100이지만 Downbeat Weight 58, Schenker-Informed 79다. 시작은 3마디 1박이나 중요 박 유효 일치는 2곳뿐이며, 구조 축약은 Query 기둥음 3개와 후보 문맥 기둥음 7개를 비교한다. 음가 완전 일치와 다른 평가축이므로 임의로 100으로 올리지 않았다.
- 상세 검색의 `Search Within Results` 표기를 통일했다. `Strengthen Downbeat Weight` 설명은 `Downbeat 가중치 4배 적용`으로 바꾸고 실제 metric adjustment multiplier도 2배에서 4배로 변경했다.
- 검색 API Vitest 60개와 TypeScript 검증 통과.

## 2026-09-07 세 번째 독립 변형 Query 100개 평가

- scripts/motif-100-benchmark.mjs가 motif-300을 지원하고 이전 suite의 source를 누적 제외하도록 확장했다. 새 세트 100개/원곡 20개가 motif-100·200과 source 중복 0임을 확인했다.
- 실제 검색 100건을 끝까지 실행했다. Top1 70, Top5 96, Top10 98, Top100 99, 미회수 1이며 중앙 순위 1, p90 순위 3이다.
- 변형별 Top5는 pitch 20/20, octave 18/20, rhythm 20/20, leap 20/20, rest 18/20이다. Q-M300-067 'Amarillis'의 내부 한 음 옥타브 이동만 admission에서 미회수됐다.
- Q-M300-090 'THAXTED (Holst)'의 15위는 같은 Holst 선율의 'I Vow to Thee, My Country'·'Jupiter' 판본들이 상위를 차지한 결과다. 알고리즘 오답으로 단정하지 않고 canonical tune/edition family 기반 다중 정답 Harness 과제로 기록했다.
- 강조 XML 및 Verovio 렌더는 100건 모두 성공했다. latency는 평균 21.36초, p50 20.04초, p90 34.85초, 최대 55.61초로 정확도에 비해 여전히 느리다.
- 전체 Query와 결과는 docs/motif-300-search-evaluation.md, evaluation/motif-300/cases.jsonl, evaluation/runs/motif-300-latest.json에 보존했다. 실행기 Vitest 2개도 통과했다.

## 2026-09-07 KY 공식 메타데이터 자동 수집

- 예약 시간을 놓친 뒤 같은 날짜에 수동 재개했다. 공식 조회 100개가 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 305개, cursor 305, 미처리 12,743개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-07.md에 저장했다.

## 2026-09-07 YouTube 대표 영상 자동 수집

- YOUTUBE_DAILY_SEARCH_LIMIT=95로 실행했으나 YOUTUBE_API_KEY가 설정되지 않아 API 호출을 보내지 않았다.
- search call 0, 신규 매칭 0, no-match 0이며 quota 및 기존 영상 자료는 변경되지 않았다.
- 영상 DB 및 검색 DB 동기화는 수행하지 않았다. 수집을 시작하려면 실행 환경에 YouTube Data API 키 설정이 필요하다.

## 2026-09-07 상세 악보 주요 Motif 오선·유사 음악 탐색

- 상세 악보 오른쪽의 '주요 interval motif' 숫자 막대를 실제 4–8음 대표 음표열과 음가를 보여주는 Verovio 오선 카드로 교체했다.
- 서버 motif 분석 결과에 대표 음표·spelling·음가, 시작/종료 마디, 반복 occurrence 위치를 포함한다. 렌더링은 기존 MEI/Verovio 런타임을 재사용하므로 별도 SVG·PNG 파일이나 전체 motif 쌍 유사도 저장소를 만들지 않는다.
- 각 카드의 '비슷한 Motif' 버튼은 선택 motif를 melody+rhythm Query로 기존 검색 API에 요청하고 현재 작품을 제외한 상위 6개 작품·파트·마디·Match 점수를 표시한다. 결과를 누르면 해당 검색 구간의 상세 악보로 이동한다.
- 임의 motif가 반드시 강박에서 시작한다고 가정하지 않도록 startsOnDownbeat은 false로 요청한다.
- 오른쪽 aside를 viewport 안의 독립 스크롤 영역으로 만들고 overscroll 격리, 안정적인 scrollbar gutter, 모바일 단일열 해제를 적용했다.
- 실제 THAXTED 8음 motif 검색에서 I Vow to Thee, My Country 및 Jupiter의 여러 파트가 100–94.59점으로 반환되는 것을 확인했다. 작품 API는 motif 8개와 첫 motif의 8음·14회 occurrence·3/4·조표 -2를 반환했다.
- motif payload 및 MEI 관련 Vitest 76개, TypeScript 검증, production build가 통과했다. 실행 사이트 HTTP 200도 확인했다.
- Windows 브라우저 자동화 helper가 sandbox 초기화 오류로 재시도 후에도 종료되어 최종 육안 클릭 검증은 남아 있다.

### 반복음 지배 Motif 억제

- 단순 반복음이 occurrence 수만으로 주요 motif 상위에 오르지 않도록 음고 정보량 하한을 추가했다.
- 길이의 60%에 해당하는 서로 다른 음고를 요구하되 최대 4개까지만 요구한다. 한 음이 전체의 절반 이상을 차지하거나, 연속 동일음 진행이 interval의 34%를 넘는 후보는 제외한다.
- 조건을 통과한 후보도 고유 음고 비율과 비반복 진행 비율이 낮으면 motif score를 감점한다.
- 실제 THAXTED 응답에서 연속 동일음 지배 패턴은 제거됐고, 추가 확인에서 발견한 2음 교대 4음 패턴도 새 기준으로 제외했다.

### 주요 Motif 6–12음과 검색 예상시간

- 주요 motif 분석 범위를 4–8음에서 6–12음으로 변경했다. 8–10음은 길이 가중치 1.25, 11–12음은 1.08, 6–7음은 0.88을 적용해 중간 길이를 우대한다.
- 작품 내부 후보 선별은 반복·길이·음가·음고 정보량을 사용하는 경량 분석으로 유지한다. 각 motif의 '비슷한 Motif'는 별도 단순 비교가 아니라 일반 Melody+Rhythm 메인 검색 API의 후보 검색, local alignment, rhythm, downbeat, structural/admission 논리를 그대로 사용한다.
- 모든 6–12음 window를 전체 corpus 메인 검색으로 미리 실행하는 방식은 작품 하나당 수백~수천 번의 전체 검색을 발생시키므로 적용하지 않았다. 사용자가 선택한 상위 motif만 요청 시 메인 검색한다.
- Query 검색 버튼에 초 단위 예상 잔여 시간을 표시한다. mode, 음표 길이 구간(short/medium/long), 전체 corpus/결과 내 검색별로 실제 완료 시간의 지수 이동 평균을 localStorage에 학습한다.
- 예상 시간이 남아 있는 동안 N초 남음으로 감소하고, 예측 시간을 넘으면 잘못 0초 완료로 보이지 않게 '검색 결과 정리 중…'으로 전환한다. 이 단계에는 후보 정렬·분류·응답 처리가 포함된다. 검색 성공·실패 모두 실제 경과 시간으로 다음 예측을 갱신한다.
- 실제 THAXTED 응답에서 주요 motif가 8음 1개와 12음 후보들로 반환되고 모든 후보가 6–12음 범위임을 확인했다. 관련 Vitest 78개, TypeScript 검증, production build 및 실행 사이트 HTTP 200이 통과했다.
# 2026-09-07 전체 악보 검색 위치 재생·탐색 개선

- 멜로디 검색 결과와 유사 Motif 결과에서 상세 악보로 이동할 때 `source=search` 문맥을 명시한다. 주소 직접 입력이나 텍스트 카탈로그의 `browse=1` 진입에는 검색 위치 UI를 노출하지 않는다.
- 검색을 통해 들어온 상세 악보는 점진 렌더링 중 첫 재생 위치를 실제 검색 일치 음표의 첫 playback index로 맞춘다. 전체 페이지 렌더링이 완료되면 자동 시작 위치는 전체 악보의 처음으로 돌아간다.
- 재생 slider에 검색 일치 음표 범위를 작은 붉은 표식으로 표시한다. 이 표식은 검색 문맥에서만 보인다.
- 재생 막대 아래에 `-5`, `-1`, `+1`, `+5` 마디 이동 버튼을 추가했다. 음표 수가 아닌 원본 `measureOrdinal` 순서로 이동하며, 재생 중 조작하면 새 위치에서 이어서 재생한다.
# 2026-09-08 클래식 레퍼토리 등록 우선순위 스프레드시트

- Open Opus 공개 API를 기준으로 10개 시대에 걸친 작곡가 220명과 작품 14,027개를 정리한 `outputs/classical-repertoire-priority-2026-09-08/classical-repertoire-priority.xlsx`를 생성했다.
- 작곡가는 S(가장 유명), A(핵심), B(주요), C(확장) 등급으로 분류했다. Open Opus Popular Composer는 S, Essential Composer는 A, 그 밖에는 인기·필수 작품 수에 따라 B/C를 나눈다.
- S·A 작곡가는 Complete Catalogue 우선, B 작곡가는 대표·필수 작품 우선, C 작곡가는 특별히 유명한 작품부터 수집하도록 정책을 표시했다.
- 작품 목록은 중세부터 21세기까지 시대 순서와 작곡가 출생 연도 순서로 배열했다. 실제 작곡 연도는 추정하지 않고 비워 두어 Wikidata와 작곡가별 권위 카탈로그로 보완할 수 있게 했다.
- 작품 등록 등급과 점수는 작곡가 등급, Open Opus 인기·필수 작품 여부, Complete Catalogue 대상 여부를 참조하는 Excel 수식으로 구성했다. XML 확보 상태와 검증 상태에는 선택 목록을 적용했다.
- `우선 등록`, `작품 목록`, `작곡가 목록`, `기준 및 출처` 네 시트를 만들고 필터, 고정 창, 조건부 서식, 출처와 분류 한계를 포함했다. XLSX 재검사에서 수식 오류는 발견되지 않았다.

## 2026-09-08 클래식 레퍼토리 우선순위 확장판

- 기존 `classical-repertoire-priority.xlsx`는 보존하고 `classical-repertoire-priority-v2.xlsx`를 별도로 생성했다.
- Open Opus 초기 220명에 없던 작곡가 30명을 `보완 작곡가` 수집 큐에 추가했다. 여성 작곡가, 흑인 작곡가, 동아시아, 라틴아메리카·카리브, 중동부 유럽을 우선 보완했으며 등급은 검증 전 제안값으로 표시했다.
- 기존 S등급 작곡가 23명 전원을 `전작 카탈로그`에 연결했다. Bach Digital, Digital Mozart Edition, Beethoven-Haus, Schubert Online은 확인 출처로 기록하고 나머지는 RISM·IMSLP 및 작곡가별 기관을 통한 추가 검증 대상으로 구분했다.
- `대표작 큐` 32건과 `교육·연주` 큐 25건을 추가했다. 교육 목록은 현행 ABRSM·RCM·대학 강의계획서와 교차검증하기 전까지 후보로만 관리한다.
- `균형 점검`에서 시대·여성·지역·흑인 작곡가 보완 상태를 집계하고, 특히 중세·르네상스·바로크·21세기의 추가 보완 필요성을 표시했다.
- `현대 저작권`은 메타데이터 등록과 XML·악보 공개를 분리했다. 권리 검토 대상 16명을 수집 큐로 만들고 관할·권리자 확인 전에는 XML 공개를 허용하지 않는 원칙을 명시했다.
- `우선 등록`에 확장 진행 현황을 추가하고 `기준 및 출처`에 Bach Digital, DME, Beethoven-Haus, Schubert Online, RISM, IMSLP, ABRSM, 국가법령정보센터 출처를 추가했다.
- 10개 시트, 기존 작품 14,027개를 유지했다. 확장 시트 전체 렌더 파일이 생성됐고, XLSX 재검사에서 누락 시트와 수식 오류는 발견되지 않았다.

## 2026-09-08 일일 KY·YouTube 수집

- KY 공식 메타데이터 100개를 조회해 100개 모두 번호 정확 일치와 비어 있지 않은 제목 조건으로 신규 저장했다. 누적 405개, 미처리 12,643개이며 오류는 없었다.
- KY 원본 XML과 검색 DB는 변경하지 않았다. 신규 목록은 docs/ky-collection/2026-09-08.md에 기록했다.
- YouTube API 키 설정 후 Pacific date 2026-09-07 기준 안전 한도 95회를 모두 실행했다. 공개·외부 삽입 가능·한국 비차단 조건을 통과한 대표 영상 95개를 `data/youtube-matches.json`에 저장했고 no-match와 quota 오류는 없었다. 검색 DB 동기화는 수행하지 않았다.

## 2026-09-08 클래식 목록과 보유 XML 자동 대조

- `classical-repertoire-priority-v2.xlsx`와 현재 `data/search-index-v2/search.sqlite`를 대조해 `classical-repertoire-priority-v3.xlsx`를 생성했다. 기존 v2는 보존했다.
- 검색 DB 384,425 stream을 source+title+composer 기준 95,625개 작품으로 묶었다. 출처별 작품은 기존 Music Analysis 8,111개, PDMX 49,606개, KYSing 37,908개다.
- 클래식 목록 14,027개를 카탈로그 번호, 작곡가, 정규화된 제목, 핵심 제목 토큰으로 비교했다. 카탈로그 번호와 작곡가/제목, 또는 제목과 작곡가가 함께 맞아야 자동 `보유`로 판정했다.
- 결과는 보유 1,520개, 부분 보유 215개, 검토 필요 3,520개, 미보유 8,772개다. 단일 강한 단서만 맞는 항목은 보유율에 포함하지 않았다.
- 기존 `작품 목록`의 XML 확보 상태를 대조 결과로 채우고, `보유 현황`, `대조 상세`, `수집 우선순위` 시트를 추가했다. 미보유 전체를 작품 등급·작곡가 등급·점수순 수집 큐로 정렬했다.
- 자동 보유 1,520개도 최종 확정이 아니라 수동 검증 대상으로 두었다. 동일 작품의 다른 악장, 편곡, 언어별 제목과 판본 관계는 후속 검증이 필요하다.
- 13개 시트와 14,027개 작품을 재검사했으며 작품 목록과 상세 대조 상태 합계가 일치하고 수식 오류는 없었다. 변경 화면 5개 렌더링도 생성됐다.
## 2026-09-08 클래식 보유 검증 큐와 1차 수집

- 클래식 보유 대조에서 자동 보유·부분 보유·검토 필요로 분류된 5,252개를 원곡·악장·편곡 관계와 권리 상태에 따라 다시 분류했다.
- 관계 분류는 동일 작품 후보 1,461개, 편곡판 후보 209개, 악장·부분 후보 2개, 동일성 검토 3,580개다. 고신뢰 표본 761개를 가장 먼저 수동 검증하도록 정렬했다.
- 권리 1차 분류는 공개 후보 3,523개, 라이선스 충돌 검토 1,373개, 권리 미확인 109개, 검색 조각만 247개다. 공개 후보도 개별 판본 확인 전에는 확정하지 않는다.
- 작품 등급·점수를 계산 결과가 아니라 수식 문자열로 읽던 중간 오류를 발견해 대조기를 `data_only=True`로 수정하고 coverage와 validation JSON을 재생성했다.
- 미보유 중 S/A급 작곡가의 A/B급 작품만 대상으로 작곡가별 상한을 적용해 46명·154곡의 `1차 수집` 목록을 만들었다. 목표 개수를 채우려고 낮은 우선순위 작품을 추가하지 않았다.
- `classical-repertoire-priority-v4.xlsx`에 `보유 검증 큐`와 `1차 수집`을 추가했다. 수동 검증, 수집 상태, 권리 상태, XML 품질 선택 항목을 포함한다.
- 15개 시트를 재검사했으며 검증 큐 5,252행, 1차 수집 154행, 46명 작곡가가 확인됐다. 수식 오류는 없고 변경 화면 4개 렌더링도 생성됐다.
## 2026-09-08 Beethoven·Mozart·Chopin 검색 인덱스 추가 및 utf8 용량 조사

- `K:/Music Analysis/MusicXML` 아래 Beethoven, Mozart, Chopin 폴더를 신규 검색 대상으로 조사했다. 지원 확장자는 총 206개, 원본 합계는 151,979,421 bytes(약 145 MiB)였다.
- 205개가 파싱됐고 Beethoven XML 1개는 첫 바이트부터 XML 문법 오류가 있어 보류했다. 파싱 결과에서 내용 해시가 같은 파일명 중복 17개를 분리했으며, 기존 본 인덱스와 같은 work ID는 없었다.
- 실제 신규 188작품을 738개 파트/보이스 선율 스트림과 1,290,740개 gram으로 구성한 delta SQLite로 만들고 본 인덱스에 트랜잭션 병합했다.
- 독립 delta는 112,754,688 bytes였고, 본 `search.sqlite`는 28,657,737,728 bytes에서 28,887,048,192 bytes로 229,310,464 bytes(약 218.7 MiB) 증가했다. 원본 세 폴더 크기의 약 1.51배다.
- 재현·감사를 위해 인벤토리, 파싱 실패, 폴더 내부 중복, 기존 인덱스 중복 대조, 병합 manifest를 `data/composer-folders-2026-09-08`에 보관했다.
- `utf8` 폴더는 아직 본 인덱스에 추가하지 않았다. 3,299개 XML, 3,415,087,170 bytes(약 3.18 GiB)이며 해시 기준 고유 파일은 3,210개다. 81개 중복 그룹에서 여분 파일 89개가 확인됐다.
- 파일 크기 분위별 100개 표본을 파싱한 결과 99개 성공, 비어 있는 Handel XML 1개 실패, 847개 선율 스트림이었다. 표본 117,634,441 bytes에서 JSONL 22,776,424 bytes, 독립 SQLite 97,869,824 bytes가 생성됐다.
- 표본과 이번 실병합 비율을 함께 적용하면 `utf8`의 독립 delta는 약 2.6–3.5 GiB, 본 인덱스 순증가는 약 4.8 GiB 중심의 4–7 GiB 범위로 예상한다. JSONL·delta·병합 임시 공간까지 포함해 최소 10–12 GiB 여유 공간을 확보한 뒤 전체 파싱하는 것이 안전하다.
- 조사 종료 시 K 드라이브 여유 공간은 약 57.96 GiB, U 드라이브는 약 21.54 GiB로, 현재 K 공간은 충분하다. 다만 26.9 GiB 본 인덱스의 완전 복사 백업까지 동시에 만들면 여유 폭이 크게 줄어드므로 `utf8` 투입 전 백업 보존 정책을 먼저 정한다.
## 2026-09-08 Verovio MusicXML 교차 성부 수직 정렬 보정

- Beethoven Piano Sonata Op.13 2악장(`work-f95d2f4544ebf9c6`)의 1–5마디를 조사했다. 원본은 한 마디 안에서 voice 1과 voice 2를 박마다 `note → backup → note`로 교차 기록해 MusicXML 시간축은 맞지만 Verovio importer에서 동시 onset 음표가 수평으로 밀리는 유형이다.
- 원본 XML과 검색·분석 onset은 수정하지 않고, `FullXmlNotation`이 Verovio에 전달하는 임시 XML DOM에만 `normalizeMusicXmlVoices`를 적용했다. 이 공통 경로를 쓰는 검색 결과 악보 조각과 상세 악보 화면에 모두 반영된다.
- 둘 이상의 staff/voice lane이 교차 재등장하고, 첫 note부터 마지막 note 사이가 note와 backup만으로 구성되며, 각 lane이 마디 시작부터 내부 공백 없이 이어지는 마디만 lane별 연속 블록으로 재배열한다.
- forward, 중간 direction·harmony·attributes, grace, 불완전 성부 등 의미 이동 위험이 있는 마디는 원문 그대로 유지한다. chord note node와 기존 검색 강조·재생 ID는 같은 DOM node를 이동하므로 보존된다.
- 관련 단위 테스트 8개가 통과했고 TypeScript 검사와 production build가 성공했다. 전체 185개 테스트 중 184개가 통과했으며, 이번 변경과 무관하게 기존 Harness 사례 `q-p1-007-sparse-downbeat-ranking.json`의 `createdAt` 누락 검증 1개는 계속 실패한다.
- 실행 사이트와 대상 URL은 HTTP 200을 확인했다. Windows CUA helper의 sandbox 초기화 오류로 최종 브라우저 좌표 육안 검증은 자동화하지 못했다.
## 2026-09-09 밀집 미세 템포 표시로 인한 Beethoven 악보 조판 오류

- `work-c05df0204a6d4955`의 검색 구간은 동일 작품 파일 안에서 마디 번호가 다시 1로 시작하는 두 번째 악장으로, 인덱스 ordinal 313–317 및 절대 onset 1248–1256에 정상 매핑됐다. 잘못된 작품·마디 선택이나 교차 성부 정규화 오작동은 아니었다.
- 원본 MusicXML이 표현적 재생을 위한 63–70 BPM대의 미세 템포 변화를 짧은 간격의 인쇄 가능한 `<metronome>` direction 12개로 기록해 Verovio가 악보 위에 전부 표시한 것이 주원인이었다.
- 렌더링용 임시 XML에서만 밀집된 순수 숫자 메트로놈 자동화를 축약한다. 4마디 범위에 4개 이상 밀집한 경우 대표 표시를 유지하고, 이전 대표와 25% 이상 차이 나는 큰 템포 전환 또는 4마디 이상 떨어진 표시는 보존한다. `Adagio cantabile` 같은 문자 지시와 다른 direction은 제거하지 않는다.
- 정리는 `FullXmlNotation` 공통 경로에서 모든 part에 적용되므로 검색 결과 악보 조각과 상세 악보 양쪽에 적용된다. 원본 MusicXML, 검색 인덱스, 재생 onset은 변경하지 않는다.
- 해당 5마디 재현에서 숫자 메트로놈 표시는 12개에서 1개로 줄었고 음표 66개와 두 오선은 그대로 유지됐다. Verovio 출력 높이는 192에서 157로 줄어 악보 상단의 겹침이 해소됐다.
- 일본어 `グランドピアノ`와 `ピアノ`를 각각 `Grand Piano`, `Piano`로 번역하고 part-name, part-abbreviation뿐 아니라 instrument-name에도 적용했다.
- 관련 렌더링 테스트 9개와 일본어 번역 회귀 테스트가 통과했고 TypeScript 검사, production build, diff 검사가 성공했다. 전체 server test의 카탈로그 검색 1건은 26.9 GiB DB 조회가 기존 5초 제한을 넘어 timeout됐으며 이번 변경의 assertion 실패는 아니다.
- 개발 서버를 재시작했으며 포트 5173 API에서 `Grand Piano`와 XML 내 일본어 이름 제거를 확인했다.
## 2026-09-09 전체 악보 encoded page break 과밀·겹침 수정

- `work-c05df0204a6d4955` 전체 악보에서 10마디 이후가 페이지 밖으로 나가고 다음 system이 가로로 겹치며, 58마디 아래 system도 겹치는 현상을 재현했다.
- 원인은 원본 MuseScore 종이 크기용 `new-system/new-page` 지시를 앱의 1900×2700 Verovio 화면 페이지에 `breaks: encoded`로 강제한 것이다. 제목·여백·배율이 달라진 화면 페이지에 원본 system 수가 그대로 들어가면서 한 페이지에 최대 7 system이 압축됐다.
- Verovio 진단에서 encoded 모드는 전체 16쪽, 10마디 1쪽, 58마디 2쪽이었고 justification ratio가 0.44–0.63까지 내려가는 과밀 경고가 반복됐다.
- 전체 악보를 `breaks: auto`로 변경해 앱의 현재 pageWidth, pageHeight, scale에 맞춰 system과 page를 다시 나누도록 했다. 비교 결과 전체 39쪽, 10마디 2쪽, 58마디 5쪽으로 분산되고 해당 페이지는 3–5 system으로 줄었다.
- 검색 악보 조각은 기존처럼 `breaks: none`을 유지 사용하므로 이번 변경의 영향을 받지 않는다. 전체 악보의 검색 일치 페이지 우선 렌더링과 점진적 3쪽 로딩도 그대로 유지된다.
- 자동 재조판 회귀 테스트를 추가했고 관련 테스트 10개, TypeScript 검사, production build, diff 검사와 실행 사이트 HTTP 200이 통과했다.

## 2026-09-09 일일 KY·YouTube 수집

- KY 공식 메타데이터 100개를 조회해 번호 정확 일치와 비어 있지 않은 제목 조건을 만족한 100개를 신규 저장했다. 누적 505개, 미처리 12,543개이며 오류는 없었다.
- KY 원본 XML과 검색 DB는 변경하지 않았고 신규 목록은 docs/ky-collection/2026-09-09.md에 기록했다.
- YouTube 수집은 자동화 실행 환경에 YOUTUBE_API_KEY가 없어 API 호출을 보내지 않았다. search call, quota, 기존 영상 자료와 검색 DB는 변경하지 않았다.

### YouTube 수동 재실행

- 재시작 후 현재 프로세스와 개발 서버에서 `YOUTUBE_API_KEY` 인식을 확인하고 YouTube 대표 영상 수집을 다시 실행했다.
- 99개 제목을 조회해 실제 영상 87개와 no-match 12개를 저장했다. 누적 194개 레코드 중 182개에 `videoId`가 있다.
- 100번째 요청 직전에 분당 Search Queries 제한 HTTP 429가 발생해 안전하게 중단했으며, state는 Pacific date 2026-09-09, search call 99, cursor 195로 기록됐다.

## 2026-09-09 Codex Windows sandbox helper 복구 경로

- 기본 `exec_command`와 `apply_patch`가 명령 시작 전에 `windows sandbox failed: helper_unknown_error: setup refresh had errors`로 실패하는 현상을 Music Analysis의 `music21 작곡 Harness 만들기` 작업 기록과 대조했다.
- `K:\MusicSearch`는 Codex 설정에서 `trusted`, Windows sandbox는 `elevated`이며 폴더 ACL에도 `CodexSandboxUsers`의 Modify 권한이 있어 프로젝트 권한 부족은 아니었다.
- 현재 작업에 남은 workspace helper 초기화 오류는 승인된 elevated 명령으로 우회하고, 파일 변경은 설치된 Codex CLI의 `--codex-run-as-apply-patch`를 사용한다. 일반 PowerShell 파일 쓰기로 대체하지 않는다.
- 이 경로로 `docs/youtube-collection-log.md`와 본 개발 로그 갱신을 실제 검증했다. 전역 보안 설정이나 프로젝트 ACL을 추가로 완화하지 않았다.

## 2026-09-09 UTF-8 BOM MusicXML Verovio 로딩 실패 수정

- `work-f95d2f4544ebf9c6` 상세 URL은 HTML 200, 작품 API 200으로 정상 응답했지만 Verovio가 `No <music> element found`와 `Error importing data`를 내고 page count 0을 반환하는 현상을 재현했다.
- 원본은 정상적인 MusicXML `score-partwise`이지만 첫 문자가 UTF-8 BOM(U+FEFF)이었다. 자동 입력 형식 감지에서는 이를 MEI로 잘못 판단했고, BOM 제거와 MusicXML 입력 형식 명시 후 동일 원본이 5페이지로 정상 조판됐다.
- `FullXmlNotation` 공통 입력 경로에서 선두 BOM을 제거하고 Verovio 옵션에 `inputFrom: musicxml`을 지정했다. 검색 결과 악보 조각과 상세 전체 악보 양쪽에 적용되며 작품 ID별 예외는 없다.
- Verovio가 데이터를 거부하거나 페이지를 만들지 못하면 빈 화면 대신 명시적인 MusicXML 로딩 오류를 표시하도록 실패 검사를 추가했다.
- BOM 제거 및 무변경 회귀 테스트를 추가했고 관련 테스트 10개, TypeScript 검사와 production build가 통과했다.

## 2026-09-09 Beethoven Op.13 2악장 전 구간 교차 성부 겹침 보정

- `work-f95d2f4544ebf9c6`의 25·30·35마디를 포함해 뒤쪽 여러 마디에서 동시 onset 음표가 수평으로 밀려 겹치는 현상을 원본 MusicXML 시간축으로 조사했다.
- 이 파일은 voice 1과 voice 2를 박마다 `note → backup → note`로 교차 기록하며, 전체 55마디가 교차 성부 배열이다. 기존 정규화는 각 voice가 마디 시작부터 내부 공백 없이 이어질 때만 적용되어 25마디처럼 한 voice가 중간에 쉬는 마디를 건너뛰었다.
- 렌더링용 임시 XML에서 voice별 블록을 만들 때 시작·중간 공백을 MusicXML `<forward><duration>…</duration></forward>`로 보존하도록 일반화했다. 실제 음표, 쉼표, chord, voice, staff, onset, duration, beam은 변경하지 않는다.
- 같은 voice 안에서 chord 표기 없이 attack이 겹치는 경우는 위험한 원본으로 보고 변환하지 않는다. chord는 root onset을 공유하며 시간축을 두 번 진행하지 않도록 별도 검증한다.
- 작품 전체 검사에서 중간 clef 변경이 없는 교차 성부 53마디가 새 안전 조건을 통과했다. 8·71마디는 각각 staff 1과 staff 2의 중간 clef 변경을 포함해, 음자리표 시점을 손상시키지 않도록 기존 보존 규칙에 따라 원문을 유지한다.
- 관련 테스트 15개, TypeScript 검사와 production build가 통과했다. 전체 테스트는 194개 중 193개 통과했으며 기존 Harness `q-p1-007-sparse-downbeat-ranking.json`의 `createdAt` 누락 1건만 이번 변경과 무관하게 실패했다.

## 2026-09-09 상세 악보 상단 재배치 및 노래방 전체 악보 테스트 모드

- 상세 화면의 제목을 sticky 제어 행에서 분리했다. 위 행에는 검색 결과로 돌아가기, 검색 일치 구간, Phrase layer, 재생 바와 재생 버튼만 두고 제목·작곡가/가수는 아래 독립 행에서 더 큰 반응형 글꼴로 표시한다.
- 로컬 개발 환경에서는 `research-preview` 노래방 상세 화면도 원본 XML 전체와 모든 파트를 표시한다. 검색 결과 카드의 작은 악보 조각은 기존처럼 검색된 파트와 일치 마디만 사용한다.
- 기존 저작권 제한 버전은 삭제하지 않았다. `restrictedPreviewXml`과 앞뒤 10마디·단일 파트 경로를 그대로 보존하고 production에서는 기본 제한 모드로 사용한다. 로컬에서도 `KYSING_FULL_SCORE_TEST_MODE=0`으로 즉시 되돌릴 수 있고, production에서 명시적으로 `1`을 설정한 경우에만 전체 테스트 모드를 허용한다.
- 실제 상세 API 표본에서 5개 파트와 `restrictedPreviewActive=false`를 확인했다. 관련 테스트 81개, TypeScript 검사와 production build가 통과했다.

## 2026-09-10 YouTube 외부 재생 실패 영상 제외

- 수집 스크립트에 `--reject-video-id`를 추가하고, 수동으로 외부 재생 실패가 확인된 영상 ID를 `rejectedVideoIds`에 영구 보존하도록 했다.
- 자동 후보 검색은 제외 목록의 ID를 건너뛰며, 이미 캐시에 저장된 같은 ID도 재수집 대상으로 되돌린다.
- YouTube Data API에서 `embeddable=true`로 응답하더라도 실제 iframe 재생이 실패할 수 있는 사례를 고려해 `pgYEJHJXFB4`를 제외하고 `Beauty and the Beast`를 공식 채널 영상 `ippaCca4L6A`로 교체했다.

## 2026-09-11 텍스트 검색 전체 결과 탐색

- 상단 검색창은 중복 제목을 제거한 상위 12개를 빠르게 미리 보여주고, 하단의 `검색 결과 더 보기`에서 별도 전체 결과 화면으로 이동한다.
- `/catalog` 화면은 검색 결과를 24개씩 보여주며 이전·다음 페이지 탐색을 지원한다. 검색어와 페이지는 URL에 보존된다.
- 카탈로그 API에 `limit`, `offset`, `hasMore`를 추가했다. 파라미터가 없는 기존 호출은 계속 12개를 반환한다.

## 2026-09-12 텍스트 검색의 판본별 결과 표시

- `A Whole New World` 일반 MusicXML 여러 판본은 정상 인덱싱되어 있었지만, 제목 단위 중복 제거로 노래방 결과 하나만 남는 원인을 확인했다.
- 텍스트 검색에서는 같은 제목도 악보 파일·편성·출처가 다르면 모두 별도 결과로 표시한다.
- 한 MusicXML 파일에서 파트와 보이스 때문에 생성된 여러 검색 스트림만 파일당 최고 우선순위 스트림 하나로 합쳐, 동일 악보가 불필요하게 반복되는 것은 방지한다.

## 2026-09-12 검색 성능 5단계: 파싱 음표 LRU

- 28.9GB 인덱스에서 `Q-M100-004`가 약 100.6초 걸려 긴 꼬리 지연이 다시 발생했음을 확인했다.
- 검색 논리를 바꾸지 않고 최근 작품의 파싱된 음표를 기본 128MiB weight-bounded LRU로 재사용한다. DB 수정 시 자동으로 폐기한다.
- 단계별 프로파일에 캐시 hit/miss와 사용 바이트를 추가하고 벤치마크 출력에도 전체 profile을 포함했다.
- 다음 단계는 동일 Query cold/warm 비교 후 SQL-side 후보 시작점 집계와 저비용 후보 사전 평가 중 실제 병목에 맞는 쪽을 선택한다.
- 첫 프로파일에서 cold 36.6초 중 retrieval 28.1초가 지배적이었고, 초기 캐시는 1,526개 순차 후보가 예산을 밀어내 hit가 없었다. 캐시 대상을 상위 full-stream 평가 작품으로 한정하고, Query 내부의 중복 n-gram postings를 token당 한 번만 조회하도록 보정했다.
- 보정 후 `Q-M100-004`는 7.32초와 7.05초에 완료됐고 두 번 모두 기대 작품 1위와 결과 83개를 유지했다. 반복 실행의 full-stream 캐시 hit는 260건, decode는 888ms에서 556ms로 감소했다. retrieval은 약 4.1–4.3초로 여전히 가장 큰 단일 병목이다.

## 2026-09-10 KY 공식 메타데이터 자동 수집

- 예약 시간을 놓친 뒤 같은 날짜에 수동 재개했다. 공식 조회 100개가 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 605개, cursor 605, 미처리 12,443개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-10.md에 저장했다.

## 2026-09-11 KY 공식 메타데이터 자동 수집

- 예약 시간을 놓친 뒤 같은 날짜에 수동 재개했다. 공식 조회 100개가 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 705개, cursor 705, 미처리 12,343개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-11.md에 저장했다.

## 2026-09-12 KY 공식 메타데이터 자동 수집

- 예약 시간을 놓친 뒤 같은 날짜에 수동 재개했다. 공식 조회 100개가 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 805개, cursor 805, 미처리 12,243개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-12.md에 저장했다.

## 2026-09-12 YouTube 외부 재생 상태 및 악보-영상 문구 정정

- `Moon River`의 `EUO34CiTA4o`가 Data API의 임베드 가능 조건을 통과하면서 실제 외부 재생은 실패하는 사례를 확인해 영구 제외했다.
- 검색 결과의 붉은 음표는 MusicXML 검색 정렬 결과이며 YouTube 타임코드 정렬이 아님을 명시하도록 문구를 고쳤다.
- 실제 동기화에는 영상별 audio-to-score alignment 결과인 score beat↔recording second 매핑이 필요하며, 현재는 구현되지 않았다.

## 2026-09-12 독립 변형 Query 50개 추가 평가

- 기존 재현 가능 Motif Harness가 `motif-100`, `motif-200`, `motif-300`의 총 300개까지 완료됐음을 확인했다. 실제 측정이 76개뿐인 과거 `query-100-evaluation-report` 주장은 이 누계에서 제외했다.
- runner에 `motif-350`을 추가하고 기존 300개 source와 중복되지 않는 새 원형 10개 × 변형 5종의 50개를 생성·실행했다. suite별 사례 수가 보고서 제목과 방법 설명에 반영되도록 고정된 “100개” 문구도 일반화했다.
- 이번 corpus 분포는 KYSing 30, 일반 MusicXML 20, PDMX 0 Query였다. 다음 50개 규모 suite에서는 PDMX 누락을 막도록 작은 suite 전용 corpus quota를 명시한다.
- 결과는 workId 기준 Top1 39/50, Top5 50/50, 미회수 0이다. 2위 11건의 1위는 모두 동일 제목의 다른 파일/판본이므로 제목 기준 Top1은 50/50이다.
- XML/Verovio 렌더는 50/50 성공했다. 두 사례는 alignment coverage 90%였으나 실제로 요청한 target 9개는 XML과 SVG에서 모두 해결됐다.
- 평균 검색 37.96초, p50 35.08초, p90 72.94초, 최대 96.37초였다. 다음 단계는 개별 곡 보정이 아니라 canonical 작품/판본 정답 집합 도입과 후보 검색·평가 지연 개선이다.

## 2026-09-13 사용자 사례 지식베이스 보완

- 기존 사례 JSON은 Query·설명·진단에는 적합하지만 대부분 앞뒤 문맥의 재현용 악보와 음표 단위 의미 라벨이 없어 미묘한 음악적 판단을 축적하기에는 부족하다고 판정했다.
- 기존 정본을 유지하면서 사례별 `context.musicxml`, 기계 판독용 `events.json`, JSON의 `knowledgeBase` 메타데이터를 추가하는 구조를 도입했다.
- MusicXML을 표기 재현 정본으로, compact event snapshot을 검색·비교용으로 사용한다. Music Analysis Canonical IR 전체를 복제하지 않으며 안정된 Canonical event ID가 생기면 외부 참조로 연결한다.
- 현상 유형, 음악적 기능, 적용 문맥, 제외 조건, 후보 규칙과 반례를 분리해 특정 작품 예외가 아닌 일반 규칙과 회귀 fixture로 재사용할 수 있게 했다.
- 자동 Motif suite에도 같은 계약을 적용하는 `capture-motif-contexts.mjs`를 추가했다. 한 원형의 다섯 변형은 원형별 MusicXML/event bundle을 공유하고, 자동 판정은 `automatic-unreviewed`로 명시해 사람의 음악적 판단과 섞지 않는다.

## 2026-09-13 일일 메타데이터 수집

- KY 공식 조회 100개를 실행해 번호 정확 일치와 비어 있지 않은 제목을 갖춘 100개를 신규 저장했다. 누적 905개, cursor 905, 미처리 12,143개이며 오류는 없었다. 원본 XML과 검색 DB는 변경하지 않았다.
- YouTube worker는 state의 Pacific date 2026-09-12에 search call 100회가 이미 기록되어 안전 한도 95회를 넘었으므로 네트워크 요청 없이 종료했다. 신규 매칭·no-match는 0이고 cursor 490을 유지했다.

## 2026-09-14 일일 메타데이터 수집

- KY 공식 조회 100개를 실행해 100개를 신규 저장했다. 누적 1,005개, cursor 1,005, 미처리 12,043개이며 429·차단·반복 오류는 없었다. 원본 XML과 검색 DB는 변경하지 않았다.
- YouTube는 Pacific date 2026-09-13 기준 안전 한도 95회를 실행해 신규 대표 영상 90개와 no-match 5개를 기록했다. 누적 videoId 560개, cursor 585이며 quota/반복 오류는 없었다. 검색 DB 동기화는 수행하지 않았다.

## 2026-09-13 KY 공식 메타데이터 자동 수집

- 예약 시간을 놓친 뒤 같은 날짜에 수동 재개했다. 공식 조회 100개가 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 905개, cursor 905, 미처리 12,143개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-13.md에 저장했다.

## 2026-09-14 KY 공식 메타데이터 자동 수집

- 예약 시간을 놓친 뒤 같은 날짜에 수동 재개했다. 공식 조회 100개가 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 1005개, cursor 1005, 미처리 12,043개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-14.md에 저장했다.

## 2026-09-14 Creator Pre-clearance Phrase/Motif 공통 연동

- 사용자 요청: 구조 분석기의 Phrase 또는 Motif를 모두 사용하고, 분석기 업데이트가 사전검토에 반영되도록 한다.
- 작곡 Harness의 현재 실행 코드가 이 저장소의 phrase-boundaries.mjs를 공유함을 확인했다. 복사본 대신 직접 import하는 어댑터를 추가했다.
- 입력/이벤트/설정 및 parser/analyzer/adapter 버전 지문을 저장하는 불변 스냅샷과 재분석 계획을 구현했다. 과거 결과와 수정값을 자동 덮어쓰지 않는다.
- Phrase/Motif ID, family, 겹침 관계, 원본 이벤트, 마디 label/ordinal, 미보정 근거를 보존한다. 동일 구간의 두 계층은 검색 task 하나로 묶는다.
- 자동 Harness에서도 사용하는 오프라인 prepare-preclearance-structure CLI를 추가했다. 실제 S-STRUCT-003에서 23개 unit, 22개 준비 Query를 생성했다.
- 관련 테스트 39개 통과. 감사/ADR: docs/creator-preclearance-audit.md.
- 현재 단계는 검색 준비까지다. 중요도 선정, 실제 검색/작품 집계, 원본 MIDI/XML 업로드, corpus 갱신 worker는 후속 구현이다.

## 2026-09-14 Creator Pre-clearance 선별·검색·작품 집계

- Phrase/Motif의 반복·길이·정보량·겹침을 기준으로 최대 7개 대표 Query를 선별하는 오프라인 모듈을 추가했다. 선별 이유와 보류 이유를 보존한다.
- 기존 searchDatabase를 그대로 호출한다. 원본 beat가 있으면 Query의 박절 위상을 보존하고, 동일 source의 자가 검색은 기본 제외한다.
- source/canonical work 단위로 묶고 최고 구간 유사도를 대표로 사용한다. 정렬된 query event의 합집합으로 coverage를 계산하고 중복 일치를 가산하지 않는다.
- 후보 구조 importance와 corpus distinctiveness가 미보정이라 reviewPriority는 null로 보존한다. 기존 occurrenceImportance를 구조 중요도처럼 표시하지 않는다.
- 각 Query, 정렬 음표, 마디/성부, 점수 근거, 실행 시간을 JSON으로 보존하고 Markdown 요약 도구를 추가했다. 이후 실행은 task별 checkpoint도 저장한다.
- 관련 테스트 46개 통과. 실제 코퍼스 검증은 evaluation/runs/preclearance-search-2026-09-14.json에 저장한다.
- 실제 실행 완료: 7개 Query, 28개 작품 그룹, 370.8초. ENDLESS LOVE의 다른 세 판본 모두 100점으로 회수됐다. 판본 통합 ID 부재와 부분 구간 고득점/낮은 전체 coverage 사례를 한계로 기록했다.
- 사람이 읽을 Query·순위 보고서: docs/creator-preclearance-search-evaluation-2026-09-14.md. 자동 검색 결과이지 전문가 적절성 판정은 아니다.
- 원본 업로드 UI, MIDI/XML 정규화, 운영 job 관리, 전체 corpus 구조 갱신은 아직 후속 작업이다.

## 2026-09-14 사전검토 1단계 실행 안정화·속도 검증

- 지난 370.8초 실행의 박자 조회 201.43초, 후보 회수 140.33초를 확인했다. 기존 박자 영속 캐시의 cold/warm 비용을 구분한다.
- 지속형 검색 worker, 구간 timeout, SIGINT/SIGTERM 취소와 worker 재생성을 추가했다.
- 입력/분석/코드/설정/인덱스 manifest와 task별 원자적 저장을 도입했다. 완료 구간만 재사용하고 실패 구간은 다시 검색한다. 살아 있는 작업의 lock은 덮어쓰지 않는다.
- token count 2MiB와 후보 목록 32MiB의 분리 LRU를 추가했다. 후보 상한·순서·채점·정렬은 유지한다. 사전검토 CLI에서만 기본 활성화한다.
- 관련 신규·기존 회귀 123개 통과. 실제 7개 Query의 전체 검색 결과가 cache-off와 동일했다.
- 관측 합계: off 169.3초, 최종 첫 실행 66.0초, 재사용 35.2초. 시스템 및 기존 캐시 효과를 포함하므로 일반 성능 보장으로 해석하지 않는다.
- 실제 무재검색 resume 0.018초, 설정 변경 재사용 거부, timeout 후 성공 재시도를 확인했다.
- 상세: docs/preclearance-stage1-performance.md. 다음은 검증된 작품·판본 관계를 이용한 통합이다.

## 2026-09-14 사전검토 2단계 작품·판본 registry

- 별도 work-identities registry, 충돌 검증, 인덱스/메타데이터 변경 시 보류, 미검토 후보 생성을 추가했다.
- ENDLESS LOVE 세 편성은 원본 XML 제목/작곡가와 다중 exact 구간을 확인해 연결했다. 원본 파일 지문과 검토 주체를 기록했고 사람 확정 라벨은 사용하지 않았다.
- 사전검토 집계에 적용: 28→26 그룹, 판본 3→작품 1. 23개 일치 구간과 전체 match 총수·점수·alignment를 보존했다.
- registry 변경은 job manifest에 반영한다. 과거 검색 결과는 재검색 없이 별도 보고서로 재집계할 수 있다.
- 관련 테스트 17개 통과. 일반 텍스트 검색의 판본별 표시는 바꾸지 않았다.
- 상세: docs/preclearance-stage2-work-identities.md. 결과: evaluation/runs/preclearance-grouped-2026-09-14.json.

## 2026-09-15 사전검토 3단계 구조 중요도 비교 검증

- 승인 서비스 용량 오류로 중단됐던 구현을 재개했다. 일반 샌드박스 초기화는 여전히 실패해 승인된 실행 환경에서 검증했다.
- 입력/후보에 같은 구조 어댑터를 적용하고, 전체 성부의 반복·음가·박자와 Phrase/Motif 관계를 별도 근거로 저장한다. 구조상 미확인 항목은 null로 남긴다.
- 후보 조각의 ID 대신 onset+MIDI를 전체 성부에 연결한다. 중간 음표를 제외한 가짜 모티프는 만들지 않는다.
- 관련 25개 테스트 통과. 실제 26그룹/30성부/56구간 중 50구간 완료, 5,000음 초과 3성부의 6구간 보류. 보강 실행 약 5.27초.
- 입력 및 후보 스냅샷 28개 약 9.70MB 저장. 기존 순위·점수·coverage·targets·alignment 불변 확인.
- 최종 Copyright Infringement Report 요구사항과 관할별 원작/편곡/판본/녹음 권리 분리 원칙을 문서화했다. 75년 단순 면책은 구현하지 않는다.
- 현재 오프라인 도구이며 운영 UI/자동 갱신에는 아직 연결하지 않았다. 다음은 긴 성부 worker 및 검토 우선순위 검증이다.
- 상세: docs/preclearance-stage3-importance.md. 결과: evaluation/runs/preclearance-importance-2026-09-15.json.

## 2026-09-15 문서 구조화·인수인계 및 긴 성부 worker

- docs/README.md를 프로젝트 전체 문서 지도로 정리했다. 현재 상태(SYSTEM_STATUS.md), 설치/데이터/재현(REPRODUCIBILITY.md), 계약, 실행 근거, 역사/계획을 구분한다. 기존 파일을 이동하지 않아 링크를 보존했다.
- 루트 README의 초기 synthetic corpus/향후 n-gram 등 오래된 설명을 현재 상태와 구분했다.
- Git에 없는 DB/원본/수집 메타데이터와 권한, Node/lockfile, 환경변수, 데이터 hash, 코드 revision/dirty patch의 인계 필요성을 명시했다. 새 환경 클린 복원 미검증과 전체 corpus one-command rebuild 미완성도 기록했다.
- 구조 분석을 중단 가능한 worker로 옮겼다. 기본 성부 60초·50,000음, 취소/timeout 처리, 제한 옵션과 실행 설정 지문 저장을 추가했다. 후처리 전체 deadline이나 구조 resume를 구현한 것으로 주장하지 않는다.
- 회귀 29개 통과. 보류 6개를 포함한 56개 구간 모두 완료. 기존 성공 50개 중요도와 전체 검색 점수/순위/targets/alignment/coverage 불변 확인.
- 새 결과 preclearance-importance-worker-2026-09-15.json 및 스냅샷 31개(35.71MB)를 보존했다. 이번 warm 보강 실행 약 2.02초.

## 2026-09-15 사전검토 우선순위 v1 실험

- 기존 검색 순서/유사도는 유지하고 별도 priorityReview.ranking을 계산한다. 구조·정렬 비율·후보 연속성·Query 내부 정보량을 곱셈 계수로 사용한다.
- 중복 판본/구간 점수는 합산하지 않고 최고 match 근거를 남긴다. 권리 조정은 하지 않으며 누락 구조는 needs-review다.
- 관련 35개 테스트 통과. 26그룹/56match 실제 평가, 기존 works 내용 불변 확인.
- ENDLESS LOVE 1위 유지. Chorale와 Lamentatio의 2/3위 역전은 정보량 감점 때문이며 전문가 적절성 미확인 사례로 기록했다.
- corpus 희귀도는 아직 null이다. Query entropy를 관용구의 실제 빈도나 법률적 침해 가능성으로 표현하지 않는다.
- 문서 지도/현황/재현 절차를 갱신했다. 상세 docs/preclearance-stage4-priority.md, 결과 evaluation/runs/preclearance-priority-2026-09-15.json.

## 2026-09-15 코퍼스 원본 빈도 기반 A/B

- 기존 i5 토큰에 대해 top-k가 아닌 전체 index의 source document frequency를 읽기 전용으로 측정한다. 파트/voice/반복은 source당 1회 집계하고 판본은 별도임을 명시한다.
- 초기 반복 JOIN 조회는 60초 timeout. ID→source 대응표를 한 번 읽는 방식으로 바꾸고 180초 제한 worker에서 다시 실행했다. 의미는 동일하며 메인 DB 변경은 없다.
- 95,813 source, 64개 패턴 측정 완료, 75.43초. df 47~62,268. 26개 작품/56개 match에 별도 corpusPriorityReview를 저장했다.
- 관련 회귀 40개 통과. 실제 소형 SQLite에서 파트/반복 중복 집계 방지를 확인했다. baseline report 전체 불변 확인.
- 검토 순위 변화는 없었다. 품질 향상 입증 전이며 사이트에는 적용하지 않았다. 원본 파일 빈도와 전체 멜로디/작품 희귀도, 법률적 침해 판단을 구분한다.
- 상세 docs/preclearance-stage5-frequency.md, 결과 evaluation/runs/preclearance-frequency-2026-09-15.json. 문서 지도/현황/재현 절차 연결 완료.

## 2026-09-15 유형별 재현 Query·사람 검토 Harness 파일럿

- 반복음/순차진행/분산화음 유사/혼합도약 각 3개, 총 12개 연속 8음 Query와 앞뒤 문맥 이벤트를 보존했다. 원형·반음수정·옥타브변형, humanReview와 knowledgeBase 필드를 분리했다.
- 초기 편성 중복이 많은 실행은 중단하고 파일을 보존했다. 검증된 canonical 또는 title/artist 선별 키로 유형 내 작품 다양성을 보강했다. 검색 병합 규칙은 바꾸지 않았다.
- 관련 회귀 43개 통과. 개선된 suite에서 원형 4개를 실제 검색했다. 3개는 60초 timeout, 도약형은 55.32초에 원본/구간 3위 회수. 원형 네 개는 같은 작품이므로 독립 작품 검증으로 해석하지 않는다.
- 나머지 8개 미실행, 전문가 판정/악보 렌더링 검증 미실행을 명시했다. timeout은 원곡 미회수로 판정하지 않는다.
- suite.json, 사례별 결과/오류, summary.json을 evaluation/runs/preclearance-review-diverse-2026-09-15에 보존했다. 검토 문서 docs/preclearance-review-pilot-2026-09-15.md, 실행 계약 docs/preclearance-stage6-review-harness.md.
- 다음 우선 작업은 짧은 Query 처리시간의 단계별 진단이다. 판정 논리나 정답 순위 고정 없이 timeout 전 진행 계측을 추가해야 한다.

## 2026-09-15 timeout 전 진행 계측·실제 응답 불변 검증

- 선택적 trace 콜백과 worker progress 통신을 추가해 SQL/후보/decode/exact/alignment/박자/구조 단계 기록을 부모 JSONL에 보존한다. 기본 검색 논리는 변경하지 않았다.
- 진행 메시지가 완료로 처리되지 않고 timeout 이전에도 보존되는 회귀를 추가했다. 관련 12개 파일/120개 테스트 통과.
- 반복음 사례 trace 재실행 40.20초 완료. engine profile의 박자 조회 19.04초, postings 8.72초, local alignment 0.74초. 후보 키 2,534/성부 1,509.
- 이후 warm trace-off 4.63초, 박자 조회 0.107초. 전체 JSON 직렬화 API 응답이 시간 profile 외에는 동일함을 확인했다. 순차 실행이므로 개선 배율로 주장하지 않는다.
- 박자 timeline의 pending cache가 검색 종료 시 저장되는 점을 확인했다. timeout 시 미저장 cache 손실 가능성이 있어 다음은 안전한 batch 저장 검증이다. 이번에는 저장 정책을 바꾸지 않았다.
- docs/preclearance-stage7-search-tracing.md, evaluation/runs/preclearance-trace-repeat-2026-09-15 및 preclearance-trace-verification-2026-09-15.json에 보존했다.
# 2026-09-15 — Motif 다중 증거 유사도 v0.2

- 기존 같은 배열 위치끼리 비교하던 Motif 가족 점수를 동적 정렬 기반 비교기로 교체했다. 조옮김 불변 음정, 윤곽, 반복/순차/도약 음형, 정규화 음가·IOI, metric strength, 정렬 coverage를 개별 evidence로 보존한다.
- 결합 점수는 melodic 40%, shape 20%, rhythm 25%, coverage 15%다. 이는 미보정 휴리스틱이며 정답 확률이 아니다.
- 장식음 삽입·누락, 반복음 확장, 음높이 대체, 리듬 변화, 조옮김, 긴 종결음 길이 변화를 transformation tag로 설명한다.
- Motif 상세 패널은 결합 점수뿐 아니라 멜로디·음형·리듬·정렬 범위와 감지된 변형을 따로 표시한다.
- `docs/README.md`를 문서 진입점으로 추가해 현재 기준 문서, 구현 설명, 날짜순 기록, 역사 문서를 구분했다. 기존 문서는 사례 링크를 깨지 않도록 이동하지 않았다.
- 회귀 검사는 완전 조옮김, 장식음 삽입, 긴 종결음 길이 변형을 포함한다. Beam transport와 exact signature 없는 sliding-window 후보 생성은 다음 단계다.

## 2026-09-15 — Beauty and the Beast Motif 가족 과잉 병합 수정

- `S-STRUCT-002`의 34개 `four-short-plus-long-arrival` 후보가 rhythmFamily 문자열 하나 때문에 모두 Motif 1의 prime 변형으로 강제되던 원인을 확인했다.
- rhythmFamily를 후보 생성 근거로만 낮추고, 가족 자동 재사용에는 결합 유사도 84 이상과 coverage 70 이상을 요구한다. 짧은 동일 길이 구간의 delete+insert 정렬이 다른 음형을 과대평가하지 않도록 gap cost도 0.48로 높였다.
- 표기는 prime 누적 대신 가족-변형 번호인 `Motif 1-1`, `Motif 1-2`, `Motif 2-1`을 사용한다. 같은 변형의 재등장은 같은 표기를 쓰되 occurrence ID는 독립적이다.
- 실제 34개 후보는 6개 가족 후보로 분리됐다. 이는 정답 가족 수가 아니라 이전의 강제 단일 가족 오류가 해소됐다는 진단 결과다.
- 관련 악보·event snapshot은 기존 `S-STRUCT-002` 자산을 재사용하고 사용자 피드백, 원인, 일반화 규칙, 실행 결과를 evaluation case에 추가했다. 대상 테스트 36개와 production build가 통과했다.

## 2026-09-15 — 주요 Motif 목록과 악보 가족 통합

- 오른쪽 목록을 악보의 motifSpans에서 집계하도록 연결했다. 가족별 횟수, 형태별 대표 악보·등장 위치, 전체 선율 attack 대비 비중을 표시한다.
- 중복 occurrence와 가족 내 겹치는 attack은 한 번만 계산하고 tie continuation은 분모·분자에서 제외한다. 비중은 중요도나 지속시간 점수가 아니다.
- 각 등장 위치 선택을 악보/상세 패널과 연결하고, 변형별 대표 구간으로 기존 타 작품 검색을 유지했다.
- 관련 테스트 25개와 production build 통과. 상세 계약: docs/motif-family-summary.md.

## 2026-09-15 — S-STRUCT-004 부분 Motif, 호흡 기호, 주기 투영 경계

- 원본 XML과 이벤트 snapshot 및 사용자 해석을 `evaluation/cases/s-struct-004-review.md`에서 연결한다.
- 내부 rhythm-cell을 containedFragments로 보존하고 실제 fermata/breath-mark/caesura를 경계 증거로 연결했다. 사용자 가정의 페르마타는 기보 사실로 추가하지 않았다.
- 후속 질문에서 반복 주기 투영이 짧아진 타이 뒤의 쉼을 넘어 새 음형을 포함함을 확인했다. 수정 승인 후 `long-arrival-rest-v1`을 추가해 긴 도착음+실제 쉼으로 시간 기반 투영 끝을 검증한다.
- 실제 두 번째 occurrence는 index 8..17에서 8..15로 줄고 D#5의 전체 타이 음가는 유지된다. 특정 work ID, 음높이, 마디 번호로 분기하지 않는다.
- 관련 45개 테스트 통과. 기준, 한계와 남은 Phrase 검토 사항은 `docs/structure-review-004.md`에 모았다.

## 2026-09-15 — Motif rhythm-cell의 앞부분 복구

- 기존 Motif 4-1의 누락된 미–파#를 확인했다. 고정 4개 짧은 음+긴 음 창이 23마디 음형 중간에서 시작한 것이 직접 원인이었다.
- 쉼으로 시작이 확인되는 연속 짧은 앞부분만 복구하는 `rest-anchored-short-pickup-v1`을 추가했다. core/complete 시작과 규칙 ID를 별도 증거로 보존한다.
- 수정 범위는 75..79에서 73..79이다. 기존 비교 기준으로 Motif 3-3 후보(91/100, coverage 78%)가 된다. 화성적 Prolongation은 아직 확정하지 않는다.
- 원본 문맥과 사용자 의견, 일반 규칙 및 한계는 S-STRUCT-004 사례와 `docs/structure-review-004.md`에 통합 기록한다.
## 2026-09-16 — 장식음 두 개 삭제 파일럿 완료

- 현재 검색을 바꾸지 않고 원형 7개 × 원형/1음 삭제/2음 삭제 = 21개 검색을 검증했다. 세 조건 모두 원본 파일 Top5 7/7이다.
- 두 음 삭제의 지정 원래 구간 회수는 6/7. 가장 무도회는 같은 선율의 반복 구간 22–26마디를 1위로 찾아 곡 회수와 위치 회수를 구별했다.
- XML 약박·짧은 순차진행 후보만 삭제했으며 확정 Schenker 분석으로 부르지 않는다. 삭제 음가도 제거한다. 전부 4/4의 떨어진 두 음이며 연속 삭제는 미검증이다.
- 긴 쉼이 포함된 초기 v1을 중단하고 입력 품질 조건을 강화한 v2로 검증했다. 동일 환경·Query의 8개 결과는 출처를 기록해 재사용하고 13개를 새로 실행했다.
- Query, 삭제 근거, XML 문맥/좌표, 원본 해시, 전체 검색 결과 및 악보 비교 페이지를 보존했다. docs/double-ornament-trial-v1.md가 경위와 최종 v2 자료의 진입점이다. 알고리즘·운영 설정은 변경하지 않았다.
## 2026-09-16 — 장식음 두 개 삭제 추가 30회 검증

- 기존과 겹치지 않는 10개 구간(5곡·8개 고유 음표열)의 원형/1음/2음 삭제 검색을 완료했다. 원본 Top5는 10/10, 10/10, 8/10이다. 오류·재시도 0건.
- 미회수 2건은 같은 Query의 반복 위치다. 원본 후보 진입 뒤 잘못된 위치 창 평가 및 admission-floor 탈락 정황을 보존했다. 특정 곡 규칙이나 점수 완화는 추가하지 않았다.
- 대표 구간과 반복 목록, 보존 음표 대응을 구별하는 audit.json과 검사 스크립트를 추가했다. Query·XML 문맥·삭제 근거·전체 응답·30개 악보/소리 페이지를 보존한다.
- 사전 20%p 하락 기준에 따라 전용 확장은 보류하고 후보 위치 검색을 후속 진단 대상으로 남겼다. docs/double-ornament-additional-v3.md 및 해당 REVIEW.md 참조.

## 2026-09-16 KY 공식 메타데이터 자동 수집

- 예약 시간을 놓친 뒤 같은 날짜에 수동 재개했다. 공식 조회 99개가 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 1104개, cursor 1104, 미처리 11,944개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-16.md에 저장했다.

## 2026-09-17 — 짧은 Query 90회 완료

- 이전 20곡을 제외한 원형 10곡(3/4 세 곡, 4/4 일곱 곡)의 12/8/6음 원형·음높이 변경·장식음 삭제를 검색했다. 시간초과 2건 재시도 후 전부 완료했다.
- 원본 파일 Top10: 원형 10/10·10/10·9/10, 음높이 변경 10/10·6/10·2/10, 삭제 8/10·0/10·0/10. 동일 작품 다른 판본 상위 회수와 파일 순위는 구분한다.
- 미회수 원인을 엄격 조건 충돌, 후보 축소, 같은 음정의 다른 리듬 구간 선택으로 나눴다. 진짜 Exact가 앞서서 생긴 정상적인 순위 저하와 Exact 과대분류도 분리했다.
- Query·변형 근거·앞뒤 XML·전체 응답·순위·진단·제안을 90개 독립 케이스로 보존했다. 180개 악보 비교 페이지와 길이별 Top5/Top10 표 제공. 스키마/참조/해시 및 Query 변형 검증 통과.
- 사용자 지시에 따라 개선은 통합 보류 목록 EVAL-001..008에 누적하고 운영 검색에는 적용하지 않았다. 상세: docs/short-query-90-v1.md.

## 2026-09-17 — 국소 옥타브·복합 변형 평가 마무리

- 비교 페이지에서 순위를 쉽게 확인하도록 상단 요약표·사례별 원형/입력 Query 순위 배지·상위 10개 결과 표를 추가했다. 원본 파일은 별도 강조하고 10위 밖이어도 실제 순위로 표시한다. 검색 재실행이나 계산법 변경 없이 저장 응답을 사용한다.

- 대조 10개, 단일 옥타브 10개, 옥타브+장식음 삭제 10개 모두 원본 파일 Top5. 최초 시간초과 1건 재시도 완료.
- 사용자의 평가 기준대로 1위 유지가 아닌 상위권 회수를 긍정적으로 평가한다. 변경 음의 deletion/다른 음 대응은 순위와 분리해 근거를 기록했다.
- 60개 비교 악보와 30개 독립 케이스 묶음 생성, 스키마·참조·해시 검증 통과. 개선안은 통합 보류 목록에 누적하고 운영 검색 코드는 변경하지 않았다.
- 승인 검토 경로 실행이 복구되어 보고서 작업을 완료했다. 일반 sandbox 실행의 helper_unknown_error는 여전히 재현된다.
- 상세: docs/octave-combination-20-v1.md.

## 2026-09-16 — 기억 입력 변형 50개 + 대조 15개 완료

- 원형 10개에서 다섯 변형을 순차 실행했다. 변형 50/50 및 원형 10/10 원본 파일 Top5, 역순 대조 0/5 원본 회수. 오류/재시도 0회.
- 회수 성공과 별개로 음 끝 쉼표 변형이 Exact 100점에 포함되는 판정 문제, 긴 음이 반복된 짧은 음으로 잘못 대응되는 사례를 확인했다. 운영 알고리즘은 변경하지 않고 일반화 가능한 개선안을 기록했다.
- 독립 export에 65개 Query 사례, 10개 앞뒤 XML/event snapshot, 전체 응답·순위·문제·제안·실행 지문을 보존했다. 스키마/참조/해시 검증 통과.
- 비교 악보 130개와 소리 페이지 제공. 브라우저 런타임 문제로 전체 화면 시각 검증은 미완료이며 자동 SVG ID/정렬 인덱스 검증과 구분한다.
- 상세 결과: docs/memory-variation-50-v1.md. 이후 사용자/자동 테스트도 동일한 케이스 보존 계약을 적용한다.

## 2026-09-16 — 수집 모델·오탐 처리 기준

- KY 메타데이터와 YouTube 대표 영상 수집은 반복·고처리량 업무이므로 GPT-5.6 Luna를 기본 모델로 사용하도록 예약 작업 prompt에 명시했다. 수집기가 결정적으로 수행하는 HTTP/XML 처리 자체에는 모델을 개입시키지 않는다.
- KY 페이지의 일반 HTML 스크립트에 포함될 수 있는 `captcha` 단어를 차단으로 오인하지 않도록 script/style 제거 후 보이는 차단 문구만 검사한다. 실제 차단·429·반복 오류가 아니면 사용자가 요청한 범위에서 재개한다.

## 2026-09-17 — 일일 메타데이터 수집

- KY 공식 조회 100개를 Luna 기준 자동화로 실행해 100개를 신규 매칭했다. 누적 1,204개, 미처리 11,844개이며 원본 XML과 검색 DB는 변경하지 않았다.
- YouTube 대표 영상은 Pacific 날짜 2026-09-16에 95회 검색해 88개를 매칭하고 7개는 no-match로 기록했다. 누적 레코드 875개, videoId 833개이며 quota/차단 오류는 없었다.
- 상세 목록과 결과는 `docs/ky-collection/2026-09-17.md`, `docs/ky-collection-log.md`, `docs/youtube-collection-log.md`에 보존했다.

## 2026-09-18 — 일일 수집 중단

- KY 공식 수집은 15회 조회·15개 신규 매칭 후 저장 단계 `UNKNOWN` 파일 열기 오류가 반복되어 중단했다.
- YouTube 수집은 실행하지 않았다(호출·quota 0). 검색 DB 동기화와 원본 XML 변경은 없었다.

## 2026-09-18 — 수집 재개 및 YouTube 저장 오류

- KY 공식 수집을 기존 한국 날짜 상태(dailyRequests 15)에서 재개해 85회 조회·85개 신규 매칭을 완료했다. 누적 1,304개, 미처리 13,048개이며 검색 DB와 원본 XML은 변경하지 않았다.
- 이어 Pacific 날짜 2026-09-17의 YouTube 수집을 95회 한도로 시작했다. 3회 호출 중 2개 매칭이 저장되고 no-match는 0개였으며, 누적 unique videoId는 797개다.
- 세 번째 처리 후 `data/youtube-backfill-state.json` 저장 단계에서 `UNKNOWN: unknown error, open ...`이 발생해 안전 중단했다. API 키는 노출하지 않았고 추가 재시도·우회·검색 DB 동기화는 수행하지 않았다.

## 2026-09-18 — 수집 재개 완료 및 저장 안정성 보완

- KY 수집 저장은 직접 덮어쓰기 대신 같은 디렉터리의 임시 파일을 기록·동기화한 뒤 교체하는 원자적 checkpoint 방식으로 바꿨다. `UNKNOWN`, `EBUSY`, `EPERM`, `EACCES` 파일 열기·교체 오류에는 3회의 짧은 제한 재시도를 적용하며, 실패해도 기존 JSON은 보존한다.
- 이 보완 뒤 KY는 남은 한국 날짜 한도 85회 조회·85개 신규 매칭을 정상 완료했다. 오늘 합계는 100회·100개 신규 매칭, 누적 1,304개이고 원본 XML·검색 DB는 변경하지 않았다.
- 같은 오류가 YouTube state 저장에서도 재현되어 YouTube cache/state에도 동일한 원자적 저장·제한 재시도를 적용했다. 이후 남은 92회 호출을 정상 완료했고 Pacific 날짜 2026-09-17의 state는 95/95 calls, cursor 970, lastError 없음으로 끝났다.
- 이 날짜의 영속 결과는 영상 89개와 no-match 5개(94개)다. 초기 직접 저장 방식이 실패한 호출 1회는 결과를 보존하지 못했으므로 호출 수 95와 결과 수가 다르며, quota를 이중 사용하지 않기 위해 재호출하지 않았다. 누적 cache는 969개 레코드·879개 고유 videoId다. 검색 DB 동기화는 수행하지 않았다.

## 2026-09-18 — 회귀 테스트·규칙 변경 모델 역할 고정

- 프로젝트 사용자 에이전트 `musicanote_regression_tester`를 GPT-5.6 Terra / medium으로, `musicanote_search_rule_engineer`를 GPT-5.6 Sol / high로 정의했다.
- Terra는 고정 suite 실행과 증거·handoff 작성만 맡으며 점수식·후보 규칙을 직접 변경하지 않는다. Sol은 재현 가능한 handoff와 음성 대조군을 근거로 일반 규칙만 수정하고 재검증·문서화를 수행한다.
- 반복 수집은 기존 예약 작업의 GPT-5.6 Luna 역할을 유지한다. 상세 계약은 `docs/agent-model-routing.md`에 기록했다.

## 2026-09-18 — 소규모 회귀 3종 v1 (Terra / medium)

- 대량 변형 테스트는 일시 중단하고 실제 2/4 corpus passage `ICH LIEBE DICH`에서 6개 고정 Query를 실행했다. Exact·리듬(원형, 전체 음가 x2, 국소 음가·쉼표 변화), 못갖춘마디·약박·마디 경계 시작, 음정/리듬 음성 대조군을 각각 포함한다.
- 원형·전체 음가 x2·국소 음가/쉼표 변화·동일 음정/다른 리듬·시작 위치 Query는 모두 원형 stream을 Top3 또는 Top2로 회수했고, 변경 멜로디/동일 리듬 음성 대조군은 Top100에서 원형을 회수하지 않았다. 모든 회수 결과의 XML target ID/SVG audit도 완결됐다.
- 이 한 passage에서는 예외적인 오탐·누락 회귀를 확인하지 않아 Sol 규칙 변경 handoff를 만들지 않았다. 전체 음가 x2가 리듬 회수·순위는 유지하면서 일부 비리듬 표시 성분을 바꾸는 관찰만 남겼으며, 독립 사례가 반복되기 전에는 규칙을 바꾸지 않는다.
- 최종 근거는 `evaluation/runs/small-regression-triad-v1-final/`과 `docs/small-regression-triad-v1.md`에 보존한다. 앞선 `small-regression-triad-v1` 및 `-retry`는 평가 runner의 source identity 참조 오류 진단본으로, 증거 집합에서 제외한다.

## 2026-09-19 — EVAL-001 엄격 Exact 리듬 판정 반영

- 허용적 IOI/rhythm similarity를 검색 회수·유사 순위용으로 유지하면서, 사용자에게 표시하는 Exact 분류에는 실제 note duration과 silent gap/rest를 따로 비교하는 `strictExactRhythmMatch`를 적용했다.
- 전 곡이 같은 속도로 연주된 경우를 위해 하나의 공통 템포 배율은 허용한다. 반면 일부 긴 음의 끝을 쉼표로 바꾸거나 내부 쉼표를 sustain으로 합치는 국소 재분배는 Exact로 인정하지 않는다. tie query는 logical attack으로 합친 뒤 검사한다.

## 2026-09-19 — 일일 KY·YouTube 수집

- KY 공식 메타데이터는 한국 날짜 한도 100회 조회를 모두 사용해 100개를 신규 매칭했다. 누적 1,404개, cursor 1,404, 남은 미처리 XML 13,048개이며 검색 DB와 원본 XML은 변경하지 않았다.
- YouTube 대표 영상은 Pacific 날짜 2026-09-18에 95회 검색하여 91개를 매칭하고 4개를 no-match로 저장했다. 누적 작품 레코드는 1,064개, 고유 videoId는 960개, cursor는 1,065다.
- quota·차단·반복 오류는 없었다. 두 수집 모두 원자적 checkpoint 저장 경로를 사용했고, API 키는 출력·기록하지 않았다.
- `absoluteExactOnly` Melody + Rhythm 결과도 엄격 판정을 통과해야 한다. 일반 Similar 후보 생성, DTW 점수, admission, 순위식은 변경하지 않았다.
- 고정 memory 사례의 원형 10/10은 Exact 유지, 음가→쉼표 변형 10/10은 Exact에서 제외됐다. 실제 DB MEM01은 원형 1위/Exact 100 유지, 변형 1위/Similar 97로 회수 순위는 유지됐다.
- `server/search-api.test.js`의 74개 테스트가 모두 통과했다. 공통 템포 배율, 내부 쉼표, sustain 대체, 종결 쉼표, tie 정규화 회귀를 포함한다.

## 2026-09-19 — EVAL-002 긴 음 도착·점유 정렬

- Melody + Rhythm local alignment에서 긴 Query 음이 짧은 반복음으로 치환되는 비용과 직전 실제 대응 음부터의 도착 간격을 비교한다. 긴 음 누락이 발견된 경우에만 가까운 시작점 최대 4개를 재평가한다. 후보 생성, Exact 분류, admission 및 결과 순위식은 그대로 유지했다.
- MEM10-absorb-ornament 재검색에서 64마디 4.5박의 0.5박 음으로 밀린 시작점이 64마디 1박의 3박 음으로 복구됐다. 다음 3박 음도 실제 긴 음에 대응하고, 사이 장식음은 삽입으로 남는다. scoped 결과는 97점, rhythm 약 97.9점이었다.
- 원형·전체 템포 x2의 정렬은 100, 장식음 흡수는 원래 긴 음 대응을 유지하며 77.5, 첫 긴 음을 짧게 바꾼 대조군은 53.2였다. `server/search-api.test.js` 75/75, `npm test -- --run` 431/431, `npm run build` 통과.
## 2026-09-21 — Phrase 기반 Motif v1

- Phrase 전체 후보를 기본으로 유지하고 내부 쉼/긴 도착음과 작품 전체 반복 지지로 세분화하는 경로를 연결했다. 미분할은 확정 Motif가 아니라 내부 분할 보류로 표시한다.
- 기존 다중 증거 비교기를 재사용하고 64 attack 거리 제한 없이 후속 Phrase의 재등장/변형을 비교한다. 상위 Phrase, 대응 구간, 버전, 탐색 한도를 저장한다.
- 화성 사례는 원본 문맥/대안/검토 상태를 가진 case와 독립 검증이 필요하며, 이번 버전에는 화성 학습/경계 가중치를 추가하지 않았다.
- 계약·제한·검증은 docs/phrase-first-motif-v1.md에 통합한다. 기존 사례 자산은 변경하지 않는다.
## 2026-09-21 — FIND THE WAY Phrase 경계 후처리 순서 수정

- S-STRUCT-005에 원본 MusicXML/444개 이벤트/변경 전 분석과 사용자 의견을 보존했다.
- 짧은 articulation gap을 경계로 선택한 뒤 minimum-attack 규칙이 진짜 종결 경계를 억제하는 원인을 수정했다. 가까운 지속 도착음+더 긴 쉼이 있을 때만 내부 경계를 먼저 낮춘다.
- 31/37/43 억제,33/46 유지 및 반복 구간77 억제/79 유지 회귀를 추가했다. 원본15마디 마지막 음은 E-natural로 사용자 설명과의 차이를 기록했다.
- 상세 기준/한계: docs/phrase-articulation-v1.11.md. 화성 해결과 beam 자체를 새로 해석한 것은 아니다.
## 2026-09-21 — 기준박 대비 Phrase 종결 v1.12

- 고정16분음표 길이가 아니라 박자에서 추정한 기준박과 주변 음가에 대한 상대 길이로 짧은 종결을 판단한다. 박자 미상/비대칭에서는 보류한다.
- FIND THE WAY의84/132/136 경계를 하위 후보로 낮춰8+9 및15–17 병합 의견을 반영했다. 일반 규칙으로119/128도 추가 병합되는 영향은 명시한다.
- 원본 사례는S-STRUCT-005를 재사용하며 상세는 docs/phrase-relative-closure-v1.12.md에 기록한다.
## 2026-09-21 — Phrase v1.13 긴 쉼 보호

- S-STRUCT-006 When We Disco XML/431개 이벤트/변경 전 분석과 사용자4–6마디 경계 의견을 보존했다.
- 기준박 대비 긴 쉼을 반복 연속성/준비부 처리로 지우지 않게 보호한다. 반복 relation은 유지하며 연속성만 구별한다.
- 내부의 작은 쉼은 가까운 종결·긴 쉼·재등장 모두가 확인되는 경우에만 보정한다. Phrase1의 최초 경계는index13(8마디 시작)이 된다.
- 기준/한계/재현 자료: docs/phrase-long-rest-v1.13.md.
## 2026-09-21 — Phrase v1.14 지속 종결 보호

- When We Disco11마디의2.5박 종결음+2.5박쉼을 보호하도록 v1.13을 보완했다. 내부9마디 호흡과13마디의 완전 반복 대응도 일반 조건으로 정리했다.
- Phrase2는8–11마디, Phrase3는12–14마디. 원본 S-STRUCT-006과 전체문맥을 재사용하며 설명/기준은 docs/phrase-sustained-closure-v1.14.md에 보존했다.
## 2026-09-21 — 반복 Phrase 구조 보정 기획

- beam/rest/기준박 관찰과 작품별 공통 구조를 이용한 상위 경계 보정 계획을 docs/REPEATED_PHRASE_STRUCTURE_PLAN.md에 통합했다.
- 기존 경계 동결→관찰 adapter→템플릿 정렬→shadow 제안→검토→선택적 적용의6단계를 정의했다. 자기 결과를 근거로 재학습하는 순환과 보호 경계 침범을 방지한다.
- 이번에는 문서만 작성했다. 분석 코드·현재 Phrase 결과·원본 악보는 변경하지 않았다.
## 2026-09-22 — 반복구조 A 기준 고정/B 관찰 초안

- S-STRUCT-006을v1.14로 재분석하여 불변 baseline을 만들고 Phrase4/5와 결합안의event 범위를 보존했다.
- 원본 beam/rest/tie 관찰과source mapping 초안을 추가했다.431음표 전부 연결,4/8/12/16마디의3+4 beam 묶음을 확인했다.
- numeric onset/tie-chain/meter/cross-staff 한계를 명시했으며 화면분석에는 연결하지 않았다. 진행 현황은 REPEATED_PHRASE_STRUCTURE_PLAN.md와 사례문서에 통합했다.

## 2026-09-22 — When We Disco / 철없던 사랑 직접 비교

- 두 KYSing 작품의 자동 Phrase 및 연속 window 탐색에 더해 전체 stream 직접 정렬을 실행했다. 대표 대응은 When We Disco 4–5마디와 철없던 사랑 23–24마디로, local 88.1196, interval 98.1, rhythm 81.875, contour 85.7143, skeleton 83.6131, structural 100이었다.
- scopeWorkIds가 이미 회수된 q-gram hit만 거르는 문제를 수정했다. 명시적 작품 비교에서는 지정 work를 full-scan 후보로 반드시 평가하며, 일반 코퍼스 검색 후보 수와 규칙은 바꾸지 않는다.
- 수정 뒤 대상 작품은 평가되지만 반복음 비중이 높은 대표 Query는 기존 low-information-floors에서 제외됐다. 반복음 오탐 방지 하한은 유지하고, 향후 두 작품 직접 비교에서는 경고와 원시 근거를 표시하는 방향을 기록했다.
- 정본 사례는 evaluation/cases/q-pair-001-when-we-disco-cheoleopdeon-sarang.json, 상세 결과와 악보 링크는 docs/when-we-disco-cheoleopdeon-sarang-comparison.md에 보존했다.
- server/search-api.test.js는 새 scoped 후보 회귀를 포함해 93개가 통과했다. 기존 catalog text search 1개는 대형 DB에서 5초 timeout으로 실패했으며 이번 후보 수정과 무관하다.

## 2026-09-22 — 복합 기억 변형 Motif 400 기획

- 기존 Motif 100·200·300·350과 source가 겹치지 않는 자동 원형 20개를 고르고, 최근 사용자 사례를 반영한 다섯 변형을 각각 적용하는 100개 baseline을 추가했다.
- 유형은 짧은 내부음 1개 생략·시간 보존, 서로 떨어진 짧은 내부음 2개 생략·시간 보존, 중간 음높이+국소 리듬 변화, 옥타브 이동+내부음 생략, 지속시간을 보존한 패싱/보조음 추가다.
- 자동으로 짧은 내부음을 고르는 것은 음악학적 장식음 정답 판정이 아니다. 원형과 변형, 전체 Query, 기대 source/work, 상위 결과, 직접 정렬, 강조/XML/Verovio 검증을 모두 저장하고 결과를 본 뒤 일반 규칙 개선 후보를 분리한다.

## 2026-09-22 — Motif 400 복합 변형 100개 실행 결과

- 20개 새 원형×5개 복합 변형을 production search Top100으로 모두 실행했다. 이전 Motif suite와 source 중복은 0이고 KYSing 30, MusicXML 35, PDMX 35개 사례다.
- 전체는 Top1 57, Top5 66, Top10 69, Top100 71, 미회수 29다. 회수 사례 중앙 순위는 1, p90은 3이다.
- 유형별 Top100은 단일 내부음 생략 17/20, 두 내부음 생략 3/20, 음높이+리듬 19/20, 옥타브+생략 16/20, 장식 추가 16/20이다.
- 누락은 직접 정렬도 하한을 넘지 못한 missed-admission 13건과 직접 정렬은 가능하지만 후보에 들지 못한 missed-retrieval 16건으로 분리됐다. 20%에 해당하는 두 음 생략은 경계 밖 변형으로 보고 즉시 허용 규칙을 추가하지 않는다.
- 원본 앞뒤 2마디 MusicXML/event snapshot 20개를 evaluation/motif-400/base-assets에 저장하고 100개 case의 knowledgeBase에 연결했다. 전체 Query와 실행 결과는 evaluation/motif-400/cases.jsonl 및 evaluation/runs/motif-400-latest.json, 사람이 읽는 결과는 docs/motif-400-search-evaluation.md에 보존했다.
- 97/100은 excerpt XML과 Verovio 검증을 완료했다. 나머지 3개는 기대 결과 미회수 후 fallback XML이 없었던 경우다. 평균 20.3초, p50 19.4초, p90 32.9초, 최대 58.1초로 성능 개선 필요가 남았다.

## 2026-09-22 — YouTube 구형 매칭 격리와 기본 재생 성부

- HAKUNA MATATA 상세 화면에 제목 단어만 같은 Zanzibar 쇼츠가 연결된 사례를 감사했다. 활성 매칭 1,053개 중 작곡가 검증이 명시된 항목은 1개뿐이어서 구형 캐시 전체를 신뢰할 수 없는 것으로 판정했다.
- 기존 캐시는 삭제 전에 `data/youtube-quarantine/`에 복구 가능한 원본으로 격리하고 활성 캐시는 schema v2 빈 상태로 초기화했다. 화면은 validationVersion 2 또는 수동 검증 항목만 사용한다.
- 신규 자동 수집은 90초 미만 영상을 무조건 제외한다. shorts/shortvideo/viral/trending 등 쇼츠·바이럴 표기도 제외하고, 작곡가 정보가 있으면 후보 제목·채널·설명의 작곡가 단서가 일치해야 한다.
- 일반 탐색·텍스트 검색·직접 상세 진입은 같은 MusicXML의 가장 위 Part/Staff/Voice를 재생 기본값으로 선택한다. 선율 검색 결과에서 들어온 경우에만 검색된 stream을 그대로 유지한다.
- HAKUNA MATATA 회귀 확인에서 일반 진입은 `P1:1:1`, 검색 전용 진입은 기존 `P1:2:2`를 유지했고 양쪽 모두 구형 YouTube ID가 노출되지 않았다.
- 재수집 목록은 파일명 전용 inventory 대신 검색 DB의 작품별 title·composer·sourceId를 사용한다. 실제 숫자로 시작하는 제목을 보호하기 위해 파일 순번 제거는 `숫자. 공백` 형식에만 적용한다.

## 2026-09-22 — 긴 Query 장식음 2개 생략 길이 임계값

- 같은 원형의 같은 두 장식음 후보를 삭제한 뒤 최종 Query 길이를 8·10·12·14·16·18음으로 맞춘 짝 비교 66건을 실행했다. 삭제 음가는 직전 생존음에 합쳐 전체 박자 길이를 보존했다.
- 현재 운영 검색(single omission 활성)만 사용했으며 2음 생략 전용 검색 규칙은 추가하지 않았다. Top100 회수는 각각 4/11, 4/11, 5/11, 5/11, 7/11, 7/11이었다. 가장 큰 상승은 14→16음 구간이다.
- 18음에서 회수 가능한 7개 원형만 보면 16·18음 7/7, 12·14음 5/7, 10음 4/7, 8음 4/7이었다. 따라서 이번 편의 표본에서는 16음 이상을 보수적 허용 구간, 10–14음을 고유성과 리듬 정보가 충분할 때만 허용하는 조건부 구간, 8음을 기본 제외 구간으로 기록한다.
- 4개 원형은 18음에서도 미회수됐으므로 길이만으로 2음 생략을 허용하지 않는다. 후보 생성, admission-floor, sparse-alignment를 분리 진단해야 한다. 시간 초과 2건은 원본 실패 기록을 보존하고 한 번 재시도했다.
- 표본은 11개 원형이지만 고유 작품/원본 파일이 5개뿐이고 반복 구간이 포함된다. 장식음 판정도 짧은 음가·약박·순차진행 휴리스틱이므로 전체 성능으로 일반화하지 않는다.
- 재현 자료: `evaluation/reports/double-omission-length-sweep-v1/suite.json`, `results.json`, `REPORT.md`, `index.html`, 전체 응답은 `evaluation/runs/double-omission-length-sweep-v1/`에 보존했다.

## 2026-09-22 — 4/4 짧은 장식음 3·4개 추가 실험

- 서로 다른 XML 감사 원본 15개에서 원음 16개를 사용해 원형 15건과 장식 변형 60건을 실행했다. 추가음은 모두 16분음표 이하이며 host 음가 또는 쉼표를 줄여 뒤 음의 시작 위치와 전체 박자 길이를 보존했다.
- 사용자의 지적에 따라 여러 위치의 분산 3·4음은 핵심 성공 조건이 아니라 강한 스트레스 대조군으로 재분류했다. 분산형 실패를 검색 결함이나 규칙 완화 근거로 사용하지 않는다.
- 핵심 평가인 한 위치의 turn-like 장식군은 3음 11/15, 4음 12/15가 Top100에 회수됐으며 회수 결과는 모두 Top10이었다. 회수 결과 평균 총점은 각각 90.4와 90.5다.
- 분산 스트레스 대조군은 3음 9/15, 4음 4/15가 회수됐다. 분산 4음 미회수 11건 중 9건은 후보 단계에서 빠져 여러 위치의 음정 연쇄 변화가 후보 생성에 큰 영향을 주는 것을 확인했다.
- 국소 장식군 미회수는 admission-floor, query-coverage, sparse-alignment로 갈렸다. 다음 개선 후보는 기둥음 정렬을 먼저 고정하고 한 위치의 짧은 삽입군만 제한적으로 흡수하는 방법이며, 오탐 대조군 검증 전에는 운영 규칙을 바꾸지 않는다.
- 회수된 분산 Query 13건은 원형과 함께 추가음을 붉게 표시한 `evaluation/reports/ornament-addition-75-v1/index.html`에 모았다. 전체 Query·변형 근거는 `suite.json`, 병합 결과는 `results.json`, 전체 검색 응답은 세 shard의 `evaluation/runs/ornament-addition-75-v1-shard-*`에 보존했다.

## 2026-09-22 — 한 위치 장식음 수 3–6개 임계값 실험

- 서로 다른 4/4 MusicXML 원본 15개에서 각각 16음 원형을 만들고, 같은 host 음 안의 동일한 0.5박 구간에 장식음 3·4·5·6개를 넣었다. 뒤 음의 onset과 Query 전체 길이는 유지했으며, 총 75개 Query를 실제 운영 검색으로 실행했다.
- 원형 대조군은 15개 중 14개가 회수됐다. 원형부터 회수되지 않은 OC11은 변형 성능 분모에서 제외하여, 변형 결과는 평가 가능한 14개 원형만 기준으로 삼았다.
- Top100 회수율은 3개 12/14(85.7%), 4개 11/14(78.6%), 5개 9/14(64.3%), 6개 3/14(21.4%)였다. 회수된 3·4음 사례는 모두 Top10에 있었고, 가장 큰 하락은 5→6음에서 나타났다.
- 미회수의 주된 판정 단계는 `query-coverage`와 `admission-floor`였으며 일부는 `sparse-alignment`가 함께 작동했다. 따라서 3–4개는 비교적 안정적, 5개는 조건부 경계, 6개는 현재 검색기에서 강한 변형으로 기록한다. 이 결과만으로 운영 하한이나 흡수 규칙은 변경하지 않았다.
- 장식 개수별 음형이 완전한 prefix 관계가 아니므로 개수 효과에 장식군의 종결 방향·contour 효과가 일부 섞였다. 또한 휴리스틱으로 만든 반음계 보조음이므로 화성적으로 타당한 장식음 정답을 뜻하지 않는다. 다음 검증에서는 동일 음형 prefix, 기둥음 고정, 비슷하지만 다른 작품의 오탐 대조군을 함께 사용해야 한다.
- 첫 병렬 실행 도중 검색 DB 크기 변경이 감지되어 안전 중단했고, 해당 실행은 `*-interrupted-db-change`로 격리했다. 이후 고정 DB에서 재실행했으며 60초를 넘긴 16건만 180초 한도로 재시도했다. 이는 평가 실행 제한 변경일 뿐 검색 점수·후보·순위 논리는 바꾸지 않는다.
- 재현 자료: `evaluation/reports/ornament-count-sweep-v1/suite.json`, `results.json`, `REPORT.md`, `index.html`. 전체 검색 응답은 `evaluation/runs/ornament-count-sweep-v1-*`에 보존했다.

## 2026-09-22 — 단일 악보 음별 삭제 민감도 시험

- CAN'T SMILE WITHOUT YOU 바이올린의 원형 16음을 한 음씩 제거한 16개 변형과 원형을 전체 코퍼스에서 검색했다. 삭제 음가는 바로 앞 이벤트에 흡수해 이후 onset과 전체 Query 길이를 유지했으며, 첫 음만 다음 이벤트에 흡수했다.
- 원형은 1위·100점이었다. 9번 B4(35마디 1박, 2박 길이)를 삭제하면 원곡이 Top100에서 사라졌다. 6·7·8번 삭제는 각각 약 18.2·17.5·20.1점, 13·14번은 약 14.6·8.8점 하락했으며 나머지는 0–3점 하락하고 1위를 유지했다.
- 7–9번과 13–14번은 긴 음·강박이라는 검색과 독립적인 특징도 강해 기둥음 검토 후보가 된다. 반면 6번은 8분음표 길이의 약박 F♯4인데도 크게 하락했다. 이는 기둥음 자체보다 pickup 또는 정렬 연결음의 삭제가 interval 경로를 두 곳 바꾼 영향일 수 있어 검색 민감도를 음악이론 정답으로 바로 사용하면 안 된다는 실제 반례다.
- 독립 특징은 검색 실행 전에 고정했으며, 검색 결과로 중요도 레이블을 학습하거나 운영 규칙을 바꾸지 않았다. 이 실험은 leave-one-note-out 엔진 진단이고 Schenker 분석 정답이 아니다. 다음 판단에는 악보 검토 또는 별도의 Phrase/화성 분석 레이어가 필요하다.
- 재현 자료: `evaluation/reports/single-note-ablation-cant-smile-v1/suite.json`, `results.json`, `REPORT.md`, `index.html`; 전체 검색 응답은 `evaluation/runs/single-note-ablation-cant-smile-v1-shard-*`에 보존했다.

### 사용자 악보 검토 후 판정 정정

- 위 실행의 결론 상태를 `inconclusive-invalid-query-boundary`로 낮췄다. Query의 1·2번 F♯–G는 앞 Phrase 종결이며 하나의 완결된 Phrase/Motif 표본이 아니다.
- 33마디 끝의 6번 F♯는 사용자 검토상 없어도 무방한 낮은 중요도 음이지만 삭제 시 18.2점 하락했다. 검색 민감도가 음악적 기둥 중요도를 과장한 거짓 양성 사례로 기록한다.
- 시작·끝 음 삭제는 interval 하나, 내부 음 삭제는 두 interval을 바꾸며, 삭제 음가를 앞 이벤트에 흡수하면 sustain까지 변한다. 그러므로 위치별 raw 점수 하락은 직접 비교 가능한 중요도 척도가 아니다.
- 34마디의 7·8번이 Motif 종결부라는 검토와 민감도 방향은 일치하지만 위 교란 요인이 통제되지 않아 신뢰성 근거로 채택하지 않는다. 이 파일럿은 검색 규칙 학습·하한 조정·기둥음 레이블 생성에 사용하지 않는다.
- 다음 시험의 선행 조건은 사람 검토를 거친 완전한 Phrase, 동일 위치 비용 대조군, 삭제로 생기는 1개/2개 interval 변화의 정규화, sustain 변화와 음고 부재를 분리한 변형이다.

### 앞 두 음과 선행 쉼표 제거 후 재실험

- 사용자 검토에 따라 앞 Phrase의 종결인 F♯–G와 그 앞의 쉼표를 제거하고, 33마디 1.5박의 B3부터 시작하는 14음 Query로 다시 실행했다. 원형은 1위·100점이었다.
- 사용자가 없어도 무방하다고 본 33마디 마지막 F♯(새 4번)는 삭제해도 1위를 유지했고 총점 하락은 5.9점이었다. 잘못된 경계를 포함했던 첫 실행의 18.2점 하락보다 크게 완화됐다.
- 34마디 Motif 종결부인 새 5·6번은 각각 5.9점과 20.3점 하락했다. 같은 종결 기능 안에서도 민감도가 크게 달라 raw 하락값이 곧 음악적 중요도라는 가정은 성립하지 않았다.
- 첫 실행에서 Top100 밖이었던 B4는 새 7번으로 이동한 뒤 삭제해도 1위·80.5점으로 회수됐다. 새 12번 A4(36마디 3박) 삭제만 Top100 밖이었다. 앞 경계 두 음의 제거만으로 민감도 지도가 크게 바뀌었다.
- Query가 약박에서 시작해 이번 실행의 Downbeat 점수가 모두 0이므로 박자 중요도 검증 자료로는 사용하지 않는다. 내부 음 삭제가 두 interval과 인접 sustain을 함께 바꾸는 교란도 남아 있다.
- 이 재실험은 Phrase 경계 정정 효과와 현재 진단법의 불안정성을 확인한 것이다. 운영 검색 규칙이나 기둥음 가중치는 변경하지 않았다.
- 재현 자료: `evaluation/reports/single-note-ablation-cant-smile-trimmed-v2/suite.json`, `results.json`, `REPORT.md`, `index.html`; 전체 검색 응답은 `evaluation/runs/single-note-ablation-cant-smile-trimmed-v2-shard-*`에 보존했다.

#### 사용자 음악적 검토

- upbeat 라–파♯ 사이의 솔이 빠질 때 큰 변화가 생기는 것은 해당 솔의 박자 위치를 고려하면 음악적으로 타당할 수 있다.
- 34마디 파♯은 바로 앞에 같은 파♯이 있으므로 하나가 빠져도 영향이 작을 수 있으며, 뒤의 긴 음들은 상대적으로 결과에 더 큰 영향을 줄 가능성이 있다.
- 이 설명은 일부 결과를 납득하게 하지만, 삭제 반응에는 박자 위치·동일음 반복·음가·앞뒤 interval 변화·인접 sustain 변화가 함께 섞인다. 따라서 leave-one-note-out을 중요음 분류기로 사용하지 않고, 독립적인 Phrase·metric·화성 분석 결과를 점검하는 보조 진단으로만 유지한다.

## 2026-09-23 — 일일 KY·YouTube 수집

- KY 공식 조회 100개를 실행해 100개 모두 번호 정확 일치와 비어 있지 않은 제목 조건으로 신규 저장했다. 누적 1,804개, cursor 1,804, 미처리 11,244개이며 429·차단·오류는 없었다.
- KY 원본 XML과 검색 DB는 변경하지 않았다. 신규 목록은 `docs/ky-collection/2026-09-23.md`에 보존했다.
- YouTube는 Pacific 날짜 2026-09-22의 95회 한도를 사용해 작품 레코드 82개에 대표 영상을 저장하고 13개를 no-match로 기록했다. 신규 고유 videoId는 31개, 활성 캐시 누적은 videoId 89개/고유 34개/no-match 14개다.
- YouTube quota·rate-limit·저장 오류는 없고 검색 DB 동기화는 수행하지 않았다. 다만 같은 정규화 제목과 작곡가를 가진 편성별 work가 결과 videoId는 공유하면서도 API 검색은 반복해 호출하는 효율 문제를 확인했다.
- 다음 실행부터 validation v2의 정규화 제목+작곡가가 같은 solo~quartet 편성은 API 호출 전에 저장 결과를 재사용하도록 수정했다. 영상 매칭은 날짜와 무관하게 재사용하고, no-match는 같은 Pacific 날짜 안에서만 공유해 다음 날 재시도 가능성을 보존한다. `scripts/youtube-backfill.test.js` 7개가 통과했으며 수정 검증 중 API 호출은 하지 않았다.

## 2026-09-23 KY 공식 메타데이터 자동 수집

- 일일 자동화로 공식 조회 100개를 실행했으며 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 1804개, cursor 1804, 미처리 11,244개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-23.md에 저장했다.

## 2026-09-24 — 일일 KY·YouTube 수집

- KY 공식 조회 100개를 실행해 100개 모두 신규 매칭했다. 누적 1,904개, cursor 1,904, 미처리 XML 11,144개이며 오류는 없다. 목록은 `docs/ky-collection/2026-09-24.md`에 보존했다.
- YouTube는 Pacific 날짜 2026-09-23의 검색 호출 95/95를 사용했다. 같은 제목·작곡가의 편성별 API 결과를 재사용하여 작품 레코드 263개를 처리했고, 영상 217개/no-match 46개를 기록했다. 신규 고유 videoId는 78개다.
- 활성 YouTube 캐시 누적은 작품 366개, videoId 보유 306개, 고유 videoId 112개다. quota·저장 오류는 없었다. KY 원본 XML과 검색 DB는 변경하지 않았다.

## 2026-09-24 KY 공식 메타데이터 자동 수집

- 일일 자동화로 공식 조회 100개를 실행했으며 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 1904개, cursor 1904, 미처리 11,144개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-24.md에 저장했다.

## 2026-09-25 — 다파트 악보 상세 화면의 페이지 자동 조정

- Symphony No.9 Op.125 (`work-5dcac52a40ce6cc9-6111b523`)는 20파트인데 기존 상세 화면은 5파트 이상을 모두 동일한 2100×3100 페이지와 21 배율로 처리했다. 이 때문에 한 시스템의 일부 오선이 페이지 경계 밖으로 밀릴 수 있었다.
- MusicXML의 실제 오선 수(`<staves>` 포함)를 기준으로 9개 이상이면 페이지 높이를 단계적으로 늘리고 배율을 조정한다. 20오선에서는 2100×6220, 배율 18을 사용하며 작은 악보의 기존 배치는 유지한다.
- Verovio가 해당 원본 XML을 새 설정에서 38쪽으로 조판했고, 38쪽 모두 시스템 하단 좌표가 페이지 하단 여백 안에 들어오는 것을 확인했다(최대 57,684 / 허용 60,100). 악보 레이아웃 회귀 테스트 17개와 전체 빌드도 통과했다. 다른 다파트 작품의 시각적 검토는 계속 필요하다.

## 2026-09-25 KY 공식 메타데이터 자동 수집

- 일일 자동화로 공식 조회 100개를 실행했으며 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 2004개, cursor 2004, 미처리 11,044개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-25.md에 저장했다.

## 2026-09-25 — KY·YouTube 일일 수집

- KY 공식 번호 100개를 조회하여 100개를 신규 매칭했다. 누적 2,004개, 미처리 11,044개이며 오류는 없었다. 목록은 `docs/ky-collection/2026-09-25.md`에 저장했다.
- YouTube는 API 키가 설정되어 있으나 Pacific 날짜 2026-09-24의 95/95 검색 한도와 quotaExceeded 기록이 있어 이번 실행에서 API를 호출하지 않았다. 신규 영상과 no-match는 모두 0개다. 활성 videoId는 543개(고유 193개), cursor 630이다.
- KY 원본 XML과 검색 DB는 변경하지 않았다. KY 메타데이터 수집 결과도 검색 DB에 별도로 동기화하지 않았다.

## 2026-09-25 — source-conditioned 화성 레이어 브리지

- `server/harmony-overlay-api.mjs`를 추가해 현재 work의 원본 악보 SHA-256으로 `Music Analysis` RomanText catalog의 overlay artifact를 조회한다.
- 제목·작곡가 유사성으로 주석을 붙이지 않는다. exact score hash가 없으면 `no_audited_source`, 동일 hash의 해석이 여러 개면 `multiple_interpretations`, catalog가 꺼져 있으면 `harmony_catalog_unavailable`로 보류한다.
- `FullScorePage` 오른쪽에 `화성 분석(실험)` 패널을 추가했다. 곡마다 기본 OFF이고 사용자가 켤 때만 요청하며, 읽기 전용이다.
- 로마숫자 label만 Campania를 사용하고 `unknown`은 일반 글꼴을 유지한다.
- 이 레이어는 원자료 주석 검토용이며 Phrase·Motif·Cadence·Pillar 계산에 전달하지 않는다. 악보 음표 위 span 색칠은 Canonical event ID ↔ Viewer note ID 매핑 회귀 테스트 뒤의 별도 단계다.
- 검증: `pnpm build` 통과. 현재 검색 DB의 일반 MusicXML에는 RomanText corpus와 byte-identical 원본이 없어 안전하게 `no_audited_source`를 반환하는 사례도 확인했다.

## 2026-09-25 — 악보 상세 화면의 화성 모호 구간 검토

- 모든 unrestricted score detail 화면에서 `HarmonyOverlayPanel`을 기본 활성화하고 진입 즉시 exact score-hash 기반 source harmony를 조회한다.
- 전체 화음을 나열하는 대신 `harmony-overlay-artifact-0.3.0`이 지정한 `review_candidate`만 먼저 표시한다. 사용자는 필요할 때만 `전체 화성도 보기`를 켠다.
- 모호 구간 카드에는 마디·beat, Roman label, 우선순위, 표면 일치율, chord-tone duration, 전후 화음을 표시한다. Roman label에만 Campania를 쓰고 `unknown`에는 적용하지 않는다.
- 구간별 의견 종류와 설명을 상세 화면에서 바로 저장한다. `/api/analysis/harmony-feedback`은 work의 score SHA-256, catalog record, annotation ID를 재검증한 뒤 8766 append-only review API로 전달한다.
- source가 정확히 일치하지 않는 악보에는 화성을 추측해 표시하지 않으며, 검증 자료가 없다는 compact 상태를 보여 준다.
- 이 레이어는 계속 `structure_influence=none`이다. 저장된 의견도 adjudication 전에는 화성 규칙·Phrase·Motif에 자동 반영하지 않는다.
- `pnpm run build` 통과.
## 2026-09-25 — exact 주석 조회에서 전곡 blind 자동 화성 분석으로 전환

- 동일 score hash의 원자료만 보여 주던 패널이 사용 목적과 다르다는 사용자 검토를 반영했다. exact-source 레이어는 감사용 보조 자료로 내리고, 모든 unrestricted 악보에 `blind-full-score-harmony-v0.1` 결과를 공급한다.
- 모든 파트·staff·voice의 attack/sustain을 읽어 전곡 화성 span을 생성한다. Phrase 경계와 source harmony label은 입력으로 사용하지 않는다.
- 조표의 관계장·단조, 전곡 음 지속 scale fit, 기능 화음 coverage, 마지막 tonic 후보로 미보정 key hypothesis를 만들고 절대 화음을 Roman 후보로 투영한다.
- Viewer는 자동 화성 개수, 조성 후보, 로마숫자, 절대 화음, span, template fit, 경쟁 후보를 보여 준다. Campania는 Roman label에만 적용한다.
- 검토 큐는 low fit, 작은 후보 margin, 3음 누락, dense/NCT 가능성을 사용하되 작품당 최대 80개 및 전체 span의 약 10%로 제한한다. 짧은 span이라는 이유만으로 검토 후보로 만들지 않는다.
- 자동 분석 의견은 `data/harmony-feedback/automatic-harmony-review.jsonl`에 append-only 저장한다. chord/key/extent/NCT 오류를 구분하며 adjudication 전에는 training과 rule update에 사용하지 않는다.
- Phrase·Motif·Pillar에는 아직 전달하지 않으며 `structure influence none`을 유지한다.
- 예시 HAKUNA MATATA: 전체 자동 화성 span 530개, 우선 검토 큐 53개, 전곡 조성 후보 C major. span 과분할과 조성 보정은 annotation evaluation의 다음 과제다.
- boundary harmony 단위 테스트 9개 및 `pnpm run build` 통과.
## 2026-09-25 — 자동 화성 항목 클릭 시 악보 구간 강조

- 오른쪽 `자동 화성 분석 · 실험` 목록의 화성 항목을 선택하면 해당 `[start, end)` 시간 범위를 악보 위에 호박색 반투명 띠로 표시한다.
- 선택된 구간의 첫 시스템으로 자동 스크롤하고 약 1초간 점멸한다. 여러 오선 시스템을 가로지르는 구간은 시스템별 띠로 나누되 하나의 화성 구간으로 취급한다.
- 화성 시작 시점에 이미 울리고 있는 최상성부 음을 시작 앵커에 포함해, 첫 attack이 늦게 등장하는 구간도 한 점으로 축소되지 않게 했다.
- 표시는 시간 범위 탐색용이다. 범위 안의 모든 음을 화음 구성음으로 단정하지 않으며, 이 의미를 툴팁에 기록했다.
- HAKUNA MATATA `work-104a3e7d61b751c7`의 6마디 자동 화성 구간으로 검증했다. 두 시스템 구간 폭은 약 86px/39px였고 자동 중앙 이동 및 `harmony-range-flash`가 확인되었다.

## 2026-09-25 — 전곡 화성 기본 표시와 Cadence 후보 레이어

- `NOTHING BUT THE BEST` (`work-cc8751218e58213a`)에서 화성이 띄엄띄엄 보인 주된 원인은 분석 누락이 아니라 UI가 전체 188개 중 우선 검토 17개만 기본 표시한 것이었다. 이제 전체 자동 화성을 기본 표시하고, 체크를 해제할 때만 모호·우선 검토 후보로 좁힌다.
- 실제 공백도 구분한다. 서로 다른 pitch class가 2개 미만인 구간이나 chord-template fit이 0.38 미만인 구간은 v0.1이 억지로 라벨을 만들지 않는다. 쉼·단선율·매우 불확실한 수직음향이 대표적이며, 화면 설명에도 이 조건을 명시했다.
- 기존 `boundaryHarmony.records[].selectedCadence`를 읽어 `Cadence 후보` 목록을 추가했다. 새로운 정답을 발명하지 않고 현재 Phrase 경계 분석이 선택한 HC·IAC 등의 미보정 가설만 노출한다.
- Cadence 항목을 선택하면 준비화음 시작부터 도착화음 끝까지를 파란색으로 표시하고 첫 구간으로 자동 이동하며 약 1초간 점멸한다. 화성 span의 호박색 강조와 시각적으로 구별한다.
- 이 곡에서 전곡 화성 188개, 우선 검토 17개, Cadence 후보 13개를 확인했다. 첫 HC 선택 시 두 개의 렌더링 구간과 `cadence-range-flash`가 실제 브라우저에서 확인되었다.
- Cadence는 아직 전곡 독립 탐색 결과가 아니라 **지원 가능한 Phrase 경계 주변 후보**다. 조성·로마숫자·Cadence 점수 모두 annotation calibration 전 가설이며 구조 분석 입력으로 되먹이지 않는다.
- 검증: production build 통과, `boundary-harmony`, `FullXmlNotation`, render-contract 테스트 26개 통과.

## 2026-09-25 — 작은따옴표 MusicXML 화성 파싱 호환

- `Piano Sonata No. 8 in C minor, Op. 13, 1st movement` (`work-474e82a835aa3acb`)에서 악보·구조 정보는 나오지만 자동 화성이 0개인 문제를 재현했다.
- 원인은 원본 MusicXML이 `id='P1'`, `number='1'`, `type='start'`처럼 작은따옴표 속성을 사용한 반면, 임시 화성 이벤트 어댑터가 큰따옴표 속성만 정규식으로 인식한 것이었다. 음표나 화성 내용의 결손이 아니었다.
- part ID, measure number, tie start/stop을 작은따옴표와 큰따옴표 모두에서 동일하게 읽도록 일반화했다. 특정 작품명·작곡가·마디에 의존하는 예외는 추가하지 않았다.
- 수정 후 해당 작품에서 전 성부 sounding event를 읽어 자동 화성 848개, 우선 검토 80개, Phrase 경계 Cadence 후보 10개, 전곡 조성 후보 C minor를 생성했다.
- 브라우저에서 전체 848개 표시와 첫 HC(7마디 4.5박) 선택 시 파란 Cadence 구간 강조를 확인했다.
- 작은따옴표 part/measure/tie fixture를 추가했고 관련 테스트 11개가 통과했다.

## 2026-09-25 — 화성 피드백의 Roman 교정 후보와 문맥 저장

- 사용자가 1마디 화성에 `이 화음은 [viio/V] 화음으로 뒤따르는 V 화음에서 해결됩니다`라고 저장한 레코드가 `automatic-harmony-review.jsonl`에 존재함을 확인했다. 기존 v0.1 레코드는 comment를 보존하지만 `trainingEligible=false`, `ruleUpdateEligible=false`라 다음 분석에 자동 사용되지 않는다.
- v0.2부터 대괄호 안의 Roman 표기를 `human.romanLabels`와 `human.suggestedRomanLabel`로 구조화한다. 슬래시 화음은 `secondary-function` case tag를 받지만 adjudication 상태는 `pending`, retrieval도 비활성 상태다.
- 선택 화음만이 아니라 바로 앞·현재·다음 자동 화성의 ID, span, 위치, 선택 후보를 `hypothesis.context`에 저장한다. 따라서 `viio/V → V` 해결 문맥을 승인 단계에서 검증할 수 있다.
- 단일 사용자 의견이 즉시 규칙을 바꾸거나 gold label이 되는 것은 금지한다. 승인된 유사 사례가 모인 뒤에만 case retrieval 또는 ranker calibration 후보로 승격한다.
- 입력창은 일반 글꼴을 유지하고, 대괄호 표기 미리보기와 저장 의견에서 대괄호 **안의 Roman 토큰만** Campania를 사용한다. 일반 문장과 brackets는 기존 글꼴이다.

## 2026-09-26 KY 공식 메타데이터 자동 수집

- 일일 자동화로 공식 조회 100개를 실행했으며 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 2104개, cursor 2104, 미처리 10,944개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-26.md에 저장했다.

## 2026-09-26 YouTube 자동 수집

- Pacific 날짜 2026-09-25의 검색 시도는 실패 호출을 포함한 94회다. 처리 결과는 매칭 217개, no-match 34개이며 편성 재사용 포함 251개다. 금일 결과의 고유 videoId는 79개, 기존 캐시 대비 고유 videoId 순증은 77개(193→270)다.
- Search Queries 분당 quota HTTP 429로 즉시 중단했다. state cursor 882, searchCalls 94이며 우회·재시도는 하지 않았다.
- 활성 캐시는 작품 880개(매칭 760, no-match 120), 고유 videoId 270개다. 원본 XML·검색 DB는 변경하지 않았고 API 키는 기록하지 않았다.

## 2026-09-27 KY 공식 메타데이터 자동 수집

- 일일 자동화로 공식 조회 100개를 실행했으며 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 2204개, cursor 2204, 미처리 10,844개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-27.md에 저장했다.

## 2026-09-27 YouTube 자동 수집

- Pacific 날짜 2026-09-26에 검색 호출 95/95를 사용했다. 매칭 214개, no-match 39개이며 편성 재사용 포함 처리 레코드는 253개다.
- 금일 결과의 고유 videoId는 81개, 기존 캐시 대비 고유 videoId 순증은 78개(270→348)다. 활성 캐시는 작품 1,133개(매칭 974, no-match 159), 고유 videoId 348개, cursor 1,135다.
- quota·rate-limit·반복 오류는 없었고 API 키는 기록하지 않았다. 원본 XML·검색 DB 동기화는 수행하지 않았다.

## 2026-09-27 — Score Tools 기반 계층과 SVG 발췌

- `ScoreSnapshot`, 원본 SHA-256 hash, stable Part/Measure/Event reference, rational timing을 도입했다.
- 원본 불변 `ViewRecipe`/`ExcerptRecipe`와 source-map sidecar를 추가했다.
- 테스트 단계의 export 권한은 전부 허용하되 `ScoreExportPolicy` 인터페이스 뒤에 두어 상용화 시 교체 가능하게 했다.
- 상세 악보 `Score Tools`에서 복수 whole Part, 연속 마디 범위, Remove Lyrics/Dynamics를 선택하고 동일 파생 XML로 SVG를 재조판할 수 있다.
- 선택 Part 전체를 새 MusicXML로 내보내며 파생 결과를 재파싱한다.
- 기존 상세 악보 렌더러와 새 exporter가 같은 지연 로딩 Verovio 런타임을 공유한다.
- 상세 구현 범위와 후속 단계는 `docs/score-tools-development.md`에 기록했다.

## 2026-09-27 — 원본 기준 Transpose Preview

- Verovio 6.3의 interval transpose를 전체 악보, 검색 일치 악보 조각, 이미지 발췌의 `현재 조옮김 적용` 선택에 같은 값으로 적용했다.
- 재생 pitch도 함께 이동하며, 원본 event mapping과 검색 강조는 원조 좌표를 유지한다.
- 조옮김은 원본 기준 절대 recipe라 누적되지 않으며 Reset View 및 작품 전환 시 원조로 복귀한다.
- 이미지 발췌는 체크박스로 현재 조옮김 적용 여부를 정한다. `Current View`/`Original Score` 드롭다운은 후속 UI 정리에서 제거했고, MusicXML은 정책대로 아직 원조만 내보낸다.

## 2026-09-27 — Transpose 반음 이동 교정

- 음정명 선택을 원조 기준 `+7 … +1, 0, -1 … -7` 순서의 반음 선택으로 교체했다.
- Verovio에는 정수 반음 문자열을 전달하며 조표와 악보 본문의 모든 음표를 같은 변환으로 렌더링한다.
- 원조로 되돌릴 때도 빈 transpose 값을 명시적으로 설정해 재사용 toolkit에 이전 상태가 남지 않게 했다.
- 실제 Verovio WASM 출력의 pitch·조표와 `-7`~`+7` 전 범위를 검증하는 통합 회귀를 추가했다.

## 2026-09-27 — 상세 악보 Part View 연결

- Score Tools에서 일부 Part를 체크하면 상세 악보 본문을 그 Part들만 남긴 파트보로 즉시 재조판한다.
- 0개 선택과 전체 선택은 전체 악보로 처리하며, 원본 XML은 수정하지 않는다.
- 같은 Part 체크 상태를 SVG Preview와 선택 Part MusicXML 내보내기에도 사용한다.

## 2026-09-27 — Score Tools 이미지 레이아웃

- 기존 한 줄 SVG를 유지하면서 가로 폭 지정 자동 줄 바꿈, 균등 2~12행, 표시 마디 번호로 지정하는 줄바꿈을 추가했다.
- 출력 폭은 600~3200px로 지정하며, 원본 XML 대신 파생 recipe와 임시 `new-system` 지시에만 저장한다.
- 세부 계약과 검증 방법은 `docs/score-tools-image-layout.md`에 분리해 기록했다.

## 2026-09-27 — Score Tools 이미지 저장 형식

- SVG 외에 PNG, JPG, PDF 저장을 추가했다.
- PNG/JPG는 Canvas에서 변환하며 PDF는 여러 결과 페이지를 한 파일로 묶는다.
- 저장 형식 계약, 래스터 안전 한도와 검증 기준을 `docs/score-tools-image-layout.md`에 기록했다.

## 2026-09-27 — 사용자 검토 반영: Score Tools 3탭과 Measure Image Export 정리

- 사용자 검토 요청은 한 화면에 섞인 기능을 `1. Transpose`, `2. Part Selection`, `3. Measure Image Export`로 분리하고, 비활성 기능·버튼을 숨기며, 조옮김·마디·레이아웃 용어를 실제 사용 의도에 맞추는 것이었다.
- 상단 3탭은 활성 탭의 본문만 렌더링한다. Transpose 탭은 별도 footer/Preview가 없고, Part Selection footer에는 원조 MusicXML 내보내기만, Image 탭에는 이미지 Preview와 Sidecar/Preview/Format/Export만 표시한다.
- Transpose 옵션은 `+7`부터 `+1`, `0 · Original · 원조`, `-1`부터 `-7` 순서로 바꾸고 `Choose how many semitones to raise or lower every note.` 안내를 추가했다.
- `Current View`/`Original Score` 드롭다운을 제거했다. Image 탭의 `현재 조옮김 적용` 체크박스가 켜지면 Transpose 탭의 절대 반음 값을 사용하고, 꺼지면 원조로 추출한다. Part Selection은 양쪽 모두에 적용된다.
- 마디 From/To 드롭다운은 `m.<표시 번호>`와 pickup만 보여 주고 `#ordinal`은 숨겼다. 내부 ordinal 선택은 recipe의 stable start/end measure ID로 변환하므로 표시 단순화가 재현성 계약을 바꾸지 않는다.
- 레이아웃 라벨은 `한 줄`, `가로 폭 지정 자동 줄 바꿈`, `행 수 지정`, `줄 바꿈 마디 직접 입력`으로 정리했다. 행 수는 2~12로 정규화한다. 직접 입력한 표시 번호는 선택 범위에서 유일할 때만 ordinal을 거쳐 stable break ID로 저장하고, 범위 밖·중복 표시 번호는 Preview 전에 차단한다.
- `ExcerptRecipe`를 `1.3.0`으로 올리고 `presentation.targetSystemCount`를 추가했다. `layout`은 `single_system | auto_wrap | system_count | custom_breaks`이고 최종 줄바꿈 위치는 `systemBreakBeforeMeasureIds`에 남긴다.
- 검증: `src/score-tools/model.test.ts` 9/9, Score Tools 단위·Verovio 통합 집중 회귀 4파일 16/16, `npm run build` 통과. 전체 회귀는 613/615가 통과했으며 실패 2개는 이번 범위 밖의 `FullScorePage.test.ts` Motif overlay 기대값이다.

## 2026-09-27 — Verovio Score Tools 휴대형 모듈 인수인계

- `@musicanote/verovio-score-tools` `0.1.0` private repo-local package에 core/image/verovio/react/style entry를 분리했다. npm publish는 하지 않고 `pnpm pack:score-tools` tarball만 사용한다.
- 다른 viewer가 fresh toolkit factory와 임시 DOM normalize hook을 주입할 수 있고 MusicSearch도 public React entry를 소비한다.
- Node 24.19.0/pnpm 11.19.0 재현 절차, pack 설치, API/Props, headless 예제, host 책임, CSS, 권한, browser/SSR, 보안, recipe migration과 known limits를 canonical 문서에 기록했다.
- 검색 DB/API/Canonical IR/YouTube·KY 환경변수는 모듈 개발에 필요하지 않다.
- package 검증은 10개 필수 dist artifact와 실행 가능한 core/image/verovio entry 3개를 확인했고, 집중 테스트 22/22와 모듈·main build가 통과했다.
- Verovio 6.3.0 LGPL-3.0-or-later와 자체 license 미확정 상태를 명시했다.
- 최종 문서: [`VEROVIO_SCORE_TOOLS_PORTABLE_MODULE_FINAL_KO.md`](VEROVIO_SCORE_TOOLS_PORTABLE_MODULE_FINAL_KO.md).
- 이식성 교차 검토에서 React declaration에 남던 잘못된 CSS 상대 import를 제거했다. MusicSearch host와 외부 host는 stylesheet entry를 명시적으로 import한다.
- Verovio 6.3 ESM/WASM subpath의 TypeScript declaration 부재, Node `>=22.12.0`, 검증 스크립트의 실제 범위, Git commit/push 전제와 clean consumer 검증 필요성을 최종 인수인계서에 명시했다.

## 2026-09-27 — Score Tools 0.2.0 Part / Staff / Voice 추출

- 기존 whole-Part recipe를 유지하면서 `PartSelection`에 Part별 Staff ID 또는 Voice ID 선택을 추가했다. 새 계약은 `ViewRecipe 1.1.0`, `ExcerptRecipe 1.4.0`이며 명시적 migration 함수를 제공한다.
- Staff와 Voice를 병렬 범위로 취급한다. Voice가 여러 Staff를 오갈 때 필요한 원래 Staff를 유지하고, Staff 선택으로 cross-staff Voice 일부가 제외되면 경고한다. source voice가 없는 음표는 Voice 1로 추정하지 않고 `Unassigned / Voice not encoded`로 표시한다.
- MusicXML에서 음표만 삭제하지 않고 제거 구간을 `forward`로 표현해 기존 `backup/forward` 시간축을 보존한다. cross-staff chord head 승격, Staff/clef 번호 재배치와 선택 경계의 tie/slur/tuplet/beam/arpeggiation 정리를 수행한다.
- 파생 XML을 다시 읽어 실제 선택 이벤트 수와 pitch/onset/duration/voice가 원본과 같은지 검증한다. 실제 남은 이벤트만 source map에 기록하며 `DerivedScore.staffCount`와 `warnings`도 파생 결과를 기준으로 계산한다.
- `applyScoreViewSelections`, `filterMusicXmlSelections`, engine `filterSelections`를 공개했다. 기존 `applyPartViewSelection`, `filterMusicXmlParts`, engine `filterParts`는 whole-Part 호환 경로로 유지한다.
- `Part / Staff / Voice` 탭의 같은 선택 상태가 상세 악보, Measure Image Export와 MusicXML export에 공통 적용된다. Image 탭은 포함 범위를 요약하고 선택 편집으로 돌아가는 경로를 제공한다.
- `@musicanote/verovio-score-tools` 현재 버전은 `0.2.0`이다. 2026-09-27 Staff/Voice 실제 MusicXML fixture를 포함한 Score Tools 집중 테스트 6파일 28/28, 상세 렌더 계약 19/19, 모듈 빌드와 전체 애플리케이션 빌드가 통과했다.
- 빈 하위 Staff/Voice 선택은 host로 전달하지 않고 마지막 정상 상세 악보를 유지한다. invalid controlled selection은 full score로 조용히 확장하지 않으며, 이미지/MusicXML 출력에 selection transform 경고를 표시한다. convenience filter의 `[]`는 full score로 통일하고 저장 recipe의 명시적 selection 규칙은 유지했다.
- 전체 회귀는 625/627가 통과했다. 실패 2개는 기존 Motif overlay 기대값(`FullScorePage.test.ts`)이며 Score Tools 집중·상세 렌더 계약에는 실패가 없다.

## 2026-09-27 — Score Tools 0.2.1 Staff/Voice 회귀 수정

- 모든 실제 Staff 또는 Voice를 선택한 scoped view는 `whole_part`와 같은 기보를 유지한다. 실제로 일부 이벤트·선언 Staff를 제외할 때만 tie/slur/tuplet/beam/arpeggiation 경계 정리를 적용한다.
- excerpt 시작 마디의 effective `clef/key/time/staff-details`를 tag와 Staff number identity별로 병합해 cross-staff Voice의 다른 Staff 음자리표가 사라지지 않게 했다.
- 파생 XML을 다시 inventory하여 sidecar `derivedEventId`를 실제 파생 measure/event ordinal과 일치시켰다. sidecar는 `1.1.0`이며 `snapshotSchemaVersion`을 기록한다.
- `ScoreSnapshot 1.1.0`을 도입했다. legacy 1.0 snapshot은 source hash가 같은 원본 XML을 `migrateScoreSnapshot`으로 재파싱해야 scoped Staff/Voice 선택에 사용할 수 있다.
- 누락 Voice는 Voice 1로 추정하지 않는다. 명시 Voice를 가진 chord head에 바로 이어지는 `<chord/>` 구성음만 그 Voice를 상속하고 나머지는 `__unassigned__`로 둔다. KY 121개와 PDMX 120개, 합계 312,664개 음표를 층화 표본으로 검사했으며 Voice 누락은 0건이었다.
- Staff 번호 압축 전에 원본 Part/Staff/Voice/마디/박 identity를 보존한다. 검색 강조, playback playhead, Phrase/Motif/Harmony anchor와 tie chain이 파생 Staff 번호가 아니라 원본 lane을 사용한다.
- 검증: Score Tools 34/34, FullXmlNotation 24/24, 모듈·main build와 package verify 통과. 실제 다중 Staff PDMX의 Staff 1, Staff 2, Voice 1 파생본도 Verovio SVG 렌더링에 성공했다. 전체 suite에서 기존 Motif overlay 기대값 2건은 계속 별도 과제이며, 텍스트 검색 1건의 최초 5초 timeout은 단독 재실행에서 통과했다.

## 2026-09-28 일일 메타데이터 수집

- KY 공식 조회 100개를 실행해 100개 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다. 누적 2,304개, cursor 2,304, 미처리 10,744개이며 오류는 없었다.
- YouTube 대표 영상 수집은 Pacific 날짜 2026-09-27 기준 95/95 호출을 사용했다. 작품 캐시는 1,425개(매칭 1,227, no-match 198), 고유 videoId 426개, cursor 1,428이다.
- YouTube의 95번째 Search 호출에서 분당 quota HTTP 429가 발생해 즉시 중단했고 재시도나 우회를 하지 않았다. 오류는 `data/youtube-backfill-state.json`에 보존했다.
- 원본 XML과 검색 DB는 변경하지 않았다. KY 날짜별 신규 목록은 `docs/ky-collection/2026-09-28.md`에 저장했다.

## 2026-09-28 KY 공식 메타데이터 자동 수집

- 일일 자동화로 공식 조회 100개를 실행했으며 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 2304개, cursor 2304, 미처리 10,744개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-28.md에 저장했다.

## 2026-09-29 KY 공식 메타데이터 자동 수집

- 일일 자동화로 공식 조회 100개를 실행했으며 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 2404개, cursor 2404, 미처리 10,644개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-29.md에 저장했다.

## 2026-09-29 YouTube 대표 영상 자동 수집

- API 키가 설정된 상태에서 Pacific 날짜 2026-09-28 기준 94/95 호출을 사용했다. 작품 캐시는 1,716개(매칭 1,476, no-match 240), 고유 videoId 505개, cursor 1,720이다.
- 기존 캐시 대비 신규 처리 레코드는 291개이고 고유 videoId는 79개 증가했다.
- 94번째 Search 호출에서 분당 quota HTTP 429가 발생해 즉시 중단했으며 재시도나 우회를 하지 않았다. 오류는 `data/youtube-backfill-state.json`에 보존했다.
- 원본 XML과 검색 DB는 변경하지 않았다.

## 2026-09-30 KY 공식 메타데이터 자동 수집

- 일일 자동화로 공식 조회 100개를 실행했으며 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 2504개, cursor 2504, 미처리 10,544개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-09-30.md에 저장했다.

## 2026-09-30 YouTube 대표 영상 자동 수집

- API 키가 설정된 상태에서 Pacific 날짜 2026-09-29 기준 95/95 호출을 정상 완료했다. 작품 캐시는 2,016개(매칭 1,733, no-match 283), 고유 videoId 585개, cursor 2,020이다.
- 기존 캐시 대비 신규 처리 레코드는 300개이고 고유 videoId는 80개 증가했다.
- quota·rate-limit·반복 오류는 없었고 `data/youtube-backfill-state.json`의 마지막 오류는 비어 있다.
- 원본 XML과 검색 DB는 변경하지 않았다.

## 2026-10-01 KY 공식 메타데이터 자동 수집

- 일일 자동화로 공식 조회 100개를 실행했으며 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 2604개, cursor 2604, 미처리 10,444개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-10-01.md에 저장했다.

## 2026-10-01 YouTube 대표 영상 자동 수집

- API 키가 설정된 상태에서 Pacific 날짜 2026-09-30 기준 95/95 호출을 정상 완료했다. 작품 캐시는 2,312개(매칭 1,974, no-match 338), 고유 videoId 661개, cursor 2,316이다.
- 기존 캐시 대비 신규 처리 레코드는 296개이고 고유 videoId는 76개 증가했다(585→661).
- quota·rate-limit·반복 오류는 없었고 `data/youtube-backfill-state.json`의 마지막 오류는 비어 있다.
- 원본 XML과 검색 DB는 변경하지 않았다.

## 2026-10-02 KY 공식 메타데이터 자동 수집

- 일일 자동화로 공식 조회 100개를 실행했으며 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 2704개, cursor 2704, 미처리 10,344개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-10-02.md에 저장했다.

## 2026-10-02 YouTube 대표 영상 자동 수집

- API 키가 설정된 상태에서 Pacific 날짜 2026-10-01 기준 95/95 검색 호출을 완료했다. 작품 캐시는 2,638개(매칭 2,264, no-match 374), 고유 videoId 743개, cursor 2,642다.
- 기존 캐시 대비 신규 처리 레코드는 326개이며 매칭 290개, no-match 36개, 고유 videoId는 82개 증가했다(661→743).
- quota·rate-limit·반복 오류는 없었고 `data/youtube-backfill-state.json`의 마지막 오류는 비어 있다.
- 원본 XML과 검색 DB는 변경하지 않았고 API 키 값은 기록하지 않았다.

## 2026-10-03 수집 자동화

- KY는 공식 조회/저장 43건, 누적 2,747건, 상태 cursor 2,746, checkpoint 기준 잔여 10,302건으로 기록했다. 상태 파일 원자적 rename이 EPERM으로 3회 실패했고 오류 상태 저장도 3회 실패하여 같은 날짜 재실행을 중단했다.
- YouTube는 PT 2026-10-02 기준 검색 95/95건을 완료했다. works 2,638→2,937, 매칭 2,264→2,536, no-match 374→401, 고유 videoId 743→827, cursor 2,941, lastError null.
- API 키는 출력·기록하지 않았고 원본 XML 변경 및 검색 DB 반영은 수행하지 않았다.

## 2026-10-04 KY 공식 메타데이터 자동 수집

- 일일 자동화로 공식 조회 100개를 실행했으며 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 2847개, cursor 2847, 미처리 10,201개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-10-04.md에 저장했다.

## 2026-10-04 YouTube 대표 영상 자동 수집

- YouTube는 Pacific 날짜 2026-10-03 기준 검색 95/95건을 완료했다. 누적 works 3,250개(매칭 2,814, no-match 436), 고유 videoId 911개, cursor 3,254, lastError null이다.
- 신규 처리 313개(매칭 278개, no-match 35개), 고유 videoId는 827개에서 911개로 84개 증가했다.
- 기존 캐시를 재사용했고 quota·rate-limit·반복 오류가 없었다. 원본 XML·검색 DB는 변경하지 않았으며 API 키 값은 기록하지 않았다.

## 2026-10-05 KY 공식 메타데이터 자동 수집

- 일일 자동화로 공식 조회 100개를 실행했으며 모두 번호 정확 일치와 비어 있지 않은 제목 조건을 통과했다.
- 누적 2947개, cursor 2947, 미처리 10,101개이며 429·차단·실행 오류는 없었다.
- 원본 XML은 변경하지 않았고, 검색 DB 반영은 수집과 분리해 아직 수행하지 않았다.
- 날짜별 목록은 docs/ky-collection/2026-10-05.md에 저장했다.

## 2026-10-05 YouTube 대표 영상 자동 수집

- YouTube는 Pacific 날짜 2026-10-04 기준 검색 95/95건을 완료했다. 신규 처리 313개(매칭 264개, no-match 49개), 누적 works 3,563개(매칭 3,078, no-match 485), 고유 videoId 988개, cursor 3,567, lastError null이다.
- 기존 캐시를 재사용했고 quota·rate-limit·반복 오류가 없었다. 공개·embeddable·syndicated·KR 허용·제목/작곡가·최소 길이 검증을 유지했다.
- 원본 XML·검색 DB는 변경하지 않았으며 API 키 값은 기록하지 않았다.

## 2026-10-05 악기 샘플 음원 통합

- 요청: Claude Code에서 만든 악기 소리를 기존 뷰어에 추가하되 이전 재생 기능을 보존한다.
- 피아노·바이올린·비올라·첼로 로컬 MP3를 추가했다(78개 음원, manifest/README 포함 약 1.8MiB). 출처·라이선스 표기를 보존했으며 새 외부 서비스나 npm 의존성은 추가하지 않았다.
- Query·추천·결과·상세 재생을 연결했다. 상세는 실제 `work.streamId`의 part-list/GM 정보를 사용하고 분석용 성부나 표시 선택을 재생 성부로 혼동하지 않는다. 지원되지 않는 악기는 피아노로 대체하고 이를 상태에 표시한다.
- 기존 동기 재생 API, 0.06초 시작 시계, 625ms/beat, 음가·쉼표·타이 합산, 재생 위치·seek·마디 이동·이조 연결을 유지했다. 추천 Query에서 빠졌던 타이 합산을 보완했다.
- 샘플 사전 로딩·중복 제거·실패 후 명시적 재시도·부분 bank의 누락 파일 복구·기본 소리 fallback을 구현했다. 로딩 완료로 연주 중 음색이나 시작 시각을 바꾸지 않는다.
- `샘플 악기 소리` 설정으로 기본 소리로 돌아갈 수 있다. 저장 실패 시 세션 설정을 유지하고 변경 시 기존 예약 소리를 중지한다. Query 수정/초기화·화면 이탈·검색 결과 교체·상세 이조 변경 때도 이전 소리/타이머를 정리한다.
- 최종 관련 회귀 120개 통과(신규 음원/상태/자산 63개 + 기존 악보 55개 + 상세 재생 이동 2개), TypeScript/production build 통과. 실행 중인 서버의 manifest·MP3 HTTP 200과 배포 자산 포함을 확인했다. 기존 Verovio 빌드 경고와 기존 Motif 분석 테스트 2개 실패는 별도 범위로 남긴다.
- 브라우저 검증 도구의 sandbox helper 초기화 실패로 실제 화면 조작·청취 검증은 미실시다. 테스트 통과를 실제 음색 청취 확인으로 주장하지 않는다. 기존 단일 검색 성부 재생이며 다파트 합주/새 tempo·실음 이조 해석은 추가하지 않았다.
- 상세 구현·재현·수동 확인 순서는 [악기 샘플 음원 통합](sampled-playback-integration.md)에 기록했다. 기존 KY/YouTube 수집 데이터와 로그는 보존했다.

## 2026-10-06 일일 수집

- KY 공식 조회 100건을 완료해 신규 100건, 누적 3047건을 기록했다. 날짜별 목록은 `docs/ky-collection/2026-10-06.md`이며 원본 XML과 검색 DB는 변경하지 않았다.
- YouTube는 Pacific 2026-10-05 기준 93/95 호출에서 quotaExceeded(HTTP 429)로 중단했다. 중간 저장 결과는 신규 처리 312건(매칭 266, no-match 46), 누적 works 3875건, 고유 videoId 1065개, cursor 3880이다. 재시도·우회와 검색 DB 반영은 하지 않았다.
