# 단계104 — 원결과 보존 실행기로 고정6곡 한 번 비교

## 목적·종점

단계103의 새 실행기를 실제 전곡 계산에 연결한다. 원102 interval/source-context adapter 대 원101 compiled/control을 같은 실행조건으로 각1회 비교한다. **음악 규칙/계수/후보/점수/beam/한도는 수정하지 않는다.** 성공할 때까지 반복하거나234곡을 다시 실행하지 않는다. 전체분모 완료율/정확도·원선택경로 동등성·실행시간 분해·단일감사·별도개발기록으로 끝낸다.

## 고정 계약

- 기존 cohort:158 Reach For The Stars!,110 It_S A Small World,61 Family Of The Poor,156 Pledging My Love,211 Walking On Sunshine,59 Experience. 단계101 freeze의 source/title/index를 재사용한다. 크기로 고른 기존 개발6곡이며 독립 Test라고 주장하지 않는다.
- 2조건×6곡,4동시,각process 전체60초(준비/import/parse/infer/원직접검산/저장/종료 포함),retry0. 정리시간은 한도를 연장한 성공이 아니다. beam8/page12/2M과원99직접검산을 유지한다. partial/late/raw complete+timeout는 제출하지 않고 누락을6곡1848quarter 분모에 유지한다.
- 기본 Windows 조회 유지, OS-label opt-in **off**. 소유 자식tree 정리 때문에 승인된 실행환경을 사용한다. 동일권한 안의 두 조건은 비교가능하지만 과거 제한환경과 직접speedup을 주장하지 않는다.
- 원26모델 SHA `2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf`. 기존 봉인 baseline6곡을 재사용하며 baseline시간을 이번에 측정했다고 주장하지 않는다.
- 검사는기존전곡/입력/점수62·실행16·신규privatewriter검사4를 함께 수행한다. 실제 개수·failure/error·시간을 기록한다. preflight 실패 시 음악실행0,기존모듈의 설치/소스 변경0.
- 단일 신규writer adapter에서 원stage103 bootstrap bytecode를 유지하며 import_module의 **private** 의존성만 통해 원worker를 로드한다. 원phase worker/final wrapper의 `write`만 same-directory atomic JSON으로 연결한다. 원부모globals/infer/parser/provider는 수정하지 않는다. source/Core/음가/ID/철자/tie를 관찰계층에 그대로 보존한다.

## 원결과·실행 상태·평가 구분

각job의 `worker.json`, `worker.ir.json.gz`, `worker.catalogs.json.gz`, `worker.phases.json`은 원자료다. `execution.json`은 parent의 독립된 상태이며 원자료를 덮어쓰지 않는다. 정상종료/nonce·시각계약/raw complete가확인되고 sourceSHA/전체IR/원범위·span/전체catalog가검증된 결과만 제출한다. 이검증은 음악정답 검증이아니다.

모든실행끝→제출예측/원자료해시봉인→gold읽기/채점 순서다. worker에는gold/title/index를전달하지않고source경로만준다. hash는내용열람/정답대입이아니며새학습0이다. 원101의complete4경로/전체catalog·원96전체IR6개와대조한다. 공통완료0이면동등성passed=null로남기고빈검사성공으로쓰지않는다. raw complete이지만시간초과인경로의비교는별도진단으로만남긴다.

전체6/공통정상완료subset의근음·triad·구성음·베이스·경계F1/coverage를분리한다. 기존numerical gate와개발scope한계를함께보고한다. 일부case한개개선을운영/편곡연결의근거로쓰지않는다. UI/Claude/서버/Git/MusicSearch/Composition 변경0이다.

## 실행안전·다음 판단

최초 preflight에서71검사 중1error가 있었다. 음악 suite를 구성하면서 music21이 먼저 로드되어 새worker 전용 import 검사의 cleanup fixture가 fresh 조건을 만족하지 못했다. 음악 판정 오류는 아니다. 실패r1과 음악실행0을 보존하고 원103검사/구현은 바꾸지 않은 채 실행 순서만 분리한다. 기존62의 재현 목록에 빠진 test_harmony_test_a도 추가한다. std-only16을 먼저 실행하고 기존62+새4를 실행한 뒤 fresh output r2에서 음악 비교를 최초1회 수행한다.

stdlib bootstrap부터launcher/실제workerPID·nonce·단조시각을기록한다. 완성되지않은시간은null이다. 5초snapshot은함수별시간분포가아니고원인단서일뿐이다. 소유live PID tree만정리하며실패시대기job은추가실행하지않고미실행도분모에남긴다. 다른작업/OS/ACL/WMI설정은변경하지않는다.

정상전곡6완료가되면지표로큰음악오류를판단한다. 여전히긴곡timeout이면parse/catalog/search/검산/저장중큰병목하나를기록해다음단계로넘기고추가동일버전실행·계수/예산sweep은하지않는다. 점수·실패·next결정은화성개발문서에기록한다.
