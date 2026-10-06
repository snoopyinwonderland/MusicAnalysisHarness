# 지속·재타격·순차 음군과 화성 가정별 역할 근거

개발 ID: `HARM-DEV-20261001-04`. 이전 [좌표·literal observation](2026-10-01-native-semantic-alignment-and-pattern-observations.md)의 후속이다. 화성 개발 정본은 [README](../README.md), 생성 목표/큰 순서는 [의미·생성 로드맵](../MUSICAL_SEMANTICS_AND_GENERATION_ROADMAP.md)에서 관리한다. 인수인계 문서에 실험 이력을 누적하지 않는다.

## 1. 목적과 이번 완료 범위

단선율을 풍부한 피아노·실내악·관현악으로 배치하려면 화음 이름뿐 아니라 실제 음표가 유지/재타격/순차 제시되는 방식을 보존해야 한다. 이번 단계는 그 **관찰 → 화성 가정에 조건부인 역할 근거**를 구현한다. 곧바로 반주 템플릿·의미 성부·작곡기로 승격하는 단계가 아니다.

완료한 기능:

- 모든 raw part/voice lane에서 타이로 이어진 한 sounding event와 독립 재타격을 구분한다.
- 철자·옥타브가 같은 음이 실제로 이어지는 범위를 묶고, 쉼/틈·다른 성부·이명동음·옥타브 교대는 연결하지 않는다.
- 동시 onset group과 서로 다른 유리수 시각의 순차 attack을 구분한다. 음가가 겹친다는 이유로 순차 attack을 부정하지 않는다.
- 원주석 또는 호출자가 공급한 여러 화성 가정을 각각 immutable track으로 저장할 수 있다.
- 그 가정별 구성음/비구성음/미정, 화음 상대 도수, 순차 공격의 시간 간격, 페달 형태·분산형 후보를 계산한다.
- 실제 G1의 27개 문맥에 연결하고 모든 원자료·Core·SOURCE·이전 분석을 불변으로 유지한다.

미완료: 역할 확정, 주선율/구조 베이스 선택, 페달/NCT 면제, 분산형+장식음 공동 최종 판정, 반주 스타일·손별 연주성·반복/전개/배치 계획, 생성, G1 전체 완료, 사용자 악보 화면 및 운영 적용.

## 2. 일반 규칙과 반례

### 2.1 Literal geometry

1. `Sounding Event`와 `Attack Event` 및 원 note의 참조/시각/누적 음가를 대조한다. 타이 continuation은 새 attack이 아니다. 누락/중복 sounding membership·불연속 source note·음가/attack 불일치는 보류한다.
2. pitch identity는 `part_id + voice_id + step + rational alter + octave`다. MIDI만 같아도 B♯/C는 별개이고 C2/C3도 별개다. raw voice 자체를 음악적 대위법 성부로 인증하지 않는다.
3. 정확히 닿거나 겹치는 같은 pitch interval의 연결 성분을 보존한다. 다른 ID로 임의 branch를 선택하지 않는다. 겹친 동일음은 `overlapping_same_pitch`/ambiguity로 남긴다. 쉼표/무음 틈을 메우지 않는다.
4. 원 onset/duration/extent와 context에서 관측한 범위, target overlap을 분리한다. context 밖 원 attack을 target 시작의 재타격으로 발명하지 않는다. 범위 끝은 제외한다. grace는 별도 point이며 연주 음가를 추정하지 않는다.
5. 모든 part의 실제 음표를 유지한다. 악기 이름·staff 번호·원 `Pedal`의 pitch token·최저음 여부·설명 키워드로 특정 lane을 의미 성부로 선택하지 않는다. 내성·상성부 지속도 관찰한다.

합성 반례에는 타이 C–C / 독립 C 재타격 / 쉼 뒤 C 재등장, 동시 C/E/G / 1/3-quarter 간격 C→E→G, 음가가 겹치는 순차 공격, 내성 C 위아래 이동, 동일음 분기, octave/enharmonic/다른 lane, target/context crop, endpoint/grace를 포함한다.

### 2.2 화성 가정 계약

`musical_harmony_assumption.py`의 track은 `score_id`, `ir_document_id`, 전체 IR 내용 SHA, 원 score SHA에 결합한다. 각 segment는 정확한 `[start,end)`, label, 독립적인 root spelling, 모든 member spellings, usable/blocked, 원 locator와 blocker를 가진다. label 문자열에서 근음을 추측하지 않는다. 다른 가정은 다른 track이며 자동 승자는 없다.

동일 track 내부 중복/겹침·구간 밖 span·중복 구성음·낡은 binding은 거부한다. 빠진 구간/blocked 구간은 `coverage_holes`로 남긴다. root가 미정인 caller 가정은 membership을 비교할 수 있지만 degree는 null이다. root가 있어도 도수는 **철자 기반 1–7 도수**이며 실제 inversion/기능/구조 역할의 확정이 아니다.

RomanText importer는 원주석의 화성을 하나의 **가정**으로만 연결한다. 검증용 gold나 독립 정답으로 사용하지 않는다.

- 원 analysis SHA와 frozen source meter index를 대조한다.
- 명시적 초기 박자와 초기 inline tonal key를 요구한다. music21 기본 C, 조표, `Key:` 헤더를 조성 확정으로 인정하지 않는다. 초기 key가 없으면 뒤 선언으로 과거를 복구하지 않고 v0.1에서 전체 import를 보류한다.
- source/IR printed measure 고유성, 실제 박자, 정상 마디/음가·padding 및 범위 내 정확 onset/duration을 확인한다.
- 고유한 literal `mN` 원문 줄이 없는 copy/range/generated 사건은 usable provenance로 승격하지 않는다. 안전한 좌표/parsed spelling은 blocked segment로 보존한다.
- `.33/.66` 등 반올림/비이진 소수 beat를 parser가 셋잇단으로 바꾼 결과는 정확 좌표로 인증하지 않는다. 해당 source measure는 보류한다.
- source annotation의 SHA/path와 usable segment의 줄 번호/raw line을 요구한다. source author라는 사실을 human reviewer 승인으로 바꾸지 않는다.

현재 written pitch 기준이다. 기존 adapter의 concert transposition 미구현을 해결하거나 관현악 실음 정렬을 인증한 것이 아니다. 이 track과 후속 근거를 concert-pitch 기능/관현악 생성에 그대로 공급하지 않는다.

### 2.3 페달 형태

연결 pitch episode와 화성 가정의 정확한 교집합을 나누어 구성음/비구성음/미정을 시간순 기록한다. 최소 두 가지 서로 다른 구성음 집합과 실제 비구성음 구간이 있을 때만 pedal 형태 후보를 만든다.

- 시작/끝이 모두 member이고 중간에 nonmember가 있으며 coverage/동일음 branch/context crop 보류가 없으면 `anchored_pedal_shape`다.
- 변화+nonmember는 있지만 복귀/완전 문맥 근거가 부족하면 `unanchored_pedal_shape`다.
- 다른 가정에서 계속 member일 수 있다. 두 결과를 모두 유지한다.
- 단지 두 구간의 member→nonmember로 return anchor를 확인하지 않는다.

이 상태는 **페달 확정이 아니다**. suspension/다른 NCT 관계/다른 화성이라는 대안을 보존한다. 상부 실제 지지·독립 준비/해결·화성 비교는 후속 연결 대상이다. source tag를 정답으로 베껴 쓰지 않는다.

### 2.4 순차 구성음·분산형

각 **한 화성 가정 segment × 한 raw lane**의 attack groups를 비교한다. 세 개 이상의 서로 다른 onset, 세 개 이상의 서로 다른 철자 구성음, onset마다 한 공격음, known member만 있을 때 `broken_chord_shape`로 표시한다. 동시 화음만으로 성립시키거나 화음 교체 양쪽 pitch union을 합쳐 성립시키지 않는다.

가정의 구성음으로 순차 제시된 형태이지 분산 반주 확정이 아니다. chord-tone melody/다른 texture도 가능하다. 세 음 기준은 보수적인 v0.1 후보 조건이지 모든 분산화음의 음악적 정의가 아니다. 두 구성음만의 반주·chordal onset group·장식음 섞인 형태는 원음을 지우지 않고 `insufficient_shape`/이유를 남긴다.

`degree_by_note`, `onset_deltas_quarter`, 원 literal sound의 음가/철자/ID를 보존한다. `missing_members`는 **attack에서 제시되지 않은 구성음**이다(`membership_scope=attacks_only`). 이미 지속 중인 구성음의 실제 부재나 화음의 불완전성으로 해석하지 않는다. blocked 가정은 `unknown_note_ids`로 분리하고 `missing_members=null`로 둔다. 미정은 비구성음이나 생략음이 아니다.

## 3. 파일·API·저장 관계

| 파일 | 기능 |
|---|---|
| `src/musicanote_harness/musical_harmony_assumption.py` | `build_track`, `import_romantext`, `validate_track` |
| `docs/harmony/schemas/musical_harmony_assumption.schema.json` | 가정·출처·span·hole·보류 계약 |
| `src/musicanote_harness/musical_role_evidence.py` | `analyze`, `validate_evidence`; literal과 가정별 근거 |
| `docs/harmony/schemas/musical_role_evidence.schema.json` | 역할 미확정 evidence 계약 |
| `src/musicanote_harness/musical_role_evidence_trial.py` | `run` 및 frozen G1 전수 실행 CLI |
| `tests/test_musical_harmony_assumption.py` | 13개 계약/수입 반례 검사 |
| `tests/test_musical_role_evidence.py` | 18개 geometry/가정/미정/불변성 검사 |
| `tests/test_musical_role_evidence_trial.py` | 12개 inventory/계보/분모/재실행/쓰기 보호 검사 |

모듈/계약은 이번 첫 연구 prototype v0.1.0이다. `mha_`/`mre_` ID와 canonical JSON SHA, 가정 ref/원 observation ref를 사용한다. 원문 SOURCE를 바꾸거나 semantic BOUND로 자동 승격하지 않는다. 숫자 confidence, selected label, 최종 role, gold, training eligibility를 발명하지 않는다.

원 XML + 전체 IR + SOURCE + coordinate attempt + literal window → 별도 harmony assumption track → 별도 role evidence의 관계다. 원음표 참조와 source/alignment/IR hash를 따라가면 악보를 재현할 수 있다. 이번 role JSON만을 MusicXML 조판 파일로 취급하지 않는다.

standalone JSON Schema 검사는 형식/seal 검사다. 전체 입력을 주는 replay는 source binding·계산 재현까지 검사하지만 음악적 정답을 검증하지 않는다. producer/schema가 바뀌면 registry/migration 없이 기존 record를 현재 계산으로 재봉인하거나 덮어쓰지 않는다.

## 4. 실제 적용 분모와 결과

최종 출력은 `output/musical-role-evidence-2026-10-01-r2/`이다. 입력은 이전 G1 최종 `output/musical-semantic-alignment-2026-10-01-r2/`의 **14 score files / 27 observations**이다. 새로운 독립 작품 27곡을 추가한 것이 아니다. 같은 작품·겹친 context·동일 geometry의 두 source statements가 있다. 독립 작품 수나 작품별 holdout 성능은 측정하지 않았다.

이전 G0의 4,729개 원문 및 G1 전체 208 Pedal 분모/181 미연결·보류도 삭제하지 않았다. 이번 대상은 정확한 기존 좌표 문맥이며 주로 Lieder이다. Beethoven/Mozart·심포니 전체의 의미 역할을 새로 검증했다는 주장이 아니다.

최종 r2: exit 0 / 242.940초 / 모든 27개 `conditional_evidence`, import exception/blocked outcome 0. 이는 실행 완료이며 모든 화성/역할이 usable 또는 정확하다는 뜻이 아니다.

| 분모/관측/가정 | 결과 |
|---|---:|
| source harmony assumption tracks | 14 |
| usable parsed harmony segments | 669 |
| source copy/range provenance 보류 segments | 586 |
| import 진단 instances | 644 |
| literal sounding event instances | 2,687 |
| 별도 grace point instances | 7 |
| exact pitch episode instances | 1,981 |
| 그중 single sound / touching reattacks | 1,584 / 397 |
| literal onset group / rest instances | 1,748 / 249 |
| anchored / unanchored pedal 형태 instances | 4 / 35 |
| pedal 형태 조건 미충족 instances | 1,942 |
| broken-chord 형태 / 조건 미충족 profiles | 16 / 789 |
| 미정을 별도로 보존한 attack note instances | 671 |
| human validation / training / gold / generation-ready | 모두 0 |

count는 겹치는 문맥의 instances이다. 4+35는 정확한 pedal 수가 아니며 16은 정확한 arpeggio/반주 수가 아니다. 모든 conditional profile은 전체 context에서 계산하고 target overlap을 별도로 제공한다. 이번 anchored 후보 4개는 모두 target과 교차한다. 전체 27개 observation의 고유 score/target geometry는 이전과 같은 25개다.

진단 644건은 copy/range/불명 source locator 586 + 비이진/반올림 beat 49 + pickup/불규칙 마디 4 + score 밖 RN span 3 + 마디 미존재/비고유 2다. copy/range의 586개는 안전한 좌표를 가진 blocked segment에도 포함되므로 **586+644를 서로 다른 source 화음 수로 합산하지 않는다**. 진단에는 RN 없는 마디 등 일반 보류가 들어갈 수도 있다. source harmony segment도 source 주석의 정답 인증이 아니다.

14개 source track의 669개 usable 부분에서 비교하고 나머지는 unknown/hole로 남겼다. copy/range의 explicit source 계보 확장은 데이터 활용을 늘리기 위한 후속 큰 수입 작업이며, 현재 parser의 복사 확장 결과만으로 provenance를 발명하지 않는다.

## 5. 실제 사례와 해석 제한

### Coleridge-Taylor, Op.57 No.1

입력 case: `631dd204fc18f0b32be641f7`. 원 observation `mpo_54e25b10c178c5eadd8a7d69`. target `[18,21)`, context `[27/2,27)`이다.

기존 원 `Pedal: E m5 b1 m5 b3`로 위치를 연결했지만 그 pitch token으로 lane을 지정하지 않았다. 실제 IR에서 E1/E2의 타이 sound `[18,22)`를 각각 관찰했다. source harmony 가정에서는 `i(member) → V43(nonmember) → viio43/VI(nonmember)`로 나온다. sound가 다음 member 복귀 전에 끝나므로 두 개 모두 `unanchored_pedal_shape`다. source가 Pedal이라고 썼다는 이유로 확정하거나 복귀음을 발명하지 않는 실제 사례다.

이 구간의 짧은 source harmony segment에서 공격음 세 개 조건을 만족시키지 못하므로 arpeggio 확정도 없다. 긴 문맥에 E/G/B가 있다고 한 화음의 분산형으로 합치지 않는다. 향후 지속 중인 구성음 + 분산 제시 + 조건부 NCT의 공동 비교가 필요한 사례로 유지한다.

### 복귀 형태 후보가 나온 사례

- Coleridge-Taylor Op.57 No.6 `Too late for love`: D3의 touching reattacks. source 가정에서 member/nonmember/return 형태가 있으나 의미 페달이나 구조 베이스 확정은 아니다.
- Louise Reichardt Op.4 No.1 `Sehnsucht nach dem Vaterlande`: E♭2/E♭3를 별개 episode로 유지. 같은 후보 geometry라도 octave doubling을 한 음으로 합치지 않는다.
- Clara Schumann Op.12 No.4 `Liebst du um Schönheit`: G♭3의 재타격 및 `iiø65 → V → V9` 가정 아래 membership 복귀. 화성의 의미/조성/역할 자체는 아직 검수되지 않았다.

이 목록은 shape 예시이며 사용자 승인·gold positive·세 가지 style family 검증으로 세지 않는다. 원문/악보/track/evidence의 실제 refs는 각 output case 디렉터리와 `evidence-index.json`에 있다. 이번에는 새 브라우저 페이지/5173 overlay를 만들지 않았다.

## 6. 검증·발견·재현

신규 검사: assumption 13 + role 18 + trial 12 = 43. 전체 Python 2,494개 / 81.053초 / OK. 합성 음악 반례와 데이터 계약 검사이며 화성 정답률 인증이 아니다. 병렬 검토에서 원 blocked 이유가 generic 보류로 축약되는 문제를 발견해 pedal/sequential 양쪽에 그대로 보존했다.

첫 actual r1: exit 0, 243.747초, 27개 전부 처리. 첫 run 이후 blocked sequential bucket의 미정을 nonmember와 명확히 분리하고 미정의 missing-members를 null로 수정했다. r1은 덮어쓰지 않은 **초기 개발 실험**이다. 최종 계약은 r2 기준이며 r1 role record를 최종 schema/replay 입력으로 간주하지 않는다. 원 literal/화성 가정/shape 분모가 유지되는지는 별도 비교한다. r1 manifest의 코드/schema SHA와 초기 필드 해석 제한을 함께 보존한다.

최종 독립 read-only 감사: 부모 입력 172개 + 현재 코드/schema 276개 + 새 artifact 43개 SHA 전부 일치. 27개 seal/source refs 및 원 IR의 실제 sounding span/attack set, episode의 누락·중복 없는 partition, 가정별 member/nonmember/unknown 및 공격음 도수 범위/분산형 조건/집계 대조 통과. r1/r2의 14개 track byte, 27개 literal/scope/pedal profile 및 sequential shape status가 동일하다. 수정 효과는 미정 attack instances 671개의 별도 표현과 blocked missing-members의 null 처리이며 음악 정답률 향상 수치가 아니다. 원 source score의 XML fidelity나 concert pitch를 새로 독립 인증한 것이 아니다.

별도 철자 도수 재계산 4,908개 일치. 메인/로그/로드맵/이 기록의 상대 문서 링크 96개 존재, 새 코드/검사/문서의 replacement character·trailing whitespace 0. `git diff --check` 통과(기존 tracked 파일의 LF→CRLF 경고만 출력). Git stage/commit/push는 하지 않았다. 원자료를 외부 모델에 보내거나 새 생성 기능의 정확도를 평가한 것은 아니다.

```powershell
$env:PYTHONPATH='K:/Music Analysis/src'
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -m musicanote_harness.musical_role_evidence_trial `
  --alignment 'output/musical-semantic-alignment-2026-10-01-r2' `
  --output 'output/musical-role-evidence-2026-10-01-r3'
```

위 r3는 다음 **새** 재실행 디렉터리다. 이미 존재하면 다른 새 rN을 사용한다. trial은 기존 output/상위 입력 안쪽 쓰기·workspace 밖 출력·누락 inventory·hash 변조·scope/ID/분모 불일치를 거부한다. importer 실패 시 literal-only로 보존하며, source/IR/coordinate 문제는 blocked outcome으로 분모를 유지한다.

## 7. 상태 보존과 다음 큰 기능

변경하지 않은 것: 원 XML/MXL/RomanText, Core/schema/production parser, 원 SOURCE/BOUND·과거 실험, 구조 분석·사용자 피드백·rights/split/gold/training, 외부 API 전송, Git, 운영 5173/기존 검토 화면. 이번 연구 근거로 기존 화성/NCT 결과를 교체하지 않았다.

다음 큰 기능은 **지속/분산 구성음 + 조건부 NCT + 여러 화성 진행을 공동 비교하여 역할·반주 슬롯을 설명하는 것**이다. 혼합/다성 raw lane에서 선율/내성/반주 후보를 별도로 보존하고, 원음가/선율·장식이 삭제되지 않게 한다. 원주석 하나만 넣어 정확도를 평가하지 않고 기존 Beethoven/Mozart의 경쟁 진행 문맥과 실제 일반 반례를 연결한다. 이후 검수된 pattern/role/use eligibility → 소규모 피아노 실현/독립 검증 → 전곡 피아노/실내악으로 진행한다.

기존 조성·secondary·기능·종지 및 과병합/과분할의 큰 개발 계획은 유지한다. 새로운 의미 기능의 후보 수가 늘었다고 그 기능을 완료 처리하지 않는다. 사용자에게 해석 선택을 요구해야 하는 실제 competing case가 준비되면 앞뒤 포함 전체 악보와 함께 제시한다.
