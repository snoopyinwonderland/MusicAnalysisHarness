# 전후 관측 문맥과 조건부 종지 전제

개발 항목: **HARM-DEV-20261001-11**. 정본 진입점은 [화성 개발 문서](../README.md)다. 직전 단계는 [계산 공유와 작품군별 batch 검증](2026-10-01-functional-sharing-and-family-batch.md)이다.

## 목적과 이번 범위

원래의 짧은 화음 분석 구간 밖에서 음이 어떻게 이어지는지와, 각 화음 가정에서 관측된 최저·최고음이 어떤 구성음인지를 함께 보존한다. 이 자료는 후속 기능·종지·비화성음 추론의 근거다. 기존 화음 구간을 넓히거나 최종 화음·성부·종지를 자동 선택하는 단계는 아니다.

구현·실제 고정 자료 r1 계산·전체 회귀·독립 저장 검증을 완료했다. 각각의 분모와 검사 범위는 아래 검증 절에서 구별한다. 음악적 정확도 향상이나 운영 반영을 선언하는 단계는 아니다.

## 왜 기존 계산을 그대로 확장하지 않는가

기존 `frozen_context_observation`은 원래 frozen sample의 target/context를 동일하게 고정한다. 기존 factor graph, harmony path, key track, completion bundle도 그 명시 범위에 묶여 있다. 창 밖 음을 가져오면서 원래 record를 재봉인하면 가정과 실제 관측 범위가 서로 달라진다.

새 레이어를 분리한다.

```text
원 full IR + frozen observation/audit
  ├─ 기존 view/path/key/completion/comparison — 불변
  ├─ 새 fmctx: 앞뒤 물리 마디와 원음·타이·후속음 관측
  └─ 새 fmcad/fmcpbatch: 기존 가정 아래 최저·최고음/종결 전제
```

관측 범위를 넓힌 결과는 **새로운 성부 연결이나 새로운 화음 path가 아니다.** 같은 raw `part_id/voice_id`의 시간상 이웃을 논리적 선율 성부의 후속음으로 확정하지 않는다. 원주석·human correction·학습 자격·Core와는 계속 분리한다.

## 일반 규칙 A — 별도 전후 관측

구현: `src/musicanote_harness/factor_context_observation.py`, 별도 version과 `fmctx_` prefix.

- full IR의 실제 내용, 원 view/observation/audit refs와 정확한 유리수 시간에 연결한다. 원 target/context는 바꾸지 않는다.
- 기본 앞뒤 한 물리 마디를 별도 envelope로 관측한다. printed measure number의 덧셈으로 마디를 찾지 않는다. 실제 global start/duration의 clock group을 이용하고 중복·겹침·공백·불규칙/score-end 조건을 기록한다.
- 원음표·쉼표·철자·기보·staff/part/voice·타이·attack·source 참조를 보존한다. linked closure의 창 밖 음표와 envelope에 실제 겹치는 음을 구별한다.
- 원 view의 각 positive sounding event를 seed로 하여 같은 raw lane의 바로 앞 종료 그룹과 바로 뒤 시작 그룹을 모두 보존한다. 동시 후보 중 하나를 최단 도약이나 가장 가까운 음으로 골라내지 않는다. point/grace는 별도 관측으로 보존하며 이 시간 이웃 조회의 seed와 섞지 않는다.
- full release에서 정확히 시작하는 음과 시간 공백 뒤에 시작하는 음을 구별한다. 공백·쉼표를 건너뛴 연결을 만들어 내지 않는다.
- envelope 밖의 후속음은 원 full IR에서 확인한 metadata-only 관측으로 표시한다. 새 envelope의 화음/해결 근거로 자동 소비하지 않는다.
- 지속/타이 continuation을 새 attack으로 바꾸지 않는다. full 타이의 출처 음가·연속성·철자 검증과 현재 구간 clip의 보존을 구별한다.
- grace/point, microtonal, source clock/pitch 보류는 별도로 표시한다. 보류 음을 버려 다른 베이스나 멜로디를 만들지 않는다.
- event/relation 예산을 전체 관측 단위로 검사한다. 초과 시 일부 성공 관계만 남기지 않고 전체 보류와 계획 분모를 보존한다. 이 예산은 선택적 관계 계산의 materialization을 보류하는 기준이며 byte/RSS 상한이 아니다. 보류 상태에도 정확한 원 snapshot과 전체 참조 inventory는 보존한다.

기존 `musical_pattern_observation`의 public schema는 SOURCE/alignment refs를 요구한다. frozen unlabeled observation을 그 계약으로 위장하지 않는다. 새 계약은 자체 typed original refs와 공통 literal projection kernel을 이용한다. 가짜 SOURCE나 alignment 승인은 만들지 않는다.

## 일반 규칙 B — 모든 화음 가정의 종지 전제

구현: `src/musicanote_harness/factor_cadence_prerequisites.py`, `fmcad_` 및 공유 계산의 `fmcpbatch_` prefix.

- 주어진 완전한 harmony path와 key track, function inventory, **하나의 동일 completion bundle**에 연결한다.
- 각 path의 시작·내부·끝 경계를 모두 검사한다. 유력한 종지에만 근거를 남기지 않는다.
- 경계 직전/도착 시점의 모든 관측 최저·최고음을 보존한다. 동률·enharmonic spelling·복수 part를 유지하며 구조적 bass/main melody로 선택하지 않는다.
- 해당 화음 가정 아래 근음/3음/5음/7음과 명시 조성 가정 아래 degree/alter를 계산한다. 완전한 ordinary triad/seventh일 때만 조건부 전위 형태를 제시한다. blocked/unknown/microtonal은 자격 조건과 함께 남긴다.
- 전후 extreme의 같은 raw lane 관계를 동일 bundle의 실제 required link 또는 same-sound carry와 대조한다. 다른 성부/다른 completion의 유리한 연결을 합치지 않는다.
- 화성 도착 `t`와 full 음의 종결 release `u`를 분리한다. 도착 이후 지속음이나 장식음이 있다는 사실만으로 종지의 긍정/부정을 확정하지 않는다.
- 음가의 quarter 길이와 IR-notated beat-unit 비율, 뒤 쉼표/attack, full release와 관측 horizon을 기록한다. 현재 IR의 meter에는 parser fallback 가능성이 있으므로 XML 박자 독립 인증/지각 accent를 주장하지 않는다.
- PAC/HC/IAC 판단에서 local key 확정, structural bass/melody, perceived accent, consonance, phrase terminal, performed timing은 미확립 전제로 유지한다. `confirmed=false`는 종지가 없다는 정답이 아니라 아직 확정하지 않았다는 뜻이다.
- bulk API는 하나의 명시 bundle 아래 모든 선언 path×key overlay를 검사한다. shared parents를 검증하고 복사·재계산을 공유하지만 caller가 신뢰된 skip을 선언할 수는 없다. record/pair 예산 초과는 전체 범위 보류이며 best 후보 축소가 아니다.

## 실제 full-IR 사전 확인

이 표는 새 레이어 설계 전에 source-clock 감사와 full IR로 확인한 실제 움직임이다. 화음·조성·종지 확정 주장이 아니다.

| 사례 | 관측 사실 | 해석의 한계 |
|---|---|---|
| Beethoven Sonata 01-1 | A♭3 `[53,57)` 다음 동일 raw lane에 D♭4 `[57,59)` | 원 target `[55,57)` 밖에 후속음은 있으나 일반 7음의 하행 2도 해결은 아님 |
| 같은 문맥 | A♭4 `[53,57)` 다음 F4 `[57,61)` | 3도 하행. 창 확대를 이유로 기대한 해결 형태로 승격하지 않음 |
| Mozart K280-1 | F5 `[43/2,45/2)` → E5 `[45/2,47/2)` | 이미 원 view 안에 있으며 harmonic cut `89/4`와 실제 release/onset `45/2`가 다름. 새 독립 양성으로 중복 집계하지 않음 |
| Chopin BI105-2op30-2 | 이전 A4 `[14,15)`는 source 시작 15에 종료, 뒤 A3은 `[17,18)` | 원 source `[15,33/2)`의 critical source로 소급 차용할 수 없음. D♯의 전역 부재도 주장하지 않음 |

원 batch의 55 function/30 resolution rows는 두 실제 움직임 등을 여러 path/key 가정에서 재사용한 조건부 행이다. 55/30개의 독립 정답이나 작품 수로 재해석하지 않는다.

## 실행기·저장·보존

`factor_context_prerequisite_trial.py`는 완료된 family batch의 registered report/plan/artifact SHA와 정확한 파일 목록을 보호한 뒤 새 직계 output 폴더에만 저장한다.

- 전체 cohort의 선언된 contexts/raw lanes와 이전 family 선택/미실행 분모를 유지한다.
- 이전 선택 문맥 모두와 모든 old groups/status/lanes/source gate를 보존한다. 예산 보류 group도 삭제하지 않는다.
- 실제 원 full IR/observation/audit를 fresh replay하고 새 sidecar를 생성한다.
- 저장된 comparison마다 모든 overlay를 같은 명시 bundle 아래 연결한다. 원 comparison이나 selector/geometry/old engine을 재실행하지 않는다.
- 창 확대 자료와 기존 path를 혼합하지 않는다. 새 context record는 기존 결과를 수정하지 않는다.
- 생성 시점 artifact SHA, 원 input/code SHA·파일 목록, 모든 성공/보류/오류 및 재현 설정을 남긴다.
- `scope_calculation_complete`와 `cohort_complete=false`, 계산 오류와 음악적 미평가를 구별한다. 개별 실패가 있어도 이미 선언한 old groups/lanes는 남긴다.

## 검증·실패·보완

검사 대상은 triplet 유리수, changing/compound meter와 parser fallback 한계, 타이 continuation, target-end half-open 규칙, source-start에 종료한 이전 음, 동시·다성부/겹침/공백, grace/microtonal/source clock 보류, 전체 예산, unknown/blocked 후보, 동일 bundle 불충족과 전역 부재 구별, 변조·재봉인·alias, 전체 old 분모/창/부모 자료 불변이다.

- **신규 focused:** context 28개/2.838초, cadence 39개/9.686초, 실행기 16개/75.836초 통과. 총 신규 83개다.
- **동결 후 전체 회귀:** `unittest discover -s tests -q`로 전체 Python **3,023개/433.215초 OK**. source를 동결한 뒤 실제 r1 계산과 병행했다. 이 수는 코드 검사 수이며 음악·종지 정답 수가 아니다.
- **독립 focused 재검사:** 별도 읽기 전용 검토자의 신규 83개/86.267초 모두 통과. 원 comparison을 실행하지 않는 대표 fresh replay와 별도로 구별한다.
- **초기 실패와 정정:** 첫 실행기 검사에서 3개 assertion이 실패했다. 이전 `Counter` 저장은 한 번도 등장하지 않은 0값 joint count key를 생략하지만 새 합계는 0 key를 명시했기 때문이다. 계산 수의 동등성만 `Counter` 비교로 정규화했고, status/후보/참조/양성 분모의 누락을 허용하지 않았다. fixture의 imported TestCase 중복 수집도 제거했다. 정정 후 실행기 16개가 모두 통과했다.
- **독립 정적 보완:** 등록 출력 SHA뿐 아니라 정확한 생성 파일 목록과 누락 파일을 검사한다. 기존 비교의 실제 canonical seal/policy와 전체 group/function/resolution/comparison/vector/pair/joint 분모, ready graph와 원 lane snapshot의 일치도 확인한다. rehashed 후보·comparison 삭제, 생성물 변조/추가, context 계산 오류와 cadence 계산 오류 반례를 포함한다.

### 실제 r1 계산

출력: `output/factor-context-prerequisites-2026-10-01-r1`. exit 0 / 200.447912초 / 계산 오류 0. 이전 family 선택을 그대로 사용한 **5문맥/15raw lanes/16groups**다. 전곡 5작품 분석이나 독립 정확도 holdout이 아니다.

| 문맥 | 원 frozen 범위 | 별도 전후 envelope | 새 notated snapshots | 새 sound snapshots | 시간 관계 |
|---|---|---|---:|---:|---:|
| Beethoven quartet | `[265,533/2)` | `[262,270)` | 57 | 53 | 18 |
| Beethoven sonata 01-1 | `[329/6,57)` | `[49,61)` | 26 | 23 | 14 |
| Chopin mazurka | `[15,17)` | `[10,22)` | 43 | 42 | 21 |
| Corelli | `[38,159/4)` | `[32,44)` | 84 | 81 | 26 |
| Mozart K280-1 | `[22,91/4)` | `[18,27)` | 48 | 40 | 10 |

모든 범위는 quarter 단위 유리수다. 기본 pre/post 각 1은 원 context와 겹치는 실제 clock groups의 앞뒤를 뜻한다. 마디 길이나 context가 걸친 마디 수가 같다는 가정은 하지 않는다.

- 원 positive sound 40개를 seed로 하여 notated snapshots 258개(음표 243/쉼표 15), sound 239개, source refs 258/attack 239/tie 4/chord onset groups 16을 저장했다. 여러 성부/화음/linked context를 포함한 관측 건수이며 258개의 정답이나 모티프 수가 아니다.
- 시간 관계 89개를 모두 저장했다. 후속 endpoint group 40개는 이 자료에서는 정확히 맞닿았지만 **logical voice edge/resolution은 전부 미확정**이다. envelope 밖 metadata-only/불명확 lane은 이 다섯 문맥에서 0이며 synthetic 반례에서는 검사했다.
- 기존 9 comparison bundle 아래 **2,195개 path×key×bundle 레코드**와 6,310 boundary observations를 저장했다. 모두 `prerequisite_observations_complete_not_cadence_assessed`다. 같은 구성음 분할 control과 반복 가정의 경계도 포함하므로 6,310개의 독립 경계/종지 사례가 아니다.
- 같은 raw lane의 extreme pair 3,840개: same-sound carry 1,655 / 해당 bundle의 required link 충족 275 / 해당 bundle에서 불충족 1,910. 마지막 수는 전역 부재나 음악적 기각 수가 아니다.
- extreme instances 16,460개 안에서 조건부 전위 형태 5,785 / 해당 전제 미평가 2,445 / 최저음이 아닌 관측 8,230. 명시 key의 조건부 음도 좌표 13,168 / 미평가 3,292. 모두 가정·시간·source guard와 연결한 반복 instance 수이며 실제 정답 음표 수가 아니다.
- terminal probe의 release-at-context-end 6,245 / release-beyond-context 1,330 instances를 구별한다. 새 cadence 전제 레코드는 원 가정 범위를 유지하므로, 새 전후 관측을 자동으로 붙여 종결 전제를 확정하지 않는다.
- Corelli의 원 한도 보류 4groups에는 새 harmonic/key 가정을 만들어 넣지 않았다. 전후 관측 자료는 저장하되 cadence 비교는 없다.
- 기존 group 상태: 비교 완료 7 / comparison pair 한도 4 / 원 path 한도 3 / interpretation pair 한도 2로 불변이다. 기존 29,650 function rows, 55,180 resolution rows, 9 comparisons, 2,195 vectors, 289,740 pair differences, joint request/solution/branch 각 30도 그대로다.
- 전체 선언 322contexts/1,013raw lanes에서 미실행 317/998과 나머지 14family 대기를 유지한다. `scope_calculation_complete=true`, `cohort_complete=false`다. key/화음/NCT/종지의 최종 선택, human/gold/training/generation 승인은 없다.
- wall-clock 200.447912초는 이번 추가 근거 계산이다. 이전 666.117564초의 다른 작업과 나누어 속도 향상률로 제시하지 않는다. 전체 회귀 검사와 병행한 실행이다.

### 저장 감사 및 참조

독립 읽기 전용 검토에서 보호 input 4,408개, current code/schema 297개와 정확 code 목록, 등록 artifact 16개의 생성 시점 SHA/파일 목록 불변을 확인했다. report를 포함한 출력 파일은 17개이고 report의 현재 SHA는 아래에 별도로 기록한다. 등록 artifact 합계 9,764,425bytes다.

다섯 context는 full IR/view/frozen observation/audit로 `validate_context` fresh replay를 모두 통과했다. 아홉 cadence batch와 2,195개 nested record의 seal·원 path/key/bundle·source snapshots·상호 refs·모든 이전 group/lane/status를 대조했다.

대표 Beethoven quartet의 22path×5keys=110개 레코드를 `validate_all_prerequisites`로 독립 fresh replay하고 그 안의 단일 레코드도 `validate_prerequisites`로 재계산했다. `max_pairs=0`의 전체 transition 보류에서도 모든 경계가 남는다. 이전 `compare_functional`을 호출하면 실패하도록 막은 상태에서도 통과했으므로 과거 큰 비교를 재실행해 결과를 덮어쓴 것은 아니다. 독립 재검토에서 남은 차단 문제는 발견되지 않았다.

두 번째 독립 읽기 전용 감사에서도 전체 5문맥의 envelope·source closure·full-IR raw-lane endpoint·motion·반개구간 배치와 공개 fresh validation이 일치했다. 위 A♭3→D♭4/A♭4→F4, F5→E5와 이전/이후 A 사례를 별도로 확인했다. 창 밖 도착음은 새 context에만 보존하며 기존 source의 구성음/성부 연결/해결로 차용하지 않았다. 실제 시간 관계 89개는 화성·성부·종지 확정 89건이 아니다.

이번 코드·검사·문서 10개 파일의 strict UTF-8·NUL/U+FFFD·줄 끝 공백과 네 개발 문서의 상대 링크 114개를 검사해 오류 0이었다. read-only `git diff --check` 오류도 0이며, 현재 untracked 파일의 공백/문자 검증은 별도 파일 검사로 수행했다. commit/push나 기존 출력 삭제는 하지 않았다.

report SHA-256:

```text
9578c1180a99941f7d78547a0a51b89a4dad91ab953d1f254cf6569bc8fd95af
```

정확한 context/packet/working-IR/comparison/bundle refs는 `context-index.json`에, 모든 생성 artifact SHA는 `report.json`에, 전체 부모 inputs·코드/설정·선택/미실행 분모는 `run-plan.json`에 저장한다. 이전 출력·원 XML/IR/revision/주석 및 기존 seal은 수정하지 않는다.

### 재현

```powershell
$env:PYTHONPATH='K:/Music Analysis/src;K:/Music Analysis/tests'
$env:PYTHONIOENCODING='utf-8'
./.venv/Scripts/python.exe -m unittest discover -s tests -q
./.venv/Scripts/python.exe -m musicanote_harness.factor_context_prerequisite_trial `
  --family-batch output/factor-functional-family-batch-2026-10-01-r1 `
  --pre-measures 1 --post-measures 1 `
  --max-events 4096 --max-relations 65536 --max-records 4096 --max-pairs 65536 `
  --output output/factor-context-prerequisites-2026-10-01-r2
```

위 `r2`는 다시 실행할 때의 **새 폴더 예**이며 이번 실제 산출물은 `r1`이다. 이미 존재하는 output을 덮어쓰지 않는다. 보류를 해제하려고 기존 schema/source gate를 완화하거나 후보를 축소하지 않는다.

## 운영 및 다음 큰 단계

운영 뷰어·구조 분석·생성기는 이번 변경 대상이 아니다. 새 관측을 이유로 기존 G1/source/training/gold 사용 정책을 승격하지 않는다.

다음에는 이 문맥 근거를 이용하는 **새로 명시한 범위의 harmony/key/성부 공동 가정**을 만들고, 유지/변화·7음/이끎음·비화성음의 경쟁 설명을 대조한다. 원 bundle에 창 밖 음을 즉석 추가하지 않는다. 종지의 구조 베이스·상성부·박절·협화/구조 종결 전제가 부족하면 그 판단만 보류하고, 최종 후보 비교 및 악보 표시 통합의 큰 계획을 계속한다.
