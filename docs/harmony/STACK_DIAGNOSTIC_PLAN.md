# 단계105 — 주기적 스택 진단과 native 종료의 분리

## 범위와 종점

단계104의 6개 native 종료가 5초 스택 출력과 겹쳤다. 시간상 연관이지 원인 확정은 아니다. 이번에는 **악보 계산 없이** 표준 라이브러리만 사용하는 4개 짧은 비교를 각 1회 실행한다. 음악 규칙, 계수, 후보, parser, IR, 이전 결과 및 컴퓨터 설정을 바꾸지 않는다. 추가 전곡 실행과 정확도 채점은 하지 않는다.

## 사전에 고정한 비교

| 순서 | 작업 | 주기적 스택 출력 | 작업 시간 | process 전체 한도 |
|---|---|---|---:|---:|
| 1 | Fraction CPU 계산 | 5초마다 | 6.5초 | 12초 |
| 2 | 같은 CPU 계산 | 없음 | 6.5초 | 12초 |
| 3 | 대기 대조군 | 5초마다 | 6.5초 | 12초 |
| 4 | 대기 대조군 | 없음 | 6.5초 | 12초 |

순차 실행, retry 0이다. CPU 작업은 시간 동안 같은 유리수 kernel을 반복한다. 반복 횟수는 달라도 kernel의 결과와 검산 digest는 같아야 한다. 처리량을 화성 속도나 음악 정확도로 해석하지 않는다. 4개가 정상 종료해도 Windows/Python의 전체 안정성을 인증하지 않는다. 소유 tree 정리가 확인되지 않으면 남은 probe는 시작하지 않는다.

## 구현 경계

원103 bootstrap의 bytecode와 원104 atomic worker 연결을 그대로 사용한다. 새 모듈은 bootstrap의 **private faulthandler 의존성**에서 주기적 watchdog 호출만 선택적으로 끈다. fatal exception handler, nonce/PID/단조시각, phase checkpoint, 전체 process deadline, 원결과와 실행 상태의 분리는 유지한다. 전역 모듈 monkeypatch나 설치 파일 수정은 하지 않는다.

새 실행 adapter에서는 주기적 진단 기본값을 off로 두고 명시적 flag로만 켠다. 이것은 진단 출력 정책이지 음악 알고리즘 변경이 아니다. 이전 runner와 봉인 결과는 변경하지 않으며, 이번에는 새 adapter로 음악을 실행하지 않는다.

## 판단과 기록

최초 사전 검사 16개 중 프로세스 검사에서 1 FAIL과 1 ERROR가 발생했다. foreign fixture는 5초 전체 한도에 걸렸고 partial fixture는 worker.json이 없었다. 원검사와 한도를 바꾸지 않고 실패 r1을 보존한다. 이 시점에 예정 probe 실행은 0회다. 타이머가 없는 fixture에서도 실행 문제가 있으므로 원인을 타이머로 단정할 수 없다.

후속 r2는 process를 실행하지 않는 의존성·event 계약 10개, 원 atomic writer 4개, 새 진단 정책 8개를 먼저 검사한다. 이는 원16검사 전체 PASS를 대신하지 않는다. **기존 process 검사 실패도 이번 진단의 대상**으로 두고, 서로 다른 작업의 예정 12초 한도 4개 probe를 최초 실행한다. 5초 fixture 한도, 원60초 전곡 한도, 음악 코드는 변경하지 않는다. 원 process 실패 미해결 상태는 report와 최종 기록에 명시한다.

4개의 실제 exit code, 타이머 출력 수, fatal 표시 수, event 문제, kernel 검산, 실행 시간을 기록한다. timer-on만 실패하면 해당 조건의 재현 증거로 보고하되 원래 화성 실행의 native 원인을 확정하지 않는다. 재현하지 못하면 그대로 미재현으로 기록한다. 실패를 숨기거나 성공할 때까지 반복하지 않는다.

화성 개발 기록에 결과와 다음 큰 과제를 남긴다. UI/Claude 편곡 연결은 현재 실패 관문이 해결되지 않았으므로 계속 보류한다. Python의 `dump_traceback_later`가 watchdog thread를 사용하며 `enable`의 fatal handler와 별개라는 계약은 [Python 3.12 공식 문서](https://docs.python.org/3.12/library/faulthandler.html)를 따른다.
