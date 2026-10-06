# 손실 없는 화음 형태·목표 화음·조성 관계

개발 항목 `HARM-DEV-20261001-14`. 앞 단계는 [진행 색인](2026-10-01-indexed-hypothesis-universe.md)이며 기존 결과/계약을 바꾸지 않는 새 연구 계층이다. 코드 검사, 실제 계산, 음악적 정확도와 운영 적용을 구별한다.

## 1. 목적과 이번 범위

이전 색인은 22,969개 공급 origin과 1,068,810개의 완전한 논리 진행을 보존하지만 기술 질의의 첫/끝 tuple만 계산했다. 그 기술 표본이 특정 family×quality 형태 전제에서 실패/미확인이라는 관측만으로 전체 universe의 조건부 형태 또는 음악적 정확도를 판단할 수 없다. 이번에는 **모든 공급 origin의 화음 형태/후속 triad-core 호환/명시 조성 투영**을 계산 공유로 표현한다. 원주석의 정답 라벨을 읽거나 후보를 음악적으로 순위화하지 않는다.

일반 규칙은 다음과 같다.

- exact 근음 철자·ordered 구성음·blocker가 같은 입력만 공유한다. PC-set이나 같은 제목으로 origin을 합치지 않는다.
- source 형태 true/false/unknown × target 형태 true/false/unknown의 아홉 분할을 보존한다. mismatch는 해당 형태 전제의 실패이며 화음 후보의 최종 기각이 아니다.
- target은 정확한 철자 근음과 기대 triad core의 포함 여부로 대조한다. 추가 구성음이 있어도 core를 포함할 수 있지만, 이것을 일반 3/7화음의 전위·실제 역할 인증으로 바꾸지 않는다.
- 모든 key 원ID, catalogue origin 수, slot 순서와 terminal 행을 보존한다. `target=None`인 마지막 slot은 앞 slot의 모든 origin 수만큼 반복된다.
- explicit unknown key는 local key가 아니다. shape 전제가 충분한데 조성이 unknown이면 shape 가능성은 남기고 조성 축은 미평가로 둔다.

이번에 **계산하지 않는 축**은 실제 note-time membership/profile, 시점별 bass/전위, 이끎음/7음의 실제 endpoint, 지연/분산 해결, 조건부 NCT의 적용, 동일 성부 completion 아래 motion 및 최종 key/function/cadence다. 기존 계산은 보존하며 다음 단계에서 연결한다. 따라서 이번 shape 양성 수를 실제 화음·secondary·해결·종지 정답 수로 읽으면 안 된다.

## 2. 별도 계약과 공유 구조

[핵심 구현](../../../src/musicanote_harness/factor_function_relations.py)은 `factor-function-relations-0.1.0`, `fmfrel_` 봉인이다. [실행기](../../../src/musicanote_harness/factor_function_relation_trial.py)는 `factor-function-relation-trial-0.1.0`이다. 이전 `fmes/fmeh/fmiidx` source·schema·Core·parser를 변경하지 않는다.

```text
모든 original variant ID → exact semantic type
                                  ↓ type × family × target quality
                          source shape kernel
                            ├─ 목표 triad core → target type join / false·unknown 보완집합
                            └─ explicit key type → key projection
모든 catalogue origin multiplicity → group / slot / key 전체 weighted counts
원 tuple + slot + family + key 질의 → 원 ID/span을 복원한 정확한 function body
```

`origin_inventory`에는 각각의 variant/segment/catalogue/span/profile ref와 supplier pointer, spelling alternative, provenance를 보존한다. `type_inventory`는 span-independent 계산 입력이지 원음표·후보 정체성을 대체하는 새 정답 객체가 아니다. 원 profile ref는 **아직 계산하지 않은 descriptor 참조**로 남는다.

`kernels`는 type당 V/V7/vii/vii7/half-diminished7 × 장/단 target의 열 가지이다. 이 목록은 교재 전체 화음의 구현 완료 목록이 아니라 기존 frozen `_function`의 지원 범위다. `target_relations`는 compatible type 목록과 unresolved 또는 resolved-minus-compatible 보완집합으로 모든 target을 표현한다. source에서 목표 근음 자체를 유도할 수 없으면 **모든 target 형태가 unknown**이며, target 철자 미정만을 unknown으로 한정하지 않는다. 전체 source×target×key나 1억 행을 생성하지 않는다.

`key_projections`는 exact expected source members·derived target root·target quality·key type에 묶여 공유된다. key 원ID 및 reference form별 수를 따로 보존한다. `primary/parallel/applied`는 이 명시 가정 아래의 관계 이름이지 작품의 국소 조성이나 기능을 확정하는 라벨이 아니다.

## 3. 정확 분모와 상태

`path_groups[].function_slots`는 각각 source catalogue, target catalogue 또는 terminal, opposite-slot multiplicity와 다음 수를 갖는다.

- 전체 `logical_function_rows`와 `terminal_target_rows`.
- 아홉 `shape_state_counts`: `TT/TF/TU/FT/FF/FU/UT/UF/UU`.
- `conditional_function_shape/withheld` 수와 key 원ID별 function-kind 수.
- 해당 group이 미확인/전체 한도 보류라면 계산 수는 `null`; known product subtotal과 unknown group 분모는 구별한다.

top-level summary는 논리적으로 표현한 수, weighted shape 계산 수, 아직 미평가인 수, 실제 query 수를 분리한다. known product 0은 빈 group이지 unknown/오류가 아니다. 반대로 공급 catalogue가 없어서 product를 알 수 없으면 0으로 확정하지 않는다. terminal은 실제 후속 화음이 없다는 결론이 아니라 **정해진 group의 후속 slot 미관측**이다.

`max_kernels`는 전체 semantic types×10의 inventory 한도다. 초과 시 kernel/target join/projection 전체를 보류하며 앞부분만 계산하거나 top-k로 줄이지 않는다. 모든 original IDs/분모/보류를 유지한다. key projection의 upper bound, byte/RSS, session lifetime을 이 한도로 보장한다고 주장하지 않는다.

## 4. 출처·입력·저장 보호

핵심 builder는 원 full IR/scope와 frozen catalogue/index의 intrinsic producer lineage를 검증한다. `prepare_relations`는 검증한 **같은 owned copy**에서 immutable 자료와 lookup을 만든다. caller 입력 변경·재봉인 변경·typed 숫자 alias·foreign tuple/key/slot과 current code 변경을 검출한다. opaque session은 외부에서 발행할 수 없고 query는 원 span/segment와 exact ordered target members를 복원한다.

build/prepare의 입력은 호출 동안 불변으로 유지하며 외부 변경과 직렬화해야 한다. before/after SHA와 coherent owned copy는 concurrent transient ABA의 원자적 caller snapshot을 보장하지 않는다. 실제 실행은 같은 입력을 다른 스레드가 변경하지 않는 조건으로 수행한다. 이미 발행된 session은 이후 caller/반환값 변경과 분리된다.

실행기는 indexed r1의 report·artifact creation SHA·정확 파일 목록·선택 문맥·원 group/lane·scope/hypothesis/index counts와 원 prerequisites/family/source/code 계보를 검증한다. saved query/assessment 봉인·참조·정책·분모와 `_function` body를 대조하고, 저장된 고유 actual bundle의 geometry provenance를 검증한다. **기존 profile/motion 전체 재계산 또는 supplier `propose` 재제안은 이번 prerequisite 검사에 포함하지 않는다.** 새 단계의 profile/endpoint/motion/bundle assessment 수는 0이다.

새 출력은 `ROOT/output`의 새 직접 자식에만 생성한다. 원 output을 갱신하지 않고 생성 시 SHA와 종료 시 SHA·목록을 대조한다. 부모 known denominator는 load/build/query 실패보다 먼저 기록하여 실패가 후보 수를 줄이지 못하게 한다. 모든 final selection/confidence/accuracy·training/gold/generation·운영 승격은 없다.

## 5. 실행과 검증

```powershell
$env:PYTHONPATH = 'K:/Music Analysis/src;K:/Music Analysis/tests'
$env:PYTHONIOENCODING = 'utf-8'
& 'K:/Music Analysis/.venv/Scripts/python.exe' -m unittest test_factor_function_relations test_factor_function_relation_trial
& 'K:/Music Analysis/.venv/Scripts/python.exe' -m musicanote_harness.factor_function_relation_trial `
  --indexed 'K:/Music Analysis/output/factor-indexed-hypotheses-2026-10-01-r1' `
  --output 'K:/Music Analysis/output/factor-function-relations-2026-10-01-r1'
```

작은 실제 supplier universe의 모든103개 tuple/1,670function body와125hold×key/1,250terminal body를 frozen `_function`과 대조한다. duplicate origin, spelling 이명동음, microtone/blocker, unknown key/reference form, extended target core, terminal multiplicity, known-empty/unknown, zero/exact/whole budget, owned alias·seal·참조·source/code 변경을 검사한다. 첫/끝 technical query는 기존 요청 순서를 유지하되 각 slot×열 가지 function을 모두 요청한다. 이 표본의 결과와 bulk weighted coverage는 분모가 다르다.

### 검증/실제 결과 상태

핵심 41개 검사/103.074초, exit 0이다. 작은 universe의 2,920개 exact body와 모든 slot/key/status/nine-state 가중 집계가 frozen oracle과 일치한다. 최초 핵심 snapshot의 38개/94.023초 통과 뒤 누락/None header의 명시적 ValueError·실제 microtonal IR·early selector 거부를 강화하여 최종 41개를 검사했다. source semantic 계산은 바꾸지 않았다.

동결 핵심 source SHA256은 `6fca9a3470a166ed59370115478b7a0d351e524b1b24baa0a88a82437103979a`, 실행기는 `dcd17717e5ed658e65390e33a1c01741e405ca3dd292927f1802440ab125815a`다. 핵심 test SHA256은 `cdd151c8bd867738881048b90ead14ad6f85c72f9590392b6f238e783ec4b936`다. 이전 source 계약들은 그대로이다.

정적 독립 감사에서 saved parent query/assessment의 unknown top-level 필드와 재봉인한 거짓 conditional incidence가 입력 검사에서 통과할 여지를 발견했다. 새 실행기에 closed metadata와 **저장 motion + 같은 actual control links**의 incidence 재구성을 추가했다. stored query의 정확 function body와 모든 정책/참조도 대조한다. 이는 저장 근거의 일관성 검사 강화이며 physical profile/endpoint/motion의 새 계산은 아니다. 관련 재봉인 반례를 추가했다.

첫 실행기 검사 41개/361.333초는 ERROR 1개였다. 삭제된 등록 파일은 기존 `Path.resolve(strict=True)`에서 `FileNotFoundError`로 올바르게 거부되지만 새 테스트가 `ValueError`만 예상했다. **해당 테스트 하나만** 정확한 missing-file 오류·파일명·output 미생성을 검사하도록 고쳤다. 다른 negative의 ValueError 요구나 실행 코드·보호 정책은 완화하지 않았다. 첫 전체 회귀도 같은 구기대가 이미 수집된 실행을 중단했으며 완료/통과 수로 집계하지 않는다. 수정 뒤 실행기/전체 회귀의 최종 결과는 아래에 추가한다.

### 실제 r1

[실행 report](../../../output/factor-function-relations-2026-10-01-r1/report.json), [문맥별 산출물](../../../output/factor-function-relations-2026-10-01-r1/context-index.json), [고정 계획/보호 SHA](../../../output/factor-function-relations-2026-10-01-r1/run-plan.json): exit 0, **596.111095초/계산 오류 0**. 부모 5문맥/15raw lanes/16old groups, 원 cohort 322문맥/1,013lanes와 미실행 317/998은 그대로다.

| 실제 문맥 | exact type / kernel | 공유 target / key projection | conditional shape 행 | terminal 행 | 실제 function 질의 |
|---|---:|---:|---:|---:|---:|
| Beethoven quartet op.18 no.1 IV | 85 / 850 | 23 / 360 | 2,665 | 2,682,500 | 620 |
| Beethoven sonata no.1 I | 124 / 1,240 | 27 / 460 | 3,815 | 5,906,050 | 620 |
| Chopin mazurka op.30 no.2 | 126 / 1,260 | 27 / 460 | 9,715 | 9,155,150 | 700 |
| Corelli op.1 no.1 | 110 / 1,100 | 25 / 410 | 21,650 | 21,695,600 | 1,260 |
| Mozart sonata K.280 I | 85 / 850 | 23 / 360 | 13,525 | 14,001,200 | 1,180 |
| **합계** | **530 / 5,300** | **125 / 2,050** | **51,370** | **53,440,500** | **4,380** |

원 221catalogues/22,969variant origins/16,206lazy profile refs와113group(known empty 1개)을 보존했다. 1,068,810logical paths/5,344,050path×key의 **106,845,950개 function-shape 행 분모를 가중 관계로 정확히 집계**했고 이 shape 단계의 known 미계산 행은 0이다. 1억 행을 배열로 만들거나 모든 실제 profile/motion을 계산한 것이 아니다. terminal은 5full-hold·108two-segment의 마지막 slot과 opposite-origin multiplicity를 포함한다.

아홉 shape 분할은 `TT=51,370`, `TF=1,521,740`, `TU=2,950,750`, `FT=671,555`, `FF=22,849,285`, `FU=45,198,050`, `UT=0`, `UF=0`, `UU=33,603,200`이다. 이 고정 범위에서는 양쪽 true 행과 blocker 없는 conditional shape 행의 수가 같다. 그 밖의106,794,580행은 조건부 전제 보류이며 음악적 오답 판정이 아니다. unknown/false 행을 지워서 양성 비율을 높이지 않았다.

function-kind 투영은 primary/parallel 각각2,634,240, applied53,325,720, unassessed48,251,750이다. 동일 후보/각 key 가정을 반복한 **가중 조합 수**이지 수백만 secondary 화음·종지 발견 수가 아니다. 별도 4,380개 technical function 질의는 기존 첫/끝 tuple·one cyclic key·all slots×10을 그대로 재생했으며 대표 음악 선택이 아니다. 새 literal profile/endpoint/motion/same-bundle assessment 계산은 모두 0이다.

보호 입력4,464개/current source·schema304개와 creation SHA를 가진 등록 artifact12개+report=정확13파일/8,944,799bytes를 저장했다. 새 report SHA256은 `8c4eab24a50b945225ca228ba42a61fc2a11acf9447ae5dd4dcbf0ae68381ac3`다. 부모 indexed report `76d94b81ab6e2916430cef0405fe747641b45b059160c981872bf23fc582c596`와 모든 frozen 계약/파일은 유지한다. 여러 문맥 실행과 코드 검사를 병행한 wall-clock이므로 이전 부분 질의의 실행 시간과 직접 속도 비교하지 않는다.

### 최종 회귀와 독립 저장 감사

수정 후 실행기 **41개/356.912초, exit 0**이다. 마지막 core/runner/test SHA는 모두 유지됐다. 실행기 test SHA256은 `84fd73f9c6750ff57cb69f8d33c72abe286d0e569e3e84f7298d7623be2226a4`다. 신규는 핵심41개+실행기41개=82개이며 최초 실패와 수정 후 통과는 구별한다. 소스·검사를 동결한 최종 전체 Python 회귀는 **3,251개/1,259.283초, OK/exit 0**이다. 이전3,169개에 신규82개를 추가한 코드 검사 수이며 작품 수나 화성 정답 수가 아니다.

첫 독립 저장 감사344.674215초 OK: 전체5문맥의 공개 full-parent/scope/currentproducer와 `validate_relations`를 재생했고, 22,969origin→exact type/catalogue/lazy-profile 모든 연결과 **4,380개 저장 함수의 frozen oracle body**가 정확 일치했다. parent loader69.237456초/fresh cases102.736679초/모든 public relation validation141.090208초/oracle24.089967초다. 모든 sample envelope/selector/flags/currentcontract도 검사했다. original index/부모 report와 보호4,464inputs/304source·schema/12creation artifacts·정확13파일 목록은 종료 시에도 불변이었다. profile/motion/old indexed query/assessment entry point를 호출하면 실패하게 둔 상태로 통과했다. geometry provenance 검증과 실제 new motion 평가는 구별한다.

두 번째 독립 저장/산술 감사56.133944초 OK: 전체22,969origin과ordered type 연결, **5,300kernels×5명시key=26,500개의 frozen oracle body**, 모든125target joins/2,050key projections, 113group의9분할·status·kind·terminal multiplicity와4,380저장 질의를 대조했다. 별도 공개 API 재현은 **5문맥/4,380개 질의 전부, 432.698292초 OK**다. 각 문맥의 fresh source/scope와 `prepare_relations`를 한 번 검증한 뒤 모든 `query_function_prepared`의 body·참조·봉인·flags가 저장 결과와 정확 일치했다. old profile/motion/Cartesian query/provider를 호출하면 실패하도록 두었고, prepared 질의 동안 `_function`도 호출 금지하여 질의별 숨은 재계산이 없음을 확인했다. caller 자료와 보호4,464inputs/304source·schema/정확13outputs의 SHA·목록은 모두 불변이었다. 이는 새 함수 형태 계약의 전수 재현이며 실제 profile/motion 전체 계산이 아니다.

최종 파일 QA: 이번8개 source/test/doc의 strict UTF-8·NUL/U+FFFD·줄끝 공백과4문서의 로컬 링크128개에서 오류0. read-only `git diff --check`도 exit0이며 다른 기존 파일의 LF→CRLF 경고만 있었다. 최종 개발 문서 갱신 뒤 보호4,464inputs/304code/12등록artifacts와정확13output 목록·report SHA를 다시 대조해 변경0을 확인했다. 원자료/기존계약을 수정하거나 경고를 없애기 위해 unrelated 파일을 재작성하지 않았다.

첫/끝 technical 표본4,380개는 모두 function 전제 보류다. 반면 전체weighted universe에는51,370conditionalshape가 있다. 따라서 표본만 보고 전체 진행이 불가능하다고 결론 내리지 않으며, bulk 형태 양성을 근거로 표본의 물리적 해결을 발명하지 않는다. 모든 실제 tuple/profile/motion과 supplier 전체 재제안의 exhaustive 검증으로 보고하지 않는다.

## 6. 다음 큰 기능과 편곡 연결

다음은 이 관계를 **실제 note-time/원 source guard/정확 경계/조건부 NCT와 같은 하나의 completion 아래** 연결하는 bulk 비교다. root/PC만으로 motion을 공유하거나 서로 다른 성부 가정에서 좋은 이끎음/7음 연결을 합치지 않는다. actual membership과 endpoint에 전제가 부족한 후보는 shape 계산이 되어도 그 축을 보류한다.

그 뒤 실제 긍정/반례를 whole-score에 표시하고 사용자 피드백을 요청한다. 이번 단계에는 새로운 화면/서버/구조 분석/생성기/Git 적용이 없다. [작곡·편곡 로드맵](../MUSICAL_SEMANTICS_AND_GENERATION_ROADMAP.md)의 역할·질감·배치·모티프 전개 슬롯은 경쟁 가정과 원음표/음가를 그대로 이어받는다. shape가 있다는 이유만으로 확정 화음 또는 생성 가능한 반주 템플릿이 되지는 않는다.
