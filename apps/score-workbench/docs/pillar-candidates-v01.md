# 기둥음 후보 v0.1 / 화성 확장 계약

## 쉼 관찰 비교 UI

‘쉼 근거 중복 검토’는 Pillar following-gap과 같은 위치의 Phrase observed-gap을 비교한다. 현재 notes/stream 및 XML 해시가 ledger와 일치해야 한다. 프레이즈 규칙의 IOI/음가 기준 계산까지 추적된 경우만 비교하며 inferred onset이나 누락/다른 revision은 보류한다.

공유 관찰은 새 근거로 세지 않는다. 추가 관찰(비교 범위 밖)은 해당 observed-gap 입력에 없다는 뜻일 뿐 다른 Phrase 규칙에서 안 썼다는 뜻이 아니다. 이 값으로 점수나 경계를 바꾸지 않는다. 출처 완료 범위는 단일 cue이고 전체 Phrase lineage 완료는 아니다.

## 근거 출처 구조화 — 부분 완료

각 독립 후보의 evidence에 ruleId/ruleVersion/family/eventRefs/label을 저장한다. eventRefs는 입력 주변음 문맥이며 전체 계산 의존성 graph가 아니다. provenance=local-input, reviewEligibility=unverified. 기존 reasons는 표시 호환용으로 유지한다. temporal gate는 문구가 아닌 규칙 ID로 판단한다.

UI는 관련 규칙을 음가·시간/박 위치/선율 관계/반복 대응으로 묶고 중복 확인 미완료를 표시한다. 이 묶음은 통계적 독립성·최종 증거 수가 아니며 기존 표시 등급을 재보정하지 않는다. generic auditEvidence는 별도 완전한 graph와 baseline ledger가 주어져야 추가 관찰을 반환한다. 현재 운영 Phrase adapter/전체 출처 graph는 아직 연결되지 않았고 자동 경계 수정은 없다.

## 최신: 독립 계산 / 시작 힌트 분리

이 절이 아래 과거 구현 설명보다 우선한다. pillarCandidates는 phraseStarts 없이 계산한다. composePillarDisplay가 phraseStarts를 별도의 phraseHints로 합친다. 독립 후보의 reasons/level은 합성 과정에서 변경되지 않는다. 시작 힌트만 있는 음은 보라색으로 표시하며 독립 점수/반복 공통 보기에는 포함하지 않는다. 기존 청록/황토는 독립 결과의 등급이다. 원본과 Phrase 경계는 바꾸지 않는다.

상세 계획/단계 상태: [Pillar–Phrase 근거 분리 계획](pillar-phrase-evidence-firewall-plan.md).

## 프레이즈 시작 근거

optional phraseStarts=[{noteId,phraseNumber}]는 현재 표시하는 프레이즈 해석의 시작음 참조다. 짧은 음이나 엇박도 시작음이면 후보로 보존한다. 단독 근거는 tentative이고, `현재 프레이즈 해석에 의존`을 표시한다. 박 위치를 바꾸거나 시작음을 강박으로 재분류하지 않는다. 참조가 입력 notes에 없으면 무시한다. 프레이즈 경계 변경 시 해당 근거도 갱신되며, 반복 공통 보기에서는 여전히 반복 대응이 필요하다.

## 검토 보기 업데이트

기둥음 보기 메뉴의 `전체 기둥 후보`는 기존 후보 모두, `반복 공통 골격 후보`는 그중 correspondences가 있는 후보만 표시한다. 이것은 대응 증거 기반 부분집합 필터이며, 표면→중경→배경의 계층적 축약은 아니다. 단 한 번 나타난 중요 음도 공통 보기에서 제외될 수 있다. 화성적 골격은 여전히 미구현이다.

각 후보의 `대응 음 N개 보기`에서 대상 마디·박·음높이와 현재 음에서 상대 음으로의 조옮김/시간 배율, 규칙 버전을 확인할 수 있다. 최대 8개까지 보존한 대응 근거 수이지 모티프 등장 횟수가 아니다. 표시 전환은 색칠만 바꾸며 원본이나 Phrase/Motif 경계는 수정하지 않는다.

## v0.3 반복 변형 근거

4음 기준 구간과 4–6음 구간을 비교하여 짧은 장식 삽입, 일정 조옮김, 0.5–2배 시간 확대/축소, 내부음 하나의 1반음 변형을 허용한다. 시간 정렬 허용오차는 기준 첫/끝 onset 간격의 8%이다. 3개 이상의 서로 다른 음높이와 2개 이상의 서로 다른 음정을 요구한다. 쉼을 가로지르는 구간은 배제한다. 끝음은 일치해야 한다. 이는 실험적 기준이지 음악 이론의 보편적 정답은 아니다.

후보 correspondences는 otherNoteId / ruleVersion / transposition / timeScale을 보존한다. 유지된 음에만 대응 근거를 부여하며, 기존 시간 근거 없이 반복만으로 새 기둥을 확정하지 않는다. 원본과 화성 채널은 불변이다. 성능을 위해 시작점 간 128 attack 이내만 비교하며 음당 8개 근거까지 남긴다. 전체곡 장거리 정렬과 다단계 골격 UI는 후속 과제다.

## v0.2 업데이트 (2026-09-23)

아래 v0.1 설명은 초기 설계 기록이다. 현재는 optional meters[measureOrdinal]로 XML의 박자 변화를 입력받아 기준 박 이상 지속과 박 위치를 함께 평가한다. 4/4 pulse=1 quarter, 6/8 pulse=1.5 quarter. 박자 미상/비정형은 기존 근거만 사용한다. 쉼 뒤 진입, 엇박 시작 후 다음 박 내부까지의 지속(타이 포함), 4박자의 중간 강박도 근거다. 기보 onset은 바꾸지 않는다.

연속적인 한두 박 길이 A–B–A(1–2반음 왕복)에서 첫 A가 기준 박에 있으면 국소 축약 기준음 후보로 보존한다. 내부음을 화성적 보조음으로 확정하거나 원본에서 제거하지 않는다. 완전한 계층적 축약과 모든 도약/변형 대응은 후속 단계다. 표면 골격과 깊은 축약의 독립 선택 UI는 아직 없다.

브라우저에서 실제 색칠 확인 완료. 렌더러가 원본 note 순서를 data-source-note-index로 전달하여 재생/search ID와 무관하게 연결한다. 이 순서는 해당 XML revision 내부 뷰 연결용이며 영구 Canonical ID는 아니다. 타이 후속 기보 음표 전체의 색칠은 아직 별도 과제다.

2026-09-23. 원본/Core/검색/프레이즈 경계를 바꾸지 않는 국소 Analysis Layer 가설이다. 오른쪽 기둥음 색칠 버튼으로 청록(비화성 근거3개 이상)/황토(2개)를 표시한다. 화성 단독 또는 충돌 근거는 보류 등급이다. 확률/정답률이 아니며 무색 음도 중요할 수 있다.

현재 근거: 주변9음 중앙 음가 대비 지속, 기보 마디 첫박, 지속 뒤 공백, 짧은 순차진행 뒤 긴 도착, 이조 불변4음 반복 위치. 반복 검사는 제한된 정확 대응으로 폭넓은 variation 인식이 아니다. 시간 근거가 상관되어 있으므로 근거 개수를 독립 확률로 해석하지 않는다. Schenker의 계층/축약 관점을 참고하지만 화성적 prolongation, Urlinie, 배경구조를 계산하지 않는다.

참고: Schenker, Free Composition (https://is.muni.cz/el/phil/podzim2007/VH_53/Schenker_Free_Composition_1.pdf), Open University voice-leading course (https://www.open.edu/openlearn/history-the-arts/music/voice-leading-analysis-music-2-the-middleground/content-section-6.2). 색칠 규칙은 해당 이론의 자동 구현이나 검증된 축약법이 아니라 본 프로젝트 실험이다.

## 화성 모듈 입력 계약

`pillarCandidates(notes,{harmonyEvidence})` / PillarReviewPanel.harmonyEvidence는 optional이다. 항목:

```typescript
{noteId, analysisId, engineVersion, evidenceRefs: string[], label,
 effect: 'supports'|'conflicts', status:'hypothesis'|'human-validated'}
```

noteId는 동일 score revision/분석 성부의 입력 note ID여야 한다. 수정판 annotation 재매핑은 화성 adapter에서 수행해야 한다. 후보마다 harmony 배열을 별도 보존해 대안/충돌/AI·human 상태를 덮어쓰지 않는다. 유효한 provenance가 없는 근거는 사용하지 않는다. 화성 정보가 없으면 기존 결과 그대로다. 화성 채널만 들어온 음은 검토용 후보로 보존하며 현재는 화성 라벨을 임의의 점수로 변환하지 않는다.

향후 화성 개발 범위: (1) versioned 화성 결과→이 계약 adapter (2) 패널의 harmony 상세 표시 및 API 전달 (3) 검증 자료 기반 화성 가중/계층 정책. 선율·리듬 계산과 악보 anchor 색칠 코드는 교체하지 않는다. 현재 API는 harmonyEvidence를 아직 공급하지 않으며 미확인 화성을 추정하지 않는다.

## 표시 한계 및 검증

원본 MusicXML의 part/staff/voice/measureOrdinal/beat/pitch를 렌더 ID로 연결한다. 초기 버전은 attack만 색칠하고 tie continuation 전부를 색칠하지 않는다. 재조판 없이 렌더된 SVG에 적용하며 토글 해제 시 원래 style로 복원한다. 미렌더 페이지와 anchor 매핑 실패는 후보 수와 표시 수 차이로 드러난다. 제한 미리보기/제안 범위에서는 패널을 숨긴다. cross-staff/생략된 voice/특이 마디 번호는 추가 검증 대상이다.

원본 불변/이조 불변/박절만으로 선정 금지/화성 분리 테스트를 둔다. 실제 브라우저 시각 검증은 아직 완료하지 않았다. 따라서 화면 확인 전 정확한 색칠이나 음악적 타당성 검증 완료를 주장하지 않는다.
