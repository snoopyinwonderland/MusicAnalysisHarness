# 화성 분석 → 편곡 참고 자료 계약 v0.1

상태: **연결 준비용·로컬 연구 후보 자료. 실제 편곡 엔진 연결 및 추론기 교체는 보류.**

2026-10-05 사용자 제공 `musicomp` 입력 계약과 실제 코드를 읽어 확인했다. `K:\Music Composition` 파일은 수정하지 않았다. 사용자는 연결하기 이르면 지금 하지 않아도 된다고 했고, 현재 검증 상태에서는 보류하는 것이 맞다. 개발 결과와 연결 판단은 [단계84 기록](records/2026-10-05-score-balance-and-arrangement-reference.md)에 남긴다.

## 1. 왜 아직 ChordSpan으로 넘기지 않는가

양쪽 시간 기준은 일치한다. 하지만 시간 좌표가 같다고 음악적 의미 계약까지 충족하는 것은 아니다.

| 항목 | 현재 연구 출력 | musicomp가 필요로 하는 것 |
|---|---|---|
| 시간 | 전체 기보 시작 기준 Fraction quarter, `[start,end)` | 동일. 못갖춘마디 실제 길이·붙임줄 합침·반복 미전개 |
| 화음 범위 | 원 후보망에서 선택된 범위와 같은 화음의 인접 합집합 | 작품/요청 범위의 일관된 ChordSpan 목록 |
| 근음·구성음 | 절대 철자와 C=0 absolute fifths TPC | 국소 으뜸음에 대한 relative fifths, 근음 먼저 |
| 국소 조성 | 미검증이므로 null | `Key(tonic_tpc, minor)`, 적어도 `tonic_pc`와 장/단조 |
| Roman·기능 | null | `token`, `function`(T/PD/D 등), 출처와 불확실성 |
| 베이스·전위 | null | 판정한 베이스 또는 명시적인 unknown. None은 근음 위치를 뜻하지 않음 |
| 확신도 | 미보정 점수 비용, confidence=null | margin/대안/근거의 의미를 구별한 소비 정책 |
| 선율 NCT·종지 | 확정 분류를 내보내지 않음 | 별도 검증한 유형/준비/해결 근거가 있을 때만 사용 |

`musicomp/analysis/harmony.py`의 `ChordSpan.root`·`tones`는 **국소 조성 기준**이다. `root_pc`는 `self.key.tonic_pc`를 참조하므로 key=null인 후보를 그대로 넣으면 안전한 불완전 객체가 되지 않는다. 현재 `source` 값도 given/inferred를 전제로 하는데, 이 연구 후보를 given으로 위장하지 않는다.

현 추론기는 선율 음도 emission·전이·프레이즈 근거와 max-marginal margin을 사용한다. 새 출력의 형태를 맞춘 것만으로 그것보다 성능이 낫다는 뜻은 아니다. 국소 조성 추정은 Claude 쪽의 별도 모델/출처로 구별해 합성할 수 있지만, 그렇게 얻은 해석을 Codex가 검증한 사실이라고 저장하지 않는다.

## 2. 파일과 사용 범위

`schema_name = musicanote-harmony-arrangement-reference`, `schema_version = 0.1.0`.

- 생성 모듈: [harmony_arrangement_reference.py](../../src/musicanote_harness/harmony_arrangement_reference.py).
- 실제 연구 산출물: [단계84 report](../../output/harmony-score-balance-2026-10-05-r1/report.json).
- **118개 범위 파일 / 23개 악장 색인 / 132개 중복 제거 후보**다. 23곡 전체의 화성 분석 파일이 아니다. 원 범위가 겹칠 수 있으므로 색인을 이어 붙여 작품 전체 ChordSpan을 만들지 않는다.
- 각 범위는 원 XML·전체 IR 경로/SHA, 모델/SHA, 원 후보망/SHA, sounding/note ID를 가진다. 성부별 음악 역할·반주 스타일을 확정하지 않는다.
- 선택 한도에서 완료하지 못한 16범위는 `unresolved=true`, 연구 승자=null이다. 예전 경로가 후보 목록에 남아 있어도 그것을 새 승자로 채우지 않는다.
- 이 자료의 연구 모델에 묶인 로컬 비상업 연구 조건을 유지한다. 운영 승격, 외부 API 전송, 모델 재배포, 자동 학습, 확정 생성 제약 사용은 허용된 것으로 간주하지 않는다.

이는 곡마다 하나의 최종 화성 JSON을 제공하는 목표의 **후보/출처 계약 초안**이다. 현재는 실제 어댑터를 호출하지 않는다. 향후 `harmony="external:<json 경로>"`를 구현할 때는 별도의 generation-ready 계약 버전을 검증해야 한다.

## 3. 필드 의미

최상위에는 다음을 둔다.

| 필드 | 의미 |
|---|---|
| score_id / ir_document_id / sample_id | 원악보 revision과 연구 범위 식별 |
| requested_scope / scope_convention | global quarter 유리수의 `[start,end)` |
| time_policy | origin, quarter 단위, pickup 실제 길이, tie union, repeats 미전개 |
| source_ref / analysis_ref | 원 XML·IR 및 case/model/원 graph 파일 SHA. 호출자가 모두 검증한 뒤 생성 |
| hypotheses | 같은 모델 점수로 재생한 source-bound 대안 목록 |
| research_selected_hypothesis_id | 이번 연구 탐색이 완료했을 때만 승자 참조 |
| engine_status / unresolved | exact 완료와 wall/resource 보류를 구별 |
| alternatives_complete=false | 저장된 세 blind arm의 대안이지 가능한 모든 화음 해석이 아님 |
| whole_score_analysis=false | 부분 범위. 범위 밖은 미분석 |
| generation_ready=false / production_adopted=false | 분석 확정/운영 적용이 아님 |
| restrictions / warnings | 연구 용도·불확실성·결측 분석의 명시 |

후보 하나는 `hypothesis_id`, `source_arms`, `raw_path_variants`, `harmonic_runs`, `score_cost`, `confidence=null`, `human_validated=false`를 가진다.

ID는 IR revision/SHA·모델 SHA·정확 범위·합집합 run 내용을 묶어 생성한다. 같은 합집합이라도 source revision/model이 달라지면 새 ID다. 기존 구조 분석/피드백 ID를 변경하지 않는다. 같은 signature 인접 edge는 하나의 run으로 합치되 raw edge IDs는 보존한다. 동음이명 철자나 다른 분석 root는 합치지 않는다. 동일 합집합의 다른 raw partition 비용이 다르면 내보내기를 중단한다.

`score_cost`는 35항 연구 모델의 비용으로 **낮을수록 선호**된다. 확률, 음악적 정답률, calibrated confidence, 다른 모델과 직접 비교 가능한 척도가 아니다. 순위가 좋은 것만으로 확정 화성에 승격하지 않는다. 후보 confidence는 null이고 margin도 임의로 발명하지 않는다.

run마다 다음을 저장한다.

- span: `{start:{numerator,denominator}, end:{numerator,denominator}}`.
- analysis_root / member_spellings: step와 rational alter. 현재 exporter는 정수 임시표만 지원하며 microtone TPC 투영은 명시적으로 거부한다.
- source_sounding_event_ids / source_note_ids: 원음표로 재현할 수 있는 참조. 경계에 걸친 tie는 원 sounding 전체와 모든 기보 note ID를 남긴다. 표시는 run span으로 clip하되 새 attack이라고 읽지 않는다.
- musicomp_candidate: 아래 예처럼 absolute TPC와 Fraction 문자열. **ChordSpan 자체가 아니다.**

```json
{
  "musicomp_candidate": {
    "start": "1/3",
    "end": "2",
    "root_absolute_tpc": 6,
    "tones_absolute_tpc": [6, 3, 7],
    "bass_absolute_tpc": null,
    "key": null,
    "rn": null,
    "function": null,
    "margin": null,
    "source": "experimental_analysis",
    "root_is_literal_member": true,
    "chordspan_ready": false
  }
}
```

위는 **형식 설명용 F♯–A–C♯ 예**이지 특정 구간의 정답/조성 확정이 아니다. C=0 absolute fifths는 F=-1,C=0,G=1,D=2,A=3,E=4,B=5이고 sharp당+7, flat당-7이다. F♯=6, G♭=-6이므로 MIDI pc는 같아도 철자가 다르게 남는다. MuseScore의 C=14 TPC와 혼동하지 않는다.

향후 `relative_tpc = absolute_tpc - local_key.tonic_tpc`로 변환할 수 있지만, **검증되거나 별도 추정이라고 표시한 local key가 있을 때만** 한다. null key를 C major로 메우지 않는다. 분석적 근음과 표면 근음이 다른 가설에서는 분석 root를 실제 구성음 목록에 추가하지 않는다. 이미 literal member인 근음만 목록 앞에 정렬한다. `tones`만 보고 분석 root와 다른 표면 triad quality를 동일 의미로 읽지 않는다.

## 4. 정답 누출과 출처 관문

참고 export가 읽을 수 있는 경로 arm은 `fresh`, `previous_context`, `frozen_old26`뿐이다. 모두 현재 고정된 연구 모델 점수로 재생한 blind 경로다. 기존 arm 이름은 그 **경로의 출처**이며 각기 다른 비용 모델의 점수라는 뜻이 아니다.

`stored_target`, 참조 annotation, 평가 결과는 exporter의 whitelist 밖이다. 그것들은 비용 진단용 ledger에서만 별도로 쓰고 소비 JSON에는 넣지 않는다. `source_labels_used=false`, `target_path_created_using_labels=false`, 원 clock accepted를 요구한다. selected path와 receipt의 원 group IDs/비용도 일치해야 한다.

원 graph의 연속 edge가 범위를 정확히 덮는지, source sound/note IDs가 실제 IR에 있는지, 음표가 run과 겹치는지, 유리수/양수 span과 모델/원 source binding을 검증한다. SHA 검증은 exporter 호출자의 책임이므로 임의 입력에서 `verified=true`만 작성하여 신뢰하면 안 된다. 제공 runner와 사후 auditor는 실제 파일 SHA를 확인한다.

## 5. 단선율만 있는 경우 / 주어진 화음 수정은 다른 업무다

단선율에는 원 화성이 유일하게 들어 있지 않다. 같은 멜로디에 여러 화성화가 가능하므로 이 입력은 **관측 화음 인식**보다 **화성 계획 제안**에 가깝다. 현재 다성 score의 source union에 근거하는 연구 분석기를 바로 melody-only harmonizer로 대체하면 안 된다.

1. 기존 musicomp harmonizer 또는 사용자 제공 계획을 기준선으로 유지한다.
2. 조성·종지 의도·스타일·프레이즈를 포함한 복수 화성 계획을 생성한다. 생성 의도와 분석 가설의 출처를 분리한다.
3. 편곡된 결과에서 실제 구성음 제시·베이스·성부 진행·NCT 준비/해결·의도한 종지를 검사한다.
4. 사용자가 고른 계획과 자동 추정/반주 생성의 성과를 별도로 평가한다.

주어진 화음과 선율이 충돌해 보이는 경우도 바로 교체하지 않는다. 사용자 예인 **Voices That Care 73–76마디**, V 위의 강박 지속 E♭와 원 편곡의 Cm7 → E♭/B♭ → B♭7은 재화성 비교 사례로 보존하되 이번 단계에서 음표를 검사하거나 정답을 판정하지 않았다. 계류/전타·확장·조성 변화 설명을 먼저 대조하고, 수정이 허용된 범위 안에서만 대안을 만든다. 범위 밖 given 화음은 유지한다. 주어진 화음은 그 편곡의 기보 target이지만 가능한 분석 해석의 유일한 정답은 아니다.

## 6. 연결 재개 기준과 최소 개발 순서

완성된 전체 분석까지 반드시 기다릴 필요는 없지만, 다음 관문을 넘기 전에는 Claude의 추론기를 교체하지 않는다.

1. **선택 성능:** 제한된 점수 공동 균형 → 고정 Dev 비교. 원 score/구간 분모·후보 부재·자원 보류·퇴행을 모두 보고, 독립 Test에서 재확인한다. 검사 통과 수나 Train 수치를 정확도로 보고하지 않는다.
2. **소비 의미:** 요청 범위의 완전한 시간 coverage, local key 출처·불확실성, root/member spelling, 판정된 bass 또는 unknown, Roman/function/대안 계약을 검증한다. 확정 NCT/종지는 각각 별도 평가하며 빠진 유형을0/부재로 읽지 않는다.
3. **작은 A/B:** 8–16마디의 단선율 화성화와 given 화음의 국소 재화성 각각에서 기존 musicomp 기준선과 비교한다. 피아노 솔로부터 구성음 제시·선율 보존·베이스/전위·성부 진행·스타일 다양성·청취 평가를 확인한다.
4. **승격과 확장:** 적합한 사용 권한/프로파일·fallback·캐시/모델 버전·rollback을 명시하고 옵트인 read-only feature부터 연결한다. 듀엣/트리오/쿼텟과 전곡/관현악은 다음 별도 관문이다.

현재 완료한 것은 후보 파일 형식과 진단 산술뿐이다. 1–3을 마치지 않았으므로 연결 일정/남은 며칠을 단정하지 않는다. 추후 Claude의 외부 입력 어댑터는 Claude가 작성하고, 이 프로젝트는 소비 가능한 검증 결과를 준비한다. 추론 화성을 프레이즈로 재투입하여 스스로 확정하는 순환은 R12처럼 계속 금지한다.
