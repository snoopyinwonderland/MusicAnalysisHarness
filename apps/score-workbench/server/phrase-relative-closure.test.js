import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {analyzePhraseBoundaries,suppressWeakShortClosures} from './phrase-boundaries.mjs';
it('merges reviewed v1.11 phrase 8+9 and 15+16+17',()=>{
 const w=JSON.parse(readFileSync('evaluation/case-assets/S-STRUCT-005/review-snapshot.json','utf8')).work;
 const a=analyzePhraseBoundaries(w.notes);
 for(const i of [84,132,136])expect(a.boundaries[i].supported).toBe(false);
 for(const i of [79,92,160])expect(a.boundaries[i].supported).toBe(true);
 expect(a.boundaries[164].supported).toBe(true); // short ending, very long silence exception
});
const check=(unit,scale=1,breath=false)=>{
 const notes=Array.from({length:6},()=>({meterCount:4,meterUnit:unit,breathSymbols:breath?[{type:'caesura'}]:[]}));
 const events=notes.map((_,i)=>({onset:i*.5*scale,end:(i*.5+.25)*scale,duration:.25*scale,attack:true,explicit:true}));
 const b=events.map((_,i)=>({index:i,strength:i===5?.8:0,continuity:0,cues:[]}));
 return suppressWeakShortClosures(notes,events,b);
};
it('uses metric beat rather than the written sixteenth value alone',()=>{
 expect(check(4)).toHaveLength(1);expect(check(8)).toHaveLength(0);
});
it('preserves the decision under equivalent metric scaling',()=>{
 expect(check(4)).toHaveLength(1);expect(check(2,2)).toHaveLength(1);
});
it('abstains on unknown meter and respects explicit breath',()=>{
 expect(check(0)).toHaveLength(0);expect(check(4,1,true)).toHaveLength(0);
});
