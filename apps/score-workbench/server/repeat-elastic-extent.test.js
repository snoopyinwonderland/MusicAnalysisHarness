import {it,expect} from 'vitest';
import {reviewElasticExtents} from './repeat-elastic-extent.mjs';
import {compareRepeatBoundaries} from './repeat-boundary-review.mjs';
const make=(pitches,base,prefix)=>pitches.map((pitchMidi,k)=>({id:prefix+k,pitchMidi,onset:base+k,durationRatio:k===pitches.length-1?2:1,meterCount:4,meterUnit:4}));
function fixture(extra=false){
 const a=make([60,62,64,65,67,69,67],0,'a');
 const b=make(extra?[72,74,76,77,77,79,81,79]:[72,74,76,77,79,81,79],12,'b');
 const notes=[...a,...b,...make([60],30,'z')];
 return {notes,groups:[{anchor:{left:{startIndex:1,endIndexExclusive:7},right:{startIndex:8,endIndexExclusive:7+b.length}}}]};
}
it('preserves anchors while recovering corresponding preceding notes',()=>{
 const {notes,groups}=fixture(),before=JSON.stringify(notes),r=reviewElasticExtents(notes,groups);
 expect(r.reviews[0].proposals.some(p=>p.left.startIndex===0&&p.right.startIndex===7)).toBe(true);
 expect(JSON.stringify(notes)).toBe(before);
});
it('maps unequal attack counts with paired arrivals',()=>{
 const {notes,groups}=fixture(true),r=reviewElasticExtents(notes,groups);
 expect(r.reviews[0].proposals.some(p=>p.attackCountDifference===1&&p.left.endIndexExclusive===7&&p.right.endIndexExclusive===15)).toBe(true);
});
it('does not attach an unrelated preceding pitch',()=>{
 const {notes,groups}=fixture();notes[7].pitchMidi=90;
 const r=reviewElasticExtents(notes,groups);
 expect(r.reviews[0].proposals.some(p=>p.preparationCounts.some(Boolean))).toBe(false);
});
it('protects internal breathing and abstains across unknown meter',()=>{
 const {notes,groups}=fixture();notes[3].breathSymbols=['caesura'];
 expect(reviewElasticExtents(notes,groups).reviews[0].proposals).toHaveLength(0);
 notes[3].breathSymbols=[];notes[3].meterCount=null;
 expect(reviewElasticExtents(notes,groups).reviews[0].proposals).toHaveLength(0);
});
it('reports budget exhaustion without pretending a full search',()=>{
 const {notes,groups}=fixture();expect(reviewElasticExtents(notes,groups,{maxAlignments:0}).status).toBe('partial');
 expect(()=>reviewElasticExtents(notes,groups,{lookback:500})).toThrow();
});
it('rejects a preceding note with incompatible duration despite a matching core',()=>{
 const {notes,groups}=fixture();notes[7].durationRatio=.125;
 const r=reviewElasticExtents(notes,groups);
 expect(r.reviews[0].proposals.some(p=>p.preparationCounts.some(Boolean))).toBe(false);
});
it('abstains at a meter change instead of converting the rest with one meter',()=>{
 const {notes,groups}=fixture();notes[6].meterCount=3;
 expect(reviewElasticExtents(notes,groups).reviews[0].proposals).toHaveLength(0);
});
it('shares small budgets across all eligible groups before a second alignment',()=>{
 const {notes,groups}=fixture();
 const r=reviewElasticExtents(notes,[groups[0],groups[0],groups[0]],{maxAlignments:3});
 expect(r.reviews.map(g=>g.alignments)).toEqual([1,1,1]);
 expect(r.alignments).toBe(3);expect(r.status).toBe('partial');
 expect(reviewElasticExtents(notes,[groups[0],groups[0]],{maxAlignments:0}).reviews).toHaveLength(2);
});
it('reports mapped boundary differences without changing the baseline',()=>{
 const {notes,groups}=fixture(),review=reviewElasticExtents(notes,groups);
 const boundaries=[{index:10,supported:true}],before=JSON.stringify(boundaries);
 const r=compareRepeatBoundaries(notes,boundaries,review);
 expect(r.rows.some(r=>r.correspondingBoundaryDifferences.length>0)).toBe(true);
 expect(r.rows.every(r=>r.autoApply===false&&r.decision==='cannot_judge')).toBe(true);
 expect(JSON.stringify(boundaries)).toBe(before);
 const same=compareRepeatBoundaries(notes,[{index:3,supported:true},...boundaries],review);
 expect(same.rows.every(r=>r.correspondingBoundaryDifferences.length===0)).toBe(true);
});
