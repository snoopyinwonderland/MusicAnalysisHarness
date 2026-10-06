import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {analyzePhraseBoundaries as analyze} from './phrase-boundaries.mjs';
const notes=id=>JSON.parse(readFileSync(`evaluation/case-assets/S-STRUCT-${id}/review-snapshot.json`)).work.notes;
it('merges short cell and following variation while retaining cell evidence',()=>{
 const n=notes('008'),a=analyze(n),off=analyze(n,{shortCell:false});
 expect(off.boundaries[230].supported).toBe(true);expect(a.boundaries[230].supported).toBe(false);
 expect(a.boundaries[226].supported).toBe(true);expect(a.boundaries[241].supported).toBe(true);
 expect(a.boundaries[230].primaryLevel).toBe('subphrase-cell');
 expect(a.boundaries[230].cues.some(c=>c.name==='short-cell-variation-continuity')).toBe(true);
});
it('abstains on different rhythm, contour, explicit breath, meter and stronger gap',()=>{
 for(const mutate of [n=>{n[231].durationRatio=.25},n=>{n[231].pitchMidi=40},n=>{n[229].breathSymbols=['caesura']},n=>{n[229].meterUnit=null},n=>{n[229].durationRatio=.25}]){
  const n=notes('008');mutate(n);
  expect(analyze(n).boundaries[230].cues.some(c=>c.name==='short-cell-variation-continuity')).toBe(false);
 }
});
it('preserves four other saved cases and generalizes beyond score identity',()=>{
 for(const id of ['004','005','006','007']){const n=notes(id);expect(analyze(n).boundaries.map(b=>b.supported)).toEqual(analyze(n,{shortCell:false}).boundaries.map(b=>b.supported));}
 const n=notes('008').map((x,i)=>({...x,id:`other-${i}`,pitchMidi:x.pitchMidi+5,measure:Number(x.measure)+80}));
 expect(analyze(n).boundaries[230].supported).toBe(false);
});
