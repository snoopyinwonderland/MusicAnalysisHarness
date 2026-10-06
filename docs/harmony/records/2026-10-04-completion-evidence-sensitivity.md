# 단계43 — 같은 음악·다른 성부 연결의 근거 민감도 검토

착수/종료: 2026-10-04. 단계42의 무연결 control과 **동일한 원음표·화음 후보·조성 가정·분할·기능 선언**을 가진 실제 저장된 linked completion을 전부 대조했다. 새 성부 추론이나 화성 정답 선택은 아니다.

## 1. 목적과 이번에 확정한 일반 규칙

음표 연결을 주면 비화성음과 해결 관계의 설명이 얼마나 달라지는지, 그 변화가 화성 판단에 필요한 다른 근거까지 충족하는지 구별한다.

1. 성부 연결만 대조할 때 원음표·타이·음가·조성 좌표·화음 구성음·화음 경계·기능 선언은 같아야 한다. 배열 순번만 같다고 다른 화음끼리 비교하지 않는다.
2. 연결 가정마다 조건부 NCT 음가와 음표 ID를 따로 보존한다. 여러 성부 가정의 유리한 설명을 합쳐 하나의 결과로 만들지 않는다.
3. 늘어난 설명은 근거 후보이지 정답률·확률·승자 점수가 아니다. 구성음이 빠진 화음, 지나치게 넓은 pitch pool, 미확정 조성, 기능·종지 전제의 부족은 그대로 남긴다.
4. 첫 변경 endpoint의 연결이 없거나 불리하면 뒤의 유리한 해결음으로 건너뛰지 않는다. 이 검토는 기존에 계산된 같은 completion의 역할 판정을 보존한다.
5. `complete_all_lane_witness`는 모든 raw lane의 연결/무연결 가정이 선언됐다는 뜻이다. 모든 성부가 연결됐거나 음악적으로 올바른 성부임을 뜻하지 않는다.
6. 모든 원 selector와 batch를 검토한 뒤에만 성공 report를 남긴다. 누락·순서 오류·입력 변조·예산 초과·출력 실패의 일부 파일을 전체 완료로 승격하지 않는다.

특정 작품명·마디 번호·사용자 정답을 분석 조건식에 넣지 않았다. 아래 작품·음표 ID는 재현용 사례 주소다.

## 2. 구현과 데이터 계약

- [비교 core](../../../src/musicanote_harness/completion_evidence_contrast.py): `completion-evidence-contrast-0.1.0`.
- [저장자료 실행기](../../../src/musicanote_harness/completion_evidence_contrast_trial.py): `completion-evidence-contrast-trial-0.1.0`.
- [실제 실행 진입점](../../../tmp/completion_evidence_contrast_pilot_20261004.py).
- [core 검사](../../../tests/test_completion_evidence_contrast.py), [읽기·실행기 검사](../../../tests/test_completion_evidence_contrast_trial.py).

실행기는 외부에서 고정한 receipt와 단계42 report의 물리 SHA를 확인한다. 같은 source-once 자료와 원 native/role batch의 연결을 확인하고 기존 `_batch`, `_entry`, `_validate_facet`를 통해 참조·원음가·pitch membership·베이스·전위·기능/credit 산술을 다시 검사한다. source-valid review를 대조하는 core 자체는 인증 gate가 아니다.

원 성부/NCT predicate는 재실행하지 않는다. 기존 기록을 읽어 그 조건부 결과와 literal 산술을 검토하는 작업이다. 저장 JSON의 `record_id`·숫자·status를 live native session의 실행 권한으로 복원하지 않는다.

원 selector 순서의 전체 목록 SHA, 모든 batch 범위, terminal의 batch 참조와 집계가 일치해야 한다. 대조에는 source/key/origin/partition/function 전제가 같은 counterpart만 들어간다. 변경된 조건부 음가에는 원 `sound_ref`, `source_note_refs`, pitch, full sounding span 및 변경된 `[start,end)`를 붙인다.

## 3. 실제 입력과 범위

이전 [단계42](2026-10-04-progression-evidence-readiness-review.md)의 quartet 문맥을 유지했다.

| 항목 | 범위 |
|---|---|
| 작품/구간 | `dcml:beethoven-quartets:n01op18-1_04`, global quarter `[262,270)` |
| 원음표 문맥 | 4 raw lanes, 53 sounding facts |
| 대조 | 같은 원 1,710 selector, 107 batch의 무연결 control ↔ linked counterpart |
| 조성 가정 | F major / D natural minor / D harmonic minor / D melodic minor ascending / unknown |
| control bundle | `fmilbundle_0906a14efed3e3c256975302`, 연결0 |
| linked bundle | `fmilbundle_1e1cd6dcdf890b211d46b870`, 연결20 |
| linked 가정의 출처 | `bounded_same_raw_lane_greedy_technical_probe` — 검수된 실제 대위 성부가 아님 |

연결20개는 첫 raw lane15개, 두 번째5개에 분포하고 나머지 두 lane의 실제 연결은0개다. 따라서 이 completion이 일반적인 실제 성부를 대표하거나 4성부의 해결을 충분히 평가한다고 주장하지 않는다. **분모 전체를 대조했다는 것과 음악적 성부 가정이 충분하다는 것은 별개다.**

원 전체 archive는 두 문맥·네 completion·8,050 selector다. 이번 완료는 그중 quartet 한 문맥의 두 대응 completion을 대조한 결과다. 1,710곡·5작품·전체 코퍼스 검증이 아니다. 단계42의 291,555 competitor pair를 재계산하지 않고, 정확히 대응하는1,710 bilateral pair를 비교했다.

### 외부 pin

- 연속 저장 receipt: `3be83bd74abaa5c7d149ba74cb75b7f47477fd9ed95c18e14e61f8b41bafb317`.
- 단계42 report: `d4b721402373fa535f6c74890e46124d85b45ec0777906da0d564d5b6de7698c`.
- 이번 actual report: `2c5504a2b91cc71a1b0b2166e09028472495b0097623c1a3fdb8d02b94200944`.

이 pin은 이번에 확인한 저장자료의 연결과 물리 내용에 관한 것이다. source 재파싱·학습·실시간 native 권한의 증명이 아니다.

## 4. 실제 결과와 음악적 의미

[실제 report](../../../output/completion-evidence-contrast-2026-10-04-r1/report.json), [원음표·연결 문맥](../../../output/completion-evidence-contrast-2026-10-04-r1/source-context.json).

전체 실행 exit0, **205.8941519초**. 입력226파일(일반 JSON9 + gzip217), decoded829,150,924B로 기본1GiB 이내다. 출력109파일/194,333,531B로 기본256MiB 이내다. source-once256MiB·일반 파일64MiB·출력 파일64MiB 기본 상한은 올리지 않았다. 종료 시 소비한 입력226개와 report 이전 출력108개의 길이/SHA를 확인했다.

| 근거 민감도 | 후보 발생 수 |
|---|---:|
| 조건부 NCT 설명 음가 증가 | 1,130 |
| 동일 | 580 |
| 감소 | 0 |
| 변경된 source credit span 발생 | 1,555 |
| 전체 내부 진행의 joint 지원 | 0 |
| joint false → false | 130 |
| joint unknown → unknown | 2,100 |

조건부 설명 변화에 등장하는 **고유 sounding event는6개**다: B♭2, D♭5, A♭2, G♭2 및 서로 다른 A♭4 두 event. 1,555는 여러 화음·조성·분할 가정에서 반복되는 span 발생 수이며 고유 음표 수가 아니다. 조건부 설명 음가를 후보 전체에 걸쳐 더한 archived 집계 `1555/2`도 곡의 실제 음가나 설명률로 사용하지 않는다.

### 아직 충족되지 않은 근거

linked 결과의 구성음 부족1,420후보·동시 core 없이 span에 모인 구성음580후보·미해결 비구성음/원자료 음가1,590후보·unknown key342후보는 유지된다. 미설명 음가0이면서 구성음이 빠진 후보는 **35→80**으로 늘었다. 이는 성능 개선률이 아니라 **설명량만으로 화음 선택 시 오판 위험이 커질 수 있다는 반례**다.

명시적 기능 선언130회에서 whole ordinary template은 모두 false로 유지됐다. 개별 ordinary role 지원도0이다. false 축은 source shape25회·target triad shape10회·function shape prerequisite30회·guarded pooled core75회·whole template130회로 중복될 수 있다. 저장된 실제 route occurrence에는 `first_changed_endpoint_not_linked_in_this_complete_witness`10회가 남는다. 모든 false를 이 한 이유로 설명하지 않는다. 필요한 route occurrence가 아예 만들어지지 않은 경우도 있고, 다른 축의 부족도 별도다.

undeclared transition2,100회는 unknown이다. 무조건 실패나 성공으로 바꾸지 않았다. 명목 HC 후보1회도 국소 조성·구조 성부·호흡/종결 등의 전제가 없으므로 확정하지 않는다.

**결론:** 실제 저장된 성부 가정이 일부 국소 NCT 설명에 영향을 준다는 점은 확인했다. 분산 화음의 최종 인식률, secondary/function/cadence 정답률이 향상됐다는 검증은 아니다. 그 판단에는 충분한 성부·구성음·시간적 화음 제시·조성·독립 주석 평가가 더 필요하다.

## 5. 재현 가능한 실제 사례

selector index는 원 배열의0-based 위치이며 마디 번호·최종 화음 순번이 아니다. 사례는 원 rule의 출력이다. 사례를 정답 조건문으로 역입력하지 않았다.

### A. 연결을 넣으면 국소 경과 형태가 설명된다

[batch0000](../../../output/completion-evidence-contrast-2026-10-04-r1/batch-0000.json), selector5.

실제 저성부의 C3 `[262,262½)` → B♭2 `[262½,263)` → A♭2 `[263,263½)`이다. 원 note ID는 각각 `note_54d18f1b3df1`, `note_213e6b67ab58`, `note_b22857715afb`다. linked 가정에는 두 순차 연결이 들어 있고 archived `local_passing` 절이 B♭2의1/2 quarter를 조건부로 설명한다. control에는 연결이 없어 설명하지 않는다.

이 후보는 `[262,270)` 전체를 Ab 근음과 Ab/C/Eb/Gb/Db/F의 넓은 구성음 목록으로 가정한다. 일반적인3/7화음의 정답으로 선언한 것이 아니다. 설명 추가 후 미설명 음가0이라도, 넓은 pooled 목록과 unknown key의 한계를 가진다. 이 사례에서 조성·화음 유지·NCT를 최종 확정하지 않는다.

### B. 미설명 음가0이어도 빠진 구성음은 해결되지 않는다

[batch0001](../../../output/completion-evidence-contrast-2026-10-04-r1/batch-0001.json), selector20.

같은 첫 부분의 Ab/C/Eb/Gb/Db/F 가정 뒤, `[266,270)`에서 Db/F/Ab/Cb를 가정한다. B♭2가 조건부 설명되면서 미설명 음가는0이 됐지만 **목표 화음의 Cb는 원음표에서 제시되지 않았다.** 링크가 누락 구성음을 만들어 내지는 않는다. 생략/재배치의 별도 근거 없이 이 후보를 정답으로 선택하지 않는다.

### C. 일부 음형 설명과 전체 화음 적합성은 독립적이다

[batch0003](../../../output/completion-evidence-contrast-2026-10-04-r1/batch-0003.json), selector55.

전체 구간에서 Gb/Bb/D를 가정한3음 후보는 A♭2의1/2 quarter 설명이 늘어도 D natural이 제시되지 않고 미해결 음가는49/2 quarter 남는다. 이49/2는 동시 여러 event의 note-time 합계이며8-quarter짜리 악보 구간 길이와 혼동하지 않는다. 작은 국소 설명이 전체 화음의 적합성을 보장하지 않는 사례다.

세 사례는 모두 unknown-key selector다. 같은 source의 다른 명시 key 대안도 원 순서로 검토했고, unknown을 조표로 대체하거나 연결 수로 조성을 추정하지 않았다.

## 6. 검증·교정과 보존

검사 대상은 genuine 소형 XML/native 데이터의 연결 유무·유리수·타이/재발음·첫 불리한 endpoint·동일 전제·음가 보존·unknown key·무승격 및 pinned gzip/전체 실행/누락/예산/출력 보호다. 소형 실행기6검사의 native/role body와 물리 파일은 실제지만 **상위 receipt ancestry는 명시 합성 fixture**다. 실제 역사 admission을 성공했다고 확대하지 않는다.

- 최초19검사 중 core12+source-binding1 PASS, reader6 ERROR: `_seal`이 객체를 제자리 변경하지 않고 새 값을 반환하는 fixture 작성 오류. 반환값을 받도록 수정했다.
- 수정19/20.083초 PASS; 소형 실행기6/7.659초 PASS; 통합25/48.235초 PASS.
- unknown key/서로 다른 기능 선언 반례2개 추가 후27검사 중1 ERROR: `key_inferred`의 위치를 flags가 아니라 review 본문으로 확인해야 하는 검사 작성 오류. 기능 코드를 완화하지 않고 검사를 교정했다. **최종27/60.257초 PASS**다.
- 기존 단계42/core/reader/native policy **70회귀/111.161초 PASS**. 중간/최종 실행을 새 고유 검사 수로 중복 합산하지 않는다.
- 선행70개 source/test/runner SHA 변경0. 별개 tracked5 변경은 유지한다. 실제 종료 후 입력226+출력108의334파일 길이·SHA 오류0, report SHA도 외부 재확인했다. Core/parser·원XML·원주석·과거결과·기본 한도·운영 UI·서버·Git 설정은 변경하지 않았다.

이번 output은 별도 디렉터리에 exclusive write로 저장했다. report 없는 partial 파일의 존재를 완료로 해석하지 않는다. 실행 후 output을 재검증하며 덮어쓰기하지 않는다. Git commit/push는 하지 않았다.

최종 QA: 새5파일 AST,3개 개발 문서 strict UTF-8/로컬 링크195개, replacement/zero-width 문자 및 끊긴 링크 오류0. `git diff --check` exit0이며 기존 tracked5의 LF→CRLF 경고는 유지됐다. 선행70SHA의 마지막 확인도 변경0이다.

## 7. 다음 기능 단위와 전체 남은 범위

7개 큰 실행 순서 중3의 진행 후보 비교 및4의 기능/종지 근거를 검증 중이다. 번호43은 개발 기록 번호이며 총43단계의 끝이나 완성률이 아니다. 현재 개발을 전체50%라고 환산할 근거도 없다.

남은 큰 묶음은 다음 네 가지다.

1. **최종 판단:** 충분한 성부 가정·조성·시간적 화음/NCT·기능/종지를 함께 검토하고, 충돌/보류/대안을 남기는 실제 선택 정책. 설명량 최대 후보를 무조건 선택하지 않는다.
2. **독립 다작품 검증:** 다음 비교는 베토벤 소나타 문맥으로 넓힌다. 이후 여러 작곡가·작품 가족·편성의 독립 주석 대조로 약점을 분류한다. 정확히 검증된 written/concert pitch와 판본 조건이 갖춰진 총보도 추가한다.
3. **악보 화면·피드백:** 최종/가설/보류를 구별한 로마자·구간·음표 근거·cadence 표시, 사용자의 앞뒤 XML/IR 문맥+설명+계산 버전 저장. 기존 운영 prototype과 이번 새 saved-only 검토를 혼동하지 않는다.
4. **구조·작곡·편곡 연결:** 화성/역할/질감/전개 정보를 별도 계층으로 소비하고, 단선율→피아노 솔로/듀엣/트리오/쿼텟부터 생성·평가한다. 모티프/프레이즈에서 완성곡, 관현악/장형식은 추가 범위다.

이번에 부족한20-link 임시 가정을 위해 계속 세부 예외를 쌓지 않는다. 먼저 Sonata의 다른 실제 문맥과 기능 후보를 대조해 일반적인 병목인지 검토한다. 전체 request가 자원 한도에 맞지 않으면 사전에 명시한 음악 범위·누락 분모·완전한 하위 요청을 기록하고, 유리한 후보만 골라 성공으로 만들거나 기본 cap을 올리지 않는다.

기간/퍼센트는 여러 작품에서 실제 선택 정확도와 수정 비용을 측정한 뒤 추정한다. 이 네 묶음의 구현 완료, 검증 완료, 운영 적용을 각각 기록한다.
