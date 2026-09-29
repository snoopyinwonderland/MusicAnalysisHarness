# DCML 반복 엔딩 시간축 정렬 검증 — 2026-09-24

## 목표와 경계

이 단계는 DCML의 주석을 **악보의 기보 위치**에 안전하게 연결하는 수입기 개선이다. 기능화성 예측, NCT·Cadence 분류, 사람이 검수한 정답 판정은 아직 아니다. 원본 MusicXML/TSV는 읽기만 했고, 해석 주석은 Canonical IR Core에 넣지 않았다.

## 발견한 원인과 일반 규칙

- 1·2번 엔딩이 있는 TSV는 `quarterbeats`가 연주 순서 기준이거나 첫 엔딩 행에서 비어 있을 수 있다. `quarterbeats_all_endings`는 두 엔딩을 모두 포함한 기보 순서의 위치다. 마디·음표·화성 **세 표 모두** 이 좌표가 완전할 때만 기보 IR과 비교한다. 하나라도 빠지면 수입을 보류한다.
- 0마디처럼 `implicit="yes"`인 짧은 마디에서, MusicXML의 `rest measure="yes"`에 명시된 2박 `duration`을 music21이 4박 전마디 쉼표로 확장하는 사례가 있다. 악보 원본을 바꾸지 않고 **메모리 안의 파싱 복사본**에서 이 표지만 제거하여 명시된 길이를 살린다. `implicit`이 아닌 마디의 쉼표에는 적용하지 않는다.
- 변환 후 TSV 음표와 IR 음표의 `(시작, 길이, MIDI)` 멀티셋, 마디 번호·시작·길이를 다시 대조한다. 반복 좌표로 연결된 레코드는 `exact`가 아닌 `verified_transform`이며, 불일치 구간의 화성 레코드는 `ambiguous`로 남긴다. `source_harmony_context`에서는 모호한 레코드를 제외한다.
- 결과 파일이 만들어졌다는 사실과 점수 전체를 재사용할 수 있다는 판단을 분리한다. `alignment_quality`는 `validated_complete`, `validated_partial`, `quarantined`로 기록한다. 마디 불일치가 있거나 음표·주석 연결률이 각각 95% 미만이면 격리한다. 부분 통과에서도 모호한 개별 화성 레코드는 사용하지 않는다. **95%는 이번 수입기의 잠정 운영 문턱이지 음악적 정답률 목표가 아니다.** `alignment_eligible`는 좌표 검증만 뜻하며 라이선스·작품 중복·사람 검수 여부를 승인하지 않는다.

## 실제 검증 결과

기존 50쌍 표본에서 43쌍은 결과 파일이 만들어졌고 7쌍은 반복 시간축으로 중단됐다. 새 수입기로 **50쌍 모두 결과 파일**을 만들었다. 하지만 새 품질 관문을 통과한 것은 **43쌍**(완전 27, 부분 16)이고 **7쌍은 격리**됐다. 즉 원래 보류한 7쌍 중 4쌍이 좌표 검증을 부분 통과했고 3쌍은 마디 번호/길이 등의 불일치로 격리됐다. 기존에 결과 파일이 있었던 자료 중에도 4쌍이 새 관문에서 격리됐다. 이를 단순히 `43→50 성공`이라고 표현하지 않는다.

50쌍에는 6,377마디·화성 주석 11,465개가 있다. 주석 정렬 상태는 `exact` 6,654, `verified_transform` 4,105, `ambiguous` 706개다. 음표표 85,271개 중 83,513개가 IR의 시작·길이·MIDI와 일치했다. 이는 전체 집계이며 격리 악보의 모호한 주석을 숨기지 않는다.

이전에 중단된 7쌍 중 위치 대조를 통과한 네 악보:

| 자료 | 연결된 화성/전체 | 음표 대조 | 상태 |
|---|---:|---:|---|
| Beethoven sonata 01-4 | 352/355 | 3156/3156 | 부분 통과 |
| Beethoven sonata 02-1 | 477/479 | 3103/3103 | 부분 통과 |
| Chopin mazurka BI115-2op33-2 | 197/202 | 1895/1902 | 부분 통과 |
| Beethoven sonata 03-1 | 481/487 | 4276/4373 | 부분 통과 |

나머지 세 악보는 격리됐다. Beethoven quartet `n02op18-2_03`와 `n03op18-3_01`은 인쇄 마디 번호가 TSV와 각각 47, 162개 행에서 다르고, sonata `02-4`는 마디 시작/길이 차이가 있다. 이 문제를 임의의 오프셋 가산이나 제목별 예외 규칙으로 덮지 않는다.

## 파일·재현

- 구현: `src/musicanote_harness/dcml_import.py`, `src/musicanote_harness/dcml_batch.py`
- 회귀 테스트: `tests/test_dcml_import.py`, `tests/test_dcml_batch.py`
- 결과: `output/dcml-batch-repeat-v2-2026-09-24/batch_summary.json`, `prepared_tracks.jsonl`, `pairs/*/preparation_report.json`

```powershell
$env:PYTHONPATH='src'
& '.\.venv\Scripts\python.exe' -m musicanote_harness.cli validate-dcml-batch `
  'output\classical-corpora-registry-2026-09-24\dcml_pair_candidates.jsonl' `
  --output 'output\dcml-batch-repeat-v2-2026-09-24' --limit 50 --timeout 90
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests -q
```

배치 재실행 시 같은 adapter version의 결과만 재사용한다. 다음 단계는 격리된 마디 번호/길이 차이를 원본 기보와 대조하여 **공통 규칙으로** 해결할 수 있는지 검토하고, 그 뒤 392개 MusicXML 후보로 확장하는 것이다. 점수 전체를 포괄하는 맹검 화성 분석 정확도는 별도 evaluator가 필요하다.
