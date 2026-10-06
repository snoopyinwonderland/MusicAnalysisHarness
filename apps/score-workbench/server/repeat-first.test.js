import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {discoverRepeats,durationRestVariants} from './repeat-first.mjs';
const make=(pitch,offset=0,shift=0)=>pitch.map((p,i)=>({id:`n${offset+i}`,pitchMidi:p+shift,onset:offset+i,durationRatio:1}));
it('finds rhythmic recurrence with transposition and a weak melodic variation',()=>{
 const a=make([60,62,64,62,67,65]),b=make([60,62,65,62,67,65],10,12),notes=[...a,...b],before=JSON.stringify(notes);
 const r=discoverRepeats(notes,{windowLengths:[6]});
 expect(r.candidates.some(c=>c.left.startIndex===0&&c.right.startIndex===6)).toBe(true);expect(JSON.stringify(notes)).toBe(before);
});
it('does not treat matching rhythm alone as a melodic recurrence',()=>{
 const r=discoverRepeats([...make([60,62,64,62,67]),...make([60,80,40,90,30],10)],{windowLengths:[5]});
 expect(r.candidates.some(c=>c.left.startIndex===0&&c.right.startIndex===5)).toBe(false);
});
it('keeps ostinato candidates explicitly low information',()=>{
 const r=discoverRepeats(make(Array(10).fill(60)),{windowLengths:[5]});expect(r.candidates[0].lowInformation).toBe(true);
});
it('records duration/rest redistribution but not different onset intervals',()=>{
 const a=make([60,62]),b=make([72,74],10);b[0].durationRatio=.5;
 const pairs=[{leftIndex:0,rightIndex:0},{leftIndex:1,rightIndex:1}];
 expect(durationRestVariants(a,b,pairs)).toHaveLength(1);b[1].onset+=.5;expect(durationRestVariants(a,b,pairs)).toHaveLength(0);
});
it('reports budget exhaustion and invalid input',()=>{
 expect(discoverRepeats(make(Array(20).fill(60)),{maxSeedChecks:0}).status).toBe('partial');
 expect(()=>discoverRepeats([{id:'a',onset:0,durationRatio:0,pitchMidi:60}])).toThrow();
});
it('recovers ALWAYS WITH ME without Phrase boundary input',()=>{
 const w=JSON.parse(readFileSync('evaluation/case-assets/S-STRUCT-008/review-snapshot.json')).work;
 const r=discoverRepeats(w.notes);const c=r.candidates.find(c=>c.left.startIndex===0&&c.right.startIndex===30);
 expect(c).toBeDefined();expect(c.variants.some(v=>v.leftEventId.endsWith('-4')&&v.rightEventId.endsWith('-34'))).toBe(true);
});
