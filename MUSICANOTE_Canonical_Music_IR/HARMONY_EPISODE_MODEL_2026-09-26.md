# 화성 문맥 사례와 유형별 판단 모델

## 목적과 구현 범위

사용자 요청: 사례 한 구간의 일치 여부보다 전후 마디, 진행, 음 형태와 분산 형태를 유형화하여 새로운 악보를 판단한다.

구현: `src/musicanote_harness/harmony_episodes.py`. 명칭은 `harmony-episodes-0.1.0`이다. 현재는 로컬 사례 검색을 유형별로 집계하는 설명 가능한 프로토타입이며, 신경망 학습이나 확률 보정은 수행하지 않는다. 기본 Viewer 엔진 교체 여부는 검증 이후 결정한다.

## 사례의 단위

각 episode는 다음을 보존한다.

- 주석의 정확 정렬된 중심 span [start,end).
- 중심 구간이 시작하는 마디의 직전 1마디부터, 끝나는 마디 뒤 2마디까지. 중간에 남은 마디 부분도 포함한다. 악보 처음·끝에서는 잘린다.
- 전후 마디의 sounding event ID, 원래 pitch spelling, rational 좌표, IR 파일 경로와 원본 악보 hash.
- 문맥에 겹치는 원자료 주석 진행과 annotation ID. 이는 reference 측 해설이며 query 특징 계산에 넣지 않는다.
- 화성 family, 적용 대상, 화음 종류, 전위, global/local key, 출처, 작품군, train/dev 구분.
- 원자료상 목표 도착 유형: 다음 주석에 도착 / 뒤 3개 주석 안에 지연 도착 / 조성 문맥 변경 / 관찰 범위 내 미도착 / 중첩 대상 보류. 이는 기보된 성부 해결을 입증하는 라벨이 아니다.

원본 주석과 Canonical IR은 기존 준비 package에 유지하며 episode는 이를 참조한다. 재현 시 source hash와 IR version을 확인한다. 복사한 음이름 목록만으로 원래 악보를 재생성하지 않는다.

## 현재 특징과 판단

1. 중심 시작 시점의 베이스를 고정 기준으로 사용한다. 전후 창 모두 같은 기준이므로 해결 목표가 바뀌면 특징도 바뀐다. 이조하면 특징은 유지된다.
2. before/current/after_0/after_1…을 나누어 duration-weighted pitch profile, attack-top contour, 정규화한 onset grid를 비교한다.
3. `block_chord`, `distributed_pitch_activity`, `sustained`, `sparse_or_mixed`를 관찰 형태로 기록한다. distributed는 아르페지오 확정 판정이 아니다. 짧은 음계 진행도 들어갈 수 있다.
4. 같은 화음이 수직형·분산형으로 제시되어도 pitch profile로 높은 관련성을 가질 수 있고, contour/rhythm은 차이를 보존한다.
5. train 사례를 비교해 화성 family별로 묶고, 같은 작품군에서 가장 비슷한 사례 하나만 기여하도록 한다. 상위 최대 3개 독립 작품의 평균을 유형 점수로 사용한다. 동일 작품군·주석 계보·score는 제외한다.
6. 유형 후보와 근거 case ID, 적용 대상, 형태, 비교 채널을 반환한다. 점수는 확률이 아니다. 2개 이상 독립 작품, 점수 0.75 이상, 경쟁 유형과 차이 0.05 이상, 전후 문맥 증거가 있어야 candidate로 표시한다. 이 임계치는 초기 가설이며 보정되지 않았다.

family 판단과 정확한 Roman numeral 판정은 다른 단계다. 현재 출력은 `applied_dominant_leading_tone` 등의 유형 후보이며 `/V`와 `/ii`의 선택까지 완료했다고 간주하지 않는다. 원본 표기를 그대로 새 악보에 복사하지 않는다.

## 발견한 데이터 정규화 문제

DCML은 `numeral=vii`, `form=o`, `figbass=7`처럼 성질을 별도 열에 보관한다. 기존 taxonomy는 numeral을 우선 읽어 일부 `viio7/V`의 quality marker가 빈 문자열이 된다. 이번 episode categorizer는 raw_fields의 form과 relativeroot를 우선 보존한다. 기존 라이브러리는 덮어쓰지 않는다. 전체 taxonomy 보정과 재발행은 다음 migration 항목이다.

## 검증 및 산출물

출력 위치: `output/harmony-episodes-2026-09-26/`.

- `episodes.jsonl`: train/dev 문맥 사례.
- `report.json`: 사례 수, 형태·family 분포, 실패 목록.
- `type-index.json`: train 사례만 사용한 family × 적용 대상 × 성질 × 주석상 도착 유형 × texture의 사례 색인.
- `dev-diagnostic.json`: family당 case ID 순 첫 4개 dev 사례의 표면 단독 대비 문맥 모델 비교. 계층별 진단 표본이므로 전체 분포의 정확도가 아니다.

평가에는 원자료 경계가 주어진다. 구간 자동 분할까지 포함한 전체 화성 분석 성능으로 해석하지 않는다. Holdout은 평가·튜닝하지 않는다. `training_eligible=false`는 유지한다.

실행:

```powershell
$env:PYTHONPATH='K:\Music Analysis\src'
.\.venv\Scripts\python.exe -m musicanote_harness.harmony_episodes --source output/dcml-batch-2026-09-24/pairs --case-library output/harmony-case-library-2026-09-25/harmony_case_records.jsonl --output output/harmony-episodes-2026-09-26
.\.venv\Scripts\python.exe -m musicanote_harness.harmony_episodes --evaluate --output output/harmony-episodes-2026-09-26
```

## 후속 개발의 우선순위

1. 후보별 실제 조성 기준을 세워 V/x와 vii°/x의 음 구성·spelling을 생성하고, 해당 x로의 즉시/지연 도착을 평가한다. 가까운 음으로의 이동을 실제 성부 해결과 혼동하지 않는다.
2. reference progression을 이용해 직접 해결, 중간 경과음·계류를 거친 해결, 연쇄 적용화음, 미해결, 공통음 감화음의 문맥 범주를 검증한다. 주석만으로 구별되지 않으면 unresolved로 남긴다.
3. voice별 attack sequence 정렬로 분산형 반복, 장식음 삽입, 음의 생략, 전위 차이를 비교한다. 현재 attack-top contour는 성부별 선율 분석을 대체하지 못한다.
4. 현재 절대 길이 비교 대신 박 단위의 강세와 화성 지속을 추가하고 다양한 context 길이를 dev에서 비교한다. 긴 지속음이 전후 프로파일을 지배하는 편향을 점검한다.
5. 추가 코퍼스는 정렬·출처·중복 계보 확인 후 별도 release로 확대한다. 자동 생성 주석과 검증 주석을 같은 가중치로 섞지 않는다.
6. 기존 combined_v0.3 검색과 동일 dev 표본·같은 반환 유형으로 비교 후 전체 dev 평가를 수행한다. 성능과 coverage가 확보되면 Viewer의 자동 분석 후보 평가에 연결한다.

## 개발 기록

- 2026-09-26: measure-context episode builder, 원본 주석 진행 보존, 공통 음높이 기준 특징, 관찰 texture 분류, 작품군별 증거 집계와 설명 출력, dev 진단 실행기를 추가했다.
- 이조 불변성, 서로 다른 해결 구별, 수직/분산 표현 비교, DCML 감화음 성질 보존, 동일 작품·holdout 배제, 조성 변경과 주석상 도착 구분 테스트 6개를 추가했다. 기존 harmony 관련 테스트와 함께 28개 통과했다.
- 실제 재구성: train 4,509 + dev 982 = 5,491개, 변환 오류 0. 적용화음 계열 712개. Block chord 2,975 / distributed pitch activity 1,587 / sparse-or-mixed 928 / sustained 1개.
- train의 복합 유형 색인은 206개다. 이는 검증된 음악 이론 유형 206종이 아니라 적용 대상·성질·주석상 도착·관찰 texture 조합의 관리용 bucket이다.
- dev 33개 유형별 진단: 표면 비교 family top-1 8/33(24.24%), 문맥 비교 12/33(36.36%), candidate 7개. 개선 방향의 근거일 뿐 채택 기준 통과가 아니다. 이 표본·집계 모델은 기존 982건 combined_v0.3 평가와 달라 직접 수치를 비교하지 않는다. 작은 표본과 낮은 정확도로 인해 Viewer 승격은 보류한다.
