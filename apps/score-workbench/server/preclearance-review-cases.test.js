import {it,expect} from 'vitest';
import {patternClass,buildReviewCases} from './preclearance-review-cases.mjs';
const notes=p=>p.map((pitchMidi,i)=>({id:'e'+i,kind:'note',pitchMidi,onset:i,durationRatio:1,measureOrdinal:1,beat:i+1}));
it('separates four automatic shape hypotheses',()=>{
 expect(patternClass(notes([60,60,60,60,60,62,60,64]))).toBe('repeated-note');
 expect(patternClass(notes([60,62,64,65,67,69,71,72]))).toBe('stepwise');
 expect(patternClass(notes([60,64,67,72,67,64,60,64]))).toBe('arpeggio-like');
 expect(patternClass(notes([60,72,69,65,64,66,70,60]))).toBe('mixed-leaps');
});
it('retains source context and unreviewed status without claiming a motif',()=>{
 const s={snapshotId:'s',identity:{sourceId:'a',workId:'w',streamId:'p'},meter:'4/4',events:notes([60,62,64,65,67,69,71,72])};
 const suite=buildReviewCases([s]);expect(suite.cases).toHaveLength(1);expect(suite.cases[0].context).toEqual(s.events);expect(suite.cases[0].humanReview.status).toBe('unreviewed');expect(suite.counts['arpeggio-like']).toBe(0);
});
it('does not fill a category with editions of the same diversity identity',()=>{
 const s={snapshotId:'s',diversityKey:'composition-a',identity:{sourceId:'a',workId:'w',streamId:'p'},meter:'4/4',events:notes([60,62,64,65,67,69,71,72])};
 const t={...s,snapshotId:'t',identity:{...s.identity,sourceId:'b'}};
 expect(buildReviewCases([s,t]).counts.stepwise).toBe(1);
});
