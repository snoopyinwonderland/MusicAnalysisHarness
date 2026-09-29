# 펼쳐진 화성 구간 분석 파일럿 — 2026-09-24

## 왜 바꾸었나

수직 화음 한 순간보다 **여러 박에 걸쳐 펼쳐진 음형이 어떤 화성을 이루는지**가 편곡·작곡에 더 중요하다는 사용자 피드백에 따라, [한 박 표면 후보 기준선](BLIND_SURFACE_HARMONY_PILOT_2026-09-24.md) 위에 별도 구간 후보기를 추가했다. 입력은 Canonical IR의 measure·sounding event뿐이며, 원본 DCML 화성/NCT/종지 주석이나 Phrase 경계를 읽지 않는다. 운영 UI·Phrase·작곡 생성에는 연결하지 않았다.

## NCT 데이터 조사 결과와 사용 제한

실제 확인한 DCML Beethoven 01-1/01-2와 Mozart K279-1의 `harmonies/*.tsv`에는 `chord`, `numeral`, `chord_tones`, `added_tones`, `cadence`, `phraseend` 등이 있고, `notes/*.tsv`에는 음높이·음가·staff·voice·`chord_id`가 있다. 그러나 **음표마다 passing/neighbor/suspension/appoggiatura 같은 NCT 종류를 확정한 열은 없다**. `chord_tones`는 화음 레이블의 구성음 정보이고 `chord_id`도 음표별 NCT 유형이 아니다. 화음 구성음과 맞지 않는 음을 추려 *검토 후보*로 삼을 수는 있지만, 그 음이 비화성음인지 또는 어느 종류인지를 바로 gold label로 만들거나 모델에 정답으로 학습시키면 안 된다. 다른 코퍼스에 NCT 주석이 존재하는지는 별도 조사 대상이다.

## 구현

- `src/musicanote_harness/harmony_unfolded.py`: 이웃한 1–4개 기보 박의 pitch class를 발음 지속 길이로 합쳐 구간 화음 후보를 만든다. 한 곡 전체에 대해 구간 손실 + 분할 비용의 동적 계획법으로 반열린 구간 `[start,end)`을 선택한다. 쉬는 창은 연결하지 않는다.
- [파일럿 출력 스키마](schemas/unfolded_harmony_pilot.schema.json)로 CLI 산출물을 검증한다. 정식 AnalysisRecord와 별도여서 미보정 적합도를 `confidence`처럼 저장하지 않는다.
- 각 구간은 시작·끝, 구성음 가중치, 후보 상위 5개, 보류 이유, 원본 note ID·sounding ID, 포함된 beat window ID를 보존한다. 각 beat에 구간 후보를 투사해 기존 [별도 DCML 진단](BLIND_SURFACE_HARMONY_PILOT_2026-09-24.md)과 같은 표본으로 비교한다.
- 명확한 한 박 후보(적합도 ≥0.9)가 있으면 더 긴 구간이 그 구성음을 다른 화음으로 덮어쓰지 못한다. 명확한 후보 옆에서 베이스가 완전4도 이상 도약해 바뀌면 그 경계를 넘어 억지로 합치지 않는다. 이는 특정 악보·마디 번호가 아닌 일반적인 **증거 보존 조건**이다. 그럼에도 국소 후보 자체가 틀리면 보호도 틀릴 수 있다.
- `tests/test_harmony_unfolded.py`: 두 박으로 나뉜 C–E–G 분산화음은 한 C 장3화음 구간으로 모으고, 뚜렷한 C→G 장3화음 두 구간은 합치지 않는 반례, 주석 필드에 대한 독립성을 검증한다.

## 동일한 제한 표본 진단

아래 숫자는 *전체 기능화성 정확도*가 아니라, 단순 DCML Roman label이 한 beat 전체를 덮는 창에서 **표면 템플릿 pitch class가 같은 수**다. 쉬운 레이블만 뽑힌 편향된 subset이며 모차르트도 실험에 사용했으므로 독립 holdout이 아니다.

| 표본 | 비교 창 | 수직 한 박 1위 | 펼친 구간 1위 | 수직 상위5 | 펼친 상위5 |
|---|---:|---:|---:|---:|---:|
| Beethoven 01-1 | 49 | 22 | 28 | 36 | 36 |
| Beethoven 01-2 | 40 | 20 | 21 | 32 | 31 |
| Mozart K279-1 | 114 | 45 | 42 | 70 | 86 |

처음의 무제한 구간 병합은 Beethoven 01-2의 1위 일치를 **20→6**으로 크게 악화시켰다. 위 증거 보존 조건 후 **21**로 회복되었다. 그래도 Mozart의 1위는 **45→42**로 악화되었으므로 배포 성능 향상이라고 주장하지 않는다. 특히 긴 구간을 만들며 장·단3화음에 장7도/도미넌트7도를 과도하게 얹는 경향이 있고, 베이스 움직임·비화성음·국소 조성을 충분히 읽지 못한다. 가설 점수는 보정된 confidence가 아니다.

## 재현

```powershell
$env:PYTHONPATH='src'
$d='output\dcml-beethoven-01-2-pilot'
& '.\.venv\Scripts\python.exe' -m musicanote_harness.cli analyze-unfolded `
  "$d\canonical_music_ir.json" --output "$d\blind_unfolded_harmony.json"
& '.\.venv\Scripts\python.exe' -m musicanote_harness.cli evaluate-surface-dcml `
  --surface "$d\blind_unfolded_harmony.json" `
  --annotations "$d\imported_annotations.jsonl" `
  --alignments "$d\alignment_records.jsonl" `
  --output "$d\unfolded_dcml_simple_diagnostic.json"
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests -v
```

2026-09-24 기준 14개 자동 테스트 통과. 명령의 첫 단계는 원본 화성 주석을 읽지 않고, 둘째 단계만 별도 scorer로 읽는다.

## 다음 개발 기준

1. NCT 유형의 gold label이 없으므로, 우선 음표별 `chord_fit`, 앞뒤 음정·음가·박자·동일 성부 해결을 **증거 후보**로 만든다. NCT 이름은 이 근거와 충분한 문맥이 모일 때 가설로만 낸다. `chord_tones` 비교는 evaluation/weak supervision으로 표시한다.
2. 한 박 후보 보호에 더해 **bass line, 각 성부의 안정·경과·계류 가능성, attack/release, 분산화음 반복 패턴**을 구간 점수에 넣는다. 화음 지속과 화음 변화가 생기는 자리의 근거를 함께 설명한다.
3. 현재 세 악장에 임계값을 더 맞추지 않는다. 다른 작곡가·편성의 독립 작품 holdout과 복수의 음악가 검토 사례를 먼저 마련한다. 개선은 적합도뿐 아니라 overmerge/undersplit, 보류 적절성, chord-tone 설명, 생성에서의 재현 가능성을 평가한다.
4. 국소 조성·전위·기능·종지·지배 화성과 반주형을 순차적으로 추가한 뒤에야 Phrase와 편곡/작곡에 공급한다. 주석을 보는 편곡과 주석 없이 분석하는 모드는 계속 분리한다.
