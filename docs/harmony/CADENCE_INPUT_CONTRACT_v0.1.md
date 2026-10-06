# 화성 → 학습형 종지 판별기 입력 계약 v0.1

상태: **설계 계약 / 운영 판별기 미연결**. 2026-10-05. 프레이즈 비교층 병합과 별개다. [개발 기록](records/2026-10-05-phrase-layer-merge-and-cadence-contract.md).

## 1. 현재 제공할 수 있는 것과 없는 것

MusicSearch의 기존 `boundary-harmony.mjs`와 Music Analysis의 새 공동 화성 선택 연구 엔진은 다른 엔진이다. 이번 프레이즈 비교층은 전자를 읽기 전용으로 호출한다. 후자의 후보 근음·구성음 선택 성과를 전자의 화면 정확도로 보고하지 않는다.

새 연구 엔진은 일부 구간에 근음·철자·구성음 후보와 선택을 내지만 **국소 조성·기능·전위를 전 구간에서 보장하지 않는다**. 누락값을 조표나 최저음으로 채워 판별기에 넣지 않는다. 기존 화면 엔진의 전곡 조성 가설도 검증된 국소 조성이 아니다.

목표는 화성 span과 종지 후보를 연결하되, 불확실성과 출처를 그대로 유지하는 것이다. 악보/마디/작곡가 이름을 알고리즘 분기 조건으로 사용하지 않는다.

## 2. 공통 envelope

- `schema_name = musicanote-harmony-cadence-input`, `schema_version = 0.1.0`.
- `score_ref`: 원 source SHA, Canonical IR document ID와 revision(있을 때), 관찰 document ID(인덱스 입력일 때), 분석 ID·엔진/가중치 SHA.
- `coordinate`: quarter 단위 rational `[start,end)`; `written-linear`와 `performed-unfolded`를 구별한다. 반복 경계를 아무 설명 없이 이어 붙이지 않는다.
- `chord_spans`: 각 span의 안정적 ID, 원 note/sounding/span refs, 선택 가설 및 대안·against evidence.
- `melody_ref`: 최상성부 선택 정책·원 event IDs·tie clock·grace 여부. 실제 attack과 tie continuation을 구별한다.
- `meter_timeline`: 못갖춘마디와 박자 변경을 포함한 마디별 박 grid. 6/8의 felt beat와 분모 단위를 구별한다.
- `breath_evidence`: **화성 없이 계산한 하위 호흡층**만 허용한다. 상위 Phrase의 경계·종지 결과는 입력 금지다.
- `input_mode`: `blind-inferred`, `annotated-oracle`, `given-score-chords` 중 하나. 평가와 저장에서 섞지 않는다.

인덱스의 float를 decimal rational로 포장한 값은 `indexed-float-decimal-not-source-rational`로 표시한다. XML divisions의 정확한 분수나 1/3을 복원했다고 주장하지 않는다. 현재 비교층에 Canonical IR ID가 없으면 null을 남기며 인덱스 ID를 Canonical note ID로 바꾸어 부르지 않는다.

## 3. Chord span 필드와 기존 musicomp adapter 대응

| MUSICANOTE 필드 | musicomp 현재 입력 | 규칙 |
|---|---|---|
| `span.start/end` | `.start/.end` | 같은 quarter 축, `[start,end)`, 의미 있는 빈 구간은 보류 |
| `root.spelling`, `root.pitch_class` | 별도 보존 필요 | F♯/G♭를 합치지 않는다. written/concert 명시 |
| `relative_root.fifths_from_local_tonic` | `.root` | **MIDI/반음/음도 번호가 아니다**. 국소 으뜸음 기준 line-of-fifths 정수 |
| `function.selected` | `.function` (`T/PD/D`) | 기능 분석 가설에서 제공; root나 Roman 문자열만으로 임의 확정 금지 |
| `roman.raw` | `.token` | 원 표현과 dialect/version 보존; `7`, `/` 검사는 adapter 규약이며 범용 의미 판정 아님 |
| `inversion.selected` | `.inv` | triad: root=`''`, first=`6`, second=`64`; seventh: root=`7`, first=`65`, second=`43`, third=`42` |
| `bass.relative_fifths` | `.bass` | key/clock이 검증된 가설의 bass만 제공. 관찰 최저음은 별도 evidence |
| `local_key.tonic_pc` | `.tonic_pc` 또는 `.key.tonic_pc` | 가설/선택/대안·confidence semantics·scope 포함; 조표→major 자동 확정 금지 |

예: C 조성에서 C, G, D, F는 relative fifths가 각각 0, 1, 2, −1이다. G의 MIDI pitch class는 7이지만 musicomp `.root`는 1이다. D 조성에서는 D=0, A=1이다. 철자가 G♯인 음과 A♭인 음은 pitch class가 같아도 relative fifths가 다르므로 철자·tonic spelling 없이 역변환하지 않는다.

**중요:** 현재 `cadence.py::_root_pos`는 `.inv`의 None/빈 문자열을 근음 위치로 읽으며, `.bass`가 없을 때도 true가 된다. 미확정값을 이 경로에 보내면 안 된다. 이 계약에서는 전위·bass 누락을 `unknown`으로 보존하고, 향후 판별기에는 root-position-known/value의 mask 또는 입력 자격 보류를 추가해야 한다. Unknown을 root position으로 위장하지 않는다. Missing-aware feature를 추가하면 모델 feature 순서/SHA를 바꾸고 재학습·교차 검증한다.

## 4. 후보와 문맥 처리

1. 화음 변화/지속 후보를 원 시간과 source refs로 정렬한다. 겹치는 경쟁 화음은 대안 lattice로 보존하고 `.root` 하나로 강제 병합하지 않는다.
2. 동일 root/function의 인접 span만 연장할 수 있다. 시간 공백·repeat barrier·국소 조성 변경을 넘겨 지속시켜서는 안 된다.
3. V→I 또는 →V는 넓은 **종지 후보**다. 부속화음의 일시적 해결, 화음 반복, prolongation을 모두 종지로 확정하지 않는다.
4. 근음 위치·강박·종결 음가·선율 음도·쉬는 길이·PD→D→T·선행/도착 지속·하위 호흡·앞 후보 거리 등을 특징으로 제공한다. 음악적 조건을 모두 hard filter로 겹쳐 정답 후보를 잃지 않는다.
5. Source/tie 연결 오류·시간축 불일치·필수 단위 불명은 **데이터 자격 관문**이다. 이것은 음악적 root-position 조건과 다르다. 데이터 오류는 valid negative training example이 아니다.
6. `.root`, `.function`, `.tonic_pc`가 불명일 때 `unresolved-input`과 이유를 반환한다. 음표/화성 대안과 앞뒤 원 악보는 남긴다. “종지 없음”으로 바꾸지 않는다.
7. 침묵 뒤 다음 선율을 후보 도착음으로 대신 쓰는 `_sounding`의 현재 한 beat 허용 정책도 버전/근거에 남긴다. 실제 sounding note와 다음 attack은 구별한다.

현재 musicomp는 `.root/.function`이 같으면 앞/뒤 화음을 건너가며, global `beat_unit(mel)`을 사용한다. 변경 박자·조성·공백 barrier에 대한 이 계약을 소비하도록 **별도 adapter와 회귀**가 필요하다. 이번에는 해당 코드를 변경하거나 모델을 가져오지 않았다.

## 5. 출력과 프레이즈 소비

종지 결과는 `cadence_id`, 도착 화음 onset, 준비/도착 span IDs, 원 선율/베이스 IDs, type 가설(PAC/IAC/HC 및 미지원 유형), 대안, 특징 vector, 선택 여부, model SHA·feature-order SHA·threshold·score/calibration·input mode를 가진다.

Harmony의 cadence strength, logistic sigmoid 출력, 정답 주석의 certainty는 서로 다른 값이다. 현재 비교층은 **기존 boundary-harmony의 미보정 strength ≥0.58**을 관문으로 쓰고 통과한 type에 고정값(PAC/IAC=1, HC=.5)을 준다. 미래 logistic 모델의 threshold=.23을 .58 관문에 단순 연결하거나 값을 부풀리지 않는다. 향후 versioned `accepted decision + producer/threshold/evidence` 계약을 추가하고 별도 검증한다. Sigmoid 값을 검증된 확률로 보고하지 않는다.

종지의 도착 시각은 도착 화음 onset이며, 프레이즈 다음 시작의 note index와 동일한 개념이 아니다. 도착 화음 안의 tie/sounding/긴 종결음 및 뒤 쉼을 보고 마지막 event와 다음 attack을 매핑한다. 먼저 모티프 중간에서 끊거나 도착음을 다음 Phrase로 무조건 넘기지 않는다. shared note 해석은 별도 overlap annotation으로 보존한다.

## 6. 검증 순서와 수치의 의미

1. 합성 단위 검사: C/G/D/F fifths, 전조 후 재기준, enharmonic spelling, 모든 전위, unknown bass/inversion, tie/grace, changing meter, 공백·repeat barrier, 도착음과 다음 attack 분리.
2. 같은 작품 분할로 `annotated-oracle` 입력 평가. 원 musicomp 21특징과 일치하는지 먼저 대조한다. Feature 추가/형식 변경은 기존 모델에 몰래 넣지 않는다.
3. 같은 악장·종지 참조에서 **blind-inferred** 화음+국소 조성 입력 평가. 종지 후보 recall → type/selection F1 → 하위/상위 경계 F1을 각각 보고한다.
4. Train/threshold 선택과 test를 작품군 단위로 분리한다. 전161악장 학습 모델을 동일161에서 다시 채점해 독립 정확도로 부르지 않는다. 근음+구성음만 평가한 화성 결과를 full Roman/local-key 정확도로 쓰지 않는다.
5. MusicSearch UI는 비교층/feature flag부터 유지한다. 기본 경계·Motif·기존 피드백 ID와 화성 연구 엔진 승격은 별도 승인/회귀다.

`K:\Music Composition\DEVELOPMENT_LOG.md` #19의 0.501/0.483은 **주석 화음·국소 조성이 주어진 교차 검증** 기록이며 이번에 독립 재실행하지 않았다. 음악 문법 후보 recall .94, precision .10 역시 같은 oracle 조건이다. 이 수치를 현재 blind 화성+종지 성능으로 보고하지 않는다. DCML의 이용 조건과 로컬 연구 범위는 유지한다.

## 7. 다음 구현의 완료 조건

- 국소 조성/기능/전위의 미확정 상태를 유지하는 versioned harmony adapter를 먼저 만든다.
- Unknown=root position 문제, 지속 span의 공백/전조 barrier, 변경 박자, arrival→phrase mapping을 검사한다.
- 준비된 같은 고정 cohort에서 oracle/blind 차이를 숫자로 낸 다음 판별기 연결 여부를 판단한다.
- 장문 미분석 구간과 source-clock 관문 등 기존 화성 J3 우선순위는 유지한다. 프레이즈 병합이 화성 계획을 대체하지 않는다.
