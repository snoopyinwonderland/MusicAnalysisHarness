import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const [suitePath, outputRoot, countRaw = '3'] = process.argv.slice(2);
if (!suitePath || !outputRoot) throw new Error('Usage: node scripts/shard-evaluation-suite.mjs <suite.json> <output-root> [count]');
const count = Number(countRaw);
if (!Number.isInteger(count) || count < 2) throw new Error('Shard count must be an integer >= 2');
const suite = JSON.parse(readFileSync(suitePath, 'utf8'));
const shards = Array.from({ length: count }, () => []);
suite.cases.forEach((testCase, index) => shards[index % count].push(testCase));
mkdirSync(outputRoot, { recursive: true });
for (let index = 0; index < count; index += 1) {
  const shardDir = `${outputRoot}/shard-${index + 1}`;
  mkdirSync(shardDir, { recursive: false });
  const caseBaseIds = new Set(shards[index].map((testCase) => testCase.baseId));
  const shard = {
    ...suite,
    schema: `${suite.schema}/shard`,
    parentSuite: suitePath,
    shard: { index: index + 1, count },
    bases: suite.bases.filter((base) => caseBaseIds.has(base.baseId)),
    cases: shards[index],
  };
  writeFileSync(`${shardDir}/suite.json`, `${JSON.stringify(shard, null, 2)}\n`, { flag: 'wx' });
}
console.log(JSON.stringify(shards.map((cases, index) => ({ shard: index + 1, cases: cases.length })), null, 2));
