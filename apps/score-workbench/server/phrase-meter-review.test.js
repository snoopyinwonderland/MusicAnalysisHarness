import {it,expect} from 'vitest';
import {sourceMeterTimeline,reviewClosureInMeter} from './phrase-meter-review.mjs';
const evidence={observed:[{id:'a',source:{measureOrdinal:1}},{id:'b',source:{measureOrdinal:2}}],mappings:[{eventId:'next',sourceEventId:'b'}]};
const closure={status:'observed',durationMatches:true,gapMatches:true,sourceNoteIds:['a'],nextEventId:'next',sourceDuration:1.5,explicitRestDuration:.5,breathSymbols:[]};
const check=(count,unit,duration,rest)=>reviewClosureInMeter({...closure,sourceDuration:duration,explicitRestDuration:rest},evidence,[1,2].map(measureOrdinal=>({measureOrdinal,meter:{count,unit}})));
it('keeps short internal breath undecided but protects strong closure',()=>{
 expect(check(4,4,1.5,.5).decision).toBe('cannot_judge');
 expect(check(4,4,2.5,5.5).decision).toBe('protect-boundary');
 expect(check(4,4,2,2).decision).toBe('protect-boundary');
});
it('uses relative beat duration and preserves equivalent scaling',()=>{
 expect(check(4,4,1.5,1.5).decision).toBe('cannot_judge');
 expect(check(4,8,1.5,1.5).decision).toBe('protect-boundary');
 expect(check(4,2,4,4).decision).toBe(check(4,4,2,2).decision);
 expect(check(6,8,3,3).durationBeats).toBe(2);
});
it('abstains on unknown, additive and changing meters',()=>{
 expect(check(5,8,3,3).status).toBe('unknown');
 const xml='<score-partwise><part id="P1"><measure><attributes><time><beats>3+2</beats><beat-type>8</beat-type></time></attributes></measure></part></score-partwise>';
 expect(sourceMeterTimeline(xml,'P1')[0].meter).toBe(null);
 expect(reviewClosureInMeter(closure,evidence,[{measureOrdinal:1,meter:{count:4,unit:4}},{measureOrdinal:2,meter:{count:3,unit:4}}]).reason).toBe('meter-change-across-closure');
});
it('inherits initial meter but rejects mid-measure time changes',()=>{
 const xml='<part id="P1"><measure><attributes><time><beats>4</beats><beat-type>4</beat-type></time></attributes></measure><measure/><measure><note/><attributes><time><beats>3</beats><beat-type>4</beat-type></time></attributes></measure></part>';
 const t=sourceMeterTimeline(xml,'P1');
 expect(t.map(x=>x.meter?.count??null)).toEqual([4,4,null]);
});
it('protects a marked breath and abstains when source durations disagree',()=>{
 const t=[1,2].map(measureOrdinal=>({measureOrdinal,meter:{count:4,unit:4}}));
 expect(reviewClosureInMeter({...closure,breathSymbols:['fermata']},evidence,t).decision).toBe('protect-boundary');
 expect(reviewClosureInMeter({...closure,durationMatches:false},evidence,t).status).toBe('unknown');
});
