# 단계104 — 새 실행기로 고정6곡 비교, 원결과 보존·총길이 검증 정정

## 결론

기존6곡×2조건을 각1회 실행했다. 원음/IR·26계수·화성 후보/점수/beam·60초 한도는 유지했고, 원worker와 실행 상태를 별도로 보존했다. 최종 정정 기준 **새구현2/6·원control3/6·봉인baseline6/6 완료**다. 12작업 중6개는 실제 native access violation으로 종료됐고1개는 시간 초과였다. import는0.707–1.023초로 빨랐으며 이번의 가장 큰 실행 문제는 긴 준비 지연이 아니라 비정상 종료다.

공통 완료2곡의 원선택 경로·비용·특징·전체catalog는 원control·기존101과 같다. 그러나 그2곡에서도 triad는엔진77.63% 대기준선79.61%,경계F1은29.91% 대42.94%다. 전곡6분모에서는 triad12.77% 대기준선68.51%로 관문FAIL이다. 누락된 결과를 포함한 제출 점수이지 국소 화음 정확도가12.77%라는 뜻은 아니다. **실행 안정성과 음악적 우월성 모두 아직 입증되지 않았고 Claude/편곡 연결은 보류한다.**

## 구현 범위·검사

- 새 `harmony_owned_score_worker.py`는 원103 stdlib bootstrap bytecode를 그대로 사용한다. import_module의 private 의존성만 원interval/compiled worker를 로드하는 adapter로 연결하며, OS-label 우회는off다.
- 두 조건의 원phase worker/final wrapper에서 `write`만 same-directory atomic JSON으로 연결했다. 원모듈 globals, infer/parser/provider, 해석 라벨,계수/후보/점수는 수정하지 않는다. publication 실패 시 기존 완성 JSON과 pending을 보존한다.
- `run_harmony_owned_whole_score.py`는 source/title/index를 원101 freeze에서 가져온다. worker에는source만 전달하고gold/title/index는 전달하지 않는다. 전체12작업 종료→원자료/제출예측 봉인→gold읽기→채점 순서이며 새학습0이다.
- 원62검사·실행16·privatewriter4=**82검사 PASS**, failure0/error0·18.949334초다. 이검사 수는화성정확도가아니다. 보완 총길이validator4도별도PASS이며 음악 재실행은0이다.
- source/wholeIR/span/fullcatalog 계약은 음악정답 검증과 구분한다. 공통0의 동등성은null로 남기도록 했으며 이번에는 실제rawcomplete2쌍을 비교했다.

원source/Core/XML/음표ID·철자·음가/tie와 이전96–103봉인은 보존했다. raw worker, IR/catalog gzip, phase, stdout/trace, execution, parent status, 제출 JSON을 구분한다. timeout이 원선택 경로를 덮어쓰던 문제는 이 실행에서 발생하지 않았다.

## 사전검사 실패와 정정

최초r1은71검사 중1error로 음악실행0이었다. suite 구성 때 music21이 먼저 로드돼 ‘새 프로세스 전용 import’ 검사의cleanup fixture가 fresh 조건을 만족하지 못했다. 원103검사/실행기는 바꾸지 않고 std-only16을 먼저 실행하도록 **신규runner의 검사 순서만** 고쳤다. 기존62목록에서 빠졌던 `test_harmony_test_a`도 추가했다. 실패r1 validation은 보존하고 fresh r2에서82PASS 후 음악계산을 최초1회 수행했다.

초기조회에서 PowerShell literal wildcard rg 오류와 없는복수형 phases script 조회도 있었다. 파일목록으로 실제 경로를 확인했으며 분석/파일변경은 없었다. 문서에 잠시 혼입된 다른 언어 문장은 본실행 전 한국어로 교정했다. 본실행freeze 뒤 신규runner/worker/plan/test는 수정하지 않았다.

## 실제12작업 — 동일승인환경·4동시·60초·재시도0

소유 자식tree를 정리할 수 있는 승인환경을 사용했다. 다른 Python/Claude 작업을 열거·종료하거나 컴퓨터 설정/ACL/WMI를 수정하지 않았다. 두 조건은 같은권한·같은bootstrap·같은5초 stack snapshot을 사용했지만 과거 제한환경/20초snapshot과 직접적인speedup 비교는 하지 않는다. 전체비교 wall은78.985178초다. baseline은기존봉인예측이며이번실행시간이아니다.

| 작품/index | native 셀 | 새구현 전체process | 원control 전체process | 최종제출 상태 |
|---|---:|---|---|---|
| Reach For The Stars! /158 | 88 |3.204984초 정상|3.195372초 정상|양쪽완료|
| It_S A Small World /110 |188|9.364831초 정상|9.283061초 정상|총길이검증 정정 후 양쪽완료|
| Family Of The Poor /61 |294|5.194873초 native종료|5.152675초 native종료|양쪽결과없음|
| Pledging My Love /156 |603|10.182117초 native종료|36.531203초 정상|control만완료|
| Walking On Sunshine /211 |1006|15.181588초 native종료|5.146609초 native종료|양쪽결과없음|
| Experience /59 |1623|20.177281초 native종료|60.277216초 timeout/소유tree정리|양쪽제출없음|

Experience control의60.277초는한도 뒤 bounded cleanup 포함이다. 한도를연장한정상완료로세지않는다. taskkill exit0·stopped/tree_cleanup_confirmed=true,원phaseJSON이유효하게보존됐다. 부분예측을제출하지않았다.

## 새로 확인한 실행 문제 — 원인 확정과 관찰 구분

6개의비정상종료는returncode **3221225477 (0xC0000005)**다. 이전102처럼faulthandler 문구만본것이아니고이번에는실제비정상process exit를확인했다. traceback에 `Windows fatal exception: access violation`이있고 종료가대체로bootstrap의5/10/15/20초 snapshot 시점과겹친다. Fraction 연산/score context등Python frame 출력이중단된흔적도있다.

**timed traceback 경로가의심되지만인과관계는아직입증하지않았다.** 동일timer가있어도SmallWorld와Pledging control은정상진행했고,Experience control은12snapshot을남기며60초까지계산했다. 따라서timer가반드시crash를일으킨다고단정하거나,음악규칙/캐시/메모리부족/Windows권한을원인으로확정하지않는다. 부분snapshot은함수별시간분포가아니다.

원worker 호출이끝나지않은6crash/1timeout의worker_call_seconds는null이다. 0초나이미끝난것으로기록하지않았다. 가장중요한추가단서는다음과같다.

- Family 양쪽:294셀중마지막checkpoint64셀·12catalog. parse는control0.431/새0.377초,음악계산중종료했다.
- Walking control:parse시작만남아종료. 새구현은parse1.790초후마지막160/1006셀·30catalog에서종료. 이번부분실행의전체IR동등성을인증하지않는다.
- Experience 새:parse1.698초,마지막480/1623셀·62catalog. control은parse2.133초,마지막1152/1623셀·142catalog,검색consume누적36.931초/catalog12.592초다. 서로진행범위가달라단순속도비율로사용하지않는다. 원직접검산/최종저장에못도달했다.
- 정상Reach/SmallWorld의계산후종료는약0.14–0.24초,Pledgingcontrol0.337초다. 완성값을저장하고도수십초종료지연이생기던현상은이번정상5작업에서관찰되지않았다.

이판단은‘화성코드는잘됐다’가아니다. 안정적으로완성하지못한음악범위는여전히모르며,정상2곡의음악수치도기준선을앞서지못했다.

## 총길이 validator 오류 — XML/예측 수정 없이 읽기 전용 정정

SmallWorld의원IR `score.duration_quarters=191`이지만마디actual끝을포함하는원parser 계약의전체길이는 **194**다. 원 `harmony_test_a.read_score`는다음식을사용한다.

```text
total = max(score.duration_quarters,
            each measure.global_start_quarter + actual_duration_quarter)
```

새parent validator가score metadata의191만읽어정상worker의194와비교한것이오류였다. 양쪽원worker는한도내exit0/complete,전체IR 모든필드동일·sourceSHA동일이고실제범위194를그대로사용했다. XML오류나음가를바꿔야할문제가아니며,기존parser의범위를늘린것도아니다.

원runner/status/score/raw를보존하고 별도 `audit_harmony_owned_results.py`가원식으로재검증했다. 전체마디끝·score release·Fraction·빈measure목록4검사PASS다. 음악재실행/새추론0·원예측수정0이다. SmallWorld두정상결과를수용한**정정score/status/제출예측**을새폴더에봉인한뒤기존6곡gold로채점했다. 최초숫자새1/control2와정정후새2/control3을구분한다.

## 정확도·동등성 결과

고정6곡전체gold분모는1848quarter다. 같은분모에crash/timeout/누락을포함한다. 다음은정정후수치다.

| 지표 | 새구현 | 원control | 봉인기준선 |
|---|---:|---:|---:|
| 전곡완료 |2/6|3/6|6/6|
| 근음 시간일치 |12.88%|22.28%|71.00%|
| 근음+3화음 종류 시간일치 |12.77%|21.47%|68.51%|
| 구성음집합 시간일치 |11.96%|18.89%|57.90%|
| 베이스 시간일치 |9.39%|18.00%|71.43%|
| coverage |16.29%|29.92%|99.89%|
| 경계F1 |10.94%|24.24%|59.75%|

원최초score의새triad6.06%/control14.76%는검증오류로SmallWorld를제외한수치이며정정score가현재해석이다. 최초score는삭제/덮어쓰지않았다. gateFAIL과개발scope도유지했다.

공통정상2곡만보면엔진=control의root78.29%/triad77.63%/경계F1 29.91%,기준선root81.58%/triad79.61%/경계F1 42.94%다. 작은subset이라우월성/일반화성능을인증하지않는다. NCT·Roman·국소조성·전위·종지·생성성능정확도는이번채점대상이아니다.

Reach/SmallWorld원경로·pageinventory·비용·특징/availability·harmonic run·state손실·operations·spans·전체catalog가현재control·원101과같다. 기존equivalence파일의timely_complete_pairs=1은총길이정정전부모판단이다. raw_complete_pairs=2는실제비교였으며정정후두쌍모두정상제출자격이다. 추가읽기전용대조에서Pledging control도기존101과모든FIELDS/catalog동일이었다. 완료한unique3곡의전체IR은원96봉인과모든필드동일이다. 나머지3곡의이번완성경로는없으므로추정해채우지않는다.

## 산출물·감사·재현

사전계약 [OWNED_WHOLE_SCORE_PLAN.md](../OWNED_WHOLE_SCORE_PLAN.md). 신규파일은worker/주runner/별도정정audit/test2/plan/이기록이고원103및음악코드를변경하지않았다.

- 최초검사실패: `output/harmony-owned-whole-score-2026-10-06-r1/validation.*`
- 단일원실행: [r2 score](../../../output/harmony-owned-whole-score-2026-10-06-r2/score.json),freeze/validation/statuses/prediction-freeze/equivalence/audit·각job의원worker/IR/catalog/phase/event/execution/trace
- 현재정정해석: [correction-r1 score](../../../output/harmony-owned-whole-score-2026-10-06-correction-r1/score.json),corrections/source-clock검사/정정statuses·예측/execution-diagnosis/audit

본실행639pin·정정감사652pin 불일치0,PASS다. 원코드/원source/원예측/raw/status/score 전부보존,본실행freeze뒤코드수정0·정정새코드도실행뒤수정0이다. 감사PASS는음악정답/안정성/속도인증이아니다.

원score SHA `c3578fa1b451db5c968a299a0036bfcc8a87f77858e783c90d1ebc56583d6d6a`,원audit SHA `a16f5ff4586d01a7d4bfeac4bf25508b06be860aa1c8f1a38a29d86862a0194f`다. 정정score SHA `c18ffb4c9cff5e6be01aeb414db4a0c0e60872060c682adbec3ffc0e8552e425`,정정audit SHA `d807ad4ddc9f72b0e8ebc6c9923acafebf9248936241722590f3127881ed431e`다.

```powershell
& '.\.venv\Scripts\python.exe' -B 'scripts/run_harmony_owned_whole_score.py' --output 'output/<fresh-run>'
& '.\.venv\Scripts\python.exe' -B 'scripts/audit_harmony_owned_results.py' --output 'output/<fresh-read-only-correction>'
```

첫명령은원봉인runner라SmallWorld validator오류도재현할수있다. 이번실행을반복하라는지시가아니며수정본없이운영사용하지않는다. 정정script는고정r2를읽고음악추론하지않는다. 새whole-run validator는후속버전에서원source식으로연결해야한다.

## 다음 큰과제·보존 범위

**native access violation을음악오류와분리하는짧은실행검증**이먼저다. timed traceback 경로의안전성을분리해확인하고이미있는phase/event telemetry를유지하면서asynchronous stack snapshot을선택적으로제외할수있어야한다. OS-label우회/계수/beam/시간한도조정으로덮지않는다. 이번에는추가6곡/234곡재실행이나runtime/컴퓨터설정변경을하지않았다.

실행이안정화된뒤에만같은원규칙의전곡완료율과기준선차이를평가하고,그결과로큰화음오류개선또는연구보존/연결을판단한다. 지금사람의화성해석피드백이없어서진행못하는단계는아니다. UI/Claude편곡/API/서버/Git 및MusicSearch/Composition변경0,기존tracked dirty5도그대로다. 장기작곡/편곡목표를완료했다고주장하지않는다.
