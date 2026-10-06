import {readFileSync} from 'node:fs';
import {describe,it,expect} from 'vitest';
import {parseQueryImport,formatCompactQuery} from '../src/music/queryImport';
import {withQueryCopy} from './evaluation-query-copy.mjs';
const batches=['memory-variation-50-v1','octave-combination-20-v1','short-query-90-v1','triple-meter-60-v1','eighth-meter-60-v1'];
describe('saved evaluation queries can be imported',()=>{
 for(const batch of batches)it(batch,()=>{
  const suite=JSON.parse(readFileSync('evaluation/reports/'+batch+'/suite.json'));
  const signature=q=>q.events.map(e=>[e.kind,e.pitchMidi,e.durationRatio]);
  for(const c of suite.cases){const q=parseQueryImport(JSON.stringify({schema:'musicanote-query',query:c.query}));expect(signature(q)).toEqual(signature(c.query));expect(q.meter).toBe(c.query.meter);expect(signature(parseQueryImport(formatCompactQuery(q),{meter:q.meter,mode:q.mode}))).toEqual(signature(q));}
 });
 it('copy augmentation is idempotent and escapes script-closing data',()=>{
  const suite={bases:[{baseId:'b',query:{events:[]}}],cases:[{caseId:'</script>',baseId:'b',query:{events:[]}}]};
  const h=withQueryCopy('<html></html>',suite);expect(withQueryCopy(h,suite)).toBe(h);expect(h.match(/<\/script>/g)).toHaveLength(1);
 });
});
