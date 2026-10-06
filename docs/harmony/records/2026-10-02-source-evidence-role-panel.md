# 음표 근거 기반 후보 패널과 실제 역할 설명 검증

개발 기록 ID: `HARM-DEV-20261002-25`.

## 1. 목적과 직전 문제

직전 [native 역할·union 검증](2026-10-02-native-role-explanation-union.md)은 source 음가를 보존했지만, first-ID 기술 패널에서 실제 supported clause가 없었다. 철자 미결정 후보가 많았고 고정 cut이 일부 full triple을 잘랐다. 이를 실제 정확도 개선으로 보고하지 않았다.

이번 목적은 **원 음표 근거로 평가 가능한 후보와 경쟁 후보를 함께 제출하는 일반적인 연구용 패널**을 만드는 것이다. 후보의 화성 정답·비화성음 역할·해결 성공을 미리 보고 선택하지 않는다. 원주석 정답이나 특정 제목·작품·마디를 후보 규칙에 넣지 않는다. 양성은 해당 후보/성부 completion 아래 전제가 성립한다는 뜻이며, 음악가가 확인한 정답을 뜻하지 않는다.

## 2. 구현 계약

- `factor_source_evidence_panel.py`: authentic native session에서 발급하는 source-evidence 패널.
- `factor_source_evidence_trial.py`: 등록 full IR/scope의 제한된 append-only 실제 실행·저장.
- 두 모듈의 새 테스트: 기존 frozen 코드·검사·출력은 수정하지 않는다.

`prepare_panel(native_session)`은 native의 immutable state identity와 현재 source contract를 캡처한다. 새 frozen/HMAC/weak-registry handle을 요구하며 저장 lattice의 seal만으로 실행 권한을 발급하지 않는다. `panel_prepared`의 반환 dict를 수정해도 내부 state는 바뀌지 않는다. `validate_panel_prepared`는 동일 session에서 전체 패널을 다시 대조한다. 모든 source/current native state를 사용 전후 검사한다. 이는 발급 불변식이며 범용 runtime monkeypatch 보안 경계가 아니다.

기존 `native.compile_bundle_prepared → native.compare_prepared → roles.prepare_explanations → roles.explain_prepared`를 그대로 소비한다. Local/boundary/ordinary의 full-envelope·source/clock/pitch/attack·실제 연결·첫 불리한 변화·None/False 구별과 same-completion union 계약은 바꾸지 않는다.

## 3. 관찰 증거와 제안 순서

### 3.1 후보 평가

구조 위치는 음표 membership을 보기 전에 정한다. Native observed coordinates의 full-hold, 절반에 가까운 cut의 two-slot, 1/3·2/3에 가까운 서로 다른 cut의 three-slot이다. 음가 좌표는 정확한 rational quarter다. 같은 거리가 나오면 앞 좌표를 택한다. 고정 cut은 최종 화음 경계가 아니며 실제 관계를 자를 수 있다.

요청된 고유 interval 각각의 **모든 native origin**을 순회한다. 원 full scope sound와 정확한 overlap을 계산하고, source blocker와 temporal guard를 모두 확인한다. 후보 root/members와 원음의 step+alter를 비교한다. Octave-insensitive spelling membership이며 F♯와 G♭를 MIDI 동음으로 합치지 않는다. 긴 tie의 full sound와 원 notated-note refs는 유지한다. 역할 계산 단계에서 full envelope가 부족하면 미판정이다.

정수 철자 root/members가 있고 hypothesis blocker가 없으며 guarded member note-time이 양수인 후보를 평가 가능한 pool에 둔다. Source guard 실패 시간·membership unknown·nonmember는 별도 raw 시간으로 보존한다. Supplier ornament/NCT labels·event-state verdict·원주석은 support의 증거로 빌리지 않는다.

각 후보의 관찰치는 다음과 같다.

- interval에서 관측되지 않은 guarded member spelling 수.
- guarded pooled member note-time과 guarded root note-time.
- source-support별 raw 음가, 근거 sound/원 note refs와 full/observed spans.

Pooled는 분산된 제시와 동시 성부를 모두 합한 **note-time**이다. 음악의 elapsed duration·신뢰도·확률이 아니다. Missing spelling 수가 0이어도 실제 동시 수직 core·화음 정답·음악적 완결성을 인증하지 않는다.

### 3.2 제한된 비교 패널

제안 순서는 missing guarded spelling 수 오름차순 → member 음가 내림차순 → root 음가 내림차순 → exact spelling signature → origin ID다. 최종 화성 ranking이 아니며 selected/rank/confidence는 null이다.

각 slot에 첫 후보와 **root+members signature가 다른 첫 경쟁 후보**를 둔다. Provider alias가 같은 철자 signature를 반복해도 그것을 별개 경쟁 화음으로 증식하지 않는다. Native의 원 origin/pointer 자체는 삭제하지 않는다. Primary와 competitor를 각각 slot 전체에 이어 **최대 두 zipped complete paths**를 만든다. 혼합 Cartesian 조합을 탐색한 것처럼 표시하지 않는다. 실제 eligible-origin·signature Cartesian 분모와 제출하지 않은 조합을 저장한다.

각 complete path에는 모든 등록 key forms와 unknown을 유지한다. Multislot은 None transition vector와 일괄 explicit V7/M vector를 별도로 비교한다. V7/M은 기능 추론이 아니라 명시 조건부 가설/control이다. Primary/secondary, tonicization/modulation/cadence를 확정하지 않는다. 다른 화음 family·quality vector와 임의 경계는 이번 패널의 검증 범위 밖이다.

## 4. 한도와 실행 계획

Candidate scan, 반복 원 note 참조, extended members membership 비용, 정렬·selector 생성의 전체 logical-work 상한을 먼저 계산한다. 초과하면 whole panel hold하며 후보 prefix를 남기지 않는다. 알려진 후보 0과 budget/source/authority 때문에 평가하지 못한 null을 구별한다. 이 한도는 CPU·RSS·byte 인증이 아니다.

등록된 다섯 구간의 **observed coordinate 수 → source sound 수 → context key** 오름차순으로 최대 두 구간을 선택한다. 양성 결과·정답 라벨로 작품을 고르지 않는다. 이 규칙의 첫 두 등록 구간은 Sonata01-1과 Beethoven quartet이다. 짧은 저복잡도 scope 편향과 원 322문맥/1,013raw lanes·이번 실행/미실행 분모를 명시한다.

각 선택 구간은 기존 전체 IR와 exact scope를 사용해 native를 한 번 fresh prepare한다. 과거 native lattice/session의 권한을 재활용하지 않는다. No-link control과 bounded same-raw-lane greedy bundle 각각 하나를 full scope에 등록한다. 이후 같은 두 bundle 각각에 모든 패널 selectors를 사전 명시한 순서의 최대3개 batch로 제출한다. Batch의 전체 work가 초과하면 그대로 hold하며 결과를 보고 잘라 재시도하지 않는다.

사전 role query cap은 100,000,000이며 API default와 다르다. 이는 sound 수가 더 큰 quartet의 conservative union 상한을 고려한 계획이며 실제 시간 예측이 아니다. Native cap2,000,000·panel selection cap3,000,000·selector cap64·greedy 최대20links를 사용한다. 모든 cap은 실행 전 plan에 저장한다. 최종 실제 cap과 whole-hold 수는 실행 기록에서 대조한다.

기존 phase22/23/24의 파일 목록·SHA와 source/Core/parser/XML·운영 UI/구조/생성/Git은 보존한다. 신규 결과는 새 output 디렉터리에만 저장한다. 사례는 전체 score IR·scope·same bundle·candidate/key/path·원 음표/음가와 앞뒤 문맥을 역추적할 수 있도록 저장하며, 자동 결과를 human accepted/Gold로 바꾸지 않는다.

## 5. 검사·교정 이력

새 공개 API/실제 fixture 검사 **47개/24.282초**가 모두 통과했다. 42개는 genuine fixture·공개 발급/검증·권한/한도 검사이고, 5개는 이름으로 구별한 pure helper/storage 산술 검사다. 별도 기존 native 역할 회귀 **57개/72.631초**도 통과했다. 서로 다른 suite와 교정 전 실행을 중복 합산하지 않으며, 단위검사 수를 실제 작품 수나 음악 정확도로 표현하지 않는다. 저장 실행기 검사와 최종 실제 실행·독립 저장 검수는 아래에서 별도로 보고한다.

신규 공개 검사는 rational triplet·spelling alias·타이와 source closure·분산된 pooled 제시와 실제 동시 구성음의 구별·grace/microtone·attack 결손·모든 등록 key/None와 V7/M vector·known zero/unknown budget·불완전 inventory·native state identity/freshness·반환 자료 변조를 포함한다. 50-selector 공개 역할 통합 fixture는 사전에 정한 100,000,000 한도 아래 실행했다. 이는 실제 작품 50개나 50개 음악 정답이 아니다. ii→D7→G의 세 화음 fixture도 일반 전제 검사이며 실제 곡의 정답을 주입한 것이 아니다.

이 실행 직전 공개 패널과 테스트를 동결했다. 실행 전후 SHA는 같고, 기존 phase24 네 source/test의 SHA도 바꾸지 않았다.

| 파일 | SHA-256 |
|---|---|
| `factor_source_evidence_panel.py` | `9c479238a5a40cd8c13493af9044f279318bebedf04e04ed95718548adaa5a25` |
| `test_factor_source_evidence_panel.py` | `d9623cc8b0d69efd13cf3c43074b7a3b01aaf5333d7e3f735dbff4e5e7dd772c` |
| `factor_source_evidence_trial.py` | `eaa1bcc3193dc9a58b9f9f0f366616ee7d65237bfc34cce0302639798d4c1af1` |
| `test_factor_source_evidence_trial.py` | `066b8e9ba68801e9e5938c31570dc58e806914d74b04fdc988438c62d7bbb9f6` |

독립 검토에서 다음 planner 계약을 보완했다. 첫 고정 50-selector 상한은 two-coordinate의 fullhold-only 요청에도 과다한 selector 한도를 요구하고 known-empty를 보류로 바꿨다. 가능한 partition과 원 origin 수에서 selector 상한을 계산하고 certified zero를 완전 path에서 annihilate하도록 했다. 반대로 index 예산으로 origin materialization이 보류됐는데 catalog는 남은 경우에는 `origins=[]`를 known zero로 읽지 않는다. Requested/available interval, materialized inventory와 evaluation upper bound, parent native status/reasons/limits를 분리했다. 일부 known-empty slot 때문에 path 상한이0이어도 다른 requested interval의 ALL-origin scan이 미상이면 selection work/sorting은None이다. 순수 in-memory 4상황/9논리 조건 확인(약2.9초)은 공개 음악 검사 수와 구별한다.

초기 신규45개는 **41PASS·1FAIL·3ERROR/15.968초**였다. Source/test의 실행 전후 SHA는 같았다. 네 건은 테스트 가정이었다: 공격이 없는 E3를 anchor에도 유지해서 fixture 발급이 먼저 거부됐고, rest-only fixture는 parser의 score duration0 때문에 요청이 score 밖이었다. Microtone interval에도 positive primary가 있다고 가정했고, 한 번에50selectors를 작은 role cap으로 제출해 정상 whole hold를 계산 완료로 기대했다. 테스트의 scope/기대·사전 한도를 실제 계약에 맞게 정정하며, 원 source/XML/음악 규칙을 통과시키기 위해 수정하지 않는다. Rest-only score를 임의 보정하지 않고 single-pitch의 genuine empty supplier 사례를 별도로 사용한다. 이후 최종 재검사는 중간45개와 중복 합산하지 않는다.

저장 실행기의 초기 15개 storage-only 검사는 12.314초에 통과했다. 이 검사는 genuine native 계산을 mock한 JSON·SHA·목록·batch·분모·사례 저장 검사로, 공개 음악 전제 검사와 구별한다. 이후 root/독립 검토에서 완료·미상 집계와 사례 출처 문제를 발견했다.

- `max_contexts=0`과 known-empty panel에서 `all([])`로 제출 계산 완료가 켜질 수 있었다. 실제 제출 여부를 완료 조건에 포함한다.
- Witness 보류로 역할 account의 credit가 null인 경우 기존 집계 helper는 알려진 값만 합해 전체 credit를 0으로 보일 수 있었다. Known subtotal·미상 account occurrence 분모·전체 null을 분리한다. Whole native/role query가 보류되어 account 자체가 생성되지 않은 경우도 미계산 분모로 보존하고 전체 제출 요청의 합을 0으로 바꾸지 않는다. Whole panel hold의 미제출 selector 상한은 별도 기록한다.
- 같은 role/geometry/status가 서로 다른 context에 있으면 첫 context의 snapshots와 뒤 context의 candidate occurrence가 합쳐질 수 있었다. Case grouping에 exact context/full-IR/scope identity를 포함하여 source 문맥을 섞지 않는다. 후보별 prerequisites·blockers·credit clips는 각 occurrence 안에 유지한다.

새 실행기와 반례 검사를 보완하며 과거 phase24 helper와 저장 결과는 덮어쓰지 않는다. 실제 작품 결과를 보고 계산을 조정한 것이 아니라 실행 전 저장 계약을 교정한 것이다. 최종 저장 전용 **19개/9.844초**가 모두 통과했고, 별도 전체 호출 계측은 10.6647809초다. 앞서 통과한 15개에 19개를 더하지 않는다. 독립 재검토에서도 세 수정과 원 SHA·동일 completion·ordered batch·음표 역추적 계약이 일치했다. source/test 두 파일의 UTF-8·NUL/U+FFFD·공백·AST 검사도 통과했다.

실제 자료의 metadata-only preflight는 37.1888887초에 통과했다. 4,600개 고유 보호 경로와 원 phase22/23/24의 정확한 28/8/10파일 목록을 확인했고, 다섯 등록 context 중 source-size 순서가 `[1,0]`으로 Sonata01-1/Quartet을 택했다. 선택된 모든 source-note refs가 해당 full IR에 존재했다. 이 preflight의 native prepare·후보 비교·출력 생성은 모두 0이며 아래 실제 실행과 구별한다.

## 6. 실제 실행과 독립 저장 검수

### 6.1 단일 실제 r1

새 출력은 [source-evidence-role-2026-10-02-r1](../../../output/source-evidence-role-2026-10-02-r1/)이다. Root가 위 네 source/test를 동결한 뒤 **한 번만** 실행했다. Exit0, `source_evidence_probe_complete_not_selected`, 566.4350003000582초였다. 계산·원 입력/코드·산출물 보존 검사는 true이고, 실패·변경 목록은 모두 빈 배열이다. 결과를 본 뒤 후보·cut·예산을 바꿔 재실행하지 않았다.

| 항목 | 소나타 1번 1악장 등록 구간 | 현악사중주 Op.18 No.1 4악장 등록 구간 |
|---|---:|---:|
| source sounds / raw lanes | 23 / 3 | 53 / 4 |
| native 좌표 / 전체 interval catalogs | 17 / 136 | 17 / 136 |
| 보존된 전체 native origins | 11,381 | 7,285 |
| 패널 요청 interval / 평가 origin occurrence | 6 / 558 | 6 / 423 |
| eligible / rejected origin occurrence | 330 / 228 | 285 / 138 |
| 제안 complete paths / key hypotheses | 6 / 5 | 6 / 5 |
| selector / 실제 completion | 50 / 2 | 50 / 2 |
| 무연결 / greedy 실제 links | 0 / 18 | 0 / 20 |
| 계산 account / clause occurrences | 100 / 1,710 | 100 / 1,720 |
| supported / failed / unassessed clauses | 65 / 1,355 / 290 | 25 / 1,555 / 140 |
| account마다 보존한 raw note-time | 85/2 quarter | 53/2 quarter |
| selector occurrence 조건부 설명량 합 | 55/3 quarter | 25/2 quarter |

합계 68개의 ordered batch, 4개의 full-scope completion에서 **200개 selector occurrence/account의 raw 음가를 모두 보존**했다. 전체 3,430개 clause occurrence는 supported90 / failed2,910 / unassessed430이다. Local neighbor50, local passing25, boundary suspension10, ordinary leading-tone5가 supported다. 동일 원음/후보가 여러 key·vector·partition에서 반복되므로 90개의 음표·곡·정답이 아니다. Ordinary seventh와 anticipation의 supported는 이번 패널에서 0이다.

세 선택 partition의 eligible Cartesian origin-path 분모는 소나타 `111 / 3,650 / 27,918`, 사중주 `84 / 924 / 10,164`다. 각 partition에서 두 zipped path만 제안하므로 합계 **42,851개 eligible Cartesian paths 중 제안12 / 미제안42,839**를 보존했다. 이번 실제 signature-path 분모도 같은 값이었다. 이것은 세 fixed partition 안의 분모이며 전체 native grid의 다른 partition·origin 조합·기능 vector를 실행했다는 뜻이 아니다.

Panel/native query/role query/completion의 whole hold는 모두 0이다. Unknown 및 uncomputed account occurrence도 0이고, planned/submitted batch68 및 selector200은 일치한다. 원 전체 분모 **322문맥/1,013raw lanes** 중 이번 실행은 **2문맥/7lanes**, 미실행은 **320/1,006**이다. 다섯 등록 pool의 나머지 세 문맥도 이번에는 실행하지 않았다. 두 작품의 전곡 평가·전체 corpus 평가가 아니다.

Root의 별도 저장 후 stream SHA/목록 검사는 4.7068442초에 변경0으로 완료했다. Plan inputs4,600·current code/schema/tests331의 고유 union4,604개와 147artifact SHA를 합한 **4,751개 고유 경로**를 재대조했고, report를 포함한 정확 **148파일/16,302,378bytes**의 목록도 일치했다. 원 phase22/23/24의 정확28/8/10파일 목록은 preflight와 실제 실행에서 보존했다. 이 SHA 검사는 과거 producer의 cold 재실행이나 화성 정확도 검사가 아니다.

| 새 결과 파일 | SHA-256 |
|---|---|
| `report.json` | `9922f49ffb27e5cf890dc223c9fe741da70a176ef9c5ff95a5520b849d53cae3` |
| `run-plan.json` | `4ace6ef053378d01f4862abc9d2d071c00cda00c13f296fd6fc6e51a2860f3c1` |
| `context-index.json` | `46dfb87202f857f5d0eb3870d6241b46bebbcfde281e5211d398f5507ab4351f` |
| `case-samples.json` | `95344411331188da46f0f1af6d65017ccdc7649e431f24925e8ccf8cc1036b20` |

### 6.2 실제 음표와 조건부 해석 사례

[case-samples.json](../../../output/source-evidence-role-2026-10-02-r1/case-samples.json)에 supported/failed의 qualified candidate occurrence3,000개에서 추적한 **148개 source-scoped geometry/status** 중 24개를 저장했다. 각 role/status의 앞 세 geometry/source identity만 보관하고 미보관124개를 명시했다. 미판정430clause는 전체 explanation records에 유지한다. 샘플을 곡의 정답 대표나 전체 coverage로 표시하지 않는다.

실제 note snapshots에는 written pitch·원음가·global/onset-in-measure·printed measure와 sequential index·denominator beat·source reference가 있고, sound snapshots에는 full span·tie/attack/lane이 있다. 후보별 정확 origin/key/partition/bundle·prerequisites/실패 이유·credit clips·comparison/path/clause refs는 각 occurrence 안에 보존했다. 주변 음표까지 재현할 수 있는 전체 IR와 원 source-file 정보를 연결했으며 XML/Core를 잘라 덮어쓰지 않았다.

구체적인 저장 예시는 다음과 같다. 아래 명칭은 **현재 가설 아래 조건부 음형**이지 최종 NCT/기능 판정이 아니다. 마디/ID는 사례 위치이며 알고리즘 조건이 아니다.

- **소나타 m.14의 C5–B4–C5:** 원 notated duration은 `1/6, 1/6, 1` quarter다. A♭–C–E♭ 후보의 `[53,57)` slot에서 두 실제 링크와 member–nonmember–member가 성립했다. B4의 `[329/6,55)`만 설명해 1/6quarter를 credit한다. 동일 원음형이 여러 partition/key에서 나타나도 한 account 안에서는 sound별 union으로 한 번만 센다. 주요 sound refs는 `sound_b4d0e1d7b1cc`, `sound_3cf5468f4a36`, `sound_0ca9fedce095`다.
- **사중주 m.132의 C3–B♭2–A♭2:** 세 음은 각각 1/2quarter다. A♭ 계열 후보와 실제 두 연결 아래 가운데 B♭2의 `[525/2,263)`가 경과-like shape로 지원됐다. Source refs는 `sound_fe4de7d72284`, `sound_8c0d684da86e`, `sound_918d0111e2dd`다. 여러 slot에서 반복된 지원은 같은 원 세 음의 다른 조건이며 새로운 음악 사례 수로 더하지 않는다.
- **소나타 m.14→15의 C5–C5–B♭4:** 원음가는 `1,1,2`quarter, full spans는 `[56,57)`, `[57,58)`, `[58,60)`이다. 왼쪽 A♭–C–E♭–G♭ / 오른쪽 B♭–D♭–F–A♭ 후보 아래 실제 preparation/carry와 첫 하행 member가 성립하여 `[57,58)`의 1quarter를 설명했다. 이것만으로 박절·실제 화음·정확한 계류 명칭을 확정하지 않는다.
- **소나타 m.13→14의 G4–A♭4:** 두 음은 각각 4quarter다. E♭–G–B♭–D♭→A♭ 계열의 명시 ordinary 가설 아래 개별 leading-tone motion은 supported이지만, 저장 `whole_ordinary_template_satisfied=false`이다. 전체 V7 해결을 통과했다고 바꾸지 않으며 credit clips도 빈 배열이다. 한 역할의 성공과 전체 해결 의무의 성공을 구별한다.

같은 후보의 무연결 control도 저장했다. 실제 두 링크가 없는 control에서 local triple을 만들어내지 않으며, 위 local middle-note credit는 0이다. 실패·미판정은 경쟁 조건과 전제 결손을 보여 주는 데이터이며 corpus 주석 오류나 악곡의 음악 오류를 뜻하지 않는다. Source-size 패널은 관찰된 음을 많이 포함하는 추가음/확장 후보를 선호할 수 있다. 설명량의 크기만으로 그 후보를 최종 화음으로 고르지 않는다.

### 6.3 독립 검수와 최종 QA

별도 **독립 metadata 감사15,104확인/6.983132초**가 통과했다. Inputs/current code의 고유4,604경로, report 포함148output 및 원 parent28/8/10파일 목록·SHA를 전수 대조했고, 원 다섯 pool에서 source-size-selected2/7 및 전체322/1,013의 미실행 분모가 일치했다. Root의 stream SHA 재검사와 별개다.

다른 검수자의 **독립 saved-case 감사23,720확인/6.0129334초**도 오류0으로 통과했다. 24샘플의430candidate occurrence를 실제 context/fullIR/scope/origin/key/bundle/comparison/native-path/explanation/path/clause refs와 body SHA까지 추적했다. 원 음높이·notated/full duration·onset·measure/sourceRef/denominator-beat·sound/attack/tie/lane/credit clip, 3,430clause 및3,000→148→24/124분모·최대3/role/status의 source-scoped 정렬이 일치했다. 이430은 저장 샘플의 qualified candidate occurrence 수이며, 전체 미판정clause430과는 별개 분모다. 148output의 pre/post SHA·147artifact creation SHA 및 문서의 네 실제 음표 예시·individual ordinary motion과 whole-template 경고도 일치했다.

Root의 별도200account saved-read 산술 검사도 여섯 범주 합/raw85/2와53/2·union-counted-once·조건부 설명량 합185/6 및 두 no-link subtotal0을 확인했다. 이는 공개 producer 재실행이나 원음 전제의 독립 재판정이 아니다. 초기 inspection helper의 잘못된 `spans` field 접근은 읽기 전용 조회에서만 발생했고 실제 `point_indices`/partition field로 조회를 교정했다. 제품·자료·실제 실행에는 영향이 없다.

**독립 saved panel/role 감사1,352,361확인/17.2466763초**도 통과했다. 두 native lattice의18,666origin·supplier pointer/철자 대안·source full span 보존, 요청981origin의 source guard/pooled spelling 지원·정렬·경쟁 signature·zipped paths·50selector×4completion 및68ordered batch를 전수 대조했다. 200raw profile/account와3,430clause를 별도 Fraction/첫 실제 변화 oracle로 검사하여 prerequisites·None/False·status·route/full envelope·제안/실제clips·ordinary OR/AND·sound별 union과 여섯 음가 범주가 모두 일치했다. 전체185/6, 소나타55/3·사중주25/2의 조건부 설명량도 정확했다. 세 독립 감사는 별개 finite 실행이며 음악적 정답률·모든 논리 경로 평가나 새 cold producer 재실행으로 합산하지 않는다.

이 감사의 초기 가정 두 가지는 감사 script만 교정했다. 원 supplier alternative의 `root_spelling=null`을 허용하고, 요청 link 순서를 canonical sorted set과 대조하도록 했다. 큰 감사 스크립트가 Windows command-line 길이 한도를 넘어 stdin으로 전달한 것도 검사 실행 방식의 교정이다. Source/test/output·음악 규칙·실제 r1을 수정하거나 재실행한 것이 아니다.

추가 독립 legal-edge/budget 감사316확인/5.7932981초도 통과했다. 68batch의 native source-size snapshot·extreme/pair/route plan 및 role clause/reference/union plan을 재계산했고, 실제 native/role cap2,000,000/100,000,000이 일치했다. 마지막 독립 pre/post SHA 검사는2.0533231초에 보호 입력과147artifact의 고유4,751파일 변경0, report 포함148파일/16,302,378bytes의 누락·추가0을 확인했다. 정확 output inventory SHA는 `3a6dc610c81286115e49f93e47303d9983421dc38d9dc8271da13e96297e9c1e`이다.

최종 QA는 신규 source/test4·문서3의 strict UTF-8/NUL/U+FFFD/공백 검사, 4AST, 130로컬 링크를 오류0으로 확인했다. 네 source/test와 report/plan/index/case의 동결 SHA·147artifact SHA·정확148파일 inventory도 불변이다. Read-only `git diff --check`는 exit0이며 기존 별개 tracked5파일의 LF→CRLF 경고만 남았다. 원 parser/Core/음악 자료·기존 작업·운영 화면·Git은 변경하지 않았다.

## 7. 다음 판단 기준

이번 실제 역할 양성과 반례를 바탕으로 같은 후보의 no-link/actual bundle, 서로 다른 후보/partition의 동일 source 음가를 대조한다. 풀기 어려운 multicut·첫 변화·spelling/clock/key·polyphonic voice 문제는 종류별로 미해결 기록을 남긴다. 단순히 설명량이 크거나 원음 membership이 많다는 이유로 추가음/확장 후보를 최종 화음으로 결정하지 않는다. 실제 source-grounded 일반 비교를 확보한 다음 완전 진행의 선택 정책과 기존 전체 악보 뷰어 연결을 준비한다.

이번 패널의 fixed cut·두 zipped paths·None/V7/M vector는 제한된 검증 장치다. 박절, 실제 화성 리듬, 다른 ordinary/secondary family, 성부의 음악적 정체성과 full V7 해결 의무를 검토할 범위는 남아 있다. 무연결 control·경쟁 해석·whole hold를 버리지 않으며, 구조 분석/생성으로 자동 승격하지 않는다. 초기 rest-only fixture에서 드러난 parser의 score duration0도 이번에 교정한 것으로 표시하지 않는다. 일반 입력/시간축 검증을 확장할 때 별도 원인 확인과 회귀가 필요하다.
