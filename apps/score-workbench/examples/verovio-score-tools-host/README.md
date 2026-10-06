# Verovio Score Tools host example

`ScoreToolsBridge.tsx` shows the smallest React boundary needed to place Score Tools over an existing Verovio viewer. It imports only published package entry points; it does not reach into the MusicSearch source tree.

The host owns:

- panel open/closed state;
- current semitone transpose value;
- selected part ids;
- immutable source XML and stable `sourceId`;
- `revisionKey`, which must change whenever the source XML revision changes;
- stable start/end measure ids, with displayed measure numbers as fallbacks;
- export authorization.

The existing viewer receives `transpose` and `viewPartIds` immediately. Selecting no parts or every part means the full score, matching the panel contract.

## Build the package

Run from the MusicSearch repository root:

```sh
pnpm exec vite build --config vite.score-tools.config.ts
pnpm exec tsc -p tsconfig.score-tools.json
node scripts/verify-score-tools-package.mjs
```

## Install from a workspace or local checkout

Build first, then add the package directory from the consuming application:

```sh
pnpm add @musicanote/verovio-score-tools@file:../MusicSearch/packages/verovio-score-tools
```

Adjust the relative path for the host repository. A pnpm workspace can instead list `packages/*` in `pnpm-workspace.yaml` and depend on:

```json
{
  "dependencies": {
    "@musicanote/verovio-score-tools": "workspace:*"
  }
}
```

## Install from a tarball

```sh
pnpm --dir packages/verovio-score-tools pack --pack-destination ../../artifacts
pnpm add ./artifacts/musicanote-verovio-score-tools-0.1.0.tgz
```

The package is private during API stabilization, but local directory and tarball installation remain available for development and internal deployment.

## Peer dependencies

Install compatible peers in the host application:

```sh
pnpm add react@^19 react-dom@^19 lucide-react@^1.34 verovio@6.3.0
```

The supported ranges are React/React DOM 18–19 and Verovio 6.3.x; the command above reproduces the currently tested major versions. Existing React 18 hosts do not need to upgrade. The host bundler must support ESM, `verovio/esm`, and `verovio/wasm`.

Verovio 6.3.0 does not publish TypeScript declarations for those two subpaths. Copy the ambient declaration from `packages/verovio-score-tools/README.md` into a host `.d.ts` file when the host imports them directly.

## Use the bridge

```tsx
import { ScoreToolsBridge } from './ScoreToolsBridge';
import { ExistingScoreViewer } from './ExistingScoreViewer';

<ScoreToolsBridge
  Viewer={ExistingScoreViewer}
  xml={musicXml}
  sourceId="catalog/work-123"
  revisionKey="work-123:revision-7"
  title="Example score"
  initialStart={12}
  initialEnd={16}
  initialStartMeasureId="measure:12"
  initialEndMeasureId="measure:16"
  renderScoreToSvg={hostRenderer}
/>
```

Create `hostRenderer` with `createVerovioRenderer({ createToolkit, normalizeDocument })`; returning a fresh toolkit for every render prevents state from leaking between scores. Omitting the prop uses the package's browser adapter.

The bridge imports the package stylesheet explicitly:

```ts
import '@musicanote/verovio-score-tools/style.css';
```

Keep that import once in the host application even if the panel is lazy-loaded. Replace `createHostExportPolicy(true)` with the host's real permission decision before production use.

`ScoreToolsPanel` is controlled: it never owns the host viewer or overwrites source MusicXML. Its callbacks only request view-state changes, and all export transformations produce derived documents.
