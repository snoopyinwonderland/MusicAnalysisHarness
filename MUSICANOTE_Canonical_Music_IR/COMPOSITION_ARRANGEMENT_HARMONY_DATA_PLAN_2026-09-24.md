# 화성 자료를 작곡·편곡 Harness에 쓰는 방법 (2026-09-24)

이 문서는 자료 적합성과 실제 주석 사례의 조사 기록이다. 개발 작업 순서와 완료 기준은 [통합 실행 계획](HARMONY_COMPOSITION_HARNESS_IMPLEMENTATION_PLAN.md)을 따른다.

## 판단

현재 폴더는 고전 조성 음악의 **화성 읽기, 종지와 성부진행 규칙 검증, 악보 기반 사례 검색**에 바로 활용할 수 있다. 스타일을 자연어로 지정하면 원하는 악기·반주·밀도로 편곡된 완성 악보가 자동 생성되는 수준의 짝지어진 지시/편곡 라벨은 아직 확인되지 않았다. 기존 악보에서 반주형을 추출하고, 소량의 목적 지향 주석을 추가한 뒤 제약 기반 생성과 사례 검색으로 시작하는 것이 현실적이다. 코퍼스의 작품 수를 지도학습 표본 수로 세지 않는다.

## 실제 증6화음 주석 예

`K:/MusicSearch/data/classical-corpora/dcmlab/beethoven-sonatas/harmonies/01-1.harmonies.tsv`와 짝인 `MS3/01-1.musicxml`의 표본이다. 파일의 작품/악장 식별자 `01-1`과 MusicXML 마디 번호를 함께 확인했다.

| TSV 열 | 값 | Harness에서의 의미 |
| --- | --- | --- |
| `mc`, `mn` | `56`, `54` | 코퍼스의 마디 카운트 56, 인쇄 마디 54. `mc`는 Canonical의 0-based index가 아니다. 차이는 measures 표로 검증하며 여린마디·반복·분할 마디 등을 확인한다. 단순 상수 또는 여린마디만으로 대응을 확정하지 않는다. |
| `quarterbeats`, `mn_onset` | `213`, `0` | 곡 시작부터 213 quarter, 인쇄 54마디 시작 |
| `duration_qb`, `timesig` | `4.0`, `2/2` | 이 해석적 화성 구간은 다음 레이블까지 4 quarter; 2/2 한 마디 |
| `label`, `chord`, `special` | `Ger6`, `Ger6`, `Ger` | 독일 증6화음이라는 분석 라벨과 파싱 결과 |
| `globalkey`, `localkey` | `f`, `iv` | 전역 조성과 이 지점의 국소 화성 문맥. 원문 표기 보존 필요 |
| `chord_tones`, `bass_note` | `-4, 0, -3, 6`; `-4` | 데이터셋 고유의 상대 음도 표현. 실제 음고는 조성/표기법 및 악보 사건과 함께 해석해야 한다. |
| 다음 행 | `mc=57`, `mn=55`, `quarterbeats=217`, `label=V[V\|HC}{`, `cadence=HC`, `phraseend=}{` | V 도착과 Half Cadence, 프레이즈 맞물림 표지가 뒤따른다. `Ger6 → V`는 이 데이터의 **실제** 연속 레이블이다. |

MusicXML의 `<measure number="54">` 안에는 `<harmony><function>Ger6</function><kind text="">none</kind></harmony>`가 있다. 이것은 악보에 부착된 **해석 주석**이며 음표/쉼표의 관찰 사실로 Core에 넣으면 안 된다. 독립 TSV도 같은 해석과 위치를 제공한다. 동일한 레이블이 XML과 TSV에 있어도 두 독립 전문가의 판정으로 세지 않는다. [DCML 공식 표준](https://dcmlab.github.io/standards/build/html/reference/reference.html)은 It6/Ger6/Fr6와 Cadence/프레이즈 문법을 정의한다.

## 입력 계약

Storage rule: use Canonical Music IR for the score's observed events and stable coordinates; store harmonic/style/accompaniment interpretations and composition/arrangement decisions in separate versioned records referencing the IR `score_id`, event IDs and `[start,end)` span. Keep the original TSV/JAMS/RomanText/MusicXML and source hash. A source `<harmony><function>Ger6</function>` is an imported annotation, never a Core note property. Melody and Piano Solo editions each get their own score/IR document with an explicit version-pair relationship and alignment map; do not merge their note IDs. The present prototype `musicanote-canonical-ir-0.2` and formal `musicanote-canonical-music-ir 0.1.0` need a compatibility adapter and ID/coordinate migration audit before bulk import.

Illustrative linked records for the observed Beethoven row (IDs are examples, not produced IDs):

```json
{
  "score_core": {"score_id":"beethoven_op2_no1_mvt1_score", "measure_id":"m_sequential_56", "printed_measure_number":"54", "global_start_quarter":{"numerator":213,"denominator":1}},
  "harmony_record": {"analysis_type":"harmony", "score_id":"beethoven_op2_no1_mvt1_score", "target":{"span":{"start":{"numerator":213,"denominator":1},"end":{"numerator":217,"denominator":1}}}, "raw_label":"Ger6", "hypothesis":{"label":"Ger6","local_key_raw":"iv"}, "provenance":{"corpus":"DCMLab","file":"harmonies/01-1.harmonies.tsv","annotation_status":"corpus_reviewed"}},
  "next_harmony_record": {"analysis_type":"harmony", "target":{"span":{"start":{"numerator":217,"denominator":1},"end":{"numerator":220,"denominator":1}}}, "raw_label":"V[V|HC}{", "cadence":"HC", "phrase_mark":"}{"}
}
```

This snippet shows linkage only; the formal Analysis Record schema requires additional IDs, hypotheses/confidence, evidence refs, status and engine fields. A corpus annotation is not a model prediction, and importing it must not assign an invented confidence. The example's `local_key_raw` is retained verbatim until the corpus-specific key resolver validates its absolute meaning.

1. `score_source`: 원본 파일·hash·작품·악장·판본·권리. Canonical IR은 모든 음표/성부/마디, 조표·박자, rational quarter 시간, attack/sounding과 source_ref를 보존한다.
2. `harmonic_annotation`: 원본 레이블과 native 좌표, 출처 코퍼스/주석자/자동 생성 여부, 정렬 상태, 분석 span `[start,end)`, local/global key hypothesis, chord spelling/function/target, governing vs surface 역할, cadence/phrase mark, 대안. MusicXML harmony tag도 Analysis/Annotation 인터페이스로 추출한다.
3. `style_profile`: 작품 전체 및 구간별 장르/시대, 편성, 박자·템포 범위, 리듬 feel, 질감, 밀도, 음역, 화성 어법, 아티큘레이션. 작곡가 이름만으로 스타일을 확정하지 않는다. 사용자가 허용/금지할 변형 범위와 예시 악보 구간을 연결한다.
4. `accompaniment_pattern`: bass/inner/upper 역할별 attack 위치를 박자에 대해 정규화하고 음도, 음역, 보이싱, 수평 진행, 다이내믹/아티큘레이션, 1–2마디 반복 단위와 변형을 저장한다. `arpeggio`, `block_chord`, `Alberti`, `waltz`, `stride`, `pad` 같은 이름은 별도의 검토 가능한 스타일 라벨이다. 자동 관찰 features와 사람이 붙인 이름을 분리한다.
5. `arrangement_pair`: 같은 음악의 Melody 판본과 Piano Solo/실제 편곡 판본을 **정렬과 유사성 검증 후** 짝짓는다. 선율 유지율, 추가된 음, 삭제/재배치된 음, 화성 변화, 베이스·내성·리듬 패턴, 악기와 음역을 before/after 기록으로 만든다. 제목 일치만으로 짝을 확정하지 않는다.
6. `request_and_plan`: 자연어 요구를 구조화한다. 예: `"선율은 유지하고, 중간 음역의 잔잔한 피아노 아르페지오, 낮은 음역의 1박 베이스, 종지 직전만 밀도 증가, 원래 조성과 마디 구조 유지"`. 이를 `preserve_melody=true`, `key_policy=keep`, `accompaniment=broken_chord`, `bass_pulse=beat1`, `density_curve=...`, `cadence_policy=preserve`, `register_limits` 등으로 파싱하고 사용자에게 보여 준다. 화성 어법이나 스타일 참조를 명시하지 않은 항목은 추정치로 표시한다.

## 작곡·편곡 Harness 흐름

`score/seed → Canonical IR → source quality/alignment check → melody and bass roles → local key + surface/governing harmony candidates → Phrase/Cadence map → style/pattern retrieval → arrangement or composition plan → constrained note generation → notation export → validation → review`

- **분석 단계**: C/E/G 같은 동시 음군, 장식음, 짧은 비화성음, 지속음/타이를 구분한다. 문맥 속 조성과 기능을 후보로 보관한다. `Ger6` 같은 레이블은 해당 조성의 해석과 다음 V로 향하는 성부진행 제약을 가진다.
- **작곡 단계**: 먼저 구절·조성 이동·Cadence 목표와 화성 리듬을 계획한다. 선율을 생성하거나 주어진 선율을 맞춘 뒤, 베이스/내성은 진행 제약으로 만든다. 주석 사례는 새 작품의 음표를 그대로 복사하기 위한 템플릿이 아니라 가능성·제약·평가 기준이다.
- **편곡 단계**: 입력 선율과 구조 보호 조건을 먼저 확정한다. 경계별 화성 후보를 검증하고, 선택된 반주 패턴을 조/박자·음역에 맞게 변환하여 배치한다. 사용자가 허용한 경우에만 재화성화하며 원본과 편곡의 차이를 기록한다.
- **평가 단계**: 음표 충돌, 저음·선율 중복, 음역, 연주 가능성, 불협화음의 준비/해결, Cadence 의도, 패턴 일관성, 요구 준수, 원본 유사성을 별도 지표로 본다. 화성 해석 불확실성이 크면 후보 비교나 인간 검토로 보낸다.

## 데이터 적합성

| 용도 | 현재 자료 | 부족한 부분 |
| --- | --- | --- |
| 고전 조성 화성·Cadence 학습/검증 | DCMLab, When in Rome 인간 분석, TAVERN; ChoCo 부분집합 | 판본 정렬·중복 제거·주석 표준 통합 |
| 코드 진행을 조건으로 한 초안 생성 | 화성 span과 악보가 있는 DCMLab, 일부 WiR/ChoCo | 생성 정책, 성부진행 제약, 결과 평가 |
| 피아노 반주 패턴 추출 | 전곡 악보의 성부/온셋/음역 관찰; 일부 full score/melody 쌍 | `반주 스타일` 라벨, 역할 검증, before/after 편곡 쌍 |
| 특정 장르·시대 요구의 정밀 편곡 | 일부 장르 자료와 악보, 사용자의 기존 사례 | 장르·질감·난이도·연주기법 등 목적 지향 주석과 검토된 요청/결과 쌍 |
| 팝/재즈/현대 스타일 전반 | ChoCo의 일부 코드 데이터 및 KYSing·MusicSearch 점수 | 실제 편곡 score의 다성부/반주·사용 허가·정렬 데이터. 고전 코퍼스만으로 일반화 불가 |

## 첫 구현 단위

1. DCMLab 10–20곡으로 Roman/key/cadence와 note/measure 좌표 연결률을 측정한다. `Ger6 → V` 같은 진행을 스코어 이벤트와 함께 케이스로 저장한다.
2. 20–30개의 악보 구간에서 반주형을 자동 추출해 사람이 이름·역할·기능을 검토한다. 전 구간에 정확한 화음 레이블을 요구하지 않는다.
3. 기존 Melody/Piano Solo 쌍에서 10곡을 골라 실제 변환 차이를 기록한다. 특히 선율이 어느 성부에 남는지, 화음 추가와 장식음을 분리한다.
4. 피아노 단일 편성, 조·박자 유지, 선율 유지의 제한된 생성 프로토타입으로 시작하고 악보 화면에서 원본/결과/분석 근거를 함께 검토한다. 이후 재화성화와 다른 편성을 확장한다.

User feedback, AI candidates, reviewed labels and corpus annotations are separate records. Corpus licences differ; source-level rights must be retained when creating redistributable models or examples.
