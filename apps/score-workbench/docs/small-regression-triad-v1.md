# Small regression triad v1

2026-09-18에 Terra 회귀 실행기가 실제 로컬 MusicXML corpus에서 고정한 6개 Query를 offline production search로 실행했다. production algorithm, parser, UI, corpus, SQLite index는 변경하지 않았고 network collection/DB sync도 하지 않았다.

## 고정 원형과 재현

- 원형: `ICH LIEBE DICH`, `work-85d804c3a08b060f`, `P1:1:1`, `3. Ich liebe Dich, Violin and Piano Duet.musicxml.xml`.
- 출처: 기존 `duple-meter-15-v1`의 source-only 선별 사례. 2/4에서 leap·반복·엇박을 섞은 12음 구간이므로 전체 순차진행/전체 동음반복 제외 정책에 걸리지 않는다.
- 실제 XML 문맥: 못갖춘 첫 마디(label 0), 원형의 약박 1.75 및 2.5 공격, 1–4번째 measure를 가로지르는 시작/종료를 `source-context.json`에 보존했다.
- 입력, code/DB 지문, 원 XML 문맥은 `evaluation/runs/small-regression-triad-v1-final/suite.json`과 같은 directory의 case JSON에 보존했다. 각 case JSON에는 full search API response, rank/candidate score/alignment와 rendering audit가 있다.

## 결과

| Case | 목적 | target rank | ranking | SVG audit |
| --- | --- | ---: | ---: | --- |
| TRIAD-01 | exact corpus control | 3 | 95.130 | 12/12 resolved/rendered |
| TRIAD-02 | global duration x2 | 3 | 95.790 | 12/12 resolved/rendered |
| TRIAD-03 | local duration + rest mismatch | 3 | 93.477 | 12/12 resolved/rendered |
| TRIAD-04 | pickup, weak-beat start, cross-bar | 2 | 100.000 | 11/11 resolved/rendered |
| TRIAD-05 | same intervals, different rhythm | 3 | 93.477 | 12/12 resolved/rendered |
| TRIAD-06 | same rhythm, different melody | not returned | — | no target to render |

The global x2 case retained rank and rhythm score (95.208); its small final-score difference comes from other reported components. The local rhythm/rest mismatch and the same-interval negative control both lowered the target ranking by about 1.65 and rhythm from 95.208 to 85.413. The altered-melody negative control did not return the source in Top100.

## Evidence and limits for Sol

- Evidence only: no rule change is implied. The source has edition duplicates above it, so stream rank 3 is not a title-level failure claim.
- Potential general issue to investigate only if a broader independent suite repeats it: changing the Query’s global duration scale preserves retrieval rank but changes non-rhythm reported components (meter/structural/skeleton). This triad does not identify the cause or establish that it is undesirable.
- Negative controls are limited to one actual source and one deterministic mutation each. They show discrimination for this passage, not a universal false-positive or false-negative rate.
- Rendering audit verifies XML target resolution and rendered SVG IDs only; it does not establish human visual quality or listening equivalence.

The prior `small-regression-triad-v1` and `-retry` directories are failed evaluator diagnostics (undefined source-identity lookup), not evidence. The final directory above is the only result set used here.
