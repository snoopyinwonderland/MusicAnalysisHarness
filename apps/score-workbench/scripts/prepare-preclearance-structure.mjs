import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { analyzeStructureSnapshot, structureHash, structureRefreshPlan, structureSearchQueries } from '../server/structure-analysis-adapter.mjs';

export function prepareStructure(input, previous = null) {
  const snapshot = analyzeStructureSnapshot(input);
  return { snapshot, refresh: structureRefreshPlan(previous, snapshot), tasks: structureSearchQueries(snapshot) };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [inputPath, outputPath, previousPath] = process.argv.slice(2);
  if (!inputPath || !outputPath) throw new Error('Usage: node scripts/prepare-preclearance-structure.mjs events.json NEW-output.json [previous-output.json]');
  const bytes = readFileSync(inputPath), input = JSON.parse(bytes.toString('utf8'));
  // Legacy case assets do not carry an original-file hash: label this accurately.
  input.sourceHash ??= `event-snapshot:${structureHash(input)}`;
  const previous = previousPath ? JSON.parse(readFileSync(previousPath, 'utf8')).snapshot : null;
  const result = prepareStructure(input, previous);
  mkdirSync(dirname(resolve(outputPath)), { recursive: true });
  writeFileSync(outputPath, JSON.stringify(result, null, 2), { flag: 'wx' });
  console.log(JSON.stringify({ snapshotId: result.snapshot.snapshotId, units: result.snapshot.units.length, tasks: result.tasks.length, refresh: result.refresh.status }));
}
