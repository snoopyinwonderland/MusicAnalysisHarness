# 시간순 장식 후보와 보류·미설명 구간

HARM-DEV-20260930-06 · 2026-09-30

## 목적과 일반 계약

직전 시간순 근거에 기존 조건부 NCT 설명을 연결했다. 특정 작품 예외, 주석 정답 역주입, 원음표 삭제, 새 교재 독해·학습·운영5173 적용은 없다.

- 유지/분할은 동일 전 성부 음표, 유리수 `[start,end)` 셀, 동일 assignment를 사용한다.
- 구성음/조건부 비구성음/보류 비구성음/미설명 비구성음/철자 미정을 따로 누적한다. 모든 기존 음가 합을 보존한다.
- 경계 음형은 양쪽 후보 index, assignment, nonmember span이 일치해야 해당 음표·셀에 적용된다. 후보 자체가 보류면 캐시된 경계 패턴을 재사용하지 않는다.
- 계류음 assessment가 abstain이면 그 사유와 함께 별도 보류로 저장한다. assessment가 없어도 계류 형태를 검증된 것으로 보지 않는다.
- 독립적인 local 조건부 설명과 다른 보류 패턴이 공존하면 양쪽 근거를 보존한다. local 설명을 지우거나 확정 NCT로 승격하지 않는다.
- 셀에는 모든 event bucket을 남긴다. 화면 요약은 미정→미설명→보류→조건부→구성음 순서이며 빈 셀은 쉼이다. 다른 성부에 미설명 음이 남으면 전체 셀은 설명 완료로 보이지 않는다. 이 우선순위는 표시 정책이지 후보 순위가 아니다.
- wall-time(실제 경과 시간)과 note-time(각 성부 음가 합)을 구별한다.
- 유지에는 기존 local 문맥, 분할에는 추가 경계 문맥이 적용되어 완전히 대칭인 평가기는 아니다. 설명량을 정확도·확률·자동 분할 점수로 쓰지 않는다.

## 구현·범위

`harmony_ornament_timeline.py` (`ornament-timeline-0.1.0`)와 replay 실행기를 추가했다. 각 boundary에는 정책만 저장하고 기존 preview 선택에는 새 상세 비교를 저장한다. 모든 조합을 전개한 것은 아니며 UI는 dropdown 선택에 따라 계산한다. 기존 stage 실행기의 페이지 제목 교체 범위를 확장했다.

`visual_review_assets/segment_contrast.js`에 새 음가 합·셀별 상태를 표시한다. 기존 비교 표는 그대로 보존한다. 원 Core/주석/후보/구조 분석/운영5173은 변경하지 않았다.

입력: `output/harmony-temporal-coherence-2026-09-30-r2/`.
출력: `output/harmony-ornament-timeline-2026-09-30-r1/`.

184표본(베토벤02-3:43, K281-3:67, K280-1:74),117경계(0/65/52), 명시적 보류 패턴21개(0/11/10) 유지. 이는 계류 오답 수나 독립 화음 수가 아니다. 기존135음형/이전 설명량 필드는 불변이다.

train/internal research 권한, source/원계획/추가계획 hash, 기존184표본의 실행 전후 hash를 검사했다. 새 필드를 제거하면 이전 JSON과 동일함을 확인했다. run-contract에 코드/UI/source report hash를 기록한다. 복사된 이전 counterfactual-checks는 과거 기록이며 이번 재실행 결과로 주장하지 않는다.

## 실제 사례·화면

K281-3 `reviewm_555ff701230fc0b8ee66`, sample16, global `[9,13)`, boundary `21/2`. 기본 Cmajor 유지 대 E♭major→Dmajor 분할은 검토용이지 추천 정답이 아니다.

B♭4 `sound_0b9d0a329fff` → A4 `sound_82e6cfa6216c`, pattern `boundary_nct_228db2cec7c3aca22fe6`. 악보/IR/source refs는 source-snapshot 및 이전 사례 기록을 보존한다.

- 이전 분할+문맥: 구성음5 / 조건부1½ / 미설명5½ quarter.
- 새 대조: 구성음5 / 조건부0 / **보류1½** / 미설명5½ quarter. 총음가12 quarter 불변.
- 무연결 선택: 구성음5 / 조건부0 / 보류0 / 미설명7. 성부 연결 근거가 없으면 계류 형태도 적용하지 않는다.
- 여기의1½는 **4분음표 기준 음가**다. 2/2 지휘박1½를 뜻하지 않는다. 작업 중 '박 분량'이라는 표현은 이 정의로 정정한다.
- 다른 성부의 미설명 음이 남아 셀 요약에는 '미설명 비구성음 포함'이 표시될 수 있다. 보류 음표는 event bucket에 별도 보존된다.

[전체 악보 검토](http://127.0.0.1:8823/real-cases/reviewm_555ff701230fc0b8ee66/whole-score.html?sample=16). 로컬 서버 실행 필요.

## 검증과 재현

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m unittest discover -s tests -p test_harmony_ornament_timeline.py
.venv/Scripts/python.exe -m musicanote_harness.harmony_ornament_timeline_trial --source output/harmony-temporal-coherence-2026-09-30-r2 --output output/harmony-ornament-timeline-2026-09-30-r1
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -m http.server 8823 --bind 127.0.0.1 --directory output/harmony-ornament-timeline-2026-09-30-r1
```

재실행은 새 출력 디렉터리에 한다. 신규8/전체1,593테스트 통과(24.053초), 기존 Verovio 경고1건/실패0. 경과 형태, 계류 보류, 무연결, 원데이터 보존, 경계 이후 음가만 적용, stale 패턴 차단, 독립 local 설명, 다성부 wall-time을 검사했다. 브라우저에서 Python 음가 일치·무연결 전환·기본 복원·전체 악보와 패널 배치를 확인했다. `git diff --check` 통과(기존 CRLF 안내). GitHub push는 하지 않았다.

## 다음 단계

유지/분할 양쪽에 동일 문맥 범위를 적용하는 비교 계약 및 실제 양성·유사 반례 평가가 필요하다. 분할로 문맥이 잘려 생기는 불이익과 긴 구간 병합으로 설명량이 커지는 이익을 통제한 뒤 후보 선택을 검토한다. 이번은 설명 가능성 분리이며 화성 정답 판정 완성이 아니다. 사용자 검수를 지금 반드시 요구하지는 않는다.
