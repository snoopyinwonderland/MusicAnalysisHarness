# 단계88 — 정답 순위 보호와 오답 교정을 분리한 한정 학습

## 1. 목적과 사전 계약

단계87의 실제 Train 오답 경쟁 자료를 사용한다. 이미 맞는 화음 진행에도 큰 `loss`만큼 점수 차이를 벌리도록 요구하던 방식과, 실제 정답 순위를 보존하는 조건을 구별한다. 임의로 계수를 강화하거나 작품별 예외를 만들지 않는다.

이번 목표는 **한 번의 학습 → 모델 봉인 → 원118범위의 label-free ordinary 선택 → 개선/퇴행과 계산 보류를 함께 측정**하는 것이다. 검사가 통과하거나 학습 margin이 줄었다는 사실을 음악 정확도 상승으로 바꾸지 않는다. Dev/독립 Test/운영 승격은 이번 범위가 아니다.

입력은 단계87의 활성240대조(원198양수 + 새42), 실제 경쟁62개, 경쟁자를 완성하지 못한7범위다. 원67자기 비교는 삭제하지 않고 비활성 이력으로 유지한다. 같은 원118 Train 범위/23전체 악장/15작품군을 재분석하고 과거152제외 범위를 재투입하지 않는다.

## 2. 점수와 학습 조건

`gap = cost(wrong) - cost(stored reference-compatible target)`이다. 양수면 target이 더 싸다. 확률이나 human 확신도가 아니다.

1. 경쟁62개 중 초기 gap이 양수인 것에는 `min(raw loss, initial gap / 2)`를 **순위 보호 하한**으로 둔다. 해당 대조를 방문할 때도 이 하한만 요구한다.
2. 초기 gap이 0 이하인 경쟁은 이미 정답보다 싸거나 동률인 오답이다. 초기 상태부터 만족할 수 없는 hard 조건을 만들지 않고 원 `loss` margin으로 교정한다.
3. 나머지 활성 대조도 원 `loss` margin을 유지한다. 원 `loss`, 경로, 정답, 특징 값은 바꾸지 않는다. 새 요구 margin은 별도 계약이다.
4. 각 PA update 뒤에 **모든 초기 양수 경쟁의 실제35항 부분 비용 gap**을 확인한다. 하한을 깨면 1, 1/2, 1/4…1/2^20의 고정 순서로 줄여 첫 안전 update를 쓰고, 없으면 이번 방문은 갱신하지 않는다.
5. 각 후보는 먼저 소수6자리로 양자화하고 의미별 bounds/초기±.05 교집합에 clamp한 뒤 검사한다. 바뀌지 않는 unknown/고정 비격자 계수는 부수적으로 반올림하지 않는다.
6. 고정3epoch, cap1/20, 같은240대조, 총720방문이다. 갱신하지 못한 방문도 평균에 포함한다. 최종 평균은 양자화 후 안전하면 사용하고, 하한을 깨면 정확한 유리수 평균을 사용한다. 선형 하한을 만족하는 방문 상태의 정확한 평균도 하한을 만족한다.

기존35항 중 입력 불확실성3/기능적 해결4는 고정하고28항만 제한 조정한다. `known_both` whole-path 차원만 gradient로 사용한다. Whole unknown은 `None`이며0으로 채우지 않는다. 이미 관측된 부분 비용은 실제 점수와 보호 검사에 남아 있다. 다른 대조의 학습으로 그 계수가 바뀔 때에도 부분 비용이 보호 하한을 깨는지 확인한다.

**한계:** 보호62개는 초기 모델 아래서 찾은 경쟁자일 뿐이다. 학습 뒤 더 싸지는 새로운 경로까지 보호했다고 주장할 수 없다. 경쟁 채굴을 끝내지 못한7범위에도 보호를 증명하지 않는다. 이를 확인하려고 실제118범위를 다시 선택한다.

## 3. 추론·평가 분리와 보존

- 동일 원 graph/6raw cap/2M전이/협력적20초 guard를 사용한다. 검색 실패 시 부분 승자·재시도·옛 결과 fallback은 없다.
- 같은35항 exact delayed DP를 재사용하되 새 모델 ID/SHA와 계약으로 기록한다. Stage85 fit identity를 새 결과에 남기지 않는다.
- 학습 후 모델/계수/SHA를 먼저 봉인하고, 추론 호출에는 Train target/loss/보호 조건을 넘기지 않는다. 선택이 끝난 뒤에만 주석으로 평가한다.
- 이전 단계83/85의 봉인 경로와 old26 경로는 **과거 대조군**이다. 이번에 새로 실행한 arm이라고 부르지 않으며 실행시간도 새 arm 시간과 비교하지 않는다. 완료 공통집합과 전체118을 함께 보고한다.
- 각 case에 전체 원XML/IR 출처, 시간/성부/note·sound ID, 새 선택/보류, 과거 경로/target을 같은 새 계수로 재계산한 상세 비용을 저장한다. Core/원주석/기존 case/model/code 봉인은 수정하지 않는다.
- 비상업적 로컬 연구 계약을 유지한다. MusicSearch/Claude Phrase·Motif/Composition/화면/서버·Git 및 운영 weights는 변경하지 않는다.

## 4. 신규 구현과 검증

- `src/musicanote_harness/harmony_ordinal_protection_learning.py`: 보호 margin·안전 update·평균·모델 계약.
- `src/musicanote_harness/harmony_ordinal_protection_trial.py`: 봉인 부모/240자료 연결·모델 freeze·원118 ordinary 선택·전체 case/대조.
- `tests/test_harmony_ordinal_protection_learning.py`: margin, feasible guard, partial/unknown, 양자화, 고정·bounds·재현·권한/모델 변조 검증.
- `tests/test_harmony_ordinal_protection_trial.py`: no-overwrite, 부모 봉인 거절, fit/freeze/selection 순서, source/case 보존, 새 모델 ID.
- `scripts/validate_harmony_ordinal_protection.py`: 단계87의87모듈을 유지하고 신규2모듈 추가.
- `scripts/audit_harmony_ordinal_protection.py`: 봉인 source/model/vector/guarded fit 산술·상세 비용·지표 재생, 새 decoder 검색/Dev0.

최초 신규13검사는 모두 통과했다. 이후 whole-gradient가 unknown이어도 부분 비용 하한은 검사한다는 검사를1개 추가했다. Actual 전 최종 회귀 검사와 실행/감사 결과는 아래에 기록한다.

## 5. 실제 결과

최종 회귀944검사/89모듈이 PASS(failure0/error0), 120.782256초다. 전체 repository 검사나944곡 분석을 뜻하지 않는다. 최초 신규13검사의 실패는 없었으며 추가1개를 포함한14개가 이 회귀에 들어 있다.

학습은 완료했고 모델 `ordinal_protection_054552388d1f893bc43eab84`를118범위 추론 전에 봉인했다. 활성240대조/720방문 중506update, 요구 margin 만족177방문, bounds/양자화로 변화 없는37방문이다. Update 중19개는 전폭,487개는 1~16회 반분해서 안전한 step을 사용했다. 최종 평균은 소수6자리 양자화 후에도 안전했다.

초기 양수 경쟁56개는 전 update·최종 모델 모두 보호 하한 위다. 나머지6경쟁은 원loss를 사용하는 soft repair, 경쟁자를 찾지 못한7범위는 미보호로 명시한다. 정책 margin 합184.033706→180.225004, 원loss margin 합211.748685→207.598310, target보다 싼 활성 오답 대조87→85다. **이는240고정 대조의 진단일 뿐 실제118범위의 정확도는 아니다.** 단계85의265대조 margin과 직접 비교하지 않는다.

모델 SHA: `b6ff68e73bf6b5b9760107344f66f5c5626da2aa5c8b93ca061c21d6cbc74f38`.
회귀 receipt SHA: `4b0d90eee150d4685b4f87d51cc5ed9086f64d28ea2b4a90faa173209b4751b0`.

Actual은792.856201초/exit0에 완료했다. 같은118범위/23전체악장/15작품군/60,129원edge에서102 exact 선택/16wall 보류다. 단계83/85와 완료 집합이 동일해 보류 회복/새 보류 모두0이다. 같은 구간끼리 비교할 수 있지만 이번 학습에 사용한 Train 자료이고, 대조 모델의 경로는 과거 봉인 결과이므로 독립 평가/동시 실행시간 비교가 아니다.

| 비교 범위·지표 | 초기 역할35(단계83) | 이전 공동35(단계85) | 이번 보호35 |
|---|---:|---:|---:|
| 공통완료102의 진행 완전 일치 | 56 | 52 | 58 |
| 공통102 근음+구성음 시간 일치 | 78.3723% | 76.1959% | 79.3244% |
| 공통102 작품군 macro | 76.4567% | 74.4862% | 77.3503% |
| 공통102 exact 경계 F1 | 74.2138% | 72.8477% | 75.0000% |
| 전체118의 진행 완전 일치 | 56 | 52 | 58 |
| 전체118 근음+구성음 시간 일치 | 57.6840% | 56.0821% | 58.3848% |
| 전체118 작품군 macro | 55.7712% | 54.2084% | 56.4298% |
| 전체118 exact 경계 F1 | 60.8247% | 59.1398% | 61.5385% |
| 전체118 시간 coverage | 73.6025% | 73.6025% | 73.6025% |

초기 역할35 대비 변경2개가 모두 새 정답이고 기존 정답 소실0이다. 이전 공동35 대비는 변경12개/새 정답7/정답 소실1이므로 **모든 과거 모델의 정답을 보존했다고 주장하지 않는다.** Stage87 경쟁62개 중 초기 양수56개의 순위를 지킨 것과, 실제 전체 선택의 정확도는 별개로 확인했다.

old26 대조도 보존했다. 전체118에서 old26은118완료/58정답/시간77.5572%이고 이번 arm은102완료/58정답/시간58.3848%다. 공통완료102에서는 old26이53정답/시간78.8937%/macro76.9061%/경계F1 73.6196%, 이번이58정답/시간79.3244%/macro77.3503%/75.0000%다. 따라서 계산 보류가 있는35항 엔진을 old26보다 운영상 우수하다고 승격할 수 없다. 전체 비교의 old26 정답 소실6/새 정답6도 기록한다. 소실6 중5는 이번 계산 보류,1은 완료 후 의미 오답이다. 두 종류를 혼동하지 않는다.

여기서 ‘진행 완전 일치/시간’은 **화음 근음·구성음과 의미 경계의 주석 기준 일치**다. Roman·전위·국소 조성·NCT 유형 정확도까지 뜻하지 않으며 이 평가의 해당 성분은 eligible time0이다. 화면/운영 승격은 보류하고, 봉인한 이번 모델을 변경하지 않는 고정 Dev 진단으로 진행할 만한 소폭 개선으로 판단한다.

Report SHA: `8dad89e1130a0e2c742172a942a72732f0d09e3d0d7a2abc0ed9b45041f2435e`.
Run-contract SHA: `e927d1c59a747c343544ce4721662fcb3ca28946af761bf34ff58eca8af6a02a`.
Model-freeze SHA: `6ff22448afa8c3c2db45349ff7660883a08f7b31c187aa299bc4bb41e5f03d6e`.
이번 자료 사본 SHA: `764a226316cdbd5bbdb3e78fddeb32045d87bacb63b125c7d1eeabfadab20e8c`.

사후 감사 PASS/exit0이다. 4,340고유SHA/4,333봉인 input reload, 240벡터·동일 fit 산술·62경쟁/56하한/위반0, 118source/23package/60,129edge·542독립 상세 경로 비용·471scalar 전이·전체/공통 지표를 재생했다. 새 decoder 검색/추가 모델 저장/Dev0이다. Actual 이후 신규6code/test/script 수정0, input4,212/artifact122/code447 pins이며 중복 경로도 각 arm의 비용을 확인했다.

Audit SHA: `6e6eee39d55d0b73250b748ad50ee964833071ae629b86c3d1705c605b24227e`.

- [전체 report](../../../output/harmony-ordinal-protection-2026-10-06-r1/report.json)
- [봉인 모델](../../../output/harmony-ordinal-protection-2026-10-06-r1/model.json.gz)
- [사후 감사](../../../output/harmony-ordinal-protection-2026-10-06-r1/post-seal-audit.json)
- [944회귀 receipt](../../../output/harmony-ordinal-protection-validation-2026-10-06-r1.json)

원 Core/주석/부모 source·code·model·artifact/운영 weights·UI/서버/Claude Phrase·Motif/Composition/MusicSearch/별개 tracked dirty5/Git를 보존했다. Merge/commit/push·외부 API 호출0이다. 모든 변경·성과·남은 오류는 화성 **개발 문서**로 관리하며 인수인계 문서에 누적하지 않는다.

### 저장된 개선 사례 — Quartet op18-1 IV m269

범위 `cont_05a973a926c1c81874af`, quarter `[2147/4,1075/2)`에서 이전 역할35의 F–A–C–E 가설이 F–A–C 3화음으로 복구됐다. 이 사례는 단계85에서도 맞았지만 다른 구간의 퇴행 때문에 당시 모델을 채택하지 않았던 곳이다. 따라서 완전히 새로운 종류의 문제를 처음 해결했다고 부르지 않는다.

같은 **이번 계수**로 재계산하면 이전 가설 비용0.234645, 새/target 비용0.232268067로 gap +0.002376933이다. 비구성음 설명에서7음을 포함한 가설의 이익은−0.196910067이고 복잡도 비용은+0.199287이다. 두 점수의 균형이 바뀌어3화음이 실제로 선택됐다. 작품/마디별 예외나 ‘E는 항상 장식음’이라는 hard 규칙을 추가하지 않았다.

원 진행은 F3 `sound_a04ae05137a5`/`note_b437e86c2217` → E3 `sound_2499e7347984`/`note_bd140b9833c7` → F3 `sound_5b168af46292`/`note_9e6a4517a6cb`다. 같은 구간의 C4/A4 지지와 전후 전체 source를 보존한다. 조건부 이웃음 설명을 사용하더라도 이 결과를 완전한 NCT 유형 정답으로 승격하지 않는다.

- [이번 전체 case와5경로 상세 비용](../../../output/harmony-ordinal-protection-2026-10-06-r1/cases/cont_05a973a926c1c81874af.json.gz)
- [원 전체 MusicXML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/c421f89dc2ddceec5a94/source.musicxml)
- [원 전체 Canonical IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/c421f89dc2ddceec5a94/parent_ir.json)

원 XML SHA는 `8ff0da1ba6f57134e14e9152f30753c4f445e0315dfd567af882d5207626dd57`, IR 파일 SHA는 `aa3f85180cdf54fd19d5e1c9cb9b86fc63cc5200248c53e0ece93727579810ad`다. 전체118의 다른 개선/퇴행도 아래 최종 결과에 함께 기록한다.

### 두 번째 개선 — Chopin op30-2 m33–34

`cont_9d29b21fdced352125a1`, quarter `[98,101)`에서 B–D–F# 가설을 끝까지 유지하던 결과가 `[98,100)`의 B–D–F#, `[100,101)`의 F#–A–C# 가설로 나뉘었다. 못갖춘마디가1quarter이고 m33 시작97/m34 시작100이다. Printed measure와 sequential index를 섞지 않는다.

m33의 F#3/B3/D4 지지 뒤, m34 첫박의 F#2 `sound_182023fb276d`/`note_2facea6ba0e2`와 C#5 `sound_c311304f477e`/`note_66878f5d331c`는 `[100,101)` 동안 지속한다. 새 가설의 모든 구성음이 이 박에 실제 수직으로 있다는 뜻은 아니다. A의 미관측 비용을 포함해 유지 가설과 교체 가설을 전체35항으로 비교한 결과다.

이전 유지 가설의 이번 비용0.276273300, 새/target 비용0.268769722, gap +0.007503578이다. 유지 쪽 구성음 지지 이익−0.319638556/단순성 이익−0.077675200과, 비구성음 설명+0.240915300/문맥 경쟁+0.054238700/새 구성음 역할+0.109663333이 경쟁한다. 변화 하나만 hard gate로 화음을 자른 것이 아니다. 단계83/85 양쪽에 없던 새 주석 일치다.

- [이번 case](../../../output/harmony-ordinal-protection-2026-10-06-r1/cases/cont_9d29b21fdced352125a1.json.gz)
- [원 전체 MusicXML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/5c080f16d704fc413e11/source.musicxml), [원 전체 IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/5c080f16d704fc413e11/parent_ir.json)

XML SHA `6846ee87f5c7b3e32c24006ae4c6bc55150552499ee86fc5a01e7c11806ebe7d`, IR SHA `df4f80c2de24f1bf98dc78129a844d9cc14b1824890ee2eef7ac4df23bbd3d19`다.

### 남은 오류·이전 공동35 대비 소실 — Chopin op33-1 m18–19

`cont_059eaab892e6b5a75494`, `[54,58)`에서 화음 교체가 여전히 quarter55.75에 시작하며 target은56이다. m19는55에서 시작한다. E#5의 짧은 `[223/4,56)` attack `sound_532499b0a606`/`note_1a16568f3d08`을 뒤 C#7 가설에 일찍 포함한 형태다. 실제 C#4/G#4/C#5/E#5/B5 음군은56에서 시작한다. 이 초기 E#5를 확정 선행음/비화성음으로 승격한 것은 아니다.

초기 역할35에서도 오답이었고, 단계85는 이곳만56 경계로 고쳤다. 이번에는 초기 모델과 같은 조기 경계가 남았다. 이번 비용은 오답−0.149782317, target−0.146363857로 gap−0.003418460이다. 구성음 지지+0.010455563/단순성+0.015649781보다 비구성음 설명−0.029523804의 이익이 크다. Stage87에서 초깃값이 이미 음수였던6개 중 하나여서 feasible hard 보호가 아니라 원loss soft repair로 처리했고, 이번에는 해결하지 못했다. 이를 누락하거나 전역 정답 보호 성공으로 감추지 않는다.

- [이번 case](../../../output/harmony-ordinal-protection-2026-10-06-r1/cases/cont_059eaab892e6b5a75494.json.gz)
- [원 전체 MusicXML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/a10b687fd43585ed8ac6/source.musicxml), [원 전체 IR](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/a10b687fd43585ed8ac6/parent_ir.json)

XML SHA `1e5592088dc107ece936d427f216f3d46fa7106de309198df07f7d87d914c864`, IR SHA `108f32fe6dfba1ccb1308dfc0ea5cc0cd362c4b057e8e1494b9ed131ebe4ed65`다. Mozart K280의 A7 축소와 다른 지속 화음/과분할 오류도 전체118case에 유지했다. 작품/마디별 강제 교정은 추가하지 않는다.

## 6. 재현

작업 폴더는 `K:\Music Analysis`, `PYTHONPATH=src;tests`, UTF-8이며 `.venv\Scripts\python.exe -B`를 사용한다. 기존 output에 덮어쓰지 않는다.

```powershell
& .venv\Scripts\python.exe -B scripts/validate_harmony_ordinal_protection.py --prior-validation output/harmony-train-protection-validation-2026-10-06-r1.json --output output/harmony-ordinal-protection-validation-2026-10-06-r1.json
& .venv\Scripts\python.exe -B -m musicanote_harness.harmony_ordinal_protection_trial --output output/harmony-ordinal-protection-2026-10-06-r1
& .venv\Scripts\python.exe -B scripts/audit_harmony_ordinal_protection.py --root output/harmony-ordinal-protection-2026-10-06-r1
```

## 7. 다음 관문

Train에서 소폭 개선과 초기 역할35의 정답 소실0을 확인했으므로 다음은 **같은 봉인 모델의 고정 Dev 진단**이다. 기존 노출 Dev는 독립 Test가 아님을 유지하고, 전체/공통 완료 지표와 계산 보류를 함께 보고한다. 그 과정에서 추가 학습·checkpoint 선택·임의 epoch/bounds 확대·작품 예외를 만들지 않는다. 이 단계의 hard guard/Train 개선만으로 운영/편곡에 연결하지 않는다. 장문 계산 보류, 전체 Roman/국소 조성/전위/NCT 분류와 공개 모델·독립 작품 평가가 남아 있다.
