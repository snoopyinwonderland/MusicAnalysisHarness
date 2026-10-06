import {it,expect} from 'vitest';
import {selectStructureQueries,runPreclearanceSearch,aggregatePreclearanceResults,SELECTION_CONFIG} from './preclearance-search.mjs';

it('keeps phrase selection unchanged when motifs are added',()=>{
 const s=snapshot();s.units.push({...s.units[0],unitId:'motif1',kind:'motif'});
 const a=selectStructureQueries(s),b=selectStructureQueries(s,{...SELECTION_CONFIG,kinds:['phrase','motif']});
 expect(b.selected.slice(0,a.selected.length)).toEqual(a.selected);expect(a.selected.every(e=>e.task.kinds.includes('phrase'))).toBe(true);
});
it('subdivides long phrases while preserving parent identity',()=>{
 const s=snapshot();s.units=[{...s.units[0],eventIds:s.events.map(e=>e.id),attackEventIds:s.events.map(e=>e.id),endQuarter:28}];
 const selected=selectStructureQueries(s,{...SELECTION_CONFIG,maximumNotes:12});expect(selected.selected.length).toBeGreaterThan(0);
 for(const e of selected.selected){expect(e.task.parentUnitIds).toEqual(['p0']);expect(e.task.query.events.filter(n=>n.kind==='note').length).toBeLessThanOrEqual(12)}
});
it('excludes verified same-composition editions without title-only filtering',async()=>{
 const same=result('same-edition'),different=result('other');
 const report=await runPreclearanceSearch(snapshot(),{excludedCanonicalWorkId:'original',resolveIdentity:w=>w.sourceId==='same-edition'?{status:'verified',canonicalWorkId:'original'}:null,search:()=>({similar:[same,different],exact:[]})});
 expect(report.works).toHaveLength(1);expect(report.works[0].key).toBe('source:other');
});

function snapshot(){
 const pitches=[60,62,65,64,67,69,65,60],events=Array.from({length:3},(_,j)=>pitches.map((p,i)=>({id:`${j}-${i}`,kind:'note',pitchMidi:p+j*2,durationRatio:1,onset:j*10+i,beat:i+1}))).flat();
 const units=Array.from({length:3},(_,j)=>({unitId:`p${j}`,kind:'phrase',eventIds:events.slice(j*8,j*8+8).map(e=>e.id),attackEventIds:events.slice(j*8,j*8+8).map(e=>e.id),startQuarter:j*10,endQuarter:j*10+8}));
 return {snapshotId:'s',identity:{sourceId:'self',workId:'self-id'},dependencies:{analyzer:'v1'},meter:'4/4',events,units};
}
const result=(sourceId='other',workId='other-id')=>({kind:'similar',localSimilarity:91,occurrenceImportance:80,alignment:Array.from({length:8},(_,i)=>({queryIndex:i,candidateIndex:i,type:'match'})),work:{sourceId,workId,streamId:'P1',title:'Other',notes:Array.from({length:8},(_,i)=>({id:`c${i}`,pitchMidi:60+i,onset:i}))}});
it('allows known local phrase meters in a changing-meter work',()=>{
 const s=snapshot();s.meter='unknown';s.events.forEach(e=>e.meter='3/4');
 expect(selectStructureQueries(s).selected[0].task.query.meter).toBe('3/4');
 s.events[2].meter='2/4';expect(selectStructureQueries(s).rejected.some(r=>r.reason==='meter-needs-review')).toBe(true);
});
it('does not merge identical note patterns with different meter or beat phase',()=>{
 const s=snapshot();s.meter='unknown';s.events.forEach((e,i)=>{e.meter=i<8?'3/4':'4/4';if(i===16)e.beat=2});
 expect(selectStructureQueries(s).selected).toHaveLength(3);
});
it('groups transposed repetitions without multiplying search tasks',()=>{
 const s=selectStructureQueries(snapshot());expect(s.selected).toHaveLength(1);expect(s.selected[0].occurrences).toHaveLength(3);
 expect(s.selected[0].importance.components.cadence).toBe(null);
});
it('suppresses short and low-information queries and bounds the task budget',()=>{
 const data=snapshot();data.events.forEach(e=>e.pitchMidi=60);
 expect(selectStructureQueries(data).selected).toHaveLength(0);
 expect(()=>selectStructureQueries(data,{...SELECTION_CONFIG,maximumTasks:8})).toThrow();
});
it('retains metric phase and excludes self across streams',async()=>{
 const data=snapshot();data.events[0].beat=2.5;
 let submitted;
 const report=await runPreclearanceSearch(data,{search:q=>{submitted=q;return {exact:[result('self','another-stream')],similar:[result()]};}});
 expect(submitted.events[0]).toMatchObject({kind:'rest',durationRatio:1.5});
 expect(report.works).toHaveLength(1);expect(report.works[0].key).toBe('source:other');
 expect(report.works[0].reviewPriority).toBe(null);
});
it('aggregates parts by source, uses union coverage and keeps best score',()=>{
 const data=snapshot(),entry=selectStructureQueries(data).selected[0];
 const a=result(),b=result('other','second');b.localSimilarity=89;
 const run={taskId:entry.task.taskId,selection:entry,result:{similar:[a,b]}};
 const groups=aggregatePreclearanceResults(data,[run,run]);
 expect(groups).toHaveLength(1);expect(groups[0].similarity).toBe(91);expect(groups[0].coverage).toBe(1);
});
it('records search failures instead of claiming successful empty results',async()=>{
 const report=await runPreclearanceSearch(snapshot(),{search:()=>{throw new Error('fixture failure');}});
 expect(report.status).toBe('partial');expect(report.runs[0].error).toBe('fixture failure');
});
it('returns needs-review when no sufficiently specific segment remains',async()=>{
 const data=snapshot();data.meter=null;
 const report=await runPreclearanceSearch(data,{search:()=>{throw new Error('must not run');}});
 expect(report.status).toBe('needs-review');expect(report.runs).toHaveLength(0);
});
it('checkpoints every completed task and gates a known accompaniment role',async()=>{
 const data=snapshot(),saved=[];
 await runPreclearanceSearch(data,{search:()=>({exact:[],similar:[]}),onResult:run=>saved.push(run)});
 expect(saved).toHaveLength(1);expect(saved[0].status).toBe('completed');
 data.identity.melodyRoleScore=.1;
 expect(selectStructureQueries(data).selected).toHaveLength(0);
 expect(selectStructureQueries(data).rejected[0].reason).toBe('low-melody-role');
});
it('reuses completed tasks, retries failures and stops scheduling on cancellation',async()=>{
 const data=snapshot();let calls=0;
 const first=await runPreclearanceSearch(data,{search:()=>{calls++;return {exact:[],similar:[]};}});
 const resumed=await runPreclearanceSearch(data,{completedRuns:first.runs,search:()=>{throw new Error('not expected');}});
 expect(resumed.runs[0].reused).toBe(true);expect(calls).toBe(1);
 const controller=new AbortController();controller.abort();
 expect((await runPreclearanceSearch(data,{signal:controller.signal,search:()=>{throw new Error('not expected');}})).status).toBe('cancelled');
});
