import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {analyzePhraseBoundaries} from './phrase-boundaries.mjs';
const notes=()=>JSON.parse(readFileSync('evaluation/case-assets/S-STRUCT-006/review-snapshot.json','utf8')).work.notes;
it('preserves recurrence across a long silence without merging phrases',()=>{
 const n=notes(),before=JSON.stringify(n),a=analyzePhraseBoundaries(n);
 expect(a.boundaries.find(b=>b.supported)?.index).toBe(13);
 expect(a.boundaries[9].supported).toBe(false);
 expect(a.boundaries[21].supported).toBe(false);
 expect(a.boundaries[29].supported).toBe(true);
 expect(a.boundaries[38].supported).toBe(false);
 expect(a.boundaries[42].supported).toBe(true);
 expect(a.boundaries[13].longRestBoundary.gapQuarters).toBe(6.5);
 expect(a.motifRelations.find(r=>r.previousIndex===0&&r.currentIndex===13)?.closeContinuation).toBe(false);
 expect(JSON.stringify(n)).toBe(before);
});
it('scales the silence protection with the metric beat',()=>{
 const n=notes().map(n=>({...n,onset:n.onset*2,durationRatio:n.durationRatio*2,meterUnit:2}));
 const a=analyzePhraseBoundaries(n);
 expect(a.boundaries.find(b=>b.supported)?.index).toBe(13);
 expect(a.boundaries[13].longRestBoundary.beatQuarters).toBe(2);
});
it('does not protect a small silence as a long rest',()=>{
 const n=notes().map((n,i)=>({...n,onset:n.onset-(i>=13?6:0)}));
 expect(analyzePhraseBoundaries(n).boundaries[13].longRestBoundary).toBeUndefined();
});
it('does not merge the interior breath without recurrence evidence',()=>{
 const n=notes().map((n,i)=>({...n,pitchMidi:i*i}));
 const a=analyzePhraseBoundaries(n);
 expect(a.boundaries[9].cues.some(c=>c.name==='interior-breath-before-repeated-restart')).toBe(false);
});
it('preserves an explicitly marked interior breath',()=>{
 const n=notes();n[8].breathSymbols=[{type:'caesura'}];
 expect(analyzePhraseBoundaries(n).boundaries[9].supported).toBe(true);
});
it('requires both sustained arrival and silence for the additional protection',()=>{
 const make=d=>[{kind:'note',pitchMidi:60,onset:0,durationRatio:d,meterCount:4,meterUnit:4},{kind:'note',pitchMidi:62,onset:d+2,durationRatio:.5,meterCount:4,meterUnit:4}];
 expect(analyzePhraseBoundaries(make(2)).boundaries[1].longRestBoundary).toBeDefined();
 expect(analyzePhraseBoundaries(make(.5)).boundaries[1].longRestBoundary).toBeUndefined();
});
