# 독립 전곡 표면 화음 후보 파일럿 — 2026-09-24

## 목표와 산출물

음악의 부분을 이해하여 작곡·편곡에 쓰려는 목표에서, 먼저 **음표가 실제로 울리는 상태를 전곡에 걸쳐 관찰하고 표면 화음 후보를 내는 첫 독립 단계**를 만들었다. `src/musicanote_harness/harmony_surface.py`는 정식 Canonical IR의 `measures`와 `sounding_events`만 읽는다. DCML 원본 화성·Cadence·Phrase 주석, 기존 Phrase 분석, music21의 전체 조성 추정은 입력에 사용하지 않는다. 산출물은 [별도 파일럿 스키마](schemas/surface_harmony_pilot.schema.json)의 beat window별 pitch-class 가중치, bass, 음표/발음 ID, 화음 후보 상위 5개와 보류 이유다. 정식 화성 AnalysisRecord나 Canonical Core는 변경하지 않았다.

이것은 **완성된 화성 이해 엔진이 아니다**. 조성·로마숫자·비화성음·지배 화성·종지·프레이즈로 아직 해석하지 않는다. `fit_score`는 현재 창의 음 집합이 기본 3·7화음 템플릿과 맞는 정도일 뿐, 정확도나 확률로 보정된 `confidence`가 아니다. `display_hint_index`도 검증된 정답 선택을 의미하지 않는다.

## 계산 계약

1. 기보된 마디의 박자 분모를 quarter 길이로 바꾸어 전곡을 반열린 `[start,end)` beat window로 순회한다. pickup·변박의 실제 마디 길이를 사용한다.
2. 타이로 이어진 음표를 분할된 note가 아닌 `sounding_event`로 읽는다. 창과 겹쳐 울린 길이를 pitch class별로 합하고, 같은 pitch class의 중복은 한 창에서 최대 1로 제한한다. 짧은 지나가는 음은 긴 지속음보다 낮은 가중치를 갖지만 NCT라고 판정하지 않는다.
3. 12개 근음 × 기본 장·단·감·증3화음 및 5종 7화음 템플릿을 평가한다. `purity`는 관찰 가중치 중 템플릿에 맞는 비율, `completeness`는 템플릿 구성음 중 관찰된 비율이다. 두 값의 가중 합으로 후보를 정렬한다. 임계값은 파일럿 휴리스틱이며 학습된 파라미터가 아니다.
4. 무음은 `rest`, pitch class 두 개 이하는 `abstained`, 템플릿 적합도가 낮으면 `abstained`, 상위 후보의 차이가 작으면 `ambiguous`로 남긴다. 보류 상태의 1위는 화면상 **선택되지 않는다**.
5. 각 창은 원본에 닿는 note ID·sounding event ID를 포함한다. 판단을 바꿀 때 음표로 돌아가 확인할 수 있다.

## 세 악장 실행 결과

| 입력 IR | 창 | 후보 표시 | 모호 | 보류 | 무음 |
|---|---:|---:|---:|---:|---:|
| Beethoven Sonata 01-1 | 306 | 164 | 67 | 73 | 2 |
| Beethoven Sonata 01-2 | 183 | 97 | 73 | 12 | 1 |
| Mozart K279-1 | 400 | 249 | 92 | 55 | 4 |

이 수는 **분류 상태의 개수이지 정답률이 아니다**. Beethoven 01-2의 quarter 1 창에서는 실제 음 C–F–A를 바탕으로 `F:major`가 1위이며 원본 주석은 `I`다. quarter 5의 `C:major`는 원본 주석 `V`와 조성 F를 고려하면 서로 양립 가능하다. 하지만 이것은 두 사례의 수동 예시일 뿐 전체 일치율이 아니다. quarter 12의 복잡한 동시음은 적합도가 낮아 보류된다. 증6화음처럼 현재 템플릿에 없는 화음은 인접 3·7화음으로 억지 확정하지 않아야 한다.

### 별도 진단: 단순 DCML 주석과 표면 구성음 비교

`src/musicanote_harness/harmony_surface_eval.py`는 분석이 **끝난 뒤에만** 원본 주석을 읽는다. `localkey=I/i`, 단순 `I/ii/IV/V/vi` 등과 단일 승인 주석이 한 beat 전체를 덮는 창만 고른다. 로마숫자를 국소 조성의 음 집합으로 풀어 후보 템플릿의 pitch class와 비교한다. 전위·적용화음·복잡한 표기는 일부러 제외한다.

| 표본 | 비교 가능 창 | 1위 구성음 동일 | 상위 5개 중 동일 | 실제 표시된 1위 동일 |
|---|---:|---:|---:|---:|
| Beethoven 01-1 | 49 | 22 | 36 | 21 |
| Beethoven 01-2 | 40 | 20 | 32 | 19 |
| Mozart K279-1 | 114 | 45 | 70 | 45 |

이 역시 **화성 기능 정확도나 전체 악보 정확도가 아니다**. 소수의 쉬운 레이블만 본 진단이며, 코퍼스의 로마숫자는 지배 화성이고 한 박의 실제 울림에는 비화성음·장식·계류가 있을 수 있다. 예를 들어 Beethoven 01-2에서 원본 `F:V`인데 창에는 `C:major7`이 1위인 경우가 있어, 추가 음을 그대로 새 화음으로 오인할 가능성이 보인다. 수치를 높이려고 이 세 곡에 맞춘 임계값/곡별 규칙을 만들지 않는다.

## 실행

```powershell
$env:PYTHONPATH='src'
& '.\.venv\Scripts\python.exe' -m musicanote_harness.cli analyze-surface `
  'output\dcml-beethoven-01-2-pilot\canonical_music_ir.json' `
  --output 'output\dcml-beethoven-01-2-pilot\blind_surface_harmony.json'
& '.\.venv\Scripts\python.exe' -m musicanote_harness.cli evaluate-surface-dcml `
  --surface 'output\dcml-beethoven-01-2-pilot\blind_surface_harmony.json' `
  --annotations 'output\dcml-beethoven-01-2-pilot\imported_annotations.jsonl' `
  --alignments 'output\dcml-beethoven-01-2-pilot\alignment_records.jsonl' `
  --output 'output\dcml-beethoven-01-2-pilot\surface_dcml_simple_diagnostic.json'
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests -v
```

`tests/test_harmony_surface.py`는 기본 장3화음, 무음, 두 음만 있을 때 보류, 주석 필드 변경에 대한 불변성, JSON Schema, 별도 scorer의 모호한 정렬 제외를 검증한다. 2026-09-24 전체 12개 테스트 통과. 운영 UI나 Phrase 판단에는 아직 연결하지 않았다.

## 다음 구현 — 이해에서 생성까지

1. **전곡 blind 평가**: DCML 주석을 analyzer 입력이 아닌 비교기로만 사용한다. 판본·작품 단위 holdout을 고정하고, 절대 화음 후보를 DCML의 국소 조성/기능 레이블과 비교 가능한 평가용 표현으로 변환한다. 겉보기 적합도를 정답률로 혼동하지 않는다.
2. **화성 시간폭과 성부 역할**: 단일 beat가 아니라 attack·지속·분산화음·반주 패턴을 여러 박에 걸쳐 묶는다. 선율 장식과 화음 구성음, 베이스 근거, 성부진행을 분리하고, phrase 경계를 입력받지 않는 독립 segmentation을 시험한다.
3. **국소 조성·기능·대안**: 조표는 관찰값으로만 쓰고, 국소 조성 후보와 화음 후보를 함께 갱신한다. Roman numeral, 전위, 적용화음, 차용, 증6화음, NCT/지배 화성을 단계적으로 확장한다. 지원 밖 음악은 보류한다.
4. **Cadence/구조**: 화성의 준비·도착과 성부진행, 박자·호흡을 묶어 종지 가설을 만든다. 이후 Phrase/Motif에는 독립 근거와 반대 근거를 함께 전달하되, 기존 Phrase 결과를 화성 판정에 쓰고 다시 Phrase에 가산하는 순환을 금지한다.
5. **편곡·작곡**: 화성 가설만으로 음표를 만들지 않는다. 구조 역할·멜로디 골격·보이싱·반주형·음역·밀도와 제약을 함께 기록하고, 생성된 악보의 보존/변경 조건을 별도 validator로 검사한다.
