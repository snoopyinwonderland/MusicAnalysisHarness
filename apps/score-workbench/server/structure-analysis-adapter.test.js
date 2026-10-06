import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { analyzeStructureSnapshot, structureRefreshPlan, structureSearchQueries } from './structure-analysis-adapter.mjs';

const input = () => ({ sourceHash:'fixture-v1', identity:{sourceId:'score',streamId:'P1:1:1'}, meter:'3/4',
  events:[60,62,65,64,67,69,65,60].map((pitchMidi,i)=>({id:`e${i}`,kind:'note',pitchMidi,
    onsetQuarter:i<4?i:i+2,durationQuarter:1,measure:Math.floor(i/3),voice:'1',staff:'1'})) });
const analyzer = () => ({version:'fixture/1',calibrated:false,
  boundaries:[{index:0,supported:false},{index:4,supported:true,strength:.8},{index:8,supported:false}],
  motifCells:[{startIndex:0,endIndex:3,rhythmFamily:'example'}]});

describe('Phrase/Motif bridge',()=>{
  it('uses phrase-local meters and defers a silent meter-change span',()=>{
    const data=input();data.meter='unknown';data.events.forEach((e,i)=>{e.meter=i<4?'3/4':'4/4';e.measureOrdinal=i<4?1:3;});
    const s=analyzeStructureSnapshot(data,{analyzer});expect(structureSearchQueries(s).map(t=>t.query.meter)).toEqual(['3/4','4/4']);
    const all=()=>({version:'one',boundaries:[]});expect(structureSearchQueries(analyzeStructureSnapshot(data,{analyzer:all}))[0].query.meter).toBe('unknown');
    data.events.forEach(e=>e.meter='3/4');data.meterTimeline=[{measureOrdinal:2,meter:'2/4'},{measureOrdinal:3,meter:'3/4'}];
    expect(structureSearchQueries(analyzeStructureSnapshot(data,{analyzer:all}))[0].query.meter).toBe('unknown');
  });
  it('invalidates snapshots on meter or timeline correction',()=>{
    const a=analyzeStructureSnapshot(input(),{analyzer}),b=analyzeStructureSnapshot({...input(),meter:'6/8'},{analyzer});
    expect(structureRefreshPlan(a,b).changed).toContain('meterHash');
  });
  it('preserves both layers and deduplicates identical spans',()=>{
    const snapshot=analyzeStructureSnapshot(input(),{analyzer});
    expect(snapshot.units.map(u=>u.kind)).toEqual(['phrase','phrase','motif']);
    expect(snapshot.units[2].phraseIds).toEqual([snapshot.units[0].unitId]);
    const tasks=structureSearchQueries(snapshot);
    expect(tasks).toHaveLength(2); expect(tasks[0].unitIds).toHaveLength(2);
    expect(tasks[0].query.meter).toBe('3/4');
    expect(snapshot.units[0].location.startMeasure).toBe(0);
    expect(snapshot.units.every(u=>u.confidence===null)).toBe(true);
  });
  it('preserves explicit rests and reconstructs observed gaps',()=>{
    const data=input(), one=()=>({version:'one',boundaries:[]});
    const snapshot=analyzeStructureSnapshot(data,{analyzer:one});
    expect(structureSearchQueries(snapshot)[0].query.events.find(e=>e.kind==='rest').durationRatio).toBe(2);
    data.events.splice(4,0,{id:'r',kind:'rest',pitchMidi:null,onsetQuarter:4,durationQuarter:2});
    const withRest=analyzeStructureSnapshot(data,{analyzer:one});
    expect(structureSearchQueries(withRest)[0].query.events.filter(e=>e.kind==='rest')).toHaveLength(1);
  });
  it('invalidates analyzer, configuration, input and parser changes without mutating history',()=>{
    const data=input(), old=analyzeStructureSnapshot(data,{analyzer});
    expect(structureRefreshPlan(old,analyzeStructureSnapshot(data,{analyzer})).status).toBe('current');
    for(const next of [
      analyzeStructureSnapshot(data,{analyzer:()=>({...analyzer(),version:'fixture/2'})}),
      analyzeStructureSnapshot(data,{analyzer,config:{profile:'next'}}),
      analyzeStructureSnapshot({...data,sourceHash:'changed'},{analyzer}),
      analyzeStructureSnapshot({...data,parserVersion:'next'},{analyzer}),
    ]) expect(structureRefreshPlan(old,next)).toMatchObject({status:'reanalysis_available',preservePrevious:true,correctionsRequireReview:true});
    expect(old.dependencies.analyzer).toBe('fixture/1');
  });
  it('rejects mixed voices, duplicate IDs and missing timing; permits cross-staff same voice',()=>{
    const data=input(); data.events[1].voice='2';
    expect(()=>analyzeStructureSnapshot(data)).toThrow('Mixed voice');
    data.events[1].voice='1';data.events[1].staff='2';
    expect(()=>analyzeStructureSnapshot(data)).not.toThrow();
    data.events[1].id='e0';expect(()=>analyzeStructureSnapshot(data)).toThrow('Unique');
    data.events[1].id='e1';data.events[1].onsetQuarter=null;
    expect(()=>analyzeStructureSnapshot(data)).toThrow('timing');
  });
  it('runs the shared analyzer on the preserved Endless Love case',()=>{
    const data=JSON.parse(readFileSync(new URL('../evaluation/case-assets/S-STRUCT-003/events.json',import.meta.url),'utf8'));
    const snapshot=analyzeStructureSnapshot({...data,sourceHash:'case-S-STRUCT-003'});
    expect(snapshot.dependencies.analyzer).toBe(snapshot.rawAnalysis.version);
    expect(snapshot.units.some(u=>u.kind==='phrase')).toBe(true);
    expect(snapshot.units.some(u=>u.kind==='motif')).toBe(true);
    expect(structureSearchQueries(snapshot).length).toBeGreaterThan(0);
    expect(snapshot.events).toHaveLength(data.events.length);
  });
});
