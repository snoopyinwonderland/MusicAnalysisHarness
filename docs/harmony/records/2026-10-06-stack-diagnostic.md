# 단계105 — 주기적 진단 분리, native 오류는 짧은 비교에서 미재현

## 결과와 적용 상태

악보 없이 Fraction CPU 작업과 대기 작업을 주기적 진단 켜짐/꺼짐으로 각 1회 비교했다. **4/4 정상 종료, native 오류 0, kernel 결과 동일**이다. 단계104에서 관찰한 native 오류의 원인을 확정하지 못했으며, 전곡 안정화나 음악 정확도 향상을 주장하지 않는다.

새 worker adapter는 주기적 스택 출력만 기본 off로 두고 명시적 flag로 켤 수 있게 했다. fatal handler, phase/event 기록, 전체 process 한도, 원결과 보존은 유지한다. 원103/104 코드와 runner를 바꾸지 않았으며, 이번 새 adapter로 음악 분석을 실행하지 않았다. 화면·Claude 편곡 연결은 계속 보류다.

## 최초 사전 검사 실패도 보존

`output/harmony-stack-diagnostic-2026-10-06-r1`에서 기존16검사는 1 FAIL과 1 ERROR, 25.183352초였다. 예정4개 probe는 시작하지 않았다.

- `test_malformed_raw_and_foreign_event_are_not_eligible`: foreign fixture가 기대한 protocol error 대신 5초 전체 timeout으로 끝났다.
- `test_partial_timeout_never_promoted`: fixture의 worker.json이 없어서 FileNotFoundError였다.

이 fixture들은 주기적 타이머를 사용하지 않는다. 따라서 실행 문제가 모두 타이머 때문이라는 주장은 성립하지 않는다. 실패 fixture의 임시 폴더는 기존 test가 정리했으므로 내부 원자료를 이번 기록에서 확인했다고 쓰지 않는다. 검사 traceback과 실패 receipt는 r1에 보존했다. 준비 지연의 가능성은 있지만 두 실패의 원인을 확정하지 않았다.

후속 r2는 process를 실행하지 않는 기존 Binding/Event10, 원 atomic writer4, 신규 진단 정책8로 검사 범위를 분리했다. **22 PASS, failure0/error0, 2.953681초**, 부모 music21 import0이다. 이는 기존 process 검사2건을 해결하거나 원16 전체를 통과시켰다는 뜻이 아니다. 원 test·5초 한도를 바꾸지 않았다. r1 실패는 r2 report에도 `prior_failures_resolved=false`로 남겼다.

## 구현 원리와 검증

신규 `harmony_stack_diagnostic.py`는 원 bootstrap 함수를 private 의존성으로 연결한다. 원 function bytecode와 전역 faulthandler/importlib는 그대로다. 진단 off일 때는 watchdog 예약·취소만 하지 않으며 fatal handler의 enable은 원 함수 그대로 호출한다. on일 때는 원 `5, repeat=True` 예약과 finally 취소를 보존한다.

음악 action은 원104 `load_worker`를 통해 원 worker의 atomic writer만 연결한다. parser/infer/provider/계수/후보/beam/음가/철자/tie·ID를 수정하지 않는다. 실제 probe는 private stdlib worker를 연결하고 synthetic source label을 파일로 열지 않는다. 원 bootstrap의 nonce/PID/단조시각·event 계약은 동일하다.

신규8검사는 fatal enable 유지, on 예약 인자·취소, boolean 정책 검증, 원 bytecode/globals 보존, 기본 off의 event 흐름, 예외 뒤 timer 취소, CPU/대기 kernel 동일성, 잘못된 action/workload 거부를 다룬다. native 예외 처리 성공 자체를 합성 검사로 인증하지 않는다.

Python 문서상 [주기적 dump는 watchdog thread를 사용](https://docs.python.org/3.12/library/faulthandler.html#dumping-the-tracebacks-after-a-timeout)한다. 이번 원인 분리는 이 선택적 진단 경로와 음악 계산을 구별하기 위한 것이다. 문서가 이번 access violation의 원인을 설명한다고 주장하지 않는다.

## 사전 고정한 4개 비교의 실제 수치

순차 각1회, retry0, 작업6.5초, 준비·저장·종료 포함 전체12초 한도였다. 음악 입력/주석/gold 열람·음악 추론·채점0이다. 모델 파일은 내용 해석 없이 기존 SHA 보존 확인에만 사용했다.

| 작업 | 진단 | process 전체 | bootstrap 시작까지 | worker 호출 | 타이머 출력 | exit code |
|---|---|---:|---:|---:|---:|---:|
| Fraction CPU | on |10.349554초|3.532778초|6.505652초|1|0|
| Fraction CPU | off |9.109121초|2.403262초|6.547993초|0|0|
| 대기 | on |10.527761초|3.665395초|6.513293초|1|0|
| 대기 | off |7.184911초|0.573250초|6.505856초|0|0|

4개 총 wall37.489731초, event 오류0·access violation 표시0이다. CPU 반복은 on3033/off3364회였지만 같은 kernel 결과/digest이며 반복 횟수를 동등한 총작업량이나 속도 향상으로 주장하지 않는다. 준비 시간 차이가 크고 각 조건이1회뿐이다. on 조건은 5초 출력이 실제 있었으므로 단순 import-only 검사와는 다르지만, 각각 한 번의 출력만 확인했다. 장시간·다성부·여러 번의 출력에서는 여전히 미확인이다.

## 저장·감사·변경 보존

사전 계약: [STACK_DIAGNOSTIC_PLAN.md](../STACK_DIAGNOSTIC_PLAN.md). 신규 파일:

- `src/musicanote_harness/harmony_stack_diagnostic.py`
- `tests/test_harmony_stack_diagnostic.py`
- `scripts/diagnose_harmony_stack.py`
- 위 사전 계약과 이 개발 기록

원103/104 실행기·음악 모듈·고정 모델·원104 결과 및 정정 결과·r1 실패를 포함한135개 pin 확인은 불일치0이었다. hash 확인은 음악 품질 인증이 아니다. r2 실행 후 봉인된 코드/계획/원자료 변경0이다. 실패 전 검사 범위 교정 및 잘못된 문서 문맥으로 실패한 patch1회는 새 비교 실행 전에 정리했고, 실제 probe의 재시도는 없었다.

결과: [report.json](../../../output/harmony-stack-diagnostic-2026-10-06-r2/report.json), [audit.json](../../../output/harmony-stack-diagnostic-2026-10-06-r2/audit.json). 각 probe의 launch/policy/events/trace/worker/execution을 따로 보존했다. 최초 r1 validation도 삭제하거나 덮어쓰지 않았다.

이번에는 원악보 변경·음악 재추론·계수 학습·서버/UI/Git·MusicSearch/Composition 변경이 없다. 기존 tracked dirty5는 그대로다.

## 다음 큰 과제와 중단 기준

**기존 native 실패 악보 한 곡에서 같은 음악 코드의 timer-on/off를 각1회 비교**하는 것이 다음이다. 6곡/234곡 전체를 다시 돌리거나 음악 규칙을 늘리는 단계가 아니다. 사전에 고정한 한 곡·동일 후보/점수/한도·원IR/선택 경로 보존으로 진단 효과와 음악 실행을 연결한다. 이번 stdlib4 정상 종료만으로 과거 실패가 해결됐다고 쓰지 않는다.

한 곡에서도 원인이 좁혀지지 않으면 같은 비교를 계속 반복하지 않는다. 최소 재현·runtime 문제를 별도로 보존하고, 안정적으로 실행되는 범위와 남은 전곡 한계를 구분해 연구 엔진의 연결 판단으로 돌아간다. 화성 계수의 미세 조정으로 실행 실패를 덮지 않는다. 사람의 화성 해석 피드백이 필요한 단계는 아직 아니다.
