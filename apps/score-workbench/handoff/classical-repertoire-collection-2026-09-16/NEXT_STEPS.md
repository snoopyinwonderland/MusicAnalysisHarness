# Recommended Next Steps

## 1. 새 프로젝트 저장 구조 확정

- `catalog/`: 작곡가·작품 권위 목록.
- `sources/`: 출처와 권리 근거.
- `scores/original/`: 원본 XML/MXL/MIDI.
- `scores/normalized/`: 변환한 MusicXML. 원본을 덮어쓰지 않음.
- `manifests/`: 파일·작품·판본 매핑 JSONL.
- `reports/`: 수집·검증 진행 보고서.

## 2. v4를 실제 작업 원장으로 전환

- `1차 수집` 154곡부터 출처 URL, 권리 상태, 다운로드 상태를 채운다.
- `보유 검증 큐`의 고신뢰 표본 761건부터 원곡/악장/편곡을 수동 확인한다.
- 행 번호 대신 안정적인 `collectionWorkId`를 발급한다.

## 3. 목록 품질 확장

- S급 작곡가의 Complete Catalogue 출처를 작곡가별 권위 카탈로그로 교체한다.
- 작품 연도와 카탈로그 번호를 권위 출처로 검증한다.
- Open Opus에서 누락된 작곡가와 비서구권·여성 작곡가 목록을 검토한다.
- 오페라 전곡/발췌곡, 모음곡/원전, 교향곡/악장, 원곡/편곡 관계를 명시적으로 모델링한다.

## 4. MusicSearch 연동

- 일정 단위(예: 검증 완료 100곡)마다 XML+manifest 묶음을 MusicSearch에 전달한다.
- MusicSearch가 반환한 workId/streamId와 파싱·렌더링 결과를 원장에 기록한다.
- DB 재대조는 대량 등록 후 또는 정기 릴리스 시 수행하고, 일별 수집마다 전체 대조하지 않는다.

## 5. 첫 번째 완료 기준

- 154곡 모두 출처·권리·XML 품질 상태가 빈칸 없이 기록됨.
- 공개 가능/내부 검색 전용/보류가 구분됨.
- MusicSearch에 전달한 파일은 원본 SHA-256과 workId가 연결됨.
- 5,252건 검증 큐 중 고신뢰 761건 수동 검증 완료.

