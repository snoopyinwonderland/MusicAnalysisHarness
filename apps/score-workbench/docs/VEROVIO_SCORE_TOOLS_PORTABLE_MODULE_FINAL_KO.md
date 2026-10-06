# Verovio Score Tools 휴대형 모듈 최종 개발·인수인계서

문서 기준일: 2026-09-27  
모듈 버전: `@musicanote/verovio-score-tools` `0.2.1`  
Recipe 계약: `ScoreSnapshot 1.1.0`, `ViewRecipe 1.1.0`, `ExcerptRecipe 1.4.0`  
현재 배포 방식: 비공개 저장소 안의 repo-local package, `pnpm pack` 전용. npm registry에는 publish하지 않는다.

## 1. 이 문서의 목적

이 문서는 다음 두 경우에 필요한 정보를 한곳에 모은 최종 인수인계 문서다.

1. 다른 컴퓨터에서 MusicSearch 저장소를 받아 Score Tools 개발을 그대로 재개한다.
2. MusicSearch와 무관한 React/Verovio 악보 뷰어에 Score Tools만 로컬 패키지로 붙인다.

모듈의 목표는 원본 `score-partwise` MusicXML을 변경하지 않고 다음 파생 기능을 제공하는 것이다.

- 원조 기준 `-7`~`+7` 반음 Transpose 보기
- Part별 전체 Part, Staff 또는 Voice 선택과 같은 선택을 적용한 MusicXML 파생본
- 연속 마디 발췌
- 한 줄, 폭 기준 자동 줄 바꿈, 지정 행 수, 직접 지정 마디 줄 바꿈
- SVG Preview와 SVG/PNG/JPG/PDF 저장
- 원본 hash, recipe hash, source event 대응을 포함한 재현용 sidecar
- 기존 뷰어가 가진 Verovio runtime과 연결할 수 있는 renderer 주입점

### 비목표

- 검색 엔진, 검색 DB, YouTube/KY 수집기, Music Analysis Canonical IR을 패키지에 포함하지 않는다.
- 이 모듈이 호스트의 전체 악보 뷰어, 라우터, 재생기, 사용자 인증을 대체하지 않는다.
- 원본 MusicXML을 덮어쓰거나 조옮긴 MusicXML 원본을 저장하지 않는다.
- `score-timewise`와 선택 Voice를 한 오선으로 강제 압축하는 `Compact to one staff`는 아직 지원하지 않는다.
- 독립 음표의 누락 Voice를 추정하거나 없는 음을 합성하지 않는다. `<voice>` 없는 연속 `<chord/>` 구성음은 바로 앞 chord head에 명시 Voice가 있을 때만 그 Voice를 상속한다.
- 상용 권한 정책을 모듈 내부에서 임의로 결정하지 않는다.

검색 corpus, SQLite index, API server 및 `YOUTUBE_API_KEY` 같은 MusicSearch 환경변수는 이 모듈의 빌드·테스트·다른 뷰어 통합에 필요하지 않다.

## 2. 모듈 구조와 entrypoint

```text
MusicSearch/
├─ src/score-tools/                    # core/image/verovio/react entry와 구현
├─ src/components/ScoreToolsPanel.tsx  # React UI
├─ src/score-tools.css                 # 독립 stylesheet
├─ src/music/verovioRuntime.ts         # 기본 Verovio WASM loader
├─ src/music/musicXmlVoiceNormalizer.ts# 임시 render DOM normalize hook
├─ packages/verovio-score-tools/       # package metadata와 생성된 dist
├─ vite.score-tools.config.ts          # ES2022 ESM library build
└─ tsconfig.score-tools.json           # declaration build
```

실제 TypeScript 원본은 `src`에 있으며 `packages/verovio-score-tools/dist`는 생성물이다. 다른 PC에서 개발할 때는 전체 저장소를 clone한다. 다른 제품에서 사용만 할 때는 `pnpm pack`으로 만든 tarball을 설치한다.

| import | 역할 | 주요 export |
|---|---|---|
| `@musicanote/verovio-score-tools` | UI 비종속 core | snapshot, recipe, 변환, layout helper, `createScoreToolsEngine` |
| `@musicanote/verovio-score-tools/image` | 이미지/PDF | `rasterizeSvg`, `pdfFromSvgPages`, `downloadBlobFile` |
| `@musicanote/verovio-score-tools/verovio` | SVG renderer | `createVerovioRenderer`, 기본 renderer, sanitizer와 renderer type |
| `@musicanote/verovio-score-tools/react` | 선택 UI | `ScoreToolsPanel`, `ScoreToolsPanelProps` |
| `@musicanote/verovio-score-tools/style.css` | UI 스타일 | CSS |

core entry는 React, image exporter, Verovio runtime을 재수출하지 않는다. 현재 MusicSearch 상세 악보도 `src/score-tools/react.ts` public React entry를 소비한다.

## 3. 핵심 데이터 계약과 원본 불변

`createScoreSnapshot(xml, sourceId)`는 XML 문자열 SHA-256 `sourceHash`, `sourceVersionId`, Part/Measure/Event inventory, 기약분수 onset/duration을 만든다. 참조 형식은 `measure:<ordinal>`, `event:<partId>:<measureOrdinal>:<eventOrdinal>`이다. 이 ID는 동일 source hash 안에서 안정적이며 원본이 바뀌면 새 snapshot을 만들어야 한다.

- `ViewRecipe 1.1.0`: 절대 반음 transpose와 Part별 `whole_part | staves | voices` 선택
- `ExcerptRecipe 1.4.0`: source, transpose, 연속 마디 stable ID, Part/Staff/Voice 선택, layout과 표시 옵션
- `ScoreSnapshot 1.1.0`: 명시 Voice와 안전한 chord-head Voice 상속을 구별하는 inventory
- sidecar `1.1.0`: source ID/hash, snapshot schema, recipe hash, recipe와 source/derived event map

`PartSelection`은 `{ partId, scope: 'whole_part' }`, `{ partId, scope: 'staves', staffIds }`, `{ partId, scope: 'voices', voiceIds }`의 union이다. 한 Part에는 한 scope만 둔다. Staff와 Voice는 병렬 선택이며 Voice를 특정 Staff 아래에 종속시키지 않는다. source `<voice>`가 없으면 원칙적으로 `__unassigned__`로 기록하고 Voice 1이라고 추정하지 않는다. 단, 명시 Voice를 가진 chord head에 바로 이어지는 `<chord/>` 구성음만 그 head Voice를 상속한다.

`ExcerptRecipe 1.4.0` layout은 `single_system | auto_wrap | system_count | custom_breaks`다. 최종 break는 `systemBreakBeforeMeasureIds`에 stable ID로 저장한다.

불변 조건은 다음과 같다.

- 모든 파생 작업은 새 DOM에서 수행하고 입력 XML 문자열을 변경하지 않는다.
- Part/Staff/Voice 및 마디 제거, lyrics/dynamics 제거, `new-system` 삽입은 파생 DOM에만 적용한다.
- Staff/Voice 추출은 원본 onset과 duration을 해석하고 제거된 시간은 `forward`로 보존한다. `<backup>/<forward>`, chord head와 Staff 번호를 파생본에 맞게 재구성한다.
- Voice 선택은 그 Voice가 사용하는 원래 Staff를 모두 유지한다. Staff 선택이 cross-staff Voice의 일부 음을 제외하면 경고한다.
- 선택 경계에서 불완전해질 tie/slur/tuplet/beam/arpeggiation은 검증·정리하고 `DerivedScore.warnings`에 남긴다.
- `normalizeDocument`도 render 직전 임시 DOM만 변경한다.
- snapshot과 recipe의 source hash/version이 다르면 거부한다.
- 파생 XML은 재파싱하고 남은 pitch/onset/duration/voice가 선택 전 원본과 같은지 검증한다.
- transpose는 현재 Verovio render option이며 조옮긴 MusicXML 파일 저장 기능이 아니다.

## 4. 다른 컴퓨터에서 개발 재개

실제 검증 환경은 Node.js `24.19.0`, pnpm `11.19.0`이다. 현재 Vite 도구 체인 조건에 맞춰 Node.js `>=22.12.0`을 권장하며 루트 `package.json`은 `pnpm@11.19.0`을 고정한다. Node 20 계열을 써야 한다면 `>=20.19.0`이어야 한다.

중요: 이 문서 작성 직후 작업 트리에는 Score Tools의 신규 파일이 아직 Git 미추적 상태로 남아 있다. 아래 `git clone` 절차는 관련 파일을 commit하고 private remote에 push한 뒤에만 완전하다. 그 전에는 현재 workspace 전체를 안전하게 복사해야 하며, 설치용 `.tgz`만으로는 TypeScript 원본 개발을 재개할 수 없다.

```powershell
git clone <PRIVATE_REPOSITORY_URL> MusicSearch
Set-Location MusicSearch
corepack enable
corepack prepare pnpm@11.19.0 --activate
pnpm install --frozen-lockfile

pnpm test:score-tools
pnpm build:score-tools
pnpm pack:score-tools
```

Corepack이 없는 Node 배포판은 공식 절차로 먼저 설치한다. `npm install`로 새 lockfile을 만들지 않는다.

- `build:score-tools`: ESM bundle, CSS, source map과 `.d.ts` 생성
- `test:score-tools`: 공개 API, image, layout, 실제 Verovio transpose 통합 회귀
- `pack:score-tools`: build 뒤 설치 가능한 `.tgz` 생성. 명령이 출력한 경로를 사용한다.

2026-09-27 기준 검증 스크립트는 10개 필수 `dist` 파일과 실행 가능한 core/image/verovio entry 3개를 확인했다. Staff/Voice 실제 MusicXML 변환을 포함한 Score Tools 집중 테스트 34/34, 상세 렌더링 테스트 24/24, 모듈 build와 MusicSearch main build도 모두 통과했다. 실제 KY/PDMX 241개 파일·312,664개 음표의 Voice 표기를 계측했고, 다중 Staff PDMX의 Staff 1/2 및 Voice 파생본을 Verovio SVG까지 렌더링했다. 이는 clean consumer 프로젝트에 tarball을 설치하는 통합 테스트나 브라우저 수동 클릭 QA를 대신하지 않는다.

MusicSearch host까지 확인할 때는 `pnpm dev`, `pnpm build`, `pnpm test`를 사용한다. 검색 DB/API 없이도 모듈 test/build/pack은 실행할 수 있다.

### 다른 PC 체크리스트

1. Node/pnpm 버전을 기록하고 frozen install 뒤 lockfile이 바뀌지 않았는지 본다.
2. 집중 테스트와 모듈 build를 먼저 통과시킨다.
3. `dist`의 core/image/verovio/react JS, CSS, types를 확인한다.
4. tarball을 작은 viewer fixture에 설치해 package exports를 확인한다.
5. Transpose, 단일 Part/Staff/Voice, cross-staff Voice, full score 복귀, 네 layout, 네 image format을 눈검사한다.
6. 변경 후 Score Tools 개발 문서와 개발 로그를 갱신한다.

## 5. 다른 viewer에 설치

이 package는 `private: true`인 repo-local package다. registry publish 대신 승인된 내부 경로로 tarball을 전달한다.

```powershell
# MusicSearch
pnpm pack:score-tools

# 다른 viewer: 위 명령이 출력한 실제 tgz 경로 사용
pnpm add <PATH_TO_SCORE_TOOLS_TGZ>
pnpm add react@^19 react-dom@^19 lucide-react@^1.34 verovio@6.3.0
```

peer 범위는 React/ReactDOM `>=18 <20`, `lucide-react >=0.400.0`, Verovio `>=6.3.0 <7`이다. 위 명령은 현재 검증한 major 조합을 재현하는 예이며 기존 React 18 host는 올릴 필요가 없다. major upgrade 전에는 SVG, transpose, layout 회귀를 다시 수행한다.

## 6. React viewer 통합

```tsx
import { useMemo, useState } from 'react';
import type { PartSelection } from '@musicanote/verovio-score-tools';
import { ScoreToolsPanel } from '@musicanote/verovio-score-tools/react';
import { createVerovioRenderer } from '@musicanote/verovio-score-tools/verovio';
import '@musicanote/verovio-score-tools/style.css';

export function ViewerScoreTools({ xml, workId, revision, title }) {
  const [open, setOpen] = useState(false);
  const [transpose, setTranspose] = useState('');
  const [partIds, setPartIds] = useState<string[]>([]); // legacy whole-Part bridge
  const [selections, setSelections] = useState<PartSelection[]>([]);
  const renderer = useMemo(() => createVerovioRenderer({
    createToolkit: ownToolkitFactory,
    normalizeDocument(document) { normalizeForThisViewer(document); },
  }), []);

  return <>
    <ExistingVerovioViewer xml={xml} transpose={transpose} selections={selections}/>
    <ScoreToolsPanel
      open={open} onClose={() => setOpen(false)}
      xml={xml} sourceId={workId} revisionKey={revision} title={title}
      initialStart={1} initialEnd={4}
      transpose={transpose} onTransposeChange={setTranspose}
      viewPartIds={partIds} onViewPartIdsChange={setPartIds}
      viewSelections={selections} onViewSelectionsChange={setSelections}
      renderScoreToSvg={renderer} exportPolicy={productionExportPolicy}
    />
  </>;
}
```

패널은 기존 full-score viewer를 소유하지 않는다. host가 callback 결과를 본문 viewer에도 적용한다. `viewSelections=[]`는 full score이며 새 통합의 권위 상태다. `viewPartIds`는 기존 whole-Part host와의 호환 bridge로 유지한다.

| React prop | 필수 | 의미 |
|---|---:|---|
| `open`, `onClose` | 예 | host 소유 panel state |
| `xml`, `sourceId`, `title` | 예 | 원본 XML, 작품 ID, 파일명 제목 |
| `revisionKey` | 권장 | 원본 revision 변경 시 snapshot 재생성 |
| `streamId` | 아니오 | deprecated MusicSearch bridge |
| `accessPolicy` | 아니오 | policy adapter에 전달할 host 문자열 |
| `initialStart`, `initialEnd` | 예 | 표시 번호 lookup과 ordinal fallback |
| `initialStartMeasureId`, `initialEndMeasureId` | 권장 | 알려진 stable measure ID |
| `transpose`, callback | 예 | `''` 또는 `-7`~`7` 정수 문자열 |
| `viewPartIds`, callback | 예 | 일부 Part ID; 빈 배열은 full score |
| `viewSelections`, callback | 새 통합에 권장 | Part별 whole Part/Staff/Voice 선택; 빈 배열은 full score |
| `exportPolicy` | 운영 시 필수 | preview/export policy adapter |
| `renderScoreToSvg` | 권장 | host Verovio renderer |

## 7. Verovio toolkitFactory와 normalize hook

최소 toolkit 계약은 `setOptions`, `loadData`, `getPageCount`, `renderToSVG`다. `createToolkit`은 render마다 새 toolkit instance를 반환한다. WASM module은 cache해도 mutable toolkit은 공유하지 않는다.

Verovio 6.3.0은 `verovio/esm`, `verovio/wasm`용 TypeScript 선언을 제공하지 않는다. 이를 직접 import하는 TypeScript host는 먼저 `src/verovio-peer.d.ts` 같은 파일을 추가한다.

```ts
declare module 'verovio/wasm' {
  const createVerovioModule: () => Promise<unknown>;
  export default createVerovioModule;
}
declare module 'verovio/esm' {
  export class VerovioToolkit {
    constructor(module: unknown);
    setOptions(options: Record<string, unknown>): void;
    loadData(data: string): boolean;
    getPageCount(): number;
    renderToSVG(page: number, xmlDeclaration?: boolean): string;
  }
}
```

```ts
import createVerovioModule from 'verovio/wasm';
import { VerovioToolkit } from 'verovio/esm';
import { createVerovioRenderer } from '@musicanote/verovio-score-tools/verovio';

const modulePromise = createVerovioModule();
const renderer = createVerovioRenderer({
  createToolkit: async () => new VerovioToolkit(await modulePromise as never),
  normalizeDocument: async document => {
    // 선택 사항: 원본이 아닌 render 임시 DOM만 안전하게 교정한다.
  },
});
```

MusicSearch 기본 adapter는 안전 조건을 충족한 beat-interleaved voice만 임시 DOM에서 재배열한다. 다른 host는 자체 loader/worker/normalizer를 위 주입점에 연결한다.

## 8. Headless/core 예제

```ts
import { createScoreToolsEngine, transposeRecipe }
  from '@musicanote/verovio-score-tools';

const engine = createScoreToolsEngine();
const snapshot = await engine.createSnapshot(musicXml, 'catalog/work-123');
const recipe = engine.createDefaultExcerptRecipe(snapshot, 5, 8);
recipe.source = 'current_view';
recipe.view.transpose = transposeRecipe('2');
recipe.selections = [{ partId: snapshot.parts[0].id, scope: 'whole_part' }];
const derived = await engine.deriveExcerpt(musicXml, snapshot, recipe);
const sidecar = engine.createSidecar(snapshot, derived, recipe);

const voiceOnly = await engine.filterSelections(musicXml, [
  { partId: 'P1', scope: 'voices', voiceIds: ['1'] },
], 'catalog/work-123');
```

`filterMusicXmlSelections`와 engine의 `filterSelections`는 Staff/Voice-aware convenience API다. 이 convenience API와 React `viewSelections`의 빈 배열은 full score를 뜻한다. 반면 저장 recipe는 재현성을 위해 한 개 이상의 명시적 selection을 요구한다. `filterMusicXmlParts`와 `filterParts`는 기존 whole-Part 호출을 위한 호환 wrapper다. `applyScoreViewSelections(doc, selections)`는 host가 만든 임시 DOM에 같은 선택을 적용하고 정규화된 선택과 경고를 반환한다.

renderer는 `createScoreToolsEngine({ renderDerivedScore: renderer })`로 주입한다. Node headless 변환은 DOMParser/XMLSerializer 호환 DOM과 Web Crypto가 필요하다. 집중 테스트는 `@xmldom/xmldom` adapter를 사용한다. image entry는 Canvas와 `Image`를 사용하므로 일반 SSR에서 바로 실행되지 않는다.

## 9. Host 책임과 권한

Host는 원본 load/저장, 작품 identity/revision, panel/transpose/Part/Staff/Voice state, callback의 full-score viewer 반영, WASM loading, 권한, download 정책, upload 크기 제한과 CSP를 책임진다. 검색 강조, playback, URL과 작품 metadata는 package 계약이 아니다.

기본 `testOpenScoreExportPolicy`는 개발 전용이며 모든 action을 허용한다. 운영 host는 `ScoreExportPolicy`를 제공하고 `preview | svg | musicxml | png | jpg | pdf`를 판정한다. 이 adapter는 client-side UI 경계이므로 보호 자료는 서버 원본 API/download endpoint에서도 다시 검증한다.

```ts
const productionExportPolicy: ScoreExportPolicy = {
  mode: 'enforced',
  decide({ action, accessPolicy }) {
    if (action === 'preview') return { allowed: true };
    return accessPolicy === 'export-allowed'
      ? { allowed: true }
      : { allowed: false, reason: '이 악보는 내보낼 수 없습니다.' };
  },
};
```

## 10. 이미지 출력과 CSS

- SVG: sanitizer를 거친 page별 Verovio SVG
- PNG: 투명 배경 Canvas raster
- JPG: 흰 배경, 기본 quality 0.94
- PDF: 여러 SVG를 JPG page로 바꾼 하나의 raster PDF
- Canvas 상한: 한 변 16,384px, 총 48,000,000 pixel; 초과 시 비율 유지 축소
- image width 600~3,200px, 50px 단위; system count 2~12

React entry는 declaration 이식성을 위해 CSS를 side effect로 자동 import하지 않는다. Host가 `style.css` entry를 한 번 명시적으로 import한다. `.score-tools-*` prefix와 `--score-tools-font-sans`, `--score-tools-font-mono`, `--score-tools-font-title`, `--score-tools-surface`, `--score-tools-panel-bg`, `--score-tools-text`, `--score-tools-muted`, `--score-tools-accent`, `--score-tools-accent-soft`를 override할 수 있다. CSS의 `color-mix`, sticky/grid/backdrop-filter 때문에 오래된 browser는 fallback QA가 필요하다.

## 11. 보안

`sanitizeVerovioSvg`는 script/foreignObject/iframe/object/embed, inline event handler와 `javascript:` link를 제거한다. 정규식 sanitizer 하나를 모든 제3자 SVG의 완전한 보안 경계로 보지는 않는다. 제3자 SVG를 직접 입력하지 말고 높은 보안 수준에서는 CSP/Trusted Types와 검증된 allowlist sanitizer를 host에 추가한다.

비신뢰 MusicXML은 upload 크기·복잡도를 제한하고 server DOM shim에서 DTD/외부 entity/network resolution을 비활성화한다. 파생 결과는 원본 위치에 덮어쓰지 않는다.

## 12. Browser/SSR 제한

- core: DOMParser, XMLSerializer, Web Crypto, TextEncoder
- download: Blob, object URL, document/anchor
- raster/PDF: Canvas, Image, canvas.toBlob
- Verovio: bundler가 `verovio/esm`, `verovio/wasm`을 resolve해야 한다.
- build target은 ES2022이며 큰 score는 main thread를 잠시 막을 수 있다.
- `.mxl`은 host가 먼저 MusicXML 문자열로 풀어야 한다.
- SSR은 DOM/Web Crypto adapter가 필요하고 Canvas export는 browser-oriented다.

## 13. 알려진 제한

- `score-partwise`만 지원하며 `score-timewise`는 거부한다.
- Part별 whole Part, Staff 또는 Voice를 선택한다. 한 Part에서 Staff와 Voice를 동시에 혼합하는 selection은 지원하지 않는다.
- Voice 선택은 필요한 source Staff를 유지한다. 별도 `Compact to one staff` 재기보는 지원하지 않는다.
- Staff 선택은 cross-staff Voice의 선택 밖 음을 제외하며 경고한다. beam/arpeggiation 등 선택 경계에서 불완전할 수 있는 기호는 보수적으로 정리되므로 파생본의 자동 beam/수동 기보를 눈검사한다.
- Voice가 지정되지 않은 Staff 지시는 전역/공용일 수 있어 필요한 Staff에 보존하고 경고한다.
- 마디는 연속 범위이고 Part group은 파생본에서 제거된다.
- 중복 표시 마디 번호는 직접 줄 바꿈 입력에서 차단한다.
- transposed MusicXML과 chord-symbol/spelling/accidental 재작성은 없다.
- PDF는 raster이며 source hash는 XML 문자열 전체에 민감하다.
- 기본 normalizer는 안전하게 판별한 voice만 교정하며 모든 비정상 XML을 복구하지 않는다.

## 14. 테스트와 QA

`pnpm test:score-tools`는 model, 실제 Staff/Voice MusicXML transform, image export, Verovio layout/transpose와 public API를 검사한다. core entry 격리, render마다 새 toolkit, SVG sanitize, `-7`~`+7` 실제 pitch/key 이동, Staff 번호 압축, cross-staff Voice의 필요 Staff 유지, chord head 승격, 보수적인 unassigned voice, effective attributes, 실제 derived event ID, 빈 선택/full-score 계약, 네 layout과 stable break ID, image/PDF 유효성, source mismatch 차단이 핵심 계약이다. 2026-09-27 결과는 34/34 통과다.

수동 QA에서는 transpose/reset, 단일 Part/Staff/Voice와 full score, cross-staff Voice 경고, pickup 및 조표·박자 변경 범위, 네 layout, lyrics/dynamics 제거, 네 저장 형식, sidecar hash와 7/12개 이상 staff overflow를 확인한다.

## 15. Migration과 versioning

- package `0.2.1`과 snapshot/recipe/sidecar schema version은 서로 별도다.
- 저장 recipe version을 무시하거나 최신 type으로 강제 cast하지 않는다.
- schema 변경에는 명시적 migrator, fixture와 round-trip test를 추가한다.
- 과거 `two_systems/three_systems`는 `system_count`와 `targetSystemCount: 2/3`으로 변환한다.
- ExcerptRecipe 1.2에서 1.3으로 올릴 때 `targetSystemCount`와 layout을 채운다. core는 자동 migration하지 않는다.
- ViewRecipe 1.0 → 1.1은 `migrateViewRecipe`, ExcerptRecipe 1.3 → 1.4는 `migrateExcerptRecipe`로 명시적으로 올린다. 기존 whole-Part selection은 그대로 호환된다.
- legacy recipe schema에 Staff/Voice scope를 억지로 넣으면 변환을 거부한다.
- `ScoreSnapshot 1.0.0`은 원본 XML과 `migrateScoreSnapshot`으로 다시 inventory한 뒤 scoped selection에 사용한다. source hash가 다르면 migration을 거부한다.
- source hash가 다르면 새 snapshot에서 recipe를 다시 만든다.
- public export 변경 시 package exports, public API test, README와 이 문서를 함께 바꾼다.

## 16. 파일 지도

| 파일 | 책임 |
|---|---|
| `src/score-tools/model.ts` | snapshot/recipe/policy/hash type |
| `musicXmlTransform.ts` | parse, inventory, Part/Staff/Voice timeline 변환, excerpt/source map와 semantic 검증 |
| `transposition.ts` | 절대 반음 option/recipe |
| `excerptLayout.ts` | width/system/break 계산 |
| `engine.ts` | stateless facade와 renderer 주입 |
| `verovioExport.ts` | toolkit adapter, SVG render/sanitize |
| `imageExport.ts` | PNG/JPG/PDF와 Blob download |
| `index.ts`, `image.ts`, `verovio.ts`, `react.ts` | public entry |
| `ScoreToolsPanel.tsx`, `score-tools.css` | React UI와 theme |
| `vite.score-tools.config.ts`, `tsconfig.score-tools.json` | module/declaration build |
| `packages/verovio-score-tools/package.json` | exports와 peer 계약 |
| `docs/score-tools-image-layout.md` | layout 세부 계약 |

## 17. 라이선스

설치된 Verovio `6.3.0` metadata는 `LGPL-3.0-or-later`다. `packages/verovio-score-tools/THIRD_PARTY_NOTICES.md`를 보존하고 배포 전 LGPL 고지·재링크 의무와 WASM 배포 형태를 검토한다.

Score Tools 자체 라이선스는 아직 확정되지 않았다. 루트 LICENSE와 package `license`를 정하기 전 공개 registry나 외부 공개 배포를 진행하지 않는다. React/lucide-react 등 third-party notices도 최종 제품 기준으로 재점검한다.

## 18. 다음 단계

1. 최소 React/Verovio fixture 저장소에서 tarball 설치 CI를 만든다.
2. 장기적으로 독립 workspace package로 옮길지 결정한다.
3. cross-staff Staff 추출의 시각 경고와 자동 beam 결과를 더 많은 실제 악보 fixture로 검증한다.
4. 안전한 경우에만 활성화할 `Compact to one staff` 고급 재기보를 별도 설계한다.
5. 대형 score render/raster의 Web Worker queue를 검토한다.
6. 운영 export policy와 서버 권한 검증을 구현한다.
7. recipe JSON Schema를 추가한다.
8. 필요하면 vector PDF backend를 검증한다.
9. 자체 라이선스와 third-party notice를 확정한다.

### Git 전달 전 필수 확인

1. `git status --short`로 `src/score-tools`, `ScoreToolsPanel`, CSS, package/config/example/verifier와 이 문서가 모두 추적 대상인지 확인한다.
2. 관련 변경을 검토해 commit하고 private remote에 push한다.
3. 별도 빈 폴더에서 clone한 뒤 `pnpm install --frozen-lockfile`, 집중 테스트, module/main build와 pack을 반복한다.
4. clean consumer fixture에 `.tgz`를 설치해 React/CSS/Verovio peer와 타입 검사를 확인한다.

## 19. 인수 완료 기준

새 개발자가 구두 설명 없이 clone/install/test/build/pack, tarball 설치, 자체 toolkitFactory 연결, React panel과 기존 viewer state 연결, headless snapshot/recipe/derived XML/sidecar 생성, 이미지 QA, 운영 policy 교체와 다음 schema 개발을 수행할 수 있으면 인수가 완료된 것이다.
