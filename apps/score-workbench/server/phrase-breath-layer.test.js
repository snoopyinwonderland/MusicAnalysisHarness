import {it,expect} from 'vitest';
import {analyzeBreathLayer,analyzePhraseLayers} from './phrase-breath-layer.mjs';

// 4/4 melody: quarters, each 2-bar unit ends on a half note followed by a quarter rest
const line=(units)=>{
 const notes=[];let t=0;
 for(let u=0;u<units;u++){
  for(const [p,d] of [[60,1],[62,1],[64,1],[65,1],[67,1],[65,1]]){notes.push({pitchMidi:p,onset:t,durationRatio:d});t+=d;}
  notes.push({pitchMidi:64,onset:t,durationRatio:1});t+=2;  // quarter + quarter rest closes the unit
 }
 return notes.map(n=>({...n,measureOrdinal:Math.floor(n.onset/4)+1,mstart:Math.floor(n.onset/4)*4,meterCount:4,meterUnit:4}));
};

it('finds the breath after each rested two-bar unit',()=>{
 const a=analyzeBreathLayer(line(4));
 expect(a.layer).toBe('breath');
 expect(a.starts).toEqual([7,14,21]);
 expect(a.boundaries.every(b=>b.cues.rest>0&&b.cues.startAlignment===1)).toBe(true);
});

it('merges tie continuations instead of reading them as new attacks',()=>{
 const notes=line(2);
 const tied=[...notes.slice(0,6),{...notes[6],durationRatio:1},{...notes[6],onset:notes[6].onset+1,durationRatio:1,tieStop:true,isAttack:false},...notes.slice(7)];
 const a=analyzeBreathLayer(tied);
 expect(a.starts).toEqual([8]);  // index refers to the original note list
});

it('upper layer nests in breath units and turns a caller-supplied cadence into a phrase end',()=>{
 const notes=line(4);
 const plain=analyzePhraseLayers(notes,{key:{tonicPc:0,minor:false}});
 expect(plain.phrases.starts.every(i=>plain.breath.starts.includes(i))).toBe(true);
 // an authentic cadence closing unit 1 (before note 7) makes that breath end a phrase end
 const withCadence=analyzePhraseLayers(notes,{key:{tonicPc:0,minor:false},cadenceAt:indices=>new Map(indices.filter(i=>i===7).map(i=>[i,{type:'PAC',strength:.8}]))});
 expect(withCadence.phrases.starts).toContain(7);
 expect(withCadence.phrases.boundaries.find(b=>b.index===7).cadence.type).toBe('PAC');
});

it('derives bar starts from MusicXML beats when measure starts are absent',()=>{
 const notes=line(2).map(({mstart,...n})=>({...n,beat:1+(n.onset-mstart)}));
 expect(analyzeBreathLayer(notes).starts).toEqual([7]);
});

it('ignores cadence hypotheses below the strength gate (unresolved, not closure evidence)',()=>{
 const notes=line(4),key={tonicPc:0,minor:false};
 const weak=analyzePhraseLayers(notes,{key,cadenceAt:indices=>new Map(indices.map(i=>[i,{type:'PAC',strength:0}]))});
 const none=analyzePhraseLayers(notes,{key});
 expect(weak.phrases.starts).toEqual(none.phrases.starts);
 expect(weak.unresolvedCadences).toBeGreaterThan(0);
 expect(weak.phrases.boundaries.every(b=>b.cadence===null)).toBe(true);
});

it('reads a non-continuous tie tail as a new attack and reports it',()=>{
 const notes=line(2);
 const bad=[...notes.slice(0,3),{...notes[3],pitchMidi:notes[3].pitchMidi+5,tieStop:true,isAttack:false},...notes.slice(4)];
 const a=analyzePhraseLayers(bad,{key:{tonicPc:0,minor:false}});
 expect(a.inputWarnings).toEqual([{index:3,issue:'tie-tail-not-continuous',reason:'pitch differs'}]);
 const gap=[...notes.slice(0,3),{...notes[3],pitchMidi:notes[2].pitchMidi,onset:notes[3].onset+.5,tieStop:true},...notes.slice(4)];
 expect(analyzePhraseLayers(gap,{}).inputWarnings[0].reason).toMatch(/gap/);
 expect(()=>analyzePhraseLayers([{...notes[0],durationRatio:-1},notes[1]],{})).toThrow(/negative/);
});

it('uses the per-measure metre string when the metre changes',()=>{
 const notes=line(2).map(n=>({...n,meter:'4/4'}));
 const a=analyzeBreathLayer(notes),b=analyzeBreathLayer(notes.map(n=>({...n,meterCount:3,meterUnit:4})));
 expect(b.starts).toEqual(a.starts);  // the per-measure 4/4 string overrides a wrong work-level 3/4
});

it('requires metre information',()=>{
 expect(()=>analyzeBreathLayer([{pitchMidi:60,onset:0,durationRatio:1},{pitchMidi:62,onset:1,durationRatio:1}])).toThrow();
});
