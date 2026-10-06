import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {analyzePhraseBoundaries,suppressShortArticulationBeforeArrival} from './phrase-boundaries.mjs';
it('preserves sustained endings after short articulation rests in FIND THE WAY',()=>{
 const {work}=JSON.parse(readFileSync('evaluation/case-assets/S-STRUCT-005/review-snapshot.json','utf8'));
 const result=analyzePhraseBoundaries(work.notes);
 expect(result.boundaries[31].supported).toBe(false);
 expect(result.boundaries[33].supported).toBe(true);
 expect(result.boundaries[37].supported).toBe(false);
 expect(result.boundaries[43].supported).toBe(false);
 expect(result.boundaries[46].supported).toBe(true);
 expect(result.boundaries[77].supported).toBe(false);
 expect(result.boundaries[79].supported).toBe(true);
 expect(work.notes[45].spelling).toBe('E4');
});

const fixture=()=>{
 const events=[{onset:0,duration:.25},{onset:.5,duration:.5},{onset:1,duration:1.25},{onset:3,duration:.5}].map(n=>({...n,end:n.onset+n.duration,attack:true,explicit:true,beatQuarters:1}));
 const boundaries=events.map((_,index)=>({index,strength:.8,continuity:0,cues:[]}));
 return {events,boundaries};
};
it('demotes short articulation before an independent sustained closure',()=>{
 const {events,boundaries}=fixture();
 expect(suppressShortArticulationBeforeArrival(events,boundaries)).toHaveLength(1);
 expect(boundaries[1].strength).toBeLessThan(.65);expect(boundaries[3].strength).toBe(.8);
});
it('does not demote when no sustained closure follows',()=>{
 const {events,boundaries}=fixture();events[2].duration=.25;events[2].end=1.25;
 expect(suppressShortArticulationBeforeArrival(events,boundaries)).toHaveLength(0);
});
it('preserves a substantial initial rest and explicit breath evidence',()=>{
 const {events,boundaries}=fixture();events[0].end=-.5;
 expect(suppressShortArticulationBeforeArrival(events,boundaries)).toHaveLength(0);
 const other=fixture();other.boundaries[1].cues.push({name:'notated-breath-symbol'});
 expect(suppressShortArticulationBeforeArrival(other.events,other.boundaries)).toHaveLength(0);
});
it('does not infer a gap from missing source timing',()=>{
 const {events,boundaries}=fixture();events[1].explicit=false;
 expect(suppressShortArticulationBeforeArrival(events,boundaries)).toHaveLength(0);
});
