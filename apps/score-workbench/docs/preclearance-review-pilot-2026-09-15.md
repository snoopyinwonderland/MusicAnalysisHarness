# 유형별 사전검토 Query 파일럿

음가 단위는 4분음표=1. 원본 순위는 top 20 안의 해당 source 회수 진단이며 정답 순위 라벨이 아니다. 전체 악보/강조 표시는 검증하지 않았다.

유형별 생성: {"repeated-note":3,"stepwise":3,"arpeggio-like":3,"mixed-leaps":3}. 실행 4개, 미실행 8개.

| 사례 | 유형 / 변형 | Query | 원본 순위 | 상태 |
|---|---|---|---|---|
| PC-REVIEW-22c02b91adea | repeated-note / source | C#5(0.25) D5(2) Rest(1.5) B4(0.5) B4(1) B4(1) B4(0.5) C#5(1) C#5(2.5) | — | failed |
| PC-REVIEW-280fa74f341a | stepwise / source | D4(1) C4(0.5) Bb3(2.5) A3(0.5) Bb3(0.5) A3(0.5) G3(4) F3(1.5) | — | failed |
| PC-REVIEW-a0cdb6427caa | arpeggio-like / source | D4(5.5) Rest(24.5) Bb3(0.5) Eb4(4) C4(2) F4(0.75) G4(0.75) A4(0.5) F4(2) | — | failed |
| PC-REVIEW-1cea256a4b6a | mixed-leaps / source | B4(0.5) B4(1) B4(1) B4(0.5) E5(1) C#5(1.5) Rest(4.5) A4(0.5) F#5(4) | 3 | completed |
| PC-REVIEW-7602f2952e54 | repeated-note / single-semitone | G4(0.140625) A4(0.14453125) Bb4(0.14453125) Rest(3) C5(0.75) C#5(0.25) Rest(0.5) C5(0.5) Rest(0.25) C5(0.25) Rest(0.5) C5(0.5) | — | not-executed |
| PC-REVIEW-f82fb8cfc0e7 | stepwise / single-semitone | C4(0.140625) D4(0.14453125) E4(0.140625) F4(0.14453125) G#4(0.140625) A4(0.14453125) Bb4(0.14453125) Rest(3) C5(0.75) | — | not-executed |
| PC-REVIEW-879fb6a48c63 | arpeggio-like / single-semitone | A4(0.25) Bb4(0.5) C5(0.5) A4(2) C#5(1) G4(0.5) C5(0.5) A4(1) | — | not-executed |
| PC-REVIEW-02b757f45f8a | mixed-leaps / single-semitone | C5(0.5) C4(0.25) C4(0.25) C4(0.25) C#4(0.5) Bb3(0.25) A3(0.25) Bb3(0.5) | — | not-executed |
| PC-REVIEW-dcf01e0a5982 | repeated-note / octave-transposition | E6(0.5) F6(0.5) E6(0.5) C6(4) Rest(2.5) C6(0.5) C6(0.33203125) C6(0.33203125) C6(0.3359375) | — | not-executed |
| PC-REVIEW-6f3eb0fdb245 | stepwise / octave-transposition | D5(0.140625) E5(0.14453125) F#5(0.140625) G5(0.14453125) A5(0.140625) B5(0.14453125) C6(0.14453125) D6(1) | — | not-executed |
| PC-REVIEW-7433d5c8d303 | arpeggio-like / octave-transposition | F#5(0.5) A5(1.25) F#5(0.25) A5(0.25) B5(1.75) Rest(0.5) D6(0.25) D6(0.25) F#6(0.5) | — | not-executed |
| PC-REVIEW-fbb26911f4de | mixed-leaps / octave-transposition | C6(1) B5(1) C6(2) A5(1) B5(0.5) C6(0.5) D6(1) G5(1) | — | not-executed |

## 검토 항목

각 사례의 suite.json humanReview 필드에 검토자, 원본이 회수되어야 하는 이유, 선호 후보 ID, 순위 이유, 음악적 기능을 별도 복사본으로 기록한다. 원본 측정 결과를 덮어쓰지 않는다. 자동 분류는 모티프/화성 분석 확정이 아니다.

## 출처와 한계

선별 모집단은 이전 한 업로드 검색의 후보 스냅샷이다. 유형당 작품 다양성은 보강했지만 전체 corpus를 대표하지 않는다. 원형·반음 수정·옥타브 이동은 서로 다른 구간에 적용되어 완전한 paired A/B가 아니다. 본 파일럿의 목적은 Harness 동작과 문제 발견이다.

[전체 Query·문맥·사람 검토 필드](../evaluation/runs/preclearance-review-diverse-2026-09-15/suite.json)

## 실패/미회수 확인

- PC-REVIEW-22c02b91adea: Search timed out after 60000ms
- PC-REVIEW-280fa74f341a: Search timed out after 60000ms
- PC-REVIEW-a0cdb6427caa: Search timed out after 60000ms
