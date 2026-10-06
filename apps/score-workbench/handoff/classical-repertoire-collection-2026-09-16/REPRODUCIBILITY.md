# Reproducibility

## 런타임

- Node.js 20 이상.
- Python 3.11 이상과 `openpyxl`.
- XLSX 생성·렌더링에는 Codex 번들 `@oai/artifact-tool`을 사용했다. 새 프로젝트에서 사용할 수 없다면 기존 XLSX를 기준 파일로 유지하고, 스크립트 교체 시 값·수식·데이터 유효성·조건부 서식·시트 수를 다시 검증한다.
- Open Opus API 접근은 초기 목록을 재생성할 때만 필요하다.

## 파이프라인

Node 스크립트는 `@oai/artifact-tool`을 해석할 수 있는 Codex 번들 런타임 또는 해당 패키지가 설치된 작업 디렉터리에서 실행해야 한다. 단순히 이 폴더에서 일반 Node를 실행하면 `ERR_MODULE_NOT_FOUND`가 발생할 수 있다. 이는 XLSX 오류가 아니라 런타임 의존성 오류다.

아래 경로는 이 인수인계 폴더를 현재 디렉터리로 가정한 예다. `<search.sqlite>`는 MusicSearch의 최신 `data/search-index-v2/search.sqlite`로 교체한다.

```text
1. 최초 목록 생성
node scripts/build-classical-repertoire-workbook.mjs <output.xlsx> <preview-dir>

2. 보완 목록 추가
node scripts/extend-classical-repertoire-workbook.mjs <source.xlsx> <output.xlsx> <preview-dir>

3. 최신 검색 DB와 자동 대조
python scripts/build-classical-coverage.py <source.xlsx> <search.sqlite> <coverage.json>

4. 대조 결과를 XLSX에 반영
node scripts/apply-classical-coverage-workbook.mjs <source.xlsx> <coverage.json> <output.xlsx> <preview-dir>

5. 보유 검증 큐와 1차 수집 큐 생성
python scripts/build-classical-validation.py <coverage.json> <search.sqlite> <validation.json>

6. 검증/수집 큐를 XLSX에 반영
node scripts/apply-classical-validation-workbook.mjs <source.xlsx> <validation.json> <output.xlsx> <preview-dir>

7. 최종 검사
node scripts/verify-classical-repertoire-workbook.mjs <output.xlsx>
```

## 재실행 시 주의

- 최초 생성기는 Open Opus의 현재 응답을 다시 받으므로 2026-09-08 스냅샷과 달라질 수 있다.
- v4에서 사람이 수정한 상태 열을 보존하려면 새로 생성한 파일과 안정 ID로 병합해야 한다. 행 번호로 병합하지 않는다.
- DB 대조기는 source/title/composer와 카탈로그·정규화 제목을 사용한 휴리스틱이다. 자동 `보유`도 수동 확인 전 확정값이 아니다.
- `*.inspect.ndjson`은 재생성 가능한 거대 검사 로그라 인수인계 패키지에서 제외했다.
- MusicSearch의 검색 DB와 원본 MusicXML은 이 패키지에 포함하지 않았다.
- `CHECKSUMS.sha256`로 최신 XLSX와 두 JSON의 무결성을 확인한다. 패키지 XLSX 해시는 MusicSearch 원본 v4와 일치한다.

## 검증 기준

- 시트 15개 존재.
- 작곡가 데이터 220행, 작품 데이터 14,027행.
- 보유 검증 큐 5,252행, 1차 수집 154행.
- 수식 오류(`#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, `#N/A`, `#NUM!`, `#NULL!`, `#SPILL!`, `#CALC!`) 없음.
- 수집 상태·권리 상태·XML 품질의 선택 목록 유지.
