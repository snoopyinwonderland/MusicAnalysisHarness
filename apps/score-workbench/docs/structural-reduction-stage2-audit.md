# 구조 변형 검색 2단계: XML 연결 및 자료 감사

2026-09-15. 상태: 원본 연결 완료, 변형 100개/검색 baseline/임시 악보 페이지 미완료.

## 이번 사용자 요구

변형 100개를 만들면 임시 페이지에서 악보로 보여 준다. 원본과 변형을 나란히 배치하고 생성기에서 보존한 음, 실제 변경한 음, 분석기 추정 기둥을 구별한다. 원본/변형 재생과 Query JSON 접근을 제공할 예정이다. 분석기 판단을 테스트 정답으로 복사하지 않는다.

## 구현 및 재현

- `scripts/structural-xml-source.py`: score-partwise 원 XML → 유리수 시간, 원 마디 번호, part/staff/voice, spelling 구성요소, diatonicPitch, tie 연결, 음표 locator, 쉼표를 보존한 JSON. 원 XML 수정 없음.
- `scripts/audit-structural-sources.mjs`: 기존 harder-100의 20개 실제 원본을 선택하고 해당 구간 앞뒤 2마디의 문맥으로 독립 분석. 표본은 기존 편의 표본이며 최종 구조 변형 suite 선별을 완료한 것이 아니다.
- `scripts/structural-xml-source.test.py`: 못갖춘마디/유리수 타이/다성부/화음/쉼표/고립 tie/필수 시간 단위 오류 검사, 4개 통과.

명령:

```powershell
& 'K:/Music Analysis/.venv/Scripts/python.exe' scripts/structural-xml-source.test.py
node scripts/audit-structural-sources.mjs evaluation/runs/structural-source-audit-v2
```

출력 폴더는 신규 폴더를 사용해야 한다. 원본 v1 실패 기록을 보존하며 재실행한 v2에는 연결 근거를 추가했다.

## 확인된 결과

20/20 XML 추출 성공. 기존 focus 총 200개 음표가 part/staff/voice + measureOrdinal + beat + pitch로 각각 원본 음표 하나에 연결됐다. raw onset만 사용하면 B08 Top Gun Anthem 및 B11 Caro Mio Ben에서 기존 색인 시간과 차이가 발생한다. 기존 색인의 마디 길이/pickup 처리와 새 어댑터의 실제 짧은 마디 시간 처리가 다를 수 있으므로 양쪽 시간은 보존하고 좌표 연결로 해결한다. 이것을 전체 production 파서 오류가 확정됐다고 해석하지 않는다.

`indexLinks`에 기존 indexNote, xmlEventIds, unique/ambiguous/missing 상태를 저장한다. 원본 이벤트 시간에 색인 offset을 덮어씌우지 않는다.

20개 모두 확정 화성 정보는 어댑터가 제공하지 않으며, 현행 실험 모듈은 전부 L0를 유지했다. provisional 관계와 휴리스틱 기둥 후보는 있어도 Schenker 분석의 확정 정답이 아니다. 이 보류율을 숨기고 성공한 사례만 고르지 않는다.

## 한계 및 다음 작업

- 이조 악기의 written pitch는 보존하지만 sounding pitch 변환은 미구현. 현재 200개 좌표 검증이 전체 DB 이조 악기 지원을 뜻하지 않는다.
- 생략 voice/staff는 MusicXML 기본값 1로 기록하고 identityDefaults를 남긴다. 이것은 독립 성부 추론이 아니다.
- cross-staff tie, score-timewise, MXL 직접 입력, 악보 전체 화성 추정은 미구현.
- 다음 suite는 생성기가 보존하는 scaffold를 분석기 확정 기둥과 분리하고, 실제 문맥에서 장식으로 해석 가능한지 악보/청취 검토할 수 있도록 만든다.
- 단순히 100개 숫자를 채우려고 임의 기둥을 선택하거나 화성 정보를 만들어 넣지 않는다. 자동 변형의 적합성/보류 사유를 먼저 기록한다.
- 임시 페이지는 100개 생성 완료 후 제공한다. 현재 페이지가 생성됐거나 검색 테스트가 실행된 상태는 아니다.
