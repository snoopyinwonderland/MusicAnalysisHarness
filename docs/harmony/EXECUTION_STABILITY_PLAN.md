# 단계103 — 실행 준비·분석·종료 분리, 결과 보존, 짧은 Windows 진단

## 범위와 종점

단계102의 원예측/코드/시험은 보존한다. 원음·IR/분석 규칙·점수·후보·계수·beam/60초 전곡 계약은 수정하지 않는다. 이번은 **whole-score 재실행이 아니라 stdlib 실행기 보완 + 음악 계산 없는 짧은 진단**이다. 기존64/234/6곡 정확도 평가를 성공할 때까지 반복하지 않는다.

확인된 call chain은 music21.common.misc.getPlatform → platform.system → Python uname → _get_machine_win32 → WMI다. 이전 로그의0x8007000e를 실제 시스템 RAM 부족 또는 process crash의 증명으로 쓰지 않는다. Python3.12.14 / music21 10.5.0의 설치 코드를 읽고 이 경로를 확인했다.

## 별도 실행 계약

- 음악 모듈을 import하기 전에 stdlib bootstrap이 실제 PID/부모PID·nonce·단조시각·runtime을 남긴다. 순서가 있는 JSONL의 마지막 불완전 행은 원문을 보존하고 미확인으로 다룬다.
- parent가 launch, module load, worker call, post-worker exit의 시간을 구분한다. 원phase sidecar의 parse/infer/검산/저장 시간과 결합할 수 있다. 미완료 단계는0초가 아니라 unknown이다.
- worker.json, phase/IR/catalog는 raw 자료로 남기고 execution.json은 별도 상태다. **timeout summary가 이미 나온 raw 결과를 덮어쓰지 않는다.** 전체 process가 한도 안에 정상 종료하지 않았다면 raw status=complete여도 prediction_eligible=false다.
- timeout 때는 이 실행기가 생성했고 아직 살아 있는 process만 정리한다. Windows의 venv launcher 자식도 같은 소유 PID tree로 정리하고, 다른 Python/Claude 작업을 이름으로 열거해 종료하지 않는다. cleanup 실패는 별도 보류로 기록한다.
- 준비시간을 제외하여 종전 완료율을 높였다고 말하지 않는다. full-process 시간과 한도는 계속 별도로 보고한다.

## opt-in OS-label 우회

Windows임을 sys.platform='win32', os.name='nt'로 확인할 수 있는 **새 worker 내부**에서만 사용한다. 설치 misc.py SHA `3d3ebec7d339132eb555f45fb8ec4e0518248cf34bfbb38b28b32f2636be778e`를 확인하고, 원 getPlatform bytecode의 private platform.system 의존성만 'Windows' 반환으로 연결한다. 원함수가 반환하는 music21 label='win'과 같다.

전역 platform.system/uname, 설치파일/환경설정/registry/WMI/ACL은 수정하지 않는다. 다른 플랫폼·설치 파일 변경은 원조회 유지, 이미music21이 로드된 프로세스에는 적용을 거부한다. 전체 CPU/OS 상세정보를 지어내거나 반환 cache를 임의채우지 않는다. 이 opt-in은 원음/화음 선택이 아닌 OS-classification 의존성에만 한정되고 운영 적용은 별도 input/selected-path 회귀가 필요하다.

## 제한 진단 순서

신규 stdlib/소유 process/결과보존/import binding 검사를 먼저 통과한다. 그 다음 아래4개를 sequential 각1회·재시도0으로 실행한다. 부모/실제workerPID를 따로 기록한다.

1. noop,5초: 음악 모듈 없는 baseline process 준비/종료
2. platform.system,10초: 독립 Windows WMI 호출 경로
3. opt-in engine import,15초: 먼저 실행하여 나중 default import보다 warm cache 이득을 의도적으로 주지 않음
4. default engine import,15초: OS-label/모듈 준비 비교

합계 process deadline45초 + bounded cleanup이며 분석/song/model/gold/Roman inference는0이다. parent log·정확한설치/새코드해시·원102 score/hash·raw traces·결과를 보존한다. 1회 import 차이를 전체 음악속도/정확도 개선으로 일반화하지 않는다. 이 진단과 기록으로 이번 단계를 끝낸다.

## 실행 전 권한 진단 — 최초 실패도 보존

제한환경의 preflight16개 중 자식 tree 정리 확인1개가 실패했다. `taskkill /PID <이 실행의 살아 있는 launcher> /T /F`는 exit1 / `ERROR: Access denied`였고 fallback으로 launcher 종료만 확인했다. 같은 환경의 단일 cleanup fixture에서도 이를 확인했다. 음악 import 진단4개는 아직0회다. 실패 validation과 원worker/별도 summary를 보존하고, 성공으로 덮어쓰지 않는다.

다음 실행은 승인된 비제한 환경의 fresh output에서 검사 후 예정4진단을 최초1회 수행한다. 다른 process를 열거·종료하거나 OS/ACL/WMI 설정을 수정하지 않는다. 이 권한 차이는 단계102의 제한환경 end-to-end 결과와 직접 속도 비교할 수 없는 요인이다. 이번 진단에서 label 우회와 default는 동일한 승인환경 조건으로 비교한다. 승인 환경에서도 cleanup 확인이 실패하면 남은 진단은 실행하지 않는다.
