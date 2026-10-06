import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {analyzePhraseBoundaries} from './phrase-boundaries.mjs';
const fixture=id=>JSON.parse(readFileSync(`evaluation/case-assets/S-STRUCT-${id}/review-snapshot.json`)).work.notes;
it('merges the duration/rest interior breath with rollback available',()=>{
 const notes=fixture('008'),before=JSON.stringify(notes),off=analyzePhraseBoundaries(notes,{repeatBreath:false}),on=analyzePhraseBoundaries(notes);
 expect(off.boundaries[35].supported).toBe(true);expect(on.boundaries[35].supported).toBe(false);
 expect(on.boundaries[30].supported).toBe(true);expect(on.boundaries[60].supported).toBe(true);
 expect(JSON.stringify(notes)).toBe(before);
});
it('protects explicit breathing and a gap beyond the short-breath allowance',()=>{
 const notes=fixture('008');notes[34].breathSymbols=['caesura'];
 expect(analyzePhraseBoundaries(notes).repeatedBreath.decisions.some(d=>d.boundaryIndex===35)).toBe(false);
 const changed=fixture('008');changed[34].durationRatio=.75;
 expect(analyzePhraseBoundaries(changed).repeatedBreath.decisions.some(d=>d.boundaryIndex===35)).toBe(false);
});
it('is independent of work identity, absolute pitch and printed measure numbers',()=>{
 const notes=fixture('008').map((n,i)=>({...n,id:`synthetic-${i}`,pitchMidi:n.pitchMidi+7,measure:Number(n.measure)+100}));
 expect(analyzePhraseBoundaries(notes).boundaries[35].supported).toBe(false);
});
it('preserves boundaries of the other saved development cases',()=>{
 for(const id of ['004','005','006','007']){
  const notes=fixture(id),off=analyzePhraseBoundaries(notes,{repeatBreath:false}),on=analyzePhraseBoundaries(notes);
  expect(on.boundaries.map(b=>b.supported),id).toEqual(off.boundaries.map(b=>b.supported));
 }
});
