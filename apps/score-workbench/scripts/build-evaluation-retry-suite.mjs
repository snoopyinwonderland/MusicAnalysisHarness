import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const [suitePath, runPrefix, outputDir] = process.argv.slice(2);
if (!suitePath || !runPrefix || !outputDir) throw new Error('Usage: node scripts/build-evaluation-retry-suite.mjs <suite.json> <run-prefix> <output-dir>');
const suite = JSON.parse(readFileSync(suitePath, 'utf8'));
const runDirs = readdirSync('evaluation/runs').filter((name) => name.startsWith(runPrefix) && !name.includes('interrupted'));
const pending = suite.cases.filter((testCase) => {
  const runs = runDirs.flatMap((dir) => {
    const file = path.join('evaluation/runs', dir, `${testCase.caseId}.json`);
    return existsSync(file) ? [JSON.parse(readFileSync(file, 'utf8'))] : [];
  });
  return !runs.some((run) => run.status === 'completed');
});
const baseIds = new Set(pending.map((testCase) => testCase.baseId));
const retry = { ...suite, schema: `${suite.schema}/retry`, parentSuite: suitePath, retrySelection: `No completed run found across ${runDirs.join(', ')}`, bases: suite.bases.filter((base) => baseIds.has(base.baseId)), cases: pending };
mkdirSync(outputDir, { recursive: false });
writeFileSync(`${outputDir}/suite.json`, `${JSON.stringify(retry, null, 2)}\n`, { flag: 'wx' });
console.log(JSON.stringify({ runDirs, retryCases: pending.length, caseIds: pending.map((testCase) => testCase.caseId) }, null, 2));
