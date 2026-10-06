# 원주석 좌표와 재현 가능한 음표 패턴 관찰

기록 ID: **HARM-DEV-20261001-03**. 날짜: 2026-10-01. 정본: [화성 개발 메인](../README.md), [개발 로그](../DEVELOPMENT_LOG.md). G0 [원문 수집](2026-10-01-musical-semantics-and-backfill.md)에 이어 **G1의 첫 부분**을 구현했다. 인수인계 문서가 아니다.

## 1. 목적과 완료 범위

사용자는 화성 이해를 바탕으로 선율·베이스·내성·반주·전개를 배치할 수 있는 작곡/편곡을 원하며, 앞으로 확보한 정보를 이전 사례에도 보충하도록 요청했다. 이번의 개발자 해석은 먼저 원주석과 실제 악보의 음표·음가·타이·성부를 연결해야 한다는 것이다.

이번에는 **명시적 Pedal 좌표 연결 + literal pattern observation**을 구현했다. 원문에 '페달'이라고 쓰인 사실, 그 문장의 시간 구간, 실제 음표 관찰, 화성적 페달 역할의 타당성은 별개다. 역할/분산화음 자동 확정, 화음 상대 음도 템플릿, 반주 realizer, 학습, 운영 뷰어는 구현하지 않았다. G1 전체 완료나 음악 정확도 향상 수치로 집계하지 않는다.

## 2. 규칙과 이론/형식 근거

[RomanText 원 규격 §2.4](https://www.trecento.com/research/Tymoczko_Gotham_Cuthbert_Ariza_RomanText.pdf)에 따르면 Pedal은 시작/종료 위치를 가지며 종료 위치는 제외한다. Form은 section 시작의 표지일 수 있지만 그 자체로 전체 extent를 주지 않는다. Note는 자유 설명이며 음표 단위 분석 레코드가 아니다. [When-in-Rome syntax](https://github.com/MarkGotham/When-in-Rome/blob/master/syntax.md)는 compound meter의 beat grouping 및 Slow/Fast의 차이도 설명한다.

일반 규칙:

1. SOURCE의 원문/물리적 줄/hash는 수정하지 않고 별도 coordinate attempt를 만든다.
2. 첫 구현은 `Pedal: <literal-token> mX bY mZ bW`처럼 양 endpoint의 박자가 명시된 문법만 연결한다. token이 `3`이어도 **좌표**는 연결할 수 있지만 음도/음높이/선택 lane은 결정하지 않는다.
3. 시작/끝의 printed measure가 source meter/score 양쪽에서 유일해야 한다. printed number와 sequential index는 별도로 기록한다.
4. source RomanText에 명시된 박자를 파싱하고 실제 beat partition을 사용한다. 6/8을 무조건 6개의 quarter beat로 읽지 않는다. 양 endpoint 및 내부 마디의 source/score 박자 일치, 정규 마디, 연속 grid를 검사한다.
5. v0.1은 정수 및 유한 이진 fraction beat만 정확 좌표로 처리한다. `.33/.66/.67`을 자동 triplet으로 반올림하지 않는다. `.2` 같은 다른 정확 fraction도 이 초기 정책에서는 **검토 필요**이지 잘못된 음악으로 판정하는 것이 아니다. native fractional convention 지원은 후속이다.
6. missing endpoint beat, 오타, pickup/irregular measure, 비유일 마디, 구간 역전/0길이, meter 미확인은 보류한다. 같은 시작/끝을 다음 음표나 다음 마디까지 늘리지 않는다.
7. 문맥은 endpoint 마디의 앞/뒤 한 마디까지 보존한다. tie/chord group/grace anchor의 closure로 밖의 원음이 필요하면 함께 저장하되 `linked_context_only`다. target을 확대하지 않는다.
8. 모든 part의 note/rest를 보존한다. raw part/voice lane은 semantic melody/bass/inner voice가 아니다. cross-staff display 위치는 원 event에 남는다.
9. original event의 onset/duration/spelling/notation은 불변이다. target overlap만 별도 clipped span으로 기록한다. grace는 point 관찰이며 performed duration이 아니다.
10. source hash/IR content hash/ID/reference/schema/seal과 재계산을 검사한다. 스키마·봉인 통과만으로 독립 XML fidelity나 음악적 정답을 인증하지 않는다.

첫 마디의 time signature가 measure 내부에 있을 때 `getContextByClass()`만 보면 놓치는 구현 문제가 단위 검사에서 발견됐다. 자체 `measure.timeSignature`를 먼저 읽고 문맥을 보도록 수정했다. 기존 production parser나 harmony 계산은 변경하지 않았다.

## 3. 계약과 변경 파일

모두 새 파일이다. 논리 schema는0.1.0이며 literal observation producer는0.1.0, 최종 alignment/trial producer는0.1.1이다. r1의0.1.0 출력은 역사 기록으로 보존했고 최종 실행은r2다.

| 파일 | 기능 |
|---|---|
| [musical_semantic_alignment.py](../../../src/musicanote_harness/musical_semantic_alignment.py) | `prepare_meter_index`, `align_statement`, `validate_alignment`; coordinates only |
| [musical_pattern_observation.py](../../../src/musicanote_harness/musical_pattern_observation.py) | `observe`, `validate_observation`, `reconstruct`; exact original IR event projection |
| [실행기](../../../src/musicanote_harness/musical_semantic_alignment_trial.py) | 전체 Pedal 분모, 고정 입력/코드 SHA, 새 로컬 snapshot/IR/attempt/pattern 저장 |
| [alignment schema](../schemas/musical_semantic_alignment.schema.json) | SOURCE ref, source SHA, endpoint, scope, status/reason, 미검수 정책 |
| [pattern schema](../schemas/musical_pattern_observation.schema.json) | 유리수 slot/target/context, Core catalog/link projection, raw lanes |
| [pattern tests](../../../tests/test_musical_pattern_observation.py) | 12 tests |
| [alignment tests](../../../tests/test_musical_semantic_alignment.py) | 11 tests |
| [runner tests](../../../tests/test_musical_semantic_alignment_trial.py) | 6 tests |

Core 객체는 기존 Core schema URI를 재사용하며 로컬 registry에서 해석한다. 새 해석 필드를 Note에 추가하지 않는다. `reconstruct()`는 event projection의 복사본을 반환하며 **완전한 MusicXML export/새 Canonical IR document가 아니다**. Voice의 전체 event catalog 등 범위 밖 ID는 원문서 참조임을 선언한다. 원 XML/MXL 전체와 전체 IR은 별도 snapshot으로 보존한다.

원 semantic SOURCE를 BOUND harmonic-role 정답으로 바꾸지 않았다. 화성 가정이 없는 상태에서 `build_bound_claim(harmonic_role=pedal)`을 발명하지 않는다. 차기 역할 가설은 해당 화성 assumption/경쟁 후보와 별도 연결해야 한다.

## 4. 실제 입력 선정과 결과

입력: [G0 r3](../../../output/musical-semantic-intake-2026-10-01-r3/report.json)의 완료된 SOURCE 목록. 이 목록의 Pedal 전부를 검사한다. 제목 유사도로 다른 악보를 고르지 않고 같은 디렉터리의 MusicXML을 우선, MXL을 다음으로 선택했다. 모든 과거 코퍼스/기존 322문맥을 이번에 정렬한 것이 아니다.

최종 실행 결과: [r2 report](../../../output/musical-semantic-alignment-2026-10-01-r2/report.json), [선정/입력/코드/환경 manifest](../../../output/musical-semantic-alignment-2026-10-01-r2/run-plan.json), [전체 attempt](../../../output/musical-semantic-alignment-2026-10-01-r2/alignment-attempts.json), [패턴 목록](../../../output/musical-semantic-alignment-2026-10-01-r2/pattern-index.json). [r1 report](../../../output/musical-semantic-alignment-2026-10-01-r1/report.json)는 덮어쓰지 않았다.

| 분모/상태 | 수 |
|---|---:|
| Pedal 원주석 / 원주석 파일 | 208 / 91 |
| sibling XML/MXL 선정 파일 | 29 |
| 전체 IR 생성 파일 / prerequisite 실패 파일 | 25 / 4 |
| exact coordinate / literal observations | 27 / 27 |
| observations가 나온 악보 파일 | 14 |
| 같은 악보·같은 target span 중복 제거 구간 | 25 |
| 선정 가능한 sibling score 없음 | 160주석 / 62파일 |
| 지원하지 않는 명시적 문법 | 15주석 |
| rounded/nonbinary beat 보류 | 1주석 |
| explicit source meter 없음 | 1주석 |
| IR prerequisite 오류 | 4주석 |
| 음악적 역할 검수 / training / gold / generation-ready | 모두 0 |

160 + 15 + 1 + 1 + 4 + 27 = 208. 미연결 주석도 분모에 남는다. 27은 독립 작품 수가 아니다. Chaminade의 동일 시간에 G/D pedal을 함께 기재한 원주석 때문에 같은 geometry를 가진 observation도 별도로 남는다. 14는 악보 파일 수이며 판본/작품 가족별 독립성은 아직 판정하지 않았다.

선정하지 못한 62디렉터리에는 `remote.json` 등이 있다. 베토벤 Op27/1 4악장과 바흐 chorale023도 그 예다. 이는 전체 데이터베이스에 악보가 없다는 뜻이 아니다. 다음에는 명시적 원자료 identity/판본/hash registry로 다른 로컬 위치의 악보를 연결해야 하며 제목만으로 매칭하지 않는다. 이번 actual은 주로 가곡이며 베토벤·모차르트 소나타의 새 semantic 양성을 검증했다는 주장은 하지 않는다. 기존 소나타 harmony 실험은 그대로 유지한다.

## 5. 실제 재현 예

Coleridge-Taylor, *Oh what comes over the Sea*, 원주석 물리적18행:

```text
Pedal: E m5 b1 m5 b3
```

source meter는 **9/8**, 세 큰 박이다. 좌표는 quarter `[18,21)`, 문맥은 `[27/2,27)`다. source의 m3 `b3.67` 주석은 별도로 rounded-beat 보류됐다. 둘을 같은 처리로 강제하지 않았다.

- SOURCE: `mse_72765e6391321680b3806a5d` / SHA `72765e6391321680b3806a5dba70735d84bcd81dbb441e84fb45a09c3806c980`.
- Alignment: `msa_517a6a5ab2303580dc4faa69` / SHA `517a6a5ab2303580dc4faa690334eb8b554dbcefc9342f89cd16fc3eb4114ea9`.
- [Observation](../../../output/musical-semantic-alignment-2026-10-01-r2/cases/631dd204fc18f0b32be641f7/mpo_54e25b10c178c5eadd8a7d69.json): `mpo_54e25b10c178c5eadd8a7d69`; SHA `54e25b10c178c5eadd8a7d69bb342fb91cca4c925840fb5107375d5491607186`.
- [원악보 snapshot](../../../output/musical-semantic-alignment-2026-10-01-r2/cases/631dd204fc18f0b32be641f7/score.musicxml), [전체 IR](../../../output/musical-semantic-alignment-2026-10-01-r2/cases/631dd204fc18f0b32be641f7/canonical-ir.json), [원문 snapshot](../../../output/musical-semantic-alignment-2026-10-01-r2/cases/631dd204fc18f0b32be641f7/analysis.txt).
- target에 걸친12events; 앞뒤 포함41notes/4rests,3tie chains,3raw lanes를 보존했다. 음표 수는 grace point도 포함한 기존 IR event 수다.

관찰 예:

| 원 note ID | onset quarters | original duration | written pitch / tie |
|---|---:|---:|---|
| `note_f01d41296a28` | 18 | 3 | E1 / start |
| `note_773c9564de0f` | 18 | 3 | E2 / start |
| `note_d8a661d6de7f` | 18 | 3/4 | G3 / none |
| `note_42204c855663` | 75/4 | 3/4 | B3 / none |
| `note_b446c6ff9c64` | 39/2 | 3/4 | F#3 / none |
| `note_7b4d681fcc61` | 39/2 | 3/4 | A3 / none |
| `note_8f99ada8ccfb` | 81/4 | 3/4 | D#4 / none |

이로써 지속되는 E 음들과 바뀌는 다른 음군을 다음 화성 가정에서 대조할 수 있다. 지금 E1/E2를 선택된 harmonic pedal이라고 확정하거나 다른 part를 반주/선율로 이름 붙이지 않았다. 원 score의 페달 notation import 경고와 화성적 pedal point는 다른 문제이며 performed pedal timing도 인증하지 않는다.

## 6. 실패/반례와 검증

단위검사 초기 alignment 4fail/2error는 첫 마디 signature 조회 문제였으며 자체 signature 우선으로 수정한 뒤 모두 통과했다. source나 gate를 완화해 통과시키지 않았다. 초기 read-only census의 PowerShell quoting/CP949 출력 오류는 파일을 바꾸지 않았고 이후 here-string/UTF-8 실행으로 해결했다.

실제4파일의 보류:

- Brahms Marienlieder Op22의2/4/5번: `duplicate_core_id:measures`.
- Reichardt *Der Sänger geht*: `event_local_global_mismatch`.

이번에는 해당 Core를 즉석 고치거나 event를 버리지 않았다. 전체 byte snapshots/실패 레코드를 남겼다. 기존 physical-measure revision 설계를 이용하는 제한 교정과 판본 확인은 후속 작업이다.

신규29검사: tie 밖의 attack 보존, exclusive endpoint, fraction overlap/원음가, 모든 part, rest, grace point, source/IR hash, duplicate/dangling ID, original time consistency, 재봉인된 누락·좌표 변조, 역할/학습 승격 금지, output 덮어쓰기 방지, 사전 source/artifact 변경 차단, 실패 분모 보존, 첫 마디 뒤의 박자 선언으로 parser 초기 기본값을 인증하지 않는 반례.

첫 r1은2,450검사67.798초OK / actual178.150초exit0였다. 최종 Python **2,451검사 / 70.290초 / OK**, 실제r2 **172.750초 / exit0**. initial meter guard와 환경 기록을0.1.1에 보강했다. 별도 read-only 대조에서 r2입력122, 코드/schema271, artifact171의 SHA 및 전208statement identity를 확인했다. 원문/score byte snapshots58개 일치. 전27pattern의 fresh alignment/observation 재계산, 원 event dict 일치, 독립 half-open target 계산과 source/alignment/IR/case 계보를 확인했다. r1과r2의모든25전체IR 및27slot/원projection/raw lane/semantics/policy도 동일하며, provenance version/ref/seal만새로기록했다.

projection 누적 instances는 notes2,867 / rests249 / tie chains164 / target events1,883이다. 구간이 겹치므로 고유 음표 수나 음악 정답 수로 쓰지 않는다. 기존 G0 출력/원자료는 수정하지 않았다. Git tracked diff whitespace 검사도 통과했다. 새 소스/문서는 untracked이며 commit/push는 하지 않았다.

## 7. 재실행과 환경

PowerShell, workspace `K:\Music Analysis`:

```powershell
$env:PYTHONPATH = 'K:/Music Analysis/src'
$env:PYTHONIOENCODING = 'utf-8'
.venv/Scripts/python.exe -m musicanote_harness.musical_semantic_alignment_trial --intake output/musical-semantic-intake-2026-10-01-r3 --output output/musical-semantic-alignment-2026-10-01-r3
.venv/Scripts/python.exe -m unittest discover -s tests
```

r3는 아직 사용하지 않은 다음 실행 이름이다. output이 이미 존재하면 runner는 중단하며 이전 결과를 덮어쓰지 않는다. 입출력/코드의 개별 절대 경로와 SHA는 run-plan/report에 있다. 환경은 r2 run-plan에 저장했다: Python3.12.14 / music21 10.5.0 / jsonschema4.26.0 / referencing0.37.0. 외부 라이브러리의 전체 실행 binary hash까지 저장한 것은 아니다.

현재 연구용 validator는 명시된 producer 버전에 묶여 있다. 과거 prototype output은 그대로 보존하지만 운영 승격 전에는 producer별 schema registry/replay 및 migration 정책이 추가로 필요하다. 기존 Canonical Core/G0 source/human annotation의 의미나 버전을 이번에 변경한 것이 아니다.

## 8. 다음 큰 개발 단위

1. `remote.json`/기존 package의 명시적 source identity를 통한 다른 로컬 악보 연결; 기존33package322문맥 sidecar의 실제 backfill은 별도 수행한다.
2. 관찰 가능한 지속·재타격·재등장과 sequential/simultaneous onset을 feature로 만들고, source의 pedal/arpeggio 설명과 **경쟁 화성 가정**을 함께 대조한다.
3. 단순 고음=선율/저음=베이스를 쓰지 않고, 원 성부 연결/지속/반복/리듬/준비·해결을 근거로 typed 역할·texture 후보와 반례를 저장한다.
4. 검토된 범위에서 chord-relative degree/register/beat slot을 만들고, 화음 교체와 종결 변형의 적용 조건을 연결한다. 그 뒤 G2 소규모 피아노 realizer/독립 재파싱·연주성 평가로 넘어간다.

동시에 기존 공통 화성 진행 비교의 조성·secondary·기능·종지 경로는 유지한다. 이번에는 원자료·production Core/parser·정식 schema·화성 판정·구조 분석·5173/8822뷰어·rights/split/gold/학습/API/Git을 바꾸지 않았다. 리뷰 UI에 실제로 표시하는 작업은 pattern/role 가설이 준비된 다음 별도 승격 단계로 기록한다.
