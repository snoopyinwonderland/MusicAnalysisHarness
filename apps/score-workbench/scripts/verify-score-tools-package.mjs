import { access, readFile, stat } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const packageRoot = resolve(repositoryRoot, 'packages/verovio-score-tools');
const distRoot = resolve(packageRoot, 'dist');

const requiredFiles = [
  'core.js',
  'image.js',
  'verovio.js',
  'react.js',
  'score-tools.css',
  'types/score-tools/index.d.ts',
  'types/score-tools/image.d.ts',
  'types/score-tools/verovio.d.ts',
  'types/score-tools/react.d.ts',
  'types/components/ScoreToolsPanel.d.ts',
];

const expectedExports = {
  core: [
    'createScoreSnapshot',
    'createScoreToolsEngine',
    'defaultExcerptRecipe',
    'deriveExcerptScore',
    'deriveSelectedPartsScore',
    'transposeRecipe',
  ],
  image: ['buildJpegPdf', 'pdfFromSvgPages', 'rasterizeSvg'],
  verovio: [
    'createVerovioRenderer',
    'renderDerivedScoreToSvg',
    'renderDerivedScoreToSvgWithDependencies',
    'sanitizeVerovioSvg',
  ],
};

const assertFile = async relativePath => {
  const absolutePath = resolve(distRoot, relativePath);
  await access(absolutePath);
  const info = await stat(absolutePath);
  if (!info.isFile() || info.size === 0) throw new Error(`Missing or empty build artifact: ${relativePath}`);
};

const importEntry = name => import(`${pathToFileURL(resolve(distRoot, `${name}.js`)).href}?verify=${Date.now()}`);

try {
  await Promise.all(requiredFiles.map(assertFile));

  const reactDeclaration = await readFile(resolve(distRoot, 'types/score-tools/react.d.ts'), 'utf8');
  if (/score-tools\.css/.test(reactDeclaration)) {
    throw new Error('React declaration must not contain a relative CSS side-effect import. Consumers import style.css explicitly.');
  }

  for (const [entry, exports] of Object.entries(expectedExports)) {
    const module = await importEntry(entry);
    for (const exportName of exports) {
      if (!(exportName in module)) throw new Error(`${entry}.js does not export ${exportName}`);
    }
  }

  console.log(`Score Tools package verified: ${requiredFiles.length} dist artifacts and ${Object.keys(expectedExports).length} executable entry points.`);
  console.log('React entry was checked as a build artifact only; no DOM or CSS loader was invoked in Node.');
} catch (error) {
  console.error('Score Tools package verification failed.');
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
}
