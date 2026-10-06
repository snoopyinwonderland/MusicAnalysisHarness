# 단계84 — 35항 경쟁 비용 분해와 편곡 후보 계약

날짜: 2026-10-05. **새 학습/화음 탐색/정확도 향상/운영 적용이 아니다.** 단계83의 봉인된 35항 모델·원 source·후보 경로를 읽어 비용 산술을 분해하고, 참조 정답을 빼고 후보를 내보내는 연결 준비용 계약을 시험했다.

## 1. 요청과 판단

사용자는 계속 개발하면서 검증 여부와 Claude 편곡 시스템 연결까지 남은 일을 물었다. `K:\Music Composition`의 입력/ChordSpan/소비 모듈을 제공한 후, 연결하기 이르면 지금 하지 않아도 된다고 했다.

실제 Python 코드를 읽어 시간/Fraction·TPC·ChordSpan와 소비 지점을 확인했다. 시간은 일치하지만 국소 조성/기능/베이스·전위와 운영 선택 성능이 미완료다. **연결 및 추론기 교체를 보류했다.** 다른 프로젝트 파일/서버/브라우저/Git는 수정하지 않았다. `Voices That Care Melody.musicxml` 경로의 존재는 확인했지만 73–76마디의 해석/편곡 검증은 아직 하지 않았다.

연결 원칙·상세 필드·단선율 화성화와 관측 분석의 구별은 [화성→편곡 참고 계약](../HARMONY_ARRANGEMENT_REFERENCE_CONTRACT.md)에 기록한다. 이는 인수인계가 아니라 버전 관리하는 화성 개발 계약이다.

## 2. 변경 범위

- [harmony_score_balance_ledger.py](../../../src/musicanote_harness/harmony_score_balance_ledger.py): 기존26+문맥7+역할2, 각 value/known/partial sum/weight/cost 및7그룹의 합계. 상대 비용의 부호와 unknown을 분리한다.
- [harmony_arrangement_reference.py](../../../src/musicanote_harness/harmony_arrangement_reference.py): blind 경로3arm만 읽는 후보 exporter. 원 edge를 합집합 run으로 재현하고 source sound/note IDs·유리수·절대 철자/TPC·SHA를 남긴다. 정답/평가/annotation은 whitelist 밖이다.
- [build runner](../../../scripts/build_harmony_score_balance.py), [사후 auditor](../../../scripts/audit_harmony_score_balance.py), [회귀 runner](../../../scripts/validate_harmony_score_balance.py).
- [비용 검사10개](../../../tests/test_harmony_score_balance_ledger.py), [후보 계약 검사12개](../../../tests/test_harmony_arrangement_reference.py).

단계79–83의 code/model/report/주석/Core는 그대로다. 새로운7개 code/test/script는 Actual 시작 후 수정하지 않았다. 점수 계수를 바꾸거나 후보를 새로 탐색하지 않았다. Training proof가 새 역할 계수0으로 관찰되었던 부분만 같은 source 특징에 현재 고정2계수를 곱해 재생하며, 기존33과 특징값/원 경로는 바꾸지 않는다.

## 3. 산술 계약

각35항에 whole-path known과 실제 점수에 들어간 known-local 부분 합을 따로 저장한다. whole-path unavailable여도 기존 scorer가 known 부분을 점수에 사용한 것까지 삭제하지 않는다. 비교 gradient에는 두 경로 모두 known인 차원만 사용할 수 있다. nullable value를0으로 바꾸지 않는다.

`left_minus_right_cost = Σ[(left scored partial − right scored partial) × fixed coefficient]`.

양수면 left가 비싸고 음수면 left가 싸다. 이를 confidence/확률/정답률로 읽지 않는다. 모든 항 곱·기존26 subtotal·문맥7 subtotal·새2 subtotal·기존33/최종35 비용·그룹 합·대조 차이를 Fraction으로 검산했다.

그룹은 input uncertainty3, member support7, nonmember explanation5, parsimony/motion7, functional resolution4, context competition7, member-role interactions2로,35항을 중복 없이 나눈다. 그룹은 진단 표현이지 새로운 음악 이론/규칙이 아니다.

## 4. 실행 결과

Actual r1 **완료/exit0·13.161325초**. Stage83의 같은118Train범위/23전체 악장 source/15명명 작품군·원60,129edge를 참조했다. 이번에 원 graph에서 새 DP를 돌린 것은 아니다.

| 산출/검산 | 결과 |
|---|---:|
| 범위별 cost ledger | 118 |
| 상세 경로 비용 | 442 |
| blind3arm 대 stored target 비용 비교 | 324 |
| Train 대조 | 265 |
| positive margin violation | 196 |
| zero-loss 보호 대조 | 67 |
| 35항 known-both 비0 gradient가 있는 대조 | 198 |
| 후보 참고 JSON | 118 |
| 중복 제거된 blind 가설 | 132 |
| 연구 승자 없는 unresolved 범위 | 16 |
| 악장별 partial scope 색인 | 23 |

Margin 합은 `68836479936128163359/354426672600000000 ≈ 194.219243`로 원 모델과 정확히 같다. **196은 오답 구간 수가 아니다.** 손실/마진 조건을 아직 만족하지 못하는 training contrast 수다. 198은 학습 차이가 있는 대조이지 198곡/정답 후보 recall/성능 향상을 뜻하지 않는다. 같은 후보 union의 raw variant는 정답과 구별하여 보존한다.

현재 fresh 완료102경로는 stored target과 비용동률56, 더싼46이다. 이전 문맥104경로는 동률56/더싼47/더비싼1, 기존26 경로118은 동률58/더싼51/더비싼9다. **비용동률은 반드시 같은 해석/음악적 정답이 아니다.** 모두 현재35계수로 재생한 것이므로 기존26 arm의 과거 점수와 직접 섞지 않는다. 16보류를 제외한 결과로 전체 정확도를 만들지 않는다.

## 5. 실제 반례의 점수 원인

모든 비교는 현재 같은 모델에서 `해당 blind 경로 − stored training target`이다. 참조 target은 사후 진단용이지 생성 참고 자료에 넣지 않는다. 원 XML/전체 IR·source 음표 설명은 [단계83 실제 사례 §7–8](2026-10-05-member-role-interactions.md)를 함께 참조한다.

| 사례 / fresh 대비 target | 구성음 지지 | 비구성음 설명 | 단순성·이동 | 문맥 경쟁 | 역할2항 | 합계 |
|---|---:|---:|---:|---:|---:|---:|
| K280-1 A7 축소 | +.205695667 | 0 | −.119400800 | −.178173750 | +.031780875 | −.060098008 |
| Chopin op30-2 literal Bminor 유지 | −.329176444 | +.236355100 | −.059367700 | +.047513000 | +.097661667 | −.007014378 |
| Quartet op18-1 mv4 근음A 소실 | 0 | +.167675586 | −.164067250 | −.204964034 | −.183115625 | −.384471323 |

위 세 fresh 비교에서는 다른 두 그룹 차이가0이다. 소수는 표시용이고 실제 비교/학습은 유리수다.

1. **K280 A7:** 구성음 지지와 새 역할은 A7 유지 쪽에 도움이 되지만, 단순성/문맥의 분할 경로 이익이 더 크다. 새 역할만 임의로 올리는 답은 다른 근음 소실 사례를 악화시킬 수 있다. [35항 ledger](../../../output/harmony-score-balance-2026-10-05-r1/ledgers/cont_9a13eb950949fd01e0e7.json.gz), [정답 없는 후보 JSON](../../../output/harmony-score-balance-2026-10-05-r1/references/cont_9a13eb950949fd01e0e7.json).
2. **Chopin:** held Bminor에서 빠진 일부 구성음 지지를 요구하지 않는 이익−.329176444가 크고, 새 C♯ attack 교체 지지+.097661667만으로는 전이를 이기지 못한다. 앞 단계의 functional held negative를 이긴 것과 실제 literal winner를 이긴 것은 다르다. [ledger](../../../output/harmony-score-balance-2026-10-05-r1/ledgers/cont_9d29b21fdced352125a1.json.gz), [후보 JSON](../../../output/harmony-score-balance-2026-10-05-r1/references/cont_9d29b21fdced352125a1.json).
3. **Op18-1:** 새 지속 A를 교체 지지로 읽는 항이−.183115625를 주지만, 앞 A7에서는 A가 이미 구성음이고 실제 A2가 있다. 단순성/문맥과 함께 근음을 버린 대안을 싸게 만든다. 새 역할은 무조건 좋은 특징이 아니며 이 반례를 보호해야 한다. [ledger](../../../output/harmony-score-balance-2026-10-05-r1/ledgers/cont_2cb186940b3312c2a145.json.gz), [후보 JSON](../../../output/harmony-score-balance-2026-10-05-r1/references/cont_2cb186940b3312c2a145.json).
4. **K281-2 복구 유지:** fresh는 target과 합계차0, 이전/기존26 경로는 +.030100589다. 구성음 지지+.016222222/새 역할+.097661667이 단순성−.044641500/문맥−.039141800을 이겨 실제 교체를 복구한 사례다. 이 성공도 보존하며 전체 퇴행을 숨기지 않는다. [ledger](../../../output/harmony-score-balance-2026-10-05-r1/ledgers/cont_b495db380fce051abef0.json.gz), [후보 JSON](../../../output/harmony-score-balance-2026-10-05-r1/references/cont_b495db380fce051abef0.json).

## 6. 편곡 연결 준비와 보류

후보 파일은 3blind arm만 사용하며 원 source event와 run geometry를 재현한다. 검증용 target, Roman 정답, local key 정답, 평가 점수는 넣지 않았다. Model/source revision이 다른 후보에는 새 ID를 만든다. 마디 번호/곡 제목을 규칙 분기에 쓰지 않는다.

모든 파일에 generation_ready/production_adopted=false, alternatives_complete=false, unknown 조성/기능/전위/종지/NCT·성부 역할·반주 스타일을 명시했다. `musicomp_candidate`의 TPC는 **절대 C=0 fifths**이지 ChordSpan의 국소 tonic 상대값이 아니다. root가 literal member인 경우에만 tones 첫 위치로 정렬하며 functional root를 구성음으로 발명하지 않는다. bass=null/key=null/function=null을 그대로 유지한다.

23개 색인은 partial scopes를 묶는 탐색 편의물이다. overlap이 있고 whole_score_analysis=false라서 전곡 화음으로 이어 붙이는 것을 금지한다. 16보류에서는 옛 경로를 fresh 정답으로 승격하지 않는다. 운영 엔진/Claude/Phrase·Motif·UI/서버 변경0이다. 기존 화면 엔진이 화음을 표시하는 것과 이 새 연구 모델의 승격은 별개다.

## 7. 검사·실패·봉인·감사

신규22검사 최초 실행에서 비용 fixture의 속성명 `context_weights`를 실제 `weights`로 오인해9ERROR였다. fixture가 사용한 context 계수를 명시하여 바로잡았다. 음악 점수/원 decoder/봉인 부모 파일 수정은 없고, Actual 전에 신규22검사 모두 PASS였다.

최종 **891관련검사/82모듈 PASS·failure0/error0·93.073811초**. 저장된 Stage83 80모듈을 유지한 regression inventory이며 repository 전체 검사라는 주장은 아니다. 제품 연결/음악 정확도 검증도 아니다.

사후 감사는 **PASS·exit0·3,999고유SHA·442비용/324비교/265대조 산술/118후보/23색인 재현**을 확인했다. 저장된 최종 합계를 받아들이는 대신 원 Stage83 receipt의 관측값/known mask와 고정계수에서35항 비용/gradient를 다시 계산했다. Export는 whitelist 경로에서 다시 만들어 비교했다. 이 감사도 음악적 정답 판정은 아니다. 3,731input·261artifact·7code pins를 보존했고 Actual/사후감사 실패·중단0이다.

문서 작성 뒤3,999봉인 hash 변경0/새7Python UTF-8·AST·공백/새 계약·기록의23개 local link·문자 QA PASS를 재확인했다. 초안의 잘못된 과거 section anchor와 다른 언어 잔여1글자는 문서만 교정했다. 메인 문서/개발 로그의 최신 상태를 단계84로 갱신하고 이전 단계81 본문은 과거 기록으로 표시했다. `git diff --check` PASS이며 기존 tracked dirty5 외 새 tracked 수정은 없다. 큰 초기 status/과거 문서 조회 출력은 잘려서 필요한 구간과 compact JSON을 다시 읽었고 봉인 자료를 바꾸지 않았다.

| 산출물 | SHA256 |
|---|---|
| report.json | `11d86b722a55501b12fad5276e07bf433a669ced935e4148e432f6f6dc8d1173` |
| run-contract.json | `b6cd380419d921f51ceb5d43b74fbfe33c33bb0081d156ee1193dc42fc7d541d` |
| train-contrasts.json.gz | `868e220dcca4c970b039065e5b8bef66a500e0cb22027c9f9a99fadfafd24385` |
| post-seal-audit.json | `d981e52e741108f74e5ce5544fa610f6be387b355b37e808bf597360f69da748` |
| validation r1 | `b1e70c042ceb10dd4ecb1fc23c255ff56cd2b6642aa20a3d1a6ff841c766037f` |

[Report](../../../output/harmony-score-balance-2026-10-05-r1/report.json), [감사](../../../output/harmony-score-balance-2026-10-05-r1/post-seal-audit.json), [회귀](../../../output/harmony-score-balance-validation-2026-10-05-r1.json).

```powershell
$env:PYTHONPATH='src;tests'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B scripts/validate_harmony_score_balance.py --prior-validation output/harmony-member-role-validation-2026-10-05-r2.json --output output/harmony-score-balance-validation-REPRO.json
.\.venv\Scripts\python.exe -B scripts/build_harmony_score_balance.py --output output/harmony-score-balance-REPRO
.\.venv\Scripts\python.exe -B scripts/audit_harmony_score_balance.py --root output/harmony-score-balance-REPRO
```

이미 존재하는 output/report/audit는 덮어쓰지 않는다. 부모 모델/권한/출처/SHA가 달라지면 중단한다. 원음/출처주석/이전 봉인 파일·별개 tracked dirty5/MusicSearch/Composition/Git를 유지한다.

## 8. 다음 큰 단위

단계83의 다음 계획 중 **실제 경쟁 비용 분해**를 완료했다. 새2항만 올리는 학습을 다시 반복하기보다, 이 진단에서 확인한 중복/상쇄를 제한된 공동 균형으로 다룬다.

다음 실험은 별도 버전에서 시작한다. 사전 계약 후보는 구성음 지지·비구성음 설명·단순성/이동·문맥7·역할2의28계수만 조정하고, input uncertainty3와 functional resolution4는 고정하는 것이다. 각 계수는 초기 Stage83값의 ±1/20 신뢰 범위와 원 의미별 sign/bounds의 교집합 안에서만 움직인다. 원265Train 대조/67zero-loss 보호·known-both gradient·3epoch/전체 방문 평균·원 후보/Fraction/6raw/2M/완전 경로 계약을 유지한다. 실제 구현 전 use/source/weight 계약을 고정하고, 후보 부족/자원 보류를 계수 학습으로 해결했다고 읽지 않는다.

새 fixed model에서 ordinary fresh 선택을 다시 실행해야 하며, 저장 대조의 margin 개선만으로 채택하지 않는다. 범위 전체/공통 완료 및 새로운 wall/기존 정답 소실을 보고 고정 Dev에 간다. 독립 Test/공개 비교와 전체 Roman·국소 조성·전위/NCT/종지 검증이 남아 있으므로 이번 후보 파일을 편곡 추론기에 주입하지 않는다. 사용자 의견을 이유로 기존 순서를 버리고 편곡 인프라 작업을 확대하지 않는다.
