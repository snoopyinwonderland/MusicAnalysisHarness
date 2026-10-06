# 같은 성부 가정의 화성·비화성음·반주 역할 공동 비교

개발 기록 HARM-DEV-20261001-08 · 2026-10-01. 정본 진입점은 [화성 개발 메인](../README.md)이다. 이 문서는 개발 문서이며 인수인계 문서가 아니다. 연구용 구현·전체 코드 회귀·고정 자료 r1 실행을 완료했다. 조건부 계산과 음악적 검수·운영 적용은 구별하며, 아래에 실제 분모와 보류·보존 결과를 기록한다.

## 목적과 구현 범위

직전의 [일반 문맥·source-clock 연결](2026-10-01-frozen-context-voice-integration.md)은 같은 원음과 성부 연결 제약을 공급했다. 이번에는 그 제약을 실제 음형의 구성음 관계, 준비·해결, 화음 상대 슬롯과 결합한다. 개별 규칙마다 가능한 서로 다른 성부를 합쳐 하나의 해석처럼 설명하지 않는다.

원본 MusicXML/IR/parser/Core schema, 이전 SOURCE/annotation, 기존 실험과 성부 geometry, 운영5173/악보 뷰어/구조 분석을 변경하지 않는다. 모든 새 레코드는 연구용 sidecar이며 화음·성부·NCT·반주 역할을 최종 선택하지 않는다. confidence·음악 정확도·학습·gold·생성 가능성도 승인하지 않는다.

## 네 접점

| 연산 | 입력과 출력 | 보장과 한계 |
|---|---|---|
| `prepare` | 정확한 working IR + mfco 관찰 + lineage audit → `fmview_` | literal closure와 source clock을 재대조. 원 XML의 독립 인증이나 의미 역할 승인 아님 |
| `make_path` / `compile_rules` | 완전한 caller 화음 가정 + view + graph → `fmhp_` / `fmcr_` | 관측과 구성음/근음 가정을 분리. 직접 연결 조건·대안·부족한 전제 보존 |
| `solve_joint` | 명시적으로 요청한 규칙들의 OR 절 → `fmjs_` | 같은 branch 안의 required/forbidden을 함께 검사. witness union·OR count 합산 금지 |
| `compare_under_completion` | 여러 완전 path + 단 하나의 graph/query/witness → `fmcmp_` | 동일 시간 셀의 all-part 음가·조건부 설명·미설명·미지원과 상대 슬롯 대조. 최종 승자 없음 |

새 관찰을 old SOURCE schema로 위장하지 않고 `vfcompletion`을 legacy assignment 목록에 삽입하지 않는다. record seal은 내부 내용의 일관성이고 원자료의 권위가 아니다. 공개 replay validator와 runner의 exact byte hash·inventory를 함께 사용한다.

## 규칙의 첫 범위

- **경과/보조:** 연속된 실제 sound `x→y→z`의 두 direct edge를 함께 요구한다. 철자상 2도와 정확한 음높이 방향, 화음 가정 아래 `member/nonmember/member`, 필요한 full extent와 clock guard를 검사한다. 가운데 음의 해당 음가만 조건부 설명 후보로 둔다. 반음계 동일음명·microtone의 미구현 해석은 정수로 반올림하지 않고 보류한다.
- **지속 선행음:** 같은 sound가 실제 화음 가정 경계를 넘는 `nonmember→member`를 검사한다. 없는 재타격 edge를 만들지 않는다.
- **재타격 선행음:** 같은 철자/옥타브의 실제 release→attack direct edge와 양쪽 membership을 요구한다. sustain/tie와 구별한다.
- **준비된 하행 계류 후보:** 실제 held sound의 준비·경계 이후 비구성음·하행 해결·direct edge를 보존한다. 구성음은 곧 협화음이 아니므로 accent/preparation consonance/dissonance/resolution consonance가 미확인인 초기 후보는 보류하고 NCT 음가를 면제하지 않는다.
- **분산형:** 한 화음 가정에서 세 개 이상 순차 공격/서로 다른 철자의 구성음을 잇는 direct chain을 조건부 형태 후보로 둔다. 화음 구성 선율/분산반주/다른 질감의 대안을 남기며 arpeggio를 확정하지 않는다. 비구성음 음가를 이 형태만으로 면제하지 않는다.
- **지속 베이스 형태:** 지속 sound의 segment별 membership/상대 도수를 보존한다. 실제 최저음·내성/상성부 지속·structural bass·pedal은 다르며 낮은 음 하나로 역할을 고정하지 않는다.

키·기능·secondary·cadence 가정이 없으면 해당 축을 미평가로 둔다. 그 공백 때문에 다른 literal/형태 관찰을 삭제하지 않는다. 준비음이나 full sound extent가 창 밖이면 몰래 외부 화성을 채우지 않는다. 원 후보의 meter/silence/기타 blocker도 유지한다.

## 공동 가능성과 설명량

한 규칙의 링크 대안은 OR이고 대안 내부는 AND/NOT이다. 여러 요청 규칙은 하나의 branch에서 AND로 결합한다. 예를 들어 `a→b`와 `a→c`는 각각 존재할 수 있지만 같은 부분 대응에서 함께 성립할 수 없으므로 branch 충돌로 기록한다. OR 대안을 전부 required로 바꾸지 않는다. 직접 `a→c`가 없다는 것은 `a→b→c`라는 같은 track 가능성의 부재가 아니다.

조건 질의의 completion은 required-only sparse witness이며 선호되는 실제 성부가 아니다. no-link baseline과 각 clause witness에서 **모든 비교 path를 같은 witness로** 다시 계산한다. 다른 witness의 음가 설명을 합치지 않는다. 요청 subset은 명시적이며 규칙 inventory 전체를 자동 정답 집합으로 요구하지 않는다.

공통 셀은 실제 attack/release, 모든 path 경계, 설명 span을 정확한 Fraction 좌표로 함께 세분한다. `(sound ID, 셀 span)`마다 실제 음가를 한 번만 집계한다. 같은 셀의 여러 설명은 refs로 보존하고 시간을 중복 가산하지 않는다. raw assumed membership과 qualified accounting은 별도다.

all-part 음가와 sampled raw-lane geometry 음가는 다른 분모다. 다른 lane의 연결을 현재 witness로 추정하지 않는다. full-source guard가 실패한 sound는 해당 음가의 의미 자격을 보류하지만 다른 lane의 literal membership까지 틀렸다고 주장하지 않는다. point/grace는 보존하며 performed timing을 발명하지 않는다.

각 슬롯은 원 source note snapshots, onset/duration/옥타브/타이/attack·raw lane을 유지하고 explicit root 아래의 철자 상대 음도만 덧붙인다. `written root-relative`를 concert pitch·국소 조성·기능·협화 관계로 바꾸지 않는다. 이는 작곡/편곡 실현을 위한 실마리이지 generation-ready 패턴이 아니다.

## 실제 자료 실험의 설계

완료·보호된 frozen voice baseline 및 lineage sidecar의 **33악보파일/322관찰/1,013raw lane 전체**를 입력 분모로 유지한다. 역사적 주석/alignment 의존 cohort이며 독립 holdout이나 annotation-independent 전곡 평가는 아니다. 원 주석 라벨을 추론에 넣지 않는다.

기존 stored lattice의 모든 complete hold reading과 각 cut의 모든 두-segment 후보 조합을 named group으로 구성한다. 원 후보 origin/근음·구성음·blocker·미표기 후보를 보존한다. 같은 화음을 인위적으로 두 segment로 자르는 모든 hold의 control도 만든다. 이 실험은 multicut 전곡 탐색 전체가 아니다.

예산은 path group, comparison pairs, 전체 clause witness 목록, 같은 path의 전체 rule-pair 목록, compiler inventory, OR branch/query work를 각각 구별한다. 한도를 넘는 named group/목록 전체를 보류하며 유리한 첫 몇 후보로 대체하지 않는다. 비교를 완료했다는 것은 조건부 계산이며 기존 화성 단계 보류나 source gate를 승격하지 않는다. 단일/쌍 clause 검사는 모든 음악 규칙 subset의 전수 평가가 아니다.

새 view는 bounded literal projection과 audit를 대조하고 이미 완료된 과거 producer/selector를 재실행하지 않는다. 동일 전곡 Core schema를 문맥마다 반복 검사했던 이전 비용을 줄이되, protected baseline과 working IR content binding·fresh source clock 검사를 유지한다. intrinsic view 검증은 **호출자가 주장한 seal이 아니라 실제 전체 직렬화 bytes + 현재 Core schema bytes/SHA**를 key로 하는 양성 결과만 최대32개 재사용한다. 원 IR/관찰/audit를 명시한 공개 replay는 매번 새 `prepare`와 대조한다. 변조/재봉인/실패/schema 변경은 재사용하지 않는다. literal schema validator도 현재 schema bytes에 묶었다. 경로/규칙/query/completion/accounting 검증을 생략하는 공개 옵션은 없다.

## 파일과 검증 기록

새 모듈은 `factor_musical_view.py`, `factor_musical_rules.py`, `factor_musical_joint.py`, `factor_musical_trial.py`와 대응 테스트 네 파일이다. 계약은 closed/versioned Python validators와 exact replay로 검사한다. 기존 production schema를 변경하지 않는다.

초기 runner fixture에서 저장 unit wrapper를 factor graph 자체로 잘못 넘겨 `invalid_record_seal`을 확인했다. wrapper의 원 SHA 대조와 내부 `unit.graph` 전달을 분리해 보완했다. 초기 runner 9개 검사 재실행은 통과했다. 실제 데이터 실패나 화성 오판으로 집계하지 않는다. 각 origin을 segment ID에 묶어 동일 구성음의 다른 공급기 출처를 삭제/중복 path 오류로 바꾸지 않는 계약도 보완했다.

초기 compiler fixture16오류는 실제 score duration3q인데 시험 context4q를 요구한 fixture 오류였다. parser의 score duration 계산을 바꾸지 않고 시험용 다른 part의 실제 sound를4q까지 유지해 교정했다. literal declared sounding duration과 span 차이를 혼동한 슬롯은 원 declared value와 별도 `span_duration`으로 분리하고 declared9q/span2q 반례를 보류로 검사했다. 같은 path의 규칙쌍 예산은 전체 combinations를 메모리에 만든 뒤가 아니라 조합 수 계산 직후 먼저 검사한다.

실제 저장 자료의 첫 문맥 in-memory pilot은 view 준비0.631초, hold31개와 같은 구성음 split control31개를 한 raw lane에서 대조24.508초였다. 전체322문맥/1,013lane 완료 수치가 아니며 음악 정답률도 아니다. 이 비용을 근거로 위 exact-content 검증 memo를 추가했다. 예산을 늘리거나 후보/원음표를 일부만 남기지 않았다.

memo 이후 같은 첫 문맥의 독립 in-memory pilot은 보호입력 확인4.754초/view1.328초/pathgroups0.406초/동일lane 대조1.794초였다. 62compiled paths/124보류 shape rules/단 하나 no-link comparison/62accounts/1,891deltas/744items이며, 이 lane에 eligible clause/joint pair는0개다. 산술·출처·동일 구성음control 확인이지 조건부NCT 양성 검증으로 보고하지 않는다. 시간 차이는 비동시 smoke 측정이며 전 실행 성능 보장은 아니다.

사전 lattice 재고 검사에서 원래 plan이 없는28문맥을 확인했다. 예전 baseline 보류를 새 lattice로 발명하지 않고 `withheld_stored_lattice_no_plan`과 원payload·unknown planned count를 남긴다. ready인데 plan이 없는 입력은 오류다. 내부cut1,216groups 중128path 초과843/철자path0개182/범위내191이며, 합계876,714개의 계획 조합은 실행/음악 정답 수가 아니다.

독립 읽기 전용 전체 workload 재고(38.457초)는 기본 예산에서 hold165/cut124의 named groups가 comparison까지 가능함을 확인했다. 같은33파일의19작품군이 포함되고 ready lane을 곱하면754 group×lane, baseline accounts37,920/deltas1,103,835이다. hold125/cut67은 comparison pair 한도 때문에 전체 보류하며, hold path 한도1/빈3/plan없음28도 별도다. clause witness 수에 따른 실제 계산량은 실행 뒤 집계한다. 이 재고를 실제 실행 완료나 음악적 coverage 인증으로 대체하지 않는다.

unit의 `conditional_calculation_complete`는 처리 루프 완료이며, 그 안에 예산 보류group이 있을 수 있다. 모든 group/path를 분석했다는 의미가 아니다. group·compiler·clause/joint pair의 보류는 각각 기록한다.

전체 회귀·독립 검토·실제 run의 결과와 추가 수정 이력은 아래에 이어 기록한다. 사전 재고·pilot 수치와 완료한 r1의 실제 집계를 구별한다.

첫 전체Python 회귀는2,800개/194.871초 중1fixture 오류(`unsafe_integration_report`)였다. 새 runner의 출처 guard를 병행 편집하던 중 기존 fixture 실행의 current-code hash 보호가 변경을 감지한 것으로 추정한다. 기존 protected producer를 수정하거나 guard를 완화하지 않고 새 소스 전부 동결 뒤 전체를 재실행했다. 이 실패를 실제 악보의 화성 오류나 통과로 보고하지 않는다. 동결 후 재현 여부와 최종 결과는 아래에 따로 기록했다.

독립 검토에서 기존 단위의 payload SHA만 맞아도 잘못 재봉인된 parent metadata를 복사할 수 있는 공백을 확인했다. lineage 입력은 child를 등록하기 **전** 보호 baseline hash 집합과 정확히 일치해야 한다. `context keys/lane count/plan version/no-reexecution`도 검사한다. observation/audit/unit의 canonical artifact 위치·byte SHA·record refs·구간/성부·null eligibility, 원geometry/status/reasons/probe inventory·최종/단계별 원상태와 `parent._gate` 전체 결과를 함께 대조한다. 단지 새 hash로 parent manifest를 다시 봉인한 입력도 차단하는 반례를 추가했다. context 결과에도 `original_final_status`를 명시 보존한다. protected producer의 전곡 Core 재검사나 옛 분석 재실행으로 돌아가지 않는다.

최종 단독focused 검사: common view25/rules21/joint32개(합계78개/6.141초), 출처 guard 추가 후 runner17개/34.575초 통과. source/code/schema 동결 뒤 실제 r1과 전체 회귀를 완료했다. 실제 실행 전 보호입력3,036개/33package/322context/1,013lane 연결을 확인했다.

소스 동결 후 전체Python **2,806개/228.111초/OK**. 앞의1fixture 오류는 재현되지 않았다. 신규95개 검사와 기존2,711개를 포함하는 코드/보존 회귀이며, 악곡 수·사람 검수·음악 정답률로 세지 않는다. 실행 전 12변경 파일의 strict UTF-8/replacement/NUL/trailing-space 검사 및4문서105상대링크, scoped `git diff --check`도 통과했다. 최종 결과와 원상태/다음 단계 표현을 갱신한 뒤 **12파일/4문서110로컬링크/문자·NUL·trailing-space/scoped diff 검사도 이슈0**이다. 실제 음악 자료 집계는 아래 별도다.

### 실제 r1 완료와 보존 결과

[최종 report](../../../output/factor-conditioned-musical-meaning-2026-10-01-r1/report.json), [context index](../../../output/factor-conditioned-musical-meaning-2026-10-01-r1/context-index.json), [unit index](../../../output/factor-conditioned-musical-meaning-2026-10-01-r1/unit-index.json)를 함께 보관한다. r1은 **2,193.954초 / exit0 / complete=true / 계산 오류0**이다. `complete=true`는 선언된 범위의 처리·보류·저장·보존 검사 완료이며 음악적 해석을 모두 확정했다는 뜻이 아니다.

| 분모·상태 | 실제 결과 | 해석 |
|---|---|---|
| 작품군 / 악보 파일 / 관찰 구간 / raw lane | 19 / 33 / 322 / 1,013 | 기존 cohort 전체 유지. 완전한33작품을 전곡 분석하거나 독립 holdout을 평가한 수치가 아님 |
| unit 처리 | conditional calculation942 / geometry 보류71 | 처리 완료 unit 안에도 group별 보류가 존재. 원geometry942ready/71abstention 불변 |
| 실제 group 비교가 존재하는 범위 | 170구간 / 450unit | 563unit은 모든 group 보류.322구간 전부가 화성 비교에 성공했다는 뜻이 아님 |
| group×lane inventory | 4,976 | 같은 구간의 hold/cut 후보군을 성부별로 계산한 수. 독립 음악 사례 수가 아님 |
| 실제 비교한 group×lane | 754 | 같은 completion으로 모든 해당 path를 대조 |
| path 한도 / comparison pair 한도 | 2,730 / 609 | named group 전체 보류. 첫 후보만 골라 통과시키지 않음 |
| geometry 보류 / complete spelled path 없음 / 원plan 없음 | 267 / 548 / 68 | 원문맥·후보·보류 사유 유지. 원plan 없는28문맥이 성부별68group으로 나타남 |
| 원 source gate | 일치926 / positive 없음40 / point 미평가31 / source-clock 보류16 | 기존 full-chain/attack-origin 진단 그대로. 일치는 의미 해석 승인 아님 |
| 원입력 / 현재 code·schema / 새 등록 artifact | 3,036 / 289 / 1,338+report | exact SHA·inventory 불변. report를 포함한 새 파일 총1,339개 |
| 사람 검수 / training / gold / generation-ready | 0 / 0 / 0 / 0 | 자동 승자·confidence·운영5173/구조 분석 승격 없음 |

별도 읽기 전용 보존성 감사는322context/1,013lane의 exact key, literal closure·IR/revision/source snapshot, 원최종/단계 상태·원geometry/parent gate, 모든 과거 부모 inventory를 대조했다. 새 artifact의 최초읽기SHA와 생성시 등록SHA·최종SHA도 모두 일치했고 이슈0이다. baseline1,338+report와 lineage325+report, integration/breadth/replay의 과거 결과는 수정하지 않았다. final report SHA는 `d8c7b1d3f77373f0a4522e4d4c779d7a17f328a5494021b3b11b535f642d2ed7`이다.

### 같은 completion의 실제 회계

독립 회계 감사는1,013unit 전체의754완료group과4,222보류group, **1,110비교 / 57,009path accounts / 674,565sound-cell 회계instances / 1,671,603경쟁path delta**를 대조했다. 각 account 내부의 `(sound, cell)`는 한 번만 세며, 서로 다른 후보/성부/query의 반복 계산을 서로 다른 음악 사례로 부르지 않는다. 674,565는 원악보의 서로 다른 음표 수가 아니다. 같은 구성음 split control16,789건에서 raw membership·조건부 음가가 모두 불변이었다.

1,110비교는754기본 비교+356추가 clause 비교다. 실제 연결을 기준으로 no-link785 / positive-link325로 구별한다. 추가 clause 중31개는 no-link completion이므로 같은 geometry가 다시 나온 것이지 독립 음악적 지지가 늘어난 것이 아니다. same-completion은 **한 비교의 모든 path에 같은 query/witness를 적용**한다는 뜻이며, 별도 query의 결과를 하나의 성부로 합친다는 뜻이 아니다.

완료한754groups **내부**의 예산/질의 재고도 별도로 전수 대조했다. compiler37,920records 전부 inventory `ready`(whole-candidate budget 보류0), clause356개 모두 exact comparison(절 한도 보류0), joint pairs2,122개 모두 평가(규칙쌍·branch/query 예산 보류0)다. 이는 앞의4,222개 **외부 group 보류**를 없앤 결과가 아니다. compiler `ready`는 후보 목록의 완결성이며 화성/NCT 정답 인증이 아니다.

계획된 고유 직접 조건절 없음515groups / 있음239groups다. empty-links 절도 '있음'에 포함한다. 239중 nonempty 절 포함213 / empty-only26이며, empty 포함31중5groups는 두 종류가 함께 있다. 최대절9개, joint pairs가 있는group60 / 없는694(최대190쌍)이고, non-exact/held 단일 절query probe는0이다. 이런 null/zero/empty 구별을 양성 음악 증거나 분석 성공률로 바꾸지 않는다.

conditional explained 음가가0보다 큰 account는3,520개/89unit/62구간이다. 실제 group을 비교한 나머지361unit/108구간은 설명 credit0이며, 비화성음이 없거나 화성 분석이 정확하다고 단정하지 않는다. 이는 필요한 direct links가 동일 completion에서 성립한 특정 path 아래의 조건부 설명이며 독립 비화성음 정답3,520개가 아니다. all-part 총음가와 sampled lane 분모, 원 source/tie/attack/declared duration/full extent/근음 상대 슬롯을 따로 보존했다.

컴파일된 후보의 상태는 아래와 같다. 서로 다른 path/control/성부/구간에서 동일 음형이 중복 등장할 수 있다. `conditional_shape`는 shape와 명시 전제가 준비됐다는 상태이지 실제 선택된 성부나 음악적 역할의 최종 인증이 아니다. 실제 query와 공동 조건 검사, 설명 시간은 별도다.

| 규칙군 | conditional shape instances | withheld instances |
|---|---:|---:|
| passing | 1,169 | 3,472 |
| neighbor | 1,420 | 2,989 |
| anticipation held | 335 | 3,989 |
| anticipation reattack | 145 | 12,725 |
| broken-chord shape | 1,266 | 42,932 |
| held-bass shape | 1,794 | 2,530 |
| prepared held suspension | 0 | 1,468 |
| passing/neighbor unsupported | 0 | 35,140 |
| chromatic passing | 0 | 8 |

반복 path/completion의 원 후보111,382instances를 추상적인 음악 규칙111,382종류라고 부르지 않는다. 다음은 실제 comparison의 동일 completion 아래에서 조건이 성립한 shape assessment의 추가 대조다. 고유 키도 `path + completion + rule`에 묶인 계산 신원이지 독립적인 음형 정답 신원이 아니다.

| 조건 성립 shape | assessment instances | 고유(path, completion, rule) | 등장 관찰 구간 |
|---|---:|---:|---:|
| passing | 1,169 | 1,169 | 32 |
| neighbor | 1,420 | 1,420 | 27 |
| broken-chord shape | 1,266 | 1,266 | 94 |
| held-bass shape | 3,869 | 2,075 | 23 |
| anticipation held | 794 | 459 | 12 |
| anticipation reattack | 145 | 145 | 5 |

설명 credit가 있는 item-family 연관instances는 passing1,169 / neighbor1,468 / held anticipation1,292 / reattack277이다. family refs가 중첩할 수 있으므로 이 수들을 서로 더해 음가·고유음표·정답 수를 만들지 않는다. broken-chord/held-bass의 설명 credit는0이며 이들은 구성음/지속의 **역할 형태 후보**일 뿐 NCT 면제 규칙이 아니다. 계류 assessment2,815와 chromatic passing8은 전부 보류다. 후보1,468개와 comparison에서 반복된 계류assessment2,815개를 혼동하지 않는다.

같은 path의 명시적 규칙쌍은 공동 가능1,043/제약충돌1,079이다. 충돌은 해당 요청들이 한 성부 completion 안에서 동시에 성립할 수 없다는 것이며 음악적 해석 전체의 기각이 아니다. 계류의 accent/협화 전제는 계속 보류하고 broken-chord/held-bass shape만으로 비구성음 음가를 면제하거나 pedal/반주 역할을 확정하지 않는다.

독립 공개 fresh replay도 no-link62paths(1.484초), 실제 positive shape76paths(1.205초), positive explained44paths(1.173초)에서 통과했다. joint solution도 대표 incompatible0.003초/possible0.005초의 fresh검사 통과. 전체2,122쌍의 요청rules/AND·OR 대안/required edge를 하나의 query/witness에 대조하고 독립witness/count 합산이 없음을 확인했다. 전체 저장 회계/직접조건 대조와 세 대표 비교·두 대표 joint solution의 새 replay를 구별한다. 이것은 모든비교를 공개 replay로 다시 실행했다거나 원XML·음악정답을 독립 인증했다는 뜻이 아니다.

### 재현 명령

workspace `K:/Music Analysis`, 로컬 `.venv` Python을 사용한다. output은 존재하지 않는 새 직계 디렉터리여야 한다. 아래 r1 이름은 이미 완료한 보존 결과이므로 재실행 시 새 이름을 사용한다.

```powershell
$env:PYTHONPATH='K:/Music Analysis/src;K:/Music Analysis/tests'
$env:PYTHONIOENCODING='utf-8'
& '.venv/Scripts/python.exe' -m unittest discover -s tests -q
& '.venv/Scripts/python.exe' -m musicanote_harness.factor_musical_trial --baseline 'output/frozen-context-voice-2026-10-01-r1' --lineage 'output/frozen-context-sound-lineage-2026-10-01-r1' --output 'output/factor-conditioned-musical-meaning-2026-10-01-r1'
```

`run-plan.json`에는 입력/code SHA와 예산, 각 context gzip에는 원음표·음가·원lattice/origin/pitch policy, 각 unit gzip에는 parent gate/compiled rules/같은 completion 비교/보류·실패가 들어간다. 완료한 `context-index.json`, `unit-index.json`, `report.json`은 최종분모·실제집계·보존검사를 연결한다. 최종report 없는 부분 실행을 완료로 읽지 않는다. 원 XML 독립 인증과 음악적 검수는 이 저장 검사와 별개다.

### 실제 자료의 조건부 설명 예

독립 읽기 전용 감사에서 추출했다. 아래 화음은 **명시적으로 공급한 경쟁 가정**이며 정답으로 선택된 화음이 아니다. 음가를 고치거나 음표를 삭제하지 않는다. 같은 path의 no-link completion에서는 비구성음을 설명하지 않으며, 필요한 direct edges가 같은 completion에서 성립할 때만 조건부 설명으로 옮긴다. raw membership 시간은 두 경우 모두 그대로다. 두 사례의 item/rule blocker는 없고 source-clock/원철자 guard는 통과했지만 key/function/cadence 및 accent/consonance는 미평가다.

| 자료·표시 마디 | 원음형과 화음 가정 | 조건부로 설명할 가운데 음 | 시간 보존 |
|---|---|---|---|
| Beethoven quartet Op.18-1 1악장 m109 | G5→F5→E5, 각1/4quarter(16분음표); C근음/C–E–G구성음 가정 | F5, passing 형태; `[325¾,326)`q | raw nonmember1/4q 불변, conditional explained1/4q; 구성음7/2q, all-part 합15/4q |
| Beethoven sonata No.2 2악장 m51 | G4→F♯4→G4, 각1/4quarter; G근음/G–B–D구성음 가정 | F♯4, neighbor 형태; `[152½,152¾)`q | raw nonmember1/4q 불변, conditional explained1/4q; 구성음5/4q, all-part 합3/2q |

총합은 동시에 소리 나는 모든 sound의 **note-time**이고 구간 wall-time이나 악곡 길이가 아니다. 가운데 음의 full extent와 여기서 설명한 clip은 두 사례 모두 일치한다. 표시 마디/작품명은 기록 설명용이며 계산 조건식에 사용하지 않는다. 독립 음악적 검수/학습/생성 승인은0이다.

- 첫 사례: context `dcml:beethoven-quartets:n01op18-1_01 / plan1476 / cont_4bea6b9587e22b750aca`, lane `part_0e5af16c2b85 / voice_a970907f9e3d`. [저장 단위](../../../output/factor-conditioned-musical-meaning-2026-10-01-r1/units/17027c510ee561b9c2ceac97.json.gz), view `fmview_b4335d6d9741ad301c1f86b5`, path `fmhp_731665f08fdf55bb08c5301b`, query `vfquery_4e45e4ec799eaaa30e37f427`, witness `vfwitness_8fe263c62dd924cdfb41aa73`, completion `vfcompletion_6d6675a3f0a6e18595f03c45`. 함께 요구하는 연결은 `sound_d3283f58058f→sound_8a1944293e0b→sound_55ec3a1e9f1d`이다.
- 둘째 사례: context `dcml:beethoven-sonatas:02-2 / plan631 / cont_606837f5bb53603cbf81`, lane `part_213ec9c5e8cb / voice_20dfa2c93bb1`. [저장 단위](../../../output/factor-conditioned-musical-meaning-2026-10-01-r1/units/2a53a1a5ae4f6114eab0319c.json.gz), view `fmview_42d91201d544edbd912d6796`, path `fmhp_2a7c809302093230be69efab`, query `vfquery_a3a49173d78502b3e2493af9`, witness `vfwitness_6a21e7f849617ee99f85cd2b`, completion `vfcompletion_32223d1fcb3320aaa94a241c`. 함께 요구하는 연결은 `sound_9057f0ccab17→sound_e6b508d4a90a→sound_f5b9200d66df`이다.

## 다음 기능

조건부 shape/accounting의 실제 지지·충돌·보류를 검토하고 필요한 사례를 전체 악보에 재현한다. 다음 큰 기능은 **명시적 조성/기능 가정 → 같은 completion의 실제 해결 → 경쟁 진행·종지 근거**를 한 번에 연결하는 것이다. 아래는 독립 코드 검토의 설계 권고이고 이번에 구현/성공했다고 집계하지 않는다.

1. **조성/기능 가정 overlay:** tonic 철자·major/minor·명시적 scale-form 정책 또는 unknown을 별도 key span으로 저장하고 view/path/segment/정확한 `[start,end)`에 묶는다. 조표나 원RN 라벨에서 key를 강제하지 않는다. primary/applied/parallel target은 경쟁 가정이다.
2. **해결 의무의 공동 검사:** V/V7/vii/vii7/viiø7의 철자 형태와 실제 이끎음/7음의 endpoint·음정/옥타브·target onset 신원/시간을 분리한다. 상행 이끎음(+1반음/+1음명단계), 하행7음(−1/−2반음/−1음명단계), 지연 carry와 기존NCT 조건을 같은 completion에서 함께 요구한다. 여러 raw lane이 필요하면 동일 view/path/context에 묶인 서로 겹치지 않는 graph/query/witness의 completion bundle을 명시하며 독립 witness의 합집합으로 정답을 만들지 않는다.
3. **진행별 근거 vector:** 구성음·target 관측·critical motion·관측 최저/최고음·기보 박절·지속/종결 단서를 따로 비교한다. raw 음가와 미해결/문맥 밖/blocked/source/grace 전제를 그대로 유지한다. cadential-profile compatibility는 근거이며 PAC/HC/전조 확정이나 confidence가 아니다.

현재 common view/path/Fraction·factor 질의·joint 절/accounting과 old 모듈의 **순수 철자/도수/박절 helper**를 재사용할 수 있다. old `progression_resolution/analyze`, `resolution_constraints/analyze`, `voice_links`, `distributed/analyze` 진입점은 legacy assignment/독립 full-IR 링크 가정에 의존하므로 그대로 재호출하지 않는다. 예전 integer pitch helper는 분모1을 확인하고 사용하며 `int(f(...))`로 microtone을 절삭하지 않는다.

기보 metric coordinate는 지각 accent가 아니고 chord membership은 협화음이 아니다. 협화 판단은 explicit bass/interval·style policy, cadence는 독립 closure/후속 진행 범위·구조적 선율/베이스 가정이 더 필요하다. home I가 V/IV 형태도 될 수 있음, accidental이 mixture/NCT일 수 있음, 독립 이끎음/7음/NCT witness가 충돌함, B4→C4가 상행해결이 아님, 누적 target음이 정확 경계신원을 인증하지 않음, 내부 V 도착이 HC를 증명하지 않음,6/4의 구성음이 곧 협화 전제가 아님을 반례로 검사한다. 미지원은 반증이나 기각이 아니다.

그 뒤 검증된 역할 슬롯의 배치·변형·실현과 독립 평가를 거쳐 구조 분석/작곡·편곡에 소비한다. 이번 prototype 자체로 화음 자동 선택·계류음 확정·분산 반주 생성·운영 화면 개선을 주장하지 않는다.
