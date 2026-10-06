import {it,expect} from 'vitest';
import {pillarCandidates} from './pillarCandidates';
import {composePillarDisplay} from './pillarDisplay';
const notes=(p:number[],d:number[])=>{let o=0;return p.map((pitchMidi,i)=>{const n={id:String(i),kind:'note',pitchMidi,durationRatio:d[i],onset:o,beat:1+o%4,measure:1+Math.floor(o/4)};o+=d[i];return n;}) as any;};
it('does not nominate meter alone',()=>expect(pillarCandidates(notes([60,62,64,65],[1,1,1,1]))).toEqual([]));
it('preserves a short offbeat phrase start as a tentative interpretation-dependent candidate',()=>{
 const n=notes([60,62,64,65],[.25,.25,.25,.25]);
 const before=JSON.stringify(n);
 const c=composePillarDisplay(n,pillarCandidates(n),[{noteId:'1',phraseNumber:2}]).find(c=>c.index===1);
 expect(c?.level).toBe('tentative');expect(c?.phraseHints).toEqual([{noteId:'1',phraseNumber:2}]);expect(c?.reasons).toEqual([]);
 expect(JSON.stringify(n)).toBe(before);
 expect(pillarCandidates(n).some(c=>c.index===1)).toBe(false);
});
it('does not create phantom notes for stale phrase references',()=>{
 const n=notes([60,62],[.25,.25]);
 expect(composePillarDisplay(n,pillarCandidates(n),[{noteId:'missing',phraseNumber:1},{noteId:'0',phraseNumber:0}])).toEqual([]);
});
it('includes beat-length surface anchors when meter is known',()=>{
 const n=notes([66,67,69,71],[1,1,1,1]);
 expect(pillarCandidates(n,{meters:{1:{count:4,unit:4}}}).map(c=>c.index)).toEqual([0,1,2,3]);
});
it('includes both half-note anchors and preserves offbeat sustained arrivals',()=>{
 const n=notes([66,67],[2,2]);
 expect(pillarCandidates(n,{meters:{1:{count:4,unit:4}}})).toHaveLength(2);
 const sync=notes([71,69,71,74],[.5,.5,.5,1]);
 expect(pillarCandidates(sync,{meters:{1:{count:4,unit:4}}}).find(c=>c.index===3)?.reasons).toContain('엇박에서 다음 박을 이어받는 지속');
});
it('does not equate an eighth-note subdivision with a compound-meter pulse',()=>{
 const n=notes([60,62,64,65,67,69],[.5,.5,.5,.5,.5,.5]);
 expect(pillarCandidates(n,{meters:{1:{count:6,unit:8}}})).toHaveLength(0);
});
it('records a delayed entrance without relocating the downbeat',()=>{
 const n=notes([66],[1]);n[0].beat=2;n[0].onset=1;
 const result=pillarCandidates(n,{meters:{1:{count:4,unit:4}}});
 expect(result[0].reasons).toContain('쉼 뒤 선율 진입');
 expect(result[0].reasons).not.toContain('기보 마디 첫 박');
});
it('retains a local returning anchor but not its short inner neighbor',()=>{
 const n=notes([71,69,71,74],[.5,.5,.5,1]);
 const result=pillarCandidates(n,{meters:{1:{count:4,unit:4}}});
 expect(result.map(c=>c.index)).toContain(0);
 expect(result.map(c=>c.index)).not.toContain(1);
 expect(result.map(c=>c.index)).toContain(3);
});
it('combines arrival and duration without mutating source',()=>{const n=notes([60,62,64,65,67],[.5,.5,.5,2,.5]);const before=JSON.stringify(n);expect(pillarCandidates(n).some(c=>c.index===3)).toBe(true);expect(JSON.stringify(n)).toBe(before);});
it('is invariant to transposition',()=>{const n=notes([60,62,64,65,67],[.5,.5,.5,2,.5]);expect(pillarCandidates(n).map(c=>c.index)).toEqual(pillarCandidates(n.map((x:any)=>({...x,pitchMidi:x.pitchMidi+5}))).map(c=>c.index));});
it('keeps optional harmony provenance and conflicts separate',()=>{const n=notes([60,62,64,65],[1,1,1,1]);const e={noteId:'1',analysisId:'h1',engineVersion:'test',evidenceRefs:['ev1'],label:'arrival alternative',effect:'conflicts' as const,status:'hypothesis' as const};const c=pillarCandidates(n,{harmonyEvidence:[e]});expect(c[0].harmony).toEqual([e]);expect(c[0].level).toBe('tentative');expect(pillarCandidates(n)).toEqual([]);});
