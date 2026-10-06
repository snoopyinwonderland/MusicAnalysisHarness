# 설치·데이터 인수인계·재현 가이드

## 1. 재현 수준

후보 프레이즈 경계 캐시는 [성능 7단계](performance-stage-7.md)를 참조한다. 기본 활성이고 MUSICANOTE_PHRASE_CACHE=0으로 해제한다. 분석기 배포 후 worker 재시작이 필요하다.

최신 성능 재측정 CLI와 SQL 실험의 환경 switch, 원본 결과 위치는 [검색 성능 6단계](performance-stage-6.md)에 있다. 실험은 기본 비활성이고 운영 적용된 최적화로 간주하지 않는다.

- 코드/fixture 회귀: 저장소와 의존성으로 실행한다.
- 실제 검색 재현: 같은 corpus index와 원본 MusicXML, 메타데이터가 추가로 필요하다.
- 과거 실행 재검토: evaluation/runs의 보고서와 `.assets` 스냅샷으로 근거를 읽는다. 최신 코드로 같은 순위를 보장하는 것은 아니다.

**Git clone만으로 전체 서비스를 재현할 수 없다.** 생성 SQLite/JSONL은 .gitignore에 있고, 원본 데이터는 외부 드라이브에 있다. 아래 인계 체크리스트를 함께 전달해야 한다. 새 컴퓨터에서의 클린 설치 전체 검증은 아직 수행하지 않았다.

## 2. 환경과 의존성

현재 검증 환경: Windows/PowerShell, Node 24.19.0 (`node:sqlite` 필요), 저장소 pnpm-lock.yaml(lockfile v9). 의존성 복원은 lockfile을 지원하는 pnpm으로 `pnpm install --frozen-lockfile`을 사용한다. package.json의 latest를 새로 해석하는 무제한 업데이트는 피한다. 재현 기록에 실제 pnpm 버전과 lockfile SHA-256을 남긴다. 정확한 pnpm 버전과 Python 환경의 클린 복원은 추가 확인 대상이다.

```powershell
node --version
pnpm --version
Get-FileHash pnpm-lock.yaml -Algorithm SHA256
pnpm install --frozen-lockfile
node node_modules/vitest/vitest.mjs run server/preclearance-importance.test.js server/structure-analysis-adapter.test.js server/preclearance-search.test.js server/work-identity.test.js server/search-worker-client.test.js
pnpm run build
pnpm run dev
```

웹 주소: http://127.0.0.1:5173/ . 개발용 Vite 설정이 검색 API middleware도 로드한다. `dist`를 정적 호스팅하는 것만으로 검색 API가 생기지 않는다. 운영 서버 패키징은 별도 설계 대상이다.

## 3. 별도 데이터 패키지 (권한 확인 후 전달)

| 항목 | 현재 위치/설정 | 필요성 |
|---|---|---|
| 검색 DB | data/search-index-v2/search.sqlite / MUSICANOTE_SEARCH_DB | 실제 검색; 검증본 약 28.9GB |
| 기본 XML | K:/Music Analysis/musicxml/ / MUSICANOTE_MUSICXML_ROOT | 악보 렌더링과 후보 박자 |
| PDMX XML | U:/MusicSearch-PDMX/xml/ / MUSICANOTE_PDMX_XML_ROOT | 해당 source의 원본 |
| KY XML | U:/KYSing_MusicXML/ / MUSICANOTE_KYSING_XML_ROOT | 해당 source의 원본; 재배포 제한 확인 |
| 판본 registry | data/work-identities.json | 검토된 작품 병합과 증거 |
| 보고서/사례 | evaluation/runs/, evaluation/case-assets/ | Query와 과거 판단 재검토 |
| YouTube 캐시 | data/youtube-matches.json 등 | 선택적; 키 없이 캐시만 확인 가능 |

다른 컴퓨터에서는 환경변수를 실제 경로로 지정한다. shell에서 Node 실행 전에 설정하며 비밀키는 인계 문서나 Git에 적지 않는다. 키는 필요한 운영자가 별도로 설정한다. 과거 README의 데이터 동기화 경로는 초기 프로토타입용이므로 전체 index 복원 절차와 혼동하지 않는다.

인계 시 서버/쓰기 작업을 멈추고 일관된 DB 백업을 만들며, 파일 크기·SHA-256·원본 목록·라이선스·수집일·코드 commit(미커밋 수정은 patch)·lockfile 지문·환경변수 이름/비밀 아닌 경로를 manifest로 보관한다. WAL 쓰기 중인 DB 파일 하나만 복사하지 않는다. 현재 보고서 size/mtime 비교는 강한 내용 무결성 해시가 아니므로 인계 해시 검증을 별도로 수행한다.

DB를 재생성하면 mtime이 달라져 과거 보고서 보강/resume가 거부될 수 있다. 지문을 임의로 바꾸지 말고 새 검색 보고서를 만든다. 파일명과 디렉터리 상대 경로도 sourceId 연결에 중요하다.

## 4. 사전검토 재현 명령

새 `evaluation/runs/handoff-*` 경로가 존재하지 않는 상태에서 순서대로 실행한다.

```powershell
node scripts/prepare-preclearance-structure.mjs evaluation/case-assets/S-STRUCT-003/events.json evaluation/runs/handoff-prepared.json
node scripts/run-preclearance-search.mjs evaluation/runs/handoff-prepared.json evaluation/runs/handoff-search.json
node scripts/regroup-preclearance-results.mjs evaluation/runs/handoff-search.json evaluation/runs/handoff-grouped.json
node scripts/analyze-preclearance-candidates.mjs evaluation/runs/handoff-prepared.json evaluation/runs/handoff-grouped.json evaluation/runs/handoff-importance.json --timeout-ms=60000 --max-notes=50000
node scripts/prioritize-preclearance.mjs evaluation/runs/handoff-importance.json evaluation/runs/handoff-priority.json
node scripts/measure-preclearance-frequency.mjs evaluation/runs/handoff-priority.json evaluation/runs/handoff-frequency.json
node scripts/export-preclearance-report.mjs evaluation/runs/handoff-frequency.json evaluation/reports/handoff-report
node scripts/verify-preclearance-report.mjs evaluation/reports/handoff-report
```

검색이 중단되면 두 번째 명령 끝에 `--resume`을 추가한다. 입력/코드/설정/index가 바뀌었으면 재사용을 거부하는 것이 정상이다. 구조 보강은 성부당 60초, 최대 50,000음이 기본값이다. Ctrl+C로 worker를 종료하고 부분 결과를 저장한다. 강제 프로세스 종료는 부분 파일을 남길 수 있으므로 결과 상태와 JSON 유효성을 확인한다. 기존 output/asset 폴더는 덮어쓰지 않는다.

실제 검증 기준 파일: preclearance-importance-worker-2026-09-15.json. 26그룹/56구간 완료, 기존 검색 결과 불변. 수치가 다르면 데이터 지문·코드 버전·설정부터 비교하고 특정 작품별 예외로 맞추지 않는다.

## 5. 원본에서 재색인할 경우

보고서 초안은 [출력 계약](copyright-infringement-report-v1.md)을 참조한다. HTML과 report.json, manifest/verification 및 원본 evidence의 assets를 함께 인계한다. 박자 캐시 변경과 중단 복구 실험은 [8단계](preclearance-stage8-cache-checkpoint.md)에 기록한다.

Python 파서 `scripts/build-musicxml-search-index.py --help`로 inventory/output/failures 경로를 확인한다. 이 도구 기본 output은 v1이며 기존 전체 corpus의 모든 수집·병합 절차를 대신하지 않는다. corpus inventory와 별도 PDMX/KY 메타데이터를 함께 인계해야 한다.

검증된 최종 works.jsonl이 있다면 `node scripts/build-search-sqlite.mjs <works.jsonl> <새-search.sqlite>`로 별도 DB를 만들 수 있다. 기존 DB를 대상으로 실행하지 않는다. 기본 DB만큼의 공간 외에 새 DB·임시 파일 공간이 필요하다. 전체 이기종 corpus를 원본부터 한 명령으로 재생성하는 작업은 아직 자동화되어 있지 않다.

## 6. 인계 수락 체크

- 코드 revision/dirty patch, lockfile 및 별도 데이터 해시가 일치하는가?
- fixture 회귀, 웹 빌드, 텍스트/멜로디 검색, 조각/상세 악보 표시가 되는가?
- 사전검토 report 상태와 failed/cancelled 수, `.assets` 파일이 맞는가?
- index·원본 권한/보관 정책과 API 키의 별도 전달이 확인됐는가?
- 새 컴퓨터에서 미검증인 항목은 완료 처리하지 않고 기록했는가?
