# 원본 음표 위치의 불변 수정 후보와 성부 참조 감사

관련 변경: HARM-DEV-20260930-27. 이전 [실제 관계·문맥 감사](2026-09-30-relation-witness-case-audit.md)의 후속이다. 화성 정답을 추가하거나 운영 분석기를 수정한 단계가 아니다.

## 문제와 조사 결과

이전 r4 사례 문맥에서 같은 pitch/onset의 장식음과 본음이 서로 다른 원본 `note[k]`를 가리킨 네 음표가 발견됐다. XML의 실제 pitch/음가/장식음 여부는 IR의 음악 이벤트와 대응할 수 있었다. 따라서 원본 악보 손상으로 단정하지 않고, 과거 저장된 locator를 새 문서 revision에서 재검사한다.

현재 `engraving.py`의 `source-note-mapping-0.2.0`은 이미 part/staff/인쇄 마디/onset/pitch/정확 유리수 duration/grace/tie를 구별한다. 이번 변경은 그 production mapper를 다시 고친 것이 아니라, 기존 immutable IR에 이를 적용해 **독립 검증한 수정 후보**를 저장하는 새 prototype이다. 예전 preparation에는 mapping version이 없어 과거의 특정 parser 버그를 확정할 수 없다.

기존 `source_identity_revision.py`는 measure/voice/tie/sound/attack/group를 재구성하는 더 넓은 migration이므로 이 작업에 재사용하지 않는다. `source_enrichment.py`도 pitch·조표·박자·음자리표·directions 등을 갱신하므로 후보에 직접 실행하지 않는다. `source_note_mapping_audit.py`의 옛 후보는 부모 document ID를 유지하고 grace/tie를 독립 비교하지 않으므로 이번 불변 revision 계약을 대신하지 못한다. 기존 코드·출력은 보존한다.

## 일반 규칙과 저장 계약

1. 원본 XML SHA와 IR의 `source_files` SHA가 같아야 한다. 현재 범위는 단일 source의 score-partwise XML이다.
2. 원본을 별도로 읽어 물리적 part/measure/note ordinal, backup/forward cursor, pitch, duration, grace, tie를 계산한다. MusicXML에는 ID만 추가한 rendering copy를 만들고, 나머지 원자료 관찰이 그대로인지 재대조한다.
3. 현재 mapper의 완전한 일대일 대응이 필요하다. 동일 pitch/onset/duration/grace/tie/voice까지 같아 구별할 수 없는 음표는 과거 XPath나 나열 순서로 강제 배정하지 않는다.
4. 독립 gate는 **물리적 마디 순번과 IR sequential order**, part/staff, 인쇄번호, onset, duration, written pitch, grace, tie 및 실제 source reference 6필드를 비교한다. 인쇄번호는 물리적 마디 ID를 대신하지 않는다.
5. 변경 허용: source reference의 `source_part_id`, `source_measure_number`, `source_voice`, `source_staff`, `source_element_index`, `source_xpath`; note notation의 `accidental_display`, `stem`, `beams`, `fermata`, `slurs`, `tuplets`, `articulations`, `time_modification`; `grace.slash`; 새 `ir_document_id`.
6. 그 외 전체 JSON의 배열 길이/순서와 의미를 보존한다. score/note/rest/source-ref IDs, source file/fingerprint, written/concert pitch, duration/global onset, logical voice/staff, grace role/order/anchor, tie/sound/attack/chord, measure/meter/key, parser metadata/validation/extensions는 바꾸지 않는다. 알 수 없는 notation/expressions도 부모에서 유지한다.
7. Canonical schema 검증과 전체 보호 projection 일치 검사 뒤에만 candidate를 저장한다. 부모 ID/source SHA/버전/후보 전체 내용으로 새 document ID를 결정론적으로 생성한다.
8. sidecar `revision.json`에 부모·원XML·후보 SHA, mapping version/policy, 변경 전후 JSON pointer(누락과 null 구별), 원래 split/rights/pitch policy, exact/mismatch/보류 상태를 저장한다. Core에 무규격 provenance 필드를 넣지 않는다.
9. 기존 annotation/analysis는 **부모 revision에 그대로 연결**한다. 같은 note ID가 남아도 새 revision으로 자동 retarget하거나 gold/학습 자료로 승인하지 않는다. 기보 correction은 향후 beam/fermata 기반 Phrase/Motif 결과에 영향을 줄 수 있으므로 모든 분석 결과가 불변이라고 주장하지 않는다.

XML voice 번호가 IR hint와 다른 유일 geometry도 현재 mapper에서는 연결 가능하다. 이때 raw `source_voice`만 기록하고 logical `voice_id`는 수정하지 않으며, 성부 인증 성공으로 세지 않는다.

## 실제 실행 범위와 결과

정본 실행은 `output/source-locator-revision-trial-2026-09-30-r2/`이다. 입력은 기존 breadth r2의 19작품 가족/33개 악보·악장, 사례는 relation-case r4의 41samples/125groupcontexts를 그대로 사용한다. 전체 33개를 시도하고 보류 package를 쉬운 것으로 교체하지 않는다. 원주석 라벨은 mapping 또는 수정 선택에 입력하지 않는다.

- 전체 음표 44,607개. 별도 현재 mapper의 읽기 전용 전수 검사에서는 44,564개 대응/43개 미대응, complete 27개/incomplete 6개였다.
- 더 엄격한 불변 revision에서는 **26개 candidate-ready / 7개 blocked**. 중복 measure ID는 physical ordinal을 하나로 인증할 수 없어 mapping 전 보류한다. 이 때문에 위 단순 mapper 집계와 revision 집계는 다르다.
- 수정 후보의 전체 31,365개 음표가 독립 source 비교 exact. 잘못된 참조 60개 교정; source reference 객체 변경 66개와 기보 객체 변경 325개는 별도 수치다. optional/null 필드 추가도 변경 수에 포함되며 전부 새로운 오류 66개라는 뜻은 아니다.
- revision 자체가 매핑한 범위는 41,078음표(41,044대응/34미대응), 중복 measure ID 때문에 매핑 전 보류한 범위는 3,529음표이다. candidate가 없는 7package의 전체 음표는 13,242개다. 전수 mapper의 43미대응과 이 34개를 혼동하지 않는다.
- 이전 사례 41samples 모두 목록에 유지. 111contexts를 새 revision으로 재대조해 모두 source fields 일치, 14contexts는 blocked package의 부모 자료로 보존.
- 출력에는 33원XML/33부모IR/26후보IR/33revision sidecars와 37context gzip, 합계162개 artifact를 보존한다. report와 run-contract는 별도다. 기존41sample 중4개는 candidate-blocked 목록으로 남아14context를 부모로 참조한다.
- 재대조 문맥의 6,426반복 음표 instances / 1,665고유 음표가 일치. 이전 전체 125contexts의 6,940instances/1,820고유 음표와 분모가 다르므로 이 숫자만으로 개선율을 계산하지 않는다.
- 기존에 알려진 네 mismatch 모두 새 revision에서 exact. 이들을 포함한 세 문맥의 경고도 해소된다. 부모 r4의 warning과 파일은 수정하지 않는다.

### 네 음표의 정확한 대응

모든 XPath의 prefix는 `/score-partwise/part[1]`이다. duration 단위는 quarter이다.

| 악보/음표 | 부모 locator | 새 locator | 실제 관찰 |
|---|---|---|---|
| Chopin BI126-3op41-1 `note_e7894af2c733` | m79/note[6] | m79/note[4] | A4, onset2, grace, duration0 |
| 같은 악보 `note_9f15da83a443` | m79/note[4] | m79/note[6] | A4, onset2, principal, duration1 |
| Mozart K280-1 `note_f5aaa47b6556` | m47/note[8] | m47/note[6] | D5, onset1, grace, duration0 |
| 같은 악보 `note_1d9f2930fc98` | m47/note[6] | m47/note[8] | D5, onset1, principal, duration2 |

본음과 장식음의 음악 event 자체를 맞바꾸거나 grace를 duration에서 추측하지 않았다. 오래된 source location/관찰 기보를 새로운 revision에서 원본과 맞춘 것이다.

### 보류를 유지한 악보

| package | 보류 이유 |
|---|---|
| Beethoven quartet n01op18-1_01 | 동일 geometry에서 미대응4개 |
| Beethoven sonata01-1 | 중복 measure ID; 별도 mapper에서는 미대응1개도 관찰 |
| Beethoven sonata02-3 | 중복 measure ID; 별도 mapper에서는 미대응8개도 관찰 |
| Chopin BI105-3op30-3 | 미대응2개 |
| Chopin BI105-4op30-4 | 미대응12개 |
| Mozart K280-3 | 중복 measure ID; 단순 note mapper는 complete지만 revision은 보류 |
| Mozart K281-3 | 미대응16개 |

미대응 원음표는 삭제하지 않는다. 반복 grace의 순서 대응 및 물리적 measure identity는 별도 migration/sequence 계약이 필요한 다음 문제다.

## 추가 성부 감사

별도 `source_locator_voice_audit.py`는 같은 현재 mapper와 원본 XML을 사용해 logical lane과 raw XML voice 관계만 관찰한다. production lane이나 음표를 재그룹하지 않는다.

전수 mapping의 17,321voice-hint 차이 중 대부분은 단순 상수 오표기만이 아니다. 매핑 가능한 음표의 168logical lanes 중 41개가 실제 XML(part,voice) 두 개를 포함하고, 127개는 하나다. 차이 음표 16,411개는 mixed lane, 910개는 single-source lane에 있다. 미대응43개는 별도 남겨 둔다.

이전 125context의 441lane instances 중 22개가 mixed(21contexts), 419개가 single-source였다. 그러나 이전 direct578 **query records**에 저장된 704selected-link instances(51고유 package+sound-ID pairs)는 모두 실제 XML(part,voice)가 같았다. query 수, link instances, 고유 연결 수는 서로 다르다. 현 양성 연결이 mixed lane 때문에 다른 명시 source voice를 잇는다는 증거는 없지만, XML voice 자체가 실제 대위법 성부를 인증하지도 않는다.

Temporal16query records의25paths/25link instances(15고유 package+sound-ID pairs) 역시 모두 같은 명시 XML(part,voice) 안에 있었다. 이전 단계에서 실제 지연 도착 양성은0이었으므로 이번25paths가 새 delayed-resolution 정답25개라는 뜻은 아니다.

성부 감사 정본은 `output/source-locator-voice-audit-2026-09-30-r2/`이며 r1은 초기 이력으로 보존한다. 33package/41sample의74gzip와 report/run-contract가 있다. 각 note의 fresh locator·실제 raw voice/staff, logical lane의 원음표 목록, saved witness의 원 sound/note IDs를 보존한다. 이 결과는 이전 화성 분석을 새로운 정답으로 승인하는 근거가 아니다.

## 초기 실행과 검증 이력

- r1은 보존한다. 26ready/7blocked,60교정과111context 결과는 같으나 mapping 전 미검사 음표를 summary에서 별도로 세지 않았다. 이를 attempted/unattempted/noncandidate partition으로 명시한 r2를 정본으로 한다.
- r2에서는 부모 snapshot의 XML SHA와 manifest를 교차 확인하고, source score path가 frozen source-files 목록에 있어야 하며, 중복 sample identity/output basename을 차단한다. XML parse failure도 보류하고 mapper에는 부모 deep copy만 전달한다.
- complete mapping 뒤 independent after-check에서 실패한 blocked 후보의 집계 반례를 추가했다. 후보 note count에 더하지 않고 `blocked_attempted_after_note_checks`에 남겨 이중 집계/중단을 방지한다. 실제33개의 7blocked는 그보다 앞 단계에서 보류돼 결과 수치는 변하지 않았다.
- `validate_revision`과 pointer diff는 canonical JSON byte 비교를 사용한다. Python의 `True == 1`, `1.0 == 1` 때문에 보호 metadata의 타입 변경이 묻히는 반례를 차단한다.
- 성부 진단 r1의 whitespace-only `<voice>`를 빈 문자열 명시 identity로 보는 helper 허점도 독립 검토에서 발견했다. 실제33XML 및44,564매핑 음표에는 공백-only voice가0개라 기존 결과에는 영향이 없었다. 별도 진단 v0.1.1/r2에서 빈 voice/staff를 보류하는 회귀를 추가했다. 원본/production mapper는 변경하지 않는다.
- 새 테스트는 같은 음높이/동시점의 grace와 principal, exact triplets, 모호한 unison/repeated grace, stale XPath, 허위 complete mapping, hash/중복/ref 오류, source 변경, 배열/기보 allowlist, 정책/압축/보류 context 등을 검사한다.
- 신규87개 검사(locator34/trial27/voice26)를 포함한 전체Python **2,136개 테스트가49.668초에 통과**했다. 기존 Verovio layout warning1건은 실패가 아니었다. 코드 검사 수는 작품 수나 음악적 정확도가 아니다.

Source revision r2는152.891초에 종료했고 251입력/251당시 source 코드 해시·파일목록과162artifact가 종료시 불변이었다. 이후 사용하지 않는 별도 voice 진단 모듈만 v0.1.1로 보강했으므로 r2의 당시 코드 해시와 이후 checkout을 구별한다. 독립 최종 감사에서도 당시251코드 중250개가 일치하고 비사용 voice 모듈1개만 이 예정된 변경임을 확인했다. revision/trial 자체는 v0.1.1로 고정되며 r2 후보 파일은 다시 덮어쓰지 않는다.

독립 감사는162artifact와37gzip의 SHA/CRC/JSON, 원XML/부모IR의 원본 byte 일치, 26후보31,365음표의schema·타입까지 보존하는 전체projection·raw XML15항목·일대일locator·sidecar pointer diff·새document ID를 재대조해 통과했다. 60교정/66ref/325notation,111재대조/14부모 보존 수치도 독립 집계와 같았다.

Voice audit r2는19.318초에 종료했다. 독립 감사에서251입력/251현재코드와파일목록/74artifact/run-contract SHA가 모두 일치했다. r1/r2 summary는 동일하며74gzip의version 이외 의미 데이터 차이는0이었다. 실제 witness의원음표도 다시 확인했다. 이 실행 시간은 전체엔진 성능 benchmark가 아니다.

## 구현과 재현

- `src/musicanote_harness/source_locator_revision.py`: 불변 note-locator 수정 후보와 독립 원자료 검사.
- `src/musicanote_harness/source_locator_revision_trial.py`: 전체 동결 package/사례·정책·해시·보류 보존 실행.
- `src/musicanote_harness/source_locator_voice_audit.py`: source voice/lane 및 기존 witness 연결의 관찰 감사.
- `tests/test_source_locator_revision.py`, `tests/test_source_locator_revision_trial.py`, `tests/test_source_locator_voice_audit.py`: 각 계약 회귀 검사.

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.source_locator_revision_trial --plan output/harmony-breadth-trial-2026-09-30-r2/frozen-plan.json --previous output/harmony-relation-case-audit-2026-09-30-r4 --output output/source-locator-revision-trial-2026-09-30-r2
.venv/Scripts/python.exe -B -m musicanote_harness.source_locator_voice_audit --plan output/harmony-breadth-trial-2026-09-30-r2/frozen-plan.json --cases output/harmony-relation-case-audit-2026-09-30-r4 --output output/source-locator-voice-audit-2026-09-30-r2
$env:PYTHONPATH='src;tests'
.venv/Scripts/python.exe -m unittest discover -s tests -q
```

완료된 output은 overwrite하지 않는다. 재실행은 새 output 경로를 사용한다. 원 XML/full parent IR/full candidate IR/sidecar/context gzip/report/contract가 함께 있어야 재현할 수 있다.

## 아직 하지 않은 것과 다음 순서

1. 부모 IR/원주석/기존 manifest/분할/권한/production parser/schema를 수정하지 않았다. 5173/8822 화면, 구조 분석 판단, 외부 API, Git commit/push도 변경하지 않았다.
2. 모든 notation·rest·global XML 시간/repeat·concert pitch·실제 대위법 성부를 인증하지 않았다. 이번 exact는 관찰한 pitched-note locator 계약에 한정한다.
3. 중복 physical measure ID와 순서로만 구별되는 grace/unison을 기존 sequence 방식과 대조한 뒤, 별도 revision에서 해결 가능성/ID aliases를 검증한다. 성부 문제는 부모 lane를 임의 분리하지 않고 raw-source 근거를 유지한다.
4. 그 기반 위에서 미설명음과 조건부 NCT·전체 구성음·경쟁 quality/생략 가설을 결합한다. 실제 delayed-resolution 양성, 관현악의 score-order written/concert timeline, 독립 화성 정확도와 최종 선택기는 계속 남아 있다.

사용자에게 새 음악 해석을 선택받아야만 이 source 수정 후보를 만들 수 있는 단계는 아니다. 사람의 의견은 해석이 충돌하는 구간에서 다시 요청한다.
