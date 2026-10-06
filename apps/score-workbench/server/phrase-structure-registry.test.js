import {it,expect} from 'vitest';
import {structureRegistry} from './phrase-structure-registry.mjs';
const notes=Array.from({length:12},(_,i)=>({id:`n${i}`,pitchMidi:60+i%4,onset:i,durationRatio:1}));
const spans=Array.from({length:4},(_,i)=>({startIndex:i*3,endIndexExclusive:i*3+3}));
it('compares earlier and later nonoverlapping frozen references without changing input',()=>{
 const before=JSON.stringify({notes,spans}),r=structureRegistry(notes,spans);
 expect(r.status).toBe('complete');expect(r.proposals[0].candidates.every(c=>c.direction==='later')).toBe(true);
 expect(r.proposals[2].candidates.every(c=>c.direction==='earlier')).toBe(true);
 expect(r.registry).toHaveLength(4);expect(r.proposals.every(p=>p.decision==='cannot_judge')).toBe(true);
 expect(JSON.stringify({notes,spans})).toBe(before);
});
it('records partial output instead of pretending all pairs were searched',()=>{
 const r=structureRegistry(notes,spans,{maxComparisons:3});
 expect(r.status).toBe('partial');expect(r.comparisons).toBe(3);expect(r.unvisitedPairs).toBe(2);
});
it('rejects overlapping baseline references',()=>{
 expect(()=>structureRegistry(notes,[{startIndex:0,endIndexExclusive:5},{startIndex:4,endIndexExclusive:8}])).toThrow();
});
it('reports endpoint/coverage gaps rather than approving high partial similarity',()=>{
 const r=structureRegistry(notes,spans);
 expect(r.proposals.flatMap(p=>p.candidates).some(c=>c.missingEvidence.includes('incomplete-coverage-requires-review'))).toBe(true);
 expect(r.proposals.every(p=>p.decision==='cannot_judge')).toBe(true);
});
