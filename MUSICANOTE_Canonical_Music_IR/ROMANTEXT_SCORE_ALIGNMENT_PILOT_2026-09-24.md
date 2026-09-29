# RomanText 악보 좌표 정렬: 파일럿과 전수 검사 — 2026-09-24

## 목적

RomanText 파일이 읽힌다는 사실만으로 화성 주석을 Canonical IR에 붙이지 않는다. 동일 폴더의 악보 후보를 결정론적으로 선택하고, 각 RomanNumeral의 인쇄 마디·박자·길이·박자표가 실제 악보 좌표와 맞는지 먼저 검사한다. 이 단계는 **좌표 검사**이며 화성 표기의 음악적 정답 여부, 사람 검수 여부, 라이선스를 승인하지 않는다.

## 구현 규칙

- 악보 후보 우선순위: `musicxml → mxl → mei → krn → mscx → mscz`.
- RomanText는 music21의 RomanText parser로 문법과 박자 내 위치를 해석한다.
- RomanText의 `mN`은 Canonical IR의 `printed_measure_number`와 유일하게 연결될 때만 사용한다.
- onset과 duration은 분모 16,384 이하의 유리수로 복원하고 오차 허용치는 quarter 기준 `1e-10`이다.
- 이벤트가 마디 밖으로 나가거나, 박자표가 다르거나, 인쇄 마디가 없거나 중복되면 `ambiguous`로 둔다.
- 자동 분석 파일은 계속 silver/machine track이며 human gold로 승격하지 않는다.
- parser가 거부한 파일을 임의로 보정하지 않고 원본 줄과 예외를 기록한다.

구현은 `src/musicanote_harness/romantext_alignment.py`, CLI는 `align-romantext-scores`다. 결과는 곡별 JSONL과 집계 JSON으로 분리한다.
전수 작업은 1–4개 독립 process worker를 사용할 수 있다. 각 pair 결과는 analysis/score SHA-256과 adapter version을 함께 `pair_cache`에 저장하므로, 중단 후 같은 원본·같은 버전만 재사용한다.

## 20곡씩의 파일럿 결과

### OpenScore Lieder

- 완전 좌표 정렬: 6곡
- 부분 좌표 정렬: 13곡
- RomanText parse/alignment 오류: 1곡
- 이벤트: exact 1,393 / ambiguous 362
- ambiguous 원인: 박자표 불일치 344, 마디 밖 이벤트 177, 중복 인쇄 마디 6, 누락 인쇄 마디 1. 한 이벤트에 복수 원인이 있을 수 있다.

한 자동 분석 파일은 선언된 박자 안에 코드 이벤트가 너무 많이 들어가 music21 parser가 거부했다. 이를 자동 수정하지 않는다. OpenScore Lieder에서는 자동 RomanText의 박자 선언과 실제 악보가 다른 사례가 상당하므로, 같은 폴더에 있다는 사실만으로 학습용 정답으로 쓰면 안 된다.

### When in Rome

- 완전 좌표 정렬: 17곡
- 부분 좌표 정렬: 2곡
- RomanText parse/alignment 오류: 1곡
- 이벤트: exact 1,640 / ambiguous 2
- ambiguous 원인: 마디 밖 이벤트 2

이 표본에서는 When in Rome 좌표가 훨씬 안정적이었다. 다만 오류 파일도 `analysis_automatic.rntxt`였고, 한 마디 안의 이벤트 수가 박자를 초과하여 parser가 거부했다. 전수 검사 전에는 전체 비율로 일반화하지 않는다.

## 2,029쌍 전수 검사 결과

같은 폴더에 지원 악보 후보가 있는 RomanText 2,029개를 모두 검사했다.

| 코퍼스 | pair | 완전 정렬 | 부분 정렬 | parser 오류 | exact event | ambiguous event |
|---|---:|---:|---:|---:|---:|---:|
| OpenScore Lieder | 1,156 | 693 | 390 | 73 | 100,980 | 8,384 |
| When in Rome | 873 | 698 | 143 | 32 | 49,421 | 1,307 |
| 합계 | 2,029 | 1,391 | 533 | 105 | 150,401 | 9,691 |

parser가 성공한 파일에서 나온 RomanNumeral 이벤트는 160,092개이며 exact 좌표 비율은 약 **93.9%**다. parser 오류 105개는 모두 `RomanTextTranslateException`으로 기록했으며, 해당 파일을 부분 성공으로 위장하지 않는다. 코퍼스별 exact 비율은 OpenScore Lieder 약 92.3%, When in Rome 약 97.4%다. 이는 좌표 성공률이지 로마숫자 화성 정답률이 아니다.

ambiguous 진단은 다음과 같다. 한 이벤트에 여러 진단이 붙을 수 있어 합계가 ambiguous event 수보다 클 수 있다.

| 진단 | OpenScore Lieder | When in Rome | 합계 |
|---|---:|---:|---:|
| 박자표 불일치 | 6,699 | 1,105 | 7,804 |
| 마디 밖 이벤트 | 2,591 | 416 | 3,007 |
| 악보의 인쇄 마디 번호가 유일하지 않음 | 1,126 | 65 | 1,191 |
| 악보에 인쇄 마디 번호가 없음 | 302 | 18 | 320 |

전수 산출물은 `output/romantext-score-alignment-all-2026-09-24/romantext_alignment_summary.json`, `romantext_alignment_records.jsonl`, `pair_cache/`에 있다.

## 함께 발견하고 수정한 Canonical IR 문제

일부 성악·피아노 악보는 서로 다른 두 파트가 같은 source part label(`Voice`)을 사용한다. 기존 prototype builder는 이를 한 내부 part로 합쳐 대표 마디가 중복될 수 있었다. 이제 동일 source label이 여러 파트에 나타나면 내부 ID를 `Voice__part_1`, `Voice__part_2`처럼 결정론적으로 분리하고, 원래 label은 `source_part_id`로 보존한다. 특정 악보 예외가 아니라 모든 중복 part label에 적용되는 규칙이다.

## 다음 단계

1. **완료:** exact 좌표 이벤트를 Imported Annotation + Alignment Record로 변환하는 곡별 importer를 구현했다.
2. **완료:** partial pair의 ambiguous 이벤트는 target 없이 원본 locator와 진단을 보존한다.
3. **완료:** `analysis_automatic`을 `machine_generated_unreviewed` track으로 명시하며 human gold와 분리한다.
4. **완료:** 악보 위 overlay, 검색·필터, 상세 source/IR 정보를 제공하는 곡별 검토 화면을 구현했다.
5. **다음:** 전수 batch 수입과 catalog를 만들고, 실제 음표/베이스/비화성음 evidence와 대조한 화성 정확도 등급을 추가한다.

후속 구현과 실제 Bach 예제는 [RomanText 수입·악보 검토 화면](ROMANTEXT_IMPORT_AND_REVIEW_2026-09-25.md)에 기록한다.

파일럿 산출물: `output/romantext-score-alignment-pilot-2026-09-24/`, `output/romantext-score-alignment-wir-pilot-2026-09-24/`.
