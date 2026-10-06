# 단계101 — 긴 전곡 단계 측정과 정확한 비용 projection

2026-10-06. 화성 개발 전용 기록이다. 목표는 단계100 뒤 남은 긴2곡의 큰 계산 병목을 파악하고 음악 판단을 바꾸지 않고 줄이는 것이다. 기존96–100, 연구용 고정모델, Core/XML/주석, MusicSearch/Composition/화면/서버/Git는 수정하지 않는다.

## 실행 전에 정한 범위

[단계 측정 사전계약](../WHOLE_SCORE_PHASE_PLAN.md) → 두긴곡진단 → [측정 후 단일 비교 계약](../WHOLE_SCORE_COMPILED_PLAN.md) 순서다. 같은6곡 개발자료이며 독립Test/234전곡의 정확도 검증은 아니다. 원26계수 숫자/단계99점수/지원domain/후보/beam8/2M/60초/source IDs/Fraction/철자/음가를 유지한다. 부분 승자 제출·정답을 보고 규칙 조정·학습·후보 축소·작품별 예외는 없다.

## 1. 두 긴곡 진단

`diagnose_harmony_whole_score_phases.py`가 각각 한 번60초·동시2로 단계100의private 원함수 binding과같은 계산을 계측했다. 전체범위이지만 timeout에부분예측을 제출하지 않는다. 작은`.phases.json` sidecar에완료단계시간·현재단계·최근셀을 남겼다. inclusive wall time은중첩되므로무작정합산하지않는다.

| 작품 | 결과 | 마지막 남은 상태 |
|---|---|---|
| Experience | 60.07초 timeout | 전체1623셀 중571consume완료; 마지막표시544셀(32셀간격),72catalog; parse2.083초/evidence1.018초/index0.614초/catalog12.894초/consume37.221초. 직접검산/저장에는도달하지않음 |
| Walking On Sunshine | 60.07초 timeout | parse가끝나지않음; 검색/압축이원인이라고확정할수없음 |

진단해시473PASS/불일치0. 시작전작은합성곡계측 대원100의출력/비용/catalog smoke PASS. 이전4동시실험과부하가다르고계측 overhead가있어서표의시간을기존실험과속도비교하지않는다. Walking의이전99baseline parse39.496초 기록도있어이번지연을XML손상으로단정하지않는다.

정본: [진단 상태](../../../output/harmony-whole-score-phase-2026-10-06-r1/diagnosis/statuses.json), [Experience 단계](../../../output/harmony-whole-score-phase-2026-10-06-r1/diagnosis/jobs/059-diagnosis.phases.json), [Walking 단계](../../../output/harmony-whole-score-phase-2026-10-06-r1/diagnosis/jobs/211-diagnosis.phases.json), [진단 감사](../../../output/harmony-whole-score-phase-2026-10-06-r1/diagnosis/audit.json).

## 2. 계산 구현 및 동일성 계약

새 `harmony_whole_score_compiled.py`의version은`local-beat-whole-score-supported-domain-0.2.2-compiled`다. 음을지우거나음가/그리드를양자화하지않는다.

- 비구성음·강박·긴음·최저음의4prefix와고정계수분모LCM으로정확한weighted integer prefix를만든다. query는전체−구성음 비용의정수차이를유리수로복구한다. float/반올림이없다. negative weight도그대로지원하며unknown/미평가항을관측0이라고선언하지않는다.
- 부재 구성음/근음/역할,복잡도,조표,지연근음,늦은구성음,조건부ornament cap은같은정의를합산한다. 후보/원catalog validation·공급/동점IDs/상태손실·해결크레딧은바뀌지않는다.
- 문맥의기준박적분은원meter prefix를이용한다. lowest는원sound행의half-open sweep을사용한다. 원RootReturnContext._support를재사용하되이미필터할같은철자root행만loop에공급한다. 성부/전체lowest/가짜쉼·tie/grace/repeat/history 관문은보존한다. 해당lookup이없는시각은원구현으로fallback한다.
- 원UnitSearch.finish와 **단계99 UnitScorer 직접점수 검산**을유지한다. 검산용source/pair cache는검색캐시와독립이다. 원legacy 전체feature 재계산도이번에는그대로두었으며검산을생략해속도를좋게보이지않는다.
- parser/gzip/후보를바꾸지않았다. 두 arm의20초stack trace·phase sidecar는관찰만하고자동고침이나부분제출을하지않는다.

## 3. 실행 전 검사

신규5+기존47=52PASS(4.842초). weighted integerprefix의양수/음수/빈table/unknown, 모든합성span의triad/seventh/기능6/4/rootunknown, 변박·triplet, 양수passing·준비된늦은3음·근음return, lowest의start/end전후·history/repeat, frontier/동점/연산/손실·부분보류·원직접승자검산·전체catalog/경로/특징/source 불변을검사했다.

최초52검사에는1FAIL이있었다. test에서원RootReturnContext에는history_gate를넘기지않고새context에만넘겨receipt의history상태null 대true가달랐다. 양쪽같은args로test만수정해PASS다. 음악코드의실패를감추지않으며본실행봉인후코드/검사/계약수정은하지않는다. 파일조회1건에서존재하지않는`test_harmony_root_context.py`를잘못지정했고실제`test_harmony_root_context_scoring.py`를읽었다.

## 4. 단일 통제 비교

실행기: `scripts/run_harmony_whole_score_compiled.py`. control=계측원100, engine=compiled. 같은6곡×2,각60초·동시4·재시도0이다. baseline은99봉인예측을재사용하고이번속도측정으로계산하지않는다. 두새예측해시를고정한뒤gold채점한다. 완료곡의선택/비용/원특징/availability/실제run/원span/전체catalog를현재control및이전100완료4와비교한다.

12작업 완료·exit0, 전체실행/채점/감사120.536427초다. engine와control모두4완료/2timeout이며 추가완료곡은없다.

| 작품/원셀수 | control wall seconds | compiled wall seconds | 결과 |
|---|---:|---:|---|
| Reach For The Stars! /88 | 2.964532 | 2.781206 | 양쪽완료 |
| It_S A Small World /188 | 9.455600 | 8.950416 | 양쪽완료 |
| Family Of The Poor /294 | 19.038902 | 18.083997 | 양쪽완료 |
| Pledging My Love /603 | 40.835071 | 38.553814 | 양쪽완료 |
| Walking On Sunshine /1006 | 60.030247 | 60.023703 | 양쪽timeout |
| Experience /1623 | 60.023266 | 60.016748 | 양쪽timeout |

이번한번의완료4곡wall감소는약5–6%다. 반복측정에의한통계적속도우월성이나모든음악의속도배수를주장하지않는다. Pledging의search consume은17.699→14.872초, catalog는12.396→13.506초, 원finish검산은2.456→2.595초였으며nested시간을합산하지않는다. 아카이브serialize/compress는각0.55/0.76초정도라이번큰병목이아니다.

**동일성:** 공통완료4곡모두현재control및이전100과원선택경로/정확한점수/26feature values·availability/실제run/원sourceIDs/상태손실/연산/제출span/page inventory/전체catalog 데이터가같다. 완료4곡의원99직접전곡점수검산PASS다. 실행후500pin감사PASS/불일치0,경로/catalog동일성PASS다. 원100에서끝난Pledging도이번에는양쪽완료하여동일승자직접대조가된다. timeout2곡은전체승자를비교하거나동일하다고인증하지않는다.

**음악지표/연결:** 전체6/1848quarter에서engine=control의root28.3233%/triad27.4397%/pcs24.6350%/bass25.5236%/coverage39.6645%/경계F1 33.6763%다. 봉인baseline은root70.9957%/triad68.5065%/coverage99.8918%/경계F1 59.7544%다. triad차이−41.0668%p, numerical gate FAIL, 기존100과음악지표가같다. 완료4subset/736quarter triad68.8975% 대baseline68.4783%,bass64.0864% 대68.0707%,경계F1 44.4444% 대54.4361%다. 작은개발subset의미세우위를편곡ready또는음악규칙의향상으로읽지않는다. 기존UI/Claude연결보류가유지된다.

### 긴곡 병목의 구체화

- Experience compiled의마지막기록은1110consume호출/137catalog/1623셀(주기checkpoint1088셀),검색37.547초/catalog12.225초다. control은1024셀/125catalog,검색39.201초/catalog11.035초다. 둘다직접검산/저장전시간이끝났으므로압축/검산을생략하는방식은이실패를해결하지못한다.60초안의처리량차이는있지만다른progress에서측정된시간을같은전체검색속도로비교하지않는다.
- Experience의20/40초stack둘다 `RemainingFeatures.domain`의전체pattern Fraction 구간교차scan에서관찰됐다. 이는검색중남은반복scan의구체적단서이며두snapshot만으로전체시간비중을정량화했다고주장하지않는다. 원pattern의same-lane/geometry/전체triple포함조건을유지한interval index가다음대상이다.
- Walking compiled는parse37.827초를썼고381consume호출/62catalog까지진행했다(주기표시352셀).20초stack는 `canonical._voice_id`→music21 `getContextByClass(Voice)`→score tree 구축,40초stack는 `grace_projection`의IRdeepcopy에서관찰됐다. 입력성부조회/tree 비용을우선줄여야하며XML잘못/음악이론오류로단정하지않는다. 단순히시간한도를늘리지않는다.
- Walking control의최종phase sidecar는 **0byte**다. 아래오류를숨기거나다른arm시간으로채우지않는다. 두stack는남아같은성부조회/consumer복사단계가관찰되지만정확한control parse초/처리셀은알수없다.

### 계측파일 끊김과 실행 후 보완

원`Telemetry.checkpoint`는JSON을직접덮어써process종료가쓰기중발생하면이전checkpoint도잘릴수있었다. 비교중Walking control에서실제로0byte가남았다. 이측정구현의결함을보존하고같은버전을재실행하지않았다.

새파일 `harmony_phase_checkpoint.py`에동일디렉터리의pending JSON을완성한뒤`os.replace`하는별도writer를만들었다. 교체실패/중단이면이전완성본이남는다. 기존봉인phases/compiled/runner/검사/계획/산출물을고치지않았다. 신규2검사는정상active checkpoint와publish 실패시이전JSON보존을검사,기존52포함최종54PASS(5.275초)다. **이writer는이번6곡시험에사용되지않았고새전곡실행0**이며이번완료율/속도/음악지표의일부로세지않는다. 디스크flush/전원손실까지보증하는journal은아니다. 이외결과요약조회중PowerShell↔Python inline f-string escaping으로1명령이실행전실패했고PS JSON조회로대체했다.

정본: [전체채점](../../../output/harmony-whole-score-phase-2026-10-06-r1/comparison/score.json), [동일성검사](../../../output/harmony-whole-score-phase-2026-10-06-r1/comparison/equivalence.json), [500pin감사](../../../output/harmony-whole-score-phase-2026-10-06-r1/comparison/audit.json), [Walking실행추적](../../../output/harmony-whole-score-phase-2026-10-06-r1/comparison/jobs/211-engine.trace.txt), [Experience실행추적](../../../output/harmony-whole-score-phase-2026-10-06-r1/comparison/jobs/059-engine.trace.txt).

## 5. 보존·산출물·다음 판단

- 신규파일: 단계계측모듈/진단runner,compiled모듈/비교runner/5검사,사전계약2개/본기록,실행뒤atomic checkpoint모듈/2검사다. 화성메인README와별도DEVELOPMENT_LOG에도결론을추가한다.
- 완료4의전체IR·원catalog·원셀선택/source trace를gzip으로보존하고timeout부분제출0이다. 진단2/비교12의상태·해시·phase/stack를보존한다.0byte sidecar도증거로보존하며동일성검사를통과한예측과혼동하지않는다.
- 기존tracked dirty5/96–100모델·코드·결과·XML/IR/주석·MusicSearch/Composition/화면/서버/Git는보존했다. 추가fit/LLM API/계수/음악규칙/후보domain/beam/timeout변경·운영적용·commit/push0이다.
- 이번수확은완료율확대가아니라 **병목을입력성부조회/consumer복사와검색pattern scan으로구체화**한것이다. 다음은원IR내용/sourceID를그대로보존하는입력경로비용과조건부pattern interval조회라는큰계산문제를먼저다룬다. 정답을보고화음규칙을덧붙이는loop로돌아가지않는다. 아직전체6/234고품질출력이나독립평가·편곡연결은해결되지않았다.

재현명령은이미쓴출력폴더를덮어쓰지않도록새빈경로가필요하다.이번기록을위해재실행하지않는다.

```powershell
$env:PYTHONPATH = 'K:\Music Analysis\src;K:\Music Analysis\tests'
& 'K:\Music Analysis\.venv\Scripts\python.exe' -B -m unittest test_harmony_phase_checkpoint test_harmony_whole_score_compiled test_harmony_whole_score_fast_positive_roles test_harmony_whole_score_fast test_harmony_whole_score_units test_harmony_whole_score test_harmony_whole_score_diagnosis test_harmony_test_a
```

scoreSHA `74a488cdcd2760ccbc4514ded1c90fc9d037f44d409eb7a5eb72c35683ace94a`, auditSHA `ce584781f781e2922ffd0030d58aa6270f88d05114b25d5464460b46bc8fc774`, equivalenceSHA `c0d206149a094cc38356d506ce9bd82cee5962d2ba9b411285c34406edf30a1f`.
