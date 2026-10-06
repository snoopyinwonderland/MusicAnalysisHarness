# Motif 가족 연결 비교층 개발 기록

- 작업일: 2026-10-05
- 상태: MusicSearch main에 로컬 병합, 기본 비활성인 비교 레이어로 통합
- 기존 Phrase 통합: [Phrase 레이어 개발 기록](phrase-layer-integration.md)
- 입력 제안·외부 측정: [Claude 원본 인계 문서](claude-handoff/phrase-layers-and-motif-discovery.md)
- 범위: Phrase 레이어와 Motif 가족 연결. 기존 화성·Phrase·Motif 경계 결정기 및 피드백 의미는 변경하지 않음.

## 1. 검토와 병합 결정

기존 main의 3e18905b에는 이미 650ca3b4의 Phrase 2층 분석과 source-bound 비교 레이어가 들어 있었다. 최신 81df315959c2bd0e893bdc4119fe3213f71884e2를 검토한 뒤, merge commit d3e7b5c7로 병합했다. Claude worktree는 수정하지 않았다.

새 발견기의 구간으로 기존 Motif 전체를 교체하지 않고, **기존 구간의 가족 연결만 보완하는 비교층**을 선택했다. 원본 문서가 보고한 BPS 32작품 결과는 다음과 같다.

| 조건 | 등장 구간 F1 | 가족 precision | 가족 recall |
|---|---:|---:|---:|
| 기존 엔진 | 0.401 | 0.952 | 0.349 |
| 새 발견기 단독 | 0.300 | 0.965 | 0.623 |
| 기존 구간 + 새 가족 연결 | 0.401 | 0.786 | 0.474 |

등장 구간 품질은 단독 교체 시 낮아지고, 가족 연결은 recall 향상과 precision 하락이 동시에 있다. 그러므로 기본 엔진으로 승격하지 않았다. JKU 5작품 측정도 원문에 있다. **BPS/JKU 정확도 측정은 이번 통합에서 독립 재실행하지 않았으며, 위 수치는 외부 보고값이다.** 아래의 10악보 검사는 정확도 측정이 아니라 비간섭·참조 연결 검증이다.

## 2. 계산 원리와 한계

새 발견기는 attack 간 IOI와 diatonic step의 쌍을 token으로 만들고, 음표 시작점들을 비교하여 반복되는 token 구간을 찾는다. LCE 행렬과 압축 이득 기반 선택을 사용한다. 기본 minNotes=4, maxBars=4, maxNotes=24, minGain=16이며 역행 변형을 허용한다.

이 방식은 동일하거나 전조된 반복 및 허용된 변형을 잘 연결할 수 있지만, **모든 음높이·리듬의 미세한 변형을 이해하는 일반적 유사도 모델은 아니다.** 기존 구간과 발견 구간의 시간 겹침이 기존 구간의 절반 이상이면 후보 연결에 사용한다. 기존 가족 관계와 새 관계를 union하므로 전이적 연결이 서로 다른 가족을 잘못 잇는 위험도 있다. F 번호와 연결 근거를 따로 보여 주어 검토할 수 있게 했다.

Phrase 끝을 새 Motif의 끝으로 대입하거나, 작품 ID별 예외 규칙을 만들지 않았다.

## 3. 통합 변경 파일

| 파일 | 역할 |
|---|---|
| server/motif-discovery.mjs | Claude 발견기 및 tie·입력 검증 보완 |
| server/motif-discovery-integration.mjs | source 계약, 제한, provenance, LRU cache |
| server/motif-discovery-integration.test.js | 보호 관문·tie·cache 회귀 |
| server/search-api.mjs | opt-in getWork 응답 필드 추가 |
| src/music/motifDiscoveryComparison.ts | snapshot 확인 및 기존 구간 가족 연결 adapter |
| src/music/motifDiscoveryComparison.test.ts | 원 구간/ID 보존·mismatch 보호 |
| src/components/MotifDiscoveryPanel.tsx | 가족별 비교 목록과 실행 상태 |
| src/components/FullScorePage.tsx | URL flag, 표시용 label 복사본, 원 선택 유지 |
| src/components/motif-family-live-regression.test.ts | 명시 실행하는 10악보 비간섭 감사 |

Claude 원본 test 및 handoff 문서는 merge commit에 포함되어 있다. 기존 수집 log와 데이터는 이번 통합 commit에서 제외한다.

### Tie와 입력 보호

- tie 뒷음은 같은 pitch, 정확히 이어지는 시각, 성부가 있으면 같은 voice일 때만 앞 attack에 합친다.
- 잘못 이어진 continuation은 새 attack으로 두고 inputWarnings에 index·issue·reason을 남긴다.
- occurrence의 endIndex는 tie의 마지막 원본 음표까지 보존한다. 이미 합쳐진 sounding event의 길이를 다시 더하지 않는다.
- 유한 pitch/onset/duration, 음수 길이, 유효 meter를 검사한다.
- 기존 familyNumber가 없는 구간들을 undefined라는 이유로 한 가족으로 묶지 않는다.

### API와 source 계약

getWork(..., {structure:'1', phraseLayers:'1', motifDiscovery:'1'})를 사용할 때만 새 응답 motifDiscovery를 추가한다. OFF에서는 해당 필드를 만들지 않는다. 제한된 preview/excerpt에는 전체 발견기를 실행하지 않는다.

계약 버전은 motif-family-comparison/1이다. cache key는 work/stream/source ID, source SHA, 렌더 XML SHA, 관찰 event SHA, 실제 엔진 코드 revision, 계약·노트 제한을 포함한다. LRU는 최대 16항목이고 반환은 defensive copy다.

각 occurrence에는 startEventId, endEventId, eventIds, occurrenceId 및 공통 quarter 단위 [start,end) 참조가 붙는다. 원본 work/stream/source와 note snapshot이 client에서 달라지면 연결을 적용하지 않는다. 하성부 검색으로 들어와도 구조 비교 표시는 기존 structureWork의 상성부를 따른다.

**이 adapter는 아직 MusicSearch indexed events를 사용하며 Canonical IR 문서를 직접 입력받지 않는다.** canonicalIrDocumentId는 null, 시간은 indexed float의 decimal rational 포장이고 원 XML divisions에서 직접 계산한 exact rational이 아니다. provenance에 이 제한을 명시했다. XML 재정렬 검증이나 Canonical IR 적용이 완료된 것처럼 표현하지 않는다.

### 자원·박자 관문

4096 input notes를 넘으면 자르지 않고 input-note-budget-exceeded로 건너뛴다. 발견기의 O(n²) Int16 행렬은 이 한도에서 약 32 MiB이며 추가 배열 비용도 있다. 호출은 아직 synchronous라서 worker 격리·실행 deadline은 후속 과제다.

meter-missing, meter-change-not-yet-supported, invalid-or-nonmonophonic-timeline은 명시 skip이다. upstream maxBars가 첫 박자를 사용하므로 변경 박자를 지원한다고 주장하지 않는다. 건너뛰어도 기존 분석은 남는다. 특정 제목에 meter를 하드코딩하거나 누락 값을 4/4로 채우지 않는다.

## 4. 화면에서 확인할 것

[Phrase·Motif 비교 악보](http://127.0.0.1:5173/score?workId=work-fd275425506cc192&browse=1&phraseLayers=1&motifDiscovery=1)

- Phrase 비교층은 기존 통합대로 상위/호흡 단위 중 선택할 수 있다.
- 새 Motif 가족 비교는 기본 OFF이며 URL motifDiscovery=1 또는 패널 버튼으로 켠다.
- 악보에는 '비교 F4 · Motif 5-1'처럼 비교 가족 F번호와 기존 Motif 번호를 함께 표시한다. F4와 기존 Motif 4는 같은 번호 체계가 아니다.
- 패널은 가족별로 기존 구간들을 묶고 해당 구간을 클릭하면 기존 Motif 세부 선택으로 연결한다.
- 기존 Motif summary, motifNumber, familyNumber, 경계, 선택과 피드백 ID는 그대로다. 표시용 복사본의 label만 바뀐다.
- 새 발견기 자체의 M번호를 기존 Motif 번호로 덮어쓰지 않는다. 새 discovery와 기존 extent의 차이도 숨기지 않는다.
- skip/error/mismatch면 기존 표시를 유지하고 사유를 보여 준다.
- 검토 중 사용자 의견을 대신 제출하지 않았다.

브라우저에서 상위14/호흡39 전환, 기존 Motif 유지, 비교 label과 가족 목록 클릭을 확인했다. 화면 증거는 다음 로컬 파일에 보관했다.

- [악보 표시](<K:/Music Analysis/output/motif-family-merge-2026-10-05/comparison-score.jpg>)
- [가족 비교 패널](<K:/Music Analysis/output/motif-family-merge-2026-10-05/comparison-panel.jpg>)

## 5. 독립 검증 결과

### 단위·전체 테스트

- 관련 6파일 36검사 통과: Motif 발견5, server integration8, Phrase breath8, Phrase integration11, client adapter3, Phrase panel1.
- search-api와 server 관련 묶음 직렬 실행: 126검사 통과.
- 전체 vitest 직렬 실행: 107파일, 675검사 중 **672통과/2실패/1skip**, 47.63초.
- skip은 환경 변수를 명시해야 실행하는 새 live 감사다.
- app/node TypeScript noEmit 둘 다 통과.
- production build(tsc -b + vite build) 통과. Verovio의 node:module externalization 및 큰 WASM bundle 경고는 남아 있으며 이번 가족 비교의 실행 실패는 아니다.
- 병합 전 병렬 baseline에는 search-api 한 검사에서 5초 timeout이 추가로 있었지만 직렬 재검사에서는 통과했다. 이를 새 알고리즘 오류나 속도 개선으로 주장하지 않는다.

전체 실패 2개는 기존 FullScorePage.test.ts의 다음 기대값이다. 병합 전에 같은 실패를 확인했고, 기존 알고리즘/기대값을 바꾸어 숨기지 않았다.

1. uses parallel relation cells, not Phrase endpoints, to bound repeated Motif variants
2. does not invent Motifs from short Phrase spans without recurrence evidence

### 실제 악보 10요청

10요청/9원 XML/6제목 계열을 병합 전 sealed baseline과 비교했다.

| 작품/요청 | 입력 notes | 기존 가족 | 비교 가족 | 새 발견 가족 | 결과 |
|---|---:|---:|---:|---:|---|
| A Whole New World Piano Solo | 353 | 32 | 24 | 5 | ready |
| 같은 XML 하성부 검색 | 353 | 32 | 24 | 5 | ready, 상성부 cache 재사용 |
| 같은 제목 Duet 하성부 검색 | 244 | 13 | 12 | 3 | ready |
| 같은 제목 Trio 하성부 검색 | 161 | 11 | 10 | 2 | ready |
| Beauty and the Beast Piano Solo | 257 | 15 | 13 | 4 | ready |
| 같은 제목 Quartet 하성부 검색 | 181 | 7 | 5 | 3 | ready |
| Hakuna Matata 하성부 검색 | 637 | 69 | 67 | 2 | ready |
| Beethoven Op.13 1악장 | 123 | 3 | 3 | 0 | meter-missing으로 skip |
| Endless Love | 172 | 20 | 19 | 1 | ready |
| Last Night of the World | 298 | 21 | 18 | 4 | ready |

Phrase·Motif flag를 동시에 켜도 notes, phraseAnalysis, boundary/fullHarmony, ledger, structureSelection, stats SHA와 기존 Motif span objects/IDs/ranges가 baseline과 같았다. 원 XML SHA, DB 크기·mtime, 기존 엔진 5개 및 별개 dirty/수집 파일 14개도 같았다. warnings는 0이었다.

새 발견기의 고유 ready 입력 cache-miss 계산은 이번 한 번의 관측에서 약 3.8–31.6ms, cache 재조회는 약 0.3–1.6ms였다. 전체 getWork의 초기 DB/cache/기존 엔진 비용과 다르며 장시간 성능 benchmark가 아니다. 가족 숫자 감소를 곧바로 정확도 향상이라고 해석하지 않는다.

Op.13 자료는 getStructureSource에서 모든 note.meter가 null인 것을 확인했다. 기존 분석을 손대지 않고 skip으로 남겼다. 이것은 작품 예외 규칙이 아니라 일반 입력 계약의 미충족이다.

[검증 receipt](<K:/Music Analysis/output/motif-family-merge-2026-10-05/comparison.json>)와 [병합 전 baseline](<K:/Music Analysis/output/motif-family-merge-2026-10-05/baseline.json>)은 원본을 덮어쓰지 않도록 보관한다.

## 6. 재현 절차

MusicSearch 폴더의 Node 환경에서 실행한다. 자동 기본 테스트는 live audit를 건너뛴다.

```powershell
pnpm test -- --fileParallelism=false
pnpm exec tsc --noEmit -p tsconfig.app.json
pnpm exec tsc --noEmit -p tsconfig.node.json
```

실제 DB와 baseline이 있는 로컬 환경에서만 감사한다. baseline의 원 XML, DB, 기존 engine, 별개 dirty 파일 snapshot이 현재와 같아야 한다. 시간이 지나 다른 작업이 바뀌었다면 이 검사는 먼저 실패하는 것이 정상이다. baseline을 현재 값으로 덮어써 통과시키지 않는다. 새 작업 비교에는 새 변경 전 snapshot을 별도로 준비한다.

```powershell
$env:MUSICANOTE_MOTIF_LIVE_AUDIT = '1'
$env:MUSICANOTE_MOTIF_AUDIT_BASELINE = 'K:/Music Analysis/output/motif-family-merge-2026-10-05/baseline.json'
$env:MUSICANOTE_MOTIF_AUDIT_OUTPUT = 'K:/Music Analysis/output/motif-family-merge-2026-10-05/comparison-rerun.json'
pnpm exec vitest run src/components/motif-family-live-regression.test.ts --fileParallelism=false
Remove-Item Env:MUSICANOTE_MOTIF_LIVE_AUDIT, Env:MUSICANOTE_MOTIF_AUDIT_BASELINE, Env:MUSICANOTE_MOTIF_AUDIT_OUTPUT
```

output가 이미 있으면 감사 test는 덮어쓰기 대신 실패한다. baseline/receipt 및 corpus는 git에 포함하지 않았다.

## 7. 남은 개발 순서

1. 실제 악보에서 다른 음형이 F 하나로 연결된 경우를 앞뒤 음표·길이·사용자 설명과 함께 저장하고, false bridge와 누락을 구별한다. 기존 extent 개선과 가족 연결 개선을 혼동하지 않는다.
2. 원자료의 일반적인 meter 관찰 복구 및 변경 박자 maxBars 계산을 별도 계약으로 보완한다. 특정 작품 규칙은 금지한다.
3. BPS/JKU benchmark를 독립 재현하고 precision 하락의 유형을 분석한다. 기본 승격은 별도 판단이다.
4. 장문 worker/memory/latency 통제를 추가하고 더 큰 편성·작품을 검증한다.
5. 리듬·음높이의 약한 변형, prolongation 및 core/complete extent를 위한 다중 증거를 기존 Phrase 기반 모델과 비교한다.
6. 화성·학습형 종지 연결은 해당 개발 계약과 검증을 별도로 진행한다. 이번 병합으로 cadence.py나 연구 가중치를 운영에 넣지 않았다.

이번 작업은 로컬 병합·통합이며 GitHub push는 수행하지 않았다.
