# 2층 Phrase 비교 레이어 통합

2026-10-05 · 로컬 main 통합 · 기본 분석 대체 아님.

## 병합 출처와 범위

- 기준 main: `d9bca19c5dac1b9fb5ea69cc5d8d9b08aefa1a38`.
- 사용자 지정 브랜치 `claude/phrase-breath-layer`의 `650ca3b472be5ac546b77ce91b9d3064e74f6135`를 fast-forward 병합했다.
- 원 worktree `K:\\MusicSearch-breath-layer`는 수정하지 않았다.
- 추가 integration: opt-in API/UI, source-bound 범위 ID와 출처, 버전 cache, 회귀 검사.
- 기존 Phrase·Motif·검색·화성·피드백 ledger의 계산 입력/엔진은 유지한다. 전체 테스트가 모두 통과한다는 뜻은 아니다.

## 사용 방법

[악보 비교 화면](http://127.0.0.1:5173/score?workId=work-fd275425506cc192&browse=1&phraseLayers=1)을 연다. 오른쪽의 **2층 Phrase 비교(실험)**를 켜고 **상위 Phrase** 또는 **호흡 단위**를 선택한다.

- URL/API `phraseLayers=1`만 활성화한다. 기본 요청에서는 계산하지 않는다.
- 선택 레이어는 악보 위 점선 띠로 표시한다. 비교 중 원 Phrase 띠만 숨기며 Motif는 유지한다.
- `현재 경계`로 원래 표시로 돌아온다. 비교 feature를 끄면 원 요청으로 다시 읽는다.
- 하위 성부에서 검색해 들어온 경우에도 구조 분석용 최상성부의 `structureWork`에 flag를 전달한다. 베이스/전 성부는 화성 보조 근거다.
- 제한 미리보기와 발췌 요청에는 새 전곡 레이어를 계산하지 않는다.
- 새 범위는 읽기 전용 비교다. 기존 피드백 ID에 새 판단을 저장하거나 기존 Motif를 재분류하지 않는다. 비교 범위의 기존 피드백 버튼은 비활성화 상태다.

## 음악 계산 계약

Claude 650ca3b4의 하위 호흡 DP와 상위 종지 단위를 그대로 소비한다.

- 종지 strength는 미보정 값이다. 0.58 이상만 받아들이고, 미달/누락은 unresolved로 남긴다.
- 통과한 유형은 정격=1, 반종지=.5의 고정 근거값으로 쓴다. strength를 확률로 부르지 않는다.
- 상위 끝은 호흡 단위 끝 **또는** 관문을 통과한 종지 후보 지점이다.
- boundary-harmony를 neutral gap cue로 읽기 전용 호출한다. 이미 센 쉼 단서를 다시 종지 근거에 더하지 않는다. 전 성부를 사용하며 “다른 성부만”이라고 하지 않는다.
- 붙임줄은 동일 pitch, 주어진 동일 voice, 앞음 끝과 뒷음 onset의 연속성이 맞을 때만 합친다. 잘못된 continuation은 새 attack + inputWarnings다. 음수 길이는 거부한다.
- 이미 tie 누적된 indexed sounding duration을 두 번 늘리지 않는다.
- 마디별 `meter`를 원 source의 getStructureSource에서 읽어 복사본에 추가한다. 전체 meterCount/meterUnit보다 우선한다. 기존 notes를 변형하지 않는다.
- 이 레이어는 기존 전곡 조성 가설을 읽는다. 검증된 국소 조성/새 화성 엔진 결과가 아니다. 기존 화성 callback의 전체 박자 처리까지 개선한 것은 아니다.

## ID·시간·cache

`server/phrase-layer-integration.mjs`가 공통 접속 경계다.

- 원 work/stream/source IDs, 실제 파일 SHA, 처리된 XML SHA, indexed observation SHA를 보존한다.
- 기존 event ID를 그대로 사용하고 모든 range에 start/end event·전체 eventIds를 연결한다.
- span은 quarter 단위 `[start,end)`. 다음 attack 직전까지의 쉼을 포함한다. 마지막 범위는 마지막 event release까지다.
- indexed Number를 정확한 **decimal rational**로 표현한다. XML divisions의 1/3 복원이라고 주장하지 않는다.
- Canonical IR document ID는 현재 null이다. indexed ID를 Canonical note ID로 위장하지 않는다.
- `alignmentStatus=indexed-events-not-revalidated-against-xml`: 원 XML과 index의 일치 여부를 이번에 독립 재파싱으로 확정하지 않았다.
- rangeId는 source/관찰/code/key/gate가 연결된 cacheKey에 의존한다. 같은 snapshot 재계산은 같고 관찰 metadata 변경 시 ID도 달라질 수 있다.
- LRU32와 방어적 copy를 사용한다. cache key에는 contract version, source·render·observation SHA, stream/work, 엔진·화성 code SHA, key, threshold가 들어간다.
- 기존 sourceXml/harmony stream cache 전체를 개편하지 않았다. 파일을 실행 중 수정할 때 기존 cache의 재생성/서버 재시작이 필요할 수 있다. source SHA 존재만으로 index의 최신 정렬을 보장하지 않는다.

## 회귀 작품과 실제 결과

봉인 기준선 및 비교 결과는 `K:\\Music Analysis\\output\\phrase-layer-merge-2026-10-05`에 있다. 실행기는 `K:\\Music Analysis\\scripts\\audit_phrase_layer_merge.mjs`다.

| 요청 workId | 계열/조건 |
|---|---|
| work-fd275425506cc192 | A Whole New World · Piano Solo |
| work-fd275425506cc192-5f596005 | 같은 원자료 · 하성부 검색 |
| work-f9eccdf1fc19fb03-88a85b71 | 같은 제목 · Duet 하성부 |
| work-33c3a5e1b3de42b9-a71ddd21 | 같은 제목 · Trio 하성부 |
| work-4229f41fc20f9574 | Beauty and the Beast · Piano Solo |
| work-4b5fce9858d70665-142c87e9 | 같은 제목 · Quartet 하성부 |
| work-104a3e7d61b751c7-d08f9a8a | Hakuna Matata · 하성부 검색 |
| work-474e82a835aa3acb | Beethoven Op.13 1악장 |
| work-9b94778a6ef069b8 | Endless Love |
| work-b4fdcba72f89a969 | Last Night of the World |

10요청/9원 XML/6제목 계열이다. 새 feature off와 on 모두 병합 전 원 분석 필드 SHA가 같고 layer error는 0이다. 원 XML/DB 크기·mtime, 기존 엔진5개, 별개 dirty/수집 문서14개도 불변이다. 이 검사는 **비간섭/연결 회귀**이며 프레이즈 정답 정확도 검사가 아니다.

새 상성부 레이어의 최초 cache-miss 계산은 이번 관측에서 약35–332ms, 재조회는 cache hit다. 전체 getWork 시간과 구별한다. 기존 분석·DB/cache/OS 시작 비용이 섞인 첫 요청28초를 새 레이어 비용으로 보거나, 따뜻한 요청과 비교해 전체 속도 향상이라고 하지 않는다. 이 수치는 한 번의 관측이며 장시간 반복 benchmark가 아니다. 하성부 검색에서는 검색 성부와 구조 성부를 둘 다 계산할 수 있는 추가 비용이 남는다.

## 테스트 및 기존 실패

- Claude 원8개 + integration11개 + panel1개 = 관련20개 통과.
- 전체 vitest: 103파일, 658검사 중656통과/2실패,27.87초.
- app/node TypeScript noEmit 둘 다 통과.
- 기존 실패 두 개는 `FullScorePage.test.ts`의 parallel Motif extent와 짧은 Phrase의 Motif recurrence 기대값이다.
- `d9bca19c`의 FullScorePage 원본 + 동일23테스트를 별도 임시 모듈로 실행하여 **같은2실패/21통과**를 재현했다. import 경로만 변경했으며 임시 두 파일은 삭제했다.
- 테스트나 기존 Motif 알고리즘을 바꿔 실패를 숨기지 않았다. 후속 구조 개발 이슈로 남긴다.
- 새 tie test 첫 시도의 범위 ID 동등성 기대는 잘못이었다. metadata 변경은 ID를 바꿔야 하므로 starts/boundaries/span은 동일, ID는 다름으로 교정했다. 엔진을 바꿔 통과시킨 것이 아니다.
- scope diff 검사는 새 파일만 대상으로 한다. 기존 수집 log의 trailing blank 경고를 이번 수정으로 주장하지 않는다.
- 브라우저에서 상위14/호흡39의 전환과 Motif 유지, 점선 레이어를 확인했다. 사용자 의견을 임의 제출하지 않았다.

## 정확도·학습형 종지 범위

외부 DCML161악장 0.366/0.371/0.389는 선율/블라인드 종지/주석 종지 조건이 다르며 이번에 재실행하지 않았다. 0.389는 운영 정확도가 아니다.

`K:\\Music Composition\\musicomp\\analysis\\cadence.py`는 이번 병합 밖이다. 국소 조성·기능·전위와 relative-fifths 단위 adapter가 필요하다. 특히 unknown inversion을 root position으로 읽지 않도록 별도 mask/관문을 먼저 설계한다. 모델 import·학습·운영 연결·외부 전송은 하지 않았다.

[화성 개발 입력 계약](<K:/Music Analysis/docs/harmony/CADENCE_INPUT_CONTRACT_v0.1.md>)과 [통합 개발 기록](<K:/Music Analysis/docs/harmony/records/2026-10-05-phrase-layer-merge-and-cadence-contract.md>)을 따른다. 기존 화성 J3의 source-clock·장문 공동 탐색 우선순위는 유지한다.

## 후속 Motif 가족 비교층

81df3159의 Motif 가족 발견 모듈도 검토·병합했다. Phrase 비교층과 동시에 사용할 수 있지만 기존 Motif 구간/ID는 그대로 두고 별도의 F 가족 label과 목록으로 비교한다. 검토 근거·코드·10악보 회귀·재현·남은 한계는 [Motif 가족 연결 개발 기록](motif-family-integration.md)에 따로 관리한다.
