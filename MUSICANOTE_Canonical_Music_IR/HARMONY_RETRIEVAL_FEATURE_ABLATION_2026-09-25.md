# Harmony Retrieval Feature Ablation — 2026-09-25

## 목적

표면 pitch profile만으로 비슷한 사례를 찾는 v0.1에 blind local-key 후보와 경계 성부진행 증거를 추가했을 때 실제 검색 품질이 좋아지는지 dev split에서 검증한다. source harmony label은 feature 계산과 순위 산정에서 완전히 가린다.

이 평가는 **주석이 제공한 화성 span 경계를 입력받은 case retrieval 평가**다. 자동 segmentation, 전체 화성 인식, Cadence/NCT 분석의 end-to-end 정확도가 아니다.

## 새 feature

### Blind local-key 후보

- 현재 span 전후 최대 8 quarter의 duration-weighted pitch-class 분포
- major/minor key profile 24개와의 적합도
- MusicXML key signature는 약한 prior로만 사용
- 상위 5개 후보와 비보정 fit score 저장
- source Roman label과 annotation key label은 사용하지 않음
- 검색 비교에서는 tonic을 관찰된 bass에 상대화하여 이조 불변성을 유지

### 경계 성부진행 증거

- span 진입·종료 경계의 좌우 sounding event
- 가장 가까운 음으로의 semitone-motion histogram
- common tone, 상행/하행 반음 수
- bass motion
- 원본 sounding-event reference

이는 준비·지속·해결의 기초 증거이며 passing/neighbor/suspension 같은 NCT 이름이나 화성 기능을 확정하지 않는다.

## 평가 계약

- query: dev 982 cases
- candidates: train 4,509 cases
- 동일 score, work family, annotation lineage 제외
- query label은 ranking 이후 metric 계산에만 사용
- holdout 1,001 cases는 열지 않음
- primary metric: harmony taxonomy family MRR 및 Top-1
- raw label metric은 inversion/compound 표기를 포함하므로 더 엄격한 보조 지표

## 결과

| profile | Raw Top-1 | Family Top-1 | Family Top-5 | Family MRR |
|---|---:|---:|---:|---:|
| surface v0.1 | 17.31% | 36.76% | 68.33% | 0.5093 |
| local key v0.2 | 27.49% | 54.48% | 76.48% | 0.6466 |
| voice leading v0.2 | 21.08% | 43.89% | 72.71% | 0.5662 |
| combined v0.3 | **29.84%** | **56.11%** | **78.31%** | **0.6635** |
| combined + NCT geometry v0.4 | 28.51% | 56.31% | 79.33% | 0.6668 |

Combined v0.3는 surface 대비 Raw Top-1 +12.53%p, Family Top-1 +19.35%p, Family MRR +0.1542다. NCT geometry를 더한 v0.4는 Family MRR이 0.0033 증가하고 Family Top-5가 1.02%p 증가했지만 Raw Top-1은 1.32%p 하락했다. 최소 Family MRR +0.01 및 Raw Top-1 하락 0.01 이하라는 승격 gate를 통과하지 못하므로 기본 profile은 `combined_v0.3`을 유지한다. NCT geometry는 삭제하지 않고 실험 evidence로 보존한다.

주요 family Top-1 변화:

- tonic: 43% → 68%
- dominant/leading-tone: 51% → 65%
- predominant diatonic: 29% → 57%
- applied dominant/leading-tone: 27% → 34%
- mediant/submediant: 14% → 30%

`applied_other`는 23건에서 여전히 0%다. Neapolitan과 augmented-sixth는 dev 표본이 각각 3건과 2건뿐이라 수치를 일반화할 수 없다. 따라서 다음 단계는 applied harmony와 chromatic predominant에 필요한 spelling·resolution·NCT 문맥을 강화하는 것이다.

## 결정

- `combined_v0.3`를 다음 dev 실험의 기본 retrieval profile로 유지한다. `combined_nct_geometry_v0.4`는 아직 승격하지 않는다.
- holdout은 feature 설계와 UI 피드백 계약을 고정한 뒤 한 번만 평가한다.
- 이 결과만으로 자동 화성 selected hypothesis를 만들지 않는다.
- Phrase, Cadence, Motif, Pillar에는 아직 영향을 주지 않는다.
- 다음은 NCT 이름을 붙이기 전 준비·유지·해결 evidence와 applied-target 후보를 설계한다.

## 산출물

- `src/musicanote_harness/harmony_case_retrieval.py`
- `src/musicanote_harness/harmony_case_retrieval_eval.py`
- `schemas/harmony_case_retrieval_ablation.schema.json`
- `output/harmony-case-library-2026-09-25/retrieval-ablation-dev.json`
