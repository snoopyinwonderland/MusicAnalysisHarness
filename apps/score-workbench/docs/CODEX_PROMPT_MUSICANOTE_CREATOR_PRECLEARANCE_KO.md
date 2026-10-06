# Codex 실행 프롬프트 — MUSICANOTE 창작물 사전검토

아래 프롬프트를 실제 Musicanote 코드 저장소를 연 Codex에 전달한다. 같은 디렉터리에 `MUSICANOTE_Creator_Preclearance_Development_Spec_KO.md`를 두고 시작한다.

---

당신은 기존 MUSICANOTE의 구조 분석기와 유사 멜로디 검색기를 연결해, 창작자가 MusicXML/MIDI 전체 작품을 업로드하고 주요 프레이즈의 유사성을 사전 검토할 수 있는 기능을 만드는 senior full-stack/MIR engineer입니다.

먼저 저장소의 `AGENTS.md`, README, 개발·배포 문서, 기존 유사검색 명세와 `MUSICANOTE_Creator_Preclearance_Development_Spec_KO.md`를 끝까지 읽으십시오. 명세보다 실제 저장소가 우선되어야 하는 부분은 추측으로 바꾸지 말고 audit와 ADR에 차이, 선택지, 권장안을 기록하십시오.

## 핵심 목표

신규 메뉴 `창작물 사전검토` 또는 저장소 명명 규칙에 맞는 feature-flagged route에서 다음 흐름을 구현하십시오.

```text
MusicXML/MIDI 업로드
→ 파일 검증·Canonical Music IR
→ 주선율 part/voice 추정과 사용자 확인
→ 기존 구조 분석기로 phrase/section/cadence 분석
→ Phrase Importance Scorer로 주요 프레이즈 선정
→ 빠른 후보 검색
→ weighted subsequence DTW 재평가
→ 업로드 곡·DB 곡 양쪽의 프레이즈 중요도 결합
→ 작품 단위 중복 제거
→ 설명 가능한 검토 결과
```

최종 결과는 법률적 침해 확률이 아니라 음악적 유사성과 검토 우선순위를 제공해야 합니다.

## 절대 지켜야 할 원칙

- 기존 구조 분석기와 직접입력 유사검색을 깨뜨리지 마십시오.
- production route를 즉시 교체하거나 공개하지 마십시오.
- 코드를 수정하기 전에 반드시 읽기 전용 Phase 0 audit를 수행하십시오.
- 검색 요청마다 XML/MIDI를 다시 파싱하지 마십시오.
- corpus 전체 프레이즈에 DTW를 실행하지 마십시오.
- DB 작품과 업로드 작품 모두 part/staff/voice identity를 보존하십시오.
- 한 작품의 모든 성부를 하나의 잘못된 interval sequence로 평탄화하지 마십시오.
- 구조 분석기의 phrase boundary를 절대적 정답으로 간주하지 말고 confidence와 사용자 수정 기능을 제공하십시오.
- Schenkerian/Ursatz 분석을 확정적 detector로 표현하지 마십시오. confidence가 있는 structural salience로만 사용하십시오.
- 짧은 scale, arpeggio, repeated note, 관습적 cadence가 높은 위험 결과가 되지 않도록 distinctiveness를 계산하십시오.
- 업로드 작품과 후보 작품의 phrase importance를 각각 계산하고 분리 표시하십시오.
- 동일 작품의 반복 occurrence와 여러 판본이 결과를 독점하지 않도록 canonical work 단위로 묶으십시오.
- `copyright infringement probability`, `침해 확률`, `불법`과 같은 확정적 UI 표현을 사용하지 마십시오.
- 사용자가 명시적으로 동의하지 않은 업로드 파일을 corpus 또는 학습 데이터에 추가하지 마십시오.
- 원본 파일, 파생 feature, 캐시, 보고서의 삭제 정책을 구현하고 테스트하십시오.
- paid API, vector DB, LLM을 MVP 필수 dependency로 추가하지 마십시오.
- repository의 기존 사용자 변경과 unrelated code를 건드리지 마십시오.
- destructive migration이나 production data 재색인을 실행하지 마십시오.

## 모델과 reasoning effort

현재 환경에서 사용할 수 있는 모델 중 작업에 충분한 가장 낮은 비용·지연 수준을 선택하십시오.

- 구조 분석기와 검색기 통합 설계, DTW/인덱스 성능, 다성 MIDI melody extraction, score calibration: frontier reasoning model, high 권장
- API, UI, schema, migration, integration test: balanced coding model, medium 권장
- fixture, 반복 ETL, 단순 문서·test 보완: fast coding model, low~medium 권장

모델 명칭이 달라졌으면 현재 공식 모델 목록에서 동등 역할을 선택하십시오. 저장소나 사용자 지침이 허용하지 않으면 subagent를 사용하지 마십시오. 복잡하다는 이유만으로 무조건 최고 비용 모델이나 max/ultra reasoning을 고정하지 마십시오.

## Phase 0 — 수정 전 필수 audit

코드를 변경하지 말고 다음을 조사하십시오.

### A. Repository와 실행 환경

- frontend/backend framework, package manager, runtime version
- local/dev/production 실행 방법
- authentication, file storage, job queue, cache
- DB 종류와 schema/migration 방식
- test, lint, build, CI 명령
- feature flag와 private route 관례

### B. 기존 구조 분석기

- 입력 형식과 호출 경로
- section, phrase, cadence 출력 schema
- event/onset/measure identity mapping
- confidence와 warning 제공 여부
- MusicXML/MIDI별 차이
- 평균·p95 실행시간과 메모리
- 실패·timeout·retry 방식

### C. 기존 검색기

- exact/similarity API와 호출 경로
- interval/contour/rhythm/downbeat/harmony/structure feature
- 후보 retrieval 방식과 index
- DTW 구현 언어, band, candidate limit
- corpus와 melody stream/phrase 수
- 동일 작품·판본 deduplication 방식
- stage별 cold/warm p50/p95

### D. 업로드 및 개인정보

- 현재 upload validation과 object storage
- owner authorization과 signed URL
- file retention/deletion
- audit log와 administrator access
- 사용자 파일의 corpus/training 편입 여부

Audit 결과를 `docs/creator-preclearance-audit.md` 또는 저장소 관례에 맞는 경로에 작성하십시오. 다음을 포함하십시오.

- 현재 데이터 흐름도
- 실제 병목과 측정값
- 재사용 가능한 코드
- 누락된 계약과 위험
- 최소 변경 구현안
- schema/index ADR
- 예상 migration과 rollback

Audit만으로 중요한 선택이 확정되지 않으면 구현을 추측으로 진행하지 말고 선택지와 권장안을 사용자에게 보고하십시오.

## 구현 순서

### 1. Baseline과 regression fixture

- 기존 구조 분석기의 대표 MusicXML/MIDI fixture를 고정하십시오.
- 기존 직접입력 exact/similarity 결과 regression test를 만드십시오.
- corpus size, phrase count, index size와 latency baseline을 기록하십시오.
- development build와 production build의 속도를 구분하십시오.
- stage timer를 먼저 추가하되 production log에 악보 내용이 노출되지 않게 하십시오.

### 2. Upload validation과 Canonical Music IR

- `.musicxml`, `.xml`, `.mxl`, `.mid`, `.midi`를 안전하게 검증하십시오.
- XML external entity, 압축 폭탄, path traversal, 과대 파일을 차단하십시오.
- source/part/staff/voice/event identity를 보존하십시오.
- tie, rest, grace, tuplet, chord, repeat, tempo/time-signature change를 명시적으로 처리하십시오.
- MIDI는 tempo map, time signature, percussion 제외, sustain 보정, quantization을 처리하십시오.
- parser/analyzer/feature version을 모든 파생 데이터에 저장하십시오.

### 3. Melody stream 추정과 확인 UI

- track/part name, monophony, 음역, note density, 반복, 최상성부 비율을 사용해 melody 후보를 순위화하십시오.
- 다성 track은 voice separation 후 복수 stream을 유지하십시오.
- `melodyRoleScore`, `roleConfidence`, `extractionMethod`를 저장하십시오.
- 자동 선택 결과와 2~3개의 대체 후보를 사용자에게 보여주십시오.
- 사용자가 선택을 변경하면 이후 phrase 분석과 검색을 일관되게 갱신하십시오.

### 4. 구조 분석기 adapter

- 기존 분석기의 내부를 이번 작업 때문에 먼저 재작성하지 마십시오.
- phrase 시작/끝, section, cadence, confidence, warning을 안정적인 adapter contract로 변환하십시오.
- 원본 score event와 분석 결과 사이의 mapping을 유지하십시오.
- 낮은 confidence와 실패를 UI와 job 상태에 전달하십시오.

### 5. Phrase Importance Scorer

명세의 초기 요소를 versioned configuration으로 구현하십시오.

- melodic prominence 25%
- repetition/recurrence 20%
- structural position 20%
- metrical/duration salience 15%
- cadence/harmonic role 10%
- structural tone salience 10%

필수 규칙:

- melody-role gate를 importance보다 먼저 적용
- 반복 bonus capped/log transform
- confidence가 낮은 component는 weight 0 후 재정규화
- 동일·변형 반복은 canonical phrase로 묶기
- 주요 3개와 보조 2~4개, 최대 canonical phrase 7개 검색
- 5~6음은 경고, 7음 이상 권장
- 자동 component와 사용자 수정값 모두 correction log에 저장

### 6. Phrase 편집 UI

- Verovio 악보에 phrase/section을 표시하십시오.
- 경계 handle drag, 주요/보조/제외, melody part 변경을 지원하십시오.
- 편집 후 전체 job을 무조건 다시 돌리지 말고 dependency가 있는 단계만 invalidation하십시오.
- undo 또는 원래 자동 분석으로 복구 기능을 제공하십시오.

### 7. 후보 검색

- exact interval match를 보존하십시오.
- interval, contour 5종, normalized rhythm/IOI, rest pattern, metric/downbeat, phrase length n-gram으로 후보를 구하십시오.
- Elasticsearch/OpenSearch가 이미 있으면 candidate sidecar로 재사용하십시오.
- 없다면 현재 관계형 DB와 corpus 규모를 측정한 뒤 indexed SQL n-gram table을 우선 검토하십시오.
- candidate limit 기본값은 프레이즈당 300으로 시작하고 evaluation으로 조정하십시오.
- 후보 검색 단계가 corpus 전체 크기에 선형 비례하지 않게 하십시오.

### 8. Weighted subsequence DTW

- 후보에만 실행하십시오.
- 순수 Python 중첩 loop를 피하고 현재 stack에 맞는 Numba/C++/Rust/vectorized implementation을 사용하십시오.
- Sakoe–Chiba band, slope constraint, early abandon을 적용하십시오.
- 음정 35, 리듬 15, metric/downbeat 15, contour 10, harmony/NCT 10, phrase structure 10, ornament tolerance 5의 초기 비중을 versioned config로 두십시오.
- passing/neighbor/grace mismatch와 gap penalty는 낮게 하십시오.
- downbeat structural tone, phrase apex, cadence 핵심음 mismatch는 높게 하십시오.
- harmony/structure confidence가 낮으면 관련 weight를 0으로 만들고 나머지를 재정규화하십시오.
- component score, alignment path, matched measure/beat, transposition, tempo scale을 반환하십시오.

### 9. Distinctiveness와 작품 단위 집계

- corpus document frequency와 phrase length를 사용해 흔한 패턴을 억제하십시오.
- global rarity와 genre-conditioned rarity를 분리해 기록하십시오.
- 동일 work의 occurrence는 한 카드로 묶으십시오.
- canonical work ID가 있으면 arrangement/edition을 묶되 권리 metadata는 잃지 마십시오.
- best alignment를 작품 순위의 중심으로 사용하십시오.
- 서로 다른 주요 프레이즈가 여러 개 일치할 때만 capped coverage bonus를 적용하십시오.
- 반복 occurrence 점수를 단순 합산하지 마십시오.

### 10. Review Priority

다음 값을 별도로 계산·저장·표시하십시오.

- similarityScore
- queryImportance
- candidateImportance
- distinctivenessScore
- coverageScore
- analysisConfidence
- reviewPriority

개념식은 다음을 출발점으로 사용하십시오.

```text
reviewPriority = similarity
  × sqrt(queryImportance × candidateImportance)
  × distinctiveness
  × coverage
  × confidence
```

이 식을 최종 진리처럼 하드코딩하지 말고 config와 calibration test로 관리하십시오. similarity가 낮은 결과를 importance bonus로 상위에 올리거나, 짧고 흔한 exact fragment를 높은 우선순위로 표시해서는 안 됩니다.

UI 등급은 `낮음`, `관찰`, `검토 필요`, `우선 검토`, `판단 보류`를 사용하십시오. 임계값은 labeled evaluation 전에 임의로 확정하지 마십시오.

### 11. Result UI와 설명

- 업로드 곡의 structure/phrase map과 중요도를 표시하십시오.
- 결과는 work 단위로 보여주십시오.
- 양쪽 악보에서 matched measure/beat를 표시하십시오.
- 일치, 변형, 삽입, 생략을 색상으로 구분하십시오.
- A/B 개별 재생과 연속 재생을 제공하십시오.
- `왜 유사한가` 설명은 실제 component와 alignment evidence에서 규칙 기반으로 생성하십시오.
- stored YouTube URL이 있다면 optional lazy-loaded preview만 제공하고 live search를 사용자 검색 path에 넣지 마십시오.
- corpus 원본 전체를 다운로드하거나 재구성할 수 있게 하지 마십시오.

### 12. Privacy, retention, deletion

- private upload가 기본입니다.
- `분석 후 원본 삭제`와 `비공개 보관`을 구분하십시오.
- corpus/training contribution은 별도 checkbox, default off입니다.
- owner/reviewer authorization을 모든 job, result, report endpoint에서 검증하십시오.
- signed URL은 짧게 만료되게 하고 전체 악보 내용을 log에 남기지 마십시오.
- delete job이 원본, 파생 feature, cache, result, report에 어떻게 전파되는지 테스트하십시오.
- 관리자의 예외 접근은 role, reason, audit log를 요구하십시오.

### 13. Background job과 관측

- normalize, structure, importance, candidate retrieval, sequence fetch, rerank, aggregation, report를 stage로 나누십시오.
- 긴 분석은 background job으로 실행하고 progress, failure reason, retry를 제공하십시오.
- 동일 파일 hash와 동일 version/config의 중복 실행은 정책에 맞게 재사용하십시오.
- stage별 latency, candidate count, DTW cell count/early abandon, cache hit를 기록하십시오.
- 개인정보가 log label이나 trace payload에 들어가지 않게 하십시오.

## API 계약

명세의 초안을 현재 API convention에 맞게 조정하십시오.

```text
POST   /api/preclearance/uploads
GET    /api/preclearance/jobs/{jobId}
GET    /api/preclearance/jobs/{jobId}/structure
PATCH  /api/preclearance/jobs/{jobId}/melody-stream
PATCH  /api/preclearance/jobs/{jobId}/phrases/{phraseId}
POST   /api/preclearance/jobs/{jobId}/search
GET    /api/preclearance/jobs/{jobId}/results
GET    /api/preclearance/jobs/{jobId}/results/{workId}
POST   /api/preclearance/jobs/{jobId}/reports
DELETE /api/preclearance/jobs/{jobId}
```

기존 convention과 다르면 이름은 바꿀 수 있지만 기능, authorization, idempotency, pagination, version fields를 보존하십시오.

## 필수 평가 데이터

작은 balanced corpus와 synthetic transformation harness부터 만드십시오.

- exact/transposed
- tempo ×0.5/×1.5/×2
- ornament insertion/deletion
- 일부 음 대체
- rhythm 변형
- wrong-downbeat hard negative
- 같은 contour, 다른 interval
- scale/arpeggio/cadence common pattern
- main theme 대 main theme
- main theme 대 accompaniment
- ambiguous MIDI melody track
- low-confidence structure/harmony

측정:

- 구조 분석기의 기존 지표 또는 phrase boundary precision/recall
- 중요 phrase 전문가 Top-3 agreement
- candidate recall@K
- Recall@10/20, MRR, nDCG
- work deduplication 정확도
- review-level precision/recall/calibration
- 장르·source별 false positive/negative
- stage별 cold/warm p50/p95

## 필수 테스트

1. 조옮김된 동일 프레이즈가 상위에 나온다.
2. 전체 tempo 비율 변화에도 normalized rhythm 유사도가 유지된다.
3. 약박 장식음 변경은 강박 구조음 변경보다 penalty가 낮다.
4. wrong-downbeat 후보가 올바른 metric alignment보다 낮다.
5. 짧은 scale/arpeggio/cadence가 높은 review priority를 받지 않는다.
6. main-theme 대 main-theme가 main-theme 대 accompaniment보다 높다.
7. 동일 작품의 반복 occurrence가 한 카드에 묶인다.
8. 서로 다른 주요 phrase 두 개가 일치하면 제한된 coverage bonus가 붙는다.
9. phrase 경계 수정 후 영향받은 결과만 재계산된다.
10. MIDI melody track 변경 후 structure/search 결과가 일관되게 갱신된다.
11. harmony/structure confidence가 낮으면 관련 weight가 꺼지고 검색은 실패하지 않는다.
12. 사용자 동의 없는 업로드가 corpus/training data에 들어가지 않는다.
13. 다른 사용자가 job ID를 알아도 원본과 결과를 읽을 수 없다.
14. 삭제 요청 후 정책 범위의 원본·파생 데이터가 제거된다.
15. 기존 직접입력 검색 regression test가 모두 통과한다.

## 성능 완료 기준

구현 전에 baseline을 측정하고 실제 corpus 규모와 server target에 근거해 숫자를 확정하십시오. 최소한 다음을 만족해야 합니다.

- 검색마다 원본 XML/MIDI를 재파싱하지 않는다.
- 전체 corpus DTW scan이 없다.
- candidate count에 상한이 있다.
- cold와 warm latency를 분리한다.
- local development와 production build를 분리한다.
- stage별 p50/p95, 후보 수, cache hit를 보고한다.
- corpus 증가에 따른 candidate retrieval과 rerank scaling test가 있다.
- sample corpus에서 정확도와 속도가 기준을 통과하기 전 전체 corpus를 재색인하지 않는다.

성능이 느릴 경우 서버 증설을 먼저 권하지 말고, XML 재파싱, full scan, DB index, sequence fetch, Python DTW, duplicate work expansion, Verovio rerender 중 실제 병목을 측정해 보고하십시오.

## 법적·표현 완료 기준

- 결과에 `침해 확률`을 표시하지 않습니다.
- 음악적 유사성과 권리 상태를 분리합니다.
- public-domain 원곡과 현대 arrangement/edition의 권리 상태를 구분할 수 있습니다.
- rights metadata가 없으면 `unknown`으로 표시합니다.
- 결과 화면과 보고서에 다음 취지의 고지가 있습니다.

> 이 결과는 음악적 유사성과 구조적 중요도를 바탕으로 검토가 필요한 구간을 제시합니다. 저작권 침해에 대한 법률적 판단을 대신하지 않으며, 권리 상태·창작 경위·접근 가능성·관할 법률 등에 대한 별도 검토가 필요합니다.

## 작업 산출물

1. `creator-preclearance-audit.md`
2. 실제 저장소 기준 implementation plan과 ADR
3. Canonical Music IR 및 API schema
4. Phrase Importance Scorer와 unit test
5. 구조 분석기 adapter와 contract test
6. 후보 검색·DTW·작품 집계 harness와 evaluation
7. feature-flagged upload/phrase/result UI
8. privacy/retention/delete test
9. 성능·정확도 평가 보고서
10. 변경 파일, migration, rollback, 미완료 위험 요약

## 중간 보고 시점

다음 단계가 끝날 때마다 결과를 보고하고 검증받으십시오.

1. Phase 0 audit 완료 후, 코드 수정 전
2. 오프라인 algorithm harness와 synthetic evaluation 완료 후
3. sample corpus search와 작품 단위 집계 완료 후
4. UI end-to-end demo 완료 후
5. privacy·성능·regression test 완료 후

거대한 rewrite를 한 번에 수행하지 마십시오. 작은 검증 가능한 변경으로 진행하고, 기존 코드와 명세가 충돌하면 임의 결정하지 말고 근거와 선택지를 제시하십시오.

---

