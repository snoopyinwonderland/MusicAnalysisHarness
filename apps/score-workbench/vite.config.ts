import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
// @ts-expect-error Runtime-only Node middleware has no browser declaration.
import { catalogSearchPlugin, corpusStatsApiPlugin, searchApiPlugin, workApiPlugin, youtubeBackfillPlugin } from './server/search-api.mjs';
// @ts-expect-error Runtime-only Node middleware has no browser declaration.
import { phraseReviewApiPlugin } from './server/phrase-review.mjs';
// @ts-expect-error Runtime-only Node middleware.
import {structurePreviewApiPlugin} from './server/structure-preview-api.mjs';
// @ts-expect-error Runtime-only Node middleware.
import {harmonyOverlayApiPlugin} from './server/harmony-overlay-api.mjs';
export default defineConfig({
  plugins: [react(), searchApiPlugin(), corpusStatsApiPlugin(), workApiPlugin(), harmonyOverlayApiPlugin(), phraseReviewApiPlugin(), structurePreviewApiPlugin(), youtubeBackfillPlugin(), catalogSearchPlugin()],
  // SQLite, MusicXML sources, collection caches, and evaluation artifacts are read
  // directly by the API. Watching their tens of thousands of files can stall the
  // Vite event loop without contributing to HMR.
  server: { watch: { ignored: ['**/data/**', '**/evaluation/**', '**/docs/**'] } },
  test: { environment: 'node' },
});
