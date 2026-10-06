import {it,expect} from 'vitest';
import {buildSearchWindows} from './search-segments.mjs';
import {analyzeStructureSnapshot,structureSearchQueries} from './structure-analysis-adapter.mjs';
import {selectStructureQueries,SELECTION_CONFIG} from './preclearance-search.mjs';
const input=()=>({identity:{sourceId:'fixture',streamId:'P1'},sourceHash:'fixture',meter:'4/4',events:Array.from({length:30},(_,i)=>({id:'e'+i,kind:'note',pitchMidi:[60,64,67,62,69,65,61,68][i%8],durationRatio:.5,onset:i*.5+(i>=10?1:0),measureOrdinal:Math.floor(i/8)+1,beat:i%8*.5+1}))});
it('includes adjacent notes across inferred phrase boundaries and preserves rests',()=>{
 const s=analyzeStructureSnapshot(input(),{analyzer:()=>({version:'test',boundaries:[{index:10,supported:true}]})}),bank=buildSearchWindows(s,{lengths:[12]});
 expect(bank.units.some(u=>u.attackEventIds.includes('e9')&&u.attackEventIds.includes('e10'))).toBe(true);
 const q=structureSearchQueries({...s,units:bank.units},{kinds:['window']})[0];expect(q.query.events.some(e=>e.kind==='rest'&&e.durationRatio===1)).toBe(true);
 expect(q.query.events.filter(e=>e.kind==='note').map(e=>e.id)).toEqual(Array.from({length:12},(_,i)=>'e'+i));
});
it('offers phrase, windows and hybrid without changing the default strategy',()=>{
 const s=analyzeStructureSnapshot(input());
 expect(selectStructureQueries(s).selected).toEqual(selectStructureQueries(s,{...SELECTION_CONFIG,segmentStrategy:'phrase'}).selected);
 const w=selectStructureQueries(s,{...SELECTION_CONFIG,segmentStrategy:'windows'});expect(w.selected.length).toBeGreaterThan(0);expect(w.selected.every(e=>e.task.kinds.includes('window'))).toBe(true);
 const h=selectStructureQueries(s,{...SELECTION_CONFIG,segmentStrategy:'hybrid'});expect(h.selected.length).toBeLessThanOrEqual(14);expect(new Set(h.selected.map(e=>e.signature)).size).toBe(h.selected.length);
});
it('reports truncation instead of claiming a complete window search',()=>{
 const bank=buildSearchWindows(analyzeStructureSnapshot(input()),{maximumWindows:2});expect(bank.units).toHaveLength(2);expect(bank.omittedByBudget).toBeGreaterThan(0);
});
