# 단계93 — 큰 Train 오답의 원인 분해와 7음 소멸 증거

## 1. 결론과 다음 우선순위

기존 Train 118구간을 전부 확인했다. **새로운 화음 선택이나 학습을 한 단계가 아니다.** 고정 모델의 완료102/주석 일치58/오답44/계산 보류16은 그대로다. 기존에 분석에 사용한 23전체악장 IR/XML, 15작품군, 원후보60,129개를 유지했다.

큰 오답의 문제는 한 종류가 아니다. 오답 시간38quarter를 원인별로 나누고, 음의 실제 지속과 구성음 지지에 관한 새 특징 하나를 구현했다. 이 특징으로 구별되는 오답은 **1구간뿐**이다. 따라서 이 특징 하나를 새로운 주력 규칙으로 채택하거나, 작은 예제의 성공을 전체 성능 향상으로 보고하지 않는다.

다음은 **지지되는 구성음의 시간적 변화와 기능적 6/4의 전후 관계**를 우선 다룬다. 임의 가중치로 이 한 사례를 고친 뒤 전체가 좋아졌다고 주장하지 않는다. 원 Train의 다른 오답 경쟁 경로와 정답 보호 대조까지 새 특징을 연결한 뒤, 의미 있는 분리력이 확인될 때만 제한 학습 → 새 공동 선택 → 고정 Dev를 진행한다. 운영 화면과 Claude 편곡 엔진 연결은 여전히 보류다.

## 2. 실행 범위와 정확한 의미

| 항목 | 실제 수행 |
|---|---|
| 자료 | 단계91에서 봉인한 원118 Train record; 부분 표본으로 축소하지 않음 |
| 출처 | 23전체악장 source package, 15작품군; 원XML/IR를 SHA로 연결 |
| 완료/보류 | 완료102, 정답58, 오답44, 원계산 보류16 그대로 |
| 경로 관찰 | 저장된 Train target118 + 기존 승자102 = 220경로, union 화음415개 |
| 새 계산 | 원35항의 승자/target 비용 분해 + source-only 소멸 특징 추출 |
| 실제 추출 시간 | 217.504391초; 새 DP의 실행 시간이나 속도 개선 수치가 아님 |
| 하지 않은 것 | 새 후보 공급·DP 재탐색·학습·가중치 변경·Dev 조회·운영 배포·원주석 수정 |

`quarter`는 **4분음표 단위의 내부 유리수 시간**이다. 2/2 또는 복합박자의 실제 기준 박과 같다고 읽지 않는다. 모든 시간 구간은 `[start,end)`다. 새 특징의 음가 판단은 원악보의 박자 변화와 복합박자 환산을 별도로 적용한다.

저장 target은 이미 주석으로 만든 Train 평가용 witness다. target의 음향 특징도 동일한 label-free 함수로 계산하지만, target 경로를 블라인드 출력으로 내보내지 않는다. 이 비교는 전체 후보 집합의 recall 재측정, 독립 Test 정확도, Roman/국소 조성/전위/NCT의 전체 정확도가 아니다.

## 3. 큰 오류의 분류

선택된 경로와 저장 target을 정확한 공통 시간 셀로 비교했다. 같은 화음의 raw 분할이나 ID 별칭 차이는 오류로 세지 않는다.

| 두 경로의 차이 | 오류 시간(quarter) | 오류 시간 중 비중 | 주의할 점 |
|---|---:|---:|---|
| 근음과 구성음 모두 다름 | `95/4` = 23.75 | 62.50% | 화음 종류·구간·비화성음 설명이 섞일 수 있으므로 추가 분해 필요 |
| 구성음은 같고 분석 근음만 다름 | `63/8` = 7.875 | 20.72% | 이 자료에서는 전부 기능적 6/4 가설 대 literal 표면 3화음 경쟁 |
| 근음은 같고 구성음이 다름 | `51/8` = 6.375 | 16.78% | 7음·변화 구성음의 추가/탈락, 구간 과병합/과분할 등을 구별해야 함 |
| 합계 | 38 | 100% | 계산 보류16의 시간을 이 완료 오답 분해에 섞지 않음 |

같은 구성음/다른 근음 오류는 8record에 있다. 오답 중 저장 target의 기능적 6/4가 선택 범위 끝에서 끝나 뒤의 **선택된 화음**을 갖지 못하는 것은 6record다. 원전체악보가 사라진 것은 아니다. 기존 해결 보너스가 다음 선택 화음을 요구하므로, 전체 원음을 가지고 있어도 단일 짧은 탐색 범위에서는 그 보너스를 사용할 수 없는 경우가 있다는 뜻이다.

이것만으로 6record의 주석 해석이 모두 확정되거나 문맥 범위 확장이 모두 정답을 복구한다고 말하지 않는다. 다음 화음을 정답 주석에서 가져오거나, 같은 베이스라는 이유만으로 종지적 6/4를 확정하는 것도 금지한다.

## 4. 구현한 일반 특징

파일: `src/musicanote_harness/harmony_member_release.py`

특징: `supported_triad_seventh_release_tail`

1. 인접한 동일 철자/구성음 경로를 union run으로 합친다. 원XML의 분할 개수에 따라 특징이 달라지지 않는다.
2. 후보가 literal 7화음인지 확인한다. 미지원 기능적 형태는 `null`; 3화음 후보는 해당 특징이 없는 known zero다.
3. 원canonical sounding event의 실제 음가를 사용한다. 붙임줄 뒤 음을 새 attack처럼 처리하거나 앞음의 짧은 기보 음가로 지속을 잘라내지 않는다.
4. 양수 음가·철자·source clock을 확인한다. source clock gate가 거부하면 `null`이다. 0음가의 grace는 구성음 지속을 만들어내지 않는다.
5. 이 run에서 실제로 나온 모든 7음의 마지막 release를 찾는다. 뒤에 7음이 다시 나오면 그 뒤 release로 갱신한다.
6. 7음이 아예 없었다면 기존 absent-seventh 비용의 영역이므로 새 특징을 추가하지 않는다. 끝까지 울리고 있으면 0이다.
7. release 이후 3화음 구성음 세 개가 **양수 지속음의 union**으로 관찰되고, 그중 구성음의 소리가 run 끝까지 도달하는지 확인한다. 동시 수직 화음만 요구하지 않는다. 구성음이 부족하거나 마지막이 쉼이면 새 경계를 확정하지 않는다.
8. 박자 기준 1박을 분산 제시 허용치로 남긴다. 이후 남는 tail의 기준 박 수를 전체 선택 범위의 기준 박 수로 나눈다.

```text
feature = max(0, tail_beats - 1) / scope_beats
```

1박 허용치는 기존 진입 지연 특징과 대응하는 **검증할 설계 가정**이지, 교재가 모든 7화음은 정확히 1박 안에 끝나야 한다고 규정한다는 뜻이 아니다. 값은 7음 소멸의 관찰 증거이며, 화음 경계·비화성음 유형·기능을 확정하지 않는다. 7음 생략과 화음 연장은 여전히 가능한 대안이다. 근거에 source sound/note ID, 원 IR SHA, 실제 release, tail, 박자 환산과 availability를 보존했다.

path 전체에 미지원 부분이 있으면 whole feature는 `null`이고 알려진 partial sum을 별도 보존한다. unknown을 관측값0이나 학습 gradient로 바꾸지 않는다. 현재는 **가중치가 없고 기존 점수도 바뀌지 않았다.**

## 5. 전수 결과 — 제한적인 구별력

| 비교 | 결과 |
|---|---:|
| 기존 정답58의 승자 대 target | 58 모두 known·특징 차이0 |
| 오답44 중 양쪽 특징이 알려짐 | 34 |
| 그중 특징 차이가 양수 | **1** |
| 그중 특징 차이0 | 33 |
| 오답44 중 whole 특징이 미지원/unknown | 10 |

415run 중 3화음 등의 해당 없는 형태305, 끝까지 실제7음이 지속85, literal 지원 밖12, 7음이 아예 없음5, tail의 완전한 3화음 지지 없음4, 허용치 적용 가능한 tail4다. 마지막4 중 양수 값은 단1개다.

**기존 정답58의 비교 차이가0이라는 사실은 새 모델이 정답58을 모두 유지한다는 증명이 아니다.** 다른 경쟁 경로가 새 점수로 더 싸질 수 있다. 모든 기존 학습 경쟁 경로와 보호 대조를 새 특징으로 다시 계산하고 fresh 선택하기 전에는 정답 보호를 주장하지 않는다.

### 실제 사례 A — Chopin op.33-1, m33

사례 ID: `cont_647b3fc4ae89a8463ecf`, 원 시간 `[97,100)`.

- m33 첫 박에 F♯2와 E4/E5가 있다. E4/E5의 실제 sound는 quarter98에서 끝난다.
- 뒤 `[98,100)`에는 F♯–A♯–C♯의 3화음 구성음이 계속 나온다.
- 기존 승자는 전체 `[97,100)`를 F♯7로 골랐다. 저장 target은 `[97,98)` F♯7, `[98,100)` F♯ 3화음이다.
- 기존 absent-third/missing-member 비용은 전체 run의 union에 A♯이 한 번 나와도 줄어든다. 이 때문에 앞부분에서 3음이 생략된 7화음과 뒷부분의 완전한 3화음을 합치는 것이 싸질 수 있다.
- 승자-target 비용 차이는 `-1819/5000`이다. 구성음 지지 차이 `-169903/500000`, 복잡도/변화 차이 `-11997/500000`이 합쳐진 값이고, NCT/해결/새 역할 비용 차이는0이다.
- 새 특징은 승자 `1/3`, target0이다. 두 경로만 동점으로 만드는 계수는 `5457/5000` = 1.0914다. **이 계수를 선택하거나 학습한 것이 아니다.** 다른 모든 후보와 정답 보호를 고려한 전역 최적 선택도 아직 계산하지 않았다.

원음표와 음가, source note ID, 앞뒤4quarter, 전체XML/IR 경로를 [저장 사례](../../../output/harmony-large-error-triage-2026-10-06-r1/cases/cont_647b3fc4ae89a8463ecf.json.gz)에 연결했다. 원악보는 [전체 MusicXML](../../../output/source-locator-revision-trial-2026-09-30-r2/sources/a10b687fd43585ed8ac6/source.musicxml)이다. 현재 화면 엔진에 이 해석을 강제로 넣지 않았다.

### 실제 사례 B — Chopin op.33-4, m34–35의 기능적 근음 경쟁

사례 ID: `cont_a5c1112825ed79a485ba`, 원 시간 `[201/2,103)`.

- 구성음 F♯–A–C♯는 두 경로에서 같다. 기존 승자 분석 근음은 F♯이고, 저장 target의 기능적 분석 근음은 C♯이다.
- 기존 승자-target 비용 차이 `-3529/40000`은 기능적 역할 복잡도 차이만으로 생긴다. 구성음·NCT·해결 특징 차이는0이다.
- target의 기능적 6/4 run이 범위 끝103에서 끝나므로 다음 선택 화음의 해결 근거가 없다. 원전체악보의 quarter103 이후 음표는 보존돼 있다.
- 새 7음 소멸 특징으로 이 근음 경쟁을 해결할 수 없다. 기능적 6/4는 이 특징의 지원 형태 밖이므로 whole 비교가 `null`이다.

[저장 사례와 전체 원악보 연결](../../../output/harmony-large-error-triage-2026-10-06-r1/cases/cont_a5c1112825ed79a485ba.json.gz). 같은 곡의 m158 `[472,474)`에 있는 D♯표면 3화음 대 A♯기능적 근음 경쟁도 같은 분류에 들어갔다. 그러나 m158 뒤에는 추가 장식·성부 이동이 있으므로 m34의 해결 형태를 그대로 강제하지 않는다.

## 6. 산출물과 원자료 보존

기본 신규5파일:

- `src/musicanote_harness/harmony_member_release.py`
- `src/musicanote_harness/harmony_large_error_triage.py`
- `tests/test_harmony_member_release.py`
- `tests/test_harmony_large_error_triage.py`
- `scripts/validate_harmony_large_error_triage.py`

감사 보완 신규3파일:

- `src/musicanote_harness/harmony_large_error_audit_v2.py`
- `tests/test_harmony_large_error_audit_v2.py`
- `scripts/validate_harmony_large_error_audit_v2.py`

결과 정본: [report.json](../../../output/harmony-large-error-triage-2026-10-06-r1/report.json). 각118case는 과거 선택/target/계산 보류, 동일35항 비용 분해, 새 관찰·unknown, 전체XML/IR와 SHA, 원ID·철자·음가, 전후 문맥을 연결한다. 원주석을 human correction으로 승격하거나 Core를 수정하지 않았다.

## 7. 검사·실패와 정정

기본 새23검사 및 기존991검사를 포함한 **1,014관련 검사/97모듈 PASS**, failure0/error0, 153.451700초다. 전체repository의 모든 검사나 1,014곡의 음악 정확도가 아니다.

준비 과정에서 unknown-meter fixture를 잘못된 `None` 형태로 넣은1ERROR, 테스트 중 meter를 바꾼 후 기존 metric cache를 초기화하지 않은1FAIL을 수정했다. 박자 함수나 기존 봉인 코드는 약화하지 않았다. 보완 감사 테스트의 다른 TestCase 클래스 import로 검사가 중복 발견된 것도 module import로 바꿨다.

실제 추출은 118개와 report를 모두 저장했지만 마지막 재로드 감사에서 `ValueError: large_error_reload_summary_changed`로 exit1이었다. 함수 내부의 tuple과 JSON에서 복원된 list가 중첩 기능적 signature에서 비교된 것이 원인이다. canonical JSON 비교는 동일했다. **원5코드·118case·report를 덮어쓰거나 추출을 재실행하지 않았다.** [최초 실패](../../../output/harmony-large-error-triage-2026-10-06-r1/failure-v1.json)를 남기고 별도v2로 의미적 동일성·특징 산술·원sound/note 연결을 점검했다. 보완 patch 문맥 불일치1회도 있었으며 실제 봉인 코드 수정 없이 보완 파일 상태를 확인해 마무리했다.

[사후 감사v2](../../../output/harmony-large-error-triage-2026-10-06-r1/post-seal-audit-v2.json) PASS: 4,862고유 pin, 118record/23전체IR, 220path/415run, 정확한 특징 산술·실제 sounding release·원 note ID를 재확인했다. 이것은 새로운 feature의 음악적 정답 검증이 아니다.

기본23검사에 보완감사4검사를 더한 새27검사와 기존991을 모두 포함해 **최종1,018관련 검사/98모듈 PASS**, failure0/error0, 138.123512초다. 최초 단독감사 테스트의 중복 발견21개와 최종 중복 없는4개를 혼동하지 않는다. UI/서버/모델/Claude·MusicSearch·Music Composition/기존 tracked dirty5/Git은 변경하지 않았다. 외부 API·merge·commit·push0이다.

## 8. 봉인과 재현

| 산출물 | SHA256 |
|---|---|
| 단계93 report | `1527e7b0a513455243e0aba1d4ff05c705b4c2b79cd2209b095f22952e082f63` |
| 원실행 계약 | `ec576f9e27c8cf58094ead1bb1b11f63cfdcd3d3419cfbf87b8d175c76860b75` |
| 사후 감사v2 | `bbdbd9c56c24826efd2ec544261ff7de08983af4356be3c8915fb74f557fb9de` |
| 기본1,014검사 validation | `d3b1d2275dc010f8f955de890a8f11c19f546d5d1aa68f120956541792b682eb` |
| 최종1,018검사 validation | `9ad1ffc432ac09036a3a22abf2f72af39ae70e921c59df60261516255b5472d3` |

PowerShell, `K:\Music Analysis`에서:

```powershell
$env:PYTHONPATH='src;tests'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B -m unittest test_harmony_member_release test_harmony_large_error_triage test_harmony_large_error_audit_v2
```

원runner는 마지막 tuple/list 감사 실패까지 보존한 실행 이력이다. 다시 실행해야 한다면 원결과를 덮어쓰지 말고 새 output 경로를 사용하고, 의미적 감사는 별도v2를 호출한다. 원 단계91 report·모델·code pins가 맞지 않으면 보류한다. 앞으로 runner를 일반화할 때는 처음부터 JSON 의미 비교를 사용해야 한다.

## 9. 다음 개발 계약

1. 큰 오류의 근음/구성음 변화부터 검토한다. 7음 소멸 하나의 성공에 맞춰 전계수나 작품 경계를 조정하지 않는다.
2. 기능적 6/4의 다음 문맥을 label-free로 관찰할 수 있는 계약을 정한다. 악보의 실제 변화·유지 베이스·4→3/6→5·장식된 해결을 구별하고, 단순 같은 구성음만으로 기능을 확정하지 않는다. 범위 확장과 score/DP 계약이 바뀌면 새 버전으로 검증한다.
3. 구성음이 등장한 시점뿐 아니라 사라진 시점, 다음 분산 제시, 성부별 남는 외부음·가능한 해결을 공동 비교한다. 지속음 삭제·음가 축소·근음 추정 덮어쓰기는 금지한다.
4. 의미 있는 특징이 정리되면 기존 Train 활성대조·실제 오답 경쟁자·정답 보호 경로 전체를 재계산한다. 현재의 220승자/target 비교만으로 보호나 학습 준비 완료를 선언하지 않는다.
5. 필요한 제한 학습과 원118 fresh 공동 선택을 먼저 한다. 동일 후보·예산 아래 오답 교정과 정답 소실, 계산 보류를 따로 보고한 뒤 고정 Dev를 거친다. 새 독립 작품군 검증과 운영·편곡 연결은 그 뒤다.

이 파일은 화성 분석 **개발 문서**이며 구조 분석 로그나 인수인계 문서에 누적하지 않는다.
