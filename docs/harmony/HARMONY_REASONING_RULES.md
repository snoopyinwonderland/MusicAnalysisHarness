# 화성 진행·경계 추론 규칙 설계

설계 버전0.1 · 2026-09-30. 사용자 방향: 단순 음집합 비교로 해결하지 못하는 경우가 많으므로 상세한 규칙과 문맥 추론을 먼저 만들고, 필요하면 AI를 활용한다.

이 문서는 **구현할 규칙의 계약**이다. 모든 항목이 이미 분석기에 들어갔다는 뜻이 아니다. 구현/실험 상태는 [개발 로그](DEVELOPMENT_LOG.md)에 기록한다. 기존 교재의 세부 독해·코퍼스 출처 기록을 대체하거나 공개 복제하지 않는다.

## 1. 판단 대상부터 분리

동일 음집합, 동일 화음, 동일 전위, 동일 기능, 동일 조성 영역은 서로 다르다. 경계는 다음 유형을 경쟁 가설로 갖는다.

- 음표/배치만 변화: 같은 화음의 분산·옥타브·재타격·성부 이동.
- 장식 과정: 경과·보조·선행·계류 등으로 표면 수직음이 일시 변화.
- 전위/베이스 변화: 구성음 집합이 같아도 실제 베이스와 전위는 바뀔 수 있음.
- 화음 변화: 근음·화음 종류·추가음 등의 해석 변화.
- 기능 변화: 같은 음집합이 다른 국소 조성에서 다른 기능을 가질 수 있음.
- 조성 영역 변화: 일시적 tonicization과 지속적 modulation을 경쟁 해석으로 유지.
- 미정: 증거 부족, 원자료 이상, 성부 연결 불명, 후보 누락.

각 가설은 `context_span`(관찰 문맥), `evaluation_span`(설명량을 평가하는 범위), `segments`(문맥에 부여한 화음 진행)을 따로 가진다. 평가 범위 밖 음을 참고했다면 그 외부 화음도 가정임을 드러내며 몰래 확정하지 않는다.

## 2. 처리 순서

1. Core 검증: 실제 onset/release, tie, written/concert pitch, voice/staff, 마디 시간, 철자.
2. 정답을 보지 않는 후보 격자: attack/release 시각에서 경계 가능성을 열어 둔다. 음표가 시작했다고 화음 변화로 확정하지 않는다.
3. 연속한 여러 셀을 묶은 모든 허용 구간에 화음 후보와 철자 대안 생성. 한 셀짜리 해석과 긴 분산화음 해석을 동시에 보존.
4. 동일 문맥·동일 성부 연결 가정에서 여러 구간의 화음을 연결한다. 어느 경계든 인접 화음만 보지 않고 전후 여러 화음 진행을 대조할 수 있어야 한다.
5. 각 규칙이 지지/반박/미관측/판정 불가 중 무엇을 말하는지 기록한다. 해석적 결과를 Core 사실로 바꾸지 않는다.
6. 구조적으로 불가능한 가설과 증거가 약한 가설을 구별한다. 규칙 충돌과 대안이 남으면 보류한다.
7. 계산을 고정한 후 주석·사용자 사례와 대조. 적합하지 않은 범위, 페달/전위/양식 미지원은 정확도 분모에서 숨기지 않고 별도 보고.

## 3. 규칙 레코드 공통 계약

각 규칙은 다음을 명시한다.

| 필드 | 내용 |
|---|---|
| rule_id / version | 의미가 바뀌면 version 변경 |
| prerequisites | 필요한 관찰·철자·성부 연결·조성 가정 |
| targets | note/sounding IDs, 유리수 span, 해당 경계/진행 가설 ID |
| observations | 실제 관측값; 근음/베이스 가정과 구별 |
| supports / contradicts | 어떤 경쟁 가설을 어떻게 지지하거나 반박하는지 |
| withheld_reasons | 준비음 미관측, 성부 불명, 조성 미정 등 |
| dependency_refs | 다른 해석에 의존한 경우 그 가설 ID; 순환 의존 금지 |
| correlated_group | 같은 음표를 공유하는 근거를 독립 증거처럼 중복 합산하지 않도록 묶음 |
| counterexamples | 반드시 통과해야 하는 반례 fixture와 실제 사례 refs |
| source_refs | 기존 교재 개념 기록, 주석 출처, 사용자 피드백 구분 |
| state | planned / implemented / unit-tested / real-tested / reviewed / production |

처음부터 모든 rule에 임의의0~1 확률을 붙이지 않는다. 증거 강도/순위 점수/보정된 확률은 서로 다른 필드다. 성능을 측정하기 전 단순 설명량을 confidence로 사용하지 않는다.

## 4. 상세 규칙 묶음

### R01 — 시간·철자·음표 연결 신뢰성

- tie continuation은 새 attack이 아니며 실제 sounding span을 유지한다.
- printed measure 번호가 변해도 sequential index와 global quarter 좌표가 같으면 표시 변경으로 기록한다. 실제 시간 이동은 별도 migration 없이 결합 금지.
- 누락/모순 duration, 중복 source ref, 설명 불가능한 tie, 미확인 concert pitch는 분석 전 경고 또는 보류한다.
- 반례: pickup, X1 같은 비숫자 마디, cross-staff, 삼잇단음표, 반복기호의 written/unfolded timeline 혼동.

### R02 — 수직음과 펼쳐진 화음

- 수직 셀의 실제 active sounds와 구간 전체의 누적 구성음은 별개 근거다.
- 구성음이 처음 관측되는 시각, 지속 합집합, attack 수, 실제 최저음 흐름을 보존한다.
- 뒤늦게 등장한 구성음 때문에 그 화음이 앞에서도 존재했다고 자동 소급하지 않는다. 장식/분산형의 성부 연결이 그 소급 해석을 지지하는지 검사한다.
- 반례: 서로 다른 짧은 화음들을 합치면 우연히 완전한7화음이 되는 구간. 한 구성음 미관측만으로 rootless/생략화음을 자동 기각하지 않는다.

### R03 — 성부 연결의 복수 가설

- XML voice는 관찰상 그룹이며 대위적 성부의 확정이 아니다. staff 이동만으로 단절하지 않는다.
- 중첩/화음 내 다음 음이 여럿이면 복수 연결과 무연결 대안을 보존한다.
- 한 연결에서만 성립하는 해결은 assignment-dependent로 표시한다. 가장 가까운 음이라는 이유만으로 준비·해결 관계를 확정하지 않는다.
- 반례: 내성 이동, 한손 옥타브, 같은 onset의 chord notes, 타 성부가 대신 진행하는 경우.

### R04 — 경과·보조·반복 장식

- 철자상 진행, 실제 음정, 리듬, 같은 성부의 전후 지지음을 함께 참조한다.
- 가운데 음만 설명하는 조건부 근거로 저장한다. 세 음 전체를 지우거나 경계 밖 지지음을 임의 생성하지 않는다.
- 화음 후보가 바뀌어 가운데 음이 구성음이 되면 그 후보에서는 장식음 설명을 중복 부여하지 않는다.
- 반례: 같은 순차 음형이 실제 화음 변화를 포함하는 경우, 변화음을 지나가는 반음계 경과, 반복음 기반 리듬과 이중 보조음.

### R05 — 계류·선행음과 비동시적 화음 전환

- 한 음이 경계 이전에 시작해 이후까지 지속하는 것과 새로 attack하는 것은 다르다.
- 계류 후보는 이전 화음에서의 준비, 경계 이후 역할, 실제 해결, 성부 동일성, 음정·박절·양식 조건을 별도 확인한다. 하행2도 하나만으로 확정하지 않는다.
- 선행음은 도착 화음과의 관계뿐 아니라 직전 화음에서의 역할, 실제 재타격/지속 여부를 검사한다.
- 반례: 지속음이 양쪽 화음의 공통 구성음인 경우, 다음 화음 후보 자체의 근거가 부족한 경우, 지연된 변화가 여러 성부에서 엇갈리는 경우.

### R06 — 베이스·전위·페달의 분리

- 실제 최저음은 관찰값, 구조적 베이스는 해석이다. 구간 전체의 최저음 하나로 전위를 고정하지 않는다.
- 구성음·근음 후보와 해당 시각의 베이스 관계로 전위 후보를 만든다. 베이스가 비구성음일 가능성도 남긴다.
- 페달은 별도 역할 가설: 지속/재타격 패턴, 위 성부의 화음 변화, 양 끝의 화성 관계를 관찰한다. 페달 존재로 화음 유지·전위를 일괄 결정하지 않는다.
- 원주석 `pedal`을 일반 구성음에 흡수하거나 버리지 않는다. 페달은 악기 sustain pedal과 구별한다.
- 반례: I 페달 위 V43, 분산형의 낮은 이웃음, 같은 화음 안의 전위 변화, ostinato를 페달로 오인.

### R07 — 적용화음과 해결

- 조표 외 음은 적용화음만의 표지가 아니다. 비화성음·차용·전조·기보 철자 등 대안을 둔다.
- V/vii 계열 형태, 목표 화음에 대한 leading-tone/7음 등 성부 진행, 뒤 목표 화음의 실제 지지를 결합한다.
- 목표가 전위·분산형·지연 도착일 수 있으므로 바로 다음 수직 셀의 PC 집합만 확인하지 않는다.
- 반례: 형태만 같은 비기능적 진행, 목표 화음 근거 부족, false-positive I7, 적용화음 연쇄, 해결 회피. 목표 기능이 미정이면 조건부 관계로 유지한다.

### R08 — 국소 조성과 조성 변화

- key signature와 추론된 key를 구별하고 복수 국소 조성 후보를 유지한다.
- 국소 진행, 도착의 지속/반복, 특징적 변화음, 종지 근거를 여러 시간 규모에서 대조한다.
- 단일 적용화음으로 modulation을 확정하지 않는다. 조성 가설이 경계 판단에 사용되었다면 그 경계로 같은 조성을 다시 독립 입증하지 않는다.
- 반례: 동음이명 전환, 공통화음 pivot, 장단조 혼합, 짧은 tonicization.

### R09 — 박절·음가·화성 리듬

- 음가의 길고 짧음은 표기 박자·국소 리듬 밀도 대비로 기록한다. 고정 quarter threshold로 모두 판단하지 않는다.
- 강박/긴 음은 경계 가능성의 한 근거일 뿐 필수 또는 충분 조건이 아니다. 당김음/타이/선행음을 보존한다.
- 경계를 많이 넣으면 구성음 설명량이 늘어나는 효과를 따로 측정한다. 경계 수 비용이나 minimum duration을 쓰더라도 실제 빠른 화성 진행을 억압하지 않는 반례 평가 후 보정한다.
- 반례: 한 박 안의 여러 화음, 긴 페달, 강박의 계류, 약박에서 시작하는 화음.

### R10 — 반복·동형 진행·변형의 역할

- 리듬·성부 진행·철자/전위 변화를 고려한 대응 구간을 보조 근거로 사용한다.
- 반복 구간의 화성 해석을 복사하지 않는다. 마지막 종지 변화, sequence의 조성 이동, 장식적 변형을 다시 검사한다.
- 반례: 같은 멜로디에 다른 반주, 재현부의 조성 변경, 선율만 유사한 비관련 구간.

### R11 — 여러 화음 진행의 경쟁

- 하나의 넓은 문맥에서 유지, 한 번 변화, 여러 번 변화하는 path를 동일 음표·시간 셀로 비교한다.
- 관측 음표 설명, 베이스/전위, 성부 진행, 박절, 기능/해결을 분리된 evidence vector로 출력한다. 상충 근거를 숨기는 단일 총점만 내지 않는다.
- 긴 화음 가설의 지연 구성음/NCT 설명과 짧은 화음 연쇄의 기능 일관성을 동시에 평가한다.
- 모든 구간 조합을 무제한 전개하지 않는다. factorized lattice를 사용하고 향후 beam/DP 탐색의 가지치기 이유·제외 경로·예산을 기록한다. 현재 단계에서는 예산 초과시 보류하며 정답처럼 일부만 남기지 않는다.
- 반례: 화음별 과분할, 다른 화음들의 과도한 병합, 동일 화음을 여러 구간으로 복제한 경로, candidate coverage 부족.

### R12 — 종지와 구조 분석

- 국소 화성 진행·실제 종결 성부·박절·이후 계속 여부로 cadence 가설을 만든다. V 도착만으로 모든 곳을 HC로 확정하지 않는다.
- 프레이즈 결과는 독립 확인되지 않았다면 화성의 강한 근거로 쓰지 않는다. 화성에서 얻은 cadence가 구조 분석에 영향을 준 후 그 구조 분석을 다시 화성 근거로 재사용하는 순환을 막는다.
- 반례: 프레이즈 내부 V, deceptive/evaded cadence, elision, 단선율 자료.

## 5. AI를 추가할 때의 경계

AI는 선택적으로 **후보 제안·근거 비교·반례 탐색·사용자 설명 정리**를 맡는다. 다음 계약을 먼저 만족해야 한다.

- 입력: 제한된 앞뒤 Canonical events/유리수 시간, 후보 진행, 규칙별 관찰, 검색 사례의 provenance. 출처/권한/라이선스에 맞춰 제공하며 원책을 무단 외부 전송하지 않는다.
- 출력: 대상 note/span IDs, 후보 진행, rule refs, 지지/반박 이유, 모르는 조건, 대안. 존재하지 않는 음표 ID나 변경된 duration은 validator가 거부한다.
- AI가 만든 후보도 기존 후보와 같은 membership/시간/성부 검사를 통과해야 한다. 설명 문장이 그럴듯한 것과 음악적 검증은 구별한다.
- 모델 자체 confidence는 정확도 보장으로 쓰지 않는다. 모델·prompt·검색 index·규칙 버전을 기록하고 규칙 전용/AI 보조 실험을 같은 고정 집합에서 비교한다.
- 미지원 화음·조성/성부 불명·후보 충돌 등 명시적 escalation 조건에서 호출한다. 실제 비용·지연·품질을 측정한 뒤 운영 채택한다.
- 이번 구현에는 외부 AI API 호출, API key 설정, 학습 또는 fine-tuning이 없다. 모델 이름만으로 향상을 보장하지 않는다.

## 6. 구현 상태와 평가 문턱

현재: 관찰/후보 모듈과 공통 문맥 NCT 실험을 재사용한 **다중 구간 가설의 저장·계산 계약 prototype**과 고정 pilot 검사를 완료했다([개발 기록](records/2026-09-30-progression-context.md)). 이 문서의 R01~R12 전체를 하나의 최종 선택기로 통합한 상태가 아니다. 특히 pedal 역할, 기능/조성 공동 추론, 다중 path 순위/최적화, 독립 정답률, AI 통합은 후속 작업이다.

규칙별 최소 통과 조건:

R02/R06/R11의 관찰 부분은 [진행별 근거 벡터](records/2026-09-30-progression-evidence.md)로 연결했다. 실제 최저음과 membership/음가·지속·누적 구성음을 계산하지만 근음/구조적 베이스·페달·기능 판정은 여전히 미완료다. 관찰 벡터를 규칙 전체의 구현 완료로 세지 않는다.

후속 R06 구현은 [근음·조건부 전위·지속 베이스](records/2026-09-30-progression-bass.md)에 기록했다. 근음은 공급기 철자 대안에서 보존하며3/7화음의 실제 최저음에 따른 전위 후보를 낸다. 구조적 베이스와 페달의 최종 판정은 여전히 별도다.

R07의 다중 path 연결은 [목표 화음·해결](records/2026-09-30-progression-resolution.md)에 기록했다. 철자 기반 형태와 직접 성부 해결의 지지를 구별하며, 국소 조성/기능 확정과 지연 해결의 승격은 남아 있다.

R03/R07의 [명시적 다성부 연결](records/2026-09-30-progression-multivoice.md)은 원 IR 검증 후 유일하고 시간상 닿는 part/voice 연결만 별도 사용한다. 다성 XML voice의 음표 대응은 아직 해결하지 않았으며 최근접 pitch로 대체하지 않는다.

후속 [다성 표기의 부분 대응](records/2026-09-30-progression-polyphony.md)은 동일 part/voice의 완전 부분 대응을 보존하되 조합 한도 초과시 보류한다. 실제4/5표본이 한도에 걸렸으므로 최종 추론에는 성부별 후보와 해결 관계 제약을 분리한 계산이 필요하다. 후보 수를 신뢰도로 쓰지 않는다.

[해결 관계별 제약 검사](records/2026-09-30-resolution-constraints.md)는 직접 해결에 한하여 링크의 공동 존재성을 계산한다. 결과가 참이어도 성부/화음의 확정이 아니며, 여러 질의의 증명용 대응을 공동 일관성 검사 없이 합치지 않는다. 지연·비인접 해결과 전곡 최적화는 별도다.

[후보 관계 검사 확대](records/2026-09-30-candidate-relations.md)는 첫 후보 기술 경로 대신 모든 touching interval의 ordinary-family 형태 관계를 보존했다. 검사1,847개에서 동시음 전제 부족1,698개를 확인했다. 따라서 R02/R05/R07의 분산/지연 도착을 검증할 필요가 있으나, 단순 누적 pitch 집합으로 조건을 대체해서는 안 된다.

R02/R05/R07의 [시간 구성음과 지연 해결](records/2026-09-30-distributed-resolution.md)은 모든 구성음의 관측, 설명되지 않은 음/쉼에 대한 보류, 실제 같은 lane의 지속·동음 연결과 공동 해결 경로를 분리했다. 제한된 합성 양성/반례는 통과했지만 실제 양성은 아직 없으며, 생략 화음과 NCT 설명 부족을 해결한 것은 아니다. “동시음 부족” 중에는 시간 전체에서도 해당 구성음이 없는 경우가 많았으므로 타이밍만의 문제라고 해석하지 않는다.

[구성음·NCT 근거 감사](records/2026-09-30-missing-evidence.md)는 후보 구간 밖 부모 문맥의 음을 availability로만 저장하고 경계 확장의 근거로 승격하지 않는다. 미관측과 실제 생략을 구별하며 저장 NCT의 모든 requirement와 assignment를 대조한다. 조건부 호환/부분 음가/문맥 부족/충돌을 보존하고 서로 다른 assignment의 설명을 무조건 합치지 않는다. R06의 반복 베이스·페달과 경쟁 화음 검사는 후속 과제다.

R06의 [반복 최저음 비교](records/2026-09-30-repeated-bass.md)는 연속 재타격 관측과 같은 interval의 경쟁 화음 표까지 연결했다. 두 구간으로 복귀 anchor를 확인하지 않으며 페달/NCT 면제를 하지 않는다. 상성부 변화·세 구간 이상 복귀·경계 과병합·공동 assignment 판단은 아직 남아 있다.

후속 [세 구간 복귀 비교](records/2026-09-30-bass-return.md)는 모든 두-cut 분할의 membership 후보 조합과 bass 이외 실제음을 기록했다. 이는 관측 조합이며 공동 성부/기능 증명이 아니다. 모든 구성음 관측을 요구하는 좁은 clean 조건은 실제 생략 화음을 보류하므로 생략·경쟁 quality를 별도 가설로 표현해야 한다. 같은 목적으로 원음표를 추가하거나 미관측을 확정 사실로 바꾸지 않는다.

[ordinary3화음5음 생략 가설](records/2026-09-30-incomplete-triads.md)은 실제 근음/3음을 요구하고 미관측5음은 가정으로만 연결한다. 특징적 증감5음·근음·3음·7화음 생략은 같은 규칙으로 면제하지 않는다. 구현된 생략 모델의 범위와 음악적 가능성을 혼동하지 않고, 관측상 같은 미지원 후보도 대안으로 유지한다. strict와 assumption 조건의 통계는 분리한다.

[생략 가설·실제 성부 움직임 대조](records/2026-09-30-omission-voice-context.md)는 양쪽 경계의 critical motion과 반복 베이스 제약을 같은 부분 대응으로 검사한다. 보조음형 contour도 베이스와의 양립·다른 contour와의 분기/병합을 대조하되 NCT coverage를 부여하지 않는다. 실제 E→E♭를 기대한 E→F로 대체하지 않으며, 정보가 부족한 경쟁 quality를 탈락시키지 않는다. 부분 대응의 존재는 전체 성부/화성 확정과 다르다.

후속 R04/R11의 [동일 assignment 유지/변화 비교](records/2026-09-30-hold-change-and-validation-coverage.md)는 같은 셀·모든 원음·완전히 동일한 부분 연결 가정으로 관찰 membership과 조건부 보조음 설명을 대조한다. 실제 빈 assignment와 베이스만 강제한 가정을 구분한다. 서로 충돌하는 contour를 합쳐 설명량을 늘리지 않으며 sound 전체 화성 범위가 없으면 외부 문맥을 보류한다. 구성음은 NCT로 바꾸지 않고 미지원 장식음/페달/미관측음은 면제하지 않는다. 현재 대상은 기존 조건부 triple로 제한되어 모든 화성 path 순위나 독립 정확도 평가를 구현한 것은 아니다. 코드 테스트·구간·고유 악장·작품 가족·정렬 적격·사람 검수·음악적 정확도는 서로 다른 지표로 기록한다.

[편성·작품 범위 확대](records/2026-09-30-breadth-and-orchestral-readiness.md)는 라벨 없는 전곡 attack 목록에서 명시적 lane별 균등 index를 고정한다. 전체 part 근거를 보존하고 실패 구간을 쉬운 구간으로 교체하지 않는다. source hash·코드 테스트·입력IR 보존·주석 좌표·사람 검수·음악적 정답률을 분리한다. 큰 편성에서 written/concert 미구현이나 판본/time-grid 차이가 있으면 총보 화성 사용을 보류한다. 축약보 검사를 총보 검증으로 세지 않으며 근음 없는 증6후보의 표기를 위해 근음을 발명하지 않는다.

[성부 geometry 재사용과 source 조옮김 준비](records/2026-09-30-geometry-cache-and-source-transposition.md)는 구현 비용과 음악 해석을 구별한다. IR 전체 snapshot/hash·정확 Fraction span·구간 밖 성부를 보존하며 재사용은 기하 정보에만 허용한다. 후보/assignment/구성음/해결/보류/예산은 매번 검증하고 모든 고정 결과의 전체 JSON을 대조한다. 자동 재사용 가드는 같은 span의 계획된 조회 수만 사용하고 음악 라벨·정답·후보 삭제를 사용하지 않는다. source `<transpose>`는 원기보음에 한 번만 적용하고 철자와 정확 음높이를 교차 확인한다. 빈 값·중복·동일 정수 staff scope·중도 변경 등 모호함은 보류한다. 제한된 source-note probe 성공을 전곡 실음 정규화, 화성 정답 또는 자료 자격 승인으로 세지 않는다.

[실제 관계·source 문맥 감사](records/2026-09-30-relation-witness-case-audit.md)는 R02/R03/R05/R07의 증명 범위를 분리한다. 직접 연결의 부분 witness를 전체 구성음·NCT·전역 성부·기능의 정답으로 승격하지 않는다. 전체 구성음의 boundary/interval 관측과 미설명음을 따로 기록하고, 동일 정확 span의 모든 competing origin/보류를 보존한다. source trace의 grace/principal 오대응은 주변문맥 문제로 별도 보류하며, frozen IR 내부 연결 재검사와 XML 전체 onset/실음 인증을 혼동하지 않는다. 구성음 배열 순서는 형태 의미가 아니며 source exact-member set/target triad subset으로 검사한다. 실제 지연 양성이 없다는 사실을 알고리즘 불가능으로 해석하지 않는다.

[불변 source locator 수정 후보](records/2026-09-30-source-locator-revision.md)는 과거의 source location 오류와 음악 이벤트의 해석을 구별한다. 같은 pitch/onset만으로 장식음과 본음을 교환하지 않으며 duration/grace/tie와 독립 raw XML·physical measure 대응을 검사한다. 전수 매핑이 모호하거나 measure ID가 중복이면 부모 문서를 유지하고 보류한다. 수정은 새 document revision과 제한된 관찰 필드에만 허용한다. 기존 annotation은 자동 재지정하지 않고, 전체 보호 JSON의 타입/배열 순서/ID/음가/성부/타이를 유지한다. source voice hint 차이·logical lane의 raw voice 혼합·실제 witness endpoint의 source voice 일치를 서로 다른 감사로 보존하며 어느 것도 실제 대위법 성부 또는 화성 정답 인증으로 승격하지 않는다.

[전체 source sequence와 physical measure 진단](records/2026-09-30-source-sequence-and-physical-measures.md)은 음표뿐 아니라 쉼표·raw chord marker·정확 유리수 cursor·전체 명시적 lane 순서를 보존한다. pinned parser의 fingerprint/ID 재현을 개별 occurrence의 독립 인증으로 승격하지 않는다. 동일 반복은 order-only 불확실성을 유지하고, 과거 locator·hash 정렬·앞 voice 상속으로 모호함을 덮지 않는다. printed label과 physical ordinal/sequence index를 분리하며, old measure ID가 중복되면 qualified alias에 sequence index를 요구한다. alias는 진단만 저장하고 기존 annotation의 bare-ID retarget을 금지한다. 마디 오른쪽 끝 grace는 global time이 다음 마디 시작과 같아도 source physical membership을 유지한다. local onset 오류는 globaltime/pitch/duration과 분리해 별도 revision으로 교정해야 한다. 전체 raw event cardinality와 공급된 parent observations coverage, partwise measure 수와 score-grid 수, 원 XML voice와 실제 대위법 성부를 각각 구별한다.

1. 구성 fixture: 참/거짓/정보 부족 각각, 조옮김과 마디 번호 변경에 동일 원리.
2. 시간·source 보존: 음 삭제/중복 계산0, 경계 삽입만으로 동일 화음 설명 변화0.
3. 실제 사례: 주석 정렬과 지원 범위 검사; 불일치도 사례로 보존.
4. hold/change/inversion-only/pedal/secondary/NCT/ambiguous를 따로 보고하며 같은 곡의 중복 표본을 독립 곡 수로 세지 않는다.
5. 개발에 본 곡과 독립 작품군 분리. 음악적 검수 전 gold 승격 금지.
6. 운영 적용 전 기존 구조 분석 회귀·렌더링·응답 시간·보류율 검사.

사용자 피드백은 앞뒤 재현 가능한 악보/IR, 원문 설명, 경쟁 해석, 수정 규칙, 양성·반례 테스트와 함께 저장한다. 특정 곡의 마디 번호를 조건식으로 넣지 않는다.

## 7. 큰 기능 통합과 국소 보류의 운영 원칙

[공통 화성 문맥 통합](records/2026-09-30-context-integration-and-measure-revision.md)은 R02/R04/R06/R07/R11의 기존 근거를 같은 exact interval/reading key에 연결한다. raw 구성음/미설명 음가, 조건부 NCT, 미관측 구성음과 생략 가정, 실제 최저음/전위, 직접·시간 해결과 경쟁 origin을 구별한다. 서로 연관된 근거를 독립 투표로 합산하거나 대안의 설명을 합쳐 정답을 만들지 않는다. 새 인덱스의 완전성과 음악 해석의 완전성은 다르다.

완전한 path와 동일 assignment를 명시한 경우에만 진행 evidence/bass/resolution을 함께 사용한다. subset evaluation span과 전체 context resolution scope를 기록한다. 자동 첫 후보/국소 주석 key/최종confidence를 추가하지 않는다. 저장된 관계 계획 중 예산 보류된 질의를 실행한 것처럼 세지 않는다.

IR의 확인된 physical measure ID/label/local onset은 새 revision에서 제한 교정하되 source locator/extension/annotation binding은 별도다. qualified alias 없이 bare ID를 retarget하지 않는다. 이 후보의 소비 범위는 note/rest/measure Core뿐이며 parent-bound 잔여 참조를 새 document의 독립 근거로 사용하지 않는다.

음표·시간·ID 오류나 참조 누락이 영향을 받는 계산을 무효화하면 먼저 해결한다. 장식/성부/quality 미지원은 해당 근거 범위에 보류로 남겨 다른 지원 구간의 큰 기능 개발을 막지 않는다. 이 원칙은 필요한 검증을 생략하거나 예산 보류를 정답으로 바꾸라는 뜻이 아니다. 상세 사례의 중요도와 현재 기능 단계는 개발 기록에서 분리한다.

## 8. 완전 진행 제안 탐색과 공동 비교

[여러 완전 진행의 탐색과 비교](records/2026-10-01-progression-search-and-joint-comparison.md)는 공통 문맥의 모든 interval/철자 후보를 사용하되 계산 제안과 음악적 선택을 분리한다. provider origin·근음 철자/provenance·구성음·보류·원음 상태가 같은 계산 그룹은 모든 출처를 보존하고 대표 adapter를 음악적 선호로 쓰지 않는다. 철자 미지원 후보를 임의 근음/철자로 채우지 않는다.

탐색에서는 exact raw 비구성음 음가와 optimistic local NCT bound를 구별한다. 국소적으로 가능해 보인 음형은 전체 path·하나의 assignment에서 다시 검사해야 하며 그 전에는 음가 면제가 아니다. 겹치는 설명은 같은 셀·실제음별 시간 합집합을 사용한다. 원시 membership/낙관적 bound/보류 노출의 별도 retention과 segment 수별 제안으로 한 점수의 과분할 선호를 제한한다. 미관측 구성음 개수는 분산형 과분할을 보상할 수 있어 탐색 목적에서 제외하고 origin별 진단으로 보존한다.

모든 완전 path는 공통 문맥 전체를 `[start,end)`로 연속하게 덮어야 한다. partial path를 성공으로 출력하지 않는다. prefix dominance/state·transition·segment·완전출력 상한의 제외는 근사 누락으로 기록한다. 정확한 stored vocabulary 경로 수는 실제 평가 수도 모든 음악적 해석의 수도 아니다. 후보 순서·개수·탐색 통과를 confidence나 정답으로 쓰지 않는다.

공동 평가는 모든 제안×모든 저장 assignment를 계획하며, 쌍별 delta는 **동일 assignment** 안에서만 계산한다. 모든 원음/유리수음가·조건부NCT·보류·실제최저음/조건부전위·미관측/생략경쟁·동일성부해결을 보존한다. explicit-IR witness와 sampled assignment의 연결을 합쳐 비구성음을 면제하지 않는다. 구성음 합집합 완전성을 분산화음 확정으로, 같은 구성음을 기능/근음/전위 동일성으로 바꾸지 않는다.

더 많은 경계와 함께 raw membership가 증가하더라도 정확도 향상이나 승자로 해석하지 않는다. 같은 구성음 단순 분할의 원음가 불변성을 검사하고 음악적 경계 증거는 후속 조성/해결/박절/음형과 대조한다. assignment/evaluation 상한은 해당문맥 전체평가 보류, pairwise상한만 넘으면 모든평가보존/쌍비교만전체보류다. 유리한 가정·경로쌍만 골라 보류를 숨기지 않는다. 현재selected/preferred=null과no-confidence 계약은 최종추론/검수/운영승격 이전까지 유지한다.

## 9. 경쟁3화음·7화음과 전략 범위 — 구현된 일부 정책

[단계45](records/2026-10-04-triad-seventh-obligation-policy.md)의CP01~CP07은 R02/R03/R04/R07/R11의 일부를 saved progression evidence 소비 정책에 연결한다. 같은 source/key/bundle/partition과나머지slot가정에서정확한triad→seventh변화를대조하고,추가7음의literal occurrence·3화음아래조건부설명/미설명음가·7화음의ordinary경로를함께보존한다. Adjacent function 가정 변화는 별도 명시한다.

3화음이의무가적다는이유로유리하지않고7음관측만으로7화음을확정하지않는다. 실제연결의첫불리한변화를건너뛰지않으며,미연결source이후같은raw lane의음이재등장하면그이후실제route를**진단만**저장한다. 중간edge·실제쉼·음악적성부를추정확정하지않고ordinary/NCT credit은추가하지않는다. Source guard·미연결·target nonmember·adverse motion은동시발생가능한축이다. Full hold의내부function은not applicable이지vacuous성공/유지실패가아니다.

이구현은새authority나최종selector가아니다. 전체key/경계최적화·생략/분산형시간근거·ordinary외지연전략·종지확정은여전히남아있다. 원소나타의원2,315후보·각1,395쌍검사는음악적독립정답률이나전곡성능으로환산하지않는다.
