import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const repositoryRoot = dirname(fileURLToPath(import.meta.url));
const fromRoot = (path: string) => resolve(repositoryRoot, path);

const isExternal = (id: string) =>
  id === 'react' ||
  id.startsWith('react/') ||
  id === 'react-dom' ||
  id.startsWith('react-dom/') ||
  id === 'lucide-react' ||
  id === 'verovio/esm' ||
  id === 'verovio/wasm';

export default defineConfig({
  plugins: [react()],
  build: {
    target: 'es2022',
    outDir: fromRoot('packages/verovio-score-tools/dist'),
    emptyOutDir: true,
    sourcemap: true,
    cssCodeSplit: false,
    lib: {
      entry: {
        core: fromRoot('src/score-tools/index.ts'),
        image: fromRoot('src/score-tools/image.ts'),
        verovio: fromRoot('src/score-tools/verovio.ts'),
        react: fromRoot('src/score-tools/react.ts'),
        style: fromRoot('src/score-tools/style.ts'),
      },
      formats: ['es'],
      cssFileName: 'score-tools',
    },
    rollupOptions: {
      external: isExternal,
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: assetInfo => assetInfo.name?.endsWith('.css') ? 'score-tools.css' : 'assets/[name]-[hash][extname]',
      },
    },
  },
});
