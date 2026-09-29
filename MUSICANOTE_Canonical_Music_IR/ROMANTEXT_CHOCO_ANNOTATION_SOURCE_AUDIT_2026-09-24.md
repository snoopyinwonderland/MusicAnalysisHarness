# RomanText·ChoCo JAMS 주석 출처·형식 검사 — 2026-09-24

## 목적과 검증 수준

DCML 밖의 주석을 분석기에 넣기 전에 실제 파일 구조와 출처 계보를 확인했다. `analysis_automatic.rntxt`나 ChoCo에 재수록된 JAMS를 사람 검수 정답으로 가정하지 않는다. 이번 검사는 **텍스트/JSON 형태·메타데이터·이벤트 시간의 기본 형태**를 확인한 것이며, 악보의 음표·마디 시간축과의 연결, 로마숫자 의미 검증, 작품/분석 중복 제거, 라이선스 확인은 하지 않았다.

## RomanText: 2,077개

| 코퍼스 | 파일 | 형태 읽기 성공 |
|---|---:|---:|
| OpenScore Lieder | 1,156 | 1,156 |
| When in Rome | 921 | 921 |

**1,876개**는 파일명이 `analysis_automatic.rntxt`이고 Analyst 헤더가 `AugmentedNet v1.9.1`이다. 나머지 **201개**는 When in Rome의 `analysis.rntxt`이며 Analyst 헤더가 `Napoles Lopez et al.`이다. 일부에는 자동 번역/교정 관련 설명도 있으므로 201개를 자동으로 human gold로 승격하지 않는다. **2,029개**는 같은 폴더에서 악보 후보 파일을 찾았고, **48개**는 찾지 못했다(모두 When in Rome). 형식상 읽혔다는 사실만으로 RomanText 문법이나 악보 위치가 검증된 것은 아니다.

## ChoCo JAMS: 106,792개

ChoCo의 테스트 fixture 18개를 제외하고 실제 파티션과 예제에서 **106,792개**를 검사했다. **106,747개**는 기본 JSON/이벤트 구조를 읽었고, **45개**에는 음수 또는 해석이 필요한 시간·길이 값이 있었다. 파싱 자체가 실패한 파일은 0개다. Mozart piano sonata JAMS의 `chord_roman` 이벤트에 `duration=-2.0`인 실제 사례가 있다. 이것이 무효값인지 원본 변환의 sentinel인지는 후속 대조 전까지 확정하지 않는다. 어떤 경우든 그대로 `[start,end)` 구간으로 사용할 수 없다.

주요 annotation namespace의 **트랙 수 / 데이터 행 수**:

| Namespace | 트랙 | 행 |
|---|---:|---:|
| `chord_harte` | 57,928 | 4,513,524 |
| `chord` | 39,235 | 3,520,976 |
| `chord_roman` | 1,554 | 338,830 |
| `key_mode` | 106,837 | 120,791 |
| `timesig` | 36,031 | 40,504 |
| `chord_m21_leadsheet` | 6,119 | 350,411 |

이 트랙·행 수는 서로 다른 음악 작품이나 정답 수가 아니다. 한 JAMS 안에 같은 시간의 서로 다른 `chord_roman` 분석 트랙이 공존하는 사례가 있어, 서로 다른 가설/출처를 유지해야 한다. ChoCo annotation metadata의 원본 코퍼스에는 `Wikifonia`, `BiaB Internet Corpus`, `When in Rome` 등이 있으며 **142,268개 annotation 트랙은 `corpus` 값이 비어 있다**. `When in Rome` 표기가 있는 트랙만도 3,592개여서 RomanText와 무관한 독립 정답으로 일괄 합산할 수 없다. 대소문자가 다른 같은 코퍼스명도 존재하므로 lineage 정규화가 필요하다.

ChoCo의 시간값이 초인지 박인지 등 좌표 기준은 자료 유형마다 다를 수 있다. 이번 단계에서는 JAMS `time`을 Canonical IR의 quarter offset에 직접 붙이지 않았다.

## 산출물과 다음 수입 순서

- 코드: `src/musicanote_harness/annotation_source_audit.py`; CLI `audit-romantext-sources`, `audit-jams-sources`.
- 결과: `output/annotation-source-audit-2026-09-24/romantext_summary.json`, `romantext_records.jsonl`, `jams_summary.json`, `jams_records.jsonl`.
- 테스트: `tests/test_annotation_source_audit.py`.

다음 구현은 (1) 같은 폴더 악보가 있는 RomanText의 시간축·Roman 문법·출처 연결, (2) ChoCo의 원본 코퍼스/분석 계보·좌표 단위별 adapter, (3) 동일 작품/판본/분석 중복 관계, (4) 45개 특수 시간값의 의미 확인 순서로 진행한다. `analysis_automatic`은 별도 **silver/auto track**으로만 사용하고 사람 주석과 섞지 않는다. 이 자료를 화성 분석기의 맹검 성능 평가 정답으로 쓰기 전에는 악보 연결과 annotation provenance를 추가로 검증한다.

RomanText의 첫 좌표 연결 구현과 40곡 파일럿 결과는 [RomanText 악보 좌표 정렬 파일럿](ROMANTEXT_SCORE_ALIGNMENT_PILOT_2026-09-24.md)에 이어 기록했다.
