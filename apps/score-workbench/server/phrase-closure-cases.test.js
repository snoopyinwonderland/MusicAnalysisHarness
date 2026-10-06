import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {analyzePhraseBoundaries} from './phrase-boundaries.mjs';
import {notationStructureEvidence} from './notation-structure-evidence.mjs';
import {sourceClosure} from './phrase-source-closure.mjs';
import {sourceMeterTimeline,reviewClosureInMeter} from './phrase-meter-review.mjs';
for(const [id,expectedBoundaries,expectedProtected] of [['004',33,8],['005',29,11],['006',41,15]]){
 it(`reproduces source-linked observations for S-STRUCT-${id} without changing input`,()=>{
  const root=`evaluation/case-assets/S-STRUCT-${id}/`,xml=readFileSync(root+'context.musicxml','utf8'),snapshot=JSON.parse(readFileSync(root+'review-snapshot.json'));
  const notes=snapshot.work.notes,before=JSON.stringify(notes),e=notationStructureEvidence(xml,snapshot.work.streamId,notes);
  expect(e.sourceHash).toBe(snapshot.xmlSha256);expect(e.mappings.every(m=>m.status==='mapped')).toBe(true);
  const timeline=sourceMeterTimeline(xml,snapshot.work.streamId.split(':')[0]);
  const checks=analyzePhraseBoundaries(notes).boundaries.filter(b=>b.supported&&b.index>0).map(b=>reviewClosureInMeter(sourceClosure(e,notes,b.index-1),e,timeline));
  expect(checks).toHaveLength(expectedBoundaries);expect(checks.every(c=>c.status==='normalized')).toBe(true);
  expect(checks.filter(c=>c.decision==='protect-boundary')).toHaveLength(expectedProtected);
  expect(JSON.stringify(notes)).toBe(before);
 });
}
