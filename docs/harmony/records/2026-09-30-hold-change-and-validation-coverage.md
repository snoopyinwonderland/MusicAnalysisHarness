# HARM-DEV-20260930-23 — 동일 성부 가정의 유지/변화 비교와 검증 범위 감사

## 요청·판단·범위

사용자 요청: “다음 하세요. 지금 분석 대상이 충분한가요. 1804개 통과라는 건 몇 곡의 작품에서 나온 숫자인가요.”

1,804는 직전 전체 Python 테스트 수다. 실제 작품 수, 화성 정답 수, 주석 수가 아니다. 파서/IR/스키마/오류 처리/합성 음악 fixture/회귀 계약 등이 포함되므로 작품 수로 환산할 수 없다. 앞으로 **코드 테스트, 실제 구간, 고유 악장, 작품 가족, 사람 검수, 평가 적격, 정확도**를 분리한다.

이번에는 직전 계획의 ‘같은 문맥에서 한 화음의 장식과 여러 화음의 변화를 비교’하는 제한적 진단을 구현했다. 동시에 실제 자료 범위를 감사하고 다른 작품의 확대 목록을 고정했다. 확대 목록의 생성은 그 작품의 새 분석 실행이나 독립 평가 완료가 아니다.

## 1. 실제 음악 검증 범위

| 최신 pilot의 악장 | 최신 구간 | 이전 동일 문맥 구간 |
|---|---:|---:|
| 베토벤 소나타 2번 3악장 (`02-3`) | 3 | 43 |
| 모차르트 K281 3악장 (`K281-3`) | 5 | 67 |
| 모차르트 K280 1악장 (`K280-1`) | 5 | 74 |
| 합계 | 13 | 184 |

13개와184개는 모두 **같은3악장/3소나타 가족**에서 나온다. 최신 생략/반복 베이스 스트레스 검사에 실제로 사용된 두 chain은 모두K280 1악장이다. 여러 후보/성부 대응을 계산한 횟수를 독립 악보 사례로 더하지 않는다.

프로젝트 전체의 과거 foundation/appendix 검사는 다른 베토벤·모차르트 악장을 포함한12악장을 다뤘고 소나타8번1/3악장 검토도 있다. 그러나 최신 규칙이 그 전체에서 검증됐다는 뜻은 아니다. 과거 결과를 최신 모듈의 정확도로 소급 사용하지 않는다.

기존117경계의 단일 변화 평가 적격은0: 비교 한쪽에 추가 주석 변화105개, 페달 참조 변환 미지원12개 때문이다. **정확도0%가 아니라, 현 평가 계약으로 정확도를 아직 계산할 수 없다는 뜻**이다.

결론:3악장은 구현 진단에는 유용하지만 일반화/음악적 정확도 판단에는 부족하다. 구간만 더 뽑기보다 다른 작품 가족과 실제 양성·근접 반례가 필요하다.

## 2. 준비된 자료와 확대 계획

현재 감사한 DCML 준비 batch는392악보/주석 package: complete221, partial112, quarantined59이며 정렬 적격333개다. complete 중 베토벤 소나타14악장, 모차르트 소나타23악장, 합계37악장이 있다. 전체392개의 사람 검수 상태는 `unverified`다. 이 수치는 **가져오기/시간 정렬 품질**이며 화성 정답률이 아니다. 다른 미감사 코퍼스까지 합친 전체 보유량도 아니다.

`harmony_validation_coverage.py`가 실제 파일 hash와 provenance로 범위를 집계한다. 악보·주석의 두 hash가 기존 manifest와 모두 일치해야 split/권한을 연결한다. 이름으로 유추한 가족 ID의 근거는 별도 표기하고, hash/가족 split 누출·미상 정책은 보류한다. 기존 holdout은 새 정렬 통과만으로 학습/개발에 풀지 않는다.

동일3pilot 가족을 제외한 complete 소나타 가족 중6개를 결정론적으로 제안했다.

| 대상 | 현 정책에 따른 이번 실행 자격 |
|---|---|
| 베토벤1번2악장 (`01-2`) | 기존train/내부 연구로 개발 회귀 실행 가능 |
| 베토벤3번2악장 (`03-2`) | 기존train/내부 연구로 개발 회귀 실행 가능 |
| 모차르트K279 1악장 | 기존holdout 보호; blind 승인 없이 실행/조정하지 않음 |
| 모차르트K282 1악장 | 기존holdout 보호; blind 승인 없이 실행/조정하지 않음 |
| 베토벤7번2악장 (`07-2`) | cross-manifest split/권한 미상으로 보류 |
| 베토벤8번2악장 (`08-2`) | cross-manifest split/권한 미상으로 보류 |

모두 이번에는 **선정·hash 고정만** 했다. 내부 실행 가능2가족도 새 독립 평가 gold가 아니다. 악장/판본/주석 계보가 같은 작품은 같은 split에 둔다. 향후 각 규칙에 양성·음악적으로 가까운 반례·정보 부족을 확보하고, 참조를 가린 계산 후 주석 대조를 한다. 오래된 source-conditioned 검사나 내부train을 blind 정확도로 보고하지 않는다. 현재 소나타 중심 자료의 시대/악기/형식 편향도 별도 평가 대상이다.

## 3. 새 계산의 일반 규칙

- 모든 sounding event와 정확한 유리수 시간 셀을 양쪽에 동일하게 사용한다. 원음을 삭제하거나 생략음을 생성하지 않는다.
- 한 화음 유지(`hold`)와 명시적인3구간 화음 경로(`change`)에 **하나의 동일한 부분 성부 대응**을 적용한다.
- contour link 부분집합 전체를 예산 안에서 검사한다. 강제 반복 베이스가 없는 경우/있는 경우를 모두 포함한다. 진짜 빈 연결과 ‘베이스만 연결’은 다르다.
- A→G→A와A→B♭→A처럼 같은 endpoint를 공유하는 경쟁 contour는 한 성부로 동시에 연결하지 않는다. 반복F3 베이스와F3→G3→F3 contour의 충돌도 보존한다.
- 보조음 조건은 바깥음 전체 지속이 구성음, 중간음 전체 지속이 비구성음이며 모든 contour link가 해당 assignment에 있어야 한다. 짧은 유리한 부분만 잘라서 조건을 만족시키지 않는다.
- sound가 공급된 화성 범위 밖까지 이어지면 필요한 외부 화성 문맥을 보류한다. 후보 blocker/unknown 철자/미지원 미세음도 보류·미정으로 보존한다.
- `change`의 구성음을 `hold`에서의 보조음 역할로 덮어쓰지 않는다. 설명 가능한 일부 음형이 있더라도 다른 모든 비구성음은 계속 미설명으로 남는다.
- 두 해석의 구성음/조건부 비구성음/보류/미설명 음가와 wall-time를 각각 저장한다. 많은 음을 설명한 쪽을 자동 승자로 선택하지 않는다.
- 동일 화음을 똑같이 세 구간에 복제하면 조건부 설명과 음가가 같아야 한다. 이 partition invariance는 자기일관성 검사이지 음악적 정답 검사 아니다.

이번 assignment 집합은 **보조음 contour 부분집합과 반복 베이스 제약의 제한된 조합**이지 전체 대위법적 성부 가설의 완전 열거가 아니다. 경과·계류·이중 보조·페달 등의 모든 NCT를 해결하지 않았다.

실제 replay는 이전 생략 단계에서 이미 적격인 return triple만 대상으로 한다. 모든 interval의 다른 후보는 기존 표에 그대로 남지만 이번에는 그 모든 path 조합을 계산하지 않는다. 이 제한을 `path_scope`에 기록한다. 일반 함수 `compare()`는 명시적으로 주어진 완전 경로를 같은 계약으로 비교할 수 있다.

## 4. 실제 관찰·결과

13개 고정pilot 입력을 보존했다. 반복 chain2개/13분할 중12분할은 이전 단계의 적격 triple이 없고, K280 sample16의 quarter7/8 분할1개만 이번 비교 대상이다. baseline 보류1표본과 이전 pair-budget 보류1표본도 유지했다.

해당 분할의 유지 후보64개 × 유효 assignment8개 × 기존 change triple1개 = **512조건부 비교**. 실제512구간이나512정답이 아니다. 같은 화음 복제 invariance512개, 진짜 빈 assignment 비교64개. 계획16constraint sets 중8개는 분기/병합 충돌이다.

실제 K280 quarter `[6,9)`에서 F-major hold 후보(`open_f140c53c1087c0fc1b1a`, whole reading19)는 총note-time11 중 구성음7, 조건부 보조음0~2, 미설명4~2다. 단위는 **모든 음의 지속을 합친 quarter-note-time**이며 구간 길이3quarter나 신뢰도와 다르다.

강제F3 베이스와 양립하는 A3→G3→G3→A3 또는 A3→B♭3→B♭3→A3를 하나씩 선택하면 hold의 조건부 설명1, 미설명3이다. 이 두 contour는 서로 같은 시작/도착A3를 공유하므로 동시에 채택할 수 없다. 베이스 제약 없는 다른 연결 가정도 별도 대안으로만 저장한다.

같은 assignment의 F–A–C(5음 생략 가정) → E–G–B♭ → F–A–C–E♭ 경로에서는 중간G/B♭가 구성음이다. 구성음note-time10/조건부 보조0/미설명 반복F3의note-time1이 남는다. C생략은 여전히 가정이고, 실제E5→E♭5를E→F해결로 바꾸지 않는다. 이 차이만으로 페달/기능/화성 변화 또는 더 유리한 해석을 확정하지 않았다.

실제음 refs와 앞뒤 문맥은 [직전 성부 대조 기록](2026-09-30-omission-voice-context.md)의 frozen IR·source snapshot과 이번 artifact에 연결돼 있다. 원자료 주석은 계산/선정에 사용하지 않았다.

## 5. 구현·재현·검증

변경: `harmony_hold_change_context.py`(version0.1.0), `harmony_missing_evidence_trial.py`의 선택적`--hold-change-context`, `harmony_validation_coverage.py`(version0.1.0), 해당 두 테스트 파일. 기존 코드/Core/parser/주석 데이터 semantics를 변경하지 않는다.

실행:

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_missing_evidence_trial --source output/harmony-distributed-resolution-2026-09-30-r1 --ir-source output/harmony-shared-context-2026-09-30-r1 --output output/harmony-hold-change-context-2026-09-30-r2 --hold-change-context
.venv/Scripts/python.exe -m musicanote_harness.harmony_validation_coverage --latest-report output/harmony-omission-voice-context-2026-09-30-r3/report.json --shared-report output/harmony-shared-context-2026-09-30-r1/report.json --prepared-tracks output/dcml-batch-repeat-v2-2026-09-24/prepared_tracks.jsonl --manifest output/harmony-dataset-manifest-2026-09-25.json --output output/harmony-validation-coverage-2026-09-30-r2 --unit-test-count 1804 --family-limit 6
```

재실행 시에는 새로운 output 폴더를 지정한다. 이미 존재하는 결과를 덮어쓰지 않는다. coverage의1,804는 사용자 질문에 해당하는 **직전 supplied 코드 테스트 지표**를 고정한 값이며, 이번 변경을 포함한 전체 테스트 수는1,846이다.

coverage CLI의 정확한 입력과 최종 결과는 `output/harmony-validation-coverage-2026-09-30-r2/run-contract.json` 및 `report.json`으로 고정한다. sources: 최신pilot report, shared-context report/source snapshots, `output/dcml-batch-repeat-v2-2026-09-24/prepared_tracks.jsonl`, 기존 case manifest, 준비report392개와 선정IR6개. 악보 자체의 새 분석 의미 검증은 이 감사에 포함하지 않는다.

최종 검증: 신규42(유지/변화23,범위 감사19),전체1,846테스트/25.035초 통과. 기존layoutwarning1건. 최종replay13artifact/241code hashes와coverage424input/3code hashes를 현 파일과 다시 대조했다. `git diff --check`, 새 파일 trailing whitespace 및개발 문서 상대 링크/대체문자 검사 통과(기존CRLF변환warning만). 수치 정본은 개발 로그의 이 단계 항목과 frozen reports다. 이번 변경은 파일 외부 공개/AI 전송/학습/새 split 할당/정답 승인/Git push를 수행하지 않았다.

## 6. 실패·정정·미해결·다음

- r1은 초기 diagnostic으로 보존한다. 별도 검토 후 후보조합 수와 실제 group 곱의 일치 guard, context event IDs를 포함한 assignment ID scope를 보강하고r2를 최종 실행한다.
- 미세음 alter를정수로 반올림/절삭해 일반음처럼 판정하지 않도록 이번 비교에서 미지원 미정 처리했다. Canonical IR의 원철자는 변경하지 않는다.
- 자동선택/기능/페달/모든NCT/장기 문맥/독립 정확도는 미완료다. 현8822악보는 이 최신 계산을 보여 주지 않는다. 운영5173/구조 분석/악보 화면에는 승격하지 않았다.
- 다음은 내부 권한이 확인된 추가2가족에서 참조라벨 없는 관측 계획을 먼저 고정해 최신 근거 비교를 재실행하고, supported 양성·근접 반례와 보류 사유를 분류한다. source annotation은 후행 대조용으로만 사용한다.
- 별도 평가 cohort의 split·판본/주석계보·권한·정렬·사람 검수 자격을 확정한 후에야 정확도 지표를 낸다. 자료 수와 코드 통과 수로 이 단계를 대신하지 않는다.
