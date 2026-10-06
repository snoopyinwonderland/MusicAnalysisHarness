# 단계102 — 원 성부·NCT 조회 최적화, 전곡 실행 지연으로 성능 확인 보류

## 결론

일반 성능 adapter를 구현했다. **합성 62검사 PASS·실제 고정6곡 전체 IR 원본과 모든 필드 동일**이다. 그러나 전곡 비교는 새 구현0/6 완료·기존101 control1/6 완료로 끝났다. 같은 원 control이 이전4/6에서 이번1/6이 됐고 모듈 로딩·Windows 플랫폼 WMI 예외가 양쪽에 나타났다. 코드 동등성 검증과 실행 안정성·속도·음악 정확도 검증을 구별한다.

이번 end-to-end 제출 성능이 낮아진 사실을 숨기거나 실패곡을 제외하지 않는다. 그렇다고 이것을 음악 판정 규칙의 퇴행으로 단정하거나, 실제 속도가 향상됐다고 발표하지 않는다. **운영/화면/Claude 편곡 연결 보류, 추가 계수/음악 규칙 실험 없음**이다. 같은 버전의 전곡 재시도를 하지 않고, 다음 우선 과제는 프로세스 준비 시간과 분석 시간의 구분 및 실행 지연 원인 확인이다.

정본 산출물:

- [사전 계약](../WHOLE_SCORE_INTERVAL_PLAN.md)
- [입력6곡 전체 IR 대조](../../../output/harmony-whole-score-intervals-2026-10-06-r1/inputs/audit.json)
- [전체 예측 채점](../../../output/harmony-whole-score-intervals-2026-10-06-r1/comparison/score.json)
- [실행 상태](../../../output/harmony-whole-score-intervals-2026-10-06-r1/comparison/statuses.json)
- [원결과를 수정하지 않는 해석 보충](../../../output/harmony-whole-score-intervals-2026-10-06-r1/comparison/execution-interpretation.json)

## 1. 문제와 실제 코드 변경

단계101에서 Walking의 Voice context 트리 구축과 Experience의 조건부 NCT 전체 패턴 Fraction 교차 조회가 스택에 나타났다. 그 두 병목만 다룬다.

### 정적 입력 성부 문맥

`harmony_context_input.py`의 VoiceLookup/ContextBuilder를 추가했다. production `canonical.py`는 변경하지 않는다. 원 CanonicalIRBuilder.build bytecode의 `_voice_id` 의존성만 private binding으로 바꾼다. time, measure, ID, tie, staff 및 FormalIRAdapter는 원 함수 그대로다.

중요한 발견: Walking importer는 현재 score tree 안에 Voice가0개지만, note/chord의 원 site에 Voice가 남아 있다. 따라서 tree에 Voice가 없다는 이유로 `voice_0`를 일괄 반환하는 shortcut은 폐기했다. 현재 site와 derivation에 대한 기본 검색 순서, sortTuple, wellFormed, context 반환 객체의 activeSite 동작을 그대로 유지한다. **한 번의 정적 score build 동안** 같은 site/flatten의 Voice 검색 tree만 재사용한다. build 뒤 lease를 해제한다. offset/stream을 편집하면서 쓰는 범용 캐시가 아니다.

설치된 music21은10.5.0이고 기본 getContextByClass source SHA는 `a9f4e0ac5912e9012177174d2a60d8c11289ded2b47dc1783eadb20545914e86`이다. 이 함수 SHA가 바뀌거나 element가 context 메서드를 override하면 원 `_voice_id`로 fallback한다. 다른 버전의 모든 helper 동작까지 안전하다고 인증한 것은 아니다. 정적 입력과 해당 런타임에 한정된 연구 adapter이며 운영 배포에는 추가 corpus 회귀가 필요하다.

### 시간구간 NCT 후보 조회

`harmony_whole_score_intervals.py`의 PatternIntervals/IntervalSearch를 추가했다. 원 RemainingFeatures가 만든 패턴을 모두 보존하고 start 정렬 + subtree max-end로 겹칠 수 없는 행만 건너뛴다. Fraction 자체를 반올림하지 않고 원 point의 정수 순서만 쓴다. 원순서·중복·긴 음·동시음·반열린 두 부등식이 유지되며 비-grid/누락 endpoint는 원 Fraction 전수조회로 fallback한다.

passing/neighbor 판정, 약박·전후음·같은 성부·범위·구성음 조건, credit, unknown, 고정26계수는 바꾸지 않았다. NCT 분류 정확도 개선이 아니라 기존 후보의 계산 비용 개선이다. beam8·2M·page12·원 전체 catalog/provider validation·source-clock/grace·독립 stage99 UnitScorer의 최종 전체 직접검산을 유지한다.

두 최적화를 함께 비교했으므로 실제 속도 효과가 확인되더라도 성부 lookup과 NCT index 각자의 기여를 따로 인증한 것은 아니다. consumer IR deepcopy는 이번에 바꾸지 않았다.

## 2. 검사와 원 입력 대조

실행 전 신규8+기존54=**62검사 PASS**, 6.494초다.

- current/external/derivation Voice, custom override·런타임 fallback, 새 build의 lease 분리
- note/rest/tie를 포함한 legacy IR 전체 일치와 원 source bytes 보존
- seed102 무작위90패턴+중복의 전 query pair, triplet Fraction·역순/동일좌표·비-grid fallback
- 긴 겹침·쉼·경계·zero-length의 **원 predicate 의미** 보존
- 실제 양수 passing/neighbor credit, 전 span/후보 특징과 비용 동일
- budget exhaustion, frontier/동점/손실/최종 원직접검산
- 전체 catalog·source IR 불변성

최초 신규검사1FAIL은 attached copied-note의 derivation을 항상 Voice로 찾을 것이라는 test 기대가 잘못된 것이었다. 원/새 실제 결과는 이미 같았다. 기본 context가 attached score의 top-level derivation을 따르는 경우 `voice_0`도 보존하도록 test를 바로잡고, unattached copied note에서 origin Voice가 검색되는 검사도 추가했다. 음악 코드나 원 parser를 이 FAIL에 맞춰 바꾸지 않았다.

그 다음 새 입력만 별도 process로 곡당60초, 각1회 파싱하고 단계96에 봉인된6개의 전체 IR과 비교했다. 새 source facts와 모든 top-level field·canonical JSON hash가 동일했다. gold/화성 주석은 읽지 않았다.488 pin 감사 PASS·불일치0이다.

|곡|새 파싱/변환 내부 초|Voice 호출|tree build / hit|전체 IR 일치|
|---|---:|---:|---:|---|
|Reach For The Stars!|0.165|130|116 / 534|동일|
|It's A Small World|0.266|307|200 / 1335|동일|
|Family Of The Poor|0.337|431|184 / 1971|동일|
|Pledging My Love|0.793|815|264 / 3811|동일|
|Walking On Sunshine|2.200|1736|680 / 8000|동일|
|Experience|2.908|2621|460 / 12645|동일|

이 표는 단독 parse-only 내부 시간이다. 비교 arm의 end-to-end 시간이나 독립 정확도 수치가 아니다.6곡 모두 fallback0이었다. 원 score/Core/entity ID 계약의 변경0이다.

## 3. 전곡 비교의 실제 결과

control=단계101 CompiledSearch+원 read_score, engine=새 ContextBuilder+IntervalSearch다. 양쪽 같은 atomic checkpoint·20초 stack,60초 whole-process 한도·4동시·각1회·재시도0이다. 전체 runner182.975846초/exit0. baseline은 단계99에 봉인한6곡 제출을 재사용했으며 이번에 baseline 시간을 재측정하지 않았다.

|곡|control 전체 process 초 / 상태|engine 전체 process 초 / 상태|
|---|---|---|
|Reach For The Stars!|58.673 / 완료|60.394 / timeout|
|It's A Small World|60.180 / timeout|60.204 / timeout|
|Family Of The Poor|60.146 / timeout|60.126 / timeout|
|Pledging My Love|60.421 / timeout|60.144 / timeout|
|Walking On Sunshine|60.074 / timeout|60.146 / timeout|
|Experience|60.124 / timeout|60.084 / timeout|

제한 시점 외 process 정리 시간 때문에 wall이60초를 조금 넘는다. 한도를 연장한 것은 아니다. 전곡 제출 완료는 **engine0/control1/baseline6**이다. 이전101은 같은 control4/6이었으므로 당시와 이번 숫자를 직접 속도 배수로 비교하지 않는다.

### Reach의 특별한 실행 상태

engine의 마지막 atomic phase checkpoint는 **worker 내부 완료**이고 총5.205초, parse0.677·infer4.121·최종 직접검산/전체 IR·catalog 저장을 마쳤다. 그러나 whole-process가60초 안에 끝나지 않아 runner는 제출에서 제외했다. control 내부12.981초 대 process58.673초다.20/40초 스택의 importlib 로딩은 phase 측정 시작 전 지연이 컸다는 근거다. process wall에서 마지막 phase elapsed를 뺀 값에는 준비/종료/마지막 checkpoint 뒤 시간도 들어가므로 전부 import 시간이라고 단정하지 않는다.

원 fullIR와 catalog gzip bytes는 engine/control/이전101 세 조건 모두 동일했다:

- IR gzip SHA `2c128cca96e82dd00c0ce78783ff1dee7b6f3820ed002ebb1c588aaa466f7348`
- catalog gzip SHA `0ca2d422f7f70e8920ff01402c1a8a6f3bfa214afec4402fb9c9155b68b9aec3`

하지만 runner의 timeout summary가 worker 결과 JSON을 대체하여 **이번 engine의 selected-path JSON은 보존되지 않았다**. 전체 IR/catalog와 phase/trace는 남아 있다. 이것을 새 승자 경로 동등성 증명으로 바꾸지 않는다. 후속 runner는 timeout일 때 이미 나온 worker receipt도 별도 파일로 보존해야 한다.

### 긴 곡의 마지막 기록

Walking engine: parse5.737초, 마지막 checkpoint96/1006셀·17catalog, 검색 누적13.817초. control은 parse 시작만 남았다. Experience engine: parse9.689초, 마지막96/1623셀·14catalog·검색15.659초, control 마지막32셀·7catalog·검색16.311초다. checkpoint 사이에도 진행하므로 이것이 마지막 실제 처리 셀 수의 정확한 상한은 아니다. 서로 처리량/phase 시작 시각이 달라 단순 속도 배수로 발표하지 않는다.

## 4. 실행 안정성 문제와 판정 한계

12 trace 중10개에 Windows exception 표시,6개에 플랫폼 `_wmi_query`와`0x8007000e`,8개에 importlib marker가 있었다. 일부는 `access violation`도 표시했다. **faulthandler 표시 후에도 checkpoint가 진행된 경우가 있다.** 따라서 모든 표시를 process crash로 세지 않는다. runner가 실제 분류한 process_error는0, timeout11, 완료1이다.

이 기록만으로 실제 시스템 RAM 부족, 디스크/보안 프로그램/다른 작업/샌드박스의 어느 것이 원인인지 확정하지 않는다. 순수 화성 계산 문제로만 설명할 수도 없다. 기본권한 Win32_Process 조회는 액세스 거부였고, 별도 읽기전용 승인 조회에서 이번 output marker를 가진 남은 Python process는0개였다. 다른 Python 작업이 관찰됐지만 출처·원인으로 단정하거나 종료하지 않았다. 컴퓨터 설정·ACL·보안 예외·실행 환경 변경0이다.

`equivalence.json`의 passed=true는 **공통 완료곡이0개여서 불일치가 없다는 빈 검사 결과**다. 실제 winner equivalence를 증명한 PASS가 아니다. 이를 명시하는 execution-interpretation.json을 추가했고 원 봉인 결과는 수정하지 않았다. 합성 동등성과6곡 입력 동등성이 확인된 것과 별개로, 실제 새 전곡 승자 비교는 미확인이다.

## 5. 채점과 연결 판단

두 예측과 봉인 baseline을 먼저 고정하고 그 뒤 gold 채점했다. 고정6곡·1848quarter 분모를 유지한다.

- engine: 제출0곡, root/triad/pcs/bass/coverage0%. 국소 화음 품질0%를 측정했다는 의미가 아니다.
- control: 제출1곡, root/triad6.06%, coverage6.06%, 경계F1 5.58%.
- 봉인 baseline6곡: root71.00%, triad68.51%, coverage99.89%, 경계F1 59.75%.
- 연결 관문 FAIL/`do_not_connect`. 공통 완료0곡이므로 음악 품질 동등 비교는 불가능하다. 독립 Test/234곡/공개모델 비교/국소조성·전위·NCT accuracy 인증이 아니다.

## 6. 파일·재현·감사·보존

신규 source/검사/사전 계약:

- `src/musicanote_harness/harmony_context_input.py`
- `src/musicanote_harness/harmony_whole_score_intervals.py`
- `scripts/run_harmony_whole_score_intervals.py`
- `tests/test_harmony_whole_score_intervals.py`
- `docs/harmony/WHOLE_SCORE_INTERVAL_PLAN.md`

별도 개발 기록/현재 상태를 이 문서, 화성 README와 DEVELOPMENT_LOG에 기록한다. 인수인계 문서나 구조 개발 로그로 대체하지 않는다.

```powershell
$env:PYTHONPATH = 'K:\Music Analysis\src;K:\Music Analysis\tests'
& '.venv\Scripts\python.exe' -B -m unittest test_harmony_whole_score_intervals test_harmony_phase_checkpoint test_harmony_whole_score_compiled test_harmony_whole_score_fast_positive_roles test_harmony_whole_score_fast test_harmony_whole_score_units test_harmony_whole_score test_harmony_whole_score_diagnosis test_harmony_test_a
& '.venv\Scripts\python.exe' -B scripts/run_harmony_whole_score_intervals.py --audit-inputs --output output/harmony-whole-score-intervals-2026-10-06-r1/inputs
& '.venv\Scripts\python.exe' -B scripts/run_harmony_whole_score_intervals.py --output output/harmony-whole-score-intervals-2026-10-06-r1/comparison
```

현재 output은 이미 존재하며 다시 실행하면 덮어쓰기 거부한다. 위 명령은 재현 절차 설명이지 이번 동일 버전 재실행 권고가 아니다.

사후514 pin 감사PASS/불일치0. 본 비교 시작 이후 신규 source/검사/계획/runner 수정0이며 입력·prediction의 SHA를 유지했다. 원source/Core/주석/모델·단계96–101·기존tracked dirty5·MusicSearch/Composition/서버/화면/Git를 보존했다. 새fit/API/commit/push0. 최초test의 기대 교정, 기본 WMI 권한거부, 결과조회용 inline Python 문자열 구문 오류1건도 이력에 남긴다. 후자는 실행 전 SyntaxError이며 결과 파일 변경0이다.

해시:

- 입력 audit `5d79257e7e59788a82cf8ea9707695c2960b04cdffd07a3ef1433c628ef8dec7`
- score `095456ba4630b0beb5b70a9d1acd03efaec5b03e6f748b3d21946305eac6de78`
- audit `e7c565b121d54a42500f31698b72761728931dfd217a567a92b86d8c0ccbd90d`
- equivalence `91d6f03df73fce068ae19a9f16fcb269418073ef250ce98ff6eb9183ed112f68`
- statuses `16cc8f903805182e8382c680b7d2a5307ff1549bd663f944a05481e85f0bbf8a`

## 7. 다음 큰 단계

1. 화성 계수/규칙을 바꾸지 말고, process 생성→모듈 준비→parse→infer→검산→저장→process 종료를 각각 기록한다. 시작/종료 지연과 음악 계산 timeout을 구별하되 end-to-end 완료율도 계속 보고한다.
2. Windows 플랫폼/WMI 예외와 실행 부담을 읽기 전용으로 진단한다. 외부 작업 중단·보안/ACL 변경은 자동 수행하지 않는다. 필요한 경우 원인과 요구되는 조치를 먼저 설명한다.
3. runner에 worker PID/준비 시각과 timeout 전 원 worker-result 별도 보존을 추가한다. 다른 작업의 종료나 시간 초과 결과 복구 제출은 하지 않는다.
4. 안정적인 실행 계약이 확인된 뒤에만 별도 버전의 제한 비교를 결정한다. 현재0/6을 성공으로 재분류하거나 같은 조건을 성공할 때까지 반복하지 않는다. 충분한 전곡 완료와 기준선 우위가 확인되기 전 Claude 연결은 하지 않는다.
