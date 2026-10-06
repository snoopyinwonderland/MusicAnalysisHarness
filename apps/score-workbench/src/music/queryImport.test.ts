import {describe,it,expect} from 'vitest';
import {parseQueryImport,formatCompactQuery} from './queryImport';
const q={version:1,mode:'melody_rhythm',meter:'3/8',startsOnDownbeat:true,events:[{id:'n',kind:'note',pitchMidi:59,durationRatio:.25},{id:'r',kind:'rest',pitchMidi:null,durationRatio:.5}]};
describe('Query JSON import',()=>{
 it('supports compact pitches, accidentals, rests, fractions and a trailing dash',()=>{const x=parseQueryImport('C4(0.5)-D♭4(1)-R(1/2)-A4#(1.5)-',{meter:'6/8'});expect(x.events.map(e=>[e.pitchMidi,e.durationRatio])).toEqual([[60,.5],[61,1],[null,.5],[70,1.5]]);expect(x.meter).toBe('6/8');});
 it('round trips compact pitch/duration and rejects partial text',()=>{const x=parseQueryImport(JSON.stringify(q));const y=parseQueryImport(formatCompactQuery(x));expect(y.events.map(e=>[e.pitchMidi,e.durationRatio])).toEqual(x.events.map(e=>[e.pitchMidi,e.durationRatio]));for(const t of ['C4(0)-D4(1)','C4(1/0)','C4(1)-junk','C#4b(1)'])expect(()=>parseQueryImport(t)).toThrow();});
 it('accepts wrapper and bare query, preserves exact durations and rests',()=>{for(const v of [q,{schema:'musicanote-query',query:q}]){const x=parseQueryImport(JSON.stringify(v));expect(x.events).toEqual(q.events);expect(x.meter).toBe('3/8');expect(x.allowContinuousStepwise).toBe(false);}});
 it('accepts JSON fences',()=>expect(parseQueryImport('```json\n'+JSON.stringify(q)+'\n```').events).toEqual(q.events));
 it('preserves permissions and spelling',()=>expect(parseQueryImport(JSON.stringify({...q,allowContinuousStepwise:true,events:[{...q.events[0],spelling:'C♭4'}]}))).toMatchObject({allowContinuousStepwise:true,events:[{spelling:'C♭4'}]}));
 it('rejects invalid JSON, unknown meter, negative duration, duplicate IDs and bad pitch',()=>{for(const v of ['oops',JSON.stringify({...q,meter:'8/banana'}),JSON.stringify({...q,events:[{...q.events[0],durationRatio:-1}]}),JSON.stringify({...q,events:[q.events[0],q.events[0]]}),JSON.stringify({...q,events:[{...q.events[0],pitchMidi:130}]})])expect(()=>parseQueryImport(v)).toThrow();});
 it('keeps tie and tuplet notation',()=>{const e={...q.events[0],tieGroup:'t',tupletGroup:'u',actualNotes:3,normalNotes:2,writtenDuration:.5,durationRatio:1/3};expect(parseQueryImport(JSON.stringify({...q,events:[e]})).events[0]).toEqual(e);});
});
