# 완전 저장된 진행 후보의 음악적 근거 검토

개발 단계 **HARM-DEV-20261004-42**. 연구용 구현·실제 저장 자료 검토 완료. 최종 화성 선택, 음악적 정확도 승인, 운영 악보 화면 적용은 아니다.

## 목적과 앞 단계

[단계41](2026-10-03-fresh-bound-storage-continuation.md)은 선택 요청의105task/291,555pair를 모두 저장했다. 이번에는 저장 성공을 화성 정확도로 읽지 않고, **같은 원음표에 대한 구성음 제시·비구성음 설명·베이스·해결·조성·종지의 충족/충돌/미검사 상태**를 음악적으로 읽을 수 있는 별도 기록으로 만든다.

원 Core/XML/음표 ID/음가/타이/원주석, 이전 공급기·비교기·저장 결과와 기본 한도는 바꾸지 않았다. 작품명·work ID·마디 번호에 따른 조건식은 없다. 사용자 교정은 원음과 연결하여 향후 일반 규칙·반례로 활용하며 이번 후보의 정답으로 입력하지 않았다.

## 구현과 API

- [근거 검토 library](../../../src/musicanote_harness/progression_evidence_review.py), `progression-evidence-review-0.1.0`.
- [저장 자료 실행기](../../../src/musicanote_harness/progression_evidence_review_trial.py), `progression-evidence-review-trial-0.1.0`.
- [실제 r1 실행](../../../tmp/progression_evidence_review_pilot_20261004.py).
- [음악/근거 검사](../../../tests/test_progression_evidence_review.py), [reader·저장 실행 검사](../../../tests/test_progression_evidence_review_trial.py).

`review_catalog(catalog, source)`는 외부에서 pin으로 확인한 codec exchange를 소비한다. DAG import는 저장 codec의 타입·구조를 검사할 뿐 live native authority를 복구하지 않는다. 동결된 `native_progression_policy._validate_facet`로 원음의 구성음 분류, 전체 시간 coverage, attack/tie, 구성음 제시, 실제 최저음, 조건부 전위, function shape, 같은 completion의 해결 경로와 credit union 산술을 대조한다. 재사용 validator의 private helper 계약은 버전에 종속되며 운영 API 안정성을 선언하지 않는다.

`review_facet`는 위 검사를 거친 근거의 **순수 투영**이다. 단독 호출은 인증·검증·음악 정답 판정 API가 아니다. `audit_pair_block`는 모든 pair의 원 순서/참조/전제/유리수 transfer 좌우 계정 및 차이를 독립적으로 대조한다. 과거 pair producer나 source pointer 전체 materialization은 재실행하지 않는다.

`run(..., prior_sha256=..., continuation_sha256=...)`는 독립 관찰된 단계40·41 report pin, borrowed source/catalog/block의 실제 byte/SHA, 모든 원 후보/task와 물리 종료를 확인한다. 선택 요청 전체를 먼저 admission하며 예산에 맞는 성공 prefix를 전체 완료로 만들지 않는다. 실행 중 native/role/contrast producer의 fresh replay는 없으며 예전 private registry를 복원하지 않는다.

## 일반 판단 규칙

| 규칙 | 이번에 보존하는 판단 | 하지 않는 확정 |
|---|---|---|
| ER01 | source/철자 불확실한 음가를 별도 보존 | 불확실한 음 삭제·0 처리 |
| ER02 | 명시 key 좌표와 unknown 대안 분리 | 조표를 확정 국소 조성으로 사용 |
| ER03 | 미관측 구성음, 실제 근음 제시와 span 보존 | 구성음 생략/분산/재배치를 자동 승인 |
| ER04 | span 전체에서는 구성음이 모두 보이지만 동시 core가 없을 수 있음 | simultaneous core를 분산화음의 필수 문턱으로 사용, 또는 pooling만으로 화음 지속 확정 |
| ER05 | 설명/미설명/미검사/불확실한 원음가와 조건부 credit 유지 | 모든 비구성음을 NCT로 처리 |
| ER06 | 개별 역할·whole template·joint support를 같은 completion에서 구별 | 개별 이끎음 해결 하나로 전체 진행 승인 |
| ER07 | 같은 root/member signature의 cut에 독립 경계 근거 요구 | 자동 병합·삭제 또는 화음 변화 확정 |
| ER08 | PAC/IAC/HC의 nominal 전제와 미확립 의미 전제를 같이 기록 | C7/V 도착 하나를 종지 정답으로 사용 |
| ER09 | 미설명 음가0이어도 가정한 구성음이 빠지면 추가 근거 필요 | 설명량 최대 후보를 승자/확률로 선택 |

특히 한 화음 유지에는 내부 transition이 없다. 이것을 whole ordinary 성공으로 vacuous 통과시키지도, 내부 진행이 없다는 이유만으로 **화음 유지 가정 자체의 실패**로 판정하지도 않는다. 내부 기능 규칙의 적용 범위와 유지 화음의 구성음·시간·베이스 검토를 분리한다.

관찰/설명의 의존성도 기록한다. raw membership·pooled presence·note-time account는 같은 원음으로부터 나온 근거이며 독립 투표3개가 아니다. 개별 해결·whole template·joint support 역시 같은 completion의 관련 근거다. key/bundle/partition/transition까지 동일한 fixed-premise ID를 유지하고 다른 key/completion의 좋은 부분을 합쳐 승자를 만들지 않는다.

## 무엇을 새로 검증했고 무엇은 저장 근거인가

새 검사는 literal projection·참조 연결·유리수 시간/계정 및 앞 단계의 조건부 결과 계약 검사다. NCT 역할 predicate 자체의 독립 재추론, 원 MusicXML 재파싱, 국소 key 추론, 구조적 bass/melody 또는 지각적 종지 승인 검사는 아니다. Cadence nominal/meaning 축과 ordinary 역할은 앞 단계의 저장 근거로 표시한다. 원주석은 이번 판단 입력으로 사용하지 않는다.

모든 결과의 `selected/rank/confidence`는 null이고 final harmony/NCT/key/cadence·training·generation·production flag는 false다. unknown/False/0은 서로 다른 상태로 보존한다.

## 검사와 개발 중 교정

최종 신규 **29검사/24.107초 PASS**: 핵심15 + reader8 + saved runner6이다. 작은 실제 XML→IR/native/role packet을 입력 생성에 사용한 검사를 큰 실제 corpus 정확도 평가로 표현하지 않는다. Saved runner6개는 실제 음악 packet/파일을 쓰지만 **receipt ancestry는 명시적으로 synthetic**이다.

핵심 검사는 원 후보/부모 보존, 원순서/참조/계정, 유리수1/3, attack/tie, unknown key의 분리, full hold의 내부 관계 비적용, ordinary 양성/무연결/첫 adverse change, 개별 해결과 whole template의 구별, 같은 signature cut, pair 누락/순서/승격/차이 조작 등을 포함한다. ER09의 독립 순수 투영 반례는 authenticated packet 검사가 아니라는 점을 테스트에 표시했다.

Reader는 pin/길이/단일 파일 및 누적 read cap/변경 후 terminal/중복JSON key/NaN/bool·float·음수·cap 상승/덮어쓰기를 검사한다. Saved runner는 실제 물리 파일의 전체 처리, pin chain 불일치, 미완료 선택 범위, 누락 task, source/catalog 변경, whole read admission 실패를 검사했다.

기존 `native_progression_policy`41 + `proof_shared_source_progression_contrast`34의 **75회귀/87.684초 PASS**는 별도 실행이다. 전 repository 전체 회귀나 음악 정답 수로 합산하지 않는다.

초기 신규23개는11오류였다. Facet의 전체 account와 pair index의 **축약3-field account**를 전체 동등 비교한 adapter 오류10건, 서로 다른 key를 단일 compact group에 넣은 fixture 오류1건이었다. 저장된 원자료·account·key를 바꾸지 않고 adapter의 exact projection과 두 개의 genuine group fixture로 교정했다. 교정 뒤23개/21.851초, 추가된 reader/runner 최종14개/3.703초를 확인했고 최종29개를 fresh process에서 재검사했다. 중간 실행을 신규 검사 수에 중복 더하지 않는다.

## 실제 r1 범위와 결과

[실행 report](../../../output/progression-evidence-review-2026-10-04-r1/report.json), [원음 문맥](../../../output/progression-evidence-review-2026-10-04-r1/source-context.json), [첫 key의 전체 후보](../../../output/progression-evidence-review-2026-10-04-r1/group-0000-evidence-review.json).

Actual **exit0/137.3594957초**. 이전111 borrowed comparison artifact와 두 pinned report를 읽었고 decoded980,783,168B<기본1GiB다. 원 source-once82,393,428B는 기존 SourceLimits와 같은 별도256MiB cap을 사용한다. 일반 JSON 파일 cap64MiB를 올린 것이 아니다. 새 output는7파일/95,977,735B이며 파일64MiB·전체256MiB 한도 안이다. 모든 consumed file의 최종 physical SHA/길이와 report 전6개 산출물 SHA를 확인했다. terminal report 자체는 자신의 쓰기를 인증하지 않으며 root가 별도로 검사한다.

**이번 실제 음악 범위는 Beethoven quartet `n01op18-1_04`의 `[262,270)` 한 문맥/4 raw lanes/53 sounding facts다.** 다섯 group은5개의 key 가정이고 음악5곡이 아니다. 원 요청 전체의2문맥/7lanes 및 선언322문맥/1,013lanes는 historical 분모로 별도 보존한다. 선택 요청1,710selector/107batch/105task/291,555pair의 모든 후보와 비교 쌍을 검토했다.

| 검토 항목 | 발생 수 | 해석 |
|---|---:|---|
| 후보 검토 | 1,710 | 같은 문맥·5key 아래의 원 후보 발생 |
| 구성음 부족 후보 | 1,420 | omission/redistribution 근거 필요 |
| span pooling 완전·동시 core 없는 slot을 포함하는 후보 | 580 | 분산형 가능성과 화음 과병합을 시간 근거로 대조해야 함 |
| 미설명/미검사/불확실한 음가가 남은 후보 | 1,650 | NCT 정답으로 승격하지 않음 |
| 미설명 음가0이지만 구성음 부족 | 35 | 동일7대안이5key에서 반복된 수. 독립35음악 사례가 아님 |
| 내부 진행 조건 미충족 후보 | 1,450 | 미선언 관계·형태 충돌·같은 completion의 해결 부족을 각각 보존 |
| 같은 signature cut 포함 후보 | 590 | 자동 병합 판정이 아님 |
| unknown key 후보 | 342 | 다른4key의 결과와 합치지 않음 |
| nominal HC 전제 발생 | 1 | 종지 정답0, 의미 전제는 보류 |
| 모든 내부 joint 지원 | 0 | 아래 무연결 대조군 전제를 함께 읽어야 함 |

이 진단들은 겹친다. 합산하여 전체 실패 수나 오류율로 쓰지 않는다. Raw total note-time은 다성부의 clipped 음가 합이며 clock 구간8quarter와 다르다.

Pair 분류는 candidate-only95,095 / partition179,920 / transition-only120 / candidate-and-transition16,420 =291,555다. 동일 전제에서 alias control은0이고 **계정은 같지만 signature 또는 partition이 다른 쌍11,120**을 보존했다. 계정이 같다는 것과 원음별 역할/음악적 읽기가 같다는 것은 다르다. Pair scalar/transfer margin 검사는 전체 source pointer materialization 재실행과 구별한다.

## 실제 사례에서 드러난 음악적 문제

아래 index는 저장 JSON의0-based `candidate_reviews`이며 마디 번호가 아니다. 재현 원음표 pitch/음가/타이/원 note snapshot은 `source-context.json`에, 모든 span·member·bass·function·cadence 근거는 각 group JSON에 남아 있다. 원XML/IR를 바꾸지 않는다.

### A. 음을 모두 포함한 큰 화음이 유리해 보이는 함정

Group0 entry116, original selector583: `[262,266)`에 가정 root A♭, ordered members **A♭–C–E♭–G♭–D♭–B♭–F**; `[266,270)`에는 **D♭–F–A♭–C♭**를 가정한다. 미설명 음가0이다. 그러나 뒤 slot의 **C♭은 미관측**이고 앞 slot의7구성음은 span pooling으로만 완전하며 한 순간의 complete core는 없다. 내부 관계도 미선언이다.

따라서 “음 설명량0손실”을 화성 정답으로 선택하면 안 된다. 분산화음 여부는 실제 제시 순서·지속·베이스·NCT와 화음 변화의 경쟁 설명으로 후속 검토한다. 미관측 C♭을 생략했다고 자동 승인하지 않는다. 반대로 simultaneous core가 없다는 이유만으로 가능한 분산화음을 기각하지도 않는다.

### B. 선언한 V7 요구와 큰 화음 후보의 형태 불일치

Group0 entry3, original selector17: 앞의 동일7member 가정에서 뒤 D♭–F–A♭ 3화음으로 가면서 명시 family V7/target quality M을 요청했다. Raw 미설명 음가0이어도 `source_shape_compatible=False`, whole ordinary=False다. 이 **명시 V7 branch**가 성립하지 않는다는 뜻이며 앞 가정의 모든 가능한 기능/확장 해석을 음악적으로 기각한 것은 아니다. Expanded 후보를 모조리 ordinary V7로 해결시킬 수 없다는 panel 한계가 드러난다.

### C. C7 모양 하나로 Half Cadence를 확정하지 않기

Group0 entry45, original selector228: F major라는 명시 key 가정 아래 `[262,270)`의 C–E–G–B♭ 가정이 끝 coordinate270에서 nominal HC 조건을 충족한다. 그러나 local key·structural bass/melody·지각 강세·협화·phrase terminal·performed timing은 미확립이다. 구간 뒤가 관찰되지 않았다고 실제 쉼표/음악 종료로 바꾸지 않는다. **원주석/사람 승인 HC 또는 최종 cadence 검출1건으로 세지 않는다.**

## 무연결 대조군의 해석 — 중요

선택한 bundle `fmilbundle_0906a14efed3e3c256975302`는 `complete_all_lane_witness`이나 **materialized links0인 all-no-link control**이다. 여기서 complete는 모든 raw lane의 연결/비연결 가정을 빠짐없이 선언했다는 뜻이지 실제 성부 진행을 올바르게 연결했다는 뜻이 아니다.

따라서 전체 joint 지원0은 무연결 전제, 명시 shape 요구 불충족 및 미선언 관계를 함께 읽어야 한다. 이를 분석기 실패율100%, 이 악곡에 유효한 진행이 없음, 규칙의 무효 또는 book 이론 적용 실패로 해석하지 않는다. 다음 큰 검토는 같은 원자료의 **실제 링크를 갖는 다른 completion**이며 이번 control 결과를 소급 바꾸지 않는다.

## 보존·동결·한계

| 파일 | SHA256 |
|---|---|
| core | `cc49a6863b509edd820460e422ff374fcf6bab1cb3e87b7efa5849eed483be5f` |
| saved runner | `613ea1ed6ef57eb844f983eb1f9df2a273595a7c304ae9247e4d87ac56da083b` |
| actual pilot | `306d97ed9404c78a1c5c7326d7f7cad721a9f07d82810e28e53de22a1cfefbaa` |
| core tests | `942671ac4ce2ed46ee0d3c775fb82f623dcd1cc6ac2ebaabc8dedeabda40ec4d` |
| reader/runner tests | `ae7d033b3a0d63b1299d429d3e9909f9b39b845822f14d51ce556e9590ab392b` |
| actual report | `d4b721402373fa535f6c74890e46124d85b45ec0777906da0d564d5b6de7698c` |

사용한 두 외부 report pin은 실제 pilot source에 고정했고 root의 독립 관찰 값과 같다. 단계41의 선행61+새4=65code/test SHA는 이번 실행 중/마감의 독립 대조에서 변경0이다. Root 마감 검수는 consumed inputs113 +새 artifact6의119경로 SHA/길이 오류0, terminal report 독립 SHA 일치,5 AST·3 UTF-8문서·188로컬 링크 오류0이다. `git diff --check`는 exit0이며 기존 tracked5개 LF→CRLF 경고만 남았다. 별개 기존 tracked5개 변경을 보존했고 Git push·서버·권한·설정·UI 변경은 하지 않았다.

이번 adapter는 선택된 source1개의 complete clean request를 지원한다. 다수source/partial/held 요청을 조합한 generic review는 명시적으로 미지원이며 성공 prefix로 위장하지 않는다. Read bytes/작업 시간/검사 수는 음악적 정확도나 RSS 보장이 아니다. 출력 한도 또는 late input 검증에 실패하면 partial 파일이 남을 수 있으나 성공 report를 생성하지 않으며 기존 결과를 덮어쓰지 않는다.

## 다음 큰 기능 순서

1. 동일 source의 실제 성부 링크 completion을 같은 근거 축으로 대조하고, 무연결 control과 가능한 해석을 구별한다. 다른 completion의 좋은 역할만 합치지 않는다.
2. 음가 설명 최대값 대신 구성음 제시·베이스/전위·역할 설명·시간 경계·조성/기능의 경쟁 읽기를 함께 쓰는 후보 축소/잠정 제안 정책을 설계한다. Missing fifth/분산/페달/장식음은 각각 근거가 있을 때만 별도 규칙으로 처리한다.
3. Sonata와 다른 편성의 등록 문맥으로 확장하고 추론을 동결한 뒤 원주석을 독립 대조한다. 많은 pair가 아니라 **작품·악장·편성·화음 유형**의 coverage를 보고한다.
4. 근거 충족/보류/대안이 표시되는 악보 레이어와 사용자의 음악적 피드백을 연결한다. 구조 분석/작곡편곡은 검증된 관찰과 조건부 해석의 차이를 유지하여 사용한다.

사용자 의견은 의미 전제가 충돌하는 실제 악보 사례에서 요청한다. 현재 저장 자료의 계정·분모·무연결 전제 검토를 진행하는 데 추가 사용자 판단은 필요하지 않다.
