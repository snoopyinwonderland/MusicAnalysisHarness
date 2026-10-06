import {it,expect} from 'vitest';
import {structuralVariation,structuralKinds} from './structural-variation.mjs';
const events=[60,62,64,67,65,64].map((pitchMidi,i)=>({id:'n'+i,kind:'note',pitchMidi,durationRatio:1}));
for(const kind of structuralKinds)it(kind+' preserves protected arrival and pitch without mutation',()=>{
 const before=structuredClone(events),r=structuralVariation(events,kind,['n0','n5']);
 expect(events).toEqual(before);expect(r.events.reduce((s,e)=>s+e.durationRatio,0)).toBe(6);
 expect(r.changes.length).toBeGreaterThan(0);expect(r.sourceToQueryMap).toHaveLength(6);
 let t=0;const last=r.events.find(e=>{if(e.id==='n5')return true;t+=e.durationRatio;return false});expect(t).toBe(5);expect(last.pitchMidi).toBe(64);
});
it('cannot move a protected internal arrival',()=>{
 expect(()=>structuralVariation(events,'internal-rhythm',events.map(e=>e.id))).toThrow('No internal rhythm site');
});
it('retains rests and rejects unsupported passing sites',()=>{
 const xs=[events[0],{id:'r',kind:'rest',durationRatio:1,pitchMidi:null},events[1]];
 expect(()=>structuralVariation(xs,'passing-insertion')).toThrow();
});
