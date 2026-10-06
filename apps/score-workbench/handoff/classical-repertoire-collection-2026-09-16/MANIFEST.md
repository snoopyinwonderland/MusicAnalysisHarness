# Package Manifest

## 포함

- `workbook/classical-repertoire-priority-v4.xlsx`
- `data/classical-repertoire-coverage-2026-09-08.json`
- `data/classical-repertoire-validation-2026-09-08.json`
- `scripts/build-classical-repertoire-workbook.mjs`
- `scripts/extend-classical-repertoire-workbook.mjs`
- `scripts/build-classical-coverage.py`
- `scripts/apply-classical-coverage-workbook.mjs`
- `scripts/build-classical-validation.py`
- `scripts/apply-classical-validation-workbook.mjs`
- `scripts/verify-classical-repertoire-workbook.mjs`
- 인수인계 문서 6개와 `requirements.txt`
- `NEW_PROJECT_PROMPT_KO.md`와 `CHECKSUMS.sha256`

## 의도적으로 제외

- v1–v3 XLSX: v4와 Git 이력으로 대체.
- `*.inspect.ndjson`: 파일당 약 71–192MB인 재생성 가능한 검사 덤프.
- `data/search-index-v2/search.sqlite`: MusicSearch의 검색 DB이며 새 프로젝트의 원본 데이터가 아님.
- 원본 MusicXML/PDMX/KYSing 파일: 별도 데이터 보관 정책과 권리 검토가 필요.
- 미리보기 PNG: 재생성 가능.

원본 위치는 `K:/MusicSearch`이며, 이 패키지는 2026-09-16에 분리 이관용으로 생성했다.
