# 단계45 — 경쟁 3화음·7화음과 해결 의무의 공동 비교

## 1. 이번에 완료한 범위

같은 원음·조성 가설·성부 연결 가정·전체 시간 분할에서 **한 구간만 3화음과 그 7화음으로 달라지는 후보**를 비교하는 연구용 정책을 구현했다. 추가된 7음의 원음표·타이·음가, 3화음 가정의 조건부 비구성음 설명, 7화음 가정의 해결 경로를 함께 보존한다. [단계44](2026-10-04-sonata-completion-evidence.md)의 다음 음악 정책을 진행한 것이며 새 저장 엔진 개발로 순서를 전환한 것은 아니다.

판단이 쉬운 3화음으로 자동 치환하거나, 악보에 7음이 있다는 이유만으로 7화음을 확정하지 않는다. 비교 결과는 최종 승자/신뢰도/정답 주석이 아니다. 전체 진행 선택·모든 조성/경계 대안의 최적화·최종 cadence·운영 악보 UI 적용은 미완료다.

교재에서 정리한 구성음/성부 해결의 원칙을 후보 경쟁 정책으로 연결했다. 이 단계에서 새 교재 장을 읽거나 모든 책 규칙을 구현 완료했다고 선언하지 않는다. 기존 `factor_delayed_obligations`와 native ordinary 전략은 실제 동음 연결을 거쳐 첫 pitch 변화까지 따라가지만, 쉼/분리 뒤 같은 음이 다시 나왔다는 것만으로 앞 음과 연결하지 않는다.

## 2. 모든 작품에 적용하는 규칙

| 규칙 | 계산/보존 | 자동으로 결론 내리지 않는 것 |
|---|---|---|
| CP01 철자 기반 비교 | root부터 3도씩 배열된 정확한 spelling과 반음 패턴으로 triad/seventh 형태 구별 | 큰 누적 pitch pool의 부분집합을 완결 화음으로 재명명하지 않음 |
| CP02 비교 문맥 고정 | 같은 source/key/bundle/partition, 나머지 slot의 root/member/span과 비인접 transition 가정 일치 | 서로 다른 key·성부·경계의 유리한 근거 합치기 금지 |
| CP03 추가음 설명 의무 | 추가 7음의 모든 literal occurrence와 원 note/attack/tie ID, 관측 범위 및 전체 sound 범위 저장 | 3화음에 속하지 않는 음을 삭제하거나 확정 NCT로 간주하지 않음 |
| CP04 의무 개수로 선택 금지 | 3화음/7화음의 실제 ordinary 역할과 whole/joint 전제 차이를 별도 보고 | 이끎음 하나가 해결된 3화음을 7화음보다 자동 선호하지 않음 |
| CP05 전략 실패와 화음 부정 분리 | source guard, 미연결, 목표구간 밖/비구성음, 잘못된 첫 변화 움직임을 별도 축으로 저장 | ordinary 전략 실패를 모든 화성 해석의 불가능으로 일반화하지 않음 |
| CP06 재등장 경로는 진단 | 미연결 source 이후 같은 raw lane/동일 octave·spelling의 재등장과 **그 이후 실제 링크** 조사 | 중간 링크/쉼/음악적 성부를 발명하거나 source의 해결 credit에 더하지 않음 |
| CP07 완전 진행 판단 | key·구성음 누락·미설명 음가·미선언 전환·pooled 시간 근거 부족을 전체 path별 유지 | 국소 전환 성공을 전체 진행/cadence 성공으로 바꾸지 않음 |

CP01이 현재 구별하는 형태는 장/단/감/증 3화음, dominant/major/minor/minor-major/half-diminished/diminished/augmented-major/augmented 7화음이다. 이는 **spellings의 관찰 형태 이름**이다. 기능, 근음의 음악적 확정, 생략/전위, jazz chord, 모든 비3도 화음을 구현한 목록이 아니다. Microtonal 또는 unresolved spelling은 보존하되 이 형태 분류에서는 unsupported로 남긴다.

CP02의 changed slot에 인접한 transition은 `V`→`V7` 같은 **가정 변화 자체**를 비교해야 하므로 다른 가정을 허용하고 모두 기록한다. 이를 동일 function 전제의 순수 credit 차이로 해석하지 않는다. 나머지 slot은 equivalent root/member/span을 요구하며 provider origin alias는 쌍에 각각 보존한다.

CP03의 조건부 설명은 같은 completion에서 이미 검증·저장한 시간 합집합과 추가음의 slot 범위를 교차한다. 음가를 float으로 계산하지 않는다. 7화음의 member에 같은 slot 안에서 NCT credit이 부여된 모순은 거부한다. Conditional coverage가 없다는 것은 **현재 이 후보가 설명하지 못했다**는 뜻이며 그 음이 실제로 NCT가 아니라는 정답 판정은 아니다.

CP05에서는 하나의 실제 endpoint에 ‘비구성음’과 ‘해결 방향 불일치’가 동시에 발생할 수 있다. 단일 대표 `kind`와 모든 `failure_axes`를 같이 저장한다. Doubling 중 일부 경로가 실패하더라도 다른 실제 경로가 충족하면 기존 existential ordinary 전략의 지원을 유지한다. 모든 doubling을 의무화하거나 첫 불리한 pitch 변화 이후를 건너뛰지 않는다.

CP07은 내부 transition이 없는 full hold를 실패로 취급하지 않는다. 해당 축은 `None/not applicable`이며 나머지 증거가 충족되면 conditional evidence complete가 될 수 있다. 이는 vacuous ordinary 진행 성공 또는 실제 화음 유지 확정이 아니다. `held_path_evidence` 역시 화음의 전역 탈락 상태가 아니라 미충족 전제 목록이다. 현재 omission model을 새 정책에 연동하지 않았으므로 missing member는 여전히 보류된다.

## 3. 실제 음악에서 확인한 핵심 사례

대상은 베토벤 소나타1번1악장 **13~15마디 `[49,61)`**, 2/2박자, 원3 raw lane/23 sounding facts다. 아래는 전체 검사 후 설명용으로 찾은 사례이지 특정 작품을 위한 예외 규칙 또는 제한된 평가집합이 아니다.

같은 F natural minor 가설/linked completion/3개 slot에서 원 selector **1281 대 1201**을 비교했다.

| 항목 | 1281: E♭–G–B♭ 3화음 가정 | 1201: E♭–G–B♭–D♭ 7화음 가정 |
|---|---|---|
| 첫 구간 | `[49,53)` | 동일 |
| 다음 구간 가정 | A♭–C–E♭ `[53,57)` | 동일 |
| 명시 ordinary 관계 | `V/M` | `V7/M` |
| G4→A♭4 | 같은 실제 edge에서 supported | 동일 |
| D♭5 | nonmember, 조건부 설명0 | member, ordinary seventh route가 미연결 |
| 첫 전환 whole/joint | True/True | False/False |
| 전체 진행/종지 확정 | 없음 | 없음 |

여기서 `V/M`·`V7/M`은 목표 A♭에 대한 template 전제 이름이다. F minor 국소 조성이나 secondary 기능을 최종 확정한 로마자 결과가 아니다. 세 번째 slot 및 두 번째 undeclared transition까지 포함한 완전 path는 보류된다.

### 추가음이 실제로 얼마나 남는가

3화음 가정에서 같은 slot 안의 D♭5 네 sounding occurrence는 다음과 같다. 시간은 모두 **4분음표 단위 global offset**, 범위는 `[start,end)`다.

| source sound | 관측 범위 | 음가 | 원 note/타이 |
|---|---|---|---|
| `sound_cae7b39ad108` | `[49,101/2)` | `3/2` | `note_2d60aad9c21b`, `note_b1e7cd2305c0`; `tie_8f5b04834d7b` |
| `sound_ba0fa309391c` | `[152/3,305/6)` | `1/6` | `note_e07ae5076fc3` |
| `sound_14db566a6e34` | `[51,52)` | `1` | `note_110b1f2983c7` |
| `sound_d3a0706d2872` | `[52,53)` | `1` | `note_2edca1a44074` |

합계 **11/3 quarter**가 3화음 가정에서 조건부 설명되지 않는다. 실제 2/2의 beat 수나 구간의 elapsed duration과 혼동하지 않는다. 첫 tied sound의 전체 범위는 `[45,101/2)`이며 분석 범위에서 잘라 보더라도 그 원타이/attack/앞 문맥을 잃지 않는다.

따라서 1281의 첫 전환 True를 근거로 1201을 버리면 악보에 실제 있는 D♭를 설명하지 않은 채 정답을 선택하게 된다. 반대로 D♭의 존재만으로 1201을 확정해도 실제 해결/지속/화음 경계의 부족한 전제가 사라지지 않는다.

### 뒤 마디의 해결을 찾되 연결은 발명하지 않음

1201의 마지막 source D♭5 `sound_d3a0706d2872 [52,53)`에는 현재 witness의 outgoing edge가 없다. 다음 slot에서 다시 나오는 D♭5 `sound_84691b622f05 [109/2,164/3)`는 C5 `sound_b4d0e1d7b1cc [164/3,329/6)`와 실제로 연결된다.

새 정책은 이 **재등장→하행 C**의 모양을 후속 전략 검증 대상으로 저장했다. 미연결 구간 `[53,109/2)`를 실제 rest/동일 musical voice/동음 연결로 자동 증명하지 않는다. Source D♭부터 뒤 C까지의 resolution credit 추가는0이고 원 ordinary False도 유지한다. 추가 raw lane/voice 경로 및 rest/동음 재등장 전략의 의미 검증이 필요하다.

## 4. 실제 전수 실행 결과

[정본 r2 report](../../../output/harmony-candidate-obligation-2026-10-04-r2/report.json). 같은 원 selector **2,315개를 control/linked에서 각각** 검사했다. 각 completion 안에서 exact extension pair **1,395개**를 모두 계산했다. 5key 가정별279쌍이며 다른 key 사이 쌍/credit union은0이다. 이는 여러 곡이나1,395개 독립 음악 사례가 아니다.

| 지표 | 무연결 control | 18edge linked technical probe |
|---|---:|---:|
| 전체 candidate path | 2,315 | 2,315 |
| exact triad/seventh pair | 1,395 | 1,395 |
| 추가 7음의 literal occurrence가 있는 쌍 | 645 | 645 |
| 추가음이 3화음 아래 일부 미설명인 쌍 | 625 | 605 |
| supported leading-tone context 발생 | 0 | 275 |
| supported seventh context 발생 | 0 | 0 |
| disconnected role occurrence 발생 | 595 | 235 |
| reappearance probe 발생 | 235 | 235 |
| 재등장 이후 ordinary seventh 형태가 있으나 원 연결 미증명 | 0 | 235 |
| 전체 path 증거 보류 | 2,315 | 2,315 |

275는 역할 단위 발생 수다. 단계44의 whole False→True20/joint False→True8과 다른 지표이며 정답 화음 수가 아니다. Linked의 대표 실패 kind 중 adverse first motion10, target 밖/nonmember75도 저장했다. 대표 kind는 우선순위로 한 개씩 집계하고 실제 복수 blocker 축은 row 안에 보존한다.

재등장 probe235개는 **고유 route 1개**가 여러 후보/key/partition 전제에서 반복된 것이다. 위 D♭→재등장 D♭→C가 그것이며235개의 독립 지연 해결 사례나 검증 양성이 아니다. 비교 쌍의 추가음에 관여한 고유 sounding source는23개다. Source guard와 관측 사실은 의미 확정과 구별한다.

실제 r2 **26.343초/exit0**, 하나의 decoded read 계정 **325,191,862B**다. Reader292파일(상위 report1/source snapshot1/review batch290), gzip3출력+report1의4파일 **1,546,675B**. Report를 제외한 decoded 출력18,583,480B이며 물리 bytes와 구별한다. 재읽은 것은 단계44가 검증한 snapshot이지 원589개 native/role 입력 전부가 아니다. Authority 복원이나 producer 재실행 없이 외부 report pin·physical SHA·literal lineage·동일 bundle role route를 대조했다.

정본 report SHA: `a935b0f75900d51377defee89c8e6a5b05914096ce2e6422a171700b8667fffc`.

## 5. 구현 파일과 재현

- [후보 경쟁 정책](../../../src/musicanote_harness/harmony_candidate_obligation_policy.py): 철자 형태, 추가음 설명, 완전 path 축, ordinary 실패와 재등장 probe.
- [저장자료 실행기](../../../src/musicanote_harness/harmony_candidate_obligation_trial.py): 외부 pin/전체 원 batch·위치/source·key/bundle/읽기·출력 예산/종료 보호.
- [전수 pilot](../../../tmp/harmony_candidate_obligation_pilot_20261004.py).
- [정책 검사](../../../tests/test_harmony_candidate_obligation_policy.py), [실행기 검사](../../../tests/test_harmony_candidate_obligation_trial.py).
- [출력 report](../../../output/harmony-candidate-obligation-2026-10-04-r2/report.json)의 artifact 목록에서 전체 원 scope/key/bundle과 양쪽 candidate-policy 파일의 길이·SHA·경로를 확인할 수 있다.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m unittest test_harmony_candidate_obligation_policy test_harmony_candidate_obligation_trial -v
.\.venv\Scripts\python.exe -B -m unittest test_completion_evidence_contrast test_completion_evidence_contrast_trial test_progression_evidence_review test_progression_evidence_review_trial test_native_progression_policy
```

Pilot의 r2 경로는 이미 존재한다. 재현 실행 때는 새 출력 경로를 명시적으로 바꾼다. 기존 r1/r2나 원본을 덮어쓰지 않는다. 기본20,000 pair 상한을 넘으면 쌍 비교 전체를 실패/보류하고 prefix만 완료로 저장하지 않는다. 부분 출력이 남아도 종료 report가 없으면 완전 실행이 아니다.

## 6. 검사·실패 이력·보존

최종 **신규26 PASS/25.511초**, 기존 completion contrast/review/native policy **97 PASS/89.143초**다. 새 검사는 genuine 작은 MusicXML→Core→native/role→review 입력을 사용한다. 물리 저장 실행기의 상위 report ancestry는 **합성**이므로 역사 코퍼스의 정확도/권한을 증명하지 않는다.

검사에는 추가음 손실 금지, V/V7 가정 차이, 미연결/반례, 실제 동음 reattack과 tie 구별, explicit rest 뒤 재등장의 미연결 보류, 불리한 첫 변화음 건너뛰기 금지, unknown key, full hold, microtonal 보존, 다른 completion/key 분리, 원음표/음가/route 변조 거부, 전체 pair 예산, native producer 재실행 금지, 원 batch 누락/외부 pin/예산/입력 변경/기존 출력 보존을 포함한다.

중간 실행 이력도 보존한다.

1. 최초14검사 ERROR: test fixture module의 없는 `kernels` alias를 참조했다. 직접 import로 교정했다.
2. 후속14검사 중1 FAIL: 첫 adverse note가 동시에 목표 nonmember이기도 했다. 단일 kind 기대를 수정하고 실제 두 failure axes를 모두 기록했다. 근거 gate 완화가 아니다.
3. 첫 actual 진입은 parent `full_archive_complete=True`를 잘못 기대해서 **출력 전 거부**됐다. 단계44는 한 context의 두 요청을 완전히 검사했지만 전체 역사 archive 완료는 False다. False를 유지한 채 개별 원 plan/terminal/batch 전수를 검증하도록 adapter 범위를 교정했다.
4. r1 actual26.890초/exit0는 이전 prototype 출력을 보존했다. 그 뒤 full-hold not-applicable·plan/terminal seal·원 key coordinate·구현 SHA 종료 보호를 추가하고 r2를 새 경로에서 전체 재실행했다. 숫자 변경은 없으며 r1과r2를 독립 음악 표본으로 합산하지 않는다.
5. 중간16/25검사 실행은 최종26 고유 검사에 중복 합산하지 않는다.

사후292입력+3출력의 physical 길이·SHA 오류0, report SHA 별도 확인, 모든 원2,315위치·1,395쌍·5key279쌍 및 selected/cadence/harmony 비승격을 대조했다. 선행79 code/test/runner/report SHA 변경0. 기존 별개 tracked5개와 원XML/Core/주석/이전결과·Git/서버/운영UI를 보존했다. 새5 Python 파일 AST, 개발 문서4개의 strict UTF-8 및 로컬 링크226개(오류0), `git diff --check`도 통과했다. 기존 tracked5개에 대한 LF→CRLF 경고만 있으며 새 오류는 없다. Commit/push0.

Code SHA는 정본 report에 core `05db3900a4076309de8da523eb0bbf06d3a7e01663d4f637cb9b2d481f257a30`, adapter `8f6974f6b01561d136555868ed7ceb2f09d350fb3bfcbab48b60aaedd9db98e4`를 저장했다. 현재 기능은 pure policy의 authenticity gate가 아니라 **이미 검증된 saved evidence 소비**다. Native ordinary의 의미 predicate를 새로 계산하거나 capability를 복구했다고 주장하지 않는다.

## 7. 다음 큰 기능 단위

1. **ordinary 외 지연/재등장/비인접 해결 전략**: source occurrence→실제 성부 후보→rest/동음 재등장→첫 변화 endpoint를 명시한 하나의 completion 안에서 검증한다. 같은 lane만으로 실제 성부를 확정하지 않고, adverse change·다른 화성 도착·source guard 실패·잘못된 target을 반례로 둔다. 이번 probe는 자동 연결 또는 credit의 허가가 아니다.
2. 이 전략과 기존 omission/분산형 근거를 **경쟁 화음·경계·조성 전체 path**에 통합한다. 이번 exact triad/seventh pair는 그 일부이며 일반 final-selection/최적화/확률 보정은 남아 있다.
3. Sonata 한 문맥에서만 성능을 주장하지 않고 기존 quartet 및 독립 작품·편성에서 검증한 뒤 악보 레이어/피드백에 반영한다. 구조 분석·편곡/작곡 생성의 소비 계약은 그대로 유지한다.

음악적으로 경쟁 해석의 우열을 고를 때 사용자의 악보 검수가 필요할 수 있다. 현재는 source/경로 가정이 부족한 기술적 보류이므로 사용자에게 정답 선택을 강요하지 않고 다음 검증을 진행할 수 있다.
