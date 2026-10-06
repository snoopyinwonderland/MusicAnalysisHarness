# 50개 paired 멜로디 변형 검색

음가: 4분음표=1. 순위는 source 회수 진단이지 음악적 정답 판정이 아니다. JSON에 전체 Query/문맥/검색 결과를 보존했다. 실제 SVG 강조와 상위 후보의 음악적 정당성은 사람 검토가 필요하다.

| 사례 | 유형 / 변형 | Query | 순위 | 시간 | 문제·개선 |
|---|---|---|---|---|---|
| PC50-f5a289189313 | repeated-note / source | C#5(0.25) D5(2) Rest(1.5) B4(0.5) B4(1) B4(1) B4(0.5) C#5(1) C#5(2.5) | 1 | 5.33s |  |
| PC50-90f14c42ad6d | repeated-note / transpose-2 | D#5(0.25) E5(2) Rest(1.5) C#5(0.5) C#5(1) C#5(1) C#5(0.5) D#5(1) D#5(2.5) | 1 | 3.14s |  |
| PC50-57eec2840de6 | repeated-note / transpose-octave | C#6(0.25) D6(2) Rest(1.5) B5(0.5) B5(1) B5(1) B5(0.5) C#6(1) C#6(2.5) | 1 | 2.92s |  |
| PC50-1055ab692f5c | repeated-note / one-note-octave | C#5(0.25) D5(2) Rest(1.5) B4(0.5) B5(1) B4(1) B4(0.5) C#5(1) C#5(2.5) | 8 | 9.01s | Original source below rank 5; higher candidates require musical review; Review competing passages; do not force source rank |
| PC50-d1e03901f158 | repeated-note / one-semitone | C#5(0.25) D5(2) Rest(1.5) B4(0.5) C5(1) B4(1) B4(0.5) C#5(1) C#5(2.5) | 미회수/실패 | 7.40s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-9d54431b228d | repeated-note / two-pitches | C#5(0.25) D5(2) Rest(1.5) C5(0.5) B4(1) B4(1) A4(0.5) C#5(1) C#5(2.5) | 미회수/실패 | 19.06s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-908c82beb746 | repeated-note / tempo-double | C#5(0.5) D5(4) Rest(3) B4(1) B4(2) B4(2) B4(1) C#5(2) C#5(5) | 1 | 3.66s |  |
| PC50-277bca0124a9 | repeated-note / local-duration | C#5(0.25) D5(2) Rest(1.5) B4(0.5) B4(1.5) B4(1) B4(0.5) C#5(1) C#5(2.5) | 1 | 4.33s |  |
| PC50-c003cc7fbcd1 | repeated-note / insert-rest | C#5(0.25) D5(2) Rest(1.5) B4(0.5) B4(1) Rest(0.5) B4(1) B4(0.5) C#5(1) C#5(2.5) | 1 | 3.51s |  |
| PC50-904b401ff219 | repeated-note / delete-inner-note | C#5(0.25) D5(2) Rest(1.5) B4(0.5) B4(1) B4(0.5) C#5(1) C#5(2.5) | 미회수/실패 | 4.39s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-63107c35162f | stepwise / source | D4(1) C4(0.5) A#3(2.5) A3(0.5) A#3(0.5) A3(0.5) G3(4) F3(1.5) | 1 | 21.26s |  |
| PC50-96e518ee5fed | stepwise / transpose-2 | E4(1) D4(0.5) C4(2.5) B3(0.5) C4(0.5) B3(0.5) A3(4) G3(1.5) | 1 | 12.35s |  |
| PC50-935a448ed9f6 | stepwise / transpose-octave | D5(1) C5(0.5) A#4(2.5) A4(0.5) A#4(0.5) A4(0.5) G4(4) F4(1.5) | 1 | 11.80s |  |
| PC50-89703c0df691 | stepwise / one-note-octave | D4(1) C4(0.5) A#3(2.5) A4(0.5) A#3(0.5) A3(0.5) G3(4) F3(1.5) | 미회수/실패 | 28.60s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-16f418fa6c39 | stepwise / one-semitone | D4(1) C4(0.5) A#3(2.5) A#3(0.5) A#3(0.5) A3(0.5) G3(4) F3(1.5) | 미회수/실패 | 39.46s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-7922eaf3c7c0 | stepwise / two-pitches | D4(1) C4(0.5) B3(2.5) A3(0.5) A#3(0.5) G3(0.5) G3(4) F3(1.5) | 미회수/실패 | 43.85s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-89175a489b00 | stepwise / tempo-double | D4(2) C4(1) A#3(5) A3(1) A#3(1) A3(1) G3(8) F3(3) | 1 | 12.53s |  |
| PC50-c348dbdfbece | stepwise / local-duration | D4(1) C4(0.5) A#3(2.5) A3(0.75) A#3(0.5) A3(0.5) G3(4) F3(1.5) | 13 | 16.36s | Original source below rank 5; higher candidates require musical review; Review competing passages; do not force source rank |
| PC50-534d1d0f39c9 | stepwise / insert-rest | D4(1) C4(0.5) A#3(2.5) A3(0.5) Rest(0.5) A#3(0.5) A3(0.5) G3(4) F3(1.5) | 2 | 13.97s |  |
| PC50-9ef1da7d1db4 | stepwise / delete-inner-note | D4(1) C4(0.5) A#3(2.5) A#3(0.5) A3(0.5) G3(4) F3(1.5) | 미회수/실패 | 6.12s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-8c8e9b176561 | arpeggio-like / source | D4(5.5) Rest(24.5) A#3(0.5) D#4(4) C4(2) F4(0.75) G4(0.75) A4(0.5) F4(2) | 1 | 17.17s |  |
| PC50-550e4132a8e2 | arpeggio-like / transpose-2 | E4(5.5) Rest(24.5) C4(0.5) F4(4) D4(2) G4(0.75) A4(0.75) B4(0.5) G4(2) | 1 | 3.88s |  |
| PC50-0d53df9ae9fc | arpeggio-like / transpose-octave | D5(5.5) Rest(24.5) A#4(0.5) D#5(4) C5(2) F5(0.75) G5(0.75) A5(0.5) F5(2) | 1 | 3.99s |  |
| PC50-f966a6bcebd2 | arpeggio-like / one-note-octave | D4(5.5) Rest(24.5) A#3(0.5) D#4(4) C5(2) F4(0.75) G4(0.75) A4(0.5) F4(2) | 미회수/실패 | 30.66s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-9e07923d55f0 | arpeggio-like / one-semitone | D4(5.5) Rest(24.5) A#3(0.5) D#4(4) C#4(2) F4(0.75) G4(0.75) A4(0.5) F4(2) | 미회수/실패 | 31.79s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-697720a79d70 | arpeggio-like / two-pitches | D4(5.5) Rest(24.5) A#3(0.5) E4(4) C4(2) F4(0.75) F4(0.75) A4(0.5) F4(2) | 미회수/실패 | 47.16s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-3248b6b41826 | arpeggio-like / tempo-double | D4(11) Rest(49) A#3(1) D#4(8) C4(4) F4(1.5) G4(1.5) A4(1) F4(4) | 1 | 6.28s |  |
| PC50-5847a541ad41 | arpeggio-like / local-duration | D4(5.5) Rest(24.5) A#3(0.5) D#4(4) C4(3) F4(0.75) G4(0.75) A4(0.5) F4(2) | 1 | 6.66s |  |
| PC50-fd99f6b158af | arpeggio-like / insert-rest | D4(5.5) Rest(24.5) A#3(0.5) D#4(4) C4(2) Rest(0.5) F4(0.75) G4(0.75) A4(0.5) F4(2) | 1 | 3.84s |  |
| PC50-4faab6c1156c | arpeggio-like / delete-inner-note | D4(5.5) Rest(24.5) A#3(0.5) D#4(4) F4(0.75) G4(0.75) A4(0.5) F4(2) | 미회수/실패 | 13.20s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-747973000139 | repeated-note / source | G4(0.140625) A4(0.14453125) A#4(0.14453125) Rest(3) C5(0.75) C5(0.25) Rest(0.5) C5(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5) | 1 | 29.68s |  |
| PC50-ea0723143a58 | repeated-note / transpose-2 | A4(0.140625) B4(0.14453125) C5(0.14453125) Rest(3) D5(0.75) D5(0.25) Rest(0.5) D5(0.5) Rest(0.25) D5(0.25) Rest(0.5) D5(0.5) | 1 | 5.49s |  |
| PC50-e08612dccb8c | repeated-note / transpose-octave | G5(0.140625) A5(0.14453125) A#5(0.14453125) Rest(3) C6(0.75) C6(0.25) Rest(0.5) C6(0.5) Rest(0.25) C6(0.25) Rest(0.5) C6(0.5) | 1 | 5.36s |  |
| PC50-146251218b53 | repeated-note / one-note-octave | G4(0.140625) A4(0.14453125) A#4(0.14453125) Rest(3) C6(0.75) C5(0.25) Rest(0.5) C5(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5) | 미회수/실패 | 40.54s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-ece2d9cd04c3 | repeated-note / one-semitone | G4(0.140625) A4(0.14453125) A#4(0.14453125) Rest(3) C#5(0.75) C5(0.25) Rest(0.5) C5(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5) | 미회수/실패 | 37.95s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-34567e3663ab | repeated-note / two-pitches | G4(0.140625) A4(0.14453125) B4(0.14453125) Rest(3) C5(0.75) C5(0.25) Rest(0.5) A#4(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5) | 미회수/실패 | 57.42s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-46259de03746 | repeated-note / tempo-double | G4(0.28125) A4(0.2890625) A#4(0.2890625) Rest(6) C5(1.5) C5(0.5) Rest(1) C5(1) Rest(0.5) C5(0.5) Rest(1) C5(1) | 1 | 6.10s |  |
| PC50-300cc5b24495 | repeated-note / local-duration | G4(0.140625) A4(0.14453125) A#4(0.14453125) Rest(3) C5(1.125) C5(0.25) Rest(0.5) C5(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5) | 1 | 5.60s |  |
| PC50-084d31c14f25 | repeated-note / insert-rest | G4(0.140625) A4(0.14453125) A#4(0.14453125) Rest(3) C5(0.75) Rest(0.5) C5(0.25) Rest(0.5) C5(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5) | 1 | 5.69s |  |
| PC50-4fb5315aaaea | repeated-note / delete-inner-note | G4(0.140625) A4(0.14453125) A#4(0.14453125) Rest(3) C5(0.25) Rest(0.5) C5(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5) | 1 | 2.57s |  |
| PC50-0e009bede7f9 | arpeggio-like / source | A4(0.25) A#4(0.5) C5(0.5) A4(2) C5(1) G4(0.5) C5(0.5) A4(1) | 1 | 57.81s |  |
| PC50-f14147794203 | arpeggio-like / transpose-2 | B4(0.25) C5(0.5) D5(0.5) B4(2) D5(1) A4(0.5) D5(0.5) B4(1) | 1 | 7.07s |  |
| PC50-3083c38e3da6 | arpeggio-like / transpose-octave | A5(0.25) A#5(0.5) C6(0.5) A5(2) C6(1) G5(0.5) C6(0.5) A5(1) | 1 | 6.83s |  |
| PC50-3d78e9f095b3 | arpeggio-like / one-note-octave | A4(0.25) A#4(0.5) C5(0.5) A5(2) C5(1) G4(0.5) C5(0.5) A4(1) | 미회수/실패 | 40.28s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-b328cadd7e6c | arpeggio-like / one-semitone | A4(0.25) A#4(0.5) C5(0.5) A#4(2) C5(1) G4(0.5) C5(0.5) A4(1) | 미회수/실패 | 60.39s | Search did not complete; Inspect timeout trace and cold cache before scoring changes |
| PC50-29648b7be293 | arpeggio-like / two-pitches | A4(0.25) A#4(0.5) C#5(0.5) A4(2) C5(1) F4(0.5) C5(0.5) A4(1) | 미회수/실패 | 51.58s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |
| PC50-20a0b2d3406f | arpeggio-like / tempo-double | A4(0.5) A#4(1) C5(1) A4(4) C5(2) G4(1) C5(1) A4(2) | 1 | 11.12s |  |
| PC50-53b50fffa58e | arpeggio-like / local-duration | A4(0.25) A#4(0.5) C5(0.5) A4(3) C5(1) G4(0.5) C5(0.5) A4(1) | 1 | 8.64s |  |
| PC50-02a69f5958e7 | arpeggio-like / insert-rest | A4(0.25) A#4(0.5) C5(0.5) A4(2) Rest(0.5) C5(1) G4(0.5) C5(0.5) A4(1) | 1 | 6.67s |  |
| PC50-1841835880ce | arpeggio-like / delete-inner-note | A4(0.25) A#4(0.5) C5(0.5) C5(1) G4(0.5) C5(0.5) A4(1) | 미회수/실패 | 20.21s | Original source absent within returned results; edition alternatives need review; Inspect retrieval vs reranking before changing thresholds; compare paired source case |