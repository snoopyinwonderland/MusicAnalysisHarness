# 단계92 — 정확한 박자 환산 재사용의 고정 Dev 비교

## 결과와 결정

같은 고정35모델·원 후보·점수로 Dev를 다시 계산했지만 **완료율·화음 경로·음악적 지표의 개선은 없었다.** 원72record 중46완료/17시간 보류/기존 입력 보류9로 단계89와 같다. 공통 완료46의 raw ID·Fraction 비용·상세 근거·전이 수·DP 진단은 모두 동일하다. 캐시 hit가 많다는 것을 음악적 개선으로 해석하지 않는다.

운영/UI/Claude 편곡 연결은 미채택 상태를 유지한다. 고정 Train/Dev의 캐시 확인을 여기서 마치고, 다음은 **큰 Train 화음·비화성음(NCT) 오류의 점수·표현 개선**이다. 보류를 없애기 위한 반복 측정만 이어가지 않는다.

## 원 자료와 실행 계약

- 원72record, 실제 탐색63graph, 고유범위60, 전체 악장 source14개, 이름 기반 작품군9개, 원44,204edge를 그대로 사용했다. 72곡/14곡의 전체 악장 분석이나 독립 Test가 아니다.
- Train15작품군과 Dev9작품군의 이름 기반 가족 겹침0이다. 악보 전체의 중복/편곡 계보 감사가 끝났다는 뜻은 아니다. 이전 컨테이너에는 이미 노출된 Dev 진단이 있어 독립적인 블라인드 성능을 주장하지 않는다.
- 모델은 단계88 순위 보호35, SHA `b6ff68e73bf6b5b9760107344f66f5c5626da2aa5c8b93ca061c21d6cbc74f38`다. 단계91 전체 Train 봉인 결과를 선행 관문으로 확인하고 같은35계수를 불러왔다. 새 fit/sweep/Dev checkpoint 선택0이다.
- 구간당20초 cooperative guard,2,000,000 전이 비교, **원 graph별 분할 상한**을 보존했다. 기본 상한6은61graph, 기존 상한18·24는각1graph다. 아래 감사 정정을 참조한다. 상한을 새로 늘린 것이 아니다.
- 박자 환산의 source-local `(start,end)` Fraction cache만 적용했다. 원 XML/IR·철자·음가·조표·변박·성부·붙임줄·grace·unknown·후보·DP·상세 비용식은 그대로다. 구간마다 새 scorer/cache를 만들었다.
- 모든72예측을 저장하고 `prediction-freeze.json`을 만든 뒤 현재 참조 보고서를 열어 평가했다. 새 target-compatible 탐색/과거 결과 fallback/부분 승자/재시도/작품별 분기0이다.
- 이전 기준26·역할35 결과는 이력으로 보존했다. 이번에 새로 계산한 것은 **같은 순위 보호35의 캐시 조건 한 개**다. 세 모델의 시간을 같은 실행에서 새로 비교한 것이 아니다.
- 기존 입력 보류9개는 재시도하지 않았다. 주석이 부분적으로만 평가되는21record도 삭제하지 않았다. 모든 구간의 전체 악보와 전후 맥락은 source 경로/SHA로 유지한다.

## 구현 파일

최초 실행용4파일:

- `src/musicanote_harness/harmony_exact_beat_dev_trial.py`: 같은 모델의 ordinary 선택, 원 이력 보존, 예측 선봉인, 사후 평가와 경로 재현.
- `tests/test_harmony_exact_beat_dev_trial.py`: 실행 계약8검사.
- `scripts/validate_harmony_exact_beat_dev.py`: 이전978검사를 유지하고 새8검사를 추가.
- `scripts/audit_harmony_exact_beat_dev.py`: 최초 감사. 모든 cap=6이라는 잘못된 가정으로 실패했다. **봉인된 원 파일을 고치지 않았다.**

감사 정정용 추가4파일:

- `src/musicanote_harness/harmony_exact_beat_dev_audit_v2.py`: 원 graph와 과거 guard, 이번 guard의 cap이 각각 같은지 검증하며 나머지 source/점수/지표 검사를 유지.
- `tests/test_harmony_exact_beat_dev_audit_v2.py`: 원18·24 허용과 상한 변경·잘못된 값 거부 등5검사.
- `scripts/validate_harmony_exact_beat_dev_audit_v2.py`: 원986검사를 보존한991검사.
- `scripts/audit_harmony_exact_beat_dev_v2.py`: 별도 `post-seal-audit-v2.json` 생성. 새 탐색/학습0, 이전 출력 덮어쓰기0.

최초4code/test/script는 실제 탐색 시작 뒤 수정0이다. 추가4파일도 v2 감사 시작 뒤 수정하지 않는다. 부모 cache/선택기/모델/주석/소스/이전 봉인 결과를 수정하지 않았다.

## 실제 검증과 감사 실패의 정정

새8검사 PASS·2.035초, 최초 관련986검사/94모듈 PASS·failure0/error0·141.219360초 후 실제 실행을 시작했다. 실제 실행은 **577.935945초/exit0**로 완료했다. 전체 repository 검사나 작품 수가 아니다.

최초 사후 감사는31번째 record의 `beat_dev_audit_selection_contract_changed`로 exit1이었다. 원 graph와 과거·새 guard에는 같은 상한24가 저장돼 있었지만, 감사 코드가 일괄6을 요구했다.72번째 record에도 같은 문제(원18)가 있다. 새 계산의 상한 변경이나 화음 결과 불일치가 아니다.

| 원 graph의 실제 상한 | graph 수 | 이번과 과거 동일 여부 |
|---|---:|---|
|6|61|동일|
|18|1|동일|
|24|1|동일|

상한24의 원 구간은 `dcml:beethoven-quartets:n06op18-6_02` / `cont_e7191dd5889497e23dc1` / `[167/2,175/2)`, 상한18은 `dcml:beethoven-sonatas:07-2` / `cont_f3c7cdac22d1e8650885` / `[105,109)`다. 이 목록은 **봉인 자료의 감사 목록이지 작품별 분석 규칙이 아니다.** 두 구간 모두 원 시간 보류를 유지했다.

따라서 원 `run-contract.json`/report의 `raw_segment_cap=6`은 **기본값을 기록한 메타데이터이며 모든 구간의 실제 상한이6이라는 선언으로 읽을 수 없다.** 기존 단계89와 당시 문서의 일괄6 설명에도 이 정정을 함께 적용한다. 원 결과·코드·보고서·과거 문서는 덮어쓰지 않고 본 기록과 별도 v2 감사로 정정 이력을 연결한다. [최초 실패 기록](../../../output/harmony-exact-beat-dev-2026-10-06-r1/audit-v1-failure.json).

추가5검사 PASS, 원986포함 최종991관련검사/95모듈 PASS·failure0/error0·139.928705초다. [최초 validation](../../../output/harmony-exact-beat-dev-validation-2026-10-06-r1.json), [정정 validation](../../../output/harmony-exact-beat-dev-audit-v2-validation-2026-10-06-r1.json).

사후 감사 v2도 PASS/exit0이다.6,695고유SHA/5,108봉인 reload·72record/63source scope/14전체package/44,204edge·236상세 비용(과거190+새46)/252scalar·role 전이·공통46승자 동등성·원9입력 보류·전체/공통 지표를 확인했다. 원 graph/과거 guard/새 guard의 실제 cap도 모두 같다. 새 decoder/fit0이다. [정정 사후 감사](../../../output/harmony-exact-beat-dev-2026-10-06-r1/post-seal-audit-v2.json).

## 전체 및 공통 완료 지표

아래 진행 일치는 **구간 전체의 근음+철자 포함 구성음 진행이 주석 투영과 같은지**를 말한다. Roman·전위·국소 조성·NCT의 전체 정확도가 아니다. 전체72에는 완전 평가51/부분21, 공통 완료46에는 완전37/부분9가 있다. 부분 주석의 알려진 시간만 시간 분모에 들어가며 unknown을 정답/오답으로 메우지 않는다.

| 지표 | 과거 순위 보호35 | 이번 캐시 |
|---|---:|---:|
|전체72 완료 / 새 시간 보류 / 기존 입력 보류|46 /17 /9|46 /17 /9|
|전체의 완전 평가 가능한 진행 일치|14 /51|14 /51|
|전체 근음+구성음 시간 일치율|19.463244%|19.463244%|
|전체 예측 시간 coverage|27.467911%|27.467911%|
|전체 작품군 macro|25.345805%|25.345805%|
|전체 의미적 경계 TP / FP / FN|30 /4 /33|30 /4 /33|
|전체 의미적 경계 F1|61.855670%|61.855670%|
|공통46의 완전 평가 가능한 진행 일치|14 /37|14 /37|
|공통46 근음+구성음 시간 일치율|70.858114%|70.858114%|
|공통46 작품군 macro|46.415860%|46.415860%|
|공통46 의미적 경계 TP / FP / FN|30 /4 /11|30 /4 /11|
|공통46 의미적 경계 F1|80.000000%|80.000000%|

보류26개를 빼고70.86%를 전체 성능으로 제시하지 않는다. 새 보류 복구/기존 완료 소실/새 정답/기존 정답 소실/공통 raw 경로 변경은 모두0이다. 평가 가능한 quality/전위/local key/degree/Roman의 시간은0이므로 정확도 값은 null이며, ‘틀린 것이0’이라는 뜻도 아니다.

이전 기준26과의 대조도 보존했다. 전체 완료62→46, 시간 일치29.754959%→19.463244%, coverage42.590432%→27.467911%다. 공통46에서는 진행11→14, 시간65.505523%→70.858114%, 경계F1 74.074074%→80%다. 하지만 기준26이 완료한16개가 이번에도 시간 보류이며 그중 기준 정답5개가 있다. 공통의 개선만으로 운영 승격하지 않는다. 이 차이는 새 캐시의 음악적 개선이 아니라 **이전 단계89에도 있던 모델·완료율 차이**다.

## 계산량과 시간

새 DP cache 조회842,109 /hit841,553 /원 적분556 /entry합556이다. 캐시 없는 독립 상세 winner 검증과 사후 경로 재현의 호출까지 포함한 전체 프로그램 호출 수는 아니다.

| 시간(초) | 과거 같은35 | 이번 캐시 |
|---|---:|---:|
|실제 탐색63구간 guarded 합|461.616805|468.113903|
|공통 완료46 guarded 합|112.949871|112.533167|
|공통 완료46 guarded 중앙값|0.725056|0.663292|

원 source 준비 합29.902737초, 새 guard 최대25.212600초다.20초는 cooperative 제한이라 한 함수가 오래 걸리면 넘어갈 수 있다. 전체 실행577.935945초는 source 준비·봉인 읽기·사후 재현까지 포함한다. 기준 arm을 동시에 새로 계산하지 않았고 머신 부하도 통제하지 않았으므로 **보장된 속도 향상은 주장하지 않는다.** guarded 전체 합은 오히려 늘었으며 완료율도 같다.

과거 같은35의190named 상세 비용(다른 arm의 경로 및 참조 witness 포함)을 전부 보존하고 새 승자46비용을 더해 **236상세 비용·252scalar/role 전이**를 재현했다. 참조 witness는 사후 평가용이며 예측/새 가중치의 입력으로 사용하지 않았다.63case를 모두 이전63case에 연결했다.

## 원악보에 연결한 유지·오답·보류 사례

개별 음악의 판정을 억지로 고치지 않았다. 아래는 이번 계산의 상태를 확인하는 자동 사례이며 새로운 human gold/NCT 정답이 아니다. 모든 시간은 quarter 단위 `[start,end)`이고 원 전체 악보가 보존돼 있다.

### 1. 유지된 일치 — Chopin op50-2, 인쇄60마디

`dcml:chopin-mazurkas:BI145-2op50-2` / `cont_4d226f9b4507f5c04236` / `[711/4,180)`.

참조와 선택 모두 `[711/4,179)` D♭근음·D♭–F–A♭, `[179,180)` G♭근음·G♭–B♭–D♭이다. 원 D♭3 `sound_168cb6dbacd2`→`note_31cb37f4e985`, F4 `sound_3383d769b1cf`→`note_f506ab4203cd`는 `[711/4,178)`·1/4음가다. 다음 D♭3 `sound_3eb3e7befe51`→`note_9ec9c2649196`는 `[178,179)`·1음가다. 새로운 장식/NCT 라벨을 확정하지 않았다.

새 비용 `11259881/67500000`, guard0.288960초·cache594조회/591hit/3적분이며 과거와 같은 raw 경로·근거다. [case](../../../output/harmony-exact-beat-dev-2026-10-06-r1/cases/1eae4adabd5eb093c0d8.json.gz), [전체 XML](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/368d46f4807d08ac9fad/source.musicxml), [전체 IR](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/368d46f4807d08ac9fad/canonical-ir.json.gz).

### 2. 오답 유지 — Beethoven sonata07 II, 인쇄37마디

`dcml:beethoven-sonatas:07-2` / `cont_a40ed377ae28d702a53e` / `[109,110)`.

참조는 `[109,219/2)` E근음·E–G♯–B–D, 뒤는 G♯근음·G♯–B–D–F다. 새 선택은 앞을 G♯–B–D♯로 골랐고 뒤만 참조와 같다. 캐시로 오답을 해결하지 않았다. 관찰된 G♯2 `sound_5d9df86dd878`→`note_315305a40d16`는1/2음가, D♯3 `sound_3bb4f21f82c7`→`note_d176ee018464`는3/8음가이고 E3 `sound_ad1b79f4885f`→`note_3609be0427de`가 `[875/8,219/2)`에1/8음가로 들어온다. 이 앞뒤 음의 역할은 경쟁 화음 아래서 더 검증해야 하며 본 기록에서 NCT를 단정하지 않는다.

새 비용 `4545437/11250000`, guard0.418713초·cache724조회/721hit/3적분, 과거와 같은 오답이다. [case](../../../output/harmony-exact-beat-dev-2026-10-06-r1/cases/0236487d891622eaf7b9.json.gz), [전체 XML](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/a86ada3752f6688ea503/source.musicxml), [전체 IR](../../../output/harmony-temporal-scoring-2026-10-05-r1/sources/a86ada3752f6688ea503/canonical-ir.json.gz).

### 3. 계산 보류 유지 — 같은 악장 인쇄36~37마디

`cont_f3c7cdac22d1e8650885` / `[105,109)`는 원 graph cap18이다. G3 `sound_22c0c6538cae`→`note_17bfdf543fb5`가 `[105,108)`·3음가로 지속하고 그 위로 짧은 음들이 움직인다. 전체 음가·철자·전후 악보는 그대로다.

원/이번 모두 시간 보류이고 이번 guard21.005716초·cache44,886조회/44,872hit/14적분이다. **상한18을6으로 바꾸거나20초를 늘리지 않았으며, 부분 경로를 화음으로 내보내지 않았다.** 이는 ‘원 상한을 유지했는지’ 감사 정정의 사례이자 캐시만으로 큰 구간이 풀리지 않는 사례다. [case](../../../output/harmony-exact-beat-dev-2026-10-06-r1/cases/fe9b0e1f69963fe907c1.json.gz). 전체 XML/IR은 위 같은 악장 경로다.

## 봉인 및 재현

정본은 [report](../../../output/harmony-exact-beat-dev-2026-10-06-r1/report.json)이며 `progress.json`은 진행용이다. 입력6,626/artifact137/code452 SHA를 저장했다. 최초 실패 후 원 report/contract/freeze·실제 탐색 코드·모델은 변경하지 않았다.

| 산출물 | SHA256 |
|---|---|
|report|`9923a4ef3306c7cf0f6094a2694258527d538a5657b50daab719066dfef29b76`|
|run contract|`1348fb08aef2214a0e6923fda162fb0daff1d4e64e1b92e0dfc431855b549e67`|
|prediction freeze|`57544384be9d646edf2fb4745213771eb19df9461490da30d31d510889cdece9`|
|최초986 validation|`b06400079d88d49c89939d699bfc16644036af527b3eacd782b5852bff612114`|
|991 validation|`3355a1f7e13635310c14900f105e98108935f178f1600a003dd56628038efd28`|
|사후 감사v2|`00632e90a121046c75cd79827f34c2ff647b9fea8a5e62e1bd89a7f61421c626`|
|최초 감사 실패 기록|`2a299fe005214bd2434a417a8cb02564a37a818df2ade82e9d2977b69b597706`|

기존 출력은 덮어쓰지 않는다. 재현 시 별도 출력 경로를 사용한다. 최초 감사 실패도 보존하며 새 검증과 별도 v2 감사가 정정 경로다.

```powershell
$env:PYTHONPATH='src;tests'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_exact_beat_dev.py --prior-validation output/harmony-exact-beat-train-validation-2026-10-06-r1.json --output output/harmony-exact-beat-dev-validation-reproduction.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_exact_beat_dev_trial --output output/harmony-exact-beat-dev-reproduction --validation output/harmony-exact-beat-dev-validation-reproduction.json
.\.venv\Scripts\python.exe -B scripts/validate_harmony_exact_beat_dev_audit_v2.py --prior-validation output/harmony-exact-beat-dev-validation-2026-10-06-r1.json --output output/harmony-exact-beat-dev-audit-v2-validation-reproduction.json
.\.venv\Scripts\python.exe -B scripts/audit_harmony_exact_beat_dev_v2.py --root output/harmony-exact-beat-dev-reproduction
```

마지막 명령은 원 판단을 다시 탐색하는 것이 아니라 생성된 예측을 사후 감사하는 절차다.

## 다음 개발 단계

1. 봉인된 Train의 큰 화음/NCT 오답을 후보 존재·같은 점수의 경쟁·근음/3음/7음 지지·앞뒤 준비와 해결로 나눠 우선순위를 정한다.
2. 근거 규칙을 일반 특징으로 보완한다. Dev의 특정 마디 강제 교정/Dev 재학습/unknown의0메우기는 금지한다.
3. 새 변경은 Train의 실제 선택과 기존 정답 보호를 확인한 뒤 같은 고정Dev에 넘긴다. 전체 Roman·국소 조성·전위·독립Test 및 생성 품질은 별도 평가한다.
4. 현재 화면·Claude Phrase/Motif/편곡은 변경하지 않고 운영 채택과 외부 연결은 보류한다.

Core/원주석/부모봉인/권한/UI/서버/MusicSearch/Music Composition/기존tracked dirty5/Git를 보존했다. merge/commit/push/API 조작0이다.

최종 QA에서 새8파일의 AST와 봉인 SHA, 화성 개발3문서의 UTF-8/깨진 문자·다른 언어 혼입·후행 공백, 본 기록의12로컬 링크, 전체72record의 지표 재계산, 공통46동등성, 원report 불변을 확인했다. `git diff --check`도 통과했고 기존tracked dirty5의106추가/326삭제는 그대로다. 검사 통과를 음악적 정확도 향상이나 전체 개발 완료율로 해석하지 않는다.
