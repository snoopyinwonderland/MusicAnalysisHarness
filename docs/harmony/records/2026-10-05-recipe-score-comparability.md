# 단계68 — 넓은 음 집합 후보와 화음 후보의 점수 비교 가능성

## 1. 해결하려는 큰 문제

단계67에서 tertian 화음으로 해석되지 않는 넓은 음 집합을 선택한 record가 10→16개로 늘었다. 미관측 3음·감/증5음·7음의 값은 `unavailable`로 올바르게 보존했지만, 가용 특징만 합하는 점수에서는 그러한 후보가 추가 비용을 피할 수 있었다. 이를 특정 작품의 후보를 금지하거나 unknown 관측을 0으로 덮어 해결하지 않는다.

이번 구현은 **음 집합을 알려진 화음 recipe로 설명할 때 남는 선언 구성음의 비율**을 별도 특징으로 만들고, 같은 승인 Train 대조에서 새 계수 하나만 결정한다. 원 graph·시간점·후보·source XML/IR와 기존 단계67 네 계수는 고정한다. 이것은 전체 NCT 분류, 국소 조성·Roman·전위·종지 완성이나 모든 화음 어휘의 구현 완료가 아니다.

결론은 **새 비용의 단독 추가를 운영에 채택하지 않는다**다. 미지원 shape 선택은 16→12record로 줄었으나 근음+구성음 시간 일치는 28.3314%→27.2812%로 퇴행했고, 완전16/51은 같았다. 경계 F1의 71.2121%→71.7557% 상승만으로 개선 완료라고 읽지 않는다. 이 실험은 ‘모르는 후보에 비용을 더하면 해결된다’는 가정을 반박하며, 시간별 구성음 지지와 생략/분산·지연/페달 설명을 함께 비교해야 한다는 다음 설계 근거다.

## 2. 일반 규칙과 정확한 의미

후보의 근음 철자를 `r`, 선언 구성음 집합을 `S`, 지원 recipe의 철자 집합을 `T`라 한다. 현재 어휘는 기존 `seventh_context.QUALITIES`의 M, m, o, +, MM7, mm7, Mm7, o7, %7, +M7, mM7이다. 기존 functional 6-4 표면 대안은 알려진 정확 recipe로 처리한다.

```text
residual(r,S) = min_T |S \ T| / |S|
outside_supported_recipe_exposure(run) = residual(r,S) × run폭 / context폭
새 비용(path) = 단계67 고정 비용(path) + 새 Train 계수 × Σ run residual exposure
```

- 근음이 있으면 같은 근음의 recipe만 비교한다. unknown 근음이면 선언 구성음을 각각 가능한 origin으로 비교하되, 후보의 근음은 여전히 unknown이고 기존 unknown-root 비용도 남는다.
- 철자를 비교한다. F와 E#를 MIDI pitch class가 같다는 이유로 합치지 않는다.
- recipe에 있지만 후보에 없는 음은 원음표나 후보에 삽입하지 않는다. 실제 제시되지 않은 구성음의 비용은 기존 특징이 맡는다. residual은 **후보가 주장하는 음 가운데 recipe 밖에 남는 음**만 센다.
- 같은 최저 residual의 recipe는 모두 receipt에 남긴다. 가장 가까운 recipe를 확정 화음이나 local key로 선택하는 단계가 아니다.
- 동일 signature의 인접 raw edges는 한 harmonic run으로 계산한다. 내부 분할로 비용을 피하거나 늘리지 않는다.
- 예: G/B/C/D/F는 G/B/D/F recipe 바깥의 C 때문에 residual `1/5`다. 이것이 C를 확정 경과음으로 뜻하지는 않는다. F/A/C/D/Eb/G는 F/A/C/Eb 바깥의 D·G가 남아 `2/6`이다.
- 3음 등 미지원 특징의 `None`/availability를 그대로 유지한다. 새 residual은 **어휘상의 거리**이므로 박자/음가가 미지원이어도 계산 가능하지만, 실제 NCT 근거가 관측됐다고 표시하지 않는다.

후보의 음 개수만 벌점으로 보는 방식과 다르다. C/E/G와 C/D/G는 모두 세 음이지만 전자는 residual 0이고 후자는 `1/3`이다. 기존 `extra_member_complexity`는 유지하므로 새 특징과 상관이 있을 수 있으며, 독립된 정보를 완전히 보장한다고 주장하지 않는다.

## 3. 중요한 한계와 채택 조건

현재 비교 어휘는 **3화음/7화음과 기존 6-4 대안에 한정**된다. 실제 증6화음·9/11/13화음·added tone·cluster 등 정당한 비-tertian/확장 화음도 양의 residual을 가질 수 있다. 따라서 이 항목은 soft 비용이지 불가능 판정/후보 제거 규칙이 아니다. 모든 음을 순간 수직으로 동시에 요구하지 않으며, 분산형의 실제 union/노출·원 비구성음 비용/생략·원 onset·tie·이전 해결 비용은 그대로다.

지원 어휘가 좁아 생긴 비용과 음악적 불가능성은 구별해야 한다. 특히 3/7화음 밖의 어휘가 많은 작품으로 운영 일반화를 주장하지 않는다. 새 계수 하나의 Dev 개선만으로 운영에 넣지 않고, 후보 ceiling·coverage·경계/전체 일치·퇴행과 미지원 shape 선택을 같이 보고한다.

## 4. 학습·평가 계약

기존 승인 비상업적 로컬 연구 계약과 원 source/라이선스 SHA를 유지한다. 학습은 기존 J2f update/collision의 중복 제거된 Train 경로 대조만 쓴다. 원 후보망의 target compatibility·loss·시간/ID/source 관문을 재확인한다. 단계67의 4계수는 그 model SHA로 고정하며 이번에는 residual 계수 하나만 5epoch, capped passive-aggressive `tau≤1/10`, `[0,1]`, 1e-6 rational quantization/평균으로 학습한다. Dev로 epoch·scale·checkpoint를 고르지 않는다.

단계67에서 role 특징 미지원 때문에 제외된 대조도 residual 자체는 계산 가능하므로 이번 학습 대조에 포함할 수 있다. 기존 support 특징의 미지원 여부는 별도 기록하며 0관측으로 바꾸지 않는다. 새 adversary를 탐색하지 않은 과거 negative pool의 편향/불완전성은 그대로다.

Dev는 같은 72구간·63원graph·44,204edge·14전체 source, 같은 raw cap·2M transition budget·원9보류를 사용한다. 두 arm은 `support_calibrated`(단계67 결과 그대로)와 `recipe_calibrated`(새 계수 추가)다. 두 arm을 새로 공동 선택하고 control 경로/비용/지표가 원 단계67 결과와 같은지 검산한다. Model고정→예측 저장/봉인→이번 단계67 평가 report 개방 순서를 따른다.

Train 부모 JSON에는 과거 Dev행도 함께 로드된다. 승인 Train행만 특징/loss/update에 쓰며 이번 reference report의 지연 개방이 **전체 이력에서 Dev 라벨을 본 적 없다는 뜻은 아니다**. 이미 노출된 Dev 실험이지 독립 blind Test가 아니다. Named family 분리와 악보/판본 전체 중복 감사도 구별한다.

## 5. 실제 결과와 검증

Train은 23악장 source package·15작품군의 **116구간/220대조**를 사용했다. Clock 보류0, 단계67 role 특징 미지원이었던 40대조도 residual 자체가 가용하여 포함했다. 새 계수는 `13929/62500 = 0.222864`다. 단계67 고정 네 계수 `.885548/.941206/.878012/.824534`는 그대로다.

새 계수 학습의 margin 부족 합은 `191.082033→190.885170`, 악화 대조0, update40회다. 매 epoch 220개 중 16개는 기존 margin을 만족하고 **196개는 새 특징 차이가 0**, 8개만 update에 기여했다. 실제 delta는 positive8/zero212/negative0이며 **220target의 residual은 모두0**이었다. 대조220개를 썼다는 것이 모두 새 정보를 주었다는 뜻은 아니다. 이 수치는 정확도가 아니고, 과거 negative pool의 정보 한계를 직접 드러낸다. 이번 target들이 지원 recipe에 들어간다는 사실과 원 corpus 전체가 단순 3/7화음으로 충분하다는 주장은 전혀 다르다. 아래 Dev 주석에는 G/C/D처럼 이 어휘 밖의 구성 집합도 있다.

Dev15package/9명명 작품군/72구간 중 원63선택/9보류·완전51/부분21·후보 ceiling36/51·coverage43.7106%를 유지했다. Named Train15/Dev9 family의 교집합0이며 악보/판본 전체 중복 감사는 아직 아니다. Dev 후보를 생성/제거하지 않았다.

| 지표 | 단계67 고정 control | 새 recipe 계수 추가 |
|---|---:|---:|
| 완전 구간 일치 | 16/51 (31.3725%) | 16/51 (31.3725%) |
| 근음+철자 구성음 시간 일치 | 28.3314% | 27.2812% |
| 같은 지표 작품군 macro | 52.8166% | 52.2322% |
| 근음 시간 일치 | 35.5309% | 35.4609% |
| 정확 경계 TP/FP/FN | 47/22/16 | 47/21/16 |
| 정확 경계 F1 | 71.2121% | 71.7557% |
| 미지원 role/양의 residual을 갖는 승자 record | 16 | 12 |

시간 지표는 원 eligible annotation time 전체를 분모로 하고 보류/coverage를 숨기지 않는다. 전체 Roman·전위·local key·종지·NCT 정확도는 이번에도 미측정이다. 단계66 시간27.0012%보다 새 결과가 높다는 비교만으로 단계67에서의 퇴행을 감추지 않는다.

변경 **6record/5고유 exact range** 중 주석 근음+구성음 일치 시간은 개선1·퇴행2·변화없음3이다. 퇴행2record는 동일 `[124,132)`의 중복이므로 독립 두 악보의 퇴행이 아니다. 이전29case를 모두 이어 저장했고 이번 변경은 그 안에 포함됐다. `case.record.source`는 원 전체 XML/IR와 SHA를 가리키고 원 note/sound ID·두 선택 경로·기존/새 비용·recipe 대안과 nullable 역할·사후 witness를 보존한다. Witness는 추론에 쓰지 않았다.

### 실제 사례와 실패 원인

- **Corelli op01n05a `[124,132)` — 큰 퇴행:** 단계67의 `[126,128)` G/Bb/D 3화음과 뒤 넓은 음 집합이, 이번에는 `[126,132)` 전체 G/Bb/D/F 7화음으로 합쳐졌다. 기존 경로의 새 비용 `.296369733`보다 합친 경로 `.286741708`이 작다. 주석 일치 시간은2→0quarter다. [첫 record](../../../output/harmony-recipe-balance-2026-10-05-r1/cases/e146c10d932bf1d6c977.json.gz), [같은 범위의 중복 record](../../../output/harmony-recipe-balance-2026-10-05-r1/cases/fde70cf5517606b2a93a.json.gz).
- **원음표 확인:** 해당 full IR에서 Bb4는 `[126,128)`, C5는 `[128,130)`, F4는 `[130,132)`에 있다. D5는 `[130,134)`의 원 tied sound다. `sound_b79ec00e79a1`/`note_311027c81246`의 F4가 **130부터만** 있는데, 기존 whole-run 존재 특징은 `[126,132)` 어디든 F가 있으면 미관측7음 비용0을 준다. 따라서 마지막에 제시된 구성음을 앞 구간의 화음 근거로 소급하여 과병합을 피하지 못했다. 실제 sustain이나 source onset을 조작한 것은 아니며, **시간적 지지의 해석이 너무 느슨한 점수** 문제다. 원 note exposure를 유지한 채 준비/해결·지연 도입·페달 및 화음 교체와 경쟁시켜야 한다. 이것을 특정 마디의 경계를 고정하는 규칙으로 만들지 않는다.
- **어휘 밖 주석의 위험:** 이전 반례 op01n04a `[38,39)`와 op01n04d `[74,75)`의 원 reference 구성 집합은 G/C/D다. 이 기록에서는 4→3 지연음을 확정하지 않지만, 그런 비-tertian 집합을 단순히 잘못된 화음으로 취급할 수 없음을 보여준다. 이 실험의 거리 특징은 여기에 `1/3`을 부과한다. 미지원 어휘 비용을 음악적 오답 비용과 동일시하면 안 된다. 두 기존 퇴행은 이번에도 복원되지 않았다. [op01n04a](../../../output/harmony-recipe-balance-2026-10-05-r1/cases/6a8ca6bf66e8cdc664fd.json.gz), [op01n04d](../../../output/harmony-recipe-balance-2026-10-05-r1/cases/5858062670a337d1b0d6.json.gz).
- **Corelli op01n04a `[169/4,43)` — 작은 개선:** G/A/B/D/F 구간을 줄이고 G/B/D가1/4quarter 맞았다. 다른 넓은 A/C#/E/F/G 집합은 남아 있어 전체 구간 성공은 아니다. [case](../../../output/harmony-recipe-balance-2026-10-05-r1/cases/ca9e8feb39a7aee296d1.json.gz).
- **Sonata09-2 `[245,250)` 및 quartet 두 범위:** 넓은 집합이 triad로 바뀌거나 그 경계가 움직였지만 주석과의 일치 시간은 늘지 않았다. 미지원 후보 선택 수 감소를 정확도 향상으로 보고하지 않는다. [Sonata](../../../output/harmony-recipe-balance-2026-10-05-r1/cases/4507aea481a2798f1b01.json.gz), [quartet06](../../../output/harmony-recipe-balance-2026-10-05-r1/cases/21c10b6cbe230806c970.json.gz), [quartet08](../../../output/harmony-recipe-balance-2026-10-05-r1/cases/2488cbcfbd69e6103674.json.gz).
- 이전 Corelli `[55,56)`의 구성음 생략 경쟁과 Chopin/Sonata07-2/quartet의 유지 사례도 저장했다. 새 계수의 효과가 없는 known-recipe 오류를 해결했다고 하지 않는다.

신규22 + 기존관련604 = **626검사/48모듈 PASS**, failure/error0, 61.297초다. Repository 전체 suite는 아니다. 신규 검사는 spelling/unknown/functional6-4·같은 음수의 다른 recipe·직접/인덱스·분할 불변·5 tiny DAG의 전수 최소경로·원 score/source 보존·Train 자격·고정4계수 포함 base cost·예측 봉인·변조/보류/덮어쓰기 금지를 포함한다. 첫 runner fixture의 reference cell을 tuple로 잘못 만든 1error는 실제 계약의 dict로 수정했다. 원 parser/source나 기존 검사 조건은 바꾸지 않았다.

Actual r1은296.956초/exit0(Train174.542초), 두 arm의 선택+독립 비용 확인 합은34.390/33.445초다. 단일 실행이며 속도 개선 benchmark로 읽지 않는다. Actual 중 새 code/test 파일을 수정하지 않았고 실제 실패 run은 없다. 문서 초안의 우발적인 다른 언어 placeholder는 즉시 한국어 설명으로 고쳤다.

사후 감사 PASS: **2,043고유SHA, Train220대조의 source 특징/고정 계수 포함 원 비용/compatible target/loss와 model fit 재생, 72×2조건의 지표, 원44,204edge codec 왕복, 독립 승자 비용126개, 14전체 Dev source, 29case/witness**를 검산했다. 감사에서 새 Dev 추론을 재실행한 것이 아니며 Train fit/대조는 재생했다. 단위 검사 통과 수와 SHA 일치를 음악적 정확도처럼 쓰지 않는다.

문서 갱신 후 새 변경12파일의 strict UTF-8·replacement character0·trailing whitespace0, 메인/로그/이번 기록의 로컬 링크278개·누락0을 확인했다. 봉인2,043SHA와 report SHA도 그대로다. `git diff --check` exit0이며 기존 tracked dirty5개의 LF→CRLF 경고는 보존했다. 별개 파일을 원복/정리하지 않았고 새 code/test는 actual 실행 이후 바꾸지 않았다.

## 6. 구현·산출물·재현

- [recipe scorer](../../../src/musicanote_harness/harmony_recipe_balance.py): 단독 거리·nullable 기존 특징 유지·정확 joint DP/독립 비용. 원 봉인 module의 globals/파일은 수정하지 않고 private binding으로 새 scorer를 구성한다.
- [Train 준비](../../../src/musicanote_harness/harmony_recipe_balance_training.py), [single coefficient learner](../../../src/musicanote_harness/harmony_recipe_balance_learning.py).
- [전체 trial](../../../src/musicanote_harness/harmony_recipe_balance_trial.py), [사후 감사](../../../scripts/audit_harmony_recipe_balance.py), [관련 회귀 실행](../../../scripts/validate_harmony_recipe_balance.py).
- [scorer tests](../../../tests/test_harmony_recipe_balance.py), [learner tests](../../../tests/test_harmony_recipe_balance_learning.py), [trial tests](../../../tests/test_harmony_recipe_balance_trial.py).

정본: [report](../../../output/harmony-recipe-balance-2026-10-05-r1/report.json), [model](../../../output/harmony-recipe-balance-2026-10-05-r1/model.json), [Train 대조](../../../output/harmony-recipe-balance-2026-10-05-r1/training-contrasts.json.gz), [run contract](../../../output/harmony-recipe-balance-2026-10-05-r1/run-contract.json), [예측 봉인](../../../output/harmony-recipe-balance-2026-10-05-r1/prediction-freeze.json), [사후 감사](../../../output/harmony-recipe-balance-2026-10-05-r1/post-seal-audit.json), [회귀 검사](../../../output/harmony-recipe-balance-validation-2026-10-05-r1.json).

Report SHA `1033719ce16be95fa6fde2619331aff2856a247f4e657ad4c9fc52fcf6a45ce8`.
Model SHA `0f00f2558d5f816cb90303fa33b18c8ce807459b542fbcbacf3f8ee839ac2200`.
Train dataset byte SHA `705fa1976d5f74238570c2e88884bab2ed5c51608fd56f8b24fd65161052de32`.
Validation SHA `ebd035df9a740cb3cac9a6b1d53aff79a4d2a8d2769934549e7d280d62278f59`.

기존 output을 덮어쓰지 않는 재현:

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_recipe_balance_trial --source output/harmony-support-balance-2026-10-05-r2 --output output/harmony-recipe-balance-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/audit_harmony_recipe_balance.py --root output/harmony-recipe-balance-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/validate_harmony_recipe_balance.py --prior-validation output/harmony-support-balance-2026-10-05-r2/test-validation.json --output output/harmony-recipe-balance-2026-10-05-r2/test-validation.json
```

## 7. 다음 큰 단위

1. **시간별 구성음 지지와 화음 유지/교체의 공동 설명**을 우선한다. ‘구간 어딘가에 한 번 등장’과 ‘앞 구간까지 같은 화음을 지지’는 다르다. 구성음의 원 onset/release·실제 분산형 반복·성부 준비/해결·페달/지연·근음 회귀를 경쟁 경로 아래에서 확인하고, 긴 화음과 짧은 교체의 비용을 함께 비교한다. 모든 구성음 동시 발음을 강제하거나 늦은 음을 무조건 교체로 보는 규칙은 만들지 않는다.
2. **지원 어휘와 조건부 장식 설명의 연결**을 정리한다. 단순3/7 밖의 변경/추가음·4–3 등은 후보 recipe와 source 조건을 명시한다. 모든 unknown을 tertian 오답으로 학습하는 정책은 금지한다. 책 개념 목록만 있고 실제 선택기에 들어가지 않은 항목도 명시한다.
3. **현재 decoder의 fresh Train adversary 대조**로 과거 negative pool의212개 zero-delta 편향을 보완하고, 점수 통합/비중복 작품군 평가를 진행한다. Dev를 보고 이번 `.222864`를 더 높이거나 좋은 구간만 골라 승격하지 않는다. 후보 부재와 선택 오류, partial annotation·어휘 미지원·진짜 성능을 분리한다.

운영 결정은 **미채택**이다. 이번 새 residual과 단계67 네 학습 계수 모두 production 승격은 하지 않았다. 전체 NCT·국소 조성/Roman/전위/종지, 남은 장문2M, 독립 test/공개 모델 비교·악보 운영/구조·작곡편곡 연결도 별도 미완료다.

원 Canonical Core·XML/주석·운영 UI·MusicSearch·Composition·Claude Motif/별개 dirty·Git는 그대로다. 이번 model은 연구 전용이며 운영 적용·외부 API 전송·commit/push는 하지 않는다.
