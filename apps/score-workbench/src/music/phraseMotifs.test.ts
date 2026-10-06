import {it,expect} from 'vitest';
import type {CorpusNote} from '../types';
import {phraseMotifs} from './phraseMotifs';
const make=(pitches:number[],durations=pitches.map(()=>.5),offset=0)=>{let t=offset;return pitches.map((p,i)=>{const n={id:String(i),kind:'note',pitchMidi:p,durationRatio:durations[i],onset:t,measure:1,beat:1,metricStrength:.5} as CorpusNote;t+=durations[i];return n})};
it('keeps a complete phrase when no internal evidence exists',()=>{
 const n=make([60,61,63,66,68]);const s=phraseMotifs(n,[{startIndex:0,endIndex:4}]);
 expect(s).toHaveLength(1);expect(s[0].analysisScope).toBe('phrase-whole-unresolved');expect(s[0].endIndex).toBe(4);
});
it('recognizes a repeated complete gesture inside one phrase',()=>{
 const n=make([60,62,61,65,60,62,61,65],[.5,.5,.5,2,.5,.5,.5,2]);
 const s=phraseMotifs(n,[{startIndex:0,endIndex:7}]);
 expect(s.map(x=>[x.startIndex,x.endIndex])).toEqual([[0,3],[4,7]]);
 expect(s[0].familyNumber).toBe(s[1].familyNumber);expect(s[1].recurrenceEvidence?.startIndex).toBe(0);
});
it('does not split merely because one note is long',()=>{
 const n=make([60,62,61,65,70,70,70,70],[.5,.5,.5,2,.5,.5,.5,2]);
 expect(phraseMotifs(n,[{startIndex:0,endIndex:7}])).toHaveLength(1);
});
it('recognizes distant transposed rhythm variants beyond 64 attacks',()=>{
 const a=make([60,62,61,65],[.5,.5,.5,2]),middle=make(Array(80).fill(40),undefined,4),b=make([65,67,66,70],[.5,.5,.5,3],50);
 const s=phraseMotifs([...a,...middle,...b],[{startIndex:0,endIndex:3},{startIndex:4,endIndex:83},{startIndex:84,endIndex:87}]);
 expect(s[0].familyNumber).toBe(s.at(-1)?.familyNumber);expect(s.at(-1)?.variantIndex).toBeGreaterThan(0);
});
it('retains short and repeated-note phrases instead of filtering their identity',()=>{
 const n=make([60,60,60,60,65,65,65,65]);const s=phraseMotifs(n,[{startIndex:0,endIndex:3},{startIndex:4,endIndex:7}]);
 expect(s).toHaveLength(2);expect(s[0].familyNumber).toBe(s[1].familyNumber);
 expect(phraseMotifs(n.slice(0,2),[{startIndex:0,endIndex:1}])).toHaveLength(1);
});
it('preserves source notes and never crosses supplied phrase bounds',()=>{
 const n=make([60,61,62,63,64,65,66,67]);const before=JSON.stringify(n),s=phraseMotifs(n,[{startIndex:0,endIndex:3},{startIndex:4,endIndex:7}]);
 expect(JSON.stringify(n)).toBe(before);expect(s.map(x=>[x.startIndex,x.endIndex])).toEqual([[0,3],[4,7]]);
});
