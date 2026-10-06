# 경계 독립 반복 탐색
사례 S-STRUCT-004 · partial · seed검사 2300 · 정렬 300
음가/쉼 치환 관찰 131건(겹친 창 중복 포함, 독립 occurrence 수 아님)
기존 Phrase 경계를 입력하지 않았다. 운영 경계/UI 변경 없음. 창 끝은 Motif 또는 Phrase 종결이 아니다.
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-34: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-34: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5
- work-b4fdcba72f89a969-15 ↔ work-b4fdcba72f89a969-42: 2.5+쉼1 → 1.5+쉼2, 다음 attack 간격 3.5
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-34: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5
- work-b4fdcba72f89a969-15 ↔ work-b4fdcba72f89a969-42: 2.5+쉼1 → 1.5+쉼2, 다음 attack 간격 3.5
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-34: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-34: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5
- work-b4fdcba72f89a969-15 ↔ work-b4fdcba72f89a969-42: 2.5+쉼1 → 1.5+쉼2, 다음 attack 간격 3.5
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-34: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5
- work-b4fdcba72f89a969-15 ↔ work-b4fdcba72f89a969-42: 2.5+쉼1 → 1.5+쉼2, 다음 attack 간격 3.5
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-34: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-34: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5
- work-b4fdcba72f89a969-15 ↔ work-b4fdcba72f89a969-42: 2.5+쉼1 → 1.5+쉼2, 다음 attack 간격 3.5
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-34: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5
- work-b4fdcba72f89a969-15 ↔ work-b4fdcba72f89a969-42: 2.5+쉼1 → 1.5+쉼2, 다음 attack 간격 3.5
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-145: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-145: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-145: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-145: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5
- work-b4fdcba72f89a969-7 ↔ work-b4fdcba72f89a969-145: 3.5+쉼1 → 2.5+쉼2, 다음 attack 간격 4.5

## 구간 후보 정리: 300개 창 → 111개 포함관계 그룹
동일 모티프 가족의 개수가 아니다. 시작 준비부/화성 완결성은 미확정. 다음 표는 앞10개 그룹의 종결 후보이다.
| 시작 index쌍 | 원래 창 수 | 끝 exclusive index쌍 | 상태 |
|---|---:|---|---|
| 0/35 | 15 | 8/43 | review-candidate |
| 0/138 | 17 | 8/146 | review-candidate |
| 0/138 | 17 | 16/154 | blocked-by-protected-interior |
| 0/146 | 15 | 8/154 | review-candidate |

## 가변 범위 리뷰
정렬 500 · partial · 후보 12개. 후보 수는 독립 등장 수가 아니다. 운영 변경 없음.