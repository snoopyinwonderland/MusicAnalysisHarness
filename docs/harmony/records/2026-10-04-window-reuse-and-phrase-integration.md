# J3e — 동일 후보 계산 재사용과 Claude 프레이즈층 통합 검토

날짜: 2026-10-04. 개발 기록 HARM-DEV-20261004-59. 기존 J3d 다음 단계이며 운영 분석기·뷰어·다른 worktree를 변경한 기록이 아니다.

## 1. 결과와 결정

- 같은 동결 72구간의 예측·후보 출처·점수·평가 결과를 유지했다. 밀집 2구간만 실제 재추론하고 나머지 70구간은 봉인된 값을 재사용했다. 63선택/9보류, 완전 일치15/51, root+members 시간25.3442%, coverage43.7106%, 경계F170.4225%는 **그대로**다.
- 두 실제 재추론의 합계121.391초→77.897초, 이번 관측에서35.83% 감소다. 한 번의 순차 비교이며 동시 다른 작업·캐시·시스템 부하를 통제한 반복 시간 실험이 아니다. 음악적 정확도 상승으로 해석하지 않는다.
- Python 신규21+이전442+추가 parser/tie/DCML33=**496 PASS**, 28.962초. 실제838고유 SHA·72범위/평가 재생·24전체 catalog 대조를 통과했다.
- 작성 검사: Python5파일 AST, 변경/신규10파일 strict UTF-8·깨진 문자/행끝 공백0, 로컬 Markdown309링크 존재, Node syntax와 `git diff --check` 통과. 기존 별개 tracked dirty5경로를 보존했다.
- Claude의 호흡층/상위 프레이즈층은 **통합 가능한 방향**이다. 기존 경계 대체가 아닌 선택 가능한 비교 레이어부터 권한다. 종지 근거의 신뢰도 소비, 입력 tie/clock 계약, 변경 박자·기존 사례 회귀 검증을 먼저 보완한다. 실제 merge/cherry-pick/외부 파일 수정은 하지 않았다.

## 2. 계산 재사용의 계약

새 파일:

- [WindowWorkspace](../../../src/musicanote_harness/harmony_window_workspace.py)
- [봉인 후 비교 runner](../../../src/musicanote_harness/harmony_window_workspace_trial.py)
- [workspace 검사](../../../tests/test_harmony_window_workspace.py)
- [물리 봉인·동일 결과·tie 검사](../../../tests/test_harmony_window_workspace_trial.py)
- [실제 catalog/평가/이상 tie 감사](../../../scripts/audit_harmony_window_workspace.py)
- [외부 프레이즈 worktree 읽기 전용 점검](../../../scripts/audit_phrase_layer_integration.mjs)

원 augmented/extended 공급자는 같은 base/context `window()`를 여러 번 계산했다. 구간별 결정론적 window 결과를 원 IR SHA에 묶인 최대8entry LRU에서 재사용한다. 서로 다른 분수 표기나 span 부가 필드도 원 결과에 남으므로, 수치만으로 key를 합치지 않고 **원 span JSON 값의 SHA**를 사용한다. 모든 공급자에 방어적 deep copy를 반환한다. Eviction은 재계산만 유발하며 후보·음표·시간점 삭제가 아니다.

이미 봉인된 기존 엔진 파일을 수정하지 않기 위해 `FunctionType`으로 **원 bytecode/default/closure를 유지한 private dependency binding**을 만들었다. 복사된 global dictionary의 `window`/공급자/`propose` 연결만 instance 안에서 교체하며 module global monkey-patch는 하지 않는다. Callable/dependency가 예상과 다르면 거부한다. 이 방법은 **연구 adapter**이며 운영 코드의 권장 최종 API라고 주장하지 않는다. 운영 승격 때는 별도 버전의 명시적 dependency injection API로 바꾸고 같은 대조 검사를 다시 해야 한다.

전체 IR의 불변 lease를 공개 연산 전후 SHA로 확인한다. 변경 탐지 시 캐시를 폐기하고 결과를 거부한다. 다른 IR object의 window 요청도 거부한다. 입력을 계산 도중 수정하는 병렬 작업은 지원하지 않는다. 원 전체 score·part·note·sound·tie·grace·source reference를 유지하며 단선율만 골라 화성을 계산하지 않는다.

후보망·가중치·음악 문턱·raw cap·2M factored search 예산·동점 규칙·원 scorer의 winner 검증은 J3d와 같다. 새로운 화음 종류나 미지원 철자를 발명하지 않는다. 장문3구간의 기존 cap/repeat 보류도 유지한다. streaming joint frontier는 이번에 구현하지 않았다.

## 3. 실제 재추론과 동일성 검사

| 구간 | J3d 시간 | 재사용 시간 | window 요청 | 실제 계산 | cache hit |
|---|---:|---:|---:|---:|---:|
| Beethoven quartet n06op18-6_02, `[167/2,175/2)` |90.420s|57.053s|988|249|739|
| Beethoven sonata07-2, `[105,109)` |30.971s|20.844s|630|159|471|
| 합계 |121.391s|77.897s|1618|408|1210|

실제 window 계산75%가량을 재사용했지만 전체 시간 감소는35.83%다. 공급자별 문맥 분석·catalog deep copy/검증·joint decoding 등은 여전히 남는다. 부분 비용 감소와 전체 실행 시간은 구별한다.

첫 `r1`은 native tuple과 봉인 JSON array를 Python 객체 equality로 비교해 `selected_prediction` 불일치라고 중단했다. 결과 값을 자동 채택하지 않았고 부분 산출물을 보존했다. JSON 계약의 정본 SHA 비교로 바꾼 `r2`에서 선택·cost·원14필드가 동일함을 확인했다. Tuple/list 차이를 허용한 것이며 pitch/time/ID/score 차이를 허용하지 않았다. 관련 물리 runner 검사에도 이 경우를 넣었다.

주석이 포함된 이전 report는 **72새 packet의 물리 SHA 봉인 이후** 처음 읽는다. 추론에는 score 관찰·동결 scope만 전달하며 reference를 넣지 않는다. 이후 별도 감사에서 모든72평가를 다시 계산하고 전체 metrics를 재현했다. 재추론2구간의 모든 catalog 출처 SHA가 동일했고, 각각 source-order quantile12개를 추가로 골라 **전체 provider 결과**를 기존 함수와 직접 비교했다(총24). 정답 일치에 따라 비교 구간을 고르지 않았다.

정본:

- [r2 report](../../../output/harmony-window-workspace-2026-10-04-r2/report.json), SHA `1e0e9257214015536b00e9282b12def7157cb47b26a4d853ca2646d3e59ce6ac`.
- [사후 감사](../../../output/harmony-window-workspace-2026-10-04-r2/diagnostics-r1/audit.json), SHA `9a5406bab32e29f49540d1505e2e024e2b2290e88b65b2c16dadb3446b3c2ba4`.
- [전체 source tie 감사](../../../output/harmony-window-workspace-2026-10-04-r2/source-tie-audit.json).

## 4. Claude가 알려 준 tie 문제의 점검

여기서는 DCML `notes.tsv`의 `tied=1/0/-1`을 걸러 만든 skyline으로 화성 sound를 만들지 않는다. TSV는 notated note의 onset/duration/MIDI 정렬을 검사하고, sound/tie는 **MusicXML→Canonical IR**에서 만든다. 따라서 musicomp의 “뒷음을 버리면서 앞음 음가를 늘리지 않음”을 그대로 공유하는 경로는 확인되지 않았다.

하지만 “문제가 없다”라고 일반화하지 않았다. 전체15package(보류 source 포함)의 multi-note sound512개를 검사해511개 연속 clock 통과/1개 불일치를 발견했다.

이상 사례: Chopin BI145-1op50-1의 C4. Source note는 `[190,192)`와 `[195,196)`인데 저장된 sound는 `[190,196)`다. Source reference는 m64 voice1와 m66 voice2를 가리키지만 normalized note에는 같은 voice ID가 있다. **중간3quarter를 건너 연결한 시간/원 성부 문제**이며 단순 tail 음가 누락의 반대 방향이다. 원본 표기와 parser voice/tie 정규화를 함께 재검토해야 하며 여기서 어느 표기가 정답인지 임의 확정하지 않았다.

- [전체 XML·전체 IR·원 note/source IDs·앞뒤 `[187,199)` 범위·진단](../../../output/harmony-window-workspace-2026-10-04-r2/diagnostics-r1/abnormal-ties/sound_8da98c2c5b56/case.json).
- 기존 source-bound clock 검사에서 `functional_clock_valid=false`, 직접 해결 link0, 해당 ornament neighbor 없음은 확인했다.
- **Raw 화성 exposure는 여전히 저장된 sound span을 사용한다.** 멜로디 해결 근거를 보류했다고 잘못된 지속 전체가 자동 제거되는 것은 아니다. 다음 source 품질 관문에 이 위험을 포함한다.
- 이 `[190,196)`는 이번 Chopin 동결5구간과 겹치지 않는다. 따라서 같은72평가 숫자가 유지된 것이 이 source 문제의 해결을 뜻하지 않는다. 원 Core·원XML·봉인 benchmark를 수정하지 않았다.

## 5. Claude 프레이즈 브랜치: 확인한 상태

사용자가 알려 준 기준은 `K:\MusicSearch-breath-layer`, branch `claude/phrase-breath-layer`, base `d9bca19c`, lower-only commit `984292cc`다. 검사 도중 상위층 변경이 완료되어 **`c6892608c984b59a6590f66904a15907ad3ef453`**로 새로 봉인됐다. 처음 두 파일의 미커밋 변경을 발견했으나 최종 점검 시 worktree는 clean이었다.

최신 커밋은 lower-only와 달리 새 파일만 추가한 상태가 아니다. 다음5파일에 변경이 있다:

1. `server/phrase-breath-layer.mjs`: 호흡층 + 상위층, DP·길이 prior·2마디 반복 시작·종지.
2. `server/phrase-breath-layer.test.js`: 5개 검사 정의.
3. `server/search-api.mjs`: `phraseLayers` 추가, neutral boundary로 기존 boundary harmony 호출.
4. `src/components/FullScorePage.tsx`: 비교 panel과 기존 preview 띠 연결.
5. `src/components/PhraseLayersPanel.tsx`: 비교 레이어 선택과 범위 목록.

`analyzePhraseBoundaries`, `boundary-harmony.mjs`, full harmony 함수 자체는 커밋 diff에서 변경하지 않았다. 새 API 호출의 추가 계산 비용은 별도 측정이 필요하다. 기존 search 결과/옛 phraseAnalysis 필드를 대체하지 않으며 구조 상성부가 다르면 기존 `structureWork=getWork(...)`와 `analysisWork`를 통해 해당 성부 결과를 사용한다. 이 연결을 코드로 확인했지만 실제 브라우저에서 모든 다성부 경우를 재현한 것은 아니다.

원 latest6파일 SHA를 전후 확인하고 read-only Node smoke5개를 통과했다. Vitest 전체 suite나 corpus 재평가를 실행한 것은 아니다. 원 worktree·main·Music Composition에 쓰지 않았다. Node child-process 생성 제한과 git 소유권 경고를 만나 shell의 별도 read-only git 호출을 사용했다. `safe.directory`는 해당 git 명령 한 번의 옵션만 사용했으며 글로벌 설정/ACL 변경은 없다.

## 6. 보고된 성능의 의미와 확인 범위

Claude의 개발 로그와 실제 JSON 보고서를 읽고 세 report의 값·원경로·SHA를 로컬 snapshot에 보존했다. 처음 오래된 `knowledge/data/phrase_layers.json`에는 상위층 개선이 한 fold에서 음수였으나, **최신 `reports/phrase_layers_final.json`과 `reports/layers_port_check.json`**에서 후속 종지 후보 개선을 확인했다. 오래된 결과와 최신 결과를 혼동하지 않는다.

| 평가 조건 | 최신 저장 수치/의미 |
|---|---|
| 코랄369곡 lower, 페르마타, ±1박 | 약0.77. 호흡층 성과이며 upper phrase 전체 정확도가 아니다. |
| 민요 Essen1500/MTC-ANN347/MTC-FS1500 | lower F1 각각0.778/0.799/0.674, 재조정 없이 적용했다는 외부 개발 기록. |
| DCML161악장, 기존 MusicSearch | F1 ±1박0.305 |
| 같은 DCML, JS upper 선율만 |0.366|
| 같은 DCML, JS upper + 현재 blind MusicSearch 종지 |0.371|
| 같은 DCML, JS upper + 주석 기반 종지 |0.389|

주석 기반 종지는 운영 시 추정해야 할 정보가 이미 주어진 조건이다. `0.389`를 현재 자동 화성 연결의 정확도로 보고하지 않는다. Blind 종지의 추가 이득은 저장 report에서0.005이며 선율/길이/반복 DP의 이득과 분리한다. 이 문서 작성자가 corpus를 재실행해 위 숫자를 독립 재현한 것은 아니다. 양식·층·정답 정의·tolerance·분할이 다른 결과를 단일 “프레이즈 정확도77%”로 합치지 않는다.

## 7. 통합 전 보완점과 합치는 방식

### 실제 코드/프로브로 확인한 점

- Upper `cadenceAt`는 type→`CADENCE_VALUE`를 점수에 쓰지만 전달받은 `strength`는 출력에만 남긴다. 같은 PAC를 strength0/1로 바꾼 synthetic 입력에서도 같은 경계가 선택되고 strength0의 PAC가 남는다. **현 API caller는 기존 `selectedCadence` 관문(대체로0.58 이상)을 거치므로 strength0가 현재 운영에서 그대로 들어온다는 뜻은 아니다.** 다만 미래 화성 엔진의 약한 후보/미확인 유형을 받을 때 type만으로 강한 종결 근거가 되지 않도록 contract를 명시해야 한다. 미보정 strength를 확률로 간주하거나 임의 곱셈으로 보정했다고 주장하지 않는다.
- `tieStop`/`isAttack=false`를 바로 직전 event에 붙이는 prepare는 다른 pitch/voice tail을 거부하지 않는다. 잘못된 pitch/voice tail과 음수 duration을 synthetic으로 주어도 예외가 나지 않았다. 현 indexed 논리 attack 입력이 이를 선행 보장하는지 확인하고 **source ID/pitch/voice/인접 clock을 검증한 adapter**를 두거나 engine에서 fail closed한다. 정상 sounding event를 이미 받았다면 tie를 두 번 누적하지 않는다.
- getWork는 notes 모두에 첫 마디의 meter를 부여하고, upper는 전역 key 가설을 받는다. 변경 박자·못갖춘마디·local-key 불확실성에 대한 입력 계약/회귀가 필요하다. 2/4/8마디 prior는 증거일 뿐 어느 작품에도 강제할 정답 길이가 아니다.
- Upper 후보는 lower 끝 **또는 별도 종지 지점**이므로 upper 경계가 lower 경계 집합의 부분집합이라는 보장은 없다. “호흡 단위 안에서만 상위 끝을 고른다”라는 panel 문구는 이를 정확히 설명하도록 수정하는 것이 좋다.

### 권장 합치기 순서

1. 위 최신 커밋을 기준으로 고정하고 **추가 비교 레이어**부터 도입한다. 기존 phrase/Motif/기둥음/피드백 ID·캐시 결과는 유지한다. 실제 병합은 별도 승인 후 수행한다.
2. 음표 index는 표시용으로만 쓰고, 새 결과에 `source_xml_sha256`, `ir_document_id`, `stream_id`, 원 attack/sounding/note ID, rational global `[start,end)`, 엔진 SHA/version을 묶는다. Source가 바뀌면 재분석/매핑 없이는 옛 feedback를 새 array index에 붙이지 않는다.
3. 화성→종지→upper는 버전이 붙은 읽기 전용 근거 연결로 한다. 종지 후보·대안·against·source note/span·미보정 강도를 전달하며 unresolved를 허용한다. Upper 선택을 다시 화성의 정답 경계로 넣는 feedback cycle은 금지한다. 쉼 단서 중복 제거는 현재 neutral boundary 방식의 장점이며 유지한다.
4. Lower/upper를 별도 평가한다. 현재 보고서와 함께 기존 사용자가 확인했던 pop Melody/Piano Solo 쌍, A Whole New World/Beauty and the Beast, 베토벤1·8번 소나타, tie·pickup·변경박자·반복 변형을 회귀 대상으로 삼는다. 작품 이름은 **시험 목록**이고 알고리즘 분기 조건이 아니다.
5. Feature flag로 기존/upper/breath를 선택하고 캐시 key에 새 layer version·source SHA·성부 정책·harmony/cadence version을 넣는다. 전체 화성 후보와 불확실성을 변경하지 않는다. 새 API의 지연·기존 검색 결과·뷰어 range/클릭 동기화를 확인한 뒤 default 교체 여부를 결정한다.

점검 정본: [읽기 전용 감사 + 원 평가 snapshot](../../../output/phrase-layer-integration-review-2026-10-04-r2/audit.json), SHA `32c1b1c2ea2c31e65475d9e0431f41f85a07d3aaec69f0faf4b63f6db14da95d`. 외부 코드6파일 불변/합성5PASS/추가 위험 probe를 구별해 저장했다. `r1`도 보존했으며 `r2`가 평가 보고서 snapshot까지 포함한 정본이다.

## 8. 재현과 다음

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m unittest test_harmony_window_workspace test_harmony_window_workspace_trial

$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_window_workspace_trial --source output/harmony-batched-frontier-2026-10-04-r1 --output output/harmony-window-workspace-NEW
.\.venv\Scripts\python.exe -B scripts/audit_harmony_window_workspace.py --root output/harmony-window-workspace-NEW
```

기존 output을 덮어쓰지 않으며 `NEW`는 새 경로여야 한다. 원 source/code/권한/split이 달라지면 pinned 비교를 거부한다.

다음 우선순위는 **장문 미분석 구간의 bounded/streaming 공동 탐색과 source-clock 관문**, 이어 과분할/과병합을 구별하는 일반 NCT·지속/교체·applied diminished 해결 점수다. 이번에는 시간 최적화와 통합 검토를 완료했지만 장문 복구·화성 정확도 상승·공개 모델 실행·독립 blind 평가·Claude main 병합·운영 UI 연결·생성 엔진 완료를 주장하지 않는다. 다른 사람이 수정 중인 코드·원주석·연구 사용 조건·원 corpus는 유지한다.
