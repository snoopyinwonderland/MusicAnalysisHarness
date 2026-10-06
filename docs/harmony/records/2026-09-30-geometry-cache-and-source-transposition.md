# 성부 기하 정보 재사용과 기보음·실음 변환 준비

단계: HARM-DEV-20260930-25. 화성 개발 문서다. 인수인계 문서나 구조 분석 기록과 별도로 관리한다.

## 목적과 범위

직전 확대 실행의 19개 작품 가족·33개 악보/악장·322개 구간을 유지한다. 계산 비용을 줄여 다음 검증량을 늘리되, 후보나 어려운 구간을 삭제해 속도를 높이지 않는다. 관현악의 서로 다른 기보음을 직접 합산하지 않도록 source 기반 실음 변환을 별도 prototype으로 준비한다.

특정 작품/마디의 정답 규칙, Canonical Core/schema/parser migration, 원악보/원주석 수정, 권리/split/gold/학습 자격 승격, 외부 AI API, 운영 5173/구조 분석/악보 화면 변경은 이번 범위가 아니다.

## 1. 기존 병목과 안전한 재사용 범위

직전 quartet 창의 209개 관계 질의는 5개의 정확한 context span을 공유했지만 전체 악보의 성부 정보를 209번 준비했다. `voice_links`의 결정론적 관측만 재사용한다.

- 전체 IR의 모든 sounding event, 정확한 Fraction 시간, 모든 `source_note_ids`의 part/voice 소속을 유지한다. attack note만으로 소속을 대신 판단하지 않는다.
- 전체 성부의 원래 삽입/진단 순서와 onset/ID 정렬 규칙을 유지한다.
- 구간 밖의 겹침과 다음 onset도 계속 확인한다. 작은 구간만 잘라 만든 성부에서 연결을 발명하지 않는다.
- 같은 기하 정보가 있어도 화음 후보·구성음 membership·candidate blocker·이끎음/7음 의무·witness·assignment·질의 예산 결과는 매번 새로 검사한다.
- 기존 sampled assignment와 explicit IR voice 연결을 합치지 않는다. `ir=None` witness 재검사는 여전히 assignment-only다.
- 반복/ending 장벽은 기존 상위 관측 계획에서 처리한다. 캐시가 장벽을 우회하거나 새 음악 규칙을 추가하지 않는다.

`prepare_voice_geometry`와 `voice_links_from_geometry`는 기존 `voice_links`의 계산을 분리한 것이다. 비캐시 호출도 같은 함수들을 사용하며 성부 추론이나 가장 가까운 음표 연결을 새로 추가하지 않는다.

## 2. 캐시 계약

`VoiceGeometryCache`는 전역/디스크 캐시가 아니라 한 악보의 짧은 실행 세션이다.

1. 입력 IR 전체를 깊은 복사해 private snapshot을 만든다. 전체 JSON SHA256과 cache/geometry/prepare 버전, 정확한 `(start,end)` Fraction을 키로 사용한다. score ID나 Python object ID만으로 재사용하지 않는다.
2. 실제 기하 정보 준비는 최초 조회까지 미룬다. survey의 기존 앞단계·pair-budget 게이트와 빈 관계 목록은 캐시 준비 없이 반환한다.
3. 세션 진입/종료에서 전체 입력 해시를 비교한다. 세션 중에는 같은 IR 객체만 허용하며 변경된 입력의 결과를 종료 시 반환하지 않는다. 세션 밖의 조회는 매번 전체 해시를 검사한다.
4. 기본 128개 exact-span LRU로 메모리를 제한한다. eviction은 기하 정보의 재계산만 유발하고 후보/질의/보류를 삭제하지 않는다.
5. 반환값은 매번 깊은 복사한다. `2/2`와 `1/1`은 같은 시간 키를 공유하지만 현재 호출의 `context_span` 표현과 추가 metadata를 다시 붙여 의미 JSON을 보존한다.

자동 활성화는 계획된 질의의 정확한 context span 재사용 수 `Σ(동일 span 질의 수−1) ≥ 16`일 때만 한다. 임계치는 초기 비용을 피하기 위한 구현상의 성능 가드이지 음악 규칙이나 최적 임계치 인증이 아니다. 화음 라벨·정답·질의 결과로 활성화를 고르지 않고 질의는 0개 삭제한다. 명시적 cache를 전달한 개발 검사는 계속 강제 재사용할 수 있다.

survey → distributed resolution → direct constraints → progression resolution에 명시적 keyword로 전달한다. monkeypatch나 암묵적 전역 상태는 쓰지 않는다. `use_geometry_cache=False`로 비캐시 경로를 유지하며 결과의 음악 계약 버전/필드를 변경하지 않는다. 캐시 버전과 코드 해시는 별도 실행 계약에 기록한다.

## 3. 고정 결과의 동등성 검사

`harmony_geometry_cache_trial.py`는 직전 r2의 모든 322개 고정 sample/plan index와 원자료·IR·artifact 해시를 확인한다. 기존 train/dev 내부 연구 정책만 사용하고 holdout 또는 변환되지 않은 조옮김 악기를 승격하지 않는다.

이번 replay는 저장된 continuous/contrast/lattice를 입력으로 받아 **relation survey와 hold/change만 다시 계산**한다. 앞단계를 새로 계산했다거나 322개 구간을 처음 분석한 것으로 세지 않는다. 두 단계의 전체 JSON을 비교해 순서·후보·보류·음표 근거·witness·미설명 음가가 달라지면 `semantic_mismatch`로 기록한다.

동일 입력/현재 코드의 cached/uncached survey microbenchmark는 고정 순서에서 collection별 첫 비어 있지 않은 질의를 선택하고 2개 collection까지 제한한다. 두 round의 실행 순서를 반대로 해 순서 효과를 줄인다. 전체 분석/서버/렌더링 속도와 비교하지 않으며 직전 full-run wall-time을 분모로 사용하지 않는다.

### r1의 동등성 통과와 성능 반례

`output/harmony-geometry-cache-trial-2026-09-30-r1/`은 322개 relation/hold-change 전체 JSON이 기존 결과와 동일했다. 실제 15,195개 조회에서 전체 악보 준비154회, exact span miss548회/hit14,647회, eviction0회였다. 입력493개·코드246개의 해시와 코드 파일 목록은 실행 동안 불변이었다.

그러나 캐시를 무조건 쓰는 것은 적절하지 않았다. 동일 코드·동일 frozen 입력·반대 순서의 2회 microbenchmark에서 quartet117질의는 평균14.154초→3.226초(4.39배)였지만, sonata6질의는0.156초→0.393초로 느려졌다. 후자는 원IR snapshot/hash 준비 비용을 충분히 회수하지 못한 사례다. r1을 삭제하거나 성공 사례만 고르지 않고 보존하며, 위의 geometry-only 재사용 가드를 추가한 r2에서 같은322개 구간과 같은 benchmark 표본을 다시 검사한다. 이 숫자는 relation survey 부분의 시간이며 전체 화성 분석/브라우저 표시 속도가 아니다.

### r2 최종 결과

`output/harmony-geometry-cache-trial-2026-09-30-r2/report.json`은 완료/exit0다. 기존19가족·33package의 **322/322 구간에서 relation survey와 hold/change의 전체 JSON이 모두 동일**했다. 새로운322개 작품이나 화성 정답이 아니다. 캐시는134개 survey에서 자동 활성화되었고 whole-score prepare134회·span miss517회/hit14,520회·eviction0회였다. 기존 실제 관계 질의15,195개·hold/change 비교66개·모든 보류/후보는 그대로다. 나머지 survey는 저재사용 또는 기존 앞단계/예산/빈 질의 조건으로 캐시를 준비하지 않았다.

입력493개·현재 코드246개의 내용 해시와 코드 파일 목록은 실행 시작/종료 사이 불변이었다. 각 frozen artifact는 실제 읽어 소비한 byte SHA256도 검사했다. 전체 실행274.392초는 preflight 제외·benchmark 포함이며 이후 full test와 일부 동시 실행되었으므로 전체 엔진의 속도 향상 지표로 사용하지 않는다.

| 같은 고정 benchmark | 질의/재사용 | 자동 캐시 | 비캐시 평균 | 자동 경로 평균 | 해석 |
|---|---|---|---|---|---|
| `n01op18-1_01`, `cont_e19939557bb600b9a92a` | 117질의/114재사용 | 켜짐 | 13.712초 | 3.496초 | 해당 relation survey에서 약3.92배 |
| `01-1`, `cont_c746e2edd7221f185acf` | 6질의/4재사용 | 꺼짐 | 0.183초 | 0.163초 | 준비 비용 회피. 작은 측정 차이를 속도 개선으로 인증하지 않음 |

각 benchmark의 모든 결과도 동일했다. 두 표본의 순서는 r1과 같으며 성능이 좋은 다른 사례로 바꾼 것이 아니다. 최적 임계치·전곡 화성 정확도·서버/화면 성능의 일반적 보장은 아니다.

### 최종 읽기 전용 독립 감사

실행 담당과 다른 검토자가 최종322개 전부의 gzip byte SHA256/CRC·JSON 파싱, 저장 reference/observed logical SHA, 이전 breadth r2의 relation/hold-change 전체 객체와 모든 배열 순서·null을 다시 대조했다. 표본/index/report 순서 및 이전/신규 각322개 artifact 파일 집합도 일치했다. frozen493입력·현재246코드의 내용 및 정확한 코드 파일 목록이 일치했고, 33package/19가족/train27·dev6/5collections와 원manifest의 분할·권한은 유지됐다.

관현악 source r2도 입력5개·코드5개·case3개를 검사하고 원XML/MXL의10선언·70note locator를 직접 대조했다.30변환의 수식·철자·음높이가 일치했고40무선언 control은 보류였다. r1/r2의 실제 written/concert pitch·source ref·변환 결과/보류 사유는 같으며 presence/count/staff metadata만 추가됐다. 전곡/화성 사용 인증·IR migration·학습/gold승격은 없었다.

감사 과정의 집계 스크립트는 정상 `query=null` 보류를 처음에 처리하지 못해 중단되었으나 null 보존을 반영해 전체322개를 마쳤다. 원 계산 오류나 JSON 불일치가 아니며 보류를 ready나false로 채워 통과시키지 않았다. 최종 차단 문제0건이다. 직접 witness578/시간 가능성16 및 기존 미지원·보류 결과는 그대로이며 최종화성/cadence/정확도 인증은 아니다.

## 4. Source 기보음·실음 변환 prototype

`harmony_source_transposition.py`는 원XML/MXL의 `<pitch>`를 직접 읽어 입력이 written pitch임을 보장한다. 이미 concert pitch로 바뀐 IR에 다시 transpose하지 않는다. 원 step/alter/octave/MIDI, source part/printed·sequential measure/element index/note ordinal/XPath, 원 `<transpose>`와 staff 범위를 따로 보존한다.

공식 MusicXML 4.0에서 transpose 값은 written pitch에 더해 sounding pitch를 얻는 값이다. diatonic/chromatic에는 octave-change가 포함되지 않으므로 다음을 각각 계산한다.

```text
음계 좌표 이동 = diatonic + 7 × octave-change
반음 이동     = chromatic + 12 × octave-change
```

수동 산식과 music21 Interval 결과의 step/alter/octave/정확한 `.ps`를 교차 확인한다. MIDI의 octave folding이나 이명동음 자동 재표기를 사용하지 않는다. diatonic이 생략된 합법적 MusicXML도 이 prototype에서는 enharmonic spelling을 추정하지 않고 보류한다.

현재 지원은 최초 timeline 이동 전의 모호하지 않은 part/staff 선언과 해당 scope에서 제한된 source-note probe다. 중도 변경은 XML 문서 순서가 아니라 score order의 적용 시점이 필요하므로 전부 보류한다. double, microtonal, concert-score/for-part, instrument-change, 겹치는 선언, source 위치 불일치도 별도 보류한다. 선언 없음은 concert pitch 인증이 아니다.

이 단계는 전체 note/tie/sounding-event 변환이나 Canonical IR migration이 아니다. 하이든 104/1, 브람스 Op45/1, 바흐 Crucifixus의 총보에서 source 선언/probe만 검사한다. 박자·판본·파트 매핑·주석/정답 자격의 기존 문제는 그대로 남는다.

### 실제 총보의 source 검사 결과

현재 최종 출력은 `output/harmony-source-transposition-probe-2026-09-30-r2/`의 `report.json`, `run-contract.json`, `cases/*.json`이다(v0.1.1). 초기 r1도 보존했다. 입력 총보 3개와 정책 README 2개, 코드 5개의 해시가 변경되지 않았음을 확인했다. 정상 자료의30개 통과/40개 보류 수치는 두 실행에서 같다.

| 총보 | 명시 transpose 선언 | 실음 교차 검사 통과 probe | 선언 없는 control 보류 |
|---|---:|---:|---:|
| 하이든 104/1 | 7 | 21 | 11 |
| 브람스 Op45/1 | 3 | 9 | 19 |
| 바흐 Crucifixus | 0 | 0 | 10 |
| 합계 | 10 | 30 | 40 |

선언당 source XML 순서의 최초 pitched note 최대 3개를 검사했다. 30개 성공은 별도의 작품이나 전곡 음표 수가 아니며, 선언 없는 40개 control은 원 기보음을 보존하되 실음으로 인증하지 않았다. 3개 가족의 전곡 실음 인증·IR migration·화성 사용 승인 수는 모두 0이다.

각 선언의 첫 실제 probe를 아래처럼 기록했다. 악기 이름은 설명용 source metadata이며 조옮김 추정 규칙에 사용하지 않는다.

| 총보의 파트 | source 표기 마디 | diatonic/chromatic/octave-change | 기보음 → 실음 |
|---|---:|---|---|
| 하이든 A Clarinet 1/2 | 1 | −2/−3/0 | F4 → D4 |
| 하이든 D Horn 1/2 | 33 | −6/−10/0 | C5 → D4 / C4 → D3 |
| 하이든 D Trumpet 1/2 | 33 | +1/+2/0 | C5 → D5 / C4 → D4 |
| 하이든 Contrabass | 1 | 0/0/−1 | D3 → D2 |
| 브람스 F Horn 1/2 | 1 | −4/−7/0 | C4 → F3 |
| 브람스 Contrabass | 1 | 0/0/−1 | F2 → F1 |

마디 33의 첫 pitched note라도 적용하는 선언은 초기 part 선언이다. 최초 휴지 마디를 건너뛰어 source note를 선택했을 뿐 onset이나 화음의 적용 시점을 계산한 것은 아니다. 모든 probe는 child index와 note ordinal로 원XML 위치를 재해결했다.

### 독립 검토에서 발견한 source 입력의 경계 문제

v0.1.0은 staff `1`/`+1`/`01`을 서로 다른 문자열로 비교하여 중복 scope를 놓칠 수 있었고, 명시적 빈 `<alter/>`/`<octave-change/>`를 요소 부재와 같은0으로 볼 수 있었다. source 선언/음높이/staff의 중복 자식도 첫 값을 고르는 문제가 있었다. 실제3개 총보에는 이 조건이 없었지만 다른 입력에서 잘못된 실음으로 통과할 수 있으므로 v0.1.1에서 보강했다.

- 원문 staff 표기는 보존하되 scope 비교는 검증된 정수로 수행한다.
- optional 요소가 없을 때만 기본0이다. 명시적 빈 값·공백뿐인 값·중복 값은 보류한다.
- pitch/step/alter/octave, transpose의 diatonic/chromatic/octave-change/double, note staff의 cardinality를 확인한다. 중복을 첫 값만 읽거나 자동 복구하지 않는다.
- 합법적으로 생략 가능한 diatonic을 이 prototype이 처리하지 못한다는 사실은 그대로 기록한다. 자료 자체가 잘못되었다고 일반화하지 않는다.

source 회귀39개(기존28+후속11)는 위의 alias/빈 값/중복·반례와 정상 optional 기본값을 포함한다. 이 변경은 source 검사 prototype의 실패 방지이며 기존 Core/parser에 적용한 변경이 아니다.

공식 근거: [transpose](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/transpose/), [octave-change](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/octave-change/), [attributes](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/attributes/). 구체적인 참고 URL·검증 날짜·music21 버전과 입력/code 해시는 별도 source audit 계약에 남긴다.

## 5. 테스트·실패·미해결

캐시 계약 회귀 37개와 trial 회귀 11개를 추가했다. 깊은 복사/metadata/Fraction 동등 키/IR 변경/scope/LRU/lazy 준비/구간 밖 겹침·후속음/cross-staff/교차 성부 tie/chord/grace/assignment별 대조/중복 후보/예산 no-pruning을 검사한다. 자동 비용 가드의 재사용15회/16회 경계, 다수 고유 span, metadata가 다른 Fraction 동치, 명시적/비활성 cache, 라벨 미참조, 모든 blocked/duplicate 후보와 IR identity gate 순서도 확인한다. trial은 source hash/고정 표본 누락/holdout 보호/실제 pipeline 동등/재실행 덮어쓰기 금지/실제 소비 bytes/입력 stage 변경도 검사한다. source 변환은 두 개 이상의 임시표, octave folding 방지, 이중 변환 거부, staff 범위, 중도 변경 보류, locator 변조, 라이브러리 오류의 fail-closed 처리 등을 검사한다.

독립 코드 검토에서 replay의 code 목록 변경, frozen stage 입력 변경, 소비 시점 artifact hash 검사 누락을 발견해 실행 전에 보강했다. 실행 끝의 코드 목록 대칭 차이와 입력 해시 변경도 실패로 보고한다. 새 output만 허용하고 이전 r2 결과를 덮어쓰지 않는다.

이번 신규87개(캐시37+trial11+source39), 전체 Python1,986개 테스트 통과(36.266초). 기존 engraving layout warning1건은 유지한다. 작품 수/화성 정답 수가 아닌 코드 회귀 검사 수다.

`git diff --check` 통과(CRLF 경고만), 이번 범위15개 코드/테스트/개발문서의 trailing whitespace·대체문자 검사와4개 개발문서의 로컬 링크 검사도 통과했다. 기존 dirty worktree와 이 단계 이전 변경은 보존했고 Git commit/push는 실행하지 않았다.

cache hit나 결과 동등성은 음악적 정답의 증거가 아니다. 이후 실제 후보 관계의 양성/근접 반례·참조 의미 대조·음악적 검수는 별도로 진행한다. 관현악 전곡 화성 분석은 score-order transpose timeline과 정확 note mapping, 판본/반복/정책 확인 이후다.

## 6. 변경 파일과 실행 재현

| 변경 | 계약/역할 |
|---|---|
| `harmony_reading_voice_context.py` | 기존 계산을 whole-score geometry 준비와 exact-span 조회로 분리. 결과 의미 버전은 기존대로 유지 |
| `harmony_voice_geometry_cache.py` | `voice-geometry-cache-0.1.0`, private snapshot·hash·bounded LRU·deep copy |
| `harmony_progression_resolution.py`, `harmony_resolution_constraints.py`, `harmony_distributed_resolution.py` | optional keyword로 geometry만 전달. witness/assignment/IR 검사는 유지 |
| `harmony_candidate_relation_survey.py` | 후보 관계 계약0.2.0 유지. 자동 비용 가드 및 비캐시 경로; 음악 JSON에 성능 metadata를 혼합하지 않음 |
| `harmony_geometry_cache_trial.py` | `geometry-cache-equivalence-trial-0.1.1`, 전체 고정 구간 동등성/성능/입력·코드 감사 |
| `harmony_source_transposition.py` | `harmony-source-transposition-probe-0.1.1`, source pitch·선언·위치의 제한된 교차 검사 |
| `tests/test_harmony_voice_geometry_cache.py`, `tests/test_harmony_geometry_cache_trial.py`, `tests/test_harmony_source_transposition.py` | 구현 동등성·fail-closed·변조/반례 회귀. 음악 작품/정답 수와 분리 |

작업 위치는 `K:/Music Analysis`다. 아래 output은 이미 생성된 경로이므로 **재실행은 새 output 이름을 사용**한다. 기존 실행/실패 기록을 덮어쓰지 않는다.

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -u -m musicanote_harness.harmony_geometry_cache_trial --reference output/harmony-breadth-trial-2026-09-30-r2 --output output/harmony-geometry-cache-trial-2026-09-30-r2 --benchmark-samples 2
.venv/Scripts/python.exe -m musicanote_harness.harmony_source_transposition --corpus-root 'K:/MusicSearch/data/classical-corpora' --output output/harmony-source-transposition-probe-2026-09-30-r2 --probes-per-scope 3
.venv/Scripts/python.exe -m unittest discover -s tests
```

## 7. 결정과 다음 단계

캐시와 자동 비용 가드는 관측 결과를 그대로 보존하는 prototype 구현으로 채택한다. 후보 선택/음악 정확도와 별개이며 운영/UI 적용은 하지 않는다. source 변환은 제한된 probe 수준을 유지한다. alias·빈 값·중복의 실패 방지와 전체 MusicXML XSD 유효성 인증도 구별한다.

1. 확대 실행에서 새로 관측한 직접 witness578개와 시간 경로 조건부 가능성16개의 실제 source/IR·경쟁 후보·근접 반례를 정리한다. 이를 독립 양성 정답이나578개 작품으로 세지 않는다. 기존의 미관측 구성음/NCT/timing/예산 보류도 포함한다.
2. 관현악은 모든 음표를 score-order transpose timeline에 연결하는 설계와 정확 source↔IR 매핑 검증이 먼저다. 중도 선언·cross-staff·tie의 지속을 시험하고 written/concert을 별도 보존한다.
3. 하이든 총보↔축약보의 박자/마디·브람스 part 매핑·판본/반복/정책을 확인한다. 현재의30개 probe만으로 전체 총보를 화성 평가에 넣지 않는다.
4. 참조 의미 대조와 검수/독립 작품군 자격을 확보한 뒤 화음·전위·secondary·NCT·경계를 분리 평가한다. 더 많은 구간의 계산 성공을 정확도로 보고하지 않는다.
