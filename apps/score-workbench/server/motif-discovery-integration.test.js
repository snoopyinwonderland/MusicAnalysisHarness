import {it,expect} from 'vitest';
import {createMotifDiscoveryComparison,motifDiscoveryEnabled} from './motif-discovery-integration.mjs';
import {discoverMotifs,linkMotifSpanFamilies} from './motif-discovery.mjs';
const identity={workId:'w',streamId:'P1:1:1',sourceId:'a.xml'};
const notes=Array.from({length:12},(_,i)=>({id:`n${i}`,onset:i,durationRatio:1,pitchMidi:60+i%4,spelling:['C4','D4','E4','F4'][i%4],meter:'4/4',measureOrdinal:Math.floor(i/4)+1,beat:i%4+1,voice:'1'}));
const args={notes,identity,sourceSha:'source',renderSourceSha:'render'};
const make=extra=>createMotifDiscoveryComparison({engineRevision:'engine',...extra});
it('is opt-in only',()=>{expect(motifDiscoveryEnabled('1')).toBe(true);for(const v of [undefined,true,'true',0])expect(motifDiscoveryEnabled(v)).toBe(false)});
it('preserves inputs and binds all occurrences to original IDs and half-open quarters',()=>{
 const before=JSON.stringify(args),r=make({analyze:n=>discoverMotifs(n,{minGain:4})})(args);expect(JSON.stringify(args)).toBe(before);expect(r.families.length).toBeGreaterThan(0);
 for(const f of r.families)for(const o of f.occurrences){expect(o.startEventId).toBe(notes[o.startIndex].id);expect(o.endEventId).toBe(notes[o.endIndex].id);expect(o.span.convention).toBe('[start,end)')}
 expect(r.provenance.canonicalIrDocumentId).toBe(null);
});
it('uses defensive cache copies and invalidates every source/stream/observation/revision',()=>{
 const compare=make(),a=compare(args);a.eventBindings[0].id='bad';expect(compare(args).eventBindings[0].id).toBe('n0');expect(compare(args).runtime.cacheHit).toBe(true);
 for(const extra of [{sourceSha:'new'},{renderSourceSha:'new'},{identity:{...identity,streamId:'P2:1:1'}},{notes:notes.map(n=>({...n,spelling:'C5'}))}])expect(compare({...args,...extra}).provenance.cacheKey).not.toBe(a.provenance.cacheKey);
 expect(make({engineRevision:'new'})(args).provenance.cacheKey).not.toBe(a.provenance.cacheKey);
});
it('evicts bounded entries',()=>{const compare=make({capacity:1});compare(args);compare({...args,sourceSha:'new'});expect(compare(args).runtime.cacheHit).toBe(false)});
it('declines over-budget input before calling quadratic discovery, without truncating',()=>{let calls=0;const r=make({maxInputNotes:8,analyze:()=>{calls++;throw Error()}})(args);expect(calls).toBe(0);expect(r.skipped).toBe('input-note-budget-exceeded');expect(r.eventBindings).toHaveLength(12)});
it('reports changing metre and malformed monophony instead of inventing results',()=>{
 expect(make()({...args,notes:notes.map((n,i)=>({...n,meter:i>5?'3/4':'4/4'}))}).skipped).toBe('meter-change-not-yet-supported');
 expect(make()({...args,notes:[{...notes[0],durationRatio:-1}]}).status).toBe('skipped');
 expect(make()({...args,notes:[notes[0],{...notes[1],onset:0}]}).status).toBe('skipped');
 expect(()=>make()({...args,sourceSha:null})).toThrow();
});
it('tie continuation requires the same voice and preserves the final tied event index',()=>{
 const tied=[...notes.slice(0,4),{...notes[3],id:'tail',onset:4,tieStop:true},...notes.slice(4).map(n=>({...n,onset:n.onset+2}))];
 const good=discoverMotifs(tied,{minGain:4,breathStarts:new Set()});expect(good.inputWarnings).toEqual([]);
 const bad=discoverMotifs(tied.map(n=>n.id==='tail'?{...n,voice:'2'}:n),{minGain:4,breathStarts:new Set()});expect(bad.inputWarnings[0].reason).toBe('voice differs');
 expect(good.families.flatMap(f=>f.occurrences).some(o=>o.endIndex===4&&o.end===5)).toBe(true);
 expect(()=>discoverMotifs([{...notes[0],durationRatio:-1}])).toThrow(/invalid/);
});
it('does not collapse unassigned old families or mutate old span IDs',()=>{
 const spans=[{startIndex:0,endIndex:3,id:'old-a'},{startIndex:4,endIndex:7,id:'old-b'}];
 expect(linkMotifSpanFamilies(notes,spans,{families:[]}).map(s=>s.linkedFamily)).toEqual([1,2]);expect(spans[0]).not.toHaveProperty('linkedFamily');
});
