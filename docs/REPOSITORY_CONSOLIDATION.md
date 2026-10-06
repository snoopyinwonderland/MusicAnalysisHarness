# 저장소 통합 개발 기록 — 2026-10-06

## 목적과 기준 위치

사용자의 요청에 따라 최신 로컬 코드 상태를 먼저 commit하고, 검색·구조 분석·공통 악보 뷰어를 MusicAnalysisHarness에 포함한다. 기존 저장소/폴더는 삭제하거나 history를 다시 쓰지 않는다. 새 분석 규칙이나 화성 연구 실험은 추가하지 않는다.

- 통합 GitHub: `https://github.com/snoopyinwonderland/MusicAnalysisHarness`
- 통합 브랜치: `codex/unified-analysis`
- Python/화성 위치: `src/musicanote_harness/`
- 웹 위치: `apps/score-workbench/`
- 전체 문서 진입점: [docs/README.md](README.md)

## 출처와 버전 보존

| 출처 | 고정 commit | 범위 |
|---|---|---|
| Harness 최신 보존 | `f1066daf9cf74734fcbebaf2094b0123640a39c2` | 최신 Python·검사·개발 기록·v1 평가 마감 |
| MusicSearch 최신 보존 | `7ac75ffd045941df6ed76f081f916ebfa3ae63ab` | 기존 Phrase/Motif + Claude 통합 + 최신 재생/UI/문서/출처 있는 음원 샘플 |
| Claude Phrase 원출처 | `650ca3b472be5ac546b77ce91b9d3064e74f6135` | 호흡/상위 종지층 및 통합 보완 |
| Claude Motif 원출처 | `81df3159` | note-level Motif 발견과 가족 연결 |
| 통합 전 structure/main 로컬 기록 | `ad5a1868` | 이전 구조 분석 저장소 snapshot |

MusicSearch의 `7ac75ffd`는 최신 코드/문서/재배포 출처가 있는 sample assets 109파일을 commit했다. 수집 중인 data 4파일은 commit에서 제외하고 원폴더에 그대로 남겼다. 이 상태를 버리지 않는다.

웹 코드와 개발 기록은 고정 source commit의 archive로 가져온다. 원 Git 이력은 기존 저장소에 보존하고, 통합 저장소에는 고정 snapshot과 위 출처 ID를 기록한다. 원본의 전체 history를 통합 repo에 병합했다고 주장하지 않는다. 따라서 과거 history 속 대용량 자료/비밀 데이터가 통합 GitHub에 유입되지 않는다.

## 포함·제외 정책

포함: 웹 src/server/scripts/packages, 실행/lockfile/TypeScript/Vite 설정, 개발 docs/handoff, 평가 설명/JSON 근거, 출처·license가 있는 public instrument samples, Python 코드/검사/규격/개발 기록.

제외: .git/.codex, .env/비밀키, node_modules/.venv/build, data의 corpus/SQLite/수집 캐시, 웹 snapshot의 원본 MusicXML/MXL/MIDI/PDF/DOCX/XML, 루트의 실험 output/reports/tmp, 공개 제외 교재 상세 문서. 웹의 기존 `evaluation` 아래 파생 JSON 평가 근거와 설명은 보존한다. 파일을 삭제한 것이 아니라 공개 commit의 범위를 제한한 것이다. 원source와 실패 실험 결과는 로컬에 유지한다.

CC BY 3.0 악기 음원 샘플은 앱 `public/samples/README.md`와 manifest의 Frank Wen/gleitz 출처 표시를 그대로 보존한다. Campania font와 기존 배포 출처도 유지한다. 이번 통합이 외부 자료의 상업적 이용 허가를 부여하지 않는다.

## 실행과 별도 데이터

새 clone:

```powershell
pnpm --dir apps/score-workbench install --frozen-lockfile
pnpm dev:score
# 또는
powershell -NoProfile -File scripts/start_score_workbench.ps1 -Port 5173
```

Python 경로/pyproject는 유지한다. 웹은 기존 앱 package/lockfile을 사용한다. root package scripts는 앱 명령을 전달하는 wrapper이며 알고리즘을 중복 구현하지 않는다.

현재 컴퓨터에서는 기존 `K:\MusicSearch\node_modules`와 `K:\MusicSearch\data`를 새 앱의 local junction으로 연결하여 설치 환경과28GB 이상 검색 DB를 복제하지 않는다. 이 junction은 Git에 올리지 않는다. 다른 컴퓨터에서는 의존성을 설치하고 별도 승인된 data package를 연결하거나 MUSICANOTE_SEARCH_DB 등 기존 환경변수를 지정해야 한다. 원MusicXML 경로는 기존 `MUSICANOTE_MUSICXML_ROOT` 정책을 따른다.

data junction은 **같은 로컬 데이터를 공유**한다. 리뷰 저장을 누르면 기존과 동일한 feedback 파일에 기록되므로 피드백 이력이 두 벌로 갈라지지 않는다. 이 데이터는 공개 Git에 포함되지 않으며 데이터 이관/백업은 별도 작업이다. 무단으로 다른 컴퓨터의 경로를 추정해 연결하지 않는다.

개발 서버는 loopback의 기존5173주소를 사용할 수 있다. 이미 실행 중인 기존 서버를 임의로 종료하지 않는다. 이번 검증은 별도 포트에서 새 앱만 잠깐 실행하고 그 소유 process tree만 종료한다. 실제 운영 프로세스 전환은 기존 서비스를 보존한 채 별도 명령으로 한다.

## 검증 결과

| 확인 항목 | 결과 | 범위와 한계 |
|---|---|---|
| 고정 source와 가져온 파일 비교 | 3,948개 canonical Git blob 모두 일치 | Windows CRLF/LF 정규화 후 Git 내용 비교. 디스크 원시 바이트가 동일하다는 주장은 아님 |
| Phrase/Motif/리뷰/재생/화면 focused 검사 | 120개 중 118개 통과, 2개 실패 | 기존 전체 test suite를 실행한 것은 아님 |
| 원본 MusicSearch의 같은 화면 검사 | 23개 중 21개 통과, 동일 2개 실패 | 통합에서 새로 생긴 오류가 아님. 아래 미해결 항목으로 보존 |
| TypeScript `tsc -b` | 통과 | 기존 앱 설정 사용 |
| Vite production build | 통과 | Verovio의 browser externalization 및 큰 bundle 경고는 남음 |
| Python AST 문법 검사 | 956파일 통과 | 문법 검사이며 전체 Python 테스트나 음악 정확도 평가가 아님 |
| 새 앱 HTTP smoke | HTML 및 작품 API 모두 200 | 아래 실데이터 작품에서 비교 레이어 응답 확인 |

화면 검사 실패는 `apps/score-workbench/src/components/FullScorePage.test.ts`의 다음 두 항목이다.

- `motif overlay spans uses parallel relation cells, not Phrase endpoints, to bound repeated Motif variants`: 예상 범위와 실제 범위 불일치.
- `motif overlay spans does not invent Motifs from short Phrase spans without recurrence evidence`: 예상 빈 목록과 실제 2개 Motif 불일치.

동일 고정 원본에서도 같은 assertion이 실패했다. 저장소 통합 중 음악 알고리즘이나 기대값을 바꾸어 검사를 통과시키지 않았다. 이 두 항목은 별도의 Motif 회귀 수정 대상이다.

공개 전 검사에서 실제 토큰 형식/개인키 패턴의 검색 결과는 없었고 앱 `data`, 의존성, build, 원본 악보 파일은 staging되지 않았다. 이름에 `data`가 들어가는 handoff의 coverage/validation JSON 2개는 원본 데이터셋이 아니라 기존 수집 평가 보고서이므로 보존했다. `git diff --check`는 가져온 원본의 끝 공백/빈 줄을 보고한다. source snapshot을 보존하기 위해 이번 통합에서는 그 서식을 일괄 변경하지 않았다. 이전 작업의 로컬 patch 2개는 보관하고 공개 범위에서 제외했다.

HTTP smoke는 별도 `127.0.0.1:5184`에서 `/`와 `/api/work/work-fd275425506cc192?phraseLayers=1&motifDiscovery=1`을 호출했다. 실제 작품 응답에 기존 `phraseAnalysis`, `fullHarmony` 및 추가 `phraseLayers`, `motifDiscovery`가 함께 있었다. 응답 약 5.5 MB, 이 호출의 응답 시간 0.917초다. 한 번의 측정이므로 일반 성능 보장으로 쓰지 않는다. 검증용 process tree만 종료했고 기존 서버는 변경하지 않았다.

재현 도구는 `scripts/smoke_score_workbench.ps1`이다. 검사 JSON, stdout/stderr, archive ZIP은 로컬 `output/repository-consolidation-2026-10-06/`에 보존하며 Git에서는 제외한다. 새 컴퓨터에서 전체 corpus가 재현되는지는 이번 검사 범위 밖이다.

화성 연구 v1은 [연결 보류로 마감](harmony/records/2026-10-06-v1-closeout.md)한 상태다. GitHub 업로드나 웹 build PASS를 음악 분석 정확도 인증으로 해석하지 않는다.
