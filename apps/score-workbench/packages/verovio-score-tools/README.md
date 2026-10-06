# @musicanote/verovio-score-tools

Portable Score Tools `0.2.1` for a browser-based MusicXML/Verovio viewer. The package keeps the source MusicXML immutable and derives transposed views, Part/Staff/Voice-filtered scores, measure excerpts, SVG previews, and SVG/PNG/JPG/PDF exports from explicit recipes.

This repository-local package is intentionally `private` while its integration API is being stabilized.

## Build

From the MusicSearch repository root:

```sh
pnpm exec vite build --config vite.score-tools.config.ts
pnpm exec tsc -p tsconfig.score-tools.json
```

The ESM bundles, CSS, source maps, and declarations are written to `packages/verovio-score-tools/dist`.

## Verification

```sh
pnpm test:score-tools
pnpm build:score-tools
pnpm build
```

The 2026-09-27 baseline passes 34/34 focused tests, the portable-module build, and the full MusicSearch build. The focused suite includes real MusicXML Staff selection, cross-staff Voice retention, cross-staff chord-head promotion, conservative missing-Voice handling, empty-selection/full-score behavior, effective multi-Staff attributes, source-map renumbering, recipe validation, and snapshot migration.

## Entry points

```ts
import {
  createScoreSnapshot,
  deriveExcerptScore,
  deriveSelectedPartsScore,
  defaultExcerptRecipe,
  applyScoreViewSelections,
  filterMusicXmlSelections,
} from '@musicanote/verovio-score-tools';

import { rasterizeSvg, pdfFromSvgPages } from '@musicanote/verovio-score-tools/image';
import { renderDerivedScoreToSvg } from '@musicanote/verovio-score-tools/verovio';
```

The core entry has no React, image-export, or Verovio runtime import. Add the `image` and `verovio` entries only when the host needs those capabilities. The React UI remains isolated in the `react` entry. If `createScoreToolsEngine()` is used for rendering, inject a renderer created from the optional Verovio entry:

```ts
import { createScoreToolsEngine } from '@musicanote/verovio-score-tools';
import { createVerovioRenderer } from '@musicanote/verovio-score-tools/verovio';

const renderDerivedScore = createVerovioRenderer({
  createToolkit: async () => hostVerovioToolkitFactory(),
  normalizeDocument: document => { hostNormalizeMusicXml?.(document); },
});
const scoreTools = createScoreToolsEngine({ renderDerivedScore });
```

Verovio 6.3.0 does not publish TypeScript declarations for its ESM/WASM subpaths. A TypeScript host that imports them directly should add this ambient declaration (for example `src/verovio-peer.d.ts`):

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

## Headless transformation

```ts
import {
  createScoreSnapshot,
  defaultExcerptRecipe,
  deriveExcerptScore,
  transposeRecipe,
} from '@musicanote/verovio-score-tools';

const snapshot = await createScoreSnapshot(musicXml, 'catalog/work-123');
const recipe = defaultExcerptRecipe(snapshot, 5, 8);
recipe.view.transpose = transposeRecipe('2');
recipe.selections = [{ partId: snapshot.parts[0].id, scope: 'whole_part' }];

const derived = await deriveExcerptScore(musicXml, snapshot, recipe);
// derived.xml is a new document; musicXml is unchanged.
```

Recipes contain stable source hashes and measure/part references. Persist the recipe and source-map sidecar when an export must be reproducible.

`ViewRecipe 1.1.0` and `ExcerptRecipe 1.4.0` accept one selection scope per Part:

```ts
import { filterMusicXmlSelections, type PartSelection } from '@musicanote/verovio-score-tools';

const selections: PartSelection[] = [
  { partId: 'P1', scope: 'staves', staffIds: ['1'] },
  { partId: 'P2', scope: 'voices', voiceIds: ['2'] },
  { partId: 'P3', scope: 'whole_part' },
];

const filteredXml = await filterMusicXmlSelections(musicXml, selections, 'catalog/work-123');
```

Passing `[]` to `filterMusicXmlSelections`, `engine.filterSelections`, or the controlled React `viewSelections` state means the unfiltered full score. A recipe persisted for `deriveExcerptScore` or `deriveSelectedPartsScore` remains explicit and must contain at least one whole-Part, Staff, or Voice selection.

Staff and Voice are parallel scopes: a Voice is not nested under a Staff. Voice extraction keeps every source Staff required by that Voice. Staff extraction can omit notes from a cross-staff Voice and reports that fact in `DerivedScore.warnings`. The transform preserves the MusicXML cursor with `backup`/`forward`, validates pitch/onset/duration/voice after reparse, promotes a retained cross-staff chord member when necessary, and conservatively removes notation that would become incomplete at a selection boundary.

Legacy `ViewRecipe 1.0.0` and `ExcerptRecipe 1.3.0` whole-Part recipes remain readable. Call `migrateViewRecipe` or `migrateExcerptRecipe` before adding scoped selections. A legacy `ScoreSnapshot 1.0.0` must be rebuilt with `migrateScoreSnapshot(snapshot, sourceXml)` before a Staff/Voice scope is used; the migrator verifies the source hash and reparses the authoritative XML instead of guessing missing Voice semantics. `score-timewise` and compacting a cross-staff Voice onto one newly engraved Staff are not supported in 0.2.1.

## React panel

Install the peer dependencies in the host application, then import the React entry and stylesheet:

```tsx
import { ScoreToolsPanel } from '@musicanote/verovio-score-tools/react';
import type { PartSelection } from '@musicanote/verovio-score-tools';
import '@musicanote/verovio-score-tools/style.css';

const [selections, setSelections] = useState<PartSelection[]>([]);

<ScoreToolsPanel
  open={open}
  onClose={() => setOpen(false)}
  xml={musicXml}
  sourceId="catalog/work-123"
  revisionKey={revision}
  title="Example score"
  initialStart={1}
  initialEnd={4}
  transpose={transpose}
  onTransposeChange={setTranspose}
  viewPartIds={partIds}
  onViewPartIdsChange={setPartIds}
  viewSelections={selections}
  onViewSelectionsChange={setSelections}
/>
```

The React entry intentionally does not import CSS for side effects. Import `style.css` explicitly once in the host so generated TypeScript declarations remain portable.

The host owns the open state, current transpose, score-content selections, source identity, and revision key. The same `viewSelections` drive the detailed score view, measure-image excerpt, and selected MusicXML export. `viewPartIds` remains as a backward-compatible whole-Part bridge; new integrations should persist `viewSelections` as the authoritative state.

For production, provide an `exportPolicy` implementation. The built-in default is the test-open policy used by the development viewer.

## Browser requirements

- Modern evergreen browser with ES2022 modules
- `DOMParser`, `XMLSerializer`, Web Crypto (`crypto.subtle`), `Blob`, and object URLs
- Canvas and `Image` for PNG/JPG/PDF export
- A bundler that can resolve `verovio/esm` and `verovio/wasm`
- React 18 or later for the optional React entry

Server-side transformation is possible only with DOM and Web Crypto-compatible adapters. Raster/PDF export is browser-oriented because it uses Canvas.
