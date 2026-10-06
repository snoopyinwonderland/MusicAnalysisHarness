# 개발 후 멜로디 변형 50개 — 결과와 검토 자료

완료 49/50, 원본 source 회수 32/50, 1위 29/50, 상위 5개 30/50. 중앙 9.01초, p95 51.58초.

5개 원본 구간 × 10개 변형의 paired 테스트다. 데이터베이스 전체의 대표 표본이나 저작권 침해 정답 집합은 아니다. 원본 미회수는 다른 판본 회수 여부와 음악적 타당성을 추가 검토해야 한다. 전체 Query와 검색 결과는 사례 JSON 및 원 실행 경로에 보존한다.

| 유형 | 실행 | source 회수 | 1위 | top 5 |
|---|---:|---:|---:|---:|
| source | 5/5 | 5 | 5 | 5 |
| transpose-2 | 5/5 | 5 | 5 | 5 |
| transpose-octave | 5/5 | 5 | 5 | 5 |
| one-note-octave | 5/5 | 1 | 0 | 0 |
| one-semitone | 4/5 | 0 | 0 | 0 |
| two-pitches | 5/5 | 0 | 0 | 0 |
| tempo-double | 5/5 | 5 | 5 | 5 |
| local-duration | 5/5 | 5 | 4 | 4 |
| insert-rest | 5/5 | 5 | 4 | 5 |
| delete-inner-note | 5/5 | 1 | 1 | 1 |

## 발견한 문제와 후속 검증 방향

- 원형/전조/전체 음가 변경이 안정적인지 먼저 보고, 개별 음 변경·옥타브 변경·삭제에서 회수가 무너지는지를 paired 비교한다.
- 같은 음 반복·음정 종류가 적은 구간은 작은 변경도 정보량과 후보 생성에 큰 영향을 줄 수 있다. 검색 후보 단계와 최종 순위 단계를 분리 진단한다.
- 원본이 순위에서 밀렸다는 것만으로 오류라고 확정하지 않는다. 상위 결과의 실제 선율·리듬·연속성·내성부 여부를 검토한다.
- API 참조 검증은 실제 SVG 전체의 강조/배치 검증이 아니다. 시각적 판정과 상위 결과의 음악적 정당성은 미검토로 남긴다.
- 아래 개선안은 후속 실험 후보이며 이번 결과에 맞춰 production 순위를 개별 조정하지 않았다.

## PC50-f5a289189313 — repeated-note / source

원본: 3. Endless Love, Violin and Piano Duet.musicxml.xml · P1:1:1 · 5–7마디

Query: C#5(0.25) D5(2) Rest(1.5) B4(0.5) B4(1) B4(1) B4(0.5) C#5(1) C#5(2.5)

상태: completed · 원본 순위 1 · 시간 5.33초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P1:1:1 | 99.00 | 5–7 |
| 2 | ENDLESS LOVE / P1:1:1 | 99.00 | 5–7 |
| 3 | ENDLESS LOVE / P2:1:1 | 92.33 | 35–37 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-90f14c42ad6d — repeated-note / transpose-2

원본: 3. Endless Love, Violin and Piano Duet.musicxml.xml · P1:1:1 · 5–7마디

Query: D#5(0.25) E5(2) Rest(1.5) C#5(0.5) C#5(1) C#5(1) C#5(0.5) D#5(1) D#5(2.5)

상태: completed · 원본 순위 1 · 시간 3.14초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P1:1:1 | 99.00 | 5–7 |
| 2 | ENDLESS LOVE / P1:1:1 | 99.00 | 5–7 |
| 3 | ENDLESS LOVE / P2:1:1 | 92.33 | 35–37 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-57eec2840de6 — repeated-note / transpose-octave

원본: 3. Endless Love, Violin and Piano Duet.musicxml.xml · P1:1:1 · 5–7마디

Query: C#6(0.25) D6(2) Rest(1.5) B5(0.5) B5(1) B5(1) B5(0.5) C#6(1) C#6(2.5)

상태: completed · 원본 순위 1 · 시간 2.92초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P1:1:1 | 99.00 | 5–7 |
| 2 | ENDLESS LOVE / P1:1:1 | 99.00 | 5–7 |
| 3 | ENDLESS LOVE / P2:1:1 | 92.33 | 35–37 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-1055ab692f5c — repeated-note / one-note-octave

원본: 3. Endless Love, Violin and Piano Duet.musicxml.xml · P1:1:1 · 5–7마디

Query: C#5(0.25) D5(2) Rest(1.5) B4(0.5) B5(1) B4(1) B4(0.5) C#5(1) C#5(2.5)

상태: completed · 원본 순위 8 · 시간 9.01초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P1:1:1 | 74.58 | 5–7 |
| 2 | ENDLESS LOVE / P1:1:1 | 74.58 | 5–7 |
| 3 | Tarantella / P1:1:1 | 74.20 | 30–31 |

관찰: Original source below rank 5; higher candidates require musical review
개선 후보: Review competing passages; do not force source rank

## PC50-d1e03901f158 — repeated-note / one-semitone

원본: 3. Endless Love, Violin and Piano Duet.musicxml.xml · P1:1:1 · 5–7마디

Query: C#5(0.25) D5(2) Rest(1.5) B4(0.5) C5(1) B4(1) B4(0.5) C#5(1) C#5(2.5)

상태: completed · 원본 순위 미회수 · 시간 7.40초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | SHOW YOURSELF / P2:1:1 | 100.00 | 59–62 |
| 2 | Amor i parto / P1:1:1 | 91.38 | 33–35 |
| 3 | O ye Christian soldiers as you march along / P2:1:1 | 91.93 | 2–3 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-9d54431b228d — repeated-note / two-pitches

원본: 3. Endless Love, Violin and Piano Duet.musicxml.xml · P1:1:1 · 5–7마디

Query: C#5(0.25) D5(2) Rest(1.5) C5(0.5) B4(1) B4(1) A4(0.5) C#5(1) C#5(2.5)

상태: completed · 원본 순위 미회수 · 시간 19.06초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | Salve Regina / P2:1:1 | 94.97 | 26–31 |
| 2 | Ascribe unto the Lord / P1:1:1 | 97.18 | 213–216 |
| 3 | Litanie della B. V. M. / P3:1:1 | 87.49 | 157–159 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-908c82beb746 — repeated-note / tempo-double

원본: 3. Endless Love, Violin and Piano Duet.musicxml.xml · P1:1:1 · 5–7마디

Query: C#5(0.5) D5(4) Rest(3) B4(1) B4(2) B4(2) B4(1) C#5(2) C#5(5)

상태: completed · 원본 순위 1 · 시간 3.66초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P1:1:1 | 99.00 | 5–7 |
| 2 | ENDLESS LOVE / P1:1:1 | 99.00 | 5–7 |
| 3 | ENDLESS LOVE / P2:1:1 | 92.33 | 35–37 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-277bca0124a9 — repeated-note / local-duration

원본: 3. Endless Love, Violin and Piano Duet.musicxml.xml · P1:1:1 · 5–7마디

Query: C#5(0.25) D5(2) Rest(1.5) B4(0.5) B4(1.5) B4(1) B4(0.5) C#5(1) C#5(2.5)

상태: completed · 원본 순위 1 · 시간 4.33초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P1:1:1 | 98.04 | 5–7 |
| 2 | ENDLESS LOVE / P1:1:1 | 98.04 | 5–7 |
| 3 | ENDLESS LOVE / P1:1:1 | 98.04 | 5–7 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-c003cc7fbcd1 — repeated-note / insert-rest

원본: 3. Endless Love, Violin and Piano Duet.musicxml.xml · P1:1:1 · 5–7마디

Query: C#5(0.25) D5(2) Rest(1.5) B4(0.5) B4(1) Rest(0.5) B4(1) B4(0.5) C#5(1) C#5(2.5)

상태: completed · 원본 순위 1 · 시간 3.51초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P1:1:1 | 98.04 | 5–7 |
| 2 | ENDLESS LOVE / P1:1:1 | 98.04 | 5–7 |
| 3 | ENDLESS LOVE / P1:1:1 | 98.04 | 5–7 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-904b401ff219 — repeated-note / delete-inner-note

원본: 3. Endless Love, Violin and Piano Duet.musicxml.xml · P1:1:1 · 5–7마디

Query: C#5(0.25) D5(2) Rest(1.5) B4(0.5) B4(1) B4(0.5) C#5(1) C#5(2.5)

상태: completed · 원본 순위 미회수 · 시간 4.39초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | 동네 오빠 (Prod. 플레이사운드) / P1:1:1 | 100.00 | 23–25 |
| 2 | 고마워 고마워 / P5:2:5 | 100.00 | 92–95 |
| 3 | HOME;RUN / P1:1:1 | 100.00 | 40–41 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-63107c35162f — stepwise / source

원본: 3. Endless Love, Violin, Cello and Piano Trio.musicxml.xml · P2:1:1 · 55–58마디

Query: D4(1) C4(0.5) A#3(2.5) A3(0.5) A#3(0.5) A3(0.5) G3(4) F3(1.5)

상태: completed · 원본 순위 1 · 시간 21.26초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P2:1:1 | 97.80 | 55–58 |
| 2 | ENDLESS LOVE / P2:1:1 | 97.80 | 55–58 |
| 3 | Custodi me MH 504 - Johann Michael Haydn / P4:1:1 | 96.96 | 19–21 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-96e518ee5fed — stepwise / transpose-2

원본: 3. Endless Love, Violin, Cello and Piano Trio.musicxml.xml · P2:1:1 · 55–58마디

Query: E4(1) D4(0.5) C4(2.5) B3(0.5) C4(0.5) B3(0.5) A3(4) G3(1.5)

상태: completed · 원본 순위 1 · 시간 12.35초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P2:1:1 | 97.80 | 55–58 |
| 2 | ENDLESS LOVE / P2:1:1 | 97.80 | 55–58 |
| 3 | Custodi me MH 504 - Johann Michael Haydn / P4:1:1 | 96.96 | 19–21 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-935a448ed9f6 — stepwise / transpose-octave

원본: 3. Endless Love, Violin, Cello and Piano Trio.musicxml.xml · P2:1:1 · 55–58마디

Query: D5(1) C5(0.5) A#4(2.5) A4(0.5) A#4(0.5) A4(0.5) G4(4) F4(1.5)

상태: completed · 원본 순위 1 · 시간 11.80초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P2:1:1 | 97.80 | 55–58 |
| 2 | ENDLESS LOVE / P2:1:1 | 97.80 | 55–58 |
| 3 | Custodi me MH 504 - Johann Michael Haydn / P4:1:1 | 96.96 | 19–21 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-89703c0df691 — stepwise / one-note-octave

원본: 3. Endless Love, Violin, Cello and Piano Trio.musicxml.xml · P2:1:1 · 55–58마디

Query: D4(1) C4(0.5) A#3(2.5) A4(0.5) A#3(0.5) A3(0.5) G3(4) F3(1.5)

상태: completed · 원본 순위 미회수 · 시간 28.60초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ZERO / P2:1:1 | 86.70 | 78–80 |
| 2 | Messiah HWV 56 / P2:1:2 | 72.97 | 43–43 |
| 3 | 크리스마스니까 / P2:1:1 | 77.82 | 25–27 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-16f418fa6c39 — stepwise / one-semitone

원본: 3. Endless Love, Violin, Cello and Piano Trio.musicxml.xml · P2:1:1 · 55–58마디

Query: D4(1) C4(0.5) A#3(2.5) A#3(0.5) A#3(0.5) A3(0.5) G3(4) F3(1.5)

상태: completed · 원본 순위 미회수 · 시간 39.46초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | Moro e mentre sospiro / P1:1:1 | 99.78 | 68–70 |
| 2 | Perché se m'odiavi / P4:1:1 | 96.01 | 18–21 |
| 3 | Brother James' Air / P1:1:1 | 96.53 | 32–34 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-7922eaf3c7c0 — stepwise / two-pitches

원본: 3. Endless Love, Violin, Cello and Piano Trio.musicxml.xml · P2:1:1 · 55–58마디

Query: D4(1) C4(0.5) B3(2.5) A3(0.5) A#3(0.5) G3(0.5) G3(4) F3(1.5)

상태: completed · 원본 순위 미회수 · 시간 43.85초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | Claros y hermosos ojos / P1:1:1 | 91.84 | 23–25 |
| 2 | Verbum iniquum et dolosum / P4:1:1 | 91.53 | 25–28 |
| 3 | The Goslings / P5:1:1 | 86.58 | 11–13 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-89175a489b00 — stepwise / tempo-double

원본: 3. Endless Love, Violin, Cello and Piano Trio.musicxml.xml · P2:1:1 · 55–58마디

Query: D4(2) C4(1) A#3(5) A3(1) A#3(1) A3(1) G3(8) F3(3)

상태: completed · 원본 순위 1 · 시간 12.53초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P2:1:1 | 97.80 | 55–58 |
| 2 | ENDLESS LOVE / P2:1:1 | 97.80 | 55–58 |
| 3 | Custodi me MH 504 - Johann Michael Haydn / P4:1:1 | 96.96 | 19–21 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-c348dbdfbece — stepwise / local-duration

원본: 3. Endless Love, Violin, Cello and Piano Trio.musicxml.xml · P2:1:1 · 55–58마디

Query: D4(1) C4(0.5) A#3(2.5) A3(0.75) A#3(0.5) A3(0.5) G3(4) F3(1.5)

상태: completed · 원본 순위 13 · 시간 16.36초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | Obsecro Domine / P3:1:1 | 97.69 | 34–36 |
| 2 | Defunctum Charites / P5:1:1 | 96.51 | 59–61 |
| 3 | For this mortal must put on immortality / P1:1:1 | 100.00 | 32–35 |

관찰: Original source below rank 5; higher candidates require musical review
개선 후보: Review competing passages; do not force source rank

## PC50-534d1d0f39c9 — stepwise / insert-rest

원본: 3. Endless Love, Violin, Cello and Piano Trio.musicxml.xml · P2:1:1 · 55–58마디

Query: D4(1) C4(0.5) A#3(2.5) A3(0.5) Rest(0.5) A#3(0.5) A3(0.5) G3(4) F3(1.5)

상태: completed · 원본 순위 2 · 시간 13.97초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | Ode on the Dissolution of Time / P2:1:1 | 97.51 | 38–40 |
| 2 | ENDLESS LOVE / P2:1:1 | 98.04 | 55–58 |
| 3 | ENDLESS LOVE / P2:1:1 | 98.04 | 55–58 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-9ef1da7d1db4 — stepwise / delete-inner-note

원본: 3. Endless Love, Violin, Cello and Piano Trio.musicxml.xml · P2:1:1 · 55–58마디

Query: D4(1) C4(0.5) A#3(2.5) A#3(0.5) A3(0.5) G3(4) F3(1.5)

상태: completed · 원본 순위 미회수 · 시간 6.12초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | THE UNBIRTHDAY SONG / P2:1:1 | 100.00 | 77–78 |
| 2 | THE UNBIRTHDAY SONG / P3:1:1 | 100.00 | 77–78 |
| 3 | AWAY IN A MANGER / P1:1:1 | 98.35 | 18–20 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-8c8e9b176561 — arpeggio-like / source

원본: 3. Endless Love, Violin, Viola, Cello and Piano Quartet.musicxml.xml · P2:1:1 · 37–47마디

Query: D4(5.5) Rest(24.5) A#3(0.5) D#4(4) C4(2) F4(0.75) G4(0.75) A4(0.5) F4(2)

상태: completed · 원본 순위 1 · 시간 17.17초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P2:1:1 | 99.00 | 37–47 |
| 2 | Drink to me only with thine eyes / P2:2:5 | 87.44 | 11–12 |
| 3 | Weihnachtsoratorium BWV 248 / P13:1:1 | 88.01 | 801–802 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-550e4132a8e2 — arpeggio-like / transpose-2

원본: 3. Endless Love, Violin, Viola, Cello and Piano Quartet.musicxml.xml · P2:1:1 · 37–47마디

Query: E4(5.5) Rest(24.5) C4(0.5) F4(4) D4(2) G4(0.75) A4(0.75) B4(0.5) G4(2)

상태: completed · 원본 순위 1 · 시간 3.88초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P2:1:1 | 99.00 | 37–47 |
| 2 | Drink to me only with thine eyes / P2:2:5 | 87.44 | 11–12 |
| 3 | Weihnachtsoratorium BWV 248 / P13:1:1 | 88.01 | 801–802 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-0d53df9ae9fc — arpeggio-like / transpose-octave

원본: 3. Endless Love, Violin, Viola, Cello and Piano Quartet.musicxml.xml · P2:1:1 · 37–47마디

Query: D5(5.5) Rest(24.5) A#4(0.5) D#5(4) C5(2) F5(0.75) G5(0.75) A5(0.5) F5(2)

상태: completed · 원본 순위 1 · 시간 3.99초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P2:1:1 | 99.00 | 37–47 |
| 2 | Drink to me only with thine eyes / P2:2:5 | 87.44 | 11–12 |
| 3 | Weihnachtsoratorium BWV 248 / P13:1:1 | 88.01 | 801–802 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-f966a6bcebd2 — arpeggio-like / one-note-octave

원본: 3. Endless Love, Violin, Viola, Cello and Piano Quartet.musicxml.xml · P2:1:1 · 37–47마디

Query: D4(5.5) Rest(24.5) A#3(0.5) D#4(4) C5(2) F4(0.75) G4(0.75) A4(0.5) F4(2)

상태: completed · 원본 순위 미회수 · 시간 30.66초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | Musikalisches Opfer BWV 1079 / P1:2:5 | 65.79 | 126–128 |
| 2 | The Lady Oriana / P3:1:1 | 66.40 | 67–72 |
| 3 | Sederunt principes MH 343 - Johann Michael Haydn / P6:1:1 | 69.73 | 13–18 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-9e07923d55f0 — arpeggio-like / one-semitone

원본: 3. Endless Love, Violin, Viola, Cello and Piano Quartet.musicxml.xml · P2:1:1 · 37–47마디

Query: D4(5.5) Rest(24.5) A#3(0.5) D#4(4) C#4(2) F4(0.75) G4(0.75) A4(0.5) F4(2)

상태: completed · 원본 순위 미회수 · 시간 31.79초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | My Story / P2:1:1 | 73.41 | 55–55 |
| 2 | Mass for Five Voices / P4:1:1 | 79.48 | 84–85 |
| 3 | Quemadmodum desiderat cervus SWV 336 / P2:1:1 | 64.83 | 154–155 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-697720a79d70 — arpeggio-like / two-pitches

원본: 3. Endless Love, Violin, Viola, Cello and Piano Quartet.musicxml.xml · P2:1:1 · 37–47마디

Query: D4(5.5) Rest(24.5) A#3(0.5) E4(4) C4(2) F4(0.75) F4(0.75) A4(0.5) F4(2)

상태: completed · 원본 순위 미회수 · 시간 47.16초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | Missa solemnis Op.123 / P14:1:1 | 86.87 | 329–330 |
| 2 | Cello Concerto Op.104 / P16:1:1 | 68.76 | 337–344 |
| 3 | Gloria / P3:1:1 | 63.75 | 734–742 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-3248b6b41826 — arpeggio-like / tempo-double

원본: 3. Endless Love, Violin, Viola, Cello and Piano Quartet.musicxml.xml · P2:1:1 · 37–47마디

Query: D4(11) Rest(49) A#3(1) D#4(8) C4(4) F4(1.5) G4(1.5) A4(1) F4(4)

상태: completed · 원본 순위 1 · 시간 6.28초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P2:1:1 | 99.00 | 37–47 |
| 2 | Drink to me only with thine eyes / P2:2:5 | 86.11 | 11–12 |
| 3 | Weihnachtsoratorium BWV 248 / P13:1:1 | 85.67 | 801–802 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-5847a541ad41 — arpeggio-like / local-duration

원본: 3. Endless Love, Violin, Viola, Cello and Piano Quartet.musicxml.xml · P2:1:1 · 37–47마디

Query: D4(5.5) Rest(24.5) A#3(0.5) D#4(4) C4(3) F4(0.75) G4(0.75) A4(0.5) F4(2)

상태: completed · 원본 순위 1 · 시간 6.66초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P2:1:1 | 100.00 | 37–47 |
| 2 | Drink to me only with thine eyes / P2:2:5 | 86.23 | 11–12 |
| 3 | Weihnachtsoratorium BWV 248 / P13:1:1 | 86.03 | 801–802 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-fd99f6b158af — arpeggio-like / insert-rest

원본: 3. Endless Love, Violin, Viola, Cello and Piano Quartet.musicxml.xml · P2:1:1 · 37–47마디

Query: D4(5.5) Rest(24.5) A#3(0.5) D#4(4) C4(2) Rest(0.5) F4(0.75) G4(0.75) A4(0.5) F4(2)

상태: completed · 원본 순위 1 · 시간 3.84초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | ENDLESS LOVE / P2:1:1 | 100.00 | 37–47 |
| 2 | Partita in D major BWV 828 / P1:2:5 | 91.27 | 37–38 |
| 3 | Partita in D major BWV 828 / P1:2:5 | 91.27 | 465–466 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-4faab6c1156c — arpeggio-like / delete-inner-note

원본: 3. Endless Love, Violin, Viola, Cello and Piano Quartet.musicxml.xml · P2:1:1 · 37–47마디

Query: D4(5.5) Rest(24.5) A#3(0.5) D#4(4) F4(0.75) G4(0.75) A4(0.5) F4(2)

상태: completed · 원본 순위 미회수 · 시간 13.20초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | 보글보글 / P2:1:1 | 87.25 | 10–11 |
| 2 | 말도 안 돼 (드라마"개인의 취향") / P2:1:1 | 88.69 | 63–66 |
| 3 | Mass for 6 Voices SV 205 / P3:1:1 | 87.95 | 296–297 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-747973000139 — repeated-note / source

원본: 4. For the First Time in Forever, Violin and Piano Duet.musicxml.xml · P1:1:1 · 0–1마디

Query: G4(0.140625) A4(0.14453125) A#4(0.14453125) Rest(3) C5(0.75) C5(0.25) Rest(0.5) C5(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5)

상태: completed · 원본 순위 1 · 시간 29.68초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 2 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 3 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-ea0723143a58 — repeated-note / transpose-2

원본: 4. For the First Time in Forever, Violin and Piano Duet.musicxml.xml · P1:1:1 · 0–1마디

Query: A4(0.140625) B4(0.14453125) C5(0.14453125) Rest(3) D5(0.75) D5(0.25) Rest(0.5) D5(0.5) Rest(0.25) D5(0.25) Rest(0.5) D5(0.5)

상태: completed · 원본 순위 1 · 시간 5.49초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 2 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 3 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-e08612dccb8c — repeated-note / transpose-octave

원본: 4. For the First Time in Forever, Violin and Piano Duet.musicxml.xml · P1:1:1 · 0–1마디

Query: G5(0.140625) A5(0.14453125) A#5(0.14453125) Rest(3) C6(0.75) C6(0.25) Rest(0.5) C6(0.5) Rest(0.25) C6(0.25) Rest(0.5) C6(0.5)

상태: completed · 원본 순위 1 · 시간 5.36초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 2 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 3 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-146251218b53 — repeated-note / one-note-octave

원본: 4. For the First Time in Forever, Violin and Piano Duet.musicxml.xml · P1:1:1 · 0–1마디

Query: G4(0.140625) A4(0.14453125) A#4(0.14453125) Rest(3) C6(0.75) C5(0.25) Rest(0.5) C5(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5)

상태: completed · 원본 순위 미회수 · 시간 40.54초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | 싸운 날 / P3:1:1 | 98.14 | 22–24 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-ece2d9cd04c3 — repeated-note / one-semitone

원본: 4. For the First Time in Forever, Violin and Piano Duet.musicxml.xml · P1:1:1 · 0–1마디

Query: G4(0.140625) A4(0.14453125) A#4(0.14453125) Rest(3) C#5(0.75) C5(0.25) Rest(0.5) C5(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5)

상태: completed · 원본 순위 미회수 · 시간 37.95초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | 아리아리 / P3:1:1 | 99.58 | 12–13 |
| 2 | Io non sapea / P3:1:1 | 99.00 | 19–21 |
| 3 | 사랑해 사랑해 / P5:1:1 | 92.99 | 42–43 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-34567e3663ab — repeated-note / two-pitches

원본: 4. For the First Time in Forever, Violin and Piano Duet.musicxml.xml · P1:1:1 · 0–1마디

Query: G4(0.140625) A4(0.14453125) B4(0.14453125) Rest(3) C5(0.75) C5(0.25) Rest(0.5) A#4(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5)

상태: completed · 원본 순위 미회수 · 시간 57.42초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | 단 한 사람 / P4:1:1 | 90.92 | 123–125 |
| 2 | Weary Wind of the West / P1:1:1 | 95.70 | 11–14 |
| 3 | 나무 / P1:1:1 | 92.77 | 47–48 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-46259de03746 — repeated-note / tempo-double

원본: 4. For the First Time in Forever, Violin and Piano Duet.musicxml.xml · P1:1:1 · 0–1마디

Query: G4(0.28125) A4(0.2890625) A#4(0.2890625) Rest(6) C5(1.5) C5(0.5) Rest(1) C5(1) Rest(0.5) C5(0.5) Rest(1) C5(1)

상태: completed · 원본 순위 1 · 시간 6.10초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 2 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 3 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-300cc5b24495 — repeated-note / local-duration

원본: 4. For the First Time in Forever, Violin and Piano Duet.musicxml.xml · P1:1:1 · 0–1마디

Query: G4(0.140625) A4(0.14453125) A#4(0.14453125) Rest(3) C5(1.125) C5(0.25) Rest(0.5) C5(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5)

상태: completed · 원본 순위 1 · 시간 5.60초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 2 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 3 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-084d31c14f25 — repeated-note / insert-rest

원본: 4. For the First Time in Forever, Violin and Piano Duet.musicxml.xml · P1:1:1 · 0–1마디

Query: G4(0.140625) A4(0.14453125) A#4(0.14453125) Rest(3) C5(0.75) Rest(0.5) C5(0.25) Rest(0.5) C5(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5)

상태: completed · 원본 순위 1 · 시간 5.69초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 2 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 3 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-4fb5315aaaea — repeated-note / delete-inner-note

원본: 4. For the First Time in Forever, Violin and Piano Duet.musicxml.xml · P1:1:1 · 0–1마디

Query: G4(0.140625) A4(0.14453125) A#4(0.14453125) Rest(3) C5(0.25) Rest(0.5) C5(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5)

상태: completed · 원본 순위 1 · 시간 2.57초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 2 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |
| 3 | FOR THE FIRST TIME IN FOREVER / P1:1:1 | 100.00 | 0–1 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-0e009bede7f9 — arpeggio-like / source

원본: kysing/27004.xml · P2:1:1 · 27–28마디

Query: A4(0.25) A#4(0.5) C5(0.5) A4(2) C5(1) G4(0.5) C5(0.5) A4(1)

상태: completed · 원본 순위 1 · 시간 57.81초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | 아름다운 세상 (영화"알라딘") / P2:1:1 | 97.80 | 27–28 |
| 2 | Take Me / P2:1:1 | 100.00 | 34–37 |
| 3 | Quartet KV 285b / P3:1:1 | 89.94 | 14–16 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-f14147794203 — arpeggio-like / transpose-2

원본: kysing/27004.xml · P2:1:1 · 27–28마디

Query: B4(0.25) C5(0.5) D5(0.5) B4(2) D5(1) A4(0.5) D5(0.5) B4(1)

상태: completed · 원본 순위 1 · 시간 7.07초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | 아름다운 세상 (영화"알라딘") / P2:1:1 | 97.80 | 27–28 |
| 2 | Take Me / P2:1:1 | 100.00 | 34–37 |
| 3 | Quartet KV 285b / P3:1:1 | 89.94 | 14–16 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-3083c38e3da6 — arpeggio-like / transpose-octave

원본: kysing/27004.xml · P2:1:1 · 27–28마디

Query: A5(0.25) A#5(0.5) C6(0.5) A5(2) C6(1) G5(0.5) C6(0.5) A5(1)

상태: completed · 원본 순위 1 · 시간 6.83초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | 아름다운 세상 (영화"알라딘") / P2:1:1 | 97.80 | 27–28 |
| 2 | Take Me / P2:1:1 | 100.00 | 34–37 |
| 3 | Quartet KV 285b / P3:1:1 | 89.94 | 14–16 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-3d78e9f095b3 — arpeggio-like / one-note-octave

원본: kysing/27004.xml · P2:1:1 · 27–28마디

Query: A4(0.25) A#4(0.5) C5(0.5) A5(2) C5(1) G4(0.5) C5(0.5) A4(1)

상태: completed · 원본 순위 미회수 · 시간 40.28초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | Götterdämmerung WWV 86D / P23:1:1 | 85.67 | 63–63 |
| 2 | Happening / P3:1:1 | 80.57 | 7–8 |
| 3 | Beethoven Ludwig van 5 6 Piano Sonata No.29 in B-flat major op.106 1st / P1:2:5 | 75.53 | 348–349 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-b328cadd7e6c — arpeggio-like / one-semitone

원본: kysing/27004.xml · P2:1:1 · 27–28마디

Query: A4(0.25) A#4(0.5) C5(0.5) A#4(2) C5(1) G4(0.5) C5(0.5) A4(1)

상태: failed · 원본 순위 미회수 · 시간 60.39초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|

관찰: Search did not complete
개선 후보: Inspect timeout trace and cold cache before scoring changes

## PC50-29648b7be293 — arpeggio-like / two-pitches

원본: kysing/27004.xml · P2:1:1 · 27–28마디

Query: A4(0.25) A#4(0.5) C#5(0.5) A4(2) C5(1) F4(0.5) C5(0.5) A4(1)

상태: completed · 원본 순위 미회수 · 시간 51.58초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | 이 마음이 찾아오면 / P2:1:1 | 96.23 | 39–41 |
| 2 | Etude op.849 / P1:2:5 | 93.76 | 24–26 |
| 3 | Valley of Lies (Feat.iann dior) / P1:1:1 | 82.88 | 25–28 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case

## PC50-20a0b2d3406f — arpeggio-like / tempo-double

원본: kysing/27004.xml · P2:1:1 · 27–28마디

Query: A4(0.5) A#4(1) C5(1) A4(4) C5(2) G4(1) C5(1) A4(2)

상태: completed · 원본 순위 1 · 시간 11.12초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | 아름다운 세상 (영화"알라딘") / P2:1:1 | 97.80 | 27–28 |
| 2 | Take Me / P2:1:1 | 100.00 | 34–37 |
| 3 | Quartet KV 285b / P3:1:1 | 89.94 | 14–16 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-53b50fffa58e — arpeggio-like / local-duration

원본: kysing/27004.xml · P2:1:1 · 27–28마디

Query: A4(0.25) A#4(0.5) C5(0.5) A4(3) C5(1) G4(0.5) C5(0.5) A4(1)

상태: completed · 원본 순위 1 · 시간 8.64초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | 아름다운 세상 (영화"알라딘") / P2:1:1 | 94.64 | 27–28 |
| 2 | Take Me / P2:1:1 | 100.00 | 34–37 |
| 3 | Quartet KV 285b / P3:1:1 | 87.49 | 14–16 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-02a69f5958e7 — arpeggio-like / insert-rest

원본: kysing/27004.xml · P2:1:1 · 27–28마디

Query: A4(0.25) A#4(0.5) C5(0.5) A4(2) Rest(0.5) C5(1) G4(0.5) C5(0.5) A4(1)

상태: completed · 원본 순위 1 · 시간 6.67초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | 아름다운 세상 (영화"알라딘") / P2:1:1 | 97.46 | 27–28 |
| 2 | Take Me / P2:1:1 | 100.00 | 34–37 |
| 3 | Hyde / P3:1:1 | 94.35 | 87–89 |

관찰: 자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.
개선 후보: 현재 결과 보존 후 전문가 비교.

## PC50-1841835880ce — arpeggio-like / delete-inner-note

원본: kysing/27004.xml · P2:1:1 · 27–28마디

Query: A4(0.25) A#4(0.5) C5(0.5) C5(1) G4(0.5) C5(0.5) A4(1)

상태: completed · 원본 순위 미회수 · 시간 20.21초

| 순위 | 결과 | 유사도 | 마디 |
|---|---|---:|---|
| 1 | Al mormorio sedean / P1:1:1 | 100.00 | 46–48 |
| 2 | Chorale harmoinisations (Nos. 121-240 in Breitkopf edition) / P1:2:5 | 97.07 | 0–0 |
| 3 | Chorale / P1:2:5 | 97.07 | 0–0 |

관찰: Original source absent within returned results; edition alternatives need review
개선 후보: Inspect retrieval vs reranking before changing thresholds; compare paired source case
