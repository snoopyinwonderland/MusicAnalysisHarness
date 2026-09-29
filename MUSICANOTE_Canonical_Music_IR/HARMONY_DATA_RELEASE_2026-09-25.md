# Harmony Data Release — 2026-09-25

## 목적

화성 사례 검색과 향후 평가에서 같은 작품의 다른 악장, 동일 score 변환본, 동일 주석 자산이 train/dev/holdout에 섞이는 것을 막는다. 이 manifest는 Canonical Music IR이 아니라 **데이터셋 운영 계약**이다. Canonical Core에는 corpus split이나 학습 자격을 넣지 않는다.

## 생성된 계약

- builder: `src/musicanote_harness/harmony_dataset_manifest.py`
- manifest schema: `schemas/harmony_dataset_manifest.schema.json`
- case schema: `schemas/harmony_case_record.schema.json` v0.2.0
- CLI:
  - `build-harmony-dataset-manifest`
  - `validate-harmony-data-release`
- tests: `tests/test_harmony_dataset_manifest.py`

Manifest entry는 다음을 분리해 보존한다.

1. score/IR/package/source path
2. corpus와 collection
3. work family와 movement
4. edition 자리(현재 null 허용)
5. annotation lineage
6. score·annotation SHA-256
7. quality summary
8. retrieval/training/blind-evaluation eligibility
9. 고정 split
10. licence·학습·외부 API 전송·재배포 권한 상태

DCML 파일명 규칙은 collection adapter로 해석한다. `_01` 같은 숫자 악장 suffix와 Corelli의 `op01n01a` 같은 문자 악장 suffix는 같은 작품군으로 묶는다. 규칙으로 안전하게 판별할 수 없는 이름은 score-stem fallback과 `unresolved_work_family`를 기록해야 하며 조용히 확정하지 않는다.

## Split 정책

- 분리 단위: `work_family_id`
- 동일 작품군은 절대 여러 split에 나누지 않는다.
- exact-aligned annotation 수를 예상 사례량으로 사용해 70/15/15에 가깝게 균형화한다.
- dev와 holdout은 각각 최소 3개 작품군을 가진다(현재 22개 작품군 기준).
- assignment는 결정론적이며 manifest의 `dataset_release_id`로 release를 고정한다.
- dev/holdout query의 사례 검색은 train 사례만 허용한다.
- holdout label은 검색 후보, weight tuning, rule 작성에 사용하지 않는다.

## 실제 release 결과

입력은 현재 준비가 완료된 DCML 43개 score package다.

| 항목 | 결과 |
|---|---:|
| package | 43 |
| work family | 22 |
| unresolved family | 0 |
| train/dev/holdout score | 30 / 6 / 7 |
| 전체 exact case | 6,492 |
| train/dev/holdout case | 4,509 / 982 / 1,001 |
| schema/build error | 0 |
| work-family split leak | 0 |
| score-hash split leak | 0 |
| annotation-hash split leak | 0 |
| manifest가 없는 case | 0 |
| identity mismatch | 0 |

산출물:

- `output/harmony-dataset-manifest-2026-09-25.json`
- `output/harmony-case-library-2026-09-25/harmony_case_records.jsonl`
- `output/harmony-case-library-2026-09-25/case_library_report.json`
- `output/harmony-case-library-2026-09-25/data_release_validation.json`

검증 상태는 `passed`다. 이는 split/참조 무결성이 맞다는 뜻이지, 주석이 모두 gold이거나 자동 학습에 승인되었다는 뜻은 아니다. 모든 case는 계속 `training_eligible=false`다.

현재 licence 상태는 명시적으로 `unverified`이며, model training·외부 API 전송·재배포는 모두 `false`다. 내부 로컬 연구/검토만 허용하는 보수적 기본값이다. 실제 라이선스 검토가 끝나기 전에는 이 값을 자동으로 승격하지 않는다.

## 다음 단계

1. train만 사용해 blind local-key 후보와 bass/voice-leading resolution evidence를 추가한다.
2. dev에서 feature ablation과 rank weight를 비교한다.
3. holdout은 설계·튜닝이 끝난 release의 최종 평가에서 한 번만 연다.
4. case-review UI는 query와 retrieved score의 앞뒤 악보 문맥을 함께 보여 주고 append-only feedback을 저장한다.
5. 새 corpus를 추가하면 기존 release를 덮어쓰지 않고 새 `dataset_release_id`를 만든다.
