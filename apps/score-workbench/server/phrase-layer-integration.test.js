import {it,expect} from 'vitest';
import {createPhraseLayerComparison,indexedQuarter,phraseLayersEnabled} from './phrase-layer-integration.mjs';
import {analyzePhraseLayers} from './phrase-breath-layer.mjs';
const identity={workId:'w',streamId:'P1:1:1',sourceId:'source.xml'};
const notes=Array.from({length:4},(_,i)=>({id:`w-${i}`,pitchMidi:60+i,onset:i*2,durationRatio:1,
 measure:Math.floor(i/2)+1,measureOrdinal:Math.floor(i/2)+1,beat:i%2?3:1,meter:'4/4',meterCount:4,meterUnit:4}));
const args={identity,notes,sourceSha:'source-sha',renderSourceSha:'render-sha'};
const make=extra=>createPhraseLayerComparison({engineRevision:'engine-sha',harmonyRevision:'harmony-sha',...extra});
it('requires an explicit feature flag',()=>{
 for(const value of [undefined,null,'0','true',true,2])expect(phraseLayersEnabled(value)).toBe(false);
 expect(phraseLayersEnabled('1')).toBe(true);
});
it('represents indexed decimal and exponent times without claiming XML fractions',()=>{
 expect(indexedQuarter(1.25)).toEqual({num:'5',den:'4'});
 expect(indexedQuarter(0)).toEqual({num:'0',den:'1'});
 expect(indexedQuarter(1e-7)).toEqual({num:'1',den:'10000000'});
 expect(indexedQuarter(1/3)).toEqual({num:'3333333333333333',den:'10000000000000000'});
 expect(()=>indexedQuarter(Infinity)).toThrow();
});
it('binds original IDs and a half-open range to the source snapshot',()=>{
 const a=make()(args);
 expect(a.provenance.canonicalIrDocumentId).toBe(null);
 expect(a.provenance.upstreamCommit).toMatch(/^650ca3b4/);
 for(const range of a.breath.ranges){
  expect(range.startEventId).toBe(notes[range.startIndex].id);
  expect(range.endEventId).toBe(notes[range.endIndexExclusive-1].id);
  expect(range.eventIds).toEqual(notes.slice(range.startIndex,range.endIndexExclusive).map(n=>n.id));
  expect(range.span.convention).toBe('[start,end)');
  expect(range.span.precision).toBe('indexed-float-decimal-not-source-rational');
 }
});
it('cached output cannot be changed by a caller',()=>{
 let calls=0;const compare=make({analyze:(...a)=>{calls++;return analyzePhraseLayers(...a)}});
 const a=compare(args);a.breath.ranges[0].eventIds[0]='wrong';
 const b=compare(args);expect(b.breath.ranges[0].eventIds[0]).toBe('w-0');
 expect(b.runtime.cacheHit).toBe(true);expect(calls).toBe(1);
});
it('invalidates when source, input, stream, key, gate or engine revisions change',()=>{
 const compare=make(),a=compare(args);
 for(const extra of [{sourceSha:'new'}, {renderSourceSha:'new'}, {notes:notes.map(n=>({...n,durationRatio:.5}))},
  {identity:{...identity,streamId:'P2:1:1'}},{key:{tonicPc:2,minor:false}},{cadenceMinStrength:.7}]){
  const b=compare({...args,...extra});expect(b.provenance.cacheKey).not.toBe(a.provenance.cacheKey);expect(b.runtime.cacheHit).toBe(false);
 }
 expect(make({engineRevision:'new'})(args).provenance.cacheKey).not.toBe(a.provenance.cacheKey);
 expect(make({harmonyRevision:'new'})(args).provenance.cacheKey).not.toBe(a.provenance.cacheKey);
});
it('evicts bounded entries without dropping notes or musical candidates',()=>{
 const compare=make({capacity:1});const a=compare(args);compare({...args,sourceSha:'new'});
 const b=compare(args);expect(b.runtime.cacheHit).toBe(false);expect(b.breath).toEqual(a.breath);
});
it('rejects unbound, duplicate and invalid inputs including single-note negative duration',()=>{
 expect(()=>make()({...args,sourceSha:null})).toThrow(/identity/);
 expect(()=>make()({...args,notes:[notes[0],notes[0]]})).toThrow(/Unique/);
 expect(()=>make()({...args,notes:[{...notes[0],durationRatio:-1}]})).toThrow(/duration/);
 expect(()=>make()({...args,cadenceMinStrength:-1})).toThrow(/gate/);
 expect(()=>make({capacity:0})).toThrow(/capacity/);
});
it('does not mutate legacy notes or source metadata',()=>{
 const before=JSON.stringify(args);make()(args);expect(JSON.stringify(args)).toBe(before);
});
it('gates missing cadence strength as unresolved, and does not call a learned model',()=>{
 const a=make()({...args,cadenceAt:indices=>new Map(indices.map(i=>[i,{type:'PAC'}]))});
 expect(a.unresolvedCadences).toBeGreaterThan(0);expect(a.phrases.boundaries.every(b=>!b.cadence)).toBe(true);
});
it('does not merge a tie tail from another voice, or add an already sounding duration twice',()=>{
 const input=notes.map(n=>({...n,voice:'1'}));input[1]={...input[1],pitchMidi:input[0].pitchMidi,onset:1,voice:'2',tieStop:true};
 const a=make()({...args,notes:input});expect(a.inputWarnings[0].reason).toBe('voice differs');
 const merged=notes.map(n=>({...n,durationRatio:2})),plain=make()({...args,notes:merged});
 const again=make()({...args,notes:merged.map(n=>({...n,tieStart:true}))});
 expect(again.breath.starts).toEqual(plain.breath.starts);
 expect(again.breath.boundaries).toEqual(plain.breath.boundaries);
 expect(again.breath.ranges.map(r=>r.span)).toEqual(plain.breath.ranges.map(r=>r.span));
 // The changed observation metadata intentionally creates different source-bound range IDs.
 expect(again.breath.ranges[0].rangeId).not.toBe(plain.breath.ranges[0].rangeId);
});
it('uses real 4/4 to 3/4 changes even when work-level metre is wrong',()=>{
 const input=[...notes,...notes.map((n,i)=>({...n,id:`later-${i}`,onset:8+i*1.5,durationRatio:.75,
  measure:3+Math.floor(i/2),measureOrdinal:3+Math.floor(i/2),beat:i%2?2.5:1,meter:'3/4'}))];
 const correct=analyzePhraseLayers(input),wrongGlobal=analyzePhraseLayers(input.map(n=>({...n,meterCount:2,meterUnit:2})));
 expect(wrongGlobal.breath).toEqual(correct.breath);expect(wrongGlobal.phrases).toEqual(correct.phrases);
});
