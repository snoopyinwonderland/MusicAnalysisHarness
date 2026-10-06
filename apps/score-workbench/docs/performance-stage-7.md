# 검색 성능 7단계 — 후보 경계 캐시 (2026-09-16)

## 적용 내용

프레이즈 문맥 중 후보 성부 전체의 경계 분석만 process-local 캐시로 재사용한다.
Query 분석과 alignment별 경계 비교는 그대로 실행한다. 순위 공식, 후보 선별, 악보 target은 변경하지 않는다.
기본 활성, MUSICANOTE_PHRASE_CACHE=0이면 기존 분석 경로다. SQL 집계 실험은 여전히 기본 비활성이다.

server/phrase-context-cache.mjs는 모든 입력 property를 순서 정규화하여 SHA-256 키를 만든다.
음높이뿐 아니라 음가·onset·타이·마디·호흡 기호 등 입력이 달라지면 다른 키가 된다.
analyzer와 breath-symbol 모듈 소스를 revision으로 사용한다. **분석기 배포 시 worker 재시작이 필요하며**
실행 중 파일을 고쳤다고 이미 로드된 함수가 바뀌는 것은 아니다. 디스크 영속 캐시가 아니므로 재시작 시 모두 비워진다.
현재 검색의 corpusNotes 입력 자체를 캐시하며, 원본 XML만 수정해 기존 index에 반영하지 않은 변경까지 새로 읽어 주는 기능은 아니다.
별도 화성 분석 레이어를 캐시하거나 검색 분석 논리에 추가하지 않았다.

후보 쪽 comparePhraseBoundaries가 읽는 strength/continuity를 Float64Array, supported/reliable을 비트 배열로 보관한다.
전체 motif 가설이나 cue 설명을 저장하지 않으며 mapped index를 읽을 때만 객체로 노출한다.
이 압축 뷰는 후보 비교 전용이며 Query 분석·보고서·JSON 직렬화에 사용하면 안 된다.
향후 비교 함수가 다른 필드를 읽도록 바뀌면 캐시 투영 계약과 회귀도 함께 수정한다.

추정 관리 용량 상한 64MiB, LRU 퇴출, 단일 초과 항목은 저장하지 않는다.
수치 backing buffers + 항목당 512bytes로 계상한다. 전체 Node heap/RSS의 절대 상한은 아니다.
키 생성 문자열과 호출 중 분석 결과, 기존 parsed cache는 별도 메모리다.

## 실측과 채택의 범위

두 Query, 각 2회, 같은 worker. 최종 packed 실행 뒤 cache-off control 실행.
시간은 wall seconds이며 OS 캐시를 초기화하지 않았다. packed 측정 중 빌드도 실행되어 엄밀한 무부하 벤치마크는 아니다.
첫 실행을 cold disk 성능으로 해석하지 않는다.

| Query | cache OFF 최초 / 반복 | packed ON 최초 / 반복 | 반복 변화 |
|---|---:|---:|---:|
| PC50-b328cadd7e6c | 12.874 / 8.986 | 15.946 / 6.510 | 약 28% 단축 |
| PC50-63107c35162f | 16.601 / 11.699 | 21.219 / 8.900 | 약 24% 단축 |

반복 phraseContext: OFF 4.978/5.367초 → ON 2.635/2.611초.
키 생성 및 alignment별 비교 비용이 남으므로 0초가 되지 않는다.
반복 cache hit는 457/778개, 관리 용량은 첫 Query 뒤 7,308,912bytes, 두 Query 뒤 16,179,004bytes.
최초 실행은 입력 fingerprint·저장 비용 때문에 오히려 약 3.1/4.6초 느렸다.
따라서 **모든 검색이 빨라졌다는 뜻이 아니며**, 장수 worker의 반복·후보 재사용을 위한 최적화다.
기본 적용하되 최초 실행 중심 workload는 환경변수로 끌 수 있다. 운영 다중 사용자 p95는 별도 검증 대상이다.

최종 ON/OFF 8회 모두 profile을 제외한 전체 반환 JSON hash가 6단계와 동일했다.
순위·점수·why·alignment/target을 포함한 데이터 동일성이고 화면 픽셀 검사나 음악적 순위 정답 검증은 아니다.
- b328: f8ff76bc047608f1720177fbf4055c00ff3b86d6a11cdb4a3a60899dc05be24d
- 63107: e75781a23eccefbb6dbd5bffe0a7a13240682f910d89da21ff8a689e5d84897c

## 실패 실험도 보존

- performance-stage7-cache-2026-09-16: 첫 구현. v8 serialization의 복제 객체 표현 차이로 키 테스트가 실패했다. 이후 안정 키로 수정.
- performance-stage7-compact-2026-09-16: 경계 객체가 용량을 채우면서 반복에도 퇴출되어 개선되지 않음.
- performance-stage7-packed-2026-09-16: 최종 수치 배열, 동일성/재사용 확인.
- performance-stage7-control-2026-09-16: 최종 코드에서 캐시 OFF 대조군.

모두 evaluation/runs 아래 manifest/summary/전체 결과 JSON 보존.
이전 실패 실행을 최종 성능 향상 근거로 합산하지 않는다. Query와 원본 사례는 기존 50개 Harness suite를 참조한다.
프로파일 CLI manifest는 search-api hash만 기록하므로 모든 의존성의 완전한 freeze를 보장하지 않는다.

## 검증·재현·다음 단계

45 tests / 5 files 통과: 캐시, phrase boundaries, retrieval cache, search worker, SQL seed 집계.
TypeScript와 Vite build 통과. 기존 Verovio externalization/큰 chunk 경고는 남아 있다.
새 회귀는 내용 복제/키 순서, 입력·revision 변경, 용량 초과·퇴출, 실제 경계 비교 및 지지/충돌/불명확 근거 동일성을 확인한다.

```powershell
$env:MUSICANOTE_SQL_SEED_AGGREGATION='0'
$env:MUSICANOTE_PHRASE_CACHE='1'
node scripts/profile-search-cases.mjs evaluation/runs/preclearance-variation50-final-2026-09-16/suite.json evaluation/runs/stage7-NEW-on PC50-b328cadd7e6c PC50-63107c35162f
$env:MUSICANOTE_PHRASE_CACHE='0'
node scripts/profile-search-cases.mjs evaluation/runs/preclearance-variation50-final-2026-09-16/suite.json evaluation/runs/stage7-NEW-off PC50-b328cadd7e6c PC50-63107c35162f
```

출력 경로는 새 이름이어야 한다. CLI retrieval cache는 미지정 시 1.
현재 실행 중인 사이트 프로세스를 강제로 재시작하거나 해당 환경을 수정하지 않았다.
다음은 키 생성 비용 감소를 동일성 검증과 함께 실험하고, 서로 다른 Query 혼합/반복 workload에서 hit율·최초 지연·p95를 측정한다.

