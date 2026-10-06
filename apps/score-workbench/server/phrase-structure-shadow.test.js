import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {alignStructureTemplate} from '../src/music/structureTemplateAlignment.ts';

it('reproduces the saved case comparison without altering baseline boundaries',()=>{
 const root='evaluation/case-assets/S-STRUCT-006/';
 const baseline=JSON.parse(readFileSync(root+'phrase-structure-v1-baseline/baseline.json'));
 const snapshot=JSON.parse(readFileSync(root+'review-snapshot.json'));
 const before=JSON.stringify({baseline,snapshot});
 const notes=snapshot.work.notes;
 const range=s=>notes.slice(s.startIndex,s.endIndexExclusive);
 const combined=notes.slice(baseline.spans[3].startIndex,baseline.spans[4].endIndexExclusive);
 const results=baseline.spans.slice(0,3).map(s=>alignStructureTemplate(range(s),combined));
 expect(results.map(r=>r.prefix.alignedAttackCount)).toEqual([8,8,8]);
 expect(results.map(r=>r.terminal.bothEndpointsPaired)).toEqual([true,false,true]);
 expect(JSON.stringify({baseline,snapshot})).toBe(before);
});
