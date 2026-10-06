import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {discoverRepeatHierarchy,reviewHierarchyBoundaries} from './repeat-hierarchy.mjs';
const w=JSON.parse(readFileSync('evaluation/case-assets/S-STRUCT-009/review-snapshot.json')).work;
it('recovers complete repeated melody despite different existing cuts',()=>{
 const before=JSON.stringify(w.notes),d=discoverRepeatHierarchy(w.notes);
 expect(d.candidates.some(c=>c.left.startIndex===0&&c.left.endIndexExclusive===18&&c.right.startIndex===49&&c.right.endIndexExclusive===67)).toBe(true);
 const review=reviewHierarchyBoundaries(w.notes,w.phraseAnalysis.boundaries,d);
 expect(review.rows.some(r=>r.differences.some(d=>d.rightIndex===58&&d.partialFrameConflict))).toBe(true);
 expect(review.rows.every(r=>!r.autoApply)).toBe(true);expect(JSON.stringify(w.notes)).toBe(before);
 expect(d.containment.length).toBeGreaterThan(0);
},20000); // Offline 20k-alignment regression; shared-server load exceeds 5s.
it('does not equate identical rhythm with incompatible melody',()=>{
 const make=(pitch,offset,prefix)=>pitch.map((pitchMidi,i)=>({id:prefix+i,pitchMidi,onset:offset+i,durationRatio:i===7?2:1,meterCount:4,meterUnit:4}));
 const n=[...make([60,62,64,65,67,69,71,72],0,'a'),...make([72,69,74,66,76,64,78,62],12,'b')];
 expect(discoverRepeatHierarchy(n).candidates).toHaveLength(0);
});
it('reports budgets and rejects malformed attack input',()=>{
 expect(discoverRepeatHierarchy(w.notes,{maxSeedChecks:0}).status).toBe('partial');
 expect(discoverRepeatHierarchy(w.notes,{maxAlignments:0}).candidates).toHaveLength(0);
 expect(()=>discoverRepeatHierarchy([w.notes[0],w.notes[0]])).toThrow();
});
it('does not extend candidates across protected breath',()=>{
 const n=w.notes.map(n=>({...n}));n[57].breathSymbols=['caesura'];
 const d=discoverRepeatHierarchy(n,{maxAlignments:500});
 expect(d.candidates.every(c=>[c.left,c.right].every(r=>!(r.startIndex<58&&r.endIndexExclusive>58)))).toBe(true);
});
