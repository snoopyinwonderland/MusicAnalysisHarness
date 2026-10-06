# Classical Repertoire Collection — Project Handoff

이 폴더는 MUSICANOTE의 클래식 레퍼토리 목록·수집·보유 검증 업무를 MusicSearch 개발에서 분리하기 위한 인수인계 패키지다.

## 현재 기준 산출물

- `workbook/classical-repertoire-priority-v4.xlsx`: 최신 업무용 스프레드시트. 15개 시트, 작곡가 220명, 작품 14,027개.
- `data/classical-repertoire-coverage-2026-09-08.json`: MusicSearch DB와 작품 목록의 자동 대조 결과.
- `data/classical-repertoire-validation-2026-09-08.json`: 보유 검증 큐와 1차 수집 큐의 원자료.
- `scripts/`: 최초 목록 생성, 목록 확장, DB 대조, 검증 큐 생성, XLSX 반영 및 최종 검증 스크립트.

`classical-repertoire-priority-v4.xlsx`가 사람이 계속 편집할 기준 파일이다. v1–v3은 이관하지 않았다. 과거 단계는 Git 저장소의 이력과 `HISTORY_AND_DECISIONS.md`로 추적한다.

## 현재 수량

| 항목 | 수량 |
|---|---:|
| 작곡가 | 220명 |
| 작품 | 14,027개 |
| 자동 보유 | 1,520개 |
| 부분 보유 | 215개 |
| 검토 필요 | 3,520개 |
| 미보유 | 8,772개 |
| 보유 검증 큐 | 5,252건 |
| 1차 수집 | 46명·154곡 |

자동 판정은 최종 확정이 아니다. 동일 작품·악장·편곡·판본 관계와 권리 상태는 사람이 검증해야 한다.

## 새 프로젝트의 첫 작업

1. 이 폴더 전체를 새 프로젝트로 복사한다.
2. `workbook/classical-repertoire-priority-v4.xlsx`를 열어 `1차 수집`과 `보유 검증 큐` 시트를 확인한다.
3. 새 프로젝트의 데이터 저장 위치, 원본 XML 저장 규칙, 작품/판본 ID 정책을 먼저 정한다.
4. MusicSearch의 최신 검색 DB와 다시 대조할 때만 `REPRODUCIBILITY.md`의 coverage/validation 파이프라인을 실행한다.
5. 수집한 XML을 MusicSearch에 전달할 때는 원본 파일과 검증된 메타데이터 매핑을 함께 전달한다. 검색 색인 생성은 MusicSearch 프로젝트의 책임으로 둔다.

## 책임 경계

- 새 프로젝트: 레퍼토리 범위, 작곡가/작품 권위 목록, 출처·권리·판본 검증, XML 수집 상태 관리.
- MusicSearch: 전달받은 XML 파싱, 검색 색인 생성, 검색·렌더링 품질, 접근 정책 집행.
- 두 프로젝트 사이의 계약: 작품 식별자, 작곡가, 작품명, 카탈로그 번호, 악장/편곡/판본 관계, 출처 URL, 권리 상태, XML 품질.

## 반드시 읽을 문서

1. `CURRENT_STATUS.md`
2. `DATA_CONTRACT.md`
3. `REPRODUCIBILITY.md`
4. `HISTORY_AND_DECISIONS.md`
5. `NEXT_STEPS.md`

