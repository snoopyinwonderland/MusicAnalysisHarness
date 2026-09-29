# Harmony Case Review UI — 2026-09-25

## 목적

RomanText 악보 검토 화면에서 현재 화성 구간과 다른 작품의 유사 화성 사례를 함께 보고, 사람이 유사성의 성격을 기록할 수 있게 했다. 이 화면은 자동 정답 생성기가 아니라 **source-linked 사례와 반례를 모으는 검토 도구**다.

## 화면 흐름

1. `http://127.0.0.1:8766/`에서 source score를 연다.
2. 악보 위 화성 기호 또는 오른쪽 화성 목록을 선택한다.
3. `유사 화성 사례`의 `다른 작품의 유사 사례 찾기`를 누른다.
4. train split에서 최대 6개 사례를 본다.
5. `후보 악보 열기`로 원본 악보의 전체 문맥과 보라색 사례 구간을 확인한다.
6. verdict, 선택적 0–4 평가축, 설명을 저장한다.

현재 예시 화면은 `/reviews/46fbaa52acc1c4b7/romantext-review.html`이다.

## 검색 계약

- query는 exact score-linked annotation span이어야 한다.
- query feature는 source harmony label을 보지 않는다.
- 후보는 data release의 `train` 사례로 한정한다.
- 동일 score를 제외하며 score별 결과는 1건으로 제한한다.
- 기본 profile은 dev ablation에서 선택한 `combined_v0.3`이다.
- similarity는 보정된 confidence나 화성 정답 확률이 아니다.
- 후보 raw label은 다른 작품의 원자료 주석이며 현재 악보로 복사하지 않는다.
- 경쟁 label/family의 분산은 불확실성 증거로 보존한다.
- Phrase, Cadence, Motif, Pillar 및 구조 분석 영향은 `none`이다.

## 피드백 계약

verdict는 다음 네 종류다.

- `useful_analogy`
- `similar_surface_different_function`
- `not_similar`
- `cannot_judge`

선택 평가축은 surface, bass motion, voice leading, harmonic function, NCT context, Phrase role이다. 모두 0–4이며 입력하지 않아도 된다.

저장은 `output/romantext-catalog-reviews-2026-09-25/harmony_case_reviews.jsonl`의 append-only record다. 같은 query/case를 다시 검토하면 이전 행을 지우지 않고 `supersedes_review_id`로 연결한다. 모든 새 행은 `training_eligible=false`, `rule_update_eligible=false`다. adjudication과 dev/holdout 재평가 전에는 검색 순위나 음악 규칙을 자동 변경하지 않는다.

## 구현

- 검색·저장 API: `src/musicanote_harness/romantext_catalog.py`
- 검토 화면: `src/musicanote_harness/romantext_review.py`
- 후보 악보 페이지: `src/musicanote_harness/harmony_case_context.py`
- 피드백 저장: `src/musicanote_harness/harmony_case_review_store.py`
- 피드백 schema: `schemas/harmony_case_review.schema.json`
- CLI: `serve-romantext-catalog --case-library --dataset-manifest --case-review-output`

API는 다음과 같다.

- `GET /api/harmony-cases/{catalog_id}?annotation_id=...&limit=6`
- `POST /api/harmony-case-context`
- `POST /api/harmony-case-reviews/{catalog_id}`

후보 악보는 처음 열 때만 생성하고 이후 cache한다. Canonical ID를 삽입한 MusicXML을 Verovio가 거부하면 원본 MusicXML을 다시 읽고 source order로 Canonical note ID를 연결한다. 기보를 IR에서 재구성하지 않는다.

## 검증

- Python compile 통과.
- catalog/review-store 단위 테스트 6개 통과.
- 생성 HTML의 inline JavaScript를 Node `--check`로 검사했다.
- WTC I Prelude 1의 첫 `I` 구간에서 train 사례 6건 반환을 확인했다.
- 후보 Beethoven quartet 사례의 score context 생성과 브라우저 열기를 확인했다.
- 실제 feedback 파일에는 테스트용 판단을 기록하지 않았다.
- 8766의 중복 server 세 개를 종료하고 현재 코드 server 하나로 재기동했다. 중복 listener가 있으면 요청이 구버전/신버전으로 분산될 수 있으므로 운영 launcher는 단일 instance lock을 후속으로 가져야 한다.

## 다음 단계

1. 실제 음악 판단을 30–50 query에 기록한다.
2. verdict와 축별 평가의 reviewer 일관성을 검사한다.
3. adjudicated dev feedback만으로 ranker 후보를 만든다.
4. 기존 `combined_v0.3`과 dev ablation을 비교한다.
5. 승격 gate를 통과한 뒤에만 holdout을 한 번 평가한다.
6. 자동 화성 hypothesis와 구조 분석 연결은 그 이후 별도 단계로 진행한다.

## 2026-09-25 — shared score viewer의 ambient ambiguity review

별도 후보 페이지를 하나씩 여는 피로를 줄이기 위해 MusicSearch의 모든 unrestricted 악보 상세 화면에 `화성 분석 · 모호 구간` 패널을 연결했다. 패널은 화면 진입과 함께 자동 조회하며, exact score SHA-256으로 일치하는 원자료 주석이 있을 때만 화성을 표시한다. 일치 자료가 없는 곡은 분석을 꾸며 내지 않고 `검증용 화성 주석 없음` 상태를 보여 준다.

`harmony-overlay-artifact-0.3.0`에서 sparse-review triage를 공통 계산한다. 다음 조건 중 하나라도 있으면 `review_candidate=true`다.

- surface support가 mixed, weak 또는 unscorable
- expected-tone presence가 0.75 미만
- chord-tone duration ratio가 0.55 미만
- notated inversion과 관찰 bass가 불일치
- possible NCT resolution evidence가 존재

presence 0.50 미만, duration ratio 0.35 미만 또는 weak evidence는 high priority다. 이 값은 주석의 정오 판정이 아니라 사람이 먼저 볼 구간을 줄이는 triage다. Viewer는 기본적으로 candidate만 보여 주고 필요하면 `전체 화성도 보기`로 모든 source label을 펼친다.

피드백은 Viewer의 `/api/analysis/harmony-feedback` bridge가 현재 work의 score hash, catalog record ID, annotation ID를 다시 대조한 뒤 8766의 append-only `/api/reviews/{catalog_id}`로 보낸다. 저장된 의견은 `training_eligible=false`이며 즉시 화성 규칙이나 구조 분석을 바꾸지 않는다. `structure_influence=none` 계약도 유지한다.

## 2026-09-25 — exact-source 중심 설계의 정정과 blind 자동 분석 v0.1

사용자 검토로 exact score hash가 있는 경우에만 표시하는 방식은 최종 목적과 다르다고 판정했다. exact source overlay는 원자료 감사용 보조 레이어로 유지할 수 있지만, 일반 악보 상세 화면의 주 레이어가 되어서는 안 된다.

MusicSearch에 `blind-full-score-harmony-v0.1`을 연결했다. 이 분석기는 현재 악보의 전 파트·staff·voice에서 attack과 sustain을 읽고, phrase 경계와 원자료 화성 라벨을 보지 않은 채 전곡의 화성 span 후보를 만든다. 조표의 관계장조·관계단조 후보, 음 지속의 scale fit, tonic/dominant/predominant coverage, 마지막 tonic 후보를 근거로 전곡 조성 가설을 만들고 각 절대 화음을 로마숫자로 투영한다.

이 결과는 아직 annotation-calibrated model이 아니다. 수집한 주석은 다음 단계에서 다음 목적으로 사용한다.

1. analyzer 입력에서 숨긴 채 train/dev/holdout 평가
2. template·segmentation·key score의 오류 유형 분류
3. 유사 annotated case retrieval과 경쟁 해석 제시
4. adjudicated 사용자 피드백만 이용한 보정

현재 자동 분석 피드백은 `data/harmony-feedback/automatic-harmony-review.jsonl`에 append-only로 저장한다. chord, key/Roman, extent, NCT, 판단 보류를 구분하며 `trainingEligible=false`, `ruleUpdateEligible=false`다. 전곡의 모든 원자 구간을 검토 대상으로 만들지 않고, low fit·작은 후보 margin·누락 3음·dense/NCT 가능성을 점수화하여 작품당 최대 80개, 전체 구간의 약 10% 이내를 우선 큐로 선택한다.
## 자동 화성 선택과 악보 시간 범위 연결

자동 분석 목록의 한 화성 가설을 누르면 뷰어는 `analysis_id`가 가리키는 `[start, end)`를 악보의 시간축에 연결한다. 선택 구간은 호박색 반투명 띠로 약 1초간 강조되고, 첫 구간으로 자동 이동한다. 줄바꿈을 통과하는 구간은 각 오선 시스템에 별도의 띠를 그린다.

이 표시는 **화음이 유지되는 시간 범위**를 보여 주는 UI이며, 내부 음표 전부가 화음 구성음이라는 주장이 아니다. 비화성음·경과음·장식음은 같은 범위에 포함될 수 있다. 현재 시작 앵커는 구조 분석용 최상성부에서 그 시점에 이미 울리는 음을 우선 사용한다. 향후 Canonical IR의 전 성부 event ID가 뷰어 SVG에 직접 연결되면 개별 구성음·비화성음 색칠을 별도 레이어로 추가한다.

## 전곡 기본 표시와 Cadence 후보

자동 화성 패널은 이제 review candidate만이 아니라 전곡의 모든 유효 span을 기본 표시한다. `NOTHING BUT THE BEST` 사례에서는 188개 중 17개만 보였던 것이 sparse display의 주원인이었다. 사용자는 체크를 해제해 다시 우선 검토 후보만 볼 수 있다.

다만 이것이 모든 시점을 강제로 채운다는 뜻은 아니다. 현재 v0.1은 서로 다른 pitch class가 2개 미만이거나 chord-template fit이 0.38 미만이면 `unknown` 화음을 양산하는 대신 span을 보류한다. 따라서 쉼, 단선율, 매우 불확실한 음향에는 실제 공백이 남을 수 있다.

Cadence UI는 `boundaryHarmony.records[].selectedCadence`가 있는 기록만 별도 목록으로 투영한다. 각 항목은 Phrase 경계의 준비화음 시작부터 도착화음 끝까지의 `[start, end)`를 참조하며, 선택 시 파란 띠와 `cadence-range-flash`로 표시한다. 이 레이어는 다음 의미 제한을 가진다.

- 전곡 임의 위치의 독립 Cadence 탐색기가 아니라 Phrase 경계 주변의 지원 가능한 후보다.
- HC, IAC, PAC 등의 label과 strength는 주석 코퍼스 보정 전 가설이다.
- 표시 결과는 아직 Phrase·Motif·Pillar 판정의 입력으로 사용하지 않는다.
- 장차 Canonical IR span과 전 성부 event ID에 연결해 preparation, arrival, bass, soprano evidence를 각각 추적할 수 있어야 한다.

브라우저 검증에서 `NOTHING BUT THE BEST`는 전곡 화성 188개, 우선 검토 17개, Cadence 후보 13개를 보였고 첫 HC 선택 시 두 개의 악보 렌더링 구간이 파란색으로 강조되었다.

## Source syntax compatibility: XML attribute quotes

`work-474e82a835aa3acb`의 Sibelius/Dolet MusicXML은 속성값에 작은따옴표를 사용했다. 전환기용 `musicXmlHarmonyStreams` 어댑터가 큰따옴표만 허용하여 part를 하나도 찾지 못했고, 화성 span이 0개가 되었다. 이는 음악 분석의 불확실성이 아니라 Source Reference 파싱 실패다.

part ID, measure number, tie type은 XML이 허용하는 작은따옴표와 큰따옴표를 모두 받아야 한다. 수정 후 이 작품에서는 화성 span 848개와 Cadence 후보 10개가 생성되었다. 향후 Canonical IR parser는 정규식 기반 속성 해석을 제거하고 XML parser가 제공하는 attribute value를 사용해야 하며, 두 quote style을 동일한 canonical fixture로 회귀 검증해야 한다.

## Human Roman correction candidate and local harmonic context

자동 화성 피드백 문장에 `[viio/V]`처럼 대괄호로 감싼 Roman 표기가 있으면 v0.2 review record는 이를 `human.romanLabels`와 `human.suggestedRomanLabel`로 구조화한다. 슬래시가 있는 표기는 `secondary-function` case tag를 받는다. 동시에 선택 구간의 바로 앞·현재·다음 화성 hypothesis를 `hypothesis.context`에 저장하여 `viio/V → V` 같은 해결 문맥을 검증할 수 있게 한다.

이 구조화는 자동 승인이 아니다. 새 record와 과거 review를 보완한 enrichment record 모두 다음 상태를 유지한다.

- `adjudicationStatus: pending`
- `retrievalEligible: false`
- `trainingEligible: false`
- `ruleUpdateEligible: false`

따라서 의견은 다음 판단을 위한 **후보 데이터**로 보존되지만 즉시 분석 규칙이나 gold label로 쓰이지 않는다. 승인된 Secondary-function 사례가 충분히 모이면 target chord, resolution chord, bass·soprano voice leading, metric position을 묶어 case retrieval 및 ranker calibration 단계로 승격한다.

Viewer는 일반 문장을 기존 글꼴로 유지하고, 입력 미리보기와 저장 의견에서 대괄호 안 Roman token만 Campania로 표시한다. `unknown`이나 일반 텍스트에는 Campania를 적용하지 않는다.
