import {it,expect} from 'vitest';
import {pillarVariationEvidence} from './pillarVariation';
import type {CorpusNote} from '../types';
function sequence(p:number[],d:number[],start=0){let onset=start;return p.map((pitchMidi,i)=>{const n={id:`${start}-${i}`,pitchMidi,durationRatio:d[i],onset};onset+=d[i];return n;}) as CorpusNote[];}
it('aligns inserted neighbors and transposed anchors without promoting the ornament',()=>{
 const a=sequence([60,64,62,67],[1,1,1,1]);
 const b=sequence([65,66,65,69,67,72],[.25,.25,.5,1,1,1],8);
 const n=[...a,...b],before=JSON.stringify(n),ev=pillarVariationEvidence(n);
 expect(ev.get(0)?.some(e=>e.otherNoteId==='8-0')).toBe(true);
 expect(ev.get(1)?.some(e=>e.otherNoteId==='8-3')).toBe(true);
 expect(ev.get(0)?.some(e=>e.otherNoteId==='8-1')).toBe(false);
 expect(JSON.stringify(n)).toBe(before);
});
it('allows a weak pitch variation but does not call that pitch a shared anchor',()=>{
 const n=[...sequence([60,64,62,67],[1,1,1,1]),...sequence([65,70,67,72],[2,2,2,2],8)];
 const ev=pillarVariationEvidence(n);expect(ev.get(0)?.[0].timeScale).toBe(2);
 expect(ev.get(1)).toBeUndefined();expect(ev.get(2)).toBeDefined();
});
it('rejects rhythm-only matches, low-information runs and gaps',()=>{
 expect(pillarVariationEvidence([...sequence([60,64,62,67],[1,1,1,1]),...sequence([60,67,65,61],[1,1,1,1],8)]).size).toBe(0);
 expect(pillarVariationEvidence(sequence([60,60,60,60,60,60,60,60],[1,1,1,1,1,1,1,1])).size).toBe(0);
 const n=[...sequence([60,64,62,67],[1,1,1,1]),...sequence([60,64,62,67],[1,1,1,1],8)];n[5].onset!+=.5;
 expect(pillarVariationEvidence(n).size).toBe(0);
});
