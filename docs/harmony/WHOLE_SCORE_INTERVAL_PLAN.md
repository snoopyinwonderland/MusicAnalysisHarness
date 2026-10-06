# 단계102 — 입력 성부 문맥·조건부 비화성음 조회의 점수 동등 최적화

## 목적과 범위

단계101의 통제 비교에서 전곡 완료율은 여전히 4/6이다. Walking의 parse 37.83초 및 Voice 문맥 트리 생성, Experience의 조건부 NCT 패턴 Fraction 전수조회가 스택에 나타났다. 계수 추가나 시간 한도 확대로 되돌아가지 않고 두 조회 비용을 줄인다. 기존 parser/운영 코드와 봉인된 단계96–101을 수정하지 않는다.

## 입력 사실 보존

Music21에서 현재 score 트리에 Voice가 없어도 분리한 PartStaff의 note sites/derivation에 Voice가 남아 있다. 따라서 `voice_0`로 일괄 처리하는 shortcut은 금지한다. 설치된 기본 `getContextByClass(Voice)`의 AT_OR_BEFORE 순서, contextSites/derivation, sortTuple와 wellFormed, 반환 객체 activeSite 동작을 유지하고 **한 번의 정적 imported score build 동안 Voice 검색 트리만 재사용**한다. 그 lease는 build 뒤 해제한다. 일반적인 가변 stream 캐시나 모든 class의 context 대체가 아니다.

런타임 기본 context 함수의 source SHA가 사전 계약과 다르거나 element가 함수를 override하면 원 `_voice_id`로 fallback한다. 원 builder bytecode는 private dependency로 `_voice_id`만 연결하고 production `canonical.py`는 바꾸지 않는다. `<harmony>` stripping, measure/voice/staff, 원음 ID·철자·음가·tie·grace, Formal IR 구조와 total-duration은 그대로다. 기존 전체 IR 6개와 모든 필드 hash가 동일해야 실제 비교를 실행한다. 현재 score 외부의 Voice site·derivation 사례도 합성 검증한다.

## NCT 판정 보존

stage100 RemainingFeatures의 pattern 생성과 step/neighbor 조건, 박자/전후 음/삼음 범위/구성음 조건, credit 및 unknown 처리는 그대로다. 시간 구간과 겹치는 패턴 조회만 정렬 start + subtree max-end로 바꾼다. 원 Fraction 경계의 정수 순서 인덱스를 사용하며 rounding/quantization은 없다. 모든 원패턴·중복·원순서와 `[start,end)`의 두 부등식을 보존하고 비-grid 쿼리는 원 전수조회로 fallback한다. 이 변경은 NCT 인식 품질 개선이 아니다.

## 검증·실행 종점

신규 합성 검증에서 원/새 성부·전체 legacy IR, NCT query/특징/비용, frontier/최종 직접검산/전체 catalog/source 불변성을 확인한다. 같은 고정 개발 6곡 전체 원IR와 새입력의 동일성 사전검사를 한 번 수행한다. 실패하면 본 비교는 진행하지 않는다.

그 다음 control=stage101 compiled+원 read_score, engine=새 입력/interval adapter를 곡당60초·동시4·각1회·재시도0, beam8·2M·page12·26고정계수로 실행한다. 양쪽 atomic checkpoint/20초 스택을 적용한다. baseline은 단계99 봉인 제출 재사용이다. 공통 완료곡은 원경로/비용/26특징/availability/operations/전체 catalog가 control과 이전101에 동일해야 한다. 새 완료곡은 독립 stage99 UnitScorer의 전체 직접검산을 통과해야 한다. 타임아웃 부분 승자는 제출하지 않는다.

예측을 먼저 봉인하고 gold로 채점한다. 완료율 변화와 공통 완료곡 품질을 구분한다. 해시 검사는 음악 정확도 인증이 아니다. 독립234곡 시험/공개모델 비교/전체 국소조성·로마자·전위·NCT 검증/화면·Claude 연결은 여전히 별개다. 이번 단일 비교·기록으로 종료하며 버전 고정 뒤 동일 음악 재시도, 계수/beam/timeout sweep은 없다.
