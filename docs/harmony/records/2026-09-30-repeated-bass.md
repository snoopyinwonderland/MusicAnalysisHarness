# 반복 최저음과 같은 구간의 경쟁 화음 비교

HARM-DEV-20260930-19 · 2026-09-30 · `repeated-bass-comparison-0.1.0`

## 목적과 일반 규칙

앞선 감사에서 남은 반복 베이스를 무조건 비화성음/페달로 면제하지 않고, 관측 흐름과 경쟁 후보를 분리한다. 사용자 승인에 따라 실험 모듈을 추가했다. 특정 작품·마디·pitch를 코드 조건으로 넣지 않는다.

1. 원 IR과 부모 문맥의 event coverage/철자/시간/source IDs를 검증한다.
2. 각 sound가 관찰된 전체 지속 시간 동안 실제 최저 pitch인지 검사한다. 더 낮은 음이 중간에 나타나면 이 좁은 반복 최저음 연결에서는 제외한다. 악보에서 삭제하는 것이 아니다.
3. 같은 명시적 part/voice, 같은 철자·옥타브, release와 다음 onset이 정확히 닿는 재타격만 연결한다. cross-staff 자체는 연결을 막지 않는다.
4. 쉼, 옥타브 치환, 다른 voice, 모호한 동음 분기/병합을 임의로 이어 붙이지 않는다. 명시적 XML voice를 실제 대위법 성부로 확정하지 않는다.
5. 두 번 이상 재타격된 연결의 sound refs/시간/관찰 범위 끝 접촉을 저장한다. `complete_repetition_extent_known=false`, `pedal_confirmed=false`다. 문맥 양끝 밖까지 반복이 이어지는지 아직 모른다.
6. 각 후보 구간과 연결이 겹치면 **정확히 같은 interval, 같은 원음표**로 해당 edge의 모든 reading을 대조한다. 베이스 구성음 여부, 근음/철자 구성음, 누락음, 비구성음 refs, 반복 베이스 이외의 비구성음, 기존 blocker를 보존한다.
7. 동일 구조라도 다른 provider/alternative 출처는 유지한다. 베이스를 포함하는 후보 목록을 별도 제공하지만 우승 후보를 고르지 않는다. blocker가 있는 후보도 관측 목록에 남으므로 목록의 존재는 적격 대안의 증명이 아니다.
8. 두 구간만으로 member→nonmember→member의 복귀 조건을 증명할 수 없다. `return_anchor_verified=false`, `bass_exempted=false`를 유지한다. 건반의 sustain pedal과 화성적 pedal point도 혼동하지 않는다.

## 구현과 테스트

- `src/musicanote_harness/harmony_repeated_bass.py`: 반복 최저음의 보수적 연결, 같은 interval의 모든 경쟁 reading 표. 같은 edge/chain 비교는 한 번만 저장하고 pair가 참조한다.
- `src/musicanote_harness/harmony_missing_evidence_trial.py`: 기존 입력 snapshot 검증 재사용, 선택적 `--repeated-bass`.
- `tests/test_harmony_repeated_bass.py`: 신규12개 / 전체 **1,755개 통과**. 쉼·다른 voice·옥타브·동음이명·동음 모호성·더 낮은 음의 개입 반례, cross-staff 연결, 단일 지속음과 구분, 후보 출처/blocker 보존, 입력 불변, 다른 IR 거부를 검사했다.

기존 지속음 페달 모듈은 변경하지 않았다. 현재 추가는 재타격 관측과 경쟁 후보 대조이지 페달 판정기 전체가 아니다. Core/원주석/직접·시간 해결 gate/구조 분석/운영5173/8822화면은 변경하지 않았다. 외부 AI·학습·GitHub 업로드 없음.

## 고정 실행

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_missing_evidence_trial --source output/harmony-distributed-resolution-2026-09-30-r1 --ir-source output/harmony-shared-context-2026-09-30-r1 --output output/harmony-repeated-bass-2026-09-30-r1 --repeated-bass
.venv/Scripts/python.exe -m unittest discover -s tests -q
```

13개 고정 표본 중 baseline 보류1개, pair 예산 보류1개를 그대로 유지했다. 나머지11개에서 관측 geometry를 검사했다. grace의0음가는 `withheld_events`에 남으며 sound를 삭제하거나 duration을 만들지 않는다. 이 geometry 검사가 끝났다는 사실이 기존120개 grace 관계의 해결 계산 미지원이 해소됐다는 뜻은 아니다.

| 표본 | 관찰한 반복 최저음 | 관련 pair | 비구성 베이스 side instances |
|---|---|---:|---:|
| Mozart K280-1 sample16 |F3 6회, global quarter `[6,9)`|718|523|
| Mozart K280-1 sample32 |F3 4회, global quarter `[12,14)`|112|42|
| 나머지 처리 표본 |이번 계약의 연결 없음|0|0|

총830개 pair에 반복 최저음 흐름이 겹친다. 비구성 베이스 side instances565개에는 모두 같은 interval의 bass-member reading이 적어도 하나 있다. 이는 중복 가능한 후보별 수치이며 **565개 개선/페달/정답**이 아니다. 2개 관찰 chain도 독립 작품2개가 아니라 같은 작품의 다른 표본이다. strict 조건의 미검출을 모든 종류의 페달 부재로 해석하지 않는다.

## 추적 가능한 실제 비교

K280 sample16의 chain은 `part_20c02db3336f` / `voice_e4f8a8472450`에서 다음 sound를 잇는다:

`sound_a4786aed9e98` → `sound_7bae7121eca4` → `sound_c396bed7c6de` → `sound_df036fb28d1a` → `sound_33323db50e3f` → `sound_04737ee1e4cd`.

원 IR: `output/harmony-shared-context-2026-09-30-r1/real-cases/reviewm_6fb07c245142d9e0421f/source-snapshot/candidate_revision_ir.json`.

결과: `output/harmony-repeated-bass-2026-09-30-r1/reviewm_6fb07c245142d9e0421f/16.json`, `interval_comparisons`의 edge2/해당 chain 표. 해당 구간 `[6,15/2)`에 34개 reading이 있다.

- reading1, E–G–B♭: 구성음은 모두 관측된다. 그러나 비구성음6 sound가 남고, 그중3개는 반복 F3 chain 이외의 음이다.
- reading5, F–A–C: F3를 포함하지만 C가 이 구간에 없고, 비구성음3 sound도 남는다.
- reading28/31 같은 넓은 확장 화음 후보는 비구성음이0이지만 구성음1개가 미관측이다. 많은 음을 포함하는 후보가 설명량만으로 승리하게 해서는 안 된다.

이 표는 원주석과 대조한 음악적 정답표가 아니다. “F3가 남으므로 페달 처리하면 끝”도 아니고 “F3를 포함하므로 F 화음이 맞음”도 아니다. 두 후보 구간 안에 다른 화음이 섞였는지까지 검사해야 한다.

## 다음 결정

실험 계층으로 유지한다. 다음은 최소 세 구간 이상의 실제 후보 진행에서 반복 베이스의 구성음→비구성음→구성음 복귀와 상성부 변화, 베이스를 구성음으로 포함하는 경쟁 진행, 경계를 너무 넓게 합친 가능성을 함께 비교하는 것이다. 기존 NCT와 해결 증명은 동일 assignment 안에서 양립하는지 별도 확인해야 한다. 불확실한 베이스를 면제하여 양성 수를 늘리는 방식은 채택하지 않는다.
