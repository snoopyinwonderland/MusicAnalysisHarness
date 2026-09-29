# 전체 코퍼스 등록과 화성 주석 정렬 확대 — 2026-09-24

## 목적과 의미

사용자 목표는 한 악보의 모든 구간을 이해하여 분석·편곡·작곡에 쓰는 것이다. 따라서 세 악장만의 DCML 표본에 머무르지 않고 로컬 코퍼스 전체를 사용 가능하게 만들기 시작했다. **모든 데이터를 활용한다**는 것은 23만 개 파일을 하나의 화성 정답 표로 섞는다는 뜻이 아니다. 먼저 원본·판본·주석 종류·시간축·출처·중복 계보를 구분하고, 각 자료를 적합한 역할에 연결한다. 이 작업은 전체 코퍼스의 학습, 화성 예측 정확도 검증, 라이선스 승인 완료를 뜻하지 않는다.

## 구현

- `src/musicanote_harness/classical_registry.py`: `K:/MusicSearch/data/classical-corpora`를 **읽기 전용**으로 순회해 `assets.jsonl`과 `registry_summary.json`을 생성한다. Windows 긴 경로도 별도 처리한다. 각 asset의 형식·코퍼스·용도 *후보*를 적되, hash·작품·판본·사람 검수·라이선스는 확인 전까지 `null`/`unverified`로 남긴다.
- `dcml_pair_candidates.jsonl`: DCML 하위 코퍼스별 악보/measure/note/harmony 표의 같은 stem을 파일 후보로 묶는다. MusicXML은 `complete_files_unaligned`, MuseScore `.mscx`는 `complete_files_requires_conversion`, 누락이 있으면 `incomplete_files`로 기록한다. 같은 stem만으로 악보·주석이 검증됐다고 주장하지 않는다.
- `src/musicanote_harness/dcml_batch.py`: `validate-dcml-batch`에서 여러 하위 코퍼스를 round-robin으로 골라 보수적으로 수입·정렬한다. 각 쌍을 별도 프로세스·시간 제한으로 실행하고, 성공 산출물을 재사용한다. `prepared_tracks.jsonl`은 score/IR/track ID와 경로를 연결하되 source-conditioned만 허용한다.
- DCML Corelli의 `gracenote` 열 부재는 선택적 열로 처리했다. Beethoven 01-4처럼 1·2번 엔딩에서 `quarterbeats`가 비어 있고 `quarterbeats_all_endings`가 있는 경우에는 작성된 악보 시간축과 실행 시간축이 다를 수 있으므로 **자동으로 다른 열을 대신 쓰지 않는다**. `unsupported_repeat_timeline`으로 명시해 보류한다.

## 전체 자산 현황

2026-09-24 로컬 실행에서 21개 코퍼스 디렉터리(루트의 별도 파일 1개 포함), **233,882개 파일**, 약 **15.0 GB**를 확인했다. 긴 경로 대응 뒤 scan error는 **0**이다. 이는 물리 파일 수이며 서로 다른 작품이나 검수된 화성 주석 수가 아니다. 주요 형식은 `.jams` 106,810개, `.musicxml` 4,694개, `.mxl` 12,903개, `.rntxt` 2,077개, `.tsv` 8,575개 등이다. ChoCo의 JAMS에는 DCML/When in Rome 등의 재수록과 다른 시간 단위가 섞여 있을 수 있으므로 독립 gold 수로 세지 않는다.

DCML `MS3` 악보를 기준으로 한 파일 후보는 **1,129쌍**:

| 상태 | 후보 수 | 의미 |
|---|---:|---|
| MusicXML + 3종 TSV | 392 | 실제 정렬 검증 대상. 아직 392쌍 모두 성공한 것은 아님 |
| MuseScore `.mscx` + 3종 TSV | 262 | 변환기·원본 악보 보존·변환 검증이 먼저 필요 |
| 대응 파일 일부 누락 | 475 | 화성 정답 쌍으로 바로 사용 불가; 악보/음표/metadata 등 다른 용도를 조사 |

`.mscx`는 music21이 직접 파싱하지 못했고 현재 컴퓨터에서 MuseScore 실행기를 찾지 못했다. 외부 변환 결과를 MusicXML 원본처럼 위장하지 않는다. 다른 코퍼스의 RomanText, JAMS, Humdrum, performance/MIDI, form 자료도 registry에는 들어왔지만 각자의 adapter·좌표/출처 확인은 아직 별도 작업이다.

## 50쌍 검증 실행 결과

5개 DCML 하위 코퍼스에서 round-robin으로 50쌍을 선택했다. **43쌍**은 정렬 자료를 만들었고 **7쌍**은 반복 엔딩 시간축으로 보류됐다. 43쌍에는 4,889마디·9,082개 화성 주석이 있으며, 6,558개 `exact`, 2,247개 `verified_transform`, 277개 `ambiguous`다. 따라서 8,805개는 악보 위치 연결을 사용해 검토할 수 있고, 277개는 자동 승인하지 않는다. 이것은 **좌표 정렬률이지 화성 레이블의 음악적 정확도·사람 검수율이 아니다**. 43개 트랙을 `prepared_tracks.jsonl`에 색인했다.

처음의 12쌍 중 Corelli 2쌍은 선택적 `gracenote` 열 때문에 실패했으나 입력 계약을 바로잡아 모두 준비됐다. Beethoven 01-4의 반복 엔딩은 parser의 global quarter가 TSV의 `quarterbeats_all_endings`와도 일치하지 않아, 숫자를 강제로 맞추지 않았다. 50쌍에서 7쌍이 같은 종류의 보류로 나타나므로 written/repeat-expanded 시간축 설계가 우선 과제다.

## 재현과 산출물

```powershell
$env:PYTHONPATH='src'
& '.\.venv\Scripts\python.exe' -m musicanote_harness.cli inventory-classical `
  'K:\MusicSearch\data\classical-corpora' `
  --output 'output\classical-corpora-registry-2026-09-24'
& '.\.venv\Scripts\python.exe' -m musicanote_harness.cli validate-dcml-batch `
  'output\classical-corpora-registry-2026-09-24\dcml_pair_candidates.jsonl' `
  --output 'output\dcml-batch-2026-09-24' --limit 50 --timeout 90
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests -q
```

Registry: `output/classical-corpora-registry-2026-09-24/{assets.jsonl,registry_summary.json,dcml_pair_candidates.jsonl}`. Batch: `output/dcml-batch-2026-09-24/{batch_summary.json,prepared_tracks.jsonl,pairs/}`. 기존 결과를 지우지 않고 동일 경로에서 재실행할 수 있다. 원본 `K:/MusicSearch/data/classical-corpora` 파일은 수정하지 않았다.

## ‘모두 활용’의 다음 게이트

1. 392개 MusicXML 쌍은 보수적인 반복 시간축 지도와 더 많은 회귀 검사를 만든 뒤 단계적으로 배치 정렬한다. 실패·모호한 주석은 빼고 성공 트랙만 조회 대상으로 등록한다.
2. 262개 `.mscx` 쌍은 신뢰할 수 있는 MuseScore→MusicXML 변환 경로를 확보하고 원본/변환본을 모두 보존한다. 음표·마디·타이·성부 대조를 통과해야 같은 방식으로 수입한다.
3. When in Rome `.rntxt`, TAVERN Humdrum, ChoCo JAMS, OpenScore/Lieder의 자동·사람 분석은 **각기 다른 adapter와 provenance**로 수입한다. 동일 작품·분석 계보를 중복 정답으로 세지 않는다.
4. 화성 레이블이 없는 악보, YCACL 관찰 슬라이스, ASAP/MAESTRO 연주, Taking Form 형식 자료는 역할에 맞는 음형·성부·스타일·형식·연주 근거로 사용한다. 없는 화성/NCT 정답을 만들어내지 않는다.
5. 실제 화성 분석 성능은 주석을 숨긴 `blind` 실행과 별도 evaluator로 측정한다. 검수된 주석을 참고하는 작곡·편곡은 `source_annotation_conditioned` 실행으로 분리하고, 출처·라이선스·annotation lineage를 결과에 기록한다.

이 문서가 완료될 때까지 **모든 코퍼스가 실제 분석기에 연결됐다고 말하지 않는다**. 현재 완료는 전체 파일 registry와 DCML 43개 score-linked 트랙의 정렬 검증이다.
