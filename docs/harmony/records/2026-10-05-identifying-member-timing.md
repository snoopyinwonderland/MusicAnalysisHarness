# 단계69 — 구성음의 첫 지지 시점과 늦은 화음 도입

## 1. 문제와 적용 범위

단계68의 recipe 벌점은 퇴행하여 채택하지 않았다. 이번 control은 **단계67 고정4계수**이며 단계68의 `.222864`는 사용하지 않는다. 원 후보망과 raw cap을 유지한 채 화음 이름과 경계를 함께 선택한다. 특정 작품/마디/정답을 규칙에 넣지 않는다.

관측 음이 구간 어딘가에 있다는 사실만으로 앞 시점의 화음을 지지한다고 볼 수 없다. 그렇다고 모든 구성음의 동시 발음을 요구하면 분산화음을 파괴하고, 늦은 음의 onset을 무조건 경계로 삼으면 지연음도 잘못 분할한다. 이번 구현은 이 문제의 **첫 구성음 도입 시점**에 한정된 연구 단계다. 구성음의 release 이후 지지·전체 페달/NCT·실제 화성 지속의 확정까지 완성했다고 하지 않는다.

## 2. 일반 규칙

명확한 3/7화음 shape에 대해 3음·감/증5음·7음 중 실제로 해당하는 역할을 계산한다. 각 역할의 **이번 run 안 첫 실제 sounding 지지**를 원 onset/release에서 구한다. 철자를 비교하며 이명동음을 합치지 않는다. 이미 지속 중인 구성음은 run 시작부터 지지하고, end에 시작한 음은 `[start,end)`에 포함하지 않는다.

```text
delay(role) = run 시작부터 first_positive_time까지의 지역 박자 단위 적분
raw(role) = max(0, delay(role) - 1박) / 전체 context의 지역 박자 단위 적분
value(role) = raw(role) × (준비된 순차 해결 후보가 있으면 1/2, 없으면 1)
late_identifying_member_exposure = 해당 역할 value의 평균
새 비용 = 단계67 고정 비용 + 승인 Train에서 정한 새 계수 × 위 특징
```

- 한 박의 유예와 `1/2`는 **Dev 실행 전 고정한 연구 가정**이다. 확률이나 보편 음악 법칙이 아니다. 박자는 실제 changing meter를 적분하고 6/9/12의 8분음표 박자는 기존 dotted-quarter 계약을 따른다.
- 역할이 전혀 제시되지 않으면 새 timing 비용은0이다. 원 미관측 역할 비용이 그대로 남으므로 이중 부과하지 않는다. 역할이 없는 triad의7음은 ‘미관측7음’이 아니다.
- unsupported/non-tertian/root-unknown shape, 알 수 없는 철자·박자는 unavailable로 남긴다. 정당한 G/C/D 같은 형태를 오답으로 처리하거나 후보를 삭제하지 않는다. 이 때문에 그런 후보는 이번 timing 특징으로 비교할 수 없는 한계도 남는다.
- 뒤에 처음 나온 구성음을 앞에서 울린 것으로 만들지 않는다. 첫 제시 이후 release만으로 추가 벌점을 부과하지 않는다. 따라서 전체 시간별 지지 모델이 아니라 **초기 소급 지지 억제**다.
- 인접 동일 signature raw edges는 한 harmonic run으로 계산한다. 조각을 나눠 timing 비용을 피할 수 없다.
- 변경 박자의 beat 정규화가 새 분모를 만들 수 있으므로 private exact integer scale만 확장했다. 근사/float 반올림이나 원 decoder/점수의 변경이 아니다.

## 3. 준비된 지연 도입의 조건부 설명

도착한 구성음과 앞 음이 검증된 같은 명시 성부의 연속 원 event여야 한다. 앞 음은 이번 run 시작 전에 시작하여 run 시작을 가로질러 지속하고, 그 끝 시각과 도착 onset이 정확히 같아야 한다. 앞 음은 이번 화음의 구성음이 아니고, 철자상 한 음계 단계·MIDI1~2반음으로 도착한다. 다른 성부, gap, 겹침/clock ambiguity, grace/repeat barrier, 실패한 원 history 관문은 할인하지 않는다.

조건이 성립하면 늦은 도입 비용을 절반으로만 줄인다. 실제 준비/도착 ID와 original span을 보존하고 `prepared_step_resolution_candidate`로 기록한다. 이는 **지연음 확정이 아니며**, 같은 화음 유지·장식된 도입·뒤 화음으로 교체가 경쟁한다. 선행 화음의 준비음 소속, 계류된 불협화음의 정확한 종류/강세, 화성 변화가 검증되지 않았으므로 suspension label을 확정하지 않는다. 원 nonmember 비용도 지우지 않는다.

각 receipt에는 first_positive_time·원 note/sound ID·실제 도입 전후 gained/lost spelling·지속 ID·지역 delay·유예/비용·조건부 해결과 경쟁 설명을 저장한다. Pedal·NCT·voice/harmony confirmation은 false다. 다음 단계는 이 증거를 실제 앞뒤로 선택되는 화음과 연결하는 것이지, 이번 할인 조건을 NCT 정답으로 만드는 것이 아니다.

## 4. 학습·평가 계약

원 NC 로컬 연구·Train 출처/권리 SHA 계약을 유지한다. 단계67 model SHA의 네 계수는 고정하고 새 scalar 하나만 동일 승인 historical contrasts에서 5epoch capped passive-aggressive로 학습한다. 이번 특징이 unavailable인 대조는 저장하되 학습에서 제외한다. Parent JSON의 역사적 Dev 행 로드와 승인 Train 행의 특징/loss/fit 사용을 구분한다. Fresh adversary를 만들지 않은 과거 negative pool의 한계는 남는다.

동일72 Dev 구간/63 원graph/44,204edge/14 전체 source를 두 arm으로 새로 선택한다. Model 고정→72 예측 봉인→단계67 reference report 개방을 지킨다. 기존9 보류를 재시도하지 않으며 ceiling/coverage·부분 주석을 유지한다. 이전29 case를 이어 저장하고 새로운 변경도 추가한다. 이미 노출된 Dev이며 독립 blind Test가 아니다. 좋은 구간만 골라 보이거나 Dev로 유예/계수/epoch를 조정하지 않는다.

## 5. 구현·검증·실행 결과

구현 파일은 [timing scorer](../../../src/musicanote_harness/harmony_member_timing.py), [Train 준비](../../../src/musicanote_harness/harmony_member_timing_training.py), [단일 계수 학습](../../../src/musicanote_harness/harmony_member_timing_learning.py), [joint trial](../../../src/musicanote_harness/harmony_member_timing_trial.py), [독립 사후 재생](../../../scripts/audit_harmony_member_timing.py), [관련 회귀 실행](../../../scripts/validate_harmony_member_timing.py)다. 봉인된 기존 module은 바꾸지 않고 private dependency binding을 사용한다.

신규 [scorer 검사](../../../tests/test_harmony_member_timing.py), [Train 안전 검사](../../../tests/test_harmony_member_timing_learning.py), [봉인/원source/보류 검사](../../../tests/test_harmony_member_timing_trial.py) **25개 통과** 후 actual r1을 시작했다. 초기 compound-meter fixture를 실제 source 계약인 `(6,8)` 대신 dict로 잘못 만들어1failure가 났고, 원 구현/검사 조건을 완화하지 않고 fixture를 수정했다. 재사용 TestCase를 이름만 바꿔 import하면 unittest가 이전 클래스도 수집하는 문제는 module import로 바꾸어 중복 집계를 제거했다. 37개라는 초기 실행 수를 새 검사 수로 보고하지 않는다.

신규25+기존관련626=**651검사/51모듈 PASS**, failure/error0, 64.810초다. Repository 전체 suite는 아니다. Actual r1은304.321초/exit0(Train173.221초), 두 arm의 선택+독립 비용 검산은36.795/35.174초다. 단일 실행이며 속도 benchmark가 아니다. Actual 실행 뒤 code/test는 수정하지 않았다. 재사용 Train 준비 helper의 stdout에 `[Train recipe]`라는 이전 이름이 남지만, 실제 row/model/feature version은 member timing이고 recipe 비용은0이 아니라 **사용하지 않는다**. 이전 비용의 private binding과 새 timing scorer/learner를 구별한다.

Train23악장 source/15명명 작품군의116구간/220대조를 모두 저장하고, timing unavailable40대조를 제외한 **104구간/180대조**로 새 scalar `.248879`를 정했다. Delta positive8/zero172/negative0이며180target의 timing 값은 모두0이다. 매 epoch16margin satisfied/156feature collision/8update, 총40update다. Margin149.754271→149.500133·악화0은 정확도가 아니다. Timing에 정보가 있는8대조는6명명 작품군에 속하므로180대조가180개의 새 학습 정보를 준다고 말하지 않는다. Fresh Train adversary를 우선해야 할 이유다.

| 지표 | 단계67 고정 control | 새 timing 계수 추가 |
|---|---:|---:|
| 완전 구간 일치 | 16/51 (31.3725%) | 16/51 (31.3725%) |
| 근음+철자 구성음 시간 일치 | 28.3314% | 28.8915% |
| 같은 지표 작품군 macro | 52.8166% | 53.1500% |
| 근음 시간 일치 | 35.5309% | 35.5309% |
| 정확 경계 TP/FP/FN | 47/22/16 | 47/23/16 |
| 정확 경계 F1 | 71.2121% | 70.6767% |
| timing 미지원 shape를 포함한 승자 record | 16 | 17 |

원63선택/9보류·완전51/부분21·ceiling36/51·coverage43.7106%는 같다. Train15/Dev9 named family의 교집합0이나 악보/판본 전체 중복 감사는 아니다. 근음+구성음 전체 eligible time을 분모로 하고 partial/unavailable을 숨기지 않았다. 완전 Roman·전위·국소 조성·종지/NCT 정확도는 측정하지 않았다.

**변경2record/2고유 범위: 시간 개선1(+2quarter), 변화없음1, eligible-time 퇴행0.** 경계 FP가1개 늘었으며 전체 성공 수도 같다. **혼합 결과/운영 미채택**이다. 무평가 구간의 변경을 성공이나 실패로 세지 않는다.

### 실제 사례와 반례

- **Corelli op01n05a `[120,132)` — 부분 개선:** 기존 `[126,132)` G/Bb/D/F 7화음 가설의 F4는 `sound_b79ec00e79a1`/`note_311027c81246`로 `[130,132)`에만 제시된다. 원 박자 단위는2quarter이므로 delay4quarter=2박, 유예1박 이후 역할 raw1/6·3음/7음 평균1/12다. 기존 경로의 새 비용은 `3352163/12000000=.279346917`이고 새 `[126,128)` G/Bb/D + `[128,132)` G/B/C/D/F 경로는 `1039339/4000000=.259834750`다. Gminor2quarter가 주석과 맞아 시간 일치가2quarter 늘었다. 그러나 주석 Gminor는 `[126,130)`이고 뒤 G7은 B natural이므로 **128의 새 경계와 뒤 넓은 집합은 여전히 잘못되거나 미완료**다. F onset130을 무조건 경계로 고정하지 않은 공동 비교지만, 이 때문에 완전 성공은 아니다. [새 사례](../../../output/harmony-member-timing-2026-10-05-r1/cases/f9c857091098f6748d8d.json.gz).
- **같은 source의 기존 `[124,132)` 두 record는 그대로:** 단계68 recipe가 이 범위를 퇴행시켰지만 이번은 그 recipe를 쓰지 않는 단계67 control 위의 실험이다. 따라서 단계68 대비 복귀를 이번 timing의 신규 개선으로 계산하지 않는다. 개선된 `[120,132)`는 그 범위를 포함하는 다른 scope이므로 독립 두 곡의 성공도 아니다. 기존 source XML SHA `b767273cb4533fe347c15bac1dff36452ee9cc0ad6f669003c1ad641ac855f60`, IR content SHA `764ccc072f2164f90e993f4e850ef96bc2bd54e46e35422b19477992b4d38203`를 그대로 참조한다.
- **Sonata09-2 `[272,280)` — 미평가 해석 변경:** C/E/G의 E는276에 처음 나타나 timing3/8이 붙었다. 선택기는 `[272,279)`를 G를 분석 근음으로 한 C/E/G functional6-4 대안으로 바꿨다. 이 대안의 timing role은 unsupported로 비용을 피한다. 원 reference가 두 구간 모두 `pedal_reference_projection_unsupported`이므로 eligible time0이고 정확도 개선/퇴행으로 판단할 수 없다. 근음/페달/6-4와 null 특징의 공정 비교 문제가 남는다. [새 사례](../../../output/harmony-member-timing-2026-10-05-r1/cases/2245ff24fed657cc9072.json.gz).
- 기존29case를 모두 이어 저장하고 새2case를 추가해 **31record/29고유 exact range**를 보존했다. 원 전체 XML/IR·앞뒤 source context·ID·두 선택 비용·첫 역할 도입·사후 witness를 저장했다. 보존된31case의 두 arm 경로 receipt에서 준비된 해결 할인 사례는0이다. 따라서 합성 검사 통과가 corpus에서 이 할인의 음악적 효용을 검증했다는 뜻은 아니다.

독립 사후 검산 **PASS: 2,049고유SHA·220Train대조의 source 특징/고정계수 포함 비용/compatible target/loss 재계산·eligible180의 model fit 재생·72×2지표·44,204원edge codec·126독립승자 비용·14전체source·31case/witness**를 확인했다. Dev 새 추론은 audit에서 재실행하지 않았으며 Train fit/대조는 재생했다. [감사 정본](../../../output/harmony-member-timing-2026-10-05-r1/post-seal-audit.json). 검사 통과 수를 음악적 정확도로 읽지 않는다.

정본: [report](../../../output/harmony-member-timing-2026-10-05-r1/report.json), [model](../../../output/harmony-member-timing-2026-10-05-r1/model.json), [Train 대조](../../../output/harmony-member-timing-2026-10-05-r1/training-contrasts.json.gz), [실행 계약](../../../output/harmony-member-timing-2026-10-05-r1/run-contract.json), [예측 봉인](../../../output/harmony-member-timing-2026-10-05-r1/prediction-freeze.json), [회귀 검사](../../../output/harmony-member-timing-validation-2026-10-05-r1.json).

Report SHA `c6bced83e4c63681543cf54b84a5de243cec7f8af2d8fc024385460cb9d4ecd4`.
Model SHA `c979d364221f7f802ea3b317a0dceea664fbd39fe10c79e15174d8a6f15c481d`.
Train dataset byte SHA `01aab1c3a092783dded89b536f1e28e4dbe96654200bc4ab550b034e1fda077c`.
Validation SHA `7197c59417dfd26464b84fa1ffa14bed7890d39cbe1a2e685d2b08f5f086c929`.

문서 갱신 후 새 code/test/script 및 메인/로그/이번 기록12파일의 strict UTF-8·replacement/우발적 다른 언어 표기·trailing whitespace를 확인했고 로컬 링크275개 누락0이었다. 초안의 우발적인 다른 언어 표기는 바로 한국어로 교정했다. `git diff --check` exit0이며 기존 tracked dirty5개의 LF→CRLF 경고는 보존했다. 별개 파일을 원복하거나 정리하지 않았다.

## 6. 재현

기존 출력은 덮어쓰지 않는다. 새 output 이름을 사용한다.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_member_timing_trial --source output/harmony-support-balance-2026-10-05-r2 --output output/harmony-member-timing-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/audit_harmony_member_timing.py --root output/harmony-member-timing-2026-10-05-r2
.\.venv\Scripts\python.exe -B scripts/validate_harmony_member_timing.py --prior-validation output/harmony-recipe-balance-validation-2026-10-05-r1.json --output output/harmony-member-timing-validation-2026-10-05-r2.json
```

## 7. 사용자 질문 — 재즈 화성 포함 여부

사용자는 이번 진행 중 “여기 재즈 화성 이론도 포함이 되어 있나요”라고 질문했다. 저장된 책 목록과 현재 코드·계획을 확인한 답은 **공통 요소 일부는 있으나 체계적 재즈 프로파일은 미완료**다.

- `seventh_context.QUALITIES`에 기본3/7화음, `harmony_extended_candidates`에 dominant7 기반의 일부9·11·13음 후보가 있다. 이 후보 코드는 고전/낭만 교재 프로파일임을 명시하며 재즈 일반 문법이나 모든 후보의 현 선택기 적용 완료를 주장하지 않는다.
- `K:\MUSICANOTE\musicanote-ai-local\books`에 David Berkman의 *The Jazz Harmony Book*, Nettles/Graf의 *The Chord Scale Theory & Jazz Harmony*, Bill Dobbins의 *A Creative Approach to Jazz Piano Harmony*, *A Chromatic Approach to Jazz Harmony and Melody*, Steve Larson의 *Analyzing Jazz* PDF 파일이 있다. **파일 목록 확인이지 책 내용 분석/규칙 구현 완료가 아니다.** 이번 질문으로 원책을 복제하거나 장별 흡수 작업을 시작하지 않았다.
- 재즈 보이싱·rootless/shell·altered tensions·대리화음·코드–스케일/선법적 문맥과 재즈 종지의 체계적 구현·정확도 검증은 별도다. 고전의 NCT/해결/종지 조건을 재즈에 전역 강제하지 않는다.
- 확장은 같은 Canonical Core를 공유하되 별도 versioned profile·case/split/score contract에서 검증한다. 현재 학습기의 narrow3/7 role 특징만으로 재즈 전체를 분석한다고 표기하지 않는다.

## 8. 운영 및 남은 범위

이번 결과는 **운영 미채택**이다. 현재 연구 결과는 UI·Core/XML/원주석·MusicSearch/Composition/Claude Motif/별개 dirty·Git에 적용하지 않는다. API 전송·merge/commit/push0. 전체 Roman/국소 조성/전위/종지/NCT, 긴2M 보류, 독립 test/공개 모델 비교·편곡/작곡 적용은 미완료다.

다음 큰 작업은 **현재 joint decoder가 실제로 고르는 fresh Train 경쟁 경로로 학습 대조를 갱신**하는 것이다. 기존 historical pool에 새 특징을 하나씩 붙이는 실험만 반복하면 정보가 있는8대조에 다시 묶인다. 승인 Train 범위에서 현재 점수로 hard negative를 만들고 target compatibility·source/권리 관문·split/단계67 기준선을 보존하여 효과를 측정한다. 후보에 정답이 없는 문제와 선택 오류·미평가 pedal/functional6-4·지원 어휘 밖 형태를 구별하며, Dev에서 `.248879`를 높이거나 특정 악보의128/130을 규칙에 넣지 않는다. 이후 시간별 구성음 지지와 실제 선택된 앞뒤 화음의 준비/해결 설명, 독립 작품군 비교로 연결한다.
