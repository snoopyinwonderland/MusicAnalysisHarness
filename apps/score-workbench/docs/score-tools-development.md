# Score Tools 개발 기록

## 목표

원본 MusicXML과 기존 분석 데이터를 수정하지 않고, 동일한 원본 버전에서 파생 악보와 연구용 발췌를 재현 가능하게 만든다. 기준 명세는 `MUSICANOTE_Score_Viewer_Features_Development_Spec_v1_1.md`다.

## 2026-09-27 — 기반 계층과 첫 수직 기능

### 구현

- SHA-256 원본 hash를 포함하는 `ScoreSnapshot`을 추가했다.
- Part, 표시 마디 번호와 분리된 measure ordinal, Part/Measure/Event 안정 참조를 만든다.
- onset과 duration은 부동소수점 대신 기약분수로 snapshot에 기록한다.
- `ViewRecipe 1.0.0`, `ExcerptRecipe 1.3.0`, source map sidecar 계약을 추가했다.
- 테스트 기간에는 모든 자료를 허용하는 `ScoreExportPolicy` 어댑터를 사용한다. 변환 코드와 UI는 정책 객체만 호출하므로 상용화 단계에서 서버 권한 판정으로 교체할 수 있다.
- 복수 whole Part와 연속 마디 범위를 원본에서 다시 추출한다.
- 첫 발췌 마디에 유효한 divisions, key, time, staves, clef, transpose를 복원한다.
- 선택하지 않은 Part와 part-list 항목을 제거하고 원본은 변경하지 않는다.
- 동일 파생 XML에서 SVG를 재조판한다. 화면 캡처는 사용하지 않는다.
- 전체 선택 Part를 새 MusicXML로 내보내고 재파싱 검증한다.
- recipe와 source event 대응을 JSON sidecar로 저장할 수 있다.
- 상세 악보 상단 `Score Tools`에서 기능을 연다. 기존 좁은 툴바에 세 기능 버튼을 각각 배치하지 않았다.

### 당시 1차 지원 범위

- 입력: `score-partwise` MusicXML
- 선택: 전체 Part 복수 선택, 연속 measure ordinal 범위
- 출력: MusicXML, SVG, PNG, JPG, PDF, JSON sidecar
- 레이아웃: 한 줄, 가로 폭 지정 자동 줄 바꿈, 행 수 지정(2~12), 줄 바꿈 마디 직접 입력
- 표시 옵션: Remove Lyrics, Remove Dynamics
- 권한: 테스트용 전체 허용

### 당시 아직 지원하지 않던 범위

- score-timewise
- ~~Staff/Voice 추출과 cross-staff 정책~~ 2026-09-27 후속 단계에서 완료
- Systems 기준 선택과 reference layout snapshot
- 조옮긴 MusicXML 파일 저장과 chord-symbol 변환
- 조표 숨김과 임시표 재계산
- 서버 비동기 작업·영구 파생 버전 저장·상용 권한 판정

### 다음 순서

1. 대표 다성부·중간 조표 변경 fixture로 브라우저 POC를 검증한다.
2. ~~Transpose preview를 원본 기준 절대 recipe로 추가한다.~~ 완료
3. 전체 Part 추출 왕복 fixture를 확대한다.
4. reference layout의 System→measure ID mapping을 추가한다.
5. ~~PNG/JPG와 PDF 저장 경로를 추가한다.~~ 완료
6. ~~Staff/Voice와 복잡 기보는 별도 단계에서 구현한다.~~ Part/Staff/Voice 선택과 보수적 경계 정리 완료

### 검증 결과

- 기존 고정 의존성에서 `pnpm run build` 통과.
- Score Tools 기반과 기존 FullXmlNotation 관련 테스트 20/20 통과.
- 전체 회귀 600개 중 598개 통과. 실패한 2개는 기존 Motif 경계 기대값이며 이번 기능이 수정하지 않은 영역이다.
- 개발 서버가 새 패널과 변환 모듈을 정상 컴파일하여 HTTP 200으로 제공하는 것을 확인했다.
- Windows UI 자동화 샌드박스 초기화 오류로 실제 버튼 클릭·다운로드 눈검사는 이번 실행에서 완료하지 못했다. 다음 단계 시작 전에 대표 fixture로 확인한다.

## 2026-09-27 — 반음 단위 Transpose Preview와 Reset

- 설치된 Verovio 6.3의 `transpose` 옵션 계약과 숫자 문자열의 반음 이동을 런타임에서 확인했다.
- 선택 범위는 원조 기준 `-7`부터 `+7`까지의 정수 반음이고, UI 표시 순서는 `+7 … +1, 0, -1 … -7`이다. 음정명 문자열 방식은 사용자 검증 결과와 요구 사양에 맞춰 제거했다.
- 현재 뷰는 항상 원본 XML에서 선택한 절대 반음 수로 다시 렌더링한다. 반복 선택으로 조옮김이 누적되지 않는다.
- 매 렌더링마다 `transpose` 값을 빈 문자열까지 명시적으로 설정해 Reset 뒤에 이전 조옮김 상태가 남지 않게 했다.
- Verovio WASM 통합 회귀에서 `0`, `+1`, `+2`, `-1`의 실제 내부 pitch와 key signature를 비교하고 `-7`~`+7` 전 범위가 유효한 악보를 만드는지 검증한다.
- 전체 악보와 검색 일치 악보 조각을 같은 interval로 표시한다.
- 악보 재생도 동일한 semitone 수만큼 이동한다. 원본 note mapping과 검색 강조 좌표는 바꾸지 않는다.
- `Reset View`는 interval을 원조로 되돌린다. 다른 작품으로 이동할 때도 자동으로 원조 상태로 초기화한다.
- Measure Image Export에서 `현재 조옮김 적용` 체크박스로 Transpose 탭의 값을 적용하거나 원조로 추출한다. 별도 `Current View`/`Original Score` 드롭다운은 제거했으며 recipe와 sidecar에는 선택 source와 transpose가 계속 저장된다.
- 조옮긴 MusicXML 저장은 아직 비활성 상태다. 선택 Part MusicXML 버튼은 `원조`임을 명시한다.
- 반음 이동 통합 회귀까지 포함해 프로덕션 빌드와 Score Tools/악보 렌더링 집중 테스트 24/24가 통과했다.

## 2026-09-27 — 상세 악보 Part View

- Score Tools의 Part 체크 상태를 상세 악보 본문의 임시 렌더 문서에도 적용한다.
- 일부 Part만 체크하면 해당 Part들만 남겨 다시 조판하며, Trio에서 Violin만 체크하면 Violin 단독 파트보가 된다.
- 체크가 0개이거나 전체 Part가 체크된 상태는 모두 전체 악보로 정규화한다.
- 원본 MusicXML과 분석 데이터는 변경하지 않으며, 상세 악보 뷰와 Preview/내보내기 선택만 공유한다.
- 이 단계 완료 후 프로덕션 빌드와 집중 회귀 26/26이 통과했다.

## 2026-09-27 — SVG 이미지 폭과 시스템 줄바꿈

- 기존 한 줄을 그대로 유지하면서 가로 폭 지정 자동 줄 바꿈, 2~12 행 수 지정, 줄 바꿈 마디 직접 입력을 추가했다.
- 출력 폭은 600~3200px 범위의 50px 단위로 recipe에 저장한다.
- 행 수 지정은 선택된 measure ordinal을 요청 행 수에 맞춰 균등 분할하며, 직접 입력은 선택한 표시 마디 번호를 stable measure ID로 변환해 해당 마디가 새 시스템에서 시작되게 한다.
- 원본의 print/page-break는 파생 발췌에서 제거하고 recipe로 생성한 `new-system`만 임시 MusicXML에 삽입한다.
- 세부 계약, UI 동작, 검증 항목은 별도 문서 [`score-tools-image-layout.md`](score-tools-image-layout.md)에 기록한다.
- 프로덕션 빌드와 Score Tools 집중 회귀 30/30이 통과했다.

## 2026-09-27 — SVG·PNG·JPG·PDF 저장

- Preview 결과의 저장 형식을 SVG, PNG, JPG, PDF 중에서 선택한다.
- PNG/JPG는 브라우저 Canvas에서 지정 폭으로 래스터화하며, JPG는 흰 배경을 사용한다.
- PDF는 외부 런타임 의존성 없이 JPEG XObject 기반으로 생성하고 여러 SVG 페이지를 한 PDF로 묶는다.
- Canvas 안전 한도와 PDF page/media box 계약은 [`score-tools-image-layout.md`](score-tools-image-layout.md)에 기록한다.
- 프로덕션 빌드와 관련 집중 회귀 33/33이 통과했다. 임시 2페이지 PDF를 pypdf/pdfinfo로 재파싱하고 Poppler PNG로 재렌더링해 방향과 잘림을 확인한 뒤 QA 산출물은 제거했다.

## 2026-09-27 — 사용자 검토 반영: 3탭 UI와 이미지 추출 입력 정리

### 사용자 요청

- 한 패널에 기능과 버튼이 한꺼번에 노출되지 않도록 Score Tools를 `1. Transpose`, `2. Part Selection`, `3. Measure Image Export`의 상단 3탭으로 분리한다.
- 조옮김 값은 위로 올리는 선택부터 빠르게 찾을 수 있게 `+7`부터 `+1`, `0`, `-1`부터 `-7` 순서로 표시하고, 조작 의미를 영어 문장으로 안내한다.
- 이미지 source를 고르는 추상적인 `Current View`/`Original Score` 드롭다운 대신 현재 조옮김을 이미지에 적용하는지 직접 표시한다.
- 마디 범위 선택에서 구현용 `#ordinal`을 숨기고, 이미지 레이아웃 이름과 줄바꿈 입력을 사용자가 이해하는 마디·행 중심 용어로 바꾼다.

### 구현

- 상단 탭은 번호와 영문 기능명을 고정했다. 비활성 탭의 본문, Preview, footer 기능 버튼은 숨기고 활성 탭에 필요한 조작만 렌더링한다.
- Transpose 탭은 반음 옵션을 `+7 … +1, 0 · Original · 원조, -1 … -7` 순서로 제공하고 `Choose how many semitones to raise or lower every note.`를 표시한다. Transpose는 계속 원본 기준 절대값이며 누적되지 않는다.
- Part Selection 탭은 체크 상태를 상세 악보에 즉시 반영하고 footer에는 `선택 Part MusicXML · 원조`만 둔다. 이미지 Preview와 이미지 저장 버튼은 이 탭에서 보이지 않는다.
- Measure Image Export 탭은 마디 범위·레이아웃·표시 제거 옵션을 모은다. `현재 조옮김 적용` 체크박스를 켜면 Transpose 탭의 현재 값을 쓰고, 끄면 원조를 사용한다. 파트 선택은 어느 경우든 반영한다.
- Image 탭에서만 Preview와 `Sidecar JSON`, `Preview`, Format, `Export` footer를 표시한다. 입력이 바뀐 Preview는 stale로 표시하고 다시 생성하기 전 내보내기를 막는다.
- From/To 드롭다운은 `m.<표시 번호>`와 pickup 여부만 보여 주며 내부 ordinal은 노출하지 않는다. 내부에서는 선택한 option의 ordinal로 범위를 결정하고 recipe에는 stable start/end measure ID를 저장한다.
- 레이아웃 라벨은 `한 줄`, `가로 폭 지정 자동 줄 바꿈`, `행 수 지정`, `줄 바꿈 마디 직접 입력`이다. 행 수는 2~12로 정규화한다. 직접 입력한 표시 마디 번호는 선택 범위 안에서 유일한지 확인한 뒤 ordinal을 거쳐 stable measure ID로 저장하며, 범위 밖 번호와 중복 표시 번호는 명시적으로 차단한다.
- `ExcerptRecipe`를 `1.3.0`으로 올리고 `presentation.targetSystemCount`를 추가했다. layout 값은 `single_system | auto_wrap | system_count | custom_breaks`이며 실제 break 위치는 계속 `systemBreakBeforeMeasureIds`에 저장한다.

### 검증

- `src/score-tools/model.test.ts` 9/9가 통과했다. 옵션 순서, 2~12 행 수 정규화, 균등 break, 표시 마디 번호 parsing과 stable ID 변환을 포함한다.
- Score Tools 단위·Verovio 통합 집중 회귀 4파일 16/16이 통과했고 `npm run build`도 성공했다.
- 전체 회귀는 98파일 중 97파일, 615개 중 613개가 통과했다. 실패 2개는 `FullScorePage.test.ts`의 Motif overlay 기대값으로 이번 Score Tools 대상 밖이며, Score Tools 테스트 실패는 없다.

## 불변 조건

- 원본 XML hash는 변환 전후 같아야 한다.
- 미리보기와 다운로드는 같은 source version과 recipe hash를 사용한다.
- 파생 XML은 다시 파싱할 수 있어야 한다.
- recipe의 빈 선택, Part 중복, Staff/Voice 하위 선택 0개, 오래된 snapshot, 잘못된 마디 범위는 차단한다. UI의 전체 해제는 full-score whole-Part 선택으로 정규화한다.
- 화면 표시용 정규화는 다운로드 MusicXML에 반영하지 않는다.

## 2026-09-27 — 휴대형 package와 최종 인수인계

- `@musicanote/verovio-score-tools`는 현재 `0.2.1` private repo-local package다. registry publish가 아니라 `pnpm pack` tarball로 다른 viewer에 전달한다.
- entry는 core `.`, `./image`, `./verovio`, `./react`, `./style.css`다. core는 React, image exporter와 Verovio runtime을 재수출하지 않는다.
- host는 `createScoreToolsEngine`과 `createVerovioRenderer`에 renderer, fresh toolkit factory와 임시 DOM normalize hook을 주입할 수 있다.
- MusicSearch도 public React entry를 소비한다. 검색 DB/API와 수집 환경변수는 모듈 build/test/pack에 필요하지 않다.
- 명령은 `build:score-tools`, `test:score-tools`, `pack:score-tools`다. Node 24.19.0/pnpm 11.19.0에서 Staff/Voice 변환을 포함한 집중 테스트 34/34, 상세 렌더링 테스트 24/24와 모듈·main build가 통과했다.
- 기본 test-open policy는 개발 전용이다. Verovio 6.3.0은 LGPL-3.0-or-later이며 자체 license는 공개 배포 전에 확정한다.
- canonical 인수인계서는 [`VEROVIO_SCORE_TOOLS_PORTABLE_MODULE_FINAL_KO.md`](VEROVIO_SCORE_TOOLS_PORTABLE_MODULE_FINAL_KO.md)다.

## 2026-09-27 — Part / Staff / Voice 선택과 공통 파생 경로

### 데이터 계약과 호환성

- `PartSelection`을 `{ partId, scope: 'whole_part' } | { partId, scope: 'staves', staffIds } | { partId, scope: 'voices', voiceIds }`로 확장했다.
- 새 recipe는 `ViewRecipe 1.1.0`, `ExcerptRecipe 1.4.0`이다. 과거 whole-Part recipe는 계속 읽을 수 있고 `migrateViewRecipe`, `migrateExcerptRecipe`로 명시적으로 올린다.
- Staff ID와 Voice ID는 UI 순번이 아니라 source MusicXML 값을 사용한다. `<voice>`가 없으면 `__unassigned__`로 기록하고 Voice 1로 추정하지 않는다. 명시 Voice가 있는 chord head에 바로 이어지는 `<chord/>` 구성음만 그 Voice를 상속한다.
- `ScoreSnapshot 1.1.0`을 사용한다. 1.0 snapshot으로 scoped selection을 실행하려면 source hash가 같은 원본 XML을 `migrateScoreSnapshot`으로 다시 inventory해야 한다.
- 한 Part에는 한 selection scope만 허용한다. Staff와 Voice는 병렬 선택이며 Voice를 Staff 하위 트리에 종속시키지 않는다.

### MusicXML 변환

- `applyScoreViewSelections(doc, selections)`가 임시 DOM의 Part/Staff/Voice 선택을 공통 적용한다. `filterMusicXmlSelections`와 engine `filterSelections`를 공개했고 기존 `filterMusicXmlParts`/`filterParts`는 whole-Part 호환 wrapper로 유지한다.
- 음표만 삭제하지 않는다. 제거된 duration-bearing chord group은 `<forward>`로 바꾸고 기존 `<backup>/<forward>` 시간축을 유지한다. chord head가 빠지고 같은 화음의 선택 음만 남으면 동일 음가인지 확인한 뒤 남은 첫 음을 head로 승격한다.
- Staff 선택은 남은 Staff를 1부터 재배치하고 clef/key/time/staff-details의 번호를 함께 정리한다. cross-staff Voice의 일부가 선택 밖으로 나가면 경고한다.
- Voice 선택은 해당 Voice가 이동하는 모든 source Staff를 유지한다. 별도 `Compact to one staff`는 구현하지 않았다.
- 선택 경계에서 끊어지는 tie/slur/tuplet을 정리한다. 실제 이벤트 또는 선언 Staff가 제외되는 scoped 파생본만 explicit beam과 chord-wide arpeggiation을 보수적으로 정리한다. 모든 Staff/Voice를 유지하는 scope 전환은 원본 기보를 그대로 보존한다.
- Voice가 지정되지 않은 Staff 지시는 전역/공용일 수 있으므로 필요한 Staff에 보존하고 경고한다.
- 변환 뒤 XML을 다시 파싱해 선택 이벤트 수와 pitch/onset/duration/voice가 원본과 동일한지 확인한다. 실제 남은 이벤트만 source map에 포함하고 `derivedEventId`는 파생 XML의 실제 measure/event ordinal을 사용한다.

### UI와 공유 상태

- 두 번째 탭은 `Part / Staff / Voice`이며 Part마다 `Whole Part`, `Staff`, `Voice` 중 한 scope를 고른다. Voice는 Staff 아래에 중첩하지 않는다.
- 같은 `viewSelections`가 상세 악보, Measure Image Export, MusicXML export에 적용된다. Image 탭에서 포함 범위를 요약하고 `Edit Selection`으로 돌아간다.
- `viewPartIds` callback은 기존 host 호환을 위해 유지하고, 새 host는 `viewSelections`/`onViewSelectionsChange`를 권위 상태로 사용한다.
- Staff/Voice 하위 체크가 0개면 Preview와 export를 차단한다. 전체 Part whole selection 또는 UI의 전체 해제는 full score로 복귀한다.

### 검증과 남은 제한

- Staff 추출, cross-staff Voice, cross-staff chord head 승격, unassigned voice, 잘못된 ID와 legacy migration을 실제 MusicXML fixture로 검증했다.
- Score Tools 집중 테스트 6파일 34/34, 상세 렌더링 테스트 2파일 24/24, 모듈 빌드와 전체 애플리케이션 빌드가 2026-09-27 통과했다.
- 전체 회귀는 100파일 중 99파일, 627개 중 625개가 통과했다. 남은 2개는 기존 `FullScorePage.test.ts` Motif overlay 기대값으로 Staff/Voice 변환 경로와 무관하며 이 작업에서 검색·분석 규칙을 바꾸지 않았다.
- 마지막 Staff/Voice 체크 해제로 생기는 빈 하위 선택은 패널 안에서 경고하고 마지막 정상 host 선택을 유지한다. 외부의 stale/unknown 선택도 full score로 조용히 확장하지 않는다.
- Image Preview는 renderer 경고뿐 아니라 cross-staff/연결 정리 같은 MusicXML 변환 경고도 함께 표시하며, MusicXML 저장 뒤에도 같은 경고를 알린다.
- convenience API의 빈 selection은 React 뷰와 동일하게 full score로 통일했고, 영구 recipe의 빈 selection 차단은 유지했다.
- `score-timewise`, 선택 Voice를 한 오선으로 재기보하는 compact mode, 모든 제3자 MusicXML의 시각적 기보 복구는 계속 범위 밖이다.
