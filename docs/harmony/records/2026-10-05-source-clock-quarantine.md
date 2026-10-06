# HARM-DEV-20261005-61 — 원음표↔지속음 시간 검증과 오류 구간 격리

## 1. 결과와 적용 상태

프레이즈 비교층 병합 전의 화성 개발 순서로 돌아와, **잘못 연결된 지속음이 화음 노출량 계산에 들어가는 문제**부터 처리했다. 특정 작품의 화음 정답을 넣은 것이 아니라 원음표와 지속음의 시간 계약을 검사하는 일반 관문이다. Motif 개선은 Claude 작업 범위로 남기고 변경하지 않았다.

- 실제 15개 전체 악보 package의 지속음 **15,937개**를 검사했다. 15,936개는 이번 시간 계약 검사 통과, 1개는 불연속이다. 다중 원음표 지속음 512개 중 511개 통과/1개 실패다. 검증된 0시간 grace 89개는 원본에서 보존했다. 전곡의 모든 의미/성부/원본 XML 해석이 정확하다는 인증은 아니다.
- 같은 동결 72구간은 모두 새 시간 관문을 통과했다. 기존 **63선택/9보류**, 완전 문맥 **15/51**, 근음+구성음 시간 일치 **25.3442%**, coverage **43.7106%**, 경계 F1 **70.4225%**가 그대로다. 기존 6개 source-preflight 보류와 3개 장문/계산 보류를 해제하지 않았다.
- 실제 오류는 기존 72구간 밖에 있다. 별도 `[187,199)` 문맥에서 새 관문이 **후보 생성 전에 보류**하고 graph 없음/후보 edge 0/decoder 전이 0을 반환했다. 오류를 분석 분모에서 몰래 제외하거나 C4 지속음을 축소/분리/삭제하지 않았다.
- 정상 인접 `[196,197)`에서 기존 추론과 관문을 거친 추론을 각각 실행했다. 후보망 전체와 결과가 동일하고 edge 9개/선택 완료다. 이것은 adapter 동일성 확인이며 해당 화음의 음악적 정답 검증은 아니다.
- 신규 32개 검사(관문 23 + 실제 봉인 runner 9) 및 관련 회귀를 합친 **414 PASS**, 19.360초다. 사후 922개 고유 파일 SHA, 전체 source 시간 감사 15개, 72개 범위·관문·평가 재생을 통과했다.

**적용 범위:** 새 연구용 `SourceClockGuard.infer()` 진입점과 검증 runner에 적용했다. 기존 화면용 엔진, 기존 봉인 모듈, MusicSearch/Composition, 원 parser/Core/XML/주석, 권한/split/학습 가중치를 변경하지 않았다. 전체 운영 진입점에 강제 적용한 상태가 아니며 이번 수치를 정확도 향상이나 운영 승격으로 부르지 않는다.

## 2. 기존 위험과 새 일반 계약

기존 `source_evidence()`와 functional evidence는 붙임줄 source clock이 잘못되면 성부 진행/NCT 근거를 보류한다. 그러나 raw harmonic exposure는 저장된 `SoundingEvent.span`을 계속 사용했다. 따라서 잘못된 음의 지속을 화음 구성음·외부음·최저음 등의 점수에 반영할 수 있었다.

새 관문은 아래 순서를 강제한다.

```text
동결된 전체 관찰 IR
  → 원 note IDs / concert spelling / attack / 유리수 clock 검사
  → 요청 범위와 오류 위험 범위의 겹침 검사
      ├─ 겹침 또는 위치 미확정: source_clock_abstention (후보·선택 없음)
      └─ 허용: 원 IR을 그대로 기존 후보/점수/공동 선택기에 전달
```

### 검사와 보류 규칙

1. Note/Sound ID가 없거나 중복이면 전역 보류한다. 비어 있거나 없는 source note, 읽을 수 없는 유리수 시간은 오류 위치를 발명하지 않고 모든 요청을 보류한다.
2. 각 source note의 onset+duration을 정확한 분수로 계산한다. onset순으로 이어지는 release, 동일한 spelled concert pitch와 octave, 첫 attack ID, sound release 및 선언 duration을 확인한다. Triplet 등에서 float tolerance로 틈을 숨기지 않는다.
3. 같은 source note를 여러 sound가 소유하거나, 음수/역방향 clock, 0음가 비-grace, 음높이 변화, part를 넘는 chain은 보류한다.
4. 알려진 오류의 위험 범위는 **저장된 sound 범위와 모든 source note 범위를 함께 감싼 envelope**다. 저장 span이 짧아 source tail을 누락했더라도 tail까지 보호한다. `[start,end)`를 사용하고 0시간 오류는 그 onset을 포함하는 요청에서 보류한다.
5. Cross-staff/cross-voice는 물리적으로 연속인 tie를 자동 오류로 만들지 않는다. 여러 normalized voice ID는 경고로 남긴다. 성부 정체성/진행 근거의 기존 stricter 관문은 별도로 유지한다.
6. 0시간 grace는 모든 원음표가 같은 onset의 grace/0duration이고 tie가 없는 경우에만 허용한다. 수행 시간을 만들어 내지 않고 기존 grace 소비 계약으로 넘긴다.
7. 검증된 전체 IR와 audit의 SHA lease를 공개 연산 전후 검사한다. 외부 수정이 감지되면 결과를 거부한다. 반환 audit와 요청은 방어적으로 복사한다.

검사의 근거는 **Canonical note↔sound 계약**이다. XML을 독립적으로 다시 파싱한 검증이나 원 `tie_chain` 테이블 전체 validator가 아니다. 동일하게 잘못 생성된 note/sound를 이 검사만으로 발견할 수는 없다. 기존 source locator/measure/repeat/alignment 관문을 대체하지 않는다. Unknown을 근음 위치나 정상 tie로 채우지 않는다.

## 3. 실제 사례 — 전체 악보와 원 IDs 보존

작품: `dcml:chopin-mazurkas:BI145-1op50-1`. 아래 식별자는 저장·재현용이며 알고리즘의 분기 조건이 아니다.

| 대상 | 원 시간 (quarter) | 원 XML 위치 |
|---|---|---|
| `note_87998727920b`, C4 | `[190,192)` | P1, printed measure 64, voice 1, staff 1, element 4 |
| `note_cd69e76a0567`, C4 | `[195,196)` | P1, printed measure 66, voice 2, staff 1, element 6 |
| `sound_8da98c2c5b56` | 저장 `[190,196)` | 위 두 note를 참조 |
| source note가 없는 틈 | **`[192,195)` = 3 quarter** | 원 지속음 노출에 잘못 포함됨 |

IR normalized voice가 같아도 실제 onset이 연속하지 않는다. Raw XML voice 숫자의 차이만으로 보류한 것이 아니다. 새 관문은 전체 오류 envelope `[190,196)`와 겹친 분석을 보류한다. 이것은 원본/정규화 오류 격리이며 음을 임의로 `190–192`/`195–196`으로 고쳐 새 화음 정답을 만들지 않았다.

저장한 [사례 JSON](../../../output/harmony-source-clock-2026-10-05-r1/cases/f74fc05a187cda372d8e/case.json)에 전후 문맥 `[187,199)`, 원 note/ref IDs, 오류 사유, 기존 3quarter exposure, 새 보류 결과와 정상 인접 대조를 함께 넣었다. 부분 이미지 대신 [전체 source MusicXML](../../../output/harmony-source-clock-2026-10-05-r1/cases/f74fc05a187cda372d8e/source.musicxml)과 [전체 관찰 IR](../../../output/harmony-source-clock-2026-10-05-r1/cases/f74fc05a187cda372d8e/canonical-ir.json.gz)을 보존했다. 새 악보 UI/색상 레이어를 생성한 것은 아니다.

- 원 XML SHA: `cae658a519c7fa157928b24a56ec4ed7e2a97418ffd31b043490889a4e5707fe`.
- 관찰 IR 내용 SHA: `8e4a7f5d3022b1e556c90191db49292d630674d013d46f4b6189af7da86ff9a0`.
- 정상 인접 결과 SHA: `91c95a527779890314a272065c5edb05ca388ed158e2694b2b840625049af68f`.

원본 문제의 수정/재파싱/annotation remapping은 별도 단계다. 현재는 오류를 안전하게 알리고 해당 계산을 중지한다.

## 4. 실제 실행·봉인·평가·실패 기록

새 runner는 J3e 정본 report SHA를 고정하고 기존 코드 pins, 72개 prediction packet SHA, frozen sample spans/plan indices, 15개 관찰 IR 내용 SHA를 확인했다. 정상 구간의 봉인된 prediction은 그대로 재사용한다. 72개 전체를 새로 추론한 것으로 보고하지 않는다.

전곡 시간 audit, 새 범위 eligibility, 오류 사례와 정상 인접의 실제 old/new 추론을 **reference report 개방 전에** 완료했다. 모든 72packet 및 source/case artifact를 물리 봉인한 다음에만 주석을 읽고 공통 평가기로 채점했다. 보류는 unknown으로 기존 분모에 남고, 보류 뒤 historical candidate ceiling을 새 후보 계산으로 보고하지 않는다. 이번 실제 72개에는 새 clock 보류가 없어 표가 그대로다.

사후 감사는 모든 pinned 파일·source audit·scope receipt·봉인 packet·공통 metric을 다시 확인했다. 실제 gap은 trial helper가 아닌 독립 rational 계산으로 `[192,195)`와 3quarter exposure를 재현했다. Python tests의 합성 `execution_error`, `unavailable` 출력은 의도한 실패/보류 테스트이며 실제 15package 실행 오류를 의미하지 않는다.

초기 신규 32개 검사에서 1개 실패했다. 합성 tie의 `[1,2)` gap이 저장 sound `[0,2)`에 포함되므로 old false exposure는 0이 아니라 **1quarter**였다. 예상값을 바로잡고 32 PASS, 이어 동일 신규 검사를 포함한 414 PASS를 확인했다. 실제 r1은 15.517초/exit 0으로 완료했고 덮어쓰기/재샘플링은 없었다. 시간은 한 번의 관측이며 속도 benchmark가 아니다.

문서·작성 검사로 변경/신규 9개 파일의 strict UTF-8, Python 5파일 AST, 로컬 문서 링크 249개와 `git diff --check`를 확인했다. 문서 patch의 부분 실행 뒤 생긴 메인 문서 중복 1개를 정리했고 메인 최신 항목/로그61은 각각1개다. 기존 별개 tracked dirty 5경로는 그대로 보존했다.

정본:

- [실행 report](../../../output/harmony-source-clock-2026-10-05-r1/report.json), SHA `6a77673c46dd01fb92ebb91225d3a3ed071b97ad9f2a473480e1676dd830d216`.
- [15개 전체 sound audit](../../../output/harmony-source-clock-2026-10-05-r1/source-clock-audit.json.gz).
- [prediction/source/case 물리 봉인](../../../output/harmony-source-clock-2026-10-05-r1/prediction-freeze.json).
- [독립 사후 감사](../../../output/harmony-source-clock-2026-10-05-r1/post-seal-audit.json): 922고유 SHA/15source/72scope, 원본·운영 변경 없음.
- [검사 실행 기록](../../../output/harmony-source-clock-2026-10-05-r1/test-validation.json): 27개 test module/414검사. 전체 repository test suite를 실행한 것은 아니다.

## 5. 구현 파일·재현

- [시간 관문](../../../src/musicanote_harness/harmony_source_clock.py): `audit`, `SourceClockGuard.scope/infer`.
- [봉인 runner 및 실제 source 진단](../../../src/musicanote_harness/harmony_source_clock_trial.py).
- [관문 검사](../../../tests/test_harmony_source_clock.py), [runner/분모/봉인 검사](../../../tests/test_harmony_source_clock_trial.py).
- [사후 감사](../../../scripts/audit_harmony_source_clock.py).

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -m unittest test_harmony_source_clock test_harmony_source_clock_trial

$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -B -m musicanote_harness.harmony_source_clock_trial --source output/harmony-window-workspace-2026-10-04-r2 --output output/harmony-source-clock-NEW
.\.venv\Scripts\python.exe -B scripts/audit_harmony_source_clock.py --root output/harmony-source-clock-NEW
```

`NEW`와 사후 감사 파일이 존재하면 거부한다. 원본/pinned 코드/입력 내용이 달라지면 과거 정본 비교를 자동 승인하지 않는다. 과거 source annotation을 새 추론 입력으로 넣거나 이용 권한을 변경하지 않는다. 새 학습/외부 API/merge/commit/push는 0이다.

## 6. 다음 우선순위

다음은 여전히 남은 **장문 3구간의 bounded/streaming 공동 화음 선택**이다. 긴 문맥은 작은 타일들의 독립 winner를 이어 붙이지 않는다. 유효한 sound의 원 onset/release와 tie를 유지하고, 모든 후보 경계를 연결한 global run 상태·score를 이어가야 한다. 이번 시간 관문을 그 후보 생성 앞에 둔다.

1. 기존 장문 보류 이유를 source/repeat/자원별로 다시 구별한다. Source/repeat의 모호함을 계산 cap 확대만으로 해제하지 않는다.
2. 원 raw-segment 한도·same-run 시작점·lexical tie-break·negative bonus·실제 다음 화음과의 해결 관계를 보존하는 continuation을 설계한다. 같은 의미 run이 계산 타일 경계를 넘을 수 있어야 한다.
3. Tiny DAG exhaustive optimum, 같은 기존 동결 문맥의 후보/점수/선택 동일성, 자원 중단과 재개, 장문의 실제 whole-score 선택을 검증한다. 근사 pruning이 필요하면 손실/unknown을 명시한 별도 arm으로 보고한다.
4. 그 후 영향 큰 과분할/과병합·applied diminished 해결·5음 혼합 선택 오류와 공개 모델/독립 작품 평가로 간다. 프레이즈/Motif를 화성 정답으로 되먹이는 순환은 만들지 않는다.

이번에 **source-clock 안전 관문은 완료**, 장문 복구·화성 정확도 상승·국소 조성/전위·공개 모델 실행·운영 승격·작곡/편곡 생성은 미완료다. 원 계획과 개발 기록을 유지한다.
