import {it,expect} from 'vitest';
import {compareMotifFamilies,motifFamilyDisplaySpans} from './motifDiscoveryComparison';
const notes=Array.from({length:8},(_,i)=>({id:'n'+i,onset:i,durationRatio:1,pitchMidi:60,spelling:'C4'}));
const spans=[{motifNumber:1,familyNumber:1,label:'Motif 1-1',startIndex:0,endIndex:3},{motifNumber:2,familyNumber:2,label:'Motif 2-1',startIndex:4,endIndex:7}] as any;
const work={workId:'w',streamId:'s',sourceId:'x',notes,motifDiscovery:{status:'ready',provenance:{workId:'w',streamId:'s',sourceId:'x'},eventBindings:notes,families:[{id:'M1',occurrences:[{start:0,end:4},{start:4,end:8}]}]}};
it('adds family hypotheses without altering legacy ranges, numbering or labels',()=>{
 const before=JSON.stringify(spans),result=compareMotifFamilies(work,spans);expect(result.error).toBe(null);expect(result.spans.map((s:any)=>s.linkedFamily)).toEqual([1,1]);expect(JSON.stringify(spans)).toBe(before);
 expect(motifFamilyDisplaySpans(result.spans,false)).toBe(result.spans);
 expect(motifFamilyDisplaySpans(result.spans,true)[1]).toMatchObject({label:'비교 F1 · Motif 2-1',motifNumber:2,familyNumber:2,startIndex:4,endIndex:7});
});
it('refuses stale stream/event/time/spelling snapshots',()=>{
 for(const changed of [{streamId:'other'},{notes:notes.map((n,i)=>i? n:{...n,onset:.5})},{notes:notes.map((n,i)=>i?n:{...n,spelling:'B#3'})}]){
  const result=compareMotifFamilies({...work,...changed},spans);expect(result.error).toBe('source-or-event-snapshot-mismatch');expect(result.spans).toBe(spans);
 }
});
it('falls back to unchanged spans on skip/error/absent discovery',()=>{
 for(const discovery of [undefined,{status:'skipped',skipped:'budget'},{status:'error',error:'bad'}])expect(compareMotifFamilies({...work,motifDiscovery:discovery},spans).spans).toBe(spans);
});
