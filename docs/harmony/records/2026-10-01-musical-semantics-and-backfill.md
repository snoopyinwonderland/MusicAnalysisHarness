# HARM-DEV-20261001-02 — 음악적 의미 원문·선택적 계약·기존 사례 보충 기반

날짜: 2026-10-01 (Asia/Seoul). 정본: [화성 개발 메인 문서](../README.md). 목표와 생성 완료 기준: [음악적 의미·배치·전개 로드맵](../MUSICAL_SEMANTICS_AND_GENERATION_ROADMAP.md). 직전 화성 계산: [완전 진행 탐색·동일 성부 공동 비교](2026-10-01-progression-search-and-joint-comparison.md).

## 1. 요청과 이번 완료 범위

사용자는 화성 분석만이 아니라 음표·음군·모티프의 역할, 앞뒤 배치와 전개를 보존하여 작곡/편곡에 이용하고, 새 정보가 충분해지면 이전 사례에도 보충하도록 요청했다. 최소 지향 범위는 단선율→복잡한 전곡 피아노 솔로 및 듀엣·트리오·쿼텟, 상위 목표는 관현악과 장형식 스타일 작곡이다. '인공 지능 모차르트'는 장기 지향이며 현재 성능 명칭이 아니다.

이번에는 **G0: 선택적 의미 sidecar + 원문 수입 + 축별 보충 대기열**을 구현했다. 원문을 실제 음표에 정렬하거나 역할을 자동 확정한 G1, 반주 실현/생성 G2–G6, 화면 적용은 아직 아니다. 현행 화성 단계의 조성·적용화음·기능·종지 및 경계 선택 순서를 유지한다. 사용자 목표를 8마디 반주나 화음 기호 표시로 축소하지 않는다.

## 2. 계약과 일반 규칙

새 schema는 `musicanote-musical-semantic-enrichment` **0.1.0**, 어휘 **0.1.0**이다. Canonical Core나 현행 정식 Analysis schema를 변경하지 않는 별도 연구용 계약이다.

| 축 | 저장 가능한 실마리 | 현재 실제 수입 상태 |
|---|---|---|
| `voice_role` | 선율/베이스/반주/내성/대선율/응답/중복 | 원문에 있어도 자동 확정하지 않음 |
| `harmonic_role` | 화음 구성음/근음·3·5·7음/NCT/페달 | `Pedal` 원태그만 축에 routing; 용어·대상 미확정 |
| `texture` | 분산/블록/알베르티/오스티나토/다성 등 | 원문 보존; 재현 패턴 슬롯은 후속 |
| `motif` | 등장/변형/core/완결 범위 | 원문 보존; 대응표 추출은 후속 |
| `form_role` | 시작/지속/전환/종결/대조/복귀 | `Form` 원태그만 routing; 구간 미정렬 |
| `development` | 반복/시퀀스/확대·축소/전위/분절/변형 | 구조화 해석 대기 |
| `placement` | 앞/뒤/중첩/교대/전경·배경/음역 관계 | typed 관계 인터페이스, 자동 계획 아님 |
| `performance` | articulation/dynamics/호흡/타이밍/장식 | 기보와 연주 해석을 분리하는 후속 축 |

- `SOURCE`: 원문·위치·출처 revision/hash, null target, `needs_alignment`. `Note`는 축/term 모두 null이며 편집 메모도 포함한다. 원작자 설명을 새 사람 검수로 승격하지 않는다.
- `BOUND`: source claim을 immutable ID/hash로 참조하는 별도 원자적 주장. score/IR hash·rational `[start,end)`·event refs·alignment ref를 요구한다. 화성적 역할은 해당 harmony assumption ref를 필수로 갖는다. source는 그대로 남는다.
- 같은 tie/sounding event도 화음이 바뀌면 별도 span의 역할을 가질 수 있다. Canonical의 기보 `chord_member`와 `chord_tone`을 혼동하지 않는다. 피아노 sustain pedal과 화성적 pedal point도 다르다.
- 관계는 `before/after/overlaps/alternates/repeats/transforms/develops/accompanies` 등의 등록된 종류를 사용한다. 같은 case/IR/harmony 가정을 유지하고 시간 관계는 rational span으로 검사한다. 일반 텍스트만으로 위치·역할·인과를 확정하지 않는다.
- 가설과 human review는 분리한다. 수치 없는 원문 confidence는 null이며 수치가 있으면 의미를 선언한다. producer/version/config/model/schema ref를 보존한다. 검수자·사용 정책 참조는 선언이지 인증이나 권리 판정이 아니다.
- JSONL은 append-only/single-writer prototype이다. 동일 retry는 중복을 만들지 않는다. revision은 현 계보 tip을 `supersedes`; 대상/판본/축을 바꾸는 재타기팅은 새 계보다. 동시 쓰기 잠금·운영 DB는 미구현이다.
- 전체 `covered`는 독립 등록된 정확 span와 event inventory 및 검수를 요구한다. 단일 음표+전곡 span이나 서로 다른 화성 가정의 합집합으로 전체 완료를 만들지 않는다. descriptor의 container/type/hash/축/중복/membership도 검사한다.

## 3. 실제 원문 수입 결과

실행 입력은 `K:/MusicSearch/data/classical-corpora/when-in-rome/Corpus/**/analysis.txt` 전부다. 다른 코퍼스의 TSV/JAMS/score note 원문을 이번 새 수입으로 전부 처리했다고 주장하지 않는다. 이전 화성 등록/계산은 그대로 보존한다.

최종 출력: [musical-semantic-intake-2026-10-01-r3](../../../output/musical-semantic-intake-2026-10-01-r3/report.json), 실제 **49.659초, exit 0**, complete/input-and-code/artifact unchanged 모두 true.

| 항목 | 실제 수치와 분모 |
|---|---|
| 수입 대상 | `analysis.txt` 1,293개; 문장이 있는 파일 744개 |
| 설명 `Note` | 2,816개 physical line, 715개 파일 |
| 형식 `Form` | 1,705개 physical line, 234개 파일 |
| 페달 `Pedal` | 208개 physical line, 91개 파일 |
| 총 source statements | 4,729개; 편집/서지 설명·중복 포함, 검증된 음악 해석 수 아님 |
| 전체 원파일 보존 | byte-identical snapshot 1,293개, 짧은 deterministic hash 경로+원경로 mapping |
| 실제 정렬/사람 검수/학습·gold 적격 | 모두 0; 외부 API 호출·키워드 음악 분류도 0 |

태그는 대소문자를 구별하지 않고 읽되 원 spelling/raw value/physical line/원래 줄바꿈/BOM을 보존한다. 주변 기본 ±2줄과 가장 가까운 앞뒤 `m` 줄을 저장한다. `context_is_target=false`; 앞의 마디를 무조건 target으로 삼지 않는다. multiline 설명은 전체 byte snapshot에서 후속 확인한다. `Form`/`Pedal` tag routing은 주석 태그 관찰이며 분석 검증이 아니다.

원문에 악보 표현과 관련된 실마리가 실제로 있다. 다음은 **주석자가 쓴 내용의 요약**이지 엔진이 판단한 정답이 아니다.

| 원자료/physical line | 원주석의 실마리 | 최종 SOURCE ID | 현재 상태 |
|---|---|---|---|
| Beethoven `Piano_Sonatas/Beethoven,_Ludwig_van/Op027_No1/4/analysis.txt`:14 | 고정 B♭ 페달 위 bass/soprano의 병행10도와 9화음 분산 | `mse_2f0e6337c34077a195f677a6` | 원문+주변 문맥 보존; texture/voice/실제 target 미분류 |
| Bach `Early_Choral/Bach,_Johann_Sebastian/Chorales/008/analysis.txt`:12 | m2 b2.5의 선행음+경과음과 soprano/alto 관계; 다른 마디 반복도 언급 | `mse_9af8852e857f82cb628d3e39` | 원문 보존; 음표 대응/반복 구간/NCT 검수 대기 |

한 문장이 여러 축의 후보를 제공할 수 있지만 원문 SOURCE는 복제 해석하지 않는다. 정렬 뒤 각 축에 별도 BOUND를 연결한다. 이 설명을 곧바로 accompaniment 실현 지시나 학습 라벨로 사용하는 경로는 아직 없다.

## 4. 이전 사례 보충과 보존

이번 등록 대상은 고정된 `harmony-context-integration-trial-2026-09-30-r1/report.json`의 **19개 작품 가족/33개 악보·악장 package/322개 문맥**이다. 전체 과거 사례 라이브러리나 코퍼스 전곡을 backfill 완료한 것이 아니다.

- source 파일 사례 1,293개와 legacy 문맥 322개의 coverage 분모를 따로 둔다. 1,615개를 독립 작품 수로 합산하지 않는다.
- legacy identity는 pair/plan index/sample/artifact hash를 사용하며 기존 status·IR document ID와 출처 policy/split metadata를 보존한다. hash 검증한 frozen parent manifest의 정보는 새 사용 허가가 아니다.
- 원주석과 raw 음표/NCT/화성 근거를 지우지 않는다. `legacy_musical_data_absent=false`; 새 8축의 `not_assessed`는 새 sidecar가 없다는 뜻이다.
- bundle gzip payload는 이번에 다시 decode/hash 계산하지 않았다. metadata/report manifest의 artifact hash는 inherited로 기록한다. bundle hash를 실제 IR hash라고 발명하지 않으며 `ir_sha256=null`이므로 지금 bound target으로 승격할 수 없다.
- 이후 정확 source/IR/hash/event inventory와 span을 등록하고 SOURCE→BOUND→검수→목적별 적격성 단계로 보충한다. 기존 파일을 덮어쓰지 않고 새 revision/sidecar를 추가한다.
- source Form 234개 파일과 Pedal 91개 파일은 해당 축 `needs_alignment`; 나머지 축은 `not_assessed`. 모두 전체 `covered`가 아니며 322 legacy 문맥도 모든 축 미평가다. 이를 역할 부재로 해석하지 않는다.

## 5. 실패·반례·정정과 독립 검사

1. 최초 테스트는 패키지가 editable install되지 않아 import 실패했다. 명시적 `PYTHONPATH=K:/Music Analysis/src`로 재현 환경을 맞췄으며 음악 규칙은 변경하지 않았다.
2. r1: 수집 4,724문장 후 긴 Windows 경로의 스냅샷 쓰기에서 `FileNotFoundError`, exit1. 미완료 디렉터리는 보존했고 report가 없으므로 완료로 세지 않는다. 원자료 수정/삭제는 없었다. 짧은 `<24hex>.txt` 저장과 original path mapping으로 보완했다.
3. 초반 shell의 4,734줄 집계는 rg 표시 줄을 physical statement와 혼동한 값이었다. 독립 CR/LF 순회에서 정식 대문자 4,724개, 소문자 `note:` 5개를 확인했다. 이 5개를 원표기 보존해 포함한 실제 수치는 4,729다. Capitalization을 음악적 의미의 증거로 사용한 것이 아니다.
4. r2: 4,729개/1,293개 파일, exit0/47.346초. 저장/경로 문제는 해결됐으나 SOURCE default producer가 계약 버전0.1.0을 사용한 한계가 있었다. 기존 r2를 수정하지 않고 actual intake version과 deterministic declared config hash를 별도로 전달하는0.1.2를 r3에서 실행했다. config에는 tag routing/case/physical line/raw value/문맥 radius/미정렬 정책을 선언한다.
5. 계약 반례: 한 음표로 전곡 coverage 자기 인증, stale IR/source/hash, 서로 다른 harmony 가정 합치기, 잘못된 chronology, mapping/string이 event inventory로 읽히는 문제, 불완전 typed source ref, forward/tampered/supersedes ref를 차단한다. 권리·검수 인증 자체를 수행했다는 뜻은 아니다.
6. 독립 auditor는 intake parser를 재사용하지 않고 physical CR/LF 원문을 순회한다. Unicode 문장 separator를 새 physical line으로 세지 않는다. 실제 위치/raw value/spelling/줄바꿈/원본문맥 및 nearest measure를 비교하고 source·legacy denominator와 정확한 artifact inventory, producer version/config/schema를 대조한다.
7. adversarial audit에서는 hash manifest를 새로 맞추더라도 누락 artifact hash entry, 중복 snapshot mapping, 재봉인된 옛 producer, 재봉인된 빈 주변문맥과 과장 집계를 허용하지 않는다.

실제 [독립 감사](../../../output/musical-semantic-intake-2026-10-01-r3/audit.json): **passed true**. source input1,293/legacy metadata3/implementation4 hashes와 produced artifact1,301개(전체 snapshot1,293+JSON/JSONL8)의 accounting 일치. 원문4,729개와 소문자5개의 위치·내용, source-case 및 legacy322 identity/status/원 IR ID·미검토 상태 일치. 실제 음악 정확도·음표 정렬·bundle 재계산 인증은 아니다.

테스트: 신규 **79개**(contract41, intake/trial27, independent audit8, workflow3). 전체 Python 결과는 아래 최종 검증 행에 기록한다. synthetic fixture는 저장/계약 반례이며 음악 gold가 아니다. 경고가 있는 기존 Verovio encoded-break fixture는 음악 정답 검증으로 사용하지 않는다.

## 6. 변경 파일과 저장 결과

코드/계약:

- `src/musicanote_harness/musical_semantic_enrichment.py` — builder/validator/JSONL append/retry/axis coverage,0.1.0.
- `src/musicanote_harness/musical_semantic_intake.py` — case-insensitive native source 문장/문맥/provenance 수입,0.1.2.
- `src/musicanote_harness/musical_semantic_intake_trial.py` — 전체 source+legacy metadata의 새 local-only 고정 실행,0.1.2.
- `src/musicanote_harness/musical_semantic_intake_audit.py` — 독립 원문·hash·accounting 감사,0.1.0.
- `docs/harmony/schemas/musical_semantic_enrichment.schema.json` — 별도 Draft2020-12 schema,0.1.0.
- `tests/test_musical_semantic_{enrichment,intake,intake_trial,intake_audit,workflow}.py` — 위 5개 테스트 파일.

문서: `docs/harmony/MUSICAL_SEMANTICS_AND_GENERATION_ROADMAP.md`, 본 기록, 메인 README/DEVELOPMENT_LOG 및 기존 통합 계획·DOCUMENT_MAP의 정본 연결. 인수인계 문서에 새 상세 기록을 누적하지 않았다.

결과 폴더는 `output/musical-semantic-intake-2026-10-01-r3/`. `run-plan.json`, source inventory/case descriptors/coverage, legacy descriptors/coverage, provenance snapshot, `source-statements.jsonl`, flat `source-snapshot/`, `report.json`, 후속 `audit.json`을 보존한다. 재실행 때 기존 폴더는 덮어쓸 수 없다. 원자료 복사본은 로컬 연구 결과이며 공개/GitHub 업로드 승인은 아니다.

immutable refs:

| 객체 | SHA-256 |
|---|---|
| 최종 report | `b37fba1113e3bf6a9ba7486e069740e358d236f0612a9112abce558c09b1e628` |
| 최종 run plan | `4640512546ce6d7ee5b16bcd11d5794259a7d7da5f89c532829fbc2b494d8cc7` |
| intake config | `718e7b0aea8be92faba1d6067c051f6499a21ceecb622426d8c68009be7eaecc` |
| 기존 context report | `22ff64ceb522cfde5039d07dc28935179e8c12add14ed52aaa0295f90e1bcebe` |
| 독립 audit 코드 | `dd124cc8579a545b3a75c62fc8577cc411366dbafa8b330a19f5e0390ac76067` |

코드4개/source1,293/metadata3과 각 결과의 전체 hash 목록은 run plan/report에 보존한다. auditor는 후속 읽기 전용 검사이며 audit.json의 hash inventory는 trial report의 사전 출력1,301개에 소급 삽입하지 않는다.

## 7. 재현 명령

PowerShell, repo cwd. 패키지는 현재 editable install이 아니므로 명시적 PYTHONPATH를 사용한다. 복제 재실행은 반드시 새로운 output 이름을 선택한다.

```powershell
$env:PYTHONPATH = 'K:/Music Analysis/src'
.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_musical_semantic*.py'
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -m musicanote_harness.musical_semantic_intake_trial --corpus-root 'K:/MusicSearch/data/classical-corpora/when-in-rome/Corpus' --legacy-report 'output/harmony-context-integration-trial-2026-09-30-r1/report.json' --output 'output/musical-semantic-intake-2026-10-01-r4'
.venv/Scripts/python.exe -m musicanote_harness.musical_semantic_intake_audit --trial 'output/musical-semantic-intake-2026-10-01-r4' --output 'output/musical-semantic-intake-2026-10-01-r4/audit.json'
```

`--output` audit는 신규 파일 exclusive creation이다. 원자료/기존 결과/코드 hash가 바뀌었다면 과거 run의 성공 플래그로 현재 입력을 인증하지 않고 실패한다.

## 8. 남은 큰 단계와 금지된 완료 주장

- 실제 score/판본/IR에 원문 위치를 연결하고, 역할·질감·전개 해석을 별도 BOUND로 만들기. 모든 자유문을 사전 없는 keyword label로 만들지 않는다.
- 재현 Pattern schema: 선율·bass·내성 lane의 rational onset/duration, 박자 상대 슬롯, chord-relative degree/register, 준비·종결 변형, 음역·손/악기 연주성, 사용 범위와 반례. 분산화음이라는 문자열만으로 생성할 수 없다.
- legacy 범위를 전체 등록 라이브러리로 확대하되 immutable IR/event inventory를 확보하고 split/rights와 중복 작품을 유지하기.
- current harmony search 뒤 조성·secondary/function/cadence와 여러 경쟁 해석을 연결하기. 새 의미 레이어는 이 경로를 대체하지 않는다.
- G2 작은 실현 검증→G3 전곡 피아노→G4 실내악→G5 관현악→G6 장형식 스타일 작곡의 완료 기준은 로드맵을 따른다. 총보 파일 출력, 악기 수나 음표 수 증가 자체는 음악성을 입증하지 않는다.

현행 `core.arrangement_plan`의 phrase-level 텍스트 계획을 삭제하지 않았다. 이번 새 계약은 그 텍스트 계획을 note-level realizer로 바꾼 것이 아니다. IR parser/정식 schema/원 XML·주석/현재 화성 계산/정책·rights·split·gold·training/외부 API/Git/운영5173·8822 및 구조 분석은 이번 작업에서 변경하지 않았다. 수입 source와 metadata/계약 hash 검사는 지정 파일 범위이며 모든 filesystem·권리·음악성에 대한 인증이 아니다.

최종 검증: 신규79개3.053초 및 전체Python **2,422개/64.492초, OK**. 독립 실제 수입 감사 exit0/passed true. 관련6개 문서의 local links 누락0, 신규/이번 관리14개 파일의 trailing whitespace0, `git diff --check` exit0. Git의 기존 LF→CRLF 안내는 보존했고 commit/push는 하지 않았다.
