# HARM-DEV-20261001-10 — 계산 공유와 작품군별 화음 변화 문맥 검증

진입점은 [화성 개발 메인 문서](../README.md)다. [직전 기능·실제 첫 pilot](2026-10-01-factor-conditioned-functional-resolution.md)을 보존하고 다음 큰 검증 단위를 진행한다. 개발 문서이며 인수인계 문서나 음악 정확도 승인서가 아니다.

## 1. 목적과 상태

후보/조성/음표/대안/보류 근거를 줄이지 않고 동일 계산을 공유한다. 실제 다음 화음이 없는 hold-only pilot의 한계를 넘어, **화음 변화 후보가 준비된 구간**을 여러 작품군에서 검증한다. 새로운 음악적 승자·cadence·NCT 확정, UI/구조 분석/생성기 승격은 이번 단계의 목표가 아니다.

comparator/resolver의 중복 복사 개선과 별도 `factor_functional_batch` 연구용 실행기를 구현하고 소스를 동결했다. 전체 회귀2,940개와 실제 다섯 자료군 batch r1, 두 독립 저장 감사·대표 공개 fresh replay를 완료했다. 직전2,917개 검사와 한 context pilot을 이번 확대 검증 완료로 세지 않는다.

## 2. 원자료의 실제 범위와 미지원 분리

protected frozen parent의 19작품군/33package/322context/1,013raw lane을 그대로 선언한다. source/Roman numeral/사용자 정답이나 계산 양성으로 사례를 선정하지 않는다. cohort 자체가 옛 주석/정렬 자격을 계승한 점은 유지하며 새 independent accuracy holdout이라고 부르지 않는다.

저장 부모 자료의 독립 전수 catalog 감사:

- group 전체1,538 = prepared481 + 원 path한도844 + 철자 진행 없음185 + stored lattice plan 없음28.
- change group1,216 = prepared191 + 원 path한도843 + 철자 진행 없음182. 준비된 change는117context/32package/19family에 있다.
- 새 기본 pair/function guard를 대입하면 prepared change191 중 path-pair한도67/interpretation-pair한도25/정적 guard통과99. 실제 resolution/request 지원은 아직 계산 전이다.
- family별 첫 change-ready context는19context/19package/52raw lane/76group이다. 그 안의 prepared change33개 중14path-pair보류/5interpretation-pair보류/14정적통과. 첫 context에 정적 통과 change가 없는9family도 쉬운 뒤 사례로 바꾸지 않는다.
- 기본5-collection round-robin 범위는5context/15raw lane/16group. prepared change8개 중4정적통과/3path-pair보류/1interpretation-pair보류. quartet/Corelli의 첫 selected change에 계산 보류가 있다는 것은 음악적 변화나 source가 없다는 뜻이 아니다.

이 catalog는 protected parent의 group 가용성과 예산 대입 감사다. 전체322context의 원 XML 음악적 정답·literal IR 재검증이 아니다. 선택 context는 원 IR/observation/audit를 추가 fresh replay한다. 양성/보류 수를 실제 실행 전에 예측하여0 또는 성공으로 저장하지 않는다.

새 실행기의 실제 read-only preflight도 통과했다: 부모 입력 로딩11.782초, 전체322context의 group 재구성210.724초. 선택은 아래와 같으며 검증 결과에 따라 다른 쉬운 구간으로 교체하지 않는다. 숫자는 원 관측 창 ID이며 인쇄 마디 번호가 아니다.

| 자료군 | frozen package / 관측 창 | 원 group 가용성 |
|---|---|---|
| Beethoven quartets | `dcml:beethoven-quartets:n01op18-1_04` /1905 | hold11, change121/121 준비 |
| Beethoven sonatas | `dcml:beethoven-sonatas:01-1` /86 | hold13, change55 준비/143 원한도 보류 |
| Chopin mazurkas | `dcml:chopin-mazurkas:BI105-2op30-2` /36 | hold37, change121/57 준비 |
| Corelli | `dcml:corelli:op01n01a` /174 | hold55, change605/242 원한도 보류/76 준비 |
| Mozart sonatas | `dcml:mozart-sonatas:K280-1` /68 | hold31, change60/42 준비 |

이 표의 hold 수는 동일 구성음 split controls를 포함하기 전 수다. 새 pair/interpretation guard는 별도로 적용한다. 전수 catalog와 선택 proof는 실제 batch-plan에 보존한다.

## 3. 사례 선택·실행 계약

`factor-functional-family-batch-0.1.0`은 전체 cohort runner와 별도다.

1. frozen manifest의 `work_family_id`, `corpus_id`, `collection_id`를 사용한다. 별도 current index로 가족을 재분류하지 않는다. 누락/동일 가족의 복수 collection 모호성은 오류로 둔다.
2. 전체 frozen context 순서를 유지하고 registered parent groups를 `path_groups(view,lattice)`로 재구성한다. index/view refs·원 statuses·pitch policy·lattice SHA/binding을 비교한다.
3. 각 family에서 처음 `status=paths_prepared`, `group_id=change:*`인 context를 후보로 선택한다. 앞서 부적격이었던 context의 원 group/status/planned count를 선택 증명에 남긴다.
4. frozen collection 순서의 round-robin으로 family를 정렬하고 기본 `family_limit=5`를 적용한다. 나머지 family는 `deferred_family_limit`, change-ready가 없는 family는 `no_paths_prepared_change_context`로 남긴다.
5. key-known/clock-pass/geometry-ready/기능 양성/NCT 정답을 선택 필터로 쓰지 않는다. 모두 실행 시의 독립 근거/보류다.
6. 선택 context의 **모든 group·path/control·raw lane·원 gate**를 유지하고 기본 예산을 그대로 사용한다. 유리한 group만 뽑거나 큰 group을 첫 후보로 축소하지 않는다.
7. current/historical full IR·revision·source note/time/tie/measure snapshots·mfco/audit·ready/held graph·query/witness/full registry bundle·가정/평가 snapshots를 저장한다. 사용자 피드백이나 training approval은 발명하지 않는다.
8. 실행된 context packet을 즉시 저장한다. 중단되면 일부 결과를 보존하되 성공 완료 보고서를 만들지 않는다. 재개가 필요하면 새 sibling과 명시적 부모 checkpoint 계약을 사용하며 기존 output을 덮어쓰지 않는다.

전체322/1,013 registry, family decisions/selected/deferred/no-eligible 및 attempted/error/unexecuted를 별도로 집계한다. `batch_complete`는 사전 선택 범위의 계산·보존 무결성이고 `cohort_complete=false`다. family 전체를 시도해도322context 전체를 실행한 것은 아니다. 정확도/G1/반주 생성 완료는 별도다.

## 4. 성능 원인과 공유 원칙

직전 실제62path×5key/3graph 저장 비교의 cold cProfile은174.125초/323,655,442호출, 저장 비교와 exact equality였다. 계측 overhead 때문에 직전 무계측68.219초와 직접 속도 비율을 계산하지 않는다.

관측 병목: deepcopy 누적110.14초, seal74.71초, `_assess_prepared`310회105.41초, resolution compile69.23초/fresh compile66.04초, overlay validation620회24.42초, 기존 lane comparison3회16.01초. 중첩 누적 시간은 합산하지 않는다. `common.ref`는 두 필드 추출이라 병목이 아니다. bounded resolution memo는64MiB 직렬화 retained-byte 한도로128entries 부근에서 꽉 차므로310개 전체를 다시 돌 때 자동 재사용을 기대하면 안 된다.

허용되는 개선은 검증된 한 호출 내부의 path/row/assessment 색인·정확한 시간/차이 공유와, 로컬에서 새로 만든 결과의 불필요한 복사를 줄이는 것이다. caller seal/skip flag를 이유로 부모 검증을 생략하거나 결과를 근사화하지 않는다. 모든 pair와 OR/AND 대안·실패/보류·필드를 유지한다. 저장 출력의 record/byte 동등성 및 public fresh validation·alias/변조 반례를 확인한다.

### 구현과 저장 비교 재검증

- comparator는 lane/account·path/time·overlay/assessment를 호출 내부에서 색인화하고, 새로 소유하는 결과만 불필요한 deepcopy/seal을 제거했다. 첫 실측68.047초는 이전68.219초와 거의 같아 이 변경만의 속도 개선을 주장하지 않는다.
- resolver의 fresh compiler/evaluation builder도 이중 복사를 제거했다. 공개 validator의 fresh replay, 원입력 digest, schema/source/HMAC binding,64MiB memo 한도는 바꾸지 않았다. memo 저장/반환의 alias 격리도 유지한다.
- 최종 cold whole comparison은56.219초, 이전68.219초보다 약17.6% 짧다. 단일 wall-clock 비교이며 CPU 경쟁/cache 등을 격리한 전체 성능 보장은 아니다.138,613,184canonical bytes·47,895전체 pair의 record/bytes가 저장 이전 결과와 완전히 일치, SHA=`10a55eff6746f3f9e0f1322b6b90a4f84f2993aa8a786eaede20c689a376cc43`, 입력 불변.
- 저장 evaluation의42rows/388,055canonical bytes를20회 구성하는 작은 비교는 이전1.813초→0.125초, record 일치. builder만의 계측이며 음악 정확도나 전체 속도가 아니다. 신규 alias/변조/fresh 평가 반례를 포함한 comparison+resolver81검사/24.880초OK.

## 5. 개발 실패·정정과 검사

- 첫 batch 검사15개/20.853초 중1실패/4오류는 옛 synthetic parent fixture의 corpus/collection 메타데이터 누락 때문이다. production의 명시 identity 요구를 완화하거나 보호된 부모를 재작성하지 않았다. integration fixture에서만 별도 synthetic identity adapter를 mock하고 실제 누락/모호성 거부를 단위 검사에 유지했다.
- 두 번째15개/20.892초의2실패는 옛 toy가hold-only라 실제 새 selection이빈 범위를 고른 것을 양성 실행 fixture로 사용한 오류다. test-only selection adapter로 그 intact synthetic context를 명시 실행하고 production change availability는별도 단위 검사로 유지했다.16개/30.326초OK 이후 부모ref/그룹 분모 검사를 추가했다.
- 마지막17개/26.331초의1오류는 resolver source를 다른 에이전트가 수정하는 중 부모 SHA가 바뀐 것이다. input guard를완화하지 않고 소스동결 뒤 전체 회귀로 재검증한다.
- 독립 검토로 catalog observation/audit/target ref를 frozen 부모와 binding하고, 결과 group의전체수/순서/ID/원status/planned paths를 강제했다. 재봉인한 부모 선택 위조·결과 그룹 절단도 거부한다.
- 다른 에이전트는 comparator/resolver 네 파일을 수정했고 root는별도 batch 두 파일을 담당했다. 최종cold 동등성 뒤 네 파일동결을 확인했으며, 최종 회귀·실제 output 생성 중 더 이상 소스를 수정하지 않는다. 병행 편집 중 결과를 최종 승인하지 않는다.
- 동결 후 독립 batch17개/29.684초OK. 두 독립 read-only 검토에서도 catalog/selection/그룹·lane·bundle 분모 및 resolver alias/검증 경계의 차단 문제 없음. 전체 회귀와 실제 출력 감사는 별도로 기록한다.
- 최종 동결 후 전체 Python **2,940검사/320.982초OK**. 직전2,917에 이번23개(batch17/comparison3/resolver3)가 추가됐다. 병행 편집 때 실패한 부모SHA 검사는 동결 후 재현되지 않았다. 악곡 수나 화성 정답 수가 아닌 코드 회귀 수다.

## 6. 재현 명령과 다음 단계

소스 동결·전체 회귀 통과 후 아래 명령의 실제 확대 실행을 완료했다. 독립 출력 감사는 아래에 별도로 기록한다.

```powershell
$env:PYTHONPATH='K:/Music Analysis/src'
$env:PYTHONIOENCODING='utf-8'
./.venv/Scripts/python.exe -m musicanote_harness.factor_functional_batch `
  --baseline output/frozen-context-voice-2026-10-01-r1 `
  --lineage output/frozen-context-sound-lineage-2026-10-01-r1 `
  --musical-meaning output/factor-conditioned-musical-meaning-2026-10-01-r1 `
  --family-limit 5 `
  --output output/factor-functional-family-batch-2026-10-01-r1
```

old outputs/Core/parser/schema/원자료/주석/정책/운영 화면/구조 판단/외부 API/Git은 변경하지 않는다. 실제 phase별 양성·보류·비용을 확인한 뒤 더 넓은 family/change 범위와 기능/cadence 전제를 검증하고 대표 전곡 악보·피드백 연결로 이어간다. source annotation과 교재의 해석은 근거이지 운영 정답을 덮어쓰는 지름길이 아니다.

## 7. 실제 r1 범위·계산 결과

저장 위치: `output/factor-functional-family-batch-2026-10-01-r1`. exit0/전체666.117564초. `batch_complete=true`, `cohort_complete=false`, 원입력/current code·schema/새artifact 불변, 계산오류0. reportSHA=`5919a80ec723b2e81742fa0167bf1032fbb74f2453fce1a49a15e0f71b18b484`.

- 선언은19family/33package/322context/1,013raw lane 그대로다. 실제는5family/5package의 **5context/15raw lane**이며317context/998lane는 미실행,14family는family-limit 대기다.5작품 전곡 화성 평가가 아니다.
- 선택된16group 모두 저장: 공동 비교 완료7, 새path-pair 한도보류4, 원path 한도보류3, 전체interpretation-pair 한도보류2. 첫 후보·쉬운 뒤 구간으로 축소/대체하지 않았다.
- function29,650rows = 조건부 형태55 + 보류29,595. resolution55,180rules = 조건부 해결 형태30 + 보류55,150.
- 준비된joint requests30/solutions30/branches30 모두`joint_possible`. 서로 다른 성부 witness를 합치거나 OR의 미평가 대안을 삭제한 결과가 아니다.
- 비교9/벡터2,195/전체pair differences289,740. bundle 아래 resolution assessments는 조건부 충족30, **해당 bundle에서만 불충족30**, 보류76,870. 불충족을 전역 부재나 화음 기각으로 바꾸지 않는다.
- 최종selected/human validated/training/gold/generation 모두 없음 또는0. 조건부 shape 수는 서로 독립인 음표/화음/작품 수나 정답 수가 아니다. key·화음 path·성부 연결 가정이 충족될 때의 증거이며 cadence 최종 확정도 아니다.

| 자료군 | 전체 group/lane | packet 계산·검증 경과 시간 | 저장 상태 |
|---|---:|---:|---|
| Beethoven quartets | 3/4 | 29.042초 | 오류0, 원3group 보존 |
| Beethoven sonatas | 3/3 | 136.655초 | 오류0, 원3group 보존 |
| Chopin mazurkas | 3/2 | 61.021초 | 오류0, 원3group 보존 |
| Corelli | 4/4 | 0.859초 | 오류0, 모든한도보류도 보존 |
| Mozart sonatas | 3/2 | 195.946초 | 오류0, 원3group 보존 |

Corelli의 짧은 계산 시간은 한도보류에 따른 것이며 음악이 단순하거나 화음 변화가 없다는 뜻이 아니다. packet 시간은 group 계산뿐 아니라 각 selected source/IR/view/audit 준비·검증을 포함하고, 전체666초에는 전수catalog·저장·마지막 불변검사도 포함한다. 단순 합이나 다른 단위의 과거 실행시간으로 전체 속도 개선율을 계산하지 않는다.

## 8. 저장 감사와 다음 기능 판단

두 독립 read-only 감사에서 차단 문제0:

- 보호입력4,379·현재source/schema294개의SHA와전체목록일치. 실행전 private 생성시점대조와plan/먼저저장한packetSHA도일치.
- 등록artifact23+report의전체24파일·생성시점SHA·정확inventory일치. working/historical full IR·revision·literal source음표/마디/유리수시간·원view/observation/audit/group 및원15lane status/reasons/gate불변.
- 원부모전체목록도불변:voice1,339/lineage326/meaning1,339/integration360/breadth393/replay35파일.
- 모든 nested seal·view/path/overlay/graph/query/witness/bundle/vector/pair refs와76,930thin assessment refs가존재하며, 모든report집계가실제5packet과일치한다.
- 선택된15raw lane의geometry14ready/1held·source gate14consistent/1no-positive는원부모그대로다. 빈성부도선택분모에서빠지지않고, 준비된다른성부와일괄기각하지않는다.
- 대표 Sonata의 `change:55` baseline comparison을 공개fresh validator로재계산:43.113초/55paths×5keys=275overlays 통과. caller payload·저장packetSHA불변. 전체289,740쌍을다시계산한것이나음악정답검수라고부르지않는다.

| 자료군 | 조건부 function shape | 조건부 resolution shape |
|---|---:|---:|
| Beethoven quartets | 0 | 0 |
| Beethoven sonatas | 10 | 10 |
| Chopin mazurkas | 20 | 0 |
| Corelli | 0 | 0 |
| Mozart sonatas | 25 | 20 |

같은원음표에여러key/scale-form/path/가정이있으므로표의숫자는독립인화음또는악곡정답수가아니다. source일치도정확한기능/cadence를보장하지않는다. 조건부지원이발견된구간과지원하지못한전제를따로확인한뒤범위를확대한다. 이batch가완료됐다는이유로신뢰도/최종화음/cadence·운영레이어/구조·편곡학습자격을승격하지않는다.

### 실제 음악 근거와 해석의 한계

| 구간 | 관측된 후보 관계·성부 움직임 | 이번 계산의 의미 |
|---|---|---|
| Sonata `change:55` | 감7화음B–D–F–A♭의이끎화음형태→C-minor target, 실제B4→C5 | 2path변형×5key tracks=10조건부형태/해결rules. **실제 연결 한 개**를여러가정에서검사한것 |
| Mozart `change:89/4` | G7형태→C-root target, 실제F5→E5 | C-major target4변형+C-minor1변형×5tracks=25형태. 그중C-major-compatible20rules에만이동근거. **실제 연결 한 개** |
| Chopin `change:33/2` | B-root V/V7형태→E-major/E-minor target | 4형태×5tracks=20관계형태, 실제성부해결을지지하는rule0. 형태만으로해결/secondary를확정하지않음 |

key track은조표관찰에서만든명시적가정이지선택된국소조성이아니다. Sonata는A♭major/Fminor의natural·harmonic·melodic-ascending/unknown, Mozart는Fmajor/Dminor의세형태/unknown, Chopin은Dmajor/Bminor의세형태/unknown을유지한다. 알려진가정의일부형태는applied관계로분류되지만unknown의기능은unassessed다. C-major/minor target대안이나5key tracks를하나의정답으로합치지않는다.

따라서이번resolution30은독립30개해결사례가아니라 **두실제sound-motion을여러진행/조성가정에서조건부설명한30rows**다. PAC/HC 확정(`confirmed`)은모두false이며실제상태는`unassessed_missing_*`다. 음악적종지지지의부재확정이아니고최종key/harmony/NCT/cadence 선택도없다. source주석의정답을계산입력으로재사용하지않는다. 전곡문맥·박절·bass/준비·해결 등추가전제가없는것을확정종지로바꾸지않는다.

다른 전제의 보류도 보존했다. Sonata의관련7음20rows는A♭4/A♭3 sound가 `[53,57)`에지속되고 target `[55,57)` 안의changed-pitch successor가관측되지않아보류다. Chopin의관련이끎음/7음30rows는critical source가source span에없다. 이때`missing_raw_lane_graph`는미관측critical-source placeholder의unbound 진단이지실제두raw lane를삭제한것이아니다. Mozart의25이끎음rows도critical source가없고,C-minor target의5개7음rows는실제E-natural이E♭target구성음이아니라보류다. source cut89/4와실제F5release/E5onset45/2도구별한다. 구조적bass/melody·지각accent·협화·phrase-terminal/연주시간의미확립과continuation≠closure는여전히cadence blocker다. 자료미관측·미구현전제·논리불충족을음악적부재로합치지않는다.

### 재현 가능한 한 실제 사례의 정확 참조

packet은 `contexts/mfco_aac19ba8657a4e7751923446.json.gz`의 Sonata context다. 앞의 case 표에서 사용한86은관측창ID이며마디번호가아니다. 저장된full IR로원악보정보를추적할수있다.

- context key: `dcml:beethoven-sonatas:01-1 / 86 / cont_c746e2edd7221f185acf`, 범위 `[329/6,57)` quarter.
- source segment: `segment_0_3eee19a47e39a91fc5b8dcff`, `[329/6,55)`; target: `segment_1_0881d4292891fc2a89f2e1e6`, `[55,57)`의C–E♭–G 가정. 명시A♭major hypothesis 아래applied 분류이지추정국소조성확정이아니다.
- 같은lane: `part_bbcb44bf9259 / voice_987646557795`. B4: `sound_3cf5468f4a36 / note_72b896ae690d`, `[329/6,55)` → C5: `sound_0ca9fedce095 / note_0ec2bdb4602c`, `[55,56)`.
- 실제source release=destination onset=change time=55. 이음정은diatonic +1/semitone +1이고원clock/written-pitch guard가통과한다. required link는위두sound ID그대로다.
- function `fmfunction_57a318fa99efca3773ab4f23`, rule `fmresolution_46c544ff0c4f76168993abd0`, observation `fmrobs_2b0c3372a468fc43b28cc2da`.
- 공동bundle `fmcmb_25fc6304dc03b63d236ee651` 아래충족,comparison `fmfcmp_ced9e4bfed0507fa26037280`. baseline bundle은이link를충족하지않는다. **baseline의불충족과다른공동branch의조건부가능성**을같이저장하며전역해결실패나자동승자로변환하지않는다.

다음 큰 기능은 **실제 change의 전후 화음·이끎음/7음·비화성음과 조성/종지 전제의 공동 근거 검증**이다. 양성 shape를 다른 악보에서 그대로 정답처럼 복사하지 않는다. 부족한 전제/예산/조옮김·판본 정책은 각 범위에 남기며, 대표 전곡 악보에서 가정·경쟁 해석·원주석을 구별해 보여 주고 이후 피드백과 연결한다.5family 다음 확대에서도 동일 family 순서와 모든 group/lane 보존 계약을 유지한다.

최종 문서 검토에서도 수치/SHA/범위/정확 참조 차단 문제는 없었다. PAC/HC의`confirmed=false`와미평가를지원부재로오해할수있는표현을위처럼정정했다. 관련10source/test/doc 파일의strict UTF-8/NUL/U+FFFD·공백과4문서111상대링크검사오류0. read-only`git diff --check`도통과했으며기존별개tracked파일의LF→CRLF알림만있다. Git을수정하거나그기존파일을변경하지않았다.
