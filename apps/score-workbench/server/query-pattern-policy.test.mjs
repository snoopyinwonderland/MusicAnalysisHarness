import {describe,it,expect} from 'vitest';
import {queryPatternNotice} from './query-pattern-policy.mjs';
const notes=p=>p.map((pitchMidi,i)=>({pitchMidi,onset:i,durationRatio:1}));
const q={mode:'melody_rhythm',allowContinuousStepwise:false,allowContinuousRepeated:false};
describe('explicit simple-pattern search policy',()=>{
 it('blocks ascending and descending chromatic/diatonic runs',()=>{for(const p of [[60,62,64,65,67,69],[70,69,67,65,64,62]])expect(queryPatternNotice(q,notes(p))).toContain('順'.replace('順','순차'));});
 it('blocks pure repetitions only',()=>expect(queryPatternNotice(q,notes([60,60,60,60,60,60]))).toContain('같은 음'));
 it('does not suppress mixed motifs, turns, leaps or short queries',()=>{for(const p of [[60,62,64,62,60,62],[60,60,60,60,62,60],[60,62,64,67,69,71],[60,62,64,65]])expect(queryPatternNotice(q,notes(p))).toBeNull();});
 it('each permission is independent',()=>{expect(queryPatternNotice({...q,allowContinuousStepwise:true},notes([60,62,64,65,67,69]))).toBeNull();expect(queryPatternNotice({...q,allowContinuousStepwise:true},notes([60,60,60,60,60,60]))).not.toBeNull();expect(queryPatternNotice({...q,allowContinuousRepeated:true},notes([60,60,60,60,60,60]))).toBeNull();});
 it('preserves legacy queries and rhythm/contour searches',()=>{for(const query of [{mode:'melody'}, {...q,mode:'rhythm'},{...q,mode:'contour'}])expect(queryPatternNotice(query,notes([60,62,64,65,67,69]))).toBeNull();});
 it('does not join across silence',()=>{const ns=notes([60,62,64,65,67,69]);ns.slice(3).forEach(n=>n.onset+=1);expect(queryPatternNotice(q,ns)).toBeNull();});
});
