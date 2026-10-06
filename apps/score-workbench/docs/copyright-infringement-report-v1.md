# Copyright Infringement Report v1 — 오프라인 검토 초안

2026-09-15. 업로드 운영 서비스가 아니라, 기존 사전검토 파이프라인의 보존된 검색·구조 근거를 사람이 비교할 수 있는 HTML/JSON 산출물로 만드는 단계다.

## 확인할 결과

- 최종 HTML: `evaluation/reports/copyright-infringement-report-2026-09-15-final/index.html`
- 전체 구조화 근거: 같은 폴더의 `report.json`
- 입력·코드 지문/렌더링 기록: `manifest.json`
- 자동 검증: `verification.json`
- 화면 확인: `qa-desktop.png` (1440px), `qa-mobile.png` (500px)

샘플은 기존 S-STRUCT-003의 **Endless Love.xml 성부 P1:1:1**이며 새 사용자 업로드가 아니다. 선택 Query 7개, 작품 그룹 26개, 보존 일치 56개, 대표 A/B 악보 52개다. 검증된 판본 연결만 병합하며 제목이 같다는 이유만으로 묶지 않는다.

작품별 유사도, 입력 선택 음표 coverage, 실험용 검토 우선순위, 코퍼스 빈도 반영 점수, 판본·일치 목록, 원본 마디·성부, 반복/음가 비중과 구조 근거를 표시한다. 최고 유사도와 대표 비교 구간의 유사도는 다를 수 있어 따로 표시한다. 성부 안 비중을 작품 전체 중요도라고 표시하지 않는다.

## 악보와 재생 계약

논리 이벤트 스냅샷을 Verovio로 재기보한다. 쉼표, 음가, 점음표, 마디 경계 분할 타이를 보존하며 alignment 음표를 붉게 표시한다. **재기보 마디 번호는 원본 마디 번호가 아니며 원래 판면·조표·음자리표의 완전 복제도 아니다.** 원본 좌표를 옆에 적고 로컬 원본 악보 링크를 제공한다.

A/B 재생은 같은 템포의 Web Audio 합성음이다. 논리적으로 합쳐진 tie는 한 번 발음한다. 오디오 파일/YouTube를 다운로드하거나 외부 CDN에 의존하지 않는다. 악보/재생은 HTML 단독으로 동작하고 JSON 링크에는 인접 report.json, 원본 링크에는 로컬 서버가 필요하다. 재생 커서는 아직 없다. 인쇄 버튼으로 브라우저 PDF 저장이 가능하나 자동 생성된 PDF 파일은 아니다.

## 재현

Node 24 계열과 설치된 lockfile 의존성을 사용한다. output은 존재하지 않는 새 경로여야 한다. 원본 evidence가 참조하는 `.assets` 스냅샷도 함께 필요하다.

```powershell
node scripts/export-preclearance-report.mjs evaluation/runs/preclearance-frequency-2026-09-15.json evaluation/reports/handoff-report
node scripts/verify-preclearance-report.mjs evaluation/reports/handoff-report
```

상위 생성 순서는 [재현 문서](REPRODUCIBILITY.md)를 따른다. 최종 샘플은 구조 분석 **v1.9 근거를 그대로 보존**한다. 현재 v1.10으로 자동 재분석한 것으로 취급하지 않는다. 새 분석을 반영하려면 구조 준비→검색→보강부터 새 실행을 만들어야 한다.

## 검증과 남은 범위

52개 악보의 음표 및 강조 대상 존재, 인라인 JavaScript 파싱, 테스트 AudioContext의 음높이·쉼 간격·중복 클릭 취소를 확인했다. 이는 실제 청취나 원본 판면과의 동등성 검증이 아니다. 데스크톱/좁은 화면 첫 카드 배치도 확인했다. 관련 회귀 127개와 TypeScript/build 통과. 기존 Verovio 대형 chunk 경고는 남아 있다.

권리는 원작/편곡/판본/녹음을 구분하되 미확인은 미확인으로 남긴다. 75년 경과만으로 clearance를 부여하지 않는다. 이 초안은 침해 확률, 법률적 판정, 이용 허락을 제공하지 않는다. 관할권·창작 경위·접근 가능성과 전문가 검토가 추가로 필요하다.

아직 남은 제품 단계: 비공개 업로드·보관/삭제·인증·운영 job/UI, 외부 구조 분석기 업데이트 연계, 권리 증거 입력/검토, 전문가 라벨로 점수 보정. HTML/JSON에 음악 이벤트가 포함되므로 재배포 권한 확인 없이 공개 배포하지 않는다. 관련 데이터와 DB는 별도 인계 대상이며 Git에 모두 포함됐다고 가정하지 않는다.
