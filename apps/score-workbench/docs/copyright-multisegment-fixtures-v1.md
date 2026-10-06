# 다구간 변형 MusicXML 파일럿 v1 — 제작 완료

## 완료 범위

- 새로 작성한 합성 원곡 4개, 각 3개의 8음 프레이즈. 제3자 악보를 복제하지 않았다.
- 원곡별 6유형, 입력 MusicXML 24개. 기준 파일은 12마디, 나머지는 새 문맥 안에 배치한 14마디.
- 4/4, 3/4, 6/8, 5/4. 각 파일 2개 파트이며 일부 세 구절 차용 사례는 마지막 구절을 P2로 이동한다.
- 전조, 국소 반음 변경, 전체 옥타브, 국소 리듬 재분배, 장식음 추가, 동일 구절 반복, 비차용 대조군.
- 마디를 넘는 타이와 쉼표가 실제로 포함된다. 이번에는 tuplet·못갖춘마디·음 삭제 유형까지 포함했다고 주장하지 않는다.

최종 자산: evaluation/fixtures/multisegment-v1-final/.
앞선 multisegment-v1/은 초기 산출물을 보존한 것이며 평가 세트에 합산하지 않는다.
최종 24개가 새 테스트 입력이고 **실제 검색 실행 24건이 아니다**. 누적 검색 테스트 수에 더하지 않는다.

## 구별해야 할 한계

합성 원곡이므로 기존 운영 DB에는 없다. 본 묶음은 정답이 확실한 파싱/구간 집계 기능 검증의 출발점이다.
실제 유명곡·현재 corpus의 recall, 음악적 자연스러움, 전문적인 phrase 판정, 법적 침해 탐지를 입증하지 않는다.
권리 상태를 법적으로 보증하지 않으며 synthetic-source-provenance를 침해 정답으로 사용하지 않는다.
배경 음계 문맥은 원본에도 쓰이므로 hard-negative에서 배경의 exact 일치가 나올 수 있다.
이는 특징적 phrase 차용과 일반 관용구를 구별하는 대조군이며, 결과가 0개여야 한다는 정답이 아니다.
현재 각 원곡 3개 프레이즈는 같은 리듬 뼈대를 공유한다. 향후 리듬/조성/형식 다양성과 실제 권한 확인 작품을 추가한다.

## 저장 구조와 누출 방지

- sources/: 원곡 XML과 이벤트. 추후 격리 DB에만 넣을 참조 후보.
- uploads/: 블라인드 파일명/제목 XML과 이벤트. 검출기에는 MusicXML만 전달.
- evaluator/cases.json: 기존 musicanote-evaluation-case/v1 24개. source hash, 유형, 변형 recipe, 고유 family/발생 정답, source↔input event/part/onset/pitch/duration 및 input XML note IDs.
- evaluator/index.json: 사람이 읽을 요약 색인.
- manifest.json: 생성 코드 hash, 파일 hash, 렌더 결과. 변형은 무작위가 아닌 고정 recipe로 재현한다.
- roundtrip-audit.json: 독립 XML 검사 및 실제 운영 파서의 round-trip 결과.
- previews/: 28개 SVG(원곡 4 + 입력 24).
- review.html: 입력 악보와 정답 구간 수, 원본 XML 링크. **실제 검색 결과/저작권 리포트가 아니다.**

같은 구절을 세 번 사용한 입력의 정답은 family=1, occurrence=3이다.
원본 기준은 동일 XML bytes/hash를 의도적으로 유지하고, 나머지 입력의 파일명/제목에는 원곡명 힌트를 넣지 않는다.
검색 엔진은 evaluator/를 읽으면 안 된다. 입력을 DB에 넣거나 파생 파일을 원곡 canonical identity로 묶어 제외하지 않는다.

## 검증 결과

28개 XML 모두 Verovio 렌더 성공(각 1page).
실제 build-musicxml-search-index.py의 parse_musicxml로 재파싱해 모든 pitched logical event의 pitch/onset/duration이 snapshot과 같음을 확인했다.
독립 ElementTree 검사로 모든 마디의 박자 합, tie/tied 일관성, 분할 tie의 합산 음가, 쉼표 시간, 고유 XML ID를 검사했다.
388개 대응 이벤트의 입력 XML/SVG ID 및 원본 위치·음높이·음가 mapping을 검증했다.
baseline hash 동일성과 실제 타이 포함도 확인했다.
표준 사례 스키마 검증 통과. 청취·브라우저 육안 판면 검토 및 실제 검색은 아직 하지 않았다.

## 재현

node scripts/generate-multisegment-fixtures.mjs NEW-directory
python scripts/verify-multisegment-fixtures.py NEW-directory

기존 폴더/검증 파일은 덮어쓰지 않는다. Python은 표준 라이브러리만 사용한다.
이 환경의 python 명령은 Windows 실행 별칭이어서 실행되지 않았으며, Codex 번들 Python으로 검증했다.
Verovio는 저장소 설치 의존성을 사용한다. 코드 hash와 환경/의존성이 달라지면 별도 새 버전으로 생성한다.

## 다음 단계

1. 원곡 4개만 넣은 격리 fixture DB 생성. 운영 DB는 유지한다.
2. 업로드 전곡 분석 → 실제 검색 → 대응 구간 회수, 고유 구절/반복 발생 집계.
3. provenance 정답과 실제 탐지를 비교하되 정답을 검출기에 주입하지 않는다.
4. 검사 범위/누락/오탐과 권리 미확인을 드러내는 리포트 시안.
5. 그 다음 허락 또는 권리 상태가 확인된 실제 작품을 별도의 holdout 세트로 추가한다.

