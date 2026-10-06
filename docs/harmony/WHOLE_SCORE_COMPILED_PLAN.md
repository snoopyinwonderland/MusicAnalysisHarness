# 단계101 — 측정 후 단일 최적화 비교 계약

기존 [단계 측정 계획](WHOLE_SCORE_PHASE_PLAN.md)의 후속이며, 진단을 보고 이번 비교 전에 확정했다. 진단2곡은60초 안에 끝나지 않았고473입력/코드해시가 보존됐다. Experience의 마지막 기록은1623셀 중571consume완료·검색37.221초·catalog12.894초·parse2.083초였으며 직접검산/압축에 도달하지 않았다. Walking은 parse가 아직 끝나지 않았다. profiler가 아닌wall time이며2동시 조건·checkpoint overhead를 포함한다.

## 이번 계산 변경

- 원 prefix 값과 고정계수의 유리수 분모 LCM으로 weighted integer prefix를 만든다. 비구성음4노출 비용을 원prefix 전체−해당 철자 구성음으로 계산한다. quantization/float/계수 변경은 없다. unknown/metric-unavailable는 원 정의와 같이 해당 항을 평가 불가로 남긴다.
- 빠진 구성음/역할·근음 지연·늦은구성음·조건부 NCT·조표항은 원 정의로 합산한다. 부재/후보를 삭제하지 않는다. conditional credit의 원 cap도 그대로다.
- 근음 문맥의 lowest는 원 sounding row sweep을 사용하고, 기준박 extent는 이미검증된 실제박 prefix를 사용한다. source root-loop는 같은 철자 원음표만 인덱스해 동일 원함수에 공급한다. 원행·성부·준비/해결·grace/repeat/history 관문을 바꾸지 않는다.
- **최종 UnitScorer는 단계99 원 직접 구현** 그대로다. 검색 weighted prefix/context cache를 직접검산으로 넘기지 않는다. 원논리의 무거운 legacy full-feature 검산도 이번에는 생략하지 않는다.
- 같은 전체catalog·원provider validation·source hash·beam8·2M·60초·source trace/tie/grace를 유지한다. 압축/parser/운영 코드는 바꾸지 않는다.

## 검증 및 종점

신규5+기존47=52검사PASS다. 양수/음수 weighted prefix·empty/unknown·모든 합성span/후보·변박·양수passing/준비된entry/root-return·직접검산·frontier/동점/손실·전곡catalog·부분보류를 검사했다. 최초검사1FAIL은 test에서한쪽만history_gate를누락해receipt의null/true가다른것이며 양쪽동일계약으로수정했다. 본실행전에만수정했고 음악코드는바꾸지않았다.

같은6곡에 control=계측단계100, engine=별도compiled를 각 한 번60초·4동시로 실행한다. 두 arm 모두20초 간격 stack trace와같은계측을켜 parser 지연과검색/검산을분리한다. 이trace는자동수정/부분제출을하지않는다. baseline은99봉인예측재사용이며 새측정속도로주장하지않는다. 기존100완료4와공통control완료곡은정확한경로/비용/특징/전체catalog가같아야한다.

결과고정후gold채점·해시감사·기록으로종료한다. 음악품질향상/234독립시험/공개모델우월성/UI/Claude연결은이번범위가아니다. 시간초과/오류/효과없음도그대로기록하며 계수/beam/timeout sweep/동일버전 재시도를하지않는다.
