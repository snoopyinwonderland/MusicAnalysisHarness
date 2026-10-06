import {describe,it,expect} from 'vitest';
import {compareSegments} from './segment-comparison.mjs';
const notes=ps=>ps.map((p,i)=>({p,o:i,d:1}));
describe('segment diagnostics',()=>{
 it('keeps a zero fitted shift',()=>{
  const a=notes([60,64,62,67,65]);const r=compareSegments(a,a);
  expect(r.variants[0].fittedSemitoneOffset).toBe(0);expect(r.variants[0].normalizedTimePitchAgreement).toBe(100);
 });
 it('preserves transposition and uniform time scale',()=>{
  const a=notes([60,64,62,67,65]);const b=a.map(n=>({...n,p:n.p+7,o:n.o*2,d:2}));const r=compareSegments(a,b);
  expect(r.variants[0].intervalEdit).toBe(100);expect(r.durationRatioEdit).toBe(100);expect(r.onsetIntervalRatioEdit).toBe(100);
 });
 it('separates global inversion from original matching',()=>{
  const a=notes([60,64,62,67,65]),b=a.map(n=>({...n,p:130-n.p}));const r=compareSegments(a,b);
  expect(r.variants[1].intervalEdit).toBe(100);expect(r.variants[0].intervalEdit).toBeLessThan(100);expect(r.countsAsRetrievalSuccess).toBe(false);
 });
 it('retains silence as separate evidence',()=>{
  const a=notes([60,64,62,67,65]),b=a.map((n,i)=>({...n,o:n.o+(i>=2?1:0)}));const r=compareSegments(a,b);
  expect(r.normalizedTimeSoundRestAgreement).toBeLessThan(100);expect(r.onsetIntervalRatioEdit).toBeLessThan(100);
 });
});
