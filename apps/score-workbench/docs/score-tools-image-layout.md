# Score Tools 마디 이미지 레이아웃

## 목적

긴 발췌를 한 시스템에 강제로 넣어 음표가 지나치게 작아지는 문제를 해결한다. 원본 MusicXML은 수정하지 않으며 `ExcerptRecipe 1.4.0`과 파생 MusicXML만으로 같은 결과를 재현한다.

## Score Tools 안의 위치

Score Tools 상단에는 `1. Transpose`, `2. Part / Staff / Voice`, `3. Measure Image Export`의 세 탭만 둔다. 비활성 탭의 본문과 기능 버튼은 숨겨 서로 다른 작업의 조작이 한꺼번에 보이지 않게 한다.

| 활성 탭 | 본문 | Preview와 footer |
|---|---|---|
| 1. Transpose | 원본 기준 반음 선택과 Reset View | 별도 Preview·export footer 없음 |
| 2. Part / Staff / Voice | 상세 악보에 즉시 반영되는 Part별 whole Part/Staff/Voice 선택 | Preview 없음, 선택 범위 MusicXML export만 표시 |
| 3. Measure Image Export | 마디 범위, 현재 조옮김 적용, 레이아웃, 표시 제거 옵션 | 이미지 Preview와 `Sidecar JSON`, `Preview`, Format, `Export`만 표시 |

Image 탭에서 옵션이 바뀌면 기존 Preview를 stale로 표시한다. 현재 선택으로 Preview를 다시 만들기 전에는 sidecar와 이미지 내보내기를 실행할 수 없다.

## 사용자 선택

| Layout | 동작 |
|---|---|
| 한 줄 | 선택 범위를 한 시스템으로 만들며 폭은 내용 길이에 따라 확장된다. |
| 가로 폭 지정 자동 줄 바꿈 | 지정 폭 안에서 Verovio 자동 조판으로 행 수를 결정한다. |
| 행 수 지정 | 2~12 사이의 행 수를 입력하면 선택된 measure ordinal을 그 수에 맞춰 균등 분할한다. 마디 수보다 많은 행은 만들지 않는다. |
| 줄 바꿈 마디 직접 입력 | 새 행에서 시작할 표시 마디 번호를 쉼표 또는 공백으로 입력한다. |

`Image width`는 600~3200px, 50px 단위다. 한 줄 모드에서는 기존 내용 폭을 보존하므로 비활성화된다. 다른 모드에서는 Verovio scale을 고려해 pageWidth로 변환하며, 내보낸 SVG에 명시적인 width/height도 기록한다.

From/To 드롭다운은 `m.<표시 번호>`와 pickup 여부만 표시한다. 구현용 `#ordinal`은 화면에 노출하지 않지만 option 값은 내부 ordinal이고, recipe 범위는 그 ordinal에 해당하는 stable start/end measure ID로 저장한다.

직접 입력한 줄바꿈 번호는 현재 From/To 범위 안의 `displayNumber`와 대조한다. 범위 밖 번호는 찾을 수 없음으로, 같은 표시 번호가 범위 안에 여러 번 있으면 모호함으로 표시해 Preview를 차단한다. 유일하게 찾은 번호만 ordinal을 거쳐 stable measure ID로 변환한다.

이미지 source용 `Current View`/`Original Score` 드롭다운은 두지 않는다. `현재 조옮김 적용` 체크박스를 켜면 Transpose 탭의 현재 반음 이동을 적용하고, 끄면 원조로 추출한다. 현재 값이 원조이면 체크박스는 비활성화된다. Part / Staff / Voice 탭의 `viewSelections`는 상세 악보, 이미지 Preview, SVG/PNG/JPG/PDF, MusicXML export에 동일하게 적용한다. Image 탭은 현재 포함 범위를 요약하고 `Edit Selection`으로 선택 탭에 돌아갈 수 있게 한다.

## 저장 형식

- `SVG`: Verovio 벡터 결과를 그대로 저장한다.
- `PNG`: SVG를 지정 해상도의 Canvas로 변환하며 투명 배경을 보존한다.
- `JPG`: 같은 Canvas 변환을 사용하고 흰색 배경과 quality 0.94를 적용한다.
- `PDF`: 각 SVG 페이지를 흰색 배경의 quality 0.95 JPEG로 변환해 하나의 다중 페이지 PDF에 넣는다. 픽셀은 96dpi 기준으로 0.75pt에 대응한다.

브라우저 Canvas 한계를 넘는 이미지에는 최대 한 변 16,384px, 최대 면적 48MP를 적용하고 종횡비를 유지한다. 여러 SVG 페이지가 생긴 PNG/JPG는 번호가 붙은 개별 파일로, PDF는 한 파일로 저장한다.

## Recipe 계약

`ExcerptRecipe.schemaVersion`은 `1.4.0`이다. `selections`에는 Part별 `whole_part | staves | voices` 범위를 저장하고 `presentation`에는 다음 값을 저장한다.

- `layout`: `single_system | auto_wrap | system_count | custom_breaks`
- `imageWidthPx`: 정규화된 SVG 가로 폭
- `targetSystemCount`: `system_count`가 목표로 하는 행 수. 2~12로 정규화하며 다른 layout에서도 결정적인 기본값을 저장한다.
- `systemBreakBeforeMeasureIds`: 새 시스템에서 시작할 stable measure ID 배열

`system_count`도 계산된 최종 break ID를 저장하므로 나중에 균등 분할 계산법이 바뀌어도 기존 sidecar가 가리키는 위치를 확인할 수 있다. `source`와 `view.transpose`는 체크박스의 의미를 각각 `original`/`current_view`와 절대 반음 recipe로 기록하며, 이를 고르는 별도 source 드롭다운은 없다.

## 파생 처리

1. 선택 Part/Staff/Voice와 연속 마디를 원본에서 다시 추출한다. Staff/Voice 변환은 원본 시간축을 `backup`/`forward`로 보존하고 파생 XML의 semantic validation을 통과해야 한다.
2. 원본의 `print` 지시를 발췌에서 제거한다.
3. recipe의 stable start/end measure ID와 break ID를 원본 measure ordinal로 복원한다.
4. 첫 번째 surviving Part의 해당 마디에만 `<print new-system="yes"/>`를 삽입한다.
5. 한 줄은 Verovio `breaks=none`, 자동 줄 바꿈은 `breaks=auto`, 행 수 지정과 직접 입력은 `breaks=line`으로 렌더링한다.
6. 결과 SVG의 시스템 수와 실제 폭을 Preview 상단에 표시한다.

## 불변 조건

- 원본 XML과 원본 hash를 변경하지 않는다.
- 마디 표기 번호는 사용자 입력과 표시에서만 사용하고, recipe 범위와 줄바꿈은 stable measure ID로 식별한다.
- 못갖춘마디나 중복된 표시 마디 번호가 있어도 내부 ordinal 기준은 변하지 않는다. 중복 표시 번호를 임의로 한 마디에 연결하지 않는다.
- 현재 한 줄 방식은 계속 선택할 수 있다.
- Part/Staff/Voice 선택, 조옮김, 가사/다이내믹 제거와 동일 recipe 안에서 조합할 수 있다.
- Voice 선택은 그 Voice가 사용하는 필요한 source Staff를 모두 유지한다. Staff 선택이 cross-staff Voice의 일부만 남기면 Preview와 파생 결과에 경고를 제공한다.
- 여러 시스템 미리보기는 SVG 자체를 높이에 맞춰 축소하지 않고, 미리보기 컨테이너가 세로·가로 스크롤을 담당한다.

## 검증

- Transpose 옵션이 `+7 … +1, 0, -1 … -7` 순서인지 검사한다.
- 12마디에서 목표 2행은 한 곳, 3행은 두 곳의 결정적 break ID를 생성하고, 행 수 입력을 2~12로 정규화한다.
- 표시 마디 번호 입력에서 `m.` 접두어·쉼표·공백을 처리하고, 범위 밖 번호와 중복 표시 번호를 각각 unmatched·ambiguous로 분리한다.
- 직접 입력과 행 수 지정이 생성한 ordinal을 stable measure ID로 바꾸며 첫 마디·범위 밖·중복 break를 저장하지 않는다.
- 600~3200px clamp와 scale별 Verovio pageWidth 변환을 단위 테스트한다.
- 실제 Verovio WASM에서 `none`은 1 system, `line`과 두 개의 `new-system`은 3 systems가 되는지 검증한다.
- scale 25, pageWidth 4800에서 SVG viewBox 폭이 1200px인지 검증한다.
- PDF 구조 회귀는 페이지 수, JPEG XObject 수, MediaBox 크기, xref/EOF 생성을 확인한다.
- 기존 저장 형식 구현 시 집중 회귀 33/33이 통과했다. 1200×800과 800×1200 임시 JPEG를 한 PDF로 묶어 2페이지, 900×600pt와 600×900pt MediaBox를 확인하고 Poppler 재렌더의 content bounding box가 모든 변에서 안쪽에 남는지 검사했다.
- 2026-09-27 UI·recipe 정리 후 `src/score-tools/model.test.ts` 9/9, Score Tools 단위·Verovio 통합 집중 회귀 4파일 16/16, 프로덕션 빌드가 통과했다.
- 같은 시점의 전체 회귀는 613/615가 통과했다. Score Tools 검사는 모두 통과했으며 나머지 2건은 `FullScorePage.test.ts`의 Motif overlay 기대값이다.
- 2026-09-27 Staff/Voice 통합 뒤에는 실제 MusicXML selection transform을 포함한 Score Tools 집중 테스트 6파일 28/28, 모듈 빌드와 전체 애플리케이션 빌드가 통과했다. Preview에는 renderer 경고와 MusicXML selection 경고를 함께 표시한다.

## 후속 범위

- 시스템별 개별 이미지 저장
- 드래그로 줄바꿈 위치 재배치
- reference layout의 기존 시스템 경계 불러오기
