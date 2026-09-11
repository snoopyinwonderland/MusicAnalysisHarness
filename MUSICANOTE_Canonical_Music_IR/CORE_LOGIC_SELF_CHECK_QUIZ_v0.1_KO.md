# MUSICANOTE 핵심 논리 이해·합의 점검 퀴즈 v0.1

## 목적

이 퀴즈는 음악 이론 실력을 평가하는 시험이 아니다. 현재 MUSICANOTE가 채택한 데이터 계약과 Phrase 분석 원칙을 사용자가 의도한 음악적 판단에 맞게 구현하고 있는지 확인하는 합의 도구다.

정답을 보기 전에 각 문항에 답하고, 확신도를 `높음/중간/낮음`으로 함께 적는다. 설계와 다른 답도 중요한 피드백이며, 반드시 오답으로 취급할 필요는 없다.

답변 예시: `1-B(높음), 2-C(중간), ... / 17: 이유...`

## A. Canonical IR과 분석 계층

### 1

MusicXML에 C4–E4–G4가 같은 onset으로 기보되어 있다. Canonical Core가 저장해야 할 가장 적절한 내용은?

- A. `chord = I`
- B. 동일 onset의 notated chord group과 각 음의 pitch spelling
- C. `tonic_function = true`
- D. `cadence = authentic`

### 2

4마디 마지막 C4가 5마디 첫 C4에 tie로 연결되었다. 가장 적절한 표현은?

- A. 두 notated note를 삭제하고 하나의 note만 저장한다.
- B. 두 note와 두 attack을 저장한다.
- C. 두 notated note, 하나의 tie chain, 하나의 sounding event와 하나의 attack을 저장한다.
- D. tie는 화면 기호일 뿐이므로 분석 데이터에서 제외한다.

### 3

Phrase가 4마디 1박에서 시작해 5마디 1박 직전에 끝난다. 공통 시간 규칙으로 맞는 것은?

- A. `[m4:b1, m5:b1)`
- B. `[m4:b1, m5:b1]`
- C. `m4`만 저장한다.
- D. 시작과 끝 음표 ID만 저장하고 시간 좌표는 두지 않는다.

### 4

조표가 샵 세 개일 때 Canonical Core가 확정할 수 있는 것은?

- A. A major
- B. F# minor
- C. A major 또는 F# minor 중 하나
- D. 샵 세 개라는 key-signature observation

### 5

F#4와 Gb4를 같은 MIDI 66으로만 저장하면 안 되는 주된 이유는?

- A. 재생 속도가 달라지기 때문이다.
- B. 기보상의 spelling이 화성·성부진행 해석의 증거가 되기 때문이다.
- C. MIDI가 옥타브를 표현하지 못하기 때문이다.
- D. MusicXML이 MIDI를 지원하지 않기 때문이다.

### 6

`metric_strength=weak`와 `nct_type=passing_tone`의 올바른 위치는?

- A. 둘 다 Canonical Core
- B. 둘 다 Human Annotation
- C. 전자는 deterministic evidence, 후자는 Analysis/Annotation
- D. 전자는 Analysis, 후자는 Canonical Core

## B. Phrase 경계와 반복 구조

### 7

경계 index `i`가 음표 `i` 직전을 뜻할 때 기본 Phrase span은?

- A. 앞 Phrase와 뒤 Phrase가 모두 음표 `i`를 포함한다.
- B. 앞 Phrase는 `i-1`에서 끝나고 뒤 Phrase는 `i`에서 시작한다.
- C. 앞 Phrase가 `i`에서 끝나고 뒤 Phrase는 `i+1`에서 시작한다.
- D. 항상 마디선으로 이동시킨다.

### 8

일반 경계 막대에 `P1│P2`라고 쓰지 않고 `P2 시작`이라고 쓰는 이유는?

- A. Phrase 1을 화면에서 숨기기 위해서다.
- B. 막대가 P2의 조성을 뜻하기 때문이다.
- C. 일반 `[start,end)` 경계가 공유 음을 뜻하지 않기 때문이다.
- D. Phrase 번호는 분석과 무관하기 때문이다.

### 9

실제로 한 음이 두 Phrase에 모두 속한다고 판단하려면?

- A. 일반 boundary index만 있으면 된다.
- B. 두 Phrase의 명시적인 overlap span 또는 경쟁 가설이 필요하다.
- C. 같은 음높이가 반복되면 자동 overlap으로 본다.
- D. 마디 첫 음이면 항상 공유한다.

### 10

짧은 음형이 비슷한 리듬과 윤곽으로 여러 번 반복되고 각 cell 사이에 짧은 쉼이 있다. 현재 v1.2의 기본 판단은?

- A. 모든 쉼을 독립적인 primary Phrase 경계로 확정한다.
- B. 쉼을 삭제한다.
- C. 전체 repeated run을 primary 후보로 보고 내부 쉼은 subphrase-cell 증거로 보존한다.
- D. 반복되는 음은 모두 하나의 sounding event로 합친다.

### 11

현재 Phrase 5에 적용된 rhythmic-gesture rule의 핵심 조합은?

- A. 같은 절대 음높이와 같은 마디 번호
- B. 동일한 가사와 대문자 시작
- C. 유사한 정규화 pickup 리듬과 내부 쉼보다 훨씬 큰 뒤쪽 종결 공백
- D. 마지막 화음이 반드시 I인 경우

### 12

두 gesture의 앞 세 음 리듬은 비슷하지만, 뒤쪽 공백이 내부 공백보다 충분히 크지 않다. 현재 규칙은?

- A. 무조건 하나의 Phrase로 합친다.
- B. rhythmic-gesture merge를 발동하지 않는다.
- C. 두 gesture를 삭제한다.
- D. 가사가 있으면 합치고 없으면 나눈다.

### 13

반복 run 내부에서 강한 PAC가 검출되었다면 향후 가장 적절한 처리 방식은?

- A. 반복 규칙이 항상 우선하므로 PAC를 버린다.
- B. PAC가 있으면 반복 증거를 삭제한다.
- C. 내부 경계 복원 가설과 전체 run 유지 가설을 evidence·confidence와 함께 경쟁시킨다.
- D. Canonical Core의 음표 객체에 최종 Phrase 번호를 덮어쓴다.

## C. 가사·화성·사람 피드백

### 14

KYSing 가사 자료를 사용하는 현재 목적에 가장 가까운 것은?

- A. 운영 분석 때 가사 문장 끝을 그대로 Phrase 경계로 사용한다.
- B. 가사가 있는 구간에서 호흡 위치와 함께 나타나는 음악적 특징을 연구하고, 최종 분석은 가사 없이도 작동하게 한다.
- C. 대문자로 시작하는 단어를 primary boundary로 사용한다.
- D. 모든 언어의 문법 분석기를 먼저 완성한다.

### 15

경계 주변 화성 분석이 불완전한 2음 sonority를 발견했다. 가장 적절한 표시는?

- A. 가장 가까운 완전 화음을 확정해서 표시한다.
- B. `A(no3)`처럼 불완전성을 보존하고 Cadence는 근거 부족으로 보류할 수 있다.
- C. 조표의 으뜸화음으로 바꾼다.
- D. 해당 경계를 삭제한다.

### 16

AI가 half cadence 0.61을 제안했고 사람이 dominant prolongation으로 고쳤다. 저장 방식은?

- A. AI 결과를 지우고 사람 결과만 Core에 기록한다.
- B. 사람 결과를 무시하고 가장 높은 AI confidence만 기록한다.
- C. AI hypothesis와 human correction을 별도 필드·버전으로 보존한다.
- D. MusicXML harmony 태그를 직접 수정한다.

## D. 음악적 판단 합의 문항 — 정답보다 이유가 중요함

### 17

다음 증거가 충돌한다면 Phrase 경계 판단에서 어떤 순서로 중요하다고 보는가?

- 호흡 가능한 실제 시간 공백
- 선율의 해결/미해결
- V–I 또는 V에서 멈추는 화성 진행
- 반복·sequence의 계속성
- 강박/약박 위치

자신의 우선순위와 “예외가 되는 경우”를 적는다.

### 18

반복 음형 네 개가 이어지는데 두 번째 cell 끝에서만 PAC가 있고, 네 번째 cell 뒤에는 긴 쉼이 있다. 다음 중 자신의 판단에 가장 가까운 것을 고르고 이유를 적는다.

- A. 네 cell 전체가 한 Phrase
- B. 두 번째 cell까지 Phrase 1, 나머지가 Phrase 2
- C. 네 개 모두 별도 Phrase
- D. Phrase와 subphrase의 두 계층을 동시에 표시

### 19

앞 Phrase의 마지막 음이 뒤 Phrase의 출발점처럼 다시 들리는 경우, 실제 overlap으로 표시해야 하는 최소 음악적 조건은 무엇이라고 보는가?

### 20

자동 분석 화면에서 경계를 고칠 때 가장 먼저 제공되어야 할 조작을 고르고 이유를 적는다.

- A. 경계 추가/삭제
- B. 경계 이동
- C. Phrase 합치기/나누기
- D. primary phrase와 subphrase 계층 변경
- E. 대안 해석 두 개를 함께 보존

## 결과 해석

- 1–16번은 현재 구현·규격과의 일치도를 확인한다.
- 17–20번은 사용자의 음악적 판단을 다음 알고리즘 우선순위와 UI 설계에 반영하기 위한 문항이다.
- 설계와 다른 답은 규격 변경 후보가 될 수 있다. 특히 13번과 17–20번은 하나의 절대 정답을 강요하지 않는다.
- 정답 및 해설은 별도 `CORE_LOGIC_SELF_CHECK_QUIZ_v0.1_ANSWER_KEY_KO.md`에 있다.
