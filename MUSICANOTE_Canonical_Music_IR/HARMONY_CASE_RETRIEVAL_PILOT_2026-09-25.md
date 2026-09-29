# Harmony Case Retrieval Pilot — 2026-09-25

## 목적

동일 악보나 동일 작품의 annotation 이식보다, **다른 작품의 유사한 음악 구간**을 화성 분석의 참고 사례와 반례로 검색하는 것이 이 단계의 목적이다. 검색된 label은 현재 악보의 정답으로 복사하지 않는다. 현재 구간의 feature는 Canonical IR의 음표 사실만 사용하고 source annotation을 보지 않는다.

## 구현

- 코드: `src/musicanote_harness/harmony_case_retrieval.py`
- schema: `schemas/harmony_case_record.schema.json`
- CLI:
  - `build-harmony-case-library`
  - `query-harmony-cases`
- 테스트: `tests/test_harmony_case_retrieval.py`
- label taxonomy: `src/musicanote_harness/harmony_label_taxonomy.py`
- feedback store: `src/musicanote_harness/harmony_case_review_store.py`
- feedback schema: `schemas/harmony_case_review.schema.json`

Case feature는 다음을 보존한다.

1. 현재 span의 시작 bass를 0으로 둔 이조 불변 pitch-class interval profile
2. 앞·현재·뒤 구간의 duration-weighted interval profile
3. span 안의 bass motion
4. rational duration
5. attack density
6. duration-weighted mean vertical note count
7. 원래 bass spelling, pitch spelling, sounding event reference

검색 점수의 v0.1 가중치는 현재 profile 50%, 앞/뒤 profile 각 12%, attack density 8%, duration·vertical density·bass motion 각 6%다. 문맥이 없는 channel은 분모에서 제외한다. 이 값은 회귀 가능한 초기 rank score이며 확률이나 calibration된 confidence가 아니다.

각 match는 다음을 함께 반환한다.

- source-linked raw harmony label
- source evidence 상태
- score/annotation/case reference와 source locator
- channel별 similarity
- 가장 비슷한 feature와 차이가 큰 feature
- 같은 검색 결과 안의 경쟁 label alternatives

현재 query와 같은 `score_id`, work family, annotation lineage를 제외한다. 한 score가 결과를 독점하지 못하도록 기본 2건까지만 허용한다. dev/holdout query는 train 사례만 검색할 수 있다.

## 화성 주석 분류

raw label은 절대 덮어쓰지 않고, 검색과 집계를 위한 taxonomy facet을 별도로 추가했다.

- base Roman degree와 대·소문자
- accidental prefix
- diminished/half-diminished/augmented quality marker
- inversion/figured-bass
- applied-to target
- Ger/Fr/It augmented-sixth 및 Neapolitan
- continuation marker와 compound path
- parse status: `parsed`, `partial`, `unsupported`, `no_chord`

3-score 774-case 파일럿에서는 728건 parsed, 31건 partial, 15건 no-chord였다. family 분포는 dominant/leading-tone 218, tonic 204, applied dominant/leading-tone 105, predominant diatonic 81, mediant/submediant 62, augmented-sixth 11, Neapolitan 4 등이었다. 이 family는 검색 결과를 묶기 위한 보수적 taxonomy이며 개별 악보에서 확정한 화성 기능이 아니다.

검색 출력은 이제 exact raw-label alternatives와 family alternatives를 모두 보존한다. 같은 표면 사례 안에서 tonic/dominant/predominant 등이 경쟁하면 그 분산 자체가 현재 feature 부족의 경고다.

## 사용자 피드백 계약

구조 분석 개선 방식과 같이 실제 사례를 보며 다음 verdict를 append-only로 저장할 수 있게 했다.

- `useful_analogy`
- `similar_surface_different_function`
- `not_similar`
- `cannot_judge`

선택적으로 surface, bass motion, voice leading, harmonic function, NCT context, Phrase role을 0–4로 따로 평가한다. 수정 리뷰는 이전 record를 삭제하지 않고 `supersedes_review_id`로 연결한다. 새 피드백은 항상 `training_eligible=false`, `rule_update_eligible=false`로 시작하며 별도 adjudication과 holdout 검증 전에는 ranker나 규칙을 자동 변경하지 않는다.

## 실제 파일럿

DCML batch의 앞 3개 실제 준비 패키지에서 library를 만들었다.

- 처리 score: 3
- case: 774
- schema/import error: 0
- 출력: `output/harmony-case-retrieval-pilot-2026-09-25/harmony_case_records.jsonl`
- report: `output/harmony-case-retrieval-pilot-2026-09-25/case_library_report.json`

첫 score의 `[0,3)` quarter 구간을 query하고 동일 score를 제외했다. 다른 두 score에서 score별 2건, 총 4건이 반환됐다.

| similarity | source label | 주요 유사 근거 | 주요 차이 |
|---:|---|---|---|
| 0.884668 | VI | vertical density, bass motion, current profile | attack density, duration |
| 약 0.87 | ii | vertical density, bass motion, next context | duration, attack density |
| 약 0.87 | V | vertical density, bass motion, next context | duration, attack density |
| 약 0.84 | I | vertical density, current profile, bass motion | duration, next context |

표면과 texture가 상당히 비슷해도 label이 `VI/ii/V/I`로 갈렸다. 따라서 nearest label을 그대로 채택하는 방식은 사용하지 않는다. 이 결과는 local key, spelling function, voice-leading resolution, NCT, 이전/다음 화성 후보가 ranker에 더 필요함을 보여 주는 반례다.

## 실행 예

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m musicanote_harness.cli build-harmony-case-library `
  'output\dcml-batch-2026-09-24\pairs' `
  --output 'output\harmony-case-retrieval-pilot-2026-09-25' --limit 3

.\.venv\Scripts\python.exe -m musicanote_harness.cli query-harmony-cases `
  --ir 'path\to\canonical_music_ir.json' `
  --library 'output\harmony-case-retrieval-pilot-2026-09-25\harmony_case_records.jsonl' `
  --start 0 --end 3 --limit 12 `
  --output 'output\harmony-case-retrieval-pilot-2026-09-25\query-example.json'
```

## 제한 및 다음 단계

- DCML 준비 패키지에는 별도 surface evidence scorer가 아직 없어 pilot record의 support band는 `unscorable`이다. 이를 낮은 품질이나 오류로 해석하지 않는다.
- work-family/annotation-lineage exclusion과 train/dev/holdout release는 구현했다. 결과는 [Harmony Data Release](HARMONY_DATA_RELEASE_2026-09-25.md)에 기록했다.
- local key와 Roman function은 query feature로 사용하지 않았다. 이는 blind query를 유지하기 위한 것이지만 기능화음 구별력이 낮다.
- NCT와 성부별 준비·해결은 아직 feature에 없다.
- 다음 단계는 train만 보면서 blind local-key 후보·bass/voice-leading resolution evidence를 추가하고 dev에서 retrieval ablation을 실행하는 것이다. holdout은 설계·튜닝 완료 전 열지 않는다.
- retrieval 결과는 아직 Phrase, Cadence, Motif, Pillar 또는 자동 화성 selected hypothesis에 연결하지 않는다.
- query와 retrieved case의 악보 문맥을 함께 표시하고 verdict/축별 평가를 저장하는 UI를 구현했다. 세부 계약과 검증은 [Harmony Case Review UI](HARMONY_CASE_REVIEW_UI_2026-09-25.md)에 있다. 다음 단계는 실제 평가 30–50건을 모은 뒤 adjudication과 dev ablation을 수행하는 것이다.
