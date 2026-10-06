# 단계98 — 전곡 과병합의 고정 경로 비용 진단

2026-10-06. 별도 화성 개발 기록이다. 새 정확도 시험이나 재학습이 아니라 단계97의 저장된 경로를 분해했다.

## 이번 결론

`Family Of The Poor`에서는 **점수 자체가 더 나은 기준선 진행보다 전곡 한 화음을 선호하는 문제**를 확인했다. beam 확대만으로 이 대조의 문제를 해결할 수 없다. 확장화음에서 평가하지 못하는 역할 특징도 확인했다. 다만 다른 두 곡은 source 철자 변환의 불확실성으로 대조 비용을 확정하지 않았다. 전체 실패 원인이 하나라고 주장하지 않는다.

다음 큰 구현 항목은 **전곡에서 일관된 점수 단위와 후보 지원 범위**다. 기존 계수에 특징 하나를 추가하는 실험이 아니다. 운영/화면/Claude 연결은 계속 보류한다.

## 구현과 범위

- [고정 경로 진단 모듈](../../../src/musicanote_harness/harmony_whole_score_diagnosis.py)
- [실행기](../../../scripts/diagnose_harmony_whole_score.py)
- [신규8검사](../../../tests/test_harmony_whole_score_diagnosis.py)
- [사전 실행·다음 점수 계약](../WHOLE_SCORE_OBJECTIVE_SPEC.md)

대상은 단계97 공통 완료3곡 전부다. source IR·음표 refs·원 Fraction 셀을 검증하고 같은 repeat/history 정책으로 기존26 직접 비용을 재계산했다. **3곡 모두 원 승자 비용이 정확히 일치했다.** baseline은 이미 봉인된 출력만 읽었다. gold/주석을 읽거나 새 화음을 생성하지 않았다.

baseline의 PC 화음은 원 source에서 관찰된 근음 철자와 정확한3/7화음 template가 유일할 때만 변환했다. gap/셀 안에서 다른 화음으로 변경/철자 불확실성이 있으면 비교 불가로 남겼다. bass 변화는 별도이며 무음 셀만 기존 signature를 유지한다. 원 provider blocker를 그대로 둔다.

이것은 **반사실적 경로 비용**이다. 이 경로가 원 후보 정책/beam에서 끝까지 도달 가능한지는 검증하지 않았다. 후보를 기존 decoder에 주입하거나 baseline이 기존 엔진의 실제 선택이라고 보고하지 않는다.

## 핵심 수치

비용은 낮을수록 좋으며 확률이 아니다.

| 곡 | 원 선택의 실제 화음 run | 원 선택 비용 | baseline 대조 비용 | 비교 상태 |
|---|---:|---:|---:|---|
| Family Of The Poor | 1 | 0.867461 | 8.004942 (115run) | 유일한 철자로 전 경로 비교 가능 |
| It_S A Small World | 4 | 0.867279 | 미확정 | 50–52quarter의2셀은 관찰 근음 철자 기반 template 없음 |
| Reach For The Stars! | 12 | 0.677499 | 미확정 | 21셀에2개 철자 대안; 임의로 고르지 않음 |

Family의 정확한 비용은 선택 `695269613/801500000`, baseline 대조 `10008899394223/1250340000000`이다. baseline의 비용 중 아래 네 항이 **7.781004**, 전체8.004942의 **97.20%**를 차지한다.

| 횟수/변경 비용 항목 | baseline 비용 |
|---|---:|
| harmonic_run_count | 2.438920 |
| member_turnover | 2.074933 |
| unanchored_change | 2.031536 |
| root_motion_distance | 1.235616 |

음표 부적합 비용(nonmember_exposure)은 baseline **0.059833** 대 원 한화음 **0.122901**이다. 더 적은 원음표 부적합이 있어도 횟수 벌점이 대조 순위를 뒤집는다. baseline은 참조 정답 그 자체가 아니며 115run이 최적이라고 주장하지 않는다. 이전 채점에서 Family의 baseline triad55.00% 대 원 선택13.33%였다는 개발 결과와 함께 읽는다.

현재 run/전이 횟수 항은 구간이 늘어날수록 누적되지만 다른 많은 특징은 전곡 시간/note-time으로 나뉜다. 국소 모델의 가중치를 전곡에 그대로 적용하는 단위 불균형을 고쳐야 한다. 단위 검사에서는 정규화 분모만2배로 바꾸면 같은 국소 nonmember 노출 값이 절반이 되지만 run-count는 그대로임을 확인했다. 이 검사는 정규화 산술의 단위 대조이며 새 XML/곡 추가의 음악적 회귀 시험은 아니다.

## 확장화음과 후보의 국소 지지

Family의6음 후보에서는 다음4특징을 평가하지 못했다.

- absent_third_exposure
- absent_altered_fifth_exposure
- absent_seventh_exposure
- late_identifying_member_exposure

`harmony_support_balance.roles`의3/7화음 shape 매칭에 해당하지 않기 때문이다. 값은 null/평가 불가이고 현재 고정 점수는 이를 비용에 더하지 않는다. **원가중치나 계산 버그를 수정한 것이 아니라 적용 범위의 한계**다. 이미 extra_member_complexity0.580371 비용이 있어 확장화음이 완전히 무벌점인 것은 아니다. 그러나3/7화음의 역할 검사를 확장화음까지 수행했다고 말할 수 없다.

Family의0–182quarter 한run은45page를 통과한다. 그 중4page에서는 근음이 관찰되지 않고,37page에서는 후보 전체 구성음이 관찰되지 않는다. Small World의56–194quarter 넓은run은35page 중6page 근음 부재/34page 전체 구성음 미관찰이다. **이 관찰만으로 화음을 금지하거나 page마다 경계를 강제하지 않는다.** 분산화음·생략·페달의 유효한 가설도 있기 때문이다. 원음표·실제 음가·철자와 page별 관찰을 JSON에 남겼다.

3곡의 key_signature_foreign_member도 평가 불가였다. 재로드된 Family 첫 마디의 조표 fifths는 null이다. IR의 미확인을 임의의 조성으로 채우지 않았다. XML 자체 조표 누락이나 parser 오류 여부를 이번 결과만으로 단정하지 않는다.

## 다음 점수 계약의 방향

[계약 초안](../WHOLE_SCORE_OBJECTIVE_SPEC.md)은 다음을 요구한다.

1. 국소 source 적합도와 화음 변경/해결을 공통 기준박 단위의 비용으로 만들고, 표시용 전곡 평균은 모든 항을 합산한 뒤 동일하게 적용한다.
2. 같은 독립 구간을 반복해도 상대적 비용이 무너지는지 먼저 검사한다. 기존26 숫자를 그대로 쓰더라도 의미가 달라지므로 새 점수 버전이지 고정 모델과 동등한 변환이 아니다.
3. 확장화음의 null 역할 검사를 ‘문제 없음’으로 읽지 않는다. 지원되는 후보군과 별도 지원이 필요한 후보군을 구별한다. 아직 충분한 근거가 없는 확장화음을 생성용 확정 결과로 승격하지 않는다.
4. 후보가 처음 제시된 위치와 이후 지속 가설을 구별하고, 후속 구성음·해결·근음/베이스와 새 진행을 비교한다. 단순히 한 번 관찰한 음을 전곡 근거로 쓰지 않는다.
5. 실제 화음 run, bass/전위 변화, 제출span을 따로 평가한다. 다음 prototype은 합성 반복 검사와 고정6곡 개발 비교 한 번으로 종료하고, 채택 판단 없이 추가 계수/전수 감사 루프를 열지 않는다.

**새 점수 prototype의 추론 실행은 아직 하지 않았다.** 이번에는 문제의 분리·재현 코드·다음 계약을 완료했다. 따라서 정확도 개선 수치나 후보 recall/beam 손실률을 새로 보고하지 않는다.

## 검증·보존·재현

진단 본 실행2.450536초/exit0, 사후480해시PASS·불일치0이다. 신규8+기존전곡7+채점11=**26검사 PASS**, failure/error0. 원234시험과6곡 pilot, 기존모델/고정코드, 원XML/IR/주석, MusicSearch/Composition/UI/서버·Git을 변경하지 않았다. 사전부터 있던 tracked dirty5도 그대로다. 학습/새decoder/계수 변경/프로세스 재시도/운영 적용/Claude 연결/commit/push0이다.

초기 소스 탐색의 Windows wildcard/없는 파일 경로 오류는 읽기 명령만 실패했으며 디렉터리·파일 필터로 정정했다. 신규 검사와 진단 실행 자체 실패는0이다. 두 곡 대조 미확정은 오류를 숨긴 것이 아니라 철자 변환 계약의 의도된 보류다.

산출물: [diagnosis.json](../../../output/harmony-whole-score-diagnosis-2026-10-06-r1/diagnosis.json), [freeze.json](../../../output/harmony-whole-score-diagnosis-2026-10-06-r1/freeze.json), [audit.json](../../../output/harmony-whole-score-diagnosis-2026-10-06-r1/audit.json).

- diagnosis SHA `7577dc21448383b695325a0ace9c1a0897ae32bf595283deb1a28cc684c45512`
- audit SHA `5f826c339decff548c20d128787661a919b9ce061d877846f567e070c89cbefb`

재현: `PYTHONPATH=K:\Music Analysis\src`에서 `K:\Music Analysis\.venv\Scripts\python.exe -B scripts/diagnose_harmony_whole_score.py --output <새 폴더>`를 사용한다. 기존 출력이 있으면 덮어쓰지 않는다. 새 inference/gold 읽기는 없다.
