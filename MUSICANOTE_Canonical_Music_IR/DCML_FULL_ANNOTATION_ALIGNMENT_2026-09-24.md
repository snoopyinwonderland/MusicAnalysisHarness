# DCML MusicXML 392쌍 화성 주석 정밀 정렬 — 2026-09-24

## 범위와 결론

MusicXML 악보와 3종 TSV가 갖춰진 DCML **392쌍 전부**를 Canonical IR로 파싱하고 마디·음표·주석 구간을 대조했다. 인쇄 마디 번호 alias 재검증을 포함한 adapter 0.3.0 결과, **품질 관문 통과는 333쌍**이다: `validated_complete` 221, `validated_partial` 112. 다른 **59쌍은 `quarantined`**이며 일반 조회/사례 입력 대상으로 자동 승인하지 않는다. 원본 코퍼스는 수정하지 않았다.

이 결과는 주석과 악보의 **좌표 연결 검증**이다. 로마숫자의 음악적 정확도, 사람 검수, 라이선스, 동일 작품 중복, 맹검 화성 예측 정확도는 확인되지 않았다. 주석에 조건을 건 편곡/검색과 주석을 숨긴 자동 분석 평가는 별도 모드로 유지한다.

| 대상 | 악보 수 | 화성 주석 | 연결된 주석 | 모호한 주석 |
|---|---:|---:|---:|---:|
| 품질 관문 통과: 완전 | 221 | 32,966 | 32,966 | 0 |
| 품질 관문 통과: 부분 | 112 | 39,382 | 38,700 | 682 |
| 격리 | 59 | 16,415 | 12,368* | 4,047 |
| 전체 | 392 | 88,763 | 84,034* | 4,729 |

`*` 격리 악보 안에서 개별 레코드의 위치가 맞아 보이더라도 **점수 전체의 품질 관문을 통과하지 않았으므로** 일반 조회용 연결 수에 포함하지 않는다. 현재 이용 가능한 위치 연결 후보는 통과 악보의 **71,666개**다. 부분 통과 악보의 682개 모호한 레코드는 `source_harmony_context`에서 제외된다.

음표표 640,792행 중 626,563행이 IR의 시작·길이·MIDI와 일치했다. 전체 마디 수는 44,989다. 음표 수 역시 격리 악보를 포함한 집계이며 악보마다 판본 차이나 파서 오류를 추가로 조사해야 한다.

## 왜 단순 표 검사로 끝낼 수 없는가

빠른 표·악보 구조 검사에서 일관됐던 270쌍 중에도 정밀 대조에서 14쌍이 격리됐다. 반대로 표 검사에 검토 신호가 있던 122쌍 중 77쌍(완전 3, 부분 74)은 정밀 대조 품질 관문을 통과했다. 인쇄 마디 번호 차이가 곧 음악적 시간축 차이는 아니기 때문이다.

| 빠른 검사 | 완전 | 부분 | 격리 |
|---|---:|---:|---:|
| 표·악보 구조 일관 270 | 218 | 38 | 14 |
| 검토 신호 122 | 3 | 74 | 45 |

## 격리 이유와 다음 일반 규칙

adapter 0.2.0에서 격리됐던 69쌍 중 **21쌍은 마디 문제의 종류가 인쇄 번호 차이뿐**이었다. adapter 0.3.0은 순차 마디(`mc`)·시작·길이·박자표·음표 대조가 일치할 때만 인쇄 번호 차이를 비차단 경고로 취급하고, `source_printed_measure_number ↔ ir_printed_measure_number` alias를 마디별로 보존한다. Harmony TSV의 `mn`이 Measure TSV의 `mn`과 다르면 별도의 차단 오류로 남긴다.

그 결과 21쌍 중 **10쌍만** `validated_partial`로 승격됐고, 11쌍은 화성 연결률 95% 미만이라 계속 격리됐다. 승격된 10쌍은 4,333개 주석 중 4,287개가 연결됐으며 46개는 여전히 ambiguous로 제외된다. 즉 alias 규칙은 검증된 좌표만 되살렸고 다른 불일치를 덮지 않았다. 전체 격리 이유는 이제 마디 차단 문제 22쌍, 음표 대조율 95% 미만 17쌍, 주석 연결률 95% 미만 53쌍이다. 한 악보에 여러 원인이 겹치므로 합산하지 않는다.

부분 통과 악보에서 모호한 주석의 주요 진단은 음표 일치 문제, source note locator 누락, 빈 `duration_qb` 등이다. 특히 빈 화성 duration은 0박짜리 점이라고 추정하지 않는다. 격리 악보의 인쇄 마디 번호·조표/박자·실제 시작/길이 차이는 별도 원인으로 유지한다.

## 재현·구현

- 구현: `src/musicanote_harness/dcml_import.py`, `src/musicanote_harness/dcml_batch.py`.
- 전체 결과: `output/dcml-batch-repeat-v2-2026-09-24/batch_summary.json`, `prepared_tracks.jsonl`, `pairs/<subcorpus>/<stem>/`.
- `prepared_tracks.jsonl`의 `alignment_quality`, `quality_reasons`, `alignment_eligible`를 확인한다. `alignment_eligible`는 **좌표 품질만** 뜻하며, 법적·음악적 승인 플래그가 아니다.

```powershell
$env:PYTHONPATH='src'
& '.\.venv\Scripts\python.exe' -m musicanote_harness.cli validate-dcml-batch `
  'output\classical-corpora-registry-2026-09-24\dcml_pair_candidates.jsonl' `
  --output 'output\dcml-batch-repeat-v2-2026-09-24' --limit 392 --timeout 180 --workers 3
```

각 악보는 독립 프로세스에서 검증된다. 같은 adapter version, 원본 경로·hash, 필요한 산출물의 존재를 확인한 경우에만 재사용하므로 중단 후 다시 실행할 수 있다. 이 결과를 곧바로 학습 데이터로 쓰지 않고, 코퍼스 출처·작품 중복·라이선스 및 화성 표기 체계 검증을 추가한다.
