import {it,expect} from 'vitest';
import {alignStructureTemplate} from './structureTemplateAlignment';
import type {CorpusNote} from '../types';
const make=(p:number[])=>p.map((pitchMidi,i)=>({id:`n${i}`,kind:'note',pitchMidi,onset:i,durationRatio:.5,metricStrength:.5} as CorpusNote));
it('supports transposed complete recurrence with source-linked alignment',()=>{
 const a=make([60,62,61,65]),b=make([65,67,66,70]),r=alignStructureTemplate(a,b);
 expect(r.status).toBe('compared');if(r.status!=='compared')return;
 expect(r.similarity).toBe(100);expect(r.terminal.bothEndpointsPaired).toBe(true);expect(r.alignmentRefs[0].leftEventId).toBe('n0');
});
it('reports partial coverage rather than claiming a complete phrase',()=>{
 const r=alignStructureTemplate(make([60,62,61,65,63,60]),make([60,62,61]));
 expect(r.status).toBe('compared');if(r.status==='compared')expect(r.coverage).toBeLessThan(100);
});
it('records rest differences independently without mutating source',()=>{
 const a=make([60,62,61,65]),b=make([60,62,61,65]);b[2].onset=2.25;const before=JSON.stringify(b),r=alignStructureTemplate(a,b);
 expect(JSON.stringify(b)).toBe(before);if(r.status==='compared')expect(r.restComparisons.some(x=>x.leftGapUnits!==x.rightGapUnits)).toBe(true);
});
it('abstains on invalid inputs and bounded work',()=>{
 expect(alignStructureTemplate([],[]).status).toBe('invalid-input');expect(alignStructureTemplate(make(Array(129).fill(60)),make([60])).status).toBe('budget-exceeded');
});
