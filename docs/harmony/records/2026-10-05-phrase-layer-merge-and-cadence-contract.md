# 프레이즈 비교층 병합과 화성→종지 입력 계약

HARM-DEV-20261005-60 · 2026-10-05 · **로컬 병합·비교 화면 완료 / 새 화성 및 학습형 종지 운영 승격은 미완료**.

## 요청과 결정

사용자 지정 `claude/phrase-breath-layer`의 `650ca3b472be5ac546b77ce91b9d3064e74f6135`를 MusicSearch main에 fast-forward 병합했다. 기존 main은 `d9bca19c5dac1b9fb5ea69cc5d8d9b08aefa1a38`이었다. [직전 통합 검토](2026-10-04-window-reuse-and-phrase-integration.md)의 조건을 따라 **추가 비교층 + feature flag**로 시작한다.

- 통합 보완7파일은 로컬 커밋 `3e18905b93ae23d3e3ce4da413849485d4c905dc`로 저장했다. GitHub push는 이번 요청에서 실행하지 않았다.
- 원 worktree `K:\MusicSearch-breath-layer`는 clean이며 변경하지 않았다.
- 기존 Phrase·Motif·검색·화성·피드백 입력/엔진과 별개 수집 데이터·문서14파일은 유지했다. 전체 worktree가 clean하다는 뜻은 아니다.
- musicomp의 학습형 종지 모델은 병합 범위 밖이다. 모델/가중치 복사·학습·배포·외부 전송은 하지 않았다.
- 사용자 추가 지시: Motif 개선은 Claude에서 진행 중이다. 완성 후 별도 검토·병합하며 이번에는 Motif를 수정하지 않는다.

## 650ca3b4 보완점과 통합 구현

| 항목 | 소비 계약 |
|---|---|
| 종지 관문 | cadenceMinStrength=.58; 누락/미달은 unresolved, 종결 근거 제외 |
| 유형별 점수 | 통과한 정격=1.0/반종지=.5; strength는 확률 아님 |
| 붙임줄 | 동일 pitch·주어진 voice·이어지는 clock만 합침; 불연속은 새 attack + warning |
| 음수 음가 | 거부; 이미 tie 누적된 sounding duration을 두 번 늘리지 않음 |
| 변경 박자 | getStructureSource의 마디 meter를 원 notes의 복사본에 추가; 전체 meter보다 우선 |
| 상위 끝 | 호흡 단위 끝 또는 관문 통과 종지 후보; breathEnd 표식 유지 |

`server/phrase-layer-integration.mjs`는 원 work/stream/source ID, 실제 파일 SHA, 처리 XML SHA, indexed observation SHA를 묶는다. range에 start/end event·전체 eventIds·quarter `[start,end)`를 저장한다. 다음 attack 직전까지의 쉼을 포함하고 마지막 범위는 마지막 release까지다. 기존 event ID는 바꾸지 않는다.

**현재 입력은 Canonical IR이 아닌 indexed logical attack snapshot이다.** Canonical IR ID는 null, alignmentStatus는 `indexed-events-not-revalidated-against-xml`이다. Float의 정확한 decimal rational에 `indexed-float-decimal-not-source-rational`을 붙이며 XML divisions의 triplet 1/3을 복원했다고 하지 않는다.

LRU32와 방어적 copy를 쓴다. cache key에 contract/source/render/observation SHA, work/stream, 엔진·화성 code SHA, key·gate를 넣는다. 같은 snapshot의 rangeId는 같고 metadata/코드가 달라지면 달라질 수 있다. 기존 sourceXml/harmony stream cache 전체는 개편하지 않았으므로 실행 중 원파일 수정 시 서버 재시작/기존 cache 재생성이 필요할 수 있다. source SHA 존재만으로 index 최신 정렬을 보장하지 않는다.

## 화면과 API

[현재 비교 화면](http://127.0.0.1:5173/score?workId=work-fd275425506cc192&browse=1&phraseLayers=1). 로컬5173 서버를 실행했다.

- 기본 요청은 계산하지 않는다. URL/API `phraseLayers=1` 또는 오른쪽 **2층 Phrase 비교(실험) 켜기**로 시작한다.
- **상위 Phrase / 호흡 단위**를 선택하면 점선 띠가 나온다. 원 Phrase 띠만 숨기고 Motif는 유지한다. 현재 경계로 복귀 가능하다.
- 하성부 검색이어도 구조용 structureWork의 최상성부에 flag를 전달한다. 전 성부 화성은 보조 근거로 읽기 전용 사용한다.
- boundary-harmony에 neutral gap cue를 주어 하위 쉼 단서를 이중 계산하지 않는다. 다른 성부만 사용한다고 하지 않는다.
- 새 비교층은 마디별 meter를 받지만 기존 화성 callback의 박자·국소 조성 처리까지 고친 것은 아니다.
- 제한 미리보기/발췌 요청에는 새 전곡 계산을 하지 않는다. 새 범위는 기존 피드백 ID에 저장하지 않고 비교 range의 기존 피드백 버튼은 비활성화한다.
- 하성부 검색에서는 검색 성부와 구조 성부를 둘 다 계산할 수 있는 비용이 남는다.
- 브라우저에서 상위14/호흡39 전환·점선 띠·Motif 유지·현재 경계 복귀를 확인했다. [화면 증거](../../../output/phrase-layer-merge-2026-10-05/upper-layer-view.jpg). 의견을 임의 제출하지 않았다.

## 실제 회귀와 지연

`scripts/audit_phrase_layer_merge.mjs`로 병합 전 기준선을 봉인한 후 default off/on을 비교했다. 원 notes, phraseAnalysis, boundary/full harmony, ledger, selection/stats를 본 요청과 structureWork에서 SHA 비교한다.

| 제목 계열/편성 | workId | 호흡 / 상위 |
|---|---|---|
| A Whole New World Piano Solo | work-fd275425506cc192 | 39 / 14 |
| 같은 XML 하성부 검색 | work-fd275425506cc192-5f596005 | 39 / 14 |
| 같은 제목 Duet | work-f9eccdf1fc19fb03-88a85b71 | 32 / 12 |
| 같은 제목 Trio | work-33c3a5e1b3de42b9-a71ddd21 | 22 / 8 |
| Beauty and the Beast Piano Solo | work-4229f41fc20f9574 | 30 / 13 |
| 같은 제목 Quartet | work-4b5fce9858d70665-142c87e9 | 24 / 12 |
| Hakuna Matata 하성부 검색 | work-104a3e7d61b751c7-d08f9a8a | 100 / 29 |
| Beethoven Op.13 1악장 | work-474e82a835aa3acb | 16 / 7 |
| Endless Love | work-9b94778a6ef069b8 | 30 / 10 |
| Last Night of the World | work-b4fdcba72f89a969 | 43 / 16 |

**10요청 / 9원 XML / 6제목 계열**에서 원 분석 필드 SHA 동일, layer error0이다. 원 event 연결/범위/cache 재사용도 확인했다. 원 XML SHA, DB 크기·mtime, 기존5엔진, 별개 dirty/수집14파일은 불변이다. 화면 Motif 함수도 수정하지 않았다. 이는 **비간섭/연결 회귀이며 경계 정확도 검사가 아니다**.

상성부 새 레이어의 최초 cache-miss runtime은 이번 관측에서35.013–331.922ms, 재조회는 모두 cache hit다. 같은 source 두 번째 요청은 이미 hit라 cold 분모에서 제외한다. 기존 분석/DB/OS 초기 비용이 섞인 첫 default 요청28.083초와 warm feature 요청을 비교해 전체 속도 향상이라고 하지 않는다. 반복 성능 benchmark가 아닌 한 번의 local 측정이다.

## 테스트와 남은 기존 실패

- 관련3파일20검사 PASS /490ms: Claude8 + integration11 + panel1.
- 전체103파일658검사: **656 PASS /2 FAIL**,27.87초. app/node TypeScript noEmit 모두 PASS.
- 새 커밋7파일 staged diff check PASS. 별개 수집 log의 기존 trailing blank 경고는 수정하지 않았다.
- integration commit 뒤 main에는 별개7tracked+7untracked 수집 수정만 남았다.
- 브라우저 로그의 기존 경고도 별도로 확인했다: Notation.tsx의 미지원 measureNumbers 옵션과 Pillar/Repeat 패널의 같은 React key다. 병합 전 코드에도 존재하며 이번에 해결하지 않았다. 악보 비교의 시각 검증 통과가 console-warning 0이라는 뜻은 아니다.
- 브라우저 로그의 기존 경고도 별도로 확인했다: Notation.tsx의 미지원 measureNumbers 옵션과 Pillar/Repeat 패널의 같은 React key다. 병합 전 코드에도 존재하며 이번에 해결하지 않았다. 악보 비교의 시각 검증 통과가 console-warning 0이라는 뜻은 아니다.

기존 FullScorePage.test.ts의 두 실패:

1. `uses parallel relation cells, not Phrase endpoints, to bound repeated Motif variants`: 기대 `[4,7],[8,15],[24,27],[28,35]`, 실제 `[4,11],[24,31]`.
2. `does not invent Motifs from short Phrase spans without recurrence evidence`: 기대 빈 목록, 기존 phrase-first가 조옮김 recurrence 두 구간을 생성.

병합 전 **d9bca19c 원 FullScorePage** + 동일23테스트를 임시 모듈로 실행하여 같은2실패/21통과를 재현했다. import 경로만 바꾸었고 임시 두 파일은 삭제했다. 원 test/Motif 함수는 수정하지 않았다. 기대값과 기존 결과 중 무엇을 바꿀지는 Claude Motif 결과와 함께 별도 검토한다. 전체 green 또는 이번 병합의 새 회귀라고 하지 않는다.

새 tie test의 첫 실행은 plain/tieStart metadata의 전체 rangeId까지 같다고 기대해1실패했다. metadata가 바뀌면 ID가 달라져야 하므로 starts/boundaries/span은 동일, ID는 다름으로 교정했다. 엔진 수정/검사 삭제로 숨긴 것이 아니다.

## 학습형 종지와 화성의 입력 계약

[CADENCE_INPUT_CONTRACT_v0.1.md](../CADENCE_INPUT_CONTRACT_v0.1.md)를 추가했다. musicomp cadence.py와 DEVELOPMENT_LOG #19에서 다음 접속 위험을 확인했다.

- `.root/.bass`는 국소 tonic 기준 **relative fifths**, MIDI pitch class/음도 번호 아님. C조성에서 G=1/F=−1이며 spelling/tonic 없이는 역변환하지 않는다.
- 현재 `_root_pos`는 inv None/누락을 근음 위치로 읽고 bass 누락도 true로 처리한다. Unknown은 mask/자격 관문으로 보존해야 한다.
- 동일 root/function 병합에 시간 공백·repeat·local key 변화 barrier가 필요하다.
- global beat 대신 meter timeline, 실제 도착 sounding note와 쉼 뒤 다음 attack 구별, cadence arrival→다음 Phrase index 매핑이 필요하다.
- 새 화성의 국소 tonic/function/inversion 미확정은 unresolved로 남긴다. 조표→major·최저음→structural bass로 대신하지 않는다.
- legacy strength .58과 logistic threshold .23은 다른 producer 계약이다. sigmoid도 검증된 확률이라고 하지 않는다.
- V→I/→V 후보는 넓게 만들고 Caplin 조건은 특징으로 쓴다. 음악 조건을 전부 hard filter로 겹치지 않는다. Source/clock 오류는 별도 데이터 관문이다.
- Oracle와 blind의 후보 recall/type/selection/boundary 성능을 따로 평가한다. 하위 호흡은 보조 가능하나 상위 Phrase/종지 결과를 자기 입력으로 돌려보내지 않는다.

사용자 제공 DCML161악장0.366/0.371/0.389, musicomp #19의0.501/0.483은 입력 조건이 다르고 이번에 독립 재실행하지 않았다. 주석 화음/국소 조성을 준 종지 F1을 현재 운영 정확도로 쓰지 않는다. 모델/가중치 가져오기·학습·운영 연결은0이며 DCML 로컬 연구 사용 범위를 유지한다.

## 파일·봉인 증거와 재현

MusicSearch 통합7파일은 commit3e18905b의 정본이다: server/phrase-layer-integration.mjs와 test, search-api.mjs, FullScorePage.tsx, PhraseLayersPanel.tsx와 test, docs/phrase-layer-integration.md. [MusicSearch 개발 문서](<K:/MusicSearch/docs/phrase-layer-integration.md>).

Music Analysis에는 회귀 실행기, 이 기록, cadence 계약, 메인/로그 연결 및 결과를 추가했다. 메인/로그에 중복된 같은 기록59는 한 번씩만 남긴다. 원 XML/Core/주석·이전 연구 코드·실험·권한은 변경하지 않았다.

| 파일 | 물리 SHA256 |
|---|---|
| baseline.json | 5d8d97986615705ce45d9e751a0e1e4ec84dba1c49fbeded3bf9297c58ffe7c6 |
| comparison-final.json | 94c38ada8f7afd8490f16fadddeb85eecd630f29bcd37942bdf235f2cff026ba |
| upper-layer-view.jpg | c9d24630795f04814b87d9b9bf6fcd6c1d6533abe35a5d3c6d5c0e4efcd5fcda |

[정본 비교](../../../output/phrase-layer-merge-2026-10-05/comparison-final.json), [검증·커밋 receipt](../../../output/phrase-layer-merge-2026-10-05/integration-validation.json). 첫 성공 comparison.json도 덮어쓰지 않고 보존했다.

문서 사후 검사:5파일 strict UTF-8/replacement0·로컬 링크243/누락0·봉인4artifact/코드8SHA 일치·메인/로그59와60 등록 각1개다. scoped diff check도 통과했다. 서버5173 listening을 다시 확인했다.

문서 사후 검사:5파일 strict UTF-8/replacement0·로컬 링크243/누락0·봉인4artifact/코드8SHA 일치·메인/로그59와60 등록 각1개다. scoped diff check도 통과했다. 서버5173 listening을 다시 확인했다.

```powershell
# MusicSearch
node node_modules/vitest/vitest.mjs run --maxWorkers=2
node node_modules/typescript/bin/tsc -p tsconfig.app.json --noEmit
node node_modules/typescript/bin/tsc -p tsconfig.node.json --noEmit
# Music Analysis: 새 파일명으로 실행. 봉인 파일 덮어쓰기는 거부한다.
node scripts/audit_phrase_layer_merge.mjs compare 'K:\MusicSearch' output/phrase-layer-merge-2026-10-05/comparison-new.json output/phrase-layer-merge-2026-10-05/baseline.json
```

이후 수집 파일이 갱신되면 preservation 비교가 실패할 수 있다. 해당 파일 SHA 변경과 분석 회귀를 구별한다.

## 다음 개발

1. 기록59의 불연속 tie/source-clock 위험을 영향 범위 보류와 올바른 관찰 소비에 연결한다. Core/XML을 몰래 고치지 않는다.
2. 장문 보류를 streaming/bounded exact joint frontier로 처리하고 같은 봉인 후보·점수/분모에서 실제 선택과 정확도를 비교한다.
3. 큰 선택 오류부터 개선하고 국소 조성·기능·전위의 미확정/대안 계약을 확립한다.
4. missing-aware adapter와 동일 입력의 oracle/blind 평가가 준비되면 학습형 종지 연결을 별도 판단한다.
5. 새 비교층의 별도 feedback namespace와 기존 Motif 이슈는 후속이다. Motif는 사용자 요청대로 Claude 결과를 기다려 검토한다.

프레이즈 병합이 원 화성 계획을 대체하지 않는다. 이번에 장문 복구·새 화성 정확도 향상·학습형 종지 배포·전체 Canonical IR 이행이 완료되었다고 보고하지 않는다.
