# 완전 진행의 조건부 제안·보류 정책

개발일: 2026-10-02. 단계: HARM-DEV-20261002-27.

## 목적과 적용 범위

직전 [원음표 정렬 경쟁 비교](2026-10-02-native-progression-source-contrasts.md)의 다음 큰 기능 단위다. 설명된 음표 수, 구성음 수, NCT credit 합 또는 cut 수만으로 화음을 선택하지 않고, **명시한 기능 진행의 조건이 같은 출처·조성 가설·전체 성부 연결 안에서 충족되는지** 판단한다.

이번 정책은 제출된 완전 진행에 대한 연구용 조건부 제안/보류 계층이다. 모든 종류의 화음 진행을 최종 해석하는 일반 선택기가 아니다. 특히 `None`인 관계를 자동으로 ordinary dominant resolution으로 만들지 않는다. 현재 positive 제안 범위는 모든 내부 관계가 명시되고 해당 ordinary 전략·원음 근거가 지원되는 제한된 읽기다. 전주나 단일 지속화음, ordinary 관계가 아닌 진행도 음악적으로 가능하지만 이번 positive 제안 계약으로 확정하지 않는다.

원 Canonical Core, XML, 원주석, 이전 후보·역할·900개 경쟁 비교, 운영 분석과 UI는 바꾸지 않는다. 기존 음표 ID·유리수 시간·full sounding span·attack/tie를 참조하며 새 제안·보류만 append-only sidecar에 저장한다.

## 구현과 입력 계약

- 핵심: [`native_progression_policy.py`](../../../src/musicanote_harness/native_progression_policy.py).
- 저장 실행기: [`native_progression_policy_trial.py`](../../../src/musicanote_harness/native_progression_policy_trial.py).
- 공개 핵심 검사: [`test_native_progression_policy.py`](../../../tests/test_native_progression_policy.py).
- 저장 전용 검사: [`test_native_progression_policy_trial.py`](../../../tests/test_native_progression_policy_trial.py).
- 버전: `native-progression-policy-0.1.0`, 저장기 `native-progression-policy-trial-0.1.0`, 규칙 `progression-proposal-hold-rules-0.1.0`.

공개 API는 `evaluate(scope, lattice, contrast, *, bundles, work_budget=2000000)`다. 출력은 `nppolicy_` record이며 저장된 contrast의 원순서대로 모든 entry를 유지한다. `selected`, `rank`, `confidence`는 null이다. 조건부 지원 목록도 유일 승자·최종 화성·Gold가 아니다.

내용 seal은 출처 인증이 아니다. 실행기가 부모의 생성 SHA, 정확 파일 inventory, 원 full IR와 scope/lattice/bundle/panel/batch의 등록 관계를 확인한다. 이 검사는 saved-evidence admission이며 live native session이나 이전 producer의 권한을 재발급하지 않는다. 공급기, native 비교, role predicate, contrast 계산을 재실행하지 않는다.

핵심 내부에서는 결정론적 **관찰·산술·참조 연결**을 다시 확인한다. pitch spelling에 따른 raw membership, slot별 실제 member/누락 목록, full/observed span, attack/tie, source atom/category와 rational account, literal active/equal-lowest bass, 선언한 function shape, axes/joint tri-truth, ordinary occurrence→role OR→whole AND, conditional credit union과 원음가를 검사한다. 이것은 원 역할 predicate의 독립 재추론이나 음악적 정답 검증이 아니다.

## 일반 규칙

기존 [문맥 추론 규칙 R01–R12](../HARMONY_REASONING_RULES.md)와 [불완전3화음의 제한](2026-09-30-incomplete-triads.md)을 적용한다. 작품명·work ID·마디 번호별 조건은 없다.

| 규칙 | 판단과 한계 |
|---|---|
| P01 | source·철자·hypothesis 불명은 보류다. 원음이나 화음의 부재로 바꾸지 않는다. |
| P02 | 명시한 key hypothesis의 좌표가 필요하다. 조표를 확정 조성으로 승격하지 않는다. |
| P03 | guarded 구성음이 빠지면 생략/분산/재배치의 추가 증거가 필요하다. 완전5도 생략 모델이나 미관측7음을 자동 적용하지 않는다. |
| P04 | source/target의 알려진 shape 불일치는 **해당 명시 family/quality 요구**의 불충족이다. 다른 기능·확장·성부 전략까지 금지하지 않는다. |
| P05 | 같은 전체 completion에서 개별 역할뿐 아니라 whole ordinary template·joint 전제를 요구한다. 첫 adverse change를 건너뛰거나 다른 completion에서 해결 링크를 빌리지 않는다. |
| P06 | 관찰된 최저음의 source guard를 확인한다. 시간별 조건부 전위 변화나 비구성음 베이스 자체를 음악적 불가능으로 판정하지 않으며 structural bass/pedal을 확정하지 않는다. |
| P07 | 내부 관계가 없거나 미선언이면 positive 진행 지원을 만들지 않는다. 빈 vector의 vacuous `all=True`를 통과 조건으로 쓰지 않는다. |
| P08 | unexplained 또는 unassessed nonmember 시간은 검토 필요다. NCT 정답으로 바꾸지 않는다. |
| P09 | 같은 ordered root/member signature를 자른 cut은 독립 경계 근거가 필요하다. 자동 삭제·병합이나 화음 변화 확정은 하지 않는다. |
| P10 | key/bundle/**partition/vector**까지 정확히 같은 그룹에서만 fixed-premise 경쟁 대안을 묶는다. 다른 조성·성부 연결·분할·기능 가정을 합쳐 승자를 만들지 않는다. |

strict simultaneous core는 literal evidence로 남지만 positive 경로의 필수 문턱으로 추가하지 않는다. 분산화음은 필요한 구성음이 한 순간에 모두 울리지 않을 수 있기 때문이다. 반대로 pooled member가 모두 보인다는 사실만으로 분산화음·화음 지속을 확정하지도 않는다.

## 상태와 의미

| 상태 | 의미 |
|---|---|
| `conditional_function_supported_alternative` | 제출된 key/completion/partition/vector와 명시한 전략 안에서 필요한 전제가 지원됨. 비서열 잠정 대안이지 최종 화음 선택이 아니다. |
| `held_missing_evidence` | 미관측 구성음, 미상 조성/source, whole ordinary 미지원, 미선언 관계 또는 독립 경계 근거 부족. 해당 화음이 틀렸다는 뜻이 아니다. |
| `not_supported_under_declared_requirements` | 알려진 source/target 형태가 명시한 기능 조건과 불일치. underlying chord나 모든 해석을 기각하지 않는다. |
| `held_whole_request` | 부모 전체 hold·불완전 completion·전체 예산 hold. 모든 제출 refs를 보존하며 부분 평가하지 않는다. |

대표 상태와 **모든 diagnostics**를 함께 저장한다. 알려진 shape 불일치와 unknown key가 동시에 있으면 양쪽 이유를 유지한다. 한 상태가 보류 전제를 숨기지 않는다. 제안이 하나여도 미평가 경쟁자를 제거하거나 unique winner 포인터를 만들지 않는다.

`alternatives`에는 원 native/role/comparison/explanation refs, premises, 상태와 규칙 ID별 이유, cut별 joint/whole/개별 역할, 원 account pointer가 있다. `fixed_premise_groups`는 같은 전제의 alternative index와 지원/보류/요구 불충족 목록만 제공한다. 모든 별도 해석의 원음표·음가·앞뒤 관계는 `parent_contrast_ref`와 원 full IR에서 역추적한다.

## 전체 보류와 자원 계약

- 핵심 최대 제출 entry256, nonnegative integer work budget. bool·음수·float budget 거부.
- 기본 work2,000,000은 변경하지 않았다. work는 logical tree/reference 방문 allowance이며 CPU 시간·메모리·정확도 보장이 아니다.
- 전체 source/lattice/contrast/bundle tree 방문, slot/profile/reference, atom×credit cover 비용을 사전에 합산한다.
- source guard는 한 API call에서 sound별로 한 번 캐시한다. origin별 pure profile도 캐시하고 diagnostics 복사 비용을 별도 charge한다. active cell마다 긴 diagnostics를 다시 훑지 않는다.
- authentic `all_lane_witness_withheld`는 템플릿 누락 오류로 실패시키지 않고 전체 정책 hold로 받는다. sound/role/ref를 favorable prefix로 평가하지 않는다.
- 전체 hold에서 evaluated=0, withheld=제출 수, 그룹/지원/보류/불충족/diagnostics 수는 null이다. 제출 목록은 사라지지 않는다.
- 명시적 empty request는 알려진0이다. 전체 악보 분석 완료가 아니다. `planned_groups=0`도 미상과 구별한다.
- 저장기의 원파일64MiB, decoded파일256MiB, 전체decoded1GiB, 결과파일64MiB 한도와 four-completion/all-entry admission은 별도다. 큰 JSON의 일부만 읽어 완료하지 않는다.

## 검증과 개발 중 교정

핵심 최종41개/32.230초 PASS, 저장 전용19개/66.805초 PASS다. 신규 테스트는 총60개이며 반복 실행이나 이전 단계 테스트를 더하지 않는다. 전 repository 통과 수 또는 음악 정답 수가 아니다.

핵심 tests는 genuine MusicXML→IR/native/role/contrast를 **시험 입력 생성 때**만 만들어 새 정책을 검사한다. 같은 completion의 genuine ordinary 양성1, no-link/adverse-first-change 반례, unknown key, target quality 불일치, 빈/None vector, 추가 cut, cross-completion, rational1/3, tie/재발음, 전체 budget/부모 hold/empty, resealed source/account/shape/template/reference 조작과 guard 캐시 방문을 다룬다. 소비 시 native/role/contrast producer 호출은 금지 mock으로 확인한다.

저장19개는 작은 temporary archive에서 contrast와 policy를 명시적으로 mock한 storage-only 검사다. 실제 음악 정확도를 검사하지 않는다. 생성 SHA·등록관계·정확 inventory·all-entry order·closed typed summary·누락/중복/다른 key/completion·parent/code 변화·bounded read·shared-input mutation·전체 hold의 null/0 구별을 검사한다. 기존 TestCase를 상속하거나 기존 전체 suite를 재발견하지 않았다.

개발 중 수정한 항목:

1. 미관측 목록 `None`을 빈 목록처럼 통과시키지 않게 했다. member presentation 전체는 pure literal projection과 exact 대조한다.
2. source atom과 scalar account를 함께 바꿔도 nonmember를 구성음으로 숨기지 못하도록 raw membership/guard/credit union을 연결했다.
3. shape의 origin/철자, axes/joint, native ordinary 전략과 role whole template를 연결했다. 개별 이끎음 True만으로 전체 ordinary False를 덮지 않는다.
4. source 범위를 벗어난 credit, member-time의 부당한 nonmember credit, 미평가 scalar의0/지원 승격을 막았다.
5. actual bass/attack/tie/observed time을 다른 slot에서 빌리지 못하게 했다.
6. source diagnostics 반복 방문 상계와 shared source의 admission-time digest 보호를 추가했다.
7. incomplete test의 처음 budget0 기대는 잘못이었다. fully forced query는 검색 work0에서도 완료될 수 있으므로 genuine impossible self-link로 authentic withheld bundle을 만들었다. 실제 corpus 입력을 바꾼 것이 아니다.
8. 초기 핵심 테스트의 오류는 강화된 validator의 오류 메시지 기대1건 및 위 fixture 기대1건이었다. 초기 저장18검사의 오류2건은 fixture artifact 문자열을 `Path`로 변환하여 고쳤다. 최종 성공 수에 초기/중간 실행을 중복 합산하지 않는다.

독립 음악/계약 검토에서 shape 불일치와 candidate 기각의 구별, literal projection/raw-state/function/ordinary/union 연결, incomplete witness와 진단 방문 상계가 지적되어 수정했다. 최종 읽기 전용 재검토에 추가 차단 결함은 없었다. 이 검토를 새 producer 실행·새 음악 정답 검수로 표현하지 않는다.

## 실제 저장 자료 실행

메타데이터-only admission29.2637953000376초: 22파일/258,951,864decoded bytes, 보호4,763경로, 이전335 code/schema/test와 현재339목록 확인. native/role/contrast/정책 계산과 신규 출력은0이었다. 이후 pure source/contrast 비용 보완 점검0.6668873999733478초에서도 정책 계산/신규 출력0이었다.

최종 사전 planned work는 다음과 같다. 결과를 보고 조건을 낮추거나 일부 그룹만 좋은 예산으로 돌리지 않았다. 네 그룹 모두 동일41,000,000으로 단일 r1을 실행한다. 최대planned40,265,338을 포함하는 실행 한도이며 기본2,000,000을 소급 변경하지 않는다.

| 등록 구간 | completion | planned work |
|---|---|---:|
| Sonata01-1 | no-link control | 40,176,842 |
| Sonata01-1 | actual greedy technical completion | 40,265,338 |
| Quartet | no-link control | 33,987,594 |
| Quartet | actual greedy technical completion | 33,993,859 |

실제 단일 r1은 **63.47109879995696초/PASS**다. 산출물은 [`run-plan.json`](../../../output/progression-proposal-policy-2026-10-02-r1/run-plan.json), [`context-index.json`](../../../output/progression-proposal-policy-2026-10-02-r1/context-index.json), [`report.json`](../../../output/progression-proposal-policy-2026-10-02-r1/report.json) 및4개의 압축 policy record다. 정확7파일/1,162,843bytes이며 계산 실패·전체 policy hold0이다.

| 결과 | 수 |
|---|---:|
| 등록 구간 / 원 raw lanes | 2 / 7 |
| key×completion별 원 대안 그룹 | 20 |
| partition/vector까지 같은 fixed-premise 그룹 | 100 |
| 제출 / 평가된 완전 진행 가정 | 200 / 200 |
| 조건부 strict ordinary 진행 지원 | 0 |
| 증거 부족 보류 | 120 |
| 명시한 기능 요구와 shape 불일치 | 80 |
| 부모의 저장된 pair 비교 | 900, 그대로 보존·재계산0 |

각 completion은50대안/25fixed-premise그룹/30보류/20명시 요구 불충족이다. 이 숫자는 같은 구간의 여러 key/completion/가정을 중복 포함하는 occurrence다. 서로 다른 음악200곡, 정답200개, 실패율40% 또는 정확도 향상을 뜻하지 않는다.

**제안0의 의미:** 실제 화음을 하나도 찾지 못했다는 뜻이 아니다. 이번 기술 panel에는 full-hold/None vector가120개, 명시 ordinary vector가80개 있다. 전자는 모든 관계가 명시·지원되는 엄격한 제안 범위를 충족하지 않으며, 후자는 적어도 한 cut에서 해당 family/target quality의 알려진 shape 요구와 불일치한다. 개별 ordinary/pooled member/NCT 설명을 최종 진행으로 올리지 않았다. 모든 내부 cut에 같은 ordinary 관계를 요청하는 기술 control이 실제 악곡의 여러 진행 종류를 대표하지 못한다는 **제안 패널의 한계**도 드러났다.

대표 진단 occurrence는 미선언 내부 관계120, missing guarded member80, 미상 key40, same-signature cut40, unexplained nonmember time125다. 한 대안에 여러 진단이 있고 어떤 값은 cut/slot occurrence이므로 서로 더해200의 분모로 쓰지 않는다. Quartet actual completion에서는 모든50대안의 unexplained-time 진단이 사라져도 strict 진행 지원0이다. 설명량이 늘어도 function/shape/boundary 전제가 자동 충족되지 않음을 보여 준다.

### 보호와 동결

생성 inputs4,763과 현재339 code/schema/test의 고유4,767경로, 원 phase26정확7/phase25정확148 inventory, 새6artifact를 실행 전후 보호했다. 새 report까지 포함한 creation/input/output union은4,774경로다. 이전 code335에 새4파일을 별도 추가한 것이며, 부모의 당시 code inventory를339로 바꾸지 않았다. `inputs_and_code_unchanged`, `artifacts_unchanged`, `computation_integrity_passed`, `submitted_policy_evaluation_complete`가 모두 true이며 change/failure 배열은 비어 있다. 이는 음악적 정답/전곡 분석 완료가 아닌 제출 정책 평가와 저장 무결성이다.

| 파일 | SHA256 |
|---|---|
| core | `1174d79dd0b0bd362623fae602ea4f754a896cac8959d7d0a46909f7b4323648` |
| runner | `27ea20d7d9e4780f16c7b9cf92ea850ad47afb85a7bb39c39e8ef433f3115ac8` |
| core tests | `ab37a2a99626b3f92d88eff3e35eddfe115895c17b8ecdb6dca87c1302027ca8` |
| storage tests | `31dfa7583e00aaa3b239af15b91fdafd537138e171b4813e920110df54c3cb7c` |
| report | `9e934690bf40e945884c6efc4e4ab23df19f3a2d6fc74046396bac9d8d06f21c` |
| plan | `561950064eb3d54f4e4531fb2a0a310ec7fc3c974409e0e4c0982beaebee2343` |
| index | `971d8fca6c1ff061ed16079ea1a6187488c4aca4586967c580b0dafa11a216e0` |

4개의 정책 ID는 원순서대로 `nppolicy_9043a27e7dd1f9a62fbd765a`, `nppolicy_581d144bd9211a0daf4ad27e`, `nppolicy_881da6ad44eff7b433f8b8c9`, `nppolicy_bf409689278fc7903c9ed2a9`다. 원 full IR/bundle/contrast를 각각 참조한다.

### 실제 사례를 해석하는 방법

- Quartet C3–B♭2–A♭2: B♭을 expanded member로 흡수하는 읽기와 같은 실제 성부 링크의 passing-like 설명을 모두 유지한다. 설명량 동률은 승자 근거가 아니다.
- Sonata C5 재발음: m14 끝 C5와 m15 C5는 tie 하나로 다시 쓰지 않는다. boundary 역할 설명과 실제 bass trade-off를 보되 whole ordinary/진행 제안으로 자동 확대하지 않는다.
- Sonata missing G♭: 미관측 구성음을 생략으로 자동 확정하지 않는다. G4→A♭4의 개별 이끎음 지원, 7음의 첫 변화/연결 문제, actual target shape 불일치와 전체 ordinary 실패를 각각 남긴다.
- Quartet D♭4–F4–A♭4: 실제 동시 triad·literal lowest D♭과 조건부 root-position을 보존한다. 같은 D♭ signature의 다음 cut이나 pooled7member의 전체 설명만으로 진행을 선택하지 않는다.

이 사례는 이전 실제 원음 packet을 같은 refs로 소비한 정책 진단이다. 새 작품별 규칙 또는 독립적인 화성 정답 라벨이 아니다. 상세 원 note/sound ID·음가·앞뒤 범위는 직전 정본과 부모 contrast에 보존되어 있다.

## 저장 결과 감사와 회귀 검증

서로 다른 세 검수의 확인 수는 탐색·산술·참조 assertion 수다. 신규60개 테스트, 실제200대안 또는 음악적 정답 수와 합산하지 않는다. 저장기의 자체 메타데이터 감사와 독립 원음표/계약 검수를 구별한다.

| 검수 | 범위 | 확인 수 / 시간 / 결과 |
|---|---|---|
| 저장기 측 메타데이터 감사 | 27 strict JSON reads/76,400,502decoded bytes. 전체4,774 SHA, 부모/새 inventory, code335/339, 원순서200refs·100fixed groups·20key/completion·cohort·limits·false flags·null winner | 5,156,229 / 13.6882151초 / PASS |
| 독립 저장 atom·계약 감사 | 19파일 pre/post SHA, 7,720source atoms·85conditional union intervals·240내부 cut assessments·1,139diagnostics. raw member/guard/category/union/scalar/group/status 및 원음가85/2·85/2·53/2·53/2 | 512,175 / 4.1037675초 / PASS |
| 독립 음악·source 연결 감사 | 20개 고유 policy/contrast/full IR/scope/lattice/bundle artifact. 200대안·100fixed groups·1,139diagnostics, 네 사례의 pitch/onset/duration/tie/재발음/실제 D♭bass·account pointer | 7,182 / 13.122180299949832초 / PASS |

세 검수 모두 producer/정책 `evaluate` 재실행이나 파일 편집 없이 저장 결과를 대조했다. 읽은 파일의 SHA 변경은0이다. Source shape False는 명시한 기능 branch만 불충족으로 분류하고, missing core·unknown key·ordinary 미지원 보류를 숨기지 않는 것도 확인했다. Sonata D♭5의 실제 attack45/full[45,101/2)/tie4+3/2와 C5의 독립 onset56·57/음가1·1, Quartet의 B♭2 passing-like credit1/2와 same-signature535/2 cut을 보존한다. 이 검수는 화성 정답률 또는 운영 분석 기능의 음악적 승인 검사가 아니다.

Root는 기존 `test_native_progression_contrast` **28개/16.654초 PASS**를 별도로 확인했다. 이는 신규60개에 포함하지 않는 직전 소비 계약의 회귀 검사다. 저장 결과 및 이전 producer는 다시 만들지 않았다.

문서 마감 전 root QA5.1089179초에서4,774보호 SHA 변경0, 새7/부모7·148 inventory 누락·추가0, 현재339code inventory 일치, 새 code/test/docs7파일의 UTF-8·NUL/U+FFFD·행끝 공백과4 AST, 로컬 Markdown 링크141개의 오류0을 확인했다. 이번 감사 기록을 추가한 최종 문서도 같은 검사를 거친다. Read-only `git diff --check`는 exit0이며 기존 별개 tracked5파일의 LF→CRLF 경고와 사용자 수정은 보존한다. Git commit/push는 하지 않았다.

## 한계와 다음 큰 기능

1. 원 322문맥/1,013 raw lanes 중 이번은 **두 등록 구간/7 raw lanes**이며 전곡2개를 완전 분석한 것이 아니다. 미실행320/1,006과 등록pool5, 원 eligible/제안/미제안/native universe를 그대로 보존한다.
2. 일반적인 지속·분산·비ordinary 관계나 생략을 충분히 증명하는 확장 전략은 아직 strict positive 제안에 연결되지 않았다. unsupported strategy는 chord 부재가 아니다.
3. 다음 큰 단위는 **source-grounded 후보와 관계 종류별 진행 제안의 보강**이다. Pooled member 설명이 높은 expanded 후보만 대표로 삼지 않고 ordinary3화음/7화음의 경쟁 읽기도 충분히 제출한다. V7를 모든 cut에 강제하지 않으며 실제 source/target shape에 맞는 기능 전략, 비ordinary·지속·분산·생략의 별도 증거와 보류를 구별한다. 현 gate를 결과에 맞춰 낮추거나 특정 작품 답을 입력하지 않는다. 이후 여러 작품의 실제 양성/반례를 같은 계약으로 검증한다.
4. 독립 음악 검수와 더 넓은 실제 자료가 필요하다. 모호한 사례에만 사람 의견을 요청하며 기존 사용자 사례를 일반 정답으로 과적합하지 않는다.
5. 운영 악보 UI·최종 화성/NCT/key/cadence·학습/Gold·구조 분석·작곡편곡·Git에는 아직 적용하지 않았다. 향후 UI는 conditional proposal과 보류 사유를 함께 표시할 수 있어야 한다.

