# 단계103 — 실행 상태·원결과 분리, Windows 준비 지연의 제한 진단

## 결론

실행기16검사와 음악 계산 없는4진단을 완료했다. 승인된 실행 환경에서는 기본 엔진 모듈도 0.748초에 로드됐고, `platform.system()`은 0.080초에 Windows를 반환했다. **단계102의 긴 준비 지연을 이번에 재현하지 못했다.** OS-label 우회는 같은 `win`을 반환했지만 기본보다 빠르지 않았다. 우회를 기본 채택하거나 WMI/샌드박스/메모리 부족을 유일한 원인으로 확정하지 않는다.

이번 성과는 계산·준비·종료 시간을 구별하고 시간 초과가 원결과를 덮어쓰지 않게 하는 별도 실행 계약이다. 전곡 처리 개선이나 화성 정확도 개선을 측정한 단계가 아니다. 현재의 Claude/편곡 연결 보류 판단은 유지한다.

## 문제와 구현

단계102에서는 Reach의 worker 내부 검산·저장이 끝났는데도 전체 프로세스가 60초를 넘었다. 기존 실행기의 timeout summary가 선택 경로 JSON을 대체해 결과 비교도 불가능했다. 원102 결과는 고치지 않고 다음 실행에 사용할 별도 모듈을 만들었다.

- `harmony_execution.py`: 음악 모듈을 로드하기 전 stdlib bootstrap, 실제 PID/부모PID와 launcher PID 분리, 실행별 nonce/순서/단조시각 JSONL, 준비·모듈 로딩·계산 호출·계산 후 종료 시간. 미완료 구간은 null이지0초가 아니다.
- `worker.json`은 원자료, `execution.json`은 parent 실행 상태다. timeout 시 원자료를 보존하며, 원자료에 complete가 있어도 한도 내 정상 종료·정상 event 계약이 아니면 제출 자격이 없다. 이 자격은 **실행 관문만**이며 음악 정확도/IR/생성 계약 검증을 대신하지 않는다.
- JSON 교체 실패 시 이전 파일과 pending을 보존한다. 불완전 event 행·잘못된 JSON·다른 nonce·순서/시각/PID 불일치는 별도 문제로 기록하고 정상 제출로 승격하지 않는다. launch 실패도 별도 summary를 남긴다.
- timeout 정리는 현재 실행기가 소유하며 아직 살아 있는 PID에만 한정한다. Windows venv launcher의 실제 자식 때문에 `/PID <owned-live-pid> /T /F`가 필요하다. 다른 Python/Claude 프로세스를 이름으로 열거하거나 종료하지 않는다. tree 정리 실패는 launcher 종료와 구별한다.
- `harmony_windows_import.py`: opt-in 새 Windows worker에서 설치 `music21.common.misc.py` SHA를 확인한 뒤 원 `getPlatform` bytecode의 private OS-label 의존성만 연결한다. 전역 `platform.system/uname`, 설치 파일·registry·ACL·WMI 설정은 변경하지 않는다. 이미 로드된 모듈은 거부하고 설치 코드 변경 시 원조회로 돌아간다. **현재 기본값은 꺼짐**이다.

원 score/Core/parser, 음표 ID/철자/음가/tie,26계수, 후보, NCT/점수, beam/예산/60초 전곡 계약은 수정하지 않았다. 음악적 판단에 관한 일반 규칙도 추가하지 않았다.

## 설치 코드에서 확인한 경로

Python3.12.14 / music21 10.5.0에서 `music21.common.misc.getPlatform → platform.system → platform.uname → win32_ver/_get_machine_win32 → _wmi_query → _wmi.exec_query` 경로를 확인했다. 음악 분석에 필요 없는 CPU architecture 조회가 OS label 준비와 연결될 수 있다.

단계102 trace의 예외 표시 뒤에도 계산 checkpoint가 이어진 사례가 있으므로 faulthandler의 Windows 예외 표시를 모두 실제 crash로 세지 않았다. `0x8007000e`만으로 실제 RAM 부족을 진단하지 않는다. 이번 진단은 이 경로의 존재와 제한된 실행 시간을 확인하며, 과거 지연의 인과관계를 입증하지 않는다.

## 실패와 실행 환경 차이

1. 첫 patch에서 없는 `tests/fixtures` 부모 디렉터리 생성이 실패했다. 부분 생성은 없음을 확인하고 fixture를 기존 tests 디렉터리에 추가했다.
2. 제한 환경의 최초16검사는15통과/1실패였다. 원결과 보존은 됐지만 Windows 자식 tree 정리 확인이 실패했다. 상세 메시지를 추가한 preflight도16중1실패이며, `output/harmony-execution-stability-2026-10-06-r1/validation.*`에 보존했다. **이때 예정4진단은 실행0회**다.
3. 별도 단일 fixture `harmony-execution-cleanup-cause-2026-10-06-r1`에서 taskkill exit1 / `ERROR: Access denied`를 확인했다. launcher 종료만 확인됐고 tree 정리는 미확인이다. raw worker의 complete와 notes는 보존됐고 prediction_eligible=false였다. 이 실패를 숨기거나 프로세스 tree가 종료됐다고 주장하지 않는다.
4. 컴퓨터 설정/ACL을 바꾸지 않고 승인된 비제한 환경으로 전환했다. fresh output r2에서 검사16개 PASS, failure0/error0·11.340715초다. 완성 raw+늦은 종료, partial+timeout, malformed raw, foreign event, 실행 실패, atomic 교체 실패, 설치 코드 drift/원전역 함수 불변을 검사했다. timeout fixture는 소유 tree 정리까지 확인했다.

권한 조건이 단계102와 다르므로 이전 60초 전곡 wall과 이번 import 시간의 차이를 같은 환경의 속도 개선으로 보고하지 않는다. 마지막4진단끼리는 같은 승인 환경·sequential·각1회·retry0이다. 우회를 먼저 실행하여 뒤의 기본 import보다 의도적인 warm cache 이득을 주지 않았다. 하지만 OS cache/부하 등은 통제되지 않았고4개의 반복 측정도 아니다.

## 실제4진단 — 음악 추론0

| 진단 | 한도 | 전체 process | 준비→bootstrap | 모듈 로딩 / 조회 | 결과 |
|---|---:|---:|---:|---:|---|
| stdlib noop | 5초 | 0.169274초 | 0.146199초 | 해당 없음 | 정상 종료 |
| platform.system | 10초 | 0.231514초 | 0.121841초 | 모듈0.006388초 / 조회0.080398초 | Windows |
| opt-in 엔진 import | 15초 | 1.311573초 | 0.123390초 | 모듈1.092262초 | win, 우회 적용 확인 |
| 기본 엔진 import | 15초 | 0.975451초 | 0.123873초 | 모듈0.747625초 | win, 우회 꺼짐 |

launcher/실제 worker PID는 각각48764/63680,67204/12580,36468/53692,42800/54620이었다. nonce/순서/시각/PID 문제0이며4개 trace 파일은0byte다. 분석 worker 호출·악보 읽기·모델 계수 학습·gold 평가·음악 추론은 하지 않았다. parent도 music21을 import하지 않았다. 4probe 완료는4곡 분석 완료가 아니며,16검사 PASS는화성 정확도 수치가 아니다.

우회 default 승격을 지지하는 증거가 없어 **기본 Windows 조회를 유지**한다. optional binding은 별도 진단 자산으로만 남긴다. 적용해 전체 음악 결과가 같다는 검증은 아직 하지 않았다.

## 저장과 단일 감사

사전 계약: [EXECUTION_STABILITY_PLAN.md](../EXECUTION_STABILITY_PLAN.md). 재현 script: [diagnose_harmony_execution.py](../../../scripts/diagnose_harmony_execution.py). 실행기가 동일 output 재사용을 거부하므로 재현할 때는 새 output을 지정한다. 재현 명령은 이번 실행을 반복하라는 지시가 아니다.

```powershell
& '.\.venv\Scripts\python.exe' -B 'scripts/diagnose_harmony_execution.py' --output 'output/<fresh-diagnostic-output>'
```

소유 process tree 종료 검사는 승인된 실행 환경에서 수행했다. 제한 환경에서는 Access denied가 다시 발생할 수 있으며 preflight 실패 시 음악 import 진단을 실행하지 않는다.

정본 output: [harmony-execution-stability-2026-10-06-r2](../../../output/harmony-execution-stability-2026-10-06-r2/report.json).

- `validation.txt/json`:16검사 결과
- `freeze.json`: 실행 전 코드/계약/설치 파일/단계102 결과482pin·계획4개·runtime
- 각 진단 `launch.json/events.jsonl/stdout.txt/trace.txt/execution.json`: 원 process·타이밍·상태·receipt
- `report.json`:4개 결과와 추론/정확도 미측정 선언
- `audit.json`: 실행 후482pin 불일치0·원102 score/audit/해석 보존·모든 출력 artifact SHA

report SHA `bf7dda0924e20fc1b2bb452aca55c08ceb36fee6f00593ddb71890b29d1d15d4`, validation SHA `68558846b4a1b846fcc700a7d2d1090a1eac1ca24d576bba4fbdfd13221967a7`, freeze SHA `fc060747b5e3af7bab8c48f458b4530f8e7595bf225d1be000a9466a8877a3c5`, audit SHA `2a6180fd338256bbdb0c931b85b0d7746e8ff4c1469dd225926a63b2f04ab66a`다. 감사 PASS는 음악 정확도/속도/운영 인증이 아니다.

## 다음 큰 단계와 중단선

새 실행기를 사용하는 **한 번의 전곡 실행 검증**이 다음이다. OS-label 우회는 끈 채로, source/전체IR/catalog/직접 검산을 유지하고 준비/분석/종료를 구별해야 한다. 원worker 선택 경로를 보존하여 같은6곡·원control·봉인 baseline의 완료율과 음악 지표를 다시 확인할 수 있어야 한다. 승인 환경 차이를 명시하고 새 실행 계약/version으로 사전에 고정한다.

이번에는 기존6곡/234곡을 다시 실행하거나 계수·beam·시간 한도를 조정하지 않았다. 다음에서도 import 우회 성공을 이유로 운영 채택하지 않고, 전체 분모에서 기준선보다 나은지로 연결 여부를 판단한다. 준비 지연이 재발하면 이 telemetry로 분리하고 동일 버전을 성공할 때까지 반복하지 않는다. 기존 화면 엔진/서버/Claude·MusicSearch·Composition 및 Git에는 변경이 없다. 기존 tracked dirty5도 그대로다.
