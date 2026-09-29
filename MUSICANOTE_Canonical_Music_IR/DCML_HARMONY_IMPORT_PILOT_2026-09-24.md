# DCML 화성 주석 수입 파일럿 — 2026-09-24

## 목적과 현재 경계

궁극적 목표는 악보의 각 부분을 음표·성부·화성·종지·반복·구조·반주 양식까지 연결해 이해하고, 이를 편곡·작곡의 계획과 검증에 사용하는 것이다. 이 단계는 그중 **외부 화성 주석을 원본 악보의 정확한 시간·음표에 연결하는 준비 과정**이다. 주석을 읽어 붙인 결과를 독립적인 자동 화성 분석이라고 부르지 않는다. Phrase/Motif 규칙이나 운영 parser는 변경하지 않았다.

## 구현 경로

- `src/musicanote_harness/dcml_import.py`: `prepare-dcml` 명령의 입력 검증·원본 해시·MusicXML/TSV 정렬·ImportedAnnotation/AlignmentRecord 생성.
- `src/musicanote_harness/harmony_context.py`: 전곡 시간축을 source-annotated/unannotated로 나눈 구간 조회 자료. 원본 레이블과 주석 파일·행·정렬 상태를 함께 보존한다.
- `src/musicanote_harness/source_enrichment.py`: 분리된 피아노 staff를 원본 P1의 staff 1/2에 대응하고, 조표·음자리표·기보 정보를 IR에 기록한다.
- `schemas/imported_annotation.schema.json`, `schemas/alignment_record.schema.json`: 출처, 원본 레이블, 정확/변환확인/모호 상태를 분리하는 계약.
- `tests/test_dcml_import.py`: 마디를 넘는 화음, 길이 0의 구조 표지, 원본 파일 불변, 음표 불일치 보류, 전곡 조회 자료를 시험한다.

수입 과정은 원본 MusicXML을 수정하지 않는다. DCML `<harmony>`의 일부 `<function>`은 music21에서 파싱되지 않으므로 **메모리 내 파싱 사본에서만** 이를 떼어 음표·기보를 읽고, TSV 해석은 별도 수입 주석으로 남긴다. source SHA-256을 모두 보존한다. `mc`는 1부터 시작하는 순차 마디, `mn`은 인쇄 번호로 구별하고, global quarter와 rational duration으로 반열린 구간 `[start,end)`를 정렬한다. 마디를 넘는 화음은 한 구간으로, 길이 0의 프레이즈 표지는 point로 보존한다. 원본 주석의 저자·검수·신뢰도가 없으면 `unknown`/`null`이고 만들어내지 않는다.

## 실제 세 악장 검증

| DCML 표본 | 마디 | 주석 | 승인된 정렬 | 보류 | 원본 XML 음표 대응 | 음표 TSV 대조 |
|---|---:|---:|---:|---:|---:|---:|
| Beethoven Sonata 01-1 | 154 | 241 | 235 exact | 6 | 1,692/1,693 | 1,687/1,693 |
| Beethoven Sonata 01-2 | 62 | 200 | 200 exact | 0 | 1,302/1,302 | 1,302/1,302 |
| Mozart K279-1 | 100 | 251 | 251 verified transform | 0 | 2,050/2,050 | 2,050/2,050 |

`verified transform`은 모차르트 원본 MusicXML의 **P1 한 파트·두 staff**가 music21에서 `P1-Staff1/2` 두 내부 파트로 풀린 것을 명시적으로 다시 연결했다는 뜻이다. 음악적 해석의 확신 점수가 아니다. `exact`도 주석의 음악적 정답성을 뜻하지 않고 **악보 위치 정렬**만 뜻한다.

Beethoven 01-1의 6개 보류 가운데 4개는 grace note 6개의 TSV 시점과 music21 시점이 1 quarter 다른 구간에 걸친다. 나머지 2개는 원본의 삽입 마디 번호 `X1`에 있는 E♭4 음표가 IR의 인쇄 마디 `48`로 정규화되어 원본 XML locator를 자동 복원하지 못한 구간이다. 보류 주석은 전곡 context에서 제외되어 빈 곳으로 표시된다. 이 오류를 숨기거나 인접 화성으로 채우지 않는다.

Beethoven 01-1의 원본 `Ger6` 주석은 quarter `[213,217)`에 있고 이후 `HC`와 프레이즈 표지가 quarter 217 부근에 이어진다. 이것은 증6화음 판별기의 성공 사례가 아니라 **수입·정렬 사례**다. 원본 주석 레이블은 음표·동시 울림 event ID와 연결되어 있어, 앞으로 독립 엔진이 음정·성부진행·해결을 예측한 뒤 비교할 수 있다.

## 재현 명령과 산출물

PowerShell, 저장소 `K:\Music Analysis`에서:

```powershell
$env:PYTHONPATH='src'
$p='K:\MusicSearch\data\classical-corpora\dcmlab\beethoven-sonatas'
& '.\.venv\Scripts\python.exe' -m musicanote_harness.cli prepare-dcml `
  --score "$p\MS3\01-1.musicxml" `
  --measures "$p\measures\01-1.measures.tsv" `
  --harmonies "$p\harmonies\01-1.harmonies.tsv" `
  --notes "$p\notes\01-1.notes.tsv" `
  --output 'output\dcml-beethoven-01-1-pilot'
& '.\.venv\Scripts\python.exe' -m unittest tests.test_dcml_import -v
```

출력은 `canonical_music_ir.json`, `imported_annotations.jsonl`, `alignment_records.jsonl`, `preparation_report.json`, `source_harmony_context.json`이다. `source_harmony_context.json`의 `source_annotation_conditioned` 정책은 **주석을 보면서 쓰는 경우**에만 허용된다. 독립 화성 예측의 성능 평가나 Phrase 개선 검증에서는 이 파일과 원본 XML의 `<harmony>`를 analyzer 입력에서 빼야 한다.

## 다음 개발 순서와 완료 조건

1. `X1` 같은 비표준/삽입 마디와 grace onset 차이를 보수적으로 정규화하고, 다른 코퍼스·파트·변박 사례로 정렬 회귀 테스트를 넓힌다. 재현 가능한 원본 note locator가 없으면 승인하지 않는다.
2. 주석 **blind/conditioned** 실행을 분리하는 평가 Harness, 작품·판본·주석 계보별 holdout, 누수 검사를 만든다. 현재 세 곡은 통합 시험이며 모델 정확도 측정용 독립 holdout이 아니다.
3. 이미 있는 Canonical IR의 vertical-slice evidence와 공격/지속음·베이스·성부 이동을 사용하여 Phrase와 무관한 **전곡 화성 후보/구간화**를 만든다. 국소 조성, 표면 화음, 기능, 비화성음, 지배 화성의 후보·반례·보류를 층별로 기록한다. 가져온 레이블을 독립 결과로 재포장하지 않는다.
4. Cadence는 화음 두 개가 이어진다는 이유만으로 확정하지 않는다. 준비–도착–성부진행–박자–호흡을 검토한 뒤 Phrase/Motif에 **독립 근거만 제한적으로** 보낸다. 순환 참조와 이중 점수 가산을 막는다.
5. 작곡·편곡은 화성 레이블만으로 끝나지 않는다. score-linked 성부 역할, 보이싱, 반주 패턴, 음역, 밀도, 변형 관계를 별도 사례로 축적하고, 생성 계획과 실제 음표를 독립 validator로 대조한다.

## 남은 위험

- 전체 코퍼스의 판본·라이선스·주석 계보 registry는 미구현이다. 파일 개수는 학습 가능한 독립 곡 개수가 아니다.
- 기존 MusicSearch UI와 전곡 context는 아직 연결되지 않았다. 화면에 보이는 자동 화성 분석 결과라고 주장할 수 없다.
- 소스 주석의 `Ger6`, `HC`, 로마숫자는 코퍼스 방언 그대로 보존했다. 표준 화성 ontology 변환과 대안 가설은 아직 없다.
- 한 악보의 주석을 참조하는 편곡과, 주석 없이 처음 보는 악보를 이해하는 엔진은 다른 성능을 갖는다. 실행 결과에 입력 정책을 반드시 붙인다.
