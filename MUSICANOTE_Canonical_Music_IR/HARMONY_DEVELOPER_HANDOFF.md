# 화성 Harness 개발 인수인계 — 여기서 시작

**2026-09-29 최신 — +M7/mM7 및 공통 후보 계약:** `harmony_candidate_catalog.propose` v0.1이 기본9형태·증6·추가음·새7화음 후보를 모아 원후보ID/철자 가정/음표상태/유리수 note-time을 같은 형식으로 제공한다. +M7/mM7은 관측 근음·3음·장7음 관문으로 제안하고5음 결측을 보존한다. 기존 `TEMPLATES`나 선택기를 변경하지 않았다. 신규20/전체1,383테스트, 새18XML 및 이전45대조군 후보 불변/계약 검사 통과. [r1 결과](../output/harmony-candidate-catalog-2026-09-29-r1/report.json), 계약·주의점·재현 (상세 기록은 공개 브랜치에서 제외). 기존24창의 기본1,160·추가음178개 보존, 신규 +M7 10개는 모두 증5음 결측인 약한 가정으로 정답이 아니다. 운영5173/악보 화면/원자료 미변경. 다음은 공통 후보를 이용한 기능·조성 가정 및 시간 근거 대조이며, 음을 많이 포함하는 후보를 자동 우선하지 않는다. 아래는 이전 이력이다.

**2026-09-29 최신 — 9·4/11·6/13음 후보와 Unit28 연결:** `harmony_extended_candidates.propose` v0.1이 원주석 없이 dominant7 기준의 추가음 후보를 만들고 Unit28의 실제 음역·이탈/도착·9–8–7 근거에 연결한다. 근음 없는9 대 반감/감7, 기본7+장식음 대 추가음, 구성음 결측을 보존한다. 모든 재즈 확장화음 지원을 뜻하지 않는다. 신규23/전체1,363테스트·30 MusicXML 검증. [최종r2 결과](../output/harmony-extended-candidates-2026-09-29-r2/report.json), 계약·통계·반례·재현 (상세 기록은 공개 브랜치에서 제외). 기존24창의 후보1,160개를 유지하며178개 추가 가정을 생성했고, 과거 주석 선정202건에서도 실행했다. 후보 수는 정확도가 아니며 기본7화음의3음이 없는 약한 가정이 많다. 누적/전체 동시/최소 지지 동시를 구별한다. 운영5173·기존 악보 화면·Core/원주석 미변경. 다음은 +M7/mM7 형태 누락과 공통 후보 계약을 정리하고, 확장 후보를 조성·기능 및 시간 비교기에 연결하는 단계다. 아래는 과거 이력이다.

**2026-09-29 최신 — 교재 규칙과 후보 생성기의 연결 누락 점검 / 증6화음 연결:** 책의 검토 완료는 분석기 전체 적용 완료가 아니다. 기존 열린 후보는 9종 3·7화음 형태였다. `harmony_augmented_candidates.propose` v0.1을 추가하여 관측된 철자의 ♭6/♯4 쌍에서 It/Ger/Fr/Ger43 후보 좌표를 생성하고 기존 Unit30 성부 해결 근거를 연결한다. 원주석/조성 정답은 입력하지 않으며 기존 후보·Core·운영5173는 그대로다. 신규14/전체1,340 테스트,15 MusicXML 대조 통과. 기존24창은 증6 제안0, 과거 Unit30 22건에서는 비교 가능21건 중18건의 원주석 계열/좌표가 후보에 포함되고3건은 grace 관문으로 보류했다. **표본과 범위는 과거 주석에서 선택되었고 오래된 IR 정렬 한계가 있으므로 정확도 수치가 아니다.** [결과](../output/harmony-augmented-candidates-2026-09-29-r2/report.json), 연결 현황·순서·한계 (상세 기록은 공개 브랜치에서 제외). 다음은 남은 9/11/13 구성 후보와 후보 공통 계약을 정리한 뒤, 기능/조성 대안·시간 판정을 통합한다. 아래 최신 표기는 과거 이력이다.

**2026-09-29 최신 — 유지/교체의 같은 음표·시간 대조:** `harmony_hold_change_contrast` v0.1이 한 K281 경계의 유지80후보×기존 교체13후보=1,040쌍을 동일한 유리수 note-time으로 대조한다. F5가 유지 전제에서는 반복 경과, 교체 전제에서는 선행음으로 설명되는 충돌을 원음표에 연결했다. 미설명 음가 차이는 추천 점수/정답이 아니며 선택 없음. 신규10/전체1,326테스트, 기존18XML 대조군 재파싱·재검증 통과. [8807 악보](http://127.0.0.1:8807/real-cases/reviewm_555ff701230fc0b8ee66/whole-score.html), [최종r2 결과](../output/harmony-hold-change-contrast-2026-09-29-r2/report.json), 조건·편향·재현·다음 관문 (상세 기록은 공개 브랜치에서 제외). 출력 약11.9MB는 연구용이며 운영 저장 최적화는 별도다. 다음은 충돌 사례의 강세·베이스/성부 진행·화성 리듬 근거 연결 및 독립 평가다. Core/원주석/운영5173 변경 없음. 아래는 이전 이력이다.

**2026-09-29 최신 — 반복음 포함 음형:** `harmony_reattack_figures` v0.1은 같은 철자 재타격을 근거 그룹으로 묶되 원 attack/음가/ID를 모두 보존한다. 동일24창에서 K281의 겹치는3음형에 조건부 경과 설명이 가능해졌다. 후보×음형24쌍/추가 후보×음48쌍은 독립 정답 수가 아니다. 원 화음 유지·교체 대안은 선택하지 않는다. 신규13/전체1,316테스트,12XML 대조 통과. [8806 악보](http://127.0.0.1:8806/real-cases/reviewm_555ff701230fc0b8ee66/whole-score.html), [r1 보고서](../output/harmony-reattack-figures-2026-09-29-r1/report.json), 계약·재현·가정 충돌 (상세 기록은 공개 브랜치에서 제외). 다음은 유지/교체 가정 아래 같은 음형의 설명 충돌 대조다. 창 밖 문맥/독립 정확도/운영 반영은 보류. 아래는 이전 이력이다.

**2026-09-29 최신 — 잔여 음별 조건부 설명:** `harmony_residual_audit` v0.1이 기존 13개 교체 후보쌍에 경과/보조/이중 보조 및 선행음·실제 지속 지연음 형태를 연결하고, 작은 셀의 구성음 대안과 병렬 저장한다. K281의 85 잔여 음 출현(고유 11음) 중 6출현에 붙은 선행음 설명은 **같은 F5 한 음**이다. 79출현은 미해결이며 13개 후보 모두 유지한다. NCT/화음 확정·순위 변경·정확도 개선 선언은 없다. 신규 10/전체 1,303 테스트 및 12 XML 대조 통과. [8805 악보](http://127.0.0.1:8805/index.html), [r1 보고서](../output/harmony-residual-audit-2026-09-29-r1/report.json), 계약·실패·재현 기록 (상세 기록은 공개 브랜치에서 제외). 음별 클릭 색칠과 이전 선택 해제를 브라우저 확인했다. 다음은 재타격을 포함한 음형/제한된 문맥 대조이며 강세·국소 조성·독립 평가와 운영 승격은 보류다. 아래는 이전 이력이다.

**2026-09-29 최신 — 유지·교체 판별 관문:** `harmony_change_gate` v0.1이 구성음 교체·베이스·2종 직접 성부 이동·지속·완전 준비 장식음 경쟁을 함께 검사한다. 기존24창/121경계/135,773후보쌍 중 MozartK281의 **한 경계에13개 경쟁 설명**이 통과했고, K280 조건부 유지18출현은2가설로 중복 제거된다. 미설명음이 남으므로13정답/독립 개선이 아니며 최종 화음/경계 선택 없음. 신규12/전체1,293테스트·18XML 대조 통과. [8804 검토](http://127.0.0.1:8804/index.html), [최종r2 보고서](../output/harmony-change-gate-2026-09-29-r2/report.json), 조건·실패·한계·재현 (상세 기록은 공개 브랜치에서 제외). 첫실행의 테스트 XML7/2 duration 지원 문제를 명시적 재타격 표기로 수정했다. 다음은 남은 residual·NCT/추가 변화·국소조성 대조와 별도 작품군 검증이다. 운영5173/Core/원주석 미변경. 아래는 이전 이력이다.

**2026-09-29 최신 — 불완전 후보까지 같은 시간축에서 대조:** `harmony_temporal_readings` v0.1이 열린 후보·시간 추적·조건부 장식음/이중 보조음을 연결했다. 기존3개 train 악장의 처음8마디를 결과와 무관하게 고정하여24창/1,160유지 후보/145 attack-release 셀을 비교한다. 셀은 화음 경계가 아니며 앞뒤 구성음으로 결측을 메우지 않는다. 불완전PC 후보1,032개, 근음 철자 미확정534개를 보존했다. **독립 정확도 평가/최종 순위·화음 선택은 아니다.** 신규12/전체1,281테스트·18XML 대조 및 원IR 시간/음가 합계·렌더ID 감사. [8803 악보 목록](http://127.0.0.1:8803/index.html), [최종r3 보고서](../output/harmony-temporal-readings-2026-09-29-r3/report.json), 정본 기록 (상세 기록은 공개 브랜치에서 제외). r3은 후보/마디 변경 시 오래된 색칠을 해제하는 UI 보완본이다. 운영5173/Core/원주석 미변경. 다음은 유지/교체 판별 기준의 대칭 반례 검증과 별도 작품군 평가다. 아래는 이전 이력이다.

**2026-09-29 최신 — 구성음의 실제 시간 추적 / 전체 계획 누락 대조:** `harmony_member_timeline` v0.1이 각 후보 구성음의 앞·안·뒤 출현, 타이로 지속하는 동일 sound와 재타격, 구간 안 누적 완성 시각과 실제 동시 완성을 구별한다. 바깥 음으로 안쪽 결측을 메우거나 화음 시작을 소급하지 않는다. 베토벤02-3/모차르트K281-3/K280-1의 기존30가설 구간에서24개는 누적 완성이 시작보다 늦고6개만 실제 동시 완성 셀이 있다. 이는 선택 편향이 있는 기존 후보 표본이며 정확도 개선 수치가 아니다. 신규12/전체1,269 unit test·21 XML 대조·원IR/렌더 ID 감사 통과. [8801 전체 악보 목록](http://127.0.0.1:8801/index.html), [r2 결과](../output/harmony-member-timeline-2026-09-29-r2/report.json), 계약·재현 (상세 기록은 공개 브랜치에서 제외). [마스터 계획 §0](HARMONY_COMPOSITION_HARNESS_IMPLEMENTATION_PLAN.md)에 P0–P13 현재/보류 관문을 추가했다. Core/기존 선택/운영5173 변경 없음. 다음은 열린 후보군에서 유지/교체 근거 대조와 독립 표본 평가이며,31마디 사용자 해석만 맞추는 개발로 한정하지 않는다. 아래는 이전 이력이다.

기준일: 2026-09-28. 이 문서는 **현재 상태·기록 위치·재현·미해결 사항의 안내서**다. 과거 실험 수치를 최신 결과로 덮어쓰지 않는다. 알고리즘 또는 데이터 계약의 정본을 대체하지 않는다.

**2026-09-29 최신 — 이중 보조음 / 구성음 진행 대조:** `harmony_neighbor_contrast` v0.1이 같은 음형을 고정 화음 아래 해석하는 가설과, 각 음을 구성음으로 설명하는 국소 후보들을 비교한다. 음형 자체와 다른 동시 음의 구성음/미설명/철자 보류 및 실제 지속시간을 분리한다. 31마디 A♭major 유지 가정은 음형 외 다른 음을 모두 구성음으로 설명하지만 G를 A♭major7, B♭를 E♭ 계열 화음으로 보는 대안도 남으며 국소 미관측 구성음이 많다. **이중 보조음 확정/화음 교체 확정/자동 순위 변경은 아니다.** [8800 비교 화면](http://127.0.0.1:8800/whole-score.html), [r2 보고서](../output/harmony-neighbor-contrast-2026-09-29-r2/report.json), 정본 개발 기록 (상세 기록은 공개 브랜치에서 제외). 신규12/전체1,257테스트,24 MusicXML 대조 통과. 기존21,815후보/구간/비용/해결 근거 유지; 운영5173 미변경. 다음은 국소 창에 부족한 구성음의 앞뒤 실제 출현과 후보 유지/교체 근거를 비교하는 단계다. 아래는 이전 이력이다.

**2026-09-29 최신 — 옥타브 중복 해결 / 이중 보조음 완전형·부분형:** context v0.2와 `harmony_voice_figures`가 순수 옥타브의 동시 시작·끝, 동일 중복 수, 동일 철자 순차 이동일 때만 조건부 성부 연결을 추가한다. 소나타1번19마디 A♭3/4→G3/4를 연결했으며 같은 중복 그룹으로 묶어 독립 투표로 세지 않는다. 31마디 G5–B♭5–A♭5는 A♭장화음 후보 아래 **선행 기준음 미확인 부분형**으로 기록한다. 사용자 이중 보조음 해석은 그대로 보존하며 자동 확정과 구별한다. 신규18/전체1,245테스트, 기존6+신규12 MusicXML 대조 통과. [8799 악보](http://127.0.0.1:8799/whole-score.html), [r2 보고서](../output/harmony-voice-figures-2026-09-29-r2/report.json), 계약·반례·재현 (상세 기록은 공개 브랜치에서 제외). Core/원주석/후보·비용/운영5173 미변경. 다음은 부분형의 준비·도착 화음과 경쟁 설명 대조이며, 더 많은 장식음 설명이 가능하다는 이유만으로 해당 화음을 선택하지 않는다. 아래는 이전 이력이다.

**최신 구현 — 후보별 베이스·전후 해결 근거:** `harmony_candidate_context` v0.1이 기존21,815후보를 삭제/재정렬하지 않고, 시간 셀의 최저음 factor와 정확히 맞닿는 창 사이의 dominant/leading-tone root 관계 및 명시적 단선율 성부 해결을 연결한다. 소나타1번15마디 B♭7 뒤 D→E♭/A♭→G,17마디 A♭→G를 확인했으나19마디는 기보상 옥타브 중복 성부로 직접 연결 보류. 시작 D베이스는 B♭7의3음(제1전위 가설);29/30뒤 D♭는 Gdim7의5음(제2전위 가설)이며 분산 베이스의 이후 변화를 별도 보존한다. **Secondary/local key/종지/구조적 전위 확정은 아니다.** [r3 결과](../output/harmony-candidate-context-2026-09-28-r3/report.json), [악보 검토](http://127.0.0.1:8798/whole-score.html), 계약·회귀·한계 정본 (상세 기록은 공개 브랜치에서 제외). 신규14/전체1,227테스트·6 XML 대조 통과. 다성부 대응/이중 보조음 설명이 다음이며, 직접 해결이 없음을 반증으로 사용하지 않는다. 운영/Core/기존 선택 미변경. 아래는 이전 이력이다.

**최신 완료 — 비구성음/생략음 포함 후보 생성:** `harmony_open_candidates` v0.1은 관측된 template pitch class가2개 이상이면 3/7화음 후보를 보존하며 미설명음·미관측 구성음을 따로 남긴다. 소나타1번 같은 `[0,125)`에574창/21,815후보; 무관한 후보도 많아 정확도 개선 수치가 아니다. 15/17/19의 B♭minor/B♭dominant7,29/30뒤 절반 Gdim7,31앞 절반 A♭major+미설명G5/B♭5를 후보로 보존했다. **기능/전위/이중 보조음 확정과 자동 순위는 아직 없다.** 사용자30마디 viio34의 뒤 절반 범위는 별도 후속 기록으로 확정. 신규15/전체1,213테스트·9 MusicXML 대조 통과. [8795 전체 악장 후보 비교](http://127.0.0.1:8795/whole-score.html), [r2 보고서](../output/harmony-open-candidates-2026-09-28-r2/report.json), 계약/한계/재현 (상세 기록은 공개 브랜치에서 제외). 다음은 전후 target·베이스/전위·이중 보조음을 통해 후보를 구별하는 단계이며, 후보 수가 늘어난 것을 학습/정답 향상으로 표현하지 않는다. 운영5173/Core 미변경. 아래는 이전 이력이다.

**최신 사용자 검토 — 소나타1번 15/17/19,29–31마디:** ii6→V56/V→V7 반복, V/viio34 구간, 31마디 c.t.에 관한 의견을 원XML·교정IR·원주석·당시 계산 및 앞뒤12마디 context와 함께 동결했다. 추가 답변으로 **c.t.=Changing Tone / Double Neighboring Tone(이중 보조음)**임을 확인했다. [사례 설명/남은 범위 확인](../reports/reviewer-cases/sonata1-harmony-2026-09-28/REVIEW.md), [음표·색칠·해시 연결](../reports/reviewer-cases/sonata1-harmony-2026-09-28/archive-r1/feedback-context.json). 29 G3 및31 G5/B♭5의 보라는 특정 화음 후보의 철자 보류이며 비화성음 판정이 아니었다. 30마디 전후 음집합이 달라 whole-measure label은 보류한다. 저장을 자동 규칙 학습/운영 반영으로 표현하지 않는다. 아래 항목은 구현 이력이다.

**최신 완료 — 소나타 1번 1악장 / 조건부 경과·보조 형태:** `harmony_conditional_ornaments` v0.1이 같은 명시적 성부의 연속 세 음을 고정 화음 경로 아래에서 검사한다. 앞 32개 물리 마디 `[0,125)`에 기존 엄격한 후보 추출을 적용한 결과 5구간, 경과 형태 4개, 조건부 장식음 성립0이었다. **정확도 향상이나 장식음 부재를 뜻하지 않는다.** 완전한 두 3화음 집합을 요구하는 선행 추출이 비화성음 포함 구간을 놓칠 수 있다는 병목을 확인했다. 다음은 이 후보 생성 관문을 일반 규칙으로 넓히고 화음/비화성음 가설을 함께 대조하는 단계다. 전체 악장 8페이지·1,693note 연결 검증, 주석241개 별도 보존(추론 입력 아님), 신규11/전체1,194테스트 통과. [소나타1번 전체 악장](http://127.0.0.1:8794/real-cases/beethoven-sonatas--01-1/whole-score.html), [최종r3 결과](../output/harmony-ornaments-sonata1-2026-09-28-r3/report.json), 정본 계약·실패·재현 (상세 기록은 공개 브랜치에서 제외). **전체 악장 분석 완료/비화성음 확정/운영5173 반영은 아니다.** 아래 '최신' 항목은 이전 이력이다.

**최신 완료 — 유지/교체 설명 대조 및 전체 악장 화면:** `harmony_path_explanation` v0.1이 한7화음/두3화음 경로를 같은 sound-time 셀에 놓고 비교한다. 13입력 행의 동일 중복3개를 제거한10고유 후보 중7은 구성음 설명 동일,3은 전후 연장 가정에서만 차이; **원 비교 범위 내부는 모두 같은 구성음 설명, 자동 선택0**. 큰 화음의 포괄력이 높은 것을 정답 근거로 쓰지 않는다. 사용자 요청에 따라 전체 악장 3/9/8페이지, 합계4,473note ID 검증 및 구간 클릭 색칠/페이지 이동 제공. [8793 전체 악장 목록](http://127.0.0.1:8793/index.html), [베토벤 전체 악장](http://127.0.0.1:8793/real-cases/reviewm_29e951c323f0a74694a0/whole-score.html), [r2 결과](../output/harmony-path-explanation-2026-09-28-r2/report.json), 계약·사례·재현 정본 (상세 기록은 공개 브랜치에서 제외). 15 XML 대조·신규14/전체1,183테스트 통과. **전체 악장 화성 분석 완료가 아니며 운영5173/Core/원주석/기존 선택 미변경.** 다음은 남는 비구성음과 설명 차이에 교재 기반 조건부 장식/지연/pedal 설명을 연결하는 단계다. 아래 항목은 이전 이력이다.

**최신 완료 — 도착 전후의 실제 지속·재등장 구별:** `harmony_temporal_context` v0.1이 앞뒤 각1분모박의 모든 성부 attack/release, 동일 sound의 지속, 별도 sound 재타격, 쉼/문맥 잘림을 구분한다. 앞뒤 구성음 표는 **도착 후보를 가정한 검사이지 앞뒤 화음 확정이 아니다.** 실제47경로/52후보 비교 중17미확정·2소속 교대·33문맥 보류; 교대2회는 베토벤 동일 짧은 창의 두 후보 비교이며 독립 개선2건이 아니다. 자동 선택0. 18 XML 대조 및 신규20/전체1,169테스트 통과. [8792 사례](http://127.0.0.1:8792/index.html), [베토벤 전후 색칠](http://127.0.0.1:8792/real-cases/reviewm_29e951c323f0a74694a0/temporal-view/polyphonic.html), [r4 결과](../output/harmony-temporal-context-2026-09-28-r4/report.json), 정본 계약·실패 이력·재현 (상세 기록은 공개 브랜치에서 제외). **운영5173/Core/원주석/화음 선택 미변경.** 다음은 동일 전체 범위의 화음 유지/교체 설명을 반례와 함께 비교하는 단계다. 아래 '최신'은 이전 이력이다.

**최신 완료 — 같은 시간창·모든 성부의 후보 대조:** `harmony_path_contrast` v0.1은 공통 구성음/한 후보에서만 구성음/양쪽 비구성음/철자 보류를 분리한다. 같은 sound ID와 음형을 겹친 창에서 독립 투표로 세지 않는다. 실제47경로 중21경로에 비교 가능 후보가 있었으며52쌍 비교 중19는 관측 소속 차이 없음,33은 성부·문맥 보류, **새 구별 판정/자동 선택0**이다. 6종×3변형=18 MusicXML 대조 및 신규14/전체1,149테스트 통과. [8790 사례 목록](http://127.0.0.1:8790/index.html), [베토벤 공통음 색칠](http://127.0.0.1:8790/real-cases/reviewm_29e951c323f0a74694a0/contrast-view/polyphonic.html), [최종r3 결과](../output/harmony-path-contrast-2026-09-28-r3/report.json), 계약·한계·재현 정본 (상세 기록은 공개 브랜치에서 제외). **정확도 향상 입증 아님; 운영5173/Core/주석/기존 선택 미변경.** 다음은 도착 창 밖의 구성음이 실제로 앞뒤 어느 시점에 울리는지, 그 맥락이 화음 유지/변경 가설을 구별하는지 대조하는 단계다. 아래 '최신'은 이전 이력이다.

**최신 완료 — 중간 음 경로의 화음 조건부 설명:** `harmony_intervening_paths` v0.1은 모든 중간 attack·쉼·겹침을 보존하고, 저장된 화음 후보 아래에서 도착 음군의 구성음 펼침 및 연속 세 음의 경과/보조 모양을 구별한다. 실제47경로 중 베토벤4경로(2도착 음군)의 구성음 펼침이 후보와 양립했다. **쉼 이전 음의 해결 확인/화음 정답 선택이 아니다.** 모차르트 두 사례는 새 설명0. 8종×3변형=24 MusicXML 대조·철자/음가 재구성, 신규15/전체1,135테스트 통과. [8788 목록](http://127.0.0.1:8788/index.html), [베토벤9–10마디 경로 색칠](http://127.0.0.1:8788/real-cases/reviewm_29e951c323f0a74694a0/path-view/polyphonic.html), [최종r3 결과](../output/harmony-intervening-paths-2026-09-28-r3/report.json), 계약·실패 이력·재현 정본 (상세 기록은 공개 브랜치에서 제외). 기존 자료·후보·경고 재현/불변 확인. **Core/원주석/운영5173/자동 화음 선택 미변경.** 다음은 이 설명이 양쪽 화음 가설에 공통인지, 한쪽만 설명하는지를 전체 성부·지속 구성음까지 포함해 비교하는 단계다. 아래 항목은 이전 이력이다.

**최신 완료 — 지연 연결의 반례·추가 검토 근거:** `harmony_link_counterevidence` v0.1은 중간 attack 생략, 이미 나온 동일 목표음, 짧은 음형 재시작 대안, 동시음 성부 모호함과 긴 공백을 별도 경고로 보존한다. 실제47음쌍 중38에 검토 사유가 있으며 **오답38개를 증명한 것은 아니다**. 기존 끝점 양립3고유 음쌍 중2에 중간 경로/앞선 목표음 경고가 붙었다. 경고 없는9쌍도 미확정이다. 4종×3변형=12 XML 대조, 신규12/전체1,120테스트 통과. [8787 사례 목록](http://127.0.0.1:8787/index.html), [모차르트 음표 색칠](http://127.0.0.1:8787/real-cases/reviewm_555ff701230fc0b8ee66/counter-view/polyphonic.html), [최종r2 결과](../output/harmony-link-counterevidence-2026-09-28-r2/report.json), 계약·재현·한계 정본 (상세 기록은 공개 브랜치에서 제외). 기존 입력/후보 재현·파일 불변 확인. **자동 선택/운영5173/Core 미변경.** 다음은 보류된 중간 경로를 분산 진행/새 음형이라는 경쟁 가설로 설명할 수 있는지 검사하는 단계이며, 경고 없음만으로 연결을 승격하지 않는다. 아래 '최신' 항목은 이전 이력이다.

**최신 완료 — 쉼·분산 도착의 제한적 연결:** `harmony_delayed_links` v0.1은 같은 기보 성부의 첫 다음attack까지 최대2분모박, 도착 창1분모박 미만의 모든 부분 대응을 별도 가설로 보존한다. 쉼·중간attack 삭제 없음. 실제3사례11음군/47가능 음쌍/84부분 대응, K281-3의 끝점 역할 양립10회는3음쌍의 중복 문맥이며 **확인된 해결이나 정확도 향상 아님**. 신규21/전체1,108테스트 통과, 기존 자료 불변. [8786 목록](http://127.0.0.1:8786/index.html), [베토벤 클릭 색칠](http://127.0.0.1:8786/real-cases/reviewm_29e951c323f0a74694a0/delayed-view/polyphonic.html), [최종r2 결과](../output/harmony-delayed-links-2026-09-28-r2/report.json), 정본 계약·한계·재현 (상세 기록은 공개 브랜치에서 제외). **직접 해결로 사용 금지, 자동 선택/운영 미변경.** 다음은 중간 경로의 연속성 대조와 쉼 뒤 독립 재진입 반례로 오연결을 검사하는 단계다.

**최신 완료 — 동시 화음의 부분 성부 대응 가설:** `harmony_polyphonic_links` v0.1은 같은 기보 성부의 정확히 맞닿는 release/attack 음군에 대해 미연결·교차를 포함한 모든 부분 대응을 보존한다. 화음 라벨로 연결을 고르지 않는다. 실제 모차르트 3음군/8가능 음쌍/13부분 대응, 베토벤은 해당 성부의 시간 간격 때문에 0음군. 새 음군이 기존 비교 경계와 일치하지 않아 **추가 해결 지지/화음 선택 변경은 0**이며 정확도 향상 아님. 신규16/전체1,087테스트,4 MusicXML 대조, 실제77음 렌더 ID 검증 및 이전 파일 불변 확인. [8785 검토 목록](http://127.0.0.1:8785/index.html), [모차르트 클릭 색칠](http://127.0.0.1:8785/real-cases/reviewm_6fb07c245142d9e0421f/polyphonic.html), [최종r4 결과](../output/harmony-polyphonic-links-2026-09-28-r4/report.json), 정본 계약·실패/기권·재현 (상세 기록은 공개 브랜치에서 제외). **운영5173/Core/원주석 미변경.** 다음은 쉼·분산 도착을 포함한 제한적 연결 후보 계약과 반례 검증이며 아직 구현하지 않았다. 아래 항목은 이전 이력이다.

**최신 완료 — 실제 해결 누락의 XML 성부 대조:** [8784 사례](http://127.0.0.1:8784/index.html), [베토벤 감사 표](http://127.0.0.1:8784/real-cases/reviewm_29e951c323f0a74694a0/index.html#voice-revision-audit). `harmony_voice_revision_audit` v0.1이 source-identity r4 사본으로 같은13후보를 검사했다. 문맥77음 중 구형 voice 번호 불일치74개지만 새 고유 연결은 모차르트 C5→B♭4 하나뿐; 기존 연결 소실0/구별 해결0. 교정 후에도 실제 같은 XML voice의 동시 음군14sound가 있어 내성 대응이 미해결이다. 교정3악장4,473note XML 대조, 전체1,071테스트·독립 검사 통과. **운영 migration/자동 화음 변경/정답률 향상 아님.** [최종r3 보고서](../output/harmony-voice-revision-audit-2026-09-28-r3/report.json), [검증](../output/harmony-voice-revision-audit-2026-09-28-r3/verification.json), 정본 계약·한계·재현 (상세 기록은 공개 브랜치에서 제외). 다음은 같은 기보 voice의 화음 안에서 성부 진행 복수 대응을 검증하는 단계다. 아래 최신 항목들은 이전 이력이다.

**최신 완료 — 공통 지지 / 한 계열 조건부 지지 구분:** [8783 대조·실제 악보](http://127.0.0.1:8783/index.html). `harmony_reading_contrast` v0.1은 같은 음 연결을 다른 역할/창으로 다시 설명해도 독립 투표로 세지 않고, 양쪽 공통/유지쪽만/분리쪽만/미확인/비교누락으로 구분한다. 신규4형태×3변형=12 XML→IR 대조 입력은 기대한 근거 분류와 일치. 실제13겹치는 후보는 한 계열만 지지하는 해결0이며 모차르트 A→B♭는 공통 근거다. **실제 정확도 향상/과병합 해결 아님; 기존 비용·선택10파일·운영5173 미변경.** 전체1,064테스트,97후보·290근거 단위 독립 검사 통과. [최종r2 보고서](../output/harmony-reading-contrast-2026-09-28-r2/report.json), [검증](../output/harmony-reading-contrast-2026-09-28-r2/verification.json), 계약·사례·한계·재현 정본 (상세 기록은 공개 브랜치에서 제외). 다음은 가중치 변경이 아니라 실제 다성부의 보류 연결을 원XML/교정 성부 revision과 대조하는 감사다. 아래 최신 항목은 이전 단계 이력이다.

**최신 완료 — 복수 해석에 전후 성부 연결 증거 추가:** [8782 검토 목록](http://127.0.0.1:8782/index.html), [모차르트 A4→B♭4](http://127.0.0.1:8782/real-cases/reviewm_555ff701230fc0b8ee66/index.html). `harmony_reading_voice_context` v0.1은 유일·연속·단음 IR 성부의 철자/옥타브와 앞뒤1·2분모박의 완전 화음 후보를 비교한다. 실제13겹치는 후보 중9내부 연결, 내부 해결0, 외부 해결2후보(**한 음쌍의 중복 문맥**)다. Aø7 유지와 Cm→Adim 분리 모두 같은 해결을 지지하므로 승자는 미결정. **기존 비용/선택10파일·Core·원주석·운영5173 미변경.** 신규18/전체1,054테스트, 85후보의 저장 근거 독립 검사 통과. [최종r3 결과](../output/harmony-reading-voice-2026-09-28-r3/report.json), [검증](../output/harmony-reading-voice-2026-09-28-r3/verification.json), 계약·한계·재현 정본 (상세 기록은 공개 브랜치에서 제외). 실제 XML 성부/대위적 성부 확정은 아니며 동시 화음의 성부 대응은 보류한다. r1/r2는 중간 버전. 다음은 양쪽 공통 지지와 구별 근거를 분리하는 대조 실험 및 교정 성부 revision 재검증이다. 아래 최신 항목들은 과거 이력이다.

**최신 완료 — 분산 구성음의 시간 누적 복수 해석:** [8781 비교](http://127.0.0.1:8781/index.html), [베토벤 실제 악보](http://127.0.0.1:8781/real-cases/reviewm_29e951c323f0a74694a0/index.html). `harmony_distributed_readings` v0.1은 실제 attack 앞뒤0.5/1/2분모박 창의 sounding 구성음을 모아 두3화음/단일7화음 가설을 보존한다. 이전 수직 방식 후보0이던 실제10사례 중 베토벤1·모차르트2사례,6문맥에13개 겹치는 후보가 생겼다. **정답률 향상/자동 선택 변경 아님.** 표시한 실제 악보3개에 유지/분리 구간선과 색칠을 추가했다. 전체1036테스트,36합성입력·85대안 비용/음표 검증, 기존 수직21입력 결과와 실제 선택10파일 불변. 정본 기록 (상세 기록은 공개 브랜치에서 제외), [r1 보고서](../output/harmony-distributed-readings-2026-09-28-r1/report.json), [독립 검증](../output/harmony-distributed-readings-2026-09-28-r1/verification.json). 페달/NCT를 지워 후보를 만들지 않는다. 다음은 원주석을 정답 입력으로 쓰지 않고 전후 성부 해결·화성 리듬·철자를 통해 두 가설의 지지/반대 근거를 보강하는 단계. 운영5173 미변경.

**최신 완료 — 공통음 두3화음 / 단일7화음의 복수 해석·비용 분해:** [8780 비교 악보](http://127.0.0.1:8780/index.html). `harmony_shared_tone_review` v0.1은 새 구성음 attack·이전 구성음 release·공통음 지속·베이스 교체를 보존하고 두 해석의 기존 목적함수 비용을 비교한다. 대표 C→Em은 분리0.340 대 Cmaj7 유지0.245; 추가 구간/교체 비용이 국소 적합도 이득을 상쇄한다. **자동 분리/새 승자 선택은 하지 않음.**7형태×3변형=21입력,63겹치는 대안 비용 검증, 전체1024테스트. 실제10사례20문맥의175인접쌍은 후보0: 짧은 수직 지속132, 불완전3화음41, 공통음/합집합 불일치2. 정확도 향상이 아니라 현재 규칙의 적용 범위 한계를 확인했다. 다음은 분산·장식 구간에서 시간 누적3화음 후보와 지속7화음 가설을 비교하는 단계다. 정본 기록 (상세 기록은 공개 브랜치에서 제외), [최종r3 보고서](../output/harmony-shared-tone-2026-09-28-r3/report.json), [독립 검증](../output/harmony-shared-tone-2026-09-28-r3/verification.json). 이전 선택 사본 hash 불변; 운영5173·Core·원주석 미변경.

**최신 완료 — 반복 음형 내부 경계의 선택 비용 실험:** [8778 비교 악보](http://127.0.0.1:8778/index.html), [베토벤 OFF/ON](http://127.0.0.1:8778/real-cases/reviewm_29e951c323f0a74694a0/index.html). 별도 `harmony_figure_shadow` v0.1이 완전 화음으로 모이는 반복 cell 안의 분할에 작은 비용을 부과하되 실제 수직 화음 교체 증거에서는 기권한다. 실제10사례20문맥 중1문맥 변경, 문맥 일치6→7/10; **새 Ab 반감7 판정의 정확성은 미검증**이다. 새 대조12입력은 OFF/ON 모두9/12, C장3화음↔E단3화음을 C장7화음으로 합치는 반례는 미해결. 기존84입력 변경0, 전체1010테스트 통과. 운영5173·기존 multiscale v0.5·Core·프레이즈·주석은 그대로이며 서비스 승격 보류. 정본 규칙·반례·재현 (상세 기록은 공개 브랜치에서 제외), [r2 보고서](../output/harmony-figure-trial-2026-09-28-r2/report.json), [독립 검증](../output/harmony-figure-trial-2026-09-28-r2/independent-validation.json). 다음은 공통음이 많은 두 화음의 교체와 단일7화음 유지 가설을 분리 검증하는 단계다. 아래 '최신' 항목은 과거 단계의 이력이다.

**최신 완료 — 실제 탈락 조건과 반복 음형 진단:** [8777 진단](http://127.0.0.1:8777/index.html), [베토벤 실제 악보](http://127.0.0.1:8777/real-cases/reviewm_29e951c323f0a74694a0/index.html). 고정10사례40조건의66경계 중35는 앞선 attack 후보 없음; 검사한66onset은 prefix 불일치26·지속 최저음22 등이 첫 탈락 조건이다. `harmony_figure_evidence`로 동일 voice의 리듬과 약한 음정 변형, 베이스 attack/지속을 분리 기록했다. 베토벤·모차르트·코렐리에서3고유 음형 쌍/4조건의 내부 경계 검토 신호를 찾았지만 **자동 화음·경계는 그대로**다. 합성84/실제40 기존 대안 객체 불변, 전체1002tests. 정본 계약·한계·재현 (상세 기록은 공개 브랜치에서 제외), [r3 저장 결과](../output/harmony-ownership-diagnostics-2026-09-28-r3/report.json). 실제 악보의 표시 context만 원XML 대응을 검증했으며, 오래된 IR의 다른 구간 locator 누락은 미교정. 다음은 동일 음형 안의 실제 화음 교체 반례를 포함한 선택 규칙 on/off 검증. 운영5173 미변경.

**최신 구현 — 공통음 경계 대안 검토:** `harmony_boundary_ownership` v0.1은 선택된 경계 앞2분모박 안의 실제 저음 attack과 뒤 완전 화음의 철자를 확인하여 대안을 보존한다. [8776 비교 악보](http://127.0.0.1:8776/index.html)에서 파란 공통음과 기존/대안 범위를 확인한다. 기본3불일치(이조/음가 포함9입력)의 의도를 모두 대안으로 찾았지만 기존과 비용이 동점이다. **자동 선택75/84는 그대로**, 같은 화음42입력 후보0개, 실제10사례40조건도 후보0개이므로 일반 정확도 향상을 주장하지 않는다. 전체993테스트 통과. 정본 계약·결과·다음 순서 (상세 기록은 공개 브랜치에서 제외), [r3 보존 산출물](../output/harmony-boundary-ownership-2026-09-28-r3/report.json). 다음은 실제 사례의 후보 탈락 조건과 반복 반주 주기/저음 재시작 증거 검토. 엔진v0.5/운영5173/프레이즈/원주석 미변경. 아래 '아직 구현 전'은 직전 벤치마크 당시 기록이다.

**최신 검증 — 분산화음의 유지/변경을 분리 측정:** 엔진v0.5는 수정하지 않고 `harmony_arpeggio_benchmark`를 추가했다. [8775 비교 악보](http://127.0.0.1:8775/index.html): 기본28형태(같은 화음14 + 변경14), 이조/음가 축소 포함84입력 ×3조건. 같은 화음14/14, 변경11/14가 작성 의도와 일치(84변형 중75; 실제 악보 정답률 아님). 세 조건의 결과가 같아 이 묶음은 최근 보완의 향상을 입증하지 않는다. 실제 고정10사례 on/off에서는3사례가 달라지고 문맥 안정은5→6이지만 Beethoven02-3은 안정→불안정이다. 다음은 **공통음으로 시작하는 새 분산화음의 제한적 역추적·복수 경계 후보** 검증이며 아직 구현하지 않았다. 전체980테스트 통과. 원XML/IR/계산 및 정본 기록 (상세 기록은 공개 브랜치에서 제외) 보존, 운영5173 변경 없음.

**최신 구현 — 화음 과병합 억제:** multiscale v0.5에 `harmony_boundary_contrast`의 박자 상대적·복수 음고 교체 soft penalty를 연결했다. [8774 m10–12](http://127.0.0.1:8774/08-1-window-2.html)에서 m12 `[46,47)` F minor를 복원하여 앞 `V/iv` 해결 후보와 실제 베이스 기준 `iv64`가 보인다. 마지막 C–D–B는 철자/불완전 화음 문제로 unknown, m11 C-only까지 포함한 부모 화음 과병합은 그대로다. 전체974테스트 통과. [8창 비교](../output/sonata-verification-2026-09-28-r3/boundary-verification.json):1창 변경. [고정30사례 on/off 비교](../output/harmony-boundary-contrast-2026-09-28/report.json):28사례 유지,2사례/60실행 중2실행 변경, 문맥 안정17→18(정답률 아님); Corelli 주변 구간 변화는 추가 검토 필요. **연구용 적용이며5173/프레이즈/원주석 미변경.** 규칙·가중치·부작용·재현 정본 (상세 기록은 공개 브랜치에서 제외).

**최신 구현 — 교재26장 Secondary 해결 관계 연결:** multiscale v0.4가 기존 베이스 단계 다음에 `harmony_applied_context`를 호출한다. 음표 철자와 자동 선택된 다음 화음, 같은 기보 성부 안의 이끎음/7음 해결 음고쌍을 이용하며 원주석 화음은 입력하지 않는다. [8773 악보 m10–12](http://127.0.0.1:8773/08-1-window-2.html)에서 m11 끝만 `V7/iv` 후보로 표시하고 클릭하면 근거와 기존 `I7` 단순 환산을 구분한다. 로마자 분모의 조성은 아직 원자료 표시 기준이다. 전체966테스트,8창 회귀 검사 통과(기존 선택 화음/비용/경계 무변경, 해결 후보3건; 정답률 아님). **과병합 자체·분산 해결·전조·운영5173 연결은 미해결.** 정본 계약·재현·한계 (상세 기록은 공개 브랜치에서 제외), [독립 검사](../output/sonata-verification-2026-09-28-r2/applied-verification.json). 아래 전위 단계는 직전 이력이다.

**최신 구현 — 베이스/전위 실제 연결:** `harmony_multiscale_shadow` v0.3의 analyze가 `harmony_bass`를 호출하며 연구용 [8772 악보](http://127.0.0.1:8772/08-1-window-2.html)에 반영됐다. m10후반 iiø65, m12첫 iv64 및 페달 제외 iv6 대안 표시. 실제 최저음 관측·조건부 전위·페달 후보·원주석 pedal을 구분한다.8창258cell 독립 확인, 직전 후보/비용/span 무변경, 전체953테스트 통과. **Secondary/과병합/운영5173 연결은 아직 아님.** 정본 계약·한계·검증 기록 (상세 기록은 공개 브랜치에서 제외). 아래 '진단만 수행'은 직전 턴 이력이다.

**2026-09-28 최신 사용자 검토:** 비창1 m10–12에서 전위 표시 미연결, Secondary 기능 미구현, m11 끝 C7 색채음의 앞부분 과병합, C pedal 원주석의 화면 문맥 누락을 진단했다. `iv6/iv/#viio6`을 오주석으로 곧바로 바꾸지 않는다(페달 위 화성 및 자연단음계 표기 관례 확인). [원문/원XML/IR/당시 계산 보존 사례](../output/harmony-feedback-2026-09-28-op13-1-m10-12/review.json), 상세 진단 및 다음 순서 (상세 기록은 공개 브랜치에서 제외). **이번 턴은 진단·기록만 수행, 엔진/UI/원주석 변경 없음.**

**현재 최신 — 비창1·3 시간축 차단 해소:** 명시된7:4연음의 tick 반올림 오차를 다른 part 길이로 교차 확인한 뒤, 원본 보존 사본에서 각각7음만 exact rational 음가로 복원했다. divisions480→3360. [사본·수정 근거·독립 검증](../output/tuplet-time-repair-2026-09-27-r1/), [r3 악보 검토](http://127.0.0.1:8771/). 전체6,837음/521쉼표의 원XML 대응 및 양쪽 시간축 검사 통과, 전체939테스트 통과. 주석868개 중13개 ambiguous는 여전히 격리한다. 두 자동 트랙 모두 시간 교정 사본을 사용하므로 회색/보라는 원본/시간 교정 비교가 아니라 음표 연결 IR 전후 비교다. **운영·원본 파일 미변경, 전곡 화성 정확도 검증/Secondary·종지 문제 해결은 아님.** 일반 규칙·제약·좌표 alias·재현은 개발 기록 (상세 기록은 공개 브랜치에서 제외) 최상단이 정본이다. 아래 r1의1·3악장 차단 기록은 이번 사본에 한해 해소됐으며 과거 이력으로 보존한다.

**최신 검토:** [소나타 검증 r1](../output/sonata-verification-2026-09-27-r1/report.json), [악보15페이지](http://127.0.0.1:8770/). Op.13의3악장+Op.2 No.1의4악장 요청 중 비창2와 소나타1의4악장이 전체 입력 검사를 통과했다(8,439음/622쉼표). 각 처음·중간·끝4마디를 동일 엔진으로 교정 전후 계산했으며15창 모두 화음 이름/span 동일. 비창1은 X1마디 성부간1/480 quarter 차이, 비창3은200마디1/160 quarter 초과 및 parser41event 시간차로 차단. 원본 임의 교정 없음. 원자료 종지 표시는 가능하지만 자동 종지·프레이즈 비교는 미실행. 전체922테스트 통과. **전곡 화성 정확도 검증/세 과제 전체 해결/production 적용은 아직 아니다.** 원인·한계·다음 계약·재현은 개발 기록 (상세 기록은 공개 브랜치에서 제외) 최상단 참조. 아래 candidate r4는 이전12악장의 완료 기록이다.

**최신 완료:** [교정 candidate revision r4](../output/source-identity-revision-2026-09-27-r4/candidate_manifest.json), [독립 검증](../output/source-identity-revision-2026-09-27-r4/independent_validation.json). 원본 순서 기반 grace tie 계약을 구현하여 미연결 endpoint0(12악장 표본).16,067음·2,018쉼표 ID/음고/음가 보존, 주석2,467개 라벨/시간좌표 유지, sounding15,877개. physical measure/source voice 및 grouping aliases를 포함한 새 revision을 생성했다. 전체914테스트 통과. **운영 manifest/기본 parser/UI 미변경, 화성 재계산·시각 검토 미실행**. 다음은 candidate r4 입력으로 영향 사례의 화성/NCT 재계산과 악보 검토. r1–r3는 중간 버전이며 사용하지 않는다. 계약·주의점·재현 정본 (상세 기록은 공개 브랜치에서 제외).

**현재 단계:** [sequence r2](../output/source-sequence-audit-2026-09-27-r2/report.json)에서 미확정29음 전부의 연결 근거를 복원하고16,067음/2,018쉼표 대조를 통과했다. 특수 마디의 local onset22개 교정 제안도 발견. [tie r3](../output/voice-tie-impact-2026-09-27-r3/report.json)는 XML voice만 교체하면 정상 타이가 끊어짐을 확인하고 유일·명시·연속 tie graph로 cross-voice9개 edge를 연결했다. **grace tie4 endpoint는 미확정이며 발행 전 계약 필요**. 전체895테스트 통과; 운영/기본 parser/manifest 그대로. [7개 전후XML 사례](../output/source-identity-cases-2026-09-27-r1/index.json), 정본 상세 기록 (상세 기록은 공개 브랜치에서 제외). 다음은 grace tie/physical measure/revision-alias 계약과 candidate migration. 아래29음 미확정 설명은 당시 기록이며 이번 복원 근거로 갱신된다.

**최신 진단:** voice-provenance-0.1.0. 성부 번호 불일치12,083음은 모두 현재 마디에 Voice 객체가 없는데 기존 문맥 검색으로 번호를 가져온 경우였다. 실제 Voice 객체가 있는2,786음은 원XML과 일치. [12악장 결과](../output/voice-provenance-audit-2026-09-27-r1/report.json), 원인·교정 제안·이전 계획 정본 (상세 기록은 공개 브랜치에서 제외). 기존 note ID에 연결한 별도 제안만 생성, **기본 parser/운영 IR/타이 변경 없음**. 전체872테스트 통과. 다음은29음의 원본 연결, Rest/voice/tie 영향 감사와 versioned migration이다. 아래 원본 연결 교환 수정은 완료됐지만 성부 문제까지 운영에서 해결됐다는 뜻은 아니다.

**최신 수정:** source-note-mapping-0.2.0. 동일 onset/pitch의 음표가 해시 순서로 교환되는 버그를 재현·수정했다. [검증 결과](../output/source-note-mapping-repair-2026-09-27-r1/report.json): 12악장16,067음, 기존 불일치35음 수정, 이전17사례 모두 XML 문맥 대조 통과.29음은 alias/grace/모호함 등으로 기권. 전체856테스트 통과. **코드 반영 완료, 과거 package 보존/후보 수정본 생성, 운영 dataset 교체 미실행**. logical voice hint의 광범위한 불일치는 별도 후속 과제. 아래 부록 당시2사례 격리는 후보 수정본에서 해소됐지만 과거 r4 결과는 그대로 보존한다. 자세한 원인·재현·적용 범위는 최신 정본 (상세 기록은 공개 브랜치에서 제외).

최신 단계: **부록 I–III 검토·원음 보존형 축약 제안 계약·XML 대조**. 정본 기록 (상세 기록은 공개 브랜치에서 제외), [최종 r4 결과](../output/harmony-appendices-audit-2026-09-27-r4/report.json), [원XML 대조/격리](../output/harmony-appendices-audit-2026-09-27-r4/verification.json). train12악장/17저장사례. 문맥음633회 대조 중4회 음가 연결 불일치가 있어2사례 격리,15사례 일치. **684 관련 테스트 통과**는 음악 정답률이 아니다. 본문33장과 제공 부록 독해 완료, 인쇄708쪽 원파일 공백은 미확인. 다음은 동일 onset/pitch 다성부 note 연결 문제의 재현·교정 검토가 우선이다. 자동 축약/전체 이론 통합/production 적용 완료가 아니다. 과거 결과 보존.

최신 부록 사례 파일: [원악보 중복음 확인](../output/harmony-appendices-audit-2026-09-27-r4/index.html). Beethoven01-2 / MozartK280-1 원음을 보라색 표시한다. XML 문맥/engraving mapping 검사는 통과했으나 file URL 브라우저 도구 접근이 차단되어 시각 QA는 미완료. 로컬 파일을 직접 열어 볼 수 있다. 완성된 화성/축약 분석 화면이 아니다.

최신 **화면**은 여전히 [분산/생략 4조건 비교 7사례](../output/harmony-ablation-visual-review-2026-09-27-r2/index.html), 서버 [8769](http://127.0.0.1:8769/). 같은 30사례를 240회 계산해 두 보완의 효과를 분리했다. 기존 결과 120개 재현 검사 통과. 안정성은 보완 없음17/30, 생략만15/30, 분산만16/30, 둘 다17/30이며 정답률이 아니다. 새 규칙 승격 없음. 아래 8768 화면은 직전 단계로 보존한다.

악보로 확인하기: [이번 분산·생략 보완 7사례](../output/harmony-multiscale-visual-review-2026-09-27/index.html), 실행 중에는 [로컬 사례 목록](http://127.0.0.1:8768/). 원자료/직전 temporal v0.3/이번 multiscale v0.1을 악보 위에서 비교한다. [이전 joint→temporal 5사례](../output/harmony-visual-review-2026-09-27-r7/index.html), 8767 서버는 보존한다. 자세한 실행·표기 제약은 최신 개발 기록 (상세 기록은 공개 브랜치에서 제외)에 있다. 두 UI 모두 production 승격이 아니다.

## 1. 읽는 순서와 기록의 정본

1. 이 문서: 무엇이 구현됐고 무엇이 아직 적용되지 않았는지 확인한다.
2. [통합 실행 계획](HARMONY_COMPOSITION_HARNESS_IMPLEMENTATION_PLAN.md): 전체 악보 이해 → 구조 분석 → 작곡·편곡의 목표, 작업 카드, 평가 기준.
3. 교과서–사례 연결 및 개발 기록 (상세 기록은 공개 브랜치에서 제외): 날짜별 문제, 가설, 실험, 결과, 채택/보류 이유. 최신 항목이 위에 있다.
4. [문서 지도](DOCUMENT_MAP.md): 코퍼스 수입·정렬·검색·검토 화면 등 이전 단계의 상세 기록.
5. [Core 규격](CANONICAL_MUSIC_IR_SPEC_v0.1.md), [시간·ID](ID_AND_TIME_COORDINATE_SPEC.md), [분석 인터페이스](ANALYSIS_INTERFACE_SPEC.md), [미해결 계약](OPEN_QUESTIONS.md).

화성의 날짜별 개발 기록은 교과서–사례 문서에 이어 쓴다. 큰 독립 단계의 보고서를 만들 때도 여기에서 링크한다. 구조 분석/UI 저장소의 기록은 그대로 유지하고, 양쪽을 변경한 경우 서로 링크한다. 동일 결과를 여러 문서에 복사해 서로 다른 최신 상태가 생기지 않게 한다.

## 2. 현재 상태와 아직 하지 않은 것

| 영역 | 확인된 상태 | 과장하면 안 되는 부분 |
|---|---|---|
| 입력·주석 | 코퍼스 등록, 일부 형식 수입/정렬, 출처·구간 연결 및 검토 도구 | 등록한 모든 자료의 수입·검증·훈련이 끝난 것은 아니다 |
| 교재 | Units 1–33 및 제공 부록 I–III 독해·부분 프로토타입 기록 | 인쇄708쪽 미확인; 이론 전체 구현/자동 학습/정확도 검증은 별도 |
| 공동 분석 | 구간·표면 화음·조건부 NCT 후보를 비용으로 비교하는 Python 실험 | 확률이 보정된 AI 모델이나 완전한 기능화성 분석기가 아니다 |
| temporal 실험 | 시간별 국소 지지를 추가하고 기존 경로와 비교 | 분산/생략 화음과 장식된 도착을 아직 충분히 판정하지 못한다 |
| 검증 | 신규 30사례 × 2문맥 × 2엔진 = 120회 계산, 우선 5사례 상세 진단 | train 개발 표본이며 독립 정답률 평가가 아니다 |
| 화면 | MusicSearch에 기존 실험 화성 레이어가 있음 | 최근 joint/temporal 진단 변경은 Viewer·Phrase 판단에 승격하지 않았다 |

최근 harmony 회귀 테스트 **178개 통과**(2026-09-27, 4조건 분리·고정 경로 재채점·문맥 절단·시각 출처 검사 추가). 이 수치는 음악적 정확도가 아닌 프로그램 회귀 검증이다. 이전 144/154/167개 기록은 개발 기록에 보존한다.

Unit 11 전용 `test_cadential*.py` 16개 및 기존 `test_*evidence.py`30개 통과. `cadential_six_four.py`는 두 순간의 철자/베이스와 직접 연결 가능한 단선율 voice만 검사한다. `cadential_six_four_audit.py`는 train 소나타 12악장36사례 및 전후 IR/주석을 보존한다. 모호한 성부/분산/확장/비근음 V 도착 때문에 표면쌍 지원0/36이며 정확도0%가 아니다. 현재 판정기를 종지 자동 탐지기로 연결하면 안 된다.

Unit12 전용 `test_sixth_degree*.py`12개 통과. 기존 harmony178개/Unit11의16개도 재실행했다. `sixth_degree_evidence.py`의 화음 연결 관찰은 조건부 형태 검사이며 성부 추적·종지 판정은 아니다. 특히 source cadence 공란은 negative gold가 아니다.

Unit13 전용 `test_predominant_seventh.py`16개, 전체 `test_predominant*.py`29개 및 기존 harmony178개 통과. `predominant_seventh.py`는 supplied family/key의7음 철자와 같은 성부의 직접 연결 geometry만 관찰한다. 준비의 협화·박절·NCT·화성 자체·지연 해결의 전체 경로는 미확정이다. 신규27사례는 JSON만 보존했고 새 악보 페이지/production 적용은 아직 없다.

Unit14 전용 `test_tonal_role_context.py`11개, 전체 `test_tonal*.py`24개와 harmony178개 통과. `tonal_role_context.propose`는 supplied 가설의 문맥 패턴/증거 필요 조건만 반환한다. V→VI/IV6 또는 IV→I만으로 cadence/Phrase를 확정하지 않는다. 원주석을 사용한180사례이며 blind detection이 아니다. source에 앞 HC가 있는데 V→IV6만 보고 deceptive로 오해할 수 있는 Beethoven 반례도 기록했다.

Unit15 전용 `test_dominant_area_evidence.py`14개, 전체 `test_dominant*.py`20개·tonal24개·harmony178개 통과. `dominant_area_evidence.observe`는 공급된 장조 기준의 이중 음계 좌표/공통3화음 가능성만 계산한다. 전조/토닉화/피벗/종지는 null. r2 source-conditioned44사례의 원자료 라벨과 실제 음표 관찰은 별개다. 화면 적용 전이다.

Unit16 전용 `test_mediant_evidence.py`20개 및 harmony178개·tonal24개·dominant20개 통과. `mediant_evidence.observe`는 supplied key의 III/VII 좌표와 모양 대안을 반환한다. 최종r3 117사례 중52개에 관련 완전 모양 후보가 있으나 정답률이 아니다. 분산/생략/장식 사례를 기권으로 남기며 자연VII 직접 주석은1개뿐이다. 원주석·타이·0길이 grace를 보존. 새 악보 페이지/production 반영 없음.

Unit17 전용 `test_root_position_context.py`18개 및 harmony178개·tonal24개·mediant20개, 합계240개 통과. `root_position_context.propose`는 supplied root triad3개 패턴을 후보화하고 실제 성부/계층/종지 증거를 요구한다.50창 중10개 후보/세 span 모두 일부 완전 모양 지지1개는 정확도가 아니다. minor v의 실제 eligible창0개를 검증 공백으로 기록. merge/sequence/cadence/phrase 판정 null. 화면 반영 없음.

Unit18 전용 `test_diatonic_sequence.py`23개 및 harmony178개·root_position18개·tonal24개·mediant20개, 합계263개 통과. `diatonic_sequence.propose`는 supplied triad4개에서 기본4모델 후보만 생성하며 `compare_voices`는 explicit part/voice별 sounding event의 리듬/도수/반음 이동을 따로 계산한다. 단순 semitone 이조 불일치로 도수 반복을 배제하지 않는다. source 경계/두 화음 단위 의존, polyphonic·불균등 장식·타이 경계 기권 한계.189창·원XML/주석/IR context/hash 보존. 새 HTML/production 적용 없음. 다음 Unit19에서6/3 연속과 연결한다.

Unit19 전용 `test_six_three_context.py`20개와 harmony178개·diatonic_sequence23개·first_inversion7개·root_position18개·tonal24개, 총270개 통과. 사례270창과 테스트270개는 별개. source-conditioned 역할 발생은 경과83/연속42/6음 대안56/보조21이며 복수 후보 가능,148창은 역할 없음. 증III eligible창0개로 실제 검증 공백. VI6/III6를 tonic/dominant로 자동 교정하지 않는다. 새 악보 화면/production 반영 없음.

최신 multiscale 실험은 같은 30사례 × 2문맥을 추가 계산했다. 직전 temporal 대비 복합 문맥 안정성은 **17→17/30**, 라벨 변화 8사례, 안정성 획득/상실 각각 2사례. 5음 생략 및 분산7화음 지지가 개선된 Corelli 사례가 있으나 Beethoven 분산3화음은 미해결이고 경계/라벨 민감성 반례가 남아 **서비스 적용 보류**다. 원인·반례·명령·화면은 최신 개발 기록 참조.

신규 30사례의 복합 문맥 안정성은 baseline 13/30, temporal 17/30이었다. 라벨 변화 9건, 내부 경계 변화 1건이며 **정답률 향상으로 해석하지 않는다**. 안정성이 낮아진 한 사례도 실제 화음은 G7을 유지하고 시작 경계만 달랐다. 이후 진단은 라벨·내부 경계·양끝 지지를 분리한다. 상세 표와 정정 근거는 개발 기록에 있다.

## 3. 구현을 찾는 지도

Unit33 검증: 전용29개 포함 관련655개 통과. train12악장702검토 기록,693literal 경계 관찰. 감7 네 목표 및 V7/Ger6 대안은 supplied shape의 PC 동등성일 뿐 실제 기능 재해석이 아니다. 즉시 다음 가설의 철자/PC 모양 호환, IR 지속/재타격/반음 변화와 source key run을 분리한다. 실제 기능적 이명동음 전조의 양성 검증, 장기 key-area/피벗/공통음 prominence/모티프 확대는 보류. unsupported modifier/다성·잠재성부·grace 역할을 억지로 판정하지 않는다.3사례11음 원XML 대조. 원IR/UI/production 미변경.

Unit32 검증: 전용32개 포함 관련626개 통과.885 case hash·11 code hash·12개 전체악장 geometry 재계산 일치. 기존 주석/조성 없이 IR의 문자적 진행부터 검출하고, 원주석/정렬상태를 나중에 연결한다. 짧은 균등간격/교대 패턴을 음계의 실제 사용으로 승격하지 않는다. 유일한 공동 경로는 병행 옥타브이며6/3 화음이나 성부교환이 아니다. grace는 구조적 중요성 미정으로 보존한다. target=null 주석 처리 오류를 r2에서 수정했고 r1은 중단 이력이다. 실제6–10/옥타브분할 양성 공백, 잠재성부/사행/변형/omnibus·기능/NCT/경계는 보류. UI/production 미변경.

Unit31 검증: 전용32개 포함 관련594개 통과.117 case hash·16 code hash·75사례 evidence 재계산 일치. 혼용/적용의 모양 중첩, 증3화음의5–#5–6 직접 경로, 감7의 공통음 모양/실제 지속/재타격/목표span의 개별 순차 이동을 분리했다. Double mixture·altered V7은 실제 검증 공백. CT 후보2개는 분산/생략·성부연결의 한계가 있어 원주석을 바꾸지 않았다. 공통음 증6/겉보기V7, 단조/7화음 혼용, 하행 bass/5–6–5, 비주석 가설 추론·기능/종지 결정은 보류. UI/production 미변경.

Unit26 검증: 전용27개 포함 관련451개 테스트 통과.204 case hash·13 code hash·4사례 재계산 일치.5유형 applied 가설과 단일 장/단 목표, 앞뒤 source 화음 비교, 실제 이끈음/7음 직접 경로를 분리했다. 단조 온음계 적용화음과 같은목표 감3→감7 연속도 보존. source key/라벨/목표/구간 의존, 비주석 전체 분석/Secondary 정확도 검증은 아직 아님. 중첩target/증6/장식6/4·형식·성부연결 보류, production/UI 미변경.

Unit27 검증: 전용29개 포함 관련480개 테스트 통과.45 case hash·14 code hash·3사례 문맥/음표 근거 재계산 일치. 같은 화음의 양쪽 조성 소속·PD/D/T 모양·원주석 연속 구간을 따로 기록하며 source HC/실제 무음을 보존한다.34창에 unknown 화음,26 run은 미검증/누락에서 끝나며 제한된 관찰 창에 전체 run이 포함된 것은7사례다. 조성/경계/화음 가설은 source-conditioned이고 자동 전조 탐지/정답률은 아니다. production/UI 미변경.

Unit28 검증: 전용26개 포함 관련506개 테스트 통과.202 case hash·14 code hash·4사례 재계산 일치. 원modifier의 의미는 아직 미해석이며, source-conditioned V7 기준과 실제 근음/3음/5음/7음·추가음·성부 경로를 분리했다. 근음/7음 없는 단독4/6음을 대체형화음으로 세지 않도록 r2에서 좁혔다. 전이/암시해결·페달·비주석 기준 추론·일반 NCT/확장화음 판정은 보류, UI/production 미변경.

Unit29 검증: 전용26개 포함 관련532개 테스트 통과.4 case hash·15 code hash·3사례 evidence 재계산 일치. 직접 감3도/채움 경로는 이 소규모 실제 cohort에서0이며 해결 부정 판정이 아니다. K280-2 분산과 쉼표, Beethoven01-1 현재 근음 부재, K280-3 bII→i6를 원XML로 확인했다. modifier/페달·긴 연장·enharmonic·major/root/second-inversion 실제 검증은 보류. 기권 사례도 r2에서 앞뒤 문맥 보존. UI/production 미변경.

Unit30 검증: 전용30개 포함 관련562개 통과.22 case hash·16 code hash·21사례 재계산 일치. 독립 두 경로가 아닌 실제 source overlap/동시 도착 pair를 검사한다. 합집합/철자 동시음/bass/pitch-class-only를 구별하며 근음/기능/종지 미확정. Fr/Ger43은 이론·합성 테스트만, source adapter 실제 지원은 It/Ger의 기본목표만. 적용 It6/vi, 분산 detour, 성부 전이, 생략/지연 해결, V(64) modifier는 보류. 공동3개는 K280-2의 반복이라 독립3작품 검증이 아님. UI/production 미변경.

Unit25 검증: 전용23개 포함 관련424개 테스트 통과. 324 case hash·11 code hash·3사례 재계산 일치. supplied7화음 root/7음 진행, 철자상3화음+추가음 대안, 최대4화음 source root chain을 저장한다. source XML voice가 같은데 IR voice ID가 다른 실제 사례도 발견했으므로 다른 IR성부 출현을 실제 transferred resolution으로 승격하지 않는다. 지연/확장/페달/잠재성부·박절은 보류. production/UI 미변경.

Unit24 검증: 전용23개 포함 관련401개 테스트 통과. 혼용 템플릿과 내린3/6 등의 실제 진입/이탈 geometry를 분리했다. Secondary Mixture를 Secondary Dominant로 자동 치환하지 않는다. 19사례/hash·11코드hash·3사례 재계산 일치. 실제 ♭VI/단조 장I 사례 부재, cross relation/종결 Picardy/확장 조영역은 보류. JSON만 추가, production/UI 미변경.

Unit23 검증: 전용23개 포함 관련378개 테스트 통과. 감7/반감7을 철자별로 구성하고 모든 구성음의 직접 진입/이탈을 관찰한다. 장조 감7을 배제하지 않고 추가문맥 대상으로 유지한다. 모양과 기능, 성부별 진행과 공동 해결은 별개다. 내부 이동을 경계 이후 해결 후보와 구분한다. source 조성/라벨/구간에 의존하는35사례 감사이며 독립정답률이 아니다. 새 JSON만 생성, production/UI 미변경.

Unit22 검증: 전용23개 포함 관련355개 회귀 테스트 통과. `rhythmic_figuration.py`는 원IR을 바꾸지 않고 실제 경계 지속/동일음 재타격/최초 이탈을 기록한다. 구성음 목록을 따로 공급하는 조건부 단계는3·7화음 입력을 허용하지만, 실제642쌍 감사는 plain triad source adapter만 사용했다. 28개는 지연 순차 도착과 호환되는 후보이지 검증된 계류 정답 수가 아니다. 페달/간접·장식해결/실제accent는 미구현. JSON 사례만 추가, production/UI 미변경.

Unit21 검증: 전용25개 포함 총332개 회귀 테스트 통과. `compare_blocks`는 IR/두 구간만으로 exact 리듬 위치 대응을 만들고, `condition_on_triads`가 별도로 supplied 화음과 연결한다. 원음표 길이/타이를 바꾸거나 암시적 sustain/실제voice를 생성하지 않는다. 90쌍/5대응/1해결 후보는 정확도 수치가 아니다. 리듬변형/성부교환/동시음/박절/전체화성은 후속 과제. 기존 모티프나 화성 전체를 exact matching으로 바꾼 것이 아니다. JSON 사례만 추가, production/UI 미변경.

Unit20 검증: `test_six_four_context.py`24개 포함 총299개 회귀 테스트 통과. 최신 r2는59창, 역할 발생 경과13/rootless V42 대안15/분산12/정지bass 해결1,25창은 역할 없음.82개 시점쌍의 완전 표면+직접해결 지지0은 분산 성부/생략과 좁은 검사 범위의 한계다. 보조형·증III 실제 사례 공백. 초기 분산후보17은 감3화음의 협화적 안정 과잉 해석을 제한해12로 수정했고 초기 산출물은 이력으로 보존한다. 실제 XML 대조·출처 내부 표현 차이·미해결·재현 명령은 정본 기록 참조. 새 UI/production 적용 없음.

아래 경로는 이 문서 기준 상대 경로이며 프로젝트 루트는 `K:\Music Analysis`다.

| 파일 | 책임과 한계 |
|---|---|
| [chromatic_tonal_context.py](../src/musicanote_harness/chromatic_tonal_context.py), [chromatic_tonal_context_audit.py](../src/musicanote_harness/chromatic_tonal_context_audit.py) | Unit33 조건부 이명동음 모양·공통음/경계 geometry와 source key 문맥. `output/harmony-unit33-audit-2026-09-27-r1/`702기록. 자동 전조·기능 재해석 판정/정답률 검증이 아님 |
| [score_reduction.py](../src/musicanote_harness/score_reduction.py), [score_reduction_audit.py](../src/musicanote_harness/score_reduction_audit.py) | 부록 literal doubling/축약 제안 계약/표기 프로파일/시퀀스 bass taxonomy. r4의17사례 중2사례 XML–IR 불일치 격리. 자동 축약·주선율 선택이 아님 |
| [chromatic_voice_leading.py](../src/musicanote_harness/chromatic_voice_leading.py), [chromatic_voice_leading_audit.py](../src/musicanote_harness/chromatic_voice_leading_audit.py) | Unit32 주석 독립 IR 반음/균등간격/교대 run·동기화된 공동 경로. `output/harmony-unit32-audit-2026-09-27-r2/`885 geometry 기록. 화성 분석/음계 사용/경계 판정이 아님 |
| [chromatic_embellishment.py](../src/musicanote_harness/chromatic_embellishment.py), [chromatic_embellishment_audit.py](../src/musicanote_harness/chromatic_embellishment_audit.py) | Unit31 명시 가설의 혼용 모양·증5 경로·감7 공통음 경쟁. `output/harmony-unit31-audit-2026-09-27-r1/`117사례. 실제 기능/종지/경계 자동 판정 아님 |
| [applied_chords.py](../src/musicanote_harness/applied_chords.py), [applied_chords_audit.py](../src/musicanote_harness/applied_chords_audit.py) | Unit26 V/V7/vii/vii7/반감7 가설·목표/이웃 비교·실제 leading-tone/7음 경로. 최신 `output/harmony-unit26-audit-2026-09-27-r2/`204사례. 비주석 목표추론/기능/전조 확정은 아님 |
| [diatonic_modulation.py](../src/musicanote_harness/diatonic_modulation.py), [diatonic_modulation_audit.py](../src/musicanote_harness/diatonic_modulation_audit.py) | Unit27 두 조의 관계/소속·PD/D/T·source-key run·수직/분산/무음 증거. 최신 `output/harmony-unit27-audit-2026-09-27-r3/`45사례. 원조성 주석과 실제 전조/종지 정답을 구별 |
| [added_dissonance.py](../src/musicanote_harness/added_dissonance.py), [added_dissonance_audit.py](../src/musicanote_harness/added_dissonance_audit.py) | Unit28 명시 V7 기준의9/4/6음·5/3/근음 부재·전후 geometry. 최신 `output/harmony-unit28-audit-2026-09-27-r2/`202사례. 원modifier와 비교기준·실제음표를 분리하며 기능/NCT/경계 확정 안 함 |
| [neapolitan_evidence.py](../src/musicanote_harness/neapolitan_evidence.py), [neapolitan_audit.py](../src/musicanote_harness/neapolitan_audit.py) | Unit29 명시 key/전위의 bII 철자·표면/분산·같은 성부 b2 경로·인접 문맥. 최신 `output/harmony-unit29-audit-2026-09-27-r2/`4사례. 자동 기능/종지/경계 결정 안 함 |
| [augmented_sixth.py](../src/musicanote_harness/augmented_sixth.py), [augmented_sixth_audit.py](../src/musicanote_harness/augmented_sixth_audit.py) | Unit30 명시 key/family/bass의 철자·동시/분산·독립/공동 경로. `output/harmony-unit30-audit-2026-09-27-r1/`22사례. root/기능/종지/경계 미확정 |
| [seventh_context.py](../src/musicanote_harness/seventh_context.py), [seventh_context_audit.py](../src/musicanote_harness/seventh_context_audit.py) | Unit25 supplied7화음 진행·겉보기3화음 대안·직접/다른 IR성부 출현 분리. 최신 `output/harmony-unit25-audit-2026-09-27-r2/`324쌍. 성부 이동/기능/지연해결 확정 아님 |
| [mixture_evidence.py](../src/musicanote_harness/mixture_evidence.py), [mixture_audit.py](../src/musicanote_harness/mixture_audit.py) | Unit24 철자별 혼용 가설·합집합/수직 지지·실제 직접 진입/이탈 분리. 최신 `output/harmony-unit24-audit-2026-09-27-r2/`19사례. supplied key/range 조건부이며 전조/Picardy/기능 자동 판정 아님 |
| [leading_tone_seventh.py](../src/musicanote_harness/leading_tone_seventh.py), [leading_tone_seventh_audit.py](../src/musicanote_harness/leading_tone_seventh_audit.py) | Unit23 감/반감7 철자·4전위 가설, 실제 구성음 독립 경로, 표면모양. `output/harmony-unit23-audit-2026-09-27/`35사례. applied/다성분리/전이/기능 확정은 미구현 |
| [rhythmic_figuration.py](../src/musicanote_harness/rhythmic_figuration.py), [rhythmic_figuration_audit.py](../src/musicanote_harness/rhythmic_figuration_audit.py) | Unit22 실제 지속/재타격/직접 이탈 및 별도 구성음 관계. `output/harmony-unit22-expanded-audit-2026-09-27/`642쌍. 초기 고정90쌍은 `output/harmony-unit22-audit-2026-09-27/`. 일반 계류/선행/페달 분류기는 아님 |
| [melodic_figuration.py](../src/musicanote_harness/melodic_figuration.py), [melodic_figuration_audit.py](../src/musicanote_harness/melodic_figuration_audit.py) | Unit21 리듬 위치의 비인접음 대응/경과·보조 geometry와 별도 조건부3화음 연결. 최신 `output/harmony-unit21-audit-2026-09-27-r2/`90쌍. 명시voice·동일정규화리듬 범위, 실제 잠재성부/종지 미확정 |
| [six_four_context.py](../src/musicanote_harness/six_four_context.py), [six_four_audit.py](../src/musicanote_harness/six_four_audit.py) | Unit20 조건부6/4 역할과 조성/주석 라벨 없이 계산하는 직접4→3·6→5 증거. 최신 `output/harmony-unit20-audit-2026-09-27-r2/`59창. 완전수직/명시성부/정지bass 한계, 분산 성부·7화음 도착·장식된해결 보류. 자동 종지/경계 판정 없음 |
| [six_three_context.py](../src/musicanote_harness/six_three_context.py), [six_three_audit.py](../src/musicanote_harness/six_three_audit.py) | Unit19 조건부1전위 역할·6음 장식 대안, 실제 최저음/바깥 음정의 시간 가중 관찰. `output/harmony-unit19-audit-2026-09-27/`270창. 명목 bass·관측 최저음·실제 bass voice를 분리하며 자동 재라벨/병합 없음 |
| [diatonic_sequence.py](../src/musicanote_harness/diatonic_sequence.py), [diatonic_sequence_audit.py](../src/musicanote_harness/diatonic_sequence_audit.py) | Unit18 기본4모델의 조건부 후보와 explicit voice geometry 분리. `output/harmony-unit18-audit-2026-09-27/`189창. 비교 불가 사유·타이/철자·출처 보존. 자동 sequence/기능/경계 판정 아님 |
| [root_position_context.py](../src/musicanote_harness/root_position_context.py), [root_position_audit.py](../src/musicanote_harness/root_position_audit.py) | Unit17 supplied root triad 관계·역할 후보와50개 인접 소나타창. `output/harmony-unit17-audit-2026-09-27/`. 실제 bass direction/성부진행/계층/자동 병합 미판정 |
| [mediant_evidence.py](../src/musicanote_harness/mediant_evidence.py), [mediant_audit.py](../src/musicanote_harness/mediant_audit.py) | Unit16 home/mediant 철자 좌표 및 III/VII의 조건부 모양 대안. `output/harmony-unit16-audit-2026-09-27-r3/`가 최종117사례. source-conditioned, selected function/tonicization/modulation/cadence null. r1 중단·r2 독해 누락 기록은 보존 |
| [dominant_area_evidence.py](../src/musicanote_harness/dominant_area_evidence.py), [dominant_area_audit.py](../src/musicanote_harness/dominant_area_audit.py) | Unit15 원조/V조 철자 좌표 및 공통3화음 compatibility. `output/harmony-unit15-audit-2026-09-27-r2/`에 applied32/source V run12. 원주석 조영역은 추론값이 아니며 시간 간격으로 끊긴 run을 전조 경계로 쓰지 않음 |
| [tonal_role_context.py](../src/musicanote_harness/tonal_role_context.py), [tonal_role_audit.py](../src/musicanote_harness/tonal_role_audit.py) | Unit14 supplied 화성 가설의 역할 대안/종지 증거 요구. `output/harmony-unit14-audit-2026-09-27/`에 source-conditioned180사례. snapshot 관찰과 source 종지 라벨은 별도 저장, 자동 화성/종지 판정 아님 |
| [predominant_seventh.py](../src/musicanote_harness/predominant_seventh.py), [predominant_seventh_audit.py](../src/musicanote_harness/predominant_seventh_audit.py) | Unit13 조건부7음 진입/이탈, 타이 지속·화음 경계 이후 이동·성부 모호함 보존. `output/harmony-unit13-audit-2026-09-27-r2/`에27사례·원본/hash·전후 주석/IR·실행 계약. source-conditioned, not blind accuracy |
| [sixth_degree_evidence.py](../src/musicanote_harness/sixth_degree_evidence.py), [sixth_degree_audit.py](../src/musicanote_harness/sixth_degree_audit.py) | Unit12 철자·장단조/raised-sixth·수직 형태와 최저음 관계, source-conditioned train82사례. `output/harmony-unit12-audit-2026-09-27/`에 실행계약·전후 맥락·hash·관찰 보존 |
| [cadential_six_four.py](../src/musicanote_harness/cadential_six_four.py), [cadential_six_four_audit.py](../src/musicanote_harness/cadential_six_four_audit.py) | Unit 11 두 시점의 표면/단선율 진행 근거와 train 소나타 사례 보존. 상대 박절·준비·실제 종지 미판정. 전체 결과 `output/harmony-unit11-audit-2026-09-27-r2/` |
| [harmony_joint.py](../src/musicanote_harness/harmony_joint.py) | 지속음 겹침, 화음 템플릿, 조건부 NCT, 분할/전이 비용으로 구간 경로 선택. 조성·로마숫자 기능의 완전한 추론은 아님 |
| [harmony_temporal_shadow.py](../src/musicanote_harness/harmony_temporal_shadow.py) | 국소 시간 구간의 후보 지지 추가. 현재 완전구성 gate가 희박·분산 증거를 제외하는 문제가 있음 |
| [harmony_multiscale_shadow.py](../src/musicanote_harness/harmony_multiscale_shadow.py), [harmony_multiscale_review.py](../src/musicanote_harness/harmony_multiscale_review.py) | 기존 기권 셀의 고정 1/2박 분산·5음 생략 지지 보완 / 고정 cohort와 이전 결과 hash 기반 비교. 별도 offline 실험 |
| [harmony_ablation_review.py](../src/musicanote_harness/harmony_ablation_review.py), [harmony_ablation_diagnostics.py](../src/musicanote_harness/harmony_ablation_diagnostics.py) | 4조건 × 30사례 × 2문맥, 재현 검사, 동일 경로/점수 기준 재채점, 큰 문맥 경로를 작은 문맥에 옮긴 비용·후보 순위 진단. 원음표/타이 절단 없음 |
| [harmony_visual_review.py](../src/musicanote_harness/harmony_visual_review.py), `visual_review_assets/` | 원XML 악보 위 주석·버전별 계산 비교, 원본/hash/이전 baseline 동일성 검증. 원자료 조성에 의존한 RN 표시는 추론과 분리 |
| [harmony_cost_diagnostic.py](../src/musicanote_harness/harmony_cost_diagnostic.py) | 주어진 경계의 후보/경로 비용 분해. 경계 자동 발견과 구별 |
| [harmony_boundary_gate.py](../src/musicanote_harness/harmony_boundary_gate.py) | 짧은 변화 분할비용 할인 실험. 회귀 문제로 기본 활성화 보류 |
| [counterpoint_evidence.py](../src/musicanote_harness/counterpoint_evidence.py) | 철자·성부진행 증거. 자동 계산된 음형을 검증된 비화성음 정답으로 취급하지 않음 |
| [harmony_review_cohort.py](../src/musicanote_harness/harmony_review_cohort.py), [harmony_review_supplement.py](../src/musicanote_harness/harmony_review_supplement.py) | 출처 주석·정렬·작품군 split을 검사하고 사례/context 구성 |
| [harmony_review_comparison.py](../src/musicanote_harness/harmony_review_comparison.py) | 사례 중복 병합, 원래 절대 시간과 지속음을 보존한 양 엔진 비교 |
| [harmony_context_sensitivity.py](../src/musicanote_harness/harmony_context_sensitivity.py) | 문맥 길이에 따른 라벨/경계 안정성 진단 |
| [harmony_candidate_explanation.py](../src/musicanote_harness/harmony_candidate_explanation.py) | 음표별 비용, 동일 경로 재채점, 근음 철자 근거 |
| [harmony_medium_review.py](../src/musicanote_harness/harmony_medium_review.py) | 고정 30사례 계획, 120회 비교, 검토 대기열 |
| [harmony_failure_context_audit.py](../src/musicanote_harness/harmony_failure_context_audit.py) | 5사례 원음표/주석/지지 gate 대조. 주석 분류는 추론 후 진단에만 사용 |

원주석은 사례 선정·사후 평가에는 사용할 수 있지만 blind 후보 계산에 정답으로 주입하지 않는다. 특정 제목, workId, 마디 번호를 분석 예외 규칙으로 사용하지 않는다. 진단용 사례 선택 ID와 production 판정 조건을 구별한다.

## 4. 사례와 실험 산출물 위치

현재 실험 입력 manifest: [harmony-dataset-manifest-2026-09-25.json](../output/harmony-dataset-manifest-2026-09-25.json).

| 산출물 폴더 (`output/` 아래) | 내용 |
|---|---|
| `harmony-review-comparison-2026-09-27/` | 병합 사례 395개, 최초 5개 smoke 비교 |
| `harmony-context-sensitivity-2026-09-27/` | 최초 5개 × 3문맥 × 2엔진 비교 |
| `harmony-candidate-explanation-2026-09-27/` | 후보가 바뀐 3사례의 비용 설명 |
| `harmony-medium-review-2026-09-27/` | `plan/cases.jsonl`, `plan/report.json`, `results/`, 종합 `report.json` 및 검토 대기열 |
| `harmony-failure-context-audit-2026-09-27/` | `report.json`과 5개 사례 JSON: 앞뒤 악보, 지속음, 주석, 비용, 원본 hash |
| `harmony-multiscale-review-2026-09-27/` | 실행 전 `run-contract.json`, 30사례 60회 새 결과 및 직전 temporal 결과, `report.json` |
| `harmony-multiscale-context-audit-2026-09-27/`, `harmony-multiscale-visual-review-2026-09-27/` | 기존 5사례+이번 안정성 저하 2사례, 원XML 악보와 이전/이번 계산 비교 |
| `harmony-ablation-review-2026-09-27/` | 실행 전 계약, 240회 계산, 문맥별 4×4 고정 경로 비용행렬, 집계 |
| `harmony-ablation-diagnostics-2026-09-27-r2/` | 7사례 문맥 절단 경로 재채점·후보 소실·음표별 설명. r1은 중단 기록으로 보존 |
| `harmony-ablation-visual-review-2026-09-27-r2/` | 7사례 원악보에서 네 보완 조건과 두 문맥 길이를 직접 비교. 서버 8769 |

진단 사례의 `context_excerpt`는 원 global 시간의 음표·쉼표·마디·지속음을 담지만 **정식 전체 Canonical IR이나 온전한 MusicXML 대체품은 아니다**. 완전한 악보 렌더링에는 기록된 원본 XML을 사용한다. 모든 사례마다 전체 XML을 중복 복사한 상태는 아니다.

최근 5사례에는 원XML 경로/hash, IR·정규화 주석·alignment hash, 비교 결과 hash, target/context, source event 연결을 저장했다. 원 TSV의 현재 파일 hash를 다시 계산한 것은 아니며 수입 단계의 source identity에 의존한다. 이 차이도 인수인계 시 유지한다.

## 5. 재현 방법

2026-09-27 로컬 확인: Python 3.12.14, music21 10.5.0, jsonschema 4.26.0, verovio 6.3.0. 프로젝트 의존성 범위는 [pyproject.toml](../pyproject.toml)에 있다. 범위 지정은 고정 환경 잠금과 다르다. 새 컴퓨터의 완전 재현은 아직 검증하지 않았다.

PowerShell에서 프로젝트 루트를 기준으로 실행한다.

```powershell
Set-Location -LiteralPath 'K:\Music Analysis'
$env:PYTHONPATH = 'src'
& .venv/Scripts/python.exe -m unittest discover -s tests -p 'test_harmony*.py'
```

30사례 재계산 예시(긴 실행): 아래 출력 폴더가 아직 없는지 확인하고, 실행마다 새로운 이름을 사용한다. 기존 기준 결과를 덮어쓰지 않는다.

```powershell
& .venv/Scripts/python.exe -m musicanote_harness.harmony_medium_review --manifest output/harmony-dataset-manifest-2026-09-25.json --comparison-dir output/harmony-review-comparison-2026-09-27 --output output/harmony-medium-review-handoff-rerun-01
```

저장된 30사례 결과를 바탕으로 5사례 진단만 재현:

```powershell
& .venv/Scripts/python.exe -m musicanote_harness.harmony_failure_context_audit --manifest output/harmony-dataset-manifest-2026-09-25.json --review-dir output/harmony-medium-review-2026-09-27 --output output/harmony-failure-context-audit-handoff-rerun-01
```

이 명령은 원데이터·수입 패키지·기존 비교 산출물이 존재해야 한다. 파일 부재나 hash 불일치는 먼저 복원/경로 매핑으로 해결하며 검증을 끄지 않는다. `--summarize`는 추론을 다시 하지 않지만 집계 보고서를 다시 쓰므로 읽기 전용 명령이 아니다.

## 6. 개발할 때 반드시 남길 기록

중요한 화성 판정/경계 변경에는 원본 악보의 전후 문맥과 이전/실험 결과를 함께 볼 수 있는 사례 페이지도 연결한다. 생성 완료, 브라우저 표시 확인, 음악적 검수 승인은 구분한다. 불완전한 음표 매핑을 조용히 승인하지 않는다.

각 변경은 아래 항목을 개발 기록에 작성해야 완료로 본다. 같은 사례를 재해석하면 기존 설명을 삭제하지 말고 정정 이유와 새 버전을 연결한다.

```text
기록 ID / 날짜 / 담당자:
문제와 기대: 사용자 원문(있으면 그대로), 개발자 요약은 별도
대상: case ID, score/IR ID, 원본 경로·hash, parser/engine 버전
구간: rational [start,end), 앞뒤 context, 음표·타이·성부 refs
관측: 실제 pitch spelling, 음가, onset/release, 박자, 베이스/성부
출처: 교재 판/장/절/직접 확인한 페이지, 주석 ID·방언·정렬 상태
가설: 가능한 설명들, 반대 증거, 아직 모르는 것
일반 규칙: 조건/적용 양식/예외/보류 기준, 작품별 override 없음
구현: 파일·함수, 버전/commit 또는 미커밋 표시와 재현 가능한 코드 snapshot/hash
실험: 입력 manifest/hash, split, 선택 정책, 파라미터, 실행 명령·환경
결과: 변경 전후, 실패·반례·회귀, 분모/누락 수, 산출물 링크
결정: 채택 / 실험 유지 / 보류 / 기각 및 이유
적용 상태: 코드 작성 / 테스트 / offline / viewer / 구조분석 반영을 각각 명시
다음: 남은 문제, 통과해야 할 관문, 필요한 사람 판단
```

### 사례 보존의 최소 기준

- 재현 가능한 악보 자산과 앞뒤 문맥, 사용자 설명, 당시 분석 후보·선택·근거를 함께 연결한다. 원본의 배포 권한이 없으면 경로/hash·취득 방법을 보관하고 별도 승인된 자산 보관소를 쓴다.
- AI 가설, 수입 주석, 사용자 교정, 검수 승인, 학습 자격을 분리한다. 미확인 항목은 null/unknown/미검토로 둔다. 사람이 하지 않은 검수를 만들어 넣지 않는다.
- 사용자 설명 원문이 복구되지 않는 과거 사례는 원문 부재로 표시한다. 전체 대화의 모든 사례가 저장되었다고 일괄 선언하지 않는다.
- 조건부 NCT 후보와 확정 NCT, 관측 최저음과 구조적 베이스, 표면 화음과 기능을 구별한다.
- 원주석의 모든 변화가 근음/품질 변화는 아니다. 전위·장식·조 문맥 변화와 음악적 경계를 별도로 기록한다.
- 이 절은 기록 운영 규칙이다. 모든 필드를 자동 강제하는 통합 DB/API나 과거 기록 전체의 누락 검사가 완료됐다는 뜻은 아니다.

## 7. 채택·보류와 다음 단계

채택한 것은 현재 **진단 기반**이다: 절대 시간/타이 지속 보존, 비용 분해, 음표 근거, 문맥 민감도 요소 분리, 주석 경계 유형 분리, 고정 사례 계획과 hash 기록.

보류한 것은 짧은 변화의 분할비용을 일괄 낮추는 적용, temporal 실험의 Viewer 승격, 특정 곡의 라벨/경계를 강제하는 수정이다. 이유는 실제 반례·문맥 민감성과 검증 부족이다. 과거 기각 실험도 삭제하지 않는다.

다음 알고리즘 과제:

아래 1·2는 multiscale v0.1에서 제한적으로 구현해 30사례를 재비교했다. v0.2에서 4조건 분리 시험을 완료했지만 단독 기능 승격의 근거는 없다. **계산 진단 재개 시** 제안 경계에 의존하는 증거 창과 top-5 후보 제외·분할비용의 상호작용을 독립 진단한다. 현재는 교재 우선 순서다. Corelli에서 앞 화음 후보가 짧은 문맥에서 12위로 탈락하고, 병합이 분할비용을 절약하는 현상을 확인했다. 이 관찰을 바로 일반 해결책이나 음악적 정답으로 간주하지 않는다.

1. 서로 다른 시간에 나온 구성음을 누적해 분산화음의 지지를 평가한다.
2. 7화음의 5음 생략과 품질 결정음인 3음 부재를 구별한다. 단순히 필요한 pitch class 수를 2개로 낮추지 않는다.
3. 장식된 도착/지속음과 새 화음의 대안을 비교하고, root/quality와 inversion/ornament 평가를 분리한다.
4. 고정한 30사례 및 반례에서 재비교한다. 개발 표본으로 조정 후 독립 평가와 화면 shadow 검토를 거쳐야 적용한다.

사용자 승인으로 교재 우선 순서를 재개하여 Unit33까지 본문/대표 악보와 부분 구현을 기록했다. 다음은 단원별 증거 계약·의존성·중복 가산 위험 정리, 필요한 부록II Score Reduction 보충, 고정 사례의 source-blind 경로/악보 비교다. Unit33의 기능적 이명동음 실제 양성·장기 key-area/공통음 prominence/피벗/모티프 확대, Unit32의 주석 독립 geometry와 화성 가설의 결합·잠재성부/사행/변형/omnibus·grace 구조 역할·옥타브분할 실제 검증, Unit31의 Double/altered V7 실제 검증·분산/잠재 성부·공통음 증6/겉보기V7·단조/7화음 혼용·비주석 추론, Unit30의 분산 성부/베이스 우회·생략 해결·Fr/Ger43 source·비기본목표·비주석 추론·V(64) modifier, Unit29의 비주석 bII 후보·현재 근음 부재/긴 연장·modifier/페달·재철자/선적/pivot 해석, Unit28의 비주석 기준/원modifier 의미·페달/암시해결·현대 양식, Unit27의 비주석 key-area/피벗/종지/형식계층, Unit26의 비주석 목표/조성/구간 추론·중첩적용·장식도착·긴 연쇄, Unit25의 실제 성부 이동·지연/확장·페달·겉보기 기능 검증, Unit24의 cross relation/종결 Picardy/확장 혼용, Unit23의 공동 음정 해결·전이·V7 장식·페달/elision은 미해결이다. Unit22의 간접·장식/생략 해결·상대 박절, Unit21의 유연한 리듬 정렬 등도 정본 기록에 보존한다. 교재 진도와 엔진 완료 상태는 따로 갱신한다. 분석 결과를 바로 Phrase 경계 정답으로 되먹임하지 않는다.

## 8. 다른 개발자에게 넘기기 전 체크리스트

**최신 순서 보정:** 위 Unit33 직후 계획에 적힌 부록II 보충은 이번 부록 I–III 단계에서 완료했다(원본708쪽 미확인). 단원 통합보다 먼저 OQ-029의 동일음 source 연결 문제를 재현/검증한다. 현재2사례는 격리만 했으며 기존 패키지나 parser를 교정한 상태가 아니다.

- [ ] 전달할 코드·문서의 commit/tag와 dirty/untracked 상태를 확정하고 테스트 결과를 연결한다. **현재 화성 파일 다수가 미커밋 상태다.**
- [ ] 필요한 실험 산출물과 manifest를 별도 보관한다. **`output/`은 `.gitignore`로 제외되어 Git push만으로 전달되지 않는다.**
- [ ] manifest가 가리키는 원XML, IR, imported annotations, alignment 패키지의 존재·hash와 경로 매핑을 확인한다. `.venv`는 복사에 의존하지 않고 환경을 재구성한다.
- [ ] 외부 `K:\MusicSearch\data\classical-corpora` 및 `K:\MUSICANOTE\musicanote-ai-local\books` 접근을 준비한다. 디렉터리 이동 후에도 자산 identity는 hash로 검증한다.
- [ ] 자료별 licence/rights를 확인한다. 현재 연구용 내부 이용과 재배포·훈련·외부 API 전송 허가는 다르다. 책/코퍼스를 무조건 GitHub나 인수인계 묶음에 넣지 않는다.
- [ ] train/dev/holdout 및 동일 작품군 분리를 유지한다. 현재 진단은 train 개발 표본이고 `blind_evaluation=false`이며, 학습 허가를 자동 승격하지 않는다.
- [ ] 새 환경에서 작은 재현과 테스트를 실행한다. 누락 자산·의존성·경로 문제를 인수인계 제한으로 기록한다.
- [ ] 화면에 적용된 버전과 offline 실험 버전을 별도로 인계한다. UI 표시가 있다는 이유로 최신 실험이 적용됐다고 판단하지 않는다.

로컬에 기록이 존재하는 것, Git에 커밋된 것, 원격에 올라간 것, 다른 컴퓨터에서 재현되는 것은 서로 다른 완료 조건이다.
