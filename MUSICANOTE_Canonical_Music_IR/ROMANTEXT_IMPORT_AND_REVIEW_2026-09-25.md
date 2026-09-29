# RomanText 수입·악보 검토 화면 — 2026-09-25

## 목적

RomanText 화성 주석을 Canonical Core에 섞지 않고, 검증된 악보 좌표를 참조하는 외부 Imported Annotation과 Alignment Record로 변환한다. 15만여 이벤트를 한 화면에 모두 그리지 않고 **한 곡씩 악보 위에서 검토**한다. 대규모 자료는 검색·필터·집계 대상으로 유지하고, 실제 음악 문맥의 판단은 선택한 곡의 온전한 악보에서 수행한다.

이 단계는 원본 주석을 MUSICANOTE가 사용할 수 있는 형태로 연결하는 작업이다. 좌표가 맞는다는 사실은 화성 해석이 정답이거나 human gold라는 뜻이 아니다.

## 구현

- `src/musicanote_harness/romantext_alignment.py`
  - 선택적으로 모든 RomanText 이벤트와 Canonical IR을 반환한다.
  - 인쇄 마디, 마디 안 onset, duration, meter를 유리수 좌표로 검증한다.
- `src/musicanote_harness/romantext_import.py`
  - exact 이벤트는 공통 `[start, end)` IR span에 연결한다.
  - ambiguous 이벤트는 원문과 진단을 보존하되 target을 만들지 않는다.
  - 겹치는 sounding event와 attack note를 evidence reference로 기록한다.
  - `analysis_automatic.rntxt`는 `machine_generated_unreviewed`로 표시한다.
  - 사람이 작성한 것으로 보이는 파일도 출처 확인 없이 human gold로 승격하지 않는다.
- `src/musicanote_harness/romantext_review.py`
  - Verovio 악보 위에 exact 로마숫자 주석을 `[start, end)` 화성 구간으로 표시한다.
  - 선택한 화성 구간의 모든 음표는 황색, 시작 attack은 녹색, 다음 화음 직전의 마지막 attack은 적색으로 구분한다.
  - 끝 좌표는 다음 화음의 시작점이므로 이전 화음에 포함하지 않는다. 화면의 적색은 끝 좌표 자체가 아니라 그 전의 마지막 attack이다.
  - 황색은 시간 범위 표시이며 그 안의 모든 음표가 화음 구성음이라는 주장이 아니다. NCT 판정은 별도 Analysis Layer에서 수행한다.
  - 화성, 조성, 마디를 검색하고 exact/ambiguous를 필터링한다.
  - 악보의 표기나 오른쪽 목록을 누르면 기준 음표를 강조하고 상세 정보를 연다.
  - 상세 정보에는 IR span, 원문 파일·줄, 정렬 상태, 출처 등급, 진단을 표시한다.
- CLI `prepare-romantext`
  - 한 쌍의 RomanText와 악보를 재현 가능한 검토 패키지로 만든다.

## 산출물 계약

곡별 패키지는 다음 파일을 가진다.

| 파일 | 역할 |
|---|---|
| `canonical_music_ir.json` | 관찰 사실과 결정론적 score event |
| `imported_annotations.jsonl` | 외부 화성 주석과 출처 상태 |
| `alignment_records.jsonl` | source locator와 IR target의 정렬 판정 |
| `source_harmony_context.json` | 분석기가 선택적으로 참조할 수 있는 source-conditioned context |
| `source_harmony_context_evidence.json` | 앞뒤 화성 경계의 bass·성부 진행·해결 후보 증거 |
| `harmony_overlay_artifact.json` | 공유 악보 Viewer가 읽는 기본 OFF·표시 전용 overlay 계약 |
| `source_harmony_evidence.json` | 원자료 화성과 실제 악보의 별도 호환 증거; 정답·confidence 아님 |
| `preparation_report.json` | exact/ambiguous 수와 출처 정책 집계 |
| `romantext-review.html` | 악보 기반 사람 검토 화면 |
| `score-page-*.svg` | Canonical ID를 보존한 악보 렌더링 |
| `engraving_id_mapping_report.json` | IR note와 SVG note의 완전성 검사 |

`source_harmony_context.json`은 blind 분석기의 입력이 아니다. source annotation을 참고하도록 명시한 평가·검색·작곡/편곡 작업에서만 사용한다. blind 평가에서는 이 파일을 숨겨 데이터 누출을 막는다.

## 실행 예

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m musicanote_harness.cli prepare-romantext `
  --analysis 'K:\path\analysis_automatic.rntxt' `
  --score 'K:\path\score.musicxml' `
  --output 'output\romantext-review\piece-001'
```

## 실제 검증 예제

When in Rome의 Bach, *The Well-Tempered Clavier I*, Prelude 1을 실제 입력으로 사용했다.

- RomanText event: 37
- exact target: 37
- ambiguous target: 0
- Canonical note ↔ 렌더링 note: 619 / 619
- source review status: `machine_generated_unreviewed`
- 로컬 검토 주소: `http://127.0.0.1:8765/wtc1-prelude-01/romantext-review.html`
- 파일: `output/romantext-import-review-2026-09-25/wtc1-prelude-01/romantext-review.html`

화면에 37개를 표시할 수 있다는 것과 150,401개 exact 이벤트를 한꺼번에 표시하는 것은 다르다. 이후 전체 운영 화면은 곡·작곡가·코퍼스·조성·화음 검색으로 대상을 고른 뒤 이 곡별 검토 화면을 여는 catalog 구조로 만든다.

## 공유 악보 Viewer 브리지

2026-09-25에 source-conditioned harmony artifact를 `K:\MusicSearch`의 공유 악보 Viewer에 **표시 전용 실험 레이어**로 연결했다.

- `harmony_overlay_artifact.json`에 `source_identity.score_sha256`와 `analysis_sha256`를 추가했다.
- catalog API `GET /api/overlay/by-score-sha256/{sha256}`가 원본 악보 byte hash로만 대상을 찾는다.
- 동일 score hash에 분석본이 둘 이상이면 하나를 임의 선택하지 않고 HTTP 409와 후보 목록을 반환한다.
- MusicSearch의 `/api/analysis/harmony-overlay?workId=...`는 score hash를 계산해 catalog API를 조회한다.
- Viewer 오른쪽의 `화성 분석(실험)`은 곡을 바꿀 때마다 기본 OFF로 초기화하며, 사용자가 켤 때만 자료를 요청한다.
- 이 단계의 Viewer 연결은 목록·출처·surface evidence 확인용이다. 악보 음표 위 직접 색칠은 Canonical event ID와 Viewer note ID의 교환 계약을 검증한 뒤 추가한다.
- `structure_influence=none`이므로 Phrase, Motif, Cadence, Pillar 점수에는 공급하지 않는다.
- 현재 검색 DB에 RomanText 코퍼스의 동일 원본 파일이 색인되지 않은 곡은 `검증용 화성 주석 없음`으로 표시한다. 제목이 같다는 이유로 다른 판본 주석을 붙이지 않는다.

## 검증

- 전체 단위 테스트: 41개 통과
- JSON Schema: Imported Annotation과 Alignment Record 검증 통과
- 악보 ID mapping: 619개 전부 연결, 누락 0
- UI: 37개 overlay와 37개 목록 항목 표시 확인
- bridge API: Bach 예제 score hash로 unique/cached 응답과 37개 item 반환 확인
- MusicSearch: TypeScript/Vite production build 통과, 기존 5173 서버에서 `no_audited_source`의 안전한 보류 응답 확인
- `git diff --check`: 공백 오류 없음

## 다음 단계

## 곡 검색 카탈로그

2,029개의 전수 정렬 결과를 다시 parsing하지 않고 읽는 검색 카탈로그를 추가했다. 작곡가·작품·경로 검색, 코퍼스와 정렬 상태 필터를 제공한다. `악보로 보기`를 누른 곡만 Canonical IR, source annotation, SVG 악보와 검토 HTML을 생성한다. 같은 source hash로 이미 생성한 곡은 cache를 재사용한다.

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m musicanote_harness.cli serve-romantext-catalog `
  'output\romantext-score-alignment-all-2026-09-24\romantext_alignment_records.jsonl' `
  --evidence-records 'output\romantext-source-evidence-all-2026-09-25\romantext_evidence_pair_records.jsonl' `
  --output 'output\romantext-catalog-reviews-2026-09-25' `
  --host 127.0.0.1 --port 8766
```

로컬 주소는 `http://127.0.0.1:8766/`이다. 서버는 catalog에 등록된 ID만 받아들이며 사용자가 임의의 파일 경로를 넘겨 parser를 실행하게 하지 않는다. exact 좌표가 하나도 없는 오류/완전 ambiguous 항목은 화면 생성 버튼을 비활성화한다. 선택적인 evidence record를 연결하면 곡별 support band 분포와 weak/mixed 필터도 제공한다.

## 다음 단계

1. **완료:** exact 좌표의 source label과 실제 음표·시작 bass를 비교하는 별도 evidence scorer를 추가했다. 자세한 규칙은 [RomanText source evidence](ROMANTEXT_SOURCE_EVIDENCE_2026-09-25.md)에 기록한다.
2. source label을 가린 blind harmony analyzer와 source-conditioned retrieval을 계속 분리한다.

## Shared Viewer 연결 갱신

`harmony-overlay-artifact-0.3.0`부터 overlay layer는 기본 활성화되며 interaction mode는 `ambiguity_review`다. 각 item은 `review_candidate`, `review_priority`, `review_reasons`를 포함한다. 이 메타데이터는 source annotation 자체를 변경하지 않고 검토 순서만 정한다. MusicSearch 상세 화면은 모호한 구간만 먼저 표시하고, 사용자의 구간별 의견은 catalog의 append-only reviewer annotation으로 저장한다.

연결은 exact MusicXML SHA-256 일치에 한정한다. 동일 곡명, 유사 멜로디 또는 편곡 관계만으로 원자료 RomanText를 다른 악보에 복사하지 않는다. 따라서 이 단계에서 모든 상세 화면에 패널은 존재하지만, source-aligned harmony가 실제로 표시되는 범위는 catalog와 정확히 일치하는 악보다. 나머지 악보의 전체 화성은 이후 blind analyzer가 hypothesis + confidence + evidence 형태로 공급해야 한다.
3. cadence, NCT, local key는 Imported Annotation 위에 추정 결과를 덮어쓰지 말고 별도 versioned Analysis Record로 만든다.
