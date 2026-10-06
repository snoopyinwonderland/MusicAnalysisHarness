# MUSICANOTE 개발 문서 지도

코드·개발 기록의 기준 저장소는 MusicAnalysisHarness다. 이 파일을 문서의 단일 진입점으로 사용한다. 실제 음악 기능의 상태와 저장소 통합 완료를 구별한다.

| 영역 | 코드 | 개발 문서 |
|---|---|---|
| Canonical Music IR | `src/musicanote_harness/` | [장기 계약](../MUSICANOTE_Canonical_Music_IR/README.md) |
| 화성 연구·주석·시험 | `src/musicanote_harness/harmony_*.py` | [화성 개발 메인](harmony/README.md), [개발 로그](harmony/DEVELOPMENT_LOG.md) |
| Phrase·Motif·기둥음·악보 표시 | `apps/score-workbench/server/`, `src/` | [구조 개발 진입점](structure/README.md) |
| 검색·재생·공통 악보 뷰어 | `apps/score-workbench/` | [웹 문서 지도](../apps/score-workbench/docs/README.md) |
| 저장소 통합·출처·실행 | 저장소 루트 | [통합 개발 기록](REPOSITORY_CONSOLIDATION.md) |

웹 개발 문서는 상대 링크와 사례 ID를 잃지 않도록 앱의 기존 `docs`에 유지하고 여기서 연결한다. 같은 문서를 두 벌 복제해서 관리하지 않는다. 화성 개발 기록은 별도 `docs/harmony`에 유지한다. 기존 문서의 '다음'은 작성 당시의 계획이며 최신 상태는 각 메인 문서의 결론을 따른다.

원source·코퍼스·실험 출력·학습 가중치와 공개 제외 교재 상세 문서는 로컬 자료다. GitHub clone만으로 실제 전체 음악 데이터가 복원된다고 주장하지 않는다.
