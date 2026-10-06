# 구성음 역할 상호작용 — 화음 확장과 실제 교체의 경쟁

개발 단계83. 단계82의 두 Train 대조가 같은7선형 항에 서로 반대되는 가중치 조건을 요구한 문제를 출발점으로 삼는다. 같은7항의 재학습 반복 대신 **두 조건부 역할 특징을 추가**한다. 기존26항과 단계82의7항 계수는 고정한다. 특정 작품/제목/마디/참조 label을 특징의 조건으로 사용하지 않는다.

## 1. 일반 규칙과 경계

새 특징은 원 Canonical Core의 음표·철자·원 sounding span·출처·명시 성부·박자를 읽지만 **선택된 화음 가설에 조건부인 외부 분석 증거**다. Core에 화성/NCT label을 넣거나 원 음표를 수정하지 않는다.

1. `supported_surface_seventh_extension_attack_exposure`: 앞 completed run의 표면3화음에 근음·3음이 실제 관찰되고, 다음 run에 새로 공격된 독점 구성음이 그 표면3화음의 가능한7음 철자와 맞는 정도다. 원7화음 어휘에서 같은3화음에7음 하나가 추가되는 경우만 비교한다. 해당 음이 앞 화음 아래 경과/보조/이중 보조 형태로 이미 조건부 설명되면 이 항에서 다시 세지 않는다. 원 sound ID별 겹치는 음가를 전체 원범위 note-time으로 나눈다.
2. `durable_nonextension_change_attack_coverage`: 앞 화음의 위 확장 후보로 설명되지 않는 새 독점 구성음 중, 원 sounding duration이 **그 음의 전체 실제 구간에서 적분한 기준박1개 이상**인 음들의 겹치는 시간 합집합이다. 전체 원범위 quarter폭으로 나눈다. 옥타브 중복/여러 성부가 같은 시간에 공급하는 것을 여러 번 세지 않는다.

첫 항은 ‘7화음은 무조건 유지’라는 관문이 아니다. 새7음이라도 실제 화음 교체·장식·생략/늦은 제시 등 다른 해석이 경쟁할 수 있다. 두 번째도 ‘긴 음이면 확정 구성음’ 또는 ‘화음을 반드시 바꾼다’는 관문이 아니다. 학습하는 soft score의 재료이며 원 후보/기존 비용/다른 근거를 남긴다. 음높이나 음가 하나로 NCT를 확정하지 않는다.

근음·3음 지지는 **앞 run 전체의 관찰 합집합**이다. 분산된 두 음이 반드시 동시에 울려야 한다고 요구하지 않는다. 불완전한3화음에서 없는3음을 만들어내지도 않는다. 알려진7화음의 ‘3화음→7화음 확장’ domain은 빈 domain으로, 미지원/근음 미상의 비3도 적층 signature는 이 분류가 unavailable인 것으로 구별한다.

기능적 근음과 표면적 근음도 분리한다. root F♯/members B-D-F♯ 후보는 표면 Bminor 6·4의 기능적 대안일 수 있다. 불일치로 자동 삭제하지 않으며, 새7음 역할은 B표면에서 계산하고 F♯분석 근음은 그대로 보존한다. 기능/종지의 확인을 주장하지 않는다. 전타음·지연음·선행음·페달·비인접 장식 해결 등 미완료 NCT 유형은 이 두 항으로 해결됐다고 하지 않는다.

## 2. Source·시간·불확실성·탐색 계약

- 새 attack은 **원 sound onset이 오른쪽 run 안에 있는 경우**다. 잘린 범위 시작에서 이미 울리던 음/붙임줄 뒷음을 새 attack으로 바꾸지 않는다.
- 0음가 장식음은 원 source/별도 ID 채널에 남긴다. 양수 노출·지속 음가 domain에 넣거나 `beat_extent(start,start)`를 호출하지 않는다. 장식음 때문에 기존 clock/voice 관문이 unavailable인 경우 그 null을0으로 바꾸지 않는다.
- 가능한7음은 철자 그대로 비교한다. 이명동음/MIDI pitch class로 몰아 합치지 않는다.
- 기존 v0.2의 명시 성부/중첩·grace/clock/history 관문과 앞 화음 아래 조건부 형태를 재사용한다. 철자/성부 또는 표면 역할의 불확실성은 null이다. 긴 음 판단에 필요한 박자가 없으면 두 번째 항은 null이며, 원 음가의 부분 관찰 합계를 알려진0/gradient로 사용하지 않는다.
- 시간은 Fraction이며 `[start,end)`다. 음 duration은 완전한 원 sounding span에서 읽고, 점수 노출은 원 평가범위/run에만 제한한다. 앞뒤 shape/anchor는 원2~3 completed union run을 사용한다. 범위를 넘어 새로운 harmony 후보/시각을 만들지 않는다.
- 원 three-run exact DP를 상속한다. 마지막 pending 전이 flush/동점/Pareto/최대6 raw·2M 비교·20초 cooperative wall guard를 그대로 쓴다. 동일 signature의 raw 조각은 합쳐 같은 점수가 된다.
- scalar 계산과 원 detailed V2 설명을 사용한 새 상세 receipt를 독립 비교한다. 새 항은 기존33점수와 별도 보관하며, 원XML/IR SHA·source sound/note IDs·원 span·역할 대안·전후 run을 각 packet에 저장한다.

## 3. 학습·검증 계약

단계82의 승인 Train **265대조/118범위/23전체 악장 source/15명명 작품군**을 그대로 사용한다. 새 target/negative 탐색·pool 갱신·Dev 활용0이다. 기존26 및 기존7계수 고정, 새2계수0초기화·사전3epoch·PA update cap1/20·계수±1/2·6자리 quantization·모든795post-visit 평균으로 한 번 학습한다. 전체 path의 해당 차원이 양쪽 모두 known일 때만 gradient를 쓴다. Zero-loss 보호 대조도 버리지 않는다. margin은 정확도가 아니다.

모델을 고정한 다음 원118graph/60,129edge에서 새 ordinary 선택을 한다. 원152제외 범위/계산 보류도 분모에서 숨기지 않는다. 전체와 공통 완료 범위의 기존26/단계82/새 모델 수치를 구별한다. 참조는 Train 평가·학습용이며 인간 유일 정답/검증 완료를 뜻하지 않는다. NC 로컬 연구 계약/기존 권한을 보존한다. 운영/UI/Core/Claude Phrase·Motif/MusicSearch/Composition/서버/Git 변경0이다.

최초 새18검사+기존850 = 868관련검사/80모듈 PASS·102.053898초였으나 실제 full-source의0음가 장식음 처리가 빠졌다. 이 회귀1개를 보완한 최종 **869관련검사/80모듈 PASS**, failure0/error0·87.866393초다. 전 repository suite나869곡/정답이 아니다. 분산 근음·3음, functional/surface root, 없는3음, 지속음/원 attack, 복합박자, unknown, 원 장식 설명, doubling 합집합, signed tiny DAG 전수/분할/0control/장식음/원자료 불변을 검사했다. 첫 Actual 전에7새Python UTF-8/AST/공백과 source-bound 두 실제 대조의 scalar/detailed 값도 확인했고, r2는 수정 후 전체 검사를 마친 다음 시작했다.

## 4. 구현 파일

- [조건부 역할 증거·exact 선택 연결](../../../src/musicanote_harness/harmony_member_role_scoring.py)
- [기존33고정·새2항 학습](../../../src/musicanote_harness/harmony_member_role_learning.py)
- [Train 실제 실험·source packets](../../../src/musicanote_harness/harmony_member_role_trial.py)
- [역할/선택 회귀](../../../tests/test_harmony_member_role_scoring.py), [학습/권한 회귀](../../../tests/test_harmony_member_role_learning.py)
- [전체 관련 validator](../../../scripts/validate_harmony_member_roles.py), [선택 없는 사후 재생 감사](../../../scripts/audit_harmony_member_roles.py)

## 5. Actual 상태

r1은32번째 scope `cont_3036b8c826ccbcbf5f0d` 특징 재생 중 `invalid_temporal_span`으로 exit1했다. 31개 partial vector packet/계약을 보존하며 model/freeze/완료 report/새 최종 선택은 없다. 이 source에는0음가 sound24개가 있고 연결 note는 모두 원 grace다. 원 sound를 삭제하지 않고, 새 양수 노출 domain과0음가를 구별하도록 보완했다. 새 테스트 초안은 zero non-grace를 만들어 기존 source 관문에서1ERROR였고, 검증된 grace의 full-source 투영을 재현하는 fixture로 바로잡았다. 이를 음악적 성공·resource 보류로 집계하지 않는다.

수정 후 r2는 **926.997719초·exit0**으로 완료했다. 사전 조건을 결과에 맞춰 바꾸지 않았다. 원118Train/23전체 악장 source/15명명 작품군·60,129edge에서102exact 선택/16wall 보류다. 단계82의104완료 중2개가 새로 보류됐고, 이전 보류가 회복된 경우는 없다. 실제 음악 경로 변경은 공통 완료102중2개다. 그중 전체 참조 일치가 새로1개 생겼고, 공통 완료에서는 이전 전체 일치의 소실0이다. **전체118에서는 기존 정답1개가 wall 보류로 빠져 새 정답1개와 상쇄된다.** 이를 ‘오답 선택1개’ 또는 ‘전체 정확도 개선’으로 바꾸지 않는다.

## 6. 학습과 실제 선택 결과 — 운영 미채택

265대조 중 새 known 비0 gradient47개, 두 새 축 모두 available164개, zero-loss 보호67개다.795post-visit·135update, epoch별 known collision149/148/148·update47/47/41이며 마지막 epoch에서 bounded-no-change6개다. 평균 새 계수는 첫 항 `84749/1000000 = +0.084749`, 두 번째 `-58597/200000 = -0.292985`다. 같은 pool의 margin 합은196.714029→194.219243으로 줄지만23대조는 악화했다. 고정 pool/평균 학습의 한계이며 새 정보47개나 margin을47곡의 개선·정확도로 보고하지 않는다.

| 비교 조건 | 전체 참조 진행 일치 | 근음+철자 구성음 시간 일치 | 작품군 macro | exact 경계 F1 | 시간 coverage |
|---|---:|---:|---:|---:|---:|
| 기존26 / 전체118 | 58/118 | 77.5572% | 77.5655% | 74.2358% | 100% |
| 단계82 / 전체118 | 56/118 | 58.4849% | 56.7434% | 61.9289% | 75.0042% |
| 새35 / 전체118 | 56/118 | 57.6840% | 55.7712% | 60.8247% | 73.6025% |
| 기존26 / 공통 완료102 | 53/102 | 78.8937% | 76.9061% | 73.6196% | 100% |
| 단계82 / 공통 완료102 | 55/102 | 78.3723% | 76.6140% | 72.9560% | 100% |
| 새35 / 공통 완료102 | 56/102 | 78.3723% | 76.4567% | 74.2138% | 100% |

공통102의 시간 일치는 같지만 작품군 macro는 낮아지고 경계 F1만 올라갔다. 전체118의 시간·macro·F1·coverage는 낮아졌다. **혼합 결과/운영 미채택**이다. 완료 subset은 resource-biased이며 전체 분모를 대체하지 않는다. 전체 평가 길이5993/24quarter·공통 완료4411/24quarter는 서로 겹치는 scope의 합이지 전체 작품 재생시간이 아니다. 참조 진행 일치는 근음+철자 구성음 및 의미 경계의 현재 평가 계약에 한정된다. 전체 Roman/quality/전위/국소 조성/NCT/종지의 독립Test 정확도가 아니다.

## 7. 실제 바뀐 두 경로와 계산 보류

### 7.1 Mozart K281-2 m6 — 빠진 교체 복구

`cont_b495db380fce051abef0`, global `[15/2,9)`. 기존은 C-E♭-G `[15/2,17/2)`→A♭-C-E♭ `[17/2,9)`였다. 새 선택은 E♭-G-B♭ `[15/2,8)`→C-E♭-G `[8,17/2)`→A♭-C-E♭ `[17/2,9)`로 참조 진행과 완전히 일치했다. m6의 E♭2/E♭3, 지속 G4/E♭5 뒤 C4 `[8,17/2)`와 A♭3/A♭4 `[17/2,9)`가 나온다. 새로운 C4는 `sound_de753a276549`/`note_543466cdfa0f`이고 원 음가1/2quarter=해당 박자 기준1박이다. A♭ 두 옥타브는 `sound_378d161da105`/`sound_d8801f666a83`이며 겹친 시간은 두 번 세지 않는다.

같은 새 계수에서 새 경로는 기존33비용 `12778457/90000000` + 새 비용 `-58597/300000` = `-4800643/90000000`다. 이전 경로는 `167449/2250000` + `-58597/600000` = `-209159/9000000`로 더 비싸다. 새 지속 교체 특징은2/3 대1/3이다. **C4가 앞에서 이미 이어진 음이라고 만들지 않고 원 attack을 사용했다.** 원 import의 exact alignment0이라는 역사도 packet에 남아 있으며, 현재 source-bound 참조 계약/승인 Train의 결과이지 인간 재승인 또는 자동 운영 학습 자격 부여가 아니다.

- [전체 XML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/ccbca834fb4f500d0cec/source.musicxml), [전체 IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/ccbca834fb4f500d0cec/parent_ir.json), [새/이전/참조 비용·출처 packet](../../../output/harmony-member-role-interactions-2026-10-05-r2/cases/cont_b495db380fce051abef0.json.gz).

### 7.2 Beethoven quartet op18-1 mv4 m111 — 경계 감소와 화음 퇴행

`cont_2cb186940b3312c2a145`, `[220,664/3)`. 이전은 A-C♯-E-G→D-F-A→A-C♯-E였다. 새 선택은 C♯-E-G `[220,441/2)`→D-F-A `[441/2,664/3)`다. 참조-compatible target은 A-C♯-E-G의 하나의 union run이다. 이전도 완전 일치는 아니지만, 근음+구성음 일치 시간은1/2quarter→0으로 **더 나빠졌다**. 단순히 경계2개가1개로 줄었다고 성공으로 보고하지 않는다.

원 m111 첫 A2/E4/G4/C♯5 `[220,441/2)`가 실제 존재한다. 뒤의 A3 `sound_0b64eadb4a87`은 원 `[441/2,445/2)`/2quarter·2기준박이며 `note_7de2a93b67ef`와 `note_bf6c18d0d95a`의 붙임줄이다. 새 왼쪽 C♯-E-G 가설에서는 이 A를 ‘새 독점/비확장 지속 구성음’으로5/8 지지하지만, A7 가설에서는 이미 A가 구성음이고 바로 앞 A2와 같은 철자 역할이다. **한 가설에서 새 독점이라고 계산되는 것이 음악적으로 새 화음이라는 뜻은 아니다.** D4/F4/C♯4/E4·상성부 B♭5-A5 등의 앞뒤 관계도 그대로 보존한다.

새 경로는 기존33비용 `38039137/116000000` + 새 비용 `-58597/320000` = `33595449/232000000`이다. 이전 경로의 같은 새 점수는 `1511799637/6960000000`, held A7 target은 `30698199/58000000`이다. 지속 교체 보상이 기존 비용 차를 넘어 근음 A2의 가치를 놓치는 선택으로 이어졌다. 같은 cue가7.1에서는 유용하고 여기서는 불리해 **새 항 하나를 보편 hard gate로 올리지 않는다.** 장식/유지/실제 교체·근음 증거의 공동 균형이 다음 과제다.

- [전체 XML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/c421f89dc2ddceec5a94/source.musicxml), [전체 IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/c421f89dc2ddceec5a94/parent_ir.json), [비용·원 sound/note IDs·전후 packet](../../../output/harmony-member-role-interactions-2026-10-05-r2/cases/cont_2cb186940b3312c2a145.json.gz).

### 7.3 새 wall 보류2개

- Corelli op01n03a `cont_ec75fd057b9e1d12feec`, `[59/2,63/2)`: 단계82의 B-D-F♯→E-G♯-B-D→A-C♯-E가 참조 일치였지만 새 검색은 wall 보류다. 저장 경로 재생 비용이 target과 같아도 fresh 완료/정답이라고 채우지 않는다.
- Mozart K281-2 `cont_677dba42ec4eb1b89d59`, `[57,117/2)`: 이전에도 참조 불일치였다. 새 검색 wall 보류, 새 역할 항은 unavailable이다. null을0/음악 판단 성공으로 바꾸지 않는다.

원14보류도 유지한다. 같은 guard에서 관찰한 계산 비용 차이는 전용 부하 조건의 speed benchmark가 아니며, 자원 문제와 음악적 오답을 별도 기록한다. 각 packet은 원 source/provenance·이전 경로·현재 계수 재생 비용을 포함한다.

## 8. 출발점의 A7와 Chopin은 아직 해결되지 않았다

Mozart K280-1 `cont_9a13eb950949fd01e0e7` `[763/4,192)`는 여전히 A-C♯-E→E-G-B다. 원 C♯4/E4 `[189,191)`, A4 `[190,191)`와 새 G5 `sound_d88119bdbc24` `[191,767/4)`가 extension3/8을 공급한다. 같은 새 점수에서 이 오답은 `23835899/120000000 ≈ 0.19863249`, held A7 target은 `517461/2000000 = 0.2587305`다. 기존33고정/이 두 경로만 비교하면 첫 계수가 최소0.24501036이어야 순위를 뒤집지만 학습 평균은0.084749다. **결과를 보고 임의로 올리지 않았다.**

- [K280 전체 XML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/53b63759291ef82365ab/source.musicxml), [전체 IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/53b63759291ef82365ab/parent_ir.json), [새/기존/target 상세 packet](../../../output/harmony-member-role-interactions-2026-10-05-r2/cases/cont_9a13eb950949fd01e0e7.json.gz).

Chopin BI105-2op30-2 `cont_9d29b21fdced352125a1` `[98,101)`의 target은 B-D-F♯ `[98,100)`→F♯-A-C♯ `[100,101)`다. C♯5의 새 지속 attack이 두 번째 특징1/3을 만든다. 원 lower F♯2 `[100,101)`와 다음 F♯3/A3/C♯4 `[101,102)`도 보존하지만 scope 밖 A를 앞당겨 발명하지 않는다.

**단계82 충돌의 functional held negative와 현재 literal held winner는 다른 경로다.** 앞선 epoch3 adversary의 분석 root F♯/표면 B-D-F♯ 유지 비용은0.3497951이어서 새 target `23811973/90000000 ≈ 0.26457748`보다 비싸졌다. 그러나 실제 literal Bminor held는 `2575631/10000000 = 0.2575631`로 여전히 더 싸 최종 선택은 병합 그대로다. 이 literal pair를 뒤집는 두 번째 계수 조건은≤-0.31402813이나 평균은-0.292985다. 고정 대조 하나의 순위 복구를 전체 경쟁 경로의 해결로 착각하지 않는다. 두 조건부 새 특징이 이전 선형 충돌을 **구별할 수 있게 한 것**과 일반 선택기가 올바르게 고른 것은 다르다.

- [Chopin 전체 XML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/5c080f16d704fc413e11/source.musicxml), [전체 IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/5c080f16d704fc413e11/parent_ir.json), [최종 held/target 상세 packet](../../../output/harmony-member-role-interactions-2026-10-05-r2/cases/cont_9d29b21fdced352125a1.json.gz).

모든118packet/118vector proof가 전체XML/IR 경로·파일 SHA/content SHA·원sound/note IDs·Fraction span·원 source locator·전후 문맥을 참조한다. Human validated는false이며 출처 annotation/target은 별도다. 동일 제목/마디 ID는 증거 설명·회귀 선택에만 쓰고 특징/학습 분기에는 쓰지 않는다.

## 9. 봉인·사후 감사·재현

Actual 시작 뒤 새 code/test/script 수정0,438code pins·240새 artifact pins·3,482input pins를 보존했다. 사후 감사는 **PASS·exit0**,3,729고유 SHA/3,721봉인 input 재로드·265Train 벡터/118source-vector packet·평균 모델 산술·118scope/23source·60,129edge·442독립 상세 경로 비용/833scalar-detailed 전이·전체/paired 지표를 재생했다. 새 탐색/Dev/추가 model 저장0이다. 코드 검증 통과와 음악적 정확도를 구별한다.

| r2 산출물 | SHA256 |
|---|---|
| report.json | `641806ea8fbfc94c135446a4134a57ff607e4fc581aad35b2274463102ccd340` |
| run-contract.json | `41eb7f4dc01abc6eff48c235fb56143c4860a64f603ff77ba850c1f58946073f` |
| model.json.gz | `3f2c10e7899b3e66696be82bc64e41530829cb48c23707c456dcc3231033d346` |
| model-freeze.json | `274d4ef4e8b2f2db3f43ad9e1ea6815ab17f473147ac7189acff0f314ad5f9f1` |
| training-vectors.json.gz | `02c9a9938513dc4188b84af9b55df3965ce7d712c81d2851ca1931c5fe6da999` |
| post-seal-audit.json | `95221af04e321c7500b3df64182b89ea65252d0c593145a3c2d00e246456f8df` |
| 최종 회귀 validation r2 | `b73151d97ab322eb62c4c0f754d2775b277cf09278359f6f78da0fa2a2ac0139` |

[실제 report](../../../output/harmony-member-role-interactions-2026-10-05-r2/report.json), [감사](../../../output/harmony-member-role-interactions-2026-10-05-r2/post-seal-audit.json), [회귀](../../../output/harmony-member-role-validation-2026-10-05-r2.json). 원 단계82 및 그 이전 봉인 파일은 덮어쓰지 않았다. 큰 최종 stdout은 잘려서 저장 JSON을 compact 조회했고, 사후 읽기 전용 테이블 조회1회는 scalar 항목을 dict로 가정해 AttributeError였다. 원 파일/계수/실험 조건 변경 없이 구별해 읽었다. r1 실패/초안 검사 오류를 숨기지 않으며 r2 Actual/감사 실패·중단0이다. 문서 작성 후3,729봉인 hash 변경0/7새Python UTF-8·AST·공백/정본22개 링크·메인/로그의 새 내용/언어·문자 QA를 재확인했다. 재현 경로 초안의 잘못된 validation 파일명과 메인 초안의 다른 언어 잔여는 실제 경로·한국어로 바로잡았고 `git diff --check`도 PASS다. 기존 tracked dirty5 외 새 tracked 수정은 없다.

```powershell
$env:PYTHONPATH='src;tests'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_member_roles.py --prior-validation output/harmony-context-refresh-validation-2026-10-05-r1.json --output output/harmony-member-role-validation-REPRO.json
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_member_role_trial --output output/harmony-member-role-interactions-REPRO
.\.venv\Scripts\python.exe -B scripts/audit_harmony_member_roles.py --root output/harmony-member-role-interactions-REPRO
```

사용 승인·원 부모 report/model/pool/code SHA가 일치해야 한다. 이미 있는 output/audit 파일은 덮어쓰지 않는다. 봉인 입력을 고치거나 재실행 결과가 다를 때 원 산출물을 삭제하지 않는다.

## 10. 다음 개발의 큰 단위

새 근거는 의미 있지만 아직 선택 균형을 고치지 못했다. 단순 재학습/계수 sweep/한 음악용 문턱을 반복하지 않는다.

1. **Train의 실제 경쟁 비용 분해:** 이전 정답·현재 승자·held/extension/functional/literal 대안까지 함께 보고, 근음·3음·지속음/장식 설명이 어디에서 중복 보상 또는 상쇄되는지 source-bound하게 진단한다. A7 pair뿐 아니라7.2처럼 기존 근음을 버려 ‘새 구성음’을 만드는 반례를 보호한다. Pool 밖 더 싼 경쟁 경로가 있으면 승인 Train에서 갱신하되 Dev를 후보/계수 튜닝에 쓰지 않는다.
2. **기존+새 점수의 제한적 공동 균형:** 기존33완전 고정/새2만 평균한 한계를 검토하고, 조정할 근거 그룹·초기 신뢰 범위·zero-loss 보호·epoch/한도를 사전 고정한 별도 버전으로 비교한다. 기존 모든 규칙을 즉시 풀거나 새7화음 강제를 넣지 않는다. 새 exact 선택/전체 분모/퇴행·wall까지 확인한 뒤 고정 Dev로 간다.
3. **승격은 검증 뒤:** 남은16자원 보류는 별도 성능 과제로 관리한다. 독립Test/공개 모델 공통평가, 전체 Roman/국소 조성/NCT/종지 및 화면/구조/작곡편곡 연결은 미완료다. 새 연구 계수는 현재 화면·운영 엔진에 넣지 않았다.

원 Core/주석/권한·Claude Phrase/Motif·MusicSearch/Composition·서버·Git·별개 tracked dirty5는 보존했다. 이 단계는 이론을 버린 것이 아니라 원음표와 이론상의 **가능한 역할**을 점수에 연결하고, 도움이 되는 곳/실패하는 곳을 실제 선택으로 확인한 것이다.
