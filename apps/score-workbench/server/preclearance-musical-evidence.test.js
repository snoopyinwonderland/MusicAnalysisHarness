import {it,expect} from 'vitest';
import {sourceAnchors,comparePassages,aggregatePhraseEvidence} from './preclearance-musical-evidence.mjs';
const ns=(pitches,offset=0)=>pitches.map((pitchMidi,i)=>({id:'n'+(i+offset),kind:'note',pitchMidi,onset:i+offset,durationRatio:1,beat:i%4+1}));
function snapshot(){const events=[...ns([60,62,65,64,67,65,62,60]),...ns([60,64,67,69,67,64,62,59],8)];return {snapshotId:'s',meter:'4/4',events,units:[0,8].map((start,i)=>({unitId:'p'+i,kind:'phrase',attackEventIds:events.slice(start,start+8).map(n=>n.id),endEventId:events[start+7].id}))}}
it('normalizes transposition and uniform tempo but retains direction and rhythm distinctions',()=>{
 const a=ns([60,62,65,64,67,65,62,60]),b=a.map(n=>({...n,pitchMidi:n.pitchMidi+12,onset:n.onset*2,durationRatio:2}));
 const same=comparePassages(a,b);expect(same.contour.score).toBe(100);expect(same.rhythm.score).toBe(100);expect(same.figures.score).toBe(100);
 const reverse=comparePassages(a,b.map(n=>({...n,pitchMidi:144-n.pitchMidi})));expect(reverse.contour.score).toBeLessThan(70);
});
it('keeps rest position as a distinct diagnostic rather than erasing it',()=>{
 const a=ns([60,62,65,64]),b=a.map(n=>({...n,onset:n.onset+(n.onset>=2?1:0)}));b.splice(2,0,{id:'r',kind:'rest',onset:2,pitchMidi:null,durationRatio:1});
 expect(comparePassages(a,b).rhythm.restPlacement).toBeLessThan(100);
});
it('requires multiple supports and does not choose anchors to fit the pair',()=>{
 const s=snapshot();expect(sourceAnchors(s).anchors).toHaveLength(0);
 s.events[0].durationRatio=2;const before=sourceAnchors(s);expect(before.anchors.map(n=>n.eventId)).toEqual(['n0']);
 comparePassages(s.events,ns([88,70,60]));expect(sourceAnchors(s)).toEqual(before);
 s.events[0].tieStop=true;expect(sourceAnchors(s).anchors).toHaveLength(0);
});
it('supports compound meter and leaves missing metric context unknown',()=>{
 const s=snapshot();s.meter='6/8';s.events[2].beat=2.5;s.events[2].durationRatio=3;
 expect(sourceAnchors(s).anchors.find(n=>n.eventId==='n2').metric).toBe(.65);
 delete s.events[2].beat;expect(sourceAnchors(s).anchors.some(n=>n.eventId==='n2')).toBe(false);
 expect(comparePassages(ns([60,62,64]),ns([70,72,74])).skeleton.score).toBe(null);
});
it('does not multiply one phrase by nested motifs, duplicates or editions',()=>{
 const s=snapshot(),m={queryIds:s.units[0].attackEventIds,similarity:90};
 const a=aggregatePhraseEvidence(s,[m]),b=aggregatePhraseEvidence(s,[m,m,{...m,queryIds:m.queryIds.slice(1,5)}]);
 expect(a.distinctPhraseFamilies).toBe(1);expect(a.reviewScore).toBe(90);expect(b).toEqual(a);
});
it('adds bounded support for a genuinely different second phrase and union coverage',()=>{
 const s=snapshot(),r=aggregatePhraseEvidence(s,s.units.map(u=>({queryIds:u.attackEventIds,similarity:90})));
 expect(r.distinctPhraseFamilies).toBe(2);expect(r.reviewScore).toBeGreaterThan(90);expect(r.reviewScore).toBeLessThan(92);expect(r.attackCoverage).toBe(1);
});
it('groups normalized repeated phrases as one family',()=>{
 const s=snapshot();for(let i=0;i<8;i++)s.events[8+i].pitchMidi=s.events[i].pitchMidi+5;
 const r=aggregatePhraseEvidence(s,s.units.map(u=>({queryIds:u.attackEventIds,similarity:90})));expect(r.distinctPhraseFamilies).toBe(1);expect(r.matchedPhraseOccurrences).toBe(2);expect(r.bonus).toBe(0);
});
