# 화음 경계를 넘는 조건부 계류·선행음 근거

개발 ID: `HARM-DEV-20261002-18`. 정본 위치: `docs/harmony/records/`. 화성 분석 개발 문서이며 인수인계 문서나 구조 분석 로그를 대체하지 않는다.

## 1. 목적과 착수 결정

[직전 시간순 구성음·local contour 단계](2026-10-01-temporal-and-local-nct-explanations.md)는 한 exact descriptor 안의 경과·보조 음형을 계산했다. 다음 큰 단위는 **원래 indexed 후보 구간 경계 양쪽의 조건부 역할 변화**다. 후보의 경계를 실제 화음 변화로 확정하거나 음을 삭제하지 않고, 앞뒤에서 각각 가능한 성부 연결을 합쳐 비화성음으로 확정하지 않는다.

이번 구현 범위는 계류·선행음의 **조건부 형태와 실제 연결**이다. 지속/동음 재타격 사슬은 후속 지연 해결의 전제가 되지만, 이끎음·7음의 여러 기능적 해결 의무를 공동 판정하는 것은 다음 단위다. 이번 단계에서 지연 Secondary·최종 NCT·화음·국소 조성·Cadence를 확정하지 않는다. 사용자가 보던 운영 악보 화면의 표시를 바꾼 단계도 아니다.

계약의 근거는 [화성 추론 규칙 R01/R03/R05/R07/R11](../HARMONY_REASONING_RULES.md)과 [메인 개발 문서](../README.md)다. 특정 제목·작품 ID·마디의 정답을 조건식으로 넣지 않는다.

## 2. 경계 구간의 계약

1. 같은 원래 indexed group의 인접한 두 slot만 하나의 구간쌍으로 사용한다. `LEFT.end == RIGHT.start`를 exact rational로 확인한다. 서로 다른 group의 유리한 후보를 붙이지 않는다.
2. 두 slot 전체가 명시적인 pair envelope다. 원 sound의 full span·attack·source/tie/철자 검사가 이 범위에서 성립해야 한다. 한 descriptor 밖의 음을 아무 말 없이 같은 화음으로 가정하지 않는다.
3. 실제 준비 attack은 LEFT 안에 있어야 한다. 경계 직전 잘린 음의 일부만 보고 준비된 음이라고 하지 않는다.
4. 지속 sound와 현재 IR의 동일 written spelling·octave(음역)의 재타격을 구별한다. 재타격을 동일 sounding event의 지속/tie로 간주하지 않으며 별도 suspension-like 가정으로 다룬다. 같은 pitch class만으로 동음 사슬을 만들지 않으며, 이 검사를 독립적인 concert pitch/조옮김 인증으로 표현하지 않는다.
5. 원 profile·membership·note-time·출처·음가·기존 completion을 보존한다. 새로운 설명은 새로운 typed record/bundle로 저장하며 과거 bundle을 확장하거나 재봉인하지 않는다.

### 설명할 수 있는 부분

| 조건부 형태 | LEFT 역할 | RIGHT 역할 | 설명량을 부여하는 부분 |
|---|---|---|---|
| 준비된 지속/동음 재타격 뒤 하행 해결 | member | nonmember → ordinary-step member | RIGHT의 실제 비구성음 부분 |
| 지속 선행음 | nonmember | 같은 실제 sound가 member로 유지 | LEFT의 실제 비구성음 부분 |
| 동음 재타격 선행음 | nonmember | 경계에서 같은 철자·음역으로 member 재타격 | LEFT의 실제 비구성음 부분 |
| 공통 구성음 | member | member | NCT 설명 없음 |

여기서 `member/nonmember`는 **지정한 화음 후보 아래**의 관계다. 협화/불협화·박절/accent·지각 호흡·국소 조성·음악적 정답까지 검사한 명칭이 아니다. 하행 2도만으로 계류를 확정하지 않는다. 미해결·다른 음정·준비가 범위 밖·source 보류·grace/point·다른 성부 가정의 반례도 유지한다.

설명량은 같은 sound·같은 side·같은 실제 completion 안에서 해당 비구성음 시간의 합집합으로 계산한다. 계류의 RIGHT 부분을 LEFT에, 선행음의 LEFT 부분을 RIGHT에 잘못 부여하지 않는다. 서로 다른 completion의 설명을 더하지 않는다. 이번 pair query는 경계 설명만 계산하며 직전 local NCT 설명과의 공동 합집합 계정은 명시적으로 미평가다.

## 3. 조합을 보존하는 유한 표현

실제 다섯 구간에는 백만 개 이상의 논리적 진행이 있으므로 모든 진행이나 descriptor 쌍을 객체로 펼치지 않는다. 원래 두 slot의 후보·origin·key·진행/기능 분모는 그대로 보존한다.

각 geometry에서 LEFT/RIGHT descriptor를 **membership vector + blocker**가 정확히 같은 partition으로 나눈다. 작은 partition 사각형과 각 사각형이 나타내는 descriptor/origin 수를 저장한다. 후보의 이름·근음·철자·순서·출처를 지우는 축약이 아니다. 명시적으로 원래 group과 LEFT/RIGHT origin을 질의할 때 계산된 정확한 부모 profile을 복구한다. 상위 한도로 profile이 없는 경우는 origin 참조를 유지하고 profile을 `null`로 둔다. 빈 profile이나 알려진 0으로 대체하지 않는다.

지속 선행음은 하나의 실제 sound가 경계를 넘기 때문에 새 edge가 필요 없을 수 있다. 따라서 무연결 completion 아래 설명량이 항상 0이라고 가정하지 않는다. 재타격/계류 해결은 필요한 **모든 carry/resolve edge**를 한 실제 all-raw-lane completion에서 함께 확인한다. 별개의 witness를 합치거나 자기 자신을 잇는 가짜 edge를 넣지 않는다.

`possible/impossible/unknown`은 필수 연결 집합의 raw-lane geometry 공동 가능성이다. 음악적 역할의 정답/부재를 판정하는 값이 아니다. descriptor 쌍 incidence, origin 쌍×key incidence, 실제 bundle별 관계 incidence는 서로 다른 분모이며 독립 성공 수 또는 confidence로 합산하지 않는다.

## 4. 구현 파일과 한도

- [factor_boundary_explanations.py](../../../src/musicanote_harness/factor_boundary_explanations.py): 새로운 `fmbe_` 계약, 원 touching pair·동음 사슬·membership partition·새 completion과 owned query.
- [factor_boundary_explanation_trial.py](../../../src/musicanote_harness/factor_boundary_explanation_trial.py): 검증된 temporal 부모를 소비하는 append-only 실행기.
- [핵심 검사](../../../tests/test_factor_boundary_explanations.py), [실행기 검사](../../../tests/test_factor_boundary_explanation_trial.py).

| 한도 | 기본값 | 의미 |
|---|---:|---|
| `max_geometry_candidates` | 4,096 | 전체 경계 geometry의 객체화 한도; 넘으면 성공 prefix를 내지 않음 |
| `max_chain_edges` | 16 | 실제 동음/해결 사슬 깊이; 실제 메타데이터에서 최대 10 연결 관측 |
| `max_membership_relations` | 65,536 | 전체 partition 관계 객체화 한도 |
| `max_new_bundles` | 4,096 | 새 필수 연결 집합 completion 한도 |
| `query_work_budget` | 100,000 | 각 raw lane의 성부 DP 질의와 필요 시 exact pair 계정 질의에 각각 적용 |

이 한도는 RSS/파일 크기/전체 실행 시간 상한이 아니다. 결과의 정수 0은 확인된 빈 결과이며, 미계산/알 수 없는 값 `null` 및 알려진 부분 집계와 구별한다. 부모의 보류를 새 지지로 바꾸거나 유리한 처음 일부만 계산 완료로 내보내지 않는다.

성부 DP 작업 단위는 방문 상태와 transition이다. exact pair 계정 질의의 사전 작업 수는 해당 group의 저장 geometry 수와 복구할 두 profile의 row 수를 합한 값이다. 한도를 넘으면 계정 전체를 보류한다. 부모 profile 또는 geometry 계획이 미완성일 때는 전체 작업 수를 `null`로 두고 알려진 저장 부분 수만 따로 보고한다. 원래 구간쌍/조합 자체가 없는 경우의 알려진 0과 구별한다.

부모는 `factor-temporal-explanations-2026-10-01-r1`이다. 닫힌 report/plan/schema·생성 시점 SHA·정확 output 목록·원문맥 순서·origin 및 전체 보호 input/code closure를 확인한다. 기존 parser/selector/주석 분석을 재실행하거나 기존 output에 덮어쓰지 않는다. 원자료 주석은 이번 추론의 정답으로 사용하지 않는다.

## 5. 검증 및 실제 실행 기록

착수 전 **읽기 전용** 메타데이터 점검은 원래 108개의 touching pair group, 1,068,109 origin 쌍과 519,427 descriptor 쌍을 확인했다. full-hold의 나머지 701 진행도 보존한다. 예비 geometry/partition 크기 계산은 완성 성부/NCT 양성 검사나 저장 결과가 아니다.

실제 r1·전체 회귀 및 독립 감사는 동결된 같은 소스에서 실행한다. 검증이 끝나기 전에 계획된 수를 통과 수 또는 음악적 정확도로 쓰지 않는다.

### 최종 동결본의 신규 검사

핵심 **35개/240.404초**, 실행기 **25개/30.879초**가 각각 새 process에서 실패·오류 0, exit0으로 통과했다. 아래 합계 60개는 두 검사 실행의 합이며, 전체 통합 회귀 실행과 구별한다. 기존 여섯 선행 core와 직전 temporal core/runner/test의 SHA는 바뀌지 않았다.

| 파일 | SHA-256 |
|---|---|
| `factor_boundary_explanations.py` | `1aa61b9663a1d91bbd861d3fa733e1d7f097e2b0aafc0f4519ee4de6ca3695f4` |
| `factor_boundary_explanation_trial.py` | `eee369306b9782561539ab7b0688b012d307022739e23ada4f452d8bf0858b29` |
| `test_factor_boundary_explanations.py` | `617e08389e4525e320eb21a9c0c55d24f4ea9df6fc2523c78c30aab7042e2986` |
| `test_factor_boundary_explanation_trial.py` | `c6f378a9a453b87e1de06dfea95f0502a4ce9f55c6e8f8fef59fe2e4edc1ae4e` |

양성뿐 아니라 첫 다른 음의 해결 실패를 건너뛰지 않기, full pair 밖의 준비음/해결음, source/tie/attack/grace/microtone 보류, 동음 재타격과 실제 지속 구별, 같은 completion 안의 전체 연결, 경쟁 화음 후보의 별도 양성 및 공동 연결 불가능, 겹친 설명 시간의 합집합, 정확 origin/profile 복구와 위조 부모/출력/질의 거부를 검사했다. 이 수는 작품 수·독립 음악 정답률이 아니다.

### 실제 r1·전체 회귀·독립 감사

**실제 r1: exit0, 1,320.989047초, 5저장/0실패.** 부모 입력의 cold 재현·새 계산·저장·최종 hash/inventory 확인을 포함한 시간이며 UI/단순 lookup 지연 시간이 아니다. 이전 다섯 구간의 분석 결과를 재작성하지 않고 새 경계 설명만 별도 저장했다. 전체 회귀와 독립 감사는 별도 실행이며 모두 완료됐다.

동결 후 **전체 Python 3,453개/2,324.486초 OK/exit0**다. 직전 3,393개와 신규 60개를 이번 한 번의 통합 실행에서 검사했다. PowerShell process 전체 계측 2,328.172679초는 unittest가 보고한 검사 시간과 구별한다. 개별 신규 검사·실제 r1·독립 감사의 시간을 이 전체 회귀 시간에 합산하지 않는다.

- [실제 report](../../../output/factor-boundary-explanations-2026-10-02-r1/report.json): SHA `fbf950cef025e1bd26a2b132dca3aeb7e87b35fe2747c508a885131e64a6d793`.
- [run-plan](../../../output/factor-boundary-explanations-2026-10-02-r1/run-plan.json): SHA `b81ec2c27d68b8f3209768f40633d11b63f24535df5fda1019ca2413292de3ac`.
- [문맥/산출물 색인](../../../output/factor-boundary-explanations-2026-10-02-r1/context-index.json): SHA `21813d3efa4ea0007603be03f248f71859910065988dad2d5b45929d757e5988`.
- 실제 보호 input 4,499개, 현재 producer/schema 310개, report 포함 정확 8파일/12,143,590bytes. 실행기 확인에서 원 입력/code/모든 부모 output 목록 및 새 artifact hash 변경 0이었다. 뒤의 독립 감사와 별도 전수 SHA 재확인은 이 자기검사와 구별한다.
- 원 22,969origin/16,206descriptor와 1,068,810논리 진행/5,344,050진행×key/106,845,950function 분모를 보존했다. 전체 선언 322구간/1,013raw lanes 중 이번 실제 선택은 5구간/15lanes이며 나머지 317구간/998lanes는 미실행이다. `cohort_complete=false`다.

| 실제 선택 문맥 | global quarter 범위 | touching groups | geometry | partition 관계 | 새/기존 bundle | 조건부 descriptor 쌍 incidence | unknown incidence |
|---|---|---:|---:|---:|---|---:|---:|
| Beethoven 현악4중주 `n01op18-1_04` | `[262,270)` | 15 | 84 | 783 | 35 / 8 | 13,752 | 8,362 |
| Beethoven 소나타 `01-1` | `[49,61)` | 15 | 107 | 1,224 | 11 / 6 | 32,039 | 13,856 |
| Chopin 마주르카 `BI105-2op30-2` | `[10,22)` | 17 | 94 | 953 | 8 / 11 | 21,116 | 14,023 |
| Corelli `op01n01a` | `[32,44)` | 32 | 183 | 1,830 | 17 / 41 | 113,739 | 31,052 |
| Mozart 소나타 `K280-1` | `[18,27)` | 29 | 61 | 591 | 2 / 14 | 20,222 | 8,649 |

529 geometry의 descriptor 쌍 incidence **2,512,694 = 조건부 200,868 + 보류 2,235,884 + unknown 75,942**를 3,390membership partition/5,381관계로 공유 표현했다. 원래 descriptor 쌍 519,427개가 geometry별로 반복되는 집계이며 독립 음악 사건 수가 아니다. 조건부 origin 쌍×key incidence 1,004,340도 별도 가중 분모다. 부모 80bundle의 body는 그대로 두고 새 73complete bundle과 실제 bundle별 관계 188,180건(조건부 3,666건)을 대조했다. 이번 실제 r1에서 새 bundle의 불가능/예산 unknown은 0이지만 membership unknown은 여전히 75,942건이다.

최대 실제 사슬은 **10edge**다. report의 generic integer subtotal `max_planned_chain_edges=19`는 각 문맥 최대치 `10+3+2+3+1`의 합이지 전역 최대 19 또는 cap16 초과가 아니다. 다섯 inventory의 cardinality는 알려져 있어 `boundary_unknown_metric_contexts={}`지만, 이것이 모든 화성 관계가 확정됐다는 뜻은 아니다.

저장 시 `pair_accounts_computed=0`/`boundary_queries_computed=0`이다. 모든 origin쌍×bundle의 계정은 펼치지 않으며 명시한 origin과 하나의 bundle을 필요 시 질의한다. 지연 기능 의무와 local+boundary 공동 계정도 0/미평가 상태를 유지했다. `selected=null`, 전체 NCT·화성·조성·secondary·cadence·음악정확도·학습/Gold·구조/생성/운영 적용은 모두 미승격이다.

### 독립 실제 검증 — 완료

별도 읽기 전용 process에서 **1,284.497174초/exit0, 전 5문맥 PASS**다. 실제 부모 입력의 cold 검증을 성공 실행에서 한 번만 수행하고(1,149.957357초), 그 process의 소유된 handles를 계속 사용했다. 준비된 NEW 공개 질의와 87개 표본의 103.079184초는 전체 시간에 포함된다. 처음 감사 helper의 query 검증 인수에서 원 필수/금지/예산 조건을 누락한 것을 발견해 준비 process를 중단하고 helper만 교정했다. 그 중단 실행은 부모 검증 완료나 통과 수로 합산하지 않으며 파일을 쓰거나 producer를 변경하지 않았다.

- 전체 239source facts의 clock/attack/tie-span 합집합/written pitch, 108구간쌍과 1,068,109origin/519,427descriptor의 조합 분모를 대조했다. 이 sound의 pitched source-note 참조는 243개이며, 원258notated slots의 나머지15개 rest를 sounding source로 세지 않는다. 범위 밖의 원 tie 시작점도 full span으로 보존하고 준비/범위 guard로 대조했다.
- 모든 529geometry/3,390partition/5,381관계의 source·첫 변화·membership vector/guard·origin 가중치·nested seal을 확인했다. geometry 자체의 상태는 **조건부 210/보류 319**이며 descriptor별 incidence 수와 다르다. 최대 사슬 10도 독립 확인했다.
- 73새 bundle의 필수 연결 집합과 실제 같은 witness를 모두 검증하고, 부모 80bundle body가 정확히 같음을 확인했다. 전체 188,180bundle별 관계와 2,512,694descriptor incidence/26,085,590origin쌍×key incidence의 완전 집계를 대조했다.
- 공개 pair 질의 87표본에서 정확한 원 profile 174개를 복구하고 raw 음가/범주 합계·side clip·합집합·같은 bundle 제한을 확인했다. 표본 중 무연결 질의 18개/조건부 설명량 양성 77개다. 지속 선행음은 실제 한 sound이므로 일부 무연결 질의도 양성이며, 양성 수는 음악적 정답률이 아니다. 실제 전체 origin쌍의 계정을 전수 질의한 검사가 아니다.
- 4,499보호 input/310현재 code·schema/정확8출력12,143,590bytes의 생성 hash·현재 hash·부모 목록·새 report SHA가 불변이었다. ROOT의 별도 전수 hash 확인도 보호 path 합집합 4,501개 변경 0, artifact 변경 0/정확8파일을 확인했다.

유한 geometry/partition/bundle의 전수 독립 검사와 대표 실제 pair의 공개 재현을 완료했다. 이 결과를 백만 진행의 음악적 전수 평가, 원주석 정답의 인증, 전곡/전체 cohort 완료 또는 운영 적용으로 해석하지 않는다.

### 실제 원음표에 연결된 조건부 예시

아래는 독립 공개 질의 87표본에 실제 포함됐던 **후보 가정의 계산 예시**다. 화음의 정답을 고른 사례가 아니다. 원음표·full duration·출처·후보 철자와 앞뒤 시간 범위를 보존했으며 accent/consonance/국소 조성/완전 NCT는 미평가다. 특히 첫 예의 `E♭–G–B → C–E–G–B♭`는 공급된 경쟁 후보 중 하나이지 해당 마디의 확정 화성 분석이 아니다.

| 항목 | Beethoven 소나타 `01-1` | Corelli `op01n01a` |
|---|---|---|
| 원본 표시 마디 | 13 | 9 (sequence index 8) |
| 가정한 LEFT → RIGHT 구성음 | `E♭–G–B → C–E–G–B♭` | `D–F–A → C–E–G` |
| 실제 음과 full span | B♭3 `[49,53)` | D3 `[32,67/2)` → C3 `[67/2,135/4)` |
| 후보 경계 | q`101/2` | q`33` |
| 조건부 형태 | 같은 sound의 지속 선행음 | 준비된 지속음 뒤 순차 하행 |
| 설명 부분 | LEFT `[49,101/2)` = `3/2q`; RIGHT 0 | RIGHT `[33,67/2)` = `1/2q`; LEFT 0 |
| 필요한 실제 연결 | 없음: 실제 한 sound이므로 self-link 금지 | D3 → C3 edge가 같은 completion에 존재 |
| 공개 질의의 새 bundle | `fmbebundle_b49d44e6a82e3905b027efa9` | `fmbebundle_3c35c18a50961926a9b3c7ab` |

원 membership 음시간은 선행음 예의 LEFT member `3q`/nonmember `3q`/total `6q`, RIGHT member `31/3q`/nonmember `157/6q`/total `73/2q`다. 하행 예는 LEFT member `4q`/nonmember `0q`/total `4q`, RIGHT member `67/4q`/nonmember `109/4q`/total `44q`다. 음을 지우거나 raw nonmember 값을 덮어쓰지 않았다. 이는 모든 동시 sound를 합친 note-time이므로 단순 시간축 구간 길이와 다를 수 있다.

선행음 예의 원 참조:

- group `fmehgroup_c8b14c19814231bac28a7074`, LEFT/RIGHT origin `fmehseg_2dffff0667af0d82dd3e7cce` / `fmehseg_bc51a8ee39f32092a1ab0f98`.
- descriptor `fmiprofile_3a3e2062820e5dfa1e004114` / `fmiprofile_8efdccebc79812a3a38aa5fb`.
- sound `sound_52e7b749f719`, source note `note_9737bdf159e9`, 실제 attack q`49`.
- geometry `fmbegeom_c830b5432d4e7fab32e5a729`, relation `fmberel_54db9c3341d3ad80a1b634bb`.

하행 예의 원 참조:

- group `fmehgroup_ae3c061ee9291f31ead88359`, LEFT/RIGHT origin `fmehseg_cbe3e0c6357916e5d1aa0e79` / `fmehseg_c43b86d29ff7669d8033c0c8`.
- descriptor `fmiprofile_1631e3fc87e91f81097e9f4c` / `fmiprofile_9c42f920760c3bc84e0ed2ff`.
- D3 sound `sound_4154125e404c` / note `note_b4f05feb79e3`; C3 sound `sound_b5a6cbe52b7a` / note `note_43cb853e6c45`.
- geometry `fmbegeom_33c5492cf6ff097bf2119c0d`, relation `fmberel_9e9e1d6d0b8438a02f998283`.

같은 origin쌍의 무연결 대조도 저장된 실제 witness/incidence로 독립 산술 확인했다. 소나타의 기존 `fmgrbundle_80bdbc30550151318a39f16a`에서는 LEFT `3/2q`/RIGHT0으로 여전히 설명되며, 코렐리의 기존 `fmgrbundle_62e15498711af0f426dd73c8`에서는 LEFT/RIGHT 모두0이다. **이 두 same-pair control 산술은 추가 공개 prepare/query 실행이 아니라 저장 자료에서 독립 유도한 검사**다. 위 새 bundle의 양성 tuple은 실제 공개 실행 표본이었다. 한 sound의 실제 지속과 연결이 필요한 하행을 혼동하지 않는 예시이며 독립 음악 검수 정답이 아니다.

### 동결 전 검토·보완

- 부모의 기존 bundle을 새 버전으로 재봉인하는 중간 adapter를 사용하지 않고, 새로운 전 성부 query/witness body를 직접 구성한다.
- membership 사각형 수를 먼저 세어 전체 한도를 넘으면 봉인된 결과 객체를 만들지 않는다. 성공 prefix를 남기지 않으며 전체 계획 수와 알려진 부분 집계는 구별한다.
- 독립 소스 검토에서 기존 `_state(sound, segment)` 호출 계약과 실제 `graph.events[].sounding_event_id` 목록을 새 코드가 잘못 사용한 두 지점을 찾아 교정했다. 이는 동결/실제 실행 전 발견이며 저장 r1의 실패 건수로 합산하지 않는다.
- profile 또는 geometry 계획이 미완성일 때 질의 작업 수를 알려진 0으로 표현하지 않는다. 전체 미정과 known subtotal을 분리한다.
- 독립 실제 형식의 합성 smoke에서 immutable session의 `MappingProxy`를 기존 dict 전용 pitch helper에 그대로 넘겨, 저장 predicate는 정상인데 공개 질의가 `unknown/unsupported`로 바뀌는 결함을 발견했다. 질의할 두 descriptor와 source facts를 소유한 값으로 복구하여 비교하도록 보완했다. 기존 부모/음표/저장 결과를 완화하는 수정이 아니다.
- 첫 핵심 26개 실행은 180.453초, 21통과/5실패였다. 위 immutable operand 결함으로 조건부 설명이 0이 된 동일한 다섯 실패는 수정 후 55.856초에 통과했다. 중간 실행을 전체 26개 또는 최종 전체 회귀 통과라고 표현하지 않는다.
- 확대 33개 실행은 219.244초, 31통과/2개 신규 fixture 오류였다. music21 exporter가 단일 2.5q 음가를 내보내지 못한 경우와, 음수 span을 허용하지 않는 helper를 음수 반례 작성에 사용한 경우다. fixture만 수정한 관련 세 검사 22.024초 통과와 최종 전체 실행을 구별한다. 원 악보·IR·parser 규칙을 느슨하게 만들지 않았다.
- 경계 구간쌍이 아예 없는 입력에서는 관련 없는 full-hold 부모가 보류여도 경계 geometry/관계/completion 계획은 알려진 0이다. 구간쌍이 있는 보류 입력과 분리하여 검사한다.

수정 뒤 동일한 독립 inline smoke를 새 process에서 재실행하여 네 합성 경우를 통과했다. 실제 부모 계약을 거친 C-major → G-major 가정에서 B4 지속 선행음은 무연결 아래 LEFT 1q, B4 재타격 선행음은 필요한 1edge 아래 LEFT 1q, C5 지속 → B4 하행 형태는 해결 1edge 아래 RIGHT 1q, C5 → C5 재타격 → B4는 두 edge가 한 completion에서 함께 있을 때 RIGHT 1q다. 재타격/해결의 무연결 control은 0이고, 두 원 origin의 공개 복구 profile은 `frozen._profile`과 정확히 같다. raw 음가/합계·최종 미선택을 확인했다. 이 네 경우는 실제 작품/정답률 또는 이번 실제 r1 표본 수가 아니다.

### 최종 파일·문서 검증

전체 회귀 후 신규 source/test/doc 7파일의 strict UTF-8·NUL/U+FFFD·줄 끝 공백, Python 4파일 AST와 세 개발 문서의 123로컬 파일 링크를 확인해 오류0이었다. 새 네 source/test SHA와 직전 temporal 네 source/test SHA가 모두 동결값과 같다. 보호 hash 합집합4,501path, 현재 producer/schema310개 목록, 정확8개 r1출력 및 report SHA를 다시 확인해 변경0이었다.

읽기 전용 `git diff --check`도 exit0이다. 기존 별개 tracked 파일 다섯 개의 LF→CRLF 경고는 그대로이며 변경하거나 자동 정규화하지 않았다. Git commit/push, 원 XML/IR/parser·기존 생산 코드/운영 뷰어·구조 분석·생성기·원주석/Gold는 이번 작업에서 수정하지 않았다.

## 6. 다음 단위의 완료 기준

1. 이끎음·7음의 key/function 가정과 boundary role을 같은 실제 completion에서 함께 검사한다.
2. 여러 해결 의무가 동시에 성립해야 한다. 하나씩 성공한 독립 witness를 합치지 않는다.
3. 같은 sound의 local contour와 경계 설명이 겹치면 같은 completion에서 합집합으로 계산한다. raw evidence·특징적 구성음·bass/change 근거는 유지한다.
4. 실제 소나타·현악사중주·마주르카·Corelli·Mozart 구간을 보존하고, 새 큰 기능 검증은 작품군/편성을 더 넓힌다. 다섯 선택 구간을 전곡 또는 전체 cohort 완료로 표현하지 않는다.
5. 최종 해석 선택·독립 음악 검수·구조/생성/UI 적용은 각각 별도 승인·검증 단계다.

### 지연 해결의 구체적 후속 설계 — 아직 구현 전

- 기존 실제 source/target/family/quality 관계를 소비하는 별도 delayed-obligation 레이어를 만든다. 경계 NCT geometry만 재사용하면 상행 이끎음·경계의 직접 다른 음 진행이 빠지므로, 실제 성부 그래프에서 중립적인 지속/동음 재타격/첫 변화/종료 경로를 공급한다. 유리한 뒤 음까지 실패한 첫 변화 지점을 건너뛰지 않는다.
- **관찰 목록 → 명시 규칙 가정 → 같은 completion의 충족 여부**를 분리한다. 모든 이끎음/7음 후보와 doubling의 실제 source·guard·경로는 관찰 목록에 보존하되, 관찰됐다는 이유로 모든 음에 동일 해결 의무를 자동 부과하지 않는다. ordinary 역할별 존재 가정(각 역할의 OR 후 역할 간 AND)과 명시한 occurrence 집합의 공동 해결 가정은 별도 전략이다. 한 양성 연결을 모든 중복음 해결로 표현하지 않는다. 미요구/미검사/보류 발생을 숨기지 않으며, 가정 실패를 음악의 오류 또는 화음의 부재로 승격하지 않는다.
- 경계에서 target 구성음 일부가 늦게 등장하는 경우, 기존 direct 모델의 실패를 그대로 보존한다. 새 계산은 경계의 core/bass 부족, 실제 해결 endpoint membership, RIGHT 안의 시간순 구성음 제시를 서로 다른 축으로 기록한다. 단순 pitch pooling이나 해결 한 개로 target 화음을 확정하지 않는다.
- 실제 경과/보조·경계 설명·지연 해결을 새 실제 bundle의 연결 아래 다시 대조하고, 같은 sound의 설명 범위를 합집합으로 계산한다. 과거 서로 다른 bundle의 설명량을 더하지 않는다. 기능 bundle의 목록만으로 가능한 모든 선택적 NCT completion을 검사했다고 주장하지 않으며, 명시한 공동 요청의 전체 예산과 미질의 분모를 보존한다.
- ordinary 직접 해결 부분집합의 기존 결과, 지연된 LT/7음의 지속과 재타격, 여러 발생음의 전략별 OR/AND, 첫 실패 뒤 늦은 성공의 거부, 공동 연결 불가능 반례, raw 음가 불변 및 실제 다섯 문맥의 저장/공개 질의를 검증한다. 현재 단계의 SHA·결과를 고치지 않고 새 버전/출력에 저장한다.
