# MUSICANOTE 화성·구조 분석 및 작곡·편곡 Harness 실행 계획

2026-09-26 추가: 구간·화음·조건부 비화성음을 함께 선택하는 구현과 실제 악보 진단은 [Joint Harmony/NCT Pilot](JOINT_HARMONY_NCT_PILOT_2026-09-26.md)에 기록한다. 33개 harmony 테스트 통과, major7 과선택과 병합 편향은 후속 검증 대상이다.

2026-09-26 추가: 전후 마디·목표 화음 도착·분산 형태를 묶는 사례 재구성과 유형별 판단 프로토타입은 [Harmony Episode Model](HARMONY_EPISODE_MODEL_2026-09-26.md)에 기록한다. 실제 train/dev 사례 5,491개와 진단 평가를 생성했으며 Viewer 승격 전 단계다.

상태: **구현 계획 v0.1 + 전체 파일 등록·DCML 392쌍 정밀 정렬·RomanText/ChoCo 형식 검사·독립 표면/펼친 화성 파일럿 / 2026-09-24**. 파일 등록과 형식 검사는 전 자료의 분석기 연결이나 학습 완료를 뜻하지 않는다. 전곡의 기능화성·NCT·종지 엔진이나 생성 엔진도 아직 구현 완료되지 않았다. 개발자 전달용 실행 순서와 완료 기준의 정본이다.

## 0. 이 문서를 사용하는 방법

### 2026-09-29 공통 후보 계약 후속

`harmony_candidate_catalog.propose` v0.1이 기본·증6·추가음 후보를 원ID/철자/가정별 원근거와 함께 통합하고 +M7/mM7을 관측 근음·3음·장7음 관문으로 추가했다. 기존9종 `TEMPLATES`와 선택기는 변경하지 않는다. 후보별 동일 sound/time 및 유리수 합계를 검사하며 승자·점수를 만들지 않는다. 신규20/전체1,383테스트·새18XML·이전45대조군 보존 검사 통과. 기존24창 총1,348후보 중 새10개는 전부 증5음 결측 +M7 가정이며 정답이 아니다. [r1 보고서](../output/harmony-candidate-catalog-2026-09-29-r1/report.json), 계약/한계/재현 (상세 기록은 공개 브랜치에서 제외). 다음은 기능/조성 가정·조건부 NCT·시간 근거 연결이다. 그 뒤 독립 평가/화면 승격으로 진행한다. 운영5173/Core 미변경.

### 2026-09-29 추가음 후보 연결 후속

`harmony_extended_candidates.propose` v0.1이 dominant7 기반9·4/11·6/13 후보를 관측 철자에서 생성하고 Unit28 성부 진행 근거에 연결한다. 기존 후보와 구성음/비화성음 경쟁 해석을 보존하며 누적 완성과 실제 동시 지지를 구별한다. 신규23/전체1,363테스트·30XML 대조 통과. 기존24창178개 추가 가정과 과거 주석 선정202건의1,408개 제안은 정확도나 운영 적용 완료가 아니다. [최종r2 보고서](../output/harmony-extended-candidates-2026-09-29-r2/report.json), 상세 기록 (상세 기록은 공개 브랜치에서 제외). 다음은 +M7/mM7 누락 및 공통 후보 계약, 그다음 조성/기능·시간 비교기 연결이다. 모든7화음 기반 확장이나 재즈 어휘까지 지원했다는 뜻은 아니다.

### 2026-09-29 우선순위 조정 — 교재 검토와 엔진 연결의 차이

사용자 요청에 따라 형태 후보 누락을 먼저 점검한다. **화음 형태 coverage → 후보 공통 계약 → 조성/기능 가설 → 유지·교체/NCT 통합 → 독립 평가·운영 승격** 순서다. 기존 근거 대조 개발을 폐기하지 않고 후보 범위가 빠진 상태에서 일부 해석만 정교화하는 위험을 먼저 줄인다. 종류별 연결 현황과 상세 기록 (상세 기록은 공개 브랜치에서 제외)이 정본이다.

첫 실행은 `harmony_augmented_candidates.propose` v0.1: 증6 It/Ger/Fr/Ger43를 관측 철자에서 생성하여 Unit30 해결 근거에 연결, 기존9종 기본 후보 유지. 신규14/전체1,340테스트·15XML 통과. 기존24창에서는 추가0; 주석 선정 과거22건에서는76경쟁 제안. 이는 후보 연결 검증이지 정확도나 운영 적용 완료가 아니다. [최종r2 보고서](../output/harmony-augmented-candidates-2026-09-29-r2/report.json). 다음9/11/13·확장 후보 공통 계약 후 Secondary/혼합/Neapolitan의 기능 가정을 연결한다. Core·원자료·운영5173는 변경하지 않는다.

### 2026-09-29 단계 대조표 — 누락 방지 / 완료 선언과 구별

후속 경쟁 설명 대조: `harmony_hold_change_contrast` v0.1이 같은 범위에서 유지/교체 가정별 구성음·조건부 NCT·미설명·철자 보류의 note-time을 비교한다. 기존 한 경계80×13가설 비교이며 정답 선택이나 독립1,040사례가 아니다. 신규10/전체1,326테스트 및 기존18XML 대조군 재검증 통과. [r2 결과](../output/harmony-hold-change-contrast-2026-09-29-r2/report.json), 개발 기록 (상세 기록은 공개 브랜치에서 제외). P5/P6 연구 진행; 강세/화성 리듬 및 P4 독립 평가/P7 운영 승격은 여전히 남아 있다.

후속 반복음 대조: `harmony_reattack_figures` v0.1이 원 attack을 보존하며 동일 철자 재타격을 조건부 경과/보조 음형으로 조사한다. 기존 동일24창에서 K281의3개 겹치는 음형에 설명이 추가되었으나 유지/교체 후보 선택은 변경하지 않았다. 신규13/전체1,316테스트·12XML 대조·화면 색칠 검증. [r1 보고서](../output/harmony-reattack-figures-2026-09-29-r1/report.json), 정본 기록 (상세 기록은 공개 브랜치에서 제외). P5/P6 연구 근거이며 P4 독립 정확도/P7 운영 승격은 아니다.

후속 잔여 음 감사: `harmony_residual_audit` v0.1이 13개 교체 후보쌍의 잔여 음과 조건부 NCT/작은 셀의 다른 구성음 대안을 보존한다. K281의 같은 F5 한 음에 6후보에서 선행음 설명이 가능했으며 후보 선택은 바뀌지 않았다. 신규 10/전체 1,303 테스트·12 XML 대조와 클릭 색칠 확인. [r1 보고서](../output/harmony-residual-audit-2026-09-29-r1/report.json), 정본 개발 기록 (상세 기록은 공개 브랜치에서 제외). P5/P6 연구 근거 추가이며 독립 정확도/P4·P7·운영 승격이 아니다.

후속 관문 실험: `harmony_change_gate` v0.1이 열린 후보쌍에 실제 구성음 교체·베이스·직접 성부 진행·지속·조건부 장식음 경쟁 조건을 적용했다. 기존121경계 중 한 경계에서13경쟁쌍, 다른 작품에서 중복제거2조건부 유지 가설을 얻었다. 신규12/전체1,293테스트·18XML 대조. [r2 보고서](../output/harmony-change-gate-2026-09-29-r2/report.json). 미설명음/화음명 ambiguity가 남아 최종 선택·독립 정확도 평가·P7/운영 승격은 아직 아니다. 자세한 제한과 다음 관문은 개발 기록에 남긴다.

후속 갱신: P5/P6의 열린 후보에 시간 추적과 조건부 NCT를 연결하는 `harmony_temporal_readings` v0.1을 구현했다. 기존3개 train 작품의 처음8마디씩24창을 결과와 무관하게 검토하여 불완전 후보를 보존한다. 신규12/전체1,281테스트·18XML 대조. 정본 개발 기록 (상세 기록은 공개 브랜치에서 제외), [실험 r3](../output/harmony-temporal-readings-2026-09-29-r3/report.json). 같은 연구 작품군이므로 P4 독립 평가 관문을 통과한 것은 아니며 P7/운영 승격은 여전히 보류다.

아래는 기존 작업 카드 P0–P13에 대한 개발 기록 대조다. 전 코퍼스를 새로 전수 검증했다는 뜻은 아니다. 구현·연구 검증·운영 승격을 별개로 관리하며, 사용자 사례는 반례/가설로 보존하고 단독으로 일반 규칙을 확정하지 않는다. 상세 재현·실패 이력은 교과서–사례 개발 기록 (상세 기록은 공개 브랜치에서 제외), 최신 진입점은 [인수인계](HARMONY_DEVELOPER_HANDOFF.md)다.

| 단계 | 현재 상태 | 완료 전 남은 관문 |
|---|---|---|
| P0 계약·기준선 | 계약/기준선 기록 있음 | 미해결 계약·버전 변경 시 회귀 및 마이그레이션 승인 |
| P1 등록·권리·중복 | registry/release 구현 이력 있음 | 신규 자료 권리·작품/주석 계보·split 재검증; 등록≠전체 사용 |
| P2 IR·음표 연결 | parser/bridge·타이/성부/시간 교정과 회귀 구현 | 입력별 loss/abstention, 다성부·반복·이조악기 검증 확대 |
| P3 주석 수입·정렬 | DCML/RomanText 등 단계별 구현 | 모든 source dialect/time domain의 완전 연결, revision remap 검증 |
| P4 독립 평가 | frozen cohort·검토 UI·대조군 있음 | 연구 표본 밖 dev/holdout, 사전 고정 승격 기준, 정확도/경계/실행시간 평가 |
| P5 독립 화성 엔진 | **진행 중:** 열린 후보·전후 해결·베이스·구성음 시간 추적 | 유지/교체 선택, local key/기능, 과도 병합·분할 억제와 독립 평가 |
| P6 NCT·특수화음 | **진행 중:** 교재 evidence·조건부 장식/이중 보조음·대안 대조 | governing harmony와 공동 판정, 희귀 유형·성부 대응의 검출률/오검출률 |
| P7 Cadence→구조 | 기존 분석/표시와 구별하여 연구 개선 승격 보류 | 독립 종지 검증, 순환 근거 차단, Phrase/Motif 회귀 후 연결 |
| P8 추가 주석 adapter | 자료 검사·일부 수입 이력 있음 | WiR/TAVERN/ChoCo 등 출처별 권리·대안·정렬 coverage 완성 |
| P9 스타일·편곡 쌍 | 후속 단계 | 역할·반주 패턴·paired score와 표현 규격/표본 검증 |
| P10 생성 계획·제약 | 후속 단계 | hard/soft constraints 및 독립 결과 validator |
| P11 편곡 생성 | 후속 단계 | 8–16마디 시험 생성·독립 평가·원곡 보존 |
| P12 작곡 생성 | 후속 단계 | 형식·동기 변형·종지 계획과 평가 |
| P13 운영 | 일부 실험 저장/조회 존재, 완성 아님 | 통합 DB/job/cache/rollback·drift/latency 검증 |

**현재 순서:** P5/P6 근거의 시간 정합성 → 열린 후보군에서 유지/교체·비화성음 설명 대조 → P4 독립 표본 검증 → 통과한 변경만 Viewer/구조 분석 승격. P9–P12의 작곡·편곡 목적을 삭제하거나 화성 표시 기능으로 대체하지 않는다.

**이월 문제:** 소나타1번15/17/19마디의 일찍 나온 음과 Secondary 범위,31마디 이중 보조음의 선행 기준음, 일반 다성부 대응, 화음 경계 과병합, 불완전 구성음·페달/지연, 기능/국소 조성 및 종지, 독립 holdout 성능은 아직 해결 완료로 표시하지 않는다. 사용자 해석·원주석·자동 가설은 계속 분리한다.

**이번 검증:** `harmony_member_timeline` v0.1, 실제3곡의 기존30가설 구간·21 MusicXML 대조, 신규12/전체1,269 unit test 통과. [r2 결과](../output/harmony-member-timeline-2026-09-29-r2/report.json). 기존 후보의 구성음 완전성을 전제로 선정된 표본이므로 일반 정확도·누락 검출률을 측정한 결과가 아니다. 운영5173/Core/원주석/기존 화음 선택은 변경하지 않았다. 아래 날짜별 설명과 §16 도입부의 구현 상태는 작성 당시 이력으로 읽는다.

처음에는 §1–5를 읽고, 실제 개발은 §16의 작업 카드 순서로 진행한다. 음악 용어는 §2, 데이터 계약은 §6, 실제 증6화음 예는 §7, 화성 알고리즘은 §9, 생성은 §11–12, 평가 기준은 §14에 있다. 현재 구현과 보류사항은 [전체 코퍼스 등록·정렬 확대](ALL_CORPORA_REGISTRY_AND_ALIGNMENT_2026-09-24.md), [654쌍 주석 전수 검사](DCML_FAST_ANNOTATION_AUDIT_2026-09-24.md), [392쌍 정밀 정렬](DCML_FULL_ANNOTATION_ALIGNMENT_2026-09-24.md), [RomanText·ChoCo 출처 검사](ROMANTEXT_CHOCO_ANNOTATION_SOURCE_AUDIT_2026-09-24.md), [RomanText 2,029쌍 좌표 정렬](ROMANTEXT_SCORE_ALIGNMENT_PILOT_2026-09-24.md), [반복 엔딩 정렬](DCML_REPEAT_TIMELINE_ALIGNMENT_2026-09-24.md), [DCML 수입](DCML_HARMONY_IMPORT_PILOT_2026-09-24.md), [독립 표면 화음](BLIND_SURFACE_HARMONY_PILOT_2026-09-24.md), [펼친 화성 구간](UNFOLDED_HARMONY_PILOT_2026-09-24.md) 기록을 확인한다.

관련 문서:

- [Canonical IR 전체 규격](CANONICAL_MUSIC_IR_SPEC_v0.1.md), [ID·시간축](ID_AND_TIME_COORDINATE_SPEC.md), [Analysis 인터페이스](ANALYSIS_INTERFACE_SPEC.md)
- [기존 경계 화성 계약](BOUNDARY_HARMONY_CADENCE_SPEC_v0.1.md), [주석 검수 계약](ANNOTATION_EXTENSION_SPEC.md)
- [로컬 코퍼스 조사](CLASSICAL_HARMONY_CORPORA_AUDIT_2026-09-24.md), [작곡·편곡 자료와 증6화음 조사](COMPOSITION_ARRANGEMENT_HARMONY_DATA_PLAN_2026-09-24.md)
- 이론 기준: `K:/MUSICANOTE_Harmony_Analysis_Harness_Guide.md`의 관찰·표면·기능·지배 화성 구분, 성부진행/NCT, 스타일 profile, 구간화, Validator.

Core의 의미는 기존 Canonical 규격을 따른다. 새 계약은 아래에 **신설 제안**으로 표시한다. 충돌은 [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)의 OQ-021 이후를 먼저 처리한다. 기록 위치 정정(2026-09-27): 화성 날짜별 구현 결과는 교과서–사례 개발 기록 (상세 기록은 공개 브랜치에서 제외)에 남기고, 구조 분석/UI 변경은 기존 MusicStructureAnalyzer 개발 로그와 상호 연결한다. 이 문서에는 단계 상태와 링크를 갱신한다. 인수인계는 [화성 개발 인수인계](HARMONY_DEVELOPER_HANDOFF.md)에서 시작한다. 아래 과거 날짜의 수치·상태는 해당 시점의 기록이지 최신 완료 상태가 아니다.

## 1. 제품 목표와 최초 범위

동일한 악보 표현과 화성 엔진이 세 가지 일을 지원해야 한다.

1. **구조 분석**: 프레이즈·모티프·기둥음 판단에 화성 진행과 Cadence 근거를 제공한다.
2. **편곡**: 원래 선율·구조·필요한 화성을 보존하고, 악기·반주형·밀도·음역·난이도 요구에 맞게 다른 음표를 만든다.
3. **작곡**: 길이·형식·조성·종지 목표·스타일·주어진 모티프를 바탕으로 화성 계획과 음표를 생성한다.

최초 구현 범위는 **고전 조성 profile, 피아노, 기보 시간축, 화성 주석이 있는 소규모 코퍼스**다. 분석은 경계 주변에서 먼저 검증한다. 편곡과 작곡은 전체 목표 구간에 화성 계획이 필요하므로, 경계 전용 API를 그대로 전곡 생성기로 사용하지 않는다. 첫 생성 데모는 8–16마디로 제한하고 같은 엔진의 전 구간 모드를 사용한다.

초기 완료 화면은 다음을 보여야 한다.

- 원본 악보, 원본 코퍼스 주석, 자동 분석을 각각 켜고 끈다.
- 한 화성 구간을 클릭하면 실제 음표와 표면 화음·기능·조성 후보·종지·근거가 오른쪽에 나온다.
- 자연어 편곡 요청을 입력하면 보존 조건과 변경 계획이 먼저 표시된다.
- 생성 악보와 원본을 비교하고, 음표 변경·요구 위반·연주 가능성 경고를 확인한다.
- 사용자가 고친 구간과 전후 악보, 설명이 재현 가능한 사례로 저장된다.

## 2. 개발자용 음악 용어와 오해 방지

| 용어 | 프로그램이 다룰 의미 | 구현 시 주의 |
| --- | --- | --- |
| 조표 / 조성 | 조표는 기보 정보, 조성은 어느 음을 중심으로 듣는지에 대한 해석 | 조표 0개를 C major로 확정하지 않는다. |
| root / bass | root는 화음 근음 후보, bass는 현재 최저 발음음 또는 분석된 베이스 성부 | 최저음=근음은 성립하지 않는다. |
| attack / sounding | 새로 시작한 음 / 이전부터 지속 중인 음을 포함한 발음 | 타이 연속음은 새 attack이 아니다. |
| sonority / chord | 동시에 울리는 음 집합 / 문맥에서 해석한 화음 | 분산화음은 한 시점에 구성음이 다 없을 수 있다. |
| inversion / voicing | 베이스에 어떤 화음 음이 오는가 / 각 음을 어떤 옥타브·성부에 놓는가 | 전위 변경이 반드시 화성 기능 변경은 아니다. |
| Roman numeral | 조성에 대한 상대 화음 표기 | `V`는 국소 조성 정보와 함께 읽는다. |
| NCT | 경과음·보조음·계류음 등 문맥적 비화성음 역할 | 음표가 짧거나 약박이라고 자동 NCT가 되지 않는다. |
| harmonic rhythm | 의미 있는 화성 변화 속도 | 음표 시작 개수와 다르다. |
| governing harmony | 여러 표면 움직임을 묶어 지배하는 화성 | 세부 화음을 삭제하지 않고 상위 span으로 연결한다. |
| Cadence | 준비와 도착, 성부진행·종결 문맥이 있는 종지 후보 | `V–I`라는 인접 코드만으로 확정하지 않는다. |
| Phrase / Motif | 한 호흡의 구절 / 반복·변형되는 작은 음형 | 반복된 작은 모티프 둘이 한 Phrase를 이룰 수 있다. |
| texture / accompaniment | 성부가 배치되는 방식 / 선율을 받치는 실제 리듬·보이싱 | 장르 이름 하나로 반주 패턴이 결정되지 않는다. |

음악 판정은 항상 `적용 조건 → 근거 → 반대 근거 → 보류 조건 → 검증 사례`로 작성한다. 설명 문구의 문자열을 검사하여 계산하지 않는다. 특정 제목·workId·마디 번호를 생산 규칙에 넣지 않는다.

## 3. 확인한 현재 구현과 재사용 경계

2026-09-24의 파일 확인 기준이다. 구현 시작 시 git 상태와 함수 계약을 다시 확인한다.

| 현재 파일 | 확인한 상태 | 계획에서의 역할 |
| --- | --- | --- |
| `K:/Music Analysis/src/musicanote_harness/canonical.py` | prototype `musicanote-canonical-ir-0.2`, Fraction 사용, segments/sounding/atoms. score ID에 파일명·크기가 관여 | 이관 원본. 정식 스키마와 동일하다고 가정하지 않는다. |
| `K:/MusicSearch/server/musicxml-harmony-events.mjs` | 정규식 기반 임시 다성부 추출, chord/tie segments. 조옮김·좌표·source ID를 포괄하는 정식 parser가 아님 | 비교 fixture와 기존 화면 호환 adapter |
| `K:/MusicSearch/server/boundary-harmony.mjs` | 장·단·감3화음/딸림7 템플릿, 조표의 관계 장·단조 후보, 선택된 boundary 주변 8 quarter 전/2 quarter 후 | baseline. 새 엔진과 A/B 비교 |
| 같은 파일의 `cadenceHypotheses` | Phrase boundary의 gap 등 일부 근거를 읽으며, 강박을 단순 beat 1/3으로 평가 | 독립 화성→Phrase feed를 만들기 전에 입력 의존성과 박자 처리를 수정해야 함 |
| `server/phrase-boundaries.mjs`, `phrase-evidence-ledger.mjs` | 기존 Phrase와 부분 근거 추적 | baseline 결과와 lineage 연결. 새 화성 결과를 단순 점수 가산하지 않음 |
| `src/music/pillarCandidates.ts`, `pillarDisplay.ts`, `pillarEvidence.ts` | 독립 기둥 후보와 Phrase 표시 힌트를 분리하는 기반 | 독립 근거/표시용 힌트 구분 재사용 |
| `schemas/*.json` | 첫 정식 IR·Analysis·Annotation 계약 | 검증 기반. 수입 주석 provenance, 미보정 score, point target은 추가 설계 필요 |

특히 현재 `analyzeBoundaryHarmony`는 supported boundary만 순회하므로 **기존 Phrase가 놓친 종지를 발견할 수 있는 후보 창 생성기**가 별도로 필요하다. 현재 로마숫자 출력이 곧 완성된 화성 이해는 아니다.

## 4. 전체 구조와 의존 방향

```text
원본 악보 ─→ 정식 Canonical IR ─→ 공격/지속/베이스/음정/박자 근거
                                           │
코퍼스 주석 ─→ 출처·표기 변환 ─→ 시간 정렬 ──┤ (평가·사례 저장)
                                           ↓
                              화성 후보·구간화·조성·NCT
                                           ↓
                         표면 화음 / 기능 / 지배 화성 / Cadence
                            │                         │
                 Phrase·Motif 검토              스타일·반주 사례 검색
                            │                         ↓
                            │               작곡/편곡 계획 → 음표 생성
                            └─────────────────────→ 검증·악보 UI
                                                        ↓
                                               사용자 교정·Case Library
```

학습/평가 시 코퍼스의 정답 주석은 scorer에 전달하고, 원본 해석 성능을 측정할 때 analyzer의 입력에서는 차단한다. XML의 `<harmony>`, 로마숫자 direction, 레이블 TSV, key/cadence 정답이 숨은 입력이 되지 않도록 run manifest에 `annotation_input_policy`를 기록한다. 주석을 사용한 편곡은 가능하지만 `source-annotation-conditioned` 실행으로 구분한다.

엔진 모드:

- `boundary_windows`: 독립적으로 생성한 종지 후보와 기존 Phrase 경계 주변을 분석. 창 밖 문맥이 부족하면 확장하거나 보류한다.
- `full_span`: 생성 대상 전체를 덮는 화성·조성 계획을 만든다. 미확정 구간은 명시한다.
- `annotation_assisted`: 출처가 있는 주석을 조건으로 분석·편곡한다. 맹검 정확도 평가와 분리한다.

### 4.1 프로젝트와 레이어의 경계 — 2026-09-24 결정

화성 분석을 구조 분석과 **독립된 코드 모듈·데이터 계약·버전**으로 만든다. 사용자가 보는 악보는 기존 MusicSearch viewer 하나를 사용하고 Harmony/Cadence를 별도 overlay로 붙인다. 신규 Git 저장소나 별도 배포 서비스는 첫 단계에서 필요하지 않다. 현재 `K:/Music Analysis`의 `musicanote_harness`는 Canonical IR·코퍼스 수입·정렬·공통 화성 엔진의 소유 후보이고, `K:/MusicSearch`는 검색·악보 화면·Phrase/Motif 및 Harmony 결과 표시를 담당한다. P0에서 실제 저장소 간 배포/소유 계약을 확인한 뒤 경로를 확정한다.

현행 `K:/MusicSearch/server/search-api.mjs`는 Phrase 경계를 계산한 뒤 `analyzeBoundaryHarmony`에 전달한다. 이 함수는 전곡의 독립 화성 분석기가 아니라 기존 경계 주변 분석의 baseline이다. 새 엔진의 기본 입력은 **IR revision + 대상 범위 + 스타일 profile**이어야 한다. Phrase 예측은 화성 계산의 필수 입력이 될 수 없다. 독립적인 화성/Cadence 후보를 만든 후에만, provenance가 확인된 근거를 Phrase 개선 후보에 연결한다. 기존 viewer에서 별도 Harmony 버튼만 만드는 것은 이 의존 관계를 해결하지 못한다.

주석 데이터 사용은 계산 범위와 별개의 실행 정책으로 구분한다:

| annotation_input_policy | 사용할 주석 | 결과 표시·평가 |
| --- | --- | --- |
| `blind` | 대상 악보의 정답 주석을 입력에서 제외 | 독립 분석 성능 평가의 기본값. 정답은 scorer만 읽음 |
| `exact_source` | 같은 판본/악장에 정렬된 승인 주석 | `imported_annotation` 출처를 명시하여 활용. 이것을 자동 발견으로 평가하지 않음 |
| `case_retrieval` | 다른 작품 또는 train 집합의 출처 있는 유사 사례 | 유사/차이 특징과 source refs를 evidence로 제공. 검색된 label을 그대로 확정하지 않음 |
| `exact_plus_cases` | 위 두 종류를 함께 사용 | 편곡·작곡의 주석 보조 모드. 출처별 기여와 상충을 기록 |

`boundary_windows`/`full_span`은 계산할 **범위**이고 위 정책은 **사용할 주석**이다. 두 설정을 분리해 run manifest에 저장한다. 예를 들어 `full_span + blind`는 전곡 독립 분석, `full_span + exact_source`는 검수된 화성을 활용하는 편곡이다.

외부 주석은 먼저 일괄 수입·정렬해 변경 불가능한 track revision으로 저장한다. 요청마다 10만 개 JAMS/TSV를 다시 읽지 않는다. 분석 시에는 `score_id/edition/revision + time range`로 정확한 주석을 조회하고, 없거나 보완이 필요하면 조성 상대 진행·리듬·베이스·성부진행 등으로 구축한 사례 색인에서 후보를 찾는다. 조회 결과와 적용 이유는 Analysis/Evidence record에 남긴다. 원본/IR/주석/엔진 버전이 바뀌면 해당 분석 cache를 무효화한다.

최초 연결 인터페이스는 `analyze_harmony(ir_revision, span, analysis_profile, annotation_input_policy) -> {harmony_records, cadence_records, evidence_records, provenance, abstentions}`처럼 정의한다. MusicSearch는 결과를 versioned API 또는 선계산 artifact로 읽고, 화면에서 직접 화성 규칙을 중복 구현하지 않는다. Phrase 모듈은 근거 의존성이 검증된 Cadence/Harmony record만 소비한다. 다른 앱이 같은 엔진을 사용하거나 배포·확장 요구가 커질 때 이 계약을 유지한 채 별도 서비스/저장소로 분리할 수 있다.

## 5. 데이터 선정, 출처, 표본 설계

| 우선순위 | 데이터 | 사용할 것 | 제외/보류할 것 |
| --- | --- | --- | --- |
| 1 | DCMLab | 같은 ID의 악보+measures+notes+harmonies, cadence/phraseend | 시간/판본 매칭 실패, 문법 미지원 라벨 |
| 2 | When in Rome | 출처 확인된 사람 RomanText와 대응 악보, 대안 해석 | `analysis_automatic`를 인간 정답으로 승격 |
| 2 | TAVERN | A/B 주석자, 함수·화성·음표가 함께 있는 Humdrum, 변주 관계 | phrase-model을 유일한 구조 정답으로 일반화 |
| 3 | ChoCo | provenance가 확인된 score subset, 장르별 진행 | audio 초 단위를 악보 quarter로 간주; stage/재수록 중복 |
| 3 | Melody/Piano Solo·Hauptstimme 쌍 | 성부 역할/추가 장식/반주 패턴의 대응 사례 | 제목만 같은 악보의 자동 정답 페어링 |
| 보조 | YCACL | 관찰 pitch slice와 추정 조성의 별도 층 | 사람이 검수한 Roman/Cadence 정답으로 사용 |
| 보조 | Taking Form, ASAP, 기타 score | 형식 구조, 이후 연주 정렬, 악보/성부 테스트 | 없는 화성 레이블을 생성해 정답으로 취급 |

2026-09-24 추가 확인 자료: DilemmaData는 MXL/TSV 기반 분석 과제가 있고, Freischütz Digital의 `.xml`은 MusicXML이 아니라 MEI이며, 세종 궁중음악 자료는 MusicXML, Wagner leitmotif 자료는 CSV가 중심이다. 확장자만 보고 공통 MusicXML parser에 넣지 않는다. 궁중음악에 고전 서양 기능화성 규칙을 기본 적용하거나 녹음 기반 Motif CSV를 음표별 화성 정답으로 사용하지 않는다. 세부 사항은 [코퍼스 조사 추가 기록](CLASSICAL_HARMONY_CORPORA_AUDIT_2026-09-24.md)을 따른다.

첫 자료 집합은 최소 12곡을 선정하고 최대 20곡 안에서 기능을 검증한다. Beethoven `01-1`은 좌표/증6화음 회귀 예이며, 전 곡을 위한 규칙의 근거 중 하나다. 표본에 pickup, 단조, 6/8, 조성 이동, 분산화음, 타이, 반복/대체마디, 명시적 Cadence, 미표기 구간을 포함한다. 표본 선택표에는 각 항목의 실제 포함 여부를 적는다.

`work_family_id`는 작품·악장·편곡 및 전조 버전을 묶고, `annotation_lineage_id`는 DCML 원문→WiR 변환→ChoCo 변환을 묶는다. 두 관계 중 하나라도 같으면 train/test를 넘나들지 않게 연결 성분 단위로 분리한다. motif/음표 sliding window 단위 랜덤 분할은 금지한다. 별도 검토곡은 초반 규칙 조정에 쓰지 않는다.

로컬 inventory의 확장자 수는 곡 수·독립 주석 수가 아니다. registry 보고서에 `physical_files`, `distinct_score_editions`, `annotation_tracks`, `paired`, `aligned`, `human`, `automatic`, `unknown`, `heldout`를 각각 출력한다. 라이선스와 attribution을 source 단위로 보존한다.

## 6. 저장 계약: 기존 IR과 신설 record

### 6.1 저장 단위

개발용 JSON/JSONL로 시작한다. 논리 계약이 통과한 뒤 PostgreSQL/JSONB와 Parquet 저장 adapter를 추가한다. 악보는 **정식 Canonical IR**, 화성 해석은 **IR을 참조하는 별도 주석·분석 record**로 저장한다. 원본을 IR로 대체하거나 버리지 않는다.

아래는 제안 배치이며, 아직 생성된 폴더가 아니다.

~~~text
corpus-registry/
  assets.jsonl, score-editions.jsonl, annotation-tracks.jsonl
  lineage.jsonl, splits/<split_version>.json
scores/<score_id>/<revision>/
  source-manifest.json, canonical-ir.json, validation.json
  maps/source-to-ir.jsonl, maps/native-time-to-ir.jsonl
annotations/<track_id>/<revision>/
  imported.jsonl, alignment.jsonl, label-parse-report.json
analysis-runs/<run_id>/
  manifest.json, harmony.jsonl, cadence.jsonl, evidence.jsonl, metrics.json
cases/<case_id>/<revision>/
  manifest.json, context-ir.json, source-excerpt.musicxml, interpretation.json
  reviews.jsonl, retrieval-features.json
generation-runs/<run_id>/
  request.json, plan.json, candidates/, validation.json, review.json
~~~

원본 위치와 hash를 manifest에 기록한다. 휴대 가능한 사례 묶음에는 사용 허가 범위에서 원본을 포함하거나 다시 가져올 수 있는 asset을 연결한다. 발췌 MusicXML은 음자리표·조표·박자·divisions·악기·이조·시작 전 타이/지속음 문맥을 포함해야 한다. 독립 재현이 불가능하면 전체 악보를 보존하고 발췌는 표시용으로만 사용한다.

### 6.2 데이터 계약 목록

| Record | 최소 필드 / 참조 | 구분 |
| --- | --- | --- |
| SourceAsset | asset_id, raw_sha256, relative_path, format, corpus/version, licence_ref, source_uri, upstream_revision | 원본 식별. 의미 정규화 hash는 별도 |
| ScoreEdition | work_family_id, score_id, edition_id, revision, source_asset_ids, parser_version, ir_document_id | Melody·Piano Solo·이조 판본 구별 |
| CanonicalIR | score/part/staff/voice/measure/note/rest/tie/sounding/attack/source refs | 기존 Core. Roman·주선율 판정 금지 |
| ImportedAnnotation | annotation_id, track_id, raw_label, native_target, source_locator, dialect/version, author_origin, source_review_status, source_confidence, provenance | 신설. 외부 사람/자동/불명 해석 |
| AlignmentRecord | annotation_id, ir_document_id, source_revision, target, mapping_status, method/version, evidence_refs, errors | 신설. 주석과 악보 대응 결과 |
| HarmonyHypothesisRecord | run_id, score_revision, target, hypotheses, selected_id, evidence_refs, dependencies, profile/version | 신설. 조성·근음·성질·전위·기능·지배 화성 후보 |
| CadenceRecord | preparation_span, arrival_point/event_refs, resolution_point, type_candidates, structural_end_candidate, next_start_candidate, evidence/counter_evidence | 신설. 종지와 구절 경계를 구별 |
| StyleProfile / AccompanimentPattern | scope, source refs, features, reviewed labels, meter applicability, role lanes, variations, constraints, status | 신설. 분석·생성용 별도 계약 |
| ArrangementPlan / CompositionPlan | request_id, input revisions, protected material, form/key/cadence targets, pattern/voicing plans, constraints, alternatives | 신설. 생성 전 계획 |
| GeneratedScoreRevision | parent_score_refs, plan_id, event_derivations, new IR, export asset/hash, validator_results | 신설. 원본 복사·변형·신규 음표의 계보 |
| ReviewRecord / CaseRecord | target revision, 전후 context, 원본 설명, 수정안, 판단 상태, 사례 분할 정보 | 기존 Annotation 방향을 확장. AI와 사람 판단 분리 |

신설 계약은 각각 schema_name/schema_version을 가진다. 자유 JSON 하나에 모든 개념을 넣지 않는다. owner와 schema reference가 등록된 extension만 허용한다.

### 6.3 공통 필드 규칙

- 모든 target은 score_id뿐 아니라 **ir_document_id 또는 immutable revision**도 참조한다.
- span.start/end는 기존 규격의 rational 객체이며 항상 [start, end)다. 기보 quarter 축과 재생 반복 확장 축을 구별한다.
- Cadence의 도착은 **point** 또는 event 참조다. 점을 표현하려고 임의의 작은 duration을 만들지 않는다.
- native_target에는 mc/mn/onset 원문, 박자, written/unfolded 구분, JAMS score/audio 좌표 등 원래 표현을 보존한다.
- source_locator는 원본 hash와 함께 TSV 행 번호/row hash, RomanText 행/token, JAMS annotation/observation index, XML element 위치를 저장한다.
- mapping_status는 exact / verified_transform / ambiguous / orphaned / unsupported. 좌표 대응의 확실성과 음악 해석의 확실성은 별개다.
- author_origin은 human / machine / mixed / unknown. 사람 주석의 자동 형식 변환은 사람 유래와 변환 이력을 함께 보존하고, 자동 분석과 구별한다.
- heuristic score는 점수이지 확률이 아니다. calibration이 없는 확률 필드는 null로 둔다. 사람의 주관적 확신도도 별도 척도로 보존한다.
- 원본에 없는 annotator/date/confidence를 만들어 넣지 않는다. imported_at은 원본 작성 시각과 다르다.
- 외부 reviewed 상태를 이 앱의 human accepted 상태로 바꾸지 않는다.
- unknown(판단 불가), unannotated(주석 없음), N.C.(화음 없음이라는 주장), parse_error를 구별한다.
- training_eligible은 검수 상태뿐 아니라 사용 허가·정렬·출처·split에 의해 결정한다.
- 모든 분석 실행에 입력 hash, parser/engine/rule/profile/config 버전, seed, annotation_input_policy, 의존 run, 종료 상태를 기록한다.

### 6.4 스키마 충돌과 이전

현재 analysis_record.schema.json은 각 hypothesis의 confidence를 숫자로 요구한다. imported label에 없는 confidence를 1.0으로 채우지 않는다. 현재 annotation_record.schema.json의 human에는 annotator_id/timestamp가 필요하고 허용 필드도 제한되어 있다. 외부 주석을 억지로 그 human 객체에 넣지 않는다.

먼저 imported_annotation.schema.json, alignment_record.schema.json, harmony_hypothesis_record.schema.json, cadence_record.schema.json을 독립 version으로 설계한다. 공통 TargetReference는 entity/span/point를 지원하도록 제안하되 기존 reader를 조용히 깨뜨리지 않는다. 기존 generic record로의 adapter는 의미가 보존되는 경우만 제공한다.

prototype → 정식 IR bridge에는 ID map, field coverage, loss report, validation 결과를 붙인다. 미지원 항목을 삭제한 채 성공 처리하지 않는다. source revision이 달라지면 주석을 무조건 재사용하지 않고 remapping 검토를 수행한다. 구버전 reader fixture와 되돌리기 가능한 manifest를 유지한다.

## 7. 실제 증6화음 사례: Beethoven Op.2 No.1, 1악장

확인한 원본은 K:/MusicSearch/data/classical-corpora/dcmlab/beethoven-sonatas/의 harmonies/01-1.harmonies.tsv, measures/01-1.measures.tsv, notes/01-1.notes.tsv, MS3/01-1.musicxml이다.

| 위치 | 원본 label | 원본 조성 문맥 | 연결 결과 |
| --- | --- | --- | --- |
| mc55, mn53, quarter209 | iv.viio65/V | globalkey=f, localkey=iv | 앞 문맥의 주석 |
| mc56, **mn54**, quarter213, duration4 | **Ger6** | globalkey=f, localkey=iv | 증6화음 주석 span [213,217) |
| mc57, **mn55**, quarter217, duration3 | V[V&#124;HC}{ | globalkey=f, localkey=iv | V 화음, HC, 맞물림 표지를 각 항목으로 분리 |

대응 XML에는 다음과 같은 표기가 있다. 다음 코드는 해당 의미를 보여 주는 축약 발췌다.

~~~xml
<measure number="54">
  <harmony print-frame="no">
    <function>Ger6</function>
    <kind text="">none</kind>
  </harmony>
</measure>
~~~

kind가 none이라고 화성 주석이 없다고 판단하면 안 된다. function의 Ger6를 읽어 **외부 해석**으로 분리한다. TSV와 XML의 동일 라벨은 같은 원천에서 변환된 것일 수 있으므로 독립된 두 명의 검증으로 세지 않는다.

수입 절차:

1. 원본 hash, resource metadata의 upstream revision, 주석 dialect와 변환 도구 버전을 저장한다.
2. measures 표를 이용해 mc → 악보의 실제 measure ID → global quarter mapping을 만든다. mc는 Canonical의 0-based index가 아니다. mn54/mc56의 차이를 단순 상수나 여린마디만으로 설명하지 않는다.
3. [213,217)에 공격하거나 지속 중인 모든 관련 성부의 음을 연결한다. 주석이 staff 2에 배치되었어도 staff 2만의 화음으로 제한하지 않는다.
4. Ger6의 원문, 파싱된 화음 종류, local/global key, 다음 V/HC를 별도 record로 연결한다.
5. chord_tones 같은 코퍼스 전용 숫자는 해당 dialect 문서를 따라 해독한다. MIDI나 pitch class로 임의 해석하지 않는다.
6. 자동 analyzer에는 label을 숨긴 blind 실행과 label을 활용하는 assisted 실행을 따로 만든다.
7. 악보 53–55마디 전후 문맥과 원본 주석·예측·차이를 검토 화면에서 확인한다. 이 마디 번호는 fixture에만 사용한다.

개발자용 연결 예시다. 아래 ID는 설명용 placeholder이며 실제 수입 결과는 아니다. 정식 record 전체를 대신하지 않는다.

~~~json
{
  "annotation_id": "import_example_ger6",
  "raw_label": "Ger6",
  "source_confidence": null,
  "native_target": {
    "mc": 56,
    "mn": "54",
    "quarterbeats": "213",
    "duration_quarterbeats": "4"
  },
  "target": {
    "ir_document_id": "<verified-ir-revision>",
    "span": {
      "start": {"numerator": 213, "denominator": 1},
      "end": {"numerator": 217, "denominator": 1}
    }
  },
  "components": {
    "special_chord": "Ger6",
    "global_key_raw": "f",
    "local_key_raw": "iv"
  },
  "mapping_status": "ambiguous"
}
~~~

예시 mapping_status는 실제 bridge가 검증되기 전임을 나타낸다. 실제 도구에서 음표·마디·시간 검증을 통과하면 exact/verified_transform으로 바꾼다.

## 8. 코퍼스 adapter와 정렬 알고리즘

### 8.1 DCML부터 시작

입력: 동일 곡의 metadata/resource JSON, measures, notes, harmonies, 대응 score. 출력: IR, 원문 유지 ImportedAnnotation, AlignmentRecord, label parse/coverage report.

- 분수 문자열은 Fraction으로 읽는다. CSV/TSV float 변환 후 분수로 되돌리는 방식은 피한다.
- mc/mn, 마디 내부 onset, quarterbeats, 반복 확장 여부를 함께 검사한다.
- 원본 표의 quarter 좌표와 score 계산 좌표가 다르면 오차를 임의 보정하지 않는다. 판본·반복·분할 마디 차이를 조사한다.
- 악보와 notes 표의 pitch spelling/onset/duration을 표본이 아니라 지원 구간 전체에서 대조한다.
- label 전체 원문과 key/change/cadence/phraseend 구성 요소를 모두 저장한다.
- 다음 화음 위치로 span을 추정할 때 원본 duration 유무와 추정 정책을 기록한다. 마지막 행을 무조건 곡 끝까지 늘리지 않는다.
- unsupported syntax는 격리하고 원문은 유지한다.

### 8.2 다른 adapter의 차이

| Adapter | 필수 처리 | 실패하기 쉬운 가정 |
| --- | --- | --- |
| When in Rome | metadata로 source/annotator 확인, analysis.txt 포함, RomanText key/meter/beat/copy/repeat 구문 해석 | .rntxt만 읽으면 사람 분석 전체가 수집된다고 생각하기 |
| TAVERN | **kern/**harm/**function spine 동기화, 마디/시간 복원, 주석자 A/B 별도 track | 두 분석을 하나의 확정 답으로 합치기 |
| ChoCo | provenance namespace, score/audio timing, 원 dataset/변환 stage 추적 | JAMS time 1.1 등을 일반 quarter float로 읽기 |
| YCACL | header 없는 열 계약 검증, pitch slice와 추정 tonic/mode 분리, ? 결측 유지 | Roman·Cadence gold로 간주하기 |
| Taking Form / ASAP | 형식 구간 또는 악보-연주 beat mapping을 별도 extension으로 저장 | 형식 구간·연주 길이를 화성 span으로 바꾸기 |

ms3/music21 등 도구는 버전 고정 adapter로 활용 가능하나, 출력이 곧 공통 계약이라고 가정하지 않는다. 도입 시 현재 설치 버전과 라이선스·변환 semantics를 확인한다.

### 8.3 정렬 승인 규칙

1. 원본/판본 식별과 timeline 종류 확인.
2. 마디 map 생성; missing/duplicate printed number를 허용하되 sequential ID는 유일하게 유지.
3. 분수 시각과 note fingerprint로 주석 target 계산.
4. 참조 음표 존재·span 범위·part 동기화·음고 기초 대조.
5. exact/verified_transform만 평가·사례 검색의 기본 집합으로 승인.
6. ambiguous/orphaned는 UI 검토 대상으로 분리하고 누락 비율을 보고. 성공 항목만 출력해 전체 성공처럼 보이지 않게 한다.
7. 반복을 펼친 주석은 occurrence ID를 사용한다. 서로 다른 반복 해석을 한 written span에 덮어쓰지 않는다. v0.1에서 대응 불가하면 보류한다.

### 8.4 MIDI·MusicXML·MXL·MEI 입력 정책과 성능

MXL은 ZIP 구조에 MusicXML이 들어 있는 **압축 악보 형식**이다. MIDI는 note on/off와 연주 시간 중심의 파일이다. MIDI의 확장자를 `.mxl`로 변경해도 MusicXML이 되지 않는다. MIDI→MusicXML은 박자 격자화, 쉼표, 성부 분리, 음이름 철자, 조표·음자리표, 타이/beam/슬러/가사 등을 추정하는 **악보 재구성** 작업이며 원본에 없던 정보를 확정 사실로 취급할 수 없다.

| 입력 | 원본 보관 | 분석 연결 |
| --- | --- | --- |
| `.xml`/`.musicxml`이며 MusicXML root | 원본 그대로 + raw hash | 정식 IR adapter. XML root 검사 필수 |
| `.mxl` | MXL 원본 + 내부 rootfile 경로/hash | 컨테이너 검사·압축 해제 후 동일 IR adapter. ZIP의 임의 첫 XML을 악보로 택하지 않음 |
| `.mid`/`.midi` | 연주 파일 원본 + timing metadata | 별도 performance event layer. 대응 악보가 있으면 score↔performance alignment |
| MIDI만 있고 악보가 필요함 | MIDI 원본과 새로 만든 MusicXML/MXL 각각 보관 | 격자화·성부·철자 추정 정책과 불확실성/검수 기록. 생성 악보는 별도 edition/revision |
| `.xml`이지만 MEI root | MEI 원본 | MEI adapter 또는 검증된 변환을 거쳐 IR. MusicXML로 오인 금지 |
| CSV/TSV/JAMS | 표/주석 원본 | source-specific label/time adapter. 독립 악보 여부 별도 확인 |

한 형식으로 전체 원본을 강제 변환하지 않는다. Asset의 `source_format`, `container_format`, `inner_format`, raw_sha256, 내부 MusicXML hash, parser_version, derivation 관계를 분리한다. 같은 음악의 `.musicxml`과 `.mxl`이 동일한 악보인지 확인할 때는 파일 바이트 hash만 비교하지 않고 내부 XML/정규화된 음표 event의 동등성을 검증한다. MXL에서 기존 MusicXML로 내보낸 경우 조표·박자·타이·성부·가사·음표 ID 및 주석 위치가 유지되는지 회귀 확인한다.

현재 MusicSearch 검색 DB의 `works` 테이블은 source 경로와 `notes` JSON을 저장하며, 악보를 열 때 원본 XML을 별도로 읽어 캐시한다. `sourceXml()`의 `.mxl` 분기는 일반 MXL parser가 아니라 PDMX의 대응 `.xml` 경로를 읽는다. 따라서 MusicXML 파일만 일괄 MXL로 치환하면 현재 viewer가 읽지 못할 수 있고, 검색 SQLite 용량도 거의 줄지 않는다.

MXL은 디스크·전송량 절감 목적으로 선택할 수 있으나, 악보 열기·화성 분석의 지연 개선은 별도 측정이 필요하다. 압축 해제와 XML 파싱, 음표 추출·악보 렌더는 여전히 수행한다. 20–50개 대표 악보에서 원본 XML과 올바른 MXL 컨테이너의 저장량, cold/warm 열기 p50/p95, CPU/메모리, index build time을 측정하고, 같은 IR event/표시 결과를 확인한 다음 적용 범위를 정한다. 기존 원본은 그 전에 교체하지 않는다. [MusicXML 4.0 MXL 규격](https://www.w3.org/2021/06/musicxml40/tutorial/compressed-mxl-files/)을 따른다.

## 9. 공통 화성 엔진: 계산 순서와 규칙

### 9.1 입력과 성부 역할

입력은 Canonical IR + profile + 대상 범위 + 선택적 외부 조건이다. 구조 분석의 선율은 검색에 사용한 part와 분리하여 상성부/연속성 기반의 후보로 고른다. 매 순간 가장 높은 음을 잇는 것과 주선율 추출은 다르다. 성부 교차·피아노 장식·일시적 고음에서는 voice continuity와 반복 대응을 함께 쓰며 후보와 근거를 남긴다.

화성에는 모든 관련 성부를 사용한다. 실제 최저음, 베이스 성부 후보, 화음 근음 후보를 구별한다. 원음 written pitch와 concert pitch를 보존하고 비교 기준을 run에 명시한다. 음역 밖 cue/ossia/percussion은 정책으로 제외하되 원본에서 삭제하지 않는다.

### 9.2 관찰 feature → 후보 생성

A. **시간 사건**: attack, release, tie continuation, rest gap, meter change, explicit fermata/breath를 수집한다. 반복/타이/셋잇단음표를 정확히 처리한다.

B. **관찰 구간**: 모든 onset마다 새 화음을 확정하지 않는다. active sounding note 집합, attack 집합, 지속 시간, 철자, register, 실제 bass를 시간 slice로 계산한다.

C. **여러 길이의 화성 후보 span**: attack/release/박 단위 후보와 긴 지속 구간을 조합한다. 창 크기는 고정 quarter 상수만 쓰지 않고 실제 박 단위와 문맥 필요에 맞춘다.

D. **조성 후보**: 조표는 prior일 뿐이다. 지속된 음도 분포, 선율·베이스 움직임, 후보 진행·이끈음 해결을 함께 사용한다. 짧은 적용화음 하나만으로 전조를 확정하지 않는다. 국소 key, tonicization, modulation은 별개 후보를 유지한다.

E. **화음 후보**: spelling과 문맥을 사용해 root/quality/inversion/applied target/생략음/NCT 가능성을 만든다. 장·단·감3화음 외의 기본7화음, 적용화음, 차용화음부터 단계적으로 늘린다.

F. **성부진행/NCT**: 계류·경과·보조·전타·선행 가능성을 앞뒤 음과 박 위치·지속·해결 방향으로 평가한다. 짧은 음=NCT라는 규칙은 금지한다. 해결음이 창 밖이면 문맥 확장 또는 보류한다.

G. **구간화 선택**: 후보 span을 DAG로 연결하고 DP 또는 beam search로 전체 진행 점수를 비교한다. 너무 잦은 화성 변경, 불필요한 조성 변경, 관찰음 설명 실패, 성부진행 충돌에 각각 별도 비용을 둔다.

제안 점수는 observed-tone fit + spelling/context fit + voice-leading fit + duration/metric fit − unexplained-tone cost − unsupported key-change cost − oversegmentation cost다. 가중치는 config에 보관하고 ablation으로 조정한다. 점수를 확률로 표시하지 않는다. 최상위 후보와 경쟁 후보, score 차이, 반대 근거를 저장한다.

### 9.3 점진적 구현 범위

**H1**: 기본3/7화음·전위·국소 key 후보·적용 딸림·타이/분산화음 관찰·variable span. 이 단계부터 기존 구현보다 넓은 후보를 다루되 고전 profile에 한정한다.

**H2**: 증6화음, 차용화음, 감7의 다의성, Neapolitan, 종지6/4, pedal, 주요 NCT 준비/해결, 표면/지배 화성 분리. 전문가 주석과 대조하지 않은 특수화음 자동 확정은 보류한다.

증6화음은 단순 pitch-class 집합만으로 딸림7화음과 구별할 수 없는 경우가 있다. 임시표 철자·국소 조성·증6 음정과 다음 진행을 확인한다. 종지6/4도 구성음만 보고 I64의 독립 으뜸 기능으로 고정하지 않는다. pedal 위의 화음에서는 bass를 항상 root로 삼지 않는다.

NCT와 화음은 상호 의존하므로 1차 후보 → NCT 조건부 평가 → 후보 재순위의 **제한된 재평가**를 사용한다. 초기 반복 상한은 2회로 설정하되 실험 파라미터임을 명시한다. 이전 후보·변경 이유를 보존하고 수렴하지 않으면 alternatives로 남긴다.

출력의 네 층:

1. observed_sonority: 실제 울린 음과 source IDs.
2. surface_chord: 국소적으로 가장 잘 설명하는 화음 후보.
3. functional_harmony: 해당 조성 안의 기능 후보.
4. governing_harmony: 여러 표면 움직임을 묶는 상위 해석.

후자의 셋은 모두 Analysis다. 같은 자료로부터 파생된 네 층을 네 개의 독립 증거로 계산하지 않는다.

## 10. Cadence를 구조 분석에 연결하는 방법

### 10.1 서로 다른 위치를 저장

Cadence span, 도착 음표 onset, 도착 화음, 구조적 종결점, 끝음의 sustain release, 다음 Phrase 시작은 다를 수 있다. 타이 끝음을 포함한 표시 범위는 실제 sounding release까지 보여 줄 수 있지만 다음 시작 음표까지 소유한다고 의미하지 않는다.

DCML의 { / } / }{는 각각 시작·구조적 종결·맞물림을 표현하는 규칙을 가진다. } 뒤에 tail/codetta가 있을 수 있으므로 }를 무조건 전체 Phrase의 끝으로 변환하지 않는다. 코퍼스의 phrase 모델도 별도 dialect 정책으로 보존한다.

### 10.2 종지 후보 판정표

| 후보 | 필요한 근거 예 | 부족하거나 반대인 경우 |
| --- | --- | --- |
| PAC | 고전 profile에서 V–I, 필요한 근음 위치와 선율 으뜸음 도착, 종결 문맥 | V–I가 통과 진행일 뿐이거나 inversion/선율 조건 불충족 |
| IAC | 정격종지 진행과 종결 문맥, PAC와 다른 선율/전위 조건 | profile마다 분류 차이가 있으므로 적용 정의 기록 |
| HC | 구절 종결에서 V에 도착, 앞 진행과 호흡 | V가 지속 중인 중간 지점이라는 이유만으로 HC 아님 |
| DC | 예상 V–I 해결이 다른 화음으로 전환되는 문맥 | V–vi만으로 언제나 기만종지라고 확정 불가 |
| EC | 종결 기대와 실제 회피가 확인되는 경우 | DC/구절 연결과의 구별에 문맥 부족하면 보류 |
| PC | IV–I 등의 변격 진행이 종결 기능을 하는 문맥 | 단순 IV–I 반주 반복은 종지 아닐 수 있음 |
| no_clear_cadence | 충분히 관찰했으나 명확한 종지 근거 없음 | 데이터 부족과 구별 |
| insufficient_evidence | 화음/선율/문맥/정렬 정보 부족 | 억지로 가장 가까운 유형을 고르지 않음 |

처음에는 PAC/IAC/HC/DC와 보류 상태부터 구현한다. 나머지는 corpus dialect와 profile 정의를 확정한 뒤 추가한다. Roman은 반드시 분석 key와 함께 출력한다.

### 10.3 Phrase와의 순환 방지

- P0: 기존 Phrase 결과를 동결해 baseline으로 저장.
- H0: **P0의 점수·레이블을 보지 않는** 화성/Cadence 실행. 후보 창은 모든 악보의 지속·휴지·진행 변화 등에서 생성하고 P0 경계는 추가 검사 위치로만 사용.
- Shadow: P0 경계와 H0를 비교해 제안만 출력. P0를 고치지 않음.
- P1: holdout 검증을 통과한 독립 H0 근거만 제한적으로 반영.
- Phrase를 근거로 만든 Pillar/Harmony 가설은 P1의 독립 입력에서 제외.
- dependency DAG의 원시 증거 집합을 비교하여 같은 rest gap/긴 음/박 위치를 여러 모듈이 중복 가산하지 않게 한다. lineage가 빠진 근거는 독립성을 인정하지 않는다.

화성은 경계를 **강화·약화·이동 제안**할 수 있다. V–I 하나로 강제 분할하거나 종지가 없다는 이유로 기존 호흡을 모두 합치지 않는다. 반복 선율의 대응 위치는 먼저 후보를 전달하되, 후속 화성이 달라지는 변형도 허용한다.

일반 규칙 카드 예:

- 조건: 짧은 반복 Motif 사이의 약한 경계이며 독립 H0에서 지배 화성이 이어짐.
- 지지: 뒤쪽의 긴 도착음과 종지 근거, 반복 대응.
- 반대: 명시적 쉼/페르마타, 다른 성부의 독립 종결, 사용자가 승인한 구조.
- 행동: 자동 병합 대신 병합 후보와 기존 분할을 함께 제시.
- 보류: 화성 후보 경쟁이 크거나 evidence가 Phrase에서 역유입됨.
- 검증: 기존 승인곡/다른 박자/다른 조성/분할이 맞는 반례에서 ablation.

## 11. 스타일·반주·편곡 사례를 위한 데이터

현재 코퍼스만으로 고전 조성 화성 평가와 조건부 생성의 기반은 만들 수 있다. 그러나 “잔잔하지만 풍부한 피아노 반주” 같은 요구를 안정적으로 실행하려면 추가적인 **역할·질감·난이도·요청-결과** 데이터가 필요하다. 작곡가 이름을 style label 하나로 붙이는 것으로 대체하지 않는다.

### 11.1 먼저 추출할 항목

| 항목 | 자동 관찰 | 분석/사람 확인 |
| --- | --- | --- |
| 편성·음역 | instrument, staff, note range, density | 실제 선율/베이스/내성 역할 |
| 리듬 | normalized attacks, 지속 비율, 반복, 쉼 | swing/feel, 반주형 이름 |
| 반주 질감 | 동시음 수, 분산 정도, bass pulse, register 분리 | arpeggio/Alberti/block/waltz/pad 등 |
| 보이싱 | 음정 간격, 중복, 성부 이동량 | 기능상 필수음·생략 허용 |
| 구절 내 변화 | 시작/중간/종결 위치별 밀도·음역 | buildup/closing/transition 역할 |
| 난이도 | 손별 동시음 폭·도약·속도·성부 수 | 손배치·페달·실제 연주 난이도 |
| 장식 | 작은 음가·보조 움직임·변형 대응 | 장식/골격 해석, 보존 필요성 |
| 스타일 | corpus/시대 metadata와 측정 feature | 적용 범위와 예외, 사람 승인 |

처음에는 검토 가능한 20–30개 반주 구간과 10개 내외 Melody/Piano Solo 대응쌍으로 시작한다. 이는 학습 충분량이 아니라 **계약과 추출기 검증 표본**이다. 다양한 스타일 성능을 보장하는 숫자로 사용하지 않는다.

### 11.2 AccompanimentPattern 계약

패턴은 실제 source span과 다음 정보를 가진다.

- meter/beat-unit 및 적용 가능한 길이, pickup 처리.
- bass/inner/upper 등 role lane과 원래 part/voice refs.
- rational onset/duration. 6/8의 점4분 박과 단순 8분 슬롯을 구별.
- 화음 상대 root/third/fifth/seventh 또는 scale-degree 후보. 원래 pitch spelling도 보존.
- octave/register, voicing spacing, doubling/omission 정책.
- articulation/dynamic 원문과 반복/종결 변형.
- 최소/최대 density, hand span, 이동량, 허용 tempo 범위.
- chord-type applicability: 3화음 패턴을 7화음·증6화음에 무조건 적용하지 않음.
- confidence/미확정 역할 및 human review, 사용 허가.

패턴에 있는 passing/neighbor tone을 모두 chord-tone 슬롯으로 바꾸지 않는다. 화음 변경을 가로지르는 sustain/tie의 처리도 선언한다.

### 11.3 Melody/Piano Solo 쌍의 사용

제목 → 작품 후보 → 선율 contour/리듬 정렬 → 전조/반복/마디 삽입 대응 → 검토 순으로 쌍을 확정한다. 두 판본이 완전히 같은 길이라고 가정하지 않는다.

정렬된 구간에서 유지/분할/연장/장식/추가 베이스·내성/재화성화 차이를 기록한다. 이 결과는 단일 악보에서도 사용할 **역할·장식·골격 추정 feature**를 검증하는 데 사용한다. 실제 추론 시 Melody 판본을 필수 입력으로 만들지 않는다.

후대에 편곡 결과를 보고 만든 설명은 inferred_caption으로 표시한다. 실제 사용자가 준 요청과 편곡 결과 쌍인 것처럼 학습시키지 않는다.

### 11.4 사용자 사례 저장

기본 전후 2마디와 필요한 해결/준비 문맥을 포함하되, 음악 단위가 더 길면 확장한다. 원본 XML 또는 재현 가능한 full-score asset, IR revision, 정확한 note/span target, 사용자 원문 설명, 시스템 당시 후보와 rule 버전, 수정안, 대안 해석을 묶는다.

이 사례에서 추출한 규칙은 제목/특정 마디가 아니라 음정·리듬·준비/해결·성부진행 조건으로 작성한다. 사례는 회귀 fixture로, 규칙은 별도 version으로 관리한다. 사례를 retrieval에 넣은 뒤 동일 작품을 맹검 test로 평가하지 않는다.

## 12. 작곡·편곡 실행 Harness

### 12.1 자연어 → 검토 가능한 요청 계약

다음은 제안 request 예다. 악보 시작 0부터 32 quarter 구간이며 4/4에서 8마디에 해당한다. 박자가 다르면 같은 32 quarter를 8마디로 해석하지 않는다.

~~~json
{
  "mode": "arrange",
  "target": {
    "start": {"numerator": 0, "denominator": 1},
    "end": {"numerator": 32, "denominator": 1}
  },
  "instrumentation": ["piano"],
  "preserve": {
    "melody_pitch": true,
    "melody_rhythm": true,
    "key": true,
    "meter": true,
    "phrase_layout": true
  },
  "harmony_policy": "preserve_selected_source_analysis",
  "allow_reharmonization": false,
  "style": {
    "profile": "common_practice",
    "texture": "broken_chord",
    "density": "low"
  },
  "playability_profile": "piano_intermediate_v1",
  "cadence_policy": "preserve",
  "candidate_count": 3
}
~~~

request에는 실제 score/IR revision, 보호할 선율 note IDs, 선택된 source analysis revision, profile/config version도 필수로 연결한다. “중급” profile은 구체적 손폭·도약·속도 기준이 등록되어야 한다. 위 예는 완성 schema가 아닌 설명용이다.

**Hard constraint**: 명시적 보존 음표, 악기 음역, 길이·박자, 금지된 재화성화, 선택한 필수 종지, 허용된 자료 사용.
**Soft objective**: 잔잔함, 밀도, 성부진행 부드러움, 패턴 다양성, 음색/스타일 유사도.

충돌하면 hard constraint를 몰래 완화하지 않고 “보존 선율과 지정 화성의 충돌” 같은 이유 및 대안을 보여 준다. harmony unknown 구간에서는 원화성을 보존했다고 말하지 않는다. 가설 A/B를 사용한 결과임을 표시한다.

### 12.2 편곡 파이프라인

1. **입력 검증**: IR/time/pitch/tie 유효성, 선율 역할 후보, 보호 범위 확인.
2. **전체 구간 화성 계획**: 주석 조건 또는 blind 후보에서 surface/governing/key/Cadence를 연결. 빈 구간·경쟁 후보 유지.
3. **사례 검색**: meter·profile·편성·화성 종류·길이·난이도에 맞는 pattern만 retrieval.
4. **구절별 패턴 계획**: 시작/유지/종결 위치에 density·bass pulse·register 변화 배치.
5. **베이스 생성**: 화성·전위 조건, 선율과의 거리, 음역·도약·종지 목표 만족.
6. **내성/voicing 생성**: 중요한 화음 음, 중복/생략, 성부 독립성·이동량 제약.
7. **리듬 실현과 장식**: 패턴에 음을 배정. 보존 선율을 침범하지 않게 별도 lane 유지.
8. **독립 검증**: 계획과 출력 음표의 비교. 실패 구간만 제한적으로 재생성.
9. **MusicXML 출력→재파싱**: tie, onset, duration, spelling, voice/staff가 유지되는지 비교.
10. **후보 비교**: 최대 3개 초안을 비교하고 사람이 승인. 자동 최종 정답 선언 금지.

원본 음표 수정은 새 score revision에서 수행한다. source event를 직접 덮어쓰지 않는다.

새로 만든 음표의 source reference를 기존 원본 음표인 것처럼 위조하지 않는다. 생성 중에는 plan/생성 연산을 참조하는 별도 event derivation을 유지한다. 최종 MusicXML을 새 SourceAsset으로 등록하고 재파싱하여 정식 Core의 source_ref를 확보한 뒤, 원본→계획→생성 event의 대응표를 별도 계보로 연결한다.

### 12.3 작곡 파이프라인

입력 seed melody/motif가 없을 수도 있다. 길이·박자·편성·style·형식·종지·조성 이동 요구를 먼저 구조화한다.

형식/구절 계획 → 모티프 원형과 변형 계획 → 화성 리듬·조성·종지 계획 → 선율 후보 → 베이스·내성 → 리듬/표현 → 검증 순이다. 주어진 선율이 있으면 선율 제약을 먼저 고정하고 화성 후보와 공동 조정한다. 모든 경우 화성을 무조건 선율보다 먼저 확정하는 것은 아니다.

반복은 exact copy뿐 아니라 이조·끝음 변형·리듬 변형·연장·축약을 계획에 명시한다. 전혀 다른 선율을 같은 Motif라고 설명하지 않도록 interval/contour/rhythm 대응을 검증한다.

재생성은 최대 횟수·실패 사유·수정 범위를 run config로 제한한다. 만족하지 못하면 초안+위반 보고서를 반환한다. 기존 악보에 있는 짧은 패턴을 사용했다는 사실만으로 저작권 안전을 보장하지 않으며, 긴 선율 복제/근접 중복은 별도 검색·검토한다.

## 13. 규칙·사례 검색·AI의 역할

- **규칙/결정론적 코드**: 파싱, 시간·ID, 관찰 feature, hard constraint, 무결성·재현 검증.
- **사례 검색**: 조성 상대 진행, 리듬·음정·성부진행·구절 역할이 비슷한 출처 있는 사례 제공.
- **통계/학습 모델**: 후보 순위, melody/ornament 역할, 스타일 pattern 선택, 추후 calibration.
- **LLM**: 자연어 요구 구조화, 경쟁 해석 설명, 검토 가능한 생성 계획과 후보 제안. XML 사실이나 corpus label을 임의로 수정하지 않음.
- **사람**: 모호한 해석·스타일·연주성과 의도 검토.

LLM API는 provider/model/version/prompt/schema를 바꿀 수 있는 별도 adapter로 둔다. 모델이 없어도 수입·평가·기본 규칙 분석이 돌아가야 한다. 모델 출력은 schema validation, event 참조 검증, constraint 검사 후에만 다음 단계로 전달한다.

문서 요약만 프롬프트에 붙이는 것으로 음악 능력이 확보되었다고 가정하지 않는다. 요청 범위의 음표·음가·성부·조성 후보·검색 사례를 구조적으로 제공한다. 사용 허가와 전송 범위를 확인하기 전 코퍼스 전체를 외부 API에 전송하지 않는다.

초기 목표는 fine-tuning이 아니라 **정렬된 사례+평가 세트+규칙+검색**이다. 이후 평가에서 무엇이 부족한지 확인한 후 모델 학습을 결정한다. 고가 모델의 채택도 정확도·지연·비용을 동일 holdout으로 비교한 뒤 결정한다.

### 13.1 음악 이론 문서 → 검증 가능한 규칙

MMIS와 Harmony Analysis Harness Guide 등 사용자의 이론 정리 문서는 **규칙의 출처와 용어 사전**으로 활용한다. 문서 전체를 Core 필드나 확정 정답으로 바꾸지 않는다. P0에서 실제 문서 revision과 서로 다른 설명을 대조하고 필요한 문서/절만 등록한다.

신설 TheoryRuleRecord는 rule_id/version, source_document/hash/section, 적용 profile, 전제 조건, 관찰 feature 목록, 해석 가설, 반대 근거, 보류 조건, 예외, positive/negative case refs, test IDs를 갖는다. 책/문서의 서술과 코드로 계산한 조건은 별도 필드로 두고, 사람이 승인한 규칙만 운영 rule set에 포함한다.

예를 들어 “증6화음은 V로 향한다”라는 요약만으로 판정하지 않는다. 필요한 철자·증6 음정 관계·국소 key 후보·성부별 해결·다음 화음의 근거를 계산하도록 나누고, 이명동음 딸림7 및 해결되지 않는 사례를 반례로 넣는다. 출처마다 정의가 다르면 둘을 alternative/profile로 구별한다. 긴 원문 복제나 사용 권한이 불명확한 학습 전송은 하지 않는다.

### 13.2 사례 검색과 규칙 개선의 절차

Case retrieval은 조성 상대 음도/음정, duration/박 위치, bass motion, 화성 후보 진행, NCT 준비·해결, 종지 역할, texture로 단계별 필터와 순위를 계산한다. embedding만으로 label을 복사하지 않는다. 이조 불변 feature와 원래 spelling·register를 함께 유지하며 왜 비슷한지와 다른지를 출력한다.

사용자 설명 저장 → 정확한 event/span 연결 → 수정안/대안 검수 → 유사 사례·반례 검색 → 일반 rule 변경 제안 → ablation/개발 회귀 → 미사용 holdout 평가 → 승인 release의 순서로 진행한다. 사람의 새 교정 한 건이 곧바로 전곡 규칙을 바꾸지 않는다. 승격되지 않은 사례도 retrieved-case evidence로 제시할 수 있으나 출처와 상태를 명시한다.

화성 사례가 늘면 후보 판별·Cadence·생성 제약의 근거는 풍부해질 수 있지만 **저장만으로 알고리즘이 자동 학습되는 것은 아니다**. 규칙 변경, 검색 집합 갱신, ranker 학습, calibration 중 어떤 경로가 바뀌었는지 run/version에 기록하고 각각 평가한다.

## 14. 평가·테스트·출시 조건

### 14.1 데이터 및 계약 gate

승인된 subset에 대해서 다음은 100%를 요구한다. 전체 corpus가 100% 처리된다는 의미는 아니다.

- schema 및 reference integrity 통과, 음표/쉼표 source traceability.
- 유리수 시간 일치, tie chain 및 transposition 일관성.
- 같은 입력/버전 재실행 시 동일 entity IDs와 의미 출력. 실행 시각/run ID는 비교 제외.
- 학습·개발·평가 집합 간 work family/annotation lineage 누수 없음.
- 오류 항목을 orphan/unsupported report에 빠짐없이 기록.
- 원본/주석 hash 변화 시 cache와 정렬 승인을 재검토.
- 생성 결과의 hard constraints 및 export/reparse 보존 통과.

### 14.2 음악 평가 지표

| 평가 | 지표 | 주의 |
| --- | --- | --- |
| 정렬 | 승인 coverage, exact/transform/ambiguous/orphan 비율 | 성공 건만 denominator로 잡지 않음 |
| 화성 | duration-weighted root/quality/inversion, key-conditioned Roman, key accuracy | root만 맞은 것과 기능까지 맞은 것 구별 |
| 화성 구간 | boundary precision/recall, span overlap, over/undersegmentation | 모든 onset을 잘라 점수 높이지 않음 |
| 특수화음 | Ger/Fr/It6 등 confusion matrix, 적용화음/감7 구별 | 희귀 유형별 표본 수 표시 |
| Cadence | type + arrival point, no-cadence false positives, abstention coverage | 구조적 끝/다음 시작과 별도 평가 |
| Phrase | 경계/범위, 과분할·과병합, 반복 대응 일관성, 승인 사례 회귀 | 종지 F1로 Phrase 품질을 대신하지 않음 |
| 생성 | 선율·리듬 보존, 음역/손폭/시간 제약, 요구 충족, harmony consistency | 음악성은 검토자 별도 평가 |
| 스타일 | texture/density/register/pattern 요구 충족, 인간 선호 | 작곡가 분류 정확도만으로 평가 금지 |

point tolerance는 정확 일치와 미리 정한 박 단위 허용치(예: 1/4박)를 함께 보고한다. 6/8 등 박 단위 정책을 version으로 고정한다. tolerance를 결과를 본 뒤 바꿔 점수를 올리지 않는다.

정확도 95% 같은 목표를 자료 확인 전에 약속하지 않는다. P4에서 baseline과 표본 수를 측정하고, 출시 기준·최소 개선 폭·허용 회귀를 사전 등록한다. 희귀 유형은 표본 부족 상태로 표시한다. 주석자 간 이견은 단일 gold로 강제 통합하지 않고 alternative-aware 평가를 병기한다.

### 14.3 필수 fixture 목록

- 단선율/다성부/피아노2staff/cross-staff, 쉬는 성부와 들어오는 성부.
- 마디선 타이, 온음표 연속, 종지 도착음의 타이, 숨은 쉼표.
- pickup/2분박/6/8/박자 변경/셋잇단음표/반복·대체마디.
- written/concert 차이, 동일 MIDI의 다른 철자, 증6화음/딸림7 구별.
- 분산화음, pedal, 계류/경과/전타, 종지6/4, tonicization와 전조.
- V–I이지만 종지가 아닌 경우, HC처럼 보이지만 이어지는 경우.
- 같은 Motif + 다른 화성 결말, 짧은 Motif 반복이 한 Phrase인 경우.
- 미지원 label, 누락 주석, 잘못된 판본, 원본 수정 후 끊어진 mapping.
- Melody/Piano Solo 쌍, 한 판본만 있는 악보.
- 생성 요청 충돌, hard constraint 실패, export roundtrip 손실.

기존 사용자 승인 사례는 개발 회귀 묶음으로 유지한다. 새 규칙은 문제 사례만 고친 결과가 아니라 전체 회귀 diff와 원인 code를 제출해야 한다.

## 15. UI·API·운영 설계

### 15.1 공유 악보 Viewer

MusicSearch의 하나의 악보 renderer를 유지하고 Analysis/Annotation/Generation은 overlay와 오른쪽 상세 panel로 연결한다. 별도 renderer로 음표 ID가 달라지는 문제를 만들지 않는다.

- Phrase, Motif, Harmony, Cadence, Pillar는 서로 다른 높이/표시 방식.
- corpus annotation / automatic hypothesis / human reviewed를 범례로 구별.
- 화성 클릭: “국소 조성 / 이전→도착→이후 / 종지 후보 / 실제 음 / NCT 후보 / 근거 / 반대 근거 / 출처”.
- Roman 부분만 Campania. 일반 텍스트·unknown·시작/마지막 음높이와 음가는 기본 폰트.
- source measure와 actual displayed measure가 다르면 둘을 명시.
- 주석 없음과 분석 실패/계산 중 상태를 구별.
- 분석 선택 시 해당 span 강조와 오른쪽 panel 선택을 동기화.
- 수정은 “현재 해석 승인 / 수정 / 거절 / 판단 보류 / 대안”으로 저장. 원본 주석 덮어쓰기 금지.
- 생성 미리보기에서 보호 선율, 추가 반주, 바뀐 음표, 검증 경고를 구별.

화성 표시를 검색·구조 분석 Viewer에 연결하는 시점은 “모든 화성 기능 완성 후”가 아니라 **계약과 표시가 안정된 뒤의 shadow integration**으로 한다.

1. 검토 전용 Viewer에서 schema, ID, `[start,end)`, source/automatic/reviewer provenance를 먼저 검증한다.
2. 공유 Viewer에는 기본 OFF인 `화성 분석(실험)` overlay와 읽기 전용 오른쪽 panel로 연결한다. 이 단계에서는 Phrase/Motif/Pillar 점수를 바꾸지 않는다.
3. 같은 artifact를 두 Viewer에서 표시하는 contract/fixture test와 기존 악보 렌더 회귀를 통과시킨다. Python의 화성 규칙을 JS에 재구현하지 않는다.
4. 독립 holdout에서 cadence/harmony 증거의 유효성이 확인되면 shadow phrase suggestion만 생성한다.
5. 사용자 승인 사례와 전체 회귀 gate를 통과한 증거만 구조 분석에 제한적으로 반영한다. feature flag를 끄면 기존 구조 결과가 완전히 재현되어야 한다.

따라서 현재 source annotation과 compatibility/context evidence는 공유 Viewer에 **시각화만 먼저 연결 가능**하다. 원자료를 볼 수 있는 scorer의 결과는 label leakage 때문에 blind 자동 화성 분석 결과처럼 표시하거나 구조 점수에 직접 넣지 않는다.

이를 위한 첫 교환 계약으로 `harmony-overlay-artifact`를 구현했다. 곡별 `harmony_overlay_artifact.json`에는 rational span, annotation/event reference, Roman label과 Campania font role, surface/context evidence 요약, provenance를 넣는다. 2026-09-25의 `0.3.0`에서는 `default_enabled=true`, `interaction_mode=ambiguity_review`로 갱신하고 sparse-review용 `review_candidate`, `review_priority`, `review_reasons`를 추가했다. `structure_influence=none`은 계속 schema 상수라서 소비 Viewer가 검토용 source label을 구조 분석 입력으로 취급하지 못하게 한다. 구현은 `src/musicanote_harness/harmony_overlay_artifact.py`, schema는 `schemas/harmony_overlay_artifact.schema.json`이다.

중요한 정정: 위 artifact는 source annotation 감사 레이어이지 일반 악보 자동 분석의 본체가 아니다. 일반 Viewer에는 별도의 blind hypothesis layer가 필요하다. 첫 연결인 `blind-full-score-harmony-v0.1`은 모든 악보에서 자동 span, 절대 화음, 조성 후보와 로마숫자 후보를 만들며, source annotation은 예측 시 보지 않는다. annotation은 평가·calibration·case retrieval에만 사용한다. 이 분리를 지켜야 annotation을 그대로 복사하는 데이터 누수와 실제 신규 악보 분석을 구별할 수 있다.

### 15.2 API 제안

아래 endpoint는 신설 제안이며 현재 존재함을 뜻하지 않는다.

| 요청 | 역할 |
| --- | --- |
| POST /api/corpus/import-jobs | registry subset과 adapter 버전으로 수입 job 생성 |
| GET /api/jobs/:id | 단계·진행량·오류·artifact 조회, 취소/재개 상태 |
| POST /api/harmony/runs | IR revision + mode + scope + profile 분석 |
| GET /api/harmony/runs/:id | 후보·근거·mapping·완료 상태 |
| POST /api/generation/plans | 요청 정규화와 constraint 충돌 검사 |
| POST /api/generation/runs | 승인된 plan의 후보 생성 |
| POST /api/reviews | 정확한 target revision에 대한 교정 기록 |

mutation에는 idempotency key를, review에는 expected revision을 사용한다. 이전 revision을 보고 한 수정은 409/stale-target 등 명확한 응답과 재정렬 제안으로 처리한다. server가 오류를 숨겨 빈 분석을 성공처럼 반환하지 않는다.

cache key에는 IR hash, schema/parser/engine/rule/profile/config version, annotation track revision, scope, pitch basis, inclusion policy를 포함한다. 악보 렌더 cache와 분석 cache는 분리한다. worker 작업을 UI thread에서 실행하지 않는다. 파일 해시가 같은 원본의 재파싱과 전체 악보 재렌더를 불필요하게 반복하지 않는다.

병렬 실행은 같은 immutable 입력에서만 하고, registry 승인·review 갱신은 충돌 검사를 한다. 장기 job은 단계별 checkpoint, 실패 재시도 횟수, 취소, 부분 결과와 오류 요약을 지원한다. 실제 표본으로 import/analysis/render의 p50/p95를 측정한 후 예상 시간을 표시한다.

## 16. 단계별 개발 작업 카드

다음 카드는 단계별 목표다. **P2/P3의 DCML 수입과 P5의 독립 표면·1–4박 구간 후보 생성만 파일럿으로 구현**했다. P0/P1의 생산 계약·코퍼스 registry, P4의 독립 holdout 평가, P5의 기능·조성·성부/NCT 통합, 그 이후 단계는 미완료다. 두 방식의 비교와 회귀는 각각의 파일럿 개발 기록을 확인한다. 각 단계 PR/변경 기록에는 입력 fixture, 실행 명령, 출력 예, 자동 테스트, 음악적 의미와 제한, 되돌리기 방법을 포함한다.

### P0 — 현재 상태 동결과 계약 합의

- 선행: 없음.
- 작업: 기존 parser/UI/Phrase/Harmony 출력 snapshot, git commit·설정 기록. OQ-021~025 및 기존 ID/time 관련 문제 우선 처리.
- 산출물: baseline manifest, contract decision log, feature coverage matrix, 개발 회귀/holdout 분할 계획.
- 완료: 같은 입력을 기존 방식으로 재현; schema family 충돌·point target·imported confidence 정책 문서 승인.
- 하지 않을 것: 기존 Phrase 규칙 변경, 대규모 parser 교체.

### P1 — Corpus registry·출처·중복·분할

- 선행: P0.
- 작업: 12–20곡 선정, SourceAsset/Edition/Track schema, hash와 provenance, 라이선스/lineage registry. 새 자료의 MusicXML/MXL/MIDI/MEI/CSV 형식과 용도 inventory를 추가한다.
- 산출물: physical/distinct/paired/human/automatic/unknown 보고서, 고정 split manifest.
- 완료: file count를 곡 수와 구별하고 변환 재수록을 연결; 같은 작품/주석 계보가 split을 넘지 않음.
- 실패 처리: 메타정보 부족은 unknown으로 격리, 추측으로 사람 정답 지정 금지.

### P2 — 정식 IR bridge·시간·ID 검증

- 선행: P0/P1.
- 작업: prototype와 MusicSearch event 표현 → formal IR adapter. missing source refs/전조/voice/tie/meter 처리. 원본 재파싱 필요 항목 명시. MXL은 컨테이너를 검증해 내부 MusicXML에 같은 adapter를 사용하고, MIDI/MEI는 별도 변환·정렬 경로로 둔다.
- 산출물: canonical-ir, source-to-ir map, native-time map, loss/validation report.
- 완료: 지원 표본 event reconstruction, IDs 재현, rational time/tie/source integrity 통과. 미지원 곡 목록 공개.
- 실패 처리: 손실 데이터는 exact 승인 금지. production viewer는 기존 경로 유지.

### P3 — ImportedAnnotation·DCML 정렬

- 선행: P1/P2.
- 작업: 새 주석/정렬 schema와 validator, dialect parser, Ger6/HC/phraseend fixture, revision-aware remapping.
- 산출물: imported labels, alignment status, source row↔score event 조회.
- 완료: 실제 01-1의 Ger6와 다음 V/HC를 악보 위치에 재현; 모든 승인 주석 참조 유효; missing confidence 허위 생성 없음.
- 실패 처리: orphan/ambiguous 유지, 수입 오류와 음악 해석 불확실성 분리.

### P4 — 평가 Harness와 주석 검토 UI

- 선행: P3.
- 작업: blind/assisted 분리, 기존 화성 baseline scorer, corpus와 예측 동시 overlay, holdout 평가 자동화.
- 산출물: metric report, error categories, split/run manifest, review export.
- 완료: 같은 run 비교 가능; XML harmony 누수 테스트; 표본별 오류 원인을 음표에서 확인.
- 결정: 이후 H1/H2/Phrase 배포 기준을 이 시점에 사전 등록.

### P5 — H1 독립 화성 엔진

- 선행: P4.
- 작업: independent candidate windows, concert/all-voice observations, variable segmentation, 기본7/전위/적용화음/key 후보.
- 산출물: 네 층 중 observed/surface/function, alternatives, dependency graph, score breakdown.
- 완료: blind baseline 대비 개선·회귀 보고, missing_phrase_boundary 후보 탐지, Phrase 점수 입력 없이 실행 가능.
- 배포: shadow만. 근거 중복/lineage 누락이면 Phrase feed 차단.

### P6 — H2 특수화음·NCT·지배 화성

- 선행: P5.
- 작업: Aug6/차용/감7/6-4/pedal/NCT 문맥과 governing span, 제한된 후보 재평가.
- 산출물: 유형별 confusion report, counter-evidence, abstention 이유.
- 완료: 철자/해결/문맥 fixture, 희귀 유형 평가와 지원 범위 공개.
- 보류: 지원하지 않는 스타일에서는 확정 대신 unknown/alternatives.

### P7 — Cadence와 Phrase 제안 연결

- 선행: P5, 해당 특수 진행에는 P6.
- 작업: point/span 분리, independent H0 → shadow boundary suggestions → 제한된 P1.
- 산출물: 원래 경계/제안/변경 이유, 반복 대응 diff, evidence firewall report.
- 완료: 사전 등록 gate 통과 및 기존 승인 사례 회귀 검토 후 feature flag로 적용.
- 보류: 화성이 불확실한 문제는 기존 일반 규칙으로 억지 해결하지 않음.

### P8 — 코퍼스 adapter 확장

- 선행: P3/P4.
- 작업: WiR human subset → TAVERN alternatives → ChoCo score subset 순.
- 산출물: 각 dialect/time/provenance fixture와 coverage report.
- 완료: 독립 정렬 검증과 중복 분할 검사 통과. audio-only는 별도 정렬 계획까지 보류.
- 참고: 데이터 양 증가는 엔진 정확도 향상과 별도 지표로 보고.

### P9 — Style·Pattern·편곡 대응쌍

- 선행: P2/P3, 자동 화성 조건 추출은 P5/P6.
- 작업: 20–30 구간/약10쌍 표본, 역할 추정, 반주 pattern contracts, chord-relative encoding, 장식 차이 기록.
- 산출물: style/pattern catalog, source↔normalized pattern, 역할 검수 화면.
- 완료: 원형 재실현과 조/음역 이동 테스트; 한 판본만으로도 feature 추출 가능.
- 실패 처리: Melody matching 불명확하면 쌍 학습 대상 제외.

### P10 — 요청·계획·제약 validator

- 선행: P9; 단순 계약 작업은 P4 후 가능.
- 작업: Arrangement/CompositionPlan, hard/soft constraints, 자연어 adapter(선택), conflict explainer.
- 산출물: plan schema, 예제 요청, constraint test suite, 보존 event map.
- 완료: 허용되지 않은 선율/조성/길이 변경 차단, 모순 요청에 설명 반환.
- 배포: 생성 없이 계획 검토 기능부터 가능.

### P11 — 8–16마디 피아노 편곡 MVP

- 선행: P10 + full_span 화성 또는 승인 source annotations.
- 작업: 보호 선율 + bass + inner voice + pattern realization, 최대3후보, 독립 validator, MusicXML roundtrip.
- 산출물: 원본/계획/생성/검증/검수 묶음.
- 완료: hard constraints 100% 통과 subset, source derivation 보존, 전문가가 비교 가능한 UI.
- 제한: style/난이도 지원 범위를 명시. 정확한 학습 모델 없어도 규칙+사례로 시작 가능.

### P12 — 작곡 MVP

- 선행: P10/P11.
- 작업: form/motif variation/harmonic rhythm/cadence 계획, 선율 생성, 제한적 재생성.
- 산출물: 동일 요구의 후보, motif 계보, 제약 충족·유사성·음악성 검토표.
- 완료: 길이/박자/편성/요구 보존, 반복변형 설명과 실제 음표 일치, 실패 이유 재현 가능.
- 제한: 듣기 좋은 결과를 자동 점수 하나로 확정하지 않음.

### P13 — 운영 확대와 지속 검증

- 선행: 해당 기능별 gate 통과.
- 작업: DB/Parquet adapter, job 재개·cache·성능 측정, immutable releases, corpus/engine/model drift 평가.
- 산출물: release manifest, rollback 절차, data/model cards, change history.
- 완료: 사용자 review가 버전 변경 후에도 유지, broken mapping 검출, 독립 holdout과 비용·지연 보고.
- 확대: 고전 profile 다음 팝/재즈·다른 편성은 별도 corpus/profile 검증 후.

**운영 준비의 첫 착수 범위는 P0–P3다.** “모든 코퍼스를 한 번에 학습”이나 “전곡 AI 화성 분석”부터 시작하지 않는다. 첫 성공은 *원본 악보의 실제 음표 위에 외부 화성 주석을 정확한 위치·출처로 표시할 수 있음*이다. P5 표면 화음 후보는 P4 평가 gate 전의 **실험용 blind baseline**으로만 실행하며, Phrase나 생성 기능에 공급하지 않는다.

## 17. 개발자 전달 패키지와 코드 소유 경계

제안 module 위치이며 아직 생성되지 않았다.

~~~text
K:/Music Analysis/src/musicanote_harness/
  corpora/registry.py
  corpora/adapters/{dcml,romantext,tavern,choco}.py
  alignment/{measure_map,annotation_map}.py
  ir_bridge/{prototype_to_formal,validation}.py
  evaluation/{harmony,cadence,structure,generation}.py
  generation/{requests,plans,constraints,patterns}.py
K:/Music Analysis/tests/
  fixtures/corpora/
  fixtures/harmony/
  fixtures/generation/
K:/MusicSearch/server/
  harmony-service.mjs
  annotation-service.mjs
  generation-service.mjs
~~~

코퍼스 변환·평가 Python과 웹 serving JS의 경계를 명시한다. 동일 시간 계산/화성 규칙을 Python·JS에 따로 구현하지 않는다. 하나의 authoritative analyzer artifact 또는 service를 JS가 소비하고, 공통 schema/fixture로 호환성을 검증한다. MusicSearch와 MusicStructureAnalyzer의 실제 현재 저장소 관계는 P0에서 확인하고 소유권을 정한다. 이 계획만으로 다른 저장소 파일을 덮어쓰지 않는다.

각 작업 인계에는 다음을 포함한다.

1. 목표와 비목표, 선행 task IDs.
2. 필드 계약과 실제 최소 입력/출력 fixture.
3. 함수/CLI/API 진입점 및 버전.
4. 단위·통합·음악 반례 테스트 명령.
5. 오류/보류 처리, 성능 측정.
6. sample score 화면과 source-linked 설명.
7. migration/rollback 및 사용자 review 영향.
8. 기존 승인 사례 전체 diff, holdout 결과.
9. 개발 로그 링크와 남은 미해결 항목.

CLI 명령 이름은 구현 PR에서 확정한다. 문서에 존재하지 않는 명령을 이미 실행 가능한 것처럼 적지 않는다.

## 18. 결정할 사항·위험·후순위

### 먼저 결정

- 정식 IR의 immutable document revision/ID registry 소유자와 prototype bridge 계약.
- point target 및 imported annotation schema; missing confidence 정책.
- written/repeat-expanded 정렬 지원 범위.
- metric beat 정책(단순/복합/변박), concert pitch 기준과 포함 성부 정책.
- 엔진 authoritative runtime 및 UI가 소비할 artifact 계약.
- 평가 split·gold 대안·기존 승인 사례의 개발/검증 역할.
- 라이선스/배포/외부 API 전송/학습 자격 기준.

### 주요 위험과 완화

| 위험 | 완화 |
| --- | --- |
| 데이터 많은데 실제 정렬은 틀림 | 작은 승인 subset과 coverage report, 원본 음표 검토 |
| 같은 주석 변환본을 여러 정답으로 셈 | work+lineage 연결 성분 분할 |
| 고전 기능화성을 팝/재즈에 강제 | profile 분리, 지원 밖 abstention |
| Phrase/Harmony/Pillar 순환 강화 | dependency DAG, primitive 증거 중복 제거, shadow gate |
| 새 parser가 기존 note ID를 바꿈 | revision map, legacy adapter, remapping 검수 |
| 생성기가 자기 점수로 자기 성공 확정 | 독립 constraint validator·holdout·사람 평가 |
| 코드 라벨만 학습해 실제 반주를 모름 | score-linked texture/voicing/pattern 데이터 |
| 문서만 늘어나 실행 위치를 모름 | 이 문서를 실행 진입점, 정본 규격/조사/로그 역할 분리 |

### 후순위

audio alignment와 performed timing, pedal inference, microtonal harmony, 전체 오케스트레이션, 고급 피아노 손배치 최적화, 광범위 팝/재즈 스타일, 대규모 모델 fine-tuning은 v0.1 필수 완료 항목이 아니다. 원본에서 읽을 수 있는 기보는 보존하되 해석 기능의 지원 여부를 별도로 표시한다.

## 19. 근거와 갱신 기록

- 로컬 조사 근거와 파일 수: [코퍼스 조사 보고서](CLASSICAL_HARMONY_CORPORA_AUDIT_2026-09-24.md).
- 실제 Ger6 및 작곡·편곡 데이터 적합성: [기초 조사](COMPOSITION_ARRANGEMENT_HARMONY_DATA_PLAN_2026-09-24.md).
- DCML label과 phrase 표지: [공식 reference](https://dcmlab.github.io/standards/build/html/reference/reference.html), [공식 specifications](https://dcmlab.github.io/standards/build/html/reference/specs.html).
- 코퍼스별 README/resource metadata/원본 TSV/XML을 각 adapter의 1차 근거로 삼는다. snapshot/commit을 manifest에 고정한다.
- 2026-09-24: 실행 계획 v0.1 작성. 현재 코드 제한, 주석/IR 정렬, 독립 화성→구조, 스타일·생성 계약, P0–P13와 gate를 정의했다. **이 문서 작성으로 parser 변경·코퍼스 일괄 변환·학습·생성 기능이 구현된 것은 아니다.**
- 2026-09-24: 새 코퍼스 네 종류의 형식과 MIDI/MXL 입력 정책을 §5/8 및 P1/P2에 추가했다. 현재 검색 DB와 악보 원본 로딩 경로를 확인했다. 파일 변환이나 저장소 교체는 실행하지 않았다.
- 2026-09-24: 주석 참고 방식과 프로젝트 경계를 §4.1에 결정·기록했다. 화성 엔진은 독립 모듈, 악보는 공유 viewer, 주석은 수입/정렬 후 색인 조회하며 실행별 정책을 남긴다.
- 2026-09-24: P2/P3의 DCML 파일럿 수입기, 출처·시간·음표 정렬 검증, 전곡 source-annotation context를 구현했다. 세 악장 결과와 실패/보류 사례는 [개발 기록](DCML_HARMONY_IMPORT_PILOT_2026-09-24.md)에 고정한다. 이 결과는 *원본 주석을 정렬한 것*이며, 독립적인 화성 예측 성능이 아니다.
- 2026-09-24: P5의 첫 독립 하위 단계로 전곡 beat window의 표면 화음 후보/보류 baseline을 만들었다. 정식 기능화성 분석과 분리하고, 주석 없는 IR만 사용한다. 세 악장 실행 수치·테스트·음악적 한계는 [독립 표면 화음 기록](BLIND_SURFACE_HARMONY_PILOT_2026-09-24.md)에 있다. P4 평가 gate를 거치기 전 구조 분석 입력으로 연결하지 않는다.
- 2026-09-24: 사용자의 ‘수직보다 펼친 구간’ 우선순위에 따라 1–4박 구간 후보기를 실험했다. 과도한 병합을 확인해 명확한 국소 후보·베이스 경계 보존을 추가했지만 Mozart 진단에서는 일부 회귀한다. DCML 표본에는 음표별 NCT 종류 정답이 없음도 확인했다. [구간 파일럿 기록](UNFOLDED_HARMONY_PILOT_2026-09-24.md)에 수치와 한계를 남기고 운영 연결은 보류했다.
- 2026-09-25: RomanText 1,902곡의 surface compatibility와 전후 화성 경계 문맥을 전수 계산했다. 공유 Viewer에는 기본 OFF·읽기 전용 실험 overlay로 먼저 연결하고, 구조 분석에는 holdout/shadow gate 전까지 공급하지 않는 순서를 §15.1에 고정했다. [RomanText evidence 기록](ROMANTEXT_SOURCE_EVIDENCE_2026-09-25.md)을 참조한다.
- 2026-09-25: 공유 Viewer 연결의 첫 단계로 score SHA-256 기반 bridge API와 MusicSearch 오른쪽 `화성 분석(실험)` 패널을 구현했다. exact source hash가 없거나 catalog가 꺼져 있거나 해석이 여러 개면 추측하지 않고 보류한다. 기본 OFF·읽기 전용이며 `structure_influence=none`이다. Canonical event ID와 Viewer note ID를 안정적으로 대응하기 전에는 악보 음표를 직접 색칠하지 않는다. 세부 계약과 검증은 [RomanText 수입·검토 기록](ROMANTEXT_IMPORT_AND_REVIEW_2026-09-25.md)에 있다.
- 2026-09-25: 동일 악보/동일 작품 이식보다 다른 작품의 유사 사례 검색을 우선한다는 결정에 따라 harmony case retrieval v0.1을 구현했다. query feature는 source label을 보지 않고 Canonical IR의 이조 불변 interval profile, 앞뒤 문맥, bass motion, duration/attack/vertical density만 사용한다. 동일 score를 제외하고 score별 최대 2건으로 다양화하며, raw label을 복사하지 않고 경쟁 alternatives와 유사/차이 feature를 반환한다. DCML 3 score에서 774 cases를 구축했고 실제 query에서 similarity 0.84–0.88인데도 VI/ii/V/I가 경쟁해 표면 유사성만으로 기능화음을 확정할 수 없음을 확인했다. [case retrieval 파일럿 기록](HARMONY_CASE_RETRIEVAL_PILOT_2026-09-25.md)을 참조한다.
- 2026-09-25: raw harmony label을 보존하면서 degree/case/alteration/quality/inversion/applied target/Aug6/Neapolitan/continuation/compound path를 별도 taxonomy로 분류했다. 774-case pilot은 parsed 728, partial 31, no-chord 15였다. 검색 결과에 raw-label과 family alternatives를 모두 추가하고, 유사 사례 feedback을 append-only로 저장하는 별도 schema/store를 만들었다. feedback은 adjudication과 holdout 전까지 training/rule update에 사용할 수 없다. 다음 단계는 두 악보 문맥을 함께 보는 case-review UI다.
- 2026-09-25: 데이터 구조를 먼저 고정했다. 43개 준비 score를 22개 work family로 묶고 exact-aligned 사례량을 기준으로 작품군 단위 train/dev/holdout manifest를 생성했다. 6,492개 case는 train 4,509/dev 982/holdout 1,001이며 work family·score hash·annotation hash 누수, manifest 누락, identity mismatch가 모두 0이다. dev/holdout query는 train case만 검색한다. 모든 case의 `training_eligible=false`는 유지한다. [Harmony Data Release](HARMONY_DATA_RELEASE_2026-09-25.md)를 참조한다.
- 2026-09-25: source label을 보지 않는 blind local-key 후보와 진입/종료 성부진행 evidence를 retrieval feature에 추가하고 dev 982건 대 train 4,509건 ablation을 실행했다. Family Top-1은 surface 36.76%, local-key 54.48%, voice-leading 43.89%, combined 56.11%였다. 이는 gold span이 제공된 사례 검색 평가이며 end-to-end 화성 분석이 아니다. holdout은 열지 않았고 구조 분석 영향도 계속 없다. [Feature Ablation](HARMONY_RETRIEVAL_FEATURE_ABLATION_2026-09-25.md)을 참조한다.
- 2026-09-25: NCT 이름을 붙이지 않고 성부별 순차 진행·원음 복귀·반음 해결·도약 뒤 반대방향 순차 진행 geometry를 source-linked evidence로 추가했다. v0.4는 Family Top-1 56.31%, Top-5 79.33%, MRR 0.6668로 소폭 개선했으나 Raw Top-1이 29.84%에서 28.51%로 하락해 승격 gate를 통과하지 못했다. `combined_v0.3`을 기본으로 유지하고 NCT geometry는 실험 evidence로 보존한다.
- 2026-09-25: RomanText 악보 검토 화면에 train-only 유사 사례 검색, 후보 원본 악보 문맥, append-only verdict/축별 평가를 연결했다. 피드백은 `training_eligible=false`, `rule_update_eligible=false`이며 구조 분석 영향은 없다. 후보 악보 rendering은 원본 기보 보존과 Canonical note trace를 유지한다. 구현·운영 계약은 [Harmony Case Review UI](HARMONY_CASE_REVIEW_UI_2026-09-25.md)를 참조한다.
