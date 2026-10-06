# J2b — Train 전용 구조화 가중치 학습과 고정 점수 비교

기록 ID: **HARM-DEV-20261004-50** · 2026-10-04. [J0–J5 실행 계약](2026-10-04-joint-decoding-and-benchmark-review.md)의 J2 후속이다. [J2a 고정 점수](2026-10-04-scored-joint-decoder.md)의 원 코드·표본·후보·과거 예측을 보존하며, 별도의 연구 가중치를 학습한다. **전체 Roman/전위/조성/NCT 기능 완료나 운영 적용 기록이 아니다.**

## 1. DCML 자료와 이번 사용 범위

DCML은 Digital and Cognitive Musicology Lab의 공개 악보·음악 분석 코퍼스다. [공식 코퍼스 메타 저장소](https://github.com/DCMLab/dcml_corpora)는 연구실이 공개·관리하는 자료들을 연결한다. 지금322문맥을 만든33개 package는 Beethoven quartets/sonatas, Chopin mazurkas, Corelli, Mozart sonatas의 다섯 출처에 속한다. 전문가 Roman 주석과 원 악보의 연결을 이용하지만, 현재 평가 계약에서는 주석을 **절대 근음+철자를 보존한 구성음 집합**으로 변환한다. 기능화성 전체를 학습하거나 모든 음표의 NCT gold를 확보했다는 뜻이 아니다.

확인한 다섯 로컬 `LICENSE` 첫 줄과 README의 licence 링크는 모두 **CC BY-NC-SA 4.0**다. 원 음악이 오래됐다는 것과 새 편집·주석·데이터베이스의 이용 조건은 별개다. [CC 이용 조건](https://creativecommons.org/licenses/by-nc-sa/4.0/)과 [NC 설명](https://creativecommons.org/faq/#does-my-use-violate-the-noncommercial-clause-of-the-licenses)을 확인했다. 내부 사용·비공개라는 사실만으로 비상업 조건 충족이 확정되지는 않는다. 이 기록은 법률 자문이나 상업 학습 허가 확인서가 아니다.

사용자가 “일단 성능 향상을 위한 내부 테스트”를 진행하도록 요청했다. 이를 **로컬 연구·검증 실험으로 제한해 해석**하고, 조건을 무시하거나 면제받았다고 기록하지 않는다. 상업 운영 적용, 외부 API 전송, 학습 가중치 배포는 허용하지 않는 연구용 범위를 별도로 기록했다. 향후 상업 개발의 목적·실제 이용에 해당 조건을 적용할 수 있는지는 권리자 확인 또는 별도 이용 허가/다른 자료가 필요할 수 있으며 미확정이다.

- [실험 전용 사용 계약](../experiments/2026-10-04-local-research-training-use.json)은 원 recall의 물리 SHA, 원 manifest entry의 canonical JSON SHA, 로컬 LICENSE/README의 물리 SHA·저장소/attribution 위치·사용자 요청 원문·제한 범위를 연결한다.
- Train27개 entry만 승인 범위에 넣는다. Dev6개 entry의 주석은 가중치 학습에 들어가지 않는다.
- 기존33개 manifest의 `automatic_training=false`, `model_training_approved=false`, licence 상태와 v0.1 schema를 변경하지 않는다. 새 계약은 이번 한정 연구 실행의 별도 사용 근거이며 기존 운영 학습 권한을 소급 발급하지 않는다.
- 계약이 pending이거나 출처 근거가 빠지거나 물리 hash가 달라지면 학습 전 거부한다. 공개 corpus라고 자동 승인하지 않는다. 체크포인트와 원자료를 Git/외부에 배포하지 않는다.
- 원 attribution/라이선스 자료는 다음 저장소의 로컬 README/해시로 보존한다: [ABC](https://github.com/DCMLab/ABC), [Beethoven sonatas](https://github.com/DCMLab/beethoven_piano_sonatas), [Chopin mazurkas](https://github.com/DCMLab/chopin_mazurkas), [Corelli](https://github.com/DCMLab/corelli), [Mozart sonatas](https://github.com/DCMLab/mozart_piano_sonatas).

## 2. 학습 원리와 누출 방지

첫 학습은 **평균 구조화 퍼셉트론(averaged structured perceptron)**이다. 새로운 거대 신경망이나 LLM API 호출이 아니다. 기존11가지 segment/transition 관측 특징의 가중치를 배워, 동일 exact DAG가 구간과 화음을 함께 고르게 한다.

```text
예측 = 현재 비용으로 원 후보망에서 가장 싼 완전 진행
학습 target = train 주석과 양립하는 원 후보만 남긴 후보망의 가장 싼 완전 진행
가중치 변화 = 학습률 × (예측 특징 합 − target 특징 합)
```

비용을 최소화하므로 이 방향은 잘못 고른 진행의 비용을 target보다 상대적으로 높인다. 정답 주석의 onset마다 반드시 새 구간을 만드는 방식이 아니다. 같은 의미의 주석 구간을 하나의 edge로 표현할 수도 있고, compatible partition 중 현재 비용이 가장 낮은 경로를 잠재 target으로 쓴다. **주석 화음을 후보에 새로 삽입하지 않는다.**

- 학습 표본은 train only. 완전 reference와6segment 이내 compatible path가 있을 때만 업데이트할 수 있다. 부분/미지원·후보 부재·연결/cap 실패·원 보류는 학습 제외 사유로 남긴다.
- 제외 표본을 평가에서 삭제하지 않는다. 동일322개 전체를 예측·평가하고 기존256개 완전 문맥과 부분/미지원66의 분모를 유지한다.
- Dev를 업데이트, epoch 선택 또는 가중치 조정에 쓰지 않는다. 초기값은 J2a 그대로, 학습률1/10·5epoch·절댓값 한도4를 이번 실행 전에 고정했다. 작품 가족→sample ID 순서이며 random shuffle0이다.
- 매 업데이트에서 가중치를1/1,000,000 단위 유리수로 반올림(동률 짝수)한다. 분모 폭증을 막는 **가중치 수치 규칙**이다. IR 시간·특징·점수는 원 유리수이며 시간 grid를 양자화하지 않는다. 평균 weight도 같은 정밀도로 저장한다.
- Signed weight도 허용한다. DAG/6segment 아래 현재1차 비용의 정확한 최적해이며 전체 음악 해석의 정확성은 아니다. 자원 초과 시 불완전 winner로 업데이트하지 않는다.
- 일관된 성부/NCT,7음 해결, 조성/applied 해결, 박절, structural bass는 여전히 unavailable이다. Missing을 false로 바꾸거나 낙관 NCT 상계를 설명 음가로 빼지 않는다.
- 예측 API는 `problem, model`을 받으며 reference 인자가 없다. Train target의 source group refs와 특징 delta는 학습 로그에 따로 남긴다. Confidence는 null이고 사람이 검수한 정답으로 승격하지 않는다.

학습할 수 있는 것은 **주어진 후보·특징 아래의 상대 비용**이다. 정답 후보 밖 오류, window 바깥 생략 화음의 지속, NCT/전위/조성 기능 등 지원하지 않은 의미를11개 weight만으로 해결했다고 주장하지 않는다.

## 3. 실행 결과

실제322문맥 전체를 **388.660446초 / exit0**에 처리했다. Train270문맥 중 완전 reference가 원 후보망의6segment 경로로 표현되는 **110문맥**에서5epoch를 학습했다. 제외160은 compatible complete path 없음83, partial/미지원49, lattice unavailable28이다. 원 보류가 partial보다 먼저 분류되므로49를 train의 전체 partial 수65와 혼동하지 않는다. Train 완전 평가205중110reachable/95unreachable·보류이며 나머지65는 partial/미지원이다.

Epoch별 업데이트는72/69/65/68/66, 합계340이다. 각epoch110개·평균550tick이며 새 작품340곡이라는 뜻이 아니다. 학습에 Dev0, 후보 주입0, 예산 때문에 업데이트를 보류한 eligible 표본0이다. Dev52문맥/완전51은 이번 fit에 사용하지 않았지만 과거 개발 과정에서 노출된 자료이므로 독립 blind test가 아니다.

| 지표 | J2a 고정 joint 점수 | 이번 학습 joint 점수 |
|---|---:|---:|
| 전체 문맥 일치 / 완전256 | 50 (19.53%) | 46 (17.97%) |
| 전체 root 시간 일치 | 40.47% | 38.01% |
| 전체 root+spelled members 시간 일치 | 30.15% | 28.84% |
| 전체 작품 가족 macro root+members | 38.35% | 37.26% |
| 정확한 의미 경계 F1 | 57.26% | 41.12% |
| Train 문맥 일치 / 완전205 | 44 | 40 |
| Dev 문맥 일치 / 완전51 | 6 | 6 |
| Dev root+members 시간 일치 | 30.45% | 29.76% |
| Dev 작품 가족 macro root+members | 31.71% | 36.41% |

동일 적격 시간7895/8quarter,291선택/31보류(원 baseline_not_ready28·edge budget3), 부분/미지원66을 유지했다. 경계 TP209→125, FP78→40, FN234→318; precision72.82%→75.76%, recall47.18%→28.22%다. **과분할은 감소했지만 필요한 경계도 놓친 과병합이 커졌다.** 전체 완전 일치 기준 개선6·퇴행10·유지 정답40·계속 오답200이다. Dev macro 상승은 일부 가족 개선 신호지만 시간 일치·경계와 반대 방향이며 전체 향상으로 보고하지 않는다.

학습 가능한110train에서도 전체 일치44→40이다. 따라서 이번 결과를 단순히 “train 개선/dev 퇴행이라는 과적합”으로 설명할 근거는 없다. 첫5epoch의 학습 방식과 현재 특징 표현이 모두 진단 대상이다. Epoch 업데이트가 계속65~72개 발생했고 완전 학습 수렴을 입증하지 않았다. 반복 수를 늘리면 좋아진다는 보장도 없다. 원 후보 ceiling132/256은 변하지 않았다.

### 가중치 변화와 진단

관측되지 않은 구성음 비용은0.3→0.03324, 추가 구성음 비용0.1→0.202287, segment 비용0.015→0.031727, unanchored change0.04→0.105818, member turnover0.02→0.092208로 바뀌었다. 나머지를 포함한 정확한 유리수는 model에 저장했다. 일관된 NCT·실제 기능 해결·박절/베이스 등의 연결이 없는 상태에서11특징만으로 target을 분리하려 하면, 다른 구간의 장식을 합쳐야 하는 증거가 실제 화음 교체를 억제하는 비용과 구별되지 않을 수 있다. 이는 다음 가설이며 모든 오류 원인의 확정 진단은 아니다.

실제 최소 비용 차이를 재계산하여 [개선/퇴행4사례](../../../output/harmony-structured-learning-2026-10-04-r1/selection-changes.json)를 별도 저장했다. 각 사례는 원 context/search의 물리 SHA·group ID·유리수 범위·근음/구성음·양쪽 예측·평가·학습 비용 차이와 특징별 기여를 포함한다. 원 note/tie/음가·XML은 원 context 및 frozen package로 역추적하며 원문을 수정하지 않는다.

- **합치기가 맞은 Dev 사례:** Corelli `op01n01d`, `cont_4aff761aeb3f30365061`, `[184,186)`. 고정 점수의 A minor→G minor→F major를 F `{A,C,F}` 한 구간으로 바꿔2quarter 전체 일치했다. Dev target을 학습에 넣어서 만든 선택이 아니다.
- **화음 종류 선택 개선:** Chopin `BI115-1op33-1`, `cont_43bca891e39173d156c4`, `[93,96)`. F# triad 이후 G#7 후보를 B triad로 바꿔 구성음 일치1→3quarter가 됐다. 추가 구성음 비용 등이 상대 선택을 바꿨지만 applied/function 정답을 학습했다고 하지 않는다.
- **필요한 마지막 화음 교체의 퇴행:** Beethoven sonata03-2, `cont_5f130fc395c3561ba6c4`, `[103,209/2)`. 고정 점수의 B7→C triad→G triad에서 마지막 `[835/8,209/2)` G 구간이 C에 병합되어 전체 일치를 잃었다. C로 합친 경로의 비구성음 비용은 더 크지만 segment·근음 이동·구성음 교체 비용의 절약이 그것을 넘었다. 학습된 비용에서 합친 진행이133839/2000000만큼 싸다는 것을 직접 확인했다. 특정 작품 예외를 만들지 않았다.
- **과병합 큰 퇴행:** Chopin `BI126-3op41-1`, `cont_351b01f7c138841b1279`, `[242,247)`. 고정4segment가 A# triad 한 구간으로 바뀌어 구성음 일치4→0quarter가 됐다. 비구성음 노출은 불리해졌지만7화음/분할/전이 비용 절약이 이겼다. 실제 선택 근거와 원주석을 모두 보존하며 이번 결과를 정답으로 승격하지 않는다.

**결정: 연구 가중치 채택 보류.** 기존 고정 score와 segment-only ablation을 유지한다. 이번 model은 실패를 재현하는 로컬 실험 checkpoint이며 운영 UI나 기존 분석 결과를 대체하지 않는다. 학습 완료와 성능 개선 완료를 구분한다.

## 4. 구현과 검사

- [학습/추론 코드](../../../src/musicanote_harness/harmony_structured_learning.py): `harmony-structured-learning-0.1.0`.
- [물리 입력을 검증하는 실험 실행기](../../../src/musicanote_harness/harmony_structured_learning_trial.py): `harmony-structured-learning-trial-0.1.0`. 이전 고정 선택을 무주석으로 재계산해 그대로인지 확인하고, 학습 후 같은322분모를 비교한다. 입력/코드·이전 결과는 종료까지 hash 보호한다.
- [검사](../../../tests/test_harmony_structured_learning.py): 비용 업데이트 부호, 평균 weight, 누락 후보 비발명, partial/시간 partition, train/dev/가족 분리, 권한 pending/외부 사용/출처 변경 거부, 재현성과 물리 실행기를 검사한다. Physical fixture는 genuine gzip이나 **상위 receipts와 license evidence는 합성 테스트 데이터**다. 실코퍼스 성능과 unit test 통과는 별개다.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m unittest test_harmony_structured_learning test_harmony_scored_decoder test_harmony_lattice_recall test_harmony_candidate_recall test_harmony_progression_search
```

최종 신규21+기존85=**106 PASS / 1.156초**, Python3개 AST 통과다. 이전105개 실행과 신규21단독 실행을 고유 검사에 중복 합산하지 않는다. 첫 사후 진단 출력이 너무 커서 도구 출력이 잘리고 JSON decode가 실패했으나 파일은 생성되지 않았다. 원 parent의 상세 note refs를 중복 복사하지 않고 group/parent refs와 특징별 비용을 남기는 축약 진단으로 다시 생성했다. 모델/예측은 바꾸지 않았다.

- [실제 report](../../../output/harmony-structured-learning-2026-10-04-r1/report.json):3,764,611B, 물리 SHA `0cf236c2a949f2158ca1cbb87ce87cc673e526e093ae7a381d5d5367afffc03a`.
- [연구 model](../../../output/harmony-structured-learning-2026-10-04-r1/model.json):581,660B, 물리 SHA `69237e290b021a932c5674738206cf3f108aed44b04e1069404a1b63f67d5ad7`. model ID/canonical content hash와 들여쓴 물리 파일 SHA를 구별한다.
- 사용 계약 물리 SHA `46bbd4871cc38e27d14fd19d317956f989a1ead6fa265ecb74d722272db4ee48`.
- 학습 코드 SHA `96d2a7b205be252f13a15183f7c5c10302e5dbd835b9a7ea5f3606b6118ba8ad`; 실행기 SHA `ad286ef438e3df98d973e856e08480b2568976cc1223c23556d7c8f6c699ff11`.
- 732고유 입력/코드 SHA를 종료까지 보호했다. 원 XML/Core/주석·원 후보·기존 점수/선택·기존 학습 자격·운영 UI/서버·Git 변경0이다. 연구 model/진단·코드·별도 사용 계약·화성 개발 문서만 추가했다. 외부 API/commit/push·상업 운영 적용·원자료/weight 배포0이다.

실제 재현은 실행기의 `--recall`, `--lattice`, `--baseline`, `--contract`와 각각의 `--expected-*-sha`, 새 `--output`을 지정한다. 원 report47/48/49와 이번 계약을 정확히 pin하며 기존 output은 overwrite하지 않는다. 실험 목적·사용자의 확인 범위가 달라지면 계약을 재사용해 운영 학습을 하지 않는다.

## 5. 다음 결정

최종 사후 검증: 원732고유입력/코드SHA 재대조 변경0, 변경4문서 strict UTF-8/replacement0·로컬 링크275/누락0, 메인/로그/계획 등록 각1개·기록50 중복0, `git diff --check` exit0이다. 문서 갱신의 부분 적용으로 생긴 임시 중복/실행 중 문구는 확인하여 정리했다. 기존5개 tracked 파일의 LF→CRLF 경고는 유지한다. 출력은3파일4,374,867B이며 사후진단28,596B의 물리 SHA는 `27ff594857389bc43bc7f61e07ddde7dc6e76ed8eb43acfc36eaa9d9351efcc5`다.

다음은 대규모 자료 정리를 다시 시작하지 않고 **이번 과병합을 일으킨 학습 목적·특징의 보완**이다. 첫 손실은 완전 경로의 특징 차이뿐이라 부분 시간 일치와 특정 경계 누락의 중요도를 직접 최적화하지 않았다. Train-only loss-augmented/margin 학습에서 정확한 시간 오류·경계 누락을 분해 가능한 비용으로 반영하는 방법과, 실제 교체 attack/구성음 지속·동일 성부 NCT/해결 근거를 연결하는 방법을 분리 검증한다. Dev를 보며 epoch를 소급 고르거나 특정 사례의 weight를 바꾸지 않는다. 학습한 비용의 개선이 입증될 때만 다음 모델 후보로 채택한다.

동시에 후보 밖85·연결22·6segment2·원 보류15의 ceiling을 유지한다. 학습 목적을 고쳐도 이 문제들이 자동 해결되지는 않는다. Full Roman/전위/조성 출력, 신규 독립 작품과 공개 모델의 공통 평가 및 후속 구조/작곡편곡 소비는 여전히 남은 큰 단계다.
