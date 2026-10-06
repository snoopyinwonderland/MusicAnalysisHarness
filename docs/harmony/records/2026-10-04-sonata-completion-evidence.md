# 단계44 — 베토벤 소나타의 성부 가정·해결·전체 진행 전제 대조

## 1. 목적과 현재 위치

단계43 quartet 대조와 **같은 일반 규칙**을 Sonata 문맥에 적용했다. 악곡/마디/정답에 대한 예외 조건을 분석기에 넣지 않았다. 기존 저장 native/role 근거를 읽고 동일 key·화음 구성음·분할 아래 무연결과 연결 가정의 차이를 검토했다. 생산 분석기나 교재 규칙 producer를 새로 계산한 작업은 아니다.

큰 실행 순서의 **3~4번(완전 진행 후보와 조성·기능·종지 근거 연결)**을 검증 중이다. 조건부 지원, 최종 화성 선택, 독립 음악 정확도, 운영 화면 적용을 구별한다. 이번에는 일부 **화음 전환**의 조건이 충족됐지만, 모든 내부 전환이 지지되는 완전 경로는0이다. “지원8”을 완성된8개 진행이나8곡으로 읽지 않는다.

## 2. 구현과 안전한 읽기/저장 계약

- [새 staged 실행기](../../../src/musicanote_harness/staged_completion_evidence_trial.py), [검사](../../../tests/test_staged_completion_evidence_trial.py), [실제 실행](../../../tmp/staged_sonata_evidence_pilot_20261004.py), [진단 사례 보존](../../../tmp/staged_sonata_diagnostics_20261004.py)을 추가했다. 기존 단계42/43, native/role producer·parser 코드는 그대로다.
- 외부 receipt SHA→등록 original index/record→scope 별도 caller SHA→양쪽 동일 plan/selector inventory→전체 batch/terminal 집계→같은 원음 전제의 contrast를 확인한다. 내부 seal만으로 source 권한을 복구하지 않는다.
- 원 selector 순서와 모든 후보를 보존한다. 긍정 결과 prefix, 특정 key만의 사후 선택, 독립 completion의 유리한 부분 합치기, None→False/0, 설명량 기반 winner/confidence는 없다.
- Bootstrap, control 검토, linked 검토, paired 대조의 **4개 명시 읽기 계정**을 둔다. 각 계정의 decoded 총량은1GiB 이하이며 단계 내부에서는 초기화하지 않는다. 전체 pipeline이 단일1GiB에 들어갔다고 주장하지 않는다.
- 일반 decoded 파일64MiB, source 전용256MiB 제한을 구별한다. 실제 lattice는103,401,361 decoded bytes여서 명시 source 전용 읽기를 사용했다. Gzip footer 길이는 보조 기대치일 뿐이며 실제 guarded 해제 길이·누적 비용·물리 SHA와 JSON duplicate/nonfinite 검사로 확인한다.
- 새 저장 계약은 무손실 gzip JSON이다. 일반 artifact의 decoded 크기64MiB/source256MiB와 **전체 물리 출력256MiB**를 별도로 제한한다. 총 decoded 출력463,574,590B를256MiB 이하라고 주장하지 않는다. 기존 JSON writer의 한도 의미/상수는 변경하지 않았다.
- 한도/참조/순서 실패 시 전체 완료 report를 만들지 않는다. 이미 생성된 진단 artifact는 실패 흔적으로 남을 수 있으나 성공 prefix로 승격하지 않는다. 기존 output은 덮어쓰지 않는다.
- 단계별 종료 뒤에도 이전 단계의 입력을 **전체 terminal 직전 다시 SHA 확인**한다. 새 snapshot은 읽기 전용 검토 자료이지 live native capability나 검수된 성부가 아니다.

## 3. 실제 원자료 범위와 분모

원 source0 `dcml:beethoven-sonatas:01-1`의 `[49,61)` quarter, **printed m.13~15**,2/2박자다. m.0의1quarter pickup 때문에 m.13 시작은49이다. printed 번호와 sequential index는 원 IR대로 유지했다. 원 source의 표기 시작음·쉼표·타이와 전후 참조를 저장했고 XML 재파싱/수정은 하지 않았다.

| 항목 | 실제 범위 |
|---|---:|
| 악장 / 문맥 | 1악장 / 1문맥 |
| Raw lanes / sounding facts | 3 / 23 |
| 한 completion의 후보 / batches | 2,315 / 145 |
| 비교한 completion | 무연결 control + linked technical probe |
| 원 native/role 경로 발생 | 4,630 (2,315×2) |
| 같은 전제의 쌍 | 2,315 |
| Key 가정별 후보 | A♭major / F natural minor / F harmonic minor / F melodic minor ascending / unknown 각463 |

Linked의18edge는 raw lane별 **상성부12 + 다른 lane4 + 별도 voice2**다. 표기 raw voice 내 greedy 연결이며 음악적 성부 검수/추론 완료가 아니다. 무연결에는 edge0이다.

전체 역사 archive의4completion/8,050selector 발생 중 이번2completion/4,630을 검토했다. 단계43의 quartet2completion/3,420과 합하면 두 등록 문맥의 양쪽 가정은 대조됐지만, 전체 작품군·전악장·모든 경쟁 후보 간 비교 완료가 아니다. 기존 경쟁 비교 저장은 quartet의291,555pair 요청 범위이며 Sonata의 모든 경쟁 pair는 이번에 계산하지 않았다.

Source scope `fmes_f676809634ab4fb9acf34b03`, fresh lattice `fmilat_a5daac1f9d08a81d4995b0b2`, 같은 plan `npsreplayplan_85f6b9c37a449e5a4b41b921`을 참조한다. Control bundle은 `fmilbundle_32b745ced2a06ef628660a12`, linked는 `fmilbundle_c637f032bcb0e8fed00fc3b3`이다. 원 source labels를 정답 선택/학습에 사용하지 않았다.

## 4. 결과 — 설명량과 음악적 지원은 별개

| 비교 항목 | 결과 |
|---|---:|
| 조건부 NCT 설명 증가 / 동일 / 감소 | 1,870 / 445 / 0 후보 |
| 원음표 credit 변화 span 발생 | 3,225 |
| 변화에 등장하는 고유 sounding event | 7 |
| Ordinary whole template False→True | 20 전환 발생 |
| Joint False→True | 8 전환 발생 |
| Joint False→Unknown | 2 전환 발생 |
| Joint False→False / Unknown→Unknown | 360 / 2,780 전환 발생 |
| 모든 내부 전환 Joint=True인 경로 | 0 |

Whole 지원20 중8은 해당 전환의 key/shape/구성음/등록 연결 조건이 함께 충족된다.2는 key가unknown이라 joint도unknown이고,10은 목표 화음에 필요한 구성음이 없어 joint=false다. 따라서 ordinary 해결20을 화성 정답20으로 바꾸지 않는다. 구성음·해결 조건의 실패 축은 겹칠 수 있으며 합산 정확도가 아니다.

변경 고유 sound는 C5(3개), B4, E♭4, B♭4, D♭5다. 모든2,315후보에는 미해결 note-time이 남았다. Missing 구성음 보류1,820, pooled 제시 보류1,790, unknown key463, nominal cadence 의미 전제 보류77 등의 수치는 **후보/구간 가정의 발생 수**이며 서로 중복되고 작품 수가 아니다.

무연결 control도305후보에서 intrinsic carry 설명을 갖는다. 원 sum은1,260quarter-note-time selector 발생이고 linked는16,915/6, 차이는9,355/6이다. 다성/후보 중복 합계이므로 악보의12quarter 길이, 고유 음표 수, 확률 또는 향상률이 아니다. “무연결이면 모든 설명0”으로 가정하지 않는다.

## 5. 원음표로 보존한 음악적 사례

[진단 사례 JSON](../../../output/staged-sonata-diagnostics-2026-10-04-r1/diagnostic-cases.json)에6개 주소의 source scope, 원음표/쉼표/음가/타이·source refs, 양쪽 review/contrast, intrinsic 원 role clauses를 보존했다. **2,315개 전수 대조 후의 설명 사례**이며 새 평가 subset이나 gold label이 아니다. 악곡 ID/selector 번호는 사례 주소일 뿐 알고리즘 조건으로 쓰지 않는다.

### A. 이끎음 해결은 지원되지만 완전 진행은 미확정 — selector1266,1281

13마디 G4 `sound_c06632d0913f` / `note_409df3e18079` `[49,53)`에서14마디 A♭4 `sound_7828a96022b7` / `note_f609dc1060e3` `[53,57)`로 가는 실제 등록 edge가 있다. 음높이·음가·베이스는 control과 같다.

1266의 G–B♭–D♭→A♭–C–E♭ 형태에는 vii→major 가정,1281의 E♭–G–B♭→A♭–C–E♭에는 V→major 가정이 있다. F natural minor 전제에서는 목표가3도라 applied 형태로 표시되지만, target coordinate는 **가정 안의 좌표**다. A♭major 등 다른 key 가정도 남아 있어 실제 Secondary나 조성을 확정하지 않는다.

위 edge의 G→A♭ ordinary leading-tone 조건은 충족돼 joint=true다. 그러나15마디와의 다음 전환은None/undeclared이고 unresolved note-time도 남는다(1266은19/3,1281은6). 후보3화음의 양성만 보고 m.13의 D♭ 등을 지워3화음으로 확정하면 안 된다.15마디 wide pool도 독립 temporal 검토 대상이다.

### B. 같은 G→A♭이어도7음의 연결 부족을 숨기지 않음 — selector1201

E♭–G–B♭–D♭→A♭–C–E♭, V7→major 가정에서는 이끎음 G4→A♭4는 true지만 seventh 역할은 false다. 검사한 D♭5는13마디 마지막 재타격 `sound_d3a0706d2872` / `note_2edca1a44074` `[52,53)`다. 현재 technical witness에는 이 sound의 outgoing edge가 없으며 `first_changed_endpoint_not_linked_in_this_complete_witness`로 보류된다.

14마디의 D♭5 `sound_84691b622f05` `[109/2,164/3)`→C5 `sound_b4d0e1d7b1cc` `[164/3,329/6)` edge는 따로 존재한다. 하지만 중간 쉼/끊긴 source route를 건너뛰어13마디7음의 해결 근거로 가져오지 않는다. 결과는 **이 complete witness의 ordinary7음 template가 미충족**이라는 뜻이지, 음악적으로 V7 해석이 틀렸다거나 D♭이 해결 불가능하다는 뜻이 아니다.

후속은 일반적인 쉼을 낀 재등장·지연/장식된 해결 전략을 별도 전제로 표현하고, 실제 route와 화음 지속/변화·반례를 검증하는 일이다. 기존 ordinary 판정을 완화하거나 이 악보의 edge를 정답으로 강제하지 않는다. 3화음의 성공이7화음 누락을 자동 정당화해서도 안 된다.

### C. 해결이 있어도 미관측 구성음을 채우지 않음 — selector1716

1266과 같은 G4→A♭4 연결이 있고 whole template=true지만 목표를 A♭–C–E♭–G♭으로 놓으면14마디 G♭ 근거가 없다. `guarded_pooled_literal_core_present=false`, joint=false를 유지한다. NCT 설명 증가가 missing G♭을 만들어 주지 않는다.

### D. 해결이 있어도unknown key는unknown — selector1268

1266과 같은 음/형태/ordinary 해결이지만 key 전제가unknown이다. Whole=true, `known_explicit_key_coordinate=None`, joint=None다. 무연결의false가 연결 후unknown으로 바뀌는 것은 다른 전제가 드러난 것이지 조성 추론 성공이 아니다.

### E. 무연결에도 동일 sound 지속의 설명은 가능 — selector345

가정된 경계55를 A♭3 `sound_84351d133d6c`와 A♭4 `sound_7828a96022b7`의 `[53,57)` sounding duration이 통과한다. 원 control role clauses는 양쪽에 `boundary_anticipation`, `carry_kind=held`, `actual_required_links=[]`를 남긴다. `[53,55)`의2+2quarter credit은 새 성부 self-link 없이 생긴 intrinsic carry다.

이는 가정된 후보/경계 아래의 조건부 해석이며 실제 anticipation 확정이 아니다. Linked는 D♭5의1/6quarter 설명을 더해25/6이지만, 설명량이 큰 후보를 정답으로 선택하지 않는다. 실제 tie chain 보존과 단순 sustained sound의 intrinsic carry도 구별한다.

## 6. 검사·실행·보존

- 최종 신규 **14검사/5.779초 PASS**, 기존 core/review/reader/runner 회귀 **56검사/58.940초 PASS**다. Genuine 작은 XML/native body·물리 gzip 검사를 사용하되 상위 receipt ancestry는 합성 fixture임을 명시했다. Native/role producer 호출을 막고 실행 성공, source pin, 모든 원 위치, 누락·한도·덮어쓰기·단계 후 변조를 확인했다.
- 최초10검사에서1 ERROR는 test의 잘못된 summary 필드명,1차 수정도 다른 잘못된 필드명이었다. 실제 결과의 `raw_time_conserved_native_paths`를 검사하도록 교정했고 최종14개를 통과했다. 음악 판단 gate는 완화하지 않았다. 중간 실행을 고유 검사 수에 중복 합산하지 않는다.
- 실제 전수 실행 **281.7621838초/exit0**. 출력 **437파일/41,895,618B**. Bootstrap108,821,014 / control739,694,376 / linked882,269,347 / paired324,878,450 decoded bytes; 합계 **2,055,663,187B**다. 각 단계1GiB 이하, aggregate는 단일1GiB 초과임을 명시한다. 메모리 peak는 이번에 측정하지 않았다.
- 실제 report SHA `ae546c207fa46e87e0cdd7c8e6cfca177862c600b798230fa1c18463f81f14c2`. [전수 report](../../../output/staged-sonata-evidence-2026-10-04-r1/report.json). 원입력589와 신규 output437의 고유1,026파일 길이/SHA·전체 목록을 사후 대조했고 오류0이다. Report의 terminal guarded input880에는 앞 단계에서 만든 snapshot도 포함된다.
- 독립 저장 산술 점검에서2,315원 위치, 각 key463, 동일 raw음/partition/slots, 양쪽6category 음가 보존, credit signed span 합계, tri-state 전환과 cadence confirmed=false를 전수 확인했다. 실행기 재실행이나 독립 음악 정답률 평가가 아니다.
- 별도 사례 저장2파일/1,552,616B, guarded read18,670,202decoded bytes/exit0. 사례 SHA `2908a25356721ecc0c99bf3bb0fec617c14e821ca03dbc07246b8943febad7e8`, [사례 저장 report](../../../output/staged-sonata-diagnostics-2026-10-04-r1/report.json) SHA `2e5d95eeb6734ba695931d8316d937ae46886fdae2ed97af8dfa62d9c6295c70`.
- 원 XML/Core/주석, 선행75 source/test/runner SHA, 별개 tracked5수정·기존출력·운영 UI/서버·Git 설정은 보존한다. Commit/push, 새 API 호출, 자동 학습/Gold 승격은 없다.
- 최종 QA에서 선행75SHA 변경0, 신규4파일 AST·개발3문서 strict UTF-8·로컬 링크197개 오류0, `git diff --check` exit0을 확인했다. 기존 tracked5의 LF→CRLF 경고는 별개이며 해당 변경을 수정하지 않았다.

## 7. 다음 큰 기능 단위

이 결과에서 “연결이 많으면 좋다”는 규칙을 추가하지 않는다. 다음은 **완전 진행에서 경쟁3/7화음·key·음표 역할·화음 경계 전제를 공동으로 판단하는 음악 정책**이다. 먼저 아래 병목을 같은 계약으로 다룬다.

1. 지원된 한 전환과 전체 경로를 구별하고, undeclared 구간은 성공으로 채우지 않는다.
2. 일부 leading-tone 지원으로 seventh 후보를 탈락시키지 않는다. 쉼을 낀 지연/재등장 해결은 명시 전략의 실제 route와 부정 사례를 함께 검증한다.
3. 구성음 누락, 미해결음, pooled temporal 제시, 구조 베이스/조성 불확실성을 독립 축으로 비교한다. 겹치는 근거를 투표로 중복 합산하지 않는다.
4. 기존 양성/반례를 frozen 회귀로 보존하고 다른 작품·편성에서 독립 검증한 후, 같은 원음표를 참조하는 악보 layer/피드백에 연결한다.

남은 큰 묶음은 **최종 화성/종지 판단 → 여러 작품·편성 독립 검증 → 악보와 사례 피드백 → 구조·작곡·편곡 연결**이다. 이번 구현은 음악적 병목을 구체화했지만 안정된 자동 화성 분석이나 편곡 생성 완성을 뜻하지 않는다. 사용자 의견이 필요한 해석 충돌은 실제 악보와 전후 문맥을 함께 준비해 요청한다.
