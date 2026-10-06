import {describe,it,expect} from 'vitest';
import {createPhraseContextCache} from './phrase-context-cache.mjs';
import {analyzePhraseBoundaries,comparePhraseBoundaries} from './phrase-boundaries.mjs';
describe('phrase context cache',()=>{
 it('reuses identical content but invalidates every property and revision',()=>{
  let calls=0;const cache=createPhraseContextCache(notes=>({version:'test',boundaries:[{n:notes[0].pitchMidi}],extra:++calls}));
  const notes=[{pitchMidi:60,durationRatio:1}];
  expect(cache.get(notes).hit).toBe(false);expect(cache.get(structuredClone(notes)).hit).toBe(true);
  expect(cache.get([{durationRatio:1,pitchMidi:60}]).hit).toBe(true);
  for(const change of [{onset:1},{durationRatio:2},{pitchMidi:61},{tieStop:true},{breathSymbols:['breath']},{measureOrdinal:2}])expect(cache.get([{...notes[0],...change}]).hit).toBe(false);
  expect(cache.get(notes,'new-analyzer').hit).toBe(false);
 });
 it('keeps candidate comparison identical for supported and conflicting boundaries',()=>{
  const q={boundaries:[{}, {supported:true,reliable:true,strength:1,cues:[{name:'observed-gap',strength:1}]},{}]};
  for(const boundary of [{supported:true,reliable:true,strength:.8,continuity:0},{supported:false,reliable:true,strength:0,continuity:1},{supported:false,reliable:false,strength:0,continuity:0}]){
   const full={version:'test',boundaries:[{},boundary,{}]},cache=createPhraseContextCache(()=>full),pairs=[{queryIndex:0,candidateIndex:0},{queryIndex:1,candidateIndex:1}];
   expect(comparePhraseBoundaries(q,cache.get([]).value,pairs)).toEqual(comparePhraseBoundaries(q,full,pairs));
  }
 });
 it('does not retain oversized values',()=>{
  const cache=createPhraseContextCache(()=>({version:'test',boundaries:[]}),{maxBytes:1});
  expect(cache.get([]).hit).toBe(false);expect(cache.get([]).hit).toBe(false);expect(cache.stats().bytes).toBe(0);
 });
 it('preserves real comparison and enforces eviction budget',()=>{
  const notes=Array.from({length:20},(_,i)=>({pitchMidi:60+i%5,durationRatio:1,onset:i+(i>8?2:0)}));
  const cache=createPhraseContextCache(analyzePhraseBoundaries,{maxBytes:20000});
  const analysis=analyzePhraseBoundaries(notes),cached=cache.get(notes).value,pairs=notes.map((_,i)=>({queryIndex:i,candidateIndex:i}));
  expect(comparePhraseBoundaries(analysis,cached,pairs)).toEqual(comparePhraseBoundaries(analysis,analysis,pairs));
  for(let i=0;i<20;i++)cache.get([{pitchMidi:i,durationRatio:1}]);
  expect(cache.stats().bytes).toBeLessThanOrEqual(20000);
 });
});
