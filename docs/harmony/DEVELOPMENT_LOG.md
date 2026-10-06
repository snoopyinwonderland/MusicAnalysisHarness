# 화성 분석 개발 로그

## HARM-DEV-20261006-CLOSE — 연구 엔진 v1 평가 마감

사용자의 마무리 요구와 최초 세 단계 계획을 기준으로 연결 관문 FAIL을 최종 판단으로 삼았다. 원105 뒤에 예고한 악보 timer 비교는 실행하지 않고 추가 계수/전곡/runtime 실험을 이어가지 않는다. IR·출처·규칙·실패/검증 기록은 보존하며 기존 화면용 엔진은 변경하지 않는다. 현재 새 작업은 저장소 통합이다. [마감 결정](records/2026-10-06-v1-closeout.md).

## HARM-DEV-20261006-105 — 주기적 스택 출력 분리·stdlib 비교 미재현

- **구현:** 새 private diagnostic adapter에서 주기적 watchdog만 기본off/명시적 opt-in으로 분리했다. 원103 bootstrap bytecode, 원104 atomic worker, fatal enable, event/phase/PID/nonce, 전체 deadline 및 원결과 보존을 유지한다. 전역·설치파일·OS/ACL 설정 변경0, 음악 규칙/계수/parser/IR/후보/점수 변경0이다. 이번 새 adapter의 악보 실행0이다.
- **최초 실패:** r1 기존16검사에서1 FAIL/1 ERROR·25.183352초, 예정probe0이다. timer 없는 foreign fixture가5초 timeout, partial fixture는 raw worker 파일이 없었다. 원검사/한도를 변경하지 않고 r1 traceback/receipt를 보존했다. 임시fixture 원자료는 기존 test가 정리했으므로 원인을 확정하지 않았다.
- **분리 검사·실제 진단:** 후속r2는 process 없는 Binding/Event10+writer4+새정책8=22 PASS·2.953681초다. 기존 process 검사2건의 해결을 뜻하지 않는다. 예정CPU/대기×timer-on/off4개를 순차 각1회·retry0·6.5초 작업/12초 전체 한도로 실행,4/4 exit0·event문제0·native오류0·kernel digest동일이다. on은각1회5초dump를 실제 기록했다. process wall은10.349554/9.109121/10.527761/7.184911초,총37.489731초·bootstrap0.573–3.665초다. 속도 향상/음악 정확도/전곡 안정성 인증으로 쓰지 않는다.
- **보존·다음:** 이전 결과/원코드/고정모델/r1실패 포함135pin 불일치0, 실행 후 신규 봉인 코드 변경0·음악추론/gold채점0이다. 기존process 실패는 report에미해결로 명시했다. 다음은 native실패 악보 한 곡의 동일 코드 timer-on/off 각1회이며6곡/234곡 재시도나계수 sweep은하지않는다. 연결/화면/Claude/서버/Git/MusicSearch/Composition 변경0·기존dirty5보존이다. [화성 개발 정본](records/2026-10-06-stack-diagnostic.md).

## HARM-DEV-20261006-104 — 새 실행기 단일6곡 비교·native 종료·source clock 검증 정정

- **개발/범위:** 새worker adapter는원103bootstrap bytecode와원interval/control worker bytecode를보존하며private final write만atomic JSON으로연결한다. 부모globals/infer/parser/provider/원IR·음표·철자/tie·26계수/후보/점수/beam8/2M/page12/60초/직접99검산불변이다. OS-label우회off·승인환경·4동시·6×2각1회·retry0·worker에는source만준다. 원worker/phase/IR/catalog와execution/status/제출을분리하고원자료를덮어쓰지않는다.
- **검사실패/실행:** 최초r1은71검사 중1error였다. 음악suite구성의선행music21 import 때문에fresh전용검사조건이깨졌다. 원103검사는변경하지않고신규runner순서만분리하며빠진test_a도추가했다. 실패r1/음악실행0보존,최종82PASS/failure0/error0·18.949334초후r2음악최초실행했다. literal wildcard/없는phases파일조회와문서언어혼입은실행전교정했다. 본비교wall78.985178초·exit0·12작업:정상raw5/native access violation6/timeout1이다.
- **실제 상태/해석:** 원parent status는새1/control2완료지만SmallWorld 정상2worker를총길이validator가잘못보류했다. 원IRscore duration은191이지만마디actual끝을포함한전체길이는194이며원parser와worker는194를사용했다. 별도읽기전용원시간식/4검사PASS로sourceSHA/fullIR/span/catalog를재검증,새2/control3으로정정했다. 원score/status/raw/봉인코드수정0·음악재실행0이다. XML/음가수정이나시간범위확장이아니다. baseline6예측재사용이며이번timing측정이아니다.
- **native 문제:** 실제6exit3221225477/0xC0000005·trace access violation표시,5/10/15/20초stack snapshot과종료가겹친다. 같은timer에서정상진행도있어인과관계확정0/RAM·WMI·권한원인확정0이다. module load0.707–1.023초로긴import지연은이번에관찰0이다. Experience control은60.277초timeout·소유live tree정리exit0/확인true,phase JSON 보존·1152/1623셀·142catalog·search36.931초/catalog12.592초다. 새는20.177초native종료·480셀/62catalog,Walking새는parse1.790초후160셀에서종료했다. 부분처리량을속도배수/음악정답으로쓰지않는다.
- **지표/동등성:** 정정전체6/1848quarter 새root12.88%/triad12.77%/coverage16.29%/F1 10.94%,controltriad21.47%,봉인baselinetriad68.51%/F1 59.75%·관문FAIL이다. 공통2triad77.63% 대baseline79.61%/F1 29.91% 대42.94%;원경로/비용/특징/원셀/전체catalog는control·기존101과같다. Pledgingcontrol도읽기전용FIELDS/catalog검사동일,complete unique3의전체IR은원96과동일이다. 원equivalence timely=1은정정전validator수치며raw비교2쌍이실제증거다. 누락은전체분모에유지하고국소NCT/Roman/key/inversion/cadence 정확도로주장0이다.
- **감사/다음/보존:** 본실행639pin·정정652pin PASS/불일치0,예측봉인뒤gold평가·본실행중/뒤신규봉인코드변경0·정정코드실행뒤변경0다. 다음은짧은native/비동기stack진단분리,동일전곡재시도·계수/beam/예산sweep0이다. 화면/Claude/API/서버/Git/MusicSearch/Composition/원96–103/기존dirty5보존·편곡연결보류다. [별도화성개발정본](records/2026-10-06-owned-whole-score.md),정정scoreSHA `c18ffb4c9cff5e6be01aeb414db4a0c0e60872060c682adbec3ffc0e8552e425`,정정auditSHA `d807ad4ddc9f72b0e8ebc6c9923acafebf9248936241722590f3127881ed431e`.

## HARM-DEV-20261006-103 — 원결과 보존 실행기·준비 지연의 제한 진단

- **개발:** stdlib bootstrap부터 실제/launcher PID·nonce·순서/단조시각을 남겨 준비/모듈로딩/계산/종료를 구별한다. worker.json 원결과와 execution.json 상태를 분리하고, timeout 뒤 complete 원자료도 정상 제출로 승격하지 않는다. malformed/torn/foreign/시각·PID 문제·launch오류·atomic교체실패를 처리한다. Windows의 소유 live PID tree만 정리하며 다른Python작업을 열거·종료하지 않는다. 별도 opt-in OS-label adapter는 설치SHA+원bytecode/private의존성으로 제한한다. 원parser/IR/음표/tie·계수/후보/점수/beam/60초/단계102봉인은 변경0이다.
- **실패/검사:** 없는 tests/fixtures 부모생성 patch실패1은 부분생성없음을 확인하고 기존tests의fixture로 교정했다. 제한환경16검사 중 자식tree정리1FAIL,상세 preflight도 같은1FAIL로r1에 보존했고 예정4진단은0회였다. 단일cleanupfixture에서 taskkill exit1/ERROR: Access denied·launcher만종료·tree미확인을 확인했다. 설정/ACL수정없이 승인환경으로 전환, fresh r2에서16PASS/failure0/error0·11.340715초·소유tree정리확인이다. 검사수는 음악정확도가 아니다.
- **실제 진단/판단:** 예정4개를 sequential 각1회·retry0으로 완료했다. whole process noop0.169274초/platform0.231514초/opt-in engine1.311573초/default0.975451초,조회0.080398초·모듈우회1.092262 대기본0.747625초다. 양쪽music21 label=win·우회적용receipt/설치SHA동일·trace4개0byte·event문제0, 음악worker 호출/악보/fit/gold평가0이다. 우회가더빠르지않아 기본미채택(off)이다. 이전지연미재현이지 WMI/권한/RAM원인확정이나 전곡문제해결이 아니다. 이전과권한환경도달라 직접speedup비교0이다.
- **감사/보존/다음:** source/설치/계약/원102결과482pin 단일감사PASS·불일치0. 원결과와 실패history보존,기존dirty5/화면/서버/Claude/MusicSearch/Composition/Git변경0·6곡/234곡재추론0이다. 다음은 새 실행기로 한 번의전곡검증,준비/분석/종료+원선택경로보존·전체분모 baseline 대조이며 계수/beam/timeout sweep은하지않는다. UI/Claude편곡연결보류다. [별도화성개발정본](records/2026-10-06-execution-stability.md), reportSHA `bf7dda0924e20fc1b2bb452aca55c08ceb36fee6f00593ddb71890b29d1d15d4`, auditSHA `2a6180fd338256bbdb0c931b85b0d7746e8ff4c1469dd225926a63b2f04ab66a`.

## HARM-DEV-20261006-102 — 성부·NCT 조회 동등 구현, 실행 지연으로 성능 검증 보류

- **일반 구현/검사:** production parser를 보존하고 static Voice context lease와 NCT interval index를 별도 모듈로 만들었다. 현재tree에Voice0이어도원site/derivationVoice를없애지않는다. 기본context의순서/검증을유지하고설치함수SHA변경/override는원조회fallback이다. 원패턴·순서·중복·반열린구간·Fraction·credit/unknown/26계수/beam8/2M/page12/catalog·원99독립검산유지다. 신규8+기존54=62검사PASS6.494초,원parser/source/Core변경0. 최초test1FAIL은attached copy의derivation기대오류로test만교정했다.
- **실제 입력/단일 실행:** 기존96의봉인전체IR6개와새파싱을전체field/hash비교해6/6동일·488pinPASS다. 본비교는6곡×2/60초/4동시/0retry,182.975846초exit0이나새0완료/6timeout·원101control1완료/5timeout이다. 이전4/6인원control도이번에는저하됐다. 원baseline6예측재사용,새측정시간으로주장0. 원전곡결과/코드/계획재실행·수정0이다.
- **실행 문제/확인 범위:** 12trace중Windows예외표시10·WMI/0x8007000e6·importlib8개. 일부예외표시후에도checkpoint가진행됐으므로processcrash로전부세지않고 실제process_error0/timeout11이다. RAM부족/외부작업/보안/샌드박스원인확정0. Reach새worker내부5.205초에원검산/전체IR/catalog저장을완료했지만process전체timeout으로제출0. gzipIR/catalog는control·이전101과동일,timeoutsummary가selected-path JSON을대체해새실제승자비교불가다. 공통완료0이라equivalence.passed=true는빈검사이며해석JSON에명시했다. 합성/입력동등성과속도/음악품질인증을구분한다.
- **숫자/결정/다음:** 고정6곡1848quarter기준새root/triad/coverage0%·원triad6.06%·봉인baseline68.51%,관문FAIL·UI/Claude편곡연결보류다. 국소화음정확도0%를측정한것이아니다. 다음큰과제는process준비/parse/infer/종료시간분리·Windows/WMI실행지연진단·timeout원workerreceipt보존이며계수/음악규칙/beam/timeout루프로돌아가지않는다. 기본WMI조회권한거부뒤승인읽기전용조회에서이번outputmarker남은worker0;다른작업종료/컴퓨터설정/ACL변경0이다.
- **감사/기록/보존:** 사후514pinPASS/불일치0,결과조회inlinePython문자열SyntaxError1실행전오류도기록했다. 기존dirty5·96–101봉인·XML/Core/주석/모델·MusicSearch/Composition/화면/서버/Git보존·fit/API/commit/push0. [별도화성개발정본](records/2026-10-06-whole-score-intervals.md). scoreSHA `095456ba4630b0beb5b70a9d1acd03efaec5b03e6f748b3d21946305eac6de78`, auditSHA `e7c565b121d54a42500f31698b72761728931dfd217a567a92b86d8c0ccbd90d`.

## HARM-DEV-20261006-101 — 긴곡 단계계측·정확한비용projection·완료율동일

- **진단/일반구현:** 남은1006/1623셀각1회60초·동시2계측·부분제출0/473pinPASS다. Experience마지막571consume/72catalog,parse2.08초·검색37.22초·catalog12.89초로직접검산전timeout,Walking은parse미완료였다. 새weighted integerprefix는원유리수/고정계수LCM으로비구성음4비용을정확히projection하고문맥beat/lowest/root-loop를인덱스한다. 원후보/catalog validation·26숫자·점수/domain/beam8/2M/60초/source trace·원99독립직접검산은유지,parser/gzip/운영변경0이다.
- **단일통제비교/한계:** 같은6곡×2/60초/4작업/0retry/120.536427초exit0다. compiled=control4완료/2timeout,이번완료4wall약5–6%감소(603셀38.55 대40.84초)이나완료율은같다. 공통4원셀경로/비용/feature/availability/source/상태손실/전체catalog가현재control·이전100과동일,원99직접검산PASS·500pinPASS다. 전체6triad27.44% 대봉인99baseline68.51%·관문FAIL·음악품질변화0,작은완료4triad68.90% 대68.48%를우월성으로보고하지않는다. UI/Claude/편곡연결보류다.
- **실제큰병목:** Walking compiled parse37.827초;20초stack는Canonical._voice_id→music21문맥Voice/score tree,40초stack는graceconsumer IRdeepcopy다. Experience20/40초stack는RemainingFeatures.domain의전체pattern Fraction교차scan,마지막1110consume/137catalog 대control1024consume/125catalog다. 둘다검산/아카이브전timeout이므로검산생략/압축축소가첫해결책이아니다. snapshot을전체함수시간분포로주장하지않는다. 다음은 **원IR/sourceID보존성부조회·consumer복사 및동등pattern interval조회**이며계수/음악규칙/beam/timeout튜닝복귀0이다.
- **오류/검사/보존:** 실행전신규5+기존47=52PASS,최초1FAIL은test의history_gate한쪽누락receipt차이로test만교정했다. Walking control phase파일은직접덮어쓰기중종료되어0byte,stack/원파일을보존하고시간을임의채우지않았다. 봉인phases/compiled/runner/검사수정·전곡재시도0,새atomic checkpoint모듈/2검사로pending후os.replace실패시이전JSON보존을검사했다. 최종54PASS이나새writer는이번비교에미사용이다. 없는test파일조회1건/PS inline표현식실행전오류1건도정본에기록했다. XML/Core/주석/모델/96–100/기존dirty5·MusicSearch/Composition/서버/화면/Git보존·fit/API/commit/push0.
- **정본:** [별도화성개발기록](records/2026-10-06-whole-score-phases.md). scoreSHA `74a488cdcd2760ccbc4514ded1c90fc9d037f44d409eb7a5eb72c35683ace94a`, auditSHA `ce584781f781e2922ffd0030d58aa6270f88d05114b25d5464460b46bc8fc774`, equivalenceSHA `c0d206149a094cc38356d506ce9bd82cee5962d2ba9b411285c34406edf30a1f`.

## HARM-DEV-20261006-100 — 점수 동등 전곡 최적화·60초 완료율3/6→4/6

- **측정/구현:** 603셀 전체IR의첫32셀 cProfile17.214151초(파싱제외/부분제출0), 검색초기화8.795845초·consume5.517641초·Fraction비교404만회다. 누적함수시간은중첩돼합산불가·전곡시간이아니다. 신규성능모듈/프로파일·비교runner/8검사/사전계획을만들었다. 원start/end sweep, span/prefix/첫양수root 재사용, 기준박에서살아남는옛특징만동등계산, 원pair함수가쓰는마지막surface, 원provider window 재사용이다. 기존26/점수/후보/domain/Fraction/sourceID/beam8/2M/60초동일, 원globals/bytecode변경0이다. paircache를원직접검산과분리했다.
- **실제 통제비교:** 같은6곡의원99control과adapter각1회·4동시·재시도0·137.963008초/exit0이다. 최적화4완료/2timeout 대원3완료/3timeout,603셀Pledging38.658589초완료 대원60초초과다. 공통3은2.70/8.90/18.30초 대3.75/12.96/29.09초이며원경로/비용/특징/보류·출처/실제run/전체catalog가이번control·이전99에모두같다. 범용속도배수로일반화0, 나머지2곡의최종병목원인확정0이다.
- **음악지표/결정:** 두새예측·봉인99박템플릿고정뒤gold채점했다. 전체6triad27.44% 대원18.74% 대봉인기준선68.51%,coverage39.66%/26.03%/99.89%, 연결관문FAIL이다. 변화는추가완료곡효과이며공통3의음악판단·triad71.54%동일이다. 완료4subset triad68.90% 대기준선68.48%는우월성입증이아니다. Pledging162run/285제출span·triad63.82% 대기준선64.68%, 원전체승자부재여서동일승자비교증명0이다. 베이스/경계·원domain한계그대로, 화면/Claude/generation-ready연결보류다.
- **검사/감사/보존/다음:** 45검사PASS·완료4원직접비용검산PASS·493pinPASS/불일치0·wholecatalog동등성PASS다. 완료4전체IR/원셀/sourceID/철자/전체catalog저장,timeout부분제출0. 원dirty5/96–99봉인·Core/XML/주석/모델·MusicSearch/Composition/화면/서버/Git보존, 봉인뒤코드/계획/검사수정·fit/API/commit/push0다. 다음은남은긴곡의 **단계별실행비용**이며 계수/beam/timeout sweep/음악규칙추가루프로복귀하지않는다. [별도화성개발정본](records/2026-10-06-whole-score-performance.md). scoreSHA `710f038c002d0ccbb2e3566228fc8bfd2d04331acd05c72e37aec4a7d06c65a1`, auditSHA `cc370de7755b29691d6409f2e7f9adfcc639be7dfbe0d259c58792ce7030259b`.
- **양수branch 보완:** 실행뒤 별도test2를추가해실제약박passing할인과준비된늦은3음1/8이양수일때도원/최적화비용동일을확인했다. 최종47검사PASS다. 봉인된원8검사/추론코드/계획/예측/감사수정·음악추론재실행0이다.

## HARM-DEV-20261006-99 — 국소 기준박 점수·고정6곡 개선과 전곡 실행 한계

- **구현/일반 계약:** 신규점수모듈/runner/11검사/사전계획이다. 실제박자의 Fraction 기준박과 셀동시음 수로 raw/강박/긴음/최저음 부적합을 국소적분하고 부재·복잡도·조표 이탈도 beat-cost로 바꿨다. run/전이/해결은 횟수prior다. 기존26계수숫자는 유지하나 의미변경·새버전이며 보정확률이 아니다. 3/7화음·기능적6/4를 선택domain으로 하고 미지원확장형은 전체catalog에 analysis-only 보존했다. 두변경 효과미분리·잔여NCT/entry정의와soft지속의한계공개·후보유효기간완성0이다.
- **실제 결과:** 단계97과같은6곡×2조건·91.691563초/exit0·재시도0·60초/4작업/beam8/2M이다. 엔진3완료/3timeout 대기준선6완료, 전부봉인뒤gold채점했다. 전체6triad18.74% 대68.51%·root18.93% 대71.00%·coverage26.03% 대99.89%·경계F1 26.24% 대59.75%, 연결관문FAIL이다. 공통3triad71.54% 대70.45%, 전체pcs67.61% 대64.05%이며 이전엔진triad42.56%에서개선됐으나 작은개발표본의우월성인증이아니다. 베이스64.57% 대70.04%·경계45.88% 대58.33%는낮다. Family1→92run, Small4→74run이며 bass변화의제출span과구별했다.
- **검사/실패/봉인:** 최종37PASS·479해시PASS·불일치0. 본실행전테스트 고정계수계약ERROR1과 공유음기대margin산술FAIL1을교정했다. 봉인뒤코드/계획/검사수정0. 완료3전체IR·원셀/철자/sourceID·전체catalog를저장했고timeout부분승자제출0이다. 이전Walking baseline timeout이이번42.31초완료여서전체과거조건을속도/정확도대조로직접주장하지않는다.
- **결정/다음/보존:** 국소화음개선은있으나전곡완료·경계/베이스미완료, 운영/Claude/generation-ready연결보류다. 다음큰과제는 **긴곡계산병목**이며계수하나추가루프로복귀하지않는다. 같은6곡재시도/추가fit/API/234확대/commit/push0. 기존dirty5·원Core/XML/주석·96–98봉인/모델·MusicSearch/Composition/화면/서버/Git보존이다. [별도화성개발정본](records/2026-10-06-whole-score-beat-units-pilot.md). scoreSHA `6bdd622c80048b5ddeb010a76f596aa5f312c5f7500283f560394ac887bc6472`, auditSHA `cbd33a83e429684fc300ea46d4f4f7f067d3f034d5d22854d6fab27efa81295c`.

## HARM-DEV-20261006-98 — 전곡 점수의 과병합 원인·확장화음 적용 범위 진단

- **범위/개발:** 단계97 공통완료3곡전부의 봉인IR/셀경로와baseline을사용한다. 새진단모듈/실행기/8검사·점수계약초안을작성, 원음표refs/Fraction/repeat정책/직접26비용을재현했다. baselinePC는source관찰근음+유일3/7template일때만반사실적경로로변환한다. 원그래프도달가능성을가정하지않고주입/재탐색하지않는다. gold/새fit/새decoder/계수변경0.
- **실제 결과:** 진단2.450536초/exit0·원승자3비용exact동일. Family 한run비용0.867461 대baseline115run대조8.004942: run-count/member-turnover/unanchored/root-motion4항7.781004(97.20%)다. nonmember비용은대조0.059833 대선택0.122901인데횟수벌점이우열을뒤집는다. 이대조의문제는beam확대만으로해결할수없다. 다른2곡은관찰근음없음2셀/철자대안2개21셀로대조미확정·임의정정0. baseline은gold가아니며새정확도향상주장0이다.
- **지원 범위/관찰:** Family6음후보의absent-third/altered-fifth/seventh/late-member4항null은3/7shape밖이라평가불가이며현재비용0기여다. extra-complexity0.580371비용도있어완전무벌점은아니다. Family45page중root미관찰4/전체member미관찰37,SmallWorld의긴run35page중6/34다. 분산/생략을금지하거나page경계강제0. key-signature특징은3곡모두미확인이고IRfifths=null을key로지어내지않는다.
- **검증/보존/다음:** 신규8+이전18=26검사PASS·사후480해시PASS·불일치0. 원234/6곡pilot/모델/원XML/IR/주석/화면/Claude/별개dirty5/Git보존·추론/재시도/commit/push0이다. 다음큰작업은 **공통기준박 비용단위·후보지원/지속범위의단일prototype**이며아직실행전이다. 계수하나추가/장시간감사루프를재개하지않고합성반복검사+고정6곡개발비교한번으로종료한다.
- **정본:** [개발 기록](records/2026-10-06-whole-score-objective-diagnosis.md), [점수 계약 초안](WHOLE_SCORE_OBJECTIVE_SPEC.md). diagnosis SHA `7577dc21448383b695325a0ace9c1a0897ae32bf595283deb1a28cc684c45512`, audit SHA `5f826c339decff548c20d128787661a919b9ce061d877846f567e070c89cbefb`.

## HARM-DEV-20261006-97 — 별도 전곡 경로·6곡 파일럿·정확도 미개선

- **개발/계약:** 단계96 모델26계수·원234결과를 유지하고 별도 전곡 모듈/실행기/7검사/사전계획을 만들었다. 원Fraction 셀을 보존하고 물리 마디 안12셀page의 후보bank를 공급하며 run시작·비용을 넘긴다. 국소 승자 이어붙이기0, provider 보류유지, beam8/누적2M/전곡60초/동시4/재시도0이다. 후보 그래프 변경·근사 손실을 공개하고 전역최적/기존v1과 같은후보/보정확률을 주장하지 않는다. 완료경로만 기존26 직접점수로 재검산해 제출한다.
- **실제 결과:** 이전입력 셀수90/200/300/600/1000/1600 근접6곡×2조건·123.348120초/exit0. 새경로3완료/3timeout 대기준선5완료/1timeout, 프로세스오류0다. 전체6·1848quarter root12.01% 대46.10%,triad11.15% 대43.61%,pcs6.93% 대35.28%,경계F1 26.59% 대48.90%다. 공통완료3·484quarter triad42.56% 대70.45%,root45.87% 대72.11%로 완료곡 자체도낮다. **정확도미개선·운영/Claude연결보류**이며 독립 Test/234곡 성능이 아니다.
- **큰 오류/다음 판단:** Family는6음 후보가294셀 전체를1run으로 차지했다. 제출120span은 베이스변화이며 화음진행120개가 아니다. Small World도117span 대4run,188셀 중132셀7음후보다. 전곡run-count/노출 정규화의균형·넓은확장화음·후보유효범위·beam손실의기여도는미분리다. 이번단계를마치고 계수추가·같은곡 재시도·234곡확대를자동으로진행하지 않는다. 후속은 **전곡점수단위/후보국소유효범위라는 큰계약**을먼저판단하며 새버전과 별도평가가필요하다.
- **검사/보존:** 사후476해시PASS·불일치0, 최종신규7+기존채점11=18검사PASS(failure/error0)다. 문서3개내부링크340개존재·UTF-8깨짐0·고정파일재확인불일치0이다. 원XML/IR/주석/모델/234결과/화면/MusicSearch/Composition/Git·기존tracked dirty5를보존했다. 완료3곡전체IR·원셀경로·철자·sound refs·blockers·버린상태수를저장했다. 실제실행뒤고정코드수정0·새fit/운영/Claude/commit/push0다. 부수적인 프로세스목록조회권한거부는기록하되권한변경0,종료는실행기/12산출물로확인했다.
- **정본:** [별도 화성 개발 기록](records/2026-10-06-whole-score-path-pilot.md), [사전 계획](WHOLE_SCORE_PATH_PILOT_PLAN.md). Score SHA `1b132bf137531d7cb7a2139d72a36a04386bdf068a2b55ee6d861ac874f6c1cb`, audit SHA `e6cc23e7b3294bbadaff7173cf3114951887b7aba7d8a13bd25dbb917ac34111`.

## HARM-DEV-20261006-96 — 모델 고정·234곡 전곡 시험 A·편곡 연결 보류

- **범위/사전 결정:** 사용자 제안에 따라 단계95 이후의 계수/특징 실험을 중단했다. 기존 Dev의 완료율 포함 성능으로 기준26 모델을 v1 고정하고, 전곡60초/동시4프로세스/재시도0·기존64셀/256sound 관문을 유지했다. 원 Piano Solo→기존 IR→기존 후보 공급/공동 선택만 연결했다. 화면용 엔진 대체, 국소 승자 이어붙이기, 정답 길이로 자르기, 새 학습/규칙/한도 확대는 없다.
- **실제 결과:** 234곡×2조건=468작업·전체 실행/채점/감사1,135.882235초, exit0. 연구 엔진은 전곡 해답0/234: 자원 보류231(88~1,623셀), source clock 보류3. 기준선은231/234완료(98.72%)·동일3곡 보류다. 시간 초과/프로세스 오류0이며, 전곡 해답 부재는 국소 화음 인식 정확도0%를 측정했다는 뜻이 아니다. 원음표/sounding 불연속3곡은 Beggin_, Oukashou, The Marsh House이며 XML 자체 오류로 단정하지 않았다.
- **채점/결정:** 전체234곡·gold74,432.5quarter 분모를 유지했다. 단순 기준선 root64.6969%/triad56.5929%/pcs42.9235%/bass67.1501%/coverage98.2776%, 경계P34.0582%/R96.0123%/F1 50.2805%. 연구 엔진 제출 점수0, triad 차이−56.5929%p·곡별 paired bootstrap95% CI[−58.4111,−54.6089]%p로 사전 연결 관문 FAIL다. 이 차이는 보류를 포함한 전곡 제출 성능이며 국소 화음 품질 비교가 아니다. **do_not_connect**: generation-ready v0.2/Claude 어댑터/운영 승격은 만들지 않으며 계수 조정으로 결론을 미루지 않는다.
- **검사/실패 기록:** 신규11채점검사 최종PASS. 중첩·다대일 경계·null bass 근음 대입·누락곡 FN을 이 저장소에서 보완했다. 원 Claude CLI는 두 제출 모두 누락곡 처리 후 report()의 KeyError('root')로 실패했고 원 파일은 수정하지 않았다. 별도1마디 C–E–G smoke에서 실제 기존26 선택기를 실행해[0,4) C장화음을 얻었으나 234곡의 추가 성공이나 정확도 검증으로 세지 않는다. 최초 PYTHONPATH import 실패와 정정도 상세 기록에 보존했다.
- **봉인/보존:** 입력/모델/코드와 두 제출을 평가 전 고정, 사후702개 해시 감사PASS/불일치0. 234곡의 전체 IR·원본 경로/SHA·음표 출처와 실패 상태를 보존했다. 기존Train 원본27해시와 시험234해시의 exact overlap0이나 이력 불완전성으로 완전 독립 인증은 하지 않는다. IR/규칙/교재/국소 사례를 연구 자산으로 남기고, 이후 전곡 실행 경로 개발은 별도 승인 범위로 둔다. 기존tracked dirty5, 원XML/주석, MusicSearch/Composition/화면·서버/Git 보존·commit/push/API0.
- **정본:** [사전 계획](FROZEN_ENGINE_TEST_A_PLAN.md), [실행 결과와 재현](records/2026-10-06-frozen-engine-test-a.md). Result SHA `473a9b6c207d528b97dedd1e25bab54ad9bb6ad54bdbd30c14744d090131bfd6`, audit SHA `4bc376a4a34793be4f7638f3e699cf729311b7fdd6673613a2444a377a7b7cea`. 화성 개발 문서에 따로 기록하며 인수인계/구조 개발 로그로 대체하지 않았다.

## HARM-DEV-20261006-95 — 구성음 시간적 소멸·독립된 후속 근거

- **개발/일반 계약:** 신규4모듈/4test/validator다. 해당 run에서 실제 관찰된3음·변화5음·7음이2기준박 창에서 다시 제시/지속되지 않는 비중을 측정한다. never-heard 부재 중복/무음 부과/수직 완전 화음 강제0이다. 범위 끝 기능적6/4의 최저 근음 시간 비중·후속 장3화음 구성음 비율·명시성부4→3/6→5를 독립시켜 일부 관찰도 비교한다. 다성 경로 추측/전위·NCT·종지 확정0,unknown은 차원별로 유지한다.
- **선택/학습 계약:** 원35계수와 단계94의3개0계수/원후보·raw 상한/20초·2M/DP bytecode/출처·철자·음가·tie를 보존한다. 새4항만625유리수조합에서 제한 Train 학습하며 양수 원margin 절반 보호/unknown gradient 제외를 유지한다. 부모와 같은118구간/241대조를 쓴다. 새계수0이면 독립 비용 동등성으로 종료하고 새 정확도를 측정했다고 말하지 않는다. 비0이면 모델봉인→원118새선택→예측전부봉인→참조평가다.
- **검사:** 기존1,042+새29=1,071관련검사/106모듈 PASS·failure0/error0·165.004225초다. validation `f7f0b32f60d63bb4fd52a72654cd2f5c910826e75e51172a874e08bb46527a3e`다. 최초 이명동음 fixture1FAIL은 캐시가 있는 출처의 token만 바꾼 문제였고 실제 F♭ 기보에서 파싱부터 재구성해 교정했다. 독립 재검산의 전체35계수·grace/barrier/history 전달을 본실행 전에 보완했다. 본실행 시작 이후 신규9코드 변경0이다.
- **학습/실제 결과:** 원118구간/23전체악장출처/15작품군·60,129edge/241대조를 유지했다. 사용240/미확인제외1·미확인차원135·양수margin보호155,625조합 중6개가능이다. 독립4→3/6→5 계수−1/20만 선택됐고 다른3개는0이다. 모델봉인→118새선택→예측전부봉인→평가를1,549.875414초/exit0에 완료했다. 완료102→100·wall16→18·참조경로일치58→57,전체근음·구성음시간58.3848%→56.3824%/coverage73.6025%→71.0996%/경계F1 61.5385%→58.6387%다. 공통100은raw ID/경로 전부같음·새정답/다른화음으로정답소실0·시간79.3006%/경계F1 74.1722%동일이다. 추가wall2에는 기존정답1이 포함된다. 학습목적 감소를 정확도 향상으로 주장하지 않는다.
- **원사례/결정/다음:** op33-1 `[97,100)`의 F♯7 소멸특징1/6 대 참조0은 계수0이어서 선택을 바꾸지 못했다. op33-4의 같은성부 A3 `[102,103)`→G♯3 `[103,104)`는 기능적6/4 후보에−1/40을 주지만 literal 근음 후보보다 여전히 비싸다. 사후320경로에서 새비0비용은 참조2개뿐이고 새선택100경로의 추가비용은 모두0이다. **선택 개선없음·전체 coverage 퇴행·운영미채택**이다. 다음은 작은 보너스를 억지로 키우기보다 가장 큰 근음/구성음 동시 오류의 분산 제시 지지·NCT 설명을 비교하고,0계수 관찰의 hot-path 부담은 별도 버전에서 점수 동등성을 검증한다. Dev/UI/운영/Claude/편곡 연결0이다.
- **감사/봉인:** 입력5,227·산출물359·신규9코드 SHA/23출처/원118scope·예측/320독립비용 재현PASS·JSON 재로드 지표동일이다. 별도읽기전용5,595pin도 불일치0이다. Guarded합603.620923초 대 과거618.405454초는 통제된 속도시험이 아니며 추가wall을 감추지 않는다. report `dbdfb879d4df04f7070ea74d7fb6f9088fb2181497402a5a546f0da1a3a0ad04`,audit `ec59cf5823c6ba61a6b5be0e3541c010a1e533be1b00cce6886d32099ce8e90e`,model `452c1daba56c7b0c1b1a84592e06473ae3135e10f00f74072708a4319d8b7315`다. 신규9코드 수정0,Train부분구간 결과이지 전곡/독립Test/Roman·전위·국소조성·NCT 정확도가 아니다.
- **보존/정본:** 기존 봉인/원Core·XML·IR·주석/기존tracked dirty5/운영·UI·서버/MusicSearch/Claude/Composition/Git 변경0이다. Dev/운영승격/API/merge/commit/push0,별도 화성 개발 문서에 기록한다. [사전 계약·일반 규칙·실행 결과](records/2026-10-06-independent-partial-support.md).

## HARM-DEV-20261006-94 — 원악보 후속 문맥·소멸 증거의 공동 선택 연결

- **개발:** 신규4개모듈/4개test/validator로 원악보 후속2기준박의 기능적6/4 구성음·최저음 지지와 명시성부4→3/6→5를 source-only 증거로 추가했다. 단계93의7음소멸 tail도 별도 비용으로 연결했다. 원35계수/원후보/raw상한/원음표·철자/tie/unknown/정확한DP bytecode와20초/2M guard를 보존하며 새run 비용을private dependency로만 연결했다. 주석의 다음화음/조성/작품별조건/원음삭제/종지확정0이다.
- **학습/실행 계약:** 활성240 Train대조와 아직포함되지않은봉인오답경로를 전수 재계산하고 새3항만125개유리수조합에서한정학습한다. 기존양수margin은절반이상보호,unknown차원은학습목표에서제외하지만실제부분비용은보존한다. 모델봉인→원118전수새선택→예측전부봉인→주석평가순서다. 작은성공을전체개선으로주장하지않는다.
- **검사:** 첫1,040검사PASS 뒤 실행벡터검사2개를추가했고,최종1,042관련검사/102모듈·failure0/error0·152.030445초PASS다. validation `4f572833539f03233a03338b525d0d5b34c5899f1b65a6a6b848829e9184b98c`다. 문서패치문맥불일치2는거부후교정했고, 대상파일의부분적용여부를확인했다.
- **학습 결과/실제 선택:** 241대조(240기존+중복아닌봉인오답1),사용240/unknown제외1·미확인차원106·양수margin보호155다. 125계수조합 중10개가능,새3계수모두0이다. Actual1,407.228286초/exit0·원118구간/23전체악장출처/15작품군/60,129edge·102완료/58참조경로일치/44불일치/16wall이다. 원118경로또는보류와공통102 raw ID가모두같고,새정답/소실/복구/완료소실0이다. 전체근음·구성음시간58.3848%/coverage73.6025%/경계F1 61.5385%,공통102시간79.3244%/경계F1 75%동일이다. Train부분구간의수치이지 전곡/독립Test/Roman·전위·국소조성·NCT정확도가아니다.
- **감사/계산/결정:** 사후4,856input/359artifact/9code SHA·23출처/118예측/322독립비용재현PASS다. 예측전부봉인뒤평가,실행중·뒤신규9코드수정0이다. guarded합618.405454초(이전481.796521초)이며과거wall은통제된속도대조가아니다. 계수0에도관찰계산이추가되어속도향상도주장하지않는다. **정확도향상없음·운영미채택**으로기록하며 Dev추가실행/UI/Claude연결0이다. 다음은구성음·베이스·해결의부분지지와반증을분리하여가장큰분산화음/NCT오류를우선한다.
- **봉인:** report `4892ecc786187905cc564cf3ff5656ecbf4b68dd5909cb8fb6666072845e1808`,audit `048ca0cb4e4abff289c7fbe27cedcf2886b37f78db1ec5dd599e1659b408facf`,model `da6501fb4a3b9012029c039b11b6ac95a13378b9f7f9b921a2d3a08ecbdbe89b`다. 검사·출처감사PASS를사람이확인한음악정답으로승격하지않는다.
- **보존/정본:** 원Core/XML/IR/주석/부모봉인/기존tracked dirty5/UI/서버/MusicSearch/Claude/MusicComposition/Git변경0다. Dev/운영승격/API/merge/commit/push0이다. [별도화성개발정본](records/2026-10-06-terminal-source-context-joint-selection.md).

## HARM-DEV-20261006-93 — 큰 Train 오답의 원인 분해·7음 소멸 일반 증거

- **개발:** 기본5code/test/script에 source-only `supported_triad_seventh_release_tail`을 추가했다. 실제 sounding/tie release 뒤 완전한 철자3화음 union이 끝까지 지지되면 기준박1 허용 후 tail/전체 박수 Fraction을 관찰한다. 재등장7음·분산 제시·0음가·변박·unknown null·raw분할 불변을 검증했다. 7음 부재 중복 비용/화음·NCT·기능 확정/원음삭제0, 아직 계수·선택기에 미연결이다.
- **실행/결론:** 원118 Train/23전체악장/15작품군·60,129edge/완료102·정답58/오답44/보류16 유지, 실제217.504391초에 target118+승자102=220path/415run을 추출했다. 오답38quarter는 근음·구성음 모두다름23.75 / 같은구성음·다른근음7.875 / 같은근음·다른구성음6.375다. 같은구성음 근음오류8record, 오답target의 범위끝 기능적6/4/선택후속없음6record다. 새 특징은 wrong34known 중1양수/33zero·10unknown, correct58차이0이다. 이것은 정답 보호/새 정확도 향상 증거가 아니다. 단1개를 위한 계수조정 대신 큰 구성음 지지·기능적 문맥을 우선한다.
- **원사례:** Chopin op33-1 m33의 E4/E5가 quarter98에 종료된 뒤 F♯–A♯–C♯로 이어져도 wholeF♯7이 싸던 원인을 분해했다. 기존gap `-1819/5000`, 새특징승자1/3·target0, 단대조동점계수1.0914는 학습/선택값이 아니다. op33-4 m34의 같은구성음/다른근음은 역할복잡도 `-3529/40000`만 차이가 나며 소멸 특징으로 해결할 문제가 아니다. 전후4quarter·전체XML/IR·음표/음가·원ID·기존35항 비용을118case에 저장했다.
- **검사/실패:** 기본새23+이전991=1,014관련검사/97모듈 PASS·153.451700초다. 초기박자fixture/cache오류2를 본실행 전 수정했다. Actual은118추출/report저장 후 tuple/list중첩signature 재로드비교에서exit1이었다. 기본5봉인코드/원report/case를 덮어쓰거나 재실행하지 않고 실패v1과 신규감사3파일을 남겼다. v2가4,862pin/118record/23IR·220path/415run 특징산술과sound/noteID·실제release동일을확인해PASS다. 의미적JSON교정이지 음악정답검증이 아니다. 보완patch 문맥불일치1/검사TestCaseimport중복도 기록하고 보완파일에서 교정했다.
- **최종검사/보존/다음:** 새27+이전991=최종1,018관련검사/98모듈 PASS·failure0/error0·138.123512초, validation `9ad1ffc432ac09036a3a22abf2f72af39ae70e921c59df60261516255b5472d3`다. 원Core/주석/기존 봉인/모델35/후보/선택/기존tracked dirty5/UI/서버/Claude/MusicSearch/Composition/Git은변경0,새fit/DP/Dev/API/merge/commit/push0이다. 기존경쟁자·정답보호를포함한새특징계약→필요시제한Train학습/fresh→고정Dev순서,단일규칙을운영에곧바로올리지않는다. [별도화성개발정본](records/2026-10-06-large-errors-and-seventh-release-evidence.md),report `1527e7b0a513455243e0aba1d4ff05c705b4c2b79cd2209b095f22952e082f63`,auditv2 `bbdbd9c56c24826efd2ec544261ff7de08983af4356be3c8915fb74f557fb9de`다.

## HARM-DEV-20261006-92 — exact cache 고정Dev·원 구간별 상한 감사 정정

- **구현/계약:** 최초4code/test/script. 단계88순위 보호35·단계90cache·단계91Train봉인을 고정하고 원72record/63graph·60고유범위/14전체악장/9작품군·44,204edge를 새 ordinary 선택했다. 모든 예측을 먼저 봉인한 뒤 주석 평가/기존 경로 재현, 기존9입력 보류/부분21/이력3arm을 보존했다. 새fit/sweep/Dev checkpoint/후보·점수·DP 변경/작품예외/재시도·fallback0,기준26·역할35는 이번 새 시간 대조가 아니다. 실제 탐색 뒤 최초4코드 수정0이다.
- **실제 결과:** Actual577.935945초/exit0·46완료/17wall/원9보류,공통46 ID/비용/근거/전이·DP진단 모두동일이다. 새정답/정답·완료소실/보류복구0,전체 근음+구성음 시간19.463244%/coverage27.467911%·진행14/51완전평가·경계F1 61.855670%,공통46시간70.858114%/macro46.415860%·진행14/37완전평가·경계F1 80% 모두같다. 캐시842,109조회/841,553hit/556적분이나 전체guard합461.616805→468.113903초,공통112.949871→112.533167초다. 통제된speedup/음악적향상/NCT·Roman·국소조성·전위/독립 Test 성능 주장이 아니다.
- **실패/정정:** 최초 감사exit1은 ‘모든상한6’ 가정이었다. 원63graph의cap6×61/18×1/24×1은 과거·새guard와 같고 원graph/SHA도 같았다.31번째 cap24와72번째 cap18의 시간보류는 그대로다. 원report/contract의6은기본값이지 일괄 실제cap가 아니라는 메타데이터 정정을 별도 개발 기록/v2에 남겼다. 최초 감사 실패/코드/예측/보고서를 보존하고 추가4파일의v2감사로 원graph+과거guard+새guard를 각각 검증한다. 작품별 분석 예외나 재탐색0이다.
- **검사/감사/봉인:** 신규8/최초986관련검사·94모듈 PASS·141.219360초,정정5/최종991관련검사·95모듈 PASS·139.928705초다. 최종failure0/error0,Actual실패0/감사v1실패1/v2PASS다. v2사후6,695고유SHA/5,108sealed reload·72예측/63case·14package/44,204edge·236상세비용(과거190전부보존+새46)/252scalar·role전이·공통46동등성/전체공통지표 감사PASS·새decoder/fit0이다. 추가4코드도v2감사 뒤 수정0. Core/원주석/부모봉인/권한/UI/서버/Claude Phrase·Motif·Composition/MusicSearch/별개tracked dirty5/Git 보존,merge/commit/push/API0이다.
- **원악보/다음/정본:** Chopin op50-2 m60 D♭→G♭ 일치유지,Beethoven sonata07 II m37 E7참조 대G♯단3화음 오답유지,m36~37많은cachehit에도 원cap18/시간보류를 전체XML/IR·음가/철자·원sound/note IDs와 연결했다. 캐시 확인을 마치고 **큰 Train 화음/NCT 오류의 일반 후보·점수·전후 문맥 개선**으로 돌아가며 운영/UI/Claude 연결은 보류한다. [상세 표·실패/정정·음표·재현·다음](records/2026-10-06-exact-beat-cache-frozen-dev.md). Report `9923a4ef3306c7cf0f6094a2694258527d538a5657b50daab719066dfef29b76`, contract `1348fb08aef2214a0e6923fda162fb0daff1d4e64e1b92e0dfc431855b549e67`, freeze `57544384be9d646edf2fb4745213771eb19df9461490da30d31d510889cdece9`, auditv2 `00632e90a121046c75cd79827f34c2ff647b9fea8a5e62e1bd89a7f61421c626`, validation991 `3355a1f7e13635310c14900f105e98108935f178f1600a003dd56628038efd28`다. 화성 **개발 문서**를 별도로 관리했다.

## HARM-DEV-20261006-91 — exact cache의 전체 Train 실제 재분석·보류 복구 없음

- **구현/계약:** 신규4code/test/script. 단계90 cache와 단계88의35계수를 고정하고 원118scope/23전체악장/15작품군·60,129edge를 같은20초/2M/6raw로 새 ordinary 선택했다. 모든118예측을 먼저 봉인한 뒤 주석 평가/과거 경로 재현을 수행했다. 새fit/Dev/후보·점수·DP 변경/작품예외/cProfile/측정 중 무거운 병렬 작업/재시도·fallback0이다. 실제 탐색 시작 뒤 새4코드 수정0이다.
- **실제 결과:** Actual934.549119초/exit0,102완료/16wall·과거와 같은 집합이다. 공통102의raw ID·Fraction 비용·상세 근거·transition/DP진단 모두동일, 새정답/정답소실/완료소실/보류복구0이다. 전체 시간일치58.384782%/coverage73.602536%/경계F1 61.538462%, 공통 시간79.324416%/macro77.350301%/진행58/102/경계F1 75% 모두 동일이다. 보류를 제거한79.32%를 전체 성능으로 보고하지 않는다. 전위/Roman/국소조성/NCT/독립 Test 정확도는 이번 평가가 아니다.
- **계산/사례/다음:** 탐색cache1,039,894조회/1,039,226hit/668적분이다. guarded 원118합518.573657→481.796521초·공통102합178.256523→157.639713초지만 과거 wall 대조는 통제실험이 아니다. op18-1 IV의D♭triad 정답 유지, sonata03 II의Bmajor→Aminor→Eminor 오답 유지,op18-1 I의많은hit에도20초 보류를 전체XML/IR/원sound·note IDs로 기록했다. 큰 구간은 복구되지 않았다. 다음은 고정Dev 확인 뒤 큰 Train 화음/NCT 오류이며 운영/UI/Claude 연결은 보류한다.
- **검사/감사/보존:** 신규10 및최종978관련검사/93모듈 PASS·failure0/error0·109.936208초. Actual/감사 실패0이다. 사후4,736고유SHA/4,730sealed reload·118source/23package/644상세비용(과거542전부+새102)/555전이·102공통동등성/예측freeze/전체·공통 지표 감사PASS·새search/fit0이다. Core/원주석/부모봉인/권한/운영·UI·서버/Claude/MusicSearch/Composition/별개tracked dirty5/Git 보존,merge/commit/push/API0이다.
- **정본:** [전체/공통 표·원음표·비용·한계·재현·다음](records/2026-10-06-exact-beat-cache-all-train.md). Report `09d170b697ca3190c850da76a646946eff75b52fd2585ad10ec8435fb67a9cce`, contract `5dd8130a63ccb6ee9502c02ae34fe0c51d9170a2d038ef282419d529ea0618ed`, prediction freeze `53ff1b5ad4d11154b63f0becbb389786469e363461c9c31817344113616b5528`, audit `5770611df3045023f1a56be21d816fa192101e53b38fc37a5982863ea15027ef`, validation `a8abaf740f7039b2d901754ace6c098ea90f35d75468e4ea264f4ff0704fdb94`다. 별도 화성 개발 문서로 관리했다.

## HARM-DEV-20261006-90 — 고정 점수 병목 측정·정확한 박자 환산 재사용

- **측정/계약:** 과거Train wall16전부+edge크기/서로다른작품군으로 선택한완료control4,20scope/13전체악장/11작품군·46,755edge를538.894749초에 cProfile 계측했다. 모델/후보/DP·20초/2M/6raw 고정,fit/새target/negative/현재Dev/작품예외0이다. 계측은 느려지므로1완료/19wall을 성능 변화로 보고하지 않는다. Guarded464.3050초 중박자 환산537,222호출/누적191.6051초(약41.27%)가 큰중복이다. DP/유리수·문맥 비용도 별도로 남는다.
- **구현/동등성:** 신규7code/test/script. Source-local `(start,end)` Fraction cache로 원 `beat_extent`를 재사용한다. 변박·복합박자/unknown null 유지·다른source/변경timeline/비양수span 거부,private dependency/동일bytecode로 원DP/scalar를 연결하되 원상세receipt/독립cost검사는 그대로다. 원118Train/23악장/15작품군·60,129edge/542저장경로·471전이의 근거/availability/비용 차이0,183.514021초다. 재현cache506조회/165적분/341hit은 fresh DP의 speed/coverage 수치가 아니다. 원20profile/118proofcase·전체XML/IR/원ID/과거caseSHA 보존이다.
- **검사/감사/보존:** 신규14 및최종968관련검사/92모듈 PASS, failure0/error0·116.067931초. 실제계측/재현/감사 실패0; 문서패치 문맥불일치1은 생성전 거부 후재적용했다. 계측 뒤 profiler/test2·재현 뒤 신규7코드 수정0. 사후4,491고유SHA/118source·23package/542경로·471전이/60,129edge/20계측 선정 감사PASS·새fit/search0이다. Core/원주석/부모봉인/권한/운영·UI·서버/Claude/MusicSearch/Composition/별개tracked dirty5/Git 보존,merge/commit/push/API0이다.
- **결정/다음:** 계산 중복의 일반 원인과 동등성까지 확인했다. **시간 보류 복구/속도·정확도 향상은 아직미측정·운영미채택**이다. 다음은 같은 고정 모델로 원118Train전체 fresh→고정Dev,이전완료소실/새완료·전체coverage/정확도와공통완료를 구별한다. 작은일부속도·검사통과로 채택하지 않고 큰화음/NCT 오답개선도 별도다.
- **정본:** [상세측정·원악보·계산계약·동등성·재현·다음](records/2026-10-06-frozen-compute-profile-and-exact-beat-cache.md). Profile `2b560ae31c7c67e23a3e676fed53d1ea0d3fd920c4a6263a13e04260bf3ec054`, replay `0257a754d782c81131e64f1f655b9b909b2d2b1cd180321df9adc080db65280a`, audit `7b82e634c0c5ba39ff43704174b8d0101758edd578f514a745a9d487259718bd`, validation `3a32e1e5eca188ebcca922bc285ed3e2ab85bc693ea7dbd013a192fa5d7255cc`. 별도 화성 개발 문서로 관리했다.

## HARM-DEV-20261006-89 — 순위 보호 모델의 고정 Dev 비교·판단 유지·계산 보류

- **구현/계약:** 신규4code/test/script. 기준26 / 단계83역할35 / 단계88순위 보호35의 전계수·순서를 고정하고 원72record/63graph·60고유범위·14전체악장 source·9작품군·44,204edge를 같은6raw/2M/조건당20초로 새 ordinary 선택했다. 원9보류/부분21/후보부재 유지·조건별 새cache·예측72 선봉인 후 참조 평가다. fit/sweep/Dev checkpoint/작품예외/후보정책 변경0, 이미 노출된Dev이지 독립Test가 아니다.
- **실제 결과/결정:** Actual1,190.943504초/exit0·기준/역할35/순위 보호35는62/46/46완료·새wall1/17/17로 이전과 같다. 역할35와 새35의 완료집합·raw path IDs·의미적 화음 모두 동일이며 공통46(완전37/부분9) 진행14/시간70.8581%/macro46.4159%/경계F1 80%다. 변경/신규정답/정답소실/계산 복구0. Train 소폭 개선이 Dev 추가 개선으로 이어지지 않았다. 기준26 공통11/시간65.5055%보다 좋지만 기준 완료16개를 추가 보류하고 그 안의 정답5개를 잃는다. 전체51평가의 진행16/14/14·전체시간29.7550%/19.4632%/19.4632%·coverage42.5904%/27.4679%/27.4679%를 구별해 **운영 미채택**이다. 원9보류와 새17wall을 같은 원인으로 묶지 않는다.
- **사례/다음:** Corelli m31 F→C→F와 op01n05a의 첫 D근음이 유지돼 단계86공동35의 퇴행은 발생하지 않았지만 뒤G7은 여전히 누락됐다. Beethoven07-2 m63 E♭4/C5를 실제 읽고도 앞D화음→F♯감7의 경계 오답은 남아 있다. 전체 XML/IR·9원sound/동일note·quarter span·같은계수 경쟁/witness 비용·63case 모두 보존했다. Dev 사례를 학습target으로 옮기거나 작품 강제 교정0이다. 다음은 고정 점수의 일반 계산 효율과 큰 Train 화음/NCT 오류 보완이며 운영·Claude 편곡 연결은 보류한다.
- **검사/감사/봉인:** 신규10 및최종954관련검사/90모듈 PASS(failure0/error0·126.342858초), 전체repo/954곡이 아니다. 준비·Actual·감사 실패0·Actual 뒤 신규4code/test/script 수정0,6,015input/137artifact/447code pins 유지. 사후6,156고유SHA/72예측/원9보류/14source/44,204edge·154승자비용/462경쟁비용/108평가용witness/627scalar상세전이·63case/이전63case/전체공통지표 감사PASS. 기준 완료62경로·비용은 과거 동일, 과거완료1새wall을 구별한다. 추가fit/search/독립Test·전체Roman/전위/key/NCT 정확도 주장0. 원Core/주석/부모봉인/권한/운영·UI·서버/Claude Phrase·Motif/Composition/MusicSearch/별개 tracked dirty5/Git 보존,merge/commit/push/API0이다.
- **정본:** [실행 계약·전체/공통 표·유지/미해결 원음표·다음·재현](records/2026-10-06-ordinal-protection-dev-check.md). Report `82ec2ecd234f4ed6165ddeb3d94392c7b05c9f22b7ac62ddb40de004d5f4f2ee`, audit `072924e3de0d15baf145a94fd8519d7885e9110e923bc72e85298579bb7505c4`, 예측 봉인 `7e256d40056a581a106e541cc1af74a2e1063ccb9596c582a2ea08a16a9af2e5`, validation `4edee09710f90f0d9026d2508320daeeb37f5654d80300f9a161c71990690227`. 별도 화성 개발 문서로 관리하고 인수인계/구조 분석 문서에 누적하지 않았다.

## HARM-DEV-20261006-88 — 순위 보호 조건과 오답 교정을 분리한 실제 학습

- **구현/계약:** 신규6code/test/script. 단계87 활성240대조/62실제 경쟁에서 초기 gap 양수56개는 `min(raw loss, initial gap/2)` 하한, 초기 비양수6개와 나머지는 원loss margin으로 학습한다. 실제35항 partial 비용으로 모든 하한을 확인하고 고정 dyadic backtracking/양자화 후 검사한다. Known-both whole-path만 gradient, unknown은 null이다. 입력 불확실성3/기능적 해결4 고정·28항 초기±.05/원bounds 교집합·3epoch/720방문 평균·506update다. 새 특징/후보/target/negative 검색·작품 예외·Dev 튜닝0, 원 graph/6raw/2M/20초 guard를 유지했다.
- **학습과 실제 결과:** 최종 모델/모든 update의56하한 위반0, policy margin184.033706→180.225004/원loss margin211.748685→207.598310은 정확도가 아니다. Actual792.856201초/exit0·원118범위/23전체악장/15작품군/60,129edge·102exact/16wall로 완료 집합도 같았다. 초기 역할35 대비 공통102 진행56→58·시간78.3723%→79.3244%·macro76.4567%→77.3503%·경계F1 74.2138%→75%다. 변경2 모두 새 정답/정답 소실0, 전체118 시간57.6840%→58.3848%/coverage73.6025% 동일이다. Train 소폭 개선으로 고정Dev 진단에 넘기되 **운영 미채택**이다. Roman·전위·국소 조성/NCT 전체 정확도나 독립Test를 뜻하지 않는다.
- **대조·원악보·한계:** 이전 공동35 대비 새정답7/소실1/변경12·52→58이며 모든 과거 정답 보호는 아니다. old26은118완료/58정답/전체시간77.5572%로 이번의16wall보다 coverage가 높다. old26 소실6 중5가 계산 보류/1이 의미 오답임을 구별했다. Quartet op18-1 IV m269의 F3–E3–F3를 Ftriad로 복구하고 Chopin op30-2 m33–34의 Bminor→F#minor 가설 교체를 복구했다. op33-1 m19 E#5의 조기 경계는 미해결이며 단계85에서 고쳤던 것이 소실됐다. 모든118case의 전체XML/IR·음가/철자·원ID/전후·새/과거/target 동일새계수 비용을 저장했고 작품별 강제 교정0이다.
- **검사/감사/봉인:** 최초 신규13PASS+partial unknown 보호1개를 추가해 최종944관련검사/89모듈 PASS(failure0/error0·120.782256초), 전체repo/944곡 주장이 아니다. 사후4,340고유SHA/4,333봉인 reload·240벡터/fit 산술/62경쟁/56하한위반0·118source/23package/60,129edge·542상세비용/471scalar전이·지표 재생 감사PASS/exit0. Actual 후 신규6code/test/script 수정0·4,212input/122artifact/447code pins. Core/원주석/부모봉인/운영·UI/서버/Claude Phrase·Motif/Composition/MusicSearch/별개 tracked dirty5/Git 보존, 새Dev/merge/commit/push/API0이다.
- **정본:** [개발 계약·실제 비교·두 개선/미해결·원악보·다음·재현](records/2026-10-06-ordinal-protection-learning.md). Report `8dad89e1130a0e2c742172a942a72732f0d09e3d0d7a2abc0ed9b45041f2435e`, model `b6ff68e73bf6b5b9760107344f66f5c5626da2aa5c8b93ca061c21d6cbc74f38`, audit `6e6eee39d55d0b73250b748ad50ee964833071ae629b86c3d1705c605b24227e`, validation `4b0d90eee150d4685b4f87d51cc5ed9086f64d28ea2b4a90faa173209b4751b0`다. 화성 개발 문서를 따로 관리하고 인수인계/다른 프로젝트에 누적하지 않는다.

## HARM-DEV-20261006-87 — 자기 비교를 실제 Train 오답 경쟁 대조로 교정

- **구현/계약:** 신규6code/test/script. 기존3-run delayed DP에 semantic-error bit만 추가해, 완전 양수-loss 경로 중 기존35항 ordinary 비용의 exact 최소를 구한다. 같은 화음의 raw분할/ID만 다른 것은 오답이 아니다. Error가 다른 state끼리 Pareto하지 않고 마지막2전이를 flush한다. 원 graph/6raw/2M/20초/35계수/철자·음가·tie·성부/unknown 보존, 재시도/부분 승자/beam/작품 예외0이다. Train 주석은 경쟁자 자격에만 쓰며 원 특징은 label-free다. 새로운 blind inference/fit은 아니다.
- **실제 결과/활성 자료:** Actual370.995158초/exit0·전체118record 유지, 보호69범위(원67 + 새정답2)/15작품군·23전체 악장/26,335edge다.62실제 경쟁/7wall보류, 새42양수 대조 추가/기존20semantic 중복 연결, 원198양수+42=활성240이다.67자기 비교는 비활성 이력에 전부 보존하고49미탐색/과거152제외·보류7case도 유지한다.62개 모두known 비0 trainable gradient지만 새 음악적 정확도 향상이나 학습 후 정답 보호를 증명하지 않는다. 중복20개는 delta/mask/loss도 원벡터와 모두 동일함을 별도 확인했다.
- **큰 진단/다음:** wrong가 stored target보다 싼6개는 모두 기존 양수 pool에도 있었으므로 이전 퇴행이 단지 사례 부족 때문은 아니다.56개는 target이 더 싸지만 요구 loss-margin 만족은2개, 해당 known-gradient 차원/기존±.05 box에서 요구 margin 가능4개다. 전체 모델의 불가능성/임의bounds 확대를 주장하지 않는다. 다음은 **정답 순위 보호와 큰 margin 요구를 구별한 한정 Train 학습→원118 fresh 선택→고정Dev**다. 계수·운영/UI/Claude 편곡 연결은 여전히 미변경이다.
- **원악보:** Quartet op18-1 IV m133–134의 D♭화음 유지 대 짧은 Fminor 과분할, m269의 F3–E3–F3와 Ftriad 대 F–A–C–E 경쟁, Chopin op41-4 m6의 같은 구성음/다른 분석 근음 경쟁을 상세35항 gap·원sound/note ID·전체XML/IR와 저장했다. 참조 기준 자동 사례이며 NCT/human 정답으로 승격하지 않았다.69case 전부 source·target·실제 경쟁자/보류·availability·gradient·차이·중복 자격을 보존한다.
- **검사/감사/보존:** 준비 fixture의0음가8ERROR와 누락work-family1ERROR를 Actual전 교정했으며 source/grace 관문은 약화하지 않았다. 신규15/최종930관련검사·87모듈 PASS, failure0/error0·105.653593초다. Actual/감사 실패0·Actual뒤 신규6코드 수정0. 사후4,210고유SHA·4,202sealedreload/69source·23package·26,335원edge/131상세비용/114scalar전이·240벡터/67이력/118record 감사PASS·새search/fit/Dev0이다. 원Core/주석/부모봉인/권한/운영·UI/서버/Claude Phrase·Motif/Composition/MusicSearch/기존tracked dirty5/Git보존, merge/commit/push/API0이다.
- **정본:** [개발 계약·실제 집계·원음표·한계·다음·재현](records/2026-10-06-train-protection-competitors.md). Report `9769f95b6fe91e2cc7e60bd18348f8897172f96d4b29c87e6c2b2b282570a2f5`, audit `658298065027cfd35ce8edc1a2dd559c968b6523781dfc68d41f03aa688b21f5`, contract `dc7c50785320171e745ed46f50e2fd4e97fd42be39e6dce978163edebfb2cac5`, active vectors `3c6c138a1c90ff76ae563b4ffa8d788bc27fed1dd97f8107d3d1e58b2abe2573`, validation `c72f4f60e50b99b18c0c5e20f00587c7eaf6c5e1065f29ee1fb656d29191f9dc`. 별도 화성 개발 문서로 관리했다.

## HARM-DEV-20261006-86 — 세 봉인 모델의 고정 Dev 비교·정답 보호 결함

- **구현/계약:** 새 runner/검사/validator/auditor4파일. 기준26/단계83역할35/단계85공동35의 전계수를 고정하고 원72record/63graph·60고유범위·44,204edge·14전체악장 source·9작품군을 같은6raw/2M/조건당20초 guard로 새 ordinary 선택했다. 조건별 새 특징cache·고정순서·원9보류/부분21/후보부재 보존, 예측72봉인 뒤 참조를 열었다. fit/sweep/loss-augmented/target-compatible 탐색/Dev튜닝/작품별예외0,이미 노출된Dev이지 독립Test가 아니다.
- **실제 결과/결정:** Actual1,274.467090초/exit0·기준/역할35/공동35는62/46/46완료·새wall1/17/17다. 전체51평가가능 중 진행16/14/13·시간29.7550%/19.4632%/17.9230%·coverage42.5904%/27.4679%/27.4679%다. 공통46(완전37/부분9)에서 진행11/14/13·시간65.5055%/70.8581%/65.2506%·macro44.7735%/46.4159%/44.3525%다. 역할35는 기준 대비 공통 새정답3/소실0이지만 추가계산보류16에 기존정답5가 들어 있어 운영 미채택을 유지한다. 공동35는 이전35 대비 변경6record/5고유범위·기존정답1소실/새정답0·시간/macro 퇴행으로 **계수 미채택**이다. 경계F1 80→80.5556%만 오른 것은TP1소실/FP2감소가 동반되므로 성공으로 골라 보고하지 않는다.
- **원음표/다음:** Corelli op01n05d m31의 F→C→F가 A단3화음→F로 병합되고,op01n05a m21의 D3/F♯4·B♭→A를 읽고도 다시B♭-D-F♯로 선택했다. 후자는 같은범위2record이며 전체 정답 소실2개로 세지 않는다. Beethoven07-2 m63도 실제E♭/C가 있어도 비용상D3화음 병합이 유리해졌다. 세 사례와 동일 새계수 비용/원sound·note ID/전체XMLIR를 기록하고63case 모두 이전63case에 연결했다. 봉인Train67zero-loss 대조 모두 같은negative/target path·scored delta0/known gradient0라 보호효과가 없다. 다음은 Train에서 **정답과 별개 실제 오답 경쟁 경로를 비교하는 보호 대조**다. Dev target추가/임의계수조정0이며 계산보류는 별도 문제다.
- **검사/감사/보존:** 준비 중 존재하지 않는상수fixture1ERROR를 Actual전 교정하고 신규9 및최종915관련검사/85모듈 PASS·failure0/error0·107.986039초다. Actual/감사 실패0·새4code/test/script Actual뒤변경0. 사후5,945고유SHA/72예측/14source/44,204원edge·154승자비용/462동일계수경쟁비용/108평가전용witness/618scalar전이/63case/전체공통지표 감사PASS·새fit/search0. 기준의완료62경로·비용은단계76과동일,과거완료1개의새wall을별도기록했다. Core/원주석/부모봉인/권한/운영·UI/서버·ClaudePhrase/Motif/Composition/MusicSearch/기존tracked dirty5/Git보존,merge/commit/push/API0이다.
- **정본:** [개발 계약·전체/공통 표·원음표·한계·다음·재현](records/2026-10-06-joint-balance-dev-check.md). Report `da0ede3f679ef066b0d09759a44723b4f7bad94596788a53122a8100a80107a8`, audit `1e61c8bc17a5dbd348efc06aabd9e71f4be6b04c325958806b40ba599b98da14`, prediction-freeze `e738e417a36abeab9545a0d38be7ad2373e50f136ca994d4dfee436f32ef1d80`, validation `e969dbd99aefea87a92c46f99e17fbf51c9548107b8e61e368b238fc5a2218d7`. 별도 화성 **개발 문서**로 관리하며 인수인계/다른 프로젝트는 수정하지 않았다.

## HARM-DEV-20261005-85 — 28계수 제한 공동 조정·실제 선택 퇴행

- **구현/계약:** 기존35항 중 입력 불확실성3/기능적 해결4는 고정하고, 나머지28계수만 단계83 초기±1/20와 원 의미별 bounds의 교집합 안에서 조정했다. 같은265 Train 대조/3epoch/795전체 방문 평균, 571update다. Known-both whole-path 차원만 gradient에 사용하며 partial score와 unknown을 구별한다. 새 특징/후보/target/negative 검색·작품별 분기·Dev 튜닝0이다. 원 XML/IR·음가/철자/붙임줄·성부·run/DP·6raw/2M/20초 guard를 유지했다.
- **학습/실제 결과:** Margin 합194.219243→185.969136이나66대조 악화,67zero-loss 대조는 모두 trainable delta0라 독립적인 정답 보호가 아니다. Actual761.455190초/exit0·118범위/23전체 악장 source/15작품 가족/60,129edge·102exact/16wall로 이전과 같은 완료/보류다. 공통102의 진행56→52·시간78.3723%→76.1959%·macro76.4567%→74.4862%·경계F1 74.2138%→72.8477%로 **운영 미채택**이다. 전체118도 진행56→52·시간57.6840%→56.0821%·coverage73.6025% 동일다. 학습 수치/검사 통과를 음악적 성능 향상으로 보고하지 않는다.
- **사례/다음:** 변경12개 중 기존 정답6소실/새 정답2, 양쪽 오답4다. Quartet op18-1 IV m269의 F-A-C-E→F triad 복구와 Chopin op33-1의 조기 화음 경계 지연 복구를 저장했다. K281-2의 E♭→Cminor가 다시 병합되고, Beethoven03-2의 짧은 다성 화음 교체/7음/근음이 소실됐다. 소실6 중5는 새 pool 밖 경쟁,1은 기존 대조의 비용 역전이다. K280 A7/Chopin held/op18-1 m111은 계속 오답이다. 모든 범위의 전체 source·note/sound IDs·모델 SHA·이전/target/새 비용을 보존했다. 다음은 봉인 모델의 고정Dev 진단이며 임의 추가 fit/운영·Claude 편곡 연결은 하지 않는다.
- **실패/검사/봉인:** 최초14신규검사의1FAIL은 무변화 비격자 계수가 반올림되는 문제로 Actual 전에 수정하고 회귀1개를 추가했다. 2ERROR는0음가/guard 타입 fixture를 교정했다. 신규15 및 최종906관련검사/84모듈 PASS·failure0/error0·104.983539초다. Actual 시작 후 새code/test/script6 수정0·4,001input/122artifact/442code pins. 사후4,129고유SHA/4,122봉인 input reload·265벡터/fit 산술·118source/23package/60,129edge·440상세 비용/387scalar 전이·전체지표 감사 PASS/exit0, 추가 decoder/Dev0이다. 원 Core/주석/부모 봉인/권한/운영·UI/서버/Claude Phrase·Motif/Composition·MusicSearch/별개 tracked dirty5/Git 보존이다.
- **정본:** [상세 개발·표·원악보 사례·실패·봉인·재현](records/2026-10-05-joint-score-balance.md). Report `d95ef8ed4d63968c752774db705e1b8472c77e67a5b7cfa09efbd36242929358`, model `a65d2238ba5392e5fd05b7a2c3758f2d01f312eea70b003b6b31a534840027e2`, audit `a8ca0d6efb86f08d54fa7d1cd5c601e4e1353883f34315da361d2cacb133f51d`, validation `cf8483bf68c22f2a0a874fcdbe59fdc260177f8867024e6a2e740bbdb00ea0b5`. 화성 개발 문서로 따로 관리하며 인수인계 문서/다른 프로젝트에 누적하지 않는다.

## HARM-DEV-20261005-84 — 35항 비용 분해·편곡 후보 계약과 연결 보류

- **개발/계약:** 단계83 봉인 모델·경로·원 source를 읽어 26+7+2항의 known/partial/value/계수/비용을 7그룹으로 분해했다. Whole unavailable을 0으로 메우지 않고 known-local 점수/known-both gradient를 구별한다. 새 fitting/search/Dev/정확도 향상은 아니다. Actual 13.161325초/exit0, 같은118Train범위/23악장source/15작품군·원60,129edge를 참조하고 442비용/324blind-target 비교/265대조 산술을 재현했다. Margin194.219243·violation196/zero-loss 보호67/35항 비0 known gradient198은 정확도/곡수가 아니다.
- **원음표 사례/다음:** K280 A7 축소는 구성음 지지+.205696/새 역할+.031781보다 단순성−.119401/문맥−.178174 이익이 크다. Chopin literal held에서는 구성음 요구 절감−.329176이 교체 지지를 이기며, op18-1 근음 소실에는 새 역할−.183116도 오답을 돕는다. K281-2 복구도 함께 보존한다. 동일35점수로 비교하므로 옛 arm의 과거 비용과 섞지 않는다. 다음은 28계수의 제한적 공동 균형→fresh 선택→고정Dev이며 새2항 임의 강화/작품 예외0이다.
- **편곡 준비/보류:** Claude의 `K:\Music Composition` score/semantic/harmony/modulation/theory와 retrieval 소비 코드를 읽었다. Fraction/pickup/tie/repeats 시간은 맞지만 absolute TPC와 국소 tonic 상대값/Key/Roman/function/bass·전위 의미는 아직 맞출 수 없다. 118scope JSON/132중복 제거 blind 후보/23partial 색인만 만들고 target/평가 주석은 제외했다. 16unresolved는 옛 후보로 승격하지 않으며 generation_ready=false다. 사용자 선택에 따라 실제 연결/추론기 교체는 보류하고 melody-only 화성 계획/국소 재화성의 별도 A/B 관문을 기록했다. [참고 계약](HARMONY_ARRANGEMENT_REFERENCE_CONTRACT.md). Claude 파일/UI/서버 수정0이다.
- **검사/봉인:** 신규22fixture 최초9ERROR는 context 속성명 착오였고 Actual 전에 교정·22PASS했다. 최종891관련검사/82모듈 PASS, failure0/error0·93.073811초다. 새7code/test/script Actual 뒤 수정0·3,731input/261artifact/7code pins. 사후3,999고유SHA/442비용/324비교/265대조/118export/23색인 감사 PASS/exit0이며 음악 정답률이 아니다. 부모 code/model/source/원주석·Core·MusicSearch/Composition·Claude Phrase/Motif·운영·별개 tracked dirty5/Git를 보존했다.
- **정본:** [상세 개발·산술·실제 반례·재현·다음 관문](records/2026-10-05-score-balance-and-arrangement-reference.md). Report `11d86b722a55501b12fad5276e07bf433a669ced935e4148e432f6f6dc8d1173`, audit `d981e52e741108f74e5ce5544fa610f6be387b355b37e808bf597360f69da748`, validation `b1e70c042ceb10dd4ecb1fc23c255ff56cd2b6642aa20a3d1a6ff841c766037f`다. 인수인계 문서로 누적하지 않았다.

## HARM-DEV-20261005-83 — 구성음 역할의 확장·교체 상호작용

- **구현/계약:** 앞 completed union run의 표면3화음/실제 근음·3음 지지 아래 가능한7음 attack 노출, 조건부 장식/확장으로 설명되지 않는 기준박1개 이상 새 독점 attack의 시간 합집합을2항으로 추가했다. Functional/literal 표면 근음·원 full sounding duration/attack·철자/성부/clock/null·0음가 grace를 구별하며3-run exact DP/flush/분할 불변·6raw/2M/20초 guard를 상속한다. 새로운2항은 외부 조건부 증거이지 확정NCT/7화음 유지 hard gate가 아니다. 원26+단계82의7계수를 모두 고정하고 같은265Train pool의 새2만0초기화/3epoch/cap1/20/bounds±1/2/795전체방문 평균으로 학습했다. 작품/마디별 분기·Dev 튜닝0이다.
- **학습/선택:** 새 known 비0gradient47/두축 available164/zero-loss 보호67,135update·23대조 margin 악화다. 계수+.084749/-.292985,margin196.714029→194.219243이며 정확도가 아니다. 실제r2는926.997719초/exit0·118scope/23전체악장source/15작품군/60,129edge·102exact/16wall이다. 공통102 진행55→56·시간78.3723%동일·macro76.6140%→76.4567%·경계72.9560%→74.2138%다. 새wall2개 중 기존정답1개가 있어 전체118의56정답은 동일하고 시간58.4849%→57.6840%·coverage75.0042%→73.6025%로 **운영 미채택**이다. 전체/공통/기존26 비교와 resource bias를 기록한다.
- **실제 사례/다음:** K281-2 m6의 E♭→Cminor→A♭ 복구와 op18-1 mv4 m111의 A7에서 근음A2를 놓치는 퇴행을 원XML/전체IR·sound/note IDs·전후/같은새점수 비용에 연결했다. 새 지속A가 한 가설에서는 교체 지지라도 앞의A7에서는 이미 구성음인 반례다. K280 A7의 새 extension3/8은 불충분해 최종 축소가 남고,Chopin은 functional held 대조를 이겨도 더 싼 literal held가 있어 최종 병합이 남는다. 고정 대조의 개선을 전체 해결로 바꾸지 않는다. 다음은 실제 경쟁 비용 분해→사전 제한한 기존+새 점수 공동 균형→고정Dev이며 계수 임의 상향/작품 예외0이다.
- **실패/검사:** 첫868관련검사 PASS 뒤 r1이32번째 source의0음가 grace에서invalid_temporal_span/exit1했다.31partial vector/계약을 보존하고 완료모델/새선택은 없다. 양수노출 domain만 구별하는 보완·원grace 회귀1개 후 **869관련검사/80모듈 PASS,failure0/error0·87.866393초**다. 합성 non-grace0음가 fixture초안1ERROR는 원 검증grace로 교정했다. r2Actual/사후감사 실패·중단0이며 큰stdout은 저장JSON으로 확인했다. 사후 읽기 전용 table의 scalar/dict 가정1AttributeError는 원자료 수정 없이 교정했다.
- **봉인/보존:** Actual뒤7새code/test/script 수정0·438code/240artifact/3,482input pins 보존. 사후 **3,729고유SHA/3,721봉인input·265벡터/118source proof·fit/평균산술·118scope/23source/60,129edge·442독립 상세비용/833scalar 전이·전체지표 감사 PASS/exit0**다. 새search/Dev/추가model저장0,Core/원주석/권한·UI/운영weights·ClaudePhrase/Motif·MusicSearch/Composition·서버·별개tracked dirty5/Git 보존이다. [정본 개발 기록·수치·실제 사례·봉인·재현](records/2026-10-05-member-role-interactions.md). Report `641806ea8fbfc94c135446a4134a57ff607e4fc581aad35b2274463102ccd340`,model `3f2c10e7899b3e66696be82bc64e41530829cb48c23707c456dcc3231033d346`,audit `95221af04e321c7500b3df64182b89ea65252d0c593145a3c2d00e246456f8df`.

## HARM-DEV-20261005-82 — 새 blind 경로를 포함한 문맥 점수 재검증

- **목적/계약:** 이전254대조에 단계81의104blind 완료 중 원 sample/path pool에 없는 모든 경로를 추가한다. 정답으로 거르지 않고 zero-loss도 보호하며14보류/93중복을 성공이나 재가중으로 바꾸지 않는다. 새11을 포함한265대조에 기존7계수0초기화/3epoch/cap1/20/bounds±1/2/known gradient/모든 방문 평균을 그대로 사용한다. 기존26·원후보·DP·source/unknown·권한을 보존하며7화음 hard gate/작품별 예외/Dev tuning/UI 승격은 없다.
- **구현/검증:** 신규9검사/source preflight PASS·새4zero-loss/7known-gradient collision 보존. 기존838+counter-v2 3+신규9=850관련검사/78모듈 PASS/failure0/error0·91.788554초.265대조/795방문/357업데이트·bound 무변경29/매 epoch margin collision66,0계수 대비margin212.958920→196.714029이나 동일 pool의 이전모델196.636469보다 약간 나쁘다.43대조 악화도 보존하며 결과로 학습 조건을 조정하지 않았다.
- **실제 선택/결정:** 원118Train/23전체 악장source/15작품군·60,129edge를681.342607초/exit0에 fresh 선택했다.104exact/14wall,이전과 공통104·회복/새보류0·변경1경로·이전정답소실0/새정답1이다. 같은104에서 전체55→56·시간77.8420%→77.9755%·macro76.1242%→76.2325%·경계72.6190%→73.4940%로 소폭 개선했다. 기존26의 같은104시간78.2202%/macro76.2965%보다 여전히 낮고 원118coverage75.0042%라 **연구 개선/운영 미채택**이다. 전체11856정답이며 기존26 대비6소실은 실제A7선택1+wall5를 구별한다. F-A-C 과분할은 유지로 복구됐지만 A7축소는 남았다.
- **원악보와 표현 한계:** 두 K280사례/같은 새 계수 두 경로의 비용·원음표/전후/전체XML·IR와 새11mined proof를 저장했다. K280 A7과 Chopin BI105-2op30-2의 known 두 축 대조는 기존26고정 상태에서 weight합 u≥-0.230120와u≤-0.599570를 동시에 요구한다. 이는 두 특정 target/경쟁 경로 순위의 제한적 선형 충돌 증명이지 전체 오류율 하한/인간 유일정답 주장이 아니다. 다음은 반복 같은7항 weight sweep이 아니라 source-bound 구성음/근음 대응·장식/교체의 상호작용 표현 보완이다.
- **봉인/감사/기록:** actual 이후 code/test/script 수정0·434code/133새artifact pins·원 inputs 보존.3,480고유SHA/3,475봉인input·265대조/11source proof/고정fit·평균 산술·118source scope/444독립 상세 비용/403scalar 전이·전체 지표 감사 PASS/exit0,새 탐색/Dev/추가 model 저장0이다. Tuple/list 집계를 정규화했다. Actual/회귀/감사 실패·중단0;읽기 전용IR 조회의 잘못된span/staff 가정 KeyError2회,잘못된문서context1회는 원자료/조건 변경 없이 교정했고 초안 언어/큰stdout도 QA했다. Core/주석/권한/화면/운영 weight/Claude Phrase·Motif/MusicSearch/Composition/별개dirty/Git 보존. [정본 개발 기록·원악보·결과·재현](records/2026-10-05-context-refreshed-pool.md). Report `ffb9b6bd49a97af745b769f00664dbeac5bd107c902ccf263bd442944d088c67`,model `2b36a64aa933a228d3d71396b3be899be2336afc39e1c217dd4e63ef6fc447dd`,audit `8491823e2ce2ac012b6cbad5931a7c6a8b0b095ec66317ed8d4d926e05ef9ce7`.

## HARM-DEV-20261005-81 — 원 점수·후보·DP를 보존하는 scalar 계산 효율

- **구현:** 새 scalar index는 source onset/release의 exact cell/실제 lowest IDs, 음가 domain·형태 domain·전이 scalar를 재사용한다. 탐색 중 상세 JSON을 만들지 않고7값/availability만 계산한다. 원 v0.2의 다음 signature는 수치 veto가 아니므로 scalar key에서만 생략하며 다음 완성 run end는 유지한다. 원 세-run DP/동점/Pareto/flush/6raw/2M·계수·candidate graph는 상속 그대로다. 마지막 승자와 저장 대조의 상세 설명/비용은 봉인 원 구현으로 독립 재생한다. Unavailable/null·partial 관측·원 철자/음가/clock/성부/anchor/grace/history와 같은 sound 합집합을 유지한다. Lazy scalar index/원 승자 재생은20초 cooperative guard에 포함하고 scalar hook도 항상 복구한다.
- **실제 효율/판정:** 원118Train/23전체source/15작품군·60,129edge를665.970685초/exit0에 새로 계산했다.104exact 선택/14wall 보류,원90완료의 raw IDs/Fraction 비용/원 상세 receipt/DP 연산 모두 동일·이전28보류 중14완료·새 보류0이다. 새 완료14중8참조 일치/6불일치로 계산과 올바른 판단을 구별한다. 같은 모델 원118 전체 일치47→55/118·시간48.1061%→58.3848%·coverage62.5897%→75.0042%는 보류 감소의 효과다. 완료104의 기존26 대비 전체53→55/104이나 시간78.2202%→77.8420%·macro76.2965%→76.1242%·경계73.3728%→72.6190%로 소폭 퇴행해 계수 미채택을 유지한다. 원152제외를 보존했다. 공통90 시간합224.226794→38.989538초는 비통제 역사 비교이며 확정 배속 benchmark가 아니다.
- **검사/감사:** 신규15+기존823=838관련검사/76모듈 PASS,failure/error0·92.509986초다. Tiny DAG 전수/signed/동점/4~6run/분할/flush/성긴 Fraction grid/unknown/부분 관측/실제 resolution conflict/guard·예외를 비교했다. Actual 중 읽기 전용 double-neighbor exact 대조도 PASS다. 원6code/test/script는 actual 이후 수정0·434code/119artifact pins 보존. 원 감사3,338SHA/3,331input·118source scope/312상세 path 비용/275scalar 전이·지표 재생 PASS/exit0이며 새 탐색/fit/Dev0이다. 이후 추가한v2 script/test는 별도 pins로 보존하고 신규3정정 검사도 PASS다.
- **집계 정정/기록:** Fresh tuple과 저장 baseline list를 직접 비교해 변경 경로 수2항목이104로 과대 집계됐다. 최초 감사도 같은 pre-JSON 표현으로 그 수를 재생한 한계를 명시한다. 원report/runner/감사를 덮어쓰지 않고 별도v2에서 같은 모델 대비14/기존26대비13으로 정정했다.3,342SHA/118저장 path 재검산 PASS·두 leaf 외 음악 지표/예측/비용/계수/원자료 변경0이다. 합성 fixture 초안의 invalid onset/row pitch/tuple.pop/불완전 source 오류는 actual 전 교정했다. 잘못된 문서 context patch2회는 변경0으로 실패 후 교정했고, 로그 초안의 다른 언어 잔여 한 줄도 한국어로 복구했다. 큰 최종 stdout 잘림은 compact 조회로 확인했다. Actual/감사/v2 실패·중단0이다.
- **원악보/다음:** Quartet op18-1 4악장의 Cminor→C7→Fminor,Chopin BI126-1op41-4의 A♭3화음 유지가 같은 모델/원후보의 새 완료 사례다. K280의 F화음 과분할과 genuineA7 축소는 원90과 같아 아직 해결되지 않았다. Model SHA는 단계80 그대로이며 이번 fit/Dev/UI/운영 적용0이다. 남은14계산 보류에만 붙들리지 않고 genuine7화음/외부음 설명과 pool 밖 Train 오답의 큰 점수 보완으로 간다. 원 Core/주석/권한/Claude Phrase·Motif/서버/MusicSearch/Composition/별개dirty/Git 보존. [정본 개발 기록·원악보 사례·봉인·재현](records/2026-10-05-context-scalar-efficiency.md). Report `d9a27279ce46407968c354a5e9a36a18bd7e1dfe1eb314a7870f50ef66d38297`,audit `a697a3294e9fc17dc46d0ff7e56d57525bf580b232c1d1459a61c4247e1a2541`,metric-v2 `c50dc4d5781489e5c531fe349af34742d266e73aba2c4e1a687f201fd4c4e004`다.

## HARM-DEV-20261005-80 — 문맥7항 제한 학습·큰 graph 비교와 미채택

- **구현/계약:** 기존26항의 단계75 평균 계수를 모두 고정하고 새7항만0에서 시작했다. 승인 Train118scope/23전체 악장 source/15작품군의 봉인 pool을 사용한다. Negative472조건에서216동일 경로를 중복 제외하고 원2resource 보류를 보존해254대조/118scope를 구성했다. Zero-loss63/known gradient collision126도 버리지 않는다. 사전3epoch·update cap1/20·각 계수±1/2·Fraction/6자리 quantization·모든762post-visit 평균·known-both 전체 차원 gradient를 고정했다. Fixed-pool calibration이지 매 방문 새 adversary/latent target 학습은 아니다. Target/과거 label-aware negative의 출처를 표시하고 일반 추론은 label-blind다.
- **학습/실제 선택:**340update·bound no-change33,margin206.634371→189.763889이나38대조 악화다. Model SHA freeze 뒤118원 graph/60,129edge에 새 ordinary를 시도했다.1,039.879255초/exit0·90exact 선택/28wall 보류다. 원6raw/2M을 유지하고 별도20초 cooperative wall guard를 명시했다. Instance hook은 항상 복원하며 부분 승자/기존 결과 fallback/beam/후보 추가0이다. 전체 일치58→47/118·시간77.5572%→48.1061%·macro77.5655%→45.1002%·경계74.2358%→50%,coverage100%→62.5897%로 **계수 미채택**이다. 완료90paired에서는46→47/90이나 시간77.6326%→76.8595%·macro76.4116%→76.1441%·경계70.2290%→69.2308%로 퇴행한다. 새3정답/선택2퇴행/기존 정답12계산 보류를 구별하며 작은 subset이나 margin을 정확도 향상으로 보고하지 않는다. 변경11경로의 시간4개선/4퇴행/3동일,원152제외 scope 유지다.
- **원음표 사례/비용:** 베토벤 Quartet op18-1의 B♭minor→D♭-F-A→B♭minor를 지속 F/D♭/두 성부 neighbor-like 근거로 의미상 B♭minor 유지로 바꿔 참조와 일치했다. 하지만 K280의 F-A-C를 E-G-B♭로 과분할하고 genuine A7을 Amajor→Eminor로 바꾸는 퇴행도 source/원IDs/전후 anchor·비용으로 보존했다. 남는 외부음/새 구성음의 보상이 기존 유지 근거를 넘는 실제 비용을 기록하되 음악별 예외/7화음 강제/확정 NCT/원음 삭제0이다. 참조 일치가 인간 재승인/유일 음악 해석을 뜻하지 않는다.
- **검사/감사:** 신규8learning+4trial·기존811=823관련검사/74모듈 PASS,failure/error0·88.969183초. 신규6Python UTF-8/AST/공백 PASS,전체 repository suite는 아니다. Actual 시작 뒤 code/test/script 수정0·전체432code/122artifact pins 불변. 사후3,211고유SHA/3,204봉인 input·254벡터/평균 모델 산술·118scope/23source/원60,129edge·326독립 path 비용·전체/paired 지표 재생 PASS/exit0다. 새 search/Dev/추가 모델 저장0이며 산술 재생을 새 모델 학습/선택으로 보고하지 않는다. 준비 단계에서 regression/actual이 겹쳐 wall 수치는 전용 부하 speed benchmark가 아니다. 임시 비용조회 literal newline SyntaxError1회/문서 context patch 실패1회(변경0)는 읽기 전용 조회/실제 문장으로 교정했고 출력 잘림/초안 다른 언어 표현도 정리했다. 실제 실험/감사 실패·중단0이다.
- **다음/보존:** 먼저 exact 의미의 계산 효율을 보완하고 같은 고정 계수/원 후보망·tiny DAG 전수/동점/unknown/분할/flush·118fresh 한도를 비교한다. 이어 genuine7/외부음·NCT 설명과 fixed-pool 밖 경쟁 오답을 Train에서 보완한다. 현재 계수 Dev tuning/운영 승격0,원NC 연구/운영 학습 미승인·Core/원주석/UI/구조/Claude Phrase·Motif/MusicSearch/Composition/서버/별개dirty/Git 보존,API/merge/commit/push0이다. 전체 Roman/전위/국소조성/NCT·종지/독립Test/공개 모델·편곡/작곡은 남아 있다. [정본: 학습·원자료·전체/paired 수치·반례·봉인·재현](records/2026-10-05-context-only-calibration.md). Report `abdcd93b7e1d75bedfb68dbf9e24e71a09793ae7411a3afb95cb86cb33b8e119`,model `f27db2416de803d3245c960e827f3786f8b3947bc1fa538fc15c9d90f17096f4`,audit `d2efea5f69ae4fa5ef18443ae207ef468d7f944076bda7d94b3ff795b91e5c69`. 인수인계가 아니라 별도 화성 개발 문서에 기록했다.

## HARM-DEV-20261005-79 — 세 run 지연 점수의 exact 공동 선택기

- **구현:** 원26항을 보존하면서 단계78의7문맥 항을 실제 선택기에 연결했다. endpoint/raw edge수/최근세 union run 시작·signature를 기억하고 다음 run이 완성될 때 이전 경계 비용을 확정한다. 끝에서 두 pending 전이를 flush하며, 같은 signature 조각은 union run으로 바꾼다. 지역3run의 lowest coverage를 전체 원 quarter폭으로 보정해 전체 v2 profile과 일치시킨다. Fraction/원 후보/최대6raw·2M·null/source-clock/grace/성부/원IDs를 보존하고 다른 history를 현재 화음이 같다고 합치지 않는다. 없는 유지 후보/확정NCT/모듈 global 변경0이다.
- **실제/한계:** 296.909185초/exit0.118Train범위/23전체source/15작품군·원60,129edge·588경로/620전이/144형태 재생,원2보류 보존. 새0계수 control118fresh경로/비용이 단계75와 동일하다. Signed 시험 아래 저장경로260개에 known 비0 특징/245개 비0 비용·437개 all-known/151개 partial unknown이다. 실행 전 edge 수/서로다른source로 고른8작은 원graph/8source·6작품군에서 강제 지연0 및 signed 시험16선택을 완료했으나 승자 모두 같고 새 비용0이다. **새 fit/음악적 정확도 향상/전체 큰 graph 성능 입증이 아니다.** 다음 학습 뒤 큰 graph의 fresh 선택/기존 정답 소실/한도 보류를 다시 측정해야 한다.
- **검사:** 신규17decoder+5trial·기존789=811관련검사/72모듈 PASS, failure/error0·92.630322초. Signed/기존 계수 변형 tiny DAG 전수 최소,4~6run 경쟁·분할 불변·동점·마지막 flush·fraction/변경박자/성긴grid/unknown/한도·원자료를 검사했다. 새6Python UTF-8/AST/공백 PASS. Actual 뒤 코드/검사/스크립트 수정0이다. 파일명 조회 오류1회는 실제 full-score 파일로 찾아 교정했고 조건/원자료 변경0. 사후 감사 PASS/3,081SHA·134새 선택 비용 재생을 확인했다.
- **다음/보존:** 제한 Train 가중치 학습→fresh 일반 선택/보류·퇴행→고정 Dev. NC 연구/운영 학습 미승인,Core/원주석/UI/MusicSearch/Composition/Claude Phrase·Motif/서버/별개dirty/Git 보존,API/merge/commit/push0. [설계·계약·결과·한계·재현](records/2026-10-05-delayed-context-joint-search.md). 완료 report `231e3743ef04ec9edb44f903abf6956d74889d03a831384fb186527c5c5718d8`,contract `8fd557e0451825abfc4bc726bef5fa387002717bf023b805ce0ec144242d6105`.

## HARM-DEV-20261005-78 — 전후 화음·장식 경쟁 표현과 자기 확인 관문 교정

- **구현/계약:** 이전 실제 선택 화음을 유지하는 가정과 현재 오른쪽 화음을 원음표에서 비교하는7문맥 특징을 추가했다. 경과/보조/이중 보조 형태와 남는 다른 성부/새 구성음/이어지는 실제 lowest/기존 dominant pair의 충돌을 Fraction·원ID·합집합 음가로 표현한다. 원26항/비용/후보/가중치/선택을 바꾸지 않는다. v0.1이 current path의 anchor membership도 요구해 E-F-G의 경쟁 가설을 차단한 문제를 실제 Train 원음표로 확인하고 원코드를 보존한 별도v0.2에서 selected anchor 상태를 대안 receipt로 분리했다. held anchor membership/clock/성부/쉼·grace 관문은 유지한다. 작품/마디별 예외0.
- **실제 자료/정보량:** v0.2 r3 202.495282초/exit0·원118Train범위/23전체 악장 source/15작품군·60,129edge·588경로/620전이/144조건부 형태(경과55/보조85/이중 보조4),원2보류 보존. 단계75 추가 dominant credit4개 중2개에 알려진 conflict가 있으나 참조 시각 경계에서도1개 있다. 자동 NCT/경계 삭제 금지다. 새7항의 known 비0 delta는 현재60오류 중29개(27전부known/2부분known),14오류는7항 모두 동일·17오류는partial unknown/known차이0이다. 기존58정답은known차이0. 새 fit/search/Dev/독립 정확도 향상이 아니라 기존 Train 진단이며 새7항만으로 모든 오류를 해결할 수 없다.
- **사례/원자료:** Quartet op18-1 mv1 m211 E3-F3-G3의 F를 C유지 아래 경과형으로 검토하되 남는 A도 보존한다. K281-2의 Ab-G-Ab/G-Ab-G가 참조 시각/추가 시각 모두에서 나오는 반례, Sonata02-2 G-F#-E가 보이지만 다른 lane 중첩 때문에 unavailable인 반례를 원sound/note IDs·source 전체 spans·선택/유지 anchor 대안과 함께 저장했다. 원 fullXML/parent/workingIR SHA/clock/graph/출처 연결은 보존한다.
- **검사/실행 실패:** 신규29+기존760=789관련검사/70모듈 PASS/failure·error0·81.217869초,신규11Python AST/UTF-8/공백 PASS. 최초 r1은 전 작품 geometry마다 선행 source-clock 검증하는 비효율로 첫case 미완료 상태에서Ctrl-C/exit1(완료report 없음)이다. 관문을 해당3-run에 필요한 형태만 lazy 검증/공유하도록 교정하고 r2로 재실행했다. r2(v0.1)는203.647220초/588경로/110형태·781검사·2,951SHA/동일 비용·벡터 재생 감사PASS로 보존했다. 합성 receipt kind 비교2FAIL/별도 G-A-B 가능성을 배제한v2 fixture1FAIL은 actual 이전 교정·조건 완화0. CIM 확인 조회는권한 거부됐고 프로세스/권한 우회0이다.
- **다음/보존:** 새 문맥 표현의 pending 비용/마지막 run flush를 exact 공동 선택기 상태에 연결한다. tiny DAG 전수/분할 불변→Train-only 제한 학습/old+new정보량→fresh ordinary 재선택→고정 Dev 순서이며 scalar 튜닝/Dev sweep/운영 반영은 아직 없다. NC 로컬 연구,Core/원주석/UI/MusicSearch/Composition/Claude Phrase·Motif/서버/별개dirty/Git 보존,API/merge/commit/push0이다. K:공간 확보 후 미반영 단계77 개발 기록/메인/로그도 반영했고 기존 C:r2/K:실패 r1 삭제0이다.
- **정본:** [개발 계약·수치·반례·봉인·재현](records/2026-10-05-context-competition.md). 완료 r3 report `f2cec47280f3101a4b56b51c655ec7e8ec018b7d696b34b71022dc7d86583924`,contract `2e5bef988d7442a615d3017681c81e3c04c515c93048500ec332d53d7ed8f7dc`.
- **r3 사후 감사:** PASS/exit0,2,954고유SHA/2,944봉인 input·118scope/23source/원60,129edge·588경로/원 비용/벡터·620전이/144형태·2보류/delta·집계 재생. 감사 새 fit/search/Dev0,Core/기존 점수 변경0이다.

## HARM-DEV-20261005-77 — Train 유지/교체 근거와 단순 지지 관문 미채택

- **개발/자료:** label-blind source profile/Train runner·검사2·validator/auditor,6Python파일. 원270Train 중118참조 가능 범위/23전체 악장 source/15작품군·원60,129edge에서 초기/단계72/단계75 ordinary와 저장 epoch3 adversary/target의588경로/620경계를 재생했다. 원2resource 보류/152제외 상태 보존, 같은 단계75 계수 비용이며 새 search/fit/Dev 없음. 참조 진단은 source profile 밖에 저장하고 target은 분석 예측이 아니다.
- **결론:** 단계75 추가33경계의 dominant credit4개 모두 도착 구성음3/3/3/4개가 있어 단순 ‘두 구성음’ 관문은 오류를 막지 못한다. target111경계의 수직 두 음 없는 분산 제시2개/새 구성음 없는3개는 hard gate의 반례다. 원음표/동일 계수 비용/원ID로 실제 사례를 보존했다. 새 정확도 향상/확정NCT/주석 무오류로 읽지 않는다.
- **검사/감사:** 760관련검사/67모듈 PASS/failure·error0/79.657586초. Actual r2 217.692133초/exit0. 2,824고유SHA·118scope·23source·588경로/비용·620profile·2보류·집계 재생 감사PASS,원 code pins424개 보존.
- **저장 실패/반영:** K:free0의 r1은38case후Errno28·39번째0바이트/완료report없음,40부분파일337,079바이트 보존. 허용 C:r2로 재실행 완료했다. 다음 개발 시 K: 약26.66GB 여유를 확인하고 이 로그/메인 문서/정식 기록을 반영했다. 원 C:결과와 실패 r1·기존 파일 삭제0이다.
- **다음/보존:** 실제 선택된 전후 화음 아래 성부·준비/진행/회귀·구성음/지속 베이스/분산형 지지를 통한 문맥 경쟁 표현부터 구현한다. 단순 threshold/Dev fit/작품 예외0. NC 로컬 연구, Core/원주석/UI/MusicSearch/Composition/Claude Phrase·Motif/서버/별개 dirty/Git 보존, merge/commit/push0.
- **정본/봉인:** [개발 기록](records/2026-10-05-transition-support.md). Report `7e9830ebab3a14dfd466fce18effce19f66bd6cb5e83d7f2a499a12198e9a172`,contract `25e73acc5da63cefff68ab089287f7d9329243c44a041cbfe6324763bb2689a5`,audit `9f302f80c00a241876502a367e17b2c5b5cd270e3464fe8725c08aa9bfd77cb4`,model `2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf`.

현재 상태와 규칙은 [메인 개발 문서](README.md)를 따른다. 구조 분석 로그·인수인계 문서와 별도로 관리한다. 최신 변경을 위에 추가한다.

## HARM-DEV-20261005-76 — 새 고정 모델 Dev 비교와 퇴행/미채택

- **실제 개발/계약:** 단계75 모델을 다시 fit하지 않고 초기/단계72/단계75 세 ordinary 조건을 원72scope에서 새로 선택했다. 모델/원source/권리/과거 봉인 SHA를 검증하고 모든 예측을 봉인한 뒤 이번 평가 참조를 열었다. 원63graph/44,204edge·14전체 악장 source/9작품군, 원9보류/부분21/정답 경로 부재도 그대로다. 두 control의 경로·비용·지표는 과거 결과와 동일하다. 새 runner/검사/validator/auditor4파일, canonical JSON 비교로 배열 순서/rational/null을 보존했다. 원 코드/후보/시간·붙임줄/철자/ID·26특징·cap6/2M·모델 변경0, loss-augmented 추론/Dev fit/checkpoint/sweep0.
- **측정/결정:** 초기/단계72/새 모델의 전체 일치는16/19/16개(완전51중), 근음+구성음 시간28.8915%/31.9253%/30.3034%, macro53.1500%/46.3740%/45.3804%, 경계F170.6767%/78.6885%/73.8462%다. 단계72→새 모델은 근음 시간35.4959%→34.1890%도 퇴행, TP/FP/FN48/11/15→48/19/15. 변경10record/10범위·시간 개선0/퇴행5/동일5·기존 전체 정답3소실/새 정답0으로 **퇴행/운영 미채택**이다. 초기 대비 소폭 개선만 골라 성공으로 보고하지 않는다.63선택/9보류·coverage43.7106%·ceiling36/51 유지, reference eligible약357.083333quarter이고 중복/겹침 포함이다. 노출된 Dev이지 독립Test/fullRoman/NCT 정확도가 아니다. Mozart eligible0은null이며 macro8가족이다.
- **원음표/원인:** Chopin op50-2 m10~11의 실제 E♭3을 읽고도 복잡도/근음 지연 절감이 비구성음 비용 증가를 이겨 E♭7→G감3화음으로 축소됐다. Quartet06-2 m42~44는 빠른 반음계 진행에서 해결 credit이 교체 비용을 압도해 맞던 전체B♭7을5run으로 과분할했다. Chopin op50-1 m47 마지막1/4quarter D5에서 E♭3화음→G단3화음 경계를 더했다. 동일 새 계수 비용/원 source의 음표·음가·onset/전후를 정본에 기록했다. 특정 작품 예외/확정NCT/중복credit 버그로 단정하지 않았다. 모든 attempted63case/60고유범위에 전체XMLIR·원ID·세 경로·특징/availability·같은 계수 경쟁 비용·사후witness 저장, 기존61case 모두 연결/새2추가다.
- **검사/감사:** 743관련검사/65고유모듈 PASS, failure/error0·81.074초; 전체repo suite는 아니다. Actual231.552초/exit0, 조건별 선택+검산67.938/39.538/40.748초이며 cold/warm cache·동시회귀가 있어 speedbenchmark로 보지 않는다. 4,370고유SHA·72예측/원9보류·14source/원44,204edge·189승자 비용/특징·189case receipt·567동일 계수 경쟁 비용·108평가전용witness·63case/기존61연결·세 지표/변경 목록 감사PASS/exit0, 감사 새search/fit0. 준비 중 과거 문서 파일명 조회1회 오류/cp949 콘솔 출력1회 오류를 정확한 경로/UTF-8 출력으로 보완했고 원자료를 변경하지 않았다. 신규4Python AST/UTF-8/공백PASS·기존5tracked dirty/diff check 보존이다.
- **다음/보존:** 가중치를 더 맞추기보다 **Train 대조의 구성음/NCT와 실제 화음 유지·교체 증거/점수 상호작용**을 우선 점검한다.3/7화음·늦은근음/생략, 빠른 순차/반음계와 진짜secondary, 해결credit·지속베이스/성부의 지지를 함께 비교하며 하드필터/작품 예외/Dev학습 target 추가는 하지 않는다. 원 후보 부재/장문보류·독립Test/공개모델·전체Roman/국소조성/전위/종지/NCT·작곡편곡/운영 연결은 남는다. NC 로컬 연구·원Core/주석·UI/서버/MusicSearch/Composition/Claude Phrase·Motif/별개dirty/Git 보존, API/merge/commit/push0. 화성 개발 메인/로그/정본만 업데이트하고 인수인계 문서에는 추가하지 않았다.
- **정본:** [계약·세 조건/작품군 지표·실제 퇴행·원음표 비용·다음 계획·재현](records/2026-10-05-adversarial-score-dev-check.md). Report SHA `6eb4037bfd5c69c24c12acdb17cf32a04885a398853e8cabf48807a3eeb1821c`, 감사 SHA `6c1c008c498e32bb2e3b48c130986944d9862f65536d5d9933b4f8a9f5a865af`, 예측 봉인 SHA `87511f72dd590c7532ce64f4a3a59711c91b04795e9d97ead59cb2359522589a`. 봉인 이후 code/test/script 변경0이며 중간 progress와 완료 report를 구별한다.

## HARM-DEV-20261005-75 — 현재 손실 경쟁 경로의 제한 학습과 혼합 결과

- **일반 규칙/실제 개발:** 기존26특징·원 후보·초기 계수·3epoch·cap.02·초기1/2~2배 trust box·전체 방문 평균을 보존하고 매 방문 현재 계수에서 exact loss-augmented adversary/latent target을 다시 선택했다. 현재 ordinary가 맞는 구간도 margin 대조에 포함하고 unknown 차원은 양쪽 관측 gradient에서 제외한다. 학습 후 모델을 먼저 고정하고 ordinary Train 추론을 새로 실행했다. 새 모듈2/원 감사v1·v2/validation/검사3을 추가했고 봉인된 이전 코드는 수정하지 않았다. 참조 주입·Dev fit/checkpoint·외부 API/운영 승격0이다.
- **측정/결정:** 118Train범위/23전체 악장 source/15작품군·원60,129edge·354방문,341업데이트/7trust-box 무변경/6보류다.348완전 대조/known gradient, 현재 정답이면서 positive-margin173방문·collision0. 단계72 대비 전체60→58/118·근음+구성음 시간77.6573%→77.5572%·macro77.8664%→77.5655%는 퇴행, 근음 시간82.7966%→83.1971%·경계TP/FP/FN82/31/29→85/33/26·F173.2143%→74.2358%는 개선해 **혼합 결과/운영 미채택**이다. 초기 기준선54→58/118도 함께 기록하되 이전 단계보다 좋아졌다고 주장하지 않는다. 변경10구간/기존 전체 정답 소실3·새 정답1, 나머지152범위는 보존/이번 모델 미평가다. Train 내 진단이지 독립/fullRoman/NCT 정확도가 아니다.
- **원음표 사례/설명:** Sonata03-2 m6~7 첫 교체를11.5→11.75quarter로 옮겨 전체 일치하지만 같은 작품m52~53의 C→G가 E–G–B로 병합되고 m8의 기능적 근음B가surface E로 바뀌어 참조와 달라졌다. Quartet01-4 m269의 F삼화음에 E를 넣는 퇴행도 있다. 새 credit/역할 복잡도와 실제 비구성음·강세·lowest 비용의 균형 원인을 동일 새 계수의 비용 차이로 기록했다. Chopin op30-4 m3의 가운데G♯7 소실은 세 방문/평균 후에도 미해결이다. 354방문·118postfit의 IDs/가중치/26특징/availability/원음표/전체XMLIR/전후 문맥·사후236receipt를 보존, 인간 정답·특정 작품 규칙으로 승격하지 않았다.
- **한도/검사/실패 교정:** 원 cap6·2M 서로 다른 연산 단위 유지. Sonata02-2/K281-2 두 adversary가각3epoch 보류하며 no-update/평균 포함; 최종 ordinary는118모두 선택했다. Actual855.195초/fit781.582초/exit0,354방문 준비/선택/저장 중앙.420초·p958.948초·최대56.427초다.731검사/63모듈 PASS·failure/error0/78.515초 + 별도 직렬화4검사PASS. 최초 사후 감사는 tuple와JSON list의 직접 equality에서 exit1, 순서/값/hash가 같음을 확인하고 봉인v1을 보존한 별도v2로 교정했다. 배열 순서/정확 수치/null을 완화하지 않았으며 학습·모델 변경0이다. 최종2,696SHA·354방문/348대조·1,174독립 비용·236원음표 source receipt·업데이트/평균/세지표 재생 감사PASS/exit0, 원 실행 code pin421변경0. 큰 콘솔 잘림/요약 key 오류는 compact schema 조회로 교정했다.
- **다음/보존:** 이번 고정 모델의 원 Dev 전범위 비교가 다음이다. Train 퇴행/기존 Dev 혼합 결과를 지우거나 Dev 손실 비중/최고 epoch를 선택하지 않는다. 후보/장문 보류·전체 Roman/국소 조성/전위/종지/NCT/독립 Test/공개 모델·작곡편곡 연결은 남는다. UI/서버/Core/원주석/MusicSearch/Composition/Claude Phrase·Motif/별개 dirty/Git 보존, merge/commit/push0. 최종 문서 초안에서 `unknown_root`의 초기0 오기는 실제 `.2`로 교정했고 중간 안내의 다른 언어 문장도 정정했다.
- **정본:** [수식·학습·세 조건 지표·실제 개선/퇴행·봉인/감사·재현](records/2026-10-05-adversarial-score-learning.md). Report SHA `9146c3783006ae433041e3bc05d1db2266e6f9cb03d6b8771e6d046705b96034`, 모델 SHA `2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf`, 최종 감사 SHA `2b315941ef3c180edbd29565d5cc6299652675167358842f462f054c65157b34`. 화성 개발 메인/로그/정본에만 누적하고 인수인계 문서에는 추가하지 않았다.

## HARM-DEV-20261005-74 — 정답 범위를 포함한 학습용 손실 경쟁 탐색

- **목적/일반 규칙:** 단계72의 ordinary loss0 방문이 가까운 오답을 margin으로 보호하지 못한 문제를 점검했다. 같은26특징의 completed-run 비용에서 Train 참조의 근음+철자 구성음 시간 손실과 의미 경계 손실을 빼고, 원 후보망의 완전 진행을 공동 탐색한다. 같은 signature의 raw 분할은 하나의 run이고 참조 경계가 빠진 손실은 onset에서도 센다. 변경 시점의 실제 기능적 pair/전이·exact rational·ID 동점을 보존한다. Adversary/latent target에는 참조 사용·training-only를 표시하고 native analysis export를 차단한다. Loss는 확률이나 전체 Roman/NCT 정확도가 아니다. 비용이 더 높은 오답도 손실이 크면 adversary가 되는 점을 명시했다.
- **실제 대조/결정:** 단계72의 고정 모델에서 재학습 없이118Train범위/23전체 악장 source/15작품군·원60,129edge를 검사했다.116완전 positive-margin/known-gradient 대조, 현재 일반 정답60개 모두에 대조가 생겼다.110경쟁 경로는 ordinary와 다르며 known-feature collision0이다. Nullable/unsupported 차원은 보존: conditional ornament45대조·세 미관측 구성음/late-member 차원 각각75대조는 양쪽 availability가 성립하지 않아 gradient에 쓰지 않는다. 일반118경로·비용·전체60/118·시간77.6573%·macro77.8664%·경계F173.2143%는 단계72와 정확히 동일하다. **정확도 개선/독립 평가/운영 승격이 아니며 계수 변경0**이다.
- **한도/사례:** 원 raw cap6 유지. 새2M의 단위는 feasible-state/raw-edge 비교로 기존 batched factor 연산과 달라 같은 작업량으로 주장하지 않는다. Sonata02-2 `[3,8)`/K281-2 `[545/6,94)` 두 adversary는2M에서 보류, ordinary/target은 보존하고 부분 대조를 학습에 쓰지 않는다. Actual374.911초, 구간 준비/선택/receipt 합계 중앙1.264초·p9510.091초·최대54.498초다. Quartet01-4의 정답 D♭삼화음도 새 loss 대조를 얻었으나 실제 예측이 틀렸다는 뜻은 아니다. Chopin op30-4의 가운데 G♯7 소실은 여전히 남으며 이번은 더 강한 대조 생성이다. 두 사례의 동일 계수 비용·손실·원음표/전체 XML/IR/IDs·전후 문맥을 저장했다.
- **검사/실패/감사:** 신규13+기존708=721검사/61모듈 PASS, failure/error0·73.831초·신규6Python UTF-8/AST PASS. 작은14DAG 전수 경로/임의 full 계수/분할·경계·functional pair·alias/nullable·변경 박자·보류/export 차단을 검사했다. 초기9검사 중8error는 batched packet 복원에 raw path길이 예산을 준 문제로, 새 모듈에서 원 functional reconstruction으로 교정했으며 원 조건/decoder를 변경하지 않았다. Actual r1 exit0/실행 이후 code/test/script 변경0. 사후2,212SHA·118Train/23source/원60,129edge·116대조/손실/마진·352독립 비용/원음표 receipt/일반지표 재생 PASS/exit0다. 감사 fit/새 decoder 탐색0. 사후 큰 출력 잘림은 compact 조회로, 초안 다른 언어 잔여 표현은 한국어로 교정했다.
- **다음/보존:** 매 방문 현재 계수에서 adversary/latent target을 갱신하는 제한 margin 학습으로 연결한다. Initial trust box·24학습/2고정·known-both-paths gradient·사전 epoch/update cap/전체 평균 유지, Dev 최고 checkpoint 선택0. 새 보류는 no-update로 남기며 필요 시 exact batching을 따로 검증한다. 나머지152범위/장문·원 source 보류/후보 부재·전체 Roman/전위/국소 조성/종지/NCT/독립 Test/공개 모델·작곡편곡은 남아 있다. UI/서버/Core/원주석/MusicSearch/Composition/Claude Phrase·Motif/별개 dirty/Git 보존, API/승격/merge/commit/push0.
- **정본:** [수식·Train 결과·한도·실제 source 사례·감사·재현](records/2026-10-05-full-score-adversary.md). Report SHA `c924e50e3b6c1b663766bd0412acd7ba3885f6cc374645af5975c85892d3d71d`, 감사 SHA `d9f8acb584d37092fd5e578a1a228ec563078d486a6e51972e0aa009abb5b971`. 메인 문서의 오래된 ‘현재 단계69’를 이전 기록으로 명시하고 현재 단계74/다음 순서를 별도로 정리했다. 인수인계 문서에는 누적하지 않았다.

## HARM-DEV-20261005-73 — 고정 온라인 모델의 별도 Dev 성능·퇴행

- **목적/구현:** 단계72 고정 평균 모델·report/model-freeze/감사 SHA 및 원 NC 연구/출처 계약을 확인하고 fit을 다시 하지 않았다. 원26특징·후보/시간/철자/붙임줄·6raw cap/2Mbudget을 유지하며 원 Dev72구간/63graph/44,204edge·14전체 악장 package/9명명 작품군 전체를 두 ordinary arm으로 새 선택했다. 참조 경로가 없는 범위·부분/보류를 제외하지 않는다. 초기 path/cost/집계 지표는 단계69 timing 기준선과 동일하다. 72개 예측을 먼저 봉인하고 이번 평가 report를 열었으며 추론에서 reference-compatible target/주석을 쓰지 않았다. 부모의 이미 노출된 Dev행 로드와 추론 미사용을 구별한다.
- **실제 Dev/결정:** 63선택/9원보류·완전51/부분21·ceiling36/51·coverage43.7106% 유지. 전체16→19/51·근음+철자 구성음 시간28.8915%→31.9253%·경계TP/FP/FN47/23/16→48/11/15·F170.6767%→78.6885%로 개선했다. 하지만 작품군 macro53.1500%→46.3740%·근음만 시간35.5309%→35.4959%·근음 macro62.1404%→52.7027%로 퇴행하여 **혼합 결과/운영 승격 보류**다. 이전 전체 정답1소실/새 정답4,변경21record/20고유범위 중 시간 개선13·퇴행3·동일5다. 시간 차이16record/15고유범위에 중복/겹침이 있어 유일한 악곡 시간 증가가 아니다. Train15/Dev9 명명 family의 교집합0이나 전체 중복/노출 감사·독립Test/fullRoman/NCT 정확도는 미완료다.
- **작품군/원음표 반례:** Corelli op01n05a~d68.3333%→80.6667%·op01n04a~d46.7105%→53.9474%와 Beethoven Sonata07-2 87.8661%→78.6611%, Sonata09-2 66.6667%→0%를 함께 기록했다. Sonata09 성분의 평가 시간은1.5quarter이며 작은 분모도 삭제하지 않는다. Mozart K283-1의 원 성분 평가 분모0은 null로 보존하고0점/주석 전체 부재로 해석하지 않는다. 코렐리 `[50,54)` 교체/F삼화음과 `[55,56)` 거짓 교체 제거는 개선했지만, 베토벤 `[15/2,10)`의 C#감7에서 C#을 빼고 `[69/2,36)`의 D#감7 교체를 늦추는 퇴행도 확인했다. 동일한 새 계수 아래 nonmember/강세 비용보다 복잡도/조표외/전이 절감이 조금 더 큰 비용 원인을 보존했다. 작품별7화음 강제/원음 삭제/Dev 계수 보정0이다.
- **사례/검사/감사:** 이전61case/58고유범위를 모두 이어 저장했고 새21변경도 그 목록 안이다. 두 경로/원source receipts/참조 사후 witness·원 XML/IR/IDs·전후 문맥·이전 SHA-bound case 경로를 남긴다. 인간 재승인false/독립testcase false다. 신규8+기존700=708검사/59모듈 PASS, failure/error0·66.252초·신규4Python AST/strict UTF-8 PASS. Actual145.055초/exit0·실행 이후 code/test/script 변경0. 사후3,614고유SHA·14source/원44,204edge·72봉인예측/126독립 승자 비용·192case 비용·61사례/두 지표 재생 PASS/exit0. 감사는 fit/새 decoder 탐색을 하지 않는다. 사후 조회의 미설정 PYTHONPATH import1실패/과도한 출력 잘림은 환경/요약 조회로 교정했다. QA의 Train `reachable` 필드 가정 KeyError1회도 Dev의 `lattice_hit`으로 교정했고 actual/code/artifact는 바꾸지 않았다. 초안의 다른 언어 표현도 한국어로 교정했다.
- **다음/보존:** 다음은 단계72 Train 반례에서 계획한 loss-augmented 경쟁 탐색으로, 현재 정답인 범위의 가까운 오답도 Train 대조로 드러내고 동일 completed-run/전이/cap 아래 작은 DAG 전수 검증을 한다. Dev 최고 epoch/계수 sweep을 하지 않는다. 후보 부재·장문/원source 보류·전위/국소 조성/종지/전체NCT·독립 Test/공개 비교·편곡/작곡은 남는다. UI/서버/Core/원주석/MusicSearch/Composition/Claude Phrase·Motif/별개 dirty/Git를 보존, API/운영 승격/merge/commit/push0.
- **정본:** [계약·전체/작품군 지표·원음표 비용 반례·감사·재현](records/2026-10-05-online-score-dev-check.md). Report SHA `9bdd36259ed5dad8ab5edd34786a6adeb54c0a956a26bb37f79e2f2bf60f8443`, 사후 감사 SHA `a32167145f04217d5aba2b71212500deb46f19c897636bb7a047698de170809e`.

## HARM-DEV-20261005-72 — 이전 정답 포함·현재 승자 갱신·신뢰 범위

- **목적/구현:** 단계71 실패 모델 대신 Stage67 네 계수+Stage69 timing을 가진 초기 전체 점수에서 시작했다. 참조 경로가 있는118Train범위/23전체 악장 package/15명명 작품군·원60,129edge에 이전 정답54개도 포함한다. 기존26특징 중24학습/2고정·원 후보/시간/붙임줄/철자·6raw cap/2M budget을 유지하고 사전 고정3epoch·update cap1/50·초기 계수 절대값1/2~2배와 기존 bounds 교차·내향6자리 quantization을 적용한다. Ordinary 현재 승자와 같은 계수의 latent target을 매 방문 새로 선택하되 **loss-augmented 탐색은 아니다.** Target만 Train 주석을 사용하며 일반 추론과 분리한다. None/availability·known 차원 gradient·평균 전체 방문 계약을 보존하고 작품/마디별 예외·정답 후보 삽입0이다.
- **실제 학습/재선택:** 354방문=171정답/181업데이트/2trust box 제한·자원 보류0. 모든 post-visit 계수를 평균하고 SHA 고정 후118ordinary를 실제 재선택했다. 초기→고정 평균의 전체 일치54→60/118·근음+철자 구성음 시간72.3344%→77.6573%·작품군 macro72.8376%→77.8664%·근음만80.8944%→82.7966%다. 이전 정답2소실/새 정답8, 변경23범위 중 시간 개선16·퇴행4·동일3이다. 경계TP/FP/FN87/38/24→82/31/29·F173.7288%→73.2143%로 소폭 퇴행한다. 모든 구간 단일화 붕괴는 없지만 **Train 내 혼합 결과/연구 후보·운영 미적용**이다. 원270 중 나머지152범위·새 Dev·독립 Test·전체 Roman/전위/국소 조성/NCT 정확도는 미측정이다.
- **원음표 비용/사례:** Quartet01-4의 F/A/C/E→F/A/C와 Corelli op01n03a의 넓은 단일 화음→두 화음은 실제 개선됐다. Sonata02-2의 실제 첫 A7에서 G를 뺀 퇴행과, Chopin op30-4의 중간 G#7을 병합한 퇴행도 보존했다. 특히 쇼팽 구간은 세 방문 모두 ordinary loss0이었으나 다른 범위의 업데이트/평균 후 틀려, 재방문만으로 모든 가까운 경쟁 오답을 margin으로 보호하지 못함을 확인했다. 계수 간 비용을 섞어 비교하지 않고 동일한 새 계수 아래 두 경로 항별 비용을 재계산했다. 354visit/118post-fit에 원scope/fullXML/IR SHA·원 note/sound IDs·전후 문맥·graph·가설/availability/비용 연결을 남긴다. 확정 NCT나 인간 재승인 정답으로 읽지 않는다.
- **검증/사후 감사:** 신규14+기존686=700검사/58모듈 PASS, failure/error0·67.439초이며 repository 전체 suite는 아니다. 신규6Python AST/strict UTF-8 PASS. Actual434.361초/exit0·준비/fit/고정374.424초이며 단일 실행 시간이다. 실행 시작 후 code/test/script 변경0. 사후2,083고유SHA·23source/원60,129edge 복원·354대조/update·826독립 경로 비용·전체 평균 모델/initial/post-fit 지표 재생 PASS/exit0다. 감사에서 새 decoder 탐색·Dev 추론/평가0. Progress checkpoint와 완료 report를 구별하며 이번 학습/검사/감사 실패는 없다. 문서 초안의 다른 언어 잔여 표현은 한국어로 교정했다.
- **다음/보존:** 이미 고정된 모델의 별도 Dev 성능·퇴행 확인을 먼저 한다. 노출된 Dev를 독립 Test로 부르지 않고 계수 sweep/최고 epoch 선택은 하지 않는다. 이후 큰 학습 보완은 Train-only loss-augmented 경쟁 탐색과 작은 DAG 전수 검사다. 현재 개선을 이전 단계의 다른 Dev 분모와 비교하지 않는다. NC 로컬 연구·출처/라이선스 SHA 계약, Core/원주석/운영UI/MusicSearch/Composition/Claude Phrase·Motif/서버/별개dirty/Git를 보존했다. API/운영 승격/merge/commit/push0이며 전체 NCT/조성/종지·독립 평가/공개 모델 비교·편곡/작곡은 남는다.
- **정본:** [설계·학습 계약·수치·원음표 반례·감사·재현](records/2026-10-05-online-score-refresh.md). Report SHA `2c442cc37756e26958d550da90c238ecef8fb6792a00cfd9274edf40d75860d1`, 사후 감사 SHA `6da04003ca3a48617058e8dc3ced1e5975fdc9e5a449a530495d22567f30421f`.

## HARM-DEV-20261005-71 — 전체 점수 Train 학습·과병합 퇴행과 미채택

- **목적/구현:** 기존 completed run·전이·기능 pair·다섯 지지 항을26차원으로 노출해24계수를 학습했다. Blocker/unresolved spelling2계수 고정·부호/bounds 사전 고정·private original decoder/reconstruction을 유지했다. None/availability를 구별하고 양쪽 관측 가능한 차원만 gradient를 냈다. 비구성음/미해결 철자가 없는 run의 조건부 비구성음 장식 domain만 알려진0으로 처리하며 NCT 확정/원 비용 변경은 없다. 원 source/모듈 global/후보/edge/cap을 바꾸거나 정답 후보를 삽입하지 않았다.
- **Train/한계:** Stage70 오류65대조/64범위/19전체 악장 package/13명명 작품군·37,242edge 재계산,26차원 trainable gradient collision0. 고정 pool5epoch·capped PA204update·평균 계수 모델, positive margin70.010849→32.642504·악화12대조다. 현재 승자 오류만 학습했으며 이전 정답 보호/online/loss-augmented negative 갱신은 없다. 초기 nonmember1→.272089·복잡도.1→1.200644·turnover.02→.563377·run count.015→.103682로 균형이 크게 바뀌었다. Margin 감소는 정확도가 아니다. NC 로컬 연구·Dev fit/epoch 선택0·독립Test 미측정이다.
- **Dev 실제 결과/결정:** Model 고정→원72예측 봉인→주석 대조. 원63graph/44,204edge·14source/9작품군·선택63/보류9·완전51/부분21·coverage43.7106% 유지. 시간28.8915%→11.8320%·macro53.1500%→12.8163%·전체16/51→5/51·경계F170.6767%→0%로 **큰 퇴행/가중치 기각·운영 미채택**이다. 이전 전체 정답15개 소실/새 정답4개,변경58record/56고유범위 중 시간 개선10·퇴행32·동일16. 선택63범위 모두 의미상 한 화음 run/모든 raw 선택은 구성음3개(기능적6-4 포함)로 수렴했다. 실제272.690초/exit0·Train101.004초·두 arm 선택+검산64.633/38.476초이며 speedbenchmark가 아니다.
- **비용/사례:** Beethoven Sonata07-2의 맞던 Gminor→G#dim7→E7이 전체 Dminor로, Chopin의 E♭7이 Gdim으로 바뀌었다. 학습 계수 아래 교체/넓은 구성음 비용 절감이 틀린 nonmember·metric·lowest 비용을 압도한다. Corelli의 병합으로8quarter를 잃은 반례와 같은 비용이 거짓 교체를 제거하여2quarter를 맞힌 사례도 함께 보존했다. 따라서 전역 병합 금지/7화음 강제는 하지 않는다. 이전31개 포함61case에 fullXML/IR SHA·원 IDs·범위/전후 문맥·두 경로/벡터/availability/항별 비용·사후 witness를 저장했으며 인간 승인false다.
- **검증/실패/감사:** 신규20+기존666=686검사/56모듈 PASS, failure/error0·66.932초. 신규9Python AST/UTF-8·tiny DAG 전수 경로/원 점수 재생/분할 불변·권리/변조/Dev 거부를 검사했다. 원자료 감사3,071고유SHA·65Train벡터/fit 재생·원44,204edge·126독립 winner 비용·192case receipt 비용·61case/두 arm 지표 PASS/exit0, 감사 새 decoder 탐색0. 임시 post-run 조회의 gzip/UTF-8 오류와 보고서 필드 조회 정정, 문서 patch의 불완전 줄 context 실패는 기록했고 actual/code/artifact를 수정하지 않았다. Progress 중간checkpoint와 완료report를 구별한다.
- **다음/보존:** Reference-compatible118Train범위에서 이전 정답54범위도 보호하고 현재 계수로 생기는 경쟁 오답을 주기적으로 새로 찾는다. Initial-score prior/regularization·조건부 점수 균형은 Train에서만 정하고 post-fit ordinary 선택도 재평가한다. 선택 편향이 원인이라는 해석은 ablation 전의 가설이며 Dev sweep/작품별 예외는 없다. 후보 부재75·원보류/부분·전체 NCT/Roman/국소조성/전위/종지·독립 Test/공개 비교/생성은 남는다. UI/Core/원주석/MusicSearch/Composition/Claude Phrase·Motif/서버/별개dirty/Git 보존, API/운영승격/merge/commit/push0.
- **정본:** [설계·수치·원음표 비용 진단·실패·재현](records/2026-10-05-full-score-calibration.md). Report SHA `3269a812a414d9e59babae34a090aa84ed91c0fbcbf7c244c79f6d1838d57e53`, 사후 감사 SHA `47c2309bf4fa3957d432ab1f9b2461ab86c4dd64c778d357349037f683dfda25`.

## HARM-DEV-20261005-70 — 현재 공동 선택기의 Train 오류 재추출

- **목적/구현:** 과거 220대조에 새 scalar만 붙이는 대신 승인 Train 전체 270구간을 현재 두 고정 점수로 다시 선택했다. 단계67 네 계수와 그 위의 단계69 timing `.248879`를 비교하며 미채택 단계68 recipe는 사용하지 않는다. 새 fit·Dev 추론·parameter sweep은 없다. 원 후보점/126,679edge·최대6 raw edge·2M factored 연산을 보존한 direct original-event backend, compatible-path ceiling과 fresh contrast 저장기를 추가했다. Ordinary 두 예측을 먼저 봉인하고 reference-compatible target을 별도로 탐색한다. Target은 학습 참조 사용을 명시하며 blind 분석/화면에 재사용하지 않는다. 작품별 예외·정답 후보 삽입0.
- **자료/분류:** 27전체 악장 패키지/16명명 작품군·270범위 source-clock 관문 통과, 실제 738.113초/exit0다. 완전 평가205/부분65·선택242/원 보류28이다. 상호 배타적 분류는 주석 일치54 / 선택 오류64 / compatible path 부재74 / cap 차단1 / 선택된 부분49 / 원 보류28이다. 부분16개가 원 보류28과 겹치므로 분모를 이중 제외하지 않는다. Ceiling118/205(57.5610%)는 표현 가능성이지 정확도가 아니다. 전체 source 연결을 보존했으나 모든 XML의 무오류를 보장하지 않는다.
- **새 대조/정보량:** 64선택 오류 범위/13작품군에서 ordinary current winner와 같은 점수의 compatible target 65고유 대조를 저장했다. 과거 pool 대비 raw와 완료 harmonic-run 기준 모두 50개가 새 진행이다. Loss-augmented adversary나 모든 negative를 모은 것은 아니다. 다섯 추가 특징이 모두 available한41개 중21개는 delta0,20개만 차이가 있고 timing 차이는1개뿐이다. Unavailable24개도 null/availability를 보존해 저장했으며 accumulator delta0을 사실상의0으로 해석하지 않는다. 후보 부재/cap75개는 weights만 바꿔 해결할 수 없다.
- **진단/사례:** 두 arm의 전체 일치54/205·근음+철자 구성음 시간32.1860%·macro40.5283%는 같다. 경계F1은56.5138%→56.7766%지만 이미 노출/학습된 Train 진단이며 독립 정확도나 새 모델의 성과가 아니다. Sonata02-2의 경계 하나는 복구됐어도 G# 포함 화음과 A삼화음은 틀리고 미지원 넓은 집합이 timing 비용을 피한다. Quartet01-4의 F/A/C 대 F/A/C/E 대조는 추가5특징이 같지만 기존 neighbor-like 근거가 이미 있다. Raw/metric/lowest nonmember와 화음 복잡도의 균형 때문에 참조 삼화음의 비용이 더 크므로, NCT 탐지 부재와 점수 선택 실패를 구별한다. 원 note/sound IDs·전체 XML/IR SHA 연결·두 경로·target·support receipts를 270scope에 보존했다. 인간 확인으로 확정하지 않았다.
- **검증/감사:** 신규15+이전관련651=666검사/53모듈 PASS, failure/error0·72.256초다. 초기 ceiling fixture가 원 graph에 없는 G edge를 요구한1FAIL을 실제 존재 경로로 교정했고 code/조건을 완화하지 않았다. Actual 이후 code/test/script를 수정하지 않았다. 사후1,595고유SHA·540ordinary packet·612독립 경로 비용·128arm 대조·65고유 대조·원126,679edge 복원·두 arm 지표 재생 PASS다. 새로운 decoder 탐색/fit 재실행은 아니다. Progress의 마지막 checkpoint `complete=false`와 종료 정본 report의 `complete=true`를 구별한다.
- **결정/다음/보존:** 새 대조를 활용하되 단일 timing 계수 반복보다 **기존 전체 점수의 NCT·베이스·화음 복잡도 균형을 Train 전용으로 학습**하는 것이 다음 우선순위다. 미지원 역할의 비교 가능성, 후보 누락·장문 보류, 독립 Test/공개 모델 비교·전체 Roman/국소 조성/전위/종지/NCT 정확도는 남는다. NC 로컬 연구 계약과 원Core/XML/주석·운영UI·MusicSearch/Composition/Claude Motif·별개 dirty·Git를 보존했다. API/운영 승격/merge/commit/push0.
- **정본:** [설계·수치·원음표 반례·재현](records/2026-10-05-fresh-train-negatives.md). Report SHA `b542fa2e7e82bc02b49edc70d3f71bfbbad1fb9b951a318200d8d6759381c532`, 사후 감사 SHA `828d615429e733796f6e45f98fcbe00eb0bc1f6aea0d92d2defbf65347bce2bb`.

## HARM-DEV-20261005-69 — 첫 구성음 지지·지역 박자 유예와 과병합 부분 개선

- **일반 규칙/구현:** 명확한3/7화음의3음·감/증5음·7음 첫 실제 지지까지 지역 박자를 적분한다. 분산 제시1박을 유예하고, run 시작 전에 시작하여 지속된 비구성음이 같은 검증된 명시 성부에서 순차 도착하면 초과 비용을 절반으로만 줄인다. 원음/ID·spelling·half-open/tie onset·grace/repeat/history 관문을 보존하고 지연음/NCT/페달을 확정하지 않는다. 전혀 없는 역할은 원 absence 비용만 남겨 이중 부과하지 않는다. 동일 raw signature 조각은 합친 run으로 계산하며 변경 박자의 exact scale만 private 확장했다. 후보 제거·float·작품별 예외0.
- **Train/한계:** 미채택 단계68 recipe 계수는 쓰지 않고 단계67 고정4계수 위에 새 timing scalar `.248879`만 학습했다. 원 승인116구간/220대조/23악장 source 중 미지원40은 저장하되 제외해104구간/180대조/15작품군을 fit했다. Positive8/zero172·180target timing0, 매 epoch16margin satisfied/156collision/8update·총40update, margin149.754271→149.500133/악화0이다. 정보 있는8대조는6작품군뿐이며 정확도 수치가 아니다. NC 연구/출처 계약 유지·Dev fit/parameter sweep/fresh adversary0.
- **Dev/결정:** 원72구간/63graph/44,204edge/14전체 source·63선택/9보류·완전51/부분21·ceiling36/51·coverage43.7106% 유지. Model고정→예측 봉인→reference 대조. 시간28.3314%→28.8915%·macro52.8166%→53.1500%로 조금 개선하나 완전16/51 동일·경계F171.2121%→70.6767%로 내려 **혼합 결과/운영 미채택**이다. 변경2record 중 +2quarter1·미평가 pedal 구간1, eligible-time 퇴행0이고 FP1증가다. 노출된 Dev이며 독립Test/fullRoman/NCT 정확도가 아니다.
- **사례/다음:** Corelli `[120,132)`의 늦은 F4를 소급하는 Gminor7 비용이 늘어 `[126,128)` Gminor2quarter를 맞혔지만 주석 끝130을 못 맞히고 뒤 넓은 집합도 남았다. 같은 source `[124,132)` 두 기존scope는 control과 같다. Sonata09-2 `[272,280)`는 Cmajor 대신 timing 미지원 functional6-4 대안이 선택됐고 원 pedal projection이 미평가라 성공/실패 판단 불가다. 원29case를 보존하고 새2를 추가한31record/29고유범위에 fullXML/IR·원 note/sound IDs·두 비용·첫 도입·사후 witness를 저장했다. 준비된 해결 할인은 보존case에서0이므로 corpus 효용을 입증하지 않았다. 다음은 **현재 decoder의 fresh Train 경쟁 경로 대조 갱신**이며 소규모 historical feature 실험만 반복하지 않는다.
- **검증/실패:** 신규25+기존626=651검사/51모듈 PASS, failure/error0·64.810초. 초기 compound fixture dict1failure를 실제 meter tuple로 교정했고 재사용 TestCase의 중복 수집도 제거했다. Actual r1 304.321초/exit0(Train173.221초), 두 arm 선택+검산36.795/35.174초다. Actual 뒤 새 code/test는 수정하지 않았다. 원 source/old code/조건 완화0.
- **재즈 질문/보존:** 공통3/7·dominant7 기반 일부9/11/13 후보와 저장된 재즈 책 파일은 확인했다. 재즈 전용 보이싱/alteration/대리화음/코드–스케일의 체계적 구현·검증은 미완료이며 고전 규칙을 전역 강제하지 않는다. 책 목록 확인을 내용 흡수 완료로 기록하지 않았다. UI·Core/원주석·MusicSearch/Composition/Claude Motif·별개 dirty·Git 보존, API/merge/commit/push0. [상세 규칙·수치·반례·지원 범위·재현](records/2026-10-05-identifying-member-timing.md). Report SHA `c6bced83e4c63681543cf54b84a5de243cec7f8af2d8fc024385460cb9d4ecd4`.
- **사후 감사:** 2,049고유SHA·220Train source 특징/고정 비용/compatible target/loss 재계산·180eligible model fit 재생·72×2지표·126독립승자 비용·원44,204edge codec·14전체source·31case/witness PASS다. Dev 새 추론 재실행은 아니다. 문서 초안의 다른 언어 표기를 한국어로 교정했고 기존 기록·실패 이력은 삭제하지 않았다.

## HARM-DEV-20261005-68 — 음 집합/화음 점수 비교 가능성과 시간적 지지의 한계

- **구현/일반 규칙:** 동일 근음의 알려진3/7 recipe 밖에 남는 선언 구성음 비율×run폭/context폭을 새 특징으로 추가했다. 철자와 unknown 역할을 보존하며 functional6-4 대안도 처리한다. Raw 같은-signature 조각을 합쳐 계산하고 후보/source 제거·없는 음 생성·NCT 확정·작품별 예외는 없다. 어휘 거리를 음악적 오답으로 확정하지 않는다.
- **Train/한계:** 단계67 고정4계수 위에 새 계수 하나 `.222864`만 승인 Train116구간/220대조/23악장 source/15작품군에서 학습했다. 기존 role 미지원40대조도 포함했다.220target의 residual0, delta positive8/zero212/negative0로 과거 negative pool 편향이 크다.5epoch update40, margin191.082→190.885·악화0은 정확도 수치가 아니다. Fresh adversary 탐색/Dev fit은 없다. 원 NC 연구/출처 계약 유지.
- **Dev/결정:** 원63graph/44,204edge/14전체 source/72구간을 두 조건으로 새로 공동 선택했다. Model고정→예측 봉인→이번 reference report 개방, 기존 단계67 winner/비용/지표 동일을 검산했다.63선택/9보류·완전51/부분21·ceiling36/51·coverage43.7106% 유지. 미지원 shape 승자16→12지만 시간28.3314%→27.2812%·macro52.8166%→52.2322%로 퇴행, 완전16/51 동일·경계F171.2121%→71.7557%다. **운영 미채택**. 변경6record/5고유 exact range는 시간 개선1·퇴행2·무변화3이고 퇴행2는 같은 `[124,132)`다. 노출된 Dev이지 독립 blind Test가 아니다.
- **사례/다음 큰 원인:** Corelli op01n05a의 F4는 원 XML/IR의 `[130,132)`에만 있고 Bb4는 `[126,128)`, C5는 `[128,130)`인데, whole-run에서 F를 한 번 보면 미관측7음 비용0이 되어 `[126,132)` Gminor7 과병합이 이겼다. 두 중복 record에서2→0quarter 퇴행했다. 주석 G/C/D와 확장/변경 음 집합에도 단순 tertian residual을 붙이는 한계를 기록했다. 원29case를 모두 이어 저장했으며 source·IDs·두 비용·모든 동점 recipe·nullable 역할·사후 witness를 보존한다. 다음은 시간별 구성음 지지와 유지/교체·분산/생략/페달/지연의 공동 설명, 어휘 연결과 fresh Train 대조다. 벌점만 더 높이는 Dev 재조정은 하지 않는다.
- **검증/실패:** 신규22+기존관련604=626검사/48모듈 PASS, failure/error0·61.297초. 초기 runner fixture의 reference cell tuple1error를 계약 dict로 수정했다. Actual r1 296.956초/exit0(Train174.542초), 두 arm 선택+검산34.390/33.445초다. 사후 **2,043SHA·220Train대조/model 재생·126승자 비용·72×2지표·원44,204edge·14전체source·29case 감사PASS**. 원 code/계수/graph/source를 완화하지 않았다.
- **보존/정본:** 운영 UI·Core/원주석·MusicSearch/Composition/Claude Motif·별개 dirty·Git 보존, API/merge/commit/push0. 전체 NCT/Roman/local key/전위/종지·장문2M·독립 평가·생성 미완료. [상세 규칙·학습·퇴행 원음·재현](records/2026-10-05-recipe-score-comparability.md). Report SHA `1033719ce16be95fa6fde2619331aff2856a247f4e657ad4c9fc52fcf6a45ce8`.

## HARM-DEV-20261005-67 — Train 전용 구성음·지속 비구성음 점수 균형

- **구현/일반 규칙:** 미관측 3음·감/증5음·7음을 별도 노출로 계산하고, 원 sounding duration이 원 onset의 박자 단위 이상인 비구성음의 실제 교집합 노출을 추가했다. 동일 signature의 raw 조각은 완전 run으로 합친다. 음표 삭제·확정 NCT·생략 금지·작품별 예외·Core 변경은 없다. 기존 점수는 고정하고 추가 4계수만 제한 학습했다.
- **Train/범위:** 기존 J2f update549+collision4를 중복 제거한 116구간/220대조·23악장 source에서, 특징 미지원 40대조를 제외한 104구간/180대조/15작품군으로 5epoch calibration했다. 새로운 adversary 탐색은 아니며 과거 negative 편향이 있다. Train 승인/NC 연구 제한을 검증했다. 계수는 .885548/.941206/.878012/.824534다. Margin 합 200.479→149.754지만 20대조는 악화했고 collision28개가 남아 정확도 향상 수치로 읽지 않는다.
- **Dev/결정:** 원 63graph/44,204edge/14전체 source를 보존하고 model고정→72예측 봉인→step66 reference 대조 순으로 실행했다. 선택63/보류9·완전51/부분21·ceiling36/51·coverage43.7106% 유지. 시간27.0012%→28.3314%·macro51.9033%→52.8166%·완전16/51 동일, 경계F173.6842%→71.2121%로 **혼합 결과/운영 미채택**이다. 변경20record/18고유 exact range 중 시간 개선6·퇴행3·무변화11이며 중복/겹침이 있다. 부모 JSON의 Dev행 로드와 학습/추론 미사용을 구별했다. Train15/Dev9 named family의 교집합0이나 전체 중복 감사/독립 blind 평가는 아니다.
- **반례/케이스:** 새 role 특징 미지원 shape 승자가 10→16record로 늘었다. Corelli [36,39), [73,76)의 넓은 음 집합/과병합으로 각1quarter 퇴행했다. 기존 [55,56)는 미관측 B♭ 후보 비용이 늘자 미관측 완전5음 B를 허용한 후보가 이겨 여전히 미해결이다. Op01n05a [124,132)의 2quarter 개선 두 record는 동일 범위다. 이전18사례를 포함한29case에 전체 XML/IR·원 IDs·두 비용·관측과 사후 witness를 보존했다.
- **검증/실패:** 신규24+기존580=604검사/45모듈 PASS, 61.186초, failure/error0. Python PATH 실패는 기존 venv로 실행했고, fixture에 없는 G7 조각은 실제 C 같은-run 대조로 고쳤다. Actual r1은 Train2/116 후 missing_measure_boundary로 중단하여 삭제하지 않았다. Train 고정 경로의 직접 원음표 계산과 Dev 원 인덱스를 분리해 point/후보 추가 없이 r2를 완료했다. 실제325.364초(Train179.954초), 두 arm 선택+검산38.932/35.828초다. **1,927SHA·180Train대조/model 재학습·126승자 비용·72×2지표·29case 사후 감사 PASS**다.
- **다음/보존:** 후보 설명/점수의 비교 가능성, 생략/분산/지연음/페달·준비/해결을 갖춘 유지/교체의 큰 오류를 우선 개선한다. 누락 벌점만 올리는 Dev 보정이나 작품별 후보 금지는 하지 않는다. 전체 NCT/Roman/local key/전위/종지·장문2M·독립 평가/운영/생성은 미완료다. Core/주석/UI/서버/MusicSearch/Composition/Claude Motif/별개 dirty/Git 보존, API/merge/commit/push0.
- **정본:** [특징·학습 계약·수치·혼합 결과·반례·재현](records/2026-10-05-train-calibrated-support-balance.md). Report SHA `8039377b21f798a4b60077eabe7a636d5bcbf00bf5c233ad51dddd627247abee`.

## HARM-DEV-20261005-66 — 실제 선택되는 좌우 화음과 조건부 NCT 전이 점수

- **질문/순서 정리:** NCT 전체 구현·정확도 검증은 미완료다. 경과/보조의 한정 점수 연결과 지연/선행/이중 보조 등의 후보 구현을 구별했다. 메인 문서 맨 앞에 원IR/이론 → 후보/선택 → 현재 화음·경계·NCT 공동 검증 → 유형 확장/독립 평가 → 화면/종지/구조/생성의 순서를 추가했다. J0~J2 실행, J3 개발 평가와 J4 큰 오류 개선 병행, J3 frozen test/공개 비교 및 J5 미완료를 명시했다.
- **일반 규칙/구현:** 준비는 완료 왼쪽run 안, 가운데 음의 끝/도착은 실제 후보 경계, 준비/도착은 왼쪽 구성음·가운데는 비구성음·도착은 선택될 오른쪽 구성음이어야 한다. 실제 두 구성음 지지를 요구하고, 별도 shared_support는 양쪽 공통 구성음 두 종류의 경계 이후 지속까지 요구한다. 이는 한정된 화성 지속 credit이지 전체 NCT 정의가 아니다. 고정 -1/2 전이 점수를 정확 공동 DP 안에 연결했다. 도착 시점의 소속만 사용하며 미래 run 끝의 화성은 가정하지 않는다. 원 비구성음 비용·source/철자/voice/tie/grace·cap·봉인 코드는 보존했다.
- **실제 비교/결정:** 원 63graph/44,204edge, 15package/9명명 작품군/72구간, 63선택/9보류, 완전51/부분21·coverage43.7106%·ceiling36/51 유지. 세 조건을 새로 선택하고 72예측 봉인 후 주석을 대조했다. Control 16/51·시간27.0012%·macro51.9033%·경계F173.6842% 그대로. Selected_roles 15/51·26.3011%·73.1343%로 퇴행, shared_support는 기준선과 동일/최종 credit0이다. **음악적 개선 미입증/운영 미채택**. 새 전체 NCT 정확도도 미측정이다.
- **사례/보존:** 쇼팽 Gdim→E♭major 비용129/560에 C5의 조건부 경과 credit -1/28이 붙어109/560이 되고, 맞던 전체 E♭7 559/2800을 이긴다. 실제 공유 구성음의 경계 이후 지속0이면 credit을 보류하여 이 퇴행을 피하지만 새로운 검출 성공은 아니다. 코렐리의 다른 두 선택 변화는 같은 `[124,132)`의 중복 범위/시간 이익0이다. 구성음 생략 과분할도 미해결. 이전18사례의 전체 XML/IR·원ID·모든 조건의 비용/전이 근거와 사후 witness를 보존했다.
- **검증/실패:** 신규27 + 기존관련553 = 580검사/42모듈 PASS, failure/error0, 57.665초. 10tiny DAG×3조건 전수 경로·동점/분할 불변 포함. 초기16검사 중 복원 budget 문제4error와 fixture identity 접근1error를 새 모듈/fixture에서 수정했고 원 점수/기존 검사 조건을 느슨하게 하지 않았다. Actual r1 260.153초/exit0, 조건별 선택+검산50.219/60.472/59.782초. 1,495고유SHA·14전체source·44,204edge·189독립 승자 비용·72×3metric·18case 사후 감사PASS다.
- **다음/범위:** 작은 공통음 관문을 반복 강화하기보다 유지/교체·생략과 장식 설명의 점수 균형, Train 전용 특징/학습 대조와 비중복 평가를 우선한다. 전체NCT/국소조성/Roman/전위/종지·장문2M·운영/생성은 남는다. 원Core/주석/자료자격/UI/MusicSearch/Composition/별개dirty/Git 보존, API/학습/merge/commit/push0.
- **정본:** [규칙·NCT 상태·순서·실제 수치·실패 사례·재현](records/2026-10-05-selected-transition-nct.md). Report SHA `3388bcb8dd0279a7c1781fa946afc3e53f4bd11498c6f87ccf37194ca8c7762d`.

## HARM-DEV-20261005-65 — 식별 구성음·지속 지지 순차 문맥의 점수 대조

- **일반 규칙/구현:** 미관측3음·감/증5음·7음의 soft exposure와, 실제 두 종류 구성음이 지속할 때 source-clock 유효한 짧은 약박 순차 문맥의 cross-run credit을 추가했다. 계수는 기존1/10·-1/2를 사전 고정했고 근음/완전5음 추가 벌점·NCT 면제·같은run 이중credit·가짜지속·후보금지·학습/sweep은 없다. 원63graph/44,204edge와 전체 XML/IR·기존 점수를 보존한 별도 scorer/trial다.
- **실제 결과/결정:**72예측을 참조 개방 전 봉인,63선택/9보류·완전51/부분21·ceiling36/51·coverage43.7106% 유지. Control 완전16/51·시간27.0012%·macro51.9033%·경계F173.6842%와 동일 재생했다. 식별음/결합은16/51·시간26.9312%,순차단독은15/51·26.3011%로 **향상 없음/운영 미채택**이다.10구간 선택변화 중 시간 이익0이며 새 조건의 비용/사례는 진단으로 보존한다.
- **원인/사례:** 쇼팽 `[28,61/2)`의 맞던E♭7을순차단독이Gdim→E♭major로분할했다. 앞뒤음의 실제 소속화음 없이source형태를경쟁화음도빌려쓰는한계다. 코렐리 `[55,56)`는없는B♭를보충한경로대신없는완전5음B를보충한경로 `.188667`이전체C `.193125`를이겨여전히오답이다. 코렐리다른구간은1/4quarter퇴행,이전Sonata/Quartet큰개선은유지했다. 이전11사례모두포함한18case의전체source·원ID·네조건비용·사후witness를감사했다.
- **실패/자원:** 첫trial fixture 참조깊이7error를수정했다. Eager source-clock 준비의r1은4/72에서중단,예측만보존/참조report 미개방이다. 사용될문맥만동일필수관문을lazy검증하고동일조회memoize한r2와4×4선택내용SHA가같다. 점수/계수불변. r2 186.962초,조건별선택+검산30.825/33.665/33.465/32.534초이며정식speedbenchmark는아니다. 사후조회root arms오인KeyError도records[].arms로정정했다.
- **검증/다음:** 신규36+관련517=553검사/39모듈 PASS·44.105초·failure/error0. 1,395고유SHA·14source·44,204원edge·252독립winner비용·72×4metric·18case사후재생PASS다. 다음은 실제선택된앞뒤화음의역할·지속/교체·생략을공동조건으로연결한큰선택오류개선,이후Train전용학습/비중복평가다. 독립blind/fullRoman/전위/종지·장문2M해결·운영승격은미완료. Core/원주석/UI/MusicSearch/Composition/별개dirty/Git보존,API/merge/commit/push0.
- **정본:** [규칙·수치·부정적 결과·원악보 사례·재현](records/2026-10-05-component-support-ablation.md). Report SHA `05b0893a6be4f0406972cfa317112142b3a5a2d51128602163e29ae14c3394b8`.

## HARM-DEV-20261005-64 — 근음 지연과 베이스 회귀 문맥 점수

- **문제/일반 규칙:** 단계63의 늦은 근음 비용이 분산/생략 문맥도 과분할했다. 최근 최저음 근음, 같은 명시 성부의 연속 구성음군/짧은 조건부 순차 패턴, 다시 최저음으로 돌아온 근음, prefix의 두 실제 구성음이 함께 있을 때만 지연 비용을 고정 `1/2`로 완화한다. 실제 근음 onset·노출량·raw 비구성음 비용은 그대로다. 쉼·다른 성부·길이 다른 겹침·철자/clock 미지원·grace·repeat/ending·손상된 앞 문맥은 credit을 보류한다. 작품별 예외/학습/sweep은 없다.
- **구현:** 새 `harmony_root_context_scoring.py`/trial과 감사·검사 추가. 원 63graph/44,204edge/14전체 XML·IR를 SHA 참조로 재사용하여 후보 생성 0회다.72예측을 봉인한 뒤 참조를 열고 세 control winner·비용·지표 동일을 확인했다. 원 봉인 코드·주석·Core·운영·서버·MusicSearch·Composition·Claude Motif·별개 dirty·Git는 보존했다.
- **전체 결과/결정:**63선택/9보류·완전51/부분21·ceiling36/51·coverage43.7106% 유지. Combined 대비 완전15→16/51·시간26.3011%→27.0012%·macro51.6722%→51.9033%·경계F173.1343%→73.6842%, 선택1개 변경/1개 개선/새 퇴행0이다. Baseline 대비 시간4개 개선/2개 퇴행은 남는다. 현재 노출된 개발 자료이며 독립 blind/full Roman/종지 성과가 아니다. **운영 미채택**.
- **개선/미해결:** Chopin `[28,61/2)`의 근음 회귀로 원 E♭7 해석을 복원했다. Quartet/Sonata 이전 개선은 유지했다. Corelli `[55,56)`는 C의 회귀/상성부 지속/조건부 베이스 경과를 찾아 비용 `.230625→.193125`로 줄였지만, 실제로 없는 B♭를 보충한 분리 경로 `.16575`가 계속 이긴다. 해당 사례에 맞춰 factor를 0으로 바꾸지 않았다. 이전 반례를 포함한11case·source note/sound IDs·조건별 비용·사후 witness를 보존했다.
- **검증/실패/시간:** 신규33+관련484=517검사/36모듈 PASS·33.426초. 12tiny DAG×4arm 전수 경로, 모든 interval indexed/unindexed, 미지원/원 source 불변·변조·봉인 검사다. 첫 fixture의 tuple/JSONarray 직접 비교 실패를 canonical hash로 고쳤고, 임시 ceiling의 잘못된 키로 나온0은 실제 `lattice_hit=36`으로 재확인했다. Runner197.298초/exit0, arm 처리(선택+독립 검산)17.987/17.363/17.510/107.094초로 새 문맥 arm이 combined보다 약6.1배 느리다.
- **감사/다음:**1,295고유SHA·72×4metric·세 control·14전체 source·44,204edge·252winner 비용·11case·새 선택 회귀 receipt1개 사후 재생 PASS. 다음은 구성음 지속/교체·베이스 경과·미관측 구성음 보충의 공동 설명과 더 넓은 작품군 대조다. 반복 문맥 계산은 같은 점수/관문을 보존해 줄이고, 장문2M 보류/J3~J5 독립 평가도 남긴다. API/권한 변경/merge/commit/push0.
- **정본:** [규칙·앞뒤 음표 문맥·수치·개선과 미해결·시간·재현](records/2026-10-05-contextual-root-return.md). Report SHA `94087347afb5f40b01e64574e77876ff1a047e1849fb15ff97472c88ff36109c`.

## HARM-DEV-20261005-63 — 시간 근거의 과분할·과병합 점수 대조

- **구현/일반 규칙:** 기존 경계 벌점·후보·source/tie/grace·exact 탐색은 유지하고, 완료 왼쪽run의 기준박자 지지량으로 해결credit을최대1까지조정하며 근음의run내첫양성관측지연을기존missing-root규모1/10의softfeature로추가했다. Rootless 이중벌점/새attack강제/분산형의지속수직완전성요구는없다. 미지원박자는원bounded credit 유지·미지원철자는unavailable이다. 네arm은실험전고정했고학습/sweep/악보별예외0. 기존봉인모듈을수정하지않은private scorer/runner다.
- **전체비교/결정:** 기존72scope중63선택구간을모두fresh·원graph1회생성/네arm공유,9보류·완전51/부분21·후보ceiling36/51·coverage43.7106%유지. Combined는두대표오류개선·시간25.3442%→26.3011%·macro49.7134%→51.6722%·경계F170.4225%→73.1343%지만완전15/51그대로(2성공/2소실),시간4증가/3감소/4동일이다. Root단독은완전14/51·경계F168.9189%퇴행. **운영미채택**. 알려진개발자료/겹치는문맥이며독립blind/fullRoman성과가아니다.
- **개선/반례:** Quartet `[167/2,175/2)`는11run→1개B♭7, Sonata `[105,109)`는2run→Gminor/G♯dim7/E7의3run으로참조일치했다. 그러나Chopin `[28,61/2)`와Corelli `[55,56)`의늦게나온근음때문에맞던전체해석을과분할했고각5/2·3/4quarter를잃었다. 다른Corelli의짧은해결credit조정도1/4quarter퇴행이다. 근음지연을화음변경의증명으로쓰지않으며전후source/원ID·조건별cost·사후witness를모두보존한다.
- **검사/실패/실행:** 신규29+기존455=484검사/33모듈PASS·32.880초. Tiny20DAG×4arm전수최적/동점·동일intervalindexed/unindexed·봉인/변조/보류분모검사다. 첫binder smoke는기존outer검사만으로실패하여nested dependency를확인하는별도binder를추가했다. 회귀launcher의목록필드int오인·사후집계의None합산두임시명령실패도기록했다. Actual518.160초/exit0,graph401.558초·네decoder21.599/21.599/20.817/22.044초이며speedbenchmark는아니다.
- **봉인/감사/다음:**72packet을참조보고서개방전에봉인.14전체XML/IR·63graph44,204edge·11변경/진단사례저장,1,202고유SHA·72×4metric·252winner독립비용·원witness사후재생PASS다. 원Core/주석/권한/운영UI/서버/MusicSearch/Composition/ClaudeMotif/별개dirty/Git보존,API/학습/merge/commit/push0. 다음은펼침/생략/실제베이스·성부지속을경쟁화음과공동설명하는조건검증및작품군비중복평가다. 장문2M보류도남는다.
- **정본:** [규칙·실제수치·개선과퇴행·보존사례·검증·재현](records/2026-10-05-temporal-harmony-scoring.md). Report SHA `9995b34a4c8ff3a0e6b2bc7bd08cefb2ef3d4911a379766ba5e9bb6681c757f0`.

## HARM-DEV-20261005-62 — 장문 공동 선택의 페이지 계산·재개·자원 한계

- **구현/일반 계약:** 원 fine grid·모든 part·spelling/tie/grace/source SHA·전체 노출량/가중치를 유지한 streaming joint session을 추가했다. raw count/run start/spelled signature/exact cost/원 ID 경로를 페이지 사이에 전달하고 same-run을 전체 합집합에서 계산한다. 페이지 승자 stitching/beam/후보 삭제는 없다. 기존 global64cell/256sound 자원 사유만 대체하고20k는global→page상한으로 바꾸며 raw6×tile/누적2M은 유지한다. checkpoint의 counter/binding/seal을 확인하고 원 scorer로 완료 winner를 검산한다.
- **실제 결과/한계:** 같은15package/9가족/72scope 중2fresh·70재사용이다. Quartet582cell/49tile은4page생성/3완료·10,231edge·127.173초, Chopin117cell/10tile은3생성/2완료·11,057edge·63.599초다. 둘 다2M연산에서 선택없이 보류했고 represented전이는9,551,923/8,220,764다. 저장 관문을 넘어도 exact 상태 조합 병목이 남는다. 전체201.949초/exit0. 반복장문1/source6보류·63선택/9보류·15/51·시간25.3442%·coverage43.7106%·경계F170.4225% 그대로이며 새 정확도 상승/장문 완료가 아니다. 새ceiling은미측정,부분inventory를전체후보망으로보고하지않는다.
- **검증/실패:** stream30/trial9+관련회귀453PASS/27.536초, v2표현/변조2PASS/0.335초로 합계455코드검사다. 첫 페이지 실제 disk재개에서204,895/290,972누적연산을 유지했다. v1사후검사는tuple/JSONarray직접비교로실패했고 원결과/코드/실패검사기를 보존한v2canonical JSON SHA대조를 추가했다.1,020고유SHA·72scope/metric·70control·7page/21,288edge·5checkpoint사후확인PASS다. 문서 첫patch의불완전context실패도기록했다.
- **보존/다음:** 두전체XML/IR·전후동결문맥·원candidateorigin/functionalreceipt·page/checkpoint를사례로저장했다. 원봉인모듈/productionUI/서버/MusicSearch/Composition/ClaudeMotif/Core/XML/주석/권한/별개dirty/Git/weights는유지했다. API/학습/merge/commit/push0. 다음은 큰과분할·과병합의선택점수와후보복잡도이며 필요시손실을명시한별도근사arm으로검증한다. 세부저장작업반복·cap일괄상향·악보별정답예외는하지않는다.
- **정본:** [계약·실패·수치·전체source사례·재현·다음](records/2026-10-05-streaming-joint-selection.md). Report SHA `9b241d30c26966741af1c4bcddfa4ba07e2c29a70def5e2648c02adb65973a60`.

## HARM-DEV-20261005-61 — 화성 개발 복귀·source-clock 오류 구간 격리

- **구현/일반 규칙:** 원 note↔sound의 정확 rational clock·concert spelling/octave·attack·release·ID 소유권을 검사하는 새 연구 관문을 후보 생성 앞에 추가했다. 오류 위험은 저장 span+source note 범위의 envelope이며 위치 미확정은 전역 보류한다. 원 sound를 축소/분리/삭제하거나 XML/Core를 수정하지 않는다. Cross-staff/voice는 물리적으로 연속이면 자동 오류로 만들지 않고 검증된 0시간 grace는 보존한다. 독립 XML 재파싱/전체 schema 인증은 아니다.
- **실제 결과:** 15개 전체 악보의15,937 sound중15,936통과/1불연속, multi-note512중511통과/1실패,0시간 grace89다. 쇼팽의190–192/195–196원음표를190–196저장 sound가 이은 사례에서192–195의3quarter 가짜 exposure를 재현했다.187–199문맥은 후보0/전이0/선택없음으로 격리했고196–197정상 인접은 old/new 전체graph9edge와 결과가 같았다. 전체 XML/IR·원note/ref IDs·전후 문맥·설명을 저장했다.
- **회귀/봉인:** 기존72prediction은 새 시간 관문 통과 후 재사용했으며 전부 재추론한 것이 아니다.63선택/9보류·완전15/51·근음+구성음시간25.3442%·coverage43.7106%·경계F170.4225% 그대로다. 오류가 기존72scope밖이라는 점을 명시한다. 주석 개방 전에 source audit/사례/예측을 봉인했고 사후922고유SHA·15source·72scope/metric을 재생했다.
- **검사/실패/상태:** 신규32+관련회귀 합계414 PASS/19.360초. 최초32검사 중1개는 합성 gap의 예상 exposure를0으로 쓴 오류였으며 실제1quarter로 바로잡았다. 실제r1 15.517초/exit0이다. 기존 봉인 모듈/운영UI/MusicSearch/Composition/parser/원본/권한/가중치를 변경하지 않았다. Motif는Claude에 맡긴 범위로 유지한다. 학습/API/merge/commit/push0, 새 연구 진입점 적용·정확도 상승/운영 승격 보류다.
- **다음/정본:** 남은 장문3구간의 source/repeat 보류를 지키는 streaming 공동 선택을 우선한다. [계약·전체 악보 사례·검증·재현·다음](records/2026-10-05-source-clock-quarantine.md). Report SHA `6a77673c46dd01fb92ebb91225d3a3ed071b97ad9f2a473480e1676dd830d216`.

## HARM-DEV-20261005-60 — Claude 프레이즈 비교층 병합·화성→종지 입력 계약

- **병합/범위:** 사용자 지정650ca3b4를 MusicSearch main에fast-forward 병합하고, feature flag/출처/캐시/화면 통합7파일을3e18905b로 로컬 커밋했다. 기존 Phrase·Motif·화성·피드백 입력과 원 worktree/별개 수집14파일은 유지했고 push0이다.
- **계약/화면:** 기본off, phraseLayers=1일 때만 하위호흡/상위Phrase를 계산한다. source/render/observation/code SHA와 원event IDs·half-open decimal-rational 범위를 연결하고 Canonical IR ID는null이다. 전 성부 화성의neutral-gap 종지 관문.58·tie검증·마디별meter를 소비하며 확률/국소조성 확정으로 보고하지 않는다. 악보 점선14/39 전환과Motif 유지를 확인했다. 새범위의 기존feedback 저장은 비활성화한다.
- **검증/실패:**10요청/9XML/6제목 계열의 default/on 기존 주요필드 SHA 동일·layer error0·cache재사용. 관련20PASS·전체658중656PASS/2FAIL·app/node TS PASS다. d9bca19c 원본에동일23검사를 대입해 같은2MotifFAIL/21PASS를 재현했고 임시2파일은 삭제했다. 테스트/기존Motif 계산을 변경하지 않는다. 새레이어 miss35–332ms는 한 번의관측이며 전체속도/정확도 향상으로 부르지 않는다.
- **화성 다음/모델:**musicomp 판별기는 병합 밖으로 둔다. relative fifths와pitch class, unknown전위와근음위치, 공백/전조/변경박자/arrival 매핑·producer threshold를 구별하는 입력계약을 작성했다. Oracle F1을운영성능으로 쓰지 않는다. 원 화성source-clock/장문joint/주요선택오류 순서는 유지하며 학습/외부API/판별기배포0이다.
- **사용자 추가/기록:**Motif는Claude에서개선중이며완료후별도검토·병합한다. 이번발견2기존실패도대조근거로 남긴다. 메인/로그의같은기록59중복만 제거했다. [개발기록·출처·증거·재현·미완료](records/2026-10-05-phrase-layer-merge-and-cadence-contract.md), [종지입력계약](CADENCE_INPUT_CONTRACT_v0.1.md).

## HARM-DEV-20261004-59 — J3e 원 후보 window 재사용·외부 프레이즈층 검토

- **구현/일반 규칙:** 원 IR SHA/정확한 span JSON/최대8entry LRU의 연구 workspace를 추가했다. 원 bytecode의 private dependency binding으로 window만 재사용하며 module globals·기존 봉인 코드·source/tie/Core·후보·점수·decoder 예산을 바꾸지 않는다. 방어적 copy와 source mutation/foreign source 거부, eviction 시 재계산을 검사했다.
- **실제 비교/결정:** 같은72packet 봉인 후 참조 개방,2fresh replay와70재사용으로 모든 선택/후보 출처/비용/metric 동일이다. 두 구간121.391→77.897초(이번 관측35.83%감소),988+630window요청을249+159계산으로 처리했다.63선택/9보류·완전15/51·root+members25.34%·경계F170.42% 그대로이며 정확도 향상/장문 복구가 아니다. r1의 tuple-vs-JSON-array 비교 중단을 보존하고 canonical JSON SHA 비교 r2를 정본으로 삼았다.
- **Tie 점검:**15전체package의512multi-note sound중511통과/1불연속이다. Chopin C4의190–192/195–196 source와190–196저장 sound·source voice1/2를 전체 XML/IR·앞뒤187–199·원 IDs와 저장했다. 기존 functional clock은 false/direct link0이나 raw harmony exposure 위험은 남는다. 해당 범위는 이번 동결5Chopin구간 밖이며 Core/benchmark를 자동 수정하지 않는다.
- **Claude 통합 판단:** 알려 준lower-only984292cc 뒤 최신c6892608의upper/API/viewer 변경을 읽기 전용으로 검토했다. 추가 비교 레이어 통합을 권하지만 실제 merge는 하지 않았다. 원6파일SHA 불변·합성5smoke PASS, 세 외부 평가 report를 SHA/값으로 보존했다. DCML JS upper 선율0.366/blind종지0.371/주석종지0.389는 서로 다른 조건이며 corpus를 여기서 재실행한 것은 아니다. 종지 type만 점수 사용/strength미소비, 잘못된tie와음수duration미거부·변경박자/성부/ID계약·회귀를 통합 전 체크로 남겼다.
- **검증/다음:** 신규21+기존442+추가parser/tie/DCML33=496PASS/28.962초,838고유SHA 불변·72metric재생·24전체providercatalog일치. 원 production/UI/서버/외부 worktree/main/주석·권한/Git 설정·별개dirty수정 보존, 학습/API/merge/commit/push0이다. 다음은 장문 bounded/streaming joint와source-clock 관문, 이어 일반선택오류 개선이다.
- **정본:** [계약·시간·전체source사례·Claude 통합 체크·재현](records/2026-10-04-window-reuse-and-phrase-integration.md). Report SHA `1e0e9257214015536b00e9282b12def7157cb47b26a4d853ca2646d3e59ce6ac`.

## HARM-DEV-20261004-58 — J3d 정확 전이 factorization·밀집 공동 선택

- **구현/일반 규칙:** 별도 prefix-integral·Pareto exact backend와 batched joint decoder를 추가했다. 같은 boundary/count/next spelled signature/actual attacks의 predecessor 최소값을 재사용하고 end별 union/blocker를 다시 더한다. Same-run의 서로 다른 start와 negative bonus·동점 ID/cap를 유지한다. 원 source clock/tie/grace/모든 part·후보·weights·raw cap는 같으며 beam/타일 winner stitching/악보별 예외는 없다. Functional pair의 관측 가능 범위만 index로 좁히되 carry/arrival의 원 전체 span은 보존하고 최종 비용은 원 scorer로 독립 재계산한다.
- **실패→완료:** 단순 Pareto/index만으로는 같은 두 구간이144.314초/2M에서 계속 보류됐다. Profile에서 후보 interval의 전체 악보 재조회와 functional pair 조회가 컸다. 전이 factorization으로 두 구간의 정확 탐색을 끝냈다. Quartet1,282,141factored 연산/3,665,360논리 전이, Sonata675,552/2,199,343이다.2M 숫자는 같지만 **연산 카운터의 단위가 달라짐**을 명시한다. 기존146.011초 중단→121.391초 완료·전체125.428초이며 동일 완료 작업의 엄밀 speed benchmark는 아니다.
- **같은72구간 결과/결정:** 기존61선택 값·source6보류·장문3보류·완전51/부분21·참조/unknown/split/권한을 유지했다. 선택61→63, 근음+구성음 시간24.34%→25.34%·macro45.85%→49.71%·coverage41.47%→43.71%다. 완전15/51은 같고 경계TP49→50/FP19→29/FN14→13·F174.81%→70.42%로 **운영 승격 보류**다. 두 새 선택은 완전 오답이며 계산 복구와 정확도를 구별한다.
- **실제 실패/다음:** Quartet의 원 Bb7 전체가11run/13raw edge로 과분할, Sonata는 첫3quarter Gminor 회복 뒤 G#dim7→E7을 E/G#/B/D/F 하나로 과병합했다. 원 참조4edge witness가 둘 다 존재하여 이제 자원 미확인이 아니라 선택 점수 오류로 구분된다. 다음은 큰 장문 source/후보 생성 재사용·streaming 공동 탐색, 일반 NCT/지속/교체와 applied diminished 해결·5음 과병합 점수 비교다. 한 경계 벌점 또는 특정 악보 예외로 양쪽을 억지 해결하지 않는다.
- **검증/보존:** 신규60+이전382=442PASS/20.720초. 두 backend 각각30tiny DAG exhaustive optimum/lex tie·모든 toy interval 특징·실제128feature comparison·2fresh 추론 receipt·72metric replay·61immutable control을 확인했다.760고유 SHA 불변과 전체 XML/IR·원 IDs·전후 결과2사례를 저장했다. 기존 코드/Core/원주석·권한/production/UI/서버·별개 수정/Git 보존, 외부 API/새 학습/commit/push0이다. Report SHA `d1f6b57e7297954c83e932b02e4418f1231874b67a4338c2404985f9c927f0f0`.
- **정본:** [정확성 계약·단위·실패·수치·사례·재현·다음](records/2026-10-04-joint-frontier-factorization.md).

## HARM-DEV-20261004-57 — J3c grace 소비·타일 후보 global joint 복구

- **일반 규칙/구현:** 원 Core를 변경하지 않는0음가 grace consumer projection과 source-bound receipt를 추가했다. 미지 performed timing을 늘리거나 NCT로 확정하지 않으며 원 grace를 넘는 가짜 direct 성부/NCT link를 보류한다. 전체 part·원 onset/release/tie/ID를 유지한12cell 타일의 모든 후보 interval을 한 global run-aware decoder에 연결한다. 타일별 winner stitching이나 seam 화음 변경 강제는 하지 않는다. 새 global64cell/256sound/20kEdge·raw6×타일/기존2M전이 계약을 명시하고 repeat/meter/source 관문은 유지한다.
- **실제 비교:** 같은72동결 구간, 기존60선택은 그대로 재사용·source6보류 유지·추론 보류6만 실제 실행했다. 새 선택1개로60→61, 전체 일치15/51은 같고 root+members 시간23.99%→24.34%·coverage41.05%→41.47%·경계F174.42%→74.81%다. 후보 ceiling33→36/51이나2개는 여전히 decode2M보류다. 복구된 쇼팽1.5quarter 중1.25quarter 일치·마지막0.25quarter 오선택이다. 원 reference/unknown mask·분모·weights/split/권한을 바꾸지 않았다.
- **큰 한계/결정:** 3장문은 global cap/repeat 때문에 보류, dense4quarter2개는104.993초/41.019초 후2M cap에서 보류됐다. 장문/실시간 문제 해결이나 음악적 완전 정답 향상을 주장하지 않으며 **운영 승격 보류**다. 다음은 장문 joint state/search 규모 축소·정확 계산 재사용, 필요 시 손실/대안/unknown을 명시한 별도 근사 arm이다. 작은 마지막 음 예외보다 큰201quarter 미분석 범위를 먼저 처리한다.
- **검증/보존:** 신규27+관련355=382PASS, 실제r1 162.033초/exit0·exception0. 72scope/60control/reference/metric exact replay·6fresh inference 일치·680고유 SHA 불변, 시도6개의 전체 XML/관찰IR/원IDs와 평가·타일/grace/선택을 저장했다. Parser/기존 점수·production UI/서버/Git·별도 dirty 수정은 유지했다. [계약·실제 수치·한계·사례·재현](records/2026-10-04-bounded-context-and-grace.md). Report SHA `a3bbd1ab7f6083e2ce5a3554396efb34f1620e51b72d1b8b36762dfa83f0d31f`.

## HARM-DEV-20261004-56 — J3b 추가 악보의 실제 추론·정답 대조

- **계약/실행:** J3a의16악보 중 원 holdout K282를 제외하고15악보/9명명 기반 작품군을 확대 개발 자료로 검사했다.14악보/8가족 source-ready, K283의 중복 measure/local onset은 원본 수정 없이6문맥 보류다. 고정 J2e 점수와 lane별 결과 비사용 quantile로72문맥을 먼저 동결하고 **모든 prediction SHA 봉인 후에만 주석 라벨을 개방**했다. 학습/Dev tuning/독립 blind 승인/운영 변경0이다.
- **실제 수치:** 60선택/12보류, 완전51/부분21, 전체 일치15/51(29.41%), root+members 시간23.99%·macro44.77%·coverage41.05%, 경계F174.42%다. 원 보존24hit11/51(21.57%)와 확장 후보망 ceiling33/51(64.71%)를 분리한다. 완전 문맥은 정답 선택15/후보 포함 선택오류18/확인된 부재15/포함 미확인3이다. 이전322문맥과 다른 표본이며 paired 향상이나 full Roman/전위/조성 정확도로 부르지 않는다.
- **큰 문제/진단:** Sparse lane의3attack이 긴 문맥을 만들어 context 관문에서 보류하고, seed grace의0음가로3문맥이 보류됐다.6추론 보류의 적격210.5quarter가 시간 coverage를 낮춘다. Reference pedal75cell/871/12quarter 미지원과 한 문맥의 약1.893e-14quarter overlap도 분리했다. Expanded oracle의 retention 문자열은 false control 탓에 실제 손실33을 뜻하지 않으므로 원 결과를 유지하고 정확한 cross table로 정정했다.
- **검증/사례:** 신규15+관련340=355PASS/9.468초, 실제r1 471.319초/exit0·exception0·사후602고유 SHA/72sealed prediction/metric exact replay다. 초기 fixture 누락2실패와 coverage 진단 key 실패도 상세 기록에 보존했다. 평가 후8사례의 전체 XML 사본/관찰IR/원note IDs/범위·주석·선택을 저장하고 노출 ledger v3에9가족을 추가했다. Source 보류 K283도 미래 새 blind 가족에서 제외하며 원 split/rights는 유지한다.
- **결정/다음:** 확대 기준선 측정 완료, 낮은 정확도이므로 운영 승격 보류다. 같은 동결 범위의 bounded long-context/carry와 grace 계약→큰 후보/선택 표현 오류→공개 모델 native adapter 비교를 우선한다. 기존 Core/XML/주석·점수/learned 미채택·UI/서버/Git는 유지한다. [개발 계약·실제 표·오류·사례·재현](records/2026-10-04-expanded-score-benchmark.md). Report SHA `71926c9155b81fd1d9792ec6cf1b79c31a1b9aa2e45c636e31e227990f3bf182`.

## HARM-DEV-20261004-55 — J3a 공통 평가와 확대 작품 준비

- **구현/계약:** 별도 common evaluator·onset 범위 adapter·동결 재현/메타데이터 runner를 추가했다. Exact quarter 시간/경계와32분 표본을 분리하며 근음/구성음 성공을 full Roman/전위/조성 성공으로 승격하지 않는다. Prediction 보류는 지원 reference 분모에 남는다. 작품군/score·annotation hash/lineage alias로 개발 중복을 검사한다.
- **실제 재현/정정:**33악보/19작품군/322문맥의 J2e/J2f 전체·시간·macro·경계 숫자를 동일하게 재현했다. 후보 포함140/부재101/보류 미확인15다. J2f의 나머지116을 전부 확인된 부재로 해석한 문장을 정정하며 원 report/예측/학습결정은 보존한다. 최초 실행은 null ceiling을 bool로 요구해 출력 전 실패했고 unavailable category로 수정 후 검사/재실행했다.
- **준비 자료/이력:** 기존392package/145명명 기반 가족의 메타데이터에서 알려진 개발/노출53·정렬/source미완전144·identity미해결5·이력미확인준비190을 구별했다. 후보190은83가족이며5collection당2가족을 결과 비사용으로 골라10가족/16악보를 stage했다. K279의 split 이전 실험과 비창08의 viewer/사용자 검토를 ledger에 보존하고 whole family를 새 blind test에서 제외한다. 원 holdout/권한을 자동 변경하지 않는다.
- **재실행/검증:**r1과 ledger v1은 보존하고08가족 노출을 추가한 v2로r2를 실행했다.243PASS/3.147초(신규38+관련205), 최종r2 1.505초/exit0·1253고유 SHA 불변·644arm별 채점(322문맥×2)·3output이다. 준비 metadata만 읽고 reserved 원 score/IR/주석 내용은 열지 않았다. Public repo 조회 후 commit pin은 HTTPS helper/socket 제한으로 미확정, 설치/모델 실행0이다.
- **결정/다음:** J3a 준비 완료, 독립 정확도/논문 재현/공개 모델 비교/운영 적용 미완료다. 다음은10가족의 전체 노출/source·정렬/실행 관문 확인→첫 확대 평가→ChordGNN native adapter와 격리 실행 준비다. 기존 J2f 미채택·Core/XML/원주석·UI/서버/Git/원 권한은 유지한다. [개발 계약·수치·목록·출처·재현](records/2026-10-04-common-benchmark-preparation.md). Report SHA `05384c37daba6edd6f99d77a612451f0ede81966a3d3c2542c892a26a767a682`.

## HARM-DEV-20261004-54 — J2f 합집합 구간·기능적 해결 근거 Train 학습

- **구현/계약:** 별도20특징 weighted exact run decoder·training-only loss adversary·평균 capped passive-aggressive learner와 frozen runner를 추가했다. J2e 후보/원 source·literal/functional root·None mask·raw blocker·6segment/2M cap을 유지한다.5epoch/cap1/10/bound4/time+boundaryλ1/4 단일 arm을 사전 고정했고 승인된 Train만 학습한다. NC 연구 계약·원 manifest 미승인·외부API/운영/배포 제한은 유지한다.
- **검증/재실행:** 신규24+회귀174=198PASS/2.778초·4AST. Exhaustive optimum·원 고정 비용 일치·union/split·loss/unknown/반올림·승인/Dev 분리·physical source/LICENSE/receipt guard·collision/clip·모델 hash를 확인했다. r1은 epoch2의40/118에서 학습용 metadata 오표기를 발견해 중단했고 output0이다. Training은 reference 사용 true, inference는 false로 수정한 뒤 점수/설정을 바꾸지 않고 r2를 실행했다.
- **실제 학습:** 15작품군/118reachable Train·590tick·549update/27margin충족/10resource skip/4collision이다. Collision4회는 Corelli 한 문맥의4epoch이며 독립4사례가 아니다.270Train 중 나머지152의 보류/미지원 이유와 전체322 평가 분모를 보존했다. r2는898.953초/exit0이다.
- **실제 결과/결정:** 같은33악보/19작품군/322문맥·완전256/부분66에서 전체 일치52→55/256이지만 시간31.97%→30.33%·macro39.08%→37.03%·경계F157.18%→44.26%로 **새 가중치 미채택**이다. 경계FP94→25 대신 FN228→310,288선택/34보류·새 자원 보류0이며 후보 ceiling140/256은 동일하다. Dev 전체7→9도 시간36.12%→34.95%·F162.03%→49.66%와 함께 보고한다. 회복16/퇴행13, 시간43이익/53퇴행을 숨기지 않는다.
- **원인/사례/다음:** global run/turnover/extra-member 비용이 커져 필요 교체/7음까지 억제한다. Mozart의긴 C#dim run, Corelli 병합, Chopin7음 제거, 직전 Sonata03-2 회복의 재퇴행과 Fminor 회복을 같은 비용 분해로 저장했다. Corelli F#aug/F#major의20차원 정확 벡터 동일도 확인했다. 다음은 J3 독립 작품 공통평가/공개 모델 비교 준비와 주요 문맥 표현 오류 개선이며 Dev 반복 tuning은 하지 않는다.
- **보존/정본:** 850고유 input/code SHA 종료·사후 불변·4output/9,330,688B. Report SHA `77350ac9eb04f11e663a6adb6d1d7fd2ff5b98d99b8495c42b8413308fc52594`. 원 Core/XML/주석·후보/예측·권한·운영UI/서버·다른 수정/Git를 유지했다. [실험·실제 사례·cost proof·출처/재현](records/2026-10-04-functional-run-learning.md).

## HARM-DEV-20261004-53 — J2e 기능적 6–4 후보와 선택된 다음 화음의 해결 점수

- **일반 규칙/구현:** 원 major/minor 표면 후보의 완전 관측 합집합과 실제 최저5음 노출에서 dominant-origin6–4 후보를 별도 추가한다. Literal/functional root·원 group·원 source IDs를 보존하며 source/Core를 변경하지 않는다. 다음 **선택된** dominant 화음과 실제 최저음 유지·4→3/6→5, 또는 Unit26 dominant-family와 leading tone/7음 direct geometry를 고정 점수에 연결한다. 다음7화음도 target triad core로 비교한다. Local key/Secondary·cadence 확정이나 polyphonic voice guessing은 하지 않는다.
- **검증/실행:** 신규30+기존151=181PASS/1.098초·4AST. Physical tampering, 원 후보 불변·원 cap, source clock/철자, unresolved 보류, exhaustive decoder, whole/split invariance, gold/title/key answer 비사용을 확인했다.20문맥 smoke는 complete=false/39.592초이며 코드 검토에서7화음 target 지원을 보완한 뒤 전체322 비교를 시작했다. 비용과 cap는 tuning하지 않았다.
- **실제 결과:** 449.734초/exit0,33악보/19작품군/322문맥·완전256/부분66이다. 후보 ceiling132→140/256, 실제 전체 일치51→52/256·시간30.46%→31.97%·macro37.59%→39.08%·경계F156.72%→57.18%다. 후보 control만으로는 semantic 경로와 지표가 같았고 해결 근거를 켰을 때만 바뀌었다.288선택/34보류·새 자원 보류0/분모 제외0을 유지했다. 새 기능적 후보7문맥 선택, 완전 회복1/퇴행0·시간16이익/2퇴행이며 모두 음악적 정답으로 확정하지 않는다.
- **사례/결정:** Sonata03-2 `[14,31/2)`는 surface Emajor/B를 functional root B로 보존해 B7→E와 실제 동일 bass에서 완전 root+members/time 일치로 회복했다. Corelli/Mozart 시간 개선과 Chopin/Quartet의 내부 leading-tone motion 과분할 실패를 함께 기록한다. 경계FP9증가·precision 저하·local key 미지원이 있어 **운영 적용 보류**다. 다음은 새 run/전이20특징 train-only 학습이다.
- **보존:** 모든 원 입력/기존 코드·예측/권한/운영UI·서버/Git를 유지했다.847고유 input/code SHA 종료·사후 불변,2output/15,832,241B. Report SHA `e3983219bc2b53fd102302514cecc74e9e98b54290cc3d295e3023c6e912f661`. 새 training/API/commit/push0이다. [정본과 실제 사례/재현](records/2026-10-04-functional-candidate-scoring.md).

## HARM-DEV-20261004-52 — J2d 음악적 근거의 실제 공동 점수 연결

- **일반 규칙/구현:** 별도 source-bound scorer/exact run-aware DAG와 두 고정 arm을 추가했다. 동일 근음+철자 signature의 인접 edge는 합집합 run으로 점수를 매겨 raw 분할 보상을 없앤다. 원6segment/후보/blocker를 유지한다. 조표 prior·박절 nonmember·최저 지속음·source-clock-consistent 동일 voice의 경과/보조 후보를 실제 선택 비용에 연결했고 NCT 확정/면제·local key/structural bass 추정과 구별한다.
- **검증/실행:** 신규35+기존109=144 PASS/1.409초·4AST. Full pinned IR→기존 measure revision→bundle source hash/ID, 원 pitch/octave/tie/source note clock, whole/partition score 동등성과 exhaustive 최적해·정확 유리수/정수 scale·cache cold/reuse·physical tampering/보류를 검사했다. 앞선40문맥 partial 두 실행은 중단하고 output을 생성하지 않았다. Profiling 후 조회/전이 cache와 정확한 정수 score 단위로 재실행했다. 규칙/weights/cap를 변경해 속도를 얻지 않았다.
- **실제 결과/결정:** 최종494.708초/exit0, 같은33악보/19작품군/322문맥·완전256/부분66이다. J2a→run-only→music의 전체 일치50→50→51, 시간30.15%→29.56%→30.46%, macro38.35%→37.46%→37.59%, 경계F157.26%→56.08%→56.72%다. Dev music의 시간32.04%/전체7도 보고하되 전체 퇴행을 숨기지 않는다. 근거 연결은 완료했지만 **새 score 운영 적용은 보류**다.
- **실패/사례:** 기존31보류+새2M보류3으로288선택/34보류, 전체 분모에서 제거0이다. Music의 완전 정답 회복6/퇴행5/유지45를 기록했고10행/9sample의 gain/loss와원ID·SHA·범위를 저장했다. Mozart Bbaug→Bbmajor 및 Corelli D/E 화음 개선, Chopin의5구성음 후보 과선택/기능적 root 미구현을 함께 보존한다. 원본 imported `V(64)/vi`는 surface Bbminor와 dominant root F가 다를 수 있어 reference 오류로 단정하지 않는다. 다음은 일반6–4/적용화음의 후보·점수 연결→새 run train-only 학습이며 특정 마디 예외가 아니다.
- **보존:** 원XML/Core/주석/후보/이전 코드·예측/권한/운영UI·서버/Git와 별개 수정은 유지했다.841고유입력/코드 SHA 종료·사후 불변,3output/9,623,473B. Report SHA `808b72c6db9d66bf91fc79ad58b3d0249fb34757dd5490ce09cfd445656aa928`. 새 training/외부 API/commit/push0이다.
- **정본:** [근거 계약·두 arm/분모/split·실제 사례·자원 실패·재현·다음](records/2026-10-04-musical-evidence-scoring.md), [실제 report](../../output/harmony-evidence-scoring-2026-10-04-r1/report.json).

## HARM-DEV-20261004-51 — J2c 시간·의미 경계 손실 학습

- **목적/계약:** J2b 과병합에 대응해 같은11관측 특징과 원322문맥에서 시간 오류만 반영한 arm과 의미 경계 FP/FN까지 반영한 arm을 비교한다. λ=0/1/4·5epoch·update cap1/10·bound4를 실행 전에 고정했고 train만 fit한다. 기존 후보·6segment·원 보류·unknown mask/부모 예측·원 권한을 유지한다. 특정 작품 예외·Dev tuning은 없다.
- **구현/검증:** 별도 exact loss-augmented adversary와 평균 capped passive-aggressive margin 학습·label-blind 추론·동결 비교 실행기를 추가했다. 신규21+기존106=127 PASS/1.325초·3AST 통과. 경계 중복·same-signature 분할·유리수 시간·exhaustive 최적해·collision/clipping·물리 guard/보류를 확인했다.
- **실제 결과:** 647.491초/exit0, 각110reachable train/5epoch·550tick, 시간 arm492/시간+경계505업데이트다. 같은322전체·완전256/부분66·291선택/31보류를 유지했다. 전체 일치 고정50→42/45, 시간30.15%→28.37%/26.71%, 경계F157.26%→48.01%/41.89%로 **두 weight 채택 보류**다. Dev 시간30.45%→32.46%/31.35%의 소폭 개선과 전체 일치6→4/5·macro/경계 퇴행을 함께 기록한다. 운영 점수/UI는 유지한다.
- **원인/사례:** 12행/11문맥의 개선·퇴행을 원 context/search SHA·group/범위·원주석에 연결했다. Mozart F장/F단 및 F증/F장 경쟁 pair의11차원 Fraction 벡터가 같음을 실제 확인해 별도2사례로 저장했다. Collision은40회/11문맥,26회/7문맥이며 inference tie-break가 정답일 수 있으므로 모두 추론 오답이라고 하지 않는다. 음수 segment 비용과 same-signature 분할의 보상으로6raw edge 선택0→34/39도 발생했다. 다음 J2d는 분할에 덜 흔들리는 feature version과 조성/동일 성부 NCT·해결/교체 근거를 점수에 연결하는 큰 단위다. Dev tuning으로 반복하지 않는다.
- **보존:** 735고유입력/코드 SHA 종료·사후 불변,5output/11,771,744B. Report 물리SHA `abea4f003bc6dae1947ede55b23ed2c7da9944e079e59015f957ec472d378193`. 원 XML/Core/주석·기존 후보/코드/예측·학습 권한·운영UI/서버·다른 tracked수정은 유지했다. 외부 API·상업 적용·checkpoint 배포·Git commit/push0이다. 사후 상세 출력 truncation은 축약 재조회했으며 원 결과는 변경하지 않았다.
- **정본:** [시간·경계 loss 계약과 비교 결과](records/2026-10-04-time-boundary-margin-learning.md).

## HARM-DEV-20261004-50 — J2b Train 전용 구조화 가중치 학습

- **범위/구현:** 별도 averaged structured perceptron·연구 추론/사용 계약·pinned 실행기·21검사를 추가했다. 동일11특징과 원6segment DAG를 유지하고 train 주석에 compatible한 원 경로를 target으로 쓴다. 후보 삽입·Dev 업데이트/epoch 선택·unknown→false·NCT 낙관 면제는 없다. 같은322문맥의 고정 baseline을 먼저 재확인하고 학습 후 전체 분모를 비교한다.
- **사용 조건:** 다섯 DCML LICENSE/README의 CC BY-NC-SA4.0을 확인했다. 사용자 내부 테스트 요청을 한정 로컬 연구 범위로 기록하며 licence waiver나 상업 이용 허가로 해석하지 않는다. 별도 실험 계약은 train27entry/원manifest·부모·출처SHA를 연결하고 pending/출처 변경/외부 사용은 거부한다. 원33manifest/schema의 미승인 상태는 그대로다.
- **실제 학습/결과:** 388.660초/exit0, train270중reachable 완전110에5epoch/550tick·업데이트340을 수행했다. 제외160과 Dev52를 평가에서 제거하지 않고322전부 비교했다. 전체 일치50→46/256, 시간 root+members30.15%→28.84%, 경계F157.26%→41.12%다. Train44→40/205, Dev6/51동일·시간30.45%→29.76%·family macro31.71%→36.41%의 trade-off를 보존한다. 경계 TP209→125/FP78→40/FN234→318로 과병합이 증가했다. 새로운 weight 채택 보류, 기존 score 유지다.
- **검증/보존:** 최종 신규21+기존85=106 PASS/1.156초·Python3AST 통과. 732고유입력/코드 SHA 종료 불변, report3,764,611B/SHA `0cf236c2a949f2158ca1cbb87ce87cc673e526e093ae7a381d5d5367afffc03a`, 연구model581,660B/SHA `69237e290b021a932c5674738206cf3f108aed44b04e1069404a1b63f67d5ad7`. 원XML/Core/주석/후보/과거예측/권한/운영UI/서버/Git 보존, 상업 운영 적용·외부 API·원자료/weight 배포·commit/push0이다.
- **사례/다음:** 합치기가 맞은 Corelli Dev 사례, Chopin 화음 종류 개선, 이전 성공Sonata03-2 마지막G 경계 병합 퇴행, Chopin4segment→1segment 과병합을 앞뒤 원음/부모SHA·group/범위·양쪽예측·특징별 비용에 연결했다. 사후진단 첫 도구 출력 truncation/JSON실패는 파일 미생성 후 중복 상세refs를 축약해 교정했다. 원 model/예측은 변경하지 않았다. 다음은 train-only 시간/경계 손실과 실제 교체/NCT·역할 근거를 연결하며 후보 ceiling은 별도로 유지한다.
- **정본:** [학습 원리·자료 조건·결과·재현·한계](records/2026-10-04-structured-weight-learning.md).
- **사후 검증:** 변경4문서 strict UTF-8/replacement0·로컬 링크275/누락0·메인/로그/계획 등록 각1개·기록50 중복0·diffcheck exit0이다. 임시 중복/실행 중 문구는 제거했고 기존5개 LF→CRLF 경고만 있다. 새 출력3파일4,374,867B의 물리 SHA와732입력/코드 불변을 재확인했다.

## HARM-DEV-20261004-49 — J2a 음악 점수·원 후보망 직접 공동 선택

- **구현/일반 규칙:** 별도 scorer/exact DAG decoder와 분리 trial·33검사를 추가했다. 구성음/미설명/누락/복잡도·실제 attack/근음 이동/구성음 교체를 고정 유리수 비용으로 쓰고 상태에 직전 철자 signature를 보존한다. 원6segment/후보/이전 보류는 유지하고 prefix/final24 pruning 없이 직접 선택한다. 일관 NCT/7음·조성/적용화음/박절/structural bass는 unknown mask로 남기며 낙관 NCT 상계를 면제하지 않는다.
- **실제 비교:** 같은322문맥/33악보/19작품군을252.139초에 처리했다. 완전 평가256중 기존5→retained music37→direct joint50전체 일치, 시간 root+members2.84%→19.39%→30.15%다. Segment-only는 전체37이나 시간31.01%/경계F157.35%로 joint30.15%/57.26%보다 높다. Joint precision72.82%/recall47.18%로 과분할과 경계 누락의 trade-off를 보존한다. 원 보존 손실67중 완전 회복10, 기존 오답→정답46·정답→오답1이다. 원 후보 ceiling132는 그대로다.
- **범위/결정:** 연구용 미학습 hypothesis를 실제 선택하지만 Roman/전위/key/NCT/cadence 음악 정답 또는 UI 승격은 아니다. 학습 자격을 조사하니33package 모두 automatic_training/model_training 미승인이고 licence unverified다. 자격 자동 해제·학습·외부 API 전송0, 고정값은 첫 결과를 본 뒤 tuning하지 않았다. 다음은 출처 사용 조건 확인→적격 train 학습과 역할/기능 점수 연결이다.
- **사례/실패:** Sonata03-2의 B7→C→G는 보존24 밖에서 완전 회복했지만 quartet의 장식음 별도 화음 과분할/처음 오판은 남았다. Mozart K280 C7→C3화음 퇴행1개를 기록했다. 첫 실행129번째의 길이0 sound 거부를 교정하여 원 ID/state를 보존하고 양의 노출에는 더하지 않았다. 음수/중복/source/objective 오염 거부는 유지한다.
- **검증/보존:** 최종 신규33+기존52=85 PASS/0.881초; physical runner의 parent receipts는 synthetic이다. 입력/코드718 SHA 종료 불변, report1파일4,075,400B/SHA `e197fc16b2199f985a39c780aa2468606cdaf8188c4fc7aad920b8e777c49825`. 코드2개·검사1개·화성 개발 문서와 계획 연결만 추가/변경했다. 원XML/Core/주석/후보/기존 결과·자격/운영UI/서버/Git 보존, 학습/commit/push0이다.
- **정본:** [점수 계약·4arm/split 수치·반례·재현·한계·다음](records/2026-10-04-scored-joint-decoder.md), [실제 report](../../output/harmony-scored-decoder-2026-10-04-r1/report.json).

## HARM-DEV-20261004-48 — 원 후보망의 정답 coverage와24path 보존 손실

- **목적/일반 규칙:** 첫 recall의191후보 누락을 원 spelled 후보망 표현 불가와 탐색/보존 손실, 원 lattice 보류로 나눴다. 같은33악보/19작품군/322문맥을 전부 처리한다. Gold는 evaluator의 최소 DAG witness에만 사용하며 선택/학습·음표/화음 발명·cap 변경으로 연결하지 않는다.
- **구현:** 별도 lattice-recall v0.1과20검사를 추가했다. Native context hash/시간점·edge·모든 reading origin·철자/원 state/보류를 확인하고 각 점의 최소segment witness를 구한다. Local 시간 coverage와 연결 가능한 full partition은 별개다. 이전 recall을 재계산해 완전히 같음을 확인했다.
- **실제 결과:**132.356초/exit0, full256중 원 lattice hit132(51.56%), 검사 가능한 lattice241중54.77%, 기존 retained hit65(25.39%) 그대로다. 누락191은 retention/탐색67·local spelled 후보 부족85·범위/연결22·6segment 초과2·lattice 보류15다. 선택 오류60/정답 선택5, 부분/미지원66을 유지한다. 원주석 의미 변화의 시간점 자체 누락0은 모든 경계 문제가 해결됐다는 뜻이 아니다.
- **사례/다음:** Quartet Fminor→Cmajor가 원2segment로 존재하나 출력24에 없음, Sonata의 local shape coverage3/8이나 compatible edge1/8로 진행 불가, quartet F→E→D만 관측되는 창의 Cmajor 후보 부재, Chopin 최소10segment 반례를 기록했다. 범위 진단은 마감하며 다음은 J2 음악 점수·자격 확인 train 학습·원 lattice 직접decode다. 51.56%는 oracle 표현 가능성이지 선택 성능 상승이 아니다.
- **검증/보존:** 신규20+기존32=52 PASS/0.869초. Synthetic physical runner와 실제 corpus 저장자료를 구별한다. 원714입력SHA 종료 불변, 새report1파일988,872B/SHA `d2be3a53917c627c22c7e64b425dfdd462e94a1cfed3c42d8d0330dff6c05acc`. 원XML/Core/주석·candidate/search/기존선택·자격/운영UI/서버/Git 보존, 학습/공개 모델/commit/push0이다.
- **정본:** [계약·원인별 수치·4사례·재현·한계·다음](records/2026-10-04-lattice-candidate-coverage.md), [실제 report](../../output/harmony-lattice-recall-2026-10-04-r1/report.json).

## HARM-DEV-20261004-47 — J0 범위 마감·후보 recall@24·첫 실제 선택

- **요청 반영:** J0 첫 자료 정리를 최대30분으로 제한하고 기존33악보/19작품군/322문맥을 전부 사용했다. 새 전수 정렬/DB 없이 manifest와 노출·자격을 보존했다. 편곡 재현에서는 Melody 화음 파트의 기보가 target 정답이며 분석에서는 weak/silver라는 task별 구별을 계획/생성 문서에 반영했다.
- **구현:** 별도 `harmony-candidate-recall-0.1.0` 평가기와 라벨 없는 고정 tuple 선택기를 추가했다. 기존 최대24개 complete path를 정답으로 재생성하지 않고 실제 selected prediction을 저장한다. 평가가 DCML fifths의 절대 root+spelled members를 유리수 시간에서 비교한다. 전위/key/function/Roman/cadence 전체 정확도나 최종 NCT 선택은 아니다.
- **첫 실제 수치:** 322전부 처리/33.277초, 완전 평가256중 recall65/256=25.39%, 첫 선택5/256=1.95%. 후보 있음/정답 없음176+후보 없음15=191, 후보 정답 존재/선택 오류60, 정답 선택5, 부분/미지원66이다. Eligible time coverage76.73%, 선택 root21.70%/root+members2.84%, 저장 path oracle45.04%/29.09%다. Oracle는 성능이 아니며 겹친 개발 train270/dev52문맥이다.
- **사례/다음:** Quartet m207에서 B♭minor triad 정답이 있는데 A음을 추가한7화음 후보를 선택한 반례, m110 C-major 정답이6후보에 없는 반례, Sonata1/2 m1 후보0, Chopin applied형 구성음 일치 표본을 저장했다. 다음은 원 lattice 표현 불가와24path 보존 손실을 구별하고 학습 점수로 연결한다. 이 결과만으로 후보 누락 원인을 단정하거나 특정 작품 룰을 추가하지 않는다.
- **검증/보존:** 신규14+기존 search18=32 PASS/0.728초. 최초1 FAIL은 fixture adapter alias를 deepcopy하여 교정했고 gate는 완화하지 않았다. Physical synthetic runner와 실제 저장자료를 구별한다. 원입력390SHA 변경0, report1파일1,822,835B/SHA `f12397eb53544dfa153974a9f0006f7cb06467d09c10ce1ecaf8da2e2d21f0eb`. 원XML/Core/주석/기존자료·자격/운영UI/서버/Git 보존, 학습/공개 모델/commit/push0이다.
- **정본:** [지표·분모·4사례·재현·한계·다음](records/2026-10-04-candidate-recall-and-first-selection.md), [실제 report](../../output/harmony-candidate-recall-2026-10-04-r1/report.json).

## HARM-REVIEW-20261004-46 — 실제 선택·DCML 학습·공통 benchmark 우선순위 검토

- **요청/판단:** 사용자 검토의 실제 화음 선택·정확도 공백, DCML 가중치 학습, 공개 모델 공통 평가를 채택했다. 경계×화음 공동 후보는 이미 구현돼 있어 “경계를 먼저 확정하기 때문”이라는 진단은 정정한다. 공동 추론만으로 조성/NCT/누락이 자동 해결되지는 않는다.
- **실제 확인:** 기존 search의 interval×reading/끝·segment DP와 기본6segment/24path, joint comparison의 selected/preferred=null·accuracy=false, 기존 인공 분산형 선택 benchmark를 확인했다. 과거 DCML snapshot은 준비392/정렬 적격333이며 오늘 독립 작품 수나 학습 허가로 재해석하지 않았다.17개 DCML 폴더와 Melody XML 한 파일의 두part/72마디·P2 chord member272/harmony tag0을 확인했다. Reserved 내용은 열지 않았다.
- **개발 순서 변경:** 단계45 뒤 지연/재등장 세부 규칙 선행 대신 J0 평가·자격·split → J1 candidate ceiling/첫 선택·정확도 → J2 학습 점수 공동decoder → J3 공개 모델 frozen test → J4 주요 오류/악보 피드백 → J5 팝·편성·구조/생성 소비를 현재 계획으로 삼는다. 기존 evidence/Core/과거 결과/규칙은 유지하고 가중 특징·설명으로 재사용한다.
- **일반 계약:** 음악적 해결·생략의 비전형성은 곧바로 전체 탈락이 아니며 unknown mask/soft evidence와 참조 무결성 hard constraint를 구분한다. 학습은 train only, 작품 가족/판본/변조 및 코퍼스 간 중복과 기존 사례 노출을 분리한다. Melody 화음 파트는 weak/silver이며 기능화성 gold로 자동 승격하지 않는다. 기존 eligibility=false를 자동 해제하지 않는다.
- **공식 비교 근거:** DCML 주석은 모든 경과/보조음 gold가 아니다. ChordGNN의 CSR/32분음표 grid와 onset 정확도·라벨 축을 구분한다. AnalysisGNN의 개발 중/RN resolve·onset 집계 TODO 및 사전학습 자료 중복을 명시한다. 논문 수치와 다른 로컬 split 수치의 직접 순위 비교는 금지한다.
- **변경/검증 범위:** 상세 검토 기록 추가, 메인 개발 문서·이 로그·장기 통합 계획의 현재 우선순위 링크 변경. 변경4문서 strict UTF-8/replacement0, 로컬 링크261개/누락0, diffcheck exit0이다. 단계45 report·정책/실행기의 SHA는 정본과 일치하며 문서 변경이라 unit test는 재실행하지 않았다. 새 선택기·가중치 학습·정확도·외부 모델 실행·운영UI·원주석/자격 변경·commit/push는0이다.
- **정본:** [채택/반박·현재 코드·공동 점수·데이터 자격·공통 평가표·J0~J5](records/2026-10-04-joint-decoding-and-benchmark-review.md).

## HARM-DEV-20261004-45 — 경쟁3화음·7화음과 해결 의무의 공동 비교

- **일반 규칙/구현:** 같은source/key/completion/partition의one-slot exact triad/seventh extension을 비교하는정책·pinned saved 실행기·전수pilot·검사26개를추가했다. 추가7음의모든원note/tie/음가·3화음아래조건부NCT/미설명범위·7화음ordinary경로를분리한다. 의무개수·단순LT양성으로3화음을택하거나7음관측만으로7화음을택하지않는다. Adjacentfunction가정차이는명시하고다른key/성부/경계의근거합집합은금지한다.
- **실제범위/결과:** Sonata1번1악장13~15마디`[49,61)`의control/linked각2,315후보와각1,395쌍(5key각279)을전수검사했다. 추가음관측645쌍,3화음아래일부미설명control625/linked605. Linked LT역할지원275는whole/joint8과다른지표이며seventh지원0/전체path보류2,315다. 재등장probe235는고유D♭→재등장D♭→C route1개의반복으로독립235사례가아니다.
- **음악적핵심:** selector1281의E♭3화음→A♭에서G→A♭가해결되어도D♭5의11/3quarter가설명되지않는다. 경쟁1201의E♭7화음ordinary실패로자동3화음선택을하지않는다. Source D♭ outgoing이없지만뒤D♭→C 실제edge를찾아전략진단에저장했다. `[53,109/2)`의연결/실제쉼/음악적성부는발명하지않고credit0/원False를유지했다.
- **검증/교정:** 최종신규26/25.511초·기존97/89.143초 PASS. 작은 genuineXML/native body와synthetic상위receipt ancestry를구별한다. 최초fixturealias14ERROR,동시adverse+nonmember원인1FAIL,전체archiveTrue오기대로actual출력전거부를기록했다. Alias직접import·복수failureaxes·원parent의전체archiveFalse와두완전request계약으로교정했고근거gate를완화하지않았다. Full-hold not-applicable·key/plan/terminal/구현SHA보호를추가한r2를정본으로하고r1/중간검사를독립표본으로합산하지않는다.
- **실제 실행/보존:** r2 actual26.343초/exit0, 단일 decoded325,191,862B, 출력4파일1,546,675B. Report SHA `a935b0f75900d51377defee89c8e6a5b05914096ce2e6422a171700b8667fffc`. 292입력+3출력의 물리 길이/SHA 오류0, 전체 원위치/쌍/key 분리 검사와 선행79SHA 불변. 원XML/Core/주석/이전결과/별개tracked5·서버/운영UI/Git 보존, commit/push0. Python5개 AST·문서4개 strict UTF-8/로컬 링크226개·diff 검사 통과. 기존5개 LF→CRLF 경고만 있다.
- **상태/다음:** 최종화성/NCT/key/cadence·Gold/training·운영악보적용은아직아니다. 다음은ordinary외지연/동음재등장/비인접해결을실제route와반례로검증하고생략/분산형·경쟁조성/경계전체path에연결한다. 여러작품·편성독립검증과악보layer/피드백,구조/작곡편곡소비순서를유지한다.
- **정본:** [음악정책·실제사례·전체수치·실패·재현·한계](records/2026-10-04-triad-seventh-obligation-policy.md), [실제report](../../output/harmony-candidate-obligation-2026-10-04-r2/report.json).

## HARM-DEV-20261004-44 — Sonata 성부 가정·해결·전체 진행 전제 대조

- **목적/일반 규칙:** 단계43의 동일 source/key/화음/partition/function 비교를 Sonata에 확장했다. 해결음 하나, whole ordinary template, joint 지원, 완전 경로와 종지를 구별한다. 무연결 intrinsic carry를0으로 가정하거나 연결 가정들의 유리한 부분을 합치지 않는다. 특정 악보 예외와 설명량 기반 정답 선택은 없다.
- **구현:** 새 staged saved-only 실행기·전수 pilot·진단 사례 저장·14검사를 추가했다. Bootstrap/control/linked/paired의 독립 계정에서 전체 원 selector와 native/role body·terminal·물리 SHA를 대조한다. 무손실 gzip의 physical/decoded 출력 비용을 구별하고 이전 stage 입력도 전체 terminal까지 보호한다. 기존 코드·producer·한도 상수·원자료·운영UI는 그대로다.
- **실제 결과:** Sonata1번1악장13~15마디 `[49,61)`,3raw lanes/23sound facts, 두 completion의각2,315후보/145batch(양쪽4,630발생)를 대조했다.18edge(12+4+2)는 technical probe다. 설명 증가1,870·동일445·감소0, 고유7sound/3,225변경 span. Whole False→True20/joint False→True8, False→Unknown2. **완전 경로 지원0**이며8개 음악 정답/전곡 개선율이 아니다. 무연결 intrinsic credit305후보도 보존했다.
- **음악적 판단:** G4→A♭4가 있어도 D♭5 seventh source의 outgoing route가 끊기면 V7 ordinary 해결은 보류한다. 3화음 양성으로7화음을 자동 탈락시키지 않는다. Whole=true라도 missing G♭이면joint=false, unknown key면joint=None다. 같은 sound 지속은 fabricated self-link 없이 조건부 boundary anticipation을 설명할 수 있다.6개 원음표/타이/음가·양쪽review/contrast·intrinsic 원clauses를 별도 저장했다.
- **검증/교정:** 최종 신규14/5.779초·기존56/58.940초 PASS. Genuine 작은XML/native body와 physical gzip이며 receipt ancestry는 합성 fixture다. 최초 test summary 필드명1 ERROR 및1차 교정의 다른 필드명 ERROR를 올바른 보존 계정 필드로 수정했다. 판단 gate는 완화하지 않았으며 중간 실행을 고유 검사에 중복 합산하지 않는다. 전수 저장 산술·cadence confirmed=false·전체2,315위치 대조도 통과했다.
- **실제 실행/보존:** 281.7621838초/exit0, 출력437파일/41,895,618B.4계정 decoded108,821,014/739,694,376/882,269,347/324,878,450B, 합계2,055,663,187B는 단일1GiB 초과다. 총 decoded 출력463,574,590B와 gzip 물리 출력 제한을 혼동하지 않는다. 원입력589+출력437의고유1,026SHA/목록 오류0, report SHA `ae546c207fa46e87e0cdd7c8e6cfca177862c600b798230fa1c18463f81f14c2`. 별도 진단2파일/1,552,616B와선행75SHA·별개tracked5·원XML/Core/주석/이전결과/Git·운영UI/서버를 보존했다. Commit/push0.
- **다음:** 완전 진행의 경쟁3/7화음·key·음표 역할·경계 전제 공동 판단. 끊긴/지연 해결은 별도 명시 전략과 실제 route/반례로 검증하고, 이후 여러 작품·편성 독립 검증 및 악보 layer/피드백에 연결한다. 최종 선택·음악 정확도·학습/Gold·작곡편곡 생성은 아직 미완료다.
- **정본:** [계약·실제 음악 사례·수치·검사·한계·다음](records/2026-10-04-sonata-completion-evidence.md), [전수 report](../../output/staged-sonata-evidence-2026-10-04-r1/report.json), [진단 사례](../../output/staged-sonata-diagnostics-2026-10-04-r1/diagnostic-cases.json).

## HARM-DEV-20261004-43 — 같은 음악·다른 성부 연결의 근거 민감도

- **목적/일반 규칙:** 같은 source/key/origin/partition/function 전제에서 성부 가정만 대조한다. 원음표·타이·음가·raw membership·베이스는 고정하고 조건부 NCT 음가·해결 근거의 차이를 원 note ID와 유리수 span에 연결한다. 여러 completion의 유리한 설명을 합치거나 설명량을 정답 점수로 쓰지 않는다.
- **구현:** 별도 core/저장자료 실행기/actual runner를 추가했다. 외부 pin→원 batch/role→동일 전제→전체 selector SHA/terminal 집계를 검증하며 source/NCT producer나 이전 competitor pair를 재실행하지 않는다. 새 native 권한·최종 화성/NCT/function/cadence·학습/Gold 승격0이다.
- **실제 범위/결과:** quartet 한 문맥 `[262,270)`,4raw lanes/53sound facts, 원1,710selector/107batch를 단계42 무연결 control과 전부 대조했다. linked probe20개는15+5개로 첫 두 lane에만 분포하며 검수된 성부가 아니다. 조건부 설명 증가1,130·동일580·감소0;1,555변경 span 발생은 고유6sound다. 내부 joint 지원0·false→false130·unknown→unknown2,100. 빠진 구성음/pooled/unknown/cadence 전제는 유지했다. 미설명0+구성음 부족35→80은 개선률이 아닌 설명량 단독 선택의 반례다.
- **검증/교정:** 최종 신규27/60.257초·기존70회귀/111.161초 PASS다. 최초 reader fixture6 ERROR는 `_seal` 반환값 미수신, 후속 unknown-key 검사1 ERROR는 필드 위치 오류라 검사를 교정했고 기능 gate를 완화하지 않았다. 실행기6검사는 genuine XML/native body와 물리 파일이지만 상위 receipt ancestry는 합성임을 기록했다. 중간19/25 및 개별6 실행을 고유 검수에 중복 합산하지 않는다.
- **실제 실행/보존:** actual205.8941519초/exit0, decoded829,150,924B<1GiB, 출력109파일194,333,531B<256MiB. 사후334input/output 길이·SHA오류0, report pin `2c5504a2b91cc71a1b0b2166e09028472495b0097623c1a3fdb8d02b94200944`. 선행70SHA 변경0·별개tracked5/원XML/주석/과거결과/기본 cap/운영 UI/서버/Git 설정 보존. commit/push0.
- **판단/다음:** 연결 가정이 국소 역할 설명에 영향을 준다는 것은 확인했지만 실제 성부/NCT·분산 화음·secondary/cadence 정답률 향상은 검증하지 않았다. 다음은 Sonata 문맥의 같은 방식 대조와 충분한 성부/기능 전제 점검이다. 최종 판단·다작품 독립 검증·화면/피드백·구조/생성의 네 큰 묶음이 남으며 기록 번호를 완성률로 쓰지 않는다.
- **정본:** [일반 계약·실제 사례·검사·한계·남은 범위](records/2026-10-04-completion-evidence-sensitivity.md), [실제 report](../../output/completion-evidence-contrast-2026-10-04-r1/report.json).

## HARM-DEV-20261004-42 — 완전 저장된 진행 후보의 음악적 근거 검토

- **구현:** 별도 evidence review v0.1과 saved-only 실행기를 추가했다. 두 외부 report pin, 원 source/catalog/block SHA, 모든 task/selector와 종료를 연결하고 동일 원음의 구성음·credit·베이스/전위·기능/종지 근거를 기록한다. 이전 authority/registry는 복구하지 않으며 native/role/pair producer를 재실행하지 않는다.
- **일반 규칙:** 같은 원음에서 나온 membership/pooling/계정 및 같은 completion의 개별/whole/joint 해결 근거를 독립 투표처럼 더하지 않는다. 내부 transition 없는 full hold를 ordinary 성공 또는 화음 유지 실패로 바꾸지 않는다. Missing constituent와 nominal cadence 의미 전제는 보류하며 설명량으로 winner/confidence를 선택하지 않는다.
- **검증:** 최종 신규29개/24.107초 PASS(핵심15·reader8·synthetic ancestry의 physical saved runner6), 기존75회귀/87.684초 PASS. 초기 account 축약 비교 adapter 오류와 cross-key fixture 오류는 원자료 변경 없이 교정했다. 중간/반복 실행은 신규 수에 합산하지 않는다.
- **실제 범위/결과:** quartet `[262,270)` 한 문맥/4raw lanes/53sound,5key group의1,710후보·105task·291,555pair를137.3594957초/exit0로 모두 검토했다. Decoded980,783,168B<1GiB, 새7파일95,977,735B. 구성음 부족1,420, pooled-only580, zero-unresolved-but-missing35(7대안×5key)와 nominal HC1을 각각 기록했으며 정답/실패율이 아니다.
- **해석/다음:** 선택 completion은 links0의 all-no-link control이다. 전체 joint 지원0은 이 전제·명시 shape 충돌·미선언 관계와 함께 해석한다. 다음은 같은 source의 실제 링크 completion을 대조하고 Sonata/다른 편성·독립 원주석 평가로 확장한다.
- **보존:** 선행65 SHA 변경0, 원 IR/XML/주석·기존 outputs·별개tracked5·UI/운영 미변경. Final harmony/NCT/key/cadence·training/generation false, selected/rank/confidence null이다. Git push 하지 않았다.
- **정본:** [단계42 개발 기록·일반 규칙·실제3사례·검사·보류·다음](records/2026-10-04-progression-evidence-readiness-review.md), [실제 report](../../output/progression-evidence-review-2026-10-04-r1/report.json).

## HARM-DEV-20261003-41 — 독립 pin·fresh request 기반의 남은 비교 연속 실행

- **착수/종료:** 2026-10-03 착수, 자정 이후2026-10-04 종료. 동일 실행이며 파일명/기록 ID는 착수일을 유지한다.
- **구현:** 별도 continuation v0.1 library/actual runner를 추가했다. 독립 관찰된 단계40 report SHA와 모든 이전 artifact 물리 해시를 보호하고 fresh 원 요청의 모든 group/task/source/selector를 결합한다. 이전 private registry를 복원하거나 JSON을 capability로 승격하지 않는다.
- **일반 규칙:** 기존86task/239,356pair는 trusted receipt 기반 borrowed 결과로 구분하고 새19task/52,199pair만 계산한다. Source/catalog는 보호 입력이며 새 writer 출력 수가 아니다. 원 전체/선택/생략 분모, 후보, 음표, pair JSON, 기본 cap을 보존한다.
- **예산/종료:** 이전 physical +새 모든 block 상계+새 plan/manifest를 합쳐 기본2GiB에 예약한다. Pinned receipt read3,085,719B도 같은1GiB decoded 예산에 계상한다. Atomic 순서/한도·전체 종료/후속 physical guard와 terminal write를 확인해야 완료가 가능하다.
- **검증/상태:** 최종 신규31 PASS/315.429초(genuine packet/physical23+explicit mock8), 기존84개 중83 PASS+1 Windows권한 SKIP/197.734초. Actual exit0/failure null·1,275.8928276초, 새19task/52,199pair 계산·저장 완료. 이전86task/239,356pair와 결합한 선택 요청105task/291,555pair 전체 저장·terminal closure 통과다. Full archive/음악적 정답/UI 완료는 아니다.
- **실제 보존/예약:** 새storage21파일149,794,182B +이전94파일827,880,027B =115파일977,674,209B≤combined 예약1,034,199,215B<기본2GiB. Receipt 포함957,633,552decoded B<1GiB. 이전102파일·새21파일·외부8artifact의 root 독립 SHA/길이/파일 inventory 오류0이며 runner15 current code confirmed다. 원 생략3request/1,361,085pair는 유지한다.
- **보존/음악적 범위:** 과거 코드·outputs·Core·주석·별개tracked5·UI/운영은 유지한다. 비교 저장 수는 화성 정답률이 아니다. 최종 선택·독립 주석 대조는 다음 큰 기능 단위이며 Git push는 하지 않는다.
- **정본:** [단계41 개발 기록](records/2026-10-03-fresh-bound-storage-continuation.md).

## HARM-DEV-20261003-40 — 새 지원 집합·유리수 상계의 저장 연결과 fresh 재검증

- **구현/버전:** 기존 storage/coordinator/actual runner를 보존한 별도 v0.2 snapshot을 추가했다. Group별 owned support/LCM proof를 한 번 준비하고 같은 proof로 모든 task의 상계를 예약한다. 새 bounds code SHA를 등록하고 proof 준비/inspection을 저장 planning 계정에 함께 넣는다. Pair JSON·원후보·원음표·타이·철자·Core·기본 한도·운영 UI는 변경하지 않았다.
- **보류/교정:** 새 StorageLimits는 모든 필드를 기본보다 낮추기만 한다. JSON/이전 plan으로 새 권한을 복원하지 않는다. Proof preparation hold는 원 분모·상계 null·비교/출력0이고, 비교 전 binding 실패는 known uncomputed로 기록하여 비교 시도 후 unknown과 구별했다. GC를 꺼도 proof 수명은 owned plan/run에 한정된다.
- **검사:** 최종 저장35+coordinator20+runner29의84개/194.668초 중83 PASS+1 Windows symlink권한 SKIP, 기존bounds21+streaming16+proof core34의71개/106.875초 PASS다. 이식 통제77개와 직접 추가7개를 구별한다. 중간77/158.626초·직접7/37.165초는 최종 검사에 중복 합산하지 않으며 mocked ancestry/API를 실제 admission으로 주장하지 않는다. Root 검수다.
- **소형 물리 저장:** 합성 XML2group·5entry·4pair를 실제 새 writer로 모두 저장했다. 구block 상계25,961B→신19,526B, 실제16,683B. Whole 예약26,196,652B·physical7,351,094B,26.5114015초/exit0·owned terminal 및 코드/fixture guard 통과다. 실제 corpus·화성 정답률·UI 성공의 의미는 없다.
- **실제 실행/범위:** 같은 byte-only source1/completion0의1,710후보·107batch·5group·291,555pair·105task를 fresh admission했다. Whole 예약은1,067.1329381초에1,207,874,256B로 반환돼 기본2GiB를 통과했다. 직전3,881,314,476B에서 후보 삭제·cap 증가 없이 줄였다. 각 group지원 집합1~2종류/LCM2/rational폭32B,planning3.6247억<1B다. 원 전체4/8,050/20group/1,652,640pair와 생략3/6,340/15group/1,361,085pair를 유지한다.
- **실제 종료:**1,702.1672661초/exit0·정상partial이다.600초 cooperative 예산에 따라86task/239,356pair 계산·저장,19task/52,199pair 미계산을 보존했다. computed-unpersisted/held/unknown0·physical94파일827,880,027B·terminal integrity/closure true이나 전체 요청 완료 false다. Storage elapsed629.6710309초는 마지막 block과 종료/추가 guard 포함이며 hard600초/RSS 보장이 아니다. Decoded954,547,833B<1GiB·execution254read 모두 완료, resource145관찰/peak5,169,995,776B·current14code guard 변경/미확인0이다. 음악 정답률·UI·winner·Gold 성공이 아니다.
- **보존/기록:** 착수 전후 선행54+새7의61SHA 변경0,actual 외부7artifact/storage94파일 길이·SHA 오류0, 별개tracked5 수정 보존이다. Git/서버/권한/설정/UI 변경0. 다음은남은19task를 포함한 전체 요청의 안전한 연속 실행이며 JSON만으로 실행 권한을 복원하지 않는다. [일반 계약·이식/새반례·검사·물리 저장·실제 실행·동결/다음](records/2026-10-03-transfer-bound-storage-and-fresh-request.md), [소형 report](../../output/transfer-bound-storage-fixtures-2026-10-03-r1/report.json), [실제 report](../../output/transfer-bound-whole-request-storage-pilot-2026-10-03-r1/pilot-report.json).
- **최종 QA:**7AST/3strict UTF-8 문서/183local links·replacement/zero-width 문자 오류0, read-only diffcheck exit0·기존tracked5와 LF→CRLF 경고 보존이다. Final source/output guards와 이전 독립 감사·작은 mocked 검사·음악 정확도를 각각 구별했다.

## HARM-DEV-20261003-39 — 역할 지원 집합과 정확한 유리수 저장 상계

- **목적/구현:** 주석 평가 질문에 답한 뒤 원래 순서로 재개했다. 별도 `proof_shared_transfer_bounds` library·검사·소형 실행기를 추가했다. Owned 후보의 모든 source row 종류 집합, endpoint LCM·전체 sound-span 분자 상계로 기존 transfer-array 항목만 좁힌다. 최종 NCT/화음 선택·atom pair run·결과/압축 샘플 없이 계산하며 candidate·원음가·pair JSON은 그대로다.
- **보류/권한:** 정확한 group/refinement/entry/task와 issued proof만 사용한다. JSON descriptor는 권한이 아니며 work/bit/scratch/retained allocation을 사전 제한하고 unknown을null로 남긴다. 기존 writer/coordinator·source/group/block/output 기본 한도는 바꾸지 않았다. 원 actual 요청의 whole hold도 아직 그대로다.
- **검증:** 최종 신규21개/20.304초, 기존 streaming16+proof core34의50개/72.904초 PASS다.80개 seed lattice/role property cases는21개 안의 반복이지 신규80검사가 아니다. 처음19개·중간21개 재검사도 중복이다. Root 검수이며 이전 독립 감사를 새 코드에 소급하지 않는다. 초기 SHA 비교 도구의 배열/path 인덱스 오류를 고쳐 기존49변경0을 확인했으며 제품 오류가 아니었다.
- **소형 관찰:**4개 합성 XML group/9entry/6pair,20.222295초/exit0. 구 block 상계33,170B→신26,063B, 실제21,329B 이하이며 code SHA 시작/끝6동일이다.7,107B(약21.43%) 상계 절감은 이 표본에만 해당한다. 실제 corpus·전체 저장 fit/화성 정확도/화면 적용 완료가 아니다.
- **최종 보호/QA:** 선행51파일(이전49+단계38 실행기/검사2) SHA 변경0, 새3SHA는 정본/실행기 기록과 같다.3AST·3문서 strictUTF-8·replacement/zero-width 문자0·174local links 누락0, read-only diffcheck exit0이다. 기존tracked5 수정과 LF→CRLF 경고만 유지했다. 원자료/Core/주석/기존 비교·저장 코드·과거 결과/Git/서버/UI 변경0이다.
- **다음/기록:** 새 proof를 소비하는 versioned 저장 연결 뒤, 같은 원1,710후보/5group/105task의 fresh 전체 예약을 재검증한다. 공개 JSON 덮어쓰기/monkeypatch·cap 증가·후보 축소로 우회하지 않는다. [정본·수식/API·검사·관찰·동결·남은 범위](records/2026-10-03-category-support-and-exact-transfer-bounds.md), [소형 report](../../output/proof-transfer-bound-fixtures-2026-10-03-r1/report.json).

## HARM-DEV-20261003-38 — 실제 원 요청의 전체 저장 예약과 진행 위치

- **구현/검사:** 새 actual runner와 명시적 mocked API 통제 검사29개를 추가했다. Closed-six 원분모·정확한 integer·전체 task/pair coverage·complete output 예약, 같은 owned request의 더 늦은 terminal snapshot, whole hold에서 비교 미호출·부분 중단·unknown/null을 확인한다. 최종 작성29/0.023초/root29/0.019초, 기존52/18.194초 PASS다. 중간 fixture형식 실패와 잘못된 module명 loader error는 정본에 기록하며 성공/고유 검사 수로 합산하지 않는다.
- **실제 범위:** 원4completion/8050/20group과 생략3/6340/15group을 보존했다. 선택1/1710/107batch/5group/291555pair/105task 전체 read join·모든 group 기본 work·각 block64MiB를 확인했다. Source-once82,408,563B+catalog64,758,220B+blocks3,715,273,325B+plan/manifest18,874,368B=**3,881,314,476B>2GiB**여서 whole output hold다. Unknown 상계가 아니며 pair0/storage 시작0/후보생략0이다.
- **자원/보존:** 실제1055.972411초/exit0/37관찰·peak5,164,068,864B(약4.809GiB), bootstrap+execution decoded954,547,833B<기본1GiB, execution254reads failed/held/never0이다. Physical read/guard와 추가 storage planning 비용은 별도다. 정확8JSON/4,491,663B, current13code guard 변경·미확인0·원/Core/주석/old registry·과거 결과·Git/서버/UI 미변경이다. 원 reader의 old prepared0/intrinsicfalse는 새 v2준비5와 구별한다.
- **큰 병목/다음:** 현재 category-transfer 모든6종류36조합과142B rational폭의 보수 항목이 block 상계의76.85%(2,855,198,115B)다. 결과 전 assumption중복 가설을 실제 원인과 구별하여 우선순위를 수정했다. 다음은 owned source rows의 가능한 category 지원 집합 proof+사전예산 exact LCM/numerator 상계다. 모든 후보/원음가/legacy 의미를 유지하며 새fit을 미리 단정하지 않는다. Assumption ref codec은 잔여 병목일 때 후속이다.
- **전체 위치:** 큰7기능 중3공동비교·탐색 검증,4조성·기능·종지는 연구용 연결 검증이다. 원 P5/P6+P4, 생성 G0/G1일부다. 화성 기반 중간에 가까움과 전체 작곡편곡50% 완료를 혼동하지 않으며 전곡 독립 평가·새 엔진UI·생성기 연결은 남아 있다. 단계/검사/후보 수로 진행률을 계산하지 않는다.
- **정확도 구별:** 기존 화성 주석 기반 surface/retrieval 진단과 이번 계산·저장 계약 검사를 구별했다. 최근 PASS/후보/pair 수는 화성 정답률이 아니며, 새 공동 분석 엔진의 전곡 독립 주석 대조는 아직 미완료다. 주석을 추론 입력으로 노출하지 않는 작품군·주석 계보 분리 평가와 원음표에 근거한 불일치 검토가 필요하다.
- **최종 QA:** 새2AST/3문서 strict UTF-8·replacement/zero-width 문자0·175local links 누락0, 동결49SHA 변경0·독립 실제8artifact 및 등록7SHA/길이 불일치0·read-only diffcheck exit0이다. 기존tracked5 및 LF→CRLF 경고는 보존하며 QA 재검사는 고유 검사 수에 더하지 않는다.
- **정본:** [범위·현재 위치·구현/교정·실측·보류·다음·주석 평가 범위](records/2026-10-03-whole-request-storage-resource-pilot.md), [실제 report](../../output/proof-whole-request-storage-pilot-2026-10-03-r1/pilot-report.json).

## HARM-DEV-20261003-37 — Proof-v2 source-once streaming 저장과 완전한 원 요청 연결

- **목적/구현:** 별도 streaming helper·v2 writer·whole-request coordinator와 세 test module을 추가했다. Frozen source와 cached local DAG를 전체 export/thaw 없이 canonical UTF-8 chunk로 쓰며, 모든 compact pair의 rational/assumption/transfer/pointer/ref/seal/key/punctuation을 포함한 schema-derived block 상계로 전체 output을 사전 예약한다. 비교 결과/압축 표본으로 admission하지 않는다. 원 scoped reader를 직접 끝까지 소비하고 모든 원 group을 같은 source로 준비한 뒤 동일 owned storage plan의 완료만 선택 원 요청에 연결한다.
- **보존/완료 진실:** 기본 output2GiB/source·catalog256MiB/block64MiB·read1GiB를 올리지 않는다. Core/원XML/주석/old registry·결과는 바꾸지 않으며 JSON descriptor가 권한을 복원하지 않는다. Original/selected/omitted 분모, whole holds·unknown null·computed-but-unpersisted·비환불 physical attempts·provisional/terminal/self-certification 구별, expectedSHA/inventory/독립 output closure를 보존한다. Caller의 빈 root나 높은 group limit로 원 정책을 약화하지 못한다.
- **검수/검사:** 최종 고유64개=stream16+writer28+coordinator20 중63 PASS/1 Windows symlink권한 SKIP다. 작성/독립 stream16(28.895/27.322초), writer27PASS+1SKIP(61.347/65.103초), root/독립 coordinator20(109.814/108.021초), 별도 기존 reader/native52/18.622초 PASS이며 독립 최종 차단0이다. 초기 fixture4error·수정 중 SHAguard로 무효화된 중간1FAIL·root중간16/64 실행은 정본에 구별하며 고유 수에 중복 합산하지 않는다.
- **소형 관찰:** 한 fresh genuine2selector/1task에서 전체 보수 예약20,053,740B/실제physical1,188,195B, block상계4,906B/실제4,060B, source1회·제출소형set terminal 완료다. 별도 actual corpus fit/RSS나 화성 정확도를 뜻하지 않으며 opaque refs가 다른 표본의 byte 수를 섞지 않는다. Core work와 추가 storage planning/source streaming/plan finalization/manifest/rawSHA/physical guard I/O는 별도 계정이다.
- **범위/다음:** 기존43동결SHA 변경0·별개tracked5 수정 유지, 새6코드/test 정본SHA와3문서에 기록했다. 새 actual1,710후보/291,555pair/105block 실행은 아직0이며 prototype 저장 성공을 전체4request/8,050후보 완료·winner/UI/구조·생성·학습/Gold로 승격하지 않는다. 다음은 정확 한 원 completion의 fresh re-admission과 전체 저장 상계/시간/RSS 사전 점검, 통과 후 bounded whole block 실제 비교·저장이다. Authenticated reload/resume·compression·OS symlink runtime 검증은 별도다.
- **최종 QA:** 새6AST/3문서 strictUTF-8·깨진 replacement character0/167local links 누락0, 기존43+새6의49SHA 불변, read-only diffcheck exit0이다. 기존tracked5 LF→CRLF 경고는 그대로 유지했으며 QA/재검사는 고유64에 합산하지 않는다.
- **정본:** [설계/API·원 요청·상계/비용·문제/교정·최종 검사/skip·revision·다음](records/2026-10-03-proof-v2-streaming-storage-and-whole-request.md). 인수인계/구조 문서가 아닌 별도 화성 개발 기록이다.

## HARM-DEV-20261003-36 — Owned 검증 증명 공유·임시 자료 수명과 실제 전체 요청 준비 통과

- **목적/구현:** 새 immutable JSON proof/DAG v0.2와 별도 v2 group·동일 원 요청의 계측기를 추가했다. 한 input guard+한 snapshot 검증, exact canonical SHA와 source/request/key/bundle/selector/path/role/원 row binding의 증명 공유, streamed catalog 해시와 transient memo/partial copy/retained traceback 정리를 구현했다. 원음표·음가·철자/alias·타이/재발음·multiplicity/null0·legacy pair를 보존하며 기본 cap/old registry·Core/주석·production/UI는 바꾸지 않는다.
- **검수/검사:** 신규 고유96개(helper48+core34+runner14), 기존 reader/native52개/19.500초 PASS다. Root96/57.538초 중 마지막 core 편집과 겹친34개는 최종SHA에서55.107초로 재검사했다. 작성/독립 재검사는 중복이며 고유 수에 더하지 않는다. Count→snapshot 간격, aggregate composition 사전예산, codec SHA·fragment sizing 비용, mappingproxy/deepcopy, mutable fields 재읽기, malformed-path/export/hash/decode/facet traceback 수명, 성공stage/retained summary를 교정했고 초기 실패·instrumentation 문제와 최종6 SHA를 정본에 기록했다. 독립 코드·실제 결과 감사 추가 차단0이다.
- **실제 범위:** 동일 source1/completion0의 전체1710selector/107batch/5group·예정291,555pair/105block을 fresh SHA/40metadata+214body의 ordered membership·selected terminal로 검증했다. Bootstrap6+execution254=260occurrences/257unique/반복3, logical decoded4,058,934+950,488,899=954,547,833B<기본1GiB다. 원4request/8050/20group/1652640pair/570block과 생략3/6340/15/1361085/465를 유지한다.
- **효과:** 모든group342/58311/21·atoms69/vector23,598을 유지하며 whole work865,341,814~890,230,520<기본1B(직전대비46.49~47.09% 감소), prepared5·원entry보존·hold0이다. Encoded DAG 합52,746,528B/catalog 교환 길이 합64,756,405B는 owned memory 표현이며 디스크 저장 완료가 아니다. 실제pair0/최종harmony·NCT·key·cadence/winner 미선택이다.
- **자원/출력:** 919.403516초/exit0, peak5,163,905,024B(4.809GiB; 직전대비45.03% 감소),43관찰·explicitGC0다. 단일 실행 비교이며 RSS 상계/GC만의 인과/화성 정확도 실증으로 확대하지 않는다. 정확11JSON/908,370B·등록10SHA/bytes·reportSHA410c90e5… 일치다. Physical body87,164,288B와guard5,967,069,895B/19,615checks는 별도계정이다. Old scoped intrinsic/prepared는false/0 그대로이며 새 v2prepared5와 구별한다.
- **보존/다음:** 선행37+신규6SHA 변경0·current10 guard changed/uncertain0·기존tracked5 사용자 변경 보존이다. Git/권한/설정 변경0이다. 다음은 새 proof-v2 source-once writer/whole-request coordinator다.105×64MiB 기본 block예약이2GiB output을 넘으므로 schema-derived compact 상계를 먼저 설계한다. Capraise/유리한prefix/표본압축률로 우회하지 않는다. Fresh process의 owned 재입장·authenticated reload/resume, 실제 대비·UI/구조·작곡편곡·Gold/학습은 별도 후속이다.
- **최종 QA:** 새6AST/3strict UTF-8 문서/161local links/11JSON·등록10SHA/bytes·정확11output/908,370B와 비용·same-plan/미승격flag 검증 PASS다. 총43동결SHA 변경0·read-onlydiffcheck exit0, 기존tracked5와LF→CRLF경고 보존이다. 실제 결과 독립 감사의 추가 차단0이며 원 body 재읽기/수정은 없다.
- **정본:** [계약·API·문제/교정·검사·실제 효과·한계·revision·다음](records/2026-10-03-owned-proof-sharing-and-transient-lifetime.md), [실제 report](../../output/proof-shared-scoped-group-pilot-2026-10-03-r1/pilot-report.json).

## HARM-DEV-20261003-35 — 무손실 local 표현·정확한 경계 결합과 실제 비용 재검증

- **목적/구현:** 새 typed JSON DAG·별도 immutable compact group·원 전체 membership의 계측기를 추가했다. 표현 subtree만 공유하며 모든 occurrence/selector·타이/재발음·음가·철자/alias·원 row/근거 refs와 legacy pair 설명을 유지한다. 실제 Fraction endpoint union을 사용하고 세 번째 후보의 추가 endpoint가 원 pair 설명을 바꾸지 않게 한다. 기존 Core/producer/registry/UI·기본 cap은 변경하지 않는다.
- **검사/교정:** 신규 고유55개(DAG24+compact23+runner8)/61.403초와 기존 reader24/0.363초·native 대비28/16.826초 PASS다. Byteobject/length 혼동·weak plan self-key 수명·raw hash/검증·catalog finalization/import/expansion 비용 누락과 open 실패 ledger/최종SHA 관찰 예외를 교정했다. 작은 genuine/synthetic 검사와 실제 corpus 결과를 구별하며 초기/subset/retest를 고유 수에 더하지 않는다.
- **실제 범위/비용:** 원 같은 source1/completion0의1710selector/107batch/5group·예정291,555pair/105block을 전부 읽고 연결했다. Bootstrap5+execution254=259ordered reads/256unique/반복3, decoded3,804,360+950,488,899=954,293,259B<기본1GiB다. Physical body86,909,714B와 guard5,964,744,346B는 별도계정이다. Metadata40·원creation347/parents6/7/7/148와 selected terminal guard를 확인했다. 원전체4completion/8,050과 생략3/6,340의 모든 분모를 보존한다.
- **효과/보류:** 각group의atoms47,196상계→실제69/vector16,141,032→23,598로 감소했다. 그러나 whole work1,617,278,315~1,682,682,609>기본1B로5개 모두 canonicalization whole hold, group발급0·pair계산0이다. 실제encoded/catalog/finalization 비용은null이다. 출력11JSON/902,174B·1002.4669633초·peak9,393,307,648B(약8.75GiB)로 메모리는 직전보다 증가했다. 명시 resource-hold와 shell exit1을 성공/음악정확도 향상으로 바꾸지 않는다.
- **메모리/다음:** 별도 작은 readonly 재현에서 recursive cost memo가 GC까지 살아 있는 현상을 확인했다. 전체 실제RSS의 원인·영구 누수·수정 완료를 단정하지 않는다. 다음은 임시 수명과 반복 검증/복사의 provenance-safe 공유이며 원입력/후보삭제·capraise·작품별 예외로 우회하지 않는다. 실제 default gate를 통과할 때만 저장/전체 대비·reload/resume로 진행한다.
- **보존/감사:** 정확11output/등록10SHA·bytes/전체ordered read·비용산술·5preflight/분모·미승격flags 독립 최종 불일치0·추가 차단0이다. 선행31+신규6SHA변경0·current-code final guard changed/uncertain0·read-onlydiffcheck exit0, 기존tracked5 사용자 변경/LF→CRLF경고는 보존했다. 원archive/과거output/production·winner/최종분석/UI·구조·작곡편곡·Gold/학습/Git 변경0이다.
- **최종 QA:** 새6AST/3strict text/158local file links·11JSON/등록10artifact SHA와bytes·exact11목록·scalar/unknown/비용 산술과 미승격flag 모두PASS다. 문서 확인과 재검사 수를 고유55unit tests에 더하지 않는다.
- **정본:** [계약·API·문제/교정·검사·실제hold·자원/메모리·revision·다음](records/2026-10-03-lossless-compact-group-and-exact-refinement.md), [실제 report](../../output/compact-scoped-group-pilot-2026-10-03-r1/pilot-report.json).

## HARM-DEV-20261003-34 — 정확한 파일별 비용과 완전한 한 원 completion의 실제 pilot

- **목적/구현:** 새 byte-only streaming 측정과 별도 scoped adapter·root 계측기를 추가했다. 원 metadata40+선택 body214의 완전254occurrence를 upfront 고정하고 원4request/8,050entry/20group/1,652,640예정pair/570예정block과 생략 범위를 보존한다. 결과가 아닌 old byte 비용만으로 원 source1/completion0을 골랐다.
- **실제 검증:** Bootstrap3+4 정상읽기1,837,094bytes, 측정950,488,899bytes로 준비952,325,993bytes다. 별도 default1GiB execution254reads/950,488,899bytes에서 실제40 역사 metadata와 선택1,710entry/107batch/terminal join을 모두 검증했다. 합계1,902,814,892bytes를 한 계정의1GiB 완료로 주장하지 않는다. 원 creation347/ordered parent6/7/7/148·정확 입력/코드 SHA·inventory와 전체/선택/생략 분모를 검증했다.
- **자원 결과/범위:** 242.9819214초, peak3,233,386,496B(약3.01GiB), 최저 관측 physical 여유11,533,078,528B다. Source 상계82,408,563B/work659,616,216는 통과했다. 5개 선택group 각각342entry/58,311pair/21block이지만 vector16,141,032·work5,552,879,397·catalog1,628,092,116~1,665,649,116B로 세 default cap을 모두 넘어 whole hold다. Body 완료True/group완료False/preparedgroup0·실제pair0/fullarchiveFalse를 구별했다. 기본한도·producer·음악 규칙/UI/정책/winner·학습/Gold 변경0이다.
- **검사/교정:** 최종 신규21+14의35개/74.403초와 별도 runner5개/0.085초, 기존 reader24개/0.366초PASS다. 초기root33/65.591초 및 author21/0.359초·14/72.605초는 중복이고 최종고유 신규40개다. Iterator의 batch/entry 혼동과 hold plan 타입을 실행 전에 교정했다. 종료 후 bootstrap 실패 비용 누락/unknown0 혼동 통제를 보완해5개검사를 추가했으며 r1 실행 코드와 최종 runner revision을 구별한다. 독립최종 차단0·실제 출력11개/등록10SHA·bytes 일치다.
- **한계/다음:** 전체4request의 대비/실제 pair·source-once corpus 저장·authenticated reload/resume는 남아 있다. 다음은 capraise보다 compact local과 정확한 rational endpoint union으로 원전체342-entry group의 메모리/연산 상계를 줄이는 작업이다. Metadata/body integrity를 화성 정확도 향상으로 확대하지 않는다. 별개 tracked5 수정·원자료/과거 결과·선행25SHA를 보존했다.
- **최종 QA:** 새6AST/9strict text/162local links/11artifact JSON·등록10output SHA/bytes와exact11목록·비용산술·완료flags 오류0, 선행25SHA변경0, read-onlydiffcheck exit0이다. 현재/실행revision SHA와 기존 tracked5 LF→CRLF 경고를 정본에 구별했다.
- **정본:** [API·예산·원 범위·실측/hold·검사·SHA·다음](records/2026-10-03-scoped-archive-resource-pilot.md), [실제 pilot report](../../output/scoped-source-archive-cost-pilot-2026-10-03-r1/pilot-report.json).

## HARM-DEV-20261003-33 — 역사 원 요청 연결과 Source-once 저장

- **목적/구현:** 직전 공유 source/core와 누적 reader를 연결하는 별도 versioned archive bridge·source-once storage·세 검사를 추가했다. Source는 한 번 소유/저장하되 원 completion/request/key/bundle/selector와 local catalog/block은 분리한다. 과거 loader/private admission registry/producer·Core/XML/주석·과거 결과는 수정하지 않았다.
- **일반 계약:** Caller-declared upfront read 예약과 실제 metadata membership을 구별한다. Metadata 이후 전체 remaining ordered body 목록을 같은 reader의 계획과 대조하여 body/source/group prefix 비용 우회를 막는다. Source/local/모든 task/terminal 비용을 먼저 예약하고, 불충분/미상/중단에도 전체 원 분모를 유지한다. Source 공유는 decode 비용 제거가 아니다.
- **발견/교정:** 역사 code SHA 덮어쓰기 충돌, 동일 original identity의 split source 중복 저장, public 원 group 선언 누락, boolean/terminal cached 권한, source/group cap의 전체 분모 기록, final-yield finish→resume 재승격, SHA 관찰 중 중단·symlink 출력 통제를 보완했다. Block마다 전체 registered-input/output-history 재해시·ledger 복사를 반복하지 않으며 terminal 전체 guard 이전 저장 수는 provisional이다.
- **최종 검사:** Root 신규 bridge16+storage28+연결4의 **48개/142.691초**, 별도 기존 core/admission **41개/80.930초 PASS**다. 작성 최종16/89.776초·28/35.432초·root초기3/3.860초와 초기/subset 재검사는 중복이다. 독립 최종 추가 차단0. Bridge ancestry는 명시 mock이며 실제40read 역사 admission 성공은 미검증이다. Genuine saved packet/유리수 pair exact 복원·source-once physical 저장·partial/whole hold 검사이지 음악 정답률이 아니다.
- **실제 범위/한계:** 원4request/8,050entry/20group/1,652,640예정pair/570예정block은 미실행 그대로다. Old34-read+body 약2.8GiB receipt를 새40-read 비용으로 승격하지 않고 기본한도 변경0다. 다음은 정확한 파일별 비용 지도와 완전한 한 원 completion의 versioned scoped pilot이며 원 전체 분모·생략 범위/full archive=false를 유지한다. 실제 group bound/RSS/runtime, authenticated reload/resume·전체 대비·winner/UI/구조/생성/학습·Gold는 남아 있다.
- **보존/기록:** 선행20+신규5의25SHA 변경0, 새5AST/8strict text/158local file link 오류0·read-only diffcheck exit0다. 명령·시간·발견/교정·mock/physical 경계와 작은 저장 관찰을 정본에 기록했다. 별개 tracked5 사용자 변경과 LF→CRLF 경고, 원자료·과거 결과를 보존했고 corpus output/Git commit/push·권한/설정 변경0다.
- **정본:** [계약/API·감사/교정·검사·비용 한계·동결/보존·다음](records/2026-10-03-shared-source-archive-bridge-and-storage.md).

## HARM-DEV-20261003-32 — Source 공유 대비와 전체 누적 읽기 예산

- **목적/구현:** 원 scope/lattice/bundles를 한 번 동결하는 별도 source handle과 local group/compact block codec, 전체 ordered read를 한 계정에 예약/계상하는 별도 reader를 구현했다. Old `PreparedGroup`을 위조하지 않고 원 request/key/bundle/selector·타이/재공격/alias/multiplicity·rational cell·unknown/0와 원 pair 설명을 보존한다. 실제 corpus/native producer/UI/정책·학습/Gold 변경은 없다.
- **일반 계약:** Source와 group-local bytes/work를 별도 사전 검사하고 quadratic task/pair 전에 count gate를 적용한다. Metadata/body와 repeated read를 모두 whole-budget에 넣고 부족/미상/missing이면 원 분모를 유지한 whole hold다. Reader 재시작/skip/reorder, 실패 사용량 환불과 부분 완료의 전체 승격을 막는다. 등록 SHA/정확 root·보호 archive 밖 output 규칙을 지원하되 caller-declared set을 역사 원 archive 인증으로 바꾸지 않는다.
- **검수/교정:** 입력 digest 항등 검사와 freeze 직전 변경 창, foreign lattice/key/origin/bundle 연결, projection work 누락, cap 자리 수에 의존한 source 상계, SHA metadata 타입을 교정했다. Reader의 매 read 전체 closure 재해시는 plan/begin/finish 전체+read별 target/current-code guard로 줄였다. Begin/finish guard 중단의 비용 미상/null·원 분모와 implicit code count도 보완했다.
- **최종 검사:** 신규 source27+reader24+root XML 연결3의 고유54개/root50.965초와 별도 기존 core25+admission16의41개/93.696초 PASS다. 작성 source27/47.275초·최종 대상1/2.133초·reader24/0.443초·root초기3/2.747초와 독립 reader23/0.426초/source geometry2/0.046초는 재검사/subset이며 별도 고유 수에 더하지 않는다. 초기 source22/36.541초의 cap-boundary1실패와 교정 이력은 정본에 보존한다. 독립 최종 추가 차단0이다.
- **한계/다음:** Source 공유로 decode 약2.8GiB가1GiB가 되지 않는다. Actual20group/463·342entry의 local 상계·RSS/전체 output/runtime은 미측정이며 default cap 통과를 선언하지 않는다. 다음은 원 membership/versioned archive bridge와 새 source-once storage adapter, 이후 전체 자원 정책과 결과 독립 실제 pilot다. 실제1,652,640pair 대비·winner/음악 정확도·운영 악보·생성 연결은 아직 없다.
- **보존:** Root의 선행 동결15SHA 변경0·신규5SHA를 정본에 기록한다. 별개 tracked5 사용자수정, XML/Core/주석/과거 output·producer를 유지했다. 신규 corpus output/Git commit/push/권한·설정 변경0이다.
- **최종 QA:** 새5AST/8strict text/156local Markdown link·신규5/선행15고정 SHA 오류/변경0, read-onlydiffcheck exit0다. 기존 tracked5와 LF→CRLF 경고만 유지했다. 소형 검사/문서 QA를 실제 corpus 대비/음악 정확도로 확대하지 않는다.
- **정본:** [계약/API·발견/교정·검사·작은 관찰·동결 SHA·한계/다음](records/2026-10-03-source-shared-contrast-and-cumulative-read-budget.md).

## HARM-DEV-20261003-31 — 진행 후보 대비의 저장·중단 처리와 실제 읽기 예산

- **목적/일반 규칙:** 계산된 pair와 완전 저장·원 archive 전체 완료를 구별한다. 원 request/key/bundle/selector/entry/task/pair 분모를 고정하고 전체 catalog/block/run plan/final manifest 용량을 비교 전에 예약한다. 부족하면 원 분모를 유지한 whole hold이며 유리한 prefix나 부분 저장을 완료로 바꾸지 않는다.
- **구현:** 새 saved-only storage library와 작은 저장 검사·root admission→core→storage 연결 검사를 추가했다. Owned `PreparedGroup`만 계산을 발급하고 exclusive 새 directory/files, encoded bytes 선 charge, partial/unknown fragment·confirmed/unconfirmed computation·persisted/held complements, source/current limited code SHA 및 output SHA/exact inventory guard를 구현했다. Source identity metadata만 바꿔 같은 group을 이중 집계하는 것도 거부하며 별개 원 completion은 합치지 않는다.
- **검수/교정:** Final manifest cap만 예약하던 문제는 derived ledger 상계와 bounded UTF-8 destination으로 보완했다. 기존 output 변조/외부 파일·catalog gzip/partial write/manifest 실패·Boolean alias·core 반환 전 interrupt를 검사했다. On-disk report의 자체 성공 인증과 owned terminal return을 구별한다. 과거 code glob을 다시 승인하거나 XML/Core/주석/producer를 바꾸지 않는다.
- **최종 검사:** 신규26 storage/46.854초+2연결/27.559초, 기존25 core/44.652초+16 admission/41.722초 모두PASS다. 신규고유28·기존회귀41이며 재검사·중간24/26개 suite·독립 pure3 subset을 더하지 않는다. 마지막 source identity만 바꾼 duplicate 반례 교정 후26+2를 다시 검사했고 독립 최종 차분 검수 추가 차단0이다. 64/65 geometry는 명시 mock intrinsic admission이고 실제 corpus나 음악 정답률이 아니다. 고정 SHA와 보호/QA는 정본에 기록한다.
- **실제 자원:** 등록1,024artifact/정확1,025목록·creation input/code union4,788SHA/ordered parent6/7/7/148 불일치0다. 1MiB gzip stream으로 native+role1,008파일/2,568,511,457decoded bytes를 실측했고 metadata34read/438,689,440와 합해3,007,200,897bytes다. 기존 cumulative1GiB cap 초과1,933,459,073bytes이며 body JSON join/pair 계산은0이다. Full lattice만으로 core catalog 상계 하한도827,210,888/649,613,648bytes여서 default256MiB를 넘는다. cap 변경0이다.
- **한계/다음:** 제출 group 저장 library에 한정하며 full archive authority·authenticated reload/resume·전체 runner·실제1,652,640pair·policy/winner/UI/구조/생성/학습/Gold는 없다. 원 inventory roots 보호/그 안에 output 금지, source-shared codec, 전체 cumulative read/membership bridge를 다음 단위로 만들고 실제 first/max-cost pilot 이후 전체 대비 여부를 정한다. 별개 tracked5 수정과 동결 선행 자료는 보존한다.
- **최종 QA:** 새3AST/7strict text/154local links·신규4 및 기존11고정SHA·receipt 산술과 원3manifest physical SHA 오류0다. Read-only diff check exit0·기존 tracked5와 LF→CRLF 경고만 유지했다. Git commit/push·권한/설정 변경0이다.
- **정본:** [구현/API·문제/교정·실측/예측·검사/보호·다음](records/2026-10-03-cross-batch-storage-and-read-budget.md), [숫자와 예산 관찰 receipt](../../reports/cross-batch-read-budget-observations-2026-10-03-r1.json).

## HARM-DEV-20261003-30 — 배치 사이의 진행 후보 대비 기반

- **목적/일반 규칙:** 저장 batch가 달라도 같은 원 source/scope/lattice/key/bundle/completion request의 완전 경로를 비교하게 한다. 원 selector/성부 가정·철자 alias·타이/attack·sound multiplicity·유리수 음가와 기존 pair cell을 보존하고 설명량으로 winner를 정하지 않는다.
- **구현:** 새 saved-only admission/core와 두 테스트를 추가했다. 역사 creation snapshot의 exact SHA/부모 목록·원 배치/terminal/ordinal을 검증하고, immutable shared catalog/원 row-index rational refinement/64이하 bounded block/compact pair와 기존 설명의 exact 재구성을 구현한다. 기존256한도/public 분석기·원 Core/XML/주석/producer·과거 결과는 바꾸지 않았다.
- **검수/교정:** 오늘의 code glob을 과거 생성 목록으로 쓰는 문제, ordered ancestor 누락, 공개 ledger/handle의 거짓 완료, 미적용 catalog/origin cap, resealed role 배열 순서, 미상 credit와 관측 rational delta 혼동을 보완했다. 기술 cap/위조 반례의 상세 이력과 final suite 결과는 정본에 기록한다. 특정 작품 정답/support threshold는 추가하지 않았다.
- **최종 검사/QA:** 고정 core25개/작성40.820초·root38.981초와 admission16개/root39.186초 PASS, 신규 서로 다른41개다. Root 같은25개 재검사·중간 suite를 중복 합산하지 않는다. Owned state·mutable rational cache·JSON subclass·O(전체task) membership·명백한 byte cap 및 Fraction 재구성 작업 비용도 교정했다. 작은 XML에서 원 pair 설명/타이/재발음/alias/nullable credit exact equality를 검사하며 실제 corpus 음악 정답률이 아니다. 최종 독립 계약 검토 추가 차단0·새4AST/3MD strict text/146local links·기존 동결7SHA변경0·read-onlydiffcheck exit0다. 네 새 파일 SHA와 초기 fixture 교정/중간 검사 이력은 정본에 보존한다.
- **실제 저장 metadata:** 최종52.8299268초/exit0,34read/438,689,440decoded bytes와 원4completion·8,050entry·20group·1,652,640예정pair·570예정block을 확인했다. Body joins/core intrinsic 전량/실제 pair 계산은0이다. Default 누적1GiB cap을 올리지 않았고 input/code closure·정확 output/ordered parent inventory 변경은0이다. Metadata admission을 음악 정확도나 전체 비교 완료라고 보고하지 않는다.
- **현재 경계/다음:** 전체 corpus 저장 실행기·output/manifest reserve·중단/전체 pair coverage terminal은 별도 다음 단계다. 이후 첫/max-cost 실제 group 자원 pilot 후 전체 대비를 진행한다. 정책/winner/confidence·Gold/학습·악보 UI·구조/작곡편곡/Git 변경0이며 별개 tracked5 사용자수정을 보존한다.
- **정본:** [계약·음악적 보존·개발 문제/교정·검사·실제 admission·한도·보존·다음](records/2026-10-03-cross-batch-contrast-implementation.md).

## HARM-DEV-20261003-29-RESOURCE — 자원 사전 점검과 전체 실제 replay 완료

- **목적/진행:** 사용자 승인에 따라 전체 numerical plan을 먼저 고정하고 source별 첫 batch/세 계획 비용 최대 batch를 결과와 무관하게 선정해 두 원 completion에서 자원 pilot를 했다. 이후 frozen runner의 **전체8,050요청 실제 계산을 완료**했다. 음악 정확도와 UI 적용은 별개다. 아래 착수/실행 중 기록은 당시 범위로 유지한다.
- **구현/보존:** `tmp/source_progression_resource_probe_20261003.py`에 입력 변경/body 저장 없는 fresh public native/role 자원 계측을 추가했다. 전체 fresh lattice와 archived본문 equality·원selector 범위·actual completion link·frozen `_batch`/Fraction guard·입력/코드 SHA·부모 inventory를 유지한다. 기존 core/runner/원XML/IR/주석/과거output·별개tracked5파일을 바꾸지 않는다.
- **측정/검수:** Windows current-process working set/private/peak와 available physical memory, 약30초 heartbeat, JSON/gzip bytes와 native/role prepare/explain 시간을 측정한다. 순수 helper import/selection PASS는 producer0이다. 독립 감사는 첫 배치만으로 충분하지 않음과128MiB 저장검사≠RSS 상한을 확인했다. 실제 결과·보존 guard·다음 결정은 완료 후 갱신한다.
- **Pilot 완료/실제 실행 착수:** 384.5278678999748초/exit0·8batch/128selector·native/role128개씩 computed16/16·raw 계정 검증 PASS다. Peak1,947,295,744bytes·표본8쌍gzip2,694,745bytes·23read/254,888,715decoded·보호4,789SHA/inventory6/7/7/148변화0을 확인했다. Tool stdout 일부 truncation을 명시한 root-compiled 계측 receipt와 실행 원코드 SHA를 정본에 기록했다. 원4completion/8,050분모를 유지한 frozen runner의 실제 전량 실행을 시작했고 admission46.8638651초/504batch 계획·새exclusive r1출력 시작을 확인했다. 전체 terminal/report 및 음악 정답률·UI·winner는 아직 미완료다. Source/producer 지원 threshold는 바꾸지 않았다.
- **정본:** [선정·측정·원자료/권한·한계·실측/실행 결정](records/2026-10-03-fresh-replay-resource-preflight.md).
- **실행 중 독립 검수:** 이미 닫힌 Sonata/no-link batch0·2의 원selector/fresh refs/음표/타이/Fraction 계정32path를 대조했다. 최종78,605유한 확인/불일치0/4.3720723001초, 읽은11파일 크기/SHA 변화0·producer/편집0이다. 초기 감사기의 lane/정렬/observed horizon 기대 오류와 교정 이력은 정본에 구별한다. 두 배치의 압축 SHA·full tie와 observed span·타이 continuation≠새 attack을 기록했으며 전체 완료/음악 정답률로 승격하지 않는다.
- **다음 큰 기능 기획:** [배치 밖까지 연결하는 진행 후보 대비](records/2026-10-03-cross-batch-progression-contrast-plan.md)를 읽기 전용 코드 검토로 정리했다. 기존256한도/public 의미는 유지하고 검증 facet·공통 rational refinement·20원그룹/1,652,640pair/570bounded block·공유근거/최소저장·전체 분모/미상/보류/중단·pilot/반례/완료 기준을 별도 새 adapter로 설계한다. 구현/대비 실행/정책/UI는0이며 현재 실행 중인 보호 코드/입력은 바꾸지 않는다.
- **전체 실제 계산 완료:** 5074.453444299987초/exit0, 원2source/4ordered completion·8,050native/role paths·504batch·fresh native 준비2/bundle4를 저장했다. 정확1025파일/183,060,358bytes, holds/incomplete/failure/partial0·원 요청 순서/분모 보존이다. Peak working set2,508,488,704bytes(약2.34GiB), 최저 관측 physical 여유13,371,228,160bytes이며 hard bound는 아니다. 수집684관찰 event/504고유batch 위치를 별도 reports receipt로 보존했다. 원322문맥/1,013lanes 중 미실행320/1,006과 전체 logical 경로 미평가를 유지한다.
- **종료 독립 검수/보호:** 최종67,141consistency 확인/58.2992549초/오류0·읽은1034경로 SHA 불변이다. Source0의 이전580본문 검수는 동일 terminal SHA/exact refs 및 최종 writer artifact hashes로 연결해 재사용하고 Quartet 신규428본문은 순차 metadata/Fraction/terminal 집계를 대조했다. 분실된 이전 개별580SHA 임시 목록과 직접 재대조했다고 주장하지 않는다. Root 별도 registered input4,784+code347의 union4,788 SHA/6.4173322초·exact parents6/7/7/148 변화0이다. 신규 unit test/producer 재실행/음악 정답 검사 수로 합산하지 않는다.
- **해석 한계/다음:** clause supported6,310/failed118,425/unassessed19,390·occurrence credit14570/3는 조건부 설명 계정이다. Ordinary true20/joint true8과 미상/보류를 음악적 정답·winner·학습/Gold로 승격하지 않는다. 전체 contrast는 미실행이며 다음 개발은 원 completion/key별 cross-batch adapter의 small equivalence·자원 pilot다. 현재 코드/원XML/IR/주석/과거 output·별개tracked5파일은 보존한다.
- **최종 QA:** MD4개 strict text/152local links·두 helper AST PASS, core/runner/tests4+probe/wrapper2+새receipt1의 총7 SHA 변화0이다. Read-only `git diff --check` exit0와 기존 tracked5파일만의 줄바꿈 경고/사용자 수정을 유지했다. 최종 출력1025목록은 별도 reports receipt를 넣지 않고 동결했다.

## HARM-DEV-20261003-29-CONT — 실행기 구현 범위 확인과 전체 진행 위치

- **정확한 승인 후 완료:** 사용자가 새 두 파일의 계산 호출/run/CLI·제한 저장기·synthetic/mock 검사 범위를 명시한 질문에 “네”라고 승인했다. 정상 patch로 closed binding/plan/header/batch/job·전체 순서/terminal 검증과 `run()`/CLI를 완성했다. 기본 총2GiB/manifest16MiB 예약·exclusive 저장·부분 파일 bytes/SHA·전체 원 작업과 prefix/미계산 분모·null 보존·progress observer·실패 exit1을 포함한다. 실제 corpus는 이번 승인/실행 범위에서 제외하며0이다. 아래 차단/검수 항목은 승인 전 snapshot이다.
- **연결 교정:** real query plan의 rational list를 integer로 검사하던 오류와 genuine witness.selected=False 오인을 수정했다. Runtime hold terminal의 incomplete complement·모든 작업 aggregate·쓰기 전 bytes 예약·held-empty를 known-empty로 표시하던 오류도 두 새 파일에서 교정했다. Top-level selected/rank/confidence는None·flagsFalse를 유지하며 음악 지원 조건/producer/특정 작품 threshold는 바꾸지 않았다.
- **최종 검사/보존:** 작성 담당 신규 저장22/22 PASS/89.970초와 root 독립 동일22/22 PASS/90.783초, root 기존 core47/47 PASS/68.132초다. 같은22재검사·중간19PASS·기존 admission7·genuine18확인은 새 검사 수에 더하지 않는다. Genuine tied XML packet과 ready/held-empty 연결, 나머지 mock archive/storage/adversarial 범위를 구별한다. 실제 read-only admission28.211113000055775초/23파일/254,888,715decoded bytes·보호4,784SHA·exact6/7/7/148과 원4작업/8,050계획은 일치했다. CLI help/import와 독립 정적 계약 검토도 PASS다. 최종QA와 네 파일 동결SHA는 정본에 기록한다. 실제 계산/새 corpus output·UI/구조/생성·Git은0이며 기존 tracked5파일은 보존한다.
- **문서/최종 QA:** 화성 개발문서4개에서 구현 상태와 승인 전 snapshot을 구별하고 교정·검사·한계·다음 미실행 명령을 기록했다. 네 AST/동결SHA·4문서 strict text/149로컬 링크 PASS, read-only diffcheck exit0·기존 tracked5파일 보존·예시 corpus output 부재를 확인했다. 기존 줄바꿈 경고는 변경하지 않았다.
- **요청/차단:** 사용자의 진행 답변을 근거로 새 runner 한 파일의 검증·집계·제한 저장기 구현을 시도했으나 자동 승인 검토가 fresh replay 실행/출력 쓰기 코드의 정확한 승인 범위를 요구하며 다시 거부했다. 적용0이며 다른 경로/agent/shell로 우회하지 않았다. 두 새 파일의 `run()`/CLI·batch 저장·총2GiB 제한·synthetic/mock 테스트 구현을 실제 corpus 실행과 구분해 확인한다.
- **승인 전 검수/보존:** 당시 runner265줄/19,884bytes와9개 draft 테스트149줄/7,355bytes의 SHA는 이전 snapshot과 같았다. Core/core test SHA도 동일했다. 당시 runner에는 admission만 있고 run/CLI/writer가 없어 새 검사·실제 corpus·산출물0이었다. 이전 신규54개 통과를 중복 합산하지 않았으며 원본/기존 코드/결과·UI/구조/생성/Git·별개 tracked5파일도 보존했다.
- **진행률:** 큰7기능과 생성 로드맵으로 대조했다. 화성 기반·계산 엔진은 중간 지점에 가깝지만 독립 음악 정확도·새 엔진 화면/구조 승격·실제 생성은 남아 있어 전체 목표 절반 완료라고 선언하지 않는다. 기능별 비용이 달라 단계 수/검사 수로 정확한 퍼센트를 계산하지 않는다.
- **정본/다음:** [후속 요청·차단·승인·구현·검사·SHA·미실행 명령·진행 위치](records/2026-10-03-replay-implementation-scope-and-progress.md). 다음은 별도 시간/메모리/출력 사전 점검과 원4completion 실제 계산이다. 예정8,050요청이나 exit0/기술검사 수를 음악 정답/완료 수로 쓰지 않는다.

## HARM-DEV-20261002-29 — fresh 원자료 진행 요청의 성부·역할 근거

- **목적/일반 규칙:** 단계28의 모든 saved 요청을 exact 전체 IR/scope/supplier provenance로 fresh rebind하고 원 두 completion의 실제 해결·NCT geometry·union 계정을 별도로 계산한다. 형태/개별 해결/전체 ordinary/조성·기능을 혼동하거나 서로 다른 성부 completion의 유리한 근거를 합치지 않는다.
- **구현/진행 상태:** 별도 immutable/HMAC bridge·전체 batch preplan·native/role stream과 direct 단계28 archival admission/append-only runner를 개발·검사 중이다. Native session2/bundle4/selector×completion8,050은 예정값이며 아직 실제 완료 수가 아니다. 악보/UI·구조·생성·학습/Gold와 Core/원자료/과거 출력은 미변경이다.
- **보강/한계:** role 준비의 native 재인증까지 비용에 계상한다. 계산 기록 ref가 있다는 이유로 평가 완료를 표시하지 않도록 실제 computed transition counts를 사용한다. 기존 frozen native API의 batch별 전체 lattice 복사 비용을 점검하고 실행 batch size/caps를 결과가 아닌 source-size 비용으로 사전 결정한다. 기존 contrast/policy256한도와1,652,640전체pair 때문에 전체 경쟁 비교는 별도 기능 단위로 남긴다.
- **승인 차단:** 핵심 bridge와 direct admission부는 추가했지만 새 계산/저장 `run()`·CLI patch가 자동 검토에서 두 번 차단됐다. 후속 구현 범위/낮은 위험 증거의 재검토도 거부되어 우회하지 않고 사용자에게 두 새 파일의 명시 승인을 요청했다. 실제 corpus8,050계산은0이며 새 storage 테스트의 실행기 의존 항목은 미완료다. 독립 core/기존 admission 검사만 계속한다.
- **검증/현재 부분 결과:** 새 core47개/80.2411426초와 저장자료 admission-only7개/46.174초 PASS(신규54개). Draft storage9개 가운데run() 의존2개는 미실행이며 full suite PASS가 아니다. 기존84회귀/143.571초는 별도다. 초기45검사의 fixture배열명·unknown key joint 기대2건만 교정했고 core 변경0이다. Batch3/64의 native/role 전체 path body·순서·raw 계정 동등성, 타이/full span·Fraction·null0·state/HMAC·whole budget을 확인했다. Root 실제 metadata-only admission27.8081182초/23read·254,888,715decoded bytes·보호4,784SHA/exact6/7/7/148과 원source/control/분모도 일치했다. 실제native/role/proposal/output0이며 당시 current346은 core test 생성 전 일시 inventory다. 현재 네 파일 SHA와 승인/미완료 상태를 정본에 보존했다.
- **정본:** [일반 규칙·계약·분모·한도·검사/실행 상태·후속 계획](records/2026-10-02-fresh-source-progression-evidence.md). 최종 검증/실제 실행·SHA는 완료 후 갱신하며 예정 수를 정답/완료 수로 승격하지 않는다.

## HARM-DEV-20261002-28 — 원음표 근거의 다양한 화음·혼합 경로·형태별 요청

- **목적/일반 규칙:** 직전 full/None·일률 V7/M 기술 panel의 한계를 지원 조건 완화가 아닌 입력 공급 보강으로 해결한다. Ordered 철자의 ordinary3/7화음을 quality+spelled root별로 보존하고 원 top2/nonordinary 대표·모든 controls를 유지한다. 원음표 source guard·missing 구성음·철자·유리수 시간은 보존하며 missing을 생략/기각/분산화음 확정으로 처리하지 않는다.
- **구현:** 별도 saved-only `source_progression_proposals`와 append-only 실행기 v0.1.0, 두 신규 tests를 추가했다. 원 seed와 모든 single-slot 교체, 각 cut의10종 형태/None options와 전체 vector/registered key·unknown·alias 순서를 보존한다. Source shape와 target triad core shape가 맞아도 실제 Secondary/해결/경계 지원은null이다. 다중 slot 동시 교체·전체 Cartesian 탐색이나 새 native authority는 아니다.
- **검증/교정:** 최종 핵심27개/37.616초·storage-only23개/109.012초 PASS(신규50개). 별도 기존 source47개/26.803초 PASS와 중간 재검사·감사 수는 중복 합산하지 않는다. root/member order·whole budget·input/contract mutation·seed/substitution/partition·원음표 refs/clip·shape tri-state·planned work/alias join을 보강했다. Pure expanded-source 반례와 temporary fixture/정규식/필드·문법 교정 이력은 정본에 보존했다.
- **사전 점검/한도:** Metadata-only16.7550815초/21read·215,581,434decoded bytes·전체272catalog/18,666origin admission은 proposal/native/output0이었다. 별도43.0905663초 preflight는 새 proposal2/native0/output0이다. 실제 실행 전 모든 source에 동일work250,000,000/path2,048/selector16,384/output128MiB를 선언했고 기본3M/512/4,096은 유지했다. 논리 visit 한도는 CPU/RSS/정확도 보장이 아니다.
- **단일 실제 r1:** 56.1784663초/exit0·두 등록 구간/7raw lanes·2source 저장·hold/failure0. Requested12interval의981origin 발생에서 eligible615/제안421/미제안194, 완전경로714·Cartesian42,851/미제안42,137, 원 controls100/추가3,925/전체4,025selector·compatible family/quality option390발생을 저장했다. 전체checked shape45,400와 구별하며 양성 화성·곡·정답 수가 아니다. 원322/1,013·미실행320/1,006·등록pool5/원native universe를 보존한다.
- **보호/향후 실행:** 정확6output/1,842,099bytes, creationinputs4,774/current343code와 부모7/7/148inventory를 보호했다. Root report 포함 고유4,784SHA·목록 전수검사에서 변경0이다. 원339creation목록은 소급 변경하지 않는다.4후속 completion 작업/8,050selector 발생은 계획이며 native evaluation/fresh session0·미승격flagsFalse/selected·rank·confidenceNull이다. 원자료/Core/주석·과거출력·운영UI/구조/생성/Git·Gold·훈련 미변경이다.
- **감사/QA:** 독립 saved 계약6,315,402확인/18.0828762초, 별도 source 음악본문182,248/6.9981626초+음가/tie242/0.6377657초(합산182,490/7.6359283초), 저장기 측4JSON/doc metadata0.009413초 모두PASS다. 감사 확인 수는 대부분 JSON visit/유한 산술이며 unit test·음악정답 수가 아니다. 초기 auditor keyprefix 가정만 교정했고 제품/자료는 그대로다. 3,570requestgroup/3,985vector/60alias·모든provenance/원controls/source/time/sound·Cartesian과4futurejob 참조가 일치했다. Missing299/421은 여전히 남으며 실제 sourceE♭7→A♭triad와 D♭5tie 사례를 정본에 보존했다. Root4동결SHA·7text/4AST/140local links/read-onlydiffcheck는 오류0이고 기존별개tracked5파일은 보존했다.
- **다음/정본:** Exact 원음표·supplier provenance의 fresh native session에 새 후보를 연결해 같은 실제 completion의 역할·해결·union·경쟁 비교/조건부 정책을 평가한다. [계약·일반 규칙·검사·실제 실행·보존·한계](records/2026-10-02-source-grounded-progression-proposals.md)에 별도 화성 개발 기록을 관리한다.

## HARM-DEV-20261002-27 — 완전 진행의 조건부 제안·보류 정책

- **목적/일반 규칙:** 같은 source/key/전체 completion/partition/vector 안에서 명시한 기능 요구의 지원·보류를 판단한다. 미관측 구성음은 자동 생략/화음 부재가 아니고, shape 불일치는 해당 declared strategy만 불충족이다. 개별 leading이나 설명량·member 수·cut 수로 최종 진행을 선택하지 않는다. 빈/None vector는 vacuous 지원으로 통과하지 않는다.
- **구현:** 별도 saved-only `native_progression_policy`와 append-only 저장기 v0.1.0, 신규 두 tests를 추가했다. P01–P10 규칙·원순서 대안·diagnostics·cut별 whole/개별 ordinary·account pointer·100fixed-premise그룹을 보존한다. Pure literal member/bass/time/attack/tie/raw-state/union/function shape·axes/template 연결을 검증하지만 native/role/contrast producer나 NCT predicate는 재실행하지 않는다.
- **개발 교정:** missing=None, raw-state/account collusion, slot 간 음표 차용, shape/axes/joint/template join, member-time credit와 conditional union, strict bool/null0, incomplete authentic bundle의 전체 hold를 보완했다. source guard를 sound별 캐시하고 diagnostic-copy/atom×credit/reference 비용을 charge했다. 저장기는 sibling completion의 shared input을 admission-time digest로 보호한다. 초기 메시지 기대1건·budget0 fixture 기대1건 및 storage Path fixture2건은 최종 검사 전에 교정했다.
- **검사/한도:** 최종 핵심41개/32.230초·storage-only19개/66.805초 PASS(신규60개, 중간 재검사 중복합산 없음). Metadata-only29.2637953초/22read·258,951,864decoded bytes와 pure 비용 추가 점검0.6668874초에서 실제 정책/producer/output0이었다. 최대planned40,265,338을 확인해 네 그룹 모두 동일work41,000,000으로 사전 선언했으며 기본2,000,000은 유지했다.
- **실제 단일 r1:** 63.47109879995696초/PASS4completion·두 등록 구간7raw lanes·200평가/100fixed-premise그룹·전체 hold/계산 실패0. 보류120/명시 기능 shape 불충족80/strict 조건부 지원0이다. 이는 화음0/음악 실패율이 아니며 full/None120과 일률 ordinary80인 제출 기술 panel의 한계도 확인했다. 원900비교와322/1,013·미실행320/1,006, 등록pool5/원 native universe·제안/미제안 분모를 유지한다.
- **보호/상태:** 정확7output/1,162,843bytes. 입력4,763·현재339 code/schema/tests의 고유4,767경로와6artifact, 부모7/148inventory를 전후 보호했고 변경/failure0이다. report까지 고유4,774creation/input/output경로와 네 새 파일 동결SHA는 정본에 기록했다. 이전335목록은 소급 변경하지 않는다. 원 source/Core/주석·최종화성/NCT/key/cadence·rank/confidence·학습/Gold·UI/구조/작곡편곡/Git은 미변경/미승격이다.
- **감사/회귀/QA:** 저장기 측 metadata5,156,229확인/13.6882151초, 독립 atom·union·계약512,175확인/4.1037675초, 독립 음악/source7,182확인/13.1221803초 모두 PASS다. 원음표·타이·재발음·미관측G♭·실제D♭bass·기능 branch불충족과보류를 대조했고 producer/정책 재실행·파일 수정0이다. 감사 확인 수는 신규 test·음악 정답 수로 합산하지 않는다. Root 기존 contrast28개/16.654초 PASS는 신규60개와 별도다. Root QA4,774SHA·새7/부모7·148inventory·current339code·7text/4AST/141로컬링크와read-onlydiffcheck 오류0, 기존별개tracked5파일의경고/수정은보존했다. 상세 검수 범위는 정본에 기록했다.
- **다음:** ordinary3/7화음과 expanded 후보를 함께 보존하고 실제 source/target shape에 맞는 관계 종류별 진행 제안을 보강한다. 모든 cut에 V7를 강제하거나 결과에 맞춰 이번 조건을 완화하지 않는다.
- **정본:** [계약·일반 규칙·양성/반례·실제 보류 원인·보존·한계](records/2026-10-02-progression-proposal-hold-policy.md).

## HARM-DEV-20261002-26 — 완전 진행의 원음표 정렬 경쟁 비교

- **목적/일반 규칙:** 직전 source panel의 모든 batch를 같은 source/scope/lattice/key/하나의 전체 성부 completion별로 모아, 완전 진행의 경쟁 해석을 같은 원음표·rational clock에서 비교한다. Candidate-only와 transition-only·양쪽 변경·partition 대비를 구별한다. 구성음 흡수/NCT credit·설명량·추가 cut으로 승자를 선택하거나 다른 key/completion의 유리한 근거를 합치지 않는다.
- **구현:** 별도 `native_progression_contrast`/append-only 저장 실행기 v0.1.0와 두 테스트를 추가했다. 여섯 category의 sound별 refinement/transfer/delta, strict 동시·pooled member 관찰, full tie/attack 및 source closure, literal bass·조건부 전위·같은 signature cut, 실제 first-change/ordinary/기능·종지 전제를 보존한다. Saved identity/creation SHA adapter이며 live native issuer나 역할 재추론이 아니다.
- **발견/교정:** 초기 AST 선언 오류와 reseal fixture prefix 두 오류를 교정했다. 독립 검토에서 native raw-state account exact 재검증, pair cover²/source refs와 atom×empty-credit-clause 비용을 추가했다. Loader의 greedy 원순서와 canonical sorted links 차이는 중복 없는 exact edge 관계로 검사하도록 수정했다. Category 변경 배열과 shape alias의 표현 한계도 명시했다. 원자료/이전 계산/특정 음악 규칙은 바꾸지 않았다.
- **최종 검사:** 핵심28개/16.233초 및 storage-only18개/42.561초 PASS. Genuine synthetic fixture와 pure helper/planner control, mock 저장 검사, 실제 음악 saved 대비를 구별하고 중간 재검사를 중복 합산하지 않는다. 네 source/test 동결SHA 및 개발 중 교정 이력은 정본에 보존한다.
- **한도/실제 단일 r1:** 결과 전 metadata+pure plan20.5475888초(신규 계산/출력0)에서 최대planned4,776,760을 확인하고 네 그룹 모두 동일work5,000,000·max_pairs2,000을 정했다. 기본work2,000,000은 그대로다. 실제55.895776199991815초/PASS4groups·두 등록 구간7raw lanes·200facet·900pair·hold0·원음가보존200/200이다. Strict 후보대비100/기능80/후보+기능80/partition640·shape alias0이다. 음악 정답률이나 전체 logical 경로 검사로 표현하지 않는다.
- **보호/범위:** 정확7output/3,056,742bytes,4,752inputs/335current code·schema·tests의 고유4,756경로와6artifact를 보호했다. 원phase25의148파일·322문맥/1,013lanes·미실행320/1,006 및 원 universe/제안·미제안 분모를 유지한다. Fresh native prepare/역할 producer/운영UI·구조/작곡편곡/Git 변경0이며 source/Core와 모든 과거 출력은 그대로다.
- **독립 감사:** metadata/참조/SHA60,753확인/13.9759738초, stdlib-only source/Fraction5,257,597확인/18.0094096초, 음악/source 및 네사례108,196확인/18.4977874초 모두 PASS다. 200facet/900pair·35,100category atom/14,400bass atom·rational transfer/delta·원 IR/타이/재발음·missing G♭·개별 leading지원/전체 ordinary실패·실제D♭bass와추가cut을 대조했다. 서로 다른 감사 확인 수를 신규 test나 음악 정답 수로 합산하지 않는다. Producer/compare 재실행·파일 편집0, exactrefs와 검수 범위는 정본에 보존한다.
- **보존 QA/다음:** root 별도4,763creationSHA/1.8966553초 변경0·부모148/새7inventory누락추가0·current335code inventory일치,7파일text/4AST/135로컬링크와read-onlydiffcheck 오류0이다. 최종 문서 교정 후 합동 QA2.0341876초에서도 같은SHA/text/AST/link/inventory 오류/변경0과diffcheck exit0을 재확인해 이번 단위를 완료했다. 기존별개tracked5파일의 LF→CRLF경고·사용자수정은보존했다. 최종 화성·NCT·key·cadence·rank/confidence·학습/Gold·generation-ready는 보류한다. 다음 큰 단위는 여러 음악적 근거를 함께 쓰는 일반 진행 제안/보류 정책이다.
- **정본:** [계약·일반 음악 규칙·실제 원음표 사례·검사·한도·보존·한계](records/2026-10-02-native-progression-source-contrasts.md).

## HARM-DEV-20261002-25 — 원 음표 근거의 후보 패널과 실제 양성·반례

- **목적/일반 규칙:** 직전 first-ID 기술 패널의 실제 역할 양성0 공백을 보완한다. Fixed observed-grid partition을 먼저 정하고, 각 요청 interval의 모든 origin에 대해 source-guarded spelling membership·pooled member/root note-time·미관측 구성음 수를 계산한다. 다른 철자 signature의 경쟁 후보와 모든 등록 key·None/V7/M vector를 보존하며, 원주석·특정 작품 정답·NCT 성공을 제안 관문으로 사용하지 않는다. 제안 순서는 최종 화성 순위가 아니다.
- **구현:** 별도 authenticated `factor_source_evidence_panel`과 append-only `factor_source_evidence_trial` v0.1.0, 새 두 테스트를 추가했다. Genuine native 전체 IR/scope를 fresh prepare하고 동일 후보들을 no-link/actual full-scope bundle 각각에 같은 순서의 최대3개 batch로 제출한다. 최대2 source-size-selected 구간·64selector·사전 role cap100,000,000과 전체 한도/known0/unknown을 저장한다. 기존 Core/parser/XML·phase22/23/24·UI/구조/생성/Git은 미변경이다.
- **발견/교정:** planner의 과도한 고정 상한·불완전 inventory의 거짓0·known-zero path와 미상 전체 스캔 혼동을 보완했다. 저장기의 빈 제출 완료 오표기, unknown/uncomputed credit의0 변환, 서로 다른 context/IR/scope의 사례 병합도 실제 실행 전에 교정하고 반례를 추가했다. 원 과거 helper/출력은 덮어쓰지 않았다.
- **검사:** 최종 신규 공개47개/24.282초(42 genuine fixture/API·5 pure 산술), 저장19개/9.844초, 별도 기존 역할57개/72.631초 PASS다. 초기45의41PASS/4fixture·budget 기대 오류와 초기 storage15PASS/12.314초를 최종 수에 더하지 않는다. 네 source/test 동결 SHA와 교정 이력은 정본에 보존했다. Metadata-only37.1888887초의 native prepare/비교/출력은0이었다.
- **실제 단일 r1:** exit0/566.4350003000582초, Sonata01-1/Quartet 두 등록 구간/7raw lanes에서 272fresh interval/18,666native origins를 보존했다. 패널12interval의981origin occurrence는 eligible615/rejected366, complete paths12/구간별 key5이다. 4completion·68ordered batch·200selector occurrence와 account 모두 raw note-time을 보존했고 whole hold0이다. 전체322/1,013 중 이번 미실행320/1,006, 등록5pool 중 미실행3을 명시한다.
- **조건부 결과/사례:** 3,430clause occurrence는 supported90/failed2,910/unassessed430이다. 보조50·경과25·계류-like10·개별 이끎음5이며 전체 ordinary 해결 성공과 구별한다. 설명량 합185/6quarter는 selector occurrence 중복을 포함하여 악곡의 설명된 실제 시간/정답률이 아니다. 3,000qualified candidate occurrence의148source-scoped geometry/status에서24샘플을 저장하고 미보관124를 명시했다. 원 note pitch/duration/onset·source/measure/beat·full sound/IR와 후보별 전제·같은 completion refs를 연결했다.
- **보호:** 정확148output/16,302,378bytes, inputs4,600·current code/schema/tests331의 union4,604 및147artifact를 포함한 고유4,751경로 SHA의 변경0이다. Root 별도4.7068442초 stream 재검수와 exact output inventory도 일치했다. 원 phase22/23/24의28/8/10파일 목록도 보존한다. 과거 producer 재실행이나 음악 정확도 검사가 아니다.
- **독립 감사:** 별개 metadata15,104확인/6.983132초, saved-case23,720확인/6.0129334초, panel/role1,352,361확인/17.2466763초 모두 PASS다. 원18,666origin·요청981pool·정렬/selector/batch·200raw profile·3,430clause의 첫 변화/None-False/ordinary OR-AND/Fraction union과 여섯 범주,24case/430candidate occurrence의 원 IR/음표/음가/measure/beat/refs를 독립 대조했다. 감사의 nullable alternative·canonical link-order·Windows 전달 한도 가정만 교정했으며 제품/출력을 바꾸지 않았다. 새 cold 재실행·음악 정답률/전체 논리 경로 평가가 아니다.
- **최종 QA:** 별도 legal-edge/budget316확인/5.7932981초와 pre/post SHA2.0533231초 PASS, 고유4,751파일 변경0·148output 누락/추가0이다. 최종7파일 text·4AST·130로컬 링크·네 source/test 및 report/plan/index/case·147artifact 동결 SHA·정확 output inventory에 오류0이다. Read-only diff check는 exit0, 기존 별개 tracked5파일의 LF→CRLF 경고만 보존한다.
- **다음:** 실제 양성과 반례를 바탕으로 완전 진행의 경쟁 화성/기능 해석을 공동 비교한다. 최종 화성/NCT/key/cadence·rank/confidence·학습/Gold·운영 악보/구조/생성은 아직 미승격이다. 최종 QA와 모든 동결 SHA·실제 음표 예시는 정본에 보존한다.
- **정본:** [일반 계약·개발·검사·실제 음표 사례·보존·한계](records/2026-10-02-source-evidence-role-panel.md).

## HARM-DEV-20261002-24 — Native 다중 화음 진행의 동일 성부 역할·union

- **목적/구현:** 직전 계획의 local passing/neighbor·boundary anticipation/suspension·명시 ordinary 이끎음/7음 역할을 exact native 진행/key/transition vector/하나의 실제 full-scope bundle에 연결하는 별도 sidecar와 제한 실행기를 구현했다. 기존 raw profiles/whole-path account/기능·종지 전제, source/Core/parser·기존 출력·UI/구조/생성/Git은 보존했다.
- **일반 규칙:** 두 실제 local 링크와 full-slot envelope, 인접 pair preparation/held·재타격/첫 변화·철자/음역/공격 guard, explicit source/target shape와 역할별OR·역할 간AND를 요구한다. Multicut/unknown·서로 다른 completion을 유리하게 합치지 않는다. Sound별 rational clip union 후 guarded nonmember만 credit하며 여섯 범주 합과 원음가를 보존한다.
- **계약 보완:** exact native 비교 재계산→owned/HMAC 발급, parent state identity·사용 전후 freshness, 원 request/hold 분모 보존, 반복 source-note closure 비용·전체 budget와 빈 요청0, 철자 미결정 critical identity의None와 known no-link/wrong-shape False 구별을 추가했다. Pure helpers만 재사용하고 old two-slot ID/credit를 trim·재봉인하지 않았다.
- **검사/이력:** 최종 신규57개/96.814초 PASS(그중 pure arithmetic1), storage-only15개/1.463초 PASS, root 동일15개/1.309초 및 별도 기존 native55개/61.913초 PASS다. 초기52의50PASS/fixture2건 오류, 중간56PASS·storage seal-fixture 오류와 독립 재현/계약 보완을 정본에 기록했으며 최종 검사 수에 중복 합산하지 않는다.
- **실제 r1:** 단일 fresh prepare/119.366852초/exit0. Sonata01-1 full IR와 exact scope 1문맥/3원 raw lanes, 17좌표/136fresh interval/11,381origin, no-link와 18actual-link 두 complete bundle 아래 full/2slot/3slot 총6기술 selector·6계정의 원음가85/2를 보존했다. Native/role whole-hold0이며 전체322/1,013 중 이번 미실행321/1,010을 분리한다.
- **양성 공백/미승격:** 실제89clause는 85unassessed/4failed/0supported, credit0이다. First-ID 패널의 spelling-withheld origin·full slot 밖 triple은 미판정이며 모두 실패/정답으로 바꾸지 않는다. 합성 양성을 실제 정확도 개선으로 확대하지 않는다. 최종 화성/NCT/key/cadence·rank/confidence·학습/Gold/생성/UI는 미승격이다.
- **보호:** 정확10output/5,199,000bytes와 inputs4,586/current code·schema·tests327의 union4,590SHA·원 phase22/23파일 목록 변경0. Root 별도 stream SHA3.974654초/생성·보호 고유4,600경로와10파일 inventory도 일치했다. 전체 parent cold replay/전곡 평가가 아니다.
- **독립 감사/QA:** saved finite37,637assertion/12.883512100초 PASS. Source closure·136catalog/11,381origin·두 bundle·여섯 native path refs, 89clause의 guard/실제 첫 변화/None-False와 sound별 Fraction union·여섯 범주·각 raw85/2를 독립 검수했다. 원322/1,013 대 실행1/3, 보호4,590SHA·원28+8/새10파일 목록도 일치했다. 초기 링크 순서 가정은 감사만 canonical order로 교정했고 제품·출력은 그대로다. 실제 양성 검수0이며 fresh native 재실행·정답률이 아니다. 최종7파일 text/4AST/126로컬 링크·동결 source/test4와 report/plan/index3의 SHA가 오류0, read-only diff check는 exit0이다.
- **다음/정본:** 실제 음표·진행 전제로 제안하는 bounded 후보 panel의 양성·반례를 확보하고 같은 completion의 완전 진행 비교에 연결한다. [계약·개발·검사·실제 실행·검증 공백](records/2026-10-02-native-role-explanation-union.md)에 모든 검수와 다음 계획을 별도 화성 개발 기록으로 보존했다.

## HARM-DEV-20261002-23 — 동일 계약의 후보 시간창 계산 공유

- **목적/순서:** 직전 실제 lattice 약38분의 명확한 중복 window를 먼저 분리하여, 다음 NCT 역할 union 연결 전 확장 비용을 줄인다. 화음 종류·정답·후보 관문이나 특정 작품 규칙을 바꾸지 않는다.
- **구현:** additive augmented/extended/catalog adapter3개와 full IR 소유 공급기·실행기를 추가했다. Fixed context 한 창만 batch 간 공유하고 raw span별 base는 batch 내 공유한다. 후보 ID/순서/pointer·음가·blockers·각 target/hypothesis theory observer 및 기존 validation을 보존한다. Provenance/측정은 별도 receipt이며 native lattice 권한을 사칭하지 않는다. Frozen/HMAC source/state/cache·code freshness·JSON strict time·whole-budget/null-vs0·context/output byte 제한을 포함한다.
- **발견/교정:** marshal code 직렬화의 실행 후 SHA 변화가 정상 실행을 변경으로 오인하여 semantic code fingerprint로 교정했다. Immutable owner/cache seal·과거 output의 nested 생성 금지/목록 보호·public call 인증 비용 포함·SHA 충돌 등록 거부도 독립 검토로 보완했다. 초기35의11PASS/23오류/1기대값failure 및 다음44의1 fixture failure는 최종 성공 수에 더하지 않는다. Repeat fixture는 현재 parser가 미수입하는 표식을 원 genuine XML에서 읽어 시험용 IR 관찰 필드로 복원했음을 명시하며 parser 구현 완료가 아니다.
- **검사:** 독립 핵심44/49.441초·저장/선택8/0.034초, root 동일52 합동50.827초 PASS. 별도 기존 공급기4suite72/0.453초 PASS. 전체 repository 검사나 음악정답률이 아니다.
- **실제 시험/비용:** 단일r1 exit0/42.751915초. 5등록full IR 문맥/25요청 occurrence/20distinct context+span/2,602후보 occurrence(중복 제외2,116)가 cold/warm 모두 fresh untouched legacy와 전체 JSON 일치했다. 기존 계산14.694741초+serialization0.326212, 새prepare+cold12.686926, warm8.670821초다. 일부 작은 단발 요청은 더 느렸다. 실측cold20/warm15window와원함수구조상90호출을구별한다. Full native cold/이전저장catalog/모든logicalpath/원parent 권한은 재실행하지 않았다.
- **보호/산출물:** 새8output1,012,788bytes와등록IR/scope·기존code/test/output·새code/test고유365SHA의변경0,원phase22 exact28파일목록전후동일. 기존source/parser/Core/XML/UI·구조·생성·Git은미변경이다. 365는과거전체4,539inputs cold replay를뜻하지않는다.
- **다음:** 새 producer 단계에서 same-completion local/boundary NCT 설명 union을 연결한다. 이번 공유기를 기존 frozen native 권한에 소급 주입하지 않는다. 실제 NCT/종지 양성 검수·최종화성 선택·confidence·Gold/학습·운영 적용은 남아 있다.
- **독립 감사/QA:** saved finite270,745확인/3.630563초 PASS. Base263/candidate30,766cell·원source239sounds/243notes의문맥별union·origin순서/type/유리수음가·catalogdigest/coldbody/warmreceipt·집계·365SHA/원28·새8inventory를확인했다. 공개producer재실행이나음악정답이아니며warm은저장receipt범위다. Root후속365protectedSHA/7artifactSHA/정확8output·10파일text/7AST/124로컬링크와read-onlydiffcheck도오류0이다.
- **정본:** [계약·검사·실제 비용·교정·다음 단계](records/2026-10-02-shared-candidate-window-supply.md).

## HARM-DEV-20261002-22 — 새 내부 구간 공급과 다중 화음 완전 진행

- **목적/일반 규칙:** 모든 observed endpoint 사이의 positive interval을 원 full IR에서 fresh 공급하고, 세 화음 이상을 새 native path/origin/bundle 계약으로 비교한다. 기존 one-cut variant trim·legacy ID 위조·독립 witness의 해결 합산·특정 작품 정답 조건이 없다.
- **구현:** exact slot-count DAG와 known/unknown/zero 분모, 원 provider/철자 대안/unknown key, 하나의 전체 raw-lane completion, complete closed selector, raw 유리수 clip/전체 음가 계정, actual first-change ordinary 전략과 경계·전위·음도·release·종지 전제를 연결했다. NCT credit는 아직 null/미통합이며 provider ornament를 증명으로 사용하지 않는다.
- **검사/보완:** 최종 공개55개/56.358초, storage-only 실행기35개/5.257초 및 root 동일35개 재검사5.160초, 별도 기존3suite124개/254.307초 OK. 같은35개 재검사를 신규 항목으로 더하지 않는다. 두 초기 core-test fixture/helper 오류와 storage mock의 ID 충돌은 테스트만 수정했다. 독립 audit로 state identity HMAC/prepare issuance window·strict DP 자료형·source closure를 포함한 query plan을 보강했다. 순수 DP4,164 weight 조합 감사는 공개/실제 음악 검사 개수와 구별한다.
- **실제 시험:** 단일r1 exit0/2,260.335986초,5선택/15raw lanes 저장·실패0이다. 정확full IR의1,469fresh interval/133,447native origin 대안·10complete bundle·250selector(75distinct origin path×key)/550slot/300내부전환/800boundary를 저장했고 전체예산보류0·원음가보존250/250이다. Metadata 등록검사와 현재 IR/scope fresh 공급이며 전체과거parent coldreplay/전체logical path/화성정답 평가가 아니다. Sonata제한교정본exact binding과원parent분모·전체322/1,013·미실행317/998을보존했다.
- **보호/비용:** 등록inputs4,539/code·schema·신규test320/정확28output75,303,652bytes를보호했다. Root별도전수stream SHA와목록은report포함고유4,571경로변경0이다. Corelli1,421.550976초/Mozart483.227186초라는비용과읽기전용current working set3,619.6MiB표본을기록하며peak RSS나원인확정으로표현하지않는다. 반복window공급/validation·origin재seal·copy/freeze/thaw·압축은정적비용후보이며후속관측·동일계약계산공유가필요하다. 실행중코드변경·예산후퇴·유리한prefix가없다.
- **독립 감사:** 전5문맥saved finite603,914확인/96.585436초오류0(첫3의167,698/25.472와교정last2의436,216/71.113436)이며별도metadata/SHA·작은sidecar9,227확인/4.424096초도PASS다. Last2초기437,300확인/72.012초중auditor의전체skeleton=nonzero라는가정60행오류는제품/자료수정없이unitweight DP로교정했고부분252/24.009초와초기실패를최종PASS에더하지않는다. Certified0 interval13·nonzero skeleton1,650,180,096/known-zero3,181,854,720/unknown0과원전체분모가일치했다. 전250panel에ordinary critical-note occurrence0/선언150joint False·나머지150None·종지nominalTrue/confirmed0이라는실제양성검증공백을기록했다. Fresh build/prepare/cold/전체logicalpath나신규unittest수·음악정답으로승격하지않는다.
- **최종 QA/기획:** 신규4source/test동결·직전4source/test·report/plan/indexSHA불변,7파일stricttext/4AST/130로컬링크와read-onlydiffcheck오류0이며기존unrelated5LF→CRLF경고를보존했다. Native 설명계층의authority/같은actual links/multicut미지원/role union/rawtime/wholebudget/반례등후속10기준은기획으로보존했고아직구현완료가아니다.
- **미승격/다음:** UI/구조/생성/Git 미변경, 최종 화성·key·NCT·cadence·확률/승자·학습/Gold 미승격. 새 arbitrary partition에 local/boundary 역할 credit의 same-completion 합집합 계정을 연결하는 것이 다음 큰 단위다.
- **정본:** [native 계약·분모·일반 규칙·검사·실제 실행 기록](records/2026-10-02-native-multi-slot-interval-lattice.md).

## HARM-DEV-20261002-21 — 완전한 진행의 조건부 조성·기능·종지 전제 연결

- **상태/목적:** 연구용 구현·동결 검사·실제r1·독립 저장 감사 완료. 같은 원 full-hold/one-cut·key·실제 completion의 직전 공동 비교에 native 경계 관찰과 기능·cadence 전제를 연결한다. 단순 applied 문자열/임시표/V 도착을 Secondary·Cadence 정답으로 승격하지 않는다.
- **일반 규칙:** 경계 before/at와 actual attack/tie carry, 도착/full release/관찰 horizon, literal bass/upper와 조건부 전위·음도를 구별한다. exact source/target function 형태·source/core/bass guards·동일 bundle의 직접/지연 ordinary 역할 근거를 함께 보존한다. 구조적 성부·국소 조성·호흡 등 미확립 의미 전제는 계속 표시한다.
- **범위/보호:** 신규 sidecar와 실행기·반례 검사만 추가한다. 기존 legacy path/view를 위장하거나 새 partition/key/completion을 만들지 않는다. 원자료·과거 결과·음가·전 미실행 분모·보류/unknown 보존, whole budget와 authentic replay, append-only 저장을 검증한다. 원XML/IR/parser/UI/구조/생성/Git/API 미변경이다.
- **검증:** 동결 핵심50개/166.253초(공개40+pure10)·동결 후 실행기37개/2.560초와 별도 기존5suite173개/267.587초 OK다. 실행기 앞37개/2.591초와 root 재검사는 같은 고유 항목이다. 중간50개49통과/1실패는 unknown coordinate와 signature-derived universe provenance를 혼동한 기대값 오류였으며 source/원key 변경 없이 검사만 교정했다. 장단조 parallel tonic/분석 시작 HC의 nominal 조건을 제한하고 실제 helper quality를 연결했다.
- **실제r1:** 단일 authentic cold process exit0/1,594.719346초·5문맥/15raw lanes 저장·0실패. 원300selector/75distinct tuple×key 아래875selector경계·200distinct tuple×key×boundary·15literal 좌표·43terminal probe·605same-raw-lane pair·25,800logical work를 저장했다. Function 형태1,250/전제평가275/actual motion25, known key240path/unknown60path, joint conditional8·조건부전위720·cadence 전제2,625는 정답 수가 아니다. 미실행317문맥/998lanes와 전체 논리 universe를 유지했다.
- **사례/보호:** Sonata의 G4→A♭4 실제지연route·비구성음bass·뒤완전core제시와 Mozart의 E5→F5 역할지원이 있어도 A♭/E♭ pooled core 미관측 때문에 기능보류하는 대조를 원note/sound/path/bundle/time refs로 기록했다. 정확8파일5,610,484bytes/4,529inputs/316producer·schema·원phase20 참조와 분모의 독립 metadata 감사 PASS.
- **독립 finite/QA:** 전5문맥 저장 source·literal/time/terminal·원parent/account·same-bundle pair 및 전제/분모 대조7.400초/147,454assertions·유리수 검사 PASS. Saved finite 감사이며 fresh공개/coldreplay·신규147,454test나정답률아니다. Pair carry110/requiredlink55/불충족440, terminal43중arrival와release다름24/endpoint10·beyond1은unknown 보존. PAC/IAC nominal 실제양성0인검증공백과HCnominal15≠확정종지를기록했다. 독립문서/사례검수일치, root별도report포함creationSHA4,539개·신규/직전8source-test동결/정확8output 변경0. 7파일text/4AST/124local links/read-onlydiffcheck 오류0이다.
- **다음:** 여러 genuine 내부 span과 세 화음 이상의 완전 partition을 새 native authority 아래 같은 전 성부 completion에서 공동 비교한다. 기존 one-cut winner나 서로 다른 witness의 유리한 해결을 이어 붙이지 않는다. 더 넓은 local-key evidence는 이후 독립 버전으로 설계하며 운영 UI/확정 음악 해석/학습·생성은 별도 검증·적용 단계다.
- **정본:** [계약·일반 규칙·한도·검증 및 실제 실행 기록](records/2026-10-02-progression-functional-and-cadence-context.md).

## HARM-DEV-20261002-20 — 완전한 진행 후보의 동일 성부 근거 비교

- **목적/일반 규칙:** 원 전체 구간 full-hold/one-cut partition의 경쟁 화음·key·명시 기능 대안을 하나의 등록 실제 completion에서 비교한다. 원 origin/profile·모든 slot의 경쟁/terminal function 형태·불확실성을 유지하고, 서로 다른 가정의 유리한 근거를 합치지 않는다.
- **구현:** 새 `factor_progression_evidence`/append-only 실행기. disjoint slot와 sound별 interval union으로 원 총음가와 조건부 설명량을 보존한다. unordered category delta는 caller 방향 표기이며 winner/rank/confidence가 아니다. explicit assumption 평가 수와 actual ordinary motion 대조 수, distinct tuple/function과 selector 반복 수를 구별한다.
- **검사:** 동결 신규 핵심37개/120.842초·실행기30개/124.108초, 직전 지연 해결76개/340.205초 각각 OK다. 한 번의 143개 전체 회귀로 표현하지 않는다. fixture 오류·교정, wrong-family motion 과계수 방지, 닫힌 authority/한도와 producer closure는 정본에 기록했다.
- **실제 r1:** exit0/1,470.694629초/5저장·0실패. 기존5구간/15raw lanes의300selector·8,850비교·75distinct tuple×key·1,250distinct function형태·275명시전제평가·25actual motion행을 저장했다. 43,415logicalwork/300whole-path계정의원총음가를보존했다. 양성55selector와60credit sound×selector 발생을구별하며정답률·전곡평가아니다. 원universe/미실행317문맥998lanes는그대로다.
- **독립 감사·보호:** 전5문맥 saved finite/독립산술 PASS(보고된active11.59초). 5,750반복포함function body·14,560raw-profile행·같은bundle의60credit발생·8,850delta를대조했다. fresh공개compare/parent coldreplay를한감사로포장하지않는다. 4,519inputs/314producer·schema와새8파일7,516,755bytes/직전8파일SHA·목록보존. ROOT전수재검사도report포함고유4,529creationSHA변경0이다.
- **사례/현재 상태:** 실제Sonata E♭4의LEFT3/2조건부경계설명·RIGHT구성음과fullhold비교, Mozart E5의동일원음/구성음계정에서목표quality전제별1/2설명차이를정본에기록했다. ordinary미검사와조건부설명량을혼동하지않는다. 원source/Core/XML/과거output/운영UI·구조·생성/Git은그대로이며연구용구현/검증완료다.
- **최종 QA:** 7파일strict UTF8/NUL/U+FFFD/공백·4AST·125로컬파일링크통과. source-test새4개/직전4개동결SHA와현재314producer/exact8output·report포함고유4,529creationSHA변경0, read-only diff check exit0(이번7파일경고없음)이다. 독립메타데이터추가검사1.2325602초도contract5/stagerefs40/hypothesis300/delayedquery275와미승격flags일치다.
- **문서 검수:** 독립 최종 검수에서 분모/complement와 Sonata/Mozart 저장 사례의 typed refs·유리수 계정 일치. raw wrapper가 cold replay 전에 검사하는 범위는 한도 이름·자료형이라는 정확한 순서로 문장만 교정했다. 코드·테스트·부모 계산은 그대로다.
- **미승격/다음:** 전체 임의 다화음 segmentation이나 최종 화성/key/NCT/cadence·학습/Gold 승인 아님. 큰 다음 단위는 완전 진행의 근거를 명시 조성/적용화음/기능·전후 cadence 전제로 연결하는 것이다.
- **정본:** [계약·개발·검증 기록](records/2026-10-02-complete-progression-evidence-contrasts.md).

## HARM-DEV-20261002-19 — 명시 해결 전략과 동일 completion의 지연 해결

- **목적/착수:** 이끎음·7음의 실제 발생 목록, 명시한 ordinary 전략, 같은 전 성부 completion의 충족을 분리한다. 기존 direct/temporal/boundary 결과와 원 source/Core/운영 화면은 보존한다.
- **일반 규칙:** source-cut에서 살아 있는 모든 doubling과 첫 변화/terminal을 남긴다. ordinary 역할별 OR 후 역할 간 AND, 또는 명시 occurrence 집합의 AND를 구별한다. 첫 실패 뒤 유리한 음까지 건너뛰지 않으며, 새 fullpair guard와 frozen direct 축을 혼동하지 않는다.
- **공동 계정:** local/boundary/delayed를 선택한 동일 실제 witness(기존 또는 새 bundle)의 연결에서 다시 검사하고 clipped interval union을 사용한다. 경계 core/bass·endpoint·시간순 제시는 별도 근거이며 최종 화음/NCT/cadence로 승격하지 않는다.
- **구현·동결 검사:** 새 핵심/append-only 실행기를 동결했다. 신규 핵심50개/251.326초·실행기26개/53.135초, 관련 이전6suite202개/847.427초 OK다. 검사 프로세스와 fixture 실패/교정 이력은 정본에 구별하고, 한 번의 전체278검사로 표현하지 않는다. 전체Python 이번 재실행은 없으며 직전3,453개 기록을 보존한다.
- **실제 r1:** exit0/1,152.861403초, 5저장/0실패. 원108touching pair의335발생/381경로·10,274TTkernels·4,136roleoptions·319공동choices가22새bundle에서모두geometry가능이었다. 기존153bundle은그대로다. 가중conditional1,205/withheld50,165/unassessed106,794,580=전체106,845,950행과원origin/전체322·1,013및미실행317/998을보존했다. 최대10과문맥별최대정수합19를구별하며곡/정답률아니다.
- **독립 감사:** singlecold863.827799초+순차finite/public496.769870초+저장closure7.561262초=active1,368.158931초/전5문맥PASS. 실제저장전독립expected와전체5body/ref/digest일치. 공개1,518질의(양성1,205/무연결301/명시집합12)+lazy12요청의15assessment=1,533functionbodies/3,066exact profiles와같은witness의union/raw음가를검증했다.60negative반례는301control에포함되며중복합산하지않는다. Quartet공개receipt와Sonata저장산술의실제음표예시를구별한다.
- **출처·보호:** 4,509inputs/312currentproducer·schema/정확8생성파일17,176,998bytes의원creationSHA·7ancestor목록불변을확인했다. ROOT별도전수SHA검사도고유input+code4,511/artifact포함4,518개불일치0과보고서creationSHA일치다. source·Core·기존output/운영UI/구조/생성/Git은변경하지않았다.
- **최종 QA:** 새source/test4개·문서3개stricttext/4AST/123로컬링크·동결SHA/current312code/exact8output·보고서포함고유4,519creationSHA의오류/변경0,read-onlydiffcheck exit0이다. 기존별개tracked5파일LF→CRLF경고를보존했다. 독립문서검수와Quartet/Sonata실제참조도일치했다.
- **미승격·다음:** 명시 ordinary 가정의 실패는 음악 오류가 아니고, 미요구doubling·예외 전략은 남는다. 최종화성/NCT/key/cadence·confidence·학습/Gold·작곡승격없다. 다음큰단위는이근거를동일한완전진행의경쟁화성/기능설명에연결하는것이다.
- **정본:** [계약·일반 규칙·검증과 개발 기록](records/2026-10-02-delayed-resolution-obligations.md).

## HARM-DEV-20261002-18 — 화음 경계를 넘는 조건부 계류·선행음 근거

- **착수/일반 규칙:** 원래 동일 indexed group의 touching LEFT/RIGHT slots만 사용한다. 준비 attack과 involved full sound를 explicit pair envelope로 검사하며, 실제 지속과 동음 재타격을 분리한다. 필요한 모든 carry/resolve 연결은 새로운 하나의 실제 all-raw-lane completion에서 성립해야 한다.
- **설명량/보존:** 계류는 RIGHT, 선행음은 LEFT의 해당 비구성음 시간만 sound별 합집합으로 설명한다. raw membership/음가·원 후보/origin/key/진행/기능 분모·기존 bundle을 바꾸지 않는다. 지속 선행음에 가짜 self-link를 넣거나 무연결 설명량을 무조건 0으로 만들지 않는다.
- **구현 범위:** 별도 `factor_boundary_explanations`/append-only 실행기와 신규 검사. partition 사각형과 원 origin 가중치를 저장하여 모든 descriptor 쌍/백만 진행을 객체로 펼치지 않는다. 원자료/Core/parser·기존 output/운영 UI/구조/생성 미변경이다.
- **신규 검사/동결:** 핵심35개/240.404초·실행기25개/30.879초 각각 실패·오류0/exit0. 저장 predicate와 immutable 공개 질의의 자료형 불일치를 동결 전에 교정하고, 같은 양성·반례와 정확 profile 복구를 검증했다. source/test SHA와 중간 실패/fixture 수정 이력은 정본에 보존한다.
- **실제 r1:** exit0/1,320.989047초, 5저장/0실패. 원108touching group의529geometry/3,390partition/5,381관계, 새73complete+기존80bundle와188,180bundle별 관계(조건부3,666)를 저장했다. descriptor 쌍 incidence2,512,694는조건부200,868/보류2,235,884/unknown75,942이며곡/정답수아니다. 원22,969origin·전체진행/기능분모·전체322/1013및미실행317/998을보존했다. 최대사슬10이며각문맥최대의정수합19를전역최대로읽지않는다.
- **독립 실제 감사:** 전5문맥/1,284.497174초/exit0. 한성공coldload에서모든239source facts·529geometry/3,390partition/5,381관계/73새+80기존bundle/188,180같은bundle관계와원조합분모를대조했다. 공개87pair표본에서174exact profile/원음가합계복구,무연결18/설명양성77을확인했다. 지속선행음의무연결양성은정상이며곡/정답수아니다. 준비helper의초기인수누락으로완료전중단한별개시도는통과로세지않는다.
- **최종 회귀:** 동결후전체Python **3,453개/2,324.486초 OK/exit0**(직전3,393+신규60의한번의통합실행). 별도PowerShell전체계측2,328.172679초와개별신규검사·실제r1·감사시간을구별한다. 검사수는곡/음악정답률아니다.
- **보호/QA:** 보호4,499inputs/310producer·schema/정확8파일12,143,590bytes의생성SHA·목록불변과ROOT별도4,501고유path SHA 재검사를확인했다. 실제두원음표예시와동일origin의무연결대조는정본에기록했다. 무연결same-pair control의저장산술검사와실제실행87공개표본을혼동하지않는다. 최종7파일UTF8/NUL/U+FFFD/공백·4AST·3문서123로컬링크·현재310code목록과새/직전8source-test동결SHA·정확8출력검사오류0,read-onlydiffcheck exit0이다. 기존별개tracked파일5개의LF→CRLF경고는보존했다.
- **후속/미승격:** 지연 이끎음·7음의 여러 기능적 해결 의무와 local+boundary 같은-completion 공동 계정은 다음 단위다. 현재 conditional role shape는 확정 계류/선행음·secondary·조성·cadence·confidence·학습/Gold가 아니다.
- **정본:** [계약·일반 규칙·한도·검증 및 실제 실행 기록](records/2026-10-02-boundary-role-explanations.md).

## HARM-DEV-20261001-17 — 시간순 구성음 제시와 조건부 local NCT 연결

- **목적:** 직전 실제 literal profiles를 소비해 한 exact 구간 안의 구성음 제시와 경과·보조 음형을 같은 실제 성부 연결에서 대조한다. 원음표·membership·출처·경쟁 후보를 제거하지 않는다.
- **착수 결정:** 기존 9 completion에는 연속 두 연결의 triple이 없어 그것만 쓰면 NCT 양성이 0으로 강제된다. 새 typed local-chain completion을 별도 생성하고 기존 bundle은 그대로 보존한다. 각각 가능한 독립 witness를 합치지 않는다.
- **범위:** 새 core/append-only 실행기/신규 검사와 독립 화성 개발 기록을 작성한다. source·Core·기존 후보/결과·운영 화면은 미변경이다. 계류·선행음·지연 해결 및 최종 분산화음/NCT 확정은 이번 단위의 완료로 선언하지 않는다.
- **구현/실행:** 새 `factor_temporal_explanations`/`factor_temporal_explanation_trial` v0.1.0을 동결했다. owned prepare/build/validate/descriptor/origin 질의, 실제 member presentation·full-span local contour·middle-only 합집합 account·정확가중음가·whole 한도/0/unknown 및 append-only failure 분모를 구현했다. 실제r1 exit0/1,103.237084초/실패0, 5구간/15raw lanes의16,206제시·239geometry·839,026회원관계쌍→3,227공유관계·33,214조건부/805,812보류쌍,71새completion+9원bundle,49,420templates/347,226계정쌍/2,195weighted 계정이다. 원22,969origin·106,845,950function 분모와 전체322/1013·미실행317/998은 그대로다. 조건부쌍/계정수는음악정답이나confidence가아니다.
- **검사/발견:** 최종신규70개(핵심49/189.060초·실행기21/9.959초) 각각OK. 초기fixture 기대/폴더/삭제hash순서 문제 및 중단실행은 정본에 구별한다. 완전NCT/분산화음/계류·지연해결/최종화성·cadence·운영적용은 미승격이다. 실제C5–B♭4–A♭4의원note refs/같은bundle/가운데2quarter만설명하는사례도저장자료로확인했다.
- **최종 회귀:** 동결 후 전체Python **3,393개/1,926.964초 OK/exit0**. 직전3,323+신규70을이번한번의통합실행에서검사했으며이전분리실행과구별한다. 검사개수는음악정답률/작품수아니다.
- **독립 실제 검증:** **1,697.670381초/exit0/전5문맥 PASS**. 원여섯입력authentic coldreplay1회,전22,969origin/16,206제시·239geometry/839,026회원쌍→3,227관계/49,420template/347,226계정쌍/2,195weighted계정과71새bundle+9원bundle의body·음가·같은witness를독립대조했다. 공개prepare문맥별1회 후 새71+무연결5에서descriptor76/origin76=152질의·exact frozen profile 복구일치. 준비포함645.489683초는UI/lookup-onlylatency아니다. 독립sourceattack/소나타typed2quarter예시·동결closure도일치.
- **보호/QA/다음:** 4,489inputs/308producer·schema/정확8출력39,725,336bytes의생성SHA·전후목록/새report690ea921d9551a2fa7c88e9ff59ed1ff5db090cb68ae19317364f0d33ca7c8fb 불변. root별도SHA전수재검사도변경0. 7파일UTF8/NUL/U+FFFD/공백/AST·동결SHA와3문서117로컬파일링크·read-onlydiffcheck오류0;기존unrelated LF→CRLF경고보존. descriptor질의profile=null/origin만복구·query_work_budget=각rawlaneDP·71조건geometry와73rawcontour의구분을문서에정확히반영했다. 다음은경계NCT/선행·계류와지연해결의전체chain공동근거이며UI/생성/최종화성/accuracy승격아니다.
- **정본:** [계약·일반 규칙·한도·검증 및 실제 실행 기록](records/2026-10-01-temporal-and-local-nct-explanations.md).

## HARM-DEV-20261001-16 — 실제 음표·시간과 동일 성부 가정의 직접 해결 근거

- **목적/일반 규칙:** 형태 관계에 실제 note-time·source guard·베이스·이끎음/7음의 spelled motion을 연결한다. 필수 연결 전체가 하나의 실제 all-lane completion에서 동시에 가능한지 대조한다. 독립 witness 합산·PC만 같은 성부 대체·작품/마디 정답 조건·원후보 삭제가 없다. 관찰 membership과 화음/NCT 정답을 구별한다.
- **구현/동결:** 새 `factor_grounded_relations`/`factor_grounded_relation_trial` v0.1.0과 대응 신규 검사72개. 모든 exact descriptor를 materialize하고 동일 row/cell 값만 공유한다. 원 variant/span/ordered member/출처를 복구하며 original weighted universe·shape false/unknown/terminal을 보존한다. 공개 build/validate/prepare/query/동일 bundle assessment, 전체 inventory/endpoint/joint 한도·0/None·상위 보류와 append-only failure 분모 보호를 구현했다. 기존 parser/Core/순수 계산·scope/index/형태 관계 source는 미변경이다.
- **보완 이력:** exact geometry 0과 unknown, 상위 한도에 snapshot 없는 알려진 ID의 질의·불완전 inventory 완료 표시, ready/unknown 혼합의 baseline 없음, 실제 key 전달을 보완했다. 직접 motion의 boundary cell만 전달하되 전체 profile은 보존한다. 초기 핵심 검사 fixture 오류2+1건은 테스트만 교정했고 최종47개 통과다. source 동결 전 runner 중단16개를25개 통과로 집계하지 않으며 발견·수정·최종 실행은 정본에 구별한다.
- **검증:** 동결 core47개/115.083초, runner25개/392.891초 OK. 별도 기존211모듈/3,251회귀/1,254.530초 OK, oldsource hash 변경0. 합계3,323개가 각각 해당 실행에서 통과했지만 한 번의 통합3,323 실행이라고 하지 않는다. 코드 검사 수는 음악 정답률·악곡 수가 아니다.
- **실제 r1:** exit0/811.000201초/오류0. 원5문맥/15raw lanes/16old groups·전체322/1013·미실행317/998·22,969origin/113indexed groups 및1,068,810paths/5,344,050path×key/106,845,950function 분모 불변.16,206literal profiles(528,468row uses/249,951cell uses→1,374/9,770exact values),10,274direct kernels/2,668endpoint pairs를 계산했다.205planned joint 중4actual 대안,control5+required4=9actual bundles/20,000bundle×kernel대조다. 조건부직접15가중행=3kernel×5key, 직접전제보류51,355/미평가106,794,580. 마지막미평가를negative로바꾸지않는다.
- **독립 감사/보호:** 첫 저장 감사에서 실행 전후inputs4,479/currentcode·schema306/artifacts7+report=8파일15,153,439bytes의SHA·전체ancestor목록,모든원출처/239sourcefacts·시간·참조·가중분모·각actualbundle의qualified-link incidence·정수/None/저장5/실패0집계일치를확인했다. 두번째932.019410초에서전16,206profile/10,274endpointkernel·690qualifiededges·9actualgeometry/witness·20,000incidences와공개prepare전5문맥freshrebuild,전224기술tuple/4,380functionbody·지원15질의·동일bundle양성20/무연결음성15assessment가일치했다. 부모relationreport와기존결과불변. 첫읽기전용진단·기술replay를새저장결과나음악정답으로합산하지않는다.
- **문서/파일 QA:** 독립 개발 문서 검토에서 최고음이 없는profile 설명·overlap음가·전제를통과한joint대안의범위를교정했다. 7신규source/test/doc의strictUTF-8·NUL/U+FFFD·줄끝공백/AST·3문서118로컬링크오류0,read-onlygitdiffcheck exit0. 기존 unrelated LF→CRLF 경고는보존한다. source/Core/UI/전체cohort·정답률/향후구현완료의거짓승격없이구분했다.
- **범위/다음:** 원XML/IR/parser/운영화면/구조/생성/API/Git 미변경, 최종화성·secondary·조성·NCT/cadence·confidence/학습/Gold 미승격. 한순간 전체 구성음·member bass·touching endpoint 때문에 보류된 분산 제시·조건부NCT·지연 해결을 새 scope의 같은 completion 아래 연결하는 것이 다음 큰 단계다. source guard 완화·곡별 예외로 통과시키지 않는다.
- **정본:** [계약·실제 음표 사례·가중 분모·검사·보완·보호·다음 단계](records/2026-10-01-literal-and-direct-motion-grounding.md).

## HARM-DEV-20261001-15 — 분석 기반의 작곡·편곡 활용 기획 보존

- **요청:** 현재 분석 도구로 이전의 단조로운 편곡을 개선하고 모티프/프레이즈 하나에서 완성 악보를 만들 수 있는지 설명한 응답을, 나중의 작곡·편곡 개발 자료로 문서에 포함한다. 기존 XML 위치는 `K:/Music Analysis/MusicXML`이다.
- **기획:** XML 형식 모방이 아닌 정렬된 편곡 변환 사례, 화음 상대 슬롯·리듬·음역·보이싱의 반주 패턴, 구절별 역할/질감/밀도·전개 계획, 네 편성별 독립 실현과 모티프→완성곡의 단계·평가를 기존 생성 로드맵 §10에 추가했다. 피아노+바이올린+비올라+첼로는 피아노 사중주이며 현악 사중주와 구별한다.
- **관측/가설 구별:** 직전 읽기 전용 목록의12,055파일과 A Whole New World의79마디 기준/네편곡·71마디 다른판본은 실제 파일 관측으로 기록한다. 제목/마디 수만으로 선율 정렬·학습 적격을 확정하지 않는다. 이전 생성기의 단조로움 원인은 코드를 검사하지 않은 개발 가설이다.
- **순서/범위:** 검토된 화성 조건의8–16마디 피아노3안→다편성→모티프 작곡의 후속 계획이며 현재 화성 검증 작업을 폐기하지 않는다. 원자료/권한/IR/경쟁 가정 보존, 음악성·연주성의 악보/청취 검토, 독립 검증·XML 재파싱·제한 수정이 필요하다. 설명/문서화로 모델 학습·생성기·편곡 성능 검증 완료를 선언하지 않는다.
- **참고:** AccoMontage와 MeloForm의 원 논문 링크·참고 범위 및 우리 시스템에 미도입 상태를 보존했다. 코드/모델 다운로드·외부 API 전송·편곡 실행·운영 화면 변경·Git commit/push 없음.
- **문서 검증:** 3문서의 strict UTF-8·NUL/U+FFFD·줄끝 공백·로컬 링크125개와새§10 anchor 참조3개 오류0. 독립 내용 검토에서 앞 응답의 주요 요구/가설/계획/제한이 빠짐없이 보존됨을 확인했다. read-only git diff check exit0, 기존 unrelated LF→CRLF 경고는 보존. 화성 core/runner와최근r1 report SHA는 문서 수정 전후 불변이며 문서-only 변경이라 코드 회귀를 재실행하지 않았다.
- **정본:** [작곡·편곡 활용 기획 — 로드맵 §10](MUSICAL_SEMANTICS_AND_GENERATION_ROADMAP.md#composition-arrangement-application-plan).

## HARM-DEV-20261001-14 — 손실 없는 화음 형태·목표·조성 관계

- **목적/일반 규칙:** 모든 원후보와 false/unknown·terminal multiplicity를 유지하면서 exact 근음/ordered members/blocker type의 기본 형태 계산, target triad-core join 및 explicit key 투영을 공유한다. source×target×key나1억 function 행을 펼치거나 top-k로 줄이지 않는다. 형태 전제/실제membership·성부해결/음악정답을 구별한다.
- **구현/동결:** 새 `factor_function_relations`/`factor_function_relation_trial`·신규82검사를 추가했다. owned immutable session의 lookup은 같은 validated copy에서 만들며 currentproducer/숫자/전체한도/typedrefs를 검사한다. 입력은 build/prepare 동안 불변으로 직렬화하고 atomic transient ABA snapshot을 주장하지 않는다. 이전 frozen source·Core·parser/IR/XML·annotation/운영 계약은 변경하지 않는다.
- **검증/발견 문제:** 핵심41개/103.074초와2,920exact frozen body·weighted9states/keys/terminal 통과. 정적 감사에서 saved parent query/assessment의 closed field와 같은 actual bundle incidence 거짓 승격 검사를 강화했다. 첫 실행기41개/361.333초는 삭제파일 오류 종류 기대1개 ERROR였다. 실제 strictresolve의 FileNotFoundError를 해당 테스트만 정확히 검사하도록 고쳤고 다른 보호 요구를 완화하지 않았다. 첫 전체 회귀는 같은 구기대가 수집된 실행을 중단했으며 통과로 집계하지 않는다. 수정 후 실행기41개/356.912초, 동결 최종 전체Python3,251개/1,259.283초 OK/exit0다. 검사 수는 음악정답·작품 수가 아니다.
- **실제 r1:** exit0/596.111095초/오류0. 기존5문맥15raw lanes16old groups·전체322/1013·미실행317/998 유지. 22,969origin/221catalogues/113group(knownempty1)의530types/5,300kernels/125targetjoins/2,050keyprojections에서106,845,950기능형태 분모 전체를 정확 가중 집계했다. conditionalshape51,370/withheld106,794,580/terminal53,440,500, 별도실제function질의4,380이다. 이들은가정/key별조합수이지확정화음수·해결양성·정확도아니다. 새profile/endpoint/motion/samebundleassessment0.
- **독립 감사:** 첫344.674215초에전5문맥public source/scope/relation replay·전origin과4,380frozen body 일치. 두번째56.133944초에전체5,300kernel×5key/모든join·projection·가중집계/저장질의일치; 별도432.698292초의공개prepare/query4,380개전수재현통과. oldprofile/motion/provider/Cartesian entrypoints와prepared query의_function 호출금지아래통과했고모든입력·source·output SHA/목록불변. 기술표본전부보류와bulk conditionalshape51,370은서로다른분모다.
- **파일 QA:** 이번8파일 strict UTF-8·NUL/U+FFFD·줄끝공백/4문서128로컬링크 오류0, read-only git diff check exit0. 기존 unrelated LF→CRLF 경고는 보존했다. 최종4,464inputs/304code/12등록artifact·정확13outputs의SHA/목록과report SHA 불변.
- **보존/범위:** inputs4,464/currentcode·schema304/artifacts12+report13파일8,944,799bytes creationSHA/목록보호. oldstatus/공급미정/한도/0·unknown 분모를 유지하고 failed build/query보다 parentknown분모를 먼저 기록한다. confidence/selected/학습/gold/생성/운영화면·Git 적용 없음. 다음은 실제 note-time/source/조건부NCT·한 completion의 motion 공동 근거다.
- **정본:** [계약·분모·실제 실행·실패·보호·후속 개발 기록](records/2026-10-01-lossless-function-relations.md).

## HARM-DEV-20261001-13 — 손실 없는 진행 색인과 필요 시 공동 비교

- **목적/일반 규칙:** 모든 공급 후보의 출처·철자·ordered slot·조성 및 정확 product 분모를 보존하고 진행 객체 전체 생성을 피한다. 공유할 수 있는 의미 입력만 지연 descriptor로 만들며 후보 정체성·blocked/unknown을 합치거나 top-k로 삭제하지 않는다. 실제 bundle 아래 조건부 compatibility와 아직 미계산인 전체 universe를 구별한다.
- **구현/동결:** 별도 `factor_indexed_hypotheses`/`factor_indexed_trial`과 신규 검사 66개. opaque owned session에서 computed profile 공유와 frozen function/motion kernel의 질의별 재생, 완전 tuple 질의, 같은 실제 multi-lane bundle 아래 경쟁 후보 비교, 전체 resource hold와 append-only 출력·부모 SHA/목록/current producer guard를 구현했다. function/motion 자체의 bulk 공유는 후속 단계다. 이전 source/scope/hypothesis/result/Core/parser/운영 계약은 변경하지 않는다. prepare 호출은 immutable 입력으로 직렬화해야 하며 concurrent transient ABA의 원자적 snapshot을 보장하지 않는다.
- **코드/발견 문제:** core39개와 runner27개, 관련136개/98.561초·runner27개/186.132초 동결 검사 OK. 첫 전체 3,169개/790.857초는 기존 cadence 검사 1개 실패였다. content-ID 정렬의 index0을 최저음 성부로 가정한 오류이며 실제 내부 F4→E4가 빠져도 extreme witness는 남는다. 분석기 변경 없이 같은 fixture의 실제 G3 lane을 누락하도록 테스트 하나만 수정하고 원 assertion+관측 불변·정상 counterpart 검사 강화; cadence39개/10.846초·수정 검사12회/4.193초 통과. source를 유지한 **최종 전체 Python 3,169개/793.347초 OK**이며 실패 이력과 최종 통과를 구별한다. 음악 정답률/악곡 수가 아니다.
- **실제 r1/분모:** exit0/503.896700초/계산 오류0. 기존5문맥15raw lanes16group 및 전체322/1013·미실행317/998을 유지했다. 221공급 spans/22,969origin variants/16,206미계산공유 descriptors,113ready factorized groups(1empty0),1,068,810논리 paths/5,344,050path×key/106,845,950기능형태 분모를 저장했다. 실제224기술질의/4,380기능행/224같은control비교뿐이며 전 기능행보류·실제공동해결shape0이다. storage첫/끝 표본은 음악 ranking/전체 musical accuracy 검사가 아니다.
- **보호/독립 감사:** inputs4,449/current source·schema302·등록artifacts12+report=13files/10,782,444bytes, 기존 expanded report SHA 불변. 첫 전체 저장53.348초와 모든224query+224assessment 공개 fresh replay400.345725초에서 정확 body·봉인·단일control·입력 불변 확인. 두 번째 전체5문맥의 full IR/source/타이/음가·출처/분모와 공개validate_index·대표query/assessment도 일치했다(공개API268.807초). 실제239sounds/258slots/15raw lanes와4full ties/2linked-only 계보 보존. 차단 없음; 원공급기 전체 재제안·100만 진행 exhaustive 비교가 아니다. 화음/조성/NCT/cadence 확정·confidence·학습/gold/생성 승인·운영 화면·Git 적용 없음. 후속은 source shape/target 호환의 손실 없는 bulk 조건부 비교다.
- **문서 QA:** source/test/doc9파일 strict UTF-8·NUL/U+FFFD·공백 및4문서 상대링크128개 오류0. read-only git diff check 오류0, unrelated 기존LF→CRLF 알림은 보존. 독립 문서 검토에서 computed profile 공유와 질의별 function/motion 재생을 구별하고 control bundle은 문맥별1개라는 표현을 명확히 했다. 최종 보호SHA/목록도 불변이다.
- **정본:** [진행 색인·공유 계산·동일 bundle 비교 개발 기록](records/2026-10-01-indexed-hypothesis-universe.md).

## HARM-DEV-20261001-12 — 새 문맥 범위의 화음·조성·성부 공동 가정

- **목적/일반 규칙:** 앞뒤 근거를 기존 가정에 차용하지 않고 새 명시 envelope에서 literal/source/성부 geometry·화음·조성 가정을 만든다. 모든 lane·spelling·blocked/unknown·무연결 대안을 보존하며 같은 completion 아래 경쟁 가정을 비교한다.
- **구현/동결:** 별도 `fmes` scope, 새 후보/비교 계약과 append-only 실행기·신규 검사 80개를 구현했다. 기존 `mfco/fmview` provenance를 위장하거나 이전 source/schema를 변경하지 않는다. 각 실제 endpoint의 source-clock/철자/attack 검사를 요구하고 일반 bass member index와 보통 3/7화음 전위를 구별한다.
- **회귀/보완:** 전체 Python 3,103개/539.439초 OK. 첫 전체 실행은 기존 owned-snapshot 검사의 첫 관측이 항상 nonempty라는 순서 가정으로 IndexError 1개였다. 테스트만 실제 snapshot을 찾아 존재·alias·봉인·fresh 재현을 검사하게 고쳤다. source 수정 없이 독립 42개와 해당 검사 12회 반복도 통과했다. 발견/수정/재검증은 정본에 상세 기록한다.
- **실제 r1/분모:** exit 0/758.445261초/계산 오류 0. 원 5문맥/15raw lane/16group과 모든 보류를 유지했다. 새 221 supplier span/22,969 variants/113group/계획 1,068,810path를 저장했으나 110group은 전체 한도 보류다. 실제는 두 full-hold group의 232path/1,160path×key rows/11,600보류 기능 형태뿐이다. 별도 ready 1group은 path 수 0인 빈 group이다. 이 수는 전체 변화 진행 분석·음악 정답률이 아니다. 5 no-link bundle/공동 해결 shape 0, 원 cohort 미실행 317문맥/998lane 그대로다.
- **독립 감사/상태:** 보호 inputs 4,428/current source·schema 300/등록 artifacts 17+report=18파일 SHA·정확 목록 불변. 모든 5scope의 full-parent 공개 fresh replay, 원음·source/tie/반개구간과 모든 공급 origin·variant·path/동일 bundle 비교 분모를 두 감사에서 확인했다. 대표 Mozart 공개 scope/builder/evaluator fresh replay 191.353초도 통과했다. 원 Core/XML/운영 화면/구조/생성/Git 변경 없음; 최종 해석 선택·학습/Gold 미승격. 조합 materialization 병목의 공유형 비교를 다음 큰 과제로 삼는다.
- **정본:** [새 문맥의 공동 가정 개발 기록](records/2026-10-01-expanded-scope-joint-hypotheses.md).

## HARM-DEV-20261001-11 — 전후 관측 문맥과 조건부 종지 전제

- **목적/일반 규칙:** 관측 창 밖의 실제 지속·후속음을 별도 문맥 근거로 저장하고, 모든 화음/조성 가정 아래 최저·최고음의 구성음·전위·음도 및 동일 completion의 연결·full release/상대 음가를 대조한다. 원 target/path/key/bundle 확장, 같은 lane→진짜 성부 확정, sustain/장식→종지 긍정·부정 확정을 하지 않는다.
- **구현:** 새 `factor_context_observation`, `factor_cadence_prerequisites`, append-only `factor_context_prerequisite_trial`과 대응 검사. 기존 SOURCE/alignment 계약을 위장하지 않는 별도 typed refs, 물리 마디 clock group, 모든 동률/전후 관계, 전체 record/pair 예산 보류, 동일 bundle의 전체 path×key overlay를 저장한다. 기존 선택·보류·성부·원자료/Core/운영/학습 사용 정책을 보존한다.
- **동결 회귀:** 신규 83개(context 28/cadence 39/runner 16), 전체 Python 3,023개/433.215초 OK. 독립 재검사 신규 83개/86.267초도 통과했다. 검사 통과 수는 음악 정확도나 작품 수가 아니다.
- **실제 r1:** exit 0/200.447912초/오류 0. 원 5문맥/15raw lanes/16groups를 유지하고 전후 notated snapshots 258개·sound 239개·시간 관계 89개를 저장했다. 기존 9 bundle 아래 2,195개 path×key×bundle 레코드/6,310 boundary observations를 계산했으나 최종 cadence는 모두 미평가다. 이전 비교 분모·예산 보류·미실행 317문맥/998lanes·14family를 보존한다.
- **독립 저장 검증:** 보호 inputs 4,408개/current code·schema 297개와 등록 artifacts 16개의 생성 시점 SHA·정확 목록·참조 일치; report의 현재 SHA는 별도로 기록했다. 전후 문맥 5개 fresh replay와 모든 cadence seal/원 path·key·bundle 대조, quartet 대표 110개 bulk 및 단일 fresh replay/whole-pair hold 통과. 두 번째 독립 감사에서도 전체 5문맥의 source closure·full-IR 시간 이웃·반개구간 배치와 실제 A♭/F/A 사례가 일치했다. 예산은 계산 materialization 보류 기준이며 byte/RSS 상한이 아니다. 원 Core·XML·운영 화면·구조·생성·Git 변경 없음.
- **독립 정적 검토/보완:** 출력의 정확 파일 목록·삭제 파일 guard, 부모 comparison의 실제 seal/policy와 전체 계산 분모, ready graph와 원 lane snapshot 일치를 추가하고 관련 반례를 작성했다. 기존 큰 비교를 재실행하지 않는다.
- **문서/파일 검사:** 이번 10개 파일의 strict UTF-8·NUL/U+FFFD·줄 끝 공백과 네 문서의 상대 링크 114개 검사에서 오류 0. read-only `git diff --check`도 오류 0이며 untracked 파일은 위 별도 검사로 확인했다.
- **정본:** [전후 문맥·종지 전제 개발 기록](records/2026-10-01-context-and-cadence-prerequisites.md).

## HARM-DEV-20261001-10 — 계산 공유와 작품군별 화음 변화 문맥 검증

- **목적/일반 규칙:** 후보·음표·keys·근거·whole-pair/OR 대안은 줄이지 않고 동일 계산을 공유한다. 화성 라벨/양성 결과 없이 frozen family별 첫 change-ready context를 선택하며 collection round-robin/명시 family 예산으로 다양한 편성을 먼저 검사한다.
- **구현/범위:** comparator/resolver 개선 및 별도 `factor_functional_batch` 실행기를 구현하고 소스 동결. 전체322/1013 catalog와 selected/withheld/deferred/error/unexecuted를 구별하고 모든 selected groups/raw lane/source gate를 보존한다. subset의 batch_complete와 cohort_complete=false를 분리한다. 동결 후 전체 회귀·실제 확대 실행·두 독립 저장 감사·대표 fresh replay 완료.
- **자료 점검:** change-ready191group/117context/32package/19family. 기본5collection 범위5context/15lane/16group의prepared change8개 중4정적통과/4계산예산보류; 실제해결/양성은아직미평가. 첫부적격을유리한뒤사례로대체하지않는다.
- **실패/보완:** synthetic identity누락·hold-only fixture오류와 병행source편집 중 SHA검사실패를 기록했다. test adapter만추가하고productionidentity/부모hash계약을완화하지않음. catalog의obs/audit/target ref·ordered group 전체분모 guard를추가. 동결 후독립batch17개/29.684초OK·두독립검토차단없음.
- **성능 검증:** 비교색인만 바꾼첫68.047초는개선으로세지않음. fresh소유builder의이중복사도줄인최종cold56.219초는이전68.219초보다약17.6%짧으며138,613,184canonical bytes/47,895pairs/recordSHA동일·입력불변. 단일wall-clock비교이고전체엔진성능/음악정확도아님. comparison+resolver81개/24.880초OK. 계측cProfile174.125초와무계측시간은속도개선율로합산하지않음.
- **동결 회귀:** 전체Python2,940개/320.982초OK; 이번추가23개(batch17/comparison3/resolver3). source동시편집SHA실패미재현.
- **실제 r1:** exit0/666.117564초/오류0.19family33package322context1013lane 선언 중5family5package의5context15lane 실행, 나머지317/998·14family대기.16groups=비교완료7/새pair한도4/원path한도3/interpretation한도2 보존. function29650 중55조건부형태, resolution55180 중30조건부형태·나머지보류.30joint_possible branches/9comparisons/2195vectors/289740pairs. bundle아래30조건부충족/30해당bundle불충족/76870보류. shape는음악정답/작품수·최종key/NCT/cadence/G1승격아님.
- **독립 실제 감사:** 입력4379/currentcode·schema294/등록artifact23+report=24파일·전체parent목록·creationSHA불변. 모든5packet의literal IR/note-time/source/원groups/15lanestatus+gate 및전체nestedref/seal/76930assessmentrefs검사일치. geometry14ready/1held·source14consistent/1no-positive보존. conditionalfunction/resolution:quartet0/0·sonata10/10·mazurka20/0·Corelli0/0·Mozart25/20. 대표sonatachange:55 공개fresh43.113초/55paths×5keys=275overlays통과·caller/저장입력불변. reportSHA와검사범위/한계는상세기록에보존한다.
- **실제 음악 근거:** Sonata의감7이끎화음형태→C-minor와B4→C5, Mozart의G7형태→C-root와F5→E5를조건부검사했다. resolution30rows는두실제sound-motion을여러path/key/scale-form에서재사용한것이지30독립해결정답이아니다. Chopin은B-rootV/V7→E대안형태20개·지원해결0. unknown은기능unassessed이고PAC/HC의confirmed=false·전제미평가이며종지지지의부재확정이아님; 최종화음/종지미선택. 상세표에관계/가정/한계구별.
- **문서 검증:** 독립수치/참조검토차단없음·PAC/HC confirmed와미평가표현정정. 관련10파일문자/공백·4문서111상대링크/read-onlygitdiffcheck오류0. 기존별개tracked파일LF→CRLF알림은변경하지않음.
- **정본:** [공유 계산과 작품군별 batch 개발 기록](records/2026-10-01-functional-sharing-and-family-batch.md). UI/구조/생성/원자료/Core/Git 변경없음.

## HARM-DEV-20261001-09 — 같은 성부의 조성·Secondary·실제 해결과 종지 전제

- **목적/일반 규칙:** 명시 key/scale-form 가정 아래 ordinary V/vii 계열을 모두 보존하고 실제 register의 LT/7음 직접·same-pitch carry 해결과 canonical NCT를 하나의 completion bundle에서 공동 검사한다. 임시표→secondary 확정, path마다 유리한 witness 선택, OR unknown 중 성공 부분만 소비하는 방식은 금지한다.
- **연구용 구현 완료/동결:** 새 `factor_functional_overlay/resolution/comparison/trial` v0.1.0과 대응 tests. 조표와 key가정·기대 target과 실제 next segment·raw member와 qualified blocker·관찰 최저음과 구조적 bass·기보 박절과 지각 accent·도착 형태와 cadence를 분리한다. Core/parser/기존 분석·source/output·운영/UI/구조/Git/학습 승격 없음.
- **검토/보완:** 전체 path×key pair 예산을 별도로 사전 검사, blocked 후보 raw membership 보존, 전체 OR 질의 완료 때만 bundle 소비, key cue의 전체 마디 coverage/변화/모호성 보류. source는 동결 전 shared immutable bundle과 boundary의 반복 계산 비용을 개선한다. 원33파일322context1013lane·모든 candidate/원상태를 유지한다.
- **코드 검증:** 신규111개(19/39/36/17)/50.621초, 독립resolution+comparison75개/24.312초, 최종전체Python2,917개/304.438초/OK. group 예외의 분모 보존과 immutable prepared/public fresh 동등성 반례 포함. 테스트 수는 악곡수/음악정답률이 아니다.
- **실제 범위/보존:** 별도scoped pilot r1 124.033초/오류0. 전체19가족33package322context1013lane를 선언하되 실행은첫1context/4lane뿐; 나머지321context1009lane 미실행.3groups 중hold31+splitcontrol31을5key/readygraph3과비교하고384/744path 원한도보류유지.310overlays/4650function/10430resolution 모두보류,1bundle/47895쌍/0jointrequest. input4379/currentcode·schema293/test4/등록artifact5+report SHA·목록불변. source형태호환도실제target전제가없거나달라서미승인; 음악적양성/secondary향상/전체cohort완료아님.
- **성능/다음:** 실제group별단계측정comparison73.240초/publicfresh78.620초통과. 여전히대량path×key비교비용이커서전체cohort실행을아직하지않음. 후보/음표를축소하지않는공유평가와여러change문맥의기능/cadence전제검증이다음큰작업. 원주석·source blocker와generation/UI보류는유지한다.
- **최종 독립 감사:** 보호전체322/1013index·실행1/4·나머지321/1009,원IR/observation/audit/group/stages/gates·전체ref/seal·5artifact+report SHA·inventory 대조일치. no-link query계수4/4/49와endpoint3/3/6,310shared-registry/3boundary/11530motion slots/10430assessmentrefs 산술일치. 저장publicview0.734초/비교fresh68.219초통과,producer 재실행금지·입력불변. 관련12파일문자/공백·4문서109링크검사오류0. 음악정답검수/전체cohort승인아님.
- **상세·계약·예산·실패/정정·재현:** [기능과 실제 해결 공동 비교 개발 기록](records/2026-10-01-factor-conditioned-functional-resolution.md).

## HARM-DEV-20261001-08 — 같은 성부 가정의 화성·장식·반주 형태 공동 비교

- **목적/일반 규칙:** 모든 화음 path를 한 query-bound completion에서 비교하고, 개별 가능한 성부 연결을 합쳐 음악 설명으로 만들지 않는다. exact rational 음표-시간을 한 번만 집계한다. 원 membership·source clock/pitch·타이/attack·후보 blocker·상대 슬롯과 대안을 보존하며 unknown/unsupported를 nonmember/기각으로 바꾸지 않는다.
- **구현:** 별도 versioned `factor_musical_view/rules/joint/trial` v0.1.0 네 모듈과 대응 tests. 경과/보조·지속/재타격 선행·분산 구성음·지속 베이스의 조건부 형태, 준비된 하행 계류의 필수 전제 보류. OR/AND/NOT와 같은 branch 공동 가능성·동일 구성음 split control을 분리한다. 운영/Core/parser/기존 분석·원주석·권한/학습/생성/Git 미변경.
- **보완/검증:** declared duration과 span duration 분리, 실제 원철자 일치 guard, 전체 조합 수 확인 후 pair 예산 검사, 실제 내용/schema bytes에 묶인 intrinsic view 양성 memo. 잘못 재봉인한 부모 metadata·source/time/claimed seal 변조와 공개 fresh replay 반례를 포함한다. common25/rules21/joint32(78개/6.141초), runner17개/34.575초 통과. 초기 fixture/wrapper 오류와 병행 편집 중 전체 회귀1오류는 상세 기록에 보존했다. 소스 동결 후 최종Python2,806개/228.111초OK, 신규95개 포함; 이전fixture오류 미재현. 음악정답률/악곡수 아님.
- **실제 범위/상태:** r1 exit0/2,193.954초/오류0. 보호입력3,036개/currentcode·schema289/19작품군33파일322구간1,013lane 유지.942unit처리/geometry보류71 안에서754group×lane비교·4,222group보류; path한도2730/pair한도609/geometry267/철자path없음548/원plan없음68. no-plan28문맥과 원source gate926/40/31/16 보존. 첫lane 31holds+31controls pilot24.508→1.794초는 구조적 산술 검사이며 조건부NCT 양성/음악 정확도 향상 수치가 아니다.
- **실제 감사/한계:** 등록artifact1338+report exactSHA/inventory·기존IR/revision/source/원stages·geometry/parentgate 불변.실제비교170구간450unit,1110동일completion비교/57009accounts/674565sound-cellinstances/1671603delta와16789동일구성음control음가불변을독립대조. positive conditional account3520/62구간89unit은정답수가아님. 비교는754baseline+356clause,실제no-link785/positive-link325(추가31절nolink재사용). 대표3비교+2jointsolution freshreplay통과. same-path규칙쌍jointpossible1043/충돌1079,계류후보1468/반복assessment2815전부보류. 모든고정자료를전곡/holdout음악정답률로세지않음.
- **다음:** 조성/secondary/기능/cadence와 실제 성부 해결·박절·협화 전제를 하나의 기능으로 연결한다. 화음 자동승자/계류·분산반주 확정/새 악보뷰어/생성기 완료는 주장하지 않는다.
- **상세·계약·반례·실패/수정·재현:** [공동 음악 의미 계산 개발 기록](records/2026-10-01-factor-conditioned-musical-meaning.md).

## HARM-DEV-20261001-07 — 일반 문맥의 별도 출처 계약과 전체 성부 연결

- **목적/일반 규칙:** 기존322문맥을 가짜 SOURCE 없이 별도 `frozen_context_observation` v0.1.0/mfco_ 계약으로 연결한다. label-independent 창 선정과 주석/alignment 의존 cohort를 구별하며 old SOURCE schema/gate를 완화하지 않는다. 정확한 working IR/revision/8부모 content SHA와 literal all-part closure를 연결하고 전체 context-observed raw lane을 준비/보류 판정 전에 선언한다.
- **구현:** 새 observation module/schema/19tests와 `harmony_frozen_context_voice_trial` v0.1.0/29tests. 원 IR30/제한 measure candidate3의fresh replay 및 원5stage content 보존. 별도 `sounding_lineage_audit` v0.1.0/16tests와 `harmony_frozen_context_lineage_trial` v0.1.0/25tests도 전체 실행했다. SOURCE/화성/NCT/legacy열거 재실행·원annotation retarget·최종 역할/진행 선택 없음. 원output수정없음.
- **개발 보완:** 원stage exact projection+알려진 missing_evidence 추가를 분리했다. obsolete breadth producer를 재실행하지 않는 계약, 상위 명시적 input/opaque 진단/provenance 보호를 구별했다. 초기 fixture의 observations/폴더 누락6오류를 수정했다. 독립 검토 후 creation-time artifact SHA/정확 inventory·신규 직계 output 정책·입력 계획 copy와 변조 반례를 추가했다. 실제 r1 생성 전에 모두 보완했다.
- **첫 검증/실제 r1:** 신규48/전체Python2,670개155.312초OK. 19작품군33파일322관찰1,013단위,1914.840초exit0. geometry ready942/보류71(빈lane40·grace/point31),exactcontrol/completion2,826개,positive5,937/point288/factor3,554·최대123자리count. 기존ready243/보류79와stages 불변; 원보류문맥의geometryready239도화성승격아님.
- **최종 독립 보존/산술:** inputs1,344/code·schema283/등록artifacts1,338+report exact SHA·inventory 불변.322identity/1,610원stages/6,717literal slots/1,013분모와전체factor/query/completion·partition 대조일치. human/training/gold/generation0. 코드·산술·저장일치는음악정답률이아님.
- **중요한 기존 결함:** scoped sound5,396개중Chopin의한full chain이source합12q/span18q·gap6q. XML6notes는연속tie voice1로정상이나중간2notes가IR다른voice로배정돼sound중복. 신규계산이만든결함아님. 선택context216→220coverage4q는맞고full계보인증은실패하므로분리한다. 원XML/IR/parser를즉석수정하거나곡별예외를만들지않고일반audit/보류sidecar로기록했다.
- **source-clock 실제/추가 발견:** 동일322/1013의sidecarr1은794.265초exit0,계산오류0. guard926일치/40positive없음/31point시간미확인/16보류. 16은위음가불일치1+continuation/stop attack-origin15로15문맥6IR에노출. continuation18instances/12고유sounds(11stop/1continue)는full음가합·연속coverage가맞으므로XML/음가오류12건으로부르지않음. closure6033instances/5405고유sounds,activepositive5937clips전부일치·outsidepositive12미평가. 기존geometry942/71보존.
- **sidecar 보완/최종 검증:** slots[].core_event ownership, 완료baseline신뢰경계와literal사전1회/대형oldstagegzip미해제,fixture의rest선택·pitch필드/mock대상오류를보완했다. pointunknown/actualconflict혼합·selector/IR변조·creation-timeartifact반례포함. 추가41/이번신규89,전체Python2711개208.777초OK. inputs2708/currentcode·schema285/새artifacts325+report·모든oldparentsSHA/inventory와원geometry/status/probes를두독립감사로확인. complete=true는진단완료이고전체source-clockpass=false는예상된진단결과; 의미/학습/gold/generation0.
- **보존/다음:** old outputs/원자료/Core/parser/주석·rights/split/학습/운영뷰어·구조분석/API/Git 미변경. 별도versioned common view/factor-conditioned evaluator로passing/neighbor·held suspension/anticipation·분산/지속베이스 상대슬롯을동일completion에서공동비교한다. OR대안의AND평탄화·독립witness합치기·oldassignment위장금지. key/function/cadence미정은해당범위에남기고큰기능을계속진행한다.
- **상세·실제 저장 예·결함·접점·반례·재현:** [일반 문맥 연결 및 source-clock 검증](records/2026-10-01-frozen-context-voice-integration.md).

## HARM-DEV-20261001-06 — 손실 없는 성부 연결 제약과 정확 질의

- **목적/일반 규칙:** 전역 assignment를 열거하거나 유력한 몇 연결만 남기지 않고, 같은 raw lane의 정확한 release/attack마다 모든 부분 대응·무연결을 factor로 보존한다. 직접 required/forbidden edges의 공동 조건을 정확 계산한다. count는 confidence/음악적 지지표가 아니며 source/화성/NCT 판단은 별도다.
- **구현:** 새 `harmony_factorized_voice_paths.py` v0.1.0과 trial v0.1.1. closed-form/작은-side subset DP·resource abstention, fresh IR/질의 replay, graph/query-bound completion namespace와 대조용 legacy token. 원 positive sound/point/source/attack/tie를 보존하고 sampled grace·empty lane을 명시 보류한다. 기존 parser/Core/schema/진행·역할 연결 inventory는 변경하지 않는다.
- **보완 이력:** r1 비교 단계의 `legacy_observe` 재호출을 독립 검토에서 확인해 10/27 관찰·47/143 단위에서 Ctrl-C 중단. plan+47 packets/무report·index를 보존한다. 최종 실행기는 원 IR의 독립 literal 투영과 frozen old inventory만 읽는다. prior inventory 118개와 null 25개를 구별하며 미계산 자료를 채우지 않는다.
- **검증:** 신규 64(graph 39/runner 25)/12.379초, 최종 전체 Python 2,622개/127.874초/OK. 작은 완전 열거와 대조 및 열거 함수를 금지한 독립 33개 검사·runner control 통과. source/tie/attack·scope·재봉인·별도 질의 completion·예산·None/불일치·분모 보호 반례 포함. 테스트 수는 악곡 수/정답률이 아니다.
- **실제 r2:** 14 score files/27 observations/143 raw lanes, 161.570초/exit 0. geometry ready 130/hold 13, exact control 390개. 기존 조합 한도 63+15=78개를 손실 없이 표현; 기존 grace 보류 25개 중 geometry ready 17개도 원 grace/NCT 보류 유지. positive instances 2,687/points 33/factors 1,462, 최대 75자리 count. 실제 화성·역할 승인, 학습/Gold/생성, UI/API/Git 변화 없음.
- **보존/다음:** 입력 623/source·schema 280/새 등록 artifacts 145 SHA·목록,143원keys/status/scope·IR geometry·390query/witness·prior118/null25와r1부분48파일 불변을 두 독립 감사로 확인했다. 원음표 음가/연속tie·source 참조 일치; 음악정답 검수나 기존전역열거 재실행은 아니다.8변경파일문자/공백·4문서99상대링크/gitdiffcheck 통과. 다음은 가짜 SOURCE 없는 일반 observation origin 계약으로 기존 Beethoven/Mozart 322문맥을 연결하고, 패턴별 공동 제약을 조성·secondary·기능·cadence/반주 슬롯 해석에 사용한다. 새 completion을 old assignment 재고로 위장하지 않는다.
- **상세:** [수식·API·실제 보류·중단/보완·재현·확대 계약](records/2026-10-01-factorized-voice-constraints.md).

## HARM-DEV-20261001-05 — 경쟁 화성·조건부 비화성음과 역할 근거 연결

- **목적/일반 규칙:** 같은 원음표·rational context의 완전한 화성 진행과 단 하나의 성부 연결 가정에 literal/conditional role evidence를 연결한다. 원 membership은 보존하고 NCT로 구성음을 발명하거나 페달/분산 반주 blocker를 면제하지 않는다. 모든 origin·대안·source refs를 유지하며 최종 역할/화성 선택은 없다.
- **구현:** 새 `musical_progression_role_link.py`와 frozen trial, 대응 tests. 현재 source/IR hash와 written-pitch policy, exact raw lane/전체 lattice·pattern·assignment 재생, path/group lineage, sealed sidecar 및 fresh replay. 운영 Core/parser/schema/UI/구조 분석은 변경하지 않는다.
- **초기 검증/성능 문제:** v0.1.0 신규50(link35/runner15)/전체Python2,544검사94.267초OK. r1을15분이상진행했으나 첫eligible32-link unit이끝나지않아개발자가Ctrl-C중단(exit1).7literal/30보류packet/plan보존, 최종report없음. 입력172/code·schema278와목록은중간독립검사에서불변. 부분30개를전체143개완료로집계하지않음.
- **v0.1.1 구현/검증:** 후보/음표/예산을줄이지않고 immutable prepared context/proposal-level track·role 공유구현. 공개fresh validator와assignment별NCT/accounting유지. 실제schema SHA/private immutable snapshot/opaque handle의오염·재hash·교환반례,weak lifecycle,public/prepared all-assignment equality검사. 신규64(link49/runner15),전체Python2,558검사96.863초OK;별도19개fresh대조일치.
- **실제 r2:**14score files/27observations의143raw lane전부분모처리,984.677초exit0. 조건부연결2단위/40link instances·고유16track/16role. 보류141=lattice30/voice inventory68/grace25/early assignment15/link budget3. activeNCT0이며정확도향상이나40음악정답을주장하지않음. 입력172/code·schema278/output172 SHA·목록,27literal/143key/25grace·전체쌍/seal/raw음가독립대조일치. 실제첫link하나의cache-bypass public fresh15.354초통과;전체40fresh재실행은아님. r1부분결과도r2와동일하게보존.
- **범위/다음:** source Pedal선정편향/원후보blocker·실제양성부족을분리기록.16track모두일부blocked(전체blocked9/혼합7).40segment incidences의usable14/blocked26,박자코드18/무음8이며원악보박자오류의독립진단은아님. 원주석정답추론/학습/Gold/생성확정/Git/API전송/뷰어승격없음. 손실없는성부관계factorization 및가짜주석없는일반observation provenance로기존Beethoven/Mozart문맥을연결하고조성·secondary·기능·cadence/반주슬롯공동해석을계속한다.
- **상세:** [규칙·source 계약·실행이력·대조예제·성능원인과다음단계](records/2026-10-01-progression-role-link.md).

## HARM-DEV-20261001-04 — 지속·재타격·순차 음군과 가정별 역할 근거

- **목적/범위:** G1 좌표·원음표 보존 다음 단계. 편곡·작곡을 위한 literal 질감/역할 근거를 모든 raw lane에서 계산한다. 의미 성부/페달/분산 반주 확정이나 생성기·G1 완료는 아니다.
- **일반 규칙/구현:** 새 harmony assumption schema/module, role evidence schema/module, frozen trial v0.1.0. 원음·철자/옥타브·rational extent·타이 attack을 보존하고 실제 touching reattack/무음 틈/동시 group/순차 onset을 구별한다. 화성 가정별 member/nonmember/unknown과 도수를 분리. 서로 다른 member sets·nonmember·return anchor의 pedal 형태, 한 가정 아래 3+순차 공격/3+구성음의 broken-chord 형태를 대안과 보류로 저장. root를 label에서 추측하거나 source Pedal을 정답으로 베끼지 않는다.
- **실제 분모:** 기존 14 score files/27 observations(고유 score/target 25) 전부 처리. 14 source assumption tracks: usable segments 669/blocked copy·range 586, 진단 644(중복 포함). sounds 2,687/grace 7/episodes 1,981/reattack episodes 397/onset groups 1,748/rests 249 instances. anchored pedal 형태 4/unanchored 35/broken-chord 형태 16은 음악 정답/독립 작품 수가 아니다. human/training/gold/generation-ready 0.
- **검증/발견:** 신규 43(assumption13/role18/trial12), 전체 Python 2,494개/81.053초 OK. r1 exit0/243.747초 보존→미정 공격음을 nonmember와 분리하고 blocked missing-members=null로 보강한 r2 exit0/242.940초. 부모 입력172/code·schema276/새artifact43 SHA 및 27 seal/IR geometry/membership/집계 독립 대조. r1/r2 literal·track·shape 동일, 671 unknown attack instances의 표현 수정. 원 blocker 보존/초기 key default 방지/음가·attack/source계보 반례 포함.
- **사례/상태:** Coleridge-Taylor Op.57 No.1 E1/E2는 i→V43→viio43/VI 가정 아래 복귀 전 sound가 끝나 unanchored로 보존. source tag만으로 pedal 확정하지 않음. 원 Core/parser/주석·이전분석·구조 분석·피드백·rights/split/Git/API/운영 및 악보 화면 변경 없음.
- **다음:** 지속/분산 구성음+조건부 NCT+경쟁 진행을 연결하고 의미 성부/반주 슬롯 후보를 비교한다. Copy/range provenance 수입 확대와 Beethoven/Mozart의 기존 일반 검증 문맥 연결을 큰 기능으로 진행하며, 원주석 하나를 정답으로 평가하지 않는다.
- **상세:** [계약·규칙·실제 사례·전체 수치·보류·재현·한계](records/2026-10-01-musical-role-evidence.md). 인수인계 문서에 누적하지 않는다.

## HARM-DEV-20261001-03 — 원주석 좌표와 literal pattern 관찰

- **목적/범위:** 편곡·작곡을 위한 G1 첫 부분. SOURCE를 실제 악보의 시간 구간과 연결하고 앞뒤 음표/음가/철자/성부/tie를 재현 가능한 sidecar에 보존한다. 역할·분산반주·화음 상대 음도 확정/생성기/G1 완료 아님.
- **구현/일반 규칙:** 두schema와pattern0.1.0, 최종alignment/trial0.1.1. 명시적 Pedal 두 endpoint와 source beat partition을 사용하며 `[start,end)`를 적용. literal pitch token과 lane 의미는 미확정. pickup/불규칙/중복·dangling ID/rounded beat/생략된 endpoint는 보류. 모든part와 원 event를 유지하고 밖의 tie/chord/grace 연결은 context-only. 원 semantic SOURCE/BOUND/정식 Core를 변경하지 않는다.
- **실제:** 전208Pedal/91파일 분모 유지. sibling XML/MXL29파일 중 IR25/오류4.14악보파일의27source statements→27literal observations(고유score/span25). not-selected160/문법15/rounded1/meter미확인1/IR오류4. 미선정62폴더는remote.json 등만 있으며 전체DB에악보없음으로단정하지않음. 음악검수/training/gold/generation-ready0.
- **검증/발견:** 최종신규29/전체2,451검사70.290초OK.r2 exit0/172.750초. 독립input122/code271/artifact171 SHA·58byte snapshots·208identity·27projection/target/계보재계산.누적note2,867/rest249/tie164는중복instance. 첫마디자체signature조회수정과초기meterdefaultguard/환경기록보강. r1(178.150초/2,450tests)보존;두실행25전체IR/27event projection동일.Brahms3파일중복measureID/Reichardt1파일local-global오류는보류하며원자료보존.
- **상태/다음:** 연구용/offline, 화면/운영 적용 없음. 다음은명시적source identity의로컬score연결과지속/재타격/순차음군관찰→화성가정별역할·질감후보→chord-relative슬롯. 이전322문맥actualbackfill은아직아님. 기존조성/secondary/function/cadence개발계획도유지한다.
- **상세/실제음표/재현/제한:** [원주석 좌표와 패턴 관찰 개발 기록](records/2026-10-01-native-semantic-alignment-and-pattern-observations.md). 인수인계 문서에 누적하지 않는다.

## HARM-DEV-20261001-02 — 편곡·작곡을 위한 음악적 의미 원문과 기존 사례 보충 기반

- **목적/큰 기능:** 화성 분석은 중간 기능이며 최종 목적은 음악적 역할·반주·모티프 전개·앞뒤 배치의 이해와 생성이다. 전곡 피아노 솔로/듀엣·트리오·쿼텟을 최소 지향 범위, 관현악·장형식 스타일 작곡을 후속 목표로 구분했다. 기존 화성의 조성/secondary/function/cadence 경로는 유지한다.
- **구현:** 별도 musical semantic schema/contract0.1.0의8축 SOURCE/BOUND·출처/version/config·가정별rational span·검수·append-only revision/retry·축별coverage. intake/trial0.1.2와 독립audit0.1.0. 미정렬 설명을 음표 사실/전체covered로 승격하지 않고 old-case 보충 대기열을 만든다. Pattern realizer/생성기/음표 역할 자동 확정/뷰어 적용은 아직 아니다.
- **실제 범위:** RomanText1,293파일 중744파일의Note2,816/Form1,705/Pedal208=4,729physical statements 및전체byte snapshots 보존. 이전 고정19가족33package322문맥을 새계약not_assessed로 등록했다. 원주석·NCT·IR/status/rights/split 보존; 모든 역사 사례 backfill이 아니며 bundle hash를 IR hash로 발명하지 않는다.
- **실패/정정:** r1긴Windows경로쓰기실패(exit1)보존→짧은deterministic snapshot mapping. rg표시줄4,734집계는정정; 실제physical4,724+소문자note5=4,729. r2완료후defaultproducer/version한계발견→actual0.1.2/config SHA선언 r3. descriptor container/self-certified coverage/재봉인된낡은producer·문맥누락/중복snapshot·artifact inventory 반례를 차단했다. 이전실패결과를덮어쓰지않음.
- **검증:** 신규79(contract41/intake·trial27/audit8/workflow3), 전체Python2,422개64.492초OK. 최종r3 exit0/49.659초. 독립입력1,293+metadata3+code4/생성artifact1,301·원문4,729/legacy322/producer/config 대조일치. source alignment/human validation/training/gold0; 코드·저장검사를음악정답률로세지않는다.
- **보존/다음:** Core/정식schema/parser/음표/기존화성계산/정책·rights·split/gold·학습/API/Git/5173·8822/구조분석변경없음. 다음은 실제 악보 역할·질감 정렬과 재현 가능한 반주 패턴 계약을 준비하며, 공통 화성 비교의 조성·적용화음·기능·종지 연결을 계속한다.
- **상세/원문사례/재현/한계:** [음악적 의미·원문·기존 사례 개발 기록](records/2026-10-01-musical-semantics-and-backfill.md), [생성 목표 로드맵](MUSICAL_SEMANTICS_AND_GENERATION_ROADMAP.md). 인수인계 문서가 아닌 화성 개발 문서로 관리한다.

## HARM-DEV-20261001-01 — 여러 완전 화음 진행의 자동 제안 탐색과 동일 성부 가정 공동 비교

- **목적/큰 기능:** 공통 문맥 연결 다음 단계. 긴 유지와 여러 화음 분할을 자동 제안하고 동일한 전체 문맥·하나의 assignment에서 비교한다. 특정 악보 정답·첫 후보 자동승자·source 재정비 반복으로 전환하지 않는다.
- **구현:** `harmony_progression_search.py` v0.1.0, `harmony_progression_joint_comparison.py` v0.1.0, `harmony_progression_search_trial.py` v0.1.0 및 대응 tests. exact raw음가/optimistic NCT bound/보류노출을 분리한 `(끝점,segment수)` DP, 모든 origin·semantic 의미·검색제외 보존. 동일assignment의 원음가/NCT/관측bass·조건부전위/누락·생략/실제해결과 pairwise delta. 확정 화성·기능·cadence·confidence·최종path 없음.
- **실제 고정 실행:** 같은19가족33package322문맥.291문맥에서5,513완전진행/1,800,273전이,39,006진행×assignment평가/281,946쌍비교. joint275완전/8pairwise-only예산보류/8assignment예산보류/31기존보류. 기존ready243·관계한도48·baseline28·edge한도3 분모 유지. 음표/후보를 줄이거나 쉬운구간으로 교체하지 않음.
- **탐색 한계:** prefix근사286/출력한도81/segment한도45/철자미지원289문맥(중첩).153,588origin readings와111,904unspelled refs 보존. 전체 stored vocabulary경로를 출력한2문맥도 음악 해석 전체에 대해 exhaustive 아님. cap 제외는 음악적 기각이 아니라 근사 누락으로 기록.
- **핵심 차이:** 같은 구성음흐름1,385쌍의 raw/conditional음가차0. 추가경계와 membership증가47,809쌍은 정확도 향상으로 사용하지 않음. optimistic bound보다 실제조건부NCT가 작은평가4,064개/상한초과0; 쇼팽 q[177,182)의 potential3/4→실제0반례 저장. 직접해결지지20relation instances도최종secondary/정답20개아님.
- **계산 보완/반례:** 고정음형·목적rank·진행별missing/관측bass/관계 재사용, assignment의NCT/해결은재계산. 최대513MB문맥의 동일9,218reading/24진행/198,136전이를 유지한51.56→35.40초 부분smoke. runner는전체preflight검사후한문맥씩재로드/hash검증하여메모리집중을피함. count필드연결과즉시mutation검사를보강했고음악규칙/예산완화없음.
- **검증:** 신규51(search18/joint24/runner9),최종Python2,343개/76.290초OK. actualr1 exit0/695.874초;input1209/currentcode260/newartifact322hash·code목록변경0(목록중복은합산하지않음). 독립전체대조133.115초에서모든322identity·origin·path universe·5513coverage/39006account/281946delta·예산·정책·원분모일치. 코드/원음가검증을음악정답률로세지않음.
- **보존/다음:** 원XML/IR/revision/주석/정책/rights/split/gold/학습/외부API/Git/parser/schema/5173·8822/구조분석미변경. 다음은조성·적용화음·기능·종지및경계선택을공통근거위에연결. 음악검수와뷰어승격은후속.
- **상세·실제사례·제외·검증·재현:** [진행 탐색과 공동 비교](records/2026-10-01-progression-search-and-joint-comparison.md). output 이름은착수일의`2026-09-30-r1`을유지하고기록날짜는실제`2026-10-01`로구분.

## HARM-DEV-20260930-29 — 큰 기능 우선의 공통 화성 문맥 통합과 제한 마디 교정

- **요청/방향:** 세부 사례에 오래 머무르지 않고 큰 기능을 먼저 구현한다. 음표·시간·ID/평가 유출처럼 계산을 무효화하는 문제만 우선 교정하고 미지원 성부·장식·해석 충돌은 해당 판단에 보류한다. 메인 개발 문서에7개 기능 단계와 완료 기준을 정리했다.
- **구현:** `source_physical_measure_revision.py`, `harmony_context_bundle.py`, `harmony_context_integration_trial.py` 각v0.1.0. limited immutable revision과 공통edge/reading·모든part의raw membership음가·missing member·조건부NCT/전위·생략 경쟁·원관계 연결. 기존 단계 전체를 재사용하며 missing 진단과 공통 근거는 실제 새 계산. 자동 최적path/최종confidence/기능·cadence 확정 없음.
- **제한 교정:**33package 중 후보3/not_required30/blocked0. 중복5묶음의measureID10·label5·event참조49·localonset15 교정. direction extension참조8은 exactpointer/부모document에보존하고독립소비금지. 원globaltime/pitch/duration/notes/rests/sounds/tie/attack/배열·주석은보호. oldlocator26후보와결합하거나annotation자동재지정안함.
- **실제 통합:**19가족33package322구간전부.5,614edges/153,588spelledreadings·111,904unspelledrefs 보존. relation계획282,000개연결, 실제15,195query에missing/NCT진단계산, 기존생략origin2,500개연결. 기존ready243/보류79와모든stages동일. 조립322개는화성성공322개아님. 실제explicitpath요청0,전체엔진재실행/순위/정답률측정아님.
- **검증:**신규71(revision40/bundle18/runner13),전체Python2,292검사/75.061초통과. 실제r1처리466.097초exit0,592input/257code/358artifact·코드목록변화0. 세후보의허용필드복원시부모전체동일을validator외독립검사. fixture누락/반례구성방식정합화후회귀통과;운영규칙완화없음.
- **최종 독립 대조:**33package/322sample identity와전체input/code/artifact/contract SHA 일치. 원breadth의1,610stages전체JSON·배열·원보류·parent/working binding 불변.153,588reading/282,000계획/15,195진단/2,500생략link/explicitpath0집계일치. 차단문제0,추가source수정없음.
- **보존/다음:**원자료/부모/주석/manifest/정책/rights/split/gold/학습/외부API/Git/productionparser/schema/5173·8822/구조분석변화없음. 다음은완전한여러화음진행과성부가정을공동비교하고과병합/과분할을판단하는큰단계. 사용자의새해석선택은이번단계필수아님.
- **상세·보류·실제범위·재현:**[공통 문맥과 제한 교정 개발 기록](records/2026-09-30-context-integration-and-measure-revision.md).

## HARM-DEV-20260930-28 — 음표·쉼표 전체 순서와 physical measure 정체성 감사

- **목적/일반 규칙:** 직전 후보의 남은 동음 grace·중복 마디 문제를 전체 source lane의 순서/쉼표/chord marker와 물리적 마디 순서로 대조한다. printed number·legacy XPath·hash 정렬로 source occurrence를 선택하지 않으며 pinned replay와 독립 정체성 인증을 구별한다. 특정 악보 해석/라벨 하드코딩 없음.
- **구현:** `source_sequence_replay_audit.py`, `source_physical_measure_audit.py`, `source_sequence_replay_trial.py` 각v0.1.0. exact rational cursor·parent fingerprint/ID·written pitch/tie/grace/part/staff/voice/globaltime·전체 event partition을 검사하고, 마디 ID+seq index의 qualified alias를 진단으로만 저장한다. raw XML `<chord/>`는 notated group이지 harmonic chord가 아니다. right-edge grace를 전역 범위만으로 다음 마디에 이동시키지 않는다.
- **실제 전수 결과:** 기존19가족33package의44,607notes+4,775rests=49,382events 전부 재현. rejected/unchecked/unmatched0. 8,698partwise마디/3,432score-grid/10,318rawlanes/6,126chordmarkers/541grace 전수 대조. 이전 미매핑34개=order-only30+고유token4 모두 관측됐지만26후보/7보류는 불변. fresh mapper43개는 별도 분모로 유지한다.
- **발견된 기존 데이터 문제:** Beethoven01-1/02-3와MozartK280-3의X1/X2/X3가 정수 표시 번호로 합쳐져 중복measureID5묶음·참조49events·표시번호차5·localonset차15. globaltime/duration은 일치. split-source-staff normalization은 실제0, right-edgegrace55. source가 같은 printed number를 반복한 오류라고 단정하지 않는다.
- **보존/권한:** 이전41cases/125contexts·모든snapshot/annotationbinding·train27/dev6·internal research33 보존. 원Core/주석/production parser/schema/화성계산/gate/Gold/학습/rights/split/외부전송/Git/5173·8822화면/구조분석 변화 없음. 이번에는 새Core revision 후보도 만들지 않음.
- **반례/검증:** 신규85(replay31/physical37/runner17), 전체Python2,221테스트/49.634초통과. malformed·rest누락·rest뒤chord·ID교환·모호한voice·grid불일치·type/hash/filelist·분모보존·덮어쓰기반례 포함. r1실행167.690초exit0;331input/254code/33gzip와계약hash 불변. 두독립감사에서raw전체사건/lanes/grid/token/parentID·geometry·집계·기존context 모두 일치. music21wedge/dashes/pedal경고는 별도 기록하며 표정기호 전체 보존 인증으로 해석하지 않음.
- **상태/다음:** physical measure만의 새 immutable revision 계약으로 ID·label·local time을 제한 교정하고 oldannotation은 parentdocument에 남긴다. order-only30건은 미인증 유지. sourcevoice/lane 별도계약 후 미설명음/NCT·공동성부·경쟁화음/생략가설·실제지연양성으로 돌아간다. 현재 사용자의 음악 해석 선택은 필수 아님.
- **상세·실제사건ID·반례·재현:** [전체 sequence와 physical measure 진단](records/2026-09-30-source-sequence-and-physical-measures.md).

## HARM-DEV-20260930-27 — 불변 source locator 수정 후보와 성부 참조 감사

- **목적:** 이전 실제 사례의 grace/principal 원본 위치 오대응을 고치되 원 XML·부모 IR·기존 annotation과 분석을 덮어쓰지 않는다. 현재 mapper0.2.0는 이미 정확 duration/grace/tie를 구별하므로 production mapper 수정이 아니라 기존 데이터의 별도 revision 검증이다.
- **일반 규칙/구현:** `source_locator_revision.py`와 trial v0.1.1. raw XML을 독립 재파싱해 physical measure ordinal·part/staff·written pitch·정확 onset/duration·grace/tie·일대일 대응을 검사한다. source locator6필드, 관찰 notation8필드와 grace.slash만 허용하고 그 외 전체 JSON은 타입/배열 순서까지 보호한다. 결정론적인 새 document ID와 SHA/version/policy/JSON-pointer diff를 sidecar에 저장한다. 모호한 unison/grace 및 중복 measure ID는 보류한다.
- **실제 범위:** 기존 19가족33package/44,607음표 모두 revision을 시도.26개 후보/7개 보류. 후보31,365음표 exact, 잘못된 참조60개 교정;66source-ref 객체·325notation 객체 변경. 기존에 발견한 네 grace/principal 오대응은 모두 교정됐다. 객체 변경 수와 음악적 오류/정답 수는 다르다.
- **사례 보존:** 이전41samples/125contexts를 목록에 유지.111contexts를 새 후보로 대조해 모두 source fields 일치;14contexts는 보류 package의 부모 자료 그대로 유지. 재대조 문맥은6,426반복 instances/1,665고유 음표이며 기존 전체 문맥의 분모와 다르다. 모든 부모 annotation/화성 결과의 revision binding은 그대로 남는다.
- **성부 문제 구분:** 별도 current mapper 전수 진단은27complete/6incomplete,44,564대응/43미대응. 현재 revision의 physical measure 보호 gate와 분모가 다르다. 전체168logical lanes 중41개는 여러 XML voice를 포함한다. 기존 direct578query records의704선택 link instances는 모두 같은 명시 XML voice지만 실제 대위법 성부 인증은 아니다. `source_locator_voice_audit.py`가 원음표·새 locator·lane·기존 연결 근거를 별도 저장한다.
- **실패/보강:** r1은 보존. mapping 전 미검사 음표를 분리하고 source-score/snapshot SHA·중복 case/basename·malformed XML·부모 deep copy 보호를 보강했다. independent check 이후 blocked인 경우의 after-count 이중 집계 반례를 고쳐 별도 진단 수치로 유지한다. boolean/numeric 타입의 Python 동등성 허점도 canonical byte 비교로 차단했다. 현재 실제33개의 음악 geometry/교정 수치는 불변이다.
- **최종 검증:** 신규87(locator34/trial27/voice26), 전체Python2,136테스트/49.668초통과. 독립 감사에서26후보31,365음표의전체보호projection/schema/rawXML15항목,162artifact·37gzip·251입력 SHA 및sidecar/새ID/집계 일치. revision r2종료 후비사용voice모듈1개만예정된보강; voice r2는현재251코드·251입력·74artifact·계약 SHA일치. 코드검사/명시XML성부일치를화성정답이나대위법성부인증으로세지않음.
- **상태/다음:** production parser/Core schema/원자료/기존 manifest/rights/split/annotation retarget/gold/training/외부 전송/Git/5173·8822화면/구조 분석 변화 없음. 다음은 중복 physical measure ID·순서 grace·source voice/lane 계약을 별도로 검토하고, 미설명음/NCT·경쟁 화음/생략 가설의 판단 근거를 결합한다. 사용자 해석 선택은 현재 source 후보 생성에 필수 아님.
- **상세·최종 검증·재현:** [불변 수정 계약, 실제 결과, 보류, 성부 진단과 검증 이력](records/2026-09-30-source-locator-revision.md).

## HARM-DEV-20260930-26 — 실제 관계 witness·경쟁 해석·원악보 문맥 감사

- **목적/일반 규칙:** 확대 실행의 실제 연결 지지를 독립 검사하고, 부분 해결 witness와 전체 화음/NCT/실제성부/기능 확정을 분리한다. 특정 작품 정답 하드코딩·원주석 라벨 입력 없음.
- **구현:** `harmony_relation_case_audit.py` v0.1.2의 exact spelling/MIDI·후보origin·전체parentIR·localspan·explicitlane·touchingtime·criticalmotion·비분기/비병합·carry/arrival/coverage검사. `harmony_relation_case_trial.py` v0.1.2의 전체inventory/동일span경쟁/bytehash·정책·source snapshot/trace저장. Core/parser/기존gate변경없음.
- **정본 실제 실행:** r4에322survey/15,195query원상태보존. 지원은15가족21package41samples, 직접578/시간16재검사·실패0.125groupinstances/118고유span/552고유형태가설 및1,919same-span경쟁origins. 시간16은전부직접578에포함되고실제지연도착0(`not_seen`). 원지원은완전정답이아님.
- **진단:** direct578의sourceboundary미완비229/target474/source비구성음400/target224(중첩). 두boundary완비+양쪽비구성음없는14도정답아님. 미선택criticalsource가남는74는전부해결여부미측정. 기존unsupported164/blocked916보존.
- **재현 가능한 사례:**21개전체sourceMusicXML/fullfrozenIR을SHA그대로저장.125groupcontexts에앞뒤1마디·모든part·note/rest/complete tie IDs·기보·sourceXPath/원음가저장. clippedstandaloneIR이아님. source선정/shape/링크기준과원queryindex를보존하고gold/훈련/공개/외부전송승격없음.
- **Source 문제:** 고유1,820문맥음표의1,816일치/4불일치(반복6,934/6). ChopinBI126-3op41-1m79A4, MozartK280-1m47D5의grace/principal동음·동시점locator교환.3context는source_note_review_required. actualwitness/carry/positiveprofile영향0;XML손상·현재parser특정버그단정없음. 원XML/frozenIR미수정,source_note_fields_all_consistent=false로보존.
- **감사 반례·실패 기록:** positivefamily/pathmetadata/임의noncritical링크허점보강. parent밖음높이/lane이local을불필요하게막는범위문제보강. 구성음순서반례는set/subset으로기존engine과정합. r3파일감사의listalias는temporal16의direct저장링크중복을유발했으므로copyhelper+회귀검사추가후r4로전체재저장. r1/r2/r3보존,문서에정본/이력구분.
- **검증:** 신규63(감사40+runner23), 전체Python2,049검사/41.681초통과. 기존layoutwarning1건유지. r4 35.814초,817inputs/248sourcecodehash·목록/sourceIRsnapshot불변. 엔진/화면속도benchmark나음악정답률아님.
- **최종 독립 감사:**41gzip/21sourceXML·IRsnapshot/provenance·817inputs/248code·목록일치.2,497행의interval/boundaryprofile와양성criticalmotion/lane/touching/carry/nonbranching을독립재계산해오류0. 저장direct578links/temporal16paths는원query와정확히동일. r3→r4는저장중복제거외semantic변화0. source불일치4음표는양성endpoint/profile와교집합0.
- **상태/다음:** source의grace/principal동음·동시점매핑계약·version/provenance가우선. 이어미설명음·전체구성음·공동성부·경쟁quality/생략가설/실제지연양성. 관현악전음표실음/timeline/판본/박자/parts/정책검토는남음. 현재8822/운영5173/구조분석/외부API/Git변경없음. 현재사용자정답선택은필수아님.
- **상세:** [일반규칙·실제집계·경쟁사례·source문제·실패이력·재현명령](records/2026-09-30-relation-witness-case-audit.md).

## HARM-DEV-20260930-25 — 성부 geometry 재사용과 source 실음 변환 준비

- **목적/일반 규칙:** 더 많은 작품 검증을 위한 계산 비용 개선과 총보의 written/concert 혼합 방지. 후보/원음/보류/성부 순서를 줄이거나 특정 작품의 정답을 하드코딩하지 않는다.
- **구현:** 기존 voice 계산을 whole-score geometry 준비/exact-span 조회로 분리. private IR snapshot/hash·버전·Fraction 키·128span LRU·deep copy·입출력 변경 검사. geometry만 재사용하고 각 후보/assignment/직접·지연 해결/예산을 다시 검사. survey의 context-span 재사용16회부터 자동 활성화하고 explicit/off 경로 유지.
- **재실행:** 기존19가족33package의322구간에서 저장 continuous/contrast/lattice를 입력으로 relation/hold-change만 재계산.322/322 전체 JSON 동일, 이전15,195질의/66조건부 비교/모든 보류 유지.134survey활성·prepare134/miss517/hit14,520/eviction0.493inputs/246code 및 코드 목록 불변, 최종r2 exit0. 새로운322개 음악/독립정답/전체pipeline재실행 아님.
- **성능 반례/수정:** r1의117질의 표본은4.39배였으나6질의는2.52배 느려짐. 실패 성능과r1보존 후 geometry-only 비용 가드 추가. 같은 표본/반대순서2회 r2:13.712→3.496초(약3.92배)와0.183→0.163초(캐시꺼짐). relation 부분 검사이며 전체 엔진/화면 성능 일반화 없음.
- **총보 source prototype:** 공식MusicXML 부호·옥타브 규칙으로 원pitch에한번적용, 수동산식↔music21 exactstep/alter/octave/ps와 source child index/note ordinal 대조. 하이든104/1(7decl21pass11controls),브람스Op45/1(3decl9pass19controls),바흐Crucifixus(0decl0pass10controls).30pass/40선언없음보류. 전곡 실음/IR migration/화성자격 승인0.
- **입력 보강:** 독립 검토의 staff1/+1/01 중복scope·명시적빈alter/octave-change·중복transpose/pitch/staff 첫값선택 문제를v0.1.1에서보류하도록수정. 정상3총보의 source refs/변환결과는r1/r2동일. 입력5/코드5hash불변, 원문/원악보는보존. 전체XSD검증인증 아님.
- **검증:** 신규87(캐시37+trial11+source39), 전체Python1,986검사/36.266초 통과. source의독립24조건matrix도통과. 기존layoutwarning1건 유지. 코드검사수/프로브수/작품수/정확도는분리한다.
- **최종 독립 감사:** 전체322gzip byte/CRC/논리SHA·JSON·배열순서/null·sample/index/파일집합,493inputs/246codehash와목록·정책 통과. source5inputs/5code·10선언/70source locator·수식/철자·r1/r2결과 불변 통과. 감사집계의null처리 오류만 보강 후 전체완료했고 원계산결과를 바꾸지 않음. 차단문제0건.
- **상태/다음:** Core/schema/parser/정책/split/rights/gold/학습/원자료/UI/운영5173/구조분석/외부API변경없음. Git commit/push없음. 실제 관계 양성 후보·근접반례·보류 감사와 관현악score-order transpose timeline/판본/박자/파트매핑 확인이 다음이다.
- **상세:** [구현 계약·두 실행·성능 반례·총보 source·재현 명령](records/2026-09-30-geometry-cache-and-source-transposition.md).

## HARM-DEV-20260930-24 — 작품·편성 확대 실행과 관현악 준비 감사

- **요청/일반 규칙:** 가능한 많은 음악과 사람 화성 주석이 있는 큰 편성을 활용. 코드 테스트/후보 조합/악장/package/작품 가족/주석 좌표/정확도를 분리한다. 특정 악보 정답 하드코딩 없음.
- **구현:** `harmony_breadth_trial.py`의 전곡/lane별 균등 index 고정·33package실행·모든 budget보류·fullstage gzip저장·source/code/planhash·IR복사 불변 검사. 실제 continuous→contrast→lattice→relation→hold/change gate를 모두 사용하며 가짜ready로 우회하지 않음. 신규 관현악 준비 모듈은 source part/transpose·사람/자동 계보·rational grid·주석 좌표만 감사.
- **실제 실행:** 기존manifest exactscore+annotationhash와정책이맞는19가족33package(train27/dev6),전곡36,820관측창 중322창 완료. quartet24/Beethoven sonata54/Chopin102/Corelli80/Mozart62창. 끝단계ready243/보류79/실행오류0;전체part보존294창,관계질의15,195/조건부hold-change66. 음악적정답률아님. 기존pilot3package/3가족도포함하므로 추가30package/16가족. holdout7/미확인hashpair349/quarantine59이유 보존(중복가능). 무단split/rights/gold/학습 승격 없음.
- **실패/수정:** r1은6package/56checkpoint 중증6표시예외3으로중단·보존. `label()`의optionalroot를중앙fallback으로처리하여It/Ger/Fr/Ger43 후보/nullroot/원음표 보존. r1/r2선정sample객체모두동일. XML숫자·엄격boolean·종료code/계획hash검사도보강. orchestral r1의optionalMXLmedia-type누락을유일한안전rootfile처리로일반수정하고r2재감사.
- **큰 편성 결과:** 하이든104/1(18parts/449주석/408정확+41모호),브람스Op45/1(22XML→23parsedparts/394정확),바흐Crucifixus(10parts/124정확). 합계967주석/926정확좌표. 하이든294축약마디대295총보마디·2/2대4/4문제,Haydn7/Brahms3nonzero transpose선언으로화성사용보류. 세family모두unassigned exploratory,accuracy/gold0승격.
- **검증:** 신규 53개(실행 29 + rootless 표시 5 + 관현악 19), 전체 1,899개 테스트 통과(33.924초). 실제 2-worker 임시 실행의 2악보/4구간도 검사했다. 기존 layout warning 1건은 유지한다. r2 최종 exit 0, source/code/plan/IR 해시 변경 0건. 문서·신규 파일의 공백 검사와 `git diff --check` 통과(CRLF 경고만). 독립 artifact 재검사는 상세 기록 참조.
- **비용/다음:** quartet완료창209관계질의에서같은5context의전체성부prepare를209번반복함을profile로확인. 후보/원음/보류를줄이지않는immutableIR/정확span별geometry캐시부터설계. 다음관현악실행은concert정규화·판본/박자/파트매핑·정책검토후. 독립화성정답률/최종선택기는미완료.
- **상태:** Core/parser/원주석/기존manifest/운영5173/구조분석/화면/외부전송/AI학습/Git변경없음.
- **상세:** [전체설계·실패·실제총보·계보·재현·최종집계](records/2026-09-30-breadth-and-orchestral-readiness.md).

## HARM-DEV-20260930-23 — 동일 성부 가정의 유지/변화와 실제 검증 범위

- **구현:** 같은 rational cells/전체 원음/하나의 assignment로 hold와3구간 change를 대조. 보조음 contour의 모든 부분집합과 강제 베이스 유/무를 검사하고 실제 빈 assignment를 보존. 충돌 연결 합집합 금지/외부 sound 지속·후보 blocker·unknown 철자·미세음 보류. 구성음/조건부 NCT/미설명 음가를 분리하며 승자 선택 없음.
- **실제 검사:** 고정13표본/같은3악장 유지. K280의1분할에서64hold×8assignment×1기존 conditional path=512비교,512동일 화음 복제 검사,64빈 assignment 비교. 새로운512사례/정답이 아니다. F-major hold의 일부 보조음 설명과 change의 구성음 역할이 달라지며 미설명F3/다른 원음은 면제하지 않음.
- **범위 감사:** 직전1,804개는 코드 테스트 수. 최신13/이전184구간은3악장/3가족. 준비392package 중complete221/partial112/quarantine59,정렬 적격333;complete 베토벤·모차르트 소나타37악장. 사람 검수392개 모두unverified. 기존117경계의현단일변화평가적격0은정확도0%가아님.
- **확대 계획:** 기존3pilot가족 밖6가족/6악장 선정·hash고정. 베토벤01-2/03-2만 기존train/내부개발 실행 가능;K279-1/K282-1holdout보호,07-2/08-2정책미상보류. 실제새화성실행/독립gold/학습승격없음. 가족/scorehash/annotationhash split충돌0.
- **검증:** 신규42(비교23+범위감사19),전체1,846테스트/25.035초 통과. 기존layoutwarning1건. 입력·기존baseline 보존/음가·cell 일치/전체예산보류/실행JSON/hash/평가정책보존 검사. 최종13artifact/241code hashes와coverage424input/3code hashes 재대조,문서링크/대체문자/새파일whitespace검사 통과. 수치가 음악적 정확도라는 뜻은 아님.
- **정정:** r1초기결과 보존. 후보조합 수와실제group곱검사,context범위 포함assignmentID 보강 후r2최종replay. coverage r1도 초기·r2가현행. source/code hashes를각run-contract에고정.
- **상태/다음:** 코드/로컬진단 구현. Core/원주석/운영5173/구조 분석/악보 화면/외부전송/Git미변경. 내부가능추가2가족에서라벨없는관측계획과양성·근접반례검증부터확대.
- **상세:** [일반 규칙·실제 음표·작품 수·정책·재현·한계](records/2026-09-30-hold-change-and-validation-coverage.md).

## HARM-DEV-20260930-22 — 생략 가설과 실제 성부 움직임의 공동 대조

- **구현:** 라벨 없는 same-part/voice graph, held/touching 경계 움직임, 순차 복귀 contour와 강제 반복 베이스의 양립·분기/병합 검사. 모든 reading 쌍의 ordinary 해결 형태를 기록하고 조건부 세 구간에서 양쪽 critical 연결을 하나의 부분 대응으로 검사. 생략음을 witness로 만들거나 bass/NCT를 면제하지 않음.
- **검증:** 신규25/전체1,804테스트 통과. 고정13표본/반복 chain2개/분할13개 보존. 기존 적격 조합1개는 E→F 실제 경로 없음. contour11 instances 중 강제 베이스와 양립2/충돌9;2개도 서로 동시에 선택 불가. 독립 음악적 정확도 아님.
- **진단:** K280 위 성부 F5→E5→E♭5는 E→F 해결과 다름. A3→G3→A3, A3→B♭3→A3는 각기 관찰 가능한 대안이며 해당 세 화음 후보에서는 중간 음도 구성음. NCT 확정하지 않음.
- **수정:** 이명동음 방향 충돌 반례를 guard에 추가. r2의 순환 JSON witness는 순수 link constraint 객체로 수정; r3 전체 실행과 hash 재검사 완료. 실패/초기 출력 보존.
- **상태/다음:** 전체 유지/복수 화음의 모든 원음 설명과 다성 NCT·반음계 진행을 공동 assignment로 비교. strict/Core/원주석/운영/악보 화면 불변.
- **상세:** [일반 규칙·실제 음표·제약 충돌·검증·재현](records/2026-09-30-omission-voice-context.md).

## HARM-DEV-20260930-21 — 불완전3화음의 명시적5음 생략 가설

- **구현:** 관측 근음/3음과 가정된 완전5도 음을 분리, ordinary 장/단3화음에 한정. 기존 missing 목록/strict gate는 그대로. 증화음·7화음 등 관측상 같은 경쟁 reading 보존. 임의 원음 생성/NCT 면제/quality 확정 없음.
- **검증:** 신규13/전체1,779테스트 통과. 기존13분할 중K280 sample16 경계7/8의1분할만 가정 아래 가능(조합1),나머지12개 부족. strict clean 양성0 유지. 정확도 향상 아님.
- **진단:** F–A를 F–A–C의5음 생략으로 가정하는 진행이 계산 가능해짐. 같은 관측의 F augmented/7화음 대안은 삭제하지 않고 생략 모델 미지원으로 남김.
- **상태/다음:** 실제 성부·경쟁 quality/근음·전후 진행의 공동 검증. 화면/운영/Core/원주석/기존 gate 불변.
- **상세:** [가정과 관측 계약·반례·실제 결과·재현](records/2026-09-30-incomplete-triads.md).

## HARM-DEV-20260930-20 — 세 구간 복귀와 다른 성부 관측 비교

- **구현:** 관찰 반복 chain의 모든 두-cut 분할. 좌/중/우 membership 복귀 후보를 그룹으로 저장, 누락음/다른 비구성음/blocker를 엄격 분리. 전체 한 화음·계속 bass-member인 대안을 유지하며 승자/페달/NCT를 고르지 않음.
- **검증:** 신규11/전체1,766테스트 통과. 고정13표본의 반복 chain2개에서13분할 비교; 복귀 형태12/형태 없음1/엄격한 관측 양성0. 독립 정확도 아님.
- **진단:** K280 sample16의 경계7/8에서 앞 F–A(C미관측), 중간 E–G–B♭와 후보 밖 F3, 뒤 F–A–C–E♭를 확인. 앞5음 미관측을 별도 생략 가설로 다룰 필요. 다른 quality/구간 해석 유지.
- **상태/다음:** 불완전 화음 근거·경쟁 quality·전후 진행 및 공동 assignment 검증. 화면/운영/원자료/gate 불변.
- **상세:** [계약·반례·실제 관측·재현](records/2026-09-30-bass-return.md).

## HARM-DEV-20260930-19 — 반복 최저음과 같은 interval의 경쟁 후보

- **구현:** 같은 part/voice·철자·옥타브의 유일한 touching 재타격을 실제 최저음일 때 연결. 같은 구간의 모든 reading을 누락음/비구성음/blocker와 함께 비교하며 table 재사용. 페달/승자/NCT 면제 없음.
- **검증:** 신규12/전체1,755테스트 통과.13표본 중 기존 보류2개 유지. K280 sample16 F3 6회, sample32 F3 4회 관측.830관계가 겹치며 비구성 베이스 side instances565개에 같은 interval의 bass-member 대안 존재. 중복 가능한 후보별 수치로 정확도 아님.
- **실제 한계:** E–G–B♭ 후보는 F3 이외에도 설명 안 된 음이 남고, F–A–C 대안은 해당 구간 C가 없음. 확장 화음의 넓은 음 집합으로 비구성음 수만 줄인 것을 승리로 처리하지 않음.
- **다음/상태:** 세 구간 이상 복귀·상성부·경계 분할 경쟁과 공동 assignment 검증. 운영/화면/Core/원주석/기존 gate 불변.
- **상세:** [원리·반례·실제 비교·재현](records/2026-09-30-repeated-bass.md).

## HARM-DEV-20260930-18 — 미관측 구성음과 저장 NCT 근거 감사

- **구현:** 고정 후보 구간/부모 문맥에서 누락 pitch·역할·원음표 refs를 분리. 저장 NCT의 전 구간 requirement/assignment/보류/설명 음가를 검증. 실제 생략/NCT/페달로 승격하지 않음.
- **검증:** 신규13/전체1,743테스트 통과.1,722관계 감사/125관계 기존 미지원 유지.4,078 누락 instances 중 구간 밖 부모 관측1,494/부모 미관측2,584. NCT 호환550/조건 충돌4,965/바깥 문맥 필요803. 모두 중복 가능한 후보별 수치이며 정답 수 아님.
- **진단:** K280 sample16의 양쪽 구성음 완전 관측76관계에서도 반복 F3가 후보 밖에 남음.76개 모두 출발 비구성음 중 전체 음가를 설명하지 못하는 음이 있음. 페달 가능성·경쟁 화음·과도한 병합을 함께 비교해야 함.
- **상태:** gate/원자료/운영/화면 불변. SHA-256 및 전체 테스트 확인. 사용자 피드백 없이 근거 진단 가능; 음악적 확정은 미완료.
- **상세:** [계약·반례·재현·실제 후속 대상](records/2026-09-30-missing-evidence.md).

## HARM-DEV-20260930-17 — 분산 구성음·지연 해결의 시간 경로

- **일반 규칙:** 시간차 구성음 관측, 지속/동음 재타격 뒤 이끎음·7음의 순차 해결을 별도 가능성으로 연결. 쉼 건너뛰기/서로 다른 성부의 임의 연결/새 비구성음 면제/음표 삭제 금지. 기존 직접 판정 보존.
- **구현:** `harmony_distributed_resolution.py`와 후보 관계 실행기의 opt-in `--temporal`. 가능한 공동 경로를 검증하지만 최적 성부/화음/조성을 선택하지 않음.
- **검증:** 신규18/전체1,730테스트 통과. 고정13표본에서1,847관계 검사,8,699관계 한도 보류 유지. 시간 전제 보류1,722/장식 timing 미지원120/기존 blocker5. 실제 양성0, 합성 양성·반례 통과. 기존 직접 요약 불변 및 모든 결과 artifact hash 확인.
- **진단 수정:** 동시성만 문제라고 볼 수 없음. 시간 전체로 봐도 구성음 미관측1,646개, 출발 비구성음 설명 부족1,542개(중복1,466). 범위 절단·생략 화음·잘못된 후보를 구별하고 NCT 근거를 독립 연결해야 함.
- **상태:** 실험 계층 유지. 화면/운영/Core/원주석 미변경. 사용자에게 실제 정확도 향상을 주장하지 않음.
- **상세:** [규칙·반례·실제 진단·재현](records/2026-09-30-distributed-resolution.md).

## HARM-DEV-20260930-16 — 임시 경로 밖의 후보 관계 검사

- **구현:** 모든 touching interval/모든 철자 ordinary-family 후보 관계를 계획해 원후보 출처를 유지한다. 더 이상 첫 reading 기술 path의 존재를 전제하지 않음. 직접 관계만 local scope로 평가하며 전체 화성 해석은 선택하지 않음.
- **검증:** 신규8/전체1,712테스트.13표본:11처리(7개는 대상 관계0),1 baseline 보류,1개8,699관계 한도 보류. 검사1,847개는 동시음 전제1,698/직접 연결 불가24/0음가 timing 미지원120/기존 blocker5. 직접 해결 양성0.
- **수정:** r1은0음가 event에서 중단; r2는 해당 범위를 미지원으로 기록. 원 IR의 B♭4/C5/D5(quarter28)3개 grace임을 확인했고 삭제/원자료 수정하지 않음. 실패 출력 보존.
- **다음:** 분산형·지연 도착의 시간 지지를 엄격한 반례와 함께 확장, 큰 후보 집합의 중복 계산 및 grace timing 별도 처리. 운영/화면 미변경.
- **상세:** [전체 계획·결과·범위·실행](records/2026-09-30-candidate-relations.md).

## HARM-DEV-20260930-15 — 해결 관계별 제약 검사

- **구현:** 같은 part/voice의 touching 음표 후보 graph는 라벨 없이 생성. 직접 해결의 필요한 링크들을 분기/병합 없이 함께 선택할 수 있는지 질의하며, 한 개의 증명용 대응을 기존 판정기로 재검증. 해당 대응은 최적/실제 성부 아님.
- **검증:** 신규11/전체1,704테스트. 소규모 양성·반례에서 완전 열거 결과와 일치, merge/branch 충돌·예산 보류·입력 불변 검사. 기존5기술 경로 모두 graph 처리(97링크),질의3개: 비인접2/동시음 전제 부족1. 직접 해결 양성 미완료.
- **한계:** 전체 경로 공동 최적화/지연 해결이 아니라 관계별 직접 해결 존재성만 계산. 질의별 증명 대응을 하나의 전곡 해석으로 합치지 않음. 실제 first-reading probe의 후보 범위 제한이 남음.
- **다음:** 일반 규칙으로 후보 관계 검사 범위를 확대하여 실제 양성/반례를 마련하고 지연 도착 전제를 검증. 화면/운영/Core/주석 미변경.
- **상세:** [계약·비교·실행·수치·한계](records/2026-09-30-resolution-constraints.md).

## HARM-DEV-20260930-14 — 다성 표기의 부분 대응과 조합 한도

- **구현:** 기존 lane별 완전 부분 대응 열거를 재사용해 여러 lane의 대응 가설을 결합. 무연결/고립음 보존, branch/merge 금지, 각 가설별 해결 계산. 최근접 pitch나 화성 정답으로 연결 선택하지 않음.
- **검증:** 신규8/전체1,693테스트. 합성4음→4음209대응 모두 검사. 실제5표본 중1개8대응 완료/4개 한도 보류. 검사 완료 표본의 직접 해결 지지0개. 실제 양성 검증 아님.
- **한계:** 표본별 가능한 조합1,536/882/14,306,656/157,216/8. 전체256 및 lane별1,024 한도는 음 삭제/정답 선택을 막는 연구용 보류 장치이며 최종 성능 설계가 아님.
- **다음:** 성부별 후보·관계별 제약을 분리한 계산으로 필요한 해결 조합을 검증. 무제한 조합 전개/한도 상향을 기본 해법으로 삼지 않음. 운영/화면 미변경.
- **상세:** [원리·수치·실패 범위·재현](records/2026-09-30-progression-polyphony.md).

## HARM-DEV-20260930-13 — 명시적 여러 성부의 해결 근거

- **구현:** 선택적 원 IR 입력을 hash/event 일치 검사 후 사용. 모든 명시적 part/voice의 유일·연속 연결을 별도 resolution 근거로 선택한다. sampled 성부와 합집합으로 섞거나 NCT assignment를 덮어쓰지 않음.
- **검증:** 신규8/전체1,685테스트. 실제5기술 경로에서17연결, 형태 관계3개는 여전히 shape-only. 다성 source voice42 event 관측/문맥 밖 후속8 event 보류(표본 간 중복 가능). 실제 직접 해결 지지0개; 정확도 향상 검증 아님.
- **수정:** 합성 악보의 source voice 번호와 수동 연결 불일치를 발견해 명시적 성부 fixture를 정정. 알고리즘 조건 완화 아님.
- **상태/다음:** 다성 표기 내부 성부 대응/지연 도착의 보수적 대안과 실제 해결 양성 사례 필요. UI/운영/주석/Core 미변경.
- **상세:** [실제 수치·계약·한계·재현](records/2026-09-30-progression-multivoice.md).

## HARM-DEV-20260930-12 — 다중 진행의 목표 화음과 해결 근거

- **일반 규칙:** 철자로 일치하는 V/V7/vii/vii7/vii_half7 형태 관계, 실제 준비된 후보의 말단 구성음, 목표의 첫 근음/3음, 선택된 성부 연결의 이끎음/7음 해결을 분리한다. 조성 없이 secondary/primary를 확정하지 않음.
- **구현:** `harmony_progression_resolution.py`, 기존 재실행기의 선택적 `--resolution`. 이후 목표 후보도 기록하지만 지연/중간 경유는 직접 해결로 자동 승격하지 않음.
- **검증:** 신규15/전체1,677테스트. 저장된5기술 경로에서 형태 관계3개/직접 해결 지지0개. 나머지7표본 적격 저장 path 없음,1 baseline 보류.0개를 정확도나 음악적 부재로 해석하지 않음.
- **상태/다음:** 기능/조성/종지 확정 및 운영/화면 반영 없음. sampled 성부 연결의 제한을 점검하고 실제 해결 양성·반례 검증을 우선한다.
- **상세:** [계약·재현·검사·한계](records/2026-09-30-progression-resolution.md).

## HARM-DEV-20260930-11 — 근음·전위와 지속 베이스 역할

- **구현:** 공급기별 철자 대안의 근음을 compact reading에 보존(0.2.0). 별도 bass 모듈에서 실제 최저음/근음 관계에 따른 조건부 전위, 비구성음 베이스 대안, 지속음의 member→nonmember→member 형태를 기록한다. 증6 근음을 발명하거나 표시 라벨에서 추출하지 않음.
- **검증:** 신규13/전체1,662테스트; 최종 상태 문구 변경 후 진행 관련38테스트 재통과. 새13표본 재계산12 ready/1보류,5기술 path에서15셀 조건부 전위/8셀 비구성음 베이스 보류. 실제 지속 베이스 형태0, 합성 양성/반례 검사 존재. 음악적 정확도 아님.
- **한계:** 단일 지속 sound의 최저음 형태만 지원. 재타격 페달·상성부/내성 페달·페달의 기능 확정 및 순위는 남음. 운영/화면/Core/원주석 미변경.
- **다음:** 기능·목표화음 해결 관계 연결 및 페달 양성/반례 실제 경로 검증. 단순 베이스 관측으로 승격하지 않음.
- **상세:** [규칙·계약·재현·제외·한계](records/2026-09-30-progression-bass.md).

## HARM-DEV-20260930-10 — 진행별 관찰 근거 벡터

- **규칙:** 구성음 설명 증가를 정확도 증가로 보지 않는다. 실제 최저음 변화와 전위/기능 변화, 누적 구성음 완성과 분산화음 확정을 구분한다.
- **구현:** 다중 path의 동일 평가 범위에 시간별 membership/실제 최저음·후보 누락·경계 양쪽 구별음/지속음 연결. 구성음/NCT 시간 차이와 경계 수 차이를 분리하며 우승 가설은 고르지 않음.
- **검증:** 신규10/전체1,649테스트. 저장된13표본 중5개에서8기술 실험(5벡터/3동일 구성음 비교).7개는 저장된 적격 path 없음,1개 baseline 보류. 제외/원입력 hash 보존. 베토벤 표본의 이번 경로 실험은0개이며 검증 성공으로 세지 않음.
- **상태/다음:** 전위는 compact 후보에 근음/구조적 베이스 역할 계약이 없어 보류. 그 계약과 페달 대안을 먼저 연결한 뒤 기능·해결/순위 검증. UI/운영/원자료 미변경.
- **상세:** [계산·반례·결과·한계](records/2026-09-30-progression-evidence.md).

## HARM-DEV-20260930-09 — 다중 진행 문맥과 상세 추론 규칙

- **일반 규칙:** 경계 하나의 유지/분할을 넘어, 동일 앞뒤 문맥에서 여러 화음을 연결한다. 관찰 문맥과 평가 범위를 분리하며 외부 음표에 의존하는 가정을 명시한다.
- **구현:** 전체 연속 구간 후보 격자, 다중 path 검사, 문맥 NCT와 부분 범위 계산 prototype. 자동 순위/최종 선택은 없음. 상세 규칙12개 계열의 근거·반례·보류·AI 선택적 인터페이스를 설계했다.
- **검증:** 신규15/전체1,639테스트. 고정13 pilot 중12 ready/1 baseline 보류,227구간·6,689후보 reading·31음형. 동일 구성음 분할 불변3건/음가 보존5건 통과. 후보 개수와 계약 검사는 정확도 아님.
- **수정 이력:** r1 출력 폴더 생성 오류, r2 이전 단계 placeholder를 보류로 집계한 문제를 보존. r3는 hash가 일치하는 원 baseline을 복구해 계산.
- **상태/다음:** 로컬 prototype만 적용. UI/운영/Core/원주석 미변경. 근거 벡터·페달·기능 해결·후보 누락과 과분할을 점검한 뒤 순위 결정. 외부 AI 호출 없음.
- **상세:** [실행·수치·한계](records/2026-09-30-progression-context.md), [상세 규칙 계약](HARMONY_REASONING_RULES.md).

## HARM-DEV-20260930-08 — 원주석을 이용한 평가 적합성 검사

- **구현:** 고정117경계에 원주석 coverage/의미 분류/후보대조 진단 연결. 주석은 사후 진단에만 사용. 시간축과 printed number 변경을 구별하고 old event ID는 재사용하지 않음.
- **결과:**105개는 한쪽 구간 내부 주석 변화,12개는 페달 참조 변환 미지원. 현1화음/2화음 비교로 실제 수치 평가 가능한 경계0개. 정답률0%가 아니며 실제 양성·반례 검증 완료로 보고하지 않음.
- **검증:**신규17/전체1,624테스트, 원입력/주석 hash 보존. 중간r1/r2 실행 문제와r3~r5 결과 모두 보존. 화면은 원주석 진행·제외 사유·전체 악보 링크 제공.
- **결정/다음:** 관찰 문맥과 판단 구간 분리, label-blind 다중 경계 후보 진행 비교, 페달 역할 별도 참조 지원. 운영 미변경.
- **상세:** [실패 원인·실제 사례·실행·다음 설계](records/2026-09-30-reference-boundary-audit.md).

## HARM-DEV-20260930-07 — 동일 문맥의 화음 유지·분할 비교

- **문제/일반 규칙:** 유지와 분할이 서로 다른 local/경계 문맥의 이점을 받지 않도록 동일 범위·성부 연결·공통 음형 규칙에서 재계산한다. 같은 구성음 집합이면 경계 삽입 전후 설명이 같아야 한다.
- **구현:** 공통 catalog/비교 모듈·고정 replay·전체 악보 패널. 이전 계산과 원자료는 보존하고 새 결과를 분리했다. 계류 형태는 계속 보류한다.
- **검증:**184표본/117경계, 공통 형태207개, 대표 동일 구성음 비교2,194개 통과. 신규14/전체1,607테스트. 형태 개수는 이전 후보 필터 적용 수치와 직접 비교하지 않으며 정답률이 아니다.
- **화면/상태:** K281 sample16에서 E♭ major 유지와 같은 화음으로 분할한 설명 일치 확인. 운영5173·Core·구조 분석은 미변경.
- **다음:** 공정한 설명 비교를 사용한 실제 화음 유지/교체의 독립 양성·반례 평가.
- **상세:** [계약·수치·실행·악보·한계](records/2026-09-30-shared-context.md).

## HARM-DEV-20260930-06 — 시간순 장식 후보와 보류·미설명 구간

- **일반 규칙:** 동일 시간 셀/성부 연결에서 장식 설명을 연결하되 계류 보류는 별도 bucket에 둔다. local 조건부 근거와 보류 근거를 함께 보존하고 확정 NCT로 승격하지 않는다.
- **구현:** `harmony_ornament_timeline.py`·replay·전체 악보 UI. 음표별 근거 refs, note-time 보존, 셀별 wall-time. 기존 결과/Core/원주석/운영5173 미변경.
- **검증:**184표본/117경계/보류21패턴 보존, 신규8/전체1,593테스트. K281 sample16의1½quarter가 새 대조에서 보류로 분리되고 무연결이면 미설명으로 돌아감. Python/UI 일치 확인. 정답률 개선 수치 아님.
- **다음:** 유지/분할의 문맥 비대칭을 통제하고 실제 양성·반례를 검증한 뒤 후보 선택 검토.
- **상세:** [계약·사례·실행·검증·한계](records/2026-09-30-ornament-timeline.md).

## HARM-DEV-20260930-05 — 분산화음과 화성 교체의 시간 순서 대조

- **문제/일반 규칙:** 구간 전체의 구성음 집합만으로 같은 화음의 분산형을 확정하지 않는다. 정확한 시간순 구성음/혼합/비구성음/쉼/미정, 실제 최저음, 양쪽 고유 구성음·지속음·동일 성부 연결을 대조한다.
- **구현:** `harmony_temporal_coherence.py`와 replay 실행기, 전체 악보 UI. 기존 replay 권한/hash/원필드 검사를 선택적 stage로 재사용. 기존 Core·후보·설명량·계류 보류 불변.
- **검사:**184표본/117경계/14,095profile. 누적 구성음 완성2,944중2,784에 비구성음 동반. 독립 화음 수·오류 수·정답률 아님. 신규20/전체1,585테스트 통과.
- **사례:** K281 sample16의 E♭major는 시작에 전 구성음이 있어도 뒤에는 혼합/비구성음 구간이 나타남. Dmajor의 F♯ 미관측은 그대로. 지속 B♭의 경계 전후 역할을 따로 표시. 브라우저 후보/무연결 전환 확인.
- **결정/다음:** 실험만 적용. 혼합 구간을 조건부 NCT와 연결하여 분산형+장식/화성 교체를 검증하되 자동 기각·운영 승격은 하지 않음.
- **상세:** [규칙·수치·사례·실행·검증·한계](records/2026-09-30-temporal-coherence.md).

## HARM-DEV-20260930-04 — 계류음 보류와 지연 구성음 대조

- **목표/일반 규칙:** 실제 구성음이 늦게 나타나는 것과 끝까지 관측되지 않는 것을 구분하고, 계류 형태에 아직 미확인인 준비/불협화/해결·박절·화성교체 조건을 명시한다. 생략/지연만으로 화음 기각하지 않음.
- **구현:** `harmony_boundary_assessment.py`와 frozen replay 실행기. 별도 보류 record에 실제 시점·음정·성부 refs·support profile과 구성음 경쟁 reading을 연결. 기존 후보/설명량 그대로 보존.
- **검증:**184표본/117경계,14,095profile(지연 후 전 구성음2,766/시작 전 구성음178/부분11,151),21계류 형태는 확정 대신 보류.21개 모두 구성음 경쟁 해석 존재. 독립 화음 수·정답률 아님. 신규16/전체1,565테스트, 원 JSON/hash 불변.
- **화면:** K281 sample16 전체 악보에서 Dmajor의 F♯ 미관측/보류 이유를 보여 주고 E♭major 선택 시 구성음 해석으로 바뀌는 것 확인.
- **상태/다음:** 실험만 적용. Core/원주석/운영5173/구조 분석 미변경. 다음은 지연 출현과 실제 화성 교체의 시간적 일관성·성부 문맥 대조.
- **상세:** [계약·사례·한계·재현](records/2026-09-30-boundary-assessment.md).

## HARM-DEV-20260930-03 — 경계의 실제 동시음·베이스·박절·시간 지지

- **목표:** 하행 음형만으로 성립하는 계류 후보를 실제 동시음 근거와 구별한다. 원래117경계/184표본/모든 후보 유지.
- **구현:** 유리수 시간 셀별 실제 최저음(중복/미정/쉼 구별), 철자 도수/반음 수, 표기 박자의 분모 단위 위치, 구성음별 관측 시간 합집합과 동시 출현을 별도 evidence로 연결했다.
- **사례:** K281 sample16 경계의 최저음 E♭ 유지, B♭와5도/7반음. Dmajor 구성음은 직후0개인 반면 E♭major는3개. 후보의 약점을 표시하되 자동 화성 선택은 안 함.
- **검증:**117경계/965셀/14,095지지 profile, 기존135음형 refs 연결. 최저 음높이 변화27/유지90은 겹치는 가정별 관측이며 정답 수 아님. 신규22/전체1,549테스트. 원출력 필드/hash/계획 불변, 브라우저 후보 전환/악보 확인.
- **상태:** 실험 증거/UI. 운영5173·Core·원주석·구조 분석 미변경. 교재 신규 독해/정확도 개선 검증 아님.
- **다음:** 실제 음정·박절·시간 지지와 계류 필수 조건/경쟁 가설을 연결하는 보류 규칙 검증.
- **상세:** [계약·수치·사례·실패/수정·재현](records/2026-09-30-boundary-observations.md).

## HARM-DEV-20260930-02 — 지속음 내부 경계 검사와 과잉 후보 점검

- **원인:** 기존184표본의 성부 attack 경계에는 온전한 관찰 성부 sound가 걸쳐 지속하는 경우가0. 실제 계류/지속 선행음0을 음악적 부재로 해석할 수 없었다.
- **일반 규칙:** 동일 범위·성부 연결을 보존하고 전 part attack 중 관찰 성부의 실제 지속음 내부 시각을 추가한다. 음높이/라벨 없이 모든 새 계획을 먼저 고정한다.
- **결과:**117추가 경계, 조건부 패턴135(지속 선행음88/계류21/기타26), 중복 제거61. 정답/개선율 아님.135대표 조합의 양쪽후보 보류·무연결·음가보존 검사. 원출력/계획/source hash 보존.
- **중요 반례 위험:** K281 sample16의 B♭→A는 형태상 계류 후보이나 선택 Dmajor의 F♯ 근거가 없다. 실제 계류음 확정으로 채택하지 않음. 화면에 후보의 미관측 구성음 안내 추가.
- **검증:** 신규10/전체1,527테스트. 연구용 추가 검사이며 운영5173/Core/원주석/구조 분석 미변경.
- **다음:** 경계 시점의 실제 베이스·수직 음정·구성음 시간 지지·박절 증거. 음악적 양성 검증은 여전히 남음.
- **상세:** [원인·계약·수치·실제 위험 사례·재현](records/2026-09-30-held-boundary-coverage.md).

## HARM-DEV-20260930-01 — 경계를 넘는 조건부 비화성음

- **문제:** 후보 구간을 나누면서 앞/뒤 음 문맥이 사라져 같은 화음의 경과/보조 설명까지 소실됐다.
- **일반 규칙/구현:** 공통 후보 양쪽의 membership과 동일 성부 연결에서 경계3음 형태·재타격/지속 선행음·실제 지속 후 하행 계류 후보를 분리한다. 적용할 비구성음 시간만 표시하고 구성음/원음표/총 음가는 바꾸지 않는다. `harmony_boundary_figures.py`와 실행기·네 열 비교 UI 추가.
- **검증:** 신규18/전체1,517테스트 통과. 기존184표본과300분할 가정 유지, 이전 JSON 필드/120 preview 비교/원본 hash 보존. 실제51경계 가정에65패턴 기록, 기본 비교13표본의 조건부 설명 추가. 독립 정확도/확정 NCT 수가 아니다.
- **검증 공백:** 실제 범위에서 준비된 계류/지속 선행음 새 양성0. 구성 대조 검사만 통과했으며 실제 양성 검증은 별도 필요.
- **사례/화면:** K281 sample15 A5의 경계 경과음 설명이 분할에서도 복원된다. ‘유지/분할(이전)/분할+문맥’ 표와 무연결 대안을 전체 악보에서 확인했다. 사용자 승인 사례로 승격하지 않는다.
- **상태:** 연구용 구현/테스트/화면. 운영5173·Core·원주석·구조 분석 미변경. 인수인계 문서에 기록하지 않음.
- **다음:** 반례·실제 양성 검증 후 박절·수직 음정·화성 교체 근거 연결.
- **상세:** [계약·사례·수치·재현·한계](records/2026-09-30-cross-boundary-figures.md).

## HARM-DEV-20260929-02 — 공통 후보의 동일 음가 유지·분할 비교

- **문제/일반 규칙:** 한 화음 전제의 조건부 NCT만으로 화음 유지 여부를 판단할 수 없다. 동일 시간 셀·전체 part 음표·전체 성부 assignment 아래 유지/분할 양쪽을 대조한다. 특정 작품 예외는 없다.
- **구현:** `harmony_segment_contrast.py`, 실행기, 전체 악보 비교 UI. 모든 카탈로그 대안을 요소별로 저장하고 선택 조합을 계산한다. 원주석·최종 승자·확률은 사용하지 않는다.
- **실제 검사:** 기존184표본/원계획 유지.150표본에서300분할 가정,205철자 비교 가능·95부족 보류.120개 미리보기 조합을 Python으로 대조. 가능한 조합 수와 실제 계산 수를 구별한다.
- **검증:** 신규13/전체1,499테스트 통과. 원184표본 파일 실행 전후 hash 및 계획 hash 불변. 새 XML 재파싱·독립 정확도 평가 아님.
- **문제 발견/수정:** r1의 빈 철자 대안 `ready` 집계를 r2에서 별도 보류로 수정. 동일 화음도 범위 절단만으로 경과음 설명이 사라질 수 있어, 음가 차이를 점수로 사용하지 않는다. r3에서 원계획 대조와 분할 점선·음표별 설명 UI 추가.
- **사례:** K281 sample15의 E♭ 유지 대 B♭→E♭ 분할. D4/A5의 역할 차이를 전체 악보 위에 표시한다. 사용자 음악적 검수 승인은 아직 없다.
- **상태/다음:** 연구용 구현·검증·화면. Core/원주석/운영5173 미변경. 다음은 경계를 넘는 NCT 문맥과 화음 교체 근거의 구별.
- **상세:** [설계·수치·실패·사례·재현·한계](records/2026-09-29-common-candidate-segment-contrast.md).

## HARM-DOC-20260929-01 — 개발 문서 독립 관리

- **요청:** “인수인계 문서가 아니라 개발 문서여야 하는데요. 화성 분석 개발 문서는 따로 관리해 주세요.”
- **문제:** 인수인계 문서에 날짜별 실험과 과거 ‘최신 상태’가 계속 쌓여 개발 정본의 역할이 혼재했다.
- **변경:** `docs/harmony/README.md`를 개발 메인 문서로, 이 파일을 변경 기록으로 지정했다. 새 상세 주제는 `docs/harmony/records/` 아래에 두도록 정했다.
- **보존:** 기존 인수인계 문서 전체 내용을 [과거 개발 이력](archive/DEVELOPMENT_HISTORY_THROUGH_2026-09-29.md)에 보존했다. 상대 링크는 새 위치에 맞췄다. 원래 인수인계 파일은 전달용 체크리스트와 개발 문서 링크만 유지한다.
- **진입점 정리:** Canonical IR README·문서 지도·통합 실행 계획·교재 문서의 현행 기록 안내를 개발 문서로 변경했다. 과거 날짜의 기록은 소급 삭제하지 않았다.
- **검증:** 상대 링크의 위치 보정을 제외한 기존 이력 전체 본문 일치 확인, 새 메인·로그·인수인계 안내의 로컬 파일 링크19개 확인, `git diff --check` 통과. 코드/분석 결과/악보 화면 변경이 없으므로 음악 분석 테스트는 재실행하지 않았다.
- **공개 범위:** 책·원자료·실험 출력·공개 제외 교재 상세 문서는 복제/업로드하지 않았다. Git commit/push는 하지 않았다.
- **결정:** 앞으로 화성 개발 결과는 개발 로그에 기록하고, 인수인계 문서에는 누적하지 않는다.

## 기존 상세 개발 기록 색인 — 2026-09-29

아래는 기존 기록으로 연결하는 색인이다. 이번 문서 정리에서 새로 실험한 결과가 아니다.

| 단계 | 상세 개발 문서 |
|---|---|
| 실제 연속 음형과 후보 대조 | [184표본·동일 음가·검증·보류](../../MUSICANOTE_Canonical_Music_IR/HARMONY_CONTINUOUS_SURVEY_2026-09-29.md) |
| 성부 경로별 조건부 NCT | [경과/보조 형태·경로 의존성](../../MUSICANOTE_Canonical_Music_IR/HARMONY_PATH_ORNAMENTS_2026-09-29.md) |
| 연속 성부 경로 | [전체 조합·음가 보존](../../MUSICANOTE_Canonical_Music_IR/HARMONY_VOICE_PATHS_2026-09-29.md) |
| 문맥 확대 | [범위·복수 대응](../../MUSICANOTE_Canonical_Music_IR/HARMONY_PATH_CONTEXT_2026-09-29.md) |
| 지연 경로 | [공통 후보 조건부 설명](../../MUSICANOTE_Canonical_Music_IR/HARMONY_CATALOG_PATHS_2026-09-29.md) |
| 미세 시간축 | [실제 attack/release 연결](../../MUSICANOTE_Canonical_Music_IR/HARMONY_CATALOG_MICROTIME_2026-09-29.md) |
| 후보 해결 관계 | [공통 후보·기능 가정](../../MUSICANOTE_Canonical_Music_IR/HARMONY_CATALOG_RESOLUTION_2026-09-29.md) |

더 이전 구현·교재 단원·실패/보류 이력은 [보관본](archive/DEVELOPMENT_HISTORY_THROUGH_2026-09-29.md)과 [기존 주제별 문서 지도](../../MUSICANOTE_Canonical_Music_IR/DOCUMENT_MAP.md)에서 찾는다. 과거 교재 상세 기록의 공개 제외 상태는 유지한다.
